# CARD-531: The admin tab icon ships in the wheel

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/531-favicon-package-data
**Worktree:** ../PythonProject4-card-531
**Source:** found 2026-11-23 by the wave 14 close: commit 7a21d0ba (owner test notes 2026-11-23, no card) added src/nonogram/admin/static/favicon.png, which no package-data glob in pyproject.toml names. Added to wave 14 because it reds the wave close.
**Idea:** —
**Wave:** 93
**Created wave:** 93
**Deferred waves:** 0
**Depends on:** —
**Touches:** pyproject.toml, scripts/impact_set.py, tests/test_puzzle_solver_page.py
**UI surface:** —
**Review score:** 9.5 (cycle 3/3 - CERTIFIED)
**Started:** 2026-11-23T13:43Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_puzzle_solver_page.py::TestPlayerAssets::test_every_admin_asset_ships_in_the_wheel` fails on main with `assert ['static/favicon.png'] == []`. Commit 7a21d0ba gave the public site's pages one tab icon, `src/nonogram/admin/static/favicon.png`, which `player/assemble.py` copies from the checkout into the site. The `"nonogram.admin"` package-data list in `pyproject.toml` names `templates/*.html`, `static/*.css` and `static/*.js` only, and the test holds that list equal to everything under `admin/static`. No admin page links the PNG (the admin's icon is an inline SVG in `base.html`), so the missing glob breaks no served page; it breaks the test's invariant.

## What to implement

1. Add `"static/*.png"` to the `"nonogram.admin"` package-data list, and extend the comment above it to say the tab icon ships the same way.
2. No new test. The existing test is the control: it fails before the change and passes after.

## Acceptance criteria

- AC-1: `test_every_admin_asset_ships_in_the_wheel` passes, and fails again if the new glob is removed.
- AC-2: No other package-data entry changes, apart from AC-3's new `"nonogram.web"` entry.
- AC-3 (added 2026-11-23 on the owner's word, from review F-001): `src/nonogram/web/static/metadata.js` ships in the wheel through a `"nonogram.web"` package-data entry, and the same wheel test holds `web/static` to it: red without the entry, green with it.

## Worktree notes

**Implementation (orchestrator, one line).** Added `"static/*.png"` to the `"nonogram.admin"` package-data list and extended its comment. `test_every_admin_asset_ships_in_the_wheel`: 1 failed before the change, 1 passed after. `tests/test_puzzle_solver_page.py -m "not browser"`: 35 passed. A real wheel build was not run: the venv has no setuptools, and an isolated build needs the network. No test added or removed (net 0).

[Review 1/3] Score: 9.5, certified. Re-derived: the wheel test passes on the branch; with the glob removed it fails listing only `static/favicon.png`. AC-2 holds: one glob added, no other package-data entry changed. ADR-0006/R1, ADR-0006/R2, ADR-0038/R5, ADR-0038/R7 and ADR-0042/R4 hold, and their tests pass. F-001 (low, pre-existing, recorded, not carded): `src/nonogram/web/static/metadata.js` is served by `web/handler.py` and loaded by both `web/pages.py` form pages, but no package-data glob names it, so a built wheel would 404 it; the wheel test covers only `admin/static` and `admin/templates`. F-002 (info): no real wheel built (no setuptools offline); fnmatch matches setuptools for flat names.

**Merge gate, round 1 (orchestrator).** `make test-gate BASE=main` answered FULL (pyproject.toml changed): 2 failed / 10680 passed / 30 skipped (unarmed) / 1 xfailed in 40 min 45 s. Both reds are `tests/test_impact_set.py::TestImpactSet_EveryShippedAssetHasADerivation` (`test_the_known_asset_types_equal_the_shipped_asset_types`: "shipped but no rule: ['.png']"; `test_every_static_file_has_a_derivation_that_is_not_full`). Same root cause as the card: 7a21d0ba put the first `.png` under `src/`, and `scripts/impact_set.py`'s `ASSET_RULES` must name every shipped asset type. Not caused by the glob.

**Fix round 1 (orchestrator).** Added `".png": "named"` to `ASSET_RULES`: the icon is bytes no code executes, read by tests that name it, as `.ttf` is. The two tests: 2 failed without the rule, 9 passed (the class) with it. `impact_set.py src/nonogram/admin/static/favicon.png` now derives 51 test files instead of FULL. No test added or removed (net 0).

[Review 2/3] Score: 9.5, certified. Re-derived: without `".png": "named"` the class gives 2 failed / 7 passed, with it 9 passed; impact, shared-UI site and TestPlayerAssets 272 passed. "named" is right: `player/assemble.py` copies the PNG byte for byte, and `test_player_shared_ui_site.py` checks the copy, so it is not "inert"; no test executes it. The 51 files: the 46 every named admin asset gets, plus 5 through `player/assemble.py`. F-003 (medium): the new pyproject comment and this card's Why said every page links the icon and a wheel would 404 it; no admin page links it (`base.html` has an inline SVG). F-004 (low): the ASSET_RULES comment left out `player/assemble.py`. F-001 (low, pre-existing, recorded) carried.

**Fix round 2 (orchestrator).** F-003 and F-004 fixed, comments and Why only; checked first with a grep: `/favicon.png` is linked only by `player/*.html` and `player/assemble.py`'s page template. No code change.

**Fix round 3 (orchestrator, owner's request: "also fix the metadata.js one").** F-001 folded in, because both changes force a FULL gate through pyproject.toml; the round-2 gate was stopped unfinished. `test_every_admin_asset_ships_in_the_wheel` now also lists `nonogram/web/static` against a `"nonogram.web"` package-data entry (name kept: only the pyproject comment refers to it). Widened test without the entry: 1 failed (`nonogram.web: static/metadata.js` unshipped); with `"nonogram.web" = ["static/*.js"]`: 1 passed. `test_puzzle_solver_page.py`, `test_impact_set.py` and `test_web_server.py` (not browser): 418 passed. Net tests 0.

[Review 3/3] Score: 9.5, certified. Re-derived: the widened test passes on 1aff636b; without the `"nonogram.web"` line it fails listing `nonogram.web: static/metadata.js`; with `static/*.css` dropped it fails listing `nonogram.admin: static/admin.css`; a missing or empty entry fails, not passes. The F-003/F-004 rewordings match the code. F-001, F-003, F-004 closed. F-005 (low, recorded): the test's package roots are a hand-written table, so a static folder in a third package would go unchecked; every tracked non-`.py` file under src is covered today. F-006 (info): the name says admin, the docstring says web too.

**Merge gate, round 3 (orchestrator).** `make test-gate BASE=main` on `9c30652e` (main fb89f9e5 merged in) answered FULL: 2 failed / 10680 passed / 30 skipped (unarmed) / 1 xfailed in 34 min 27 s. Both reds (`test_public_player.py::test_the_player_tree_is_static_and_adds_nothing_to_the_package`, `test_public_player_pages.py::test_the_two_pages_add_nothing_to_the_package_and_no_toolchain`) refuse the text `player/` anywhere in pyproject.toml (ADR-0041/R3), and the round-2 comment named `player/assemble.py`. Fix round 4: the comment says "the public site's assembler" instead; comment-only. Re-run instead of a fourth FULL: the 2 reds plus `TestPlayerAssets`, 7 passed; every non-browser test file that reads pyproject.toml (21 files), 1698 passed / 13 skipped (unarmed DB) / 0 failed. The wave close that follows this merge runs the bare full suite on main.
