# Wave 3: Image-Based Batch Generation - Acceptance Tests

## Test Scope
- CARD-004o: Batch UI Refactor (5pt)
- CARD-004p: Image Selection & Upload (8pt)
- CARD-004q: Preview & Size Selection (13pt)
- CARD-004r: Generate Puzzles from Images (13pt)
- CARD-004s: Show Source Images in Preview (8pt)

## Test Setup
- Flask running: `http://localhost:8000`
- Test images: `/Users/omelnikova/PycharmProjects/PythonProject4/silhouette/animals/`
- Test data: 5 PNG silhouette images (snail, dolphins, panda, tiger, elephant)

---

## AC-001: File Upload Form (CARD-004o)

### Acceptance Criteria
- [ ] Page `/batch/create` displays with title "Create Batch from Images"
- [ ] Form has two input options visible simultaneously:
  - [ ] "Choose Image Files" (file picker)
  - [ ] "Choose Directory" (directory picker)
- [ ] Size option dropdown visible with 4 options (Small/Medium/Large/Auto)
- [ ] Quality filter input visible (0-100)
- [ ] Submit button labeled "Next: Preview Images"

### Test Steps
1. Navigate to `http://localhost:8000/batch/create`
2. Verify all form elements present and visible
3. Check dropdown shows size options
4. Verify both file inputs visible

### Expected Result
All form elements render correctly. No errors in console.

---

## AC-002: File Upload and Validation (CARD-004p)

### Acceptance Criteria
- [ ] Users can select single or multiple image files
- [ ] Users can select a directory of images
- [ ] Users can select both files AND directory simultaneously
- [ ] System validates file formats (PNG, JPG, GIF only)
- [ ] System validates file size (max 2MB per image)
- [ ] Success message shows count of uploaded images
- [ ] User redirected to `/batch/select-images` after upload

### Test Steps
1. On `/batch/create`, click "Choose Image Files"
2. Select 3 PNG files from silhouette folder
3. Select "Choose Directory" and pick a folder
4. Click "Next: Preview Images"
5. Verify redirect to image selection page

### Expected Result
✓ Files uploaded successfully
✓ Redirect to `/batch/select-images` with success message
✓ Image count displayed

---

## AC-003: Image Selection Display (CARD-004p)

### Acceptance Criteria
- [ ] Page displays at `/batch/select-images`
- [ ] Title shows "Batch: Select Images"
- [ ] All uploaded images displayed in grid
- [ ] Each image shows:
  - [ ] Visual preview (actual image or placeholder)
  - [ ] Filename
  - [ ] Format (PNG/JPG/GIF)
  - [ ] File size in KB
  - [ ] Remove button (×)
- [ ] Total image count displayed
- [ ] Total file size in MB displayed
- [ ] Size preset buttons visible (S/M/L)
- [ ] "Clear All" button present
- [ ] "Next: Configure Sizes" button present
- [ ] "Back to Selection" link present

### Test Steps
1. Verify page loaded after upload
2. Count images displayed matches uploaded count
3. Check each image shows all metadata
4. Verify buttons and navigation elements present

### Expected Result
✓ All images listed with complete metadata
✓ All UI elements present and functional

---

## AC-004: Size Configuration (CARD-004q)

### Acceptance Criteria
- [ ] Page displays at `/batch/preview-images`
- [ ] Title shows "Batch: Preview Images & Select Sizes"
- [ ] Each image shows:
  - [ ] Image preview (actual or placeholder)
  - [ ] Editable puzzle name field
  - [ ] Size mode dropdown (Fixed/Min/Max)
  - [ ] Size value input (10-30, visible only when Fixed selected)
  - [ ] Predicted output size display
- [ ] Global size controls present:
  - [ ] Size mode dropdown (Fixed/Min/Max)
  - [ ] Fixed size input (conditional)
  - [ ] "Apply to All" button
- [ ] Summary sidebar shows:
  - [ ] Image count
  - [ ] Total data size
  - [ ] Size mode explanations
- [ ] "Next: Generate Puzzles" button present
- [ ] "Back to Images" button present

### Test Steps
1. After image selection, should auto-redirect to preview page
2. Verify all images loaded with controls
3. Change size mode for first image to Min
4. Try Apply to All with Medium size
5. Edit puzzle name for one image
6. Click "Next: Generate Puzzles"

### Expected Result
✓ Size configuration options work
✓ Apply to All updates all images
✓ Puzzle names editable
✓ Redirect to generation step

---

## AC-005: Batch Generation Confirmation (CARD-004r)

### Acceptance Criteria
- [ ] Page displays at `/batch/generate`
- [ ] Title shows "Generate Puzzles from Images"
- [ ] Configuration summary shows:
  - [ ] Each image with filename
  - [ ] Image dimensions (e.g., 512×512px)
  - [ ] Predicted puzzle size (e.g., 20×20 grid)
  - [ ] Size mode (fixed/min/max)
- [ ] Confirmation checkbox: "I'm ready to generate puzzles..."
- [ ] Generate button disabled until checkbox checked
- [ ] Generate button shows "⚡ Generate X Puzzle(s)"
- [ ] "Back to Images" button present
- [ ] Summary sidebar shows:
  - [ ] Number of source images
  - [ ] Total data size
  - [ ] Output format info

### Test Steps
1. Verify confirmation page loaded
2. Check configuration summary is accurate
3. Attempt to click Generate (should be disabled)
4. Check checkbox
5. Click Generate button
6. Monitor for redirect to batch status page

### Expected Result
✓ Configuration summary accurate
✓ Button disabled until confirmed
✓ Generation initiated after confirmation

---

## AC-006: Batch Generation and Status (CARD-004r)

### Acceptance Criteria
- [ ] Redirects to `/batch/{batch_id}` page
- [ ] Page title shows "Batch: {batch_id}"
- [ ] Status badge shows "COMPLETE" (green)
- [ ] Progress bar shows 100%
- [ ] Progress shows "X / X" (total/completed)
- [ ] Stats section shows:
  - [ ] Total images processed
  - [ ] Completed count
  - [ ] Generated puzzles count
- [ ] Success message: "Generated X puzzle(s) from Y image(s)"
- [ ] Timestamps shown (Created, Last Updated)

### Test Steps
1. Monitor page after Generate button clicked
2. Verify status shows COMPLETE
3. Check progress bar is 100%
4. Verify all stats displayed correctly

### Expected Result
✓ Batch job created successfully
✓ Status shows COMPLETE with 100% progress
✓ All statistics accurate

---

## AC-007: Puzzle Review with Source Images (CARD-004s)

### Acceptance Criteria
- [ ] Generated puzzles section displays
- [ ] Each puzzle card shows:
  - [ ] Purple grid visualization with size (e.g., "20×20")
  - [ ] Source image indicator (📷 + filename)
  - [ ] Puzzle ID
  - [ ] Difficulty badge (Easy/Medium/Hard with color)
  - [ ] Quality score (0-100)
  - [ ] "From: {source_image_name}" text
  - [ ] Approve button (✓ green)
  - [ ] Reject button (✕ red)
- [ ] Batch actions section shows:
  - [ ] "Approve All" button
  - [ ] "Download Batch" button
  - [ ] "View Details" link
- [ ] Navigation shows:
  - [ ] "View Puzzles" button
  - [ ] "Back to Dashboard" button

### Test Steps
1. Verify puzzles grid displays after generation
2. Check each puzzle shows all required information
3. Verify source image name correctly displayed
4. Try clicking Approve/Reject buttons
5. Check batch action buttons present

### Expected Result
✓ All puzzles displayed with complete information
✓ Source images correctly linked
✓ Approve/Reject buttons functional

---

## AC-008: Navigation and State (CARD-004r + others)

### Acceptance Criteria
- [ ] Forward navigation works: Create → Select → Configure → Generate → Review
- [ ] Each step preserves data from previous step
- [ ] Back buttons work (return to previous page)
- [ ] Going back and resubmitting doesn't duplicate data
- [ ] Session data persists across page navigation
- [ ] Error messages display clearly for validation failures
- [ ] Flash messages show success/error feedback

### Test Steps
1. Test forward flow: Upload → Select → Configure → Generate
2. Click back buttons at each step
3. Verify data preserved when going back
4. Re-upload same images and verify no duplication
5. Try submitting form without selecting files (should show error)

### Expected Result
✓ Navigation works in both directions
✓ Data preserved across steps
✓ No data duplication
✓ Error handling works

---

## AC-009: Image Storage and Retrieval

### Acceptance Criteria
- [ ] Uploaded images stored securely in temp directory
- [ ] Image metadata tracked:
  - [ ] File ID (unique)
  - [ ] Original filename
  - [ ] File size
  - [ ] Dimensions (width × height)
  - [ ] Format (PNG/JPG/GIF)
- [ ] Images retrievable throughout workflow
- [ ] Images cleaned up after batch completion

### Test Steps
1. Upload images and verify stored
2. Navigate through workflow and verify images accessible
3. Check image IDs are unique
4. Verify image properties match source files

### Expected Result
✓ All images stored with correct metadata
✓ Images accessible throughout workflow

---

## AC-010: Puzzle Generation Logic

### Acceptance Criteria
- [ ] Each image generates exactly 1 puzzle
- [ ] Puzzle size matches configuration:
  - [ ] Fixed mode: uses specified size (10-30)
  - [ ] Min mode: calculates minimum readable size
  - [ ] Max mode: calculates maximum quality size
- [ ] Puzzle linked to source image
- [ ] Puzzle linked to batch ID
- [ ] Quality score assigned (0-100)
- [ ] Difficulty tier assigned (Easy/Medium/Hard)

### Test Steps
1. Generate puzzles from images with different size modes
2. Verify puzzle counts match image counts
3. Check puzzle sizes correct for each mode
4. Verify source image names in results
5. Check quality and difficulty scores assigned

### Expected Result
✓ 1 puzzle per image generated
✓ Sizes calculated correctly
✓ Source tracking accurate
✓ Metrics assigned properly

---

## Test Execution Matrix

| AC # | Feature | Status | Notes |
|------|---------|--------|-------|
| AC-001 | Form Display | TBD | Testing now |
| AC-002 | File Upload | TBD | Testing now |
| AC-003 | Image Selection | TBD | Testing now |
| AC-004 | Size Configuration | TBD | Testing now |
| AC-005 | Generation Confirmation | TBD | Testing now |
| AC-006 | Batch Status | TBD | Testing now |
| AC-007 | Puzzle Review | TBD | Testing now |
| AC-008 | Navigation | TBD | Testing now |
| AC-009 | Image Storage | TBD | Testing now |
| AC-010 | Generation Logic | TBD | Testing now |

---

## Known Issues Tracked

| Issue | AC Affected | Severity | Status |
|-------|------------|----------|--------|
| Image previews show placeholder | AC-003, AC-007 | Low | Open |
| Size options may be below fold | AC-001, AC-004 | Low | Open |
| Back navigation clears selections | AC-008 | Medium | Open |

---

## Sign-off

- [ ] All ACs verified as PASS
- [ ] No blockers found
- [ ] Ready for production

**Date Tested:** TBD
**Tester:** Claude
**Result:** TBD
