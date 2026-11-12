# CARD-441: The line view reads like the board — a settled number is ringed, and the heavy fifth rule shows between black cells

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 0.5c (0.1d)
<!-- Basis: two CSS rules in the line view and one browser test; the cost is choosing a divider that reads heavier than the thin one. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/441-line-view-reads-like-the-board
**Worktree:** ../PythonProject4-card-441
**Source:** owner 2026-11-12 (project thread, trying line focus live): *"I've noticed 2 small things in the row screen: 1) we circle around the solved cue number, not crossing it; 2) there's no divider between 2 black cells around 5x line"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-439
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_line.py
**Review score:** — (no review cycle; owner request, 2026-11-12)
**Started:** 2026-11-12T18:20Z
**Closed:** 2026-11-12T19:00Z
**Actual:** —
**Merge commit:** e8f3e7d5
**Blocked by:** —

## Why

CARD-439 said a settled clue number in the line view with a strike-through, where the board rings it. And the heavy every-fifth rule in a strip is ink, so between two black cells it was ink on ink and the two cells read as one.

## What to implement

1. `.player-line-num.is-circled`: a grid-ink ring (border plus an inset shadow, so nothing moves), radius 22 px — round for one digit, a pill for two — the digit keeping its ink; no strike, no muted colour (the board keeps the digit's ink too).
2. A black cell on either side of a heavy rule keeps a paper gap as wide as the rule (`.is-major[data-state="filled"]` on its left, `:has(+ .is-major)` on its right), so the rule reads as ink between two paper lines, heavier than the thin divider (which already showed between black cells).

## Acceptance criteria

- **AC-1** (ringed): on a row whose marks settle its clue, every number has `is-circled`, `text-decoration-line: none`, a border in the filled cell's ink and a radius at least half its height. (test: `TestSolverLine_ReadsLikeTheBoard::test_ring_and_divider`)
- **AC-2** (two cells): at a heavy rule with black on both sides, both cells carry a box-shadow that is not their own ink. (same test; fails on `main`'s stylesheet, run as the control)

## Worktree notes
- **[Design, 2026-11-12]** A first attempt gave every black cell the board's thin inset hairline. It made the thin dividers between black cells three light pixels wide and the heavy one a thinner dark line between two hairlines — the heavy rule read LIGHTER than the thin one. The paper gap beside the heavy rule only keeps the thin divider as it was.
