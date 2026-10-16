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
**Touches:** src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py, tests/test_browser_fixture_scope.py (amended 2026-10-16 at the decompose station — see the Architecture revision below; this card is the first to add a browser-family test since CARD-235 froze the family, and the freeze cannot be satisfied and the card implemented at the same time)
**Review score:** 9.0 (cycle 1/3 — 0 critical, 0 important, 3 minor; both gates pass)
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

## Architecture revision — 2026-10-16, decompose station

**This section was added after implementation, and it is not a change to what rule C does.**
The implementation is accepted as it stands. What follows is one bounded amendment forced by a
guard this card had no way to anticipate.

### What the gate found

The full-suite gate came back `1 failed, 7499 passed` in 940 s. The one failure is
`tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`,
at `assert len(ids) == 422` — the browser family now collects **434**. This card added ten
browser-driven tests to `tests/test_puzzle_solver_clues.py`, which is one of that family's
twelve files. Nothing is wrong with rule C, and nothing is wrong with the ten tests.

### Why this is CARD-235's guard outliving its own scope, not this card's defect

CARD-235's **AC-2 states its own scope in its own words**: *"no test lost: the collected test
count and every test's node id are unchanged — **this card changes fixtures, never coverage**."*
The guard exists to prove that **CARD-235's diff** changed no coverage. It was committed as a
permanent assertion over the repository instead, so it now reads as "no card may ever add a
browser test again". CARD-213 is simply the first card to try.

This is worth stating generally, for the retrospective's rule-promotion pass, because it is a
*different* rule from the one wave 41 produced and the two are easy to confuse: **a guard
written to prove one card's diff did not change something must not be committed as a standing
repository invariant without restating what it asserts.** Wave 41's rule is about a claim being
wider than its mechanism; this is about a claim being correct but *outliving its subject*.

### The amendment — exactly this, and no more

Nine `422` literals sit in that file and they do **not** all mean the same thing. Eight of them
describe **frozen historical measurements** and are correct as they stand:

- `:485` `test_the_before_is_the_number_the_card_was_cut_on` reads the count out of
  `BEFORE_ARTEFACT`. CARD-217's artefact genuinely recorded 422. **Do not touch.**
- `:503`, `:525` `_failed_bars(saving, 422)` — per-test arithmetic over the two committed
  artefacts, both of which hold 422 tests. **Do not touch.**
- `:800` the committed order record says "422 selected". That is a committed file from
  CARD-235's run. **Do not touch.**
- `:15`, `:42`, `:126`, `:682` prose about the measured saving. Narrow the wording only — "the
  422 the family held **when it was measured**" — because the saving is about the measured
  family. Claim-reducing, so it invalidates nothing.

**Exactly one** `422` is a claim about the family *today*: `:711`, inside the failing test. Two
things are wrong with it and both must be fixed:

1. **It is redundant.** The two assertions immediately below it — `sorted(ids - before) == []`
   and `sorted(before - ids) == []` — already imply `ids == before` and therefore
   `len(ids) == len(before)`. The literal adds no coverage; it only fires first and reports
   `434 == 422` instead of the designed, far more useful `"tests added"` with the list.
2. **It is a snapshot, in a test whose own docstring says it is not one** — *"Compared against
   an independent record, not against a snapshot ... A snapshot regenerated from today's tree
   could only ever agree with today's tree."* A hand-written 422 is precisely a snapshot. This
   is wave 41's family in miniature, in the file that polices the family.

Replace the literal and the two set assertions with a baseline of the shape CARD-238's
retrospective promoted — **CARD-217's recorded set PLUS an explicit, reasoned allowlist of node
ids added since**, each entry carrying the card that added it and why:

- "tests added" must still fire for an **unrecorded** addition. That is the half worth keeping.
- "tests removed" must keep working unchanged.
- The count must be **derived** from `before | allowlist`, never written by hand again.
- The equality must go red in **both** directions: when an unrecorded test appears, and when an
  allowlisted one is removed without being struck from the allowlist. State the derivation in
  the docstring so the claim and the mechanism agree.

The ten node ids this card adds are the allowlist's first entries, attributed to CARD-213.

### Guardrails on the amendment itself

- **GA-1:** do not weaken the guard to make this card pass. Deleting the test, loosening it to
  an inequality, or replacing the set comparison with a count is a refusal, not a fix. If the
  only way through is to weaken it, write `[BLOCKER] guardrail conflict` and stop.
- **GA-2:** do not touch the eight historical `422`s beyond the four prose narrowings named
  above. They describe measurements that already happened.
- **GA-3:** do not re-measure the family or regenerate either artefact. The saving CARD-235
  recorded is not in question here and re-running a profile on this host would disturb its
  provenance — a mistake CARD-238's notes record twice.
- **GA-4:** `tests/test_puzzle_solver_clues.py` and `solver_state.js` are **done**. Do not
  revisit rule C, and do not remove or move any of the ten new tests to dodge the guard.

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

### Amendment — the browser-family baseline (2026-10-16)

**Built** on `card/213-unique-clue-circle`. The diff is confined to
`tests/test_browser_fixture_scope.py`; nothing under `meta/` is committed and
`tests/test_puzzle_solver_clues.py` / `solver_state.js` are byte-identical to
the accepted implementation (verified with `git status` after the controls
below — both files are absent from it).

**What replaced the literal.** `:711`'s `assert len(ids) == 422` and the two
set assertions under it are gone. In their place, in the AC-2 section:

* `ADDED_SINCE_BEFORE` — a `dict[node id, (card, reason)]` of every node id the
  family has gained since `BEFORE_ARTEFACT` was measured. Its doc comment
  states why an allowlist and not a number, quoting CARD-235's AC-2 scope
  sentence, and says what adding or deleting a browser test now costs.
* `_baseline_node_ids(allowlist=None)` — the derivation:
  `_family_node_ids(BEFORE_ARTEFACT) | set(allowlist or ADDED_SINCE_BEFORE)`.
  The parameter exists only so the control can run the same code over an
  altered table.
* `_collection_drift(collected, baseline)` — `{"added": sorted(collected -
  baseline), "removed": sorted(baseline - collected)}`.
* `test_the_family_collects_exactly_what_card_217_measured` now asserts
  `drift["added"] == []` ("tests added"), then `drift["removed"] == []`
  ("tests removed"), then `len(ids) == len(baseline)` **last** — the count is
  `len` of the union, never a literal, and it is asserted after the sets so the
  useful message fires first (the old literal's whole defect was firing first
  with `434 == 422`). Its docstring now states the derivation in full, so the
  "independent record, not a snapshot" claim and the mechanism agree.
* `test_the_baseline_goes_red_in_both_directions` — the control the allowlist
  needed (CARD-238's rule). Four claims over injected sets: an unrecorded
  addition is reported; the entry is what lets a recorded one through (same
  tree, empty allowlist → reported as added); an allowlisted test that
  disappears is caught **with** its entry and clean **without** it; a
  CARD-217-recorded test that disappears is caught under any allowlist; and
  `len(_baseline_node_ids(...))` moves with the table.
* `test_every_allowlist_entry_is_attributed_and_not_already_recorded` — the
  set's hygiene check: `(card, reason)` shape, `CARD-\d+`, a reason of ≥ 8
  words, a node id under `FAMILY_PREFIX`, and not already in CARD-217's record
  (which would double-count in the derived baseline).

**The allowlist holds twelve entries, not ten.** The card's revision section
says ten; the measured delta is twelve (`434 - 422`), and all twelve are from
this card's `tests/test_puzzle_solver_clues.py`. The three not covered by the
card's "ten" wording are the second tests of the AC-1/AC-2 pairs and AC-5's
`test_the_old_table_is_covered` / `test_the_reference_reproduces_the_pre_card_
verdicts` — i.e. the controls the Worktree notes above already describe, which
the prose counted as parts of their ACs rather than as separate node ids. Every
entry is attributed to CARD-213 with its AC and its reason; none was added to
make a number come out.

**Controls actually run** (each mutation applied, run, reverted; none
committed):

1. *Unrecorded addition.* A trivial `test_control_a_unrecorded_addition` was
   appended to `tests/test_puzzle_solver_mirror.py` — a family file this card
   does not own, chosen so GA-4's file was never touched for this.
   `test_the_family_collects_exactly_what_card_217_measured` failed with
   `tests added: ['tests/test_puzzle_solver_mirror.py::test_control_a_
   unrecorded_addition']`. Proves the half of the guard worth keeping still
   fires, and that it fires on any family file, not just the one in the
   allowlist.
2. *Allowlisted test removed, entry left standing.* The twelve lines of
   `TestSolverClues_RuleCOnlyAddsToTheOldTable::test_the_old_table_is_covered`
   were deleted from `tests/test_puzzle_solver_clues.py`. The same test failed
   with `tests removed: [... ::test_the_old_table_is_covered]`. Proves the
   equality goes red in the second direction — an allowlist entry cannot be
   left behind by a deletion.
3. *The same removal with the entry struck.* With the deletion still in place,
   that one `ADDED_SINCE_BEFORE` entry was removed: the class went green
   (4 passed). Proves the removal is **caught with its entry and missed
   without it**, which is what makes striking an entry a deliberate edit rather
   than a side effect. `tests/test_puzzle_solver_clues.py` was then restored
   from a copy taken before step 2 and `git status` confirms it is unmodified.
4. *The derivation itself.* `_baseline_node_ids` was mutated to return
   `_family_node_ids(BEFORE_ARTEFACT)` alone (allowlist ignored). Both the main
   test and the new control failed. Proves the control is not vacuous: it is
   the union that the control is testing, not a tautology over one set.

Whole file re-run after reverting everything: `tests/test_browser_fixture_
scope.py` **25 passed in 44.87 s** (23 before this amendment, +2 new tests).
The full suite was deliberately not run — CARD-228's gate holds the lock and
this file carries timing-sensitive teardown bounds.

**The nine `422`s.** Four prose mentions narrowed, wording only, each
claim-reducing: `:15` ("all 422 tests *the family held when it was measured*"),
`:42` ("every one of the 422 tests the family held *when it was measured* runs
under"), `:126` ("422 *(the family as it was measured)* x (0.327 - 0.028)"),
`:682` ("the 422 browser tests the family held *when it was measured* pay it
once each"). Four left exactly as they were, per GA-2, because each reads a
measurement that already happened: `:485` `test_the_before_is_the_number_the_
card_was_cut_on` (CARD-217's artefact), `:503` and `:525` `_failed_bars(...,
422)` (per-test arithmetic over the two committed artefacts, both of which hold
422 tests), and `:800` the committed order record's "422 selected". One —
`:711` — replaced, as above. Neither artefact was re-measured or regenerated
(GA-3); `BEFORE_ARTEFACT` is read, never written.

**What is *not* falsifiable here, stated rather than left implied.** The
allowlist's *reasons* are prose and only their shape is checked (≥ 8 words, a
card id that matches `CARD-\d+`). No test can tell that a reason is honest, or
that `"AC-1"` in an entry is the AC that test really serves — an entry carrying
a plausible sentence and the wrong AC would pass. The guard asserts the node id
set; the attribution is a review artefact. The one real tripwire behind it is
that an entry can never *hide* a test's disappearance (control 2) and can never
be silently inherited by a different test (any rename shows as both an addition
and a removal), so a wrong entry costs a reviewer's attention and not coverage.
The guard also still says nothing about whether an added test is any *good* —
it was never meant to, and `ADDED_SINCE_BEFORE` does not make it a review gate.

### Orchestrator log

- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
- [Scope] src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py — exactly the card's Touches:, no drift, no SCOPE+ entries, solver.js untouched as the card predicted
- [Build gate] review.test_scope is `full` in config.yml, so the cycle gate IS the full suite (no pytest-testmon in this venv — the python-pro recipe explicitly refuses to narrow without it). Run under the repo-level lock meta/kanban/.full-suite.lock, since CARD-228 is active in the same wave.

### Orchestrator log

- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
- [Scope] src/nonogram/admin/static/solver_state.js, tests/test_puzzle_solver_clues.py — exactly the card's Touches:, no drift, no SCOPE+ entries, solver.js untouched as the card predicted
- [Build gate] review.test_scope is `full` in config.yml, so the cycle gate IS the full suite (no pytest-testmon in this venv — the python-pro recipe explicitly refuses to narrow without it). Run under the repo-level lock meta/kanban/.full-suite.lock, since CARD-228 is active in the same wave.
- [Build gate] cycle 0 attempt 1: **1 failed, 7499 passed, 9 skipped in 940.80s**. The one failure
- [Fix 1] declarations: one bounded fix cycle, diff confined to `tests/test_browser_fixture_scope.py`.
- [Retrospective material] A rule distinct from wave 41's and easy to confuse with it: **a guard
- [Fix 1] verified in the main repo rather than accepted on the agent's report: diff confined to tests/test_browser_fixture_scope.py (+294/-15); the clues file and solver_state.js absent from the fix commit; allowlist parsed with `ast` → 12 entries, all from the clues file, all attributed to CARD-213, shortest reason 19 words; the four prose narrowings present at :15/:43/:128/:685; the four historical assertions untouched at :488/:506/:528/:1079; `assert len(ids) == 422` gone. **The agent corrected my own number and was right**: the revision section said ten new tests, the measured delta is twelve (434 − 422). The three extra are control halves and the two pure-Python tests the first report had folded into their ACs. Nothing was added or removed to make a count work.
- [Fix 1] the one claim the agent declined to make falsifiable, stated rather than buried: the allowlist's *reasons* are prose and only their shape is machine-checked, so an entry with a plausible sentence and the wrong AC would pass. What IS falsifiable is the part that protects coverage — an entry cannot hide a test's disappearance, and a rename shows as an addition and a removal. That is the honest bound, and recording it is the behaviour CARD-238's AC-7 was cut to buy.
- [Build gate] cycle 0 attempt 2 (after Fix 1): **7502 passed, 9 skipped, exit 0 in 902.87s**. The
  arithmetic reconciles: attempt 1 was 7499 passed + 1 failed = 7500 collected-and-run, and the fix
  added exactly the two new control tests. Skips stable at 9 across all three full-suite runs this
  wave (both of CARD-213's and CARD-228's), which is CARD-238's host-state fix holding.
- [Review 1/3] spawned. Briefed on the same two cost rules as CARD-228's reviewer (no full suite,
  mutation runs scoped to the card's own test files) plus one this card needs specifically: a
  concurrent reviewer is active and `tests/test_browser_fixture_scope.py` carries timing-sensitive
  bounds, so any timing failure must be re-confirmed in isolation before being reported. Reporting a
  CPU-contention false red as a finding would be this week's defect family committed by the review
  station itself.
- [Review 1/3] the two questions it was told ARE the review: (1) rule C's soundness, including the
  ordering consequence the implementation agent flagged rather than fixed — a line clued `1 2` marked
  `DDWDW.....` now circles both numbers though the runs sit in the wrong order — and whether the
  general soundness argument holds at the line's edges and for a clue value equal to the sum of
  others; (2) whether the amendment preserved CARD-235's guard, with the allowlist held to CARD-238's
  promoted standard since `ADDED_SINCE_BEFORE` is exactly "a set a guard consults". It was also told
  to verify the Python reference's *calibration* claim, on the grounds that an uncalibrated
  independent reference is worse than none because it still looks like evidence.
- [Review 1/3] **score 9.0**, risk LOW, 0 critical, 0 important, 3 minor. Score gate AND severity
  gate both pass on cycle 1. Report synced to meta/review/20261016T182448Z-CARD-213-cycle1.yml.
- [Review 1/3] the reviewer PROVED rule C's soundness rather than accepting the agent's argument,
  and the proof is the card's most valuable artefact: an independent re-implementation plus its own
  brute-force oracle over **all clues x all mark strings over {D,W,.} for every line length 1..8 —
  63,211 placement-bearing cases, 0 oracle violations**, plus CARD-188's 6000-line safety corpus
  (5068 placement-bearing, 0 violations). It also closed the two edge cases I asked about by
  argument: closure holds at the line's edges, and a clue value equal to the sum of others cannot
  be confused with a merge, because a merge needs the separating cell filled and closure forbids it.
- [Review 1/3] **the ordering question is correctly deferred, and the reviewer settled it with a
  measurement rather than an opinion.** The "misleading circle on impossible marks" family PRE-DATES
  rule C and is dominated by rules A and B: over all lines of length <= 7, marks that fit no
  placement already drew >=2 circles in **941** cases before this card (>=1 circle in 10,347), e.g.
  `(1,1) "DWW"` circles both numbers off a single run via the two independent rule-A walks. Rule C
  adds **226**. So G-3 is not being stretched — it is being exercised at the same character and a
  smaller magnitude than rule A already does, and an ordering check would belong to A and B as much
  as to C. That reframes the owner-facing flag I raised earlier: it is not a new wart this card
  introduces, it is a pre-existing one it slightly enlarges.
- [Review 1/3] mutation: the reviewer ran the agent's five claimed mutants **plus four of its own,
  9/9 killed**, each scoped to the clues file (~4 s per run against ~900 s unscoped), sha256-restored
  after each. Its M7 is the one that mattered — rule A skipping a mismatched run instead of stopping
  — because it proves the card's edits to the `STOPS` table did NOT destroy rule A's demonstration;
  the repeated-value twins work.
- [Review 1/3] on the amendment: **the guard is not weakened, and the fix agent's recorded bound is
  narrower than it claimed.** Five controls run against the real tree, including one the fix agent
  never claimed (G5): a bogus allowlist entry naming a nonexistent test is caught as "tests removed",
  so a fabricated node id cannot be smuggled in and a stale entry cannot sit silently. The
  unfalsifiable residue is only the attribution *text* on an entry whose node id is real — which
  costs reviewer attention, never coverage. All twelve attributions were read against the tests they
  name and all twelve are correct. GA-1..GA-4 all honoured; the four historical assertions are
  **byte-identical**, and `solver_state.js` + the clues file are byte-identical to `e107af4` in the
  amendment commit.
- [Fix, cycle 1 minors] Two of the three minors were in scope and I applied them myself rather than
  spend an agent round trip — commit `a674209`, 64 passed:
  * F-001 the rule comment block now states rule C's ordering blindness, with the 941-vs-226
    measurement as the reason it is a deliberate choice and not an oversight.
  * F-003 AC-7's `assert lines >= 200` became `assert lines == 4920`. The corpus is fully determined
    by its seed and shape list, so an inequality permitted a 24-fold silent shrink; an equality is
    the pattern CARD-238's retrospective promoted, for exactly this reason. The two anti-vacuity
    counts beside it stay inequalities, which is correct — they measure reach, not size.
- [Fix, cycle 1 minors] F-002 was NOT fixed here and that is deliberate: it is a gloss drift in
  `meta/architecture/requirements.yml` (FR-044/AC-347's then-clause enumerates only rules A and B
  while its named test now carries a rule-C row), the file is architect-delta-owned and outside this
  card's `Touches:`. **Carded as CARD-240** (P3, 0.25d, depends on CARD-213). I verified the
  diagnosis before carding it, including the part a careless fix would get wrong: AC-346 is NOT
  affected, because its clue `"2 2"` repeats the value so rule C cannot fire and "neither 2 is
  circled" remains correct. CARD-240's AC-2 guards that byte-identically.
- [AC/EC/G gate] spawned for AC-1..AC-7, G-1..G-5, the two System contract rules, and the
  amendment's own GA-1..GA-4. Briefed to produce its own verdicts rather than inherit the review's,
  to prefer `-k` selection, and to re-confirm any timing failure in isolation before reporting it.
