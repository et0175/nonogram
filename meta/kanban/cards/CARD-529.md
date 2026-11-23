# CARD-529: test_book_pdf_band.py's glyph cache stops keeping whole uncropped arrays alive

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/529-glyph-cache-copy
**Worktree:** —
**Source:** roadmap wave 14, cut 2026-11-23 on the owner's "pick a no-decision wave from the backlog". IDEA-212 (CARD-218 review cycle 2 finding).
**Idea:** IDEA-212
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_band.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-23T09:35Z
**Closed:** 2026-11-23T11:41Z
**Actual:** 1c — ratio 1/1 = 1.0
**Merge commit:** bacbe8e7160b82f8094a24c640ed8ee9a6858754
**Blocked by:** —

## Why this card exists

In `tests/test_book_pdf_band.py`, `_set_once` is an unbounded `@lru_cache`. It returns `_cropped(...)`, a numpy slice: a view that keeps the whole uncropped base array alive. Measured on 2026-10-24 at CARD-218 review cycle 2: the cache held 666 entries and 24.4 MB for the rest of every session that touched the file. The backlog item's title says about 111 MB; the body's figure is 24.4 MB, and neither figure has been re-measured. The code shape was re-confirmed on 2026-11-18. The file already has a retention control naming these caches.

## What to implement

1. Re-measure on main: run the file alone and size `_set_once`'s retained memory by the bases its arrays keep alive (numpy `nbytes` of each `.base`), and state the figure.
2. Make the cache keep only what it returns, for example a `.copy()` of the cropped region, so the uncropped base can be freed. Keep the cache itself, since its speed is why it exists.
3. Re-measure retained bytes and the file's run time, before and after.

## Acceptance criteria

* **AC-1**: after the change, every cached array owns its data (no `.base`, or a base no larger than itself). Put that check inside the file's existing retention control. Control: removing the copy turns it red.
* **AC-2**: retained bytes before and after are stated, measured the same way both times. The file's run time does not grow by more than 5%.
* **AC-3**: no test result changes: the same tests pass before and after, and the net test count is 0.

## Guardrails

* **G-1**: tests-only card; nothing under src/ changes.

## Worktree notes

**2026-11-23, implementation (CARD-529 worktree).**

- Change: `_set_once` returns `_cropped(...).copy()` instead of the view; its docstring says why. The check went into the existing retention control, `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind.test_no_module_level_accumulator_retains_a_page_bitmap`: it sets one entry (`_set_once("529", BAND_FONT_PX)`) so the check is never vacuous, reads the cache store through `gc.get_referents(_set_once)`, asserts the store is non-empty, and asserts no cached array has a `.base` larger than itself. A paragraph was added to the class docstring; the 2026-10-24 figures in it are kept as history. Nothing under src/ changed. `tests/helpers/shared_fixture_controls.py`'s `_step` docstring still quotes the 2026-10-24 view/base figures as a measured limit of the walk. It is outside this card's Touches and was left alone.
- Measurement: a scratch pytest plugin (outside the repo) at `pytest_sessionfinish` reads `_set_once`'s cache dict through `gc.get_referents`. It sums `nbytes` of each value's `.base`, or of the value itself when it owns its data, counting each object once. Same plugin, same command (`tests/test_book_pdf_band.py` alone, unarmed), before and after. Two runs each:
  - before (main code): currsize 783, 0 of 783 own their data, view nbytes 26,742,429 B, **retained 123,623,682 B**; pytest time 16.37 s / 17.15 s.
  - after: currsize 784 (the extra one is the control's warm-up entry), 784 of 784 own their data, **retained 26,747,109 B**; pytest time 15.09 s / 14.59 s. Run time did not grow (AC-2).
  - Neither the backlog's "about 111 MB" nor the card's 24.4 MB was carried over. The 2026-10-24 figures were taken at currsize 666, and the cache has grown since.
- Controls (each restored, `cmp` against the kept copy, `git diff --stat` shows only the change):
  - removing `.copy()`, node id alone, gives red: `AssertionError: 1 of the 1 arrays `_set_once` caches are views of a larger array ... [((45, 104), 4680, 41064)]`.
  - removing the warm-up call, node id alone with a cold cache, gives red: `AssertionError: `_set_once`'s cache store could not be read`. The two pre-existing asserts in that test are unchanged by this card.
- Gate: `tests/test_book_pdf_band.py` whole, unarmed, `-rfs`: before 91 passed, 0 failed, 0 skipped. After 91 passed, 0 failed, 0 skipped (AC-3). Net collected count: 10695 before, 10695 after (net 0).

[Review 1/3] Score: 9.5, certified. Re-derived with two instruments: a session-end walk (main 783 entries, 0 owning their data, 123,623,682 B; head 784, all owning, 26,747,109 B) and tracemalloc bytes freed by `cache_clear()` (123,880,247 B and 26,977,831 B); 91 passed, 0 skipped; run time 15.04/14.62 s on main against 14.47/14.64 s at head; control 1 red alone and in the whole file, control 2 red alone with a cold cache; `.copy()` keeps dtype bool and every caller compares by value; the warm-up key is used nowhere else; the `gc.get_referents` read fails closed. F-001 (minor, recorded): `_step` in tests/helpers/shared_fixture_controls.py and `test_the_bound_on_a_numpy_arrays_contents_is_the_collectors` in tests/test_shared_fixture_controls.py still state the 2026-10-24 view figures in the present tense, and that test's assert message says the cache figure understates its base memory 4.5-fold; the general limit they describe still holds. F-002 (low): the retention class's docstring and second assert message still call `_set_once` out of scope and backlogged. F-003 (low): the byte instrument was a scratch plugin; the reviewer rebuilt it from the notes and got identical figures. F-004 (info): the cache read relies on CPython internals and fails closed.

**Merge gate (orchestrator).** `make test-gate BASE=main` on `90d530f2` (main merged into the branch first) answered SELECTION: 4646 passed / 15 skipped (unarmed) / 8 deselected / 1 xfailed / 0 failed in 19 min 15 s, then the marked run 4 passed. The remaining marked tests are owed at the wave close.
