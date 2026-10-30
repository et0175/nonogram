# CARD-324: The public player gains zoom — four shared functions it already serves and never calls

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`.
**Idea:** —
**Wave:** —
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_zoom.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

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

1. `player/play.js`: import `ZOOM_MIN`, `ZOOM_MAX`, `ZOOM_STEP`, `clampZoom`,
   `stepZoom`, `pinchZoom`, `anchoredScroll` from `/solver_state.js` and hold a
   zoom value in the page's state. **Derive nothing** — the bounds, the step and
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
