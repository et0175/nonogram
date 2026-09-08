# CARD-004o: Batch Generation UI Refactor (Remove Random, Add Images)

**Wave**: 3 (Image-based generation)  
**Size**: 5pt  
**Status**: Pending  
**Priority**: High

## Summary

Remove "Random generation" mode from batch creation UI. Simplify to single "From Images" workflow with directory/upload selection instead of random parameters.

## Acceptance Criteria

- [ ] Remove "Random" generation option from batch_create.html
- [ ] Simplify form to accept only image source parameters
- [ ] Add directory picker (or upload button) for source images
- [ ] Form submits to new endpoint `/batch/from-images`
- [ ] Redirect to image preview page after selection
- [ ] Error handling for invalid/empty directory

## Test Cases

```gherkin
Scenario: User selects images from directory
  Given: User is on batch creation page
  When: They click "Select from directory"
  Then: Directory picker opens
  And: They select a directory with images
  And: Form shows count of images found
  And: Submit button is enabled

Scenario: Invalid directory handling
  Given: User selects empty directory
  Then: Error message appears
  And: Submit button stays disabled

Scenario: Form structure
  Given: Old form had "count, sizes, theme" options
  When: New form loads
  Then: Only "source directory" or "upload" fields shown
  And: No "random generation" options visible
```

## Files to Modify

- `src/nonogram/admin/templates/batch_create.html` - Simplify form
- `src/nonogram/admin/app.py` - Add new route, remove random option
- `src/nonogram/admin/batch_generator.py` - Add `create_batch_from_images()` method

## Implementation Notes

- Keep old `create_batch()` method for testing, mark as deprecated
- New form should guide user through workflow: Select → Preview → Generate
- Directory picker can use HTML5 file input with `webkitdirectory` attribute
- Or provide backend endpoint to scan directory on server

## Dependencies

- None (standalone UI refactor)

## Related Cards

- CARD-004p: Image selection & upload page
- CARD-004q: Image preview with size selection
