# CARD-237: The streaming-shape memory guard measures the export, not CPython's own footprint

**Status:** review
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

- [Orchestrator error, corrected] **My own card body got the arithmetic wrong, and the
  implementer caught it.** I wrote "a floor near 200 MB and an export costing ~78 MB … the
  export is now the SMALLER half of the quantity being asserted." Measured: the floor is
  **110.0–110.6 MB** (4.36–4.38 page bitmaps, 13.7% of the cap), and the export's marginal cost
  is **68.3–148.1 MB**. So the export is the LARGER and noisier half, not the smaller one.
  Where I went wrong: I reasoned "the floor must be under 202 MB or `_habitable` would skip",
  then quietly used that CEILING as an estimate of the value. A bound is not a measurement. I
  did at least write "verify that rather than assuming it" into the brief, which is the only
  reason the error cost nothing.
  The DIAGNOSIS survives intact and is in fact strengthened: the guard was asserting the child's
  total, the floor is the *stable* term (it moved 0.6 MB across nine runs), so subtracting it
  removes the interpreter's footprint without importing new noise. But the consequence differs
  from what I predicted — the bound had to be sized against the INSTRUMENT'S noise rather than a
  tight multiple of a quiet figure, because `ru_maxrss` is a peak and how much of 307 freed
  bitmaps the allocator returns to the OS depends on what else is resident. That variance is
  also the mechanism behind the original flake.
- [Review score] — (cycle not yet run)
- [Build gate] AC-5: **three consecutive locked solo full suites, all green**, on byte-identical
  code (verified against a saved copy):
    run 1  13:06:40–13:24:16Z  17m32s  7162 passed, 11 skipped  export margin 5.30 / 16 bitmaps
    run 2  13:25:22–13:43:37Z  18m10s  7162 passed, 11 skipped  export margin 3.44 / 16
    run 3  14:01:50–14:18:35Z  16m37s  7162 passed, 11 skipped  export margin 5.15 / 16
  Plus two earlier full suites on near-final code (margins 3.41 and 5.87). **Five green where
  the old guard was 1 in 4.** The 5.87 datum is why the bound is 16 and not 8 — the agent chose
  8 first and discarded it after a run measured 5.04, on the reasoning that 8 "would have
  shipped the same flake one interpreter later". That is the failure mode of the constant it
  was replacing, recognised and avoided rather than repeated.
- [Guard] G-2 held in the strongest form available: `CHILD_HEADROOM` is **removed, not widened**.
  The cap (32), `CHILD_FLOOR_SHARE` (0.25) and the test's claim are untouched.
  The new bound's justification is the part I find convincing — it is not a tuned number but a
  closed argument: 16 page bitmaps for the export plus the 8 that `CHILD_FLOOR_SHARE` permits the
  floor is 24 of the cap's 32, so whenever BOTH guards pass, the child is *proved* to fit the cap
  with a quarter unused. That reconstructs exactly the whole-child margin the old 3x constant
  asserted directly, out of two halves neither of which drifts with CPython.
- [Guard] AC-3 — the criterion I said I would read first, and it holds. The regression mutant was
  applied at the real measurement seam inside `_capped_child` (not the fabricated-child seam the
  unit tests use), and the real test went red. The agent then walked the mutant down to find
  where the guard stops biting: **red at +14 retained pages (17.88 bitmaps), green at +12
  (15.9)** — so it fires at roughly 13 of 307 pages retained, a **4% shape regression**, two
  orders of magnitude short of the list shape it is contrasted against. A bound that tolerates
  everything was the outcome I refused to accept; this one demonstrably does not.
  Two further real-path mutants: +80 MB on both children (CPython grows) → GREEN at a 284.0 MB
  total **that the old bound rejected**, which is AC-2 demonstrated live rather than argued; and
  +92 MB → SKIPPED with the unchanged message, so G-3's self-invalidation still fires ahead of
  any verdict.
- [Observability] the guard now prints its margin on a PASSING run, not only on failure. Worth
  noting as the actual root cause of the two gate cycles this cost: the floor was measured and
  discarded, and the margin was only ever printed when it had already failed. A number computed
  and thrown away is a number nobody can act on.

### Implementation notes (carried from the worktree)

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

### CARD-237 implementation notes (agent, 2026-10-15)

- **[The measured floor — the number the card's argument rests on]** The floor child
  (interpreter, imports, corpus book, one drawn page, under the same 807.84 MB cap) measures
  **110.0–110.6 MB = 4.36–4.38 page bitmaps, 13.7 % of the cap**, and it moved by 0.6 MB across
  every run taken for this card — solo, whole-file, and four full suites. The card expected
  ~200 MB; it is not 200 MB, and that matters in a way that strengthens the card's diagnosis
  rather than weakening it: the floor is the *stable* term, so subtracting it removes the
  interpreter's footprint without importing any new noise. `CHILD_FLOOR_SHARE = 0.25` is
  therefore still 1.8x away from skipping, and the skip was confirmed to fire at a floor of
  202.2 MB (see the mutants below).
- **[The measured export marginal cost]** `streaming.resident - floor.resident` measured
  **2.70, 2.85, 3.22, 3.41, 3.44, 5.04, 5.15, 5.30 and 5.87 page bitmaps** (68.3–148.1 MB)
  across nine runs of the pair. The spread is the instrument's, not the export's: `ru_maxrss`
  is a peak, and how much of 307 pages' worth of freed bitmap the allocator returns to the OS
  depends on what else is resident — which is exactly why the OLD bound failed inside a busy
  suite and passed solo. The streaming child's *total* ranged 178.7–258.5 MB here against the
  old 269.3 MB bar: the old guard was not failing because of the export at all.
- **[The bound and its justification, in page bitmaps]** `CHILD_EXPORT_COST_IN_PAGES = 16`
  (403.92 MB). It is the largest bound that keeps the two guards' arithmetic closed: 16 plus
  the 8 page bitmaps `CHILD_FLOOR_SHARE` permits the floor to be is 24 of the cap's 32, so
  whenever both guards pass, the streaming child is *proved* to fit the cap with a quarter of
  it unused — the whole-child margin the old 3x constant asserted directly, reconstructed from
  two halves, neither of which drifts with CPython. Against measurement it is 2.4x the largest
  export cost on record (~6.56 bitmaps, derived from the card's worst red total of 276.1 MB
  less the floor measured here) and 19x below the ~307 bitmaps of the shape it must separate
  the export from. It was NOT sized off the quiet-run figure, deliberately: that is the figure
  that mis-sized the old constant.
- **[G-2 compliance]** `CHILD_HEADROOM` was not widened — it is gone, replaced by a constant on
  a different quantity, with its own measured justification table in its comment.
  `CHILD_CAP_IN_PAGES` (32), `CHILD_FLOOR_SHARE` (0.25) and the test's claim are untouched.
- **[AC-3 mutants, on the REAL path]** The streaming child's reported resident set was inflated
  inside `_capped_child` (the measurement seam — not the fabricated-child seam the unit tests
  use) and the real test run:
  - `+307 page bitmaps` (the whole book retained) → **RED**:
    `AssertionError: the export itself cost 7824.0 MB (309.92 page bitmaps) in the capped child
    — the streaming child's 7934.5 MB less the floor child's 110.5 MB — against a bound of 16
    page bitmaps (404 MB). The export, not the interpreter, has grown into the cap, so this
    test's verdict is no longer about the export's shape / assert 7824041304 < 403920000`
  - `+14 page bitmaps` → **RED** at 17.88 bitmaps; `+12` → green at 15.9. So the guard bites at
    roughly a 13-of-307-page retention — a 4 % shape regression, two orders of magnitude short
    of the list shape.
  - `+80 MB on both children` (CPython grows) → **GREEN**, floor 7.54 bitmaps (23.6 % of the
    cap), export 3.71, streaming total 284.0 MB — a total the old 3x bound rejected. That is
    AC-2 demonstrated on the real path.
  - `+92 MB on both children` → **SKIPPED** with the existing message (floor 202.2 MB, over
    25 % of the cap). G-3's self-invalidation still fires, and fires before a verdict.
  - Unit-level mutants, each reverted: asserting on the child's total again turns 5 of the 8
    new tests red; `CHILD_EXPORT_COST_IN_PAGES = 320` (the "weaken until green" fix) turns 3
    red; deleting the floor-share skip turns AC-4's test red.
- **[AC-5 — three consecutive locked solo full suites, identical code]**
  | run | window (UTC) | pytest | result | reported margin |
  |-----|--------------|--------|--------|-----------------|
  | 1 | 13:06:40–13:24:16 | 17m32s | 7162 passed, 11 skipped | export **5.30** bitmaps (133.7 MB) of 16; floor 4.37 (13.7 %); total 244.1 MB |
  | 2 | 13:25:22–13:43:37 | 18m10s | 7162 passed, 11 skipped | export **3.44** bitmaps (86.8 MB) of 16; floor 4.37 (13.7 %); total 197.2 MB |
  | 3 | 14:01:50–14:18:35 | 16m37s | 7162 passed, 11 skipped | export **5.15** bitmaps (130.0 MB) of 16; floor 4.37 (13.7 %); total 240.4 MB |
  Two earlier full suites on near-final code (11:29–11:45Z, margin 3.41; 12:48–13:05Z, margin
  5.87) also passed, so it is 5 for 5 where the old guard was 1 in 4. The margin is printed by
  the test on every run (`CARD-237 margin [sentry]: …`, visible under `-rP`) so the next drift
  is seen coming instead of arriving as a red gate.
- **[Why the guard now reports its own margin]** The defect was undiagnosable for two gate
  cycles because the floor was measured and discarded and the margin was only ever printed on
  failure. Both are now visible on a passing run.
