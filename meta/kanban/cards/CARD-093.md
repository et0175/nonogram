# CARD-093: A random batch that stops early keeps the puzzles it had already made

**Status:** in progress
**Priority:** P3
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** yes
**Branch:** card/093-batch-keeps-puzzles-it-made
**Worktree:** ../PythonProject4-CARD-093
**Source:** owner — "open a card for finding 9" (`docs/GENERATION_ALGORITHM.md` §10.2 finding 9, CARD-092)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-083 (merged) — revisits one of its decisions; CARD-088 (merged) — the batch clock
**Touches:** src/nonogram/orchestrator.py (`generate_batch`), src/nonogram/admin/batch_generator.py (`_generate_random_batch`), tests/test_batch_abandonment.py, docs/GENERATION_ALGORITHM.md (§9.1, finding 9)
**Review score:** —
**Started:** 2026-09-15
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`orchestrator.generate_batch` collects puzzles in memory and returns them at the
end. The admin's random batch (`BatchGenerator._generate_random_batch`, the
only production caller) stores them only after that call returns. So **any
exception out of `generate_batch` discards every puzzle the batch had already
made**, and the batch row is marked `ERROR` with nothing stored.

Two exits raise after puzzles may already exist:

| exit | what the batch did | what is lost |
|---|---|---|
| `MAX_CONSECUTIVE_ABANDONMENTS` (3) in a row | stops, as CARD-083 designed | every puzzle made before those three |
| `SolverTimeout` on one candidate | stops (CARD-083's open question: should it survive?) | the same |

A third path loses the same work for a different reason: CARD-088's own rationale
for the 75 s batch clock was that "a worker killed mid-batch loses everything it
had produced". The clock makes that unlikely; nothing makes it harmless.

The admin comment in `_generate_random_batch`'s caller says "each one commits
individually". Each *does* commit individually — but only after the whole batch
has succeeded, so the comment describes a property the flow does not have.

**Image batches are not affected.** `admin.app` generates and stores one picture
at a time and records an error per picture, so a failure keeps everything before it.

### This revisits a CARD-083 decision, deliberately

CARD-083 made 3-in-a-row raise on purpose: at that rate a request is infeasible
rather than unlucky, and "shorter" would be the wrong answer. That reasoning is
about **stopping** — not spending 47 more candidates' worth of solves on a
hopeless request — and this card keeps it. What CARD-083 did not weigh is the
puzzles made *before* the three, and its own measurement is the reason it
matters: it exists because "at 25x25 a 50-puzzle batch lost everything roughly a
third of the time". It fixed that for one bad draw and left it in place for three.

### How often, honestly

Rarely, at the parameters the admin actually sends (density 50, no tier):

- 3 consecutive abandonments need three failures in a row at a per-candidate
  rate of about 1% at 30x30 since CARD-091 — roughly one in a million windows.
- `SolverTimeout`: 0 in 100 requests at 30x30 since CARD-091 (it was 1 in 100).

So this is a P3: the loss is total when it happens, and it happens seldom. It
becomes likely the moment a caller passes a tier — a Medium request is ~3% of
random grids, so abandonments in a row are the expected case — which the admin
does not do today but `generate_batch` accepts.

## Acceptance criteria

- **AC-1** (the stopping rule stands) — 3 consecutive abandonments still end
  the batch at the third, and no further candidate is attempted.
  `test_it_stops_rather_than_finishing_the_loop` keeps passing unchanged.
- **AC-2** (puzzles made before a stop are stored) — a scripted batch that makes
  7 puzzles and then abandons 3 in a row leaves **7 puzzles in the store**, with
  the batch record saying why it stopped and how many were made. Likewise for a
  batch that makes 7 and then meets a `SolverTimeout`.
- **AC-3** (the reason is visible) — the batch record distinguishes "stopped:
  3 consecutive abandonments" and "stopped: solver timeout" from a clean
  finish and from a clock stop, as separate notes, the way CARD-080/083/088
  already keep refusals, abandonments and not-attempted counts apart.
- **AC-4** (a batch that made nothing still fails loudly) — zero puzzles is
  still a failed batch, raised as today with the cause chained, whichever exit
  produced it (CARD-083 F-001's both-exits rule).
- **AC-5** (no second bound, no clock change) — `MAX_CONSECUTIVE_ABANDONMENTS`,
  `BATCH_BUDGET_SECONDS`, `MAX_BATCH_COUNT` and the per-candidate retry bounds
  are unchanged; `tests/test_admin_serving.py` still passes.
- **AC-6** (the doc follows) — `docs/GENERATION_ALGORITHM.md` §9.1 describes
  the new behaviour, finding 9 is marked closed with this card, and
  `meta/ops/check_doc_references.py` still resolves every reference.

## Guardrails

- **G-1** — `SolverTimeout` still **ends** the batch. Whether a batch should
  *survive* a timeout is CARD-083's open owner question and is not answered
  here; this card only stops the work made before it being thrown away.
- **G-2** — `orchestrator` does not learn about storage. Whatever mechanism
  hands puzzles to the admin as they are made, the domain module must not import
  the admin, the DB or the review service (ADR-0007; the structural import
  guard in `tests/test_cli.py` enforces the direction).
- **G-3** — image batches are untouched; they already keep partial work.
- **G-4** — `nonogram_admin.db`, `src/nonogram.egg-info/*` and the stray PDFs
  stay uncommitted; commit with explicit pathspecs only.

## Open questions for the owner

- **Q-1 — how should the made puzzles reach the store?**
  - **(a) Store as they are made (recommended).** `generate_batch` takes an
    optional `on_puzzle` callable and calls it once per finished puzzle; the
    admin passes its existing store step. Covers **all three** losses —
    consecutive abandonments, `SolverTimeout`, *and* a worker killed mid-batch —
    with one mechanism, and makes the "each one commits individually" comment
    true. Callers that pass nothing see no change, so the ten test modules that
    treat the result as a list are unaffected.
  - **(b) Return instead of raise when something was made.** 3-in-a-row ends
    the batch and returns a `BatchResult` with a new "gave up" marker. Smallest
    diff, but it covers only the abandonment exit: a timeout or a killed worker
    still loses everything.
  - **(c) Raise, but carry the puzzles on the exception.** Keeps CARD-083's
    loud exit, but every caller has to remember to dig the puzzles out of an
    error, and it still does nothing for a killed worker.
- **Q-2 — what status does a batch that stopped early, with puzzles stored,
  end in?** Proposed: **`COMPLETE` with a "stopped early" note** carrying the
  reason and the counts, and `ERROR` only when nothing was produced. The
  alternative is `ERROR` with puzzles attached, which would show a batch as
  failed while its puzzles sit in the list.
