# CARD-411: Probe's buttons are clear and full size — '✓ Keep' and '✗ Wrong guess' — and the bar still costs the board no ground

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Small in code; the cost is the CARD-268 budget claim ('the bar is paid for above the toolbar, so the board sits where it sat'), which the larger buttons break and which must be re-paid, not relaxed. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/411-probe-buttons-full-size
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-411
**Source:** owner player findings 2026-11-07, item 8, third bullet: "Clearer, larger buttons. Use '✓ Keep' and '✗ Wrong guess' at full toolbar size" (text cut off in the document after 'tool'; read as 'full toolbar size'; owner Q14 confirms the wording 'Wrong guess' replacing 'Contradiction').
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-404
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_page.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The accessible names 'Keep' and 'Contradiction' are used by tests that find buttons by role and name and by the `data-player-probe-action` attributes (the attributes are the stable handle and do not change). Serialize after CARD-410 (same bar) if both are in flight. -->
**Review score:** —
**Started:** 2026-11-09T23:18Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Today the probe bar's buttons are `height: calc(var(--control-h) - var(--space-3))`, `font-size: var(--text-sm)`, in a bar that is paid for by negative margins so that the board does not move when a probe opens (CARD-268, `TestSolverProbe_TheBarCostsTheBoardNoGround`: 'there is no slack'). Full-size buttons are taller by `--space-3`: the budget must be re-paid (for example by reserving the bar's row always on compact screens, or by showing the Keep/Wrong guess pair in the place the Probe button occupies, which the owner's 'at full toolbar size' naturally suggests: Probe becomes the pair while a probe is open).

**[OWNER RULING 2026-11-07, on the drafter's question]** 'Contradiction' is renamed '✗ Wrong guess' (with '✓ Keep'), at full toolbar size.

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

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
* the behaviour is verified ONCE, on the admin page (owner test-budget ruling, 2026-11-07): no duplicate public-mode cell is added; a public-mode cell exists only where the behaviour differs in public mode (for example Check and the error counter do not exist there); CARD-385's existing public-mode sweep and the byte-identity test cover the copy;
* the served-tree scan (`TestSharedUi_TheServedTreeCarriesNoAnswer`) still passes: a feature that needs the answer is not allowed to read it in public mode (ADR-0041/R2).

## Viewports the card must verify

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390 x 844** (phone portrait), **844 x 390** (phone landscape), **1280 x 720** and **1440 x 900** (desktop), each on a 15 x 15 board and on the owner's 30 x 29 class of board (use a 30 x 30 stored grid; the exact puzzle 1750b436-... is in the production database, which is off limits to this work). For each: no horizontal page scroll, no control clipped, the board does not move when the thing the card changes appears or disappears, and the card's own claim.

## Worktree notes

[Env] forge from /Users/omelnikova/MyProjects/forge_1; orchestrated from the player-phone thread.
[Impl 2026-11-10] Commit cff14cee. Mechanism: the card's recommended "Probe becomes the pair". The toggle, Keep and Wrong guess sit in the History group in a .player-probe-slot grid; the one not shown keeps its box (visibility), so the row is equally wide closed and open. The probe line keeps only the leaving note, at a fixed height. G-4 holds: data-player-probe-action values and nextProbe/abandonProbe are untouched.
[Measure] Board top, closed = open (before this card: closed / open): 1280x720 238.8 = 238.8 (238.8 / 238.8); 1440x900 202.8 = 202.8 (202.8 / 202.8); 390x844 391.9 = 391.9 (391.9 / 424.8); 844x390 240.5 = 240.5 (243.3 / 263.8). Pair: 38.78 px tall on desktop (= Hint), 44 x 36 compact (= Hint).
[Decision pending, owner] Desktop has no room in the row for the pair. Built: option A — History buttons show icons on desktop too (names kept in clipped labels and titles), with no 44 px floor there (a mouse target), which keeps the counters stacked in row one: board top 238.8 at 1280 and 202.8 at 1440, closed and open — exactly today's. Option B (words kept): the counters wrap to a second row, board 10.8 px lower at 1280 and 46.8 px lower at 1440. Asked 2026-11-10 with screenshots (~/Documents/nonogram-reviews/CARD-411/).
[Glyphs] Keep's ✓ is success-coloured and Wrong guess's ✗ danger-coloured: on the phone the icon-only Keep otherwise read as Check's tick beside it (screenshot A-open-390x844).
[Tests] Net node ids 0. Re-pointed with the 2026-11-07 finding named: TestSolverProbe_TheBarCostsTheBoardNoGround (AC-1..AC-3; board top closed = open = after Keep, the 844x390 landscape measured inside the 390x844 case; pair height = Hint, >= 44 px compact; names Keep / Wrong guess; no "Contradiction"), TestSolverProbe_OnlyOneProbeAtATime::test_a_second_press_opens_nothing (no toggle offered while open), the resume note cell (AC-5 names). AC-4 by the unchanged probe rule cells. FROZEN base-css re-recorded (bs-alt sha, verified against the real file). The one control: the slot's visibility reserve removed -> BarCosts red at 1280x720. The base-css "[hidden]" plant kept able to fail: the note states display: block.

[Tests] First player-set run (cff14cee): 17 red, all from the 1280 row wrapping (board 10.8 px lower) plus the slot's place in the History group; fixed in 149a14f7 (desktop min-width) and these re-points, each naming the 2026-11-07 finding: TestSolverHint_PlacesTheButtonAndTheCounter (Check precedes the probe slot, which closes the group), TestSolverPhone_CompactToolbar's label sweep (drawn buttons only), the 600x844 band overflow 75 -> 72 in TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted and TestSolverPhone_MirroredGutterSticks (the zoom moved beside the counters there; toolbar 2.78 px shorter, stage 3 px taller).
[Review 1/3] Score: 7.5 — fail. F-001 (Important): the History-row slot's reserve moved the board where the card had not measured (public 390x844 +44, public 600/601x844 +46.8, admin 700x900 +46.8, admin 1000x500 +16): any in-row reserve wraps somewhere. Fixed by a different mechanism (9bdca4b5): the pair goes back to the probe line, which is now a full control row of FIXED height (Probe, or the pair and the note) — the board never moves on open/close, measured admin and public at 1280x720, 1440x900, 390x844, 844x390, 600x844, 601x844, 700x900, 1000x500, 1024x768, 360x740 (closed = open = after Wrong guess, all 20). The cost, paid once: the line is a control row where it was a small-button row, exactly --space-3 = 12 px on the admin page (1280: 238.8 -> 250.8; 390: 391.9 -> 403.9) and 4 px on the public page (390: 171.3 -> 175.3); TheBarCostsTheBoardNoGround asserts exactly --space-3 (retired claim: "costs nothing"), plant: the fixed height removed -> red at 1280 and 1440. The option A/B desktop question is withdrawn (no desktop icon change any more); F-003 and F-004 moot with it. F-002: focus handed Probe -> Keep on open and back on close (asserted in test_a_second_press_opens_nothing). F-005 noted: Wrong guess and the 30x30 measured by the reviewer at 14 sizes, all equal. The Hint/clues/phone re-points of 149a14f7 revert to main (the slot is gone); the CompactToolbar label sweep counts drawn buttons. Report meta/review/20261110T002326Z-CARD-411-cycle1.yml.
[Rework 2 / option C, f5ce248e] The full-height line everywhere (9bdca4b5) reddened 26 player cells: 12 px less stage on every desktop shrank big-board cells (30x30 at 1440: 16.625 -> 16.312) and took the column band's stick away at 1280x600. Put to the owner 2026-11-10 as A (full height everywhere) / B (today's height, clearer) / C (full height on compact screens only), C recommended and built pending the answer. C: on a mouse screen the line keeps its small-button height and costs nothing (board exactly as main: 1280x720 238.8, 1440x900 202.8, 700x900 282.4, 1280x600 238.8); on a compact screen the pair is Hint's size (36 px, 44 wide) on a full control row, 12 px of stage (admin 390x844 391.9 -> 403.9; public 4 px). The board never moves on open/close: admin and public at 1280x720, 1440x900, 390x844, 844x390, 600x844, 601x844, 700x900, 1000x500, 1280x600, 360x740. Re-pinned by exactly 12 px with the reason: TheRoomForAStuckBandIsMeasuredNotPredicted [390x844] and [600x844], MirroredGutterSticks (both cells). BarCosts asserts the cost (0 mouse, --space-3 compact) and the pair's height (Hint's compact, the line's on a mouse screen).
[Review 2/3] Score: 8.5 — gated only by F-101 (Important, an owner decision): AC-2 as written (the pair = Hint's height at 1280x720) is not met under option C (24 px on a mouse screen); waits for the owner's A/B/C answer — if C, AC-2 and the title claim are amended; if A, the mouse line becomes --control-h. Cycle-1 F-001..F-005 verified fixed by the reviewer: 48 cases (admin + public, 15x15 + 30x30, 12 sizes) with the board still; cost vs main 0 on a mouse screen, exactly --space-3 on every compact screen. F-102: the public cost is 12 px, not 4 (my 4 px read a different public layout); corrected here and to the owner. F-103: the note clamps to two lines on compact screens (three at <= 360 px spilled 1.45 px), full sentence in its title (ccf86bb9). F-104: the focus hand-back on close is asserted in test_a_second_press_opens_nothing (plant: removed -> red). Report meta/review/20261110T012653Z-CARD-411-cycle2.yml.
[OWNER RULING 2026-11-10] "A" — the pair at full toolbar height on EVERY screen; the probe line is a full control row everywhere and costs the board --space-3 (12 px) once, on desktop too (accepted with the stated consequences: big-board cells smaller at 1440, the column band at 1280x600 no longer kept). AC-2 stands as written; F-101 resolved by this ruling.
[Impl, ruling A, 764ec09f] The probe line is a full control row on every screen; its height follows its buttons (min-height --control-h) so a labelled desktop button (38.78 px) does not overhang a fixed line onto the board. Cost, once: 14.78 px of stage on a mouse screen, 12 px compact; never moves on open/close. Consequences found and re-pointed (each cell names the ruling): measured stage/overflow/cell figures +14.78 desktop (1280x720 overflow 118 -> 133; 30x30 cell at 1440 16.625 -> 16.25; 20x12 at 1280x720 27.34 -> 26.20); at 1280x600 the column band is no longer kept (recorded in TheRoomForAStuckBandIsMeasuredNotPredicted); a 22x14 at 1280x760 and a 30x25 at 1920x1080 lose the doubled rung, so the windows whose premise is that room grow by the stage lost (SHORT_720 600 -> 615, LAPTOP_760 760 -> 775, WIDE 1080 -> 1095), as CARD-403 did; the 1100x700 single-digit ring pair now parts (0.78 px) like the phone's. Net node ids 0.
[Review 3/3] Score: 9.0 — passed. The reviewer measured 68 rows (admin + public, 15x15 + 30x30, 17 sizes): the board top equal closed / open / after Keep / after Wrong guess everywhere, the pair = Hint's height everywhere, the note inside the line (5.5-13.2 px clear); cost vs main: admin +14.78 mouse / +12 compact, public +12 everywhere (its labelled buttons are 36 px — F-204). Plants: line fixed at control-h, pair at the small size, a 1 px deeper pull -> red. Follow-ups fixed in 6c0c104f: F-201 the note clamps to two lines on every screen (a large default font at 601-760 px had grown the line on open); F-202 stale comments rewritten; F-203 the hand-back after Keep asserted too. Report meta/review/20261110T032901Z-CARD-411-cycle3.yml.
[Gate] Player set (owner ruling 2026-11-09) on 6c0c104f: 1394 passed, 9 skipped (DATABASE_URL unset), 0 failed. Net node ids 0. Full suite owed at the wave close.
