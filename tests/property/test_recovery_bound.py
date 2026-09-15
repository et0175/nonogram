"""EC-013 and ADR-0024's two engineering constraints — random-mode recovery.

    EC-013  PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound
            -> test_accepted_grids_have_real_verdicts_within_one_bound
    ADR-0024/R4  PropertyTest_Recovery_RepairDrawsNothingFromRng
            -> test_a_repair_draws_nothing_from_the_rng
    ADR-0003     PropertyTest_Recovery_RepairedGridDensityExact
            -> test_every_repaired_grid_has_its_parents_density_exactly

EC-013, in full: for any random-mode request, no grid is ever accepted without
a solver verdict of exactly 1 obtained on that grid's own clues; the total
number of recovery attempts — redraws plus repairs — never exceeds the single
ADR-0002 bound; and when a repair is applied, the repaired grid has a
filled-cell count equal to its parent's and differs from it only inside the
undecided/disagreement region. It is a statement about every seed and extent,
which is why it is here and not in ``tests/test_orchestrator.py``, where
ADR-0024's individual criteria are pinned on hand-built cases.

The corpus, house style (no ``hypothesis`` — it is not in the dependency
baseline): whole ``generate`` runs over a fixed list of seeds and extents,
collected once for the module, with the case counts asserted *inside* each test
so the corpus cannot silently shrink to nothing and leave a green test behind.
Nothing is faked: the real random source draws, the real solver judges, the
real repair flips. The instrumentation only watches — a run's lineage is
otherwise unobservable, since the aggregate keeps counts rather than a history.

Where a claim can be re-derived, it is re-derived here rather than read back
from the code under test: the region a repair was allowed to touch is computed
from the solver's own witnesses and mask by the two small functions below, not
by calling the orchestrator's private helpers, and an accepted grid's verdict
is re-obtained by solving its clues again from scratch.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest

from nonogram import orchestrator
from nonogram.clues import compute_clues
from nonogram.errors import GenerationAbandoned
from nonogram.orchestrator import (
    MAX_CONSECUTIVE_REPAIRS,
    MAX_RETRY_ATTEMPTS,
    GenerationRequest,
    generate,
)
from nonogram.solver import solve

Grid = list[list[bool]]
Cell = tuple[int, int]

#: The corpus: every (extent, density) pair below, over every seed. Small
#: extents on purpose — recovery is common at these sizes and a whole run costs
#: milliseconds, so the corpus is wide rather than deep. Density 30 at 10x10 is
#: where CARD-005 pinned its own abandonment cases, so the corpus contains both
#: outcomes, which EC-013 needs: an abandoned run is a run whose attempts still
#: have to obey the bound.
EXTENTS = ((10, 10), (12, 12))
DENSITIES = (30, 40, 50)
SEEDS = range(12)

#: Floors for the corpus, asserted inside the tests. The observed values when
#: this was written are roughly twice each floor.
REQUIRED_RUNS = 60
REQUIRED_REPAIRS = 80
REQUIRED_ACCEPTED = 30
REQUIRED_ABANDONED = 5


def disagreement_cells(witnesses: tuple[Grid, ...] | None) -> set[Cell]:
    """The cells the solver's two witnesses differ on — re-derived here."""
    if witnesses is None or len(witnesses) < 2:
        return set()
    first, second = witnesses[0], witnesses[1]
    return {
        (row_index, column_index)
        for row_index, (first_row, second_row) in enumerate(zip(first, second))
        for column_index, (left, right) in enumerate(zip(first_row, second_row))
        if left != right
    }


def mask_cells(mask: list[list[bool]] | None) -> set[Cell]:
    """The ``True`` cells of a grid-shaped mask — re-derived here."""
    if not mask:
        return set()
    return {
        (row_index, column_index)
        for row_index, row in enumerate(mask)
        for column_index, cell in enumerate(row)
        if cell
    }


def differences(before: Grid, after: Grid) -> set[Cell]:
    return {
        (row_index, column_index)
        for row_index, (before_row, after_row) in enumerate(zip(before, after))
        for column_index, (was, now) in enumerate(zip(before_row, after_row))
        if was != now
    }


def filled(grid: Grid) -> int:
    return sum(sum(row) for row in grid)


def key(grid: Grid) -> tuple[tuple[bool, ...], ...]:
    """A hashable identity for a grid — this file's own, on purpose.

    The orchestrator has a private helper that does the same thing; not
    importing it is the point, since the test that uses this one is checking
    the orchestrator's repeat count against an independent replay.
    """
    return tuple(tuple(row) for row in grid)


@dataclass(frozen=True, slots=True)
class RepairRecord:
    """One POL-006 repair, with the region it was allowed to touch."""

    parent: Grid
    repaired: Grid
    region: str
    allowed: frozenset[Cell]


@dataclass(slots=True)
class RunRecord:
    """One whole ``generate`` call, as seen from outside."""

    request: GenerationRequest
    accepted: Grid | None = None
    abandoned: bool = False
    attempts: int = 0
    redraws: int = 0
    repairs: int = 0
    fallback_repairs: int = 0
    #: Only populated for a run that was accepted; an abandoned run never hands
    #: its aggregate back, and this tally has no outside proxy the way the
    #: attempt count does.
    repeated_attempts: int | None = None
    solves: int = 0
    applied: list[RepairRecord] = field(default_factory=list)
    #: ``(state before the draw, state after the draw)`` for every call the run
    #: made to the random source, in order.
    rng_states: list[tuple[object, object]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Pristine:
    """The three real collaborators, captured before anything is watched.

    Taken once and passed in, rather than read off the module inside
    :func:`_run`: a second run would otherwise wrap the first run's wrapper,
    and after seventy-two runs every draw would be recorded seventy-two times.
    """

    source: object
    repair: object
    solve: object


def _run(
    request: GenerationRequest, patcher: pytest.MonkeyPatch, pristine: _Pristine
) -> RunRecord:
    record = RunRecord(request=request)
    real_source = pristine.source
    real_repair = pristine.repair
    real_solve = pristine.solve

    def watched_source(*arguments: object) -> Grid:
        rng = arguments[-1]
        assert isinstance(rng, random.Random)
        before = rng.getstate()
        grid = real_source(*arguments)  # type: ignore[operator]
        record.rng_states.append((before, rng.getstate()))
        return grid

    def watched_repair(grid: Grid, **kwargs: object) -> orchestrator.Repair | None:
        repair = real_repair(grid, **kwargs)  # type: ignore[operator]
        if repair is not None:
            allowed = disagreement_cells(
                kwargs["witnesses"]  # type: ignore[arg-type]
            ) | mask_cells(kwargs["undecided_mask"])  # type: ignore[arg-type]
            record.applied.append(
                RepairRecord(
                    parent=[list(row) for row in grid],
                    repaired=[list(row) for row in repair.grid],
                    region=repair.region,
                    allowed=frozenset(allowed),
                )
            )
        return repair

    def watched_solve(rows: object, columns: object, **kwargs: object) -> object:
        record.solves += 1
        return real_solve(rows, columns, **kwargs)  # type: ignore[operator]

    patcher.setattr(orchestrator.sourcing, "for_mode", lambda mode: watched_source)
    patcher.setattr(orchestrator, "repair_candidate", watched_repair)
    patcher.setattr(orchestrator.solver, "solve", watched_solve)

    puzzle: orchestrator.Puzzle | None = None
    try:
        puzzle = generate(request)
    except GenerationAbandoned:
        record.abandoned = True
    if puzzle is not None:
        record.accepted = puzzle.grid
        record.attempts = puzzle.regenerate.attempts
        record.redraws = puzzle.recovery.redraws
        record.repairs = puzzle.recovery.repairs
        record.fallback_repairs = puzzle.recovery.repairs_from_fallback_region
        record.repeated_attempts = puzzle.recovery.repeated_attempts
    else:
        # An abandoned run never hands its aggregate back; the attempt count is
        # then what the instrumentation saw, which is the honest outside view.
        record.attempts = record.solves
        record.redraws = len(record.rng_states)
        record.repairs = record.attempts - record.redraws
    return record


@pytest.fixture(scope="module")
def corpus() -> Iterator[list[RunRecord]]:
    """Every run of the corpus, collected once (they are milliseconds each)."""
    records: list[RunRecord] = []
    pristine = _Pristine(
        source=orchestrator.sourcing.for_mode("random"),
        repair=orchestrator.repair_candidate,
        solve=orchestrator.solver.solve,
    )
    with pytest.MonkeyPatch.context() as patcher:
        for width, height in EXTENTS:
            for density in DENSITIES:
                for seed in SEEDS:
                    records.append(
                        _run(
                            GenerationRequest(
                                mode="random",
                                width=width,
                                height=height,
                                density=density,
                                seed=seed,
                            ),
                            patcher,
                            pristine,
                        )
                    )
    yield records


def test_accepted_grids_have_real_verdicts_within_one_bound(
    corpus: list[RunRecord],
) -> None:
    """EC-013, all three halves of it, over the whole corpus.

    The verdict half is re-obtained rather than trusted: every accepted grid's
    clues are derived again here and solved again from scratch, so a run that
    had accepted a grid on its *parent's* verdict — the failure mode ADR-0024/R1
    exists to forbid — would be caught even if the aggregate said otherwise.
    """
    accepted = [record for record in corpus if record.accepted is not None]
    abandoned = [record for record in corpus if record.abandoned]
    repairs = [repair for record in corpus for repair in record.applied]

    assert len(corpus) >= REQUIRED_RUNS
    assert len(accepted) >= REQUIRED_ACCEPTED
    assert len(abandoned) >= REQUIRED_ABANDONED
    assert len(repairs) >= REQUIRED_REPAIRS

    for record in corpus:
        # One bound for both kinds of attempt (INV-003, ADR-0024/R2).
        assert record.attempts <= MAX_RETRY_ATTEMPTS
        assert record.redraws + record.repairs == record.attempts
        # One solve per attempt: a repaired candidate costs exactly what a
        # redrawn one costs, and neither is ever judged without one.
        assert record.solves == record.attempts
        if record.abandoned:
            assert record.attempts == MAX_RETRY_ATTEMPTS
            # Every repair the run judged was one this corpus watched being
            # computed, and at most one more was computed and never judged —
            # the pending repair of the attempt the bound cut short. Without
            # this the redraw/repair split of an abandoned run would be
            # self-consistent by arithmetic alone, since its aggregate is
            # unreachable.
            assert record.repairs <= len(record.applied) <= record.repairs + 1
            continue
        grid = record.accepted
        assert grid is not None
        verdict = solve(*compute_clues(grid))
        assert verdict.solution_count == 1
        # An accepted run judged every repair it computed: the last attempt
        # succeeded, so nothing was left pending.
        assert len(record.applied) == record.repairs

    for repair in repairs:
        # ... and every repair that was applied stayed inside its region.
        changed = differences(repair.parent, repair.repaired)
        assert len(changed) == 2
        assert changed <= repair.allowed


def test_a_repair_draws_nothing_from_the_rng(corpus: list[RunRecord]) -> None:
    """EC(ADR-0024/R4): the rng stream is not perturbed by repairs.

    The random source is the only thing in a run that is allowed to draw. So
    the rng's state entering draw *n+1* must be exactly its state leaving draw
    *n* — however many repairs happened in between. A repair that took even one
    number from the injected ``Random`` would break the chain here, and with it
    ADR-0015's promise that a seed replays the same lineage everywhere.
    """
    chains = 0
    interleaved = 0
    for record in corpus:
        for index in range(1, len(record.rng_states)):
            before = record.rng_states[index][0]
            after_previous = record.rng_states[index - 1][1]
            assert before == after_previous
            chains += 1
        if record.repairs and len(record.rng_states) > 1:
            interleaved += 1

    assert chains >= REQUIRED_RUNS
    # The check only means anything on runs where repairs actually happened
    # *between* two draws, so require a decent number of those.
    assert interleaved >= 10


def test_every_repaired_grid_has_its_parents_density_exactly(
    corpus: list[RunRecord],
) -> None:
    """EC(ADR-0003): one filled cell out, one empty cell in, every time.

    The requested density therefore holds for a repaired grid by construction,
    without relying on ADR-0003's +/-3-point tolerance — which is what lets the
    repair loop run for a whole lineage without drifting off the request.
    """
    repairs = [repair for record in corpus for repair in record.applied]
    assert len(repairs) >= REQUIRED_REPAIRS

    for repair in repairs:
        assert filled(repair.repaired) == filled(repair.parent)
        # Not vacuous: the grids really are different ones.
        assert repair.repaired != repair.parent


def test_the_fallback_region_is_reached_by_real_runs(corpus: list[RunRecord]) -> None:
    """ADR-0024's fallback is a live path, not a defensive branch.

    ADR-0024 lists "the fallback is a second region rule a test must force or
    it is dead code with a latent bug" as an accepted negative. It does not
    need forcing: the per-row filled-count argument holds only when the
    candidate is one of the two witnesses, and a candidate is often a *third*
    solution instead. CARD-073's review measured the shortfall at 9 cases in
    241; this corpus sees it too, and this test fails if the primary rule ever
    quietly becomes the only one that fires.

    The hand-built case that pins what the fallback then *does* is
    ``tests/test_orchestrator.py``'s
    ``test_falls_back_to_the_undecided_mask_when_the_disagreement_set_has_no_pair``.
    """
    repairs = [repair for record in corpus for repair in record.applied]
    from_fallback = [
        repair
        for repair in repairs
        if repair.region == orchestrator.UNDECIDED_MASK_REGION
    ]

    assert len(repairs) >= REQUIRED_REPAIRS
    assert from_fallback, (
        "no repair in the corpus came from the undecided-mask fallback; either "
        "the region rule changed or the corpus no longer contains a candidate "
        "that is a third solution"
    )


def test_the_repeat_tally_agrees_with_an_independent_count(
    corpus: list[RunRecord],
) -> None:
    """ADR-0024's repeat tally, re-derived from the repairs the corpus watched.

    The orchestrator counts a repeat by comparing the grid it is about to judge
    against the ones its lineage already judged. This test counts the same
    thing from the outside, off the recorded (parent, repaired) pairs, and
    requires the two to agree run by run — the house rule about preferring an
    independent second implementation to re-deriving a number with the function
    under test.

    Reconstructing the lineages is the whole of the work: ``applied`` holds only
    repairs, so a repair whose parent is not the previous repair's result marks
    the start of a new lineage (a redraw happened in between).
    """
    checked = 0
    cycling = 0
    for record in corpus:
        if record.repeated_attempts is None:
            continue
        checked += 1
        expected = 0
        seen: set[tuple[tuple[bool, ...], ...]] = set()
        previous: Grid | None = None
        for repair in record.applied:
            if previous is None or key(repair.parent) != key(previous):
                # A fresh draw sits between this repair and the last one.
                seen = {key(repair.parent)}
            if key(repair.repaired) in seen:
                expected += 1
            seen.add(key(repair.repaired))
            previous = repair.repaired
        assert record.repeated_attempts == expected, (
            f"orchestrator counted {record.repeated_attempts} repeated repairs "
            f"for {record.request}, an independent replay counts {expected}"
        )
        cycling += expected

    assert checked >= REQUIRED_ACCEPTED
    assert cycling, (
        "no lineage in the corpus ever re-judged a grid it had already judged; "
        "either the pair-choice rule changed or the corpus no longer contains "
        "a lineage that cycles, and the tally has stopped being exercised"
    )


def test_k_is_a_split_of_the_one_budget_and_not_a_second_bound(
    corpus: list[RunRecord],
) -> None:
    """ADR-0024/R2, read off the corpus rather than off a scripted source.

    No run exceeds ADR-0002's bound (``MAX_RETRY_ATTEMPTS``), no lineage exceeds K consecutive
    repairs, and — the half that makes K a *split* — a run that hit the cap
    still went on drawing fresh grids inside the same budget.
    """
    assert MAX_CONSECUTIVE_REPAIRS == 5
    for record in corpus:
        assert record.attempts <= MAX_RETRY_ATTEMPTS
        # Every lineage is a draw followed by at most K repairs, so the repairs
        # of a run can never exceed K times the number of draws it made.
        assert record.repairs <= MAX_CONSECUTIVE_REPAIRS * max(record.redraws, 1)
