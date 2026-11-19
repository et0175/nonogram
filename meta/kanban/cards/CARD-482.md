# CARD-482: The proof PDF is written in the book's interior colour mode, not always RGB

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/482-proof-colour-mode
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-482
**Source:** roadmap rescore 2026-11-18, wave 2 (IDEA-021, WSJF 5.0); premise re-read against main on 2026-11-19.
**Idea:** IDEA-021
**Wave:** 81
**Created wave:** 81
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_proof.py, tests/test_book_proof_pages.py
**UI surface:** none
**Review score:** 9.0 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-19T07:14Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`book_proof.render_proof_pdf` saves the proof pages with Pillow straight from `"RGB"` images, so every page carries `/DeviceRGB` (CARD-147 F-008). The interior writer chooses `"L"` (`/DeviceGray`) for a black-and-white book (`book_pdf_generator.py`'s mode table). The proof draws only black (`_annotate`'s one `fill="black"`), so a proof of a B&W book announces colour the interior does not.

## What to implement

Write the proof in the same mode the interior would use for the given book: `"L"` for a black-and-white interior, `"RGB"` for a colour one, by the same rule the interior uses (read it, don't restate it). Convert the pages, not the drawing.

## Acceptance criteria

* **AC-1**: a proof of a B&W book has every page image object at `/DeviceGray` (read from the PDF bytes); a colour book's proof stays `/DeviceRGB`.
* **AC-2**: page size and DPI are unchanged (the existing proof tests stay green unedited, or each edit is explained).
* **AC-3**: one control: reverting the conversion reds AC-1's test.
* **AC-4**: net test count at most +1 (change an existing proof test where one fits).

## Guardrails

* **G-1**: `book_pdf_generator.py` is not edited. The proof may call the same public mode rule, but not the private writer.
* **G-2**: the owner looks at a rendered proof after merge (image-pipeline rule); put renders in `~/Documents/nonogram-reviews/CARD-482`.

## Worktree notes

—
