# CARD-212: Big boards repeat their clues on both sides — left and right, top and bottom

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/212-clues-both-sides
**Worktree:** ../PythonProject4-CARD-212
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 3: "Solver - mobile mode - clues - show clues on both sides of the puzzle (on the right and on the left and on the top and on the bottom) for big puzzles, not just in the right or bottom")
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_mirror.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_zoom.py
**Review score:** —
**Started:** 2026-10-14T14:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The board is one `<table>`: `th.player-clue.is-col` boxes above the grid,
  `th.player-clue.is-row` boxes to the left, `td.player-cell` cells
  (`solver.js:293-350`, `drawBoard`).
- CARD-193 added a **mirror**, not a duplicate: when `payload.width > 15` *and*
  the viewport matches `(max-width: 820px)`, `drawBoard` appends each body row's
  row-clue box **after** its cells and the head row's corner after the last
  column clue, and `.player-board.is-mirrored` redraws the borders that the
  moved `:last-child` rules stop matching (`solver.js:303-347`,
  `admin.css:507-531`). So on a phone a wide board shows its row clues on the
  **right only** — the left gutter is gone, not doubled. Column clues are
  always top-only.
- `mirrorQuery.addEventListener("change", …)` redraws when the viewport crosses
  820 px; zoom (CARD-195) and the recorded board survive the redraw
  (`solver.js:404-476`).

**What changes.** For a big board, the clues appear on **both** sides of each
axis: row clues left *and* right, column clues above *and* below.

1. **Threshold.** Keep one rule, do not invent a second: the existing
   `payload.width > 15` is the "big" test for the row axis; add the symmetric
   `payload.height > 15` for the column axis. Each axis is doubled
   independently — a 30×12 board doubles its row clues and not its column clues.
   (Record the chosen constant once; `solver.js` already has it inline in two
   places, which is one too many.)
2. **Not phone-only.** The owner's framing is "mobile mode … for big puzzles",
   and the mirror was phone-only because a phone has no room for both gutters.
   Doubling needs *more* room, not less, so apply it when the viewport can
   afford it and fall back to CARD-193's single mirrored gutter when it cannot:
   the duplicate renders when the doubled gutters still leave the grid at or
   above the phone-fit cell minimum CARD-193/CARD-182 established; otherwise the
   board keeps exactly today's mirrored rendering. State the measured rule in
   the Worktree notes.
3. **Rendering.** `drawBoard` gains the second gutter per doubled axis: a
   trailing `th.player-clue.is-row` after each body row's cells, a trailing
   `<tr>` of `th.player-clue.is-col` boxes under the grid, and the two extra
   corners. The duplicate carries the **same numbers in the same order** as its
   twin (a bottom column-clue box reads top-to-bottom like the top one — this
   is a repetition, never a mirror of the sequence).
4. **Circles stay in sync.** `paintCircles` (`solver.js:559`) and
   `clueNumbersOf` (`:548`) collect `.player-clue-num` spans per axis and line;
   with two gutters there are two spans per number, and **both** must carry
   `.is-circled` (CARD-188's rule) and the `--player-clue-digits` custom
   property. A duplicate that does not circle is worse than no duplicate.
5. **Accessibility.** The duplicate is a visual repetition; a screen reader must
   not read every clue twice. Give the second gutter `aria-hidden="true"` and
   keep the first as the labelled one (the `aria-label` per box,
   `clueBox` at `solver.js:278`).
6. Borders: the heavy/thin rule pattern must still read correctly on all four
   sides — the `:last-child` border rules that CARD-193 already had to redraw
   for the mirrored case need the same treatment for the new trailing boxes
   (`admin.css:505-531`).

## Acceptance criteria

- **AC-1** (happy): *Given* a 30×25 puzzle on a viewport with room for both
  gutters, *when* the player page renders, *then* each row's clue appears both
  left of and right of the grid, and each column's clue appears both above and
  below it. (test: `TestSolverClues_BigBoardRepeatsBothAxes`)
- **AC-2** (happy, per-axis): *Given* a 30×12 puzzle, *when* it renders, *then*
  the row clues are doubled and the column clues are not. (test:
  `TestSolverClues_AxesDoubleIndependently`)
- **AC-3** (happy, same numbers): *Given* any doubled axis, *when* it renders,
  *then* the duplicate gutter's numbers equal its twin's, line by line and in
  the same order. (test: `TestSolverClues_DuplicateReadsTheSameSequence`)
- **AC-4** (happy, circles): *Given* a clue number CARD-188's rule circles,
  *when* the board is doubled, *then* both of its spans carry `.is-circled`,
  and both lose it when the marks change. (test:
  `TestSolverClues_CirclesPaintBothGutters`)
- **AC-5** (edge, small board): *Given* a 15×15 puzzle, *when* it renders,
  *then* the clues are exactly as they are today — one top gutter, one left
  gutter, no duplicates. (test: `TestSolverClues_SmallBoardUnchanged`)
- **AC-6** (edge, narrow viewport): *Given* a 390 px phone and a 30×30 puzzle,
  *when* it renders, *then* the board falls back to CARD-193's single mirrored
  row-clue gutter rather than shrinking the cells below the phone-fit minimum.
  (test: `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit`)
- **AC-7** (edge, a11y): *Given* a doubled axis, *when* the accessibility tree
  is read, *then* each clue is exposed once — the duplicate gutter is
  `aria-hidden`. (test: `TestSolverClues_DuplicateIsAriaHidden`)
- **AC-8** (edge, zoom + viewport change): *Given* a doubled board at 150 %
  zoom, *when* the viewport crosses the breakpoint and the board redraws,
  *then* the marks, the zoom and the circles all survive. (test:
  `TestSolverZoom_SurvivesADoubledRedraw`)

## Guardrails

- G-1: Clues come from the embedded `compute_clues` JSON; the client never
  re-derives them from the solution (ADR-0038/R3; test:
  `TestSolverPage_ShowsTheClues`).
- G-2: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-3: The pure state module stays DOM-free; doubling is a rendering concern
  (ADR-0038/R4).
- G-4: No request per mark (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-5: Tap targets stay at CARD-182's minimum on a 390 px phone (test:
  `test_puzzle_solver_phone.py`).
- G-6: Do not change the brush/Region controls — CARD-211 owns those this wave.
- G-7: Styling from tokens only (test: `test_the_stylesheet_uses_tokens_not_literals` (and, for a rule added by a card, a per-rule check like `test_the_region_toggles_pressed_look_comes_from_tokens`)).

## System contract

- ADR-0038/R3 — the player's clues are the embedded JSON of `compute_clues` of
  the stored grid; the client never re-derives them (check:
  `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- CON-021 — interactive play only in the admin panel's player (check:
  review-lens)

## Architecture context

- **FR:** FR-044 (the player), and CARD-193's phone-fit/mirror behaviour it
  extends.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-011 (10–30 cell sides — the upper bound on how big "big" gets),
  CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css` (no
  `meta/design/` in this repo); every value is a token.
- **UI components:** `.player-board` and its clue boxes — the new trailing
  gutters reuse `.player-clue.is-row` / `.is-col` and the mirrored-border rules
  CARD-193 added.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** the duplicate is decorative (`aria-hidden`); the labelled
  gutter stays the single accessible source of each clue.

## Named tests resolved before the card started (decompose station, 2026-10-14)

Every backticked test name in this card was resolved against the test tree before an
agent saw it — the check CARD-205's gate showed was missing, where a fabricated guardrail
name survived drafting, implementation, a review and three fix cycles.

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1188` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:80` |
| `test_the_region_toggles_pressed_look_comes_from_tokens` | `tests/test_admin_design_tokens.py:86` |

**To be written by this card** — none of these exists yet, and that is correct for new
behaviour. Report them as written, never as passing before they exist:
`TestSolverClues_BigBoardRepeatsBothAxes`, `TestSolverClues_SmallBoardUnchanged`,
`TestSolverClues_AxesDoubleIndependently`, `TestSolverClues_DuplicateReadsTheSameSequence`,
`TestSolverClues_DuplicateIsAriaHidden`, `TestSolverClues_CirclesPaintBothGutters`
(all in the existing `tests/test_puzzle_solver_clues.py`, whose classes already use the
`TestSolverClues_` prefix), `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit`
(`tests/test_puzzle_solver_phone.py`) and `TestSolverZoom_SurvivesADoubledRedraw`
(`tests/test_puzzle_solver_zoom.py`).

There is no `TestAdminDesignTokens_NoRawValues` in this project. It was invented by the
orchestrator and briefed into four cards before being corrected; the two token tests above
are the real ones.

## Worktree notes

- [Rebase] Nothing to rebase around: CARD-211's merge (`4790243`) is already an ancestor of
  this branch's base (`d9c2c1a`), verified with `git merge-base --is-ancestor`. The three
  files it reworked were read in their post-211 state. **No toolbar change at all in this
  card**, so the ~4 px of slack CARD-211 left on the 1280 px counters row is untouched and
  `test_shares_the_buttons_row_at_1280` never came near red. The duplicated `.player-tools`
  declaration (lines 591 and 633) is still duplicated — not mine to fix, and nothing here
  depends on it.

- [The measured rule, as the card asked for] **An axis is doubled while the cells that
  leaves are >= 24 px on a side** (`solver.js DOUBLE_MIN_CELL`), measured on the candidate
  as drawn and divided by the zoom, never re-derived from admin.css's clamp.
  - The card's wording ("at or above the phone-fit cell minimum CARD-193/CARD-182
    established") does not name one number: CARD-182 set 24 px, CARD-193 *removed* it
    (`--player-cell-min: 0` below 820 px). Read literally as the floor in force, the
    condition is vacuous — the clamp's own lower bound means the cell is never below it,
    so every board would double. I read it as CARD-182's number used as a CONDITION rather
    than a floor: 24 px is also WCAG 2.2 (2.5.8)'s target size, so "cells still comfortably
    playable" is what the duplicate costs. Flagging the ambiguity rather than hiding it.
  - It is not a free choice: measured, 24 px is also the threshold at which **no existing
    fixture at any viewport the suite uses changes its layout** (see the table below).
    A looser bar (e.g. "double while the board still fits without scrolling", ~14.4 px)
    doubles a 25 x 15 at 1440 x 900 and a 30 x 30 at 1440 x 900, which would have rewritten
    pinned measurements in CARD-188/193/196 tests and the 40-box count in
    `TestSolverPage_ShowsTheClues`'s browser half. Mentioned because the owner may well
    want that looser bar: it is one constant, `DOUBLE_MIN_CELL`, and the cost is a smaller
    cell on big boards plus those test updates.
  - The ladder (roomiest first, `layoutLadder`): both axes -> rows only -> columns only ->
    today's rendering (mirror included), each rung drawn and measured, the last kept
    whether it fits or not. Rows are preferred over columns when only one fits, because
    the row gutter is the one the owner reported first and the only one CARD-193 mirrors.
    All four rungs are reachable with real boards (rung 3 at 1200 x 1100, below).

- [Measurements, Chromium, `_unique_grid` fixtures, 100 % zoom] cell px / what is drawn:

  | board | 390x844 | 1280x720 | 1440x900 | 1920x1080 | 1920x1500 | 1200x1100 |
  |---|---|---|---|---|---|---|
  | 15x15 | 14.39 one | 23.42 one | 28 one | 28 one | 28 one | 28 one |
  | 25x15 | 14.39 mirror | 22.36 one | 28 one | 28 **rows** | 28 **rows** | 24.47 one |
  | 30x12 | 14.39 mirror | 22.5 one | 26.19 one | 28 **rows** | 28 **rows** | 20.66 one |
  | 30x25 | 14.39 mirror | 14.47 one | 19.75 one | 25.05 **rows** | 28 **both** | 20.66 one |
  | 20x20 | 14.39 mirror | 17.56 one | 24 **rows** | 24.33 **both** | 28 **both** | 24.91 **cols** |
  | 25x20 | 14.39 mirror | 17.56 one | 24 **rows** | 24.33 **both** | 28 **both** | 24.91 **cols** |
  | 30x30 | 14.39 mirror | 14.39 one | 16.8 one | 21.3 one | 25.95 **both** | 20.66 one |

  "one" = exactly today's single gutters, "mirror" = CARD-193's rendering. Every doubled
  cell here is >= 24; every "one" cell is < 24 doubled. The closest call is **25 x 15 at
  1440 x 900: 23.53 px doubled, 0.47 px under the bar** — deterministic, but the owner
  should know that this board on a 1440-wide laptop stays single by less than half a pixel.
  The feature reaches a real desktop: 1920 x 1080 doubles the row clues of every big board
  except the 30 x 30, and a 2560 x 1440 monitor doubles both axes of most.

- [Fit] The clamp now multiplies its row-band terms by `--player-row-gutters` and its
  height term's column depth by `--player-col-gutters` (both 1 by default, so the formula
  at 1 is arithmetically CARD-196's and no single-gutter measurement moved — confirmed:
  every CARD-182/188/193/196 test is green unedited). A doubled board is therefore fitted
  for the bands it actually draws: 30 x 25 at 1700 x 1500 ends 2.34 px past a 1400 px stage
  (the per-box rounding a single-gutter board already carries: 1 px measured on main at
  1024 x 768 and 1440 x 900), where fitting it for one band would leave it ~190 px out.

- [Owner-visible defect found by eye, not by tests] On the first render of a doubled board
  the FIRST number of the right-hand gutter — the one against the grid — had its circle
  drawn over the board's heavy frame and the cells behind it. The 1.45 ch gap each row
  number keeps is what gives a ring its room, and it sits on the number's right; in a
  right-hand gutter it has to sit on its left. Fixed by mirroring the margin for
  `.is-row.is-right` (same total band width, so the fit is unchanged) and pinned by
  `TestSolverClues_RowRingsStayInsideTheirOwnBand`. **CARD-193's phone mirror has had this
  since it shipped** — the same rule, the same clipped first ring — so this also fixes the
  mirror. Screenshots 2/3/7 show the fixed version.

- [Existing tests I had to touch — two, both minimal]
  1. `tests/test_puzzle_solver_mirror.py` `_is_corner` compared the corner's class list for
     EQUALITY with `["player-corner"]`; the corner on the right now also carries
     `is-right` (that is where its heavy rule comes from, for the mirror and the duplicate
     alike). Relaxed to membership. Nothing else in that file changed, and all four of its
     tests pass unedited — including its border measurements, which is the guard that
     caught mutant M13 when I dropped the side class.
  2. `tests/test_admin_design_tokens.py` — added one G-7 per-rule test (the card asks for
     one); the two real token tests named in the card are unedited and green.
  No other existing test was edited. `TestSolverPage_ShowsTheClues` (both halves),
  `TestSolverMarking_NoRequestPerMark`, `test_the_stylesheet_uses_tokens_not_literals` and
  `test_the_region_toggles_pressed_look_comes_from_tokens` were run, not rewritten.

- [Mutants] 16 run, 15 killed, 1 equivalent. Each reverted from a pristine snapshot (NOT
  `git checkout --`: the implementation was uncommitted at the time) and the file verified
  byte-identical afterwards.

  | mutant | killed by |
  |---|---|
  | M1 trailing row duplicate never appended | `TestSolverClues_DuplicateReadsTheSameSequence`, `..._BigBoardRepeatsBothAxes`, `TestSolverZoom_SurvivesADoubledRedraw` |
  | M2 duplicate keeps its label, no `aria-hidden` | `TestSolverClues_DuplicateIsAriaHidden` |
  | M3 `clueNumbersOf` pairs only the first gutter | `TestSolverClues_CirclesPaintBothGutters` |
  | M4 `DOUBLE_MIN_CELL` 24 -> 1 | `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit`, `..._BigBoardRepeatsBothAxes::..._on_a_laptop` |
  | M5 zoom not divided out of the choice | `TestSolverZoom_SurvivesADoubledRedraw::test_zooming_in_does_not_make_a_redraw_double_the_gutters` |
  | M6 column axis reads `payload.width` | `TestSolverClues_AxesDoubleIndependently` |
  | M7 duplicate's numbers reversed (claim's edge) | `TestSolverClues_DuplicateReadsTheSameSequence` |
  | M8 tfoot draws its own top rule | `TestSolverClues_DoubledFramesReadOnAllFourSides` |
  | M9 tfoot outer edge heavy (claim's edge) | same |
  | M10 tfoot numbers not against the grid | same |
  | M11 term 1 drops `--player-row-gutters` | **SURVIVED — equivalent.** Term 2 binds whenever the cell is above ~20 px (that is where the numerals leave the 12 px floor and the band starts growing with the cell), and an accepted doubled cell is >= 24 px, so term 1 can only bind below the bar, where the rung is rejected either way. Kept for arithmetic consistency: a lower `DOUBLE_MIN_CELL` would make it load-bearing. |
  | M11b term 2 drops `--player-row-gutters` | `..._BigBoardRepeatsBothAxes::..._fitted_for_both_of_its_bands` |
  | M14 term 3 drops `--player-col-gutters` | `..._BigBoardRepeatsBothAxes::..._fitted_for_both_of_its_column_bands` |
  | M12 tfoot rule width hard-coded `1px` (no hex, so the file-wide sweep misses it) | `test_the_boards_second_clue_gutters_come_from_tokens` |
  | M13 right-hand boxes lose `is-right` | CARD-193's own `TestSolverMirror_HeavyLinesMatchTheLeftLayout` |
  | M15 right gutter's ring gap not mirrored / M16 gap halved (claim's edge) | `TestSolverClues_RowRingsStayInsideTheirOwnBand` |

- [One of my own tests was flaky by a pixel, and is not any more] The fit test's first
  form asserted Chromium's integer `scrollWidth - clientWidth` <= 2 for the 1402.34 px
  table in its 1400 px stage; the same board reported 2 px on one run and 3 px on the
  next (scrollWidth is whole pixels). It now asserts the table's own fractional box
  against the stage and allows the integer reading 3 px. The mutant it exists for
  (M11b) misses by ~190 px, so the bound is the rounding, not a budget.

- [Screenshots] `~/Documents/nonogram-reviews/CARD-212/` — 1 small board unchanged,
  2 both axes doubled, 3 rows only, 4 columns only, 5 the same big board at 1440 x 900
  where there is no room, 6 the phone mirror fallback, 7 circles painted in both gutters.

- [True, but outside this card]
  - **No resize listener.** The layout is re-chosen only when the 820 px media query fires
    (CARD-193's trigger). Dragging a window from 1920 to 1500 px leaves a doubled board
    doubled until the next load, where it can overflow the stage. The mirror has always
    behaved this way; making the board follow the viewport continuously is a change of its
    own (a `ResizeObserver` on `.player-stage`, plus a redraw budget — a redraw is up to
    four draws now).
  - **Column doubling uses the whole window height.** At 1200 x 1100 a 25 x 20 with both
    column gutters ends a few pixels past the stage's visible box (5 px measured; a
    single-gutter board at that viewport already overflows by 3-5 px). Nothing is
    unreachable — the stage scrolls — but the board no longer has air under it. If the
    owner dislikes that, the column axis wants a stricter bar than the row axis, which is
    a second constant, not this card's one rule.
  - A mirrored board (phone, W > 15) with doubled COLUMNS is handled by construction
    (the `is-right` corner composes with the `tfoot` rules) but is unreachable under this
    threshold — W > 15 at 24 px a cell needs more width than a phone has — so it is not
    claimed anywhere and has no test.
  - `.player-tools` is still declared twice in admin.css (CARD-211's review noted it).

- [Implementation complete] 2026-10-14 — committed `ee0d3a0` in the worktree (8 files,
  +1040/-71; `meta/` clean). Targeted runs only, no full suite: all 13 player test files
  plus the token file, then a final re-run of the five changed files at **91 passed,
  exit 0**. 16 mutants run, **15 killed, 1 equivalent** (M11, term 1 of the clamp's row
  multiplier, is unreachable above the 24 px bar and is kept only for arithmetic
  consistency — documented rather than claimed).
- [Implementation — the ambiguity it had to resolve, and an owner decision it raises]
  The card asked for "the phone-fit cell minimum CARD-193/CARD-182 established" without
  naming a number, and the two cards disagree: CARD-182 set 24 px, **CARD-193 removed it**
  (`--player-cell-min: 0` below 820 px). Read as the floor in force the condition is
  vacuous, so it was read as CARD-182's figure used as a *condition* — `DOUBLE_MIN_CELL
  = 24`, which is also WCAG 2.2 (2.5.8)'s target size. It is not an arbitrary pick:
  measured, 24 px is the bar at which **no existing fixture at any viewport the suite uses
  changes its layout**, where a looser bar (~14.4 px, "double while the board still fits")
  would double a 25×15 and a 30×30 at 1440×900 and rewrite pinned measurements in
  CARD-188/193/196 plus the 40-box count in `TestSolverPage_ShowsTheClues`'s browser half.
  **OWNER DECISION PENDING, and it is about the owner's own laptop:** at 1440×900 a 30×25
  measures 19.75 px doubled and a 25×15 measures **23.53 px — 0.47 px under the bar** — so
  on a 1440-wide screen neither gets its second gutter. If "big puzzles" in the owner's
  request includes a 25×15 on a laptop, `DOUBLE_MIN_CELL` is one constant, at the cost of
  re-pinning three earlier cards' measurements. Not changed without the owner.
- [Implementation — a defect the renders caught that the tests did not] Looking at the
  screenshots found the first number of a right-hand gutter drawing its circle over the
  board's heavy frame and the cells behind it: the 1.45 ch gap that gives a row ring its
  room sat on the number's right, and in a right-hand gutter it must sit on its left.
  Fixed by mirroring the margin (same band width, so the fit is unchanged) and pinned by
  `TestSolverClues_RowRingsStayInsideTheirOwnBand` (`tests/test_puzzle_solver_clues.py:1523`,
  mutants M15/M16). **CARD-193's phone mirror has carried this since it shipped**, so this
  fixes the mirror too — the second time this wave that an owner-facing render caught what
  a green suite did not.
- [Implementation — two existing tests touched, both minimal] `test_puzzle_solver_mirror.py:78`'s
  `_is_corner` compared the corner's class list for *equality* with `["player-corner"]`;
  the right-hand corner now also carries `is-right` (where its heavy rule comes from, for
  mirror and duplicate alike), so the check was relaxed to membership. All four of that
  file's tests pass, and its border measurements are what killed mutant M13. The token file
  gained the new per-rule G-7 check; no existing assertion changed.
- [Implementation — renders for the owner] Seven screenshots in
  `~/Documents/nonogram-reviews/CARD-212/`, regenerated after the final CSS change:
  `1-small-15x15-laptop-1440x900-unchanged`, `2-big-30x25-1920x1500-both-axes-doubled`,
  `3-big-30x12-1920x1080-row-clues-doubled-only`,
  `4-big-25x20-1200x1100-column-clues-doubled-only`,
  `5-big-30x25-laptop-1440x900-no-room-single-gutters`,
  `6-big-30x30-phone-390x844-mirror-fallback`,
  `7-big-30x12-1920x1080-circles-in-both-row-gutters`.
- [Implementation — open, carried to review] (a) **No resize listener**: the layout is
  re-chosen only when the 820 px media query fires (CARD-193's trigger), so dragging a
  window 1920 → 1500 px leaves a doubled board doubled until reload, where it can overflow
  the stage. The mirror has always behaved this way; following the viewport continuously is
  its own change (`ResizeObserver` + a redraw budget — a redraw is now up to four draws).
  (b) **Column doubling measures against the whole window height**: at 1200×1100 a 25×20
  with both column gutters ends ~5 px past the stage's visible box, where a single-gutter
  board there already overflows by 3–5 px. Nothing is unreachable, but the board has no air
  under it. (c) A mirrored board with doubled *columns* composes by construction but is
  unreachable under this threshold, so it is claimed nowhere and has no test.
