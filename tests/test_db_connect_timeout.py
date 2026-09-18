"""CARD-097 — a database that answers nothing must not stop the suite.

    AC-0  TestDb_ConnectionAttemptGivesUp
          -> test_a_database_that_never_answers_fails_instead_of_hanging*

The bug this pins, in one line: a connection attempt with no deadline is
indistinguishable from a database that is merely slow, and libpq's default
deadline is *none at all*.

The observed case was Postgres.app 18, which shows a macOS permission dialog
when an application first connects. Until somebody clicks it the TCP socket is
`ESTABLISHED` — so the client believes it is connected — but authentication
never completes and `connect()` never returns. A full suite run sat in that
state for eleven minutes at 0% CPU before it was killed by hand (CARD-097),
and the `db_required` skip hook, whose whole job is to skip these tests when
the database is unreachable, could not fire: its own ``SELECT 1`` was the call
that hung.

The fixture below reproduces that shape without needing Postgres at all: a
socket that listens and never accepts. The kernel completes the TCP handshake
from the backlog queue, so connecting *succeeds*, and then nothing ever
arrives. That is the same trap, and it is what any deadline has to escape.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from pathlib import Path

import pytest

from nonogram.db import session as db_session

#: Generous enough not to be flaky on a loaded machine, short enough that a
#: regression is a slow test rather than a hung suite.
_ALLOWED_SECONDS = 15

REPO_ROOT = Path(__file__).resolve().parent.parent


@contextmanager
def _black_hole_port():
    """A port that completes the TCP handshake and then says nothing.

    ``listen`` with no ``accept``: the kernel answers the SYN from the backlog
    queue, so the client's ``connect`` returns successfully and its first read
    waits forever. This is what a Postgres blocked on a permission dialog
    looks like from the client side.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        yield listener.getsockname()[1]


def test_a_database_that_never_answers_fails_instead_of_hanging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-0: the attempt ends in an error, inside the configured deadline.

    The assertion that matters is the clock, not the exception type: any
    failure is fine, and a hang is not. ``_ALLOWED_SECONDS`` is well above the
    shipped timeout so a slow machine cannot turn this red, and well below the
    "eleven minutes and counting" this card exists to stop.
    """
    with _black_hole_port() as port:
        url = f"postgresql://postgres:postgres@127.0.0.1:{port}/nonogram_test"
        monkeypatch.setenv("DATABASE_URL", url)
        monkeypatch.setattr(db_session, "CONNECT_TIMEOUT_SECONDS", 2)
        monkeypatch.setattr(db_session, "engine", None)
        monkeypatch.setattr(db_session, "_engine_url", None)

        started = time.monotonic()
        with pytest.raises(Exception):
            # `engine.connect()`, because that is the call that hung: it is
            # what `tests/conftest.py`'s `db_required` hook makes to decide
            # whether to skip. A `Session` would not do — SQLAlchemy connects
            # lazily, so building one succeeds against a black hole and the
            # test would pass while proving nothing.
            db_session._init_engine()
            with db_session.engine.connect():
                pass
        elapsed = time.monotonic() - started

    assert elapsed < _ALLOWED_SECONDS, f"took {elapsed:.1f}s — that is a hang"


def test_a_sqlite_url_is_not_given_a_postgres_connect_option(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deadline is a libpq option, so it must not reach SQLite.

    ``connect_timeout`` is a PostgreSQL connection parameter; SQLite's driver
    has no such keyword and raises ``TypeError`` if handed one. The admin's
    own tests, the re-grade fixtures and every legacy in-memory path run on
    SQLite URLs, so passing the option unconditionally would trade a rare hang
    for a certain crash.
    """
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'x.db'}")
    monkeypatch.setattr(db_session, "engine", None)
    monkeypatch.setattr(db_session, "_engine_url", None)

    db_session._init_engine()
    with db_session.engine.connect() as opened:
        assert opened is not None


# --------------------------------------------------------------------------
# AC-1 — a hang anywhere becomes a failure with a stack
# --------------------------------------------------------------------------


def test_a_hanging_test_is_killed_and_its_stack_printed(tmp_path) -> None:
    """AC-1: the net, exercised on a deliberate hang.

    Run in a subprocess, because the guard's remedy is to kill the process —
    there is no way to observe that from inside the process it kills. The
    subprocess loads the guard explicitly (``-p tests.hang_guard``) with a
    two-second bound instead of the shipped two minutes, so the mechanism is
    proved without the wait.

    Three things are asserted, and the third is the one with the value: the
    run ends, it ends unsuccessfully, and the output names **the function that
    hung** — which is precisely what eleven minutes of silence did not.
    """
    hanging = tmp_path / "test_hangs_on_purpose.py"
    hanging.write_text(
        "import time\n\n\ndef test_hangs_on_purpose():\n    time.sleep(120)\n"
    )

    dump_file = tmp_path / "hang.txt"
    environment = dict(
        os.environ,
        NONOGRAM_TEST_HANG_SECONDS="2",
        NONOGRAM_TEST_HANG_DUMP=str(dump_file),
    )
    environment["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + str(REPO_ROOT)
    finished = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(hanging),
            "-p", "tests.hang_guard", "-o", "addopts=", "-q",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=environment,
    )

    output = finished.stdout + finished.stderr
    dumped = dump_file.read_text() if dump_file.exists() else ""
    assert finished.returncode != 0, output
    assert "Timeout" in dumped, dumped or output
    assert "test_hangs_on_purpose" in dumped, dumped or output

    # Where the stacks went is asserted on a run that exits normally, below:
    # this one is killed, and a killed process never flushes the stdout it
    # buffered — the same trap that made the dump itself invisible twice.


def test_the_reachability_verdict_is_taken_once_per_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-2: one deadline per run, not one per test that wants a database.

    The deadline fixed the hang and created a smaller problem in its place:
    with a database that listens and never answers, every fixture that wanted
    one paid ten seconds to find out. Measured before this cache, with the
    corpus of `test_wave3_*` tests: **eight minutes and twenty-four seconds**
    for a run that reports the same 26 skips in about ninety seconds, because
    ~25 tests each paid two attempts in setup. After it: two minutes.

    So the verdict is memoised per URL. Asserted by counting probes rather
    than by timing, because a timing assertion here would be a flake on a
    loaded machine and would not say *why* it was slow.
    """
    import tests.conftest as conftest

    probes = 0

    with _black_hole_port() as port:
        url = f"postgresql://postgres:postgres@127.0.0.1:{port}/probe_once"
        monkeypatch.setattr(conftest, "_DATABASE_VERDICTS", {})
        monkeypatch.setattr(db_session, "CONNECT_TIMEOUT_SECONDS", 1)

        # Patched on `sqlalchemy` itself, because the helper imports
        # `create_engine` inside the function rather than at module scope.
        import sqlalchemy

        real_create_engine = sqlalchemy.create_engine

        def counting(*args, **kwargs):
            nonlocal probes
            probes += 1
            return real_create_engine(*args, **kwargs)

        monkeypatch.setattr(sqlalchemy, "create_engine", counting)

        first = conftest._unreachable_reason(url)
        second = conftest._unreachable_reason(url)

    assert first and second, "a black hole is not reachable"
    assert first == second
    assert probes == 1, f"probed {probes} times; the verdict is not cached"


def test_a_run_says_where_a_hang_dump_would_go(tmp_path) -> None:
    """The guard announces its file and its bound in the run header.

    Otherwise the dump is a secret: the run that needs it is the run that gets
    killed, and a killed run cannot tell anybody anything. Checked on a
    passing run — which flushes its output — and without ``-q``, since that is
    what suppresses the header.
    """
    passing = tmp_path / "test_passes.py"
    passing.write_text("def test_passes():\n    assert True\n")
    dump_file = tmp_path / "hang.txt"
    environment = dict(
        os.environ,
        NONOGRAM_TEST_HANG_SECONDS="30",
        NONOGRAM_TEST_HANG_DUMP=str(dump_file),
        PYTHONPATH=str(REPO_ROOT / "src") + os.pathsep + str(REPO_ROOT),
    )

    finished = subprocess.run(
        [
            sys.executable, "-m", "pytest", str(passing),
            "-p", "tests.hang_guard", "-o", "addopts=",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=environment,
    )

    output = finished.stdout + finished.stderr
    assert finished.returncode == 0, output
    assert str(dump_file) in output, output
    assert "30s per test" in output, output
