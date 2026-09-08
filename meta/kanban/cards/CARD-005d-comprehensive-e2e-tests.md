# CARD-005d: Comprehensive E2E Test Suite

**Status**: Pending  
**Priority**: High  
**Wave**: 1-2  
**Size**: Large (13 points)

## Description

Expand E2E tests to cover complete workflows and edge cases: full admin panel workflows, error scenarios, concurrency, data consistency, and performance.

## Acceptance Criteria

- [ ] AC-1: test_admin_panel_e2e.py expanded to 30+ tests
- [ ] AC-2: Complete workflow: batch generation → puzzle review → book creation → PDF download
- [ ] AC-3: Error workflows: batch failure → retry → success
- [ ] AC-4: Concurrent operations: multiple batches running simultaneously
- [ ] AC-5: Data consistency: after operation, database matches expected state
- [ ] AC-6: Performance tests: operations complete within target times
- [ ] AC-7: Filters work correctly with various combinations
- [ ] AC-8: Bulk operations work with filters applied
- [ ] AC-9: Book selection (auto-balanced and manual) produces correct puzzle distribution
- [ ] AC-10: All tests marked and can be run by category: `pytest -m e2e`

## Test Requirements

**E2E Tests** (expand existing):
- Batch generation workflows (small, medium, large)
- Puzzle review workflows (filter, approve, reject, bulk)
- Book creation workflows (auto-balanced, manual selection)
- PDF generation workflows
- Error recovery workflows
- Concurrency tests
- Performance benchmarks

## Dependencies

- conftest.py with fixtures
- All admin services implemented

## Worktree Notes

- Organize tests by workflow/feature
- Use class-based test organization
- Create helper functions for common operations
- Run coverage: `pytest --cov tests/test_admin_panel_e2e.py`
- Run by type: `pytest -m smoke`, `pytest -m slow`
