# CARD-402: Landscape phones get the toolbar as a vertical icon column at the side — the board gets nearly the full height

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- One layout mode (a column beside the board) with the hardest part being what to do with the two bars that are currently toolbar children (probe bar, counters) and the sticky bands; kept to one viewport class (short screens) so it stays one day. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/402-landscape-tool-column
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-402
**Source:** owner player findings 2026-11-07, item 5: "Toolbar as a vertical icon column at the side. Brush, Region, Undo, Redo, Reset, Hint and zoom stack in one strip about 52 px wide. They fit in 375 px of height, and on the left they're under your thumb." ... "The board then gets nearly the full height, about 20 rows at today's cell size instead of 5."
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-401, CARD-403
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_percent.py, tests/test_puzzle_solver_maybe.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The real dependencies: CARD-401 (the icons and the compact switch are what fit the strip into 52 px) and CARD-403 (the stage's height must be measured from the real layout: with the toolbar beside the board, 'what stands above the board' is a different quantity from today's `--player-chrome-h`). -->
**Review score:** —
**Started:** 2026-11-10T07:08Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

At 844 x 390 the toolbar still wraps above the board and the board is about five rows tall. The owner's design: in landscape the tools become a vertical icon strip about 52 px wide on the left (thumb side), the board takes the freed height. The twelve controls (Brush, Region, Undo, Redo, Reset, Hint, Check on admin, Zoom -, readout, Zoom +, Fit once CARD-406 lands) must fit in the 390 px viewport height with room for the browser chrome (the owner's measure: 375 px).

Things in today's markup that are NOT part of the owner's list and need a home: the counters (Errors, Hints, Progress), the Probe bar (a toolbar child with `flex-basis: 100%`), the solved banner (shares the `.player-slot` with the tools), the reset confirmation dialog (inside `.player-history`), the explain line (title row) and the usage text. The owner's earlier ruling that the Hint/Probe bars are NOT children of `.player-toolbar` belongs to the play.js family (`tests/test_public_player_hint.py::TOOLBAR_BUTTONS` pins that button set); the admin template DOES nest `.player-probe` inside `.player-toolbar`, and the admin cells that pin it are `tests/test_puzzle_solver_probe.py::TestSolverProbe_TheBarCostsTheBoardNoGround` (board position) and `tests/test_puzzle_solver_hint.py::TestSolverHint_PlacesTheButtonAndTheCounter`. The author reads both and states in Worktree notes how the admin set is pinned (by those cells, by `data-player-*` attribute) so CARD-399's audit has a named survivor.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Landscape/short mode:** under the same compact condition as CARD-401 AND `orientation: landscape` (or the short-height arm alone: the owner Q5 decides whether a short desktop window counts), `.player-toolbar` becomes a column, about 52 px wide, on the LEFT (owner Q6: thumb side; recommended left, with no right-hand alternative until someone asks), to the left of the stage, the stage taking the rest of the width and the full available height.
2. **Everything has a home:** the counters, the solved banner, the probe bar and the reset confirmation are placed by the author and reported with a screenshot at 844 x 390 for each state (idle, probe open, solved, reset confirmation, hint rung 2). Recommended: counters in a compact line above the stage or in the strip's foot as numbers only; the reset confirmation and the probe bar as popovers anchored to the strip; the solved banner replaces the counters line. These are recommendations, not decisions.
3. **The stage uses the freed height** with no nested vertical scroll at 100% on a board that fits (CARD-403's measured cap is what makes this true).
4. **A strip taller than the viewport scrolls itself** (never clips a control) so a 320 px-tall window still reaches every button.

## Acceptance criteria

* **AC-1** (the strip): at 844 x 390, 852 x 393 and 874 x 402 the toolbar is a single column at most 56 px wide at the left edge of the content, every control inside the viewport without page scroll, each at least 44 px tall (measured). (test: new geometry cells; plant: put the strip on the right / let it exceed 56 px)
* **AC-2** (the board gets the height): at 844 x 390 a 30 x 29 board shows at least 18 rows at 100% before scrolling (the owner's target is about 20 at today's cell size; the author measures the cell size and writes the number). (test: new cell; evidence: Worktree note)
* **AC-3** (every state has a home): idle, probe open, solved, reset confirmation and hint rung 2 each leave every control reachable and the board's box unchanged from the idle state (the board does not move when a bar appears, the CARD-268 budget claim kept). (test: re-pointed `TestSolverProbe_TheBarCostsTheBoardNoGround` at 844 x 390; new state cells)
* **AC-4** (portrait and desktop unchanged): at 390 x 844, 1280 x 720 and 1440 x 900 the layout equals CARD-401's. (test: the geometry cells of CARD-401 and the percent/maybe cells unchanged)
* **AC-5** (no clipped control at the smallest window): at 568 x 320 the strip scrolls and every button can be reached by scrolling it. (test: new cell; plant: `overflow: hidden`)
* **AC-6** (public mode): the same strip on the public-mode page without Check, the errors counter or progress. (test: public-mode cell)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** Pinch/drag gestures on the board are unaffected by the strip (it takes no touch-action from the board; CARD-195's pinch rules hold).
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
