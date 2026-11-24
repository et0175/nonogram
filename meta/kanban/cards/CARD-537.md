# CARD-537: The CARD-145 export minors, verified first and fixed only where still live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/537-export-minors
**Worktree:** ../PythonProject4-card-537
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-025.
**Idea:** IDEA-025
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_memory.py
**UI surface:** —
**Review score:** —
**Started:** 2026-11-24T07:52Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-145's review left two minors: a same-length byte change would still pass the interior byte-length assertion, and the uploaded cover's RGBA path is not measured for memory. Re-checked on main at the cut: `TestBookPdfMemory`'s determinism group in `tests/test_book_pdf_memory.py` now has `test_the_same_book_is_the_same_length_every_time` beside `test_the_same_book_writes_the_same_operators_every_time` (sha256 per content stream) and `test_the_same_book_renders_to_the_same_pixels_every_time` (per-page digests). The first minor may now be moot, because a same-length change would have to leave both the operators and the pixels unchanged to escape. The module docstring describes a cover half of the memory bound; whether it covers an RGBA upload is not known.

## What to implement

1. Verify first. Minor 1: name the class of same-length byte change that would escape all three determinism tests (if any) and show it with a mutant, or record moot with the mutants that were caught. Minor 2: find whether any memory test feeds the cover an RGBA image (an uploaded PNG with alpha); if none does, measure one run with an RGBA cover against the bound the cover half uses.
2. Fix only the live ones. For minor 2, a live result means the RGBA path exceeds or is not covered by the bound: add the RGBA case as a parameter of the existing cover test, not a new test.
3. No change to `src/`. If the RGBA path breaks the bound, stop and report it: that is a product change and needs its own card.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### 2026-11-24 — implementation (verify first)

Probes and mutant harnesses are scratch files under `/private/tmp/claude-501/card537/` (`mutants.py`, `mutants_after.py`, `straddle.py`, `ast_rgba.py`, `rgba_probe.py`), each run as `PYTHONPATH=src:. <main venv python> <script>` from this worktree, with the assembled interior writers bound the way `tests/conftest.py`'s `_assembled_default_interior_writers` binds them.

**Minor 1 — LIVE, fixed.** `mutants.py` applies one same-length byte change to a copy of a real baseline export and hands the pair to the three determinism tests of `TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport`. On the merge-base tests, four classes escaped all three: `/FontName /DejaVuSans` -> `/DejaVuSant` in the font descriptor, `/ProcSet [ /PDF /Text ]` -> `/Texx`, one digit of an xref offset, one bit flipped in the embedded font program's Flate data. Caught: `/MediaBox` width, a JPEG byte on a raster page (both by the pixels test), a Flate byte in a content stream (operators and pixels tests). The fifth escaping class, the info dictionary's `/CreationDate` one second later, is legitimate: `straddle.py` exported the baseline twice 1.2 s apart and the files differed at exactly 2 byte positions, both in `/CreationDate` and `/ModDate` (Pillow writes them at one-second resolution). Fix: `test_the_same_book_is_the_same_length_every_time` is renamed `test_the_same_book_is_the_same_bytes_every_time` and now compares the two files byte for byte with only those two timestamps masked (`_INFO_TIMESTAMP`, `_without_timestamps`, which asserts it masked exactly 2). Re-run of the harness against the fixed test (`mutants_after.py`): all four former escapes are red on the bytes test with "the same book wrote different bytes outside the info timestamps"; the timestamp mutant stays green, by design.

Control (AC-2): a temporary src mutant in `book_vector.py`'s font-object writer alternated `FontName` between `DejaVuSans` and `DejaVuSant` on successive exports (same length). With the fix, `pytest tests/test_book_pdf_memory.py::TestBookPdfMemory_AnOperatorsPageIsTheSameStreamEveryExport` gave 1 failed, 3 passed: `test_the_same_book_is_the_same_bytes_every_time` red with `AssertionError: the same book wrote different bytes outside the info timestamps` / `At index 379826 diff: b't' != b's'`. With the test file reverted to the merge base and the same src mutant: 4 passed. The src mutant was reverted; `git diff --stat` afterwards showed only `tests/test_book_pdf_memory.py`.

**Minor 2 — LIVE, NOT fixed: the RGBA cover breaks the bound; product change, needs its own card.** `ast_rgba.py` walks every `tests/**/*.py` with `ast`: of the calls to `export_book`/`export_cover`/`create_cover_page`/`_cover_page` in `tests/test_book_pdf_memory.py` and in the two modules that import it (`tests/test_book_pdf_band.py`, `tests/test_book_puzzle_frame.py`), none passes a `cover_image`, and no test module anywhere holds both an `"RGBA"` constant and a `cover_image=` keyword. So no memory test feeds the cover any uploaded image, RGB or RGBA. `rgba_probe.py` ran `export_book` through the module's own `_measured` probe three ways: no upload, an RGB upload and an RGBA upload (1200 x 1800, resized by `create_cover_page`). All three registered 16 pages with `peak_pages == 1` and `peak_in_pages == 1.00`. No upload and the RGB upload both peaked at 25,245,000 B, which is `PEAK_IN_PAGES * PAGE_BITMAP_BYTES`. The RGBA upload peaked at 33,660,000 B: `create_cover_page` returns `cover_image.resize(...)`, which keeps the mode, so the one retained page is a four-byte-a-pixel bitmap. That is 1.33 RGB page bitmaps, over the byte bound `test_the_whole_book_holds_one_page_bitmap_at_a_time` asserts (`probe.page_bytes == PAGE_BITMAP_BYTES`, `probe.peak == PEAK_IN_PAGES * PAGE_BITMAP_BYTES`). Retention in pages still holds; the byte bound does not. Per the card ("No change to `src/`... stop and report it"), no parameter was added, because it would be red. Not measured: the writer's transient RGB conversion of that page inside `_write_page`, which the probe does not register.

Test budget (AC-3): `--collect-only -q -o addopts= tests/` gave 10713 before and 10713 after. Net 0: one test renamed and strengthened, none added.

Gate (unarmed, `-o addopts= -rfs`): `tests/test_book_pdf_memory.py` (the touched file) plus `tests/test_book_pdf_band.py` and `tests/test_book_puzzle_frame.py`, the two modules that import it. Result: 213 passed, 1 skipped, 0 failed. The one skip is `test_the_same_pair_under_an_address_space_cap_the_kernel_enforces`, because `setrlimit(RLIMIT_AS)` raised ValueError on this platform; that is the expected platform skip. `tests/test_kanban_review_record.py` passed 71 after the card edit.
