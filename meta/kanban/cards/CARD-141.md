# CARD-141: Answer-page rows take the height they need, so the spare white falls at the page foot

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/141-answer-page-row-heights
**Worktree:** —
**Source:** owner, 2026-09-23 ("I'd rather have this white band on the bottom"), ruling on CARD-133's open question
**Idea:** —
**Wave:** 26
**Depends on:** CARD-134
**Touches:** src/nonogram/export/layout.py, tests/test_answer_page_layout.py, tests/property/test_answer_page_layout.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-24T17:24:11Z
**Closed:** 2026-09-24T18:08:26Z
**Actual:** —
**Merge commit:** a83cc54
**Blocked by:** —

## What to implement

`compute_answer_page_layout` divides the usable area into `capacity` equal tiles and draws
each answer at the top of its own tile, hanging from its caption. Every answer on a page
shares one cell size, so a 10x10 grid is physically shorter than a 20x20 at the same cell —
and a row of small answers leaves slack under it. On a mixed 4-up page that slack is a deep
white band across the middle of the page, and the page reads as two unrelated rows instead
of one block (`~/Documents/nonogram-reviews/CARD-134/03-mixed-1.png`).

The owner ruled on 2026-09-23: **the spare white belongs at the foot of the page**, not
between the rows. Vertical centring inside each tile was the alternative and was rejected —
it spreads the slack around every grid rather than gathering it.

1. **Each row takes the height its content needs**: the caption band plus the tallest grid
   in that row at the page's cell size, plus `ANSWER_TILE_GAP_MM` between rows. Rows are
   laid from the top of the usable area (under the heading, where there is one) and the
   leftover height accumulates at the bottom of the page.
2. **The cell size does not change.** Compute it exactly as today, from the equal-tile
   worst case, and only then lay the rows out at their content height. This is what keeps
   the computation non-circular and every pinned figure intact: 3.97 mm for a 20x20 six-up,
   3.87 mm under a heading, 3.19 mm for a 30x30 four-up, the 5.0 mm cap and the 10x10 at
   5.0 mm (AC-262, AC-265, AC-294, AC-295) all still hold. If any of those numbers moves,
   the implementation has gone wrong.
3. **Horizontal geometry is untouched.** Two columns, the same column width and gap, each
   answer still centred horizontally in its column as it is today.
4. **The page still reads as a regular grid.** One cell size for every answer on the page
   stays the rule (the docstring's "a 10x10 next to a 20x20 does not pull the page out of
   true"); what changes is only where a row's unused height goes. Update that docstring so
   it describes the vertical rule it now implements.

Out of scope: the caption's own position within a row, the heading, the packing walk that
decides which answers land on which page (CARD-134's, and unchanged by this), and any
change to `capacity` or the 6-up/4-up rule.

## Acceptance criteria

- New: on a mixed page whose top row is short, the gap between the two rows is
  `ANSWER_TILE_GAP_MM` and the remaining height is below the bottom row.
  test: TestAnswerLayout_SpareHeightFallsAtThePageFoot
- New: the cell size for every pinned case is unchanged from before this card.
  test: TestAnswerLayout_CellSizesAreUnchangedByRowPacking
- New: a page whose answers are all the same size looks exactly as it does today, apart
  from the foot.
  test: TestAnswerLayout_UniformPageIsUnchangedAboveTheFoot
- New: no row ever overlaps the next, and no answer leaves the usable area, for any mix.
  test: PropertyTest_AnswerLayout_RowsNeverOverlapNorOverflow

## Guardrails

- G-1: One cell size per page (ADR-0036/R2). This card changes vertical placement only —
  it must not make a grid's cell depend on its own extent.
- G-2: The pinned millimetre figures (AC-262, AC-265, AC-294, AC-295) are unchanged. Their
  tests stay green and are not edited to accommodate this card.
- G-3: CLI and web A4 output stay byte-identical (CON-019). `compute_answer_page_layout`
  has no CLI or web caller, so the golden tripwire must not move at all.
- G-4: Do not edit `src/nonogram/admin/**` — the panel decides no geometry.

## Architecture context

- **FR:** FR-042 (the answer key)
- **ADR:** ADR-0036/R2 (geometry lives in COMP-007)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner ruling, 2026-09-23, closing CARD-133's open question with the CARD-134
  renders as evidence. Note this is the OPPOSITE of the two-up ruling the same day, and
  deliberately so: on a two-up puzzle page the slack stays BETWEEN the two puzzles (the
  upper slot's top edge must align with a facing single page), while on an answer page the
  slack goes to the FOOT. The two pages are read differently — a puzzle page is worked one
  puzzle at a time, an answer page is scanned as a block.
- [Depends on CARD-134] Waits for it because CARD-134 is the card that renders and captions
  these pages; starting both against the same geometry would collide.

### Implementation, 2026-09-24 (branch `card/141-answer-page-row-heights`)

- **What changed.** `compute_answer_page_layout` still measures the page as `capacity`
  equal tiles and still fits every cell against that measured tile (new helper
  `_answer_cell_mm`, lifted out of `_answer_tile` unchanged). What is new is that the cell
  is then used to lay the rows out: `_answer_row_heights_mm` gives each row
  `ANSWER_CAPTION_MM + max(rows x cell)` over the answers in it, and the rows are stacked
  from the first row's top with `ANSWER_TILE_GAP_MM` between them. A row is never taller
  than the measured tile (the cell is at most that tile's own height fit), so the unused
  height accumulates at the page foot by construction. `_answer_tile` now takes the cell
  and its row's height instead of the equal tile's; both tiles of a row share the row's
  height, so a page still reads as rows. Horizontal geometry, the caption band, the
  heading line, `capacity` and the packing walk are untouched.
- **G-1 held.** The cell is computed from the capacity's equal tile only — a grid's cell
  still cannot depend on its own row's extent, which is what keeps the computation
  non-circular. `TestAnswerLayout_CellSizesAreUnchangedByRowPacking` asserts the negative
  directly: the same answer prints at the same cell whoever shares its row and whichever
  slot it lands in.
- **G-2 held.** AC-262/265/294/295's tests were not touched and are green: 3.9725 mm,
  3.1946 mm, 5.0 mm and the headed 3.839 mm are all unchanged.
- **G-3 held.** No CLI or web caller exists; `tests/property/test_cli_exports_byte_identity.py`
  and `tests/test_export_a4_golden.py` are green and unmoved.
- **Page count unchanged.** `admin/book_answer_key.py`'s walk closes a page on INV-011's
  longest-side rule and the answer count alone — it never consults a layout height — so the
  default plan's 31-answer-page budget (CARD-129's input) cannot move on this card.
- `SCOPE+ tests/test_layout_answer_tiles.py` and `SCOPE+ tests/property/test_book_answer_tiles.py`
  — one assertion each encoded the *old* vertical rule ("the tile is the equal tile's
  height"). Both were retargeted to the new rule (a row is its caption plus its tallest
  grid, and never more than the measured tile), re-derived independently from the Book 1
  literals as those files do. Nothing else in either file changed, and no pinned-figure
  test was edited.
- **Renders** (owner eyeball, per the standing note): `~/Documents/nonogram-reviews/CARD-141/`
  — `01-mixed-six-up.png` is the CARD-134 mixed page that prompted the ruling, now one
  block with a ~29 mm white band at the foot; `02-mixed-four-up.png`, `03-uniform-six-up.png`.
- **Tests.** New `tests/test_answer_page_layout.py` (the three AC classes) and
  `tests/property/test_answer_page_layout.py` (the seeded 3000-page corpus plus an
  exhaustive 1764-page sweep of every square pair that can share a row, over the whole
  supported 10..30 range at both capacities — deliberately wider than INV-011, since
  no-overlap/no-overflow is geometry and must hold on any mix).

[Scope] src/nonogram/export/layout.py, tests/test_answer_page_layout.py, tests/property/test_answer_page_layout.py, tests/test_layout_answer_tiles.py, tests/property/test_book_answer_tiles.py
[Touches drift] tests/test_layout_answer_tiles.py, tests/property/test_book_answer_tiles.py — declared SCOPE+ by the agent; each held one assertion encoding the old vertical rule this card changes
[Scope gate] grown (2 files beyond Touches, 23 lines, both declared) — not runaway: no sibling poaching, CARD-144's layout.py overlap is the already-serialized conflict edge
[Review 1/3] score 9.0 — 0 critical, 0 important, 3 minor. Risk LOW.
[Review sync] 1 report -> meta/review/
[Mutation] 8/8 killed, incl. M5 (revert to the pre-card equal-tile height) killed by the two RETARGETED test files alone — the retargeted assertions actively forbid the old behaviour rather than merely tolerating the new one.
[Scope gate] grown, accepted — reviewer's independent verdict agrees the two SCOPE+ test edits are net-tightening (one assertion out, two/three in; a new upper bound and a strict-inequality witness added).
[Guard] G-1..G-4 all hold. G-2 nuance recorded: the edited file IS the pinned-figure file (AC-262/265/294/295 live at lines 114/147/169/195), but the single edited hunk at 311-323 sits in a class that never asserted a millimetre figure. Read the note as "no pinned-figure TEST edited", not "no pinned-figure file touched".
[Cross-card] Answer page count structurally cannot move: book_answer_key.py imports only dataclasses, typing and nonogram.difficulty.Tier — no layout import exists, so the packing walk cannot read a height. CARD-129's 31-answer-page budget is safe, confirmed empirically too.
[Follow-up] F-001 (minor): requirements.yml:3295 still defines FR-042's tile height as the equal division. Outside this card's Touches; the raw-requirements delta already holds the owner's ruling. Route: architect pipeline, before CARD-144/CARD-129 size anything against the FR's formula.
