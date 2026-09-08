"""AC-084 and the ADR-0011 cooperative deadline mechanism behind it.

    AC-084  TestGenerate_30x30_RespectsTimeoutBound
            ->  TestGenerate_30x30_RespectsTimeoutBound (the class below)

*given* a 30x30 random-grid generation request (the largest supported grid
under CON-011) using a seed measured to drive the solver past the deadline,
*when* generation runs, *then* it completes within 30s or fails clearly with a
`SolverTimeout` — it never hangs indefinitely.

AC-084 supersedes AC-038, which said the same thing at 50x50. Only the size
moved: CON-011 narrowed the supported range to 10..30 for print legibility
(NFR-005), so a 50x50 request is now rejected by ``validate_size`` before the
solver is ever entered, and a fixture built on one would be testing input
validation while claiming to test the deadline.

The two halves of that "or" are tested separately, because they are different
claims and only one of them is about the timeout at all:

* a 30x30 request the solver *can* finish returns a real, exportable puzzle
  well inside the bound — under the production 30s budget, unfaked;
* a 30x30 request the solver *cannot* finish stops with ``SolverTimeout``
  rather than running forever.

Why the second one does not wait 30 real seconds
------------------------------------------------
It substitutes a short budget for ADR-0001's 30s and leaves everything else —
the request, the grid, the solver, the deadline machinery — real. That is
exactly the testing affordance ADR-0011 chose the cooperative mechanism *for*:
"a ``SolverTimeout`` can be triggered deterministically in tests by injecting a
near-immediate deadline, with no reliance on real wall-clock waits". The number
30.0 is pinned by its own one-line test, so the substitution scales a constant
this file has checked rather than assuming one.

The scaling is only honest if the request is one that really does outrun the
full budget, and at 30x30 that had to be re-measured rather than inherited:
CARD-018 strengthened line logic (bidirectional probing, a per-solve line memo,
a widening restart schedule), so CARD-004's 50x50 parameters say nothing about
what is hard three sizes down. :data:`HARD_DENSITY` and the seed below are the
result of that search — see CARD-023's worktree notes for the seeds, densities
and times. The headline: at 30x30 and 40% density, the *first* candidate grid
alone keeps the solver busy for more than 60 seconds, so the request is
genuinely unfinishable inside ADR-0001's 30s and the short budget expires on
real solver work rather than on a deadline that had passed before the solver
was asked anything.

Beyond AC-084, the module-level tests below pin the mechanism's three
load-bearing properties: the deadline is checked *inside* the two loops rather
than once at the entrance (otherwise "never hangs" is false), it covers the
whole request rather than each retry, and it is entirely absent when no
deadline is passed (guardrail G-2 — the solver's existing behaviour is
unchanged).
"""

from __future__ import annotations

import random
import time
from types import SimpleNamespace

import pytest

from nonogram import orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import ExportRejected, SolverTimeout
from nonogram.orchestrator import GenerationRequest, Puzzle, generate
from nonogram.solver import solve
from nonogram.solver.propagate import Board, LineCache, check_deadline, propagate
from nonogram.sourcing import random_grid

# --------------------------------------------------------------------------
# Fixtures and helpers
# --------------------------------------------------------------------------

#: The largest grid CON-011 supports, read from the one place that defines it
#: (ADR-0022/R2). The tests below also assert the resulting grid is 30 cells a
#: side, so the fixture is anchored to AC-084's "30x30" rather than to wherever
#: the constant drifts next.
MAX_SUPPORTED_SIZE = random_grid.MAX_SIZE

#: A budget short enough to keep the suite quick, long enough that the solver
#: is genuinely working when it expires (the observed overshoot at 30x30 is
#: under a millisecond, so this is hundreds of checks deep, not one).
SHORT_BUDGET_SECONDS = 0.25

#: The density CARD-023 measured as the hard class at 30x30, the largest grid
#: CON-011 supports: line logic settles almost nothing and the search grinds.
#: Measured, not inherited — 50%, the hard class CARD-004 found at 50x50, is
#: *easy* at 30x30 today (its candidates solve in tens of milliseconds and the
#: request ends in ``GenerationAbandoned``, not a timeout), while every seed
#: tried at 40% and 45% outran the full 30s budget.
HARD_DENSITY = 40

#: The seed used with :data:`HARD_DENSITY`. Nothing distinguishes it — every
#: seed measured at this density outran the budget — but it is pinned so the
#: fixture is a fixed, reproducible request rather than a lucky draw.
HARD_SEED = 7

#: High density is the easy class at every supported size — line-solvable with
#: no branching at all, ~3ms for the one candidate a 30x30 request needs.
EASY_DENSITY = 75

#: A budget the hard fixture's *first* candidate must already outrun, used by
#: the premise test below. Sixty times under the measured >60s, so it is
#: checking the fixture and not this machine's speed.
#:
#: Deliberately 1.0s and not AC-084's real 30s deadline. The gap is a known,
#: accepted blind window: a solve landing in [1s, 30s) falsifies AC-084's
#: premise while this test stays green. Closing it would cost 30 seconds of
#: wall clock on every future suite run, forever, and the measured margin makes
#: the regression remote — this seed's first candidate exceeded 60s (>2x
#: ADR-0001's whole budget) when measured, so reaching the window needs a
#: 30-60x solver improvement on this instance. CARD-018 was an improvement of
#: roughly that order on *some* grids, which is why the margin is recorded here
#: rather than assumed: whoever disturbs this fixture next should re-measure and
#: update this number, not trust it.
PREMISE_BUDGET_SECONDS = 1.0


def _hard_request() -> GenerationRequest:
    """AC-084's request: 30x30, at the density measured to outrun the budget."""
    return GenerationRequest(
        mode="random",
        width=MAX_SUPPORTED_SIZE, height=MAX_SUPPORTED_SIZE,
        density=HARD_DENSITY,
        seed=HARD_SEED,
    )


def _branching_clues() -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """A clue set that exercises *both* of ADR-0011's checkpoints.

    Built from a real grid rather than written by hand — a grid's own clues are
    guaranteed satisfiable, so the search does real work instead of failing out
    on a contradiction — and this particular one was picked because it needs
    both loops: line logic settles a good part of the board (so propagation
    runs several sweeps) and then stalls with cells left (so the search
    branches, five times). The tests below assert those two facts about it
    rather than assuming them, so a solver change that made it trivial would
    say so instead of quietly weakening the coverage.
    """
    rng = random.Random(22)
    grid = [[rng.random() < 0.5 for _ in range(8)] for _ in range(8)]
    return compute_clues(grid)


class _FakeClock:
    """A monotonic clock that stands still, then jumps far past the deadline.

    Substituted for the ``time`` module inside
    :mod:`nonogram.solver.propagate`, which is the single place the solver
    reads a clock for the deadline. Standing still until a chosen read makes
    "how many checks happened, and where" observable and exactly reproducible —
    a real clock could only answer it statistically.
    """

    #: The frozen "now" every read returns until the clock is made to expire.
    NOW = 1000.0
    #: A deadline that :attr:`NOW` has not reached.
    DEADLINE = NOW + 1.0

    def __init__(self, expire_on_read: int = 2**60) -> None:
        self.reads = 0
        self._expire_on_read = expire_on_read

    def monotonic(self) -> float:
        self.reads += 1
        return self.NOW if self.reads < self._expire_on_read else self.DEADLINE + 1.0


def _install_clock(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> _FakeClock:
    """Point the solver's deadline check at ``clock``."""
    from nonogram.solver import propagate as propagate_module

    monkeypatch.setattr(propagate_module, "time", SimpleNamespace(monotonic=clock.monotonic))
    return clock


def _blank_board(
    rows: tuple[tuple[int, ...], ...], columns: tuple[tuple[int, ...], ...]
) -> tuple[Board, list[bool], list[bool]]:
    """The starting state ``solve`` builds before its first propagation."""
    from nonogram.solver.propagate import canonical_clue

    board = Board.blank(
        tuple(canonical_clue(clue) for clue in rows),
        tuple(canonical_clue(clue) for clue in columns),
    )
    return board, [True] * len(rows), [True] * len(columns)


# --------------------------------------------------------------------------
# AC-084 — TestGenerate_30x30_RespectsTimeoutBound
# --------------------------------------------------------------------------


class TestGenerate_30x30_RespectsTimeoutBound:
    """AC-084: a 30x30 request completes inside the bound or fails clearly."""

    def test_the_enforced_bound_is_adr_0001s_thirty_seconds(self) -> None:
        """The number AC-084 names, pinned where the mechanism reads it.

        Everything else in this class either runs under this budget or
        substitutes a smaller one for it; without this assertion, a budget that
        had drifted to 300s would still pass every other test here.
        """
        assert orchestrator.GENERATION_BUDGET_SECONDS == 30.0

    def test_a_30x30_request_the_solver_can_finish_completes_inside_the_bound(
        self,
    ) -> None:
        """The first half of AC-084's "or", under the real production budget.

        No monkeypatching at all: a genuine 30x30 request at the largest size
        CON-011 supports, ADR-0001's real 30s deadline, and a verified unique
        puzzle at the end of it. The margin is not close — a line-solvable
        30x30 is a few milliseconds — which is the point: the timeout exists
        for the hard class, and must not be collecting the easy one on the way
        past.
        """
        started = time.monotonic()
        puzzle = generate(
            GenerationRequest(
                mode="random",
                width=MAX_SUPPORTED_SIZE,
                height=MAX_SUPPORTED_SIZE,
                density=EASY_DENSITY,
                seed=1,
            )
        )
        elapsed = time.monotonic() - started

        assert elapsed < orchestrator.GENERATION_BUDGET_SECONDS
        assert puzzle.ready_for_export is True
        assert puzzle.solution_count == 1
        assert len(puzzle.grid or []) == 30

    def test_a_30x30_request_the_solver_cannot_finish_raises_solver_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The second half: the hard class stops clearly instead of hanging.

        :data:`HARD_DENSITY` at 30x30 is CARD-023's measured hard class — this
        exact request runs past ADR-0001's full 30s budget, on its first
        candidate alone — and it is asked for with a real grid, real clues and
        the real solver. Only ADR-0001's budget is scaled down, per this
        module's docstring. What is asserted is the *shape* of the failure: a
        named domain error, not a hang, not a ``RecursionError``, and not a
        puzzle.
        """
        monkeypatch.setattr(
            orchestrator, "GENERATION_BUDGET_SECONDS", SHORT_BUDGET_SECONDS
        )

        with pytest.raises(SolverTimeout) as raised:
            generate(_hard_request())

        assert "deadline" in str(raised.value)

    def test_the_hard_fixtures_first_candidate_alone_outruns_a_budget(self) -> None:
        """The premise the timeout half rests on, asserted rather than assumed.

        This reproduces the request's very first candidate — the orchestrator
        seeds one ``random.Random(seed)`` and draws it exactly this way — and
        shows the solver cannot finish even that one inside
        :data:`PREMISE_BUDGET_SECONDS`.

        **What it catches, stated precisely.** It catches the seed becoming
        *trivially* easy, which is the failure this card exists to prevent: the
        naive substitution (keep density 50, swap 50x50 for 30x30) solves in
        ~0.04s and fails here loudly, as does EASY_DENSITY at ~0.003s.

        It does **not** verify AC-084's own wording, "a seed measured to drive
        the solver past the deadline". That deadline is
        :data:`~nonogram.orchestrator.GENERATION_BUDGET_SECONDS` = 30s; this
        asserts 1.0s. A solve landing in [1s, 30s) falsifies AC-084's premise
        while this stays green — an accepted blind window, because closing it
        costs 30s of wall clock on every future suite run forever. See
        :data:`PREMISE_BUDGET_SECONDS` for the measured margin that makes the
        regression remote.

        Note the timeout half does not go vacuous inside that window either: at
        8s per candidate the 0.25s scaled budget still expires mid-solve on real
        solver work. What would be false there is this premise claim, not the
        deadline mechanism the timeout half exercises.

        The day a solver improvement makes this seed easy, this goes red and
        says *re-measure*, instead of the fixture quietly becoming a test of
        nothing.
        """
        request = _hard_request()
        grid = random_grid.generate(
            request.width, request.height, request.density, random.Random(request.seed)
        )
        rows, columns = compute_clues(grid)

        with pytest.raises(SolverTimeout):
            solve(rows, columns, deadline=time.monotonic() + PREMISE_BUDGET_SECONDS)

    def test_the_overshoot_past_the_deadline_is_small(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """"Never hangs" is a claim about *when* it stops, not just that it does.

        ADR-0011's one negative consequence is that a cooperative check can
        only fire between whole steps, so the call returns slightly after the
        deadline rather than exactly on it. This bounds that slack generously —
        a whole budget's worth — so the test is not measuring this machine's
        speed, while still failing loudly if a checkpoint were ever moved
        somewhere a long-running step could hide behind (the observed overshoot
        at 30x30 is 0.3-0.7 ms, against a 250 ms budget).
        """
        monkeypatch.setattr(
            orchestrator, "GENERATION_BUDGET_SECONDS", SHORT_BUDGET_SECONDS
        )

        started = time.monotonic()
        with pytest.raises(SolverTimeout):
            generate(_hard_request())
        elapsed = time.monotonic() - started

        assert elapsed < 2 * SHORT_BUDGET_SECONDS

    def test_a_timed_out_request_yields_no_puzzle_at_all(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """INV-002 / guardrail G-4: a timeout is abandonment, not a degraded pass.

        The strongest form the invariant can take here: ``generate`` returns
        *nothing* on this path, so there is no object for a caller to mistake
        for a result — the aggregate the run mutated is unreachable by the time
        the exception surfaces. The companion test below covers the weaker but
        more direct statement about the aggregate itself.
        """
        monkeypatch.setattr(
            orchestrator, "GENERATION_BUDGET_SECONDS", SHORT_BUDGET_SECONDS
        )
        request = _hard_request()

        result: Puzzle | None = None
        with pytest.raises(SolverTimeout):
            result = generate(request)

        assert result is None

    def test_a_candidate_whose_solve_timed_out_is_never_ready_for_export(self) -> None:
        """INV-002 at its enforcement point, without going through the pipeline.

        A timed-out attempt gets as far as ``record_candidate`` and no further:
        ``confirm_uniqueness`` is the only writer of ``ready_for_export``, and
        it is never reached. So the aggregate the run leaves behind is exactly
        the state built here — a candidate with clues and no verdict — and the
        export gate must refuse it.
        """
        puzzle = Puzzle(
            request=GenerationRequest(mode="random", width=10, height=10), seed=0
        )
        puzzle.record_candidate([[True, False], [False, True]])

        assert puzzle.ready_for_export is False
        assert puzzle.solution_count is None
        with pytest.raises(ExportRejected):
            puzzle.require_ready_for_export()


# --------------------------------------------------------------------------
# The mechanism: where the check happens (ADR-0011's two checkpoints)
# --------------------------------------------------------------------------


def test_a_deadline_already_in_the_past_stops_the_solver_before_any_work() -> None:
    """The degenerate case, and the one every other test's premise rests on."""
    rows, columns = _branching_clues()

    with pytest.raises(SolverTimeout):
        solve(rows, columns, deadline=time.monotonic() - 1.0)


def test_check_deadline_ignores_a_deadline_that_has_not_passed() -> None:
    """The other side of the same boundary — no spurious timeouts."""
    check_deadline(time.monotonic() + 60.0)
    check_deadline(None)


def test_propagation_checks_the_deadline_at_every_fixed_point_sweep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0011's first checkpoint is *inside* the sweep loop, not before it.

    A clock that never expires makes the number of checks observable: a board
    that needs several sweeps to reach its fixed point is checked several
    times. If the check had been hoisted out of the loop, this would be 1
    however long propagation ran — which is the failure mode that would make
    "never hangs" untrue while every timeout test still passed.
    """
    rows, columns = _branching_clues()
    board, dirty_rows, dirty_columns = _blank_board(rows, columns)
    clock = _install_clock(monkeypatch, _FakeClock())

    assert propagate(board, dirty_rows, dirty_columns, _FakeClock.DEADLINE) is True
    assert clock.reads >= 2, "propagation checked the deadline only once"


def test_propagation_stops_at_the_sweep_after_the_deadline_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same loop, with the clock expiring on its second read.

    Pairs with the test above: that one shows the check repeats, this one shows
    a repeat actually raises. Together they rule out a check that runs every
    sweep but only looks at the clock once.
    """
    rows, columns = _branching_clues()
    board, dirty_rows, dirty_columns = _blank_board(rows, columns)
    _install_clock(monkeypatch, _FakeClock(expire_on_read=2))

    with pytest.raises(SolverTimeout):
        propagate(board, dirty_rows, dirty_columns, _FakeClock.DEADLINE)


def _blind_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable ADR-0011's *first* checkpoint, leaving only the branch one.

    Every deadline test that goes through ``solve`` is ambiguous without this.
    The search calls propagation once per guess, and propagation checks the
    deadline before its first sweep — so an expired deadline is caught either
    way, and a test that only asserts "it raised" would still pass with the
    branch-node check deleted. Handing propagation ``deadline=None`` from
    inside ``search`` removes that second explanation: whatever the two tests
    below observe, only the branch checkpoint can have produced it.
    """
    from nonogram.solver import search as search_module

    real_propagate = search_module.propagate

    def deadline_blind_propagate(
        board: Board,
        dirty_rows: list[bool],
        dirty_columns: list[bool],
        deadline: float | None = None,
        cache: LineCache | None = None,
    ) -> bool:
        # ``cache`` is CARD-018's per-solve line memo: forwarded untouched, so
        # the substitution changes exactly one thing — the deadline — and the
        # search still runs at its normal speed underneath.
        return real_propagate(board, dirty_rows, dirty_columns, None, cache)

    monkeypatch.setattr(search_module, "propagate", deadline_blind_propagate)


def test_the_search_checks_the_deadline_at_every_branch_node(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0011's second checkpoint, counted against the search's own signal.

    With propagation blinded (see :func:`_blind_propagation`), every clock read
    during this solve comes from the top of the search loop. ``branch_nodes``
    is the solver's own report of how many times it had to guess, and each of
    those guesses is made after passing that loop top — so the read count
    cannot be lower. Asserting against the reported signal rather than a
    hard-coded number keeps this honest if the branching heuristic is retuned.
    """
    rows, columns = _branching_clues()
    _blind_propagation(monkeypatch)
    clock = _install_clock(monkeypatch, _FakeClock())

    result = solve(rows, columns, deadline=_FakeClock.DEADLINE)

    assert result.signals.branch_nodes >= 2, "this clue set no longer exercises the search"
    assert clock.reads >= result.signals.branch_nodes


def test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The second checkpoint is load-bearing on its own, not a duplicate.

    Same blinding, an already-expired deadline, and a clue set that reaches the
    search: the only thing left that can raise is the branch-node check. The
    sanity solve first shows the blinded solver still answers normally when no
    deadline is given, so the raise below is the checkpoint firing and not the
    substitution breaking the search.
    """
    rows, columns = _branching_clues()
    _blind_propagation(monkeypatch)

    assert solve(rows, columns).solution_count >= 1

    with pytest.raises(SolverTimeout):
        solve(rows, columns, deadline=time.monotonic() - 1.0)


# --------------------------------------------------------------------------
# The deadline is the request's, not the attempt's (COMP-002)
# --------------------------------------------------------------------------


def test_every_attempt_in_one_request_shares_one_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of computing it in ``generate`` and not in ``solve``.

    A per-solve budget would make 20 regenerate retries a ten-minute
    "timeout" — the arithmetic CARD-006 and ADR-0002's "together but
    independently" note both call out. Recording the deadline each attempt is
    handed shows the budget is fixed once for the request.
    """
    seen: list[float] = []
    real_solve = orchestrator.solver.solve

    def recording_solve(rows, columns, *, deadline=None, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(deadline)
        return real_solve(rows, columns, deadline=deadline, **kwargs)

    monkeypatch.setattr(orchestrator.solver, "solve", recording_solve)

    # A 10x10 at 50% that takes four candidates to find a unique one — real
    # rejections from the real solver, not injected verdicts, so the retries
    # being counted are the retries POL-001 actually performs.
    puzzle = generate(
        GenerationRequest(mode="random", width=10, height=10, density=50, seed=2)
    )

    assert puzzle.regenerate.attempts > 1, "the retry loop ran only one attempt"
    assert len(seen) == puzzle.regenerate.attempts
    assert len(set(seen)) == 1, f"the deadline was recomputed per attempt: {seen}"


def test_the_deadline_is_the_budget_measured_from_the_start_of_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It is ``monotonic() + budget``, on the clock the solver compares against.

    Checked as a band rather than an equality: the two readings are taken
    microseconds apart on a real clock, and pinning them exactly would be
    testing the machine, not the code.
    """
    monkeypatch.setattr(orchestrator, "GENERATION_BUDGET_SECONDS", 12.5)
    seen: list[float] = []

    def recording_solve(rows, columns, *, deadline=None, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(deadline)
        return orchestrator.solver.SolveResult(
            solution_count=1,
            solution=[[]],
            signals=orchestrator.solver.SolveSignals(0, 0, 0, 0, 0.0),
        )

    monkeypatch.setattr(orchestrator.solver, "solve", recording_solve)

    before = time.monotonic()
    generate(GenerationRequest(mode="random", width=10, height=10, density=50, seed=0))
    after = time.monotonic()

    assert len(seen) == 1
    assert before + 12.5 <= seen[0] <= after + 12.5


# --------------------------------------------------------------------------
# Guardrail G-2 — no deadline, no change
# --------------------------------------------------------------------------


def test_omitting_the_deadline_leaves_the_solver_exactly_as_it_was() -> None:
    """The default is "no deadline", and it reads no clock and raises nothing.

    Every pre-existing solver test and the EC-001 property corpus call
    ``solve`` this way, so this is the assertion that says CARD-006 added a
    capability rather than changing one.
    """
    rows, columns = _branching_clues()

    without = solve(rows, columns)
    with_far_deadline = solve(rows, columns, deadline=time.monotonic() + 3600.0)

    assert without.solution_count == with_far_deadline.solution_count
    assert without.solution == with_far_deadline.solution
    assert without.signals.branch_nodes == with_far_deadline.signals.branch_nodes
    assert without.signals.backtracks == with_far_deadline.signals.backtracks
    assert without.signals.line_logic_cells == with_far_deadline.signals.line_logic_cells


def test_a_deadline_never_reads_the_clock_when_it_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``deadline=None`` keeps the solver a pure function of its clues.

    Not a micro-optimisation dressed up as a test: ADR-0007 and CARD-004's
    guardrails make the solver's purity a property other things rely on (the
    property corpus needs no fixture; two runs on the same clues are
    identical). A clock consulted on the default path would break that
    silently.
    """
    rows, columns = _branching_clues()
    clock = _install_clock(monkeypatch, _FakeClock())

    solve(rows, columns)

    assert clock.reads == 0
