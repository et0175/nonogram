# Admin Panel Testing Plan

Comprehensive testing strategy for the Nonogram Admin Panel including test scenarios, edge cases, and performance benchmarks.

## Testing Phases

### Phase 1: Core Workflows (Manual)
Test the happy path and critical user flows locally.

#### Batch Generation Workflow
- [ ] Generate small batch (50 puzzles)
  - Verify: Status shows GENERATING → COMPLETE
  - Verify: Progress bar reaches 100%
  - Verify: "50/50 Completed" appears in batch details
  
- [ ] Generate medium batch (100 puzzles)
  - Verify: Takes ~10-15 seconds locally
  - Verify: All puzzles stored in database
  
- [ ] Generate large batch (200 puzzles)
  - Verify: Takes ~20-30 seconds locally
  - Verify: No browser timeout
  - Verify: All metrics calculated correctly

#### Puzzle Review Workflow
- [ ] View generated puzzles
  - Verify: Puzzle count updates correctly
  - Verify: Filters work (size, difficulty, quality)
  - Verify: Pagination works (25 per page)
  
- [ ] Approve/reject puzzles
  - [ ] Approve single puzzle
    - Verify: Status changes to "approved"
    - Verify: Count in dashboard updates
  - [ ] Reject single puzzle
    - Verify: Status changes to "rejected"
    - Verify: No longer appears in draft filter
  
- [ ] Bulk operations (if implemented)
  - Approve multiple
  - Reject multiple
  - Clear selection

#### Book Creation Workflow
- [ ] Create book with approved puzzles
  - Verify: Puzzle count selected correctly
  - Verify: Book appears in Books list
  - Verify: Status shows "draft"
  
- [ ] Generate PDF
  - Verify: PDF downloads
  - Verify: PDF has correct puzzles
  - Verify: PDF is readable (open and check manually)

### Phase 2: Edge Cases (Manual)
Test boundary conditions and error scenarios.

#### Empty/Boundary States
- [ ] Generate batch with count=50 (minimum)
- [ ] Generate batch with count=200 (maximum)
- [ ] Try to generate with count=49 (below minimum)
  - Expected: Error message
- [ ] Try to generate with count=201 (above maximum)
  - Expected: Error message
- [ ] Review with 0 puzzles in system
  - Expected: "No puzzles found" message
- [ ] Create book with 0 approved puzzles
  - Expected: Error or disabled button

#### Filter Edge Cases
- [ ] Filter by size=10
  - Expected: Only 10x10 puzzles
- [ ] Filter by size=30
  - Expected: Only 30x30 puzzles
- [ ] Filter by size range (10-15)
  - Expected: Only puzzles in that range
- [ ] Filter by difficulty=Easy (if any exist)
  - Expected: Only Easy puzzles
- [ ] Filter by quality_min=80
  - Expected: Only high-quality puzzles
- [ ] Combine filters: size=20, difficulty=Medium, quality_min=70
  - Expected: Only puzzles matching all criteria

#### Error Handling
- [ ] Database connection failure
  - Expected: Error message, not crash
- [ ] Batch generation timeout
  - Expected: Graceful error, batch marked as ERROR
- [ ] PDF generation failure
  - Expected: Download button disabled, error message
- [ ] Invalid form input
  - Expected: Validation error before submission

### Phase 3: Performance (Automated)
Measure performance under load.

#### Local Benchmarks
```python
# Tests to run
- Generate 50 puzzles: target < 5 seconds
- Generate 100 puzzles: target < 10 seconds
- Generate 200 puzzles: target < 20 seconds
- Query 1000 puzzles: target < 1 second
- Generate PDF with 100 puzzles: target < 5 seconds
```

#### Render Benchmarks
```python
- Generate 200 puzzles: target < 60 seconds (free tier is slower)
- Query same with filters: target < 2 seconds
```

### Phase 4: Browser Compatibility (Manual)
Test across browsers.

- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if available)

### Phase 5: Responsiveness (Manual)
Test on different screen sizes.

- [ ] Desktop (1920x1080)
- [ ] Tablet (768x1024)
- [ ] Mobile (375x667)

## Automated Test Scenarios

Run with: `pytest tests/test_admin_panel_e2e.py -v`

See: `tests/test_admin_panel_e2e.py` for implementation

## Findings Tracker

See: `ADMIN_FINDINGS.md` for issues discovered during testing

## Performance Baseline

Establish baseline performance numbers:

| Operation | Target | Measured (Local) | Measured (Render) |
|-----------|--------|------------------|-------------------|
| Generate 50 puzzles | < 5s | TBD | TBD |
| Generate 100 puzzles | < 10s | TBD | TBD |
| Generate 200 puzzles | < 20s | TBD | TBD |
| Generate PDF (100 puzzles) | < 5s | TBD | TBD |
| Query 1000 puzzles | < 1s | TBD | TBD |

## Known Limitations (To Improve)

- [ ] Batch generation is synchronous (blocks request during generation)
  - Impact: Large batches may timeout
  - Fix: Implement async generation with job queue
  
- [ ] No batch history (can't see past batches)
  - Impact: User doesn't know what was generated before
  - Fix: Store batches in database, show history
  
- [ ] No puzzle preview before approval
  - Impact: Hard to judge puzzle quality
  - Fix: Show preview on hover or modal
  
- [ ] No bulk operations
  - Impact: Approving 200 puzzles requires 200 clicks
  - Fix: Add "Select All" + "Approve Selected" UI
  
- [ ] No error recovery
  - Impact: Failed batch leaves pending state
  - Fix: Add "Retry" or "Cancel" buttons

## Test Environment Setup

### Local
```bash
cd /Users/omelnikova/PycharmProjects/PythonProject4
export FLASK_ENV=development
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nonogram_poc"
python -m flask --app src.nonogram.admin.app run
# Visit http://localhost:5000
```

### Render
```bash
# No setup needed - use production instance
# Visit https://nonogram-admin.onrender.com
```

## Test Report Template

When you find an issue, add it to `ADMIN_FINDINGS.md` using this format:

```markdown
## Issue: [Title]

**Status**: `new` | `investigating` | `fixed` | `wontfix`

**Severity**: `critical` | `high` | `medium` | `low`

**Description**: 
[What happened, what was expected]

**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
...

**Environment**: Local | Render

**Screenshots**: [If applicable]

**Notes**: [Any additional context]
```

---

**Next**: Start with Phase 1 (Core Workflows) and document findings in ADMIN_FINDINGS.md
