# CARD-232: Solutions become fixed tiles, four to a page in a 2x2 grid, each with its clues

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/232-solution-tiles
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Solutions: fixed tiles, with clues"
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the frame), CARD-225 (the cell size rule the tiles inherit)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_solved_answer_key.py, tests/test_book_solved_page.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card232.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The owner's requirement:** *"Each solution sits in a tile of the same size, four to a page in
a 2 x 2 grid, with its clues in the same grey boxes as the puzzle pages... Within a page, every
grid is centred in its tile, so the tiles line up even when grid sizes differ."*

**Current behaviour (shipped over three cards — read them before changing anything).**
CARD-197/198 put the solved grid, its clues and a caption on the answer pages; CARD-202 packs
**small** solutions (width<=15, height<=20) 2-or-4 to a page while others take a full page;
CARD-203 moved the caption closer to the grid and right-aligned it with it; CARD-204 added
`caption_slot` after a 65-character picture name put ink 9.6 mm outside the page, then fixed a
clamped caption overprinting the folio. All of that machinery is in
`book_answer_key.py` + `book_pdf_generator.py`'s `_draw_solved_slot` / `solved_puzzle_page` /
`_packed_answer_page`.

**What changes.**

1. A solution sits in a **tile of fixed size**, four to a page in a **2x2 grid** — so tiling is
   the rule rather than a size-dependent exception. CARD-202's "small solutions pack, others
   take a page" becomes "every solution is a tile", with one exception the owner keeps
   explicitly: **wide-but-short solutions stay on CARD-209's one-column, three-row page**.
2. Each tile carries **its clues**, in the same grey boxes as the puzzle pages (CARD-208).
3. **Every grid is centred in its tile**, so the tiles line up across differing grid sizes.
4. The tile header (number, name, dots) and the page's running head are **CARD-233**.

**The trap, named.** `_draw_solved_slot`'s return value has **two** consumers,
`solved_puzzle_page` and `_packed_answer_page`, which must change together; nothing in the code
enforces it. That asymmetry produced gating defects in CARD-203 cycle 1, CARD-203 cycle 2,
CARD-204 Fix 7 and CARD-204 cycle 5 — "the same two call sites, the same asymmetry, one card
later", in the reviewer's words. It is in `backlog.md` as a standing retro item. This card
rewrites exactly that area: change both consumers in the same commit, and if the return value
can be made a value object both must take, do that and say so.

## Acceptance criteria

- **AC-1** (happy, 2x2): *Given* a book of solutions, *when* the answer pages are exported,
  *then* each full answer page holds four tiles in a 2x2 grid, all four tiles the same size.
  (test: `TestSolutionTiles_FourToAPageInTwoByTwo`)
- **AC-2** (happy, clues in every tile): *Given* each tile, *then* its clues are drawn in the
  grey boxes, on the same two sides as the puzzle pages.
  (test: `TestSolutionTiles_EveryTileCarriesItsClues`)
- **AC-3** (happy, centred in its tile): *Given* a page whose four solutions have different
  grid sizes, *then* each grid is centred in its own tile and the four tiles' boxes are
  identical. (test: `TestSolutionTiles_GridsAreCentredInIdenticalTiles`)
- **AC-4** (edge, a short last page): *Given* a solution count that is not a multiple of four,
  *then* the last page holds the remainder in the same tile positions — no resizing to fill.
  (test: `TestSolutionTiles_LastPageKeepsTheTileSize`)
- **AC-5** (guard, CARD-209's exception): *Given* wide-but-short solutions, *then* they still
  use the one-column, three-row page, with the same tile furniture.
  (test: CARD-209's own classes, re-run unchanged)
- **AC-6** (guard, the caption defect stays fixed): *Given* a 65-character picture name, *then*
  no ink leaves the usable area and nothing overprints the folio, on both the tiled page and
  CARD-209's page. (test: the existing `caption_slot` classes in `tests/test_book_solved_page.py`)
- **AC-7** (edge, the page count): *Given* the corpus, *then* the answer section's page count is
  recorded against CARD-202's packing and the change attributed, and
  `unpaired_interior_page_count` agrees with what was written.
  (test: `TestSolutionTiles_AnswerPageCountIsAttributed`)

## Guardrails

- G-1: INV-002 — a solution is only ever the stored, verified solution; nothing here recomputes
  one (check: review-lens).
- G-2: ADR-0033/R1 — book assembly never changes a puzzle's grid, clues, tier or strategies
  (check: review-lens).
- G-3: Both consumers of `_draw_solved_slot`'s return value change together (G-3 of CARD-226,
  restated because this is the card that actually rewrites them).
- G-4: Every answer page keeps its folio (test:
  `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-5: Out of scope — the tile header and running head (CARD-233), the clue boxes' own drawing
  (CARD-208).
- G-6: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-232 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-002** — its own `check:` ref is dead; logged in `backlog.md` and unaffected by the
  2026-10-17 delta, so review-lens remains the check until that is fixed.

- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membe… (check: review-lens)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-042 (the answer key), FR-033 (titles only in the answer key).
- **INV:** INV-002.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0033/R1, ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [This card replaces a rule, not a figure] CARD-202's "small solutions pack, the rest take a
  page" was itself an owner decision (2026-10-08, no six-up) and CARD-209 was cut from the same
  doc. Read both cards' notes before changing the packing predicate: the owner has already
  ruled on tiling density twice, and this card narrows those rules to "always a tile" with
  CARD-209's page as the single exception.
