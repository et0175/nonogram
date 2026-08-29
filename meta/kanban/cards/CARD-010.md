# CARD-010: Difficulty tier selection and resample loop

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/010-difficulty-tier-resample
**Worktree:** ../PythonProject4-card-010
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 7
**Depends on:** CARD-009, CARD-011
**Touches:** src/nonogram/orchestrator.py, src/nonogram/difficulty.py, src/nonogram/cli.py, tests/test_resample.py, tests/test_difficulty_tiers.py
**Review score:** 9.5 (cycle 1/3)
**Started:** 2026-08-28T12:00:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Turns CARD-009's raw score into the user-facing Easy/Medium/Hard selector, and closes the
loop that makes a requested tier actually come out.

1. **Tier selector (FR-008).** `--difficulty {easy,medium,hard}` on the parser (parsing
   only), with the unsupported-tier rejection as a **domain** error inward of COMP-001
   (ADR-0010, same pattern as FR-001's size range). The requested tier is recorded on the
   `Puzzle` aggregate at creation, "pending score confirmation" (AC-020).
2. **Tier cutoffs (ADR-0005).** Map the 0..100 score to the three tiers at the ADR-0005
   cutoffs. Keep the cutoffs as named constants in `difficulty.py` next to the formula, not
   inlined in the orchestrator — Increment 2's checkpoint checks that generating at each
   tier produces a score in that tier's tertile band, and a single source for the bands is
   what makes that checkable.
3. **POL-004 ResampleOnDifficultyOutOfRange (FR-010).** In the orchestrator: score each
   candidate; if the score is outside the requested tier's range, resample a new candidate
   and **re-score it** before any further check (AC-026). Reuse CARD-005's shared bounded
   loop primitive — do not write a second counted loop.
4. **POL-005 / INV-003.** The resample loop shares the 20-attempt bound (ADR-0002). At the
   bound, abandon with a clear error (AC-027). INV-003 has exactly one home: COMP-002.

## Acceptance criteria

- **AC-020** (happy) — given a request specifying difficulty `"Medium"`, when generation
  runs, then the resulting puzzle is tagged with requested tier `"Medium"` pending score
  confirmation.
  *test:* `TestSelectDifficulty_AcceptsValidTier`
- **AC-021** (negative) — given a request specifying difficulty `"Extreme"` (not a supported
  tier), when generation is requested, then the request is rejected with an
  unsupported-difficulty error.
  *test:* `TestSelectDifficulty_RejectsUnknownTier`
- **AC-024** (happy) — given a scored candidate whose score falls within the requested
  `"Hard"` tier's threshold range, when the score is checked, then the candidate is accepted
  as final and no further resampling occurs.
  *test:* `TestResample_AcceptsCandidateInRange`
- **AC-025** (boundary, POL-004) — given a scored candidate whose score falls outside the
  requested tier's threshold range, when the score is checked, then the resample policy fires
  and a new candidate is generated.
  *test:* `TestResample_FiresWhenScoreOutOfRange`
- **AC-026** (boundary, POL-004) — given a newly resampled candidate produced in response to
  an out-of-range score, when the resample completes, then the new candidate is re-scored
  automatically before any further check.
  *test:* `TestResample_RescoresNewCandidate`
- **AC-027** (boundary, INV-003, POL-005) — given a candidate that has already been resampled
  up to the configured maximum retry bound without matching the requested tier, when the
  score is checked again, then generation is abandoned with a clear error.
  *test:* `TestResample_StopsAtMaxRetryBound`

## Guardrails

- G-1: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/export/**`, `src/nonogram/sourcing/**` — Increment 2 is additive on top of
  Increment 1; the resample loop must revert without touching the solver or the
  orchestrator's core generation logic (handoff Increment 2 Rollback)
- G-2: INV-003 has exactly one home — `orchestrator.py` (trace.yml NFR-002 note). Reuse
  CARD-005's shared bounded-loop primitive; do not add a second independent counter
  (test: TestRetryLoop_BoundedIterations)
- G-3: Difficulty is a heuristic score bucket, not a construction guarantee (CON-004). The
  resample loop discards and re-draws candidates; it must not steer grid construction toward
  a tier, and an "Easy" puzzle carries no promise of being backtracking-free
- G-4: `--difficulty` validation stays inward of argparse (ADR-0010) — no `choices=` shortcut
  for AC-021; the unsupported-tier error is a domain error
- G-5: The existing regenerate-on-uniqueness-failure behavior is unchanged — resampling
  composes with it, it does not replace it
  (test: TestRegenerate_FiresOnUniquenessFailure, TestRegenerate_StopsAtMaxRetryBound)
- G-6: NFR-001's timing budget still holds with scoring in the loop — a resample loop that
  scores every candidate must not push 20x20 p95 past 5s
  (test: BenchGenerate_20x20_p95Under5s)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-008, FR-010
- **NFR:** NFR-002
- **INV:** INV-003
- **CON:** CON-004
- **POL:** POL-004, POL-005
- **ADR:** ADR-0002, ADR-0005, ADR-0007, ADR-0010, ADR-0013
- **Components:** COMP-002, COMP-006, COMP-001, COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-005 review, cycle 1] Two things to know about the retry primitive
this card reuses (`orchestrator.RetryCounter` + `run_bounded`):
1. `MAX_REGENERATE_ATTEMPTS = 20` is named for CARD-005's own loop, but ADR-0002 gives
   the same bound (20) to resample too. Don't declare a second literal `20` for the
   resample counter — either import/reuse the existing constant under a shared name, or
   rename it to something like `MAX_RETRY_ATTEMPTS` with `MAX_REGENERATE_ATTEMPTS =
   MAX_RESAMPLE_ATTEMPTS = MAX_RETRY_ATTEMPTS`, so the two bounds can't silently drift
   apart.
2. The regenerate counter is deliberately NOT reset between calls to `run_bounded` —
   its budget spans the whole request, not one invocation of the primitive. If this
   card's resample loop wraps/nests inside the regenerate loop, confirm that's still the
   semantics POL-004 wants (a resample attempt that itself regenerates does not get a
   fresh 20-attempt regenerate budget), and that an inner `GenerationAbandoned` correctly
   ends the outer loop too rather than being caught and retried as a resample failure.

[CARD-010 implementation]

**What was built**

1. *Tiers, in `difficulty.py` next to the formula* (card point 2). `Tier` is a `StrEnum`
   (`easy`/`medium`/`hard`) whose value **is** its `--difficulty` spelling, plus `.label`
   for AC-020's display form ("Medium"). ADR-0005's cutoffs are two named constants
   `EASY_MAX_SCORE = 33.0` / `MEDIUM_MAX_SCORE = 66.0`; `TIER_BANDS` and
   `tier_for_score()` are both *derived* from them, so the band table and the classifier
   cannot disagree at a boundary and a retune moves one place. Cutoffs belong to the band
   below them (`33.0` is Easy, `66.0` is Medium), which is ADR-0005's `[0,33] / (33,66] /
   (66,100]` read literally. `parse_tier()` is the AC-021 domain check, case- and
   whitespace-insensitive so AC-020's own capitalized "Medium" is accepted.
2. *The selector* (card point 1). `--difficulty TIER` on the parser with **no `choices=`**
   (G-4): the help text reads the tier vocabulary from `difficulty.Tier` — the same
   trick `--export` uses with `export.FORMATS`, so `--help` can't drift from what
   `parse_tier` accepts — but the *rule* stays inward. `GenerationRequest.difficulty` is
   a raw `str | None`; `generate()` resolves it to a `Tier` in the same place and for the
   same reason it resolves the FR-015 name — before the seed is drawn and before the
   aggregate exists, so a bad tier leaves nothing behind. The aggregate carries
   `requested_tier` (what was asked for, AC-020's tag) separately from `difficulty_score`
   / `difficulty_tier` (what the candidate turned out to be) — that split is what makes
   "tagged pending score confirmation" a state the type can express.
3. *POL-004* (card points 3-4). Every uniquely-solvable candidate is scored inside the
   regenerate attempt, off the signals of the solve that just happened; the tier check
   runs in the resample attempt that wraps it.

**Retry-counter reuse — the two questions the CARD-005 note asked**

*One bound constant, two counters.* Took the note's second option verbatim:
`MAX_RETRY_ATTEMPTS = 20` with `MAX_REGENERATE_ATTEMPTS = MAX_RESAMPLE_ATTEMPTS =
MAX_RETRY_ATTEMPTS`. Both aliases are exported (so `RetryCounter("resample",
MAX_RESAMPLE_ATTEMPTS)` still reads as "this policy's bound") but there is exactly one
literal `20` in the package. `test_the_two_loops_share_one_bound_constant` asserts
**identity**, not equality — two independently-declared `20`s would satisfy `==` today
and diverge on the first retune. No new counted loop was written: `Puzzle.resample` is a
second `RetryCounter` and `attempt_candidate_in_tier` a second attempt callable, both
driven by the existing `run_bounded` (G-2).

*How the loops compose.* Resample outer, regenerate inner, exactly as the note framed
it — one resample round runs the whole regenerate loop to get a unique candidate, then
keeps it only if its score is in tier (G-5: POL-001 is wrapped, not replaced). Both
answers the note asked for are **yes**, and both are now pinned by tests rather than left
as reasoning:

- The regenerate counter is still not reset, so a resample round does **not** get a fresh
  20-attempt regenerate budget: across a whole request at most 20 grids are ever sourced,
  however the two rejection causes divide them up
  (`test_the_regenerate_budget_is_the_requests_and_not_the_rounds`). This is also what
  keeps G-6 honest — see below.
- An inner `GenerationAbandoned` ends the outer loop, because `run_bounded` re-raises
  whatever an attempt raises; it is not caught and retried as a tier miss
  (`test_an_exhausted_regenerate_loop_ends_the_run_rather_than_resampling`).

*The one thing that fell out of that and needed a decision.* Because the budget is
shared, a run that keeps missing its tier usually ends on the **regenerate** bound rather
than the resample one (the inner loop consumes attempts for both causes). Reporting only
"no candidate grid had exactly one solution" there names the wrong cause: candidates
*were* unique and were discarded for their score. So the regenerate loop's abandonment
`reason` is now tier-aware — with `--difficulty` it says "no candidate grid was both
uniquely solvable and scored inside the Medium band (33-66) ... the two checks share one
20-attempt budget", and **without** `--difficulty` it is byte-identical to CARD-005's
wording (G-5, pinned by
`test_an_abandonment_message_is_unchanged_when_no_tier_was_requested`). The resample
loop's own message is narrower, since it only ever rejects for one cause.

**G-6 / the AC-037 xfail**

Untouched and still `xfail(strict=True)`, failing for the same pre-existing reason
(CARD-018's solver search-strength gap). The resample loop adds no extra pass over
candidates: scoring is O(cells) arithmetic on signals the solve already produced (no
solver re-entry, per COMP-006's contract), it runs **only** for candidates that passed
the uniqueness check (`test_a_non_unique_candidate_is_not_scored_at_all`), and the shared
budget caps a request at 20 sourced grids with or without `--difficulty` — so the
benchmark corpus, which passes no `--difficulty`, does exactly the work it did before
plus one arithmetic pass per accepted candidate.

**Two observations for later, deliberately not fixed here**

1. *The score distribution is skewed low, so Hard is currently unreachable in practice.*
   Measured on real unmocked runs of the shipped pipeline (8 seeds each):
   10x10/50% → 0.00-0.01; 15x15/45% → 8.7-34.0; 20x20/55% → ~0.01; 25x25/50% →
   6.9-42.5. Everything lands Easy or low-Medium; nothing came near 66. This is precisely
   the consequence ADR-0005's own "Negative" section predicts ("equal tertile bands could
   leave one tier — most likely Hard — under-populated, causing the resample loop to hit
   the maximum-retry bound more frequently"), and both ADR-0005 and ADR-0013 defer the
   numbers until real distributions exist. These *are* the first real distributions. The
   fix is a retune of `SIGNAL_WEIGHTS` and/or the two cutoffs — an ADR-0005/ADR-0013
   revision, not a code change, and out of this card's scope. Worth a backlog card.
2. *A score is not bit-reproducible across runs, though a tier normally is.* ADR-0013
   puts wall-clock solve time in the formula (weight 0.15), so two runs of the identical
   seed score within a whisker of each other rather than identically — which in principle
   lets a candidate sitting exactly on a band boundary be accepted in one run and
   resampled in the next. Pre-existing from CARD-009's formula, not introduced here;
   `test_the_same_seed_replays_the_same_resample_run` asserts the *work* replays (same
   grids, same counters, same tier) and tolerates the score to 1.0 rather than asserting
   that the machine is a clock-free abstraction.

**Scope: two files outside the predicted `Touches:`**

Both flagged rather than done silently (per CARD-011's precedent):

- `src/nonogram/errors.py` — added `UnsupportedDifficulty(NonogramError)` for AC-021.
  The alternative was defining the exception in `difficulty.py`, which would break the
  architecture rule that `errors.py` is the one flat, import-free hierarchy every layer
  raises from. One class, no behaviour, same shape as its six siblings.
- `tests/test_cli.py` — one line. `test_every_domain_error_has_an_exit_code` asserts the
  exit-code table covers the *whole* hierarchy by reflection, so a new error class fails
  the suite until it is mapped; `UnsupportedDifficulty` was added to `ERROR_EXIT_CODES`
  as `INVALID_INPUT`, alongside the other "you asked for something that doesn't exist"
  errors. No existing assertion was changed or weakened.

Not touched, noted for whoever owns it: `README.md`'s Status paragraph is stale from
several cards back (it still says there is no export writer and no solver timeout) and
says nothing about `--difficulty`. Out of scope here.

**Test results**

`./.venv/bin/python -m pytest` → **1003 passed, 1 xfailed** in ~17s (baseline before this
card: 930 passed, 1 xfailed). No regressions; the AC-037 xfail is unchanged in status and
in reason. 73 new tests across `tests/test_difficulty_tiers.py` (AC-020, AC-021, the
ADR-0005 cutoffs) and `tests/test_resample.py` (AC-024 through AC-027, loop composition,
INV-003).

*On test style:* AC-024 asks for a candidate scoring in the **Hard** band, and no
hand-drawable small grid will ever produce one — that is the scale working as designed.
So `tests/test_resample.py` adds a third style alongside `test_orchestrator.py`'s
scripted / pinned-seed pair: *scripted-score* tests that substitute
`difficulty.score_difficulty` with a fixed sequence while leaving the uniqueness verdict
to the real solver (G-3) and the classification to the real `tier_for_score`. What is
under test there is the orchestrator's loop — which candidate it keeps, how often it
re-draws, where it stops — not the number, which is COMP-006's and is tested against real
solves in `tests/test_difficulty.py`. Each AC also has at least one fully-unmocked
counterpart (`test_stops_at_max_retry_bound_with_the_real_scorer`,
`test_a_puzzle_generated_for_a_tier_really_scores_in_that_tier`) so the scripted ones
cannot be papering over a collaborator that does not behave as assumed.

### Orchestrator notes

- **[Scope]** Touches match predicted plus two explicitly-flagged additions
  (`src/nonogram/errors.py` for the new `UnsupportedDifficulty` class,
  one line in `tests/test_cli.py` mapping its exit code) — no silent creep.
- **[Build gate]** PASSED (full, independently re-run by orchestrator in a
  fresh venv: 1003 passed, 1 xfailed, exit 0; AC-037 xfail unchanged in
  status and reason).
- **[Review 1/3] 9.5/10 — PASS.** Report:
  `meta/review/20260829T000000Z-CARD-010-cycle1.yml`. All 6 ACs and all 6
  guardrails verified directly against code (not just tests), including
  hand-tracing the resample/regenerate loop composition: the regenerate
  counter is never reset between resample rounds, so the whole request
  shares one 20-grid sourcing budget (`MAX_RESAMPLE_ATTEMPTS` is therefore
  structurally non-binding except in the exact lockstep case — noted as
  Minor F-004, not a defect, since it's the ADR-0002-conformant reading).
  G-3 (no steering of sourcing toward a tier) and G-6 (no AC-037 benchmark
  regression — file untouched, scoring runs post-uniqueness-check only,
  work is byte-identical to before with no `--difficulty`) both
  independently reproduced. Byte-identical no-tier abandonment message
  claim verified directly against the diff. Zero Critical/Important
  findings; four Minor polish items (docstring over-claim, unused fixture,
  a comment clarification, one docstring wording nit) — none blocking.
  **Out-of-scope observation surfaced, not this card's to fix:**
  `--difficulty hard` is unreachable at every size/density independently
  measured by the reviewer (ceiling ~43 vs. ADR-0005's floor of 66) —
  exactly the risk ADR-0005's own Consequences section predicted and
  deferred pending real distributions; these are the first real ones.
  Needs a backlog card for an ADR-0005/ADR-0013 weights/cutoffs retune,
  not a code fix here. Merging.
