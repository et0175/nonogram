"""EC(NFR-007 / CON-014): a re-graded row is a pure function of its stored grid.

    PropertyTest_Regrade_PureFunctionOfStoredGrid
        -> test_the_grade_is_the_same_under_a_dilated_clock
        -> test_the_grade_is_the_same_whatever_the_budget
        -> test_two_runs_over_one_table_leave_identical_rows

The re-grade is the one point of no return in the 2026-09-12 delta: after it,
the stored grade is whatever this batch said, and there is no second opinion to
compare against. So "the same rows in produce the same rows out" has to be a
property over a corpus, not an example — an example passes for a batch that is
deterministic on the one grid somebody happened to pick.

Why the clock is the thing being dilated
----------------------------------------
CON-014 and ADR-0029/R3 forbid a clock reading from entering a grade, and
ADR-0013's ``time_pressure`` term is the reason the rule is written down: under
it, a boundary candidate scored differently on a slower machine, so ADR-0015's
"the same seed replays the same run" held only when no difficulty was requested.
ADR-0029 closed that structurally — ``elapsed_seconds`` is not a member of
``difficulty.SolverSignals``, so the scorer cannot read a clock it was never
handed — and this batch adds exactly one clock of its own: ADR-0011's per-row
deadline. The property below is that this clock can only decide *whether* a row
is graded, never *how*.

Test style (project CLAUDE.md)
------------------------------
No ``hypothesis`` — it is not in the dependency baseline. The corpus is built by
hand from a seeded ``random.Random`` and its size is asserted inside the tests,
so it cannot silently shrink to nothing. Each grid also carries its own seed in
the failure message, so a failing case is reproducible without re-running the
whole corpus.

Guardrail G-1: every database here is built under ``tmp_path`` from the ORM
metadata. The live ``nonogram_admin.db`` is never opened.
"""

from __future__ import annotations

import random
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nonogram.admin.regrade import Grade, grade_stored_grid, regrade
from nonogram.clues import compute_clues
from nonogram.db.models import Base, Puzzle

#: Enough cases that a determinism bug has to be systematic to hide, and small
#: enough extents that the whole corpus solves in well under a second. The
#: minimum is asserted in every test that walks it.
CORPUS_SEED = 20260914
CORPUS_SIZE = 240
MIN_CASES = 150


def _corpus() -> list[tuple[int, list[list[bool]]]]:
    """``(seed, grid)`` pairs — a spread of extents and densities, all seeded.

    Densities from sparse to dense on purpose: the interesting rows for this
    property are the ones near a band edge, and which grids those are is not
    something the test can know in advance.
    """
    cases: list[tuple[int, list[list[bool]]]] = []
    for index in range(CORPUS_SIZE):
        seed = CORPUS_SEED + index
        rng = random.Random(seed)
        height = rng.randint(4, 12)
        width = rng.randint(4, 12)
        density = rng.uniform(0.2, 0.8)
        grid = [
            [rng.random() < density for _ in range(width)] for _ in range(height)
        ]
        cases.append((seed, grid))
    return cases


def _grades(cases) -> dict[int, Grade]:
    """The graded cases of a corpus, keyed by seed. Ambiguous grids drop out."""
    graded = {}
    for seed, grid in cases:
        outcome = grade_stored_grid(grid, deadline=time.monotonic() + 60.0)
        if isinstance(outcome, Grade):
            graded[seed] = outcome
    return graded


def test_the_corpus_is_large_enough_to_mean_anything() -> None:
    """Guard the corpus: a property over three cases is an example.

    Size is not the only thing that can quietly degrade. A corpus of grids that
    all settle at the bottom rung would still be 150 cases and would exercise
    one branch of the ladder, so the rung coverage is pinned too — the measured
    spread is 148 ``simple_overlap``, 3 reaching ``line_dp`` and 4 reaching
    ``probe_contradiction``, i.e. all three tiers that a line-solvable puzzle
    can land in.
    """
    graded = _grades(_corpus())
    assert len(graded) >= MIN_CASES, (
        f"only {len(graded)} of {CORPUS_SIZE} corpus grids were uniquely "
        "solvable; the property tests below would be asserting almost nothing"
    )

    tiers = {grade.tier for grade in graded.values()}
    rungs = {rung for grade in graded.values() for rung in grade.strategies}
    assert len(tiers) >= 3, f"the corpus only reaches {tiers}"
    assert len(rungs) >= 3, f"the corpus only exercises {rungs}"


def test_the_grade_is_the_same_under_a_dilated_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same grids, graded on a machine where time runs eight times faster.

    ``time.monotonic`` is dilated globally, so the solver's own deadline checks
    see the dilation too — which is the honest version of "a slower machine",
    and the one ADR-0013's ``time_pressure`` term would have failed.
    """
    cases = _corpus()
    baseline = _grades(cases)
    assert len(baseline) >= MIN_CASES

    real_monotonic = time.monotonic
    origin = real_monotonic()
    monkeypatch.setattr(
        time, "monotonic", lambda: origin + (real_monotonic() - origin) * 8.0
    )

    dilated = _grades(cases)

    assert dilated.keys() == baseline.keys(), (
        "the dilated clock changed which rows could be graded at all — the "
        "budget is too tight for this corpus and the test is measuring the "
        "machine rather than the property"
    )
    for seed in baseline:
        assert dilated[seed] == baseline[seed], f"grade moved under dilation, seed {seed}"


@pytest.mark.parametrize("budget", [1.0, 5.0, 60.0, 3600.0])
def test_the_grade_is_the_same_whatever_the_budget(budget: float) -> None:
    """ADR-0011's deadline decides *whether* a row is graded, never *how*.

    A budget that turned out too tight would show up as a missing key, not as a
    different grade — which is the distinction the assertion below draws.
    """
    cases = _corpus()
    baseline = _grades(cases)
    assert len(baseline) >= MIN_CASES

    under_budget = {}
    for seed, grid in cases:
        outcome = grade_stored_grid(grid, deadline=time.monotonic() + budget)
        if isinstance(outcome, Grade):
            under_budget[seed] = outcome

    for seed, grade in under_budget.items():
        assert grade == baseline[seed], f"grade moved with the budget, seed {seed}"


def test_two_runs_over_one_table_leave_identical_rows(tmp_path: Path) -> None:
    """The whole batch, twice, over a table built from the corpus.

    The end-to-end statement of the property: not just that the grading
    function is pure, but that running the operational job twice is the same as
    running it once — legacy columns included.
    """
    cases = _corpus()[:60]
    path = tmp_path / "corpus.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)

    factory = sessionmaker(bind=engine)
    with factory() as session:
        for seed, grid in cases:
            clues = compute_clues(grid)
            session.add(
                Puzzle(
                    id=uuid.uuid4(),
                    grid=grid,
                    clues_rows=[list(clue) for clue in clues.rows],
                    clues_cols=[list(clue) for clue in clues.columns],
                    width=len(grid[0]),
                    height=len(grid),
                    difficulty_score=70,
                    difficulty_tier="Medium",
                    strategies_used=["LineLogic", "ConstraintProp"],
                    puzzle_name=f"seed-{seed}",
                )
            )
        session.commit()

    def snapshot() -> list[tuple]:
        with factory() as session:
            return [
                (
                    str(row.id),
                    row.difficulty_score,
                    row.difficulty_tier,
                    tuple(row.strategies_used or ()),
                    row.legacy_difficulty_score,
                    row.legacy_difficulty_tier,
                )
                for row in session.query(Puzzle).order_by(Puzzle.id).all()
            ]

    def run() -> None:
        with factory() as session:
            regrade(session, dry_run=False)
            session.commit()

    run()
    first = snapshot()
    run()
    second = snapshot()

    assert len(first) == len(cases)
    assert first == second
