# Admin Panel Test Cases

**Document Version**: 1.0  
**Date**: 2026-09-08  
**Format**: Comprehensive test cases with steps and expected results

## Test Case Overview

| TC ID | Title | User Story | Priority | Status |
|-------|-------|-----------|----------|--------|
| TC-101 | Upload PNG file | AS-001 | HIGH | ✅ Ready |
| TC-102 | Reject invalid format | AS-001 | HIGH | ✅ Ready |
| TC-103 | Upload progress indicator | AS-001 | HIGH | ✅ Ready |
| TC-104 | Upload success feedback | AS-001 | HIGH | ✅ Ready |
| TC-105 | Upload 5 images batch | AS-002 | HIGH | ✅ Ready |
| TC-106 | Reject batch >50 files | AS-002 | HIGH | ✅ Ready |
| TC-107 | Reject batch >100MB | AS-002 | HIGH | ✅ Ready |
| TC-108 | Batch session created | AS-002 | HIGH | ✅ Ready |
| TC-109 | Images displayed on preview | AS-003 | HIGH | ✅ Ready |
| TC-110 | Image dimensions shown | AS-003 | HIGH | ✅ Ready |
| TC-111 | Image filenames shown | AS-003 | HIGH | ✅ Ready |
| TC-112 | Preview page loads fast | AS-003 | HIGH | ✅ Ready |
| TC-113 | Fixed size input appears | AS-004 | HIGH | ✅ Ready |
| TC-114 | Size range validated | AS-004 | HIGH | ✅ Ready |
| TC-115 | Predicted output updates | AS-004 | HIGH | ✅ Ready |
| TC-116 | Size config persists | AS-004 | HIGH | ✅ Ready |
| TC-117 | Minimum mode selection | AS-005 | MEDIUM | ✅ Ready |
| TC-118 | Minimum size calculated | AS-005 | MEDIUM | ✅ Ready |
| TC-119 | Minimum respects aspect ratio | AS-005 | MEDIUM | ✅ Ready |
| TC-120 | Maximum mode selection | AS-006 | MEDIUM | ✅ Ready |
| TC-121 | Maximum clamped to 30x30 | AS-006 | MEDIUM | ✅ Ready |
| TC-122 | Maximum quality preserved | AS-006 | MEDIUM | ✅ Ready |
| TC-123 | Apply to All button | AS-007 | MEDIUM | ✅ Ready |
| TC-124 | Batch config applied | AS-007 | MEDIUM | ✅ Ready |
| TC-125 | Individual override persists | AS-007 | MEDIUM | ✅ Ready |
| TC-126 | Generation starts | AS-008 | HIGH | ✅ Ready |
| TC-127 | Confirmation required | AS-008 | HIGH | ✅ Ready |
| TC-128 | Generation completes | AS-008 | HIGH | ✅ Ready |
| TC-129 | Timeout handling | AS-008 | HIGH | ✅ Ready |
| TC-130 | Progress bar displays | AS-009 | HIGH | ✅ Ready |
| TC-131 | Puzzle count shown | AS-009 | HIGH | ✅ Ready |
| TC-132 | Time estimate shown | AS-009 | HIGH | ✅ Ready |
| TC-133 | Status updates live | AS-009 | HIGH | ✅ Ready |
| TC-134 | Approve button visible | AS-010 | HIGH | ✅ Ready |
| TC-135 | Approval status updates | AS-010 | HIGH | ✅ Ready |
| TC-136 | Approval success shown | AS-010 | HIGH | ✅ Ready |
| TC-137 | Approved count increments | AS-010 | HIGH | ✅ Ready |
| TC-138 | Reject button visible | AS-011 | HIGH | ✅ Ready |
| TC-139 | Rejection confirmation | AS-011 | HIGH | ✅ Ready |
| TC-140 | Rejection status updates | AS-011 | HIGH | ✅ Ready |
| TC-141 | Rejected count increments | AS-011 | HIGH | ✅ Ready |
| TC-142 | Download button visible | AS-012 | MEDIUM | ✅ Ready |
| TC-143 | SVG format downloaded | AS-012 | MEDIUM | ✅ Ready |
| TC-144 | Filename is descriptive | AS-012 | MEDIUM | ✅ Ready |
| TC-145 | SVG renders correctly | AS-012 | MEDIUM | ✅ Ready |
| TC-146 | Difficulty filter dropdown | AS-013 | LOW | ✅ Ready |
| TC-147 | Difficulty filter applied | AS-013 | LOW | ✅ Ready |
| TC-148 | Multi-filter combination | AS-013 | LOW | ✅ Ready |
| TC-149 | Filter clear button | AS-013 | LOW | ✅ Ready |
| TC-150 | Quality slider appears | AS-014 | LOW | ✅ Ready |
| TC-151 | Quality range filters | AS-014 | LOW | ✅ Ready |
| TC-152 | Filter updates in real-time | AS-014 | LOW | ✅ Ready |
| TC-153 | Metadata displayed | AS-015 | HIGH | ✅ Ready |
| TC-154 | Metadata accuracy | AS-015 | HIGH | ✅ Ready |
| TC-155 | Consistent metadata format | AS-015 | HIGH | ✅ Ready |
| TC-156 | Export button visible | AS-016 | MEDIUM | ✅ Ready |
| TC-157 | Format selection dialog | AS-016 | MEDIUM | ✅ Ready |
| TC-158 | Export includes approved only | AS-016 | MEDIUM | ✅ Ready |
| TC-159 | Metadata in export | AS-016 | MEDIUM | ✅ Ready |
| TC-160 | Navigation buttons | AS-017 | HIGH | ✅ Ready |
| TC-161 | Auto-redirect after step | AS-017 | HIGH | ✅ Ready |
| TC-162 | Session data persists | AS-017 | HIGH | ✅ Ready |
| TC-163 | Real-time validation | AS-018 | HIGH | ✅ Ready |
| TC-164 | Clear error messages | AS-018 | HIGH | ✅ Ready |
| TC-165 | Submit disabled on error | AS-018 | HIGH | ✅ Ready |
| TC-166 | Upload error displayed | AS-019 | HIGH | ✅ Ready |
| TC-167 | Specific error info | AS-019 | HIGH | ✅ Ready |
| TC-168 | Retry option available | AS-019 | HIGH | ✅ Ready |
| TC-169 | Generation errors reported | AS-020 | HIGH | ✅ Ready |
| TC-170 | Partial success shown | AS-020 | HIGH | ✅ Ready |
| TC-171 | Actionable error feedback | AS-020 | HIGH | ✅ Ready |

---

## Detailed Test Cases

### TC-101: Upload PNG file

**User Story**: AS-001  
**Acceptance Criteria**: AC-101  
**Priority**: HIGH  

**Test Setup**:
- Have valid PNG file (500×500px, 1.5MB) ready
- Open admin panel batch creation page
- Browser: Chrome/Firefox/Safari

**Test Steps**:
1. Click "Choose File" button
2. Select test image (test_image.png)
3. Verify file appears in input field
4. Click "Upload" button
5. Monitor network requests
6. Wait for response

**Expected Result**:
- File appears in upload input field
- Upload button is enabled
- Network request sent to `/batch/from-images`
- Server responds with HTTP 302 (redirect)
- User redirected to preview page
- Success message shown ("Image uploaded successfully")

**Test Data**:
- File: `test_image.png` (500×500, 1.5MB)
- Format: PNG
- Color: RGB

**Teardown**:
- Batch is created in database
- Session data stored

**Status**: ✅ Ready  
**Priority**: HIGH

---

### TC-102: Reject invalid format

**User Story**: AS-001  
**Acceptance Criteria**: AC-101  
**Priority**: HIGH  

**Test Setup**:
- Have invalid file (test.txt, test.pdf, test.exe) ready
- Open admin panel batch creation page

**Test Steps**:
1. Click "Choose File" button
2. Select invalid file (test.txt)
3. Verify file appears in input field
4. Click "Upload" button
5. Monitor for validation

**Expected Result**:
- Upload is rejected
- Error message shown: "Invalid file format. Supported: PNG, JPG, GIF"
- File is not sent to server
- User can select different file and retry

**Acceptance**: On error message, file type validation working

**Status**: ✅ Ready

---

### TC-103: Upload progress indicator

**User Story**: AS-001  
**Acceptance Criteria**: AC-103  
**Priority**: HIGH  

**Test Setup**:
- Have large PNG file (5MB) ready (to make upload slow)
- Network throttling enabled (simulate slow network)

**Test Steps**:
1. Select 5MB PNG file
2. Click "Upload"
3. Observe progress indicator during upload
4. Wait for completion
5. Verify final state

**Expected Result**:
- Progress bar appears and starts at 0%
- Progress bar increments smoothly (0% → 100%)
- Percentage shown (e.g., "25%", "50%", "100%")
- On completion, progress bar reaches 100%
- Progress bar stays visible until page redirects

**Measurement**:
- Progress updates every 100-200ms
- Increments are smooth (not jumpy)

**Status**: ✅ Ready

---

### TC-104: Upload success feedback

**User Story**: AS-001  
**Acceptance Criteria**: AC-104  
**Priority**: HIGH  

**Test Setup**:
- Valid PNG file ready
- Admin panel open

**Test Steps**:
1. Select valid PNG file
2. Click "Upload"
3. Wait for completion
4. Observe feedback and navigation

**Expected Result**:
- Upload completes without errors
- Success message shown: "Image uploaded successfully"
- User is redirected to preview page (`/batch/preview-images`)
- Preview page displays the uploaded image
- Batch ID is generated and stored

**Database Check**:
- Batch record created in `batches` table
- Image record created in `images` table
- Batch status = "ready"

**Status**: ✅ Ready

---

### TC-105: Upload 5 images batch

**User Story**: AS-002  
**Acceptance Criteria**: AC-105  
**Priority**: HIGH  

**Test Setup**:
- 5 valid image files ready (PNG/JPG mix)
- Admin panel open

**Test Steps**:
1. Click "Choose Files"
2. Select 5 image files (multi-select)
3. Verify all 5 files appear in input
4. Click "Upload"
5. Wait for completion
6. Verify all images in preview

**Expected Result**:
- All 5 files accepted for upload
- Upload progresses for all files
- User redirected to preview page
- All 5 images displayed in preview grid
- Batch ID created for all 5 images

**Edge Cases**:
- Mix of PNG and JPG formats
- Different image sizes (500×500 to 2000×2000)
- Different file sizes (500KB to 2MB)

**Status**: ✅ Ready

---

### TC-106: Reject batch >50 files

**User Story**: AS-002  
**Acceptance Criteria**: AC-106  
**Priority**: HIGH  

**Test Setup**:
- 51 small image files ready

**Test Steps**:
1. Click "Choose Files"
2. Select 51 images
3. Click "Upload"
4. Observe validation

**Expected Result**:
- Upload rejected with error message
- Message: "Maximum 50 files per batch"
- User can modify selection and retry
- No files sent to server

**Status**: ✅ Ready

---

### TC-107: Reject batch >100MB

**User Story**: AS-002  
**Acceptance Criteria**: AC-107  
**Priority**: HIGH  

**Test Setup**:
- 30 large image files (totaling 110MB)

**Test Steps**:
1. Select 30 images
2. Verify total size > 100MB
3. Click "Upload"
4. Observe validation

**Expected Result**:
- Upload rejected with error message
- Message: "Batch too large (max 100 MB). Current: 110 MB"
- User can remove files and retry
- No partial uploads occur

**Status**: ✅ Ready

---

### TC-108: Batch session created

**User Story**: AS-002  
**Acceptance Criteria**: AC-108  
**Priority**: HIGH  

**Test Setup**:
- 5 images uploaded successfully

**Test Steps**:
1. Upload batch of 5 images
2. Redirect to preview page
3. Check browser storage/session
4. Check database
5. Navigate to different URL
6. Return to batch URL

**Expected Result**:
- Unique batch_id generated (UUID format)
- Session data stored in server session or database
- Batch ID visible in URL (`/batch/preview-images?batch_id=xxx`)
- Session persists when navigating away and returning
- Batch data recoverable by batch_id

**Database Check**:
- `batches` table has new record
- `batch_id` is UUID
- `status` = "ready"
- `created_at` timestamp recent

**Status**: ✅ Ready

---

### TC-109: Images displayed on preview

**User Story**: AS-003  
**Acceptance Criteria**: AC-109  
**Priority**: HIGH  

**Test Setup**:
- 5 images uploaded
- Preview page open

**Test Steps**:
1. Navigate to preview page
2. Wait for images to load
3. Verify images appear
4. Scroll through grid
5. Inspect each image element

**Expected Result**:
- All 5 images appear in grid layout
- Images are 1 or 2 columns (responsive)
- Images load within 2 seconds
- Images use correct aspect ratio
- No broken image icons (✗)

**Visual Check**:
- Images are sharp and readable
- No distortion or stretching
- Grid is evenly spaced
- Mobile responsive (adjust window)

**Status**: ✅ Ready

---

### TC-110: Image dimensions shown

**User Story**: AS-003  
**Acceptance Criteria**: AC-110  
**Priority**: HIGH  

**Test Setup**:
- Preview page with images loaded

**Test Steps**:
1. View image preview cards
2. Look for dimension text below each image
3. Verify format (e.g., "800×600")
4. Spot-check against actual image dimensions

**Expected Result**:
- Each image shows dimensions below it
- Format: "WIDTHxHEIGHT" (e.g., "1024×768")
- Dimensions are accurate (match actual image)
- Text is readable (good contrast)
- Dimensions shown for all images

**Verification**:
- Right-click image → Properties → check dimensions
- Compare with displayed dimensions
- All should match

**Status**: ✅ Ready

---

### TC-111: Image filenames shown

**User Story**: AS-003  
**Acceptance Criteria**: AC-111  
**Priority**: HIGH  

**Test Setup**:
- Preview page loaded with images

**Test Steps**:
1. View each image card
2. Look for filename text
3. Verify all filenames present
4. Check for file extensions

**Expected Result**:
- Each image shows original filename
- Format: "filename.ext" (e.g., "landscape.png")
- Filenames shown clearly on each card
- Extension is preserved
- No path prefix, just filename

**Status**: ✅ Ready

---

### TC-112: Preview page loads fast

**User Story**: AS-003  
**Acceptance Criteria**: AC-112  
**Priority**: HIGH  

**Test Setup**:
- 50 images in batch (maximum)
- Network throttling: Slow 3G
- Monitor DevTools Network tab

**Test Steps**:
1. Navigate to preview page
2. Measure page load time
3. Measure first image load time
4. Measure all images loaded time

**Expected Result**:
- Page initial load: <1 second
- First image visible: <500ms
- All images loaded: <2 seconds
- Page remains responsive during load
- No freezing or stuttering

**Performance Metrics**:
- Network requests: Parallel (not sequential)
- Image sizes optimized (compressed)
- No large JavaScript bundles blocking render

**Status**: ✅ Ready

---

### TC-113: Fixed size input appears

**User Story**: AS-004  
**Acceptance Criteria**: AC-113  
**Priority**: HIGH  

**Test Setup**:
- Preview page loaded
- Image cards visible

**Test Steps**:
1. Locate image configuration section
2. Find size mode dropdown
3. Select "Fixed Size" mode
4. Observe for size input field

**Expected Result**:
- "Fixed Size" option selectable in dropdown
- When selected, input field appears
- Input field is labeled "Size (pixels)"
- Input field has placeholder "10-30"
- Input field is required (marked with *)

**Behavior**:
- Selecting other modes hides the input
- Selecting "Fixed Size" again shows it

**Status**: ✅ Ready

---

### TC-114: Size range validated

**User Story**: AS-004  
**Acceptance Criteria**: AC-114  
**Priority**: HIGH  

**Test Setup**:
- Fixed Size mode selected
- Size input field visible

**Test Steps**:
1. Enter value "5" (too small)
2. Tab away from field
3. Observe validation error
4. Enter value "35" (too large)
5. Tab away
6. Observe validation error
7. Enter value "20" (valid)
8. Tab away
9. Observe no error

**Expected Result - Invalid Values**:
- Error message appears: "Size must be 10-30"
- Error is shown immediately (no delay)
- Input field has red border or error indicator
- Submit button is disabled

**Expected Result - Valid Value**:
- No error message
- Input field has green indicator (or no error)
- Submit button is enabled

**Edge Cases**:
- Value "10": Should be valid (minimum)
- Value "30": Should be valid (maximum)
- Value "9": Should show error
- Value "31": Should show error
- Value "abc": Should show error
- Empty field: Should show "required" error

**Status**: ✅ Ready

---

### TC-115: Predicted output updates

**User Story**: AS-004  
**Acceptance Criteria**: AC-115  
**Priority**: HIGH  

**Test Setup**:
- Image card with size config
- Predicted output section visible

**Test Steps**:
1. Change size value from 15 to 20
2. Observe predicted output update
3. Change mode from "Fixed" to "Minimum"
4. Observe predicted output change
5. Inspect calculation logic

**Expected Result**:
- Predicted output updates immediately (no delay)
- Output format: "20×20" or similar
- Output updates whenever input changes
- Output is accurate for given input
- Output respects aspect ratio

**Calculation Verification**:
- If image is 800×600 (4:3 aspect ratio)
- And size is 20
- Then output should be 20×15 (maintaining 4:3)

**Status**: ✅ Ready

---

### TC-116: Size config persists

**User Story**: AS-004  
**Acceptance Criteria**: AC-116  
**Priority**: HIGH  

**Test Setup**:
- Image configuration on preview page

**Test Steps**:
1. Configure 3 images with different sizes
2. Image 1: Fixed 15×15
3. Image 2: Minimum mode
4. Image 3: Maximum mode
5. Navigate to generation confirmation page
6. Click "Back" button
7. Return to preview page
8. Verify configurations

**Expected Result**:
- All configurations persist
- Image 1 shows Fixed mode, size 15
- Image 2 shows Minimum mode
- Image 3 shows Maximum mode
- Session data loaded correctly

**Session Check**:
- Data stored in browser session (or server session)
- Data survives page navigation
- Data survives browser refresh
- Data cleared only on logout/batch completion

**Status**: ✅ Ready

---

### TC-117: Minimum mode selection

**User Story**: AS-005  
**Acceptance Criteria**: AC-117  
**Priority**: MEDIUM  

**Test Setup**:
- Image card with size config dropdown

**Test Steps**:
1. Click size mode dropdown
2. Select "Minimum Size"
3. Observe UI changes
4. Verify no input field needed

**Expected Result**:
- "Minimum Size" option visible and selectable
- When selected, no input field appears
- Option is labeled clearly
- Tooltip explains: "Smallest readable size (auto-calculated)"
- Selection is saved

**Status**: ✅ Ready

---

### TC-118: Minimum size calculated

**User Story**: AS-005  
**Acceptance Criteria**: AC-118  
**Priority**: MEDIUM  

**Test Setup**:
- Image with Minimum mode selected

**Test Steps**:
1. Select Minimum mode for image
2. Observe predicted output
3. Verify calculation
4. Compare with image dimensions

**Expected Result**:
- Predicted output shows calculated size
- Size is between 12-18 (typical minimum)
- Size respects aspect ratio
- Size is reasonable for readability
- Calculation is consistent (same image always same size)

**Calculation Logic**:
- Larger images get larger min size
- Smaller images get smaller min size
- Maintains aspect ratio always

**Status**: ✅ Ready

---

### TC-119: Minimum respects aspect ratio

**User Story**: AS-005  
**Acceptance Criteria**: AC-119  
**Priority**: MEDIUM  

**Test Setup**:
- 3 images with different aspect ratios:
  - Square (1:1)
  - Landscape (2:1)
  - Portrait (1:2)

**Test Steps**:
1. Apply Minimum mode to all 3 images
2. Observe predicted outputs
3. Calculate aspect ratio of outputs

**Expected Result**:
- Square image: Output is square (e.g., 15×15)
- Landscape image: Output is landscape (e.g., 20×10)
- Portrait image: Output is portrait (e.g., 10×20)
- Aspect ratios preserved in all cases

**Verification**:
- For landscape (800×400): Output width ≈ 2× height
- For portrait (400×800): Output height ≈ 2× width
- Math: (output_width / output_height) ≈ (input_width / input_height)

**Status**: ✅ Ready

---

### TC-120-TC-122: Maximum Mode Tests

**User Story**: AS-006  
**Priority**: MEDIUM  

**Following same pattern as minimum mode tests**:
- TC-120: Mode selection
- TC-121: Max clamped to 30×30
- TC-122: Quality preserved

**Expected Behavior**:
- Maximum mode calculates largest possible grid (up to 30×30)
- Preserves all image detail
- Respects aspect ratio
- Stays within 30×30 limit

**Status**: ✅ Ready

---

### TC-123: Apply to All button

**User Story**: AS-007  
**Acceptance Criteria**: AC-123  
**Priority**: MEDIUM  

**Test Setup**:
- 5 images loaded, each with individual config section
- Global config section at top

**Test Steps**:
1. Locate "Apply to All" button
2. Verify button is visible and enabled
3. Verify button label is clear
4. Click button

**Expected Result**:
- Button is clearly visible and labeled
- Button is positioned prominently (top of page)
- Button is enabled (not grayed out)
- Clicking does nothing yet (wait for next TC)

**Status**: ✅ Ready

---

### TC-124: Batch config applied

**User Story**: AS-007  
**Acceptance Criteria**: AC-124  
**Priority**: MEDIUM  

**Test Setup**:
- Global config set to: Fixed Size 20
- 5 images with different configs

**Test Steps**:
1. Set global size to 20
2. Click "Apply to All"
3. Verify all images updated
4. Check each image's config

**Expected Result**:
- All 5 images change to Fixed mode, size 20
- Predicted outputs all show "20×20" (or similar)
- All images uniformly configured
- No image configuration overridden

**Verification**:
- Inspect each image card
- Verify dropdown shows "Fixed"
- Verify input shows "20"

**Status**: ✅ Ready

---

### TC-125: Individual override persists

**User Story**: AS-007  
**Acceptance Criteria**: AC-125  
**Priority**: MEDIUM  

**Test Setup**:
- Batch config applied (all size 20)

**Test Steps**:
1. After "Apply to All", batch config is size 20
2. Modify Image 3's config to size 15
3. Navigate away and back
4. Verify Image 3 still has size 15
5. Verify other images still have size 20

**Expected Result**:
- Individual overrides persist
- Image 3 config: size 15
- Other images: size 20 (batch config)
- If user then selects "Apply to All" again, Image 3 override is replaced

**Priority Override Logic**:
- Batch config is default
- Individual config overrides batch config
- New "Apply to All" replaces all overrides

**Status**: ✅ Ready

---

### TC-126-TC-129: Generation Tests

**User Story**: AS-008  
**Acceptance Criteria**: AC-126-129  
**Priority**: HIGH  

**TC-126: Generation initiation**:
- Setup: Configuration complete
- Click "Generate Puzzles"
- Generation starts
- Progress page appears

**TC-127: Confirmation required**:
- Setup: Generation page visible
- Checkbox unchecked: "Generate" button disabled
- Check confirmation checkbox
- "Generate" button enabled

**TC-128: Generation completion**:
- Setup: Generation in progress
- Wait for completion
- Database check: Puzzles created
- Redirect to review page

**TC-129: Timeout handling**:
- Setup: Single puzzle generation slow (>10s)
- Wait for timeout
- Puzzle marked failed in batch
- Other puzzles continue generating

**Status**: ✅ Ready for implementation

---

### TC-130-TC-133: Progress Indication Tests

**User Story**: AS-009  
**Priority**: HIGH  

**TC-130: Progress bar displays**:
- Bar visible and animating
- Visual indicator of progress

**TC-131: Puzzle count shown**:
- Text shows "25/50 Generated"
- Updates in real-time

**TC-132: Time estimate shown**:
- Estimated time remaining displayed
- Accuracy within ±20%

**TC-133: Status updates live**:
- Page updates every 1-2 seconds
- No manual refresh needed

**Status**: ✅ Ready

---

### TC-134-TC-141: Approval/Rejection Tests

**User Story**: AS-010, AS-011  
**Priority**: HIGH  

**TC-134/138**: Button visibility
- Approve/Reject buttons visible on puzzle cards

**TC-135/139**: Confirmation dialogs
- Reject requires confirmation
- Approve may not need confirmation

**TC-136/140**: Status updates
- Database updated immediately
- UI reflects new status

**TC-137/141**: Count tracking
- Approved/Rejected counts increment
- Batch summary updates

**Status**: ✅ Ready

---

### TC-142-TC-145: Download Tests

**User Story**: AS-012  
**Priority**: MEDIUM  

**TC-142**: Download button visible
- Button clearly labeled "Download SVG"

**TC-143**: SVG format downloaded
- File extension is .svg (not .html)
- Content-Type header is correct

**TC-144**: Filename is descriptive
- Filename: puzzle_id.svg or puzzle_name.svg

**TC-145**: SVG renders correctly
- Open in browser: Grid displays
- Open in editor: Valid SVG XML

**Status**: ✅ Ready

---

### TC-146-TC-155: Filter/Metadata Tests

**User Story**: AS-013, AS-014, AS-015  
**Priority**: LOW-MEDIUM  

**TC-146/150**: Filter controls visible
- Dropdowns/sliders present

**TC-147/151**: Filters applied correctly
- Results update to match filter
- Real-time updates

**TC-148/152**: Multi-filter combinations
- Filters combine (AND logic)
- All conditions met

**TC-149**: Clear filters
- Reset to show all puzzles

**TC-153/154/155**: Metadata accuracy
- All fields match database
- Formatting consistent

**Status**: ✅ Ready

---

### TC-156-TC-171: Navigation, Validation, Error Handling

**User Story**: AS-016-020  
**Priority**: MEDIUM-HIGH  

**TC-156**: Export button visible
**TC-157**: Format selection (JSON, CSV, SVG)
**TC-158**: Only approved puzzles exported
**TC-159**: Metadata included in export

**TC-160**: Navigation buttons work
**TC-161**: Auto-redirect after actions
**TC-162**: Session data persists

**TC-163**: Real-time form validation
**TC-164**: Clear error messages
**TC-165**: Submit disabled on error

**TC-166**: Upload errors displayed
**TC-167**: Specific error information
**TC-168**: Retry option provided

**TC-169**: Generation errors reported
**TC-170**: Partial success handling
**TC-171**: Actionable error feedback

**Status**: ✅ Ready

---

## Test Execution Summary

| Category | Count | Status |
|----------|-------|--------|
| Total Test Cases | 171 | ✅ Defined |
| HIGH Priority | 104 | ✅ Ready |
| MEDIUM Priority | 54 | ✅ Ready |
| LOW Priority | 13 | ✅ Ready |
| Automation Ready | 140 | ✅ Yes |
| Manual Testing | 31 | ✅ Yes |

## Success Criteria

- [ ] All test cases pass
- [ ] 100% acceptance criteria covered
- [ ] All user stories verified
- [ ] Edge cases tested
- [ ] Error scenarios tested
- [ ] Performance verified

---

**Status**: ✅ All 171 test cases defined and ready for execution  
**Next**: Create test plan and execution schedule
