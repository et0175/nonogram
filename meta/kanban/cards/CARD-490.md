# CARD-490: The arrange page marks a puzzle that will not print, as the book page already does

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/490-arrange-not-printed
**Worktree:** —
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-024, WSJF 3.46 (CARD-140 F-007).
**Idea:** IDEA-024
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/book_arrange_puzzles.html, tests/test_book_arrange*.py
**UI surface:** admin book arrange page (page labels)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

On the arrange page (`arrange_puzzles_in_book`, `book_arrange_puzzles.html`) a puzzle the interior cannot draw sits between the "page 3" and "page 4" labels with no marker, so the screen says it prints on page 3. The template has only the `page_plan_failed` branch. The book detail page (`book_detail`) already says "Not printed: cannot be drawn" for the same rows (CARD-165).

## What to implement

1. Reproduce first: a book holding one undrawable puzzle; record what the arrange page shows today.
2. The arrange page marks such a row "Not printed: cannot be drawn", with the same wording and the same source of truth as `book_detail` (reuse the computation; do not derive "undrawable" a second way).
3. The row does not sit under a page label it will not print on.

## Acceptance criteria

* **AC-1**: an undrawable puzzle's row on the arrange page carries the marker and no page number; control: drop the marker from the template, it reds.
* **AC-2**: a book with no undrawable puzzle renders the arrange page byte-identical to main (compare the HTML of one ordinary book before and after).
* **AC-3**: net test count at most +1; report it.

## Guardrails

* **G-1**: the page plan itself is unchanged; this is display only.
* **G-2**: the marker's wording is `book_detail`'s, not new copy.

## Worktree notes
