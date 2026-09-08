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

if docker exec nonogram-postgres psql -U postgres -d nonogram_poc -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Docker)${NC}"
elif docker-compose exec postgres psql -U postgres -d nonogram_poc -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Docker Compose)${NC}"
elif psql -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Homebrew)${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
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
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
echo -e "${GREEN}✓ Environment set${NC}"
echo ""

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
if alembic upgrade head > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠ Migrations may have issues${NC}"
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
