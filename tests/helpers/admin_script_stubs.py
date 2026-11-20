"""The stub programs and helpers the three admin-script suites share.

``tests/test_start_admin_local.py`` (CARD-150, CARD-151) built these, and
``tests/helpers/admin_scripts.py`` (CARD-152, the two sibling scripts' harness)
imported them from that test file by their private names, so renaming one there
broke the other two suites (CARD-152 F-005). They live here now, under public
names, and both import them from this module (CARD-492, IDEA-038); moved
verbatim apart from the names.

* :data:`PSQL_MODEL` / :data:`PSQL_SHIM` -- CARD-151's model of how real psql
  reads its target, behind a bash shim, so the three scripts are judged by one
  model;
* :data:`DOCKER_STUB` -- a docker with no daemon;
* :func:`tool_dir` -- a directory of stub programs, built once per process per
  stub set (CARD-236);
* :func:`plain` -- the scripts' coloured output with the colour codes dropped;
* :func:`all_pairs` -- a greedy pairwise covering array, for the URL-shape
  corpora.
"""

from __future__ import annotations

import atexit
import re
import shlex
import shutil
import sys
import tempfile
from functools import cache
from itertools import combinations, product
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
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
#   harness pins both, so the developer's own name cannot decide a test);
# * a URI's ``?query`` carries connection keywords too (host, port, user,
#   dbname, sslmode, ...), and each overrides the URI part it names -- the
#   documented libpq URI semantics, cross-checked offline against libpq's own
#   parser in CARD-151's review.
#
# Which databases "exist": every identifier-shaped name except STUB_MISSING_DB,
# or -- when STUB_EXISTING_DBS is set -- only the names it lists.  No server has
# a database called "postgresql+psycopg2://...".
#
# Written in Python with urllib.parse on purpose: the script under test is bash,
# and an independent second parser is what makes the cross-check worth having.
# Besides the raw ``psql ...`` line it logs a ``connect ...`` line -- what this
# psql would actually have connected to -- so a test can assert on the database,
# host, port, credentials and any query-given keyword the check carried.
PSQL_MODEL = r"""
import os
import re
import sys
from urllib.parse import parse_qsl, unquote, urlsplit

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
    # libpq reads connection keywords from the query too, and they override
    # the URI's own parts: ``?host=`` names the server, ``?dbname=`` the
    # database (CARD-151 review cycle 1, F-001).  An unknown key is an error.
    for key, value in parse_qsl(u.query, keep_blank_values=True):
        if key not in KEYWORDS:
            sys.stderr.write('psql: error: invalid URI query parameter: "%s"\n' % key)
            sys.exit(1)
        conn[key] = value
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

DOCKER_STUB = r"""#!/bin/bash
# No daemon in a test run; the script must fall through to the local branch.
echo "docker $*" >> "$STUB_LOG"
echo "Cannot connect to the Docker daemon." >&2
exit 1
"""

# psql is the Python model above, behind a bash shim. ``python`` itself is
# stubbed on PATH, so the shim names this interpreter by absolute path; the
# model's own path is filled in by :func:`tool_dir`, which is what decides
# where the pair lives.
MODEL_PATH = "@PSQL_MODEL@"
PSQL_SHIM = (
    "#!/bin/bash\n"
    f"exec {shlex.quote(sys.executable)} {MODEL_PATH} \"$@\"\n"
)

@cache
def tool_dir(stubs: tuple[tuple[str, str], ...]) -> Path:
    """A directory of stub programs, built **once per process** per stub set.

    CARD-236, and the only change that card makes to how the trio's 83 tests
    run: this used to be built inside each test's own ``tmp_path``, so every
    run of a script executed five never-before-seen executables. On this host that is what the suite
    was paying for -- and it is not the price of spawning a process. Measured
    (``meta/profiling/card-236-admin-local-subprocess-cost.md``):

    * one ``--check-only`` run of ``start_admin_local.sh`` with freshly
      written stubs: **1.10--1.38 s**;
    * the same run against a stub directory a previous run had already
      executed: **0.07--0.12 s**;
    * writing the five files at all: **0.003--0.006 s**, so the cost is in
      ``execve`` and not in the build.

    The host runs Microsoft Defender with real-time protection
    (``wdavdaemon privileged``), which scans an executable synchronously the
    first time it is run; the trio burned 11 s of CPU across 118 s of wall
    clock, i.e. it was blocked, not computing. Keying the cache on the stub
    *bodies* means a different stub set (the siblings' ``pytest`` in place of
    ``python``, or psql left off PATH altogether) gets its own directory
    automatically, so no test silently acquires a tool it was written without.

    What this deliberately does **not** share is the throwaway project root:
    the script, the no-op ``.venv/bin/activate`` and the call log stay inside
    each test's ``tmp_path``, so every test still copies and executes the real
    script and still reads back only its own calls. Nothing stopped executing.

    The stubs hold no state between runs -- they are told what to do through
    the environment (``STUB_LOG``, ``STUB_EXISTING_DBS``, ``STUB_MISSING_DB``,
    ``STUB_ALEMBIC_FAIL``, ``STUB_PYTEST_FAIL``) and append to the log named
    there -- which is what makes one copy safe to share.
    """
    directory = Path(tempfile.mkdtemp(prefix="admin-script-stubs-"))
    atexit.register(shutil.rmtree, directory, ignore_errors=True)
    model = directory / "psql_model.py"
    model.write_text(PSQL_MODEL)
    for name, body in stubs:
        stub = directory / name
        stub.write_text(body.replace(MODEL_PATH, shlex.quote(str(model))))
        stub.chmod(0o755)
    return directory


def all_pairs(dimensions: list[tuple]) -> list[tuple]:
    """A greedy pairwise covering array over ``dimensions``.

    Rows are drawn from the full product until every pair of values of every
    two dimensions appears in some row.  Deterministic: ``max`` keeps the first
    best row, and the product is enumerated in a fixed order.
    """
    indices = [range(len(d)) for d in dimensions]

    def pairs(row: tuple[int, ...]) -> set:
        return {
            ((i, row[i]), (j, row[j]))
            for i, j in combinations(range(len(row)), 2)
        }

    uncovered = set().union(*(pairs(r) for r in product(*indices)))
    candidates = list(product(*indices))
    rows: list[tuple[int, ...]] = []
    while uncovered:
        best = max(candidates, key=lambda r: len(pairs(r) & uncovered))
        rows.append(best)
        uncovered -= pairs(best)
    return [tuple(d[k] for d, k in zip(dimensions, row)) for row in rows]
