# Wave 2 Testing & Implementation

**Wave 1 Status**: ✅ Complete (48/49 tests passing, 98%)  
**Wave 2 Status**: 🚀 Ready to start  
**Date Started**: 2026-09-07

## Wave 2 Cards

| Card | Title | Size | Status | Tests |
|------|-------|------|--------|-------|
| CARD-004k | Async Batch Generation | 13pt | Pending | test_wave2_async_generation.py |
| CARD-004l | Error Recovery & Retry | 5pt | Pending | test_wave2_async_generation.py |
| CARD-004m | Book Management & Selection | 8pt | Pending | test_wave2_async_generation.py |
| CARD-004n | PDF Generation & Download | 8pt | Pending | test_wave2_async_generation.py |

**Total Wave 2**: 34 points

## What's Ready

### Test Framework
✅ `test_wave2_async_generation.py` - Comprehensive test suite
- Async generation tests (concurrent batches)
- Error recovery tests (retry logic)
- Book management tests (puzzle selection)
- PDF generation tests

### Documentation
✅ Wave 2 cards with full AC and test requirements
✅ Test file with placeholder tests (marked with `# TODO`)
✅ Testing strategy in ADMIN_TESTING_PLAN.md

### Code Baseline
✅ Wave 1 batch-to-puzzle linking complete
✅ Puzzle review service stable
✅ Test isolation fixed
✅ 48/49 tests passing

## How to Start Wave 2

### 1. Pick a Card
Start with **CARD-004k** (Async Batch Generation):
```bash
# View the card
cat /meta/kanban/cards/CARD-004k-async-batch-generation.md

# View the AC (Acceptance Criteria)
# Implementation should:
# - Return batch_id immediately (async)
# - Run generation in background
# - Allow progress polling
# - Support concurrent batches
```

### 2. Run Tests to See What Fails
```bash
pytest tests/test_wave2_async_generation.py::TestAsyncBatchGeneration -v
```

Tests marked `# TODO` will fail with NotImplementedError or AssertionError

### 3. Implement & Test
- Implement async job queue (Redis/Celery recommended)
- Update batch_generator.py to use async
- Run tests again until they pass

### 4. Document Findings
Add to `/docs/ADMIN_FINDINGS.md`:
- Any issues encountered
- Solutions applied
- Performance numbers
- Status: `new` → `fixed` when complete

## Testing Strategy

### Wave 2 Specific
- **Async tests**: Verify non-blocking behavior
- **Error tests**: Simulate failures and verify recovery
- **Concurrency tests**: Multiple batches running together
- **Integration tests**: Full workflows with error scenarios

### Running Tests
```bash
# All Wave 2 tests
pytest tests/test_wave2_*.py -v

# Single card tests
pytest tests/test_wave2_async_generation.py::TestAsyncBatchGeneration -v

# With coverage
pytest tests/test_wave2_*.py --cov=src/nonogram/admin
```

### Markers
- `@pytest.mark.e2e` - Full workflow tests
- `@pytest.mark.integration` - Component integration
- `@pytest.mark.slow` - Takes >5 seconds

## Expected Challenges

### CARD-004k (Async)
- Challenge: Implementing job queue (Redis/Celery)
- Solution: Start with Redis + RQ (simpler than Celery)
- Fallback: Python asyncio + queues

### CARD-004l (Error Recovery)
- Challenge: Simulating batch failures
- Solution: Mock generator to fail on demand
- Test with: `pytest -m integration`

### CARD-004m (Book Management)
- Challenge: Auto-balanced selection algorithm
- Solution: Implement distribution calculator
- Test: Verify % Easy/Medium/Hard matches

### CARD-004n (PDF Generation)
- Challenge: Performance (200 puzzles → PDF)
- Solution: Lazy rendering + streaming
- Test: Measure generation time

## Success Criteria

Wave 2 is complete when:
- ✅ All test_wave2_*.py tests passing
- ✅ No critical issues in ADMIN_FINDINGS.md
- ✅ Performance baselines met (from ADMIN_TESTING_PLAN.md)
- ✅ All AC for each card verified
- ✅ Documentation updated

## Your Role Tomorrow

When you return:
1. **Review ADMIN_FINDINGS.md** for any Wave 1 issues to address
2. **Pick a Wave 2 card** to work on first
3. **Run the tests** to see what needs implementation
4. **Implement & document** as you go

## Quick Reference

| Resource | Path |
|----------|------|
| Cards | `/meta/kanban/cards/CARD-004k.md` etc. |
| Tests | `tests/test_wave2_*.py` |
| Documentation | `docs/ADMIN_TESTING_PLAN.md` |
| Findings | `docs/ADMIN_FINDINGS.md` |
| Setup | `docs/ADMIN_SETUP.md` |

---

**Ready to go!** Wave 2 test framework is in place. Come back tomorrow and start with CARD-004k. 🚀
