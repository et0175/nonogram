# CARD-428: Landscape: the zoom control wraps onto two rows (− and 100% on one, + alone below)

**Status:** in_progress
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The strip is a 2-column grid and the zoom group has three members; the fix is a span or a reflow of that one group. The cost is re-pinning CARD-402's landscape geometry, which several cells measure. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/428-landscape-zoom-row
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-428
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 5. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_zoom.py
<!-- Derived 2026-11-11 from `admin.css`'s CARD-402 block (`@media (max-height: 500px) and (orientation: landscape)`), whose `.player-toolbar` is `grid-template-columns: repeat(2, 44px)` with `.player-zoom` as `display: contents` — so its three children flow into the 2-wide grid. `tests/test_puzzle_solver_phone.py` holds CARD-402's own landscape cells; name it in the brief. Conflict edge: CARD-424 and CARD-426 also edit `admin.css` — serialize. -->
**Review score:** —
**Started:** 2026-11-11T18:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Measured on production in landscape, at both 844x390 and 874x402:

```
rows = 2   tops = [240, 292]
  −      x=40  y=240  44x44
  100%   x=92  y=240  44x44
  +      x=40  y=292  44x44
```

The owner's words: *"zoom button gets awkwardly in 2 lines (+, number and -)"*. The mechanism is CARD-402's side strip: `.player-toolbar` is `grid-template-columns: repeat(2, 44px)` and `.player-zoom` is `display: contents`, so its **three** children flow into a **two**-column grid and wrap 2 + 1. The readout ends up beside the minus and the plus is orphaned on the next row — so the two steppers, which are a pair, are the two things not next to each other.

This is cosmetic in the sense that nothing is unreachable, and not cosmetic in the sense that `−` and `+` reading as a pair is what makes a stepper a stepper.

## Decision owed before implementation (owner)

**D1:** which of the three shapes? (a) `−` and `+` side by side on one row with the readout spanning both columns below (the readout is also the Fit control, so it is the one that can take a full-width row); (b) all three in one row by letting the zoom group break out of the 2-column grid; (c) the readout dropped to a tooltip in landscape, leaving a clean pair. **Default if unanswered:** (a) — it keeps every target 44 px, keeps the pair adjacent, and spans the member that is already full-width-friendly elsewhere in the strip (the brush slot and the counters already span both columns).

## What to implement

1. The chosen shape, in CARD-402's own landscape block, keyed on the same selectors it already uses. Every control stays at least 44 x 44 px (CARD-423's floor, which this block already sets explicitly).
2. Re-measure the landscape strip and the board beside it at 844x390 and 874x402, and re-pin whatever CARD-402's cells measure in `tests/test_puzzle_solver_phone.py` — in the dated form those lines already carry.

## Acceptance criteria

- **AC-1** (the steppers are a pair, on one row): at 844x390 and 874x402, `−` and `+` share a row (equal rounded `top`) and are horizontally adjacent, and the zoom group occupies no more rows than the chosen shape allows. (test: changed cell in `tests/test_puzzle_solver_zoom.py`; plant: revert the rule and the cell reds.)
- **AC-2** (nothing shrank): every control in the landscape strip is still at least 44 x 44 px. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar`, unchanged — it already asserts this at 844x390.)
- **AC-3** (the board kept its room): the stage's box beside the strip at 844x390 is unchanged, or changed by exactly the measured amount, recorded in Worktree notes. (test: CARD-402's existing landscape geometry cells, re-pinned if they move.)
- **AC-4** (portrait untouched): at 390x844 the zoom group's geometry is unchanged. (test: the existing portrait cells.)

**Net test count: 0 added.**

## Worktree notes

- **[Env]** forge version unresolved (no `.claude-plugin/plugin.json` at the executing path; no `meta/.skills.yml` in this project, so no `forge.min_version` comparison and no `models:` block — agents inherit the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`. That command is **exit 127 in a worktree** (none has a `.venv`): use `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`, or `make test-gate PY=<main>/.venv/bin/python`. Fork point `8ecb8758`, interactive mode.
- **[Impact scope]** Derive with `scripts/impact_set.py --gate --against main`, never from a standing note: CARD-423 shipped two criticals past a hand-picked 10-module set the script would have caught.
- **[Concurrency, LIVE]** **CARD-426 is `in_progress` in `PythonProject4-card-426` and is editing `src/nonogram/admin/static/solver.js` and `src/nonogram/admin/static/admin.css` right now.** The two cards own different regions — 426 the brush menu's rules and `openMenu`/`closeMenu`, this card the CARD-402 landscape block — and different test modules (`test_puzzle_solver_brush_menu.py` vs `test_puzzle_solver_zoom.py`). Whichever merges second rebases. Keep every edit inside the CARD-402 block and additive; anything outside it is a `SCOPE+` line.
- **[Owner ruling]** D1 was **not** answered; the card's recorded default applies — shape (a), `−` and `+` side by side with the readout spanning both columns below. The owner said only "start 428 too", which is not a ruling on the shape, so the default is taken as the card wrote it and the author does not invent a different one.
