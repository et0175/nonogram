# CARD-473: The browser no longer zooms the play page, so the clues and toolbar cannot be pinched off screen

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 0.25c (0.1d)
<!-- Basis: one meta tag and one assertion. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/473-no-page-pinch (merged into ux-review-cards)
**Worktree:** —
**Source:** owner 2026-11-17 (project thread "UX and design review"): *"I've tested on android - scrolling can make cues not visible"*, with a screenshot of puzzle 68 (27x30) in an Android Chrome tab showing only cells — no clues, no toolbar, no title.
**Idea:** —
**Wave:** 80
**Created wave:** 80
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/assemble.py, tests/test_player_shared_ui_site.py
**Review score:** — (no review cycle; owner report, 2026-11-17)
**Started:** 2026-11-17T08:40Z
**Closed:** 2026-11-17T09:00Z
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The board's own zoom never hides the toolbar (the stage is capped under it), so a screen of cells only is the browser's page zoom: a pinch that did not start on a cell (the cells are `touch-action: pan-x pan-y`) zoomed the whole page, and the sticky clue bands stick to the stage, not to the window.

## What to implement

The play page's viewport meta: `width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no`. The board keeps its own − / + / Fit and pinch.

## Acceptance criteria

- **AC-1**: the served play page carries that viewport meta (tests/test_player_shared_ui_site.py, the stylesheet cell).
- **AC-2**: on the owner's Android phone a two-finger pinch on the puzzle page no longer zooms the page (owner check after publish).

## Worktree notes
- **[Reopens]** memory/ruling of 2026-11-05 ("leave the browser's pinch on"), on the reported device problem that ruling named as its reopen condition.
- **[Unverified in emulation]** Chromium's `Input.synthesizePinchGesture` at a Galaxy S9+ emulation zoomed neither production nor the fix (visualViewport.scale stayed 1), so AC-2 is the owner's phone.
- **[Gate]** Player/site set: 415 passed.
