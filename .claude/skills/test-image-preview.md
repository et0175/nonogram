# UI Test: Image Preview & Cropping

Test image preview functionality, content-aware cropping, and preview rendering.

## Test Cases

### Test 1: Preview Image Loading
**Objective:** Verify all uploaded images display previews without errors

1. Upload birds or crabs directory
2. On preview page, verify:
   - All image boxes load (200×200px)
   - Cropped images display (blank space removed)
   - No "Failed to load image" placeholder text
   - Images maintain aspect ratio
   - Preview quality is acceptable

**Success Criteria:**
- ✓ 100% of images show preview (not placeholder error)
- ✓ No console errors in browser DevTools
- ✓ Thumbnails load within 2 seconds

### Test 2: Content-Aware Cropping
**Objective:** Verify blank space is properly removed from images

1. Upload birds directory
2. Check image previews:
   - Bird silhouettes should be centered
   - No excessive white/gray space around edges
   - Content (bird shape) clearly visible
   - Aspect ratio preserved

3. Upload crabs directory
4. Check image previews:
   - Crab/sea creature shapes centered
   - Blank space minimized
   - Details visible (legs, tentacles, etc.)

**Technical Details:**
- Cropping threshold: 200 (pixels darker than this = content)
- Algorithm: Detect content edges, crop to bounding box
- Result: Smaller, more focused preview images

**Success Criteria:**
- ✓ Cropped images smaller than originals
- ✓ Content fills most of preview box
- ✓ No black borders or excessive margins
- ✓ Silhouettes clearly recognizable

### Test 3: Puzzle Size Prediction
**Objective:** Verify predicted puzzle grid sizes are accurate

1. Upload birds directory
2. For each image, check "Predicted Output" box:
   - Fixed size: Should match selected value (15×15, 20×20, etc.)
   - Min size: Should be smallest readable
   - Max size: Should be largest without quality loss

**Expected Results:**
- Small silhouettes (bird1, raven1): 15×15 to 20×20
- Medium silhouettes (dove1, crab2): 20×20 to 25×25
- Large silhouettes (duck1, owl1): 25×25 to 30×30

**Success Criteria:**
- ✓ Size predictions are reasonable
- ✓ Predictions don't exceed 30×30 (max)
- ✓ Predictions don't go below 10×10 (min)
- ✓ Min/Max modes adjust dynamically

### Test 4: Preview Box Styling
**Objective:** Verify UI elements render correctly

1. Upload directory
2. On preview page, verify:
   - Boxes are square (200×200px)
   - Images use `object-fit: cover` (no distortion)
   - Placeholder text not visible for valid images
   - Hover effects work (if any)
   - Mobile responsive (boxes scale on small screens)

**Browser DevTools Check:**
- Image element: `<img class="preview-img">`
- Parent box: `.image-preview-box` (200px square)
- Correct CSS applied

### Test 5: Error Handling
**Objective:** Verify graceful error handling

1. Try to access non-existent image file:
   - System should show placeholder
   - Error should be in console, not blocking UI
   - Page should remain usable

2. Test with corrupted image file:
   - Preview should show error gracefully
   - Other images continue loading
   - No page crash

**Success Criteria:**
- ✓ Invalid images show placeholder (⚠️ Failed to load image)
- ✓ User can still proceed with other images
- ✓ Error messages are helpful

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Preview page load | < 3s | ? |
| Image preview render | < 1s each | ? |
| Cropping calculation | < 500ms | ? |
| Total page with 10 images | < 5s | ? |

## Browser Compatibility

Test on:
- ✓ Chrome (incognito mode)
- ✓ Opera
- ✓ Firefox (if available)
- ✓ Safari (if available)

## Notes

- Preview images are cropped versions, not originals
- Cropping endpoint: `/api/image/<file_id>/cropped`
- Original images available at: `/api/image/<file_id>`
- All previews should be responsive and mobile-friendly
