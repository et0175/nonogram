# CARD-544: A two-up page whose grids are swapped under their bands fails a test

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/544-two-up-slot-swap
**Worktree:** ../PythonProject4-card-544
**Source:** roadmap wave 19, cut 2026-11-24 on the owner's "card both" (CARD-541 review F-001).
**Idea:** —
**Wave:** 98
**Created wave:** 98
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_two_up.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-24T19:06Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-541's review (F-001) ran mutant R4: `vector_two_up_page` in `src/nonogram/admin/book_pdf_generator.py` zips `reversed(payloads)`, so each band keeps its "Puzzle N" number but sits over the other puzzle's grid. It survived `tests/test_book_detail_page.py` (39 passed), `tests/test_book_pdf_two_up.py` (53 passed) and the behavioural tests of seven more two-up-touching files (295 passed; the one red was the static call-count scan `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`, not a behavioural catch). A printed book could therefore number its two-up puzzles over the wrong grids, and the solution pages would then point the reader at the wrong answer.

## What to implement

1. Verify first. Re-run mutant R4 on main against `tests/test_book_pdf_two_up.py` and record that it survives (or, if something now catches it, record which test and stop at AC-1).
2. If live, extend an existing test in `tests/test_book_pdf_two_up.py` (or its parametrize) so that it checks, for each slot of a two-up page, that the band's puzzle number sits above the grid of that same puzzle: use two puzzles whose drawn grids can be told apart (for example different sizes or different clues) and read the placement from the exported page itself, not from the arguments passed to a helper.
3. The fix is test-only. Do not change `vector_two_up_page` or any other source file.

## Acceptance criteria

- AC-1: the verdict on R4 is recorded in `## Worktree notes` with the command and result, backed by a run, never by reading code alone.
- AC-2: with the extended test, mutant R4 (reversed payloads) reds it, and a second mutant that swaps the two slots' geometry instead of their payloads reds it too; on the real code it is green. Record the three runs.
- AC-3: owner's test budget: change existing tests rather than add; net test count at most +1; report it.

## Worktree notes

### CARD-544 implementation (2026-11-24)

All pytest runs: `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest tests/test_book_pdf_two_up.py -o addopts= -q -rfs` from this worktree, 0 skips in every run. Every mutant was applied with `sed` to `src/nonogram/admin/book_pdf_generator.py` and reverted with `git checkout --`; `git diff -- src` was empty after each.

**AC-1 -- verdict on R4: it survives, and it is an equivalent mutant on every reachable input.** R4 = `zip((pair.upper, pair.lower), plan.numbers, reversed(payloads), strict=True)` in `vector_two_up_page`.
- Real code, file at HEAD: `53 passed`. Under R4, file at HEAD: `53 passed` (exit 0). It survives.
- Why nothing reading the page can catch it, measured rather than read: a probe (`scratchpad/probe.py`, not committed) built the interior of a two-up pair through `interior_pages` for the tier pairs (easy, easy), (easy, Easy), (guess, hard), (Hard, guess) and hashed every operators page's decoded content streams. Real code: `360cac49fc8e59fa`, `360cac49fc8e59fa`, `e56087821a81e4c8`, `e56087821a81e4c8`; under R4: the same four hashes. The operators R4 writes are identical to the real ones.
- What that run shows: the slot's grid and clues come from `pair.upper`/`pair.lower` (the `Layout`), not from the payload; the payload feeds only `band_identity(number, payload.difficulty)`, and a pair only forms when both payloads have the same `tier_of_record` (`_pairable_tier`, compared with `is`). So reversing the payloads swaps two identical tier words. The card's premise ("each band sits over the other puzzle's grid") does not hold for R4 itself; the real risk is a band paired with the other slot's layout, which M2 and M3 below produce.

**AC-2 -- the extended test.** `TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand::test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two` now prints a pair told apart by clues: puzzle one is `_puzzle(**_SMALL_PAIR)` (single-cell runs, no "2"), puzzle two is the new fixture `_paired_runs_puzzle` (same 13x13-cell drawing, so the band geometry the class pins does not move, but row 0 and column 0 carry runs of two). The test reads the exported page's text layer with poppler (`_clues_under_each_band`: each "Puzzle N" band row, and the clue digits from that row down to the next band or, for the lower slot, to the footer rule) and asserts `{1: digits of puzzle one, 2: digits of puzzle two}`. Nothing is read from the arguments of a helper. The class attribute `PUZZLES` feeds `_page`, which `test_the_two_bands_are_not_the_same_line` shares.
- Real code, extended file: `53 passed` (exit 0).
- R4, extended file: `53 passed` (exit 0). It survives, as the AC-1 hash run predicts: no test reading the page can red an equivalent mutant. **AC-2's "R4 reds it" is therefore not met, and cannot be.** The owner should rule whether R4 is closed as equivalent.
- M2, slot geometry swapped (`zip((pair.lower, pair.upper), plan.numbers, payloads, strict=True)`), extended file: `3 failed, 50 passed`: `TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand::test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two` (at its band-ink assertion, line 1231, before the new one), `TestBookPdf_TwoUpPageNumbersInOrderEachWithOwnBand::test_the_numbers_follow_the_pages_before_this_one`, `TestBookPdf_ABandIsReadInTheMediumItWasWritten::test_the_two_up_page_the_writer_draws_carries_both_bands_upper_first`.
- M3, control for the new assertion: `compute_pair_layout`'s two clue arguments swapped in the page walk (bands still read 1 then 2, top to bottom, but each sits over the other puzzle's grid; this is the "band over the wrong grid" the card describes). File at HEAD: `2 failed, 51 passed` (`TestBookPdf_PairJustAboveTwoUpMinimumShares::test_the_pair_prints_on_one_page`, `TestTwoUp_ThresholdsRederivedFromTheOneLineFooter::test_n_cells_pair_at_the_shared_cell_and_n_plus_one_print_as_two_pages`, both on unequal-size pairs; the AC-251 test stayed green). Extended file: `3 failed, 50 passed`, the same two plus `test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two`, red at the new assertion (line 1252): `{1: Counter({'1': 10, '0': 8, '2': 6})} != {1: Counter({'0': 14, '1': 10})}`.

**AC-3 -- test budget.** One existing test extended, no test added: 53 passed before, 53 after. Net test count **0**. New module helpers (not tests): `_FOOTER_RULE_PT`, `_clues_under_each_band`, `_clue_digits`, `_paired_runs_puzzle`.

[Review 1/3] Score: 9.5, certified. Re-derived with my own runs (`-o addopts= -rfs`, 0 skips; every mutant reverted with `git checkout -- src`, `git status --short` clean after each). Real code: `tests/test_book_pdf_two_up.py` 53 passed; main's file and the branch's both define 45 test functions and collect 53, so the net test count is 0 (AC-3). R4 (`reversed(payloads)` in `vector_two_up_page`): 53 passed, and it is an equivalent mutant. The function reads the payload only for `band_identity(number, payload.difficulty)`, which prints `tier_of_record(...).label`. The drawing and clues come from `pair.upper`/`pair.lower`, and the footer label and pointer come from `plan.numbers`. `puzzle_pages` pairs two puzzles only when `_pairable_tier(first) is not None and is _pairable_tier(second)`. My own probe hashed every interior page (operators or pixels) of a 3-puzzle book built through `interior_generator(_book()).interior_pages`, for the tier pairs (easy,easy), (easy,Easy), (guess,hard), (Hard,guess), (medium,MEDIUM) and (easy,hard). Real code gave the same hashes on two runs, and R4 gave the same hashes on all six. M2 (slot geometry swapped) changed all six, so the probe can tell pages apart. AC-2's R4 clause cannot be met as written: its premise, CARD-541 F-001's "band over the other grid", describes M3, not R4. M3 (`compute_pair_layout`'s clue arguments swapped): 3 failed, 50 passed, and `test_the_upper_band_reads_puzzle_one_and_the_lower_puzzle_two` fails at the new assertion (line 1252), which is the only assertion in its class that catches it. The new helper fails loudly without poppler (`word_boxes` raises `RuntimeError`) rather than skipping. F-001 (low, open): the owner should close AC-2's R4 clause as equivalent. F-002 (low, open): the new assertion sits under the existing `if isinstance(raw, ContentStream)` branch, so it would silently stop running if the page went back to raster; the page is vector today.

**Orchestrator.** F-001: AC-2's R4 clause is closed as an equivalent mutant. The card's premise was the orchestrator's reading of CARD-541's review F-001, and two runs (the implementer's probe and the reviewer's six-tier-pair probe) show that R4 leaves every interior page unchanged, because a pair shares one tier and the payload feeds only the band's tier word. The defect the card meant, a band printed over the other puzzle's grid, is M3, and the extended test catches it at its new clue assertion. F-002 (the assertion runs only inside the vector branch) is recorded, not carded: the page is vector today, and a return to raster would be a card of its own.
