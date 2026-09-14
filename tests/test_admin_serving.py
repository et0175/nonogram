"""CARD-086 — the deployed panel's server, and the bound its slowest route needs.

    TestAdminServing_UsesAProductionServerInDeployment   (AC-1)
    TestAdminServing_TheDependencyLivesInTheAdminExtra   (AC-2, G-1, G-3)
    TestAdminServing_TheRequestTimeoutClearsTheSlowestRoute (AC-4)
    TestRegrade_StopsWithinItsOwnBoundAndSaysSo          (AC-4)
    TestAdminServing_DeploysOnPurpose                    (Q-2)

The file's subject is a shell script and a manifest, which no unit test would
normally read. They are read here because the numbers in them are load-bearing
against numbers in the code: `--timeout` has to clear
`REGRADE_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS`, and nothing but a test
holds those together — a comment saying so is exactly what drifts.
"""

from __future__ import annotations

import re
import time
import tomllib
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nonogram.admin.regrade import REGRADE_BUDGET_SECONDS, regrade
from nonogram.orchestrator import GENERATION_BUDGET_SECONDS

ROOT = Path(__file__).resolve().parents[1]
START_SH = ROOT / "start.sh"
RENDER_YAML = ROOT / "render.yaml"


def _start_script() -> str:
    return START_SH.read_text(encoding="utf-8")


def _start_command() -> str:
    """The script with its comments stripped — what actually runs.

    The comments explain what `flask run` used to do and why it went, so a
    check for "no flask run" over the raw text fails on the explanation rather
    than on the command. Asserting over the executable lines is the assertion
    that was meant.
    """
    return "\n".join(
        line for line in _start_script().splitlines() if not line.lstrip().startswith("#")
    )


def _timeout_flag() -> int:
    """The ``--timeout`` gunicorn is started with, read from the script."""
    match = re.search(r"--timeout\s+(\d+)", _start_command())
    assert match, f"no --timeout in {START_SH.name}: gunicorn would use its 30s default"
    return int(match.group(1))


class TestAdminServing_UsesAProductionServerInDeployment:
    """AC-1: the deployment does not run Flask's development server."""

    def test_the_start_script_runs_gunicorn(self) -> None:
        script = _start_command()

        assert "gunicorn" in script
        assert not re.search(r"\bflask\b.*\brun\b", script), (
            "`flask run` is the development server that warned about itself in "
            "Render's boot log on every deploy"
        )

    def test_it_loads_the_app_through_the_factory(self) -> None:
        """AC-3: so CARD-085's boot refusal still fails the deploy.

        A module-level app object would be built at import time by each worker
        with no chance for ``AdminConfigurationError`` to mean anything;
        through the factory the exception propagates out of the worker's app
        load, which is what stops a misconfigured panel coming up open.
        """
        assert "create_app()" in _start_command()

    def test_it_execs_rather_than_forking(self) -> None:
        """``exec`` so gunicorn is PID 1 and receives the platform's SIGTERM.

        Without it the shell is the signal's target and gunicorn never drains:
        graceful shutdown is configured below and would be decoration.
        """
        assert re.search(r"^exec gunicorn", _start_command(), re.M)

    def test_graceful_shutdown_is_configured(self) -> None:
        assert "--graceful-timeout" in _start_command()

    def test_one_worker_unless_this_was_revisited(self) -> None:
        """G-4: multi-worker safety has not been examined.

        The admin keeps in-memory state in its legacy (non-DB) mode, so a
        second worker is a separate question rather than a free win.
        """
        assert re.search(r"--workers\s+\"?\$\{?WEB_CONCURRENCY:-1\}?\"?", _start_command())


class TestAdminServing_TheDependencyLivesInTheAdminExtra:
    """AC-2 / G-1 / G-3: gunicorn is an extra, not part of the baseline."""

    @staticmethod
    def _manifest() -> dict:
        return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_the_core_dependency_baseline_is_untouched(self) -> None:
        """ADR-0006/R1 — restated here so this card's own file says it.

        ``tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed``
        is the rule's check and runs unmodified; this asserts the same thing
        from the card that could most plausibly have broken it.
        """
        packages = {
            re.split(r"[<>=!~\[ ]", line)[0].lower()
            for line in self._manifest()["project"]["dependencies"]
        }

        assert packages == {"pillow", "numpy"}

    def test_gunicorn_is_declared_in_the_admin_extra(self) -> None:
        extras = self._manifest()["project"]["optional-dependencies"]
        admin = {re.split(r"[<>=!~\[ ]", line)[0].lower() for line in extras["admin"]}

        assert "gunicorn" in admin

    def test_the_test_suite_does_not_need_it(self) -> None:
        """G-3: a developer with only the dev extra still runs the tests.

        Asserted by import rather than by reading the manifest: if anything
        under ``src/nonogram/`` grew an ``import gunicorn``, this file would be
        the wrong place to find out, but it would find out.
        """
        dev = self._manifest()["project"]["optional-dependencies"]["dev"]

        assert not any("gunicorn" in line.lower() for line in dev)

    def test_it_is_in_the_deployment_requirements(self) -> None:
        assert "gunicorn" in (ROOT / "requirements.txt").read_text(encoding="utf-8")


class TestAdminServing_TheRequestTimeoutClearsTheSlowestRoute:
    """AC-4: the two numbers that have to agree, held together by a test.

    gunicorn kills a worker whose request exceeds ``--timeout``. The slowest
    route is ``POST /regrade``, which stops *starting* rows at
    ``REGRADE_BUDGET_SECONDS`` and lets a row already started run for up to
    ``GENERATION_BUDGET_SECONDS`` more. If ``--timeout`` does not clear that
    sum, the run is killed before its own bound can stop it and the work is
    lost rather than reported — the bound would be decoration.
    """

    def test_the_worker_timeout_clears_the_regrade_ceiling(self) -> None:
        ceiling = REGRADE_BUDGET_SECONDS + GENERATION_BUDGET_SECONDS

        assert _timeout_flag() > ceiling, (
            f"gunicorn --timeout is {_timeout_flag()}s but POST /regrade can "
            f"take up to {ceiling:.0f}s "
            f"({REGRADE_BUDGET_SECONDS:.0f}s of starting rows + one row's "
            f"{GENERATION_BUDGET_SECONDS:.0f}s); the worker would be killed "
            f"before the route's own bound could stop it"
        )

    def test_the_timeout_is_set_at_all(self) -> None:
        """gunicorn's default is 30s, which the ceiling above exceeds on its own."""
        assert _timeout_flag() != 30, "that is gunicorn's default, not a decision"


class TestRegrade_StopsWithinItsOwnBoundAndSaysSo:
    """AC-4: the run stops on its own clock, and the report admits it.

    The bound is chosen so it never fires on data like today's — a copy of the
    290-row development database re-graded in 5.5 s end to end (CARD-086 AC-5)
    — so these tests drive it with an injected clock rather than real work.
    """

    @staticmethod
    def _clock_that_jumps_after(calls: int):
        """A clock that runs normally, then leaps past the run budget.

        It cannot simply return small numbers. ``regrade`` uses this same seam
        for two different things: the run's own deadline, *and* the base of
        each row's ``deadline=monotonic() + budget_seconds`` — which is handed
        to the solver, which reads the **real** clock. A fake returning ``2.0``
        therefore gives the solver an absolute deadline decades in the past,
        every row times out, and the test measures nothing it meant to.

        So this returns the real clock plus an offset, and only the offset
        jumps. Row deadlines stay in the future; the run deadline is what the
        leap crosses.
        """
        base = time.monotonic()
        state = {"calls": 0}

        def clock() -> float:
            state["calls"] += 1
            return base + (0.0 if state["calls"] <= calls else 999.0)

        return clock

    @staticmethod
    def _db(tmp_path: Path, rows: int):
        from tests.test_admin_regrade import UNIQUE_GRID, _add_row, _new_db

        engine = _new_db(tmp_path / "bound.db")
        for index in range(rows):
            _add_row(engine, UNIQUE_GRID, name=f"row-{index}")
        return engine

    def test_a_run_that_fits_reports_no_shortfall(self, tmp_path: Path) -> None:
        """G-5: over ordinary data the report is exactly what it was."""
        engine = self._db(tmp_path, rows=5)

        with sessionmaker(bind=engine)() as session:
            report = regrade(session, dry_run=True)

        assert report.not_attempted == 0
        assert report.stopped_early is False
        assert report.row_count == 5

    def test_a_run_that_runs_out_of_time_stops_and_counts_what_it_missed(
        self, tmp_path: Path
    ) -> None:
        engine = self._db(tmp_path, rows=5)
        with sessionmaker(bind=engine)() as session:
            report = regrade(
                session,
                dry_run=True,
                run_budget_seconds=10.0,
                monotonic=self._clock_that_jumps_after(4),
            )

        assert report.stopped_early is True
        assert report.not_attempted > 0
        assert report.row_count + report.not_attempted == 5, (
            "every row is either an outcome or counted as not attempted — a "
            "row that fell out of both would be silently unaccounted for"
        )

    def test_the_rows_it_did_reach_are_still_fully_reported(
        self, tmp_path: Path
    ) -> None:
        """A short run is a short run, not a broken one."""
        engine = self._db(tmp_path, rows=5)
        with sessionmaker(bind=engine)() as session:
            report = regrade(
                session,
                dry_run=True,
                run_budget_seconds=10.0,
                monotonic=self._clock_that_jumps_after(4),
            )

        assert report.row_count >= 1
        for outcome in report.regraded:
            assert outcome.grade is not None

    def test_a_row_is_never_skipped_for_running_out_of_time(
        self, tmp_path: Path
    ) -> None:
        """CON-005's vocabulary stays about puzzles, not about clocks.

        The deadline is checked *before* a row, so a row that starts finishes.
        A SkipReason meaning "we ran out of time" would make a skipped row
        ambiguous between "this is not a puzzle" and "we were in a hurry",
        which is the one thing the skip list must never be.
        """
        engine = self._db(tmp_path, rows=5)
        with sessionmaker(bind=engine)() as session:
            report = regrade(
                session,
                dry_run=True,
                run_budget_seconds=10.0,
                monotonic=self._clock_that_jumps_after(4),
            )

        assert report.skipped == (), (
            "these rows are all uniquely solvable; a skip here would mean the "
            "clock had leaked into the skip vocabulary"
        )

    def test_the_bound_is_its_own_number(self) -> None:
        """INV-003 / ADR-0002: one bound per question.

        The run's budget is not derived from the per-row one, and is not equal
        to it by coincidence — "how long may the batch work?" is a different
        question from "how long may one solve take?" (CARD-083 answered the
        same way for generate_batch).
        """
        assert REGRADE_BUDGET_SECONDS != GENERATION_BUDGET_SECONDS
        assert REGRADE_BUDGET_SECONDS > GENERATION_BUDGET_SECONDS, (
            "a run budget below one row's budget would stop every run after "
            "its first row"
        )


class TestAdminServing_DeploysOnPurpose:
    """Q-2: a deploy to production is a decision, not a side effect of merging."""

    def test_autodeploy_is_off(self) -> None:
        """It was on, and that is how CARD-081's host guard reached production
        without anyone choosing to send it — every route 404'd until it was
        diagnosed — and how CARD-085's merge took the service down until its
        variables were set."""
        content = RENDER_YAML.read_text(encoding="utf-8")

        assert re.search(r"^\s*autoDeploy:\s*false\s*$", content, re.M), (
            "render.yaml should carry autoDeploy: false"
        )
        assert not re.search(r"^\s*autoDeploy:\s*true\s*$", content, re.M)


# --------------------------------------------------------------------------
# CARD-086 follow-up — the deployment diagnoses itself
#
# Written after a live deploy 404'd every route and there was no way to tell,
# from outside or from the logs, which of three causes it was. The 404 is
# deliberately indistinguishable from "no such page" for a scanner (CON-016);
# that is exactly why the operator needs the reason somewhere else.
# --------------------------------------------------------------------------


class TestAdminServing_TheConfiguredHostIsWhatTheOperatorPasted:
    """ADMIN_ALLOWED_HOST accepts what the dashboard actually shows.

    Render's dashboard displays ``https://nonogram-admin.onrender.com``, so
    that is what gets pasted. Compared against a bare ``Host`` header it never
    matches, and the result is a panel that 404s every route while every
    variable looks right — the failure this class exists to prevent recurring.
    """

    HOST = "nonogram-admin.onrender.com"

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch):
        for name in (
            "ADMIN_ALLOWED_HOST", "ADMIN_USER", "ADMIN_PASSWORD",
            "SECRET_KEY", "DATABASE_URL",
        ):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("ADMIN_USER", "operator")
        monkeypatch.setenv("ADMIN_PASSWORD", "x" * 20)
        monkeypatch.setenv("SECRET_KEY", "k" * 20)

    @pytest.mark.parametrize(
        "pasted",
        [
            pytest.param("nonogram-admin.onrender.com", id="bare-host"),
            pytest.param("https://nonogram-admin.onrender.com", id="with-scheme"),
            pytest.param("https://nonogram-admin.onrender.com/", id="scheme-and-slash"),
            pytest.param("nonogram-admin.onrender.com/", id="trailing-slash"),
            pytest.param("http://nonogram-admin.onrender.com:443", id="with-port"),
            pytest.param("  nonogram-admin.onrender.com  ", id="whitespace"),
            pytest.param("NONOGRAM-ADMIN.ONRENDER.COM", id="upper-case"),
        ],
    )
    def test_every_shape_an_operator_might_paste_works(
        self, monkeypatch: pytest.MonkeyPatch, pasted
    ) -> None:
        import base64

        from nonogram.admin import app as admin_app

        monkeypatch.setenv("ADMIN_ALLOWED_HOST", pasted)
        application = admin_app.create_app()
        token = base64.b64encode(f"operator:{'x' * 20}".encode()).decode()

        with application.test_client() as client:
            response = client.get(
                "/", headers={"Host": self.HOST, "Authorization": f"Basic {token}"}
            )

        assert response.status_code == 200, pasted

    @pytest.mark.parametrize(
        "unusable",
        [
            pytest.param("https://nonogram-admin.onrender.com/puzzles", id="with-path"),
            pytest.param("https://", id="no-host"),
            pytest.param("https://host/?q=1", id="with-query"),
        ],
    )
    def test_a_value_that_is_not_a_host_fails_at_boot(
        self, monkeypatch: pytest.MonkeyPatch, unusable
    ) -> None:
        """Loudly, where an operator is looking, not silently per request."""
        from nonogram.admin import app as admin_app

        monkeypatch.setenv("ADMIN_ALLOWED_HOST", unusable)

        with pytest.raises(admin_app.AdminConfigurationError) as caught:
            admin_app.create_app()

        assert "ADMIN_ALLOWED_HOST" in str(caught.value)


class TestAdminServing_SaysWhyItRefused:
    """The 404 tells a scanner nothing; the log tells the operator everything."""

    HOST = "nonogram-admin.onrender.com"

    @staticmethod
    def _captured(application):
        import logging

        records: list[str] = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        application.logger.addHandler(Capture())
        application.logger.setLevel(logging.INFO)
        return records

    def test_a_host_mismatch_is_logged_with_both_values(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from nonogram.admin import app as admin_app

        monkeypatch.setenv("ADMIN_ALLOWED_HOST", self.HOST)
        monkeypatch.setenv("ADMIN_USER", "operator")
        monkeypatch.setenv("ADMIN_PASSWORD", "x" * 20)
        monkeypatch.setenv("SECRET_KEY", "k" * 20)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        application = admin_app.create_app()
        records = self._captured(application)
        with application.test_client() as client:
            client.get("/", headers={"Host": "wrong.example.com"})

        assert any("wrong.example.com" in line for line in records), records
        assert any(self.HOST in line for line in records), records

    def test_the_response_itself_still_gives_nothing_away(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CON-016: the log is for the operator, never the body for the caller."""
        from nonogram.admin import app as admin_app

        monkeypatch.setenv("ADMIN_ALLOWED_HOST", self.HOST)
        monkeypatch.setenv("ADMIN_USER", "operator")
        monkeypatch.setenv("ADMIN_PASSWORD", "x" * 20)
        monkeypatch.setenv("SECRET_KEY", "k" * 20)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        application = admin_app.create_app()
        with application.test_client() as client:
            response = client.get("/", headers={"Host": "wrong.example.com"})

        body = response.get_data(as_text=True)
        assert response.status_code == 404
        assert self.HOST not in body
        assert "ADMIN_ALLOWED_HOST" not in body

    @pytest.mark.parametrize(
        "value, expected",
        [
            pytest.param("nonogram-admin.onrender.com", "reachable", id="deployed"),
            pytest.param(None, "loopback-only", id="local"),
            pytest.param("   ", "loopback-only", id="whitespace-reads-as-unset"),
        ],
    )
    def test_the_boot_log_says_which_door_is_open(
        self, monkeypatch: pytest.MonkeyPatch, value, expected
    ) -> None:
        """The whitespace case is why this exists as well as the mismatch log.

        ``ADMIN_ALLOWED_HOST="   "`` is indistinguishable from unset, so it
        lands in loopback-only mode and 404s every request through a proxy —
        with no mismatch to log, because the host check never runs. Stating the
        mode at boot is the only thing that catches it.
        """
        import logging

        from nonogram.admin import app as admin_app

        for name in ("ADMIN_ALLOWED_HOST", "DATABASE_URL"):
            monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv("ADMIN_ALLOWED_HOST", value)
        monkeypatch.setenv("ADMIN_USER", "operator")
        monkeypatch.setenv("ADMIN_PASSWORD", "x" * 20)
        monkeypatch.setenv("SECRET_KEY", "k" * 20)

        records: list[str] = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        handler = Capture()
        logging.getLogger("nonogram.admin.app").addHandler(handler)
        try:
            application = admin_app.create_app()
            application.logger.addHandler(handler)
            application.logger.setLevel(logging.INFO)
            # create_app logs during construction; rebuild with the handler on
            # the logger it will use.
            records.clear()
            application = admin_app.create_app()
        finally:
            logging.getLogger("nonogram.admin.app").removeHandler(handler)

        assert any(expected in line for line in records), (expected, records)
