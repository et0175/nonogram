# CARD-450: The landscape strip fits the shortest phones — Probe beside Hint, tighter gaps under 360 px

**Status:** done
**Priority:** P1
**Category:** bug
**Estimate:** 0.5c (0.1d)
<!-- Basis: two `order` rules and one short-height gap rule in the landscape block, and two sizes added to the strip test. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/450-short-landscape
**Worktree:** ../PythonProject4-card-450
**Source:** owner 2026-11-16 (project thread): *"Протестуй будь-ласка сама згідно зі своїм планом тут (на android), напиши, що знайшла, та виправ помилки"* ("test it yourself by your plan, on Android, write what you found and fix the bugs"). Checklist item 6 on a Galaxy S9+ in landscape.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-448
**Touches:** src/nonogram/admin/static/admin.css, tests/test_player_public_mode.py
**Review score:** — (no review cycle; owner request, 2026-11-16)
**Started:** 2026-11-16T16:00Z
**Closed:** 2026-11-16T16:40Z
**Actual:** —
**Merge commit:** c6400e89
**Blocked by:** —

## Why

CARD-448's three-wide strip fits 844 x 340, but a Galaxy S9+ on its side is 658 x 320, and 658 x 264 with Chrome's address bar: on the live site Probe sat below the edge there for a 30 x 30 (bottom 324 of 320), and at 264 the zoom too. The history group leaves one cell empty after Hint (and after Line), and Probe drew a row of its own after the zoom pill.

## What to implement

In the landscape block, `order` places Probe straight after Hint (the empty cell) and the zoom pill and counters after it — one row less; the drawing only, the focus order stays the DOM's. Under 360 px tall the strip's gaps halve.

## Acceptance criteria

- **AC-1**: at 658 x 320 and 658 x 264, as at CARD-448's four sizes, every control is inside the strip's view with the page unscrolled. (test: `TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board`, which reds on `main`'s stylesheet: lowest control 309 against 305)

## Worktree notes
- **[Measured, 2026-11-16, live vs prototype, Chromium Android emulation]** Galaxy S9+ 658x320: 30x30 Probe OUT (324) → in; 658x264: Probe and zoom OUT → in, only the counter's text below. Pixel 7 839x412 and 839x356 unchanged (all in). Found by the Android QA run, `~/Documents/nonogram-reviews/QA/QA_Checklist_Nonograms_v2_android.xlsx`.
- **[Gate, 2026-11-16]** The 22 files that measure landscape or 844 px viewports: 622 passed, 0 failed.
