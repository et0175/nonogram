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
(``propagate.overlap_deduction``, and the greedy under it,
``propagate.overlap_extremes``) is checked here too, against an independent
enumeration of every placement of the line rather than against itself: the
house rule is a second implementation, not a second call. That cross-check is
the one this file exists to carry. Getting the leftmost/rightmost placement
right *in the presence of known-filled cells* is where this rule goes wrong
quietly — a greedy that only dodges known-empty cells will happily strand a
known-filled one in a gap, and every mask read off it then claims cells no
placement agrees on.

Rung tags are also asserted here to be invariant under transposition only in
passing; ADR-0029/R5's property over a corpus lives next to EC-011 in
``tests/property/test_solver_witnesses.py``.
"""

from __future__ import annotations

import random

import pytest

from nonogram import difficulty
from nonogram.clues import compute_clues
from nonogram.orchestrator import Puzzle, GenerationRequest
from nonogram.solver import (
    MANY,
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
    line_intersection,
    overlap_deduction,
    overlap_extremes,
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
#: and no probe. Recorded rather than described. Under the revised ladder every
#: one of its 225 cells falls to the knowledge-relative overlap rule alone, so
#: it is the ``simple_overlap``-only end of the scale — :data:`LINE_DP_12` is
#: the line-solvable puzzle that needs the placement DP. Both rung mixes are
#: asserted where they are used, so a re-grade cannot pass silently.
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

#: AC-A's middle: a 12x12 that line logic also finishes on its own, but only
#: with the full placement intersection — 133 of its 144 cells are settled at
#: level 2 and 11 at level 1, with no probe needed. Recorded because
#: "line-solvable *and* needs the DP" is not a property you can draw by hand,
#: and because without it AC-A would be satisfied by two puzzles that never
#: leave the bottom rung and the middle rung of the ladder would go untested.
LINE_DP_12 = _from_ascii(
    ".......#.###",
    "....#.##....",
    "##.#..#.##.#",
    "#...######.#",
    "#.###.#.....",
    "..####...#.#",
    "##...#.#.#.#",
    ".#.......##.",
    "#.##.##...#.",
    "#.###..##.#.",
    "#....####..#",
    "..#..#.##.#.",
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
    """AC-A, as the 2026-09-12 ADR-0029 revision re-words it.

    Three recorded puzzles, one per rung of the ladder, so that every rung is
    reached by some puzzle and each puzzle's own top rung is pinned:

    * :data:`LINE_SOLVABLE_15` never leaves ``simple_overlap``;
    * :data:`LINE_DP_12` is line-solvable too but needs the full placement
      intersection, so it tops out at ``line_dp``;
    * :data:`NEEDS_PROBE_10` needs a refuted probe and tops out at
      ``probe_contradiction`` — with ``branch_nodes == 0``, because under the
      revision probing is a *phase* of the solve rather than search work, which
      is what makes the puzzle gradeable on this ladder at all (ADR-0025 would
      otherwise call it ``Tier.GUESS``).

    The first two are AC-A's "line-solvable" half: every cell carries a rung
    and none of them is ``probe_contradiction``.
    """
    for grid, expected_rungs in (
        (LINE_SOLVABLE_15, (RUNG_SIMPLE_OVERLAP,)),
        (LINE_DP_12, (RUNG_SIMPLE_OVERLAP, RUNG_LINE_DP)),
    ):
        line_solvable = solve(*compute_clues(grid))

        assert line_solvable.solution_count == 1
        assert line_solvable.signals.branch_nodes == 0
        assert all(tag is not None for line in line_solvable.rung_tags for tag in line)
        assert line_solvable.signals.rung_cells[RUNG_PROBE_CONTRADICTION] == 0
        # Not a formality: two puzzles that both stopped at the bottom rung
        # would pass everything above and leave ``line_dp`` untested.
        assert line_solvable.signals.rungs == expected_rungs

    needs_probe = solve(*compute_clues(NEEDS_PROBE_10))

    assert needs_probe.solution_count == 1
    assert needs_probe.signals.rung_cells[RUNG_PROBE_CONTRADICTION] >= 1
    assert RUNG_PROBE_CONTRADICTION in needs_probe.signals.rungs
    assert needs_probe.signals.rungs[-1] == RUNG_PROBE_CONTRADICTION
    assert all(tag is not None for line in needs_probe.rung_tags for tag in line)
    # ADR-0029's point: the probing phase finished it, so the search never ran.
    assert needs_probe.signals.branch_nodes == 0


def test_the_rung_list_is_the_distinct_rungs_present_in_ladder_order() -> None:
    """``signals.rungs`` and ``signals.rung_cells`` are one fact read twice.

    The list is derived from the per-cell tags and nothing else, so a cell
    count and the list can never disagree — which is the property ADR-0029
    leans on when it says the list *is* the grade (R1, R2).
    """
    for grid in (LINE_SOLVABLE_15, LINE_DP_12, NEEDS_PROBE_10, SWITCH_BLOCK):
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

    ADR-0025 keys the Guess tier on ``branch_nodes``, and CARD-072 appends the
    word downstream where the list is persisted; the solver's own list stays
    the three-rung ladder whatever the solve had to do. Checked on the two
    shapes that could leak a fourth name — a puzzle that needed a refuted probe
    (the top rung), and a clue set the search had to branch on.
    """
    for rows, columns in (
        compute_clues(NEEDS_PROBE_10),
        compute_clues(SWITCH_BLOCK),
    ):
        result = solve(rows, columns)

        assert set(result.signals.rungs) <= set(RUNG_ORDER)
        assert "guess" not in result.signals.rungs


# --------------------------------------------------------------------------
# ADR-0029/R2 — computed inside the one verifying solve
# --------------------------------------------------------------------------


def _replay_untagged(rows: tuple[tuple[int, ...], ...], columns: tuple[tuple[int, ...], ...]) -> None:
    """Run ``solve``'s three phases and its search with nothing tagged.

    The honest baseline for "does classification cost a call?": the same level-1
    overlap fixed point, the same level-2 propagation, the same level-3 probing
    phase and the same restart loop, reached through the same module-level names
    (so a counting wrapper sees them), differing from :func:`solve` in the one
    thing under test — no ``RungTagger`` is ever attached, and level 3 writes
    its rungs into a grid that is thrown away.
    """
    canonical_rows = tuple(canonical_clue(clue) for clue in rows)
    canonical_columns = tuple(canonical_clue(clue) for clue in columns)
    height = len(canonical_rows)
    width = len(canonical_columns)
    total_cells = height * width
    cache = LineCache.blank(height, width)
    board = Board.blank(canonical_rows, canonical_columns)
    discarded: list[list[str | None]] = [[None] * width for _ in range(height)]

    if not search_module.propagate_overlap(board, [True] * height, [True] * width, None):
        return
    if not search_module.propagate(board, [True] * height, [True] * width, None, cache):
        return
    if board.decided == total_cells:
        return
    speculative_width, speculative_limit = search_module._round(0)
    speculative = search_module._search(
        board,
        cache,
        speculative_width,
        speculative_limit,
        0,
        None,
        search_module._Counters(),
    )
    if speculative is not search_module._CUT_OFF and len(speculative) == MANY:
        return
    board, contradicted = search_module._probe_fixed_point(board, cache, None, discarded)
    if not contradicted and board.decided == total_cells:
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
        )
        if found is not search_module._CUT_OFF:
            return
        round_index += 1


@pytest.mark.parametrize(
    "name",
    ["line_solvable", "line_dp", "needs_probe", "switch_block", "unsolvable"],
)
def test_rung_tags_are_computed_inside_the_one_solve(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """EC(ADR-0029/R2): no second solve and no re-propagation to classify.

    Every entry point the solve reaches propagation through is wrapped with a
    call counter, and a tagged ``solve`` is compared against the identical run
    with nothing tagged. Equal counts is the claim: the rungs fall out of
    deductions the solve was making anyway, so classification adds no work to
    count — it certainly does not re-enter ``solve``.

    ADR-0029/R2's other half — that the ladder's fixed points are *phases of
    one monotone forward solve*, each continuing from the board the previous
    left — is structural here rather than counted: ``solve`` builds exactly one
    :class:`Board`, never resets it, and hands whatever a phase leaves to the
    next one. A phase that re-propagated from a blank board to classify would
    show up in these counts immediately.
    """
    if name == "unsolvable":
        rows, columns = UNSOLVABLE_ROWS, UNSOLVABLE_COLUMNS
    else:
        grid = {
            "line_solvable": LINE_SOLVABLE_15,
            "line_dp": LINE_DP_12,
            "needs_probe": NEEDS_PROBE_10,
            "switch_block": SWITCH_BLOCK,
        }[name]
        rows, columns = compute_clues(grid)

    calls = {"propagate": 0, "propagate_overlap": 0, "search": 0}
    real_propagate = search_module.propagate
    real_overlap = search_module.propagate_overlap
    real_search = search_module._search

    def counting_propagate(*args: object, **kwargs: object) -> object:
        calls["propagate"] += 1
        return real_propagate(*args, **kwargs)  # type: ignore[arg-type]

    def counting_overlap(*args: object, **kwargs: object) -> object:
        calls["propagate_overlap"] += 1
        return real_overlap(*args, **kwargs)  # type: ignore[arg-type]

    def counting_search(*args: object, **kwargs: object) -> object:
        calls["search"] += 1
        return real_search(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(search_module, "propagate", counting_propagate)
    monkeypatch.setattr(search_module, "propagate_overlap", counting_overlap)
    monkeypatch.setattr(search_module, "_search", counting_search)

    result = solve(rows, columns)
    tagged = dict(calls)

    for key in calls:
        calls[key] = 0
    _replay_untagged(rows, columns)
    untagged = dict(calls)

    assert tagged == untagged
    # The overlap fixed point is a phase of the solve, not an extra pass.
    assert tagged["propagate_overlap"] == 1
    # ...and where there is a grade to report, the tagged run really did
    # classify, or the comparison is vacuous. A clue set that is not a puzzle
    # reports no attribution at all (ADR-0029's 2026-09-12 scoping), so there
    # the vacuity check is the other way round.
    if result.solution_count == 1:
        assert any(tag is not None for line in result.rung_tags for tag in line)
    else:
        assert all(tag is None for line in result.rung_tags for tag in line)


def test_a_clue_set_that_is_not_a_puzzle_carries_no_rung_attribution() -> None:
    """ADR-0029's 2026-09-12 scoping: no grade without exactly one solution.

    A clue set with two solutions, and one with none, are not puzzles — they
    have no difficulty and no strategies list — so the solver reports no
    attribution for them at all: every cell ``None``, an empty rung list and an
    all-zero histogram, whatever the deduction phases happened to settle on the
    way to the verdict. This is also what lets the solve skip level 3 once
    round 0 has shown a clue set ambiguous: there is nothing left for the dear
    rung to attribute.

    ADR-0029/R5's negative half rides along: the search writes no tags either,
    and both of these verdicts come out of the search.
    """
    for rows, columns in (
        compute_clues(SWITCH_BLOCK),
        (UNSOLVABLE_ROWS, UNSOLVABLE_COLUMNS),
    ):
        result = solve(rows, columns)

        assert result.solution_count != 1
        assert all(tag is None for line in result.rung_tags for tag in line)
        assert result.signals.rungs == ()
        assert dict(result.signals.rung_cells) == dict.fromkeys(RUNG_ORDER, 0)
        # Shape is still reported, so a consumer can index it blind.
        assert [len(line) for line in result.rung_tags] == [
            len(line) for line in result.undecided_mask
        ]


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


def _feasible_placements(
    runs: tuple[int, ...], length: int, known_filled: int, known_empty: int
) -> list[tuple[tuple[int, ...], int]]:
    """Every placement of ``runs`` consistent with what is known, enumerated.

    The independent second implementation the house style asks for, and the
    only thing in this file that knows what "consistent" means without asking
    the code under test: it lays the runs out recursively, builds each
    placement's filled mask, and keeps a placement only when it covers every
    known-filled cell and no known-empty one. Both conditions, and the second
    is the one a greedy gets wrong.

    Returns one ``(starts, filled_mask)`` pair per feasible placement.
    """

    def lay_out(index: int, position: int, starts: list[int]) -> list[tuple[int, ...]]:
        if index == len(runs):
            return [tuple(starts)]
        found: list[tuple[int, ...]] = []
        tail = sum(runs[index:]) + (len(runs) - index - 1)
        for start in range(position, length - tail + 1):
            starts.append(start)
            found.extend(lay_out(index + 1, start + runs[index] + 1, starts))
            starts.pop()
        return found

    placements: list[tuple[tuple[int, ...], int]] = []
    for starts in lay_out(0, 0, []):
        mask = 0
        for start, run in zip(starts, runs, strict=True):
            mask |= ((1 << run) - 1) << start
        if mask & known_empty:
            continue
        if known_filled & ~mask:
            continue
        placements.append((starts, mask))
    return placements


def _overlap_corpus(count: int) -> list[tuple[tuple[int, ...], int, int, int]]:
    """Seeded ``(runs, length, known_filled, known_empty)`` triples.

    Lines are short (up to 11 cells) so that enumerating every placement is
    cheap, and the known masks are drawn *and then thinned*, which is what
    makes most of the corpus feasible rather than a pile of contradictions that
    would test only the ``None`` path. Both feasible and infeasible triples are
    kept: a rule that called an impossible line possible is as wrong as one
    that mislocated a run.
    """
    rng = random.Random(20260912)
    corpus: list[tuple[tuple[int, ...], int, int, int]] = []
    while len(corpus) < count:
        length = rng.randint(1, 11)
        runs: list[int] = []
        room = length
        while room > 0 and rng.random() < 0.55:
            run = rng.randint(1, room)
            runs.append(run)
            room -= run + 1
        clue = tuple(runs)
        if sum(clue) + len(clue) - 1 > length:
            continue
        full = (1 << length) - 1
        known_filled = rng.getrandbits(length) & full & rng.getrandbits(length)
        known_empty = rng.getrandbits(length) & full & ~known_filled
        if rng.random() < 0.5:
            known_empty &= rng.getrandbits(length)
        corpus.append((clue, length, known_filled, known_empty))
    return corpus


#: ADR-0029/R4's corpus. The floor the card names is 500 triples; this is the
#: count actually built, asserted inside the test so it cannot shrink silently.
OVERLAP_CASES = 800

OVERLAP_CORPUS = _overlap_corpus(OVERLAP_CASES)


@pytest.mark.parametrize(
    ("clue", "length", "known_filled", "known_empty", "expected_filled", "expected_empty"),
    [
        # The textbook case, on a blank line: a run longer than half the line
        # overlaps itself.
        ((4,), 5, 0b00000, 0b00000, 0b01110, 0b00000),
        # No overlap at all — a short run in a long line fixes nothing.
        ((1,), 3, 0b000, 0b000, 0b000, 0b000),
        # ...until the line says something. One known-empty cell pins it.
        ((1,), 3, 0b000, 0b001, 0b000, 0b001),
        # A known-filled cell the run must cover, which is the case a greedy
        # that only dodges known-empty cells gets wrong: with cell 2 filled,
        # run 0 can no longer start at 0, so cells 0 and 1 are empty.
        ((1,), 3, 0b100, 0b000, 0b100, 0b011),
        # An exact fit is settled completely, both values.
        ((1, 1), 3, 0b000, 0b000, 0b101, 0b010),
        # The empty line: every cell empty, no arithmetic needed.
        ((), 4, 0b0000, 0b0000, 0b0000, 0b1111),
    ],
)
def test_overlap_deduction_matches_the_textbook_rule(
    clue: tuple[int, ...],
    length: int,
    known_filled: int,
    known_empty: int,
    expected_filled: int,
    expected_empty: int,
) -> None:
    """ADR-0029's ``simple_overlap``, on lines small enough to read by eye."""
    assert overlap_deduction(clue, length, known_filled, known_empty) == (
        expected_filled,
        expected_empty,
    )


@pytest.mark.parametrize(
    ("clue", "length", "known_filled", "known_empty"),
    [
        # A clue that cannot fit at all.
        ((3, 3), 5, 0, 0),
        # A filled cell no placement can cover: runs (1,1) in a line of 4 can
        # only cover {0,2}, {0,3} or {1,3}, and none of those covers both 1
        # and 2.
        ((1, 1), 4, 0b0110, 0b0000),
        # Every cell the run could live in is known empty.
        ((2,), 4, 0b0000, 0b1111),
    ],
)
def test_overlap_deduction_reports_an_impossible_line(
    clue: tuple[int, ...], length: int, known_filled: int, known_empty: int
) -> None:
    """A line with no feasible placement is ``None``, not a pile of masks."""
    assert overlap_deduction(clue, length, known_filled, known_empty) is None
    assert overlap_extremes(clue, length, known_filled, known_empty) is None


def test_the_overlap_greedy_finds_the_true_extreme_start_of_every_run() -> None:
    """ADR-0029/R4: ``overlap_extremes`` really is the min and max start.

    The trap this exists for: the leftmost and rightmost placements have to be
    the ones *consistent with the line's known cells*, and a placement that
    leaves a known-filled cell uncovered is infeasible however comfortably its
    runs fit between the known-empty ones. A greedy that misses that returns a
    start that is too small, and every mask derived from it then claims cells
    no placement agrees on — a ``simple_overlap`` tag for a deduction the rule
    cannot actually make.

    So the greedy is compared, over a seeded corpus, against the componentwise
    minimum and maximum start taken from an enumeration of *every* feasible
    placement — a second implementation, not a second call. Feasibility itself
    is cross-checked both ways at the same time.
    """
    assert len(OVERLAP_CORPUS) >= 500, (
        f"corpus shrank to {len(OVERLAP_CORPUS)} triples, below the floor of 500"
    )

    feasible_cases = 0
    for clue, length, known_filled, known_empty in OVERLAP_CORPUS:
        placements = _feasible_placements(clue, length, known_filled, known_empty)
        extremes = overlap_extremes(clue, length, known_filled, known_empty)
        context = f"runs={clue} length={length} filled={known_filled:b} empty={known_empty:b}"

        if not placements:
            assert extremes is None, f"{context}: called an impossible line possible"
            continue

        feasible_cases += 1
        assert extremes is not None, f"{context}: called a possible line impossible"
        leftmost, rightmost = extremes
        for index in range(len(clue)):
            starts = [placement[0][index] for placement in placements]
            assert leftmost[index] == min(starts), f"{context}: run {index} leftmost"
            assert rightmost[index] == max(starts), f"{context}: run {index} rightmost"

    assert feasible_cases >= 200, f"only {feasible_cases} feasible triples in the corpus"


def test_overlap_deduction_never_claims_more_than_every_placement_agrees_on() -> None:
    """ADR-0029/R4: the rule is sound, so it can define a rung.

    What the overlap rule settles must be a *subset* of what enumeration says
    every feasible placement agrees on. If it ever claimed more, a cell would
    be tagged ``simple_overlap`` for a value the rule gets wrong — the one way
    this classifier could lie about a solve — and, worse, the level-1 fixed
    point would write a cell some solution contradicts, which is CON-005.

    The same loop pins the other side of the rung's definition: overlap is
    *weaker* than the placement DP it is distinguished from, so anything it
    settles ``line_intersection`` settles too. Were that ever false, "only the
    DP could reach this cell" would stop meaning anything.
    """
    checked = 0
    for clue, length, known_filled, known_empty in OVERLAP_CORPUS:
        placements = _feasible_placements(clue, length, known_filled, known_empty)
        if not placements:
            continue
        checked += 1
        context = f"runs={clue} length={length} filled={known_filled:b} empty={known_empty:b}"

        full = (1 << length) - 1
        agreed_filled = full
        agreed_empty = full
        for _starts, mask in placements:
            agreed_filled &= mask
            agreed_empty &= full & ~mask

        deduced = overlap_deduction(clue, length, known_filled, known_empty)
        assert deduced is not None, context
        filled, empty = deduced
        assert filled & ~agreed_filled == 0, f"{context}: unsound filled"
        assert empty & ~agreed_empty == 0, f"{context}: unsound empty"
        # Supersets of what was already known, as ``line_intersection`` is.
        assert filled & known_filled == known_filled, context
        assert empty & known_empty == known_empty, context

        dp = line_intersection(clue, length, known_filled, known_empty)
        assert dp is not None, f"{context}: the DP disagreed about feasibility"
        assert filled & ~dp[0] == 0, f"{context}: overlap outran the DP (filled)"
        assert empty & ~dp[1] == 0, f"{context}: overlap outran the DP (empty)"

    assert checked >= 200, f"only {checked} feasible triples in the corpus"
