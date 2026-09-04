# Nonogram Generation Algorithms

Technical documentation of the nonogram puzzle generation and solving algorithms used in the nonogram generator (v1.0).

## Table of Contents

1. [Main Generation Pipeline](#main-generation-pipeline)
2. [Random Grid Generation](#random-grid-generation)
3. [Clue Computation](#clue-computation)
4. [Uniqueness Solver](#uniqueness-solver)
5. [Difficulty Scoring](#difficulty-scoring)
6. [Image Conversion Pipeline](#image-conversion-pipeline)
7. [Size Discovery & Validation](#size-discovery--validation)
8. [Summary](#summary)

## Main Generation Pipeline

**Component:** COMP-002 (Orchestrator)

The generation follows a retry-bounded loop with multiple decision points:

```
START
  ↓
PARSE REQUEST (size, mode, difficulty, etc.)
  ↓
LOOP (retry_counter < MAX_RETRIES):
  ├─ SOURCE GRID
  │   ├─ Random: Generate random grid at requested density
  │   ├─ Library: Load built-in template image
  │   └─ Image: Convert uploaded image via dithering
  │
  ├─ COMPUTE CLUES
  │   └─ Run-length encoding: Row & column clues
  │
  ├─ UNIQUENESS CHECK
  │   ├─ Solver: Count solutions (0, 1, or ≥2)
  │   ├─ If 1 solution → Continue
  │   └─ If ≠1 → Regenerate, retry loop
  │
  ├─ DIFFICULTY SCORING
  │   ├─ Heuristic scoring: solver signals
  │   ├─ Map to tier: Easy/Medium/Hard
  │   ├─ If matches requested tier → Continue
  │   └─ If ≠ tier → Resample, retry loop
  │
  └─ EXPORT
      └─ PNG/SVG/JSON/CSV/PDF formats
END
```

## Random Grid Generation

**Component:** COMP-003 (Sourcing)

### Input
- `size`: W×H (grid dimensions)
- `density`: 0-100% (percentage of filled cells)
- `seed`: Random seed for reproducibility

### Algorithm

```
ALGORITHM:
  1. Calculate target_filled = (W×H) × (density/100)
  2. Create empty grid
  3. Generate random indices for target_filled cells
  4. Shuffle indices using seeded RNG
  5. Mark first target_filled cells as filled
  6. Verify density is within ±3% tolerance
  7. RETURN grid as list[list[bool]]
```

### Constraints

- **Size:** 10×10 to 50×50 (v1.0) or 10×10 to 30×30 (documented minimum)
- **Density:** 0-100% (exclusive boundaries)
- **Seeded:** Same seed + size = same grid (reproducible)

## Clue Computation

**Component:** COMP-004 (Clues)

### Input
- `solution_grid`: list[list[bool]]

### Algorithm (per line - row or column)

```
ALGORITHM:
  1. Scan left-to-right: Find contiguous filled runs
  2. Record run lengths in tuple: (len1, len2, len3, ...)
  3. Empty line → (0,) NOT ()
  4. Full line → (width,)
```

### Examples

| Pattern | Clue |
|---------|------|
| ██·███·· | (2, 3) |
| ········ | (0,) |
| ████████ | (8,) |

### Output
- `tuple[tuple[int, ...], ...]` for rows and columns

## Uniqueness Solver

**Component:** COMP-005 (Solver)

### Input
- `row_clues`: Clues for each row
- `column_clues`: Clues for each column

### Algorithm

```
ALGORITHM:
  1. LINE PROPAGATION
     ├─ For each line: compute ALL valid placements
     ├─ Find cells that are filled in ALL placements
     ├─ Find cells that are empty in ALL placements
     ├─ Propagate deduced cells across perpendicular lines
     └─ Repeat until fixed point (no new deductions)

  2. SOLUTION COUNTING
     ├─ IF line-logic alone produces complete grid
     │  └─ solution_count = 1, RETURN
     ├─ IF contradiction found
     │  └─ solution_count = 0, RETURN
     └─ BACKTRACKING SEARCH
        ├─ Pick most-constrained unknown cell
        ├─ Try filled: recursive solve
        ├─ If valid solution found: increment count
        ├─ Try empty: recursive solve
        ├─ If valid solution found: increment count
        ├─ If count > 1: STOP (fail-fast)
        └─ RETURN count (0, 1, or MANY)
```

### Performance Characteristics

| Scenario | Time | Method |
|----------|------|--------|
| Easy/Dense grids | ~1ms | Line-logic only |
| Mid-density grids | ~100-500ms | Some backtracking |
| Hard grids at 40×40+ | ~1-10s | Extensive search |

### Critical Property

**Must NEVER false-positive:** The solver must never report a puzzle as uniquely solvable when it actually has 0 or ≥2 solutions. This is verified by the mandatory property test (`tests/property/test_solver_uniqueness.py`).

## Difficulty Scoring

**Component:** COMP-006 (Difficulty)

### Input
- `solution_grid`: The solution grid
- `clues`: Row and column clues
- `solver_signals`: Metrics from the solver

### Algorithm

```
ALGORITHM:
  1. Collect solver signals:
     ├─ cells_solved_by_line_logic (early deductions)
     ├─ backtracking_depth (search depth needed)
     ├─ solver_time (milliseconds)
     └─ grid_size (area in cells)

  2. Compute heuristic score:
     score = weighted_combination(
       cells_solved_by_line_logic * 0.3,
       backtracking_depth * 0.3,
       solver_time * 0.2,
       grid_area * 0.2
     )

  3. Map to tier:
     ├─ score < T1 → Easy
     ├─ T1 ≤ score < T2 → Medium
     └─ score ≥ T2 → Hard

  4. RETRY LOOP:
     If computed_tier ≠ requested_tier:
       → Regenerate candidate (retry up to 20 times)
```

### Key Properties

- Uses solver signals, not just puzzle size
- Heuristic-based (not exhaustive brute-force)
- Regenerates on difficulty mismatch

## Image Conversion Pipeline

**Component:** COMP-003 (Image Sourcing)

### Input
- `user_image`: JPEG/PNG/etc.
- `target_size`: W×H grid dimensions

### Algorithm

```
ALGORITHM:
  1. Load image (JPEG/PNG/etc via PIL)
  2. Convert to grayscale
  3. Find ink bounding box (trim white borders)
  4. Resize to target_size using aspect-preserving crop
  5. Floyd-Steinberg dithering:
     ├─ For each pixel:
     │  ├─ Compare to 50% threshold
     │  ├─ If above: set to white, distribute error
     │  └─ If below: set to black, distribute error
     └─ Error distribution coefficients: [7/16, 3/16, 5/16, 1/16]
  6. Binarize to grid (white=empty, black=filled)
  7. Run uniqueness check

  8. If NOT unique (0 or >1 solutions):
     ├─ Bounded pixel nudge:
     │  ├─ Flip candidate pixels in ambiguous regions
     │  ├─ Re-check uniqueness (up to 10 attempts)
     │  └─ If success: use nudged grid
     ├─ If still not unique:
     │  └─ Report error to user (retry with different image)
```

### Output
Uniquely-solvable nonogram derived from the image

### Floyd-Steinberg Dithering Details

The dithering algorithm distributes quantization error to neighboring pixels using these weights:

```
        X    7/16
  3/16  5/16  1/16
```

Where X is the current pixel. This produces high-quality binary images from grayscale input.

## Size Discovery & Validation

**Component:** COMP-001 (CLI) + Domain Validation

The system doesn't have a "suggested size" algorithm per se. Instead, it **accepts user-specified sizes within valid ranges**.

### v1.0 Specification

- **Supported:** 10×10 to 30×30 (per side)
- **Validation:** Domain function (not CLI layer)
- **Out-of-range:** Rejected with `NonogramError`

### Practical Guidance

| Grid Size | Generation Time | Typical Difficulty |
|-----------|-----------------|-------------------|
| 10×15 | ~1 second | Easy |
| 20×20 | ~2-5 seconds | Easy-Medium |
| 30×30 | ~10+ seconds | Medium-Hard |

### For IMAGE MODE

Size is determined by:
1. User specifies desired grid size
2. Image is resized to that grid size
3. Aspect ratio is preserved (crop if needed)

**Note:** Smaller target sizes = higher detail loss in conversion

## Summary

### Generation Algorithm Overview

The generation algorithm is a **bounded-retry pipeline** that:

1. Generates a candidate solution grid (random/library/image)
2. Computes clues via run-length encoding
3. Verifies uniqueness with a constraint-propagation solver
4. Scores difficulty with solver signals
5. Regenerates if validation fails (uniqueness or difficulty mismatch)
6. Exports in requested format(s)

### Critical Components

| Component | Role | Critical Property |
|-----------|------|-------------------|
| **Uniqueness Solver** | Verifies exactly 1 solution exists | Must NEVER false-positive (report unique when ambiguous) |
| **Line Logic** | Fast constraint propagation | Solves easy/dense grids without backtracking (~1ms) |
| **Backtracking** | Exhaustive solution search | Fail-fast at 2 solutions (avoid full enumeration) |
| **Difficulty Heuristic** | Maps puzzles to Easy/Medium/Hard | Uses solver signals (not just puzzle size) |

### Key Guarantee

✅ **All exported puzzles have exactly 1 solution guaranteed.**

---

**Document Version:** 1.0 (Nonogram Generator v1.0)  
**Last Updated:** 2026-09-04  
**Components Referenced:** COMP-001 through COMP-008  
**Architecture:** See CLAUDE.md for component dependencies and design principles
