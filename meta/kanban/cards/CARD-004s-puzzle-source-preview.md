# CARD-004s: Show Source Images in Puzzle Preview

**Wave**: 3 (Image-based generation)  
**Size**: 8pt  
**Status**: Pending  
**Priority**: High

## Summary

Extend puzzle review page to display original source image alongside puzzle. Allow users to verify puzzle quality against original before approval.

## Acceptance Criteria

- [ ] Puzzle detail modal shows original image (solution) in sidebar
- [ ] Original image displayed at same size as puzzle for comparison
- [ ] Image name/metadata shown below
- [ ] Works in `/puzzles` list view (hover or detail view)
- [ ] Works in `/batch/{batch_id}` batch status page
- [ ] Graceful fallback if original image not available
- [ ] Image preview cached efficiently (no performance impact)
- [ ] Mobile-responsive: image stacks vertically on small screens

## Test Cases

```gherkin
Scenario: User views puzzle with source image
  Given: Puzzle generated from "sunset.jpg"
  When: User clicks on puzzle in list
  Then: Detail modal shows:
    - Left: Generated puzzle grid
    - Right: Original image (sunset.jpg)
  And: Both same visual size for easy comparison

Scenario: Verify quality before approval
  Given: Puzzle detail view open
  When: User sees original image
  Then: Can assess:
    - Is puzzle recognizable from image?
    - Did conversion preserve key features?
    - Is quality acceptable?
  And: Then approve/reject based on quality

Scenario: Fallback for missing image
  Given: Puzzle whose source image was deleted
  When: User views puzzle detail
  Then: Shows placeholder: "Original image not found"
  And: Puzzle can still be approved/rejected

Scenario: Mobile view
  Given: User on mobile device
  When: Viewing puzzle detail
  Then: Image and puzzle stack vertically
  And: Both remain fully readable
```

## UI Layout

```
┌──────────────────────────────────────────────────────┐
│ Puzzle Detail                          [×]           │
├──────────────────────────────────────────────────────┤
│                                                      │
│ Puzzle ID: puzzle_000042                            │
│ Source: sunset.jpg                                  │
│ Size: 20×20                                         │
│ Difficulty: Medium  Quality: 78/100                 │
│                                                      │
│ ┌─────────────────┐  ┌─────────────────┐            │
│ │  Generated      │  │  Original       │            │
│ │  Puzzle         │  │  Image          │            │
│ │  (20×20)        │  │  (same visual)  │            │
│ │                 │  │                 │            │
│ │  ██  ▓  ░ ░ ██  │  │  (photo preview)│            │
│ │  ██  ▓▓ ░ ░ ██  │  │                 │            │
│ │  ▓▓  ██ ░ ░ ░░  │  │                 │            │
│ │                 │  │                 │            │
│ └─────────────────┘  └─────────────────┘            │
│                                                      │
│ [Approve] [Reject] [Save Draft]                     │
└──────────────────────────────────────────────────────┘
```

## Files to Modify

### Templates
- `src/nonogram/admin/templates/puzzle_detail_modal.html` (new)
- `src/nonogram/admin/templates/puzzles_list.html` - Add click handler
- `src/nonogram/admin/templates/batch_status.html` - Show image in puzzle card

### Backend
- `src/nonogram/admin/app.py` - Route `/puzzle/{puzzle_id}/detail` (JSON)
- `src/nonogram/admin/puzzle_review.py` - Return image_path in puzzle data

## Implementation Notes

### Image Display Strategy

```python
# Puzzle data structure (extended)
puzzle = {
    "id": "puzzle_000042",
    "grid": [[0,1,0], ...],
    "clues_rows": [...],
    "clues_cols": [...],
    "width": 20,
    "height": 20,
    "puzzle_name": "sunset_puzzle",
    "original_image_path": "uploads/batch_xyz/sunset.jpg",  # NEW
    "original_image_url": "/api/puzzle/puzzle_000042/image",  # NEW (serve via API)
    "difficulty_tier": "Medium",
    "quality_score": 78,
    ...
}
```

### Image Serving

- API endpoint: `GET /api/puzzle/{puzzle_id}/image`
- Returns original image from storage
- Cached with ETag headers (avoid re-serving)
- 404 if image not found (show placeholder)

### Performance

- Load image only when detail view opened (lazy load)
- Cache image for 24 hours (browser cache)
- Thumbnail for list view (100×100px)
- Full image for detail view (up to 2000×2000px)

## Data Model

Update `PuzzleReviewService.add_puzzle()`:

```python
def add_puzzle(
    self,
    # ... existing params ...
    original_image_path: Optional[str] = None,  # NEW
) -> str:
    """Add puzzle with optional source image reference."""
    puzzle_id = ...
    self.puzzles[puzzle_id] = {
        # ... existing fields ...
        "original_image_path": original_image_path,
    }
```

## Dependencies

- CARD-004r: Generate puzzles from images (provides image_path)

## Related Cards

- CARD-004q: Image preview with size selection (user sees before generation)
- CARD-004r: Generate puzzles from images (stores original_image_path)

## Future Enhancements

- Quick-compare view: overlay puzzle grid on original image
- Zoom in/out controls for detailed inspection
- Toggle between puzzle and original image (flip animation)
- Mark puzzles that diverge too far from original
