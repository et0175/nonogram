# CARD-541: The book detail page's print-number fallback for a repeated puzzle id, verified first and pinned only if live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/541-repeated-id-number
**Worktree:** ../PythonProject4-card-541
**Source:** roadmap wave 18, cut 2026-11-24 on the owner's pick of "a small Wave 18" from the backlog's remaining no-decision items. IDEA-084.
**Idea:** IDEA-084
**Wave:** 97
**Created wave:** 97
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_detail_page.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-24T11:03Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-165's review left three minors (F-001/F-002/F-003). F-003: the stored-order fallback with a repeated id is untested (a mutant survived). F-001: the printed-number test reads the band only through the single-puzzle-page path, with no shared two-up fixture. Re-checked on main at the cut: the book detail view in `src/nonogram/admin/app.py` builds its rows from `book.puzzle_ids` as copies ("a repeated id is two rows here as it is two rows there; rows are matched back by identity"), and `tests/test_book_detail_page.py` has a CARD-165 section. Whether either minor is still live is not known. F-002 (the no-plan banner points to Finalise even when the cause is a code bug) is banner wording the owner decides, and is not in this card.

## What to implement

1. Verify first. F-003: write a mutant of the detail view's fallback that mishandles a repeated id (for example, matching rows back by puzzle id instead of by identity, or dropping the second copy) and run `tests/test_book_detail_page.py` against it. F-001: check whether any test reads a printed number from a two-up page; if none does, run a mutant that numbers two-up pages wrongly and see whether a test notices.
2. Fix only the live ones, by extending an existing test or its parametrize.
3. Leave the banner wording alone.

## Acceptance criteria

- AC-1: each in-scope item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a computed figure), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and a fix to a test or to code has one control that fails when the fix is reverted. A comment-only fix records the computed figure instead.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### 2026-11-24 — verify-first verdicts, fixes, controls (python-pro)

Source: the only CARD-165 review, `meta/review/20261004T084051Z-CARD-165-cycle1.yml` (main checkout). Mutant script: `/private/tmp/claude-501/card541/mutate.py`, with four mutants. Each one asserts `count(old) == 1` and is restored with `git checkout -- src/`. `git diff --stat -- src/` was empty after every run. Command for every run: `.venv/bin/python -m pytest -o addopts= -rfs -q tests/test_book_detail_page.py`.

- M4 (F-003): in `book_detail`'s `number_plan_failed` fallback, `for p in book.puzzle_ids` becomes `for p in dict.fromkeys(book.puzzle_ids)`.
- MP (F-001, page side): `book_detail`'s `numbers` numbers each row by its puzzle-page position instead of `enumerate(plan.printed)`. This is identical on one-up books.
- T2 (F-001, band side): `vector_two_up_page` zips `plan.numbers[::-1]`.

**F-003: LIVE.** On the merge-base test file, M4 gave 38 passed (survives).

**F-001: LIVE.**
- Probe plugin (`/private/tmp/claude-501/card541/probe/twoup_probe.py`): over the merge-base test file it counted 67 page plans and 196 one-puzzle pages, and no two-up page was planned or drawn.
- On the merge-base test file, MP and T2 each gave 38 passed (both survive).
- T2 is caught elsewhere, by `tests/test_book_pdf_two_up.py::TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand::test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two`. MP is caught by nothing on the merge-base file.
- Once a two-up page formed, the helper's `spy_two` was found broken. It still had the old two-argument signature, so `vector_two_up_page`'s `play_page`/`solution_pages` raised `TypeError: spy_two() takes 3 positional arguments but 5 were given` and the interior download returned 302. The spy had never run.
- Pairing probe (`/private/tmp/claude-501/card541/pairprobe.py`, 4 easy puzzles on an 8x10 trim): grids of 5, 8, 10 and 12 cells pair; 15 does not.

**Fixes (tests only, `tests/test_book_detail_page.py`; no src change):**
- `_add_puzzle`, `_make_book` and `_book_stored_as` take `side=20`. The rectangle is clamped with `min(..., side)`, which changes no 20x20 fixture.
- `test_each_number_is_the_band_the_exported_interior_prints` is parametrized: one-up at side 20, and two-up at side 10, which gives an easy pair, a medium pair and a hard page printed alone. It asserts the plan has a two-up page exactly when the case says so.
- `_bands_the_export_prints`'s `spy_two` now forwards `*args, **kwargs`.
- `test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers` stores `ids + [ids[0]]`. Its existing assertion "stored order, as stored" now needs both copies.

**Controls (branch test file; all mutants restored):**
- M4: `test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers` is red. `AssertionError: stored order, as stored ... Right contains one more item: 'puzzle_000001'`.
- MP: `test_each_number_is_the_band_the_exported_interior_prints[two-up]` is red. `assert 'Puzzle 2 · Easy' == 'Puzzle 1 · Easy'`.
- T2: the same `[two-up]` case is red. `assert 'Puzzle 2 · Easy' == 'Puzzle 1 · Easy'`.
- With the fix reverted (merge-base test file), M4, MP and T2 each gave 38 passed. With only the `spy_two` change reverted, the `[two-up]` case is red with the `TypeError` above.

**Figures (re-derived at the end):**
- Branch: `tests/test_book_detail_page.py` 39 passed, 0 failed, 0 skipped.
- Neighbour gate, run unarmed: `tests/test_book_detail_page.py` + `tests/test_book_pdf_two_up.py` gave 92 passed, 0 skipped.
- Net collected: merge-base 10714, branch 10715, a net change of +1 (from the parametrize).

F-002 (banner wording) was left alone: the owner decides it.

[Review 1/3] Score: 9.5, certified. I re-derived the verdicts with my own mutants, without reusing the implementer's scripts; each was restored with `git checkout`, and all runs used `-o addopts= -rfs` with 0 skips. R1 drops the repeated row in `book_detail`'s `number_plan_failed` fallback by skipping an id already listed: red on the branch (`test_a_book_whose_page_plan_cannot_be_built_shows_no_numbers`, 1 failed / 38 passed), survives main's file (38 passed). R2 numbers rows by their puzzle-page ordinal instead of `enumerate(plan.printed)`, wrong only on two-up books: red on the branch (`test_each_number_is_the_band_the_exported_interior_prints[two-up]`), survives main's file (38 passed). R3 reverses `plan.numbers` in `vector_two_up_page`: red on the same `[two-up]` case, survives main's file (38 passed). The `[two-up]` case really draws a two-up page and `[one-up]` does not: with `spy_two` replaced by a raise, `[one-up]` stays green and `[two-up]` goes red. Restoring only `spy_two`'s old two-argument signature also reddens `[two-up]`. The `side` parameter defaults to 20 and changes nothing for existing callers; no assert was weakened. Figures reproduce: 38 passed under each mutant on main's file; 39 passed on the branch; 92 with `tests/test_book_pdf_two_up.py`; 10714 to 10715 collected (net +1). F-001 (low, out of scope): a mutant R4 that reverses the payloads in `vector_two_up_page` (each band keeps its number but sits over the other puzzle's grid) survives this file (39 passed), `tests/test_book_pdf_two_up.py` (53 passed) and the behavioural tests of 7 more two-up files; the only red is the call-count scan `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`. The spy names each puzzle by argument order, not by the grid it draws.

**Orchestrator.** F-001 recorded, not carded under the cut bar (it needs no decision and blocks nothing); raised with the owner at the wave close as a candidate card, because a band printed over the wrong grid would reach a printed book unnoticed.
