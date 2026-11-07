# CARD-397: The admin solver's browser files stop paying per-test server and page setup — measured first, kept only if it saves

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-07 ("I'd do a+c, after measurement"; memory gate-time-cuts-a-and-c): C = pure speed, NO coverage move, each saving proven by a before/after --durations on the file alone. Measurement: ~/Documents/nonogram-reviews/suite-profile-2026-11-07/gate-card388-durations.txt (contended full run; shares only). Owner rule: pure speed, order independence guarded by tests/test_browser_fixture_scope.py.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-395
**Touches:** tests/conftest.py, tests/test_puzzle_solver_page.py, tests/test_browser_fixture_scope.py, tests/test_puzzle_editor_ui.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

<!-- MEASURE-FIRST. CARD-235 (meta/profiling/card-235-browser-teardown.md) already measured that one new_context + new_page + close costs 57 ms and that widening the page scope buys ~24 s at its date; the bulk of the old teardown was a 0.5 s serve_forever poll, fixed. In the CARD-388 gate run the admin solver / editor family (16 files, 586.5 s) spends 91.6 s in setup + teardown and 494.9 s in CALL (the sweeps and plants themselves). The honest ceiling of this card is therefore the setup+teardown (about 92 s summed, about 70 s solo), and only the part that is the per-test server start and page creation, not the fixtures' real work. If the measurement says less than the AC-4 floor, the card closes as a recorded null. -->
## Why this card exists

The admin solver browser tests are 12.7 % of the suite (586.5 s over 16 files). The public-player browser family that was the larger part of the browser time (1270 s) is being retired (CARD-R), so it is deliberately NOT in this card's scope. For the admin family, per-test cost splits as 494.9 s call, 71.4 s setup, 20.2 s teardown. A module-scoped Chromium page and server, with the page's state reset between tests (storage cleared, route listeners removed, viewport restored, console/error collectors emptied), could remove most of the 91.6 s, at the cost the CARD-235 note names: order dependence. `tests/test_browser_fixture_scope.py` (reverse order, shuffled order, every test alone, a failure does not cascade) exists to hold exactly that, and with CARD-395 its two ordering probes run at the wave close and are lifted at any gate that edits `tests/conftest.py`.

## What to implement

1. Before any change: profile each of the 16 files alone with `--durations=0` (three runs, idle host) and write setup, call, teardown per file to `meta/profiling/card-397-browser-setup.md`. Decide from that table, in the card, which files have a per-test setup large enough to matter (floor: AC-4) and which fixtures it comes from (`live`, `browser_page`, a per-file `_build_app`).
2. For the files above the floor only: move the server and the Chromium page to module scope with a `reset_page_state` step that restores every piece of state a test of that file can leave behind. The reset's list of state is DERIVED, by an `ast` walk of the file's tests for the browser APIs they call that mutate the page (`set_viewport_size`, `add_init_script`, `route`, `evaluate` of storage writes, `on(...)`), and a test asserts the reset covers each.
3. Keep `browser_page` function-scoped for any file where the derived list contains a mutation the reset cannot undo (and say which).

## Acceptance criteria

* **AC-1** (order independence still holds): `tests/test_browser_fixture_scope.py` passes unmodified and its reverse-order, shuffled-order, alone and no-cascade cells run against each converted file. (test: the existing cells; the probe-file list in that module gains the converted files.)
* **AC-2** (the reset is complete and a plant proves it): for a converted file, a test that leaves a stored value, a viewport, a route and a listener behind is followed by a test that would read them; the reset removes all four. A reset with one clause removed reds a named cell per clause. (test: new cells in `tests/test_browser_fixture_scope.py`.)
* **AC-3** (no claim moves): the converted files' node ids, assertions and plants are unchanged (diff shows fixture-scope lines only); every test that went red in the planted-failure cells before still goes red. (evidence: node-id set difference empty; the files' own plants.)
* **AC-4** (measured, with a floor): per converted file, before/after `--durations` on the file ALONE, three runs each; a file is kept converted only if setup+teardown fell by at least 30 % AND the file's total fell by at least 3 s. If NO file clears the floor, the card closes as a recorded null with the table, and `meta/profiling/card-397-browser-setup.md` is the deliverable.
* **AC-5** (no hidden cost): the Chromium process count and peak RSS over the converted files do not rise (measured once, pasted).

## Guardrails

* **G-1** Pure speed: no test deleted, merged, skipped or loosened (G-4).
* **G-2** Not the public-player files (CARD-R retires them); not `player/`.
* **G-3** `tests/conftest.py` is a hotspot: the card does not run beside CARD-320, CARD-387 or CARD-395.

## System contract

* ADR-0038/R7-R8 — the admin player is driven in real Chromium (check: AC-1)
* CARD-235 — no file's page scope changed because it bought a sixth of the order-dependence risk; this card changes that only where AC-4 proves it is worth it

## Worktree notes

(none yet)
