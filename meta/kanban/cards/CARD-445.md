# CARD-445: The line view can go quiet but cannot be asked — it has no Hint

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (0.75d)
<!-- Basis: one control in a toolbar that is already tight, plus the press's own handler reused. The cost is not the button — it is where it goes at 390 px without taking a row from the strips, and whether the view's own clue tint is the right place for the answer. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/445-the-line-view-can-be-asked
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-445
**Source:** owner ruling, 2026-11-14, taken at CARD-435's close: *"Leave it, card it separately."* Put to them with the measured gap — their two CARD-435 rulings (the probe stays quiet until Hint; the rule applies to both surfaces) combine so that in the line view the red clues can never appear at all. They declined adding a control inside CARD-435 after it had passed two review cycles, and declined exempting the line view from the quiet rule.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-435
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_line.py
<!-- Derived 2026-11-14. buildLineView and the line view's own `is-broken` / `is-flagged` toggles are in solver.js; the view's toolbar geometry is in admin.css's compact block; TestSolverLine_ProbesInTheView is CARD-442's home for the view's probe. Re-derive with scripts/impact_set.py --gate rather than trusting this list — tests/test_puzzle_solver_phone.py holds the compact control census and the frozen base-css census samples the toolbar, so both are candidates the moment a control is added. -->
**Review score:** —
**Started:** 2026-11-16T21:10:00Z
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
- **[Env]** forge 2026.10.29; no `meta/.skills.yml`. Start gate `decision: gate`; fork point interactive/target tip `dbd90abb`. `Depends on: CARD-435` satisfied — `done` and live. Pin, drift and state-table gates not applicable.
- **[Owner rulings, 2026-11-16, both taken before dispatch with measured figures in hand]** **Open point 2 → "Everything, and offer to jump there."** The ask flags the visible line's clue when the guess breaks it, **names the other broken rows and columns**, and offers them as **tappable targets that pivot the view to them**. The owner was told in the question itself that this option "adds navigation this card didn't scope, so it would likely grow past its 2c estimate" and chose it anyway. **Estimate re-stamped 2c → 3c (0.75d)**, which is the honest consequence, not a renegotiation. **Open point 3 → "Borrow the board's existing announce line."** The sentence goes to `#puzzle-player-explain`; the view gets no live region of its own, so there is exactly one place the sentence is written and AC-4's anti-drift property covers the announcement too.
- **[Open point 1 RESOLVED BY MEASUREMENT, on production, before dispatch — a control costs the strips NOTHING]** Measured on `0978469757` (30 x 25) with the view open, at both viewports the card names:
  - **390x844**: the view is `position: fixed`, 390x844. Head row (`Board`, `Rows`, `Cols`) 358x44 @12; `Previous row`/`Next row` @149; the clue row 358x44 @289; **`.player-line-strips` 358x132 @345** (two 358x52 strips); the tools block **358x100 @497 — already TWO rows**: six brushes/history at y 497, and **`Probe` (90.6x44) ALONE at y 553 with ~267 px of that row free.**
  - **844x390**: strips 559x132 @120; tools **559x44 @268, ONE row** holding six 44 px controls plus `Probe` 90.6 = 354.6 px, leaving **~204 px free on that row.**
  - **So in both orientations there is an existing row with room beside `Probe`.** AC-3 ("the strips keep their room") is satisfiable without taking a row — but it is still an AC: **re-measure the strips' box on main and after, and report the delta**, because `flex-wrap` can move a row for reasons a free-space sum does not predict.
- **[A CARD PREMISE THAT DISSOLVED ON CONTACT — open point 3 was built on a non-existent element]** The card says *"The view has its own live region; whether the sentence goes there, or the view borrows the board's, is a decision"*. **It has none.** Measured on production: **zero** `[aria-live]` and zero `[role=status]` elements inside `#puzzle-player-line`, at both viewports. So the choice was never "its own versus the board's" — it was "add one, or borrow". The owner chose borrow. This is the third instance this wave of a premise that reads as measured and was not: state what you have not measured as unmeasured.
- **[What is already in place, verified by name and not by line number]** `TestSolverLine_ProbesInTheView` **exists** (`tests/test_puzzle_solver_line.py`), so AC-1's test ref is live rather than planned. The board's quiet-probe machinery is `probeAsked`, `setProbe` (its only writer), `askedProbe()` and `brokenNow()` in `solver.js` — that is the path AC-4 requires both surfaces to share. And `#puzzle-player-explain` is **already centred in the VIEWPORT** (CARD-427, owner's ruling of 2026-11-11), which is why borrowing it can work over a `position: fixed` dialog at all — **but verify it actually paints above the view**; a viewport-centred box still loses to a later stacking context, and nothing yet proves the z-index works out.
