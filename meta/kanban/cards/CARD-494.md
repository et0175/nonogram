# CARD-494: The arrange page's continued label and warning-tinted "Not printed" line; the last "guess is a tier" passages

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/494-continued-label-and-guess-text
**Worktree:** ../PythonProject4-card-494
**Source:** owner 2026-11-20 ("make these changes"), on the two questions left after wave 4: CARD-490 review F-003 and the three passages CARD-491 recorded outside its files.
**Idea:** —
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/templates/book_arrange_puzzles.html, src/nonogram/admin/static/admin.css, tests/test_book_arrange_page_breaks.py, src/nonogram/export/__init__.py, src/nonogram/admin/puzzle_review.py, docs/GENERATION_ALGORITHM.md
**UI surface:** admin book arrange page (page labels, "Not printed" marker)
**Review score:** —
**Started:** 2026-11-20T06:45Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **CARD-490 F-003 (owner's call, 2026-11-20: change it).** When an unprintable puzzle splits a pair on the arrange page, the label "page 6 · two puzzles" is printed twice, which reads as two pages; and the "Not printed: cannot be drawn" line is styled exactly like a page label.
2. **CARD-491's leftovers (owner: fix them).** Three passages still describe `guess` as a fourth tier: `nonogram.export`'s `difficulty` field docstring ("four members, \"Guess\" among them", "cat-guess.pdf"), `PuzzleFilter.difficulty`'s comment in puzzle_review.py ("ADR-0025's four tiers included"), and docs/GENERATION_ALGORITHM.md §7 ("ADR-0025 (the fourth tier) replaced …"; "its error message lists all four tiers" — measured 2026-11-20: `parse_tier` lists easy, medium, hard).

## What to implement

1. A page label repeated after an unprinted row reads "page N, continued" (no "· two puzzles"); the label that opens a page is unchanged.
2. The "Not printed" line takes the warning colour token (`--color-warning`, 5.6:1 on surface) for its text and rules; no new colour literal.
3. The three passages and the doc's "all four" line say what is true today (ADR-0031: three tiers; `guess` is a strategy).

## Acceptance criteria

* **AC-1**: the re-label test asserts "page 6, continued" after the unprinted rows and "page 6 · two puzzles" exactly once; control: the old template reds it.
* **AC-2**: the marker's computed colour is the `--color-warning` token (checked the way the admin's existing computed-style tests check a token); control: drop the rule, it reds.
* **AC-3**: an ordinary book's arrange page byte-identical to main (no unprinted row reaches either change).
* **AC-4**: net test count 0.

## Guardrails

* **G-1**: the page plan, the marker's wording and `book_detail` unchanged.
* **G-2**: comment/doc edits only in the three passages' files; no code behaviour there.

## Worktree notes
