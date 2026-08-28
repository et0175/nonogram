# CARD-012: PNG and SVG export renderers

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/012-png-svg-export
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 6
**Depends on:** CARD-006, CARD-007
**Touches:** src/nonogram/export/png.py, src/nonogram/export/svg.py, src/nonogram/export/layout.py, src/nonogram/export/__init__.py, tests/test_export_image.py, tests/test_cli.py, tests/test_export_json.py
**Review score:** 9.3 (cycle 1/3)
**Started:** 2026-08-28T10:17:03Z
**Closed:** 2026-08-28T10:51:18Z
**Actual:** 0.1d
**Merge commit:** 641f04f
**Blocked by:** —

## What to implement

The print-ready half of COMP-007: a finalized puzzle rendered as the **blank** grid plus its
row and column clues — what a person prints and solves. The solution is deliberately not on
these outputs (it is the JSON/CSV export's job, and the PDF answer key's).

1. `export/layout.py` — the shared geometry: clue gutter widths derived from the longest
   row/column clue, cell size, grid lines with heavier every-5th rules. Both renderers and
   CARD-014's PDF consume this, so keep it a pure function of (grid size, clues) returning
   coordinates — no Pillow or SVG types in its signature.
2. `export/png.py` — raster via Pillow (ADR-0006), at a resolution that stays legible when
   printed at A4. **This raster path is what CARD-014's PDF reuses** (CON-006: PDF is a
   second sink on this path, not a new dependency), so expose the rendered `Image` object,
   not only the file-writing wrapper.
3. `export/svg.py` — vector output via stdlib string/XML generation; no new dependency.
4. Register both formats in `export/__init__.py`'s dispatch table. `--export`'s accepted
   values are derived from that registry (CARD-007), so this card needs **no** `cli.py` edit.
5. **AC-030 — the INV-002 export gate.** Export of an unverified puzzle is refused and
   nothing is written. The check is enforced in COMP-002 (CARD-005/007 built it); this card
   adds the test that proves the gate holds for the image formats and that no partial file
   is left on disk.

## Acceptance criteria

- **AC-028** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as PNG, then a PNG file containing the blank grid and clues is written to disk.
  *test:* `TestExport_WritesPNG`
- **AC-029** (happy) — given a finalized, uniqueness-confirmed puzzle, when it is exported
  as SVG, then an SVG file containing the blank grid and clues is written to disk.
  *test:* `TestExport_WritesSVG`
- **AC-030** (negative, INV-002) — given a puzzle that has not yet passed the uniqueness
  check, when export is requested, then export is rejected and nothing is written, because
  the puzzle is not ready.
  *test:* `TestExport_RejectsUnverifiedPuzzle`

## Guardrails

- G-1: Do not edit `src/nonogram/export/csv_export.py`, `src/nonogram/export/json_export.py`
  — owned by CARD-013 this wave. `export/__init__.py` is shared with CARD-013 (both register
  a format): keep the edit to adding rows to the dispatch table, never restructuring it
- G-2: Do not edit `src/nonogram/sourcing/**` (CARD-008), `src/nonogram/difficulty.py`
  (CARD-009), `src/nonogram/cli.py` (CARD-008 and CARD-011 own it this wave) — registering
  the formats in `export/__init__.py` is sufficient, because `--export`'s accepted values
  are derived from that registry (CARD-007)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py` — export is additive on
  top of Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: No new dependency — PNG via Pillow, SVG via stdlib string generation (ADR-0006,
  CON-006). Do not reach for `svgwrite`, `cairosvg`, `reportlab` or similar
- G-5: The INV-002 readiness gate stays in COMP-002 (ADR-0007, trace.yml FR-011 note) — do
  not duplicate the check inside the renderers
- G-6: Out of scope — no interactive or playable output; v1 ships static files only
  (CON-002). No PDF (CARD-014)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-011
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-006
- **ADR:** ADR-0006, ADR-0007, ADR-0008
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### Summary

Delivered on `card/012-png-svg-export`. Four source files, one test file:

- `src/nonogram/export/layout.py` (new) — the shared print geometry, a pure function.
- `src/nonogram/export/png.py` (new) — the Pillow raster, with the `Image` exposed (CON-006).
- `src/nonogram/export/svg.py` (new) — stdlib-generated XML, no new dependency (G-4).
- `src/nonogram/export/__init__.py` — **two rows added** to `_FORMATS`, plus the `PNG`/`SVG`
  name constants and one stale docstring sentence. Nothing restructured (G-1).
- `tests/test_export_image.py` (new) — 50 tests covering AC-028/029/030 and the geometry.

`orchestrator.py` was **not** touched. Predicted as a possible Touch; verified unnecessary —
`export_puzzle()` already dispatches through the registry and already calls
`require_ready_for_export()` before building the payload, so registering two rows is the
whole of the wiring. `cli.py` was not touched either (G-2): `--export`'s `choices` come from
`export.FORMATS`, and a test asserts both new formats parse with the adapter unedited.

Two stale assertions in pre-existing test files had to move, both about *the registry having
exactly one row* rather than about anything this card changed:

- `tests/test_export_json.py::test_the_registry_knows_the_json_format` asserted
  `FORMATS == (JSON,)`. Now asserts JSON's membership and its renderer — pinning the whole
  tuple in the JSON renderer's own file would make every later card's row look like a JSON
  regression. Its sibling `test_an_unregistered_format_is_a_wiring_bug...` used `"png"` as its
  example of an unknown format; it now uses `"pdf"` (CARD-014's, still unregistered).
- `tests/test_cli.py`'s `format-not-in-increment-1` usage-error case passed `--export png`;
  same substitution to `pdf`. `json_export.py` itself was not edited (G-1).

### Design notes

**`layout.py` — the geometry decisions.** `compute_layout(row_clues, column_clues) -> Layout`,
returning plain ints/floats/tuples: `GridLine(index, position, start, end, width, major)` and
`ClueEntry(value, line, depth, center_x, center_y)`. No Pillow type, no SVG string, no path in
the signature, which is what lets CARD-014's PDF consume it without inheriting either
renderer's library.

- *Grid size is not a parameter.* It is not separate information — `len(row_clues)` is the row
  count and `len(column_clues)` the column count, and INV-001 makes the clue sets the encoding
  of the grid, so a size argument could only ever agree with them or be a bug. Mismatched clue
  sets (rows but no columns) raise `ValueError` as a pipeline bug.
- *Gutters are derived, not fixed.* Each is as deep as the longest clue in its direction, so a
  puzzle whose rows never need more than three numbers does not carry a gutter sized for
  twenty-five. Minimum depth is 1, which the `(0,)` empty-line marker (AC-013) guarantees.
- *Clues are aligned against the grid* — rows right-aligned, columns bottom-aligned — so the
  last number of every clue abuts the edge, which is how a printed nonogram is read.
- *Grid lines span the gutters.* The line between column 4 and 5 continues up through the
  column-clue gutter; that is what makes a clue readable as belonging to its line. The corner
  block where the two gutters meet stays empty.
- *Every 5th rule.* `_is_major(index, last)` is `index % 5 == 0 or index == last`, so a 12-wide
  grid gets heavy rules at 0, 5, 10 **and** 12 — the frame closes even when the width is not a
  multiple of five. Heavy is exactly 2x thin; both renderers draw thin rules first so a heavy
  line stays visually continuous where it crosses one.
- *Integer arithmetic throughout.* Centres are `origin + index * cell + cell // 2`, not
  `round((index + 0.5) * cell)` — the rounded form drifts a pixel from the grid line at odd
  cell sizes (Python's banker's rounding on the `.5`), which showed up as clue text sitting
  off-centre in its box. Caught by the alignment tests.

**PNG resolution: 300 DPI, A4, with a clamped cell.** The card asks for "legible when printed
at A4", which is a physical statement, so the geometry is computed in millimetres and converted
once at `DPI = 300`. 300 is the print convention: at 150 a thin rule and a small clue digit both
alias, at 600 the 50x50 page is 4x the bytes for detail no home printer resolves. Page constants
are A4 portrait with a 12 mm margin.

The cell is then the largest that fits the printable area, clamped into 2.0 mm .. 6.5 mm:

| puzzle | cells across (gutter + grid) | cell | image |
|---|---|---|---|
| 10x10, short clues | 15 | 77 px (6.5 mm) | 1285 x 1285 |
| 20x20, short clues | 25-ish | 77 px (6.5 mm) | 2055 x 2055 |
| 50x50, typical clues | 63 | 41 px (3.5 mm) | 2457 x 2457 |
| 50x50, worst-case 25-number clues | 75 | 29 px (2.5 mm) | 2459 x 2459 |

The **cap** stops a 10x10 being blown up into a poster — past ~6.5 mm a cell is not easier to
mark, just more paper. The **floor** is the honest limit of the format: a maximum-size puzzle
with maximum-length clues needs 75 cells across, and rather than shrink past the point where a
pencil mark is meaningless the layout holds 2 mm cells and lets the image exceed A4 (a user
printing a 50x50 is scaling it or using A3 either way; a silently unreadable page is worse).
`write_png` stamps the DPI into the PNG's `pHYs` chunk, without which a viewer assumes 72 DPI
and prints the page at four times its intended size. The SVG carries the same information as a
physical `width`/`height` in inches over a pixel `viewBox` — a pixel `width` would be re-read at
the consumer's own 96/in and print at a third size.

**Why the `Image` object is exposed (CON-006).** `render_image(payload) -> PIL.Image` is the
real entry point; `write_png(payload, path) -> Path` is the sink that adds the DPI tag and
nothing else; `render(payload, path) -> None` is the `Renderer` the registry dispatches through.
CON-006 makes FR-016's PDF *a second sink on this same raster* (Pillow's
`save_all`/`append_images`), which is what keeps PDF one card rather than a reopened dependency
decision. A module exposing only "write a PNG here" would force CARD-014 to write a throwaway
file and read it back, or to redraw the page against a second geometry that could drift from
this one. It also makes the drawing assertable without a filesystem or a decoder — the same
benefit `json_export.document` gives the JSON shape.

**The blank grid is structural, not a rule to remember.** `compute_layout` is handed the clues
and never the grid, so no filled-cell coordinate exists downstream for either renderer to draw.
`test_the_output_does_not_depend_on_the_solution_grid` proves it the strong way: byte-identical
PNG raster and byte-identical SVG markup for a payload carrying the real solution and one
carrying `grid=[]`. The solution is not merely omitted from the page — it is never read.

**INV-002 (G-5).** No readiness check exists in any of the three new modules; a test asserts
that at source level for `png.py`, `svg.py` and `layout.py`, alongside CARD-007's package-wide
scan. AC-030 is tested per-format (PNG and SVG, `solution_count` unjudged / 0 / MANY), plus a
multi-format case proving a refused export leaves *none* of the formats behind, plus the CLI
path (exit code 5, message on stderr, empty destination).

### Test results

`./.venv/bin/python -m pytest -q`: **688 passed, 1 xfailed** in ~15s. The xfail is the
pre-existing, already-tracked AC-037 benchmark. Baseline before this card was 636 passed +
1 xfailed; the +52 is 50 new tests in `tests/test_export_image.py` and 2 parametrize expansions
in `test_export_json.py::test_every_registered_format_is_accepted_by_the_cli`, which iterates
`export.FORMATS`. No regressions.

AC coverage:
- **AC-028** `TestExport_WritesPNG` -> `test_export_writes_png` (real pipeline, pinned seed 0),
  plus `test_the_png_contains_the_clues`, `test_the_png_grid_is_blank`,
  `test_the_png_records_its_print_resolution`.
- **AC-029** `TestExport_WritesSVG` -> `test_export_writes_svg` (same pinned seed), plus
  `test_the_svg_draws_the_grid_and_the_clues`, `test_the_svg_grid_is_blank`,
  `test_the_svg_declares_a_physical_size_over_a_pixel_viewbox`.
- **AC-030** `TestExport_RejectsUnverifiedPuzzle` ->
  `test_export_rejects_an_unverified_puzzle[png|svg]`,
  `test_export_rejects_an_image_the_solver_did_not_call_unique`,
  `test_a_rejected_multi_format_export_writes_none_of_the_formats`,
  `test_a_rejected_image_export_reaches_the_user_as_exit_code_five`.

Both outputs were also verified visually: the PNG and the SVG (rendered via `qlmanage`) are the
same drawing, pixel for pixel in layout — blank grid, both gutters populated, heavy rules every
five.

### Merge note for the orchestrator

`export/__init__.py` will conflict with CARD-013, which registers `csv`. This card's edit there
is three added rows (`PNG`/`SVG` constants, two `_FORMATS` entries, two `__all__` entries) plus
one docstring sentence that no longer says "only the JSON renderer exists today". The resolution
is to keep both sides' rows.

[Scope] Predicted Touches plus tests/test_cli.py and tests/test_export_json.py (outside prediction — 2 pre-existing "registry has exactly one row" assertions updated to membership checks; no assertion's intent changed, same pattern as CARD-007's scope note). orchestrator.py NOT touched (predicted but verified unnecessary — export_puzzle() already dispatches through the registry). cli.py untouched (G-2). export/csv_export.py, json_export.py's existing content, sourcing/**, difficulty.py, solver/**, clues.py untouched (G-1/G-2/G-3 held).
[Build gate] PASSED (full, independently re-run by orchestrator: 689 collected, 688 passed, 1 xfailed, 0 failed, exit 0).
[Review 1/3] Score: 9.3 — crit: 0, imp: 0, 8 minor + 2 info. Every load-bearing claim independently verified via mutation testing (leaked-solution mutant, dropped pHYs tag mutant, px-instead-of-inches SVG mutant, broken-every-5th-rule mutant, gate-moved-after-write mutant — all caught by the named tests, not just "an exception was raised"). layout.py confirmed genuinely pure (no grid/size/Pillow/SVG types in signature). Blank-grid claim confirmed structural (byte-identical output regardless of solution). G-5 confirmed sole enforcement point via mutation. CON-006 three-layer design (render_image/write_png/render) confirmed real, with the written file proven byte-identical to the exposed raster. PNG resolution/geometry design (300 DPI, A4, physical-units-first, integer centre arithmetic avoiding banker's-rounding drift) judged sound engineering, no reconsideration needed. All 8 Minor findings non-gating (docstring overstating an unreachable 2mm clamp floor — M-1; a near-tautological test — M-2; test duplication with weaker coverage than CARD-007's package-wide scan — M-3; cosmetic assertion — M-4; SVG/PNG stroke-rendering not literally pixel-identical despite "pixel for pixel" phrasing — M-5; docstring rewrap artifact sitting in the exact hunk CARD-013 will conflict on — M-6, worth fixing before merge; line-length nits — M-7; missing 50x50 smoke test — M-8, manually verified fine by reviewer: 2459x2459px, 0.04s render). Final verdict: PASS — ready to merge.
