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

### Implementation round 1 (2026-11-25)

**Verdict:** done. `_write_page`'s `mode` is now a required keyword; both `_write_pdf` guards are live and kept (F-002 closes as "not dead"); F-003 declined. Net test count +1.

**Measurement (step 1, AC-1).** Call sites by `ast` (script walks every `ast.Call` in `src/` and `tests/` whose callee name is `_write_page` or `_write_pdf`, and prints the enclosing function and the keywords passed):

```
src/nonogram/admin/book_pdf_generator.py::export_book calls _write_pdf positional=2 keywords=['mode', 'kinds']
src/nonogram/admin/book_pdf_generator.py::export_interior calls _write_pdf positional=2 keywords=['mode', 'kinds']
src/nonogram/admin/book_pdf_generator.py::export_cover calls _write_pdf positional=2 keywords=['mode', 'kinds']
src/nonogram/admin/book_pdf_generator.py::_write_pdf calls _write_page positional=6 keywords=[]
(+ 17 test/helper calls of _write_pdf, every one passing mode= and kinds=)
```

- `_write_page` has **one** caller: `BookPDFGenerator._write_pdf`, which passed `mode` (positionally, sixth argument). No caller relied on the default. Three test wrappers stand in for it via monkeypatch and forward `*args, **kwargs` unchanged: `band_draws` (fixture of `TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage`), `test_a_page_that_fails_at_page_12_of_14_hands_the_caller_nothing`, and the `write_page_and_compare` wrapper in `tests/test_book_pdf_ink_mode.py`. All three forward a keyword `mode=` unchanged.
- Modes reaching `_write_pdf` (same script, printing the `mode=` value): production passes `self.interior_bitmap_mode` (twice) and the literal `'RGB'` (`export_cover`). `interior_bitmap_mode` is `InkMode.bitmap_mode`, which returns `"L" if self is InkMode.BLACK_AND_WHITE else "RGB"`; tests pass only `'L'`, `'RGB'` or `interior_bitmap_mode`.
- **Colour-space guard** (`if mode not in _PDF_COLOUR_SPACE`): unreachable from production (above). Before this card **no test reached it either**: the message text `a book PDF is written in` appears in no test (`grep -rn` over `tests/` hit only `src/`), and no call passes another mode. Yet `TestWritePdf_RefusesWhatItCannotWrite`'s docstring said both before-the-buffer refusals were "each driven". Kept, because `_write_pdf` is a boundary the test tree calls directly (17 calls above) and without the guard the failure changes shape: mutant M1 below shows a raster page then fails as `KeyError: 'CMYK'` from `_write_page` mid-write; and inside `_write_pdf` `mode` is read only by this guard and by the `_write_page` call, so an all-vector file would accept any mode silently.
- **Page-count/kinds guard** (`if len(kinds) != page_count`): unreachable from production as long as `interior_stream`'s `page_kinds` walk agrees with its page plan. They are two separate walks, and `interior_stream`'s own comment says the check sits in `_write_pdf` so that a drifted kind list is refused. Held by `tests/test_book_pdf.py::TestWritePdf_RefusesWhatItCannotWrite::test_a_kind_list_that_is_not_one_per_page_is_refused`. Kept.

Guard mutants, each run on `tests/test_book_pdf.py::TestWritePdf_RefusesWhatItCannotWrite` (5 collected) with the guard's `if` replaced by `if False:`, then restored from a copy:

```
M1 colour-space guard removed: FAILED ...::test_a_colour_space_it_does_not_know_is_refused (KeyError: 'CMYK')   1 failed, 4 passed, exit 1
M2 kinds-length guard removed: FAILED ...::test_a_kind_list_that_is_not_one_per_page_is_refused (IndexError)    1 failed, 4 passed, exit 1
unmutated:                                                                                                         5 passed, exit 0
```

**The change.**
- `src/nonogram/admin/book_pdf_generator.py`, `BookPDFGenerator._write_page`: `mode: str = "RGB"` becomes `*, mode: str`. The docstring's "defaults to RGB" paragraph is replaced by the reason it is required. `BookPDFGenerator._write_pdf` now passes `mode=mode`. Nothing else in the module changed.
- `tests/test_book_pdf.py`, `TestWritePdf_RefusesWhatItCannotWrite`: one new cell, `test_a_colour_space_it_does_not_know_is_refused`. It makes the class docstring's "each driven" claim true for the colour-space refusal, which no test drove before.
- F-003 (the redundant `UPDATE` in `migrations/versions/013_book_interior_ink_mode.py`) is **declined**. That migration is applied history: editing it changes nothing on a migrated database and puts a fresh one at risk. No migration was touched.

**AC-2 mutant (default restored + `mode=` dropped from the one real caller, `_write_pdf`).** I applied both edits and confirmed them with `git diff`, then ran `tests/test_book_pdf_ink_mode.py` (52 collected):

```
FAILED ...TestBookInk_BlackAndWhiteInteriorIsGrayscale::test_every_page_declares_devicegray_and_one_channel
FAILED ...TestBookInk_BlackAndWhiteInteriorIsGrayscale::test_no_mark_moves_on_any_page_bitmap
FAILED ...TestBookInk_BlackAndWhiteInteriorIsGrayscale::test_the_file_the_owner_downloads_is_the_one_the_book_chose[InkMode.BLACK_AND_WHITE-DeviceGray]
FAILED ...TestBookInk_BlackAndWhiteInteriorIsGrayscale::test_the_grayscale_file_is_materially_smaller
FAILED ...TestBookInk_ColourInteriorIsUnchanged::test_black_and_white_is_shorter_than_colour_at_the_current_length
FAILED ...TestBookInk_CoverIgnoresTheInteriorMode::test_export_book_writes_a_grey_interior_beside_a_colour_cover
FAILED ...TestBookInk_InkPositionsDoNotDependOnTheMode::test_the_two_modes_agree_on_every_page_of_every_book
7 failed, 45 passed, exit 1
```

Caught by existing tests. I then restored the file from a copy of the post-change source. `git diff src/` afterwards shows only the intended change (`mode=mode` at the call, `*, mode: str` in the signature, the docstring).

**AC-3 byte identity.** A scratch script freezes `time.gmtime` (the only non-deterministic input: `_write_pdf` stamps CreationDate/ModDate) and builds the generator through the production builder `book_interior_vector.interior_generator` on `corpus_book("card-546")` with `baseline_puzzles()`. Two runs on the base agreed with each other (`diff` empty). Before and after the change:

```
bw interior: bitmap_mode=L bytes=868448 DeviceGray=4 DeviceRGB=0 sha256=70a67148fc1cb0256a39f2d23e0cee963892a4bfae46133207875b990f2fc02e
colour interior: bitmap_mode=RGB bytes=1005258 DeviceGray=0 DeviceRGB=4 sha256=b0c80a400c6f909b7af4d5d3d0df19ee4de5fde0408a7aab0bff22c7caf6c4e7
cover (RGB) of bw book: bytes=138664 DeviceRGB=1 sha256=8b61f0f24e463a4244950e85e1736d261564db58706588f03c445e6c7dab1656
diff after-vs-before: exit 0 (identical)
```

The bw interior writes 4 raster pages as DeviceGray and its other pages as vector, so the digest covers both a vector/bw file and an RGB file.

**AC-4 test budget.** Net test count **+1** (`test_a_colour_space_it_does_not_know_is_refused`). No existing test was changed. No test called `_write_page` relying on the default, so none needed editing.

**Test runs on the final code.**
- `tests/test_book_pdf_band.py::TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage` + `tests/test_book_pdf_memory.py::TestBookPdfMemory_NothingHalfWrittenEscapes` (the `_write_page` wrappers): 7 collected, 7 passed, 0 skipped, exit 0.
- `tests/test_book_pdf.py tests/test_book_pdf_ink_mode.py tests/test_book_puzzle_page_vector.py tests/test_book_solved_answer_key.py`: 332 collected, 332 passed, 0 skipped (no SKIPPED/FAILED lines under `-rfs`), exit 0.
- `tests/test_kanban_review_record.py`: 71 passed, 0 skipped, exit 0.
- The full suite was not run here; the merge gate runs it.
