#!/bin/bash

# Setup-only script (no Flask startup)
# Use this for one-time setup or in non-interactive environments

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The database this script will use -- resolved exactly as
# start_admin_local.sh resolves it (CARD-150, CARD-151), so the three admin
# scripts agree on which database a given shell means (CARD-152).
#
# An exported DATABASE_URL wins. This script used to hardcode
# ``export DATABASE_URL=.../nonogram_poc`` over whatever the caller exported,
# after checking a different database altogether. The resolution happens here,
# before the banner, because the prerequisite check has to target it.
#
# Copied from start_admin_local.sh rather than sourced from a shared file:
# tests/test_start_admin_local.py runs that script alone in a throwaway root,
# where a sourced helper would not exist. Keep the three copies identical.
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

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Nonogram Admin Panel - Setup Only${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3${NC}"

if ! command -v psql &> /dev/null; then
    echo -e "${RED}✗ PostgreSQL not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL${NC}"

# PostgreSQL is running AND the database this script will migrate is
# reachable, on every branch. The Homebrew branch used to run a bare
# ``psql -c "SELECT 1"``, which checks the default database ($USER) and says
# nothing about the one alembic is about to use; the Docker branches checked
# nonogram_poc whatever DATABASE_URL said (CARD-152). Connecting to a database
# that does not exist fails, it does not create one -- and neither does this
# script. A value that is not a URL, and a URL that names no database, are
# refused before any psql runs.
if [[ "$DATABASE_URL" != *://* ]]; then
    echo -e "${RED}✗ DATABASE_URL is not a URL${NC}"
    echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
    echo "  Give it as a URL, e.g. postgresql://postgres@localhost:5432/nonogram_dev"
    echo "  This script does not create a database."
    exit 1
fi
if [ -z "$DB_NAME" ]; then
    echo -e "${RED}✗ DATABASE_URL names no database${NC}"
    echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
    echo "  Put the database's name after the host, e.g. .../nonogram_dev (or ?dbname=...)"
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

cd "$PROJECT_ROOT"

# Activate venv
echo -e "${YELLOW}Activating virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "Create with: python3 -m venv .venv"
    exit 1
fi
source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Set environment
echo -e "${YELLOW}Setting environment variables...${NC}"
export FLASK_ENV=development
# Resolved at the top of the script, and already checked above.
export DATABASE_URL
echo -e "${GREEN}✓ Environment set${NC}"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
echo ""

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
# A failed migration used to print "⚠ Migrations may have issues", discard
# alembic's output -- the one message that explains the problem -- and go on to
# say "Setup complete!" (CARD-152, as CARD-150 fixed in start_admin_local.sh).
# Refuse, and say what alembic said.
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
    echo "  Setup is not complete. Fix the migration and run this script again."
    exit 1
fi
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Setup complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps:"
echo "  1. Start Flask:     ./scripts/start_admin_local.sh"
echo "  2. Run tests:       ./scripts/run_admin_tests.sh wave1"
echo ""
