# CARD-237: The streaming-shape memory guard measures the export, not CPython's own footprint

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/237-memory-guard-floor-relative
**Worktree:** —
**Source:** found in flight at CARD-234's merge gate, 2026-10-15 — owner decision the same day to fix the guard before merging wave 40
**Idea:** —
**Wave:** 40
**Depends on:** —
**Touches:** tests/test_book_pdf_memory.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-15T11:21:04Z
**Closed:** 2026-10-15T16:36:28Z
**Actual:** 0.7d
**Merge commit:** 194cb40
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
- **AC-5** (happy, it actually passes now, repeatedly) — **AMENDED at review cycle 1, 2026-10-15,
  because as originally written this criterion was blind to the defect the review then found.**
  *Given* the real test and every new guard test this card adds, *when* each is run **three times
  inside a full suite AND at least five times solo (single-file, quiet host)**, *then* all runs
  pass. Record every run and its reported margin.
  (test: the real `test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under` plus
  all four `TestMemoryGuard_*` classes, evidenced by recorded runs in BOTH conditions)
  *Why amended:* the original said "inside a full suite three times" only, reasoning from the old
  guard's failure mode, where host LOAD produced the red. That certified the wrong direction. The
  review found a new flaky test whose polarity is reversed — it passes under load (a busier host
  means a higher peak means a larger measured marginal cost) and fails SOLO, which is the
  single-file run that is this file's own debugging path. Five full suites passed and would have
  passed forever. **"Flaky" has no inherent polarity, so a flake criterion must exercise both
  conditions**, and the cheap direction is the one nobody runs.
- **AC-6** (guard, the twin keeps working) — **AMENDED at the AC gate, 2026-10-15: the criterion
  as I first wrote it was unverifiable on this platform, which is a defect in the requirement and
  not in the code.** *Given* the `RLIMIT_AS` twin test that runs the same pair under the kernel's
  bound, *then* (a) it is updated consistently with the new guard — same tuple shape, same guard
  call, same claim — demonstrated by READING the diff; and (b) where the kernel cannot enforce the
  cap, it SKIPS with a named reason naming the limitation and the test that carries the claim
  instead, demonstrated by observing that skip under `-rs`. Execution of the kernel-enforced path
  is explicitly **NOT** claimed on a host whose kernel refuses it.
  (test: `test_the_same_pair_under_an_address_space_cap_the_kernel_enforces` — read for (a),
  its `-rs` skip line for (b))
  *Why amended:* the original said "updated consistently and still expresses the same claim",
  which reads as satisfiable but the gate correctly refused to book it, because the only available
  evidence was a SKIP and a skip proves nothing about execution. On this Darwin build
  `setrlimit(RLIMIT_AS, 807840000)` raises `ValueError: current limit exceeds maximum limit` — the
  kernel will not bound a process below about 1 TiB. That is a standing platform fact, not
  something this card can fix, and it predates the card.
  This is deliberately NOT the forbidden move of hand-patching an AC to match the code. The code
  is unchanged by this amendment; what changed is that the criterion now states what can actually
  be evidenced and what cannot, instead of implying execution it can never get. The alternative —
  leaving an AC permanently unverifiable — would mean every future card touching this file
  inherits a gate item that can only ever be waived, and a gate that is always waived stops being
  a gate. Recorded here rather than silently passed.

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

- [Review sync] 1 report(s) → meta/review/20261015T143100Z-CARD-237-cycle1.yml
- [Review 1/3] Score: 7.5 — crit: **1**, imp: 0. Below min_score AND a Critical stands, so the
  gate is closed twice over. The card does NOT merge on this cycle.
- [Review 1/3] ⚠ **THE FLAKE WAS RELOCATED, NOT REMOVED** — and the polarity is inverted, which
  is why everything else looked green.
  `TestMemoryGuard_InterpreterGrowthDoesNotTripTheGuard::test_a_floor_at_the_edge_of_the_share_still_passes`
  guards against vacuity by asserting the constructed pair would have failed the OLD 3x bound.
  Its floor is pinned one byte under the share bar (201,959,999 B) and it adds **this run's live**
  export measurement — so it demands `measured_export > 67,320,001 B = 2.667 page bitmaps`. The
  implementer's own recorded minimum was 2.70 bitmaps: **1.2% above the threshold**. The reviewer
  measured 65.5, 66.6, 66.7, 67.0, 67.1 MB and the test went RED every time — **5 reds in ~11
  solo invocations on the committed tree with no mutant applied.**
  This is the exact defect class the card was cut to remove — a bound placed just above the
  minimum of an instrument with a 2.26x spread — reproduced inside the fix. The inversion is the
  dangerous part: the old guard failed in a busy suite and passed solo; this one **passes in a
  busy suite and fails SOLO**, because a busier host means a higher peak means a larger measured
  marginal cost. So it fails precisely on the single-file run that is this file's own debugging
  path.
- [Review 1/3] **MY OWN AC-5 IS WHY THIS NEARLY SHIPPED, and that is a defect in the card I
  wrote.** I specified "run it inside a full suite three times … the flake is gone, not merely
  re-rolled", reasoning from the old guard's failure mode, where load caused the red. AC-5 is
  therefore blind by construction to a test whose polarity is reversed: all five full suites
  passed (margins 3.41–5.87, comfortably above the 2.667 threshold) and would have passed
  forever. An AC written against one failure mode certified the absence of the opposite one.
  The correction belongs in the card, not just in this note: **a flake criterion must demand
  repeated runs in BOTH conditions — in-suite and solo** — because "flaky" has no inherent
  polarity and the cheap direction is the one nobody runs. The reviewer reached the same
  conclusion independently and asked that the fix be re-derived by repeated SOLO runs, on the
  grounds that "a single green run is exactly the evidence that failed to detect this defect in
  the first place." That is now a requirement of cycle 2.
- [Review 1/3] What the reviewer verified clean, so the fix stays narrow: the closure arithmetic
  is real AND enforced (`_habitable`'s skip is a genuine precondition — it is deliberately not
  `lru_cache`d, so it re-fires, and stubbing it red-tests AC-4); `CHILD_HEADROOM` is gone
  repo-wide with nothing loosened to compensate (G-2); AC-3 re-derived independently on the real
  seam (red at +14 → 16.87 bitmaps, green at +12 → 15.60, so ~13 of 307 pages = 4.2%), and a
  30-page regression would be red by 2x; the floor is stable at 110.5–110.6 MB across four runs;
  AC-2's +80 MB demonstration is real, not tautological (green at a 282.7 MB total the old bound
  rejected); the margin print cannot fail or spam and its arithmetic cross-checks.
  All five of its mutants were killed, including "weaken the constant to 320" (3 tests red) and
  "re-aim the guard at the total" (5 red).
- [Review 1/3] An honest qualification I am recording rather than letting the headline stand
  alone: the new guard is **stronger as a discriminator, looser as an absolute bound.** The old
  bar sat at ~6.3 export bitmaps — *inside* the 2.59–5.87 noise band, which is why it fired at
  roughly the base rate and its true positives were indistinguishable from its false ones. The
  new bound sits 2.7x outside that band. But on the child's total, the composition permits
  < 605.9 MB where the old constant demanded < 269.3 MB — 2.25x looser. That is disclosed in the
  constant's own comment and permitted by the guardrails, and it matters less than it reads only
  because the fine-grained claim is carried elsewhere: `test_neither_book_holds_more_than_one_page_bitmap`
  asserts an EQUALITY at one page bitmap through the in-process instrument, untouched by this
  card. The RSS guard only has to be a coarse envelope check. That is the reason 16 is
  defensible rather than merely safe — not the noise margin on its own.
- [Review 1/3] AC-6 recorded as **static PASS / dynamic UNVERIFIED**, not demonstrated: the
  RLIMIT_AS twin is consistently updated (same 3-tuple unpack, same guard, same claim — and a
  stale 2-tuple would have been an immediate ValueError, so silent inconsistency is impossible),
  but it SKIPS on this host because the kernel refuses `setrlimit` below 1 TiB on this Darwin
  build. A skip proves nothing about execution and is not booked as evidence.
- [Fix 1] FIXED F-001 (Critical) — the AC-2 vacuity guard no longer measures anything. Its pair
  is now two CONSTANTS: floor `201,959,999 B` (one byte under the share bar) plus a new
  `WORST_RECORDED_EXPORT_IN_PAGES = 6.56` — a recorded measurement used only to construct the
  pair, **never compared against as a bound**. The guard is kept rather than weakened and now
  clears the old 3x bound by **1.365x on the total, 2.46x on the export term**, unconditionally.
  The live half moved into its own test (`test_this_hosts_measured_export_passes_the_new_guard`),
  which is the half AC-2 actually claims and the half a measurement carries robustly.
  Also FIXED F-002: `test_the_bound_is_where_the_constant_says_it_is` gains one ABSOLUTE
  assertion (`CHILD_EXPORT_COST_IN_PAGES < CORPUS_PAGE_COUNT / 10`, i.e. 16 < 30.7) and its
  docstring now states plainly that both original edges are expressed in the constant and so
  hold for any value of it, citing the 320 mutant that exposed it.
- [Fix 1] declarations: 2 FIXED, both with DECLARATIONS lines, both naming real corrections —
  and I cross-checked the central claim against the diff rather than accepting it, the way a
  "matrix updated" claim gets checked. The `CHILD_EXPORT_COST_IN_PAGES` measurement table really
  is corrected in the diff: `68.3-148.1 MB / 2.70-5.87` → `46.9-148.1 MB / 1.86-5.87`. G-2
  likewise verified mechanically: the only occurrence of `CHILD_EXPORT_COST_IN_PAGES` in the
  diff is a docstring reference to the 320 mutant; `CHILD_CAP_IN_PAGES`, the bound itself and
  `CHILD_FLOOR_SHARE` are byte-identical. No bound was widened to fix a test.
- [Fix pre-gate] PASSED — the three tests the fix named, by exact node id, under the lock:
  **3 passed**. All three exist; none was an invented name.
- [Fix 1] ⚑ **The fix agent confirmed the Critical harder than the review had, against its own
  interest.** Six fresh solo re-measurements of the real pair gave **1.86, 2.54, 3.21, 3.42,
  3.52, 3.67** bitmaps — and the old live threshold was **2.667**, so **two of its own six
  measurements fall below it**. The committed test would have gone red 2-in-6 on its own host,
  which independently reproduces the reviewer's 5-reds-in-11 by a different route. An agent
  producing the evidence that its own earlier work was flaky is the behaviour that makes this
  pipeline worth running.
  It also widened the recorded spread honestly: the export is now **1.86–6.56 bitmaps on record,
  a 3.5x spread**, where the implementer had recorded 2.70–5.87 (2.2x) and the reviewer measured
  2.26x. Against that, the floor's spread is **1.005x**. That asymmetry is the whole justification
  for subtracting the floor rather than bounding the total: one term is stable to half a percent,
  the other moves by a factor of three and a half.
- [Fix 1] evidence in BOTH conditions, per the amended AC-5 — this is what the original AC-5
  could not have asked for:
  * solo, AC-2 class alone: **8 consecutive runs, all green** (5.79–6.09 s)
  * solo, all four `TestMemoryGuard_*` classes: **5 consecutive runs, all green**, 9 passed, 0 skips
  * full suite, locked and solo: **green twice** — final tree `7163 passed, 11 skipped in 952.31s`
    (margin: export 5.94 bitmaps of 16, floor 4.38 at 13.7%, streaming total 260.6 MB), and the
    pre-correction tree `7163 passed, 11 skipped in 1004.09s` (margin 3.86)
  * the 11 skips are the expected set in both runs: 1x `RLIMIT_AS` (kernel refuses setrlimit
    below 1 TiB), 8x no `DATABASE_URL`, 2x absent `suite-timing.log`. **No guard test skipped.**
  Zero reds in any run, in either condition.
- [Fix 1] On the margin question I said I would not accept a thin answer to: no observed value is
  an input to the vacuity guard any more, so its margin is exact and unconditional and the
  instrument's spread cannot reach it at any multiplier. For the one assertion that IS live — the
  measured export under the 16-bitmap bound — the nearest observed value is 5.94, i.e. **2.69x of
  headroom**, and 2.44x against the worst figure on record. The thin margin is gone, not widened.
- [Review sync] 2 report(s) → meta/review/20261015T153022Z-CARD-237-cycle2.yml
- [Review 2/3] Score: 9.0 — crit: 0, imp: 0. **Critical ✓ RESOLVED**, and the reviewer answered
  the question that mattered most in the negative: **the file now contains NO flaky test** — it
  enumerated every assertion pairing a measured quantity with a threshold and none sits inside
  the instrument's spread. Severity gate clear.
  Evidence standard this card earned: **37 invocations, zero reds** on the clean tree — 20x the
  pure pair, 8x the live sibling, 5x the real capped test with margins captured, 3x the 9-test
  family, 1x the whole file (53 passed, 1 skipped) under the lock, all solo on a verified-quiet
  host. Mutation: 7 mutants, 5 killed. `WORST_RECORDED_EXPORT_IN_PAGES = 2.0` → red, so the
  vacuity guard is load-bearing rather than a tautology; `CHILD_EXPORT_COST_IN_PAGES = 320` →
  red at the new anchor, where in cycle 1 that same test stayed green.
- [Review 2/3] Determinism verified line by line, not asserted: the fixed test's four statements
  are int arithmetic on two constants plus two `_a_child_reporting()` calls, which build a
  `CappedChild` from literals and never reach `_capped_child`. **It spawns no child.** And
  `WORST_RECORDED_EXPORT_IN_PAGES` was grepped across all seven of its uses — definition, three
  docstrings, the pair construction, a failure message, and one equality that is a
  "which-quantity-did-the-guard-assert-on" check rather than a gate. **There is no
  `assert … < WORST_…` anywhere**, so the card did not quietly acquire a second bound sized off
  a measurement, which would have been the defect pattern a third time.
- [Review 2/3] On my 3.5x-spread question, answered precisely and it does not threaten the bound:
  **the widening is entirely at the BOTTOM** (new minimum 1.86); the maximum on record is
  unchanged at 6.56, so headroom above the worst case is still 2.44x and the cycle-1 judgement
  ("looser in absolute terms, stronger as a discriminator") stands unaltered. But the
  **sensitivity floor does move with the instrument**: it is now a BAND of **9.4–14.1 retained
  pages** (3.1–4.6% of 307) rather than the ~11–13 cycle 1 quoted, because what the guard can
  still catch is `16 − measured`. Worth keeping in mind for any future claim about this guard's
  precision.
  The reviewer's own five fresh solo measurements (2.93, 4.18, 4.75, 5.20, 4.91) produced **no
  value below the old 2.667 threshold** — cycle 1's reds did not reproduce today, which it noted
  is itself the point about reproducibility, and precisely why the fix had to remove the live
  term rather than re-measure and re-tune it.
- [Review 2/3] An honest limit of the new anchor, recorded rather than glossed: `16 < 30.7` is
  the **loosest of three** ceilings the file already imposes. Mutating the bound through the
  family shows the binding ceiling is **20** (imposed incidentally by AC-1's figures) and the
  second is ~22–27 (AC-3's fraction test); mutants at 17 and 20 survive. The anchor never fires
  first for a widening between 21 and 30. Its genuine value is narrower than its docstring
  implies: it is the only DETERMINISTIC ceiling (AC-3's rides the live measurement) and the only
  one stated inside the test that advertises pinning the bound — which is exactly the gap F-002
  named. Kept, with the limit written down.
- [Docs] F-006 applied by the orchestrator, doc-only and claim-weakening in the honest direction:
  the corrected measurement table had not propagated to the two prose sites derived from it, which
  still said "the export is 3-6 bitmaps" and "as few as 10-13 of the book's 307 pages". Now
  1.9–6.6 and 9–14, with the reason stated inline — the range widened at the bottom during the
  cycle-1 fix, so the sensitivity floor is a band, not a number. This matters more in this file
  than it would elsewhere, because **its constants are justified BY their comments**; a constant
  whose stated basis is stale is a constant nobody can re-derive. No assertion touched, so no
  re-review owed.
- [Review 2/3] Two Minors left OPEN rather than fixed, deliberately: F-004 (the live sibling's
  trailing equality is tautological — same pure function on the same two arguments; the test is
  not vacuous because the guard call itself can fail, only the equality is decorative) and F-005
  (mutants at 17 and 20 survive). Both are genuine. Neither is fixed here because they are test
  ASSERTION changes, and editing assertions after a passing review without re-reviewing is worse
  practice than shipping a decorative assert. Routed to the retrospective instead.
- [AC/EC check] All criteria/constraints ✓ (evidence): **12 of 12 demonstrated** under the
  amended AC-5 and AC-6. A fresh-context gate agent demonstrated 10 directly; the two it
  correctly refused were closed by the orchestrator afterwards, not waived.
  * AC-1 ✓ `TestMemoryGuard_HeadroomIsMeasuredAgainstTheFloor` 2 passed (+7x solo) — and the
    behavioural half is the convincing part: two constructed children with an IDENTICAL 30-bitmap
    total get OPPOSITE verdicts, which a bound on the total cannot do.
  * AC-2 ✓ 2 passed (+7x solo) · AC-3 ✓ 3 passed (+7x solo), all three via
    `pytest.raises(AssertionError, match="the export itself cost")`, and non-vacuous because all
    three floors sit at the largest `CHILD_FLOOR_SHARE` permits, so the total cannot be what
    catches them · AC-4 ✓ 2 passed (+7x solo), asserting all four fragments of the pre-existing
    skip message
  * AC-5 ✓ **both halves, on a frozen tree.** Solo half: the gate ran 6 whole-file runs plus
    per-class node-id runs on a verified-quiet host — every new guard test and the real test 7x
    solo, zero reds, zero guard-test skips. In-suite half: **3 locked solo full suites on tree
    hash `bc1aed6`**, margins **4.23 / 4.36 / 4.79** page bitmaps of the 16-bitmap bound, floor
    4.37–4.38 (13.7% of cap) throughout, exits 0 in 960/967/965s.
  * AC-6 ✓ under the amended wording: (a) static consistency demonstrated by reading the diff —
    the twin's two changed lines are TEXTUALLY IDENTICAL to the sentry test's executed lines
    (`floor, streaming, materialised = _the_pair_under_one_cap(<MECHANISM>)` and
    `_assert_the_streaming_child_fitted(streaming, floor)`), and a stale 2-tuple would have been
    an immediate `ValueError`, so silent inconsistency is impossible; (b) the skip carries its
    named reason, observed under `-rs` in all 7 gate runs and in my own. Execution of the
    kernel-enforced path is NOT claimed — the kernel refuses it on this host.
  * G-1 ✓ all four claim elements are CONTEXT lines in the combined delta (verified by grep for
    `CHILD_OVER_CAP_EXIT|OVER THE CAP|page_count`; the single hit is inside the NEW test helper,
    not the real test) · G-2 ✓ `CHILD_HEADROOM` grep-absent from the file AND from the repo
    outside `meta/`; the three bounds unmoved; **`WORST_RECORDED_*` grepped across all six uses
    with `grep -E "WORST_RECORDED[A-Z_]*\s*[<>=!]|[<>]\s*WORST_RECORDED"` returning NOTHING**, so
    no `assert ... < WORST_...` exists and the card did not acquire a second measurement-sized
    bound · G-3 ✓ the committed hunk header proves `_habitable`'s body is outside the hunk
    (`@@ -926,16 +994,68 @@`) · G-4/G-5 ✓ structural, one code file, zero hits against
    CARD-218/219/235's footprints · G-6 ✓ zero import lines added; both real dependency-baseline
    tests green
  * Only one skip anywhere, the RLIMIT twin, and **no item's verdict rests on it** — AC-6 books
    the skip's named reason as evidence of (b), not as evidence of execution.
- [Build gate] MERGE GATE — satisfied by the three AC-5 suites rather than a fourth run, and the
  reasoning is mechanical rather than a judgement call: the merge gate exists because the REBASED
  tree is what ships. `git diff --name-only 909c624..main` returns **nothing outside `meta/`** —
  main has advanced by five commits, all of them kanban bookkeeping — so the rebase cannot alter
  a single line of code under test. The three suites already ran on exactly the code that will
  ship, on a frozen hash, under the lock, solo. A fourth would cost 16 minutes for zero new
  information. If main acquires a code commit before this merges, this reasoning expires and the
  gate must be re-run.
- [Misstep, recorded] I edited this file's comments while the FIRST attempt at AC-5's in-suite
  half was running against it, drifting the hash from `6029f75` to `bc1aed6` mid-run. The edits
  were comment-only and cannot change execution, but on a card whose entire subject is
  measurement provenance, evidence of ambiguous provenance is not evidence. I aborted that run,
  froze the tree, and restarted all three. ~16 minutes of machine time lost, correctly spent:
  accepting it would have contradicted the standard I had just enforced twice against others.
- [Trace] no write-back owed: this card's Architecture context is `FR: —` (untraced
  test-integrity card), so there is no trace.yml link to append evidence to. Recorded rather
  than skipped silently. ⚑ The reviewer found something worth the retrospective's attention
  though: the card names NFR-008 for the memory envelope and **NFR-008 is the cell-size NFR** —
  a grep of requirements.yml finds NO memory-envelope requirement at all, and the 512 MB figure
  lives only as `ENVELOPE_BYTES` in this test file, sourced to CARD-145 prose. So this file is
  executable evidence for an envelope the model never states. That is a model gap, not a defect
  in this diff.
- [Closed] merged 194cb40, actual 0.7d against 0.5d. Two review cycles (7.5 then 9.0), one
  fix cycle, one AC amended at the decompose station (AC-5) and one at the AC gate (AC-6), both
  because I had written criteria that could not detect what they claimed to.
