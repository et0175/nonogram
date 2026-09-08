# End-to-End Testing Documentation

## Overview

This document describes the end-to-end test suite for the Nonogram Admin Panel Wave 3 image-to-puzzle workflow.

## User Flows

### Flow 1: Image Upload & Preview
**Objective**: Verify users can upload images and see previews

**Steps**:
1. Navigate to `/batch/create`
2. Upload single image (PNG, JPG, GIF)
3. Click "Next: Preview Images"
4. Verify original image displays
5. Verify puzzle metadata shown (size, difficulty, quality)

**Expected Results**:
- Image loads in preview
- Metadata matches uploaded image properties
- Navigation buttons available

### Flow 2: Batch Image Upload with Configuration
**Objective**: Verify users can upload multiple images and configure sizes

**Steps**:
1. Navigate to `/batch/create`
2. Upload 3-5 images
3. Configure puzzle sizes (Fixed/Min/Max)
4. Apply to all or per-image
5. Click "Next: Generate Puzzles"

**Expected Results**:
- All images load
- Size configuration saves
- Redirect to generation confirmation page

### Flow 3: Puzzle Generation & SVG Display
**Objective**: Verify puzzles generate and SVG grids display correctly

**Steps**:
1. Complete upload & configuration
2. On generation page, check confirmation checkbox
3. Click "Generate Puzzles"
4. Wait for processing
5. Verify SVG grids display
6. Test download SVG button

**Expected Results**:
- Puzzles generate successfully
- SVG grids display (not error messages)
- Download produces valid .svg file
- Approve/Reject buttons visible

### Flow 4: Puzzle Management
**Objective**: Verify users can approve/reject generated puzzles

**Steps**:
1. View generated puzzles page
2. Click "Approve" on a puzzle
3. Confirm dialog
4. Click "Reject" on another puzzle
5. Confirm dialog

**Expected Results**:
- Approve marks puzzle as approved
- Reject removes puzzle from batch
- Actions persist in database

## Test Cases

### TC-001: Single Image Upload
- **Flow**: Flow 1
- **Input**: landscape.png (2000×1000px)
- **Expected**: Image previews correctly, grid 30×15 at default settings

### TC-002: Multiple Image Batch
- **Flow**: Flow 2
- **Input**: 5 images (landscape, portrait, square, etc.)
- **Expected**: All 5 images load, preview all 5

### TC-003: SVG Generation & Display
- **Flow**: Flow 3
- **Input**: Single image batch
- **Expected**: SVG displays as grid (not original image), download works

### TC-004: Approve Puzzle
- **Flow**: Flow 4
- **Input**: Generated puzzle from TC-003
- **Expected**: Puzzle status changes to approved

### TC-005: Reject Puzzle
- **Flow**: Flow 4
- **Input**: Generated puzzle from TC-003
- **Expected**: Puzzle status changes to rejected/removed

### TC-006: Download SVG File
- **Flow**: Flow 3
- **Input**: Click download button on generated puzzle
- **Expected**: Browser downloads .svg file (not .html)

## Test Execution

### Setup
```bash
python -m pytest tests/e2e/ -v
```

### Tear Down
- Clear session data
- Remove uploaded test images
- Reset database state

## Success Criteria

- All 6 test cases pass
- No error messages in UI
- SVG files download correctly
- Database state updates on approve/reject
- Response times acceptable (< 2s per operation)
