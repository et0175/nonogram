# Admin Panel Scripts

Quick scripts to set up and test the Nonogram Admin Panel locally.

## Prerequisites

- Python 3.11+ (with virtual environment activated, project installed with `pip install -e '.[dev]'`)
- PostgreSQL 15+ running locally
- A database that already exists, and a `DATABASE_URL` pointing at it. The
  project default is
  `postgresql://postgres:postgres@localhost:5432/nonogram_poc` for the panel's
  two scripts, and
  `postgresql://postgres:postgres@localhost:5432/nonogram_test` for
  `run_admin_tests.sh` (see below for why). In all three
  scripts — `start_admin_local.sh`, `setup_admin_local.sh` and
  `run_admin_tests.sh` — a `DATABASE_URL` you exported yourself wins over that
  default, and each prints the URL it settled on and where it came from
  (`exported by the caller` or `project default`). Each checks that the
  database it names is reachable and stops if it is not, or if the URL names no
  database at all. The check tries three ways in turn and the first that
  answers wins: a `nonogram-postgres` Docker container, then a Docker Compose
  `postgres` service, then your local `psql`. Only the local `psql` way checks
  the URL's host, port and credentials (a driver-qualified
  `postgresql+psycopg2://` URL included); the two Docker ways connect as
  `postgres` inside the container and check only that a database of that
  **name** exists there — so with such a container running, a URL aimed at
  another server passes if the container happens to hold a database of the
  same name. **The scripts never create a database** —
  which one you want is your call. `psql -l` lists the ones you have, and
  `createdb <name>` makes a new one if that is what you want.

## Scripts

### `start_admin_local.sh` — Full Setup + Start Flask

**Runs everything**: checks prerequisites, activates venv, sets env vars, runs migrations, starts Flask.

```bash
./scripts/start_admin_local.sh              # Default: port 5000
./scripts/start_admin_local.sh --port 8000 # Custom port
./scripts/start_admin_local.sh --no-migrate # Skip migrations
./scripts/start_admin_local.sh --check-only # Run every check, start nothing
```

**Which database it uses.** A `DATABASE_URL` you exported wins; with none
exported it falls back to the project default
`postgresql://postgres:postgres@localhost:5432/nonogram_poc`. Step `[4/6]`
prints the URL it settled on and where it came from, so there is no guessing:

```bash
export DATABASE_URL="postgresql://postgres@localhost:5432/nonogram_dev"
./scripts/start_admin_local.sh --check-only   # says: (exported by the caller)
```

**It stops rather than serving a panel that cannot read anything** (CARD-150):

- If that database is unreachable — the server is down, or the database does not
  exist — step `[1/6]` names it, exits non-zero, and starts nothing. It does not
  create the database for you.
- If `alembic upgrade head` fails, step `[5/6]` prints what alembic said and
  exits non-zero. `--no-migrate` is the explicit way to start without migrating.
- `--check-only` runs all six steps except the final `flask run`, which is handy
  for finding out whether local startup would work at all.

**Access**: http://localhost:5000

### `setup_admin_local.sh` — Setup Only (No Flask)

Setup without starting Flask. Use for one-time setup or CI/CD.

```bash
./scripts/setup_admin_local.sh
export DATABASE_URL="postgresql://postgres@localhost:5432/nonogram_dev"
./scripts/setup_admin_local.sh               # says: (exported by the caller)
```

It uses the same database as `start_admin_local.sh` would — your exported
`DATABASE_URL`, else the project default — and stops the same way (CARD-152):

- If that database is unreachable, it names it, exits non-zero, and migrates
  nothing. It does not create the database for you.
- If `alembic upgrade head` fails, it prints what alembic said, exits non-zero,
  and does not print "Setup complete!".

After setup, start Flask manually:
```bash
source .venv/bin/activate
export FLASK_ENV=development
# The same URL setup used: your own exported DATABASE_URL if you have one,
# else the project default below. It must already exist — nothing here
# creates one.
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/nonogram_poc}"
# nonogram.admin.app, never src.nonogram.admin.app: the src.-prefixed spelling
# loads the admin package a second time and the two copies disagree (CARD-139).
python -m flask --app nonogram.admin.app run
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

**Which database the tests get.** Your exported `DATABASE_URL`, else the project
default; it says which before running anything. Once the arguments are parsed
it checks that database is reachable and stops, running no test, if it is not
or if the URL names no database — the suite's database-backed tests would
otherwise skip and the run would come back green. That holds for every test
type, `unit` and `smoke` included: each needs `psql` installed and the
database reachable before any test runs. `--help` and a mistyped option answer
without a database.

Its project default is
`postgresql://postgres:postgres@localhost:5432/nonogram_test`, not the panel's
`nonogram_poc`: the suite itself refuses a database whose name does not contain
`test` (`tests/database_guard.py`, CARD-109), so the panel's database would
stop pytest at start-up. `nonogram_test` must already exist (`createdb
nonogram_test` if you want it). To use another test database, export it:

```bash
export DATABASE_URL="postgresql://postgres@localhost:5432/my_other_test"
./scripts/run_admin_tests.sh wave1
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

# In another terminal, run Wave 1 tests. With no DATABASE_URL exported they
# use nonogram_test, not the panel's database (see run_admin_tests.sh above).
./scripts/run_admin_tests.sh wave1
```

### Day 2+: Restart and test

```bash
# Start Flask (setup already done)
./scripts/start_admin_local.sh --no-migrate

# Run tests (nonogram_test, unless you exported another DATABASE_URL)
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

# Set env vars. A DATABASE_URL you already exported is kept; otherwise the
# project default that start_admin_local.sh falls back to is used. Either way
# the database must already exist.
export FLASK_ENV=development
export DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/nonogram_poc}"

# Run migrations
alembic upgrade head

# Start Flask (port 5000).
# nonogram.admin.app, never src.nonogram.admin.app: the src.-prefixed spelling
# loads the admin package a second time and the two copies disagree (CARD-139).
python -m flask --app nonogram.admin.app run

# Or use different port
python -m flask --app nonogram.admin.app run --port 8000

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

### Database not reachable

All three scripts stop at their database check naming the database they were
asked to use (`start_admin_local.sh` at step `[1/6]`, `setup_admin_local.sh`
under "Checking prerequisites", `run_admin_tests.sh` before running any test).
Either PostgreSQL is not running, that database does not exist, or — on the
local `psql` way, the only one that reads them — the URL's host, port or
credentials are wrong:

```bash
psql -l                                  # which databases do I have?
export DATABASE_URL="postgresql://postgres@localhost:5432/nonogram_dev"
./scripts/start_admin_local.sh --check-only
```

The script will not create the database — see Prerequisites.

### Migration errors

`start_admin_local.sh` exits at step `[5/6]`, and `setup_admin_local.sh` at
"Running database migrations", each printing alembic's own message.

```bash
# Check current migration
alembic current

# Rollback and retry
alembic downgrade base
alembic upgrade head

# Or start the panel without migrating
./scripts/start_admin_local.sh --no-migrate
```

## Documentation

For detailed testing workflow and test plan, see:

- **Setup & Testing**: `docs/TESTING_WORKFLOW.md`
- **Test Checklist**: `docs/ADMIN_TESTING_PLAN.md`
- **Issue Tracking**: `docs/ADMIN_FINDINGS.md`
- **General Setup**: `README.md`

## Questions?

See `docs/TESTING_WORKFLOW.md` for the complete manual testing guide.
