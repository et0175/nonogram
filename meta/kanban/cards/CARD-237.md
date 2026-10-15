# CARD-237: The streaming-shape memory guard measures the export, not CPython's own footprint

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/237-memory-guard-floor-relative
**Worktree:** ../PythonProject4-card-237
**Source:** found in flight at CARD-234's merge gate, 2026-10-15 — owner decision the same day to fix the guard before merging wave 40
**Idea:** —
**Wave:** 40
**Depends on:** —
**Touches:** tests/test_book_pdf_memory.py
**Review score:** —
**Started:** 2026-10-15T11:21:04Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`tests/test_book_pdf_memory.py::TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`
fails **most** full-suite runs on this host and blocks every card's merge gate. Measured
across four full suites at the normal 11 skips, two different branches:

| run | tree | result |
|-----|------|--------|
| 09:20–09:35Z | `card/235` (no CARD-234 code) | FAILED, 279.7 MB |
| 10:15–10:33Z | `card/234` rebased | FAILED, 280.3 MB |
| 10:41–10:56Z | `card/235` | FAILED, 276.1 MB |
| 11:00–11:15Z | `card/235`, tree unchanged from 10:41 | **PASSED** |

One pass in four, on unchanged trees, against a bar of 269.3 MB. It passes alone in 6.75 s,
so isolation is the one condition in which it cannot discriminate anything.

**The failing line is not the test's claim — it is the test's self-invalidation tripwire:**

```python
resident = child.report["resident"]
assert resident * CHILD_HEADROOM < CHILD_CAP_BYTES, (
    f"the streaming child peaked at {resident / 1e6:.1f} MB against a "
    f"{CHILD_CAP_BYTES / 1e6:.0f} MB cap — under {CHILD_HEADROOM}x of "
    "headroom, so this test's verdict has started to depend on the "
    "interpreter's footprint rather than on the export's shape"
)
```

The message is correct and the tripwire is working as designed. It has detected exactly the
condition it was written to detect. **What is wrong is the quantity it measures.**

`resident` is the streaming child's TOTAL resident set — interpreter, imports, the corpus
book, and the export. The cap is 32 page bitmaps (807.84 MB). So the assertion compares
(floor + export) against the cap, and the floor is now the dominant term:

- `CHILD_HEADROOM = 3`'s own comment records the measured value as **4.06x** (CARD-198, down
  from 4.7x), i.e. a streaming peak around 199 MB.
- Today the same shape measures 276–280 MB — about **2.9x**. CPython's own footprint has grown
  roughly 80 MB under this test since that number was taken.
- `CHILD_FLOOR_SHARE = 0.25` allows the floor alone up to 201.96 MB before `_habitable` skips.
  So a floor near 200 MB and an export costing ~78 MB sit inside a 269.3 MB bar. The export is
  now the SMALLER half of the quantity being asserted.

**Do not fix this by widening the constant until it passes.** Weakening a guard so a gate goes
green is the specific failure this project's discipline exists to prevent, and a 2.5x constant
would simply fail again on the next interpreter upgrade.

**The fix the code is already set up for.** `_habitable(mechanism)` ALREADY spawns a floor
child — interpreter, imports, corpus book, one page, under the same cap — and already returns
it. And `_the_pair_under_one_cap` **throws that return value away**:

```python
def _the_pair_under_one_cap(mechanism: str) -> Tuple[CappedChild, CappedChild]:
    _habitable(mechanism)            # <-- the measured floor is discarded here
    return (
        _capped_child(STREAMING_SHAPE, mechanism),
        _capped_child(MATERIALISED_SHAPE, mechanism),
    )
```

So the number that makes this guard drift-proof is measured on every single run and then
dropped on the floor. Thread it through and express the headroom against the **export's own
marginal cost** (`streaming.resident - floor.resident`) rather than against the child's total.
That quantity is what "the export's shape" means, it is what the assertion's own message
claims to be about, and it does not move when CPython grows — because the floor grows with it.

Pick and justify the bound in the code's own comment, the way the existing constants are
justified: the claim being protected is that the streaming shape FITS where the materialised
shape dies by orders of magnitude (~305 page bitmaps against 32). A margin on the surviving
half was never what carried that claim, so the bound should be loose enough not to be a
tripwire on normal drift and tight enough to catch a real regression — e.g. the export's
marginal cost staying a small multiple of a single page bitmap, which is the unit the whole
file reasons in.

Keep the tripwire's SPIRIT: if the floor ever genuinely does swallow the cap, the test must
still refuse to render a verdict. `_habitable`'s `CHILD_FLOOR_SHARE` skip is that mechanism
and it should remain.

## Acceptance criteria

- **AC-1** (happy, the guard measures the export): *Given* the streaming child and the floor
  child from the same run, *then* the headroom assertion is computed from the export's marginal
  cost (`streaming.resident - floor.resident`), not from the streaming child's total resident
  set. (test: `TestMemoryGuard_HeadroomIsMeasuredAgainstTheFloor`)
- **AC-2** (guard, the drift that broke it no longer breaks it): *Given* a floor child whose
  resident set is inflated to just under `CHILD_FLOOR_SHARE` of the cap, *when* the streaming
  child's marginal cost is unchanged, *then* the guard still passes — the thing that used to
  fail must now not. (test: `TestMemoryGuard_InterpreterGrowthDoesNotTripTheGuard`)
- **AC-3** (guard, NOT weakened — the important one): *Given* a streaming child whose *marginal*
  export cost is inflated to the materialised shape's order of magnitude, *then* the guard still
  FAILS. Prove the new bound catches a real regression rather than merely tolerating everything.
  (test: `TestMemoryGuard_StillFailsWhenTheExportItselfRegresses`)
- **AC-4** (guard, the skip survives): *Given* a floor child over `CHILD_FLOOR_SHARE` of the
  cap, *then* the test still SKIPS with its existing message rather than passing or failing —
  the self-invalidation mechanism is retained, not replaced.
  (test: `TestMemoryGuard_StillSkipsWhenTheFloorSwallowsTheCap`)
- **AC-5** (happy, it actually passes now, repeatedly): *Given* the real test on this host,
  *when* it is run inside a full suite **three** times, *then* it passes all three — the flake
  is gone, not merely re-rolled. Record the three runs and their reported margins.
  (test: the real `test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`,
  evidenced by three recorded full-suite runs)
- **AC-6** (guard, the twin keeps working): *Given* the `RLIMIT_AS` twin test that runs the same
  pair under the kernel's bound where available, *then* it is updated consistently and still
  expresses the same claim. (test: the twin test in the same file, named in the implementation)

## Guardrails

- G-1: The test's CLAIM does not change. This card may change only what the headroom tripwire
  measures. The pair-under-one-cap structure, the 808 MB cap, the materialised shape dying, and
  the page count being read back out of the written PDF all stay exactly as they are.
- G-2: Do not widen `CHILD_HEADROOM` (or the cap) as the fix. If the final implementation still
  carries a constant, it must be justified against a *measured* quantity in its own comment, as
  every other constant in this file is.
- G-3: `_habitable`'s `CHILD_FLOOR_SHARE` skip stays. A test that cannot discriminate must keep
  refusing to render a verdict.
- G-4: No production code. `src/**` is out of scope entirely — this is a test-integrity card.
- G-5: Do not touch the render-heavy frozen set beyond this one file (CARD-218/219's footprint),
  and do not touch the browser family (CARD-235's, in flight).
- G-6: No new dependency (ADR-0006/R1).

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)
- CON-005 — the solver's uniqueness property is untouched by this card (check: review-lens)

## Architecture context

- **FR:** — (untraced test-integrity card; its done-ness is the ACs above, not an FR)
- **NFR:** NFR-008's neighbourhood — this file is the executable evidence for the book export's
  memory envelope, so the guard's integrity is what makes that evidence worth anything.
- **Components:** COMP-009 (tests only).
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is P1 and ahead of the wave] It is not a defect in any card's code. It is a gate
  that returns a false red about three times in four, and the merge gate runs once per card with
  16 cards left in the interior redesign. Left alone it would have produced roughly a dozen
  spurious investigations, and the cheapest of those already cost CARD-234 a full gate cycle
  plus a wrong diagnosis from me.
- [How it was found] CARD-234's merge gate went red on it. The first diagnosis — mine — blamed
  concurrent load from a sibling card, which was wrong twice over: the lock had not been
  violated, and the test fails *more* on a quiet host because more of the suite actually runs.
  The CARD-235 agent then volunteered the datum that settled it, from a solo locked run on a
  branch carrying none of CARD-234's code. Both agents independently located the defect in the
  3x constant rather than in the export, and the owner chose to fix it before merging.
- [The clue was in the constant's own comment] `CHILD_HEADROOM = 3` is documented as having
  measured 4.06x, itself noted as *down* from 4.7x. A margin recorded as shrinking across two
  cards is a margin on its way to zero; nobody read it as a prediction.
