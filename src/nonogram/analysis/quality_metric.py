"""Quality metrics for image-to-nonogram conversion.

Measures how well a generated nonogram puzzle preserves the original image.
Three components:
1. Visual Similarity: Pixel-level match between original and generated
2. Structural Integrity: Do major features (silhouette, edges) remain?
3. Recognizability: Can a human identify what the original image was?
"""

from dataclasses import dataclass
from typing import Tuple
from enum import Enum
import numpy as np
from PIL import Image


class Recognizability(Enum):
    """How recognizable is the original image in the nonogram."""

    HIGH = "high"  # Clearly identifiable (80%+)
    MEDIUM = "medium"  # Somewhat recognizable (50-80%)
    LOW = "low"  # Hard to identify (< 50%)


@dataclass
class QualityMetrics:
    """Metrics for image-to-nonogram quality.

    Attributes:
        visual_similarity: 0.0-1.0, pixel-level match ratio
        silhouette_match: 0.0-1.0, edge/outline preservation
        density_match: 0.0-1.0, filled-cell density similarity
        recognizability: HIGH/MEDIUM/LOW based on combined metrics
        quality_score: 1-100 combined quality score
    """

    visual_similarity: float  # 0.0-1.0
    silhouette_match: float  # 0.0-1.0
    density_match: float  # 0.0-1.0
    recognizability: Recognizability
    quality_score: int  # 1-100

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "visual_similarity": round(self.visual_similarity, 3),
            "silhouette_match": round(self.silhouette_match, 3),
            "density_match": round(self.density_match, 3),
            "recognizability": self.recognizability.value,
            "quality_score": self.quality_score,
        }


def _image_to_binary(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to binary numpy array (0 or 1).

    Args:
        image: PIL Image (any mode)

    Returns:
        Binary numpy array (dtype=uint8, values 0 or 1)
        Black pixels (value 0) → 1 (filled)
        White pixels (value 255) → 0 (empty)
    """
    # Convert to grayscale if needed
    if image.mode != "L":
        image = image.convert("L")

    # Convert to numpy array
    img_array = np.array(image, dtype=np.uint8)

    # Threshold at 127: dark pixels (≤127) become 1, light pixels (>127) become 0
    binary = (img_array <= 127).astype(np.uint8)

    return binary


def _grid_to_binary(grid: list) -> np.ndarray:
    """Convert nonogram grid (list of lists of bool) to binary numpy array.

    Args:
        grid: List[List[bool]] where True = filled, False = empty

    Returns:
        Binary numpy array (dtype=uint8, values 0 or 1)
    """
    return np.array(grid, dtype=np.uint8)


def _resize_to_match(image_array: np.ndarray, grid_array: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Resize image to match grid dimensions for comparison.

    Args:
        image_array: Original image as binary array
        grid_array: Generated grid as binary array

    Returns:
        Tuple of (resized_image, grid) both same size
    """
    image_h, image_w = image_array.shape
    grid_h, grid_w = grid_array.shape

    if (image_h, image_w) == (grid_h, grid_w):
        return image_array, grid_array

    # Resize image to match grid dimensions using nearest-neighbor
    # Convert binary (0/1) to grayscale (0/255) for resizing
    image_grayscale = (image_array * 255).astype(np.uint8)
    image_pil = Image.fromarray(image_grayscale)
    resized_pil = image_pil.resize((grid_w, grid_h), Image.NEAREST)

    # Convert back to binary by thresholding
    resized_array = np.array(resized_pil, dtype=np.uint8)
    resized_binary = (resized_array <= 127).astype(np.uint8)

    return resized_binary, grid_array


def calculate_visual_similarity(
    original_image: Image.Image, puzzle_grid: list
) -> float:
    """Calculate pixel-level similarity between image and grid.

    Compares original image (converted to binary) with the generated
    nonogram grid cell by cell.

    Args:
        original_image: PIL Image (any mode)
        puzzle_grid: List[List[bool]] nonogram grid

    Returns:
        Similarity ratio 0.0 (no match) to 1.0 (perfect match)
    """
    image_array = _image_to_binary(original_image)
    grid_array = _grid_to_binary(puzzle_grid)

    # Resize image to match grid
    image_resized, grid = _resize_to_match(image_array, grid_array)

    # Calculate pixel-level match
    matches = np.sum(image_resized == grid)
    total = image_resized.size

    similarity = matches / total if total > 0 else 0.0
    return float(similarity)


def calculate_silhouette_match(
    original_image: Image.Image, puzzle_grid: list
) -> float:
    """Calculate edge/outline preservation.

    Detects edges in both image and grid, then compares.
    High edge match indicates silhouette is preserved.

    Args:
        original_image: PIL Image
        puzzle_grid: List[List[bool]] nonogram grid

    Returns:
        Edge match ratio 0.0-1.0
    """
    image_array = _image_to_binary(original_image)
    grid_array = _grid_to_binary(puzzle_grid)

    # Resize to match
    image_resized, grid = _resize_to_match(image_array, grid_array)

    # Detect edges using simple Sobel-like approach (4-connectivity)
    def get_edge_pixels(arr: np.ndarray) -> np.ndarray:
        """Get pixels that are adjacent to opposite value."""
        edge = np.zeros_like(arr, dtype=bool)
        h, w = arr.shape

        for i in range(h):
            for j in range(w):
                # Check 4 neighbors
                neighbors = []
                if i > 0:
                    neighbors.append(arr[i - 1, j])
                if i < h - 1:
                    neighbors.append(arr[i + 1, j])
                if j > 0:
                    neighbors.append(arr[i, j - 1])
                if j < w - 1:
                    neighbors.append(arr[i, j + 1])

                # Edge if has different valued neighbor
                if neighbors and any(n != arr[i, j] for n in neighbors):
                    edge[i, j] = True

        return edge

    image_edges = get_edge_pixels(image_resized)
    grid_edges = get_edge_pixels(grid)

    # Calculate edge overlap
    both_edge = np.logical_and(image_edges, grid_edges).sum()
    either_edge = np.logical_or(image_edges, grid_edges).sum()

    if either_edge == 0:
        # No edges detected (solid image)
        return 1.0

    silhouette = both_edge / either_edge
    return float(silhouette)


def calculate_density_match(
    original_image: Image.Image, puzzle_grid: list
) -> float:
    """Calculate filled-cell density similarity.

    Compares the proportion of filled cells between image and grid.

    Args:
        original_image: PIL Image
        puzzle_grid: List[List[bool]] nonogram grid

    Returns:
        Density match ratio 0.0-1.0
    """
    image_array = _image_to_binary(original_image)
    grid_array = _grid_to_binary(puzzle_grid)

    # Resize to match
    image_resized, grid = _resize_to_match(image_array, grid_array)

    # Calculate fill ratios
    image_fill = np.sum(image_resized) / image_resized.size
    grid_fill = np.sum(grid) / grid.size

    # How close are the densities? (0 = very different, 1 = identical)
    density_diff = abs(image_fill - grid_fill)
    density_match = 1.0 - density_diff

    return float(density_match)


def measure_quality(
    original_image: Image.Image, puzzle_grid: list
) -> QualityMetrics:
    """Measure overall quality of image-to-nonogram conversion.

    Combines three metrics into a single quality score and recognizability.

    Args:
        original_image: Original image (PIL Image)
        puzzle_grid: Generated nonogram grid (List[List[bool]])

    Returns:
        QualityMetrics with score, recognizability, and component breakdowns
    """
    # Calculate components
    visual_sim = calculate_visual_similarity(original_image, puzzle_grid)
    silhouette = calculate_silhouette_match(original_image, puzzle_grid)
    density = calculate_density_match(original_image, puzzle_grid)

    # Weighted combination (adjust weights based on importance)
    # Visual similarity is most important, silhouette next, then density
    quality_score_0_1 = (visual_sim * 0.5) + (silhouette * 0.35) + (density * 0.15)

    # Convert to 1-100 scale
    quality_score = int(round(quality_score_0_1 * 100))
    quality_score = max(1, min(100, quality_score))  # Clamp 1-100

    # Determine recognizability tier
    if quality_score >= 80:
        recognizability = Recognizability.HIGH
    elif quality_score >= 50:
        recognizability = Recognizability.MEDIUM
    else:
        recognizability = Recognizability.LOW

    return QualityMetrics(
        visual_similarity=visual_sim,
        silhouette_match=silhouette,
        density_match=density,
        recognizability=recognizability,
        quality_score=quality_score,
    )


if __name__ == "__main__":
    # Example usage
    # Create a simple test image (black square on white background)
    test_image = Image.new("L", (10, 10), 255)
    for i in range(3, 7):
        for j in range(3, 7):
            test_image.putpixel((i, j), 0)

    # Create matching grid
    grid = [[False] * 10 for _ in range(10)]
    for i in range(3, 7):
        for j in range(3, 7):
            grid[i][j] = True

    metrics = measure_quality(test_image, grid)
    print(f"Quality Score: {metrics.quality_score}/100")
    print(f"Recognizability: {metrics.recognizability.value}")
    print(f"Visual Similarity: {metrics.visual_similarity:.2%}")
    print(f"Silhouette Match: {metrics.silhouette_match:.2%}")
    print(f"Density Match: {metrics.density_match:.2%}")
