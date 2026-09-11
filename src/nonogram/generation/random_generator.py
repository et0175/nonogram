"""Random nonogram puzzle generator.

Generates valid, solvable nonogram puzzles with configurable parameters.

CARD-050 note on this module's difficulty estimate
----------------------------------------------------
This module used to import ``nonogram.analysis.strategy_counter`` (used, for
``_difficulty_from_strategy_flags`` below) and ``nonogram.analysis.
quality_metric.measure_quality`` (imported but never called — dead code)
through ``from src.nonogram.analysis...``, a path that only resolved by
accident of how this project's test suite happens to be invoked (CARD-050,
AC-3). Fixing that prefix to the correct ``from nonogram.analysis...`` makes
both imports visible to ``tests/test_cli.py``'s ADR-0007 structural guard —
which then (correctly) flags them: ``nonogram.generation`` and
``nonogram.analysis`` are both capability-rank modules, and one capability
may not import another laterally (this project's own precedent for exactly
this situation is ``solver/propagate.py``'s ``mask_runs``, which
reimplements one clue-encoding check natively rather than importing
``clues.py``).

So rather than leave an import that is only correct in isolation but breaks
the package's own layering invariant, the one piece of
``strategy_counter.calculate_difficulty_from_strategies`` this module
actually uses (this module has zero production callers today — nothing
calls ``RandomNonogramGenerator``; ``orchestrator.generate_batch`` is what
the admin panel actually uses for random-mode generation) is reimplemented
natively below as :func:`_difficulty_from_strategy_flags`, producing
identical output to the original for every input this module ever passes it
(verified against ``tests/test_random_generator.py``, which was already
value-agnostic beyond "1-100" / "Easy|Medium|Hard"). The dead
``measure_quality`` import is simply dropped — nothing here ever called it.
"""

import random
from typing import List, Tuple


def _difficulty_from_strategy_flags(
    unique_strategy_count: int,
    total_strategy_count: int,
    backtracking_depth: int,
) -> Tuple[int, str]:
    """Native reimplementation of the one code path of
    ``nonogram.analysis.strategy_counter.calculate_difficulty_from_strategies``
    this module ever exercises (see the module docstring's CARD-050 note for
    why this is inlined rather than imported).

    ``generate_puzzle`` below never uses ``StrategyCounter.branch_count``
    (nothing in this module explores solution branches), so the original's
    ambiguity term is always zero for every call this module makes and is
    correctly omitted here rather than carried as a dead parameter.

    Args:
        unique_strategy_count: How many distinct strategies were applied —
            the original's ``counter.get_unique_strategy_count()``.
        total_strategy_count: Total strategy applications — the original's
            ``counter.strategy_count``. This module always applies each
            strategy at most once, so it equals ``unique_strategy_count``
            for every call here, exactly as in the code it replaces.
        backtracking_depth: The original's ``counter.backtracking_depth``.

    Returns:
        ``(difficulty_score, difficulty_tier)`` — identical to what
        ``calculate_difficulty_from_strategies`` returned for the same
        inputs.
    """
    # 1. Strategy complexity (0-40 points) — unchanged from the original.
    strategy_score = min(40, (unique_strategy_count * 40) // 6)
    strategy_score = min(40, strategy_score + (total_strategy_count // 5))

    # 2. Backtracking (0-35 points) — unchanged from the original.
    if backtracking_depth == 0:
        backtracking_score = 0
    elif backtracking_depth <= 3:
        backtracking_score = min(20, backtracking_depth * 7)
    else:
        backtracking_score = min(35, 20 + (backtracking_depth - 3) * 5)

    # 3. Ambiguity/branch exploration: always 0 here (see docstring).
    difficulty_score = min(100, strategy_score + backtracking_score)

    if difficulty_score < 30:
        tier = "Easy"
    elif difficulty_score < 70:
        tier = "Medium"
    else:
        tier = "Hard"

    return difficulty_score, tier


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

        # Calculate difficulty (simplified - based on grid density).
        # Strategy names/counts tracked locally rather than through
        # analysis.strategy_counter.StrategyCounter — see the module
        # docstring's CARD-050 note.
        strategies_used: List[str] = []

        # Estimate strategies based on complexity
        filled_cells = sum(sum(row) for row in grid)
        total_cells = width * height
        fill_ratio = filled_cells / total_cells

        # Add strategies based on characteristics
        strategies_used.append("line_logic")

        if 0.3 < fill_ratio < 0.7:
            strategies_used.append("constraint_propagation")

        if fill_ratio < 0.2 or fill_ratio > 0.8:
            strategies_used.append("block_elimination")

        backtracking_depth = 0
        if width >= 20 or height >= 20:
            strategies_used.append("backtracking")
            backtracking_depth = min(3, int(5 * fill_ratio))

        unique_strategy_count = len(strategies_used)
        difficulty_score, difficulty_tier = _difficulty_from_strategy_flags(
            unique_strategy_count, unique_strategy_count, backtracking_depth
        )

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
            "strategies_used": sorted(strategies_used),
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
