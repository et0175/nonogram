"""A per-test wall-clock bound, so a hang fails loudly instead of forever.

Registered by ``tests/conftest.py`` for the whole suite, and usable on its own
(``-p tests.hang_guard``), which is how its own test drives it in a subprocess.

Why this exists, and why it is not a package. CARD-097's stall — a connection
attempt with no deadline, against a Postgres waiting on a permission dialog —
cost an afternoon of ``ps``, ``sample`` and ``lsof`` to identify, because a
hung run says nothing at all: no output, no failure, no stack. The fix for
*that* hang is a connection deadline (``nonogram.db.session``). This is the
net for the next one, from wherever it comes.

``faulthandler`` rather than ``pytest-timeout`` — the owner's call on CARD-097.
It is stdlib, so ADR-0006/R1's dependency baseline does not move for a
debugging convenience, and it dumps **every** thread's stack rather than only
the one pytest is watching, which matters when the stuck thread is a driver's
and not the test's.

What it does *not* do: distinguish a hang from an honestly slow test. There is
no such distinction available at this level — which is why the bound is set
far above the slowest honest test rather than close to it.
"""

from __future__ import annotations

import faulthandler
import os
import tempfile
from pathlib import Path

import pytest

#: How long one test may run before the suite treats it as hung, dumps every
#: thread's stack to stderr and aborts.
#:
#: Two minutes. The slowest honest test in this suite is a seeded corpus
#: property test in the tens of seconds, and the whole suite runs in about
#: ninety; so this cannot fire on work, only on a stop. Override with
#: ``NONOGRAM_TEST_HANG_SECONDS`` — the guard's own test sets it to a couple of
#: seconds to prove the mechanism without waiting two minutes for it.
HANG_SECONDS = float(os.getenv("NONOGRAM_TEST_HANG_SECONDS", "120"))

#: Where the stacks are written when a test overruns.
#:
#: A **file**, not stderr, and that is the whole lesson of getting this wrong
#: twice. pytest captures output at the file-descriptor level, so a dump
#: written to fd 2 during a test lands in a capture buffer that is discarded
#: when the process is killed a moment later — the first version printed
#: nothing at all. Duplicating fd 2 at import time fixes that *only* if this
#: module is imported before capture is installed, which is true when it is
#: loaded with ``-p tests.hang_guard`` and false when ``tests/conftest.py``
#: imports it. Depending on that ordering is how the second version printed
#: nothing.
#:
#: A file has no such ordering problem. The path is announced at session start
#: so it is not a secret, and it is truncated per session so a stale dump from
#: last week cannot be mistaken for today's.
DUMP_PATH = Path(
    os.getenv("NONOGRAM_TEST_HANG_DUMP")
    or Path(tempfile.gettempdir()) / "nonogram-test-hang.txt"
)

_DUMP_TARGET = None


def pytest_configure(config):
    """Open (and truncate) the dump file, and say where it is."""
    global _DUMP_TARGET
    if HANG_SECONDS <= 0:
        return
    _DUMP_TARGET = DUMP_PATH.open("w", buffering=1)


def pytest_report_header(config):
    """Say the bound and the dump path in the run header.

    Through the header hook rather than by writing a line directly, because a
    run's default options here include ``-q`` and a hand-written line is
    swallowed by it. This is best-effort in any case: the path is fixed and
    documented, so a killed run's stacks are findable even when nothing was
    printed.
    """
    if _DUMP_TARGET is None:
        return None
    return f"hang guard: {HANG_SECONDS:.0f}s per test; stacks -> {DUMP_PATH}"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    """Arm the dump before each test, cancel it after.

    Per test rather than per session: a session-wide alarm would name the
    whole run rather than the test that stopped, and the name is most of the
    value. ``exit=True`` means the process is killed after the stacks are
    written — brutal, and correct: at that point the run has already failed,
    and the alternative is the eleven silent minutes this replaces.
    """
    if _DUMP_TARGET is not None:
        faulthandler.dump_traceback_later(
            HANG_SECONDS, file=_DUMP_TARGET, exit=True
        )
    try:
        yield
    finally:
        if _DUMP_TARGET is not None:
            faulthandler.cancel_dump_traceback_later()
