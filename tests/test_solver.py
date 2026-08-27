"""COMP-005 tests: solution counting with fail-fast uniqueness (FR-006).

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-015  TestSolver_ReportsUniqueSolution      -> test_reports_unique_solution*
    AC-016  TestSolver_ReportsUnsolvable          -> test_reports_unsolvable*
    AC-017  TestSolver_FailsFastOnSecondSolution  -> test_fails_fast_on_second_solution*

EC-001/CON-005 — the property that the uniqueness verdict is never a false
positive — lives in ``tests/property/test_solver_uniqueness.py``, where it is
checked over thousands of generated clue sets against ADR-0014's brute-force
oracle. This file covers the three named acceptance criteria, the ADR-0012
bitmask/boundary seam, the FR-009 signal hooks, and the oracle itself.

Every puzzle here is small enough to verify by hand from the docstring that
draws it, and the ones that are not obvious are additionally pinned by
``brute_force_oracle.count_solutions_by_cell``, which enumerates every
``2 ** (n * n)`` grid and so cannot be wrong for the same reason the solver
might be.
"""

from __future__ import annotations

import random

import pytest

from nonogram.clues import compute_clues, encode_line
from nonogram.solver import MANY, SolveResult, solve
from nonogram.solver.propagate import canonical_clue, line_intersection, mask_runs
from tests.helpers.brute_force_oracle import (
    count_solutions,
    count_solutions_by_cell,
    line_candidates,
)

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_clues.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"
_EMPTY = "·"


def _line(pattern: str) -> list[bool]:
    assert set(pattern) <= {_FILLED, _EMPTY}, f"bad pattern glyph in {pattern!r}"
    return [glyph == _FILLED for glyph in pattern]


def _grid(*patterns: str) -> list[list[bool]]:
    return [_line(pattern) for pattern in patterns]


def _mask(pattern: str) -> int:
    """The bitmask of a pattern, bit ``i`` for cell ``i`` (ADR-0012)."""
    return sum(1 << index for index, glyph in enumerate(pattern) if glyph == _FILLED)


#: A plus sign. Every non-central row and column has a single filled cell, and
#: the full middle line already accounts for it, so nothing else can be filled:
#: unique, and solvable by line logic alone.
#:
#:     ··█··
#:     ··█··
#:     █████
#:     ··█··
#:     ··█··
PLUS = _grid("··█··", "··█··", "█████", "··█··", "··█··")

#: A 6x6 that line logic cannot finish — the solver has to guess, backtrack,
#: and still come back with exactly one solution. Taken from the property
#: corpus, pinned here because "unique after branching" is a distinct code
#: path from "unique by propagation".
BRANCHING_ROWS = ((1, 1), (0,), (2, 1), (1,), (1, 1), (1, 1))
BRANCHING_COLUMNS = ((2,), (1, 1, 1), (1, 1), (1, 1), (1,), (0,))


# --------------------------------------------------------------------------
# AC-015 — a clue set with exactly one solution
# --------------------------------------------------------------------------


def test_reports_unique_solution() -> None:
    """AC-015: one valid solution -> ``solution_count = 1`` and that grid.

    The plus sign above, whose clues are ``(1,) (1,) (5,) (1,) (1,)`` in both
    directions. Returning *a* grid is not enough: it has to be the grid the
    clues came from, since a solver that answers "unique" with the wrong grid
    is wrong twice over.
    """
    rows, columns = compute_clues(PLUS)

    result = solve(rows, columns)

    assert result.solution_count == 1
    assert result.solution == PLUS
    assert result.is_unique


def test_reports_unique_solution_that_needs_backtracking() -> None:
    """AC-015 again, on a puzzle line logic alone cannot finish.

    Propagation stalls here, so the answer comes out of the branch-and-
    backtrack half of the search. Both halves have to be able to produce a
    ``solution_count = 1``, and only this one exercises the second.
    """
    result = solve(BRANCHING_ROWS, BRANCHING_COLUMNS)

    assert result.solution_count == 1
    assert result.signals.branch_nodes > 0, "expected this puzzle to need a guess"
    assert result.solution is not None
    derived = compute_clues(result.solution)
    assert (derived.rows, derived.columns) == (BRANCHING_ROWS, BRANCHING_COLUMNS)


def test_reports_unique_solution_for_an_all_empty_grid() -> None:
    """AC-013's ``(0,)`` marker is a clue like any other, and it is unique.

    The degenerate end of FR-004's density range (0%) has to come back as a
    solvable puzzle rather than as an error or an empty-count, because
    CARD-005's loop judges it on uniqueness like everything else.
    """
    empty = _grid("···", "···", "···")
    rows, columns = compute_clues(empty)
    assert rows == ((0,), (0,), (0,))

    result = solve(rows, columns)

    assert result.solution_count == 1
    assert result.solution == empty


def test_reports_unique_solution_for_an_all_filled_grid() -> None:
    """The other degenerate end (100% density), for the same reason."""
    filled = _grid("███", "███", "███")

    result = solve(*compute_clues(filled))

    assert result.solution_count == 1
    assert result.solution == filled


def test_solution_grid_is_not_transposed() -> None:
    """The ADR-0012 seam: bit order and orientation, on an asymmetric grid.

    ADR-0012 flags the bitmask/boundary conversion as where an off-by-one or a
    bit-order slip would live, and a square, symmetric example would hide a
    transposition entirely. This grid is deliberately neither.
    """
    grid = _grid("█··██", "··█··", "███··", "····█")
    rows, columns = compute_clues(grid)
    assert rows == ((1, 2), (1,), (3,), (1,))

    result = solve(rows, columns)

    assert result.solution_count == 1
    assert result.solution == grid


# --------------------------------------------------------------------------
# AC-016 — a clue set with no solution
# --------------------------------------------------------------------------


def test_reports_unsolvable() -> None:
    """AC-016: contradictory clues -> ``solution_count = 0``, no grid.

    A run of 3 cannot be laid out in a 2-cell row. The filled totals agree
    (3 = 2 + 1), so this is not caught by a cheap accounting check — the line
    logic has to notice that the row admits no placement at all.
    """
    result = solve(((3,), (0,)), ((2,), (1,)))

    assert result.solution_count == 0
    assert result.solution is None
    assert not result.is_unique


def test_reports_unsolvable_when_the_filled_totals_disagree() -> None:
    """AC-016: rows claiming 5 filled cells and columns claiming 2.

    The other shape of contradiction: every individual line is placeable, but
    no grid can satisfy both directions because they do not even agree on how
    many cells are filled.
    """
    result = solve(((5,), (0,)), ((1,), (1,), (0,), (0,), (0,)))

    assert result.solution_count == 0
    assert result.solution is None


def test_reports_unsolvable_only_after_searching() -> None:
    """AC-016: a contradiction no amount of line logic can see.

    Every line here is individually placeable and propagation reaches a fixed
    point without complaint; the emptiness is only provable by trying the
    remaining possibilities and running out. ``count_solutions_by_cell``
    enumerates all 65,536 4x4 grids to confirm there really are none, so this
    test cannot be made to pass by a solver that gives up too early.
    """
    rows = ((1,), (1,), (1, 1), (1, 1))
    columns = ((1,), (2,), (2,), (1,))
    assert count_solutions_by_cell(rows, columns) == 0

    result = solve(rows, columns)

    assert result.solution_count == 0
    assert result.solution is None
    assert result.signals.backtracks > 0, "expected the verdict to require search"


def test_malformed_clues_raise_rather_than_reporting_unsolvable() -> None:
    """A negative run is a bug at the call site, not a hard puzzle.

    Reporting ``solution_count = 0`` for it would hide the defect behind a
    perfectly plausible domain answer — and, since CARD-005 reacts to a 0 by
    generating another grid, would turn a typo into an infinite retry loop.
    """
    with pytest.raises(ValueError, match="positive ints"):
        solve(((-1,), (0,)), ((0,), (0,)))
    with pytest.raises(ValueError, match="positive ints"):
        solve(((1, 0), (0,)), ((1,), (0,)))


# --------------------------------------------------------------------------
# AC-017 — more than one solution, without enumerating them
# --------------------------------------------------------------------------


def test_fails_fast_on_second_solution() -> None:
    """AC-017: stop at the second distinct solution, do not enumerate.

    Every row and every column of this 12x12 has the clue ``(1,)``, so its
    solutions are the 12x12 permutation matrices — 12! = 479,001,600 of them.
    Any solver that enumerated even a noticeable fraction would not return
    this side of a week; returning promptly, having visited a couple of dozen
    branch nodes, is what "fails fast" means operationally.
    """
    size = 12
    clue_set = tuple((1,) for _ in range(size))

    result = solve(clue_set, clue_set)

    assert result.solution_count == MANY
    assert result.signals.branch_nodes < 200, (
        f"visited {result.signals.branch_nodes} branch nodes for a clue set "
        f"with 479,001,600 solutions — that is not fail-fast"
    )
    assert result.signals.elapsed_seconds < 1.0


def test_reports_two_for_the_smallest_ambiguous_puzzle() -> None:
    """AC-017 at the boundary: exactly two solutions, reported as ``MANY``.

    The 2x2 with one filled cell per row and per column — the two diagonals.
    ``MANY`` reads as ">= 2"; nothing in the API distinguishes two solutions
    from two million, and nothing downstream needs it to.
    """
    rows = columns = ((1,), (1,))
    assert count_solutions_by_cell(rows, columns) == 2

    result = solve(rows, columns)

    assert result.solution_count == MANY


def test_the_returned_grid_for_an_ambiguous_puzzle_is_still_a_solution() -> None:
    """A witness, not "the" solution — but it must at least be one of them.

    ``SolveResult.solution`` is documented as the first solution found when
    the count is ``MANY``. Callers gated on uniqueness must not use it, but it
    must not be junk either: a returned grid always matches the clues.
    """
    rows = columns = ((1,), (1,))

    result = solve(rows, columns)

    assert result.solution is not None
    derived = compute_clues(result.solution)
    assert (derived.rows, derived.columns) == (rows, columns)


# --------------------------------------------------------------------------
# FR-009 signal hooks (emitted here, scored in CARD-009)
# --------------------------------------------------------------------------


def test_signals_report_full_line_logic_coverage_when_no_guess_is_needed() -> None:
    """ADR-0013's easiest-end case: everything solved before the first branch.

    AC-023 requires a puzzle solved entirely by line logic with no
    backtracking to score at the easy extreme. That is CARD-009's arithmetic,
    but it can only be right if the solver reports the inputs this way.
    """
    result = solve(*compute_clues(PLUS))

    signals = result.signals
    assert signals.total_cells == 25
    assert signals.line_logic_cells == 25
    assert signals.branch_nodes == 0
    assert signals.backtracks == 0
    assert signals.elapsed_seconds >= 0.0


def test_signals_report_partial_line_logic_coverage_when_guessing_is_needed() -> None:
    """The other side: a stalled fixed point leaves cells for the search.

    ``line_logic_cells`` counts what propagation settled *before the first
    guess*, so it must be strictly less than the grid when the solver had to
    branch — otherwise CARD-009 would score every puzzle as trivially easy.
    """
    result = solve(BRANCHING_ROWS, BRANCHING_COLUMNS)

    signals = result.signals
    assert signals.total_cells == 36
    assert signals.line_logic_cells < signals.total_cells
    assert signals.branch_nodes >= 1


def test_signals_are_reported_even_when_there_is_no_solution() -> None:
    """An unsolvable candidate still has to say how much work it cost.

    CARD-005 discards these, but ADR-0011's deadline and NFR-001's timing are
    measured across every attempt, not only the successful ones.
    """
    result = solve(((3,), (0,)), ((2,), (1,)))

    assert result.signals.total_cells == 4
    assert result.signals.elapsed_seconds >= 0.0


# --------------------------------------------------------------------------
# Purity (ADR-0007 / guardrail G-2)
# --------------------------------------------------------------------------


def test_solving_the_same_clues_twice_gives_the_same_answer() -> None:
    """No module-level state: two calls cannot influence each other.

    Everything but the wall-clock signal is compared, which is the whole
    observable surface of a pure function. If a cache or a counter ever
    appeared at module level, an ambiguous puzzle solved twice is where it
    would show.
    """
    rows = columns = ((1,), (1,))

    first, second = solve(rows, columns), solve(rows, columns)

    assert _comparable(first) == _comparable(second)


def _comparable(result: SolveResult) -> tuple[object, ...]:
    """Everything about a result except the wall clock."""
    signals = result.signals
    return (
        result.solution_count,
        result.solution,
        signals.line_logic_cells,
        signals.total_cells,
        signals.branch_nodes,
        signals.backtracks,
    )


def test_solving_does_not_mutate_the_clues_it_was_given() -> None:
    """The clue set is shared with the scorer and the exporters (ADR-0012)."""
    rows = ((1, 1), (0,), (2,))
    columns = ((1, 1), (1,), (1,))
    before = (rows, columns)

    solve(rows, columns)

    assert (rows, columns) == before


# --------------------------------------------------------------------------
# Line logic: the bitmask primitives (ADR-0012)
# --------------------------------------------------------------------------


def test_line_intersection_deduces_the_overlap() -> None:
    """The classic overlap: a run of 4 in a 5-cell line pins the middle three.

    Leftmost placement covers cells 0-3, rightmost covers 1-4, so cells 1, 2
    and 3 are filled in every placement while 0 and 4 are decided by neither.
    Two placements, and nothing is known to be empty.
    """
    filled, empty, placements = line_intersection((4,), 5, 0, 0)

    assert filled == _mask("·███·")
    assert empty == 0
    assert placements == 2


def test_line_intersection_uses_what_is_already_known() -> None:
    """Knowing one cell is empty collapses the same line to one placement."""
    filled, empty, placements = line_intersection((4,), 5, 0, _mask("█····"))

    assert placements == 1
    assert filled == _mask("·████")
    assert empty == _mask("█····")


def test_line_intersection_reports_a_contradiction() -> None:
    """No placement survives -> ``None``, the search's cue to backtrack."""
    assert line_intersection((4,), 5, 0, _mask("··█··")) is None
    assert line_intersection((3,), 2, 0, 0) is None
    assert line_intersection((), 3, _mask("·█·"), 0) is None


def test_line_intersection_handles_the_empty_clue() -> None:
    """An empty line has exactly one placement: every cell empty (AC-013)."""
    filled, empty, placements = line_intersection(canonical_clue((0,)), 4, 0, 0)

    assert (filled, empty, placements) == (0, _mask("████"), 1)


def test_line_intersection_confirms_a_fully_decided_line() -> None:
    """The completed-line shortcut agrees with the general DP, both ways."""
    known_filled = _mask("██·█·")
    known_empty = _mask("··█·█")

    assert line_intersection((2, 1), 5, known_filled, known_empty) == (
        known_filled,
        known_empty,
        1,
    )
    assert line_intersection((3,), 5, known_filled, known_empty) is None


def test_line_intersection_agrees_with_exhaustive_enumeration() -> None:
    """The DP against brute force, over every line up to 10 cells.

    The DP never materialises a placement, so nothing about it is obvious by
    inspection. Enumerating every pattern of the line, filtering to those
    consistent with what is known, and intersecting them by hand is obvious —
    and the two must agree on the deduced cells and on the placement count,
    for every clue and every partial state sampled here.
    """
    rng = random.Random(31415)
    checked = 0
    for length in range(1, 11):
        patterns = line_candidates_by_length(length)
        for _ in range(40):
            clue = encode_line(rng.choice(patterns))
            known_filled, known_empty = _random_knowledge(rng, length)

            expected = [
                pattern
                for pattern in patterns
                if _mask_of(pattern) & known_empty == 0
                and ~_mask_of(pattern) & known_filled == 0
                and encode_line(pattern) == clue
            ]
            deduced = line_intersection(
                canonical_clue(clue), length, known_filled, known_empty
            )
            checked += 1

            if not expected:
                assert deduced is None, f"clue={clue} length={length}"
                continue
            assert deduced is not None, f"clue={clue} length={length}"
            filled, empty, placements = deduced
            assert placements == len(expected)
            all_filled = _mask("")
            for index in range(length):
                bit = 1 << index
                if all(_mask_of(pattern) & bit for pattern in expected):
                    all_filled |= bit
            all_empty = sum(
                1 << index
                for index in range(length)
                if all(not _mask_of(pattern) & (1 << index) for pattern in expected)
            )
            assert (filled, empty) == (all_filled, all_empty), (
                f"clue={clue} length={length} known={known_filled:b}/{known_empty:b}"
            )
    assert checked == 400


def line_candidates_by_length(length: int) -> list[tuple[bool, ...]]:
    """Every pattern of ``length`` cells, as tuples of bools."""
    return [
        tuple(bool((bits >> index) & 1) for index in range(length))
        for bits in range(1 << length)
    ]


def _mask_of(pattern: tuple[bool, ...]) -> int:
    return sum(1 << index for index, cell in enumerate(pattern) if cell)


def _random_knowledge(rng: random.Random, length: int) -> tuple[int, int]:
    """A random consistent partial state: each cell filled, empty or unknown."""
    known_filled = known_empty = 0
    for index in range(length):
        roll = rng.random()
        if roll < 0.2:
            known_filled |= 1 << index
        elif roll < 0.4:
            known_empty |= 1 << index
    return known_filled, known_empty


def test_mask_runs_agrees_with_the_clue_module() -> None:
    """The solver's finished-line encoder vs CARD-002's, over every 8-bit line.

    ``mask_runs`` is the CON-005 self-check's other half, and it is native to
    the solver because ADR-0007 forbids importing ``clues`` laterally. That
    makes it a reimplementation, so it is pinned against the original here —
    from the test tree, where the import is allowed — for all 256 lines of
    length 8, including the empty one (``()`` on this side of the boundary,
    ``(0,)`` on the clue module's).
    """
    for bits in range(1 << 8):
        line = [bool((bits >> index) & 1) for index in range(8)]
        expected = encode_line(line)
        assert mask_runs(bits, 8) == canonical_clue(expected)


# --------------------------------------------------------------------------
# Bounded larger-grid round-trip (ADR-0014, direction 2)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("size", [10, 20, 30])
def test_finds_the_source_grid_at_production_sizes(size: int) -> None:
    """A grid's own clues are solvable, at sizes the property corpus omits.

    ADR-0014's free-direction check asks for this all the way to 50x50. It is
    bounded here — three seeded grids at 75% density, all solved by line logic
    in milliseconds — because ADR-0011's cooperative deadline is CARD-006's
    work (guardrail G-5), and until it exists an unlucky mid-density grid at
    these sizes would hang the suite rather than fail it. The card's worktree
    notes carry the measurements behind that choice.
    """
    rng = random.Random(4242 + size)
    grid = [[rng.random() < 0.75 for _ in range(size)] for _ in range(size)]

    result = solve(*compute_clues(grid))

    assert result.solution_count >= 1
    if result.is_unique:
        assert result.solution == grid


# --------------------------------------------------------------------------
# The oracle itself (ADR-0014) — an unverified oracle is just a second guess
# --------------------------------------------------------------------------


def test_the_two_oracles_agree() -> None:
    """Line-candidate enumeration vs enumerating all ``2 ** (n * n)`` grids.

    The property test leans on ``count_solutions``, which prunes by column
    prefix; ``count_solutions_by_cell`` prunes nothing whatsoever. They are
    compared here on every grid size the slow one can bear (up to 16 cells),
    so a pruning bug in the fast oracle cannot silently agree with a matching
    bug in the solver.
    """
    rng = random.Random(2718)
    for _ in range(24):
        size = rng.choice((2, 3, 4))
        grid = [
            [rng.random() < rng.choice((0.2, 0.5, 0.8)) for _ in range(size)]
            for _ in range(size)
        ]
        rows, columns = compute_clues(grid)

        assert count_solutions(rows, columns) == count_solutions_by_cell(rows, columns)


def test_the_oracle_counts_a_known_ambiguous_puzzle_exactly() -> None:
    """Sanity anchor: the 3x3 with one filled cell per line has 6 solutions.

    The 3x3 permutation matrices, 3! = 6 — a number that can be checked
    without trusting either implementation.
    """
    rows = columns = ((1,), (1,), (1,))

    assert count_solutions(rows, columns) == 6
    assert count_solutions_by_cell(rows, columns) == 6
    assert count_solutions(rows, columns, limit=MANY) == MANY


def test_the_oracle_enumerates_every_line_matching_a_clue() -> None:
    """``line_candidates`` is the oracle's ground truth; check it by hand.

    A clue of ``(1, 1)`` in four cells has exactly three layouts, and a clue
    that cannot fit has none. Compared as a set: the enumeration order is the
    helper's own business, the completeness of the set is not.
    """
    assert set(line_candidates((1, 1), 4)) == {
        (True, False, True, False),
        (True, False, False, True),
        (False, True, False, True),
    }
    assert len(line_candidates((1, 1), 4)) == 3
    assert line_candidates((0,), 3) == [(False, False, False)]
    assert line_candidates((4,), 3) == []
