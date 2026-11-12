# CARD-432: The board hands its scroll to the page — the fling carries on after the finger stops, and 104 px of board is unreachable

**Status:** in_progress
**Priority:** P1
**Category:** bug
**Estimate:** 1c (0.5d)
<!-- The likely fix is one declaration, `overscroll-behavior: contain` on `.player-stage`, which CARD-402 already uses on the landscape strip. The cost is the part that is NOT the declaration: establishing WHY the page takes a gesture that starts over a board with 104 px of unused scroll, and whether removing the page's own slack is needed too. Measure first; the one-liner may be half an answer. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/432-board-scroll-containment
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-432
**Source:** owner question, 2026-11-12: *"why it still scrolls out of inertia when I already stopped scrolling?"* — asked after the wave's three publishes, and traced the same day. Very probably also the content of the owner's play-test **finding 6** of 2026-11-11 (*"When we scroll on the clues - the puzzle jumps down and up"*), which could not be reproduced when the findings were carded and was deliberately left uncarded for want of a reproduction.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_zoom.py
<!-- Derived 2026-11-12. `.player-stage`'s rule and its preceding comment block are in admin.css; `tests/test_puzzle_solver_zoom.py` owns `TestSolverZoom_TheBoardScrollsInsideItsStage`, which is where a scroll-containment claim belongs. `tests/test_puzzle_solver_clues.py`, `_hint.py` and `_phone.py` also read `scrollTop`/`scrollLeft` and are the modules most likely to move — name them in the brief and re-derive rather than assume. Nothing under `player/`: admin.css is in COPIED_FROM_ADMIN. -->
**Review score:** —
**Started:** 2026-11-12T14:05:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Measured on production (`https://nonogram.adverax.io`), 390x844 emulated touch, the 30x30 `52603b6dee` zoomed to **175%**:

```
stage scroll room        319 px down, 549 px across
page scroll room          23 px
touch-drag up on board   stage stays at 215/319      page 0 -> 23
force stage.scrollTop     stage reaches 319          (so the stage is NOT stuck)
computed styles          .player-stage overscroll-behavior: auto,  scroll-behavior: auto
                         html scroll-behavior: smooth
```

Three facts, of which only the first is ordinary:

1. **The inertia itself is the platform's fling.** Every touch scroller decelerates after the finger lifts. That is not a defect and this card does not try to remove it.
2. **The fling does not stay on the board.** `.player-stage` computes `overscroll-behavior: auto`, so scrolling may chain out of it, and the page has 23 px of slack to chain into. A drag that starts **over the puzzle** moves the **page**. When the finger lifts, the page keeps gliding — which is exactly the owner's "it still scrolls when I already stopped".
3. **104 px of the board is unreachable by finger at that zoom.** The stage sits at 215 of 319 and gesture input will not advance it, while assigning `scrollTop` directly reaches 319 immediately. The board has more to show and the gesture cannot get there.

**An existing declaration in the same file is falsified by this.** The comment block above `.player-stage` (the CARD-160/FR-044 header) ends: *"below the floor the board scrolls inside `.player-stage` and the page never does."* The page does — 23 px of it, measured. That sentence has to go with the fix, and it is the reason this was never caught by reading.

**The project already knows the remedy for the sibling case.** `overscroll-behavior` appears **exactly once** in the whole stylesheet: `overscroll-behavior: contain` on the landscape tool strip, added by CARD-402 for this very class of problem. The one surface a reader actually drags on never got it.

## What is measured and what is not — read this before fixing

The **effect** is measured: the page takes the gesture, the board does not move, the stage has room left. The **dispatch reason** is not: I did not establish why Chromium hands a touch that starts over the board to the document scroller rather than to `.player-stage`. So:

- `overscroll-behavior: contain` on `.player-stage` is the **hypothesis**, not a known fix. Apply it and measure; if the page still takes the gesture, the containment was not the cause and the card must say so rather than ship a declaration that reads like a fix.
- The page's 23 px of slack is the other half of the pair. Where it comes from is unestablished — `.player-stage`'s `max-height: max(calc(100svh - var(--player-above)), 5rem)` is sized to end above the fold, so a 23 px overflow means something below or beside it is taller than that arithmetic assumes. **Find out which element overflows** before deciding whether to contain the scroll, remove the slack, or both.
- All of the above is **emulated touch** (Playwright, `is_mobile`, CDP touch events). It is geometry, not a thumb. The owner's own report is the stronger evidence that it is real.

## What to implement

1. **Establish the dispatch reason** — which scroller receives a touch that starts over the board, and why. Then fix the cause, not the symptom.
2. **Contain the board's scroll** so a fling that reaches the board's limit does not continue into the page, matching what CARD-402 already does for the strip.
3. **Make the remaining 104 px reachable** — a board with scroll room must yield it to a drag. If (2) alone achieves this, say so with the measurement; if it does not, this is the part that matters most, because it is the one that hides puzzle from the reader.
4. **Correct the falsified comment** in the same diff: "and the page never does" is not true today. Replace the sentence; do not append its history to it (the wave's standing lesson — one card shipped 115 comment lines above a 12-line handler by appending).

## Acceptance criteria

- **AC-1** (the board's scroll stays on the board): at 390x844 with the 30x30 zoomed past fit, a touch drag over the board that exhausts the stage's scroll leaves `window.scrollY` unchanged. (test: a changed cell in `tests/test_puzzle_solver_zoom.py::TestSolverZoom_TheBoardScrollsInsideItsStage`; plant: remove the containment and the cell reds.)
- **AC-2** (every pixel of the board is reachable): at the same viewport and zoom, repeated drags move `stage.scrollTop` from 0 to its maximum — the figure measured, not assumed — with no residue that only a programmatic assignment can reach. (test: the same cell; this is the AC that fails today at 215 of 319.)
- **AC-3** (nothing else moves): the fit path at 100% is unchanged — a board that fits still does not scroll, the stage still ends above the fold, and `TestSolverPhone_BoardFitsThePhoneWidth` and the clue-band cells in `tests/test_puzzle_solver_clues.py` pass unchanged. (test: those cells, unchanged.)
- **AC-4** (the claim in the file is true again): no comment in `admin.css` states that the page never scrolls, unless the card has made that true and the test asserts it. (test: AC-1's cell is the assertion; evidence: the replaced sentence.)

**Net test count: 0 added** — `TestSolverZoom_TheBoardScrollsInsideItsStage` already owns this subject; change it.

## Worktree notes

—
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`, so no `min_version` comparison exists to make. Start gate `decision: gate` (command from `review.test_command`); fork point interactive/target tip. Pin, drift and state-table gates all not applicable.
- **[Stale figures, read this first]** Every figure in this card's `## Why this card exists` was measured on production on 2026-11-12 **before four cards landed on the same surface**: CARD-430 (the zoom group became one joined pill), CARD-431 (the portrait title went 30 px → 20 px, explicitly "giving the board the height back"), CARD-439 (a twelfth control, Line, joined the compact toolbar) and CARD-437. Three of those four change the toolbar's height or width, and `.player-stage`'s cap is `max-height: max(calc(100svh - var(--player-above)), 5rem)` — i.e. it is computed FROM the height above it. So the stage's 319 px of scroll room, the page's 23 px of slack, the 215/319 the drag reached and the 104 px unreachable are all **suspect and must be re-measured before anything is changed**. The DEFECT is not in doubt — the page taking a gesture that starts over the board is a mechanism, not a figure — but every number attached to it is.
