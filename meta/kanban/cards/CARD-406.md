# CARD-406: A Fit zoom step below 100% shows the whole board — the zoom model learns a floor that is the board's own fit

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 4c (1.5d)
<!-- Over the 3c target on purpose: the zoom model is a pure module with many pinned arithmetic cells (`stepZoom`, `pinchZoom`, `anchoredScroll`, the 100..300 range in `solver_state.js`) and a UI of its own (button, readout, pinch below 100%); the owner lifts the cap only by ruling, so if the pure model alone takes a cycle the UI is split into a follow-up card. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, items 2, 5 and 9: "A 'Fit' zoom step below 100% that shows the whole board." (item 2); "With Fit, the whole 29 rows would fit at roughly 10 px cells." (item 5); the usage line "Zoom: - / + or Fit to see the whole puzzle." (item 9).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-403, CARD-404
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Depends on CARD-403 (the stage height: Fit is computed against it) and CARD-404 (the clue band at 10 px cells is a capped, constant strip; without it Fit's cell size is dominated by an uncapped numeral floor). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Today `ZOOM_MIN = 100`, `ZOOM_MAX = 300`, `ZOOM_STEP = 25` in `solver_state.js` and 100% means 'the fitted size' clamped by `--player-cell-min` (14 px desktop, 0 under 820 px) and `--player-cell-max` (28 px). So 100% is already the best fit on a phone in portrait; on a landscape phone (844 x 390, over the 820 breakpoint) or a short window the 14 px floor binds and the board does not fit. The owner wants a step below 100% that shows the whole board (roughly 10 px cells for 29 rows at 390 px height).

Two constraints that are owner rulings and must not be contradicted silently: (1) 2026-11-06 'I like your min-max rule as a principle, but cells smaller by default' (CARD-384): a floor-and-cap rule stays; Fit is an explicit user action that goes below the floor, it does not remove the floor from 100%. (2) CARD-384's derived floor exists because the circle rings overlap below a cell size on a 30 x 30 at 390 px (it measured a ring gap of -0.5 px at 14 px): at Fit's ~10 px cells the rings overlap unless suppressed or reshaped (owner Q9).

**[OWNER RULING 2026-11-07, on the drafter's question]** Fit applies to puzzles that DO NOT FIT at 100% zoom on compact screens (phones) only; desktop keeps opening at 100%. Fit is the bottom step of the minus button AND there is a Fit button when Fit < 100%.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Pure model first** (`solver_state.js`): the zoom range gains a Fit floor that is not a constant: Fit is `fitZoom(board, stage)` = the percent of the 100% cell size at which the whole board (both clue bands included) fits the stage's box; when the board already fits at 100%, Fit equals 100% and the step does not exist (Zoom out stays disabled). `stepZoom`, `clampZoom`, `pinchZoom` and `anchoredScroll` take the floor as an argument; the old 100..300 behaviour is the floor = 100 case and its existing pure cells stay byte-for-byte (`TestZoomArithmetic_PureFunctions`).
2. **The control:** the zoom group shows 'Fit' as the readout when the zoom is at the floor (and a 'Fit' button that jumps to it; owner Q10: a button or just the minus step). Zoom out steps down 100 -> Fit; pinch is continuous down to Fit.
3. **No layout surprise:** Fit is a view setting like zoom (never saved, never in history, resets on load); the ring and numeral rules at ~10 px cells follow owner Q9.
4. **Scroll anchoring** keeps the viewport centre over the same board point while going into and out of Fit (the CARD-195 formula, extended to the floor).

## Acceptance criteria

* **AC-1** (the pure floor): `fitZoom` returns 100 for a board that fits at 100% and the strictly smaller percent that fits the stage otherwise; for a table of boards and stages it equals an independent computation from the cell, band and stage sizes. (test: new pure cells next to `TestZoomArithmetic_PureFunctions`; plant: use the viewport instead of the stage and it reds)
* **AC-2** (the old range is untouched): every existing arithmetic cell passes unchanged (`stepZoom`, `pinchZoom`, `anchoredScroll` at floor = 100). (test: existing cells, node ids unchanged)
* **AC-3** (Fit shows the whole board): at 844 x 390 and 390 x 844 a 30 x 29 board at Fit has no scroll on either axis and the whole board, clue strips included, is inside the stage; one more percent of zoom in and the board scrolls. (test: new browser cells; plant: off-by-one in the floor)
* **AC-4** (the control): at Fit the readout says 'Fit', Zoom out is aria-disabled, Zoom in goes to 100%; at 100% Zoom out goes to Fit when Fit < 100 and is disabled when Fit = 100. (test: new cells; the zoom button cells of CARD-195 re-pointed only where the disabled-at-100 claim is changed by an owner finding)
* **AC-5** (pinch below 100): a two-finger pinch out from 100% reaches Fit and stops there; the single-finger drag and Region rules of CARD-195 (e) hold. (test: new pinch cell)
* **AC-6** (not saved, no request): Fit is not in `serializeState`, not in localStorage, sends nothing. (test: re-pointed `TestSolverZoom_IsNotSavedAndSendsNothing` extended)
* **AC-7** (tap targets and circles at Fit): the zoom buttons stay 24 px or more (44 px in compact mode); the ring/numeral outcome at Fit is the owner's ruling in Q9, asserted by a cell. (test: new cell)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** 100% is still 'the fitted size' (CARD-195): Fit never changes what 100% means.
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
