# CARD-327: The public player gains a hint that DERIVES instead of reveals — and `play.js`'s comment saying it cannot is wrong

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-10-30 — "no maybe brush, no hints etc... I'd like both to reuse the same functionality". The orchestrator measured the hint question before carding it and found the shipped code's own account of it to be false; that measurement is this card's premise and is restated below so the implementation re-derives it rather than trusting it.
**Idea:** —
**Wave:** —
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_hint.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists: a claim in shipped code that does not hold

`player/play.js`'s header states, as one of three consequences of the page never
having the answer:

> `solver_state.js`'s `isSolved`, `errorCount`, `solvedPercent` and `hintCell`
> all take `solution` and are therefore unreachable from this page. No error
> count, no progress percent, no hints (CARD-283 G-4). **Adding any of them
> publicly needs the answer**, which is a new architecture question.

**The last sentence is false for hints, and true for the other three.** Measured
2026-10-30 against `src/nonogram/admin/static/solver_state.js`:

- `errorCount(board, solution)`, `solvedPercent(board, solution)` and
  `firstWrongRow(board, solution)` use the solution **as the comparand** —
  "how many of your marks differ from the answer" has no solution-free form.
  These stay out, by the owner's 2026-10-30 decision.
- `hintCell(board, rows, columns, solution)` touches the solution for exactly
  **two** things, and neither is the deduction:
  1. `truth(row, col)` — to spell the state it returns, and
  2. `knownLine(board, solution, axis, index)` — to read the player's **wrong**
     marks as `UNKNOWN` before deducing.
- The deduction itself is **`lineForced(clue, cells)`**, which takes **no
  solution at all**: a forward/backward reachability table over
  (position, runs placed), natively reimplementing
  `nonogram.solver.propagate.line_intersection`. For a cell `hintCell` returns
  with `deduced: true`, `lineForced` **has already computed that cell's state** —
  `truth()` only re-spells what the clues decided.
- Rungs 1 and 2 are solution-free throughout: `nextRung(rung, event)`,
  `HINT_RUNGS`, `RUNG_POINT`/`RUNG_EXPLAIN`/`RUNG_REVEAL`, `HINT_REASONS` and
  `hintReason(clue, cells, at)`. So is `hintCount(history)`, and so is
  `hintStroke(row, col, state)`.

**So a hint that derives the cell from the clues is available to this page
today, with no solution in any asset.** That is what this card ships.

### What is NOT available, stated before any code is written

1. **The fallback rung.** `hintCell` falls back to revealing an arbitrary
   undecided cell when no line forces one (`deduced: false`). That branch reads
   the answer and has no solution-free form. **The public player's exhausted
   state is rungs 1-2's existing sentence** — CARD-269 already designed and
   shipped it as case (b) in `hintLine`'s comment: *"there is no line to look
   at, so rungs 1 and 2 point at NOTHING and say so, instead of handing over a
   cell while claiming a line deduction was missed."* Reuse that semantics; do
   not invent a public-only fallback.
2. **Wrong-mark discarding.** `knownLine` exists so a hint deduces from the
   player's *correct* marks only. Without the answer this page cannot tell a
   wrong mark from a right one, so it must deduce from **the board as the player
   has it**. The consequence is real and is item 3 of "What to implement":
   a wrong mark can make `lineForced` return `null` for that line.

### The interpretation this card relies on, declared rather than assumed

ADR-0041/R2 forbids a public asset from carrying "a solution grid or data from
which any solution cell is recoverable, for any puzzle, on any export path".
A derived hint **adds no data to any asset** — `puzzle/<key>.json` is unchanged,
and the computation runs in the player's browser over clues it already has.
Note also that CON-005 / INV-002 make every published puzzle **uniquely
solvable**, so the published clues already determine every solution cell; the
public player's own `isClueSolved` already rests on exactly that fact.

**This card therefore reads R2 as a rule about what an asset carries, not about
what a browser can compute from it.** That reading is declared here so the
reviewer checks it rather than discovering it — and this board has met the same
over-literal-reading problem before: `player/assemble.py`'s own docstring
records that EC-048's literal text "is not satisfiable by any implementation of
ADR-0041 at all". **If the reviewer or the owner disagrees with this reading,
that is an escalation to the architect station, not a thing to settle in the
worktree.** AC-6 is the mechanical half of the claim.

## What to implement

1. **Correct the false comment, with the test that makes the correction true.**
   `play.js`'s header must say what actually holds: the error count, the
   progress percent and Check need the answer; the hint does not, and why. A
   claim may be changed only together with the test that proves the new one
   (this board's first rule) — AC-1 and AC-6 are those tests.
2. **A native `hintCell` equivalent** in `play.js`: run `lineForced` over each
   row and column clue against the board as the player has it, and return the
   first undecided cell some line forces, **with the state `lineForced` gives
   it** — never a state read from anywhere else, because there is nowhere else.
   Reimplemented natively rather than imported around, which is the precedent
   CLAUDE.md names for exactly this situation (`solver/propagate.py`'s
   `mask_runs`), and **cross-checked against `solver_state.js`'s own functions
   from the test tree, where the import is legal**.
3. **Decide and declare the contradicting-line case.** `lineForced` returns
   `null` when no placement fits — on this page that means the player's own
   marks contradict that line's clue. Choose one behaviour and test it:
   skip that line and deduce from the others, or surface it. **Surfacing it is
   a feature, not a bug fix** — "this line cannot be right" is solution-free and
   is the nearest honest thing to the error count the owner is not getting. If
   it is surfaced, it is its own AC; if it is skipped, say why in one line.
4. **Reuse the ladder, do not rebuild it.** `nextRung`, `HINT_RUNGS`,
   `hintReason`, `hintCount` and `hintStroke` are imported from
   `/solver_state.js`. Rung 3's stroke is `hintStroke`, so a hint is one undo
   step and `hintCount` reads it off the undo stack exactly as the admin's does.
5. **The names.** The admin player records a naming trap at
   `puzzle_solve.html:134-135`: *"The counter's names are `.player-hints` /
   `data-player-hints`: `player-hint` is the usage paragraph below the board."*
   `player/play.html:91` **already uses `.player-hint` for its own usage
   paragraph**. Follow the admin's split; do not overload the singular.

## Acceptance criteria

- **AC-1** (rung 3 derives the cell): *Given* a board where a line forces an
  undecided cell, *when* Hint is pressed to rung 3, *then* that cell is marked
  with the state **`lineForced` returns for it**, recorded as a hint stroke, and
  the hint count rises by one. The expected cell and state are taken from
  `lineForced` in the test, never from a fixture's solution. (test:
  `TestPublicHint_RungThreeDerivesTheCell`)
- **AC-2** (rungs 1 and 2 point and explain): *Given* the same board, *then*
  rung 1 highlights the line the deduction comes from and says so, and rung 2
  adds the reason from `hintReason` — one of `HINT_REASONS`, read from the
  module. (test: `TestPublicHint_RungsOneAndTwoPointAndExplain`)
- **AC-3** (the ladder climbs and resets as the module says): *Given* repeated
  presses and board changes, *then* the rung follows `nextRung` for the
  `RUNG_EVENTS` that occur — asserted against the module's return value, not
  against a sequence spelled into the test. (test:
  `TestPublicHint_TheLadderIsTheModules`)
- **AC-4** (the exhausted state says so): *Given* a board no line forces a cell
  on, *then* the page says the clues decide nothing more by themselves and
  **reveals no cell** — the public player has no fallback rung, and this AC is
  what proves it did not grow one. (test:
  `TestPublicHint_ExhaustedRevealsNothing`)
- **AC-5** (a hint is one undo step): *Given* a hint at rung 3, *when* undo is
  pressed, *then* the hinted cell returns to undecided and the hint count falls
  by one; redo restores both — `hintCount` read from the module. (test:
  `TestPublicHint_AHintIsOneUndoStep`)
- **AC-6** (no answer anywhere, and the asset is unchanged): *Given* the built
  site, *then* `puzzle/<key>.json` carries exactly the fields it carried before
  this card (measured 2026-10-30: `clues`, `width`, `height`, `key`, `tier`),
  the page holds no solution grid in any variable, and the only request it
  issues is the GET of its own puzzle file. **This is the mechanical half of the
  R2 reading declared above.** (test: `TestPublicHint_TheAssetGainsNothing`)
- **AC-7** (the two deductions agree): *Given* a seeded corpus of boards, *then*
  the public player's native deduction returns the same cell and state as
  `solver_state.js`'s `hintCell` does **on every board where no mark is wrong** —
  the condition under which `knownLine` is the identity, so the two are
  comparable. Where a mark IS wrong the two legitimately differ, and the test
  asserts that divergence is confined to exactly those boards. Minimum case
  count asserted inside the test. (test:
  `TestPublicHint_TheDeductionAgreesWithTheModuleOnCleanBoards`)
- **AC-8** (the comment is true): *Given* `play.js`'s header, *then* its account
  of what the page can and cannot do matches the shipped behaviour — the error
  count, the progress percent and Check named as needing the answer, the hint
  named as deriving. Asserted as a claim-vs-behaviour check, the shape
  ADR-0039/R1 requires. (test: `TestPublicHint_TheHeaderClaimIsTrue`)

## Engineering constraints

- **EC(ADR-0041/R2):** across a seeded corpus spanning extents, tiers and
  mark patterns, no asset the site serves gains a field, and no value the page
  holds in memory is a solution grid — neither before nor after any number of
  hints. Minimum case count asserted inside the test.
- **EC(ADR-0041/R3):** every ladder value, reason and count the page uses is the
  one `/solver_state.js` returns for the same input; the page re-implements the
  **deduction** (item 2, the `mask_runs` precedent) and nothing else.

## Guardrails

- **G-1: do not edit `solver_state.js` or `tokens.css`** — byte-identical
  build-time copies (ADR-0041/R3), checked by `player/assemble.py`'s
  `COPIED_FROM_ADMIN` at assembly time and from the test tree. **This card will
  want to add a solution-free `hintCell` to the shared module. It must not.**
  That is the right design and the wrong card: the module is byte-shared with a
  file CARD-268 is editing right now, and changing it is an escalation to the
  decompose station.
- **G-2: do not touch `src/nonogram/admin/**`** — CARD-268 is live in
  `solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and
  `puzzle_solve.html`. Read them; change nothing.
- **G-3: no fallback rung.** If no line forces a cell, the page reveals
  nothing (AC-4). A public-only fallback would have to read the answer, which
  is the one thing this card exists to avoid.
- **G-4: no field is added to any served asset** (AC-6/EC above), and no
  solution grid is held in any page variable.
- **G-5: do not touch `isClueSolved` or the solved banner.** The hint is a
  deduction over clues; the solved check is clue satisfaction. Related, not the
  same, and CARD-326 carries the same warning for the circles.
- **G-6: the error count, the progress percent and Check are NOT in scope** —
  the owner's 2026-10-30 decision left them out. A card that adds them has
  reversed an owner decision in a worktree.
- **G-7: `.player-hint` stays the usage paragraph** (item 5); the counter takes
  the admin's `.player-hints` / `data-player-hints` names.
- **G-8: marking, Region, undo/redo and reset are untouched** — their tests run
  unedited, except that the hint stroke joins the history like any other.
- **G-9: styling from tokens only**, and the hint highlight must stay distinct
  from CARD-325's crosshair tint and CARD-323's maybe cell, if either lands.
- **G-10: no test deleted, renamed, skipped or merged**, `parametrize` ids
  included (gate: node-id set difference with `-o addopts=''`).

## System contract

- ADR-0041/R2 — no public asset carries a solution grid or recoverable solution data (check: CARD-282's and CARD-283's guards, plus AC-6 — **and read the "interpretation" section above before judging this row**)
- ADR-0041/R3 — the board-state module and tokens are byte-identical build-time copies, never edited (check: `player/assemble.py`'s `COPIED_FROM_ADMIN`, plus its test-tree half)
- ADR-0041/R4 / CON-021 — play state is this browser's localStorage only (check: review-lens)
- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check: review-lens)
- ADR-0038/R2 — no network request per mark, hints included (check: AC-6)
- ADR-0038/R3 — the clues the page deduces from are the payload's (check: review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check: review-lens)
- ADR-0038/R6 — only the admin player, behind the CON-015/CON-016 door, ships the solution to a browser; **this card adds no new consumer of it** (check: AC-6)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: CARD-160's fixtures)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-8 — this card's premise is a false claim in shipped code)
- CON-005 / INV-002 — every published puzzle is uniquely solvable (check: `test_every_fixture_puzzle_is_uniquely_solvable`)

## Architecture context

- **FR:** FR-045 (the public player). Like the admin player's hint ladder before it, this is an owner-decided player feature that will warrant an FR-045 amendment with its own AC range; the owner decision of 2026-10-30 goes through `inputs/raw-requirements.md` on the architect side — this card does not edit `requirements.yml`, and its ACs above are the card-local statement the gate holds onto (quick-card rule).
- **ADR:** ADR-0041/R1-R4, ADR-0038/R1-R4, R6, R8, ADR-0039/R1
- **Components:** COMP-011
- **Trace:** not updated by this card

## Design context

- **Design system:** `player/player.css`, every value a token (G-9).
- **UI components:** `.player-toolbar` gains a Hint button; the clue cells and the board gain the rung-1 line highlight; a `.player-hints` counter region joins the toolbar, as the admin's does.
- **Screens:** `/play/<key>`.
- **Standards:** a real button with an accessible name and `aria-disabled` when there is nothing to hint; the rung-1/2 sentences go in a `role="status"` region so a screen reader hears the explanation, which is the whole point of rungs 1-2; the owner validates the look on a real puzzle render before merge, **and on a phone width** — CARD-321 exists because the admin ladder's answer line truncated there.

## Worktree notes

- **[Serialization, not dependency]** This card and CARD-323, CARD-324,
  CARD-325, CARD-326 all touch `player/play.js`, `play.html` and `player.css`,
  so their overlap is **1.0** and the conflict graph serializes any two in one
  wave. Deliberately not a `Depends on` edge — none needs another's output (the
  board's rule, stated on CARD-220's `Wave:`). **This one is the natural last
  slot** of the five: it is the only one with a design question, and the other
  four will have settled the public player's toolbar and test harness by then.
- **[Why `architectural` on a 1d card]** Not for its size. It is the first
  implementation anywhere in this repo of a hint that **derives** rather than
  reveals, it rests on a declared reading of ADR-0041/R2 that a reviewer must
  judge, and it corrects a false claim in shipped code. The marker also resolves
  the fix station to the heavy class, which is right for a card whose
  corrections are the same class of reasoning as its implementation.
- **[Re-derive the premise, do not trust it]** Every figure in "Why this card
  exists" is the orchestrator's, measured 2026-10-30. Re-derive them before
  building on them — especially that `lineForced` takes no solution and that
  `hintCell`'s only two uses of it are `truth()` and `knownLine`. If any of that
  does not reproduce, the card's premise is wrong and that is a finding, not an
  obstacle to work around.
