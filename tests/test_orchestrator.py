"""COMP-002 tests: the generation pipeline, its aggregate and its retry bound.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-018  TestRegenerate_FiresOnUniquenessFailure -> test_regenerate_fires_on_uniqueness_failure*
    AC-019  TestRegenerate_StopsAtMaxRetryBound     -> test_regenerate_stops_at_max_retry_bound*
    AC-039  TestRetryLoop_BoundedIterations         -> test_retry_loop_bounded_iterations*
    AC-111  TestRecovery_RepairFlipsOnePairInsideUndecidedMask
    AC-132  TestRecovery_RepairLeavesCellsOutsideMaskUntouched
    AC-112  TestRecovery_RecoveredGridIsReverifiedBySolver
    AC-113  TestRecovery_RepairAttemptsCountAgainstRetryBound
    AC-114  TestRecovery_RepairKeepsFilledCountExact
    AC-A/B/C/D (CARD-074)                            -> the TestRecovery_* section
                                                        at the end of this file

The invariants this module is the single enforcement point for (ADR-0007) are
covered directly rather than incidentally: INV-002 (the export gate) in the
"aggregate" section, INV-003 (the retry bound) in the "retry primitive"
section, INV-001 (clues track the grid) where the candidate is recorded.

Two styles of test appear side by side on purpose.

*Scripted* tests replace the mode's grid source with a fixed sequence of
hand-drawn grids and let the **real** clue derivation and the **real** solver
judge them. That keeps the loop's behaviour exactly reproducible without ever
faking the uniqueness verdict the loop turns on — faking it would test the
mock, and guardrail G-3 says the verdict is the solver's.

*Pinned-seed* tests run the whole pipeline unmocked at a seed chosen so that a
real random grid needs (or never gets) a real regeneration. They are the
evidence that the composition works end to end; the scripted tests are the
evidence that it works for the reason claimed. A pinned seed that stops
behaving as its comment describes should be re-pinned by re-running the sweep
the comment names, not deleted.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from nonogram import difficulty, errors, orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import (
    ExportRejected,
    GenerationAbandoned,
    InvalidDensity,
    NonogramError,
    SizeOutOfRange,
    SolverTimeout,
)
from nonogram.orchestrator import (
    MAX_REGENERATE_ATTEMPTS,
    GenerationRequest,
    Puzzle,
    RetryCounter,
    generate,
    run_bounded,
)
from nonogram.solver import MANY, SolveResult, SolveSignals, solve

# --------------------------------------------------------------------------
# Helpers — same notation as tests/test_clues.py: ``█`` filled, ``·`` empty.
# --------------------------------------------------------------------------

_FILLED = "█"
_EMPTY = "·"


def _grid(*patterns: str) -> list[list[bool]]:
    for pattern in patterns:
        assert set(pattern) <= {_FILLED, _EMPTY}, f"bad pattern glyph in {pattern!r}"
    return [[glyph == _FILLED for glyph in pattern] for pattern in patterns]


#: Two solutions, so the uniqueness check rejects it: its clues are all ``(1,)``
#: in both directions, which the opposite diagonal satisfies just as well.
#:
#:     █·
#:     ·█
AMBIGUOUS = _grid("█·", "·█")

#: The same shape mirrored — a *different* grid with the same ambiguous clues,
#: used where a test has to show that a discarded candidate was really replaced.
#:
#:     ·█
#:     █·
ALSO_AMBIGUOUS = _grid("·█", "█·")

#: Exactly one solution. Row 0 is forced by ``(2,)``; column 0's ``(2,)`` then
#: forces row 1's single filled cell into column 0.
#:
#:     ██
#:     █·
UNIQUE = _grid("██", "█·")


def _verdict(solution_count: int) -> SolveResult:
    """A solver result with a chosen count — for the two paths no real grid
    can produce (``0`` solutions) or that CARD-006 will add (a timeout)."""
    return SolveResult(
        solution_count=solution_count,
        solution=None,
        signals=SolveSignals(
            line_logic_cells=0,
            total_cells=0,
            branch_nodes=0,
            backtracks=0,
            elapsed_seconds=0.0,
        ),
    )


class _ScriptedSource:
    """Stands in for one sourcing mode: hands out pre-written grids in order.

    Records every call so a test can assert *how many* candidates the loop
    asked for and that they all drew from the same injected ``Random``.
    """

    def __init__(self, *grids: list[list[bool]], repeat_last: bool = False) -> None:
        self._grids = list(grids)
        self._repeat_last = repeat_last
        self.calls: list[tuple[int | None, int | None, int | None, random.Random]] = []

    def __call__(
        self,
        width: int | None,
        height: int | None,
        density: int | None,
        rng: random.Random,
    ) -> list[list[bool]]:
        self.calls.append((width, height, density, rng))
        index = min(len(self.calls) - 1, len(self._grids) - 1)
        if not self._repeat_last and len(self.calls) > len(self._grids):
            raise AssertionError(
                f"the loop asked for candidate {len(self.calls)} but the script "
                f"only has {len(self._grids)}"
            )
        return self._grids[index]

    @property
    def candidates_requested(self) -> int:
        return len(self.calls)


class _RaisingSource:
    """A grid source that fails instead of producing a candidate."""

    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    def __call__(
        self,
        width: int | None,
        height: int | None,
        density: int | None,
        rng: random.Random,
    ):
        self.calls += 1
        raise self._error


def _install_source(
    monkeypatch: pytest.MonkeyPatch, source: Callable[..., object]
) -> list[str]:
    """Point every mode at ``source``; return the list of modes looked up."""
    modes: list[str] = []

    def fake_for_mode(mode: str) -> Callable[..., object]:
        modes.append(mode)
        return source

    monkeypatch.setattr(orchestrator.sourcing, "for_mode", fake_for_mode)
    return modes


def _request(**overrides: object) -> GenerationRequest:
    """A minimal valid request; the scripted source ignores extent/density."""
    fields: dict[str, object] = {
        "mode": "random",
        "width": 10,
        "height": 10,
        "density": 50,
        "seed": 0,
    }
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


def _puzzle(**overrides: object) -> Puzzle:
    return Puzzle(request=_request(**overrides), seed=0)


def _without_repairs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn ADR-0024's repair step (POL-006) off for a scripted-source test.

    ``MAX_CONSECUTIVE_REPAIRS = 0`` is ADR-0024's own rollback switch: with it
    the recovery loop is exactly the pure-redraw loop POL-001 was before
    CARD-074, so the scripted grid sequence maps one-to-one onto attempts
    again. Every test that calls this is asserting POL-001's own behaviour —
    which candidate is kept, how many grids are drawn, where the bound stops —
    and would otherwise be asserting it *through* a repair lineage, which has
    its own coverage in the CARD-074 ``TestRecovery_*`` tests (both kinds of
    attempt against the same one counter, in tests/test_orchestrator.py) and in
    tests/property/test_recovery_bound.py.

    It is a real switch and not a test seam: the constant is read by
    :func:`nonogram.orchestrator.generate` on every run, and 0 is the value the
    card's rollback plan names.
    """
    monkeypatch.setattr(orchestrator, "MAX_CONSECUTIVE_REPAIRS", 0)


# --------------------------------------------------------------------------
# The Puzzle aggregate (AGG-001) — one instance per request, INV-001/INV-002
# --------------------------------------------------------------------------


def test_the_aggregate_carries_the_requests_attributes() -> None:
    """AGG-001's mode/extent/density are attributes of the one instance.

    The extent is two attributes, not one (ADR-0022/R1), and a rectangle here
    so that reading either from the wrong field would fail.
    """
    puzzle = _puzzle(mode="random", width=15, height=22, density=40)

    assert puzzle.mode == "random"
    assert (puzzle.width, puzzle.height) == (15, 22)
    assert puzzle.density == 40


def test_recording_a_candidate_keeps_the_clues_in_step_with_the_grid() -> None:
    """INV-001: clues always equal the run-length encoding of the grid.

    Grid and clues are written by one operation, so a second candidate cannot
    leave the first one's clues attached.
    """
    puzzle = _puzzle()

    first = puzzle.record_candidate(AMBIGUOUS)
    assert puzzle.grid is AMBIGUOUS
    assert first == compute_clues(AMBIGUOUS)
    assert puzzle.clues == compute_clues(AMBIGUOUS)

    second = puzzle.record_candidate(UNIQUE)
    assert puzzle.grid is UNIQUE
    assert second == compute_clues(UNIQUE)
    assert puzzle.clues == compute_clues(UNIQUE)


def test_a_fresh_aggregate_is_not_ready_for_export() -> None:
    """INV-002: the gate starts closed and no candidate has been judged."""
    puzzle = _puzzle()

    assert puzzle.ready_for_export is False
    assert puzzle.solution_count is None
    assert puzzle.grid is None
    assert puzzle.clues is None


@pytest.mark.parametrize(
    ("solution_count", "opens_gate"),
    [
        pytest.param(0, False, id="unsolvable"),
        pytest.param(1, True, id="unique"),
        pytest.param(MANY, False, id="many"),
    ],
)
def test_the_export_gate_opens_only_for_exactly_one_solution(
    solution_count: int, opens_gate: bool
) -> None:
    """INV-002 at its single enforcement point (ADR-0007)."""
    puzzle = _puzzle()
    puzzle.record_candidate(UNIQUE)

    accepted = puzzle.confirm_uniqueness(solution_count)

    assert accepted is opens_gate
    assert puzzle.ready_for_export is opens_gate
    # The solver's number is stored as given, never re-derived (G-3).
    assert puzzle.solution_count == solution_count


def test_recording_the_next_candidate_closes_the_gate_again() -> None:
    """A verified candidate does not vouch for the one that replaces it."""
    puzzle = _puzzle()
    puzzle.record_candidate(UNIQUE)
    puzzle.confirm_uniqueness(1)
    assert puzzle.ready_for_export is True

    puzzle.record_candidate(AMBIGUOUS)

    assert puzzle.ready_for_export is False
    assert puzzle.solution_count is None


def test_the_export_gate_rejects_an_unverified_puzzle() -> None:
    """INV-002 as the export cards will call it (COMP-007 -> this gate)."""
    puzzle = _puzzle()
    puzzle.record_candidate(AMBIGUOUS)
    puzzle.confirm_uniqueness(MANY)

    with pytest.raises(ExportRejected) as excinfo:
        puzzle.require_ready_for_export()

    assert "uniqueness" in str(excinfo.value)


def test_the_export_gate_passes_a_verified_puzzle() -> None:
    puzzle = _puzzle()
    puzzle.record_candidate(UNIQUE)
    puzzle.confirm_uniqueness(1)

    puzzle.require_ready_for_export()  # does not raise


def test_one_aggregate_spans_every_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """AGG-001 is not re-created per retry — which is why INV-003's counter
    is one invariant on one instance rather than a per-attempt tally."""
    source = _ScriptedSource(AMBIGUOUS, ALSO_AMBIGUOUS, AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    puzzle = generate(_request())

    # A per-retry aggregate would have come back reporting a single attempt.
    assert puzzle.regenerate.attempts == 4
    assert source.candidates_requested == 4
    assert puzzle.grid == UNIQUE
    assert puzzle.request == _request()


# --------------------------------------------------------------------------
# The pipeline: source -> clues -> uniqueness -> ready (FR-007)
# --------------------------------------------------------------------------


def test_the_pipeline_produces_a_verified_puzzle_end_to_end() -> None:
    """The unmocked composition of CARD-003, CARD-002 and CARD-004.

    Pinned seed: at 10x10 / 50% density, seed 0's first candidate is already
    unique (sweep: seeds 0..11 all converge within four attempts).
    """
    puzzle = generate(_request(width=10, height=10, density=50, seed=0))

    assert puzzle.ready_for_export is True
    assert puzzle.solution_count == 1
    assert puzzle.regenerate.attempts == 1
    assert puzzle.grid is not None
    assert len(puzzle.grid) == 10
    assert all(len(row) == 10 for row in puzzle.grid)
    # INV-001, and an independent re-check of the verdict the loop acted on.
    assert puzzle.clues == compute_clues(puzzle.grid)
    assert solve(*compute_clues(puzzle.grid)).solution_count == 1


def test_the_same_seed_reproduces_the_same_run() -> None:
    """ADR-0015: one injected Random, so a seed replays the whole run."""
    first = generate(_request(seed=4242))
    second = generate(_request(seed=4242))

    assert first.grid == second.grid
    assert first.clues == second.clues
    assert first.regenerate.attempts == second.regenerate.attempts
    assert first.seed == second.seed == 4242


def test_a_different_seed_gives_a_different_run() -> None:
    """The reproducibility above is the seed's doing, not a constant grid."""
    assert generate(_request(seed=1)).grid != generate(_request(seed=2)).grid


def test_an_absent_seed_is_drawn_and_recorded_for_replay() -> None:
    """ADR-0015: without --seed one is drawn, and the run stays reproducible
    after the fact because the aggregate carries the effective seed."""
    unseeded = generate(_request(seed=None))

    assert isinstance(unseeded.seed, int)
    assert unseeded.request.seed is None
    replay = generate(_request(seed=unseeded.seed))
    assert replay.grid == unseeded.grid


def test_two_unseeded_runs_do_not_share_a_seed() -> None:
    """The drawn seed comes from entropy, not from a fixed fallback."""
    seeds = {generate(_request(seed=None)).seed for _ in range(5)}

    assert len(seeds) == 5


def test_every_attempt_draws_from_the_one_injected_random(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0015: the same Random instance is threaded through the whole run,
    so *which* candidates get discarded is reproducible too, not just the
    first one."""
    source = _ScriptedSource(AMBIGUOUS, AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    generate(_request(seed=7))

    rngs = [rng for *_, rng in source.calls]
    assert len(rngs) == 3
    assert all(rng is rngs[0] for rng in rngs)
    assert isinstance(rngs[0], random.Random)
    # Seeded from the request, not from global state.
    assert rngs[0].random() == random.Random(7).random()


def test_the_mode_selects_the_grid_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """The dispatch is COMP-003's (sourcing.for_mode), resolved once."""
    source = _ScriptedSource(UNIQUE)
    modes = _install_source(monkeypatch, source)

    generate(_request(mode="random"))

    assert modes == ["random"]


def test_the_requested_size_and_density_reach_the_grid_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _ScriptedSource(UNIQUE)
    _install_source(monkeypatch, source)

    generate(_request(width=12, height=25, density=35))

    assert [call[:3] for call in source.calls] == [(12, 25, 35)]


def test_cli_rectangular_request_produces_width_by_height_grid() -> None:
    """AC-085 / TestCLI_RectangularRequestProducesWidthByHeightGrid (happy).

    A pinned-seed test, in this module rather than ``tests/test_cli.py``,
    despite the ``TestCLI_`` prefix requirements.yml gives it: the criterion's
    *given* is "a GenerationRequest carrying width 30 and height 20" and its
    *when* is "generation runs to completion", which is COMP-002's seam, not
    argv's. ``captured_requests`` in the CLI module deliberately stubs the
    pipeline out (see its docstring), so the criterion is unassertable there.

    The sibling test above pins the extent going *in* to the source, through a
    scripted one; this pins the shape coming *out* of a real, unmocked run. A
    transposition anywhere downstream of ``_source_arguments`` — in the
    aggregate, the clue derivation, or the solver round trip — survives that
    test and fails this one. The clue lengths are asserted for the same reason:
    a swap that left the grid alone but derived clues against the transpose
    would otherwise pass on the grid assertions alone.

    Density 70, not the default: at 30x20 the mid-range densities cannot
    produce a uniquely-solvable grid within the retry bound at all — every seed
    tried abandoned after 20 attempts, taking 7-30s each (measured 2026-09-02;
    0/3 seeds at densities 10, 15, 20, 30 and 35, 3/3 at 60 and above). That is
    a real product limit, filed as its own backlog item; it is not this test's
    subject, so the density here is chosen to stay clear of it.
    """
    puzzle = generate(
        GenerationRequest(mode="random", width=30, height=20, density=70, seed=0)
    )

    assert puzzle.grid is not None
    assert len(puzzle.grid) == 20
    assert {len(row) for row in puzzle.grid} == {30}

    assert len(puzzle.clues.rows) == 20
    assert len(puzzle.clues.columns) == 30


def test_an_unknown_mode_fails_before_any_candidate_is_sourced() -> None:
    """A wiring bug must not be reported as 20 infeasible candidates.

    ``image`` was the stand-in for an unregistered mode until CARD-015
    registered it; the case is about a mode that is not in the dispatch table
    at all, so it is now a made-up one. (A mode that *is* registered but has no
    argument list is the sibling wiring bug, covered in
    ``tests/test_sourcing_image.py``.)
    """
    with pytest.raises(ValueError, match="unknown grid sourcing mode"):
        generate(_request(mode="webcam"))


def test_a_run_writes_no_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CON-003 / guardrail G-4: the aggregate is in-memory only."""
    monkeypatch.chdir(tmp_path)
    source = _ScriptedSource(AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)

    generate(_request(out=tmp_path, export_formats=("json",)))

    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------
# What is a retry, and what is not (the failure matrix)
# --------------------------------------------------------------------------


def test_an_invalid_request_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid request does not become valid by being asked 20 times.

    Two shapes of invalid, because since CARD-033 they are caught in two
    different places and only one of them reaches the source at all.

    An out-of-range *extent* is refused while the extent is resolved: FR-023's
    derivation has to know the requested extent is usable before it decides
    anything from it (and, in image mode, before it decodes a file), so it asks
    the same shared validator the sources ask and refuses first. The source is
    therefore called **zero** times — strictly better than once, and asserted as
    zero rather than loosened to "fewer than 20", because "not retried" is a
    weaker claim than "not reached".

    An invalid *density* is not the extent's business and still travels out of
    the source itself, on its first and only call. That half is what keeps this
    test about the retry rule rather than about validation placement: an
    exception from sourcing ends the run, whichever exception it is.
    """
    extent_source = _RaisingSource(SizeOutOfRange("grid width must be 10..30"))
    _install_source(monkeypatch, extent_source)

    with pytest.raises(SizeOutOfRange):
        generate(_request(width=60, height=60))

    assert extent_source.calls == 0

    density_source = _RaisingSource(InvalidDensity("density must be 0..100"))
    _install_source(monkeypatch, density_source)

    with pytest.raises(InvalidDensity):
        generate(_request(width=20, height=20, density=150))

    assert density_source.calls == 1


def test_an_invalid_size_reaches_the_domain_check_unmocked() -> None:
    """The same path with the real sourcing module (ADR-0010: validation is
    inward of the CLI, so a missing --size is rejected here)."""
    with pytest.raises(SizeOutOfRange):
        generate(_request(width=None, height=None))


def test_a_solver_timeout_is_not_treated_as_a_uniqueness_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CARD-006 adds the deadline (guardrail G-5); this pins the loop's side
    of the contract now, so a timeout can never be silently retried 20 times.

    A timeout says nothing about the candidate — it says the run is out of
    time — and ADR-0002's attempt bound and ADR-0001's time budget are meant
    to operate independently.
    """
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)

    def timing_out(rows: object, columns: object, **_: object) -> SolveResult:
        # ``**_`` absorbs the ``deadline=`` keyword CARD-006 added to
        # ``solver.solve``. This test predates it and pins the *loop's* side of
        # the contract, which is unchanged by how the solver learns the
        # deadline; the assertion below is untouched.
        raise SolverTimeout("deadline exceeded")

    monkeypatch.setattr(orchestrator.solver, "solve", timing_out)

    with pytest.raises(SolverTimeout):
        generate(_request())

    assert source.candidates_requested == 1


def test_a_zero_solution_verdict_is_retried_like_a_many_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POL-001 fires on ``solution_count != 1``, not on "more than one".

    No real grid yields 0 solutions (it is a solution of its own clues), so
    this path is only reachable by handing the loop the verdict directly.
    """
    source = _ScriptedSource(AMBIGUOUS, AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    counts = iter([0, 0, 1])
    monkeypatch.setattr(
        # ``**_`` absorbs CARD-006's ``deadline=`` keyword — see the note on
        # ``timing_out`` above.
        orchestrator.solver, "solve", lambda rows, columns, **_: _verdict(next(counts))
    )

    puzzle = generate(_request())

    assert puzzle.regenerate.attempts == 3
    assert puzzle.ready_for_export is True


# --------------------------------------------------------------------------
# AC-018 (POL-001) — TestRegenerate_FiresOnUniquenessFailure
# --------------------------------------------------------------------------


def test_regenerate_fires_on_uniqueness_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate the solver reports as non-unique is discarded and a new one
    is sourced and re-checked, with no user interaction."""
    source = _ScriptedSource(AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    def no_prompting(*args: object, **kwargs: object) -> str:
        raise AssertionError("the regenerate policy must not ask the user anything")

    monkeypatch.setattr("builtins.input", no_prompting)

    puzzle = generate(_request())

    assert source.candidates_requested == 2
    assert puzzle.regenerate.attempts == 2
    assert puzzle.grid == UNIQUE
    assert puzzle.solution_count == 1
    assert puzzle.ready_for_export is True


def test_regenerate_fires_on_uniqueness_failure_repeatedly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The policy is a loop, not a single second chance."""
    source = _ScriptedSource(AMBIGUOUS, AMBIGUOUS, ALSO_AMBIGUOUS, AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    puzzle = generate(_request())

    assert source.candidates_requested == 5
    assert puzzle.regenerate.attempts == 5


def test_regenerate_discards_the_failed_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """"Discard" means the rejected grid is gone, not merely re-judged."""
    source = _ScriptedSource(ALSO_AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    puzzle = generate(_request())

    assert puzzle.grid == UNIQUE
    assert puzzle.grid != ALSO_AMBIGUOUS
    assert puzzle.clues == compute_clues(UNIQUE)


def test_regenerate_fires_on_a_real_random_candidate() -> None:
    """The same policy with nothing mocked.

    Pinned seed: at 10x10 / 50% density, seed 1's first candidates are not
    uniquely solvable and the loop converges on the third (sweep over seeds
    0..11: 1, 3, 4, 2, 2, 1, 4, 4, 1, 2, 2, 1 attempts).
    """
    puzzle = generate(_request(width=10, height=10, density=50, seed=1))

    assert puzzle.regenerate.attempts > 1
    assert puzzle.ready_for_export is True
    assert solve(*compute_clues(puzzle.grid)).solution_count == 1


# --------------------------------------------------------------------------
# AC-019 (INV-003, POL-005) — TestRegenerate_StopsAtMaxRetryBound
# --------------------------------------------------------------------------


def test_the_regenerate_bound_is_the_adr_0002_value() -> None:
    """ADR-0002/R1 (CARD-090): 30, measured, not ADR-0002's original guess of 20.

    The pin is the point. The constant and the ADR are meant to move together,
    so a future retune that edits one and not the other fails here rather than
    leaving an accepted decision describing a number the code stopped using.
    """
    assert MAX_REGENERATE_ATTEMPTS == 30


def test_regenerate_stops_at_max_retry_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At the bound the run is abandoned with a clear error, not retried."""
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_request())

    assert source.candidates_requested == MAX_REGENERATE_ATTEMPTS
    message = str(excinfo.value)
    assert str(MAX_REGENERATE_ATTEMPTS) in message
    assert "regenerate" in message
    assert "one solution" in message


def test_an_abandoned_run_reports_a_domain_error() -> None:
    """GenerationAbandoned is a NonogramError, so the adapter maps it onto an
    exit code instead of letting a traceback reach the user."""
    assert issubclass(GenerationAbandoned, NonogramError)


def test_regenerate_stops_at_max_retry_bound_for_a_real_request() -> None:
    """The same bound with nothing mocked — repairs included (AC-113).

    Pinned seed: at 10x10 / 30% density, seed 3's twenty attempts — redraws
    and ADR-0024 repairs together — never reach a uniquely-solvable candidate
    (sweep over seeds 0..11 with the repair step live: seeds 3, 4, 5, 6, 9 and
    11 exhaust the budget). Re-pinned by CARD-074: the previous pin, seed 0,
    now *succeeds* on its nineteenth attempt after fourteen repairs, which is
    the change ADR-0024 makes and not a regression — its Negative section says
    in as many words that every seed that ever hit MANY maps to a different
    accepted grid. Re-pin by re-running the sweep, not by deleting the test.
    """
    with pytest.raises(GenerationAbandoned):
        generate(_request(width=10, height=10, density=30, seed=3))


def test_an_abandoned_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The abandonment path leaves no partial artefact behind (G-4)."""
    monkeypatch.chdir(tmp_path)
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)
    _without_repairs(monkeypatch)

    with pytest.raises(GenerationAbandoned):
        generate(_request(out=tmp_path))

    assert list(tmp_path.iterdir()) == []


# --------------------------------------------------------------------------
# AC-039 (INV-003) — TestRetryLoop_BoundedIterations, the shared primitive
# --------------------------------------------------------------------------


class _Attempts:
    """An attempt callable that succeeds on a chosen attempt number."""

    def __init__(self, succeed_on: int | None = None) -> None:
        self._succeed_on = succeed_on
        self.calls = 0

    def __call__(self) -> str | None:
        self.calls += 1
        return "candidate" if self.calls == self._succeed_on else None


@pytest.mark.parametrize(
    "bound",
    [
        pytest.param(1, id="single-attempt"),
        pytest.param(5, id="the-adr-0002-nudge-cap"),
        pytest.param(MAX_REGENERATE_ATTEMPTS, id="the-adr-0002-retry-bound"),
    ],
)
def test_retry_loop_bounded_iterations(bound: int) -> None:
    """A loop whose candidates never pass stops after exactly ``bound``
    attempts and reports a clear failure instead of looping indefinitely."""
    counter = RetryCounter("regenerate", bound)
    attempts = _Attempts()

    with pytest.raises(GenerationAbandoned) as excinfo:
        run_bounded(counter, attempts, reason="nothing passed")

    assert attempts.calls == bound
    assert counter.attempts == bound
    assert counter.exhausted is True
    assert str(bound) in str(excinfo.value)


def test_retry_loop_bounded_iterations_never_exceeds_the_bound() -> None:
    """INV-003 as a property over every bound and every outcome shape."""
    for bound in range(0, 26):
        for succeed_on in (None, 1, bound, bound + 1, 2 * bound):
            counter = RetryCounter("regenerate", bound)
            attempts = _Attempts(succeed_on)
            try:
                run_bounded(counter, attempts, reason="nothing passed")
            except GenerationAbandoned:
                pass
            assert counter.attempts <= counter.bound
            assert attempts.calls == counter.attempts


def test_retry_loop_stops_at_the_first_success() -> None:
    """The bound is a ceiling, not a quota: a good candidate ends the loop."""
    counter = RetryCounter("regenerate", MAX_REGENERATE_ATTEMPTS)
    attempts = _Attempts(succeed_on=1)

    assert run_bounded(counter, attempts, reason="nothing passed") == "candidate"
    assert attempts.calls == 1
    assert counter.attempts == 1
    assert counter.exhausted is False


def test_retry_loop_accepts_a_success_on_the_last_allowed_attempt() -> None:
    """Off-by-one guard: the bound-th attempt is inside the budget."""
    counter = RetryCounter("regenerate", MAX_REGENERATE_ATTEMPTS)
    attempts = _Attempts(succeed_on=MAX_REGENERATE_ATTEMPTS)

    assert run_bounded(counter, attempts, reason="nothing passed") == "candidate"
    assert counter.attempts == MAX_REGENERATE_ATTEMPTS
    assert counter.exhausted is True


def test_a_zero_bound_abandons_without_attempting_anything() -> None:
    counter = RetryCounter("regenerate", 0)
    attempts = _Attempts(succeed_on=1)

    with pytest.raises(GenerationAbandoned):
        run_bounded(counter, attempts, reason="nothing passed")

    assert attempts.calls == 0


def test_an_attempt_that_raises_still_consumes_its_budget() -> None:
    """An interrupted attempt is counted: a retry budget must not be refunded
    by a crash, or a repeatedly-failing attempt could loop forever."""
    counter = RetryCounter("regenerate", MAX_REGENERATE_ATTEMPTS)

    def explode() -> str | None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_bounded(counter, explode, reason="nothing passed")

    assert counter.attempts == 1


def test_the_counter_is_not_reset_between_loops() -> None:
    """The counter belongs to the aggregate, so its bound applies to the whole
    generation request rather than to one call of the primitive."""
    counter = RetryCounter("regenerate", 5)

    run_bounded(counter, _Attempts(succeed_on=2), reason="nothing passed")
    assert counter.attempts == 2

    later = _Attempts()
    with pytest.raises(GenerationAbandoned):
        run_bounded(counter, later, reason="nothing passed")

    assert later.calls == 3
    assert counter.attempts == 5


def test_the_abandonment_message_names_the_loop_and_the_bound() -> None:
    """POL-005's message has to read as "infeasible request", not "crash"."""
    counter = RetryCounter("pixel-nudge", 5)

    with pytest.raises(GenerationAbandoned) as excinfo:
        run_bounded(counter, _Attempts(), reason="the image never became unique")

    message = str(excinfo.value)
    assert "pixel-nudge" in message
    assert "5" in message
    assert "the image never became unique" in message


def test_a_counter_refuses_to_advance_past_its_bound() -> None:
    """INV-003 is a property of the counter type, not only of the loop that
    happens to use it — a hand-rolled caller cannot overshoot either."""
    counter = RetryCounter("regenerate", 1)

    assert counter.record_attempt() == 1
    with pytest.raises(RuntimeError, match="INV-003"):
        counter.record_attempt()

    assert counter.attempts == 1


# --------------------------------------------------------------------------
# CARD-074 / ADR-0024 — POL-006's repair, then POL-001's redraw
#
#   AC-111  TestRecovery_RepairFlipsOnePairInsideUndecidedMask
#   AC-132  TestRecovery_RepairLeavesCellsOutsideMaskUntouched
#   AC-112  TestRecovery_RecoveredGridIsReverifiedBySolver
#   AC-113  TestRecovery_RepairAttemptsCountAgainstRetryBound
#   AC-114  TestRecovery_RepairKeepsFilledCountExact
#   AC-A    TestRecovery_RedrawsAfterKConsecutiveRepairs
#   AC-B    TestRecovery_FallsBackToUndecidedMaskWhenNoPairInDisagreementSet
#   AC-C    TestRecovery_SameSeedReplaysSameRepairLineage
#   AC-D    TestRecovery_AbandonmentRateNotWorseThanPureRedraw
#
# The corpus-wide claims (EC-013, the rng-independence of the pair choice, the
# exact density of every repaired grid) live in
# tests/property/test_recovery_bound.py.
# --------------------------------------------------------------------------


def _ambiguous_at_forty_percent() -> list[list[bool]]:
    """AC-111's given: a 20x20 grid at density 40 whose solve reports MANY
    with a six-cell undecided mask.

    Constructed rather than sampled, and the reason is worth recording: a
    *drawn* 20x20 grid at density 40 is nowhere near line-solvable — a sweep of
    300 seeds found none with an undecided mask under thirteen cells, and a
    sixth of them could not be solved inside two seconds at all. A grid with a
    six-cell mask at that density has to be built.

    The build is a rigid part plus one gadget. Rows 0..7 filled edge to edge is
    160 cells, exactly 40% of 400, and every clue of it is forced: a row clue
    of ``(20)`` has one placement and a row clue of ``(0)`` has one placement,
    so line logic settles the whole grid. Three cells are then taken out of row
    7 and put back as isolated singles at (10, 0), (12, 0) and (14, 1) — which
    leaves the filled count at 160 and turns columns 0 and 1 into the clue pair
    the ambiguity lives in. The solver reports:

        undecided mask    (10,0) (10,1) (12,0) (12,1) (14,0) (14,1)  — six
        witnesses differ  (12,0) (12,1) (14,0) (14,1)                — four

    i.e. a disagreement set inside the mask, as EC-011 says, with the parent
    filled at (12, 0) and (14, 1) and empty at (12, 1) and (14, 0).
    """
    grid = [[False] * 20 for _ in range(20)]
    for row in range(8):
        for column in range(20):
            grid[row][column] = True
    for row, column in ((7, 0), (7, 1), (7, 2)):
        grid[row][column] = False
    for row, column in ((10, 0), (12, 0), (14, 1)):
        grid[row][column] = True
    return grid


def _solved(grid: list[list[bool]]) -> SolveResult:
    """The real solver's verdict on ``grid``'s own clues (CON-005)."""
    return solve(*compute_clues(grid))


def _cells(mask: list[list[bool]]) -> set[tuple[int, int]]:
    return {
        (row_index, column_index)
        for row_index, row in enumerate(mask)
        for column_index, cell in enumerate(row)
        if cell
    }


def _differences(
    before: list[list[bool]], after: list[list[bool]]
) -> set[tuple[int, int]]:
    return {
        (row_index, column_index)
        for row_index, (before_row, after_row) in enumerate(zip(before, after))
        for column_index, (was, now) in enumerate(zip(before_row, after_row))
        if was != now
    }


def _filled(grid: list[list[bool]]) -> int:
    return sum(sum(row) for row in grid)


def _capture_puzzles(monkeypatch: pytest.MonkeyPatch) -> list[Puzzle]:
    """Collect every aggregate :func:`generate` builds, abandoned runs included.

    A run that raises ``GenerationAbandoned`` never hands its puzzle back, so
    its counters and its ADR-0024 tally are otherwise unobservable — and they
    are exactly what AC-113 is about. The subclass changes no behaviour; it
    only keeps a reference.
    """
    created: list[Puzzle] = []
    real_puzzle = orchestrator.Puzzle

    class _Recorded(real_puzzle):  # type: ignore[valid-type,misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            created.append(self)

    monkeypatch.setattr(orchestrator, "Puzzle", _Recorded)
    return created


class _RepairRecorder:
    """Wrap ``orchestrator.repair_candidate`` and remember every call.

    The lineage a run took is otherwise invisible from outside: the aggregate
    keeps counts, not a history. Nothing is faked — the real function computes
    the real repair — so this observes the loop rather than replacing part of
    it.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        real: Callable[..., orchestrator.Repair | None],
    ) -> None:
        self._real = real
        self.calls: list[tuple[str, tuple[int, int], tuple[int, int]] | None] = []
        monkeypatch.setattr(orchestrator, "repair_candidate", self)

    def __call__(
        self, grid: list[list[bool]], **kwargs: object
    ) -> orchestrator.Repair | None:
        repair = self._real(grid, **kwargs)
        self.calls.append(
            None if repair is None else (repair.region, repair.emptied, repair.filled)
        )
        return repair


class _SolveRecorder:
    """Wrap ``orchestrator.solver.solve`` and remember the clues it was given.

    Again an observer over the real solver: every verdict the assertions turn
    on is the solver's own (guardrail G-3).
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._real = orchestrator.solver.solve
        self.clues: list[tuple[object, object]] = []
        monkeypatch.setattr(orchestrator.solver, "solve", self)

    def __call__(self, rows: object, columns: object, **kwargs: object) -> SolveResult:
        self.clues.append((rows, columns))
        return self._real(rows, columns, **kwargs)


# --- AC-111 / AC-132: what one repair does, and what it leaves alone --------


def test_repair_flips_one_pair_inside_the_undecided_mask() -> None:
    """AC-111: exactly one filled and one empty cell inside the mask swap.

    Both cells come from the witness-disagreement set, which is a subset of the
    mask (EC-011), so "inside that six-cell mask" holds for the primary region
    rule and for the fallback alike.
    """
    grid = _ambiguous_at_forty_percent()
    verdict = _solved(grid)
    mask = _cells(verdict.undecided_mask)

    assert verdict.solution_count == MANY
    assert len(mask) == 6

    repair = orchestrator.repair_candidate(
        grid, witnesses=verdict.witnesses, undecided_mask=verdict.undecided_mask
    )

    assert repair is not None
    changed = _differences(grid, repair.grid)
    assert len(changed) == 2
    assert changed <= mask
    assert changed == {repair.emptied, repair.filled}
    # One cell of each kind, which is the whole of ADR-0024/R3's flip rule.
    assert grid[repair.emptied[0]][repair.emptied[1]] is True
    assert repair.grid[repair.emptied[0]][repair.emptied[1]] is False
    assert grid[repair.filled[0]][repair.filled[1]] is False
    assert repair.grid[repair.filled[0]][repair.filled[1]] is True


def test_repair_leaves_every_cell_outside_the_mask_untouched() -> None:
    """AC-132: the repair is local to the region — 394 of the 400 cells of this
    grid cannot move, whatever the pair choice does."""
    grid = _ambiguous_at_forty_percent()
    verdict = _solved(grid)
    mask = _cells(verdict.undecided_mask)

    repair = orchestrator.repair_candidate(
        grid, witnesses=verdict.witnesses, undecided_mask=verdict.undecided_mask
    )

    assert repair is not None
    for row_index, row in enumerate(grid):
        for column_index, cell in enumerate(row):
            if (row_index, column_index) in mask:
                continue
            assert repair.grid[row_index][column_index] == cell


def test_the_pair_choice_is_deterministic_in_the_grid_and_the_witnesses() -> None:
    """ADR-0024/R4: same inputs, same pair — and host state does not enter.

    The global ``random`` module is re-seeded and drawn from between the two
    calls: a repair that consulted any source of randomness at all would have
    to disagree with itself here.
    """
    grid = _ambiguous_at_forty_percent()
    verdict = _solved(grid)

    random.seed(1)
    first = orchestrator.repair_candidate(
        grid, witnesses=verdict.witnesses, undecided_mask=verdict.undecided_mask
    )
    random.seed(999)
    for _ in range(10):
        random.random()
    second = orchestrator.repair_candidate(
        grid, witnesses=verdict.witnesses, undecided_mask=verdict.undecided_mask
    )

    assert first == second
    # The rank is (row, column) over the region: the first filled cell and the
    # first empty cell in row-major order.
    assert first is not None
    assert (first.emptied, first.filled) == ((12, 0), (12, 1))


# --- AC-114: the filled count, and so the density, is exact ----------------


def test_repair_keeps_the_filled_count_exact() -> None:
    """AC-114: five repairs in a row, every one of them 160 filled cells.

    The lineage is re-solved between repairs, as the loop does — each repair
    reads its own parent's witnesses — and the count is asserted after every
    one rather than only at the end, so two flips that cancelled out would
    still be caught.
    """
    grid = _ambiguous_at_forty_percent()
    assert _filled(grid) == 160

    for _ in range(5):
        verdict = _solved(grid)
        assert verdict.solution_count == MANY
        repair = orchestrator.repair_candidate(
            grid, witnesses=verdict.witnesses, undecided_mask=verdict.undecided_mask
        )
        assert repair is not None
        assert _filled(repair.grid) == 160
        assert len(_differences(grid, repair.grid)) == 2
        grid = repair.grid


# --- AC-B: the fallback region is a live path, not dead code ---------------


def test_falls_back_to_the_undecided_mask_when_the_disagreement_set_has_no_pair() -> (
    None
):
    """AC-B: a disagreement set holding no filled/empty pair of the parent.

    ADR-0024's per-row filled-count argument only applies when the candidate
    grid is itself one of the two witnesses. Often it is not — the witnesses
    are the first two solutions the search found, and the parent can be a third
    — and CARD-073's review measured nine cases out of 241 where every
    disagreeing cell was *empty* in the parent. This is that case, built by
    hand so the condition is exact rather than incidental: the witnesses differ
    only at (1, 1) and (1, 2), both empty in the parent, so there is no filled
    cell for the primary rule to empty.

    The wider mask does hold a pair, and the repair must take it rather than
    quietly degrading into a redraw.
    """
    grid = [
        [True, False, False, False],
        [False, False, False, False],
        [False, True, False, False],
        [False, False, False, False],
    ]
    first_witness = [
        [True, False, False, False],
        [False, True, False, False],
        [False, True, False, False],
        [False, False, False, False],
    ]
    second_witness = [
        [True, False, False, False],
        [False, False, True, False],
        [False, True, False, False],
        [False, False, False, False],
    ]
    # What line logic left open: the disagreeing pair, plus (0, 0) — filled in
    # the parent, and what makes the fallback region usable at all.
    undecided_mask = [
        [True, True, False, False],
        [False, True, True, False],
        [False, False, False, False],
        [False, False, False, False],
    ]

    disagreement = _differences(first_witness, second_witness)
    assert disagreement == {(1, 1), (1, 2)}
    assert all(grid[row][column] is False for row, column in disagreement)

    repair = orchestrator.repair_candidate(
        grid,
        witnesses=(first_witness, second_witness),
        undecided_mask=undecided_mask,
    )

    assert repair is not None
    assert repair.region == orchestrator.UNDECIDED_MASK_REGION
    assert (repair.emptied, repair.filled) == ((0, 0), (0, 1))
    assert _differences(grid, repair.grid) == {(0, 0), (0, 1)}
    assert _filled(repair.grid) == _filled(grid)


def test_the_disagreement_set_is_preferred_when_it_holds_a_pair() -> None:
    """The other side of AC-B: the fallback is a fallback, not the rule.

    Same parent, same mask, witnesses that disagree on a filled cell too — the
    pair now comes from the disagreement set, and the mask's extra cells are
    not consulted even though (0, 0) ranks first over the mask as a whole.
    """
    grid = [
        [True, False, False, False],
        [True, False, False, False],
        [False, True, False, False],
        [False, False, False, False],
    ]
    first_witness = [row[:] for row in grid]
    second_witness = [row[:] for row in grid]
    second_witness[1][0] = False
    second_witness[1][1] = True
    undecided_mask = [
        [True, True, False, False],
        [True, True, False, False],
        [False, False, False, False],
        [False, False, False, False],
    ]

    repair = orchestrator.repair_candidate(
        grid,
        witnesses=(first_witness, second_witness),
        undecided_mask=undecided_mask,
    )

    assert repair is not None
    assert repair.region == orchestrator.WITNESS_DISAGREEMENT_REGION
    assert (repair.emptied, repair.filled) == ((1, 0), (1, 1))


def test_a_region_with_nothing_to_flip_produces_no_repair() -> None:
    """Neither region holds a filled/empty pair: there is nothing to flip.

    The loop's answer is a redraw — POL-001, exactly as before — and the
    aggregate records that the lineage ended for want of a region rather than
    at the K cap, which are different facts about K's calibration.
    """
    grid = [[False, False], [False, False]]

    assert (
        orchestrator.repair_candidate(grid, witnesses=None, undecided_mask=None) is None
    )
    assert (
        orchestrator.repair_candidate(
            grid,
            witnesses=(
                [[False, False], [False, True]],
                [[False, True], [False, False]],
            ),
            undecided_mask=[[True, True], [True, True]],
        )
        is None
    )


# --- AC-112 / AC-113 / AC-A: the repair inside the one bounded loop --------


def test_a_recovered_grid_is_reverified_by_the_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-112 / ADR-0024/R1: a repaired candidate is accepted only on a fresh
    solver verdict of 1 on its own re-derived clues.

    Pinned seed, nothing mocked but the two observers: at 10x10 / 30% density
    seed 10 draws one grid, repairs it twice and accepts the second repair. So
    the accepted grid is *not* a grid the source ever produced, and the
    evidence that it was judged rather than assumed unique is that the solver
    was asked about its own clues — one solve per attempt, the last of them
    this grid's.
    """
    solves = _SolveRecorder(monkeypatch)
    drawn: list[list[list[bool]]] = []
    real_source = orchestrator.sourcing.for_mode("random")

    def recording_source(*args: object) -> list[list[bool]]:
        grid = real_source(*args)
        drawn.append([list(row) for row in grid])
        return grid

    monkeypatch.setattr(
        orchestrator.sourcing, "for_mode", lambda mode: recording_source
    )

    puzzle = generate(_request(width=10, height=10, density=30, seed=10))

    assert puzzle.recovery.repairs > 0
    assert puzzle.grid not in drawn  # the accepted grid is a repair
    assert len(solves.clues) == puzzle.regenerate.attempts
    accepted_clues = compute_clues(puzzle.grid)
    assert solves.clues[-1] == (accepted_clues.rows, accepted_clues.columns)
    assert puzzle.solution_count == 1
    assert puzzle.ready_for_export is True
    # And the verdict stands when the accepted grid is re-solved from scratch.
    assert _solved(puzzle.grid).solution_count == 1


class _RecoveryShape(NamedTuple):
    """How ADR-0024's interleave divides one exhausted retry budget.

    A lineage costs one redraw plus ``MAX_CONSECUTIVE_REPAIRS`` repairs, so the
    budget splits into whole lineages and at most one partial one. Every count
    below follows from the two constants; none of it is observation, which is
    why the tests derive it instead of pinning literals that are really a
    statement about the bound. CARD-090's retune (20 -> 30) broke four such
    literals at once, and this exists so the next one breaks none.
    """

    redraws: int
    repairs: int
    capped_lineages: int
    repeated: int


def _recovery_shape() -> _RecoveryShape:
    per_lineage = orchestrator.MAX_CONSECUTIVE_REPAIRS + 1
    full, remainder = divmod(MAX_REGENERATE_ATTEMPTS, per_lineage)
    redraws = full + (1 if remainder else 0)
    # A capped lineage re-judges a grid it has already seen on every repair but
    # its first; a partial lineage never reaches the cap to do so.
    return _RecoveryShape(
        redraws=redraws,
        repairs=MAX_REGENERATE_ATTEMPTS - redraws,
        capped_lineages=full,
        repeated=full * (orchestrator.MAX_CONSECUTIVE_REPAIRS - 1),
    )


def test_repair_attempts_count_against_the_retry_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-113 / ADR-0024/R2: one counter, both kinds of attempt, one bound.

    The scripted source hands back the same ambiguous 20x20 grid for ever, and
    its repair lineage is the pathological one K exists for: the pair choice
    swaps (12, 0) with (12, 1), the next solve locates the same ambiguity, and
    the repair swaps them back — the lineage oscillates between two grids and
    never converges. The bound's worth of attempts later the run is abandoned,
    and those attempts are drawn grids *plus* repairs, not that many of either.

    The counts are derived rather than pinned, because they are arithmetic, not
    observation: one lineage costs a redraw plus ``MAX_CONSECUTIVE_REPAIRS``
    repairs, so the budget divides into whole lineages and a possible partial
    one. Written as literals they were silently a statement about the bound, and
    CARD-090's retune (20 -> 30) broke all three of them at once.
    """
    shape = _recovery_shape()
    puzzles = _capture_puzzles(monkeypatch)
    source = _ScriptedSource(_ambiguous_at_forty_percent(), repeat_last=True)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned) as excinfo:
        generate(_request())

    puzzle = puzzles[-1]
    assert puzzle.regenerate.attempts == MAX_REGENERATE_ATTEMPTS
    assert puzzle.recovery.redraws == shape.redraws
    assert puzzle.recovery.repairs == shape.repairs
    assert puzzle.recovery.attempts == puzzle.regenerate.attempts
    assert puzzle.recovery.lineages_at_repair_cap == shape.capped_lineages
    assert puzzle.recovery.lineages_without_repairable_region == 0
    assert puzzle.recovery.repeated_attempts == shape.repeated
    assert source.candidates_requested == shape.redraws

    message = str(excinfo.value)
    assert str(MAX_REGENERATE_ATTEMPTS) in message
    assert "regenerate" in message
    assert "one solution" in message


def test_the_run_summary_reads_as_one_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0024's observability: repairs versus redraws, and lineages at K.

    Additive and inert — nothing in the pipeline reads these numbers back — but
    they are the data ADR-0024 says the K recalibration needs, so they have to
    be legible.
    """
    puzzles = _capture_puzzles(monkeypatch)
    source = _ScriptedSource(_ambiguous_at_forty_percent(), repeat_last=True)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned):
        generate(_request())

    summary = puzzles[-1].recovery.describe()
    assert f"{MAX_REGENERATE_ATTEMPTS} recovery attempts" in summary
    shape = _recovery_shape()
    assert f"{shape.redraws} redraws" in summary
    assert f"{shape.repairs} repairs" in summary
    assert (
        f"{shape.capped_lineages} lineages reached the repair cap of "
        f"{orchestrator.MAX_CONSECUTIVE_REPAIRS}" in summary
    )
    assert (
        f"{shape.repeated} of the repairs re-judged a grid the lineage had "
        "already seen" in summary
    )


def test_a_cycling_lineage_is_told_apart_from_one_still_making_progress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The repeat tally separates the two populations inside ``lineages_at_repair_cap``.

    ADR-0024 defers K's calibration and names this log as its data. Read alone,
    ``lineages_at_repair_cap`` is ambiguous in exactly the way that matters: a
    lineage stopped by K while it was still reaching new grids might convert if
    K were larger, and a lineage cycling between two grids provably will not,
    however large K grows. On the pathological grid the two look identical —
    five lineages, all at the cap — and only the repeat count distinguishes
    them: ten of the fifteen repairs re-solved a grid their own lineage had
    already judged, so raising K here would buy nothing but solver time.

    The contrast case is the same request with a source that stops being
    ambiguous: its lineage reaches the cap having judged a new grid every time,
    and the repeat count stays at zero. One number, two stories, which is the
    point of recording it.
    """
    puzzles = _capture_puzzles(monkeypatch)
    source = _ScriptedSource(_ambiguous_at_forty_percent(), repeat_last=True)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned):
        generate(_request())

    cycling = puzzles[-1].recovery
    shape = _recovery_shape()
    assert cycling.lineages_at_repair_cap == shape.capped_lineages
    assert cycling.repeated_attempts == shape.repeated
    # Two thirds of the repair budget spent re-judging known grids: the signal
    # that says "K is not the constraint here", which the cap count alone hides.
    assert cycling.repeated_attempts > cycling.repairs // 2


def test_the_repeat_tally_reads_zero_on_a_lineage_that_keeps_finding_new_grids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The other half of the contrast, on a real drawn grid rather than a script.

    Guards against the field silently becoming a constant — a tally that can
    only count up says as little as one that never does. This seed's run makes
    two repairs, both landing on grids the lineage had not judged before, and
    the second of them is accepted; so the count has to stay at zero here while
    it reads ten on the cycling run above.

    Pinned to a seed deliberately: the claim is about a specific lineage's
    shape, and ADR-0015 guarantees the same lineage replays on every machine.
    """
    puzzles = _capture_puzzles(monkeypatch)

    generate(_request(width=10, height=10, density=40, seed=2))

    recovery = puzzles[-1].recovery
    assert recovery.redraws == 1
    assert recovery.repairs == 2
    assert recovery.repeated_attempts == 0


@pytest.mark.parametrize(
    ("bound", "expected_draws", "expected_repairs", "expected_cap"),
    [
        # One lineage: the draw, then repairs 1, 2 and 3. The third consecutive
        # repair is still a repair — K is not reached until it has been made.
        (2, 1, 1, 0),
        (3, 1, 2, 0),
        (4, 1, 3, 1),
        # The attempt after the third repair is the redraw: K consecutive
        # repairs failed, so the lineage is discarded and POL-001 sources.
        (5, 2, 3, 1),
        (8, 2, 6, 2),
        (9, 3, 6, 2),
    ],
)
def test_redraws_after_k_consecutive_repairs(
    monkeypatch: pytest.MonkeyPatch,
    bound: int,
    expected_draws: int,
    expected_repairs: int,
    expected_cap: int,
) -> None:
    """AC-A: the K boundary from both sides, with the counter arithmetic.

    The bound is lowered rather than the script lengthened so that each run
    ends *at* the attempt under test: at a bound of 4 the run stops on the
    third consecutive repair, and at 5 the extra attempt is a redraw. Every row
    asserts the same three things — how many grids the source was asked for,
    how many repairs were made, and that the two sum to the attempts the one
    counter recorded (ADR-0024/R2, INV-003).

    Lowering ADR-0002's bound is the only way to observe a *particular*
    attempt's kind, since a run reports counts rather than a history. K is
    pinned to 3 here rather than read from production: the table spells out
    K=3's boundaries literally, because a boundary test whose expected values
    are computed by the same arithmetic as the code would not test the boundary.
    The production value is pinned in ``tests/property/test_recovery_bound.py``
    (5 since CARD-091), and the boundary shape is the same at any K.
    """
    monkeypatch.setattr(orchestrator, "MAX_CONSECUTIVE_REPAIRS", 3)
    monkeypatch.setattr(orchestrator, "MAX_REGENERATE_ATTEMPTS", bound)
    puzzles = _capture_puzzles(monkeypatch)
    source = _ScriptedSource(_ambiguous_at_forty_percent(), repeat_last=True)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned):
        generate(_request())

    puzzle = puzzles[-1]
    assert source.candidates_requested == expected_draws
    assert puzzle.recovery.redraws == expected_draws
    assert puzzle.recovery.repairs == expected_repairs
    assert puzzle.recovery.lineages_at_repair_cap == expected_cap
    assert puzzle.recovery.attempts == puzzle.regenerate.attempts == bound


def test_library_mode_never_repairs(monkeypatch: pytest.MonkeyPatch) -> None:
    """ADR-0024/R5: POL-006 is random mode's. Library mode keeps POL-001.

    The same scripted ambiguous grid and the same lowered bound as above, in
    the other re-drawable mode: six grids are asked for rather than two, and
    the tally records no repair at all.
    """
    monkeypatch.setattr(orchestrator, "MAX_REGENERATE_ATTEMPTS", 6)
    puzzles = _capture_puzzles(monkeypatch)
    source = _ScriptedSource(_ambiguous_at_forty_percent(), repeat_last=True)
    _install_source(monkeypatch, source)

    with pytest.raises(GenerationAbandoned):
        generate(_request(mode="library", library_key="cat", density=None))

    assert source.candidates_requested == 6
    assert puzzles[-1].recovery.repairs == 0
    assert puzzles[-1].recovery.redraws == 6


# --- AC-C: a seed replays its lineage --------------------------------------


def test_the_same_seed_replays_the_same_repair_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-C / ADR-0015: same seed, same accepted grid, same lineage.

    Not merely the same answer: the same *sequence* of repairs, cell for cell,
    through an observer over the real repair. Seed 42 at 10x10 / 30% density
    accepts on its nineteenth attempt after five draws and fourteen repairs,
    three of which came from the fallback region — a lineage long enough for a
    difference to show up in.
    """
    real_repair = orchestrator.repair_candidate
    request = _request(width=10, height=10, density=30, seed=42)

    first_recorder = _RepairRecorder(monkeypatch, real_repair)
    first = generate(request)
    first_lineage = list(first_recorder.calls)

    second_recorder = _RepairRecorder(monkeypatch, real_repair)
    second = generate(request)

    assert first_lineage  # the seed really does repair, or this asserts nothing
    assert first_lineage == second_recorder.calls
    assert first.grid == second.grid
    assert first.clues == second.clues
    assert first.regenerate.attempts == second.regenerate.attempts
    assert first.recovery == second.recovery
    assert first.recovery.repairs > 0
    assert first.seed == second.seed == 42


# --- AC-D: the calibration check the handoff asks for ----------------------


def test_the_abandonment_rate_is_not_worse_than_pure_redraw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-D: on one seeded corpus, repair must not abandon more often.

    A *check* of the card's calibration measurement rather than the measurement
    itself — the 20x20 corpus at densities 20, 25 and 30 that ADR-0024 asks for
    is in the card's Worktree notes and takes minutes. This is the slice cheap
    enough to live in the suite: 10x10 at 30% density, the extent and density
    CARD-005 pinned its own abandonment cases at, over a corpus whose size is
    asserted here so it cannot silently shrink. Measured when written: 18
    abandonments with repair against 26 without, over these 36 seeds.

    The claim is one-sided on purpose. ADR-0024 does not promise that repair
    rescues a given seed — a repair spends an attempt a redraw would have spent,
    so a seed whose lucky draw was the eighteenth can lose it — only that the
    reaction is not a net loss across a corpus.
    """
    corpus = range(36)
    assert len(corpus) >= 30

    def abandonments(consecutive_repairs: int) -> int:
        monkeypatch.setattr(
            orchestrator, "MAX_CONSECUTIVE_REPAIRS", consecutive_repairs
        )
        failures = 0
        for seed in corpus:
            try:
                generate(_request(width=10, height=10, density=30, seed=seed))
            except GenerationAbandoned:
                failures += 1
        return failures

    with_repair = abandonments(3)
    pure_redraw = abandonments(0)

    assert with_repair <= pure_redraw


# --------------------------------------------------------------------------
# CARD-076 — generate_batch's tier validation accepts ADR-0025's fourth value
# --------------------------------------------------------------------------


@pytest.mark.parametrize("tier", list(difficulty.Tier))
def test_generate_batch_accepts_every_tier_the_enum_names(
    tier: difficulty.Tier, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CARD-070's batch gate reads the tier vocabulary off the enum.

    So ADR-0025's fourth member reached it without an edit, and that is the
    property worth pinning: a hand-written ``{"EASY", "MEDIUM", "HARD"}`` would
    have refused ``guess`` and the failure would have surfaced as "unknown
    tier" on a tier that exists.

    Parametrized over ``Tier`` itself rather than over a transcribed list, so
    the *next* member is covered the moment it lands. The generation call is
    stubbed: what is under test is the gate, not the loop, and asking the real
    pipeline for a Guess puzzle would exhaust POL-004's budget (see
    ``tests/test_difficulty_tiers.py::
    test_requesting_the_fourth_tier_is_a_generation_outcome_not_a_rejection``).

    Spelling is no longer part of the gate: CARD-070 routed it through
    ``difficulty.parse_tier``, so ``"GUESS"``, ``"guess"`` and ``"Guess"`` are
    one tier. This test still feeds ``tier.name`` — the spelling that worked
    before — so it keeps pinning the enum-reading property without becoming a
    test of the widening; the widening has its own tests below.
    """
    made: list[str | None] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        made.append(request.difficulty)
        puzzle = Puzzle(request=request, seed=0)
        puzzle.record_candidate([[True, True], [True, False]])
        puzzle.confirm_uniqueness(1)
        puzzle.record_difficulty(10.0, 0)
        return puzzle

    monkeypatch.setattr(orchestrator, "generate", fake_generate)

    puzzles = orchestrator.generate_batch(
        count=1, sizes=[10], source="random", difficulty_tier=tier.name
    )

    assert len(puzzles) == 1
    # The canonical value, not the caller's spelling: the request is parsed
    # again downstream and handing it ``parse_tier``'s own answer means the
    # second parse cannot disagree with the first (CARD-070).
    assert made == [tier.value]


def test_generate_batch_still_refuses_a_tier_that_does_not_exist() -> None:
    """The gate is still a gate: growing the enum did not open it.

    The mirror of the test above, and the reason that one is not vacuous — a
    validation that accepted everything would pass it for every member.

    CARD-070 changed the error from a local ``ValueError`` to the domain's
    ``UnsupportedDifficulty``, which COMP-001 already maps to
    ``ExitCode.INVALID_INPUT``; the message lists the tiers that do exist.
    """
    with pytest.raises(errors.UnsupportedDifficulty, match="unsupported difficulty tier"):
        orchestrator.generate_batch(
            count=1, sizes=[10], source="random", difficulty_tier="EXTREME"
        )


# --------------------------------------------------------------------------
# CARD-070 item 1 — the batch accepts the spelling its docstring advertises
# --------------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["Easy", "easy", "EASY", "  Easy  "])
def test_generate_batch_accepts_every_spelling_parse_tier_accepts(
    spelling: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``"Easy"`` is what the docstring promised and what used to raise.

    The gate compared enum *names*, so only ``"EASY"`` got through —
    ``docs/GENERATION_ALGORITHM.md`` §10.2 finding 1. Every caller passes
    ``None``, which is why a documented spelling could raise for as long as it
    did: no test and no user ever tried the middle case.
    """
    made: list[str | None] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        made.append(request.difficulty)
        puzzle = Puzzle(request=request, seed=0)
        puzzle.record_candidate([[True, True], [True, False]])
        puzzle.confirm_uniqueness(1)
        puzzle.record_difficulty(10.0, 0)
        return puzzle

    monkeypatch.setattr(orchestrator, "generate", fake_generate)

    puzzles = orchestrator.generate_batch(
        count=1, sizes=[10], source="random", difficulty_tier=spelling
    )

    assert len(puzzles) == 1
    assert made == [difficulty.Tier.EASY.value]


def test_the_empty_string_is_a_tier_that_does_not_exist_on_both_paths() -> None:
    """The spelling the two paths used to disagree about.

    ``""`` is falsy, so the old guard skipped ``parse_tier`` entirely and the
    batch read it as "any tier" while ``generate`` refused it one frame down —
    the exact split routing through ``parse_tier`` was supposed to close
    (review cycle 1, F-001). Asserted as one claim about both functions rather
    than two separate ones, so a future change cannot fix half of it.
    """
    with pytest.raises(errors.UnsupportedDifficulty) as batch_error:
        orchestrator.generate_batch(
            count=1, sizes=[10], source="random", difficulty_tier=""
        )
    with pytest.raises(errors.UnsupportedDifficulty) as single_error:
        orchestrator.generate(
            GenerationRequest(
                mode="random", width=10, height=10, density=50, seed=1, difficulty=""
            )
        )

    assert str(batch_error.value) == str(single_error.value)


def test_none_is_still_the_way_to_say_any_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tightening the empty string must not tighten ``None``, which is what
    every caller in the codebase actually passes."""
    made: list[str | None] = []

    def fake_generate(request: GenerationRequest) -> Puzzle:
        made.append(request.difficulty)
        puzzle = Puzzle(request=request, seed=0)
        puzzle.record_candidate([[True, True], [True, False]])
        puzzle.confirm_uniqueness(1)
        puzzle.record_difficulty(10.0, 0)
        return puzzle

    monkeypatch.setattr(orchestrator, "generate", fake_generate)

    puzzles = orchestrator.generate_batch(
        count=1, sizes=[10], source="random", difficulty_tier=None
    )

    assert len(puzzles) == 1
    assert made == [None]


def test_generate_batch_and_the_cli_refuse_the_same_words() -> None:
    """One vocabulary, not two.

    The point of routing through ``parse_tier`` is that a batch and an
    interactive run cannot disagree about which tiers exist. Asserted by
    comparing the two answers rather than by restating either.
    """
    with pytest.raises(errors.UnsupportedDifficulty) as batch_error:
        orchestrator.generate_batch(
            count=1, sizes=[10], source="random", difficulty_tier="extreme"
        )
    with pytest.raises(errors.UnsupportedDifficulty) as parse_error:
        difficulty.parse_tier("extreme")

    assert str(batch_error.value) == str(parse_error.value)


def test_the_refusal_names_the_tiers_that_do_exist() -> None:
    """A refusal that does not say what *would* work is a dead end.

    Read off the enum, so the message cannot drift from the rule — including
    ADR-0025's fourth tier, which the card's AC-1 (written before that ADR
    landed) still calls "the three tiers".
    """
    with pytest.raises(errors.UnsupportedDifficulty) as caught:
        orchestrator.generate_batch(
            count=1, sizes=[10], source="random", difficulty_tier="extreme"
        )

    message = str(caught.value)
    for tier in difficulty.Tier:
        assert tier.value in message, tier
