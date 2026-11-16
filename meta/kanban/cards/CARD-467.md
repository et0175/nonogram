# CARD-467: Region's automatic switch-off says so

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M11 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Region turns off when zooming in so that drags scroll; the only sign is the button losing its green.

## What to implement

The first time it happens in a session, a short toast: "Zoomed in: drag now scrolls. Turn on Region to paint by dragging."

## Acceptance criteria

- **AC-1**: zooming in from a fitted board with Region on shows the toast once per session.

## Worktree notes
