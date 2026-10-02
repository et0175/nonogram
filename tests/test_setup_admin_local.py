"""CARD-152: ``scripts/setup_admin_local.sh`` checks and migrates the database it will use.

It used to check one database (a bare ``psql -c "SELECT 1"`` reaches the
server's default), hardcode ``DATABASE_URL`` to another over whatever the
caller exported, and report "Setup complete!" after a failed migration whose
output it had thrown away.  The harness -- stubs on ``PATH``, a throwaway
project root, CARD-151's psql model -- lives in ``tests/helpers/admin_scripts.py``;
no database is touched and none needs to be running.
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers.admin_scripts import (
    README,
    DatabaseCheckContract,
    ExportedDatabaseUrlContract,
    connections,
    run_script,
)

SCRIPT = "setup_admin_local.sh"


class _Setup:
    SCRIPT = SCRIPT
    CONSUMER = "alembic"
    PAST_THE_CHECK = "Activating virtual environment"
    FINISHED = "Setup complete!"


def test_the_harness_reaches_the_end_of_the_script(tmp_path: Path) -> None:
    """Guard on the guard: with everything healthy the run completes."""
    run = run_script(SCRIPT, tmp_path)

    assert run.returncode == 0, run.output
    for line in (
        "reachable (Homebrew)",
        "Virtual environment activated",
        "Environment set",
        "Migrations completed",
        "Setup complete!",
    ):
        assert line in run.stdout, f"{line!r} missing from:\n{run.output}"
    assert run.called("alembic") == ["alembic upgrade head"]


class TestSiblingScripts_ExportedDatabaseUrlWins(_Setup, ExportedDatabaseUrlContract):
    """AC-1 for setup_admin_local.sh (run_admin_tests.sh: tests/test_run_admin_tests.py)."""


class TestSetupAdminLocal_ChecksTheTargetDatabase(_Setup, DatabaseCheckContract):
    """AC-2: the check reaches the database the URL names, on every branch.

    The contract's ``test_an_absent_database_is_refused_while_the_servers_default_answers``
    is the AC itself; the rest pin each URL-parsing branch the check relies on.
    """

    def test_the_old_bare_check_would_have_passed_here(self, tmp_path: Path) -> None:
        """The defect, made concrete: the default database answers, the target does not.

        ``nonogram_poc`` -- the project default -- is absent and the database
        named after the user is present, which is exactly where a bare
        ``psql -c "SELECT 1"`` printed a green tick.
        """
        run = run_script(SCRIPT, tmp_path, existing_dbs=["stub_owner", "postgres"])

        self.assert_stopped_at_the_check(run)
        assert "Database 'nonogram_poc' is not reachable" in run.stdout
        assert "(project default)" in run.stdout
        assert [c["dbname"] for c in connections(run)] == ["nonogram_poc"]


class TestSetupAdminLocal_StopsOnAFailedMigration:
    """AC-3: a failed ``alembic upgrade head`` is an error, with alembic's words."""

    MESSAGE = (
        "FAILED: Can't locate revision identified by 'deadbeef'\n"
        "  (the second line matters too)"
    )

    def test_it_exits_non_zero_and_never_claims_completion(
        self, tmp_path: Path
    ) -> None:
        run = run_script(SCRIPT, tmp_path, alembic_fails=True, alembic_message=self.MESSAGE)

        assert run.returncode != 0, run.output
        assert "Migrations failed" in run.stdout
        assert "Setup complete!" not in run.output
        assert "may have issues" not in run.output

    def test_it_quotes_alembics_own_message(self, tmp_path: Path) -> None:
        run = run_script(SCRIPT, tmp_path, alembic_fails=True, alembic_message=self.MESSAGE)

        # The stub writes to stderr, so the message reaching ``output`` proves
        # nothing; only the script's own indented quote lands on stdout.
        assert "alembic upgrade head said:" in run.stdout
        for line in self.MESSAGE.splitlines():
            assert f"    {line.strip()}" in run.stdout, (
                f"alembic said {line.strip()!r} and the script did not quote it:"
                f"\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
            )
        assert "(no output)" not in run.stdout

    def test_a_silent_failure_still_stops_and_says_so(self, tmp_path: Path) -> None:
        run = run_script(SCRIPT, tmp_path, alembic_fails=True, alembic_message="")

        assert run.returncode != 0, run.output
        assert "    (no output)" in run.stdout
        assert "Setup complete!" not in run.output

    def test_a_successful_migration_still_completes(self, tmp_path: Path) -> None:
        run = run_script(SCRIPT, tmp_path)

        assert run.returncode == 0, run.output
        assert "Migrations completed" in run.stdout
        assert "Setup complete!" in run.stdout


def test_the_readme_no_longer_says_the_siblings_ignore_an_exported_url() -> None:
    readme = README.read_text()
    assert "do not yet honour" not in readme
    prerequisites = readme.split("## Prerequisites", 1)[1].split("\n## ", 1)[0]
    assert "wins" in prerequisites, prerequisites
    for name in ("start_admin_local.sh", SCRIPT, "run_admin_tests.sh"):
        assert name in prerequisites, f"{name} missing from Prerequisites"
