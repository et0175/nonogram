# CARD-213: A clue number unique in its line gets circled wherever its run is closed

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/213-unique-clue-circle
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 4: "Solver - if we have only one (unique) option for some number of black cells (e.g. 3 for the set 1 2 3 2 1) and that number is found (we have correct .xxx. sequence), then please place this number (3 in this case) in a circle")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** `circledNumbers`
(`solver_state.js:412`, rules documented at `:369-385`) circles a clue number by
exactly two rules, and states "nothing else circles a number (no matching by
length alone)":

- **Rule A** — walk in from each edge: skip white cells, stop at the end or at
  an undecided cell; at a dark run, stop unless it is **closed** (bounded by a
  white cell or the line's edge on both sides) and its length is the next
  unassigned clue number **from that edge**; then circle that number and walk
  on. The two walks are independent.
- **Rule B** — every dark run of the line is closed and their lengths left to
  right are exactly the clue: every number is circled.

So in a line clued `1 2 3 2 1`, a closed run of 3 found in the middle — with
undecided cells still between it and both edges — circles **nothing**: neither
walk can reach it.

**What changes — rule C.** A clue number whose **value occurs exactly once in
that line's clue** is circled as soon as the line holds exactly one closed dark
run of that length. The deduction is sound without any edge anchoring: if no
other number in the clue has that length, a closed run of that length can only
be that number.

1. Add rule C to `circledNumbers`, next to A and B, and extend the rule
   comment block at `:369` — that block is the specification readers trust, so a
   rule not described there is a rule that will be deleted by a later card.
2. **Uniqueness is per line, per value.** `1 2 3 2 1` → the `3` is unique; the
   two `2`s and the two `1`s are not, and rule C never fires for them (rules A
   and B still can).
3. **Exactly one matching closed run.** If the line holds two closed runs of
   the unique length, the marks are contradictory and rule C circles nothing —
   it must not pick the first or the leftmost.
4. Undecided cells elsewhere in the line are irrelevant to rule C: the run's own
   two neighbours are what "closed" means.
5. A `0` clue (`[0]`) keeps its existing rule (circled only when every cell of
   the line is white) — rule C does not apply to it.
6. The circles are read from the **board and the payload's clues only**, never
   from the solution (ADR-0038/R3), and the state module stays DOM-free
   (ADR-0038/R4) — rule C is pure, like A and B. `solver.js` needs no change:
   `paintCircles` already paints whatever `circledClues` returns.

## Acceptance criteria

- **AC-1** (happy): *Given* a line clued `1 2 3 2 1` with a closed run of three
  dark cells in the middle and undecided cells on both sides of it, *when* the
  circles are computed, *then* the `3` is circled and no other number is.
  (test: `TestSolverClues_UniqueLengthCirclesAnywhere`)
- **AC-2** (edge, non-unique value): *Given* the same clue with a closed run of
  **two** dark cells mid-line and undecided cells either side, *when* the
  circles are computed, *then* nothing is circled — `2` occurs twice. (test:
  `TestSolverClues_RepeatedLengthDoesNotCircle`)
- **AC-3** (edge, two matching runs): *Given* a line clued `1 2 3 2 1` holding
  two closed runs of three, *when* the circles are computed, *then* neither
  circles the `3`. (test: `TestSolverClues_AmbiguousUniqueLengthCirclesNothing`)
- **AC-4** (edge, not closed): *Given* a run of three dark cells with an
  undecided cell on one side, *when* the circles are computed, *then* the `3` is
  not circled. (test: `TestSolverClues_OpenRunDoesNotCircle`)
- **AC-5** (guard, rules A and B): *Given* every case in the existing
  clue-circle test corpus, *when* the circles are computed, *then* the results
  are exactly as before this card, except where rule C adds a circle. (test:
  `test_puzzle_solver_clues.py`, existing cases unchanged)
- **AC-6** (edge, zero clue): *Given* a line clued `0`, *when* some cells are
  white and some undecided, *then* nothing is circled; *when* all are white,
  *then* the `0` is circled (unchanged). (test:
  `TestSolverClues_ZeroClueRuleUnchanged`)
- **AC-7** (property, both axes): *Given* a seeded corpus of boards and clue
  sets (≥ 200 lines, asserted in the test), *when* circles are computed for
  rows and for the transposed columns, *then* the two agree — rule C is
  axis-independent. (test:
  `PropertyTest_SolverClues_RuleCInvariantUnderTransposition`)

## Guardrails

- G-1: Circles are computed from the board and the embedded clues only, never
  from the solution (ADR-0038/R3; test: `TestSolverPage_ShowsTheClues`).
- G-2: The state module stays DOM-free and pure (ADR-0038/R4).
- G-3: The error counter and the solved predicate are untouched — a circle is
  not a correctness claim ("wrong but self-consistent marks can circle a
  number"; tests: `test_puzzle_solver_progress.py`,
  `test_puzzle_solver_percent.py`).
- G-4: Rules A and B keep their current behaviour; rule C only ever adds
  circles (AC-5).
- G-5: Do not touch the clue rendering/DOM — CARD-212 owns that this wave.

## System contract

- ADR-0038/R3 — the player's clues come from the embedded `compute_clues` JSON;
  the client never re-derives them from the solution (check:
  `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — the player's state logic is a pure module with no DOM access
  (check: review-lens)
- ADR-0038/R1 — hand-written JS, no framework or build step (check:
  review-lens)
- CON-021 — interactive play only in the admin panel's player (check:
  review-lens)

## Architecture context

- **FR:** FR-044 (the player) — the clue-circle behaviour CARD-188 built.
- **ADR:** ADR-0038/R1, R3, R4.
- **CON:** CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: `static/solver_state.js`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—
