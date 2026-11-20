# CARD-509: Two small leftovers: the PDF text helper writes text.pdf into the working directory; a DATABASE_URL with leading whitespace gets "<malformed scheme>"

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/509-text-pdf-and-url-strip
**Worktree:** ../PythonProject4-card-509
**Source:** roadmap wave 7 (cut 2026-11-20 on the owner's "go with option 2, start wave 7"). IDEA-219 (found at the wave-6 closes), IDEA-094 (CARD-176 F-003, WSJF 2.31).
**Idea:** IDEA-219, IDEA-094
**Wave:** 86
**Created wave:** 86
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/helpers/pdf_vector.py, src/nonogram/db/session.py, tests/test_db_url_*.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T23:31Z
**Blocked by:** —

## Why this card exists

1. **IDEA-219.** tests/helpers/pdf_vector.py's `extracted_text` (and, by the same `out_dir or Path(".")` default, `rendered_page` and `word_boxes`) writes its scratch PDF into the current directory when no `out_dir` is given. Every full suite leaves an untracked `text.pdf` in the checkout it ran from; each wave-6 worktree had one, and main has one now.
2. **IDEA-094.** src/nonogram/db/session.py's `_scheme_of` partitions the raw string without stripping, so `' postgresql://…'` is reported as `<malformed scheme>`, a weaker hint than naming the scheme or saying the value has surrounding whitespace.

## What to implement

1. The helpers write to a temporary directory when no `out_dir` is given, and leave nothing behind. Find every caller (by `ast`/import, not text search) to check none relies on the file staying in the cwd.
2. A DATABASE_URL with leading or trailing whitespace gets a message that says so (or is stripped before parsing, if that is safe for every caller: say which and why). The password never appears in the message.

## Acceptance criteria

* **AC-1**: running the pdf_vector callers from a clean directory leaves no new file in it (control: the old default reds a check that lists the cwd before/after, folded into an existing test).
* **AC-2**: `' postgresql://u:p@h/db'` gets a message naming the whitespace or the real scheme, not `<malformed scheme>`; the existing message rows still hold (control reds).
* **AC-3**: net test count 0 (fold the new rows into existing parametrised tests); report it.

## Guardrails

* **G-1**: no change to what any test asserts about a PDF.
* **G-2**: do not delete main's existing untracked text.pdf; the orchestrator handles it.

## Worktree notes
