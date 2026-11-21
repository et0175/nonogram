# CARD-513: Two book-route minors: a no-puzzle book's download, and the plan tripwire logged twice

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/513-book-route-minors
**Worktree:** ../PythonProject4-card-513
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-052 (wave-30 goal check) and IDEA-043 (CARD-153 F-009/F-011), bundled: each alone is below `sizing.min_estimate`.
**Idea:** IDEA-052, IDEA-043
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/books.html or book_detail.html, src/nonogram/admin/app.py, tests of the books list and Finalise
**UI surface:** books list, book detail (interior download button)
**Review score:** —
**Started:** 2026-11-21T05:47Z
**Blocked by:** —

## Why this card exists

1. **IDEA-052.** On a book with no puzzles, /books offers the interior download (it returns a 200 PDF), while /book/<id> disables the same button. The two pages disagree and no AC covers either. Decide by what the download produces: if a no-puzzle interior is a valid PDF a user might want, /book should offer it; if not, /books should not. Prefer the more conservative (disable on both) unless the code shows the empty PDF is deliberate; say which and why.
2. **IDEA-043.** A plan tripwire on GET Finalise is logged twice (the helper logs, then Flask logs the same error). Also, the G-1 "never laid out again" spy only sees layouts through `BookPDFGenerator`, which is the only layout path today per ADR-0036/R2; record that scope in the test's docstring instead of widening the spy, unless a second path exists.

## What to implement

Re-verify each against main first; drop anything already closed, with one line in the notes.

## Acceptance criteria

* **AC-1**: on a no-puzzle book the two pages agree about the interior download, and an existing books-list or book-detail test asserts it (control: main's template reds it).
* **AC-2**: the tripwire is logged once (control: main's double log reds a caplog count).
* **AC-3**: the spy's scope is stated truthfully in its docstring (or widened if a second layout path exists, found by `ast`).
* **AC-4**: net test count at most +1; report it.

## Guardrails

* **G-1**: run the database-backed selection armed (at the worktree's own `*_test` database) and unarmed, and report both with `-rfs`.
* **G-2**: never connect to the production database.

## Worktree notes
