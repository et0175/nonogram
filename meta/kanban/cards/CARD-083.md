# CARD-083: A batch survives a candidate it had to abandon

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/083-batch-survives-abandonment
**Worktree:** ../PythonProject4-CARD-083
**Source:** owner decision on CARD-082's open question ("yes, make batches survive an abandoned candidate")
**Idea:** —
**Wave:** 1
**Depends on:** — (CARD-082 merged a13c9bf)
**Touches:** src/nonogram/orchestrator.py (generate_batch's loop + one constant), src/nonogram/admin/batch_generator.py (the shortfall note), tests/test_batch_abandonment.py (new), tests/test_admin_uniqueness_boundary.py (the note's tests)
**Review score:** 8.0 (cycle 1), all findings fixed
**Started:** 2026-09-14
**Closed:** 2026-09-14
**Actual:** —
**Merge commit:** d3db715
**Blocked by:** —

## Why

`generate_batch` called `generate` in a loop with nothing around it, so the
first `GenerationAbandoned` ended the whole batch — after doing all the work
for every candidate before it.

That is not a rare event. Measured over 200 draws per size at the density
`generate_batch` hardcodes (50):

| extent | abandoned | p |
|---|---|---|
| 10x10 | 0/200 | 0.000 |
| 15x15 | 0/200 | 0.000 |
| 20x20 | 0/200 | 0.000 |
| 25x25 | **4/200** | **0.020** |
| 30x30 | — | reaches ADR-0011's 30s deadline instead (`SolverTimeout`) |

At 25x25 a 50-puzzle batch lost everything roughly a third of the time. CARD-080
made the *store* tolerant of a refusal and counted it; generation had no
equivalent, which is what CARD-082 surfaced as the owner question this card
answers.

## What was decided

1. **Skip, do not retry.** An abandoned candidate is dropped and the batch
   moves to the next slot. It is *not* given a second budget: POL-001 already
   spent `MAX_RETRY_ATTEMPTS` draws on it, and a retry at the batch level would
   be the second bound INV-003 and ADR-0002 exist to prevent.
2. **The shortfall is the return value.** `generate_batch` returns a list that
   may be shorter than `count`; the caller compares the two. No new return type
   — there is exactly one production caller, and it already had `len(puzzles)`.
3. **Two cases still fail loudly**, because "shorter" is the wrong answer for
   them:
   - **nothing was produced** — a batch of zero puzzles is not a short batch,
     it is a failed one;
   - **`MAX_CONSECUTIVE_ABANDONMENTS` (3) in a row** — at the worst rate this
     function can reach (p = 0.02) that is 8 chances in a million, so it means
     the parameters are infeasible, not unlucky. Without it, skipping would
     have removed the thing that used to stop a hopeless request: a
     `count=200` run would spend 4000 solves discovering what used to take 20.
   Both messages carry the counts, and the consecutive case chains the
   candidate's own abandonment as `__cause__` — CARD-080's F-008 lesson, where
   a batch-level error replaced the candidate-level one and the admin's
   `exc_info` log went blind.
4. **A `SolverTimeout` is not skipped.** ADR-0011's 30s bound is per request,
   so swallowing timeouts per candidate would leave a batch with no time bound
   at all — 200 x 30s is an hour and a half where the request used to fail in
   thirty seconds. 30x30 reaches the deadline rather than the retry bound, so
   this is not a hypothetical extent.
5. **The admin says which shortfall happened.** An abandoned candidate and a
   store-refused candidate are reported as two separate sentences on the batch
   record, never one "missing puzzles" number: the first is ordinary bad luck
   at a known rate, the second should be unreachable and is a bug. Merging them
   would undo what CARD-080's note was for.

## Acceptance criteria

- **AC-1** — a batch with one abandoned candidate returns `count - 1` puzzles
  and attempts every remaining slot.
  *test:* `TestBatch_SurvivesAnAbandonedCandidate`
- **AC-2** — a batch that produced nothing raises, and so does one that
  abandoned `MAX_CONSECUTIVE_ABANDONMENTS` candidates in a row; the second
  stops rather than finishing the loop, and both name the counts.
  *test:* `TestBatch_StillFailsWhenTheBatchItselfFailed`
- **AC-3** — a `SolverTimeout` still ends the batch and is never counted as an
  abandonment.
  *test:* `TestBatch_DoesNotSwallowATimeout`
- **AC-4** — the admin reports a generator shortfall and a store refusal as
  distinguishable statements, and says nothing when a batch is complete.
  *test:* `test_a_generator_shortfall_is_reported_as_a_different_thing`,
  `test_both_shortfalls_are_reported_side_by_side`,
  `test_a_full_batch_carries_no_shortfall_note`

## Guardrails

- G-1: No change to POL-001's per-puzzle retry bound, `MAX_RETRY_ATTEMPTS`, or
  any counter INV-003 governs. This card adds a *batch* bound and touches no
  per-puzzle one.
- G-2: No edits under `src/nonogram/solver/`, `difficulty.py`, or
  `sourcing/`. The generation of a candidate is unchanged; only the loop's
  reaction to one is new.
- G-3: `generate`'s own contract is untouched — it is not in the diff — and
  `generate_batch(count=1)` still raises on an abandoned candidate (AC-019).
  What a count=1 caller *reads* does change: the message is now the batch's
  rather than the candidate's. The candidate's own exception is chained as
  `__cause__` on both exits, so nothing is lost (review cycle 1, F-004).
- G-4: Commit only your own files; `nonogram_admin.db` and the egg-info churn
  are standing noise.

## System contract

- INV-003 / NFR-002 — automatic-retry counters stay within their bounds
  (check: TestRegenerate_StopsAtMaxRetryBound, and G-1 above)
- ADR-0011 — every solve deadline-bounded; a batch must not become a way to
  spend unbounded time (check: TestBatch_DoesNotSwallowATimeout)
- ADR-0002 — one bound per question, no second bound (check: review-lens; the
  new constant answers a different question and says so in its docstring)

## Open question for the owner

**Should a batch survive a `SolverTimeout` too?** Decided no here, because it
would remove the batch's only time bound. The honest alternative is a
*whole-batch* deadline — skip a timed-out candidate but give the batch its own
ceiling — which is a bigger change than this card and wants its own decision.
30x30 batches are the ones that will meet it.

## Worktree notes

### Measured on real batches, not only on scripted ones

Six real `generate_batch(count=20, sizes=[25])` runs against the actual
pipeline, after the change:

```
run 1: 20/20   run 3: 20/20   run 5: 18/20
run 2: 18/20   run 4: 20/20   run 6: 20/20
=> 4 full, 2 short-but-kept, 0 lost entirely
```

Two of six batches met an abandoned candidate. Before this card each of those
runs raised and discarded the 18 puzzles it had already produced; now they are
kept and the shortfall is stated. That ratio also matches the per-candidate
measurement — p = 0.02 over 20 candidates gives a ~33% chance of at least one,
and 2 of 6 is 33%.

### Why the tests script `generate` instead of running it

Every assertion in `tests/test_batch_abandonment.py` needs a *specific*
sequence of outcomes — abandonment in the first slot, the last slot, twice in a
row, three times in a row, never. Producing those for real means waiting on a
1-in-50 event at a size where each candidate costs about half a second, per
assertion. The scripted double makes the sequence the input.

What the scripting stands on — that `generate` raises `GenerationAbandoned`
when it cannot make a candidate unique within the bound — is
`TestRegenerate_StopsAtMaxRetryBound`'s claim, not this file's, and the six
real runs above are the end-to-end check that the two meet.

### Eight mutants, eight killed

The counter never incremented; the counter never reset on success; `>=`
weakened to `>`; `except Exception` instead of `except GenerationAbandoned`
(the timeout-swallowing version); the empty-batch raise removed; `from
abandonment` dropped; the shortfall note never written; and the two shortfalls
merged into one number. The last two matter most — they are the ones that would
leave the behaviour correct and the owner uninformed, which is the failure mode
CARD-080 and CARD-082 were both about.

### Review cycle 1 fixes (5900515)

Three of the five findings were one root cause: the empty-batch exit was
written as the general all-failed path, when the consecutive bound reaches
every `count >= 3` case first.

| finding | what was wrong | what it is now |
|---|---|---|
| F-001 | Only the consecutive exit chained the candidate's abandonment, so `count` 1 or 2 gave `__cause__ None` — **CARD-080's F-008 defect on the other branch of the function whose own commit message cites that lesson.** | Both exits chain it, pinned by a parametrize spanning count 1, 2, 3 and 10 — the boundary between the two exits. |
| F-003 | The empty-batch message read as the general answer while being reachable only below the bound. | Says so, and says why. |
| F-004 | G-3 claimed the single-puzzle contract was untouched. `generate` is; what a count=1 caller *reads* is not. | Narrowed to what was checked. |
| F-002 | The card withdrew `puzzle_count == count` and left four assertions pinning it. | They assert what survives: the batch *tracks* what it stored, and that number agrees with the rows in it. |
| F-005 | A short script meant two mutants died on `IndexError`, not on an assertion. | Padded to the full count. |

**Two things fell out of F-002 that were not on the card.**

`tests/test_batch_history.py` had never had CARD-082's treatment — 18
`create_batch` calls, **900 real unseeded draws per run**, 30s of every suite
run, all to assert metadata (ids, sizes, themes, timestamps, ordering). Counts
are now the floor and unasserted sizes are 15. The three heavy batch files
together: **38s → 10.4s**.

And removing the exact-count assertion surfaced a defect underneath it: three
tests called `_generate_random_batch` explicitly *after* `create_batch`, which
already generates synchronously. **Every one of those batches was generated
twice**, so the store held twice the rows `puzzle_count` claimed. Harmless
while nothing compared the two — which is exactly why replacing `== 20` with
`== len(stored)` found it.

Seven mutants, seven killed.
