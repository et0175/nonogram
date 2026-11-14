# CARD-445: The line view can go quiet but cannot be asked — it has no Hint

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: one control in a toolbar that is already tight, plus the press's own handler reused. The cost is not the button — it is where it goes at 390 px without taking a row from the strips, and whether the view's own clue tint is the right place for the answer. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling, 2026-11-14, taken at CARD-435's close: *"Leave it, card it separately."* Put to them with the measured gap — their two CARD-435 rulings (the probe stays quiet until Hint; the rule applies to both surfaces) combine so that in the line view the red clues can never appear at all. They declined adding a control inside CARD-435 after it had passed two review cycles, and declined exempting the line view from the quiet rule.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-435
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_line.py
<!-- Derived 2026-11-14. buildLineView and the line view's own `is-broken` / `is-flagged` toggles are in solver.js; the view's toolbar geometry is in admin.css's compact block; TestSolverLine_ProbesInTheView is CARD-442's home for the view's probe. Re-derive with scripts/impact_set.py --gate rather than trusting this list — tests/test_puzzle_solver_phone.py holds the compact control census and the frozen base-css census samples the toolbar, so both are candidates the moment a control is added. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-435 made a contradiction probe keep quiet until the reader asks, on the owner's ruling of 2026-11-14, and a second ruling the same day applied that to **both** surfaces — the board and CARD-439's line view, which has its own red clue tint and its own flagged Contradiction button.

Only the board has a Hint control. So the two rulings combine into a dead end: **inside the line view the flags can now never appear.** Review cycle 1 measured the state and put it more sharply than "go back to the board" — `buildLineView` ships close, previous, next, undo, redo, probe-open, Keep and Abandon, and nothing else, so once the reader marks anything in the view the flags are gone and there is no way to get them back without leaving. In the view the feature is reachable only as a read-only interlude.

**This is not a defect in CARD-435.** Both of its cycles ruled the quiet rule correctly implemented, and the reviewer judged that adding a control is new UI and the owner's call. The owner then made that call: card it.

## What to implement

A way to ask, inside the line view, for the clues the open guess has already broken — reusing the board's own press handler rather than a second implementation of it, so the two surfaces cannot drift in what they answer.

## The open points, which are the actual cost

1. **Where it goes.** The view's toolbar is already tight: CARD-428's landscape block gives it two 44 px columns, and the strips themselves are the point of the screen. A control that takes a row from the strips is worse than the dead end it fixes. **Measure the toolbar at 390x844 and 844x390 before choosing**, and report what the control costs the strips.
2. **Whether the answer belongs in the view at all.** The view shows one line. The board's answer is "these rows and columns are broken" — possibly several, most of them not the line on screen. So the honest answer in the view may be narrower (does THIS line's clue break?) or may have to name lines the reader cannot see. **Decide and say which, with the owner if it changes what they get.**
3. **The announce line.** The board's press writes a sentence to `#puzzle-player-explain`. The view has its own live region; whether the sentence goes there, or the view borrows the board's, is a decision and not a detail.

## Acceptance criteria

- **AC-1** (the view can ask): with a probe open in the line view and marks that break a line, a press of the view's own ask control reveals the flags the board's press would reveal, derived by the same code path. (test: a changed cell in `tests/test_puzzle_solver_line.py::TestSolverLine_ProbesInTheView`; plant: remove the control's handler and the cell reds.)
- **AC-2** (quiet until asked, still): before that press the view shows no `is-broken` clue and no `is-flagged` Contradiction — CARD-435's property, unchanged. (test: the cell CARD-435 already changed, unchanged by this card.)
- **AC-3** (the strips keep their room): at 390x844 and 844x390 the strips' own box is no smaller than it is today, the figure measured on main and not predicted. (test: the geometry cells in `tests/test_puzzle_solver_line.py`; this is the AC that fails if the control takes a row.)
- **AC-4** (one answer, not two): the sentence and the flags come from the board's handler, so a change to what the press answers moves both surfaces at once. (evidence: the shared call path, named.)

## Worktree notes
