# CARD-277: A drag at 200% zoom marked the whole board once — reproduce it before deciding what it is

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/277-zoom-drag-marked-everything
**Worktree:** —
**Source:** CARD-270's fix round hit it once and chased it rather than reporting it; CARD-270's review cycle 2 ruled that recording it was right for that card's gate but that it **needs a card of its own** — "a drag marking 225 cells instead of 5 at 200% zoom is correctness-shaped nondeterminism in the player's drag handling", and "recorded, not diagnosed" dies with the worktree. Board precedent is one card old: F-004 got CARD-275 rather than a note.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_puzzle_solver_zoom.py, src/nonogram/admin/static/solver.js
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What was actually observed — and the honest width of it

**Once.** On the first of five runs during CARD-270's fix round, two tests in
`tests/test_puzzle_solver_zoom.py` failed together:

- `test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line` (`:417`)
- `test_marks_zoom_and_circles_survive_crossing_both_ways` (`:685`)

**The symptom: the drag marked 225 cells instead of 5.** 225 is 15×15 — *every cell of the board*, not a
few extra and not one cell repeated. That number is the most informative thing known about this bug and
the card is named after it.

**It did not reproduce.** Four subsequent runs were green: the same selection with CARD-270's edits
stashed (491 passed), the same selection with them restored (491 passed), the zoom file alone (25
passed), and a twelve-file set (558 passed). CARD-270's reviewer additionally established it is **not**
CARD-270's doing, structurally: that card's diff is five files naming neither
`tests/test_puzzle_solver_zoom.py` nor `conftest.py`, its whole `test_puzzle_solver_page.py` change is six
lines inside a data dict, and the isolation guards are green including the alone-probe and both
order-independence probes.

**So what is known is: one observation, 225 cells, not reproduced, not attributable to the card that saw
it.** Everything below this line is a suspect list, not a diagnosis. **Do not write a fix against a
suspect.**

## The mechanism it would have to go through

`solver.js`'s `pointermove` handler (`:1232`) appends to `gesture.path` every cell `cellUnder` returns
that differs from the previous one, and `cellUnder` (`:942`) is
`document.elementFromPoint(x, y)?.closest("td.player-cell")`. The whole accumulated path is then applied
as one `dragStroke`. So **225 marked cells means the path genuinely accumulated 225 distinct cells** —
the handler did what it was told; the question is why it was told that.

Three suspects, each with a different verdict attached, and they are **not** equally likely:

1. **A redraw mid-drag.** `redraw()` rebuilds the table, and since CARD-212 it fires on any window resize,
   not only on crossing 820 px. A phone collapsing its URL bar does it; so can a scrollbar appearing when
   a 200 %-zoomed board overflows `.player-stage`. If the old `td` elements die under a live gesture
   while `gesture.path` survives, the path can take on cells the pointer never visited. **If this is it,
   it is a real user-facing bug** — the hint highlight already needed re-applying across a redraw
   (CARD-212 review cycle 2, G-003), which is precedent that live state and redraws interact badly here.
2. **Synthetic-event interpolation.** Playwright's `mouse.move` can be driven in steps; at 200 % zoom the
   same CSS distance covers twice the device pixels, so an under-stepped synthetic drag can land on a
   different set of cells than the test means. **If this is it, it is a test-harness artifact** — fix the
   test's stepping, and the player is innocent.
3. **Scroll-position skew.** `elementFromPoint` takes *viewport* coordinates. A zoomed board that scrolls
   between the test computing a target and the event being delivered maps those coordinates onto other
   cells. **This one can be either**, depending on whether the scroll is something a user can cause.

## What to implement

1. **Reproduce it first, and do not proceed without a reproduction.** This is the whole card. Run the two
   named tests in a loop (they are browser tests — budget for it, and run them *alone* and in the
   twelve-file set, since the one failure appeared in a multi-file run and not in the file alone).
   Record the loop count and the hit rate; an honest "N runs, 0 reproductions" is a **publishable
   result** for this card and is better than a fix aimed at a guess.
2. **If it reproduces: capture the path, not just the count.** Instrument the failing run to record
   `gesture.path` (or the resulting stroke's cell list) and the board's scroll offset and bounding rect at
   each `pointermove`. The three suspects above make *different* predictions about what the path looks
   like — a contiguous sweep across the whole board, a jump, or a duplicate-free superset — so the
   captured path picks the suspect instead of the implementer picking it.
3. **Then fix the cause, with a regression test that fails without the fix.** If it is suspect 1, the fix
   is in `solver.js` and the test is a redraw forced mid-gesture. If suspect 2, the fix is in the test's
   drag stepping and `solver.js` must not change. **Do not change `solver.js` for a harness artifact** —
   that would be a production change bought by a test defect.
4. **If it does not reproduce after a declared budget**, close the card with the measurement written down:
   how many runs, in which selections, at which zoom levels, and what instrumentation was in place that
   *would* have caught it. Add the instrumentation to the test permanently if it is cheap, so the next
   occurrence is diagnosable rather than another anecdote. A flake that is recorded with its hit rate and
   its detector is a different thing from a flake that is recorded as a sentence.

## Acceptance criteria

- **AC-1** (the honest fork): *Given* a declared reproduction budget, *then* the card reports **either** a
  reproduction with the captured `gesture.path` and the suspect it selects, **or** a measured
  non-reproduction with the run count, selections and instrumentation — and in both cases the figure is
  stated with its domain (how many runs, which selection, which zoom). (evidence: the card's own
  measurement; no test if it does not reproduce)
- **AC-2** (a fix is caused, not guessed): *Given* a reproduction, *then* the fix names the mechanism it
  changes and a regression test **fails without it and passes with it** — demonstrated, not asserted.
  (test: named at that point; it cannot be named before the cause is known, and this card will not
  pretend otherwise)
- **AC-3** (production is not paid for a test defect): *Given* the diagnosis is suspect 2
  (synthetic-event stepping), *then* `src/nonogram/admin/static/solver.js` is **unchanged** —
  `git diff --name-only main...HEAD -- src/` empty — and only the test's drag driving changes. (gate:
  structural)
- **AC-4** (the detector outlives the card): *Given* either outcome, *then* a drag test asserts the
  marked-cell **count** against the cells the drag was meant to cover, so a future recurrence names
  itself instead of being read as "225 ≠ 5". (test: `TestSolverZoom_ADragMarksOnlyWhatItCrossed`)
- **AC-5** (no silent widening): *Given* any change to the drag path, *then* the existing zoom, marking,
  mirror and phone suites pass **unedited**. (gate: `tests/test_puzzle_solver_zoom.py`,
  `test_puzzle_solver_marking.py`, `test_puzzle_solver_mirror.py`, `test_puzzle_solver_phone.py`)

## Guardrails

- G-1: **Do not "fix" this by loosening an assertion.** The two tests that caught it assert an exact
  marked set; weakening either to a range or a floor would hide the next occurrence and is the one
  outcome worse than leaving the bug open.
- G-2: No change to `solver_state.js` — the pure module applies the stroke it is given; this is about
  what the stroke contains (ADR-0038/R4).
- G-3: Hand-written JS only, no framework or build step (ADR-0038/R1); no request per mark
  (ADR-0038/R2).
- G-4: If the cause turns out to be the redraw path, **do not change when `redraw()` fires** — CARD-212
  measured that behaviour and CARD-193 owns the breakpoint rule. Fix how a live gesture survives a
  redraw, not the redraw's trigger.
- G-5: This card **must not block CARD-270's merge**, and does not depend on it. CARD-270's reviewer was
  explicit, and the structural evidence above says the flake predates it.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: review-lens)
- ADR-0038/R8 — browser tests run against locally installed Chromium and **fail or skip loudly**, never
  silently; a flake investigation must not weaken that (check: review-lens)
- CON-021 — interactive play only in the admin panel's player (check: review-lens)

## Architecture context

- **FR:** FR-044 (the player). Drag marking is AC-303/AC-304-era behaviour; zoom is CARD-195's.
- **ADR:** ADR-0038/R1, R2, R4, R8.
- **Components:** COMP-009 (admin panel: static JS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** — run them, do not rewrite them (G-1):

| name | resolves to |
|------|-------------|
| `test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line` | `tests/test_puzzle_solver_zoom.py:417` |
| `test_marks_zoom_and_circles_survive_crossing_both_ways` | `tests/test_puzzle_solver_zoom.py:685` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |

**To be written by this card:** `TestSolverZoom_ADragMarksOnlyWhatItCrossed`, plus whatever AC-2's
regression test turns out to be — deliberately unnamed until the cause is known.

## Worktree notes

- **[The 225 is the clue, and it is in the card's title for that reason]** 225 = 15×15 = the whole board.
  Any explanation that accounts for "a few extra cells" does not account for this. Start from the fact
  that the accumulated path reached *every* cell and work backwards.
- **[Browser-test cost]** These are pytest-playwright/Chromium tests (ADR-0038/R7, dev-only extra). A
  reproduction loop is the expensive part of this card; say up front how many runs the budget buys and
  report the number actually run. Do not run the full suite — this board defers that to the merge gate,
  and a sibling card may be live.
- **[Known-good baselines to compare against]** 491 passed for the eleven sibling player files +
  `test_puzzle_editor_ui.py`; 25 passed for the zoom file alone; 558 for the twelve-file set. Those are
  CARD-270's measurements and they are the "green" readings this card is trying to break.
- **[A non-reproduction is a result, not a failure]** This board's rule is that a figure is a claim and
  its control is recomputation. "Did not reproduce in N runs" with N stated, the selection stated and the
  instrumentation stated is worth more than a speculative fix, and it is the outcome this card should be
  willing to ship.
