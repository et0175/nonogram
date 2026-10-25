# CARD-276: Close the door axis for real — anchoring as a fixed point, and the residue CARD-262 declared

**Status:** done
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
**Wave:** 58
**Depends on:** CARD-262 (it edits the guard that card declared; do not start before it merges)
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** 6.5 (cycle 2/3) — NOT CERTIFIED; merged on a recorded gate decision, AC-1 unmet and AC-5 unverified, both routed to CARD-300
**Started:** 2026-10-24
**Closed:** 2026-10-25
**Actual:** 3.0d
**Merge commit:** f794d5a8
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
  if it is not 0, the sites it newly refuses are enumerated rather than summarised. (**the named verifier does not exist** — corrected 2026-10-24 at the fix
  pre-gate: it is an **assertion inside**
  `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`,
  at `ac479658` and at HEAD. Run and update it there; do not invent a test of
  that name. `check_ref_missing`, the family AC-6 of this very card exists to
  catch.)
- **AC-3** (the declaration is falsified on purpose): *Given* the closure, *then*
  `test_the_declared_blind_spots_are_still_silent` **reds** on every row the closure reaches, and those
  rows are removed from `MEASURED_BLIND_SPOTS` in the same commit as the mechanism that closes them — a
  declaration outliving its hole is the defect this card exists to end. (test: the named test, red then
  updated)
- **AC-4** (`ONE_STEP_ANCHOR` is gone, not retired in place): *Given* the closure, *then* the class is
  **deleted** from `CALLEE_EXEMPTIONS`, `CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` and
  `CALLEE_EXEMPTION_REACH`, and the zero-cost-class equality still reds when emptied. (**the named verifier does not exist** — same correction: it is an
  **assertion inside**
  `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`.
  The zero-cost-class equality must still red when emptied, asserted there.)
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
`test_the_declared_blind_spots_are_still_silent`, `test_every_callee_exemption_is_read_twice_on_its_own_branch`,
`test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it`,
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

## [DISPATCH 2026-10-24 — wave 58, orchestrator]

Fork point **`cef9f619`** (main). Worktree `../PythonProject4-card-276`, branch
`card/276-anchoring-as-a-fixed-point`, `.venv` symlinked so the configured
`./.venv/bin/python -m pytest` works verbatim.

**Dependency satisfied, for once without an override.** `Depends on: CARD-262`,
and CARD-262 is `done` at `faea50a5`. Its note — *"this card edits the same
single file, and CARD-262's merge gate re-verifies its sha"* — is honoured: this
dispatch is after that merge, not around it.

**Dispatched in parallel with CARD-282 on the owner's instruction, and the
conflict graph agrees** rather than being overridden. `Touches` intersection is
**empty**: this card edits exactly `tests/test_book_export_interior_cover.py`;
CARD-282 touches `src/nonogram/admin/{player_bundle.py,app.py}`,
`templates/book_detail.html` and `tests/test_player_bundle.py`. No declared
`conflict.hotspots` entry is shared. They are genuinely concurrent, not
serialized-in-the-same-wave.

**One cost interaction the owner should know is real, and it runs the other
way.** CARD-282's *impact set* contains this card's file, because 75 test files
import the admin app — **563.58 s over 2,942 tests, 39.5 % of a 1426.16 s
suite** — and **344.29 s of that 564 s, 61 %, is this one file.** So CARD-282
pays this file's cost on every cycle while this card is still in flight. That is
not a conflict and needs no serialization; it is the measured reason CARD-287
exists, and the reason the owner was given the option of ordering 287 first.

**The cross-card obligation CARD-287 is waiting on, restated here because it is
cheap now and expensive later.** CARD-287 asks this card to **record this
class's per-test durations before and after its change**. The class is
**95.3 % (327.94 s) of the file at 14,258 ms/test**, and CARD-287 is sized
against it. Take the measurement; G-6 forbids reporting *durations as this
card's claim*, and this is a different thing — a datum handed to a successor,
recorded as such. If the two obligations seem to collide, record the figure and
say that G-6 governs the card's own claims rather than a successor's input.

### Correction, same day — I under-reported this card's gate by 16 %

The 39.5 % figure above came from **my grep** for admin-app importers (75 files,
563.58 s). The **committed tool** disagrees and is right: `scripts/impact_set.py
src/nonogram/admin/app.py` reports **98 files = 654.16 s over 5,739 tests =
45.9 %** of a 1426.16 s suite. Its own docstring says why — it prints "a
superset", and it includes unconditionally the ~22 tests that **scan the tracked
tree** (`git ls-files`, `git grep`, `rglob`) rather than importing what they
judge, which no import-graph grep can see.

So **five gate runs is ~55 minutes, of which ~29 is
`tests/test_book_export_interior_cover.py` alone** (344.29 s, **52.6 % of the
impact set**). The decision does not change; the number it was taken on was
light, and a figure is a claim whose control is recomputation — through the
project's own instrument, not a grep that approximates it.

**And the reason CARD-274 would not have helped, measured 2026-10-24 when the
owner asked whether to run it first:** the gate cost comes from tests importing
`nonogram.admin.app` **itself** — 82 `from nonogram.admin.app import`, 10
`import nonogram.admin.app`, 8 `from nonogram.admin import app`, and **zero
naming a route module**. After the blueprint split `app` still imports the
blueprints, so a change to `routes/book.py` keeps `app` in its
reverse-dependency closure and this set does not shrink. **The split moves code,
not the import graph the gate reads.**
## Worktree notes — implementation round (2026-10-24)

**One commit, `tests/test_book_export_interior_cover.py` only.** `git diff
c2cb8e3e..HEAD -- src/` prints **nothing**; so does the working-tree form
`git diff c2cb8e3e -- src/`. G-1 holds. `git status --short` is exactly
`M tests/test_book_export_interior_cover.py` plus the pre-existing untracked
`.venv` symlink.

### Line numbers of the named tests, resolved at start (pre-edit)

`test_every_door_shape_is_read_or_refused_and_never_silent` :3513 ·
`test_each_door_axis_arm_catches_a_shape_the_other_misses` :3556 ·
`test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them` :3607 ·
`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost` :3816 ·
`test_each_door_reaching_shape_is_refused_by_the_mechanism_that_refuses_it` :3881 ·
`test_every_callee_exemption_is_read_twice_on_its_own_branch` :3922 ·
`test_the_receiver_resolution_bound_is_reported_rather_than_capped` :3977 ·
`test_the_declared_blind_spots_are_still_silent` :4551.

**Two names in the dispatch brief's "already exist, do not rewrite" list do not
exist**, at `ac479658` or anywhere else:
`test_the_callee_exemption_cost_sequence_is_measured` (AC-2) and
`test_a_zero_cost_class_must_absorb_a_blind_spot_row` (AC-4). Both are
**assertions inside** `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`
— the cost-sequence equality and the zero-cost-class equality. AC-2 and AC-4
name them as tests, so the card and the brief share the error. They were run and
updated as assertions of that one test.

Also: the brief says this worktree's copy of the card is frozen and missing
`[DISPATCH]`. It is not — it is byte-identical to main's (both at `57559af5`).

### 1. The closure — `anchored_to_a_fixed_point`

`anchored` was a one-step syntactic property. It is now a **fixed point** over
the `bound` table the arm already builds: a key is anchored only if **every**
binding occurrence of it holds a `Name`/`Attribute` that is **itself** anchored,
followed until the chain reaches a binding this module's own text shows — a
`def`, a `class` or an `import`. One helper, `anchor_refusal`, serves both the
`ast.Name` and the `ast.Attribute` branch, so the two storages cannot drift
apart again (CARD-262's row R2 was exactly "the sibling copy of the `anchored`
check").

Two deliberate **non**-terminals, both the fail-closed direction: a **parameter**
is not a terminal (its callers are the call-graph axis) — which is what refuses
R4 and R5 — and a key with **no** binding occurrence at all is not anchored.

**Cycles and the bound REFUSE, never cap (G-7).** `AnchorNotAFixedPoint` is
raised by the cycle check (`key in chain`, checked first, because it is the more
precise report) and by `ANCHOR_RESOLUTION_DEPTH` — 4, the same value and the same
discipline as `RECEIVER_RESOLUTION_DEPTH`, whose F-503 pattern this extends. The
call loop turns either raise into a refusal naming the call. The bound's cost on
this module is **0**, asserted.

**Why passing a resolved chain is safe, and why that is the claim's edge.** A
geometry door cannot stand at a `def`/`import` terminal without being
**spelled**, and a spelled door referenced rather than called is refused by the
pre-existing reference arm — measured as `CHAINS_THAT_RESOLVE` row E2. That table
is the ADR-0039/R1 **edge** control: a blanket refusal of every anchored callee
closes every counterexample below and is a cap, not a closure. Mutant M2 is that
cap, and it reds 3 cells.

### The plant table (all measured, `_outcome` over the planted module)

| plant | shape | before | after |
|---|---|---|---|
| W1 alone | `getattr(self, "page_" + "spec")` called directly | refusal | refusal |
| W9 alone | `_m = getattr(...); _m2 = _m` | refusal | refusal |
| **W1 × W9** (R1b) | `_x = getattr(self, "page_" + "spec"); _d = _x` | **silent** | **refusal** |
| R1 | the same with the suffix in a module name | **silent** | **refusal** |
| R2 | the same in the attribute storage | **silent** | **refusal** |
| R4 | door held by a constructor parameter | **silent** | **refusal** |
| R5 | door forwarded as a parameter, aliased once | **silent** | **refusal** |
| R7 | two-step alias chain | **silent** | **refusal** |
| CALL-GRAPH alias row | `_f = self.puzzle_pages; _f([], 3 + len(section))` | **silent** | **refusal** |
| **I2** TWO further assignments, locals | `_x = getattr(...); _y = _x; _z = _y; _d = _z` | silent | **refusal** |
| **I3** TWO further assignments, attributes | `self._x = getattr(...); self._y = self._x; self._z = self._y` | silent | **refusal** |
| I4 | a chain crossing both storages | silent | **refusal** |
| I5 | R4 + two more links (`_h.door` → `_m` → `_d`) | silent | **refusal** |
| I6 | R5 + two more links inside the forwarder | silent | **refusal** |
| I7 | the call-graph alias row + two more links | silent | **refusal** |
| E1 | a four-link chain onto a module-level `def` | resolved | **resolved** (no plant refusal) |
| E2 | the same onto an imported door | refusal (reference arm) | **refusal (reference arm)**, named |
| cycle | `_p = _q; _q = _p` | n/a | **refusal naming the cycle** |
| 5-link chain past the bound | `_a = … ; _e = _d2` onto a `def` | n/a | **refusal naming the bound** |
| 4-link chain inside the bound | one link shorter | n/a | **resolved** |

The six R-rows and the W1×W9 cross are `DOOR_SHAPES`' **W30–W35** now, where a
silent outcome is forbidden rather than recorded; the call-graph alias row is
`CHAINS_THAT_MUST_NOT_BE_SILENT`' I7. All 36 `DOOR_SHAPES` rows come back
`("refusal",)`.

### 2. The refusal-cost sequence, re-measured end to end

```
  760  ()
  509  ('builtins',)                                           step 251
  203  (… 'definitions and imports')                           step 306
  201  (… 'parameters')                                        step   2
    0  (… 'an attribute of a receiver this module does not define')  step 201
```

`ONE_STEP_ANCHOR`'s row is **gone**, and the **transitive step's own number is
0**: the shipped walk reports `sites=23, vocabulary=6, refusals=0`, identical to
the base. Not one of this module's 816 calls reaches a callee key with an
`anchored` binding occurrence at all — `unreadable` and `opaque` run first and
catch every one — so following the chain further cannot refuse what stopping did
not. Nothing is newly refused, so there is nothing to enumerate. Every remaining
class strictly drops the count, so
`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` is **empty** again.

### 3. `ONE_STEP_ANCHOR` deleted, with the cell counts

Deleted from `CALLEE_EXEMPTIONS`, `CALLEE_EXEMPTION_COST`,
`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` and
`CALLEE_EXEMPTION_REACH` (AC-4). Cost of the deletion on this module: **0
refusals** (0 → 0). Blind-spot cells before: **11 rows, all `()`**. After:
**4 rows, all `()`** — two VALUE, one CALL-GRAPH (parameter used as a callee)
and R3 (the external-attribute class). The seven that left came back
`('refusal',)`.

### 4. The declaration reds (AC-3)

`test_the_declared_blind_spots_are_still_silent`, run against the mechanism with
CARD-262's table restored verbatim, red on its own silence equality and named
every row:

```
('the CALL-GRAPH axis: an alias of a non-door position method', ('refusal',))
("the ONE-STEP ANCHOR: the cross of this card's own W1 and W9 (R1b)", ('refusal',))
('the ONE-STEP ANCHOR: an assembled name aliased once (R1)', ('refusal',))
('the ONE-STEP ANCHOR: the same in the attribute storage (R2)', ('refusal',))
('the ONE-STEP ANCHOR: a door held by a constructor parameter (R4)', ('refusal',))
('the ONE-STEP ANCHOR: a door forwarded as a parameter and aliased once (R5)', ('refusal',))
('the ONE-STEP ANCHOR: a two-step alias chain (R7)', ('refusal',))
```

The two VALUE rows, the parameter-callee row and R3 stayed `()`. All seven rows
left `MEASURED_BLIND_SPOTS` **in this same commit** as the mechanism that closes
them.

### 5. The six unfired cells (AC-5)

**Domain for every figure below:** the committed `tests/kill_matrix.py`;
`Pass.RECORDING`; `ast.Assert` **node** counts, never collected-test counts;
child instrumentation **off**; ANY-RED aggregation; every mutant
line-count-preserving; `SHIPPED` re-run between mutants and FAIL-free each time;
pytest exit **0** on every mutant while the matrix recorded FAIL cells — a
test-level reading would have published all of them as survivors. Selection was
targeted (not the whole file), so a cell outside the selection reads
`NOT-REACHED` by construction; that is a stated bound, not a survival.

**Against `ac479658`'s committed bytes** (`55311d7b…`, byte-identical to
`c2cb8e3e`'s copy — so the thing CARD-262's matrix never ran against):
6 mutants, 184 assertion nodes, SHIPPED 0 FAIL of 20 reached, 5 tests selected.

| cell | mechanism DELETED | FAIL | nodes | vs CARD-262's claim |
|---|---|---|---|---|
| N8 | the one-step gate in the `ast.Attribute` branch | **1** | :4631 (`test_the_declared_blind_spots_are_still_silent`, the absorbed-row reading) | **claimed 2** (:4604 + :4631). :4604 **PASSes**: neutering the attribute gate leaves the attribute-storage rows silent, which is what that equality already expects. CARD-262's cell count for N8 was one cell too high |
| N12b | the class's membership of `CALLEE_EXEMPTIONS` | **5** | :3866, :3941, :3967, :4591, :4604 | matches exactly |
| N13 | the cross row's silence (`_d = _x` → `_d = _x()`) | **1** | :4604 | matches |
| N14 | the derived idiom authority (`set() | set()`) | **2** | :4214, :4220 | matches |
| N16 | `_plant_refusals`' attribution window | **1** | :3967 | matches |
| N18 | the own-instance surface rule | **1** | :3913 | matches |

**Against this card's HEAD:** 5 mutants, 196 assertion nodes, SHIPPED 0 FAIL of
27 reached, 16 tests selected.

| cell | mechanism DELETED | FAIL | nodes |
|---|---|---|---|
| N8h | the **fixed-point** gate in the `ast.Attribute` branch | **1** | :5080 (`test_a_chain_of_any_length_…`, the parametrised chain assertion — I3 is the attribute-storage chain) |
| N13h | the W30 row's plain alias (`_d = _x` → `_d = _x()`) | **0** | — **declared no-op, with proof**: `_x()` binds `_d` to an expression, so the `opaque` branch refuses it where the fixed point refused the alias. Both forms refuse, so the row's declared outcome cannot move. The mutant changed the file (the instrument verifies `old` is present) and changed nothing observable, which is itself the evidence that the **closure**, not the row's exact text, is what refuses it. Not a survivor |
| N14 | same as above | **2** | :4461, :4467 |
| N16 | same as above | **1** | :4214 |
| N18 | same as above | **1** | :4160 |

N12b has **no HEAD analogue**: the class it removes from the list no longer
exists. That is this card's AC-4, not a gap.

### 6. This card's own mutant table — each DELETES a mechanism its claims name

Same domain as above. Batch A selection: the new door-axis class +
`test_every_door_shape_is_read_or_refused_and_never_silent`. Batch B selection:
the prose class + `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`.

| mutant | the mechanism it DELETES | FAIL | nodes red | nodes passing |
|---|---|---|---|---|
| M1 | the fixed point's recursion — one step again | **3** | :3773, :3786 (the `DOOR_SHAPES` outcome equality and the all-rows-refuse count), :5080 (the chain table) | the resolve/cycle/bound readings, which a one-step anchor also satisfies |
| M2 | the **terminal** rule — every anchored callee refuses (a cap) | **3** | :5107 (`CHAINS_THAT_RESOLVE`), :5171, :5182 (the bound's "inside resolves" and "raised past it resolves") | :5080, :3773, :3786 — a cap closes every counterexample, which is exactly why the edge needed its own control |
| M3 | the cycle check | **1** | :5126 | the rest; a cycle then hits the depth bound and reports the wrong mechanism |
| M4 | the bound's raise → `return True` (the F-503 fail-open cap) | **1** | :5165 | — |
| M5 | the zero-cost-class equality, in the "listed but paying" direction | **2** | :4113, :4120 | — |
| M6 | the reference scan (`findall` → `()`) | **3** | :5313, :5373, :5382 | — |
| M7 | the authority's `test_` derivation (`startswith("")`) | **1** | :5347 | — (see below) |
| M8 | the one shared resolution (`missing` → `[]`) | **1** | :5382 | — (see below) |

**The instrument found a real survivor in a control this card had just written,
which is the point.** In the first draft of `TestGuardProse_EveryNamedControlExists`,
**M7 survived with 0 FAIL of 10 reached at exit 0**: the control computed its own
missing-name list instead of exercising the one the check uses, and asserted only
that the authority was *large*. So widening the derivation to every `def` in
`tests/` changed nothing any assertion read — and the obvious sibling mutant,
`missing = []`, would have survived both tests for the same reason. Closed by
one shared `_unresolved()` classmethod plus
`test_the_authority_holds_tests_and_only_tests`, which asserts the authority's
**membership** in both directions (a test of this class is in it; `_plant`, a
helper of this very module, is not). Re-fired: **M7 reds 1, M8 reds 1.**

**Not measured, declared:** `test_each_door_axis_arm_catches_a_shape_the_other_misses`
was outside every mutant selection because it costs 99 s per reading. Its tables
were re-measured directly instead (below), and no mutant cell is claimed in it.

### 7. What moved in the per-arm tables

`SILENT_WITHOUT_THE_DOOR_ARMS`: 24 of 30 → **30 of 36** (the six new rows are all
silent with both arms removed). `kept` is still **6**.

`SILENT_WITHOUT_ONE_ARM` moved, and the move is the measurement: W9's chained
alias used to be the **door-spelling** arm's own row, silent with the callee arm
alone. The fixed point refuses it too, so it is carried by both arms and is in
neither list. The callee-identity arm's list goes 17 → **23** rows; the
door-spelling arm's goes 2 → **1** (W19's `import … as` rename). One row is
enough for the per-arm claim, and the docstring now says plainly that if W19's
`alias` clause were ever deleted that arm would have nothing exclusively its own.

### 8. The prose defects (AC-6)

* `_page_positions`' **opening sentence** now states the reach the walk has:
  closed on the whole door axis (identity to a fixed point, spellings over the
  grammar) and on the position axis's binding occurrences only; module, value
  and call-graph open by declaration; four exemption classes, one of which
  absorbs a door-reaching shape (R3). The old sentence claimed "the door axis
  and the position axis's binding occurrences" and left the one-step narrowing
  fifteen lines below it.
* The `CALLEE_EXEMPTIONS` attribute doc no longer names the control CARD-262's
  final round deleted. The dead name is not re-spelled anywhere, because the new
  standing check would (correctly) red on it.
* `test_no_docstring_names_a_test_that_does_not_exist` is that standing check:
  references are read from the module's **docstrings (`ast`) and comments
  (`tokenize`)**, because the defect lived in a `#:` attribute doc that no
  docstring walk sees; marked-up and anchored, so `tests/test_x.py` in prose is
  not mistaken for a claim about a control; resolved against every `def test_*`
  under `tests/` (5,149 names). It finds **17** references in this module, all
  resolving. Fired as a control: re-inserting the dead name makes it red by
  name.

### 9. Axes NOT closed, and where the asymmetry is stated

The **VALUE** and **CALL-GRAPH** axes are untouched, and the **MODULE** axis
too. `POSITION_LITERALS` still admits `1` and caps nothing, and
`module_integers` still reads only a top-level `ast.Assign` of a bare int. The
call-graph axis is **narrowed and not closed**: the fixed point refuses a chain
it cannot resolve, which is not the same as resolving the call graph, and the
parameter-used-as-a-callee row still witnesses the axis.

The asymmetry the CARD-262 gate asked to have stated is now stated in three
places: on `MEASURED_BLIND_SPOTS` ("three of the four remaining rows have no
lever… CARD-276 closed neither axis and so built neither"), in
`test_the_declared_blind_spots_are_still_silent`'s docstring, and in the class
docstring's axis table. The **MODULE** axis's control is still a census
equality, which reds when the census moves rather than when the walk's reach
does; this card did not touch it and says so here rather than silently
inheriting the claim.

### 10. CARD-287's duration datum (recorded as a successor's input, not as a claim)

G-6 forbids this card from building a claim on a duration, and nothing above
rests on one. The figure is recorded because CARD-287 is sized against it.
Domain: `./.venv/bin/python -m pytest tests/test_book_export_interior_cover.py
--durations=0`, one file, `-p no:randomly`, same host, uncontended; "before" run
in the main checkout at `c2cb8e3e` (file sha `55311d7b…`), "after" in this
worktree.

* guard class, 23 collected tests: **340.02 s → 335.18 s** (the 20 tests with a
  recorded `call` duration; 3 are under pytest's 0.005 s cutoff)
* whole file: **354.89 s → 387.75 s** (90 → 103 collected tests); the +32.9 s is
  the two classes this card adds, which measure 36.73 s over 13 tests
* the shape inside the class, which is what CARD-287 will care about: the six
  moved rows took cost **out** of
  `test_the_declared_blind_spots_are_still_silent` (43.38 → 12.75) and put it
  into `test_every_door_shape_is_read_or_refused_and_never_silent`
  (68.77 → 85.18) and `test_each_door_axis_arm_catches_a_shape_the_other_misses`
  (83.66 → 99.21), which reads each row three times. Net for the class ≈ 0; the
  file grows by the new classes.

### 11. Plant shapes NOT tried, so a third party's pre-gate plants go somewhere new

A chain through a **container** (`_t = [getattr(...)]; _d = _t[0]`); through a
**comprehension** target; a chain one link of which is a **walrus**; a chain
through a `with … as`; a chain whose terminal is a **parameter default**; a
chain built in a **loop body** so the same key has two anchored occurrences with
different targets; a **cross-class attribute spelling collision** (two classes
spelling `self._d`, one resolving and one not — reasoned to fail closed because
`opaque` runs before the fixed point, but **not executed**); a chain through a
**decorator**; `__getattr__`/metaclass-provided attributes; a `*args`
forwarder; a callback parameter used as a callee (declared open); anything
crossing a **module** boundary (declared open); and any plant on the VALUE axis
beyond the two already declared. Finding nothing silent in those is a useful
result and should be recorded as one.

### 12. Every mutant figure above was fired against the bytes this commit holds

The defect CARD-276 AC-5 exists to end is a matrix that ran against bytes other
than the commit's. So after the last edit to the file — the M7/M8 fix in the
prose class — the AC-5 HEAD batch and batch A were **re-fired** against the
final bytes, `4a2a28eb…`:

* AC-5 HEAD: 5 mutants, 198 assertion nodes, SHIPPED 0 FAIL of 27 reached;
  N8h 1 FAIL (:5080), N13h **0 FAIL** (the declared no-op), N14 2 (:4461,
  :4467), N16 1 (:4214), N18 1 (:4160) — cell for cell what the earlier run
  measured.
* Batch A: 4 mutants, 198 nodes, SHIPPED 0 FAIL of 12 reached; M1 3 (:3773,
  :3786, :5080), M2 3 (:5107, :5171, :5182), M3 1 (:5126), M4 1 (:5165).
* Batch B was already fired after that fix (4 mutants, M5 2, M6 3, M7 1, M8 1).
* The `ac479658` batch ran against `55311d7b…`, that commit's own file bytes,
  verified by `shasum` before and after.
* The file was restored from a pristine copy kept **outside** the worktree after
  every mutation run, and the restore verified with `diff -q` and `shasum -a
  256` each time, never with `git checkout`.

**Final verification run, this commit's bytes:**
`tests/test_book_export_interior_cover.py` — **104 passed**, 0 failed, 0
skipped, 375.38 s. `tests/test_suite_profile.py tests/test_guard_integrity.py` —
**572 passed** (the frozen render-set grep among them, which this file is in).
`tests/test_kill_matrix.py` green in an earlier combined run (648 passed with
those two). No full-suite run was taken and
`meta/kanban/.full-suite.lock` was never written; CARD-282 was concurrent in
`../PythonProject4-card-282` throughout.

## [FIX PRE-GATE on `ced5e648` — 2026-10-24, orchestrator] PASSED, with one bound to declare and two card defects to fix

### The plants — six shapes the round declared untried, all executed, all refuse

This family's whole history says the evidence comes from someone other than the
walk's author: cycles 1 and 2 of CARD-262 each found a Critical via third-party
plants. So the round was asked to list what it had **not** tried, and did. I ran
six of them, driving `_plant`/`_outcome` directly rather than through the 393 s
file:

| orchestrator plant | outcome |
|---|---|
| P1 chain through a **container** — `_t = [getattr(self, "page_" + "spec")]; _d = _t[0]` | **refusal** |
| P2 chain through a **comprehension** target | **refusal** |
| P3 a **walrus** link — `_d = (_w := _x)` | **refusal** |
| P4 **loop body**: one key, two anchored occurrences with different targets | **refusal** |
| **P5 cross-class attribute spelling collision** — two classes spelling `self._d`, one resolving and one not | **refusal** |
| P6 terminal is a **parameter default** | **refusal** |

**P5 is the one that matters**: the round named it as *"the one I would plant
first"* and said plainly it had **reasoned** the outcome rather than executed it.
Executed, it refuses. A reasoned fail-closed is now a measured one.

### And the edge holds, which is the half that distinguishes a fixed point from a cap

A closure that refuses everything is a cap. Chains that **should** resolve:

| plant | outcome |
|---|---|
| E1 (shipped) four links onto a module-level `def` | `()` — resolves |
| **Q1 mine** three links onto a module-level `def` | `()` — resolves |
| **Q2 mine** one link onto a module-level `def` | `()` — resolves |

So the mechanism discriminates by chain **terminal**, not by chain **length**,
which is what M2 claims and this confirms through a second instrument.

### The one thing my plants found that nobody had — a bound to declare, not a defect

**Q3: `_t = [interior_page_count]; _d2 = _t[0]` — a container step onto a
terminal the walk CAN see — refuses**, where the same chain without the container
resolves. That is **correct** under ADR-0039/R2 (a shape it cannot analyse is a
failure, never a silent pass) and it is a loss of *precision*, not of safety.

But it sharpens the headline figure, and the sharpening belongs on the card:
I grepped the real module for a container-mediated callee and found **0**. So
**"the transitive step costs 0 refusals" means "no such shape exists in this
module", not "the walk resolves them."** Those are different claims and only the
first is measured. **To be stated in the declared bound before this card merges.**

### AC-5's premise verified, which is what makes the six firings meaningful

The card says CARD-262's commit holds `55311d7b…` while its fix agent's matrix
ran against `f6d113ed…`. Checked: `git show ac479658:…` and
`git show c2cb8e3e:…` both hash to **`55311d7be57a34ad`**. So firing against this
worktree's base **is** firing against CARD-262's committed bytes, and AC-5 is
answerable at all.

**And firing them corrected one of the figures they rested on.** The round reports
**N8 = 1 FAIL at `:4631`, not the 2 CARD-262 claimed** — `:4604` passes, because
neutering the attribute gate leaves the attribute-storage rows silent, which that
equality already expects. That is a correction to a **merged** card's figure,
found by doing the thing AC-5 asked for. Accepted on the round's measurement; I
did not re-run the matrix, and I say so.

### Structural checks

| check | result |
|---|---|
| **G-1** `git diff c2cb8e3e..HEAD -- src/` | **0 lines** |
| footprint | one file, **+911/−271** |
| the guard file, whole | **104 passed, 0 failed, 0 skipped**, 393.54 s |
| **G-5** position-axis definitions byte-identical | **holds** — see the note below |
| `ONE_STEP_ANCHOR` gone from all four tables | confirmed in the diff |

**One shade of over-statement in the round's G-5 claim, recorded because precision
is the subject of this card.** It reported *"grep over the diff returns
nothing"*. My grep returns **one** line: an **added comment** at diff line 421,
`#: value as :data:`RECEIVER_RESOLUTION_DEPTH`, and for the same reason` — a
prose cross-reference in the new `ANCHOR_RESOLUTION_DEPTH` docstring. **No
position-axis definition changed**, so G-5 holds in substance. The claim should
have been "no definition changed", not "the grep is empty".

### The round found a survivor in a control it had just written — credited, not merely noted

M7 survived at **0 FAIL of 10 reached, exit 0**: the first draft of
`TestGuardProse_EveryNamedControlExists` recomputed its own missing-name list
instead of exercising the one the check uses, and asserted only that the
authority was *large* — so widening the derivation to every `def` in `tests/`
changed nothing any assertion read, and the sibling mutant `missing = []` would
have survived both tests. Closed with one shared `_unresolved()` plus a
two-directional authority test; re-fired, M7 reds 1 and M8 reds 1.

**That is the wave-49 rule working as intended** — *a fix runs the kill
instrument over its own additions before hand-back, because the agent that writes
a control is the cheapest place to discover it cannot fail.* It is the first time
on this board a round has caught that in itself rather than having a cycle catch
it.

### THE CARD'S OWN DEFECT — AC-2 and AC-4 name tests that do not exist

Verified at `ac479658` and at HEAD: **`test_the_callee_exemption_cost_sequence_is_measured` and `test_a_zero_cost_class_must_absorb_a_blind_spot_row` do not exist as tests anywhere.** Both are **assertions inside**
`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`.

This card's AC-2 and AC-4 name them with `(test: …)`, and so did my brief — **the
card and the brief share the error**, and the card's drafting section lists both
under "Already exist — run them, do not rewrite them".

**This is the `check_ref_missing` family, and it is the ninth and tenth instance
found on this board**, after the eight fictional `TestCuration_*` verifiers
CARD-219's cycle 1 found across three cards. The irony the round noted is exact:
**AC-6 of this very card commissions
`test_no_docstring_names_a_test_that_does_not_exist`** — a derived, default-deny
check over the module's own `:meth:`/backticked references — and it would have
caught these two had they been in a docstring rather than in a card.

**Resolved the way CARD-219's F-003 was: once, at the AC, rather than by inventing
the tests.** AC-2 and AC-4 are rewritten below to name the assertion and its host
test. The round already ran and updated them as assertions of that test, which is
the correct reading.

### What the round did not close, and says so in three places

**VALUE** (two rows), **CALL-GRAPH** (parameter used as a callee) and **MODULE**
untouched; the call-graph axis is **narrowed, not closed** — refusing an
unresolvable alias chain is not resolving a call graph. The asymmetry is stated
on `MEASURED_BLIND_SPOTS`, in the control's docstring and in the axis table, and
the MODULE axis's census-equality weakness is noted as inherited rather than
touched. `MEASURED_BLIND_SPOTS` goes **11 rows → 4**, all four still `()`.

### The structural fact this family needs carried forward

The round's §11.4 is the most useful sentence in its hand-back and it is not
about this card: **the `anchored` branch is unreachable on this module** because
`unreadable`/`opaque` are checked first. So the closure and the `ONE_STEP_ANCHOR`
deletion are both free here — **and no behavioural control for either can come
from this module's own text. Every one has to come from a plant.** Which means
the third-party-plant budget on this family is not prudence, it is the only
available evidence. **Put that in the next card's brief in this family.**

### Still open for cycle 1 — not findings, the shape I would attack

`anchor_key` resolves an attribute target **by name only**, inheriting `bound`'s
`(storage, spelling)` keying. The round reasoned that a mixed key refuses earlier
via `opaque` and that an all-resolving key with an externally installed door is
R3's declared class — **and said plainly that this is reasoning, not
measurement**, and that it is the shape it would attack first. My P5 covers the
cross-class spelling collision and it refuses; the remaining untested shapes are
`__getattr__`/metaclass-provided attributes, a decorator link, a `*args`
forwarder, a callback parameter used as a callee, and anything crossing a module
boundary. **Cycle 1's plants go there.**

## [CYCLE 1 ADJUDICATION — 2026-10-24, orchestrator] 5.5, NOT CERTIFIED — the level is NOT resolved, and this is the family's fifth appearance

Report: `meta/review/20261024T120140Z-CARD-276-cycle1.yml` (synced; `yaml.safe_load`
OK; 5 findings, 3 gating). **Aggregate round counter: 3 of 6** — a fix round, its
pre-gate and a cycle 2 all fit.

The card asked one question and the cycle answered it with plants rather than
reading: **the chain-LENGTH half is genuinely resolved and the edge holds; the
KEY half is not.** Two shapes reach the real geometry door with a bare literal
page position and the walk reports nothing, and both sit **exactly one level of
indirection beyond the one this card closed** — which is this family's signature
across all five attempts.

### F-1 (Critical, gating) — reproduced here, first command

`bound` (`:1928`) and `anchor_key` (`:2154`) key an attribute by **spelling
alone**, across every receiver, class and scope. So
`anchored_to_a_fixed_point` returns True for a spelling as soon as **one** binding
occurrence of it resolves *anywhere in the module*, and the attribute branch at
`:2455-2459` **`continue`s** — skipping the own-instance surface rule, the
mechanism whose own comment (`:2029-2035`) claims it covers *"`setattr`,
`__set_name__`, a metaclass … F-401's P1/P5/P8"*.

```
setattr-installed door, NO laundering occurrence      -> ('refusal',)
the SAME door + one unrelated `self._d = <resolving>`  -> ()
```

**One unrelated resolving occurrence of the spelling, in a different class, is
the whole difference.** Three further shapes share the mechanism and are all
silent — a `__set_name__`+`setattr` install, a metaclass `__getattr__`, and a
`__getattr__` installed by `setattr` — and the second of those is
**`DOOR_SHAPES` row W29, a row this card asserts refuses, silenced by appending
one assignment.**

**And it corrects my brief exactly where I was most confident.** I named the
mixed-key and externally-installed-door cases as the shapes to attack and
predicted both would fail closed via `opaque`. The **mixed** key does — any
opaque occurrence of the spelling refuses first, which is why laundering W28/W29
by *adding* a resolving occurrence beside an opaque one fails. The
**externally-installed-door** case does **not**, and it is **not R3** as the
round reasoned: `setattr` creates no `ast.Store`, so the spelling's only
occurrence is the resolving one and the receiver stays `self`. My prediction was
wrong in the one direction that matters.

### The accountability regression — the reviewer's substance is right and its wording is wrong, measured

Cycle 1 said *"neither has any lever — exhaustive search over all 16
`CALLEE_EXEMPTIONS` subsets … leaves both silent."* **Exhaustively re-measured
with `_plant_refusals` (the attributing instrument) over every subset at both
revisions:**

| | subsets exposing the plant's own lines | minimal single drops |
|---|---|---|
| **fork point `c2cb8e3e`** (5 exemptions, 32 subsets) | **24** | `a callee anchored one step and no further`, `builtins` |
| **HEAD `ced5e648`** (4 exemptions, 16 subsets) | **8** | `builtins` **only** |

So a lever does survive at HEAD, and the finding's wording overstates. **But the
substance is sharper than it claimed, not weaker:** the fork point had a lever
that **names the mechanism** — `a callee anchored one step and no further`, i.e.
`ONE_STEP_ANCHOR` — and this card **deleted that class**. HEAD's only surviving
single-drop lever is `builtins`, which fires because **the plant's own three
lines happen to call `getattr`**, not because anything can see a
`setattr`-installed door. A lever that fires on an unrelated feature of the
plant's text is not accountability for the door axis.

**That is verbatim what CARD-262's own `ONE_STEP_ANCHOR` docstring recorded about
"Fix 1"**: *"it was in no exemption list, cost nothing in the sequence below and
no control could see it."* This card deleted the class — correctly, on cost — and
left the silent pass that the class had been accidentally accounting for.

### I nearly contradicted a correct Critical with a confounded instrument, and the card had warned me

My **first** lever search dropped each exemption and read `_outcome`. It reported
`('refusal',)` for **every** drop at both revisions, which reads as "levers
everywhere, the finding is wrong". It is wrong because `_outcome` reads the
**module's total** refusals, and this card's own `_plant_refusals` docstring
(`:3709`) says so in as many words: *"removing `builtins` costs this module 251
of its own and removing the external-attribute class 201, so an
`== ("refusal",)` on the module's total is satisfied by the module and says
nothing about the plant."*

**This is the third time this session an instrument of mine answered a different
question than the one I asked** — after CARD-218's Q5 (a mutant that tripped the
guard in front of the one under test) and CARD-282's F4 (an absence verified
against one spelling). Here it would have cost a true Critical its severity.
Recorded as the pattern: **before reading a measurement as a contradiction,
check that the instrument attributes to the thing in question.**

### F-2 (Major, gating) — the terminal, and a second removed lever

The closure's stated safety argument (`:2168-2173`, repeated in the card's §1) is
*"a geometry door cannot stand at a `def`/`import` terminal without being
spelled."* A **decorator** does exactly that: `@_mk def _deco_door(...)` where
`_mk` returns `getattr(sys.modules[__name__], "book_page_" + _S)` puts the real
imported door at a `def` with its name assembled. Resolved chain → **silent**.

**And the lever is gone the same way:** the *direct* call is gated (dropping
"definitions and imports" reds it), but one alias away the resolving branch
`continue`s at `:2415` first and dropping that gate reds nothing. **A second R3
lever that existed at the fork point and does not now.**

Cycle 1 also measured that the naive symmetric `Name`-branch fix is **not** free
— it breaks E1/E2 into the fall-through refusal. **So F-2's remedy needs design,
and it is the half I expect to slip to a successor.**

### F-3 (Major, gating) — AC-6's own deliverable, falsified

The rewritten opening sentence — *"fails closed on the **whole** door axis"*,
*"every `ast.Call` is refused unless this walk can positively anchor its
callee"* — and the axis table's *"closed by CARD-276: the sentence is true
again"* are both false under F-1 and F-2.

The same paragraph says why that matters here more than anywhere: *"it was
re-asserted as true twice while it was false, and a reader of the third version
should be able to see what that cost."* **This diff is the third
re-assertion.** AC-6 commissioned `test_no_docstring_names_a_test_that_does_not_exist`
to stop prose drifting from mechanism, and the prose about the mechanism drifted
in the same commit.

### F-4 / F-5 (minor, non-gating)

`REFERENCES_AT_LEAST`'s doc says the prose names "fifteen distinct controls";
recomputed with the module's own resolver it is **17** (the floor of 14 is fine,
and the card's §8 says 17 — only the rationale sentence is stale, **in the class
built to catch stale prose**). And `MEASURED_BLIND_SPOTS`' VALUE row 2 enumerates
three defeaters of `module_integers` and omits `len(_FRONT_MATTER_PAGES)`, which
**this card's own §2 names** — measured silent, as are `int(3.0)` and four others.

### My three rulings, answered

* **Container-step bound: covered in substance, non-gating.** Q3 reproduced
  exactly, and the shipped file already forestalls the claim I was guarding
  against — `CALLEE_EXEMPTION_COST`'s doc (`:3182-3190`) states the 0 as *"not one
  of this module's 816 calls reaches a callee key with an `anchored` binding
  occurrence at all"*. Cycle 1 **verified that independently** by instrumenting
  both anchored branches: **0 hits each over 816 `ast.Call` nodes.** One sentence
  for the precision loss; do not gate it.
* **Parametrise-per-row: holds.** 14 node ids in the two new classes including
  `[I1]`…`[I7]` and `[E1]`/`[E2]`; whole file 104. Every cell count is
  per-assertion-addressable.
* **Zero-cost-class second half: holds.** Tuple empty, vacuity stated at
  `:3209-3212`, and the sequence strictly drops at every step so the first
  equality does carry the claim.

### What checks out — and a negative result worth as much as a finding

**Every committed figure reproduces in a second domain** (recomputed by calling
`_page_positions` directly rather than through the tests): 760/509/203/201/0;
blind spots 11 → 4, all `()`; 36/36 `DOOR_SHAPES`;
`SILENT_WITHOUT_THE_DOOR_ARMS` 30; `SILENT_WITHOUT_ONE_ARM` 23 and **1**; 17
prose references, 0 missing. **G-1** re-verified at 0 lines. **G-5 holds by AST
extraction of each definition's exact source span** — not grep — all eight
byte-identical, which is a better instrument than the one I used at the pre-gate.
**G-7's letter holds**: no silent cap anywhere in the new mechanism. The M7 fix
is sound.

**And three of the shapes nobody had executed found nothing silent** — a
decorator link *in the chain*, a `with … as` link, and a module-boundary chain
**all refuse through `opaque`**. Cycle 1 recorded that as a useful negative
result rather than padding, which is the right instinct and is noted here so a
successor does not re-plant them.

### What cycle 1 did not check

The 393 s full-file run (the pre-gate established 104/0/0; it ran **419 passed, 0
skipped** over the two new classes plus `tests/test_suite_profile.py`, which keeps
trap 9 clear). No full suite; the lock was never taken, with CARD-282 concurrent.
The CON-019 tripwires (G-2 holds structurally: one file, `src/` 0 lines).
`kill_matrix.py` itself. The MODULE axis census equality.
`SILENT_WITHOUT_ONE_ARM` row **membership** (counts only). And it **could not
build a local-name-storage analogue of F-1**, and says why — which is a bound on
the finding, not a gap in it.
## [FIX ROUND 1 on cycle 1 — 2026-10-24, fix agent] F-1 closed, F-2 half closed and half declared with a lever, F-3 rewritten to the mechanism that shipped

Scope: one file, `tests/test_book_export_interior_cover.py`.
`git diff c2cb8e3e..HEAD -- src/` is **0** lines (re-verified; `src/nonogram/admin/book_pdf_generator.py`
sha256 `d8b9ece8…` unchanged, working tree and index both clean under `src/`).

### FIX 1 (F-1, Critical) — the conditional, and cycle 1's five claims re-derived here

The attribute branch's `continue` is now inside `if blocked is not None:`, so a
chain the fixed point **resolves** falls through to the own-instance surface rule
instead of past it. Four lines of mechanism; the rest of the hunk is the comment
that says what stood there.

**Every one of cycle 1's five claims re-derived by driving `_page_positions`
directly against the edited bytes, not taken from the review:**

| claim | re-derived |
|---|---|
| A2 refuses | `('refusal',)`, at the surface rule — `"an attribute of this module's own instance that BookPDFGenerator never spells"` |
| module cost 0 refusals | **23 sites, 6 vocabulary, 0 refusals** — identical to `ced5e648` |
| 36 `DOOR_SHAPES` unchanged | 36 rows, **0 mismatches** against their declared outcomes |
| both `CHAINS_THAT_RESOLVE` | E1 `[]`, E2 `['a geometry door referenced without being called']` — both as declared |
| all 7 `CHAINS_THAT_MUST_NOT_BE_SILENT` | I1–I7 all `('refusal',)` |

Also unchanged and re-measured: `PLANTED_SHAPES` 0 mismatches; the cost sequence
**760 / 509 / 203 / 201 / 0**; all `MEASURED_BLIND_SPOTS` rows still `()`.

**The three further shapes, each with its own refusing control.** `SURFACE_SHAPES_LAUNDERED`
is parametrised S1/S2/S3 and each row is read **twice** — without the laundering
occurrence and with it — because a row that stops reaching a call at all would
satisfy a bare "it refuses" for the wrong reason. At `ced5e648` every pair read
`('refusal',)` then `()`; all three now read `('refusal',)` / `('refusal',)`.
S1 is the Critical's own plant A2, S2 the metaclass `__getattr__`, S3 the
`__getattr__` installed by `setattr`. Cycle 1's B1 is `DOOR_SHAPES` W25 and is
laundered there instead, by the rule below, so it is not paid for twice.

**W29's launderability — and the brief's row number is wrong, measured.** The
control is not written for one row: `test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`
derives, from each `DOOR_SHAPES` row's own AST, an unrelated `_UnrelatedResolver`
class that resolves every **attribute** callee the row spells, and asserts the
row's declared outcome is unchanged. The derivation reaches **14 of the 36** rows
and is held to an equality against `LAUNDERABLE_DOOR_SHAPE_LABELS`, so a row that
gains or loses an attribute callee reds rather than silently entering or leaving
the reading; `test_the_laundering_derivation_parsed_every_planted_body` makes a
body it cannot parse a FAILURE instead of an empty laundering.

Measured at `ced5e648`, **three** rows could be switched off from outside
themselves: **W21, W23 and W25**. **W29 cannot** — its installer's store is
*spelled* (`owner._door = getattr(...)`), so the `opaque` branch refuses it
before the anchor is consulted, with or without a resolving occurrence. W29 is
the row cycle 1 and the brief both named; the launderable `__set_name__` row is
**W25**, the `setattr` one. All 14 rows keep their declared outcome now.

The 22 rows with no attribute callee are **not** read here, and that is stated on
the derivation rather than skipped quietly: their laundering text is empty, so
the reading would be byte-identical to
`test_every_door_shape_is_read_or_refused_and_never_silent`'s. The local-name
storage has no laundering analogue — cycle 1 could not build one and said why.

### FIX 2 (F-2, Major) — route taken: **close the decorator, declare the residue, and give it a lever**

Not the naive symmetric `Name`-branch fix cycle 1 warned about, and not a
declaration that leaves the premise standing. Two changes:

1. **The terminal rule.** A definition's binding occurrence now carries its own
   AST node, and a **decorated** definition is not a fixed point: the decorator
   replaces what the `def` binds, so the identity read off the text is not the
   identity at the call. T1 (`@_mk def _deco_door` where `_mk` returns
   `getattr(sys.modules[__name__], "book_page_" + _S)`) and T2 (the same
   returning `getattr(BookPDFGenerator, "page_" + _S)`) were both **silent** at
   `ced5e648` and both refuse now. **Module cost: 0** — the anchored branch is
   unreachable on this module, which cycle 1 measured independently as 0 hits
   over 816 `ast.Call` nodes, and I re-derived as 0 refusals and an unchanged
   cost sequence.
2. **The lever, which is FIX 4.** A **fifth** `CALLEE_EXEMPTIONS` class,
   `a chain whose terminal is a definition or an import`, gates the resolved
   pass in **both** storages. With it in place a resolved chain passes; with it
   removed every resolved chain refuses and names itself.

`CHAINS_THAT_RESOLVE` did not move and gained a row: **E3**, an attribute callee
whose chain resolves and whose calling class spells it, silent as declared. E1
and E2 are both local-name rows, so a cap in the *attribute* branch would have
closed every counterexample and red nothing; E3 is the edge that reds instead.

### FIX 4 — accountability, per row still open

| row | lever | measured with `_plant_refusals` |
|---|---|---|
| R8 `the TERMINAL class: a definition rebound where this walk can see no store` | **its own class**, `a chain whose terminal is a definition or an import` | silent with all five classes (`()`); with that one class dropped → `[(…, "a callee whose alias chain this walk resolved to a definition or an import in this module's own text…")]`, attributed to the plant's own lines |
| the `CALLEE_EXEMPTION_REACH` row for the same class | the class | silent with all five; without it, refusal naming `_d2` |
| the two VALUE rows, the CALL-GRAPH row | **none**, as before | `_page_positions` exposes no lever for either axis; declared, unchanged |

**No row's lever is `builtins`.** R8's plant is split across the two storages on
purpose: the gate is written once per storage, so a single reading would have
certified one gate and left a mutant on the other with no cell. The
`CALLEE_EXEMPTION_REACH` row reads the **attribute** branch's gate (X6 below) and
R8 reads the **local** branch's (X5 below).

The class's own step is **0**, so it is listed in
`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` and kept **only** because it
absorbs R8. That un-vacuums the second half of the narrowed rule, which the
previous commit had to declare vacuous.

### FIX 3 — the sentence, before and after

**Before** (`_page_positions`, the opening paragraph): *"It fails closed on the
**whole** door axis — callee identity resolved to a **fixed point** over the
alias chain, door spellings closed over the grammar"*, and the axis table:
*"**closed by CARD-276**: the sentence is true again, of a fixed point rather
than of one step"*.

**After**: *"On the door axis it refuses every `ast.Call` whose callee it cannot
anchor to a **fixed point** over the alias chain, and every `GEOMETRY_DOORS`
spelling held outside the grammar it reads. What it does **not** close is the far
side of a chain it *can* resolve: a terminal's identity is read off the `def`,
`class` or `import` this module's text shows. A **decorator** puts an unspelled
door at exactly such a terminal, so a decorated definition is not read as one and
the chain onto it refuses; a definition rebound where this walk can see no store
at all — `globals()`, a module `__dict__` store, an importer's monkeypatch — is
**not** reached, and that residue is the ADR-0039/R3 exemption class `a chain
whose terminal is a definition or an import`, with a `MEASURED_BLIND_SPOTS` row
read in both directions. This sentence said "fails closed on the whole door axis"
for exactly one commit and was false when it shipped, for the third time in this
family."*

And the axis table's bullet now reads **"narrowed — not closed — by CARD-276"**,
names which half is closed and which is declared, and ends: *"**So the sentence
is still false**, of exactly that residue — and the residue has a named exemption
class, its own step of the measured cost sequence (0, listed … and kept only by
the blind-spot row it absorbs) and a lever that names it … re-asserted as true
**three** times while it was false, and a reader of the **fourth** version should
be able to see what that cost."*

Why it is true of this commit: every clause is a reading above. "Refuses every
call it cannot anchor" — the cost sequence's 760 with no exemption and the 36 +
14 + 7 + 3 + 2 refusing rows. "A decorated definition refuses" — T1, T2.
"A rebind it cannot see is not reached" — R8, asserted silent. "With a lever" —
R8's second reading.

### FIX 5 — F-4 and F-5

* **F-4.** The stale "fifteen distinct controls" sentence is **not** restated with
  a corrected number. A figure nothing recomputes goes stale again, and this
  file's own rule is that a figure's control is recomputation — so the rationale
  now records what the stale figure cost, points at the reading
  `test_no_docstring_names_a_test_that_does_not_exist` prints, and carries no
  count. (`REFERENCES_AT_LEAST = 14` is untouched; the live reading is **19**
  after this diff, 0 missing, against an authority of 5,155 test names.)
* **F-5.** `MEASURED_BLIND_SPOTS`' VALUE row 2 now states its enumeration as
  **partial**, says what bounds it (*anything that is not a top-level `ast.Assign`
  of a bare int `Constant`*), and names all five measured defeaters including
  `len(_FRONT_MATTER_PAGES)` and `int(3.0)`.

### The mutant table — nine mutants, each DELETING a mechanism this round's claims name

**Domain, stated because a figure without one is not a figure.** Instrument:
the committed `tests/kill_matrix.py`. Target
`tests/test_book_export_interior_cover.py`, **203 `ast.Assert` nodes** (node
count, not a collected-test count). Child instrumentation **off**. Every mutant
is line-count-preserving and was validated present by the instrument, which
refuses a mutant whose `old` is absent — and every one produced a changed
reading, so none is a no-op. Batch A selection:
`TestDoorAxis_TheNextIndirectionIsNotSilentEither` (33 collected). Batch B
selection: the three exemption/blind-spot tests (3 collected). **SHIPPED: 0 FAIL
of 14 reached, pytest exit 0**, in every reading.

| mutant | the mechanism it DELETES | FAIL | cells red | cells passing / notes |
|---|---|---|---|---|
| **X1** | FIX 1's conditional — the attribute branch's `continue` becomes unconditional again | **2** | `:5619` (`test_a_door_installed_from_outside_the_text_survives_one_resolving_occurrence`, S1–S3), `:5691` (`test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`, W21/W23/W25) | the chains, the edge rows, the terminal rows — a one-step-or-fixed-point mechanism satisfies all of them, which is why F-1 needed its own controls |
| **X2** | the whole fixed point's **resolve** path (`return True` → `return False`): every anchored callee refuses — a cap | **3** | `:5590` (`CHAINS_THAT_RESOLVE`, E1/E2/E3), `:5780`, `:5791` (the bound's "inside resolves" and "raised past it resolves") | `:5549`, `:5691`, `:5619` — a cap closes every counterexample in this class, which is exactly why the edge rows exist (G-7) |
| **X3** | the terminal rule — the decorator check (`decorator_list` → an attribute no node has) | **1** | `:5716` (`test_a_decorated_definition_is_not_a_terminal_this_walk_can_read`, T1/T2) | everything else; F-2's closure has exactly one control and this is it |
| **X4** | the **edge** of the terminal rule — `is not None`, so *every* definition terminal refuses | **3** | `:5590` (E1 and E3; E2 is an `import` and still resolves), `:5780`, `:5791` | `:5716` passes — refusing every `def` also closes T1/T2, which is the pair ADR-0039/R1 asks for: one mutant inside the claimed region, one at its edge |
| **X7** | the laundering **derivation** (`if not spelled:` → always) | **1** | `:5654` (`test_the_laundering_derivation_reaches_the_rows_it_declares`) | and `:5691` goes **NOT-REACHED** with 13 reached instead of 14: with the derivation empty the 14 parametrised readings stop existing. That is the vacuity the derivation test is for, and the NOT-REACHED cell is the evidence that nothing else would have noticed |
| **X5** | the **local**-storage half of the terminal lever (`not in exempt` → `not in cls.CALLEE_EXEMPTIONS`, so the gate never fires) | **1** | `:5089` (`test_the_declared_blind_spots_are_still_silent`'s *absorbed* reading — R8's lever) | the silence reading itself passes, which is the point: a row that is silent with the class and silent without it has no lever |
| **X6** | the **attribute**-storage half of the same lever | **1** | `:4430` (`test_every_callee_exemption_is_read_twice_on_its_own_branch`) | X5 and X6 red **different** cells, which is why the lever's two plants are in different storages — one plant would have certified one gate |
| **X8** | the zero-cost-class equality in the "listed but paying" direction (`CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` emptied) | **1** | `:4329` | AC-4's *"the zero-cost-class equality still reds when emptied"*, re-fired against this round's bytes |
| **X9** | R8's `absorbed_by`, so the 0-cost class absorbs no blind-spot row | **1** | `:4336` (the subset assertion) | this is the **second half of the narrowed rule carrying a claim** rather than being vacuous, which is what the previous commit had to declare it was |

**Which kills are instrumented-only: none of batch B's.** The recording pass
reports exit 0 by construction, so the same four mutants were re-fired under
`Pass.RERAISING`: **all four give pytest exit 1 with the same cells** (X8's
`:4336` becomes NOT-REACHED, which is the re-raising pass short-circuiting at
`:4329`, not a changed verdict). Batch A's re-raising reading is recorded
below.

**Batch A's re-raising reading: every one of the five is a real kill, not an
instrument attribution.** `Pass.RERAISING`, same selection and same 203-node
denominator: X1 **exit 1**, 14 reached, 2 FAIL (`:5619`, `:5691`); X2 exit 1, 12
reached, 2 FAIL (`:5590`, `:5780` — `:5791` is NOT-REACHED because the test
short-circuits at `:5780`); X3 exit 1, 14 reached, 1 FAIL (`:5716`); X4 exit 1,
12 reached, 2 FAIL (`:5590`, `:5780`); X7 exit 1, 13 reached, 1 FAIL (`:5654`).
The only differences from the recording pass are short-circuited siblings, which
is the pass's documented cost and not a changed verdict. SHIPPED is 0 FAIL of 14
reached at exit 0 in both passes.

**Restores.** The file was restored from a pristine copy kept **outside** the
worktree after every mutation run and the restore verified with `diff -q` **and**
`shasum -a 256` (`07e8e1e7…`), never with `git checkout`. A grep for this round's
own mutant markers (`no_decorator_here`, `not in cls.CALLEE_EXEMPTIONS`,
`spelled or 1`) finds none. `src/nonogram/admin/book_pdf_generator.py` is
`d8b9ece8…` and `src/nonogram/export/layout.py` is `3a384f33…`, both unchanged
(G-1, G-2).

### Figures this round moved, re-measured and published

| figure | was | is |
|---|---|---|
| `tests/test_book_export_interior_cover.py` collected | 104 | **126** |
| the two door-axis classes' node ids | 14 | **36** |
| `CHAINS_THAT_RESOLVE` rows | 2 (E1, E2) | **3** (E1, E2, **E3**) |
| `CALLEE_EXEMPTIONS` | 4 | **5** |
| `CALLEE_EXEMPTION_REACH` rows | 4 | **5** |
| `CALLEE_EXEMPTION_COST` steps | 5 | **6** — `((), 760)`, `509`, `203`, `201`, `0`, `0` |
| `CALLEE_EXEMPTIONS_THAT_COST_THIS_MODULE_NOTHING` | `()` | **1 member**, and the second half of the narrowed rule is no longer vacuous |
| `MEASURED_BLIND_SPOTS` rows | 4 | **5** (R8 added) |
| prose references resolved by `TestGuardProse` | 17 | **19**, 0 missing, authority 5,155 |
| `def test_` in the file | 75 | **80** — five added, **none** removed, renamed, skipped or merged |

**Unchanged and re-measured, not assumed:** 23 sites / 6 vocabulary / 0 refusals;
the cost sequence 760 / 509 / 203 / 201 / 0; `DOOR_SHAPES` 36 rows, 36 labels, 0
mismatches; `PLANTED_SHAPES` 0 mismatches; all 7 `CHAINS_THAT_MUST_NOT_BE_SILENT`
`('refusal',)`; E1 `[]` and E2's one reference-arm shape; every
`MEASURED_BLIND_SPOTS` row `()`; `SILENT_WITHOUT_THE_DOOR_ARMS` 30 and
`SILENT_WITHOUT_ONE_ARM` 23 / 1 (green in the file run — the arms' internals only
ever gained refusals, and no row changed arm).

**G-5 re-verified by AST source-span extraction against `c2cb8e3e`**, not by
grep: `BINDERS_READ`, `STRING_FIELDS_READ`, `EXEMPTION`, `BINDER_BINDINGS`,
`POSITION_LITERALS`, `GEOMETRY_DOORS`, `POSITION_PARAMETER` and
`RECEIVER_RESOLUTION_DEPTH` are **all eight byte-identical**.

### Cost, as plant counts rather than durations (G-6)

The round adds **27 plant readings**: 14 (the derived `DOOR_SHAPES` laundering,
one per attribute-callee row) + 6 (`SURFACE_SHAPES_LAUNDERED`, three rows read
twice) + 2 (`TERMINAL_SHAPES`) + 1 (E3) + 2 (R8, silent and with its lever
dropped) + 2 (the new `CALLEE_EXEMPTION_REACH` row, both readings). Two of the
five new nodes cost **no** plants at all (the derivation's parse check and its
label equality). The 22 `DOOR_SHAPES` rows with no attribute callee are
deliberately **not** re-planted: their laundering text is empty, so the reading
would be byte-identical to the existing table's. That choice is stated on the
derivation rather than left to be found.

### Section 8 of this card is superseded by FIX 3

§8's first bullet describes the opening sentence as *"closed on the whole door
axis … four exemption classes, one of which absorbs a door-reaching shape
(R3)"*. That sentence is gone; see FIX 3 above for what replaced it and why.
§11's "plant shapes NOT tried" list loses three more entries:
`__getattr__`/metaclass-provided attributes (S2, S3) and a chain **whose
terminal** is a decorator (T1, T2) — a chain with a decorator *link*, which §11
also names, was executed by cycle 1 and refuses through `opaque`, and is a
recorded negative result that should not be re-planted.

### Three things this round found wrong in cycle 1, the adjudication and the fix brief

1. **The launderable `DOOR_SHAPES` row is W25, not W29 — and the metaclass shape
   is not a `DOOR_SHAPES` row at all.** Cycle 1's evidence block says B1 is *"W29
   with the installer's spelled store replaced by `setattr`"*, which is **W25**;
   the adjudication and the fix brief compressed that to "W29 … silenced by
   appending one assignment" and the brief additionally attributed it to the
   metaclass `__getattr__` (cycle 1's B2), which has no row anywhere. Measured
   at `ced5e648`, appending a resolving occurrence of the callee's spelling to
   each of the 14 attribute-callee rows silences **W21, W23 and W25** and
   **not W29**: W29's installer store is *spelled* (`owner._door = getattr(…)`),
   so `opaque` refuses it before the anchor is consulted. The brief's W23 was
   nobody's finding. Closing it by rule over the derived set rather than by row
   is what caught the third one and the false one.
2. **There is no M9 on this card.** The brief asks for "M9's actual pytest
   output" and says the error-kill label was repeated on the card. CARD-276's
   mutant table is **M1–M8** plus the inherited N-cells (N8/N8h, N12b, N13/N13h,
   N14, N16, N18); no cell is labelled an error-kill and `grep -n "M9"` over the
   card (both copies) and over `meta/review/20261024T120140Z-CARD-276-cycle1.yml`
   returns nothing. The item looks carried over from CARD-282's brief. The one
   label worth restating here is M7, and the card already states it correctly:
   **a genuine survivor** at 0 FAIL of 10 reached, exit 0 — not an error — in a
   control the same round had just written.
3. **F-2's "close it properly" half was affordable, against the brief's
   expectation.** The brief predicted the design work would slip to a successor
   and offered declaration as the likely right call. The naive symmetric
   `Name`-branch fix cycle 1 measured *is* unfree, as stated — but
   discriminating the terminal (a decorated definition is not one) costs **0
   refusals**, moves no declared table, and leaves E1/E2 untouched, because the
   anchored branch is unreachable on this module. So the decorator is closed and
   only the unseeable rebind is declared. The brief's framing of FIX 1 and FIX 4
   as separable is also slightly off: they share one mechanism — the resolved
   pass — and closing F-1 without gating that pass would have left exactly the
   accountability hole F-4 bills.

### What this round did NOT check

* **No full suite, and `meta/kanban/.full-suite.lock` was never written or
  taken** — CARD-282 is concurrent in `../PythonProject4-card-282` and
  `tests/conftest.py`'s guard raises on a foreign holder, which would red every
  run that card's agents make. The merge gate's full suite is the
  orchestrator's.
* The **MODULE** axis's census equality, unchanged and still inheriting the
  weakness the card already states.
* The per-arm tables' **row membership** (`SILENT_WITHOUT_ONE_ARM`): the file
  run exercises the equalities, and nothing in this diff can move a row between
  arms — the callee arm only ever gained refusals — but no per-arm reading was
  taken by hand.
* `scripts/impact_set.py`'s set beyond the five files run below. `test_scope` is
  impact and this diff is one test file with `src/` at 0 lines.

### Runs taken

* `tests/test_book_export_interior_cover.py` — **126 passed, 0 failed, 0
  skipped** (exit 0), on bytes differing from the commit's only in prose; the
  authoritative re-run on the committed bytes `07e8e1e7…` is recorded below.
  Collection on the committed bytes: **126**, and **36** node ids over the two
  door-axis classes, including `[I1]`–`[I7]`, `[E1]`–`[E3]`, `[S1]`–`[S3]`,
  `[T1]`/`[T2]` and the 14 `[W…]` laundering ids.
* `tests/test_suite_profile.py` — **405 passed**, 0 skipped. The frozen
  render-set grep is in there, so **trap 9 is clear**: this file still mentions
  `puzzle_pages` (row I7) and the snapshot equality holds.
* `tests/test_guard_integrity.py` — **167 passed**.
* `tests/test_kill_matrix.py` — **76 passed**, so the instrument this round's
  figures come from is green on these bytes.
* The three CON-019 tripwires plus the byte-identity property test —
  `tests/test_export_a4_golden.py tests/test_book_puzzle_frame.py
  tests/test_book_qr_slot.py` **269 passed**, and
  `tests/property/test_cli_exports_byte_identity.py` **3 passed**, both without
  being edited (G-2).
* **0 skips in every run above.** Green-with-skips reads the same as green, so
  the passed counts are quoted and not the exit codes.

### The authoritative run on the committed bytes, and the one test pytest could not finish here

`tests/test_book_export_interior_cover.py` on `07e8e1e7…`, in three
class-partitions that sum to **126** collected (verified by
`--collect-only`: 67 + 23 + 36):

| partition | result |
|---|---|
| everything but the three guard/door classes (67) | **67 passed**, 59 deselected, 0 skipped |
| `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage` minus one test (22) | **22 passed**, 1 deselected, 0 skipped |
| `TestDoorAxis_…` + `TestGuardProse_…` (36) | **36 passed**, 0 skipped |

**125 of 126 passed under pytest here, 0 failed, 0 skipped.** The one test not
run to completion by pytest in this round is
`test_each_door_axis_arm_catches_a_shape_the_other_misses`, and the reason is
**environmental, not a failure**: this sandbox reaps a long-running shell, and
that test's 144 plant readings now exceed what it allows — four whole-file
attempts were each cut off *inside* that test with no FAIL cell and no summary
line, which is precisely the "exit code is not a verdict" trap. An **exit 1 with
no summary is not a red test**, and it is not a green one either, so it is not
reported as either.

What it asserts was verified instead by recomputing all four of its equalities
in a second domain, driving `_page_positions` directly with each `door_arms`
setting: **`callee identity` 23 silent (declared 23), `door spelling` 1 (declared
1), both arms removed 30 (declared 30), `kept` 6.** All four hold, so those
figures are unchanged. The test also passed in a complete **126 passed, 0
failed, 0 skipped** whole-file run taken earlier in this round, against bytes
differing from the commit's only inside docstrings and comments.

**That is a cost datum a successor needs, and it is stated as a count, not a
duration (G-6):** the single most expensive control in this file makes
**3 × 36 + 36 = 144** plant readings, which is more than this round's whole
addition (27). CARD-287 is sized against this class; if anything in it should be
cheapened first, it is that test's three-readings-per-row shape, not the tables
this round added.

## [FIX ROUND 1 PRE-GATE on `31897571` — 2026-10-24, orchestrator] PASSED — and I attributed a phantom to this card twice before measuring both arms

### The mechanism work, verified with my own instruments

| check | result |
|---|---|
| **F-1** — my own unchanged A2 plant (`setattr`-installed door + one unrelated resolving occurrence) | bare `('refusal',)`, laundered **`('refusal',)`** — **closed** (it was `()` at `ced5e648`) |
| **the launderable rows**, by a **derived** resolver over all 36 `DOOR_SHAPES` | before: **W21, W23, W25**; after: **none**. 14 rows carry an attribute callee |
| **G-1** `git diff c2cb8e3e..HEAD -- src/` | **0 lines** |
| footprint | one file, **+1515/−256** |
| **partition B** — the 33 tests this round added | **33 passed, 119.51 s** |

**The round's correction of my adjudication is confirmed to the row, and my own
probe then reproduced the error it was correcting.** I had written "W29 …
silenced by appending one assignment"; cycle 1's evidence actually said *"W29
with the installer's spelled store replaced by `setattr`"*, which **is W25**.
Measured: W25 installs with `setattr` (no `ast.Store`, so the spelling's only
occurrence is the resolving one) and **W29 installs with a spelled store, so
`opaque` refuses first and it never laundered.** **W23 was nobody's finding** —
the round found it by closing the property as a **rule over a derived set**
rather than for the named row. And my first hand-written laundering probe
**missed W23 because it used one spelling** (`_door`, where W23's callee is
`self.text`). *The instinct my brief had — name the row — is the instinct that
misses the third row.*

### THE PHANTOM: I blamed this card twice for a machine-load artefact

Recorded in full because the error is more instructive than the finding.

**What I claimed, and retracted, twice:**

1. *"The round pushed `test_each_door_axis_arm_catches_a_shape_the_other_misses` past the point where it can run."* **False** — the test run alone dies at **`ced5e648` too** (120.98 s) as well as at `31897571` (120.93 s).
2. *"The whole file completed before the round and not after, and that is the round's delta."* **Also false** — the pre-fix whole file, from bytes hashing `4a2a28eba300`, **dies now as well**, although those same bytes gave **104 passed in 393.54 s** at my own pre-gate hours earlier.

**The controlled experiment I should have run first** — both revisions, back to
back, nothing of mine running:

```
ARM 1 POST-fix (31897571): exit=1 -> [ 57%] .....
ARM 2 PRE-fix  (ced5e648): exit=1 -> [ 57%] .....
```

**Byte-identical stopping points.** And the round's own three attempts
(`finalrun.txt` 17:21, `finalrun2.txt` 17:32, `finalrun3.txt` 17:41) are
byte-identical to both. **Six runs, two revisions, three hours apart, the same
`[ 57%]` and five dots.** The diff is not implicated.

**The cause**, measured: **zero python processes running, load average 12–20 on
an 11-core box.** Top consumers are PyCharm (19.9 %), a `claude` process up
2d 2h (15.4 %), IntelliJ IDEA (12.2 %), WindowServer and Chrome. A test costing
~99 s warm on a quiet machine stretches past a hard **~120 s** per-test ceiling
under that load, and every run containing it stops in the same place.

**Why I got it wrong, which is the reusable part:** both of my readings compared
**a quiet run from hours earlier against a loaded run from minutes earlier** —
two arms measured under different conditions. That is the exact confound this
card's own `_plant_refusals` docstring warns about in another guise, the one I
caught in cycle 1's "no lever" claim, and the one I have written into every
brief this wave. **I policed it in four other agents' measurements and committed
it twice in my own diagnosis inside an hour.**

Also found and cleaned: two orphaned polling shells (`until grep -qE …; sleep`)
left by this round waiting on its own `finalrun*.txt`. Cheap, but litter.

### What this pre-gate therefore does and does not establish

**Establishes:** F-1 closed, the launderable rows closed as a derived rule, G-1
clean, the round's own 33 tests green at 119.51 s, and its corrections to my
adjudication confirmed.

**Does NOT establish:** a whole-file green at this commit. The last whole-file
green on this file is **104 passed / 393.54 s at `ced5e648`**, taken when the
machine was quiet. **A whole-file run at `31897571` is owed and must be taken on
a quiet machine** — it is the merge gate's precondition, not this pre-gate's,
and it is a condition of the host rather than of the diff.

**Routed out:** the per-test ceiling and this file's proximity to it are not this
card's defect and not its to fix. **CARD-292** carries them with these
measurements.

## [CYCLE 2 — 2026-10-24, review agent] 6.5, NOT CERTIFIED — the sixth appearance, and the round budget is spent

`meta/review/20261024T213626Z-CARD-276-cycle2.yml`, reviewed `31897571`,
`aggregate_round: 6`, `round_limit: 6`, **`fix_round_available: false`**.
Score **6.5** against `min_score: 8`. Verdict: *"the question this card exists
to answer is answered NO."*

**What converged, and the review says so plainly:** fix round 1 closed every
shape cycle 1 named — F-1, F-2 and F-3 all reproduce as closed under the
reviewer's own plants — the cost sequence 760/509/203/201/0/0 re-derived
identically in a second domain by calling `_page_positions` directly, the
chain's bound and cycle check refuse and report (G-7 holds, no silent cap
anywhere in the new mechanism), and the decorated-terminal rule survives the
brief's two attempts to reopen it (the check is on decorator **presence**, so
decorator identity cannot matter).

**What did not:** the hole moved one indirection again, which is this family's
signature across all six appearances. Fix 1 closed cycle 1's Critical by
routing a resolved attribute chain into the own-instance surface rule — and
that rule's authority was built with `ast.walk` over the `ClassDef`, so every
nested `def` anywhere inside the class counted as the class's attribute
surface. Nine such names already stand on `BookPDFGenerator`. **That one
needed nothing appended at all**, because the module's own text supplied the
laundering occurrence, and step 8f's mutant aimed at the authority's breadth
**survived** — proving no assertion in the file could see it.

| cycle 2 finding | severity | disposition |
|---|---|---|
| **F-1** the class's attribute surface is built with `ast.walk`, so nine nested names launder a `setattr` door with no scaffolding and no lever | critical | **CLOSED inline** at `084fa6d7` |
| **F-2** the same Critical one indirection in — a resolving store of the same spelling *inside the calling class* | major | **DECLARED inline** (R9) |
| **F-3** two clauses of the fourth version of the axis-2 sentence are measurably false | major | **CORRECTED inline** |
| F-4 a lever reporting a refusal that is only the plant's own `getattr` | minor | recorded, not taken |
| F-5 | minor | recorded, not taken |

## [CYCLE 2's GATING FINDINGS TAKEN INLINE — 2026-10-25, orchestrator] F-1 at `084fa6d7`, F-2 and F-3 after it

The round budget is exhausted, so these were taken by the orchestrator rather
than by a seventh round. Each is recorded with the measurement that certifies
it, and the one place my own instrument was wrong is recorded too.

### F-1 — closed at `084fa6d7`, free, with the control its surviving mutant proved missing

One condition: the definition must be a **direct member** of the holder. Cost
on this module: **unchanged** — `sites=23 vocabulary=6 refusals=0`, all 36
`DOOR_SHAPES` rows matching their declared outcomes, and all nine spellings
now refusing. The control is
`test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface`: it
derives the nested names from the module's own AST, asserts a non-vacuity
floor, and reds **naming all nine spellings** when the authority is widened
back. Certified in both arms — intact passes, widened fails.

**Not taken, on a measurement:** this arm admits a *decorated* method while
the module-level terminal rule refuses a decorated definition, so the terminal
rule is applied in one of the two places a definition is read. True — but
adding the `decorator_list` gate costs this module **4 refusals on a tree with
no defect in it** (four decorated methods on `BookPDFGenerator`). By CARD-262's
own precedent for choosing a shape by cost, a shape that fires on a clean
module is the wrong shape. Routed to the successor, not absorbed.

### F-2 — DECLARED as R9, re-measured against this card's own HEAD rather than inherited

The cycle-2 report measured F-2 at `31897571`. **`084fa6d7` then narrowed the
surface rule's authority, which is the same mechanism F-2's vehicle travels
through**, so the reading had to be retaken before the declaration could be
written. Taken by driving `_GUARD._plant` / `_outcome` / `_plant_refusals`
outside pytest, every arm printing its own identity first (test file
`9cb9dbf994defb1f`, subject `d8b9ece883241015`, `DOOR_SHAPES` 36,
`CALLEE_EXEMPTIONS` 5):

| arm | outcome at `084fa6d7` |
|---|---|
| C — the same-class resolving store | `()` **silent** |
| C2 — the two-link variant | `()` **silent** |
| attribution control `self._d = None` | `('refusal',)` |
| attribution control `self._d = 1 + 2` | `('refusal',)` |
| lever — drop **only** the terminal class | **exactly 1** attributed refusal, `:6719`, naming its own mechanism |
| module cost | `sites=23 vocabulary=6 refusals=0` — the declaration is **free** |
| all 36 `DOOR_SHAPES` rows | **0 mismatches** |

So F-2 stands at HEAD: `084fa6d7` did not close it as a side effect. The
attribution control is what says the silence is specifically the **resolved
pass** and not the surface rule in general, and the two-link variant is what
says it is the level and not the step count.

**The lever is measured, not asserted.** Exhaustive over all 32 exemption
subsets: **24 expose it**, with exactly **two minimal sets** — `builtins`,
which fires on the plant's own `getattr` and is therefore no lever by cycle
1's F-4 standard, and the terminal class itself, which yields the single
refusal above. That is what makes R9 two-directional rather than an assertion
of silence.

**R9's own two directions certified by mutation**, each killed by its *aimed*
assertion with R9's exact row in the failure cell, target restored and the
restore verified by sha256 (`9be1e17a5c9123fc` before and after):

| mutant | aimed at | result |
|---|---|---|
| M1 — R9's resolving store → an opaque one | the silence assertion | **KILLED**, `At index 5 diff: (…R9…, ('refusal',)) != (…R9…, ())` |
| M2 — R9's `absorbed_by` → a different class | the absorbed assertion | **KILLED**, `At index 2 diff: (…R9…, False) != (…R9…, True)` |

**A defect of my own instrument, recorded because it is this card's family one
level out.** My first certification script reported "SILENCE assert fired" for
M2 as well, and concluded M2 was not killed by its aimed assertion alone. That
was **false, and false in the direction of a finding**: pytest echoes the
*source* of the asserts above a failure, so the silence assertion's message
text appeared in M2's output as echoed source rather than as a fired
assertion. Each failure carries exactly one `AssertionError` and M2's is the
absorbed one. A substring search over pytest output cannot tell a fired
assertion from a printed one — which is the same shape as reading absent
evidence as zero evidence, the trap this card's fix-4 pre-gate recorded.

### F-3 — the fifth version of the sentence, and it counts vehicles instead of claiming an axis

Cycle 2 named two clauses measurably false. Both are corrected, and so is the
third site the report found carrying the same overclaim:

- **`:1203` "One of the two is closed"** — false because the KEY axis has
  **three vehicles, not one**. Two are closed (the unrelated-class vehicle by
  fix 1; the class-surface vehicle by `084fa6d7`) and the third is declared
  (R9). The fifth version states the count and names which mechanism answers
  which vehicle.
- **`:1213` "still false, of exactly that residue"** — `exactly` is the clause
  that failed. The residue is now **two declared rows**, R8 and R9, both
  absorbed by the same exemption class. The word is gone and the rows are
  named.
- **`TestDoorAxis_…`'s class docstring, "this class holds both answers"** —
  corrected to **two of the KEY one's three vehicles**, plus the TERMINAL one.

**Also corrected, which is F-2's remedy item 2 and the reason the prose was
false in three places at once:** the exemption class's reach statement said
its residue was the unseeable-rebind case **alone**. It is two shapes. Fixed
in `anchored_to_a_fixed_point`'s docstring, in `_page_positions`' opening
docstring, and in `CALLEE_EXEMPTION_REACH`'s doc — the class absorbing a shape
its reach statement does not name is CARD-262's F-502 pattern, which is why
all three sites moved rather than the one the finding cited.

**Verified, by node id rather than `-k`** (this board has twice recorded a `-k`
selection collecting nothing and reading as a pass): **19 passed, 0 failed,
175.79 s** across `test_the_declared_blind_spots_are_still_silent`,
`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`,
`test_every_door_shape_is_read_or_refused_and_never_silent`,
`test_no_docstring_names_a_test_that_does_not_exist` (AC-6's own standing
check, which accepts the new references — every test the new prose names
exists), `test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface`
and all 14 parametrisations of
`test_no_door_shape_is_laundered_by_an_unrelated_resolving_occurrence`.

**One claim of mine corrected mid-edit by the file itself:** I first wrote that
`test_a_name_nested_inside_a_method_is_not_the_classs_attribute_surface` lives
in the guard class. It lives in `TestDoorAxis_TheNextIndirectionIsNotSilentEither`
— the very class whose docstring I was correcting — so the docstring now says
"below" and points at it in place rather than across classes. Caught by
reading the class boundaries, not by the prose check, which only verifies that
a named test exists and not that it is where the sentence says.

## [MERGE GATE on `f94e52b5` — 2026-10-25, orchestrator] PASSED

Commit `10a7c324` (one file, **+160/−50**), then main merged in at `f94e52b5`.

**Integration measured before it was taken.** Main had moved **32 commits**
since the fork point `c2cb8e3e`, touching six code paths — `admin/app.py`,
`admin/player_bundle.py`, `admin/templates/book_detail.html`,
`difficulty.py`, `tests/test_difficulty.py`, `tests/test_player_bundle.py`.
**None is this card's file and none is the guard's subject module**
(`admin/book_pdf_generator.py`), so every figure the guard asserts about that
module survives the integration rather than needing re-derivation. The merge
was clean and the branch's only diff against main is still the one test file.

| gate check | result |
|---|---|
| **full suite** at `f94e52b5`, lock written by the gate | **9160 passed, 27 skipped, 0 failed**, exit 0, 26:07 |
| skip count against the baseline | **27 — the baseline exactly** (26 DB + 1 `setrlimit`), where CARD-218's gate saw 101 |
| suite reconciliation | 9160 + 27 = **9187** = the branch's collection count |
| **collection delta** vs main | **+37**, reconciling exactly to this file's 90 → 127 |
| whole-file run at `084fa6d7` | **127 passed, 467.30 s**, exit 0 — the green cycle 2 named as this gate's precondition, owed since `ced5e648` |
| **G-1** `git diff --name-only main...HEAD -- src/` | **0 files** |
| **G-2** `export/layout.py` in the branch diff | 0 — CON-019's tripwires green without being edited |
| **G-4** `pyproject.toml` in the branch diff | 0 |
| **G-5** position-axis structures in `10a7c324` | **no line** touching `BINDERS_READ`, `STRING_FIELDS_READ`, `BINDER_BINDINGS` or `EXEMPTION =` |
| lock hygiene | written by the gate with absolute `worktree:` and `commit:`, trap scoped to a subshell, verified **gone** afterwards |

**The per-commit collection ladder**, which is what makes the +37 structural
rather than asserted: main **90**, fork point `c2cb8e3e` **90** (identical, so
there is no hidden drift under the branch), `ced5e648` **104**, `31897571`
**126**, `084fa6d7` **127**, `10a7c324` **127**. This commit adds **no**
collected test, which is the right answer for a table row and prose —
`test_the_declared_blind_spots_are_still_silent` iterates the table rather than
being parametrised over it.

**A figure of this card's own, corrected at the gate.** The fix-round-1
pre-gate note above calls partition B *"the 33 tests this round added"*. The
collection delta for `31897571` is **+22**. The reconcilable reading is
CARD-264's — 11 of the 33 node ids were *modified* existing tests rather than
added ones — but **only the 22 is verified here**; the split is not. Routed to
CARD-300 rather than restated. It is a small instance of this card's own
family and it is recorded as one.

**G-6, stated rather than quietly resolved.** The guardrail reads *"take no
timing measurements and report no durations"*, and this record reports several
(175.79 s, 467.30 s, 26:07). The reading applied: G-6 bars timing as a
**deliverable or a claim** — CARD-287's scope, which this card must not stray
into — and not gate bookkeeping, since the card's own fix-round-1 pre-gate
recorded `119.51 s` and `393.54 s` under the same guardrail. On the stricter
literal reading the guardrail was already breached before this round and is
breached again here. Either way it is the orchestrator's call being recorded,
not an unnoticed violation: **no duration in this card is used as evidence for
anything**, and the one timing question that matters — the per-test ceiling —
is CARD-292's by name.
