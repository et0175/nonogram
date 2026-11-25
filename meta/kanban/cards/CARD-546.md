# CARD-546: The book PDF writer loses its dead defaults and guards (CARD-147 leftovers)

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/546-book-writer-dead-code
**Worktree:** ../PythonProject4-card-546
**Source:** roadmap wave 21, cut 2026-11-25 on the owner's "pick the next no-decision wave from the backlog". Backlog IDEA-019 (CARD-147 F-002/F-003/F-005).
**Idea:** IDEA-019
**Wave:** 100
**Created wave:** 100
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py (`BookPDFGenerator._write_pdf`, `BookPDFGenerator._write_page` only), the existing tests that call `_write_pdf` / `_write_page` (tests/test_book_pdf.py, tests/test_book_pdf_memory.py, tests/test_book_puzzle_page_vector.py) only if a call there relies on a removed default
**UI surface:** —
**Review score:** —
**Started:** 2026-11-25T11:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-147's review left three dead pieces in the book PDF writer (F-002, F-003, F-005). The backlog triage (2026-11-18) asked that they be checked as still reachable before any work, because CARD-416 moved most pages to vector. Checked at the cut on 2026-11-25: `BookPDFGenerator._write_pdf` and `BookPDFGenerator._write_page` both still exist and are still called. `_write_pdf` takes `mode` as a required keyword, yet `_write_page` still declares `mode: str = "RGB"`. That default is the exact failure the required keyword exists to prevent: a call that forgets the mode silently writes RGB.

## What to implement

1. **Measure first, and record it in `## Worktree notes`.** List every caller of `_write_page` and say whether each one passes `mode`. For each `raise ValueError` at the top of `_write_pdf` (the unknown-colour-space refusal and the page-count/kinds mismatch), say whether any production path can reach it. If a test reaches it, name that test. "Unreachable from production but held by a test" is a valid finding; say so plainly.
2. **Make `mode` a required keyword of `_write_page`**, as it already is on `_write_pdf`. Fix any caller that relied on the default. The bytes written must be unchanged for every existing caller.
3. **The guards.** Keep a guard that a test holds, or that protects a boundary another module or a test can call through. Remove a guard only if step 1 shows nothing can reach it, and state why. If every guard turns out to be live, leave them all and say so; that closes F-002 as "not dead".
4. **Out of scope:** the redundant `UPDATE` in `migrations/versions/013_book_interior_ink_mode.py` (F-003). That migration is applied history; editing it changes nothing on a migrated database and risks a fresh one. Record it as declined in the notes; do not edit any migration.
5. Do not touch `tests/conftest.py`, `tests/database_guard.py` or any guard file.

## Acceptance criteria

- AC-1: the step-1 measurement is recorded in `## Worktree notes` with the commands used (an `ast`-based or grep call-site listing, the test names that reach each guard) and their output.
- AC-2: `_write_page` has no default for `mode`. One mutant control: restoring `mode: str = "RGB"` together with dropping `mode=` from one real caller must be caught by an existing test, or the notes must say plainly that no test catches it and why that is acceptable.
- AC-3: the PDFs written are byte-identical before and after for at least one RGB book and one vector/bw book. Show this by comparing a digest, or by naming an existing digest-pinning test that ran green.
- AC-4: owner's test budget: change existing tests rather than add new ones; net test count at most +1; report it.

## Worktree notes
