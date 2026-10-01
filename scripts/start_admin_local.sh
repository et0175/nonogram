#!/bin/bash

# Local Admin Panel Setup & Startup Script
# Usage: ./scripts/start_admin_local.sh [--port PORT] [--no-migrate] [--help]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults
PORT=5000
RUN_MIGRATIONS=true
CHECK_ONLY=false
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The database this script will use.
#
# An exported DATABASE_URL wins. The hardcoded ``export DATABASE_URL=...`` that
# used to sit at step [4/6] overwrote whatever the caller had exported, so there
# was no way to point this script at another database without editing it
# (CARD-150). The resolution happens here, before the banner, because step [1/6]
# has to check the database the panel will actually read.
DEFAULT_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
if [ -n "${DATABASE_URL:-}" ]; then
    DATABASE_URL_SOURCE="exported by the caller"
else
    DATABASE_URL="$DEFAULT_DATABASE_URL"
    DATABASE_URL_SOURCE="project default"
fi
# The database name, for the psql checks and for the message when they fail.
DB_NAME="${DATABASE_URL##*/}"
DB_NAME="${DB_NAME%%\?*}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --no-migrate)
            RUN_MIGRATIONS=false
            shift
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: ./scripts/start_admin_local.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT           Flask port (default: 5000)"
            echo "  --no-migrate          Skip database migrations"
            echo "  --check-only          Run every check, report what would be used, do not start Flask"
            echo "  --help                Show this help message"
            echo ""
            echo "Environment:"
            echo "  DATABASE_URL          Database to use. An exported value wins; otherwise"
            echo "                        the project default $DEFAULT_DATABASE_URL"
            echo "                        is used. The database must already exist - this"
            echo "                        script never creates one. If it is unreachable, or"
            echo "                        if a migration fails, the script stops."
            echo ""
            echo "Examples:"
            echo "  ./scripts/start_admin_local.sh                # Default (port 5000, run migrations)"
            echo "  ./scripts/start_admin_local.sh --port 8000   # Use port 8000"
            echo "  ./scripts/start_admin_local.sh --no-migrate  # Skip migrations"
            echo "  ./scripts/start_admin_local.sh --check-only  # Check everything, start nothing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Nonogram Admin Panel - Local Environment Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}[1/6]${NC} Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ psql (PostgreSQL) not found${NC}"
    echo "  Install with: brew install postgresql@15"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL found${NC}"

# Check PostgreSQL is running AND that the database this script will use is
# reachable -- on every branch, not only the Docker ones.
#
# This branch used to run a bare ``psql -c "SELECT 1"``, which connects to the
# default database ($USER) and says nothing about $DB_NAME. It printed
# "✓ PostgreSQL is running (Homebrew)" on a machine where nonogram_poc did not
# exist and then served a panel whose every database read failed (CARD-150).
# Both Docker branches already asserted the database; now all three agree.
#
# Connecting to a database that does not exist fails, it does not create one,
# and this script creates nothing: which database the owner wants is their call.
if docker exec nonogram-postgres psql -U postgres -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Docker)${NC}"
elif docker-compose exec postgres psql -U postgres -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Docker Compose)${NC}"
elif psql "$DATABASE_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Homebrew)${NC}"
else
    echo -e "${RED}✗ Database '$DB_NAME' is not reachable${NC}"
    echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
    echo "  Either PostgreSQL is not running, or '$DB_NAME' does not exist."
    echo "  Start PostgreSQL with: docker-compose up -d postgres"
    echo "  Or:                    brew services start postgresql@15"
    echo "  See which databases you have with: psql -l"
    echo "  Point this script at one of them with: export DATABASE_URL=..."
    echo "  This script does not create a database."
    exit 1
fi
echo ""

# Navigate to project root
cd "$PROJECT_ROOT"

# Check venv exists
echo -e "${YELLOW}[2/6]${NC} Checking virtual environment..."
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "  Create with: python3 -m venv .venv"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment exists${NC}"
echo ""

# Activate venv
echo -e "${YELLOW}[3/6]${NC} Activating virtual environment..."
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# The launch line below asks for ``nonogram.admin.app`` (see the comment there),
# and that name resolves ONLY through the editable install's path entry: the
# package lives at ``src/nonogram``, so the working directory yields
# ``src.nonogram`` and never a bare ``nonogram``. Check it here so a venv without
# the install fails with the command to run instead of a raw ModuleNotFoundError
# out of flask. Deliberately does not install anything on the developer's behalf.
if ! python -c 'import nonogram' > /dev/null 2>&1; then
    echo -e "${RED}✗ Project not installed in the virtual environment${NC}"
    echo "  'import nonogram' failed, so --app nonogram.admin.app cannot resolve."
    echo "  Install it with: pip install -e .   (in the activated venv, from $PROJECT_ROOT)"
    exit 1
fi
echo -e "${GREEN}✓ Project importable (editable install present)${NC}"
echo ""

# Set environment variables
echo -e "${YELLOW}[4/6]${NC} Setting environment variables..."
export FLASK_ENV=development
# Resolved at the top of the script, and already checked at step [1/6].
export DATABASE_URL
echo -e "${GREEN}✓ Environment variables set${NC}"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
echo ""

# Run migrations (optional)
if [ "$RUN_MIGRATIONS" = true ]; then
    echo -e "${YELLOW}[5/6]${NC} Running database migrations..."
    # A failed migration used to print "⚠ Migrations may have issues (but
    # continuing)" and discard alembic's output -- the one message that would
    # have explained the problem (CARD-150). Refuse, and say what alembic said.
    # --no-migrate is the explicit flag for starting without migrating.
    if MIGRATION_OUTPUT="$(alembic upgrade head 2>&1)"; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${RED}✗ Migrations failed${NC}"
        echo "  alembic upgrade head said:"
        if [ -n "$MIGRATION_OUTPUT" ]; then
            echo "$MIGRATION_OUTPUT" | sed 's/^/    /'
        else
            echo "    (no output)"
        fi
        echo "  Fix it, or start without migrating: ./scripts/start_admin_local.sh --no-migrate"
        exit 1
    fi
else
    echo -e "${YELLOW}[5/6]${NC} Skipping migrations (--no-migrate)"
fi
echo ""

# Start Flask
echo -e "${YELLOW}[6/6]${NC} Starting Flask application..."
if [ "$CHECK_ONLY" = true ]; then
    # Every check above has run for real; the only thing skipped is the
    # ``flask run`` below, which never returns. This is what makes the script's
    # decisions testable (tests/test_start_admin_local.py).
    echo -e "${GREEN}✓ All checks passed; not starting Flask (--check-only)${NC}"
    exit 0
fi
echo -e "${GREEN}✓ Flask starting on port $PORT${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Admin Panel is ready!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "  URL:  http://localhost:$PORT"
echo "  Logs: Check output below"
echo ""
echo "  To stop: Press Ctrl+C"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Start Flask.
#
# ``nonogram.admin.app``, not ``src.nonogram.admin.app`` (CARD-139): the two
# spellings name the same file but are two different module trees to Python, so
# launching by the ``src.``-prefixed one loaded the admin package twice and the
# panel crashed on Print setup with ``ValueError: tuple.index(x): x not in
# tuple`` out of ``book_plan.Plan.cell``. The package no longer contains a
# relative import, so the two trees can no longer disagree — but there is
# nothing to gain from the prefix either, and pointing the repo's own launcher
# at the spelling that caused a live 500 is how the trap gets rediscovered.
# ``nonogram`` resolves through the editable install activated above, from any
# working directory.
python -m flask --app nonogram.admin.app run --port $PORT
