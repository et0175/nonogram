# CARD-080: No write path can store a puzzle that is not uniquely solvable

**Status:** ready
**Priority:** P1
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/080-uniqueness-at-the-storage-boundary
**Worktree:** —
**Source:** CARD-077's pre-implementation measurement (2026-09-14); owner decision "report only on CARD-077, cleanup is its own card"
**Idea:** —
**Wave:** 1
**Depends on:** — (the cleanup this card was opened for has already been done)
**Touches:** src/nonogram/admin/puzzle_review.py (add_puzzle guard), src/nonogram/admin/app.py + batch_generator.py (handle the refusal), tests/test_admin_uniqueness_boundary.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

**The cleanup this card was opened for has been done.** On 2026-09-14, at the
owner's direction, the 20 stored puzzles that were not uniquely solvable were
deleted from `nonogram_admin.db` — each re-verified against the real solver at
the moment of deletion (all `solution_count = 2`, two of them `approved`), the
denormalised `batches.puzzle_count` recomputed, and all 16 survivors re-verified
as uniquely solvable. Integrity and foreign-key checks clean. What remains of
this card is the part that stops it happening again.

**Nothing structurally prevents a recurrence.** `puzzle_review.add_puzzle` is a
storage method that trusts its caller: it has no uniqueness check of its own.
Its two live callers — `batch_generator.py:335` and `app.py:466` — do go through
`orchestrator.generate`, which enforces INV-002, so today's writes are sound.
But that is an argument about callers, not a property of the store, and the 20
deleted rows are what the argument costs when it stops holding: they were
written by `image_to_puzzle.create_puzzle_from_image`, a third caller that
derived a tier from the grid's *size* and never called the solver. CARD-076
deleted that function, which closes this instance and not the class.

Uniqueness is the product's defining property (FR-006). A store that will
accept a non-puzzle is one refactor away from holding non-puzzles again.

## What to implement

1. **A uniqueness guard at the storage boundary.** `add_puzzle` refuses a grid
   whose clues do not have exactly one solution, raising rather than storing.
   The verdict comes from the real solver (CON-005), deadline-bounded
   (ADR-0011) — not from a flag the caller passes, which would just move the
   trust one frame up the stack.
2. **Callers handle the refusal** rather than swallowing it: the batch
   generator counts it as a failed candidate, the upload route reports it. A
   refusal is a bug in the caller, so it must be loud.
3. **The cost is bounded and measured before it ships.** A solve per stored
   puzzle is the same solve the pipeline already did, so the guard doubles it —
   measured at 0.5s for 36 rows, i.e. ~14ms each, against a batch that already
   spends seconds per puzzle generating. If a real corpus makes that wrong, say
   so with numbers rather than adding a bypass flag.
4. **An audit action** that re-verifies every stored row and reports (not
   changes) any that fail — so the property can be checked at any time, not
   only at write. This is the one piece of the original card worth keeping:
   the deletion is done, but being able to ask the question again is not.

## Acceptance criteria

- **AC-A** — given a grid whose clues have two solutions, when `add_puzzle` is
  called with it, then it raises and nothing is written.
  *test:* `TestStorageBoundary_RefusesAnAmbiguousGrid`
- **AC-B** — given a uniquely solvable grid, when `add_puzzle` is called, then
  the row is stored exactly as before this card.
  *test:* `TestStorageBoundary_StoresAUniqueGridUnchanged`
- **AC-C** — the guard asks the solver rather than trusting a caller-supplied
  flag or a stored column.
  *test:* `TestStorageBoundary_AsksTheSolverNotTheCaller`
- **AC-D** — a solve that times out is refused rather than stored, and says so
  (an unproven grid is not a proven puzzle).
  *test:* `TestStorageBoundary_RefusesRatherThanStoringAnUnprovenGrid`
- **AC-E** — the audit action reports every non-unique stored row and changes
  nothing.
  *test:* `TestStorageAudit_ReportsWithoutWriting`

## Guardrails

- G-1: Never run against the live DB from a test — copies only.
- G-2: This card writes no stored row and deletes none. The audit reports.
- G-3: Uniqueness comes from the real solver (CON-005); no heuristic, no
  reading of a stored flag, no caller-supplied boolean.
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

### The deletion this card was opened for (2026-09-14, done outside the card)

36 rows -> 16. Every deleted row re-verified against the real solver at the
moment of deletion rather than from the earlier report; all 20 reported
`solution_count = 2`, so none was removed on stale evidence, and a row that
could not be proven either way would have been kept (none occurred).

| | |
|---|---|
| deleted | 20 (2 of them `approved`) |
| kept | 16, each re-verified uniquely solvable |
| extents deleted | 20x20 x12, 20x24 x4, 20x30, 22x20, 26x20, 30x30 |
| after | `integrity_check: ok`, `foreign_key_check` clean, `batches.puzzle_count` recomputed |

Recovery, two ways: a file copy in the session scratchpad, and `git checkout --
nonogram_admin.db`, since the file is tracked and HEAD still holds all 36. The
DB is deliberately left uncommitted so that second path stays open until the
owner is satisfied.
