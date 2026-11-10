# CARD-400: A clue number the player's marks have settled gets circled — the uncircled-but-solved cases are enumerated and the owner's example reproduced before any rule changes

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 3c (1d)
<!-- Small in code (one pure function and its table), but the first step is a measurement and the second is a rule the owner has pinned twice (CARD-188 AC-6, CARD-213 AC-2/AC-4). If the measurement shows the missing circles all belong to ONE already-pinned class, the card stops after step 2 and reports instead of changing the rule (owner question Q1). -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/400-settled-numbers-circle
**Worktree:** —
**Source:** owner player findings 2026-11-07, item 10: "BUG: Some solved numbers are not circled (last but one '2' in this picture)", puzzle 1750b436-5669-4ed0-9bc0-56aa2f7e34be on the admin panel (production database: off limits to this work, so the line is read from the owner's screenshot or supplied by the owner). Source file: `~/Documents/nonogram-reviews/player-findings-2026-11-07/OWNER-FINDINGS.md`.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py, meta/architecture/requirements.yml, docs/how-it-works/01-domain/puzzle-creation/08-playing-a-stored-puzzle.md
<!-- `solver.js` (paintCircles / clueNumbersOf) is expected NOT to change: it was read at drafting time and paints whatever `circledClues` returns after every commit AND after every redraw (`redraw()` ends in `showProgress(null)`), so a stale-paint defect is ruled out by reading. If the author finds otherwise, solver.js joins Touches and the finding is reported. `tests/test_public_player_circles.py` pins play.js's port (CARD-399 family) and is NOT touched. -->
**Review score:** 9.0 (cycle 1)
**Started:** 2026-11-10T09:51Z
**Closed:** 2026-11-10T12:22Z
**Actual:** 1 review cycle (wall clock excluded, owner ruling)
**Merge commit:** 207470ef
**Blocked by:** —

## Why this card exists

Item 10 of the owner's findings: on the owner's puzzle a number whose run the player has marked is not circled (the "last but one 2" of a line). Nothing in the paint path loses a circle (it repaints on every commit and every redraw, twins together); the decision is `circledNumbers(clue, cells)` in `solver_state.js`, which circles a number only by rule A (closed runs walked in from an edge, contiguous), rule B (every dark run closed and the runs equal the clue) or rule C (a value unique in the clue, matched by exactly one CLOSED run). "Closed" means a white cell or the line's edge on both sides: an undecided cell, or a `?`, beside a run keeps it open.

Four hypotheses for the owner's number, in order of likelihood, each with the existing owner decision it would collide with (this is why the card measures before it fixes):

* **H1, open run.** The player filled the run but left a neighbour undecided (the player never marks whites: `isSolved` accepts undecided whites, so a solved board can be full of open runs). The line is then complete in blacks and uncircled. Pinned: CARD-213 AC-4 / `TestSolverClues_OpenRunDoesNotCircle` ("open means open"). Fixing H1 REVERSES that decision.
* **H2, repeated value, not reachable by a walk.** The "2" shares its value with another number in the clue (rule C refuses), and the walk from the edge stops at a neighbour the player has not closed yet (the last number's run is open or unmarked). Pinned: CARD-213 AC-2 / `TestSolverClues_RepeatedLengthDoesNotCircle` and AC-346 / `TestSolverClues_AmbiguousRunStaysUncircled`. A geometric rule (below) would circle some of these and keep the pinned ambiguous cases uncircled.
* **H3, a stray mark.** A wrong-but-closed dark run, or a mismatched closed run, stops a walk (`test_a_mismatched_closed_run_stops_its_walk`) or breaks rule B's equality, so the number beside it stays uncircled although its own run is right. Decision-neutral to circle only if the owner calls it a defect.
* **H4, a `?` (Maybe) beside the run.** `?` is neither dark nor white to every rule, so it keeps a run open. Same family as H1.

Data the author needs from the owner for the exact line (not derivable): the clue of the row or column that holds the uncircled "2" and the state of every cell of that line in the screenshot (dark, white dot, blank, `?`).

**[OWNER RULING 2026-11-07, TEST BUDGET]** "I don't want to double tests for them - mostly it's not a new functionality. I'd rather have less tests than more." So: (1) the behaviour is implemented ONCE in the admin files and verified ONCE, on the admin page; NO duplicate public-mode copy of a cell is added (the byte-identity test and CARD-385's existing public-mode sweep cover the copied files); a public-mode cell is added only where the behaviour genuinely differs in public mode; (2) prefer CHANGING an existing test (re-pin a measurement the change legitimately moves, retire a claim the change replaces and assert the new one in the same place) over adding a new one; (3) a new test is added only for a claim that is a NEW owner decision and is not already asserted by an existing test; ONE discriminating assertion per behaviour change, with at most ONE control that can fail per card (the repo's controls-that-can-fail rule is met by that one control, not by a mutant cell per acceptance criterion); (4) delete tests whose claim the change makes obsolete, with a named survivor (the owner's rule: a test is kept only if its claim is a live decision); (5) the closing note states the NET test-count change (collected node ids before and after); a pure re-layout or restyle card should end at or below zero net. Where an acceptance criterion below asks for more cells than this allows, this ruling wins and the author states which criterion is verified by an existing test or by review-lens evidence instead.

## What to implement

1. **Reproduce the owner's line.** Add a cell to `tests/test_puzzle_solver_clues.py` (same harness as `_numbers`) with the owner's clue and marks, asserting today's verdict (the "2" uncircled) and naming which hypothesis it is. If the line cannot be obtained, say so and use step 2's table to show which class(es) can produce it.
2. **Enumerate, do not guess.** Over every clue and every marking of lines up to length 8 where the marks are consistent with SOME placement of the clue (no wrong mark) and the number's own run is fully dark, list the numbers that are not circled, grouped by cause (open run beside an undecided cell, open run beside `?`, repeated value with an unreachable walk, a stray mark). Record the group sizes in Worktree notes (the same idiom as the "941 cases" comment in `solver_state.js`: measured, with the harness named). This table is what the owner rules on.
3. **Fix the classes the owner rules in, and only those.** Candidate rule D, offered not decided: a number is circled when its run is fully dark and closed AND the line's geometry leaves exactly one number it can be (the numbers before it fit left of the run, the numbers after it fit right of it, counting closed runs on each side). D keeps AC-346's "2 2" middle run uncircled (both numbers fit) and circles a middle run that only one number can own. A relaxation of "closed" (a complete line of blacks with undecided neighbours circles) is a separate ruling (H1 / Q1) and a separate arm.
4. **Re-point only what the ruling changes.** AC-346/AC-347 and the pinned tests above stay as they are unless the owner rules the class in; then the old claim is retired in the docstring with the date and the new claim asserted. `circledNumbers` stays a pure function of (clue, cells), reads no solution, and is the same function the public mode uses.
5. **Docs.** The rule comment block in `solver_state.js` ends with a table that matches the code, and `08-playing-a-stored-puzzle.md` states the rule in the owner's words.

## Acceptance criteria

* **AC-1** (the owner's line is reproduced): a cell asserts the pre-fix verdict on the owner's clue and marks and names its cause (H1..H4); if the line was not obtainable the card says so in Worktree notes and AC-2 carries the whole weight. (test: new cell in `tests/test_puzzle_solver_clues.py`; evidence: review-lens on the Worktree note)
* **AC-2** (the table is measured): a cell enumerates the classes over lines up to length 8 with an independent brute force (a second implementation, not `circledNumbers`), asserts the count per class, and the counts in Worktree notes equal what the cell computes. (test: new cell; plant: change the enumerator's closedness test and the counts must move)
* **AC-3** (the ruled-in classes circle): for each class the owner rules in, the marks of AC-2's table circle the number, and the same marks with ONE cell changed (the neighbour that makes the number ambiguous or wrong) do not. (test: new paired cells, same shape as `TestSolverClues_OpenRunDoesNotCircle`'s pairs)
* **AC-4** (nothing the owner did not rule in moves): every pinned cell keeps its verdict: `TestSolverClues_AmbiguousRunStaysUncircled`, `_RepeatedLengthDoesNotCircle`, `_OpenRunDoesNotCircle`, `_ZeroClueRuleUnchanged`, the property cells (`NeverCirclesWhatBruteForceDoesNot`, `RuleCOnlyAddsToRulesAAndB`, `RuleCInvariantUnderTransposition`) except the ones whose class was ruled in, each named with the decision that changed it. (test: node-id set difference empty; changed cells listed)
* **AC-5** (never circles a wrong number): no new rule circles a number on a marking that fits no placement of the clue unless the pinned "wrong but self-consistent" behaviour already did. (test: the existing brute-force property cell, extended to the new rule; plant: drop rule D's geometry check and it reds)
* **AC-6** (public mode, same function): the public-mode page circles the same numbers for the same marks. (test: a cell in the CARD-385 sweep file or `test_player_shared_ui_site.py`'s browser cells)

## Guardrails

* **G-1** Admin files are the only source edited (see "How this reaches the public player"); no `play.js` / `player.css` / `play.html` work.
* **G-2** `touch-action` on the board is not touched (owner 2026-11-05: stays as it is; do not reopen), and the crosshair, the Maybe ground and the cell min/max principle (owner 2026-11-06: keep a floor-and-cap rule, cells smaller by default) are not reopened unless this card's Source says so.
* **G-3** Nothing is saved that was not saved before: view settings stay out of `serializeState` and localStorage (CARD-195 rule 6).
* **G-4** The rule is a function of the line's marks and the payload's clue only; it must not read `payload.solution` (public mode seals it).
* **G-T** No test is deleted, renamed, skipped or weakened to fit. A test is changed ONLY if its claim is a CHANGED owner decision named in this card's Source: the old claim is retired in the test's docstring with the decision's date and the new claim is asserted in the same cell (a number is re-measured, not relaxed). The owner's rule applies: a test is kept only if its claim is a live decision. Node-id set difference against the merge-base is shown in Worktree notes, and every new cell has a plant that makes it red (an edge mutant, not only a happy path).

## System contract

* ADR-0041/R3 — the public player runs byte-identical copies of the admin files (check: `TestSharedUi_ByteIdentity`, unchanged table)
* ADR-0041/R2 — no solution in any public asset (check: `TestSharedUi_TheServedTreeCarriesNoAnswer`, unchanged)
* ADR-0038/R3, R4 — pure rules live in `solver_state.js`, clues come from the payload (check: the pure cells named in the ACs)
* ADR-0038/R3 — clues come from the payload; the answer is not an input (check: AC-5 / the sealed-solution cell)

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

OWNER REPRODUCTION 2026-11-08 (the data "What to implement" item 1 asked for; supplied by the owner, not derived): on the admin panel, puzzle 32861a84-0750-44f7-b0b1-f7502368f0dc (https://nonogram-admin.onrender.com/puzzle/32861a84-0750-44f7-b0b1-f7502368f0dc/solve), line 27: the clue's 4 and 3 are solved (circled), and the 1 and 1 at the left could be circled but are not. The author reads the puzzle's clues from the puzzle file/bundle WITHOUT touching the production database (nonogram_poc is never connected); if the clue and the marks of line 27 cannot be recovered from a local copy, ask the owner for the clue and the state of each cell of line 27 (dark, white, undecided) instead of guessing. This is a second instance of the same class as the original item-10 example (a settled number beside a settled run not circled) and may separate H1/H2 (the two 1s share a value, so rule C refuses) from H3: record which hypothesis it supports.
[OWNER RULING 2026-11-10] "ok but I think it would be nice to fix all 3": circle a number when the marks pin it down (the same span, all dark, in every placement of the clue consistent with the marks). All three measured groups (open beside undecided, open beside "?", closed repeated value with a blocked walk) are settled by construction and circle; nothing still ambiguous does. Retires CARD-213 AC-4 "open means open" and the repeated-value refusal where the number is pinned.
[Impl 2026-11-10] Commits 95468af2 (rule D + tests), docs commit. circledNumbers gains rule D: a number whose run has ONE feasible start over the placements that fit the marks (earliest == latest, from lineForced's reachability table), all its cells dark. The owner's line (column 7, clue 6 3 2, last 2 dark at rows 22-23, blank above) circles. A/B/C kept (they still read marks that fit no placement as before). A bug found on the way and fixed before commit: the greedy earliest-start loop could skip a dark cell and spin (it hung the test run); it now stops at a dark cell.
[Tests] Net node ids +1: TestSolverClues_PinnedNumbersCircle (AC-1 owner line; AC-2/3/5 property: every clue and every fitting marking of lines 1..7, 16,292 lines, circles exactly what an independent brute force calls pinned). Re-pointed, each naming the 2026-11-10 ruling: _brute_circles (no "closed" requirement) and the safety property's brute_only (>= 100 -> == 0: equal on fitting lines); RuleExamples rows DD.DD..... (2 2) and WDWD...... (1 1 1); RepeatedLength and OpenRun cells held to the reference; the Python reference _rule_circles gains rule D via _pinned (a memoised start search, agreeing with the brute force on all 16,292 lines); RuleCOnlyAddsToTheOldTable (rule C's additions kept, D on top, module == reference); CirclesFollowEveryCommit held to the reference at each step. AC-346 (the ambiguous "2 2") unchanged and green. Plant: rule D's earliest==latest test removed -> the property and the safety cells red. AC-6 (public mode): the same pure function on byte-identical files (no new cell, owner test budget). Docs: 08-playing-a-stored-puzzle.md states the rule in the owner's words; requirements AC-345 / AC-347 amended.
[Tests] Player set on 37e432ff: 1395 passed + 2 red (TestSolverZoom_SurvivesADoubledRedraw: row 0 fully marked now also pins some columns' first numbers, so it counts row circles — re-pointed with the ruling; the CARD-217 registry: the new id registered). Re-run green. Pre-existing on main, not this card: meta/architecture/requirements.yml does not parse (line 5929, a book AC with an unquoted colon).
[Review 1/3] Score: 9.0 — passed. The reviewer fuzzed 200,000 lines of length 1-12 with dark, white, blank and "?" (110,032 fitting): circledNumbers equals an independent brute force's pinned set on every one; marks that fit nothing return as main did; 30-60-cell lines terminate (20,000 in 379 ms); circledClues on a 30x30 ~1.06 ms per commit. Follow-ups: F-001 the AC-1 cell's owner line now at its screenshot rows (24 blank, rows 25-26 dark, 4 white); the 2026-11-08 instance (row 27, clue 1 1 1 4 3 1 1 1) is also circled now — its second and third 1. F-002 test_PropertyTest_SolverClues_RuleCOnlyAddsToRulesAAndB's docstring names the ruling (the reference now carries D: a stronger claim). F-003 AC-2's per-class counts are carried by review-lens, not a test (owner test budget): the figures (21,316 / 46,901 / 34,643 / 1,124) were re-derived exactly by the reviewer; the "beside a blank" bucket includes 12,258 runs with a blank and a "?" beside them. F-004 viewports: n/a — a pure-logic change with no layout change (circles are a class on existing numerals). Report meta/review/20261110T120313Z-CARD-400-cycle1.yml.
[Gate] Player set (owner ruling 2026-11-09) on 22858aeb: 1397 passed, 9 skipped (DATABASE_URL unset), 0 failed. Net node ids +1.
