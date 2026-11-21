# CARD-515: A DATABASE_URL with surrounding whitespace connects to the database it names

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/515-database-url-whitespace
**Worktree:** ../PythonProject4-card-515
**Source:** roadmap wave 9, cut 2026-11-21 on the owner's "yes, start wave 9", which accepted the recommendation to trim rather than refuse. IDEA-224 (CARD-509 review F-001).
**Idea:** IDEA-224
**Wave:** 88
**Created wave:** 88
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/db/session.py, tests/conftest.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-21T20:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-509's review (F-001): `make_url` keeps a trailing space or newline in the database name ("db "), so a URL pasted with one connects to a database that does not exist and nothing says why. The "with trailing whitespace" wording appears only when the URL also fails to parse. Owner's ruling 2026-11-21: trim surrounding whitespace, do not refuse.

## What to implement

Re-verify the premise on main first (a URL ending in a space and one ending in a newline: what database name does `normalized_url` give?). Then trim leading and trailing whitespace from the URL text once, where every reader of DATABASE_URL goes through it. Find every reader of the variable by `ast` (src/, migrations/, scripts/, tests/conftest.py) and make sure each one sees the same trimmed value: in particular the test suite's per-worktree `*_test` name resolution and its production guard must agree with what the app connects to, or a padded URL could pass one check and connect elsewhere.

## Acceptance criteria

* **AC-1**: a URL ending in a space, a newline, or both, and one starting with a space, all give the same database name as the clean URL (control: main's code reds it, naming "db " or similar).
* **AC-2**: every DATABASE_URL reader found by `ast` sees the trimmed value; list them in the notes with how each is reached.
* **AC-3**: whitespace inside the URL (not at its ends) is left alone; the password is never echoed in any message (EC-1 unchanged).
* **AC-4**: net test count at most +1; change existing tests in preference to adding. Report it.

## Guardrails

* **G-1**: never connect to the production database; armed runs use the worktree's own `*_test` database on localhost.
* **G-2**: no other change to what a clean URL connects to.

## Worktree notes
