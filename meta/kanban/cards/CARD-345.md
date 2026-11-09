# CARD-345: The blind set splits by module co-location, so a new non-branch deadline check *inside* the search module still escapes

**Status:** skipped
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.25d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as I-1 by CARD-278's review cycle 1 (2026-11-04), which certified that card at 8.8 and classed this as Important but non-gating. Carded rather than folded in because CARD-278's own Source cites the wave-48 rule — a widening added after certification ships its final edit uncertified — and because that card's item 4 asked for the standing form to be *proposed*, not built. The proposal was measured and half-delivered; this card is the other half.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-278
**Touches:** tests/test_timeout.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 tech-debt triage. No work is owed here.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The residual, measured by CARD-278's review rather than argued

CARD-278 made `_blind_propagation` derive its blind set from the solver's own call graph, so a
new deadline check in a new function reds the helper instead of escaping it. **That holds for
the propagation side and not for the search side.**

`_propagation_side_deadline_sites` partitions the derived set by **module co-location**: a site
defined outside the search module is blinded; a site defined alongside the search is assumed to
*be* the checkpoint under test. **Co-location is not ownership.**

**Demonstrated red-defeating**, by CARD-278's reviewer, by planting one new
`check_deadline(deadline)` in `solve`'s own prologue — the same *shape* as the original defect,
a non-branch prologue check:

| state | result |
|---|---|
| plant alone, unmutated | **18 passed** — the new control does not notice |
| plant + the four-site branch mutant | **1 failed, 17 passed**, and `test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not` is **green again** |

So the exact defect CARD-278 fixed can be reintroduced by putting the new check one module to
the left. **Re-derive that before implementing** — it is a dated reading and a different result
is the finding.

## The second half: an unguarded premise, true today

The helper asserts that a derived site **is** an attribute of the search module. It never
asserts that **all of that site's reachable callers** are defined there. If a `propagate.py`
function reachable from `solve` ever called `propagate` with a live deadline, the namespace
substitution would leak and nothing would say so.

CARD-278's review measured that it holds today — every caller of `propagate` /
`propagate_overlap` reachable from `solve` (`_lookahead`, `_probe`, `solve`) is defined in
`search.py`. **It is true, not guarded**, which is the distinction ADR-0039/R1 exists to make.

## What to implement

1. **Guard the caller premise, derived not listed.** Assert that every caller of each blinded
   site reachable from the blinding entry point is defined in the search module. CARD-278's
   review states this is cheap and in the same deny shape as the two arms already there —
   **verify that rather than taking it on trust**, and if it is not cheap, say so with the
   measurement.
2. **Decide what to do about the co-location split**, and say which you chose: narrow the
   partition so a non-branch check inside the search module is blinded too (which needs a
   definition of "branch checkpoint" that does not reduce to "lives in `search.py`"), or
   declare the bound as permanent and pin it with a control. **A bound declared without a
   control that can fail is the defect this card family keeps finding** — if you declare, pin.
3. **Also correct `_blind_propagation`'s own docstring, which keeps the singular.** Measured
   by CARD-278's merge gate (its finding 5): the helper's summary line says *"leaving only the
   branch one"* and its body *"only the branch checkpoint can have produced it"*. That is the
   **same defect** the gate's M-2 fixed one function up, and the gate deliberately did **not**
   touch it — M-2 named a specific clause, the card was certified, and widening the edit set
   after certification is what CARD-278's own `Source` warns against. It is one clause, and
   this card already holds the file.
4. **Do not weaken CARD-278's two existing deny arms.** They fire on planted violations today
   (a derived site absent from the search module's namespace; one carrying no `deadline`
   parameter), and both were independently re-fired by its reviewer.

## Acceptance criteria

- **AC-1** *Given* a new non-branch `check_deadline` planted inside the search module, *then*
  something **reds** — either the helper refuses it or a control names it. The plant is the
  one CARD-278's review used (`solve`'s prologue), and the acceptance is that the branch
  checkpoint test no longer goes green under it.
  (test: named by the implementation; state it)
- **AC-2** *Given* the caller premise, *then* it is **asserted and derived**, and planting a
  caller of a blinded site outside the search module makes it **red** (ADR-0039/R1: caught
  WITH, missed WITHOUT).
  (test: named by the implementation; state it)
- **AC-3** *Given* CARD-278's two existing deny arms, *then* both still fire on their planted
  violations, demonstrated — not read as green.
  (test: `test_the_blind_set_is_derived_from_the_solvers_own_call_graph`)
- **AC-4** *Given* `tests/test_timeout.py`, *then* its other tests pass **unedited** — not
  weakened, retargeted or deleted. CARD-278's review measured 17 pre-existing bodies
  byte-identical in `ast`; that property must survive.
  (gate: `tests/test_timeout.py`)
- **AC-5** *Given* any bound this card declares rather than closes, *then* it carries a control
  that can fail, or the card states why none is possible.
  (check: review-lens)

## Guardrails

- **G-1** — No `src/` change. This is a test helper's model of the solver, not the solver.
- **G-2** — Do not weaken the branch-checkpoint test to make the partition tidy. The whole
  point is that it must red without the thing it names.
- **G-3** — No new runtime dependency (ADR-0006/R1); stdlib only.
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.
  CARD-278's G-5 noted the irony and it still applies: a card about a timeout test must not
  measure time. Use the suite's injected clock.
- **G-5** — `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed
  WITHOUT it (check: `test_the_blind_set_is_derived_from_the_solvers_own_call_graph`)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate, not
  hand-written; where none exists it defaults to deny (check: review-lens)
- ADR-0038/R8 — tests fail or skip loudly, never silently; no new skip (check: review-lens)

## RETIRED 2026-11-09 — tech-debt triage

A guard over the test tooling, not the book or the player; under the owner's rule (keep a test only if its claim is a live product decision) it is not worth building.
