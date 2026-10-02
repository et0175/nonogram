# CARD-159: Book forms keep what you typed and say the right step

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-130 handover, CARD-136 handover (backlog); templates re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 30
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_setup_print.html, src/nonogram/admin/templates/book_create.html, src/nonogram/admin/app.py, tests/test_book_workflow_steps.py, tests/test_book_create.py (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Three form defects on the book workflow:

1. **"Step 1 of 4" next to a five-step stepper.**
   `book_setup_print.html:12` still says "Step 1 of 4". CARD-130's G-4 kept this
   file frozen while CARD-118 was in flight; CARD-118 has merged since. The prose
   guard in `tests/test_book_workflow_steps.py:1052` skips this step on purpose
   (`PROSE_CHECKED = (0, 2, 3, 4)`), and the comment beside it explains how to
   re-enable it.
2. **The inches option can't be used.** The width and height inputs carry fixed
   `min="10" max="30"` (and `48`) values in centimetres
   (`book_setup_print.html:46` and its siblings). With "Inches" selected, a real
   8.5 in trim fails the browser's own validation before it is submitted.
3. **`/book/create` throws away what you typed.** On error, the route flashes the
   message and re-renders `book_create.html` with no form values (`app.py:2438-2440`).
   Edit was fixed for this same defect in CARD-130; create was left frozen by that
   card's objective 3.

## What to do

1. Fix the step text (or derive it from the stepper's own step list, so it
   can't drift again) and add step 1 to `PROSE_CHECKED`.
2. Make the inputs' `min`/`max` follow the selected unit: switch them when the
   unit radio changes, or drop the browser bounds and rely on the server's
   validation, which already reports out-of-range trims. Either way, an inches
   value inside KDP's bounds must submit.
3. Re-render `/book/create`'s refusal with the submitted values filled in, the
   same way edit does after CARD-130.

## Acceptance criteria

- **AC-1:** Print setup's prose names the step the stepper marks as current, and
  the prose guard checks every step.
  *test: the prose guard in tests/test_book_workflow_steps.py with step 1 restored*
- **AC-2:** With the inches unit chosen, an 8.5 x 11 in trim is accepted by the
  rendered form's bounds and by the server.
  *test: TestPrintSetup_InchesTrimIsReachable*
- **AC-3:** A refused `/book/create` shows the form again with the submitted
  title and fields filled in.
  *test: TestBookCreate_RefusalKeepsTypedInput*

## Guardrails

- G-1: Server-side trim validation is unchanged (KDP bounds stay where they are).
- G-2: Use existing tokens and components only.
- G-3: The owner checks the rendered forms in both units (see
  owner-validates-visually). Put the renders in
  `~/Documents/nonogram-reviews/CARD-159/`.

## Architecture context

- **FR:** FR-038 (book workflow steps, as CARD-130), FR-030 and FR-031 (print setup, as CARD-136)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Form-side leftovers from CARD-130 and CARD-136. Cut on 2026-10-02.
