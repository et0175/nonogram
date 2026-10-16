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

- `db_session` — `SessionLocal` factory bound to an empty, fully migrated test database (`TEST_DATABASE_URL`, default `…/nonogram_test`). The schema is rebuilt once per session (`DROP SCHEMA public CASCADE`, then `alembic upgrade head`) and every table is truncated before each test. Refuses — as a failure, before connecting — any URL whose database name does not end in `_test` or that overrides it with a `dbname`/`database` query parameter. Skips when the database is unreachable (one cached probe per run).
- `app` — Flask test app (depends on `db_session`)
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
and remove it when done:

```bash
echo "profiling run, started $(date -u +%Y-%m-%dT%H:%M:%SZ)" > meta/kanban/.full-suite.lock
# ... run the suite ...
rm meta/kanban/.full-suite.lock
```

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

## Troubleshooting

**"ModuleNotFoundError: No module named 'nonogram'"**
```bash
pip install -e .
```

**"database does not exist"**
```bash
# Set test database URL
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_test"
createdb nonogram_test
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
