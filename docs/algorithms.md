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

The generation follows retry-bounded loops with multiple decision points (POL-001 through POL-005, ADR-0002):

```
START
  ↓
PARSE REQUEST & VALIDATE (size, mode, difficulty, image path, etc.)
  ↓
RESOLVE EXTENT (apply source's shape if bare --size N given)
  ↓
RANDOM SEED (draw OS entropy if not provided)
  ↓
FOR random/library modes:
  RESAMPLE LOOP (retry_counter < 20):
    REGENERATE LOOP (retry_counter < 20, shared budget):
      ├─ SOURCE GRID (random draw or library re-render)
      ├─ COMPUTE CLUES (run-length encoding)
      ├─ UNIQUENESS CHECK (solver.solve: 0, 1, or ≥2 solutions)
      ├─ If solution_count ≠ 1 → reject, regenerate
      ├─ DIFFICULTY SCORE (off solver signals, not a second solve)
      └─ Return scored candidate
    │
    ├─ DIFFICULTY TIER CHECK (does candidate match --difficulty?)
    ├─ If score in tier → SUCCESS, exit loops
    └─ If ≠ tier → reject candidate, resample (try regenerate loop again)
  │
  └─ If no success after 20 attempts → POL-005: Abandon, report reason

FOR image mode:
  ├─ SOURCE GRID (convert image once via Floyd-Steinberg dithering)
  ├─ COMPUTE CLUES
  ├─ UNIQUENESS CHECK
  ├─ If solution_count = 1 → Continue to tier check
  │
  ├─ Else (not unique):
  │   NUDGE LOOP (retry_counter < 5):
  │     ├─ Nudge: flip one more pixel of the original conversion
  │     ├─ COMPUTE CLUES & UNIQUENESS CHECK
  │     └─ If solution_count = 1 → SUCCESS, exit nudge loop
  │   │
  │   └─ If no success after 5 nudges → POL-003: Abandon, stop altering image
  │
  ├─ DIFFICULTY TIER CHECK
  ├─ If score not in tier → Abandon (no tier recovery for image mode)
  └─ SUCCESS → EXPORT

EXPORT (all modes):
  └─ Write in requested format(s): PNG/SVG/JSON/CSV/PDF
END
```

## Random Grid Generation

**Component:** COMP-003 (Sourcing)

### Input
- `width`, `height`: Grid dimensions (10-30 cells each, validated independently)
- `density`: 0-100% (percentage of filled cells, validated before any draw)
- `rng`: Seeded random.Random instance (ADR-0015, for reproducibility)

### Algorithm

```
ALGORITHM:
  1. Validate extent: each side must be in [10, 30] (AC-069/AC-070)
  2. Validate density: must be in (0, 100) range (AC-011)
  3. Calculate target_filled = (width × height) × (density / 100)
  4. Create flat list: [True] * target_filled + [False] * (total - target_filled)
  5. Shuffle list in-place using rng (deterministic with same seed)
  6. Reshape flat list into 2D grid: [width, height] row-major
  7. RETURN grid as list[list[bool]]
```

### Density Accuracy (ADR-0003)

The filled fraction is within ±3 percentage points **by construction**:
- Compute exact target cell count (one value, not stochastic)
- Shuffle exact positions (no probability per cell)
- Only error: rounding of fractional cells (max ±0.5 cells, << 3 points)
- Holds at the smallest grid (10×10): no randomness can break the guarantee

### Constraints

- **Size:** 10×10 to 30×30 (per side, inclusive)
- **Density:** 0-100% (exclusive boundaries, validated before drawing)
- **Seeded:** Same seed + size + density = same grid (reproducible)
- **Density Accuracy:** Within ±3 percentage points (by construction, not by chance)

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
- `deadline`: (optional) Absolute monotonic deadline for cooperative timeout (ADR-0011)

### Output
- `solution_count`: 0 (no solutions), 1 (unique), or MANY=2 (≥2 solutions)
- `solution`: The complete grid if solution_count==1, else None
- `signals`: FR-009 difficulty metrics from the solve

### Algorithm

```
ALGORITHM:
  1. LINE PROPAGATION (constraint propagation)
     ├─ For each line: compute ALL valid placements
     ├─ Find cells that are filled in ALL placements
     ├─ Find cells that are empty in ALL placements
     ├─ Propagate deduced cells across perpendicular lines
     └─ Repeat until fixed point (no new deductions)
     └─ Check timeout at each fixed point (ADR-0011)

  2. SOLUTION COUNTING
     ├─ IF line-logic alone produces complete grid
     │  └─ solution_count = 1, RETURN (success)
     ├─ IF contradiction found
     │  └─ solution_count = 0, RETURN (impossible)
     └─ BACKTRACKING SEARCH
        ├─ Find unknown cell with most constraints
        ├─ Try filled: recursive solve
        ├─ If valid solution found: increment count
        ├─ Try empty: recursive solve
        ├─ If valid solution found: increment count
        ├─ If count ≥ 2: RETURN MANY (fail-fast)
        └─ Check timeout before each branch (ADR-0011)
```

### Performance Characteristics

| Scenario | Time | Method |
|----------|------|--------|
| Easy/Dense grids | ~1ms | Line-logic only |
| Mid-density grids | ~100-500ms | Some backtracking |
| Hard grids at 40×40+ | ~1-10s | Extensive search |

### Critical Properties

**Must NEVER false-positive:** The solver must never report a puzzle as uniquely solvable when it actually has 0 or ≥2 solutions (INV-002). This is verified by the mandatory cross-check property test (`tests/property/test_solver_uniqueness.py`) which runs the solver against an independent brute-force oracle.

**Fail-fast at 2 solutions:** The search stops the instant a second distinct solution is found (AC-017). It never counts further — this is what makes uniqueness checking affordable to call on every candidate in the regenerate loop.

**Cooperative timeout:** Respects ADR-0011's generation deadline (30s per request, shared across all retries). Raises `SolverTimeout` on exhaustion; does not return an answer.

## Difficulty Scoring

**Component:** COMP-006 (Difficulty)

### Input
- `solution_grid`: The solution grid
- `clues`: Row and column clues
- `solver_signals`: Metrics from the solver

### Algorithm

```
ALGORITHM:
  1. Collect solver signals (from the uniqueness check solve):
     ├─ line_logic_cells: cells settled by line logic alone
     ├─ total_cells: grid area
     ├─ branch_nodes: search nodes expanded beyond line logic
     └─ elapsed_seconds: wall-clock time for entire solve

  2. Normalize signals to 0..1 scale:
     ├─ line_logic_gap = 1 - (line_logic_cells / total_cells)
     ├─ branch_pressure = min(branch_nodes / total_cells, 1.0)
     ├─ time_pressure = min(elapsed_seconds / size_budget, 1.0)
     ├─ size_pressure = (grid_area - 100) / 800 (clamped to 0..1)
     └─ density_pressure based on clue counts (how full/empty)

  3. Compute effort score (ADR-0013 formula):
     effort = 0.40 * line_logic_gap
            + 0.45 * branch_pressure
            + 0.15 * time_pressure

  4. Apply relief factor (structural difficulty normalizer):
     relief = 1.0 - 0.15 * (1 - size_pressure)
                   - 0.15 * (1 - density_pressure)

  5. Final score (0..100 scale):
     score = 100 * effort * relief

  6. Map to tier (ADR-0005's equal bands):
     ├─ score ∈ [0, 33] → Easy
     ├─ score ∈ (33, 66] → Medium
     └─ score ∈ (66, 100] → Hard

  7. RETRY LOOP:
     If computed_tier ≠ requested_tier:
       → Regenerate candidate (retry up to 20 times, shared budget)
```

### Key Properties

- **No second solve:** Scores off signals from the uniqueness check only (FR-009)
- **Size and density are normalizers:** Act multiplicatively, never additively
- **AC-023 guarantee:** A puzzle solved entirely by line logic scores ≤ 15 points (Easy)
- **Fail-fast heuristic:** Not calibrated machine learning; based on ADR-0013 tuning
- **Shared retry budget:** Regenerate and resample loops share one 20-attempt budget

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
     ├─ Bounded pixel nudge (POL-002, up to 5 attempts max per ADR-0002):
     │  ├─ Flip one more pixel of the original conversion
     │  ├─ Prioritize pixels by: switch participation, boundary position, centre
     │  ├─ Re-check uniqueness on nudged grid
     │  └─ If solution_count = 1 → SUCCESS
     ├─ If still not unique after 5 nudges:
     │  └─ Report error to user (POL-003: stop altering image)
```

### Output
Uniquely-solvable nonogram derived from the image

### Floyd-Steinberg Dithering Details

The dithering algorithm distributes quantization error to neighboring pixels:

```
        X    7/16   (right)
  3/16  5/16  1/16  (left, down, right-down)
  (left, down, right-down neighbors)
```

Pillow's `Image.convert("1")` implements Floyd-Steinberg as its default 1-bit dither (ADR-0006). Error propagation passes quantization error to 4 neighbors using the weights above, producing high-quality binary images from grayscale input without pure thresholding artifacts.

## Size Discovery & Validation

**Component:** COMP-001 (CLI) + Domain Validation

The system doesn't have a "suggested size" algorithm per se. Instead, it **accepts user-specified sizes within valid ranges**.

### v1.0 Specification (CON-011, NFR-001)

- **Supported:** 10 to 30 cells per side (inclusive), both dimensions validated independently
- **Validation:** Domain function in `random_grid.validate_extent()` (not CLI layer per ADR-0010)
- **Out-of-range:** Rejected with `SizeOutOfRange` error before any grid is sourced
- **Rectangle, not square:** Extent is always a (width, height) pair; a bare `--size N` is completed by the source's shape

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
