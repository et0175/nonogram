# CARD-493: Three test minors: a vacuous trim assertion, a bare-token echo row, and two claims a proof test makes

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/493-test-minors
**Worktree:** ../PythonProject4-card-493
**Source:** roadmap rescore 2026-11-18, wave 4 (cut 2026-11-20; premises re-read against main the same day). IDEA-068 WSJF 3.08 (unverified at the rescore), IDEA-093 WSJF 3.08, IDEA-097 WSJF 3.08 (partly).
**Idea:** IDEA-068, IDEA-093, IDEA-097
**Wave:** 83
**Created wave:** 83
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_plan_storage.py, tests/test_db_url_driver.py, tests/test_book_proof_pages.py, src/nonogram/admin/book_proof.py
**UI surface:** —
**Review score:** 9.6 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T02:27Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-068 (CARD-120 F-009).** A trim assertion in tests/test_book_plan_storage.py is vacuous in DB mode. Which one was never established at the rescore; find it (run the trim tests armed and unarmed, plant a wrong trim, see which stays green).
2. **IDEA-093 (CARD-176 F-001/F-002).** tests/test_db_url_driver.py has echo rows for `postgresql:hunter2://` and `hunter2@h://x/db` but none pins the documented echo of a bare leading token (`hunter2://`); AC-1's echo check accepts any corpus scheme rather than the one drawn for that case.
3. **IDEA-097 (CARD-172 F-001/F-002).** tests/test_book_proof_pages.py credits the 1493/2048 cap-height ratio to "OS/2 sCapHeight" in the bundled face; check the font's tables (fontTools is not a dependency: read the bytes, or say so); `book_proof._annotate`'s docstring claims square page 2 keeps its foot note but only 11×8.5 is asserted.

## What to implement

Re-verify each first; drop any already closed with one line.

1. The vacuous assertion asserts something a wrong trim breaks, in DB mode.
2. One row (extend the existing parametrisation, not a new test) pins the bare-token echo; the AC-1 check compares against the scheme drawn for that case.
3. The comment names the ratio's real source; the docstring's square-page claim is either asserted (extend the existing 11×8.5 case) or the docstring is cut back to what is asserted.

## Acceptance criteria

* **AC-1**: item 1's assertion reds under a planted wrong trim, ARMED (DB mode); report the armed and unarmed skip counts with `-rfs`.
* **AC-2**: item 2's row reds when the echo of a bare token changes.
* **AC-3**: net test count 0 (parametrised rows count; report the collected count before and after).

## Guardrails

* **G-1**: no production code change except `_annotate`'s docstring.
* **G-2**: never connect to the production database; the armed run uses the worktree's own `_test` database.

## Worktree notes
- [Verify] All three items re-verified open on the branch; none dropped.
- [Item 1 / IDEA-068] The vacuous assertion was F-009's own: `test_route_refuses_110_percent_and_keeps_the_stored_plan` compared `get_book(...).metadata.size` before and after. "DB mode" in tests/test_book_plan_storage.py is the SQLite session-factory mode (`MODES = ("memory", "db")`, `sqlite_session_scope`); nothing in the file is `db_required` and `_build_app` sets its own DATABASE_URL, so arming Postgres does not change the mode. Since CARD-136 `setup_print` writes the trim to the print columns, never to `metadata.size` (a new book reads `'8x10'` there in both modes), so the old assertion was vacuous in BOTH modes, not only DB mode. Measured: planted mutant (`set_print_spec` called when the plan is refused) on a git-archive copy of HEAD -> old test 2 passed unarmed, 2 passed armed. Fix: the test now compares `(trim_width_cm, trim_height_cm)` before and after, and pins the before value to `("21.59", "27.94")` so the submitted 15.24 x 22.86 differs.
- [Control AC-1] Same mutant on the branch: `[memory]` and `[db]` both red, unarmed and armed (worktree's own `nonogram_pythonproject4_card_493_436f6c2fe5e7_test`), on `assert ('15.24', '22.86') == ('21.59', '27.94')`. The second new assert (`trim_before == ("21.59", "27.94")`) is a precondition that the mutant cannot reach (it runs after the first); it holds on a fresh book in both modes. Skips: 0 unarmed, 0 armed for this test.
- [Item 2 / IDEA-093] Row `("hunter2://h/db", "hunter2")` added to `test_scheme_of_returns_a_grammatical_scheme_or_a_placeholder` beside the CARD-176 [Limit] rows. `test_PropertyTest_DbUrl_MalformedUrlErrorNeverEchoesASecret` now takes the scheme drawn per case from `_secret_corpus` (drawn at the same point in the random stream; the 720 URLs are identical to HEAD's, compared directly) and asserts the echo equals it, or `<malformed scheme>` for the positions in `_ECHOES_A_PLACEHOLDER` (`scheme-glued`, `before-separator-behind-at`). `_SCHEME_PLACEHOLDERS` lost its only use and was removed.
- [Control AC-2] Mutant in `_scheme_of` (a candidate with no `:` before it and not starting postgres/sqlite/mysql/`db.` becomes the placeholder): on the branch only the new row is red, `assert '<malformed scheme>' == 'hunter2'` (1 failed, 56 passed); on HEAD the same mutant is 56 passed.
- [Control F-002] Mutant `return candidate.lower()` in `_scheme_of`: HEAD 56 passed (old check accepted any corpus scheme); branch red on the property, `assert 'postgresql' == 'POSTGRESQL'` (case `scheme-colon`).
- [Item 3 / IDEA-097] Font tables read with `struct` from src/nonogram/export/fonts/DejaVuSans.ttf: OS/2 is version 1 (86 bytes) and has no sCapHeight; `head.unitsPerEm` = 2048; `glyf` yMax of "H" and "P" = 1493. The comment above `DEJAVU_CAP_HEIGHT_RATIO` now names that source. Square page: on 8.5 x 8.5 in the 15 x 15 page's note is below the drawing (note top 2330 px, drawing bottom 2264 px), so `test_the_eleven_by_eight_and_a_half_small_page_keeps_its_foot_note` now loops over 11 x 8.5 and `SQUARE_TRIMS_CM` (no new id). 8.25 x 8.25 in is refused outright (`REFUSED_TRIMS_CM`), so `book_proof._annotate`'s docstring no longer names it, both in the foot sentence and in the tight-leading clue-corner sentence (8.5 x 8.5 page 0 measured at the tight leading, 45 px vs 50).
- [Control item 3] Mutant in `_annotate` (raise into the fallback when the page is square): HEAD's test 1 passed; branch red, `AssertionError: the note is not below the drawing on 21.59 x 21.59 cm` / `assert 334 > 2264`. `_assert_note_inside_margins_and_clear`'s asserts stay green under it (the fallback note is also inside the margins and clear of ink); the red assert is the below-the-drawing one.
- [Count AC-3] `--collect-only -q -o addopts= tests/`: 10707 on HEAD (git-archive copy), 10708 on the branch: +1. The id diff is exactly one: `test_scheme_of_returns_a_grammatical_scheme_or_a_placeholder[hunter2://h/db-hunter2]`. That row cannot be folded into an existing row: each row is one `(raw, expected)` input, and no existing row has a bare leading token without `:`.
- [Gate] tests/test_book_plan_storage.py, tests/test_db_url_driver.py, tests/test_book_proof_pages.py and neighbours tests/test_book_plan.py, tests/test_book_setup_print_mobile.py, tests/property/test_book_plan.py: 272 passed, 0 failed, 0 skipped unarmed; 272 passed, 0 failed, 0 skipped armed. Production change: only `_annotate`'s docstring (G-1).

[Review 1/3] Score: 9.6, nothing gating, certified. Re-measured independently: the planted wrong trim (`set_print_spec` on a refused plan) leaves the merge-base test green and reds HEAD's in both modes ("db" is the SQLite session factory), unarmed and armed, 0 skips; no other test in the file asserts the vacuous `metadata.size`; the bare-token row matches CARD-176 [Limit]; the per-case scheme check and `_ECHOES_A_PLACEHOLDER` each red under their mutants; the 720-case corpus identical to the merge-base's; the TTF read again with struct (OS/2 v1, 86 bytes, no sCapHeight; unitsPerEm 2048; glyf yMax of H and P 1493); 8.25 x 8.25 in refused ("no room for the proof note"), 8.5 x 8.5 in keeps the 15 x 15 note at the foot. Low findings fixed inline by the orchestrator: F-001 the +1 had a net-0 route — the `("sqlite:///nono.db", "sqlite")` row's only distinct trait (an empty authority) is one `_scheme_of` never reads, and the now-exact property check already pins its answer for sqlite, so the row was dropped: collected 10707, equal to the merge-base, net 0. F-002 the comment above `FALLBACK_PAGES` still counted the refused 8.25 x 8.25 in square ("on the squares ... 13.5 to 19.9 mm"): now names the 8.5 x 8.5 in square and 11 x 8.5 in and points at the test that asserts the foot placement, carrying no figure. F-003 (info) `_FALLBACK_NOTE_LEADING`'s comment in book_proof.py cites a measurement on the refused trim; left for the next card that touches book_proof.py (G-1). After: test_db_url_driver, test_book_proof_pages, test_book_plan_storage 222 passed.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 1 failed / 9006 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed, plus 11 marked passed; 2 marked owed at the wave close. The red was this card's: `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage::test_the_module_axis_bound_is_measured_rather_than_declared` pins the source line of book_proof.py's one geometry-door call, and `_annotate`'s shorter docstring moved that same call from line 760 to 758 (green on main). The pin moved 760 -> 758 with a dated note, as CARD-391 and CARD-482 did; no other test pins a book_proof.py line. tests/test_book_export_interior_cover.py re-run alone: 150 passed. The gate was not re-run for this one test constant; the wave-close full suite, run right after this merge, covers it.
