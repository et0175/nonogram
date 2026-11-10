# CARD-412: A wrong guess becomes progress — after it, the player is offered to mark the guessed cell the other way

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- A new interaction on top of the probe transaction. The logic is small; the care is in WHEN it is valid (the guess is a single cell; later probe marks are consequences, not further guesses) and in the undo story (the mark is one normal stroke). -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/412-wrong-guess-offer
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-412
**Source:** owner player findings 2026-11-07, item 8, first bullet: "Turn a contradiction into progress. After pressing 'Contradiction', say something like 'Your first guess was wrong, so that cell must be white. Mark it?'". Whether it marks automatically or asks is the owner's wording 'Mark it?'; owner Q15 confirms asking.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-411
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. -->
**Review score:** —
**Started:** 2026-11-10T03:48Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Logic: a probe is a hypothesis; Wrong guess means the hypothesis led to a contradiction, so in a uniquely solvable puzzle the hypothesis is false. If the hypothesis was ONE cell set to dark (white), the cell must be white (dark). The offer is only honest when the probe was a single-cell hypothesis followed by consequences the player deduced; a probe that opened with a multi-cell stroke (a drag) or that holds several independent guesses does not identify 'the first guess'. The player can still mislead themselves with an unsound later mark, so the offer asks ('Mark it?') and does not mark, and the mark is an ordinary stroke (undoable).

`abandonProbe` (CARD-268 rule 4) undoes to the checkpoint and closes the probe; the probe's first stroke (`probeCells(history, probe)` gives the members) is what the offer is computed from BEFORE the abandon runs.

**[OWNER RULING 2026-11-07, on the drafter's question]** The offer ASKS and never auto-marks: 'Your first guess was wrong, so that cell must be white. Mark it?' with Yes/No; it appears only when the probe's first stroke was a single dark or white cell (later marks could be unsound guesses). The button is named '✗ Wrong guess' (CARD-411).

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Pure rule** `probeVerdict(history, probe)` in `solver_state.js`: returns `{row, col, state}` (the cell to offer, in the OPPOSITE state of the first probe stroke) only when the first probe stroke marked exactly one cell as FILLED or EMPTY (not MAYBE, not a drag, not a hint stroke); otherwise null (no offer).
2. **The offer:** after Wrong guess, a one-line prompt by the board (in the same strip as CARD-409's hint text, so there is one place that talks to the player) 'Your first guess was wrong, so row R, column C must be white/black. Mark it?' with 'Mark it' and 'No thanks'; also written to the live region. Dismissed by the next board tap, Escape or the buttons; 'Mark it' records one normal stroke (one undo step, counts toward errors if wrong exactly as any stroke) and highlights the cell briefly.
3. **No offer** when the probe was empty, the first stroke was a drag or Maybe, the board is solved, or after Keep.
4. **Public mode:** works (it reads only the history). No solution is consulted to decide the offer; whether the offered mark is right is not checked (that is the player's deduction).

## Acceptance criteria

* **AC-1** (the pure rule): for a table of probes (single dark cell, single white cell, drag, Maybe, hint stroke, empty, a probe shrunk by undo past the checkpoint) the verdict is the opposite state of the first stroke's cell for the first two only, and null for every other; an independent computation agrees. (test: new pure cells; plant: offer for a drag)
* **AC-2** (the offer appears and is honest): after Wrong guess on a single-cell probe the prompt names the cell by 1-based row and column and the opposite colour, in the strip by the board and in the live region. (test: new browser cells; plant: name the wrong colour)
* **AC-3** (Mark it is one normal stroke): pressing it paints the cell, one Undo takes it back, errors count it like any stroke. (test: new cells)
* **AC-4** (No thanks changes nothing): the board equals the checkpoint board; the history has only the abandoned strokes' undos. (test: new cell)
* **AC-5** (no offer where it would mislead): none after Keep, none for an empty probe, none when the first stroke is not a single dark/white cell. (test: new cells)
* **AC-6** (probe rules unchanged): CARD-268's rule cells and the save rules pass with no node removed. (test: node-id difference)
* **AC-7** (the board does not move): the offer appears and disappears without moving the board. (test: new geometry cell, the CARD-409 idiom)

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
[Impl 2026-11-10] Commit 5ed14d4a. probeVerdict + markStroke in solver_state.js; the offer is #puzzle-player-offer, a second element in the hint strip's place and look (.player-explain), not the aria-hidden explain line itself, because it holds two buttons and must take the pointer; its sentence is written to the live region too. placeExplain places it clear of the named cell (.is-offered joins its targets). Closed by the next pointer-down outside it, Escape, Mark it / No thanks, or any recorded change (commit()); not offered on a solved board.
[Tests] Net node ids +2 (registered in ADDED_SINCE_BEFORE): TestSolverProbe_StateIsPureAndStatesAreFour::test_the_wrong_guess_verdict_matches_its_table (AC-1; seven cases, an independent expectation from the op list) and TestSolverProbe_AWrongGuessOffersTheOtherColour::test_the_offer_names_the_other_colour_and_marks_it_once (AC-2..AC-5, AC-7). AC-6 by the unchanged probe rule cells. The card's control: the colour swapped -> the browser cell red; also a drag offered -> both red. Screenshot ~/Documents/nonogram-reviews/CARD-412/offer-390x844.png.
[Tests] Player set before review on 5ed14d4a: 1393 passed, 3 red, all test_player_base_css (the page gained the offer's two buttons): the reviewer-sample count 22 -> 24 with the reason and FROZEN re-recorded (verified against the real bootstrap) in the next commit; the file re-run green.
[Review 1/3] Score: 7.5 — fail. F-301: the public census now reads data-player-offer and step_offer drives both buttons in public mode. F-302, measured (15x15 and 30x30 at 390x844, 844x390, 1280x720, 1440x900): the offer inside the stage at every size, never over the named cell, the cell in view, no horizontal scroll; the page never scrolls (window.scrollY 0, stage top fixed); the board's top is unchanged except at 844x390, where the STAGE scrolls the named cell clear of the strip by design (CARD-409's lift; stage scrollTop 107 -> 138). Strip height 56 px desktop, 62 landscape, 108 at 390 (wraps). F-303: Hint/Check close the offer (one strip at a time); a redraw/resize restores the outline and re-places it. F-304: Escape, a press outside and a keyboard Undo asserted to close it (plants red). F-305: no offer when the guess recoloured a mark the player had made the other way (table row added). F-306: focus to Probe after either button. Report meta/review/20261110T041346Z-CARD-412-cycle1.yml.
[Review 2/3] Score: 8.5 — fail on two Important findings. F-401 (focus still dropped to <body>: handOn tested <body> while the hidden button still held focus): fixed — Mark it / No thanks focus Probe directly; asserted in the offer cell (plant: removed -> red). F-402 (the offer covered the named cell in the last rows: 844x390 rows 11-13 of 15 / 26-28 of 30 with the stage at its last scroll; 390x844 row 8 where the board does not scroll): fixed in placeExplain, shared with the hint strip — when the lift needs more room than the stage has, a spacer after the board as tall as the shortfall, removed with the strip; asserted at 844x390 for two bottom rows (plant: no spacer -> red), page scroll 0. F-403 (keyboard zoom does not re-place a strip) and F-404 (a redraw restores the outline but may leave the cell out of view, as the hint does) not changed: both are the hint strip's existing behaviour. Report meta/review/20261110T044803Z-CARD-412-cycle2.yml.
[Review 3/3] Score: 7.0 — fail (the last cycle). F-401 and F-402 verified fixed, but the F-402 spacer in placeExplain (shared with the hint strip) caused F-501 (a resize while present collapses Fit: 15x15 at 844x390 zoom 0.29 -> 0.10, board 108 -> 41 px, persists) and F-502 (closing on pointerdown drops it, the stage scroll snaps under the tap and the wrong cell is marked; the board moved 5-33 px on close). Reverted (the spacer and its test arm) — back to the placement all three reviews found sound; F-401's focus fix kept. F-503 (the stage grew 8 px below its cap) gone with it. Left: the F-402 limit — in the board's last rows, when the stage has no scroll left (844x390 rows 11-13 of 15 / 26-28 of 30; 390x844 row 8 of 15), the offer can lie over the named cell; the sentence names its row and column. Put to the owner 2026-11-10: merge with this limit, or hold. Report meta/review/20261110T052312Z-CARD-412-cycle3.yml.
[OWNER RULING 2026-11-10] "ok" to merging with the F-402 limit (the offer may lie over the named cell in the board's last rows when the stage has no scroll left; the sentence names the row and column).
[Gate] Player set (owner ruling 2026-11-09) on a19ab1d5: 1397 passed, 9 skipped (DATABASE_URL unset), 0 failed. Net node ids +2. Merged on the owner's "ok" after review cycle 3 failed on the reverted spacer (the review gate is not met; the owner accepted). Full suite owed at the wave close.
