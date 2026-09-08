# Image-to-Nonogram Quality Metrics

**Purpose:** Measure how well a generated nonogram preserves the original image  
**Status:** MVP Implementation Complete  
**Version:** 1.0 (POC)

---

## Overview

When converting an image to a nonogram puzzle, not all conversions are equally good. Some preserve the original subject clearly; others lose important details. The quality metric system measures this preservation on a scale of 1-100.

**Use case:** Admin panel can filter generated puzzles by quality and only include high-quality ones in books.

---

## Quality Components

### 1. Visual Similarity (50% weight)

**What it measures:** Pixel-level match between original image and generated grid.

**How it works:**
- Convert original image to binary (black/white)
- Resize to match grid dimensions (nearest-neighbor)
- Compare cell-by-cell
- Score = `matching_cells / total_cells`

**Example:**
- Perfect match: 100/100 cells match → 1.0 similarity
- Complete opposite: 0/100 cells match → 0.0 similarity
- 80 matching, 20 different → 0.80 similarity

**Why 50%:** Most important factor—if pixels don't match, puzzle doesn't represent the image.

### 2. Silhouette Match (35% weight)

**What it measures:** Edge/outline preservation.

**How it works:**
- Detect edges in both original and grid (4-connectivity)
- Compare edge pixels
- Score = `overlapping_edges / total_edges`

**Example:**
- Original has clear outline, grid preserves it → high score
- Original has clear outline, grid fills it → low score
- Original is noisy, grid smooths it → medium-high score (some improvement)

**Why 35%:** Silhouette is what humans recognize most. A person can identify a face from just its outline.

### 3. Density Match (15% weight)

**What it measures:** Proportion of filled cells.

**How it works:**
- Calculate fill ratio in original: `filled_cells / total_cells`
- Calculate fill ratio in grid: `filled_cells / total_cells`
- Score = `1.0 - abs(original_density - grid_density)`

**Example:**
- Original: 25% filled, Grid: 25% filled → 1.0 density match
- Original: 25% filled, Grid: 75% filled → 0.50 density match (very different)

**Why 15%:** Less critical than visual or silhouette, but still indicates overall character.

---

## Recognizability Classification

Based on combined quality score:

| Score | Recognizability | Meaning |
|-------|-----------------|---------|
| 80-100 | **HIGH** | Clear, unmistakable representation |
| 50-79 | **MEDIUM** | Recognizable but some details lost |
| 1-49 | **LOW** | Difficult to identify original image |

---

## Overall Quality Score

```
quality_score = (visual * 0.50 + silhouette * 0.35 + density * 0.15) * 100
quality_score = max(1, min(100, quality_score))  # Clamp 1-100
```

---

## Examples

### Example 1: Perfect Quality (Score 100)

Original image: Black square on white background  
Generated grid: Same black square on white grid

```
Metrics:
  Visual similarity:    100%  (all pixels match)
  Silhouette match:     100%  (edges match perfectly)
  Density match:        100%  (25% filled both)
  Calculation: (1.0 * 0.50) + (1.0 * 0.35) + (1.0 * 0.15) = 1.0 = 100 points
  Recognizability: HIGH ✓
```

### Example 2: Medium Quality (Score 60)

Original image: Portrait photo  
Generated grid: Recognizable as face, but some features lost

```
Metrics:
  Visual similarity:     70%  (outline matches, details fuzzy)
  Silhouette match:      85%  (face outline preserved)
  Density match:         65%  (slightly more/fewer filled cells)
  Calculation: (0.70 * 0.50) + (0.85 * 0.35) + (0.65 * 0.15) = 0.74 = 74 points
  Recognizability: MEDIUM ~
```

### Example 3: Poor Quality (Score 25)

Original image: Detailed landscape  
Generated grid: Hard to recognize as landscape

```
Metrics:
  Visual similarity:     30%  (many pixels mismatched)
  Silhouette match:      40%  (edges mostly lost)
  Density match:         15%  (dramatically different fill)
  Calculation: (0.30 * 0.50) + (0.40 * 0.35) + (0.15 * 0.15) = 0.27 = 27 points
  Recognizability: LOW ✗
```

---

## Implementation

### Core Module: `src/nonogram/analysis/quality_metric.py`

```python
from PIL import Image
from src.nonogram.analysis import measure_quality

# Load original image and generated grid
original = Image.open("photo.jpg")
puzzle_grid = [[True, False, True, ...], ...]

# Measure quality
metrics = measure_quality(original, puzzle_grid)

print(f"Quality Score: {metrics.quality_score}/100")
print(f"Recognizability: {metrics.recognizability.value}")
print(f"Visual Similarity: {metrics.visual_similarity:.1%}")
print(f"Silhouette Match: {metrics.silhouette_match:.1%}")
print(f"Density Match: {metrics.density_match:.1%}")
```

### Integration Points

**Where used:**
1. **Puzzle Generator** → After grid generated, calculate quality
2. **Admin Panel** → Display quality score for each puzzle
3. **Database** → Store quality_score, recognizability in nonograms table
4. **Filtering** → Admin can exclude low-quality puzzles (< 60 score)

**Database Fields (Nonogram table):**
```sql
quality_score INT              -- 1-100
recognizability VARCHAR        -- 'high', 'medium', 'low'
```

---

## Validation & Tuning

### Empirical Testing

To validate quality scoring, test with real images:

```
Image Type      Quality Score  Expected Tier  Verification
Simple logo     92            HIGH           ✓ Clearly recognizable
Portrait        65            MEDIUM         ~ Some features visible
Landscape       42            LOW            ✗ Hard to identify
Detailed text   18            LOW            ✗ Text not readable
```

Adjust weights (0.50 / 0.35 / 0.15) if needed based on user feedback.

### Performance Impact

Quality calculation should be fast:
- v1 generation time: 100ms (baseline)
- v2 + quality calculation: 105-110ms (< 15% overhead)
- Acceptable: < 200ms per puzzle

If slow, optimize:
- Cache binary image conversion
- Use scipy's edge detection instead of custom
- Resample image once, reuse for all metrics

---

## Known Limitations (v1)

1. **No learning:** Uses fixed thresholds and weights
2. **Binary only:** Compares 0/1 pixels, no grayscale
3. **No style adaptation:** Same scoring for photos, logos, drawings
4. **Fixed resize:** Always uses nearest-neighbor (could try bilinear)

**Future improvements (v2+):**
- Train weights on user ratings
- Support grayscale quality (not just binary)
- Different scoring for different image types
- Better edge detection (Canny, Sobel)

---

## References

- **Quality Metric Tests:** tests/test_quality_metric.py
- **Difficulty Engine:** docs/DIFFICULTY_ENGINE.md
- **Image Processing:** Uses PIL (Pillow), NumPy

---

**Last Updated:** 2026-09-06  
**Status:** ✅ MVP Complete  
**Next:** Integrate with puzzle generator pipeline
