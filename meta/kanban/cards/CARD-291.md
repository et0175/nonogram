# CARD-291: Approval refuses a puzzle whose solve needed guessing — the human-solvability gate

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/291-approval-guess-gate
**Worktree:** — (removed at merge)
**Source:** owner session 2026-10-24 (the Christmas-ornament report); memory `guess-puzzles-in-book-c1`
**Idea:** —
**Wave:** 65 <!-- assigned 2026-10-28. HARD contention: CARD-291 declares src/nonogram/admin/app.py, which meta/kanban/config.yml names as a conflict HOTSPOT (CARD-131/132/139/140/142) precisely so it serializes intentionally rather than by arithmetic accident -- and CARD-305 at wave 67 declares app.py too (measured intersection: exactly that path). They must not run concurrently; wave 65 satisfies that with room. CARD-298 (w65) intersects CARD-291 EMPTY. If only ONE of 291/301 can have a slot, this is the one to take: CARD-301 is a verification hole, while CARD-291 prevents a defect that ALREADY REACHED A BOOK -- seven guess-requiring puzzles were pulled from book c1 and production was regraded across 311 rows. Adjacent waves make the 64/65 ordering nearly free, so both are scheduled; reversing them is defensible if the owner weights that owner-facing risk above cost. -->
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py, tests/test_approval_guess_gate.py, tests/test_puzzle_review.py, tests/test_bulk_operations.py <!-- AMENDED 2026-10-29 after review cycle 1 (F-003). Growth is FULLY JUSTIFIED and measured, but as written the line would mis-scope the next reviewer and the next concurrency check -- and `app.py` is a declared HOTSPOT. ADDED, both forced: `src/nonogram/admin/static/puzzle_edit.js` (+3) and `tests/test_puzzle_editor_ui.py` (+16), because the edit route's refusal vocabulary is a default-deny seam held as an EQUALITY on both sides -- `TestPuzzleEditor_Guardrails::test_the_refusal_vocabulary_is_load_bearing_on_both_sides` reds the moment the route emits a `reason` absent from `app.py`'s `EDIT_REFUSAL_REASONS` or the client's `REFUSALS_THAT_NEVER_WRITE`. Measured both ways by the reviewer: changing the token on EITHER side reds it (:985 app side, :989 client side). So CARD ITEM 5 CANNOT BE IMPLEMENTED INSIDE THE DECLARED TOUCHES. Also added `meta/architecture/decisions/adr/0032-admin-storage-guarantees.md` (the R3 flip the card owes). KEPT, and recorded rather than silently dropped: `tests/test_puzzle_review.py` and `tests/test_bulk_operations.py` were declared but needed NO EDIT -- their fixtures approve 2x2 and 10x10 solid grids, which pass the gate, and `BulkOutcome`'s new fields are appended. G-4 holds with ZERO fixture edits, verified: `git diff -- tests/` removes not one line. -->
**Review score:** 9.0 (cycle 1 of 3, CERTIFIED, no gating findings)
**Started:** 2026-10-29
**Closed:** 2026-10-29
**Actual:** 1d (estimate 1d)
**Merge commit:** 70f8e07e
**Blocked by:** — (was: the architect delta — resolved 2026-10-24 the same day: DEC-047 recorded resolved, ADR-0032 revised with R3, FR-046/AC-393..396/EC-051/US-029 minted, trace + CAP-004 rows added, validators 0 errors)

## [Premise RE-MEASURED at dispatch — 2026-10-29, orchestrator] the remediation already happened; the GATE has not

**The "Why this card exists" section below is accurate as history and stale as a
description of production.** Read it that way. Measured from the repo rather than
from the card:

**What is already done, and verifiable here.** All three remediation commits
exist on `main`: `61de1a04` (ADR-0032/R3 + FR-046 and the stock decision),
`ccac87e5` (**ADR-0029/R6** — a branching solve scores the ceiling, in code and
docs), `504384eb` (the pre-regrade snapshot of 311 production rows). ADR-0029
records R6 in its own revision history. Per the owner session of 2026-10-24: all
**7 puzzles were removed from book c1 (164 → 157) and rejected**, and production
was regraded across **311 rows** — 0 skipped, the only tier moves being those 7
to hard/100, 24 other rows drifting ±1 point, and **no new guess rows**.

**So the sentence "six are approved and all six are in book c1" is no longer
true of production, and the card must not be implemented as though a live
contamination is waiting to be found.** The defect it describes *reached a book*
and was *removed from it*; that history is the card's justification, not its
current state.

**What is still open is exactly this card, and nothing else covers it.** The
approval doors are **ungated**: the scoring formula now refuses to under-grade a
branching puzzle, but nothing refuses to *approve* one. The grade is a number;
the gate is a door, and the door is what this card builds.

**One residual the implementation must not assume away.** The deployed Render
service runs **pre-R6 code** — deploys there are dashboard-managed and the repo's
`render.yaml` does not drive them — so a puzzle generated or edited on production
is still graded by the **old** formula until a redeploy. For anything created in
that window, this gate is the only defence, which is an argument for AC-395's
fail-closed behaviour being the load-bearing criterion rather than a corner case.
Do **not** connect to the production database as part of this card; the premise
above is established from the repo and the owner's recorded session.

### Its five check refs are HONEST planned refs — keep them that way

Measured: `AC-393`, `AC-394`, `AC-395`, `AC-396` and `EC-051` each name a full
node id under `tests/test_approval_guess_gate.py`, a file that **does not yet
exist**, and **none of the five resolves to anything** — neither a definition nor
a prose mention anywhere in `tests/`. That is the **correct** state for an
unstarted card and the opposite of the defect this board has been finding all
week: a ref that reads as mechanically checked while nothing backs it. This card
owes all five as **definitions**.

**So the AC/EC gate for this card has a specific bar:** each of the five must
resolve to a real collected node id by merge, verified with
`git grep -nE '(class|def)[[:space:]]+<name>'` and by `--collect-only`, **not** by
`git grep -lw` — which on this board has been satisfied by a docstring more than
once, and in one case by 110+ files none of which were code.

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

## [Review cycle 1 — 9.0 CERTIFIED, 2026-10-29]

`min_score: 8`, cycle 1 of 3. **No gating findings**; 4 minor, 3 informational.
Report synced to `meta/review/20261029T000000Z-CARD-291-cycle1.yml`.

Impact gate, derived in two passes (13 card symbols grepped over `tests/` → 27
modules, plus 4 added by hand for structural guards this change can break without
naming their symbols — `test_collected_names.py`, `test_cli.py`,
`test_admin_import_consistency.py`, `test_admin_regrade.py`): **32 files, 1377
passed, 0 failed, 4 skipped, 79.6 s.** All four skips are
`tests/conftest.py:207` (`db_required`, no `DATABASE_URL`) in
`test_puzzle_edit_routes.py::TestPuzzleEditRoutes_OverTheRealDatabase`, **and the
same four skip on `main`** — no skip count moved, and **0 skips in this card's own
file**.

### F-001 was TAKEN as a fix round, not deferred — commit `2eb93c2a`

**A ref that resolves to a SKIPPED function is not a checked one.** Measured: with
`@pytest.mark.skip` above any of the five criteria, the file reported *"36 passed,
1 skipped"* and `test_the_registrys_check_refs_for_this_card_all_resolve` stayed
**green**. Resolving a ref to a module-level callable proves the function *exists*;
it does not prove the criterion *runs* — the same defect as a dead ref, one level
in, in the one card written to stop that defect reproducing.

Fixed by `_silenced`, kept out of the resolve test precisely so its control can
drive it over a **synthetic namespace**: at HEAD no function here carries a skip
mark, so asserting over the real tree would pass whatever the helper did, `return
[]` included. Both directions proved to bite by the orchestrator:
`@pytest.mark.skip` on a criterion reds the resolve test at **:2066**; `_silenced`
short-circuited to `return []` reds the control at **:2128**. The control also pins
that `skipif` counts, that a live function is **not** claimed, and that a ref
naming nothing stays the resolve test's `missing` case so the two assertions cannot
stand in for each other. File 37 → **38 passed, 0 skipped**; node ids **+38 / −0**,
all in this file.

The general form is **CARD-307's**: it writes one resolve-guard per module, and
each must carry this skip-mark requirement or it will certify refs that never run.

### F-002, recorded as a declared residual — the approve route pays the verdict twice

Counted on `puzzle_review.solve` through a real `test_client()`: believed list →
**0** solves (200); **unbelieved list → 2** (200); refusal → 1 (409); service path
→ 1. The route asks `approvability_of` and then `approve_puzzle` re-asks
`_approvability`. **The card's cost note is correct for the normal population** —
generation and the edit flow both write a believable list, so the common case is 0
solves — and the doubling reaches only legacy or invented-name rows. Bulk is
unaffected (1 per row). What is true and worth saying: `test_the_happy_path_does_not_enter_the_solver`
drives only the **service**, so the *route's* cost is unmeasured. Not fixed here;
it is a cost, not a defect, and the fix is a route-level memo whose own control
would be new work.

### Two corrections about WHICH test does the work — neither a weakness

Both reproduced by the orchestrator:

1. **`test_no_real_door_could_be_excused_by_listing_it` never reads
   `APPROVES_NOTHING`** — the name appears only inside its failure-message string.
   It asserts a standing property of the five doors (`_cannot_approve` non-empty).
   Moving a real door onto the exemption list is caught by
   **`test_every_exemption_is_still_unable_to_approve`** plus the size pin. The
   protection is real and bites; the test whose name claims it is not the one doing
   it. Worth renaming or re-documenting, since a reader will reach for the wrong
   one.
2. **Parametrizing a criterion would NOT kill its ref.** pytest matches node-id
   *prefixes*, so a parametrized `test_unknown_verdict_fails_closed` still collects
   under its bare node id (measured: `[1]`, `[2]`, 2 collected). The orchestrator's
   dispatch brief worried about this; the real hole was the skip mark.

### The `status: partial` warning is NOT this card's to clear, now measured

The round said so and the review measured it: `[WARN] FR-046 requirement has no
tests yet (status: partial)` fires on `trace.yml`'s `status: partial` **alone** —
`forge_1`'s `validators/trace.py:71-73` never reads the entry's `tests:` list,
which for FR-046 already holds all five node ids. `requirements.yml` has **0**
occurrences of `status: partial` and FR-046 has no `status` key there at all.
Board-wide: **43 of 75** trace rows are `partial`, 40 with no tests; the three that
list tests are NFR-001 (1), **FR-045 (15)** and FR-046 (5). **FR-045 is the
precedent this card cites and its row is still `partial` with 15 live tests.** So
flipping FR-046 alone would be a one-card board-wide convention change. **The
card's claim is satisfied for 5 of the 6 FR-046 warnings**; the convention flip is
filed separately, not smuggled in here.

### Predicate name — justified, and amended so nobody "restores" it (F-004)

Card item 2 asks for `needs_guessing(puzzle_id)`; it shipped as
`approvability_of(puzzle_id) -> Approvability | None`. **Justified, not drift**, on
three grounds, two of them measured: AC-395 needs a third outcome carrying its own
message, which a bool cannot; one enum read is **one** `strategies_for` call where
two booleans would be **two** budgeted re-solves (`_approvability` measured at
exactly 1 solve, and F-002 shows what one extra call already costs); and
`GridNotApprovable.verdict` is the same member, so the edit refusal and the
approval refusal cannot drift. The card's prose is left as the request it was, with
this note as the answer.

### AC/EC/G verification gate (`done` step 2a) — run by node id

**AC-393, AC-394, AC-395, AC-396, EC-051: 5 passed, 0 skipped, 0 failed.**
- **G-1** holds: the only `strategies_used` occurrence in the added `src/` lines is
  a subscript **read** passed as an argument; no assignment to grade, score, tier
  or `strategies_used`; no write of `PuzzleStatus.DRAFT`/`REJECTED`, so nothing
  demotes. The reviewer additionally measured it as a **byte-for-byte row no-op** —
  deep-copied the row, drove a refused approval down both verdict paths, diffed
  every key: delta **NONE** on both.
- **G-2** holds: `difficulty.py`, `orchestrator.py`, `solver/**` untouched; 0
  occurrences of `score_difficulty`/`classify` in the `src/` diff.
- **G-3** holds by substance: **no import statement is added to `src/` at all**,
  `pyproject.toml` untouched. **Not** credited to
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`, which has zero definitions in
  this repo and reads alive only because ~223 tracked files spell the token.
- **G-4** holds with **zero** fixture edits: both named files unedited and green
  (37 passed), and `git diff -- tests/` removes not one line.
- **G-5** holds: node ids **+38 / −0**, no deleted `def`/`class` in `tests/`.

## [MERGED `70f8e07e` — 2026-10-29]

Fast-forward onto `main`, five commits. **Merge gate attempt 2 green:**

```
9695 passed, 27 skipped, 1 xfailed, 0 failed     1197.28s (19:57)
skips: 26 × DATABASE_URL unset + 1 × setrlimit   — the baseline exactly, both named
hang dumps: 0     real rival pytest: 0 at both ends     load 5.35 → 10.03
```

Collection reconciles exactly: 9695 + 27 + 1 = **9723**, against main's 9685 — the
**+38 / −0** measured on the branch, every one in this card's own file.

**Attempt 1 was RED and the defect was the orchestrator's**, which is the part of
this card worth keeping. The control written for F-001 used
`@pytest.mark.skipif(True, reason="probe")` on an inner function, and CARD-238's
`_conditional_silences` AST-walks **every guarded source** for a `skipif` and
reports it **whatever it is keyed on** — width its own docstring calls deliberate.
So the probe registered as a new host-state silence anywhere in the tree:
`test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones` red, with
`test_the_outcomes_are_identical_with_and_without_the_log` as the cascade (2
failed, 9693 passed, 27 skipped, 1 xfailed).

**The guard was right and stricter than the test, so the decorator went, not the
guard.** Adding the probe to `MEASURED_SILENCES_ELSEWHERE` would have asserted the
silence depends on the host, which it does not — and that list's own comment says
the baseline must be *"a record of what it reports, not of what a sentence here
wishes it reported"*. The marks are now attached by assigning `pytestmark`, the
way pytest itself stores a decorator's result; they are still real `Mark` objects,
so the control would still fail if `_silenced` read the wrong attribute. Verified
four ways: `_conditional_silences` reports `[]` for the file, both reddened tests
pass, the file is 38 passed / 0 skipped, and **both controls still bite**.

**Why no review round saw it:** the F-001 fix was written **after** cycle 1
certified, and the reviewer's impact scope never reached
`tests/test_suite_profile.py`. The merge gate was the only thing that ran that
guard against the change — the argument for re-running the impact set *extended by
the meta-guards* after a post-certification fix, rather than treating the earlier
score as evidence about the newer commit.

**Re-based twice and re-measured, not assumed.** The gate ran against base
`6761c899`; `main` then gained four kanban-only commits. Twelve files reference
`meta/kanban` or `meta/review`, so that delta was a real risk surface rather than
inert text: the branch was rebased onto `ccb612c9` and the nine **collected**
modules among those twelve run **939 passed, 1 xfailed, 0 failed, 0 skipped**.

### Post-merge, and it confirms CARD-308's mechanism arithmetically

Validator on `main` after the merge: **0 errors, 102 warnings**, and all five refs
resolve to real `def` lines (326 / 505 / 649 / 801 / 1548). No FR-046 dead-ref
warning remains.

```
honest pre-merge main   107    (106 observed + 1 falsely silenced by this card's own review YAML)
after the merge         102    = 107 − 5 refs repaired
observed drop           106 → 102 = −4
```

So the **depressed baseline would have under-reported this card's repair by one**.
That is the clean confirmation of the sync-erosion defect: the warning the YAML
silenced was AC-395's, one of this card's own five.

### A correction to review cycle 1's figures, measured off the file

Cycle 1 argued the `status: partial` warning is not this card's to clear, and **the
conclusion is right while its numbers are wrong**. It reported *"43 partial, 40
with no tests at all, and three that list tests — NFR-001 (1), FR-045 (15),
FR-046 (5)"*. Counted over all 75 links: **32 covered, 43 partial, and 42 of the
43 partial rows LIST tests** (only `CON-017` lists none), carrying **409** test
refs between them. The largest is **FR-044 with 85 tests, still partial**; FR-045
has **19**, not 15. The conclusion is stronger than cycle 1 made it: `status:
partial` carries almost no information about whether a requirement has tests.

**And the inverse direction is a finding nobody has raised: 9 of the 32 `covered`
rows list no tests at all** — rows whose status says checked and whose test list
is empty, while `validators/trace.py` gates all three of its checks on `status ==
"covered"`. Recorded on CARD-307.

`trace.yml`'s FR-046 row needed **no new test names** — all five were already
listed as planned refs and are now real definitions. Its notes are updated and the
status is **deliberately left `partial`**, because flipping one row would be a
board-wide convention change.
