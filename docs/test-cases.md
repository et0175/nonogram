# Test Cases — Nonogram Generator

## Traceability: Acceptance Criteria to Test Cases

| AC | Title | Verified By | Status |
|---|-------|-------------|--------|
| AC-001 | Random grid generation | TC-003-001, TC-003-002, TC-003-003 | ✓ |
| AC-002 | Library template loading | TC-003-004, TC-003-005 | ✓ |
| AC-006 | Invalid library key rejection | TC-003-004 (error case) | ✓ |
| AC-008 | Missing image file error | TC-003-006 (error case) | ✓ |
| AC-021 | Unsupported difficulty tier rejection | Test suite | ✓ |
| AC-050 | Out-of-range size rejected like CLI | Test suite | ✓ |
| AC-052 | Server loopback-only binding | Test suite | ✓ |
| AC-053 | Web UI requires no credentials | Test suite | ✓ |
| AC-123 | Error displays inline with form | test_the_page_displays_error_inline_with_form_ac_123 | ⚠️ Failing |

---

## Test Organization

Tests are organized by **component** (COMP-001..008) and **quality dimension** (unit, integration, property, UI).

| Component | Purpose | Modules |
|-----------|---------|---------|
| COMP-001 | CLI adapter | src/nonogram/cli.py |
| COMP-002 | Orchestrator | src/nonogram/orchestrator.py |
| COMP-003 | Sourcing | src/nonogram/sourcing/ |
| COMP-004 | Clue computation | src/nonogram/clues.py |
| COMP-005 | Solver | src/nonogram/solver/ |
| COMP-006 | Difficulty | src/nonogram/difficulty.py |
| COMP-007 | Export | src/nonogram/export/ |
| COMP-008 | Web UI | src/nonogram/web/ |

---

## COMP-001: CLI Adapter Tests

### TC-001-001: Basic Argument Parsing

**Test Level:** Unit  
**Location:** tests/test_cli.py::test_basic_parsing

**Given:**
```bash
nonogram generate --mode random --size 20 --density 30 --difficulty Easy
```

**When:**
The CLI argument parser processes the tokens

**Then:**
- [ ] A `GenerationRequest` object is created
- [ ] `request.mode == "random"`
- [ ] `request.size == (20, None)` (bare N defers to domain)
- [ ] `request.density == 30`
- [ ] `request.difficulty == "Easy"`
- [ ] No exceptions are raised

---

### TC-001-002: Rectangular Size Token

**Test Level:** Unit  
**Location:** tests/test_cli.py::test_rectangular_size

**Given:**
```bash
nonogram generate --mode random --size 20x30
```

**When:**
The CLI parser encounters the "NxM" token

**Then:**
- [ ] `request.size == (20, 30)`
- [ ] Both dimensions are parsed correctly
- [ ] No spaces around the 'x' are required

---

### TC-001-003: Bare Size Token (Backward Compatibility)

**Test Level:** Unit  
**Location:** tests/test_cli.py::test_bare_size_token

**Given:**
```bash
nonogram generate --mode random --size 25
```

**When:**
CLI parser processes the token

**Then:**
- [ ] `request.size == (25, None)` (NOT (25, 25))
- [ ] The unspecified dimension is completed inward by the domain
- [ ] Allows distinction between bare N and explicit NxN

---

### TC-001-004: Invalid Size Token Rejection

**Test Level:** Unit  
**Location:** tests/test_cli.py::test_invalid_size_tokens

**Given:**
Any of: `--size 30x`, `--size x20`, `--size 30x20x10`, `--size 30.5`

**When:**
CLI parser processes the token

**Then:**
- [ ] Argument parsing rejects the token
- [ ] Error message indicates valid format: "Size must be 'N' or 'NxM'"
- [ ] Program exits with non-zero code

---

### TC-001-005: Out-of-Range Size (Domain Validation)

**Test Level:** Unit  
**Location:** tests/test_cli.py::test_out_of_range_size

**Given:**
```bash
nonogram generate --mode random --size 60x60
```

**When:**
CLI passes to domain orchestrator

**Then:**
- [ ] CLI successfully parses and passes to domain
- [ ] Domain validates and rejects (10..30 range)
- [ ] Error message is from domain, not CLI: "Grid dimensions must be 10..30"
- [ ] This distinguishes parsing errors (CLI) from validation errors (domain)

---

### TC-001-006: Help Text Completeness

**Test Level:** UI  
**Location:** tests/test_cli.py::test_help_text

**When:**
`nonogram --help` or `nonogram generate --help`

**Then:**
- [ ] Help text lists all valid modes: random, library, image
- [ ] Help text lists all difficulty tiers: Easy, Medium, Hard
- [ ] Help text lists all export formats: png, svg, json, csv, pdf
- [ ] Example commands are provided
- [ ] Size format is documented: "N or NxM (e.g., 20 or 20x30)"
- [ ] Library keys are listed or referenced

---

## COMP-003: Sourcing Tests

### TC-003-001: Random Grid Generation

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_random_grid.py::test_random_grid_basic

**Given:**
- Size: (20, 20)
- Density: 30
- Seed: 42

**When:**
`random_grid.generate(size=(20, 20), density=30, seed=42)`

**Then:**
- [ ] Returns a `list[list[bool]]` of shape (20, 20)
- [ ] Approximately 30% of cells are True
- [ ] Seeded invocation with same seed produces identical grid
- [ ] Different seed produces different grid

---

### TC-003-002: Density Boundary Cases

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_random_grid.py::test_density_boundaries

**Given:**
Density values: 0, 1, 50, 99, 100

**When:**
Random grids are generated with each density

**Then:**
- [ ] Density 0: all cells are False (empty grid)
- [ ] Density 100: all cells are True (full grid)
- [ ] Intermediate densities produce expected fill percentages (±5%)

---

### TC-003-003: Rectangular Random Grid

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_random_grid.py::test_rectangular_random

**Given:**
- Size: (25, 15)
- Density: 40

**When:**
Random grid is generated with rectangular size

**Then:**
- [ ] Grid shape is exactly (25, 15)
- [ ] All 375 cells are either True or False
- [ ] Density is approximately 40%
- [ ] Grid is not square-forced or stretched

---

### TC-003-004: Library Template Loading

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_library.py::test_library_loading

**Given:**
Library key "cat"

**When:**
`library.get_template("cat")`

**Then:**
- [ ] A `list[list[bool]]` is returned
- [ ] Shape is (16, 16) or larger
- [ ] Grid contains only pure black/white (True/False)
- [ ] Grid is not empty (has filled cells)

---

### TC-003-005: All Built-in Templates

**Test Level:** Integration  
**Location:** tests/test_sourcing/test_library.py::test_all_templates_exist

**When:**
Each registered library key is queried

**Then:**
- [ ] At least 4 templates are registered
- [ ] All templates load without errors
- [ ] All templates are at least 16×16
- [ ] All templates are pure black/white

---

### TC-003-006: User Image Upload Conversion

**Test Level:** Integration  
**Location:** tests/test_sourcing/test_image.py::test_image_conversion_basic

**Given:**
- Image file: `tests/fixtures/cat_silhouette.jpg` (563×980)
- Target size: (20, 30)

**When:**
Image is loaded, greyscaled, and dithered to target size

**Then:**
- [ ] Output is a `list[list[bool]]` of shape (20, 30)
- [ ] Grid contains only True/False (pure black/white, no grey)
- [ ] Content from the source image is recognizable
- [ ] Image is not stretched; aspect-preserving crop is used

---

### TC-003-007: Image Trimming

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_image.py::test_image_trimming

**Given:**
Image with significant white borders (e.g., 50px border all around)

**When:**
Image is trimmed to ink bounding box (threshold <128)

**Then:**
- [ ] White borders are removed
- [ ] Ink bounding box is smaller than original
- [ ] Content is preserved and centered
- [ ] Result is used for aspect ratio checking and resizing

---

### TC-003-008: Image Aspect Ratio Refusal

**Test Level:** Integration  
**Location:** tests/test_sourcing/test_image.py::test_aspect_ratio_refusal

**Given:**
- Image: 200×1000 (ratio 0.2, trimmed)
- Requested grid: 15×30 (ratio 0.5)

**When:**
Image conversion is attempted

**Then:**
- [ ] Request is refused before any dithering
- [ ] Error message explains: "Image aspect ratio (0.2) differs from grid (0.5) by >2:1"
- [ ] Error suggests solution: "Try a different grid shape or crop the picture"
- [ ] No partial grid is generated

---

### TC-003-009: Boundary Case — Exactly 2:1 Mismatch

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_image.py::test_aspect_boundary_2x1

**Given:**
- Image: 200×600 (ratio 0.33, trimmed)
- Requested grid: 15×30 (ratio 0.5)
- Mismatch factor: 0.5/0.33 ≈ 1.5 (within 2:1)

**When:**
Request is evaluated

**Then:**
- [ ] Request is ACCEPTED (not refused)
- [ ] Mismatch is less than 2:1, so passes the guard
- [ ] Retains exactly 50% or more of image

---

### TC-003-010: Derived Grid Size from Portrait Image

**Test Level:** Integration  
**Location:** tests/test_sourcing/test_image.py::test_derived_size_portrait

**Given:**
- Image: 300×600 (portrait, ratio 0.5, trimmed)
- Bare size: 25 (longer side)

**When:**
Size derivation computes the shorter side

**Then:**
- [ ] Derived side = round(25 × 0.5) = round(12.5) = 12 (or 13)
- [ ] Clamped to MIN_SIZE: max(12, 10) = 12
- [ ] Final grid: 25×12 (wider than input)
- [ ] Retains 99% of content (vs 76% from square crop)

---

### TC-003-011: Clamping at MIN_SIZE

**Test Level:** Unit  
**Location:** tests/test_sourcing/test_image.py::test_size_clamping

**Given:**
- Image: 500×5000 (very tall, ratio 0.1, trimmed)
- Bare size: 15 (longer side)

**When:**
Derived side is computed: `round(15 × 0.1)` = 1.5 → 2 (after rounding)

**Then:**
- [ ] Computed value is 2, below MIN_SIZE=10
- [ ] Value is clamped: max(2, 10) = 10
- [ ] Final grid: 15×10 (both sides in range)
- [ ] Content retention is calculated and image is refused if <50%
- [ ] Error message: "Image is too tall for --size 15; try --size 25 or taller"

---

## COMP-004: Clue Computation Tests

### TC-004-001: Basic Clue Encoding

**Test Level:** Unit  
**Location:** tests/test_clues.py::test_encode_line_basic

**Given:**
Line: `[T, T, F, T, T, T, F, F]` (8 cells)

**When:**
`clues.encode_line(line)`

**Then:**
- [ ] Result is `(2, 3)`
- [ ] Runs of filled cells are correctly identified
- [ ] Gaps between runs are not included in output

---

### TC-004-002: All-Empty Line

**Test Level:** Unit  
**Location:** tests/test_clues.py::test_encode_empty_line

**Given:**
Line: `[F, F, F, F, F]` (all false)

**When:**
`clues.encode_line(line)`

**Then:**
- [ ] Result is `(0,)`, NOT `()`
- [ ] Empty lines encode as a single clue of 0

---

### TC-004-003: All-Filled Line

**Test Level:** Unit  
**Location:** tests/test_clues.py::test_encode_full_line

**Given:**
Line: `[T, T, T, T, T, T, T, T]` (8 cells, all true)

**When:**
`clues.encode_line(line)`

**Then:**
- [ ] Result is `(8,)`
- [ ] Single run of all cells

---

### TC-004-004: Grid-to-Clues Round-Trip

**Test Level:** Integration  
**Location:** tests/test_clues.py::test_grid_to_clues_roundtrip

**Given:**
A 10×10 grid with known pattern

**When:**
Row and column clues are computed, then used to solve back

**Then:**
- [ ] Clues preserve enough information to uniquely reconstruct the grid
- [ ] Reconstructed grid matches original exactly
- [ ] Works for any grid size and aspect ratio

---

## COMP-005: Solver Tests

### TC-005-001: Unique Solution Detection

**Test Level:** Property  
**Location:** tests/property/test_solver_uniqueness.py

**Given:**
100 valid nonogram puzzles from test corpus

**When:**
Solver runs on each puzzle and counts solutions

**Then:**
- [ ] Solver reports solution count = 1 for 100% of cases
- [ ] No false positives (puzzle actually has 1 solution)
- [ ] No false negatives (puzzle has 1 but solver says 0)

---

### TC-005-002: Impossible Puzzle Detection

**Test Level:** Unit  
**Location:** tests/test_solver.py::test_impossible_puzzle

**Given:**
Clues that are mutually contradictory (no solution exists)

**When:**
Solver attempts to find solutions

**Then:**
- [ ] Solver detects contradiction early
- [ ] Returns solution count = 0
- [ ] Does not waste time searching for non-existent solutions

---

### TC-005-003: Ambiguous Puzzle Detection (Fail-Fast)

**Test Level:** Unit  
**Location:** tests/test_solver.py::test_ambiguous_puzzle_failfast

**Given:**
Clues with 2+ valid solutions

**When:**
Solver searches for solutions with fail-fast mode enabled

**Then:**
- [ ] Solver finds first solution
- [ ] Solver continues searching and finds a second distinct solution
- [ ] Solver stops immediately upon finding second solution
- [ ] Returns solution count ≥ 2 (without enumerating all)
- [ ] Completes in reasonable time (not exhaustive search)

---

### TC-005-004: Constraint Propagation Effectiveness

**Test Level:** Unit  
**Location:** tests/test_solver.py::test_constraint_propagation

**Given:**
Simple puzzles solvable by line logic alone

**When:**
Solver runs constraint propagation phase

**Then:**
- [ ] Easy puzzles (10×10, low density) are solved without backtracking
- [ ] Solver tracks cells determined by propagation vs backtracking
- [ ] Performance is acceptable for typical sizes

---

## COMP-006: Difficulty Scoring Tests

### TC-006-001: Difficulty Score Range

**Test Level:** Unit  
**Location:** tests/test_difficulty.py::test_score_range

**When:**
Puzzles are scored

**Then:**
- [ ] Scores are numeric (e.g., 0..100 range)
- [ ] Easy puzzles score lower than Hard puzzles (on average)
- [ ] Score is deterministic (same puzzle, same score)

---

### TC-006-002: Tier Classification

**Test Level:** Unit  
**Location:** tests/test_difficulty.py::test_tier_classification

**Given:**
Puzzle with score 25

**When:**
Score is classified into a tier

**Then:**
- [ ] Score 0–33: Easy
- [ ] Score 34–66: Medium
- [ ] Score 67–100: Hard
- [ ] Thresholds match the implementation

---

### TC-006-003: Built-in Templates Always Score Easy

**Test Level:** Unit  
**Location:** tests/test_difficulty.py::test_builtin_easy

**Given:**
All 4 built-in library templates at 20×20

**When:**
Each is scored

**Then:**
- [ ] All score as Easy
- [ ] No built-in template scores Medium or Hard
- [ ] This is a documented property (pinned by test)

---

## COMP-007: Export Tests

### TC-007-001: PNG Export

**Test Level:** Integration  
**Location:** tests/test_export.py::test_export_png

**Given:**
A 20×20 puzzle

**When:**
`export.export_png(puzzle, "output.png")`

**Then:**
- [ ] PNG file is created
- [ ] Image contains grid lines and clues
- [ ] Clues are positioned on all four margins
- [ ] Cell size is appropriate for printing
- [ ] File is valid PNG (opens in image viewers)

---

### TC-007-002: SVG Export

**Test Level:** Integration  
**Location:** tests/test_export.py::test_export_svg

**Given:**
A 20×20 puzzle

**When:**
`export.export_svg(puzzle, "output.svg")`

**Then:**
- [ ] SVG file is created
- [ ] SVG is valid XML (passes validation)
- [ ] Renders correctly in web browsers
- [ ] Grid and clues are visually identical to PNG

---

### TC-007-003: JSON Export Round-Trip

**Test Level:** Integration  
**Location:** tests/test_export.py::test_json_roundtrip

**Given:**
A puzzle with known properties

**When:**
Puzzle is exported to JSON, then re-imported

**Then:**
- [ ] All fields match: width, height, row clues, column clues, solution, name, difficulty
- [ ] No data is lost
- [ ] Re-exported JSON is byte-identical

---

### TC-007-004: CSV Export Readability

**Test Level:** Integration  
**Location:** tests/test_export.py::test_csv_export

**Given:**
A 10×10 puzzle

**When:**
`export.export_csv(puzzle, "output.csv")`

**Then:**
- [ ] CSV file is created
- [ ] File is readable in spreadsheet software
- [ ] Format is intuitive (one row per grid row, clues separately)
- [ ] All puzzle data can be reconstructed from CSV

---

### TC-007-005: PDF Export — Page Count

**Test Level:** Integration  
**Location:** tests/test_export.py::test_pdf_pages

**Given:**
A puzzle with name "cat" and difficulty "Hard"

**When:**
`export.export_pdf(puzzle, "output.pdf")`

**Then:**
- [ ] PDF file is created
- [ ] PDF has exactly 2 pages
- [ ] File is readable by standard PDF viewers

---

### TC-007-006: PDF Export — Page 1 (Puzzle)

**Test Level:** Integration  
**Location:** tests/test_export.py::test_pdf_page1

**Then:**
- [ ] Page 1 contains blank grid (no solution)
- [ ] Clues are visible on all four margins
- [ ] Header shows: "cat — Hard"
- [ ] No solution cells are revealed

---

### TC-007-007: PDF Export — Page 2 (Answer Key)

**Test Level:** Integration  
**Location:** tests/test_export.py::test_pdf_page2

**Then:**
- [ ] Page 2 reveals the solution grid (all cells marked)
- [ ] Header shows: "cat — Hard" + "Answer Key"
- [ ] Clues are still visible
- [ ] Cells are clearly marked as filled/empty

---

### TC-007-008: File Naming Convention

**Test Level:** Unit  
**Location:** tests/test_export.py::test_filename_convention

**Given:**
Puzzle: name="eagle", size=(20, 25), difficulty="Medium"

**When:**
Export filenames are generated

**Then:**
- [ ] PNG: `eagle-20x25-Medium.png`
- [ ] SVG: `eagle-20x25-Medium.svg`
- [ ] PDF: `eagle-20x25-Medium.pdf`
- [ ] JSON: `eagle-20x25-Medium.json`
- [ ] CSV: `eagle-20x25-Medium.csv`
- [ ] Filenames are Windows-safe (no special characters)
- [ ] Non-ASCII names are preserved in filenames

---

## COMP-008: Web UI Tests

### TC-008-001: Server Startup

**Test Level:** UI  
**Location:** tests/test_web.py::test_server_startup

**When:**
`nonogram serve` is run

**Then:**
- [ ] Server starts without errors
- [ ] Server binds to 127.0.0.1:5000 (or configured port)
- [ ] Console shows: "Server running at http://localhost:5000"
- [ ] Server is ready to accept requests

---

### TC-008-002: Form Page Load

**Test Level:** UI  
**Location:** tests/test_web.py::test_form_page_load

**When:**
User navigates to http://localhost:5000

**Then:**
- [ ] Page loads (HTTP 200)
- [ ] Page title contains "Nonogram Generator"
- [ ] Form is visible with all fields:
  - Source selection (library OR image upload)
  - Grid size input
  - Difficulty selection
  - Export format checkboxes
  - Submit button

---

### TC-008-003: Form Validation — Invalid Size

**Test Level:** UI  
**Location:** tests/test_web.py::test_form_validation_size

**When:**
User enters size "30x" and submits

**Then:**
- [ ] Form is not submitted to server
- [ ] Error message appears: "Invalid size format. Use 'N' or 'NxM'"
- [ ] User can correct and resubmit

---

### TC-008-004: Random Generation via Web

**Test Level:** Integration  
**Location:** tests/test_web.py::test_web_random_generation

**Given:**
Form filled with:
- Source: random
- Size: 20
- Difficulty: Easy
- Formats: PNG, JSON

**When:**
Form is submitted

**Then:**
- [ ] Generation completes
- [ ] Response shows success message
- [ ] File paths are listed: `random-2026-09-04-1430-20x20-Easy.png`, etc.
- [ ] Files exist on disk and are valid
- [ ] Difficulty is Easy as requested

---

### TC-008-005: Image Upload via Web

**Test Level:** Integration  
**Location:** tests/test_web.py::test_web_image_generation

**Given:**
Form with:
- Source: image (file upload)
- Image file: cat.jpg
- Size: 20x30
- Difficulty: Hard

**When:**
Form is submitted with file

**Then:**
- [ ] File is uploaded and processed
- [ ] Generation completes
- [ ] Puzzle name defaults to "cat" (file stem)
- [ ] Exported files use name "cat-20x30-Hard.*"
- [ ] Difficulty is Hard as requested

---

### TC-008-006: Cross-Origin Request Rejection

**Test Level:** UI  
**Location:** tests/test_web.py::test_cors_rejection

**Given:**
POST request from malicious.com to http://localhost:5000/generate

**When:**
Request has `Origin: https://malicious.com`

**Then:**
- [ ] Request is rejected (HTTP 400 or 403)
- [ ] Error message explains: "Cross-origin requests not allowed"
- [ ] Generation does not proceed

---

### TC-008-007: Loopback-Only Binding

**Test Level:** UI  
**Location:** tests/test_web.py::test_loopback_binding

**When:**
Server is running on 127.0.0.1:5000

**Then:**
- [ ] Connecting from 127.0.0.1 succeeds
- [ ] Connecting from 192.168.x.x (local network) fails
- [ ] Connecting from external IP fails
- [ ] Server does not expose to network

---

## Critical Invariants

### INV-001: Solver Correctness

**Test Level:** Property  
**Location:** tests/property/test_solver_uniqueness.py::test_solver_never_false_positive

**Property:**
Every puzzle reported as unique actually has exactly 1 solution

**Verification:**
- [ ] Run solver on 100+ random grids
- [ ] For each, verify against independent brute-force oracle
- [ ] No mismatches between solver and oracle
- [ ] Solver reports correct count for all cases

---

### INV-002: Round-Trip Integrity

**Test Level:** Integration  
**Location:** tests/test_integrity.py::test_roundtrip_all_formats

**Property:**
Export → Parse → Re-export produces byte-identical output

**Verification:**
- [ ] Generate puzzle
- [ ] Export to JSON, CSV
- [ ] Parse exported files
- [ ] Re-export
- [ ] Compare byte-by-byte: original == re-exported

---

### INV-003: Architecture Layering

**Test Level:** Unit  
**Location:** tests/test_architecture.py::test_no_lateral_imports

**Property:**
CLI and Web never import each other; capabilities never import laterally

**Verification:**
- [ ] AST walk of src/nonogram/cli.py: no imports of web/
- [ ] AST walk of src/nonogram/web/: no imports of cli.py
- [ ] AST walk of capability modules: no lateral imports
- [ ] Orchestrator is the only point of convergence

---

### INV-004: Grid Bounds

**Test Level:** Unit  
**Location:** tests/test_bounds.py::test_grid_dimensions

**Property:**
All generated grids have width and height in [10, 30]

**Verification:**
- [ ] Generate 100 grids with random parameters
- [ ] Check: 10 ≤ width ≤ 30 and 10 ≤ height ≤ 30 for all
- [ ] No grid violates bounds

---

### INV-005: Web UI Isolation

**Test Level:** Integration  
**Location:** tests/test_security.py::test_web_isolation

**Property:**
Web server binds to loopback only and rejects cross-origin requests

**Verification:**
- [ ] Attempt connection from non-loopback IP: fails
- [ ] Attempt cross-origin request: fails
- [ ] Verify Sec-Fetch-Site header validation

---

## Test Execution Summary

```
Unit Tests:           ~80 tests
Integration Tests:    ~30 tests
Property Tests:       ~5 test suites (100+ generated cases each)
UI Tests:             ~15 tests
Critical Invariants:  ~5 tests

Total:                ~250 test cases
Expected runtime:     ~60–90 seconds on typical hardware
Coverage target:      >90% of production code
```

Each test uses a unique name format: `test_<component>_<scenario>_<variant>`  
Example: `test_cli_size_rectangular`, `test_solver_uniqueness_property`

---

## Test Data & Fixtures

- **Picture Corpus:** 25 high-contrast silhouettes in tests/fixtures/pictures/
- **Grid Corpus:** Pre-generated grids with known properties in tests/fixtures/grids/
- **Brute-Force Oracle:** Independent solver in tests/helpers/brute_force_oracle.py
- **Seeded Random:** All randomized tests use fixed seeds for reproducibility

