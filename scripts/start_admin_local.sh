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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
        --help)
            echo "Usage: ./scripts/start_admin_local.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT           Flask port (default: 5000)"
            echo "  --no-migrate          Skip database migrations"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/start_admin_local.sh                # Default (port 5000, run migrations)"
            echo "  ./scripts/start_admin_local.sh --port 8000   # Use port 8000"
            echo "  ./scripts/start_admin_local.sh --no-migrate  # Skip migrations"
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

# Check PostgreSQL is running (via Docker)
if docker exec nonogram-postgres psql -U postgres -d nonogram_poc -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Docker)${NC}"
elif docker-compose exec postgres psql -U postgres -d nonogram_poc -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Docker Compose)${NC}"
elif psql -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running (Homebrew)${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo "  Start with: docker-compose up -d postgres"
    echo "  Or: brew services start postgresql@15"
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
echo ""

# Set environment variables
echo -e "${YELLOW}[4/6]${NC} Setting environment variables..."
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
echo -e "${GREEN}✓ Environment variables set${NC}"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  DATABASE_URL=$DATABASE_URL"
echo ""

# Run migrations (optional)
if [ "$RUN_MIGRATIONS" = true ]; then
    echo -e "${YELLOW}[5/6]${NC} Running database migrations..."
    if alembic upgrade head > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${YELLOW}⚠ Migrations may have issues (but continuing)${NC}"
    fi
else
    echo -e "${YELLOW}[5/6]${NC} Skipping migrations (--no-migrate)"
fi
echo ""

# Start Flask
echo -e "${YELLOW}[6/6]${NC} Starting Flask application..."
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

# Start Flask
python -m flask --app src.nonogram.admin.app run --port $PORT
