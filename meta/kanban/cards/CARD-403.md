# CARD-403: The board's scroll box ends above the fold at any toolbar height — no scroll inside a scroll — and the jump while scrolling is reproduced and fixed

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 3c (1d)
<!-- The first half is a known mechanism (a one-row estimate in `--player-chrome-h`); the second half (the jump) is not reproduced yet and may be CARD-277's family. If the jump does not reproduce in two attempts the card records the attempt and closes that half as 'not reproduced' with a test that would catch it; it does not guess a cause. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 6: "Scrolling inside a scroll. Once zoomed, the board becomes its own scroll box, 616 px tall, starting 317 px down a 844 px screen. Its bottom edge and sideways scrollbar sit off-screen, so you scroll the page and the board separately." and "Scrolling makes the whole puzzle to jump."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The claim 'the stage's cap follows the real toolbar' already exists for play.js (`tests/test_public_player_zoom.py::TestPublicZoom_TheStageEndsAboveTheFold`, retiring with CARD-399); this card makes it true for the admin file and so gives CARD-399's audit a named survivor. No dependency on CARD-401: this is independent of how many rows the toolbar has, which is the point. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**Mechanism (verified in the code):** `.player-stage { max-height: calc(100svh - var(--player-chrome-h)) ; overflow: auto }` and `--player-chrome-h` is `topbar + space-6 + space-12 + control-h + space-4 + space-8`: it allows ONE toolbar row. On a phone the toolbar wraps to three or four rows (and the explain line, the probe bar and the counters add more), so the stage's box starts 317 px down an 844 px screen and is still 616 px tall: its bottom and its horizontal scrollbar are below the fold, and the page scrolls as well as the stage. The public player already fixed exactly this for itself (cap = measured distance from the top of the page); the admin file never did. The fit of the cell (`min(width term, height term)`) uses the same one-row constant, so the 100% cell size is also computed against a taller stage than the player really has.

**The jump:** not reproducible by reading. Candidates, to be tried in this order: (1) the page scroll chaining into the stage (or the reverse) when the stage reaches its end; (2) `redraw()` on the `resize` event a phone fires when the URL bar collapses mid-scroll (`window.addEventListener("resize", ...)` redraws the whole table from history, which replaces the stage's content and can reset scroll); (3) sticky bands switching on/off (`keepCluesInView` toggles `is-keeping-*` after a zoom) changing layout under the finger; (4) CARD-277's unexplained drag-marks-everything at 200% (read its Worktree notes; it is `ready`, not merged). The author reproduces on a real viewport emulation with scripted scroll and a resize event and records the result.

## What to implement

1. **Measured cap.** The stage's `max-height` and the cell's height term follow the stage's real distance from the top of the page, whatever the chrome above it is (rows of toolbar, the explain line, the probe bar), with the `--space-4` air below. Mechanism is the author's (a CSS-only form using the toolbar's own height if one exists, or a `ResizeObserver` writing one custom property; no layout thrash and no oscillation: the same discipline `keepCluesInView` states for its measurement).
2. **At 100% on a board that fits, nothing changes** (CARD-195 'the fitted size is what 100% means'): the 28 px at 1440 x 900 cell pin stands.
3. **One scroller.** At every viewport in the list the stage's bottom edge and its horizontal scrollbar are inside the window at page scroll 0, and the page itself does not need to scroll to reach the board's bottom edge (the usage text below the board may need page scroll; the board does not).
4. **The jump:** reproduce, or record the failed attempt, and add the cell that would catch it (page scroll position and stage scroll position unchanged by a resize event that changes nothing; the table element's identity stable across a scroll).

## Acceptance criteria

* **AC-1** (the stage ends above the fold): at every viewport of a sweep (width 320..1440 step 20 x height 320..900 step 30, the shape of the retiring play.js cell) and for a 30 x 30 board at 100% and at 200%, the stage's bottom is at or above `innerHeight - air`. (test: new cell in `tests/test_puzzle_solver_zoom.py`; plant: restore the one-row constant and the 390 x 844 arm reds)
* **AC-2** (100% unchanged where it fit): the 15 x 15 at 1440 x 900 still draws 28 px cells at 100% and 56 px at 200%. (test: `TestSolverZoom_HundredPercentIsTheFittedSize` unchanged)
* **AC-3** (no oscillation): drawing the page twice, and scrolling the page, leave the stage's height and `--player-cell` unchanged; a burst of 8 resize events with unchanged size redraws once (the existing `..._a_burst_of_resize_events_redraws_once` unchanged). (test: new + existing)
* **AC-4** (the horizontal scrollbar is reachable): at 390 x 844 and 844 x 390, zoomed to 200%, the stage's scrollbar thumb and its bottom edge are in the window. (test: new cell)
* **AC-5** (the jump): either a cell reproduces it red on the merge-base and green after the fix, or Worktree notes record two reproduction attempts with the exact script and the card closes that half as 'not reproduced', with the guard cell above kept. (test: new cell; evidence: Worktree note)
* **AC-6** (stickiness unaffected): `TestSolverClues_StayInViewOnAPlainBigBoard` and `TestSolverZoom_CluesStayInViewWhileZoomed` keep their verdicts; any measured overflow number they hold (91, 211, 104/111) that changes because the stage is now shorter is re-measured and the change attributed to this card's cap, never relaxed. (test: those cells, numbers re-derived)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The jump half does not 'fix' by suppressing an event (no `preventDefault` on scroll, no `overscroll-behavior` guess) without the reproduction that shows it is the cause.
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)


## Architecture context

FR-044 (the admin puzzle player, TERM-037) and FR-045 (public player, COMP-011) — the public player gets this behaviour by the shared-UI mode, not by its own code. The author reads the AC ids in `requirements.yml` FR-044 and amends exactly the ones whose claim changes (do not guess ids; AC-345..AC-347 are the circling ACs). Related: CARD-277 (zoom drag marked every cell, ready, unreproduced).

## How this reaches the public player

One source of truth (owner direction 2026-11-07; ADR-0041/R3): the change is made ONLY in the admin files (`src/nonogram/admin/static/solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and the admin templates). Nothing in `player/play.js`, `player/player.css` or `player/play.html` is edited or tested by this card: CARD-399 retires them, and production serves `play.js` until the owner deploys the shared-UI mode, so this card reaches production only through the shared-UI rebuild and that deploy (the owner's timing; CARD-394 and CARD-399 are NOT dependencies of this card). What the card owes the public side:

* the shared-UI tree assembled from the changed files passes `tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity` with no edit to the table it holds (the copies stay byte-identical; no override layer, no public-only rule);
* every new behavioural cell runs on the admin page AND on the public-mode page (`mode: "public"`, no solution, CARD-385's sweep in `tests/test_player_public_mode.py`), or the card says in one line why the behaviour does not exist in public mode (for example Check and the error counter);
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

(none yet)
