# CARD-380: Probe mode on the public player — the hypothesis transaction, needing no answer

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d) <!-- Stated in review cycles at DRAFT time, so the card cannot redden tests/test_kanban_review_record.py when it is stamped into a wave (CARD-325 did). A forecast, not a tuned figure: the pure state machine already exists and is solution-free (so this is wiring, like CARD-324/325/326, which took 3, 1 and 1 review cycles), but the semantic surface is larger than theirs (eleven declared rules, a save that must never hold probe strokes, a clamp, a fourth mark on a board that already carries three) and one rule (7) needs a design choice the admin never faced. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner question 2026-11-06 ("do we have a card for contradiction-probe mode on player?") answered by the orchestrator with "no", then "draft the probe card, queue it behind 327". The admin's version is CARD-268, from the owner's decision of 2026-10-22: "for puzzles that need contradiction-probing add another color for probing cells", shaped in that session into a transaction.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-327 <!-- a REAL dependency and not only serialization: rule 3 says every mark made while a probe is open, hint strokes included, belongs to the probe; the public page has no hint until CARD-327 lands, so the interaction cannot be built or tested before it. CARD-327 also settles where a non-toolbar control lives on this page, which this card reuses. They also share play.js, play.html and player.css (overlap 1.0), so they could not run in one wave anyway. -->
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_probe.py, tests/test_public_player_agreement.py <!-- the agreement file because the probe's look is a look the public player reimplements, so it is held to the admin's there (CARD-328's one home), as CARD-325, 326 and 327 did; tests/test_public_player.py is a SCOPE+ edit only if the listener census demands it, declared as CARD-325's was -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The owner's 2026-10-30 request for the public player ("the player misses a lot of the player from the admin player... I'd like both to reuse the same functionality") became cards for the maybe cell (CARD-323), zoom (CARD-324), the crosshair (CARD-325), circled clue numbers (CARD-326) and the derived hint (CARD-327). **Probe mode, the admin's CARD-268, is not among them.** Measured 2026-11-06: no public-player card (323 to 328, 282, 283) mentions it; CARD-283's out-of-scope list names the error count, hints, scores, accounts and server-side state, and does NOT name probe; `player/play.js`, `player/play.html` and `player/player.css` contain no probe code. **So it is a gap in the parity list, not a recorded exclusion** (the error count, progress percent and Check ARE recorded exclusions, by the owner's 2026-10-30 decision, and stay out).

**What is reusable, measured from the signatures in `solver_state.js` 2026-11-06:** `nextProbe(probe, history, event)`, `probeStart(history, probe)`, `probeCells(history, probe)`, `abandonProbe(history, probe)` and `checkpointHistory(history, probe)` take a history and a probe state and NO solution. The whole transaction (open, membership, abandon, clamp, checkpointed save) is solution-free; this is wiring, as zoom was. The one place the admin's version touches the answer is rule 7 (below).

### Why a transaction and not a fifth cell state (carried from CARD-268, unchanged)

A solver probing makes a GROUP of marks under one hypothesis and then reverts them all or keeps them all. Probing places filled, empty and maybe marks, so one extra colour cannot carry it: it is a layer orthogonal to the mark, never a fifth entry in `CELL_STATES`. Probe membership lives beside `data-state` (the admin uses `data-probe` on the cell), never inside it, because every selector, save and test keyed on the four state values depends on there being four.

## Declared semantics (CARD-268's, with the public page's differences marked)

The history (`{board, done: [{stroke, before}], undone: [stroke]}`) is the foundation. A probe is a checkpoint in it; membership is DERIVED from history, never stored per cell.

1. **Depth 1.** At most one probe open at a time.
2. **Start.** A Probe control opens a probe at the current history position.
3. **While open**, every mark made (any brush, hint strokes too) belongs to the probe and renders in the probe look, with all four `data-state` looks still distinguishable under it. **On this page a hint stroke exists only once CARD-327 has landed (the dependency).**
4. **Abandon ("contradiction"):** one action undoes back to the checkpoint, the board is exactly as at probe start, the probe closes; redo after an abandon follows the existing history rules.
5. **Commit ("confirmed"/Keep):** the marks lose the probe look and become normal; the probe closes; commit touches no cell.
6. **Undo/redo during a probe** work as today (LIFO). Undoing past the checkpoint clamps it; the probe can shrink to empty and stay open. (CARD-268's review found the checkpoint cannot be a single number: it is the frozen set of strokes the history held on BOTH stacks when it opened. That is already in the shared module; do not re-derive it, and do not "simplify" it back.)
7. **Solved while probing commits. DIFFERS HERE. [RULE 7 CONFIRMED by the owner 2026-11-06: "yes, I agree with the auto-commit", after the orchestrator explained that 'solved' means the WHOLE puzzle (every row and column clue satisfied, the state that already shows the solved banner) and not a single finished line; no longer a default to confirm.]** the admin decides "solved" by comparing against the solution (`isSolved`), which this page does not have. The public page's solved check is `isClueSolved`, an exact clue-satisfaction check that is the same fact for a uniquely solvable puzzle. **Default: a probe whose marks reach the clue-solved state commits, and the solved banner and lock behave exactly as today.** The alternative is that the public probe never auto-commits. Either way `isClueSolved` and the solved banner are READ and NOT TOUCHED (G-3), and the AC for this rule asserts the chosen behaviour with a constructed board.
8. **Counters and circles read the board as it is, probe marks included** (CARD-326's circles: the circle set is `circledClues` of the recorded board, which includes probe strokes, exactly as the admin's does). There is no error count or progress percent on this page.
9. **The save never contains probe strokes.** The public player's save is the FILE'S OWN (`play.js`'s header says it is not `serializeState`), so the checkpoint logic must be applied to ITS save: while a probe is open the stored entry is the entry as of the checkpoint, and a reload resumes at the probe's start with no probe open. The page says so, in one short line, where the probe controls are.
10. **Reset** clears the board, the history and any open probe.
11. **Open/closed is player state** and belongs in the pure module; `play.js` only says which event happened and reads the value through it (ADR-0038/R4).

## What is DIFFERENT on this page, and was not in CARD-268 (the gaps this card must close)

1. **Where the controls live.** The admin has three buttons (Probe, Keep, Contradiction) on the toolbar's last flex line. The owner's ruling for CARD-327's Hint was that its control lives OUTSIDE the toolbar, because the toolbar is one row only from 839 px in landscape, already wraps between about 780 and 838 px (the owner's open F-1 residue from CARD-324), and `tests/test_public_player_zoom.py` reds by design on any new toolbar button. **The same pressure applies here and more (three controls, two of them offered only while a probe is open): the probe controls are NOT children of `.player-toolbar`, `tests/test_public_player_zoom.py` and its pinned bound run UNEDITED and green, and each control is at least 44 px in its touch dimension.** Reuse the placement CARD-327 settles. If they cannot live outside the toolbar, STOP and report.
2. **A fourth mark on a board that already carries three.** The crosshair tints the crossed row and column and their clue boxes (`is-crossed`), the circles draw a ring on clue numbers (`is-circled`, a border on the number's `::before`), CARD-327 adds a hint highlight on a line, and now the probe look lands on CELLS. The admin's probe look is a DASHED OUTLINE and never a ground tint, by the owner's 2026-10-30 decision after its tint measured dE76 2.55 from the crosshair's (the same colour for two small cells); `admin.css` carries the measurement and a channel census. A probed cell that is also crossed and a probed cell under a hinted line must show both; by pixels, tokens only.
3. **The look joins `tests/test_public_player_agreement.py`** (CARD-328's one home): declare any divergence from the admin with its reason and a MEASURED figure, comparing the WHOLE declaration set of the rules (CARD-326's first extractor was default-allow on unlisted properties).
4. **The listener census.** `test_every_player_control_is_in_the_ec_050_walk` censuses every `addEventListener` type and reds on any addition: three buttons use `click`, which the file already registers; if it needs an edit it is a declared SCOPE+ edit (CARD-325's record shows one and why it was judged honest).
5. **Zoom, scroll, pinch.** The probe look must stay legible and in place at the zoom maximum and at a scrolled offset, and a two-finger pinch must neither open a probe nor change one.
6. **`touch-action` stays `auto`** (owner decision 2026-11-05).

## Acceptance criteria

- **AC-1** (marks carry the probe look): *Given* an open probe, *when* marks are made with the filled, empty and maybe brushes (and, once CARD-327 has landed, a rung-3 hint), *then* each cell keeps its normal `data-state` and additionally carries the probe marker, and cells marked before the probe carry none. (test: `TestPublicProbe_MarksCarryTheLook`)
- **AC-2** (abandon): *Given* a probe with N strokes over a pre-probe board B, *when* Contradiction is pressed, *then* the board equals B cell for cell, the probe is closed and no marker remains. (test: `TestPublicProbe_AbandonRestoresTheCheckpointBoard`)
- **AC-3** (commit): *Given* a probe with marks, *when* Keep is pressed, *then* every cell's `data-state` is unchanged, every probe marker is gone and the probe is closed. (test: `TestPublicProbe_CommitKeepsCellsAndDropsTheLook`)
- **AC-4** (undo during a probe): *Given* an open probe, *then* undo pops probe strokes first and their markers clear with them; *given* undo past the checkpoint, *then* the checkpoint clamps, the probe stays open and empty and the next mark belongs to it; and the case CARD-268's review found (a stroke made BEFORE the probe must not come back inside it after a redo) holds. (test: `TestPublicProbe_UndoClampsTheCheckpoint`)
- **AC-5** (depth 1): *Given* an open probe, *then* the Probe control cannot open a second one (disabled, or a no-op with the pressed state unchanged: pick one and test that one). (test: `TestPublicProbe_OnlyOneProbeAtATime`)
- **AC-6** (the save): *Given* an open probe with marks, *then* this page's OWN localStorage save equals the save as of the checkpoint: a reload shows the pre-probe board, no probe open and the pre-probe undo history intact. (test: `TestPublicProbe_AReloadAbandonsTheOpenProbe`)
- **AC-7** (solved while probing; the chosen behaviour of rule 7): *Given* a constructed board and a probe whose marks reach the clue-solved state, *then* the page does what rule 7 says, CONFIRMED by the owner (the probe commits, no marker remains, the solved banner and lock appear exactly as today), with a matched control where the same marks outside a probe solve it. (test: `TestPublicProbe_SolvingCommitsTheProbe`)
- **AC-8** (circles read the board as it is): *Given* probe marks, *then* the circle set equals `circledClues` of the recorded board, probe strokes included, exactly as for the same marks made without a probe. (test: `TestPublicProbe_CirclesSeeProbeMarksAsMarks`)
- **AC-9** (pure module, four states, tokens): *Given* the shipped code, *then* the probe transitions are `solver_state.js`'s (the page defines none of its own), `CELL_STATES` still has exactly today's four members, the look's colours come from tokens, and `solver_state.js` and `tokens.css` are byte-identical to the admin's. (tests: `TestPublicProbe_StateIsThePureModulesAndStatesAreFour`, `test_the_public_probe_look_comes_from_tokens`)
- **AC-10** (the controls are outside the toolbar): *Given* the built page, *then* none of the probe controls is a child of `.player-toolbar`, `tests/test_public_player_zoom.py` and its measured one-row bound run UNEDITED and green, the toolbar's button set is exactly what it was, and each control is at least 44 px in its touch dimension and legible and reachable at the zoom maximum and at a scrolled offset. (test: `TestPublicProbe_TheControlsAreOutsideTheToolbar`)
- **AC-11** (the marks coexist, by pixels): *Given* a probed cell that is also crossed by the crosshair, a probed cell under a hinted line, and a clue number that is circled, *then* each mark is distinguishable from the others and all of them show together. (test: named by the implementation; state it)
- **AC-12** (no answer, no request): *Given* every interaction above, *then* the page holds no solution field, `puzzle/<key>.json` carries exactly the fields it carried before, and the only request is the GET of its own puzzle file. (test: `TestPublicProbe_NoAnswerAndNoRequest`)
- **AC-13** (the look agrees with the admin's): *Given* both sheets, *then* the probe look is held to the admin's in `tests/test_public_player_agreement.py` with every divergence declared with its reason and a measured figure, comparing the whole declaration set. (test: `TestPlayerLooksAgree_TheProbeIsTheSameLook`, in that file)

## Owner decisions this card carries

- **Rule 7 (DECIDED 2026-11-06: auto-commit, confirmed by the owner; this was a stated default and is no longer open):** auto-commit a probe when it reaches the clue-solved state (the clue check is exact for a uniquely solvable puzzle and this mirrors the admin), or never auto-commit on the public page. The owner confirmed it on 2026-11-06 ("yes, I agree with the auto-commit"). WHY it is right, as the owner was told: a hypothesis that reaches the whole solution was correct, because every published puzzle has exactly one solution, so there is nothing left to abandon; and without it a player who finishes the picture inside an open probe would (a) lose the finishing marks on a reload, because rule 9 says the save never contains probe strokes, and (b) still see a Contradiction button that one press would use to undo the entire finished picture. The remaining open item of this section is only the look (a measured question).
- **The look:** the admin's dashed outline is the starting point; whether the public page keeps it exactly is a measured question (AC-13, AC-11), not a taste one.

## Guardrails

- **G-1** — Do not edit `solver_state.js` or `tokens.css`: byte-identical build-time copies (ADR-0041/R3). If the module's probe functions do not give the page what it needs, that is a finding to raise, not a licence to write a second rule.
- **G-2** — Do not touch `src/nonogram/admin/**`: read `solver.js`'s probe wiring, change nothing.
- **G-3** — Do not touch `isClueSolved` or the solved banner: rule 7 READS the solved state, nothing here changes how it is computed.
- **G-4** — No solution reaches the page and no field is added to any served asset (ADR-0041/R2, CARD-283 G-4).
- **G-5** — Marking, Region, undo/redo and reset are untouched; their tests run unedited, except that a stroke made inside a probe is a member of it.
- **G-6** — Styling from tokens only.
- **G-7** — No test deleted, renamed, skipped or merged, `parametrize` ids included (node-id set difference with `-o addopts=`).
- **G-8** — `touch-action` stays `auto`; the toolbar and zoom's pinned bound are unedited (AC-10).
- **G-9** — The probe is never a fifth cell state: `CELL_STATES` has exactly four members (AC-9).

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data (check: AC-12)
- ADR-0041/R3 — the board-state module and tokens are byte-identical build-time copies, never edited (check: AC-9 and `player/assemble.py`'s `COPIED_FROM_ADMIN`)
- ADR-0041/R4 / CON-021 — play state is this browser's localStorage only (check: AC-6)
- ADR-0038/R2 — no network request per mark, probe included (check: AC-12)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: AC-9)
- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R3 — a declared bound carries a reason and a measured residue, written in the test (check: review-lens)

## Lessons the author must be told (from this week's player cards)

Read the Worktree notes of `meta/kanban/cards/CARD-324.md`, `CARD-325.md`, `CARD-326.md` and `CARD-327.md` on `main` first. What cost review cycles or stopped gates: a structural 'reads no solution' scanner must be default-deny on PROPERTY reads as well as identifiers, refuse computed member access and refuse every operator in the code it vouches for; behavioural plants that rewrite the served `play.js` must go through a Playwright ROUTE with a SERVED CANARY; every plant needs a matched control in the same run and the scenario that fired must be asserted, not just that something did; write each declared bound IN THE TEST with its reason, a MEASURED number and a control that fails just past it; the agreement extractor must compare the whole declaration set, not a listed few; a card that adds tests can red a census module it never touches (run `tests/test_suite_profile.py`, `tests/test_impact_set.py`, `tests/test_check_ref_resolution.py`, `tests/test_cli.py`, `tests/test_kanban_review_record.py` and the rest of the standing list; write NO test body with a silent `return`; never add to a frozen registry); and for every `!=` and `not in` you touch, plant its failure.

## Worktree notes

(none yet)
