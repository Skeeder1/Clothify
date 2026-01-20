"""Database operations using asyncpg with connection pooling."""

import logging
import json
import random
import string
from uuid import UUID
from typing import Optional
import asyncpg

from .config import config

logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_pool() -> asyncpg.Pool:
    """Initialize the database connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    logger.info("Initializing database connection pool...")
    _pool = await asyncpg.create_pool(
        config.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=60
    )
    logger.info("Database connection pool initialized")
    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def get_pool() -> asyncpg.Pool:
    """Get the connection pool, initializing if needed."""
    if _pool is None:
        return await init_pool()
    return _pool


async def get_or_create_user(discord_id: str, discord_name: str) -> UUID:
    """
    Get existing user or create new one.

    Args:
        discord_id: Discord user ID
        discord_name: Discord username

    Returns:
        User UUID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Try to get existing user
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE discord_id = $1",
            discord_id
        )

        if row:
            # Update last_seen_at
            await conn.execute(
                "UPDATE users SET last_seen_at = NOW(), discord_name = $2 WHERE discord_id = $1",
                discord_id, discord_name
            )
            return row["id"]

        # Create new user
        row = await conn.fetchrow(
            """
            INSERT INTO users (discord_id, discord_name)
            VALUES ($1, $2)
            RETURNING id
            """,
            discord_id, discord_name
        )
        logger.info(f"Created new user: {discord_name} ({discord_id})")
        return row["id"]


async def create_job(
    user_id: UUID,
    discord_message_id: str,
    input_file_paths: list[str],
    product_name: str,
    garment: str,
    size: str,
    genre: Optional[str] = None,
    angle: Optional[str] = None,
    custom_prompt: Optional[str] = None
) -> UUID:
    """
    Create a new job with pending status.

    Args:
        user_id: User UUID
        discord_message_id: Discord message ID
        input_file_paths: List of input file paths
        product_name: Product name extracted from filename
        garment: Garment type
        size: Size code
        genre: Gender selection (Homme/Femme)
        angle: Angle selection (face/Profil/dos/Trois-quarts face)
        custom_prompt: Optional custom prompt from message content

    Returns:
        Job UUID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Store input_file_paths as JSON array string
        input_paths_str = json.dumps(input_file_paths)

        row = await conn.fetchrow(
            """
            INSERT INTO jobs (
                user_id, discord_message_id,
                input_file_paths, product_name, garment, genre, angle, size, custom_prompt, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::size_code, $9, 'pending')
            RETURNING id
            """,
            user_id, discord_message_id,
            input_paths_str, product_name, garment, genre, angle, size, custom_prompt
        )

        # Update user's total_jobs count
        await conn.execute(
            "UPDATE users SET total_jobs = total_jobs + 1 WHERE id = $1",
            user_id
        )

        # Log to job_logs
        await conn.execute(
            """
            INSERT INTO job_logs (job_id, status, message)
            VALUES ($1, 'pending', 'Job created from Discord')
            """,
            row["id"]
        )

        logger.info(f"Created job {row['id']} for message {discord_message_id}")
        return row["id"]


async def get_done_jobs() -> list[asyncpg.Record]:
    """
    Get all jobs with status 'done'.

    Returns:
        List of job records
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, discord_message_id,
                   input_file_paths, output_file_path, product_name,
                   garment, size, custom_prompt, created_at, completed_at
            FROM jobs
            WHERE status = 'done'
            ORDER BY completed_at ASC
            """
        )
        return rows


async def get_job_output(job_id: UUID) -> Optional[str]:
    """
    Get output_file_path for a specific job.

    Args:
        job_id: Job UUID

    Returns:
        Output file path or None if not yet available
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT output_file_path FROM jobs WHERE id = $1",
            job_id
        )
        return row["output_file_path"] if row else None


async def update_job_status(job_id: UUID, status: str, message: Optional[str] = None) -> None:
    """
    Update job status.

    Args:
        job_id: Job UUID
        status: New status ('pending', 'processing', 'done', 'error', 'sent')
        message: Optional log message
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE jobs SET status = $2::job_status WHERE id = $1",
            job_id, status
        )

        # Log status change
        log_message = message or f"Status changed to {status}"
        await conn.execute(
            """
            INSERT INTO job_logs (job_id, status, message)
            VALUES ($1, $2::job_status, $3)
            """,
            job_id, status, log_message
        )

        logger.info(f"Job {job_id} status updated to {status}")


async def get_pending_jobs_count() -> int:
    """Get count of pending jobs."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM jobs WHERE status = 'pending'"
        )
        return row["count"]


async def get_user_stats(discord_id: str) -> Optional[dict]:
    """Get user statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.discord_name, u.total_jobs, u.created_at,
                   COUNT(CASE WHEN j.status = 'pending' THEN 1 END) as pending_jobs,
                   COUNT(CASE WHEN j.status = 'done' THEN 1 END) as completed_jobs
            FROM users u
            LEFT JOIN jobs j ON u.id = j.user_id
            WHERE u.discord_id = $1
            GROUP BY u.id
            """,
            discord_id
        )
        if row:
            return dict(row)
        return None


async def product_name_exists(product_name: str) -> bool:
    """
    Check if a product name already exists in the database.

    Args:
        product_name: Product name to check

    Returns:
        True if exists, False otherwise
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM jobs WHERE product_name = $1 LIMIT 1",
            product_name
        )
        return row is not None


async def generate_unique_product_id() -> str:
    """
    Generate a unique product ID (6 characters, alphanumeric).

    The ID is checked against the database to ensure uniqueness.

    Returns:
        Unique product ID (e.g., 'ABC123')
    """
    max_attempts = 100
    for _ in range(max_attempts):
        # Generate 6 character ID (uppercase letters + digits)
        product_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Check if it exists
        if not await product_name_exists(product_id):
            return product_id

    # Fallback: use longer ID if all attempts fail
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
