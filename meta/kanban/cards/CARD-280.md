# CARD-280: The solved board stops being a worksheet and becomes the picture

**Status:** ready
**Priority:** P3
**Category:** feature
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/280-solved-reveal-the-picture
**Worktree:** —
**Source:** Owner's request 2026-10-23: *"I'd like to make an animation after the user solves the puzzle in player more festive. What would you propose?"* — then "make a card for it". The proposal below is the orchestrator's, built after reading what the player already does on solve rather than from a blank page, which is what moved it away from the obvious answer (see **Why**).
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_solved_reveal.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — the celebration currently congratulates the grid, not the picture

**What already happens on solve**, read from the code rather than described from memory: the filled cells
flash `--color-success` in a diagonal sweep (`--player-wave = row + col`, 12 ms a step, about a second —
`solver.js:559`, `admin.css:884`), a success-coloured outline draws just inside the board
(`admin.css:870`), `.player-toolbar.is-solved .player-tools` hides the tools (`:861`), the banner
`#puzzle-player-solved` fades in carrying the picture's name (`:863`, `player-solved-in` at `:881`), a
live region announces, and the board locks. `prefers-reduced-motion` already has a **complete** static
path (`:887-889`). So this card is not adding the player's first animation. It is fixing what the
existing one celebrates.

**The payoff of a nonogram is the picture, and at the moment of victory the board still wears every
piece of scaffolding the player used to find it:** ink cells, *plus* the thin per-cell rules
(`admin.css:589`'s inset hairline, CARD-270), *plus* the heavy fifth rules, *plus* a grey dot on every
single empty cell (`:590` — a 28% circle, not an X), *plus* one or two clue gutters per axis. The thing
somebody worked twenty minutes to uncover is on screen behind a worksheet.

And the sweep compounds it: `row + col` is a diagonal across the **whole board including the empties**,
so what visibly animates is the grid's geometry. The picture is incidental to its own celebration.

## What to implement — three layers, in this order, and the first is the one that matters

### 1. Strip the worksheet (the card's core; ship this even if 2 and 3 are dropped)

On the transition into solved, take the chrome away and leave pure ink on paper for a beat: the per-cell
hairline, the fifth rules, the outer frame's worksheet weight, the empty-cell dots and the clue gutters
fade out, so what remains is the shape the clues were describing all along. Then restore the chrome —
or leave it off behind a small, persistent **"Show grid"** toggle, which is the better answer if the
owner wants to look at the picture rather than watch it for two seconds. **State which you shipped and
why.**

No new assets and no new mechanism: every element involved already exists and is already addressable
from `.player-board.is-solved`. The success outline at `:870` should **stay** — it is the frame around
a finished print, and it is the one piece of chrome that reads as celebration rather than as scaffolding.

### 2. Make the sweep follow the picture, not the geometry

Replace `--player-wave = row + col` with a **breadth-first distance through the filled region**, seeded
at the filled cell nearest the board's top-left, so the shape lights up *along itself* and a disconnected
part (an eye, a detached limb) lights in its own time rather than when the diagonal happens to cross it.

**This is a pure function of the board and belongs in `solver_state.js`** — ADR-0038/R4 keeps state logic
out of rendering, and `solver.js` must do nothing with the result but set the custom property, exactly as
it does today at `:559`. Undecided and empty cells take no part; a cell the wave never reaches (there are
none on a solved board, by construction, but the function must say what it returns anyway) needs a
defined value, not an implicit `undefined` reaching CSS `calc()`.

The CSS at `:884` does not change. One number changes meaning.

### 3. Let the words earn it

The page already tracks `errorCount` and `hintCount` (`solver.js:683-695`). A solve with neither deserves
different words from a solve that took four hints — *"Solved with no errors and no hints"* is more festive
than a generic banner **because it is specific and true**, and a hinted solve gets honest, warmer wording
rather than the same sentence. Recognition, not decoration, and it costs almost nothing.

Keep the picture's name in the banner; it is the best thing already there.

## The constraint that will break a naive implementation — measured, not predicted

**`.is-solved` is re-applied on paths that are not a solve, and a CSS animation restarts every time its
class is added.** `showProgress` toggles the class on every call (`solver.js:702-703`), and it is called
from three places. Read off the code:

| path | what happens today |
|---|---|
| **page load of a saved solved board** (`showProgress(null)` at `:760`, after the draw) | `.is-solved` is applied to a freshly built table → **the celebration replays** |
| **a redraw** — `mirrorQuery` crossing 820 px, or a zoom change, rebuilding the table (CARD-193/CARD-195/CARD-212) | same path, same call → **replays again, on a window resize** |
| **redo back into solved** after an undo un-solved it | class removed then re-added → **replays** |

For today's one-second colour flash that is tolerable and nobody filed it. **For this card it is not:** a
grid that vanishes and returns every time the window crosses a breakpoint is worse than no reveal at all.

**So the card must split the STATE from the TRANSITION**, and this is the design decision it exists to
get right:

- **the state** (the picture shown without its worksheet) follows `.is-solved`, so a reloaded solved
  board still shows the picture — that is information about the board and it should survive a redraw;
- **the transition** (the sweep, the fade-out of the chrome) fires only on a **genuine** solve, which
  needs a marker the redraw path does not re-add. A one-shot class added where `now !== solved` is
  already computed (`:698`) and removed on animation end is the cheapest honest shape; **whatever is
  chosen must be stated and must be held by a test that redraws a solved board and asserts the
  transition did not re-run.**

A reload of an already-solved puzzle should **not** replay the celebration. That is a decision, so it is
written here rather than discovered: the player is being reopened, not won.

## Acceptance criteria

- **AC-1** *Given* a board that becomes solved, *then* the worksheet chrome named in step 1 is no longer
  visible on the board while the solved state holds, and the success frame **is** still visible.
  (test: `TestSolvedReveal_TheChromeGoesAndTheFrameStays`)
- **AC-2** *Given* a solved board, *then* every filled cell is still exactly the picture's shape — the
  reveal removes chrome and **moves no cell**: the filled set and each cell's position and extent are
  unchanged from before the solve, compared against the pre-solve rendering rather than asserted.
  (test: `TestSolvedReveal_TheRevealMovesNoCell`)
- **AC-3** *Given* a solved board that is then **redrawn** (a breakpoint crossing and a zoom change),
  *then* the picture state persists and the **transition does not re-run** — demonstrated in both
  directions: it runs on the genuine solve, and it does not run on the redraw.
  (test: `TestSolvedReveal_ARedrawDoesNotReplayTheCelebration`)
- **AC-4** *Given* a page load of a **saved** solved board, *then* the picture state is present and the
  transition does not run. (test: `TestSolvedReveal_AReloadDoesNotReplayTheCelebration`)
- **AC-5** *Given* an undo that un-solves and a redo that re-solves, *then* the chrome returns on the
  undo and the picture state returns on the redo, and the card states whether the transition re-runs on
  the redo — **either answer is acceptable, an undeclared one is not**.
  (test: `TestSolvedReveal_UndoRestoresTheWorksheet`)
- **AC-6** *Given* `prefers-reduced-motion: reduce`, *then* the full **reveal** is present — the picture
  without its worksheet, the frame, the banner, the earned wording — with **no** animation or transition
  anywhere in the player, extending the existing block at `admin.css:887-889` rather than adding a second
  one. The reduced-motion path must not be a degraded reveal; only the motion is dropped.
  (test: `TestSolvedReveal_ReducedMotionKeepsTheRevealAndDropsTheMotion`)
- **AC-7** *Given* the wave values for a solved board, *then* they are produced by a **pure function in
  `solver_state.js`** of the board alone, every filled cell has a defined finite value, and a board whose
  picture is in two disconnected parts gives each part its own run of values — asserted on the function,
  not on pixels. (test: `TestSolvedReveal_TheWaveIsAPureFunctionOfTheFilledRegion`)
- **AC-8** *Given* a solve with no errors and no hints and a solve with hints, *then* the banner's words
  differ and each is true of its own solve — the counts are read from the live state, never restated.
  (test: `TestSolvedReveal_TheWordsMatchTheSolve`)

## Guardrails

- G-1: **`CELL_STATES` is unchanged** (`solver_state.js:31`). This card adds no cell state; "revealed"
  is a property of the board, not of a cell. CARD-268's probe mode holds the same line.
- G-2: **Nothing about the fit ladder, the breakpoint or the zoom changes.** CARD-193 owns the
  breakpoint rule, CARD-195 the zoom, CARD-212 the measured gutter ladder — and `drawSettledLayout`'s
  draw counts are pinned by draw marks (`TestSolverClues_TheLadderStopsAtTheFirstRungThatFits`). **Do not
  animate geometry**: CARD-277 is an open flake in drag handling at 200 % zoom, and a decorative change
  that moves layout is how a delight feature becomes a correctness bug.
- G-3: **`solver_state.js` stays pure and rendering-free** (ADR-0038/R4) — no DOM, no CSS, no timing in
  it. The wave function takes a board and returns numbers.
- G-4: **No new dependency and no build step.** Hand-written JS and CSS only (ADR-0038/R1); the
  dependency baseline is closed (ADR-0006/R1). No confetti library, no canvas particle system, no sound.
  A celebration that needs a dependency is out of this project's scope by two separate rules.
- G-5: **No network request** on solve or on any mark (ADR-0038/R2), and play state stays browser-local
  (CON-021). A "first solve ever" flourish would need server state and is **not** in this card.
- G-6: **The reduced-motion block is extended, never bypassed.** No `!important` escape, no second media
  block that re-enables motion.
- G-7: ADR-0036/R4 — no codepoint in U+25A0..U+25FF, U+2022 or U+2219 in any `src/nonogram/**` string
  literal. A "festive" change is exactly where a stray ★ or • gets typed; **verify rather than assume**.
- G-8: Browser tests fail or skip **loudly** with a named reason, never silently (ADR-0038/R8). An
  animation is not an excuse for a test that cannot fail — a timing-based assertion that passes because
  it waited long enough is the shape to avoid; assert on classes, computed styles and the wave values.
- G-9: Take no timing measurements and report no durations — other work may share the machine. Animation
  *durations in CSS* are declared values, not measurements, and are fine.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark (check: `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: review-lens)
- ADR-0038/R8 — browser tests fail or skip loudly with a named reason (check: review-lens)
- ADR-0036/R4 — no dingbat codepoints in `src/nonogram/**` string literals (check: review-lens)
- CON-021 — interactive play only in the admin panel's player; play state browser-local (check: review-lens)

## Architecture context

- **FR:** FR-044 (the player). The solved banner, lock and announce are AC-303/AC-304-era behaviour; the
  progress percent is CARD-187's, the clue circles CARD-188's.
- **ADR:** ADR-0038/R1, R2, R4, R8; ADR-0036/R4; ADR-0006/R1.
- **Components:** COMP-009 (admin panel: static JS/CSS).
- **Trace:** `meta/architecture/trace.yml` — a new AC may be owed if the owner wants the reveal in the
  registry; this card does not add one on its own authority.

## Design context

- **Screens:** the admin player (`/puzzle/<id>/play`-class route).
- **Standards:** tokens-only styling. The reveal must use existing tokens — `--color-success`,
  `--grid-ink`, `--grid-paper`, `--player-thin`, `--duration-base`, `--ease` — and the budget for new
  tokens is **zero unless a measurement says otherwise**, the standard CARD-270 met by spending none.

## Worktree notes

- **[Read the existing solved path before designing anything]** `solver.js:683-705` (`showProgress`),
  `:559` (the per-cell `--player-wave`), `:760` and `:784` (its two callers), and `admin.css:861-889`
  (the whole solved block including the reduced-motion escape). The card's central constraint comes from
  those line numbers and they will move — **locate them by text, not by line**, the lesson CARD-264 paid
  for twice.
- **[The re-fire is already live today, at a tolerable size]** Resizing the window across 820 px on a
  solved board replays the colour flash right now. That is worth knowing because it means the split
  between state and transition **fixes an existing wart** rather than only avoiding a new one — and it is
  a free, honest line for the card's own notes if a reviewer asks what the card improved beyond polish.
- **[Why BFS and not a distance transform]** The wave wants *"how far along the shape is this cell"*,
  not *"how far from the edge"*. A geometric distance would light the middle of a thick stroke last; a
  BFS along filled neighbours lights the shape the way a pen draws it. 4-neighbour or 8-neighbour is a
  choice with a visible difference on diagonal strokes — **pick one and say which**.
- **[The owner's own words on what festive means here]** The proposal the owner accepted leads with
  *the picture*, not with sparkle, and the three rejected options are recorded in the session: confetti
  or particles (two rules against it), sound, and anything that animates geometry. A reviewer should
  treat a drift back toward decoration as scope growth, not as enthusiasm.
- **[Conflict prediction]** `solver.js`, `solver_state.js` and `admin.css` are also CARD-267's
  (crosshair), CARD-268's (probe mode) and CARD-269's (hint ladder) footprint, so this card **serialises
  against all three** in the conflict graph and must not be dispatched beside them. The owner was told
  this when the card was requested and did not ask for it sooner, which is why it is **P3** while those
  three are P2 — a priority that is a queue position, not a judgement about the feature.
- **[Do not run the full suite]** Export `NONOGRAM_FULL_SUITE_LOCK` to a scratch path for every pytest so
  the board's own lock is never read, written or created. The merge gate runs the full suite.
- **[Browser-test cost]** These are pytest-playwright/Chromium tests (ADR-0038/R7, dev-only extra). The
  sibling player files are the model for the fixtures; `tests/test_puzzle_solver_zoom.py` shows how a
  redraw is forced, which AC-3 needs.
