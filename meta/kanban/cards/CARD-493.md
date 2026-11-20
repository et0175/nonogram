# CARD-493: Three test minors: a vacuous trim assertion, a bare-token echo row, and two claims a proof test makes

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/493-test-minors
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-068 WSJF 3.08 (unverified at the rescore), IDEA-093 WSJF 3.08, IDEA-097 WSJF 3.08 (partly).
**Idea:** IDEA-068, IDEA-093, IDEA-097
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_plan_storage.py, tests/test_db_url_driver.py, tests/test_book_proof_pages.py, src/nonogram/admin/book_proof.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-068 (CARD-120 F-009).** A trim assertion in tests/test_book_plan_storage.py is vacuous in DB mode. Which one was never established at the rescore; find it (run the trim tests armed and unarmed, plant a wrong trim, see which stays green).
2. **IDEA-093 (CARD-176 F-001/F-002).** tests/test_db_url_driver.py has echo rows for `postgresql:hunter2://` and `hunter2@h://x/db` but none pins the documented echo of a bare leading token (`hunter2://`); AC-1's echo check accepts any corpus scheme rather than the one drawn for that case.
3. **IDEA-097 (CARD-172 F-001/F-002).** tests/test_book_proof_pages.py credits the 1493/2048 cap-height ratio to "OS/2 sCapHeight" in the bundled face; check the font's tables (fontTools is not a dependency: read the bytes, or say so); `book_proof._annotate`'s docstring claims square page 2 keeps its foot note but only 11×8.5 is asserted.

## What to implement

Re-verify each first; drop any already closed with one line.

1. The vacuous assertion asserts something a wrong trim breaks, in DB mode.
2. One row (extend the existing parametrisation, not a new test) pins the bare-token echo; the AC-1 check compares against the scheme drawn for that case.
3. The comment names the ratio's real source; the docstring's square-page claim is either asserted (extend the existing 11×8.5 case) or the docstring is cut back to what is asserted.

## Acceptance criteria

* **AC-1**: item 1's assertion reds under a planted wrong trim, ARMED (DB mode); report the armed and unarmed skip counts with `-rfs`.
* **AC-2**: item 2's row reds when the echo of a bare token changes.
* **AC-3**: net test count 0 (parametrised rows count; report the collected count before and after).

## Guardrails

* **G-1**: no production code change except `_annotate`'s docstring.
* **G-2**: never connect to the production database; the armed run uses the worktree's own `_test` database.

## Worktree notes
