# Issue: Size Configuration Should Respect Image Aspect Ratio

**Status:** 🔴 OPEN - Needs Implementation  
**Severity:** MEDIUM  
**Found By:** User Review  
**Date:** 2026-09-08

---

## Problem Statement

Current implementation creates square puzzles regardless of input image aspect ratio.

**What's wrong:**
- Size value (20) produces 20×20 grid for ALL images
- Works for square images (512×512 → 20×20) ✓
- Wrong for rectangular images:
  - 1920×1080 landscape → 20×20 ✗ (should be ~36×20)
  - 600×1000 portrait → 20×20 ✗ (should be ~12×20)

**Expected behavior:**
- Size value (20) = MINIMUM dimension of output puzzle
- Other dimension calculated from image aspect ratio
- Maintains image proportions in puzzle

---

## Root Cause

**File:** `src/nonogram/admin/image_manager.py`

**Current predict_size() returns single dimension:**
```python
def predict_size(self) -> int:
    # ... calculation ...
    return size_value  # Only ONE value
```

**Problem:** Both width and height end up being the same value, creating square puzzles.

---

## Solution

### Update predict_size() to return (width, height) tuple:

```python
def predict_size(self) -> tuple:
    """Predict (width, height) respecting aspect ratio."""
    img_width, img_height = self.dimensions
    aspect_ratio = img_width / img_height
    
    # Calculate minimum dimension
    if self.size_mode == "fixed":
        min_size = self.size_value
    elif self.size_mode == "max":
        min_size = min(img_width // 2, img_height // 2, 30)
    else:  # min
        min_size = max(10, (min(img_width // 2, img_height // 2)) - 5)
    
    # Calculate other dimension from aspect ratio
    if img_width >= img_height:  # Landscape
        width = int(min_size * aspect_ratio)
        height = min_size
    else:  # Portrait
        width = min_size
        height = int(min_size / aspect_ratio)
    
    # Clamp both to 10-30
    width = max(10, min(width, 30))
    height = max(10, min(height, 30))
    
    return (width, height)
```

---

## Test Cases

| Image | Aspect | Size | Expected | Notes |
|-------|--------|------|----------|-------|
| 512×512 | 1.0 | 20 | 20×20 | Square stays square |
| 1920×1080 | 1.78 | 20 | 36×20 | Landscape preserved |
| 600×1000 | 0.6 | 20 | 12×20 | Portrait preserved |
| 1024×768 | 1.33 | 20 | 27×20 | Maintains aspect |

---

## Files to Update

1. `src/nonogram/admin/image_manager.py` - predict_size() method
2. `src/nonogram/admin/templates/image_preview.html` - Show both dims
3. `src/nonogram/admin/batch_generator.py` - Use both width/height
4. Tests - Update expectations

---

## Acceptance Criteria

- [ ] predict_size() returns (width, height)
- [ ] Size = minimum dimension only
- [ ] Other dimension from aspect ratio
- [ ] Both clamped to 10-30
- [ ] Templates show "W×H grid"
- [ ] Batch generator creates rectangular grids
- [ ] All tests passing

---

**Priority:** Should fix before CARD-004t  
**Component:** Wave 3 Size Configuration
