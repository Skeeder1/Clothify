"""Configuration module for Clothify Discord Bot."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# Load universal configuration from config.yaml
CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    _yaml_config = yaml.safe_load(f)


class Config:
    """Bot configuration loaded from environment variables (.env) and config.yaml."""

    # ==========================================
    # SECRETS (from .env)
    # ==========================================
    
    # Discord
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_GUILD_ID: str = os.getenv("DISCORD_GUILD_ID", "")
    
    # Database (environment-specific)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/clothify")
    
    # Google AI
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")
    
    # n8n
    N8N_ENCRYPTION_KEY: str = os.getenv("N8N_ENCRYPTION_KEY", "")

    # ==========================================
    # PATHS (from .env - environment-specific)
    # ==========================================
    
    SHARED_VOLUME_PATH: str = os.getenv("SHARED_VOLUME_PATH", "/files")
    
    # Derived path constants
    INPUT_DIR: str = f"{SHARED_VOLUME_PATH}/input_image"
    OUTPUT_DIR: str = f"{SHARED_VOLUME_PATH}/output_image"

    # ==========================================
    # UNIVERSAL CONFIG (from config.yaml)
    # ==========================================
    
    # Bot behavior
    POLL_INTERVAL_SECONDS: int = _yaml_config['bot']['poll_interval_seconds']
    WATCH_TIMEOUT_SECONDS: int = _yaml_config['bot']['watch_timeout_seconds']
    WATCH_INTERVAL_SECONDS: int = _yaml_config['bot']['watch_interval_seconds']
    DISCORD_CHANNEL_NAME: str = os.getenv("DISCORD_CHANNEL_NAME", "bot_clothify")
    SUPPORTED_EXTENSIONS: list[str] = _yaml_config['bot']['supported_extensions']
    
    # Discord UI
    VIEW_TIMEOUT: int = _yaml_config['discord']['view_timeout']
    PENDING_UPLOAD_TTL: int = _yaml_config['discord']['pending_upload_ttl']
    
    # Database schema
    VALID_GARMENTS: list[str] = _yaml_config['database']['valid_garments']
    VALID_SIZES: list[str] = _yaml_config['database']['valid_sizes']
    
    # n8n
    N8N_TIMEZONE: str = _yaml_config['n8n']['timezone']
    N8N_PORT: int = int(os.getenv("N8N_PORT", "5678"))
    
    # Jobs
    MAX_JOB_ATTEMPTS: int = _yaml_config['jobs']['max_attempts']
    STALE_TIMEOUT_MINUTES: int = _yaml_config['jobs']['stale_timeout_minutes']

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.DISCORD_BOT_TOKEN:
            raise ValueError("DISCORD_TOKEN is required in .env")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required in .env")
        if not cls.GOOGLE_AI_API_KEY:
            raise ValueError("GOOGLE_AI_API_KEY is required in .env")
        return True


config = Config()
