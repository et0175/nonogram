# CARD-539: An uploaded cover is held as one RGB page, so a transparent upload stays within the one-page memory bound

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/539-rgb-cover
**Worktree:** ../PythonProject4-card-539
**Source:** found 2026-11-24 by CARD-537 (IDEA-025, minor 2), which stopped on its own rule because the fix changes `src/`. Added to wave 17.
**Idea:** IDEA-025
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** CARD-537
**Touches:** src/nonogram/admin/book_pdf_generator.py (`BookPDFGenerator.create_cover_page`), tests/test_book_pdf_memory.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T08:40Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`BookPDFGenerator.create_cover_page` returns an uploaded cover as `cover_image.resize(...)`, which keeps the upload's mode. An RGBA upload (a PNG with transparency) is therefore held at 4 bytes a pixel. CARD-537 measured `export_book` through `tests/test_book_pdf_memory.py`'s own probe: peak 25,245,000 B with no upload and with an RGB upload, 33,660,000 B with an RGBA upload. All three held one page at a time. The RGBA peak is over the bound `test_the_whole_book_holds_one_page_bitmap_at_a_time` holds the book to. `_write_page` already converts every page to RGB as it writes, so the printed cover keeps no alpha today. No memory test feeds the cover any upload at all.

## What to implement

1. Before changing anything, export the cover page from an RGBA upload on main (with transparent and half-transparent regions) and record its digest. That is today's printed appearance.
2. Make `create_cover_page` hand back an RGB page for an upload in any mode, holding one page at 3 bytes a pixel.
3. The printed cover must not change: compare against step 1's digest. If converting before or after the resize changes the pixels (Pillow resamples RGBA with premultiplied alpha), keep today's pixels, for example by resizing first and converting after, inside `create_cover_page`. If today's pixels cannot be kept within the bound, stop and report: what a transparent region prints as is the owner's call.
4. Add the RGBA upload as a case of the existing whole-book memory test (a parameter, not a new test function). It must fail on main's `create_cover_page` and pass after the fix.
5. Update the docstring's "returned untouched" sentence to say what the code now does.

## Acceptance criteria

- AC-1: with an RGBA upload, `export_book`'s measured peak equals the no-upload peak, by the module's own probe.
- AC-2: the printed cover from an RGBA upload is byte-identical to main's (digest recorded before and after), or the card stopped and reported under step 3.
- AC-3: the new parameter fails on main's `create_cover_page` with its assertion text recorded, and passes on the branch.
- AC-4: owner's test budget: net tests at most +1 (one parameter), reported.

## Worktree notes

### 2026-11-24 — implementation

Scratch tools under `/private/tmp/claude-501/card539/`: `digests.py` (each upload mode's printed cover, `export_cover` through the module's `_measured`), `peak.py` (`export_book` through `_measured`, interior writers bound as `tests/conftest.py`'s `_assembled_default_interior_writers` binds them), each run as `PYTHONPATH=src:. <main venv python> <script>` from this worktree.

**What changed.** `BookPDFGenerator.create_cover_page`: an upload is resized in its own mode (LANCZOS, as before) and the result is returned as is when it is `"RGB"`, otherwise `page.convert("RGB")` — the order `_write_page` converted it in, so the printed pixels are kept. Its docstring's "returned untouched" sentence now says this. `tests/test_book_pdf_memory.py`: `test_the_whole_book_holds_one_page_bitmap_at_a_time` is parametrized `upload` in `[None, "RGBA"]` (ids `no-upload`, `rgba-upload`); the RGBA case exports the book with `_transparent_cover_upload()` (1200 x 1800; a fully transparent band with colour (200, 30, 90) under alpha 0, a half-transparent band, an opaque band) inside `_measured`, asserts with `same_page` that the printed cover is `upload.resize(...).convert("RGB")`, then the existing page and peak assertions. `tests/test_book_export_interior_cover.py`: `CALLEE_EXEMPTION_COST` moves by the one added call, 727/467/171/170/0/0 -> 728/468/172/171/0/0 (the module's `ast.Call` count 799 -> 800, by `ast`).

**Digests (step 1 before src changed, then after).** `export_cover` PDF sha256 (first 16 hex, `/CreationDate` and `/ModDate` masked), identical before and after; the probe's retained cover page before -> after:

| upload | printed cover digest | retained cover page (B) |
|---|---|---|
| RGBA | 16a25082a9192281 | 33,660,000 -> 25,245,000 |
| RGB | 42b09e37c24b9a1a | 25,245,000 -> 25,245,000 |
| LA | 66c118fccad25111 | 16,830,000 -> 25,245,000 |
| L | 4b00602ca068a34e | 8,415,000 -> 25,245,000 |
| P with transparency | 4be37baf8c957840 | 8,415,000 -> 25,245,000 |
| PA | 0689823e8803564b | 16,830,000 -> 25,245,000 |
| CMYK | 4813397808f580f9 | 33,660,000 -> 25,245,000 |
| 1 | 6ff77b946d035666 | 8,415,000 -> 25,245,000 |
| I | 3d9bfdb353329b8b | 8,415,000 -> 25,245,000 |
| F | d7f9f656d7dd5757 | 8,415,000 -> 25,245,000 |

The page's RGB pixel digests also agree in every mode. Converting before the resize would not keep them: on the RGBA upload it changes 7,215,972 of 8,415,000 pixels, and on the test upload the transparent band prints (0, 0, 0) resized-first and (200, 30, 90) converted-first. For L, P, 1, I, F, LA and PA the retained cover page grows to one RGB page; the writer already converted it to RGB transiently, and the whole-book peak is unchanged. Not investigated: the probe's `bitmap_bytes_of` costs I and F pages at one byte a pixel.

**AC-1.** `peak.py`: main — no upload 25,245,000 B (1.00 page), RGBA upload 33,660,000 B (1.33); branch — both 25,245,000 B (1.00); all 16 pages seen, `peak_pages` 1.

**AC-2.** RGBA printed cover 16a25082a9192281 before and after (table above).

**AC-3.** Control 1, main's `create_cover_page` restored over the branch: `[rgba-upload]` red, `E assert 33660000 == 25245000` on `assert probe.page_bytes == PAGE_BITMAP_BYTES`; 1 failed, 1 passed. Control 2, a convert-then-resize mutant: red with `AssertionError: the uploaded cover printed different pixels from main's`. Branch: 2 passed. After each control src was restored and `git diff --stat` showed only the card's changes.

**AC-4.** `--collect-only -q -o addopts= tests/`: 10713 on main, 10714 on the branch. Net +1, the one parameter.

**Callee-cost table.** `tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage`: 23 passed on main's tree (a detached worktree of main, since removed) at 727/467/171/170/0/0, and 23 passed on the branch at 728/468/172/171/0/0. Before the table moved, the branch measured `[((), 728), ...]` and failed with "At index 0 diff: ((), 728) != ((), 727)".

**Gate** (unarmed, `-o addopts= -rfs`): `tests/test_book_pdf_memory.py`, `tests/test_book_cover.py`, `tests/test_book_export_interior_cover.py`, `tests/test_book_pdf_ink_mode.py`, `tests/property/test_book_export_interior.py`, `tests/test_book_pdf_band.py`, `tests/test_book_puzzle_frame.py`: 463 passed, 1 skipped, 0 failed. The skip is `tests/test_book_pdf_memory.py`'s `setrlimit(RLIMIT_AS)` platform skip (ValueError: current limit exceeds maximum limit).

**Scope.** The production upload route (`_uploaded_cover` in `admin/app.py`) already converts the upload to RGB before export, so the RGBA memory overrun this card fixes is reached only by direct `export_book`/`export_cover` callers, and what a transparent region prints on the route is unchanged by this card.
