# CARD-464: Book tiles show the size; only the current section opens

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.2d)
<!-- Basis: the review finding's proposal, sized before reading the code; re-estimate at pick-up. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** owner 2026-11-16 (project thread "UX and design review"): *"I think you can create cards for all of your findings and take them one by one"* — finding M8 of the review doc https://claude.ai/artifact/4gu4yk21Kt9CapTXbwVv11; screenshots ~/Documents/nonogram-reviews/UX-review/shots/
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/book.html, player/pages.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

Every tile in a section is the same blank square with a number; Easy is open by default and pushes Medium and Hard far down on a phone.

## What to implement

Each tile carries its size in small text under the number. The section holding the "continue" puzzle opens; the others start collapsed.

## Acceptance criteria

- **AC-1**: tiles show W×H.
- **AC-2**: with progress in Medium, Medium is the open section.

## Worktree notes
