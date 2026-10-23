# CARD-271: Big boards lose their bottom and left clues — keep clues in view whatever the fit ladder decides

**Status:** done
**Priority:** P2
**Category:** ops
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/271-clues-stay-in-view
**Worktree:** — (removed at merge)
**Source:** quick — owner bug report 2026-10-22: "clues sometimes are missed at the bottom and at the left for big puzzles"; no handoff increment
**Idea:** —
**Wave:** 55
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_clues.py, tests/test_puzzle_solver_phone.py, tests/test_puzzle_solver_zoom.py <!-- AS MERGED, which is wider than drafted: tokens.css was NOT touched (no token added), and four files outside this list were -- tests/test_admin_design_tokens.py (the selector-list equality had to gain the new rule), tests/test_puzzle_solver_fifth_rule.py (F-002's helper plus the screenshot/resize interaction), tests/test_puzzle_editor_ui.py (F-008's editor control) and tests/test_browser_fixture_scope.py (the 27 node ids the family's registry owed). None of the four is a production file; the production pair is exactly as drafted. -->
**Review score:** 9.5 (cycle 2, CERTIFIED; cycle 1 was 6.0)
**Started:** 2026-10-23T15:05Z
**Closed:** 2026-10-23
**Actual:** 1d (dispatched 15:05Z, merged 22:14Z — one implementation round, a pre-gate, two review cycles, one fix round with three corrections, two full suites)
**Merge commit:** 476abf18
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

### [F-101, review cycle 2] The cross-check compared a ROUNDED cover against the bar

**Fixed.** `_ROOM` returned the cover only as `+Math.min(…).toFixed(1)`, and
four sites compared THAT against `port * STICK_MAX_SHARE`, where
`solver.js:863`'s `affords` compares the raw `Math.min(overflow, bandSize)`.
`overflow` and `port` are integers on both sides, so the band's fractional
part was the only divergence -- a +/-0.05 px window, one-sided toward agreeing
with a page that sticks where the rule refuses: at port 980 the bar is 392.0,
a true cover of 392.04 rounds to 392.0, and the rounded form answers KEEP
where solver.js answers NOT-KEEP.

It is my own F-003 edit's miss: that change touched this very expression under
"it moves with it or it stops being a cross-check", tracked the VALUE and left
the PRECISION. ADR-0039/R2 is about derivation rather than resemblance, and a
figure that tracks one and not the other is resemblance.

`_ROOM` now returns `coverRaw` beside `cover`. **All four** comparison sites
read the raw value; the rounded one stays in the payload, which is what every
failure message on this card prints:

| site | what it holds |
|------|---------------|
| `tests/test_puzzle_solver_clues.py` `_verdict` | nine assertions, incl. both F-001 controls and both editor controls |
| `tests/test_puzzle_solver_clues.py` the room table's own re-derivation | the five measured viewports |
| `tests/test_puzzle_solver_zoom.py` the give-up ladder | **owner decision 2** (both axes give up at 300 %) |
| `tests/test_puzzle_solver_phone.py` the 390 px refusal | **owner decision 1**, and it compares with `>`, so rounding errs the OTHER way -- a true cover of 392.04 reads as 392.0 and the assertion fails where the rule says it holds |

Both directions of one root. Fixing `_verdict` alone would have left the two
owner-decision controls re-deriving the rule from a rounded number.

**No verdict moves on any measured board** -- the point of the fix is that
raw and rounded agree everywhere this suite looks, so it is a correctness fix
to the derivation and not a behaviour change. All 22 boards the four sites
use, with both verdicts:

| board | port | cover (rounded) | coverRaw | bar | raw / rounded |
|-------|------|-----------------|----------|-----|---------------|
| room table 30x30 1280x720 | [980, 492] | [0, 91] | [0, 91] | [392.0, 196.8] | [T,T] / [T,T] |
| room table 30x30 1280x600 | [980, 372] | [0, 135.4] | [0, 135.390625] | [392.0, 148.8] | [T,T] / [T,T] |
| room table 30x30 900x700 | [600, 472] | [104, 111] | [104, 111] | [240.0, 188.8] | [T,T] / [T,T] |
| room table 30x30 390x844 | [358, 583] | [272.2, 0] | [272.15625, 0] | [143.2, 233.2] | [F,T] / [F,T] |
| room table 30x30 600x844 | [568, 583] | [136, 0] | [136, 0] | [227.2, 233.2] | [T,T] / [T,T] |
| zoom ladder @100% | [980, 492] | [0, 91] | [0, 91] | [392.0, 196.8] | [T,T] / [T,T] |
| zoom ladder @125% | [980, 492] | [0, 168.6] | [0, 168.59375] | [392.0, 196.8] | [T,T] / [T,T] |
| zoom ladder @150% | [980, 492] | [0, 201.7] | [0, 201.65625] | [392.0, 196.8] | [T,F] / [T,F] |
| zoom ladder @175% | [980, 492] | [118, 234.7] | [118, 234.71875] | [392.0, 196.8] | [T,F] / [T,F] |
| zoom ladder @200% | [980, 492] | [274, 267.9] | [274, 267.921875] | [392.0, 196.8] | [T,F] / [T,F] |
| zoom ladder @225% | [980, 492] | [431, 301] | [431, 300.984375] | [392.0, 196.8] | [F,F] / [F,F] |
| zoom ladder @250% | [980, 492] | [487.4, 334.2] | [487.390625, 334.1875] | [392.0, 196.8] | [F,F] / [F,F] |
| zoom ladder @275% | [980, 492] | [535.8, 367.3] | [535.84375, 367.25] | [392.0, 196.8] | [F,F] / [F,F] |
| zoom ladder @300% | [980, 492] | [584.3, 400.3] | [584.3125, 400.3125] | [392.0, 196.8] | [F,F] / [F,F] |
| F-001 player 15x15 1920x1500 @200% at load | [1620, 1150] | [0, 0] | [0, 0] | [648.0, 460.0] | [T,T] / [T,T] |
| F-001 player 15x15 -> 1024x768 @200% resized | [724, 540] | [376.3, 270.4] | [376.28125, 270.390625] | [289.6, 216.0] | [F,F] / [F,F] |
| F-001 player 15x15 1024x768 @200% loaded | [724, 540] | [376.3, 270.4] | [376.28125, 270.390625] | [289.6, 216.0] | [F,F] / [F,F] |
| F-001 player 15x15 1600x1200 @200% grow control | [1300, 972] | [0, 178] | [0, 178] | [520.0, 388.8] | [T,T] / [T,T] |
| editor 30x30 1280x720 load-time | [980, 492] | [0, 91] | [0, 91] | [392.0, 196.8] | [T,T] / [T,T] |
| editor 15x15 1920x1500 @200% at load | [1620, 1206] | [0, 0] | [0, 0] | [648.0, 482.4] | [T,T] / [T,T] |
| editor 15x15 -> 1024x768 @200% resized | [724, 540] | [359.4, 307.3] | [359.359375, 307.28125] | [289.6, 216.0] | [F,F] / [F,F] |
| editor 15x15 1024x768 @200% loaded | [724, 540] | [359.4, 307.3] | [359.359375, 307.28125] | [289.6, 216.0] | [F,F] / [F,F] |

22 boards, the two verdicts identical on every one, the `>` comparison
identical on every one, and `keeping` equal to the raw verdict on every one
(all three asserted in the demonstration, not eyeballed). **Nearest approach
to a bar anywhere in the suite: 4.86 px** (the 150 % column axis, 201.65625
against 196.8) -- about a hundred times the window the rounding could have
opened, which is why this closes as a correctness fix rather than a
behaviour change.

**Mutant M-101**, line-count preserving (1620 lines before and after),
restored from a file copy and `sha256 77cc6c4c…` verified -- never
`git checkout <rev> -- <path>`, which stages the path:

| mechanism | outcome |
|-----------|---------|
| `affords`'s compared quantity halved (`Math.min(overflow, bandSize) / 2`), so the page keeps where the rule refuses | KILLED. 3 failed, 5 passed, 0 collection errors. `clues.py:2654` and `clues.py:2694` (both F-001 controls) and `editor_ui.py:4054` (the editor's), each `keeping [True, True]` against a verdict of `[False, False]` |

All three cells are `_verdict`-based, so the changed expression bites.
`src/` is unchanged: `solver.js` is `77cc6c4c…`, as it was at the certified
head.

### Records corrections -- two line figures, and what they are each a case of

Both were flagged by review cycle 2 and both are mine. They are NOT the same
mistake, and the difference is the interesting part:

* **`zoom.py:1116` for the CON-021 snapshot assertion was simply wrong when
  written.** Re-derived: at the fix round's own commit `29e019a7` the line
  `assert _board_snapshot(page, puzzle) == before` is at **1115**; `:1114` is
  its comment. A figure copied one line off from pytest's own failure line.
* **`editor_ui.py:3988` for the D4 row was RIGHT when written and went stale.**
  Re-derived: `assert at_load["keeping"] == _verdict(at_load)` is at 3988 in
  `29e019a7` and at **4003** after the PG-3 commit moved it. Not a miscopy --
  a correct figure invalidated by a later commit in the same round.

And a third, created while writing this block: **the F-101 edit above moved
the CON-021 assertion again**, from 1115 to **1119**, because it added four
comment lines upstream of it. So the corrected figure was stale before this
paragraph was finished.

Which is the point, and the reason both are recorded by their ASSERTION TEXT
here and not only by number: `assert _board_snapshot(page, puzzle) == before`
in `test_zooming_and_panning_record_and_save_nothing`, and
`assert at_load["keeping"] == _verdict(at_load)` in
`test_the_editors_gutters_obey_the_room_condition`. A name survives the next
commit; a line number is a copy of a figure the file already states, which is
the PG-1 / F-005 family in its third shape this card. CARD-281 exists to
mechanise the class and nothing here tries to pre-empt it.

### [Merge gate] The browser family's registry — 27 node ids this card owed

`tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`
was red: 27 node ids collected in the browser family and recorded nowhere.
All 27 are this card's — 20 in `_clues.py`, 3 in `_phone.py`, 4 in `_zoom.py`
— and **25 of them pre-date the fix rounds**: they are the implementation
round's AC-1..AC-6 tests, so the guard has been red since `023157e3` and
every gate this card ran was selected too narrowly to notice. The fix rounds
added two (`test_a_resize_after_a_zoom_re_measures_the_room`,
`test_a_grown_window_re_measures_the_room_too`). `_fifth_rule.py` contributes
none — this card only edited tests there — and the editor's three are outside
the family, whose prefix is `tests/test_puzzle_solver`.

All 27 are now in `ADDED_SINCE_BEFORE`, each with `CARD-271` and the reason
that test exists, in the file's own idiom (`f"{FAMILY_PREFIX}_clues.py::"`,
one entry per parametrized node id, as CARD-270's block does). The guard
alone: **29 collected, 29 passed, 0 skipped, EXIT=0** — it was 1 failed, 28
passed.

#### Sibling census guards, one by one — measured, not assumed

A 24-minute suite found one; the point of this table is that it does not have
to find a second. Every guard in `tests/` that holds a count, a node-id set,
a file list or a tree snapshot, with whether this card's eight changed files
enter its subject:

| guard | its subject | this card in it? | evidence |
|-------|-------------|------------------|----------|
| `test_browser_fixture_scope.py` | node ids of `tests/test_puzzle_solver_*.py`, globbed live against CARD-217's artefact + `ADDED_SINCE_BEFORE` | **YES** | the failure above; fixed, 29 passed |
| `test_suite_profile.py` | `regrep_render_set(tests/)` against `RENDER_HEAVY_SNAPSHOT`, plus the silence census over the tree | no | `RENDER_API_PATTERN` is the BOOK render API (`interior(`, `export_book`, `render_pages`…), not a browser screenshot: it matches **none** of this card's six test files, before or after, and none is in the snapshot (re-greped both revisions). The silence census needs an added skip; the diff adds none. **Ran anyway: 399 passed, EXIT=0** |
| `test_guard_integrity.py` | the guards in `test_suite_profile.py`, judged from outside; rglobs `src/nonogram` and `tests` | no | nothing added or silenced at module scope. **Ran: 167 passed, EXIT=0** |
| `test_db_engine_lifecycle.py` | every `*.py` under `tests/` (engine hand-set spellings) and CARD-252's docstring authority roots (`src/nonogram` + `tests`) — this card's docstrings ARE in its subject | in subject, unaffected | **Ran: 18 passed, 2 skipped, EXIT=0**; both skips are `conftest.py:207 DATABASE_URL`, the board's known DB skip, and the file is untouched by this card |
| `test_impact_set.py` | every `*.py` under `tests/` — `.venv` strings reaching a spawner, and the derived always-on scanner set | in subject, unaffected | no changed test file contains `.venv`, and the diff adds no `rglob`/`glob(`/`os.walk`/`iterdir`, so neither derivation moves. **Ran: 34 passed, EXIT=0** |
| `test_cli.py` | the component map in `src/nonogram/__init__.py`'s docstring against the modules on disk, `_ADAPTERS`, and the layering import walk over `src/nonogram/**/*.py` | no | `git diff ec42e6ea -- 'src/**/*.py'` is **empty** — this card's only production changes are `solver.js` and `admin.css`, which that walk cannot see, and no module was added or removed. **Ran: 135 passed, EXIT=0** |
| `test_card_060_grid_renderer_surface.py` | `src/**/*.py` for two deleted symbol names | no | same empty `.py` diff; the card writes neither `grid_to_svg_bytes` nor `get_svg_filename` |
| `test_admin_import_consistency.py` | `src/nonogram/admin/**/*.py` relative imports | no | same empty `.py` diff |
| `test_fixture_integrity.py` | the committed images under `tests/fixtures/` | no | the card adds no fixture; `git diff --name-status` over `tests/` is all `M`, no add and no delete |
| `test_naming.py` | exported puzzle FILENAMES (FR-015); its `iterdir` is over a `tmp_path` | no | no tree census; nothing of this card is in its reach |
| `test_web_server.py` | the web server's own baseline | no | not a tree census over this card's files; also inside `test_guard_integrity`'s `_FILES`, which ran green |

Also checked and unmoved: no new test FILE enters the family, so
`PAGE_ISOLATION` and every file-list in the family guard are unchanged (that
list's own tests are among the 29 that now pass).

#### Runs

| selection | result |
|-----------|--------|
| `tests/test_browser_fixture_scope.py` | **29 collected, 29 passed, 0 skipped, EXIT=0** (was 1 failed, 28 passed) |
| `tests/test_suite_profile.py` | 399 passed, 0 skipped, EXIT=0 |
| `tests/test_guard_integrity.py` | 167 passed, 0 skipped, EXIT=0 |
| `tests/test_db_engine_lifecycle.py` | 18 passed, 2 skipped (`DATABASE_URL`), EXIT=0 |
| `tests/test_impact_set.py` | 34 passed, 0 skipped, EXIT=0 |
| `tests/test_cli.py` | 135 passed, 0 skipped, EXIT=0 |
| the 16 selector-naming files + marking | **696 collected, 692 passed, 4 skipped, EXIT=0** — unmoved |

No test added, removed or renamed by this change: `ADDED_SINCE_BEFORE` is a
data table, and the 17-file selection collects exactly what it collected
before. `src/` untouched: `solver.js 77cc6c4c…`, `admin.css 04d40cc5…`.

### What this cost, and what it will cost the next card

Stated for the backlog, as an observation rather than a change — the guard is
not this card's to edit.

**The registry is discoverable only by a run nobody makes in the inner loop.**
`tests/test_browser_fixture_scope.py` names none of
`player-board`/`player-clue`/`player-stage`/`admin.css`, so it is outside the
17-file selection this card gated on four times; and it reaches the family
through a `--collect-only` SUBPROCESS, so there is no import edge for
`scripts/impact_set.py` to follow either. This card ran four gate selections
and two full-depth review cycles — and a pre-gate and two fix-round
re-derivations on top — and the first thing to see it was a 24-minute full
suite at the merge gate. That is the same family as PG-2: a derivation that
is blind to a real dependency and fails OPEN.

**The cost is paid late and by the wrong round.** The 25 entries owed here
were owed by the implementation round; they were registered in a fix round,
by which point the reasons had to be reconstructed from the tests rather than
written beside them. The entries are better for having the ACs settled, but
nothing about the mechanism ensured that.

**The measured observation.** The guard's expected set is a UNION of a frozen
artefact and a hand-maintained table, and the half that must move is the hand
one. Two cheaper derivations exist and neither needs the guard to weaken:

1. the family's node ids are already derivable from the tree — the guard
   derives the *live* set that way. What a card actually owes is the REASON,
   not the id, and a reason has a natural home beside the test. A registry
   keyed on ids that a `--collect-only` already enumerates is storing the
   half that can be derived and asking a human for the half that cannot;
2. whatever the registry's shape, the guard is reachable by a selector that
   knows a changed `tests/test_puzzle_solver_*.py` implies it. That edge is a
   one-line fact about the glob at `test_browser_fixture_scope.py:378`, and
   it would have moved this from a merge-gate failure to an inner-loop one on
   the first run of the implementation round.

Neither is attempted here. Routed to the backlog beside PG-2, which it
rhymes with: **both are impact-derivation gaps that fail open, and this one
has now cost a card a red merge gate.**

## [REVIEW CYCLE 2 2026-10-23] 9.5, CERTIFIED — and the family that cost cycle 1 does not recur

`10 − 0 critical − 0 important − 0.5 (one medium) = 9.5`, against `min_score: 8`.
Risk LOW. Report: `meta/review/20261023T173228Z-CARD-271-cycle2.yml`.

Cycle 1 was 6.0. All eight of its findings are closed, **seven of them under a
control the reviewer made FAIL**, and the eighth (F-003) on a derivation,
because no control can exist for a dead branch. Ten directions attacked by
deleting the mechanism each claim names; nine killed with cells. The one
survivor is the `_quiet` settle, and the reviewer answered the brief's
condition rather than waving at it: the property that wait guards — one board
generation per reading pair — is held **deterministically** by
`fifth_rule.py:355`, which the reviewer made fire with a named diagnosis
(`draws 1 → 2, stash restored: False`), so the wait is flake-reduction and the
assertion is the soundness guard.

The headline is the system contract: **cycle 1's one `✗` (ADR-0039/R1, F-002)
is now `✓`, and closed with a control that fails rather than a reworded
claim** — an injection that moves a keeping board's cells relative to the
table reds `fifth_rule.py:361` in four cells while all six tests of the
control the shipped helper used to merely *cite* stay green. Two-sided,
exactly as the rule requires. PG-3's instance of the same family is closed the
same way. ADR-0039/R2 now holds better than before the card: the band fallback
defaults to DENY and both derived constants name their own absence. 16 rules
checked, 11 ✓, 5 ⚠ unchecked, 0 ✗, nothing carried forward — the delta touches
`src/` and `tests/`, which every one of these rules' scope globs intersects,
so carry-forward was refused fail-closed.

### F-101 — the one medium, and the review's own premise for it was incomplete

`_ROOM` returned `cover` rounded to a tenth and **every** comparison against
the bar read that rounded figure, while `solver.js:862`'s `affords` compares
the raw `Math.min`. `overflow` and `port` are integers on both sides, so the
band's fraction was the only divergence, and it was one-sided toward agreeing
with a page that sticks: at port 980 the bar is 392.0, and a true cover of
392.04 rounds to 392.0, so the derived check answers KEEP where solver.js
answers NOT-KEEP. A ±0.05 px window under nine assertions.

**The review said nothing else read `cover` except failure messages. Four
sites made the comparison**, and the orchestrator measured that before a round
was spent on the stated fix: `_verdict`, the room table's own re-derivation,
and — the two that matter — `test_puzzle_solver_phone.py:914` and
`test_puzzle_solver_zoom.py:1061`, **the controls holding this card's two
owner decisions**. The phone site compares with `>`, so rounding errs the
other way there: a true cover of 392.04 reads as 392.0 and the assertion fails
where the rule says it holds. Same root, both directions — the shape this
board keeps paying for when only one direction gets a control. Fixed at all
four (`47f7ea9d`); `grep '\["cover"\]' tests/*.py` now returns nothing.

Closed as a correctness fix to the derivation and not a behaviour change, and
that was asserted rather than eyeballed: on **22 boards** — the five-viewport
room table, the nine-step zoom ladder, both F-001 controls in both directions
and all four editor readings — the rounded and raw verdicts are identical, the
`>` comparison is identical, and `keeping` equals the raw verdict. The nearest
approach to a bar anywhere in the suite is **4.86 px** (150 %, column axis:
201.65625 against 196.8), about a hundred times the window the rounding could
have opened. One mutant certifies the changed expression still bites: halving
the quantity `affords` compares reds `clues.py:2654`, `clues.py:2694` and
`editor_ui.py:4054`, all three `_verdict`-based, line count preserved and
`solver.js` sha256 verified after restore.

It was routed as a narrow certification fix rather than a follow-up card
deliberately: two lines in a test helper, against a card in a hotspot shared
with CARD-267, CARD-268, CARD-269 and CARD-280 — a card here would have
serialized behind all of them while the card's central cross-check stayed
non-identical to its source.

### Routed, not fixed here

- **F-102** (low) — the capture settle doubles `fifth_rule.py`'s wall-clock,
  measured 27.35 s against 13.84/13.40/12.96 s, about +4 % on the 17-file
  gate. Not the flake-sleep ADR forbids: deleting it makes the file *flakier*,
  and the obvious cheaper shape was refuted (the first `_board` of a test is
  not exempt, because `set_viewport_size` itself fires `resize`). Backlogged
  with the one deterministic cheaper form — poll the draw count until two
  reads agree.
- **F-104** (info) — the element-screenshot/`resize` interaction, backlogged
  and **bounded by measurement**: four `.screenshot(` sites in `tests/`, and
  exactly one is an element screenshot — the one this card fixes.
- **F-105** (info) — F-001's residual class hunted and **refuted** in-tree:
  the stage's `client` box is unmoved by marks, the brush menu and a hint, and
  only `scrollHeight` moves on the zoom, which `zoomed()` already
  re-measures. Backlogged with the durable shape: a `ResizeObserver` would
  close the class by construction instead of by enumerating the events that
  happen to change the stage — which is how F-001 existed in the first place.

### Three record figures corrected, and they are not the same mistake

`zoom.py:1116` → **`:1115`** was wrong when written (a figure copied one line
off pytest's own output). The D4 row's `editor_ui.py:3988` → **`:4003`** was
*right* when written and went stale when the PG-3 commit moved the assertion.
And the orchestrator's own "105 of 141 blocked": the shipped control's reading
at base is **105 of 140** — the 141 was the cycle-1 probe at a different
scroll position, not this control. The round then moved the corrected 1115 to
1119 while writing the correction, so both sites are now recorded by their
**assertion text** as well as their number.

### Stall judgement — the orchestrator's, not the machinery's

`min_improvement` is `"off"` and `family_regression` is `warn` as of
`ebedc757`, so no escalation check ran and none was owed. The judgement:
6.0 → 9.5 at equal or greater depth — ten mutants against cycle 1's nine, plus
a behaviour probe cycle 1 did not run — with no gating finding left and the
one medium closed before the gate. Not a stall. The `[Family]` note the
reviewer wrote is **record-only**: the PG-1/F-005 family (a figure copied
beside a mechanism that already states it) recurs in a third shape, the
authority this time being pytest's own failure line, with no code or test
implicated. CARD-281 owns mechanising that class. Cycle 1's own family —
a claim whose control cannot fail — does **not** recur anywhere in the delta.

Aggregate round counter: 5 of 6 (implementation, pre-gate, cycle 1, fix round 1
with its two corrections, cycle 2). No fatigue escalation.

## [MERGE GATE 2026-10-23, orchestrator] Two full suites, two reds, both accounted for — merged on a UNION argument, stated rather than buried

### AC/EC/G gate — 18 node ids, 65 collected, 65 passed, 0 skipped, EXIT=0

Selected by explicit node id, never by `-k`: AC-1 `TestSolverClues_StayInViewOnAPlainBigBoard`,
AC-2 `TestSolverPhone_MirroredGutterSticks`, AC-3 `TestSolverZoom_CluesStayInViewWhileZoomed`,
AC-4 `TestSolverClues_TheLadderStopsAtTheFirstRungThatFits`, AC-5
`TestSolverClues_SmallBoardsUnaffectedByStickiness`, AC-6
`TestSolverClues_StickyGutterRendersCleanly`, plus the room table, the
doubled-gutter class, `TestSolverClues_TheStageIsTheScrollContainer`, CON-021's
`TestSolverZoom_IsNotSavedAndSendsNothing`, both draw-count pins
(`TestSolverZoom_SurvivesADoubledRedraw`), ADR-0038/R2's
`TestSolverMarking_NoRequestPerMark`, G-2's
`test_the_stylesheet_uses_tokens_not_literals`, the selector equality
`test_the_boards_second_clue_gutters_come_from_tokens`, and F-008's
`TestPuzzleEditor_TheBoardKeepsItsCluesByTheSameRule`. **Zero skips in this
selection**, which matters because green-with-skips reports the same collected
count and the same exit 0 as fully verified.

### The lock, and a control that CAN fail

Both full suites ran under a lock this gate WROTE — `holder`, `why`,
`worktree`, `commit`, `at` — which is the provenance the board's own backlog
item says a gate owes, and the correction to CARD-264's row in
`suite-timing.log` two lines above these: that gate held no lock and nothing in
the tree could notice, because the guard's subject is a FOREIGN lock and "no
lock" and "my own lock, released" are one observation from inside the run.
The lock was then demonstrated rather than asserted: asked from main's tree,
`full_suite_lock.current_verdict()` **refused**, naming this holder. A lock
that cannot refuse anybody is the board's own version of this card's subject.

### Attempt 1 — `47f7ea9d`, 1452 s: `1 failed, 8953 passed, 27 skipped, EXIT=1`

`tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`
reds at `:1294`: this card added **27** node ids to the browser-fixture family
and registered none in `ADDED_SINCE_BEFORE`. The card's own, and **25 of the
27 pre-date the fix rounds** — the guard had been red since the implementation
commit `023157e3`.

Nothing earlier could have caught it, and that is the finding: the file names
none of `player-board`/`player-clue`/`player-stage`/`admin.css`, so it is
outside the 17-file selection this card gated on FOUR times, and it reaches
the family through a `--collect-only` **subprocess**, so `scripts/impact_set.py`
has no import edge to follow. Four gate selections, two full-depth review
cycles, a pre-gate and two fix-round re-derivations passed over it. PG-2's
family in a second guise — a derivation blind to a real dependency, failing
**open** — and backlogged beside it, with the eleven sibling census guards
enumerated one by one rather than assumed (`git diff ec42e6ea -- 'src/**/*.py'`
is EMPTY, so every guard that walks Python modules is out of scope by
construction; the rest were run).

Fixed in `cb18d45d`, guard re-run: **29 passed, 0 skipped, EXIT=0**.

### Attempt 2 — `cb18d45d`, 1560 s: `1 failed, 8953 passed, 27 skipped, EXIT=1`

A different test, and not this card's:
`test_puzzle_solver_marking.py::TestSolverClickFollowsTheBrush::test_touch_taps_follow_the_brush[chromium]`
— `Page.goto: Timeout 30000ms exceeded`. Diagnosed rather than dismissed: the
page and three of its four assets returned 200 and **`solver_state.js` never
completed**, so `load` never fired. This card does not touch
`solver_state.js` (G-3: byte-identical to the fork point), and the machine was
under load averages **5.12 / 17.00 / 18.48** — attempt 2's own wall clock was
2114 s against pytest's 1560 s, i.e. 555 s of the box being busy elsewhere.
Established as a flake rather than assumed: the class re-run **three times on
the merged tree, 11 passed each time** (9.6 s / 7.1 s / 7.8 s).

Skips, both runs, every one attributed: **26** `tests/conftest.py:207
Database not reachable: DATABASE_URL is not set` and **1**
`tests/test_book_pdf_memory.py:1296 setrlimit(RLIMIT_AS)` refused by this
kernel. **Zero in a browser file.**

### Why this merged, and on what

A **union** argument, and it is not the coverage argument this gate refused
earlier in the same session. That one would have left a delta unmeasured; this
one leaves nothing unmeasured. Every one of the **8981** collected tests
passed green in at least one of two full suites, on trees that differ **only**
by an inert data table (`git diff --numstat 47f7ea9d..cb18d45d` is
`229 0 tests/test_browser_fixture_scope.py`, and `git diff 47f7ea9d..HEAD --
src/` is empty). Each run's single red is accounted for: attempt 1's was the
card's own, is fixed, and its guard passes; attempt 2's is a load-induced
flake in a file this card changes no behaviour in, reproduced green three
times on the tree that merged. The suite grew 8904 → 8953 passed since
CARD-264.

A third suite was deliberately NOT run: at a 15-minute load average of 18 it
would have measured the machine rather than the tree, and the honest
alternative — wait for a quiet box — was offered to the owner, who said merge.

### The merged tree IS the gated tree

`git diff ec42e6ea..main -- . ':(exclude)meta/'` is one file,
`ONLINE_GAME_SPECIFICATION.md` (70/22), and **no test reads it or globs
repo-root markdown** (checked, not assumed). So main's nine commits since the
fork point owe this card no coverage argument, unlike CARD-264's gate which
had to re-run an interaction surface.

The branch carried **no `meta/`** — `git diff --name-only
ec42e6ea..card/271-clues-stay-in-view -- meta/` is empty — so the CARD SYNC
PROTOCOL held end to end across five commits and three agent hand-backs.

## [POST-MERGE 2026-10-23] The union argument is superseded, not merely defended

This card merged on a stated union argument because neither full suite was
green end to end: attempt 1 failed on the card's own browser-family registry
debt, attempt 2 on a load-induced `Page.goto` flake in an untouched file.

A full suite run **after** the merge, on `ae164099` — merged main with this
card in it — for CARD-220's duration profile, came back
**8954 passed, 27 skipped, 0 failed, EXIT=0 in 1433 s**, essentially solo
(1436 s of wall clock against pytest's 1433 s, against attempt 2's 555 s gap).
So the tree this card produced now has one unbroken green full suite behind it,
measured rather than argued, and the union argument stands only as the record
of what was known at the moment of merging.

Two figures worth carrying off this card, both for CARD-220: the suite is
**8981 collected** and costs **160 ms/test** against the 2026-10-15 solo
profile's **131 ms/test** (930.81 s / 7082 tests) — 21 % slower per test while
growing 27 % — and the 18 browser-marked files are **646 tests at 734 ms each**
against that profile's 422 at 868 ms, i.e. the family grew 53 % while per-test
cost fell 15 %, which is CARD-235 showing up in the numbers.
