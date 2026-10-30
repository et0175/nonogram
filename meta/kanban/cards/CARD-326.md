# CARD-326: Circled clue numbers on the public player — the clue readout that needs no answer

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
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_circles.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
