# CARD-209: Wide-but-short solutions pack 3 to a page, one column × three rows

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/209-solutions-one-by-three
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("### Solutions: Use fixed slots — 6 solutions 2 columns × 3 rows ↓ 4 solutions 2 columns × 2 rows ↓ 3 solutions 1 column × 3 rows"); owner decision 2026-10-13 via AskUserQuestion — **add the 1×3 tiling only, keep the shipped 2-or-4-up rule**: the 2026-10-08 decision that a with-clues tile has no clue-gutter room at six to a page stands, so no 6-up page is built.
**Idea:** —
**Wave:** —
**Depends on:** CARD-204
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_answer_key.py, tests/test_book_solved_answer_key.py, tests/test_layout_answer_tiles.py, tests/property/test_book_answer_tiles.py, tests/helpers/book_corpus.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `export.layout.SOLVED_TILE_CAPACITIES = (2, 4)` (`layout.py:2633`) and
  `_SOLVED_TILE_COLUMNS = 2` (`:2640`): a packed solved page is **always two
  columns**, one or two rows. `compute_packed_solved_layout` (`:2796`) fits the
  tile as `(usable width − gap)/2` wide by `(usable height − (rows−1)·gap)/rows`
  tall, cell capped at `SOLVED_TILE_MAX_CELL_MM = 6.0`.
- `book_answer_key.qualifies_for_packing` (`:397`) packs only answers with
  `width ≤ PACKED_MAX_WIDTH (15)` **and** `height ≤ PACKED_MAX_HEIGHT (20)`.
  `plan_small_answer_pages` (`:474`) cuts a one-level run of such answers into
  pages of 4, then 2, then a leftover 1 — never 3.
- Everything else — anything wider than 15 or taller than 20 — keeps CARD-198's
  treatment: **one full page per answer**. A 30×8 solution therefore takes a
  whole page while using about a quarter of it.

**What changes.** A third tiling joins the two: **one column × three rows**, for
answers that are too wide for a half-width tile but short enough that three of
them stack on one page.

1. **Geometry (COMP-007, `layout.py`).** Extend the packed-solved layout to a
   1-column/3-row tiling: tile width = the full usable width, tile height =
   `(usable height − 2·SOLVED_TILE_GAP_MM)/3`, cell capped at
   `SOLVED_TILE_MAX_CELL_MM` as today, each tile carrying its own band and
   clues exactly as a 2/4-up tile does. Keep the existing `(2, 4)` tilings
   byte-identical — add a capacity, do not reshape the function's existing
   answers (a second capacity tuple entry and a columns term that is 1 for it,
   2 for the others).
2. **Qualification (COMP-009, `book_answer_key.py`).** A *wide-short* answer is
   one that does **not** qualify for 2/4-up packing and whose cell at the 1×3
   tile stays at or above the floor the packed tiles already respect (do not
   invent a second floor — derive the bound from
   `compute_packed_solved_layout`'s own fit and state the resulting cell
   bounds in the card's Worktree notes, e.g. "width ≤ 30 and height ≤ N on
   Book 1's trim"). Such answers pack 3 to a page, same level only, in
   puzzle-number order; a run's leftover 1 or 2 take a 1×3 page with the
   remaining slots empty (a short page, not a reshuffle — the alternative,
   mixing a leftover into a 2/4-up page, would put two tilings on one page).
3. **Precedence.** An answer that qualifies for 2/4-up keeps CARD-202's
   treatment unchanged. The new rule only ever takes answers that print on a
   full page today, so the card is strictly page-saving.
4. **Page counts.** `plan_small_answer_pages`'s result feeds
   `interior_page_count`, the `InteriorStream` counts and
   `book_kdp.unpaired_interior_page_count` — all three must agree with what the
   walk writes (the same tripwire shape already in `interior_stream`).
5. The page's own feasibility check (`_packed_page_is_feasible` /
   `_degrade_infeasible_packed_pages`, `book_pdf_generator.py:2372`/`:2409`)
   must cover the new tiling too: an infeasible 1×3 page degrades into smaller
   pages rather than printing an illegible tile.

## Acceptance criteria

- **AC-1** (happy): *Given* three consecutive easy answers of 30×8, *when* the
  answer section is planned, *then* they share one page as a single column of
  three tiles, each with its own band and its own row/column clues. (test:
  `TestBookAnswerKey_WideShortAnswersPackThreeToAPage`)
- **AC-2** (happy, geometry): *Given* such a page, *when* its layout is
  computed, *then* each tile is the full usable width, the three tiles are
  separated by `SOLVED_TILE_GAP_MM`, and every tile's cell is equal and at or
  below `SOLVED_TILE_MAX_CELL_MM`. (test:
  `TestLayoutAnswerTiles_OneByThreeTiling`)
- **AC-3** (happy, order): *Given* any book, *when* the answer section is
  planned, *then* reading the plan's pages front to back yields the answers in
  puzzle-number order exactly once each, with no page mixing two levels or two
  tilings. (test: `PropertyTest_BookAnswerTiles_OrderAndOneTilingPerPage`)
- **AC-4** (edge, leftover): *Given* a one-level run of four wide-short
  answers, *when* it is planned, *then* the first three share a 1×3 page and
  the fourth takes a 1×3 page with two empty slots — never a 2/4-up page.
  (test: `TestBookAnswerKey_WideShortLeftoverKeepsItsTiling`)
- **AC-5** (guard, unchanged rule): *Given* answers of 15×20 or smaller, *when*
  the section is planned, *then* their pages are exactly what CARD-202 shipped
  (4, then 2, then 1), and their rendered pages are byte-identical. (test:
  `TestBookSolvedAnswerKey_PackedPagesUnchanged`)
- **AC-6** (edge, tall answers): *Given* an answer taller than the 1×3 tile can
  hold at the floor (e.g. 12×30), *when* the section is planned, *then* it
  still prints on a full page of its own. (test:
  `TestBookAnswerKey_TallAnswerStillTakesAFullPage`)
- **AC-7** (happy, counts): *Given* any book, *when* its interior is exported,
  *then* `interior_page_count`, `InteriorStream`'s counts and
  `book_kdp.unpaired_interior_page_count` all equal the number of pages the
  walk actually wrote. (test: `TestBookExport_AnswerCountsAgreeWithTheWalk`)
- **AC-8** (edge, legibility): *Given* a 1×3 page at Book 1's trim, *when* it is
  drawn, *then* every face on it holds CON-020's 10 pt floor except the clue
  digits, whose floor is the cell's. (test:
  `TestInteriorType_EveryFaceHoldsTheFloor`)

## Guardrails

- G-1: No 6-up answer page is built (owner decision 2026-10-08, reaffirmed
  2026-10-13) — `SOLVED_TILE_CAPACITIES` gains `3`, never `6`.
- G-2: The 2/4-up tilings' geometry and rendered pages are unchanged
  (test: `TestBookSolvedAnswerKey_PackedPagesUnchanged`).
- G-3: Every answer appears exactly once, in puzzle-number order, and no page
  holds two levels (INV-011's surviving half; test:
  `PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook`).
- G-4: A solved tile keeps its clues, its visible grid lines through the filled
  cells and its caption (CARD-197/198/203) — this card changes tiling only.
- G-5: Do not change puzzle-page placement or the QR slot — owned by CARD-204.
- G-6: CLI and web-UI exports stay byte-identical (CON-019).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-209 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-011 — still owed.** Its capacity clause was already stale after CARD-198/202 and this
  card amends it again; the architect-station delta those cards flagged now covers three rules.
  The 2026-10-17 delta did **not** touch INV-011 — it carried CON-018, NFR-008, FR-030, FR-031,
  FR-032, FR-043 and INV-013 only — so this is unchanged and still outstanding.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-042 (the book's answer key) — amended by CARD-198, again by
  CARD-202, and a third time here; the architect-station delta is still open.
- **ADR:** ADR-0036/R2, ADR-0037/R1.
- **CON:** CON-011 (10–30 cell sides, which bounds "wide"), CON-018, CON-019,
  CON-020.
- **Components:** COMP-007 (`export/layout.py`), COMP-009
  (`book_answer_key.py`, `book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The artifact **keeps this card** and ties it into the new solutions layout:

- *"Wide, short solutions keep the one-column, three-row page from CARD-209. They use the same
  tile header and running head, so those pages look like part of the same set."*
- So this card survives as the **single exception** to CARD-232's "every solution is a tile, four
  to a page" rule, and it must adopt **CARD-233's tile header and running head**.
- **Depends on:** CARD-232 (the tile rule it is the exception to) and CARD-233 (the header it
  adopts). Sequencing matters: implementing this card first would build furniture that CARD-233
  then replaces. Update the card's `Depends on:` field at dispatch.
- Its clues now sit in CARD-208's grey boxes like every other solution.
