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
**Wave:** 38
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

- [Review cycle 1] 2026-10-14 — **7.0/10, below the 8 gate. 0 critical, 3 Important (all
  gating), 5 minor.** Report: `meta/review/20261014T153035Z-CARD-212-cycle1.yml`. Reviewer's
  confidence high; every figure in it came from a command they ran, including a real Chromium
  AX-tree dump and a timing probe applied and reverted.
  - **F-001 — a doubled board cannot survive a window resize.** One page load of a 30x25,
    resized without ever crossing 820 px: `1920x1500 dup=55 cell=28.00, no overflow` ->
    `1100x900 dup=55 cell=14.39, stage overflow x=176` -> `900x800 dup=55 cell=14.39, x=376
    y=44`; **reloaded at 900x800 the same board is dup=0, 14.39 px, no overflow at all.** So the
    card's own rule is violated by 1.7x, with 376 px of sideways scroll the pre-card board did
    not have. **The implementation's reason for deferring it was wrong, and this is the finding
    worth remembering:** "the mirror has always behaved this way" is false, because the mirror's
    condition *is* the media query it listens to and so can never be stale. This card is the
    first to put a **continuous** condition behind a **discrete** trigger.
  - **F-002 — the ladder costs ~4x the time-to-board on the commonest desktop case.** Same
    board, same viewport, identical final DOM; only the rung count differs. 30x30 at 1280x720,
    **4 rungs: 807/907/951 ms, DCL 732 ms** against **1 rung: 125/218/228 ms, DCL 129 ms**;
    control at 2560x1440 (2 rungs) 474/490 vs 133/229. ~600-700 ms of wasted work on the largest
    supported board, paid by exactly the boards that gain nothing — and it is the stated reason
    F-001 was deferred. Doubling is monotone (it only grows a subtrahend or a denominator), so
    drawing the fallback rung first and early-outing is sound: 4 draws become 1 in the common
    case. Pin it with a **draw count**, not a timing.
  - **F-003 — the 24 px justification is false, and the band it switches on is untested.** The
    claim "24 px is the bar at which no existing fixture at any viewport the suite uses changes
    its layout" does not hold: `AC_GRID` 25x15 (`tests/test_puzzle_solver_page.py:98`) doubles
    at 1440x900, `AC301_GRID` 20x20 (`:100`) doubles at 1440x900, `GRID_16_WIDE` 16x15
    (`tests/test_puzzle_solver_mirror.py:46`) doubles at 1440x900 **and** 820x900. The suite is
    green only because no test pairs those fixtures with those viewports. At the suite's default
    1280x720, row doubling is on for **11 of 28 shapes** swept (16x10 .. 22x14) — and the one
    existing guard covering that ground, `_assert_every_fifth_line_heavier`
    (`tests/test_puzzle_solver_page.py:630`), **goes red when pointed at a 20x12 there**
    ("Left contains 12 more items" — it compares 2x-height clue boxes against `height-1`). Its
    caller's seeded 12-size corpus avoids the band by luck. The true sentence is "no fixture x
    viewport **pair** the suite exercises".
  - **Confirmed, no finding:** M11 really is equivalent (term 1 binds only below 20 px, under
    the bar) — the implementation's equivalence argument stands as written. The ring fix is real
    and so is its claim about CARD-193: on the phone mirror itself, worst-case clearance is
    **+7.75 px at HEAD against -2.72 px with the pre-fix margin restored**. Accessibility is
    clean on a real AX tree: 25 rowheaders, 30 columnheaders, **zero duplicate names**. Both
    touched tests are fine. All 8 engaged ADR-0038 rules and all 7 guardrails hold.
  - **Minor (non-gating):** F-004 `.is-mirrored` now styles nothing while a new comment presents
    it as the marker; F-005 the "23.53 px / 0.47 under" headline reproduces as 23.47 and a third
    25x15 fixture doubles there; F-006 a column-band fit asserts <=10 on a measured 5; F-007 the
    new token test's regex can swallow comment text; F-008 "only the rung that stays is ever
    painted" is not demonstrated.
- [Orchestrator correction, owed] F-003 falsifies a sentence **the orchestrator put in front of
  the owner**, not just one in the notes: the 24 px decision was presented with "no existing
  fixture at any viewport the suite uses changes layout". The owner's choice to keep 24 px
  stands — the suite is green, nothing in CARD-188/193/196 needs re-pinning, and that was the
  substance of the option — but the justification was stronger than the measurement. Fix the
  sentence wherever it appears, in the notes and in the code comments.

## Implementation agents' own records (verbatim, synced from the worktree 2026-10-14)

_The ledger above is the orchestrator's, one record per station. This is the implementation
and fix agents' own, copied out of the worktree before it is discarded. Where the two
disagree, the ledger is authoritative._

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
  - It is not a free choice: measured, 24 px is the threshold at which **no fixture x
    viewport PAIR the suite actually exercises changes its layout** (see the table below).
    **Corrected at review cycle 1 (F-003):** my first wording — "no existing fixture at
    any viewport the suite uses" — is false, and I repeated it to the orchestrator. Three
    fixtures DO change layout at viewports the suite uses elsewhere; re-measured by me at
    HEAD: `AC_GRID` 25x15 (`tests/test_puzzle_solver_page.py:98`) draws 15 duplicates at
    1440x900 (24.36 px), `AC301_GRID` 20x20 (`:100`) draws 20 (24.88 px), `GRID_16_WIDE`
    16x15 (`tests/test_puzzle_solver_mirror.py:46`) draws 15 at 1440x900 (28 px) and at
    820x900 (25.66 px). No test pairs those fixtures with those viewports, which is the
    only reason the suite is green on them — luck, not a property of the bar.
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
  1440 x 900: 23.47 px doubled, 0.53 px under the bar** (re-measured at review cycle 1,
  F-005: my first figure, 23.53/0.47, does not reproduce) — and it is a property of the
  GRID, not of the size. The clamp reads the deepest row clue, so the CARD-182/193 25x15
  fixtures measure 23.47 px and stay single while `AC_GRID`, a 25x15 with a shallower
  deepest clue, measures 24.36 px and DOES double. The owner should choose with that
  spread in view, not with one number.
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
     alike). Relaxed to membership. Nothing else in that file changed, and all five of its
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
  - ~~**No resize listener.**~~ FIXED at review cycle 1 (F-001), and my reason for
    deferring it — "the mirror has always behaved this way" — was **wrong**: the mirror's
    condition IS the media query it listens to, so it can never be stale, while this
    card's is a continuous measurement behind that discrete trigger. See the cycle-2
    section below.
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

### Review cycle 1 — fixes (7.0/10, gate 8; 0 critical, 3 Important, 5 minor)

- **F-001 (gating) — a doubled board now follows the window, not only the breakpoint.**
  A trailing-debounced `resize` listener (RESIZE_SETTLE = 150 ms) calls the existing
  `redraw()`, guarded by the same `width > BIG_SIDE || height > BIG_SIDE` test as the
  media-query listener. Measured on the reviewer's own walk (30 x 25, one page load at
  1920 x 1500, never crossing 820 px): before, `1100x900 dup=55 cell=14.39 ovX=176` and
  `900x800 dup=55 cell=14.39 ovX=376`; after, `1100x900 dup=0 cell=17.63 ovX=1` and
  `900x800 dup=0 cell=14.39 ovX=104`, **byte-for-byte what a reload at each of those
  windows gives** (I measured the reload in the same session: `900x800 dup=0 cell=14.39
  ovX=104`, `1100x900 dup=0 cell=17.63 ovX=1`). The review's reload baseline said "no
  overflow at all" at 900 x 800; I could not reproduce that half — a 30-wide board at a
  600 px stage is floor-bound and scrolls on a reload too — so the claim I make is the
  one I can prove: **after a resize the board is exactly the board a reload would have
  drawn.** Two tests in `tests/test_puzzle_solver_zoom.py`, inside the AC-8 class:
  `test_a_resize_that_never_crosses_the_breakpoint_rechooses_the_layout` (marks, zoom and
  circles survive both ways) and `test_a_resize_settles_on_the_layout_a_reload_would_have_given`
  (resize == reload, asserted as equality of the whole measured shape).
  Accepted cost, stated rather than hidden: a resize-redraw drops the hinted cell's
  highlight, exactly as a breakpoint-crossing redraw has since CARD-193.

- **F-002 (gating) — the ladder draws today's rendering first and early-outs.**
  `drawSettledLayout` draws the plain board, and only if THAT clears the bar does it try
  the doubled rungs (doubling is monotone: each gutter adds a subtrahend to both width
  terms and a band to the height term, so a plain board under the bar can never be
  rescued). If no rung fits, the plain table already built is re-inserted rather than
  rebuilt. Draw counts, measured through a new `performance.mark` per board built
  (DRAW_MARK), before -> after:

  | board @ viewport | draws before | draws after | duplicates |
  |---|---|---|---|
  | 30x30 @1280x720 | 4 | **1** | 0 |
  | 30x25 @1440x900 | 4 | **1** | 0 |
  | 15x15 @1280x720 | 1 | 1 | 0 |
  | 22x14 @1280x720 (plain clears the bar, the rung misses) | 2 | 2 | 0 |
  | 20x12 @1280x720 | 2 | 2 | 12 |
  | 30x12 @1920x1080 | 2 | 2 | 12 |
  | 30x25 @1920x1500 | 1 | 2 | 55 |
  | 30x25 @1920x1080 | 2 | 3 | 25 |

  So the case the reviewer timed at ~810 ms (30 x 30 at 1280 x 720, four draws) is now one
  draw; a board that CAN afford a duplicate pays one extra draw for the plain probe, which
  is the trade the early-out makes. Pinned by draw count, not by timing
  (`TestSolverClues_TheLadderStopsAtTheFirstRungThatFits`), because a timing assertion on
  this suite would be flaky and would not say what is meant.

- **F-003 (gating) — the false claim corrected, and the band it hid now covered.**
  (a) The justification is rewritten above with the three fixture x viewport pairs named.
  (b) `_assert_every_fifth_line_heavier` (`tests/test_puzzle_solver_page.py:630`) and the
  `_RULES` probe now group the clue boxes by `data-line` and assert the fifth-line pattern
  PER GUTTER, so a doubled board is checked instead of crashing the helper ("Left contains
  12 more items"). (c) `(20, 12)` is added to the seeded corpus of
  `test_PropertyTest_every_size_...` — at 1280 x 720 that size doubles — and the test now
  also asserts `doubled >= 1`, so the corpus can never drift back out of the band silently.
  (d) Two new tests in `tests/test_puzzle_solver_clues.py`
  (`TestSolverClues_MidSizeBoardsDoubleOnAnOrdinaryLaptop`): a 20 x 12 at 1280 x 720 draws
  both row gutters at 26.88 px with the same numbers and the same heavy fifth-line rules in
  each, and a 22 x 14 there — plain 24.59 px, doubled rung just under the bar — draws one.
  The bar itself is unchanged at 24 px (owner's decision).

- **F-004 (minor, done)** — admin.css's comment now says plainly that no rule selects
  `.is-mirrored` any more and that it is a state marker only.
- **F-005 (minor, done)** — re-measured; 23.47 / 0.53 px, with the AC_GRID spread, in the
  table's paragraph above.
- **F-006 (minor, done)** — the column-band bound is `<= 6` on a measured 5 (was `<= 10`),
  with the docstring saying it is the known residue and not a budget.
- **F-007 (minor, done)** — the per-rule token test strips `/* ... */` before scanning, so
  a comment mentioning `.is-right` can no longer be read as a selector.
- **F-008 (minor, done)** — redraw()'s comment no longer claims the discarded rungs are
  never "painted"; it says what is true and checkable: they are replaced within the same
  task, so no frame is produced from one, and only the rung that stays is wired. The notes'
  "all four of its tests" is corrected to five.
- **C-2's suggestion (done, not a finding)** — the ring-clearance test is now also run on
  CARD-193's phone mirror (390 x 844, `.is-mirrored`), the board that carried that defect
  longest, not only on the 1920 x 1500 duplicate.

- [Cycle-2 mutants] 8 run, 8 killed, each reverted from a pristine snapshot and the file
  verified byte-identical:

  | mutant | killed by |
  |---|---|
  | M17 resize listener returns immediately | `..._rechooses_the_layout` |
  | M18 resize guard ignores the board size (a 15x15 redraws) | `..._a_board_too_small_to_double_is_not_redrawn_by_a_resize` |
  | M19 early-out removed, every rung walked again | `TheLadderStopsAtTheFirstRungThatFits[30x30]` |
  | M20 early-out accepts any plain board (`< 0`) | same |
  | M21 the missed-rung path rebuilds instead of re-inserting | `TheLadderStops...[22x14]` (3 draws, not 2) |
  | M22 the fifth-line helper flattens the gutters again | `TestSolverPage_EmphasisesEveryFifthLine` property test |
  | M4 (re-run against the fixed tests) threshold 24 -> 1 | `TheLadderStops...`, `MidSizeBoards...` |
  | M3 (re-run) `clueNumbersOf` pairs only the first gutter | `CirclesPaintBothGutters` |

- [Still open, with reasons]
  - **Column doubling uses the whole window height** (unchanged from cycle 1): a 25 x 20
    with both column gutters ends ~5 px past the stage's visible box at 1200 x 1100. Now
    pinned at `<= 6` rather than `<= 10` (F-006). A stricter bar for the column axis is a
    second constant and an owner decision, not this card's one rule.
  - **The mirrored + doubled-columns composition** stays unreachable under a 24 px bar and
    therefore untested and unclaimed; the review confirmed it composes by construction.
  - **M11 stays equivalent** — the reviewer re-derived the 20 px threshold algebraically and
    measured ten board/viewport pairs identical. Left as documented, not killed.

- [Fix cycle 1 complete] 2026-10-14 — committed `7c2ed8d` in the worktree. All three gating
  findings closed with measurements, all five minors done, **8 mutants run and 8 killed**, each
  reverted from a pristine snapshot with the file verified byte-identical.
  - **F-001** — a trailing-debounced `resize` listener now runs the same `redraw()`, guarded by
    the same "is this board big" test, and the resized board is asserted to be *the board a
    reload would have drawn* rather than merely "not stale". Killed by M17 (listener returns
    immediately) and M18 (guard ignores board size, so a 15x15 redraws).
  - **F-002** — today's rendering is drawn **first** and nothing else is drawn at all when it is
    already under the bar, on the monotonicity argument the reviewer supplied. Measured draw
    counts: **30x30 @1280x720 goes 4 draws -> 1**, 30x25 @1440x900 4 -> 1. A board that *can*
    afford a duplicate pays one extra draw for the plain probe (30x25 @1920x1500 goes 1 -> 2) —
    that is the trade the early-out makes, and it is recorded rather than hidden. Pinned by a
    `performance.mark` **draw count**, not a timing, exactly as the review asked.
  - **F-003** — the false sentence is corrected everywhere with the three fixture x viewport
    pairs named; `_assert_every_fifth_line_heavier` now groups by `data-line` and checks the
    pattern **per gutter** instead of crashing on a doubled board; `(20, 12)` joins the seeded
    corpus **with an assertion that at least one member doubles**, so the corpus cannot drift
    back out of the band silently; and two new tests pin both sides of the boundary at
    1280x720 (a 20x12 that doubles at 26.88 px, a 22x14 that does not).
  - The ring-clearance pin now also runs on **CARD-193's phone mirror**, the board that carried
    that defect longest — the reviewer's suggestion, taken.
  - **Still open, with reasons given:** column doubling measures against the whole window height
    (~5 px past the stage's visible box at 1200x1100, now pinned at `<= 6` instead of `<= 10`);
    the mirrored + doubled-columns composition is unreachable under a 24 px bar and so stays
    unclaimed and untested; M11 remains equivalent, which the reviewer independently re-derived.
