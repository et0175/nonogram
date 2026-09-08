# Wave 3: Image Preview with Size Selection - Acceptance Criteria
**Based on CARD-004q requirements**

**Target Page:** `/batch/preview-images`  
**Purpose:** Allow users to preview uploaded images and individually configure puzzle size before generation

---

## AC-001: Page Layout and Display

- [ ] Page loads at `/batch/preview-images` with title "Batch: Preview Images & Select Sizes"
- [ ] **Subtitle:** "Configure puzzle size for each image (Fixed, Min, or Max)"
- [ ] Page displays all uploaded images from previous step
- [ ] Images arranged in grid layout (responsive, 1-2 columns based on viewport)
- [ ] For each image, show:
  - [ ] **Image preview** - actual cropped preview thumbnail (150×150px or similar square)
  - [ ] **Filename** - displayed above or below preview
  - [ ] **Original dimensions** - shown as "W×H" (e.g., "1200×800")
  - [ ] **Puzzle name field** - editable text field, default: filename without extension
  - [ ] **Size controls** - dropdown + input field + output prediction
  - [ ] **Action buttons** - Approve/Remove buttons (per image)

---

## AC-002: Image Preview Display (Critical Issue)

- [ ] **MUST SHOW ACTUAL IMAGE** (not placeholder)
- [ ] Previews display the actual uploaded image file
- [ ] If image can't be loaded, show placeholder with error message
- [ ] Cropped to square aspect ratio (150×150 or 200×200)
- [ ] Images use object-fit: cover to maintain aspect ratio
- [ ] Fallback: If image serving unavailable, show dimension/format info with 📷 icon

### Implementation Note
**Current Issue:** Previews show 🖼️ placeholder instead of actual image  
**Root Cause:** Image files stored in temp directory not being served  
**Solution Needed:**
- Create image serving endpoint: `/images/<file_id>` 
- Serve images with proper MIME type
- Or embed as base64 data URIs
- Ensure CORS/security handling

---

## AC-003: Puzzle Name Editing

- [ ] Editable text field for each image
- [ ] Default value: image filename without extension (e.g., "vacation_photo_001")
- [ ] User can change name for generated puzzle
- [ ] Name changes persisted through workflow
- [ ] Name validation: allow alphanumeric, underscores, hyphens
- [ ] Display character count or length limit

---

## AC-004: Individual Size Configuration

### Size Mode Selector
- [ ] Dropdown for each image with three options:
  - [ ] **"Fixed Size"** - User specifies exact size (10-30)
  - [ ] **"Minimum Size"** - Auto-calculates minimum readable size
  - [ ] **"Maximum Size"** - Auto-calculates max size preserving quality

### Fixed Size Mode
- [ ] When "Fixed Size" selected, show number input field
- [ ] Input range: 10-30 (cells per side)
- [ ] Input labeled "Size Value" or "Cells Per Side"
- [ ] Real-time validation: show error if outside range
- [ ] Default value: 20

### Min/Max Size Modes
- [ ] When "Minimum" or "Maximum" selected, hide number input
- [ ] Display calculated size inline or in preview section
- [ ] Show how calculation was determined (e.g., "Based on: 1200×800px image")

### Output Prediction
- [ ] Display predicted puzzle size below controls
- [ ] Format: "Output: 20×20 grid" or "Predicted: 20×20 cells"
- [ ] Real-time update as user changes mode/value
- [ ] Color coding:
  - [ ] Green: Valid (10-30 range)
  - [ ] Red: Invalid (outside range)
  - [ ] Yellow: Warning (e.g., very small or very large)

---

## AC-005: Apply to All Functionality

- [ ] **"Apply to All" button** - applies same size to all images at once
- [ ] Button location: in global controls section at top
- [ ] When clicked:
  - [ ] Reads current image's size mode and value
  - [ ] Applies to ALL images in the batch
  - [ ] Updates all preview predictions
  - [ ] Shows confirmation message (optional)
- [ ] Individual images can still be changed after "Apply to All"

---

## AC-006: Global Size Controls (Optional/Summary)

- [ ] Summary section shows batch statistics:
  - [ ] Total images: N
  - [ ] Size mode distribution (e.g., "2 Fixed, 1 Min, 2 Max")
  - [ ] Predicted output sizes
- [ ] Info section explains size modes:
  - [ ] "Fixed: Set exact size (10-30)"
  - [ ] "Min: Smallest readable size"
  - [ ] "Max: Best quality preserving image detail"

---

## AC-007: Size Prediction Algorithm

**Must match CARD-004q specification:**

```
Min size: 10 cells (absolute minimum)
Max size: min(width÷2, height÷2, 30)
  - Rule: at least 2 pixels per cell
  - Absolute max: 30 cells

Examples:
- 512×512px image:
  - Min: 10 (hardcoded minimum)
  - Max: min(512÷2, 512÷2, 30) = min(256, 256, 30) = 30
  - Fixed: user value (e.g., 20)

- 1200×800px image:
  - Min: 10
  - Max: min(1200÷2, 800÷2, 30) = min(600, 400, 30) = 30
  - Fixed: user value

- 400×300px image:
  - Min: 10
  - Max: min(400÷2, 300÷2, 30) = min(200, 150, 30) = 30
  - Fixed: user value

- 256×256px image:
  - Min: 10
  - Max: min(256÷2, 256÷2, 30) = min(128, 128, 30) = 30
  - Fixed: user value (but 10-30 range enforced)
```

---

## AC-008: Validation and Error Handling

- [ ] **Size validation:**
  - [ ] Fixed mode: value must be 10-30
  - [ ] Show error badge or message if outside range
  - [ ] Invalid sizes prevent generation
  
- [ ] **No size set:**
  - [ ] Default to "Fixed: 20" for all images
  - [ ] Show default values clearly

- [ ] **Missing image:**
  - [ ] Show error state (e.g., "Image not found")
  - [ ] Don't allow generation of batch with missing images

---

## AC-009: Navigation and State Preservation

- [ ] **"Next: Generate Puzzles" button** - proceeds to confirmation page
- [ ] **"Back to Images" link** - returns to image selection page
  - [ ] Preserves size configurations in session
  - [ ] User can return and modify sizes again
  - [ ] Back navigation doesn't clear settings

- [ ] **Generate button state:**
  - [ ] Enabled only if:
    - [ ] All images have valid sizes
    - [ ] All sizes in 10-30 range
    - [ ] All images still accessible
  - [ ] Disabled with tooltip if validation fails
  - [ ] Disabled message explains why

---

## AC-010: User Experience - Clarity

- [ ] **Clear labeling:**
  - [ ] "Default Puzzle Size" on creation form (page 1)
  - [ ] "Puzzle Size" for each image (page 2)
  - [ ] "Output:" or "Predicted:" for preview calculations

- [ ] **Visual hierarchy:**
  - [ ] Image preview prominent (largest visual element per image)
  - [ ] Size controls clearly grouped together
  - [ ] Apply to All button visually distinct

- [ ] **Responsive design:**
  - [ ] Mobile: single column layout
  - [ ] Tablet: 1-2 columns
  - [ ] Desktop: 2-3 columns
  - [ ] Controls stack vertically below each image

---

## Test Scenarios

### Scenario 1: Fixed Size for All Images
```
Given: 3 images (512×512, 1200×800, 800×600)
When: User selects "Fixed Size" and enters "15"
And: Clicks "Apply to All"
Then: All 3 images show "Output: 15×15"
And: All have Fixed mode selected with value 15
```

### Scenario 2: Individual Customization
```
Given: 3 images
When: Image 1: Fixed 15
And: Image 2: Min (calculates to 10)
And: Image 3: Max (calculates to 30)
Then: Preview shows: 15×15, 10×10, 30×30
And: All are valid (green status)
And: Generate button enabled
```

### Scenario 3: Invalid Size
```
Given: Image with size set to 35
When: User views output prediction
Then: Shows "Output: 35×35 (INVALID - max 30)"
And: Error badge appears
And: Generate button becomes disabled
And: Tooltip: "Size must be 10-30"
```

### Scenario 4: Edit Puzzle Names
```
Given: Image "vacation_photo_001.jpg"
When: User changes name to "beach_sunset_2024"
Then: Puzzle will be stored with name "beach_sunset_2024"
And: Previous name "vacation_photo_001" not used
```

### Scenario 5: Back Navigation Preserves Settings
```
Given: User configured sizes on page 2
When: Clicks "Back to Images"
And: Adds/removes images
And: Returns to page 2
Then: Previous size settings preserved for same images
```

---

## UI Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────┐
│ Batch: Preview Images & Select Sizes                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Global Size Controls (Optional):                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Apply size to all images:                          │ │
│ │ [Fixed ▼] [20 _______] [Apply to All]             │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ Image 1: vacation.jpg (1200×800)                        │
│ ┌──────────┐  Puzzle Name: [vacation_______]            │
│ │          │  Size: [Fixed ▼] [20 _______]              │
│ │  [Image] │  → Output: 20×20 grid                      │
│ │ Thumb    │                                            │
│ └──────────┘                                            │
│                                                         │
│ Image 2: sunset.jpg (512×512)                           │
│ ┌──────────┐  Puzzle Name: [sunset________]             │
│ │          │  Size: [Min ▼]                             │
│ │  [Image] │  → Output: 10×10 grid (predicted)         │
│ │ Thumb    │                                            │
│ └──────────┘                                            │
│                                                         │
│ [◄ Back to Images] [Next: Generate Puzzles ▶]          │
└─────────────────────────────────────────────────────────┘
```

---

## Files Affected

- `src/nonogram/admin/templates/image_preview.html`
- `src/nonogram/admin/app.py` (route `/batch/preview-images`)
- `src/nonogram/admin/image_manager.py` (size prediction)
- `src/nonogram/admin/static/` (image serving, CSS styling)

---

## Issues to Fix

### Issue 1: Image Preview Shows Placeholder (🖼️) Instead of Actual Image
**Severity:** HIGH (User feedback indicated)  
**Status:** Needs fix  
**Solution:** Implement image serving endpoint

### Issue 2: Size Controls May Not Be Clear for Individual Configuration
**Severity:** MEDIUM  
**Status:** Improve UX  
**Solution:** Better visual grouping and labeling per image

### Issue 3: Size Algorithm Verification
**Severity:** MEDIUM  
**Status:** Verify against requirements  
**Solution:** Ensure max_size calculation matches spec

---

## Sign-Off

**Reviewed Against:** CARD-004q requirements  
**Date:** 2026-09-08  
**Status:** Ready for implementation review

