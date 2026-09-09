# UI Test: Generated Puzzles Page

Test the puzzle generation results, grid rendering, and puzzle management features.

## Test Cases

### Test 1: Puzzle Grid Display
**Objective:** Verify generated puzzle grids render without errors

1. Complete batch generation with birds or crabs directory
2. Navigate to "Generated Puzzles" page
3. Verify each puzzle:
   - ✓ Grid SVG loads correctly
   - ✓ Grid is 200×200px (preview size)
   - ✓ No "Failed to load grid" error messages
   - ✓ Clues visible (row/column numbers)
   - ✓ Solution grid matches generated size

**Success Criteria:**
- ✓ 100% of grids display (no failures)
- ✓ Grids are black & white nonogram format
- ✓ All puzzle previews load within 2 seconds
- ✓ No console errors in DevTools

### Test 2: Puzzle Information Display
**Objective:** Verify puzzle metadata displays correctly

1. On Generated Puzzles page, check each card shows:
   - ✓ Size (e.g., "15×15")
   - ✓ Difficulty tier (Easy/Medium/Hard)
   - ✓ Quality score (1-100)
   - ✓ Source image name
   - ✓ Download button

**Data Validation:**
- Size matches target configuration
- Difficulty tier is valid (not null/undefined)
- Quality score is 1-100 range
- Source image name is recognizable
- Download button is functional

**Success Criteria:**
- ✓ All metadata displays
- ✓ No missing or "N/A" values for valid fields
- ✓ Formatting is consistent across cards
- ✓ Numbers are reasonable (quality > 0, size > 0)

### Test 3: Download Functionality
**Objective:** Verify puzzle download works

1. On Generated Puzzles page
2. Click "⬇️ Download SVG" button on any puzzle
3. Verify:
   - ✓ Browser starts download
   - ✓ File is named correctly (puzzle_<id>.svg or similar)
   - ✓ File size is reasonable (5-50KB)
   - ✓ SVG file is valid (can open in browser/Illustrator)

**File Validation:**
- File type: SVG (text/svg+xml)
- Content: Valid SVG markup
- Contains: viewBox, grid lines, numbers/clues
- Can be viewed: Open in browser or image viewer

**Success Criteria:**
- ✓ Download initiates
- ✓ File is valid SVG
- ✓ File contains expected puzzle content
- ✓ No corrupted or empty files

### Test 4: Puzzle Action Buttons
**Objective:** Verify approve/reject functionality

1. On Generated Puzzles page
2. Test "✓ Approve" button:
   - ✓ Puzzle moves to "Approved" status
   - ✓ UI updates to show approval
   - ✓ Can still download after approval

3. Test "✕ Reject" button:
   - ✓ Shows confirmation dialog
   - ✓ Puzzle moves to "Rejected" status
   - ✓ Removed from active list (or marked rejected)

**Success Criteria:**
- ✓ Buttons are responsive
- ✓ Actions complete without errors
- ✓ Confirmation dialog prevents accidental rejection
- ✓ Status updates in UI immediately

### Test 5: Batch Summary Information
**Objective:** Verify summary sidebar is accurate

1. On Generated Puzzles page, check sidebar:
   - ✓ Generated count matches puzzles displayed
   - ✓ Batch ID is shown (clickable/copyable)
   - ✓ "Generation complete!" message visible
   - ✓ Navigation buttons work:
     - "➕ Create New Batch"
     - "🏠 Back to Dashboard"

**Success Criteria:**
- ✓ Summary counts are accurate
- ✓ Batch ID is valid and unique
- ✓ Navigation buttons navigate correctly
- ✓ All UI elements are visible

### Test 6: Responsive Layout
**Objective:** Verify page works on different screen sizes

1. Test on desktop (1512×784):
   - ✓ Grids 200×200px
   - ✓ 2 puzzles per row (6-column layout)
   - ✓ Sidebar visible on right
   - ✓ No horizontal scrolling

2. Test on tablet (800×600):
   - ✓ Layout adapts
   - ✓ Puzzles stack appropriately
   - ✓ Information readable
   - ✓ Buttons accessible

3. Test on mobile (375×667):
   - ✓ Full responsive
   - ✓ Single column layout
   - ✓ Sidebar collapses (if needed)
   - ✓ Touch targets adequate (44px minimum)

**Success Criteria:**
- ✓ Layouts adapt smoothly
- ✓ Content readable at all sizes
- ✓ No content overflow
- ✓ Touch-friendly on mobile

## Error Scenarios

### Failed Grid Rendering
If grids don't load:
1. Check `/api/puzzle/<puzzle_id>/grid` endpoint
2. Verify SVG generation logic in app.py
3. Check grid data in database
4. Look for grid validation errors

### Missing Puzzle Metadata
If metadata missing:
1. Check puzzle data structure
2. Verify metrics calculated correctly
3. Check database for NULL values
4. Review difficulty calculation

### Download Failures
If download fails:
1. Check file exists on disk
2. Verify content-type headers
3. Check file permissions
4. Review error logs

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Page load | < 3s | ? |
| Grid render (per puzzle) | < 500ms | ? |
| 10 puzzles total | < 5s | ? |
| Download initiation | < 1s | ? |

## Notes

- Grids are SVG (vector format)
- Stored in database or generated on-demand
- Preview size: 200×200px
- Each grid should show clues clearly
- Grid rendering uses `/api/puzzle/<id>/grid` endpoint
