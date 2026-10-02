# CARD-154: Print setup saves the plan and the trim together, and refuses "nan"

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-136 handover (2026-09-23), two backlog entries; code re-read on main beaecdd, 2026-10-02
**Idea:** —
**Wave:** 29
**Depends on:** —
**Touches:** src/nonogram/admin/print_specs.py, src/nonogram/admin/book_manager.py, src/nonogram/admin/app.py, tests/test_print_specs.py (new), tests/test_book_plan_storage.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Print setup writes a book's distribution plan and its trim size as two separate
DB transactions: `BookManager.save_plan` (`book_manager.py:728`, commits at
~:773) and then `set_print_spec` (:776). If the second write fails, the first one
has already committed.

There is a real input that makes this happen:
`PrintSpecValidator.validate_trim_size` (`print_specs.py:138`) checks the trim
with `<`/`>` comparisons only. `float("nan")` fails every comparison, so the
string `"nan"` passes validation, `create_spec` builds a spec, `save_plan`
commits, and only then does `set_print_spec`'s `math.isfinite` guard (:849)
raise. The book ends up with the new plan and the old trim. The same goes for
`"inf"`.

## What to do

1. Refuse a non-finite trim in `validate_trim_size`, so it never reaches storage.
   Keep `set_print_spec`'s guard as defence in depth.
2. Write the plan and the trim in **one** session in DB mode, so either both
   are stored or neither is. In memory-only mode, keep the same all-or-nothing
   behaviour.
3. Check the margin validators for the same NaN gap while you're there, and
   close it if it exists.

## Acceptance criteria

- **AC-1:** `validate_trim_size` refuses `"nan"`, `"inf"` and `"-inf"` for
  either dimension, with the same message shape as other invalid input.
  *test: TestTrimValidation_RefusesNonFiniteValues*
- **AC-2:** If writing the trim fails after the plan has been accepted, the stored
  plan is unchanged (DB mode).
  *test: TestPrintSetup_PlanAndTrimCommitTogether*
- **AC-3:** Submitting `"nan"` as the width on Print setup re-renders the form with
  the refusal, and neither the plan nor the trim changes.
  *test: TestPrintSetup_NanWidthChangesNothing*

## Guardrails

- G-1: Don't change any valid trim, margin or plan behaviour. Existing Print setup
  tests stay green without edits, unless they asserted the two-transaction shape.
- G-2: No schema change, no migration.
- G-3: The regression tests must run against a database (use
  `sqlite_session_scope`, since DB-mode tests skip silently without
  `nonogram_test`). Don't make them depend on the owner's Postgres.

## Architecture context

- **FR:** FR-030, FR-031 (print setup, as CARD-136); CON-018 (margin defaults)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] CARD-136's handover listed the NaN edge and the two-transaction writer
  as separate items. They're one defect: NaN is the input that makes the split
  write visible. Cut on 2026-10-02.
- [Related, not in scope] memory-only `get_book` returns the live `Book`, so a
  caller can write an invalid trim past validation (CARD-136, owner-accepted).
  That stays on the backlog.
