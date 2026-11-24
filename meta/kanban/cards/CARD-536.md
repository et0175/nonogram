# CARD-536: The longest-side filter minors from CARD-190, verified first and fixed only where still live

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/536-side-range-minors
**Worktree:** ../PythonProject4-card-536
**Source:** roadmap wave 17, cut 2026-11-24 on the owner's "pick the next no-decision wave from the backlog". IDEA-154.
**Idea:** IDEA-154
**Wave:** 96
**Created wave:** 96
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/puzzle_review.py (comments only, if any), tests/test_admin_filter_side_range_and_name.py
**UI surface:** —
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-11-24T07:52Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-190's review left five minors (F-002/F-003, O-001/O-004/O-005): no test pins `PuzzleReviewService._side_bounds`' 10..30 edge (mutants E1/E4, which turn `MIN_SIZE <= low` or `high <= MAX_SIZE` into a strict `<`, survived); the AC-4 API test does not assert the store; the pagination test passes under both meanings of the filter; a stale "either side" comment in `puzzle_review.py`; and no FR traces the review filter. Re-checked on main at the cut: `tests/test_admin_filter_side_range_and_name.py` has grown since (for example `test_an_open_bound_means_the_supported_limit`, `test_a_longest_side_range_asks_about_max_width_height_not_either_side`, `test_the_longest_side_range_pages_its_own_members_and_counts_them`), and the comment by the longest-side branch now reads "max(width, height), not \"either side\"". So some items may be moot.

## What to implement

1. Verify first. For each of the first four items, record live or moot: run E1 and E4 as mutants of `_side_bounds` against `tests/test_admin_filter_side_range_and_name.py`; read the AC-4 API test (`TestPuzzlesApi_SizeRangeUsesLongestSide`) and the pagination tests against a mutant that filters by either side; grep `src/nonogram/admin/puzzle_review.py` for any comment that still describes the filter as "either side".
2. Fix only the live ones, preferring a changed assert in an existing test to a new test.
3. The fifth item (no FR traces the filter) is out of scope: `requirements.yml` and `trace.yml` are written only by the architect pass. Record it in the notes, not here.

## Acceptance criteria

- AC-1: each item has a recorded verdict, live or moot, backed by a run (a mutant, a probe or a test), never by reading code alone. Record the command and its result in `## Worktree notes`.
- AC-2: every live item is fixed, and its fix has one control that fails when the fix is reverted.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### Verdicts (2026-11-24, worktree run)

Mutant runner: `/private/tmp/claude-501/card536/mutant.py <NAME>` (scratch, not committed). It applies one mutant with a `count(old) == 1` assert per replacement, runs pytest with `-o addopts= -rfs -q`, and restores the file. `git diff --stat -- src/` was empty after every run.

- F-003 (E1/E4 survive on `_side_bounds`): **moot**. E1 (`MIN_SIZE <= low` to `MIN_SIZE < low`) against `tests/test_admin_filter_side_range_and_name.py`: 10 failed, 18 passed. E4 (`high <= MAX_SIZE` to `high < MAX_SIZE`): 3 failed, 25 passed, among them `test_an_open_bound_means_the_supported_limit` and `test_a_row_outside_the_supported_range_belongs_to_no_longest_side_range` (`ValueError: Size range must stay within 10-30 cells`). No change.
- F-002 (AC-4 API test does not assert its store): **live**. Mutant STORE puts the `admin_app` fixture on the sqlite store (DATABASE_URL set to sqlite, `nonogram.db.session_scope` patched). `TestPuzzlesApi_SizeRangeUsesLongestSide::test_the_api_lists_only_the_15x12` still passed (1 passed, exit 0).
  Fix: that test now asserts `service._session_factory is None` before it adds rows.
  Control: STORE against the fixed test gives 1 failed, with `assert <function sqlite_session_scope.<locals>.scope ...> is None`.
- O-001 (pagination test passes under both meanings): **live** for `test_the_page_reads_from_and_to_and_keeps_them_in_pagination`. Mutant EITHER filters by either side in both store branches (memory: `any(low <= s <= high for s in sides)`; DB: `or_` of the two `between`s). Against the AC-4 class, the AC-3 class, that test and `test_the_longest_side_range_pages_its_own_members_and_counts_them`: 4 failed, 1 passed, and the one that passed was this test. Its range 25-30 cannot tell the two meanings apart, because a side of 25..30 is also the longest side within the supported range. The AC-3 tests and the store-level pagination test already failed under EITHER, so the property itself was pinned.
  Fix: the same test now uses three 10x10 rows and one 20x30 row at `size_from=10&size_to=20`, and asserts that `butterfly3.jpg` is not listed.
  Control: EITHER against the fixed tests gives 5 failed, 0 passed. This test fails on `assert 'Puzzles (3 total)' in ...`, because either-side counts 4.
- O-004 (stale "either side" comment in `puzzle_review.py`): **moot**. A `tokenize` pass over the file's COMMENT and STRING tokens finds one comment with "either side". It sits by the in-memory longest-side branch of `filter_puzzles` and reads `max(width, height), not "either side"`, which contrasts the filter with "either side" and does not describe it that way. No change.
- O-005 (no FR traces the review filter): **out of scope**. `requirements.yml` and `trace.yml` are written only by the architect pass, so it is recorded here for that pass.

src/ is unchanged. The only changed file is `tests/test_admin_filter_side_range_and_name.py`, where two existing tests were edited and none were added.

Gate (unarmed, `-o addopts= -rfs -q`): `tests/test_admin_filter_side_range_and_name.py`, `tests/test_book_select_tabs.py`, `tests/test_puzzles_list_pagination.py`, `tests/test_card_066_status_filter.py`, `tests/property/test_longest_side_buckets.py`, `tests/test_card_063_limits.py`, `tests/test_card_065_follow_ups.py`. Result: 141 passed, 0 failed, 0 skipped. Collected count (`--collect-only -q -o addopts= tests/`) is 10713 before and 10713 after, so the net change is 0.

[Review 1/3] Score: 8.5, not certified (one high finding). I re-derived every verdict with my own mutants, restoring each file by copy. STORE (`admin_app` on sqlite): the AC-4 API test fails on the branch (1 failed, and 1 failed/27 passed for the whole file) and passes on main's test (1 passed), so F-002 is live and fixed. EITHER (either-side matching in both store branches): the pagination test fails on the branch (1 failed; whole file 10 failed/18 passed) and passes on main's test (1 passed; whole file 9 failed/19 passed), so O-001 is live and fixed. The new butterfly3.jpg assert discriminates; the old "dot" assert could never fail. O-004 is moot: the one "either side" comment is a contrast. F-003 is not moot (F-001, high). The notes ran the card text's tightening mutants, which do die (branch 11/17 and 2/26; the notes' 10/18 and 3/25 are main's test file, F-002 low). CARD-190's own E1 (`high <= MAX_SIZE + 1`) and E4 (`MIN_SIZE - 1 <= low`) still survive the five covering files at 125 passed each, because the impossible-range parametrize's out-of-range cases become inverted pairs once the open bound is filled in. Suggested fix: swap them for `(None, MAX_SIZE + 1)` and `(MIN_SIZE - 1, None)` (net 0). Gate set: 141 passed, 0 skipped. Test file: 28 collected. Orchestrator's note: the card's Why defined E1/E4 the wrong way round (tightening, not CARD-190's loosening); that was the orchestrator's wording, not the implementer's.

**Fix round 1.** This corrects the F-003 verdict above: F-003 was **live**, not moot, and it is now fixed. My first pass ran tightening mutants. CARD-190's review defines E1 and E4 as loosening mutants of `_side_bounds`: LE1 makes the high check `high <= MAX_SIZE + 1`, and LE4 makes the low check `MIN_SIZE - 1 <= low`. Mutant runner: the same scratch `mutant.py`, which now also holds LE1 and LE4. `git diff --stat -- src/` was empty after every run.
- Reproduced on the branch before the fix, against `tests/test_admin_filter_side_range_and_name.py`: LE1 28 passed (exit 0), and LE4 28 passed (exit 0). Both survive. Cause: in `test_an_impossible_longest_side_range_is_reported_too`, the cases `(MAX_SIZE + 1, None)` and `(None, MIN_SIZE - 1)` become 31..30 and 10..9 once the open bound is filled in. Those pairs are inverted, so the inverted check raises whether or not the range check is right.
- Fix: that parametrize now uses `(None, MAX_SIZE + 1)` and `(MIN_SIZE - 1, None)`, which fill in to 10..31 and 9..30. Neither pair is inverted, so only the range check can reject them. `(25, 15)` and `(5, 5)` are kept. The case count is unchanged.
- Control: LE1 gives 1 failed, 27 passed, in `test_an_impossible_longest_side_range_is_reported_too[longest_side_range0]` with `Failed: DID NOT RAISE ValueError`. LE4 gives 1 failed, 27 passed, in `test_an_impossible_longest_side_range_is_reported_too[longest_side_range1]` with `Failed: DID NOT RAISE ValueError`.
- The strict-mutant figures above came from main's copy of the file. Re-derived on this branch with the fix applied: strict E1 gives 11 failed, 17 passed; strict E4 gives 2 failed, 26 passed.
- Gate (same seven files, unarmed, `-o addopts= -rfs -q`): 141 passed, 0 failed, 0 skipped. Collected tests: 10713, so the net change for the card is still 0. src/ is unchanged.
