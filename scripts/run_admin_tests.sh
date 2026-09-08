#!/bin/bash

# Admin Panel Test Runner Script
# Usage: ./scripts/run_admin_tests.sh [TEST_TYPE] [OPTIONS]

set -e

# Colors
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

# Set environment
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"

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
