"""Tests for random nonogram generator."""

import pytest
from src.nonogram.generation import RandomNonogramGenerator, get_generator


@pytest.fixture
def generator():
    """Get a fresh generator for testing."""
    return RandomNonogramGenerator(seed=42)


class TestGridGeneration:
    """Test random grid generation."""

    def test_generate_grid_valid(self, generator):
        """Generate a valid grid."""
        grid = generator.generate_grid(10, 10, density=0.5)

        assert len(grid) == 10
        assert all(len(row) == 10 for row in grid)
        assert all(isinstance(cell, bool) for row in grid for cell in row)

    def test_generate_grid_different_sizes(self, generator):
        """Generate grids of different sizes."""
        for size in [10, 15, 20, 25, 30]:
            grid = generator.generate_grid(size, size, 0.5)
            assert len(grid) == size
            assert all(len(row) == size for row in grid)

    def test_generate_grid_density_respected(self, generator):
        """Verify density parameter affects output."""
        # Low density - fewer filled cells
        grid_sparse = generator.generate_grid(20, 20, density=0.2)
        sparse_fill = sum(sum(row) for row in grid_sparse) / 400

        # High density - more filled cells
        generator2 = RandomNonogramGenerator(seed=43)
        grid_dense = generator2.generate_grid(20, 20, density=0.8)
        dense_fill = sum(sum(row) for row in grid_dense) / 400

        assert sparse_fill < dense_fill

    def test_generate_grid_invalid_size(self, generator):
        """Reject invalid sizes."""
        with pytest.raises(ValueError):
            generator.generate_grid(5, 10)  # Too small

        with pytest.raises(ValueError):
            generator.generate_grid(50, 10)  # Too large

    def test_generate_grid_invalid_density(self, generator):
        """Reject invalid density."""
        with pytest.raises(ValueError):
            generator.generate_grid(10, 10, density=-0.1)

        with pytest.raises(ValueError):
            generator.generate_grid(10, 10, density=1.5)


class TestClueGeneration:
    """Test clue generation from grids."""

    def test_generate_clues_simple(self, generator):
        """Generate clues from a simple grid."""
        # Simple grid: all filled top row, empty bottom row
        grid = [
            [True, True, True, False],
            [False, False, False, False],
        ]

        row_clues, col_clues = generator.generate_clues(grid)

        assert row_clues[0] == [3]
        assert row_clues[1] == [0]
        assert col_clues[0] == [1]
        assert col_clues[1] == [1]
        assert col_clues[2] == [1]
        assert col_clues[3] == [0]

    def test_generate_clues_complex(self, generator):
        """Generate clues from a complex grid."""
        # Grid: 1 1 pattern
        grid = [
            [True, False, True],
            [False, False, False],
        ]

        row_clues, col_clues = generator.generate_clues(grid)

        assert row_clues[0] == [1, 1]
        assert row_clues[1] == [0]

    def test_generate_clues_from_random_grid(self, generator):
        """Generate clues from a random grid."""
        grid = generator.generate_grid(15, 15, density=0.5)
        row_clues, col_clues = generator.generate_clues(grid)

        assert len(row_clues) == 15
        assert len(col_clues) == 15
        assert all(all(isinstance(c, int) for c in clue) for clue in row_clues)
        assert all(all(isinstance(c, int) for c in clue) for clue in col_clues)


class TestPuzzleGeneration:
    """Test complete puzzle generation."""

    def test_generate_puzzle(self, generator):
        """Generate a complete puzzle."""
        puzzle = generator.generate_puzzle(20, 20, theme="christmas")

        assert "grid" in puzzle
        assert "clues_rows" in puzzle
        assert "clues_cols" in puzzle
        assert "width" in puzzle
        assert "height" in puzzle
        assert "theme" in puzzle
        assert "difficulty_score" in puzzle
        assert "difficulty_tier" in puzzle
        assert "quality_score" in puzzle

        assert puzzle["width"] == 20
        assert puzzle["height"] == 20
        assert puzzle["theme"] == "christmas"
        assert 1 <= puzzle["difficulty_score"] <= 100
        assert puzzle["difficulty_tier"] in ["Easy", "Medium", "Hard"]
        assert 1 <= puzzle["quality_score"] <= 100

    def test_generate_puzzle_default_params(self, generator):
        """Generate puzzle with default parameters."""
        puzzle = generator.generate_puzzle()

        assert puzzle["width"] == 20
        assert puzzle["height"] == 20
        assert puzzle["theme"] == "generic"

    def test_generate_puzzle_different_themes(self, generator):
        """Generate puzzles with different themes."""
        for theme in ["christmas", "halloween", "easter", "valentine"]:
            puzzle = generator.generate_puzzle(theme=theme)
            assert puzzle["theme"] == theme

    def test_puzzle_has_valid_clues(self, generator):
        """Generated puzzle has valid clues."""
        puzzle = generator.generate_puzzle(15, 15)

        assert len(puzzle["clues_rows"]) == 15
        assert len(puzzle["clues_cols"]) == 15


class TestBatchGeneration:
    """Test batch puzzle generation."""

    def test_generate_batch(self, generator):
        """Generate a batch of puzzles."""
        puzzles = generator.generate_batch(count=50, sizes=[15, 20])

        assert len(puzzles) == 50
        assert all("grid" in p and "clues_rows" in p for p in puzzles)

    def test_generate_batch_sizes_respected(self, generator):
        """Batch puzzles use specified sizes."""
        puzzles = generator.generate_batch(count=50, sizes=[10, 20, 30])

        sizes = {p["width"] for p in puzzles}
        assert sizes.issubset({10, 20, 30})

    def test_generate_batch_theme_respected(self, generator):
        """Batch puzzles have specified theme."""
        puzzles = generator.generate_batch(count=50, sizes=[20], theme="halloween")

        assert all(p["theme"] == "halloween" for p in puzzles)

    def test_generate_batch_invalid_count(self, generator):
        """Reject invalid batch count."""
        with pytest.raises(ValueError):
            generator.generate_batch(count=30, sizes=[20])  # Too small

        with pytest.raises(ValueError):
            generator.generate_batch(count=250, sizes=[20])  # Too large

    def test_generate_batch_invalid_sizes(self, generator):
        """Reject invalid sizes in batch."""
        with pytest.raises(ValueError):
            generator.generate_batch(count=100, sizes=[5, 50])


class TestReproducibility:
    """Test reproducibility with seeds."""

    def test_generator_seeded_is_reproducible(self):
        """Seeded generator produces same puzzles."""
        gen1 = RandomNonogramGenerator(seed=12345)
        gen2 = RandomNonogramGenerator(seed=12345)

        puzzle1 = gen1.generate_puzzle()
        puzzle2 = gen2.generate_puzzle()

        assert puzzle1["grid"] == puzzle2["grid"]
        assert puzzle1["clues_rows"] == puzzle2["clues_rows"]

    def test_batch_seeded_is_reproducible(self):
        """Seeded batch generation is reproducible."""
        gen1 = RandomNonogramGenerator(seed=54321)
        gen2 = RandomNonogramGenerator(seed=54321)

        batch1 = gen1.generate_batch(count=50, sizes=[15])
        batch2 = gen2.generate_batch(count=50, sizes=[15])

        for p1, p2 in zip(batch1, batch2):
            assert p1["grid"] == p2["grid"]


class TestSingleton:
    """Test singleton pattern."""

    def test_get_generator_singleton(self):
        """get_generator returns singleton."""
        gen1 = get_generator()
        gen2 = get_generator()

        assert gen1 is gen2

    def test_get_generator_with_seed_creates_new(self):
        """get_generator with seed creates new instance."""
        gen1 = get_generator()
        gen2 = get_generator(seed=42)

        assert gen1 is not gen2
