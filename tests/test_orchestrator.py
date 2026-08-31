"""COMP-002 tests: the generation pipeline, its aggregate and its retry bound.

AC / test-id mapping — the trace.yml names, kept traceable from these
pytest-idiomatic function names:

    AC-018  TestRegenerate_FiresOnUniquenessFailure -> test_regenerate_fires_on_uniqueness_failure*
    AC-019  TestRegenerate_StopsAtMaxRetryBound     -> test_regenerate_stops_at_max_retry_bound*
    AC-039  TestRetryLoop_BoundedIterations         -> test_retry_loop_bounded_iterations*

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

import pytest

from nonogram import orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import (
    ExportRejected,
    GenerationAbandoned,
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
        self.calls: list[tuple[int | None, int | None, random.Random]] = []

    def __call__(
        self, size: int | None, density: int | None, rng: random.Random
    ) -> list[list[bool]]:
        self.calls.append((size, density, rng))
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

    def __call__(self, size: int | None, density: int | None, rng: random.Random):
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
    """A minimal valid request; the scripted source ignores size/density."""
    fields: dict[str, object] = {"mode": "random", "size": 10, "density": 50, "seed": 0}
    fields.update(overrides)
    return GenerationRequest(**fields)  # type: ignore[arg-type]


def _puzzle(**overrides: object) -> Puzzle:
    return Puzzle(request=_request(**overrides), seed=0)


# --------------------------------------------------------------------------
# The Puzzle aggregate (AGG-001) — one instance per request, INV-001/INV-002
# --------------------------------------------------------------------------


def test_the_aggregate_carries_the_requests_attributes() -> None:
    """AGG-001's mode/size/density are attributes of the one instance."""
    puzzle = _puzzle(mode="random", size=15, density=40)

    assert puzzle.mode == "random"
    assert puzzle.size == 15
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
    puzzle = generate(_request(size=10, density=50, seed=0))

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

    generate(_request(seed=7))

    rngs = [rng for _, _, rng in source.calls]
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

    generate(_request(size=12, density=35))

    assert [(size, density) for size, density, _ in source.calls] == [(12, 35)]


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
    """An invalid request does not become valid by being asked 20 times."""
    source = _RaisingSource(SizeOutOfRange("grid size must be between 10 and 30"))
    _install_source(monkeypatch, source)

    with pytest.raises(SizeOutOfRange):
        generate(_request(size=60))

    assert source.calls == 1


def test_an_invalid_size_reaches_the_domain_check_unmocked() -> None:
    """The same path with the real sourcing module (ADR-0010: validation is
    inward of the CLI, so a missing --size is rejected here)."""
    with pytest.raises(SizeOutOfRange):
        generate(_request(size=None))


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

    puzzle = generate(_request())

    assert source.candidates_requested == 5
    assert puzzle.regenerate.attempts == 5


def test_regenerate_discards_the_failed_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """"Discard" means the rejected grid is gone, not merely re-judged."""
    source = _ScriptedSource(ALSO_AMBIGUOUS, UNIQUE)
    _install_source(monkeypatch, source)

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
    puzzle = generate(_request(size=10, density=50, seed=1))

    assert puzzle.regenerate.attempts > 1
    assert puzzle.ready_for_export is True
    assert solve(*compute_clues(puzzle.grid)).solution_count == 1


# --------------------------------------------------------------------------
# AC-019 (INV-003, POL-005) — TestRegenerate_StopsAtMaxRetryBound
# --------------------------------------------------------------------------


def test_the_regenerate_bound_is_the_adr_0002_value() -> None:
    assert MAX_REGENERATE_ATTEMPTS == 20


def test_regenerate_stops_at_max_retry_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At the bound the run is abandoned with a clear error, not retried."""
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)

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
    """The same bound with nothing mocked.

    Pinned seed: at 10x10 / 30% density, seed 0 produces twenty consecutive
    candidates that are not uniquely solvable (sweep over seeds 0..11: seeds
    0, 1, 4, 5, 10 and 11 all exhaust the budget).
    """
    with pytest.raises(GenerationAbandoned):
        generate(_request(size=10, density=30, seed=0))


def test_an_abandoned_run_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The abandonment path leaves no partial artefact behind (G-4)."""
    monkeypatch.chdir(tmp_path)
    source = _ScriptedSource(AMBIGUOUS, repeat_last=True)
    _install_source(monkeypatch, source)

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
