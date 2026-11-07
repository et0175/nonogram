# CARD-409: A hint is seen — a stronger highlight with a short pulse, the hint text right by the board, and 'the highlighted row (13)' wording

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- Three small changes with one hard constraint: the text moves out of the title row (where a 2026-10-30 owner decision put it because it costs no vertical space) to the board, without moving the board; the measurement of that trade is the work. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 7, bullets 2-4: "Make the highlight stronger. Use a clearly visible tint on the line and its clue, and maybe a short pulse when it appears."; "Show the hint text right by the board: just above it, or as a small strip over its top edge that disappears on the next tap."; "Word it as 'the highlighted row (13)' so the highlight does the pointing and the number is a backup."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-408
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, player/assemble.py, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_page.py, tests/test_player_shared_ui_site.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. It edits `player/assemble.py` and `tests/test_player_shared_ui_site.py` only for the usage-sentence hook (`SHARED_UI_HINT_CLAUSE` / `SHARED_UI_HINT_REPLACEMENT`, the CARD-386 F-2 ruling 'in the line at the top of the page'), which becomes false when the line moves; CARD-394 edits the same two files (serialize with it in whichever order it merges; neither depends on the other). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Three owner decisions are being CHANGED here, each recorded so no test is silently weakened:
* 2026-10-30 (CARD-269): the explain line lives in the title row (`#puzzle-player-explain`, `.page-head`) because it costs zero vertical space. The owner now wants it by the board. The 4.187 px of vertical slack at 1280 x 720 that decision measured has not grown; so a line that takes layout space moves the board (the card-wide 'board does not move' budget of CARD-268/269). An overlay strip over the board's edge costs no layout space.
* The tint: `.is-hint-line` uses `--color-accent-tint`, measured against the crosshair and the probe marker (CARD-267/268 hold dE76 floors between them); a stronger tint must keep those separations (the probe ring's floor is 20 dE76 against every ground, including the hint-line ground).
* CARD-386 F-2 (owner ruling 2026-11-07): the public page's usage sentence says answers are written 'in the line at the top of the page'. After this card that is false; the sentence and the assembler's hook that enforces it (refused unless found exactly once) change with it.

**[OWNER RULING 2026-11-07, on the drafter's question]** The hint text appears as an OVERLAY STRIP at the stage's BOTTOM edge (never covering the sticky column clues, costing no vertical space) that disappears on the next tap; this replaces the owner's 'just above or over its top edge' wording because a top strip would cover the pinned column clues.

## What to implement

1. **Stronger highlight:** raise the `.is-hint-line` tint on the line's cells and its clue boxes, and add a short pulse on appearance (`prefers-reduced-motion` gets no animation; the existing `player-hint-line-in` keyframes are the base). Re-measure the separations: hint line vs crosshair vs probe ring vs Maybe cell ground, each with its floor (the CARD-267/268/269 distinguishability cells keep their floors; a floor is raised, never lowered).
2. **The text by the board.** Owner's two options: a line just above the board (reserves height; moves the board on desktop: owner Q13) or a strip over the board's edge that disappears on the next tap (no layout cost). Recommended: a strip over the stage's BOTTOM edge, not the top, so it never covers the sticky column clues the hint is pointing at; the owner may prefer the top edge, in which case the strip sits below the sticky band, not over it. The strip carries the same sentence as the live region (aria-hidden as today, the live region is unchanged and still says everything) and is dismissed by the next pointer-down anywhere, by Escape and by the next press. It does not intercept the board's pointer events beyond its own box.
3. **Wording:** 'the highlighted row (13)' / 'the highlighted column (7)' for rung 1 and rung 2; the number stays as a backup. Rung 3's 'row r, column c is black' sentence is unchanged unless the owner rules otherwise. `ladderPointText` / `ladderExplainText` in `solver_state.js` and the sentences that tests name are changed together.
4. **The title-row line retires** (`#puzzle-player-explain` in `.page-head`): the markup, the `admin.css` 4.187 px arithmetic comment and the measured 'zero vertical space' cells are replaced by this card's own measurements; the hidden live region (`#puzzle-player-announce`) is untouched.
5. **The usage sentences** that say where the answer appears (admin template paragraph and the assembler's replacement) are corrected to 'above the board' / 'over the board' truthfully; CARD-413 replaces the paragraph wholesale later.

## Acceptance criteria

* **AC-1** (the highlight is stronger and apart): the line's tint differs from plain paper by at least the new floor and from the crosshair, the probe ring and the Maybe ground by at least their existing floors, measured in dE76 from computed colours at 1280 x 720 and 390 x 844. (test: the existing distinguishability cells with the hint-line floor raised and the others unchanged; plant: revert the tint)
* **AC-2** (the pulse is real and optional): on press, the line's cells have a running animation of the pulse for a bounded time; under `prefers-reduced-motion: reduce` there is none. (test: `getAnimations()` cells; plant: delete the keyframes)
* **AC-3** (the text is by the board): after each rung and after Check the visible sentence is inside the stage's box (or directly above it, per Q13), readable (not clipped, 12 px or more), at 390 x 844, 844 x 390 and 1280 x 720; it disappears on the next pointer-down and on Escape; the live region keeps the same sentence. (test: new rectangle cells; plant: leave it in the title row)
* **AC-4** (the board does not move): the board's top and the toolbar's box are identical before the press, with the sentence showing, and after it is dismissed. (test: new cell using the CARD-268 'no ground' idiom)
* **AC-5** (the wording): rung 1 and rung 2 say 'the highlighted row (N)' or 'the highlighted column (N)' with N the 1-based number; the old 'Look at row N' wording is gone. (test: re-pointed `ladderPointText` / `ladderExplainText` cells; the changed claim is named with the finding)
* **AC-6** (the public sentence): the assembled public page's usage text no longer says 'at the top of the page'; the assembler still refuses a fragment where its clause is not found exactly once. (test: `tests/test_player_shared_ui_site.py` cell for the new clause, one plant for the old wording at 390 and 1280)
* **AC-7** (reduced hint behaviour): the ladder, counter, one-undo-step, and 'rungs 1-2 record nothing' rules are unchanged. (test: existing cells, node-id difference)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The live region keeps carrying every sentence in full (screen-reader path unchanged); the visible strip is the addition.
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)
* CARD-269 rung semantics (check: the existing ladder cells)

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
