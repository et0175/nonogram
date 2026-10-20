# Admin Panel Test Suite - Wave 1

Comprehensive tests for Wave 1 features: batch history, puzzle preview, bulk operations.

## Test Files

### Feature Tests

- **test_batch_history.py** — Batch history tracking and retrieval
  - Batch metadata storage
  - Batch list and filtering
  - Batch detail pages
  - Batch retry functionality

- **test_puzzle_preview.py** — Puzzle preview modal data
  - Preview data availability (grid, clues)
  - Grid rendering for all sizes (10×10 to 30×30)
  - Clue formatting
  - Preview API endpoints

- **test_bulk_operations.py** — Bulk approve/reject operations
  - Bulk approve single and multiple puzzles
  - Bulk reject single and multiple puzzles
  - Bulk operations with filters applied
  - Validation and idempotency

### End-to-End Tests

- **test_wave1_e2e.py** — Complete workflows combining all Wave 1 features
  - Batch generation → history verification
  - Puzzle preview before approval
  - Bulk operations on filtered puzzles
  - Complete workflow integration test

## Running Tests

### All Wave 1 Tests

```bash
pytest tests/test_batch_history.py tests/test_puzzle_preview.py tests/test_bulk_operations.py tests/test_wave1_e2e.py -v
```

### By Category

**Unit Tests Only** (fast, no database):
```bash
pytest -m unit -v
```

**Integration Tests** (uses database):
```bash
pytest -m integration -v
```

**E2E Tests** (full workflows):
```bash
pytest -m e2e -v
```

**Smoke Tests** (quick sanity checks):
```bash
pytest -m smoke -v
```

**Performance Tests**:
```bash
pytest -m performance -v
```

### Specific Test File

```bash
pytest tests/test_batch_history.py -v
pytest tests/test_puzzle_preview.py -v
pytest tests/test_bulk_operations.py -v
pytest tests/test_wave1_e2e.py -v
```

### Specific Test Class

```bash
pytest tests/test_batch_history.py::TestBatchHistoryStorage -v
pytest tests/test_bulk_operations.py::TestBulkApprove -v
```

### Specific Test

```bash
pytest tests/test_batch_history.py::TestBatchHistoryStorage::test_batch_stored_with_metadata -v
```

### With Coverage

```bash
pytest --cov=src/nonogram/admin --cov-report=html tests/

# Open htmlcov/index.html in browser
```

### Slow Tests (warnings)

Tests marked `@pytest.mark.slow` take longer than 5 seconds:

```bash
pytest -m slow -v    # Run only slow tests
pytest -m "not slow" -v  # Skip slow tests
```

## Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.unit` — Unit tests (isolated, fast)
- `@pytest.mark.integration` — Integration tests (use database)
- `@pytest.mark.e2e` — End-to-end tests (full workflows)
- `@pytest.mark.smoke` — Smoke tests (quick sanity checks)
- `@pytest.mark.slow` — Slow tests (>5 seconds)
- `@pytest.mark.performance` — Performance benchmarks

## Fixtures

Available fixtures (from `conftest.py`):

- `db_session` — `SessionLocal` factory bound to an empty, fully migrated test database (`TEST_DATABASE_URL`; when unset, **a name derived from this repo root** — see below). The schema is rebuilt once per session (`DROP SCHEMA public CASCADE`, then `alembic upgrade head`) and every table is truncated before each test. The database is created if it does not exist. Refuses — as a failure, before connecting — any URL whose database name does not end in `_test` or that overrides it with a `dbname`/`database` query parameter. Skips when the database is unreachable (one cached probe per run).
- `app` — Flask test app (depends on `db_session`)

#### One test database per worktree (CARD-244)

The fixtures above **erase** the database they are given. Until CARD-244 every
pytest process on the machine was given the same one, `nonogram_test`, so two
cards running at once destroyed each other's data rather than merely contending
for it — measured in wave 44 as two failures in `test_book_trim_persistence`
that are 200 passed in isolation, and as a 48-test "regression" in a build gate
that never existed.

So with `TEST_DATABASE_URL` unset the name is derived from the resolved repo
root:

    nonogram_<tree>_<12 hex of sha256(root)>_test

for example `nonogram_pythonproject4_543f9f3f05e1_test` (41 bytes) for the
repo and `nonogram_pythonproject4_card_244_d541cdce17d1_test` (50 bytes) for a
worktree beside it. The slug is trimmed so the name never exceeds Postgres's
63-byte limit — which Postgres silently *truncates* rather than refuses, and a
truncation collision would put the shared-database bug straight back. The
digest is taken over the whole path, so two deep trees whose names truncate
alike still differ.

The database is created on first use, through the `postgres` maintenance
database, and migrated to head by the usual session fixture. Nothing has to be
set up by hand.

An exported `TEST_DATABASE_URL` is used **verbatim** and no name is derived, so
CI, `scripts/run_admin_tests.sh` and a hand-run with one exported all behave
exactly as before. `run_admin_tests.sh` now sets it to the `DATABASE_URL` it
checked, so the database it reports is the database the fixtures erase.

The names end in `_test` on purpose: that is the one thing
`_refuse_unless_test_database` requires, so deriving a name needed no change to
the guard that keeps `DROP SCHEMA` away from the panel's `nonogram_poc`.

- `client` — Flask test client
- `puzzle_review_service` — Puzzle review service
- `batch_generator_service` — Batch generator service
- `generator` — Nonogram generator
- `sample_puzzle` — Single generated puzzle
- `sample_puzzles` — 10 generated puzzles
- `cleanup_puzzles` — Cleanup fixture

## Continuous Integration

To run in CI/CD:

```bash
# Install test dependencies
pip install -e '.[dev]'

# Run all tests with coverage
pytest --cov=src/nonogram/admin --cov-report=xml tests/

# Exit with failure if coverage < 80%
pytest --cov=src/nonogram/admin --cov-fail-under=80 tests/
```

## Writing New Tests

When adding tests for new features:

1. Create test file: `tests/test_feature_name.py`
2. Use fixtures from `conftest.py`
3. Mark tests with appropriate markers (`@pytest.mark.unit`, etc.)
4. Include docstrings explaining what's being tested
5. Follow naming convention: `test_<what_is_being_tested>`

Example:

```python
"""Tests for my new feature."""

import pytest


class TestMyFeature:
    """Test my new feature."""

    @pytest.mark.unit
    def test_feature_does_something(self, fixture_name):
        """Test that feature does something specific."""
        result = fixture_name.do_something()
        assert result is True
```

## Debugging Tests

### Verbose Output

```bash
pytest -vv tests/test_batch_history.py
```

### Print Debug Info

```python
def test_something(puzzle_review_service):
    result = puzzle_review_service.get_stats()
    print("Stats:", result)  # Will print during test
    assert result['total'] > 0
```

Run with: `pytest -s tests/` (captures output)

### Stop on First Failure

```bash
pytest -x tests/  # Stop on first failure
pytest -x -vv tests/  # Verbose + stop first
```

### Run Only Failed Tests

```bash
pytest --lf tests/  # Run last failed
pytest --ff tests/  # Run failed first
```

## Performance Baselines

Update performance table in `docs/ADMIN_FINDINGS.md`:

```bash
# Time a specific test
time pytest tests/test_wave1_e2e.py::TestCompleteWorkflowWave1::test_complete_wave1_workflow -v

# Run with timing
pytest --durations=10 tests/test_wave1_e2e.py
```

## Re-measuring the whole suite (profiling runs)

> The rest of this file predates wave 20 and describes the admin-panel tests
> only. This section is current and covers the **whole** suite.

The suite's cost per test roughly doubled over waves 30–38 (68 ms/test →
133–159 ms/test). CARD-217 profiled it once and committed the result so that
nobody re-derives it by hand. Re-measure when you want to check that trend, or
after any card that claims to have made the suite faster.

### The command

```bash
./.venv/bin/python -m pytest --durations=0 --durations-min=0 -q
```

`--durations=0` asks for every test instead of the slowest N. `--durations-min=0`
is the part people forget: without it pytest still hides everything faster
than 5 ms, and with ~7 000 tests the hidden tail is large enough to distort
every per-file share. Both are stock pytest — **do not** add `pytest-xdist`,
`pytest-testmon` or a profiling plugin for this (ADR-0006/R1 keeps the
dependency baseline closed; a dev-extra addition is its own decision).

pytest reports `setup`, `call` and `teardown` as separate lines per test. Keep
all three: a test whose *setup* dominates is a fixture problem, and a test
whose *call* dominates is a test problem. They are not fixed the same way.

### It must be the only suite on the host

This is the part that invalidates the measurement when skipped. Concurrent
runs inflate every number — wave 37 has two cards whose suites overlapped and
whose timings are therefore unusable, and wave 38 saw a shared host add six
minutes to a gate and fail a test on a timing bound it would otherwise have
met. Even two quiet-host runs of near-identical suites a few hours apart
differ by ~19 %, so a contended run tells you nothing at all.

Before starting, and again when it finishes:

```bash
ps -Ao pid,command | grep -E "[p]ytest"     # must print nothing
ls meta/kanban/.full-suite.lock             # must not exist
```

Take the lock for the duration so a concurrent `cmd-start-review` backs off,
and remove it when done. **The lock is enforced** since CARD-255: a pytest run
started in any *other* worktree while this file exists refuses to start, so the
file has to say which worktree holds it, as an **absolute** path. A lock
written without a `worktree:` line — or with a relative one, `worktree: .` —
names no tree the guard can resolve, and refuses every run on the host,
including yours. `$PWD` below is absolute, which is why it is spelled that way.

```bash
LOCK=/Users/omelnikova/PycharmProjects/PythonProject4/meta/kanban/.full-suite.lock
{ echo "holder: profiling run"
  echo "at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "worktree: $PWD"
  echo "commit: $(git rev-parse --short HEAD)"; } > "$LOCK"
trap 'rm -f "$LOCK"' EXIT   # armed here, where the lock is yours: a Ctrl-C
                            # would otherwise leave it for 6h
# ... run the suite ...
rm -f "$LOCK"; trap - EXIT  # and disarmed here, in the same breath
```

The `trap` is the difference between an interrupted profile and a board that
refuses every run for the next six hours. **Disarm it with the lock.** An
`EXIT` trap at top level is armed until the *shell* exits, not until the
profile ends — so a trap left armed in an open terminal deletes whatever is at
that path whenever you later close the window, and by then the lock there may
be a live gate's. `rm -f` on a path this shell no longer owns is the silent
direction this guard exists to close, reached through the handling for the
loud one. (A `( ... )` subshell around the three steps does the same job if
you would rather not think about it.)

The gate scripts have the same `rm -f` shape and no trap of their own; they
live outside this repo and are nobody's to edit here, so an aborted *gate*
still leaves its lock behind and the override (below) is the way past it.

The path is the **main** checkout's, whichever worktree you run in: every gate
script writes that one file, and `tests/full_suite_lock.py` reads that one file
(see its module docstring for the staleness rule and
`NONOGRAM_IGNORE_FULL_SUITE_LOCK`, the override that walks past a lock whose
holder is gone and announces that it did).

The guard's other switch, `NONOGRAM_FULL_SUITE_LOCK`, points it at a different
file. It exists so the guard's own tests never create or delete the board's
real lock, and it is not a thing to reach for by hand: a path holding no lock
makes every verdict "no lock, go ahead". Since CARD-256 a run that sets it says
which file it read and which one it did not, in the terminal summary — it
changes this guard's verdict, so it may not change it quietly. Neither switch
may be set by anything *in* the tree: one `export` in a pytest wrapper would
decide it for every run through that wrapper, and
`test_nothing_in_the_tree_sets_either_of_the_guards_env_switches` greps the
whole tracked tree for both names (this file is one of the three allowed to
name them, which is why they are spelled out here).

If anything else was running, **wait and re-run**. Do not record the number.
An artefact that cannot honestly say `solo run: yes` is not a profile.

### Where the artefacts live

```
meta/profiling/suite-durations-<YYYYMMDD>.txt   raw --durations output + header
meta/profiling/rank_durations.py                the derivation (committed)
meta/profiling/suite-hotspots-<YYYYMMDD>.md     the rankings and the conclusion
```

Naming convention: `<YYYYMMDD>`, the UTC date of the run, on both the durations
file and the hotspots file, so a profile and its analysis always pair by name.

That convention allows one profile per date, and `tests/test_suite_profile.py`
holds it to that: it pairs every `suite-durations-*.txt` with its hotspots
document by name and requires the date to be eight digits. A card that
re-profiles the suite on the same day as an existing profile — CARD-235 did,
measuring its own saving against CARD-217's run — therefore names its artefact
after itself (`meta/profiling/card-235-durations-after.txt` and
`card-235-browser-teardown.md`) rather than taking the date name twice. Such a
pair sits outside that harness, so the card carries the equivalent checks
itself: CARD-235's are in `tests/test_browser_fixture_scope.py`, and they call
the same `rank_durations.py` rather than restating any figure of their own.

The `.txt` carries a `#`-comment header before the table stating the commit
sha, the host, the Python version, the exact command, the wall clock, the
pass/skip counts and `solo run: yes`. `tests/test_suite_profile.py` enforces
those fields, so an artefact missing one fails the suite rather than quietly
becoming the record.

### Deriving the rankings

Never hand-count them:

```bash
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/suite-durations-<YYYYMMDD>.txt > /tmp/rankings.txt
```

It prints the 50 slowest tests (split by phase), the 20 slowest files with
their share of attributed time, and the render-heavy files' total share. Its
stdout is a pure function of the artefact's bytes, so re-running it reproduces
the committed document exactly; paste the output into the hotspots file rather
than retyping any figure.

The render-heavy file set is frozen as a constant in that script, with the
`grep` that produced it recorded alongside. To check it against the current
tree:

```bash
./.venv/bin/python meta/profiling/rank_durations.py \
    meta/profiling/suite-durations-<YYYYMMDD>.txt --verify-render-set tests >/dev/null
```

Drift is reported on stderr; stdout is unaffected, so this cannot change a
committed ranking.

### Logging the run

Append one line to `meta/kanban/suite-timing.log` in the existing format:

```
2026-10-15T05:34:34Z wave-39 card-217-profiling-run 931s PASS (7073 passed, 9 skipped, 0 failed) [131ms/test]
```

A note **after** the rate bracket is legal too, and has been in use since
wave 38 — but only inside parentheses, which is the form the parser gives a
field of its own (`extra`):

```
2026-10-14T19:20:17Z wave-38 card-212-merge-gate 1123s PASS (7053 passed, 9 skipped, 0 failed) [159ms/test] (a first attempt on a shared host failed at 1476s)
```

A **bare** trailing note — the same sentence without the parentheses — is
**not** legal and does not parse at all: CARD-217's merge-gate line wrote one
(`… [135ms/test] — the profiling card's own gate; …`) and it is the malformed
line CARD-238 was cut from. Prose lives inside parentheses; nothing but a
parenthesised note may follow the rate bracket. This paragraph is the one
place in this repository that says so, and it was missing until CARD-239 —
`skills/kanban/references/cmd-run.md`, which is what the dispatcher actually
reads at a merge gate, lives outside this repository and still documents only
the bracket-terminated form.

That log is gitignored (`.gitignore`'s blanket `*.log`), so it is **not**
committed and a fresh checkout will not have one — append to it anyway; it is
the only place the cost trend is kept across waves. Its line format is pinned
by `TIMING_LOG_LINE` in `rank_durations.py` and tested, so keep to it. **No
test reads the live log** (CARD-238): the format is asserted against entries
the tests construct, and the one thing that reads the real file is a
subcommand somebody runs on purpose, over a path they name:

```bash
./.venv/bin/python meta/profiling/rank_durations.py --check-log meta/kanban/suite-timing.log
```

It reports the lines the entry contract rejects and how many of the lines
carrying a rate bracket actually give their rate back, exits 1 if either
count is wrong, and never writes.

## Measuring which assertions a mutant kills (`kill_matrix.py`)

`tests/kill_matrix.py` reports, for one target test file and a set of mutants,
**every** `ast.Assert` node in that file as `PASS` / `FAIL` / `NOT-REACHED` /
`BLIND`, keyed on each node's own `lineno`. Its tests are
`tests/test_kill_matrix.py`.

Why it exists at all: a test short-circuits at its first failing assert, so one
`FAILED` line says nothing about the arms that never ran — **a surviving mutant
and a never-reached assert look identical** in a test-level reading. This board
rebuilt that instrument five times in one wave and each build hit a *different*
way it lies. Those six ways are its acceptance criteria, each with a control
that fails.

### Two passes, and a figure must say which one it came from

Both are the same transformer with one difference: whether its handler
re-raises.

| pass | what it buys | what it costs |
| --- | --- | --- |
| `Pass.RECORDING` | per-arm attribution — every arm measured, no short-circuit hides one | suppressed propagation: with `child_instrumentation=True`, an arm that reads a child pytest's outcome **cannot** record `FAIL`, so it is reported `BLIND` |
| `Pass.RERAISING` | true propagation and true cross-process semantics | stops at the first failing assert in a test, leaving later arms `NOT-REACHED` |

Neither pass alone is the kill set. An instrumented-only kill is an
*attribution* a plain run cannot make; a plain-only kill is an *observation* the
instrument cannot make — and only the second kind corrupts a figure. An
instrumented-only kill does not establish that an arm has its own control (a
subsumed arm reds under the instrument too), only that the attribution needs the
instrument.

`pass_` is positional on `Runner.run()` with no default, `Matrix` refuses a
`pass_` that is not a `Pass` member, and every figure interpolates both the pass
and the denominator. The denominator is the `ast.Assert` node count, carried
separately from `collected_tests`, so a figure cannot quote one while meaning
the other.

### Using it

```python
from tests.kill_matrix import Edit, Mutant, Pass, Runner

runner = Runner(selection=["tests/test_thing.py::test_one_arm"], repo_root=REPO)
result = runner.run(
    Pass.RECORDING,
    [Mutant("ROT", (Edit(path=SRC, old="shipped", new="rotted"),))],
)
print(result.table())          # the grid, with the pass in its header
print(result.cell("ROT", 897))  # one cell
```

`Edit` is validated before it is applied. `expect` is how many occurrences of
`old` the caller asserts are there (all are replaced); `occurrence` (1-based)
instead targets exactly one, which is what a repeated line forces a caller to
do.

### What it refuses, and why each refusal exists

| refused | because |
| --- | --- |
| a mutant that changes the **line count** | every assert below the edit shifts its `lineno` and reports `NOT-REACHED`; a green run with a blank matrix is indistinguishable from a file that never ran |
| a mutant whose `old` is **absent** | it writes nothing, so every assert passes — indistinguishable from a surviving mutant |
| a mutant whose `old` occurs a different number of times than `expect` | a by-text substitution on a repeated line mutates a different site and returns a false reading; name the `occurrence` |
| a target with **two asserts on one line** | the matrix is keyed on a lineno and could only merge them into one cell |
| an **empty** selection, a directory, a path that is not a file, or a selection spanning two files | it never runs the full suite, and a selection it cannot resolve to one file is a failure, not a silent pass |
| starting while `meta/kanban/.full-suite.lock` exists under the given repo root | another worktree owns the host; it also never writes a lock |
| an edit naming `_refuse_unless_test_database` or `nonogram_poc`, or an edit to `tests/conftest.py` or `tests/database_guard.py` | the database guard is never widened or bypassed |

Aggregation across executions is **ANY-RED**: one RED anywhere is a kill. An
assert inside a `for` loop runs once per iteration and an assert in a test that
also runs in a child process records once per pid, and last-write-wins loses
those REDs — `aggregate_last_write_wins` is kept beside `aggregate_any_red` as
the control that must disagree with it.

`SHIPPED` is re-run and asserted FAIL-free **between** mutants, not only at the
start, and compared to its own first reading cell for cell: a leaked patch and a
real kill look identical.

Restores are `cp -p` from backups, verified with `diff -q` **and**
`shasum -a 256`, with every later edit's content read from the backup.
**No git command anywhere** — `test_kill_matrix.py` enumerates that from this
module's own AST rather than by reading it. It takes no timing measurements and
reports none; `subprocess`'s `timeout=` is a bound on a hung child, not a
measurement.

### Its two anchors

`test_kill_matrix.py` reproduces two matrices this board measured three
independent ways in wave 50, which is what keeps the instrument from certifying
itself:

* `tests/test_full_suite_lock.py` at `ddb1731b` — **130 of 130 PASS and
  reached**, zero `NOT-REACHED`, with `41` as the *collected test* count and
  never the denominator.
* `tests/test_db_engine_lifecycle.py` at `b441ba00` — CARD-257's four-arm grid
  at `:859` / `:878` / `:889` / `:897`: six `DOC-NAME-DEL` cells RED at `:878`,
  four `DOC-HEAD-DEL` cells RED at `:889`, `NAMES-BLIND` RED at `:859` with the
  three arms below it `NOT-REACHED`, `POINTER-ROT` and `POINTER-DEL-WORD` RED at
  `:897`, `CONTROLS-RENAME-ONLY` `PASS`, SHIPPED all-PASS.

### Declared bounds

* `child_dependent_linenos` is **intra-function**: it marks every assert after a
  possible spawn in the same function, so it over-marks rather than
  under-marks, and it does **not** see an arm that reads a child's outcome
  through a helper's return value or a fixture.
* The `BLIND` overlay is applied only when `child_instrumentation=True`. With it
  off the child is pristine, propagation across the boundary is intact, and
  those arms are measured for real.
* One target file per run, so a matrix's domain is never ambiguous.
* The database-guard refusal is a path-and-text refusal over the sites that
  carry the guard today, not an analysis of what an edit would do.

## Troubleshooting

**"ModuleNotFoundError: No module named 'nonogram'"**
```bash
pip install -e .
```

**"database does not exist"**

Since CARD-244 the fixtures create their own database, so this should not
happen for a derived name. If you have pointed `TEST_DATABASE_URL` at a name
outside `[a-z0-9_]`, the fixtures decline to create it (they would have to
interpolate it into `CREATE DATABASE`) and say so in the skip reason — make it
yourself, or pick a plainer name:
```bash
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_mine_test"
createdb nonogram_mine_test
```

**"Refusing to set up the test database"**
`TEST_DATABASE_URL` names a database the `db_session` fixture must not erase. Point it at a database whose name ends in `_test`. The role in the URL must own the `public` schema of that database (the fixture drops and recreates it).

**Tests fail with "Connection refused"**
```bash
# Verify PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# Or check:
pg_isready
```

**Import errors in tests**
```bash
# Reinstall in dev mode
pip install -e '.[dev]'

# Verify PYTHONPATH
echo $PYTHONPATH
```

## Next Steps

After Wave 1 tests pass:

1. Document any issues found in `docs/ADMIN_FINDINGS.md`
2. Create Wave 2 test files for async generation, error recovery, etc.
3. Add Playwright/browser tests for UI interactions
4. Set up CI/CD pipeline to run tests on every push

---

**Test Status**: Wave 1 ✓ Complete  
**Coverage Target**: 80%+  
**Run Command**: `pytest tests/ -v`
