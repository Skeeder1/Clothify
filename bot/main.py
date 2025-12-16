#!/usr/bin/env python3
"""
Clothify Discord Bot - Main Entry Point

A Discord bot that receives product images, saves them for AI processing,
and sends back the generated professional e-commerce images.
"""

import logging
import sys

import discord

from .config import config
from .database import init_pool, close_pool
from .handlers.message import setup_message_handler
from .handlers.tasks import start_polling_task, stop_polling_task
from .utils.files import ensure_directories_exist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def create_bot() -> discord.Client:
    """
    Create and configure the Discord bot client.

    Returns:
        Configured Discord client
    """
    # Set up intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True

    # Create client
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        """Called when the bot is ready and connected."""
        logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
        logger.info(f"Connected to {len(client.guilds)} guild(s)")

        # Ensure directories exist
        ensure_directories_exist()

        # Initialize database connection pool
        try:
            await init_pool()
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.error("Bot will continue but database operations will fail")

        # Start background polling task
        start_polling_task()

        logger.info("Clothify Bot is ready!")

    @client.event
    async def on_disconnect():
        """Called when the bot disconnects."""
        logger.warning("Bot disconnected from Discord")

    @client.event
    async def on_resumed():
        """Called when the bot resumes a session."""
        logger.info("Bot session resumed")

    # Set up message handler
    setup_message_handler(client)

    return client


async def shutdown(client: discord.Client) -> None:
    """
    Graceful shutdown procedure.

    Args:
        client: Discord client to shut down
    """
    logger.info("Shutting down...")

    # Stop polling task
    stop_polling_task()

    # Close database pool
    await close_pool()

    # Close Discord connection
    await client.close()

    logger.info("Shutdown complete")


def main() -> None:
    """Main entry point."""
    logger.info("Starting Clothify Discord Bot...")

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create and run bot
    client = create_bot()

    try:
        client.run(config.DISCORD_BOT_TOKEN, log_handler=None)
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
