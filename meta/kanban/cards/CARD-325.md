# CARD-325: The public player gains the crosshair — the one admin control that reads no board at all

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
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_crosshair.py
**Review score:** —
**Started:** —
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
  a test in the test tree reads each and asserts they make the same decision on
  the four cases of item 1 — the control that makes this card's deliberate
  duplication detectable if one side drifts. (test:
  `TestPublicCrosshair_TheTwoImplementationsAgree`)

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
