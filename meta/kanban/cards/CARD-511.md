# CARD-511: At 600x900 the board no longer moves when a puzzle is solved

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/511-solve-shift-600
**Worktree:** ../PythonProject4-card-511
**Source:** roadmap wave 8, cut 2026-11-21 on the owner's "yes, start wave 8". IDEA-223, recorded by CARD-507's implementer and review.
**Idea:** IDEA-223
**Wave:** 87
**Created wave:** 87
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js (if the banner's reveal needs it), tests/test_puzzle_solver_maybe.py
**UI surface:** puzzle player (compact layout, solved banner)
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-21T05:47Z
**Blocked by:** —

## Why this card exists

CARD-507 measured, at 600x900 in the compact layout, that the board moves dx +12.656, dy +27.203 px when a puzzle is solved, for all eight names it tried, including a 10-character one; identical before and after CARD-507, so pre-existing. At 1100x700 and 390x844 the board holds still (CARD-507's AC-1 and test_wraps). 600x900 is a portrait tablet. The player is the shared admin player and the public site's copy (one source of truth: change the admin static files only).

## What to implement

1. Reproduce in Chromium: the board's bounding box before and after solving at 600x900, and find which box change moves it (the banner appearing, a toolbar row wrapping, a column changing width). Record the cause measured, not guessed.
2. Fix it at that cause so the board does not move on solve at 600x900, without moving it at the widths that already hold (1100x700, 390x844), and without changing the layout before solve.
3. Hold it by extending an existing test (CARD-507's test_wraps or its neighbour in tests/test_puzzle_solver_maybe.py) with the 600x900 viewport, rather than adding a test.

## Acceptance criteria

* **AC-1**: at 600x900 the board's box is the same (within 0.5 px) before and after solve, for a short and a long name; control: the base CSS reds it with the measured shift.
* **AC-2**: at 1100x700 and 390x844 the existing no-move assertions still hold; the pre-solve layout at all three sizes is unchanged (board box within 0.5 px of base).
* **AC-3**: net test count 0 (a parameter, not a test, if the viewport is a param; report it, and if a node id is renamed record it in tests/test_browser_fixture_scope.py's `RENAMED_SINCE_BEFORE` as a move).

## Guardrails

* **G-1**: the browser-family census (tests/test_browser_fixture_scope.py) is a frozen registry outside impact scope: a new or renamed browser node id reds it at the gate. Re-derive, never paste the printed figure.
* **G-2**: admin static files only; nothing under player/ (the public site copies them at build).
* **G-3**: the owner validates renders after merge: leave before/after screenshots at the three sizes in ~/Documents/nonogram-reviews/CARD-511/.

## Worktree notes

### Implementation (2026-11-21)

**Cause, measured (step 1).** A Playwright probe under /private/tmp/claude-501/card511/ (it asserts at import that `nonogram` resolves to this worktree) read the box of every element before and after the solving click, on GRID (15x15), with "Lighthouse" and the 120-character words name. At 600x900 the base CSS gives dx +12.65625, dy +27.203125 for both names (premise holds). What changes on solve:
- `syncLine` hides Line (`lineOffered()` is false once the player is locked), and the row's gaps go from 4 to 8 px; row 1 (brush slot, history buttons, zoom) then ends at 525 px, leaving 51 px of the 568 px row.
- The probe bar (`flex: 1 1 0` in the portrait compact block, min-content one 44 px button because it wraps) moves up into those 51 px; Show grid, which appears on solve, wraps under Probe there, so that row is 96 px tall.
- The counters lose their row partner and drop to a third row (24.8 px tall, was 49.6 beside the bar).
- The toolbar grows 101.59 -> 128.80 px (+27.203), the stage gets that much shorter, and the board, fitted to the stage, shrinks 565.14 -> 539.83 px wide and is centred (dx +12.656).
The banner itself does not cause it (it sits in the brush slot's box, as at 390).

**Change.** admin.css, `@media (max-width: 600px) and (orientation: portrait)`: new rule `.player-toolbar.is-solved .player-probe { flex-wrap: nowrap; }` with a CARD-511 comment. Solved, the bar's min-content is Probe + Show grid (96 px), which does not fit the 51 px, so the bar keeps its row beside the counters. Only the solved state is selected, so the unsolved layout cannot change. solver.js is untouched.

**After (AC-1, AC-2), same probe.** 600x900, 1100x700 and 390x844, both names: dx 0, dy 0. Toolbar at 600x900 solved: 101.59 px. Pre-solve board box identical to base at all three sizes, both names (0 differences; exact, not only within 0.5 px).

**Portrait sweep (beyond the card, recorded).** GRID, "Lighthouse", height 900, widths 391-460 step 3 and 470-590 step 10 (37 viewports), base vs after; pre-solve board box: 0 differences.
- 400-418: base dy +19.203, after 0 (fixed as a side effect).
- 421-451: base dy +46.406, after dy +27.203. NOT fixed. Cause measured at 440: the probe bar's share of row 2 is 92 px, Probe + Show grid need 96, so with the new rule the counters wrap to a row of their own (base: Show grid stacked under Probe, plus the same). Fixing it needs room for Show grid that row 2 does not have there (for example Show grid taking Line's or Probe's slot once solved), which is an owner-visible choice; candidate idea for the backlog.
- 391-397, 454-590: 0 in both.
An earlier coarser run (step 10, plus 412x844, 480/540/600x844, 600x1024, 600x700, both names) agrees: 600x844, 600x1024 and 600x700 moved in base (dx +13.625 / 0 / +9.266, dy +27.203) and give 0 after.

**Tests (AC-1..AC-3, net 0).**
- `TestSolverMaybe_BoardDoesNotMoveOnSolveAtAnyWidth::test_sweep`: `_SWEEP` gains `(600, 900)`, so it solves "Lighthouse" (the short name) there too; `checked == len(_SWEEP) == 29` (was 28). No node id changes.
- `TestSolverMaybe_LongNameBannerWrapsInsideTheToolsWidth::test_wraps`: viewport `(1440, 900)` became `(600, 900)` (the long names). 1440x900 is the same desktop rule as 1100x700, which stays, and test_sweep still solves the short name at 1440. Two node ids renamed: `test_wraps[chromium-1440-900-words|one-token]` -> `[chromium-600-900-...]`, recorded as moves in tests/test_browser_fixture_scope.py's `RENAMED_SINCE_BEFORE` (CARD-511). Docstrings say so.

**Controls.**
1. Base admin.css (the change is one added rule, so this is the mechanism removed): `test_sweep` red, `AssertionError: 600:+12.6562,+27.2031`; `test_wraps[chromium-600-900-words]` and `[...-one-token]` red on the board-shift assert, `AssertionError: (12.65625, 27.203125)` / `assert (30.078125, 336.390625) == (17.421875, 309.1875)`; the other 4 test_wraps cases passed. admin.css copied back and `cmp`-checked.
2. Census without the two rename entries (HEAD's test_browser_fixture_scope.py): `test_the_family_collects_exactly_what_card_217_measured` red, `AssertionError: tests added: [...test_wraps[chromium-600-900-one-token]', ...test_wraps[chromium-600-900-words]'] are collected in the browser family but recorded nowhere`. File copied back and `cmp`-checked.

**Screenshots (G-3).** ~/Documents/nonogram-reviews/CARD-511/before/ and .../after/: 600x900, 1100x700 and 390x844, short and long name, unsolved and solved (12 each).

**Load note.** The machine's load average was ~64 during this work; one gate attempt of test_sweep failed on `Page.goto: Timeout 30000ms` (not an assertion) and passed when rerun alone.

[Review 1/3] Score: 9.5, nothing gating, certified. Re-measured with the reviewer's own probe: base 600x900 dx +12.656, dy +27.203, both names, fix 0,0 (600x844, 600x700, 600x1024 likewise); no overflow at any portrait width 320-600 (probe bar's scrollWidth − clientWidth 0, no sideways scroll); pre-solve boxes identical to base at all 27 viewports; base-CSS control reds `test_sweep` and both `test_wraps[chromium-600-900-*]`; census 33 passed; worktree collects 10689 (net 0). F-001 (low): a second partly-fixed band at 327-339 px (base dy +52.0, now +24.797), not in the notes; it joins the backlog idea with 421-451. F-002 (low): `test_wraps` no longer checks a long name at 1440x900 (1100x700 shares the rule; 1440 measured 0,0 today), accepted for the net-0 budget. F-003 (info): a `RENAMED_SINCE_BEFORE` entry starts on the previous entry's closing line. F-004 (info): no test holds the probe bar inside the toolbar now that it cannot wrap; no overflow measured.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 7651 passed / 30 skipped (the unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 12 deselected / 1 xfailed / 0 failed, then 6 passed marked.
