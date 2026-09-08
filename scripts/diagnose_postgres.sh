#!/bin/bash

# PostgreSQL Diagnostic Script
# Helps identify connection and setup issues

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}PostgreSQL Diagnostic${NC}"
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

    # Check if nonogram_poc database exists
    echo ""
    echo -e "${YELLOW}5. Checking databases...${NC}"
    psql -h localhost -U postgres -d postgres -c "\l" | grep nonogram_poc
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ nonogram_poc database exists${NC}"
    else
        echo -e "${YELLOW}⚠ nonogram_poc database not found${NC}"
        echo "  Create with: createdb nonogram_poc"
    fi
    echo ""

    # Test with DATABASE_URL
    echo -e "${YELLOW}6. Testing with DATABASE_URL...${NC}"
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
    if psql $DATABASE_URL -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ DATABASE_URL connection works${NC}"
    else
        echo -e "${YELLOW}⚠ DATABASE_URL connection failed${NC}"
        echo "  URL: $DATABASE_URL"
        echo "  Try: psql \$DATABASE_URL -c 'SELECT 1'"
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
        echo "  Your DATABASE_URL should use: postgresql+psycopg://postgres:postgres@/nonogram_poc?host=/tmp"
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
echo "  → Then: createdb nonogram_poc  (if database doesn't exist)"
echo "  → Then: ./scripts/start_admin_local.sh"
echo ""
echo "If connection fails but PostgreSQL shows as running:"
echo "  → Check password: default is 'postgres'"
echo "  → Check if database 'nonogram_poc' exists"
echo "  → Try: psql -h localhost -U postgres -d postgres -c 'SELECT 1'"
echo ""
