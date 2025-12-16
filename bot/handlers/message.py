"""Message handler for receiving and processing images."""

import logging
import os

import discord

from ..config import config
from ..database import get_or_create_user, create_job, get_pending_jobs_count, get_user_stats
from ..utils.files import save_attachment
from ..utils.parser import parse_filename, get_usage_help

logger = logging.getLogger(__name__)


def setup_message_handler(client: discord.Client) -> None:
    """
    Set up the message handler for the Discord client.

    Args:
        client: Discord client instance
    """

    @client.event
    async def on_message(message: discord.Message) -> None:
        """Handle incoming messages."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Handle commands
        if message.content.startswith("!"):
            await handle_command(message)
            return

        # Check for image attachments
        if not message.attachments:
            return

        await handle_image_upload(message)


async def handle_command(message: discord.Message) -> None:
    """Handle bot commands."""
    content = message.content.lower().strip()

    if content == "!help":
        help_text = (
            "**Clothify Bot - Help**\n\n"
            "Upload an image with the correct filename format to generate a professional product image.\n\n"
            f"{get_usage_help()}\n\n"
            "**Commands:**\n"
            "`!help` - Show this help message\n"
            "`!status` - Show bot status and your stats"
        )
        await message.reply(help_text)

    elif content == "!status":
        pending_count = await get_pending_jobs_count()
        user_stats = await get_user_stats(str(message.author.id))

        status_text = f"**Clothify Bot Status**\n\n"
        status_text += f"Pending jobs in queue: **{pending_count}**\n\n"

        if user_stats:
            status_text += f"**Your Stats:**\n"
            status_text += f"Total jobs: {user_stats['total_jobs']}\n"
            status_text += f"Pending: {user_stats['pending_jobs']}\n"
            status_text += f"Completed: {user_stats['completed_jobs']}"
        else:
            status_text += "You haven't submitted any jobs yet."

        await message.reply(status_text)


async def handle_image_upload(message: discord.Message) -> None:
    """
    Handle image upload from a Discord message.

    Args:
        message: Discord message with attachments
    """
    # Filter for supported image formats
    valid_attachments = []
    for attachment in message.attachments:
        ext = os.path.splitext(attachment.filename)[1].lower()
        if ext in config.SUPPORTED_EXTENSIONS:
            valid_attachments.append(attachment)

    if not valid_attachments:
        return  # No valid images, ignore silently

    # Process each valid image
    saved_paths = []
    parsed_info = None
    has_errors = False

    for attachment in valid_attachments:
        # Parse filename to extract product info
        parsed = parse_filename(attachment.filename)

        if not parsed.is_valid:
            # Reply with error and usage help
            error_msg = (
                f"Invalid filename: `{attachment.filename}`\n"
                f"Error: {parsed.error}\n\n"
                f"{get_usage_help()}"
            )
            await message.reply(error_msg)
            has_errors = True
            continue

        # Save the first valid parsed info for the job
        if parsed_info is None:
            parsed_info = parsed

        try:
            # Save attachment to input directory
            file_path = await save_attachment(attachment, config.INPUT_IMAGES_PATH)
            saved_paths.append(file_path)
            logger.info(f"Saved image: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save attachment {attachment.filename}: {e}")
            await message.add_reaction("❌")
            await message.reply(f"Failed to save image `{attachment.filename}`: {str(e)}")
            has_errors = True

    # If no valid files were saved, return
    if not saved_paths or parsed_info is None:
        return

    try:
        # Get or create user
        user_id = await get_or_create_user(
            discord_id=str(message.author.id),
            discord_name=str(message.author)
        )

        # Get custom prompt from message content (if any text was included)
        custom_prompt = message.content.strip() if message.content.strip() else None

        # Create job in database
        job_id = await create_job(
            user_id=user_id,
            discord_message_id=str(message.id),
            discord_channel_id=str(message.channel.id),
            input_file_paths=saved_paths,
            product_name=parsed_info.product_name,
            garment=parsed_info.garment,
            size=parsed_info.size,
            custom_prompt=custom_prompt
        )

        # React with hourglass to indicate processing
        await message.add_reaction("⏳")

        logger.info(
            f"Created job {job_id} for user {message.author} "
            f"with {len(saved_paths)} image(s)"
        )

    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        await message.add_reaction("❌")
        await message.reply(f"Failed to process your request: {str(e)}")
