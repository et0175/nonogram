# CARD-404: Clue strips stop growing with the zoom — the numbers cap at a readable size while the cells grow — and the strips stay pinned at every zoom

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 4c (1.5d)
<!-- Over the 3c target on purpose: the cap touches the numeral size, the strip thickness, the ring (circle) geometry, the fit arithmetic of the cell and the sticky share (`STICK_MAX_SHARE`), which are one coupled calculation in admin.css and solver.js. If the first cycle shows the ring geometry alone is a cycle, the ring cells split into a follow-up card; the owner lifts the cap by ruling only. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner player findings 2026-11-07, items 3 and 6 ("The clue strips zoom too. At 200% the row clues take about 135 px ... Keeping the clue text at a fixed readable size while only the cells grow would roughly double the playing area. Alignment should stay of course." with the owner's own spec: cap the numbers around 13-14 px; the cap only limits growth when zooming IN; a column's box stays narrow when zoomed out so a two-digit clue keeps today's small size; the along-the-line dimension keeps zooming with the cells). Item 3: "At 100% and above the clue strips stay pinned (row clues at the side, column clues at the top)."
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_zoom.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_fifth_rule.py, tests/test_admin_design_tokens.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Conflict edges: CARD-401/402/403 (admin.css; serialize), CARD-405 and CARD-406/408/410 (all depend on the strip geometry this card fixes). -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**Mechanism (verified):** `.player-board { font-size: max(12px, cell * 0.6) }`, so the numerals, the row band (`--player-row-ch` in ch) and the circle rings all grow linearly with the cell. At 200% a 28 px cell is 56 px and the numerals 33 px, which is the owner's 135 px row strip. The column band is `--player-col-depth` rows of cell-height boxes, so it grows the same way. The sticky mechanism (CARD-271) then refuses to stick: `STICK_MAX_SHARE = 0.4` of the stage; `solver.js` itself records that at 300% 'the band is 9 cells deep in an 11-cell stage' so the clues scroll away exactly where the owner needs them, which is the same defect the owner listed under item 3. Capping the numerals makes the band constant above the cap, which is what lets the strip stay pinned at every zoom.

Along the line (a row clue box is one cell tall, a column clue box one cell wide) keeps zooming with the cells; the thickness (row strip width, column strip height) comes from the numeral size and is what the cap holds. The owner's example numbers: at 200% a row's clue is a 29 px-tall box holding 14 px numbers.

## What to implement

1. **Cap the clue numerals** at a readable size (owner: 13-14 px; owner Q7 fixes the number; recommended 14 px) when the cell grows past the size at which `0.6 * cell` reaches it; below that the existing rule (`max(12px, 0.6 * cell)`) is unchanged. `?` glyphs in cells keep growing with the cell (they are cell content, not clue text).
2. **Strip thickness follows the capped numerals,** not the cell: the row band's `--player-row-ch` term and the column band's depth are computed from the capped size, and the fit arithmetic of the cell (the three-term `min(...)` and the `0.36 * ch` growth term) is re-derived from the new constants, not patched. The 100% fitted size of boards where the cap does not bind is unchanged.
3. **Alignment stays exact:** each clue box still spans exactly one cell along its line, so each clue sits beside its own row or column at every zoom.
4. **The circle rings** (CARD-188/213 pill geometry derived from `--player-clue-digits`) follow the capped numerals; the existing ring cells re-pass at their new constants.
5. **Sticky at every zoom:** `keepCluesInView` / `STICK_MAX_SHARE` are re-measured against the capped band: at 300% on a 30 x 30 at 1280 x 720 and 390 x 844 the row clues and column clues of the cell under each corner stay in view (CARD-271's phone and 300% exclusions, recorded there as 'owner decisions about the BAND', are exactly what this card's owner request reverses; the author states the old exclusion and the new measurement).
6. **Docs:** the CARD-271 comment block in `solver.js` and the `admin.css` header comments are updated to the new rule.

## Acceptance criteria

* **AC-1** (the strip stops growing): for a 30 x 30 at 1280 x 720, the row strip's width and the column strip's height at 200% and 300% are at most the value at the zoom where the cap first binds, plus the rule widths (equal to within 1 px), and the numerals' computed font-size never exceeds the cap. (test: new cell in `tests/test_puzzle_solver_zoom.py`; plant: remove the cap and the 200% arm reds)
* **AC-2** (alignment): at 100%, 200%, 300% every row clue box's top and height equal its row's, and every column clue box's left and width equal its column's, to the pixel. (test: new cell; plant: set the clue box height to the numeral height)
* **AC-3** (the playing area grows): at 200% on the owner's class of board at 390 x 844 the visible cells exceed the merge-base's by the measured amount (the owner estimates roughly double; the number is measured and written in the card). (test: new cell with the merge-base's figure as a recorded constant; evidence: Worktree note)
* **AC-4** (small cells keep today's size): zoomed out or at 100% on a 30-wide board the numerals are exactly as before (12 px floor; a two-digit column clue fits its narrow box). (test: `TestPlayerNumerals_*` cells unchanged)
* **AC-5** (pinned at every zoom): at 100%, 200% and 300%, scrolled to each corner, the clues of the corner cell are inside the stage, on the board's plain and its doubled layouts. (test: `TestSolverZoom_CluesStayInViewWhileZoomed` extended to 300% and to 390 px; the CARD-271 exclusions it records are retired with the date)
* **AC-6** (rings): every ring cell passes at the new constants (`TestSolverClues_TheCircleIsVisible`, `_SingleDigitRowRingsMayTouch`, `_RowRingsStayInsideTheirOwnBand`, two-digit rings on a 30 x 30). (test: existing cells; any changed number is attributed to the cap)
* **AC-7** (fifth-line rules and fit): the 15 x 15 28 px / 56 px pin and the fifth-rule geometry cells pass unchanged. (test: existing cells)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The cap is an upper bound on growth only: no numeral gets smaller than it is today anywhere.
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)


## Architecture context

FR-044 (the admin puzzle player, TERM-037) and FR-045 (public player, COMP-011) — the public player gets this behaviour by the shared-UI mode, not by its own code. The author reads the AC ids in `requirements.yml` FR-044 and amends exactly the ones whose claim changes (do not guess ids; AC-345..AC-347 are the circling ACs). ADR-0038 (player constraints) apply as for any solver.js edit. CARD-271's recorded exclusions are reversed on the owner's request here.

## How this reaches the public player

One source of truth (owner direction 2026-11-07; ADR-0041/R3): the change is made ONLY in the admin files (`src/nonogram/admin/static/solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and the admin templates). Nothing in `player/play.js`, `player/player.css` or `player/play.html` is edited or tested by this card: CARD-399 retires them, and production serves `play.js` until the owner deploys the shared-UI mode, so this card reaches production only through the shared-UI rebuild and that deploy (the owner's timing; CARD-394 and CARD-399 are NOT dependencies of this card). What the card owes the public side:

* the shared-UI tree assembled from the changed files passes `tests/test_player_shared_ui_site.py::TestSharedUi_ByteIdentity` with no edit to the table it holds (the copies stay byte-identical; no override layer, no public-only rule);
* every new behavioural cell runs on the admin page AND on the public-mode page (`mode: "public"`, no solution, CARD-385's sweep in `tests/test_player_public_mode.py`), or the card says in one line why the behaviour does not exist in public mode (for example Check and the error counter);
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

(none yet)
