# CARD-523: On narrow phones the board stays put on solve: Show grid takes Line's place

**Status:** in_progress
**Priority:** P3
**Category:** feature
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/523-show-grid-takes-line
**Worktree:** ../PythonProject4-card-523
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-225 (CARD-511 notes and review F-001).
**Idea:** IDEA-225
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/templates (solver page), tests/test_puzzle_solver_maybe.py
**UI surface:** admin solver page toolbar (solved state, portrait phones)
**Review score:** —
**Started:** 2026-11-22T13:38Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

After CARD-511, on portrait phones 327-339 px and 421-451 px wide the board still moves down about 25-27 px when a puzzle is solved: once Line hides, Probe plus Show grid need about 96 px, the probe bar's share of the row narrows, and its counters wrap to a row of their own. Owner's ruling 2026-11-22: once solved, Show grid takes Line's place in the toolbar, so the row keeps its width and the board does not move.

## What to implement

Re-verify on main first with the existing solve sweep (tests/test_puzzle_solver_maybe.py's sweep and `test_wraps`, real solves in Chromium): measure the board's dx/dy on solve across portrait widths 320-600 px, and confirm the two bands. Then put Show grid in Line's slot once the puzzle is solved (markup order, CSS, or both: the smallest change that keeps one control per slot), so the solved toolbar fits its row at every width.

The public player has no Show grid (CARD-511's publish record), so the public toolbar must stay as it is; the public site is a build-time copy of these admin files, so check that copy too.

## Acceptance criteria

* **AC-1**: across portrait widths 320-600 px (the sweep's own steps, including 327-339 and 421-451), a real solve moves the board by 0 px in x and y (control: main's code shows the two bands moving).
* **AC-2**: wider and landscape layouts the sweep already covers stay at 0 movement; Show grid and every other solved-state control stays reachable and labelled.
* **AC-3**: the public player's toolbar is unchanged: an assembled site's play page shows the same controls as before, before and after solving.
* **AC-4**: net test count 0; extend the sweep's widths rather than adding a test. Report it.

## Guardrails

* **G-1**: no publish; the owner publishes the player.
* **G-2**: renders for the owner go to ~/Documents/nonogram-reviews/CARD-523/ (before/after at 330 px and 430 px, solved); never into the repo.

## Worktree notes
