# Admin Panel Test Findings

Centralized tracking of issues discovered during testing of the Nonogram Admin Panel. Add new findings here as you test locally.

**Last Updated**: 2026-09-07

## Format

When documenting a finding, use this template:

```markdown
## Issue: [Brief title]

**Status**: `new` | `investigating` | `fixed` | `wontfix`

**Severity**: `critical` | `high` | `medium` | `low`

**Description**: 
[What happened, what was expected]

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]

**Environment**: Local | Render

**Expected Behavior**: [What should happen]

**Actual Behavior**: [What actually happened]

**Screenshots**: [Attach if visual]

**Notes**: [Any additional context]
```

---

## Active Issues

## Issue: Batch history doesn't track puzzle-to-batch relationship

**Status**: `fixed` ✅

**Severity**: `high` (was high, now resolved)

**Description**: 
Wave 1 tests show that batch generation and puzzle storage work correctly, but there's no way to retrieve which puzzles belong to which batch. Tests expect `batch.get_batch_puzzles()` to return only that batch's puzzles, but it currently returns all puzzles with the matching theme.

**Root Cause**:
- Puzzles table has no `batch_id` foreign key
- `get_batch_puzzles()` filters by theme (not batch-specific)
- Database schema incomplete for batch-to-puzzle linking

**Steps to Reproduce**:
1. Run `pytest tests/test_batch_history.py::TestBatchDetails -v`
2. See test failure: `assert len(puzzles) == 30` but gets 100

**Environment**: Local

**Expected Behavior**: 
- Each puzzle stores `batch_id` it was generated from
- `get_batch_puzzles(batch_id)` returns only puzzles from that batch
- Batch history shows "30 puzzles" not "100 puzzles"

**Actual Behavior**: 
- Puzzles don't track their source batch
- All puzzles with same theme returned
- Can't tell which batch generated which puzzles

**Affected Tests** (9 tests, 82% pass rate):
- test_batch_stored_with_metadata
- test_batch_tracks_completion_time
- test_filter_batches_by_status_complete
- test_filter_batches_by_status_pending
- test_batch_detail_shows_all_metadata
- test_batch_detail_includes_puzzle_list
- test_bulk_approve_all_easy_puzzles
- test_batch_history_filters_by_status
- test_complete_wave1_workflow

**Fix Required**:
1. Add `batch_id` column to puzzles table (foreign key)
2. Update `add_puzzle()` to accept and store batch_id
3. Update `get_batch_puzzles()` to filter by batch_id
4. Update batch generation to pass batch_id to puzzle service

**Fix Applied** (2026-09-07):
- Added `batch_id` column to puzzle storage in PuzzleReviewService
- Updated `add_puzzle()` to accept and store batch_id parameter
- Updated `PuzzleFilter` to support batch_id filtering
- Modified `get_batch_puzzles()` to filter by batch_id instead of theme
- Added `completed_at` timestamp to BatchJob for completion tracking
- Fixed test isolation by creating fresh PuzzleReviewService per test

**Result**: 48/49 Wave 1 tests now passing (98%)
- All batch history tests fixed
- All puzzle preview tests passing
- All bulk operation tests passing
- Core E2E workflows working
- One test has flaky timing (passes individually, sometimes fails in suite)

**Notes**:
- Implementation is synchronous (async is CARD-004k)
- Batch generation completes immediately after creation
- Batch-to-puzzle linking works with batch_id foreign key
- Test isolation improved with fresh service instances

---

---

## Wave 3 Enhancements: Image-Based Batch Generation

**Status**: `new` (Specification phase)

**Priority**: High (production-critical workflow)

**Description**: 
Enhance batch generation to support image-to-puzzle conversion workflow. Replace random generation with image-based generation, allowing users to upload/select images from directory, preview them with configurable sizes, and generate puzzles with original images visible.

**Scope**:
1. UI redesign - remove "Random" mode, add "From Images" as primary path
2. Directory/upload selection for source images
3. Image preview page with size selection (fixed, min, max options)
4. Batch generation from selected images
5. Puzzle preview showing original image (solution)
6. Puzzle name management (default: filename)

**Assumptions**:
- Image-to-puzzle conversion already implemented (src/nonogram/...)
- Support PNG, JPG, GIF formats
- Max image size: 2000x2000px
- Temporary storage of uploaded images during batch workflow
- Puzzle names: editable, filterable later
- Size options: fixed number (10-30), min (smallest that preserves quality), max (largest that preserves quality)

**Expected Workflow**:
1. User goes to Batch Generation
2. Selects "From Images" → directory picker or upload
3. Previews images with individual size selection
4. Confirms selection (can add/remove images)
5. System generates puzzles using selected parameters
6. Puzzles appear in review with original images visible

**Related Components**:
- Image processing: src/nonogram/generation (already done)
- Web UI: src/nonogram/web (already has size selection UI)
- Admin UI: new pages and endpoints needed

---

<!-- Add new findings here as you discover them during testing -->

### Example: (To Delete)

## Issue: Batch generation timeout after 2 minutes

**Status**: `new`

**Severity**: `high`

**Description**: 
When generating 200 puzzles on a free Render instance, the request times out after ~2 minutes even though generation completes successfully in the background.

**Steps to Reproduce**:
1. Go to Batch Generation
2. Create Large Batch (200 puzzles)
3. Wait for generation to complete

**Environment**: Render (free tier)

**Expected Behavior**: Status should reach 100% and show "COMPLETE"

**Actual Behavior**: Request hangs; page shows loading spinner indefinitely

**Notes**: Backend batch is created successfully; issue is frontend timeouts only

---

## Completed Issues (Fixed)

### Issue: Puzzles not storing in database (FIXED)

**Status**: `fixed`

**Severity**: `critical`

**Description**: 
Batch generation reported success but no puzzles appeared in Puzzle Review.

**Steps to Reproduce**:
1. Generate batch (50 puzzles)
2. Go to Puzzle Review
3. See 0 puzzles

**Environment**: Both Local and Render

**Root Cause**: 
- Local: _generate_random_batch() was a stub that never called actual generator
- Render: puzzle_review_service wasn't initialized when singleton was created

**Fix Applied**:
- Implemented _generate_random_batch() to call generator.generate_batch() and store each puzzle
- Changed singleton injection to lazy initialization with parameter passing
- Added DATABASE_URL env var to Render

**Commit**: 9dd019a, 3233013

**Lessons Learned**:
- Singleton + dependency injection is tricky; lazy init with parameters is safer
- Always test E2E through the actual web UI, not just unit tests

---

## Testing Progress

### Phase 1: Core Workflows

- [ ] Batch Generation
  - [ ] Small batch (50)
  - [ ] Medium batch (100)
  - [ ] Large batch (200)

- [ ] Puzzle Review
  - [ ] View puzzles
  - [ ] Filters work
  - [ ] Approve/reject

- [ ] Book Creation
  - [ ] Create book
  - [ ] Generate PDF

### Phase 2: Edge Cases

- [ ] Empty states
- [ ] Boundary values
- [ ] Error handling

### Phase 3: Performance

- [ ] Measure generation times
- [ ] Measure query performance

### Phase 4-5: Browser & Responsiveness

- [ ] Browser compatibility
- [ ] Mobile responsiveness

---

## Performance Baseline (To Update)

As you test, fill in the measured times:

| Operation | Target | Measured (Local) | Measured (Render) | Date |
|-----------|--------|------------------|-------------------|------|
| Generate 50 puzzles | < 5s | [TBD] | [TBD] | 2026-09-07 |
| Generate 100 puzzles | < 10s | [TBD] | [TBD] | 2026-09-07 |
| Generate 200 puzzles | < 20s | [TBD] | [TBD] | 2026-09-07 |
| Query 1000 puzzles | < 1s | [TBD] | [TBD] | 2026-09-07 |
| Generate PDF (100) | < 5s | [TBD] | [TBD] | 2026-09-07 |

---

## Known Limitations (To Fix)

Priority order for improving the admin panel:

1. **Synchronous batch generation** (blocks request)
   - Impact: Large batches may timeout in production
   - Mitigation: Use smaller batches locally until fixed
   - Fix: Implement async job queue (Celery or similar)

2. **No batch history**
   - Impact: Can't see what was generated in previous sessions
   - Mitigation: Keep notes manually
   - Fix: Store batch metadata in database

3. **No puzzle preview**
   - Impact: Hard to judge quality before approval
   - Mitigation: Approve/reject based on metrics
   - Fix: Add preview modal or hover

4. **No bulk operations**
   - Impact: Approving 200 puzzles = 200 clicks
   - Mitigation: Use filters to narrow scope
   - Fix: Add "Select All" + "Approve Selected"

5. **No error recovery**
   - Impact: Failed batch leaves in PENDING state
   - Mitigation: Hard refresh and try again
   - Fix: Add "Retry" or "Cancel" buttons

---

## Testing Notes

### How to Add a Finding

1. Copy the format template above
2. Fill in all fields
3. Add under "Active Issues"
4. Update severity and status as investigation progresses
5. When fixed, move to "Completed Issues (Fixed)"

### How to Share Findings

Send a message with:
- The issue title and description
- Steps to reproduce
- Environment (local or Render)
- Any screenshots or error messages

Example:
> Found an issue: when I try to approve a puzzle with status=draft, nothing happens. No error message, just silent fail. Let me add this to ADMIN_FINDINGS.md.

I'll then:
1. Read the issue from ADMIN_FINDINGS.md
2. Investigate the code
3. Fix or discuss the root cause
4. Update the findings file with the fix

---

## Questions to Explore

- [ ] What happens if I generate a batch, then before it completes, generate another batch?
- [ ] Can I filter by multiple sizes (e.g., 10 OR 20 OR 30)?
- [ ] What's the maximum number of puzzles that can be in one book?
- [ ] Does PDF generation work for all themes?

---

## Next Steps

1. **Start Phase 1 testing locally** using the steps in ADMIN_TESTING_PLAN.md
2. **Document any issues** you find in this file
3. **Share findings** - I'll investigate and fix them
4. **Iterate** on fixes until all tests pass

Let's build this systematically! 🚀
