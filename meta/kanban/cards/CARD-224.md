# CARD-224: The grid goes back to centred, sitting at 42% of the puzzle area's spare height

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/224-grid-centred-again
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 2 ("Grids are pushed to one edge and pinned to the top. On most pages the lower third of the page is empty (pp. 28, 75, 125), so the page looks unbalanced") and "Puzzle area" + the artifact's own note on reversing CARD-204
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the area), CARD-223 (the QR must be out of the gutter strip before the strip stops existing)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card224.json, tests/helpers/two_up_ink.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Read this first: this card deliberately reverses the central decision of CARD-204, which
merged on 2026-10-14 after 12.2 days and 8 fix cycles.** The owner knows, and says so in the
artifact: *"This reverses the flush-right and flush-left placement from CARD-204 back to
centring. That alignment was what freed the gutter-side strip for the QR. Once the QR has its
own footer, centring is the calmer choice."* Treat CARD-204 as a decision the product has
outgrown, not as work to be undone carelessly: it also delivered the QR slot, the two-up
folio reserve and `export.layout.caption_slot`, **and all three of those stay**.

**Current behaviour (verified by reading the code).**

- A puzzle page's drawing sits **flush to the page's outer edge, mirrored by parity** (right
  on right-hand pages, left on left-hand ones) — CARD-204's placement, which made FR-032's own
  "centred" statement false. **The amendment logged for that in `backlog.md` was CANCELLED, not
  applied** (2026-10-17, commit `91609aa`), precisely because this card restores the centring:
  FR-032's "centred" clause stands as originally written and is correct again.
- The drawing is **pinned to the top** of its area under the band (FR-032's "fixed top edge"),
  which is what leaves the lower third of a page empty on pp. 28, 75 and 125.

**What changes.**

1. The grid is **centred horizontally** in the puzzle area again. Parity stops moving it.
2. Vertically it sits at **42% of the spare height** — the artifact's figure, with the
   artifact's reason: *"which looks centred once the header sits above it."* So 42% is an
   optical decision, not an arithmetic one. Declare it once, named, with that sentence as its
   docstring, and do not silently "improve" it to 50%.
3. The spare height is measured against CARD-222's puzzle area (header rule to footer rule),
   so the grid can never land on either rule.
4. Keep what CARD-204 built that this does not contradict: `caption_slot` (it bounded a real
   defect — a 65-character picture name putting ink 9.6 mm outside the page), the two-up folio
   reservation, and the QR (now in the footer, CARD-223).

**One trap, named because this family has already produced five regressions.** CARD-204's own
retro lesson is in `backlog.md`: `_draw_solved_slot`'s return value has **two** consumers,
`solved_puzzle_page` and `_packed_answer_page`, which must change together, and nothing in the
code enforces it. The same asymmetry produced a gating defect in CARD-203 cycle 1, CARD-203
cycle 2, CARD-204 Fix 7 and CARD-204 cycle 5. If this card changes anything a slot returns,
change both consumers in the same commit and say so.

## Acceptance criteria

- **AC-1** (happy, centred): *Given* a left-hand page and a right-hand page holding the same
  puzzle, *when* both are drawn, *then* the drawing's left and right margins within the puzzle
  area are equal to within a pixel, and the two pages place it identically — parity no longer
  moves it. (test: `TestBookPuzzleFrame_GridIsCentredOnBothParities`)
- **AC-2** (happy, the 42%): *Given* a puzzle area with spare height `s`, *when* the grid is
  placed, *then* the gap above it is `0.42 * s` and the gap below `0.58 * s`, measured off the
  drawn ink. (test: `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`)
- **AC-3** (guard, never on a rule): *Given* every grid size the book admits and every trim,
  *when* a page is drawn, *then* no grid or clue ink touches the header rule or the footer
  rule. (test: `TestBookPuzzleFrame_GridClearsBothRules`)
- **AC-4** (edge, the tallest grid): *Given* the tallest grid that fits at all, *then* the
  42% rule degrades to "as low as it fits" rather than pushing ink past the footer rule, and
  the page says which rule bound it. (test: `TestBookPuzzleFrame_TallestGridYieldsToTheFooter`)
- **AC-5** (guard, CARD-204's survivors): *Given* a 65-character picture name, *when* the
  answer page is drawn, *then* `caption_slot` still bounds it inside the usable area — the
  defect CARD-204 Fix 7 and Fix 8 closed does not come back with centring.
  (test: the existing caption-slot classes in `tests/test_book_solved_page.py`)
- **AC-6** (happy, the lower third): *Given* the corpus pages the owner named (28, 75, 125),
  *when* they are drawn, *then* the empty band below the grid is **0.58 of the puzzle area's
  spare height and the band above it 0.42** — so the spare is split in the 42/58 ratio instead
  of all of it falling below a top-pinned grid, and the band below is at most **1.4x** the band
  above. That is the measured form of "the page looks unbalanced": today the lower band is the
  *whole* spare. (test: `TestBookPuzzleFrame_NoEmptyLowerThird`)
  **Corrected 2026-10-17 (registry delta):** this criterion previously read "the empty band
  below the grid is no larger than the band above it", which **contradicts AC-2** — AC-2 puts
  0.42 of the spare above and 0.58 below, so the band below is deliberately the larger one.
  FR-032 was amended per AC-2 and the owner's artifact (AC-366/AC-367), so AC-6 was the wrong
  one and is corrected here rather than left to gate the card against a false claim.

## Guardrails

- G-1: FR-040's pairing behaviour is unchanged — this card moves a grid inside its slot, it
  does not change which puzzles share a page (test: the existing pairing tests).
- G-2: The two-up folio reservation CARD-204 added still holds: every two-up page keeps its
  folio (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-3: `caption_slot` is not removed or widened.
- G-4: Out of scope — the cell size (CARD-225), the slot split (CARD-226), the header's
  content (CARD-207).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-224 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-032 — settled on 2026-10-17 (commit `91609aa`), and not the way a mechanical pass would
  have settled it. Two clauses pull opposite ways and only one of them moved:**
  1. **CANCELLED, not applied** — the amendment CARD-204 had logged against the "horizontally
     the drawing is centred across the usable width" clause. Because this card *reverses*
     CARD-204's flush-by-parity placement, the centred clause is **correct again and stands as
     originally written**; writing CARD-204's logged amendment would have made the registry
     wrong in the opposite direction. The cancellation is recorded against the logged request
     in `meta/kanban/backlog.md`.
  2. **AMENDED** — the **fixed top edge** clause, which is what this card actually breaks. The
     drawing now **floats at 42% of the puzzle area's spare height** (gap above = 0.42 ×
     spare, gap below = 0.58 × spare), measured off the drawn ink. AC-190 is **retired** with
     its test `TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage`; **AC-366** and **AC-367**
     state the new truth, and EC-022's "one fixed offset … never varies between puzzle pages"
     is restated as the 42% ratio (instances now AC-189, AC-240, AC-366, AC-367).
  AC-366/AC-367 name this card's own planned test
  `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`, which does not exist yet.
  **Nothing is owed at the architect station** — do not re-apply CARD-204's pending amendment.
- **Mirrored margins are now a geometric no-op on Book 1** (gutter == outside == 12.700 mm,
  CON-018 as amended 2026-10-17). FR-030's AC-272 and AC-273 now hold the same span
  (12.700..203.200 mm) and FR-032's AC-274/AC-275 the same left edge (25.45 mm), so on the
  default profile **a passing parity assertion about the usable area or a margin width is an
  identity, not evidence** that mirroring works. The mirroring rule (FR-030's last sentence,
  TERM-034) and EC-032's "gutter minus outside" formula stay true with a zero difference and
  still bite on any book storing **unequal** margins — the only configuration in which
  mirroring is actually under test. Owner decision 2026-10-17: record this, do not restore the
  asymmetry by changing a margin. An assertion about *which side* something sits on (left vs
  right by parity) still has teeth; one about *how wide* the margin is does not.
  For this card that lands on **AC-1**: "parity no longer moves it" is the right claim, but on
  Book 1 the before-and-after left edges coincide anyway (25.45 mm at both parities), so AC-1
  proves the centring, not the removal of the mirroring. A book with unequal margins is what
  makes the second half of that claim observable.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-032 (both clauses above — settled 2026-10-17, commit `91609aa`: the "centred"
  clause stands and CARD-204's logged amendment is cancelled; the fixed-top-edge clause became
  the 42% float, with AC-190 retired and AC-366/AC-367 added), FR-040 (pairing, unchanged).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1.
- **Components:** COMP-009, COMP-007.
- **Trace:** not updated by this card.

## Worktree notes

- [On reversing 12 days of work] CARD-204 cost 12.2d against a 2.5d estimate and found three
  real print defects on the way (a caption 9.6 mm outside the page, a caption overprinting a
  folio, two-up pages losing their folios). Those findings are *why* this reversal is cheap:
  the tests they left behind are the ones that will catch this card if it gets the geometry
  wrong. Reverting the placement is not reverting the card.
