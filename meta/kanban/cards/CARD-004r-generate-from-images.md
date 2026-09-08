# CARD-004r: Generate Puzzles from Images (Core Logic)

**Wave**: 3 (Image-based generation)  
**Size**: 13pt  
**Status**: Pending  
**Priority**: High

## Summary

Implement core image-to-puzzle generation logic in admin backend. Process selected images with configured sizes, generate puzzles, store original images with puzzles for preview.

## Acceptance Criteria

- [ ] New method: `batch_generator.create_batch_from_images(image_configs)`
- [ ] Input format: List of `{image_path, puzzle_name, size}`
- [ ] Call image processing pipeline for each image
- [ ] Store puzzle with link to original image
- [ ] Track progress: "3 of 10 puzzles generated"
- [ ] Store original image for later preview (or reference path)
- [ ] Update batch status: PENDING → GENERATING → COMPLETE
- [ ] Error handling: skip failed images, log errors
- [ ] Return batch_id for tracking
- [ ] Redirect to batch status page with progress

## Test Cases

```gherkin
Scenario: Generate batch from 3 images
  Given: 3 images with configured sizes
  When: User clicks "Generate"
  Then: Batch creation starts
  And: Page shows "Generating 3 puzzles..."
  And: Progress bar updates
  When: All puzzles generated
  Then: Redirects to batch status page
  And: Shows "3/3 puzzles generated"

Scenario: Error handling - 1 image fails
  Given: 3 images, 1 can't generate solvable nonogram
  When: Generation starts
  Then: Valid images are generated
  And: Failed image shows error: "Can't generate solvable nonogram"
  And: Final batch has 2 puzzles
  And: Batch status shows: "2/3 puzzles (1 failed)"
  And: User can see which image failed

Scenario: Original image storage
  Given: Generated puzzle from "beach.jpg"
  When: Puzzle is stored
  Then: Original image saved as puzzle.image_path
  And: Can retrieve original image for preview

Scenario: Puzzle name assignment
  Given: Image "sunset.jpg" → puzzle_name "sunset_puzzle"
  When: Puzzle generated
  Then: Puzzle.puzzle_name = "sunset_puzzle"
  And: Can filter/search by this name
```

## Files to Create/Modify

- `src/nonogram/admin/batch_generator.py`
  - Add `create_batch_from_images(image_configs)` method
  - Add `_generate_puzzle_from_image(image_path, size, name)` helper
  - Modify `BatchJob` to track original_image_path

- `src/nonogram/admin/app.py`
  - Route: POST `/batch/generate-from-images`
  - Accept image configs from preview page
  - Handle async/sync generation

## Implementation Strategy

### Data Flow

```
Image preview page (user confirms)
  ↓
POST /batch/generate-from-images
  ↓
batch_generator.create_batch_from_images([
  {image_path: "temp/img1.jpg", puzzle_name: "img1", size: 20},
  {image_path: "temp/img2.jpg", puzzle_name: "img2", size: 25},
  ...
])
  ↓
For each image:
  1. Call image_processor.process(image_path, size)
  2. Get grid + clues
  3. Store puzzle with original_image_path
  ↓
Return batch_id
  ↓
Redirect to /batch/{batch_id}
```

### Original Image Storage

Options:
1. **Path-based**: Store `image_path` in puzzle (requires persistent storage)
2. **Base64-embedded**: Store small thumbnail in puzzle (larger DB)
3. **Reference-based**: Store image_id, retrieve from image service

**Recommendation**: Path-based with cleanup on batch deletion

### Async vs Sync

- **Wave 3**: Keep synchronous (like Wave 1)
- **Wave 4**: Add async with Celery (parallel processing)
- For now: Generate in sequence, show progress

## API Contract

```python
def create_batch_from_images(
    image_configs: List[Dict[str, Any]],  # [{image_path, puzzle_name, size}, ...]
    theme: str = "photos",
    quality_filter: int = 0,
) -> str:
    """
    Generate batch from images.
    
    Args:
        image_configs: List of image configurations
        theme: Batch theme (for categorization)
        quality_filter: Min quality score (0-100)
    
    Returns:
        batch_id for tracking progress
    
    Raises:
        ValueError: If invalid image configs
        RuntimeError: If image processing fails
    """
```

## Dependencies

- CARD-004q: Image preview with size selection (provides input)
- Image processing already implemented in `src/nonogram/...`

## Related Cards

- CARD-004s: Show source images in puzzle preview (visualization)
- CARD-004k: Async generation (future enhancement)

## Notes

- Reuse existing `puzzle_review_service` for storage
- Extend `BatchJob` dataclass with `original_images` field
- Log generation time for performance tracking
