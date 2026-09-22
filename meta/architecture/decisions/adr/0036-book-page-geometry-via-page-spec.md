# ADR-0036: Book page geometry is a page spec passed to compute_layout

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-030 requires the book PDF to size each puzzle's cell for the book's own trim and margins. The usable area is the trim minus the outside, gutter, top and bottom margins, minus the 12 mm title band. The cell is computed from the puzzle's real clue depth, capped at the 7.5 mm standard cell, with the top edge at a fixed position and the page always portrait (FR-032, NFR-008, CON-018). FR-031 needs the same per-puzzle cell size on the selection tiles, to flag puzzles below the 4.8 mm floor.

Today COMP-007's `export/layout.py` has one entry point, `compute_layout(row_clues, column_clues)`. It hard-codes A4 with 12 mm margins, NFR-005's comfort-cap curve (9.0 → 6.5 mm) and NFR-006's rule of turning the sheet whichever way prints the larger cell. A guardrail in its docstring (G-1, from the card that built it) says "no second paper size". The admin panel (COMP-009) renders every book page through `export.pdf.render_pages`, so books print on A4 geometry inside an 8.5×11 page.

CON-019 requires the CLI and web UI PNG/SVG/PDF to stay byte-for-byte unchanged. ADR-0007's layering and the import guard in `tests/test_cli.py` allow `admin/` (a rank-0 adapter) to import `export/`, but never the reverse. ADR-0033 keeps Book assembly in CTX-001, so print vocabulary in COMP-007 crosses no context boundary.

## Decision

We will give COMP-007 a `PageSpec` value object and make it an optional parameter of `compute_layout`, whose default reproduces today's A4 behaviour exactly. `PageSpec` carries:
- the page size and the four margins;
- the reserved title band;
- the orientation policy: NFR-006's "larger cell wins", or portrait only;
- the cell-cap policy: NFR-005's comfort curve, or a flat cap.

The book builds a `PageSpec` from its stored trim and margins (CON-018): 8.5×11 in, gutter 0.5 in, outside/top/bottom 0.375 in, 12 mm band, portrait only, flat 7.5 mm cap. The book PDF and FR-031's selection tiles both call the same function with it. The CLI and web UI never pass one.

This keeps one implementation of cell fitting, clue gutters, grid-line placement and the every-5th rule, all of which are already tested. It turns CON-019 into one mechanical guarantee, pinned by a golden-byte test on the default path. The tile's cell size and the PDF's cell size cannot disagree, because they come from the same call. The G-1 guardrail is retired: COMP-007 now knows more than one sheet, but only through an explicit `PageSpec`, never by guessing.

## Alternatives considered

### Book-owned geometry in the admin panel
COMP-009 would compute the cell, gutters and placement itself and hand COMP-007 a finished layout to draw. COMP-007 would publish its drawing helpers (`_gutter_depth`, `_axis_lines`, `_rule_widths`). The A4 path would stay literally untouched. Rejected: it creates a second cell-fitting implementation that must be kept consistent through a cross-check test. It widens COMP-007's public API anyway. And it puts more logic into an adapter that ADR-0007 intends to be thin.

### A sibling entry point in export
`export/book_layout.py` with `compute_book_layout(row_clues, column_clues, page)` would share export's private helpers, leaving `compute_layout` unedited. Rejected: it retires G-1 just the same, and two entry points over one set of helpers can drift in how they place the band and gutters. One function with an explicit default is the smaller surface.

## Consequences

### Positive
- One geometry implementation for the CLI, the web UI, the book PDF and the selection tiles. A fix to cell fitting or line placement reaches all of them.
- CON-019 holds by construction and is proven by a golden-byte test: the default `PageSpec` is today's constants, and the A4 path's output is pinned.
- FR-031's floor check and the printed book use the same numbers, so a tile marked "4.9 mm" prints at 4.9 mm.

### Negative
- COMP-007's contract grows: print-production concepts (gutter margin, flat cap, portrait-only) become `PageSpec` fields, and the shared function carries branches only the book exercises.
- The layout module's docstring guardrail G-1 must be rewritten, and its extensive measurements (A4 sweeps over 441 extents) describe only the default spec. Book-spec behaviour needs its own measured tests.
- `render_pages` and the PDF sink must thread the spec through, so their signatures change too (optional, defaulted).

### Neutral
- NFR-005 and NFR-006 are unchanged for the default spec. The book spec opts out of them explicitly: flat 7.5 mm cap, portrait only. NFR-008 is the book's own range (4.8–7.5 mm).
- ADR-0007 needs no revision: admin → export is already a legal import, and nothing in export learns about the admin panel.
- DEC-039 (what the band shows and the line thresholds) builds on this spec: the title band's height is a `PageSpec` field.

## Clarifications (2026-09-22)

### Two-up pages
FR-040 lets two small puzzles share a page at one shared cell of at least 7.0 mm. COMP-007 gains a pair-aware call that takes both clue sets and the book's `PageSpec`, computes the one cell both slots use, and returns both layouts with their positions on the page. The admin panel still fits no cells itself (R2). A single puzzle keeps using `compute_layout` as above.

### Gutter margin and page count
KDP's minimum gutter grows with page count, and page count depends on the layout. To avoid a loop, the book always lays out with its stored gutter margin; for Book 1 that is 0.5 in, which KDP accepts up to 300 pages. Finalising a book refuses when the actual page count needs a larger gutter than the one stored.

### Mirrored margins
A bound book puts the gutter margin on the binding side: on the left of right-hand (odd) pages and on the right of left-hand (even) pages. The book's `PageSpec` therefore carries the page's parity, and the drawing is centred across the usable width between the two side margins. The top edge stays fixed (FR-032). The default A4 spec has no parity and is unchanged.

## References

- DEC-035 (resolved by this ADR)
- CTX-001; COMP-007 (Export Renderers), COMP-009 (admin panel); CAP-005, CAP-006
- FR-030, FR-031, FR-032, NFR-005, NFR-006, NFR-008, CON-018, CON-019, CON-006
- ADR-0007 (layering, unchanged), ADR-0033 (Book in CTX-001)
- src/nonogram/export/layout.py (`compute_layout`, `_fit_cell`, `_orientation_for`), src/nonogram/export/pdf.py, src/nonogram/admin/book_pdf_generator.py

## History

- 2026-09-22: Created — book geometry is an optional `PageSpec` on `compute_layout`, defaulting to today's A4; layout.py's "no second paper size" guardrail (G-1) retired.
- 2026-09-22: Clarified (owner, same session; FR-040) — two-up pages come from a pair-aware COMP-007 call with one shared cell; the book lays out with its stored gutter margin and finalise checks it against KDP's page-count minimum. Decision unchanged.
- 2026-09-22: Clarified (owner) — margins are mirrored by page parity and the drawing is centred across the usable width. Decision unchanged.

## Rules

```yaml
- id: ADR-0036/R1
  statement: >-
    compute_layout called without a PageSpec produces exactly today's A4
    geometry; CLI and web output are byte-for-byte unchanged by any
    book-only PageSpec field.
  scope: {contexts: [CTX-001], code: ["src/nonogram/export/**"]}
  check: {kind: test, ref: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden}
  severity: mandatory
- id: ADR-0036/R2
  statement: >-
    Book page geometry is computed only by COMP-007's layout functions
    (compute_layout, and the pair-aware call for two-up pages) with the
    book's PageSpec; the admin panel does not fit cells or place grid lines
    itself.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/**"]}
  check: {kind: review-lens}
  severity: mandatory
```
