# CARD-005b: Comprehensive Unit Tests for Admin Services

**Status**: Pending  
**Priority**: High  
**Wave**: 1  
**Size**: Large (13 points)

## Description

Unit tests exist for batch generation and puzzle metrics, but coverage is incomplete. Add comprehensive unit tests for all admin services to ensure 80%+ code coverage.

## Acceptance Criteria

- [ ] AC-1: >80% code coverage for admin services
- [ ] AC-2: All service methods have unit tests
- [ ] AC-3: Filter logic tested (by size, difficulty, quality, combinations)
- [ ] AC-4: Bulk operations tested (approve multiple, reject multiple)
- [ ] AC-5: Book difficulty distribution calculation tested
- [ ] AC-6: Input validation tested for all validators
- [ ] AC-7: Edge cases tested (empty lists, invalid IDs, boundary values)
- [ ] AC-8: Tests marked with @pytest.mark (unit, integration, etc.)
- [ ] AC-9: All tests pass locally and in CI

## Test Requirements

**Unit Tests** (to write):
- test_batch_service.py (10+ tests)
- test_puzzle_review_service.py (15+ tests)
- test_book_manager.py (10+ tests)
- test_validators.py (10+ tests)
- test_metrics.py (5+ tests)

Each test file should:
- Use fixtures from conftest.py
- Test happy path and error cases
- Be independent (no shared state)

## Dependencies

- conftest.py with fixtures
- Services implemented

## Worktree Notes

- Create test files in tests/ directory
- Use pytest fixtures for setup/teardown
- Generate coverage report: `pytest --cov=src/nonogram/admin tests/`
- Aim for 80%+ coverage
