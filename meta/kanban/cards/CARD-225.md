# CARD-225: One cell size per grid size across the whole book, capped at 7.5 mm

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/225-one-cell-size-per-grid-size
**Worktree:** ../PythonProject4-card-225
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 4 ("Cell size jumps around. A 20x20 grid prints larger or smaller depending on its clue widths, so grids of the same size don't match across pages") and "The rules behind it": Cell size
**Idea:** —
**Wave:** 48
**Depends on:** CARD-222 (the usable area the sizes are fitted against changes with the margins)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_plan.py, tests/test_book_cell_size.py, tests/property/test_book_pdf_geometry.py, tests/test_book_interior_type_floor.py, tests/fixtures/book_baseline_card225.json, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/book_finalize.html, meta/profiling/rank_durations.py, tests/helpers/two_up_ink.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** 7.5 (cycle 1/3 — four Important; does not pass)
**Started:** 2026-10-19T15:41:00Z
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

_Assembled 2026-10-19 by `system_rules.py --card CARD-225 --root meta/architecture` (46 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 14 by rule; 32 dropped.** Curated under [`meta/kanban/curation.md`](../curation.md): keep every in-scope rule whose enforcement does not reach this card's new code, drop the rest. The kept ones are the rules **nothing executes**, plus `ADR-0039`, whose checks are tests but which declares they do not reach code written later.

⚑ **Tightened mid-flight, 2026-10-19: this contract was 17 rules an hour ago.** The model's `contexts: [CTX-001]` key was matching every card before any `code:` glob was consulted, so precisely-scoped rules behaved as package-wide. It was removed from 31 rule scopes and the authored globs became load-bearing. Only rules that do not apply to this card's files were removed — nothing that was relevant to work already done has gone.

- **ADR-0022/R1** — _nothing executes this_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar \"size\", and no
  source mode constructs a grid from one integer.
- **ADR-0023/R1** — _nothing executes this_
  Export metadata records a grid's extent as separate width and height fields. No export format
  writes a scalar \"size\" field, and no decoder reconstructs a grid's dimensions from one.
- **ADR-0033/R1** — _nothing executes this_
  Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty
  tier or strategies; the only puzzle field it may write is the book-membership mirror
  (puzzles.book_id).
- **ADR-0036/R2** — _nothing executes this_
  Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the
  pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells
  or place grid lines itself.
- **ADR-0037/R1** — _nothing executes this_
  A book puzzle page never prints the picture's title; its band shows the puzzle number and the
  solver's tier only.
- **ADR-0037/R2** — _nothing executes this_
  Under the book PageSpec the puzzle grid has exactly three rule weights -- 0.48 pt ordinary
  cell lines in grey, 1.28 pt every fifth line on both axes, 2.08 pt outer border -- each of
  them at least 2 device pixels at the render resolution, with the cell lines lighter in ink
  than the fifth lines and the border; the default PageSpec's strokes are unchanged.
- **ADR-0038/R1** — _nothing executes this_
  The puzzle player's client is hand-written JavaScript and CSS served as static files by the
  admin panel. There is no front-end framework, no build step, no npm toolchain and no vendored
  third-party JavaScript library. Adding any of these reopens this ADR (and ADR-0006/R1 for
  vendored code).
- **ADR-0038/R6** — _nothing executes this_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _nothing executes this_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _nothing executes this_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
- **ADR-0039/R1** — _declares its checks do not reach new code_
  A set a guard consults needs a completeness test written before the set, and any claim the
  guard makes about what it catches needs a control that can fail: caught WITH the set member
  present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and
  must be narrowed to what is measured or deleted.
- **ADR-0039/R2** — _declares its checks do not reach new code_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where
  no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE,
  never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _declares its checks do not reach new code_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured
  bound with its own failing control.
- **CON-021** — _nothing executes this_
  Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served
  behind the door that guards every other admin page (CON-015, CON-016). No other surface — the
  CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never persisted on the server: no progress, marks, error count, score or solve time
  is written to a database, file or server, no network request is made per mark, and no user
  account exists for playing (CON-017). The one place play state may be kept is the browser's
  own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was;
  it never leaves that browser. The admin player ships the puzzle's solution grid to the browser
  to compute the error count and the solved state; this is permitted for the admin panel only,
  and a public or reader-facing player must not send a puzzle's solution to the browser before
  the puzzle is solved.

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

## Failure matrix

Declared **before** any code was written (architectural-complexity obligation). One row
per boundary x failure mode, with the behaviour this card ships and a numeric bound where
one exists. "Grid size" is the pair `(columns, rows)` read off a puzzle's own clue sets.

| # | Boundary | Failure mode | Declared behaviour | Numeric bound |
|---|----------|--------------|--------------------|---------------|
| F-1 | `book_cell_sizes(spec, members)` | the book holds **no** member of some grid size | that grid size has no entry; a caller asking for one gets today's per-puzzle fit (`book_cell_mm`) | — |
| F-2 | `book_cell_sizes` | exactly **one** member of a grid size | the min over a singleton is that member's own fit — AC-5 degenerates by construction, not by a branch | — |
| F-3 | `book_cell_sizes` | one member's clue sets are unreadable / disagree about the grid | `ValueError` propagates from `book_cell_mm`; **no** grid size gets a size, so nothing is printed on a guessed cell. **Amended during implementation:** the bare propagation broke the standing contract that *every* abort of `interior` names a puzzle, so `section_plan` catches it and raises `RuntimeError("puzzle <id> could not be laid out: ...")` with the `ValueError` as its `__cause__` — `_unmeasurable_members` finds the culprit on the failure path only. **Amended again, review cycle 1 F-002:** the amendment had been applied to `section_plan` only, so the editor's `puzzle_page_plan` — which settles the same map two lines away — let that `ValueError` out bare (no id, no position, no `__cause__`) for *every* neighbour shape, including the member with **no** same-tier neighbour, which reached neither stage before this card and so aborted that entry nowhere. Both entries now route through `_unmeasurable_members`, so a member's failure is a named `RuntimeError` from either. Pinned by the four original cases of `TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle` plus its three `test_the_editors_page_count_names_the_member_whatever_neighbour_it_has` cases | — |
| F-3b | `cell_sizes` / `section_plan` / `puzzle_page_plan` | the **book's** stored print specification cannot be laid out (a non-numeric trim, a margin outside KDP's bounds) | a bare `ValueError` naming the column, **not** a per-puzzle `RuntimeError`: the failure is the book's and belongs to no member, so naming all 120 of them for it would be a per-puzzle message for a book-level fault. Both entries read the sheet once, before the cell map's handler, so the distinction `_unmeasurable_members` already drew is kept by the callers too (review cycle 1, F-006). Pinned by `test_an_unreadable_print_specification_is_the_books_own_failure` | — |
| F-4 | `book_cell_sizes` | members handed in a different order, or the same member twice | the result is byte-identical: `min` over a set-valued grouping (AC-7) | — |
| F-5 | `book_cell_spec(spec, cell_mm)` | `cell_mm` **above** the spec's own flat cap | the cap wins: `min(spec.cell_cap, cell_mm)`. NFR-008's 7.5 mm can never be widened by this card (G-1) | cap <= 7.5 mm on every book profile |
| F-6 | `book_cell_spec` | `cell_mm <= 0`, NaN, or `spec.cell_cap is COMFORT_CURVE` | `ValueError`, naming the argument. A book sheet always carries a flat cap; a CLI/A4 spec has no book cell and is refused rather than silently given one (ADR-0036/R1) | — |
| F-7 | exactness of the shared cell | the cap is a `float` while the fit is an exact `Fraction`, so `min(cap, fit)` for the **deepest** member may differ from the cap by one float ulp | `Layout.page.cell_mm` is **exactly equal** for every member of a grid size (`float(Fraction(repr(x))) == x` round-trips). The exact `pitch` fed to `_round_px` may differ by <= 1 ulp for the deepest member only | <= 2^-52 * 7.5 mm ~ 1.7e-15 mm, i.e. <= 2e-14 device px at 300 DPI. A boundary pixel could in principle round the other way only within that distance of a half-pixel tie; no case in this card's measured corpus does |
| F-8 | two-up page (FR-040) | the smaller of the two grid sizes' book cells is **below** `TWO_UP_MIN_CELL_MM` (7.0 mm) | the pair is **refused** and the two puzzles print on separate pages. This is a behaviour change: today the pair is fitted from the pair alone and could clear 7.0 mm. **EC-027's property can see it since review cycle 1 (F-003)**: `tests/property/test_book_pairing.py` now drives `puzzle_pages` through the whole-book map, its oracle caps every offer at the two grid sizes' book cells, its rendered corpus no longer drops books holding two members of one grid size, and two hand-built books put F-8 and F-9 in the corpus with counters asserting each — measured, both halves fail when `_pair_cell_mm` is made to return `None` | book cell < 7.0 mm => no two-up page for that pair |
| F-9 | two-up page | the pair's own two-up fit is **smaller** than the smaller book cell | the pair fit wins — it is a physical constraint of putting two drawings on one sheet. AC-4's "the smaller of their two sizes" is a **cap**, not a floor | drawn cell = min(book cell A, book cell B, pair fit) |
| F-10 | the floor (FR-031) at the add gate | a submitted puzzle clears the floor alone but its grid size's **shared** cell does not | refused without a stored override, with the shared figure named. The gate measures the **prospective membership**: the book's current members **union** the whole submission, because that is what will be printed if the add succeeds | — |
| F-11 | the add gate | a below-floor sibling in the same submission is itself refused, so it never joins | the refusal of the *other* members of its grid size was nevertheless measured with it in the set — one pass, no fixpoint. **Declared residue:** such a member can be refused for a sibling that did not join; the owner's remedy is to resubmit without it. Chosen over a fixpoint loop deliberately | one measurement pass per add |
| F-12 | the finalise count (AC-187/AC-188) | the book holds a deep member of a grid size admitted by a stored override | **every** member of that grid size is listed below the floor, each with the shared cell as its `cell_mm` — AC-6 | — |
| F-13 | the selection tile (CARD-123) | the candidate is not a member, so it has no shared cell | the tile keeps showing the candidate's **own** fit on this book's sheet — a ceiling, not a promise. **Declared divergence from EC-021's "three readings, one number"**: the tile can read above the gate's figure once the book holds a deeper member of the same grid size. The gate's refusal names the figure it enforced, so the owner is told the real number at the one moment it binds. **The loop and its bound are pinned since review cycle 1 (F-004)** by `tests/test_book_select_floor_tiles.py`'s `TestBookSelect_ATileClearsTheFloorAndTheAddStillRefusesIt` — an unflagged 6.15 mm tile for a 30x30 candidate, the refusal naming 4.54 mm, and `tile > gate` on that book | tile figure >= gate figure, always |
| F-14 | `puzzle_pages` / `puzzle_section` | called without a `cell_sizes` map (a direct caller, a test) | falls back to today's per-puzzle fit. Both production entries (`section_plan`, `puzzle_page_plan`) compute and pass the map over the **whole** book, never over one level's slice. The fallback is still a declared contract but is no longer what EC-027's property exercises (review cycle 1, F-003) | — |
| F-15 | the answer key (FR-042) | an answer tile's cell is fitted by `plan_small_answer_pages` / `solved_puzzle_page` | **unchanged.** FR-042 has its own band ([3.19, 5.0] mm) and its own cap; this card changes the puzzle pages' cell only (G-4) | — |
| F-16 | the guide page, dividers, TOC | their probe layouts read `self.page_spec(n)` | **unchanged** — they are handed the book's uncapped sheet, so no book-wide puzzle cell can move a rule, a face or a page count on them (ADR-0036/R1) | — |
| F-17 | a book with one grid size whose shared cell is at the 7.5 mm cap | nothing to lower | the cap stands; the cell is 7.5 mm and not larger (AC-3, G-1) | == 7.5 mm |

## Measured cost, 2026-10-19 — what a book-wide cell takes away

A book-wide size is by construction **<=** the per-puzzle size, so this is a cost and not a
trade. Measured, not estimated: `tests/test_book_cell_size.py`'s
`TestBookCellSize_TheCostOfABookWideCell` builds **60 books** of **8..40** puzzles each from a
seeded `random.Random(225)` over the twelve grid sizes a book admits, at **density 0.5** — the
population NFR-008's own amendment note sweeps ("random 30x30 grids at density 0.5 reach depth
13") — and reads each puzzle's cell twice: `book_cell_mm` (before) and that grid size's
`book_cell_sizes` entry (after). **1388 puzzles.** The figures below are asserted by that test,
so the distribution cannot drift silently; a different seed moves them, which is why the seed is
fixed and stated.

| | before | after |
|---|---|---|
| cell, min / median / max (mm) | 4.4302 / 5.7727 / 7.5000 | 4.4302 / 5.7727 / 7.5000 |
| puzzles at the 7.5 mm cap | 332 | 332 |
| puzzles below the 4.75 mm floor | **186** | **325** |

| loss | |
|---|---|
| puzzles unchanged | 992 / 1388 (**71.5%**) |
| relative loss, mean / median / p90 / p99 / **max** | 1.02% / 0.00% / 3.57% / 6.98% / **9.30%** |
| worst absolute loss | **0.5234 mm** |

**Read it as follows.**

- **The worst case is one puzzle losing 9.3% of its cell (0.52 mm)** — a shallow-clued member of
  a grid size whose deepest member is far deeper. Nearly three quarters of the corpus is
  untouched, because at density 0.5 most members of one grid size already have nearly the same
  clue depth.
- **Nothing ever prints larger**, and the two ends of NFR-008's band do not move: the smallest
  cell in a book is still the deepest-clued member's own figure (it is what everything else is
  fitted *to*), and a grid size already at the cap stays at the cap — 332 puzzles before and
  332 after.
- **The real cost is FR-031's flag: 186 -> 325 puzzles below the floor, +75%.** That is the
  honest headline. It is not a new breach of NFR-008's band — it is the band describing what is
  printed instead of what each puzzle could have had to itself — but it is 139 more puzzles that
  need a stored per-puzzle override before they can join a book, and the owner feels that at the
  selection step.
- **Where the owner's own books sit inside this.** The card's decompose-station table (2026-10-14)
  measured the margin cost per *grid size and clue depth*; this measures the per-*book* cost on
  top of it, and the two compose: a deeply-clued 30x30 still prints 4.7625 mm at depth 10 and
  4.4302 mm at depth 13, and now every other 30x30 in the same book prints there too.

**Two further corpora, measured the same way and recorded here rather than asserted** (the suite
pins the density-0.5 one; these are the bracket around it, from
`scratchpad/cost.py`, seeds 1225 and 2225, 60 books each):

| corpus | puzzles | unchanged | loss mean / max | worst absolute | below floor before -> after |
|---|---|---|---|---|---|
| clue depths uniform over the admissible range (**the worst case this rule has**) | 1317 | 58.7% | **5.38% / 31.58%** | **2.3138 mm** | 138 -> 283 |
| random grids at density 0.25 (picture-like, sparser) | 1449 | 68.6% | 1.25% / 12.20% | 0.7580 mm | 7 -> 23 |

The uniform-depth corpus is the bound, not a prediction: it draws a clue depth uniformly from
`1..ceil(width/2)`, which puts a 1-deep and a 15-deep 30x30 in the same book routinely. Real
pictures do not. It is recorded because it is what the rule costs **at worst**, and because
111 of its puzzles drop off the 7.5 mm cap, which the density-0.5 corpus does not show at all.

## Worktree notes (CARD-225 implementation, 2026-10-19)

### STRUCTURE decisions

- **STRUCTURE: the per-grid-size cell is a *selection* over `compute_layout`'s own answers, not a
  second fit** — `book_page_spec.book_cell_sizes(spec, members)` groups members by
  `(columns, rows)` and takes the **minimum** of `book_cell_mm` within each group. Nothing in it
  measures a sheet, a margin or a gutter, so ADR-0036/R2 ("the admin panel fits no cell") holds
  verbatim and EC-021's "one computation" still has one implementation.
- **STRUCTURE: the minimum, not "the deepest-clued member's fit"** — they are the same number
  whenever one member is deepest on both axes, which is the case NFR-008's AC-369 and this card's
  AC-2 state. They differ when one member has the deeper **row** clues (the width term) and
  another the deeper **column** clues (the height term): the minimum is then the only figure at
  which neither overflows, and "the deepest-clued member" has no single referent. The minimum
  also makes non-overflow an identity — `result <= book_cell_mm(spec, *m)` for every member *m* —
  rather than a case analysis.
- **STRUCTURE: the figure reaches the page as a lowered `PageSpec.cell_cap`**
  (`book_page_spec.book_cell_spec`), never as a new placement. A placed page's cell is
  `min(cap, page fit)`, and the shared figure is at or below every member's own fit by
  construction, so the cap is what binds for every member of the grid size and `compute_layout`
  still does all the measuring. This is the precedent `compute_pair_layout`'s own `fit_spec`
  already set. It is also why `src/nonogram/export/layout.py` needed **no edit at all** on this
  card, although the card's `Touches` admits it.
- **STRUCTURE: the cap is lowered, never raised** — `min(spec.cell_cap, cell_mm)`. G-1 (NFR-008's
  band is not widened) is therefore structural rather than tested-for: there is no code path by
  which this card can produce a cell above 7.5 mm.
- **STRUCTURE: the map is settled once, in `section_plan`, over the whole book, and carried on
  `SectionPlan.cell_sizes`.** `section_plan` is the one seam through which a book's pages are
  decided (CARD-140), and it is the only place that holds every printable member at once. A map
  built in `puzzle_pages` would be one **level's** slice (FR-041 cuts the pairing walk level by
  level), which would print a grid size at two cells in one book. Both production entries pass
  it: `section_plan` -> `puzzle_section` -> `puzzle_pages` for pairing, and `interior_stream` ->
  `_blank_page` for single pages. `puzzle_page_plan` (CARD-251's editor) computes it the same way,
  so the editor's page-break answer is still asked of the pages the book really prints.
  *A per-level mutant survived two rounds of tests before this claim was pinned — see M6 below.*
- **STRUCTURE: `cell_sizes=None` means today's per-puzzle fit** (F-14). An optional parameter
  rather than a required one, because `puzzle_pages`/`puzzle_section` are public and called
  directly by tests; the two production callers always pass it. The alternative — defaulting to a
  map built from whatever slice the method was handed — would have been a silently *wrong*
  default rather than a visibly absent one.
- **STRUCTURE: the add gate measures the *prospective* membership** — `book.puzzle_ids` plus the
  whole submission (`BookManager._below_floor_for` / `_member_clue_sets`, one bulk `get_puzzles`).
  That is what will be printed if the add succeeds, so the floor judges the cell the page will
  really carry, and it makes "the finalise count equals the gate's verdict on the same members"
  an identity rather than a coincidence. Refusal stays **per puzzle** (FR-031's own posture); the
  one-pass residue is declared as F-11.
- **STRUCTURE: the selection tile keeps the candidate's *own* fit, and that is a declared
  divergence from EC-021** (F-13). The printed cell is a property of a *membership*; a candidate
  on the selection tab is not a member and has no grid size's shared cell. So `app.py`'s
  `_book_cells` now has two readings, chosen by whether the caller names a membership: the
  finalise screen passes `members=puzzles_in_book` and gets the printed figure (AC-6), the
  selection tab passes none and gets the candidate's ceiling. **EC-021's "three readings, one
  number" cannot survive NFR-008 as amended** — see the finding below.
- **STRUCTURE: the answer key is untouched** (F-15). FR-042 fits an answer tile in its own band
  ([3.19, 5.0] mm) with its own cap; this card changes puzzle pages only (G-4). Likewise the
  guide page, the TOC and the dividers are drawn on the **uncapped** sheet (F-16), so no
  book-wide puzzle cell can move a rule, a face or a page count on them.

### Mutants run (every one restored from a byte-identical backup and `diff`-confirmed)

Backups in `scratchpad/card225-pristine/`; after every mutant the file was copied back and
`diff -q` reported identical. The tree is unmutated.

| # | mutant | result |
|---|---|---|
| M1 | `book_cell_sizes`: `min(current, cell_mm)` -> `max` (the shared figure becomes the *shallowest* member's) | **13 failed** / 27 passed |
| M2 | `book_cell_sizes`: the grid-size key drops the rows, `(columns, 0)` (every grid of one width shares a cell) | **19 failed** / 21 passed |
| M3 | `book_cell_spec`: `min(cap, cell_mm)` -> `max` (the cap never binds, so the book-wide figure never reaches the page) | **7 failed** / 33 passed |
| M4 | `_pair_cell_mm`: `min(known)` -> `max` (a shared page takes the *larger* of the two book cells) | **1 failed** / 39 passed |
| M5 | `_blank_page` ignores the map (`_puzzle_page_spec(page, None)`) | **6 failed** / 34 passed |
| M6 | `puzzle_section` sizes **each level's slice** on its own instead of passing the book's map | **survived twice, then killed** — see below |
| M7 | `_below_floor_for` drops `_member_clue_sets` (the gate ignores the book's current members) | **1 failed** / 41 passed |
| M8 | the finalise route drops `members=` (the count falls back to the per-puzzle fit) | **1 failed** / 41 passed |
| M9 | `FLOOR_MM = 4.64` — **the lower side of CARD-222's 0.22 mm straddle** | **4 failed** / 38 passed |
| M10 | `FLOOR_MM = 4.60` — the concrete scenario CARD-222's review named ("4.6 is too small") | **4 failed** / 38 passed |
| M11 | `FLOOR_MM = 4.77` — the upper side CARD-222 had already bounded | **4 failed** / 38 passed |
| M12 | `FLOOR_MM = 4.70` | **green — and declared so** (see AC-370 below) |

**M6 is the finding of this card's own mutation pass, and it took two rounds.** The claim
"the map is the book's, never a level's slice" was written into `cell_sizes`' and
`puzzle_section`'s docstrings before anything tested it, and the mutant survived the whole
first test file. The first widening (a 20x20 grid size split across the Easy and Hard levels,
measured off the ink) **also** failed to kill it: single pages are drawn from
`SectionPlan.cell_sizes` in `interior_stream` and never see the slice at all, so the only place
the mutant is observable is the **pairing** path. The second widening —
`test_the_pair_is_capped_by_a_member_in_another_level`, a pair in the Easy level whose grid
size's deep member is graded Hard — kills it. Both tests are kept: the first pins the claim's
substance, the second is the one that can see the mutant.

**M12 is a declared residue, not an oversight.** `FLOOR_MM = 4.70` ships green because no
behaviour of this system distinguishes it from 4.75: NFR-008's justification determines only
that the floor must **admit** a depth-10 30x30 (4.7625 mm) and **refuse** a depth-11 one
(4.6463 mm). AC-370's test closes `FLOOR_MM` to exactly that bracket — **(4.6463, 4.7625]**,
0.116 mm, down from CARD-222's measured (4.54, 4.76] — and
`TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor`'s docstring says in so many words that
it is not closed further and why. Narrowing the claim rather than widening the test: a test that
reported a tighter pin would be asserting something the requirement does not say.

### AC -> test mapping

| AC | test |
|---|---|
| AC-1 | `TestBookCellSize_SameGridSizeSameCell` (4 cases + the cross-level one) |
| AC-2 (= NFR-008 **AC-369**) | `TestBookCellSize_FitsTheDeepestMember` |
| AC-3 | `TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap` |
| AC-4 | `TestBookCellSize_SharedPageTakesTheSmaller` (incl. F-8's refusal boundary and the cross-level pair) |
| AC-5 | `TestBookCellSize_SoleMemberOfItsSize` |
| AC-6 (= NFR-008 **AC-371**) | `TestBookCellSize_BelowFloorFlagFollowsTheSharedSize` |
| AC-7 | `TestBookCellSize_IsOrderIndependent` |
| NFR-008 **AC-370** (the inherited obligation) | `TestBookCell_ThirtyByThirtyDepthTenHoldsTheAmendedFloor` |
| card item 5 (the cost) | `TestBookCellSize_TheCostOfABookWideCell` |
| G-1 | structural (`book_cell_spec` lowers only) + `TestBookCellSize_HoldsTheSevenAndAHalfMillimetreCap`, and the existing NFR-008 tests still green |
| G-2 | the existing FR-031 tests (`tests/test_book_floor.py`, `tests/test_book_select_floor_tiles.py`, `tests/property/test_book_membership_floor.py`) all green |
| G-3 | `test_each_page_still_draws_its_own_grid_unrotated`, and `tests/test_book_floor.py`'s `test_the_puzzle_is_untouched_by_being_measured` |
| G-5 | no fixture regenerated or deleted; none needed re-recording (see below) |

**G-5, measured rather than asserted:** no baseline fixture needed re-recording. Every existing
baseline corpus has **at most one member per grid size, or several with identical clue depths**
(`book_corpus.baseline_puzzles` is 30x30x9, two identical 10x10x3s and a 15x15x4;
`corpus_puzzles` is 18x18 and 20x20 all at depth 6), so the shared figure equals the per-puzzle
one for every one of them and the pages are byte-identical. That is also why
`tests/fixtures/book_baseline_card225.json` (named in `Touches`) was **not** created: a baseline
that records no change is a fixture nobody can regress against.

### Findings for the orchestrator (nothing edited under `meta/architecture/**`)

1. **EC-021's "three readings, one number" is incompatible with NFR-008 as amended, and this
   card narrows it rather than meeting it.** The tile, the add refusal and the finalise count
   cannot all be one number once the printed cell is a property of a *membership*: a candidate on
   the selection tab has no membership and therefore no shared cell. What this card ships is: the
   **gate** and the **finalise count** are one number (the printed, book-wide figure), and the
   **tile** is the candidate's own ceiling, which equals it exactly whenever the candidate would
   be the only member of its grid size. Recorded as F-13 and as a `STRUCTURE:` note; EC-021's
   own wording is owed a decision at the architect station, which this card does not take.
2. **The existing EC-021 property corpus cannot see this card at all.**
   `tests/property/test_book_membership_floor.py` draws 24 puzzle shapes and **all 24 extents are
   distinct** (verified by re-running its own `puzzle_shapes()`), so every grid size has exactly
   one member and the shared figure is the per-puzzle figure in every one of its 384 decisions.
   The file is green, unchanged, and that green says nothing about this card — which is why the
   cost corpus in `tests/test_book_cell_size.py` exists. Its corpus was **not** widened: that is
   EC-021's property, not this card's, and widening it would have changed what a standing
   property test is about.
3. **`tests/test_layout_page_spec.py` still measures the retired CON-018 margins.** The tests
   NFR-008's AC-238 and AC-239 *name* —
   `TestBookCell_ThirtyByThirtyNineDeepAboveFloor` and `TestBookCell_TwelveDeepBandFallsBelowFloor`
   — are written against a literal `BOOK1_ODD` spec with `outside/top/bottom = 9.525 mm` and a
   `BOOK1_USABLE_WIDTH_MM = 193.675`, and they assert **4.97 mm** and **4.61 mm** against the
   **retired 4.8 mm** floor. The registry's re-measured figures are 4.885 mm and 4.536 mm. They
   are green because the spec is a literal, so nothing is broken — and the amended figures *are*
   pinned, by `tests/test_book_page_spec.py` (4.885 at line 249, 4.536 at line 473) under
   different names. So AC-238/AC-239's **named** tests do not measure their criteria. Left
   untouched: the file is outside this card's `Touches` and the drift is CARD-222's residue, not
   this card's. Worth a card.
4. **Two G-1 guards in `tests/test_book_select_floor_tiles.py` were updated, and one of them was
   briefly a control that could not fail.** `test_the_finalise_count_follows_it_too` and
   `test_the_tile_flag_and_the_finalise_count_are_the_one_verdict` stub `app.book_cell_mm` and
   require both screens to follow; the finalise count now reads `book_cell_sizes`, so that stub is
   stubbed too. The first attempt returned `{(0, 0): 1.0}` — a key no record can match, so the
   lookup missed and the count was reached through the `book_cell_mm` fallback instead. Both
   stubs now key by the members they are handed, and the `book_cell_mm` stub was removed from the
   finalise case so the figure can only have come from the new door.

### What the reviewer should look at hardest

1. **`BookManager._below_floor_for`'s prospective membership** — F-10 and F-11 are the two
   consequences and F-11 is the declared-wrong one: a submitted member the floor goes on to
   refuse was still in the set its siblings were measured with, so a sibling can be refused for a
   puzzle that did not join. One pass, no fixpoint, chosen deliberately. Judge the choice, not
   the absence of a loop.
2. **F-13, the tile/gate divergence**, against finding 1 above. This is the one place the card
   knowingly fails a standing EC rather than meeting it.
3. **F-7's exactness bound.** `cell_mm` is *exactly* equal for every member of a grid size
   (`float(Fraction(repr(x))) == x` round-trips), but the exact `pitch` fed to `_round_px` can
   differ by <= 1 float ulp for the **deepest** member, which is why this card's tests assert "one
   device pixel spread over the grid's columns" rather than pixel identity. The claim in the test
   file's docstring is written to exactly that bound.
4. **M6's two-round history.** The claim was in a docstring before any test could see it, which is
   the finding family waves 46-47 clustered. Check that the second widening really is the test
   that kills it and that the first one is not now claiming more than it catches.

### System contract — verdicts

The 17 curated rules, judged. Several are in scope without being in this card's subject area
(the card records that residue: the model's scopes resolve to all of CTX-001), and those are
said so rather than contorted into relevance.

| rule | verdict |
|---|---|
| ADR-0033/R1 — assembly never changes a puzzle's grid, clues, tier or strategies | **held.** This card writes no puzzle field at all; it changes a `PageSpec.cell_cap` and reads clue sets. `book_cell_sizes` takes `(row_clues, column_clues)` and nothing else — not an id, not a tier, not a grid. Pinned by `test_each_page_still_draws_its_own_grid_unrotated` and by `tests/test_book_floor.py::test_the_puzzle_is_untouched_by_being_measured` (green). |
| ADR-0036/R1 — `compute_layout` without a `PageSpec` is byte-identical A4; CLI/web output unchanged by any book-only field | **held, structurally.** `src/nonogram/export/layout.py` is **unedited**. The new cap lives on the book's `PageSpec`, which the default A4 path never carries, and `book_cell_spec` *refuses* a spec with `CellCapPolicy.COMFORT_CURVE` rather than giving a CLI sheet a book cell. `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`, `tests/test_export_a4_golden.py` and `tests/property/test_cli_exports_byte_identity.py` all green. |
| ADR-0036/R2 — book page geometry computed only by COMP-007's layout functions with the book's `PageSpec`; the panel places nothing | **held.** The per-grid-size figure is a `min` over `compute_layout`'s own `page.cell_mm` values and reaches the page as a lowered cap, so every coordinate still comes out of `compute_layout`/`compute_pair_layout`. The precedent is `compute_pair_layout`'s own `fit_spec`. The panel added no arithmetic on a margin, a gutter or a sheet. |
| ADR-0036/R3 — exactly one function in `src/nonogram/**` puts a round mark on a page | **not reached.** No mark is drawn by anything this card touches. `test_the_books_own_pages_carry_no_undeclared_round_mark` green. |
| ADR-0036/R4 — no string literal in `src/nonogram/**` holds U+25A0..U+25FF, U+2022 or U+2219 | **held.** Checked by running `test_no_module_types_a_round_mark_as_a_character` over the edited files (green); the new docstrings use ASCII `*` for their bullets. |
| ADR-0037/R1 — a book puzzle page never prints the picture's title | **not reached.** No band text changed. |
| ADR-0037/R2 — thin rule >= 0.25 mm, heavy twice the thin, pure black; the default spec's strokes unchanged | **held, and worth the reviewer's eye.** A smaller cell gives thinner rules, which is exactly why `min_thin_rule_mm` exists and is untouched on the book profile (0.25 mm). `tests/property/test_book_layout.py` (the ADR-0037/R2 strokes) and `tests/test_book_page_frame.py`'s furniture floor are green over the new cells. |
| CON-020 — no interior text below 10 pt, clue digits inside clue cells exempt | **held.** Clue digits follow the cell (CON-020's own 2026-10-06 exemption, INV-006), which is the only type this card can move; no face, caption, band or folio size changed. `TestInteriorType_EveryFaceHoldsTheFloor` and `tests/test_book_interior_type_floor.py` green. |

**A count to flag, not to fix.** The brief says the curated System contract holds **17** rules;
the `## System contract` section of this card lists **8** as bullets (ADR-0033/R1,
ADR-0036/R1..R4, ADR-0037/R1, ADR-0037/R2, CON-020), plus two *carried notes* (NFR-008 and
AC-370's owed test) that are context rather than rules, and a footnote recording 52 further
package-wide-scoped rules deliberately not listed. Every one of the 8 is judged above — none
is skipped and none is left implicit. The 8-vs-17 gap is in the projection, not in this card's
coverage, and the card's own instruction applies: fix the source artifact, never the list. No
`meta/architecture/**` file was edited.

### Commit

`ba6c5b7` on `card/225-one-cell-size-per-grid-size` — 8 files, `src/` and `tests/` only, staged
with explicit pathspecs. Nothing under `meta/` is committed; this card's own notes stay in the
working tree for the orchestrator, and `meta/architecture/**` is untouched.

Files: `src/nonogram/admin/book_page_spec.py` (the two new functions),
`src/nonogram/admin/book_pdf_generator.py` (the map, threaded),
`src/nonogram/admin/book_manager.py` (the gate),
`src/nonogram/admin/app.py` (the finalise flag),
`src/nonogram/admin/templates/book_select_puzzles.html` (prose only — the tile's figure is
re-described as a ceiling), `tests/test_book_cell_size.py` (new),
`tests/property/test_book_pdf_geometry.py` (EC-022's corpus reads the book-wide cell),
`tests/test_book_select_floor_tiles.py` (two G-1 guards stub the new door too).
`src/nonogram/export/layout.py` is **unedited** although `Touches` admits it.

### What was run (not the full suite — the orchestrator runs that at the gates)

`tests/test_book_cell_size.py` (43), every `tests/test_book_*.py` and `tests/test_books_list_*.py`
with `tests/test_answer_page_layout.py` and `tests/test_layout_page_spec.py` (**2609 passed,
1 skipped**), all nine `tests/property/test_book_*.py` plus `tests/test_cli.py`'s structural
import guard, `tests/test_export_a4_golden.py`,
`tests/property/test_cli_exports_byte_identity.py`, `tests/test_book_difficulty_dots.py`,
`tests/test_book_interior_type_floor.py`, and five `tests/test_admin_*.py`. All green. No timing
figure was taken anywhere (a sibling card is running concurrently).

The tree is clean and unmutated: every mutated file was restored from
`scratchpad/card225-pristine/` and `diff -q` confirmed identical before the commit.

## Worktree notes (CARD-225 fix cycle 1, 2026-10-19 — review cycle 1 scored 7.5, four Important)

One root cause behind three of the five Important findings, and the review named it: **both
standing properties whose *meaning* this card changes are verified over corpora that cannot hold
two members of one grid size.** The implementation notes recorded that blindness for EC-021's
corpus and not for EC-027's — the one whose verdict the card actually moved. Everything below
follows from that split: EC-027's corpus is *fixed*, EC-021's is *left alone* and its card-side
face is tested instead.

### F-003 (important, EC-027) — the pairing property can now see F-8, and fails for the right reason

`tests/property/test_book_pairing.py` was green over 3600 books and structurally could not
instantiate the pairing verdict this card ships, twice over: the walk half called
`puzzle_pages` with **no `cell_sizes`** (the F-14 fallback, no longer production), and the
rendered half filtered out every book with two members of one extent. The oracle
`_expected_pages` decided each offer from the pair alone. All three are closed:

* **the production door.** The walk half now calls
  `generator.puzzle_pages(payloads, cell_sizes=generator.cell_sizes(payloads))` — the map
  `section_plan` and `puzzle_page_plan` both settle.
* **the oracle.** New `Sheet.single_height_mm`, `Sheet.cell_mm(across, down)` (FR-030's
  single-page fit, this module's own arithmetic) and `Sheet.book_cell_mm(order)` (the minimum
  within each grid size), copied in shape from `tests/property/test_book_pdf_geometry.py`'s
  `Sheet.book_cell_mm`. `Sheet.shared_cell_mm` takes a `cap=` that replaces NFR-008's standard
  cell as the first term of **both** minima (unreserved and reserved), which is exactly where
  `compute_pair_layout`'s `fit_spec` carries the lowered cap. `_expected_pages` reads the whole
  book's cells before it walks it and caps each offer at `_book_cap_mm` — the smaller of the two
  members' grid-size cells. Cross-checked against production for the six hand-built members:
  **identical to the last bit** (`diff = 0.000e+00`), not merely within tolerance.
* **the corpus.** The rendered half's distinct-*extent* filter is replaced by a distinct-*drawing*
  filter, and the read-back is `(columns, rows, across, down)` — all four measured off the ink
  (`_measured_extent`, from `page_ink`'s own `left`/`top`/`grid_right`/`grid_bottom`), so two
  members of one grid size at different clue depths are still told apart by the sequence the pages
  show. Measured: the ink gives 23.966 for 24, two orders of magnitude from the next integer.
  Two members of one grid size *and* identical gutters are one drawing twice over and are still
  filtered out — there is nothing on the page to tell them apart.
* **and the shape the sweep cannot draw.** F-8 needs one grid size to hold a pair that fits
  two-up *and* a third, deeper member that takes the size's cell under 7.0 mm. On Book 1 that
  needs 22..24 columns, shallow rows, and the same grid size **twice** in a book of at most
  eight: `_puzzle` draws a side in that window about once in twenty-three and the pair of them
  essentially never — zero occurrences in the 3600-book sweep. So `_book_cell_books()` builds
  two books by hand (the refusal at 22x10, the smaller-cell case at 24x10), appended **after**
  the sweep through a generator so every existing minimum still reads on the same rng stream.
  Counters `refused_on_book_cell >= 1`, `book_cell_lowered >= 1` and `shared_binds >= 1` assert
  the new term is not a no-op — the `shared_binds` pattern this same diff introduced in
  `test_book_pdf_geometry.py`.

**The property can now fail, measured.** Mutant M-A: `_pair_cell_mm` returns `None` (the
book-wide term deleted from the production side). Before this fix both tests passed; now **both
fail** — the walk half on `assert [(1, 2), (3,)] == [(1,), (2,), (3,)]`, the rendered half on
its own page read-back. Mutant M-B: `book_cell_sizes` takes `max` instead of `min` within a grid
size — **both fail** as well. Both files restored from byte-identical backups, `diff -q`
confirmed.

### F-001 (important) — `book_cell_spec`'s two refusals, reached the only way they can be

`grep -rn "book_cell_spec" tests/` returned zero. New
`TestBookCellSpec_LowersTheCapAndRefusesANonBookSheet` in `tests/test_book_page_spec.py`: the
cap wins above 7.5 mm and at it (F-5); the spec is otherwise untouched (`== replace(spec,
cell_cap=...)`); a `COMFORT_CURVE` sheet is refused, asserted both on `DEFAULT_PAGE_SPEC` (the
CLI/A4 sheet the ADR-0036/R1 verdict is about) and on a *book* sheet given the curve, so the
refusal is not passing for want of a parity; and ten bad `cell_mm` values are refused naming the
argument — `0`, `-1`, `-0.5`, NaN, ±inf, `True`, `False`, a string and `None` (F-6).

**The both-refusals mutant is now red.** Mutant M-C, exactly the reviewer's: both `raise
ValueError` blocks deleted and the COMFORT_CURVE branch replaced by `return replace(spec,
cell_cap=float(cell_mm))`. Before: **287 passed, 0 failed** over the five plausible files. After:
**11 failed, 289 passed**, every failure in the new class. Restored, `diff -q` identical.

### F-002 (important) — the documented contract is true again, and the "alone" case now exists

Measured on this branch before the fix, driving `puzzle_page_plan` with
`tests/test_book_pdf.py::_unmeasurable_puzzle`:

| case | `main` (7bc93c1) | this branch, before | this branch, after |
|---|---|---|---|
| same-tier neighbour | `RuntimeError "puzzle #1, #2 could not be laid out: …"`, `__cause__` a `ValueError` | `ValueError "clue sets disagree about the grid: …"`, `__cause__` `None` | `RuntimeError "puzzle 'Half-unmeasurable' could not be laid out: …"`, `__cause__` a `ValueError` |
| alone in its tier | planned fine, 1 page | the same bare `ValueError` | the same named `RuntimeError` |
| different-tier neighbour | planned fine, 2 pages | the same bare `ValueError` | the same named `RuntimeError` |

`puzzle_page_plan` now wraps its `cell_sizes` call in the `_unmeasurable_members` →
`RuntimeError` the sibling already had, and passes the rows' own **ids** (not positions) so the
message is the handle a 120-puzzle book offers. Its `Raises:` block is re-derived from the code
rather than re-worded: it records that the abort is now raised for a member whatever neighbour it
has, which is new, and that the ValueError case is the *book's* spec. Three new parametrized
cases in `TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle` — including **alone**, which exists
on no earlier tree — plus an assertion that the good neighbour is not accused. Verified red
against the pre-fix file: all three fail. Failure-matrix row F-3 amended; `section_plan`'s own
`Raises:` block updated too.

### F-004 (important) — this card's half of the EC-021 divergence, tested; the registry half untouched

`tests/property/test_book_membership_floor.py`'s corpus is **left alone** (confirmed again:
`puzzle_shapes()` gives 24 shapes with 24 distinct extents) and no `meta/architecture/**` file is
edited. What is new is the loop the owner meets, in
`tests/test_book_select_floor_tiles.py::TestBookSelect_ATileClearsTheFloorAndTheAddStillRefusesIt`:
a book already holding a 30x30 at 12/8-deep gutters (joined with its own stored override, as
INV-006 requires), then a 30x30 candidate at 1/1 —

* the tile shows **6.15 mm** with `data-below-floor` absent;
* `books.below_floor(book_id, [candidate])` refuses it naming **4.54 mm**, the grid size's own
  figure, and the selection POST shows that figure and the floor;
* `tile >= gate`, asserted, plus `tile > gate` so the bound is not vacuous on this book;
* a control: without the deep member the same candidate is admitted.

Written to survive the registry's decision either way — it asserts what each screen shows and
the ordering between the two figures, and no sentence of EC-021. Discriminating: with
`_member_clue_sets` dropped from the prospective membership, two of the four fail.

### F-005 (important) — the docstring now says what the test does

M6 reproduced: with `puzzle_section`'s walk handed `self.cell_sizes(payloads[start:end])`,
`tests/test_book_cell_size.py` gives **1 failed, 42 passed** and the quoted test
(`test_the_size_is_the_books_and_not_one_levels`) **passes**; the single failure is
`TestBookCellSize_SharedPageTakesTheSmaller::test_the_pair_is_capped_by_a_member_in_another_level`,
two classes away. The docstring is corrected to that — it is the claim's substance on the
single-page path and **not** a guard, because single pages are drawn from
`SectionPlan.cell_sizes` in `interior_stream` and never see the slice — and it names the test
that does kill M6. The cross-reference is added in both directions, so the pair is legible as a
pair from either end.

### Minors

* **F-006 — fixed, with a correction to the finding.** The shape it describes is not reachable:
  measured before the fix, a book with `trim_width_cm="abc"` raises a bare
  `ValueError("book trim_width_cm must be a number of cm, not 'abc'")` from **both**
  `section_plan` (which reads the sheet for its TOC measurement several lines *above* the cell
  map's try) and `puzzle_page_plan` (which had no handler at all). No 120-number message was ever
  produced. The remedy was taken anyway, because the property held only by the accident of one
  call's position: `section_plan` now reads `spec = self.page_spec(1)` once and feeds
  `page_frame(spec)` (no extra call), `puzzle_page_plan` reads it before its new handler, and
  `test_an_unreadable_print_specification_is_the_books_own_failure` pins the ValueError for both
  entries. New failure-matrix row **F-3b**.
* **F-010 — taken.** One sentence each in `BookManager._below_floor_for` and `app._book_cells`:
  the floor's subject moving from a puzzle to a membership takes the measured corpus from 186 to
  325 below the floor — +75%, 139 more puzzles needing a stored override — met at the selection
  step, and `TestBookCellSize_TheCostOfABookWideCell` is named as where it is pinned.
* **F-007 — taken.** `_measure` became a module-level `functools.lru_cache`d `_measured_cost(seed)`
  returning immutable tuples; the six tests keep their independence (none writes to what they
  share) and `test_the_corpus_is_the_size_it_says_it_is` still asserts `MIN_COST_CASES` against
  that same object, so the corpus cannot silently shrink. One construction and ~2.8k
  `compute_layout` calls instead of six and ~16.6k. **No timing figure is claimed** (a sibling
  card is live).
* **F-008 — taken, and asserted.** New `_in_submission_order(refusals, puzzle_ids)`, called at
  both of `_below_floor_for`'s return points, restores the order the one-loop version had by
  construction. `TestBookFloor_RefusalsComeBackInSubmissionOrder` pins it with an unreadable
  member *between* two below-floor ones — the only arrangement that can tell the restored order
  from "unreadable first" — plus the reversed control, which is marked as a control because it
  passes either way. Red without the sort.
* **F-009 — judged; the suggestion's first half declined, its second taken.** No filtering or
  caching was added: the finding's own suggestion is "nothing to do now", there is no registry
  threshold, and timing is forbidden this cycle. The figure (a 150-member book pays 150
  `compute_layout` calls to judge one add) and the identified narrowing (filter the member walk
  to members sharing a grid size with the submission — an identical result over a strictly
  smaller set, because the map's other keys are never read) are now stated in
  `_member_clue_sets`' own docstring, where the cost is incurred.

### Mutants run this cycle, and what each did

| | mutant | before the fix | after |
|---|---|---|---|
| M-A | `_pair_cell_mm` returns `None` (book-wide term deleted from pairing) | `test_book_pairing.py` green | **both** EC-027 tests fail |
| M-B | `book_cell_sizes` takes `max` instead of `min` within a grid size | — | **both** EC-027 tests fail |
| M-C | both `book_cell_spec` refusals deleted, COMFORT_CURVE branch returns a spec | 287 passed / 0 failed | **11 failed**, all in the new class |
| M-D | `puzzle_page_plan` left as committed (the pre-fix file restored) | — | the three new `puzzle_page_plan` cases fail |
| M-E | `_below_floor_for`'s `prospective` drops `_member_clue_sets` | — | 2 of the 4 new selection-tab tests fail |
| M-F | `_in_submission_order` returns the list unsorted | — | the F-008 order test fails (its control passes, as declared) |
| M-G | `puzzle_section`'s walk sized on `payloads[start:end]` (M6, re-measured) | 1 failed / 42 passed | unchanged — which is the point of F-005 |

Every mutated file was restored from a byte-identical backup and `diff -q`'d; `git diff --stat`
was used to confirm the two files that should match HEAD exactly do. The tree carries no mutant.

### What was run (not the full suite — the gates own that)

* the nine directly affected files, plus `tests/test_cli.py`'s structural import guard and
  `tests/test_suite_profile.py`'s frozen-render-set guard: **867 passed, 4 skipped**;
* every `tests/test_book_*.py` and `tests/property/test_book_*.py`, with
  `tests/test_books_list*.py`, `tests/test_export_a4_golden.py`,
  `tests/property/test_cli_exports_byte_identity.py`, `tests/test_layout_page_spec.py` and
  `tests/test_answer_page_layout.py`: **2779 passed, 1 skipped**;
* `tests/test_admin_*.py` and `tests/test_puzzle_*.py`: **1326 passed, 4 skipped**.

All green. **No timing figure is claimed anywhere** — two sibling cards are live. The frozen
render set needs no restatement: every new render call site is in a file already in it
(`test_book_pairing.py`, `test_book_pdf.py`, `test_book_cell_size.py`), and the guard
`test_the_frozen_render_set_still_matches_the_grep_that_defines_it` is green.

### Commit

`0cba979` on `card/225-one-cell-size-per-grid-size` — 9 files, `src/` and `tests/` only, staged
with explicit pathspecs. Nothing under `meta/` is committed: this card's notes and
`meta/review/20261019T173817Z-CARD-225-cycle1.yml` (all ten findings written back as
`status: fixed`, `fixed_in: 0cba979`, with F-006's and F-009's decisions recorded in full) stay
in the working tree for the orchestrator, and `meta/architecture/**` is untouched.

### [Fix 1] declarations — orchestrator, 2026-10-19 · `0cba979`

**All ten findings closed with demonstrations rather than assertions.** 9 files, `src/` and `tests/`
only; 867 / 2779 / 1326 passed across three widening selections; the frozen render set needed **no**
restatement, because every new render call site is in a file already in it.

**The decisive evidence for F-003 is the one that matters most: before this fix, the mutant that
deletes the book-wide term from production left `test_book_pairing.py` GREEN. It now reds both halves.**
A second mutant (`book_cell_sizes` taking `max` instead of `min`) reds both too, and the widened
oracle was cross-checked against `book_cell_mm` for all six hand-built members at **diff = 0.000e+00**
— identical to the last bit, not merely within tolerance.

**⚑ The fix found something the finding had not: F-8 does not occur in the random sweep at all.** It
needs one grid size holding both a pair that survives CARD-204's folio reserve *and* a member of the
same size at ≥28 cells — **zero occurrences in 3600 books**. So the corpus alone could never have
caught it, and two books were hand-built and appended **after** the sweep through a generator, so every
existing minimum still reads on the same rng stream. Three counters assert the new term is not a no-op.

**The agent flagged that as the judgement call for the certifier rather than burying it**, and it is the
right thing to flag: adding hand-built books *is* widening a standing property's corpus, which this
card was right to refuse for EC-021. The distinction it relied on is the one the brief drew — EC-027 is
the property this card's own change invalidated — and it stated what unpicks cleanly if a certifier
disagrees: the two books are separable, and the oracle, the production door and the drawing-extent
read-back stand without them.

**⚑ F-006's premise was wrong, and it said so instead of quietly recording a fix.** The 120-number
message the finding described **was never producible**: `section_plan` reads the sheet for its TOC
measurement several lines *above* the cell map's try, and `puzzle_page_plan` had no handler at all, so
both entries already raised a bare `ValueError`. It took the remedy anyway — because the property held
only by that one call's position — and corrected the finding's premise in the report and the card.

**F-002 is now measured on three trees**, including the "alone in its tier" case that **exists on no
earlier tree**: `main` planned it fine, this branch's first cut raised a bare `ValueError`, and the fix
raises a `RuntimeError` naming the row. **F-005 took the docstring remedy** and names the one test two
classes away that actually kills M6. **F-009's suggestion was half-declined with its reason** — no
filtering or caching added, the figure and the identified narrowing recorded in the docstring instead.

- **[Build gate 2]** `0cba979` — **2 failed**, 8558 passed, 1 skipped, 15:19.
  `tests/property/test_book_ready_gate.py::test_no_exit_from_draft_bypasses_it_in_either_storage_mode[published-db]`
  (SQLAlchemy's insertmanyvalues sentinel processor was handed a float: `UUID(hex=inf)` →
  `AttributeError: 'float' object has no attribute 'replace'`) and
  `tests/test_admin_binding.py::TestAdminPanel_BindsLoopbackOnlyByDefault::test_loopback_is_served`
  (nothing answered on `127.0.0.1:62714` while its own server was up).
- **[Build gate 2 — not solo in fact]** The gate's guard refuses to START while another pytest is
  alive; it cannot stop one from starting afterwards. CARD-253's implementation agent ran a
  288-test Chromium suite (3:05) and two further selections inside this gate's 15-minute window.
  So the guard did its job and the window was still shared — the rule needs a lock other runs
  **honour**, not only a check at the door. Recorded as a defect in the gate procedure, not in
  this card's code.
- **[What that does and does not license]** It does **not** license writing the two failures off.
  Both files pass solo (15 passed, 6.9s), but 15 green tests are not evidence about an 8558-test
  run. The discriminator is that this suite has **no `pytest-randomly`** — collection order is
  deterministic — so a solo full suite must reproduce anything that is real or order-dependent,
  and can only come back green if the cause was concurrent. Gate 3 runs solo, first in wave 48's
  serialized chain, and is the measurement. Until it returns, this card's verdict is **unknown**,
  not green.
- **[Build gate 3 — PASSED]** `0cba979`, **solo**: 8560 passed, 1 skipped, 14:39, EXIT=0. The two
  tests gate 2 failed on are in that count and green. Order is deterministic in this suite, so this
  run is the evidence gate 2's failures were **concurrent-window artefacts** and not this card's —
  the attribution is now measured, not argued. Fix cycle 1's ten findings stand closed on a green
  full suite; next station is the certification review (cycle 2).
