# CARD-324: The public player gains zoom — four shared functions it already serves and never calls

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1c (0.5d) <!-- RESTATED in review cycles at wave 79's open, 2026-11-05, before dispatch rather than at it, so the wave's ratio is computable from the outset. Was 0.5d. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** `card/324-public-player-zoom`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-324
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`.
**Idea:** —
**Wave:** 79 <!-- DISPATCHED 2026-11-05T06:23Z as wave 79's player card, at the owner's request. Measured free of CARD-358: Touches intersection EMPTY. It queues against CARD-325/326/327, which all touch the same three player files; this is the one the owner's quality priority favours, since the behaviour already exists and only the glue is missing. Cut off the stamping commit. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_zoom.py, tests/test_public_player.py, tests/test_public_player_pages.py
**Review score:** —
**Started:** 2026-11-05T06:23Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

> **⚠ PREMISE CHECKED AT THE STATION, 2026-11-05 — the load-bearing half HOLDS, three carried
> figures have MOVED** (ADR-0039/R4). Re-measured before dispatch:
>
> **Holds, and it is the part the card stands on:** all **seven** names — `ZOOM_MIN`, `ZOOM_MAX`,
> `ZOOM_STEP`, `clampZoom`, `stepZoom`, `pinchZoom`, `anchoredScroll` — are exported by
> `solver_state.js` **and present in the served copy** the public player would import, so "the
> shared module already holds the behaviour and only the glue is missing" is correct.
> `player/player.css` still has **zero** zoom rules. `play.js` imports none of the seven — its one
> zoom mention is a **comment**. And the four functions take **numbers only**
> (`clampZoom(value)`, `stepZoom(current, direction)`,
> `pinchZoom(startZoom, startDistance, currentDistance)`,
> `anchoredScroll(scroll, anchor, oldZoom, newZoom)`), so **ADR-0041/R2 is satisfied by signature**
> — none can carry a solution cell.
>
> **Moved, and retracted here:**
> • *"the served copy is byte-identical to the admin's (`diff -q` clean, 1163 lines)"* — the admin's
>   file is now **1367** lines, the served copy **1163**, and `diff -q` reports **DIFFER**. The
>   served copy is a **gitignored build artefact** (`.gitignore:7:build/`), so this is a stale local
>   build 204 lines behind, not a divergence in the tree. **It does not block the card** — all seven
>   names are in it — but the round should regenerate the build rather than trust the copy on disk.
> • *"`admin.css`'s 18 zoom rules"* — now **23**.
> • *"`play.html` has no zoom group"* — **correct**, but it does carry **2** zoom mentions, both
>   comments about mobile-first reading. Stated so a round grepping for `zoom` is not surprised.
>
> **Re-derive all of these rather than carrying them.** Three of five figures moved in six days.

**The public page serves the zoom arithmetic and calls none of it.** Measured
2026-10-30: `solver_state.js` exports `ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP`,
`clampZoom`, `stepZoom`, `pinchZoom` and `anchoredScroll`; the served copy at
`build/site/solver_state.js` is **byte-identical to the admin's** (`diff -q`
clean, 1163 lines), and `player/play.js` imports **none** of those seven names.
`player/player.css` contains **zero** zoom rules against `admin.css`'s 18, and
`player/play.html` has no zoom group.

Every one of those functions is **pure arithmetic over numbers** — none takes a
board, a payload or a solution. So this is the clearest case on the board of the
thing the owner asked for: the shared module already holds the behaviour, and
only the public player's glue is missing.

A board at `limits.MAX_SIZE` on a phone is the case that makes it matter, which
is also why CARD-271 (the admin's clue-visibility card) and CARD-321 (the hint
ladder's two widths) exist on the admin side.

## What to implement

1. `player/play.js`: import **`ZOOM_MIN`, `ZOOM_MAX`, `stepZoom`, `pinchZoom`,
   `anchoredScroll`** from `/solver_state.js` — **five names, not seven** — and hold a
   zoom value in the page's state.

   > **⚠ CORRECTED 2026-11-05** (ADR-0039/R4). This instruction read *"import `ZOOM_MIN`,
   > `ZOOM_MAX`, `ZOOM_STEP`, `clampZoom`, `stepZoom`, `pinchZoom`, `anchoredScroll`"* — seven
   > names. Measured: the admin's own glue imports **five**
   > (`solver.js`: `{ZOOM_MAX, ZOOM_MIN, anchoredScroll, pinchZoom, stepZoom}`), `clampZoom`
   > occurs **0** times in `solver.js`, and `stepZoom`/`pinchZoom` clamp their own returns.
   > Importing seven plants **two unused names**. The orchestrator retracted this in the
   > premise block at the top of the card and **not here, in the instruction a round acts
   > on** — caught as F-6 by cycle 1. R4 says *everywhere it was written*, and a premise
   > block is not everywhere. **Derive nothing** — the bounds, the step and
   the clamp are the module's, and re-spelling any of them here is the defect
   this card exists to avoid. `anchoredScroll` is what keeps the cell under the
   pointer fixed across a zoom change; use it rather than re-deriving a scroll
   offset.
2. `player/play.html`: a zoom group in `.player-toolbar` — out button, readout,
   in button — modelled on the admin's (`puzzle_solve.html:283-285`):
   `data-player-zoom-action="out"/"in"` with `aria-label`s, and a
   `data-player-zoom-readout` showing the percent.
3. `player/player.css`: the zoom transform on the stage, from tokens.
   `.player-stage` (`data-player-stage`) is the existing scroll container.
4. Pinch on a touch device via `pinchZoom`, and the pointer-type question
   `gesturePaints` already answers for marking — a pinch must **not** paint.
   **This is the card's sharpest interaction risk:** two pointers down on the
   stage is a pinch, and the first of them has already begun a drag stroke under
   the existing code. State what happens to that stroke and test it.
5. Keyboard: the admin's zoom buttons carry no `aria-keyshortcuts`; do not
   invent one here. Match the admin, or state the divergence and why.

## Acceptance criteria

- **AC-1** (the controls zoom): *Given* the page at 100%, *when* zoom-in is
  pressed, *then* the readout shows `100 + ZOOM_STEP`% and the rendered cell
  size grows — the percent read from the module's constant, never from a literal
  `125`. (test: `TestPublicZoom_TheControlsChangeTheZoom`)
- **AC-2** (the bounds are the module's): *Given* the page at `ZOOM_MAX`,
  *then* zoom-in is `aria-disabled="true"` and pressing it changes nothing;
  likewise zoom-out at `ZOOM_MIN`. Both bounds are **read from
  `/solver_state.js`** in the test, so a change to the module moves the test
  with it. (test: `TestPublicZoom_TheBoundsComeFromTheModule`)
- **AC-3** (zoom paints nothing): *Given* any zoom change, *then* the recorded
  history is unchanged and no cell's `data-state` moves — zoom is a view, not a
  stroke. (test: `TestPublicZoom_ZoomRecordsNoStroke`)
- **AC-4** (the anchor holds): *Given* a scrolled, zoomed stage, *when* the zoom
  changes, *then* the scroll offset is the one `anchoredScroll` returns for that
  anchor — **asserted against the module's own return value**, not against a
  pixel figure copied into the test. (test:
  `TestPublicZoom_TheAnchoredScrollIsTheModules`)
- **AC-5** (a pinch zooms and does not paint): *Given* two pointers on the
  stage, *then* the zoom follows `pinchZoom` over the pointer distance and **no
  cell is marked** — including the cell the first pointer went down on. (test:
  `TestPublicZoom_APinchZoomsAndPaintsNothing`)
- **AC-6** (no request): *Given* every zoom interaction above, *then* the page
  issues no network request beyond the initial GET of its own puzzle file
  (ADR-0038/R2). (test: `TestPublicZoom_NoRequestPerZoom`)

## Engineering constraints

- **EC(ADR-0041/R3):** across the zoom range, every bound, step and clamped
  value the page uses equals the value `/solver_state.js` returns for the same
  input — no bound, step or clamp is re-implemented in `play.js`. Asserted over
  a seeded sweep of the whole range with a minimum case count inside the test.

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`** — byte-identical
  build-time copies (ADR-0041/R3), checked by `player/assemble.py`'s
  `COPIED_FROM_ADMIN` at assembly time and from the test tree.
- **G-2: do not re-derive the zoom arithmetic.** If a needed function is
  missing from the shared module, that is a **finding to raise**, not a licence
  to write a second copy here — a second copy is the drift ADR-0041/R3 exists
  to prevent, and this card's EC is exactly that claim.
- **G-3: no solution reaches the page** (ADR-0041/R2, CARD-283 G-4).
- **G-4: marking, Region, undo/redo and reset are untouched** — their tests run
  unedited.
- **G-5: styling from tokens only.**
- **G-6: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).
- **G-7: do not touch `src/nonogram/admin/**`** — CARD-268 is editing the admin
  player's static files in a sibling worktree.

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data (check: CARD-282's and CARD-283's guards)
- ADR-0041/R3 — the board-state module and tokens are byte-identical build-time copies, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0041/R4 / CON-021 — play state is this browser's localStorage only (check: review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: AC-6)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: review-lens — the zoom value is the module's arithmetic, the transform is rendering)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures)

## Architecture context

- **FR:** FR-045 (the public player)
- **NFR:** NFR-008
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R2, R4, R8
- **Components:** COMP-011
- **Trace:** not updated by this card (quick-card rule; see CARD-323's note)

## Design context

- **Design system:** `player/player.css`, every value a token (G-5).
- **UI components:** `.player-toolbar` gains a zoom group; `.player-stage` gains the transform.
- **Screens:** `/play/<key>`.
- **Standards:** real buttons with accessible names and `aria-disabled` at the bounds, mirroring the admin's zoom group; the owner validates the look on a real puzzle render, and **on a phone width** — the case the feature is for.

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

[Fix round for cycle 2, commit `80bf0fe5`] **The stage-height bug is FIXED and the operand classification is
DONE; the owner's readout-hiding layout is NOT shipped, because it does not fit at 844.** Five files,
**+606/−19** (`player/play.js`, `player/player.css`, `tests/test_public_player.py`,
`tests/test_public_player_zoom.py`, and `tests/test_public_player_pages.py` under `SCOPE+`). **Orchestrator-verified:**
no `src/` change, nothing under `meta/` on the branch, `touch-action` 0 lines of diff, the three protected
build directories unmodified (`build/site` 09:31, `build/site-fix` 10:25, main's deploy candidate 10:08), and
`build/site-fix2` SHA-identical to the branch's `play.js` and `player.css`. **`Touches` corrected on this card**:
it still named four files while two test files had been extended under `SCOPE+` (round 1's
`test_public_player.py` and this round's `test_public_player_pages.py`) — the same record-drift as the
listener census, found by the round, fixed by me.

[Fix round] **⚠ THE OWNER'S DECISION DID NOT SURVIVE CONTACT, AND MY ESTIMATE WAS WRONG IN THE UNLUCKY
DIRECTION.** I briefed *"hide the % readout in landscape"* on an image-derived estimate and flagged it as
**unmeasured**: group ~143 px with the readout, ~96 without, ~102 px free at 844, "just fits, ~6 px to spare".
**Measured by the round:** group **134.5 px** with the readout, **92 px** hidden; natural width of the three
groups plus two 12 px gaps **814.4 px**; toolbar width = viewport − 32. **Slack with the readout hidden:
844×390 **−2.4 px — DOES NOT FIT** (still 100 px, two rows)**; 852×393 +5.6 px (one row); 874×402 +27.6 px.
Narrowest viewport where the toolbar is one row: **847 px hidden, 889 px shown.** Hiding the readout buys
**42 px; 844 needs 47.** The round **stopped, as the brief told it to, rather than ship a layout that still
wraps at the headline iPhone width.** That instruction (*"if it does not fit at 844, say so and stop"*) is why
the estimate error cost one round-trip and not a shipped defect.

[Fix round] **Options that DO fit at 844, measured and deliberately not shipped** (they are layout choices):
**toolbar gap `--space-2` (8 px) in landscape** — +5.6 px at 844, +13.6 at 852; **zoom-button `min-width` 40 px**
— +5.6 px at 844, **but it shrinks the 44 px touch target the round itself chose**; side padding 8 px — no
change, still −2.4. **The first is the only one that keeps the touch targets**, which is the owner's stated
priority (quality and maintainability), so it is the one pursued next.

[Fix round] **A CORRECTION TO A FIGURE I GAVE THE OWNER: "whole board rows visible 3 → 2" was measured
against stage geometry that ran below the fold.** Cycle 2 compared main's player with the zoom build at
844×390 and reported 3 rows against 2. The round now reports that the zoom build's stage bottom sat at
**y 436.5 against a 390 px fold**, so part of the earlier "2" was reach the player could not see. **After the
derived cap the honest figure is about ONE whole row at 844×390** (stage 193 px, band 134 px) — *the cap
makes "rows visible" honest rather than larger.* **Not re-measured by the orchestrator.** The wrap's real
cost is therefore **larger** than "3 → 2" implied, which strengthens the case for fixing it.
**A side effect worth knowing:** at 844×390 and 100% the **column band is now UNPINNED** — the 193 px stage
cannot leave two cells under a 134 px band, so the derived rule lets go. The old "both axes pinned at the
floor" assertion was narrowed to the phone only, with the reason recorded in the test.

[Fix round] **The stage-height bug: derived, not constant.** `keepCluesInView` now writes the stage's measured
page offset as `--player-above-h`; the CSS cap is that offset plus the air (`--space-4`) plus the stage's own
2 px border, with the old one-row allowance as the fallback. **Sweep: 1026 viewports (widths 320–1440 step
20, heights 390–900 step 30), 0 violations of stage bottom ≤ `innerHeight`; the same sweep on the pre-fix
code shows 522 violations, worst 154.5 px below the fold, so the control can fail.** A `ResizeObserver` on the
stage's border box now re-asks the rule when the toolbar changes height with no window resize
(`site-fix`: 0; `site-fix2`: 1 — orchestrator-verified). The census was extended by derivation: exactly one
observer, handed `keepCluesInView`, with exactly one `.observe(`; no listener has a computed type; the
pair regex's blindness to inline arrows is **declared**, with the total count as what catches them.
The page-scroll inequality cycle 2 found unasserted (space below the stage < stage top) **is now asserted**:
worst margin **20 px** over 150+ viewports (105 against 125 at 920×390).

[Fix round] **The operand table — the cycle-2 remit, done, and it is the deliverable.** Every plant by text
with the count `== 1`, SHA-256 both ends, restored from captured content, matched control green (16 passed,
0 skipped). **Killed:** the row predicate (`clientWidth` → `innerWidth`/`offsetWidth`/`scrollWidth`; gutter
`.width` → `.height` or the column gutter; `-` → `+`; **`>=` → `>` killed by an exact-equality test, the
equality manufactured by pinning gutter and stage to whole pixels since the natural 125% equality sits at
319 px**; factor 1.5; `* width` → `* height`, **not equivalent since the cell is 29×33 at 100%**; class name;
`toggle(name, force)` → `add`/`remove`); the column predicate symmetrically; `CELLS_BESIDE` at 1, 3 and 1.5;
`visibleHeight` (min→max, `innerHeight`→`innerWidth`, `rect.top`→`rect.bottom`, dropped `clientTop`/`scrollY`,
flipped `scrollY`, `-`→`+`, `clientHeight`→`offsetHeight`/`scrollHeight` — **the `scrollY` family killed by a
new test that scrolls the page, which nothing did before**); the measured cell (a major-rule cell instead of
the first, **the 0.5 px pitch residue is real so killed, not declared**); the guard operands; the stage-cap
write; and the listeners. **Declared, each with a reason and a measurement:** `onScreen < clientHeight` →
`<=` (**equivalent** — both branches return the same number at equality); `window.innerHeight` →
`document.documentElement.clientHeight` (differ only by a classic horizontal scrollbar; **equal at 2610 of
2610 samples** in headless Chromium, so not a gap *in this environment*); and `!board` in the guard
(**subsumed** by the other three operands, since gutters and cells are built inside the one board — the
plant survives at 16 passed). **The 1.5 factor re-derived by the round over widths 320–720 step 2 across all
nine rungs, 1809 samples each: the shipped rule has 0 violations, the 1.5 mutant has 72** (e.g. 354–368 px at
150%, 406–412 px at 175%) — against cycle 2's 11 over a coarser sweep; **the test's range is derived from
geometry, not copied.**

[Fix round] **Suite:** impact-scoped **536 passed / 0 failed / 0 skipped** (the 526 baseline + 10 new), 
`DATABASE_URL` unset; armed not run. A first run found one failure
(`test_the_listing_pages_carry_no_colour_literal_and_only_defined_tokens`, a token census that reds on a
script-written custom property) which the round fixed by naming `--player-above-h` there the way
`--player-wave` is. **The round waited on CARD-358's gate lock and did not override**; its mutation
runner's first pass hit that refusal (pytest exit 4) and those mutants were re-run once the lock cleared,
so the results above are from the clean reruns. Renders 13 and 14 added (stage bottom 436.5 px against a
390 px fold, then 374 px); **both still show the wrapped toolbar, since the readout change was not shipped.**
ADR-0041/R2: `setAttribute("data-state"` is 0 under `player/`; `dataset.state` writes are still exactly the
three accounted ones; the added lines read geometry only.

[Review 2/3] Score: **7.5 — CHANGES REQUESTED** (threshold 8.0), the second 7.5 in a row. **One more
cycle is allowed.** Artefact `meta/review/CARD-324-cycle2.yml`, uncommitted. **Cycle 1's F-1 to F-6 are
all closed**, and the cycle found **one new defect in the card's own change** plus a set of surviving
mutants. The reviewer worked from copies in the scratchpad and touched none of the three protected
directories (the owner's play-test copy, `build/site-fix`, main's deploy candidate); `player/play.js` is
SHA-identical to the branch and to `build/site-fix` at the end.

[Review 2/3] **THE TOOLBAR WRAP IS CAUSED BY THIS CARD, and the fix round's "existing layout" claim is
WRONG** — measured, on the same 30×30 puzzle, main's player (no zoom) against `build/site-fix`:

| 844×390 | main | with zoom |
|---|---|---|
| toolbar | 44 px, one row | **100 px, two rows** |
| zoom group | — | alone on row 2 |
| first board row at | y 261 | y 317 |
| whole board rows visible | **3** | **2** |

Swept at 390 px tall: main stays one row (44 px) from about 780 to 932 px wide; the zoom build wraps from
780 to 880 and not at 890 or wider, so **the group needs about 889 px.** **Phones affected: iPhone
landscape at 844, 852 and 874.** No cost at 390×844 (the group fits on row 3 beside the history buttons;
152 px in both builds) or at 1440 px, and at 667–740 px main wraps too so the group adds nothing there.
**The orchestrator read this off render 12's pixel geometry before measuring (first row ends ~726 of 844,
~102 px free against ~143 px needed); the reviewer's measurement agrees.**
**And a second defect rides on it:** in the wrapped state the stage bottom is at y 437, **47 px below the
fold**, because `--player-chrome-h` allows ONE toolbar row; the page is 541 px tall, so it scrolls as well
as the stage. That is this card's `max-height: calc(100svh − chrome)` rule assuming a layout the toolbar
no longer has. **Not fixed by the reviewer — options, not a decision:** a narrower group (it needs under
~102 px of free room at 844), placing it on the tools row, a non-wrapping group, or dropping the readout
below a width.

[Review 2/3] **Cycle 1's six items, each re-verified.** F-1 closed (listener and rotating test). F-2 closed:
**E4 on the column axis reds 3 tests and its twin on the ROW axis (`.height` for `.width`) reds 4**, so the
symmetry now holds in both directions. F-3 closed: the rule holds on the **real DOM pitch**
(`border-collapse` tiling, so the rect width IS the pitch: cell 29/36/43/50/57 at 100/125/150/175/200%,
major-rule columns +0.5 px) and the reach test sweeps quarter-cell offsets with a genuine control. F-4
closed, with the residue below. **F-5 closed as defensive: the reviewer re-ran S1** (removed the restore
loop and its assert) **and both walk tests stayed green**, so "defensive" is accurate rather than asserted.
F-6 closed.

[Review 2/3] **Surviving mutants — the real finding, and it is the SAME FAMILY as CARD-363's.** All six
tests green under each: **a factor of 1.5 on the row axis** — swept viewport widths 320–520 step 6 across
all nine rungs: **the shipped rule has 0 violations (no pinned axis with fewer than one whole cell); the 1.5
mutant has 11**, e.g. 356 px at 150% and 410 px at 175%. **The test sweeps only 390 and 844 wide, so it cannot
tell 2 from 1.5** — the derived rule is right and its test does not hold it. Also surviving:
`innerWidth` in place of `stage.clientWidth` on the row axis; dropping `window.scrollY`, flipping its sign,
or dropping `stage.clientTop` (**nothing scrolls the page in the tests**); and `>=` changed to `>` on
either axis, a **measure-zero** boundary that should be declared rather than tested.
**Mutants that DO red** (re-fired and new): E4 col 3, listener removed 2, `CELLS_BESIDE = 1` 2, empty
`resize` handler 2, col predicate without the factor of 2, `stage.clientHeight` restored, E4's row twin 4,
`orientationchange` instead of `resize` 2, a different handler on `resize` 2, a second `window` listener
(census only), an inline arrow on `resize` (**census only** — the pair regex is blind to it and the total
count catches it), a stale geometry cache (rotating test), `visibleHeight` taking max for min 2, a row
factor of 3 and no row factor at all.
**One precision:** Playwright's `set_viewport_size` fires only `resize`, so the rotating test catches the
*missing* `resize`, not the wrong event by name; a regression to `orientationchange` alone is still caught.

[Review 2/3] **F-4's "conservative once the page is scrolled" holds, on an unasserted inequality.** Scrolled
to 0, half and max and zoomed through all nine rungs at 390×844, 844×390 and 390×700: **no state left zero
reachable cells, and scrolling only added reach**, so the predicate pins less — the safe direction. **But
it holds only because the space below the stage (164 px) is smaller than the stage's top offset (233 px),
and nothing asserts that.** `Math.min` guard intact: `play.js` uses a comparison. **Census:** acceptable
and **not a control**; the behavioural coverage is the rotating test.
**ADR-0041/R2 holds**: 0 `setAttribute("data-state"` under `player/`, exactly 3 `dataset.state` writes
(blank constant, `paint()`'s own board, the brush swatch), the added lines read only
`getBoundingClientRect/clientWidth/clientHeight/clientTop/innerHeight/scrollY`, puzzle JSON keys
`clues/height/key/tier/width`, `touch-action` 0 lines of diff, 0 `meta/` files on the branch.
**Suite: 526 passed / 0 failed / 0 skipped in 66 s**, `DATABASE_URL` unset, `-rEfs` — **this reproduces
the orchestrator's corrected baseline** (`464 + 59 = 523` before the round's three tests), no full suite
started, the lock absent.

[Review 2/3] **⚠ FOR THE NEXT ROUND: the cycle-1 fix round patched the cells the review named and two
more survived** — the exact pattern CARD-363 hit across three cycles, where each fix was correct and
incomplete because it was scoped to what the last reviewer pointed at, until a fourth pass changed the
**remit** to classify the whole population. **The same remit applies here, and cycle 3 is the last:**
enumerate **every operand, constant and comparison** in the pinned-gutter predicates and `visibleHeight`,
and for each either have a test that reds a mutant of it or **declare it a measure-zero / equivalent
survivor with the reason** (ADR-0039/R3). Patching the 1.5 factor alone would leave `innerWidth`,
`scrollY` and `clientTop` for cycle 3 to find.

[Fix round for cycle 1, commit `7872f3bc`] **F-1 to F-5 fixed**, three files changed
(`player/play.js`, `tests/test_public_player_zoom.py`, `tests/test_public_player.py` already `SCOPE+`),
**+283/−46**. Orchestrator-verified: `touch-action` untouched (0 lines of diff), nothing under `meta/`
on the branch, `play.html` and `player.css` unchanged. Impact-scoped **467 passed / 0 failed / 0 skipped**,
`DATABASE_URL` unset. **No full suite — the merge gate still owes it.** The round assembled into
`build/site-fix` and never touched `build/site` (the owner's play-test copy, verified still the PRE-fix
build: 0 resize listeners). `build/site-fix`'s `play.js` and `player.css` are SHA-identical to the branch.

[Fix round] **F-1: a `resize` listener, with a rotating test.** `window.addEventListener("resize",
keepCluesInView)`. It bound `resize` **only**, not `orientationchange`, with a reason worth keeping:
`orientationchange` can fire before the new dimensions are laid out, and a rotation always resizes. No
debounce, since no need could be shown. The probe reproduced the defect first (rows False/cols True before
rotating; True/False after) and the fix reproduces it too.

[Fix round] **⚠ THE 175% RUNG: decided a DEFECT and fixed, with a DERIVED rule — and the derivation is
sound.** `CELLS_BESIDE = 2`: a window of width `w` over cells of pitch `c` holds a whole cell at every
scroll offset exactly when `w >= 2c`, so a pinned gutter now needs room for two cells. **Orchestrator
verified by sweeping every integer width from 1 to 149 at pitch 50 over 4000 scroll offsets: the claim
"min whole cells >= 1 iff w >= 2c" holds for all of them** (w=99 gives 0, w=100 gives 1, w=150 gives 2).
Measured effect at 390 px: row gutter pinned through 150% (101 px beside a 257 px gutter, 43 px cell),
lets go at 175%; at 844×390 the column gutter lets go from 125%.
**The residue is declared and it is what a thumb will feel:** an unpinned gutter scrolls off the left
edge, so from 175% on a phone the **row clues are out of view until the player scrolls back.** That is
the trade for never leaving zero reachable cells, and it is the same question as the admin's full
`STICK_MAX_SHARE` rule, which this page deliberately still does not take — the owner's call.

[Fix round] **F-2 and the plants.** Gutter sweep now runs at 390×844 **and** 844×390 with a **two-axis**
non-vacuity check (each axis must have a rung where it holds and one where it lets go). **E4 — `.width`
where `.height` belongs — which survived all 18 before, now reds three tests.** Table of plants, each by
text with the count asserted `== 1`, SHA-256 both ends, restored from captured content, matched control
21/21 first, `0 skipped`: remove the `resize` listener (rotation test + the EC-050 census); `resize` bound
to an empty handler (same two); E4 (sweep, reach sweep, rotation); `CELLS_BESIDE = 1` (sweep, reach
sweep); column predicate without the factor of 2 (sweep, reach sweep); predicate reading
`stage.clientHeight` again (sweep, reach sweep). **Every fix has a plant that reds it.**

[Fix round] **F-3, F-4 re-derived by the round, not copied.** Stage client width **358**; row gutter
**173/215/257/299/341** at 100/125/150/175/200%; cell **29/36/43/50/57** — matching the reviewer. The
1440 px half holds at all nine rungs. **F-4: 708/943/844 reproduced exactly** (stage top 233,
`clientHeight` 708, bottom 943, inner height 844). The column predicate now reads the on-screen height
with the page at its top, written as a comparison rather than `Math.min` because
`test_play_js_spells_no_bound_step_or_clamp_of_its_own` forbids `Math.min` in `play.js` — **a guard
the round found by tripping it and kept intact**, which is the right response. Declared
**conservative once the page itself is scrolled down.**

[Fix round] **Census extension, honestly described.** The listener test reads the
`window.addEventListener("<type>", handler)` pairs out of `play.js`, requires exactly
`[("resize", "keepCluesInView")]`, and adds the derived types to the expected census. A second `window`
listener or a different handler still reds. **It is a pinned (type, handler) pair, so only partly
derived, and not a control — and the comment says so.**

[Fix round] **F-5 resolved the cheap way, and NOT verified.** The round kept the restore and called it
defensive in the docstring, saying no seed is known where the coupling bites. **It did not re-run the
reviewer's S1 plant**, so the reviewer's measurement (removing the loop leaves both tests green) is the
only evidence either way. Low risk, since the reason is no longer claimed — but it is an assertion of
absence rather than a measurement.

[Fix round] **A baseline of MINE did not reproduce, and the cause is my omission.** I briefed the round
to reproduce "523 passed / 0 skipped" over a file list; it measured **464** at `d21d7757`. The
reviewer's 523 selection included `tests/test_book_player_domain.py` (**59** tests; `464 + 59 = 523`) and
**my brief dropped it.** The round's 464 → 467 is its own three new tests. The correct selection to
quote is the brief's list **plus `test_book_player_domain.py`**, which is **526** after this round.

[Fix round] **A claim of the round's I think is wrong, left for cycle 2 to measure rather than
asserted.** It says that at 844×390 the toolbar wrapping to two rows, leaving about one board row on
screen, "is the existing layout". From render 12's pixel geometry the first toolbar row ends at about
726 css px of 844, leaving about 102 px free against a zoom group needing about 143 px — so **the wrap
looks caused by the zoom group this card added**, costing board height in a 390 px-tall viewport. **Not
measured by the orchestrator; read off an image.** Cycle 2 is asked to compare the toolbar height at
844 px between main's player (no zoom) and `build/site-fix`.

[Fix round] **Wording corrected, not a defect:** the reviewer's "E4 lets the column gutter go from 175%
at 844×390" was true of the OLD one-cell rule; under the new rule and visible height it is **125%**.
Renders **10–12** added beside 01–09 in `~/Documents/nonogram-reviews/CARD-324/`; orchestrator viewed 10 and
12. **ADR-0041/R2 re-derived by the round:** 0 `setAttribute("data-state"` under `player/`, `dataset.state`
writes still exactly 3, the new code reading viewport and scroll geometry only.

[Review 1/3] Score: **7.5 — CHANGES REQUESTED** (threshold 8.0). Artefact
`meta/review/CARD-324-cycle1.yml`, uncommitted. Six items for cycle 2; the load-bearing two are F-1
and F-2.

[Review 1/3] **Both render-found defects now have controls that can fail — proven by planting each
defect BACK, not by reading.** The flat `min-width` plant is caught by a test taking two readings a
flat floor breaks differently: the computed content width against the module's own step ratio, **and
`min(cell_boxes) > max(before_boxes)`** — a strict inequality over every cell, which is the defect
exactly as the owner would see it ("a wider gutter and no bigger cells"). The pinned-gutter plants are
caught two ways, and the second test is a real control rather than a mirror: it puts the class back
**by hand** at `ZOOM_MAX` and counts cells clearing the gutter, measuring the **consequence**. An edge
plant weakening the threshold to `>= 0` was also caught, so the predicate test is a genuine second
spelling and not a tautology.

[Review 1/3] **F-1 (high) — a THIRD instance of the same family, live and untested, and the round's
"pre-existing" framing is REFUTED.** Zoom to 250% on 390×844, then rotate to 844×390 with no further
interaction: the pinned classes stay `rows=false / cols=true` while the geometry wants
`rows=true / cols=false` — **both wrong, in both directions** — and cells fully inside the unoccluded
band = **0**. One press of either zoom button recovers it to 10.
**Why the framing matters:** the round called this *"a pre-existing shape, named rather than left
silent."* It is not pre-existing. **Before this card there was no zoom and both gutters pinned
unconditionally**, and at 100% in landscape the geometry still affords them. `keepCluesInView` and the
conditional pinning are **this card's own new mechanism**, so staleness across a resize is its
**residue**. Naming is the right disposition for an inherited shape; this one needed a fix or an
explicitly tested refusal. Not charged critical only because one visible, labelled button recovers it.

[Review 1/3] **F-2 (medium) — the `keeps-cols` arm has no control that can fail, and an edge mutant
proved it.** E4 (`colClue.getBoundingClientRect().width` where it must read `.height`) left **all 18
green**: at 390×844 `keepsCols` is `True` at every rung, so the assertion is `True == True`
throughout, and the class's own non-vacuity guard reads the **row** list only. Reach measured — at
844×390 the col gutter legitimately lets go from 175% up and E4 keeps it pinned at every rung, **the
vertical twin of the defect the renders found**, landing in exactly F-1's geometry. One landscape rung
plus a two-axis non-vacuity assertion closes both.

[Review 1/3] **F-3 (medium) — the declared bound's measured residue is WRONG IN BOTH PLACES IT IS
WRITTEN** (card notes and the test module's docstring): *"the row gutter lets go at 250%"* measures as
**200%**. Measured three times over the module's own harness — stage client width 358, row gutter
173/215/257/299/341 at 100/125/150/175/200, cell 29/36/43/50/57. The 1440 px half holds (nothing lets
go at any of nine rungs). **And the unstated residue is the part the owner will meet:** at **175%** the
rule is satisfied by 60 px of band beside a 299 px gutter with a 50 px cell — one column — and at the
scroll the zoom itself lands on, **zero cells are fully visible**. The seven original renders step
100 → 150 → max, so **that rung was never seen.** The reviewer rendered it:
`08-review-cycle1-390px-175-percent-one-column.png` and `09-…-200-percent-…`.

[Review 1/3] Lower findings: **F-4** `stage.clientHeight` (708) overstates the visible band — the stage
bottom sits at 943 against an 844 inner height, ~98 px below the fold, and the col predicate reads
that same height. **F-5** the `SCOPE+` restore's *stated reason* does not reproduce — a plant removing
the restore loop entirely left both tests green; **keep the restore, retitle the reason.** **F-6** is
the orchestrator's: the card body's "What to implement" item 1 still instructed the refuted
seven-name import, corrected above.

[Review 1/3] **Everything the orchestrator asked to be adjudicated came back verified.** The derived
import set is **real and stronger than a list** — it fails on drift from either side — with one caveat
said aloud: it is an equality against *another page's* consumed surface, so an admin-only change reds
it as a declaration rather than a bug. **M7 re-fired and is caught by name**, and the reviewer checked
that `_tap` being a mouse click does not weaken it (`if (gesture) return` sits after the touch/pen
branch, so a stale gesture blocks mouse and touch alike); it then found a **second** instance of that
shape already controlled, and identified **F-1 as the third and uncontrolled one**. **M5 verified
behavioural** (300 never appears in `play.js` either way), as is **E3** (the two `anchoredScroll` axes
swapped), so AC-4 is not a reading of whatever happened. The `SCOPE+` derivation is real with no
hidden coupling. **ADR-0041/R2 re-derived in full and holds** — 0 `setAttribute("data-state"`, exactly
3 `dataset.state` writes all accounted (the third a *swatch*, not a cell), the signature control fires,
and the live payload keys are still exactly `columns/height/key/rows/tier/width`.

[Review 1/3] **The full suite was started and STOPPED BY MEASUREMENT rather than abandoned or pushed
through**, which is the right call and a finding in itself: at ~1.5% of **10424** collected tests in
three minutes it projected **2–3 hours** and would have held the host against CARD-358's concurrent
review for all of it. The reviewer's `EXIT` trap did not fire (shell killed), so it read the lock
back, confirmed holder **and** worktree were its own, removed it and confirmed absence with `find` —
correct recovery, and the same hazard CARD-377's residue 2 names. **CARD-358 took the lock four
minutes later and the reviewer did not touch it.** In place of the suite it ran a selection **~3×
broader** than the round's: **523 passed / 0 failed / 0 skipped** in 59.8 s. `db_required` derived at
**29 of 10424**; none in scope, which is why 0 skipped rather than a fraction of 30. **The full suite
is still owed before merge.**

[Round, commit `d21d7757`] Implemented: five files, +1788. INV-023 clean. Impact-scoped selection
**180 passed / 0 skipped** against a 162-passed baseline. **No full suite** — CARD-358 held the lock
for most of the session and the round **waited rather than overriding**, with neither override env
var touched. **The full suite is still owed before merge.**

[Round] **TWO FIGURES OF THE ORCHESTRATOR'S BRIEF REFUTED, both re-verified independently**
(ADR-0039/R4):
• **"import the seven names" is wrong — the admin's own glue imports FIVE.** Measured:
  `solver.js` imports `{ZOOM_MAX, ZOOM_MIN, anchoredScroll, pinchZoom, stepZoom}`, and `clampZoom`
  occurs **0** times in it (3 times inside `solver_state.js` only). `stepZoom` and `pinchZoom` clamp
  their own returns, and `solver.js`'s `applyZoom` says in as many words that it does not clamp.
  Importing seven would have planted **two unused names**. The round imported the same five **and
  made the test derive that set from `solver.js`'s imports** rather than listing it, so the two
  pages' consumed surface cannot drift — better than either the card's reading or mine.
• **"`admin.css` has 23 zoom rules" was a LINE count, not a rule count.** 23 lines match `zoom`
  case-insensitively; the overwhelming majority are comment prose. The rules zoom actually needs are
  **seven**: six taken, two of those modified, one refused.

[Round] **The one refusal, with its reason — and it is the right call.** `admin.css`'s
`.player-zoom .btn { padding-left/right: 5px }` is a **desktop** constraint that keeps
"Progress: N%" on the panel's counters row at 1280 px. This toolbar has no counters and every visit
is a thumb, so the round used `min-width: 44px; justify-content: center` instead. A rule copied for
provenance rather than for its reason would have been the easy wrong answer.

[Round] **⚠ THE RENDERS FOUND TWO DEFECTS THAT SIX GREEN ACs DID NOT.** This is the strongest
evidence yet for the owner's standing rule that image and UI work is validated **by eye**:
1. **`.player-cell`'s `min-width` was a flat 28 px** (`--player-cell-min`), equivalent to the admin's
   `min-width: var(--player-cell)` only while nothing multiplied the cell. With `table-layout: fixed`
   Chromium sizes a column to the largest min-width in it and **ignores the specified width** —
   measured at 125%: `--player-cell` resolved to 35 px, the clue band's numerals grew, **and every
   cell stayed 28 px.** A wider gutter and no bigger cells. **Every AC was green.**
2. **At 300% on a 390 px screen the sticky row gutter was wider than the whole stage** — pinned, it
   covered every column and **no cell was reachable at all.** Every AC was green through this too.
   `keepCluesInView` now pins a gutter only while the stage still has room beside it for a whole
   cell, **derived — no share, no constant.** Measured: at 390 px both gutters pin at 100/150/200%
   and the row gutter lets go at 250%; at 1440 px nothing lets go at any rung.
   **⚠ RETRACTED (ADR-0039/R4): "lets go at 250%" is WRONG — cycle 1 measured 200%.** Stage
   client width 358; row gutter 173/215/257/299/341 at 100/125/150/175/200; cell 29/36/43/50/57.
   The 1440 px half holds. **The unstated residue is the part that matters to a player:** at
   **175%** the rule is met by 60 px of band beside a 299 px gutter with a 50 px cell — one
   column — and at the scroll the zoom itself lands on, zero cells are fully visible. The
   round's original renders step 100 → 150 → max and never showed that rung; cycle 1's renders
   08 and 09 do. Quoted figure kept above so the correction is legible, not silent.

[Round] **Nine mutants, and the one that SURVIVED is the instructive one.** M7 — dropping
`gesture = null` from `beginPinch` — left **all 180 green**, because a stale `gesture` leaks no mark:
the pinch's own `releaseTouch` swallows both pointers, so it blocks the **next** `pointerdown` and
the board simply cannot be marked again until a reload. Both AC-5 arms now **tap after the pinch**;
re-run, M7 is caught by name. The orchestrator's named edge mutant (**M2**, a local `clampZoom` with
identical behaviour) was caught, and the round added **M3**, the sharper form — a local step with the
import **left in place**, so `stepZoom` is imported and never called and the answers are identical —
also caught. **M5** (`>` for `>=`) is invisible to every source-text guard and was caught
**behaviourally**.

[Round] **ADR-0041/R2 derived rather than quoted:** `setAttribute("data-state"` → **0** in every file
under `player/`. The three `data-state` writes are all in `play.js` and all accounted — the blank
board's module constant, `paint()`'s displayed board, and the player's own brush. What the zoom adds
writes is two `aria-disabled`, one `textContent` percent, one `--player-zoom` number and two scroll
offsets; its inputs are bounds, button presses, pointer coordinates and scroll position. **Held by
signature in the test**, with a control that plants a `board` parameter and sees it.

[Round] **The build was regenerated and the stale artefact is gone.** `build/` did not exist in the
fresh worktree; the "1163 lines, 204 behind" figure was re-derived in the **main** repo. After
running the documented driver the served copy is **1367 lines and `diff -q` clean** against the
admin's, re-assembled after every code change including the last.

[Round] **`tests/test_public_player.py` declared `SCOPE+`.** Adding the zoom group red
`test_every_player_control_is_in_the_ec_050_walk`, which is exactly what that guard is for. Extended
by **deriving a third set** (`data-player-zoom-action`) rather than adding two names to a list, and
the walk **restores** the zoom after each press with the reason stated: zoom changes every cell's
size, and a walk that left it raised would move the board out from under `drag_a_line`'s mouse drag
and fail for a reason that is not EC-050's.

[Round] **Renders at `~/Documents/nonogram-reviews/CARD-324/`** — seven PNGs of a marked 30-cell board
at 390 px unless noted: 100% (cell 29 px, "−" greyed), 150% (43 px), zoom-max (85 px, **column clues
above and reachable cells below** — before the gutter fix this same shot showed only clue band),
panned at 300%, back to 100%, the control group alone, and 1440 px at 150%.

[Round] **Three findings routed up, not absorbed** — see the card's decision block below for the
`touch-action` one, which is the owner's. The other two: taking the admin's full `STICK_MAX_SHARE`
affordance rule would unpin this page's row gutter at **100%** on a 390 px screen, contradicting
`player.css`'s promise and a guarded test, so CARD-271's full feature is a card rather than a
worktree call; and `keepCluesInView` runs at start and on every zoom but **not on resize**, so a
rotation at high zoom can leave a gutter pinned that no longer affords — pre-existing shape, named
rather than left silent.

[Round] **A process note that confirms a memory entry rather than adding one:** the round's own
`pgrep -f "m pytest"` wait-loop **matched its own argv** and reported "CARD-358 pytest is gone" while
CARD-358 was alive; `lsof -d cwd` showed two live processes in that worktree. Same family as the
orchestrator's own instance the same night — **the candidate set must not come from argv either.**

- **[Serialization, not dependency]** This card and CARD-323, CARD-325,
  CARD-326, CARD-327 all touch `player/play.js`, `play.html` and `player.css`,
  so their overlap is **1.0** and the conflict graph serializes any two in one
  wave. Deliberately not a `Depends on` edge — none needs another's output, and
  a sequencing preference written as a dependency pollutes the graph the
  dispatcher reasons over (the board's rule, stated on CARD-220's `Wave:`).
- **[The pinch/drag collision is the real work]** Items 1-3 are wiring. Item 4
  is a genuine interaction decision — the admin player answered it for its own
  stage and `gesturePaints` is the module's half of that answer, but the public
  page's pointer handling is its own code. Decide it explicitly and record the
  decision here; do not let it fall out of whichever listener fires first.
