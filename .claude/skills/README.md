# Nonogram Admin Panel UI Testing Skills

Comprehensive testing skills for the admin panel batch puzzle generation workflow.

## Available Skills

### 1. **test-admin-ui.md** - Complete Flow Testing
Master checklist for testing the entire admin panel workflow.

**What it covers:**
- Starting admin console
- Dashboard verification
- Batch creation flow
- Directory upload basics
- Image preview & sizing
- Puzzle generation
- Multi-directory testing
- Success criteria & failure scenarios

**When to use:** Before releases, for end-to-end validation

**Time estimate:** 15-20 minutes

---

### 2. **test-directory-upload.md** - Directory Upload Feature
Focused testing of directory selection and image loading.

**What it covers:**
- Birds directory (10 images)
- Crabs directory (15 images)
- Size configuration (Fixed/Min/Max)
- Image name customization
- Batch summary information
- File loading error handling
- Performance benchmarks

**When to use:** Testing directory upload feature specifically

**Time estimate:** 10-15 minutes

---

### 3. **test-image-preview.md** - Image Preview & Cropping
Detailed testing of image preview rendering and content-aware cropping.

**What it covers:**
- Preview image loading
- Content-aware cropping (threshold 200)
- Puzzle size prediction
- Preview box styling
- Responsive design
- Error handling for corrupted images
- Performance benchmarks

**When to use:** Testing image processing and preview quality

**Time estimate:** 10-15 minutes

---

### 4. **test-generated-puzzles.md** - Puzzle Results Page
Testing generated puzzle display, metadata, and actions.

**What it covers:**
- Puzzle grid rendering (SVG)
- Puzzle metadata display (size, difficulty, quality)
- Download functionality
- Approve/Reject buttons
- Batch summary sidebar
- Responsive layout
- Performance benchmarks

**When to use:** Testing puzzle generation results

**Time estimate:** 10-15 minutes

---

### 5. **test-error-scenarios.md** - Error Handling & Regression
Comprehensive error scenario testing and regression checks.

**What it covers:**
- Invalid directory handling
- Large file handling (up to 2MB)
- Mixed image formats (JPG/PNG)
- Rapid user interactions
- Network/connection issues
- Regression tests for known issues
- Accessibility testing
- Performance regression

**When to use:** Before releases, regression testing, stress testing

**Time estimate:** 20-30 minutes

---

## Quick Start

### For a Quick UI Test (5 minutes)
```bash
1. Run test-admin-ui.md steps 1-4
2. Verify batch creation page loads
3. Check directory upload works
```

### For Pre-Release Testing (30 minutes)
```bash
1. Run test-admin-ui.md completely
2. Run test-error-scenarios.md regression tests
3. Document any failures
```

### For Feature Validation (15 minutes)
```bash
1. Run test-directory-upload.md
2. Run test-image-preview.md
3. Verify all success criteria met
```

### For Full QA Suite (45-60 minutes)
```bash
1. Run all skills in order:
   - test-admin-ui.md
   - test-directory-upload.md
   - test-image-preview.md
   - test-generated-puzzles.md
   - test-error-scenarios.md
2. Document results
3. Create bug reports for failures
```

---

## Test Data Available

### Birds Directory
- **Path:** `/silhouette/animals/birds/`
- **Image count:** 10
- **Formats:** JPG, PNG
- **Size range:** 6KB - 265KB
- **Images:** bird1, bird2, dove1, dove3, duck1, duck2, owl1, raven1, simple_bird2, tsaplia1

### Crabs & Sea Creatures Directory
- **Path:** `/silhouette/animals/crabs/`
- **Image count:** 15
- **Formats:** JPG, PNG
- **Size range:** 16KB - 195KB
- **Images:** crab1-6, heachhock1-3, jellyfish1-2, octopus1, sea_horse1-2

---

## Key Success Criteria Summary

### Must Have (Critical)
- ✅ No "Failed to load image" errors
- ✅ No "Failed to load grid" errors
- ✅ Directory upload works for both test directories
- ✅ All images convert to grids
- ✅ Puzzles generate without timeout
- ✅ Downloads work correctly

### Should Have (Important)
- ✅ Responsive layout on mobile/tablet
- ✅ Preview images load quickly
- ✅ Metadata displays accurately
- ✅ Error messages are helpful
- ✅ No 403 Forbidden errors

### Nice to Have (Performance)
- ✅ Dashboard loads in < 2 seconds
- ✅ Preview page loads in < 5 seconds
- ✅ Generation completes in < 10 seconds
- ✅ Downloads start in < 2 seconds

---

## Known Issues & Workarounds

### Issue: 403 Forbidden in Chrome
- **Root cause:** macOS AirPlay using port 5000
- **Workaround:** Use port 5005 instead
- **Alternative:** Use incognito mode or Opera

### Issue: File picker dialog invisible in browser automation
- **Root cause:** Native OS dialog can't be automated
- **Workaround:** Use Python script to test backend directly
- **Status:** Acceptable - automated tests verify functionality

### Issue: "Failed to load image" (FIXED)
- **Root cause:** OS temp cleanup removed files before browser loaded
- **Fix:** Use persistent storage `/tmp/nonogram_uploads/`
- **Status:** ✅ Fixed and verified

---

## Test Execution Commands

### Start Admin Console
```bash
cd /Users/omelnikova/PycharmProjects/PythonProject4
python3 /tmp/run_admin.py &
# Runs on port 5005
```

### Run Backend Tests
```bash
cd /Users/omelnikova/PycharmProjects/PythonProject4
./.venv/bin/python -m pytest tests/test_batch_generator.py -v
```

### Test Directory Upload Directly
```bash
python3 /tmp/test_full_workflow.py
```

---

## Reporting Issues

When an issue is found:
1. Document the exact steps to reproduce
2. Include browser/OS information
3. Check console for error messages
4. Take screenshots if relevant
5. File as bug with reproduction steps

---

## Continuous Improvement

These skills should be updated when:
- New features are added
- Bugs are fixed
- Performance requirements change
- User feedback suggests improvements
- New edge cases are discovered

Last updated: 2026-09-09
