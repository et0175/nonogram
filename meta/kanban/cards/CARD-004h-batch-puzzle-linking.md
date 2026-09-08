# CARD-004h.1: Batch-to-Puzzle Linking (Blocker)

**Status**: Pending  
**Priority**: High  
**Wave**: 1 (blocker for 004h)  
**Size**: Small (3 points)  
**Depends On**: CARD-004h

## Description

CARD-004h (Batch History) implementation blocked by missing batch-to-puzzle relationship in database. Puzzles don't track which batch generated them, making it impossible to retrieve batch-specific puzzle lists.

This is a quick fix needed to complete Wave 1 testing.

## Acceptance Criteria

- [ ] AC-1: Puzzles table has `batch_id` column (foreign key to batches table)
- [ ] AC-2: `add_puzzle()` accepts optional `batch_id` parameter and stores it
- [ ] AC-3: `get_batch_puzzles(batch_id)` filters puzzles by batch_id (not theme)
- [ ] AC-4: Batch generation passes batch_id when storing puzzles
- [ ] AC-5: All 9 failing Wave 1 tests now pass
- [ ] AC-6: Batch history correctly shows only its own puzzles (not all same-theme puzzles)

## Test Requirements

**Unit Tests**:
- Puzzle storage with batch_id
- Batch puzzle retrieval by batch_id

**E2E Tests**:
- Generate batch → retrieve puzzles → verify only that batch's puzzles returned

## Root Cause

Wave 1 tests show:
- Batch generation works ✓
- Puzzle storage works ✓
- Puzzle filtering works ✓
- **Batch-to-puzzle linking missing** ✗

Current implementation:
- `get_batch_puzzles()` filters by theme
- Multiple batches with same theme return same puzzles
- Can't tell which puzzles belong to which batch

## Why High Priority

Without this:
- Can't complete CARD-004h (Batch History)
- 9 Wave 1 tests fail (18% failure rate)
- Batch history feature is unusable in production
- User can't see/retry specific batches

## Implementation Notes

1. **Database migration**:
   - Add `batch_id VARCHAR(36)` to puzzles table
   - Add foreign key to batches table (if batches table exists)
   - For now: just store batch_id string

2. **puzzle_review_service.add_puzzle()**:
   ```python
   def add_puzzle(self, ..., batch_id=None):
       puzzle_id = f"puzzle_{self._next_id:06d}"
       self.puzzles[puzzle_id] = {
           ...
           "batch_id": batch_id,
           ...
       }
   ```

3. **batch_generator._generate_random_batch()**:
   ```python
   self.puzzle_review_service.add_puzzle(
       ...,
       batch_id=batch_id  # Pass batch_id
   )
   ```

4. **batch_generator.get_batch_puzzles()**:
   ```python
   # Filter by batch_id, not theme
   filter_opts = PuzzleFilter(batch_id=batch_id, limit=100)
   ```

5. **Add batch_id to PuzzleFilter**:
   ```python
   batch_id: Optional[str] = None
   ```

## Failing Tests After Fix

Once implemented, these 9 tests should pass:
- test_batch_stored_with_metadata ✓
- test_batch_tracks_completion_time ✓
- test_filter_batches_by_status_complete ✓
- test_filter_batches_by_status_pending ✓
- test_batch_detail_shows_all_metadata ✓
- test_batch_detail_includes_puzzle_list ✓
- test_bulk_approve_all_easy_puzzles ✓
- test_batch_history_filters_by_status ✓
- test_complete_wave1_workflow ✓

**Result**: 49/49 tests passing (100% Wave 1 coverage)

## Next Steps

1. Implement batch_id column storage
2. Update puzzle_review_service to handle batch_id
3. Update batch_generator to pass batch_id
4. Run tests: `pytest tests/test_batch_history.py tests/test_puzzle_preview.py tests/test_bulk_operations.py tests/test_wave1_e2e.py -v`
5. All tests should pass

---

**Estimated Time**: 30 minutes  
**Complexity**: Low (schema + parameter passing)  
**Risk**: Low (in-memory storage, no migration needed yet)
