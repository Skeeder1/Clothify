"""Filename parser for extracting product information."""

import os
from dataclasses import dataclass
from typing import Optional

from ..config import config


@dataclass
class ParsedFilename:
    """Parsed filename information."""
    product_name: str
    garment: str
    size: str
    extension: str
    is_valid: bool
    error: Optional[str] = None


def parse_filename(filename: str) -> ParsedFilename:
    """
    Parse filename following convention: {product}-{garment}-{size}.{ext}

    Examples:
        - "hoodie_nike-pull-2.webp" -> product=hoodie_nike, garment=pull, size=2
        - "tshirt-tshirt-1.webp" -> product=tshirt, garment=tshirt, size=1
        - "pull_noir-pull-1.webp" -> product=pull_noir, garment=pull, size=1

    Args:
        filename: The filename to parse

    Returns:
        ParsedFilename with extracted information
    """
    # Get extension
    name, extension = os.path.splitext(filename)
    extension = extension.lower()

    # Check extension is supported
    if extension not in config.SUPPORTED_EXTENSIONS:
        return ParsedFilename(
            product_name="",
            garment="other",
            size="2",
            extension=extension,
            is_valid=False,
            error=f"Unsupported extension: {extension}. Supported: {', '.join(config.SUPPORTED_EXTENSIONS)}"
        )

    # Split by hyphen
    parts = name.split("-")

    if len(parts) < 3:
        return ParsedFilename(
            product_name=name,
            garment="other",
            size="2",
            extension=extension,
            is_valid=False,
            error=f"Invalid filename format. Expected: product-garment-size.ext (e.g., hoodie_nike-pull-2.webp)"
        )

    # Extract parts: everything before last 2 parts is product name
    size = parts[-1]
    garment = parts[-2]
    product_name = "-".join(parts[:-2])

    # Validate size
    if size not in config.VALID_SIZES:
        return ParsedFilename(
            product_name=product_name,
            garment=garment if garment in config.VALID_GARMENTS else "other",
            size="2",  # Default size
            extension=extension,
            is_valid=False,
            error=f"Invalid size: {size}. Valid sizes: {', '.join(config.VALID_SIZES)}"
        )

    # Validate garment
    if garment not in config.VALID_GARMENTS:
        return ParsedFilename(
            product_name=product_name,
            garment="other",  # Default to 'other'
            size=size,
            extension=extension,
            is_valid=False,
            error=f"Invalid garment: {garment}. Valid garments: {', '.join(config.VALID_GARMENTS)}"
        )

    return ParsedFilename(
        product_name=product_name,
        garment=garment,
        size=size,
        extension=extension,
        is_valid=True
    )


def get_usage_help() -> str:
    """Get help text for filename format."""
    return (
        "**Filename Format:** `product-garment-size.ext`\n\n"
        "**Example:** `hoodie_nike-pull-2.webp`\n\n"
        f"**Valid garments:** {', '.join(config.VALID_GARMENTS)}\n"
        f"**Valid sizes:** {', '.join(config.VALID_SIZES)}\n"
        f"**Valid extensions:** {', '.join(config.SUPPORTED_EXTENSIONS)}"
    )
