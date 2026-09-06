"""Image metadata extraction and puzzle dimension suggestions (CARD-031).

This module extracts metadata from uploaded images and generates suggestions
for puzzle dimensions that fit the image's aspect ratio within the 10..30
constraint (CON-011).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from pathlib import Path
from typing import NamedTuple

from nonogram.sourcing import image as sourcing_image

__all__ = [
    "AspectRatio",
    "ImageMetadata",
    "extract_metadata",
    "suggest_dimensions",
]


class AspectRatio(NamedTuple):
    """A simplified aspect ratio representation.

    Attributes:
        width: The width component of the ratio (simplified).
        height: The height component of the ratio (simplified).
        decimal: The decimal representation (width / height).
    """

    width: int
    height: int
    decimal: float


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    """Metadata extracted from an uploaded image.

    Attributes:
        width: The image width in pixels (ink bounding box).
        height: The image height in pixels (ink bounding box).
        aspect_ratio: The simplified aspect ratio.
    """

    width: int
    height: int
    aspect_ratio: AspectRatio


def _simplify_ratio(width: int, height: int) -> tuple[int, int]:
    """Simplify a ratio to its lowest terms.

    Args:
        width: The width component.
        height: The height component.

    Returns:
        (simplified_width, simplified_height)
    """
    divisor = gcd(width, height)
    return width // divisor, height // divisor


def extract_metadata(image_path: Path) -> ImageMetadata:
    """Extract metadata from an uploaded image.

    Args:
        image_path: Path to the uploaded image file.

    Returns:
        ImageMetadata with dimensions and aspect ratio.

    Raises:
        UnreadableImage: If the image cannot be read or decoded.
    """
    width, height = sourcing_image.source_shape(str(image_path))
    simplified_w, simplified_h = _simplify_ratio(width, height)
    aspect_ratio = AspectRatio(
        width=simplified_w,
        height=simplified_h,
        decimal=round(width / height, 2),
    )
    return ImageMetadata(width=width, height=height, aspect_ratio=aspect_ratio)


def suggest_dimensions(
    metadata: ImageMetadata, min_size: int = 10, max_size: int = 30
) -> list[tuple[int, int]]:
    """Generate 2-3 suggested puzzle dimensions based on image aspect ratio.

    The suggestions fit the image's aspect ratio within the min_size..max_size
    constraint. Dimensions are ordered by how closely they match the aspect
    ratio (closest first).

    Args:
        metadata: The extracted image metadata.
        min_size: Minimum grid dimension (default 10, per CON-011).
        max_size: Maximum grid dimension (default 30, per CON-011).

    Returns:
        A list of (width, height) tuples, 2-3 items long, ordered by ratio
        match quality. All dimensions are within [min_size, max_size].
    """
    aspect_w = metadata.aspect_ratio.width
    aspect_h = metadata.aspect_ratio.height
    target_ratio = aspect_w / aspect_h

    suggestions: list[tuple[float, tuple[int, int]]] = []

    # Try all combinations within the constraint
    for w in range(min_size, max_size + 1):
        for h in range(min_size, max_size + 1):
            grid_ratio = w / h
            # Calculate how close this dimension is to the target aspect ratio
            ratio_error = abs(grid_ratio - target_ratio) / target_ratio
            suggestions.append((ratio_error, (w, h)))

    # Sort by ratio error (closest first) and take 2-3 best
    suggestions.sort(key=lambda x: x[0])

    # Return top 2-3 suggestions (prefer 3 if available)
    result_count = min(3, len(suggestions))
    return [dims for _, dims in suggestions[:result_count]]


def format_aspect_ratio(aspect_ratio: AspectRatio) -> str:
    """Format aspect ratio as a string for display.

    Args:
        aspect_ratio: The aspect ratio to format.

    Returns:
        A string like "4:3 (1.33)".
    """
    return f"{aspect_ratio.width}:{aspect_ratio.height} ({aspect_ratio.decimal})"
