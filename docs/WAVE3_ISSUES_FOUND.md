# Wave 3: Issues Found During Final Testing
**Date:** 2026-09-08  
**Status:** Documented and ready for fixes

---

## Issue #1: Image Previews Show Placeholder Instead of Actual Images

**Severity:** HIGH 🔴  
**User Feedback:** "Image preview - I see no picture"  
**AC Reference:** AC-002 in WAVE3_IMAGE_PREVIEW_ACS.md

### Current Behavior
- Image preview boxes show placeholder icon (🖼️) with dimensions
- Example: "512×512 PNG" instead of actual image thumbnail
- This is on `/batch/preview-images` page

### Expected Behavior (Per Requirements)
- Actual image thumbnail should display (150×150 or 200×200px)
- Square crop using object-fit: cover
- Actual image file content visible to user

### Root Cause
- Image files stored in temporary directory
- No image serving endpoint created (`/images/<file_id>`)
- Cannot display actual image in HTML without serving mechanism

### Solution Approach
1. **Create image serving endpoint:**
   - Route: `/images/<file_id>` or `/batch/image/<file_id>`
   - Serve from temp directory with proper MIME type
   - Add security: validate file_id, check file exists

2. **Update image_preview.html template:**
   - Replace placeholder with `<img src="/images/{file_id}">` 
   - Add image loading error handling
   - Fallback to placeholder if image unavailable

3. **Or alternative: Base64 encoding**
   - Read image file -> convert to base64
   - Embed as data URI: `<img src="data:image/png;base64,...">`
   - Simpler but larger HTML payloads

### Files to Modify
- `src/nonogram/admin/app.py` - Add image serving route
- `src/nonogram/admin/templates/image_preview.html` - Update img src
- `src/nonogram/admin/templates/image_selection.html` - Update img src

### Test Case
```
Given: User uploaded image test1_snail.png (512×512)
When: Navigates to /batch/preview-images
Then: Should see actual snail silhouette image thumbnail
And: Not a placeholder icon
```

---

## Issue #2: Size Calculation - Verify Against Requirements

**Severity:** MEDIUM 🟡  
**User Feedback:** "Size should be taken into account a bit differently - it's size of one side"  
**AC Reference:** AC-007 in WAVE3_IMAGE_PREVIEW_ACS.md

### Current Implementation
Located in `src/nonogram/admin/image_manager.py` (lines 42-63):

```python
def predict_size(self) -> int:
    width, height = self.dimensions
    min_size = 10
    max_pixel_per_cell = 2
    max_size = min(
        width // max_pixel_per_cell,
        height // max_pixel_per_cell,
        30,  # Absolute max
    )
    
    if self.size_mode == "min":
        return max(min_size, max_size - 5)
    elif self.size_mode == "max":
        return max_size
    else:  # fixed
        return self.size_value
```

### Requirements Spec (CARD-004q)
```python
min_size = 10                           # ✓ CORRECT
max_size = min(width÷2, height÷2, 30) # ✗ ISSUE - Current uses // not ÷2
```

**Issue Found:**
- Current: `width // max_pixel_per_cell` = `width // 2` = `width ÷ 2` ✓ **Actually CORRECT**
- Spec: `image_width // 2` ✓ **Matches**
- The implementation appears correct!

### Verification Needed
1. Test with specific image sizes:
   - 512×512: Should give max_size = 30 (min(256, 256, 30))
   - 1200×800: Should give max_size = 30 (min(600, 400, 30))
   - 400×300: Should give max_size = 30 (min(200, 150, 30))
   - 256×256: Should give max_size = 30 (min(128, 128, 30))

2. Test "min" mode calculation:
   - Current: `max(min_size, max_size - 5)`
   - Spec says "slightly smaller than max"
   - Current logic: min_size=10, if max_size=30 → returns max(10, 25) = 25 ✓

### Conclusion
**Size calculation appears correct per spec.** The comment "size of one side" is accurate - it's a square puzzle (20×20 means 20 cells per side).

### Recommendation
- Leave algorithm as-is (it's correct)
- Add unit tests to verify with known image sizes
- Document in code that size is square puzzle dimension

---

## Issue #3: Individual Size Configuration Clarity

**Severity:** MEDIUM 🟡  
**User Feedback:** "I'd like user to be able to change size for individual puzzles"  
**Current State:** Feature exists but UX may not be clear

### Current Implementation
- Template `image_preview.html` has per-image size controls (lines 71-91)
- Each image shows: size mode dropdown, size value input
- "Apply to All" button available for global change

### What Works
- ✅ Users CAN change size for individual images
- ✅ Per-image size dropdown present
- ✅ Size input field present and conditional
- ✅ Preview updates in real-time
- ✅ "Apply to All" button available

### UX Improvements Needed
1. **Better visual grouping:**
   - Group size controls clearly with each image
   - Add visual border or card to emphasize per-image settings

2. **Clearer labeling:**
   - Label: "Puzzle Size (10-30 cells)"
   - Add help tooltip explaining options

3. **Real-time feedback:**
   - Show output size calculation immediately
   - Color code valid/invalid sizes
   - Show error message if outside range

4. **Mobile responsiveness:**
   - Ensure controls stack nicely on small screens
   - Don't crowd controls together

### Recommendation
- Enhance styling in `image_preview.html`
- Add better visual separation per image
- Consider adding info icon or tooltip
- Test on mobile to verify layout

---

## Priority for Next Steps

### Must Fix (Blocks Production)
1. ⚠️ **Image preview displays placeholder** - Users can't see actual images
   - Impact: Can't visually verify image selection
   - Difficulty: Medium (need endpoint + template change)
   - Estimated: 1-2 hours

### Should Fix (UX Improvement)
2. **Clarify individual size configuration UI**
   - Impact: Users understand they can customize per-image
   - Difficulty: Low (CSS + labeling changes)
   - Estimated: 30 minutes

### Verify (Code Quality)
3. **Confirm size calculation algorithm**
   - Impact: Ensure correct puzzle generation
   - Difficulty: Low (add unit tests)
   - Estimated: 30 minutes

---

## Test Cases for Fixes

### Test 1: Image Preview Display
```
Scenario: View image thumbnail
Given: User uploaded test1_snail.png (512×512)
When: Navigates to /batch/preview-images
Then: Actual image thumbnail displays in preview box
And: Image shows snail silhouette (not placeholder)
And: Dimensions shown: 512×512
And: Format shown: PNG
```

### Test 2: Individual Size Change
```
Scenario: Customize size for single image
Given: Image 1 (512×512) with default size 20
And: Image 2 (1200×800) with default size 20
When: User changes Image 1 size to Fixed 15
Then: Image 1 shows "Output: 15×15"
And: Image 2 still shows "Output: 20×20"
And: "Apply to All" doesn't change Image 1 (only if clicked)
```

### Test 3: Size Algorithm Verification
```
Scenario: Max size calculation for different images
Given: Image A: 512×512 → Expected max: 30
Given: Image B: 1200×800 → Expected max: 30
Given: Image C: 256×128 → Expected max: 30 (clamped)
When: User selects "Max" mode
Then: All show correct predicted size
And: All are within 10-30 range
```

---

## Summary of Findings

| Issue | Severity | Status | Fix Effort |
|-------|----------|--------|------------|
| Image previews placeholder | HIGH | Needs fix | Medium |
| Size UI clarity | MEDIUM | Improve UX | Low |
| Size algorithm verification | MEDIUM | Review code | Low |

**Next Phase:** CARD-004t (Cleanup) should include these fixes before production deployment.

