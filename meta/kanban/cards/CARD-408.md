# CARD-408: Hint and Check bring what they point at into view — the hinted row or column, or the filled cell — at any zoom and in both orientations

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- One behaviour (scroll the stage so the target is visible and not under a sticky band), but it must hold across zoom, orientation, doubled and plain gutters and the three ladder rungs plus Check; the arithmetic of 'not under the sticky band' is the part that takes the cycles. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 7, first bullet (marked essential): "Scroll the board so the hinted row or column, or the filled cell, is in view, at any zoom and in both orientations. This is the essential one."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-403, CARD-404
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_zoom.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Real dependencies: CARD-403 (it fixes which element scrolls; a scroll-into-view written against today's nested scroller would move the page as well) and CARD-404 (the sticky bands are what the target must not hide under; their depth changes with it). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**Evidence:** `solver.js` paints `.is-hint-line` on a line's cells and clue boxes (`setLadderLine` / `paintLadderLine`) and `.is-hinted` on a revealed cell, and never moves any scroll position: a repo search for `scrollIntoView|scrollTo|scrollLeft|scrollTop` finds only the zoom anchoring (`applyZoom`) and no hint path. On a zoomed board the highlighted line can be entirely off-screen, so the press looks dead.

For a ROW the target is its vertical position (the row must be below the sticky column band and inside the stage; horizontally the row clue is pinned, the cells are the content); for a COLUMN the horizontal one; for a revealed CELL both. The sticky bands cover the first `band` pixels of the scroll box, so naive `scrollIntoView` leaves the target UNDER a band. Check's row (CARD-269) is the same problem and is included, because it is Hint's neighbour and the same helper serves both.

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
* every new behavioural cell runs on the admin page AND on the public-mode page (`mode: "public"`, no solution, CARD-385's sweep in `tests/test_player_public_mode.py`), or the card says in one line why the behaviour does not exist in public mode (for example Check and the error counter);
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

(none yet)
