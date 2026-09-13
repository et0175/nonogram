# CARD-080: No write path can store a puzzle that is not uniquely solvable

**Status:** in_progress
**Priority:** P1
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/080-uniqueness-at-the-storage-boundary
**Worktree:** ../PythonProject4-CARD-080
**Source:** CARD-077's pre-implementation measurement (2026-09-14); owner decision "report only on CARD-077, cleanup is its own card"
**Idea:** —
**Wave:** 1
**Depends on:** — (the cleanup this card was opened for has already been done)
**Touches:** src/nonogram/admin/app.py (upload route reports a refusal and skips that picture), src/nonogram/admin/batch_generator.py (counts a refusal, keeps the batch going), src/nonogram/admin/puzzle_review.py (the guard, the audit, and MockGenerator rewritten to produce real puzzles), src/nonogram/cli.py (its exit-code group), src/nonogram/errors.py (NotUniquelySolvable), tests/test_admin_uniqueness_boundary.py (new — AC-A..AC-E), tests/test_batch_generation_e2e.py (tier assertion through tier_of_record; score range 0..100), tests/test_cli.py (the new error in the exit-code table), tests/test_puzzle_preview.py (same), tests/test_puzzle_review.py (fixture grid was the ambiguous diagonal), tests/test_wave3_e2e.py (same fixture)
**Review score:** 8.0 (cycle 1) -> 8.5 (cycle 2), all gating findings fixed
**Started:** 2026-09-13T15:20Z
**Closed:** 2026-09-13
**Actual:** —
**Merge commit:** b40e6b1
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
  TestStorageBoundary_AsksTheSolverNotTheCaller)
  *Was* `TestQuarantine_ReverifiesRatherThanTrustingTheReport` — a leftover
  from the card's original quarantine framing, naming a test that was never
  written and no longer matches any AC. A dead check ref reads as a live check
  and is worse than none.
- ADR-0011 — every solve is deadline-bounded (check: review-lens)
- CON-015 / CON-016 — the admin is reachable from this machine only (check:
  TestAdminPanel_BindsLoopbackOnlyByDefault,
  TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine)
  *Was* `NFR-003 / CON-009 ... (check: existing admin binding tests)`. CON-009
  is COMP-008's rule and there were no admin binding tests — the same false
  claim CARD-077 carried, found by its review (F-003) and fixed by CARD-081,
  which added the constraints and the tests this line can now honestly cite.
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

### What the guard found when it was switched on (2026-09-13)

The guard itself was small. What it exposed was not.

**29 existing tests broke, and every one of them for the right reason.** They
were storing grids that are not puzzles. The single root cause was
`MockGenerator` — which lives in **`src/nonogram/admin/puzzle_review.py`**, not
in the test tree — producing:

- a random 50%-density grid, which is almost never uniquely solvable (measured
  over 20 draws per cell: 0/20 unique at density 0.2 and 0.35, 2-12/20 at 0.5,
  17-18/20 at 0.65, for sizes 10-20);
- `clues_rows`/`clues_cols` of random integers **bearing no relation to the
  grid** they shipped beside;
- a random `difficulty_score` and a random tier — a "Hard" on a score of 17 was
  an ordinary output.

So the suite's picture of a stored puzzle was a non-puzzle carrying invented
clues and an invented grade. That is the same defect as
`image_to_puzzle.create_puzzle_from_image`, the function that wrote the twenty
rows deleted on 2026-09-14 — **still shipping in `src/` after that one was
deleted**, which is precisely the "one refactor away" this card was opened
about. The card's own premise ("its two live callers do go through
orchestrator.generate, so today's writes are sound") was therefore not quite
true: a third caller was already there, and it was the one the tests used.

Rewritten to ask rather than invent: clues from `clues.compute_clues`, grid
resampled until the solver certifies it, grade from that same solve through the
real scorer and classifier. Density 0.65, chosen off the measurement above, so
the resample loop almost always succeeds on its first or second draw — 10
puzzles in 18ms.

**The residue after that fix was small and also real.** Two literal fixtures
used `[[True,False],[False,True]]`, the diagonal 2x2, which has two solutions;
exactly 2 of the 16 possible 2x2 grids are ambiguous and they are the two
diagonals, so each was a one-cell change. Two more tests asserted
`difficulty_tier in ['Easy','Medium','Hard']` — a hardcoded label list that
assumed a spelling the real classifier does not emit (it writes the enum value)
and predated ADR-0025's fourth tier, so a Guess puzzle would have failed them
too. Both now go through `tier_of_record`, and their score bounds move from
`1..100` to ADR-0029's actual `0..100`.

**The guard needed a shape check, for the reason `regrade._as_grid` has one.**
`compute_clues` will happily encode things that are not grids, and the result
then *solves*: `[]` encodes to two empty clue sets, `[[]]` to `((0,),)`, and the
string `"not a grid"` to ten rows of one filled cell — a 10x1 grid that is
uniquely solvable, so a guard that only asked the solver would have stored the
string. Strict about cell type here, where `regrade._as_grid` deliberately
coerces: that one reads rows an older version of this system already wrote,
this one is a write boundary where a non-boolean cell is a caller's bug.

**Callers.** The batch generator logs at error level and counts a refusal as
`refused_count` rather than as a stored puzzle, and keeps going — one bad
candidate is no reason to lose the batch. The upload route reports it in the
results list and skips that picture. Both treat it as a bug rather than a data
condition, because every candidate they offer came through
`orchestrator.generate`, which enforces INV-002.

**Cost.** One solve per stored row, which is the same solve the pipeline
already did — measured at ~14ms per row against a batch that spends seconds per
puzzle generating. No bypass flag was added and none is wanted: a flag would
move the trust back to the caller, which is the arrangement that produced the
twenty rows.

**AC-C is structural, not just tested.** ``_refuse_unless_uniquely_solvable``
takes ``(self, grid)`` — it never receives ``clues_rows``, ``clues_cols``,
``difficulty_tier`` or any other thing the caller says about the grid, so
"trusts the caller" is not a state this code can be mutated into one line at a
time. The tests cover the behaviour (a caller supplying another grid's clues
and a full set of plausible grades is still refused); the signature is what
makes the behaviour unavoidable.

**Mutation check, seven mutants.** Six killed: guard removed, ambiguity
accepted, timeout treated as proof, shape check removed, audit silenced, and
``MockGenerator``'s resample loop removed. One was a badly written no-op of my
own and one — the resample loop — **initially survived**: at density 0.65 a
first draw is unique about nine times in ten, so a seeded batch of eight can be
all-first-draw-unique and the loop can be deleted with the suite still green.
The test that was supposed to pin it was passing on seed luck. Replaced with two
that force the solver to refuse the first draws and assert the generator drew
again, and that an exhausted ``MAX_DRAWS`` raises rather than returning the last
grid.

### Review cycle 1 fixes (74cc3ab)

Three Important findings, one root cause between the first two: **one guard
was made to answer two different questions**, and its write-path strictness is
wrong for the read path.

| finding | what was wrong | what it is now |
|---|---|---|
| F-001 | `audit_uniqueness` ran the write guard, which refuses a cell that is not a `bool`. A row stored as `[[1,1],[0,1]]` is a uniquely solvable Easy puzzle and was reported as a failure. | Reads through `_as_readable_grid`: shape checked exactly as strictly, cell type coerced. |
| F-002 | `deadline_seconds` was accepted and ignored — the one solve it reached hardcoded `GENERATION_BUDGET_SECONDS`. | Threaded into the solve and into the timeout reason. The write boundary keeps ADR-0011's bound as its own default. |
| F-003 | `refused_count` was incremented and never read, under a comment saying the count was what told the owner. | Carried onto the batch record as `error_message`, which `batch_status.html` already renders. No migration; the batch is not marked failed. |

F-004 was documented rather than chased, as its suggestion asked: every
`MockGenerator` puzzle is Easy *structurally* — density does not move it — so a
test that needs another tier must pin a grid the way `GUESS_GRID` is pinned.

**Why `_as_readable_grid` is a reimplementation and not an import.**
`regrade._as_grid` is the same rule, and both modules live in `admin/`, so the
import would be legal. It is duplicated anyway because the package's answer to
shared logic is a native copy cross-checked from the test tree
(`solver/propagate.py`'s `mask_runs` is the precedent) — here over a seeded
309-case corpus of the shapes and cell types a JSON column can actually hold,
with the corpus asserted to contain at least 50 readable and 50 unreadable
cases so the agreement cannot be vacuous.

**Not fixed, deliberately.** F-005 (the audit materialises the whole table) —
same shape and same scale as CARD-077's F-010, accepted for the same reason.
F-006 (item 4 asked for an audit *action*; a method was delivered) is an owner
question: either a read-only `GET /audit` beside `/regrade`, or amend item 4 to
say the capability is the deliverable and a screen is a later card.

**Verification.** Seven mutants, seven killed — the read path's coercion and
its rectangularity check, the budget in both the deadline and the message, and
the refusal note in the legacy branch, the DB branch, and its silence on a
clean batch. Suite unchanged at the known 14 pre-existing failures;
`test_batch_history::test_batch_list_sorted_by_date_newest_first` is the
standing unseeded `GenerationAbandoned` flake (3/3 green standalone), not this
change.

### Review cycle 2 fixes (b70a050)

Cycle 2 ran the mutation certification cycle 1 had deferred, with **eight
mutants deliberately different from the ones the cycle-1 fixes were written
against**. Four survived. Two were equivalent mutants; two were real holes, and
both are now closed.

| finding | what was wrong | what it is now |
|---|---|---|
| F-008 | The objection-as-string refactor dropped `raise ... from exc`. Measured: `__cause__` **and** `__context__` both `None` on the timeout path — and that is the log `batch_generator` writes with `exc_info=True`, the one this card names as where the per-candidate detail lives. | `_why_this_is_not_a_puzzle` returns `(reason, cause)`. The write path re-attaches it, the audit drops it, and a *verdict* still carries no cause so a refusal that is an answer does not read as a malfunction. |
| F-007 | The cross-check that justifies reimplementing `regrade._as_grid` could not generate a non-list row — every corpus row was a list comprehension, so **0 of 300** cases reached `isinstance(line, list)` and deleting that check left the suite green. | Non-list rows at *matching width* (the only shape that gets past the width check to reach the type check), generated and hand-written, plus a test asserting they are there. |
| F-011 | `_refuse_unless_uniquely_solvable` had a `deadline_seconds` parameter with no caller, contradicting the docstring and test that say ADR-0011's bound here is not a caller's choice. | Removed. The audit keeps its budget, because raising it is how an operator asks a deeper question; the write path does not, because a write that needed longer than the generation budget to be proven was not proven. |
| F-013 | `assert job.status is not BatchStatus.ERROR` against a method that never assigns status — an assertion that could not fail. | Drives `create_batch`, where the decision actually lives, and pins that the COMPLETE update does not clear the refusal note. |

F-012 and F-015 came free in the same lines: the `compute_clues` branch now
carries the `# pragma: no cover` its twin at `regrade.py:304` already had, and
the zero-solutions arm carries a note that it is unreachable while clues are
derived from a grid (120 random derived clue sets: 97 unique, 23 ambiguous,
none unsolvable).

**Still open, by choice.** F-009 (the audit can report a row twice if the
`continue` is lost, and the covering assertion is a `dict`, which cannot see
duplicate ids), F-010 (four shape malformations collapsed into one reason
string), F-014 (the coercion in `_as_readable_grid` is inert — `compute_clues`
already reads truthiness, so the shape screening is the load-bearing half),
plus cycle 1's F-005 and F-006.

**The process note worth keeping.** Three of cycle 2's five test findings —
F-007, F-009, F-013 — share one cause: the tests and the mutants that checked
them were written by the same author in the same sitting, so the mutants mostly
confirmed what that author already believed. The four survivors only appeared
because the review picked deliberately different ones. Mutants chosen by the
test's author certify less than they look like they do.
