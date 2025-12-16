"""Message handler for receiving and processing images."""

import logging
import os

import discord

from ..config import config
from ..database import get_pending_jobs_count, get_user_stats
from ..utils.files import save_attachment
from .views import GarmentSelectView, PendingUpload, set_pending_upload

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

        # Only listen in the bot_clothify channel
        if message.channel.name != "bot_clothify":
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
            "**Clothify Bot - Aide**\n\n"
            "Uploadez une image pour générer un visuel produit professionnel.\n\n"
            "**Comment ça marche:**\n"
            "1. Envoyez une image (JPG, PNG, WebP)\n"
            "2. Sélectionnez le type de vêtement dans le menu\n"
            "3. Choisissez la taille du visuel\n"
            "4. Attendez que l'image soit générée\n\n"
            "**Commandes:**\n"
            "`!help` - Afficher cette aide\n"
            "`!status` - Voir le statut du bot et vos stats"
        )
        await message.reply(help_text)

    elif content == "!status":
        pending_count = await get_pending_jobs_count()
        user_stats = await get_user_stats(str(message.author.id))

        status_text = f"**Clothify Bot - Statut**\n\n"
        status_text += f"Jobs en attente: **{pending_count}**\n\n"

        if user_stats:
            status_text += f"**Vos statistiques:**\n"
            status_text += f"Total jobs: {user_stats['total_jobs']}\n"
            status_text += f"En attente: {user_stats['pending_jobs']}\n"
            status_text += f"Terminés: {user_stats['completed_jobs']}"
        else:
            status_text += "Vous n'avez pas encore soumis de jobs."

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

    # Save all valid images
    saved_paths = []
    for attachment in valid_attachments:
        try:
            file_path = await save_attachment(attachment, config.INPUT_IMAGES_PATH)
            saved_paths.append(file_path)
            logger.info(f"Saved image: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save attachment {attachment.filename}: {e}")
            await message.add_reaction("❌")
            await message.reply(f"Erreur lors de la sauvegarde de `{attachment.filename}`: {str(e)}")
            return

    if not saved_paths:
        return

    # Get custom prompt from message content (if any text was included)
    custom_prompt = message.content.strip() if message.content.strip() else None

    # Store pending upload
    user_id = str(message.author.id)
    pending = PendingUpload(
        image_paths=saved_paths,
        original_message=message,
        user_id=user_id,
        user_name=str(message.author),
        custom_prompt=custom_prompt
    )
    set_pending_upload(user_id, pending)

    # Send garment selection view
    view = GarmentSelectView()
    await message.reply(
        "🧥 **Quel type de vêtement ?**\n\nSélectionnez dans le menu ci-dessous:",
        view=view
    )

    logger.info(f"Started interactive flow for user {message.author} with {len(saved_paths)} image(s)")
