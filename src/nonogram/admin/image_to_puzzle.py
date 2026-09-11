"""Convert images to nonogram puzzles.

Handles image processing, grid extraction, and puzzle generation.
"""

import random
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

try:
    from PIL import Image as PILImage
    import numpy as np
except ImportError:
    PILImage = None
    np = None

from nonogram import clues as nonogram_clues
from nonogram.errors import NonogramError
from nonogram.sourcing import image as sourcing_image


def image_to_grid(image_path: str, target_size: Tuple[int, int]) -> Optional[List[List[bool]]]:
    """Convert image to boolean grid (nonogram).

    Delegates to :mod:`nonogram.sourcing.image` — the same ink-bounding-box
    trim, aspect-preserving centre-crop to the grid's own ratio (ADR-0022/R3),
    and Floyd-Steinberg dithering that ``nonogram generate --mode image`` and
    ``nonogram serve`` use. A puzzle generated here from a given file now
    matches (rather than diverges from, as a previous bounding-box-only crop
    plus a plain resize used to) one generated from the same file through the
    CLI/web path — a plain resize squashes a non-square crop into the target
    square and drops thin detail (e.g. a bird's legs) that dithering keeps.

    Args:
        image_path: Path to image file
        target_size: Target (width, height) for grid

    Returns:
        List[List[bool]] grid where True = filled, False = empty
        Or None if conversion fails
    """
    if not PILImage or not np:
        return None

    width, height = target_size
    try:
        return sourcing_image.generate(image_path, width, height, random.Random())
    except NonogramError as e:
        print(f"Error converting image: {str(e)}")
        return None


def generate_clues(
    grid: List[List[bool]],
) -> Tuple[Tuple[Tuple[int, ...], ...], Tuple[Tuple[int, ...], ...]]:
    """Generate nonogram clues from grid.

    Delegates to :func:`nonogram.clues.compute_clues` — the canonical
    run-length encoder (ADR-0012) admin already calls correctly elsewhere
    (``app.py``'s ``clues.encode_line`` usage). A ragged ``grid`` raises
    ``ValueError`` (via that function's ``zip(..., strict=True)`` guard)
    instead of an uncontrolled ``IndexError``.

    Args:
        grid: List[List[bool]] where True = filled cell

    Returns:
        (row_clues, col_clues), each a tuple of per-line clue tuples
        (ADR-0012 boundary type — ``(0,)`` for an empty line, never ``()``).
    """
    computed = nonogram_clues.compute_clues(grid)
    return computed.rows, computed.columns


def create_puzzle_from_image(
    image_path: str,
    target_width: int,
    target_height: int,
    theme: str = "image",
) -> Optional[Dict[str, Any]]:
    """Create a complete puzzle from an image.

    Args:
        image_path: Path to image file
        target_width: Target puzzle width
        target_height: Target puzzle height
        theme: Theme name for the puzzle

    Returns:
        Dictionary with puzzle data or None if failed
    """
    # Convert image to grid
    grid = image_to_grid(image_path, (target_width, target_height))
    if grid is None:
        return None

    # Generate clues
    row_clues, col_clues = generate_clues(grid)

    # Calculate metrics
    filled_cells = sum(sum(row) for row in grid)
    total_cells = target_width * target_height
    density = filled_cells / total_cells if total_cells > 0 else 0

    # Simple quality score based on density (prefer 30-70% filled)
    if 0.2 <= density <= 0.8:
        quality_score = 80 + int(20 * (1 - abs(density - 0.5) * 2))
    else:
        quality_score = max(40, 80 - int(40 * abs(density - 0.5)))

    # Difficulty based on size
    size_difficulty = (target_width + target_height) / 2
    if size_difficulty < 15:
        difficulty_tier = "Easy"
        difficulty_score = 20 + int(30 * (size_difficulty / 15))
    elif size_difficulty < 25:
        difficulty_tier = "Medium"
        difficulty_score = 50 + int(30 * ((size_difficulty - 15) / 10))
    else:
        difficulty_tier = "Hard"
        difficulty_score = 80 + int(20 * min(1, (size_difficulty - 25) / 5))

    return {
        "grid": grid,
        "clues_rows": row_clues,
        "clues_cols": col_clues,
        "width": target_width,
        "height": target_height,
        "theme": theme,
        "difficulty_score": int(difficulty_score),
        "difficulty_tier": difficulty_tier,
        "quality_score": int(quality_score),
        "recognizability": "medium",  # Images always medium recognizability
        "strategies_used": ["LineLogic", "ConstraintProp"],
    }
