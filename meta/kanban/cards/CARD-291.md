# CARD-291: Approval refuses a puzzle whose solve needed guessing — the human-solvability gate

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/291-approval-guess-gate
**Worktree:** —
**Source:** owner session 2026-10-24 (the Christmas-ornament report); memory `guess-puzzles-in-book-c1`
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, tests/test_approval_guess_gate.py, tests/test_puzzle_review.py, tests/test_bulk_operations.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (was: the architect delta — resolved 2026-10-24 the same day: DEC-047 recorded resolved, ADR-0032 revised with R3, FR-046/AC-393..396/EC-051/US-029 minted, trace + CAP-004 rows added, validators 0 errors)

## Why this card exists (measured, 2026-10-24)

Production holds **7 puzzles whose verifying solve branched** (`branch_nodes`
59–283) — 63–97 % of their cells are settled only by search, so no human can
finish them without stacked trial-and-error. All seven are graded **medium**
(scores 66–77), six are **approved and in book c1**, and the 15×15 the owner
played has **zero** cells derivable by line logic from the empty board. Unique
(CON-005 holds for every one) is not the same fact as humanly derivable, and
nothing between generation and a printed page currently asks the second
question. The grader cannot be the gate: CARD-098 retired the GUESS tier on
evidence that covered only random draws ("no random draw in the supported range
branches at all"), and the image pipeline — which produced all seven — is
exactly the source that branches. `score_difficulty` reads `rung_cells` and
never `branch_nodes`, and within the probe band the share metric *inverts* for
branching puzzles: the heavier the search, the fewer probe-settled cells, the
lower the score. Re-tuning score bands would re-scale every stored grade;
refusing at approval changes exactly the puzzles that should never ship.

`choose_givens` is not the remedy either — verified: it reveals **zero** cells
for these puzzles, because its contract is uniqueness, which they already have.

## What to implement

**The invariant:** a puzzle in status `approved` or `in_book` needs no
guessing — its verifying solve has `branch_nodes == 0`. Enforced at every door
into that state, never by demoting rows already behind it (see Out of scope).

1. **The verdict, and what defaults to DENY.** "Needs guessing" is read off
   `PuzzleReviewService.strategies_for(puzzle)` — the existing FR-029 answer:
   the stored solver-written list when there is one, else one re-solve under
   `GENERATION_BUDGET_SECONDS`. The gate's predicate is
   `STRATEGY_GUESS in strategies`. **`None` — an unreadable grid, a non-unique
   grid, or a solve that did not conclude — refuses approval** with its own
   message ("could not verify…", distinct from the guess refusal): an approval
   is a claim of publishability and an unverifiable claim fails closed, the
   same posture as INV-002. The shape rule (wave 46): the control for the
   DENY default is a puzzle whose verdict is *unknown*, not a fourth guess
   example.
2. **The per-puzzle chokepoint.** `_set_status` is where CARD-100 put the
   book protection — one implementation, one rule, one place to be wrong. The
   gate joins it there, firing **only on a transition to
   `PuzzleStatus.APPROVED`** (reject and restore stay ungated), in **both**
   modes of the dual-mode store (in-memory and `_session_factory`). The
   return contract grows the same way CARD-100's did: callers that must say
   *why* ask a predicate first (`needs_guessing(puzzle_id)` beside
   `in_a_book`), so `approve_puzzle` keeps returning bool.
3. **The route says why.** `POST /puzzle/<id>/approve` already distinguishes
   "in a book" (409) from "not found" (404); it gains the two new refusals
   with messages naming the fact ("needs guessing to solve — not approvable"
   / "solvability could not be verified"), through `_prefers_json` and flash
   alike.
4. **The bulk path is the same rule, not a sibling with the identical
   defect.** `set_batch_status(…, APPROVED)` does *not* go through
   `_set_status` — it writes `puzzle["status"]` in its own two loops. It
   holds back guess-needing (and unverifiable) puzzles the way it holds back
   in-book ones, and `BulkOutcome` grows a field so `_bulk_report` can say
   "N held back: need guessing" instead of absorbing them into a count.
5. **The edit door into the invariant.** A replacement grid stored through
   `POST /puzzle/<id>/edit` onto a puzzle whose status is `approved` or
   `in_book` is refused when its (already computed — the verify phase grades
   it) strategies include `guess`, alongside the existing refusals. A draft
   puzzle may store a branching grid; it just cannot be approved carrying one.
6. **The writer enumeration (ADR-0039/R2).** The set of gate sites is derived,
   not hand-listed: a test walks `src/nonogram/**` with `ast` and collects
   every assignment/write of `PuzzleStatus.APPROVED` (both the enum member and
   its `.value`); each collected site must be one of the gated doors, and a
   new writer fails the suite until it is. The controls are per ADR-0039/R1:
   each door caught WITH the gate present (a branching fixture refused),
   missed WITHOUT it (the gate deleted → the same fixture approves), measured
   per assertion.

**Cost note for the implementer:** the gate re-solves only when the stored
`strategies_used` is not solver-written (`_is_strategies_list`), so approvals
of normally-generated puzzles stay O(1) reads — generation and the edit flow
both store the list. Verify that assumption at the edit seam rather than
restating it: the two-phase edit (CARD-245) must leave the stored list in step
with the stored grid, or the gate reads a stale verdict. Gate tests use
`sqlite_session_scope` for the DB mode — `db_required` tests skip green
without `nonogram_test` and a skipped gate test is an ungated door.

## The architect delta (landed 2026-10-24, same day)

ADR-0032/R3, FR-046 (AC-393..396), EC-051 and US-029 exist — read the rule out
of **ADR-0032 itself** (`meta/architecture/decisions/adr/0032-admin-storage-guarantees.md`,
Rules block), not out of this card's paraphrase; DEC-047 records the rejected
alternatives. requirements.yml, trace.yml and capabilities.yml carry the rows;
validators ran 0 errors (FR-046's planned-test warnings are the FR-045
precedent and are this card's job to clear).

**AMENDED 2026-10-25 — ADR-0032/R3's check is now a `review-lens`, and this card
owes the flip.** R3 was written naming
`tests/test_approval_guess_gate.py::test_every_approved_writer_passes_the_gate`
as a `kind: test` ref. That file does not exist — it is the test **this card
writes** — and a `kind: test` ref to a nonexistent test is read as mechanically
checked by `system_rules.py` and `forge:review` Step 8h. The consequence was
pointed at this card specifically: **the review of the card writing the guard
would have been told the guard already exists**, so a gap in it would have drawn
no flag. R3 is therefore held as a lens until this card lands, with the planned
name in a comment beside it.

**What this card must do about it:** write that test under exactly that path and
node id, then flip R3's check back to
`{kind: test, ref: tests/test_approval_guess_gate.py::test_every_approved_writer_passes_the_gate}`
in the ADR, in the same change. The flip is part of the card, not a follow-up —
an ADR rule whose check is a lens after its delivery card merged is a rule that
quietly stopped being verified. Repaired alongside the same defect in ADR-0042's
four planned refs (commit `c12c33ce`); CON-020's own check comment carries the
precedent for the flip's shape.

## Acceptance criteria

FR-046 (to be minted by the delta above).

- AC-393: Given a draft puzzle whose verifying solve branched, when the owner
  approves it (route or service, either store mode), then the approval is
  refused with a message naming that the puzzle needs guessing and the status
  stays draft (test: tests/test_approval_guess_gate.py::
  test_approve_refuses_a_branching_puzzle).
- AC-394: Given a batch holding branching and non-branching puzzles, when the
  batch is approved, then the non-branching ones approve, the branching ones
  keep their status, and the report states how many were held back and why
  (test: tests/test_approval_guess_gate.py::
  test_batch_approve_holds_back_branching_puzzles).
- AC-395: Given a puzzle whose strategies cannot be determined (unreadable
  grid, non-unique grid, or a solve that does not conclude in budget), when
  approval is attempted, then it is refused with the could-not-verify message
  — never approved (test: tests/test_approval_guess_gate.py::
  test_unknown_verdict_fails_closed).
- AC-396: Given an approved or in-book puzzle, when an edit whose verified
  replacement grid needs guessing is stored, then the store refuses and the
  stored grid is unchanged; the same replacement stores onto a draft (test:
  tests/test_approval_guess_gate.py::
  test_edit_refuses_a_branching_grid_behind_the_approved_door).

## Engineering constraints

- EC-051 (ADR-0032/R3, ADR-0039/R1-R2): every write of
  `PuzzleStatus.APPROVED` in `src/nonogram/**` passes the gate — the writer
  set is derived by AST walk, default-DENY on an unlisted writer, and each
  door's control reds with the gate deleted at that door.
  test: tests/test_approval_guess_gate.py::
  test_every_approved_writer_passes_the_gate

## Guardrails

- G-1: No stored grade, score, tier, or `strategies_used` row changes — the
  gate reads, never writes verdicts (the regrade module stays untouched).
  Nothing demotes an existing approved/in-book puzzle.
- G-2: `score_difficulty`, `classify` and `src/nonogram/difficulty.py` are
  untouched — the gate is curation-side by design (see Why), not a grader
  change. src/nonogram/solver/**, src/nonogram/orchestrator.py untouched.
- G-3: The runtime dependency baseline stays closed (ADR-0006/R1; the AST
  walk is stdlib `ast`).
- G-4: Existing refusal behavior is additive: CARD-100's in-book refusals and
  their tests (tests/test_puzzle_review.py, tests/test_bulk_operations.py)
  stay green, with fixture edits only where `BulkOutcome` grew.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0032/R1 — every puzzle stored through the admin panel proved uniquely
  solvable at the storage boundary. (check: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0039/R1 — a guard's claims need controls that can fail: caught WITH the
  mechanism, missed WITHOUT it. (check: per-door, named in EC-051)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can
  enumerate, not hand-written. (check: test_every_approved_writer_passes_the_gate)
- ADR-0029/R2 — one verifying solve per grade; the gate reuses its stored
  answer rather than entering the solver a second time on the happy path.
- CON-005 — uniqueness never false-positive. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-002 — a puzzle is only marked ready for export after its uniqueness
  check confirmed exactly one solution; this card is the same posture one door
  earlier. (check: TestExport_RejectsUnverifiedPuzzle)
- INV-008/INV-012 — book membership changes are explicit and confirmed; the
  gate never edits membership.

## Out of scope, said rather than implied

- **The six approved guess-puzzles already in book c1** (Star s3, Snowflake
  s1, Holly s3, Santa, Candy c4, Fire f4): the owner decided 2026-10-24 —
  regrade every production row and REMOVE the guess-level puzzles (pull from
  c1, reject). Executed the same day as a one-time operation through the
  panel (snapshot in meta/ops/, per the regrade runbook); this card's gate is
  the standing rule that keeps the stock clean afterwards. Nothing here
  demotes anything automatically.
- **Regrade** keeps reporting `guess` without demoting anyone (G-1). A regrade
  that *discovers* guess on an approved puzzle is a report for the owner — a
  demotion policy, if wanted, is a separate decision.
- **The grader's inversion is CLOSED** — same day, by ADR-0029/R6 (owner
  follow-up decision, commit ccac87e5): a branching solve now scores the
  ceiling (100, tier hard) before any rung is read, with
  tests/test_difficulty.py::test_a_branching_solve_pins_the_ceiling_and_outranks_every_ladder_score
  as its control. The gate is still needed and unchanged in scope: *hard* is a
  publishable tier and "needs guessing" must **refuse**, not re-label — the
  score's job is to not lie, the gate's job is to not sell it. G-2 stands:
  this card does not touch difficulty.py further.

## Worktree notes

—
