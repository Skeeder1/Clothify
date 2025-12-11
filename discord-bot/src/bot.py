import os
import discord
from discord import app_commands
from discord.ext import commands
import httpx
from loguru import logger

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Bot connected: {bot.user}")
    try:
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            await bot.tree.sync(guild=guild)
        else:
            await bot.tree.sync()
        logger.info("Commands synced")
    except Exception as e:
        logger.error(f"Sync error: {e}")


@bot.tree.command(name="generate", description="Generate a product visual")
@app_commands.describe(
    image="Photo of the item",
    morphology="Mannequin body type",
    preset="Presentation style"
)
@app_commands.choices(morphology=[
    app_commands.Choice(name="Small", value="small"),
    app_commands.Choice(name="Slim", value="slim"),
    app_commands.Choice(name="Medium", value="medium"),
    app_commands.Choice(name="Large", value="large"),
])
@app_commands.choices(preset=[
    app_commands.Choice(name="Standing mannequin", value="mannequin"),
    app_commands.Choice(name="On table", value="table"),
    app_commands.Choice(name="Worn", value="worn"),
    app_commands.Choice(name="On hanger", value="hanger"),
])
async def generate(
    interaction: discord.Interaction,
    image: discord.Attachment,
    morphology: app_commands.Choice[str],
    preset: app_commands.Choice[str]
):
    await interaction.response.defer(thinking=True)

    try:
        payload = {
            "user_id": str(interaction.user.id),
            "channel_id": str(interaction.channel_id),
            "image_url": image.url,
            "morphology": morphology.value,
            "preset": preset.value,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()

        await interaction.followup.send(
            f"🎨 **Generation started!**\n"
            f"Body type: {morphology.name}\n"
            f"Style: {preset.name}"
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await interaction.followup.send("❌ Error, please try again.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
