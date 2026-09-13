# CARD-077: Re-grade the admin DB under the ladder scale — admin action, backup first, legacy columns kept ⚑

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/077-admin-db-regrade
**Worktree:** ../PythonProject4-CARD-077
**Source:** meta/architecture/handoff.md#increment-10 (Migration paragraph, ⚑ risk); ADR-0029 Migration: rewrite
**Idea:** —
**Wave:** 1
**Depends on:** CARD-076
**Touches:** migrations/versions/006_*.py (new, expand-only: legacy grade columns), src/nonogram/db/models.py (two nullable legacy columns), src/nonogram/admin/regrade.py (new — the batch), src/nonogram/admin/app.py (one POST route + confirmation page), src/nonogram/admin/templates/regrade.html (new), src/nonogram/admin/templates/dashboard.html (link), tests/test_admin_regrade.py (new), tests/test_db_e2e_smoke.py
**Review score:** —
**Started:** 2026-09-14T01:30Z
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

### Measured before implementation started (2026-09-14)

The card is written around a risky migration over real stored grades. Two facts
about the actual data change what it is.

**1. The working-copy `nonogram_admin.db` holds 0 puzzles.** The 36 puzzles and
8 batches exist only in the committed version of the file (it is tracked). The
working copy was emptied on 2026-09-11 at 19:44 and has not been written since
— repeated full-suite runs on 2026-09-13 left its mtime untouched, so the test
suite is not what emptied it. Whether those rows should come back is the
owner's call; they are recoverable with `git show HEAD:nonogram_admin.db`.

**2. Of the 36 rows in the committed copy, 20 (56%) are not uniquely
solvable** — every one reports `solution_count=2`. That is a data-integrity
problem, not a grading one: a clue set with two solutions is not a puzzle, and
four of the 36 rows are marked `approved`. AC-C already says such a row is
skipped and reported rather than rewritten, so the card's design is right; what
is new is the scale, which makes the skip list the headline rather than a
footnote.

Their provenance explains the grades. The stored scores are 65..100 with tiers
33 Medium / 3 Hard and no Easy — a distribution the ADR-0013 scorer cannot
produce, since it bounded a line-solvable puzzle at 15. These rows were graded
by `admin/image_to_puzzle.create_puzzle_from_image`'s private size-based
derivation, which never called the solver and never checked uniqueness. CARD-076
deleted that function as dead. So the re-grade is not "ADR-0013 values to
ADR-0029 values" — it is "values from a path that never solved anything, to real
ones".

**Dry run over a scratch copy** (writes nothing), 36 rows in 0.5s:

| | |
|---|---|
| re-graded | 16 |
| skipped, not uniquely solvable | 20 |
| new distribution | Easy 12, Hard 4, Medium 0, Guess 0 |
| moves | Medium->Easy 11, Medium->Hard 4, Hard->Easy 1 |

Not one row keeps its grade. The 0.5s runtime also means the card's "real
operational job" framing is over-cautious at this data size — the rehearsal
discipline still stands, but the batch is not long-running.

### What changed under the card while it was being built (2026-09-13)

Both facts above have since moved, and the note is kept rather than corrected
because it is the reasoning the design was built on.

**The rows came back, and then the broken ones went.** The owner restored the
36 puzzles and 8 batches into the working copy, and then directed that the 20
non-unique rows be deleted outright — reversing the "report only" reading of
fact 2. That deletion happened outside this worktree and is not this card's
work. The live table now holds **16 puzzles**, every one re-verified as
uniquely solvable, with `batches.puzzle_count` recomputed.

**What that changes for the card: nothing.** AC-C is still required and still
implemented — a non-unique or timed-out row is left untouched and reported with
its reason. What changed is that its tests now *construct* an ambiguous grid
(`tests/test_admin_regrade.py::AMBIGUOUS_GRID`, a 2x2 whose clues both
diagonals satisfy) instead of leaning on the real table containing one. That is
strictly better: the test no longer depends on the database happening to be
broken. Future non-unique rows are CARD-080's.

### AC-F rehearsal — over a copy of the live DB as it now stands (2026-09-13)

Never the live file (G-1). Procedure: `cp nonogram_admin.db` to a scratch
directory, `alembic upgrade 006` on the copy, dry run, then write, then a
second write.

The copy's `alembic_version` read **003** while its schema already carried
`puzzle_name`/`book_id`, so it was out of step with itself. The 003 -> 006
chain nevertheless ran clean on the copy (16 puzzles, 8 batches and 0 books
intact afterwards, both legacy columns present). **Worth the owner's attention
before any live run**: the stamp being behind the schema is a pre-existing
condition, not something 006 introduced.

| | |
|---|---|
| rows | 16 |
| re-graded | 16 |
| skipped | 0 |
| runtime | 0.15 s (dry run and write alike) |
| tiers before | Medium 15, Hard 1 |
| **tiers after** | **Easy 12, Hard 4, Medium 0, Guess 0** |
| moves | medium->easy 11, medium->hard 4, hard->easy 1 |
| rows keeping their tier | 0 |

**Skipped rows: none.** Every stored row was uniquely solvable, which is the
direct consequence of the deletion above.

Per row, smallest extent first:

| id | extent | before | after | strategies |
|---|---|---|---|---|
| 0a07ccc2 | 20x20 | Medium (65) | Hard (68) | simple_overlap, probe_contradiction |
| 0b322efc | 20x20 | Medium (65) | Easy (33) | simple_overlap |
| 13cc7c15 | 20x20 | Medium (65) | Easy (33) | simple_overlap |
| 272c63f7 | 20x20 | Medium (65) | Hard (67) | simple_overlap, probe_contradiction |
| 2b8233da | 20x20 | Medium (65) | Easy (33) | simple_overlap |
| ac588486 | 20x20 | Medium (65) | Easy (33) | simple_overlap |
| baf6ef1e | 20x20 | Medium (65) | Easy (33) | simple_overlap |
| 6c4f39f4 | 20x22 | Medium (68) | Easy (33) | simple_overlap |
| 24f98a82 | 23x20 | Medium (69) | Easy (33) | simple_overlap |
| b0a48383 | 20x23 | Medium (69) | Easy (33) | simple_overlap |
| 68a51875 | 20x24 | Medium (71) | Easy (33) | simple_overlap |
| dcc54bee | 20x24 | Medium (71) | Easy (33) | simple_overlap |
| e4be67be | 24x20 | Medium (71) | Easy (33) | simple_overlap |
| 75d22fd3 | 25x20 | Medium (72) | Hard (98) | simple_overlap, probe_contradiction |
| 3535e73e | 27x20 | Medium (75) | Hard (99) | simple_overlap, line_dp, probe_contradiction |
| cecbdc75 | 20x30 | Hard (80) | Easy (33) | simple_overlap |

Also checked on the copy:

- the dry run left the file **byte-identical** (sha256 before == after) and its
  report is outcome-for-outcome equal to the write run's;
- a **second** write run left the file byte-identical to the first — idempotent
  in fact, not just in principle;
- the legacy columns hold the pre-run pairs (15 Medium, 1 Hard) and the second
  run did not touch them;
- the admin puzzle list renders the new grades: 12 Easy badges, 4 Hard badges.

The old grades' spread is worth naming. Every one of the 16 sat in 65..75 with
a single 80, and the extent was the only thing that moved them — 20x20 rows all
scored exactly 65 whatever the picture. That is the size-based derivation
showing through. Under the ladder the same 16 spread across two real tiers, and
the four Hard ones are Hard because their solve needed
`probe_contradiction`, not because they are big: `cecbdc75` is the *largest*
grid in the table at 20x30 and it never leaves `simple_overlap`.

**Easy is one point on the scale.** All 12 Easy rows score exactly 33 — the
known consequence of a bottom-rung puzzle having share 1.0 by construction
(`difficulty.py`'s module docstring, CARD-076). Nothing to fix here; it is
input for ADR-0005's owed recalibration.

### Notes on the build

- **The stored score is the ADR-0029 float rounded *up*, not to nearest.** The
  column is an `Integer`, and a band is `(low, high]` with whole-number edges,
  so a ceiling keeps the stored number inside the same band as the float it
  came from. Ordinary rounding does not: a `line_dp` row that settled one cell
  at its top rung scores 33.08, rounds to 33, and would read back as Easy while
  the tier string beside it said Medium.
- **The legacy-capture guard is `legacy_difficulty_tier IS NULL`, and the
  capture always writes non-NULL** — `NO_LEGACY_TIER` (`""`) for a row that had
  no tier at all. Without that, a row with no stored grade would leave the guard
  open after the first run and the *second* run would capture the first run's
  own values as if they were the originals. AC-B's real requirement is
  once-per-row-ever, not once-in-the-common-case.
- **`guess` is appended to the strategies list on the tier, not on
  `branch_nodes`.** Both say the same thing, but reading the count in `admin/`
  would put a second reader of EC-015's rule outside `difficulty.py`
  (ADR-0025/R2).
- **Card item 6 was already done** by CARD-076's review fix: `app.py` and
  `book_pdf_generator.py` both count the Guess tier through
  `book_pdf_generator.tier_breakdown` and `difficulty.tier_of_record`. Verified,
  not re-implemented.
- **The card calls `nonogram_admin.db` "standing untracked noise" (G-6); it is
  in fact tracked.** The rule is the same either way — commit only with explicit
  pathspecs — but it is tracked, so an accidental `git add -A` would commit a
  real diff rather than a new file.
