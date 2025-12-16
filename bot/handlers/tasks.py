"""Background tasks for polling completed jobs."""

import asyncio
import logging
from typing import Optional

from ..config import config
from ..database import get_done_jobs, update_job_status
from ..utils.files import file_exists

logger = logging.getLogger(__name__)

# Task reference for cancellation
_polling_task: Optional[asyncio.Task] = None


async def poll_done_jobs() -> None:
    """
    Poll for completed jobs.

    This task runs continuously, checking for jobs with status 'done'
    and marking them as sent once output is ready.
    """
    logger.info(f"Starting job polling task (interval: {config.POLL_INTERVAL_SECONDS}s)")

    while True:
        try:
            await process_done_jobs()
        except Exception as e:
            logger.error(f"Error in polling task: {e}")

        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)


async def process_done_jobs() -> None:
    """Process all jobs with status 'done'."""
    done_jobs = await get_done_jobs()

    if not done_jobs:
        return

    logger.info(f"Found {len(done_jobs)} completed jobs to process")

    for job in done_jobs:
        await process_single_job(job)


async def process_single_job(job: dict) -> None:
    """
    Process a single completed job.

    Args:
        client: Discord client instance
        job: Job record from database
    """
    job_id = job["id"]
    output_path = job["output_file_path"]
    product_name = job.get("product_name", "product")

    logger.info(f"Processing completed job {job_id} - {product_name}")

    # Check if output file exists
    if not output_path or not file_exists(output_path):
        logger.error(f"Output file not found for job {job_id}: {output_path}")
        await update_job_status(job_id, "error", "Output file not found")
        return

    # Mark job as sent (image delivery handled externally via n8n)
    await update_job_status(job_id, "sent", "Job completed, output ready")
    logger.info(f"Job {job_id} marked as sent - output: {output_path}")


def start_polling_task() -> asyncio.Task:
    """
    Start the background polling task.

    Returns:
        The created asyncio Task
    """
    global _polling_task
    _polling_task = asyncio.create_task(poll_done_jobs())
    logger.info("Polling task started")
    return _polling_task


def stop_polling_task() -> None:
    """Stop the background polling task."""
    global _polling_task
    if _polling_task is not None:
        _polling_task.cancel()
        _polling_task = None
        logger.info("Polling task stopped")
