"""COMP-005 tests: the undecided mask, the second witness, the rung tags.

CARD-073's three additions to the solver's result, none of which changes a
verdict. AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-107  TestSolver_ReportsSecondWitnessWhenMany
            -> test_reports_a_second_witness_when_many
    AC-131  TestSolver_BothWitnessesReencodeToInputClues
            -> test_both_witnesses_reencode_to_the_input_clues
    AC-108  TestSolver_UndecidedMaskListsCellsLeftAtFirstFixedPoint
            -> test_undecided_mask_lists_the_cells_left_at_the_first_fixed_point
    AC-109  TestSolver_UndecidedMaskIsEmptyForLineSolvablePuzzle
            -> test_undecided_mask_is_empty_for_a_line_solvable_puzzle
    AC-110  TestSolver_NoWitnessWhenUnsolvable
            -> test_no_witness_when_unsolvable
    AC-A    TestSolver_LineSolvableSetTagsEveryCellWithoutProbeContradiction
            -> test_a_line_solvable_set_tags_every_cell_without_probe_contradiction
    EC-012  TestSolver_ResultFieldsUnchangedForExistingCallers
            -> test_result_fields_are_unchanged_for_existing_callers
    ADR-0029/R2  TestSolver_RungTagsComputedInsideTheOneSolve
            -> test_rung_tags_are_computed_inside_the_one_solve

AC-B ("verdicts identical") has no test of its own here by construction: it is
``tests/test_solver.py`` and ``tests/property/test_solver_uniqueness.py``
passing *unedited*, which is guardrail G-1 and is checked by running them.

EC-011 — that the witnesses always disagree only inside the mask — is a
property over a seeded corpus and lives in
``tests/property/test_solver_witnesses.py``, next to EC-001's.

The overlap rule ``simple_overlap`` is defined against
(``propagate.overlap_masks``) is checked here too, against an independent
enumeration of every placement of the line rather than against itself: the
house rule is a second implementation, not a second call.
"""

from __future__ import annotations

import random

import pytest

from nonogram import difficulty
from nonogram.clues import compute_clues
from nonogram.orchestrator import Puzzle, GenerationRequest
from nonogram.solver import (
    MANY,
    RUNG_CROSS_LINE,
    RUNG_LINE_DP,
    RUNG_ORDER,
    RUNG_PROBE_CONTRADICTION,
    RUNG_SIMPLE_OVERLAP,
    SolveResult,
    solve,
)
from nonogram.solver import search as search_module
from nonogram.solver.propagate import (
    Board,
    LineCache,
    canonical_clue,
    overlap_masks,
)
from tests.helpers.brute_force_oracle import line_candidates

# --------------------------------------------------------------------------
# Fixtures — same notation as tests/test_solver.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"
_EMPTY = "·"


def _grid(*patterns: str) -> list[list[bool]]:
    for pattern in patterns:
        assert set(pattern) <= {_FILLED, _EMPTY}, f"bad pattern glyph in {pattern!r}"
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


def _from_ascii(*rows: str) -> list[list[bool]]:
    """A grid drawn with ``#`` and ``.`` — for the two large recorded fixtures."""
    return [[glyph == "#" for glyph in row] for row in rows]


#: AC-107/AC-108's puzzle: a 10x10 whose only ambiguity is one 2x2 switching
#: block in the top-left corner.
#:
#: Two filled cells on the leading diagonal of that corner and nothing else::
#:
#:     █·········        ·█········
#:     ·█········   or   █·········
#:     ··········        ··········
#:          :                 :
#:
#: Both grids encode to the *same* clues — every one of rows 0, 1 and columns
#: 0, 1 holds a single filled cell either way, and every other line is empty —
#: so the clue set has exactly two solutions that differ in exactly the four
#: cells of the block. Line logic settles the eight empty lines and then stalls:
#: row 0's clue ``(1,)`` admits a placement in column 0 and one in column 1, and
#: no cell is filled in both, which is precisely why those four cells are what
#: the first fixed point leaves open.
SWITCH_BLOCK = _grid(
    "█·········",
    "·█········",
    "··········",
    "··········",
    "··········",
    "··········",
    "··········",
    "··········",
    "··········",
    "··········",
)

#: The four cells of that block, as ``(row, column)``.
SWITCH_CELLS = frozenset({(0, 0), (0, 1), (1, 0), (1, 1)})

#: AC-109/AC-A's puzzle: a 15x15 line logic decides completely, with no guess
#: and no probe. Recorded rather than described — it is a dense random grid,
#: picked because a *designed* pattern tends to be settled by the overlap rule
#: alone and would leave ``line_dp`` and ``cross_line`` untested. Its rung mix
#: is asserted in the test that uses it, so a re-grade cannot pass silently.
LINE_SOLVABLE_15 = _from_ascii(
    "#.....##.#.####",
    "####..#.####.##",
    "..#.###.#..####",
    "#######.###.#.#",
    "..#.#####.#...#",
    "##.#...#.###.#.",
    "#######.##.####",
    ".###.##.#..#.##",
    "#.##...##.#####",
    "..#####..#..##.",
    "#.##.##.#######",
    ".#.##..#..#..##",
    "#..##..#.####.#",
    ".##############",
    "#######.#####.#",
)

#: AC-A's other half: a 10x10 whose unique solution the search reaches only by
#: refuting values — a probe rules one value of a cell out, the other is forced,
#: and cells settle that line logic never could. Also recorded: "needs a
#: refutation" is not a property you can draw by hand.
NEEDS_PROBE_10 = _from_ascii(
    ".....####.",
    "##...###..",
    "...#....#.",
    "...#....#.",
    "#.#..#....",
    "..##.#.###",
    ".....##..#",
    "#..#.####.",
    "#...#..#..",
    ".....#.#..",
)

#: AC-110's puzzle: a 4x4 with no solution at all, which line logic cannot see
#: until its first sweep reaches the columns.
#:
#: Rows 2 and 3 are empty, so column 0's clue ``(1, 1)`` — two filled cells with
#: a gap between them — has only rows 0 and 1 left to live in and cannot fit.
#: The row totals and the column totals agree (2 each), so the solver does not
#: take its arithmetic short cut; it propagates, settles the two empty rows, and
#: finds the contradiction with the eight cells of rows 0 and 1 still open.
UNSOLVABLE_ROWS: tuple[tuple[int, ...], ...] = ((1,), (1,), (0,), (0,))
UNSOLVABLE_COLUMNS: tuple[tuple[int, ...], ...] = ((1, 1), (0,), (0,), (0,))


def _disagreements(first: list[list[bool]], second: list[list[bool]]) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row, (left, right) in enumerate(zip(first, second, strict=True))
        for column, (a, b) in enumerate(zip(left, right, strict=True))
        if a != b
    }


def _set_cells(mask: list[list[bool]]) -> set[tuple[int, int]]:
    return {
        (row, column)
        for row, line in enumerate(mask)
        for column, flag in enumerate(line)
        if flag
    }


# --------------------------------------------------------------------------
# AC-107, AC-131 — the second witness
# --------------------------------------------------------------------------


def test_reports_a_second_witness_when_many() -> None:
    """AC-107: MANY carries two witnesses differing in exactly the block.

    *given* the clues of a 10x10 grid containing exactly one 2x2 switching
    block, *when* it is solved, *then* the result reports MANY and carries two
    witness grids that differ in exactly those four cells.
    """
    rows, columns = compute_clues(SWITCH_BLOCK)

    result = solve(rows, columns)

    assert result.solution_count == MANY
    assert result.solution is not None
    assert result.second_witness is not None
    assert result.witnesses == (result.solution, result.second_witness)
    assert _disagreements(result.solution, result.second_witness) == SWITCH_CELLS


def test_both_witnesses_reencode_to_the_input_clues() -> None:
    """AC-131: both witnesses are genuine solutions of the clues given.

    Re-encoded through ``nonogram.clues`` — COMP-004's own encoder, which the
    solver may not import (ADR-0007) and which therefore checks the solver's
    native ``mask_runs`` rather than agreeing with it by construction.
    """
    rows, columns = compute_clues(SWITCH_BLOCK)

    result = solve(rows, columns)

    assert len(result.witnesses) == MANY
    for index, witness in enumerate(result.witnesses):
        encoded = compute_clues(witness)
        assert encoded.rows == rows, f"witness {index} rows"
        assert encoded.columns == columns, f"witness {index} columns"


# --------------------------------------------------------------------------
# AC-108, AC-109, AC-110 — the first-fixed-point undecided mask
# --------------------------------------------------------------------------


def test_undecided_mask_lists_the_cells_left_at_the_first_fixed_point() -> None:
    """AC-108: exactly the switching block is left undecided, nothing else."""
    rows, columns = compute_clues(SWITCH_BLOCK)

    result = solve(rows, columns)

    assert _set_cells(result.undecided_mask) == SWITCH_CELLS
    assert [len(line) for line in result.undecided_mask] == [10] * 10


def test_undecided_mask_is_empty_for_a_line_solvable_puzzle() -> None:
    """AC-109: a 15x15 line logic finishes leaves nothing open and no witness."""
    rows, columns = compute_clues(LINE_SOLVABLE_15)

    result = solve(rows, columns)

    assert result.solution_count == 1
    assert result.signals.branch_nodes == 0
    assert not any(any(line) for line in result.undecided_mask)
    assert [len(line) for line in result.undecided_mask] == [15] * 15
    assert result.second_witness is None
    assert result.witnesses == (result.solution,)


def test_no_witness_when_unsolvable() -> None:
    """AC-110: zero solutions, no witness, and the mask still reported.

    The mask is the point: propagation settled rows 2 and 3 and then hit the
    contradiction, so the eight cells of rows 0 and 1 are what it left open.
    Reporting it on a zero-solution verdict is what lets a caller ask *where*
    the clue set stopped making sense.
    """
    result = solve(UNSOLVABLE_ROWS, UNSOLVABLE_COLUMNS)

    assert result.solution_count == 0
    assert result.solution is None
    assert result.second_witness is None
    assert result.witnesses == ()
    assert _set_cells(result.undecided_mask) == {
        (row, column) for row in (0, 1) for column in range(4)
    }


def test_the_mask_is_reported_even_for_a_clue_set_refused_on_arithmetic() -> None:
    """The filled-total short cut still reports a grid-shaped mask (AC-110).

    ``solve`` refuses a clue set whose row and column filled totals disagree
    before it builds a board at all. Nothing was decided there, so every cell
    is open — reported, rather than left as an empty list a caller would have
    to special-case.
    """
    result = solve(((2,), (0,)), ((1,), (0,)))

    assert result.solution_count == 0
    assert _set_cells(result.undecided_mask) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert result.rung_tags == [[None, None], [None, None]]


def test_a_grid_with_no_cells_reports_empty_rows_for_both_additions() -> None:
    """The zero-cell corner keeps its shape: one empty line per row."""
    result = solve(((0,), (0,)), ())

    assert result.solution_count == 1
    assert result.undecided_mask == [[], []]
    assert result.rung_tags == [[], []]
    assert result.signals.rungs == ()


# --------------------------------------------------------------------------
# AC-A — the rung tags
# --------------------------------------------------------------------------


def test_a_line_solvable_set_tags_every_cell_without_probe_contradiction() -> None:
    """AC-A: line-solvable tags every cell and never ``probe_contradiction``.

    Both halves of the criterion, on two recorded puzzles: a 15x15 line logic
    finishes on its own, and a 10x10 whose unique solution the search reaches
    only by refuting values.
    """
    rows, columns = compute_clues(LINE_SOLVABLE_15)
    line_solvable = solve(rows, columns)

    assert line_solvable.solution_count == 1
    assert all(tag is not None for line in line_solvable.rung_tags for tag in line)
    assert line_solvable.signals.rung_cells[RUNG_PROBE_CONTRADICTION] == 0
    assert RUNG_PROBE_CONTRADICTION not in line_solvable.signals.rungs
    # Not a formality: a puzzle settled entirely by the overlap rule would pass
    # the two assertions above while telling us nothing about the other rungs.
    assert line_solvable.signals.rungs == (
        RUNG_SIMPLE_OVERLAP,
        RUNG_LINE_DP,
        RUNG_CROSS_LINE,
    )

    probe_rows, probe_columns = compute_clues(NEEDS_PROBE_10)
    needs_probe = solve(probe_rows, probe_columns)

    assert needs_probe.solution_count == 1
    assert needs_probe.signals.rung_cells[RUNG_PROBE_CONTRADICTION] >= 1
    assert RUNG_PROBE_CONTRADICTION in needs_probe.signals.rungs
    assert needs_probe.signals.rungs[-1] == RUNG_PROBE_CONTRADICTION


def test_the_rung_list_is_the_distinct_rungs_present_in_ladder_order() -> None:
    """``signals.rungs`` and ``signals.rung_cells`` are one fact read twice.

    The list is derived from the per-cell tags and nothing else, so a cell
    count and the list can never disagree — which is the property ADR-0029
    leans on when it says the list *is* the grade (R1, R2).
    """
    for grid in (LINE_SOLVABLE_15, NEEDS_PROBE_10, SWITCH_BLOCK):
        rows, columns = compute_clues(grid)
        result = solve(rows, columns)

        tallied = {rung: 0 for rung in RUNG_ORDER}
        for line in result.rung_tags:
            for tag in line:
                if tag is not None:
                    tallied[tag] += 1

        assert dict(result.signals.rung_cells) == tallied
        assert result.signals.rungs == tuple(
            rung for rung in RUNG_ORDER if tallied[rung]
        )
        # Ladder order, not encounter order.
        positions = [RUNG_ORDER.index(rung) for rung in result.signals.rungs]
        assert positions == sorted(positions)


def test_guess_is_not_appended_to_the_rung_list() -> None:
    """``guess`` is not a rung here (ADR-0029, CARD-073 guardrail G-4).

    The switching-block puzzle is settled only by branching, so a classifier
    that treated a guess as a rung would show it. ADR-0025 keys the Guess tier
    on ``branch_nodes``, and CARD-072 appends the word downstream; the solver's
    list stays the four-rung ladder.
    """
    rows, columns = compute_clues(SWITCH_BLOCK)

    result = solve(rows, columns)

    assert result.signals.branch_nodes > 0
    assert set(result.signals.rungs) <= set(RUNG_ORDER)
    assert "guess" not in result.signals.rungs
    # The four block cells were settled by a guess, so no rung claims them.
    untagged = {
        (row, column)
        for row, line in enumerate(result.rung_tags)
        for column, tag in enumerate(line)
        if tag is None
    }
    assert untagged == SWITCH_CELLS


# --------------------------------------------------------------------------
# ADR-0029/R2 — computed inside the one verifying solve
# --------------------------------------------------------------------------


def _replay_untagged(rows: tuple[tuple[int, ...], ...], columns: tuple[tuple[int, ...], ...]) -> None:
    """Run ``solve``'s algorithm with no tagger attached to the board.

    The honest baseline for "does tagging cost a call?": the same propagation
    and the same restart loop, reached through the same module-level names
    (so a counting wrapper sees them), differing from :func:`solve` in the one
    thing under test — ``board.tagger`` is never set.
    """
    canonical_rows = tuple(canonical_clue(clue) for clue in rows)
    canonical_columns = tuple(canonical_clue(clue) for clue in columns)
    height = len(canonical_rows)
    width = len(canonical_columns)
    cache = LineCache.blank(height, width)
    board = Board.blank(canonical_rows, canonical_columns)
    if not search_module.propagate(
        board, [True] * height, [True] * width, None, cache
    ):
        return
    if board.decided == height * width:
        return
    round_index = 0
    while True:
        probe_width, node_limit = search_module._round(round_index)
        found = search_module._search(
            board,
            cache,
            probe_width,
            node_limit,
            round_index,
            None,
            search_module._Counters(),
            [0] * height,
        )
        if found is not search_module._CUT_OFF:
            return
        round_index += 1


@pytest.mark.parametrize(
    "name",
    ["line_solvable", "needs_probe", "switch_block", "unsolvable"],
)
def test_rung_tags_are_computed_inside_the_one_solve(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EC(ADR-0029/R2): no second solve and no re-propagation to classify.

    Both entry points the search reaches propagation through are wrapped with
    call counters, and a tagged ``solve`` is compared against the identical
    run with no tagger attached. Equal counts is the claim: the tags fall out
    of deductions the solve was making anyway, so classification adds no work
    to count — it certainly does not re-enter ``solve``.
    """
    if name == "unsolvable":
        rows, columns = UNSOLVABLE_ROWS, UNSOLVABLE_COLUMNS
    else:
        grid = {
            "line_solvable": LINE_SOLVABLE_15,
            "needs_probe": NEEDS_PROBE_10,
            "switch_block": SWITCH_BLOCK,
        }[name]
        rows, columns = compute_clues(grid)

    calls = {"propagate": 0, "search": 0}
    real_propagate = search_module.propagate
    real_search = search_module._search

    def counting_propagate(*args: object, **kwargs: object) -> object:
        calls["propagate"] += 1
        return real_propagate(*args, **kwargs)  # type: ignore[arg-type]

    def counting_search(*args: object, **kwargs: object) -> object:
        calls["search"] += 1
        return real_search(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(search_module, "propagate", counting_propagate)
    monkeypatch.setattr(search_module, "_search", counting_search)

    result = solve(rows, columns)
    tagged = dict(calls)

    calls["propagate"] = 0
    calls["search"] = 0
    _replay_untagged(rows, columns)
    untagged = dict(calls)

    assert tagged == untagged
    # ...and the tagged run really did classify, or the comparison is vacuous.
    if result.solution_count != 0 or name != "unsolvable":
        assert any(tag is not None for line in result.rung_tags for tag in line)


# --------------------------------------------------------------------------
# EC-012 — nothing an existing caller reads has changed
# --------------------------------------------------------------------------


def test_result_fields_are_unchanged_for_existing_callers() -> None:
    """EC-012: the three pre-existing fields keep their pre-existing meaning.

    Exercised through the actual consumers rather than by inspection: the
    orchestrator's ``solution_count == 1`` gate (INV-002), COMP-006's signals
    protocol, and the boundary-type rule that says neither addition may be an
    int bitmask (ADR-0012, guardrail G-3). EC-001's oracle cross-check is the
    third consumer and is covered by ``tests/property/test_solver_uniqueness.py``
    passing unedited (guardrail G-1).
    """
    for grid, expected_count in (
        (LINE_SOLVABLE_15, 1),
        (NEEDS_PROBE_10, 1),
        (SWITCH_BLOCK, MANY),
    ):
        rows, columns = compute_clues(grid)
        result = solve(rows, columns)

        assert result.solution_count == expected_count
        assert result.is_unique is (expected_count == 1)

        # The orchestrator's gate, called for real.
        puzzle = Puzzle(request=GenerationRequest(mode="random"), seed=0)
        puzzle.record_candidate(grid)
        assert puzzle.confirm_uniqueness(result.solution_count) is (expected_count == 1)

        # COMP-006 still recognises the signals object it is handed.
        assert isinstance(difficulty.score_difficulty(result.signals, rows), float)

        # ``solution`` is still a grid of bools, never a mask.
        assert result.solution is not None
        assert all(isinstance(cell, bool) for line in result.solution for cell in line)

        # Neither addition is an int bitmask at the boundary.
        assert isinstance(result.undecided_mask, list)
        assert all(isinstance(line, list) for line in result.undecided_mask)
        assert all(
            isinstance(cell, bool) for line in result.undecided_mask for cell in line
        )
        assert isinstance(result.rung_tags, list)
        assert all(
            tag is None or isinstance(tag, str)
            for line in result.rung_tags
            for tag in line
        )
        if result.second_witness is not None:
            assert all(
                isinstance(cell, bool)
                for line in result.second_witness
                for cell in line
            )


def test_a_hand_built_result_still_needs_only_the_three_original_fields() -> None:
    """The additions are defaulted, so every existing construction still works.

    ``tests/test_timeout.py`` and ``tests/test_orchestrator.py`` both build a
    ``SolveResult`` by hand to stand in for a solve; EC-012 is only true if
    that keeps compiling, which is what this pins.
    """
    result = SolveResult(
        solution_count=1,
        solution=[[True]],
        signals=search_module.SolveSignals(1, 1, 0, 0, 0.0),
    )

    assert result.second_witness is None
    assert result.undecided_mask == []
    assert result.rung_tags == []
    assert result.witnesses == ([[True]],)
    assert result.signals.rungs == ()
    assert dict(result.signals.rung_cells) == dict.fromkeys(RUNG_ORDER, 0)


# --------------------------------------------------------------------------
# ADR-0029/R4 — the native overlap rule, checked against enumeration
# --------------------------------------------------------------------------


def _true_intersection(clue: tuple[int, ...], length: int) -> tuple[int, int]:
    """What *every* placement of ``clue`` agrees on, by enumerating them all.

    The independent second implementation the house style asks for: it walks
    the concrete placements ``brute_force_oracle.line_candidates`` produces and
    shares no code with either ``overlap_masks`` or the placement DP.
    """
    # ``line_candidates`` speaks AC-013's boundary form, where an empty line is
    # ``(0,)``; ``overlap_masks`` speaks ``canonical_clue``'s, where it is
    # ``()``. Translating here keeps the oracle exactly as it is (guardrail
    # G-1) and keeps the two representations from leaking into each other.
    candidates = line_candidates(clue or (0,), length)
    assert candidates, f"no placement of {clue} in a line of {length}"
    filled = 0
    empty = 0
    for position in range(length):
        values = {candidate[position] for candidate in candidates}
        if values == {True}:
            filled |= 1 << position
        elif values == {False}:
            empty |= 1 << position
    return filled, empty


@pytest.mark.parametrize(
    ("clue", "length", "expected_filled", "expected_empty"),
    [
        # The textbook case: a run longer than half the line overlaps itself.
        ((4,), 5, 0b01110, 0b00000),
        # No overlap at all — a short run in a long line fixes nothing.
        ((1,), 3, 0b000, 0b000),
        # An exact fit is settled completely, both values.
        ((1, 1), 3, 0b101, 0b010),
        # The empty line: every cell empty, no arithmetic needed.
        ((), 4, 0b0000, 0b1111),
        # A clue that cannot fit is not classified at all.
        ((3, 3), 5, 0, 0),
    ],
)
def test_overlap_masks_match_the_textbook_rule(
    clue: tuple[int, ...], length: int, expected_filled: int, expected_empty: int
) -> None:
    """ADR-0029's ``simple_overlap``, on lines small enough to read by eye."""
    assert overlap_masks(clue, length) == (expected_filled, expected_empty)


def test_overlap_masks_never_claim_more_than_every_placement_agrees_on() -> None:
    """ADR-0029/R4: the rule is sound, so it can classify a DP deduction.

    A seeded corpus of every clue that fits in a line of up to 9 cells: what
    the overlap rule fixes must be a *subset* of what enumeration says every
    placement agrees on. If it ever claimed more, a cell would be tagged
    ``simple_overlap`` for a value the rule gets wrong — the one way this
    classifier could lie about a solve.
    """
    rng = random.Random(20260912)
    checked = 0
    for length in range(1, 10):
        for _ in range(40):
            runs: list[int] = []
            room = length
            while room > 0 and rng.random() < 0.6:
                run = rng.randint(1, room)
                runs.append(run)
                room -= run + 1
            clue = tuple(runs)
            if sum(clue) + len(clue) - 1 > length:
                continue
            checked += 1
            overlap_filled, overlap_empty = overlap_masks(clue, length)
            true_filled, true_empty = _true_intersection(clue, length)
            assert overlap_filled & ~true_filled == 0, (clue, length)
            assert overlap_empty & ~true_empty == 0, (clue, length)
    assert checked >= 200, f"corpus shrank to {checked} lines"
