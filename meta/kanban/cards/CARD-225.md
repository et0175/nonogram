# CARD-225: One cell size per grid size across the whole book, capped at 7.5 mm

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/225-one-cell-size-per-grid-size
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 4 ("Cell size jumps around. A 20x20 grid prints larger or smaller depending on its clue widths, so grids of the same size don't match across pages") and "The rules behind it": Cell size
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the usable area the sizes are fitted against changes with the margins)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_plan.py, tests/test_book_cell_size.py, tests/property/test_book_pdf_geometry.py, tests/test_book_interior_type_floor.py, tests/fixtures/book_baseline_card225.json, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_finalize.html, meta/profiling/rank_durations.py, tests/helpers/two_up_ink.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code and `export/layout.py`'s own docstrings).**

- A book cell is fitted **per puzzle, on that puzzle's real clue depth**: `cell = min(7.5,
  usable_w / (width + row-clue depth), ...)` (`export/layout.py:1966`), inside NFR-008's
  4.75..7.5 mm band. So two 20x20 puzzles print at different sizes when their clue columns
  differ in width — exactly the owner's issue 4.
- A shared (two-up) page already reduces to a shared cell (`export/layout.py:1909`), but the
  shared figure is derived from the pair, not from the book.

**What changes.**

1. **One cell size per grid size, book-wide.** All 20x20 puzzles in a book print at the same
   cell; all 25x15 at theirs. The size for a grid size is the **smallest** size that every
   puzzle of that grid size in this book can take — i.e. fitted against the deepest clue
   stack among them, so no puzzle of that size overflows.
2. The flat **7.5 mm cap stands** (NFR-008's standard cell, and the owner restates it).
3. **Two puzzles sharing a page use the smaller of their two sizes** — the owner's rule,
   which is what makes their grids line up (and what CARD-226 then aligns the slots around).
4. **The NFR-008 amendment this card flagged has LANDED** (2026-10-17, commit `91609aa`).
   NFR-008 no longer says the cell is fitted "per puzzle on its real clue depth": its condition
   now reads **per grid size per book, fitted to the deepest-clued member of that grid size** —
   this card's rule — and its band is now **4.75..7.5 mm**. **Nothing is owed at the architect
   station**; read NFR-008 as the spec, including its new AC-369, AC-370 and AC-371. This card
   still does not edit `meta/architecture/**`.
5. Record the cost honestly: a book-wide size is by construction **≤** the per-puzzle size, so
   some puzzles print smaller than they do today. Measure the corpus's distribution before and
   after and state the worst case, including whether anything lands on NFR-008's 4.75 mm floor
   (and therefore on FR-031's below-floor flag).

## Acceptance criteria

- **AC-1** (happy, one size per grid size): *Given* a book holding several 20x20 puzzles with
  different clue depths, *when* the interior is exported, *then* every one of them is drawn at
  the same cell size, measured off the ink. (test: `TestBookCellSize_SameGridSizeSameCell`)
- **AC-2** (happy, the deepest clue stack decides): *Given* that set, *then* the shared size
  equals the size the *deepest-clued* member would have taken alone — so nothing overflows
  and nothing is smaller than it needs to be. (test: `TestBookCellSize_FitsTheDeepestMember`)
- **AC-3** (happy, the cap): *Given* a book of small grids with shallow clues, *then* the cell
  is 7.5 mm and not larger. (test: `TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap`)
- **AC-4** (happy, a shared page): *Given* two puzzles of different grid sizes on one page,
  *then* both are drawn at the smaller of their two book sizes.
  (test: `TestBookCellSize_SharedPageTakesTheSmaller`)
- **AC-5** (edge, one puzzle of its size): *Given* a grid size with exactly one puzzle in the
  book, *then* the rule degenerates to today's per-puzzle fit for it.
  (test: `TestBookCellSize_SoleMemberOfItsSize`)
- **AC-6** (edge, the floor): *Given* a book whose deepest-clued 30x30 forces a cell below
  NFR-008's 4.75 mm floor, *then* the below-floor flag FR-031 already defines is raised for
  **every** puzzle of that grid size, not only the one that forced it — the flag must describe
  what is printed. (test: `TestBookCellSize_BelowFloorFlagFollowsTheSharedSize`)
- **AC-7** (guard, determinism): *Given* the same book, *when* the sizes are computed twice,
  *then* they are identical, and they do not depend on the order the puzzles were added.
  (test: `TestBookCellSize_IsOrderIndependent`)

## Guardrails

- G-1: NFR-008's 4.75..7.5 mm band is not widened — this card changes how the figure is
  *chosen*, not what is allowed (test: the existing NFR-008 tests).
- G-2: FR-031's below-floor flag and per-puzzle override keep working (test: the existing
  FR-031 tests).
- G-3: A puzzle's grid, clues, tier and strategies are never changed — ADR-0033/R1. This card
  changes a drawing size only (check: review-lens).
- G-4: Out of scope — where the grid sits (CARD-224), the slot split (CARD-226), clue boxes
  (CARD-208).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-225 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **NFR-008 — the amendment this card flagged LANDED** on 2026-10-17 (commit `91609aa`), both
  halves of it: the band is now **4.75..7.5 mm**, and the figure is chosen **per grid size per
  book, fitted to the deepest-clued member of that grid size** — this card's own rule, now the
  registry's. The hand-marking rationale for 4.8 mm was **retired, not carried** (it argues for
  4.8 and cannot justify 4.75); the recorded reason is the owner's: the CON-018 margin change
  must not make the book worse than today, and 4.75 mm restores exactly today's breach point.
  **Nothing is owed at the architect station.** Build against AC-238 (4.885 mm at depth 9),
  AC-239 (4.536 mm, below the floor), **AC-369** (two 30x30s, 5-deep and 9-deep, both print at
  4.885 mm — the cell the 9-deep member fits; this is this card's AC-2 as a registry criterion),
  **AC-370** (depth 10 → 4.762 mm, at or above the amended floor where the retired 4.8 mm floor
  would have refused it) and **AC-371** (depth 13 → 4.430 mm, admitted only by FR-031's stored
  override).
- **AC-370 owes this card a test that is named nowhere else.**
  `TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor` appears on no card; NFR-008's
  amendment note says whoever picks this card up must write it rather than assume it exists.
  AC-369's and AC-371's names are this card's own planned ones.

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

- **FR:** FR-031 (the floor flag), FR-040 (pairing — a shared page's size rule).
- **NFR:** **NFR-008 (amended 2026-10-17, commit `91609aa` — band 4.75..7.5 mm, figure chosen
  per grid size per book; nothing owed)**.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0033/R1, ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- **[Inherited obligation, measured by CARD-222's review cycle 2 — land the floor's missing
  lower pin before you change anything about cell sizing]** ⚠ `FLOOR_MM` is pinned **tightly
  above and loosely below**. Measured by mutation on the merged-candidate tree, the interval in
  which the constant can be changed with the suite still fully green is **(4.54, 4.76]**:
  * `FLOOR_MM = 4.77` → reds (`TestBookCell_TwelveDeepBandFallsBelowFloor`), so the upper side
    is a real boundary;
  * `FLOOR_MM = 4.64` → **fully green**, on the non-DB floor set *and* on `test_book_floor.py`
    run in isolation;
  * `FLOOR_MM = 4.53` → reds hard (35 failures), which bounds the slack from below.
  The only thing holding the lower side is `tests/test_book_floor.py:499`'s straddle
  `4.54 < FLOOR_MM <= 4.76` — **a 0.22 mm straddle, not a boundary.**
  **Concrete failure scenario:** `FLOOR_MM = 4.60` ships green and admits cells the owner
  explicitly rejected — NFR-008's own note records "4.6 is too small".
  **Why this is yours and why it did not gate CARD-222.** The gap is the *absence* of a test,
  not a defect CARD-222 introduced, and it is already declared: `requirements.yml` states that
  AC-370's `TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor` "is a test this amendment
  newly owes CARD-225 — it is named on no card". **AC-370 is exactly the 4.762 mm lower-side
  pin**, and it is confirmed absent from `tests/`. So it was visible and assigned rather than
  hidden — but **you are the card that moves cell sizing**, so the pin has to exist *before*
  your changes land, or your own regression surface is a 0.22 mm straddle. Write AC-370's test
  first; the measured interval above is the control you are closing.


- [Why this is P1 and architectural] It is the only card of the set that changes what the
  reader *solves* rather than where it sits: a smaller cell is a harder puzzle to mark by
  hand. NFR-008's band exists for that reason, and this card moves a figure inside it for
  every puzzle in the book at once.

## Measured at the decompose station, 2026-10-14 — the margins cost 4.9% of every cell

Run against the repo's own `_placed_cell_mm` with the shipped Book 1 spec and the artifact's
four margins, so this is a measurement and not an estimate. Usable width goes 193.68 -> 184.15 mm
(-4.9%); usable height 248.35 -> 237.19 mm. The fit is width-bound for every grid the book
admits, so **every cell that is not already at the 7.5 mm cap loses exactly 4.9%**:

| grid | clue depth | today | at the new margins |
|------|-----------|-------|--------------------|
| 15x15 | any | 7.50 (capped) | 7.50 (capped) |
| 20x20 | shallow | 7.50 (capped) | 7.50 (capped) |
| 20x20 | deep | 7.45 | 7.08 |
| 25x25 | deep | 5.87 | 5.58 |
| 30x30 | shallow | 5.53 | 5.26 |
| **30x30** | **deep** | **4.84** | **4.60 — below NFR-008's floor (4.75 mm since the 2026-10-17 amendment; 4.8 mm when this was measured — 4.60 is under both)** |
| **30x12** | **deep** | **4.84** | **4.60 — below the floor** |

Small grids are unaffected because they are already at the cap. The cost falls entirely on the
large, deeply-clued puzzles — which are the hard ones, printed for the readers most likely to
mark cells by hand. A deeply-clued 30x30 sits just above the floor today and crosses it at the
artifact's four margins, which raises FR-031's below-floor flag. (Figures as measured on
2026-10-14; the floor itself moved to 4.75 mm on 2026-10-17 — see the correction at the foot of
this card.)

**This compounds with CARD-222.** Under a book-wide size per grid size, the deepest-clued
member decides for every puzzle of that size, so one deep 30x30 drags every 30x30 in the book
to 4.60 mm and raises the flag for all of them. The two cards are individually reasonable and
jointly push a whole grid size under the floor. **Surfaced to the owner as a decision before
either card starts.**

## Owner decision 2026-10-14 — the gutter stays at 0.5 in

Presented with the measurement above, the owner chose **outer 0.5 in, top 0.55 in, bottom
0.47 in as drawn, but the gutter unchanged at KDP's required 0.5 in** rather than the
artifact's 0.75 in. Re-measured against `_placed_cell_mm` with the shipped spec:

| | usable width | deep 30x30 cell | deep 25x25 | deep 20x20 |
|---|---|---|---|---|
| today | 193.68 mm | 4.84 mm | 5.87 | 7.45 |
| **shipped by this card** | **190.50 mm** | **4.76 mm** | **5.77** | **7.33** |
| artifact as drawn (0.75 in gutter) | 184.15 mm | 4.60 mm | 5.58 | 7.08 |

The cost falls from 4.9% to **1.6%**, uniformly, on every cell not already at the 7.5 mm cap.
Usable height goes 248.35 -> 241.49 mm.

**Stated as it was presented to the owner on 2026-10-14:** a deeply-clued 30x30 or 30x12 lands
at 4.76 mm, which was then 0.04 mm under NFR-008's 4.8 mm floor, so FR-031's below-floor flag
fired for that case. The owner accepted that with the reasoning that the gutter is where the
page curves anyway, so width spent there is the least useful width on the page.

**Corrected 2026-10-17 (registry delta, commit `91609aa`) — that case is no longer under the
floor.** NFR-008's floor moved to **4.75 mm**, chosen precisely so the margin change costs no
grid a clue-depth step, and the case above re-measures to **4.7625 mm** on the amended margins
with the repo's own `_placed_cell_mm` — **0.012 mm above the floor, so the flag does not fire
for it.** The registry states exactly this as AC-370, "where the retired 4.8 mm floor would
have refused it". The residue moves one depth step deeper and is still real: on the amended
margins a 30x30 falls under 4.75 mm from **clue depth 11 (4.6463 mm)**, depth 12 gives
4.5357 mm, and random 30x30 grids at density 0.5 reach **depth 13 (4.4302 mm)** (NFR-008's own
sweep, reproduced here with `_placed_cell_mm`). So CARD-225 must still handle a grid size whose
shared size is under the floor (its AC-6) — but the example that makes it non-hypothetical is
now a depth-11-or-deeper 30x30, **not** the depth-10 case tabled above. This correction
re-measured the geometry, not the corpus: re-measure the corpus before claiming either way.

**So CON-018's gutter clause is NOT amended** — only its outer, top and bottom values. That
also keeps CON-018's own KDP reasoning intact (0.375 in up to 150 pages, 0.5 in for 151-300,
and Book 1 straddles 150), which the 0.75 in gutter would have left stranded.
