# CARD-405: On phones the row clues stay on the left and the column clues on top — the right-hand mirror is retired, because the clues are pinned

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- Retiring a layout the owner asked for (CARD-193) is mostly deleting; the cost is the many cells that pin the mirror and the question what happens to the doubled gutters of CARD-212 (owner Q8). If the owner rules that the doubled gutters go too, that is a second card, not part of this one. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 4: "Mobile mode - clues - to put them to the right and bottom was the idea that it's not convenient to go without them on screen if the puzzle needs scrolling ... For now I think that sticky clues and crosshair solve that problem ... so we can have clues always at left and top (mobile mode) and check that clues are sticky."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-404
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_fifth_rule.py, tests/test_puzzle_solver_zoom.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-193 mirrors the row clues to the right-hand side for boards wider than 15 columns at or below 820 px (`isMirrored()` = `payload.width > BIG_SIDE && mirrorQuery.matches`), so that a player swiped to the right still sees clues; CARD-212 doubled the gutters (left+right, top+bottom) on big boards. The owner now says sticky clues plus the crosshair solve the visibility problem and the clues should always be at left and top. CARD-404 makes the stickiness hold at every zoom (it is the real dependency: before it, the mirror is the only thing that keeps clues visible on a phone at high zoom).

`solver.js` records that on a mirrored phone 'the band is 76% of the stage' so stickiness is refused there; without the mirror and with capped numerals (CARD-404) the left band is narrow enough to stick.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Retire the phone mirror:** `isMirrored()` is false at every width; the right-hand row gutter is not drawn on a phone for a single-gutter board. `mirrorQuery` and the 820 px redraw crossing are removed or left inert by decision of the author, reported in the card.
2. **The doubled gutters (CARD-212)** are NOT removed by this card. What the card measures and reports for the owner: on the owner's class of board at 390 x 844 and at 1280 x 720, which layouts still draw a duplicate gutter, what it costs in cell size, and whether the clues are in view with stickiness alone (owner Q8: recommended to retire the duplicates as a separate card once this one shows the numbers).
3. **Stickiness verified on a phone:** at 390 x 844, 100% and 200%, scrolled to every corner of a 30 x 30, the clues of the corner cell are visible (the cells AC-5 of CARD-404 extended in this card's file set).
4. **Docs/comments:** the CARD-193 mirror comments in `solver.js`, `admin.css` and the template header are updated; `puzzle_solve.html`'s CARD-212 paragraph keeps its truth.

## Acceptance criteria

* **AC-1** (clues left and top on a phone): at 390 x 844 a 30 x 30 and a 20 x 20 draw the row clues in the left gutter only (no `.is-right` box) for a single-gutter board, and the column clues on top. (test: re-pointed `tests/test_puzzle_solver_phone.py` mirror cells; the old 'mirrored right gutter' claim retired with the owner finding's date)
* **AC-2** (sticky on a phone): scrolled to each corner at 100% and 200%, the corner cell's row clue and column clue are both inside the stage and painted above the cells. (test: new cells; plant: remove `.is-keeping-rows` and the cell reds)
* **AC-3** (the fit is no worse): the 390 px fit pins (`TestSolverPhone_BoardFitsThePhoneWidth`, the 25-wide ceiling) are re-measured because the right gutter's width is returned to the cells; each changed number is attributed to the retired mirror and the card lists the old and new cell sizes for 15, 20, 25, 30 wide. (test: existing cells, numbers re-derived; evidence: Worktree note)
* **AC-4** (desktop unchanged): at 1280 x 720 and 1440 x 900 every layout cell passes unchanged. (test: existing cells)
* **AC-5** (nothing is lost in circles/hints): circles still paint in every gutter that exists; hint line and crosshair still tint the boxes of the single gutter. (test: `TestSolverClues_CirclesPaintBothGutters` etc. unchanged where the gutters still exist)

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

(none yet)
