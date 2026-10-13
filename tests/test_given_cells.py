"""COMP-005/COMP-002 tests: revealing cells instead of changing the picture.

CARD-214. AC / test-id mapping — the card's names, kept traceable from these
pytest-idiomatic function names:

    AC-1  TestGivenCells_MakeThePuzzleUnique
              -> test_given_cells_make_the_puzzle_unique*
    AC-2  TestGivenCells_UniqueGridNeedsNone
              -> test_given_cells_unique_grid_needs_none*
    AC-3  TestGenerate_RevealPolicyNeverChangesTheGrid
              -> test_generate_reveal_policy_never_changes_the_grid*
    AC-4  TestGivenCells_RefusesBeyondTheCap
              -> test_given_cells_refuses_beyond_the_cap*
    AC-8  TestGivenCells_ContradictoryGivenCountsZero
              -> test_given_cells_contradictory_given_counts_zero*

The card's Failure matrix rows are covered here too, each by the test its
numeric bound names: the cap (F1), the chooser's solve budget against the retry
bounds (F2, ``test_the_reveal_policy_keeps_the_random_mode_retry_bound``), the
deadline landing mid-chooser (F3), the contradictory given (F4), a malformed
assignment (F5) and clues that are not the grid's (F6). F9 and F10 — I/O and
concurrency — have nothing to test: this path opens no file and starts no
thread.

AC-6 (the EC(CON-005) property under givens) lives in
``tests/property/test_solver_uniqueness.py``, against the independent
brute-force oracle; AC-7 (determinism) in ``tests/property/test_given_cells.py``.
AC-5 ("with the flag off nothing moved") is the existing recovery suite still
passing unchanged — ``tests/property/test_recovery_bound.py`` and
``tests/test_orchestrator.py``'s ``TestRecovery_*`` section — plus
``test_solver.py``'s corpus check that ``givens=None`` changes no verdict.

Scripted grids, real solver
---------------------------
The house style of ``tests/test_nudge.py`` and ``tests/test_orchestrator.py``:
only the *grid* a mode produces is scripted, and everything downstream of it —
the clue derivation, the solver, the chooser, the policy — is the real
pipeline. A test that faked the uniqueness verdict would be testing the fake,
and the verdict being the solver's is precisely what CON-005 and this card's
guardrails claim.

Two grids do almost all of the work, both built from ``_switching_pairs``: a
diagonal filled pair with nothing near it is the textbook non-unique nonogram
(the other diagonal has the same row clues and the same column clues), and each
pair needs exactly one revealed cell to break. That makes the arithmetic of the
cap a property of the fixture rather than of the heuristic's luck:

``_SIX_SWITCHES``   12x12, six pairs -> six reveals, under the cap of 7.
``_EIGHT_SWITCHES`` 12x12, eight pairs -> eight reveals, over the cap of 7.

``test_the_scripted_grids_are_what_the_ac_tests_assume`` pins both facts
against the real solver, so a change that made them unique, or cheaper to fix,
fails loudly there instead of quietly turning the AC tests vacuous.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from nonogram import cli, clues, orchestrator, solver
from nonogram.errors import (
    GenerationAbandoned,
    GivenCellsCapExceeded,
    NonogramError,
    SolverTimeout,
)
from nonogram.orchestrator import (
    MAX_GIVEN_CELL_SHARE_PERCENT,
    MAX_NUDGE_ATTEMPTS,
    MAX_RETRY_ATTEMPTS,
    GenerationRequest,
    generate,
    given_cells_cap,
)

Grid = list[list[bool]]
Givens = list[list[bool | None]]

#: A real picture, so that nothing in the request-resolution path has to be
#: mocked (``_resolved_extent`` reads the file's shape only for a bare
#: ``--size``, and these requests state both sides — but the path still has to
#: exist). The scripted source is what actually produces every grid below, so
#: this file is never converted.
_FIXTURE_IMAGE = Path(__file__).parent / "fixtures" / "landscape.png"


# --------------------------------------------------------------------------
# Grids, and the properties the tests below lean on
# --------------------------------------------------------------------------


def _switching_pairs(size: int, corners: tuple[tuple[int, int], ...]) -> Grid:
    """A blank ``size`` x ``size`` grid with a filled diagonal pair per corner.

    ``(r, c)`` fills ``(r, c)`` and ``(r + 1, c + 1)``. Lifted deliberately
    verbatim from ``tests/test_nudge.py`` rather than imported: that module is
    about POL-002's mechanism and this one about a different policy, and a
    shared helper between them would make a change to one silently re-pin the
    other's arithmetic.
    """
    grid = [[False] * size for _ in range(size)]
    for row, column in corners:
        grid[row][column] = True
        grid[row + 1][column + 1] = True
    return grid


#: Six independent ambiguities on a 12x12: six reveals, cap 7.
_SIX_SWITCHES = _switching_pairs(
    12, ((1, 1), (1, 5), (1, 9), (5, 1), (5, 5), (5, 9))
)

#: Eight of them: eight reveals needed, cap 7 — the refusal, by arithmetic.
_EIGHT_SWITCHES = _switching_pairs(
    12, ((1, 1), (1, 5), (1, 9), (5, 1), (5, 5), (5, 9), (9, 1), (9, 5))
)

#: One ambiguity: one reveal breaks it, and it is the smallest grid on which
#: "the first disagreement cell by (row, column)" is predictable by hand.
_ONE_SWITCH = _switching_pairs(12, ((1, 1),))

#: A plus sign on a 12x12 — line-solvable, uniquely so, and Easy. AC-2's given,
#: and the "already unique, missed tier" given further down. 12x12 rather than
#: something smaller because CON-011 is a *domain* rule enforced inward of the
#: CLI: a 7x7 request is refused by ``validate_extent`` before any source runs,
#: so a grid below MIN_SIZE cannot be driven through ``generate`` at all.
_PLUS = [
    [row == 6 or column == 6 for column in range(12)] for row in range(12)
]


def _solve(grid: Grid, givens: Givens | None = None) -> solver.SolveResult:
    """The real solver's verdict on ``grid``'s own clues (never a stand-in)."""
    grid_clues = clues.compute_clues(grid)
    return solver.solve(grid_clues.rows, grid_clues.columns, givens=givens)


def _choose(grid: Grid, cap: int) -> Givens:
    """The real chooser on ``grid``'s own clues."""
    grid_clues = clues.compute_clues(grid)
    return solver.choose_givens(
        grid, grid_clues.rows, grid_clues.columns, cap=cap
    )


def test_the_scripted_grids_are_what_the_ac_tests_assume() -> None:
    """Guard the fixtures: an ambiguity count that drifted would make the cap
    tests pass while asserting nothing.

    Every number here comes from the real solver and the real chooser, and the
    two cap facts the AC tests rest on are stated as the arithmetic they are:
    six reveals fit under 7, eight do not.
    """
    assert given_cells_cap(_SIX_SWITCHES) == 7
    assert given_cells_cap(_EIGHT_SWITCHES) == 7

    assert _solve(_SIX_SWITCHES).solution_count == solver.MANY
    assert len(solver.revealed_cells(_choose(_SIX_SWITCHES, cap=7))) == 6

    assert _solve(_EIGHT_SWITCHES).solution_count == solver.MANY
    with pytest.raises(GivenCellsCapExceeded):
        _choose(_EIGHT_SWITCHES, cap=7)

    assert _solve(_PLUS).solution_count == 1


# --------------------------------------------------------------------------
# AC-1 — TestGivenCells_MakeThePuzzleUnique
# --------------------------------------------------------------------------


def test_given_cells_make_the_puzzle_unique() -> None:
    """The criterion: what the chooser returns makes a *fresh* seeded solve
    report exactly 1, and every revealed cell holds the grid's own value.

    Both halves matter and neither implies the other. A chooser that revealed
    the *wrong* values could still force uniqueness — by making the clues
    describe a different grid, or none — and the puzzle a user then solved
    would contradict the picture it came from. So the values are checked
    against the source grid cell by cell, and the uniqueness is checked by a
    solve this test runs itself rather than by the chooser's own last word.
    """
    givens = _choose(_SIX_SWITCHES, cap=given_cells_cap(_SIX_SWITCHES))
    revealed = solver.revealed_cells(givens)

    assert revealed, "an ambiguous grid must need at least one reveal"
    for row, column, value in revealed:
        assert value == _SIX_SWITCHES[row][column], (
            f"({row}, {column}) was revealed as {value} but the grid holds "
            f"{_SIX_SWITCHES[row][column]}"
        )

    fresh = _solve(_SIX_SWITCHES, givens)
    assert fresh.solution_count == 1
    assert fresh.solution == _SIX_SWITCHES


def test_given_cells_make_the_puzzle_unique_without_touching_the_grid() -> None:
    """The chooser computes a value and changes nothing — not the grid it was
    handed, and not the clues.

    Stated as a test because "returns the set of revealed cells, as a value,
    computing nothing in place" is the whole reason this policy can claim to
    preserve the picture: a chooser that repaired the grid on the way would
    satisfy every other assertion in this file.
    """
    grid = [row[:] for row in _SIX_SWITCHES]
    before = clues.compute_clues(grid)

    _choose(grid, cap=given_cells_cap(grid))

    assert grid == _SIX_SWITCHES
    assert clues.compute_clues(grid) == before


def test_given_cells_reveal_the_first_ambiguous_cell_by_row_then_column() -> None:
    """ADR-0024/R4's rule, adopted by this card: the cell revealed is the first
    by ``(row, column)`` on which the solver's two witnesses disagree.

    Checked on a grid whose *whole* ambiguity is one switching pair, so one
    reveal is the entire choice and nothing after it can confuse the reading.
    The witnesses come from the real solver, so the expected cell is whatever
    COMP-005 actually reports rather than a hand-written literal — a test that
    invented the disagreement set could agree with the chooser and disagree
    with the solver.
    """
    verdict = _solve(_ONE_SWITCH)
    assert verdict.solution_count == solver.MANY
    first, second = verdict.witnesses
    disagreements = [
        (row, column)
        for row, (left, right) in enumerate(zip(first, second, strict=True))
        for column, (one, other) in enumerate(zip(left, right, strict=True))
        if one != other
    ]
    assert len(disagreements) == 4, "one switching pair is four disagreeing cells"
    row, column = min(disagreements)

    revealed = solver.revealed_cells(_choose(_ONE_SWITCH, cap=1))

    assert revealed == ((row, column, _ONE_SWITCH[row][column]),)


# --------------------------------------------------------------------------
# AC-2 — TestGivenCells_UniqueGridNeedsNone
# --------------------------------------------------------------------------


def test_given_cells_unique_grid_needs_none() -> None:
    """A grid that is already uniquely solvable gets no reveals at all.

    The empty assignment, not "one harmless cell": a reveal is a piece of the
    answer given away, so the policy must spend none where none is needed —
    and ``revealed_cells`` must read the all-``None`` grid as nothing, since
    that is the value the orchestrator tests to decide whether the policy had
    anything to do.
    """
    givens = _choose(_PLUS, cap=given_cells_cap(_PLUS))

    assert solver.revealed_cells(givens) == ()
    assert givens == [[None] * 12 for _ in range(12)]
    assert _solve(_PLUS, givens).solution_count == 1


def test_given_cells_unique_grid_needs_none_even_with_a_cap_of_zero() -> None:
    """``cap=0`` is a meaningful question — "does this need any reveal?" — and
    an already-unique grid answers it without raising.

    The boundary of the cap from the other side: ``cap=0`` on an *ambiguous*
    grid refuses immediately, having revealed nothing.
    """
    assert solver.revealed_cells(_choose(_PLUS, cap=0)) == ()

    with pytest.raises(GivenCellsCapExceeded) as refusal:
        _choose(_SIX_SWITCHES, cap=0)
    assert "0" in str(refusal.value)


# --------------------------------------------------------------------------
# AC-8 — TestGivenCells_ContradictoryGivenCountsZero
# --------------------------------------------------------------------------


def test_given_cells_contradictory_given_counts_zero() -> None:
    """A given that contradicts a unique solution makes the count 0.

    Not 1 — the solver must not ignore the assignment it was given — and not
    an exception: a partial assignment no solution extends is a fact about the
    count, exactly as a contradictory clue set is (AC-016). The distinction is
    the whole of what "seeded count" means, and a caller that got an exception
    here would have to treat an ordinary outcome as an error.
    """
    grid_clues = clues.compute_clues(_PLUS)
    assert solver.solve(grid_clues.rows, grid_clues.columns).solution_count == 1

    contradicted: Givens = [[None] * 12 for _ in range(12)]
    # (0, 0) is empty in the plus sign, so revealing it as filled contradicts
    # the one solution the clues have.
    assert _PLUS[0][0] is False
    contradicted[0][0] = True

    verdict = solver.solve(grid_clues.rows, grid_clues.columns, givens=contradicted)

    assert verdict.solution_count == 0
    assert verdict.solution is None
    assert verdict.second_witness is None


def test_given_cells_contradictory_given_counts_zero_for_a_whole_wrong_grid() -> None:
    """The same answer when *every* cell is revealed, wrongly.

    The fully-given case is the one where no search happens at all — the board
    is complete before line logic runs — so it exercises a different path to
    the same verdict than the single contradicted cell above. Its companion is
    the fully-given *correct* grid, which must answer 1.
    """
    grid_clues = clues.compute_clues(_PLUS)

    correct: Givens = [[cell for cell in row] for row in _PLUS]
    assert solver.solve(
        grid_clues.rows, grid_clues.columns, givens=correct
    ).solution_count == 1

    inverted: Givens = [[not cell for cell in row] for row in _PLUS]
    assert solver.solve(
        grid_clues.rows, grid_clues.columns, givens=inverted
    ).solution_count == 0


def test_a_malformed_givens_is_a_value_error_not_a_verdict() -> None:
    """The shape is part of the contract, and a broken one is a caller bug.

    Reported the way ``solve`` already reports a malformed clue set, for the
    same reason: a ragged or short assignment would otherwise seed *some* of
    the cells the caller meant and silently answer a different question.
    """
    grid_clues = clues.compute_clues(_PLUS)

    with pytest.raises(ValueError, match="row"):
        solver.solve(grid_clues.rows, grid_clues.columns, givens=[[None] * 12])
    with pytest.raises(ValueError, match="cell"):
        solver.solve(
            grid_clues.rows,
            grid_clues.columns,
            givens=[[None] * 12] * 11 + [[None] * 3],
        )


def test_the_chooser_refuses_clues_that_are_not_the_grids_own() -> None:
    """The INV-001 guard: a grid and clues that disagree is a caller bug.

    The chooser reveals cells of the *grid* it is handed, so it can only answer
    for that grid's own clues — and the failure it must not have is the quiet
    one: returning reveals that make some *other* grid uniquely solvable, which
    is a puzzle whose answer is not the picture it came from. Both ways of
    seeing the mismatch are checked, because a mismatched pair reaches whichever
    one the clues happen to allow, and both are checked:

    * **a unique solution that is not this grid.** The eight-pair clues against
      the six-pair grid: the reveals pin the six pairs that grid has and empty
      the two it does not, which leaves exactly one solution — the eight-pair
      grid. This is the quiet failure, and the branch worth having a test for.
    * **no solution at all.** Clues whose row and column filled counts cannot
      both hold have no solution, so they encode no grid; a *reveal* can never
      produce this outcome (one of the two disagreeing witnesses always
      survives the revealed value), so it can only come from the clues
      themselves.

    Reported as a ``ValueError`` naming the invariant rather than as "cannot be
    made unique": only one of the two is a fact about a picture. Unreachable
    through ``generate``, where ``record_candidate`` derives the clues from the
    grid it is recording.
    """
    eight = clues.compute_clues(_EIGHT_SWITCHES)

    with pytest.raises(ValueError, match="INV-001") as unique_elsewhere:
        solver.choose_givens(_SIX_SWITCHES, eight.rows, eight.columns, cap=50)
    assert "its solution" in str(unique_elsewhere.value)
    assert "no solution" not in str(unique_elsewhere.value)

    unsatisfiable: tuple[tuple[int, ...], ...] = ((3,),) + ((0,),) * 11
    assert solver.solve(unsatisfiable, ((0,),) * 12).solution_count == 0
    with pytest.raises(ValueError, match="INV-001") as no_solution:
        solver.choose_givens(_PLUS, unsatisfiable, ((0,),) * 12, cap=50)
    assert "no solution" in str(no_solution.value)


def test_the_chooser_honours_the_cooperative_deadline() -> None:
    """ADR-0011 through the chooser: a passed deadline ends it, with no verdict.

    The chooser makes up to ``cap + 1`` solves and reads no clock of its own —
    it hands the request's one absolute instant to each of them, and the
    solver's own checkpoints raise. What matters at this boundary is that the
    timeout travels *out*: a reveal policy that caught it would retry a request
    whose budget is already spent, and ``SolverTimeout`` is deliberately not a
    ``GenerationAbandoned``, so the policy's ``except`` clause in ``generate``
    cannot swallow it even by accident.
    """
    assert not issubclass(SolverTimeout, GenerationAbandoned)

    grid_clues = clues.compute_clues(_SIX_SWITCHES)
    with pytest.raises(SolverTimeout):
        solver.choose_givens(
            _SIX_SWITCHES,
            grid_clues.rows,
            grid_clues.columns,
            cap=7,
            deadline=time.monotonic() - 1.0,
        )


# --------------------------------------------------------------------------
# AC-4 — TestGivenCells_RefusesBeyondTheCap
# --------------------------------------------------------------------------


def test_given_cells_refuses_beyond_the_cap() -> None:
    """The refusal: more reveals than the cap allows, so no puzzle, and the
    error names the cap.

    The message is checked because a cap the user cannot see is an internal
    limit rather than a judgement, and this error's whole job is to say "the
    picture was left alone on purpose".
    """
    with pytest.raises(GivenCellsCapExceeded) as refusal:
        _choose(_EIGHT_SWITCHES, cap=7)

    message = str(refusal.value)
    assert "7" in message, message
    assert "cap" in message, message


def test_given_cells_refuses_beyond_the_cap_through_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same refusal through the whole pipeline, with the flag set.

    The run spends its own recovery first — image mode's five nudges — and only
    then tries to reveal, so this also pins that the refusal comes *after* the
    existing policy rather than instead of it.
    """
    source = _CountingSource(_EIGHT_SWITCHES)
    _install_source(monkeypatch, source)
    puzzles = _capture_puzzles(monkeypatch)

    with pytest.raises(GivenCellsCapExceeded):
        generate(_image_request(reveal_given_cells=True))

    assert source.candidates_requested == 1, "the picture was never re-sourced"
    assert puzzles[0].nudge.attempts == MAX_NUDGE_ATTEMPTS
    assert puzzles[0].ready_for_export is False
    assert puzzles[0].givens is None, (
        "a refused run must leave no revealed cells on the aggregate"
    )


def test_the_cap_refusal_is_grouped_with_the_other_no_puzzle_failures() -> None:
    """AC-4's CLI half: ``exit_code_for``'s MRO walk maps the new error to
    ``GENERATION_FAILED``, with no new row in the table.

    That grouping is the point rather than the code: the enum groups by what
    the user has to do, and "the run did not produce a usable puzzle" is the
    same thing to do about an exhausted retry bound, a timed-out solve and a
    picture that needed too much of its answer given away.
    """
    assert issubclass(GivenCellsCapExceeded, GenerationAbandoned)
    assert issubclass(GivenCellsCapExceeded, NonogramError)
    assert cli.exit_code_for(GivenCellsCapExceeded("too many")) == (
        cli.ExitCode.GENERATION_FAILED
    )
    assert cli.exit_code_for(GivenCellsCapExceeded("too many")) == (
        cli.exit_code_for(GenerationAbandoned("gave up"))
    )


def test_the_cap_is_five_percent_of_the_grid_over_the_whole_size_range() -> None:
    """The cap's numbers, pinned at the ends of CON-011's range.

    A share and not a count, because five revealed cells is a hint on a 10x10
    and invisible on a 30x30 — and floored integer arithmetic, so there is no
    rounding mode to get wrong.
    """
    assert MAX_GIVEN_CELL_SHARE_PERCENT == 5
    assert given_cells_cap([[False] * 10 for _ in range(10)]) == 5
    assert given_cells_cap([[False] * 20 for _ in range(20)]) == 20
    assert given_cells_cap([[False] * 30 for _ in range(30)]) == 45
    assert given_cells_cap([[False] * 30 for _ in range(10)]) == 15
    assert given_cells_cap([]) == 0


# --------------------------------------------------------------------------
# Scripted sources and captured aggregates (the test_nudge.py shapes)
# --------------------------------------------------------------------------


class _CountingSource:
    """A grid source that reports how many candidates were asked of it.

    Image mode must never ask for a second candidate, and the count is how
    that is observed — a nudge is an edit to the first, and a *reveal* is not
    even that.
    """

    def __init__(self, grid: Grid) -> None:
        self.grid = grid
        self.candidates_requested = 0

    def __call__(self, *arguments: object) -> Grid:
        self.candidates_requested += 1
        return [row[:] for row in self.grid]


def _install_source(
    monkeypatch: pytest.MonkeyPatch, source: _CountingSource
) -> None:
    monkeypatch.setattr(orchestrator.sourcing, "for_mode", lambda mode: source)


def _capture_puzzles(monkeypatch: pytest.MonkeyPatch) -> list[orchestrator.Puzzle]:
    """Collect every aggregate ``generate`` builds, for a run that raises."""
    built: list[orchestrator.Puzzle] = []
    real_puzzle = orchestrator.Puzzle

    def capturing(*args: object, **kwargs: object) -> orchestrator.Puzzle:
        puzzle = real_puzzle(*args, **kwargs)  # type: ignore[arg-type]
        built.append(puzzle)
        return puzzle

    monkeypatch.setattr(orchestrator, "Puzzle", capturing)
    return built


def _image_request(**overrides: object) -> GenerationRequest:
    """An image-mode request over a scripted source.

    ``binarisation`` stays ``None`` on the aggregate, since the source in use
    is not ``sourcing.image.generate`` — the conversion never happens.
    """
    fields: dict[str, object] = {
        "mode": "image",
        "image": _FIXTURE_IMAGE,
        "width": 12,
        "height": 12,
        "seed": 1,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


def _random_request(**overrides: object) -> GenerationRequest:
    fields: dict[str, object] = {
        "mode": "random",
        "width": 12,
        "height": 12,
        "density": 20,
        "seed": 3,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# AC-3 — TestGenerate_RevealPolicyNeverChangesTheGrid
# --------------------------------------------------------------------------


def test_generate_reveal_policy_never_changes_the_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The criterion: with the flag set, an image whose nudge bound is spent is
    accepted **cell-for-cell as it converted**, with the uniqueness coming from
    the revealed cells.

    Three assertions and each one is load-bearing. The grid is compared against
    the conversion cell by cell — not "differs in few cells", *equal* — which
    is the promise the owner's complaint is about. The verdict is 1 and the
    export gate is open, so this is a real puzzle and not an accepted failure.
    And the five nudges were still spent first: the picture-preserving remedy is
    the last one tried, not the cheap one tried first.
    """
    source = _CountingSource(_SIX_SWITCHES)
    _install_source(monkeypatch, source)

    puzzle = generate(_image_request(reveal_given_cells=True))

    assert puzzle.grid == _SIX_SWITCHES
    assert puzzle.clues == clues.compute_clues(_SIX_SWITCHES)
    assert puzzle.solution_count == 1
    assert puzzle.ready_for_export is True
    assert puzzle.nudge.attempts == MAX_NUDGE_ATTEMPTS
    assert source.candidates_requested == 1

    revealed = solver.revealed_cells(puzzle.givens)
    assert len(revealed) == 6
    for row, column, value in revealed:
        assert value == _SIX_SWITCHES[row][column]

    # The accepted puzzle is unique *given* those cells, re-checked here by an
    # independent solve: INV-002's clause, as a test rather than as a claim.
    assert _solve(puzzle.grid, puzzle.givens).solution_count == 1
    assert _solve(puzzle.grid).solution_count == solver.MANY


def test_generate_without_the_flag_still_abandons_the_same_picture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-5 at this card's own boundary: the flag off is the old behaviour.

    The same scripted conversion as the test above, the same five nudges, and
    the same ``GenerationAbandoned`` the pipeline has always raised — with no
    ``GivenCellsCapExceeded``, no reveal and no givens anywhere. The pair of
    tests is the evidence that the flag, and nothing else, is what changed.
    """
    source = _CountingSource(_SIX_SWITCHES)
    _install_source(monkeypatch, source)
    puzzles = _capture_puzzles(monkeypatch)

    with pytest.raises(GenerationAbandoned) as abandoned:
        generate(_image_request())

    assert type(abandoned.value) is GenerationAbandoned
    assert puzzles[0].nudge.attempts == MAX_NUDGE_ATTEMPTS
    assert puzzles[0].givens is None


def test_the_reveal_policy_does_not_fire_while_the_nudge_can_still_help(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A conversion one nudge away from a puzzle is nudged, not revealed.

    The ordering guarantee from the other side: the policy is a last resort, so
    a picture the existing remedy can fix must come back *changed and with
    nothing given away* rather than unchanged and pre-filled. Without this, a
    flag meant to rescue hopeless pictures would quietly start giving away
    cells of the easy ones.
    """
    source = _CountingSource(_ONE_SWITCH)
    _install_source(monkeypatch, source)

    puzzle = generate(_image_request(reveal_given_cells=True))

    assert puzzle.ready_for_export is True
    assert puzzle.givens is None
    assert puzzle.nudge.attempts == 1
    assert puzzle.grid != _ONE_SWITCH, "the nudge is what fixed this one"


def test_the_reveal_policy_keeps_the_random_mode_retry_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Random mode: every redraw and every repair first, then the first draw
    revealed — and INV-003's bound is untouched.

    The numbers are the point. The regenerate counter stops at
    :data:`MAX_RETRY_ATTEMPTS` exactly, as it did before this card (ADR-0024/R2
    is not relaxed and the reveal policy advances no counter of its own), the
    repairs ADR-0024 prescribes all happened, and the grid finally accepted is
    the **first** one drawn rather than the last one repaired — which is what
    makes this a picture-preserving remedy in a mode that has a repairing one.
    """
    source = _CountingSource(_SIX_SWITCHES)
    _install_source(monkeypatch, source)

    puzzle = generate(_random_request(reveal_given_cells=True))

    assert puzzle.regenerate.attempts == MAX_RETRY_ATTEMPTS
    assert puzzle.regenerate.attempts <= puzzle.regenerate.bound
    assert puzzle.recovery.repairs > 0, "POL-006 still ran its lineages"
    assert puzzle.grid == _SIX_SWITCHES
    assert len(solver.revealed_cells(puzzle.givens)) == 6
    assert puzzle.ready_for_export is True


def test_the_reveal_policy_does_not_rescue_a_missed_difficulty_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run abandoned for a *tier* miss stays abandoned.

    Revealing cells is a uniqueness remedy, exactly as POL-002's nudge is
    ("a conversion that is unique but misses the requested tier is not
    nudged"). A conversion that is already unique needs no reveal, so the
    chooser returns nothing and the original abandonment is re-raised rather
    than a puzzle being accepted for a tier it does not have — which would be
    the flag silently widening what ``--difficulty`` means.
    """
    source = _CountingSource(_PLUS)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned) as abandoned:
        generate(_image_request(difficulty="hard", reveal_given_cells=True))

    assert type(abandoned.value) is GenerationAbandoned
    assert "tier" in str(abandoned.value) or "difficulty" in str(abandoned.value)
