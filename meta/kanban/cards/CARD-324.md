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
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_zoom.py
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
