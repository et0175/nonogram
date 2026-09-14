# CARD-084: Drop the legacy difficulty columns — the snapshots replaced them

**Status:** done
**Priority:** P3
**Category:** chore
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/084-drop-legacy-difficulty-columns
**Worktree:** ../PythonProject4-CARD-084
**Source:** owner decision — "I think we can remove legacy difficulty"
**Idea:** —
**Wave:** 1
**Depends on:** — (CARD-077 merged 3de767f, which added the columns and said dropping them is a later card)
**Touches:** src/nonogram/db/models.py, src/nonogram/admin/regrade.py, src/nonogram/admin/templates/regrade.html, src/nonogram/admin/app.py (one docstring), migrations/versions/007_drop_legacy_grade_columns.py (new), tests/test_admin_regrade.py, tests/property/test_regrade_determinism.py
**Review score:** — (merged without a review cycle at the owner's call; the code was already complete and green when the card was parked)
**Started:** 2026-09-14
**Closed:** 2026-09-14
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Migration 006 added `legacy_difficulty_score` / `legacy_difficulty_tier` so
CARD-077's re-grade batch had somewhere to put the value it was about to
overwrite. Its own docstring names this card:

> Dropping them once the owner has reviewed the new distribution is a separate,
> deliberate card.

The owner has reviewed it. What makes this a removal rather than a judgement
call is that **the columns never held anything**. Measured today across all
three databases that have the schema:

| database | rows | legacy columns filled | already on the ladder scale | stamp |
|---|---|---|---|---|
| `nonogram_ubss` (Render, production) | 86 | **0** | 86/86 | 006 |
| `nonogram_dev` (local Postgres) | 294 | **0** | 34/294 | 006 |
| `nonogram_admin.db` (SQLite) | 16 | **0** | 16/16 | 006 |

0 of 396 rows, everywhere. Production's 86 rows were re-graded **out of band on
2026-09-13**, before migration 006 existed, so the capture path they were meant
to protect never ran for them — a fact CARD-077's `dc47626` already records and
`regrade.html:141` already tells the operator. The columns have been carrying a
promise they were never in a position to keep.

### What replaced them, and why it is better

A JSON snapshot taken immediately before a run, committed to git:

- `meta/ops/render-grades-backup-20260913.json` — 86 rows (production's genuine
  pre-run grades, taken before the out-of-band run)
- `meta/ops/dev-grades-backup-20260914.json` — 294 rows, taken for this card

It beats the columns on every axis that matters:

1. **It is versioned and off-box.** A column lives in the database it is meant
   to protect; a restore that loses the database loses the safety net with it.
2. **It captures every row, not just re-graded ones.** The columns only fill on
   a row the batch actually rewrites; a skipped row (ambiguous, timed out,
   unreadable — CARD-077 AC-C) records nothing.
3. **It can be taken more than once.** `_capture_legacy_grade`'s guard is
   deliberately once-per-row-*ever*, so the columns hold the state before the
   *first* run and are blind to every run after it. A second re-grade under a
   future scale would have nowhere to go.
4. **It is auditable by reading a file**, not by querying production.

Point 3 is the one that settles it: the columns are a one-shot mechanism, and
the one shot was already spent off-band on production without firing.

### What this costs

CARD-077's **AC-B** is two claims joined by "and": *running the batch twice on
the same copy yields byte-identical rows, and the legacy columns are not
overwritten by the second run*. The first half is about the grader being
deterministic and survives untouched — its test
(`test_two_runs_leave_byte_identical_rows`) is the real statement and gets
stronger, not weaker, once it is not sharing a class with a column check. The
second half is being retired on purpose, and this card is where that is
recorded: **the pre-run grades of a future re-grade are preserved by taking a
snapshot first, as a documented operator step, not by a column.**

Note that `nonogram_dev` has **260 rows still on the pre-ladder scale**, so a
future re-grade run against dev is a real possibility, not a hypothetical. That
is exactly why the dev snapshot is a precondition of this card and not a
formality.

## Acceptance criteria

- **AC-1** (schema) — migration `007` drops `legacy_difficulty_score` and
  `legacy_difficulty_tier` from `puzzles`, and nothing else. Every other
  column, `strategies_used` and `difficulty_*` included, is untouched, and
  existing rows stay valid and readable across the upgrade.
  *test:* `TestMigration007_DropsExactlyTheTwoColumns`
- **AC-2** (reversible in shape) — `007`'s `downgrade` re-adds the two columns
  as nullable, so `006 -> 007 -> 006` returns the schema to where it was. It
  does **not** claim to restore data: the values are gone, which is the point
  of the drop, and the docstring must say so rather than imply an undo.
  *test:* `TestMigration007_DowngradeRestoresTheShapeNotTheData`
- **AC-3** (the batch still does its job) — `regrade` rewrites
  `difficulty_score` / `difficulty_tier` / `strategies_used` from one solve,
  skips what it cannot grade, and is still idempotent: two runs on the same
  copy leave byte-identical rows.
  *test:* existing `TestRegrade_RewritesGradeAndStrategiesFromOneSolve`,
  `TestRegrade_SkipsUnsolvableRowsAndReportsThem`, and
  `test_two_runs_leave_byte_identical_rows` (its class renamed, since it no
  longer preserves legacy columns)
- **AC-4** (no reader left behind) — no module, template, or test reads or
  writes either column, and `NO_LEGACY_TIER` / `_capture_legacy_grade` are
  gone. `git grep -w legacy_difficulty_score` and
  `git grep -w legacy_difficulty_tier` return hits only in history-bearing
  documents: migration `006`, migration `007`, `CARD-077.md`, this card, and
  `meta/review/`.
  *test:* a structural test in `tests/test_admin_regrade.py` that walks
  `src/nonogram/**/*.py` and the admin templates for the two names, in the
  spirit of `tests/test_cli.py`'s import guard
- **AC-5** (the operator is told the truth) — `regrade.html` no longer promises
  a legacy capture. It states what is actually true: the run overwrites the
  stored grades, it is not reversible from inside the app, and the pre-run
  values are whatever snapshot was taken before it.
- **AC-6** (applied) — `007` is applied to all three databases and each reports
  stamp `007` with the two columns absent.

## Guardrails

- **G-1** — **snapshot before schema.** `meta/ops/dev-grades-backup-20260914.json`
  is committed on this branch *before* `007` runs anywhere. It was taken against
  a quiet database with an asserted-stable row count (294 → 294 across the read);
  do not replace it with a read taken while the admin panel is in use.
- **G-2** — **the three databases are applied in this order: SQLite, dev,
  Render.** Production last, after the first two have proved the migration on
  both backends. Render is the owner's data and the only copy that matters.
- **G-3** — never commit `nonogram_admin.db` (CARD-077 G-6 / CARD-080 G-5). It
  is standing modified noise, along with `src/nonogram.egg-info/*` and the stray
  `*.pdf` files in the repo root.
- **G-4** — **do not touch migration `006`.** It is applied everywhere and is
  part of the upgrade path from any older copy; `007` supersedes it forward,
  it does not edit it. The existing `TestMigration006_*` tests stay green and
  stay meaningful — they test the 005 → 006 step, which is still a real step.
- **G-5** — `difficulty.tier_of_record` keeps its "not a tier" reading of the
  empty string. `NO_LEGACY_TIER` was one caller, not its reason for existing:
  the stored rows in `nonogram_dev` use six different tier spellings
  (`easy`/`Easy`/`medium`/`Medium`/`hard`/`Hard`), which is what that function
  is actually for.
- **G-6** — no behaviour change to grading, classification, or the ladder.
  This card removes a storage side-effect and nothing else.

## Plan

1. Take the dev snapshot (**done** — 294 rows, count asserted stable) and
   commit it.
2. Write `migrations/versions/007_drop_legacy_grade_columns.py`, revision `007`,
   down_revision `006`, `batch_alter_table` for SQLite as 004/005/006 do.
3. Remove the two `Column`s from `src/nonogram/db/models.py`.
4. Remove from `src/nonogram/admin/regrade.py`: the `NO_LEGACY_TIER` constant
   and its comment block, its `__all__` entry, `_capture_legacy_grade` and its
   call site, and the module-docstring paragraph that promises the capture
   (~15 references).
5. Rewrite the four legacy-capture sentences in
   `src/nonogram/admin/templates/regrade.html` (lines 26, 133, 134, 141) and
   the one in `src/nonogram/admin/app.py:1781`.
6. Tests: drop the four legacy-specific tests, rename
   `TestRegrade_IsIdempotentAndPreservesLegacyColumns`, fix the two references
   in `tests/property/test_regrade_determinism.py:205-206`, and add the AC-1,
   AC-2 and AC-4 tests.
7. Apply `007` in G-2's order, recording each stamp. **Done 2026-09-14:**

| # | database | rows before/after | legacy filled | stamp |
|---|---|---|---|---|
| 1 | `nonogram_admin.db` (SQLite) | 16 / 16 | 0 | 006 -> **007** |
| 2 | `nonogram_dev` (local PG) | 282 / 282 | 0 | 006 -> **007** |
| 3 | `nonogram_ubss` (Render) | 86 / 86 | 0 | 006 -> **007** |

SQLite was proved on a `/tmp` copy before the real file was touched — the
backend where `DROP COLUMN` rebuilds the table, so "only two columns went" is a
claim about what the rebuild copied. Grades, tiers and strategies all intact on
the copy first, then on the file. `meta/ops/render-grades-backup-20260914-pre007.json`
holds production's 86 rows taken immediately before the migration, with the
count asserted stable across the read.

0 legacy values on all three, exactly as the card predicted — 384 rows and not
one of them had anything to lose.

## Open questions for the owner

- **Q-1** — should `meta/ops/` gain a short `README.md` saying that a snapshot
  is a required step before any re-grade run? Without it, the mechanism that
  replaces the columns is a convention held in this card's prose. *(Suggested:
  yes, three lines.)*
- **Q-2** — ~~`nonogram_dev` holds 260 rows still on the pre-ladder scale. Do
  you want a re-grade run against dev after this card lands?~~ **Answered
  2026-09-14: no.** Dev's grades do not need to be correct. This does not
  change the card: the snapshot still has to exist before `007` drops the
  columns, because it is the only remaining record of what those 294 rows were
  graded, and "we do not need it today" is not "we can never want it".

## Worktree notes

**Unparked and rebased onto main 2026-09-14**, after CARD-085 and CARD-086
merged. One conflict, in `regrade.py`: this card deletes the `NO_LEGACY_TIER`
block and CARD-086 added `REGRADE_BUDGET_SECONDS` immediately after it.
Resolved by keeping the new constant and dropping the old one — the two changes
are adjacent, not competing. The `regrade` loop then carried both edits
together: CARD-086's run deadline and `not_attempted`, and this card's removal
of the legacy capture from the same block. 222 admin tests pass after the
rebase.

**Dev had drifted.** The snapshot in `meta/ops/dev-grades-backup-20260914.json`
records 294 rows; dev held 282 by the time the migration ran. That is the owner
pruning between the two moments, not a fault — and it is the reason the
snapshot names its `taken_at`. It is a record of a moment, not a claim about
the present.

**Production checked after the fact**, not only before: the live panel still
answers `401` to an anonymous request, so the migrated schema and CARD-085's
credential gate are both working against the same database.
