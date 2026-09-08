# CARD-004p: Image Selection & Upload Page

**Wave**: 3 (Image-based generation)  
**Size**: 8pt  
**Status**: Pending  
**Priority**: High

## Summary

Create new page for selecting and previewing source images before batch generation. Users can upload images or select from directory, view thumbnails, and add/remove images from batch.

## Acceptance Criteria

- [ ] New page: `/batch/select-images` displays selected images as thumbnails
- [ ] Thumbnails show image filename and dimensions
- [ ] Remove button (×) on each thumbnail to remove from selection
- [ ] "Add more images" button to upload additional images
- [ ] Display count: "X images selected (Y MB)"
- [ ] Next button redirects to size selection page
- [ ] Back button returns to batch creation
- [ ] Error if no images selected when clicking Next

## Test Cases

```gherkin
Scenario: User views selected images
  Given: 5 images uploaded from directory
  When: Page loads
  Then: 5 thumbnails displayed in grid
  And: Each shows filename and "WxH px"
  And: Total size shown at bottom

Scenario: Remove image from batch
  Given: 5 images displayed
  When: User clicks × on image 3
  Then: Image removed from display
  And: Count updates to "4 images selected"
  And: Page stays on same view

Scenario: Add more images
  Given: User on image selection page
  When: They click "Add more images"
  Then: File picker opens
  And: Selected images are added to list
  And: Duplicates are ignored (by filename)

Scenario: Next button disabled state
  Given: No images selected
  Then: Next button is disabled/greyed out
  When: User selects images
  Then: Next button becomes enabled
```

## UI Layout

```
┌─────────────────────────────────────────┐
│ Batch Generation: Select Images         │
├─────────────────────────────────────────┤
│                                         │
│ [Add more images] [Clear all]           │
│                                         │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ img1.jpg │ │ img2.jpg │ │ img3.jpg │ │
│ │ 800×600  │ │ 1024×768 │ │ 1200×900 │ │
│ │    × │ │    × │ │    × │ │
│ └──────────┘ └──────────┘ └──────────┘ │
│                                         │
│ 3 images selected (2.5 MB)              │
│                                         │
│ [Back] [Next >]                         │
└─────────────────────────────────────────┘
```

## Files to Create

- `src/nonogram/admin/templates/image_selection.html` - Image grid with remove buttons
- `src/nonogram/admin/app.py` - Route `/batch/select-images`
- `src/nonogram/admin/image_manager.py` - New service for image handling

## Implementation Notes

- Store selected images in session during workflow
- Thumbnails generated using PIL (Pillow)
- Max image size: 2MB per image
- Max image dimensions: 2000×2000px (validate on upload)
- Supported formats: PNG, JPG, GIF (all 3 can be in same directory)
- Filename used as default puzzle name (editable later)

## Dependencies

- CARD-004o: Batch UI refactor (forms must redirect here)

## Related Cards

- CARD-004q: Image preview with size selection (next step)
- CARD-004r: Generate puzzles from images (final step)
