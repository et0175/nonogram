# CARD-323: The public player gains the Maybe brush — the fourth mark whose look already ships

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-10-30 — "the player misses a lot of the player from the admin player: e.g. no maybe brush, no hints etc... I'd like both to reuse the same functionality", raised against a locally assembled site at `http://localhost:8081/play/00d5d88065`. The orchestrator measured the gap before carding it; this is the cheapest of the five cards it produced, and the only one whose styling already exists.
**Idea:** —
**Wave:** —
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_maybe.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is this small

`MAYBE` is **already one of the four members of `CELL_STATES`** in
`solver_state.js`, which ADR-0041/R3 requires the public site to serve as a
**byte-identical copy** of the admin player's module — so the public page is
already shipping every transition the fourth mark needs. Measured 2026-10-30:
`clickedState` and `clickStroke` handle `MAYBE` with no special case, and
`player/player.css` **already carries its look**, as the one rule
`.player-cell[data-state="maybe"] { background: var(--color-surface-hover); }`
(at `:411` when this card was cut — **locate it by the selector, not by the line**:
that file gained 45 lines from an out-of-pipeline commit within half an hour of
this card being written, and a bare line number is the figure CARD-281 exists
because of).

What excludes it is **one line and one button**: `player/play.js`'s `TOOLS`
constant is `[FILLED, EMPTY, UNKNOWN]`, and its comment states the reason —
*"MAYBE ("?") is the admin player's fourth and is not offered here, so a cell
reachable from this page is one of these three (CARD-283, 'three cell states')"*.

**That is a scope decision, not a constraint.** Unlike the error count, the
progress percent and Check — which take `solution` and are therefore
unreachable from a page that by design never has the answer — the Maybe brush
needs nothing the page does not already have. The owner's 2026-10-30 decision
reverses the scope choice and leaves the three answer-dependent features out.

## What to implement

1. `player/play.js`: add `MAYBE` to the `TOOLS` array, imported from
   `/solver_state.js` alongside the three already there. **The order is the
   DOM's** (the constant's own comment says so), so place it where the button
   sits — the admin's order is filled, empty, maybe, unknown
   (`puzzle_solve.html:257-260`), and matching it is the point of the card.
2. `player/play.html`: a fourth `data-player-tool="maybe"` radio in
   `.player-tools`, built exactly like its three siblings — `role="radio"`,
   `aria-checked="false"`, and a `.player-swatch` carrying the state so the
   swatch inherits the look the stylesheet already defines.
3. `player/player.css`: **only if a swatch rule is genuinely missing.** The
   cell look exists; check whether `.player-swatch[data-state="maybe"]`
   resolves through the same rule before adding anything. **A rule that
   duplicates one already there is a finding against this card**, not a
   deliverable — the whole premise is that the look already ships.

## Acceptance criteria

- **AC-1** (the brush marks): *Given* the public player with the Maybe brush
  chosen, *when* a cell is clicked, *then* that cell carries
  `data-state="maybe"` and the recorded history holds one stroke whose state is
  the module's `MAYBE`. (test: `TestPublicMaybe_TheBrushMarksACell`)
- **AC-2** (four tools, in the admin's order): *Given* the page, *then*
  `.player-tools` holds exactly four `data-player-tool` buttons and their DOM
  order is `filled, empty, maybe, unknown` — **the same sequence as the admin
  player's menu**, asserted against that template's order rather than against a
  list spelled twice. (test: `TestPublicMaybe_FourToolsInTheAdminsOrder`)
- **AC-3** (the radio group still behaves): *Given* four tools, *then* exactly
  one carries `aria-checked="true"` at any time, and choosing Maybe unchecks
  the previous tool. (test: `TestPublicMaybe_OneToolIsCheckedAtATime`)
- **AC-4** (the look is not re-declared): *Given* the stylesheet, *then* the
  maybe cell's appearance is defined in **exactly one place** and that place is
  the rule that existed before this card — a per-rule check, not a grep for the
  word. (test: `TestPublicMaybe_TheLookIsDeclaredOnce`)
- **AC-5** (the save round-trips a maybe): *Given* a board with maybe marks,
  *when* the page is reloaded, *then* those cells come back as
  `data-state="maybe"` — the public save is `play.js`'s own, so this is the
  arm that proves the fourth state survives it. (test:
  `TestPublicMaybe_AReloadRestoresMaybeMarks`)

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`.** Both are
  byte-identical build-time copies (ADR-0041/R3); `player/assemble.py`'s
  `COPIED_FROM_ADMIN` table checks the equality at assembly time **and** from
  the test tree. An edit here is caught, but by the wrong gate and late.
- **G-2: no solution reaches the page.** `puzzle/<key>.json` carries clues and
  extent only (measured 2026-10-30: `clues`, `width`, `height`, `key`, `tier`).
  This card adds no field to it (ADR-0041/R2, CARD-283 G-4).
- **G-3: the three existing brushes are untouched** — their values, their DOM
  attributes and their tests stay as they are.
- **G-4: styling from tokens only** — `var(--color-*)`, never a literal.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).
- **G-6: do not touch `src/nonogram/admin/**`.** CARD-268 is editing the admin
  player's static files in a sibling worktree; this card's whole footprint is
  under `player/` precisely so the two cannot collide.

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or data from which any solution cell is recoverable (check: CARD-282's and CARD-283's guards)
- ADR-0041/R3 — the board-state module and the design tokens are reused by byte-identical build-time copy, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0041/R4 / CON-021 — play state persists only in this browser's localStorage, per puzzle; nothing server-side (check: review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: `TestSolverMarking_NoRequestPerMark`'s public-side equivalent)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures, imported by `tests/test_public_player.py`)

## Architecture context

- **FR:** FR-045 (the public player)
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R2, R8
- **Components:** COMP-011
- **Trace:** `meta/architecture/trace.yml` — not updated by this card (a scope reversal inside a shipped FR, like the player features before it; the owner decision goes through `inputs/raw-requirements.md` on the architect side, and the ACs above are the card-local statement the gate holds onto — quick-card rule)

## Design context

- **Design system:** `build/site/tokens.css` is the byte-identical copy of `src/nonogram/admin/static/tokens.css`; `player/player.css` is the public player's own sheet and every value in it is a token (G-4).
- **UI components:** `.player-tools` gains a fourth `.player-tool-item`; `.player-cell[data-state="maybe"]` already exists.
- **Screens:** `/play/<key>`.
- **Standards:** real buttons with accessible names, `role="radio"` + `aria-checked` as the three siblings already do; the owner validates the look on a real puzzle render before merge.

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

- **[Serialization, not dependency]** This card and CARD-324, CARD-325,
  CARD-326 and CARD-327 all touch `player/play.js`, `player/play.html` and
  `player/player.css`, so their predicted overlap is **1.0** and the
  dispatcher's conflict graph will serialize any two of them in one wave.
  That is deliberately **not** written as a `Depends on` edge: none of them
  needs another's output, and a sequencing preference written as a dependency
  pollutes the graph the dispatcher reasons over (the board's own rule, stated
  on CARD-220's `Wave:` field). Run them in any order.
- **[Smallest first]** This is the cheapest of the five and the only one whose
  styling already exists, so it is the natural first slot — it proves the
  public player's test harness and the four-tool DOM before the larger cards
  build on them.
