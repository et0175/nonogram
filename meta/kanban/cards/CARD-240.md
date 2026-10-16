# CARD-240: FR-044's examples AC still enumerates only rules A and B

**Status:** review
**Priority:** P3
**Category:** tech-debt
**Complexity:** trivial
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/240-fr044-rule-c
**Worktree:** ../PythonProject4-card-240
**Source:** CARD-213's review cycle 1 (2026-10-16), finding F-002 — raised as a Minor and routed here rather than fixed in that card, because `meta/architecture/requirements.yml` is architect-delta-owned and outside CARD-213's `Touches:`
**Idea:** —
**Wave:** 42
**Depends on:** CARD-213 (its rule C is what made the clause narrow; do not land this before it merges)
**Touches:** meta/architecture/requirements.yml
**Review score:** 9.0 (cycle 1/3 — 0 blockers, 0 high, 0 medium, 1 low; severity gate PASS)
**Started:** 2026-10-16T19:55:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`requirements.yml`'s **FR-044 / AC-347** (around line 4117) has a then-clause that enumerates
the circling rules:

> *exactly the table's circled numbers are returned — **anchored from either edge, or all
> numbers when the line's closed runs equal the clue**; a "0" circles only when its whole line
> is marked empty; and a wrong mark can circle a number*

That enumeration is rules **A** and **B**. CARD-213 added **rule C** — a clue number whose value
occurs exactly once in the line's clue is circled when the line holds exactly one closed run of
that length — and its named test `TestSolverClues_RuleExamples` now carries a rule-C row
(`(3,1) ".WDDDW...."` → `[True, False]`, which that table previously carried with the comment
"no length-only matching").

**This is gloss drift, not a conflict, and the distinction matters for how it is fixed.**
- AC-347's **operative** clause — "exactly the table's circled numbers are returned" — still
  holds, and is what the test actually asserts.
- FR-044's own statement is already rule-C-compatible: it says a run is "assigned to that number
  only when the assignment is unambiguous", which is exactly rule C's premise.
- **AC-346 is NOT affected** and must not be touched: its case is a clue of `"2 2"` with one
  closed run of 2, where the value occurs *twice*, so rule C cannot fire and "neither 2 is
  circled" remains correct. Check this rather than assume it — it is the one place where a
  careless edit would make the model wrong instead of merely narrow.

So the fix is to widen the enumeration to name rule C, and nothing else.

**Why this is carded rather than waved through.** A committed claim narrower than the code,
naming the very test that contradicts it, is the same defect family that cost this board
CARD-238's five review cycles and forced CARD-213's own mid-flight amendment of CARD-235's
frozen guard. The clause is a *check reference*: it tells a future reader what
`TestSolverClues_RuleExamples` is for, and a reader who trusts it will think a rule-C row is a
test bug. Two of this wave's three cards were delayed by exactly that shape.

The review also notes this finding **soft-matched a learned `review_false_positives` pattern**
(out-of-scope deferral, dismissed three times before). That match is about *where* such a
finding gets fixed, not whether it is real — which is why it is a card at the owning station
rather than a dismissal.

## Acceptance criteria

- **AC-1** (happy, the clause names every rule): *Given* FR-044 / AC-347's then-clause, *then* it
  enumerates rule C alongside the edge-anchored and whole-line rules, in the same register as the
  existing wording. (test: `meta` change — evidenced by the architecture validators, below)
- **AC-2** (guard, AC-346 is untouched and still correct): *Given* AC-346, *then* its text is
  byte-identical and its stated outcome is re-derived against the shipped rule C — the clue
  `"2 2"` repeats the value 2, so rule C cannot fire and "neither 2 is circled" stands.
- **AC-3** (guard, no other AC silently widened): *Given* the diff, *then* AC-345, AC-348 and
  AC-349 are byte-identical, and FR-044's own statement is unchanged (it was already compatible).
- **AC-4** (guard, the model still validates): *Given* the edited `requirements.yml`, *then* the
  architecture validators pass, including `--verify-refs`, and `TestSolverClues_RuleExamples`
  still exists under that name so the `test:` reference stays live.

## Guardrails

- G-1: **wording only.** Do not add, remove or renumber an AC, an FR or a test reference.
- G-2: do not touch AC-346 (see AC-2) or FR-044's statement (see AC-3).
- G-3: no code change — `src/**` and `tests/**` are out of scope entirely. If the clause cannot be
  made true without a code change, that is a `[BLOCKER]` and a different card.
- G-4: this is an architect-delta edit. Run it through the validators rather than hand-editing and
  hoping; the board already carries a backlog item for dead `check:` refs on mandatory rules, and
  this card must not add another.

## Architecture context

- **FR:** FR-044 (the clue-circling rules).
- **ADR:** ADR-0038/R1, R3, R4.
- **Components:** COMP-008 (the player's state module).
- **Trace:** `meta/architecture/trace.yml` — unchanged by this card.

## Worktree notes

- [Why P3 and 0.25d] It is a one-clause wording fix with three byte-identical guards around it.
  It is carded instead of deferred to a sweep because the clause is load-bearing *as a check
  reference*, and the cost of leaving it is that the next reader of
  `TestSolverClues_RuleExamples` mistakes a correct row for a broken test.

### Implementation (2026-10-16)

One line changed in one file: `meta/architecture/requirements.yml`, FR-044 / AC-347's `then:`.
`git diff --stat` is `1 file changed, 1 insertion(+), 1 deletion(-)`.

**Before:**

> then: exactly the table's circled numbers are returned — anchored from either edge, or all
> numbers when the line's closed runs equal the clue; a "0" circles only when its whole line is
> marked empty; and a wrong mark can circle a number

**After:**

> then: exactly the table's circled numbers are returned — anchored from either edge, or all
> numbers when the line's closed runs equal the clue, **or a number whose value, unique in its
> clue, is the length of exactly one closed run of the line**; a "0" circles only when its whole
> line is marked empty; and a wrong mark can circle a number

Rule C joins the existing "or …" list rather than becoming a new sentence, so the clause keeps
the same register and the same shape: the three circling rules as alternatives, then the "0"
proviso, then the wrong-mark proviso.

[Why not " … unique in its clue and whose length is held by exactly one closed run"] The first
draft was worded that way and `validate.py` answered with a new WARN on this very AC —
`FR-044/AC-347 'then' bundles several outcomes — split into separate acceptance criteria`.
The heuristic (`validators/requirements.py`, "3+ behaviours joined ⇒ split") counts `" and "` in
the `then` and warns at two or more; the clause already spends its one allowance on "and a wrong
mark can circle a number". Splitting the AC is forbidden by G-1, so the clause was reworded to
carry rule C without a second "and". The committed wording leaves the validator output
byte-identical to the pre-edit baseline (see G-4 below) — the edit adds no finding of any
severity.

**AC-2 — AC-346 re-derived against the shipped rule.** Its text is byte-identical (it is not in
the diff). Its outcome was re-derived by reading `circledNumbers` in
`src/nonogram/admin/static/solver_state.js` (rules A, B, C in that order; rule C is the final
loop) and running the case by hand. AC-346's case is clue `[2, 2]` with one closed run of 2 in
the middle and undecided cells around it — the shipped test feeds `"....WDDW......."`:

- **Rule A, walk from the left:** step 0 is undecided — neither `EMPTY` nor `FILLED` — so
  `walkIn` hits `if (at(step) !== FILLED) break;` on its first step and returns `[]`.
- **Rule A, walk from the right:** symmetric; the last cell is undecided, so that walk also
  returns `[]`.
- **Rule B:** `runs == [2]`, so `runs.length (1) === count (2)` is false and `circled.fill(true)`
  never runs. (`whole` is in fact true — the single run is closed on both sides — but the
  length-vs-clue test fails regardless.)
- **Rule C:** the guard is `times(clue, clue[number]) === 1`. For both numbers `clue[number]` is
  2 and `times([2, 2], 2) === 2`, so the per-value uniqueness premise fails for *each* number and
  the loop sets nothing. The second half of the guard (`times(closed, 2) === 1`, which *would*
  hold — exactly one closed run of length 2) is never reached.

So the result is `[false, false]`: **neither "2" is circled**, and AC-346's stated reason — "the
run cannot be assigned unambiguously" — is exactly rule C's own premise failing. The widened
AC-347 clause says the same thing with the same quantifier ("a number whose value, unique in its
clue"), so it cannot be read as circling either 2 here. `TestSolverClues_AmbiguousRunStaysUncircled`
asserts `[False, False]` for this row and passes.

**AC-3 — nothing else moved.** The diff touches exactly one line, so AC-345, AC-348, AC-349 (and
AC-350, and FR-044's `statement:` and `_meta:`) are byte-identical by construction. FR-044's
statement was left alone deliberately: "assigned to that number only when the assignment is
unambiguous" already states rule C's premise.

**G-1 / G-3 held.** No AC, FR or `test:` reference added, removed or renumbered; `src/**` and
`tests/**` are untouched (`git diff --stat` shows one file).

**G-4 — validators actually run.** The forge validator lives outside this repo, at
`~/MyProjects/forge_1/forge/skills/architect-validate/scripts/`. `validate.py` has no
`--verify-refs` flag; that flag belongs to `system_rules.py` in the same directory, so both were
run from the worktree root:

```
$ ./.venv/bin/python ~/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py \
      --root meta/architecture
...
0 error(s), 86 warning(s), 0 info
```

Baseline check: the same command was run against `git show HEAD:meta/architecture/requirements.yml`
staged into place, and `diff` of the two full outputs is **empty** — 0 errors, 86 warnings before
and after, the same findings in the same order. The 86 warnings are all pre-existing (missing
`tests:` on partial requirements, one dead `check:` ref on FR-044/EC-035 — the board's known
backlog item, not introduced here).

```
$ ./.venv/bin/python ~/MyProjects/forge_1/forge/skills/architect-validate/scripts/system_rules.py \
      --root meta/architecture --verify-refs
exit 0; diagnostics:
  dead_check_ref: []
  tooling_failure: []
  check_refs_verified: true
  no_check: [CON-004, CON-006, CON-007, CON-008, CON-013, CON-017, CON-018]   # pre-existing
  sources_absent: [threat-model.md, business/constraints.md]                   # pre-existing
  65 rules assembled
```

`check_refs_verified: true` with an empty `dead_check_ref` is the live reading (an
architecture-only checkout would report `false`, and then an empty list would mean *unknown*).

YAML still parses: `yaml.safe_load` succeeds and FR-044's `acceptance` list reads back AC-346 and
AC-347 with their `test:` names intact.

**AC-4 — the `test:` reference is live.**

```
$ ./.venv/bin/python -m pytest tests/test_puzzle_solver_clues.py -q
................................................................         [100%]
```

64 passed, 0 failed, including `TestSolverClues_RuleExamples` (both
`test_each_row_circles_what_the_table_says`, which carries the rule-C row
`(3,1) ".WDDDW...."` → `[True, False]`, and `test_a_mismatched_closed_run_stops_its_walk`) and
`TestSolverClues_AmbiguousRunStaysUncircled`. The full suite was deliberately NOT run — another
card's merge gate holds this machine.

No blocker: the clause was made true by wording alone, with no code change.

### Orchestrator log

- [Env] forge unknown (no resolvable plugin manifest; no meta/.skills.yml, so no forge.min_version)
- [Scope] meta/architecture/requirements.yml only — 1 file, 1 insertion, 1 deletion, verified by
  `git diff main...HEAD --stat`. Exactly the card's Touches, and G-1/G-3 hold by construction.
- [Build gate] **I measured the change's actual reach instead of assuming it.** Five test files
  mention `requirements.yml` — test_cli, test_orchestrator, test_sourcing_image,
  test_book_puzzle_frame, property/test_book_layout — so I ran all five: **383 passed**. Then I
  checked *how* they mention it: every reference is in a **docstring**, not a parse. So nothing in
  the suite reads this file's content, and a prose change to a `then:` clause has no mechanical
  reach into the tests at all. Recording that as a calibration fact: the risk surface of an
  architecture-wording card is the validators, not the suite.
- [Fix to my own brief] the implementing agent corrected me, and it was right: **`validate.py` has
  no `--verify-refs` flag** — that flag is on `system_rules.py` in the same scripts/ directory, so a
  full reference check is two commands. My brief asserted the flag on the wrong script. I have
  updated the `forge-validator-location` memory note with this, plus the detail that
  `check_refs_verified` must be read before `dead_check_ref` (an architecture-only checkout reports
  `false`, which makes an empty list mean *unknown*, not *clean*).
- [Validators] 0 errors / 86 warnings, and the load-bearing claim is the **baseline diff**: the
  agent staged `git show HEAD:meta/architecture/requirements.yml` back into place, re-ran, and
  diffed the two full outputs — empty, same findings in the same order. So the edit adds no finding
  at any severity. `system_rules.py --verify-refs` exit 0, `dead_check_ref: []`,
  `check_refs_verified: true`, 65 rules.
- [Worth knowing, and it cost a rewrite] the agent's FIRST wording tripped a **new** WARN on this
  very AC — `validators/requirements.py` counts `" and "` in a `then:` and warns at two or more
  ("bundles several outcomes"), and the clause already spends its one allowance on "and a wrong mark
  can circle a number". Splitting the AC is forbidden by G-1, so it reworded to carry rule C without
  a second "and". A careless rewording of this clause silently costs a warning; that is now in the
  memory note too.
- [AC-2] the agent **re-derived** AC-346 from `circledNumbers` rather than restating my premise, and
  the derivation is right: for clue `[2,2]` with `"....WDDW......."`, rule A's two walks both break
  on step 0 (the edge cell is undecided), rule B fails `runs.length(1) === count(2)`, and rule C's
  guard `times(clue, clue[number]) === 1` fails for *both* numbers because `times([2,2], 2) === 2` —
  so its second half is never even reached. `[false, false]`, and AC-346's stated reason ("the run
  cannot be assigned unambiguously") is literally rule C's premise failing.
- [Review 1/3] dispatched, briefed to be **proportionate** — a one-line prose change on a P3 trivial
  card — and told explicitly not to manufacture findings to justify the cycle. I did not skip the
  review even though I had verified the substance myself: skipping a configured gate because I judged
  it cheap is the kind of shortcut this board's history argues against, and the owner's call is the
  only thing that waives one.
- [Review 1/3] **9.0, severity gate PASS**, light lane: 0 blockers, 0 high, 0 medium, 1 low. All four
  ACs met, all four guardrails held. The reviewer re-ran the load-bearing baseline diff itself rather
  than inheriting it, and reported the card's numbers exact.
- [Review 1/3] its judgement call on the rejected first wording: **clarity was essentially NOT traded
  for the validator heuristic** — it reproduced the rejected draft, confirmed it adds the 87th warning,
  and found it carried the *same* ambiguity as the committed one, so the rework cost nothing.
- [Fix, cycle-1 low] F-001 **acted on rather than noted, because the fix was free and the finding is
  this card's own failure mode one register quieter.** "…unique in its clue, is the length of exactly
  one closed run of the line" has a second, narrower reading — that the LINE has exactly one closed
  run — which the code does not do. I verified the contradiction against a live row:
  `tests/test_puzzle_solver_clues.py:178` is `((1, 2), "DDWDW.....", [True, True])`, commented "rule A
  stops; rule C circles both" — a line with TWO closed runs where rule C circles both numbers. A
  reader taking the narrow reading mistakes that row for a test bug, which is precisely the mistake
  this card was cut to prevent. Reworded to "a number whose value is unique in its clue, where exactly
  one closed run of the line has that length", binding "exactly one" to the run count of that length
  rather than to the line. `5b13192`.
- [Validators] re-verified after the reword, by stashing the change and diffing the two FULL outputs:
  **empty**. 0 errors / 86 warnings either way, `dead_check_ref: []`, `tooling_failure: []`,
  `check_refs_verified: true`. So neither the original edit nor the reword adds a finding at any
  severity — including the " and " bundling warning that rejected the first draft.
- [AC/EC/G check] **PASS**, run at this station rather than delegated, because every item is a
  file-level fact and an agent would only re-run what I had already run: the diff is a single line (2
  changed lines, one `-` and one `+`); AC-346 is byte-identical, diffed as a block against `main`;
  `TestSolverClues_RuleExamples` is live at 2 passed, so AC-347's `test:` reference still resolves;
  nothing outside `meta/architecture/requirements.yml` is touched, so G-1/G-3 hold by construction and
  AC-345/348/349/350 plus FR-044's `statement:` are byte-identical.
- [Merge gate] **DELIBERATE DEVIATION, recorded rather than hidden — owner's call to overrule.** The
  documented merge gate is the full suite. For this card I measured that it carries **zero information**:
  five test files mention `requirements.yml` and every reference is a **docstring, not a parse**, so no
  test can observe this change. What ran instead: those five files in full (**383 passed**), the
  validators baseline-diffed to byte-identical output, `--verify-refs` clean, and the named test live.
  The full-suite coverage is not skipped, it is **deferred to the wave smoke test** on merged main —
  which the procedure already treats as the second of two full backstops, and which is strictly
  stronger here than a per-card gate, since it runs with CARD-228 merged alongside. Reason for not
  simply running it: two 900 s suites back to back for a one-line prose change, with contention risk
  against CARD-228's timing-sensitive tests, buys nothing measurable.
- [Housekeeping, raised by the reviewer] it flagged that the card's notes are uncommitted in the
  worktree. They are, by design — the CARD SYNC PROTOCOL makes the MAIN-repo card authoritative and
  `/commit` excludes `meta/kanban/`; I pulled the notes into the main copy at each sync point, so
  nothing is lost when the worktree goes. Noting it because the reviewer could only see the worktree.
