"""CARD-109 — refuse to run the suite against a database nobody chose.

``nonogram.admin.app.create_app`` reads ``DATABASE_URL`` and connects to
whatever it names. Most test files clear the variable first; four did not, and
did not mean to use a database at all. So a developer with ``DATABASE_URL``
exported — the shell you are in right after running the membership backfill or
an alembic upgrade — ran the suite and those tests read and wrote that
database.

Both halves of that were seen on 2026-09-21: a stray ``books`` row left in the
development database by a test run, and then four e2e tests that failed the
moment that database was emptied mid-session and passed again on a clean run.
The second is the one that matters — the suite's verdict had become a property
of the shell rather than of the code.

Why this refuses rather than quietly unsetting
----------------------------------------------
Silently clearing ``DATABASE_URL`` for tests that did not ask for it would fix
the damage and hide the mistake, which is the same trade the
``except (ImportError, Exception): pass`` in CARD-104 made — and that clause is
how an entire discarded feature stayed invisible for weeks. The whole defect
here is that **nothing said anything**. So the guard stops the run, names the
database it refused, and says how to proceed on purpose.

It never connects. Reading the URL is enough to decide, and a connection is
precisely what CARD-097 spent a card making safe to avoid.

This lives in its own module rather than in ``conftest.py`` so that its own
test can load it into a subprocess with ``-p tests.database_guard`` and watch
it act, which a hook defined in the conftest could not do.
"""

from __future__ import annotations

import os

__all__ = ["OPT_OUT", "TEST_MARKERS", "report_line", "verdict"]

#: Set this to run the suite against a database the guard would otherwise
#: refuse. Named in every refusal, so the way out is never a thing to go and
#: look up.
OPT_OUT = "NONOGRAM_ALLOW_FOREIGN_DATABASE"

#: What makes a database name look like one the suite may use. Deliberately a
#: name test rather than a connection test: a database called ``nonogram_test``
#: is one somebody made for this, and one called ``nonogram`` is not.
TEST_MARKERS = ("test",)


def _database_name(database_url: str) -> str:
    """The last path segment of a URL, without credentials or query string.

    Parsed by hand rather than with ``urllib``, because the only thing needed
    is the name and the one thing that must never happen is echoing the
    password — a refusal gets printed, and printed things get pasted into
    issues and chat.
    """
    tail = database_url.rsplit("/", 1)[-1]
    return tail.split("?", 1)[0].strip()


def verdict(database_url: str | None, *, opted_out: bool) -> tuple[bool, str]:
    """May the suite run against this? And what should the header say?

    Returns ``(allowed, reason)``. The reason is written to be read in a
    failure message, so it names the database and never the credential.
    """
    if not database_url:
        return True, "DATABASE_URL is not set; the suite uses its own storage"

    name = _database_name(database_url)
    if any(marker in name.lower() for marker in TEST_MARKERS):
        return True, f"DATABASE_URL names {name!r}, which reads as a test database"

    if opted_out:
        return True, (
            f"DATABASE_URL names {name!r}, which does not read as a test "
            f"database — allowed because {OPT_OUT} is set"
        )

    return False, (
        f"Refusing to run the suite against {name!r}.\n"
        f"\n"
        f"DATABASE_URL is set, and this test suite builds admin apps that "
        f"connect to whatever it names — including tests that do not mean to "
        f"use a database at all. It would read and write {name!r}.\n"
        f"\n"
        f"If that is not what you want (it usually is not — this happens after "
        f"running a migration or the membership backfill in the same shell):\n"
        f"    unset DATABASE_URL\n"
        f"\n"
        f"If it is what you want:\n"
        f"    {OPT_OUT}=1 pytest ...\n"
        f"\n"
        f"A database whose name contains 'test' is allowed without either."
    )


def current_verdict() -> tuple[bool, str]:
    """:func:`verdict` for the environment this process is actually in."""
    return verdict(
        os.getenv("DATABASE_URL"),
        opted_out=bool(os.getenv(OPT_OUT)),
    )


def report_line() -> str | None:
    """The run-header line, or ``None`` when there is nothing to say.

    Silent in the ordinary case — `DATABASE_URL` unset — because a line on
    every run is a line nobody reads by the third one.
    """
    if not os.getenv("DATABASE_URL"):
        return None
    _allowed, reason = current_verdict()
    return f"database guard: {reason.splitlines()[0]}"


def pytest_configure(config) -> None:
    """Stop the run before collection when the database is not ours."""
    import pytest

    allowed, reason = current_verdict()
    if not allowed:
        raise pytest.UsageError(reason)
