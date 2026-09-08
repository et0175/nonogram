# Admin Panel User Stories

**Document Version**: 1.0  
**Date**: 2026-09-08  
**Format**: User stories with acceptance criteria  

## Story Overview

| Story ID | Title | Priority | Status |
|----------|-------|----------|--------|
| AS-001 | User uploads single image | HIGH | ✅ Ready |
| AS-002 | User uploads batch of images | HIGH | ✅ Ready |
| AS-003 | User previews uploaded images | HIGH | ✅ Ready |
| AS-004 | User configures puzzle size (fixed mode) | HIGH | ✅ Ready |
| AS-005 | User configures puzzle size (minimum mode) | MEDIUM | ✅ Ready |
| AS-006 | User configures puzzle size (maximum mode) | MEDIUM | ✅ Ready |
| AS-007 | User applies configuration to all images | MEDIUM | ✅ Ready |
| AS-008 | System generates puzzles from batch | HIGH | ✅ Ready |
| AS-009 | User sees generation progress | HIGH | ✅ Ready |
| AS-010 | User approves generated puzzle | HIGH | ✅ Ready |
| AS-011 | User rejects generated puzzle | HIGH | ✅ Ready |
| AS-012 | User downloads puzzle as SVG | MEDIUM | ✅ Ready |
| AS-013 | User filters puzzles by difficulty | LOW | ✅ Ready |
| AS-014 | User filters puzzles by quality score | LOW | ✅ Ready |
| AS-015 | User views puzzle metadata | HIGH | ✅ Ready |
| AS-016 | User exports batch summary | MEDIUM | ✅ Ready |
| AS-017 | User navigates between pages | HIGH | ✅ Ready |
| AS-018 | User receives form validation feedback | HIGH | ✅ Ready |
| AS-019 | User handles upload errors | HIGH | ✅ Ready |
| AS-020 | User handles generation errors | HIGH | ✅ Ready |

---

## Story Details

### AS-001: User uploads single image

**As a** puzzle creator  
**I want to** upload a single image to the admin panel  
**So that** I can generate a nonogram puzzle from it

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-101: File type validation
  - Given: User selects a file for upload
  - When: File type is PNG, JPG, or GIF
  - Then: File is accepted for upload
  
- AC-102: File size validation
  - Given: User selects a file for upload
  - When: File size is ≤ 2 MB
  - Then: File is accepted for upload
  
- AC-103: Upload progress feedback
  - Given: User initiates file upload
  - When: Upload is in progress
  - Then: Progress indicator shows upload percentage
  
- AC-104: Upload success feedback
  - Given: Upload completes successfully
  - When: File has been sent to server
  - Then: Success message displays and user redirected to preview page

**Test Cases**: TC-101, TC-102, TC-103, TC-104  
**Related Requirement**: REQ-2.1.1

---

### AS-002: User uploads batch of images

**As a** batch administrator  
**I want to** upload multiple images (5-50) in one batch  
**So that** I can generate puzzles from all of them together

**Priority**: HIGH  
**Effort**: 5  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-105: Multiple file selection
  - Given: User accesses upload form
  - When: User selects "Choose files"
  - Then: Multi-file selection dialog opens
  
- AC-106: Batch size limit enforcement
  - Given: User selects files for upload
  - When: User selects >50 files
  - Then: Error message shows "Maximum 50 files per batch"
  
- AC-107: Batch total size validation
  - Given: User selects multiple files
  - When: Total batch size > 100 MB
  - Then: Error message shows "Batch too large (max 100 MB)"
  
- AC-108: Batch session creation
  - Given: User uploads 5-50 files successfully
  - When: Upload completes
  - Then: Unique batch ID is generated and stored

**Test Cases**: TC-105, TC-106, TC-107, TC-108  
**Related Requirement**: REQ-2.1.1

---

### AS-003: User previews uploaded images

**As a** puzzle creator  
**I want to** see the original uploaded images before configuration  
**So that** I can verify they look correct

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-109: Image display
  - Given: User has uploaded images
  - When: User navigates to preview page
  - Then: All uploaded images display in grid
  
- AC-110: Image dimensions shown
  - Given: Images are displayed
  - When: User views preview page
  - Then: Image dimensions (WxH pixels) shown below each image
  
- AC-111: Image filenames shown
  - Given: Images are displayed
  - When: User views preview page
  - Then: Original filename shown for each image
  
- AC-112: Image loading performance
  - Given: User loads preview page with 50 images
  - When: Page loads
  - Then: Page loads in <2 seconds

**Test Cases**: TC-109, TC-110, TC-111, TC-112  
**Related Requirement**: REQ-2.2.1

---

### AS-004: User configures puzzle size (fixed mode)

**As a** puzzle creator  
**I want to** set a fixed grid size (e.g., 20×20) for each image  
**So that** all puzzles in the batch have consistent size

**Priority**: HIGH  
**Effort**: 5  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-113: Size input field
  - Given: User is on preview page
  - When: User selects "Fixed Size" mode
  - Then: Input field appears for entering size (10-30)
  
- AC-114: Size range validation
  - Given: User enters size value
  - When: Value is <10 or >30
  - Then: Error message "Size must be 10-30"
  
- AC-115: Predicted output shown
  - Given: User enters valid size
  - When: User changes size value
  - Then: Predicted output dimensions update in real-time
  
- AC-116: Configuration saved
  - Given: User configures size for an image
  - When: User navigates away or proceeds
  - Then: Configuration is saved in session

**Test Cases**: TC-113, TC-114, TC-115, TC-116  
**Related Requirement**: REQ-2.2.2

---

### AS-005: User configures puzzle size (minimum mode)

**As a** puzzle creator  
**I want to** use minimum readable size for images  
**So that** I can generate puzzles quickly with less detail

**Priority**: MEDIUM  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-117: Mode selection
  - Given: User is on preview page
  - When: User selects "Minimum Size" mode
  - Then: Mode is applied (no input field needed)
  
- AC-118: Auto-calculation
  - Given: User selects minimum mode
  - When: Mode is applied
  - Then: System calculates minimum readable size and shows it
  
- AC-119: Consistency check
  - Given: Multiple images with different sizes
  - When: Minimum mode applied to all
  - Then: Each gets its own calculated minimum (respecting aspect ratio)

**Test Cases**: TC-117, TC-118, TC-119  
**Related Requirement**: REQ-2.2.2

---

### AS-006: User configures puzzle size (maximum mode)

**As a** puzzle creator  
**I want to** use maximum quality size for images  
**So that** I can preserve maximum image detail

**Priority**: MEDIUM  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-120: Mode selection
  - Given: User is on preview page
  - When: User selects "Maximum Size" mode
  - Then: Mode is applied
  
- AC-121: Max grid limit
  - Given: User selects maximum mode
  - When: System calculates size
  - Then: Result is clamped to maximum 30×30 grid
  
- AC-122: Quality preservation
  - Given: Maximum mode applied
  - When: User views predicted output
  - Then: Shows highest possible grid size up to 30×30

**Test Cases**: TC-120, TC-121, TC-122  
**Related Requirement**: REQ-2.2.2

---

### AS-007: User applies configuration to all images

**As a** batch administrator  
**I want to** apply the same size configuration to all images at once  
**So that** I don't have to configure each image individually

**Priority**: MEDIUM  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-123: Global config option
  - Given: User is on preview page
  - When: User selects mode and size
  - Then: "Apply to All" button is available
  
- AC-124: Batch application
  - Given: User clicks "Apply to All"
  - When: Configuration is applied
  - Then: All images use the same mode/size
  
- AC-125: Override capability
  - Given: User has applied configuration to all
  - When: User modifies one image's configuration
  - Then: Individual image override persists while others keep batch config

**Test Cases**: TC-123, TC-124, TC-125  
**Related Requirement**: REQ-2.2.2

---

### AS-008: System generates puzzles from batch

**As a** puzzle creator  
**I want to** generate puzzles from all configured images  
**So that** I can review and approve them

**Priority**: HIGH  
**Effort**: 8  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-126: Generation initiation
  - Given: User has configured all images
  - When: User clicks "Generate Puzzles"
  - Then: Generation process starts
  
- AC-127: Confirmation required
  - Given: User is on generation page
  - When: User hasn't confirmed
  - Then: "Generate" button is disabled
  
- AC-128: Generation completion
  - Given: Generation is processing
  - When: All images are processed
  - Then: System generates puzzles and stores in database
  
- AC-129: Timeout handling
  - Given: Single puzzle generation takes >10 seconds
  - When: Timeout limit reached
  - Then: Puzzle is marked as failed, batch continues

**Test Cases**: TC-126, TC-127, TC-128, TC-129  
**Related Requirement**: REQ-2.3.1

---

### AS-009: User sees generation progress

**As a** puzzle creator  
**I want to** see real-time progress of puzzle generation  
**So that** I know how long it will take

**Priority**: HIGH  
**Effort**: 5  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-130: Progress bar display
  - Given: Generation is in progress
  - When: User views processing page
  - Then: Progress bar shows 0-100% completion
  
- AC-131: Puzzle count display
  - Given: Generation is in progress
  - When: User views processing page
  - Then: Text shows "25/50 Generated"
  
- AC-132: Time estimate
  - Given: Generation is in progress
  - When: User views processing page
  - Then: Estimated time remaining shown (e.g., "2 minutes left")
  
- AC-133: Status updates
  - Given: User views processing page
  - When: Status updates
  - Then: Page updates every 1-2 seconds

**Test Cases**: TC-130, TC-131, TC-132, TC-133  
**Related Requirement**: REQ-2.3.3

---

### AS-010: User approves generated puzzle

**As a** quality reviewer  
**I want to** mark a generated puzzle as approved  
**So that** it can be included in the final book

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-134: Approve button visible
  - Given: User views generated puzzle
  - When: Puzzle is displayed
  - Then: "Approve" button is visible and clickable
  
- AC-135: Status update
  - Given: User clicks "Approve"
  - When: Action completes
  - Then: Puzzle status changes to "Approved" in database
  
- AC-136: Feedback shown
  - Given: User clicks "Approve"
  - When: Action completes
  - Then: Success message shown ("Puzzle approved ✓")
  
- AC-137: List update
  - Given: Puzzle was approved
  - When: User views puzzle list
  - Then: Approved count increments and puzzle appears in approved list

**Test Cases**: TC-134, TC-135, TC-136, TC-137  
**Related Requirement**: REQ-2.4.2

---

### AS-011: User rejects generated puzzle

**As a** quality reviewer  
**I want to** reject a puzzle that doesn't meet quality standards  
**So that** it's excluded from the final book

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-138: Reject button visible
  - Given: User views generated puzzle
  - When: Puzzle is displayed
  - Then: "Reject" button is visible and clickable
  
- AC-139: Confirmation dialog
  - Given: User clicks "Reject"
  - When: Dialog appears
  - Then: User must confirm ("Are you sure?")
  
- AC-140: Status update
  - Given: User confirms rejection
  - When: Action completes
  - Then: Puzzle status changes to "Rejected" and removed from review list
  
- AC-141: Rejection recorded
  - Given: Puzzle was rejected
  - When: User views batch summary
  - Then: Rejected count increments

**Test Cases**: TC-138, TC-139, TC-140, TC-141  
**Related Requirement**: REQ-2.4.2

---

### AS-012: User downloads puzzle as SVG

**As a** puzzle creator  
**I want to** download a generated puzzle as SVG format  
**So that** I can use it externally

**Priority**: MEDIUM  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-142: Download button visible
  - Given: User views generated puzzle
  - When: Puzzle SVG grid is displayed
  - Then: "Download SVG" button is visible
  
- AC-143: File format
  - Given: User clicks "Download SVG"
  - When: File downloads
  - Then: File is .svg format (not HTML)
  
- AC-144: Filename
  - Given: User downloads SVG
  - When: File downloads
  - Then: Filename is puzzle ID or descriptive name
  
- AC-145: Content validity
  - Given: SVG file is downloaded
  - When: File is opened
  - Then: SVG renders correctly in browser/application

**Test Cases**: TC-142, TC-143, TC-144, TC-145  
**Related Requirement**: REQ-2.4.2

---

### AS-013: User filters puzzles by difficulty

**As a** batch reviewer  
**I want to** filter puzzles by difficulty tier (Easy/Medium/Hard)  
**So that** I can review similar puzzles together

**Priority**: LOW  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-146: Filter dropdown
  - Given: User views puzzle list
  - When: Filter controls load
  - Then: Difficulty dropdown shows Easy/Medium/Hard options
  
- AC-147: Filter application
  - Given: User selects "Medium"
  - When: Filter applied
  - Then: Only Medium difficulty puzzles shown
  
- AC-148: Multi-filter
  - Given: User has applied difficulty filter
  - When: User applies another filter (e.g., quality)
  - Then: Filters combine (AND logic)
  
- AC-149: Filter clear
  - Given: Filters are active
  - When: User clicks "Clear Filters"
  - Then: All filters removed, all puzzles shown

**Test Cases**: TC-146, TC-147, TC-148, TC-149  
**Related Requirement**: REQ-2.4.3

---

### AS-014: User filters puzzles by quality score

**As a** batch reviewer  
**I want to** filter puzzles by quality score range (e.g., 70-100)  
**So that** I can focus on high-quality puzzles

**Priority**: LOW  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-150: Quality slider
  - Given: User views puzzle list
  - When: Filter controls load
  - Then: Quality range slider appears (0-100)
  
- AC-151: Range selection
  - Given: User adjusts slider
  - When: Range is set to 75-100
  - Then: Only puzzles with quality ≥75 shown
  
- AC-152: Real-time update
  - Given: User adjusts slider
  - When: Value changes
  - Then: Puzzle list updates immediately

**Test Cases**: TC-150, TC-151, TC-152  
**Related Requirement**: REQ-2.4.3

---

### AS-015: User views puzzle metadata

**As a** batch reviewer  
**I want to** see puzzle metadata (size, difficulty, quality, source)  
**So that** I can make informed approval decisions

**Priority**: HIGH  
**Effort**: 2  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-153: Metadata display
  - Given: User views puzzle card
  - When: Card is rendered
  - Then: Size (20×20), Difficulty (Medium), Quality (75), Source (original.jpg) shown
  
- AC-154: Metadata accuracy
  - Given: Metadata is displayed
  - When: User reviews values
  - Then: All values match database records
  
- AC-155: Consistent formatting
  - Given: Multiple puzzles displayed
  - When: User views puzzle cards
  - Then: Metadata formatted consistently across all cards

**Test Cases**: TC-153, TC-154, TC-155  
**Related Requirement**: REQ-2.4.1

---

### AS-016: User exports batch summary

**As a** batch administrator  
**I want to** export batch summary (approved puzzles, metadata)  
**So that** I can prepare for book generation

**Priority**: MEDIUM  
**Effort**: 5  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-156: Export button
  - Given: User views batch page
  - When: Page loads
  - Then: "Export" button visible
  
- AC-157: Format selection
  - Given: User clicks "Export"
  - When: Dialog appears
  - Then: Format options shown (JSON, CSV, SVG Archive)
  
- AC-158: Approved only
  - Given: User selects export format
  - When: Export completes
  - Then: Only approved puzzles included in export
  
- AC-159: Metadata included
  - Given: Export file generated
  - When: File is opened
  - Then: All puzzle metadata included (ID, size, clues, quality, difficulty)

**Test Cases**: TC-156, TC-157, TC-158, TC-159  
**Related Requirement**: REQ-2.5.2

---

### AS-017: User navigates between pages

**As a** puzzle creator  
**I want to** navigate between upload, preview, generation, and review pages  
**So that** I can move through the workflow smoothly

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-160: Page links
  - Given: User is on any workflow page
  - When: Page loads
  - Then: Navigation buttons show "Back" and "Next" (where applicable)
  
- AC-161: Redirect after action
  - Given: User completes a step (upload, config, generate)
  - When: Step completes
  - Then: User automatically redirected to next page
  
- AC-162: Session persistence
  - Given: User navigates back
  - When: User returns to previous page
  - Then: Previous configuration/data still present

**Test Cases**: TC-160, TC-161, TC-162  
**Related Requirement**: REQ-4.1.1

---

### AS-018: User receives form validation feedback

**As a** puzzle creator  
**I want to** get immediate feedback when I fill out forms incorrectly  
**So that** I can fix errors before submitting

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-163: Real-time validation
  - Given: User enters invalid value (e.g., size=100)
  - When: User tabs away from field
  - Then: Error message appears immediately
  
- AC-164: Clear error messages
  - Given: Validation fails
  - When: Error message shown
  - Then: Message is clear ("Size must be 10-30")
  
- AC-165: Submit disabled
  - Given: Form has validation errors
  - When: User tries to submit
  - Then: Submit button is disabled until errors fixed

**Test Cases**: TC-163, TC-164, TC-165  
**Related Requirement**: REQ-4.3.2

---

### AS-019: User handles upload errors

**As a** puzzle creator  
**I want to** receive helpful error messages if upload fails  
**So that** I can understand what went wrong and fix it

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-166: Error display
  - Given: Upload fails (network error, timeout, etc.)
  - When: Error occurs
  - Then: Error message displayed (not generic error)
  
- AC-167: Specific error info
  - Given: Upload fails for specific reason
  - When: Error message shown
  - Then: Includes: what happened, why, and how to fix
  
- AC-168: Retry option
  - Given: Upload failed
  - When: User views error
  - Then: "Retry" button available to re-attempt

**Test Cases**: TC-166, TC-167, TC-168  
**Related Requirement**: REQ-7.1.1

---

### AS-020: User handles generation errors

**As a** puzzle creator  
**I want to** get clear error messages if puzzle generation fails  
**So that** I can troubleshoot and retry

**Priority**: HIGH  
**Effort**: 3  
**Status**: ✅ Ready  

**Acceptance Criteria**:
- AC-169: Error reporting
  - Given: Generation fails for one/more puzzles
  - When: Process completes
  - Then: Failed puzzles listed with reason
  
- AC-170: Partial success
  - Given: Some puzzles succeed, some fail
  - When: Generation completes
  - Then: Successful puzzles shown, failed ones listed separately
  
- AC-171: Actionable feedback
  - Given: Puzzle generation failed
  - When: User views error
  - Then: Message suggests action (e.g., "Image too small, try uploading larger image")

**Test Cases**: TC-169, TC-170, TC-171  
**Related Requirement**: REQ-7.1.2

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total User Stories | 20 |
| HIGH Priority | 14 |
| MEDIUM Priority | 5 |
| LOW Priority | 1 |
| Total Acceptance Criteria | 70+ |
| Total Test Cases Planned | 171 |
| Est. Total Effort | 90 story points |

---

**Status**: ✅ All stories ready for development  
**Next**: Create test cases (see ADMIN_PANEL_TC.md)
