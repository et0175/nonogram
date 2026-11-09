# CARD-408: Hint and Check bring what they point at into view — the hinted row or column, or the filled cell — at any zoom and in both orientations

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- One behaviour (scroll the stage so the target is visible and not under a sticky band), but it must hold across zoom, orientation, doubled and plain gutters and the three ladder rungs plus Check; the arithmetic of 'not under the sticky band' is the part that takes the cycles. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/408-hint-into-view
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-408
**Source:** owner player findings 2026-11-07, item 7, first bullet (marked essential): "Scroll the board so the hinted row or column, or the filled cell, is in view, at any zoom and in both orientations. This is the essential one."
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-403, CARD-404
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_zoom.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Real dependencies: CARD-403 (it fixes which element scrolls; a scroll-into-view written against today's nested scroller would move the page as well) and CARD-404 (the sticky bands are what the target must not hide under; their depth changes with it). -->
**Review score:** —
**Started:** 2026-11-09T18:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**Evidence:** `solver.js` paints `.is-hint-line` on a line's cells and clue boxes (`setLadderLine` / `paintLadderLine`) and `.is-hinted` on a revealed cell, and never moves any scroll position: a repo search for `scrollIntoView|scrollTo|scrollLeft|scrollTop` finds only the zoom anchoring (`applyZoom`) and no hint path. On a zoomed board the highlighted line can be entirely off-screen, so the press looks dead.

For a ROW the target is its vertical position (the row must be below the sticky column band and inside the stage; horizontally the row clue is pinned, the cells are the content); for a COLUMN the horizontal one; for a revealed CELL both. The sticky bands cover the first `band` pixels of the scroll box, so naive `scrollIntoView` leaves the target UNDER a band. Check's row (CARD-269) is the same problem and is included, because it is Hint's neighbour and the same helper serves both.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **A pure helper** in `solver_state.js` (ADR-0038/R4): given the stage's scroll offsets and client size, the sticky bands' depths and the target's box, return the scroll offsets that bring the target fully inside the visible box minus the bands; it returns the current offsets when it is already inside (no movement, no jump).
2. **Wire it** to rung 1, rung 2, rung 3 (the revealed cell) and Check; the scroll happens after the highlight is painted and after any redraw; reduced-motion players get no smooth animation (instant), everyone else gets a short smooth scroll or instant (owner may rule; recommended instant, because a smooth scroll fights the pulse of CARD-409).
3. **Both orientations and every zoom,** including Fit (nothing to scroll) and 300%.
4. **No page scroll is caused:** only the stage's scroll position changes (after CARD-403 the page does not need to scroll to see the board).

## Acceptance criteria

* **AC-1** (the pure helper): for a table of (offsets, sizes, bands, target) the result puts the target fully inside the visible box minus the bands, returns the input when it is already inside, and clamps at the scroll limits; an independent computation in the test agrees. (test: new pure cells; plant: ignore the band and the 'under the band' arm reds)
* **AC-2** (rung 1 and 2): at 200% on a 30 x 30, with the hint line far from the viewport, pressing Hint leaves every cell and the clue box of the hinted line inside the visible stage, not covered by a sticky band; on a row hint and on a column hint. (test: new browser cells at 390 x 844, 844 x 390, 1280 x 720; plant: remove the scroll call)
* **AC-3** (rung 3): the revealed cell is inside the visible box and not under a band. (test: new cell)
* **AC-4** (Check): the first wrong row is in view after Check (admin only). (test: new cell in the hint module; public mode has no Check)
* **AC-5** (no movement when already visible): pressing Hint when the target is in view changes neither the stage's nor the page's scroll. (test: new cell; plant: always scroll to centre)
* **AC-6** (only the stage scrolls): `window.scrollY` is unchanged by the press at every viewport. (test: new cell)
* **AC-7** (existing hint behaviour): the ladder, the counter and the one-undo-step rules are unchanged: the existing `tests/test_puzzle_solver_hint.py` cells pass with no node removed. (test: node-id difference)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).

* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)


## Architecture context

FR-044 (the admin puzzle player, TERM-037) and FR-045 (public player, COMP-011) — the public player gets this behaviour by the shared-UI mode, not by its own code. The author reads the AC ids in `requirements.yml` FR-044 and amends exactly the ones whose claim changes (do not guess ids; AC-345..AC-347 are the circling ACs).

## How this reaches the public player

One source of truth (owner direction 2026-11-07; ADR-0041/R3): the change is made ONLY in the admin files (`src/nonogram/admin/static/solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and the admin templates). Nothing in `player/play.js`, `player/player.css` or `player/play.html` is edited or tested by this card: CARD-399 retires them, and production serves `play.js` until the owner deploys the shared-UI mode, so this card reaches production only through the shared-UI rebuild and that deploy (the owner's timing; CARD-394 and CARD-399 are NOT dependencies of this card). What the card owes the public side:

* the shared-UI tree assembled from the changed files passes `tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity` with no edit to the table it holds (the copies stay byte-identical; no override layer, no public-only rule);
* the behaviour is verified ONCE, on the admin page (owner test-budget ruling, 2026-11-07): no duplicate public-mode cell is added; a public-mode cell exists only where the behaviour differs in public mode (for example Check and the error counter do not exist there); CARD-385's existing public-mode sweep and the byte-identity test cover the copy;
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

[Env] forge from /Users/omelnikova/MyProjects/forge_1; orchestrated from the player-phone thread.
[Impl 2026-11-09] 9b05011c + review-1 fixes. revealScroll (solver_state.js) + bringIntoView (solver.js, the stage only, instant: item 2's recommended instant). Rungs 1-2 and Check's row: the line's cells AND its labelled clue box on both axes — a zoomed 30-cell line does not fit sideways, so revealScroll's "box larger than the view" arm puts the line's start (its clue) just past the band and shows the clue and the first cells (AC-2 read that way: every cell is not physically possible at 200% on a phone). Rung 3: the revealed cell on both axes. A redraw that repaints the highlight moves nothing.
[Measure] 30 x 30 at 200%, stage scrolled to the far corner: at 844 x 390 and 1440 x 900 the hint line's cells come in across the line, its clue box is in the stage, the revealed cell is fully in view clear of the bands, Check's row comes in; window.scrollY unchanged throughout. At 390 x 844 the 30 x 30 keeps no band at 200% (owner ruling 2026-11-09), so the cell moved to 1440 x 900 where both bands stick.
[Tests] New TestSolverZoom_HintComesIntoView: the pure cell (7 cases incl. the upper clamp) and 844 x 390 / 1440 x 900. Plants run: revealScroll ignoring the band (pure cell red), no bringIntoView in setLadderLine (both browser cells red), rowBand = 0 and colBand = 0 in bringIntoView (1440 x 900 red). Node ids +3 (all in the browser registry); none removed; tests/test_puzzle_solver_hint.py untouched (AC-7).
[Review 1/3] Score: 7.0 — F-001 (no band exercised) fixed by the 1440 x 900 viewport; F-002 (clue box) fixed as above; F-003 this note; F-004 the axis-specific assertion; F-005 an upper-clamp case; F-006 (row band read from the first row clue, assumed left) holds while the mirror is inert (CARD-405), noted; F-007 the function moved above cellUnder's comment. Report meta/review/20261109T190847Z-CARD-408-cycle1.yml.
