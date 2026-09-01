# CARD-025: Printed cell size becomes min(comfort cap, page fit)

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/025-print-cell-size-comfort-cap
**Worktree:** ../PythonProject4-card-025
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 16
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, tests/test_export_image.py, tests/test_export_pdf.py, tests/property/test_layout_cell_size.py
**Review score:** 8.5 (cycle 3/3)
**Started:** 2026-08-31T08:35:00Z
**Closed:** 2026-08-31T09:35:00Z
**Actual:** 0.1d
**Merge commit:** cbf5ae2
**Blocked by:** —

## What to implement

This card **fixes a defect that exists today** and does not depend on rectangular grids at
all. `src/nonogram/export/layout.py` caps every grid at a flat `MAX_CELL_MM = 6.5`, so the
measured printed cell is an identical **6.52 mm from 10x10 through 25x25** and 5.93 mm at
30x30. Only 30x30 is accidentally right: a 10x10 prints about **30% smaller** than
`docs/cell_size.md` asks for.

NFR-005 replaces the flat cap with a **declining function of the grid's larger dimension**,
applied as a ceiling:

```
cell = min(comfort_cap(max(width, height)), page_fit)
```

- `comfort_cap` is `docs/cell_size.md`'s **CHOSEN-VALUE list** — 10 -> 9.0 mm, 15 -> 8.0 mm,
  20 -> 7.5 mm, 25 -> 7.0 mm, 30 -> 6.5 mm — **linearly interpolated** between those points.
  The table in that file records the band that was *considered*; the chosen list records
  what was *decided*. Encode the five chosen points, not the table's ranges.
- `page_fit` is the existing computation: the largest cell keeping the whole drawing —
  grid **plus clue gutter plus header band** — inside the A4 printable area.
- **The cap is a CEILING, never a floor.** When the two disagree, page-fit wins. Measured
  during elicitation: the cap binds only up to about 15 cells per side; from 20 up the clue
  gutter makes page-fit the binding term every time (20x20 -> 6.89 mm, 30x30 -> 4.54 mm at
  45% density). An implementation that treats the chosen value as a target will assert
  something A4 cannot deliver.
- `MIN_CELL_MM`'s existing floor behaviour is unchanged: below it, the drawing is allowed
  to exceed A4 rather than shrink past the point where a pencil mark is meaningless.

### Where the change lands

`_fit_cell(total_columns, total_rows)` takes *totals* (grid + gutter), which is right for
page-fit and wrong for the comfort cap — the cap is a function of the **grid's** larger
dimension, not the drawing's. `compute_layout(row_clues, column_clues)` already knows the
grid: `len(column_clues)` is its width and `len(row_clues)` its height. Thread those to the
cap computation without changing `compute_layout`'s public signature (G-4).

Replace the `MAX_CELL_MM` constant's role: it is no longer the cap, it is (at most) the
value for the largest supported grid. Its `__all__` export, its docstring ("the cap is
'large enough to mark, larger is just paper'") and the module docstring's description of
the clamp all move with the behaviour.

### Why this card is independent of the rectangular-extent work

`layout.py` derives extent from the clue sets, not from a size parameter, so it is already
rectangle-tolerant structurally — verified empirically during elicitation. AC-082's 12x10
and 10x12 puzzles are therefore constructible here today, from hand-built clue sets, with
no `(width, height)` request in existence. This card can ship first or last in the
increment.

## Acceptance criteria

- **AC-080** (NFR-005)
  - given: a finalized 10x10 puzzle, small enough that the comfort cap is the binding term
  - when: it is rendered for print at 300 DPI
  - then: the cell edge measures 9.0 mm +/-0.2 mm, and the whole drawing fits inside the A4
    printable area
  - kind: boundary
  - test: `TestLayout_SmallGridTakesTheComfortCap`
- **AC-081** (NFR-005)
  - given: a finalized 30x30 puzzle, the largest supported grid, whose clue gutter makes the
    comfort cap unreachable
  - when: it is rendered for print at 300 DPI
  - then: the cell edge is strictly LESS than the 6.5 mm comfort value for 30 and the whole
    drawing still fits inside the A4 printable area — page-fit wins, and the cap is never
    treated as a floor
  - kind: boundary
  - test: `TestLayout_LargeGridIsPageFitBoundNotCapBound`
- **AC-082** (NFR-005)
  - given: two finalized puzzles with the same larger dimension but different shapes, 12x10
    and 10x12, both small enough that the comfort cap binds
  - when: each is rendered for print at 300 DPI
  - then: both take the cap implied by their larger dimension 12, not by their smaller
    dimension 10 — so both measure 8.6 mm +/-0.2 mm, and orientation alone does not change
    the cell size
  - kind: boundary
  - test: `TestLayout_CapComesFromLargerDimensionRegardlessOfOrientation`
- **AC-083** (NFR-005)
  - given: a finalized 13x11 puzzle, whose larger dimension 13 falls between the
    chosen-value points 10 (9.0 mm) and 15 (8.0 mm), and which is small enough that the cap
    binds
  - when: it is rendered for print at 300 DPI
  - then: the cell edge measures 8.4 mm +/-0.2 mm — linear interpolation,
    9.0 - (13-10)/(15-10) * (9.0-8.0)
  - kind: boundary
  - test: `TestLayout_InterpolatesBetweenChosenCellSizes`

The +/-0.2 mm tolerance is about two device pixels at 300 DPI (~0.085 mm each) — tight
enough to hold the decision, loose enough for DPI rounding. Do not widen it.

## Engineering constraints

- **EC-008** (NFR-005, verbatim from requirements.yml)
  - statement: For every supported grid, the printed cell size is less than or equal to the
    comfort cap that `docs/cell_size.md`'s chosen values assign to that grid's larger
    dimension; and that cap is itself a non-increasing function of the larger dimension
    across the whole 10..30 range. The FINAL cell size is not required to be monotone in
    the larger dimension, because page-fit depends on the clue gutter and so on the
    puzzle's clues rather than on its dimensions alone.
  - kind: consistency
  - instances: AC-080, AC-081, AC-082, AC-083
  - test: `PropertyTest_Layout_CellSizeNeverExceedsComfortCap`

  Note the two halves: the corpus must span the whole 10..30 range in **both** dimensions
  (including non-square shapes) to check the `<=` claim, and the cap function itself must
  be checked for non-increase independently of any puzzle — asserting only the first half
  would pass trivially on a cap that jumped around.

## Guardrails

- G-1: Do not edit `src/nonogram/export/__init__.py`, `src/nonogram/export/json_export.py`,
  `src/nonogram/export/csv_export.py`, `tests/test_export_json.py`,
  `tests/test_export_csv.py`, `tests/property/test_export_roundtrip.py` — owned by CARD-024
  this wave.
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/difficulty.py`,
  `src/nonogram/orchestrator.py`, `src/nonogram/cli.py`, `tests/test_timeout.py` — owned by
  CARD-023 this wave and CARD-027 later.
- G-3: The comfort cap is a CEILING, never a floor. Page-fit still wins when the two
  disagree, and `MIN_CELL_MM`'s existing behaviour is preserved unchanged — below the floor
  the drawing is allowed to exceed A4 rather than shrink past the point where a pencil mark
  is meaningless (test: TestLayout_LargeGridIsPageFitBoundNotCapBound).
- G-4: `compute_layout`'s public signature keeps taking the two clue sets and nothing else.
  Grid extent is derived from them (`len(column_clues)`, `len(row_clues)`), never passed in
  as a width/height parameter — that derivation is precisely why this card is independent
  of the rectangular-extent work, and adding the parameter would couple it (test:
  TestLayout_CapComesFromLargerDimensionRegardlessOfOrientation).
- G-5: Out of scope — the header band's geometry, the clue-gutter depth rule
  (`_gutter_depth`), the major/minor rule widths (`_rule_widths`), `DPI`, the A4 page
  constants and the page margin are all unchanged. Only the cell-size term moves.
- G-6: Do not edit `docs/cell_size.md`. It is the decided spec this card implements, not an
  artifact to adjust when a number is inconvenient; the chosen-value list is normative and
  the table above it is the range that was considered.

## System contract

- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its
  current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has
  confirmed exactly one solution (US-005, FR-011). (check:
  TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library
  mode, resample attempts for difficulty matching, or pixel-nudge attempts for image
  mode) never exceeds its configured maximum bound (NFR-002). (check:
  TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound,
  TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in
  every source mode and at every point in its regenerate/resample/nudge lifecycle
  (US-016, CON-011, FR-019). (check: TestGenerateRandom_AcceptsMaxSide30,
  TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted
  as unique must never actually have 0 or more than 1 solutions. This is the mandatory
  correctness property the whole tool depends on. (check:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback)
  only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052
  as a gate-enforced mandatory constraint — a `check:` the system contract actually
  collects — so BCON-0001's socket-reach half is discharged by more than a threshold
  visible only in requirements.yml. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as
  cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header
  naming a non-loopback host), and refuses any absolute-form request target whose
  authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced
  mandatory constraint — a `check:` the system contract actually collects — so
  BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach
  half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets
  Host from the request's target url, not from the page's origin. (check:
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE
  project-wide and applies to every source mode (random, built-in library, uploaded
  image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range
  FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019
  restates the behaviour over the narrowed range. (check:
  PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded
  source image's by more than 2x is refused with an explanatory error rather than
  converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) /
  max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule
  "never silently discard more than half the user's picture". Retaining exactly 50% (a
  ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (check:
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
  routing, form rendering, request parsing, and mapping onto
  orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py;
  it may import the orchestrator but no capability module may import it or cli.py.
  (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No
  public function signature, request field, or export field reduces a grid's extent to a
  single scalar "size", and no source mode constructs a grid from one integer. (check:
  review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height
  fields. No export format writes a scalar "size" field, and no decoder reconstructs a
  grid's dimensions from one. (check: review-lens)


## Architecture context

- **FR:** —
- **NFR:** NFR-005
- **CON:** —
- **ADR:** — (the A4 / 300 DPI print target is a layout-module decision recorded in
  `layout.py`'s own docstring and CARD-012's worktree notes, not an ADR)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

## Inherited from CARD-029 (2026-08-31)

CARD-029 sweeps up the stale 10..50 range prose CARD-023's guardrails blocked, but
deliberately excludes `src/nonogram/export/layout.py` because THIS card already owns
that file and is rewriting its cell-size rule wholesale. Fold these in here rather
than letting two cards edit one file back to back:

- `layout.py:61` — "the *floor* is the honest limit of the format. A 50x50 grid whose
  clues run to 25 numbers needs seventy-five cells across"
- `layout.py:98` — "the 50x50 page is four times the bytes"
- `layout.py:111` — `MIN_CELL_MM`'s justification, "small enough that a 50x50 still
  fits". Note this one is not merely stale: under NFR-005's `min(comfort cap, page
  fit)` the floor's whole rationale changes, so restate it rather than swapping the
  number.
- `layout.py:129` — `_CLUE_FONT_RATIO`'s "the longest possible run is 50, AC-038".
  Verified: at 30 the longest run is still TWO DIGITS, so 0.62 is unchanged — only
  the number and the superseded AC id are wrong.
- `layout.py:314` — "set a 50x50 puzzle's header in the same 2 mm type as its clues"

### Measured printed cell size, before and after

Reproducible: `random_grid.generate(n, 45, random.Random(42))` -> `compute_clues` ->
`compute_layout`, cell converted at 300 DPI. "gutter" is the row-clue gutter, so the
drawing is `n + gutter` cells across.

| grid  | gutter | across | BEFORE  | AFTER   | comfort cap | page fit | binds AFTER |
|-------|--------|--------|---------|---------|-------------|----------|-------------|
| 10x10 | 4      | 14     | 6.52 mm | 8.97 mm | 9.0 mm      | 13.21 mm | **cap**     |
| 15x15 | 6      | 21     | 6.52 mm | 7.96 mm | 8.0 mm      |  8.81 mm | **cap**     |
| 20x20 | 7      | 27     | 6.52 mm | 6.86 mm | 7.5 mm      |  6.86 mm | page fit    |
| 25x25 | 8      | 33     | 5.59 mm | 5.59 mm | 7.0 mm      |  5.59 mm | page fit    |
| 30x30 | 10     | 40     | 4.57 mm | 4.57 mm | 6.5 mm      |  4.57 mm | page fit    |

BEFORE is the flat `MAX_CELL_MM = 6.5` cap: an identical 6.52 mm at 10x10, 15x15 and
20x20 (77 px), i.e. exactly the defect the card describes — the same cell for a 10x10 and
a 20x20, and ~30% under the decided value at 10x10. The 25x25 and 30x30 rows were already
page-fit bound and are byte-identical after the change, which is the expected shape of the
fix: only the sizes where the flat cap was the binding term move.

The measured 25x25/30x30 BEFORE values are 5.59/4.57 mm rather than the card's 6.52/5.93 —
same phenomenon, a different sample. Those two rows are page-fit bound, so the number
depends on the puzzle's actual gutter rather than on its dimensions; at 30% density this
seed gives the same 5.59/4.57. Nothing in the fix depends on which sample is used.

### Where the two terms cross over

- The cap binds up to about 15 cells a side and never past 20 with a realistic gutter,
  exactly as elicited. At 20x20 the two terms are already within 0.6 mm of each other.
- At 30 a side page fit binds for **every** puzzle, not just dense ones: the shallowest
  possible gutter is 1 cell, so a 30-wide grid always draws at least 31 cells across, and
  186 mm / 31 = 6.0 mm < the 6.5 mm cap. AC-081 therefore cannot be made to fail by
  choosing a friendlier puzzle.

### How the cap was verified to be a ceiling, not a target

Four independent checks, none of which a target-shaped implementation survives:

1. `tests/property/test_layout_cell_size.py::test_no_supported_puzzle_prints_a_cell_larger_than_its_cap`
   walks all 441 supported extents (10..30 x 10..30, non-square included) with three
   puzzles each — a seeded random-density one, a checkerboard (deepest gutter the shape
   allows) and a one-filled-cell grid (shallowest) — and asserts `printed <= cap` for all
   1323. It then asserts **both** sides of the `min()` were actually observed to bind
   (674 cap-bound, 649 page-fit bound, against thresholds of 100 each): a ceiling nothing
   ever reaches, and a cap being treated as a target, each fail that pair.
2. `test_a_large_grid_is_page_fit_bound_not_cap_bound` (AC-081) asserts the 30x30 cell is
   *strictly less* than 6.5 mm and that the drawing still fits the printable area.
3. `test_the_cap_ignores_the_gutter_that_page_fit_is_made_of` pins the asymmetry directly:
   two 20x20 puzzles share a cap and do not share a printed cell.
4. The cap is converted to device pixels by **truncation**, not rounding
   (`int(mm / 25.4 * DPI)` in `_fit_cell`), so "printed <= cap" holds exactly in
   millimetres rather than to within half a pixel. Worst-case loss is under one device
   pixel (0.085 mm), well inside AC-080..083's +/-0.2 mm: the five chosen sizes land at
   8.97 / 7.96 / 7.45 / 6.94 / 6.43 mm.

`MIN_CELL_MM` is untouched and is still the one clamp allowed to beat page fit (G-3). It
is now unreachable inside CON-011's range — the worst 30x30 draws 45 cells across and
still gets ~4.06 mm; page fit has to fall below 2 mm, i.e. past ~92 cells across, before
the floor bites — so its test moved to a deliberately out-of-range drawing and its
rationale was restated rather than renumbered.

### CARD-029's inherited prose sweep (all in `layout.py`)

`layout.py:61` (floor rationale, restated not renumbered), `:98` (DPI comment),
`:111` (`MIN_CELL_MM`), `:129` (`_CLUE_FONT_RATIO` — 0.62 unchanged, the two-digit claim
now cites CON-011's 30 instead of the superseded AC-038's 50), `:314` (header type size,
now "a 30x30 puzzle's header in the same 3 mm type" — measured: a 30x30 prints a 2.8 mm
clue digit). Plus one site the inherited list did not name:

- SCOPE+ `src/nonogram/export/layout.py:43` — "counting to twelve along a **fifty**-cell
  row" in the every-5th-rule paragraph. Same stale-range class as the five listed sites,
  same file, same sweep; left behind, it would have needed a third card to touch this file.

### Deviations and judgement calls

- **`page_fit` still measures the drawing only, not the header band.** NFR-005's threshold
  text says page fit keeps "grid PLUS clue gutter PLUS header band" inside A4, but the
  existing computation the card points at (`_fit_cell`) measures grid + gutter, and G-5
  puts the header band's geometry out of scope. Folding the band in would shrink PNG and
  SVG — neither of which draws a header — for a band they never pay for today, which is
  the exact design `layout.py`'s docstring and CARD-014 record. Verified instead that the
  band still lands on A4 at both ends of the new range (new PDF test, 10x10 and 30x30).
  One adversarial 30x30 (rows alternately full and empty: row gutter 1, column gutter 15,
  45 cells down) overflows the A4 page height by 68 px (~5.8 mm) once the band is added —
  **pre-existing and unchanged by this card**: that puzzle is page-fit bound at 70 px both
  before and after, the old flat cap having been 77 px. Worth a card; not this one.
- `tests/test_export_pdf.py::test_the_written_pages_are_a4_sized_at_the_print_resolution`
  compared the `/MediaBox` as formatted text and broke on the new cell size: Pillow writes
  each coordinate in its shortest form (`220.8`), the test's `:.2f` expected `220.80`. The
  page size was correct. Fixed by comparing the box as numbers (`_page_sizes`), which is
  what the test is actually about. The file is in `Touches:`.
- `MAX_CELL_MM` kept as a name but re-derived: it is now `CELL_COMFORT_MM[-1][1]`, the
  comfort value for the largest supported grid, and is documented as no longer a clamp.
  Nothing outside `layout.py` and its tests reads it.
- No change to `_gutter_depth`, `_rule_widths`, `header_band`, `DPI`, the A4 constants or
  the page margin (G-5). `compute_layout`'s signature is unchanged; the grid's extent
  reaches the cap as `max(len(column_clues), len(row_clues))`, derived inside the function
  (G-4). Nothing under G-1's or G-2's file lists was touched, and `docs/cell_size.md` was
  not edited (G-6) — it does not exist in this worktree, so the five chosen values are
  encoded from NFR-005 in `requirements.yml` and cited as NFR-005, never as that path.

### Suite

`./.venv/bin/python -m pytest` -> **1312 passed, 1 xfailed** (baseline 1300 passed,
1 xfailed; +12 = 5 AC-080..083 items, 5 EC-008 property tests, 2 PDF page-fit params, the
renamed floor test replacing the old one one-for-one).

## Inherited from CARD-029 (2026-08-31)

CARD-029 sweeps up the stale 10..50 range prose CARD-023's guardrails blocked, but
deliberately excludes `src/nonogram/export/layout.py` because THIS card already owns
that file and is rewriting its cell-size rule wholesale. Fold these in here rather
than letting two cards edit one file back to back:

- `layout.py:61` — "the *floor* is the honest limit of the format. A 50x50 grid whose
  clues run to 25 numbers needs seventy-five cells across"
- `layout.py:98` — "the 50x50 page is four times the bytes"
- `layout.py:111` — `MIN_CELL_MM`'s justification, "small enough that a 50x50 still
  fits". Note this one is not merely stale: under NFR-005's `min(comfort cap, page
  fit)` the floor's whole rationale changes, so restate it rather than swapping the
  number.
- `layout.py:129` — `_CLUE_FONT_RATIO`'s "the longest possible run is 50, AC-038".
  Verified: at 30 the longest run is still TWO DIGITS, so 0.62 is unchanged — only
  the number and the superseded AC id are wrong.
- `layout.py:314` — "set a 50x50 puzzle's header in the same 2 mm type as its clues"

### Orchestrator notes

- **[Scope]** Independently confirmed. Diff touches exactly 4 files, all inside
  `Touches:`. G-1/G-2 forbidden files absent. G-4 verified by comparing
  `compute_layout`'s signature against main — unchanged,
  `(row_clues, column_clues) -> Layout`. G-5 verified constant by constant
  against `git show main:` — DPI, both page dimensions, margin, MIN_CELL_MM and
  HEADER_BAND_MM all byte-identical. CARD-029's inherited prose sweep is
  complete: `grep "50x50\|fifty-cell"` on layout.py returns 0.
- **[Build gate]** PASSED — full suite independently re-run in the worktree's
  own venv: **1312 passed, 1 xfailed**, exit 0 (baseline 1300/1, so +12).
- **[Ceiling verification]** The card's central risk was an implementation
  treating the chosen values as TARGETS rather than a ceiling, which would
  assert something A4 cannot deliver. Verified by exhaustive sweep rather than
  by sampling: **all 441 supported extents x 3 gutter regimes = 1323 cases,
  ZERO cap violations.** Both terms of the `min()` genuinely bind — 666
  cap-bound, 657 page-fit-bound — so it is a real two-sided minimum, not a
  ceiling nothing reaches (a cap treated as a target, and a cap nothing ever
  touches, each fail that pair). Tightest margin is **+0.0033 mm** at 10x23,
  printed just UNDER the cap, which is the truncate-to-whole-pixels choice
  working as designed.
- **[Defect fixed, measured]** At 45% density, seed 42: 10x10 goes 6.52 -> 8.97
  mm and 15x15 6.52 -> 7.96 mm (both now cap-bound); 20x20, 25x25 and 30x30 are
  page-fit bound and unchanged, which is the fix's expected shape rather than a
  gap.
- **[Card correction]** The implementer flagged that this card's own "before"
  figures for 25x25 (6.52) and 30x30 (5.93) came from a TRIVIAL-clue probe
  (a 1-cell gutter), while a real 45%-density puzzle at those sizes reads
  5.59/4.57 — page-fit bound, so the value follows the puzzle's gutter, not its
  dimensions. Both readings are correct for their inputs; the card's framing was
  misleading, and the correction is right. Recorded rather than quietly amended.

- **[Review 1/3]** Score: 6.5 — crit: **1**, imp: 1. Report:
  `meta/review/20260831T081015Z-CARD-025-cycle1.yml`. Severity gate BLOCKS.
- **[Adversarial]** F-001 CONFIRMED by the orchestrator independently, and it is
  a REGRESSION THIS CARD INTRODUCED — not the pre-existing condition the
  implementer recorded. Reproduced by loading base and head `layout.py`
  side by side: a 10x25 grid of alternating full/empty rows (uniquely solvable,
  `solution_count == 1`, so it clears the INV-002 export gate and reaches a real
  PDF) gives drawing 3210 + band 142 = 3352 <= 3508 on `5e9f2de` (**fits**) and
  3400 + 142 = 3542 > 3508 on `9553c0b` (**overflows by 34 px**).
  Swept all 441 supported extents x 2 patterns: **50 combinations overflow under
  head that did not under base, 0 go the other way, 119 overflowed in both.**
  A strict superset — so the card's "pre-existing and bit-identical" claim is
  true only of the single 30x30 example the implementer tested, and false
  generalised. The cause: `_fit_cell` measures page fit over grid + gutter only,
  which was harmless under a flat 6.5 mm cap and is not harmless under a cap
  rising to 7.0 mm at 25 cells. This contradicts NFR-005's threshold verbatim
  ("grid PLUS clue gutter PLUS header band"), the card's own "Where the change
  lands" wording, and the new `_fit_cell` docstring the diff itself added.
- **[Review sync]** 1 report(s) → meta/review/.
- **[Fix 1] declarations** — commit `40c8196`. F-001 fixed by giving `_fit_cell`
  a keyword-only `reserved_height_mm` and having `compute_layout` pass
  `HEADER_BAND_MM`, so page fit measures what NFR-005 says it measures.
  **Orchestrator re-ran the 441 x 2 sweep against base independently:
  0 new overflows, 0 remaining, and 119 PRE-EXISTING overflows fixed** — all 882
  combinations now fit A4, so the branch is strictly better than main on this
  property rather than merely neutral. (The agent reported "169 fixed" measuring
  against its own broken head; against base it is 119 pre-existing + the 50 it
  had introduced. Same end state.)
  Deviation from the reviewer's preferred fix, and it is sound: a PDF-only band
  could not be threaded, because `pdf.py`/`png.py`/`svg.py` all call
  `compute_layout` positionally and are OUTSIDE this card's `Touches:`. A shared
  reservation is NFR-005's own definition of page fit, and `_fit_cell` still
  takes it as an argument so the seam exists when those files become editable.
  Measured cost: the cell moves in 169 of 1323 cases by at most **0.25mm**, all
  of them tall drawings — far below what the original deviation feared. Every
  headline size is unchanged: 10x10 still 8.97mm, 15x15 still 7.96mm.
  F-002 fixed and **pre-verified failing on the unfixed head** before the fix
  was applied ("10x25: 3400px of drawing plus a 142px band overruns A4's
  3508px") — a test that would not have caught the regression is not a fix.
  Corpus extended to 4 patterns x 441 = 1764 cases, adding the alternating-rows
  regime, which is the only one where page fit's HEIGHT term binds.
  F-003/F-004/F-005 fixed. F-006 (NFR-005's stale monotonicity clause in
  requirements.yml) correctly reported and NOT touched — outside `Touches:`,
  needs a model correction.
- **[Record correction]** The implementer's false "pre-existing and
  bit-identical" claim was **retracted in place** in the worktree notes —
  quoted, refuted with the sweep numbers, and annotated with the method failure
  that produced it: a deviation justified from ONE sample, with the word
  "pre-existing" doing the work of a sweep that was never run. Verified present.
- **[Build gate]** PASSED — 1314 passed, 1 xfailed (baseline 1312), independently
  re-run. G-4 verified byte-identical to base by diffing the signature; scope is
  exactly the 4 `Touches:` files.

- **[Review 2/3]** Score: 8.0 — crit: 0, imp: 1. Report:
  `meta/review/20260831T083908Z-CARD-025-cycle2.yml`.
  CONFIRMATION MODE: 8 verdicts carried, 4 re-verified — the reviewer's own
  intersection check found INV-002 and ADR-0019/R1 LOOKED carriable but their
  scope does intersect the delta (the INV-002 rejection tests live in the two
  touched test files; the import guard walks `layout.py`), so both were
  re-derived rather than carried. Correct call.
  System contract: 12 checked, 3 ✓ holds, 9 ⚠ unchecked, 0 ✗ violated.
  **F-001 verified fixed beyond what was claimed**: 441 extents x 8 patterns =
  3528 cases, zero band-inclusive A4 overflows in either axis. No feedback loop
  (`header_band().height` is a module constant, independent of `Layout.cell`, so
  the reservation applies once and converges trivially). Width is safe by
  construction — `pdf._titled` grows only height. The bound is tight, not slack:
  met with equality at 10x30-class shapes.
- **[Fix 2] declarations** — commit `9aa3351`.
  F-101 fixed: `_alternating_rows`' docstring claimed it was the ONLY regime
  where page fit's height term binds. Measured false — 111 for alternating-rows
  but 58 for checkerboard and 58 for a dot lattice. **Verified independently by
  the orchestrator**: removing the reservation and asserting page fit over only
  the PRE-EXISTING patterns still yields 58 failures, first at 10x25
  checkerboard. So the fourth pattern strengthens the corpus but is not what
  made the assertion capable. Load-bearing rather than cosmetic: the false
  version invited scoping the assertion to one pattern and deleting 58 real
  witnesses, restoring the blindness that let the regression ship.
  Also corrected: `height // 2` is `ceil(height/2)`, and the 1.5x crossover was
  computed from the pre-reservation height (1.40x now).
  Dead `_page_sizes` helper removed.
- **[Finding REFUTED, not applied]** ⚠ The cycle-2 Minor claiming
  `header_band`'s "13%" was overstated and should read 4.6% is **wrong**.
  Measured directly: **169 of 1323 (12.8%)** across the corpus's three patterns
  — which is what the original sentence said. The review's 4.6%/61 matches
  neither denominator (58/882 = 6.6% over the two shallower patterns, 169/1323
  over all three). I had already made the edit before checking and reverted it.
  The docstring now names the corpus it measured and carries both figures, so
  the number is checkable rather than quoted.
  Worth recording as a pattern: this card has now produced a false claim inside
  a fix commit that retracted a false claim, and then a review of THAT carrying
  an unverified number. Measuring each claim rather than inheriting it is the
  only thing that has broken the chain.

- **[Review 3/3]** Score: 8.5 — crit: 0, imp: 0. Gate PASSES.
  Delta was documentation-only and proven inert: docstring-stripped AST
  comparison shows `layout.py` and `test_layout_cell_size.py` IDENTICAL to
  cycle 2, and `test_export_pdf.py` differing only by the removed dead helper.
  Cycle 3 also ADJUDICATED my refutation of cycle 2's "13%" finding, which I had
  asked it to: **the refutation's conclusion was right — no real finding was
  dismissed — but its stated reason was wrong.** `61/1323` DOES match a real
  corpus: the three patterns as they stood BEFORE this card added a fourth. Two
  different three-pattern subsets share the denominator 1323, so the original
  sentence was AMBIGUOUS rather than incorrect, and the right fix was always to
  name the corpus.
- **[AC/EC check]** GATE: **11 verified, 0 violated, 0 unverified**. All four ACs
  measured independently against a harness that reimplemented `comfort_cap_mm`
  from NFR-005's literals rather than reading the module. EC-008 verified
  EXHAUSTIVELY: 441 extents x 6 clue patterns = 2646 cases, 0 cap violations,
  tightest margin +0.0033mm, both sides of the `min()` binding (1259 cap-bound /
  1387 page-fit-bound). G-5 confirmed the fix only READS the band's height —
  `header_band`, `_gutter_depth` and `_rule_widths` bodies all AST-identical.
  **Regression sweep, three trees side by side: base 119 overflows, the broken
  commit 169, HEAD 0. Zero new, 119 fixed.**
- **[Fix 3] declarations** — commit `afd6063`. Both gates independently found the
  numbers I wrote in `9aa3351` were wrong, and re-measuring confirmed it:
  `header_band` called 1323 "the three patterns the module sweeps" — it sweeps
  FOUR, so the whole-corpus cost is 172/1764 (9.8%). The kill-check figure is 61
  (58 checkerboard + 3 random), not 58. The per-pattern counts conflated "the
  reservation moves the cell" (111/58/3/0) with "page fit's height term binds"
  (a larger, different quantity). The 1.40x crossover had been corrected in one
  docstring of three. All now measured directly and stated against a NAMED
  corpus with a per-pattern breakdown, so every figure is checkable.
  I also cited "a dot lattice" that exists nowhere in this repository — copied
  from a review without checking — and my own grep then missed `_random_grid`
  because its signature takes a third argument, which nearly led me to
  "correct" a right number to a wrong one.
- **[Pattern, for the record]** Cycle 3 named this precisely: "numbers stated in
  prose without the sweep that would establish them — third consecutive cycle,
  each time smaller and each time in the commit that corrects the previous one."
  I was the third generation. The only thing that broke the chain was measuring
  every figure against the tree rather than inheriting it from a review.
- **[Merge]** Merged to main as `cbf5ae2` (--no-ff). Merge gate on the MERGED
  tree: 1314 passed, 1 xfailed. 169 staged user files unstaged before the merge
  and restored after, with the four carrying a staged/worktree split verified
  byte-for-byte against pre-merge backups. The branch touched none of them
  (verified by set intersection before merging).
