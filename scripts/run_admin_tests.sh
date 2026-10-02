#!/bin/bash

# Admin Panel Test Runner Script
# Usage: ./scripts/run_admin_tests.sh [TEST_TYPE] [OPTIONS]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate venv if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    source .venv/bin/activate
fi

# The database the suite is pointed at -- resolved exactly as
# start_admin_local.sh resolves it (CARD-150, CARD-151), so the three admin
# scripts agree on which database a given shell means (CARD-152). An exported
# DATABASE_URL wins; this script used to hardcode
# ``export DATABASE_URL=.../nonogram_poc`` over it. Resolved before the
# arguments are parsed so --help can name the default. Copied rather than
# sourced from a shared file: tests/test_start_admin_local.py runs that script
# alone in a throwaway root, where a sourced helper would not exist.
DEFAULT_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
if [ -n "${DATABASE_URL:-}" ]; then
    DATABASE_URL_SOURCE="exported by the caller"
else
    DATABASE_URL="$DEFAULT_DATABASE_URL"
    DATABASE_URL_SOURCE="project default"
fi
# The database name: whatever follows the host, up to any ?query -- unless the
# query names one itself (?dbname= overrides the path for libpq and the panel's
# driver alike; the last one wins). Empty when the URL names no database, which
# the check below refuses rather than let psql substitute the user's database.
DB_PATH="${DATABASE_URL#*://}"
DB_QUERY=""
if [[ "$DB_PATH" == *\?* ]]; then
    DB_QUERY="${DB_PATH#*\?}"
fi
DB_PATH="${DB_PATH%%\?*}"
if [[ "$DB_PATH" == */* ]]; then
    DB_NAME="${DB_PATH#*/}"
else
    DB_NAME=""
fi
DBNAME_IN_QUERY='.*&dbname=([^&]*)'
if [[ "&$DB_QUERY" =~ $DBNAME_IN_QUERY ]]; then
    DB_NAME="${BASH_REMATCH[1]}"
fi
# The URL as psql is handed it: psql parses only postgresql:// and postgres://,
# so drop a +driver from the scheme (postgresql+psycopg2:// is what the panel
# builds, CARD-148) and nothing else -- the check still carries the URL's host,
# port, credentials and query. Alembic and the panel get DATABASE_URL as given.
PSQL_URL="${DATABASE_URL%%://*}"
PSQL_URL="${PSQL_URL%%+*}://${DATABASE_URL#*://}"

# Set environment. DATABASE_URL is checked below, once the arguments are
# parsed, so --help and a mistyped option still answer without a database.
export FLASK_ENV=development
export DATABASE_URL

# Defaults
TEST_TYPE="all"
VERBOSE=""
COVERAGE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        all)
            TEST_TYPE="all"
            shift
            ;;
        wave1)
            TEST_TYPE="wave1"
            shift
            ;;
        wave2)
            TEST_TYPE="wave2"
            shift
            ;;
        e2e)
            TEST_TYPE="e2e"
            shift
            ;;
        unit)
            TEST_TYPE="unit"
            shift
            ;;
        smoke)
            TEST_TYPE="smoke"
            shift
            ;;
        integration)
            TEST_TYPE="integration"
            shift
            ;;
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help)
            echo "Usage: ./scripts/run_admin_tests.sh [TEST_TYPE] [OPTIONS]"
            echo ""
            echo "Test Types:"
            echo "  all          Run all admin panel tests (default)"
            echo "  wave1        Run Wave 1 tests (batch, preview, bulk ops)"
            echo "  wave2        Run Wave 2 tests (async, error recovery, books, PDF)"
            echo "  e2e          Run end-to-end tests only"
            echo "  unit         Run unit tests only"
            echo "  smoke        Run smoke tests only (quick)"
            echo "  integration  Run integration tests only"
            echo ""
            echo "Options:"
            echo "  -v, --verbose     Verbose output"
            echo "  --coverage        Show code coverage"
            echo "  --help            Show this help"
            echo ""
            echo "Environment:"
            echo "  DATABASE_URL      Database the tests use. An exported value wins; otherwise"
            echo "                    the project default $DEFAULT_DATABASE_URL"
            echo "                    is used. The database must already exist - this"
            echo "                    script never creates one. If it is unreachable, the"
            echo "                    script stops before running any test."
            echo ""
            echo "Examples:"
            echo "  ./scripts/run_admin_tests.sh wave1                # Run Wave 1 tests"
            echo "  ./scripts/run_admin_tests.sh e2e -v               # Verbose E2E tests"
            echo "  ./scripts/run_admin_tests.sh all --coverage       # All tests + coverage"
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
echo -e "${BLUE}Nonogram Admin Panel - Test Runner${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# The database the suite will use is reachable -- checked the way
# setup_admin_local.sh and start_admin_local.sh check it, on every branch.
# Without this, an unreachable database did not stop anything: the suite's
# database-backed tests skip when they cannot connect (tests/conftest.py), so
# the run came back green having tested nothing that needed it (CARD-152).
echo -e "${YELLOW}Checking the database...${NC}"
echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ psql (PostgreSQL) not found${NC}"
    echo "  Install with: brew install postgresql@15"
    exit 1
fi
if [[ "$DATABASE_URL" != *://* ]]; then
    echo -e "${RED}✗ DATABASE_URL is not a URL${NC}"
    echo "  Give it as a URL, e.g. postgresql://postgres@localhost:5432/nonogram_test"
    echo "  This script does not create a database."
    exit 1
fi
if [ -z "$DB_NAME" ]; then
    echo -e "${RED}✗ DATABASE_URL names no database${NC}"
    echo "  Put the database's name after the host, e.g. .../nonogram_test (or ?dbname=...)"
    echo "  See which databases you have with: psql -l"
    echo "  This script does not create a database."
    exit 1
fi
if docker exec nonogram-postgres psql -U postgres -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Docker)${NC}"
elif docker-compose exec postgres psql -U postgres -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Docker Compose)${NC}"
elif psql "$PSQL_URL" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running, database '$DB_NAME' reachable (Homebrew)${NC}"
else
    echo -e "${RED}✗ Database '$DB_NAME' is not reachable${NC}"
    echo "  Either PostgreSQL is not running, or '$DB_NAME' does not exist."
    echo "  Start PostgreSQL with: docker-compose up -d postgres"
    echo "  Or:                    brew services start postgresql@15"
    echo "  See which databases you have with: psql -l"
    echo "  Point this script at one of them with: export DATABASE_URL=..."
    echo "  This script does not create a database."
    exit 1
fi
echo ""

# Build pytest command
CMD="pytest"

case $TEST_TYPE in
    all)
        CMD="$CMD tests/test_wave1_*.py tests/test_wave2_*.py"
        echo "Running: All admin panel tests"
        ;;
    wave1)
        CMD="$CMD tests/test_wave1_*.py tests/test_batch_history.py tests/test_puzzle_preview.py tests/test_bulk_operations.py"
        echo "Running: Wave 1 tests (batch history, preview, bulk operations)"
        ;;
    wave2)
        CMD="$CMD tests/test_wave2_*.py"
        echo "Running: Wave 2 tests (async, error recovery, books, PDF)"
        ;;
    e2e)
        CMD="$CMD -m e2e"
        echo "Running: End-to-end tests only"
        ;;
    unit)
        CMD="$CMD -m unit"
        echo "Running: Unit tests only"
        ;;
    smoke)
        CMD="$CMD -m smoke"
        echo "Running: Smoke tests (quick)"
        ;;
    integration)
        CMD="$CMD -m integration"
        echo "Running: Integration tests only"
        ;;
esac

# Add options
if [ ! -z "$VERBOSE" ]; then
    CMD="$CMD $VERBOSE"
    echo "Output: Verbose"
fi

if [ "$COVERAGE" = true ]; then
    CMD="$CMD --cov=src/nonogram/admin --cov-report=html"
    echo "Coverage: Enabled (output in htmlcov/)"
fi

CMD="$CMD -v"
echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────${NC}"
echo ""

# Run tests
eval $CMD

echo ""
echo -e "${BLUE}─────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}Tests completed!${NC}"
echo ""

if [ "$COVERAGE" = true ]; then
    echo "Coverage report: $(pwd)/htmlcov/index.html"
    echo ""
fi
