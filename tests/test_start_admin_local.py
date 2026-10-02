"""CARD-150: ``scripts/start_admin_local.sh`` refuses a database it cannot use.

How a shell script gets tested here
-----------------------------------

The script cannot be driven end to end: it finishes with ``flask run``, which
never returns. So it grew a ``--check-only`` flag that runs every check for
real and stops just short of that last line, and these tests drive the actual
file through it.

Everything the script talks to on the way is replaced by a stub earlier on
``PATH`` -- ``psql``, ``docker``, ``docker-compose``, ``alembic``, ``python`` --
and the script runs inside a throwaway project root built in ``tmp_path``.  Two
consequences, both deliberate:

* **No database is touched.**  Not created, not dropped, not migrated, not even
  connected to.  ``nonogram_dev``, ``nonogram_test`` and ``nonogram_poc`` are
  the owner's (CARD-150 G-2).
* **Nothing here needs PostgreSQL running**, so none of these tests can skip
  silently -- which would be a poor joke in the card about a database check.
  The stubs decide what is reachable, and the test asserts what the script
  *decided*, not what the machine happens to have.

The stubs also keep a log of how they were called, which is what makes the
original defect visible: a bare ``psql -c "SELECT 1"`` and a
``psql "$DATABASE_URL" -c "SELECT 1"`` both succeed against a running server,
and only the recorded argument list tells them apart.

CARD-151 made the ``psql`` stub a *model* rather than a yes-man.  An
always-succeeding stub passed a check that handed psql a driver-qualified
``postgresql+psycopg2://`` URL -- which real psql takes whole as a database
name -- and one that named no database, which real psql answers by connecting
to a database named after the user.  The model reproduces both measured
behaviours and logs what it would have connected to.
"""

from __future__ import annotations

import os
import re
import shutil
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "start_admin_local.sh"
README = REPO_ROOT / "scripts" / "README.md"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """The script writes a coloured ✓/✗ register; assert on the words."""
    return _ANSI.sub("", text)


# Stands in for psql.  It is a *model* of how real psql reads its target, not a
# yes-man: an always-succeeding stub passes a check that hands psql a string it
# cannot parse, and that is exactly how CARD-151's two defects got past
# CARD-150's suite.  The behaviours modelled were measured against the real
# psql on the owner's machine (CARD-151, "What to implement"):
#
# * only ``postgresql://`` and ``postgres://`` are URIs.  ``postgresql+psycopg2://``
#   is not one: with no ``=`` in it, the *whole string* is taken as a database
#   name ("FATAL: database "postgresql+psycopg://..." does not exist"); with an
#   ``=`` (a ``?query``) libpq tries to read it as ``key=value`` conninfo and
#   rejects the keyword;
# * a URI with no database name falls back to a database named after the user,
#   and a URI with no user to the login user ($PGUSER, else $USER here -- the
#   harness pins both, so the developer's own name cannot decide a test).
#
# Which databases "exist": every identifier-shaped name except STUB_MISSING_DB,
# or -- when STUB_EXISTING_DBS is set -- only the names it lists.  No server has
# a database called "postgresql+psycopg2://...".
#
# Written in Python with urllib.parse on purpose: the script under test is bash,
# and an independent second parser is what makes the cross-check worth having.
# Besides the raw ``psql ...`` line it logs a ``connect ...`` line -- what this
# psql would actually have connected to -- so a test can assert on the database,
# host, port and credentials the check carried.
_PSQL_MODEL = r"""
import os
import re
import sys
from urllib.parse import unquote, urlsplit

args = sys.argv[1:]
log = open(os.environ["STUB_LOG"], "a")
log.write("psql " + " ".join(args) + "\n")

VALUED = {"-c", "-d", "-h", "-p", "-U", "-f", "-v"}
opts, positional = {}, []
i = 0
while i < len(args):
    a = args[i]
    if a in VALUED and i + 1 < len(args):
        opts[a] = args[i + 1]
        i += 2
        continue
    if not a.startswith("-"):
        positional.append(a)
    i += 1

conn = {"user": opts.get("-U", ""), "password": "", "host": opts.get("-h", ""),
        "port": opts.get("-p", ""), "dbname": opts.get("-d", "")}
target = positional[0] if positional else ""
if len(positional) > 1 and not conn["user"]:
    conn["user"] = positional[1]

KEYWORDS = {"host", "hostaddr", "port", "dbname", "user", "password",
            "sslmode", "connect_timeout", "application_name", "options"}
if target.startswith(("postgresql://", "postgres://")):
    u = urlsplit(target)
    conn["user"] = unquote(u.username or "") or conn["user"]
    conn["password"] = unquote(u.password or "")
    conn["host"] = u.hostname or conn["host"]
    conn["port"] = str(u.port) if u.port else conn["port"]
    conn["dbname"] = unquote(u.path[1:]) if u.path.startswith("/") else ""
elif "=" in target:
    for token in target.split():
        key = token.split("=", 1)[0]
        if "=" not in token or key not in KEYWORDS:
            sys.stderr.write('psql: error: invalid connection option "%s"\n' % key)
            sys.exit(1)
        conn[key] = token.split("=", 1)[1]
elif target:
    conn["dbname"] = target

conn["user"] = conn["user"] or os.environ.get("PGUSER") or os.environ.get("USER", "")
conn["dbname"] = conn["dbname"] or os.environ.get("PGDATABASE") or conn["user"]
log.write("connect " + " ".join("%s=%s" % kv for kv in conn.items()) + "\n")
log.close()

listed = os.environ.get("STUB_EXISTING_DBS")
exists = (conn["dbname"] in listed.split()) if listed is not None else bool(
    re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", conn["dbname"]))
if conn["dbname"] == os.environ.get("STUB_MISSING_DB"):
    exists = False
if not exists:
    sys.stderr.write('psql: error: connection to server at "%s", port %s failed: '
                     'FATAL:  database "%s" does not exist\n'
                     % (conn["host"] or "localhost", conn["port"] or "5432",
                        conn["dbname"]))
    sys.exit(2)
sys.exit(0)
"""

_DOCKER_STUB = r"""#!/bin/bash
# No daemon in a test run; the script must fall through to the local branch.
echo "docker $*" >> "$STUB_LOG"
echo "Cannot connect to the Docker daemon." >&2
exit 1
"""

_ALEMBIC_STUB = r"""#!/bin/bash
echo "alembic $*" >> "$STUB_LOG"
if [ -n "${STUB_ALEMBIC_FAIL:-}" ]; then
    printf '%s\n' "$STUB_ALEMBIC_MESSAGE" >&2
    exit 1
fi
echo "INFO  [alembic.runtime.migration] Will assume transactional DDL."
exit 0
"""

_PYTHON_STUB = r"""#!/bin/bash
# Covers the editable-install probe (`python -c 'import nonogram'`, CARD-139)
# without needing a venv; also catches a `flask run` that should never happen.
echo "python $*" >> "$STUB_LOG"
exit 0
"""

DEFAULT_DB = "nonogram_poc"
STUB_USER = "stub_owner"


@dataclass(frozen=True)
class Run:
    returncode: int
    output: str
    calls: list[str]
    # ``output`` is the two streams concatenated, so it cannot tell the
    # script's own words from a stub's message that merely leaked past the
    # script to the terminal -- and that distinction is the whole of AC-3's
    # message clause (CARD-150, review cycle 1, F-001).  Keep the streams
    # apart as well, so a test that cares can assert on what the script
    # itself printed.
    stdout: str = ""
    stderr: str = ""

    def called(self, program: str) -> list[str]:
        return [c for c in self.calls if c.split(" ", 1)[0] == program]


def run_script(
    tmp_path: Path,
    *args: str,
    database_url: str | None = None,
    missing_db: str | None = None,
    alembic_fails: bool = False,
    alembic_message: str = "",
    existing_dbs: list[str] | None = None,
) -> Run:
    """Run the real script inside a throwaway root, with stubbed tools."""
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts" / SCRIPT.name
    shutil.copyfile(SCRIPT, script)
    script.chmod(0o755)

    # The script sources this and then probes the editable install; a no-op
    # activate is enough, because `python` is stubbed on PATH anyway.
    activate = root / ".venv" / "bin" / "activate"
    activate.parent.mkdir(parents=True)
    activate.write_text(":\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # psql is the Python model above, behind a bash shim: ``python`` itself is
    # stubbed on PATH, so the shim names this interpreter by absolute path.
    model = tmp_path / "psql_model.py"
    model.write_text(_PSQL_MODEL)
    psql_shim = (
        "#!/bin/bash\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(model))} \"$@\"\n"
    )
    for name, body in (
        ("psql", psql_shim),
        ("docker", _DOCKER_STUB),
        ("docker-compose", _DOCKER_STUB),
        ("alembic", _ALEMBIC_STUB),
        ("python", _PYTHON_STUB),
    ):
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)

    log = tmp_path / "calls.log"
    log.write_text("")

    env = {
        k: v
        for k, v in os.environ.items()
        # A DATABASE_URL or PG* inherited from the developer's shell would
        # decide the outcome instead of the test.
        if k != "DATABASE_URL" and not k.startswith("PG")
    }
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["STUB_LOG"] = str(log)
    # The psql model falls back to a database named after the user, as real
    # psql does (CARD-151); pin who "the user" is so the developer's login
    # name cannot decide an outcome.
    env["USER"] = env["LOGNAME"] = STUB_USER
    if existing_dbs is not None:
        env["STUB_EXISTING_DBS"] = " ".join(existing_dbs)
    if missing_db is not None:
        env["STUB_MISSING_DB"] = missing_db
    if alembic_fails:
        env["STUB_ALEMBIC_FAIL"] = "1"
        env["STUB_ALEMBIC_MESSAGE"] = alembic_message
    if database_url is not None:
        env["DATABASE_URL"] = database_url

    completed = subprocess.run(
        ["bash", str(script), *args],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return Run(
        returncode=completed.returncode,
        output=_plain(completed.stdout + completed.stderr),
        calls=[line for line in log.read_text().splitlines() if line.strip()],
        stdout=_plain(completed.stdout),
        stderr=_plain(completed.stderr),
    )


def test_the_harness_reaches_the_end_of_the_script(tmp_path: Path) -> None:
    """Guard on the guard: with everything healthy the run gets to [6/6].

    If this ever fails, the tests below stop proving anything -- they would be
    passing because the script died early for a reason of the harness's own.
    """
    run = run_script(tmp_path, "--check-only")
    assert run.returncode == 0, run.output
    for step in ("[1/6]", "[2/6]", "[3/6]", "[4/6]", "[5/6]", "[6/6]"):
        assert step in run.output, f"{step} missing from:\n{run.output}"
    assert "All checks passed" in run.output
    # --check-only stops short of the one line that never returns.
    assert not [c for c in run.called("python") if "flask" in c], run.calls


class TestStartAdminLocal_RefusesAMissingDatabase:
    """AC-1: the target database is unreachable -> non-zero, named, no panel."""

    def test_exits_non_zero_naming_the_database(self, tmp_path: Path) -> None:
        run = run_script(tmp_path, "--check-only", missing_db=DEFAULT_DB)

        assert run.returncode != 0, run.output
        assert DEFAULT_DB in run.output
        assert "not reachable" in run.output
        assert "✗" in run.output or "not reachable" in run.output

    def test_refuses_before_starting_anything(self, tmp_path: Path) -> None:
        run = run_script(tmp_path, missing_db=DEFAULT_DB)

        assert run.returncode != 0
        # It stops inside step [1/6]: no venv step, no migration, no flask.
        assert "[2/6]" not in run.output
        assert run.called("alembic") == []
        assert [c for c in run.called("python") if "flask" in c] == []

    def test_the_local_branch_checks_the_target_database(
        self, tmp_path: Path
    ) -> None:
        """The defect itself: the local branch used to check another database.

        A bare ``psql -c "SELECT 1"`` connects to the default database (``$USER``)
        and succeeds while the target is absent.  The recorded argument list is
        the only place that distinction shows up, so that is what is asserted:
        every psql the script runs must name the database it is about to use.
        """
        run = run_script(tmp_path, "--check-only")

        psql_calls = run.called("psql")
        assert psql_calls, f"the script ran no psql at all:\n{run.output}"
        for call in psql_calls:
            assert DEFAULT_DB in call, (
                "a psql check that does not name the target database says "
                f"nothing about it: {call!r}"
            )

    def test_a_different_database_is_unaffected(self, tmp_path: Path) -> None:
        """The refusal is about the database in use, not a blanket failure."""
        run = run_script(
            tmp_path,
            "--check-only",
            database_url="postgresql://postgres@localhost:5432/nonogram_elsewhere",
            missing_db=DEFAULT_DB,
        )

        assert run.returncode == 0, run.output
        assert "nonogram_elsewhere" in run.output
        assert "reachable" in run.output


class TestStartAdminLocal_RespectsAnExportedDatabaseUrl:
    """AC-2: an exported DATABASE_URL wins; otherwise the project default."""

    def test_uses_an_exported_url_and_says_so(self, tmp_path: Path) -> None:
        url = "postgresql://someone:secret@localhost:5432/nonogram_dev"
        run = run_script(tmp_path, "--check-only", database_url=url)

        assert run.returncode == 0, run.output
        assert url in run.output
        assert "exported by the caller" in run.output
        # Not merely printed: it is the database that got checked, and the one
        # handed to alembic and to the panel.
        assert run.called("psql")
        for call in run.called("psql"):
            assert "nonogram_dev" in call, call
        assert DEFAULT_DB not in run.output

    def test_falls_back_to_the_project_default(self, tmp_path: Path) -> None:
        run = run_script(tmp_path, "--check-only")

        assert run.returncode == 0, run.output
        assert f"DATABASE_URL={default_database_url(run)}" in run.output
        assert "project default" in run.output
        assert DEFAULT_DB in default_database_url(run)

    def test_an_exported_url_survives_into_the_environment(
        self, tmp_path: Path
    ) -> None:
        """The old hardcoded export overwrote the caller's value at step [4/6]."""
        url = "postgresql://someone@localhost:5432/nonogram_dev"
        run = run_script(tmp_path, "--check-only", database_url=url)

        step4 = run.output.split("[4/6]", 1)[1]
        assert url in step4.split("[5/6]", 1)[0], step4


def default_database_url(run: Run) -> str:
    """The default the script itself reports, rather than one restated here."""
    match = re.search(
        r"DATABASE_URL=(\S+) \(project default\)", run.output
    )
    assert match, f"the script printed no default DATABASE_URL:\n{run.output}"
    return match.group(1)


class TestStartAdminLocal_RefusesAndReportsAFailedMigration:
    """AC-3: a failed ``alembic upgrade head`` stops the script and is shown."""

    MESSAGE = (
        "FAILED: Can't locate revision identified by 'deadbeef'\n"
        "  (the second line matters too)"
    )

    def test_exits_non_zero(self, tmp_path: Path) -> None:
        run = run_script(
            tmp_path,
            "--check-only",
            alembic_fails=True,
            alembic_message=self.MESSAGE,
        )

        assert run.returncode != 0, run.output
        assert "Migrations failed" in run.output
        # It does not go on to the panel.
        assert "[6/6]" not in run.output
        assert [c for c in run.called("python") if "flask" in c] == []

    def test_alembics_own_message_reaches_the_output(
        self, tmp_path: Path
    ) -> None:
        run = run_script(
            tmp_path,
            "--check-only",
            alembic_fails=True,
            alembic_message=self.MESSAGE,
        )

        for line in self.MESSAGE.splitlines():
            assert line.strip() in run.output, (
                f"alembic said {line.strip()!r} and the script threw it away:"
                f"\n{run.output}"
            )
        assert "may have issues" not in run.output

        # The assertions above are also satisfied by alembic's message merely
        # leaking past the script: the stub writes it to stderr, and
        # ``run.output`` is both streams concatenated.  Drop the ``2>&1`` from
        # the script's capture and they still pass, which is the pre-card
        # defect surviving its own test (F-001).  Only the script's own
        # ``sed 's/^/    /'`` can put the message, four-space indented, on the
        # script's *stdout* -- so that is what pins the quoting.
        for line in self.MESSAGE.splitlines():
            assert f"    {line.strip()}" in run.stdout, (
                f"the script did not quote {line.strip()!r} under its own"
                f" 'alembic upgrade head said:'; it only reached the terminal."
                f"\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
            )
        assert "(no output)" not in run.output, (
            "the script captured nothing from alembic -- the message went"
            f" straight to the terminal instead:\nstdout:\n{run.stdout}"
            f"\nstderr:\n{run.stderr}"
        )

    def test_no_migrate_is_the_explicit_way_past_it(
        self, tmp_path: Path
    ) -> None:
        run = run_script(
            tmp_path,
            "--check-only",
            "--no-migrate",
            alembic_fails=True,
            alembic_message=self.MESSAGE,
        )

        assert run.returncode == 0, run.output
        assert run.called("alembic") == []
        assert "Skipping migrations" in run.output

    def test_a_successful_migration_still_continues(
        self, tmp_path: Path
    ) -> None:
        run = run_script(tmp_path, "--check-only")

        assert run.returncode == 0, run.output
        assert "Migrations completed" in run.output
        assert run.called("alembic") == ["alembic upgrade head"]


class TestStartAdminLocal_ReadmeMatchesTheScript:
    """AC-4: scripts/README.md describes what the script actually does.

    Everything asserted here is first read out of a *run* of the script -- the
    default URL it reports, the flags its own --help lists -- so the README is
    checked against behaviour rather than against a second copy of the prose.
    """

    def test_it_names_the_database_the_script_defaults_to(
        self, tmp_path: Path
    ) -> None:
        url = default_database_url(run_script(tmp_path, "--check-only"))
        assert url in README.read_text(), (
            f"the script defaults to {url} and the README does not say so"
        )

    def test_it_documents_every_flag_the_script_accepts(
        self, tmp_path: Path
    ) -> None:
        help_text = run_script(tmp_path, "--help").output
        flags = sorted(set(re.findall(r"(?m)^\s+(--[a-z-]+)\s", help_text)))
        assert "--check-only" in flags and "--no-migrate" in flags, flags

        readme = README.read_text()
        for flag in flags:
            if flag == "--help":
                continue
            assert flag in readme, f"{flag} is undocumented in scripts/README.md"

    def test_it_says_an_exported_database_url_wins(self) -> None:
        readme = README.read_text()
        assert "DATABASE_URL" in readme
        lowered = readme.lower()
        assert "exported" in lowered
        assert "wins" in lowered or "takes precedence" in lowered

    def test_a_claim_about_the_scripts_names_the_script_it_holds_for(
        self,
    ) -> None:
        """Prerequisites governs every script the README documents.

        Only ``start_admin_local.sh`` honours an exported ``DATABASE_URL``;
        ``setup_admin_local.sh`` and ``run_admin_tests.sh`` still
        ``export DATABASE_URL`` over the caller's value.  This suite drives
        none of them -- every other assertion in this class comes from a run
        of ``start_admin_local.sh`` -- so an unqualified precedence claim in
        Prerequisites was invisible to it (CARD-150 review cycle 1, F-002).
        Read the siblings' source instead: a documented script that
        overwrites ``DATABASE_URL`` has to be named where the claim is made.
        Fixing those scripts is a separate card; when one is fixed it drops
        out of this check by itself.
        """
        readme = README.read_text()
        prerequisites = readme.split("## Prerequisites", 1)[1].split("\n## ", 1)[0]
        assert any(
            word in prerequisites.lower() for word in ("wins", "takes precedence")
        ), f"Prerequisites no longer states the precedence:\n{prerequisites}"

        documented = re.findall(r"(?m)^### `([A-Za-z0-9_.-]+\.sh)`", readme)
        assert "start_admin_local.sh" in documented, documented
        for name in documented:
            source = (REPO_ROOT / "scripts" / name).read_text()
            if not re.search(r"(?m)^\s*export\s+DATABASE_URL=", source):
                continue
            assert name in prerequisites, (
                f"{name} exports DATABASE_URL over the caller's value, so the"
                " precedence claim in Prerequisites is not true of every"
                " script documented here and has to say which one it means:"
                f"\n{prerequisites}"
            )

    def test_it_says_a_missing_database_stops_the_script(
        self, tmp_path: Path
    ) -> None:
        run = run_script(tmp_path, "--check-only", missing_db=DEFAULT_DB)
        assert run.returncode != 0, run.output  # the behaviour being documented

        lowered = README.read_text().lower()
        assert "does not exist" in lowered or "unreachable" in lowered
        assert "exits non-zero" in lowered or "stops" in lowered
        # And that it will not quietly fix it for you.
        assert any(
            phrase in lowered
            for phrase in ("does not create", "never create", "will not create")
        ), "the README does not say the script creates no database"

    def test_it_says_a_failed_migration_stops_the_script(
        self, tmp_path: Path
    ) -> None:
        run = run_script(
            tmp_path, "--check-only", alembic_fails=True, alembic_message="boom"
        )
        assert run.returncode != 0, run.output  # the behaviour being documented

        lowered = README.read_text().lower()
        assert "alembic" in lowered
        assert "--no-migrate" in lowered
        assert "exits non-zero" in lowered or "stops" in lowered

    def test_it_no_longer_states_a_database_as_a_bare_prerequisite(
        self, tmp_path: Path
    ) -> None:
        """The stale line: "Database `nonogram_poc` created" under Prerequisites.

        The script creates nothing and now refuses when the database is absent,
        so the prerequisite section has to say which database and that it is
        only the default.
        """
        readme = README.read_text()
        prerequisites = readme.split("## Prerequisites", 1)[1].split("\n## ", 1)[0]
        assert "DATABASE_URL" in prerequisites, prerequisites


# ---------------------------------------------------------------------------
# CARD-151: the check understands the URLs the panel accepts
# ---------------------------------------------------------------------------


def connections(run: Run) -> list[dict[str, str]]:
    """What each psql the script ran would have connected to.

    Read from the psql model's ``connect`` log lines -- its own, independent
    reading of the argument list -- rather than re-parsed here.
    """
    return [
        dict(pair.split("=", 1) for pair in call.split(" ")[1:])
        for call in run.called("connect")
    ]


def _refused_naming_no_database(run: Run) -> None:
    assert run.returncode != 0, run.output
    assert "names no database" in run.stdout, run.output
    assert "✓ PostgreSQL is running" not in run.output, run.output
    assert "reachable" not in run.output.replace("not reachable", ""), run.output
    assert "[2/6]" not in run.output, run.output


class TestStartAdminLocal_AcceptsADriverQualifiedUrl:
    """AC-1: ``postgresql+psycopg2://`` is what the panel builds; the check takes it.

    ``normalized_url`` (CARD-148) puts the driver into every URL the panel
    uses, and leaves an explicitly named one alone.  Real psql takes such a
    string whole as a database name and reports it missing, so the check must
    not hand it over as is.
    """

    URL = "postgresql+psycopg2://someone:secret@localhost:5432/nonogram_dev"

    def test_the_check_succeeds_against_a_reachable_database(
        self, tmp_path: Path
    ) -> None:
        run = run_script(tmp_path, "--check-only", database_url=self.URL)

        assert run.returncode == 0, run.output
        assert "database 'nonogram_dev' reachable" in run.output
        assert "All checks passed" in run.output

    def test_psql_is_handed_a_url_it_parses(self, tmp_path: Path) -> None:
        run = run_script(tmp_path, "--check-only", database_url=self.URL)

        assert connections(run) == [
            {
                "user": "someone",
                "password": "secret",
                "host": "localhost",
                "port": "5432",
                "dbname": "nonogram_dev",
            }
        ], run.calls

    def test_the_panel_still_gets_the_url_as_exported(
        self, tmp_path: Path
    ) -> None:
        """Only psql's copy loses the driver; the panel's keeps it (G-4)."""
        run = run_script(tmp_path, "--check-only", database_url=self.URL)

        step4 = run.output.split("[4/6]", 1)[1].split("[5/6]", 1)[0]
        assert f"DATABASE_URL={self.URL} (exported by the caller)" in step4

    def test_other_drivers_are_accepted_too(self, tmp_path: Path) -> None:
        for i, driver in enumerate(("psycopg", "asyncpg", "pg8000")):
            url = f"postgresql+{driver}://someone@localhost:5432/nonogram_dev"
            run = run_script(tmp_path / str(i), "--check-only", database_url=url)
            assert run.returncode == 0, (driver, run.output)
            assert [c["dbname"] for c in connections(run)] == ["nonogram_dev"]


class TestStartAdminLocal_RefusesAUrlThatNamesNoDatabase:
    """AC-2: a URL with no database is a configuration error, never a green tick.

    Given one, real psql connects to a database named after the user.  Where no
    such database exists the old check failed with "database '' is not
    reachable"; where one does, it printed a green tick naming no database and
    started the panel.  Both cases are driven, by telling the psql model which
    databases exist.
    """

    URL = "postgresql://someone@localhost:5432/"

    def test_refuses_when_a_database_named_after_the_user_exists(
        self, tmp_path: Path
    ) -> None:
        run = run_script(
            tmp_path,
            "--check-only",
            database_url=self.URL,
            existing_dbs=["someone", STUB_USER, "nonogram_dev"],
        )
        _refused_naming_no_database(run)

    def test_refuses_when_no_database_named_after_the_user_exists(
        self, tmp_path: Path
    ) -> None:
        run = run_script(
            tmp_path,
            "--check-only",
            database_url=self.URL,
            existing_dbs=["nonogram_dev"],
        )
        _refused_naming_no_database(run)

    def test_the_message_names_the_url_its_source_and_creates_nothing(
        self, tmp_path: Path
    ) -> None:
        run = run_script(tmp_path, "--check-only", database_url=self.URL)

        assert f"DATABASE_URL={self.URL} (exported by the caller)" in run.stdout
        assert "does not create a database" in run.stdout

    def test_refuses_before_any_psql_runs(self, tmp_path: Path) -> None:
        """psql is never given the chance to substitute a database of its own."""
        run = run_script(tmp_path, "--check-only", database_url=self.URL)

        assert run.called("psql") == [], run.calls
        assert run.called("alembic") == []
        assert [c for c in run.called("python") if "flask" in c] == []


class TestStartAdminLocal_StillChecksTheTargetDatabase:
    """AC-3: what CARD-150 won survives the fix.

    The check still names the database it is about to use and carries the
    URL's host, port and credentials -- including when the URL had a driver
    to strip -- and it still fails when that database is absent.
    """

    PLAIN = "postgresql://someone:secret@db.example:6543/nonogram_dev"
    DRIVER = "postgresql+psycopg2://someone:secret@db.example:6543/nonogram_dev"
    EXPECTED = {
        "user": "someone",
        "password": "secret",
        "host": "db.example",
        "port": "6543",
        "dbname": "nonogram_dev",
    }

    def test_the_check_carries_the_urls_host_port_and_credentials(
        self, tmp_path: Path
    ) -> None:
        for i, url in enumerate((self.PLAIN, self.DRIVER)):
            run = run_script(tmp_path / str(i), "--check-only", database_url=url)

            assert run.returncode == 0, (url, run.output)
            assert connections(run) == [self.EXPECTED], (url, run.calls)
            for call in run.called("psql"):
                assert "nonogram_dev" in call, call

    def test_it_still_fails_when_the_database_is_absent(
        self, tmp_path: Path
    ) -> None:
        for i, url in enumerate((self.PLAIN, self.DRIVER)):
            run = run_script(
                tmp_path / str(i),
                "--check-only",
                database_url=url,
                missing_db="nonogram_dev",
            )

            assert run.returncode != 0, (url, run.output)
            assert "Database 'nonogram_dev' is not reachable" in run.stdout
            assert f"DATABASE_URL={url} (exported by the caller)" in run.stdout
            assert "does not create a database" in run.stdout
            assert "[2/6]" not in run.output


def test_the_decision_over_an_enumerated_corpus_of_url_shapes(
    tmp_path: Path,
) -> None:
    """Every URL shape: refuse when it names no database, else check exactly it.

    The URLs are assembled here from parts, so the expected database, host,
    port and credentials are the parts themselves -- not something re-derived
    with the script's own slicing -- and what psql would have connected to is
    the psql model's independent reading.
    """
    schemes = (
        "postgresql",
        "postgres",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "postgresql+asyncpg",
    )
    credentials = (("", ""), ("someone", ""), ("someone", "s3cret"))
    ports = ("", "6543")
    paths = ("/nonogram_dev", "/", "")
    queries = ("", "?sslmode=require")

    cases = 0
    failures: list[str] = []
    for scheme in schemes:
        for user, password in credentials:
            for port in ports:
                for path in paths:
                    for query in queries:
                        userinfo = (
                            f"{user}:{password}@" if password
                            else f"{user}@" if user
                            else ""
                        )
                        hostport = f"db.example:{port}" if port else "db.example"
                        url = f"{scheme}://{userinfo}{hostport}{path}{query}"
                        dbname = path[1:]
                        run = run_script(
                            tmp_path / f"case{cases}",
                            "--check-only",
                            "--no-migrate",
                            database_url=url,
                        )
                        cases += 1
                        if not dbname:
                            if (
                                run.returncode == 0
                                or "names no database" not in run.stdout
                                or "✓ PostgreSQL is running" in run.output
                                or run.called("psql")
                            ):
                                failures.append(f"{url}: not refused\n{run.output}")
                            continue
                        expected = {
                            "user": user or STUB_USER,
                            "password": password,
                            "host": "db.example",
                            "port": port,
                            "dbname": dbname,
                        }
                        if run.returncode != 0 or connections(run) != [expected]:
                            failures.append(
                                f"{url}: expected a check of {expected},"
                                f" got {connections(run)}\n{run.output}"
                            )

    assert cases >= 180, f"the corpus shrank to {cases} cases"
    assert not failures, f"{len(failures)} of {cases} cases wrong:\n" + "\n".join(
        failures[:5]
    )
