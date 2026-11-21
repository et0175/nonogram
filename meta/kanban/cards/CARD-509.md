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
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
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

### Implementation (2026-11-21)

**Premises, re-verified by a run.** IDEA-219: running `TestPlayPage_TocAndFoliosFollowTheInsertedPages` on the unchanged tree left an untracked `text.pdf` in the worktree (removed; main's copy untouched, G-2). IDEA-094: `_scheme_of(' postgresql://u:p@h/db')` returned `'<malformed scheme>'`, and `normalized_url` raised with it.

**IDEA-219.** `tests/helpers/pdf_vector.py`: new private `_scratch(out_dir)` context manager. It yields `out_dir` (created, left in place) when given; with no `out_dir` it yields a `tempfile.TemporaryDirectory` that is removed on exit. `rendered_page`, `extracted_text` and `word_boxes` all write inside it. `rendered_page`'s body moved to `_render_into` so the read-back happens before the directory goes away. Callers found by `ast` (every Call named one of the three, repo-wide): 40 call sites before this card, 42 after (the two added to the play-page test below). Exactly one passes no `out_dir`: `test_the_solutions_row_and_every_later_folio_are_the_real_page_numbers` (extracted_text). None reads a scratch file back afterwards; every result is the return value. Out of scope, found on the way: `test_book_grid_rules.py`'s `Drawn.render` has its own `self._tmp_path or Path(".")` fallback. It is dead today because all four `Drawn(...)` constructions pass `tmp_path=` (checked by `ast`). Not changed.

**IDEA-094: name, not strip.** `_scheme_of` appends `", with leading whitespace"` (or `trailing`, or `leading and trailing`) to its answer for the stripped text. For example, `' postgresql://…'` now reads `'postgresql, with leading whitespace'`. Only the error message changes. Stripping inside `normalized_url` would change a *successful* parse for all its callers (`_init_engine`, both modes of `migrations/env.py`, the test suite's DB probe in `tests/conftest.py`, and test helpers). `'postgresql://u:p@h/db '` parses today with `database == 'db '`, measured. So stripping is a behaviour decision, not a message fix. The password stays out: the scheme grammar is applied to the stripped text exactly as before.

**Tests (folded, no new items).**
- `test_the_solutions_row_and_every_later_folio_are_the_real_page_numbers`: chdir to an empty `tmp_path`. The existing `extracted_text` call runs there, plus one `word_boxes(data)` and one `rendered_page(data, 9)` with results unused. Then it asserts the directory is still empty. The PDF assertions are unchanged (G-1).
- `test_scheme_of_returns_a_grammatical_scheme_or_a_placeholder`: each string row is also checked padded leading, trailing, and both.
- `test_PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret`: each of the 720 corpus URLs is also run with a leading space. It must raise, name the space, and keep the secret out of the rendered traceback. The AC-2 literal `' postgresql://u:<secret>@h/db'` is checked after the loop.

**ACs.**
- AC-1: the folded test is green.
- AC-2: `'postgresql, with leading whitespace'` is asserted for the literal. The 14 existing rows and the corpus's unpadded expectations still hold.
- AC-3: collected 10689 before (stash) and 10689 after, so net 0.

**Controls (each restored; `git diff --stat` after shows only the four intended files).**
- `_scratch`'s temp branch replaced by `Path(".")`: the folded play-page test reds with `AssertionError: assert [PosixPath('/.../vector.pdf')] == []`, "Left contains 4 more items, first extra item: ...bbox.pdf".
- Whitespace branch disabled (`if False:`): 13 failed, namely 12 of the 14 `_scheme_of` rows (`assert '<malformed scheme>' == 'postgresql, ...ng whitespace'` and similar) and the property test (`assert '<malformed scheme>' == 'POSTGRESQL, ...ng whitespace'`). The 2 non-string rows are not padded, so they stay green.
- Leading-only mutant: 12 failed (the trailing assert).
- "both" misnamed `leading`: 12 failed (the both assert).
- Message echoes the stripped text: the property test reds with `assert 'QXSECRE)TdX8o' not in 'Traceback (...'`.

**Gate (unarmed, `-o addopts= -rfs`).** Files: test_db_url_driver, test_book_play_online_page, test_db_engine_lifecycle, test_db_isolation, test_card_349_cold_database, test_admin_binding, test_book_pdf_vector_primitives, test_book_pdf_memory, test_qr_vector_draw, test_book_footer_pointer, test_kill_matrix, test_impact_set, test_suite_profile, test_book_interior_type_floor. Result: 1151 passed, 0 failed, 18 skipped. 17 skips are "Database not reachable: DATABASE_URL is not set" (db_required, unarmed). 1 is the setrlimit(RLIMIT_AS) platform skip in test_book_pdf_memory. No scratch PDF was left in the worktree afterwards.

[Review 1/3] Score: 9.5, nothing gating, certified. Re-measured: both controls re-fired red (temp-dir default -> `Path(".")`: the play-page test reds on 4 left-over PDFs; whitespace branch off: 13 red); 42 reader calls found by `ast`, 3 without `out_dir`, none reading a scratch file back; all 17 caller files run from an empty cwd, 797 passed, 1 skipped (setrlimit), cwd still empty; `make_url` keeps a trailing space or newline in the database name, so naming rather than stripping holds; 2,160 padded corpus variants never echo the secret; `_scheme_of` total on odd inputs; net 0 (10689). F-001 (low, out of scope, owner's call) a trailing space still passes silently into the database name, and the "trailing whitespace" wording appears only when the URL also fails for another reason. F-002 (info) two `_scratch` helpers (pdf_vector, pdf_pages), forced by the import direction. F-003 (info) `Drawn.render`'s cwd fallback in test_book_grid_rules.py is dead today.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION (9033 tests; the selection takes the lock): 9002 passed / 30 skipped (29 DATABASE_URL unset + 1 setrlimit, the unarmed count) / 1 xfailed / 0 failed, 30 min; the 13 wave_close_only tests ran (lifted).
