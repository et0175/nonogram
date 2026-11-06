# CARD-327: The public player gains a hint that DERIVES instead of reveals — and `play.js`'s comment saying it cannot is wrong

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 3c (1d) <!-- RESTATED in review cycles 2026-11-06 at dispatch, in the SAME edit that stamps the wave (a waved card with no Nc term reddens tests/test_kanban_review_record.py: CARD-325 did). Was 1d. 3c is a forecast, not a tuned figure: this is an ARCHITECTURAL card (the first in-repo hint that derives and does not reveal, a native re-implementation of the deduction cross-checked against the module, and a declared reading of ADR-0041/R2 the reviewer must judge). Comparators among the player cards: CARD-325 1 cycle (est 2c), CARD-326 1 cycle (est 2c), CARD-324 3 cycles (est 1c); the mean ratio of wave 79 is about 1.1. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/327-public-derived-hint
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-327
**Source:** owner request 2026-10-30 — "no maybe brush, no hints etc... I'd like both to reuse the same functionality". The orchestrator measured the hint question before carding it and found the shipped code's own account of it to be false; that measurement is this card's premise and is restated below so the implementation re-derives it rather than trusting it.
**Idea:** —
**Wave:** 79
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/play.js, player/play.html, player/player.css, tests/test_public_player_hint.py, tests/test_public_player_agreement.py <!-- agreement file added 2026-11-06 (SCOPE+ acceptable): the hint highlight is a look the public player reimplements, so it is held to the admin's there, as CARD-325 and CARD-326 did -->
**Review score:** —
**Started:** 2026-11-06T04:35Z
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
- **AC-9** (the control is OUTSIDE the toolbar; added 2026-11-06 on the owner's ruling): *Given* the built page, *then* the Hint control is not a child of `.player-toolbar`, `tests/test_public_player_zoom.py` and its measured one-row bound run UNEDITED and green, and the toolbar's button set is exactly what it was before this card. The control sits next to the usage paragraph or under the board, is at least 44 px in its touch dimension, and is reachable and legible at the zoom maximum and at a scrolled offset. (test: `TestPublicHint_TheControlIsOutsideTheToolbar`)
- **AC-10** (the hint highlight is distinct; added 2026-11-06, makes G-9 testable): *Given* a hinted line, *then* its highlight is distinguishable by PIXELS from the crosshair's tint (CARD-325, `is-crossed`) and from a circled clue number's ring (CARD-326), and a line that is hinted, crossed AND circled shows all three. Tokens only. (test: named by the implementation; state it)

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

## Owner rulings and premise re-verified 2026-11-06 (zoom, the crosshair and the circles have merged since this card was written)

Read against `main` by the orchestrator. **Owner rulings (2026-11-06), asked and answered before this card was dispatched:** (1) **ADR-0041/R2 is read as a rule about what an ASSET CARRIES, not about what a browser can compute from it: ACCEPTED.** The derived hint adds no data to any asset (`puzzle/<key>.json` stays exactly `clues`, `height`, `key`, `tier`, `width`), runs in the player's browser over clues it already has, and published puzzles are uniquely solvable (CON-005 / INV-002), so the clues already determine every cell, as the player's own solved check already relies on. The reviewer still checks the reading and AC-6 is its mechanical half. (2) **The Hint control lives OUTSIDE the toolbar: DECIDED** (added as AC-9). The toolbar is one row only from 839 px in landscape and already wraps to two rows between about 780 and 838 px (the owner's open F-1 residue from CARD-324), and `tests/test_public_player_zoom.py` reds BY DESIGN on any new toolbar button; a toolbar button would have moved that pinned bound. If the author finds a Hint control cannot live outside the toolbar, STOP and report: do not move the zoom bound.

**Verified true:** every export the card relies on is exported by `solver_state.js` today (`lineForced`, `nextRung`, `HINT_RUNGS`, `RUNG_POINT`, `RUNG_EXPLAIN`, `RUNG_REVEAL`, `HINT_REASONS`, `hintReason`, `hintCount`, `hintStroke`, `RUNG_EVENTS`, `hintCell`, `knownLine`); the false header sentence ("Adding any of them publicly needs the answer", "No error count, no progress percent, no hints (CARD-283 G-4)") is present in `play.js` verbatim; `play.html` already uses `.player-hint` (with `data-player-hint hidden`) for its usage paragraph, so the admin's split (`.player-hints` / `data-player-hints` for the counter) still applies (G-7); `play.js` carries 5 mentions of the word "hint", all comments, `play.html` 2, `player.css` 2: no hint behaviour exists yet.

**STALE in this card, corrected here and not elsewhere:** (a) **G-1 and G-2 say CARD-268 is "editing" or "live in" `solver.js`, `solver_state.js`, `admin.css`, `tokens.css` and `puzzle_solve.html`: CARD-268 is DONE** (as are CARD-269, 282, 283, 323, 325 and 326). The guardrails themselves STAND: do not edit `solver_state.js`, `tokens.css` or anything under `src/nonogram/admin/**`; a solution-free `hintCell` in the shared module is still the right design and still the wrong card. (b) The Estimate was in DAYS (restated above). (c) The 2026-10-30 'Re-verified' table's zero counts for zoom, circle and crosshair rules are all STALE: zoom (CARD-324), the crosshair (CARD-325) and the circles (CARD-326) are merged and live, and the Worktree notes' sibling list ("CARD-323, 324, 325, 326") is finished: this card is the LAST of them. (d) Line numbers in the card (`play.js:83` and others) are stale: cite by NAME.

**GAPS the card does not state (close each with a real test, as CARD-325 and CARD-326 did):** (1) **three marks now share the clue boxes and the board**: the crosshair tints the crossed row and column and their clue boxes (`is-crossed`), the circles draw a ring on clue numbers (`is-circled`), and the hint adds a highlight on a line: they must coexist (AC-10), from tokens only (G-9); read CARD-325's and CARD-326's records on `main` for how each was made not to hide the others (the circle is a BORDER on the number's `::before` precisely so the crosshair's background tint cannot hide it). (2) **the look joins `tests/test_public_player_agreement.py`** (CARD-328's one home for 'a look the public player reimplements is held to the admin's'): declare any divergence with its reason and a MEASURED figure; Touches now names the file. (3) **the listener census**: `test_every_player_control_is_in_the_ec_050_walk` in `tests/test_public_player.py` censuses every `addEventListener` type and reds on any addition; a Hint button's `click` is a type the file already registers for other controls, so it may need no edit, but if it does that file is a SCOPE+ edit and CARD-325's record shows what that edit looked like and why it was judged honest. (4) **zoom and scroll**: the hint highlight and the control must be legible and in place at the zoom maximum and at a scrolled offset (a test, as CARD-325's AC-7 and CARD-326's did). (5) **hint stroke and circles/crosshair**: a rung-3 hint is a recorded stroke, so it must move the circles exactly as any mark does and must not leave a crosshair behind. (6) **AC-4's trap**: the exhausted state must reveal NOTHING, and a plant that makes the page reveal a cell when no line forces one must red it; AC-7's cross-check against `hintCell` is only on boards with no wrong mark (`knownLine` is then the identity), and the test must assert that the two legitimately differ exactly where a mark is wrong. `touch-action` STAYS `auto` (owner decision 2026-11-05).

**What cost review cycles on this board this week, so do these first time:** write each declared bound IN THE TEST with its reason, a MEASURED number and a control that fails just past it (ADR-0039/R3); a structural 'reads no solution' scanner must be default-deny on PROPERTY reads as well as identifiers, refuse computed member access, and refuse every operator in the code it vouches for (CARD-325's first scanner denied only by identifier and its reviewer planted seven bypasses; CARD-326's had a comma-operator hole); every claim needs a test that fails if it is false, with a matched control in the same run; for every `!=` and `not in` you touch, plant its failure; behavioural plants that rewrite the served `play.js` must go through a Playwright ROUTE with a SERVED CANARY (rewriting the file and disabling the cache through CDP both let plants go unserved at random: CARD-326's author measured it); and when a plant is 'killed', say which scenario fired, not just that something did.

**STANDING CENSUS RULE** (it stopped two merge gates): after your work run on your tip, with `-rEfs`, `tests/test_suite_profile.py`, `tests/test_impact_set.py`, `tests/test_check_ref_resolution.py`, `tests/test_cli.py`, `tests/test_kanban_review_record.py`, `tests/test_collected_names.py`, `tests/test_guard_integrity.py`, `tests/test_shared_fixture_controls.py`, `tests/test_full_suite_lock.py`, `tests/test_browser_fixture_scope.py`, `tests/test_naming.py`, `tests/test_fixture_integrity.py`, `tests/test_card_349_cold_database.py` and the seven public-player modules. `test_suite_profile` counts any early `return` inside a test body as a silent host-state silence: write NO test body with a silent `return`; never add to a frozen registry to get green.

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

[Author round, commits `e48b70ff`, `320b3adc`, `07f69bed`] Verified by the orchestrator by git facts only: worktree clean, three commits over the cut `9ef90933`; diff over the cut is exactly six files (`player/play.html` 37, `player/play.js` 334, `player/player.css` 106, `tests/test_public_player.py` 12, `tests/test_public_player_agreement.py` 280, `tests/test_public_player_hint.py` 2609 new; 3368 insertions, 10 deletions); `src/`, `tests/helpers` and `meta/` diffs 0; `git diff 9ef90933 -- tests/test_public_player_zoom.py` is empty (AC-9's "zoom unedited"); the one added bare `return` in `tests/` is inside the nested generator helper `go` of `_placements`, not a test body; no added skip or xfail. NOT re-run by me: any test (a CARD-379 fix round holds pytest in another worktree). Author-reported (labels are the author's): hint module 163 node ids; whole-module node ids 409 -> 587 across the seven public-player modules plus the hint module, 0 removed, 178 added (28 in agreement); 360-board AC-7 corpus with minimum counts asserted in the test, three-way cross-check (the served `lineForced`, `hintCell`, and a Python brute-force oracle that shares no code); 32 route-plants each with a served canary and a matched control, the "fired" set pinned by exact equality; 26 scanner bypass plants; 13/13 scenarios asserted to run; suite 1702 passed, 3 skipped (all `conftest.py` unarmed-DB), 0 failed, in 486 s (13 census modules 1102; `test_kill_matrix` and the full suite NOT run; armed DB pass NOT run). **Decisions the reviewer must judge, declared by the author:** (1) the Hint control is in `.player-below > .player-hint-bar` beside the usage paragraph, outside the toolbar (AC-9, owner ruling); zoom's pinned premise (space below the stage < offset above it, as small as 21 px at 840 px and up at the cut) forced the placement, and `say()` HIDES the usage paragraph while a hint sentence shows (without the swap 84 of 170 grid viewports break the premise; with it the worst margin is 54 px); (2) the public hint tint is deliberately stronger than the panel's (`--color-accent-tint` is only 6/255 from the crosshair grey on this page; public tint 20, blend 10 and 14; `TINT_FLOOR` 8 against a smallest measured 10, margin 2, headless Chromium on this Mac) - CARD-325's comment had promised the same token; (3) the page's own save now keeps and validates `hint: true` on a stroke (`savedStroke`/`strokeOf`; version stays 1, old saves load) because a reload turned a hint into a plain mark and zeroed the count: NOT named in the card, touches the save format, to be checked against G-8 and ADR-0041/R4; (4) SCOPE+ `tests/test_public_player.py` (the action-set assertion, the expected-control count, the walk entry, comments) and `play.html`'s false "no hint button" header sentence; (5) a contradicting line is SKIPPED (surfacing "this line cannot be right" would reverse the owner's error-count decision), held both ways by `TestPublicHint_AContradictingLineIsSkipped`; (6) the rung is mirrored as `data-player-rung`, not a new `window.publicPlayer` key. AC-vs-body mismatches found by the author: Design context says the counter joins the toolbar (contradicts AC-9; the ruling was followed); AC-6 / the header say the only request is the puzzle GET (the page also GETs its four static assets: asserted one `.json` GET per load, none per hint); no AC named for the contradicting-line decision or AC-10's test (named by the author). Weak spots the author declares: last-row, full-board, control-never-disabled and old-outline plants move only 2-3 umbrella node ids; `a-null-line` and `a-forced-cell-reads` plants break too much to discriminate; a design observation (not carded): at 300% on a phone the lit line is out of view because neither page auto-scrolls to it. Not verified by the author: other machines' rendering distances, a real phone. Renders in `~/Documents/nonogram-reviews/CARD-327/`. Not yet reviewed.

[Review 1/3] Score: 8.5 (threshold 8.0 reached; 0 blockers; 8 findings F-1..F-8, none needs an owner decision or earns a card under the cut bar). Reviewer-reported, not re-run by the orchestrator; "mine" is the reviewer's. Findings in `meta/review/CARD-327-cycle1.yml` (a private clone; copy in `~/Documents/nonogram-reviews/CARD-327/review-cycle1-instruments/`). Correctness: the reviewer's own oracle (`oracle.mjs`, slices `forcedLine`/`derivedHint` out of `play.js` and enumerates all 2^n lines) gave 0 mismatches over 4000 random lines (contradictory marks and '?' included) and over two 3000-board corpora (the first-undecided, row-first tie rule matches brute force; on boards with no wrong mark no wrong cell, equal to the module's `hintCell`); G-3 six presses on the exhausted fixture reveal nothing, count 0, undo stack 0, no request; 191 boards with wrong marks, 126 with a skipped contradicted line, `derivedHint` matches the board-as-is oracle on all; a hint taken from a wrong mark can state a wrong cell (declared, inherent to ADR-0041/R2). ADR-0041/R2, R3, ADR-0038: assembled site's puzzle JSON keys exactly `clues, height, key, tier, width`; no non-comment `solution` in `play.js`/`player.css`; `assemble.py` and `src/` diffs empty; `solver_state.js` and `tokens.css` byte-identical to the admin copies; 0 requests over 4 presses. Declared decisions: (1) placement and the usage-paragraph hide ACCEPTABLE (F-4, low, no card): zoom module unedited and green (39), worst margin 54 px over 232 viewports, 0 violations; costs: the touch-screen Region instruction disappears until the next recorded change, and the zoom premise is now held by a UI swap so any future line below the stage reds the zoom module; (2) the stronger tint is honest: at rest a lit-only cell is 40 from plain, 20 from crossed, 10 from lit-and-crossed (the reviewer's first reading of 9 was a mid-fade artefact); floor 8, margin 2, one machine; (3) the SAVE-FORMAT change is WITHIN THE CARD, no owner decision (F-5): same key, `v` stays 1, a save with no `hint` loads, a non-`true` `hint` discards the whole save as any malformed stroke, top-level keys exactly the pre-card set, no rung/line/probe field, a reload keeps count 1 with rung 1 and nothing lit, downgrade is safe; ADR-0041/R4 and G-8 hold; the card text should record it; (4) SCOPE+ edits honest (two deleted lines in `test_public_player.py`). Tests: hint 163 passed; the other seven public-player modules 34/154/86/70/21/33/39 (600 total with hint); node ids 409 -> 600, 0 removed, 191 added (the author's 587 is stale; the last commit added 13); census 13 modules 1102 passed + 3 skipped (all unarmed-DB), 0 red; 14 of the 32 plants re-fired incl. the weak ones, all as pinned. Findings: F-1 (low, inline) two behaviours nothing pins: M10 (rung 3 also writes a second localStorage key holding the board) and M12 (the counter reads 0 after Reset) pass every real test; add "a hint writes exactly one key" and "the counter survives Reset" (or state them as unheld); F-2 (low, inline) 5 of 13 novel scanner bypasses pass (module-level `const` stash, closure `const memo`, alias const, an unscanned helper called from the click handler, a regex literal containing a quote): the default-deny closes `let` and `window`, not closure `const`; extend it or narrow the "no page variable holds a grid" claim; consequence today nil (no solution on the page), the helper fallback is caught behaviourally (plant M9 fires `exhausted`); F-3 info the stale node-id figure; F-5 save format, record on the card; F-6 info the card's Design context says the counter joins the toolbar, contradicting AC-9 (the ruling was followed; correct the card text); F-7 info (agreed, not carded) at 300% on a phone the lit line may be out of view, no auto-scroll; F-8 info the wrong-mark behaviour. Not done by the reviewer: full suite, `test_kill_matrix`, armed DB, a real phone or another machine's rendering, 18 of 32 plants.