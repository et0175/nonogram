# CARD-140: The arrange screen shows the book's real page breaks, not one every three puzzles

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/140-arrange-real-page-breaks
**Worktree:** —
**Source:** owner, 2026-09-23 ("arrangement of puzzles by pages — it shows 3 puzzles per page, even for big ones")
**Idea:** —
**Wave:** 26
**Depends on:** CARD-128
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_arrange_page_breaks.py
**Review score:** 9.0 (2 cycles)
**Started:** 2026-09-25T07:53:56Z
**Closed:** 2026-09-25T10:52:00Z
**Actual:** 0.4d
**Merge commit:** 5d54019
**Blocked by:** —

## What to implement

`book_arrange_puzzles.html:114` draws a page divider every third puzzle:

    {% if puzzle.order % 3 == 0 and puzzle.order < puzzles[-1].order %}
    <div class="page-break-divider"><span>page {{ (puzzle.order // 3) + 1 }}</span></div>

Three per page was never true of any book this project prints. It is scaffolding from the
original arrange step, written before the book had a page model at all. The PDF puts **one
puzzle per page**, except a two-up pair: same tier, adjacent in print order, both fitting at
one shared cell of at least 7.0 mm (INV-010, CARD-127). So the real maximum is two, and for
big puzzles on a small trim it is one. The owner reported the screen showing three pages'
worth of big puzzles on one page.

The generator already decides this. `PuzzlePagePlan` (book_pdf_generator.py:351) carries a
page's 1-based interior position and the puzzle numbers on it, and the pairing walk builds
the list. **Do not re-implement pairing in the admin panel or the template** — ADR-0036/R2
says the panel fits no cell and places no tile, and a second implementation of INV-010 is
exactly the defect this card exists to remove.

1. **Expose a pure planning seam.** The existing walk needs full `ExportPayload`s because it
   renders; the arrange screen has no grids and should not load them. Extract (or add beside
   it) a function that decides the page plan from what the screen already has — each
   puzzle's tier and (width, height) extent, plus the book's PageSpec — and have the
   rendering path call that same function, so the two can never disagree. Both the stored
   extent and the tier are already on the puzzle record.
2. **Render breaks from the plan.** The divider appears where the plan starts a new page,
   and its label is the plan's page number, not an arithmetic guess. Two puzzles sharing a
   page are shown as sharing it.
3. **Show the level dividers too** (CARD-128, which this card depends on): a level's first
   puzzle opens a new page behind a divider page, so the arrange screen must show that break
   as well, labelled with the level. This is why the card waits for CARD-128 rather than
   racing it.
4. **Page numbers are interior numbers.** The interior starts at the guide page (INV-013), so
   the first puzzle page is not page 1. Show the number the printed book will carry.

Out of scope: changing pairing, the divider design, or anything about the arrangement
semantics (level-confined moves are CARD-126's and stay untouched). This card changes what
the screen *reports*, never what the book *does*.

## Acceptance criteria

- New: a book of 30x30 puzzles shows one puzzle per page, never three.
  test: TestArrangeBreaks_BigPuzzlesAreOnePerPage
- New: two adjacent same-tier puzzles that pair are shown sharing one page, with one page
  number.
  test: TestArrangeBreaks_PairedNeighboursShareAPage
- New: the page numbers shown are the interior numbers the PDF prints, for the same book.
  test: TestArrangeBreaks_NumbersMatchTheGeneratedInterior
- New: the screen's page plan and the PDF's page plan are the same object for any book — an
  independent corpus, not one call compared with itself.
  test: PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook
- New: a level's first puzzle starts a new page and the break names the level.
  test: TestArrangeBreaks_LevelStartsANewPage

## Guardrails

- G-1: The panel decides no geometry (ADR-0036/R2). Pairing stays in COMP-007 / the
  generator; the screen asks and renders. No cell fitting, no 7.0 mm literal, no tier
  comparison for pairing in app.py or the template.
- G-2: INV-010 is unchanged — this card must not alter which puzzles pair, only what is
  displayed. The CARD-127 pairing tests stay green and untouched.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).
- G-4: No schema change and no stored page plan — pages are decided at PDF time
  (Increment 15 Rollback).

## Architecture context

- **FR:** FR-036 (arrangement), FR-041
- **INV:** INV-010 (pairing), INV-013 (interior parity)
- **ADR:** ADR-0036 (geometry ownership), ADR-0033
- **Components:** COMP-009, COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Env] forge 2026.8.17
- [Origin] Owner, 2026-09-23, after the first working deploy: "it shows 3 puzzles per page,
  even for big ones". The same message asked whether a level should start a new page —
  that half is CARD-128 (divider pages per level), already scheduled in this wave, so this
  card only has to display it.
- [Why it survived this long] Every book card so far changed the PDF, and the arrange
  screen's indicator was never wired to it. No test compared the two, which is why AC-4 is
  a property test over an independent corpus rather than another example.

### Implementation (2026-09-25)

- [The seam] `BookPDFGenerator.section_plan(rows) -> SectionPlan`
  (`book_pdf_generator.py`) is the extracted **eager** half of `interior_stream`: the print
  order, the payload pass (with the same drop and the same warning), and the level +
  pairing walk. `interior_stream` now calls it and does nothing of its own before the
  tripwires, so the export path and the arrange screen ask *one* function where a puzzle
  prints. No geometry moved: the pairing verdicts are still COMP-007's
  `compute_pair_layout`, called from the same walk as before (G-1, ADR-0036/R2; G-2 —
  `puzzle_pages`/`puzzle_section` are untouched and the CARD-127/CARD-128 tests were not
  edited). Nothing is stored and no schema moved (G-4); `export/**` and the A4 goldens were
  not touched (G-3).
- [Deviation from step 1, deliberate] The card proposed a planner over "each puzzle's tier
  and (width, height) extent". **Extent is not enough**, and AC-4 is what makes that fatal:
  a pair's shared cell is fitted from both puzzles' real clue depths
  (`layout._gutter_depth`), so an extent-only planner answers INV-010 differently from the
  book. Measured on AC-4's own corpus — `corpus_books()` at its default seed 140, grids from
  `comb_grid`, each same-tier neighbour pair offered to COMP-007's `compute_pair_layout` on
  the page the greedy walk of `planned_by_hand` would share: **24 books, 164 puzzles, 99
  same-tier neighbour pairs of which the walk offers 93, and 10 of those 93 verdicts flip**
  when both puzzles' clues are flattened to one run per line at the same extent (10 under a
  solid-grid flattening, row `(width,)` / column `(height,)`, and 10 under a
  filled-count-preserving one, `(sum(runs),)` per line). The plan therefore travels from the
  row's **stored clues** — `clues_rows`/`clues_cols`, on the puzzle record beside the extent
  and the tier, already loaded by the arrange route — so the screen loads nothing extra and
  the two plans cannot differ. Recorded in `section_plan`'s docstring and in the test
  module's, and re-derived on every run by
  `test_extent_alone_would_disagree_with_the_book_on_this_corpus` so it cannot go stale
  again.
- [The screen] `app.py` gained one module-level reader, `_printed_places(book, puzzles)`,
  which asks `section_plan` and turns the plan into per-row labels (`page`, `opens_page`,
  `shares_page`) plus each level's divider page. It fits no cell, compares no tier and holds
  no 7.0 mm literal. A book whose stored print specification will not lay out is logged and
  listed without page labels rather than 500ing on the owner three steps before Finalise.
- [The template] The `order % 3` divider is gone. A break now opens every page the plan
  starts — `page 7`, `page 7 · two puzzles` for a two-up page, and
  `page 2 · Easy divider page` for a level's divider — so two paired puzzles sit under one
  page number with no rule between them, and every number is an **interior** number
  (INV-013: page 1 is the guide page, so the first puzzle page is 3, not 1). Each row also
  carries `data-page`, which is what the tests parse. The divider's design is unchanged
  (same `.page-break-divider` markup and CSS).
- [Page estimate untouched] The sidebar's "~N pages" is still the old rough count; making it
  exact is CARD-129's, not this card's.

AC → test (all in `tests/test_book_arrange_page_breaks.py`):

- AC-1 one puzzle per page for 30x30s, never three —
  `TestArrangeBreaks_BigPuzzlesAreOnePerPage` (3 tests: five 30x30s are pages 3..7, the
  screen agrees with both independent plans, and no label claims a shared page).
- AC-2 a pair shown sharing one page, with one page number —
  `TestArrangeBreaks_PairedNeighboursShareAPage` (4 tests: one label for the shared page, no
  rule between the two rows, the third of a run starts the next page, and different tiers
  never share).
- AC-3 the numbers shown are the interior numbers the PDF prints —
  `TestArrangeBreaks_NumbersMatchTheGeneratedInterior` (2 tests: the interior the **download
  route** served is read back with `tests/helpers/pdf_pages.pdf_pages` and each page the
  screen named is measured off its own ink — two 10-column drawings on the page it calls
  shared, a 30x30 grid on the page it gives the big puzzle, no ruled grid on the pages it
  calls divider pages).
- AC-4 the two plans are the same for any book —
  `test_PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook` (the repo's
  `test_PropertyTest_*` naming, so it is collected): 24 seeded books, 164 puzzles, three
  readings compared per book — the route's HTML, `planned_by_hand` (an independent second
  implementation of the walk in the test tree, over COMP-007 and `book_page_spec`, which
  never imports the generator's walk), and the export path's own `section_plan`. The test
  asserts its own corpus size and that it produced at least five shared and five single
  pages, so it cannot shrink into agreeing about nothing.
- AC-5 a level's first puzzle starts a new page and the break names the level —
  `TestArrangeBreaks_LevelStartsANewPage` (3 tests: the six labels of an easy/medium/hard
  book in order, a pair split by a level boundary, and no divider for an empty level).

Mutation-checked: labelling the break with the row's own number instead of the plan's page
fails 8 of the 13 tests, the property test among them.

- SCOPE+ tests/test_book_level_order.py — CARD-128 left two tests pinning the divider that
  this card removes (`..._counts_the_whole_book_not_each_level` expected `["2", "3"]` for
  seven puzzles, and `..._follows_the_last_puzzle_of_the_book` expected *no* divider at all
  for three). Both were rewritten to the new labels, keeping their original subject — the
  numbers do not restart at a level heading, and no rule dangles after the last row. No
  CARD-127 pairing test was touched (G-2).
- Suite: the whole of it (5301 collected) with exactly the two pre-existing failures named
  in the handover and nothing else —
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`
  (both stale heading assertions on the batch-create form, untouched by this card).

### Orchestrator gates (2026-09-25)

- [Scope] src/nonogram/admin/app.py, src/nonogram/admin/book_pdf_generator.py,
  src/nonogram/admin/templates/book_arrange_puzzles.html,
  tests/test_book_arrange_page_breaks.py, tests/test_book_level_order.py — one commit, 5ccd7a9.
- [Build gate] PASSED (full, re-run by the orchestrator in the worktree, not taken on the
  agent's word): the two pre-existing failures above and nothing else. The two touched test
  files alone: 75 passed.
- [Guard] G-1..G-4 checked mechanically before review, not read off the agent's summary:
  no `7.0`/`compute_pair_layout`/`_gutter_depth` and no tier comparison in `app.py` or the
  template (G-1); `puzzle_section`'s signature byte-identical to main, the `ids=` kwarg
  already existed there, `puzzle_pages` and the CARD-127 tests untouched (G-2); the diff
  names no `src/nonogram/export/**` and no `a4_golden` path (G-3); no migration and no
  stored plan (G-4).
- [System contract] The card was cut without a `## System contract` section; the model's
  lens yields 44 applicable rules for this card's scope. Rather than freeze 44 statements
  into the card, the section below names the ids and the reviewer regenerates the
  statements at review time — the projection is then fresh by construction, which is what
  the freshness rule is protecting. Regenerate with:
  `python3 <forge>/skills/architect-validate/scripts/system_rules.py --card CARD-140`.
- [Card defect, for the decompose station] Step 1 of "What to implement" specifies the
  planning seam over "each puzzle's tier and (width, height) extent". That is provably
  insufficient — see the implementation's deviation note above — and the card should be
  corrected at decompose so the next reader is not misled into an extent-only planner that
  passes four of the five AC.

- [Review 1/3] 8.0 · risk MEDIUM · lane DEEP ·
  `meta/review/20260925T084912Z-CARD-140-cycle1.yml` · 0 critical, 2 important, 2 minor.
  System contract: 44 rules — 11 ✓ holds (each cited to a named test run green on 5ccd7a9),
  33 ⚠ unchecked (all `no_eligible_fact`), 0 ✗ violated. G-1..G-4 ✓ independently.
  The seam was verified single line-by-line against main, including the export path's
  tripwires, `answer_key`, `tier_breakdown` and `first_answer_page` — 254 passed, 1 skipped
  over the eight book-export test files. Nothing the orchestrator pre-verified turned out
  wrong.
  - F-001 (important) The measurement that justifies departing from the card's step 1 does
    NOT reproduce: the docstring and the deviation note above claim 24 books / 145 puzzles /
    126 same-tier verdicts / 21 flips; independently re-derived from the test module's own
    corpus it is 164 puzzles / 99 pairs (93 offered) / 10 flips, and 126 is arithmetically
    impossible against a ceiling of 99. **The conclusion stands** — 10 of 99 verdicts flip,
    so an extent-only planner really would disagree with the printed book — but the figures
    are the whole recorded justification and sit in a docstring later cards will cite
    instead of re-measuring.
  - F-002 (important) The catch-all around `_printed_places` blanks every page label AND
    every level divider, which renders identically to a book with no page structure; it
    also swallows errors raised inside `_printed_places` itself — a rename of
    `SectionPlan.ids` would degrade the screen in silence, which is precisely the
    single-seam regression class this card exists to make impossible. No test drives the
    branch, so the comment's "does not 500 on the owner" promise is unverified.
  - F-003 (minor) `places` keyed by `str(id)`: two rows with `id=None` collapse to one
    entry. Unreachable today, and the only inexact step in the seam.
  - F-004 (minor) AC-4 keys on `item-order`, which counts every member, while the plan
    numbers only rows that built a payload — identical on this corpus by accident, and the
    undrawable-member case is uncovered.
  - Deferred to cycle 2 by the cost ladder: `8f-mutation` and `8g-baseline` certification.
- [Review sync] 1 report → meta/review/

### [Fix 1] Cycle-1 review findings (2026-09-25)

Report: `meta/review/20260925T084912Z-CARD-140-cycle1.yml` (score 8.0). All four findings
fixed; nothing dismissed. Scope held to the five files the implementation already touched.

- **F-002 (important) — the catch-all around `_printed_places`.** The guard stays (standing
  convention: an intentional outer try/except is not removed) and is now two clauses.
  `(RuntimeError, ValueError)` are the failures the seam *declares* — `RuntimeError` from the
  pairing walk (`puzzle_pages`), `ValueError` from `book_page_spec`/`BookPDFGenerator.__init__`
  on a stored trim or margin that is not a sheet — and are logged as a warning. A second
  `except Exception` keeps the screen up for anything else but logs it with
  `app.logger.exception(...)`, so a bug *inside* `_printed_places` (a renamed plan field, a
  changed `numbers` index — the single-seam regression class this card exists to remove) is on
  the record with its traceback and is distinguishable in the log from a book whose stored
  specification is at fault. The screen no longer misinforms: the route passes
  `page_plan_failed` and the template renders one line where the first page label would have
  been — `alert alert-warning` / `role="status"`, the Print setup step's own pattern for a
  stored specification it could not read, with no colour, size or font literal of its own, so
  the design-token check still passes. Four new tests in
  `TestArrangeBreaks_WhenThereIsNoPlanToShow`: the step answers 200 and lists every row with
  no labels and the notice when the trim cannot be laid out; a planned book shows no notice;
  the declared failure logs one WARNING with no traceback and names the column; and a plan
  whose pages name puzzles it does not carry (an `IndexError` raised inside the seam itself)
  still answers 200, still shows the notice, and is logged at ERROR *with* `exc_info`.
- **F-001 (important) — the deviation's figures did not reproduce.** Re-measured from scratch
  (not copied from the review), from the test module's own `corpus_books()` at its default seed
  140, grids from `comb_grid`, rows from the new `corpus_rows`, and the greedy same-tier walk
  of `planned_by_hand` — which now optionally reports each pair it offers COMP-007 and the page
  they would share, so the measurement reads *that* walk rather than being a fourth
  implementation of it. Page specs from a book with no stored print specification, which is
  CON-018's Book 1 profile and so exactly what `create_book` leaves. **Measured: 24 books,
  164 puzzles, 99 same-tier neighbour pairs in print order, 93 of them actually offered by the
  greedy walk (a pair that forms consumes its successor), and 10 flipped verdicts** when both
  puzzles' clues are flattened to one run per line at the same extent — 10 under a solid-grid
  flattening (each row `(width,)`, each column `(height,)`) and 10 under a
  filled-count-preserving one (each line `(sum(runs),)`), so the figure is not an artefact of
  one flattening. The old 145/126/21 are gone from all three places (the test module docstring,
  `section_plan`'s docstring, this card's deviation note); 126 was impossible against a ceiling
  of 99. The conclusion is unchanged and stands: the flips are not zero, so extent alone
  answers INV-010 differently from the book and the plan must travel on the stored clues. It
  is now pinned by `test_extent_alone_would_disagree_with_the_book_on_this_corpus`, which
  re-derives every figure on each run (0.05 s: no book is stored and no page is drawn) and
  asserts both the exact set and the two properties that matter — the walk cannot offer more
  pairs than the corpus has same-tier neighbours, and the flips are not zero.
- **F-003 (minor) — `places` keyed by `str(id)`.** `SectionPlan` gained `printed`: the rows
  that built a payload, themselves, in print order and parallel to `ids`/`payloads`.
  `_printed_places` now writes `places[id(plan.printed[number - 1])]` and the route reads
  `places.get(id(puzzle))`, so the key is the plan's own coordinate resolved to the row it
  names. Two rows with no id, or ids that stringify alike, no longer collapse into one entry
  with the later row's page. `interior_stream` is untouched beyond passing the new field
  through `section_plan`; the export path's behaviour is byte-identical.
- **F-004 (minor) — AC-4 keyed on `item-order`.** `shown_plan` now keys on the plan's own
  puzzle number: the rows carrying a `data-page`, counted 1..n in document order. (`item-order`
  counts the whole membership and is read only by the new `shown_orders`, where that number is
  the subject.) New `shown_rows` reads each row's own `data-page`. The degenerate case the
  review focus named is now covered by
  `test_an_undrawable_member_shifts_no_other_rows_page`: a three-row book whose middle row's
  stored clues `_payload` cannot read is still listed, carries no page, and shifts neither of
  the other two — `shown_rows` is `[3, None, 4]` and the plan is `{1: 3, 2: 4}`, agreeing with
  both `planned_by_hand` over the drawable rows and `generated_plan` over all of them. Keyed on
  `item-order` that book would have read `{1: 3, 3: 4}` and failed with a confusing diff.

- Suite after the fix: the whole of it (5307 collected, +6) with exactly the two pre-existing
  failures named in the handover and nothing else —
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
  and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`.
  Guardrails re-checked: no geometry, literal or tier comparison entered `app.py` or the
  template (G-1); `puzzle_pages`/`puzzle_section` and the CARD-127 pairing tests untouched
  (G-2); `export/**` and the A4 goldens untouched (G-3); nothing stored, no schema change
  (G-4); no dependency added.

- [Build gate] PASSED (full, after Fix 1 / 71f9b41): the two pre-existing failures and
  nothing else, 5307 collected.
- [Review sync] 2 report(s) -> meta/review/ (cycle-1 report now carries all four findings at
  `status: fixed`, `fixed_in: 71f9b41`).
- [Orchestrator finding, handed to cycle 2 rather than fixed here] The F-003 fix keys the
  label dictionary by object identity — `places[id(plan.printed[number - 1])]` written,
  `places.get(id(puzzle))` read. Correct today, because `print_order` reorders the very dicts
  the route holds, and the plan keeps them alive for the request. But it couples the screen to
  identity across a module boundary: if that ever stops holding (a copy, a re-fetch, DB-mode
  materialising fresh rows per call), no exception fires, every lookup misses,
  `page_plan_failed` stays False, and the screen renders with no labels AND no notice — the
  silent-misinformation mode F-002 was fixed to remove, reintroduced through the fix for
  F-003. A count check (labelled rows vs `len(plan.printed)`) would turn it back into the
  visible notice. Left for the reviewer to judge, to keep the second circuit independent.

- [Review 2/3] 9.0 · risk LOW · lane FAST ·
  `meta/review/20260925T103146Z-CARD-140-cycle2.yml` · 0 critical, 0 important, 3 minor.
  Both deferred certifications ran. All four cycle-1 findings confirmed fixed; the fix round
  introduced no Critical or Important defect, and cycle 1's strongest guarantee (the export
  path is behaviour-identical) survives it — `SectionPlan.printed` is purely additive and
  `interior_stream` never reads it.
  - **Mutation check: 8 mutants, 0 survivors.** M1 page-number assignment → 15 kills; M2 the
    identity key swapped for an object the route never holds (the hypothesised silent total
    miss) → 17 kills; M3 the payload-drop `continue` → 3; M4 the template's break condition
    → 4; M5 the `shares_page` boundary → 4; M6 `page_plan_failed` propagation → exactly 1;
    M7 the ERROR clause downgraded to warning → exactly 1; M8 the test-side numbering moved
    back to membership counting → exactly 1, the undrawable-member test, the only test that
    can tell the two numberings apart. Working tree verified byte-clean afterwards.
  - Step 8g baseline: typed `unavailable (provider_unavailable)`, not deferred again —
    `review.visual: off`, no run target, no baselines directory, so no later cycle would
    change the answer. Static UI check green instead: no colour/px/font/`style=` literal in
    the template diff, `tests/test_admin_design_tokens.py` passing, and the new notice is
    `book_setup_print.html:91`'s pattern verbatim.
  - [Orchestrator finding judged] F-005: the identity keying is **real but unreachable on any
    path that exists today**, verified rather than assumed — `print_order` reorders the same
    objects and never copies, `section_plan` appends the row itself, and the route fetches
    each member ONCE and puts that one object into both the template rows and
    `_printed_places`, so both the legacy in-memory and the DB mode are safe; the inverse
    collapse needs a book holding one puzzle twice, which `book_manager` forbids on both
    branches. The verdict on the remedy is the useful part: keep the key, fix the detection.
    A positional key — the one identity-free option — fails **unsafely** (a row shows another
    row's page) where identity fails **safely** (no label), and it reintroduces the duplicate
    collapse. So: identity + a count check (labelled rows vs `len(plan.printed)`, flipping
    the existing `page_plan_failed`).
  - F-006 (minor) `puzzle_section`'s `ValueError("ids must be parallel to payloads")` is a
    caller precondition — the seam-bug class the ERROR clause exists for — yet lands in the
    WARNING clause without a traceback. Unreachable today (lockstep appends).
  - F-007 (minor) A dropped row renders between the "page 3" and "page 4" labels with no
    marker, so the screen implies it prints on page 3. Deliberate (a test pins the
    rendering) and far milder than the uniform blank F-002 removed.
  - Reviewer did NOT complete a whole-suite run (recorded `budget_truncated`: ~3.5 h
    projected). It ran 527 targeted tests green and confirmed the two failures are
    pre-existing by reproducing them on main. The full-suite evidence for this card is the
    orchestrator's own run on 71f9b41, above.
- [AC/EC/G check] Every AC verified by the test the card names, run in the worktree on
  71f9b41: AC-1 `TestArrangeBreaks_BigPuzzlesAreOnePerPage` 3 passed · AC-2
  `TestArrangeBreaks_PairedNeighboursShareAPage` 4 · AC-3
  `TestArrangeBreaks_NumbersMatchTheGeneratedInterior` 2 · AC-4
  `test_PropertyTest_ArrangeBreaks_AgreeWithTheGeneratedBook` 1 · AC-5
  `TestArrangeBreaks_LevelStartsANewPage` 3. Plus the fix round's
  `TestArrangeBreaks_WhenThereIsNoPlanToShow` 5, the F-001 pin 1 and the undrawable-member
  test 1 — 19 in the file, all green. G-1..G-4 re-confirmed by the reviewer independently.
- [Review sync] 2 report(s) → meta/review/

## System contract

_A projection, regenerated — never hand-edited. 44 rules apply to this card's scope
(`src/nonogram/admin/**`, `tests/**`):_

ADR-0006/R1, ADR-0019/R1, ADR-0022/R1, ADR-0022/R3, ADR-0022/R4, ADR-0024/R1, ADR-0024/R2,
ADR-0024/R3, ADR-0024/R4, ADR-0024/R5, ADR-0027/R1, ADR-0027/R2, ADR-0029/R1, ADR-0029/R2,
ADR-0029/R3, ADR-0029/R4, ADR-0029/R5, ADR-0032/R1, ADR-0032/R2, ADR-0033/R1, ADR-0035/R1,
ADR-0036/R1, ADR-0036/R2, ADR-0037/R1, ADR-0037/R2, CON-005, CON-009, CON-010, CON-011,
CON-012, CON-015, CON-016, INV-001, INV-002, INV-003, INV-005, INV-006, INV-007, INV-008,
INV-009, INV-010, INV-011, INV-012, INV-013

The load-bearing ones for this diff: **INV-010** (which puzzles pair), **INV-013** (the
interior's page-1 parity), **ADR-0036/R1–R2** (PageSpec owns geometry; the panel fits no
cell and places no tile), **ADR-0033/R1**, **ADR-0019/R1** (the adapter holds HTTP concerns
only — the rule `_printed_places` is judged against).
