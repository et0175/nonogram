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
**Touches:** pyproject.toml, scripts/impact_set.py
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-23T13:43Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_puzzle_solver_page.py::TestPlayerAssets::test_every_admin_asset_ships_in_the_wheel` fails on main with `assert ['static/favicon.png'] == []`. Commit 7a21d0ba gave every page one tab icon, `src/nonogram/admin/static/favicon.png`. The `"nonogram.admin"` package-data list in `pyproject.toml` names `templates/*.html`, `static/*.css` and `static/*.js` only, so a built wheel has no icon to serve. An editable install, which is how the checkout runs, still finds it.

## What to implement

1. Add `"static/*.png"` to the `"nonogram.admin"` package-data list, and extend the comment above it to say the tab icon ships the same way.
2. No new test. The existing test is the control: it fails before the change and passes after.

## Acceptance criteria

- AC-1: `test_every_admin_asset_ships_in_the_wheel` passes, and fails again if the new glob is removed.
- AC-2: No other package-data entry changes.

## Worktree notes

**Implementation (orchestrator, one line).** Added `"static/*.png"` to the `"nonogram.admin"` package-data list and extended its comment. `test_every_admin_asset_ships_in_the_wheel`: 1 failed before the change, 1 passed after. `tests/test_puzzle_solver_page.py -m "not browser"`: 35 passed. A real wheel build was not run: the venv has no setuptools, and an isolated build needs the network. No test added or removed (net 0).

[Review 1/3] Score: 9.5, certified. Re-derived: the wheel test passes on the branch; with the glob removed it fails listing only `static/favicon.png`. AC-2 holds: one glob added, no other package-data entry changed. ADR-0006/R1, ADR-0006/R2, ADR-0038/R5, ADR-0038/R7 and ADR-0042/R4 hold, and their tests pass. F-001 (low, pre-existing, recorded, not carded): `src/nonogram/web/static/metadata.js` is served by `web/handler.py` and loaded by both `web/pages.py` form pages, but no package-data glob names it, so a built wheel would 404 it; the wheel test covers only `admin/static` and `admin/templates`. F-002 (info): no real wheel built (no setuptools offline); fnmatch matches setuptools for flat names.

**Merge gate, round 1 (orchestrator).** `make test-gate BASE=main` answered FULL (pyproject.toml changed): 2 failed / 10680 passed / 30 skipped (unarmed) / 1 xfailed in 40 min 45 s. Both reds are `tests/test_impact_set.py::TestImpactSet_EveryShippedAssetHasADerivation` (`test_the_known_asset_types_equal_the_shipped_asset_types`: "shipped but no rule: ['.png']"; `test_every_static_file_has_a_derivation_that_is_not_full`). Same root cause as the card: 7a21d0ba put the first `.png` under `src/`, and `scripts/impact_set.py`'s `ASSET_RULES` must name every shipped asset type. Not caused by the glob.

**Fix round 1 (orchestrator).** Added `".png": "named"` to `ASSET_RULES`: the icon is bytes no code executes, read by tests that name it, as `.ttf` is. The two tests: 2 failed without the rule, 9 passed (the class) with it. `impact_set.py src/nonogram/admin/static/favicon.png` now derives 51 test files instead of FULL. No test added or removed (net 0).
