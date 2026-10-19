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
**Review score:** —
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
| F-3 | `book_cell_sizes` | one member's clue sets are unreadable / disagree about the grid | `ValueError` propagates from `book_cell_mm`; **no** grid size gets a size, so nothing is printed on a guessed cell. **Amended during implementation:** the bare propagation broke the standing contract that *every* abort of `interior` names a puzzle, so `section_plan` catches it and raises `RuntimeError("puzzle <id> could not be laid out: ...")` with the `ValueError` as its `__cause__` — `_unmeasurable_members` finds the culprit on the failure path only. Pinned by the four cases of `TestBookPdf_UndrawablePuzzleAbortsNamingThePuzzle` | — |
| F-4 | `book_cell_sizes` | members handed in a different order, or the same member twice | the result is byte-identical: `min` over a set-valued grouping (AC-7) | — |
| F-5 | `book_cell_spec(spec, cell_mm)` | `cell_mm` **above** the spec's own flat cap | the cap wins: `min(spec.cell_cap, cell_mm)`. NFR-008's 7.5 mm can never be widened by this card (G-1) | cap <= 7.5 mm on every book profile |
| F-6 | `book_cell_spec` | `cell_mm <= 0`, NaN, or `spec.cell_cap is COMFORT_CURVE` | `ValueError`, naming the argument. A book sheet always carries a flat cap; a CLI/A4 spec has no book cell and is refused rather than silently given one (ADR-0036/R1) | — |
| F-7 | exactness of the shared cell | the cap is a `float` while the fit is an exact `Fraction`, so `min(cap, fit)` for the **deepest** member may differ from the cap by one float ulp | `Layout.page.cell_mm` is **exactly equal** for every member of a grid size (`float(Fraction(repr(x))) == x` round-trips). The exact `pitch` fed to `_round_px` may differ by <= 1 ulp for the deepest member only | <= 2^-52 * 7.5 mm ~ 1.7e-15 mm, i.e. <= 2e-14 device px at 300 DPI. A boundary pixel could in principle round the other way only within that distance of a half-pixel tie; no case in this card's measured corpus does |
| F-8 | two-up page (FR-040) | the smaller of the two grid sizes' book cells is **below** `TWO_UP_MIN_CELL_MM` (7.0 mm) | the pair is **refused** and the two puzzles print on separate pages. This is a behaviour change: today the pair is fitted from the pair alone and could clear 7.0 mm | book cell < 7.0 mm => no two-up page for that pair |
| F-9 | two-up page | the pair's own two-up fit is **smaller** than the smaller book cell | the pair fit wins — it is a physical constraint of putting two drawings on one sheet. AC-4's "the smaller of their two sizes" is a **cap**, not a floor | drawn cell = min(book cell A, book cell B, pair fit) |
| F-10 | the floor (FR-031) at the add gate | a submitted puzzle clears the floor alone but its grid size's **shared** cell does not | refused without a stored override, with the shared figure named. The gate measures the **prospective membership**: the book's current members **union** the whole submission, because that is what will be printed if the add succeeds | — |
| F-11 | the add gate | a below-floor sibling in the same submission is itself refused, so it never joins | the refusal of the *other* members of its grid size was nevertheless measured with it in the set — one pass, no fixpoint. **Declared residue:** such a member can be refused for a sibling that did not join; the owner's remedy is to resubmit without it. Chosen over a fixpoint loop deliberately | one measurement pass per add |
| F-12 | the finalise count (AC-187/AC-188) | the book holds a deep member of a grid size admitted by a stored override | **every** member of that grid size is listed below the floor, each with the shared cell as its `cell_mm` — AC-6 | — |
| F-13 | the selection tile (CARD-123) | the candidate is not a member, so it has no shared cell | the tile keeps showing the candidate's **own** fit on this book's sheet — a ceiling, not a promise. **Declared divergence from EC-021's "three readings, one number"**: the tile can read above the gate's figure once the book holds a deeper member of the same grid size. The gate's refusal names the figure it enforced, so the owner is told the real number at the one moment it binds | tile figure >= gate figure, always |
| F-14 | `puzzle_pages` / `puzzle_section` | called without a `cell_sizes` map (a direct caller, a test) | falls back to today's per-puzzle fit. Both production entries (`section_plan`, `puzzle_page_plan`) compute and pass the map over the **whole** book, never over one level's slice | — |
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

### [Scope] orchestrator, 2026-10-19 — clean, plus one proactive SCOPE+

**8 files changed, every one inside the predicted `Touches`** (its globs `tests/test_book_*.py` cover
`test_book_select_floor_tiles.py`). **No drift.** Several predictions went unused with stated reasons,
which is the better direction to be wrong in: `export/layout.py` needed **no edit at all** because the
book-wide figure reaches the page as a *lowered cap* and `compute_layout` still does every measurement;
`book_plan.py`, `book_finalize.html` and the helper modules were not needed; and
`tests/fixtures/book_baseline_card225.json` was **deliberately not created** — every existing baseline
corpus has at most one member per grid size or members at identical depths, so pages are byte-identical
and *"a baseline recording no change is one nobody can regress against"*.

**`meta/profiling/rank_durations.py` — SCOPE+, added by the orchestrator before the gate, not by the
agent.** `tests/test_book_cell_size.py` reads the cell off the **rendered ink**, so it matches
`RENDER_API_PATTERN` **23 times** and was absent from the frozen render-heavy snapshot. CARD-251 found
that same condition the expensive way, with a red merge gate; here it was **measured directly** (23
matches, file absent) and restated deliberately, which is what the guard asks for and costs fifteen
minutes less. Unlike CARD-251's entry this file genuinely draws, so the share it contributes is a real
render cost rather than an over-statement — which matters because CARD-218 and CARD-219 are sized
against that figure.

### [Orchestrator] A brief defect of mine, recorded

The implementation brief told the agent its curated contract held **17 rules**; the worktree copy it
actually reads carried the **8** the card was drafted with. Both numbers were mine: I re-curated the
main copy to 17 **after** the worktree was created, then tightened it to 14 later the same hour when
the `contexts: [CTX-001]` short-circuit was removed. The agent noticed the gap and said so rather than
assuming. Nothing was built against the wrong contract — it judged all 8 it had and recorded a verdict
per rule — but the brief asserted a number the agent could not see, which is the same shape this board
keeps finding. **A card's contract must be re-derived before its worktree is cut, not after.**

### [Build gate] PASSED (full, 963s, SOLO) — orchestrator, 2026-10-19 · `c0d35c0`

**EXIT=0, first attempt: 8537 passed / 1 skipped / 0 failed.** The count reconciles exactly — `main`
**8495** collected → branch **8538**, **+43**, and the card's own `tests/test_book_cell_size.py` holds
exactly **43** cases. Every test this card added is in its own file.

**It passed first time because the render-set was restated before the gate, not after.** CARD-251 hit
the same condition as a red merge gate; here it was measured directly and fixed in advance, so
`test_suite_profile` stayed green.
