# CARD-326: Circled clue numbers on the public player — the clue readout that needs no answer

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d) <!-- RESTATED in review cycles 2026-11-05, at QUEUE time rather than at stamp, so the card cannot red tests/test_kanban_review_record.py when it is stamped into a wave (CARD-325 did, because it was stamped with a day estimate). Was 0.5d. 2c is a forecast, not a tuned figure: CARD-325, the closest comparator (a player feature in the same three files), took 1 review cycle, CARD-324 took 3; this card carries a hazard the others did not (AC-4 needs a constructed board where every number is circled and the board is still wrong). -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/326-public-circled-clues
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-326
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`.
**Idea:** —
**Wave:** 79
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_circles.py
**Review score:** 8.4 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-05T21:24Z
**Closed:** 2026-11-06T01:29Z
**Actual:** 2c -- **ratio 0.500** (1 review cycle, derived as 1 distinct ordinal among the `[Review N/M] Score:` lines, against the 2c estimate). Sized by derived datum, **wall-clock excluded** per the owner's standing ruling. Datum: **4 tracked files** (`player/play.js`, `player/player.css`, `tests/test_public_player_agreement.py`, new `tests/test_public_player_circles.py`), **+1976 / -1** lines against the cut `ce22c0e7` at the certified tip `239cc7e9`; `src/` diff 0.
**Merge commit:** `423aef15`
**Blocked by:** —

## Why this card exists

CARD-188 shipped circled clue numbers to the admin player: a clue number is
circled once the player's marks account for it. Measured 2026-10-30:
`solver_state.js` exports `circledNumbers(clue, cells)` and
`circledClues(board, rows, columns)` — **neither takes `solution`** — and the
served copy at `build/site/solver_state.js` is byte-identical to the admin's.
`player/play.js` imports neither; `player/player.css` has **zero** circle rules
against `admin.css`'s 22.

So the whole behaviour is already on the page, reachable, and unused. It belongs
in the same bucket as CARD-324's zoom: wiring, not porting.

### The trap this card must not walk into

`player/play.js`'s header already warns about these two functions, and the
warning is **correct and must be preserved**:

> `isClueSolved` is the solved check ... It is written here, natively, and NOT
> built out of solver_state.js's circledNumbers: that function circles a number
> under three rules, two of which fire on marks that satisfy no clue, so "every
> number circled" is not "every clue satisfied".

**Circling a number and satisfying a clue are different predicates.** This card
adds the circles as a *readout* and must leave `isClueSolved` exactly as it is.
A card that "simplifies" the solved check to "every number circled" would ship a
page that declares victory on a wrong board — and would do it while every test
named below still passed, because none of them is about the solved check.

## What to implement

1. `player/play.js`: import `circledClues` (and `circledNumbers` if the
   rendering needs the per-line form) from `/solver_state.js` and recompute the
   circles on every history change — a repaint already happens per
   stroke/undo/redo, so hook that, do not add a second repaint path.
2. `player/play.html` / `player/player.css`: the circle look on a clue number,
   from tokens, mirroring the admin's appearance. The clue cells already exist;
   this adds a marker attribute and its rule.
3. **Leave `isClueSolved` untouched** (see above), and leave the solved banner's
   behaviour untouched.

## Acceptance criteria

- **AC-1** (a circle appears when the marks account for a number): *Given* a
  board whose marks account for a clue number, *then* that number carries the
  circle marker and numbers not accounted for carry none — the expected set
  taken from **`circledClues`'s own return value**, not from a list spelled into
  the test. (test: `TestPublicCircles_TheMarksCircleTheNumbers`)
- **AC-2** (the circles follow the history): *Given* circled numbers, *when*
  undo and redo move the board, *then* the circle set equals `circledClues` for
  the board at each step — including after a reset, which clears all of them.
  (test: `TestPublicCircles_TheyFollowUndoRedoAndReset`)
- **AC-3** (the predicate is not re-implemented): *Given* the shipped code,
  *then* the circle set the page renders comes from `/solver_state.js` and
  `play.js` contains no second rule for when a number is circled — asserted
  structurally over the source. (test: `TestPublicCircles_ThePredicateIsTheModules`)
- **AC-4** (the solved check is NOT the circle set): *Given* a board where
  **every clue number is circled but the board is not solved**, *then* the
  solved banner stays hidden and `isClueSolved` is false. This is the card's
  guard against the trap above, and it needs a **constructed** board exhibiting
  the divergence — if no such board can be constructed for the fixture puzzles,
  say so and construct one for a fixture of this card's own. (test:
  `TestPublicCircles_CirclesAreNotTheSolvedCheck`)
- **AC-5** (no answer, no request): *Given* every interaction above, *then* the
  page holds no solution field and issues no request beyond the initial GET of
  its own puzzle file. (test: `TestPublicCircles_NoAnswerAndNoRequest`)

## Engineering constraints

- **EC(ADR-0041/R3):** across a seeded corpus of boards spanning extents and
  mark patterns, the circle set the page renders equals `circledClues`'s return
  value for the same board — no case where the page's set and the module's set
  differ. Minimum case count asserted inside the test.

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`** — byte-identical
  build-time copies (ADR-0041/R3).
- **G-2: do not touch `isClueSolved` or the solved banner.** The distinction
  between "circled" and "satisfied" is the whole hazard here; AC-4 is its
  control. Weakening either to reuse the other is the one change this card must
  not make.
- **G-3: do not re-implement the circling rule.** If `circledClues` does not
  give the page what it needs, that is a **finding to raise**, not a licence to
  write a second rule (EC above is exactly that claim).
- **G-4: no solution reaches the page** (ADR-0041/R2, CARD-283 G-4).
- **G-5: marking, Region, undo/redo and reset are untouched** — their tests run
  unedited.
- **G-6: styling from tokens only.**
- **G-7: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).
- **G-8: do not touch `src/nonogram/admin/**`** — CARD-268 is editing the admin
  player's static files in a sibling worktree.

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data (check: CARD-282's and CARD-283's guards)
- ADR-0041/R3 — the board-state module and tokens are byte-identical build-time copies, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: AC-5)
- ADR-0038/R3 — the clues the page renders are the payload's (check: review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: AC-3)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures)
- CON-005 / INV-002 — every published puzzle is uniquely solvable, which is what the public solved check rests on (check: `test_every_fixture_puzzle_is_uniquely_solvable`)

## Architecture context

- **FR:** FR-045 (the public player)
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R4, R8
- **Components:** COMP-011
- **Trace:** not updated by this card (quick-card rule; see CARD-323's note)

## Design context

- **Design system:** `player/player.css`, every value a token (G-6).
- **UI components:** the clue cells gain a circle marker; the admin's look is the reference.
- **Screens:** `/play/<key>`.
- **Standards:** the circle is a readout and never the only carrier of meaning; the owner validates the look on a real puzzle render before merge.

## [Re-verified 2026-10-30 15:15] `main` moved under this card, and every premise was re-measured

**Another session committed to the public player, directly on `main`, outside the
card pipeline**, within half an hour of these five cards being cut:

- `2400501b` *"player: the white mark is a dot and solving is revealed, matching the
  panel"* — `player/play.js` **+3**, `player/player.css` **+57/−12**,
  `tests/test_public_player.py` **+143**, `tests/test_public_player_pages.py` **+9**.
  That is this card's exact footprint.
- `7ec579e4` and `7d34892e` — docs only (`docs/deploy/player.md`,
  `docs/how-it-works/**`), no code.

**Every measured premise in this card was re-derived afterwards and all of them
still hold** (15:15, against `7a2cfdf1`):

| premise | at cutting | now |
|---|---|---|
| `TOOLS = [FILLED, EMPTY, UNKNOWN]` | yes, `play.js` | yes, `play.js:83` |
| `.player-cell[data-state="maybe"]` styled | yes | yes, one rule |
| `player.css` zoom rules | 0 | **0** |
| `player.css` circle rules | 0 | **0** |
| `player.css` crosshair rules | 0 | **0** |
| `play.js`'s false hint comment present | yes | **yes**, verbatim |
| `play.js` length | 576 | **579** |

**What changed that a dispatching agent must know:** that commit brought a sixth
feature over by hand — the white mark as a dot, and a solved sweep whose
per-cell delay `play.js` now sets as `--player-wave`, *"as solver.js sets it for
the admin player"*. So the public player is being closed toward the admin
player's feature set **from two directions at once**: these cards, and
direct-to-`main` commits. **Re-measure this card's figures at dispatch rather
than trusting the table above** — it is a record of one moment, and the moment
had already moved once.

## Worktree notes

- **[Serialization, not dependency]** This card and CARD-323, CARD-324,
  CARD-325, CARD-327 all touch `player/play.js`, `play.html` and `player.css`,
  so their overlap is **1.0** and the conflict graph serializes any two in one
  wave. Deliberately not a `Depends on` edge (the board's rule, stated on
  CARD-220's `Wave:`).
- **[AC-4 may be the hardest assertion on this card]** It needs a board where
  every number is circled and the board is still wrong. `circledNumbers`
  circles under three rules, two of which fire on marks satisfying no clue — so
  such a board exists by construction, but finding one for an existing fixture
  may take a search. A constructed fixture is the acceptable answer; a weakened
  AC is not.

[Author round, commit `5f218331`] Verified by the orchestrator: branch `card/326-public-circled-clues` (the only `card/326` branch; the author's report named a second branch name by slip), tip `5f218331`, one commit over the cut `ce22c0e7`, worktree clean; four files, 1788 insertions and 1 deletion (`player/play.js` 62, `player/player.css` 50, `tests/test_public_player_agreement.py` 292, new `tests/test_public_player_circles.py` 1385); `src/`, `player/play.html`, `player/solver_state.js`, `player/tokens.css`, `tests/test_public_player.py`, `tests/helpers` and `meta/` diffs 0; no deleted test line, no added bare early-`return`, no added skip or xfail; no `addEventListener` added in `play.js`; no `touch-action` line in the CSS diff; the `play.js` change is one import (`circledClues` only), a header comment block, `clueNumbersOf(table)`, `paintCircles(clueNumbers, circled)`, a `const clueNumbers = clueNumbersOf(...)` after `drawBoard`, and ONE line in the existing `refresh()` repaint, `paintCircles(clueNumbers, circledClues(history.board, payload.rows, payload.columns))`, reading the RECORDED board and not the mid-drag `shown`; `isClueSolved` and the solved banner are UNCHANGED (the two diff lines that mention them are the new header comment); my own run of `tests/test_public_player_circles.py`, `tests/test_public_player.py` and `tests/test_public_player_agreement.py` unlifted gave 222 passed. Author-reported, not re-run by me: the 7 public-player modules together 385 passed, 0 failed, 0 skipped, 0 errors (run before the final one-line test edit; the agreement module re-run afterwards, 20 passed, and the plants script re-ran circles, public and agreement on the commit: 222 passed); the 13 census modules 1102 passed, 3 skipped (all "Database not reachable: DATABASE_URL is not set"), 0 failed; G-7 over all tests with `-o addopts= --collect-only -q`: cut 10623 ids, tip 10717, 0 removed, 94 added (74 in the circles module, 20 in the agreement file).

DESIGN: `paintCircles` is a closed-vocabulary painter whose only decision is `span.classList.toggle("is-circled", circled[axis][line][k])`, a bare member of the module's return value with no operator, comparison or condition (an undefined force would FLIP the class, so it reads the module's array by the same axis, line and index the spans were collected under); the hook adds no listener and no second repaint path. The ring is a border on the number's `::before` (`.player-board .player-clue-num.is-circled::before { border-color: var(--grid-ink) }`), tokens only, so the crosshair's background tint on the clue box cannot hide it; it is sized in the numeral's em (`--player-circle: 1.05em`, width the span's own `100%` plus clearance and line) and moves no gutter because `tests/test_public_player_zoom.py` pins them. The author's first cut spaced the gutters wider (line-height 1.45, margin 0.9em) and reddened 13 existing zoom, crosshair and pages nodes that were green on the clean cut; it was redone layout-neutral and those modules re-run green; a digit-count custom property also reddened the token census, so it is not used. Card item 2 said play.html / player.css "adds a marker attribute": the author used the admin's CLASS `.is-circled`, set by JS, and left `play.html` unchanged although it is in Touches.

AC-4, constructed board and plant: `test_no_existing_fixture_has_the_extra_cell_board` measured the four shared grids and none leaves every number circled when a fully marked solution gets ONE extra black cell (bounded to single-extra-cell boards; other wrong boards were not searched); the author built a 10x10 fixture of its own (`CIRCLES_GRID`, seed 3 of a density sweep; the solver confirms exactly one solution), the board = the fully marked solution plus one extra black cell, five such cells work (`EXTRA_CELLS` = (0,4),(0,7),(1,0),(4,0),(6,0), re-derived by `test_the_constructed_board_is_what_the_card_says`); on each of the five boards every number is circled, `isSolved()` is false, the banner is hidden and `body[data-solved]` is "false", with the solution as the matched control where the check does fire. Plants rewrite the SERVED `play.js` through a Playwright ROUTE (never written to the tree or the site; the author measured that rewriting the served file and disabling the cache through CDP both let plants go unserved at random): `BANNER_FROM_CIRCLES` and `RULE_FROM_CIRCLES` each make the same board read as solved; a structural scan also keeps `isClueSolved` free of circle names (default-deny) and checks the warning text is preserved. THE FOUR GAPS: (1) crossed AND circled, `TestPublicCircles_ACrossedClueStillShowsItsCircle` reads pixels (the crossed box shows its tint at its corner and the ring is ink at its left edge for both the row and the column clue, ring size unchanged by crossing), three plants each beside a control (the tint clears the ring, the tint as an `::after` overlay, the tint hides the number); (2) agreement, SCOPE+ `tests/test_public_player_agreement.py`, `TestPlayerLooksAgree_TheCirclesAreTheSameLook` (20 nodes; the found (admin, public) value PAIR compared with each declared pair, every declared fact a key the extractor produces, the pair differs, the reason at least 120 characters; 14 one-sided plants on both sides; a stale-exemption arm and a drift-inside-a-fact arm; 10 agreeing facts enumerated as non-empty); (3) listener census, the card adds no listener, `test_every_player_control_is_in_the_ec_050_walk` runs UNEDITED and green, `test_the_circle_code_registers_no_listener_and_the_file_adds_none` holds it; (4) zoom, `TestPublicCircles_StayLegibleAndInPlaceWhenZoomedAndScrolled` (the 30x30 fixture at the zoom maximum on a desktop viewport unscrolled and on a 390 px phone scrolled a quarter and three quarters of the way into the clue gutters, because a mid-board scroll leaves no clue number in view at 300%; it samples up to 8 rings in view and UNCOVERED by hit test at the centre and four edge midpoints and checks ink on all four edges), with two DECLARED bounds written in the test (`RING_GAP_FLOOR_PX = 0.25`, the admin's own `--player-ring-gap`, measured minimum gaps 1.00 px row and 0.59 px column at the phone's 100% and 3.11 px and 1.77 px at 300%, control `--player-circle: 1.09em`; `RING_SCALE_TOLERANCE = 0.01`, measured residue 0.0003 on the phone and 0.0007 on the desktop, control a 15 px ring) and `TestPublicCircles_AnInPlaceRingIsMeasuredNotAssumed` (ring shifted right, shifted down, border-style none, faded to nothing, each with its control). DECLARED DIVERGENCES from the admin (10 entries; the three `--player-circle*` carry a measured figure each, the rest are structural): `board.--player-circle` admin `calc(var(--player-cell) * 0.88)` vs public `1.05em` (the compact gutters, a 0.42-cell numeral and line-height 1.1, cannot take a 0.88-cell ring: ring/numeral 1.47 at the panel against 2.1 if copied here, 0.59 px stacked-ring gap measured, public ring 14.98 px at 100% and 44.97 px at 300% on the 1440 px desktop); `board.--player-circle-w` 0.06 vs 0.035 of a cell (1 px at the 28 px cell floor, 3 px at 300%); `board.--player-circle-clear` 0.05 vs 0.02 of a cell (must fit the 0.35em gap between row numbers, measured 1.00 px clear); `board.--player-ring-gap` admin 0.25px, public absent; `ring.--player-ring` admin's digit-count expression, public absent (no script-set property); `ring.width`; `ring.left`; `column_ring.is_capped` admin True, public False (the widest column ring is 62.8 px at 300% in a 103 px cell); `digit_count.is_set_by_script`; `painter.pairs_twin_gutters` admin True (CARD-212), public False (this page has one gutter per axis).

Plants and evidence (author-reported): behavioural plants served by a Playwright ROUTE; each plant test asserts the unplanted control clean first, in the same test. 8 AC-2 plants (survives-undo, left-after-reset, preview-not-record, wrong-axis, first-line-skipped, last-line-skipped, repeat-by-value, toggle-without-force; one node each), 2 AC-4 plants, 13 + 4 + 3 scanner plants (the painter, collector, import and hook, and the solved-check body), 3 GAP-1 plants, 2 declared-bound plants, 4 in-place plants. The scanner is default-deny on identifiers, PROPERTY reads, strings, punctuation and computed member access (exact index sequences only) and refuses every operator, so no comparison or condition can host a second rule. Existing node ids moved when each plant is applied to the SOURCE tree, run on a scratch clone at `5f218331` over only THREE modules (circles, `test_public_player`, agreement; 222 nodes, control 222 passed; the other four public-player modules were NOT run per plant): banner-from-circles 45 (2 existing: `test_solved_fires_on_clue_satisfaction_only`, `test_the_empty_mark_is_a_dot_and_solving_is_revealed`), rule-from-circles 48 (same 2 existing), preview-not-record 44 (0 existing), left-after-reset 11, survives-undo 12, wrong-axis 55 (+3 errors, 1 existing: `test_play_page_renders_and_marks`), first-line-skipped 44, css-tint-overlay 4, css-ring-1.09em 7, css-ring-in-px 8; the counts include collateral nodes that red only because their own matched control is planted, so the number that detects a plant directly is smaller. Red-first evidence: the two test files run against the clean cut gave 80 failed, 2 errors, 14 passed of 96 selected (the 14 are implementation-independent); the author wrote the AC-1 test first and saw it red, and wrote the rest AFTER the implementation without seeing each individually red first. Seeded EC corpus: `Random(326)`, 5 puzzles x 6 patterns x 2 draws = 60 cases (asserted >= 60), 4 distinct extents (not five: the card's fixture shares 10x10 with the shared min grid), 0 mismatches, asserting circled > 0, uncircled > 0 and at least one repeated-value line with mixed flags. Browser renders for the owner, in `~/Documents/nonogram-reviews/CARD-326/`: `01-circles-100pct.png` (the 15x15 "Gift box", top 8 rows marked), `02-crossed-and-circled.png` and `02b-crossed-closeup.png`, `03-phone-100pct-solved-board.png`, `04-phone-zoom-max.png`, `05-phone-zoom-max-scrolled.png`, `06-30x30-all-circled.png`. WHAT THE AUTHOR SAW, and the item for the OWNER'S EYE: the rings are slim vertical pills hugging the digit, tighter than the admin's roomy circles; that is forced by the compact gutters the zoom tests pin, and is the declared `--player-circle` divergence. Not verified: per-plant red counts for the other four public-player modules; visual acceptability (the owner's call); the full suite; an armed `DATABASE_URL`; ruff and mypy (none configured). Not yet reviewed.

[Review 1/3] Score: **8.4 - PASS** (threshold 8.0), at tip `5f218331`. No AC or EC failure and no circle/solved confusion; the findings are small and fixable inline. Derived by the reviewer (private clones `rev326-cycle1/{tip,cut,mut,site,renders}`, the tip clone `5f218331` and the cut clone `ce22c0e7` on every run; pytest run only after the CARD-357 lock cleared; a preview server started and stopped): G-7 over all tests with `-o addopts= --collect-only -q` cut 10623 ids, tip 10717, 0 removed, 94 added (74 circles, 20 agreement), matching the author; the seven public-player modules at the tip 385 passed, 0 skipped, 0 failed, with zoom, crosshair, maybe and pages passing UNEDITED, `tests/test_public_player.py` unchanged so the listener census runs unedited, no `addEventListener` in the diff, `play.html` and the toolbar bound unchanged; the 13 census modules 1102 passed, 3 skipped (all `tests/conftest.py:233`, "Database not reachable: DATABASE_URL is not set"), 0 failed; no added skip, xfail or bare early `return` (the only deleted line is the `.is-col .player-clue-num` rule, which was widened); no `touch-action` line added; G-1 `solver_state.js` and `tokens.css` SHA-256 equal to `src/nonogram/admin/static/` in an assembled site, `src/` diff empty. AC-4 RE-DERIVED WITHOUT THE PAGE'S CODE: the solver says `CIRCLES_GRID` has exactly 1 solution; a node run of `circledClues` on the five `EXTRA_CELLS` boards circles all 51 numbers on each; an independent line-run check says none of the five is solved and the solution is; an exhaustive single-extra-cell search finds exactly those 5 cells; the author's route plants are SERVED (the planted banner reads as solved); the reviewer's own variants all leaked the wrong board (`isClueSolved` using circles only on a repeated-value line; the banner when two rows are circled; the banner when all rows are circled; `body[data-solved]` driven from circles), each with a served canary, and the author's `body == "false"` assertion caught the body-only one. EC corpus: 5 puzzles x 6 patterns x 2 draws = 60 cases, at least 4 distinct extents, 0 mismatches; it compares the page with `circledClues` evaluated in the page, which is independent of the DOM but BY DESIGN not independent of the module. Zoom bounds re-measured on the assembled 30x30: on the 390 px phone at 100% the smallest gaps are 1.00 px (row) and 0.59 px (column), at 300% 3.11 and 1.77; ring height 12.34 -> 37.03 on the phone and 14.98 -> 44.97 on the 1440 px desktop; the widest ring 62.8 px in a 103 px cell; the controls hold (`--player-circle: 1.08em` gives a 0.25 px gap, exactly the floor, and `1.09em` gives 0.12 px, red; the 15 px control gives a scale ratio of 1.0; a +0.1 px ring gives -0.5%, inside the 1% tolerance); contrast of the ring (#1c2333) on the clue ground (#efe9dc) 12.98:1, computed by hand. Plants fired by the reviewer: 14 behavioural route plants on `play.js`, each with a canary (columns-only index +1, rows-only +1, force undefined when false, add-only-never-remove, rows-only, last column skipped, last span skipped, repeated lines never circle, comma operator, transposed indexes, displayed board instead of recorded, rows/columns swapped in the call, paint only when done grows, paint skipped on redo) plus 4 AC-4 variants x 2 boards: all caught; CSS plants in the crossed test caught opacity, border-width 0, ring recoloured to the tint, ring resized (the `!=` on the ring size the author never planted) and a clip, while `z-index:-1` and a number background did not hide the ring (the ring sits in the sticky box's own stacking context: judged ineffective plants, not holes); 5 source plants on the tip clone in the 3-module run (cols-off-by-one, add-never-remove, comma-k, indexes-transposed went red, the comma-k and transposed ones only through behaviour tests because the scanner passes them clean (F-1); solved-from-circles-repeats went red); 9 one-sided agreement plants into copies were all reported; the `not in` guard the author left unplanted (`a[fact] not in {"", _ABSENT, "False"}`) reds as intended. Every declared reason is TRUE and carries a reason (0.88/0.6 = 1.47 and 0.88/0.42 = 2.1 hold, 0.06 x 28 = 1.68 px holds, the column-cap and `--player-ring-gap` claims match `admin.css`); the structural entries are acceptable (`ring.left` is a genuine centring and `ring.width` carries its numbers elsewhere).

Findings, ranked: F-1 (low-medium, inline): the AC-3 scanner has holes, so "no operator, no second rule" is narrower than stated: these pass `circle_code_violations` clean: the comma operator `(circled[axis][line][k], k)` (a second rule, `k > 0`), indexes `[k][line]` or `[line][line]`, a second `is-circled` toggler elsewhere in `play.js` written with single quotes or a template literal, and a rule in a function not named like "circle"; behaviour tests catch the first two, a second toggler passed all 222 nodes (its effect was a no-op, so only the STATIC claim is false; no behavioural miss found); fix: drop `,` from the painter punctuation, make the index sequence an ordered exact `axis/line/k`, count `is-circled` across all quote kinds. F-2 (low, inline): the agreement extractor is default-allow on unlisted properties: a one-sided `z-index`, `opacity`, `transition` or `transform` on the ring, or `opacity`/colour on `.is-circled`, was UNSEEN (a ring transition would contradict the CSS comment "No transition"); fix: compare the whole merged declaration set of the ring rules. F-3 (trivial): stale prose, "Nine entries in three groups" where the table has 10 entries and 13 agreeing facts. F-4 (low): the pixel checks are narrow: on the phone at 300% only 6-7 of 195 circled rings are in view and uncovered (57 of 195 on desktop), so the up-to-8 sample covers all of them and a defect confined to a few rings elsewhere would escape; at phone offsets 0 and 0.75 only column rings are sampled (the test allows no row kind on a phone); the crossed check reads only the left edge at mid-height, so a plant clipping the ring's right half passed for the row box; a ring shifted by less than 2 px is invisible to the 2 px band. F-5 and F-7 (info): plant tests assert only "some problem", not which scenario; the EC corpus never asserts that the page's total equals the module's total (a longer DOM would pass silently); `test_the_circle_code_registers_no_listener_and_the_file_adds_none` scans two bodies only, the census test holds the file. F-6 (OWNER'S EYE, not a defect): the tight rings, a declared design choice forced by compact gutters the zoom tests pin; the ring is legible with a 1 px line at 100%; neighbouring rings are 1.00 and 0.59 px apart on the phone and 1.25 and 0.72 px on desktop, so repeated numbers such as 1 1 1 1 1 read as a chain; in the reviewer's and the author's renders at 100% on a 390 px phone and a 1440 px desktop, 15x15 and 30x30, with two-digit numbers, repeats and a crossed clue, the rings are legible, and a crossed clue still shows its ring; the compact look is the admin's look made small, and the final call is the owner's. Not verified: the author's full 23-plant table (the reviewer ran 14 route plants, 5 source plants, 7 CSS plants and the agreement plants); per-plant red counts over the other modules; any real device; red-first evidence for ACs 2-5, which the author says does not exist. Next: a fix round for F-1 to F-3 (and F-4/F-5 where cheap), then the merge gate.

[Fix round for review 1, commit `239cc7e9`] Verified by the orchestrator at tip `239cc7e9`: worktree clean; one commit over the reviewed `5f218331`; over the cut `ce22c0e7` still exactly the four files (`player/play.js`, `player/player.css`, `tests/test_public_player_agreement.py`, `tests/test_public_player_circles.py`); `player/play.js` and `player/player.css` have a ZERO-line diff since the reviewed commit (the fix round is tests only); `src/`, `play.html`, `tests/test_public_player.py`, `solver_state.js`, `tokens.css` and `meta/` diffs 0; `git diff --stat 5f218331 HEAD` 2 files, 213 insertions and 25 deletions (`tests/test_public_player_agreement.py` 38, `tests/test_public_player_circles.py` 200); no added bare early-`return` line and no added skip or xfail decorator; my own run of the circles, agreement, `test_public_player` and `test_suite_profile` modules unlifted gave 696 passed. Author-reported, not re-run by me: the seven public-player modules plus the 13 census modules together 1511 passed, 3 skipped (all "Database not reachable: DATABASE_URL is not set"), 0 failed, 0 errors; G-7 against the cut 0 removed or renamed and 118 added (94 from `5f218331` plus 24 new), against `5f218331` 0 removed or renamed and 24 added (circle-code scanner plants 7, crossed-clue clip plants 3, in-place residue tests 2, ring and `.is-circled` agreement plants 12); the plant test's existing parametrize ids unchanged (a fourth `expect` field was added to its parameters).

F-1, the scanner holes: a comma is now allowed only as a call argument, an arrow-parameter separator, the one `of [...]` literal or an object literal after `return`, and anywhere else is reported as a comma operator; index chains are read IN ORDER (`circled` must be read `[axis][line][k]`, `clueNumbers` as `[axis]`; the earlier set-membership check could not see `[k][line]` or `[line][line]`); `is-circled` is counted across all quote kinds and every function, comments stripped, and must be exactly 1. Seven new plants in the existing parametrized scanner test, the unplanted source clean first in the same test, each moving exactly its one node: the comma operator `(circled[axis][line][k], k)`, `circled[axis][k][line]`, `circled[axis][line][line]`, `circled[line][axis][k]`, a second toggler in single quotes in another function named `decide`, a second toggler in a template literal, and a `className = "... is-circled"` assignment. The author ran the OLD scanner from `5f218331` on five of them (comma, `[k][line]`, `[line][line]`, single-quote toggler, template toggler): it reported all five CLEAN, confirming the holes; the new one reports each. F-2: the agreement extractor now compares EVERY declared property of the number, ring and circled rules as the union of both sheets with a missing property compared as absent; plants into in-memory copies of `admin.css` and `player.css` (never `src/` on disk): on the ring, both sides, z-index, opacity, transition, transform (8 nodes) and on `.is-circled`, both sides, opacity and color (4 nodes); each asserts the exact property fact moves and the unplanted pair is clean first; the class now has 32 nodes (was 20). F-3: the stale "Nine entries in three groups" is replaced by a sentence saying one entry per property, the count left to the table. F-4(a): the crossed check now reads all four ring edges for both the row box and the column box, with 3 new clip-path plants (right half, lower half, upper half), each beside its control; before the edit a plant clipping only the right half passed. F-4(c): the in-place band is a named constant `IN_PLACE_BAND_PX = 2` with its residue declared next to it and measured at 300% on 8 sampled rings: a 1 px shift is invisible (0 of 8 report), a 1.5 px shift is caught (7 of 8; 2 px and 3 px also 7 of 8); two nodes, the 1 px shift asserting NOT caught and the 1.5 px shift asserting caught, each with its control first. F-5/F-7: the AC-2 plant test now carries an `expect` field and asserts the scenario that owns each plant fired (survives-undo "undo", left-after-reset "reset", preview-not-record "mid-drag", the rest "differ from circledClues"); the EC corpus also asserts the page's TOTAL numbers and TOTAL circled numbers equal the module's; the listener-scan test's docstring now says it covers the two circle bodies only and that `tests/test_public_player.py::test_every_player_control_is_in_the_ec_050_walk` holds the rest of the file.

**DISCREPANCY, unresolved:** F-4(b) coverage. The reviewer reported that on the phone at 300% only 6-7 of 195 circled rings are in view and uncovered (57 of 195 on desktop). The author could NOT reproduce that: on its fixture (the 30x30 fully marked at the 300% maximum, 423 circled numbers, a different fixture and count from the reviewer's 195) it measured, in view and uncovered / sampled: desktop unscrolled 61 (45 column, 16 row) / 8 (6 column, 2 row); phone a quarter into the gutters 16 (all row) / 8; phone three quarters in 15 (10 row, 5 column) / 8 (5 row, 3 column); about 3.6% of circled rings in view on the phone; at the first offset no column ring is sampled. The figures are stated in the zoom class's declared-bound comment as measured, with the claim narrowed to "the rings that can be seen are in place". The author did NOT change the "no row kind on a phone" allowance (it measured and declared the coverage instead). Not done by the author: F-6 (the tight rings, the OWNER's eye, left as declared); per-plant red counts against the SOURCE tree were not re-run this cycle (the earlier table stands for the original plants; the new plants are test-side and were each shown red or caught in their own test). Next: the merge gate.

**Closing note (merge gate, merged `423aef15`).** The review record above is not rewritten; these are the items the owner should hold, stated as the gate found them.

- **(a) F-6, the tight rings, is the owner's call.** The ring is a declared design choice forced by the compact gutters the zoom tests pin; two reviewers' renders found it legible. The final visual judgement is the owner's: renders are in `~/Documents/nonogram-reviews/CARD-326/` and the play-test build is `build/site-circles` in the CARD-326 worktree, which is kept for that reason.
- **(b) The coverage figure is unresolved.** The reviewer measured 6-7 of 195 circled rings in view and uncovered on the phone at 300%; the author could NOT reproduce it (15-16 of 423 on its own fixture, a different fixture and count). It is left unresolved, and the zoom bound's claim is narrowed to "the rings that can be seen are in place".
- **(c) Red-first evidence is thin.** It exists only for AC-1; the rest of the tests were written after the implementation. Per-plant red counts on the source tree were measured over three of the seven public-player modules only.
- **(d) The EC corpus is independent of the DOM, not of the module.** It compares the page with `circledClues` evaluated in the page: independent of the DOM by design, but not of the module that defines it.
- **(e) On `main`, NOT deployed.** The live site serves the crosshair build; the circles ship only if the owner asks for a deploy.
- **Gate finding, not this card:** `tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces` takes about 119 to 121 s armed on this machine, at `tests/hang_guard.py`'s 120 s per-test ceiling, which `_exit()`s the whole run; on the default ceiling the full run died there twice (identical logs, 6326 results then nothing), and the test alone did the same on a clean clone of the pre-merge main tip. The gate ran with `NONOGRAM_TEST_HANG_SECONDS=300`. A killed run also leaves `tests/test_db_engine_lifecycle.py` mutated in the working tree.

## Premise re-verified 2026-11-05 (zoom CARD-324 and the crosshair CARD-325 have merged since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC; it corrects what the card says about the tree and names gaps.

- **Dependencies and shared module are intact.** `circledNumbers(clue, cells)` and `circledClues(board, rows, columns)` are still exported by `solver_state.js` (neither takes a solution), `play.js` already imports from `/solver_state.js` (zoom's `ZOOM_MIN`, `ZOOM_MAX`, `stepZoom`, `pinchZoom`, `anchoredScroll` among others) but NOT `circledClues`/`circledNumbers` (its one mention of them is the header comment that warns against building `isClueSolved` out of them, which stands and must be preserved), and `player.css` still has no circle RULE (its one mention of the word is a comment). The wiring-not-porting premise holds.
- **G-8 is STALE:** CARD-268 is `done` and nothing is editing the admin player's static files. The guardrail itself stands: do not touch `src/nonogram/admin/**`.
- **GAP 1, the clue numbers now carry a second marker.** The crosshair (CARD-325, merge `fd37038c`) toggles `is-crossed` on clue BOXES and gives them a tint. The circle marker lands on clue NUMBERS inside those boxes. Decide and state how the two coexist (a crossed clue box whose number is circled must still read as circled, and the circle must not be drawn by a rule the crosshair's tint can hide), from tokens only (G-6), and add a test that a crossed and circled clue shows both.
- **GAP 2, the look is a look the public player REIMPLEMENTS, so it is held to the admin's** (CARD-328, `done`, established `tests/test_public_player_agreement.py` as the one home for that, as CARD-325's AC-6 used it; `admin.css` has 22 circle rules to the public sheet's none). No AC here says so. Add the circles' look to that file (declaring any divergence, with its reason and a MEASURED figure, not asserting sameness wholesale) and add it to Touches; CARD-325's record on `main` shows the shape (five declared divergences, each a stated reason, the found value PAIR compared with each declared pair).
- **GAP 3, the listener census.** `test_every_player_control_is_in_the_ec_050_walk` in `tests/test_public_player.py` censuses every `addEventListener` type and reds on any addition. The card says to hook the existing repaint and add no second repaint path, so it should add no listener; if it does, that file is a SCOPE+ edit exactly as it was for CARD-325 (read CARD-325's record for what that edit looked like and why it was judged honest).
- **GAP 4, zoom.** Circles are drawn on clue numbers inside a stage zoom rescales and scrolls; they must stay legible and in place at the zoom maximum and at a scrolled offset (a test, as CARD-325's AC-7 did for the crosshair). No toolbar control is added by this card; if one turns out to be needed, STOP: `tests/test_public_player_zoom.py` reds on any new toolbar button by design and that needs an owner decision.
- **`touch-action` stays `auto`** (owner decision 2026-11-05, recorded on CARD-324).
- **What cost review cycles on this board today, so do these first time:** write each declared bound IN THE TEST with its reason, a MEASURED number and a control that fails just past it (ADR-0039/R3); a structural "reads no X" scanner must be default-deny on PROPERTY reads as well as identifiers (CARD-325's first AC-2 scanner denied only by identifier; its reviewer planted seven bypasses); every claim needs a test that fails if it is false, with a matched control in the same run; for every `!=`/`not in` you touch, plant its failure; and the AC-4 trap above (circled is not satisfied) needs a CONSTRUCTED board and a plant that makes the solved check use the circle set.
- **STANDING CENSUS RULE** (it stopped two merge gates): after your work run on your tip, with `-rEfs`, `tests/test_suite_profile.py`, `tests/test_impact_set.py`, `tests/test_check_ref_resolution.py`, `tests/test_cli.py`, `tests/test_kanban_review_record.py`, `tests/test_collected_names.py`, `tests/test_guard_integrity.py`, `tests/test_shared_fixture_controls.py`, `tests/test_full_suite_lock.py`, `tests/test_browser_fixture_scope.py`, `tests/test_naming.py`, `tests/test_fixture_integrity.py`. `test_suite_profile` counts any early `return` inside a test body as a silent host-state silence: write NO test body with a silent `return`, and never add to a frozen registry to get green.
