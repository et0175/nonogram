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
**Touches:** pyproject.toml
**UI surface:** —
**Review score:** —
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
