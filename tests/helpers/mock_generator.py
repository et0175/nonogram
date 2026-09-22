"""``MockGenerator`` — a cheap generator that still produces real puzzles.

Moved here from ``src/nonogram/admin/puzzle_review.py`` by CARD-055
(2026-09-22), **unchanged**: same draws, same seed behaviour, same output. It
was never instantiated by any production route — its callers are this test
tree — but it sat in ``src/`` under a name that reads as a legitimate generator
option beside ``orchestrator.generate_batch``, one mistaken import away from
writing invented ``quality_score``/``recognizability`` values into a real
batch. CARD-080 had already flagged the location while fixing what the class
invented; this card is that leftover.

It still invents two fields — ``quality_score`` and ``recognizability`` are
drawn at random. That is deliberate and now unremarkable: in the test tree an
arbitrary fixture value is a fixture value. Making them honest (``None``, as
CARD-050 decided for random mode) is a separate question, filed rather than
bolted onto the move — see CARD-055's Worktree notes.

Everything else it produces is real, per CARD-080: the grid is resampled until
the solver certifies exactly one solution, the clues come from
``clues.compute_clues`` on that grid, and the grade comes from that same solve
through the real scorer and classifier.
"""

import math
import random
import time

from nonogram.admin.puzzle_review import PuzzleReviewService
from nonogram.clues import compute_clues
from nonogram.difficulty import classify, score_difficulty
from nonogram.errors import NotUniquelySolvable, SolverTimeout
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS
from nonogram.solver import solve


class MockGenerator:
    """A cheap generator for tests and demos that still produces real puzzles.

    "Mock" is historical and now means only *cheap* — it does not call the
    orchestrator, so it skips naming, the retry policies and the image path.
    What it no longer skips is the one thing that makes a grid a puzzle.

    Until CARD-080 it emitted a random 50%-density grid, clue lists of random
    integers **unrelated to that grid**, and a random ``difficulty_score`` and
    tier. Almost none of its output was uniquely solvable, and 29 tests fed it
    to :meth:`PuzzleReviewService.add_puzzle` — so the suite's picture of "a
    stored puzzle" was a non-puzzle with invented clues and an invented grade.
    That is the same defect as ``image_to_puzzle.create_puzzle_from_image``,
    the function that wrote the twenty rows deleted on 2026-09-14, and it was
    still shipping in ``src/`` after that one was removed.

    Three things changed, all of them "ask, don't invent":

    * the clues come from :func:`nonogram.clues.compute_clues` on the grid it
      actually produced (CARD-051's one encoder), so grid and clues agree;
    * the grid is resampled until the solver certifies exactly one solution
      (CON-005), so its output passes the storage guard because it deserves to
      and not because the guard was relaxed;
    * the grade comes from that same solve through the real scorer and
      classifier (ADR-0029, ADR-0025/R2), so no second grading implementation
      lives here either.

    Density is 0.65 rather than 0.5 deliberately. Uniqueness is not uniform in
    density — measured over 20 grids per cell, a random grid is uniquely
    solvable 0/20 at density 0.2 and 0.35, 2-12/20 at 0.5, and 17-18/20 at
    0.65, for sizes 10 to 20. Sparse grids are the hard ones: the structural
    tension that makes a sparse grid uniquely solvable is the same tension that
    makes it hard to find. At 0.65 the loop below almost always succeeds on its
    first or second draw, at a few milliseconds a solve.

    **Every puzzle this emits is Easy, and that is structural rather than a
    tuning choice.** Measured over 25 puzzles at sizes 10/15/20: all Easy, all
    scoring exactly 33. Widening the band does not move it — 0.55-0.75 and
    0.5-0.8 both give the same answer — because a dense random grid that *is*
    uniquely solvable is exactly the kind line logic settles on the bottom rung
    with share 1.0, which pins the score at the Easy band's top edge. So a test
    that needs a second tier cannot get one from here: pin a grid the way
    ``tests/test_admin_regrade.py``'s ``GUESS_GRID`` is pinned — seeded search,
    literal cells, premise asserted against the solver — or it will pass
    without ever exercising the tier it claims to (CARD-080 review, F-004).
    """

    #: Fill density. A measured choice, not a default — see the class
    #: docstring; lowering it makes the resample loop expensive fast.
    DENSITY = 0.65

    #: How many grids to draw before giving up on one puzzle. Generous: the
    #: expected number of draws at DENSITY is under two, so reaching this bound
    #: means something about the solver or the extent has changed, and saying so
    #: loudly beats returning a grid nobody checked.
    MAX_DRAWS = 40

    def __init__(self, seed=None):
        """Initialize the generator. ``seed`` makes a run reproducible."""
        import random
        self.rng = random.Random(seed)

    def generate_batch(self, count, sizes, theme='christmas'):
        """Generate a batch of puzzles, every one of them uniquely solvable.

        Args:
            count: Number of puzzles to generate
            sizes: List of grid sizes as int or (width, height) tuples
                  Examples: [15, 20] or [(20, 20), (36, 20)]
            theme: Theme name

        Returns:
            List of puzzle dicts, in the shape ``add_puzzle`` takes.

        Raises:
            NotUniquelySolvable: no uniquely solvable grid was found for an
                extent within :attr:`MAX_DRAWS` draws. Raised rather than
                returning the last draw: a caller that asked for a puzzle and
                silently got a non-puzzle is the failure this card is about.
        """
        puzzles = []

        for i in range(count):
            size_spec = self.rng.choice(sizes) if sizes else 15

            # Handle both int and (width, height) tuple formats
            if isinstance(size_spec, (tuple, list)):
                width, height = size_spec
            else:
                width = height = size_spec

            grid, clues_rows, clues_cols, score, tier, strategies = (
                self._draw_until_unique(width, height)
            )

            puzzle = {
                'grid': grid,
                'clues_rows': clues_rows,
                'clues_cols': clues_cols,
                'width': width,
                'height': height,
                'theme': theme,
                'difficulty_score': score,
                'difficulty_tier': tier,
                'quality_score': self.rng.randint(1, 100),
                'recognizability': self.rng.choice(['low', 'medium', 'high']),
                'strategies_used': strategies,
            }
            puzzles.append(puzzle)

        return puzzles

    def _draw_until_unique(self, width, height):
        """Draw grids at :attr:`DENSITY` until the solver certifies one.

        The solve that certifies the grid is the solve its grade comes from —
        one solver entry per puzzle, the rule ADR-0029/R2 states for the real
        pipeline and which there is no reason to break here.
        """
        for _ in range(self.MAX_DRAWS):
            grid = [
                [self.rng.random() < self.DENSITY for _ in range(width)]
                for _ in range(height)
            ]
            row_clues, column_clues = compute_clues(grid)
            try:
                result = solve(
                    row_clues,
                    column_clues,
                    deadline=time.monotonic() + GENERATION_BUDGET_SECONDS,
                )
            except SolverTimeout:
                continue
            if result.solution_count != 1:
                continue

            score = score_difficulty(result.signals)
            tier = classify(score)
            return (
                grid,
                [list(run) for run in row_clues],
                [list(run) for run in column_clues],
                math.ceil(score),
                tier.value,
                # FR-029, off the same certifying solve as the grade beside it
                # (CARD-072). Before this the dict below carried a hardcoded
                # ``['LineLogic', 'ConstraintProp']`` — names this system's
                # solver has never produced, stored in the same column the
                # real pipeline writes, where nothing downstream could tell
                # them apart. Borrowed from ``PuzzleReviewService`` rather than
                # copied: one rule for appending ``guess`` (ADR-0025/R2), and
                # a demo generator is not a reason to acquire a second.
                PuzzleReviewService._strategies_of(result),
            )

        raise NotUniquelySolvable(
            f"no uniquely solvable {width}x{height} grid in {self.MAX_DRAWS} draws "
            f"at density {self.DENSITY}; returning an unchecked grid is what "
            "CARD-080 exists to prevent"
        )
