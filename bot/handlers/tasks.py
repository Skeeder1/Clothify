"""Job watcher for monitoring and sending completed jobs to Discord."""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import discord

from ..database import get_job_output, update_job_status
from ..utils.files import file_exists, docker_to_host_path

logger = logging.getLogger(__name__)

# Configuration
WATCH_TIMEOUT = 120  # 2 minutes max
WATCH_INTERVAL = 5   # Poll every 5 seconds

# Discord client reference (set by main.py)
_discord_client: Optional[discord.Client] = None


def set_discord_client(client: discord.Client) -> None:
    """
    Set the Discord client reference for sending messages.

    Args:
        client: Discord client instance
    """
    global _discord_client
    _discord_client = client
    logger.info("Discord client set for tasks")


async def start_job_watcher(
    job_id: UUID,
    discord_message: discord.Message,
    product_name: str
) -> None:
    """
    Start a watcher task for a specific job.

    The watcher polls the database for the job's output_file_path.
    Once available, it sends the image to Discord.

    Args:
        job_id: UUID of the job to watch
        discord_message: Original Discord message to reply to
        product_name: Product name/ID for the response
    """
    asyncio.create_task(
        _watch_job(job_id, discord_message, product_name)
    )
    logger.info(f"Started watcher for job {job_id}")


async def _watch_job(
    job_id: UUID,
    discord_message: discord.Message,
    product_name: str
) -> None:
    """
    Watch a job and send the image when ready.

    Args:
        job_id: UUID of the job to watch
        discord_message: Original Discord message to reply to
        product_name: Product name/ID for the response
    """
    elapsed = 0

    while elapsed < WATCH_TIMEOUT:
        await asyncio.sleep(WATCH_INTERVAL)
        elapsed += WATCH_INTERVAL

        try:
            # Check if output file path is set
            output_path = await get_job_output(job_id)

            if output_path:
                # Convert Docker path to host path
                host_path = docker_to_host_path(output_path)
                logger.info(f"Job {job_id}: output found at {host_path}")

                if file_exists(host_path):
                    # Send image to Discord
                    await _send_image_reply(discord_message, host_path, product_name)
                    await update_job_status(job_id, "sent", "Image sent to Discord")
                    logger.info(f"Job {job_id} completed and sent to Discord")
                    return
                else:
                    logger.warning(f"Job {job_id}: file not found on disk yet: {host_path}")

        except Exception as e:
            logger.error(f"Error watching job {job_id}: {e}")

    # Timeout reached
    logger.error(f"Job {job_id} timed out after {WATCH_TIMEOUT}s")
    await update_job_status(job_id, "error", f"Timeout after {WATCH_TIMEOUT}s - no response from n8n")

    # Notify user of timeout
    try:
        await discord_message.reply(
            content=f"**Erreur:** Le traitement de `{product_name}` a expire (timeout {WATCH_TIMEOUT}s)."
        )
    except Exception:
        pass


async def _send_image_reply(
    message: discord.Message,
    image_path: str,
    product_name: str
) -> None:
    """
    Send the generated image as a reply to the original message.

    Args:
        message: Discord message to reply to
        image_path: Path to the image file
        product_name: Product name/ID
    """
    file = discord.File(image_path, filename=Path(image_path).name)
    await message.reply(
        content=f"**Image generee !**\n**Produit:** `{product_name}`",
        file=file
    )

    # Update reactions: remove hourglass, add checkmark
    try:
        await message.remove_reaction("\u23f3", _discord_client.user)
    except (discord.errors.NotFound, discord.errors.Forbidden, AttributeError):
        pass

    try:
        await message.add_reaction("\u2705")
    except (discord.errors.Forbidden, AttributeError):
        pass

    logger.info(f"Sent image reply for product {product_name}")
