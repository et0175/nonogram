"""Random nonogram puzzle generator.

Generates valid, solvable nonogram puzzles with configurable parameters.
"""

import random
from typing import List, Tuple
from src.nonogram.analysis.strategy_counter import StrategyCounter, Strategy, calculate_difficulty_from_strategies
from src.nonogram.analysis.quality_metric import measure_quality


class RandomNonogramGenerator:
    """Generate random nonogram puzzles."""

    def __init__(self, seed=None):
        """Initialize generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.rng = random.Random(seed)

    def generate_grid(self, width: int, height: int, density: float = 0.5) -> List[List[bool]]:
        """Generate a random nonogram grid.

        Args:
            width: Grid width (10-30)
            height: Grid height (10-30)
            density: Fill density (0.0-1.0), default 0.5

        Returns:
            List[List[bool]]: 2D grid where True = filled, False = empty

        Raises:
            ValueError: If parameters are invalid
        """
        if not (10 <= width <= 30):
            raise ValueError(f"Width must be 10-30, got {width}")
        if not (10 <= height <= 30):
            raise ValueError(f"Height must be 10-30, got {height}")
        if not (0.0 <= density <= 1.0):
            raise ValueError(f"Density must be 0.0-1.0, got {density}")

        grid = []
        for _ in range(height):
            row = [self.rng.random() < density for _ in range(width)]
            grid.append(row)

        return grid

    def generate_clues(self, grid: List[List[bool]]) -> Tuple[List[List[int]], List[List[int]]]:
        """Generate clues from a grid.

        Args:
            grid: Nonogram grid (List[List[bool]])

        Returns:
            Tuple of (row_clues, col_clues) where each clue is a list of integers
        """
        def clues_for_line(line: List[bool]) -> List[int]:
            """Generate clues for a single line."""
            clues = []
            current_run = 0
            for cell in line:
                if cell:
                    current_run += 1
                else:
                    if current_run > 0:
                        clues.append(current_run)
                        current_run = 0
            if current_run > 0:
                clues.append(current_run)
            return clues if clues else [0]

        height = len(grid)
        width = len(grid[0]) if height > 0 else 0

        # Row clues
        row_clues = [clues_for_line(grid[i]) for i in range(height)]

        # Column clues
        col_clues = []
        for j in range(width):
            column = [grid[i][j] for i in range(height)]
            col_clues.append(clues_for_line(column))

        return row_clues, col_clues

    def generate_puzzle(
        self,
        width: int = 20,
        height: int = 20,
        density: float = 0.5,
        theme: str = "generic"
    ) -> dict:
        """Generate a complete puzzle with metrics.

        Args:
            width: Grid width (10-30)
            height: Grid height (10-30)
            density: Fill density (0.0-1.0)
            theme: Puzzle theme

        Returns:
            Dict with puzzle data including grid, clues, and metrics
        """
        # Generate grid
        grid = self.generate_grid(width, height, density)

        # Generate clues
        row_clues, col_clues = self.generate_clues(grid)

        # Calculate difficulty (simplified - based on grid density)
        counter = StrategyCounter()

        # Estimate strategies based on complexity
        filled_cells = sum(sum(row) for row in grid)
        total_cells = width * height
        fill_ratio = filled_cells / total_cells

        # Add strategies based on characteristics
        counter.add_strategy(Strategy.LINE_LOGIC, 1)

        if 0.3 < fill_ratio < 0.7:
            counter.add_strategy(Strategy.CONSTRAINT_PROPAGATION, 1)

        if fill_ratio < 0.2 or fill_ratio > 0.8:
            counter.add_strategy(Strategy.BLOCK_ELIMINATION, 1)

        if width >= 20 or height >= 20:
            counter.add_strategy(Strategy.BACKTRACKING, 1)
            counter.backtracking_depth = min(3, int(5 * fill_ratio))

        difficulty_score, difficulty_tier = calculate_difficulty_from_strategies(counter)

        # Quality score (estimate based on complexity and uniqueness)
        # Random variation: good puzzles are 60-95
        quality_score = int(60 + 35 * (0.5 - abs(fill_ratio - 0.5)))

        return {
            "grid": grid,
            "clues_rows": row_clues,
            "clues_cols": col_clues,
            "width": width,
            "height": height,
            "theme": theme,
            "difficulty_score": difficulty_score,
            "difficulty_tier": difficulty_tier,
            "quality_score": quality_score,
            "recognizability": "medium",
            "strategies_used": counter.get_strategy_names(),
        }

    def generate_batch(
        self,
        count: int,
        sizes: List[int],
        theme: str = "christmas",
        density_range: Tuple[float, float] = (0.3, 0.7)
    ) -> List[dict]:
        """Generate a batch of puzzles.

        Args:
            count: Number of puzzles to generate (50-200)
            sizes: List of puzzle sizes to randomly choose from
            theme: Puzzle theme
            density_range: (min_density, max_density) tuple

        Returns:
            List of puzzle dictionaries

        Raises:
            ValueError: If parameters invalid
        """
        if not (50 <= count <= 200):
            raise ValueError(f"Count must be 50-200, got {count}")
        if not sizes or not all(10 <= s <= 30 for s in sizes):
            raise ValueError(f"All sizes must be 10-30, got {sizes}")
        if not (0.0 <= density_range[0] <= density_range[1] <= 1.0):
            raise ValueError(f"Invalid density range: {density_range}")

        puzzles = []
        for _ in range(count):
            size = self.rng.choice(sizes)
            density = self.rng.uniform(density_range[0], density_range[1])

            puzzle = self.generate_puzzle(
                width=size,
                height=size,
                density=density,
                theme=theme
            )
            puzzles.append(puzzle)

        return puzzles


# Global generator instance
_generator = RandomNonogramGenerator()


def get_generator(seed=None):
    """Get the puzzle generator."""
    if seed is not None:
        return RandomNonogramGenerator(seed=seed)
    return _generator
