#!/bin/bash

# PostgreSQL Diagnostic Script
# Helps identify connection and setup issues

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# The database to diagnose -- resolved exactly as start_admin_local.sh,
# setup_admin_local.sh and run_admin_tests.sh resolve it (CARD-150..152), so
# this script checks the database those scripts would use in the same shell.
# It used to check and suggest nonogram_poc whatever DATABASE_URL said, and
# overwrote DATABASE_URL with it (CARD-492, IDEA-035).
#
# An exported DATABASE_URL wins. Copied rather than sourced, like the other
# copies; tests/test_setup_admin_local.py holds them identical.
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

echo -e "${BLUE}PostgreSQL Diagnostic${NC}"
echo "  DATABASE_URL=$DATABASE_URL ($DATABASE_URL_SOURCE)"
echo ""

# 1. Check if psql command exists
echo -e "${YELLOW}1. Checking psql command...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ psql found at:${NC} $(which psql)"
    psql --version
else
    echo -e "${RED}✗ psql command not found${NC}"
    echo "  Install: brew install postgresql@15"
    exit 1
fi
echo ""

# 2. Check Homebrew PostgreSQL
echo -e "${YELLOW}2. Checking Homebrew PostgreSQL service...${NC}"
if command -v brew &> /dev/null; then
    if brew services list | grep -q postgresql@15; then
        STATUS=$(brew services list | grep postgresql@15 | awk '{print $2}')
        echo "  Service status: $STATUS"
        if [ "$STATUS" = "started" ]; then
            echo -e "${GREEN}✓ PostgreSQL is running via Homebrew${NC}"
        else
            echo -e "${YELLOW}⚠ PostgreSQL is stopped (Homebrew)${NC}"
            echo "  Start with: brew services start postgresql@15"
        fi
    else
        echo -e "${YELLOW}ℹ PostgreSQL@15 not installed via Homebrew${NC}"
    fi
else
    echo -e "${YELLOW}ℹ Homebrew not found${NC}"
fi
echo ""

# 3. Check Docker
echo -e "${YELLOW}3. Checking Docker containers...${NC}"
if command -v docker &> /dev/null; then
    if docker ps | grep -q postgres; then
        echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
        docker ps | grep postgres
    elif docker ps -a | grep -q postgres; then
        echo -e "${YELLOW}⚠ PostgreSQL container exists but is stopped${NC}"
        docker ps -a | grep postgres
        echo "  Start with: docker-compose up -d postgres"
    else
        echo -e "${YELLOW}ℹ No PostgreSQL container found${NC}"
    fi
else
    echo -e "${YELLOW}ℹ Docker not found${NC}"
fi
echo ""

# 4. Try connecting to default database
echo -e "${YELLOW}4. Attempting connection to PostgreSQL...${NC}"
echo ""

# Try localhost with default user
echo -e "${YELLOW}Testing connection to localhost:5432...${NC}"
if psql -h localhost -U postgres -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Successfully connected to localhost:5432${NC}"

    # Check if the resolved database exists on this server. Inside the `if`,
    # so `set -e` cannot end the script when the name is not listed (the bare
    # `psql ... | grep` that stood here did exactly that, CARD-492).
    echo ""
    echo -e "${YELLOW}5. Checking databases...${NC}"
    if [ -z "$DB_NAME" ]; then
        echo -e "${YELLOW}⚠ DATABASE_URL names no database${NC}"
        echo "  Put the database's name after the host, e.g. .../nonogram_dev (or ?dbname=...)"
    elif psql -h localhost -U postgres -d postgres -c "\l" | grep -qw -- "$DB_NAME"; then
        echo -e "${GREEN}✓ $DB_NAME database exists${NC}"
    else
        echo -e "${YELLOW}⚠ $DB_NAME database not found on localhost:5432${NC}"
        echo "  Create with: createdb $DB_NAME"
    fi
    echo ""

    # Test with DATABASE_URL, as given (psql is handed it without a +driver)
    echo -e "${YELLOW}6. Testing with DATABASE_URL...${NC}"
    if psql "$PSQL_URL" -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ DATABASE_URL connection works${NC}"
    else
        echo -e "${YELLOW}⚠ DATABASE_URL connection failed${NC}"
        echo "  URL: $DATABASE_URL ($DATABASE_URL_SOURCE)"
        echo "  Try: psql \"$PSQL_URL\" -c 'SELECT 1'"
    fi
else
    echo -e "${RED}✗ Cannot connect to PostgreSQL${NC}"
    echo ""
    echo "Trying alternative connection methods..."
    echo ""

    # Try socket connection
    echo -e "${YELLOW}Trying Unix socket (no host)...${NC}"
    if psql -U postgres -d postgres -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Socket connection works${NC}"
        # psycopg2, not psycopg (v3): psycopg2-binary is the DBAPI this project
        # installs, and `normalized_url` deliberately leaves an explicitly named
        # driver alone — so an operator who followed the old advice got
        # `ModuleNotFoundError: No module named 'psycopg'`, the 2026-09-25
        # outage's exact error, out of the repo's own diagnostic (CARD-148).
        echo "  Your DATABASE_URL should use: postgresql+psycopg2://postgres:postgres@/${DB_NAME:-<database>}?host=/tmp"
    else
        echo -e "${RED}✗ Socket connection also failed${NC}"
        echo ""
        echo "PostgreSQL is definitely not running. Try:"
        echo "  Option 1: brew services start postgresql@15"
        echo "  Option 2: docker-compose up -d postgres"
        echo "  Option 3: postgres -D /usr/local/var/postgres"
    fi
fi
echo ""

# 7. Summary
echo -e "${BLUE}═════════════════════════════════════════${NC}"
echo -e "${YELLOW}Recommended next steps:${NC}"
echo ""
echo "If PostgreSQL is running and connection works:"
echo "  → Run: ./scripts/setup_admin_local.sh"
echo "  → Then: ./scripts/start_admin_local.sh"
echo ""
echo "If PostgreSQL is NOT running:"
echo "  → Run: brew services start postgresql@15"
echo "  → Then: createdb ${DB_NAME:-<database>}  (if database doesn't exist)"
echo "  → Then: ./scripts/start_admin_local.sh"
echo ""
echo "If connection fails but PostgreSQL shows as running:"
echo "  → Check password: default is 'postgres'"
echo "  → Check if database '${DB_NAME:-<database>}' exists"
echo "  → Try: psql -h localhost -U postgres -d postgres -c 'SELECT 1'"
echo ""
