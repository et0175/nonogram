# CARD-435: A probe keeps quiet until it is asked — the red clues and the flagged Contradiction wait for Hint

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (0.5d) <!-- widened from 2c by the owner's ruling of 2026-11-14: two surfaces, not one. -->
<!-- Basis: paintBroken already derives the whole answer on every commit; the change is gating when it is PAINTED, plus a new trigger on Hint. The cost is the trigger's semantics (see the open point) and keeping the derive-and-rewrite discipline that makes a close or an undo leave nothing stale. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/435-probe-quiet-until-asked
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-435
**Source:** owner's play-test doc "Гра - тест", 2026-11-12, item 4: *"I think we'll remove the contradiction-probing red 'contradiction hint', show it only if we press 'Hint' in the contradiction-probe mode"*. Ruled the same day: **"Both, until Hint"** — no red clues and no Contradiction highlight while probing; pressing Hint reveals both.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_line.py
<!-- Derived 2026-11-12. paintBroken and paintProbe are in solver.js; brokenLines is in solver_state.js and is NOT changed by this card (the derivation stays, only its painting is gated). tests/test_puzzle_solver_probe.py::TestSolverProbe_BrokenLinesAreFlagged owns the subject. The Hint button's own behaviour lives with the hint family — tests/test_puzzle_solver_hint.py is in scope the moment the trigger is decided. Re-derive with scripts/impact_set.py --gate. -->
**Review score:** —
**Started:** 2026-11-14T03:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-410 was the owner's finding of **2026-11-07**: *"Flag broken lines during a probe. When a row or column can no longer match its clue, tint that clue red and gently highlight the Contradiction button."* It was built as asked: `.is-broken` on every clue box of a line the open probe broke, `.is-flagged` on Contradiction while there is one, derived and rewritten on every commit so a close or an undo leaves nothing stale.

Five days of play later the owner wants it silent. The reason is readable from the feature itself: a contradiction probe is a guess the reader is testing, and the page answering *"that guess is already dead"* before they have worked it out removes the deduction they opened the probe to make. The flag is not wrong — it is early.

**This narrows a ruling that is five days old.** Recorded here so the next reader does not read it as drift.

## The open point the implementation must have ruled before it starts

The ruling says the reveal is triggered by **Hint, pressed in probe mode**. Hint today reveals one undecided cell as a stroke. So the trigger is ambiguous in a way that changes the work, and it is **not settled by this card**:

- **A** — in probe mode, Hint reveals the broken lines *instead of* revealing a cell (one button, two meanings by mode).
- **B** — Hint keeps revealing a cell, and *also* paints whatever is broken (one meaning, plus the flag).
- **C** — the flags appear on the first Hint of a probe and then stay live for the rest of that probe (ask once, keep answering).

**Ask the owner before implementing.** A is the most literal reading of their words; C is the one that does not punish a reader who asks early and keeps playing. Do not pick by inference — this card is the record that the question was open, and the answer belongs in its Source line.

## What to implement

1. While a probe is open and Hint has not been pressed for it: no `.is-broken` on any clue box, no `.is-flagged` on Contradiction. The board, the counters and the probe's cell markers are unaffected.
2. On the ruled trigger: the flags appear, derived exactly as they are today.
3. Closing the probe (Keep or Contradiction), undoing past the checkpoint, or a redraw leaves nothing stale and resets the asked/not-asked state — the derive-and-rewrite discipline in `paintBroken` is the thing that makes this safe, so keep it; do not introduce a flag that is only cleared on one path.
4. `brokenLines` in `solver_state.js` is unchanged. This card gates painting, not deriving.
5. The editor still never flags (it has no probe bar), and that stays true without a second code path.

## Acceptance criteria

- **AC-1** (quiet by default): with a probe open and marks that break a line, no clue box carries `.is-broken` and Contradiction does not carry `.is-flagged`. (test: `tests/test_puzzle_solver_probe.py::TestSolverProbe_BrokenLinesAreFlagged`, rewritten — it asserts today's automatic flag, which is the behaviour being withdrawn; it keeps its fixtures and its name.)
- **AC-2** (asking reveals): after the ruled trigger, exactly the clue boxes `brokenLines` names carry `.is-broken`, both twins of a doubled axis, and Contradiction carries `.is-flagged`. (test: the same cell.)
- **AC-3** (nothing stale): closing the probe, and separately undoing past the checkpoint, each leave no `.is-broken` and no `.is-flagged`, whether or not the trigger was pressed. (test: the existing close/undo cells in the same module, extended — they already assert the no-stale property and must keep asserting it through the new state.)
- **AC-4** (no probe, no flag): with no probe open, the trigger paints nothing. (test: the same cell as AC-1.)

**Net test count: 0 added** — `TestSolverProbe_BrokenLinesAreFlagged` and the module's close/undo cells already own this subject.

## Worktree notes
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`. Start gate `decision: gate`; fork point interactive/target tip `6151e876`. Pin, drift and state-table gates not applicable; no dependencies.
- **[Owner ruling 1, 2026-11-14] HINT REVEALS THE BROKEN LINES, NOT A CELL.** The card's `## The open point the implementation must have ruled before it starts` named three readings. The owner chose **A, the literal one**: while a probe is open, Hint changes meaning — it tints the clues the guess has already killed and flags Contradiction, **instead of** revealing a cell. They declined B (Hint keeps one meaning everywhere and additionally paints) and C (ask once, then stay live for that probe). **The consequence this creates, named here so it is handled and not discovered:** a reader inside a probe can no longer get a cell revealed at all until they close it. Hint's accessible name and title must say what it does in probe mode, and `hintCount` must not move for a reveal that revealed no cell — a hint ladder that counts a non-reveal would corrupt the one counter the player reads.
- **[Owner ruling 2, 2026-11-14] BOTH SURFACES, SAME RULE.** The card predates **CARD-442**, which gave the line view its own probe — `solver.js` now toggles `is-broken` on `lineParts.clue` and `is-flagged` on `lineParts.probe.abandon`, a second pair entirely separate from the board's `paintBroken`. The owner ruled the quiet rule applies to **both**, so the same probe cannot behave one way on the board and another in the line view. This **widens the card**: `Touches:` gains `tests/test_puzzle_solver_line.py` (whose `TestSolverLine_ProbesInTheView` is CARD-442's home for this) and the estimate moves 2c → 3c. They declined "the board only" (which the card as written would have delivered) and "line view only".
