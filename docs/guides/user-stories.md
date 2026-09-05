# User Stories — Nonogram Generator

## Overview

This document contains user stories organized by feature area and release (v1.0, future). Each user story describes:
- **Who**: The user persona (Puzzle Creator, Player, etc.)
- **What**: The feature or capability they want
- **Why**: The value or motivation for the feature
- **Acceptance Criteria**: Concrete conditions that define "done" for the user story
- **Related Requirements**: Links to functional (FR-xxx) and non-functional (NFR-xxx) requirements

## Relationship to Requirements and Formal Acceptance Criteria

**User Story AC vs Formal AC:** The "Acceptance Criteria" listed here in each user story are user-facing conditions that should be met. They are different from the formal **Acceptance Criteria (AC-001..AC-166)** defined in `meta/kanban/cards/CARD-*.md`, which are implementation-level test specifications tied to specific development cards. User story ACs are *what the user needs*; formal ACs in kanban cards are *how we verify it*.

**Traceability:**
- Each user story maps to one or more Functional Requirements (FR-xxx)
- Each FR maps to one or more kanban cards (CARD-xxx)
- Each kanban card lists formal Acceptance Criteria (AC-xxx)
- Each formal AC has a corresponding test case (TC-xxx)

To find formal ACs for a user story:
1. Note the FR numbers in "Related Requirements"
2. Search `meta/kanban/cards/` for cards implementing those FRs
3. Read the "Acceptance criteria" section of each card to see AC-xxx

## v1.0: Core Generation & Export

### US-001: Random Grid Generation

**As a** Puzzle Creator  
**I want to** generate a random black/white grid at a chosen size  
**So that** I have raw material for a puzzle without designing one by hand

**Acceptance Criteria:**
- [ ] User can run `nonogram generate --mode random --size 20 --density 30`
- [ ] A 20×20 grid is generated with approximately 30% filled cells
- [ ] Grid dimensions are in the valid range (10..30 per side)
- [ ] Each cell is independently randomized
- [ ] Grid can be seeded for reproducibility: `--seed 42` produces the same grid on repeated runs
- [ ] Generated grid is used as the solution source for puzzle generation
- [ ] No errors or crashes for any valid size in 10..30 range

**Related Requirements:** FR-1, FR-4, NFR-1

---

### US-002: Built-in Image Library

**As a** Puzzle Creator  
**I want to** pick a picture from a built-in image library (cat, house, heart, moon, etc.)  
**So that** I can generate a recognizable-shape puzzle without drawing one myself

**Acceptance Criteria:**
- [ ] User can run `nonogram generate --mode library --library-key cat`
- [ ] At least 4 built-in templates are available and discoverable via `nonogram --help`
- [ ] Each template is 16×16 or larger
- [ ] Template images are stored as PNG with pure black/white pixels
- [ ] Library keys map correctly to templates (e.g., "cat" → cat.png)
- [ ] User can list available templates via a help command
- [ ] Library-sourced puzzles pass the same uniqueness check as random grids
- [ ] Error message is clear if an invalid library key is specified

**Related Requirements:** FR-2, FR-8

---

### US-003: User Image Upload

**As a** Puzzle Creator  
**I want to** upload my own image and have it converted into a black/white puzzle grid  
**So that** I can turn a personal picture into a nonogram

**Acceptance Criteria:**
- [ ] User can run `nonogram generate --mode image --image-path ./cat.jpg`
- [ ] Image is loaded from disk (JPEG, PNG, and common formats supported)
- [ ] Image is automatically greyscaled
- [ ] User specifies target grid size via `--size 20x20`
- [ ] Image is resized to target dimensions
- [ ] Floyd–Steinberg dithering is applied
- [ ] Result is a pure black/white grid (no grey pixels remain)
- [ ] Web UI allows image upload via form file input
- [ ] Error message if image file does not exist or is unreadable
- [ ] Error message if image format is unsupported

**Related Requirements:** FR-3, FR-22

---

### US-004: Clue Computation

**As a** Puzzle Creator  
**I want to** have the tool compute row and column clues from any solution grid  
**So that** I get a playable puzzle definition, not just a picture

**Acceptance Criteria:**
- [ ] Given a solution grid, clues are computed automatically
- [ ] Row clues are computed for each row via run-length encoding
- [ ] Column clues are computed for each column via run-length encoding
- [ ] Clues are stored as tuples of integers (e.g., (2, 3) for runs of 2 and 3 filled cells)
- [ ] All-empty lines encode to (0,), not ()
- [ ] All-filled lines encode correctly (e.g., 20 filled cells in a 20-wide line → (20,))
- [ ] Clues work correctly for any grid size and aspect ratio (10×10, 20×30, etc.)
- [ ] Clues are round-trip accurate: grid → clues → can solve back to original grid

**Related Requirements:** FR-5

---

### US-005: Uniqueness Verification

**As a** Puzzle Creator  
**I want to** have the tool verify a puzzle has exactly one solution before handing it to me  
**So that** I never end up with an unsolvable or ambiguous puzzle

**Acceptance Criteria:**
- [ ] After clue computation, solver checks solution count
- [ ] Valid puzzles (solution count = 1) are accepted and exported
- [ ] Impossible puzzles (solution count = 0) are rejected with error message
- [ ] Ambiguous puzzles (solution count ≥ 2) are rejected early without enumerating all solutions
- [ ] Solver uses constraint-propagation + backtracking for efficiency
- [ ] Solver fails fast once a second distinct solution is found
- [ ] Solver never reports false positives across all test cases
- [ ] Verification completes in reasonable time for puzzles up to 30×30

**Related Requirements:** FR-6, NFR-3

---

### US-006: Automatic Regeneration on Failure

**As a** Puzzle Creator  
**I want to** have random/library-generated puzzles that fail the uniqueness check regenerated automatically  
**So that** I don't have to manually retry until I get a valid one

**Acceptance Criteria:**
- [ ] User runs `nonogram generate --mode random --size 20`
- [ ] If first candidate fails uniqueness check, a new one is generated
- [ ] Process repeats until a valid puzzle is found
- [ ] Maximum retry bound is enforced (20 attempts)
- [ ] User sees a progress message or completion message
- [ ] If retry bound is exceeded, error message explains why (e.g., "Could not generate a valid puzzle after 20 attempts at 50x50")
- [ ] Every exported puzzle is guaranteed to have exactly one solution
- [ ] User does not see failed candidates or partial results

**Related Requirements:** FR-7, NFR-2

---

### US-007: Image Nudging on Uniqueness Failure

**As a** Puzzle Creator  
**I want to** have automatic pixel adjustments tried when my uploaded image doesn't yield a unique solution  
**So that** minor ambiguity doesn't force me to redo the whole conversion by hand

**Acceptance Criteria:**
- [ ] User uploads an image and specifies size: `--mode image --image-path cat.jpg --size 20x20`
- [ ] If converted grid fails uniqueness check, nudging begins
- [ ] Nudging attempts to flip a small number of cells (1–3) near ambiguous regions
- [ ] Each nudge attempt is followed by a re-check of uniqueness
- [ ] Nudging is limited to ~10 attempts
- [ ] If nudging succeeds, adjusted grid is used
- [ ] If nudging fails, error message tells user to retry with a different image or size
- [ ] Original image file on disk is never modified
- [ ] User sees how many nudges were attempted

**Related Requirements:** FR-13

---

### US-008: Difficulty Level Selection

**As a** Puzzle Creator  
**I want to** choose a difficulty level (Easy/Medium/Hard)  
**So that** I get puzzles that match how much of a challenge I want

**Acceptance Criteria:**
- [ ] User can run `nonogram generate --mode random --difficulty Easy`
- [ ] Difficulty options are: Easy, Medium, Hard
- [ ] Web UI offers radio buttons or dropdown for tier selection
- [ ] Difficulty tier is stored with puzzle metadata
- [ ] Tier is displayed in exported files (JSON metadata, PDF header)
- [ ] Error message if invalid tier is specified
- [ ] CLI `--help` lists all valid difficulty tiers
- [ ] Same puzzle always scores the same tier regardless of generation attempt

**Related Requirements:** FR-8, FR-9

---

### US-009: PNG and SVG Export

**As a** Puzzle Creator  
**I want to** export a finished puzzle as PNG/SVG  
**So that** I can print it or use it as an image

**Acceptance Criteria:**
- [ ] User can run `nonogram generate ... --export-formats png,svg`
- [ ] PNG file is written to output directory
- [ ] SVG file is written to output directory
- [ ] Both formats render the blank puzzle grid with clues
- [ ] Clues are positioned on all four margins (top, bottom, left, right)
- [ ] Cell size scales inversely with grid dimension (larger cells for small grids)
- [ ] Printed puzzle cells are comfortable to mark by hand (≥6.5mm)
- [ ] Both formats are valid and openable in standard image viewers
- [ ] File naming follows convention: `<name>-<WxH>-<difficulty>.png`
- [ ] No visible artifacts or rendering errors

**Related Requirements:** FR-11, NFR-5

---

### US-010: JSON and CSV Export

**As a** Puzzle Creator  
**I want to** export the underlying grid and clues as JSON/CSV  
**So that** I can reuse the puzzle data in another tool or app later

**Acceptance Criteria:**
- [ ] User can run `nonogram generate ... --export-formats json,csv`
- [ ] JSON file contains: width, height, row clues, column clues, solution grid, name, difficulty
- [ ] CSV file is tabular with one row per clue or grid row, easily readable in spreadsheets
- [ ] Both formats capture 100% of puzzle information
- [ ] Exported data can be parsed and reimported without loss
- [ ] Round-trip test passes: export → parse → reconstruct → export again → byte-identical
- [ ] Files are valid JSON/CSV syntax (pass standard validators)
- [ ] File naming follows convention: `<name>-<WxH>-<difficulty>.json`
- [ ] Error handling for write failures

**Related Requirements:** FR-12, NFR-7

---

## v1.1: PDF Export & Naming

### US-011: Puzzle Naming

**As a** Puzzle Creator  
**I want to** have every puzzle carry a name (auto-generated by default, or one I choose)  
**So that** I can tell my puzzles apart when I have several saved

**Acceptance Criteria:**
- [ ] Auto-generated names follow patterns by source mode:
  - Library: key name (e.g., "cat")
  - Image: file stem (e.g., "eagle_silhouette" from eagle_silhouette.jpg)
  - Random: mode+timestamp (e.g., "random-2026-09-04-1430")
- [ ] User can override auto-generated name via `--name "My Custom Name"`
- [ ] Name is stored in puzzle metadata
- [ ] Name appears in PDF headers, JSON/CSV exports, and file paths
- [ ] Special characters in custom names are sanitized for file paths (Windows-safe)
- [ ] Non-ASCII names render correctly in PDFs (no tofu boxes)
- [ ] Error message if name is empty after override

**Related Requirements:** FR-15

---

### US-012: PDF Export with Answer Key

**As a** Puzzle Creator  
**I want to** export a puzzle as a single PDF containing both the blank puzzle and its answer key  
**So that** I have one printable file with everything needed to solve and check it later

**Acceptance Criteria:**
- [ ] User can run `nonogram generate ... --export-formats pdf`
- [ ] PDF file is created with exactly 2 pages
- [ ] Page 1: blank puzzle grid with clues, no solution
- [ ] Page 2: solution grid revealed (all cells marked), "Answer Key" label in header
- [ ] Both pages show puzzle name and difficulty tier in header
- [ ] Header format: "{Name} — {Difficulty}" (e.g., "cat — Hard")
- [ ] PDF is printable on standard A4/Letter paper
- [ ] Cells are sized appropriately for hand-marking (same as PNG/SVG)
- [ ] Page orientation matches grid shape (landscape for wide, portrait for tall/square)
- [ ] File naming follows convention: `<name>-<WxH>-<difficulty>.pdf`
- [ ] PDF generated using Pillow (no external dependencies)
- [ ] PDF opens in standard PDF readers

**Related Requirements:** FR-16, NFR-6

---

## v1.2: Web UI

### US-013: Web-Based Generation Form

**As a** Puzzle Creator  
**I want to** have a local web page where I can pick puzzle source, grid size, difficulty, and export formats  
**So that** I can generate a puzzle without having to remember or type CLI flags

**Acceptance Criteria:**
- [ ] Web server starts via `nonogram serve` or similar command
- [ ] Server binds to 127.0.0.1:5000 (or similar localhost port)
- [ ] Web page loads at http://localhost:5000
- [ ] Form includes fields:
  - Source selection: dropdown for library OR file upload for image
  - Grid size: text input accepting "N" or "NxM" format
  - Difficulty: radio buttons for Easy/Medium/Hard
  - Puzzle name: optional text input
  - Export formats: checkboxes for PNG, SVG, JSON, CSV, PDF
- [ ] Form validation provides clear error messages for invalid inputs
- [ ] Submit button triggers generation
- [ ] Form is responsive and works on mobile and desktop
- [ ] Page title and header clearly identify the tool

**Related Requirements:** FR-17

---

### US-014: Web UI Uses Same Pipeline as CLI

**As a** Puzzle Creator  
**I want to** have the web UI run through the exact same generation pipeline as the CLI  
**So that** I get identical guarantees no matter which interface I used

**Acceptance Criteria:**
- [ ] Web UI and CLI both call the same `orchestrator.generate()` function
- [ ] Uniqueness verification is identical on both paths
- [ ] Regenerate-on-failure loops work the same way
- [ ] Resample loops respect the same retry bounds and difficulty thresholds
- [ ] Image nudging uses the same algorithm on both paths
- [ ] File exports produce identical output on both paths
- [ ] Difficulty scoring produces identical scores on both paths
- [ ] Error handling and error messages match between UI and CLI
- [ ] Architectural tests verify no lateral imports between CLI and Web modules

**Related Requirements:** FR-17

---

### US-015: Web UI Security (Localhost-Only)

**As a** Puzzle Creator  
**I want to** have the web UI only reachable from my own machine, with no login required  
**So that** I don't accidentally expose puzzle generation to my network or need to manage credentials

**Acceptance Criteria:**
- [ ] Server binds to 127.0.0.1 (loopback) only, not 0.0.0.0 or external IPs
- [ ] Attempts to connect from other machines are refused
- [ ] Cross-site requests are rejected based on Sec-Fetch-Site header validation
- [ ] Requests with non-loopback Origin header are rejected
- [ ] No authentication/login required for local requests
- [ ] Server does not expose a public endpoint
- [ ] No session tokens or credentials stored on disk
- [ ] CORS headers prevent external sites from making requests
- [ ] Documentation notes that binding must not be changed for production use

**Related Requirements:** FR-17, NFR-4, CON-007

---

## v1.3: Rectangular Grids & Print Legibility

### US-016: Rectangular Grid Support

**As a** Puzzle Creator  
**I want to** ask for a rectangular grid (--size 30x20, not just --size 30)  
**So that** a puzzle can match the shape of the picture I have rather than forcing everything into a square

**Acceptance Criteria:**
- [ ] User can run `nonogram generate --size 30x20` for a 30-wide by 20-tall grid
- [ ] User can run `nonogram generate --size 30` which creates a 30x30 square (backward compatible)
- [ ] Both width and height are accepted in range 10..30 inclusive
- [ ] Parsing rejects malformed tokens (e.g., "30x", "x20", "30x20x10")
- [ ] Error message clearly indicates valid format when invalid token is provided
- [ ] Rectangular grids work with all source modes (random, library, image)
- [ ] All downstream components (solver, clues, exports) handle rectangles correctly
- [ ] Web form accepts both "N" and "NxM" notation in size field

**Related Requirements:** FR-18, CON-011

---

### US-017: Image Fitted to Requested Shape

**As a** Puzzle Creator  
**I want to** have my uploaded silhouette fitted to the grid shape I asked for instead of being square-cropped  
**So that** a tall picture like an eagle keeps its head and feet instead of losing them

**Acceptance Criteria:**
- [ ] User uploads a portrait image (e.g., 563×980 pixels)
- [ ] User specifies `--size 15x30` (tall grid)
- [ ] Image is cropped to a centered rectangle with the grid's aspect ratio
- [ ] Crop preserves significantly more content than a square crop (e.g., 87% vs 57%)
- [ ] Image is then resized to exactly 15×30 pixels
- [ ] No stretching is applied; only crop and resize
- [ ] Landscape and square images are also handled correctly
- [ ] Aspect ratio is computed from the trimmed (ink bounding box) source image

**Related Requirements:** FR-20

---

### US-018: Aspect Mismatch Refusal

**As a** Puzzle Creator  
**I want to** have the tool refuse and explain when my picture shape doesn't match my requested grid  
**So that** I don't get a puzzle silently made from only a third of my picture

**Acceptance Criteria:**
- [ ] User uploads a 200×1000 image (ratio 0.2) and requests `--size 15x30` (ratio 0.5)
- [ ] Request is refused because ratios differ by >2:1
- [ ] Error message explains why: "Image aspect ratio (0.2) differs from grid (0.5) by more than 2:1; crop would discard >50% of image"
- [ ] Error message suggests solution: "Try a different grid shape or crop the image yourself"
- [ ] A 15×30 grid with a 563×980 image (ratio 0.63) is accepted (retains >50%)
- [ ] Boundary case: exactly 2:1 mismatch is accepted (retains exactly 50%)
- [ ] Error message is clear and actionable, not cryptic

**Related Requirements:** FR-21, CON-012

---

### US-019: Print-Legible Cell Sizes

**As a** Puzzle Creator  
**I want to** have the printed puzzle's cells be a comfortable size to write in  
**So that** a 10×10 I print is not the same cramped size as a 30×30

**Acceptance Criteria:**
- [ ] A 10×10 puzzle prints with larger cells than a 30×30 puzzle
- [ ] Minimum cell size: ≥6.5mm (comfortable to mark by hand)
- [ ] Maximum cell size: ≥8.5mm at 10×10 (does not feel wasteful)
- [ ] Cell size is a declining function of grid dimension
- [ ] For rectangular grids, cell size is based on the grid's larger dimension
- [ ] Page orientation is chosen to maximize cell size (see US-022)
- [ ] All export formats (PNG, SVG, PDF) use the same cell sizing logic
- [ ] Cell size calculation is documented and tunable

**Related Requirements:** NFR-5

---

### US-022: Page Orientation Following Grid Shape

**As a** Puzzle Creator  
**I want to** have the printed page turn to match a wide or tall grid  
**So that** a rectangular puzzle isn't squeezed onto the wrong page axis

**Acceptance Criteria:**
- [ ] A 30×15 grid prints in landscape orientation (page is wider)
- [ ] A 15×30 grid prints in portrait orientation (page is taller)
- [ ] A 30×30 grid prints in portrait (ties resolve to portrait)
- [ ] Page orientation is determined by whichever layout produces larger cells
- [ ] PDF exports respect the orientation rule
- [ ] PNG/SVG exports are generated at dimensions matching the page orientation
- [ ] Orientation decision is made automatically; user does not need to specify it
- [ ] Clue layout adjusts to the page orientation (clues on all four margins)

**Related Requirements:** NFR-6

---

## v1.4: Image Refinements & Smart Sizing

### US-020: Image Margin Trimming

**As a** Puzzle Creator  
**I want to** have a picture's blank white margin trimmed away before fitting to the grid  
**So that** the puzzle isn't wasted on empty border cells

**Acceptance Criteria:**
- [ ] White margins (blank areas) are detected via ink bounding box
- [ ] Threshold for "ink" is mid-grey (~pixel value <128)
- [ ] Margins are removed before aspect ratio checking and resizing
- [ ] After trimming and dithering, grid carries at most 1 blank row/column at each edge
- [ ] Trimming is best-effort, not guaranteed (some blank cells may remain post-dither)
- [ ] Original image file is never modified
- [ ] Trimming works for images from all sources (user upload, library)
- [ ] User sees how much of the image was trimmed (optional feedback)

**Related Requirements:** FR-22

---

### US-021: Derived Grid Size from Picture Shape

**As a** Puzzle Creator  
**I want to** have a bare --size N derive the grid's shorter side from my picture's shape  
**So that** a landscape or portrait picture keeps far more of its content without my having to calculate NxM

**Acceptance Criteria:**
- [ ] User runs `nonogram generate --mode image --image-path landscape.jpg --size 25`
- [ ] N=25 is treated as the grid's longer side
- [ ] Shorter side is derived: `round(25 × short/long)` from the source's trimmed ratio
- [ ] Derived side is clamped to MIN_SIZE=10 at the bottom only
- [ ] Result: a 25×derived grid that follows the source's shape
- [ ] Example: a 563×980 image derives to 25×18 (retains ~99% vs 76% from square crop)
- [ ] Explicit `--size NxM` continues to fix both sides exactly and is unaffected
- [ ] Square images remain square: N×N
- [ ] Error if derived grid would discard >50% due to aspect ratio ceiling
- [ ] Error message names the smallest --size N that would work

**Related Requirements:** FR-23

---

### US-022: Page Orientation Optimization

**As a** Puzzle Creator  
**I want to** have the printed page automatically orient for maximum cell size  
**So that** my puzzles print comfortably regardless of their shape

**Acceptance Criteria:**
- [ ] Page orientation (landscape vs portrait) is chosen to maximize printed cell size
- [ ] Both layouts are computed; the one with larger cells is used
- [ ] Ties resolve to portrait
- [ ] Orientation is determined automatically without user input
- [ ] PDF exports use the chosen orientation
- [ ] Clues are laid out correctly for both orientations
- [ ] Measured across 441 grid sizes: cell size improves by average 1.2% vs fixed portrait
- [ ] Small grids (largest side ≤15) never rotate (already optimal)
- [ ] Orientation choice is logged/visible to user

**Related Requirements:** NFR-6

---

## Summary

| Wave | Stories | Focus |
|------|---------|-------|
| v1.0 | US-001–010 | Core generation, solving, exports |
| v1.1 | US-011–012 | Naming and PDF |
| v1.2 | US-013–015 | Web UI |
| v1.3 | US-016–019 | Rectangles, print legibility |
| v1.4 | US-020–022 | Image refinements, smart sizing |

**Total: 22 user stories**
