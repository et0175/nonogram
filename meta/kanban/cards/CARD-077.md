# CARD-077: Re-grade the admin DB under the ladder scale — admin action, backup first, legacy columns kept ⚑

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/077-admin-db-regrade
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-10 (Migration paragraph, ⚑ risk); ADR-0029 Migration: rewrite
**Idea:** —
**Wave:** 1
**Depends on:** CARD-076
**Touches:** migrations/versions/006_*.py (new, expand-only: legacy grade columns), src/nonogram/db/models.py (two nullable legacy columns), src/nonogram/admin/regrade.py (new — the batch), src/nonogram/admin/app.py (one POST route + confirmation page), src/nonogram/admin/templates/regrade.html (new), src/nonogram/admin/templates/dashboard.html (link), tests/test_admin_regrade.py (new), tests/test_db_e2e_smoke.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Every stored `difficulty_score` and `difficulty_tier` in `nonogram_admin.db`
was graded under ADR-0013 and is wrong under ADR-0029's scale
(Migration: rewrite). Grandfathering is not an option: NFR-007's
machine-independence would be false for old rows, and a book assembled from
a mix of ADR-0013 and ADR-0029 grades would be mislabelled. The re-grade is
a real operational job — it re-solves every stored puzzle from its clues —
and is the one point of no return in the 2026-09-12 delta, which is why it
is its own card, scheduled last within Increment 10, run behind an admin
action, and rehearsed on a backup first.

**⚑ Risk (register capture offered by the handoff):** point of no return
once run on the live DB. Mitigations on this card: expand-only migration,
old values copied to legacy columns before overwrite, dry-run mode, backup
rehearsal, owner eyeball of the new distribution before the legacy columns
are dropped (a later card, not this one).

**Sequencing.** After CARD-076 (the scorer and classifier it re-grades
with). CARD-072 need not land first — the batch writes `strategies_used`
from the same solve, and CARD-072's display picks the values up whenever it
lands; if CARD-072 is already merged, reuse its `add_puzzle`
`strategies_used` plumbing rather than writing the column twice.

## What to implement

1. **Expand-only Alembic migration `006`:** add nullable
   `legacy_difficulty_score` (Integer) and `legacy_difficulty_tier`
   (String) to `puzzles`. No column dropped, no NOT NULL, no backfill in
   the migration itself; reversible downgrade drops the two columns.
   Existing rows stay valid (CARD-072 G-4's rule).
2. **The batch (`admin/regrade.py`):** for every stored puzzle, re-derive
   clues from the stored grid (`nonogram.clues`, the CARD-051 route), solve
   ONCE through the real pipeline path (`solver.solve` -> the CARD-076
   classifier with `(score, branch_nodes)`), and rewrite
   `difficulty_score`, `difficulty_tier` and `strategies_used` (the ordered
   rung list + `guess` iff branched — the same derivation CARD-072 uses).
   Before the first overwrite of a row, copy its current score/tier into
   the legacy columns **only if they are still NULL** — so a re-run never
   clobbers the ADR-0013 values with ADR-0029 ones. Deterministic and
   idempotent: running it twice yields identical rows (NFR-007/CON-014;
   ADR-0015). Per-row solver deadline (ADR-0011's
   `GENERATION_BUDGET_SECONDS` family); a row that times out or whose grid
   is not uniquely solvable is left unchanged and listed in the report,
   never silently rewritten.
3. **Dry-run mode** that produces the report (per-row old tier -> new tier,
   the new tier distribution, rows skipped and why) without writing.
4. **Admin action:** one POST route behind a confirmation page showing the
   dry-run report first; the confirm button runs the write. Localhost-only
   like the rest of the admin (NFR-003/CON-009); no new dependency.
5. **Rehearsal, in this order, recorded in Worktree notes:** copy
   `nonogram_admin.db` -> run the batch on the copy -> record the new tier
   distribution and the skipped rows -> put the distribution in front of
   the owner in the admin list. **Running it on the live DB is the owner's
   call after that review, not the card's.**
6. Book assembly and PDF headers read `difficulty_tier` strings
   (`admin/app.py:1013-1015`, `book_pdf_generator.py:143-145` count
   Easy/Medium/Hard only) — add the `Guess` count so books built after the
   re-grade are not silently short a tier.

## Acceptance criteria

- **AC-A** (rewrite) — given a DB copy with rows graded under ADR-0013,
  when the batch runs, then every uniquely solvable row's
  `difficulty_score`/`difficulty_tier`/`strategies_used` equal what the
  CARD-076 scorer and the CARD-073 rung list produce for its clues, and
  the legacy columns hold the pre-run values.
  *test:* `TestRegrade_RewritesGradeAndStrategiesFromOneSolve`
- **AC-B** (idempotent, deterministic) — running the batch twice on the
  same copy yields byte-identical rows, and the legacy columns are not
  overwritten by the second run.
  *test:* `TestRegrade_IsIdempotentAndPreservesLegacyColumns`
- **AC-C** (safety) — a row whose grid is not uniquely solvable or whose
  solve times out is left unchanged and appears in the report with its
  reason.
  *test:* `TestRegrade_SkipsUnsolvableRowsAndReportsThem`
- **AC-D** (dry-run) — the dry-run mode writes nothing and reports the
  same distribution the write mode would produce.
  *test:* `TestRegrade_DryRunWritesNothing`
- **AC-E** (migration) — migration 006 upgrades an existing DB in place
  (existing rows readable, `strategies_used` untouched) and downgrades
  cleanly.
  *test:* `TestMigration006_ExpandOnlyAndReversible`
- **AC-F** (owner gate, handoff checkpoint) — the re-grade over a copy of
  `nonogram_admin.db` completes and the new tier distribution is in front
  of the owner in the admin list; Worktree notes carry the distribution
  and the skipped rows. Live-DB run is not on this card.

## Engineering constraints

- **EC(ADR-0029/R2, projected)** — each row is re-graded from exactly one
  solve; the tier and the strategies list of a row come from that same
  solve (solver entered once per row — call-counter test).
  *test:* `TestRegrade_EntersSolverOncePerRow`
- **EC(NFR-007 / CON-014, projected)** — the re-graded values of a row are
  a pure function of its stored grid: identical under a dilated clock and
  on repeated runs.
  *test:* `PropertyTest_Regrade_PureFunctionOfStoredGrid`

## Guardrails

- G-1: Never run on the live `nonogram_admin.db` from a test or from the
  card's own work — copies only; the live run is the owner's action.
- G-2: Migration is expand-only: no column dropped or narrowed, no NOT
  NULL; dropping the legacy columns is a later card after the owner's
  review.
- G-3: Tier and strategies derive only through CARD-076's classifier and
  CARD-073's rung list — no private grading logic in `admin/` (ADR-0025/R2,
  ADR-0029/R2); no re-solve for classification beyond the one per row.
- G-4: No edits under `src/nonogram/solver/`, `difficulty.py`,
  `orchestrator.py`, `export/**`, `web/**`; `nonogram.clues` is called, not
  reimplemented (CARD-051).
- G-5: Do not build the strategy filter or detail display (CARD-072).
- G-6: `nonogram_admin.db` is standing untracked noise in the working
  tree — never commit it; commit only your own files with explicit
  pathspecs.

## System contract

- ADR-0029/R2 — no second solver entry for classification (check:
  TestRegrade_EntersSolverOncePerRow)
- ADR-0025/R2 — tier classification has exactly one implementation, in
  difficulty.py (check: review-lens; CARD-076's ast guard covers src/)
- ADR-0029/R3 / CON-014 — no clock reading enters a grade (check:
  PropertyTest_Regrade_PureFunctionOfStoredGrid)
- CON-005 — the solver's verdict is the uniqueness authority; a row that
  is not uniquely solvable is not re-graded, it is reported (check:
  TestRegrade_SkipsUnsolvableRowsAndReportsThem)
- ADR-0011 — every solve is deadline-bounded (check: review-lens)
- NFR-003 / CON-009 — admin action bound to localhost like the rest of the
  admin (check: existing admin binding tests)
- ADR-0006/R1 — no new runtime dependency (check: review-lens)

## Architecture context

- **FR:** FR-026, FR-029 (stored `strategies_used`)
- **NFR:** NFR-007
- **CON:** CON-014, CON-005
- **ADR:** ADR-0029 (Migration: rewrite; R2, R3), ADR-0025 (R2), ADR-0011,
  ADR-0015
- **Components:** admin panel + `src/nonogram/db/**` (known mapping gap:
  no COMP owns these globs — trace.yml FR-029 row); COMP-006 / COMP-005
  called, not changed
- **Trace:** meta/architecture/trace.yml (FR-026, FR-029 rows)

**Checkpoint (handoff, the re-grade half):** the re-grade batch over a copy
of `nonogram_admin.db` completes and the owner has eyeballed the new
distribution in the admin list.
**Collapses:** the stored-grades-are-wrong migration risk (⚑ register
capture offered).
**Rollback (handoff, verbatim):** Not additive: the point of no return is
running the re-grade batch on the live DB. Everything before it reverts
with the branch; the batch itself must be run on a backup first, and the
old columns are dropped only in a later card.

## Worktree notes

—
