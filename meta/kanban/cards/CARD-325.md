# CARD-325: The public player gains the crosshair — the one admin control that reads no board at all

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d) <!-- RESTATED in review cycles 2026-11-05 at dispatch, which was LATE: this card was stamped into wave 79 with a day estimate and that reddened tests/test_kanban_review_record.py (a waved card with no Nc term) until it was restated. Was 0.5d. 2c is a forecast, not a tuned figure: the closest comparator, CARD-324 (a player feature in the same three files), took 3 review cycles against 1c; the two tests-only slice cards took 1; this one adds a design question (zoom gap, AC-7) and a cross-implementation check. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/325-public-crosshair
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-325
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`.
**Idea:** —
**Wave:** 79
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_crosshair.py, tests/test_public_player_agreement.py, tests/test_public_player.py (SCOPE+, declared by the author: the EC-050 listener census reds on any added `addEventListener` type, and `pointerleave` is new) <!-- AC-6 already said the agreement check joins tests/test_public_player_agreement.py, but Touches omitted it; added 2026-11-05 -->
**Review score:** —
**Started:** 2026-11-05T14:50Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why the crosshair is the most portable piece in `solver.js`

CARD-267 shipped the crosshair to the admin player: hovering a cell highlights
its row, its column and their clues. Measured 2026-10-30: it lives **only** in
`src/nonogram/admin/static/solver.js` as `wireCrosshair(stage)`, with **nothing
in the shared module** — `grep -c crosshair solver_state.js` is **0**.

So unlike CARD-324's zoom, there is no shared function to import. But the
crosshair is also the **easiest** admin control to bring over, for a reason
CARD-267 wrote down as its own G-5 and the call site still records at
`solver.js:1046-1047`: **the crosshair reads no board.** It is pure DOM over the
stage — no cell state, no history, no clues data and emphatically no solution.
Everything that makes the answer-dependent features unreachable from this page
is absent here.

**This card therefore has a design question the other four do not:** the same
behaviour will exist in two files. The owner's 2026-10-30 decision was to wire
the public player up now and **keep two UI layers** rather than extract a shared
one (the extraction was offered and declined — CARD-268 is live in `solver.js`,
and an extraction would have to wait for it). So the duplication here is
**deliberate and recorded**, not discovered. CLAUDE.md already names the
precedent for exactly this situation: `solver/propagate.py`'s `mask_runs`
reimplements a clue-encoding check natively rather than importing across a
boundary, and is **cross-checked against the other implementation from the test
tree, where the import is legal**. Do the same here.

## What to implement

1. Read `wireCrosshair` in `src/nonogram/admin/static/solver.js` **in full**,
   including the comment block at `solver.js:420-455`, which records four
   decisions already paid for: the gutter corner, the no-hover phone case, why
   an exempt touch would undo every touch crosshair, and why a remembered
   position with nothing painted is the half-painted crosshair the card refuses.
   **Do not rediscover these.**
2. `player/play.js`: a native crosshair over `[data-player-stage]`, following
   those decisions. It reads the DOM and nothing else — if it needs a board, a
   clue array or the payload, the design has gone wrong.
3. `player/play.html` / `player/player.css`: whatever attributes and rules the
   highlight needs, from tokens. The admin uses `admin.css`'s 12 crosshair
   rules; `player.css` has none — mirror the **look**, not the selectors, since
   the two sheets do not share class names everywhere.
4. **Cross-check the two implementations from the test tree.** One test imports
   nothing from `src/` at runtime (the public page cannot), but the test tree
   may read both files: assert that the public crosshair's decisions match the
   admin's on the four cases item 1 names, so a later change to one is visible
   against the other. This is the card's answer to the duplication.

## Acceptance criteria

- **AC-1** (hover highlights the cross): *Given* the public board, *when* the
  pointer enters a cell, *then* that cell's row and column carry the crosshair
  marker and its row clue and column clue are highlighted; *when* it leaves,
  *then* every marker clears. (test: `TestPublicCrosshair_HoverHighlightsTheCross`)
- **AC-2** (the crosshair reads no board): *Given* the shipped code, *then* the
  crosshair's implementation references no cell state, no history, no clue data
  and no payload field — asserted structurally over the source, not by eye.
  (test: `TestPublicCrosshair_ItReadsNoBoard`)
- **AC-3** (it paints nothing): *Given* any hover or pointer movement across the
  board, *then* the recorded history is unchanged and no cell's `data-state`
  moves. (test: `TestPublicCrosshair_HoverRecordsNoStroke`)
- **AC-4** (the drag case): *Given* a drag in progress, *then* the crosshair
  behaves as CARD-267 decided for the admin player — **state which of its four
  recorded decisions applies and test that one**, rather than asserting a
  behaviour this card invents. (test: `TestPublicCrosshair_ADragKeepsTheDecision`)
- **AC-5** (no hover, no half-crosshair): *Given* a touch device with no hover,
  *then* the page shows either a full crosshair or none — never a remembered
  position with nothing painted, which is the state CARD-267 explicitly refuses.
  (test: `TestPublicCrosshair_TouchIsNeverHalfPainted`)
- **AC-6** (the two implementations agree): *Given* both players' sources, *then*
  the crosshair's agreement check **joins `tests/test_public_player_agreement.py`**,
  the file **CARD-328** establishes as the one home for "a look the public player
  reimplements is held to the admin's" — asserting they make the same decision on
  the four cases of item 1, and **declaring** any divergence with its reason
  rather than asserting sameness wholesale. Do not start a parallel guard here.
  (test: `TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions`, in that file)

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`** — byte-identical
  build-time copies (ADR-0041/R3).
- **G-2: do not touch `src/nonogram/admin/**` AT ALL**, including `solver.js`,
  which this card reads. **CARD-268 is editing exactly that file in a sibling
  worktree.** Read it; do not change it. If the admin crosshair needs a fix,
  that is a finding to raise against a new card, never an edit here.
- **G-3: the crosshair reads no board** (CARD-267's own G-5, carried over). If
  an AC seems to need board state, stop and raise it — a crosshair that reads
  the board is a different feature with a different safety argument.
- **G-4: no solution reaches the page** (ADR-0041/R2, CARD-283 G-4).
- **G-5: marking, Region, undo/redo and reset are untouched** — their tests run
  unedited, and the crosshair must not change which pointer events reach them.
- **G-6: styling from tokens only.**
- **G-7: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data (check: CARD-282's and CARD-283's guards)
- ADR-0041/R3 — the board-state module and tokens are byte-identical build-time copies, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering; the crosshair is **rendering only** and so adds nothing to the module (check: AC-2)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures)
- CON-021 — play state is this browser's localStorage only; the crosshair persists nothing (check: review-lens)

## Architecture context

- **FR:** FR-045 (the public player)
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R2, R4, R8
- **Components:** COMP-011
- **Trace:** not updated by this card (quick-card rule; see CARD-323's note)

## Design context

- **Design system:** `player/player.css`, every value a token (G-6). The crosshair tint must stay distinct from the maybe cell's `--color-surface-hover` (CARD-323) and from CARD-327's hint highlight, if both land.
- **UI components:** `.player-cell` and the clue cells gain the crosshair marker; `.player-stage` carries the listeners.
- **Screens:** `/play/<key>`.
- **Standards:** the crosshair is a hover affordance and never the only carrier of meaning; the owner validates the look on a real puzzle render before merge.

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
  CARD-326, CARD-327 all touch `player/play.js`, `play.html` and `player.css`,
  so their overlap is **1.0** and the conflict graph serializes any two in one
  wave. Deliberately not a `Depends on` edge (the board's rule, stated on
  CARD-220's `Wave:`).
- **[The duplication is the owner's decision, dated]** 2026-10-30: offered the
  choice between wiring `player/` up now and extracting a shared UI layer
  first, the owner chose to wire up now, with two UI layers remaining. AC-6 is
  what keeps that choice honest — without it, "the same behaviour in two files"
  is a promise nothing checks. If a future card does extract the shared layer,
  AC-6's test is the thing it deletes, and that deletion is the evidence the
  extraction worked.
- **[AC-6 moved to CARD-328's file, same day]** The agreement pattern stopped
  being this card's invention within hours: `2400501b` landed the dot and the
  solved reveal on `main` by reimplementing two more of the admin's looks, and
  **CARD-328** was cut to own the guard over them. Its
  `tests/test_public_player_agreement.py` is now the one home for the pattern —
  including the decision this card would otherwise have had to make alone, that
  a guard asserts the **shared** parts and **declares** the legitimate
  divergences (measured there: the dot's rules are declaration-for-declaration
  identical, while the sweep's selectors differ for a stated reason, so a guard
  demanding sameness wholesale would be false). Read CARD-328 before writing
  AC-6's test; a third copy of this reasoning is what it exists to prevent.

[Author round, commit `ac0ab9db`] Verified by the orchestrator: tip `ac0ab9db`, one commit over the cut `f8bb2eb8`, worktree clean; five files, all insertions (`player/play.js` +148, `player/player.css` +40, `tests/test_public_player.py` +12, `tests/test_public_player_agreement.py` +378, new `tests/test_public_player_crosshair.py` +1220), zero deletions in any test file; `src/`, `player/solver_state.js`, `player/tokens.css`, `player/play.html` and `meta/` diffs 0; the 1 `touch-action` line in the diff is text in a comment or test, not a rule change (not yet checked line by line by me; the review will). Author-reported, not yet re-run by me: crosshair module plus the whole agreement file 152 passed; `test_public_player.py`, `_zoom`, `_maybe`, `_pages` 127 passed, no skips; G-7 node-id set difference over 6 modules 201 ids before, 279 after, 0 removed, 78 added; the TDD red run with `play.js` and `player.css` swapped to the originals gave 67 failed and 10 passed (the 10 true without the feature). Design: `wireCrosshair(stage)` and `crossedParts` in `play.js` use the browser hit test (`cellUnder`) and toggle `is-crossed` on cells and clue boxes; it reads no board, history, clue text, payload, storage or network and never calls `preventDefault`. CARD-267's four decisions: (1) a non-cell point keeps the crosshair, tested by `test_a_clue_box_and_the_corner_keep_the_crosshair_where_it_was`; (2) the no-hover phone, `TestPublicCrosshair_TouchIsNeverHalfPainted`; (3) touch is exempt from the leave rule, asserted by recording that a touch `pointerleave` really fired; (4) no half-painted crosshair, kept BY CONSTRUCTION (this page draws its table once, so there is no redraw to call `forget()` from) and held by `test_the_public_page_has_no_redraw_to_forget_after`, a declared divergence in AC-6. AC-7 (added by the author to close the zoom gap, real tests): `TestPublicCrosshair_ItLandsOnTheCellUnderThePointerWhenZoomedAndScrolled`, covering zoom max, a scrolled stage, a scrolled page at 844x390, and a two-finger pinch (a second pointer takes the crosshair off; none is left when the fingers lift). AC-6: `TestPlayerLooksAgree_TheCrosshairMakesTheSameDecisions` in the agreement file, five declared divergences each with a stated reason (public also hears `pointerup`/`pointercancel` to count fingers, also clears on `pointerdown`, also reads the pointer type in `pointerdown`, has no redraw to forget after, and so needs the cross painted for its "already there" shortcut); the CSS half holds the same three selectors and the one property (`background`) and declares the tint difference (9% of `--color-text` mixed into `--grid-paper`, because `--color-surface-hover` is the public Maybe cell's ground and `--color-accent-tint` is the admin hint line's tint that CARD-327 brings over). 15 author plants, each with its matched control green and 0 skipped, moved 24, 4, 3, 3, 12, 40, 38, 15, 23, 21, 15, 17, 2, 2 and 1 node ids; AC-2's structural scanner is default-deny with 16 parametrized plants. Renders for the owner, in `~/Documents/nonogram-reviews/CARD-325/`: `01-hover-100pct-desktop.png`, `02-hover-zoom-max-scrolled-stage.png`, `03-hover-zoom-max-page-scrolled-landscape.png`, `04-touch-tap-phone-stays-after-lift.png`, `05-mid-pinch-no-crosshair.png`. Not seen by anyone: a real phone, or real-device native pinch (the pinch tests run Chromium under CDP, where the page's native pinch stays engaged after a two-finger pinch, `visualViewport.scale` 1.28, which the tests correct for and the code comment explains; this is the already-declared `touch-action: auto` residue from CARD-324). No toolbar control was added, so zoom's wrap bound is unaffected.

Findings routed, not fixed: (a) SCOPE+ `tests/test_public_player.py`: `test_every_player_control_is_in_the_ec_050_walk` censuses every `addEventListener` type and reds on any addition (the crosshair adds 5 listeners, `pointerleave` a new type); the author derived the crosshair's five from `wireCrosshair`'s own text and pinned them by name so a sixth still reds, and says folding the crosshair into marking's four listeners would not avoid `pointerleave`: an owner call if the owner prefers it; (b) the ADMIN's `wireCrosshair` has no pinch decision (it listens only to `pointerdown`, `pointermove` and `pointerleave`), so a two-finger pinch on the admin player probably starts or leaves a crosshair; not tested on the admin, not carded (G-2); recorded in the AC-6 declarations; (c) on the phone at 300% with scroll 0 no whole cell is reachable because the row gutter is wider than the stage (CARD-324's measured trade-off), so the unscrolled baseline in the AC-7 tests is a desktop viewport.

[Review 1/3] Score: **8.3 - PASS** (threshold 8.0), at tip `ac0ab9db`; no blocker, no finding an owner decision. Derived by the reviewer: the six named player modules unlifted 279 passed, 0 skipped (crosshair 58, agreement 94, `test_public_player` 34, zoom 39, maybe 21, pages 33); G-7 over the six modules 201 node ids before, 279 after, 0 removed, 78 added (agreement 20, crosshair 58), the edits to existing test files pure insertions; scope exactly the five files, `src/` and `play.html` diffs 0; `tokens.css` and `solver_state.js` byte-identical to `src` (G-1). The author's "one `touch-action` line" is THREE comment lines (the CSS keeps `touch-action: auto`; immaterial; the author's figure is corrected here). All 15 author plants killed with a matched control (78 passed, 0 skipped) in the same harness; of the reviewer's 15 edge mutants 14 were killed (11 by browser tests, 3 only by the agreement file's text-level facts: pen exempt from leave, `preventDefault` added) and 1 survived. Plant caveats, not blockers: P11 (no null guard) is behaviourally equivalent (`moveTo(null)` throws inside the handler, the exception is swallowed, nothing paints) and is seen only by the agreement text facts; removing the primary-pointer reset alone, or "a lift never ends the pinch" alone, each survives because they mask each other (removing both is killed by `test_crossing_resumes_after_a_pinch`); a pen counted in a pinch and a third finger painting have no test. AC-6: the five declared divergences are true and each is a stated reason, not a restatement (the admin's pinch lives in `beginPinch`, it clears only on `pointerleave`, its `redraw()` calls `forget()`, `drawBoard` has one call site); sameness is not asserted wholesale (the found value PAIR is compared with each declared pair, so drift inside an exempted fact reds); planting six mutations into a COPY of `solver.js` reds the class with 14 to 16 failures each against 20 passing unmutated. SCOPE+ `tests/test_public_player.py` (+12): reds without the edit, a sixth listener still reds with it in all four plants (`keydown` inside `wireCrosshair`, `pointerleave` in `start()`, `mouseleave` for `pointerleave`, a duplicated `pointermove`), weakens nothing; the reviewer judges it the honest repair and not an owner decision (`pointerleave` is the one new type and folding the crosshair into marking's listeners cannot avoid it, because no existing event reports a mouse leaving the stage). The harness correction for the native-pinch offset (`visualViewport.offsetLeft/Top` after a CDP two-finger pinch) is sound and not vacuous: removing it reds `test_crossing_resumes_after_a_pinch` (the cross lands on (8,1) instead of (6,0)), flipping its sign reds it, and the restored control is green. Visual (author's renders 01, 02, 05 read correctly, plus the reviewer's own at 100% and 300%): the crossed row stays distinguishable and legible; computed independently by the WCAG formula, clue text on the tint 12.96:1, text on paper 15.44:1, filled cells under the cross 8.19:1, a crossed Maybe cell's teal "?" 6.09:1, tint against paper 1.19:1. The tint is `color-mix(--color-text 9%, --grid-paper)`, Chromium computes rgb(235,233,230), matching a hand mix; tokens only, no literal colour. Findings: F-1 AC-2's scanner is "default-deny" by IDENTIFIER only; PROPERTY reads are a blacklist, and planted into `wireCrosshair` none of `.attributes`, `.className`, `.classList.contains('is-solved')`, `getAttribute('data-'+'st'+'ate')`, `getAttributeNames()`, `.children[0]`, `.nextElementSibling` was reported (fix inline: an allowlist, about 10 lines; real exposure is small because `data-state` holds the player's marks, not the solution, and ADR-0041/R2 holds by the payload); F-3 the tint-versus-Maybe test asserts only `!=`: the crossed tint rgb(235,233,230) and the Maybe ground rgb(241,235,221) have a luminance contrast of 1.019 and differ by a 9-unit blue shift, so a near-miss tint would pass (fix inline with a minimum channel distance); F-4 a stale comment in the agreement file ("Four entries, all of them consequences of one fact" above a table of five); F-5 some guards are text-only (pen leaving the stage, `preventDefault` in a crosshair listener, a pen in a pinch, a third finger, a page error): a `pageerror` collector would turn P11 into a real kill; F-6 the comment-only `touch-action` figure above. F-2 (OWNER NOTE, not carded, not an AC defect): at 300% on the real assembled site in HEADLESS Chromium, after a wheel scroll with the pointer still, the cell under the pointer went from (9,16) to (13,16) and then (13,19) while the cross stayed at (9,16); AC-7 scrolls THEN moves, so it cannot see this; the admin has the same design; a headed browser may send a synthetic move after scrolling and the reviewer could not verify that, so it is unconfirmed on real hardware. ADMIN PINCH PARITY (measured on a copy, with a two-finger CDP touch on the admin editor page): finger 1 down puts the cross at (3,3), finger 2 down moves it to (9,9), a spread moves it to (10,8), and after the lift it is still there: the admin starts, follows and leaves a crosshair on a pinch. Not this card's to fix (G-2) and the divergence is declared; not carded. Not verified: real touch hardware, headed desktop Chrome after a scroll, Safari, Firefox, and the full suite.

[Fix rounds for review 1, commits `dee2a59e` and `fb0131f1`] Verified by the orchestrator at tip `fb0131f1`: worktree clean; over the cut `f8bb2eb8` the same five files as the reviewed commit and nothing else (`player/play.js`, `player/player.css`, `tests/test_public_player.py`, `tests/test_public_player_agreement.py`, `tests/test_public_player_crosshair.py`); `src/`, `play.html`, `solver_state.js`, `tokens.css` and `tests/helpers` diffs 0; `player/player.css` unchanged since the reviewed `ac0ab9db`; zero deleted lines in any test file; my own run of the crosshair, `test_public_player`, zoom and agreement modules unlifted gave 237 passed, no skips. `dee2a59e` (tests only): F-1 AC-2's property reads are now an allowlist of 19 names derived from what `wireCrosshair`, `crossedParts`, `cellUnder` and `isAt` use, computed member access is refused, eight parametrized bypass plants each go red with the unplanted source clean in the same test; F-3 the crossed tint must be at least twice as far (6.0 euclidean sRGB, read from `tokens.css`) from the Maybe ground as the design system's two near-identical warm grounds are from each other (`--color-surface-hover` and `--color-surface-sunken`, 3.0 apart); the real tint is 11.0 away, a margin of 1.8x, unchanged, and a 99%-`--color-surface-hover` plant reds `test_a_crossed_cell_is_not_the_colour_of_a_maybe_cell`; F-4 the stale comment corrected; F-5 the crosshair module has its own `browser_page` with a `pageerror` collector (plant P11, no null guard, now moves 4 node ids red where it was undetected) and `test_a_third_finger_neither_paints_nor_follows` (plant E14 moves 1).

A DEFECT IN THE CARD'S OWN `play.js`, found by the review's surviving mutant E09 and proved by the author's test: `wireCrosshair`'s pointerdown reset its finger count on ANY primary pointer, but `isPrimary` is per pointer TYPE, so a pen press while a finger was down wiped the finger and touch plus pen never reached two (`play.js` itself counts touch and pen together as a pinch); the crosshair painted at the pen's cell. Fixed in `fb0131f1`, orchestrator-authorized (`play.js` is in Touches, the fix is smaller than a card): the count is now a `Map` of pointer id to type and a primary pointer resets only the entries of its OWN type (`pinching = down.size >= 2`), so a pen counts with a finger, a finger counts with a pen, and a lost `pointerup` is cleared by the next primary of the same type. `git diff ac0ab9db -- player/play.js` is 2 hunks and 19 changed lines, nothing else; the listener census is unchanged (no listener added), so the five pinned in `tests/test_public_player.py` stay exact. Three tests added: `test_a_pen_counts_toward_a_pinch`, `test_a_finger_counts_toward_a_pinch_that_a_pen_began` (both red on the shipped code), and `test_a_lost_pen_pointerup_does_not_stick_a_pinch` (synthetic `PointerEvent`s, because a real pen cannot lose its own release; green on the old code, it guards the opposite mutant). Plants with matched controls and 0 skipped: E09 (`isFinger` drops pen) 2 node ids, old behaviour re-planted 2, primary-resets-nothing 1. Author-reported, not re-run by me: six modules 291 passed, 0 failed, 0 skipped; G-7 201 ids before (carried from the first round's collection on main), 291 after, 0 removed, nothing renamed or merged. THE REVIEWER DID NOT SEE THIS `play.js`: review 1 scored `ac0ab9db`; the 19-line fix and the `dee2a59e` tests were verified by the orchestrator and by their own plants, not re-reviewed, and the merge gate's armed full suite is the check on them. Not done: F-2 (an unconfirmed stale crosshair after a wheel scroll with a still pointer), by design.

## Premise re-verified 2026-11-05 (zoom has merged since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC; it corrects what the card says about the tree.

- **Dependencies are met.** CARD-328 (owner of `tests/test_public_player_agreement.py`) is `done` and the file exists; CARD-267 and CARD-268 are `done`.
- **G-2's "CARD-268 is editing exactly that file in a sibling worktree" is STALE:** CARD-268 is done and nothing is editing `src/nonogram/admin/static/solver.js`. The guardrail itself stands: read `wireCrosshair`, do not edit it.
- **The `solver.js` line numbers in item 1 have moved** (`420-455` is now about `424-468`; the `1046-1047` call site is now about `1162`). Do not use any line number; find `wireCrosshair` and the four decisions by NAME and by their comment text (gutter corner, no-hover phone case, why an exempt touch would undo every touch crosshair, the half-painted crosshair the card refuses).
- **`wireCrosshair` is in the admin file only:** `crosshair` has 0 mentions in `play.js`, `player.css` and `play.html`, so there is nothing to reuse and nothing to collide with.
- **GAP: this card predates zoom (CARD-324, merged `18aeac30`).** No AC says what the crosshair does on a ZOOMED stage, or after the page or stage has scrolled. Cell geometry, the gutter corner and the clue highlight are all read from a stage that zoom now rescales and scrolls, and the pinch handler also owns two-pointer input. The author decides and states it: at minimum the crosshair must land on the cell under the pointer at the zoom maximum and at a scrolled offset, and a pinch must neither start nor leave a crosshair. If that needs an AC, add AC-7 here (a test, not review-lens) and say so; it is in scope.
- **No toolbar control is added by this card,** so zoom's measured toolbar wrap bound (one row at and above 839 px landscape; wraps between 560 and 838 px) is unaffected. If the author finds a control is needed after all, STOP: `tests/test_public_player_zoom.py` reds on any new toolbar button by design, and it needs an owner decision.
- **`touch-action` stays `auto`** (owner decision 2026-11-05, recorded on CARD-324): the crosshair must not depend on changing it, and a no-hover touch device shows a full crosshair or none (AC-5).

