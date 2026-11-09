# CARD-401: Icon-only toolbar on phones and short screens — Region shows two cells, the title and tier badge share a line

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- A branch commit (b47d8988) already implements most of the phone half; it is starting material only (it did not go through a gate; its two test edits and its blind spots are listed in Why). The cost is the short-screen switch, the icons for every control, the two-cell Region icon and the 44 px-versus-52 px question, each measured at four viewports. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/401-icon-only-toolbar
**Worktree:** —
**Source:** owner player findings 2026-11-07, items 1 and 5 ("Mobile - have only icons on buttons, no text. And reduce region icon to 2 cells."; "Smaller title, or the title on the same line as the difficulty badge"; "Icon-only should switch on for short screens as well as narrow ones"). All findings apply to the admin solver and the public player alike (one source).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/templates/_icons.html, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_brush_menu.py, tests/test_puzzle_solver_hint.py, tests/test_puzzle_solver_page.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_zoom.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. Conflict edges: CARD-400 (none: disjoint production files), CARD-402/403/404 (all edit admin.css and puzzle_solve.html: serialize). -->
**Review score:** 9.5 (cycle 1)
**Started:** 2026-11-09T09:05Z
**Closed:** 2026-11-09T10:08Z
**Actual:** 1 review cycle (wall clock excluded, owner ruling)
**Merge commit:** 071e4698
**Blocked by:** —

## Why this card exists

On a 390 px phone the 30 x 29 puzzle's toolbar wraps onto four rows (about 40% of the screen) before the board starts, and the admin's `--player-chrome-h` assumes ONE row. The owner wants buttons to carry icons only on phones, and the switch to apply to short screens (landscape phones, 844 x 390) as well as narrow ones, plus a two-cell Region icon and a smaller title.

**The existing branch commit** `claude/project-thread-2wh6wp` b47d8988 ("feat(player): icon-only toolbar on phones", written by another session, never gated; the owner told that agent to stop; do not merge, cherry-pick or check it out) was read for this card. Assessment, so the author does not rediscover it:
* Right: visually hides the word (`.player-btn-label` clip pattern) so the accessible name stays, adds `title=` tooltips, a bulb icon for Hint and a tick for Check that appear on phones only, brush trigger shows its swatch alone, solved banner shows the tick and "Solved", 44 px minimum width; measured 1280 px layout unchanged and the board 96 px higher at 375 px. The phone-only icon trick (`.player-phone-icon { display: contents }`) is reasonable.
* Breaks or misses: (1) the switch is `max-width: 600px` only: a landscape phone (844 x 390) gets none, which is finding 5's explicit ask; (2) Region still shows THREE cells (`player-brush-run` unchanged) and is in the 116 px group by accident of width; (3) zoom buttons are not iconised and `Hint`/`Check` keep their text above 600 px, so the 600-820 px band (tablet portrait, the 820 mirror breakpoint) is a third layout; (4) the solved banner loses the picture name visually on phones (the name was the answer reveal, CARD-163: it stays in the accessibility tree but a sighted player no longer sees what they solved; this is a behaviour change nobody ruled on); (5) `Check` gets an icon in markup but Check is admin-only: in public mode the markup is shared, so the bulb/tick spans ship twice; harmless but unmeasured; (6) the new CSS is appended at the file's end after all the rules it overrides, with no test that pins the breakpoint to a measurement (the 13rem `.player-tools` floor and the wrap point are re-derived by hand in a comment).
* Tests it edited: `tests/test_puzzle_solver_brush_menu.py` (adds a 390 px branch to the slot-width test: slot 116, trigger 44, region offset 52, `return`s early before the old 208/136 assertions: the old claim is still asserted for 1280/1440, so this is a re-measure of a changed layout, not a weakening, but the early `return` skips the remaining 390 px assertions of that test, which now go unasserted at 390: the new card must assert them at their new values) and `tests/test_puzzle_solver_hint.py` (Hint and Check now on Reset's row at 390: the old assertions "below Undo/Redo/Reset" and "above the counters, a row of their own" were replaced by "on Reset's row" plus a kept "above the counters"; a changed layout claim, and the test's docstring is updated, so honest in form; but the claim was never an owner decision, it was a measurement, so the new card re-derives it from the owner's finding rather than inheriting it).
* Verdict: usable starting material for the label-hiding mechanism, the accessible-name approach and the bulb icon; NOT usable as the implementation, because it does not deliver the short-screen switch or the Region icon and it silently drops the visible picture name. Take the ideas, write the card's own cells.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **One switch for "compact": narrow OR short.** A single media condition (for example `(max-width: 600px), (max-height: 500px)`; the exact numbers are measured on the toolbar's real wrap points and held by a test, the way the public player held its landscape bound: the width at which the groups wrap is found in the page and the breakpoint must cover it) turns the labelled buttons into icon-only buttons. Undo, Redo, Reset, Hint, Check (admin), Zoom out/in, Probe (see CARD-411 for Keep/Wrong guess) each get an icon (owner Q3 picks the set; recommended defaults in the question). The word stays in the accessibility tree and `title`/`aria-label` give the name; the tests that find buttons by role and name keep finding them.
2. **Region shows two cells,** not three (`.player-brush-run` holds two `.player-swatch`; the aria-label "Region" stays; `syncTrigger` paints two). On all widths (the owner's finding is about the icon, not the breakpoint): decide in Q4 whether desktop keeps three. Recommended: two everywhere, one definition.
3. **The title and the tier badge on one line** on compact screens (the `h1` shrinks on compact screens, the badge sits beside it); the explain line stays as it is in this card (CARD-409 moves it).
4. **Measured chrome, not the one-row estimate:** the card does not fix `--player-chrome-h` (CARD-403 does) but must not make it worse; state the toolbar's height at each viewport before and after.
5. **Solved banner keeps the picture name visible** on compact screens (the answer is the reward, CARD-163): shorten the label, not the name, or wrap into the board-does-not-move budget; whichever is chosen is asserted by `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth` unchanged.
6. **Tap targets** stay at least 44 px wide and `--control-h` tall in compact mode (CARD-195 AC-11 floor is 24 px; the owner's strip in CARD-402 is 52 px wide: nothing here may be narrower than 44 px).

## Acceptance criteria

* **AC-1** (icons only when compact): at 390 x 844 and at 844 x 390 every toolbar button's visible box contains no text node taller than 0 and an icon; at 1280 x 720 and 1440 x 900 the labelled buttons are unchanged. (test: new cells in `tests/test_puzzle_solver_phone.py` or a new module; plant: widen the media query by 1 px / drop the `max-height` arm and the 844 x 390 arm reds)
* **AC-2** (names survive): every button still has its accessible name ("Undo", "Redo", "Reset", "Hint", "Check", "Zoom in", "Zoom out", "Brush: <chosen>", "Region") and `title`; the keyboard Tab order of CARD-161 is unchanged. (test: role/name cells, the existing order test unchanged; plant: remove one label span's text)
* **AC-3** (Region is two cells): `.player-region` holds exactly two `.player-swatch` in the chosen brush's state; the button's box is no wider than it needs. (test: `tests/test_puzzle_solver_brush_menu.py` Region cells re-pointed; the old "three" claim retired with its date)
* **AC-4** (the toolbar shrinks as measured): the toolbar occupies at most N rows (N measured and written in the card at 390 x 844 and 844 x 390; the target is the owner's: one row of tools plus one of history/zoom or better), and the board's top is higher than before by the measured amount. (test: new geometry cell; evidence: Worktree note numbers)
* **AC-5** (nothing else moves): the 1280 x 720 and 1440 x 900 toolbar geometry equals the merge-base's to the pixel (the existing percent / maybe / brush-menu layout cells pass unchanged at those widths). (test: the existing cells)
* **AC-6** (the picture name stays readable): solved at 390 x 844 the banner shows the name and the board has not moved. (test: `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth` unchanged + a new visible-name cell; plant: hide the name visually)
* **AC-7** (every changed pin is a changed decision): the two test edits of b47d8988 are not inherited; each test changed here names the owner finding that changed its claim, and the 390 px assertions the branch's early `return` skipped are asserted at the new values. (test: node-id set difference + review-lens on the diff)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The branch commit b47d8988 is not merged, cherry-picked or built upon as a git object; its ideas are re-implemented under this card's gate.
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)
* CON-021 — the admin player remains the single admin-side play surface (check: review-lens)

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

[Env] forge executing from /Users/omelnikova/MyProjects/forge_1 (no version comparison run; the orchestrator is the player-phone thread, 2026-11-09).
[Impl 2026-11-09] Commit 7902d5a8 on card/401-icon-only-toolbar. Owner-question defaults taken (no recorded answer found; the owner's "go ahead and fix your findings" of 2026-11-09 is the authority): **Q4** Region is TWO cells at every width (one definition) — this moves the 1280/1440 tools-group interior (trigger 136 -> 151, toggle offset 144 -> 159, slot still 208), an explicit exception to AC-5's "to the pixel", re-pinned and dated in the test; **Q3** icons: undo, redo (mirrored undo), refresh (Reset), bulb (Hint), tick (Check, admin only), dashed square (Probe, the probe cells' own dashed outline). Zoom −/+ keep their text glyphs (already one-character icons): a recorded deviation from AC-1's literal "no text node"; swap to SVG if the owner wants it strict.
[Measure 2026-11-09] Shared-UI preview built from main (before) and from the branch (after), the same admin files the panel serves; toolbar [top, height] px and board top, 15x15 (0b910577ca) and 30x30 (52603b6dee) identical:
  | viewport | toolbar before | toolbar after | board top before -> after | title + badge one line |
  | 390x844  | 113, 188 (4 rows) | 102, 92 (2 rows: tools+history, zoom+counter) | 318 -> 210 (-108) | yes / yes (h1 2.5 -> 1.9 rem) |
  | 844x390  | 87, 95 (2 rows) | 75, 48 (1 row) | 198 -> 139 (-59) | yes / yes |
  | 1280x720 | 87, 48 | 87, 48 | 151 -> 151 | yes / yes |
  | 1440x900 | 87, 48 | 87, 48 | 151 -> 151 | yes / yes |
  No horizontal page scroll at any of the eight. The probe bar is a third compact row at 390 (its own bar, CARD-411's). --player-chrome-h untouched (CARD-403 owns it); at 390 the stage top is now closer to what it assumes, not further.
[Solved banner] On compact screens the banner shows the tick and the NAME; "Solved:" is visually hidden (.player-solved-label). The name wraps to at most two lines at --text-xs inside the 101 px slot (~25 characters) and is clamped with an ellipsis beyond that; accepted as the trade for the board not moving on solve (TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth unchanged, including its 120-character names at 390). The public site drops titles from the served schema, so there the banner shows what solver.js writes for an untitled puzzle.
[Tests] Changed (claims retired with the 2026-11-07 finding named in each docstring): test_puzzle_solver_brush_menu.py slot-geometry test (390 now asserted at 101/44/52 instead of skipped; 1280/1440 re-measured) and the two Region cell-count tests (3 -> 2; names kept per G-T); test_puzzle_solver_hint.py Hint/Check on Reset's row at 390. New: TestSolverPhone_CompactToolbar (2 viewport cells + the visible solved name). Net collected node ids +3 (review F5 dropped the redundant 1280 cell, d3f030bd). Plant: dropping the (max-height: 500px) arm reds the 844x390 cell alone (run by the author and by the reviewer); hiding the name visually reds the AC-6 cell (reviewer).
[Review 1/3] Score: 9.5 — no critical/important. F1 (worktree evidence) and F3 (title line) answered by the [Measure] note; F2 (Q4) by [Impl]; F4 (clamp) accepted in [Solved banner]; F5 fixed d3f030bd; F6 recorded in [Impl]. Report: meta/review/20261109T092612Z-CARD-401-cycle1.yml.
[Closing note, merge gate, merged 071e4698] Full suite from the worktree, unarmed (no local Postgres; the 29 DATABASE_URL skips + 1 setrlimit skip, 30 in all, as the unarmed baseline expects). Gate 1 red on 4: the frozen browser-family registry (3 new ids, recorded in ADDED_SINCE_BEFORE), tests/test_player_base_css.py's FROZEN table x2 (re-recorded against the real Bootstrap file, sha256 unchanged, same Chromium; the project stylesheet still equals it), and tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses::test_an_export_that_retains_a_fraction_of_the_book_fails, which reds on main 9406a630 alone (host bound at 15.3 retained pages) and is not this card's. The three fixed files re-run green (88a09351); no second full run. Accuracy: 1 review cycle against an estimate of 3c = 0.33. Net node ids +3.

