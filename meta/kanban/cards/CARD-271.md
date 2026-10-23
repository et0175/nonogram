# CARD-271: Big boards lose their bottom and left clues — keep clues in view whatever the fit ladder decides

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/271-clues-stay-in-view
**Worktree:** ../PythonProject4-card-271
**Source:** quick — owner bug report 2026-10-22: "clues sometimes are missed at the bottom and at the left for big puzzles"; no handoff increment
**Idea:** —
**Wave:** 55
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_zoom.py
**Review score:** —
**Started:** 2026-10-23T15:05Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, with its mechanism verified in the code

**Symptom (owner).** On big puzzles the clues are sometimes missing at the
bottom and at the left.

**Mechanism — three converging causes, all by design, which is why "sometimes":**

1. **The plain-first bar.** `drawSettledLayout` (`solver.js:735`) draws
   today's single-gutter board first and tries no duplicate at all when its
   cells are already under `DOUBLE_MIN_CELL` (24 unzoomed px,
   `solver.js:395`). The code's own comment measures the consequence: at
   1280×720 that is *every board from about 24 columns up*. So the biggest
   puzzles — the ones CARD-212's duplicates were built for — are exactly the
   ones that render without bottom (and right) clues.
2. **The ladder prefers the row axis.** When both axes are big but only one
   duplicate fits, `layoutLadder` (`solver.js:660`) tries
   `{rowGutters: 2, colGutters: 1}` before `{colGutters: 2}` — the bottom
   clues are the first to be sacrificed.
3. **The mirror removes the left gutter on phones.** At ≤ 820 px with
   width > 15, CARD-193 draws the one row-clue gutter on the *right*
   (`isMirrored`, `solver.js:646`) — by owner decision, so on a phone a big
   board can lack both the left clues (mirror) and the bottom clues (cause 1).

And across all three: the gutters are ordinary table rows/columns, so once the
board overflows `.player-stage` (big board, or any board zoomed to 300%),
whatever gutter scrolls out of the viewport is simply gone — nothing keeps a
clue in view while the player works at the far corner. CARD-212's own stated
intent was *"a player scrolled to the far edge still has clues in view"*; the
duplicates deliver that only when they fit, and causes 1–3 are precisely the
cases where they don't.

## What to implement

**Keep clues in view on both axes, at every board size, scroll position and
zoom — without undoing any CARD-212/CARD-193 decision.** Recommended
mechanism: **sticky gutters as the fallback.**

1. When an axis renders with a single gutter (duplicate didn't fit, or the
   mirror holds), that gutter's clue boxes become `position: sticky` against
   the board's scroll container — column clues stick to the top (or the
   bottom, for a tfoot gutter), row clues to the left (or the right when
   mirrored) — so the clues stay in view wherever the player scrolls or
   zooms. Sticky boxes need an opaque background (`.player-clue` already has
   `var(--color-surface)`) and a z-index above cells; the corner boxes stick
   on both axes.
2. When a duplicate *does* fit, CARD-212's behaviour is untouched: same
   ladder, same rungs, same draw counts — the duplicates may also be sticky,
   but nothing about which layout is chosen changes.
3. Verify at implementation that `.player-stage` is the scroll container
   sticky resolves against (Chromium supports `position: sticky` on `th`/`td`
   in a scrolling block; if the overflow actually lives on an ancestor, say
   so and move it or stick against that — a finding, not a silent fix).
4. The heavy-rule pattern, circles (both twins), `.is-hinted`, the crosshair
   (CARD-267, if merged first) and the solved outline must all render
   correctly on and under sticky boxes — cells scroll *under* the gutter, so
   the gutter's own borders must fully cover its edge.
5. No layout decision moves into the state module: this is rendering
   (ADR-0038/R4), `solver_state.js` is not edited.

Out of scope, recorded: changing `DOUBLE_MIN_CELL`, the ladder order, or the
mirror decision. If the owner would rather lower the bar or re-order the
ladder instead of (or beside) sticky, that is an owner decision to surface at
the render, not a choice the implementation makes.

## Acceptance criteria

- **AC-1** (happy, the reported case): *Given* a 30×30 board at 1280×720 —
  today a plain board, cells under the doubling bar — *when* the stage is
  scrolled to the bottom-right cells, *then* that row's row clues and that
  column's column clues are inside the viewport (bounding-rect assertion),
  and the cells scrolled past are under, not over, the gutters. (test:
  `TestSolverClues_StayInViewOnAPlainBigBoard`)
- **AC-2** (happy, phone + mirror): *Given* a 30×30 board at 390 px (mirrored:
  row clues on the right only), *when* the board is scrolled in both axes,
  *then* the right row-clue gutter and the column-clue gutter remain in view.
  (test: `TestSolverPhone_MirroredGutterSticks`)
- **AC-3** (happy, zoom): *Given* any big board at 300 % zoom, *when* the
  stage is panned to each corner, *then* at least one clue box of the current
  row and of the current column is in view at every position. (test:
  `TestSolverZoom_CluesStayInViewWhileZoomed`)
- **AC-4** (edge, CARD-212 untouched): *Given* boards where the duplicates
  fit, *then* the ladder settles on exactly the rungs it settles on today —
  `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` and the whole
  existing clue/phone/zoom suites pass with their assertions unedited (new
  tests are added; existing ones only gain nothing). (gate: the named class,
  unedited)
- **AC-5** (edge, small board): *Given* a 15×15 board that fits its stage,
  *then* nothing observable changes: no scrolling, gutters where they are
  today, all existing small-board assertions green. (test:
  `TestSolverClues_SmallBoardsUnaffectedByStickiness`)
- **AC-6** (edge, visual integrity): *Given* a sticky gutter with the board
  scrolled behind it, *then* the gutter's background is opaque, its heavy
  rule edge is drawn, and circled clue numbers (CARD-188) render on it
  exactly as on a static gutter. (test:
  `TestSolverClues_StickyGutterRendersCleanly`)

## Guardrails

- G-1: `DOUBLE_MIN_CELL`, `BIG_SIDE`, `layoutLadder`'s rung order and
  `isMirrored` are not changed — this card adds visibility, it does not
  re-litigate fit (the owner may re-open those separately after seeing the
  render).
- G-2: Hand-written JS/CSS, tokens only (ADR-0038/R1; tests:
  `test_the_stylesheet_uses_tokens_not_literals`, plus a per-rule check if
  the fix adds colored values).
- G-3: `solver_state.js` is not edited (ADR-0038/R4); no request per mark or
  per scroll (ADR-0038/R2; test: `TestSolverMarking_NoRequestPerMark`).
- G-4: Marks, history, save, hint, circles and progress are untouched by
  scrolling — a scroll or a sticky repaint records nothing and saves nothing
  (CON-021).
- G-5: The redraw path keeps its draw-count pins: the ladder tests that count
  draws by draw marks run unedited (AC-4).
- G-6: The three renders — big board at desktop, phone width, 300 % zoom — are
  **produced and handed to the owner**, written to
  `~/Documents/nonogram-reviews/CARD-271/`. <!-- AMENDED 2026-10-23 by owner
  decision: "да, мержи по гейтам". As written this guardrail said *before
  merge*, which contradicts the owner's standing instruction that merges go on
  gates and renders are reviewed AFTER landing. The renders are still mandatory;
  what is not mandatory is waiting on an eyeball to merge. A reviewer must not
  file this as unsatisfied when the renders exist and the gates passed. -->

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R3 — clues are the embedded JSON of `compute_clues`; the client
  never re-derives them (check: `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- CON-021 — play state persists only in this browser's localStorage; nothing
  per scroll (check: review-lens)

## Architecture context

- **FR:** FR-044 — this completes CARD-212's stated intent ("a player
  scrolled to the far edge still has clues in view") for the cases its
  duplicates cannot cover, and preserves CARD-193's mirror decision.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-011 (30×30 is the biggest board — the worst case is bounded),
  CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; sticky needs
  no new colors — background and rules already exist on `.player-clue`.
- **UI components:** `.player-clue` boxes and corners gain stickiness; no new
  elements.
- **Screens:** `/puzzles/<id>/solve` (and the editor's board, which shares
  the stylesheet — confirm no editor regression on the render).
- **Standards:** gutters opaque over scrolled cells; no animation on stick;
  the accessibility tree is unchanged (sticky is visual only).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits` | `tests/test_puzzle_solver_clues.py:2114` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** (across `tests/test_puzzle_solver_clues.py`,
`tests/test_puzzle_solver_phone.py`, `tests/test_puzzle_solver_zoom.py`) —
none exists yet; report them as written, never as passing before they exist:
`TestSolverClues_StayInViewOnAPlainBigBoard`,
`TestSolverPhone_MirroredGutterSticks`,
`TestSolverZoom_CluesStayInViewWhileZoomed`,
`TestSolverClues_SmallBoardsUnaffectedByStickiness`,
`TestSolverClues_StickyGutterRendersCleanly`.

## Worktree notes

- **[The "sometimes" is now enumerable]** The three causes above predict
  exactly when clues go missing; AC-1..AC-3 pin one representative of each.
  If reproduction finds a *fourth* way (e.g. a resize race in `redraw()`),
  that is a finding to record here, not to fold silently into the fix.
- **[Sticky-in-table risk]** `position: sticky` on table cells has
  per-browser quirks; the suite runs Chromium only (ADR-0038/R8), so assert
  what Chromium does and record the bound — other browsers are untested, and
  that is the project's standing browser-test boundary, not this card's gap.
- **[Conflict note]** Touches overlap CARD-267 (crosshair: `solver.js`, CSS)
  and CARD-269 (hint ladder: same files) and CARD-270 (`admin.css`,
  `tokens.css`); the dispatcher serializes same-wave overlaps. If CARD-267
  merges first, AC-6's "renders cleanly" check includes the crosshair tint on
  a sticky gutter.

## [Dispatch note 2026-10-23] Two prerequisites measured before the brief, because both could have made this card unverifiable

**1. Every one of AC-1..AC-6 is a browser test, and ADR-0038/R8 says they fail or skip *loudly*.** If
Chromium were absent they would all **skip green** and the card would "pass" having verified nothing —
the green-with-skips shape this board has already carded (a skipped run reports the same collected count
and the same exit 0 as a verified one; only the **passed** count separates them). Measured before
dispatch: `playwright` imports, five Chromium builds are in `~/Library/Caches/ms-playwright/`, and the
card's three test files run **105 passed, 0 skipped**. So this card's evidence is real, and **any skip in
those files during this card is a signal, not normal**.

**2. The inner loop does not need the full suite.** `scripts/impact_set.py` over this card's six
`Touches` returns a real **26-file selection**, not `FULL` — unlike CARD-264, whose `CLAUDE.md` tripped
the fail-closed branch and forced six full gates in one day. The selection is pinned in the brief, so the
per-round cost is ~2 minutes of tests instead of ~24, and the full suite runs **once**, at the merge gate.

**Conflict note for the dispatcher, not an action for this card.** `src/nonogram/admin/static/solver.js`
and `admin.css` are the board's busiest hotspot: CARD-280 (solved reveal), CARD-267 and CARD-277 all land
there. This card holds them for its duration; the other three must not run concurrently with it.

  merges first, AC-6's "renders cleanly" check includes the crosshair tint on
  a sticky gutter.

## Worktree notes -- implementation (2026-10-23)

### What the three causes look like at this tip, re-verified before implementing

All three hold, at the line numbers below (they had moved by 50-odd lines):

| cause | where, now | measured here |
|-------|------------|---------------|
| 1. plain-first bar | `drawSettledLayout`, `solver.js:784`; `DOUBLE_MIN_CELL`, `solver.js:395` (pre-card) | a 30 x 30 at 1280 x 720 draws plain, cell 14.39 px |
| 2. ladder prefers rows | `layoutLadder`, `solver.js:660` (pre-card) | unchanged, untouched |
| 3. mirror on phones | `isMirrored`, `solver.js:646` (pre-card) | 390 x 844: `is-mirrored`, one gutter, on the right |

### The scroll container, measured (card item 3)

**`.player-stage` IS the scroll container, and nothing had to move.** Walked
the table's ancestor chain on the live page: of `TABLE.player-board`,
`DIV.player-stage`, `MAIN.main`, `DIV.shell`, `BODY`, `HTML`, exactly one has
a scrolling `overflow` -- the stage (`overflow: auto` on both axes) -- and it
is the one with content past its visible box (211 px at 1280 x 600). Pinned
by `TestSolverClues_TheStageIsTheScrollContainer`.

Two side findings from that walk, both recorded rather than worked around:

* `.player-stage` carries `container-type: inline-size`, which applies layout
  containment and so makes the stage a stacking context. The gutters'
  z-indexes are therefore scoped inside it and cannot reach over the toolbar
  menus (`z-index: 10`) or the flash stack (`1040`).
* **In this headless Chromium the DOCUMENT does not scroll from script.** At
  390 x 844 the solve page is 1256 px tall and `scrollingElement.scrollTop =
  300`, `window.scrollBy`, `scrollIntoView` and a synthesized wheel all leave
  `scrollY` at 0, while Playwright's CDP-driven `scroll_into_view_if_needed`
  moves it to 400. `document.elementFromPoint` takes WINDOW coordinates, so
  without that every hit-test below the fold answers null -- which is why
  `_to_corner` brings the stage into the window through Playwright and not
  through the page's own JS. Recorded because the next card that hit-tests a
  phone viewport will meet it.

### What shipped, and the one place it differs from the card

Sticky gutters, as the card asks -- **with a measured room condition the card
did not anticipate, because without it the fix takes the board away from the
player.**

A stuck band floats OVER the cells it used to scroll away from, so keeping the
clues in view and keeping the board in view are the same space spent twice.
Unconditional sticking (the first implementation, run against the suite)
reddened five tests that pass on `main`, each a real player action lost:

* `TestSolverPhone_TouchDragMarksOnAFittedBoard` (tap and drag) -- at 390 px
  the mirrored row band is 272.2 px of a 358 px stage, so the cells it hangs
  over cannot be tapped at all; the recorded tap landed on the band.
* `TestSolverZoom_OneFingerDragIsUnchangedByZoom` (x2) and
  `TestSolverZoom_ZoomKeepsTheViewCentre` -- the same thing at zoom.

Control-run before attributing: all five pass on unmodified `main` and fail
here, run alone. **Not CARD-277.** Mine.

So `keepCluesInView` (solver.js) measures, per axis, what the band could
actually cover -- `min(that axis's overflow, the band's own size)` -- against
`STICK_MAX_SHARE` of the stage, and marks the table `.is-keeping-rows` /
`.is-keeping-cols`. It runs after every draw and after every zoom (the band is
magnified with the cell, so a zoom changes the answer). The per-box markers
`.is-stuck-row` / `.is-stuck-col` say WHICH box is the one that would stick;
admin.css's four rules do the sticking.

**`STICK_MAX_SHARE = 0.4` is a bar between two measured sets, and the gap is
narrow enough that the number is an owner decision:**

* the cases this card must fix top out at **0.364** (30 x 30 at 1280 x 600:
  the whole 135.4 px column band off a 372 px stage);
* the cases where a stuck band demonstrably took the board away start at
  **0.496** (the 1024 x 768 / 200 % drag above) and run to **0.76** (the
  390 px phone).

Nothing was measured between 0.364 and 0.496. Both edges are mutants that red
(0.5 reds the drag test; 0.36 reds the 1280 x 600 column axis).

### What that costs against the ACs, stated rather than smoothed over

| AC | verdict |
|----|---------|
| AC-1 desktop plain board | **met**, at all three measured viewports |
| AC-2 phone + mirror | **met at 600 x 844** (mirror still holds, band can hide 136 px of a 568 px stage). **NOT met at 390 x 844** -- the row axis keeps its cells instead of its clues. The column axis still sticks there. |
| AC-3 zoom | **met while zoomed, not at 300 %.** Plain 30 x 30 at 1280 x 720: rows keep to 200 %, columns to 125 %. Doubled 30 x 25 at 1920 x 1500: rows to 150 %, columns to 200 %. At 300 % neither axis keeps on either board. |
| AC-4 CARD-212 untouched | met; a duplicate, the tfoot band and the duplicate's corner are `static` at every zoom |
| AC-5 small board | met |
| AC-6 visual integrity | met (opacity sampled in pixels, heavy edge, CARD-188 rings) |

### Two owner decisions, with the measurement each needs

1. **The 390 px phone.** A 272.2 px row band on a 358 px stage cannot be held
   in view without hiding the board. The options are all about the BAND, not
   about stickiness: drop CARD-193's mirror on the widest boards, cap how deep
   a row band may be (wrap it, shrink the 1.45 ch gap), or accept that a phone
   player scrolls to read the clues. Render 02 shows what ships; render 04
   shows the same board at 600 px where the mechanism works.
2. **Zoom magnifies the clue band as much as the cells.** `--player-zoom`
   multiplies the cell and the numerals are 0.6 x the cell, so the band's
   share of the stage barely falls: at 300 % the plain board's column band is
   400.3 px of a 492 px stage -- nine cells of an eleven-cell view. **If the
   clue band did not zoom with the cells, every axis of both zoom tables above
   would keep its clues at every zoom level.** That is a CARD-195 decision
   about what zoom means. Render 03 shows 300 % today; render 05 shows 125 %.

G-1 held throughout: `DOUBLE_MIN_CELL`, `BIG_SIDE`, `layoutLadder`'s rung
order and `isMirrored` are byte-identical.

### Two files outside `Touches` had to be touched, both setup and not assertions

Neither is in the brief's pre-computed 26-file selection, and both red on this
change -- worth the dispatcher knowing, because the selection was derived from
`Touches` and `Touches` was derived from the mechanism, not from who reads
`admin.css`.

* `tests/test_admin_design_tokens.py` --
  `test_the_boards_second_clue_gutters_come_from_tokens` is an EQUALITY over
  every rule whose selector mentions `is-right` or `tfoot`. The new mirrored
  side-swap rule is such a rule, so it joins that list and `auto` joins the
  allowed keywords beside `none`/`left`/`top`. The guard's point -- a colour
  or a rule width written as a literal -- is untouched.
* `tests/test_puzzle_solver_fifth_rule.py` -- `_board` takes an ELEMENT
  screenshot of the table, and an element screenshot ignores the stage's
  overflow clip, so a stuck band landed in the capture over 113 px of cells
  (columns 12-19 at 390 px) that the player cannot see at that scroll anyway.
  `_board` now takes the `.is-keeping-*` classes off for the duration of the
  capture and puts them back; sticking is layout-neutral, so the geometry it
  reads is unchanged. Control: with CARD-270's hairline deleted, 12 of that
  file's 17 tests still red, so the helper did not neuter it.

### Runs

* three card files, before: **105 collected, 105 passed, 0 skipped**
* three card files, after: **130 collected, 130 passed, 0 skipped** (+25)
* derived impact selection against the fork point, 28 files: **3000
  collected, 2989 passed, 11 skipped, exit 0**. The 11 skips are all
  `tests/conftest.py:207 Database not reachable: DATABASE_URL is not set` --
  the board's known silent-DB-skip, none of them in a browser file.
* every test file that names `player-board` / `player-clue` / `player-stage` /
  `admin.css` (17 files): **687 passed, 4 skipped**.

**`scripts/impact_set.py --base main` now returns `FULL`, and not because of
this card.** `main` has moved to `8b0ca0e2`, which adds
`ONLINE_GAME_SPECIFICATION.md` at the repo root -- outside the script's
`KNOWN_ROOTS`, so it fails closed. Against the fork point
(`git merge-base main HEAD`) it returns the real 28-file selection above. The
merge gate will want the same base, or it will be told to run everything for a
spec document.

### Mutants: every mechanism DELETED, and what red

| # | mechanism deleted | assertion that reds |
|---|-------------------|---------------------|
| M1 | the column band's sticky rule (admin.css) | AC-1 `col.inside` -- `dTop -91` at 1280 x 720 |
| M2 | the row band's sticky rule | AC-1 `row.inside` -- `dLeft -104` at 900 x 700 |
| M3 | the mirrored side-swap rule | AC-2 `row.inside` at the opened corner (`dLeft 431.7`) |
| M4 | the corner's z-index over both bands | AC-1 corner `hit` reads `another gutter box` |
| M5 | the corner's opaque background | AC-6 pixel reads `(28, 35, 51)` = `--grid-ink` |
| M6 | `clueBox`'s duplicate test (every box marked) | AC-4 `duplicateRows == ['sticky']` |
| M7 | `cornerBox`'s per-axis row test | AC-4 corner table |
| M8 | the `keepCluesInView()` call in `redraw()` | room test `keeping == [False, False]` |
| M9 | the `player.zoomed()` re-measurement | zoom ladder: columns still keep at 150 % |
| M10 | the `min()` with the overflow | room test: 900 x 700 rows stop keeping |
| E1 | **edge** `STICK_MAX_SHARE` 0.4 -> 0.5 | the 200 % touch drag marks nothing |
| E2 | **edge** `STICK_MAX_SHARE` 0.4 -> 0.36 | room test: 1280 x 600 columns stop keeping |
| E3 | **edge** `position: sticky` -> `relative` | AC-1 `col.inside`, `dTop -91` |

13 applied, 13 killed, tree restored byte-identical after each.

### Renders (G-6, as amended)

`~/Documents/nonogram-reviews/CARD-271/`, 30 x 30, half-marked so filled cells
scroll under the gutters:

* `01-desktop-1280x720-both-gutters-kept.png` -- the reported case, fixed
* `02-phone-390-row-clues-NOT-kept.png` -- owner decision 1, what ships
* `03-zoom-300-neither-axis-kept.png` -- owner decision 2, what ships
* `04-phone-600-mirrored-gutter-kept.png` -- the mirrored gutter held in view
* `05-zoom-125-both-axes-kept.png` -- both bands held while zoomed

### Checks held

* ADR-0036/R4: no added line under `src/nonogram/**` carries U+25A0..U+25FF,
  U+2022 or U+2219. (The three pre-existing U+2022 in
  `admin/pdf_generator.py` are that rule's one named, asserted exemption,
  `DINGBAT_EXEMPT_MODULES`, and are untouched.)
* G-2: no hex added; `test_the_stylesheet_uses_tokens_not_literals` green; the
  one coloured value (`.player-corner { background: var(--color-bg) }`) has
  its own per-rule check with four literal controls.
* G-3: `solver_state.js` byte-identical; no request per mark or per scroll.
* G-4/CON-021: `TestSolverZoom_CluesStayInViewWhileZoomed`'s own
  `test_zooming_and_panning_record_and_save_nothing` compares the whole
  solve-state snapshot across zoom + five pans.
* G-5: the three card test files have **0 deleted lines** (`git diff
  --numstat`: 743/0, 155/0, 182/0). The ladder test runs unedited.

## [FIX PRE-GATE 2026-10-23, orchestrator] PASSED — re-derived, not read off the round's report

The round's own table has 13 rows. None of them is evidence here: a pre-gate
exists to check the instrument's claim. Everything below was measured at the
gate, in this worktree, by the dispatcher.

### Reconciled against the round's claims — all of them hold

| claim | re-derivation | verdict |
| --- | --- | --- |
| 7 files, the three card test files with 0 deleted lines (G-5) | `git diff --numstat` fork-point→HEAD: 58/0, 126/6, 11/1, 743/0, 33/1, 155/0, 182/0 | holds |
| three card files 130 passed, 0 skipped (from a 105/0 baseline) | 130 passed, 0 skipped, 77.5 s | holds |
| G-1: `DOUBLE_MIN_CELL`, `BIG_SIDE`, the ladder's rung order, `isMirrored` untouched | the ONLY changed line naming any of the four is an added comment saying so; `layoutLadder`'s body (:736-745) carries no `+`/`-`; the ladder test's class body extracted by `ast` from **both** revisions is byte-identical, 43 lines | holds |
| G-3 `solver_state.js` byte-identical | `git diff --stat` empty | holds |
| ADR-0036/R4 | no added line under `src/nonogram/**` carries U+25A0..U+25FF, U+2022 or U+2219 | holds |
| G-6 renders handed over | five PNGs in `~/Documents/nonogram-reviews/CARD-271/` (three required) | holds |
| `impact_set.py --base main` returns `FULL` | reproduced. `KNOWN_ROOTS` has no repo root, so `ONLINE_GAME_SPECIFICATION.md` fails closed. `--base ec42e6ea` → the real 28 files | confirmed |

**AC/EC/G gate, nine classes by explicit node id: 31 collected, 31 passed, 0
skipped, EXIT=0.** (`-rs`, never `-q` — `pyproject.toml:89` already sets it and
a second one suppresses the count line entirely.)

### The merged tree WILL BE the gated tree — measured, not hoped

`git diff ec42e6ea..main -- src/ tests/ CLAUDE.md docs/ pyproject.toml` is
**empty**. main moved three commits since the fork point and every one is spec
or board bookkeeping (`ONLINE_GAME_SPECIFICATION.md`, `handoff.md`,
`meta/kanban/**`). CARD-264 had to re-run an interaction surface to cover a
moved main; this card does not, and the reason is on the record rather than
assumed.

### Mutants: nine directions, re-derived independently, nine honest kills

Not the round's table — the dispatcher's own points, chosen to bracket the
room condition in **BOTH** directions, because a mechanism controlled in one
direction is the exact shape that survived CARD-264's fix round 4.

| # | mechanism DELETED | outcome |
| --- | --- | --- |
| P1 | the `keepCluesInView()` call in `redraw()` | KILLED, 15 red |
| P2 | the `min()` with the overflow (band size alone) | KILLED, 8 red |
| P3 | the re-measurement after a zoom (`zoomed:`) | KILLED, 20 red |
| P4 | edge: `STICK_MAX_SHARE` 0.4 → 0.36, just under the must-fix cases | KILLED, 5 red |
| P5 | edge: 0.4 → 0.5, just over the board-eating cases | KILLED, 2 red |
| P6′ | the room condition made vacuous — **every** axis keeps (0.99) | KILLED, 8 red |
| P7′ | the room condition made total — **no** axis keeps (0.01) | KILLED, 18 red |
| P8 | the mirrored side-swap rule | KILLED, 4 red |
| P9 | the column band's sticky rule | KILLED, 10 red |

The two bracketing rows are the ones worth reading. P6′ reds on
`test_a_390px_phone_keeps_its_cells_rather_than_its_row_clues`, both 200 %
drags, `test_a_tap_fills_exactly_that_cell` and the zoom-out centre — i.e. the
five player actions the round says it lost when it implemented the card
literally are **held by controls**, not just reported. P7′ reds on every
in-view assertion of AC-1/AC-2/AC-3. So the bar is controlled from above and
from below.

**Two of those nine were NOT honest kills on the first pass, and the pre-gate
is where that was caught.** Spelled as `Infinity` and `-1`, P6/P7 exited
non-zero with **three collection errors and zero failure cells**: `:2798`
reads the constant out of the source with `([0-9.]+)`, so an unparseable value
makes `re.search` return `None` at import time and the three importing files
never collect. The mechanism never ran. Respelled inside the regex's domain
(0.99 / 0.01) they are honest kills with `collection_errors == 0` asserted.
This is CARD-264's trap (b) in its mirror image — there a clean-looking exit 1
with no cells, here a non-zero exit that was the harness dying — and the rule
it confirms is the same one: **an exit code is not a verdict; the cells are.**

Trap (a) honoured: all six anchors pre-counted to exactly one occurrence.
SHIPPED read first and clean (158 passed, exit 0, five files). `solver.js` and
`admin.css` restored and sha256-verified after every mutant.

### PG-1 — two comments quantify a two-fifths bar as "half"

`STICK_MAX_SHARE = 0.4`, and `solver.js`'s authority block states it correctly
("Two fifths is a MEASURED bar"), names both edges (0.364 / 0.496) and names
the two tests that red on a moved bar. Two test-file comments say *half*:

- `tests/test_puzzle_solver_clues.py:2887` — "could hide is at most half the stage"
- `tests/test_puzzle_solver_zoom.py:1036` — "until its band would hide more than half the stage"

Not load-bearing — both sit above an assertion that re-derives the decision
from the constant itself, so the control is right and the figure is a copy.
Filed at the pre-gate precisely because this class took four of CARD-264's
five gating findings, and CARD-281 exists to mechanise it.

### PG-2 — the impact derivation is blind to static assets, and fails OPEN

Measured, not inferred:

```
scripts/impact_set.py src/nonogram/admin/static/admin.css \
                      src/nonogram/admin/static/solver.js
  -> 23 files
intersection with the 16 test files naming player-board / player-clue /
player-stage / admin.css
  -> EMPTY
```

Cause, in `select()`: a changed path with no Python module name resolves
`module` to `None` and hits `continue`, on the stated grounds that "the
always-on scanners already cover the tracked-tree guards that DO read it".
That holds for a guard reading the asset as **text** and fails for a browser
test loading it at **runtime**. So this card's derived 28-file selection comes
entirely from its four changed *test* files plus the always-on scanners, and
**not one file in it renders a player board.**

`changed_from_git`'s docstring states the property the script must keep:
failing open is "the one direction this script must never fail". On a pure
CSS/JS card it fails open. The eleven files outside the selection that read
the changed assets by selector:

```
test_book_finalise_guide_preview_layout.py  test_puzzle_solver_maybe.py
test_puzzle_edit_routes.py                  test_puzzle_solver_mirror.py
test_puzzle_editor_ui.py                    test_puzzle_solver_page.py
test_puzzle_solver_brush_menu.py            test_puzzle_solver_percent.py
test_puzzle_solver_hint.py                  test_puzzle_solver_progress.py
                                            test_puzzle_solver_resume.py
```

**This card is not exposed.** The round ran all 17 selector-naming files by
hand (687 passed, 4 skipped) instead of trusting the selection — which is how
it found five regressions that are green on `main`. Had it trusted the derived
set, the inner loop would have run **zero** tests that exercise the change.
Routed to the backlog, and it bears directly on the owner's open question
about impact-scoped gates: the answer for Python cards and the answer for
asset cards are not the same answer.

### Handed to review cycle 1 to MEASURE, not to accept

1. `_board()` in `test_puzzle_solver_fifth_rule.py` screenshots with the
   `is-keeping-*` classes **off** and evaluates `_GEOMETRY` after the `finally`
   has put them **back** — capture and geometry are read in two different class
   states. Sound only if sticking is layout-neutral, which is separately
   controlled; confirm that control covers `_GEOMETRY`'s own terms.
2. `test_the_boards_second_clue_gutters_come_from_tokens` gained a fifth
   selector (an equality, so the new rule had to join it) and `auto` in the
   allowed keyword set. `auto` is neither a colour nor a length, so the guard's
   subject is untouched — but it is a widening and should be read as one.
3. `test_zooming_and_panning_record_and_save_nothing` (G-4 / CON-021) reds
   under P7′. Check that CON-021's control is not coupled to stickiness in a
   way that makes it a weaker *recording* control than it reads as.
4. The constant's source-read reds as an opaque collection error, not a named
   failure, when the value leaves `([0-9.]+)`. The CARD-281 pattern applied
   with a sharp edge.
