# CARD-016: Bounded pixel-nudge recovery loop for image mode

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/016-pixel-nudge-recovery
**Worktree:** ../PythonProject4-card-016
**Source:** meta/architecture/handoff.md#increment-3
**Idea:** —
**Wave:** 10
**Depends on:** CARD-015
**Touches:** src/nonogram/orchestrator.py, src/nonogram/sourcing/image.py, tests/test_nudge.py
**Review score:** —
**Started:** 2026-08-29T09:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The recovery path for image mode. An uploaded image is the user's picture, so it cannot be
discarded and redrawn the way a random grid can — instead the tool makes a small, bounded
number of pixel adjustments and re-checks uniqueness.

1. **POL-002 AutoNudgePixelsOnImageUniquenessFailure (FR-013).** When the converted grid
   fails the uniqueness check and `nudge_count < cap`, apply a bounded pixel nudge and
   re-check. The policy decision lives in COMP-002; the nudge itself is **applied by
   COMP-003**, which owns the grid the image produced (trace.yml FR-013 note).
2. **The heuristic.** Pick the cell whose flip most plausibly disambiguates — e.g. inside a
   line the solver could not decide, or at a run boundary. The heuristic's effectiveness is
   the risk this card exists to collapse; keep it in one named function so it can be swapped
   without touching the loop, and record what you tried in the worktree notes.
3. **Cap: 5 attempts (ADR-0002)** — distinct from the 20-attempt regenerate/resample bound.
   Reuse CARD-005's shared bounded-loop primitive with a different bound; INV-003 still has
   exactly one home (COMP-002).
4. **POL-003 ReportFailureWhenNudgeCapExhausted.** At the cap, stop altering the image and
   report failure. The message must tell the user what to do next: retry with a different
   image or a different size (AC-036) — not just "failed".
5. Carry the running `nudge_count` on the `Puzzle` aggregate; CARD-017 reports it.

## Acceptance criteria

- **AC-034** (happy, POL-002) — given an uploaded image whose initial conversion fails the
  uniqueness check, with nudge attempts remaining under the cap, when the auto-nudge policy
  evaluates, then a bounded pixel nudge is applied automatically and the result is
  re-checked.
  *test:* `TestNudge_AttemptsBoundedRecovery`
- **AC-035** (boundary, INV-003, POL-003) — given an uploaded image conversion that has
  exhausted the configured nudge cap without reaching uniqueness, when the uniqueness check
  is evaluated again, then the tool reports failure to the user and stops altering the image.
  *test:* `TestNudge_ReportsFailureAtCap`
- **AC-036** (negative) — given a reported nudge-cap failure, when the failure is presented
  to the user, then the message states that the user should retry with a different image or
  size.
  *test:* `TestNudge_FailureMessageSuggestsRetry`

## Guardrails

- G-1: Do not edit `src/nonogram/sourcing/random_grid.py`,
  `src/nonogram/sourcing/library.py`, `src/nonogram/solver/**`,
  `src/nonogram/export/**`, `src/nonogram/clues.py`, `src/nonogram/difficulty.py` — the
  nudge loop must revert without touching random/library modes, the solver, or export
  (handoff Increment 3 Rollback)
  (test: TestGenerateRandom_ProducesRequestedSize, TestGenerateLibrary_ProducesCatGrid,
  TestExport_WritesPNG)
- G-2: The nudge cap is 5 (ADR-0002) and is enforced through COMP-002's single bounded-loop
  primitive — INV-003 has exactly one home. Do not add an independent counter in
  `image.py`
  (test: TestRetryLoop_BoundedIterations)
- G-3: At the cap the tool **stops altering the image** and reports — no unbounded "one more
  try", no silent continued modification (POL-003, FR-013 statement)
- G-4: Uniqueness is still the solver's verdict — a nudged grid is re-checked in full, never
  assumed unique because a nudge was applied (CON-005 is mandatory)
- G-5: Out of scope — no nudge-count CLI output (FR-014, CARD-017); this card only carries
  the count on the aggregate
- G-6: No new dependency (ADR-0006)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-013
- **NFR:** NFR-002
- **INV:** INV-003
- **CON:** CON-005
- **POL:** POL-002, POL-003
- **ADR:** ADR-0002, ADR-0004, ADR-0007
- **Components:** COMP-002 (policy + bound), COMP-003 (applies the nudge), COMP-005 (re-check)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

### What landed

Three files, two of them the predicted `Touches:` and one flagged below.

**`src/nonogram/orchestrator.py` (COMP-002) — the policy.**

* `MAX_NUDGE_ATTEMPTS = 5`, its own module constant, deliberately **not** chained to
  the `MAX_RETRY_ATTEMPTS = 20` / `MAX_REGENERATE_ATTEMPTS` / `MAX_RESAMPLE_ATTEMPTS`
  family (G-2, ADR-0002). The comment on it states why the two numbers must not move
  together: 20 is "how many fresh candidates is a request worth", 5 is "how much of the
  user's own picture may be altered behind their back", and aliasing them would let a
  retry retune silently license twenty edits to a photograph.
* A third `RetryCounter` field on `Puzzle`: `nudge = RetryCounter("pixel-nudge",
  MAX_NUDGE_ATTEMPTS)`, next to `regenerate` and `resample`. INV-003 keeps exactly one
  home and one mechanism — nothing in `image.py` counts (G-2).
* `generate()`'s image branch: when the single conversion fails the uniqueness check it
  now enters `run_bounded(puzzle.nudge, attempt_nudged_candidate, reason=...)` instead
  of raising immediately. `run_bounded`'s existing exhaustion branch *is* POL-003 (G-3):
  at the bound it raises rather than nudging again, and nothing catches it or adds a
  sixth try.
* Refactor to make G-4 structural: `attempt_candidate()` was split into
  `judge_candidate(grid)` (clues → uniqueness → score) plus a thin sourcing wrapper.
  There is now exactly **one** `solver.solve` call in the module, shared by random,
  library, image and nudged-image candidates, so a nudged grid cannot be judged by a
  different (or absent) rule than any other. CON-005 is not re-stated in the nudge path;
  it is the same path.
* The tier check stays *outside* the nudge loop: a conversion that is unique but misses
  `--difficulty` still ends the run as CARD-015 left it. Nudging is a uniqueness remedy,
  and nudging until the score drifts into a band would be POL-004 by other means.
* `_image_uniqueness_reason` reworded for AC-035/AC-036 — it now says the tool adjusted
  up to 5 pixels and **has now stopped altering it**, and names the two levers that
  actually change the answer ("retry with a different image, or a different `--size`").
  `--seed` is still deliberately absent: neither the conversion nor the nudge draws from
  the RNG, so re-seeding reproduces the same grid *and* the same five edits.

**`src/nonogram/sourcing/image.py` (COMP-003) — the mechanism.** `nudge(grid,
attempt_number) -> list[list[bool]]`, plus `nudge_cells(grid, count)` for the ranking it
delegates to. It takes the attempt number as an argument and keeps no state: no counter,
no bound, no loop on this side of the line.

### The nudge heuristic — what I chose, and why

The card asked for the reasoning even if the heuristic is imperfect, so:

**Ranking (`nudge_cells`).** Every cell is scored and sorted by, in order:

1. **switching-block participation** (`_switch_counts`) — how many 2x2 blocks of the form
   `█· / ·█` (or its mirror) the cell belongs to. This is the primary signal and the whole
   bet: a diagonal pair with nothing else near it is the textbook non-unique nonogram,
   because exchanging the two diagonals changes no row clue and no column clue. Real
   ambiguity is usually a *chain* of such blocks, so participation is counted rather than
   blocks flagged — a cell shared by several is where a chain is anchored;
2. **disagreeing-neighbour count** (`_boundary_counts`) — the card's "at a run boundary",
   counted over the 4-neighbourhood. A cell with no disagreeing neighbour is buried inside
   a solid area, where a flip damages the picture more than it changes the puzzle;
3. **distance from the centre**, ascending — the subject is in the middle (the crop policy
   already threw the edges away once);
4. row, then column, so the result is fully deterministic.

**Spacing.** Flips are selected greedily with a Chebyshev-1 exclusion around each cell
already chosen. Without it the top-5 would all land inside one switching block — and
flipping *both* cells of a diagonal pair just produces the other diagonal, i.e. the same
ambiguity again. With it, each successive flip breaks a different local structure.

**Cumulative from the conversion, not from the previous nudge.** Attempt *n* flips the
best *n* cells of the **original** converted grid. Two reasons. (a) Nudging the previously
nudged grid makes each ranking depend on the last flip, which lets a flip be undone by the
next one and turns a five-attempt budget into a two-grid oscillation. (b) It makes POL-003
observable: at the cap the grid is provably "the conversion plus at most five pixels",
rather than having drifted somewhere unrelated to the user's picture. A pleasant
side-effect for **CARD-017/ADR-0004**: `puzzle.nudge.attempts` *is* the cell-diff count
against the original conversion, exactly the number ADR-0004 wants reported — no second
quantity to compute or keep in step.

**What I wanted and could not build.** The card's other suggestion — flip a cell *the
solver could not decide* — is the strictly better heuristic and this codebase cannot
express it today. `SolveSignals` reports how many cells line logic settled but not *which*,
and never which cells two solutions disagreed on; surfacing a disagreement mask is a change
to COMP-005's contract, which G-1 puts out of bounds for this card. COMP-003 could not ask
the solver anyway (ADR-0007 forbids lateral capability imports), so it would have to travel
orchestrator → `nudge`. Left as the obvious next iteration; the swap point is designed for
it (see below).

**Measured effectiveness.** Sweeping the three fixtures over sizes 10..25 (the six
conversions that previously failed): `bands.png`@10 recovers in 2 nudges, `wide.png`@19 in
1, `tall.png`@12 in 3, `tall.png`@19 in 1; `wide.png`@22 and `tall.png`@22 still reach the
cap. Four of six recovered — enough to say the primary signal is finding something real,
not enough to retire the risk. The two survivors are now the pinned real-image cap cases.

### How the two-component split works

`orchestrator.generate` owns *when and how often* (`run_bounded` + the `nudge`
`RetryCounter` + `MAX_NUDGE_ATTEMPTS` + the failure wording); `sourcing.image.nudge` owns
*which cell*. The whole coupling is one call:

```python
image_source.nudge(converted, puzzle.nudge.attempts)
```

`puzzle.nudge.attempts` is read straight off the counter because `run_bounded` advances it
*before* calling the attempt, so it is already this attempt's 1-based number — no shadow
copy of the count, which is what keeps INV-003 single-homed (G-2). Swapping the heuristic
means replacing the bodies of `nudge`/`nudge_cells` and touching nothing in COMP-002; the
loop never learns what a "cell" is, and the mechanism never learns what a "bound" is.

### Scope deviation (flagged, per CARD-010/011/014/015 practice)

Predicted `Touches:` was `orchestrator.py, sourcing/image.py, tests/test_nudge.py`. I also
edited **`tests/test_sourcing_image.py`** — four CARD-015 tests pinned behaviour this card
deliberately supersedes and could not both stay and be true:

* `test_a_non_unique_conversion_fails_cleanly_without_regenerating` → renamed
  `test_a_non_unique_conversion_is_never_re_sourced`. Its real claim (the source is asked
  for exactly one candidate) survives untouched and is still asserted; the run now recovers
  via a nudge instead of raising, and the old name asserted the outcome, not the claim.
* `test_a_non_unique_conversion_leaves_both_retry_counters_at_zero` — name still accurate
  ("both" = regenerate + resample). Dropped the `pytest.raises` and the
  `ready_for_export is False`; kept the counter assertions and "one aggregate per run".
* `test_a_real_image_that_converts_ambiguously_reports_it` — re-pinned from `bands.png`@10
  (now repaired by 2 nudges) to `wide.png`@22 (survives all 5), following the test's own
  "re-pin by re-running the sweep, don't delete" instruction. The old case became
  `test_nudge.py`'s real-image *recovery* test, so nothing was lost.
* `test_the_image_module_exposes_no_retry_machinery` — narrowed. It asserted `image.__all__`
  contained no nudge at all; CARD-016 puts the mechanism there on purpose. It now pins only
  what never moved (no `RetryCounter`, no `MAX_*` bound), and the full split pin moved to
  `test_nudge.py::test_the_image_module_counts_nothing_itself`, which additionally asserts
  that `nudge` *takes* its attempt number and so cannot have an opinion about the cap.

No other file was touched. Nothing under G-1's list (`random_grid.py`, `library.py`,
`solver/**`, `export/**`, `clues.py`, `difficulty.py`) was edited; no new dependency (G-6);
no nudge-count CLI output (G-5 — the count sits on the aggregate for CARD-017).

### Tests

`tests/test_nudge.py`, 31 cases. AC mapping in the module docstring, in the house style:
`TestNudge_AttemptsBoundedRecovery` → `test_nudge_attempts_bounded_recovery*`,
`TestNudge_ReportsFailureAtCap` → `test_nudge_reports_failure_at_cap*`,
`TestNudge_FailureMessageSuggestsRetry` → `test_nudge_failure_message_suggests_retry*`.

Two scripted grids carry the loop tests, and both are cross-checked against the *real*
solver at the top of the module so an AC test cannot silently go vacuous: `_ONE_SWITCH`
(one diagonal pair, one flip from unique) and `_SIX_SWITCHES` (six spread-out pairs — five
nudges cannot break six, so cap exhaustion is arithmetic, not luck). Uniqueness is never
faked anywhere; the highest-value test is
`test_nudge_attempts_bounded_recovery_re_solves_every_nudged_grid`, which wraps
`solver.solve` and asserts 1 + 5 calls whose clue sets are exactly those of the conversion
and its five nudges — a loop that "recovered" by assuming a nudged grid unique would pass
every other assertion in the file. G-3 is tested as a *count of edits*
(`...stops_altering_the_image`: `nudge` called with attempt numbers `[1..5]` and no sixth)
rather than only as a message, since an unbounded "one more try" would raise the same error.

Full suite in the worktree: **1153 passed, 1 xfailed** (baseline 1122 passed, 1 xfailed;
+31 = exactly this card's new tests, no other count moved). The pre-existing AC-037 xfail
(`tests/bench_generate.py::test_20x20_p95_is_under_5s`) is unchanged in both status and
reason.

### Orchestrator notes

- **[Scope]** Touches match predicted plus one explicitly-flagged file
  (`tests/test_sourcing_image.py` — four CARD-015 tests updated to reflect
  the deliberate behavior change from "fail immediately" to "nudge then
  fail at cap", following those tests' own "re-pin, don't delete"
  convention). No silent creep. G-1/G-6 confirmed clean (empty diff on all
  guarded paths plus `pyproject.toml`).
- **[Build gate]** PASSED (full, independently re-run by orchestrator in a
  fresh venv: 1153 passed, 1 xfailed, exit 0; AC-037 xfail unchanged in
  status and reason).
