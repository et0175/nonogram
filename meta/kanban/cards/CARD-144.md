# CARD-144: A frame around the puzzle on book pages — the clue bands boxed, the CLI untouched

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/144-book-puzzle-frame
**Worktree:** —
**Source:** owner, 2026-09-23 ("I'd add a frame around puzzle, around the top and left sides"), shape and scope settled by AskUserQuestion the same day
**Idea:** —
**Wave:** 26
**Depends on:** CARD-141
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/export/pdf.py, tests/test_book_puzzle_frame.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

A book puzzle page draws the clue bands as bare numbers beside the grid. The owner asked for
the classic framed look: one rectangle around the whole block, with the clue bands boxed off
from the grid and an empty corner box.

    +---+-------+
    |   | 2   1 |      <- column clue band, boxed
    |   | 1   3 |
    +---+-------+
    | 1 | | | | |
    | 2 | | | | |      <- row clue band, boxed
    | 3 | | | | |
    +---+-------+

1. **Book pages only.** The owner chose this over framing standalone exports, so CON-019
   stands and the golden A4 fixtures are not touched. Carry it as a new optional `PageSpec`
   field defaulting to *off*, so `compute_layout` called without a PageSpec produces exactly
   today's A4 geometry and ink (ADR-0036/R1). The book's PageSpec turns it on; the CLI and
   web paths never do.
2. **The frame is ink, not geometry.** Draw it on the boundaries the layout already computes
   — the outer edge of the clue gutters and the grid's existing outer border, which already
   serves as the divider between band and grid. The cell size, the drawing's position and
   the gutter depths must not move by a single pixel: every measured figure stays as it is
   (4.97 mm on the 30x30 with 9-deep clues, 7.5 mm on the 15x15, the two-up 7.39 mm pair).
   If a cell figure changes, the implementation has gone wrong.
3. **Weights follow ADR-0037/R2.** The frame uses the heavy rule — the same weight as the
   grid's outer border, twice the thin rule, pure black. It must not introduce a third
   weight.
4. **Both trims.** The owner likes 6x9 and 8.5x11 alike, so the frame must sit correctly on
   any stored trim and on both page parities, and on a two-up page it frames each puzzle of
   the pair separately, not the pair as a whole.

Out of scope: framing answer-key tiles (they are a packed grid of their own and the owner
did not ask), the guide, divider or cover pages, and any change to the band that carries
"Puzzle N · Tier".

## Acceptance criteria

- New: on the book PageSpec a puzzle page carries a closed rectangle around clues and grid,
  with the clue bands boxed and the corner empty.
  test: TestPuzzleFrame_BookPageCarriesTheFrame
- New: `compute_layout` without a PageSpec, and every CLI/web export, are byte-identical to
  before this card.
  test: TestPuzzleFrame_DefaultPageSpecIsUnchanged
- New: the cell size and drawing origin on the book PageSpec are unchanged by the frame, for
  a 30x30 with 9-deep clues and a 15x15.
  test: TestPuzzleFrame_GeometryIsUnmovedByTheFrame
- New: every frame rule is the heavy weight, at least twice the thin rule, in pure black.
  test: TestPuzzleFrame_UsesTheHeavyRuleOnly
- New: on a two-up page each puzzle is framed separately.
  test: TestPuzzleFrame_PairIsFramedPerPuzzle

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical, and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited. The tripwire must not move at
  all. test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden,
  PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry
- G-2: ADR-0037/R2 — thin rules at least 0.25 mm, heavy exactly twice the thin, pure black.
  No new stroke weight.
- G-3: Geometry is unchanged. This card adds ink only; no cell fitting, gutter depth or
  origin may move. CARD-116's and CARD-118's measured figures stay green.
- G-4: Do not edit `src/nonogram/admin/**` — the panel decides no geometry (ADR-0036/R2).

## Architecture context

- **FR:** FR-041 (book page layout)
- **CON:** CON-019 (byte-identity), CON-018 (margins)
- **ADR:** ADR-0036 (PageSpec, geometry ownership), ADR-0037 (stroke weights)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, reviewing the CARD-118 proof renders on both trims. The frame
  shape was chosen from three sketches (boxed clue bands, one plain outer rectangle, or an
  open top-and-left L) and the scope from two (book pages only, or everywhere). The owner
  took the boxed clue bands, book pages only — explicitly keeping CON-019 intact rather than
  amending it and regenerating the goldens.
- [Why it waits for CARD-141] Both edit `src/nonogram/export/layout.py`.
