"""CARD-152: a harness for the two sibling admin scripts, and what they share.

``setup_admin_local.sh`` and ``run_admin_tests.sh`` resolve and check
``DATABASE_URL`` exactly the way ``start_admin_local.sh`` does after CARD-150
and CARD-151.  This module drives either of them the way
``tests/test_start_admin_local.py`` drives that one:

* the real script is copied into a throwaway project root (with a no-op
  ``.venv/bin/activate``), because both scripts ``cd`` to the root they are
  run from and source the venv there;
* everything they talk to is a stub earlier on ``PATH`` -- ``psql``,
  ``docker``, ``docker-compose``, ``alembic``, ``pytest`` -- so **no database
  is created, dropped, seeded, migrated or even connected to**, and nothing
  here needs PostgreSQL running (CARD-152 G-2, G-4);
* the environment is stripped of ``DATABASE_URL``/``PG*``/``VIRTUAL_ENV`` and
  ``USER``/``LOGNAME`` are pinned, so the developer's shell cannot decide an
  outcome.

The ``psql`` stub is CARD-151's independent model of how real psql reads its
target (libpq URI + query semantics, built on ``urllib.parse``), imported from
that suite rather than copied, so the three scripts are judged by one model.
It logs a ``connect user= password= host= port= dbname=`` line: what psql
would actually have connected to.

``alembic`` and ``pytest`` -- whichever the script hands the database to --
also log the ``DATABASE_URL`` they were given, which is what "the script did
not overwrite it" means in practice.

The classes at the bottom are contracts: each sibling's test file subclasses
them with its own script, so every URL-handling branch is pinned in both.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

# These four are private names of tests/test_start_admin_local.py, which this
# card must leave unmodified (CARD-152 Touches). Renaming or moving any of them
# there breaks tests/test_setup_admin_local.py and tests/test_run_admin_tests.py
# with an ImportError -- move them here, or to their own tests/helpers/ module,
# when that file is next open.
from tests.test_start_admin_local import (
    _DOCKER_STUB,
    _PSQL_MODEL,
    _all_pairs,
    _plain,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
README = SCRIPTS / "README.md"

DEFAULT_DB = "nonogram_poc"
STUB_USER = "stub_owner"

# Logs its arguments and the DATABASE_URL it was handed; fails on request
# with a message on stderr, as alembic does.
_ALEMBIC_STUB = r"""#!/bin/bash
echo "alembic $*" >> "$STUB_LOG"
echo "alembic-env DATABASE_URL=${DATABASE_URL-<unset>}" >> "$STUB_LOG"
if [ -n "${STUB_ALEMBIC_FAIL:-}" ]; then
    if [ -n "$STUB_ALEMBIC_MESSAGE" ]; then
        printf '%s\n' "$STUB_ALEMBIC_MESSAGE" >&2
    fi
    exit 1
fi
echo "INFO  [alembic.runtime.migration] Will assume transactional DDL."
exit 0
"""

# Stands in for the test run itself: run_admin_tests.sh must never start a
# real suite from inside this one.
_PYTEST_STUB = r"""#!/bin/bash
echo "pytest $*" >> "$STUB_LOG"
echo "pytest-env DATABASE_URL=${DATABASE_URL-<unset>}" >> "$STUB_LOG"
if [ -n "${STUB_PYTEST_FAIL:-}" ]; then
    echo "1 failed" >&2
    exit 1
fi
echo "1 passed"
exit 0
"""


@dataclass(frozen=True)
class Run:
    returncode: int
    output: str  # both streams, colour stripped
    stdout: str  # the script's own words (stubs write their errors to stderr)
    stderr: str
    calls: list[str]

    def called(self, program: str) -> list[str]:
        return [c for c in self.calls if c.split(" ", 1)[0] == program]

    def handed(self, consumer: str) -> list[str]:
        """The DATABASE_URL each run of ``consumer`` (alembic/pytest) saw."""
        prefix = f"{consumer}-env DATABASE_URL="
        return [c[len(prefix):] for c in self.calls if c.startswith(prefix)]


def connections(run: Run) -> list[dict[str, str]]:
    """What each psql the script ran would have connected to (model's reading)."""
    return [
        dict(pair.split("=", 1) for pair in call.split(" ")[1:])
        for call in run.called("connect")
    ]


def run_script(
    script_name: str,
    tmp_path: Path,
    *args: str,
    database_url: str | None = None,
    missing_db: str | None = None,
    existing_dbs: list[str] | None = None,
    alembic_fails: bool = False,
    alembic_message: str = "",
    pytest_fails: bool = False,
    without_psql: bool = False,
) -> Run:
    """Run the real ``scripts/<script_name>`` in a throwaway root, tools stubbed.

    ``without_psql`` leaves psql off ``PATH`` altogether: no stub is written,
    and the developer's ``PATH`` (which may hold a real psql) is replaced by the
    stub directory plus a directory of links to the few programs the scripts
    need before their psql lookup -- ``dirname`` and ``python3``.
    """
    root = tmp_path / "project"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts" / script_name
    shutil.copyfile(SCRIPTS / script_name, script)
    script.chmod(0o755)

    activate = root / ".venv" / "bin" / "activate"
    activate.parent.mkdir(parents=True)
    activate.write_text(":\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    model = tmp_path / "psql_model.py"
    model.write_text(_PSQL_MODEL)
    psql_shim = (
        "#!/bin/bash\n"
        f"exec {shlex.quote(sys.executable)} {shlex.quote(str(model))} \"$@\"\n"
    )
    stubs = [] if without_psql else [("psql", psql_shim)]
    for name, body in (
        *stubs,
        ("docker", _DOCKER_STUB),
        ("docker-compose", _DOCKER_STUB),
        ("alembic", _ALEMBIC_STUB),
        ("pytest", _PYTEST_STUB),
    ):
        stub = bin_dir / name
        stub.write_text(body)
        stub.chmod(0o755)

    log = tmp_path / "calls.log"
    log.write_text("")

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DATABASE_URL", "VIRTUAL_ENV") and not k.startswith("PG")
    }
    if without_psql:
        tools = tmp_path / "tools"
        tools.mkdir()
        for program in ("dirname", "python3"):
            found = shutil.which(program)
            assert found, f"{program} is needed to run the script"
            (tools / program).symlink_to(found)
        env["PATH"] = f"{bin_dir}{os.pathsep}{tools}"
    else:
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["STUB_LOG"] = str(log)
    env["USER"] = env["LOGNAME"] = STUB_USER
    if existing_dbs is not None:
        env["STUB_EXISTING_DBS"] = " ".join(existing_dbs)
    if missing_db is not None:
        env["STUB_MISSING_DB"] = missing_db
    if alembic_fails:
        env["STUB_ALEMBIC_FAIL"] = "1"
        env["STUB_ALEMBIC_MESSAGE"] = alembic_message
    if pytest_fails:
        env["STUB_PYTEST_FAIL"] = "1"
    if database_url is not None:
        env["DATABASE_URL"] = database_url

    bash = shutil.which("bash")
    assert bash, "bash is needed to run the script"
    completed = subprocess.run(
        [bash, str(script), *args],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return Run(
        returncode=completed.returncode,
        output=_plain(completed.stdout + completed.stderr),
        stdout=_plain(completed.stdout),
        stderr=_plain(completed.stderr),
        calls=[line for line in log.read_text().splitlines() if line.strip()],
    )


class _SiblingScript:
    """What a contract needs to know about the script it is applied to."""

    #: ``scripts/<SCRIPT>``.
    SCRIPT: str
    #: The program the script hands DATABASE_URL to (``alembic``/``pytest``).
    CONSUMER: str
    #: Printed only once the database check has passed.
    PAST_THE_CHECK: str
    #: Printed only when the script ran to its end.
    FINISHED: str
    #: The database the script falls back to with nothing exported. The panel's
    #: scripts share ``nonogram_poc``; run_admin_tests.sh overrides it (CARD-168).
    DEFAULT_DB: str = DEFAULT_DB

    def run(self, tmp_path: Path, **kwargs) -> Run:
        return run_script(self.SCRIPT, tmp_path, **kwargs)

    def assert_went_on(self, run: Run, url: str) -> None:
        assert run.returncode == 0, run.output
        assert self.FINISHED in run.stdout, run.output
        assert run.handed(self.CONSUMER) == [url], run.calls

    def assert_stopped_at_the_check(self, run: Run) -> None:
        assert run.returncode != 0, run.output
        assert "✓ PostgreSQL is running" not in run.output, run.output
        assert self.PAST_THE_CHECK not in run.stdout, run.output
        assert self.FINISHED not in run.stdout, run.output
        assert run.called(self.CONSUMER) == [], run.calls
        assert "does not create a database" in run.stdout, run.output


class ExportedDatabaseUrlContract(_SiblingScript):
    """AC-1: an exported DATABASE_URL is the one used, and the script says so."""

    URL = "postgresql://someone:secret@localhost:5432/nonogram_dev"

    def test_an_exported_url_is_used_and_attributed_to_the_caller(
        self, tmp_path: Path
    ) -> None:
        run = self.run(tmp_path, database_url=self.URL)

        self.assert_went_on(run, self.URL)
        assert f"DATABASE_URL={self.URL} (exported by the caller)" in run.stdout
        assert "project default" not in run.stdout
        assert self.DEFAULT_DB not in run.output
        assert [c["dbname"] for c in connections(run)] == ["nonogram_dev"]

    def test_with_nothing_exported_it_says_it_used_the_project_default(
        self, tmp_path: Path
    ) -> None:
        run = self.run(tmp_path)

        assert run.returncode == 0, run.output
        assert "(project default)" in run.stdout
        assert "exported by the caller" not in run.stdout
        [handed] = run.handed(self.CONSUMER)
        assert f"DATABASE_URL={handed} (project default)" in run.stdout
        assert handed.endswith(f"/{self.DEFAULT_DB}"), handed
        assert [c["dbname"] for c in connections(run)] == [self.DEFAULT_DB]

    def test_a_driver_qualified_url_reaches_the_consumer_as_exported(
        self, tmp_path: Path
    ) -> None:
        url = "postgresql+psycopg2://someone@localhost:5432/nonogram_dev"
        run = self.run(tmp_path, database_url=url)

        self.assert_went_on(run, url)
        assert f"DATABASE_URL={url} (exported by the caller)" in run.stdout


class DatabaseCheckContract(_SiblingScript):
    """Every URL-handling branch of the check, pinned for this script.

    Each test names the one-character slip in the script it exists to catch.
    """

    def test_the_check_targets_the_urls_database_on_every_branch(
        self, tmp_path: Path
    ) -> None:
        # Catches: a bare ``psql -c`` on the local branch, or a Docker branch
        # still hardcoding nonogram_poc.
        url = "postgresql://someone@localhost:5432/nonogram_dev"
        run = self.run(tmp_path, database_url=url)

        self.assert_went_on(run, url)
        assert "database 'nonogram_dev' reachable (Homebrew)" in run.stdout
        docker = run.called("docker") + run.called("docker-compose")
        assert len(docker) == 2, run.calls
        for call in docker:
            assert "-d nonogram_dev -c SELECT 1" in call, call
        assert [c["dbname"] for c in connections(run)] == ["nonogram_dev"]

    def test_an_absent_database_is_refused_while_the_servers_default_answers(
        self, tmp_path: Path
    ) -> None:
        # Catches: any check that connects somewhere other than the target.
        url = "postgresql://someone@localhost:5432/nonogram_dev"
        run = self.run(
            tmp_path, database_url=url, existing_dbs=["someone", STUB_USER, "postgres"]
        )

        self.assert_stopped_at_the_check(run)
        assert "Database 'nonogram_dev' is not reachable" in run.stdout
        assert f"DATABASE_URL={url} (exported by the caller)" in run.stdout
        assert [c["dbname"] for c in connections(run)] == ["nonogram_dev"]

    def test_a_driver_is_stripped_for_psql_only(self, tmp_path: Path) -> None:
        # Catches: handing psql DATABASE_URL as is (it would take the whole
        # string as a database name) or stripping more than the +driver.
        for i, driver in enumerate(("psycopg2", "psycopg", "asyncpg")):
            url = f"postgresql+{driver}://someone:secret@db.example:6543/nonogram_dev"
            run = self.run(tmp_path / str(i), database_url=url)

            self.assert_went_on(run, url)
            assert connections(run) == [
                {
                    "user": "someone",
                    "password": "secret",
                    "host": "db.example",
                    "port": "6543",
                    "dbname": "nonogram_dev",
                }
            ], (driver, run.calls)
            [psql] = run.called("psql")
            assert psql.startswith("psql postgresql://someone:secret@"), psql

    def test_the_check_carries_the_urls_query(self, tmp_path: Path) -> None:
        # Catches: cutting the query off psql's copy of the URL.
        url = (
            "postgresql+psycopg2://someone:secret@localhost:5432/nonogram_dev"
            "?host=db.example&port=6543&sslmode=require"
        )
        run = self.run(tmp_path, database_url=url)

        self.assert_went_on(run, url)
        assert connections(run) == [
            {
                "user": "someone",
                "password": "secret",
                "host": "db.example",
                "port": "6543",
                "dbname": "nonogram_dev",
                "sslmode": "require",
            }
        ], run.calls
        assert "database 'nonogram_dev' reachable" in run.stdout

    def test_a_dbname_in_the_query_overrides_the_path(self, tmp_path: Path) -> None:
        # Catches: ignoring ?dbname= (the path's database would be named while
        # psql checks another one).
        url = "postgresql://someone@localhost:5432/nonogram_dev?dbname=nonogram_other"
        run = self.run(tmp_path, database_url=url, existing_dbs=["nonogram_other"])

        self.assert_went_on(run, url)
        assert "database 'nonogram_other' reachable" in run.stdout, run.output
        assert [c["dbname"] for c in connections(run)] == ["nonogram_other"]
        for call in run.called("docker") + run.called("docker-compose"):
            assert "-d nonogram_other " in call, call

    def test_a_url_naming_its_database_only_in_the_query_is_accepted(
        self, tmp_path: Path
    ) -> None:
        # Catches: deciding "names no database" from the path alone.
        url = "postgresql://someone@localhost:5432?dbname=nonogram_dev"
        run = self.run(tmp_path, database_url=url)

        self.assert_went_on(run, url)
        assert "database 'nonogram_dev' reachable" in run.stdout

    def test_an_empty_dbname_in_the_query_names_no_database(
        self, tmp_path: Path
    ) -> None:
        # Catches: ``[^&]+`` for ``[^&]*`` -- an empty ?dbname= ignored, so the
        # path's nonogram_dev is named while libpq connects to ``someone``.
        # nonogram_dev is absent and ``someone`` present: a regression here is
        # a green tick, not an error.
        for i, url in enumerate(
            (
                "postgresql://someone@localhost:5432/nonogram_dev?dbname=",
                "postgresql://someone@localhost:5432/?dbname=",
            )
        ):
            run = self.run(
                tmp_path / str(i), database_url=url, existing_dbs=["someone", STUB_USER]
            )

            self.assert_stopped_at_the_check(run)
            assert "DATABASE_URL names no database" in run.stdout, (url, run.output)
            assert run.called("psql") == [], (url, run.calls)

    def test_the_last_dbname_in_the_query_wins(self, tmp_path: Path) -> None:
        # Catches: taking the first ?dbname= (libpq keeps the last).
        url = (
            "postgresql://someone@localhost:5432/nonogram_dev"
            "?dbname=nonogram_first&dbname=nonogram_other"
        )
        run = self.run(tmp_path, database_url=url, existing_dbs=["nonogram_other"])

        self.assert_went_on(run, url)
        assert "database 'nonogram_other' reachable" in run.stdout, run.output
        assert [c["dbname"] for c in connections(run)] == ["nonogram_other"]
        assert "nonogram_first" not in run.stdout.replace(url, ""), run.output

    def test_a_url_that_names_no_database_is_refused_before_psql(
        self, tmp_path: Path
    ) -> None:
        # Catches: dropping the empty-name refusal (psql would substitute a
        # database named after the user, which exists here).
        for i, url in enumerate(
            (
                "postgresql://someone@localhost:5432/",
                "postgresql://someone@localhost:5432",
                "postgresql+psycopg2://someone@localhost:5432/",
            )
        ):
            run = self.run(
                tmp_path / str(i), database_url=url, existing_dbs=["someone", STUB_USER]
            )

            self.assert_stopped_at_the_check(run)
            assert "DATABASE_URL names no database" in run.stdout, (url, run.output)
            assert f"DATABASE_URL={url} (exported by the caller)" in run.stdout
            assert run.called("psql") == [] and run.called("docker") == [], run.calls

    def test_a_value_that_is_not_a_url_is_refused_under_its_own_message(
        self, tmp_path: Path
    ) -> None:
        # Catches: dropping the ``*://*`` test (the value would be refused for
        # the wrong reason, or sliced into a psql target).
        for i, value in enumerate(
            ("nonogram_dev", "localhost/nonogram_dev", "host=/tmp dbname=nonogram_dev")
        ):
            run = self.run(tmp_path / str(i), database_url=value)

            self.assert_stopped_at_the_check(run)
            assert "DATABASE_URL is not a URL" in run.stdout, (value, run.output)
            assert "names no database" not in run.stdout, (value, run.output)
            assert f"DATABASE_URL={value} (exported by the caller)" in run.stdout
            assert run.called("psql") == [], (value, run.calls)

    def test_the_decision_over_a_pairwise_corpus_of_url_shapes(
        self, tmp_path: Path
    ) -> None:
        """Refuse a URL naming no database; otherwise check exactly the one named.

        The URLs are assembled from parts, so the expected connection *is* the
        parts, not something re-derived with the script's own slicing.
        """
        schemes = ("postgresql", "postgres", "postgresql+psycopg2", "postgresql+asyncpg")
        credentials = (("", ""), ("someone", ""), ("someone", "s3cret"))
        ports = ("", "6543")
        paths = ("/nonogram_dev", "/", "")
        queries = (
            ("", {}),
            ("?sslmode=require", {"sslmode": "require"}),
            ("?host=other.example&port=7654", {"host": "other.example", "port": "7654"}),
            ("?dbname=nonogram_other&user=qowner", {"dbname": "nonogram_other", "user": "qowner"}),
            ("?dbname=", {"dbname": ""}),
        )
        dimensions = [schemes, credentials, ports, paths, queries]
        shapes = _all_pairs(dimensions)
        covered = {
            (i, dimensions[i].index(s[i]), j, dimensions[j].index(s[j]))
            for s in shapes
            for i, j in combinations(range(len(dimensions)), 2)
        }
        assert len(covered) == sum(
            len(dimensions[i]) * len(dimensions[j])
            for i, j in combinations(range(len(dimensions)), 2)
        )

        cases, failures = 0, []
        for scheme, (user, password), port, path, (query, keywords) in shapes:
            userinfo = f"{user}:{password}@" if password else f"{user}@" if user else ""
            hostport = f"db.example:{port}" if port else "db.example"
            url = f"{scheme}://{userinfo}{hostport}{path}{query}"
            expected = {
                "user": user,
                "password": password,
                "host": "db.example",
                "port": port,
                "dbname": path[1:],
                **keywords,
            }
            expected["user"] = expected["user"] or STUB_USER
            run = self.run(tmp_path / f"case{cases}", database_url=url)
            cases += 1
            if not expected["dbname"]:
                if (
                    run.returncode == 0
                    or "names no database" not in run.stdout
                    or run.called("psql")
                ):
                    failures.append(f"{url}: not refused\n{run.output}")
            elif (
                run.returncode != 0
                or connections(run) != [expected]
                or f"database '{expected['dbname']}' reachable" not in run.stdout
                or run.handed(self.CONSUMER) != [url]
            ):
                failures.append(
                    f"{url}: expected {expected}, got {connections(run)}\n{run.output}"
                )

        assert cases >= 20, f"the corpus shrank to {cases} cases"
        assert not failures, f"{len(failures)} of {cases} wrong:\n" + "\n".join(
            failures[:5]
        )
