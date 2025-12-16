"""Background tasks for polling completed jobs."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import discord

from ..config import config
from ..database import get_done_jobs, update_job_status
from ..utils.files import file_exists

logger = logging.getLogger(__name__)

# Task reference for cancellation
_polling_task: Optional[asyncio.Task] = None


async def poll_done_jobs(client: discord.Client) -> None:
    """
    Poll for completed jobs and send results back to users.

    This task runs continuously, checking for jobs with status 'done'
    and sending the generated images back to the original Discord message.

    Args:
        client: Discord client instance
    """
    logger.info(f"Starting job polling task (interval: {config.POLL_INTERVAL_SECONDS}s)")

    while True:
        try:
            await process_done_jobs(client)
        except Exception as e:
            logger.error(f"Error in polling task: {e}")

        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)


async def process_done_jobs(client: discord.Client) -> None:
    """
    Process all jobs with status 'done'.

    Args:
        client: Discord client instance
    """
    done_jobs = await get_done_jobs()

    if not done_jobs:
        return

    logger.info(f"Found {len(done_jobs)} completed jobs to process")

    for job in done_jobs:
        await process_single_job(client, job)


async def process_single_job(client: discord.Client, job: dict) -> None:
    """
    Process a single completed job.

    Args:
        client: Discord client instance
        job: Job record from database
    """
    job_id = job["id"]
    channel_id = job["discord_channel_id"]
    message_id = job["discord_message_id"]
    output_path = job["output_file_path"]

    logger.info(f"Processing completed job {job_id}")

    # Check if output file exists
    if not output_path or not file_exists(output_path):
        logger.error(f"Output file not found for job {job_id}: {output_path}")
        await update_job_status(job_id, "error", "Output file not found")
        return

    try:
        # Get the channel
        channel = client.get_channel(int(channel_id))
        if channel is None:
            # Try fetching the channel
            try:
                channel = await client.fetch_channel(int(channel_id))
            except discord.NotFound:
                logger.warning(f"Channel {channel_id} not found for job {job_id}")
                await update_job_status(job_id, "sent", "Channel not found, marked as sent")
                return
            except discord.Forbidden:
                logger.warning(f"No access to channel {channel_id} for job {job_id}")
                await update_job_status(job_id, "sent", "No channel access, marked as sent")
                return

        # Try to get the original message
        original_message = None
        try:
            original_message = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            logger.warning(f"Original message {message_id} not found for job {job_id}")
        except discord.Forbidden:
            logger.warning(f"No access to message {message_id} for job {job_id}")

        # Send the output image
        output_file = discord.File(output_path)
        product_name = job.get("product_name", "product")

        if original_message:
            # Reply to the original message
            await original_message.reply(
                f"Your product image for **{product_name}** is ready!",
                file=output_file
            )

            # Add checkmark reaction to original message
            try:
                await original_message.add_reaction("✅")
            except discord.Forbidden:
                logger.warning(f"Cannot add reaction to message {message_id}")

            # Try to remove hourglass reaction
            try:
                await original_message.remove_reaction("⏳", client.user)
            except (discord.Forbidden, discord.NotFound):
                pass  # Ignore if we can't remove the reaction
        else:
            # Send to channel without reply
            await channel.send(
                f"Product image for **{product_name}** is ready! "
                f"(Original message not found)",
                file=output_file
            )

        # Update job status to sent
        await update_job_status(job_id, "sent", "Image sent to Discord")
        logger.info(f"Successfully sent output for job {job_id}")

    except discord.HTTPException as e:
        logger.error(f"Discord API error for job {job_id}: {e}")
        # Don't mark as error, will retry on next poll
    except Exception as e:
        logger.error(f"Unexpected error processing job {job_id}: {e}")
        await update_job_status(job_id, "error", f"Error sending image: {str(e)}")


def start_polling_task(client: discord.Client) -> asyncio.Task:
    """
    Start the background polling task.

    Args:
        client: Discord client instance

    Returns:
        The created asyncio Task
    """
    global _polling_task
    _polling_task = asyncio.create_task(poll_done_jobs(client))
    logger.info("Polling task started")
    return _polling_task


def stop_polling_task() -> None:
    """Stop the background polling task."""
    global _polling_task
    if _polling_task is not None:
        _polling_task.cancel()
        _polling_task = None
        logger.info("Polling task stopped")
