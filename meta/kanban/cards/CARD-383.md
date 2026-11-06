# CARD-383: The vector interior refuses, by name and before any page, a puzzle title its encoding cannot set — gated on the medium so it is green BOTH ways

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 2c (1d)
<!-- Stated in review cycles at DRAFT time, so the card cannot redden tests/test_kanban_review_record.py when it is stamped into a wave (CARD-325 did). Basis, mine: one new NonogramError subclass, one pre-walk check, one branch in each of two export handlers, one exit-code table row, and about six new tests with controls, all inside 7 files; no sibling comparator is exact (CARD-234's UnletterableTitle did the cover half of the same shape). The risk that would push it to 3c is the gating test: the refusal must be exercised by LIFTING a declaration that is still in the registry today, and CARD-379's `_ensure_declared` shows how much care a lift needs. NOT priced: whether any real book has a non-Latin title (the owner has not said and the production database is off limits), a wider embedded face (its own card), and any change to the readiness gate itself. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-322's premise pass finding M3b (2026-11-06) and the owner's ruling D4, "accept your recommendations for D3, D4 and D8": REFUSE LOUDLY on a title the vector interior's encoding cannot set, no transliteration, no wider font in this card; accepted as "pre-flip card B" in CARD-322's re-cut. The re-cut's measurements (mine, a private clone of main at `bb8d1121`) are quoted below.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/errors.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/app.py, src/nonogram/cli.py, tests/test_cli.py, tests/test_admin_error_text.py, tests/test_book_pdf_band.py
<!-- Over-declared in the conservative direction (compute_excess penalises only under-declaration). Per file: errors.py = the new class; book_pdf_generator.py = the pre-walk check, gated on the medium; app.py = the branch in BOTH export handlers (`generate_book_pdf_download` and the second handler that calls `_export_part(book, part, puzzles)`); cli.py = ONLY if the new class does not inherit its exit code through the MRO from `InvalidPuzzleName`; tests/test_cli.py = the one exit-code table row (NOT the structural layering guard: that guard is not edited); tests/test_admin_error_text.py = the new handler cells; tests/test_book_pdf_band.py = the refusal tests and the re-expression of the full-corpus band test. CARD-322 edits book_pdf_generator.py and app.py after this card; both are conflict.hotspots in meta/kanban/config.yml, which serialises them. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-322 converts the last five interior kinds to PDF operators. The operators are shown with one embedded face through `book_vector.encode_text`, which sets CP-1252 and raises `UnrepresentableText` for anything else. The raster pages did not have that limit. **Measured (mine, under the five-kind probe):** `tests/test_book_pdf_band.py::test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle` goes red with `RuntimeError: puzzle 'b0-p2' could not be drawn: 'Χιονονιφάδα' (U+03A7) is not in the interior's cp1252 encoding`. So once the answer page is operators, a book whose answer-page caption holds Greek, Cyrillic or Hebrew stops exporting its interior, and says so as a bare `RuntimeError`. The owner ruled (D4): refuse loudly with a message that names the puzzle, and nothing else: no transliteration, no wider font.

Three facts the premise pass did not have (all mine, read this run):

1. **The string that can offend is the answer caption's title, not only the puzzle's name.** `book_answer_key.answer_title(custom_title, puzzle_name)` returns the per-book custom title (`books.puzzle_titles`, set on the Arrangement step) when one is set, otherwise the name. A check on the name alone passes a book whose custom title is Greek.
2. **The walk re-wraps every page exception in `RuntimeError`** (`except Exception as e: raise RuntimeError(f"puzzle {named} could not be drawn: {e}")`). A `NonogramError` raised inside the page loop would be re-typed and `cli.exit_code_for` would never see it. **The check must run before the first page is drawn and outside that `try`.**
3. **Both export handlers in `app.py` end in `except Exception: ... flash(PDF_EXPORT_FAILED, "error")`.** Without a branch ahead of it, "refuse loudly" reaches the owner as the generic failure text. Three routes go through the two handlers (`finalise`, `download-pdf`, `generate-pdf`).

**This card lands BEFORE CARD-322 and must be green both ways.** Today `page_medium(PageKind.ANSWER)` is RASTER, the raster answer page sets Greek perfectly well (a DejaVu face), and an un-gated check would refuse books that export today. So the check fires only when the answer page is written as operators, and it is exercised by LIFTING the declaration in a test (the CARD-379 pattern), not by waiting for CARD-322.

## What to implement

1. **The error.** A `NonogramError` subclass in `src/nonogram/errors.py`, flat and import-free like its neighbours. The cheap shape is a subclass of `InvalidPuzzleName` so `cli.exit_code_for`'s MRO walk maps it to `INVALID_INPUT` with no `cli.py` edit; the explicit-row alternative is allowed (then `src/nonogram/cli.py` is edited). The precedent is CARD-234's `UnletterableTitle` (refused by name at the cover). The class carries the offending puzzle's id and the offending characters as attributes so the handlers do not re-parse a message.
2. **The check, before the walk, gated on the medium.** In `book_pdf_generator.BookPDFGenerator`, before any page of the interior is produced and outside the walk's per-page `try`: when `page_medium(PageKind.ANSWER) is PageMedium.VECTOR`, take the string each answer caption will print for every puzzle the interior will draw (the `answer_title` the walk itself uses; **derive where the walk calls it, do not re-implement the choice**) and refuse the first that `encode_text` rejects, naming the puzzle (its id and its number in the book), the offending characters with their codepoints, and the remedy. `encode_text` is the authority (as `_carried_by_the_interior` in `tests/test_book_pdf_band.py` already uses it); never a second character table. When the medium is RASTER the check does nothing. Decide and state where it lives so that it runs on every door into the walk (`export_interior`, `interior_stream`, `interior_pages`: the module's own comments call them "one walk behind three doors"), and check every caller of those doors for one that must keep working with an unprintable title (for example the Finalise counts in `app.py`, which read the plan and not the pages): a plan-only caller must not start raising. Say what you found.
3. **The message is in the readiness-gate voice.** Model: `book_manager.NO_PLAN_REFUSAL` (what is wrong, then the one remedy, written for the owner on a screen). It names the puzzle, shows the characters, and says to rename the puzzle or retitle it on the Arrangement step.
4. **Both export handlers in `app.py`.** Add, ahead of each `except Exception`, a branch for THIS class only that flashes the refusal's message as an error and redirects as the generic branch does. **Do not catch `NonogramError` broadly:** `UnletterableTitle` (the cover) also reaches these handlers today and is shown as the generic text; changing that is scope growth. **CARD-177's contract stands:** raw exception text must never reach the screen (`tests/test_admin_error_text.py::test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen`); the message flashed is the one the refusal builds from the owner's own typed strings and codepoints, and the new test shows a driver-style marker inside the exception chain still never reaches the screen.
5. **Tests, each with a control that can fail** (write them first):
   * (i) a lifted-answer-declaration book with a Greek puzzle name raises the new error, names that puzzle, and produces no bytes (nothing is written before the refusal);
   * (ii) the control, same lift, same book with a Latin name: exports;
   * (iii) the mutant: delete the pre-check and (i) reds with the `RuntimeError` it replaced;
   * (iv) a Greek per-book custom title on a Latin-named puzzle is refused, and a Latin custom title on a Greek-named puzzle is NOT (the printed string decides);
   * (v) UNLIFTED (today's tree), the same Greek-named book exports: the gate is real (this is the cell that stops an un-gated check landing);
   * (vi) `tests/test_cli.py` gains the table row for the new class (`test_every_domain_error_has_an_exit_code` requires one for every declared `NonogramError` subclass, so a class without a row reds it) and `test_domain_error_maps_to_its_exit_code[<name>]` is green;
   * (vii) in `tests/test_admin_error_text.py`, all three routes flash the refusal text for a lifted Greek-title book, and still flash `PDF_EXPORT_FAILED` for every other exception (the existing parametrized cells stay green untouched);
   * (viii) re-express `test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`: its own docstring says it is red on a converted interior and that the red is CARD-322's. It must be green BOTH ways: the expectation is **derived from `page_medium(PageKind.ANSWER)`**, never listed, so unlifted it bands every name, and under the probe it asserts the names the interior cannot carry are refused and the rest are banded, keeping the corpus floors (G-4). Its matched control `..._ForEveryNameTheInteriorCanCarry` is untouched.

## Acceptance criteria

- **AC-1** *Given* the answer page declared vector (by lifting the declaration), *then* a book whose answer-caption string for any puzzle holds a character outside the interior's encoding is refused before any page is produced, by the new `NonogramError` subclass, whose message names the puzzle and the characters and gives the remedy.
  (test: the new cells (i) and (iv) of item 5, in `tests/test_book_pdf_band.py`)
- **AC-2** *Given* the same lift, *then* a book whose every caption string is encodable exports unchanged.
  (test: the control (ii) of item 5)
- **AC-3** *Given* today's tree (answer page raster), *then* the Greek-named book still exports and the check never fires.
  (test: cell (v) of item 5; it is the guard against an un-gated landing)
- **AC-4** *Given* the pre-check is deleted, *then* AC-1's test reds.
  (test: the mutant (iii), run as a plant with `must_red` asserted non-empty before it runs)
- **AC-5** *Given* the new class, *then* `cli.exit_code_for` maps it to `INVALID_INPUT` and `tests/test_cli.py`'s every-error-has-a-code cell stays green.
  (test: `test_every_domain_error_has_an_exit_code`, existing, and `test_domain_error_maps_to_its_exit_code` for the new row)
- **AC-6** *Given* the refusal in any of the three export routes, *then* the owner sees the refusal's message and not `PDF_EXPORT_FAILED`; every other exception still shows `PDF_EXPORT_FAILED`; and no raw exception text reaches the screen.
  (test: cell (vii) in `tests/test_admin_error_text.py`, plus the existing `test_the_flash_is_the_constant_and_the_error_is_logged` and `test_PropertyTest_AdminErrors_RawExceptionTextNeverReachesTheScreen`, existing and unmodified)
- **AC-7** *Given* the full-corpus band test, *then* it is green unlifted and green under the five-kind probe with its expectation derived from the medium.
  (test: `test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`, re-expressed; run both ways with the instruments below)
- **AC-8** *Given* a caller that only plans the interior (the Finalise counts), *then* it does not start raising for an unprintable title; the report names each caller of the walk's three doors and what it does.
  (check: review-lens, because the set of callers is read from `src/` by `ast`, not by a test)
- **AC-9** *Given* the owner's open question, *then* the report states in one line that whether any real book has a non-Latin title is UNANSWERED and was not looked up (the production database is off limits), and that a wider embedded face is its own card.
  (check: review-lens)

## How to measure, and the instruments are not yours to build

The probe is `scratchpad/card338/probe_five_kinds.py` (loaded with `-p`, `PYTHONPATH=scratchpad/card338`); the per-module census is `scratchpad/card338/census_five_kinds.py --only <module>`; the on-disk end state is `scratchpad/card338/fidelity_to_the_end_state.py <module>`. `-rEfs` as ONE flag; `-o addopts=` as two argv items; the whole environment inherited. Do not build or edit them. The hang guard default is 300 s (CARD-381); set nothing about `NONOGRAM_TEST_HANG_SECONDS`. Do not kill processes by name.

## Guardrails

- **G-1** — **The check is gated on the medium** (`page_medium(PageKind.ANSWER)`); un-gated it changes what today's books export. Cell (v) is its guard.
- **G-2** — Do not catch `NonogramError` broadly in the handlers; do not change how `UnletterableTitle` or any other exception is shown.
- **G-3** — No transliteration, no substitution, no `.notdef` boxes, no wider face, no new font file in this card (D4). A wider face would be package data and its own card.
- **G-4** — No test deleted, renamed, skipped or merged, parametrize ids included; do not lower a corpus floor in the band test. Re-expression of the one named test is the only edit to an existing test body, apart from the single table row in `tests/test_cli.py`.
- **G-5** — Do not edit `tests/test_cli.py`'s structural layering guard (only the exit-code table gains its row) and do not give `nonogram.errors` an import. `errors.py` stays flat and import-free.
- **G-6** — Raw exception text never reaches the screen (CARD-177): the flashed text is the refusal's own, built from the owner's typed strings.
- **G-7** — No `src/` change beyond the files in Touches; the readiness gate (`book_manager`) is not edited by this card.
- **G-8** — No new runtime dependency (ADR-0006/R1).
- **G-9** — A full suite needs the board's lock; never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`; you do not run the full suite. Do not connect to the production database.
- **G-10** — Take no timing measurements and report no durations.

## System contract

- FR-043 — the book's export is two files, the interior and the cover (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0035 — the readiness gate refuses with a remedy written for the owner (check: review-lens; this card borrows its voice and does not edit the gate)
- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a derivation that cannot classify a shape fails rather than passes (check: review-lens)
- ADR-0006/R1 — the runtime dependency baseline stays closed (check: `test_the_dependency_baseline_is_still_closed`)

## Worktree notes

(none yet)
