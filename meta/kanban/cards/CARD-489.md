# CARD-489: Two book_manager leaks: the hand-edit mark survives a count change, and memory mode hands out the live Book

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/489-book-manager-leaks
**Worktree:** ../PythonProject4-card-489
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-011 WSJF 3.46, IDEA-014 WSJF 3.08; one card because both live in src/nonogram/admin/book_manager.py.
**Idea:** IDEA-011, IDEA-014
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_manager.py, tests/test_book_plan_storage.py, tests/test_book_manager*.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T00:32Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-011 (CARD-120 F-007).** `revise_plan` keeps a hand-edit mark on a plan cell. Typing a cell back to its prefill reads as handled (the 2026-11-18 triage), but when the puzzle count changes the edits are still judged against the OLD prefill, so a cell can stay "hand-edited" (or lose the mark) for the wrong reason.
2. **IDEA-014 (CARD-136, owner-accepted 2026-09-23).** In memory-only mode `BookManager.get_book` returns `self.books.get(book_id)`, the live `Book`; a caller can write an invalid trim past `set_print_spec`'s validation. DB mode already returns a fresh object.

## What to implement

Re-verify each against main first, in a test, before changing code; drop any already closed with one line in the notes.

1. A count change re-judges the hand-edit marks against the NEW prefill (a cell equal to the new prefill is not hand-edited; one that differs is).
2. Memory mode's `get_book` returns a copy, so mutating it changes nothing stored; writes still go through the manager's own setters.

## Acceptance criteria

* **AC-1**: a count change followed by a read gives marks consistent with the new prefill; control: the old comparison reds it.
* **AC-2**: mutating the object `get_book` returns (memory mode) leaves the stored book unchanged; control: return the live object, it reds. Every existing memory-mode caller that mutated the returned book on purpose is found (by `ast`/grep of call sites, listed in the notes) and moved to a setter, or the card stops and reports. (Amended 2026-11-20 by the orchestrator after the implementation: a TEST seed site that stores a value no setter accepts on purpose — an unreadable trim or ink mode, a raw puzzle order, a forced status — writes the memory store directly, `manager.books[book_id]`, as its DB branch writes the row; product callers still go through setters.)
* **AC-3**: net test count at most +2; report it.

## Guardrails

* **G-1**: DB mode's behaviour unchanged (its tests are `db_required`; run them armed at the worktree's own `_test` database and report the skip count with `-rfs`).
* **G-2**: no schema change.

## Worktree notes
