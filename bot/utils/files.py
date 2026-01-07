"""File utilities for saving and managing images."""

import os
import logging
from pathlib import Path

import discord

from ..config import config

logger = logging.getLogger(__name__)


def ensure_directories_exist() -> None:
    """Create input and output directories if they don't exist."""
    input_path = Path(config.INPUT_DIR)
    output_path = Path(config.OUTPUT_DIR)

    input_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Ensured directories exist: {input_path}, {output_path}")


async def save_attachment(attachment: discord.Attachment, directory: str) -> str:
    """
    Save a Discord attachment to the specified directory.

    Args:
        attachment: Discord attachment object
        directory: Directory to save the file

    Returns:
        Full path to the saved file

    Raises:
        IOError: If file cannot be saved
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)

    # Use the original filename
    filename = attachment.filename
    file_path = dir_path / filename

    # Handle duplicate filenames by adding a counter
    counter = 1
    original_stem = file_path.stem
    while file_path.exists():
        file_path = dir_path / f"{original_stem}_{counter}{file_path.suffix}"
        counter += 1

    # Save the file
    await attachment.save(file_path)
    logger.info(f"Saved attachment: {file_path}")

    return str(file_path)


def get_output_file_path(input_filename: str) -> str:
    """
    Get the expected output file path for a given input filename.

    Args:
        input_filename: Name of the input file

    Returns:
        Full path to the expected output file
    """
    # Output files have the same name but in the output directory
    output_path = Path(config.OUTPUT_DIR) / input_filename
    return str(output_path)


def file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return Path(file_path).exists()


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size if file_exists(file_path) else 0
