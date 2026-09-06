"""Tests for image quality metrics."""

import pytest
from PIL import Image
import numpy as np
from src.nonogram.analysis.quality_metric import (
    Recognizability,
    QualityMetrics,
    calculate_visual_similarity,
    calculate_silhouette_match,
    calculate_density_match,
    measure_quality,
    _image_to_binary,
    _grid_to_binary,
)


@pytest.fixture
def perfect_match_image():
    """Create a simple test image (black square on white)."""
    img = Image.new("L", (10, 10), 255)  # White background
    for i in range(3, 7):
        for j in range(3, 7):
            img.putpixel((i, j), 0)  # Black square in middle
    return img


@pytest.fixture
def perfect_match_grid():
    """Create grid that matches perfect_match_image."""
    grid = [[False] * 10 for _ in range(10)]
    for i in range(3, 7):
        for j in range(3, 7):
            grid[i][j] = True
    return grid


@pytest.fixture
def inverted_grid():
    """Create grid opposite of perfect_match_image."""
    grid = [[True] * 10 for _ in range(10)]
    for i in range(3, 7):
        for j in range(3, 7):
            grid[i][j] = False
    return grid


class TestImageConversion:
    """Test image/grid conversion utilities."""

    def test_image_to_binary_grayscale(self):
        """Convert grayscale image to binary."""
        img = Image.new("L", (5, 5), 255)
        img.putpixel((1, 1), 0)  # Black pixel

        binary = _image_to_binary(img)

        assert binary.shape == (5, 5)
        assert binary[1, 1] == 1  # Black pixel becomes 1
        assert binary[0, 0] == 0  # White pixels become 0

    def test_image_to_binary_rgb(self):
        """Convert RGB image to binary."""
        img = Image.new("RGB", (5, 5), (255, 255, 255))

        binary = _image_to_binary(img)

        assert binary.shape == (5, 5)
        assert binary.dtype == np.uint8

    def test_grid_to_binary(self):
        """Convert grid to binary array."""
        grid = [[True, False], [False, True]]

        binary = _grid_to_binary(grid)

        assert binary.shape == (2, 2)
        assert binary[0, 0] == 1
        assert binary[0, 1] == 0


class TestVisualSimilarity:
    """Test visual similarity calculation."""

    def test_perfect_match(self, perfect_match_image, perfect_match_grid):
        """Perfect image-grid match = 1.0 similarity."""
        similarity = calculate_visual_similarity(perfect_match_image, perfect_match_grid)

        assert similarity == 1.0

    def test_complete_inversion(self, perfect_match_image, inverted_grid):
        """Completely inverted grid = 0.0 similarity."""
        similarity = calculate_visual_similarity(perfect_match_image, inverted_grid)

        assert similarity == 0.0

    def test_partial_match(self, perfect_match_image):
        """Partially matching grid = intermediate similarity."""
        # Grid with only half the black pixels (8 instead of 16)
        # But the 8 filled cells overlap perfectly with original
        grid = [[False] * 10 for _ in range(10)]
        for i in range(3, 7):
            for j in range(3, 5):  # Only first 2 cols
                grid[i][j] = True

        similarity = calculate_visual_similarity(perfect_match_image, grid)

        assert 0.0 < similarity < 1.0
        # 8 overlapping filled + 84 overlapping empty = 92/100
        assert 0.85 < similarity < 0.95

    def test_resize_to_match_dimensions(self):
        """Small image should be resized to match grid."""
        # Small image
        small_img = Image.new("L", (5, 5), 255)
        for i in range(2, 4):
            for j in range(2, 4):
                small_img.putpixel((i, j), 0)

        # Larger grid
        grid = [[False] * 10 for _ in range(10)]
        for i in range(4, 8):
            for j in range(4, 8):
                grid[i][j] = True

        # Should not crash, should resize
        similarity = calculate_visual_similarity(small_img, grid)

        assert 0.0 <= similarity <= 1.0


class TestSilhouetteMatch:
    """Test edge/outline preservation."""

    def test_perfect_silhouette(self, perfect_match_image, perfect_match_grid):
        """Perfect match = high silhouette match."""
        silhouette = calculate_silhouette_match(perfect_match_image, perfect_match_grid)

        assert silhouette == 1.0

    def test_silhouette_with_noise(self, perfect_match_image):
        """Grid with same outline but noise in fill."""
        grid = [[False] * 10 for _ in range(10)]
        for i in range(3, 7):
            for j in range(3, 7):
                grid[i][j] = True

        # Add random noise inside
        import random

        random.seed(42)
        for _ in range(5):
            i, j = random.randint(3, 6), random.randint(3, 6)
            grid[i][j] = False

        silhouette = calculate_silhouette_match(perfect_match_image, grid)

        # Silhouette should still be high (outline preserved)
        assert silhouette > 0.7


class TestDensityMatch:
    """Test filled-cell density similarity."""

    def test_perfect_density(self, perfect_match_image, perfect_match_grid):
        """Perfect match = 1.0 density match."""
        density = calculate_density_match(perfect_match_image, perfect_match_grid)

        assert density == 1.0

    def test_opposite_density(self, perfect_match_image, inverted_grid):
        """Inverted grid = very low density match."""
        density = calculate_density_match(perfect_match_image, inverted_grid)

        # 16 pixels filled vs 84 pixels filled (opposite)
        assert density < 0.5

    def test_half_density(self, perfect_match_image):
        """Grid with 2x the filled cells = low density match."""
        grid = [[True] * 10 for _ in range(10)]
        for i in range(5, 10):
            for j in range(5, 10):
                grid[i][j] = False

        density = calculate_density_match(perfect_match_image, grid)

        assert 0.0 < density < 0.5


class TestQualityMeasurement:
    """Test overall quality measurement."""

    def test_perfect_quality(self, perfect_match_image, perfect_match_grid):
        """Perfect match = high quality score."""
        metrics = measure_quality(perfect_match_image, perfect_match_grid)

        assert metrics.quality_score == 100
        assert metrics.recognizability == Recognizability.HIGH
        assert metrics.visual_similarity == 1.0
        assert metrics.silhouette_match == 1.0
        assert metrics.density_match == 1.0

    def test_poor_quality(self, perfect_match_image, inverted_grid):
        """Inverted grid = low quality score."""
        metrics = measure_quality(perfect_match_image, inverted_grid)

        assert metrics.quality_score < 50
        assert metrics.recognizability == Recognizability.LOW

    def test_quality_score_range(self, perfect_match_image, perfect_match_grid):
        """Quality score is always 1-100."""
        # Create various mismatch grids
        test_grids = [
            [[False] * 10 for _ in range(10)],  # All empty
            [[True] * 10 for _ in range(10)],  # All filled
            perfect_match_grid,  # Perfect
        ]

        for grid in test_grids:
            metrics = measure_quality(perfect_match_image, grid)
            assert 1 <= metrics.quality_score <= 100

    def test_recognizability_tiers(self, perfect_match_image):
        """Test recognizability classification."""
        # High quality: nearly perfect match
        grid_high = [[False] * 10 for _ in range(10)]
        for i in range(3, 7):
            for j in range(3, 7):
                grid_high[i][j] = True
        metrics_high = measure_quality(perfect_match_image, grid_high)
        assert metrics_high.recognizability == Recognizability.HIGH

        # Low quality: inverted
        grid_low = [[True] * 10 for _ in range(10)]
        for i in range(3, 7):
            for j in range(3, 7):
                grid_low[i][j] = False
        metrics_low = measure_quality(perfect_match_image, grid_low)
        assert metrics_low.recognizability == Recognizability.LOW

    def test_to_dict_serialization(self, perfect_match_image, perfect_match_grid):
        """Test conversion to dictionary."""
        metrics = measure_quality(perfect_match_image, perfect_match_grid)
        d = metrics.to_dict()

        assert "visual_similarity" in d
        assert "silhouette_match" in d
        assert "density_match" in d
        assert "recognizability" in d
        assert "quality_score" in d

        assert d["quality_score"] == 100
        assert d["recognizability"] == "high"
