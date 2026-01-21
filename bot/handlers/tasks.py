"""Job watcher for monitoring and sending completed jobs to Discord."""

import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

import discord

from ..database import get_job_output, update_job_status
from ..utils.files import file_exists

logger = logging.getLogger(__name__)

from ..config import config

# Configuration (loaded from environment variables)
WATCH_TIMEOUT = config.WATCH_TIMEOUT_SECONDS
WATCH_INTERVAL = config.WATCH_INTERVAL_SECONDS


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
    product_name: str,
    interaction: discord.Interaction = None
) -> None:
    """
    Start a watcher task for a specific job.

    The watcher polls the database for the job's output_file_path.
    Once available, it sends the image to Discord.

    Args:
        job_id: UUID of the job to watch
        discord_message: Original Discord message to reply to
        product_name: Product name/ID for the response
        interaction: Discord interaction for ephemeral error messages
    """
    asyncio.create_task(
        _watch_job(job_id, discord_message, product_name, interaction)
    )
    logger.info(f"Started watcher for job {job_id}")


async def _watch_job(
    job_id: UUID,
    discord_message: discord.Message,
    product_name: str,
    interaction: discord.Interaction = None
) -> None:
    """
    Watch a job and send the image when ready.

    Args:
        job_id: UUID of the job to watch
        discord_message: Original Discord message to reply to
        product_name: Product name/ID for the response
        interaction: Discord interaction for ephemeral error messages
    """
    elapsed = 0

    while elapsed < WATCH_TIMEOUT:
        await asyncio.sleep(WATCH_INTERVAL)
        elapsed += WATCH_INTERVAL

        try:
            # Check if output file path is set
            output_path = await get_job_output(job_id)

            if output_path:
                # Use path directly (no conversion needed - shared volume)
                logger.info(f"Job {job_id}: output found at {output_path}")

                if file_exists(output_path):
                    # Send image to Discord
                    await _send_image_reply(discord_message, output_path, product_name)
                    await update_job_status(job_id, "sent", "Image sent to Discord")
                    logger.info(f"Job {job_id} completed and sent to Discord")
                    return
                else:
                    logger.warning(f"Job {job_id}: file not found on disk yet: {output_path}")

        except Exception as e:
            logger.error(f"Error watching job {job_id}: {e}")

    # Timeout reached
    logger.error(f"Job {job_id} timed out after {WATCH_TIMEOUT}s")
    await update_job_status(job_id, "error", f"Timeout after {WATCH_TIMEOUT}s - no response from n8n")

    # Notify user of timeout via ephemeral message (visible only to them)
    if interaction:
        try:
            await interaction.followup.send(
                content=f"**❌ Erreur:** Le traitement de `{product_name}` a expiré (timeout {WATCH_TIMEOUT}s).\nVeuillez réessayer.",
                ephemeral=True
            )
        except Exception as e:
            logger.warning(f"Could not send ephemeral error: {e}")


async def _send_image_reply(
    message: discord.Message,
    image_path: str,
    product_name: str
) -> None:
    """
    Send the generated image and delete the original message.

    Args:
        message: Discord message to reply to
        image_path: Path to the image file
        product_name: Product name/ID
    """
    file = discord.File(image_path, filename=Path(image_path).name)
    
    # Send image in channel without text
    await message.channel.send(file=file)

    # Delete original message (with user's uploaded image)
    try:
        await message.delete()
        logger.info(f"Deleted original message for product {product_name}")
    except (discord.errors.NotFound, discord.errors.Forbidden) as e:
        logger.warning(f"Could not delete original message: {e}")

    logger.info(f"Sent image for product {product_name}")
