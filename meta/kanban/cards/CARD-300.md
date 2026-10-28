# CARD-300: The door axis's seventh appearance, priced before it is attempted — R9's closure, the surface rule's two unequal halves, and whether this guard should survive the vector interior at all

**Status:** parked
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/300-door-axis-seventh
**Worktree:** —
**Source:** orchestrator, 2026-10-25, from CARD-276's merge as a declaration. CARD-276 landed at cycle 2's **6.5, NOT CERTIFIED**, with its round budget spent (6 of 6) and **AC-1 unsatisfied by its own review's verdict** — the level is unresolved at the sixth appearance. This card is where that goes, so the residue is owned rather than inherited by whoever next opens the file.
**Idea:** —
**Wave:** —
**Created wave:** 58
**Deferred waves:** 5 <!-- corrected 2026-10-28: created at wave 58 and passed over for 59, 60, 61, 62 and 63 while this counter still read 0. A deferral counter that never increments is the silent-drift shape this board tracks, and it made the card look freshly queued rather than five times skipped. -->
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Read this before deciding to do it at all

**The honest first question is not "how do we close R9" but "should this guard
exist in the form the vector interior leaves it".** CARD-276 is the family's
sixth appearance and six rounds bought a narrowing, not a closure. A seventh
round on the same mechanism, in the same file, is the shape this board has
already paid for — so this card is written to be *priced* first and attempted
second, and declining it with a recorded reason is a legitimate outcome.

Three facts bear on that decision, and they were measured, not assumed:

1. **The guard's subject is medium-independent.** It checks that a page
   *position* claim cannot be laundered by a geometry door installed on the
   generator from outside the module's text. Page positions survive
   vectorisation — a vector interior still has front matter and page numbers —
   and ADR-0042/R6 forbids measuring *ink*, which is a different axis. So the
   vector phase does **not** make this guard moot.
2. **But its subject class is about to be reshaped.** CARD-294..298 rewrite the
   interior drawing path and CARD-298 makes `_write_pdf` choose a medium per
   page. Cycle 2's F-1 was specifically about **nine names nested inside
   `BookPDFGenerator`'s methods** (`produce` in `interior_stream`; `set_page`,
   `line_image`, `technique_rows`, `fits_width` in `create_guide_page`;
   `paragraph`, `picture`, `space`, `technique` in `set_page`). Those nine are
   a fact about today's class body. Closing R9 against them now means
   re-deriving the authority after the phase lands.
3. **The file is contended three ways.** `tests/test_book_export_interior_cover.py`
   holds **34 of the 315 interior pixel sites** and is simultaneously
   **CARD-287's** (344.29 s, 24.4 % of the suite), **CARD-292's** (the per-test
   ceiling) and in CARD-299's path (R6's default-deny guard would red on those
   34 sites). `meta/profiling/adr-0042-migration-census.md` §"What this implies
   for the card plan" argues that the conversion and the cheapening are **one
   piece of work done once**. A door-axis round that opens this file alone pays
   the serialization cost a fourth time.

**The recommendation this card carries into its own dispatch:** sequence it
*with* CARD-287/292/299 on this file rather than before them, and let whoever
takes it decide whether R9's closure is worth a mechanism change at all or
whether the right move is to keep the declaration and spend the round on the
file's cost instead. That is a judgement for a round with the measurements in
front of it, which is why this card does not pre-commit to closing anything.

## What is actually owed

### 1. R9 — the residue CARD-276 declared, with its measurement already taken

`MEASURED_BLIND_SPOTS`' R9: *a resolving store of the same spelling inside the
**calling** class*. Fix round 1 made the attribute branch's `continue`
conditional on a refusal so a resolved chain falls through to the own-instance
surface rule — and that fallback is **defeated by construction** exactly there,
because the store that resolves the chain *is* the store that puts the spelling
on the surface. Both of its conditions are met by one line, so neither can fail
independently.

Measured at `084fa6d7`, by driving the guard's own classmethods outside pytest
with every arm printing its identity first — **this is the baseline a closure
must move**, and it is already paid for:

| arm | outcome |
|---|---|
| C — the same-class resolving store | `()` silent |
| C2 — the two-link variant | `()` silent |
| attribution control `self._d = None` | `('refusal',)` |
| attribution control `self._d = 1 + 2` | `('refusal',)` |
| lever — drop only the terminal class | exactly 1 refusal at `:6719`, naming its own mechanism |
| module cost | `sites=23 vocabulary=6 refusals=0` |

The attribution control is what says the silence is the **resolved pass** and
not the surface rule in general. The two-link variant is what says it is the
level and not the step count — so a fix that closes C and leaves C2 open is
this family's seventh appearance and should be recognised as such at review.

**The cost rule this card inherits** (CARD-262's precedent, applied twice
since): choose the shape by what it costs on a defect-free module. A shape that
fires on a clean tree is the wrong shape.

### 2. The surface rule's two unequal halves — recorded by CARD-276 and deliberately not taken

`084fa6d7` closed F-1 by requiring a definition to be a **direct member** of
the holder. Cycle 2 observed, and the closure's own commit message records,
that **this arm admits a decorated method while the module-level terminal rule
refuses a decorated definition** — so the terminal rule is applied in one of
the two places a definition is read.

It was not taken, on a measurement: adding the `decorator_list` gate costs this
module **4 refusals on a tree with no defect in it** — four decorated methods
on `BookPDFGenerator`. By the cost rule above that makes it the wrong shape as
stated. It needs either an exemption with its own control or a different
formulation. **Deciding which is this card's, and it is a design question, not
a patch.**

### 3. AC-5's six cells — unverified on CARD-276 and inherited honestly

CARD-276's AC-5 asked that N8, N12b, N13, N14, N16 and N18 be fired against
CARD-262's committed `ac479658` and against CARD-276's HEAD. **Cycle 2 reports
they were not re-fired**, and names it *"the largest single thing I did not
measure"*: the round's correction of CARD-262's N8 from 2 FAIL to 1 remains an
unverified figure on a merged card's behalf. Either fire them or **declare them
unfired with a reason** — a third round inheriting them silently is the
declaration-outliving-its-hole defect that `MEASURED_BLIND_SPOTS` exists to
prevent.

### 4. The pre-gate note's own loose figure, found at CARD-276's merge gate

CARD-276's fix-round-1 pre-gate calls partition B *"the 33 tests this round
added"*. The collection delta for that commit is **+22** (104 → 126 on this
file). The reconcilable reading is CARD-264's — 11 of the 33 node ids were
*modified* existing tests rather than added ones — but **only the 22 was
verified**, not the split. Correct the note or verify the split; do not restate
33 as an addition count.

## Acceptance criteria

- **AC-1** (the decision is recorded before the work): *Given* this card's
  three framing facts re-checked against the tree as it then stands, *then* the
  card records an explicit decision to **close R9**, to **keep the declaration
  and re-point the round at the file's cost**, or to **retire the guard's door
  axis** if the vector phase has made it unverifiable — with the measurement
  that decides it. (evidence: the decision and its figures on the card. A card
  that starts editing the mechanism without this is doing the sixth round
  again.)
- **AC-2** (only if AC-1 chose closure — the level, not the instance): *Given*
  the closure, *then* **C and C2 are both read or refused, never silent**, and
  so is a plant built by appending two further assignments to either; and the
  cost on a defect-free module is stated, with newly refused sites enumerated
  rather than summarised if it is not 0. (test:
  `test_every_door_shape_is_read_or_refused_and_never_silent` and
  `TestDoorAxis_TheNextIndirectionIsNotSilentEither`, extended. **Two mutants
  per ADR-0039/R1, each DELETING a mechanism the claims name** — a mutant that
  only breaks what the fix added certifies the addition and says nothing about
  load-bearingness, which is CARD-264's recorded orchestrator fault and applies
  to every fix brief on this family.)
- **AC-3** (the declaration does not outlive its hole): *Given* a closure of
  R9, *then* `test_the_declared_blind_spots_are_still_silent` **reds on R9** and
  the row leaves `MEASURED_BLIND_SPOTS` and `BLIND_SPOT_LABELS` **in the same
  commit** as the mechanism that closes it, and the reach statements in
  `anchored_to_a_fixed_point`, `_page_positions` and `CALLEE_EXEMPTION_REACH`
  drop the shape in that same commit. (test: the named test, red then updated.
  All three prose sites are listed because CARD-276 measured that this class's
  reach statement was false in **three places at once**.)
- **AC-4** (the two halves agree, or the asymmetry is declared): *Given* the
  surface rule and the module-level terminal rule, *then* either both apply the
  decorator check or the difference is a named exemption with its own control
  and its measured cost. (evidence: the control, or the exemption row and the
  4-refusal figure re-measured.)
- **AC-5** (CARD-276's six cells): *Given* `ac479658` and CARD-276's merge
  commit, *then* N8, N12b, N13, N14, N16 and N18 are each fired and recorded
  with the assertion node they kill under a stated instrument domain — **or**
  declared unfired with a reason. (evidence: the mutant table; no new test.)
- **AC-6** (no figure restated without a reading): *Given* the diff, *then*
  every count it asserts about the tree is re-derived through a deployed
  enumerator rather than copied, the partition-B figure above included. (test:
  the existing prose and census checks; evidence for the rest.)

## Guardrails

- G-1: **No production behaviour change.** `git diff --name-only main...HEAD -- src/`
  must be **empty**, as it was for CARD-206, CARD-262 and CARD-276. This card
  changes what the guard sees, never what the generator does.
- G-2: Do not edit `src/nonogram/export/layout.py`; keep the three CON-019
  byte-identity tripwires green **without editing them**.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-5: **A cap is not a closure.** If a fixed point needs a bound, that bound
  **refuses** and reports itself, as `RECEIVER_RESOLUTION_DEPTH` and
  `ANCHOR_RESOLUTION_DEPTH` already do. Re-introducing a silent cap fails this
  card whatever else it achieves.
- G-6: **Do not weaken an arm to make a broader claim true.** The position-axis
  closure and CARD-276's transitive fixed point stay byte-identical unless this
  card has a measured reason, stated.
- G-7: Do not open this file concurrently with CARD-287, CARD-292 or CARD-299 —
  it is a declared `conflict.hotspots` neighbour in effect even where the glob
  does not name it, and four cards editing it in sequence is the cost the census
  argues against.
- G-8: **Take no timing measurements and report no durations** unless this card
  deliberately takes the cost route, in which case CARD-287's instrument is the
  one to use rather than a new one.

## Architecture context

- **ADR:** ADR-0039 (R1 controls that can fail, R2 default-deny, R3 an exemption
  is a claim and carries a control for what it must not absorb), ADR-0040,
  ADR-0042 (the vector interior, which decides fact 2 above)
- **Components:** COMP-005
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—


## [PRICED — 2026-10-28] **PARKED.** The mechanism half is declined; AC-5 is split out

This card asked to be priced before it was attempted. It has been, and the answer
is **don't give it a wave as written.**

**What it buys is bounded by its own guardrail.** `G-1` mandates that
`git diff --name-only main...HEAD -- src/` be **EMPTY**, so the entire card buys
**zero production behaviour** by construction. It changes what a guard sees, never
what the generator does.

**The estimate is 1d; the family's observed spend is the real figure.** CARD-206
(0.5d) → 8.5 at cycle 3/3, escalated, resolved by slice. CARD-262 (1d) → 9.3 at
cycle 3/3. CARD-276 (1d) → **6.5, NOT CERTIFIED**, round budget spent 6 of 6,
merged on a recorded gate decision with AC-1 unmet. **~2.5d of estimate against
~12 review rounds, and the most recent did not certify.** This is the *seventh*
appearance of the same mechanism in the same file, and the card says so itself:
"six rounds bought a narrowing, not a closure."

**Two cost multipliers specific to now.** The file is **6852 lines** and is the
suite's dearest; AC-6 requires every count re-derived through a deployed
enumerator, and that module's call figures have **moved twice since this card was
written** — CARD-227 took them 770→772 and CARD-305 772→776 — so any round pays
that re-measurement and **pays it again when CARD-298 lands**. And `G-7` forbids
opening the file concurrently with CARD-299 (wave 66), so the earliest honest wave
for the mechanism half is **67**, behind both.

**Its framing facts were re-measured, and two still hold exactly while one changed
in the card's favour.** The nine nested names are **still exactly nine** (an `ast`
walk over current main — CARD-227 and CARD-305 both edited that module and added
only calls and comments, no nested defs). The 4-refusal decorator figure is **still
exactly four**, and they are now **named for the first time**:
`interior_bitmap_mode`, `_grid_size`, `_payload`, `_puzzle_payload` — which makes
the card's own "wrong shape as stated" judgement checkable at last. But **§3's
"contended three ways" is now one way**: CARD-287 and CARD-292 are both `done`,
leaving only CARD-299. And the card's own recommended *alternative* use of the
round — "spend it on the file's cost instead" — is **already banked**: wave 62 took
the suite −26.8 %, so the 344.29 s / 24.4 % figure §3 quotes is stale and the
cheapening it proposed has happened. That alternative is no longer a reason to take
the card.

**AC-1's own question, answered: keep the declaration.** R9 is a guard's
self-declared blind spot with a reproducible baseline and an attribution control
proving the silence is the resolved pass. **That is the discipline working, not a
hole** — and closing it buys a cleaner guard, not a safer product, which `G-1`
guarantees. §2's asymmetry is explicitly "a design question, not a patch", and the
shape as stated costs four refusals on a defect-free module, which the inherited
cost rule already disqualifies. Fact 2's risk is also still live: CARD-298 makes
`_write_pdf` choose a medium per page, and `produce` — one of the nine — lives in
`interior_stream`, so closing R9 against today's nine means re-deriving the
authority one wave later.

**AC-5 is split out and belongs with the dead-check-ref sweep, not behind an
architectural redesign.** It is the only part with real epistemic value and the
cheapest (~0.25d): fire CARD-276's six unfired mutants (N8, N12b, N13, N14, N16,
N18) against `ac479658` and CARD-276's HEAD, **or declare them unfired with a
reason.** Its own evidence line says "the mutant table; no new test" — no mechanism
change, no `src/` edit, no new test, no design question. It earns a slot on its own
because CARD-276's cycle 2 called this "the largest single thing I did not
measure", and what is unverified is **a correction of CARD-262's N8 from 2 FAIL to
1 — a live figure standing on a merged card's behalf.** Queued in
`meta/kanban/backlog.md`.

**Revisit trigger for the mechanism half:** after **CARD-298** merges, and only if
the nine nested names have actually moved. Declining with a recorded reason is an
outcome this card explicitly licenses.
