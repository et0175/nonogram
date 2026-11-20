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
