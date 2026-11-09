# CARD-361: 22 refs with no definition anywhere produce no finding at all, because `trace.py` only asks the resolver about `status: covered` entries

**Status:** skipped
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** architectural
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Surfaced by CARD-335's review cycle 1 while refuting that round's F-8, and explicitly flagged as **not** CARD-335's: *"a third blind spot in the same detector, independent of revival."* The reviewer found it by patching `CodeSearch.exists` to report refs dead and discovering that eight of them produced no ERROR — because the entry declaring them is `status: partial`.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/trace.yml, meta/architecture/requirements.yml, tests/test_check_ref_resolution.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 tech-debt triage. No work is owed here.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The blind spot, measured

`trace.py`'s `_check_covered_tests` is scoped **by name and by docstring** to `status: covered`
entries: *"covered → every listed test must actually be defined in the codebase (git grep) —
catches a `covered` that names tests which were never written."* Verified at the station: the
function's own documentation says so, and the project has no `.skills.yml`, so the
requirements-side channel is WARN rather than ERROR.

**The consequence, measured by CARD-335's reviewer:** **22 refs resolve `False` today — no
definition anywhere in the codebase — and the board reports 0 errors.** Their trace entries are
`status: partial` or carry no `status:` at all (e.g. the superseded FR-001 entry), so the walk
`continue`s **before** it asks the resolver.

So a ref that names a test nobody ever wrote is reported **only if** someone also claimed the
requirement was fully covered. **Claiming less protects the claim from being checked.**

**Re-derive the 22.** It is a dated reading and the set matters more than the count.

## Why this is the third blind spot in one detector, and why that matters

| blind spot | mechanism | status |
|---|---|---|
| committed artefacts revive dead refs | the resolver is a **text** search over tracked files | **bounded** by CARD-335 (10 refs pinned, cause-side door shut for three spellings) |
| a blown batch answers `None` for 200 names | a linear budget against a super-linear cost | **fixed** by CARD-335 (`meta/profiling/*.txt binary`) |
| **a ref declared only on a non-`covered` entry is never asked about** | `status != "covered"` → `continue` | **this card** |

All three make a dead ref read as alive. The first two are now closed or bounded, which is what
makes this one visible — and it is the one that needs **no** artefact, **no** timeout and **no**
accident. It is the detector's documented scope.

## A fourth blind spot in the same detector, routed here by CARD-335's merge gate

CARD-335 landed a census guard over **the ignore rules**, so a tracked artefact whose path **no
rule matches** never enters the census and the cell stays green. Measured with
`git check-ignore --no-index`: `meta/review/<CARD-NNN>/cycle1.yml` (nested — `meta/review/*.yml`
does not cross `/`) and `meta/measurements/durations.txt` are both addable with **plain
`git add`, rc 0, no warning**.

**Both directories are flat today, so there is no live hole** — and a new artefact that *revives*
a ref still reds the pre-existing CARD-308 gate, so the **outcome** is guarded even where the
**cause** is not.

**But the bound was recorded docstring-only, so ADR-0039/R3 is only partly satisfied:** R3 asks
that a bound carry **its own failing control**, and this one has none. CARD-308's gate is named as
the outcome-side backstop instead. **That gap is this card's to close or to decline with a
reason** — a bound without a control that can fail is the defect this family keeps producing, and
declining it is a legitimate answer only if stated.

## The design question, which this card must answer before it changes anything

**`covered` meaning "I assert every criterion has a live test" is a coherent contract**, and
hardening it is what `_check_covered_tests` was built for. The question is whether a
**`partial`** entry should assert anything about the tests it *does* list.

Three positions, and the card must choose with a reason:

1. **A listed test must exist regardless of the entry's status.** `partial` then means "not every
   criterion is covered", not "the things I named might be fiction". Strongest, and it would turn
   22 silent refs into findings today — so **the migration cost is the real question**, not the
   principle.
2. **Keep the scope and make the silence loud.** Report, at a lower severity, that N refs on
   non-`covered` entries were **not checked** — so the number is visible rather than absent.
   Cheapest honest option.
3. **Declare the bound and pin it.** State in the validator's own docs that non-`covered` entries
   are unchecked, and add a control asserting the count so it cannot grow unremarked.

**Position 1 is a `forge_1` change and this board never edits `forge_1`** — it is the validator
of record and read-only. So if the answer is 1, this card's deliverable is a **finding and a
measurement handed upstream**, plus whichever of 2 or 3 can be done here. **Say that explicitly
rather than discovering it halfway.**

## What to implement

1. **Re-derive the 22**, naming the instrument, and classify each: is the ref dead because the
   test was renamed, never written, or superseded? The three have different answers.
2. **Measure the migration cost of position 1** — how many findings would appear if every listed
   test had to exist. CARD-335's reviewer measured the revival-side equivalent at **+3 dead-ref
   WARNs**; this is the larger sibling of that number and nobody has it.
3. **Choose a position and say why the other two lose.**
4. **Whatever you choose, leave a control.** A bound declared without a control that can fail is
   the defect this family keeps producing.

## Acceptance criteria

- **AC-1** *Given* the live authorities and the live resolver, *then* the set of refs that
  resolve `False` **and produce no finding** is derived, named and classified by cause — not
  just counted.
  (test: named by the implementation; state it)
- **AC-2** *Given* position 1, *then* its migration cost is **measured** (how many findings
  appear), and the figure is reported whether or not position 1 is chosen.
  (test: named by the implementation; state it)
- **AC-3** *Given* the chosen position, *then* a control exists that **reds** when the unchecked
  population grows — derived from the authorities rather than a hard-coded list (ADR-0039/R2).
  (test: named by the implementation; state it)
- **AC-4** *Given* anything this card cannot fix because it lives in `forge_1`, *then* it is
  stated as a finding with its measurement, and **`forge_1` is not edited**.
  (check: review-lens)
- **AC-5** *Given* CARD-335's two closed blind spots, *then* this card's change does not reopen
  either — the 436-warning repair holds and the bookkeeping-only gate still reds on a revival.
  (test: `tests/test_check_ref_resolution.py`)
- **AC-6** *Given* CARD-335's AC-4 reach bound (a tracked artefact whose path no ignore rule
  matches), *then* it either **gains a failing control** — a planted nested artefact path makes
  something red — or the card states the measured reason it cannot, naming CARD-308's gate as the
  outcome-side backstop. **Docstring-only is what it has now and is what ADR-0039/R3 does not
  accept.**
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — **`/Users/omelnikova/MyProjects/forge_1` is READ-ONLY.** It is the validator of
  record. A fix that belongs there is a finding handed upstream, never an edit.
- **G-2** — Do not raise a severity to make the problem visible. Turning WARNs into ERRORs
  without deciding position 1 is a change of contract disguised as a fix.
- **G-3** — Do not repair a dead ref by deleting the claim that names it. A ref pointing at a
  test nobody wrote is information; the fix is to write the test, retire the criterion, or
  record the gap — each with a reason.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations.
- **G-6** — A full suite needs the board's lock (structured, worktree identity, no pid). Never
  set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard
  fires in `pytest_configure` for **any** selection.
- **G-7** — **When comparing validator WARN sets, match `^[[:space:]]*\[WARN`** (the validator
  indents two spaces, so a bare `^\[WARN` matches nothing and `comm` then compares empty with
  empty and reports clean), and **assert both sides non-empty before comparing.**

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0038/R8 — findings are reported loudly, never silently absent (check: review-lens)

## RETIRED 2026-11-09 — tech-debt triage

A guard over the test tooling, not the book or the player; under the owner's rule (keep a test only if its claim is a live product decision) it is not worth building.
