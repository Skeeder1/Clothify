"""Discord UI components for interactive bot flow."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import discord

from ..config import config
from ..database import get_or_create_user, create_job, generate_unique_product_id
from .tasks import start_job_watcher

logger = logging.getLogger(__name__)

# ===========================================
# Pending Uploads Cache
# ===========================================

@dataclass
class PendingUpload:
    """Stores temporary upload state between interactions."""
    image_paths: list[str]
    original_message: discord.Message
    user_id: str
    user_name: str
    garment: Optional[str] = None
    custom_prompt: Optional[str] = None
    selection_message: Optional[discord.Message] = None
    created_at: datetime = field(default_factory=datetime.now)


# Cache for pending uploads (key: user_id)
pending_uploads: dict[str, PendingUpload] = {}


def get_pending_upload(user_id: str) -> Optional[PendingUpload]:
    """Get pending upload for a user."""
    upload = pending_uploads.get(user_id)
    if upload:
        # Check if expired (5 minutes timeout)
        if (datetime.now() - upload.created_at).seconds > 300:
            del pending_uploads[user_id]
            return None
    return upload


def set_pending_upload(user_id: str, upload: PendingUpload) -> None:
    """Store pending upload for a user."""
    pending_uploads[user_id] = upload


def remove_pending_upload(user_id: str) -> None:
    """Remove pending upload for a user."""
    pending_uploads.pop(user_id, None)


# ===========================================
# Garment Options
# ===========================================

GARMENT_OPTIONS = [
    ("🧣", "Écharpe", "echarpe"),
    ("🧥", "Pull", "pull"),
    ("👕", "T-shirt", "tshirt"),
    ("👔", "Chemise", "chemise"),
    ("🧥", "Veste", "veste"),
    ("🧥", "Manteau", "manteau"),
    ("👖", "Pantalon", "pantalon"),
    ("👖", "Jean", "jean"),
    ("🩳", "Short", "short"),
    ("👗", "Jupe", "jupe"),
    ("👗", "Robe", "robe"),
    ("🧢", "Bonnet", "bonnet"),
    ("🧢", "Casquette", "casquette"),
    ("👜", "Sac", "sac"),
    ("❓", "Autre", "other"),
]


# ===========================================
# Garment Selection View
# ===========================================

class GarmentSelect(discord.ui.Select):
    """Dropdown menu for selecting garment type."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label=label,
                value=value,
                emoji=emoji
            )
            for emoji, label, value in GARMENT_OPTIONS
        ]
        super().__init__(
            placeholder="Sélectionnez un type de vêtement...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle garment selection."""
        user_id = str(interaction.user.id)
        selected_garment = self.values[0]

        # Get pending upload
        upload = get_pending_upload(user_id)
        if not upload:
            await interaction.response.send_message(
                "Cette sélection n'est pas pour vous, ou votre session a expiré.",
                ephemeral=True
            )
            return

        # Verify it's the same user who uploaded
        if user_id != upload.user_id:
            await interaction.response.send_message(
                "Cette sélection n'est pas pour vous.",
                ephemeral=True
            )
            return

        # Update garment        # Update garment
        upload.garment = selected_garment
        set_pending_upload(user_id, upload)

        # Find garment label for display
        garment_label = next(
            (label for _, label, value in GARMENT_OPTIONS if value == selected_garment),
            selected_garment
        )

        logger.info(f"User {user_id} selected garment: {selected_garment}")

        # Delete the original selection message to keep chat clean
        try:
            if upload.selection_message:
                await upload.selection_message.delete()
        except discord.errors.NotFound:
            pass  # Message already deleted
        except Exception as e:
            logger.warning(f"Could not delete selection message: {e}")

        # Send size selection as ephemeral message
        await interaction.response.send_message(
            content=f"**Vêtement:** {garment_label}\n\n📏 **Quelle taille de visuel ?**",
            view=SizeSelectView(user_id),
            ephemeral=True
        )


class GarmentSelectView(discord.ui.View):
    """View containing the garment selection dropdown."""

    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.add_item(GarmentSelect())

    async def on_timeout(self):
        """Handle view timeout."""
        # Disable all components
        for item in self.children:
            item.disabled = True


# ===========================================
# Size Selection View
# ===========================================

class SizeSelectView(discord.ui.View):
    """View with buttons for selecting size."""

    def __init__(self, user_id: str):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="1 - Petit", style=discord.ButtonStyle.secondary, custom_id="size_1")
    async def size_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_size_selection(interaction, "1")

    @discord.ui.button(label="2 - Standard", style=discord.ButtonStyle.primary, custom_id="size_2")
    async def size_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_size_selection(interaction, "2")

    @discord.ui.button(label="3 - Moyen", style=discord.ButtonStyle.primary, custom_id="size_3")
    async def size_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_size_selection(interaction, "3")

    @discord.ui.button(label="4 - Grand", style=discord.ButtonStyle.secondary, custom_id="size_4")
    async def size_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_size_selection(interaction, "4")

    async def handle_size_selection(self, interaction: discord.Interaction, size: str):
        """Handle size button click and create the job."""
        user_id = str(interaction.user.id)

        # Verify it's the same user
        if user_id != self.user_id:
            await interaction.response.send_message(
                "Cette sélection n'est pas pour vous.",
                ephemeral=True
            )
            return

        # Get pending upload
        upload = get_pending_upload(user_id)
        if not upload:
            await interaction.response.send_message(
                "Session expirée. Veuillez renvoyer votre image.",
                ephemeral=True
            )
            return

        if not upload.garment:
            await interaction.response.send_message(
                "Erreur: vêtement non sélectionné.",
                ephemeral=True
            )
            return

        try:
            # Generate unique product ID
            product_id = await generate_unique_product_id()

            # Get or create user in database
            db_user_id = await get_or_create_user(
                discord_id=user_id,
                discord_name=upload.user_name
            )

            # Create job in database
            job_id = await create_job(
                user_id=db_user_id,
                discord_message_id=str(upload.original_message.id),
                input_file_paths=upload.image_paths,
                product_name=product_id,
                garment=upload.garment,
                size=size,
                custom_prompt=upload.custom_prompt
            )

            # Start job watcher (monitors DB and sends image when ready)
            await start_job_watcher(job_id, upload.original_message, product_id)

            # React to original message
            try:
                await upload.original_message.add_reaction("⏳")
            except discord.errors.Forbidden:
                pass

            # Find labels for display
            garment_label = next(
                (label for _, label, value in GARMENT_OPTIONS if value == upload.garment),
                upload.garment
            )
            size_labels = {"1": "Petit", "2": "Standard", "3": "Moyen", "4": "Grand"}

            # Send ephemeral confirmation and reply to original message
            await interaction.response.send_message(
                content=(
                    f"✅ **Job créé avec succès !**\n\n"
                    f"**ID:** `{product_id}`\n"
                    f"**Vêtement:** {garment_label}\n"
                    f"**Taille:** {size_labels.get(size, size)}\n\n"
                    f"⏳ Traitement en cours... Vous recevrez l'image directement sur le message original."
                ),
                ephemeral=True
            )

            logger.info(f"Created job {job_id} for user {user_id} - {product_id}")

            # Clean up pending upload
            remove_pending_upload(user_id)

        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            await interaction.response.send_message(
                f"Erreur lors de la création du job: {str(e)}",
                ephemeral=True
            )

    async def on_timeout(self):
        """Handle view timeout."""
        for item in self.children:
            item.disabled = True
