# CARD-004q: Image Preview with Size Selection

**Wave**: 3 (Image-based generation)  
**Size**: 13pt  
**Status**: Pending  
**Priority**: High

## Summary

Create preview page showing selected images with individual size selection. Users can set puzzle size for each image using 3 options (fixed number, min, max) and preview quality before generation.

## Acceptance Criteria

- [ ] Page: `/batch/preview-images` displays each image with controls
- [ ] For each image: show cropped preview, filename, dimensions
- [ ] Size selector dropdown: "Fixed (10-30)", "Min", "Max"
- [ ] If "Fixed": number input appears (10-30 range)
- [ ] If "Min" or "Max": shows predicted size (e.g., "Min: 15px")
- [ ] Edit puzzle_name field (defaults to filename, no extension)
- [ ] Apply size to single image or "Apply to all" button
- [ ] Preview updates in real-time (shows output puzzle size)
- [ ] Generation button becomes active only if all valid
- [ ] Back to image selection, or generate
- [ ] Error handling for invalid configurations

## Test Cases

```gherkin
Scenario: User sets fixed size for all images
  Given: 3 images on preview page
  When: User selects "Fixed (10-30)" size option
  And: Enters "20" in number field
  And: Clicks "Apply to all"
  Then: All 3 images show "Size: 20×20" prediction
  And: Generate button becomes enabled

Scenario: Mix of size options
  Given: 3 images with different original dimensions
  When: Image 1: Fixed 15
  And: Image 2: Min (predicts 12)
  And: Image 3: Max (predicts 28)
  Then: Preview shows different puzzle sizes
  And: All are valid (10-30 range)

Scenario: Edit puzzle name
  Given: Image "vacation_photo_001.jpg"
  When: User clicks edit name field
  Then: Default shows "vacation_photo_001"
  And: User can change to "beach_sunset"
  And: Name is used in puzzle storage

Scenario: Min/Max size prediction
  Given: Image 1200×800 px
  When: User selects "Max"
  Then: Prediction shows "Max: 25px" (largest that preserves quality)
  When: User selects "Min"
  Then: Prediction shows "Min: 12px" (smallest readable)

Scenario: Invalid size handling
  Given: User has mixed sizes (15, 35, 20)
  When: Size 35 is outside valid range
  Then: Error badge shows on that image
  And: Generate button is disabled
  And: Tooltip explains "Size must be 10-30"
```

## UI Layout

```
┌───────────────────────────────────────────────────────────────┐
│ Batch Generation: Preview Images & Select Sizes               │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│ Image 1: vacation_001.jpg (1200×800)                          │
│ ┌─────────────┐  Name: [vacation_001________]                 │
│ │   Preview   │  Size: [Fixed ▼] [15 ____]  [Apply to all]   │
│ │   (150×100) │  → Output: 15×15 puzzle                       │
│ └─────────────┘                                               │
│                                                               │
│ Image 2: sunset.jpg (1024×1024)                               │
│ ┌─────────────┐  Name: [sunset_______________]                │
│ │   Preview   │  Size: [Min ▼]                                │
│ │   (150×150) │  → Output: 18×18 puzzle (predicted)          │
│ └─────────────┘                                               │
│                                                               │
│ Image 3: beach.jpg (900×600)                                  │
│ ┌─────────────┐  Name: [beach________________]                │
│ │   Preview   │  Size: [Max ▼]                                │
│ │   (150×100) │  → Output: 22×22 puzzle (predicted)          │
│ └─────────────┘                                               │
│                                                               │
│ [◄ Back] [Generate >]                                         │
└───────────────────────────────────────────────────────────────┘
```

## Files to Create/Modify

- `src/nonogram/admin/templates/image_preview.html` - Preview grid with controls
- `src/nonogram/admin/app.py` - Route `/batch/preview-images`
- `src/nonogram/admin/image_manager.py` - Size prediction logic

## Implementation Notes

### Size Prediction Algorithm

```python
def predict_size(image_width, image_height, mode):
    """Predict puzzle size based on image and mode."""
    # Min size: avoid too-small unreadable puzzles
    min_size = 10
    
    # Max size: largest that preserves image quality
    # Rule: pixel_per_cell >= 2 (at least 2px per cell)
    max_pixel_per_cell = 2
    max_size = min(
        image_width // max_pixel_per_cell,
        image_height // max_pixel_per_cell,
        30  # Absolute max
    )
    
    if mode == "min":
        return max(min_size, max_size - 5)  # slightly smaller
    elif mode == "max":
        return max_size
    else:  # fixed - user provides
        return user_value
```

### Reuse Web UI Components

- Steal cropping preview logic from `src/nonogram/web` if available
- Size selector UI already implemented in web UI

## Dependencies

- CARD-004p: Image selection page (provides image list)

## Related Cards

- CARD-004r: Generate puzzles from images (next step)
- CARD-004s: Show source images in puzzle preview
