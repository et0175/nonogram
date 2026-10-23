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
**Review score:** 6.0 (cycle 1, NOT CERTIFIED — fix round 1 complete at `c1f11264`, its pre-gate PASSED, review cycle 2 dispatched)
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
| 7 files, the three card test files with 0 deleted lines | `git diff --numstat` fork-point→HEAD: 58/0, 126/6, 11/1, 743/0, 33/1, 155/0, 182/0 | holds |
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

## [REVIEW CYCLE 1 2026-10-23] 6.0, NOT CERTIFIED — one real player-visible bug, found by a reviewer that could not break anything else

Report: `meta/review/20261023T151341Z-CARD-271-cycle1.yml` (synced from the
worktree). Eight findings: 1 critical, 1 important, 2 medium, 3 minor, 1 info.
Score arithmetic: 10 − 2 (F-001) − 1 (F-002) − 0.5 − 0.5 (F-003, F-004) = 6.0.

Cycle 1 is the first scored cycle, so the STALLED CHECK and the FAMILY
REGRESSION CHECK have no prior to compare against and did not fire.

### F-001 is real. I re-derived it myself before spending a fix round on it

A critical finding gets the same treatment as a round's claim. I wrote my own
probe from `solver.js` and the card's helpers rather than reading the
reviewer's, and it reproduces — **larger than reported**.

The defect is structural and it is one missing call site. `keepCluesInView()`
(`:842`) is reached from exactly two places, `redraw()` (`:862`) and
`zoomed()` (`:910`); a viewport change reaches `redraw()` only through `:920`
`if (isBig) redraw()` and `:942` `if (!isBig) return`. So on a **small** board
no viewport change re-measures anything, and the `is-keeping-*` classes set at
load survive a resize that invalidates them. The guard was right before this
card — a 15 × 15 has no mirror and no duplicate, so it had nothing to redraw —
and this card is what makes *every* board's rendering viewport-dependent.

15 × 15, loaded 1920 × 1500, zoomed to 200 %, resized to 1024 × 768, waited
600 ms (4 × `RESIZE_SETTLE`), stage scrolled to bottom-right:

```
stale    keeping=[True, True]   verdict=[False, False]
         cover=[376.3, 270.4]  port=[724, 540]  overflow=[424, 518]
fresh    keeping=[False, False] verdict=[False, False]   <- same board, same viewport,
healed   keeping=[False, False] verdict=[False, False]      same zoom, reached by LOADING
stale_hits  {'visible': 141, 'blocked': 105}
fresh_hits  {'visible': 140, 'blocked': 0}
healed_hits {'visible': 140, 'blocked': 0}
```

Shares **0.520 and 0.501** against a 0.4 bar, and at the corner **105 of 141
visible cells do not take their own tap** — the reviewer measured 35 of 70 at
a different scroll position. `fresh` and `healed` are the controls that make
the stale reading mean something: the mechanism is correct everywhere it is
*reached*, so this is a missing call and not a broken measurement. The reverse
direction is stale too (a board grown wider keeps `[False, False]` where the
fresh decision is `[True, True]`).

It is precisely the configuration this card measured and **refused** —
`solver.js:437-447` names "a 15 × 15 at 1024 × 768 and 200% zoom … 359.4 px
row band over a 724 px stage" at share 0.496. The refusal holds at load and at
zoom; the resize path reinstates it.

**My first probe refuted its own finding, and that is worth recording.** At
scroll (0, 0) a sticky box sits exactly at its flow position and covers
nothing, so a consequence probe that does not scroll the stage measures its
own omission and reports zero blocked cells. The staleness assertions passed
on that first pass and only the consequence assertion failed, which is what
pointed at the probe rather than at the finding. Instrument first, verdict
second — the same lesson the pre-gate's two dishonest kills taught three hours
earlier, in a third shape.

### The rest of the cycle, and why the score understates the card

The reviewer states this plainly and I agree with it: everything about this
card **except** F-001 is unusually strong. Twenty-eight mutants across the
implementation round, my pre-gate and this cycle; every AC with a control;
both owner-decision limitations pinned as **list equalities that red in both
directions**; the one figure derived from source rather than copied. The
reviewer could not break the corner's painting claim (killed in `hit` *and* in
pixels, refuting its own prior), could not break the side-swap behaviourally
and **explained why that is correct** rather than filing it (a band wide
enough to make the left and right constraints conflict is past 40 % of the
port, which the room condition refuses to stick at all), and filed no
boundary-coverage noise after establishing that `affords`' `<=` edge is
unreachable by construction.

One of its nine mutants survived (F-003, the `=== null ? 0` fallback) and it
proved the branch **dead rather than untested** — the distinction that keeps
that from being a coverage finding.

Of my four handed items: item 1 **refuted as sound-by-citation and confirmed
sound-in-fact** (the cited control covers band/overflow/port; `_GEOMETRY`
reads none of the three — F-002); item 2 **confirmed a safe widening and in
fact a strengthening**, since the selector list is an equality so `admin.css`
:624 is now inside the guard; item 3 **confirmed coupled but bounded**, CON-021
holding independently at `zoom.py:481`; item 4 **measured and worth one line**.

### Routed into fix round 1 rather than carried

F-001 (with the AC-5 case it needs, certified against the **base** revision
since an added call site cannot be certified by deleting what the round
added), F-002, F-003, F-004, F-005, F-006, F-007, PG-1's two "half the stage"
comments, and F-008 — the card's own unproduced editor confirmation, which the
round must produce or close with a measured reason.

**The fix brief carries the constraint that makes F-001 non-trivial:** the
`!isBig` guard must not simply be dropped. Its reasoning is written at
`:913-918` and `:933-937` and it is about cost — a `redraw()` is "tens of
milliseconds of layout", which is why the resize path is debounced at all,
while `keepCluesInView()` is a few `getBoundingClientRect()` reads and two
`classList.toggle`s. Reaching the cheap one on every board's viewport change
is the likely fix; reaching the expensive one would contradict a comment the
round would then owe an argument against.

## Worktree notes -- fix round 1 (2026-10-23)

Cycle 1 scored 6.0, NOT CERTIFIED. All eight findings plus the pre-gate's
PG-1 were worked. Two of them were answered with a measurement that disagrees
with the report, and both are stated as disagreements rather than smoothed
over.

### F-001 CRITICAL -- fixed, and certified against the mechanism-free state

**The fix.** `solver.js`: the two viewport listeners now reach a shared
`viewportChanged()` -- `redraw()` when `isBig`, `keepCluesInView()` otherwise
-- and the resize listener no longer returns early on a small board. The
`isBig` gate stays on the REDRAW, exactly where its two comments
(`solver.js:913-918`, `:933-937`) reason it belongs.

**The measurement behind that choice, which the brief asked to be stated.** A
redraw of every board on every resize is a board build for a decision that
needs two class toggles, and the test that says so is a DRAW COUNT, not a
duration (G-7): mutant D3 replaces the split with an unconditional `redraw()`
and
`tests/test_puzzle_solver_zoom.py::TestSolverZoom_SurvivesADoubledRedraw::test_a_board_too_small_to_double_is_not_redrawn_by_a_resize`
reds at `zoom.py:908` with `assert 2 == 1`, while the two new F-001 tests stay
green. So the two designs are distinguished by an existing pin, the comment is
honoured rather than contradicted, and nothing in the card's "burst of resize
events" bound moves.

**The control AC-5 did not have**, added to
`TestSolverClues_SmallBoardsUnaffectedByStickiness`:

| test | what it pins |
|------|--------------|
| `test_a_resize_after_a_zoom_re_measures_the_room` | the stale STICK: 15 x 15, loaded 1920 x 1500, zoomed 200 %, dragged to 1024 x 768 |
| `test_a_grown_window_re_measures_the_room_too` | the reverse: 1024 x 768 -> 1600 x 1200, where the rule says there IS room |

Both compare against the same board, viewport and zoom reached by LOADING
there, re-derive the decision from the page's own `cover`/`port` and
`STICK_MAX_SHARE`, and assert the three inputs (`port`, `band`, `overflow`)
match between the two routes, so the comparison is of one board and not of
two. The first also counts cells whose own centre does not hit-test to
themselves, scrolled to the bottom-right -- the trap the brief names: at
scroll 0 a sticky box sits at its flow position and covers nothing.

**Certification, which cannot be a deletion of something this round added:**
checked `src/nonogram/admin/static/solver.js` out at the base commit
`023157e3` (the mechanism-free state), left the new tests in place:

```
2 failed, 3 passed
clues.py:2656  resized keeping [True, True] != verdict [False, False]
               band [376.3, 270.4]  overflow [424, 518]  port [724, 540]
               resized_hits {'visible': 140, 'blocked': 105}
clues.py:2696  the grown direction: [False, False] != [True, True]
```

With the fix: 5 passed. 105 of 140 visible cells unable to take their own tap
is the consequence, reproduced independently of both the reviewer's probe and
the orchestrator's.

### F-002 IMPORTANT -- fixed, and it found a second defect on the way in

`_board()` now reads `_GEOMETRY` inside the unstuck window and asserts it
equals the reading taken with the classes back, so the claim carries its own
control instead of citing
`test_sticking_changes_neither_the_band_nor_the_overflow` -- which asserts the
band, the overflow and the port, three terms `_GEOMETRY` never reads.
`_UNSTICK` deletes its `keptClasses` stash on the way out, and `_board`
asserts the table carries no `data-kept-classes` afterwards, so the "no later
assertion sees a page this file invented" half of the claim is checked too.

**Demonstrated, not argued** (mutant I2'): a `transform: translateY(2px)` on
the cells of a keeping board moves every cell relative to the table while
leaving the band, the overflow and the port untouched. All SIX tests of
`TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` -- the cited
control -- stay GREEN, and `fifth_rule.py:361` reds with "sticking moved the
table's own geometry". That is F-002's gap, measured from both sides.

**The second defect, which the new control exposed.** Adding a read inside the
capture window made
`test_leaving_a_filled_cell_at_the_boards_edge_the_first_pixel_is_the_hairline[phone]`
fail in 2 runs of 3. Control run first, as the brief requires: the same
five-file selection with THIS file at the base revision and the same fixed
`solver.js` passed 3 of 3, so it was mine to explain, not CARD-277's. It is
not a flake but a soundness hole, and the probe says why:

```
start viewport: [390, 844]  draws: 1
after an element screenshot: [390, 844]  draws: 1  events: [['resize', 390, 844]]
after 600 ms:               [390, 844]  draws: 2
```

**A Playwright element screenshot makes the page fire `resize`** -- the
viewport never changes -- and `RESIZE_SETTLE` later CARD-212's debounced
listener REDRAWS the board, replacing the whole table. So every capture in
this file leaves a redraw landing a moment later, and the shipped `_board`
read its geometry after that boundary: `png` could describe one table
generation and `geometry` its replacement, silently. (The shipped helper met
the same condition as `TypeError: Cannot read properties of undefined (reading
'split')`, with nothing to say which table it had been handed.)

Fixed by making the window provably one generation: `_quiet()` waits out the
pending redraw before anything is read, and the draw count is compared across
the window afterwards. Mutant D10 deletes the wait -- 1 of 2 runs of the
five-file selection reds with `Locator.screenshot: Element is not attached to
the DOM`, i.e. the redraw detaching the table mid-capture. With the wait: 5 of
5 runs green. This is not a CARD-271 defect; it is an interaction between
CARD-212's resize listener and this file's captures, and CARD-271 is simply
where it became visible.

### F-003 -- fixed, and no test can cover it, measured rather than claimed

`solver.js:845` now answers `Infinity`, not `0`. `Infinity` is the largest
value `affords` can be handed, so the only axis that still keeps with its band
unmeasurable is one whose own overflow is already inside the share -- a band
of any size could cover no more than that overflow anyway. A `0` answered the
opposite: `Math.min(overflow, 0) <= port * 0.4` is always true, so an axis
whose labelled gutter could not be found would STICK (ADR-0039/R2).
`clues.py`'s `_ROOM` reimplements the expression and was moved with it.

**No mutant certifies this and that is the finding, not a gap**: the review's
own R2 deleted the guard outright and all 158 tests stayed green, because
every board `drawBoard` produces marks one `is-stuck-row` and one
`is-stuck-col` box. The branch is DEAD, not untested, so its direction is all
there is to get right. Written into the code comment beside it.

### F-004 -- fixed, one step past the suggestion

The review suggested hoisting the stickiness precondition above the pan loop.
That fixes the attribution but still aborts before `_board_snapshot` is
compared, so CON-021-under-panning stays unverified on exactly the cycles when
stickiness is broken -- the finding's own second cost. Instead the keeping is
READ in the loop and JUDGED after the recording assertion. Mutant D9
(`STICK_MAX_SHARE` 0.4 -> 0.01, the room condition made total) reds
`zoom.py:1119` -- the precondition -- with `zoom.py:1116`, the snapshot
comparison, evaluated and passed. Nothing the in-loop assertion covered is
lost: the six readings (at the zoom and after each of the five pans) are all
asserted.

### F-005, F-007, PG-1 -- fixed in the form that cannot drift again

* F-005: the ordinal is gone. The docstring names the rule it adds
  (`.player-board.is-keeping-rows .is-stuck-row.is-right`) and leaves the
  count to the equality one line below, which is mechanically present. Mutant
  D6 (the rule deleted from admin.css) reds that equality at
  `test_admin_design_tokens.py:439`.
* F-007: `STICK_MAX_SHARE`'s derivation is split and named. Mutant D8
  (`const STICK_MAX_SHARE = Infinity;`, outside the regex's domain) now gives
  `AssertionError: solver.js no longer declares STICK_MAX_SHARE as a decimal`
  in all three importing files, where it gave `AttributeError: 'NoneType'
  object has no attribute 'group'`. Still three collection errors -- an
  import-time derivation cannot avoid that -- but attributable.
* PG-1: both "half the stage" comments now NAME `STICK_MAX_SHARE` instead of
  quantifying it (`clues.py`, `zoom.py`), because both sit above an assertion
  that re-derives the decision from the constant, so the figure was a stale
  copy and never a second opinion. The number has one home, `solver.js`.
  `RESIZE_SETTLE` gained the same treatment where this round needed it.

### F-006 -- fixed behaviourally; the pixel half is MEASURED TO BE UNAVAILABLE

The mirrored corner now carries two independent behavioural readings in
`test_both_bands_are_in_view_at_every_corner`: geometry (`inside`,
`dRight == 0`, `dTop == 0`) and the hit-test (`hit in GUTTER_PAINTS`). Both
red on the review's R4 (`cornerBox`'s `row: mirrored` -> `row: false`), which
took the kill count from 1 cell to 2 tests (`phone.py:860`, `phone.py:885`);
and mutant D6b, which removes only the CORNER from the side-swap rule, reds
`phone.py:863` -- the corner's own geometry reading -- proving it bites
independently of the declaration equality.

**Disagreement with the brief, measured.** The brief asks for "the same
two-way control -- in `hit` and in pixels". A pixel control is not available
here, and shipping one would have been the very shape F-002 is about. I wrote
one, and mutant D5b (deleting `.player-corner { background: var(--color-bg) }`)
left it GREEN while reddening the desktop sample. The reason, measured at
600 x 844 with all 900 cells filled:

```
document.elementsFromPoint(corner centre)
  scrollLeft 0   shift [-135.9, 0]  -> [the corner, TABLE, .player-stage, .main]
  scrollLeft 136 shift [0, 0]       -> [the corner, TABLE, .player-stage, .main]
```

Nothing is ever behind this corner. It lives in the `<thead>`, above every
cell, and the mirror puts the row band on the right, so the desktop claim
("the crossing is a hole through which the cells show") has no counterpart on
a mirrored board. The uncontrolled assertion was deleted and the measurement
written beside the readings that do bite.

### F-008 -- produced, and the review's reason for bounding it is wrong

`tests/test_puzzle_editor_ui.py` gains
`TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule`: a 30 x 30 edit page,
asserting the editor's stage is the scroll container (`#puzzle-player`,
`overflow-y: auto`), that solver.js marked the kept gutter of each axis, and
that `keeping` equals the decision re-derived from the editor page's OWN
measurements -- at load and again after a viewport change. Mutant D4 (the
`keepCluesInView()` call deleted from `redraw()`) reds it at
`editor_ui.py:3988`.

**Disagreement, measured.** F-008 bounds its own risk with "the editor ships
no zoom control, so F-001's zoom-then-resize path cannot reach it". It does
ship one: `puzzle_edit.html:146-150` is a `.player-zoom` group with
`[data-player-zoom-action="out"]`, `[data-player-zoom-readout]` and
`[data-player-zoom-action="in"]`, forty-odd lines above the
`.player-stage#puzzle-player` the finding quotes. Pinned by
`test_the_editor_ships_the_zoom_control`. So F-001 reached the editor too, and
the editor is covered by the same fix rather than exempt from the defect.

### Mutants: every mechanism DELETED, with the cells

| # | mechanism DELETED | outcome |
|---|-------------------|---------|
| D1 | **the F-001 fix itself**, by checking `solver.js` out at base `023157e3` -- the mechanism-free state, since an added call site cannot be certified by deleting what was added | KILLED. 2 failed, 3 passed. `clues.py:2656` keeping [True,True] vs verdict [False,False], 105 of 140 cells blocked; `clues.py:2696` the grown direction |
| D2 | the added `else keepCluesInView();` branch | KILLED. 2 failed, 3 passed, same two cells |
| D3 | the branch SPLIT -- `viewportChanged` made an unconditional `redraw()` | KILLED. `zoom.py:908 assert 2 == 1`, the small board's draw-count pin. 1 failed, 11 passed |
| D4 | the `keepCluesInView()` call in `redraw()` | KILLED. 7 failed: `editor_ui.py:3988` (F-008), `clues.py:3103` x5, `clues.py:3126` |
| D5 | `cornerBox`'s `row: mirrored` (the mirrored crossing) | KILLED. 2 failed: `phone.py:860` (behavioural, NEW this round), `phone.py:885` (declaration) -- was 1 cell before |
| D6 | the mirrored side-swap rule, whole | KILLED. 3 failed: `phone.py:817`, `phone.py:885`, `test_admin_design_tokens.py:439` (F-005's mechanical count) |
| D6b | the CORNER's share of that rule only (`.is-stuck-row.is-right` -> `th.is-stuck-row.is-right`) | KILLED. `phone.py:863` -- the corner's own geometry reading, NEW this round |
| D7 | `_UNSTICK`'s `delete table.dataset.keptClasses` | KILLED. 11 failed, `fifth_rule.py:367` "_UNSTICK left data-kept-classes on the table" |
| D8 | `STICK_MAX_SHARE`'s value put outside the regex's domain (`Infinity`) | KILLED, and NAMED: `AssertionError: solver.js no longer declares STICK_MAX_SHARE as a decimal` x3, where it was `AttributeError: 'NoneType'` |
| D9 | the room condition made total (0.4 -> 0.01) | KILLED at `zoom.py:1119`, the precondition, WITH `zoom.py:1116` (the CON-021 snapshot) evaluated and green -- F-004's whole point |
| D10 | `_quiet()`'s settle before a capture | KILLED, 1 of 2 runs of the five-file selection: `Locator.screenshot: Element is not attached to the DOM`. Intermittent by nature and reported as such |
| E1 | **edge**, 0.4 -> 0.5 (just over the board-eating cases) | KILLED. `TestSolverZoom_OneFingerDragIsUnchangedByZoom::test_a_region_touch_drag_at_200_percent_marks_exactly_five_cells`. 1 failed, 13 passed |
| E2 | **edge**, 0.4 -> 0.36 (just under the must-fix cases) | KILLED. `clues.py` room table [1280x600] + `test_sticking_changes_neither_the_band_nor_the_overflow`. 2 failed, 12 passed |
| I2' | **injection**, not a deletion: cells moved relative to the table (`transform: translateY(2px)`) while band/overflow/port stay put. The subject -- layout-neutrality -- is a property of `position: sticky` and cannot be deleted | KILLED at `fifth_rule.py:361`, with all SIX cells of the CITED control green. F-002 demonstrated |
| D5b | `.player-corner`'s background, on the MIRRORED board | **SURVIVED**, and that is the measurement behind F-006's disagreement above, not a gap left open. The desktop sample reds (`clues.py:2771`, reads --grid-ink); nothing is ever behind the mirrored corner |

14 directions applied, 13 killed, 1 survived-and-explained. Both source files
sha256-verified against the shipped tree after every mutant
(`solver.js 77cc6c4c...`, `admin.css 04d40cc5...`); every anchor pre-counted
to exactly one occurrence before any edit, and the one that counted 0 was
REFUSED by the harness rather than silently applied. Every row reports cells,
never an exit code: D8 exits 2 with no tests collected and is still a kill
because the three named errors say what broke.

### Runs -- predicted first, reconciled after

Predicted delta before running: **+2 in `clues.py`** (the two F-001 controls),
**+2 in `editor_ui.py`** (F-008's two), **+0 net in `phone.py`** (one test
added, then deleted when D5b measured it uncontrollable), **+0** in
`zoom.py`, `fifth_rule.py`, `admin_design_tokens.py` -- all three were edits
to existing tests.

| selection | at `023157e3` | now | delta |
|-----------|---------------|-----|-------|
| the three card files | 130 passed, 0 skipped | **132 passed, 0 skipped, EXIT=0** | +2, the two clues tests |
| those three + design_tokens + fifth_rule | 158 passed, 0 skipped, exit 0 | **160 passed, 0 skipped, EXIT=0** | +2, same two |
| the 16 selector-naming files + marking | 687 passed, 4 skipped, exit 0 | **691 passed, 4 skipped, EXIT=0** | +4, those two plus editor_ui's two |

Reconciled exactly. The 4 skips are the same four, all
`tests/conftest.py:207 Database not reachable: DATABASE_URL is not set` from
`tests/test_puzzle_edit_routes.py:375`; **zero skips in a browser file**. The
five-file selection was run 5 times after the `_quiet` fix (3 consecutive plus
2) and is green every time; before it, 2 of 3 red.

`-q` never passed (`pyproject.toml:89` sets it), no `-k` anywhere, every
selection by explicit path or node id.

### Guardrails re-derived at the end of the round

* **G-1**: `git diff 023157e3 -- solver.js` contains no `+`/`-` line naming
  `DOUBLE_MIN_CELL`, `BIG_SIDE`, `layoutLadder` or `isMirrored`. Untouched.
* **G-3**: `git diff ec42e6ea -- solver_state.js` is empty.
* **G-5**: against the fork point the three card test files are **967/0,
  194/0, 214/0 -- still zero deleted lines**. Every line this round replaced
  was a line this card itself added, so the fork-point diff records no
  deletion. Against the base commit the three show 4, 0 and 6 deletions, all
  of them rewrites of this card's own prose or expressions, enumerated:
  `clues.py` the `STICK_MAX_SHARE` derivation (3) and the "half the stage"
  comment (1); `zoom.py` the `test_each_axis...` docstring (4), the
  `..._record_and_save_nothing` docstring tail (1) and the in-loop keeping
  assertion that F-004 moved (1). Outside the three: `fifth_rule.py` 3
  fork-point deletions (`_board`'s one-line docstring, its two body lines) and
  `test_admin_design_tokens.py` 1 (the `allowed` set, from the implementation
  round).
* **G-7**: no duration is measured or asserted anywhere this round. The two
  settle waits (`_settled`, `_quiet`) are derived from `RESIZE_SETTLE` and
  wait OUT a debounce; the performance claim behind the F-001 design is
  carried by a DRAW COUNT (D3), not by a timing.
* **ADR-0036/R4**: no added line under `src/nonogram/**` carries
  U+25A0..U+25FF, U+2022 or U+2219.
* **ADR-0038/R1**: no added line under `src/` matches
  `import |require\(|<script src="http`; `pyproject.toml` untouched.
* **G-2**: no hex added to `admin.css` -- in fact `admin.css` is byte-identical
  to the implementation round's (`04d40cc5...`); this round changed no CSS.
* **ADR-0038/R4**: the room decision stayed a DOM measurement in `solver.js`.

### G-6, as amended

**No re-render is owed.** All five handed renders are load-and-zoom states at
a fixed viewport, and nothing this round changes what a freshly loaded board
decides: `keepCluesInView`'s terms are untouched, the only changed branch is
the dead missing-box fallback, and the room table + the zoom ladder (which
assert exactly those five configurations) are green unchanged.

One render is ADDED, for the configuration the fix does change:
`~/Documents/nonogram-reviews/CARD-271/06-resize-after-zoom-re-measured.png`
-- a 15 x 15 loaded at 1920 x 1500, zoomed to 200 %, dragged to 1024 x 768,
scrolled to the bottom-right. `keeping [False, False]`, which is what that
viewport's own terms give, and `{'visible': 140, 'blocked': 0}`: every visible
cell takes its own tap. Before the fix the same page showed `keeping [True,
True]` and 105 of those 140 cells blocked.

### Two things handed on rather than fixed here

1. **A Playwright element screenshot makes the page fire `resize`**, and
   CARD-212's debounced listener redraws the board a moment later. Every file
   that element-screenshots a player board is exposed to reading two board
   generations as one; `tests/test_puzzle_solver_fifth_rule.py` is fixed here,
   but the interaction belongs to the board, not to this card. Worth a card.
2. **F-008's premise was wrong about the editor's toolbar** and the editor is
   a second surface for every solver.js rendering decision. One test is
   produced here, as the brief asked; a systematic editor pass over the
   gutters is not this card's.

### [PG-3, fix round 1 pre-gate] The editor clause could not fail -- corrected

The pre-gate is right and the finding is the one this round exists to close,
re-created inside the test that closed it. Measured here independently:
`TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule` run in full with
`solver.js` at base `023157e3` -- F-001 present -- was **2 passed, EXIT=0**.
`isBig` is `payload.width > BIG_SIDE || payload.height > BIG_SIDE` with
`BIG_SIDE = 15`, so the clause's `_unique_grid(30, 30)` is big on both sides
and its resize always reached `redraw()`. The one branch F-001 was in is the
one a 30 x 30 cannot take. ADR-0039/R1, in the same shape as F-002.

**Remedy 1 taken, because the configuration DOES exist on the editor page.**
Measured before rewriting anything, and measured from inside `tests/` --
which matters, see the instrument note below. A 15 x 15 on the EDITOR page:

| zoom | 1920 x 1500 | 1024 x 768 | decides differently |
|------|-------------|------------|---------------------|
| 100 % | `[True, True]`, overflow `[0, 0]` | `[True, True]`, overflow `[0, 0]` | no |
| 150 % | `[True, True]`, overflow `[0, 0]` | `[True, False]`, band `[270.4, 231.2]`, port `[724, 540]` | yes |
| **200 %** | `[True, True]`, band `[409.5, 350.2]`, overflow `[0, 0]` | `[False, False]`, band `[359.4, 307.3]`, cover `[359.4, 307.3]`, port `[724, 540]` | **yes, on both axes** |

200 % is taken: the widest contrast, and the same recipe the clues.py cases
use. The clause moved out into
`test_a_resize_after_a_zoom_re_measures_the_editors_room` -- 15 x 15, zoomed
200 %, 1920 x 1500 -> 1024 x 768, with the same-viewport LOADED control and
the three input-identity assertions, exactly as the player's cases.

**Certified the way the brief asks:** `git checkout 023157e3 --
src/nonogram/admin/static/solver.js`, whole class run ->

```
1 failed, 2 passed, EXIT=1
editor_ui.py:4056  resized["keeping"] != verdict(resized)
                   at_load [True, True]  band [409.5, 350.2]  overflow [0, 0]
                   loaded  [False, False] band [359.4, 307.3] overflow [372, 519]
```

restored from a copy taken before the checkout, `sha256
77cc6c4c3bf12d850b709633edf6eb5c92bdd763c54c7b2d44bbfce258b20a90` verified.
With the fix: 3 passed. **The rest of F-008 was not re-opened** -- the marker
census and the load-time room equality are unchanged on the 30 x 30, and the
pre-gate's own mutant kills the latter.

**An instrument note, because it nearly cost this measurement.** My first two
probes of this lived in the scratchpad, outside `tests/`, and reported the
EDITOR's and the PLAYER's 15 x 15 alike as having **no `is-stuck-*` markers at
all** (`band [inf, inf]`, `keeping [False, False]`) -- which would have said
remedy 1 was impossible and sent me to remedy 2, deleting a clause that can in
fact be made to bite. The same board read from a file inside `tests/` has the
markers. The tell was in the run's own output: `PytestUnknownMarkWarning:
Unknown pytest.mark.browser`, i.e. the suite's configuration was not being
applied to that file. **A probe outside `tests/` is not this suite's
instrument.** Every number in this block was taken from a file inside
`tests/`, run once and deleted.

### Records correction -- G-5

The Runs block above reports G-5 as deleted-line counts in the three card test
files. That is the wrong subject. **G-5 is "The redraw path keeps its
draw-count pins: the ladder tests that count draws by draw marks run unedited
(AC-4)."** On its real subject it HOLDS, re-derived: no changed line of
`tests/test_puzzle_solver_zoom.py` lies in the body of a draw-counting test,
and both pins -- `..._a_burst_of_resize_events_redraws_once` and
`..._a_board_too_small_to_double_is_not_redrawn_by_a_resize` -- carry no `+`
or `-` line at all. That the second of them is also what separates this
round's two candidate designs for F-001 (mutant D3) is the guardrail doing
its job, not a conflict with it.

The deleted-line counts are still true and still worth keeping -- they are the
record for the three card files' no-deletion discipline (967/0, 194/0, 214/0
against the fork point) -- but they are not G-5, and a guardrail restated
wrong on the permanent record is how the next card re-learns it.

## [FIX ROUND 1 PRE-GATE 2026-10-23, orchestrator] PASSED — one gating finding of the gate's own, corrected before the cycle

Fix round 1 is `29e019a7` + the correction `c1f11264`, on base `023157e3`.
Nothing below is read off the round's report; every row was measured here.

### Reconciled against the round's claims

| claim | re-derivation | verdict |
| --- | --- | --- |
| 7 files, 569/32 against base (before the correction) | `git diff --numstat 023157e3..29e019a7`: 54/5, 12/7, 92/0, 228/4, 106/10, 39/0, 38/6 = 569/32 | holds |
| `solver.js` sha256 `77cc6c4c…`, `admin.css` untouched this round | `77cc6c4c3bf12d850b709633edf6eb5c92bdd763c54c7b2d44bbfce258b20a90`, verified again after every mutant of mine | holds |
| three card files 132, + design_tokens + fifth_rule 160 | `--collect-only`: **132** and **160** | holds |
| 16 selector-naming + marking | **691 passed, 4 skipped, EXIT=0, 376.7 s** at `29e019a7` (695 collected); **696 collected** after the correction | holds |
| the `+4` | attributable BY NAME: the base→`29e019a7` test diff adds exactly four `def test_` lines (two in `clues.py`, two in `editor_ui.py`), removes none, touches no `@pytest.mark.parametrize`; so `phone.py` and `zoom.py` are +0, including the phone case the round deleted after its own D5b | holds |
| the 4 skips | `tests/conftest.py:207 Database not reachable: DATABASE_URL is not set`, all four in `test_puzzle_edit_routes.py` (`73 passed, 4 skipped` run alone with `-rs`), **zero in a browser file** | holds |
| G-1 | no `+`/`-` line of the `solver.js` diff names `DOUBLE_MIN_CELL`, `BIG_SIDE`, `layoutLadder` or `isMirrored` | holds |
| G-3 | `solver_state.js` byte-identical to the fork point | holds |
| G-5, on its real subject | no changed line of `zoom.py` lies in a draw-counting test body; both pins carry no `+`/`-` at all | holds |
| G-7 | no added line names `perf_counter`/`time`/`timeit`/`elapsed`/`duration` | holds |
| ADR-0036/R4 | 54 added `src/nonogram/**` lines, none carrying U+25A0..U+25FF, U+2022, U+2219 | holds |
| G-6 | six renders in `~/Documents/nonogram-reviews/CARD-271/`; `06-resize-after-zoom-re-measured.png` is the configuration the fix changes | holds |
| F-008's premise | `puzzle_edit.html:146-149` **is** a `.player-zoom` group with both `data-player-zoom-action`s and the readout — the round is right and review cycle 1 was wrong | the round's disagreement (b) stands |
| the cycle-1 YAML's eight findings marked fixed | `diff` of the two copies is exactly 8 × `status: open` → `fixed` and nothing else | holds |
| card notes appended, not edited in place | worktree card `509/0` then `71/11` confined to `editor_ui.py` | append-only |

### F-001 — certified by the instrument written before the fix existed

My cycle-1 probe, unchanged, against the fixed tree — 15 x 15 loaded at
1920 x 1500, zoomed to 200 %, dragged to 1024 x 768, settled, scrolled to the
corner:

```
at_load   keeping=[True,True]   verdict=[True,True]   cover=[0,0]         port=[1620,1150]
stale     keeping=[False,False] verdict=[False,False] cover=[376.3,270.4] port=[724,540]
fresh     keeping=[False,False] verdict=[False,False] cover=[376.3,270.4] port=[724,540]
healed    keeping=[False,False] verdict=[False,False] cover=[376.3,270.4] port=[724,540]
stale_hits {'visible': 140, 'blocked': 0}        (was 141 visible / 105 blocked)
```

It fails now, at exactly the assertion that STATES the defect, with its
comparability and mechanism-where-reached assertions still passing; against
base `solver.js` the same probe passes. A control that fails in both
directions (ADR-0039/R1).

Three mutants of the gate's own, line-count preserving, sha256 restored after
each: **M1** base `solver.js` → the two new AC-5 cases red (2 failed, 4
passed, my probe among the greens), so the added call site is certified
against the mechanism-free state and not by deleting what the round added;
**M2** `keepCluesInView();` deleted from `redraw()` (1620 → 1620 lines) → the
new editor control reds at its first assertion; **M4** below.

### PG-3 (the gate's own, GATING) — and its correction

**M3**: the whole new editor class run against `solver.js` at base
`023157e3`, i.e. with F-001 present → **2 passed, EXIT=0**. The round wrote
that F-001 reached the editor too and added a clause for it ("after a viewport
change too, F-001's path"), but its board was `_unique_grid(30, 30)` and
`isBig` is `width > BIG_SIDE || height > BIG_SIDE` with `BIG_SIDE = 15`, so a
30 x 30 is big on both sides and its resize always reached `redraw()` — the
one branch the defect never entered. F-002's own family, a claim whose control
cannot fail, re-created inside the test added to close a finding about a claim
whose control could not fail. Handed back rather than carried into the cycle:
a review cycle is for what the gate cannot measure, and this one was measured.

The round took remedy 1 after measuring that the configuration exists — a
15 x 15 on the editor page decides `[True,True]` at 1920 x 1500 and
`[False,False]` at 1024 x 768 **at 200 % zoom**, alike at 100 %, so the zoom
is load-bearing and an unzoomed clause would have been vacuous for a second
reason. **M4**, mine, closes it: the corrected class against base `solver.js`
is **1 failed, 2 passed, EXIT=1**, red at `editor_ui.py:4056`
(`resized["keeping"] == _verdict(resized)` → `[True,True] == [False,False]`)
with the two pre-existing readings green, so the kill is attributable to the
clause and not to the file. With the fix, 3 passed. Counts reconciled: one
`def test_` added, `editor_ui.py` **117 collected**, the 17-file selection
**696 collected** = my 695 + 1.

### Two instrument defects, both the gate's to record

**Mine.** The first run of the 17-file selection reported `EXIT=4`, "no tests
ran in 0.00s" and `ERROR: file or directory not found:` followed by all
seventeen paths as ONE argument. Cause: zsh does not word-split an unquoted
parameter expansion, so `FILES=$(… | tr '\n' ' ')` then `pytest $FILES` hands
pytest a single path. Re-run with an array and a printed `count=17`. The
fourth shape of today's lesson and the cheapest: a run that measures nothing
announces itself only in its exit code.

**`git checkout <rev> -- <path>` STAGES the path.** Both the round and this
gate hit it while certifying against base: the working tree reads right and
the index holds the base file (`MM`), so a later commit without explicit
pathspecs would have shipped the reverted `solver.js`. Caught both times by
reading `git status`. The gate's remaining certifications used
`git show <rev>:<path> > <path>`, which touches no index at all — that is the
form to use, and it is now on the record beside the board's standing
explicit-pathspec rule.

**One of the round's own, and it is the day's lesson again.** Its first two
PG-3 probes lived in the scratchpad, outside `tests/`, and reported the
editor's and the player's 15 x 15 alike as carrying no `is-stuck-*` markers at
all — which would have said remedy 1 was impossible and sent it to delete a
clause that can in fact be made to bite. The tell was in the run's own output:
`PytestUnknownMarkWarning: Unknown pytest.mark.browser`, i.e. the suite's
configuration was not reaching the file. Every figure it then used was taken
in-tree. Instrument first, verdict second — the fifth shape today, and the
first one where the instrument's own warning line was the thing that caught
it.

### Housekeeping

`tests/test_card271_orch_f001.py`, my cycle-1 probe, was untracked in the
worktree and would have been collected by a bare full-suite run at the merge
gate. Removed from the worktree; it lives in the session scratchpad.
