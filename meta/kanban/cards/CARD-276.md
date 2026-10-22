# CARD-276: Close the door axis for real — anchoring as a fixed point, and the residue CARD-262 declared

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/276-anchoring-as-a-fixed-point
**Worktree:** —
**Source:** CARD-262's owner decision of 2026-10-22 (**declare the axis, land the card**) named this card as the place the closure goes, and CARD-262's AC/EC/G gate added four items that are written down nowhere else. Both are carried below verbatim in substance.
**Idea:** —
**Wave:** —
**Depends on:** CARD-262 (it edits the guard that card declared; do not start before it merges)
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — a hole that moved one level of indirection four times, and was then priced and declared

CARD-262 did not close the door axis. That was the **owner's decision**, not a failure: cycle 2's score
fell 5.7 → 5.2, the stalled check fired, and rather than spend a last cycle with nothing left to certify
it, the owner chose to declare the axis honestly and land the guard's real win — the polarity inversion,
760 of 816 calls refusing with nothing exempted.

**The family, in one sentence, because four gating findings share it:** *the guard keeps claiming a reach
it has not measured.* It has gated CARD-206 cycle 2, CARD-206 cycle 3, CARD-262 cycle 1 and CARD-262
cycle 2, and **each time the hole moved exactly one level of indirection** — a list of shapes → a storage
→ a quantifier over an empty set → one step of alias resolution. This card is judged on whether it
resolves the **level**, not the instance. A fix that closes the current counterexample and leaves the
next indirection open is this family's fifth appearance, and should be recognised as such at review.

**What "one step" means today.** `anchored` holds when *some* binding occurrence of that one name holds a
syntactic `Name`/`Attribute`. The walk never follows the alias. So appending one assignment buys silence
on any shape the arms refuse, and the plainest counterexample crosses CARD-262's **own** rows W1 and W9
with no scaffolding:

```python
_x = getattr(self, "page_" + "spec"); _d = _x
_d(3 + len(section))
first_answer_page = 1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
```

W1 alone refuses. W9 alone refuses. Their cross is **silent**.

## What to implement

### 1. The closure (the card's subject)

Make anchoring **transitive**: anchored only if every binding occurrence holds a `Name`/`Attribute` that
is **itself anchored**, as a fixed point over the `bound` table the arm already builds.

- **Cycles and the recursion bound are REFUSED, never capped.** CARD-262 already moved both depth caps
  from fail-open to raising a reported bound (`RECEIVER_RESOLUTION_DEPTH`), using the pattern the
  vocabulary fixed point 500 lines above has always used. Extend that discipline, do not re-introduce a
  cap.
- **Re-measure the refusal cost the way 760 → 0 was measured**, and publish the new sequence. The
  transitive version will refuse more; the number is the deliverable, not a footnote. CARD-262's
  measured precedent for *how* to choose a shape by cost: one shared opaque table cost **51** refusals
  on a defect-free module while keying on `(storage, spelling)` cost **0**.
- **Delete `ONE_STEP_ANCHOR` when it closes.** Its cost on this module is **0** — the gate re-measured
  that independently — so by CARD-262's own narrowed rule it is a deletable exemption kept alive only by
  its blind-spot rows. Removing the class today costs 0 refusals and **turns six of the seven declared
  plants into refusals**, measured by CARD-262's fix agent. That is this card's cheapest first move and
  its own best control.

### 2. The three declared residues (each currently has a control asserting it is SILENT — closing one must red that row)

- **The one-step-anchor class** — 6 `MEASURED_BLIND_SPOTS` rows (R1, R1b, R2, R4, R5, R7). Closing the
  axis must red `test_the_declared_blind_spots_are_still_silent` on each, which is the point of the
  declaration: it is falsifiable by construction.
- **The VALUE axis** — `POSITION_LITERALS` admits `1` and caps nothing, so `… + len(section) + 1 + 1 + 1
  + 1` passes while three extra front-matter pages are added. CARD-262's implementer called this *"the
  one I would fix first"* and it is still open. `module_integers` also reads only a top-level
  `ast.Assign` of a bare int, so `_HIDDEN_FRONT_MATTER: int = 3`, `= 1 + 2`, an `if`-block constant and
  `len(_FRONT_MATTER_PAGES)` all defeat it.
- **The CALL-GRAPH axis** — a position forwarded past a callee the walk resolves *by name*: an alias of a
  non-door position method, a callback parameter used as a callee, a `*args` forwarder.

### 3. The four items CARD-262's AC/EC/G gate found that exist nowhere else

The gate said plainly these "are not yet written down anywhere". They are now.

1. **Six matrix cells were never fired against the committed bytes.** A concurrent session edited 23
   docstring sites after CARD-262's fix agent certified it, so its matrix ran against `f6d113ed…` while
   the commit holds `55311d7b…`. Fired against the committed bytes since: SHIPPED, N17, N10 (the
   orchestrator's) and the gate's A, B, C, D, E. **Still unfired: N8, N12b, N13, N14, N16, N18.** Those
   six rest on a blanked-constant AST equality plus an identical assert-lineno tuple, not on a re-run.
   **Fire them.** It is cheap and it closes a gap that is currently argued rather than measured.
2. **A claim pointing at a control that does not exist.** The `CALLEE_EXEMPTIONS` docstring at test-file
   **line 2985** still names `:meth:`test_no_callee_exemption_absorbs_a_door_it_must_not`` — a test
   CARD-262's final round **deleted**, replaced by `CALLEE_EXEMPTION_REACH` +
   `test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`. Cosmetic in effect,
   ADR-0039/R1's own family in kind.
3. **`_page_positions`' docstring still opens** *"The walk fails closed on the door axis and on the
   position axis's binding occurrences"*, and its qualifying parenthesis names three open axes without
   naming the axis-2 class; the one-step narrowing arrives 15 lines later in the same docstring. Fix the
   opening sentence, not just the paragraph below it.
4. **Four of the eleven blind-spot rows have no second reading at all** — the two VALUE and the two
   CALL-GRAPH rows. `_page_positions` exposes `doors=`, `follow_terms=`, `door_arms=` and
   `callee_exemptions=` and **no lever for those axes**, so their control asserts silence only, with no
   "caught with the exemption removed" direction. If this card closes either axis, give it a lever and a
   two-directional control; if it does not, say so where the asymmetry is stated.

Also carried: **the MODULE axis's control is a census equality**, so it reds when the census moves rather
than when the walk's reach moves — weaker than the exemption classes' controls, and currently correct but
worth stating if this card touches it.

## Acceptance criteria

- **AC-1** (the level, not the instance): *Given* the transitive fixed point, *then* the W1×W9 cross and
  all six one-step rows are **read or refused, never silent**, and so is a plant built by appending **two**
  further assignments to any of them — the next indirection, which is how this card shows it resolved the
  level. (test: `test_every_door_shape_is_read_or_refused_and_never_silent`, extended;
  `TestDoorAxis_TheNextIndirectionIsNotSilentEither`)
- **AC-2** (cost, published not hidden): *Given* the closure, *then* the refusal-cost sequence is
  re-measured end to end and asserted as an equality, with the transitive step's own number stated — and
  if it is not 0, the sites it newly refuses are enumerated rather than summarised. (test:
  `test_the_callee_exemption_cost_sequence_is_measured`, updated)
- **AC-3** (the declaration is falsified on purpose): *Given* the closure, *then*
  `test_the_declared_blind_spots_are_still_silent` **reds** on every row the closure reaches, and those
  rows are removed from `MEASURED_BLIND_SPOTS` in the same commit as the mechanism that closes them — a
  declaration outliving its hole is the defect this card exists to end. (test: the named test, red then
  updated)
- **AC-4** (`ONE_STEP_ANCHOR` is gone, not retired in place): *Given* the closure, *then* the class is
  **deleted** from `CALLEE_EXEMPTIONS`, `CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` and
  `CALLEE_EXEMPTION_REACH`, and the zero-cost-class equality still reds when emptied. (test:
  `test_a_zero_cost_class_must_absorb_a_blind_spot_row`, unchanged and still green with the class gone)
- **AC-5** (the six unfired cells): *Given* the committed bytes of CARD-262's `ac479658` **and** of this
  card's HEAD, *then* N8, N12b, N13, N14, N16 and N18 are each fired and recorded with the assertion node
  they kill, under a stated instrument domain. (evidence: the card's mutant table; no new test)
- **AC-6** (the prose defects): *Given* the shipped file, *then* no docstring names a test that does not
  exist, and `_page_positions`' **opening sentence** states the reach the walk actually has. (test:
  `test_no_docstring_names_a_test_that_does_not_exist` — a new standing check, derived by AST over the
  module's own `:meth:`/backticked test references, default-deny)
- **AC-7** (equalities stay equalities): *Given* the whole change, *then* `len(sites)`, the vocabulary
  and the guide-counting count still red in **both** directions. (tests: CARD-262's three, unedited)

## Guardrails

- G-1: **No production behaviour change.** `git diff --name-only main...HEAD -- src/` must be **empty**,
  as it was for CARD-262 and CARD-206. This card changes what the guard *sees*, never what the generator
  *does*.
- G-2: Do not edit `src/nonogram/export/layout.py`; keep the three CON-019 byte-identity tripwires green
  **without editing them**.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated; `_refuse_unless_test_database`
  is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: **Do not weaken an arm to make a broader claim true.** The position-axis closure
  (`BINDERS_READ`/`STRING_FIELDS_READ`/`EXEMPTION`, the 8-member `BINDER_BINDINGS` controls) is untouched
  and stays byte-identical unless this card has a measured reason, stated.
- G-6: Take no timing measurements and report no durations.
- G-7: **A cap is not a closure.** If the fixed point needs a bound, that bound **refuses** and reports
  itself, as `RECEIVER_RESOLUTION_DEPTH` already does. Re-introducing a silent cap fails this card
  whatever else it achieves.

## System contract

- **ADR-0039/R1** — a claim needs a control that can fail: caught WITH the mechanism, missed WITHOUT it.
  Four of this family's gating findings were R1 violations (check: `test_the_control_for_each_spelling_depends_on_the_set`)
- **ADR-0039/R2** — a guard's set is derived from an authority the runtime can enumerate; a shape it
  cannot analyse is a **FAILURE, never a silent pass** (check: `test_the_guard_sets_are_derived_and_not_hand_written`)
- **ADR-0039/R3** — every exemption carries a control for what it must NOT absorb, held to an equality,
  with whatever it still cannot see recorded as a measured bound with its own failing control (check:
  `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`)
- **ADR-0036/R2** — book page geometry is computed only by COMP-007's layout functions with the book's
  PageSpec; this is why a geometry **door** is the right authority at all (check: review-lens)

## Architecture context

- **Components:** COMP-009 (`book_pdf_generator.py`) and its test guard. No requirement's verifying test
  changes.
- **ADR:** ADR-0039/R1–R3 are the whole subject; ADR-0036/R2 is the authority the door rests on.
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** in `tests/test_book_export_interior_cover.py` at CARD-262's `ac479658` — run them, do
not rewrite them: `test_every_door_shape_is_read_or_refused_and_never_silent`,
`test_the_declared_blind_spots_are_still_silent`, `test_the_callee_exemption_cost_sequence_is_measured`,
`test_every_callee_exemption_is_read_twice_on_its_own_branch`,
`test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`,
`test_a_zero_cost_class_must_absorb_a_blind_spot_row`,
`test_the_receiver_resolution_bound_is_reported_rather_than_capped`,
`test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them`.
**Resolve their line numbers at start** — this card's own edits will move them.

**To be written by this card** — none exists yet:
`TestDoorAxis_TheNextIndirectionIsNotSilentEither`,
`test_no_docstring_names_a_test_that_does_not_exist`.

## Worktree notes

- **[Use the committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line
  453. Do not write another. Keep deletion mutants **line-count-preserving**, report the **domain** of
  every figure (recording vs re-raising pass; assert-node count vs collected-test count), and prove each
  mutant non-no-op before calling anything a survivor — CARD-262 had three "survivors" that were defects
  in the mutants, and one real survivor it found in a control it had just written.
- **[The strongest evidence on this family has always come from a third party's plants]** Cycles 1 and 2
  each found a Critical via plants chosen by someone other than the walk's author, and CARD-262's AC-3
  control was exactly that. Budget for it: have someone other than the implementer build the plants,
  give them the harness and the tables, and tell them that finding nothing silent is a useful result.
- **[Estimate]** 1d and `architectural` deliberately. The diff will be small; three attempts at this
  family have been small. The owner's wave-50 rule floors a claim card at 0.75d and forbids `trivial`,
  and `architectural` is what makes the pipeline read the ADRs in full and demand a declared failure
  matrix before code — the discipline whose absence escalated CARD-206.
- **[Do not start before CARD-262 merges]** `Depends on` is load-bearing here: this card edits the same
  single file, and CARD-262's merge gate re-verifies its sha.
