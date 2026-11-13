# CARD-443: The probe's marker a bit more visible — on the board, in the strip and on the map

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5c (0.1d)
<!-- Basis: two custom properties, three outline widths and a state class on the map's probe edge; the cost is keeping the measured separations and a black cell readable. -->
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/443-probe-marker-stronger
**Worktree:** ../PythonProject4-card-443
**Source:** owner 2026-11-13 (project thread): *"please make contradiction-probing cells a bit more visible"*.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-268, CARD-442
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/solver.js, player/player.css (the lesson's probe edge, pinned to the player's), tests/test_admin_design_tokens.py, tests/test_puzzle_solver_probe.py
**Review score:** — (no review cycle; owner request, 2026-11-13)
**Started:** 2026-11-13T12:15Z
**Closed:** 2026-11-13T12:45Z
**Actual:** —
**Merge commit:** f0b04af2
**Blocked by:** —

## Why

The probe's dashed ring on a light cell was 86 % of the warning hue (rgb(150, 115, 35), 4.33:1 on paper) at the heavy rule's 2 px; on a phone's 12-14 px board cell it read as a faint frame.

## What to implement

The marker stays an OUTLINE (the owner's 2026-10-30 channel ruling, CARD-268 F-001: a ground tint collided with the crosshair's), so "more visible" is colour and width, not a fill:

1. `--player-probe` is `--color-warning` itself: rgb(133, 93, 0), 5.80:1 on paper. `--player-probe-ink` (the light amber for black cells, 8.22:1 on ink) unchanged.
2. The board's ring is 1.5 x the heavy rule (3 px) on a light cell; a black cell keeps 2 px, because a 3 px light ring left too little black to read as black.
3. The strip's ring 2 -> 4 px (its cells are about 23 x 48 px).
4. The map's probe edge is 2 px and classed by state: dark amber on a light cell, light amber on a black one (it was the light amber everywhere at 1.5 px, faint on paper).

## Acceptance criteria

- **AC-1** (colour and the census): the probe's colour rules are token-only and the census of rules naming the probe colours lists the map's filled-cell rule. (test: `test_the_probe_tint_comes_from_tokens`, which reds on `main`'s stylesheet)
- **AC-2** (still apart from every ground, dashed, not a fill): `TestSolverProbe_TheMarkerIsMeasurablyApartFromItsGround` — ring dashed, non-zero, dE76 over the floor on all six grounds, the ground not repainted — unchanged and green.

## Worktree notes
- **[Measured, 2026-11-13]** Before/after at 390x844 on a 30 x 30 with a black, a white and a "?" probe cell beside an ordinary black mark: `~/Documents/nonogram-reviews/CARD-443/`. A first cut widened the black cell's ring to 3 px as well; on the board its black centre shrank to about 6 px and read as amber, so that one width was put back.
- **[Gate, 2026-11-13]** The 13 player/probe/line/lesson files: 537 passed, 3 red, then all re-run green after two deliberate updates and one flake: `test_the_lesson_uses_tokens_and_the_players_probe_colours` pins the lesson's probe colour to the player's (the lesson now matches, widths too); `test_the_four_states_stay_apart_under_the_tint` held ONE ring width on all four states, now one per ground with the filled ring narrower (its comment keeps the old claim); `test_the_check_is_green_on_the_real_files_and_red_on_the_mutant[hintLine-reads-the-solution-ungated]` passed on its own re-run, untouched by this card.
