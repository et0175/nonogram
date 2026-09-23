# CARD-138: Batch generation can ask for a difficulty

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/138-batch-difficulty-target
**Worktree:** ../PythonProject4-CARD-138
**Source:** owner, 2026-09-23 (after CARD-137's regrade: 37 mediums in ~300, a 150-puzzle book at 40/40/20 needs 60)
**Idea:** —
**Wave:** 25
**Depends on:** CARD-137
**Touches:** src/nonogram/admin/batch_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/generate_batch.html, tests/test_batch_difficulty_target.py
**Review score:** —
**Started:** 2026-09-23
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The engine can already generate to a tier: `GenerationRequest.difficulty` drives the
resample loop (a unique puzzle whose grade misses the requested tier is discarded and
the source is asked again, POL-004), and the CLI exposes it as `--difficulty`. The admin
batch generator hard-codes the opposite — `batch_generator.py:438`
`difficulty_tier=None,  # Accept any difficulty` — so the only way to fill a book's
medium quota is to generate at random and hope.

After CARD-137 moved the medium/hard cutoff to 90, medium is a wide band rather than a
sliver, so a targeted resample now terminates quickly. Before it, this field would have
been a trap.

Add the field:

1. **`generate_batch.html`** gains a difficulty select — Any (default, today's
   behaviour) / Easy / Medium / Hard — beside the existing size and count fields, using
   the existing form controls and tokens (no new CSS).
2. **The route** passes the chosen tier through to `batch_generator`, which passes it to
   `orchestrator.generate_batch(difficulty_tier=...)` instead of the hard-coded `None`.
   Parse the tier through `difficulty.parse_tier` — do not re-implement the mapping, and
   do not compare scores against cutoffs anywhere (ADR-0031/R1: `classify` is the only
   classifier).
3. **Report honestly when it gives up.** The resample loop is bounded; a batch that
   asked for 40 mediums and made 31 must say so in the batch note, the way CARD-093's
   early-stop note already does — not silently return fewer, and not fail the batch.
4. **Keep the existing stop rules.** `GenerationAbandoned` / `SolverTimeout` handling
   (batch_generator.py:433-445) is unchanged: work already made is kept and the batch
   completes with a note.

Out of scope: per-tier counts in one batch ("20 easy + 20 medium"), any change to the
resample bound itself, and image-mode generation (image mode takes no density and its
difficulty distribution is a separate question, already on the backlog).

## Acceptance criteria

- New: a batch requested as Medium returns only puzzles whose stored tier is medium, or
  fewer than requested with a note saying how many were made.
  test: TestBatchDifficulty_MediumBatchReturnsOnlyMediums
- New: a batch requested as Any behaves exactly as today (no tier filtering).
  test: TestBatchDifficulty_AnyIsUnchanged
- New: the generate form offers the four choices and defaults to Any.
  test: TestBatchDifficulty_FormOffersTheChoices
- New: when the loop cannot fill the count, the batch completes with the puzzles it made
  and the note names the shortfall.
  test: TestBatchDifficulty_ShortfallIsReportedNotSilent

## Guardrails

- G-1: `classify` stays the only place a score meets the cutoffs (the AST guard in
  tests/test_difficulty_tiers.py).
- G-2: Do not change the resample bound, `GenerationAbandoned`/`SolverTimeout` handling,
  or CARD-093's early-stop behaviour.
- G-3: Do not edit `src/nonogram/export/**`, `tests/fixtures/a4_golden/**`, or any book
  module (`book_*.py`) — this card is about generation, not assembly.
- G-4: The CLI's `--difficulty` path and its output stay byte-identical (CON-019).

## Architecture context

- **FR:** FR-008 (requested tier), FR-026
- **ADR:** ADR-0031 (three tiers), ADR-0029 (ladder), ADR-0005/CARD-137 (the cutoff)
- **Components:** COMP-002, COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23. CARD-137's regrade took production from 7 to 37 mediums in
  ~300 puzzles (~12%); a 150-puzzle book at 40/40/20 needs 60, so ~23 are missing and
  random generation fills that slowly. The owner chose this over moving the cutoff again
  (93 would call a 79%-probed grid "medium") and over editing the plan to match supply.
