# Wave 3: Image-Based Batch Generation

**Status**: 🚀 Ready to start (cards created, awaiting approval)  
**Date Started**: 2026-09-08  
**Total Points**: 47pt

## Vision

Transform batch generation from random puzzles to image-based workflow. Users upload/select images, preview with configurable sizes, generate high-quality puzzles, and verify quality against originals.

## Wave 3 Cards

| Card | Title | Size | Status | Dependencies |
|------|-------|------|--------|--------------|
| CARD-004o | Batch UI Refactor | 5pt | Pending | None |
| CARD-004p | Image Selection & Upload | 8pt | Pending | CARD-004o |
| CARD-004q | Image Preview with Sizes | 13pt | Pending | CARD-004p |
| CARD-004r | Generate Puzzles from Images | 13pt | Pending | CARD-004q |
| CARD-004s | Show Source Images | 8pt | Pending | CARD-004r |

**Total**: 47 points

## Workflow After Wave 3

```
User starts batch generation
  ↓
1. [CARD-004o] UI shows only "From Images" mode
  ↓
2. [CARD-004p] User uploads/selects images
  ↓
3. [CARD-004q] User previews images with size options (Fixed/Min/Max)
  ↓
4. [CARD-004r] System generates puzzles from images
  ↓
5. [CARD-004s] Puzzle preview shows original image for quality check
  ↓
User approves/rejects puzzles, adds to books
```

## Key Features

### 1. Simplified UI (CARD-004o)
- Remove "Random generation" completely
- Single flow: "From Images"
- Cleaner, more focused interface

### 2. Image Management (CARD-004p)
- Upload or directory selection
- Thumbnail preview grid
- Add/remove images
- Show count and total size

### 3. Size Configuration (CARD-004q)
- 3 size options per image:
  - **Fixed**: User-specified (10-30)
  - **Min**: Smallest readable (auto-calculated)
  - **Max**: Largest that preserves quality (auto-calculated)
- Individual or "apply to all"
- Edit puzzle names (default: filename)
- Real-time preview of output

### 4. Generation Engine (CARD-004r)
- Process images sequentially (async in Wave 4)
- Call existing image-to-puzzle pipeline
- Track progress and errors
- Store original image path with puzzle
- Handle failures gracefully

### 5. Quality Verification (CARD-004s)
- Show original image in puzzle detail
- Compare puzzle vs. original side-by-side
- Verify recognizability before approval
- Mobile-responsive layout

## Success Criteria

Wave 3 is complete when:
- ✅ All 5 cards have passing tests
- ✅ No critical issues in ADMIN_FINDINGS.md
- ✅ Users can complete full workflow: Select → Preview → Generate → Verify
- ✅ Original images accessible in puzzle preview
- ✅ Performance acceptable for 200+ images

## Testing Strategy

### Manual Testing (Day 1-2)
1. Upload test images (PNG, JPG) of various sizes
2. Configure sizes: mix of fixed/min/max
3. Generate batch and verify quality
4. Check original image display
5. Approve/reject and add to books

### Automated Testing
```bash
pytest tests/test_wave3_image_generation.py -v
pytest tests/test_image_preview.py -v
pytest tests/test_source_images.py -v
```

### Performance Targets
- Upload 50 images: < 5 seconds
- Generate 50 puzzles: < 30 seconds (sequential)
- Show image preview: < 1 second (cached)
- Puzzle detail modal: < 500ms

## File Structure

```
src/nonogram/admin/
├── templates/
│   ├── batch_create.html (CARD-004o - simplified)
│   ├── image_selection.html (CARD-004p - new)
│   ├── image_preview.html (CARD-004q - new)
│   ├── puzzles_list.html (modified for CARD-004s)
│   └── puzzle_detail_modal.html (CARD-004s - new)
├── batch_generator.py (CARD-004r - new methods)
├── image_manager.py (CARD-004p/004q - new)
└── app.py (all cards - new routes)

tests/
├── test_wave3_image_generation.py (CARD-004r)
├── test_image_preview.py (CARD-004q)
└── test_source_images.py (CARD-004s)

docs/
├── ADMIN_FINDINGS.md (Wave 3 specification added)
└── WAVE3_OVERVIEW.md (this file)
```

## Estimated Timeline

| Phase | Duration | Cards |
|-------|----------|-------|
| UI Refactor | 2-3 hours | CARD-004o |
| Image Upload & Selection | 3-4 hours | CARD-004p |
| Preview & Size Config | 4-5 hours | CARD-004q |
| Generation Engine | 4-5 hours | CARD-004r |
| Source Image Display | 3-4 hours | CARD-004s |
| Testing & Polish | 2-3 hours | All |
| **Total** | **18-24 hours** | **5 cards** |

## Known Constraints

1. **Synchronous Generation**: Images processed one at a time (fine for 50-100, slow for 1000+)
   - Solution: Async queue in Wave 4

2. **Image Storage**: Original images kept in temp directory during batch
   - Solution: Implement cleanup on batch deletion

3. **Size Algorithm**: Heuristic-based (not machine learning)
   - Solution: Good enough for MVP; enhance later

4. **No Batch Modifications**: Can't add/remove images after creation
   - Solution: Can recreate or implement in Wave 4

## Next Steps

1. **Review**: User confirms these cards match requirements
2. **Adjust**: Make any changes to card specifications
3. **Start CARD-004o**: Begin UI refactor
4. **Iterate**: Test locally, document findings
5. **Review**: Each card demoed before moving to next

## Design Decisions (Confirmed ✅)

- ✅ **Keep random generation**: Add to cleanup card (CARD-004t) for later
- ✅ **Max image size**: 2MB per image
- ✅ **Supported formats**: PNG, JPG, GIF (all 3 in one directory)
- ✅ **Bad image handling**: Skip with message "Can't generate solvable nonogram" → continue batch
- ⏳ **Error message display**: Show in batch status page (e.g., "2 failed" badge)
- ⏳ **Async approach for Wave 4**: TBD (Celery, RQ, or asyncio)

---

**Ready to proceed?** Reply with any adjustments to these cards, and we'll start with CARD-004o! 🚀
