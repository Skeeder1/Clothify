"""Configuration module for Clothify Discord Bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")


class Config:
    """Bot configuration loaded from environment variables."""

    # Discord
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/clothify")

    # File paths
    INPUT_IMAGES_PATH: str = os.getenv("INPUT_IMAGES_PATH", "./images/input")
    OUTPUT_IMAGES_PATH: str = os.getenv("OUTPUT_IMAGES_PATH", "./images/output")

    # Polling
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))

    # Supported image extensions
    SUPPORTED_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png", ".webp"]

    # Valid garment types (must match database enum)
    VALID_GARMENTS: list[str] = [
        "echarpe", "pull", "tshirt", "chemise", "veste",
        "manteau", "pantalon", "jean", "short", "jupe",
        "robe", "bonnet", "casquette", "sac", "other"
    ]

    # Valid sizes (must match database enum)
    VALID_SIZES: list[str] = ["1", "2", "3", "4"]

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_BOT_TOKEN is required")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        return True


config = Config()
