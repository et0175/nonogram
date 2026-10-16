# CARD-240: FR-044's examples AC still enumerates only rules A and B

**Status:** in_progress
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
**Review score:** —
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
