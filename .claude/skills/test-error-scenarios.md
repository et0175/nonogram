# UI Test: Error Scenarios & Regression Testing

Test error handling, edge cases, and ensure no regressions.

## Error Scenario Tests

### Scenario 1: Invalid Directory Selection
**Objective:** Verify graceful error handling for invalid directories

1. Navigate to batch creation page
2. Try to select invalid/empty directory
3. Verify:
   - ✓ System shows error message
   - ✓ User can select different directory
   - ✓ No page crash
   - ✓ Can retry without page reload

**Expected Behavior:**
- Error message: "Directory is empty or contains no supported images"
- UI remains responsive
- User can navigate back and try again

### Scenario 2: Large Image Files
**Objective:** Verify handling of large images (up to 2MB limit)

1. Upload directory with large images (200KB+ each)
2. Verify:
   - ✓ Files upload successfully
   - ✓ Previews load (might take longer)
   - ✓ Generation completes without timeout
   - ✓ No memory errors

**Success Criteria:**
- ✓ Handles up to 2MB per file
- ✓ Progress indication shown
- ✓ Timeout > 30 seconds for large batch

### Scenario 3: Mixed Image Formats
**Objective:** Verify mixed JPG/PNG formats work

1. Select directory with both JPG and PNG files
2. Verify:
   - ✓ All formats recognized
   - ✓ Previews load for all
   - ✓ Conversion works for all
   - ✓ No format-specific errors

**Test Data:**
- Birds: JPG and PNG mixed ✓
- Crabs: JPG and PNG mixed ✓

### Scenario 4: Rapid Successive Operations
**Objective:** Verify system handles rapid user interactions

1. Quickly upload directory
2. Rapidly click sizing options (Fixed → Min → Max → Fixed)
3. Quickly apply changes to multiple images
4. Verify:
   - ✓ No race conditions
   - ✓ UI stays responsive
   - ✓ Final state is consistent
   - ✓ No duplicate operations

**Success Criteria:**
- ✓ System queues/debounces properly
- ✓ Final state matches last user action
- ✓ No stuck UI elements

### Scenario 5: Network/Connection Issues
**Objective:** Verify graceful handling of connection problems

1. Start batch generation
2. Simulate network latency (browser DevTools throttling)
3. Verify:
   - ✓ Generation completes (with delay)
   - ✓ No errors shown prematurely
   - ✓ Retry mechanism works if needed
   - ✓ Progress indicator shows wait state

**Test Conditions:**
- Slow 3G throttling
- Offline then reconnect
- High latency (500ms+)

## Regression Tests

### Regression 1: No "Failed to Load" Errors
**Objective:** Ensure previous issue doesn't return

Previous Issue: "Failed to load image" errors for bird silhouettes (temp file cleanup)

**Test:**
1. Upload birds directory
2. Generate puzzles
3. Navigate to Generated Puzzles page
4. Verify:
   - ✓ NO "Failed to load image" in preview
   - ✓ NO "Failed to load grid" in puzzle cards
   - ✓ All images and grids render

**Success Criteria:**
- ✓ 100% of files load successfully
- ✓ No placeholder error messages visible
- ✓ Temp files persist for entire session

### Regression 2: No 403 Forbidden Errors
**Objective:** Ensure Chrome CORS issue is fixed

Previous Issue: 403 Forbidden in Chrome (now fixed with port 5005)

**Test:**
1. Open admin panel in Chrome (regular, not incognito)
2. Navigate through all pages
3. Verify:
   - ✓ NO 403 errors
   - ✓ All API calls succeed
   - ✓ Downloads work
   - ✓ No CORS errors in console

**Test Browser:**
- Chrome (main browser)
- Opera (alternative)
- Incognito mode (fallback)

### Regression 3: Cropping Behavior
**Objective:** Ensure cropping is correct (not too aggressive)

Previous Issue: Cropping too aggressive early in development

**Test:**
1. Upload birds directory
2. Check image previews
3. Verify:
   - ✓ Content centered in box
   - ✓ Not too much blank space
   - ✓ Content is visible and recognizable
   - ✓ Aspect ratio preserved

**Success Criteria:**
- ✓ Threshold at 200 is correct
- ✓ Silhouettes clearly visible
- ✓ No over-cropping

### Regression 4: Preview Sizing
**Objective:** Ensure preview sizing is correct

Previous Issue: Preview pictures initially too large

**Test:**
1. Upload directory
2. Check preview box sizes:
   - ✓ Image preview box: 200×200px
   - ✓ Puzzle preview box: 200×200px
   - ✓ Both use `aspect-ratio: 1` (square)
   - ✓ Both responsive on mobile

**Success Criteria:**
- ✓ Preview size consistent across pages
- ✓ Boxes maintain aspect ratio
- ✓ Images scale without distortion

### Regression 5: Temp File Cleanup
**Objective:** Ensure temp files persist during session

Previous Issue: OS cleanup removed temp files before browser could load them

**Test:**
1. Upload directory of images
2. Check `/tmp/nonogram_uploads/` directory
3. Verify:
   - ✓ Files created with UUID names
   - ✓ Files persist during entire batch
   - ✓ Files accessible via `/api/image/` endpoints
   - ✓ Files cleaned up after batch (or manually)

**Success Criteria:**
- ✓ Files use persistent storage (not mkstemp)
- ✓ Files named: `<uuid>_<filename>`
- ✓ Files persist for entire user session

## Accessibility Tests

### Test 1: Keyboard Navigation
1. Tab through all interactive elements
2. Verify:
   - ✓ All buttons reachable by keyboard
   - ✓ Tab order is logical
   - ✓ Enter/Space activates buttons
   - ✓ Escape closes dialogs (if any)

### Test 2: Color Contrast
1. Check button/text contrast ratios
2. Verify:
   - ✓ Text readable (WCAG AA minimum)
   - ✓ Errors clearly visible
   - ✓ Success states clear

### Test 3: Screen Reader Compatibility
1. Test with screen reader (NVDA, JAWS, or built-in)
2. Verify:
   - ✓ Page structure announced correctly
   - ✓ Form labels associated
   - ✓ Image alt text present
   - ✓ Buttons have accessible names

## Performance Regression

### Baseline Metrics (from testing)
- Admin console startup: ~3 seconds
- Dashboard load: < 2 seconds
- Batch creation page: < 2 seconds
- Preview page with 10 images: < 5 seconds
- Generation page: < 10 seconds
- Download: < 2 seconds

### Regression Check
Run performance tests and verify:
- ✓ No significant slowdown (>20%)
- ✓ Memory usage stable (no leaks)
- ✓ No console warnings (except deprecation)
- ✓ Images optimize/lazy-load correctly

## Notes

- Keep this checklist updated as new features are added
- Run before each release
- Document any new regressions found
- Track performance over time
