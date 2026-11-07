# CARD-410: Probe flags broken lines — a row or column the probe's marks can no longer satisfy tints its clue red, and the Contradiction button is gently highlighted

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- A pure detector already exists (`lineForced` returns null when no placement fits); the cost is the 'broken BY the probe' scoping, the red clue channel apart from circles/crosshair/hint, and the button highlight. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 8, second bullet: "Flag broken lines during a probe. When a row or column can no longer match its clue, tint that clue red and gently highlight the Contradiction button."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-404
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_probe.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. After CARD-404 because the clue box geometry and tints it edits are the surface this card paints on. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`solver_state.js` already exports `lineForced(clue, cells)`: 'null when no placement fits', treating FILLED and EMPTY as fixed and UNKNOWN and MAYBE as free. A line is BROKEN when it returns null. During a probe, the lines the player's EARLIER marks had already broken (a wrong mark before the probe) must not light up as if the probe broke them: the owner's flag means 'your guess led to this'. So the set is: lines broken now AND not broken at the probe's checkpoint (the checkpoint board is available: `checkpointHistory(history, probe)`).

This reads the clue and the marks only (no solution): it works in public mode, and it does reveal a mistake during a probe by design (the owner asked for it); outside a probe nothing is flagged (Check is the admin's tool for that).

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Pure function** `brokenLines(board, checkpointBoard, rows, columns)` in `solver_state.js` returning the row and column indices broken now but not at the checkpoint.
2. **Paint:** a clue box of a broken line gets a red tint (a new class, `.is-broken`; red from the tokens: `--color-danger` or its tint; no token added to `tokens.css`, derived with `color-mix` as the probe and hint tints are) on every gutter box of the line (twins together); the colour is apart from circles' ink, crosshair, hint line and probe ring by the same dE76 floors CARD-268 set, and the contrast of the numbers on the red passes 4.5:1.
3. **The button:** while at least one line is broken the Contradiction button (today's label; CARD-411 renames it) gets a gentle highlight (outline/pulse, not a colour change that reads as disabled/enabled).
4. **Only during a probe,** and repaint on every commit, undo/redo and redraw (twins of CARD-188's paint discipline); closing the probe (Keep or Contradiction) clears every flag.

## Acceptance criteria

* **AC-1** (the pure rule): over a seeded corpus of lines (clue, checkpoint marks, probe marks) the function flags exactly the lines `lineForced` calls broken now and not at the checkpoint, checked against an independent brute-force placement enumerator; a line broken before the probe is not flagged. (test: new property cell with a minimum case count inside the test; plant: drop the checkpoint subtraction)
* **AC-2** (the clue turns red, both gutters): on a doubled board both twins of a broken line's clue are red together, and clear when the probe closes by Keep and by Contradiction. (test: new browser cells; plant: paint one twin)
* **AC-3** (apart from the other tints): the red differs from plain, crosshair, hint-line and probe-ring grounds by the CARD-268 floors, measured. (test: extension of `TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround`'s idiom, new cell)
* **AC-4** (the button): the Contradiction button has the highlight class exactly while a line is broken. (test: new cell)
* **AC-5** (no probe, no flag): with no open probe nothing is red however wrong the marks are; circles are unchanged. (test: new cell)
* **AC-6** (public mode): the same behaviour with no solution. (test: public-mode cell)

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
