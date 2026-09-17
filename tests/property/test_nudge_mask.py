"""EC-014 — the nudge's cells come from the solver, and the attempts nest.

    EC-014  PropertyTest_Nudge_FlippedCellsSubsetOfUndecidedMaskAndNested
            -> test_flipped_cells_come_from_the_solver_and_nest

EC-014, in full: for any conversion the solver reports ``MANY`` for, and any
attempt *n* in 1..:data:`MAX_NUDGE_ATTEMPTS` that adds a cell, the set of cells
attempt *n* flips has exactly one more member than attempt *n − 1*'s, contains
every cell attempt *n − 1* flipped, and its new cell belongs to the
witness-disagreement set of attempt *n − 1*'s candidate — or, when that set
holds no unflipped cell, to that candidate's undecided mask. The grid attempt
*n* judges differs from the **original** conversion in exactly those cells.

It is a statement about every ambiguous grid rather than about a chosen one,
which is why it lives here and not in ``tests/test_nudge.py``, where FR-013's
individual criteria are pinned on two hand-built conversions and one
photograph.

The corpus, house style (no ``hypothesis`` — it is not in the dependency
baseline): seeded random grids across the supported extents, kept only when the
**real** solver reports ``MANY`` for them, with the case counts asserted inside
each test so the corpus cannot silently shrink to nothing and leave a green
test behind. Nothing about the choice is faked — every witness pair and
undecided mask below is COMP-005's own report on the grid the previous attempt
was judged on, obtained by re-solving that grid's clues from scratch.

Why random grids stand in for conversions
-----------------------------------------
EC-014 is a property of the *mechanism*, and the mechanism sees a grid and a
solver verdict — it cannot tell a dithered photograph from a random draw, and
:func:`nonogram.sourcing.image.next_nudge_cell` has no access to the file. A
seeded random corpus is therefore the same input distribution as far as the
constraint is concerned, and it reaches ambiguous grids far more cheaply than
decoding pictures does. CARD-096's corpus sweep over the owner's 25 real
pictures is the complement to this, and lives in ``meta/ops/`` rather than in
the suite: it measures how often the mechanism *succeeds*, which is a number to
report rather than a property to assert.

The fallback half is built rather than found
--------------------------------------------
A ``MANY`` verdict always has two witnesses, so the disagreement set is never
empty on the first attempt and a found corpus exercises the undecided-mask
fallback only by luck. The second test scripts it directly — a mask, a witness
pair whose disagreement is already spent — so the branch is covered on purpose
rather than incidentally (the same reasoning ``repair_candidate``'s fallback is
tested under in ``tests/property/test_recovery_bound.py``).

Where a claim can be re-derived it is re-derived here: the disagreement set is
computed from the solver's two witnesses by the small function below, not by
calling the module under test's private helper.
"""

from __future__ import annotations

import random

import pytest

from nonogram import clues, solver
from nonogram.orchestrator import MAX_NUDGE_ATTEMPTS
from nonogram.sourcing import image

Grid = list[list[bool]]
Cell = tuple[int, int]

#: Extents and densities the corpus draws from. Both sides of the supported
#: range are represented but the extents stay small deliberately: EC-014 is a
#: property of the *choice*, which does not know how big the grid is, while the
#: cost of finding an ambiguous grid is a **solve**, and random mid-density
#: grids at 20x20 and above are the solver's known-hard class (COMP-005's
#: docstring). Spending the suite's seconds there would buy no case the smaller
#: extents do not already cover.
_EXTENTS = ((10, 10), (12, 12), (10, 14), (15, 15), (16, 12))
_DENSITIES = (25, 35, 45, 55, 65)
_SEEDS = range(12)

#: Asserted inside the tests, not merely produced: a corpus that stopped
#: finding ambiguous grids would otherwise leave a vacuous green behind. Taken
#: at about two thirds of what the settings above actually yield today (192
#: grids, 738 attempts), so ordinary drift in the solver or the draw does not
#: turn this into a flake while a real collapse still fails it.
_MINIMUM_AMBIGUOUS_GRIDS = 120
_MINIMUM_ATTEMPTS = 480


def _draw(width: int, height: int, density: int, rng: random.Random) -> Grid:
    """A grid with exactly ``density``% of its cells filled, shuffled."""
    total = width * height
    filled = round(total * density / 100)
    cells = [True] * filled + [False] * (total - filled)
    rng.shuffle(cells)
    return [cells[row * width : (row + 1) * width] for row in range(height)]


def _verdict(grid: Grid) -> solver.SolveResult:
    """COMP-005's report on ``grid``'s own clues — never a stand-in."""
    grid_clues = clues.compute_clues(grid)
    return solver.solve(grid_clues.rows, grid_clues.columns)


def _disagreeing(witnesses: tuple[Grid, ...] | None) -> set[Cell]:
    """Where the two witnesses differ — the test tree's own second walk."""
    if witnesses is None or len(witnesses) < 2:
        return set()
    first, second = witnesses[0], witnesses[1]
    return {
        (row, column)
        for row, (first_row, second_row) in enumerate(zip(first, second, strict=True))
        for column, (left, right) in enumerate(zip(first_row, second_row, strict=True))
        if left != right
    }


def _set_cells(mask: list[list[bool]] | None) -> set[Cell]:
    """The set cells of a grid-shaped mask."""
    if not mask:
        return set()
    return {
        (row, column)
        for row, mask_row in enumerate(mask)
        for column, cell in enumerate(mask_row)
        if cell
    }


def _differences(left: Grid, right: Grid) -> set[Cell]:
    """Every cell where two same-shaped grids disagree."""
    return {
        (row, column)
        for row, (left_row, right_row) in enumerate(zip(left, right, strict=True))
        for column, (a, b) in enumerate(zip(left_row, right_row, strict=True))
        if a != b
    }


def _ambiguous_corpus() -> list[Grid]:
    """Seeded grids the real solver reports ``MANY`` for."""
    corpus: list[Grid] = []
    for seed in _SEEDS:
        rng = random.Random(seed)
        for width, height in _EXTENTS:
            for density in _DENSITIES:
                grid = _draw(width, height, density, rng)
                if _verdict(grid).solution_count == solver.MANY:
                    corpus.append(grid)
    return corpus


@pytest.fixture(scope="module")
def ambiguous_grids() -> list[Grid]:
    return _ambiguous_corpus()


def test_the_corpus_is_large_enough_to_mean_something(
    ambiguous_grids: list[Grid],
) -> None:
    """The corpus guard, stated separately so a shrunken corpus fails with its
    own name rather than as a confusing failure inside the property."""
    assert len(ambiguous_grids) >= _MINIMUM_AMBIGUOUS_GRIDS


def test_flipped_cells_come_from_the_solver_and_nest(
    ambiguous_grids: list[Grid],
) -> None:
    """EC-014, over the whole corpus, one attempt at a time.

    The loop COMP-002 runs, replayed here so that every intermediate state is
    visible: at each attempt the previous candidate is re-solved from scratch,
    its disagreement set and undecided mask are re-derived from that verdict,
    and the cell the mechanism adds is checked against them before it is
    applied. Four things are asserted per attempt — the new cell's source, the
    strict nesting, the exact size, and that the grid judged differs from the
    **original** conversion in precisely the flipped set.
    """
    attempts_checked = 0

    for original in ambiguous_grids:
        flipped: list[Cell] = []
        judged = original
        verdict = _verdict(original)

        for _ in range(MAX_NUDGE_ATTEMPTS):
            disagreeing = _disagreeing(verdict.witnesses)
            mask = _set_cells(verdict.undecided_mask)
            previous = set(flipped)

            cell = image.next_nudge_cell(
                judged,
                flipped,
                witnesses=verdict.witnesses,
                undecided_mask=verdict.undecided_mask,
            )
            if cell is None:
                # Nothing left to add. The loop's counter still advances, but
                # there is no flipped set to make a claim about.
                assert not (disagreeing - previous) and not (mask - previous)
                break

            # The cell's source: the disagreement set, or the mask exactly when
            # the disagreement set holds nothing unflipped.
            if disagreeing - previous:
                assert cell in disagreeing - previous
            else:
                assert cell in mask - previous

            flipped.append(cell)
            judged = image.nudge(original, flipped)
            attempts_checked += 1

            # Nesting, and the exact size.
            assert previous < set(flipped)
            assert len(set(flipped)) == len(previous) + 1
            assert len(flipped) == len(set(flipped))

            # The grid this attempt judges differs from the ORIGINAL conversion
            # in exactly the flipped set — never from the previous attempt's.
            assert _differences(original, judged) == set(flipped)

            verdict = _verdict(judged)
            if verdict.solution_count == 1:
                break

    assert attempts_checked >= _MINIMUM_ATTEMPTS


def test_the_mask_fallback_is_used_exactly_when_the_disagreement_is_spent() -> None:
    """The fallback half of EC-014, scripted so it cannot be reached by luck.

    A ``MANY`` verdict always has two witnesses, so a found corpus meets the
    fallback only when a run happens to exhaust a disagreement set before the
    cap. Here the disagreement is one cell wide by construction: attempt 1 must
    take it, and attempt 2 must come from the mask.
    """
    grid = [[False] * 8 for _ in range(8)]
    for row in range(2, 5):
        for column in range(2, 5):
            grid[row][column] = True
    witnesses = ([row[:] for row in grid], [row[:] for row in grid])
    witnesses[1][6][6] = True
    mask = [[False] * 8 for _ in range(8)]
    for cell in ((0, 0), (1, 1), (6, 6)):
        mask[cell[0]][cell[1]] = True

    first = image.next_nudge_cell(
        grid, (), witnesses=witnesses, undecided_mask=mask
    )
    assert first == (6, 6)

    second = image.next_nudge_cell(
        grid, [first], witnesses=witnesses, undecided_mask=mask
    )
    assert second in {(0, 0), (1, 1)}
    assert second != first

    third = image.next_nudge_cell(
        grid, [first, second], witnesses=witnesses, undecided_mask=mask
    )
    assert third not in {first, second}

    exhausted = image.next_nudge_cell(
        grid, [first, second, third], witnesses=witnesses, undecided_mask=mask
    )
    assert exhausted is None
