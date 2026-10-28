# CARD-267: Crosshair — the player highlights the hovered cell's row, column and their clues

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/267-player-crosshair
**Worktree:** —
**Source:** quick — owner decision 2026-10-22 (player-convenience session, option 1: "highlight row/column for selected cell so that the gaze don't slide away"); no handoff increment
**Idea:** —
**Wave:** 63
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_crosshair.py, tests/test_admin_design_tokens.py, tests/test_puzzle_solver_marking.py, tests/test_puzzle_solver_page.py, tests/test_browser_fixture_scope.py , tests/test_puzzle_editor_ui.py <!-- 9th entry added 2026-10-28 at fix round 1: a prose-only de-numbering of the stale ordinal at :759, which THIS CARD made stale by two when it added the fourteenth PAGE_ISOLATION row. No claim change; its 117 tests green at 1ef355c0.  corrected 2026-10-28 by the implementation round: tokens.css REMOVED (it is mirrored verbatim from meta/design/tokens.css and pinned by a test; a derived component value belongs in admin.css beside --player-thin). Four test files ADDED, and the breakdown stated so it is checkable (the earlier wording said "three are registries ... and the third", which miscounts and is self-inconsistent -- corrected 2026-10-28, cycle 1 F-008): TWO are registry joins a new family file is forced into -- tests/test_puzzle_solver_page.py (which holds PAGE_ISOLATION) and tests/test_browser_fixture_scope.py (the ALONE_RECORD sampling, which this card's file postdates); ONE adds a new claim test (tests/test_admin_design_tokens.py, AC-8/G-4); and ONE is the non-weakening accommodation G-6 now permits by name (tests/test_puzzle_solver_marking.py). The Touches LIST itself is correct: 8 declared, 8 in the diff. -->
**Review score:** 7.0 → **9.5 cycle 2/3 CERTIFIED**, zero critical, zero important, one minor
**Started:** 2026-10-28T07:23:17Z
**Closed:** 2026-10-28T18:55:49Z
**Actual:** 1.4d
**Merge commit:** 4b4a26e7
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The board is one `<table>`: `th.player-clue.is-col` boxes above (and, on big
  boards, below) the grid, `th.player-clue.is-row` to the left (and right),
  `td.player-cell` cells with `data-row`, `data-col` and `data-state`
  (`solver.js`, `drawBoard`). Each clue box carries its 0-based line in
  `data-line`, which is what pairs a duplicate gutter's box with its twin
  (CARD-212) — `clueNumbersOf` collects spans by axis + `data-line`, never by
  DOM order, and `paintCircles` (CARD-188) paints **both** twins.
- Pointer handling lives in `solver.js` (pointerdown/move/up with a drag
  preview; clue boxes keep `touch-action: auto` and are not markable). Nothing
  reacts to a pointer that is merely *over* a cell.
- The precedent for a pure view behaviour is Zoom (CARD-195, template comment):
  "It is a view setting only: it changes no board state, is never saved" — the
  crosshair is the same class of thing, and even less: it is not a setting, it
  has no toggle and no persistence at all.

**What changes.** When the player's attention is on a cell, the board shows a
crosshair: that cell's whole row and whole column are lightly tinted, and the
row's and column's clue boxes are highlighted — so the eye can travel from a
cell to its clues and back without sliding onto a neighbouring line.

1. **Which cell has the crosshair.** On a pointer that can hover (mouse, pen in
   range): the cell under the pointer; leaving the board clears it. During any
   marking gesture: the cell the gesture is currently over. On touch (no
   hover): the crosshair appears with the gesture and **stays on the last
   touched cell** after pointerup — a phone player keeps their place between
   taps. A fresh page load shows no crosshair.
2. **What gets marked.** A class (suggested: `.is-crossed`) on every
   `td.player-cell` of the row and of the column, and on every clue box whose
   axis + `data-line` matches — on a doubled axis that is **both** twins, the
   same rule as circles. Exactly one row and one column carry it at a time.
3. **Rendering only.** No change to `solver_state.js` — the crosshair is not
   player state (ADR-0038/R4): never in a stroke, never in the undo history,
   never in the save, invisible to `serializeState`. It changes no
   `data-state`.
4. **Pointer-move cost.** A move within the same cell does nothing; a move to a
   new cell toggles the old row/column/clues off and the new on — never a
   board redraw, and no work per move beyond the two line sweeps.
5. **Colors from tokens.** The tint must keep all four `data-state` looks
   (unknown / filled / empty / maybe) plainly distinguishable, and must not be
   confusable with CARD-188's clue circles. ~~New values go in `tokens.css`.~~
   **CORRECTED 2026-10-28 (cycle 1 F-004):** they do not. `static/tokens.css` is
   mirrored verbatim from `meta/design/tokens.css` and byte-pinned by a test, and
   a *derived* component value belongs in `admin.css` beside `--player-thin`.
   The implementation deviated from this instruction and was right to; the
   instruction was wrong, and the deviation is recorded below rather than left
   as a silent disagreement between the brief and the diff.
6. **Redraws.** After a mirror-breakpoint or zoom redraw (`drawBoard` reruns),
   no stale `.is-crossed` survives — cleared or recomputed, either is fine, a
   half-painted crosshair is not.
7. **Accessibility.** The crosshair is decorative and redundant by nature (it
   repeats where the pointer already is): it adds **no** ARIA attributes, no
   live announcements, and must not change what a screen reader reads per cell
   or clue.

Out of scope, recorded so the review does not invent it: hovering a *clue box*
does not light its line (a candidate follow-up, not this card), and the
crosshair gets no on/off setting unless the owner asks for one after seeing it.

## Acceptance criteria

- **AC-1** (happy): *Given* a rendered puzzle, *when* the pointer hovers cell
  (r, c), *then* every cell of row r, every cell of column c, and the clue
  boxes with `data-line` r (row axis) and c (column axis) carry the crosshair
  marker, and no other cell or clue box does. (test:
  `TestSolverCrosshair_RowColumnAndCluesLight`)
- **AC-2** (happy, move): *Given* a crosshair on (r, c), *when* the pointer
  moves to (r2, c2), *then* the old row/column/clues are cleared and exactly
  the new ones are marked. (test: `TestSolverCrosshair_FollowsThePointer`)
- **AC-3** (happy, doubled board): *Given* a board big enough for CARD-212's
  duplicate gutters, *when* a cell is hovered, *then* **both** twins of its
  row clue and **both** twins of its column clue carry the marker. (test:
  `TestSolverCrosshair_LightsBothTwinsOnADoubledBoard`)
- **AC-4** (happy, touch): *Given* a touch drag across cells, *then* the
  crosshair follows the cell under the finger during the drag, the drag still
  marks exactly as today, and after pointerup the crosshair remains on the
  last touched cell. (test: `TestSolverCrosshair_TouchKeepsTheLastCell`)
<!-- AC-5, cycle 1 F-005: "leaves the board" is not what the code watches — it
     clears on leaving `.player-stage`, which is a WIDER region than the board.
     The padding / gutter-corner case (pointer inside the stage but outside the
     board) is commented in the implementation and UNTESTED; recorded here so it
     is a known boundary rather than an assumed one. -->
- **AC-5** (edge, leave): *Given* a hover crosshair, *when* the mouse leaves
  the board, *then* the crosshair clears. (test:
  `TestSolverCrosshair_ClearsWhenThePointerLeaves`)
- **AC-6** (edge, view-only): *Given* any sequence of hovers, *then* no cell's
  `data-state` changed, the undo history is exactly as without them, and no
  save was written — and `solver_state.js` is not edited by this card at all.
  (test: `TestSolverCrosshair_IsPureView`; the no-edit clause is G-5,
  structural)
- **AC-7** (edge, redraw): *Given* a crosshair, *when* the board redraws
  (viewport crosses the mirror breakpoint, or zoom), *then* no stale marker
  survives the redraw. (test: `TestSolverCrosshair_NoStaleMarkerAfterRedraw`)
- **AC-8** (edge, a11y + tokens): *Given* the shipped page, *then* hovering
  adds no ARIA attribute anywhere, and the new CSS rules take every color from
  tokens — with a per-rule check in the token test file, CARD-212 G-7 style.
  (tests: `TestSolverCrosshair_AddsNoAria`,
  `test_the_crosshair_tint_comes_from_tokens`)

## Guardrails

- G-1: Clues come from the embedded `compute_clues` JSON; the client never
  re-derives them (ADR-0038/R3; test: `TestSolverPage_ShowsTheClues`).
- G-2: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-3: No request per mark — and none per hover either (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-4: Styling from tokens only (test:
  `test_the_stylesheet_uses_tokens_not_literals`, plus the per-rule check in
  AC-8).
- G-5: `src/nonogram/admin/static/solver_state.js` is not edited — the
  crosshair is rendering, and a crosshair that needs the state module has been
  designed wrong (ADR-0038/R4).
- G-6: Marking behaviour is untouched: click sequence, drag preview/commit,
  Region, hint, circles, counters and the save all behave exactly as today.
  **AMENDED 2026-10-28, review cycle 1 F-001.** This guardrail used to end
  *"(the existing `tests/test_puzzle_solver_*.py` files run unedited)"*, and that
  parenthesis is **unsatisfiable by any card that adds a family file** — not
  merely inconvenient for this one. `tests/test_browser_fixture_scope.py:2050`
  asserts `set(PAGE_ISOLATION) == on_disk` over a glob of
  `tests/test_puzzle_solver_*.py`, and `PAGE_ISOLATION` itself lives in
  `tests/test_puzzle_solver_page.py` — a file matching that very glob. So a new
  family file *forces* an edit to an existing family file, mechanically and
  independently of any design choice. It also **contradicted this card's own
  body item 2**, which requires a class on every `td.player-cell`: both could
  not hold.

  What G-6 now says: marking **behaviour** is unchanged, and an edit to an
  existing family file is permitted only where it is **non-weakening** — the
  claims it carries are unchanged and each still kills its own mutant — and
  **recorded on this card**. Three such edits exist in this diff, and the
  implementation record enumerated two of them:

  1. `tests/test_puzzle_solver_marking.py` — the `ClickCycles` accommodation
     (`wait_for_timeout(0)` → `mouse.move(1, 1)`), because a click leaves the
     pointer on the cell it clicked and the crosshair tints what is under the
     pointer, so the old read-back measured the *crossed* look rather than the
     mark. Reverting it reds `marking.py:298` with the background measured as
     `--player-cross-ink`. Reading a mark's look with the pointer parked under
     the tint is the wrong reading point; the accommodation is correct.
  2. `tests/test_puzzle_solver_page.py` — the new `_STRIPPED` line. Neutering it
     reds.
  3. `tests/test_puzzle_solver_page.py` — **the `PAGE_ISOLATION` registry row**,
     which the record filed under "registries outside `Touches:`" rather than
     under G-6. It is the instance that proves the clause unsatisfiable, so it
     belongs here.

  One over-reach in the record is corrected with it: the `ClickCycles` failure is
  **not** structurally forced — a non-background channel would have left computed
  `backgroundColor` untouched — so the CSS channel argument is a design judgement
  rather than a necessity. It is a sound judgement; it is not a proof.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R3 — clues are the embedded JSON of `compute_clues`; the client
  never re-derives them (check: `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- CON-021 — interactive play only in the admin panel's player; nothing
  persisted server-side (check: review-lens)

## Architecture context

- **FR:** FR-044 (the player). This is a view convenience inside the already
  decided player; the owner decided it 2026-10-22. FR-044's statement is not
  amended by this card — if the architect pipeline wants it recorded, the
  owner decision goes through `inputs/raw-requirements.md` as usual.
- **ADR:** ADR-0038/R1–R4.
- **CON:** CON-015/CON-016 (the admin door), CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; every value is
  a token (G-4).
- **UI components:** `.player-board`, its `td.player-cell` and
  `th.player-clue` boxes — the crosshair is a class on existing elements, no
  new elements.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** decorative highlight, no ARIA; all four cell states stay
  distinguishable under the tint; owner validates the look on a real puzzle
  render before merge (standing practice for player visuals).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** (in `tests/test_puzzle_solver_crosshair.py`,
except the token check, which joins `tests/test_admin_design_tokens.py`) —
none exists yet; report them as written, never as passing before they exist:
`TestSolverCrosshair_RowColumnAndCluesLight`,
`TestSolverCrosshair_FollowsThePointer`,
`TestSolverCrosshair_LightsBothTwinsOnADoubledBoard`,
`TestSolverCrosshair_TouchKeepsTheLastCell`,
`TestSolverCrosshair_ClearsWhenThePointerLeaves`,
`TestSolverCrosshair_IsPureView`,
`TestSolverCrosshair_NoStaleMarkerAfterRedraw`,
`TestSolverCrosshair_AddsNoAria`,
`test_the_crosshair_tint_comes_from_tokens`.

## Worktree notes

—

## [IMPLEMENTATION — 2026-10-28] `ee6e284e` — and G-6's "unedited" clause is NOT satisfiable

Three commits, 8 files. **G-5 verified from git: `solver_state.js` is not in the
changed set** — the crosshair is rendering, as designed. Wave 63, run
concurrently with CARD-227 and CARD-284.

Two top-level functions and two call sites in `solver.js`: `crossedParts` selects
the clue boxes by **axis + `data-line`**, so a CARD-212 doubled gutter lights both
twins **by construction** — the same reason `clueNumbersOf` pairs circles that
way. `wireCrosshair` owns its own `pointerdown`/`pointermove`/`pointerleave`
listeners, calls no `player` callback, reads no board, and never `preventDefault`s
or stops propagation. The crosshair clears only on `pointerleave` of the stage,
so **a pointer over a clue box keeps it** — which is the card's actual purpose.

Four CSS rules, with the tint **derived** from two design tokens. Figures
re-derived and the door named: `--player-cross-ink` by arithmetic is
`rgb(62.1, 67.0, 78.2)`, mean **0.2710**; Chromium's own
`getComputedStyle(…).backgroundColor` reads `rgb(62.08, 67.00, 78.20)`, mean
**0.27095** — two instruments agreeing. Gap between the crossed light ground and
the crossed filled ground **0.640** against the test's 0.4 bar.

### G-6 cannot be satisfied as written, and that is measured rather than argued

G-6 says *"the existing `tests/test_puzzle_solver_*.py` files run unedited."*
**Two of them failed on the first family run**, and neither failure is a
behaviour change:

- `TestSolverMarking_RevealsNoCorrectness` compares `document.body.outerHTML`
  taken **before any pointer has touched the board** against the same after a
  drag — so it differed by `is-crossed` on one row, one column and their clue
  boxes, **and by nothing else**. Fixed by adding one line to `_STRIPPED`,
  **exactly as CARD-188 added its `is-circled` line.**
- `TestSolverMarking_ClickCycles` read a clicked cell's computed background with
  the pointer **still parked on it** — i.e. under the tint. **All three of its
  look assertions would have failed; only the first was reported** — the
  short-circuit trap, caught here rather than mistaken for one defect. Fixed by
  reading the look with the pointer off the board, which is the same claim read
  where it is made.

**Any class-based marker hits the first one**, and the round could find no design
that avoids it without abandoning the card's own *"a class on every cell of the
row and of the column"*. **So G-6 needs amending to allow test accommodation
while still forbidding behaviour change** — taking the crosshair into those
tests' expected values would have made them assert the crosshair, which is the
version that must stay forbidden.

### Kill instrument — 17 mutants, 16 killed, 1 declared, per assertion

Each deletes one line's content keeping the newline, so every other line keeps its
number; both files restored and `git hash-object` verified before == after.
**Inside/edge pairs** for each mechanism: the move listener vs the no-op boundary,
the two ends of each sweep pair, a leave with a crosshair vs a leave with none,
the general cell rule vs the specificity override that must beat it.

Three results worth keeping. **MJ-6** (deleting `crosshair.forget()` in `redraw`)
kills **only** the re-hover assertion — the half-painted state AC-7 is actually
about — while "no marker survived" stayed green, *as a deletion must*. **MJ-10**
produced a real `TypeError` on an ordinary mouse movement over a fresh board.
**MJ-11 SURVIVED and is declared**: the `table === null` guard is **dead, not
untested** — `start()` returns before `wireCrosshair` on a refused payload and a
redraw replaces the table inside one task — so only its *direction* matters, and
it fails toward not painting. CARD-271's `keepCluesInView` precedent.

**And it named what the instrument cannot certify, by category rather than
glossing it.** ~~A deletion only ever makes the crosshair do **less**, so no
deletion mutant can red the negative claims (AC-6's whole-snapshot equality, no
request, no ARIA, G-5's structural checks).~~ **[CORRECTED 2026-10-28, cycle 1
F-002 — this was wrong about *why*, and the correction matters more than the
sentence.]** No mutant could red the negative claims **while the test was driven
from an empty board: the limit was the STATE, not the mutant class.** An
*addition* mutant (`localStorage.clear()` in the paint loop, cycle 1's M13)
reached the claim and **survived**, and so did a second one stripping every
`is-circled` (MA-2) — so the blindness was never about deletions only making the
crosshair do less. Both red now. Fix round 1 drives the snapshot from a board that
**has** state and asserts all seven fields away from their virgin value first, and
MA-2 fired against the pre-fix test file survives — which is what proves the fix
is the thing that makes it red. Those rest on their own positive
controls — and **three were measured firing** (MJ-1 reds the request test's "a
crosshair was made", the ARIA test's, and pure-view's), so those readings are not
instrument blindness. Two controls no mutant of its own can red are named as
such rather than claimed as kills.

### Pre-gate — two invocations at HEAD, and the honest reason it is two

**A, the whole browser family (G-6's evidence), 14 files: 503 collected, 503
passed, 0 skipped**, 347.13 s, exit 0. **B, the derived blast radius, 11 files:
461 collected, 457 passed, 4 skipped**, 118.24 s, exit 0. Totals **964 collected,
960 passed, 4 skipped, 0 failed.** All four skips named: `db_required` at
`conftest.py:207`, the standing "DB tests skip silently" condition, unrelated to
this card. Hang-guard dump **0 bytes**; `NONOGRAM_TEST_HANG_SECONDS` set nowhere.

**Three earlier attempts at a single 25-file invocation were abandoned, and the
reason is the wave's real cost.** With 4–5 sibling pytest processes the host went
from loadavg 12.95 to **52.07** and the run fell to ~4 tests/min against ~96 at
loadavg 4.5. It stopped rather than keep loading the box — and critically,
because `tests/test_browser_fixture_scope.py` bounds each child pytest at
**90 s**, sized for a 21.5 s ordering run: under that load **the bound would have
turned contention into test FAILURES**, i.e. a wrong verdict. **No verdict is
claimed from those three runs.** That is the right call, and it is the clearest
measured cost of running three cards at once on this box.

### The filename collision — this report closes CARD-284's mystery

CARD-284 reported that *"something re-executed my harness twice"*. **It was this
station.** The shared scratchpad root held `mutate.py` under the same name both
used, so this round launched **CARD-284's** script twice, against
`…-card-284` rather than its own worktree, and killed both — the second kill
landing while `player/pages.js` carried a `// MUTANT` edit. **Each station found
one half of the event and both reported it; neither hid it.** Resolved: CARD-284
re-ran its whole census under a per-mutant HEAD precondition (27/27), and its
tree is verified clean with both files at HEAD. **This station's own worktree was
never affected** (clean throughout, blob hashes verified), and it moved everything
into `scratchpad/card267/` with prefixed names. Both stations independently
proposed the same rule, now in the orchestrator's standing brief rules.

### Deviations and what could not be established

- **`tokens.css` deliberately NOT edited**, departing from the card's brief item
  5. It is mirrored verbatim from `meta/design/tokens.css`, pinned by
  `test_the_served_tokens_are_the_design_systems_tokens`, and its own header says
  to edit it through forge:ui and never by hand — editing it would also have gone
  outside `Touches:` into `meta/design/`. A crosshair tint is a value **derived**
  from two tokens for one component, which is what `--player-thin` already is. **A
  real design-system token would be a forge:ui change and a second card.**
- **Three registries outside `Touches:` had to be joined**, and the third was
  found only by running the gate: `test_puzzle_solver_page.py`'s `PAGE_ISOLATION`,
  and `test_browser_fixture_scope.py`'s 15 `ADDED_SINCE_BEFORE` entries **plus**
  an `ALONE_PROBES` entry that `test_the_record_reaches_every_file_in_the_family`
  demands of any family file postdating CARD-235.
- **The crosshair also reaches the manual editor** — `puzzle_edit.html` loads the
  same `solver.js` (CARD-246's second consumer). The card's scope statement does
  not mention it. Measured harmless (editor suite green in run B) and arguably a
  benefit, but **a scope fact for the owner to rule on**.
- **The look is not owner-validated.** The Design context asks for a render review
  on a real puzzle before merge. The exact computed values are above so the check
  is cheap; the choice of `--color-surface-hover` over `--color-accent` is the one
  thing only an eyeball can settle.
- **Could not establish** the negative claims by deletion mutant (above);
  a single-invocation pre-gate over the whole 25-file radius (three attempts
  abandoned under saturation) — **declared as a bound rather than called sound**.
- A stale ordinal was dropped where `len()` makes it mechanical, and **a second
  stale ordinal in `test_puzzle_editor_ui.py:759` was reported rather than
  touched**, being outside both the Touches and the blast radius' reason to change.
- **Nothing shipped uncertified**: the last commit was followed by the full A+B gate.


## [CYCLE 1 — 2026-10-28] **7.0, NOT CERTIFIED** — zero code defects, two surviving mutants, and a card that contradicted itself

Report: `meta/review/20261028T144500Z-CARD-267-cycle1.yml` (10 findings, parses).
Reviewed `ee6e284e` against merge-base `7a62d704`. **14 mutants fired, 10 killed,
3 survived, 1 discarded as invalid.** System contract: **5 rules checked, 5 ✓,
0 ✗.** Gates: **302 distinct tests, 0 skips anywhere, 0 failures** — including
the 117/117 editor suite and the 128/128 co-change peers whose run the API
interruption had cut short.

Risk **LOW**. Every AC is backed by a mutant that kills at the cell the
implementation named. **What gates this card is evidence quality, plus the card's
own text** — three of the four card-side findings are repaired above (F-001's
G-6 amendment, F-004's `tokens.css` instruction, F-005's AC-5 boundary, F-008's
miscounted `Touches` comment).

### F-002 (important) — AC-6's purity test cannot fail on a destructive side effect

**M13 survived: 15/15 green.** One added line in the paint loop —
`localStorage.clear()` on every hover — passes **every** crosshair test,
including AC-6's nominated
`test_a_long_hover_sequence_changes_no_state_no_history_and_no_save`, whose
snapshot contains `"save": Object.entries(localStorage)`.

The cause is the state, not the mutant class: the test is driven from a **virgin
board** (`assert before["states"] == [U] * 225`, verified at
`tests/test_puzzle_solver_crosshair.py:578`), so four of its seven snapshot
fields sit at their initial value and `save` compares `[] == []`. An equality
between two empty things can catch only *additive* effects. The implementation
record framed this as a limit of deletion mutants — "no deletion mutant can red
the negative claims" — but **M13 is an addition and survives anyway**, so the
registry row's catch-claim *"a single changed field reds it"* is false in a
nameable direction. No user-facing bug: the shipped code never touches storage,
and M13 had to add the call. **Fix: drive the snapshot from a board that already
has state**, as `TestSolverMarking_RevealsNoCorrectness` does; then M13 must red.

This is the same shape as CARD-305's cycle-1 gating finding, found the same day
in a different card: *a nominated "this is the test that catches it" cell driven
from the one state in which its own defect is invisible.* Two independent
instances in one wave makes it a family, not a coincidence.

### F-003 (important) — "measured in computed pixels" overstates the instrument

`tests/test_puzzle_solver_crosshair.py:212`. **Three of four states are told
apart by an `::after` content string, not by pixels.** Surviving mutant M11 made
the dot pixel-identical to the tint and all 16 tests stayed green. The
inside/edge pair fired as the rules require: M7 (filled override) killed, M11
survived.

What the review conceded and checked, so the finding stays narrow: the
docstring's *"a tint that flattened the dot away fails one of them"* is
**arithmetically safe** — a tint reaching the dot's mean luma 0.392 cannot also
clear the 0.589 the margin arm needs. And the substance was verified in a new
domain (WCAG 2.1 contrast): dot **5.25:1**, "?" **6.20:1** against the tint. **The
shipped CSS is fine; only the claims are wide.**

### F-006, F-007, F-009 (minor)

**F-006** the ARIA probe's only control is "found some elements", not "can read an
ARIA attribute" — responsiveness *is* established by M10 (killed), so this is a
control-placement gap rather than blindness. One line. **F-007** on touch, a
redraw drops the crosshair with no event to bring it back, which defeats body
item 1's own "keeps their place between taps" rationale; measured condition —
`viewportChanged` redraws only `if (isBig)`, so boards past `BIG_SIDE` only.
Permitted by item 6; the tension was unrecorded, and is recorded here now.
**F-009** one unexplained red of
`test_leaving_the_stage_clears_it_and_a_clue_box_does_not` across 8 whole-file
runs, under a CSS-only mutant that left it green on two re-fires — **not
mutant-attributable, and the failing cell is unknown** because the reviewer's own
harness truncated the traceback. Plausible mechanism named (no settle after
`mouse.move`, unlike its sibling tests). Carried as a flake to watch, not as a
verdict.

### The validator delta, explained rather than attributed

Worktree reads **0 errors / 117 warnings** against main's **0 / 113**. The +4 is
**merge-base drift, not this card**: CARD-227's architecture work landed on main
after `7a62d704` and cleared four dead check refs. This card touches **zero**
`meta/architecture` files, so no regression is attributable to it.

### Could not establish, in the review's own words

The failing cell of F-009's single red (traceback lost to the harness's own
truncation) · whether the implementation's pre-gate runs A and B are disjoint,
which its "964 collected" total assumes · **the owner's eyeball on a real
render** — figures handed over instead, and they agree across two doors:
`--player-cross-ink` is `rgb(62.08, 67.00, 78.20)` by arithmetic against
Chromium's `color(srgb 0.243451 0.262745 0.306667)`, the mean agreeing to five
figures, with a luma gap of 0.64016 against the 0.4 bar · whether the editor
reach is *wanted* (see below) · the full suite, which this cycle did not run.

### Out of scope, and one of them needs the owner

**The crosshair reaches the manual editor.** `puzzle_edit.html:153` is a
`.player-stage` and `:207` loads the same `solver.js`, so the editor gets the
crosshair too. **Measured harmless — 117/117 editor tests green** — but whether
it is *wanted* there is a scope call nobody has made. Also:
`tests/test_puzzle_editor_ui.py:759` carries a stale ordinal ("the twelve";
`PAGE_ISOLATION` now holds 14), reported and deliberately not touched. FR-044 is
unamended and `raw-requirements.md` has 0 mentions — pre-declared by the card.


## [FIX ROUND 1 — 2026-10-28] `1ef355c0` — 12 mutants, 12 killed, and the fix's own control fired against the pre-fix tree

5 files, +235/−43. The `src/nonogram/admin/static/*` changes are **comment-only**;
**no shipped behaviour moved this round.** HEAD changed under the round mid-flight
(`ee6e284e` → the merge `b74e9083`) and **no verdict was taken against a stale
assertion**: the harness resolved HEAD fresh per run rather than from a literal
SHA, and no mutant had been fired yet. The merge touches none of this card's files.

### F-002 closed — and proved by firing the fix's own control against the OLD tree

AC-6's purity snapshot now drives from a board that **has state** (a closed run
painted by real clicks, plus one stroke taken back so Redo is live), with the
virgin reading **kept as the premise**: all seven fields must differ from their
virgin value before a hover is made. `_purity_snapshot` is extracted so the three
readings cannot drift apart.

**The control that makes this more than an assertion:** MA-2 fired against the
**pre-fix** test file — the virgin-board drive cycle 1 reviewed — **survived,
15/15 green**. Against the fixed test it kills. So the fix is what makes it red,
and the root cause is the **state**, not the mutant class.

**The class was audited, not just the named instance.** Three other negative claims
are correctly polarised with their own in-test controls; one
(`test_hovering_adds_no_aria_attribute…`) **had the same defect in the destructive
direction** and F-006's single line closes both; and one — `assert problems == []`
— is an empty-vs-empty with **no in-test instrument control**, left in place and
named rather than passed over. ~~**the one remaining gap of this shape**~~
**[CORRECTED 2026-10-28, cycle 2 F-001: there are TWO, and the second is inside
the very test this round reports F-006 as having closed "both" defects of.]**
`tests/test_puzzle_solver_crosshair.py:877` — `assert …#puzzle-player-announce…
inner_text() == ""` — is a second bare empty-vs-empty. Cycle 2 proved the halves
separately: a paint loop that **writes** to the announce region is killed, so the
direction AC-8 forbids is covered, but a paint loop that **clears** it **survived
at exit 0**, because the test drives from a board where the region is empty by
design. The region is **not** vacuous — `solver.js:835-836` writes the solved
banner and the hint text — so a hover arriving while an announcement is live is
reachable and unvisited. **No shipped defect**: the crosshair slice contains no
such write, and the mutant had to add one.

### F-003 closed by narrowing the claim *and* adding the arm

Each mark with a paint of its own is read in computed pixels against the tinted
ground **through the channel that paints it** (dot → `::after` background, "?" →
`::after` colour). All three wide claims rewritten to say *three* measurements, not
one. MB-3 (the inside re-fire of cycle 1's M7) **moved its kill cell** because the
pixel arm now precedes it — stated, not glossed.

Figures agree across **three** doors, the third new: token arithmetic, Chromium's
own computed values inside MB-1/MB-2's failure output (`rgb(241, 235, 221)`, mean
0.91111 — exact agreement, in a run the implementation never made), and **CIE L\***
perceptual lightness (ΔL\* 52.25 / 56.74 / 64.80, all past the ~20 that reads as a
visible step).

### The owner's editor decision, kept and tested

`TestSolverCrosshair_ReachesTheManualEditor`, two cells, in the **existing**
crosshair file, importing CARD-246's `_open_editor` rather than copying it. Both
assert **first** that they are on the editor page (`#puzzle-editor-save`, which
exists nowhere else), and **MD-3 reds that premise** when the cells are pointed at
the solve page — so neither can pass on the player page and claim the editor.
Living in the existing file, the only registry obligation is two new
`ADDED_SINCE_BEFORE` rows, **proved load-bearing by ME-1**. A new family file would
have forced a `PAGE_ISOLATION` row, an `ALONE_PROBES` entry and an encounter with
the frozen render set — avoided **rather than dodged by wording**.

- **AC-9** (edge, second consumer): *Given* the manual editor's page, *when* a cell
  is hovered, *then* that row, that column and their clue boxes carry the marker,
  and leaving the stage clears it. (test: `TestSolverCrosshair_ReachesTheManualEditor`.)
- **Design context → Screens** gains `/puzzle/<id>/editor` beside `/puzzles/<id>/solve`.
- **Scope, owner decision 2026-10-28:** the crosshair applies on **both** pages that
  load `solver.js`. That reach is **deliberate, not incidental.**

### F-007 declined with a measurement rather than an argument

Probed on AC-7's own scenario, instrument outside `tests/`: the screen point that
is cell **(5, 7)** at 1280×720 is cell **(4, 12)** after the mirror-breakpoint
redraw. Repainting the remembered `[row, col]` would put the crosshair on (5, 7)
**while the pointer sits on (4, 12)** — trading "no crosshair after a redraw" for
"a crosshair on the wrong cell", which is *nearer* to the stale marker AC-7 forbids
than today's `forget()`. A correct repaint needs client coordinates and a re-hit-test
— new state, new mechanism — and would invert AC-7's shipped assertion, which has a
kill. **Stays declared, as body item 6 permits.**

### F-009 not reproduced, and no sleep added

**21 runs, 21 green** (the named cell 15× alone, the whole file 6×, `--tb=long`,
no truncation). Slowest whole-file run 19.37 s against cycle 1's red at 22.52 s, so
load variance alone did not reproduce it. **No settle was added, because the
mechanism could not be explained** — an unexplained sleep is papering over. What was
added is independently justified: the leave test's premise is now the *full*
crosshair, so if cycle 1's plausible mechanism is real the next occurrence fails
**at the premise** with a readable message instead of looking like a leave defect.

### Gate — F-010 answered, with disjointness checked rather than assumed

**1074 collected / 1074 passed / 0 skipped / 0 failed** over **18 files, pairwise
disjoint by path**, in four invocations (47 + 260 + 422 + 345). That is the finding's
point: the paths are listed, `sort | uniq -d` is empty, and one `--collect-only -q`
over all 18 returns **1074** — a count of **distinct** tests, not a sum over an
overlapping union. `tests/test_suite_profile.py` ran and is green.

**One run abandoned with no verdict claimed:** a single 18-file invocation projected
≈34 min and would have run `test_browser_fixture_scope.py`'s 90 s-bounded child
pytests under its own load — the exact mechanism that turns contention into
failures. Killed, log renamed `…-ABANDONED-no-verdict.txt`.

### Card items retired by this round

The **"964 collected"** figure is retired for the 1074 above, whose domain is named
and whose disjointness is checked. The **validator note is retired**: worktree and
main now read the same figure, delta zero — cycle 1's +4 was merge-base drift the
merge absorbed. *Instrument note: this round read 1 error / 112 warnings; the
orchestrator's `forge_1` copy reads 0 / 112. The two validator copies on this box
disagree on the error count — a known split, not a tree change.*

### Could not establish, in the round's own words

F-009's red or its failing cell (21 runs, 21 green) · **the owner's eyeball on a
real render**, still owed by the Design context, figures now agreeing across three
doors · the full suite, not run by the brief · **whether the four `::after`
channels are exhaustive for future cell states** — a fifth state painted through an
`outline` or `box-shadow` would be outside the arm, stated so the narrowed claim is
not re-read as a wider one.


## [CYCLE 2 — 2026-10-28] **9.5 CERTIFIED** — 19 mutants, and the differential was reproduced in both directions

Report: `meta/review/20261028T175955Z-CARD-267-cycle2.yml`. Reviewed `1ef355c0` on
base `b74e9083`. **19 mutants: 16 killed, 2 survived by design (the differential
controls), 1 survived as the minor above.** System contract **5 checked, 5 ✓, 0 ✗**
— every ref verified alive by a `def`/`class` grep rather than by the validator's
verdict, and deliberately **not** with `git grep -w`. Validator **0 errors / 112
warnings on both worktree and main, delta zero**, confirming this card's
retirement of cycle 1's +4.

### The round's strongest claim reproduced — and then strengthened

Fix round 1's differential (MA-2 against the pre-fix test file **survives**, and
kills against the fixed one) **reproduced exactly**: 15 collected, 15 passed, exit
0, against the old side's own blob. **Cycle 2 then ran the differential in the
other direction, which the fix round had not:** M13 against the pre-fix file *also*
survives 15/15. So *"the fix is what makes it red, and the root cause is the state
rather than the mutant class"* is now measured on **two independent mutants**
rather than one.

And the new premise is a genuine per-field control, not a tautology: neutering the
drive state kills with all seven fields virgin, and an **edge** mutant dropping
only the trailing Undo kills naming the single offending field (`assert ['redo'] ==
[]`).

### M7's "moved kill cell" — real, benign, and sharpened

The line number genuinely moved +28 (`:270` → `:298`), but **the assertion is
byte-identical**, and the pixel arm does *not* intercept M7 — arm 2 reads only the
empty/maybe channels, which the filled override leaves alone — so the kill falls
through to the same assertion it always did. Nothing was relocated. The card's
sentence is true under the line-number reading and cycle 2 notes it would be
stronger saying so.

### Figures — a fourth door, and a chromatic one

Cycle 2 re-derived rather than re-ran: its own sRGB arithmetic reproduces
`--player-cross-ink` at mean `0.27095` with a luma gap of `0.64016` against the 0.4
bar, and CIE L\* agrees **exactly** at 52.25 / 56.74 / 64.80. **New fourth door:
CIEDE2000 ΔE = 44.55 / 50.89 / 57.92** — a *chromatic* metric none of the three
earlier doors used, all ~19–25× the 2.3 JND, computed in pure Python so no shared
code path.

### The three dispositions, judged

**F-007 sound and honestly declined** — body item 6 explicitly permits clearing, so
declining is *within* the contract, and the mechanism was confirmed in code: the
redraw fires only `if (isBig)`, and across AC-7's own transition the mirror query
flips row gutters 2→1 *and* the cell pitch re-fits, so `[row, col]`→screen-point is
broken by construction. (Cycle 2 **could not re-derive the exact (5,7)→(4,12)**
without a browser probe it did not build, and says so — the conclusion does not
rest on that figure.) **F-009 is a genuine premise strengthening, not a
relabelling**, and it is measured: the leave test now reds **at its new premise**
with "nothing to clear" instead of later at the leave equality, on the editor cell
too. It still does not fix the flake, and the card says so. **The editor cells were
placed on the merits**, confirmed on both halves — and cycle 2 asked the sharper
question the round had not: *do they measure anything of the editor, or only that it
loaded?* A mutant reds 10 of 17 cells **including both editor cells**, so they
genuinely measure the row, the column and both clue axes there.

### Measurement hygiene worth recording

**Every mutant run was a recording pass**, so a short-circuited assert cannot read
as a surviving mutant. **0 skips in every invocation** (crosshair 17, suite_profile
410, design_tokens 12, editor_ui 117). One exit-4 from a wrong node id was caught
and **no verdict claimed from it**. "Comment-only `src/`" was verified
**mechanically** — both files code-identical to base after comment stripping —
rather than by reading the diff.

### What the merge gate still owes

1. **The owner's eyeball on a real render.** The Design context asks for it by name
   and none has been seen. Four doors of figures now agree, but an instrument
   reading pixels is not an eyeball, and `--color-surface-hover` over
   `--color-accent` is the one thing only an eyeball settles.
2. **The full suite against a base re-merged from main.**
3. Nothing else.
