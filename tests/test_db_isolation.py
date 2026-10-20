"""CARD-244 — each repo root gets its own test database, so two cards cannot wipe each other.

Every pytest process on this machine used to point at one database,
``nonogram_test``, and ``tests/conftest.py``'s session fixture rebuilds the
database it is given destructively — ``DROP SCHEMA public CASCADE``,
``CREATE SCHEMA public``, ``alembic upgrade head``. Two worktrees running at
the same time therefore did not merely contend for it: each erased the
other's schema mid-run. Wave 44 paid for that twice — two failures in
``test_book_trim_persistence`` that are 200 passed in isolation, and a
48-test "regression" in CARD-222's build gate that never existed.

What is verified here, and where the proof lives
------------------------------------------------
* **AC-1/AC-5** are pure: the name is a function of the resolved repo root
  (:mod:`tests.db_name`), and this file checks the two properties that make it
  safe to use — distinct per root, and a legal Postgres identifier — against a
  seeded corpus rather than a handful of examples. The legality check is an
  *independent* implementation (a regex for what Postgres accepts unquoted),
  not a second call to the function being tested.
* **AC-3** is the property every other pipeline on this board depends on: an
  explicit ``TEST_DATABASE_URL`` is handed on byte-for-byte. It is asserted
  with the derivation monkeypatched to raise, so "no name is derived" is
  observed rather than argued.
* **AC-4** is G-1. The fixture's refusal is what stands between
  ``DROP SCHEMA`` and the live panel's ``nonogram_poc``; deriving a name adds
  a *second* dangerous path — ``CREATE DATABASE`` — so both are asserted
  against the same list of names, with spies proving neither connects.
* **AC-2/AC-6** are executed, in real pytest subprocesses, because that is the
  runner that gates. AC-6 carries its counterfactual: the same pair of
  processes is run again against a single shared database, and the test fails
  if that pair comes back green (ADR-0039/R1 — a claim whose control cannot
  fail is narrative, not coverage).
"""

from __future__ import annotations

import os
import random
import re
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from tests import db_name
from tests.conftest import (
    _MAINTENANCE_DATABASE,
    _ensure_test_database,
    _refuse_unless_test_database,
)
from tests.db_name import (
    DIGEST_CHARACTERS,
    MAX_IDENTIFIER_BYTES,
    SLUG_CHARACTERS,
    SUFFIX,
    default_test_database_url,
    derive_test_database_name,
    resolve_test_database_url,
)

REPO = Path(__file__).resolve().parent.parent

#: What PostgreSQL accepts as an identifier without quoting it: a letter or
#: underscore, then letters, digits, underscores or dollars. Written out here
#: as the independent side of AC-1 — the derivation builds the name by
#: construction, and this says what "legal" means without consulting it.
_UNQUOTED_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_$]*\Z")

#: A password that must never appear in a refusal (as CARD-156 pinned it).
_SECRET = "s3cr3t-pw"


def _is_legal_database_name(name: str) -> bool:
    """Would Postgres take ``name`` as an unquoted identifier, unfolded?

    Two conditions, both independent of :mod:`tests.db_name`: the spelling
    (:data:`_UNQUOTED_IDENTIFIER`) and the 63-**byte** limit. Bytes, not
    characters: ``NAMEDATALEN`` counts bytes, so a name of 63 non-ASCII
    characters is over the limit while ``len()`` says it is not.
    """
    return bool(_UNQUOTED_IDENTIFIER.match(name)) and len(name.encode("utf-8")) <= 63


def _synthetic_roots(seed: int, count: int) -> list[str]:
    """``count`` distinct absolute paths, built with stdlib ``random`` only.

    ``hypothesis`` is not in the dependency baseline, so the corpus is seeded
    by hand — and the caller asserts a minimum size, so it cannot silently
    shrink to the two cases that happen to pass.

    The segments deliberately include the shapes a real worktree name has
    (``PythonProject4-card-244``), plus the ones that would break an
    identifier if they reached it unfiltered: dots, spaces, quotes,
    semicolons, non-ASCII, leading digits, and runs of punctuation.
    """
    rng = random.Random(seed)
    alphabet = "abcXYZ019-_. '\";&$()пример漢"
    roots: dict[str, None] = {}
    while len(roots) < count:
        depth = rng.randint(1, 5)
        segments = []
        for _ in range(depth):
            length = rng.randint(1, 18)
            segments.append("".join(rng.choice(alphabet) for _ in range(length)))
        candidate = "/" + "/".join(segments)
        # ``..`` and ``.`` would make two different strings resolve to one
        # path, which is not a collision in the derivation but would look
        # like one. Drop them rather than special-case them.
        if any(segment in ("", ".", "..") for segment in segments):
            continue
        resolved = str(Path(candidate).resolve())
        roots.setdefault(resolved, None)
    return list(roots)


class TestTestDbUrl_NameIsDerivedPerWorktree:
    """AC-1: distinct repo roots get distinct, legal database names.

    The two halves are checked separately on purpose. "Distinct" without
    "legal" buys a name Postgres truncates to 63 bytes behind the suite's
    back — which would silently re-merge two long roots onto one database,
    the exact failure this card exists to remove. "Legal" without "distinct"
    is the bug we started from.
    """

    def test_two_real_sibling_worktrees_derive_different_names(self):
        # The two roots this board actually runs from: the repo and a card's
        # worktree beside it. Spelled out rather than discovered, so the case
        # survives both trees being removed.
        main = derive_test_database_name("/Users/omelnikova/PycharmProjects/PythonProject4")
        card = derive_test_database_name(
            "/Users/omelnikova/PycharmProjects/PythonProject4-card-244"
        )

        assert main != card
        assert _is_legal_database_name(main), main
        assert _is_legal_database_name(card), card
        # The slug keeps the name readable in ``psql -l``: the point of
        # deriving from the root rather than hashing it outright.
        assert "pythonproject4" in main
        assert "pythonproject4_card_244" in card

    def test_the_same_root_always_derives_the_same_name(self):
        # Two processes in one worktree must agree, or the session fixture of
        # the second would rebuild a database the first is using.
        root = "/Users/omelnikova/PycharmProjects/PythonProject4-card-244"
        assert derive_test_database_name(root) == derive_test_database_name(Path(root))
        # Spellings that resolve to one path are one database.
        assert derive_test_database_name(root) == derive_test_database_name(root + "/.")
        assert derive_test_database_name(root) == derive_test_database_name(root + "/tests/..")

    def test_a_seeded_corpus_of_roots_is_distinct_and_legal(self):
        roots = _synthetic_roots(seed=244, count=400)
        assert len(roots) >= 400, "the corpus shrank; it is the measurement"

        names = [derive_test_database_name(root) for root in roots]

        illegal = [name for name in names if not _is_legal_database_name(name)]
        assert illegal == [], illegal
        assert all(name.endswith(SUFFIX) for name in names), [
            n for n in names if not n.endswith(SUFFIX)
        ]
        collisions = len(names) - len(set(names))
        assert collisions == 0, f"{collisions} of {len(names)} roots collided"

    def test_every_derived_name_passes_the_fixtures_own_refusal(self):
        """The derivation and G-1's guard are checked against each other.

        ``_refuse_unless_test_database`` is the independent implementation
        here: it reads a URL's text and decides, knowing nothing about how the
        name was built. A derivation that produced a name the guard refuses
        would turn every bare ``pytest`` run into a hard failure, and one that
        produced a name the guard *should* refuse is the G-1 defect.
        """
        roots = _synthetic_roots(seed=2244, count=200)
        assert len(roots) >= 200, "the corpus shrank; it is the measurement"
        for root in roots:
            _refuse_unless_test_database(default_test_database_url(root))

    def test_the_url_differs_only_in_the_database_name(self):
        # Host, port and credentials are the project's local default; only the
        # path moves. Anything else would make the derived URL a second place
        # where connection details are decided.
        main = default_test_database_url("/tmp/alpha")
        card = default_test_database_url("/tmp/beta")
        assert main.rsplit("/", 1)[0] == card.rsplit("/", 1)[0]
        assert main.startswith("postgresql://postgres:postgres@localhost:5432/")


class TestTestDbUrl_ExplicitOverrideIsUsedVerbatim:
    """AC-3: an exported ``TEST_DATABASE_URL`` is handed on untouched.

    CI, ``scripts/run_admin_tests.sh`` and the owner's own shell all set it,
    and a derivation applied on top of any of them would point the suite at a
    database nobody chose. The derivation is monkeypatched to raise for these
    cases, so "no name is derived" is a thing the test observes rather than
    infers from the returned string.
    """

    @pytest.fixture
    def derivation_refuses(self, monkeypatch):
        def explode(*_args, **_kwargs):
            raise AssertionError("the derivation ran despite an explicit override")

        monkeypatch.setattr(db_name, "derive_test_database_name", explode)
        monkeypatch.setattr(db_name, "default_test_database_url", explode)

    @pytest.mark.parametrize("exported", [
        "postgresql://postgres:postgres@localhost:5432/nonogram_test",
        # The shapes other pipelines use: a driver named, a query string, a
        # non-local host, and a name that looks derived but is not.
        "postgresql+psycopg2://ci:pw@db.internal:6543/ci_run_41_test?sslmode=require",
        "postgresql://postgres@localhost/nonogram_mine_test",
        "nonogram_pythonproject4_000000000000_test",
        # Not a URL at all, and an empty value: both must survive to the
        # fixture's refusal rather than be quietly replaced by a default. A
        # misconfiguration somebody has to see (CARD-156's rule), not a
        # silent fall-back.
        "not-a-url",
        "",
    ])
    def test_the_exported_value_is_returned_byte_for_byte(
        self, exported, derivation_refuses
    ):
        resolved = resolve_test_database_url(
            {"TEST_DATABASE_URL": exported}, repo_root="/Users/x/SomeTree"
        )
        assert resolved == exported

    def test_only_an_unset_variable_derives(self):
        derived = resolve_test_database_url({}, repo_root="/Users/x/SomeTree")
        assert derived == default_test_database_url("/Users/x/SomeTree")
        # An environment carrying other variables must not change the answer.
        assert resolve_test_database_url(
            {"DATABASE_URL": "postgresql://h/nonogram_poc", "HOME": "/Users/x"},
            repo_root="/Users/x/SomeTree",
        ) == derived

    def test_the_conftest_fixture_reads_the_variable_through_this_function(self):
        """The fixture and the function under test are the same code path.

        Without this, AC-3 could pass against a helper the fixture does not
        call. The fixture is invoked with a monkeypatched environment and its
        answer compared to the function's.
        """
        import tests.conftest as suite_conftest

        # The fixture's own body, unwrapped from pytest's definition object,
        # so this calls the code the suite calls rather than a copy of it.
        fixture = suite_conftest.test_db_url._get_wrapped_function()

        exported = "postgresql://postgres@localhost:5432/nonogram_ac3_probe_test"
        previous = os.environ.get("TEST_DATABASE_URL")
        os.environ["TEST_DATABASE_URL"] = exported
        try:
            assert fixture() == exported
            os.environ.pop("TEST_DATABASE_URL")
            assert fixture() == default_test_database_url(REPO)
        finally:
            if previous is None:
                os.environ.pop("TEST_DATABASE_URL", None)
            else:
                os.environ["TEST_DATABASE_URL"] = previous


class TestTestDbUrl_LongPathsStayUniqueAndLegal:
    """AC-5: at the 63-byte identifier limit the name truncates, not collides.

    Postgres does not refuse an over-long database name — it **truncates** it
    to ``NAMEDATALEN - 1`` = 63 bytes and says so in a notice. So a scheme
    that let the name grow past 63 would hand two different deep worktrees
    one database, quietly, which is this card's bug wearing a different hat.
    The digest is therefore inside the budget rather than appended to it.

    Measured: ``nonogram_`` + up to 36 slug characters + ``_`` + 12 digest
    characters + ``_test`` = **63 bytes at saturation**; the two real roots on
    this board come out at 41 bytes (the repo) and 50 bytes (this worktree).
    """

    #: ``nonogram_`` + slug + ``_`` + digest + ``_test``.
    EXPECTED_SATURATED_LENGTH = 9 + SLUG_CHARACTERS + 1 + DIGEST_CHARACTERS + len(SUFFIX)

    def test_the_budget_adds_up_to_the_postgres_limit(self):
        # Computed from the module's own constants, so a change to any of them
        # that overflows the limit fails here rather than in Postgres.
        assert self.EXPECTED_SATURATED_LENGTH == MAX_IDENTIFIER_BYTES == 63

    def test_the_measured_lengths_of_the_names_this_board_uses(self):
        lengths = {
            "/Users/omelnikova/PycharmProjects/PythonProject4": 41,
            "/Users/omelnikova/PycharmProjects/PythonProject4-card-244": 50,
        }
        for root, expected in lengths.items():
            name = derive_test_database_name(root)
            assert len(name.encode("utf-8")) == expected, (root, name, len(name))

    def test_a_long_root_saturates_at_the_limit_and_stays_legal(self):
        long_root = "/Users/omelnikova/PycharmProjects/" + "a" * 120
        name = derive_test_database_name(long_root)
        assert len(name.encode("utf-8")) == MAX_IDENTIFIER_BYTES
        assert _is_legal_database_name(name), name

    def test_two_long_roots_that_truncate_alike_still_differ(self):
        """The case the truncation itself creates.

        Both basenames agree on their first 80 characters, so the readable
        part of the name is identical after truncation; only the digest — taken
        over the **whole** resolved path, not the truncated slug — separates
        them.
        """
        shared = "worktree-" + "x" * 80
        first = derive_test_database_name(f"/Users/o/trees/{shared}-aaa")
        second = derive_test_database_name(f"/Users/o/trees/{shared}-bbb")

        assert first != second
        assert first[: 9 + SLUG_CHARACTERS] == second[: 9 + SLUG_CHARACTERS], (
            "the readable part should be identical here; the digest is the "
            "only thing keeping these two apart, and that is what is tested"
        )
        for name in (first, second):
            assert len(name.encode("utf-8")) == MAX_IDENTIFIER_BYTES
            assert _is_legal_database_name(name), name

    def test_two_long_roots_with_the_same_basename_still_differ(self):
        """Sibling checkouts of the same name under different parents.

        ``…/a/PythonProject4`` and ``…/b/PythonProject4`` have the same
        basename, so a scheme that hashed only the basename would merge them.
        """
        deep = "/".join("d" * 20 for _ in range(6))
        first = derive_test_database_name(f"/Users/o/{deep}/one/PythonProject4")
        second = derive_test_database_name(f"/Users/o/{deep}/two/PythonProject4")
        assert first != second
        assert first.rsplit("_", 3)[0] == second.rsplit("_", 3)[0]

    def test_a_corpus_of_long_roots_is_distinct_and_within_the_limit(self):
        rng = random.Random(5244)
        roots = []
        for _ in range(300):
            tail = "".join(rng.choice("ab-_.XY") for _ in range(rng.randint(60, 140)))
            roots.append(f"/Users/omelnikova/PycharmProjects/PythonProject4-{tail}")
        roots = sorted(set(roots))
        assert len(roots) >= 300, "the corpus shrank; it is the measurement"

        names = [derive_test_database_name(root) for root in roots]
        assert len(set(names)) == len(names), "two long roots derived one name"
        over = [n for n in names if len(n.encode("utf-8")) > MAX_IDENTIFIER_BYTES]
        assert over == [], over
        assert all(_is_legal_database_name(n) for n in names)

    def test_a_root_with_no_usable_basename_still_derives_a_legal_name(self):
        # ``/`` has no basename, and a basename of pure punctuation leaves no
        # slug at all; the digest alone must still make a legal name.
        for root in ("/", "/'\";&", "/漢字"):
            name = derive_test_database_name(root)
            assert _is_legal_database_name(name), (root, name)
            assert name.endswith(SUFFIX)


#: The names the suite must never set up, create, drop, connect to or truncate.
#:
#: ``nonogram_poc`` is the live admin panel's database and holds the owner's
#: real puzzles; ``nonogram_dev`` is the development one. They head the list
#: because this card's one catastrophic defect would be a derivation that
#: reached either. The rest are the shapes that *look* close enough to pass a
#: looser rule: a name that merely contains "test" (CARD-109's bar, not this
#: one), a backup of the old shared database, the maintenance database the
#: ``CREATE DATABASE`` is issued through, and the uppercase spellings that a
#: case-insensitive comparison would have let in.
_NAMES_THAT_MUST_BE_REFUSED = (
    "nonogram_poc",
    "nonogram_dev",
    "nonogram",
    "postgres",
    "template1",
    "test_nonogram",
    "nonogram_test_backup",
    "nonogram_testing",
    "NONOGRAM_POC_TEST",
    "nonogram_poc_TEST",
)

#: URLs whose *path* ends in ``_test`` while something else decides where the
#: driver actually connects, or that cannot be read at all. Paired with the
#: token the refusal must name.
_URLS_THAT_MUST_BE_REFUSED = (
    ("postgresql://u:{pw}@192.0.2.1:5432/nonogram_test?dbname=nonogram_poc", "dbname"),
    ("postgresql://u:{pw}@192.0.2.1:5432/nonogram_test?database=nonogram_dev", "database"),
    ("postgresql://u:{pw}@192.0.2.1/nonogram_test?sslmode=x&DBNAME=nonogram_poc", "DBNAME"),
    # No database at all: libpq would substitute the connecting user's own.
    ("postgresql://u:{pw}@192.0.2.1:5432/", "''"),
    ("postgresql://u:{pw}@192.0.2.1:5432", "''"),
    # Unparseable (the port is not a number) — refused without echoing it.
    (
        "postgresql://u:{pw}@192.0.2.1:notaport/nonogram_test",
        "not a URL SQLAlchemy can parse",
    ),
)


class TestTestDbSetup_StillRefusesANonTestDatabase:
    """AC-4 / G-1: deriving a name opened no path to ``nonogram_poc``.

    Before this card one function could erase a database:
    ``_test_database_tables``, guarded by ``_refuse_unless_test_database``.
    This card adds a second dangerous one — ``_ensure_test_database`` issues
    ``CREATE DATABASE`` — so **both** are asserted here, against one list of
    names, rather than trusting that "the derived names all end in ``_test``"
    will go on being true.

    Nothing may connect. The host is TEST-NET-1 (192.0.2.1, RFC 5737), which
    routes nowhere, so even a guard that failed open could not reach a real
    ``nonogram_poc``; and the spies record every attempt to build an engine or
    open a DBAPI connection, so the attempt itself is what fails the test
    (CARD-156's Fix-1 F-002 learned that the hard way — a refusal moved below
    the reachability check reported SKIPPED, green in a "0 failed" gate).
    """

    @pytest.fixture
    def connection_attempts(self, monkeypatch):
        """Every engine or connection anything tries to open, and it must be none."""
        import psycopg2
        import sqlalchemy

        import tests.conftest as suite_conftest
        from nonogram.db import session as db_session_module

        attempts: list[str] = []

        def spy(name):
            def record(*args, **kwargs):
                attempts.append(f"{name}{args[:1]}")
                raise AssertionError(f"{name} called for a refused database")
            return record

        monkeypatch.setattr(sqlalchemy, "create_engine", spy("sqlalchemy.create_engine"))
        monkeypatch.setattr(
            db_session_module, "create_engine", spy("session.create_engine")
        )
        monkeypatch.setattr(psycopg2, "connect", spy("psycopg2.connect"))
        # A cached verdict, or a cached creation attempt, would answer without
        # the call the spies are watching for.
        monkeypatch.setattr(suite_conftest, "_DATABASE_VERDICTS", {})
        monkeypatch.setattr(suite_conftest, "_DATABASE_CREATION_ATTEMPTS", {})
        return attempts

    @pytest.mark.parametrize("name", _NAMES_THAT_MUST_BE_REFUSED)
    def test_the_fixtures_refusal_still_names_and_refuses_it(
        self, name, connection_attempts
    ):
        url = f"postgresql://someone:{_SECRET}@192.0.2.1:5432/{name}"
        try:
            with pytest.raises(pytest.fail.Exception) as refused:
                _refuse_unless_test_database(url)
        finally:
            assert connection_attempts == [], connection_attempts

        assert repr(name) in str(refused.value)
        assert _SECRET not in str(refused.value)

    @pytest.mark.parametrize("name", _NAMES_THAT_MUST_BE_REFUSED)
    def test_the_creation_path_will_not_make_it_either(
        self, name, connection_attempts
    ):
        """The new ``CREATE DATABASE`` must not be aimable at the panel's database.

        It answers with a reason rather than raising, because its callers can
        only skip (G-2) — but it must answer *without touching anything*, and
        the reason must be the refusal's, not "I could not connect".
        """
        url = f"postgresql://someone:{_SECRET}@192.0.2.1:5432/{name}"
        try:
            reason = _ensure_test_database(url)
        finally:
            assert connection_attempts == [], connection_attempts

        assert reason is not None, f"{name} was not refused creation"
        assert repr(name) in reason
        assert _SECRET not in reason

    @pytest.mark.parametrize("template,token", _URLS_THAT_MUST_BE_REFUSED)
    def test_a_url_that_redirects_the_driver_is_refused_by_both(
        self, template, token, connection_attempts
    ):
        url = template.format(pw=_SECRET)
        try:
            with pytest.raises(pytest.fail.Exception) as refused:
                _refuse_unless_test_database(url)
            reason = _ensure_test_database(url)
        finally:
            assert connection_attempts == [], connection_attempts

        assert reason is not None, "the creation path did not refuse it"
        for message in (str(refused.value), reason):
            assert token in message, message
            assert _SECRET not in message

    def test_a_name_it_cannot_classify_is_not_created(self):
        """ADR-0039/R2's default-deny, on the one statement that takes no parameters.

        ``CREATE DATABASE`` cannot bind its identifier, so the name is
        interpolated. This name ends in ``_test``, so the *refusal* lets it
        through — and the creation path must still decline it rather than
        reason about how its quoting handles a double quote and a semicolon.
        Nothing connects, so nothing is created either way; the assertion is
        that it declined and said why.
        """
        import sqlalchemy

        import tests.conftest as suite_conftest

        hostile = 'nonogram_"; DROP DATABASE nonogram_poc; --_test'
        url = f"postgresql://u:p@192.0.2.1:5432/{hostile}"

        attempts: list = []
        original = sqlalchemy.create_engine
        suite_conftest._DATABASE_CREATION_ATTEMPTS.clear()
        try:
            sqlalchemy.create_engine = lambda *a, **k: attempts.append(a) or original(*a, **k)
            # The refusal itself cannot stop this one: the name ends in _test.
            _refuse_unless_test_database(url)
            reason = _ensure_test_database(url)
        finally:
            sqlalchemy.create_engine = original
            suite_conftest._DATABASE_CREATION_ATTEMPTS.clear()

        assert attempts == [], attempts
        assert reason is not None and "[a-z0-9_]" in reason, reason

    def test_the_refusal_is_what_stops_it_and_not_something_else(self):
        """The control for every case above (ADR-0039/R1).

        "``nonogram_poc`` is never created" is the kind of claim that passes
        for the wrong reason — an unreachable host, a cached verdict, a typo in
        the test's URL. So the rule is removed and the same case re-run: with
        :func:`_refusal_reason` neutralised, ``nonogram_poc`` reaches
        ``create_engine``. That is what makes the assertion above a measurement
        of the guard rather than of the network.

        Nothing connects here either: the engine is never built, because the
        spy raises on the attempt — recording it is the whole point.
        """
        import sqlalchemy

        import tests.conftest as suite_conftest

        url = "postgresql://u:p@192.0.2.1:5432/nonogram_poc"
        attempts: list = []

        def spy(*args, **kwargs):
            attempts.append(args[0])
            raise AssertionError("stopped before connecting")

        original_refusal = suite_conftest._refusal_reason
        original_engine = sqlalchemy.create_engine
        try:
            suite_conftest._refusal_reason = lambda _url: None
            sqlalchemy.create_engine = spy
            suite_conftest._DATABASE_CREATION_ATTEMPTS.clear()
            _ensure_test_database(url)
        except AssertionError:
            pass
        finally:
            suite_conftest._refusal_reason = original_refusal
            sqlalchemy.create_engine = original_engine
            suite_conftest._DATABASE_CREATION_ATTEMPTS.clear()

        assert len(attempts) == 1, (
            "the control did not fire: with the refusal removed, "
            "_ensure_test_database should have reached create_engine, so the "
            "passing cases above may be passing for some other reason"
        )
        # And it was aimed at the maintenance database of that very URL — i.e.
        # the refusal is the only thing between CREATE DATABASE and the panel.
        assert attempts[0].database == _MAINTENANCE_DATABASE


# --------------------------------------------------------------------------
# The executed half: AC-2 and AC-6 run real pytest processes.
#
# "Measure with the runner that gates" — a bare module exec cost this board
# three wrong diagnoses, and both of these claims are about what a pytest
# process does to a database, which only a pytest process can show.
# --------------------------------------------------------------------------

#: How long a probe waits for its peer before calling the rendezvous broken.
#: Comfortably under the hang guard's 120s per test, so a peer that never
#: arrives fails with an explanation rather than a stack dump.
_RENDEZVOUS_SECONDS = 45.0


def _server_url(reference_url: str, database: str) -> str:
    """``reference_url``'s server, pointed at ``database``.

    Built from the session's own ``test_db_url`` rather than from a constant,
    so these tests follow whatever host, port and credentials the owner or CI
    configured instead of assuming localhost.
    """
    from nonogram.db import session as db_session

    url = db_session.normalized_url(reference_url).set(database=database)
    # Not ``str(url)``: SQLAlchemy renders the password as ``***`` there, and
    # the subprocess needs a URL it can actually authenticate with.
    return url.render_as_string(hide_password=False)


def _maintenance_engine(reference_url: str):
    from sqlalchemy import create_engine

    from nonogram.db import session as db_session

    return create_engine(
        db_session.normalized_url(reference_url).set(database=_MAINTENANCE_DATABASE),
        isolation_level="AUTOCOMMIT",
        **db_session._engine_options(reference_url),
    )


def _existing_databases(reference_url: str) -> set[str]:
    """``pg_database`` — the authority, enumerated, rather than a guess."""
    from sqlalchemy import text

    engine = _maintenance_engine(reference_url)
    try:
        with engine.connect() as connection:
            return set(connection.execute(text("SELECT datname FROM pg_database")).scalars())
    finally:
        engine.dispose()


def _drop_database(reference_url: str, name: str) -> None:
    """Remove a database this test made.

    The name is checked against the shape this test file creates before the
    statement is built, not because the caller is untrusted but because this
    is the one function in the suite that can destroy a database outright, and
    ``nonogram_poc`` is three characters away from several of the strings
    nearby.
    """
    from sqlalchemy import text

    assert name.startswith("nonogram_") and name.endswith(SUFFIX), name
    assert re.fullmatch(r"[a-z0-9_]+", name), name
    assert name not in ("nonogram_poc", "nonogram_dev", "nonogram_test"), name

    engine = _maintenance_engine(reference_url)
    try:
        with engine.connect() as connection:
            # A pooled connection a finished subprocess left behind would make
            # DROP DATABASE refuse; close them first rather than retry.
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        engine.dispose()


def _alembic_head() -> tuple[str, ...]:
    """Head read from the migration scripts themselves, no ``env.py`` run.

    The independent side of "migrated to head": asking the database what
    version it is at and comparing it to what the scripts say head is, rather
    than to what the fixture believes it ran.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    return tuple(ScriptDirectory.from_config(Config(str(REPO / "alembic.ini"))).get_heads())


def _version_in(database_url: str) -> tuple[str, ...]:
    from sqlalchemy import create_engine, text

    from nonogram.db import session as db_session

    engine = create_engine(
        db_session.normalized_url(database_url),
        **db_session._engine_options(database_url),
    )
    try:
        with engine.connect() as connection:
            return tuple(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
    finally:
        engine.dispose()


def _pytest_env(**overrides) -> dict:
    """A clean environment for a child pytest: this run's own DB variables out.

    ``DATABASE_URL`` and ``TEST_DATABASE_URL`` are dropped unless an override
    puts them back, so a child never inherits the database *this* process is
    using — which would make every one of these assertions meaningless.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("DATABASE_URL", "TEST_DATABASE_URL")
    }
    env.update({k: v for k, v in overrides.items() if v is not None})
    return env


def _run_pytest(root: Path, target: str, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, "-m", "pytest", target,
            "-o", "addopts=", "-q", "-p", "no:cacheprovider",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.db_required
class TestTestDbSetup_CreatesTheDatabaseWhenAbsent:
    """AC-2: a database that has never existed is created, migrated, and used.

    This is what makes a per-tree name usable at all: the whole point is that
    a fresh worktree's database is new, and "it does not exist" used to reach
    the suite as a *skip*. A skip is green, so without this the card would have
    replaced "two cards corrupt each other" with "every new card tests
    nothing" — strictly worse, and much harder to notice.

    Run as a real pytest subprocess with **both** ``DATABASE_URL`` and
    ``TEST_DATABASE_URL`` pointed at the absent database, because that is what
    a worktree actually exports and because the two are read by different
    code: the ``db_required`` gate (which runs before any fixture, and so had
    to learn to create the database too) and the session fixture.
    """

    def test_a_database_that_has_never_existed_is_created_and_migrated(self, test_db_url):
        name = f"nonogram_card244_ac2_{os.getpid()}_test"
        url = _server_url(test_db_url, name)

        if name in _existing_databases(test_db_url):
            _drop_database(test_db_url, name)
        assert name not in _existing_databases(test_db_url), (
            "the premise of this test is that the database is absent"
        )

        try:
            run = _run_pytest(
                REPO,
                "tests/test_db_e2e_smoke.py::test_db_session_fixture_works",
                _pytest_env(DATABASE_URL=url, TEST_DATABASE_URL=url),
            )
            output = run.stdout + run.stderr

            assert run.returncode == 0, output
            assert "1 passed" in output, output
            # The failure this guards against is a *green* one, so the word is
            # asserted absent rather than the exit code asserted zero alone.
            assert "skipped" not in output, output
            assert name in _existing_databases(test_db_url), output
            assert _version_in(url) == _alembic_head()
        finally:
            _drop_database(test_db_url, name)

    def test_the_same_absent_database_skips_rather_than_fails_with_no_server(
        self, test_db_url
    ):
        """G-2: an unreachable server is still a skip, and now says more.

        Port 1 on TEST-NET-1 refuses everything, so this is the "Postgres is
        not running" path with the database also absent — both reasons at
        once. It must come back as a skip (not a failure, G-2) and the skip
        must name the creation that could not happen, because a skip nobody can
        explain is how the 48-test phantom regression happened.
        """
        name = f"nonogram_card244_offline_{os.getpid()}_test"
        url = f"postgresql://postgres:postgres@192.0.2.1:1/{name}"

        run = _run_pytest(
            REPO,
            "tests/test_db_e2e_smoke.py::test_db_session_fixture_works",
            _pytest_env(
                DATABASE_URL=url,
                TEST_DATABASE_URL=url,
                # The connect deadline is ten seconds; two of them plus pytest
                # start-up must stay inside the subprocess timeout.
                NONOGRAM_TEST_HANG_SECONDS="0",
            ),
        )
        output = run.stdout + run.stderr

        assert run.returncode == 0, output
        assert "1 skipped" in output, output
        assert name not in _existing_databases(test_db_url), output


#: The probe each of AC-6's two trees runs. Generated into the tree rather
#: than kept as a file in ``tests/``, so it is not part of the suite and
#: cannot be run by accident with half its environment missing.
#:
#: The two processes are ordered by a filesystem rendezvous instead of by
#: sleeping, so the interleaving that matters is *forced* rather than hoped
#: for: tree B waits for tree A to have committed a row before B's session
#: fixture reaches ``DROP SCHEMA``, and A does not look at its own row until
#: B has finished writing. Against one shared database that order destroys
#: A's row every single time; against two it cannot. A test that depends on
#: timing is how a counterfactual quietly stops being one.
#:
#: The wait for the peer is at *import* time on purpose. Waiting inside the
#: test body would order the two test bodies, leaving the session fixtures —
#: the ``DROP SCHEMA`` that does the actual damage — to race.
_PROBE = '''\
"""Generated by tests/test_db_isolation.py (CARD-244). Not part of the suite."""

import os
import time
from pathlib import Path

TAG = os.environ["CARD244_TAG"]
SIGNAL = Path(os.environ["CARD244_SIGNAL"])
PEER = Path(os.environ["CARD244_PEER"])
DEADLINE = float(os.environ["CARD244_DEADLINE"])


def _wait_for(path):
    limit = time.monotonic() + DEADLINE
    while not path.exists():
        if time.monotonic() > limit:
            raise AssertionError(f"{TAG}: peer never reached {path}")
        time.sleep(0.02)


if os.environ.get("CARD244_WAIT_FIRST"):
    _wait_for(Path(os.environ["CARD244_WAIT_FIRST"]))


def test_this_tree_sees_only_its_own_rows(db_session):
    from nonogram.db.models import Batch

    session = db_session()
    try:
        session.add(Batch(theme=TAG))
        session.commit()
    finally:
        session.close()

    SIGNAL.write_text(TAG)
    _wait_for(PEER)

    session = db_session()
    try:
        themes = sorted(t for (t,) in session.query(Batch.theme).all())
    finally:
        session.close()
    assert themes == [TAG], f"{TAG} saw {themes}"
'''

#: What a second repo root needs for a pytest process to reach ``db_session``.
#: Directories are copied, not linked — see :func:`_make_root`.
_ROOT_CONTENTS = (
    "pyproject.toml",
    "alembic.ini",
    "migrations",
    "src",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/db_name.py",
    "tests/hang_guard.py",
    "tests/database_guard.py",
    # CARD-255: the third module `tests/conftest.py` imports a hook from. A
    # copied root without it cannot import its own conftest, and both arms of
    # AC-6 below come back red for a reason that has nothing to do with
    # databases. Each copied root is its own main root (no `.git`), so it
    # resolves a lock path of its own, finds nothing there, and the probes run
    # exactly as they did.
    "tests/full_suite_lock.py",
    "tests/helpers",
)


def _make_root(destination: Path) -> Path:
    """A second repo root: what a pytest process needs, **copied**.

    Copied and not symlinked, because ``tests/db_name.py`` derives the
    database name from ``Path(__file__).resolve().parent.parent`` — and
    ``resolve()`` follows symlinks, so a linked tree would resolve back to
    this repo and both processes would derive the *same* name. That would make
    AC-6's two arms identical and its green meaningless.
    """
    import shutil

    destination.mkdir(parents=True, exist_ok=True)
    for relative in _ROOT_CONTENTS:
        source = REPO / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(
                source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
        else:
            shutil.copyfile(source, target)
    (destination / "tests" / "test_probe_card244.py").write_text(_PROBE)
    return destination


def _run_two_trees(
    roots: tuple[Path, Path], rendezvous: Path, shared_url: str | None
) -> list[subprocess.CompletedProcess]:
    """Run both trees' probes at once; return their results in tree order.

    ``shared_url`` is the single variable between AC-6's two arms. ``None``
    lets each tree derive its own database (the fix); a URL forces both onto
    that one database (the world before the fix).
    """
    rendezvous.mkdir(parents=True, exist_ok=True)
    signals = [rendezvous / "tree-a", rendezvous / "tree-b"]
    results: list = [None, None]

    def go(index: int):
        results[index] = _run_pytest(
            roots[index],
            "tests/test_probe_card244.py",
            _pytest_env(
                TEST_DATABASE_URL=shared_url,
                CARD244_TAG=("a", "b")[index],
                CARD244_SIGNAL=str(signals[index]),
                CARD244_PEER=str(signals[1 - index]),
                CARD244_DEADLINE=str(_RENDEZVOUS_SECONDS),
                # Only B waits: it must not reach DROP SCHEMA until A has
                # committed a row there is something to destroy.
                CARD244_WAIT_FIRST=str(signals[0]) if index == 1 else None,
            ),
        )

    threads = [threading.Thread(target=go, args=(i,)) for i in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


@pytest.mark.db_required
@pytest.mark.slow
class TestDbIsolation_TwoTreesDoNotCorruptEachOther:
    """AC-6: the property this card exists for, executed — and its control.

    Two pytest processes, two real repo roots, started together. With
    per-worktree names each sees only its own rows. **And then the same pair
    is run again against one shared database and must come back red** —
    without that, "two processes do not corrupt each other" is a claim whose
    control cannot fail, which is exactly what ADR-0039/R1 calls narrative
    rather than coverage, and exactly the shape of claim wave 43's retro found
    behind every gating finding on this board.

    The red is not hypothetical: wave 44 produced two failures in
    ``test_book_trim_persistence`` under contention that are 200 passed in
    isolation, and a 48-test phantom regression in CARD-222's build gate. The
    control arm reproduces that mechanism on demand.

    One test, not two, because the two arms are one measurement: an isolation
    proof whose control was skipped (no Postgres, a changed fixture) is not a
    proof, and splitting them would let the green half pass alone.
    """

    def test_two_trees_pass_concurrently_and_the_same_pair_reds_when_they_share(
        self, test_db_url, tmp_path
    ):
        roots = (_make_root(tmp_path / "tree-a"), _make_root(tmp_path / "tree-b"))
        derived = [derive_test_database_name(root) for root in roots]
        assert derived[0] != derived[1], derived
        assert all(name not in _existing_databases(test_db_url) for name in derived), (
            "the probe databases must not pre-exist; the test creates them"
        )

        try:
            # ---- The fix: each tree derives its own database. -------------
            isolated = _run_two_trees(roots, tmp_path / "rv-isolated", shared_url=None)
            isolated_output = [r.stdout + r.stderr for r in isolated]

            assert all(name in _existing_databases(test_db_url) for name in derived), (
                isolated_output
            )
            for tag, result, output in zip("ab", isolated, isolated_output):
                assert result.returncode == 0, f"tree {tag}: {output}"
                assert "1 passed" in output, f"tree {tag}: {output}"
                # A skip would pass the returncode check while proving nothing
                # — the failure mode ADR-0038/R8 is about.
                assert "skipped" not in output, f"tree {tag}: {output}"

            # ---- The counterfactual: one database, same everything else. --
            shared = _run_two_trees(
                roots,
                tmp_path / "rv-shared",
                shared_url=_server_url(test_db_url, derived[0]),
            )
            shared_output = [r.stdout + r.stderr for r in shared]

            assert any(r.returncode != 0 for r in shared), (
                "the control did not fire: two trees sharing one database both "
                "passed, so the isolated arm above proves nothing about "
                "isolation. Check that the rendezvous still orders tree B's "
                "session fixture after tree A's write.\n"
                f"tree a:\n{shared_output[0]}\ntree b:\n{shared_output[1]}"
            )
            # And it must red for the stated reason — a destroyed row or a
            # destroyed schema — not because the probe failed to start.
            blamed = "\n".join(shared_output)
            assert ("saw []" in blamed or "saw ['b']" in blamed
                    or "UndefinedTable" in blamed or "does not exist" in blamed), blamed
        finally:
            for name in derived:
                _drop_database(test_db_url, name)
