# Admin Panel Scripts

Quick scripts to set up and test the Nonogram Admin Panel locally.

## Prerequisites

- Python 3.11+ (with virtual environment activated)
- PostgreSQL 15+ running locally
- Database `nonogram_poc` created

## Scripts

### `start_admin_local.sh` — Full Setup + Start Flask

**Runs everything**: checks prerequisites, activates venv, sets env vars, runs migrations, starts Flask.

```bash
./scripts/start_admin_local.sh              # Default: port 5000
./scripts/start_admin_local.sh --port 8000 # Custom port
./scripts/start_admin_local.sh --no-migrate # Skip migrations
```

**Access**: http://localhost:5000

### `setup_admin_local.sh` — Setup Only (No Flask)

Setup without starting Flask. Use for one-time setup or CI/CD.

```bash
./scripts/setup_admin_local.sh
```

After setup, start Flask manually:
```bash
source .venv/bin/activate
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
python -m flask --app src.nonogram.admin.app run
```

### `run_admin_tests.sh` — Test Runner

Run tests by type: Wave 1, Wave 2, unit, E2E, smoke, integration.

```bash
./scripts/run_admin_tests.sh wave1                  # Wave 1 tests
./scripts/run_admin_tests.sh wave2                  # Wave 2 tests
./scripts/run_admin_tests.sh all -v                # All tests, verbose
./scripts/run_admin_tests.sh e2e --coverage        # E2E + coverage report
./scripts/run_admin_tests.sh unit                   # Unit tests only
./scripts/run_admin_tests.sh smoke                  # Quick smoke tests
./scripts/run_admin_tests.sh --help                 # Show options
```

## Measurement scripts

Not admin-panel tooling: one-shot measurements kept in the repo because the number they
produced is a *calibration*, and a calibration nobody can re-run is a guess with a
decimal point.

### `measure_difficulty_cutoff.py` — where the medium/hard cutoff can sit

Builds a seeded corpus through the existing generator (`orchestrator.generate`, random
mode — the path the admin's batch generation uses) and scores it through the existing
scoring path, then reports, for each candidate medium/hard cutoff, the resulting
easy/medium/hard shares: overall, per FR-034 longest-side bucket, and per density. No
solver re-entry, no new entry point, and it never opens a database.

```bash
./.venv/bin/python scripts/measure_difficulty_cutoff.py                  # ~200s, 1010 requests
./.venv/bin/python scripts/measure_difficulty_cutoff.py --draws 2        # quick look
./.venv/bin/python scripts/measure_difficulty_cutoff.py --json out.json  # also dump the rows
```

One `random.Random` seeds the whole run and the corpus size is asserted, so the table
replays exactly. It produced the evidence the owner chose
`difficulty.MEDIUM_MAX_SCORE = 90.0` from (CARD-137); re-run it before moving that
constant again.

## Typical Workflow

### Day 1: Set up and start testing

```bash
# Full setup + start Flask
./scripts/start_admin_local.sh

# In another terminal, run Wave 1 tests
./scripts/run_admin_tests.sh wave1
```

### Day 2+: Restart and test

```bash
# Start Flask (setup already done)
./scripts/start_admin_local.sh --no-migrate

# Run tests
./scripts/run_admin_tests.sh wave1 -v
```

### Testing specific features

```bash
# E2E tests only
./scripts/run_admin_tests.sh e2e -v

# Unit tests with coverage
./scripts/run_admin_tests.sh unit --coverage

# All tests verbose
./scripts/run_admin_tests.sh all -v
```

## Manual Commands

If you prefer to run commands manually:

```bash
# Activate venv
source .venv/bin/activate

# Set env vars
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"

# Run migrations
alembic upgrade head

# Start Flask (port 5000)
python -m flask --app src.nonogram.admin.app run

# Or use different port
python -m flask --app src.nonogram.admin.app run --port 8000

# Run all tests
pytest tests/test_wave1_*.py tests/test_wave2_*.py -v

# Run Wave 1 tests only
pytest tests/test_batch_history.py tests/test_puzzle_preview.py tests/test_bulk_operations.py tests/test_wave1_e2e.py -v

# Run with coverage
pytest tests/test_wave1_*.py --cov=src/nonogram/admin --cov-report=html
```

## Troubleshooting

### PostgreSQL not running

```bash
# Homebrew (macOS)
brew services start postgresql@15

# Docker
docker-compose up -d postgres
```

### Port 5000 already in use

Use `--port` flag:
```bash
./scripts/start_admin_local.sh --port 8000
```

### Virtual environment not found

Create one:
```bash
python3 -m venv .venv
pip install -e '.[dev]'
```

### Migration errors

```bash
# Check current migration
alembic current

# Rollback and retry
alembic downgrade base
alembic upgrade head
```

## Documentation

For detailed testing workflow and test plan, see:

- **Setup & Testing**: `docs/TESTING_WORKFLOW.md`
- **Test Checklist**: `docs/ADMIN_TESTING_PLAN.md`
- **Issue Tracking**: `docs/ADMIN_FINDINGS.md`
- **General Setup**: `README.md`

## Questions?

See `docs/TESTING_WORKFLOW.md` for the complete manual testing guide.
