"""CARD-148 — the database driver is named, not inherited from a default.

    AC-1  TestDbUrl_DriverIsNamedNotInherited
    AC-2  TestDbUrl_TheResolvedDriverIsInstalled
    AC-3  TestDependencyBaseline_SqlalchemyIsNotCapped
    AC-4  TestDbUrl_InMemoryModeImportsNoDriver
    EC-1  TestDbUrl_NormalisationChangesNothingElse

The outage this pins, in one line: **nothing in this repository changed.**

`requirements.txt` asked for `sqlalchemy>=2.0`. On 2026-09-25 SQLAlchemy
released 2.1.0, which changed the default DBAPI for a bare `postgresql://` URL
from psycopg2 to psycopg (v3). Render's managed Postgres issues a bare
`postgresql://` and this project installs psycopg2-binary, not psycopg. The
next build resolved to 2.1.0 and the panel stopped booting with
`ModuleNotFoundError: No module named 'psycopg'`.

The whole suite was green while that was true, and it stayed green for the same
reason the deploy failed: the venv here is pinned by history to 2.0.52, where
the same bare URL resolves to psycopg2. Nothing in the tree asserted *which*
driver the engine would be built on, so the one fact that differed between this
machine and production was the one fact nobody was checking.

So the tests below assert against what is **installed** rather than against a
version number. A test that said "SQLAlchemy must be 2.0.x" would pass on the
day the next default changes and tell nobody anything; a test that resolves the
URL the panel actually hands `create_engine` and then imports that driver fails
on exactly the days it should.
"""

from __future__ import annotations

import logging
import os
import random
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from sqlalchemy.engine import URL, make_url

from nonogram.db import session as db_session

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# AC-1 — the URL handed to create_engine names its driver
# --------------------------------------------------------------------------


class TestDbUrl_DriverIsNamedNotInherited:
    """Every scheme `DATABASE_URL` can carry arrives at `create_engine` named."""

    @pytest.mark.parametrize(
        "scheme",
        [
            # What Render's managed Postgres hands out, and the shape that
            # broke: no driver, so SQLAlchemy picked one.
            pytest.param("postgresql", id="bare-postgresql"),
            # Render's legacy alias. SQLAlchemy dropped it in 1.4 — `make_url`
            # still parses it and `get_dialect()` then raises
            # NoSuchModuleError, so this one was never merely inheriting a
            # default, it was broken outright.
            pytest.param("postgres", id="legacy-postgres-alias"),
            # Already correct; must survive being normalised.
            pytest.param("postgresql+psycopg2", id="already-explicit"),
            # URL schemes are case-insensitive; SQLAlchemy's dialect registry
            # is not.
            pytest.param("POSTGRESQL", id="uppercase-scheme"),
        ],
    )
    def test_the_engine_url_names_the_shipped_driver(self, scheme: str) -> None:
        url = db_session.normalized_url(
            f"{scheme}://panel:secret@db.example.com:5432/nonogram"
        )
        assert url.drivername == f"postgresql+{db_session.POSTGRES_DRIVER}"

    def test_the_shipped_driver_is_the_one_the_project_installs(self) -> None:
        """The constant is not a guess — it is the package in the `db` extra.

        `POSTGRES_DRIVER` and `psycopg2-binary` are two statements of the same
        fact in two files, which is the shape that drifts. Asserted here rather
        than trusted, because the drift would look exactly like the outage.
        """
        extras = _pyproject()["project"]["optional-dependencies"]["db"]
        installed_dbapis = {
            requirement.split(">")[0].split("=")[0].split("<")[0].strip().lower()
            for requirement in extras
        }
        driver = db_session.POSTGRES_DRIVER
        # `psycopg2-binary` and `psycopg2` are the same DBAPI under two
        # distribution names, and either is a legitimate way to install it.
        assert {driver, f"{driver}-binary"} & installed_dbapis, (
            f"session.POSTGRES_DRIVER is {driver!r}, "
            f"but the db extra installs {sorted(installed_dbapis)}"
        )

    def test_an_explicitly_chosen_other_driver_is_left_alone(self) -> None:
        """A named driver is a decision; only an *absent* one is the defect.

        Overriding `postgresql+psycopg://` would make this normalisation the
        very thing it replaces — code deciding the DBAPI behind the operator's
        back. The backend alias is still canonicalised, because `postgres+x`
        is not a dialect SQLAlchemy can load.
        """
        assert (
            db_session.normalized_url("postgresql+psycopg://u:p@h/db").drivername
            == "postgresql+psycopg"
        )
        assert (
            db_session.normalized_url("postgres+pg8000://u:p@h/db").drivername
            == "postgresql+pg8000"
        )

    def test_a_non_postgres_url_passes_through_untouched(self, tmp_path) -> None:
        """SQLite runs every legacy and test path here; it has no business
        acquiring a PostgreSQL DBAPI."""
        raw = f"sqlite:///{tmp_path / 'admin.db'}"
        assert db_session.normalized_url(raw) == make_url(raw)
        assert db_session.normalized_url(raw).drivername == "sqlite"

    def test_create_engine_receives_the_named_url_with_its_password_intact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The production path, and the trap inside it.

        `str(url)` renders the password as `***`. Normalising via text would
        therefore produce a URL that looks right in a log and cannot
        authenticate — a failure that arrives as "password authentication
        failed" and points at the database. So the object is passed through,
        and this test is what says so: it captures the actual argument
        `_init_engine` gives `create_engine` and checks both that it is a `URL`
        and that the secret survived.
        """
        captured: list = []

        def capturing(url, **kwargs):
            captured.append(url)
            return object()

        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://panel:s3cr3t-p%40ss@db.example.com:5432/nono"
        )
        monkeypatch.setattr(db_session, "create_engine", capturing)
        monkeypatch.setattr(db_session, "sessionmaker", lambda **kwargs: None)
        monkeypatch.setattr(db_session, "engine", None)
        monkeypatch.setattr(db_session, "_engine_url", None)

        db_session._init_engine()

        assert len(captured) == 1
        handed_over = captured[0]
        assert isinstance(handed_over, URL), (
            "a string here means the password went through str(url) at some "
            f"point and may be '***': {handed_over!r}"
        )
        assert handed_over.drivername == f"postgresql+{db_session.POSTGRES_DRIVER}"
        assert handed_over.password == "s3cr3t-p@ss"

    def test_the_connect_deadline_still_reaches_a_normalised_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CARD-097's libpq deadline must not be lost to CARD-148's rewrite.

        `_engine_options` decides by scheme, and the scheme it reads is now one
        step away from the scheme `create_engine` sees. Both spellings Render
        can send are checked, since the legacy alias is the one a scheme-by-
        string check is most likely to miss.
        """
        for scheme in ("postgresql", "postgres", "POSTGRESQL"):
            options = db_session._engine_options(f"{scheme}://u:p@h/db")
            assert options["connect_args"]["connect_timeout"] == (
                db_session.CONNECT_TIMEOUT_SECONDS
            )
        assert db_session._engine_options("sqlite:///x.db") == {}


# --------------------------------------------------------------------------
# AC-2 — the driver that gets used is a driver that exists here
# --------------------------------------------------------------------------


class TestDbUrl_TheResolvedDriverIsInstalled:
    """The test the outage owed: resolve, then actually import.

    Note what is asserted and what is not. Not "SQLAlchemy is version X" — that
    passes on the day the default moves. Not "SQLAlchemy's default for a bare
    `postgresql://` is importable" either, because after AC-1 that default is
    no longer what the panel uses, and demanding it be installed would make the
    suite red on a perfectly healthy 2.1.x install for a driver this project
    deliberately does not ship.

    What is asserted is the thing that was actually false on 2026-09-25: the
    DBAPI the panel's engine would be built on is importable. Run against the
    code as it stood before this card — where the URL reached `create_engine`
    bare — this fails on SQLAlchemy 2.1.x and passes on 2.0.x, which is exactly
    the difference between production and this machine that nothing caught.
    """

    def test_the_driver_the_panel_would_use_can_be_imported(self) -> None:
        url = db_session.normalized_url(
            "postgresql://panel:secret@db.example.com:5432/nonogram"
        )
        dialect = url.get_dialect()
        assert dialect.driver == db_session.POSTGRES_DRIVER
        # The assertion is the call: `import_dbapi` raises ImportError when the
        # DBAPI is not installed, which is the ModuleNotFoundError the deploy
        # died of, relocated to a test.
        assert dialect.import_dbapi() is not None

    def test_every_scheme_the_environment_can_send_resolves_to_a_real_driver(
        self,
    ) -> None:
        """Including the legacy alias, which does not resolve at all unencoded."""
        for scheme in ("postgresql", "postgres", "POSTGRESQL", "postgresql+psycopg2"):
            dialect = db_session.normalized_url(f"{scheme}://u:p@h/db").get_dialect()
            assert dialect.import_dbapi() is not None, scheme

    def test_the_resolution_does_not_depend_on_the_installed_default(self) -> None:
        """What SQLAlchemy would have chosen is recorded, never relied upon.

        On 2.0.x `inherited` is 'psycopg2' and on 2.1.x it is 'psycopg'; the
        panel's own answer is the same on both. That invariance *is* the fix,
        and it is the one assertion here that a future default change cannot
        quietly satisfy.
        """
        inherited = make_url("postgresql://u:p@h/db").get_dialect().driver
        chosen = db_session.normalized_url("postgresql://u:p@h/db").get_dialect().driver

        assert chosen == db_session.POSTGRES_DRIVER
        if inherited != chosen:
            # Not a failure — a fact worth printing on the day it appears,
            # because it means this machine is now resolving the way the failed
            # deploy did and the normalisation is the only thing standing
            # between the two.
            print(
                f"note: SQLAlchemy's default for a bare postgresql:// is "
                f"{inherited!r} here; the panel uses {chosen!r} regardless."
            )


# --------------------------------------------------------------------------
# AC-3 — the cap comes off, and the baseline it sat in does not move
# --------------------------------------------------------------------------


def _pyproject() -> dict:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def _requirements() -> list[str]:
    """`requirements.txt` without its comments or blank lines.

    Comments are stripped on purpose: the file explains the outage at length
    and the words `<2.1` appear in that explanation. A test that searched the
    raw text would be asserting about prose.
    """
    lines = []
    for line in (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        requirement = line.split("#", 1)[0].strip()
        if requirement:
            lines.append(requirement)
    return lines


class TestDependencyBaseline_SqlalchemyIsNotCapped:
    """The stopgap cap is gone from both files that carried it.

    A cap is a dependency on a deadline nobody chose: 2.0.x stops getting fixes
    eventually, and `<2.1` is the kind of line that survives for two years
    because removing it is scary. It comes off here, with AC-1 and AC-2 behind
    it, and these tests are what stop it being quietly reintroduced instead of
    the next default change being handled.
    """

    def test_requirements_txt_puts_no_ceiling_on_sqlalchemy(self) -> None:
        pinned = [r for r in _requirements() if r.lower().startswith("sqlalchemy")]
        assert pinned, "sqlalchemy vanished from requirements.txt"
        for requirement in pinned:
            assert "<" not in requirement, (
                f"{requirement!r} caps SQLAlchemy again. The cap was CARD-148's "
                "stopgap; naming the driver is the fix."
            )

    def test_the_db_extra_puts_no_ceiling_on_sqlalchemy(self) -> None:
        extra = _pyproject()["project"]["optional-dependencies"]["db"]
        pinned = [r for r in extra if r.lower().startswith("sqlalchemy")]
        assert pinned, "SQLAlchemy vanished from the db extra"
        for requirement in pinned:
            assert "<" not in requirement, f"{requirement!r} caps SQLAlchemy again"

    def test_the_two_files_agree_on_the_sqlalchemy_requirement(self) -> None:
        """Two files, one requirement. They drifted once already."""
        from_requirements = [
            r.lower().replace(" ", "")
            for r in _requirements()
            if r.lower().startswith("sqlalchemy")
        ]
        from_extra = [
            r.lower().replace(" ", "")
            for r in _pyproject()["project"]["optional-dependencies"]["db"]
            if r.lower().startswith("sqlalchemy")
        ]
        assert from_requirements == from_extra

    def test_the_runtime_baseline_is_still_pillow_and_numpy(self) -> None:
        """G-1 / ADR-0006/R1: this card moved no dependency into the core.

        The database packages stay in the `db` extra. Asserted here because
        "remove a cap" and "install a different driver" are one keystroke apart
        and only one of them was in scope.
        """
        names = {
            requirement.split(">")[0].split("=")[0].split("<")[0].strip().lower()
            for requirement in _pyproject()["project"]["dependencies"]
        }
        assert names == {"pillow", "numpy"}, (
            f"ADR-0006/R1's baseline moved: {sorted(names)}"
        )


# --------------------------------------------------------------------------
# AC-4 — without a DATABASE_URL, no driver is imported at all
# --------------------------------------------------------------------------


#: Every DBAPI a URL in this project could name, plus the stdlib one. In-memory
#: mode talks to no database, so none of these has any reason to be loaded —
#: and `sqlite3` is on the list precisely because it is free to import and so
#: the easiest to start importing by accident.
_DRIVER_MODULES = (
    "psycopg2",
    "psycopg",
    "pg8000",
    "asyncpg",
    "sqlite3",
    "MySQLdb",
    "pymysql",
)

_IN_MEMORY_PROBE = """
import os, sys

assert "DATABASE_URL" not in os.environ, "the probe was handed a DATABASE_URL"

from nonogram.admin.app import create_app

app = create_app()
# In-memory mode is a fact about the constructed services, not about a branch
# having been taken: a `None` session factory is what "no database" means here.
assert app.puzzle_review_service._session_factory is None, "not in-memory mode"

# A real request, so the assertion below covers the serving path rather than
# only the import of the module.
response = app.test_client().get("/")
assert response.status_code == 200, response.status_code

loaded = sorted(
    name for name in sys.modules
    if name.split(".")[0] in %(drivers)r
)
print("DRIVERS:" + ",".join(loaded))
"""


class TestDbUrl_InMemoryModeImportsNoDriver:
    """Naming a driver must not mean loading one when there is no database.

    Checked in a subprocess against `sys.modules`, because that is the only
    place the answer actually lives. Asserting that `_init_engine` returned
    early, or that a session factory is `None`, would prove a branch was taken
    and say nothing about whether some import at module scope had already
    pulled psycopg2 in — which is the failure this guards, and which a
    same-process test cannot see once any earlier test has imported the driver.
    """

    def test_no_database_driver_is_in_sys_modules(self) -> None:
        environment = dict(os.environ)
        environment.pop("DATABASE_URL", None)
        environment["PYTHONPATH"] = (
            str(REPO_ROOT / "src") + os.pathsep + str(REPO_ROOT)
        )

        finished = subprocess.run(
            [sys.executable, "-c", _IN_MEMORY_PROBE % {"drivers": _DRIVER_MODULES}],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=REPO_ROOT,
            env=environment,
        )

        output = finished.stdout + finished.stderr
        assert finished.returncode == 0, output
        reported = [
            line for line in finished.stdout.splitlines() if line.startswith("DRIVERS:")
        ]
        assert reported, output
        loaded = [name for name in reported[-1][len("DRIVERS:") :].split(",") if name]
        assert not loaded, (
            "in-memory mode imported a database driver: "
            f"{loaded} — nothing without a DATABASE_URL should"
        )

    def test_the_probe_would_notice_a_driver_that_was_imported(self) -> None:
        """The negative test above, shown detecting something.

        An assertion that a list is empty passes just as happily when the list
        can never be filled. So the same probe is run once more with an
        `import psycopg2` prepended: if that run also reports nothing, the
        detection is broken and the test above is decoration.
        """
        environment = dict(os.environ)
        environment.pop("DATABASE_URL", None)
        environment["PYTHONPATH"] = (
            str(REPO_ROOT / "src") + os.pathsep + str(REPO_ROOT)
        )

        finished = subprocess.run(
            [
                sys.executable,
                "-c",
                "import psycopg2\n"
                + _IN_MEMORY_PROBE % {"drivers": _DRIVER_MODULES},
            ],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=REPO_ROOT,
            env=environment,
        )

        output = finished.stdout + finished.stderr
        assert finished.returncode == 0, output
        assert "DRIVERS:psycopg2" in finished.stdout, output


# --------------------------------------------------------------------------
# EC-1 — nothing but the driver changes, and the password goes nowhere
# --------------------------------------------------------------------------


#: Fixed, so the corpus is the same set of URLs on every run and in every
#: checkout. `random.Random` rather than hypothesis: ADR-0006/R1's baseline is
#: closed and a property-testing library is not in it, so this project builds
#: its corpora by hand and asserts their size (see tests/README.md).
_CORPUS_SEED = 148

#: Below this the corpus has silently shrunk and the test is no longer the
#: statement it claims to be. The generator below enumerates deliberately — the
#: seed only shuffles and samples — so this floor is a real one.
_MINIMUM_CORPUS = 200

#: Passwords chosen for the characters that carry meaning inside a URL. Each
#: one is a password a reasonable generator produces and a naive
#: string-surgery normaliser mangles: `@` ends the credentials, `:` separates
#: them, `/` ends the authority, `?` starts the query, `#` starts a fragment,
#: and a literal `%` is where double-encoding shows up.
_PASSWORDS = (
    None,
    "",
    "simple",
    "p@ssword",
    "pa:ss",
    "pa/ss",
    "pa?ss",
    "pa#ss",
    "100%sure",
    "%40already%2Fencoded",
    "sp ace",
    "üñïçø∂e",
    "x" * 64,
)

_USERNAMES = (None, "panel", "nonogram_app", "user@corp", "us:er")

#: Including an IPv6 literal, which is the one host shape that needs brackets
#: and therefore the one a hand-rolled parser loses.
_HOSTS = (
    "localhost",
    "127.0.0.1",
    "2001:db8::1",
    "dpg-abc123-a.frankfurt-postgres.render.com",
)

_PORTS = (None, 5432, 5433)

_DATABASES = (None, "", "nonogram", "nonogram_test", "db-with-dash")

_QUERIES = (
    {},
    {"sslmode": "require"},
    {"sslmode": "require", "connect_timeout": "5"},
    {"application_name": "nonogram panel"},
)

#: Both spellings the environment can send, both cases, and both "already
#: explicit" shapes — the last of which must come out unchanged rather than
#: gaining a second `+driver`.
_SCHEMES = (
    "postgresql",
    "postgres",
    "POSTGRESQL",
    "postgresql+psycopg2",
    "postgresql+psycopg",
)


def _corpus() -> list[URL]:
    """Seeded URL shapes, as `URL` objects.

    Built as objects and rendered to text with `render_as_string(hide_password=
    False)` rather than assembled by hand. Two reasons. It is the only way to
    get the percent-encoding right for the passwords above without
    reimplementing it in the test — and reimplementing it is how a test ends up
    agreeing with a bug. And it means the *expected* value of every field is
    the object's own field, so the comparison is against something independent
    of the function under test.

    The enumeration is exhaustive over schemes × passwords, which is where the
    risk is; the other four components are cycled by the seeded generator so
    every combination of scheme and password is seen against a varied rest of
    the URL without the product exploding.
    """
    shuffler = random.Random(_CORPUS_SEED)
    urls: list[URL] = []
    for scheme in _SCHEMES:
        for password in _PASSWORDS:
            for _ in range(4):
                urls.append(
                    URL.create(
                        drivername=scheme,
                        username=shuffler.choice(_USERNAMES)
                        if password is None
                        else shuffler.choice([u for u in _USERNAMES if u]),
                        password=password,
                        host=shuffler.choice(_HOSTS),
                        port=shuffler.choice(_PORTS),
                        database=shuffler.choice(_DATABASES),
                        query=shuffler.choice(_QUERIES),
                    )
                )
    return urls


_CORPUS = _corpus()


class TestDbUrl_NormalisationChangesNothingElse:
    """EC-1, over a corpus rather than an example."""

    def test_the_corpus_is_the_size_it_claims_to_be(self) -> None:
        """A corpus can only shrink by accident, so its floor is asserted.

        Without this the whole class degrades quietly: an edit that drops a
        scheme or a password from the tuples above leaves every test below
        green and covering less.
        """
        assert len(_CORPUS) >= _MINIMUM_CORPUS, len(_CORPUS)
        assert len({url.render_as_string(hide_password=False) for url in _CORPUS}) >= (
            _MINIMUM_CORPUS // 2
        ), "the corpus is mostly duplicates"
        # Every shape the design called out is actually present.
        assert any(url.password is None for url in _CORPUS)
        assert any(url.password == "" for url in _CORPUS)
        assert any("@" in (url.password or "") for url in _CORPUS)
        assert any("%" in (url.password or "") for url in _CORPUS)
        assert any(url.host == "2001:db8::1" for url in _CORPUS)
        assert any(url.port is None for url in _CORPUS)
        assert any(url.database in (None, "") for url in _CORPUS)
        assert any(url.query for url in _CORPUS)
        assert any("+psycopg2" in url.drivername for url in _CORPUS)
        assert any("+psycopg" == url.drivername[-8:] for url in _CORPUS)
        assert any(url.drivername.isupper() for url in _CORPUS)

    def test_every_part_but_the_driver_survives(self) -> None:
        """Host, port, database, credentials and query, field by field.

        Field-by-field rather than by comparing rendered strings, because
        `render_as_string` sorts query parameters and normalises encoding — a
        string comparison would fail on URLs that are in fact identical, and
        the natural fix for that noise is to loosen the assertion until it
        stops saying anything.
        """
        for source in _CORPUS:
            raw = source.render_as_string(hide_password=False)
            result = db_session.normalized_url(raw)

            assert result.username == source.username, raw
            assert result.password == source.password, "password altered"
            assert result.host == source.host, raw
            assert result.port == source.port, raw
            assert result.database == source.database, raw
            assert dict(result.query) == dict(source.query), raw

    def test_every_postgres_url_in_the_corpus_comes_out_naming_a_driver(self) -> None:
        for source in _CORPUS:
            result = db_session.normalized_url(
                source.render_as_string(hide_password=False)
            )
            backend, plus, driver = result.drivername.partition("+")
            assert backend == "postgresql", result.drivername
            assert plus and driver, (
                f"{source.drivername!r} came out as {result.drivername!r} — "
                "still inheriting a default"
            )

    def test_normalising_twice_changes_nothing_further(self) -> None:
        """Idempotent, because it runs on whatever the last deploy left behind.

        An operator who fixes `DATABASE_URL` by hand — the obvious reaction to
        the outage — now hands this function a URL it already produced. If that
        were not a fixed point, the remedy and the fix together would be worse
        than either.
        """
        for source in _CORPUS:
            once = db_session.normalized_url(
                source.render_as_string(hide_password=False)
            )
            twice = db_session.normalized_url(
                once.render_as_string(hide_password=False)
            )
            assert twice == once, once.render_as_string(hide_password=True)

    def test_a_sqlite_url_is_returned_exactly_as_given(self, tmp_path) -> None:
        """The pass-through half of EC-1, over the shapes this project uses.

        Compared against ``make_url(raw)`` rather than against ``raw`` itself,
        and the difference is not pedantry: on SQLAlchemy 2.1
        ``render_as_string`` percent-encodes the colons in ``:memory:`` while
        2.0 leaves them alone. A string comparison here fails on 2.1 for a
        change this function did not make — it would be a test of SQLAlchemy's
        renderer wearing this card's name, and the obvious way to "fix" it
        would be to start doing string surgery in production.
        """
        for database in (
            f"{tmp_path / 'admin.db'}",
            f"{tmp_path / 'with space.db'}",
            ":memory:",
        ):
            for raw in (f"sqlite:///{database}", f"sqlite+pysqlite:///{database}"):
                result = db_session.normalized_url(raw)
                assert result == make_url(raw), raw
                assert result.database == make_url(raw).database, raw

    def test_no_password_in_the_corpus_reaches_a_log_record(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Nothing here logs, and that is asserted rather than assumed.

        A `DATABASE_URL` is the one configuration value that is also a secret,
        and the natural instinct when writing a normaliser is to log what it
        did. Captured at DEBUG so even a stray `logger.debug(url)` is caught.
        """
        with caplog.at_level(logging.DEBUG):
            for source in _CORPUS:
                db_session.normalized_url(
                    source.render_as_string(hide_password=False)
                )

        logged = "\n".join(record.getMessage() for record in caplog.records)
        for source in _CORPUS:
            if source.password:
                assert source.password not in logged, "a password was logged"
        assert not caplog.records, (
            f"normalized_url logged {len(caplog.records)} record(s): {logged}"
        )

    @pytest.mark.parametrize(
        "unparseable",
        [
            pytest.param("postgresql:/panel:{secret}@db.example.com/nono", id="one-slash"),
            pytest.param("://panel:{secret}@db.example.com/nono", id="no-scheme"),
            pytest.param("postgresql//panel:{secret}@db.example.com/nono", id="no-colon"),
            pytest.param("", id="empty"),
        ],
    )
    def test_an_unparseable_url_is_rejected_without_quoting_the_password(
        self, unparseable: str
    ) -> None:
        """The other half of "never reaches an exception message".

        SQLAlchemy's own `ArgumentError` has echoed the offending string back
        before now, and that string is where the password is. So the error is
        replaced rather than wrapped, and the replacement is checked for the
        secret in both the message and the traceback's chain — `raise ... from
        None` is what keeps the cause out of the latter, and it is easy to drop
        by accident.
        """
        secret = "hunter2-do-not-print-me"
        raw = unparseable.replace("{secret}", secret)

        with pytest.raises(RuntimeError) as failure:
            db_session.normalized_url(raw)

        assert secret not in str(failure.value)
        assert failure.value.__cause__ is None
        # `raise ... from None` leaves `__context__` set but marks it
        # suppressed, which is what stops the traceback printing it. The flag
        # is the thing to assert: without it the "During handling of the above
        # exception" block puts SQLAlchemy's message — and one day the URL —
        # back on stderr.
        assert failure.value.__suppress_context__ is True
        # The scheme is fair game and is the only thing worth saying: it is
        # what makes the error actionable at all.
        assert "DATABASE_URL" in str(failure.value)
