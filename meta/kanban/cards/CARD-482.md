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

**What changed (commit bd32fece).** `book_proof.render_proof_pdf` now builds
`BookPDFGenerator(book)` once, reads its public `interior_bitmap_mode` and
converts the **finished** pages to it (`page.convert(mode)`) before the
unchanged `save(..., dpi=(DPI, DPI))`. The page loop moved into a private
`_drawn_pages(generator)` so the generator is not constructed twice;
`proof_pages(book)` is `_drawn_pages(BookPDFGenerator(book))` and still returns
the drawn `"RGB"` pages, so every pixel-level proof test reads what it read
before. `book_pdf_generator.py` is not edited (G-1); the mode rule is read, not
restated.

**`book=None`.** Read from the code, and measured by the cycle-1 reviewer (`render_proof_pdf(None)` gave DeviceGray on both pages): `BookPDFGenerator(None)` takes
`book_ink_mode(None)` -> `ink_mode_from_stored(None)` -> `DEFAULT_INK_MODE`,
which is `InkMode.BLACK_AND_WHITE`, so a `None` proof is `"L"` /
`/DeviceGray` -- the same as a book with an empty `interior_ink_mode` column,
which is the coherence `proof_pages`' docstring already claims for trims.

**AC-1 (measured, from the PDF bytes via
`test_book_pdf_ink_mode.pdf_image_objects`).** Book 1 profile, 2 pages each:
no stored mode -> `DeviceGray` x2; stored `"bw"` -> `DeviceGray` x2 (decoded
mode `L`); stored `"colour"` -> `DeviceRGB` x2 (decoded mode `RGB`). Test:
`tests/test_book_proof_pages.py::TestBookProof_TwoTrimSizedPagesAtExpectedCells::test_the_proof_is_written_in_the_books_interior_colour_space`.

**AC-2.** The same test asserts all three are 2550 x 3300 px and MediaBox
(0, 0, 612, 792) pt. No existing proof test was edited; the file runs 93 passed,
0 skipped.

**AC-3 (control, measured).** Replacing the conversion line with
`pages = _drawn_pages(generator)` reds exactly the new test (1 failed, 92
passed; `AssertionError: default` on the colour-space line). A second mutant,
`mode = "L"` hard-coded, reds it on the colour arm (`AssertionError: colour`).
Both restored with `git checkout --`; tree clean.

**AC-4.** Collected in `tests/test_book_proof_pages.py`: 92 on main, 93 on the
branch (+1).

**Other runs (all `-o addopts= -rfs`, zero skips).** `test_book_proof_pages.py`
+ `test_admin_error_text.py` (monkeypatches `render_proof_pdf` on the route) +
`test_book_pdf.py::test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision`
(AST check that `render_proof_pdf` still reaches `save(save_all=...)` and not
`_write_pdf`): 136 passed. `test_suite_profile.py` + `test_check_ref_resolution.py`
+ `test_book_pdf_ink_mode.py`: 528 passed. The render census is file-level and
this file was already in it.

**G-2 renders.** `~/Documents/nonogram-reviews/CARD-482/`: `proof_bw.pdf`
(959,899 B), `proof_colour.pdf` (1,048,422 B), and `proof_bw_page1.png`,
`proof_colour_page1.png` (page 1 decoded from each PDF's image XObject, in its
written mode).

[Review 1/3] Score: 9.0, nothing gating, certified. Conversion lossless (0 non-grey pixels; `convert("L")` = R channel) and pixel-identical to the interior's own B&W path for both pages; seven mutants each red the new test. F-001 (low) the `None` claim was read, not run; F-002 (low) the docstring's first line said "proof_pages as one PDF".

[After certification, uncertified] One docstring line in `render_proof_pdf` reworded for F-002 and the notes' `None` line corrected for F-001; no code change.
