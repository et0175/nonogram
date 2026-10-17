"""CARD-244 — the test database a repo root owns, derived from that root.

Why derive it at all
--------------------
``tests/conftest.py``'s session fixture rebuilds the database it is handed
destructively: ``DROP SCHEMA public CASCADE``, ``CREATE SCHEMA public``,
``alembic upgrade head``, plus a ``TRUNCATE`` of every table before each test.
Until this card every pytest process on this machine was handed the same
database, ``nonogram_test``. Two worktrees running at once therefore did not
merely contend for it — each erased the other's schema mid-run, and the
suite's verdict became a property of what a sibling card happened to be doing.

Measured on this board in wave 44: a 7-file DB selection beside a full suite
produced two failures in ``test_book_trim_persistence`` that are 200 passed in
isolation, and CARD-222's build gate reported 57 skipped against this suite's
normal 9 — a 48-test "regression" that did not exist. ``conftest.py``'s own
comment already named the hazard ("several pipelines share nonogram_test");
its answer was a ten-second ``lock_timeout``, which turns a hang into an
error. A better failure, not a fix.

So the default database name is a **function of the resolved repo root**. A
worktree can only ever name its own.

Why the name ends in ``_test`` rather than starting with ``nonogram_test_``
---------------------------------------------------------------------------
CARD-244's card sketched ``nonogram_test_<slug>``. It is spelled the other way
round — ``nonogram_<slug>_test`` — for one reason, and it is G-1's reason.

``conftest._refuse_unless_test_database`` refuses any URL whose database name
does not end in ``_test``. That refusal is the whole of what stands between
this fixture's ``DROP SCHEMA`` and the live admin panel's ``nonogram_poc``,
and ``tests/test_card_156_db_fixture.py`` pins the names it must refuse —
including ``nonogram_test_backup``, which is refused *because* "starts with
nonogram_test" is not good enough. Deriving ``nonogram_test_<slug>`` would
have meant widening that guard to admit a prefix, retiring that case, and
betting the owner's real data on the new rule. Deriving ``nonogram_<slug>_test``
needs no change to the guard at all: every name this module produces is
accepted by exactly the rule that was already there, and every name it
refused it still refuses.

The shape, and the 63-byte budget
---------------------------------
::

    nonogram_  <slug, ≤36 chars>  _  <digest, 12 hex chars>  _test
    └── 9 ──┘                    └1┘ └────── 12 ───────┘ └── 5 ──┘

``NAMEDATALEN`` is 64, so an identifier is 63 bytes. Postgres does not
*refuse* a longer database name — it truncates it and carries on with a
notice. That is why the digest sits inside the budget instead of being
appended to the readable part: a scheme that could overflow would have two
different deep worktrees quietly truncate onto one database, which is this
card's bug wearing a different hat.

The slug is the root's basename, so ``psql -l`` stays readable, and it is
*only* the readable part: the digest is taken over the whole resolved path, so
two roots whose basenames truncate alike, and two same-named checkouts under
different parents, still get different names. 12 hex characters is 48 bits —
not a proof of uniqueness but far past the handful of worktrees this machine
holds, and the distinctness is measured over a seeded corpus in
``tests/test_db_isolation.py`` rather than asserted here.

This module imports nothing from the project (only ``hashlib``/``pathlib``/
``re``), so ``conftest.py``, the tests and any script can ask it for the name
without dragging in ``nonogram.admin``.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

__all__ = [
    "DIGEST_CHARACTERS",
    "MAX_IDENTIFIER_BYTES",
    "PREFIX",
    "REPO_ROOT",
    "SLUG_CHARACTERS",
    "SUFFIX",
    "default_test_database_url",
    "derive_test_database_name",
    "resolve_test_database_url",
]

#: The repo root this file belongs to: ``tests/`` sits directly under it.
#: Resolved, so a path reached through a symlink names the same database as
#: the path reached directly.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: PostgreSQL's identifier length. ``NAMEDATALEN`` is 64 and the terminator
#: takes one byte. A longer name is truncated, not refused — see the module
#: docstring for why that matters here.
MAX_IDENTIFIER_BYTES = 63

#: Every derived name starts with this, so the suite's databases sort together
#: in ``psql -l`` and are recognisable as the suite's.
PREFIX = "nonogram_"

#: …and ends with this, which is the one thing
#: :func:`tests.conftest._refuse_unless_test_database` requires. Not
#: negotiable: it is what keeps ``nonogram_poc`` and ``nonogram_dev`` out of
#: reach without touching that guard (G-1).
SUFFIX = "_test"

#: Hex characters of SHA-256 over the resolved root — 48 bits.
DIGEST_CHARACTERS = 12

#: Characters of the readable slug. The remainder of the 63-byte budget once
#: the prefix, the digest, its separator and the suffix are taken.
SLUG_CHARACTERS = (
    MAX_IDENTIFIER_BYTES - len(PREFIX) - 1 - DIGEST_CHARACTERS - len(SUFFIX)
)

#: Everything that is not a lowercase ASCII letter or digit. Replaced by ``_``
#: rather than dropped, so ``my.tree`` and ``mytree`` stay distinguishable in
#: the readable part (and distinct in the digest regardless).
_NOT_IDENTIFIER_SAFE = re.compile(r"[^a-z0-9]+")

#: Where the suite's own database lives when nobody says otherwise. Only the
#: database name is derived; the rest is the project's long-standing local
#: default, so a derived URL is not a second place where connection details
#: get decided.
_LOCAL_SERVER = "postgresql://postgres:postgres@localhost:5432"


def _slug(root: Path) -> str:
    """The readable part of the name: ``root``'s basename, identifier-safe.

    Lowercased, every run of unsafe characters collapsed to one ``_``, then
    trimmed to :data:`SLUG_CHARACTERS` and stripped of the separators that
    trimming can leave dangling. May legitimately come back empty — ``/`` has
    no basename, and a basename of pure punctuation leaves nothing — in which
    case the caller builds the name from the digest alone.
    """
    collapsed = _NOT_IDENTIFIER_SAFE.sub("_", root.name.lower())
    return collapsed[:SLUG_CHARACTERS].strip("_")


def derive_test_database_name(repo_root: str | Path) -> str:
    """The database name ``repo_root`` owns.

    Deterministic, and a pure function of the *resolved* path: two spellings
    of one directory name one database (two pytest processes in the same
    worktree must agree, or the second would rebuild the first's schema), and
    two different directories name two.

    Always within :data:`MAX_IDENTIFIER_BYTES` and always a legal unquoted
    PostgreSQL identifier — the slug is restricted to ``[a-z0-9_]``, the
    digest to hex, and the name begins with a letter by construction.
    ``tests/test_db_isolation.py`` checks both against an independent reading
    of what Postgres accepts, over a seeded corpus.
    """
    resolved = Path(repo_root).resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:DIGEST_CHARACTERS]
    slug = _slug(resolved)
    middle = f"{slug}_{digest}" if slug else digest
    return f"{PREFIX}{middle}{SUFFIX}"


def default_test_database_url(repo_root: str | Path) -> str:
    """The URL the suite uses for ``repo_root`` when nothing is exported."""
    return f"{_LOCAL_SERVER}/{derive_test_database_name(repo_root)}"


def resolve_test_database_url(environ, repo_root: str | Path = REPO_ROOT) -> str:
    """Which database the fixtures act on: the exported one, or this tree's.

    An exported ``TEST_DATABASE_URL`` is returned **verbatim** and no name is
    derived (AC-3). CI, ``scripts/run_admin_tests.sh`` and the owner's own
    shell all set it, and a derivation laid over any of them would point the
    destructive fixture at a database nobody chose.

    "Exported" means *present*, not *non-empty*: ``TEST_DATABASE_URL=""`` is
    carried through to
    :func:`tests.conftest._refuse_unless_test_database`, which fails the run
    and says so. Falling back to a working default there would turn a
    configuration mistake into a green run against a different database —
    which is how "DB mode passes" came to mean "DB mode skipped" in the first
    place.
    """
    exported = environ.get("TEST_DATABASE_URL")
    if exported is None:
        return default_test_database_url(repo_root)
    return exported
