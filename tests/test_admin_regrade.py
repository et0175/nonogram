"""CARD-077 — the re-grade batch, its safety rules, and migration 006.

    TestRegrade_RewritesGradeAndStrategiesFromOneSolve   (AC-A)
        -> test_a_uniquely_solvable_row_gets_the_pipeline_grade
        -> test_the_stored_strategies_are_the_solves_own_rungs
        -> test_the_legacy_columns_hold_the_pre_run_values
        -> test_the_stored_score_still_classifies_as_the_stored_tier
    TestRegrade_IsIdempotentAndPreservesLegacyColumns    (AC-B)
        -> test_two_runs_leave_byte_identical_rows
        -> test_the_second_run_does_not_overwrite_the_legacy_columns
        -> test_a_row_that_had_no_grade_cannot_have_one_invented_for_its_legacy
    TestRegrade_SkipsUnsolvableRowsAndReportsThem       (AC-C)
        -> test_an_ambiguous_row_is_not_touched
        -> test_an_ambiguous_row_is_reported_with_its_reason
        -> test_a_timed_out_row_is_not_touched_and_is_reported
        -> test_an_unreadable_grid_is_reported_rather_than_fatal
        -> test_a_skipped_row_never_reaches_the_legacy_columns
    TestRegrade_DryRunWritesNothing                     (AC-D)
        -> test_the_database_file_is_byte_identical_after_a_dry_run
        -> test_the_dry_run_reports_what_the_write_run_produces
    TestMigration006_ExpandOnlyAndReversible            (AC-E)
        -> test_upgrade_adds_two_nullable_columns_in_place
        -> test_upgrade_leaves_existing_rows_and_strategies_untouched
        -> test_downgrade_removes_exactly_those_two_columns
    TestRegrade_EntersSolverOncePerRow                  (EC ADR-0029/R2)
        -> test_the_solver_is_entered_exactly_once_per_row
        -> test_a_skipped_row_costs_one_solve_too_not_two

The determinism property (EC NFR-007 / CON-014,
``PropertyTest_Regrade_PureFunctionOfStoredGrid``) lives in
``tests/property/test_regrade_determinism.py``.

**No test here opens the live ``nonogram_admin.db``** (guardrail G-1). Every
fixture builds its own SQLite file under ``tmp_path`` from the ORM metadata, so
a test run cannot reach the owner's data even by accident — which is why the
ambiguous-row cases construct an ambiguous grid by hand rather than relying on
the real table happening to contain one.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from nonogram.admin.regrade import (
    NO_LEGACY_TIER,
    Grade,
    Skip,
    SkipReason,
    grade_stored_grid,
    regrade,
)
# Private, and imported deliberately: `_as_grid` and `_stored_score` are the two
# places where a stored row stops being JSON and starts being a puzzle, and both
# have behaviour worth pinning that no public entry point exposes directly.
from nonogram.admin.regrade import _as_grid, _stored_score
from nonogram.clues import compute_clues
from nonogram.db.models import Base, Puzzle
from nonogram.difficulty import Tier, classify, score_difficulty
from nonogram.solver import solve

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Grids the whole file is built on
# --------------------------------------------------------------------------

#: A grid whose clues have exactly one solution — the row the batch is *for*.
#: Deliberately not symmetric in any axis, because the ambiguity below is
#: exactly what symmetry produces.
UNIQUE_GRID = [
    [True, True, True, False, False],
    [True, False, False, False, True],
    [True, True, True, True, False],
    [False, False, True, False, False],
    [True, True, True, True, True],
]

#: Two solutions, not one: the clues are "one filled cell per row and per
#: column" on a 2x2, which both diagonals satisfy. CON-005 says a clue set like
#: this is not a puzzle and has no grade, so the batch must leave it alone.
AMBIGUOUS_GRID = [
    [True, False],
    [False, True],
]

#: A second unique grid, so tests that need two distinct rows do not lean on
#: two copies of one.
OTHER_UNIQUE_GRID = [
    [True, False, True],
    [True, True, True],
    [False, False, True],
]

#: A grid whose verifying solve has to *search*: uniquely solvable, but line
#: logic alone does not finish it, so the solver branches (14 nodes) and
#: ADR-0025's EC-015 makes the tier ``Tier.GUESS`` whatever the score is.
#:
#: It exists because every other grid in this file is line-solvable, which left
#: the one test that names ``guess`` asserting ``False == False`` — it could not
#: reach the branch it was written for (CARD-077 review cycle 1, F-001). That is
#: not a hypothetical gap: commit bb1d5f6 records a real ``Tier.GUESS`` row in
#: the production database, so the branch is on the live path of the migration
#: this card performs.
#:
#: Found by seeded search over square grids at density 0.35..0.6, smallest
#: first; 9x9 is the first extent where a branching unique grid turns up at all.
#: Pinned as literal cells rather than regenerated, so the fixture cannot drift
#: with the search.
GUESS_GRID = [
    [False, False, True, True, False, False, True, True, False],
    [True, False, True, False, False, True, False, False, True],
    [True, False, False, True, False, False, True, False, False],
    [False, False, False, True, True, False, True, False, False],
    [False, True, False, False, True, False, False, False, False],
    [True, False, True, True, False, False, False, False, False],
    [False, True, False, True, True, False, False, False, False],
    [False, True, False, False, False, False, False, True, True],
    [False, True, False, False, False, False, False, False, False],
]


def _assert_solution_counts() -> None:
    """The fixtures' premise, checked against the solver rather than asserted.

    If a future solver change made ``AMBIGUOUS_GRID`` unique, every AC-C test
    below would pass for the wrong reason — they would be exercising the
    re-grade path and asserting nothing. Pinning the premise here turns that
    into one obvious failure instead of four silent ones.
    """
    assert solve(*compute_clues(UNIQUE_GRID)).solution_count == 1
    assert solve(*compute_clues(OTHER_UNIQUE_GRID)).solution_count == 1
    assert solve(*compute_clues(AMBIGUOUS_GRID)).solution_count == 2

    # GUESS_GRID's premise is two facts, not one: unique *and* reached by
    # search. A solver improvement that settled it by line logic alone would
    # leave the guess tests below passing vacuously again, which is exactly the
    # failure this fixture was added to end.
    guess_result = solve(*compute_clues(GUESS_GRID))
    assert guess_result.solution_count == 1
    assert guess_result.signals.branch_nodes > 0, (
        "GUESS_GRID no longer branches, so nothing in this file reaches "
        "Tier.GUESS and the guess assertions are vacuous"
    )


def test_the_fixture_grids_are_what_the_tests_assume() -> None:
    _assert_solution_counts()


# --------------------------------------------------------------------------
# A database of our own, never the owner's (G-1)
# --------------------------------------------------------------------------


def _new_db(path: Path):
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    return engine


def _add_row(
    engine,
    grid,
    *,
    name: str = "row",
    score: int | None = 70,
    tier: str | None = "Medium",
    strategies=("LineLogic", "ConstraintProp"),
    status: str = "draft",
    row_id: uuid.UUID | None = None,
) -> str:
    """Insert one puzzle row in the shape the live table actually holds.

    The defaults are the live rows' own shape: a ``Medium`` display-spelled
    tier, a score in the 65..100 band, and a two-element strategies list that
    names no rung on ADR-0029's ladder. That is what the batch has to replace.
    """
    row_id = row_id or uuid.uuid4()
    clues = compute_clues(grid) if grid and isinstance(grid[0], list) else None
    with sessionmaker(bind=engine)() as session:
        session.add(
            Puzzle(
                id=row_id,
                grid=grid,
                clues_rows=[list(c) for c in clues.rows] if clues else [],
                clues_cols=[list(c) for c in clues.columns] if clues else [],
                width=len(grid[0]) if clues else 0,
                height=len(grid) if clues else 0,
                difficulty_score=score,
                difficulty_tier=tier,
                strategies_used=list(strategies),
                status=status,
                puzzle_name=name,
            )
        )
        session.commit()
    return str(row_id)


def _run(engine, *, dry_run: bool = False, **kwargs):
    with sessionmaker(bind=engine)() as session:
        report = regrade(session, dry_run=dry_run, **kwargs)
        session.commit()
    return report


def _row(engine, row_id: str) -> dict:
    """One row's graded columns, as plain values a comparison can hold onto."""
    with sessionmaker(bind=engine)() as session:
        row = session.get(Puzzle, uuid.UUID(row_id))
        assert row is not None
        return {
            "difficulty_score": row.difficulty_score,
            "difficulty_tier": row.difficulty_tier,
            "strategies_used": row.strategies_used,
            "legacy_difficulty_score": row.legacy_difficulty_score,
            "legacy_difficulty_tier": row.legacy_difficulty_tier,
            "status": row.status,
        }


def _expected_grade(grid) -> Grade:
    """What the pipeline says this grid's grade is, derived independently.

    Through ``clues`` -> ``solver`` -> ``difficulty`` directly, not through
    ``regrade``: a test that called the function under test to compute its own
    expectation would assert the batch against itself. The ceiling is spelled
    out here for the same reason — it is the contract ("the stored integer
    stays in the band its float came from"), not a call into the production
    helper.
    """
    result = solve(*compute_clues(grid))
    score = score_difficulty(result.signals)
    tier = classify(score, result.signals.branch_nodes)
    return Grade(
        score=math.ceil(score),
        tier=tier,
        strategies=tuple(result.signals.rungs),
    )


# --------------------------------------------------------------------------
# AC-A — the rewrite
# --------------------------------------------------------------------------


class TestRegrade_RewritesGradeAndStrategiesFromOneSolve:
    """AC-A: a graded row's three columns are what the current pipeline says."""

    def test_a_uniquely_solvable_row_gets_the_pipeline_grade(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "a.db")
        row_id = _add_row(engine, UNIQUE_GRID)

        _run(engine)

        expected = _expected_grade(UNIQUE_GRID)
        row = _row(engine, row_id)
        assert row["difficulty_tier"] == expected.tier.value
        assert row["difficulty_score"] == expected.score

    def test_the_stored_strategies_are_the_solves_own_rungs(self, tmp_path: Path) -> None:
        """FR-029's list, and not the ``["LineLogic", "ConstraintProp"]`` that
        was there — a pair of names that appears nowhere on ADR-0029's ladder.
        """
        engine = _new_db(tmp_path / "a.db")
        row_id = _add_row(engine, UNIQUE_GRID)

        _run(engine)

        expected = _expected_grade(UNIQUE_GRID)
        assert _row(engine, row_id)["strategies_used"] == list(expected.strategies)

    def test_the_legacy_columns_hold_the_pre_run_values(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "a.db")
        row_id = _add_row(engine, UNIQUE_GRID, score=75, tier="Medium")

        _run(engine)

        row = _row(engine, row_id)
        assert row["legacy_difficulty_score"] == 75
        assert row["legacy_difficulty_tier"] == "Medium"
        assert row["difficulty_tier"] != "Medium", (
            "the fixture is only interesting if the grade actually moved"
        )

    def test_the_stored_score_still_classifies_as_the_stored_tier(
        self, tmp_path: Path
    ) -> None:
        """The column is an Integer, so the float has to lose its fraction —
        and it must not lose its band on the way out.

        A row whose stored number reads back as a different tier than the
        string beside it is a row that contradicts itself, and every consumer
        that compares the two would be right to disbelieve both.
        """
        engine = _new_db(tmp_path / "a.db")
        ids = [
            _add_row(engine, UNIQUE_GRID, name="one"),
            _add_row(engine, OTHER_UNIQUE_GRID, name="two"),
        ]

        _run(engine)

        for row_id in ids:
            row = _row(engine, row_id)
            assert classify(row["difficulty_score"], 0).value == row["difficulty_tier"]

    def test_a_row_is_graded_by_its_grid_not_by_its_stored_clues(
        self, tmp_path: Path
    ) -> None:
        """CARD-051: the one encoder is ``clues.compute_clues``.

        The stored ``clues_rows``/``clues_cols`` are display copies. Here they
        are deliberately wrong; the grade must be the grid's all the same.
        """
        engine = _new_db(tmp_path / "a.db")
        row_id = _add_row(engine, UNIQUE_GRID)
        with sessionmaker(bind=engine)() as session:
            row = session.get(Puzzle, uuid.UUID(row_id))
            row.clues_rows = [[99]] * len(UNIQUE_GRID)
            row.clues_cols = [[99]] * len(UNIQUE_GRID[0])
            session.commit()

        _run(engine)

        expected = _expected_grade(UNIQUE_GRID)
        assert _row(engine, row_id)["difficulty_tier"] == expected.tier.value


# --------------------------------------------------------------------------
# AC-B — idempotent, deterministic, and the legacy columns are written once
# --------------------------------------------------------------------------


class TestRegrade_IsIdempotentAndPreservesLegacyColumns:
    """AC-B / NFR-007 / CON-014: same rows in, identical rows out."""

    def test_two_runs_leave_byte_identical_rows(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "b.db")
        ids = [
            _add_row(engine, UNIQUE_GRID, name="one"),
            _add_row(engine, OTHER_UNIQUE_GRID, name="two"),
            _add_row(engine, AMBIGUOUS_GRID, name="ambiguous"),
        ]

        _run(engine)
        after_first = [_row(engine, row_id) for row_id in ids]
        _run(engine)
        after_second = [_row(engine, row_id) for row_id in ids]

        assert after_first == after_second

    def test_the_second_run_does_not_overwrite_the_legacy_columns(
        self, tmp_path: Path
    ) -> None:
        engine = _new_db(tmp_path / "b.db")
        row_id = _add_row(engine, UNIQUE_GRID, score=88, tier="Hard")

        _run(engine)
        _run(engine)

        row = _row(engine, row_id)
        assert row["legacy_difficulty_score"] == 88
        assert row["legacy_difficulty_tier"] == "Hard"

    def test_a_row_that_had_no_grade_cannot_have_one_invented_for_its_legacy(
        self, tmp_path: Path
    ) -> None:
        """The case a NULL-guard alone gets wrong, and the reason for the sentinel.

        A row with no stored grade leaves nothing to preserve. If "already
        captured?" were answered by ``legacy IS NULL``, the first run would
        write NULL, the guard would still read "not captured", and the *second*
        run would copy in the values the *first* run produced — legacy columns
        quietly holding ADR-0029 grades labelled as pre-run ones.
        """
        engine = _new_db(tmp_path / "b.db")
        row_id = _add_row(engine, UNIQUE_GRID, score=None, tier=None)

        _run(engine)
        first = _row(engine, row_id)
        _run(engine)
        second = _row(engine, row_id)

        assert first["legacy_difficulty_tier"] == NO_LEGACY_TIER
        assert first["legacy_difficulty_score"] is None
        assert second["legacy_difficulty_tier"] == NO_LEGACY_TIER
        assert second["legacy_difficulty_score"] is None


# --------------------------------------------------------------------------
# AC-C — safety: what the batch refuses to grade, it refuses to touch
# --------------------------------------------------------------------------


class TestRegrade_SkipsUnsolvableRowsAndReportsThem:
    """AC-C / CON-005 / ADR-0011. The skip path, given first-class treatment.

    The ambiguous row is constructed here rather than taken from real data:
    a test that depended on the stored table containing a broken row would
    stop testing anything the moment the table was cleaned up.
    """

    def test_an_ambiguous_row_is_not_touched(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "c.db")
        row_id = _add_row(engine, AMBIGUOUS_GRID, score=65, tier="Medium", status="approved")
        before = _row(engine, row_id)

        _run(engine)

        assert _row(engine, row_id) == before, (
            "a non-unique row must be left exactly as it was — grade, "
            "strategies and status alike; cleaning it up is a different card"
        )

    def test_an_ambiguous_row_is_reported_with_its_reason(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "c.db")
        row_id = _add_row(engine, AMBIGUOUS_GRID)

        report = _run(engine)

        (skipped,) = report.skipped
        assert skipped.puzzle_id == row_id
        assert skipped.skip.reason is SkipReason.NOT_UNIQUE
        assert "2 or more" in skipped.skip.detail
        assert report.skips_by_reason[SkipReason.NOT_UNIQUE] == 1

    def test_a_timed_out_row_is_not_touched_and_is_reported(self, tmp_path: Path) -> None:
        """ADR-0011: every solve is deadline-bounded, and a timeout is not a verdict."""
        engine = _new_db(tmp_path / "c.db")
        row_id = _add_row(engine, UNIQUE_GRID)
        before = _row(engine, row_id)

        report = _run(engine, budget_seconds=-1.0)

        (skipped,) = report.skipped
        assert skipped.skip.reason is SkipReason.TIMED_OUT
        assert _row(engine, row_id) == before

    @pytest.mark.parametrize(
        "grid",
        [
            pytest.param([], id="empty"),
            pytest.param([[True, False], [True]], id="ragged"),
            pytest.param([[]], id="empty-row"),
            pytest.param("not a grid at all", id="not-a-list"),
            pytest.param([True, False], id="flat-list"),
        ],
    )
    def test_an_unreadable_grid_is_reported_rather_than_fatal(
        self, tmp_path: Path, grid
    ) -> None:
        """A batch that died on row 3 of 36 would leave the table half re-graded."""
        engine = _new_db(tmp_path / "c.db")
        with sessionmaker(bind=engine)() as session:
            session.add(
                Puzzle(
                    id=uuid.uuid4(),
                    grid=grid,
                    clues_rows=[],
                    clues_cols=[],
                    width=0,
                    height=0,
                    difficulty_score=70,
                    difficulty_tier="Medium",
                )
            )
            session.commit()

        report = _run(engine)

        (skipped,) = report.skipped
        assert skipped.skip.reason is SkipReason.UNREADABLE_GRID

    def test_a_skipped_row_never_reaches_the_legacy_columns(self, tmp_path: Path) -> None:
        """The legacy columns record an overwrite. A skipped row had none."""
        engine = _new_db(tmp_path / "c.db")
        row_id = _add_row(engine, AMBIGUOUS_GRID)

        _run(engine)

        row = _row(engine, row_id)
        assert row["legacy_difficulty_score"] is None
        assert row["legacy_difficulty_tier"] is None

    def test_one_bad_row_does_not_stop_the_good_ones(self, tmp_path: Path) -> None:
        engine = _new_db(tmp_path / "c.db")
        bad = _add_row(engine, AMBIGUOUS_GRID, name="bad")
        good = _add_row(engine, UNIQUE_GRID, name="good")

        report = _run(engine)

        assert report.row_count == 2
        assert {o.puzzle_id for o in report.regraded} == {good}
        assert {o.puzzle_id for o in report.skipped} == {bad}


# --------------------------------------------------------------------------
# AC-D — the dry run
# --------------------------------------------------------------------------


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestRegrade_DryRunWritesNothing:
    """AC-D: the preview costs a solve per row and a write of nothing."""

    def test_the_database_file_is_byte_identical_after_a_dry_run(
        self, tmp_path: Path
    ) -> None:
        """Asserted on the file's bytes, not on the rows.

        Reading the rows back would only prove the *values* did not change; the
        claim the confirmation page makes is stronger than that — that nothing
        was written at all.
        """
        path = tmp_path / "d.db"
        engine = _new_db(path)
        _add_row(engine, UNIQUE_GRID, name="one")
        _add_row(engine, AMBIGUOUS_GRID, name="two")
        engine.dispose()

        before = _digest(path)
        engine = create_engine(f"sqlite:///{path}")
        report = _run(engine, dry_run=True)
        engine.dispose()

        assert report.dry_run is True
        assert report.regraded, "the dry run must have had something to report"
        assert _digest(path) == before

    def test_the_dry_run_reports_what_the_write_run_produces(
        self, tmp_path: Path
    ) -> None:
        """The same rows through both paths, compared outcome by outcome.

        This is the property the confirmation page rests on: the owner approves
        a report, and the run they approve is the run that happens.
        """
        rows = [
            (UNIQUE_GRID, "one"),
            (OTHER_UNIQUE_GRID, "two"),
            (AMBIGUOUS_GRID, "ambiguous"),
        ]
        previewed = _new_db(tmp_path / "preview.db")
        written = _new_db(tmp_path / "written.db")
        # The same primary keys on both sides, so the two reports are
        # comparable row for row rather than only in aggregate.
        for grid, name in rows:
            row_id = uuid.uuid4()
            for engine in (previewed, written):
                _add_row(engine, grid, name=name, row_id=row_id)

        preview = _run(previewed, dry_run=True)
        applied = _run(written, dry_run=False)

        assert preview.distribution == applied.distribution
        assert preview.moves == applied.moves
        assert preview.skips_by_reason == applied.skips_by_reason
        assert [
            (o.puzzle_id, o.grade, o.skip) for o in preview.outcomes
        ] == [(o.puzzle_id, o.grade, o.skip) for o in applied.outcomes]


# --------------------------------------------------------------------------
# AC-E — migration 006
# --------------------------------------------------------------------------


def _alembic_config(url: str):
    """A config built in code rather than from ``alembic.ini``.

    Same script directory and same URL, but no ``config_file_name`` — so
    alembic skips ``fileConfig``, and running a migration inside the test
    process does not reconfigure the whole suite's logging on its way past.
    """
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture
def pre_006_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A database in the shape it had *before* 006, with a row already in it.

    Built by creating today's schema and dropping the two new columns again,
    rather than by replaying 001..005: what AC-E is about is whether 006
    upgrades a table that already holds data, and this produces exactly that
    table without making the test depend on five older migrations still
    running.
    """
    path = tmp_path / "pre006.db"
    url = f"sqlite:///{path}"
    engine = _new_db(path)
    row_id = _add_row(engine, UNIQUE_GRID, name="already here")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE puzzles DROP COLUMN legacy_difficulty_score"
        )
        connection.exec_driver_sql(
            "ALTER TABLE puzzles DROP COLUMN legacy_difficulty_tier"
        )
    engine.dispose()

    monkeypatch.setenv("DATABASE_URL", url)
    from alembic import command

    config = _alembic_config(url)
    command.stamp(config, "005")
    return path, url, row_id


def _columns(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("puzzles")}
    finally:
        engine.dispose()


class TestMigration006_ExpandOnlyAndReversible:
    """AC-E / G-2: expand-only, in place, and it comes back off cleanly."""

    def test_upgrade_adds_two_nullable_columns_in_place(self, pre_006_db) -> None:
        _path, url, _row_id = pre_006_db
        from alembic import command

        before = _columns(url)
        assert "legacy_difficulty_score" not in before

        command.upgrade(_alembic_config(url), "006")

        after = _columns(url)
        assert after - before == {"legacy_difficulty_score", "legacy_difficulty_tier"}
        assert before <= after, "expand-only: 006 may not drop or rename a column"

        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                nullable = {
                    column["name"]: column["nullable"]
                    for column in inspect(connection).get_columns("puzzles")
                }
        finally:
            engine.dispose()
        assert nullable["legacy_difficulty_score"] is True
        assert nullable["legacy_difficulty_tier"] is True

    def test_upgrade_leaves_existing_rows_and_strategies_untouched(
        self, pre_006_db
    ) -> None:
        _path, url, row_id = pre_006_db
        from alembic import command

        command.upgrade(_alembic_config(url), "006")

        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        "SELECT difficulty_score, difficulty_tier, strategies_used, "
                        "legacy_difficulty_score, legacy_difficulty_tier "
                        "FROM puzzles"
                    )
                ).one()
        finally:
            engine.dispose()

        assert row.difficulty_score == 70
        assert row.difficulty_tier == "Medium"
        assert "LineLogic" in row.strategies_used
        assert row.legacy_difficulty_score is None, (
            "006 must not backfill: NULL is the signal that a row has not been "
            "re-graded, and the batch's write-once guard reads it"
        )
        assert row.legacy_difficulty_tier is None

    def test_downgrade_removes_exactly_those_two_columns(self, pre_006_db) -> None:
        _path, url, row_id = pre_006_db
        from alembic import command

        before = _columns(url)
        command.upgrade(_alembic_config(url), "006")
        command.downgrade(_alembic_config(url), "005")

        assert _columns(url) == before

        engine = create_engine(url)
        try:
            with engine.connect() as connection:
                surviving = connection.execute(
                    text("SELECT count(*) FROM puzzles")
                ).scalar()
        finally:
            engine.dispose()
        assert surviving == 1, "a reversal is not a way to lose the table's rows"


# --------------------------------------------------------------------------
# EC(ADR-0029/R2) — one solve per row
# --------------------------------------------------------------------------


class TestRegrade_EntersSolverOncePerRow:
    """The solver is entered once per row, and everything graded comes from it.

    ADR-0029/R2's rule survives every other change to the difficulty model: a
    second entry to classify, or to re-derive the strategies list, would make
    the grade and the list two accounts of two different solves.
    """

    @pytest.fixture
    def counting_solve(self, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple] = []
        real = solve

        def counted(row_clues, column_clues, **kwargs):
            calls.append((row_clues, column_clues))
            return real(row_clues, column_clues, **kwargs)

        monkeypatch.setattr("nonogram.admin.regrade.solve", counted)
        return calls

    @pytest.mark.parametrize("row_count", [1, 3, 7])
    def test_the_solver_is_entered_exactly_once_per_row(
        self, tmp_path: Path, counting_solve, row_count: int
    ) -> None:
        engine = _new_db(tmp_path / "e.db")
        for index in range(row_count):
            _add_row(engine, UNIQUE_GRID, name=f"row-{index}")

        _run(engine)

        assert len(counting_solve) == row_count

    def test_a_skipped_row_costs_one_solve_too_not_two(
        self, tmp_path: Path, counting_solve
    ) -> None:
        """The uniqueness verdict and the grade come out of the same entry.

        A row that turns out ambiguous must not be solved again "to be sure" —
        the first solve already answered, and CON-005 makes that answer final.
        """
        engine = _new_db(tmp_path / "e.db")
        _add_row(engine, AMBIGUOUS_GRID, name="ambiguous")
        _add_row(engine, UNIQUE_GRID, name="unique")

        _run(engine)

        assert len(counting_solve) == 2


# --------------------------------------------------------------------------
# The grading function on its own, away from any database
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# The admin action — a confirmation page in front of the one point of no return
# --------------------------------------------------------------------------


class TestRegradeRoute_PreviewsBeforeItWrites:
    """Card item 4 / AC-F: the owner sees the report before anything moves.

    Thin on purpose. The batch's behaviour is tested above, directly; what is
    left to check here is the wiring — that GET really is the dry run, that
    POST really writes, and that the distribution the owner is asked to approve
    reaches the page.
    """

    @pytest.fixture
    def client(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        path = tmp_path / "route.db"
        engine = _new_db(path)
        self.unique_id = _add_row(engine, UNIQUE_GRID, name="a real puzzle")
        self.ambiguous_id = _add_row(engine, AMBIGUOUS_GRID, name="two solutions")
        engine.dispose()

        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path}")
        from nonogram.admin.app import create_app

        app = create_app()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.path = path
        with app.test_client() as client:
            yield client

    def test_get_previews_and_writes_nothing(self, client) -> None:
        before = _digest(self.path)

        response = client.get("/regrade")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Re-grade puzzles" in body
        assert "not uniquely solvable" in body, (
            "the skipped rows and their reasons are the part of this page that "
            "says what the run could not vouch for"
        )
        assert _digest(self.path) == before

    def test_post_applies_the_run_the_preview_described(self, client) -> None:
        client.get("/regrade")

        response = client.post("/regrade", follow_redirects=True)

        assert response.status_code == 200
        engine = create_engine(f"sqlite:///{self.path}")
        try:
            regraded = _row(engine, self.unique_id)
            untouched = _row(engine, self.ambiguous_id)
        finally:
            engine.dispose()

        assert regraded["difficulty_tier"] == _expected_grade(UNIQUE_GRID).tier.value
        assert regraded["legacy_difficulty_tier"] == "Medium"
        assert untouched["difficulty_tier"] == "Medium"
        assert untouched["legacy_difficulty_tier"] is None


# --------------------------------------------------------------------------
# The stored integer keeps the band its float came from (CARD-077 review F-002)
# --------------------------------------------------------------------------


class TestStoredScore_KeepsTheBandItsFloatCameFrom:
    """``_stored_score`` ceils rather than rounds, and these are the cases that
    tell the two apart.

    Cycle 1 measured that nothing in the suite could: the two hand fixtures both
    score exactly 33.0 — an integer, where ceil and round agree by construction
    — and across the 240-grid property corpus, 6 grids have a fractional score
    and *none* land where the two functions classify differently. So the
    decision the module's longest docstring defends was verified by no test at
    all. These assert it directly on the numbers rather than waiting for a grid
    that produces them.
    """

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            # Just inside a band's lower edge: the cases where rounding down
            # would carry the number back across into the band below.
            pytest.param(33.08, 34, id="line_dp-one-cell-above-its-floor"),
            pytest.param(33.5, 34, id="line_dp-midpoint"),
            pytest.param(66.04, 67, id="probe-one-cell-above-its-floor"),
            pytest.param(66.5, 67, id="probe-midpoint"),
            # Exact edges are whole numbers already and must not move.
            pytest.param(0.0, 0, id="floor-of-the-scale"),
            pytest.param(33.0, 33, id="easy-ceiling-exact"),
            pytest.param(66.0, 66, id="medium-ceiling-exact"),
            pytest.param(100.0, 100, id="top-of-the-scale"),
            # Out-of-range input is clamped, not wrapped.
            pytest.param(-0.5, 0, id="below-the-scale"),
            pytest.param(100.4, 100, id="above-the-scale"),
        ],
    )
    def test_the_integer_is_the_ceiling_within_the_scale(self, score, expected) -> None:
        assert _stored_score(score) == expected

    @pytest.mark.parametrize(
        "score",
        [0.01, 12.4, 32.99, 33.0, 33.08, 50.5, 65.99, 66.0, 66.04, 80.3, 99.9, 100.0],
    )
    def test_the_stored_integer_classifies_as_the_float_did(self, score) -> None:
        """The property the ceiling exists to hold, stated as the property.

        ``branch_nodes=0`` on both sides: this is about the score-to-band
        mapping, and EC-015's guess rule deliberately ignores the score
        entirely (see the GUESS case below, which is the documented exception).
        """
        assert classify(float(_stored_score(score)), 0) is classify(score, 0)

    def test_rounding_instead_of_ceiling_would_break_that(self) -> None:
        """The discriminating case, named.

        Without this the suite cannot tell ``math.ceil`` from ``round``, which
        is what cycle 1 found. 33.08 is a real score: a ``line_dp`` puzzle that
        settled one cell in roughly four hundred at its top rung.
        """
        assert classify(33.08, 0) is Tier.MEDIUM
        assert classify(float(round(33.08)), 0) is Tier.EASY, (
            "if this fails, rounding is no longer lossy here and the test "
            "above has stopped discriminating"
        )
        assert classify(float(_stored_score(33.08)), 0) is Tier.MEDIUM

    def test_a_guess_row_is_the_documented_exception(self) -> None:
        """EC-015 keys Tier.GUESS on a fact about the solve, not on the score,
        so a guess row's stored number need not read back as ``guess`` — and
        cannot, since no band maps to it.

        Pinned so the claim in ``_stored_score``'s docstring stays bounded to
        what it can actually promise.
        """
        graded = grade_stored_grid(GUESS_GRID)

        assert isinstance(graded, Grade)
        assert graded.tier is Tier.GUESS
        assert classify(float(graded.score), 0) is not Tier.GUESS


def test_a_branching_solve_ends_its_strategies_list_with_guess() -> None:
    """FR-029's list ends in ``guess`` when the verifying solve searched.

    The positive case, stated positively. The biconditional below is the honest
    shape of the rule but it cannot fail on a line-solvable grid, which is how
    the branch went untested through cycle 1 — so the branch is asserted here
    on a grid that actually reaches it.
    """
    graded = grade_stored_grid(GUESS_GRID)

    assert isinstance(graded, Grade)
    assert graded.tier is Tier.GUESS
    assert graded.strategies[-1] == "guess"
    # ``guess`` is appended to the rungs, not substituted for them: the list
    # still says how the line work went before the search started.
    assert graded.strategies[:-1], "the rungs the solve did use are still there"
    assert "guess" not in graded.strategies[:-1], "appended once, at the end"


def test_a_line_solvable_solve_has_no_guess_on_its_strategies_list() -> None:
    """The negative case, on the same rule. Together with the test above this
    is the biconditional — each half on a grid that can refute it."""
    graded = grade_stored_grid(UNIQUE_GRID)

    assert isinstance(graded, Grade)
    assert graded.tier is not Tier.GUESS
    assert "guess" not in graded.strategies


@pytest.mark.parametrize("grid", [UNIQUE_GRID, OTHER_UNIQUE_GRID, GUESS_GRID])
def test_guess_is_on_the_list_exactly_when_the_tier_says_so(grid) -> None:
    """ADR-0025/R2 read as one rule over every gradable fixture in the file.

    Parametrised over both sides of it, so the corpus this runs on can no
    longer be all-one-side without the parametrisation visibly shrinking.
    """
    graded = grade_stored_grid(grid)

    assert isinstance(graded, Grade)
    assert ("guess" in graded.strategies) == (graded.tier is Tier.GUESS)


@pytest.mark.parametrize(
    "junk",
    [
        pytest.param(None, id="none"),
        pytest.param(42, id="int"),
        pytest.param({}, id="dict"),
        pytest.param("[[true]]", id="json-text-not-decoded"),
        pytest.param([[True, False], [True]], id="ragged"),
    ],
)
def test_grade_stored_grid_reports_junk_rather_than_raising(junk) -> None:
    """Not "it returned something" — *what* it returned, and why.

    The previous form asserted ``is not None`` over a function that has no
    None path, so it could only fail by raising; and two of its five inputs
    (``[[None]]``, ``[["x", "y"]]``) are coerced into valid grids by
    ``_as_grid`` and were quietly exercising the happy path. Both are fixed
    here: these five are all genuinely unreadable, and the reason is asserted.
    """
    outcome = grade_stored_grid(junk)

    assert isinstance(outcome, Skip)
    assert outcome.reason is SkipReason.UNREADABLE_GRID


@pytest.mark.parametrize(
    ("grid", "filled"),
    [
        pytest.param([[None, None]], 0, id="null-cells-read-as-empty"),
        pytest.param([["x", "y"]], 2, id="truthy-strings-read-as-filled"),
        pytest.param([[1, 0]], 1, id="ints-read-as-bool"),
    ],
)
def test_a_grid_of_non_booleans_is_coerced_rather_than_refused(grid, filled) -> None:
    """``_as_grid`` reads truthiness, and that is deliberate — see its docstring.

    Pinned as its own test because it is the surprising half of the contract:
    the shape of a stored grid is validated strictly, its cell *type* is not.
    A row of JSON nulls is a grid of empty cells, not a data defect.
    """
    outcome = grade_stored_grid(grid)

    assert isinstance(outcome, Grade)
    assert sum(row.count(True) for row in _as_grid(grid)) == filled
