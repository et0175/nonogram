# CARD-213: A clue number unique in its line gets circled wherever its run is closed

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/213-unique-clue-circle
**Worktree:** ../PythonProject4-card-213
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 4: "Solver - if we have only one (unique) option for some number of black cells (e.g. 3 for the set 1 2 3 2 1) and that number is found (we have correct .xxx. sequence), then please place this number (3 in this case) in a circle")
**Idea:** —
**Wave:** 42
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py
**Review score:** —
**Started:** 2026-10-16T17:04:17Z
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

**Built** (commit `e107af4` on `card/213-unique-clue-circle`; files:
`src/nonogram/admin/static/solver_state.js`,
`tests/test_puzzle_solver_clues.py` — exactly the card's `Touches:`, no
`SCOPE+` entries, `solver.js` untouched).

Rule C lives in `circledNumbers` next to A and B: the run scan that rule B
already did now also collects the lengths of the *closed* runs, and rule C
circles number *i* when `clue` holds `clue[i]` exactly once and that list of
closed lengths holds it exactly once. Pure, DOM-free, reads only the cells
and the clue (ADR-0038/R3, R4). The rule comment block at the head of the
section describes rule C in full — the uniqueness being per line and per
value, the two-matching-runs refusal, the irrelevance of the rest of the
line, and that the `0` clue is outside it.

One line per AC:

* **AC-1** — `TestSolverClues_UniqueLengthCirclesAnywhere`: five lines,
  including `1 2 3 2 1` with a closed run of three mid-line, circling only
  the 3; its second test is the control showing rules A and B circle nothing
  on any of them, so every circle in the table is rule C's.
* **AC-2** — `TestSolverClues_RepeatedLengthDoesNotCircle`: four sets of
  marks holding one closed run of two circle nothing under `1 2 3 2 1`, and
  the paired test runs the *same* marks under `1 2 3`, where the 2 is
  circled in every row.
* **AC-3** — `TestSolverClues_AmbiguousUniqueLengthCirclesNothing`: four
  pairs; the half with two (or three) closed runs of three circles nothing,
  the half with one circles the 3.
* **AC-4** — `TestSolverClues_OpenRunDoesNotCircle`: five pairs (open right,
  open left, open both, and an open side against the far edge); the open half
  circles nothing, the closed half circles the 3.
* **AC-5** — `TestSolverClues_RuleCOnlyAddsToTheOldTable`: the two examples
  tables' fifteen pre-card verdicts kept as a frozen `BEFORE` snapshot. Rule
  C never turns a True into a False, and changes exactly three lines
  (`(3,1) ".WDDDW...."`, `(1,2) "DDWDW....."`, `(2,1) ".....WDWDD"`), all
  asserted as a set, not a count. Those three rows' expectations in
  `ROWS`/`STOPS` are updated, and each of the two `STOPS` rows gained a twin
  whose clue repeats every value (`(1,1,2,2)`, `(2,2,1,1)`), so rule A's
  "the walk stops" demonstration survives with rule C unable to fire.
* **AC-6** — `TestSolverClues_ZeroClueRuleUnchanged`: `[0]` circles only on
  an all-white line (that row is the control that fails if the `0` branch is
  dropped for rule C), and the last rows read the same marks under `1`, where
  rule C is the only rule that can fire.
* **AC-7** — `test_PropertyTest_SolverClues_RuleCInvariantUnderTransposition`:
  180 boards over three shapes, 4920 lines (asserted `>= 200`); the
  transposed board with its clue sets swapped equals the upright board with
  its axes swapped, every line also matches the Python reference, and the
  corpus is asserted to contain >= 150 lines rule C changes and >= 100 lines
  only rule C circles — so the property cannot hold vacuously.
* **G-4 (property)** — `test_PropertyTest_SolverClues_RuleCOnlyAddsToRulesAAndB`:
  3000 seeded lines; the module equals `_rule_circles` with rule C on, never
  loses a circle `_rule_circles` gives with rule C off, and the corpus is
  asserted to hold >= 500 changed, >= 500 untouched and >= 300 lines whose
  clue repeats every value.
* **G-1 / G-3** — unchanged and re-run green:
  `tests/test_puzzle_solver_page.py` (`TestSolverPage_ShowsTheClues`),
  `test_puzzle_solver_progress.py`, `test_puzzle_solver_percent.py`.

`_rule_circles` is the rule block written again in Python from its prose
(not from the JS), the repo's second-implementation style. It is calibrated,
not assumed: `test_the_reference_reproduces_the_pre_card_verdicts` shows that
with `rule_c=False` it reproduces all fifteen pre-card verdicts of the
committed module.

**Mutation check run by hand** (each mutation applied to the JS, suite run,
then reverted — not committed): rule C taking any matching closed run
instead of exactly one; rule C ignoring clue-value uniqueness; open runs
counted as closed; the `[0]` early return removed; rule C removed
altogether. Every one of the five turns at least one of the new tests red,
and the fifth reds all four AC test classes — the negatives are paired, so
they fail both when the rule fires wrongly and when it does not fire.

**Invariants the card did not name, found while implementing:**

1. *Rule C is sound against the existing brute-force oracle, and that is
   load-bearing.* `test_PropertyTest_SolverClues_NeverCirclesWhatBruteForce
   DoesNot` (CARD-188 AC-1) asserts every circle is one the brute force
   agrees with: number *i* is circled only if run *i* covers the same cells
   in every placement agreeing with the marks. Rule C passes it for a reason
   worth recording — a closed run of dark cells is a maximal filled run of
   that length in *every* agreeing placement, so when the length occurs once
   in the clue, that run is that number in every placement. The test stayed
   green unmodified, including its `brute_only >= 100` count.
2. *Rule C has no ordering check, by design, and it is visible on
   wrong-marks lines.* `(1,2) "DDWDW....."` now circles both numbers even
   though the runs appear in the wrong order (2 then 1). That is the card's
   literal rule and is consistent with "wrong but self-consistent marks can
   circle a number" (G-3) — those marks fit no placement at all, so AC-1's
   oracle never sees them. Two of the three changed `STOPS` rows are of this
   kind. If the owner wants the circle withheld there, that is a later card
   (it would need a left-to-right ordering check across the closed runs), not
   a defect in this one.
3. *Rule C cannot fire on a column from a single fully marked row* — a lone
   dark cell whose neighbours along the other axis are undecided is not a
   closed run — which is why the player-page and zoom tests that count
   exactly the circles of one marked row (`test_puzzle_solver_zoom.py`
   `circled == 2 * numbers`) still hold.

**Suite run before handing off:** `tests/test_puzzle_solver_clues.py` (64
passed), plus `test_puzzle_solver_page.py`, `_marking`, `_maybe`,
`_progress`, `_percent`, `test_cli.py` (exit 0) and `_hint`, `_mirror`,
`_zoom`, `_resume`, `_brush_menu`, `_phone` (130 passed). Nothing under
`meta/` is committed.

### Orchestrator log

- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
- [Scope] src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py — exactly the card's Touches:, no drift, no SCOPE+ entries, solver.js untouched as the card predicted
- [Build gate] review.test_scope is `full` in config.yml, so the cycle gate IS the full suite (no pytest-testmon in this venv — the python-pro recipe explicitly refuses to narrow without it). Run under the repo-level lock meta/kanban/.full-suite.lock, since CARD-228 is active in the same wave.
