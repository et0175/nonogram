# CARD-411: Probe's buttons are clear and full size — '✓ Keep' and '✗ Wrong guess' — and the bar still costs the board no ground

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Small in code; the cost is the CARD-268 budget claim ('the bar is paid for above the toolbar, so the board sits where it sat'), which the larger buttons break and which must be re-paid, not relaxed. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 8, third bullet: "Clearer, larger buttons. Use '✓ Keep' and '✗ Wrong guess' at full toolbar size" (text cut off in the document after 'tool'; read as 'full toolbar size'; owner Q14 confirms the wording 'Wrong guess' replacing 'Contradiction').
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-404
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_page.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The accessible names 'Keep' and 'Contradiction' are used by tests that find buttons by role and name and by the `data-player-probe-action` attributes (the attributes are the stable handle and do not change). Serialize after CARD-410 (same bar) if both are in flight. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Today the probe bar's buttons are `height: calc(var(--control-h) - var(--space-3))`, `font-size: var(--text-sm)`, in a bar that is paid for by negative margins so that the board does not move when a probe opens (CARD-268, `TestSolverProbe_TheBarCostsTheBoardNoGround`: 'there is no slack'). Full-size buttons are taller by `--space-3`: the budget must be re-paid (for example by reserving the bar's row always on compact screens, or by showing the Keep/Wrong guess pair in the place the Probe button occupies, which the owner's 'at full toolbar size' naturally suggests: Probe becomes the pair while a probe is open).

**[OWNER RULING 2026-11-07, on the drafter's question]** 'Contradiction' is renamed '✗ Wrong guess' (with '✓ Keep'), at full toolbar size.

## What to implement

1. **Names and glyphs:** 'Keep' -> '✓ Keep' and 'Contradiction' -> '✗ Wrong guess' (owner Q14), with the glyphs `aria-hidden` and the accessible names 'Keep' and 'Wrong guess'. In compact mode (CARD-401) the labels may drop to the glyph with the name in the accessibility tree and a `title`.
2. **Full size:** the two buttons use the toolbar's `--control-h` and `--text-base`, and are at least 44 px in compact mode.
3. **Re-pay the ground:** the board's top is unchanged by opening and closing a probe (author's mechanism, measured; the 'Probe becomes the pair' form is the recommended one).
4. **The leaving-abandons note** keeps its wording (it names the two buttons: update the names in it).

## Acceptance criteria

* **AC-1** (the labels): while a probe is open the two buttons have the accessible names 'Keep' and 'Wrong guess' and show the glyphs; the old name 'Contradiction' is gone from the page. (test: re-pointed role/name cells; the changed claim is named with the finding; plant: leave the old label)
* **AC-2** (the size): each button's height equals the toolbar button height at 1280 x 720 and 390 x 844, and is at least 44 px wide in compact mode. (test: new geometry cell)
* **AC-3** (no ground): the board's top is the same with no probe, with a probe open and after closing it, at 1280 x 720, 390 x 844 and 844 x 390. (test: `TestSolverProbe_TheBarCostsTheBoardNoGround` re-pointed to the new mechanism; the claim 'the board does not move' is kept, only its mechanism changes)
* **AC-4** (behaviour unchanged): Keep commits, Wrong guess undoes back to the checkpoint, redo and the save rules (CARD-268 rules 4-10) are unchanged. (test: the existing probe rule cells, node-id difference empty)
* **AC-5** (the note): the leaving-abandons line names the new button names. (test: re-pointed text cell)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The `data-player-probe-action` attribute values and the probe state machine (`nextProbe`, `abandonProbe`) are not touched.
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)
* CARD-268 probe semantics (check: the existing rule cells)

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
