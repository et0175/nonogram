# CARD-497: The Print setup refusal page shows the plan that was submitted, not the stored one

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/497-refusal-planned-row
**Worktree:** ../PythonProject4-card-497
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-012, WSJF 2.31 (unverified at the rescore).
**Idea:** IDEA-012
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_setup_print.html, tests/test_book_plan_storage.py, tests/test_book_setup_print*.py
**UI surface:** admin Print setup (step 2), the refusal re-render
**Review score:** —
**Started:** 2026-11-20T09:50Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-120 F-008: when Print setup refuses a submission (a split that does not sum to 100, an unreadable trim), the page is re-rendered, and its "Planned" row was read from the **stored** plan rather than the one the owner just submitted, so the summary disagrees with the form the owner is looking at. Unverified at the rescore: `setup_print` and the template's Planned row were located but which plan the refusal render passes was not traced.

## What to implement

1. Reproduce first, in a test, on main: submit a refused plan whose counts differ from the stored one; record what the Planned row shows.
2. If live: the refusal render's Planned row reflects the submitted plan (or says it was not saved), from the same values the form carries back (CARD-120's "carry the plan input back"). If already closed: one line in the notes, no code.

## Acceptance criteria

* **AC-1**: on a refused submission the Planned row shows the submitted plan's figures; control: main's route reds it. Or, if moot, the reproduction recorded in the notes.
* **AC-2**: a successful submission's page unchanged (compare its HTML before and after).
* **AC-3**: net test count at most +1 (extend an existing refusal test if one fits).

## Guardrails

* **G-1**: nothing is stored on a refused submission (the existing refusal tests stay green).

## Worktree notes

### 2026-11-20 implementer (CARD-497)

**Reproduction (on the branch base, 87a6c372): it was a real bug.** The stored plan was DEFAULT_PLAN (150 at 40/40/20, Planned 60 / 60 / 30). After a POST of 120 at 30/45/25 with an unreadable trim (`width=5`), the page showed the submitted figures in the fields, but the `<tfoot>` Planned row still read `60 / 60 / 30`. The submitted plan's own figures are 36 / 54 / 30. The same row read `60 / 60 / 30` after a refused split (30/45/35). Cause: `_plan_context` built `plan_tier_counts` from the stored plan even when it carried the submission back into the fields. Recorded in a scratch capture script (outside the repo) and in the two extended tests below, which are red against the base route.

**Change.**
- `setup_print` keeps the plan `_plan_from_form` parsed as `submitted_plan`, even when the plan is not stored. It keeps it before the "unchanged plan, so no edit" reset.
- `_plan_context` takes a new `submitted_plan` argument. If a refused submission carried the plan fields, the Planned row now comes from `submitted_plan.tier_counts`. If the plan itself was refused, the row is `None`.
- `book_setup_print.html` renders a `None` Planned row as one cell: "Not saved: correct the plan above". A plan with an invalid split has no planned figures to show.
- A form without the plan fields, and every GET, still reads the stored plan.

**AC-1.**
- `test_trim_refusal_carries_the_plan_input_back` now asserts that `_planned_row(html) == ["36", "54", "30"]`.
- `test_refused_split_keeps_the_typed_matrix` now asserts that the row is one "Not saved" cell.
- `_planned_row` is a new helper, not a test.
- Control 1 (app.py and the template restored to the base): all 4 parametrized cases red. The trim test fails with `assert ['60', '60', '30'] == ['36', '54', '30']`. The split test fails with `AssertionError: ['60', '60', '30']`.
- Control 2 (only `submitted_plan = new_plan` deleted): both cases of the trim test red, with `['Not saved: ...e plan above'] == ['36', '54', '30']`. The split test stays green, as expected, because its plan is refused either way.
- After both controls the tree was restored, and `git diff --stat` shows only the intended 3 files.

**AC-2.** The scratch capture rendered 4 pages on the base and on the fix, with book UUIDs normalised: the GET prefill page, the successful POST (302 body and Location), the page it redirects to, and the Print setup page reopened after the success. All 4 are byte-identical.

**G-1.** Nothing is stored on a refusal. Both extended tests still assert `get_plan(book_id) == DEFAULT_PLAN`, and the capture shows the refused book's stored plan still at 60 / 60 / 30.

**Gate (unarmed, `-rfs`).** I ran the touched file, `tests/test_book_plan_storage.py`, and the Print setup neighbours: test_book_setup_print_mobile, test_book_trim_persistence, test_book_player_domain, test_book_divider_pages_option, test_print_specs, test_book_pdf_ink_mode, test_book_workflow_steps, test_admin_import_consistency and test_book_proof_pages. Result: 813 passed, 0 failed, 0 skipped.

**Observed, not changed (cut bar).** On a refused render, the FR-034 "disagrees with the split" alert above the matrix is still built from the stored plan (`plan_disagrees`, `plan_column_totals`). It is the same family as this card, but outside its AC.

**AC-3.** Net collected count (`--collect-only -q -o addopts= tests/`) is 10708 before and 10708 after, so +0. I extended 2 existing tests and added no new test.
