# CARD-407: A big puzzle opens at Fit — the player sees what they are solving before they zoom in

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- One decision (what counts as big and what the opening zoom is) on top of CARD-406's model; small, but it changes the first thing every owner and player sees, so it carries the owner's go in the Source. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 2: "Big puzzles would open at Fit, so the player sees what they're solving." 'Big' is not defined by the owner (owner Q11).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-406
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_page.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-195 rule 6: zoom is never saved and starts at 100% on every load. CARD-406 adds the Fit floor. This card changes the INITIAL zoom for big puzzles: instead of 100% they open at Fit. 'Big' candidates: the board does not fit the stage at 100% (the objective rule, recommended: it reuses `fitZoom < 100`); or a side past `BIG_SIDE = 15` (the existing constant for the clue doubling); or a cell-count threshold. Owner Q11 chooses; Q12: whether the same applies on desktop (a 30 x 30 at 1280 x 720 scrolls 91 px at 100%; Fit would shrink it to nearly the 14 px floor-less size) or only compact screens.

**[OWNER RULING 2026-11-07, on the drafter's question]** A 'big' puzzle is one whose whole board does not fit on screen at 100% zoom (objective: reuses the Fit computation); applies on compact screens (phones) only at first; desktop keeps opening at 100%.

## What to implement

1. **The opening zoom** is `fitZoom` when the chosen 'big' rule holds, otherwise 100% (unchanged). A reload re-applies the rule (nothing is saved).
2. **A resume does not override the player:** zoom was never part of the save, so a resumed board opens at the rule's zoom, not at the last one (state this in the page text where zoom is described).
3. **The first draw is not wasted:** the board is drawn once at the opening zoom (no 100% flash then a redraw), measured by counting `drawBoard` calls the way `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` does.

## Acceptance criteria

* **AC-1** (opens at Fit): a puzzle the rule calls big opens with the readout 'Fit' and the whole board visible; one the rule calls small opens at 100%. (test: new browser cells with the boundary neighbour on each side; plant: invert the rule)
* **AC-2** (not saved): a reload after zooming to 200% reopens at the rule's zoom. (test: re-pointed `TestSolverZoom_IsNotSavedAndSendsNothing`)
* **AC-3** (one draw): the number of `drawBoard` calls to first paint is unchanged from the merge-base. (test: the ladder-count cell, unchanged expectations)
* **AC-4** (existing opens): every existing cell that assumes 'opens at 100%' on a board the rule now calls big is changed ONLY with the owner finding named as the reason; the rest pass unchanged. (test: node-id difference with the list)

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
