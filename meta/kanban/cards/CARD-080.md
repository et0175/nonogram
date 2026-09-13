# CARD-080: Quarantine the stored puzzles that are not uniquely solvable ⚑

**Status:** ready
**Priority:** P1
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/080-quarantine-ambiguous-rows
**Worktree:** —
**Source:** CARD-077's pre-implementation measurement (2026-09-14); owner decision "report only on CARD-077, cleanup is its own card"
**Idea:** —
**Wave:** 1
**Depends on:** CARD-077 (its report is this card's input)
**Touches:** src/nonogram/admin/regrade.py (read its skip list), src/nonogram/admin/app.py (one action), src/nonogram/admin/templates (a review screen), tests/test_admin_quarantine.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

**20 of the 36 puzzles stored in `nonogram_admin.db` are not uniquely
solvable.** Every one of them reports `solution_count = 2` against the real
solver, and four of the 36 rows are marked `approved` — that is, eligible for
a book. A clue set with two solutions is not a nonogram: a solver following
the clues cannot reach the intended picture, so a puzzle printed from one of
these rows is unsolvable as drawn.

They were not produced by the generation pipeline. Their stored grades —
scores 65..100, tiers 33 Medium / 3 Hard and no Easy — are a distribution
ADR-0013's scorer cannot produce, because it bounded a line-solvable puzzle
at 15 points. They came from
`admin/image_to_puzzle.create_puzzle_from_image`, a private path that derived
a tier from the grid's *size* and never called the solver at all. CARD-076
deleted that function (it was already dead), so no new row can be created this
way — but the rows it wrote are still in the database and still reachable by
book assembly.

CARD-077 re-grades what it can and lists these rows with their reason; by the
owner's decision it changes nothing about them, so that deleting stored data is
never a side effect of a card whose job is re-grading. This card is that
decision, taken deliberately.

**⚑ Risk:** touches stored rows the owner may still want. Mitigations: the
owner chooses the disposition per row or in bulk from a screen that shows what
is wrong with each; nothing is deleted without that choice; the action is
reversible for as long as the rows are only marked, not removed.

## What to implement

1. **A quarantine status, not a delete.** Non-unique rows get
   `status = 'rejected'` (the value the review screens already understand) plus
   a recorded reason, so they leave the approved pool and cannot reach a book
   while remaining inspectable. Deletion, if the owner wants it, is a second
   action on the same screen.
2. **Re-verify at the moment of action, do not trust the report.** The solve is
   cheap (36 rows in 0.5s measured) and a stale report would quarantine a row
   that is actually fine. One solve per row, through the real solver
   (CON-005), deadline-bounded (ADR-0011).
3. **A review screen** listing each affected row with its extent, its stored
   grade, the verdict (`2 solutions`), and a rendered thumbnail, so the owner
   is deciding about pictures rather than about ids.
4. **Bulk and per-row actions**, both behind a confirmation showing the count.
5. **Report what changed** — before/after counts by status, written to the
   card's Worktree notes.

## Acceptance criteria

- **AC-A** — given a stored row whose clues have two solutions, when the
  quarantine action runs, then its status becomes `rejected` and its reason is
  recorded; its grid, clues and grades are unchanged.
  *test:* `TestQuarantine_MarksAmbiguousRowRejected`
- **AC-B** — given a stored row that is uniquely solvable, when the action
  runs over the whole table, then that row is untouched in every column.
  *test:* `TestQuarantine_LeavesSolvableRowsAlone`
- **AC-C** — the action re-solves each row rather than reading CARD-077's
  report, so a row that has since been fixed is not quarantined.
  *test:* `TestQuarantine_ReverifiesRatherThanTrustingTheReport`
- **AC-D** — a quarantined row is not offered to book assembly.
  *test:* `TestQuarantine_QuarantinedRowsAreNotSelectableForABook`
- **AC-E** — running the action twice changes nothing the second time.
  *test:* `TestQuarantine_IsIdempotent`

## Guardrails

- G-1: Never run against the live DB from a test — copies only.
- G-2: No row is deleted by the default action; deletion is a separate,
  separately-confirmed action.
- G-3: Uniqueness comes from the real solver (CON-005); no heuristic, no
  reading of a stored flag.
- G-4: No edits under `src/nonogram/solver/`, `difficulty.py`,
  `orchestrator.py`.
- G-5: Commit only your own files; `nonogram_admin.db` is standing untracked
  noise.

## System contract

- CON-005 — the solver's verdict is the uniqueness authority (check:
  TestQuarantine_ReverifiesRatherThanTrustingTheReport)
- ADR-0011 — every solve is deadline-bounded (check: review-lens)
- NFR-003 / CON-009 — admin action bound to localhost (check: existing admin
  binding tests)
- ADR-0006/R1 — no new runtime dependency (check: review-lens)

## Architecture context

- **FR:** FR-006 (uniqueness is the product's defining property)
- **CON:** CON-005
- **ADR:** ADR-0011
- **Components:** admin panel; COMP-005 called, not changed

**Open question for the owner, to settle on this card:** these 20 rows are
image-derived puzzles. Re-deriving a *unique* puzzle from the same source image
is what CARD-075's nudge exists for — so a third disposition, "re-generate from
the source image", may be better than either keeping or deleting them. The
screen should make that choice visible even if the action lands later.

## Worktree notes

—
