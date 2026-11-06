# CARD-384: Align the public player's crosshair colour and cell-size bounds with the admin solver's

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d)
<!-- Stated in review cycles at DRAFT time (see CARD-380). Basis, carried and not measured: the change itself is four declarations in player/player.css, but every layout-dependent pin written by CARD-324..327 and CARD-380 (the zoom premise, the hint module's margin constants, the crosshair, circles, maybe, pages and probe pixel tests) was measured at a 28 to 34 px cell and a grey crosshair, so the cost is in re-deriving them honestly. CARD-327 and CARD-380 each took 3c (1d) with similar ripple. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner question 2026-11-06 ("why the cell size and crosshair color is different between public player and the admin player's solver?"), then the owner ruling "align the crosshair colour with admin and I'd align the max-min cell size also". Both differences were deliberate when made (the public page is mobile-first and reached by QR code; its grey crosshair was chosen to stay clear of the hint line's green and the Maybe cell's beige), so this card REVERSES two design choices at the owner's request; it does not fix a defect. **Owner ruling 2026-11-06, second message: "I don't like to drop the minimum to 0, I like your min-max rule as a principle, but I'd have cells smaller by default".** Read as: KEEP the floor-and-cap mechanism (`clamp(min, fit, max)`) and a non-zero floor on every viewport; do NOT adopt the admin's `@media (max-width: 820px)` zero-floor rule; make the default bounds smaller than the public page's current 28 to 34 px, which the admin's 14 and 28 px are. If the owner meant other numbers, they will say so; the card uses the admin's values.
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-380
<!-- CARD-380 (probe mode) is in review and declares player/player.css, tests/test_public_player_agreement.py, tests/test_public_player_hint.py and tests/test_public_player.py as Touches, the same files this card edits; the two must not run concurrently. CARD-380's fix round also re-pins the zoom premise margins on a 1 px width sweep, which is the baseline this card re-measures against. -->
**Touches:** player/player.css, tests/test_public_player_agreement.py, tests/test_public_player.py, tests/test_public_player_zoom.py, tests/test_public_player_hint.py, tests/test_public_player_probe.py, tests/test_public_player_crosshair.py, tests/test_public_player_circles.py, tests/test_public_player_maybe.py, tests/test_public_player_pages.py
<!-- A starting list, over-declared in the conservative direction: the author derives which of these actually change by running them, and names any file outside the list as SCOPE+. The zoom module is on the list because its pinned premise is geometry (board height against the offset above it) and a 14 to 28 px cell changes both. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The public player (`player/player.css`) and the admin solver (`src/nonogram/admin/static/admin.css`) were built to look and behave as one player (CARD-328's agreement file holds them to it), with a short list of declared differences. Two of them are visible to anyone who opens both:

* **Cell size.** Public: `--player-cell-min: 28px`, `--player-cell-max: 34px`. Admin: `--player-cell-min: 14px`, `--player-cell-max: 28px`. The public bounds were chosen for a thumb (the `player.css` header says the admin's ~18 px cells at 390 px "are already on the backlog as too small to tap"), at the accepted cost that a 30 x 30 board does not fit a 390 px screen and scrolls sideways inside the stage.
* **Crosshair colour.** Public: `--player-cross: color-mix(in srgb, var(--color-text) 9%, var(--grid-paper))`, a cool grey, with `--player-cross-ink` mixed from it. Admin: `--player-cross: var(--color-surface-hover)` (`#f1ebdd`, a pale cream) with `--player-cross-ink` mixed from that. The agreement file declares the tint as a difference (`test_the_crosshair_sheet_rules_agree_and_the_tint_is_a_declared_difference`); the grey exists so the crosshair stays clear of the hint line's green and the Maybe cell's warm beige (see the `player.css` comments above `.is-hint-line`).

The owner asked for both to be aligned with the admin's. This card does that, MEASURES what it does to everything that was tuned around the old values, and reports it.

## What to implement

1. **Crosshair colour.** In `player/player.css`, make `--player-cross` and `--player-cross-ink` the admin's declarations (read them from `admin.css`, do not retype a value), and delete the now-false comments that justify the grey. Update the agreement file so the crosshair sheet rules AGREE: the declared tint difference is removed, and the test that asserted it becomes an equality with a plant that restores the old grey and reds.
2. **Cell bounds.** In `player/player.css`, set `--player-cell-min` and `--player-cell-max` to the admin's values (14px and 28px at the time of drafting: read them from `admin.css`). Add them to the agreement file's compared facts (admin and public declaration equal, with a one-sided plant that reds). Do NOT adopt the admin's `@media (max-width: 820px)` rule that drops the floor to 0px: the owner ruled against it ("I don't like to drop the minimum to 0"). The consequence is that on a phone a large board is wider than the screen and scrolls sideways inside the stage, as today but with smaller cells; the card reports it (AC-5).
3. **Re-measure everything that was tuned at the old values**, and re-pin it with the reason written in the test (ADR-0039/R3): the zoom module's premise (board height against the offset above it; sweep the viewport width at 1 to 2 px steps over 320..999 at heights 390 and 844 on the 30 x 30 board, as CARD-380's fix round does, not on the module's 40 px grid), the hint module's `WORST_MARGIN_PX` and `VIOLATIONS_WITHOUT_THE_SWAP`, the crosshair, circles, maybe, pages and probe pixel tests. A pin that moves is re-derived, not loosened to fit; a pin whose control cannot fail afterwards is a defect.
4. **Collisions are measured and REPORTED, not dodged.** With the cream crosshair, measure (dE76, the same method and floors the existing tests use) the crosshair against: the Maybe cell ground, the hint line tint (the public page's 18 % accent mix AND the panel's `--color-accent-tint`), the plain paper, the crossed filled-cell ground, the circle ring and the probe look. If any pair falls below the floor that its own test already holds, STOP that item and report the figures to the orchestrator; do not change the look to escape the collision (the owner chose the alignment). Where the panel's own accent tint is now distinguishable from the crosshair, REPORT whether the public hint tint's declared divergence could be dropped; do not drop it in this card.

## Acceptance criteria

* **AC-1** *Given* the public stylesheet, *then* `--player-cross` and `--player-cross-ink` are the admin's declarations and the agreement file holds the crosshair sheet rules EQUAL, with a plant that restores the grey and reds. (test: the re-pointed `test_the_crosshair_sheet_rules_agree...` in `tests/test_public_player_agreement.py`, named by the implementation)
* **AC-2** *Given* both stylesheets, *then* `--player-cell-min` and `--player-cell-max` are equal, held by the agreement file, with a one-sided plant that reds. (test: named by the implementation)
* **AC-3** *Given* the cream crosshair, *then* the distances in item 4 are measured and written into the tests as figures, each against a floor, and none is below its floor, OR the author stopped and reported. (test: named by the implementation; a stop is a legitimate outcome)
* **AC-4** *Given* every layout-dependent pin of the public-player modules, *then* each is green and re-derived (the fine-grid zoom sweep including widths 388 to 391 at height 844 and the 840 px column), with the reason for each moved constant written in the test. (test: the existing modules, edited only where a pin moved, with node ids compared)
* **AC-5** *Given* a 10 x 10, a 20 x 20 and a 30 x 30 board at 390 px wide and at 1280 px, *then* the cell size and whether the board scrolls sideways are measured before and after and recorded in the card's closing note. This is the owner-visible consequence (cells smaller than the 28 px thumb floor); it is a report, not a test. (check: review-lens, because a committed test cannot assert the owner's view of a tap target)
* **AC-6** *Given* the changed stylesheet, *then* `touch-action` is still `auto`, no solution reaches any public asset, and `player/solver_state.js` and `player/tokens.css` are byte-identical copies, unedited. (test: the existing AC tests of `tests/test_public_player.py`)

## Guardrails

* **G-1** `touch-action` stays `auto` (owner decision 2026-11-05).
* **G-2** Do not edit `solver_state.js` or `tokens.css` (ADR-0041/R3), and do not add a token to them.
* **G-3** Do not adopt the admin's `@media (max-width: 820px)` zero-floor rule (OWNER RULING: the floor stays above 0 on every viewport), and do not change the hint tint, the Maybe look, the circles look, the probe look or the zoom controls, in this card. Report the cases where the alignment makes one of those declarations untrue.
* **G-4** No test deleted, renamed, skipped or merged, `parametrize` ids included (node-id set difference with `-o addopts=`). A re-pointed test keeps its node id.
* **G-5** A constant that moves is re-derived from a measurement and carries its reason in the test; no tolerance is widened to make a pin pass.
* **G-6** Styling from tokens only; read the admin's values from `admin.css`, do not retype them.

## System contract

* ADR-0041/R2: no public asset carries a solution (check: AC-6)
* ADR-0041/R3: `solver_state.js` and `tokens.css` are byte-identical build-time copies (check: AC-6)
* ADR-0039/R1: a claim needs a control that can fail (check: AC-1, AC-2)
* ADR-0039/R3: a declared bound carries a reason and a measured residue, written in the test (check: review-lens)

## Lessons the author must be told

Read the Worktree notes of `meta/kanban/cards/CARD-324.md`, `CARD-325.md`, `CARD-326.md`, `CARD-327.md` and `CARD-380.md` on `main` first. CARD-380's review found that the zoom module's 40 px width grid skips real phone widths (388 to 391), so a green there proves little: use a 1 to 2 px sweep. The hint module holds `play.js` to a closed declaration census and a source scanner; this card edits CSS and tests, not `play.js`, so those should not move: if one does, say why.

## Worktree notes

(none yet)
