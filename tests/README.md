# Admin Panel Test Suite - Wave 1

Comprehensive tests for Wave 1 features: batch history, puzzle preview, bulk operations.

## Test Files

### Feature Tests

- **test_batch_history.py** — Batch history tracking and retrieval
  - Batch metadata storage
  - Batch list and filtering
  - Batch detail pages
  - Batch retry functionality

- **test_puzzle_preview.py** — Puzzle preview modal data
  - Preview data availability (grid, clues)
  - Grid rendering for all sizes (10×10 to 30×30)
  - Clue formatting
  - Preview API endpoints

- **test_bulk_operations.py** — Bulk approve/reject operations
  - Bulk approve single and multiple puzzles
  - Bulk reject single and multiple puzzles
  - Bulk operations with filters applied
  - Validation and idempotency

### End-to-End Tests

- **test_wave1_e2e.py** — Complete workflows combining all Wave 1 features
  - Batch generation → history verification
  - Puzzle preview before approval
  - Bulk operations on filtered puzzles
  - Complete workflow integration test

## Running Tests

### All Wave 1 Tests

```bash
pytest tests/test_batch_history.py tests/test_puzzle_preview.py tests/test_bulk_operations.py tests/test_wave1_e2e.py -v
```

### By Category

**Unit Tests Only** (fast, no database):
```bash
pytest -m unit -v
```

**Integration Tests** (uses database):
```bash
pytest -m integration -v
```

**E2E Tests** (full workflows):
```bash
pytest -m e2e -v
```

**Smoke Tests** (quick sanity checks):
```bash
pytest -m smoke -v
```

**Performance Tests**:
```bash
pytest -m performance -v
```

### Specific Test File

```bash
pytest tests/test_batch_history.py -v
pytest tests/test_puzzle_preview.py -v
pytest tests/test_bulk_operations.py -v
pytest tests/test_wave1_e2e.py -v
```

### Specific Test Class

```bash
pytest tests/test_batch_history.py::TestBatchHistoryStorage -v
pytest tests/test_bulk_operations.py::TestBulkApprove -v
```

### Specific Test

```bash
pytest tests/test_batch_history.py::TestBatchHistoryStorage::test_batch_stored_with_metadata -v
```

### With Coverage

```bash
pytest --cov=src/nonogram/admin --cov-report=html tests/

# Open htmlcov/index.html in browser
```

### Slow Tests (warnings)

Tests marked `@pytest.mark.slow` take longer than 5 seconds:

```bash
pytest -m slow -v    # Run only slow tests
pytest -m "not slow" -v  # Skip slow tests
```

## Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.unit` — Unit tests (isolated, fast)
- `@pytest.mark.integration` — Integration tests (use database)
- `@pytest.mark.e2e` — End-to-end tests (full workflows)
- `@pytest.mark.smoke` — Smoke tests (quick sanity checks)
- `@pytest.mark.slow` — Slow tests (>5 seconds)
- `@pytest.mark.performance` — Performance benchmarks

## Fixtures

Available fixtures (from `conftest.py`):

- `app` — Flask test app
- `client` — Flask test client
- `puzzle_review_service` — Puzzle review service
- `batch_generator_service` — Batch generator service
- `generator` — Nonogram generator
- `sample_puzzle` — Single generated puzzle
- `sample_puzzles` — 10 generated puzzles
- `cleanup_puzzles` — Cleanup fixture

## Continuous Integration

To run in CI/CD:

```bash
# Install test dependencies
pip install -e '.[dev]'

# Run all tests with coverage
pytest --cov=src/nonogram/admin --cov-report=xml tests/

# Exit with failure if coverage < 80%
pytest --cov=src/nonogram/admin --cov-fail-under=80 tests/
```

## Writing New Tests

When adding tests for new features:

1. Create test file: `tests/test_feature_name.py`
2. Use fixtures from `conftest.py`
3. Mark tests with appropriate markers (`@pytest.mark.unit`, etc.)
4. Include docstrings explaining what's being tested
5. Follow naming convention: `test_<what_is_being_tested>`

Example:

```python
"""Tests for my new feature."""

import pytest


class TestMyFeature:
    """Test my new feature."""

    @pytest.mark.unit
    def test_feature_does_something(self, fixture_name):
        """Test that feature does something specific."""
        result = fixture_name.do_something()
        assert result is True
```

## Debugging Tests

### Verbose Output

```bash
pytest -vv tests/test_batch_history.py
```

### Print Debug Info

```python
def test_something(puzzle_review_service):
    result = puzzle_review_service.get_stats()
    print("Stats:", result)  # Will print during test
    assert result['total'] > 0
```

Run with: `pytest -s tests/` (captures output)

### Stop on First Failure

```bash
pytest -x tests/  # Stop on first failure
pytest -x -vv tests/  # Verbose + stop first
```

### Run Only Failed Tests

```bash
pytest --lf tests/  # Run last failed
pytest --ff tests/  # Run failed first
```

## Performance Baselines

Update performance table in `docs/ADMIN_FINDINGS.md`:

```bash
# Time a specific test
time pytest tests/test_wave1_e2e.py::TestCompleteWorkflowWave1::test_complete_wave1_workflow -v

# Run with timing
pytest --durations=10 tests/test_wave1_e2e.py
```

## Troubleshooting

**"ModuleNotFoundError: No module named 'nonogram'"**
```bash
pip install -e .
```

**"database does not exist"**
```bash
# Set test database URL
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_test"
createdb nonogram_test
```

**Tests fail with "Connection refused"**
```bash
# Verify PostgreSQL is running
psql -U postgres -c "SELECT 1;"

# Or check:
pg_isready
```

**Import errors in tests**
```bash
# Reinstall in dev mode
pip install -e '.[dev]'

# Verify PYTHONPATH
echo $PYTHONPATH
```

## Next Steps

After Wave 1 tests pass:

1. Document any issues found in `docs/ADMIN_FINDINGS.md`
2. Create Wave 2 test files for async generation, error recovery, etc.
3. Add Playwright/browser tests for UI interactions
4. Set up CI/CD pipeline to run tests on every push

---

**Test Status**: Wave 1 ✓ Complete  
**Coverage Target**: 80%+  
**Run Command**: `pytest tests/ -v`
