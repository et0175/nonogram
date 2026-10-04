"""CARD-152: ``scripts/run_admin_tests.sh`` points the suite at the database you chose.

It used to hardcode ``DATABASE_URL`` to ``nonogram_poc`` over whatever the
caller exported, and check nothing: the suite's database-backed tests skip
when they cannot connect, so a run against an unreachable database came back
green.  Now it resolves and checks the URL exactly as the other two admin
scripts do, after parsing its arguments -- so ``--help`` and a mistyped option
still answer with no database at all.

CARD-168: with nothing exported it now defaults to ``nonogram_test``, not the
panel's ``nonogram_poc`` -- the suite's guard (``tests/database_guard.py``)
refused that default at start-up.  The other two scripts keep ``nonogram_poc``.

``pytest`` is a stub on ``PATH`` (``tests/helpers/admin_scripts.py``): no real
suite runs from inside this one, and no database is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.admin_scripts import (
    DatabaseCheckContract,
    ExportedDatabaseUrlContract,
    connections,
    run_script,
)

SCRIPT = "run_admin_tests.sh"
TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/nonogram_test"


class _Runner:
    SCRIPT = SCRIPT
    CONSUMER = "pytest"
    PAST_THE_CHECK = "Running:"
    FINISHED = "Tests completed!"
    DEFAULT_DB = "nonogram_test"


def test_the_harness_reaches_the_end_of_the_script(tmp_path: Path) -> None:
    run = run_script(SCRIPT, tmp_path)

    assert run.returncode == 0, run.output
    assert "reachable (Homebrew)" in run.stdout
    assert "Running: All admin panel tests" in run.stdout
    assert "Tests completed!" in run.stdout
    assert len(run.called("pytest")) == 1, run.calls


class TestSiblingScripts_ExportedDatabaseUrlWins(_Runner, ExportedDatabaseUrlContract):
    """AC-1 for run_admin_tests.sh (setup_admin_local.sh: tests/test_setup_admin_local.py)."""


class TestRunAdminTests_ChecksTheTargetDatabase(_Runner, DatabaseCheckContract):
    """The same check as setup_admin_local.sh, before any test runs."""


class TestRunAdminTests_KeepsItsArguments:
    """G-1: every argument it took before still does what it did."""

    def test_help_answers_without_a_database(self, tmp_path: Path) -> None:
        run = run_script(SCRIPT, tmp_path, "--help", existing_dbs=[])

        assert run.returncode == 0, run.output
        assert "Usage: ./scripts/run_admin_tests.sh" in run.stdout
        for word in ("wave1", "wave2", "e2e", "unit", "smoke", "integration",
                     "--verbose", "--coverage", "DATABASE_URL"):
            assert word in run.stdout, word
        assert TEST_DB_URL in run.stdout  # it names the default it falls back to
        # Every test type -- unit and smoke too -- now checks the database first
        # (CARD-152 review F-003); --help says so.
        assert "Every test type, unit and" in run.stdout, run.stdout
        assert run.called("psql") == [] and run.called("pytest") == [], run.calls

    def test_an_unknown_option_is_refused_without_a_database(
        self, tmp_path: Path
    ) -> None:
        run = run_script(SCRIPT, tmp_path, "--bogus", existing_dbs=[])

        assert run.returncode == 1, run.output
        assert "Unknown option: --bogus" in run.stdout
        assert run.called("psql") == [] and run.called("pytest") == [], run.calls

    def test_each_test_type_and_option_reaches_pytest(self, tmp_path: Path) -> None:
        expected = {
            ("all",): ["tests/test_wave1_*.py", "tests/test_wave2_*.py"],
            ("wave1",): ["tests/test_wave1_*.py", "tests/test_batch_history.py"],
            ("wave2",): ["tests/test_wave2_*.py"],
            ("e2e",): ["-m e2e"],
            ("unit",): ["-m unit"],
            ("smoke",): ["-m smoke"],
            ("integration",): ["-m integration"],
            ("unit", "-v"): ["-m unit", "-vv"],
            ("unit", "--verbose"): ["-m unit", "-vv"],
            ("e2e", "--coverage"): ["-m e2e", "--cov=src/nonogram/admin"],
        }
        for i, (args, pieces) in enumerate(expected.items()):
            run = run_script(SCRIPT, tmp_path / str(i), *args)

            assert run.returncode == 0, (args, run.output)
            [call] = run.called("pytest")
            for piece in pieces:
                assert piece in call, (args, call)

    def test_a_failing_suite_still_fails_the_script(self, tmp_path: Path) -> None:
        run = run_script(SCRIPT, tmp_path, "unit", pytest_fails=True)

        assert run.returncode != 0, run.output
        assert "Tests completed!" not in run.stdout


class TestRunAdminTests_NeedsPsqlForEveryTestType:
    """Review F-003: the check runs for every test type, so psql is required."""

    def test_without_psql_it_stops_before_any_test(self, tmp_path: Path) -> None:
        # Catches: dropping the ``command -v psql`` guard (under ``set -e`` the
        # Docker branches would fail and the script would blame the database),
        # or exempting unit/smoke from the check.
        for i, test_type in enumerate(("unit", "smoke", "all")):
            run = run_script(SCRIPT, tmp_path / str(i), test_type, without_psql=True)

            assert run.returncode == 1, (test_type, run.output)
            assert "psql (PostgreSQL) not found" in run.stdout, (test_type, run.output)
            assert "Running:" not in run.stdout, (test_type, run.output)
            assert "Tests completed!" not in run.stdout, (test_type, run.output)
            assert run.called("pytest") == [], (test_type, run.calls)
            assert run.called("docker") == [] and run.called("docker-compose") == [], (
                test_type,
                run.calls,
            )


class TestRunAdminTests_DefaultsToTheTestDatabase:
    """CARD-168 AC-2: nothing exported -> ``nonogram_test``; an exported URL still wins."""

    #: Set in this process's own environment, so a harness that leaked the
    #: developer's DATABASE_URL into the script would show it.
    DECOY = "postgresql://decoy@localhost:5432/nonogram_decoy_test"

    def test_with_nothing_exported_it_checks_and_uses_nonogram_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", self.DECOY)
        # Only nonogram_test exists, so a script still checking the panel's
        # nonogram_poc would stop here instead of passing.
        run = run_script(SCRIPT, tmp_path, existing_dbs=["nonogram_test"])

        assert run.returncode == 0, run.output
        assert "decoy" not in run.output, run.output  # the harness unset it
        assert f"DATABASE_URL={TEST_DB_URL} (project default)" in run.stdout
        assert "database 'nonogram_test' reachable (Homebrew)" in run.stdout
        assert [c["dbname"] for c in connections(run)] == ["nonogram_test"]
        assert run.handed("pytest") == [TEST_DB_URL], run.calls
        assert "nonogram_poc" not in run.output, run.output

    def test_with_nothing_exported_the_panels_database_is_not_enough(
        self, tmp_path: Path
    ) -> None:
        # The old default's database alone: the run stops at the check.
        run = run_script(SCRIPT, tmp_path, existing_dbs=["nonogram_poc"])

        assert run.returncode != 0, run.output
        assert "Database 'nonogram_test' is not reachable" in run.stdout
        assert run.called("pytest") == [], run.calls

    def test_an_exported_url_still_wins_and_is_named_as_the_source(
        self, tmp_path: Path
    ) -> None:
        url = "postgresql://someone@localhost:5432/nonogram_mine_test"
        run = run_script(
            SCRIPT, tmp_path, database_url=url, existing_dbs=["nonogram_mine_test"]
        )

        assert run.returncode == 0, run.output
        assert f"DATABASE_URL={url} (exported by the caller)" in run.stdout
        assert "project default" not in run.stdout
        assert [c["dbname"] for c in connections(run)] == ["nonogram_mine_test"]
        assert run.handed("pytest") == [url], run.calls
        assert "nonogram_test" not in run.output.replace("nonogram_mine_test", "")
