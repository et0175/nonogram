# CARD-208: Printed clue numbers sit in ruled boxes, like the player's clue cells

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/208-printed-clue-boxes
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (under "## Puzzle page header": "Have clue numbers in box:" followed by a sample image)
**Idea:** —
**Wave:** —
**Depends on:** CARD-204
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_layout.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Read this first — one inference the card rests on.** The doc line is
"Have clue numbers in box:" followed by an image the card drafter could not
read (Google Docs serves the doc as text; the image is not in it). The reading
taken here is the one the surrounding text supports and the one the player
already implements: **each clue number sits in its own ruled cell-sized box, so
the clue gutters read as a continuation of the grid** (`admin.css`
`.player-clue.is-col` / `.is-row` draw exactly that on screen). If the owner
meant something else by the image — a single box around the whole clue, say —
this card is re-sliced at the decompose station rather than reinterpreted in the
worktree.

**Current behaviour (verified by reading the code).**

- `export.layout.ClueEntry` (`layout.py:752`) already places one *conceptual*
  box per clue number: `value`, `line`, `depth` (0-based from the outer edge,
  right-aligned for rows / bottom-aligned for columns) and the box's centre.
- Nothing rules those boxes. `_write_clues` (`book_pdf_generator.py:1193`)
  draws the digits only; `_stroke_drawing` (`:1118`) strokes the **grid's**
  lines plus `slot.frame`, whose own added ink is "its left and top sides, the
  outer edges of the two clue gutters" — so the gutters today have an outer
  edge and an inner edge (the grid's border) and nothing between them.
- So a printed puzzle's clue numbers float in an unruled gutter, while the
  same puzzle's clues on screen sit in boxes.

**What changes.**

1. **Geometry in COMP-007** (ADR-0036/R2 — the admin panel may not place
   things): `Layout` gains the clue gutters' own ruled lines — the
   cross-gutter boundaries at every `depth` step, in both gutters, with the
   same every-5th weighting rule the grid uses where it applies (the lines
   continuing the grid's own row/column boundaries are the heavy ones that are
   already heavy on the grid, so a clue box lines up with its row/column).
   Express them in the same shape `vertical_lines`/`horizontal_lines` already
   use (`GridLine`: position + width), so the renderer consumes positions and
   derives nothing.
2. **Drawing in COMP-009**: `_stroke_drawing` strokes the new lines with the
   existing thin/heavy order (thin first, heavy last — the overlap rule its
   docstring states), pure `INK`, no new weight (ADR-0037/R2).
3. **Scope: book pages only, for now.** CON-019 makes the CLI's and web UI's
   PNG/SVG/PDF exports byte-identical regardless of book geometry, and
   `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` pins the A4 golden. The
   new lines are therefore emitted **only under a book `PageSpec`**, and the
   default spec's layout stays byte-identical. Record in the Worktree notes
   that the owner may want the single-puzzle exports to match later — that is a
   separate card with a golden refresh, not a quiet widening here.
4. Both a single puzzle page and each two-up slot get the boxes (a two-up slot
   is a puzzle page).

## Acceptance criteria

- **AC-1** (happy): *Given* a puzzle printed on a book page, *when* the page is
  drawn, *then* every clue number is enclosed by four rules — the gutter's
  outer edge or a cross-gutter rule on each side, and the grid's border or a
  cross-gutter rule on the others — forming one cell-sized box per number.
  (test: `TestBookPuzzleFrame_EveryClueNumberIsBoxed`)
- **AC-2** (happy, alignment): *Given* any book puzzle page, *when* it is
  drawn, *then* each clue box's inner boundary coincides exactly with its own
  row's or column's grid boundary — a clue box is never half a cell out of
  register with the row it belongs to. (test:
  `PropertyTest_BookLayout_ClueBoxesRegisterWithTheirLines`)
- **AC-3** (happy, weights): *Given* any book puzzle page, *when* it is drawn,
  *then* a clue-gutter rule continuing a heavy (every-5th or border) grid line
  is heavy and every other is thin, both at the PageSpec's own widths.
  (test: `TestBookPuzzleFrame_ClueRuleWeightsFollowTheGrid`)
- **AC-4** (happy, two-up): *Given* a two-up page, *when* it is drawn, *then*
  both slots carry boxed clues. (test: `TestBookPdfTwoUp_BothSlotsBoxTheirClues`)
- **AC-5** (edge, zero clue): *Given* a line whose clue is `(0,)`, *when* the
  page is drawn, *then* its single `0` is boxed like any other number.
  (test: `TestBookPuzzleFrame_ZeroClueIsBoxed`)
- **AC-6** (guard): *Given* any generation request, *when* the CLI or web UI
  writes a PNG, SVG or PDF, *then* the bytes are identical to before this card.
  (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`,
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`)
- **AC-7** (edge, digit legibility): *Given* the smallest cell a book may print
  (CON-018/INV-006's floor), *when* a page is drawn, *then* the clue digits
  still sit inside their boxes with clearance on both sides — the boxes do not
  clip the digits. (test: `TestBookInteriorTypeFloor_ClueDigitsFitTheirBoxes`)

## Guardrails

- G-1: The puzzle grid's own lines, frame and cell fitting are unchanged — this
  card adds gutter rules and nothing else (test:
  `PropertyTest_BookPdfGeometry_GridUnchangedByClueBoxes`).
- G-2: CLI and web-UI exports stay byte-identical (CON-019, ADR-0036/R1).
- G-3: No geometry computed in `book_pdf_generator.py` — every position comes
  from `export/layout.py` (ADR-0036/R2).
- G-4: Do not change puzzle-page placement or the QR slot — owned by CARD-204.
- G-5: Out of scope — the answer/solution pages' clue rendering (CARD-197's
  solved layout) is not touched by this card.

## System contract

- ADR-0036/R2 — book page geometry is computed only by COMP-007's layout
  functions; the admin panel does not fit cells or place grid lines (check:
  review-lens)
- ADR-0036/R1 — the default PageSpec's layout is byte-identical to the A4
  golden (check: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`)
- ADR-0037/R2 — thin rule ≥ 0.25 mm, heavy = 2 × thin, pure black (check:
  review-lens)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- CON-020 — clue digits are the one exemption from the 10 pt floor; their floor
  is CON-018/INV-006 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)

## Architecture context

- **FR:** FR-016 (the printable puzzle page), FR-031/NFR-008 (the book's cell
  floor, which AC-7 measures against).
- **ADR:** ADR-0036/R1, ADR-0036/R2, ADR-0037/R2.
- **CON:** CON-018, CON-019, CON-020.
- **Components:** COMP-007 (`export/layout.py` — the new line positions),
  COMP-009 (`book_pdf_generator.py` — stroking them).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—
