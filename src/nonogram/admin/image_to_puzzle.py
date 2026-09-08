"""Convert images to nonogram puzzles.

Handles image processing, grid extraction, and puzzle generation.
"""

from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

try:
    from PIL import Image as PILImage
    import numpy as np
except ImportError:
    PILImage = None
    np = None


def image_to_grid(image_path: str, target_size: Tuple[int, int]) -> Optional[List[List[bool]]]:
    """Convert image to boolean grid (nonogram).

    Args:
        image_path: Path to image file
        target_size: Target (width, height) for grid

    Returns:
        List[List[bool]] grid where True = filled, False = empty
        Or None if conversion fails
    """
    if not PILImage or not np:
        return None

    try:
        # Open and convert to grayscale
        img = PILImage.open(image_path).convert('L')

        # Crop blank space around the image (content-aware cropping)
        arr = np.array(img)

        # Find rows and columns with content (not blank/white)
        # Threshold: pixels darker than 200 are considered content
        content_threshold = 200
        has_content = arr < content_threshold

        # Find bounding box of content
        rows_with_content = np.any(has_content, axis=1)
        cols_with_content = np.any(has_content, axis=0)

        if np.any(rows_with_content) and np.any(cols_with_content):
            # Get indices of rows/cols with content
            row_indices = np.where(rows_with_content)[0]
            col_indices = np.where(cols_with_content)[0]

            # Crop to bounding box
            top = row_indices[0]
            bottom = row_indices[-1] + 1
            left = col_indices[0]
            right = col_indices[-1] + 1

            img = img.crop((left, top, right, bottom))

        # Resize to target size
        img = img.resize(target_size, PILImage.Resampling.LANCZOS)

        # Convert to numpy array
        arr = np.array(img)

        # Threshold to binary (using Otsu's method - simple fixed threshold)
        threshold = 128
        binary = arr < threshold

        # Convert to list of lists
        grid = binary.tolist()
        return grid

    except Exception as e:
        print(f"Error converting image: {str(e)}")
        return None


def generate_clues(grid: List[List[bool]]) -> Tuple[List[List[int]], List[List[int]]]:
    """Generate nonogram clues from grid.

    Args:
        grid: List[List[bool]] where True = filled cell

    Returns:
        (row_clues, col_clues) where each is List[List[int]]
    """
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    def encode_line(line: List[bool]) -> List[int]:
        """Encode a line into nonogram clues."""
        clues = []
        count = 0
        for cell in line:
            if cell:
                count += 1
            elif count > 0:
                clues.append(count)
                count = 0
        if count > 0:
            clues.append(count)
        return clues if clues else [0]

    # Generate row clues
    row_clues = [encode_line(grid[i]) for i in range(height)]

    # Generate column clues
    col_clues = []
    for j in range(width):
        column = [grid[i][j] for i in range(height)]
        col_clues.append(encode_line(column))

    return row_clues, col_clues


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
