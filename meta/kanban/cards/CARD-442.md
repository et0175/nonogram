# CARD-442: Probe inside the line view — see an open probe, and start, keep or abandon one from there

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: the probe's transitions already exist (CARD-268/411/412); this card shares them with a second set of buttons, paints the probe in the strip and the map, and lifts the Wrong-guess offer above the dialog. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/442-line-view-probe
**Worktree:** ../PythonProject4-card-442
**Source:** owner 2026-11-12 (project thread): *"Please add a contradiction-probing mode on one line screen (both when we appear on the screen already in the contradiction-probing, and start it from here)"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-439, CARD-268
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, player/how-to-solve.html, tests/test_puzzle_solver_line.py, tests/test_browser_fixture_scope.py (ADDED_SINCE_BEFORE)
**Review score:** — (no review cycle; owner request, 2026-11-12)
**Started:** 2026-11-12T19:30Z
**Closed:** 2026-11-12T20:00Z
**Actual:** —
**Merge commit:** 0b666a45
**Blocked by:** —

## Why

Marks made in the line view already went through the player's one `commit`, so with a probe open they silently became probe strokes — but the view showed nothing of it: no dashed marks, no Keep or Wrong guess, and the CARD-412 offer after a Wrong guess sat under the dialog (z-index 1030 against 1050).

## What to implement

1. **One implementation.** wireMarking's three probe transitions become functions (`openProbe`, `keepProbe`, `wrongGuess`), called by the probe bar's buttons and by the view's; neither set clicks the other.
2. **Controls.** A Probe group in the view's tools row: Probe, which becomes Keep and Wrong guess while a probe is open (CARD-411's rule). A line of its own on a portrait phone, beside the brushes in landscape. Wrong guess carries the board's red flag (CARD-410) while the probe has broken a line.
3. **Painting.** Strip cells in the probe carry `data-probe` with the board's dashed marker; the focused line's clue is tinted red when the probe broke it; the map outlines the probe's cells in the probe colour; the offered cell of a Wrong guess is outlined in the strip. The tip line explains the probe while one is open.
4. **The offer on top.** While the view is open every `.player-explain` (the offer is one) is at z-index 1060; Mark it / No thanks hand focus to the view's Probe.
5. **Tutorial.** Step 5 says Probe works in the view too.

## Acceptance criteria

- **AC-1** (open probe shows; Keep): a probe opened on the board shows in the view (Keep and Wrong guess visible, its cell dashed in the strip, on the board and on the map); a mark in the view joins it; Keep in the view closes it on the board too and keeps the marks. (test: `TestSolverLine_ProbesInTheView::test_an_open_probe_shows_and_keep_keeps_it`)
- **AC-2** (start; Wrong guess; offer): Probe in the view opens the board's probe; Wrong guess undoes its marks; the offer is the topmost element at its centre, names the cell, outlines it in the strip, and Mark it marks it with the view still open. (test: `TestSolverLine_ProbesInTheView::test_a_wrong_guess_in_the_view_undoes_it_and_offers_the_other_colour`)

## Worktree notes
- **[Measured, 2026-11-12]** Local assembled site, 390x844 touch, 30 x 30: the probe group is its own row under the tools, `scrollWidth` 390. The token sweep `test_the_probe_tint_comes_from_tokens` collects every rule naming the probe colours; its expected list gains the three line-view rules, and the map outline's geometry is a rule of its own (the probe bar's layout precedent), so only its colour is swept. At 844x390 it sits beside the brush and history in the tools row (y 268, 44 tall), the strips untouched.
- **[Fixed in passing]** CARD-441's `test_ring_and_divider` was never added to ADDED_SINCE_BEFORE, which reddened `test_the_family_collects_exactly_what_card_217_measured` on `main`; registered here.
