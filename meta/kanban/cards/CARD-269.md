# CARD-269: Hint ladder — point at the line, explain the deduction, and only then reveal; plus a Check for wrong marks

**Status:** in progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/269-hint-ladder
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-269
**Source:** quick — owner decision 2026-10-22 (player-convenience session: "propose more sophisticated hint" → ladder proposal approved); no handoff increment
**Idea:** —
**Wave:** 67 <!-- STAMPED 2026-10-30 on owner decision: paired with CARD-306 after CARD-308's merge closed wave 66. Chosen over CARD-268 (they overlap 0.86 on solver_state.js/solver.js/admin.css/tokens.css, so only one can run) and over CARD-216 (its core is a stored column plus a migration, and all 27 of this suite's skips are DATABASE_URL-gated, so its own verification would land skipping green on this box). -->
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_hint.py, tests/test_admin_design_tokens.py
**Review score:** **8.5 (cycle 2/3) — CERTIFIED**; cycle 1 5.5, cycle 2 8.5, **delta +3.0** against `min_improvement: 0.5`, 0 gating open. Two fix rounds.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why a ladder

CARD-183's Hint is a one-shot answer machine: one press reveals a cell. The
gentlest useful hint — "look at row 7" — does not exist, so a player who only
needs a nudge pays the full answer, and the row-major fallback reveal (AC-329)
teaches a wrong lesson: the player concludes they missed a line deduction when
in fact none existed. A ladder gives the same button three escalating answers
for the same situation, so the player chooses how much help to take; and a
separate Check answers the question Hint silently dances around today — "is
one of my marks wrong?" (`hintCell` ignores wrong marks but never says so).

## Declared semantics (decided before code, owner-approved 2026-10-22)

1. **One button, three rungs.** Pressing Hint escalates: rung 1 points at a
   line, rung 2 adds why, rung 3 reveals the cell (exactly today's behaviour).
   Any recorded change — a mark, a drag, undo, redo, a reset, and rung 3's own
   stroke — resets the ladder to rung 1. A page load starts at rung 1. The
   rung is player state like Region's flag: transition rules pure in
   `solver_state.js`, the value held in `solver.js`, never in a stroke, never
   in the history, never saved.
2. **Rung 1 — where to look.** The line (row or column) through the cell
   today's `hintCell` scan picks, chosen as the axis whose `lineForced` pass
   forces that cell (row first when both do). Its cells and its clue box(es) —
   both twins on a CARD-212 doubled axis — take a highlight
   (`.is-hint-line`), and the live region says "Hint: look at row N" (or
   column N). No cell changes, no stroke, "Hints: N" unchanged.
3. **Rung 2 — what to see.** Same line, same highlight; the live region adds
   the reason. A named case may be claimed only when its precondition is
   verified on the line, at minimum: *runs complete* ("every run in this row
   is placed — the rest is white": the line's correct filled marks already
   total the clue) and *overlap* ("the N-run must overlap in the middle
   whatever its position": the line holds no known marks at all). Every other
   situation gets the generic, always-true phrasing: "every placement of this
   row's clues agrees on at least one cell." The text must never state a
   reason the code did not check. No cell changes, no stroke.
4. **Rung 3 — reveal.** Today's hint, unchanged: the same cell, the same
   `hint: true` stroke, `.is-hinted`, the announce text of `hintText`, the
   counter up by one, one undo step, replay and save exactly as shipped.
5. **Coherence.** Because any board change resets the ladder, rungs 1–3 of one
   ladder always describe one situation: the line of rungs 1–2 contains the
   cell rung 3 reveals.
6. **Exhausted state** (undecided cells exist, none line-forced): rungs 1 and
   2 highlight nothing and announce "Hint: no single row or column decides a
   cell right now."; rung 3 is today's fallback reveal with its "(from the
   solution)" text. Suggesting a probe cell here is deliberately deferred to a
   follow-up after CARD-268 ships — this card changes no text when that lands.
7. **Check is a separate control**, next to Hint. With at least one wrong mark
   (a mark differing from the solution; "?" is never wrong), it highlights the
   row of the first wrong cell row-major and announces "Check: a mark in
   row N is wrong." — the row, never the cell. With none it announces
   "Check: no wrong marks." It changes no cell, records no stroke, moves no
   counter, resets the Hint ladder (it changes what the player will look at),
   and its highlight clears like rung 1's.
8. **Counting.** `hintCount` already counts only `hint: true` strokes, so
   rungs 1–2 and Check are free and "Hints: N" keeps meaning "cells I didn't
   deduce myself" — no change to the counter's code or semantics.
9. **Disabled states follow Hint's today:** board locked or no undecided cell
   → Hint is `aria-disabled` at every rung; Check is `aria-disabled` when the
   board is locked. Neither control exists in edit mode (the solution there is
   the grid being rewritten — `nextHint` already answers null; Check must be
   absent for the same reason).
10. **Supersession, named.** This card supersedes three shipped clauses of
    FR-044's hint ACs: AC-327's "when Hint is pressed … exactly one cell
    changes" (now the *third* press), AC-329's fallback reveal on the first
    press (now rung 3, with rungs 1–2 saying the truth), and AC-334's "each
    press reveals one cell" (three presses are now one ladder, one reveal).
    AC-328, AC-330, AC-331, AC-332, AC-333 and AC-335 are unchanged in
    substance — AC-335's no-animation rule extends to the line highlight.
    The FR-044 amendment goes through `inputs/raw-requirements.md` on the
    architect side (the AC-303/AC-304 supersession is the precedent); this
    card does not edit `requirements.yml`.

## What to implement

**Current behaviour (verified by reading the code).**

- `solver_state.js`: `lineForced(clue, cells)` is a full line intersection
  (forward/backward reachability; every placement must agree) — not a
  heuristic; `hintCell(board, rows, columns, solution)` scans row-major for
  the first undecided cell forced by its row's or column's `lineForced` over
  the player's *correct* marks, else falls back to the first undecided cell
  with `deduced: false`; `hintStroke` tags the stroke `hint: true`;
  `hintCount` counts those on the undo stack.
- `solver.js`: `[data-player-action="hint"]` records the stroke, `.is-hinted`
  marks the cell until the next commit, `hintText` writes the live region
  (`#puzzle-player-announce`), `[data-player-hints]` shows the count; in edit
  mode `nextHint` answers null and the button is not rendered.
- Tests: `tests/test_puzzle_solver_hint.py` holds all ten hint classes
  (module, reveal, placement, wrong marks, fallback, undo, solve+lock,
  disabled, keyboard/no-request, reduced motion).

**What changes.**

1. `solver_state.js`: the pure half of the ladder — the rung transition
   (press → what happens, reset events), the rung-1/2 line choice for a
   `hintCell` result, the rung-2 classifier with its two named cases and the
   generic fallback, and Check's first-wrong-row scan. Each a function of its
   arguments, testable via `await import('/static/solver_state.js')`.
2. `solver.js`: the ladder value and its resets beside the Region flag; rung
   rendering (`.is-hint-line` on the line's cells and clue twins, cleared on
   reset), the three announce texts, the Check button wiring and its
   highlight/announce.
3. `puzzle_solve.html`: the Check button in the History group after Hint; the
   template's hint comment paragraph updated to describe the ladder.
4. `tokens.css`/`admin.css`: the line-highlight tint, tokens only, visually
   distinct from `.is-hinted`, CARD-188's circles and (if present by then)
   CARD-267's crosshair; no animation under `prefers-reduced-motion`.
5. `tests/test_puzzle_solver_hint.py`: adapt exactly the three superseded
   classes (`TestSolverHint_RevealsOneCell` presses three times,
   `TestSolverHint_FallsBackToTheSolution` walks the exhausted ladder,
   `TestSolverHint_KeyboardAndNoRequest` operates the full ladder by
   keyboard); add the new classes below. No other existing test file changes,
   except the per-rule token check joining `tests/test_admin_design_tokens.py`.

## Acceptance criteria

- **AC-1** (happy, rung 1): *Given* a blank 15×15 player page, *when* Hint is
  pressed once, *then* no cell changes, "Hints: 0" stays, the line through the
  cell `hintCell` picks carries `.is-hint-line` on its cells and its clue
  box(es), and the live region says to look at that line. (test:
  `TestSolverHintLadder_FirstPressPointsAtALine`)
- **AC-2** (happy, rung 2): *Given* rung 1 shown, *when* Hint is pressed
  again, *then* still no cell changes and the live region carries a reason —
  the named case only when its precondition holds on that line, the generic
  phrasing otherwise. (test: `TestSolverHintLadder_SecondPressExplains`)
- **AC-3** (happy, rung 3): *Given* rung 2 shown, *when* Hint is pressed a
  third time, *then* exactly the cell the ladder's line contains is revealed
  as today — `hint: true` stroke, `.is-hinted`, "Hints: 1", one undo step —
  and the ladder is back at rung 1. (test:
  `TestSolverHintLadder_ThirdPressRevealsTheSameSituation`)
- **AC-4** (edge, reset): *Given* rung 2 shown, *when* the player marks any
  cell (or presses undo, redo, or Check), *then* the next Hint press is rung 1
  again, and the old line highlight is gone. (test:
  `TestSolverHintLadder_AnyChangeResetsTheLadder`)
- **AC-5** (edge, exhausted): *Given* a board whose undecided cells are not
  deducible from any single line, *then* presses one and two highlight nothing
  and announce that no single row or column decides a cell, and press three
  reveals with the shipped "(from the solution)" announcement. (test:
  `TestSolverHint_FallsBackToTheSolution`, adapted)
- **AC-6** (happy, Check wrong): *Given* a board with wrong marks, *when*
  Check is pressed, *then* the row of the first wrong cell row-major is
  highlighted and announced by row number only, no cell changes, no stroke is
  recorded, and both counters are unchanged. (test:
  `TestSolverCheck_NamesTheFirstWrongRow`)
- **AC-7** (edge, Check clean): *Given* a board with no wrong marks ("?" marks
  present), *when* Check is pressed, *then* it announces no wrong marks and
  highlights nothing; *given* a locked board, Check reports
  `aria-disabled="true"`; *given* edit mode, Check is absent. (test:
  `TestSolverCheck_CleanLockedAndEditMode`)
- **AC-8** (edge, honesty): *Given* a line whose runs are not all placed,
  *then* the "runs complete" phrasing never appears for it; *given* a line
  with any known mark, *then* the "overlap" phrasing never appears for it —
  each named case's precondition checked in the pure module, both directions
  (claimed when true, generic when false). (test:
  `TestSolverHintLadder_TheReasonIsNeverALie`)
- **AC-9** (edge, nothing persists): *Given* any ladder position and a Check
  press, *then* the localStorage save equals byte-for-byte the save of the
  same marks without them, and a reload starts at rung 1. (test:
  `TestSolverHintLadder_NeitherRungNorCheckIsSaved`)
- **AC-10** (edge, a11y + tokens + no request): *Given* the shipped page,
  *then* the whole ladder and Check operate by keyboard with accessible names
  ("Hint", "Check"), issue no network request, animate nothing under
  `prefers-reduced-motion` (line highlight included), and the new CSS takes
  every color from tokens with a per-rule check. (tests:
  `TestSolverHint_KeyboardAndNoRequest` adapted, `TestSolverHint_ReducedMotion`
  extended, `test_the_hint_line_tint_comes_from_tokens`)

## Guardrails

- G-1: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-2: No request per press — Hint at every rung and Check make no network
  request (ADR-0038/R2; AC-10, and `TestSolverMarking_NoRequestPerMark` runs
  unedited).
- G-3: Rung-3's stroke, replay, undo and save behaviour are byte-compatible
  with CARD-183's: `hintStroke`, `savedStroke` and `SAVE_VERSION` unchanged, a
  save written by today's player loads unchanged and vice versa.
- G-4: `CELL_STATES` is not extended; `hintCell` and `lineForced` keep their
  signatures and semantics (the ladder *wraps* them — AC-328's
  wrong-marks-ignored behaviour must hold at every rung).
- G-5: AC-330, AC-331, AC-332, AC-333 and AC-335 keep passing with their
  classes unedited except where this card's supersession list names them;
  among existing test files only `tests/test_puzzle_solver_hint.py` and
  `tests/test_admin_design_tokens.py` change.
- G-6: Styling from tokens only (test:
  `test_the_stylesheet_uses_tokens_not_literals`, plus the per-rule check in
  AC-10).
- G-7: Play state stays browser-local (CON-021); the rung and Check leave no
  trace in localStorage (AC-9).
- G-8: Do not implement the probe-cell suggestion (semantics rule 6 defers
  it); the exhausted-state text ships as written there.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R3 — clues are the embedded JSON of `compute_clues`; the client
  never re-derives them (check: `TestSolverPage_ShowsTheClues`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- ADR-0038/R6 — only the admin player, behind the CON-015/CON-016 door, ships
  the solution to the browser; Check is a new *reader* of it inside the same
  page, not a new shipper (check: review-lens)
- CON-021 — play state persists only in this browser's localStorage, per
  puzzle; nothing server-side (check: review-lens)

## Architecture context

- **FR:** FR-044 — this amends the Hint behaviour CARD-183 shipped
  (AC-327..AC-335, EC-042). The supersession is named in semantics rule 10;
  the owner decision of 2026-10-22 goes through `inputs/raw-requirements.md`
  on the architect side — this card does not edit `requirements.yml`, and its
  ACs above are the card-local statement the gate holds onto (quick-card
  rule).
- **ADR:** ADR-0038/R1–R4, R6.
- **CON:** CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; every value is
  a token (G-6).
- **UI components:** the History group gains the Check button after Hint
  (AC-333's order claim must stay true — Check goes after Hint, and the AC's
  "Hint is the last control" clause is part of what the amendment supersedes
  if the review reads it strictly: surface it, don't pick silently);
  `.is-hint-line` on existing cells and clue boxes, no new elements on the
  board.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** real buttons, accessible names, announcements through the
  existing live region only; reduced motion honoured; owner validates the
  look and the three announce texts on a real puzzle render before merge.

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (all in `tests/test_puzzle_solver_hint.py` unless noted;
line numbers at drafting):

| name | resolves to |
|------|-------------|
| `TestSolverHintModule` | `:442` (extend with the pure ladder/classifier/Check tests) |
| `TestSolverHint_RevealsOneCell` | `:518` (adapt — three presses) |
| `TestSolverHint_PlacesTheButtonAndTheCounter` | `:592` (extend — Check placement) |
| `TestSolverHint_IgnoresWrongMarks` | `:626` (unedited) |
| `TestSolverHint_FallsBackToTheSolution` | `:663` (adapt — exhausted ladder) |
| `TestSolverHint_IsOneUndoableStroke` | `:689` (unedited) |
| `TestSolverHint_CanSolveAndThenLocks` | `:741` (unedited) |
| `TestSolverHint_DisabledWithNothingToReveal` | `:779` (unedited) |
| `TestSolverHint_KeyboardAndNoRequest` | `:837` (adapt — the full ladder) |
| `TestSolverHint_ReducedMotion` | `:886` (extend — the line highlight) |
| `TestSolverPage_ShowsTheClues` | `tests/test_puzzle_solver_page.py:206` |
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** — none exists yet; report them as written,
never as passing before they exist:
`TestSolverHintLadder_FirstPressPointsAtALine`,
`TestSolverHintLadder_SecondPressExplains`,
`TestSolverHintLadder_ThirdPressRevealsTheSameSituation`,
`TestSolverHintLadder_AnyChangeResetsTheLadder`,
`TestSolverHintLadder_TheReasonIsNeverALie`,
`TestSolverHintLadder_NeitherRungNorCheckIsSaved`,
`TestSolverCheck_NamesTheFirstWrongRow`,
`TestSolverCheck_CleanLockedAndEditMode`,
`test_the_hint_line_tint_comes_from_tokens`.

## Worktree notes

- **[Semantics first]** The "Declared semantics" block is the decided
  contract; divergence is recorded beside it with its reason, never edited
  into it (CARD-262's rule).
- **[AC-333 reading]** AC-333 says "Hint is the last control of the History
  group". Adding Check after Hint makes that sentence false under a strict
  reading. The ladder supersession (rule 10) should name this clause too in
  the raw-requirements delta; the card's own placement claim (Design context)
  is the one the gate holds. Surface it in cycle 1 rather than arguing either
  reading silently.
- **[Classifier scope]** Two named cases plus the generic fallback is the
  floor, not the target — more named cases are welcome, but each must carry a
  verified precondition and an AC-8-style both-directions test, or it ships
  as the generic phrasing. A reason that can lie is worse than no reason.
- **[Conflict note]** Touches overlap CARD-267 (crosshair: `solver.js`, CSS,
  template) and CARD-268 (probe: those plus `solver_state.js`); the
  dispatcher's overlap prediction will serialize whatever lands in one wave.
  The follow-up this card defers — the exhausted-state hint suggesting a
  probe cell — becomes draftable only after CARD-268 merges.

---

## Implementation — `560d7e09` → `abebc70b`, 8 files, +1895/−65

**The ladder wraps CARD-183's reveal rather than replacing it.** `hintCell`, `lineForced`
and `hintStroke` are untouched (G-4). The pure half in `solver_state.js` is a **frozen
transition table** — `nextRung(rung, event)` raises `RangeError` on an unknown rung or
event rather than falling through — plus `knownLine()` built from **correct marks only**,
so rungs 1–2 cannot drift from the cell rung 3 reveals. `hintLine()` returns **null in
exactly one case**: the hint is not a *deduced* cell. **That null is the exhausted state**,
and it is the whole mechanism by which the fallback stops lying.

### How the wrong lesson stops being taught, with the measurement

When `hintLine` is null, rungs 1 and 2 highlight **nothing** and say *"no single row or
column decides a cell right now."* Rung 3 is CARD-183's reveal with its shipped
*"(from the solution)"* wording, byte for byte.

**Two separate claims, two separate assertions**: the sentence, **and**
`_lined(page) == {cells: [], rowClues: [], colClues: []}` — because a reworded sentence
with a highlighted line still under it would be pointing at a deduction that does not
exist. **Mutant M5 is the proof that pair is load-bearing**: it makes rungs 1–2 claim a
row on the exhausted board — the precise falsehood this card exists to remove — and reds
**only** that one cell while its two siblings stay green.

**Nine mutants, all deletion-or-one-line**, needle asserted unique, blob sha printed
before/mutated/restored (all restored OK), `__pycache__` swept both ways, every instrument
green on the unmutated tree first. Each AC-level class also carries its **own in-test
negative control** — a deducible board that *does* get a line, two presses with nothing
between them that *do* climb, rung 3 that *does* change the save.

**29 node ids added, 0 removed, 0 renamed, 0 merged. Zero skips** (`-rs` printed nothing
across a 545-test selection). Runtime as ranges: the two card files 41–43 s, the 11-file
affected selection 346–365 s.

### It caught a blind instrument of its own

Its first captures were taken **the instant after the press — mid-fade** — so the tint read
as barely there, and it deepened the colour on that reading. **The instrument was wrong,
not the colour**: with `getAnimations()` settled, the design-system token
`--color-accent-tint` reads clearly. It reverted to the token, kept both sets for the owner
to compare, and **wrote the trap into the `admin.css` comment** so the next eyeball of that
colour waits for the animation. That is the day's dominant failure family — a reading taken
before the quantity existed — caught by the round on itself.

### Three corrections to this card

- **The card's "unedited" list is wrong for four classes.** `TestSolverHint_IgnoresWrongMarks`,
  `_IsOneUndoableStroke`, `_CanSolveAndThenLocks` and `_TheHighlightSurvivesARedraw` all
  press Hint once and expect a reveal, so **all four fail under the ladder**. Adapted
  mechanically through one `_reveal()` helper, no assertion weakened. **The superseded set
  is seven classes, not three.**
- **G-5's blast radius is wrong** — two further existing files had to change
  (`test_puzzle_solver_maybe.py`, `test_puzzle_solver_percent.py`), both marked in place as
  unforeseen by the card.
- **The "both halves" claim about the runs-complete precondition is over-stated**: the
  second half cannot fail on its own, because once a placement exists and the marks total
  the clue, every placement fills exactly the marked cells. The check was kept — the
  sentence says it, so the code saying it should check it — with an honest note instead of
  a comment implying two independent guards.

### Divergences chosen and recorded, not hidden

Pure ladder tests went in a **sibling class** rather than extending
`TestSolverHintModule`, so each class docstring stays true about which card it covers. A
ladder press and a Check press now clear `lastClick` — they are *inputs*, the rule the
reset confirmation already follows — which is semantically right **and** keeps
`test_puzzle_solver_marking.py` untouched.

**And one player-visible gap is owed as a follow-up**: the on-page usage paragraph does not
mention the ladder, because `test_the_page_copy_describes_the_new_click` pins it by exact
equality and the card forbids editing that file. The round **reverted its own copy
addition** rather than edit a forbidden file. A one-sentence on-page copy change is owed.

### CARD-263's path, clarified — report only

`nextRung(rung, event)` takes the rung as an argument rather than reading a global, and
`HINT_RUNGS`/`RUNG_EVENTS` are an enumerable authority the announce table is checked
against — so CARD-263 slots in as **a second ladder on Check**, reusing `nextRung`
unchanged and `firstWrongRow` as its rung-2 scan. **The one thing CARD-263 must decide,
which this card did not**: `Errors: N` is a live `role="status"` region updated on every
mark, so making the count cost a press means **hiding or freezing that counter** — a change
to CARD-162's shipped behaviour that needs an owner decision, not just a rung. `errorCount`
and the counter were not touched.

### TWO ITEMS ESCALATED TO THE OWNER — see the board entry

1. **A visible layout change at 1280 px.** 2. **AC-333 is now false under a strict reading.**

### OWNER DECISIONS 2026-10-30

**1. The taller toolbar at 1280 px is ACCEPTED.** Measured: the counters need **268 px**
on one line and Check leaves them **186** — short by **exactly Check's own 82 px** — so the
Progress group wraps onto its own row at 1280 and the toolbar goes 187 px → **223 px**.
1440 px still fits all three. This is the pre-CARD-194 arrangement returning at a common
width, and the owner had accepted the current one, which is why the round escalated it
instead of letting it pass as incidental.

The round asserted the layout **as it now is** and added a **1440 px control**, so the
test proves a *threshold moved* rather than a layout broke — the distinction that keeps
this from reading as a regression later. The captures at both widths are in
`~/Documents/nonogram-reviews/CARD-269/`, including an A/B of a deeper tint that was
**tried and rejected**.

**2. AC-333 is amended to name Check**, applied on this branch at `bcd136b5`. The retired
clause read *"Hint is the last control of the History group, after Reset"*, and Check's
arrival made it false under a strict reading. The owner chose to let the **requirement
follow the design decision** the card's own Design context already specified, rather than
relocate the button. The counter half is deliberately untouched: the 1280 threshold moved,
but `"Hints: N"` still follows `"Errors: N"` on one row.

**The `test:` ref was checked rather than assumed, and it is NOT dead** — it names the
*class* `TestSolverHint_PlacesTheButtonAndTheCounter`, which survives at
`tests/test_puzzle_solver_hint.py:777`; only its internal method names changed
(`hintIsLastChild` → `checkIsLastChild` + `checkFollowsHint`). A renamed ref that still
reads alive is the defect class CARD-308 and CARD-319 exist for, so the check was made
before the amendment rather than after.

**Still owed as a follow-up, and not this card's to take:** the on-page usage paragraph
does not mention the ladder, because `test_the_page_copy_describes_the_new_click` pins it
by exact equality and this card forbids editing that file. The round **reverted its own
copy addition** rather than edit a forbidden file. One sentence, player-visible, owed.

---

## Review cycle 1 — **5.5 / 10, NOT CERTIFIED** (`min_score: 8`), 3 gating

`meta/review/20261029T222119Z-CARD-269-cycle1.yml`. Eleven findings, thirteen judgements.

### F-1 (gating) — the branch is red, and the round did not know

`tests/test_puzzle_solver_resume.py` is **15/15 at the base `560d7e09`** and **13/15 at
`bcd136b5`**, deterministic across two runs and reproduced inside a 12-file selection.
`test_reload_restores` and `test_saves_every_change` each press Hint **once** and assert the board
or the localStorage entry changed; **under the ladder, one press changes neither.**

**This is the round's own correction-1 class in a THIRD file.** The card says *"G-5's blast radius is
wrong — two further existing files"*; it is wrong by **three**, and the third was left failing. The
second failure is **the save**, which **G-3 and AC-9 are both about.** And the derivation was
available: `grep -rln '"Hint"' tests/` returns **seven** player files that press the button, and it
names `resume.py`. **The round's "11-file affected selection" excluded it** — a selection, not a
derivation, which is the defect under the two reds.

### F-2 (gating) — rung 2 is invisible to a sighted player. **WITH THE OWNER.**

`#puzzle-player-announce` is a **1×1 clipped region**, measured 1×1 live. By **SHA-256 of element
screenshots with `getAnimations()` settled**, rung 2's board and toolbar are **byte-identical to
rung 1's** — and the instrument was proved first: rung 1 *does* differ from blank, rung 3 from both.
The class toggle off/on **coalesces in one task**, so there is not even a re-fade, and under reduced
motion there is no animation at all.

So **the rung whose job is "explain the deduction" — half the card's title — changes nothing a
sighted player can see.** On the exhausted board **rungs 1 and 2 both** show nothing; **Check on a
clean board** shows nothing. CARD-183's Hint always did something visible on every press; the ladder
introduces **presses indistinguishable from a dead button.** The one visible channel, the line tint,
is **1.15:1** against the paper — under **WCAG 1.4.11's 3:1** — and carries **two meanings** (rung 1
vs Check) with only the hidden sentence to separate them.

**And all ten ACs are phrased "the live region says…", so they pass while the feature does not reach
the player.** That is the shape the board has been correcting all day, in the acceptance criteria
this time.

The reviewer's answer to the asked judgement: **shipping with no on-page mention is not acceptable,
and not as documentation debt** — the on-page paragraph is the only remaining channel that could
explain two presses with no visible effect. Reverting the copy rather than editing a forbidden file
was still the right call.

### F-3 (gating) — the supersession is recorded nowhere executable

**AC-327, AC-329 and AC-334 are live and unamended in `requirements.yml`, each now false of the
shipped code**, and each carries a `test:` ref that **resolves to a live class now asserting the
opposite**. CARD-308/CARD-319's defect class one level up: **ref alive, requirement dead.**
`inputs/raw-requirements.md`, where the card routes the FR-044 delta, was **never touched** — while
`bcd136b5` **does** edit `requirements.yml`, **which the card forbids itself twice.** Fix round 1
writes the delta; the three amendments are owed and are the owner's, as AC-333's was.

### F-4 (important) — the evidence for an owner decision does not exist

The card claims captures at both widths. **All 20 are 1280 px. There is no 1440 px capture**, and
`announcements.txt` states the toolbar shown *"is NOT the shipped layout"*. **So the owner accepted
the 1280 px layout change on evidence that is not there** — and the figures *were* right
(268 / 186 / 82 / 1440-fits-all all re-derive exactly, 82 two ways), so this is a missing-artefact
defect, not a wrong-measurement one. Surfaced to the owner; fix round 1 produces the real captures.

### Answers to the brief's questions

- **`hintLine()`'s null: behaviourally one case, structurally three.** `hint === null` (unreachable
  from the UI), the fallback (the real exhausted state), and **"neither axis forces it"** — the
  *"I could not tell"* null, unreachable **only because `knownLine` duplicates `hintCell`'s
  projection by hand.** Measured: **mutating that projection passes every page test**; only the 1×3
  unit assertion reds. **The card's whole promise rests on those two nulls being the same thing, and
  today they are the same only by a duplication nothing guards.** G-4's *"AC-328 holds at every rung
  by construction"* has **no control**.
- **Drift rungs 1–2 → rung 3: none.** `commit()` is the single choke point; all seven call sites
  traced including `setBoard` → `marking.commit`, and `editing` is a `const`. **Sound.**
- **Enumerable authority: partly, and the card misattributes it.** The working authority is
  **`HINT_REASONS`**, not `HINT_RUNGS`/`RUNG_EVENTS`. **`LADDER_REASON` is not exported**, so both
  comments claiming *"the suite asserts these keys ARE `HINT_REASONS`"* assert something **no test
  can perform**. Second lists do exist: `RUNG_AFTER_PRESS`, the test's `_REASON_SENTENCE`,
  `knownLine`, and an underived rung ternary. **One unreachable row, `(3, "press")`** — an
  unreachable row is an untested row.
- **M5 reproduces exactly**, reddening only the one cell with seven siblings green — **and its pair
  is genuinely two independent assertions**, measured: the converse mutant reds the *second* having
  **passed** the first. The card's strongest claim survives intact.
- **The four adapted classes weakened no assertion**, several strengthened. **The superseded set
  really is seven.**
- **The runs-complete third correction is RIGHT**: deleting the second half leaves 53/53 green — a
  permanent surviving mutant, honestly noted, and the note is the right form.
- **The five toolbar numbers re-derive exactly**, and **the 1440 control does achieve the
  threshold-moved-not-broken distinction** — the same inequality is false at 1280 and true at 1440.
  But **187 → 223 are bottom-edge coordinates, not heights**; the real heights are **39 → 75 px**,
  mislabelled on this card, in `admin.css` and in the test docstring.
- **AC-333's ref resolves to a real `class` line**, exactly as the card claims; `hintIsLastChild` is
  gone and the amended `then:` is genuinely asserted. **The check made before the amendment was
  sound.** Residue: that class's docstring is now stale.
- **The colour claim holds**: the shipped capture samples **`#e6efec`, exactly
  `--color-accent-tint`**, and `tokens.css` is byte-identical to `meta/design/tokens.css`. The
  round's `getAnimations()` self-catch was right.
- **CARD-263's path is report-only**, `errorCount` and the counter untouched. Confirmed.

### Also measured wrong in shipped code, and one figure of the round's

- **"Assigning the SAME string is a no-op in the DOM" is false** — a MutationObserver records the
  identical assignment, so the stated rationale does not hold.
- **Check reads `aria-disabled="false"` mid-drag while its handler silently returns**; Hint reads
  `"true"`.
- `8 files +1895/−65` and **29 node ids added, 0 removed/renamed/merged (94 → 123)** re-derive, zero
  skips across every run, both unforeseen files marked in place. **The two card files measured
  36.4 s, below the card's stated 41–43 s** — a band exceeded in the *low* direction, which is the
  day's third card to do that.

### Strengths the review named

The **1800-line seeded reason corpus with counted near-misses and independent re-verification of the
module's own claims**; the exhausted pair; the 1440 discriminator; in-test negative controls
throughout; and the `getAnimations()` self-catch written into `admin.css` so the next eyeball of that
colour waits for the animation. **The ladder does remove the falsehood it set out to remove.**

- [Review 1/3] Score: 5.5 ✗ below threshold, 3 gating findings
- [Fix 1] Dispatched on F-1, F-3, F-4, F-5, F-6, F-7, F-8, F-9, F-10. **F-2 excluded and escalated**
  — a visible channel for rung 2 is a player-facing design decision with an accessibility dimension,
  and the on-page copy sentence it depends on is already owed to the owner.

---

## Fix round 1 — `bcd136b5` → `ef5e03af`, 5 commits, branch **GREEN**

Branch now **11 files, +2225/−76**; this round **+355/−52**. `requirements.yml` **byte-unchanged by
this round**. F-2 deliberately untouched: no visible channel designed, no copy paragraph edited, tint
unchanged. Lock absent for the whole round, no refused run, no 0-collected run banked.

### F-1 — fixed, and the derivation was the defect under the two reds

**The review's own derivation was wrong twice**: `grep -rln '"Hint"' tests/` returns **six** files,
not seven, and one of the six is `test_puzzle_editor_ui.py`, the **editor** file. So the round built
a wider, defensible union instead — *(anything pressing or reading Hint/Check)* ∪ *(anything
asserting the toolbar's layout, because **Check is a new button in the toolbar**)* = **13 files**,
one of them a derivation false positive **kept in the run so the exclusion is measured rather than
asserted**.

| tree | result |
|---|---|
| base `560d7e09` | **511 passed, 0 failed, 0 skipped** |
| `bcd136b5` | **2 failed, 538 passed** |
| HEAD `ef5e03af` | **540 passed, 0 failed, 0 skipped** |

**The two reds reproduce exactly, are exactly the two the review named, and nothing else in the
13-file set was red** — so the derived set is wide enough *and* the review's attribution was right.

Fixed through a local `_reveal()` helper at **three** press sites, not two: the two reds plus one in
`TestSolverResume_ResetClearsTheSave` that **passed either way but whose Hint press had silently
become a no-op**, so it no longer put a hint stroke in the save its own assertions walk. Every
assertion unchanged. **The fix is load-bearing, measured**: one site back to a single press reds
`test_saves_every_change` and nothing else. **G-5's blast radius is wrong by three existing files,
not two**, and the adapted set is **12 classes across 4 files**.

### F-3 — the delta is where the card routes it

`meta/architecture/inputs/raw-requirements.md` gains an 85-line delta naming **AC-327, AC-329,
AC-334** one by one — what each `then:` still says, what the code does, **the live class that now
asserts the opposite**, and the amendment owed — plus **AC-335's owed extension** (the rule extends
to the line highlight; the test already asserts it, the AC does not) and **AC-328** recorded as
unchanged in substance but now *structurally* guaranteed by the F-7 fix. **The three ACs were not
amended** — those are the owner's, as AC-333's was. And the question I asked it to answer:
**`bcd136b5`'s `requirements.yml` edit does NOT exceed the owner's AC-333 decision** — the diff is
exactly that one `then:` line plus its comment block, touching no other id.

### F-4 — the captures the card claimed, now actually taken

Confirmed with PIL that **no 1440 px capture existed** and that `announcements.txt` did say the
toolbar shown was not the shipped layout. New: `10-shipped-layout-1280px-{fullpage,toolbar}.png`
(980×**75**) and `11-shipped-layout-1440px-{fullpage,toolbar}.png` (1140×**39**).

**The discipline is asserted, not just followed**: the probe awaited every animation's `finished`,
then **asserted `getAnimations()` was empty**, **asserted two consecutive measurements byte-identical**,
and **asserted the announce region was in its shipped 1×1 clipped state** — nothing was made visible
or restyled to take them. 00–09 kept; the caveat is now scoped to them. **The owner has re-confirmed
on these**, and they show something neither the card nor the review recorded: **the wrap reorders the
counters.** At 1440 they read *Progress · Errors · Hints*; at 1280 the top row is *Errors · Hints*
and **Progress drops to the second row**, so the first counter becomes the last read.

### F-5 — and the figures cycle 1 *certified* do not re-derive

**187 → 223 are bottom-edge coordinates**; the real heights are **38.797 → 74.797 px**, top `y=148`,
identical at 1280×900 and 1280×720, and confirmed by a **second independent instrument** — the
element screenshots' own crop heights, 75 and 39. **`admin.css` never carried 187/223**; one code
site, not two, so F-5's own claim was wrong there.

Then the larger one. Cycle 1 called 268 / 186 / 82 *"exact, 82 confirmed two ways"*. Measured:
- one line of `.player-counters` **needs 263.66 px** — the rule's column-gap is **16 px, not the 20
  cycle 1 used**, which is how that sum landed on a different quantity and still looked exact;
- **268 is not a need at all** — 267.59 px is the width the flex layout *gave* the counters at 1280
  without Check, 186.23 with it;
- **Check costs 81.36 px**, not 82 (its 73.36 px box + the group's 8 px gap); 82 is the difference of
  two already-rounded widths, and **the "second way" is the same rounding on another pair** — real
  widths 359.22 and 440.58, difference 81.36. **It repeated the derivation rather than checking it.**
- **The threshold claim survives in figures that reproduce**: 267.59 ≥ 263.66 fits; 186.23 is short by
  **77.43 px** so Progress wraps; 346.23 ≥ 263.66 fits at 1440. **The test asserts inequalities on
  positions and was always right — only the prose was wrong.**

And it caught **its own blind instrument** doing it: setting `style.width='max-content'` on a flex
item with `flex:1 1 0` **returns the given width unchanged**. Replaced with a children-plus-gap
measurement before anything was committed.

### F-6, F-7/G-4, and the small ones

`LADDER_REASON` is now `export const` and asserted against `HINT_REASONS` **both directions**, so the
two comments claiming that **are true for the first time**. The underived rung ternary became an
exported, asserted map — a rung with no entry is a `RangeError` at the press rather than silently
rendering rung 2's text. `RUNG_AFTER_PRESS` is **derived** from `HINT_RUNGS`, which also disposes of
**F-8's unreachable row**, and its comment now attributes the real 3→1 step to `commit()`'s
`"change"`, which is what does the work. The test-side sentence map is **declared a deliberate second
list with its reason** — the player-facing wording is what that file exists to pin, and importing the
shipped map could only confirm the page says what the page says. Attribution fixed in code:
**`HINT_REASONS` is the authority; `HINT_RUNGS` keys nothing in the announce path.**

**F-7/G-4 — the control that reds now exists.** `hintCell` projects **through** `knownLine` instead
of a five-line copy, so the no-drift property is structural. Measured both sides: at `bcd136b5` the
projection mutant reds **only** the pure-module test — **52 page tests pass, AC-328's own class among
them**; at HEAD the same mutant **also reds `TestSolverHint_IgnoresWrongMarks`**, and it bites
because that class deliberately picks a board where face-value reading gives a *different* hint.
Negative control: a semantically identical rewrite leaves all 12 green.

**`hintLine`'s three nulls are now written apart**, and the third — a deduced cell no axis forces —
**is no longer a null at all but an asserted impossibility (`RangeError`)**, because a player could
not tell it from the exhausted state. Asserted with its own control: a hand-built deduced hint
throws, while the real result on the *same* board still returns the exhausted null. **That closes the
structural gap cycle 1 named: the two nulls are no longer the same thing by a duplication nothing
guards.**

F-9's false "no-op in the DOM" comment is struck for what is true; F-10's Check now carries
`locked || gesture !== null` like Hint, with Hint as the in-test positive control and a mutant that
reds exactly that test; the stale docstring no longer says AC-333's clause is undecided.

### Figures

**Node ids: base 109 → HEAD 138 over the five changed files, +29 added, 0 removed/renamed/merged** — **CORRECTED by fix round 3: the implementation's share is 28, not 29.** Measured per-commit against the merge base and cross-checked per id with `git log -S`: **28 from the implementation + 7 from fix round 2 = 35** added to the browser family. —
and **this round added 0 and removed 0**, `comm` empty both directions. The card's 94 → 123 over four
files plus resume.py's constant 15 gives the same +29/−0. **Skips: none, and `-rs` printed no skip
section in any of the four whole-set runs.** Runtime **28.9–29.9 s** for the card's two files on an
idle box, against the card's stated **41–43 s** and cycle 1's **36.4 s** — *"all three are probably
real under different load, which is the point"*; the card's range needs its conditions. Whole set
**284–349 s**. No load figure. The card's `8 files +1895/−65` re-derives exactly.

### Five things it measured wrong in the review or my brief

1. `grep -rln '"Hint"' tests/` returns **6**, not 7, and one is the editor file.
2. F-5's *"mislabelled in `admin.css`"* — `admin.css` never carried those numbers.
3. **268 / 186 / 82 do not re-derive as stated**, and *"confirmed two ways"* was the same rounding
   twice.
4. `bcd136b5`'s `requirements.yml` edit does **not** exceed the owner's decision.
5. The announce region's line number shifted by 5; the review's number was right at `bcd136b5`.

It also hit the documented zsh word-splitting trap once, produced a 0-collected run, **and reported
it as what it was rather than as green.**

- [Fix 1] `ef5e03af` — F-1 and F-3 closed, branch green at 540 passed; every should-fix and
  nice-to-have addressed; three figures cycle 1 certified measured wrong and corrected in code.

## OWNER DECISIONS 2026-10-30 (second pair)

**3. Rung 2 gets a VISIBLE sentence on the page.** The announce text is promoted into a real visible
line near the toolbar, so **every press changes something seen as well as spoken** — and that also
settles the tint's two-meanings problem, since the sentence is what separates rung 1 from Check. The
tint is **not** being recoloured; its measured **1.15:1 against the paper, under WCAG 1.4.11's 3:1**,
is to be declared as a residual with the reason it is acceptable — the tint now reinforces rather
than carrying meaning alone. **This decision unblocks the owed on-page copy sentence**, which fix
round 1 correctly refused to take.

**4. The 1280 px layout is re-confirmed on real captures**, not on the arithmetic alone — the owner
chose to look at the thing they had accepted, since the artefact cited for it had not existed.

- [Fix 2] Dispatched on F-2 with decision 3 in hand. **The property to assert is "every press changes
  something a sighted player can see", not "the live region says…"** — all ten ACs are phrased the
  latter way, which is exactly why they passed while the feature did not reach the player.

---

## Fix round 2 — `ef5e03af` → `d22f1de0`. **F-2 closed; all three gating findings are closed.**

**746 passed / 0 failed / 4 skipped** over a derived **18-file** set. Nothing pushed or rebased;
`meta/kanban/cards/` and `requirements.yml` untouched.

### Where the line went was decided by measurement, and the first two answers were wrong

**The obvious reading of the owner's words cannot be afforded.** At 1280×720 — this suite's default
viewport — the 15×15 board's bottom edge is at **715.813 px in a 720 px viewport**. The page has
**4.187 px of vertical slack**; a line of that size needs **22.328 px**, of which only the toolbar's
own 16 px margin is reclaimable: **+6.328 px minimum against 4.187 px available.**

Spending it anyway pushes the board out of the viewport, Playwright scrolls to reach a cell, and any
test comparing a **viewport-relative** box across an action starts comparing two scroll positions.
Measured rather than predicted:

| board shift | reds |
|---|---|
| +38.312 px | 5 |
| +22.328 px | 4 |
| +10.328 px | 4 |
| **+6.328 px** | **2** — one whose drag re-measures the centre *between* its own mouse moves, so the board slides out from under a pointer path already computed; one whose solving click scrolls 2 px |
| **0 px — the page-head row** | **0** |

So the line is the third item of the `.page-head` row, which holds a line of text at **zero vertical
cost by construction**: `flex: 1 1 0` + `min-width: 0` means it can never force that row to wrap nor
widen it, and `nowrap` means it is always exactly one line, shorter than the `<h1>` that sets the
row's height. **The CSS comment carries the whole derivation, both rejected placements, and the note
that a future card wanting room there should fix the drag helper rather than buy it from this
margin.**

### The property, asserted as a property

`TestSolverHintLadder_EveryPressChangesSomethingSeen`, 7 tests, phrased against the **visible**
sentence — **deliberately not "the live region says…", which is how all ten card ACs passed while
the feature did not reach the player.** The headline test walks three presses and asserts three
visibly different pages, **and keeps F-2's own measurement alive as a live assertion**: between rung
1 and rung 2 the board and toolbar are still indistinguishable, **so the visible line is the entire
reason that press is visible.**

**The instrument was proved in both directions before anything was claimed with it.** Positive:
blank → rung 1 differs on board and line. Negative: **the same state measured twice, nothing
between, is byte-identical on all three regions** — so a reported difference is in the page, not the
instrument, which is the obvious way element screenshots could have read noise. **And the separation
was measured, not chosen**: repaint noise is **1–2 levels**, every real change **≥20** (a focus ring
20, a highlighted row 25, a revealed cell or an appearing sentence 204–227). The comparison is
**componentwise** — a tuple compare *"would have let 9 levels through on 6 pixels"*.

### The two dead-button cases are now visible, and a third is declared rather than hidden

The exhausted board's first press and Check on a clean board both change the line while the **board
digest is unchanged**, so the line is demonstrably carrying each alone — with the wrong-marks board
as the in-test control that the same instrument *does* see a board change when there is one.

**Declared residual, asserted in a test rather than left as prose:** the card's own rule fixes
**one** sentence for both exhausted rungs, so **the second press on an exhausted board still changes
nothing seen.** Giving it its own sentence changes declared semantics and is the owner's call; the
round did not invent copy.

### The accessibility choice, proved against Chromium's real tree

`aria-hidden="true"` on the visible copy, the announce region unchanged as the AT channel — because
that region is already the page's single `role="status"` announcement channel, and a second
non-live copy would make a screen reader meet each sentence **twice**. **Proved via CDP
`Accessibility.getFullAXTree`, not by asserting an attribute's spelling**: as shipped every node
carrying the sentence is un-ignored and from the announce region; removing `aria-hidden` raises the
count; restoring it returns the tree **exactly**. The announce region is asserted in its shipped 1×1
clipped state **on a real press, not only at load.**

### The owner-authorised copy sentence, and the tint

The usage paragraph and its exact-equality pin both gain one sentence describing the three presses
and Check, naming where each answer appears. **Nothing else in that file changed.** The tint is
**not** recoloured: re-measured at **1.1526:1** against WCAG 1.4.11's 3:1, with the ratio function
proved first (black on white 21.0000, a colour on itself 1.0000). Accepted as a residual because the
sentence now carries the meaning — **and the sentence is also what tells rung 1's highlight from
Check's, the job one tint could never do.**

### The owner's accepted 1280 px toolbar is exactly where it was

Every toolbar and board figure is **identical at base and at HEAD, line empty and line full**, at
both 1280 and 1440 — and **frozen on a press**, verified at 390 / 820 / 821 / 1024 / 1280. **Fix
round 1's five corrected figures all re-derive exactly** (263.656 need, 267.594 and 186.234 given,
81.359 cost, 77.422 shortfall, 74.797/38.797 heights), confirming the review's 268/186/82 were the
rounding artefacts it said they were.

**Two further residuals declared:** the line **ellipsises between about 820 px and 1270 px**; and
**inline at 390 px the title and badge would leave it 5.859 px**, which *"would have put F-2 straight
back for phone players"* — so a narrow-width rule gives it its own row at a constant +38.328 px,
where the board still fits. A phone/mid-width design for this line is a follow-up.

### Nine things it measured wrong — including three of its own

1. **Cycle 1's "byte-identical" is not a reproducible instrument.** The **board** does reproduce at 0
   differing pixels; the **toolbar does not**, once a visible line exists — the announce write
   invalidates a tile and Chromium re-rasters, returning **6 of 73,500 pixels** one level apart on
   the deducible board and **23** on the exhausted one. Cycle 1's own digest still reproduces
   exactly, **so its measurement was sound and the claim's FORM was not**; the test now bounds the
   per-channel level instead, because the pixel count tracks how big a region Chromium chose to
   re-raster.
2. **`meta/architecture/requirements.yml:4733` still states the retired figures** — *"268 px needed
   against 186 px left, short by exactly Check's own 82 px"*. Fix round 1's correction reached
   `admin.css` and the test docstring but **not that site**. **Owed**, and out of both rounds' scope.
3. **The lock did not stay free**: CARD-304's merge gate took it mid-run. The round's chained base
   runs **aborted cleanly on the guard**, CARD-304's gate was untouched, and **the clean lock-free
   re-run is the one carrying the verdict** — a 15 s tail overlap with 750 collected, not 0.
4. **Its own first instrument was wrong and its own test caught it**: a `min-height` computed
   **22.32 px** while the line box an actual sentence makes is **22.328125 px** — Chromium rounds a
   used line-height to 1/64 px and a min-height to the raw value — **so the board moved 0.015625 px
   on a press.** Replaced with a zero-width-space `::before`: *a line box reserves a line box
   exactly.*
5. **Its own second instrument was wrong**: the first draft asserted the a11y duplication by DOM text
   count and got 2 — **the right count of DOM copies and the wrong count of anything a screen reader
   meets.**
6. **It corrupted one of its own runs and discarded it** — it edited source files while a browser run
   was in flight, since the live server serves them from disk. Killed, re-run clean, **not reported
   as a result.**
7. **The orchestrator's framing of the layout risk was milder than the truth**: the brief warned about
   disturbing the 1280 px threshold *if* the line went in the toolbar row. **The measured truth is
   that the toolbar-to-board gap cannot take the line at all.**
8. Confirmed wrong as cycle 1 and fix round 1 both said: `grep -rln '"Hint"' tests/` returns **6**
   files, one of which is the editor file.
9. Confirmed **correct**, having re-derived them: the 138 node baseline, the 77.422 px shortfall, all
   five corrected toolbar figures, the heights, and 1.15:1 for the tint.

**Node ids 138 → 145: +7 added, 0 removed, 0 renamed, 0 merged.** **Skips: 4, identical at base and
HEAD**, all `db_required` methods of one class, `DATABASE_URL is not set` — environmental,
base-invariant, and this round touches no Python and no DB code. Runtime **~384 s quiet, 425–440 s
with anything else on the box**. No load figure.

- [Fix 2] `d22f1de0` — F-2 closed; all three gating findings closed; three residuals declared and
  measured rather than discovered later.
- [Review 2/3] Dispatched.

---

## Review cycle 2 — **8.5 / 10, CERTIFIED**. 5.5 → 8.5, **delta +3.0**, 0 gating open.

`meta/review/20261030T093000Z-CARD-269-cycle2.yml`. Recommendation: **land it**; its two should-fix
findings belong to a successor, not another cycle.

### All three gating findings closed, and F-2 is the best-evidenced work on the card

- **F-1** — resume is **15/15 at HEAD**, inside the reviewer's **own independently derived 20-file
  impact set**, wider than either round's: **911 collected, 907 passed, 0 failed, 4 skipped.**
- **F-2** — measured on the live page: rung 1 → rung 2 moves the line **1,915 px at 217 levels while
  the board is byte-identical**; the exhausted first press **1,771 px at 217**; Check on a clean
  board **768 px at 217** — both with the board byte-identical. **All three dead-button cases now
  change something seen, two of them carried by the line alone.**
- **F-3** — exactly **85 added / 0 removed** lines naming AC-327/329/334, and `requirements.yml`
  carries only the owner's AC-333 amendment, one `then:` line, no other id.

### The instrument's three proofs reproduce, and the reviewer went looking for the gap

Negative: same state twice, **byte-identical on all three regions, six repeats across two states.**
Separation: **noise ≤ 2 levels, smallest real change 20** — the focus ring, re-measured at exactly 20.

**"Nothing lands in 4–20" was tested rather than assumed.** The reviewer reached the gap the only way
it is reachable: **darkening the tint by 4 levels over 10,524 board pixels still reads
indistinguishable; 5 is caught.** That is a property of bounding **magnitude rather than area**, and
it is **documented in the docstring — known rather than overlooked.** The componentwise claim checks
out arithmetically: a count bound of ≤6 admits a 9-level change on 6 px; the level bound rejects it.

**Ruling on cycle 1's byte-identity claim: fix round 2 is right, and more right than it knew.** The
board half reproduces exactly at 0 differing pixels. The toolbar half does not — **and the
reviewer's own numbers differ from fix round 2's** (16 px at 2 levels against its 6 at 1; 20 against
its 23). **That disagreement is the best possible evidence for fix round 2's thesis**: the
measurement was sound, the claim's *form* was not.

### Placement re-derives to the digit, and the reviewer found a stronger test than the shipped one

715.813 / 4.187 / 22.328 all exact; the toolbar margin is exactly 16 px; the computed style is
exactly `flex-grow 1 / flex-shrink 1 / flex-basis 0px / min-width 0px / nowrap`. **Stronger than the
shipped test**: removing the element from the live page leaves head, board, toolbar, counters and
progress at **identical boxes at 1280×720, 1280×900 and 1440×900.** The **1280 threshold is
untouched**, identical empty, full, and with the line gone.

**Seven mutants, all bite.** `say()` reds **7/7**; the clear reds exactly the right one; removing
`aria-hidden` reds the a11y test; the zero-width space reds **6**; and `_INVISIBLE_LEVEL` is **pinned
between two live failures in opposite directions** (4→250 reds 3, 4→0 reds 2) — **genuinely derived,
not chosen.**

### The asked judgements

- **The exhausted second press is a correctly scoped residual, not F-2 surviving.** The repeated
  sentence is **true and complete** — the rule says one thing *because there is nothing more to say*
  until CARD-268. **Inventing copy would have been wrong; asserting it in a test was right**, and it
  is a real assertion with the pixel delta in its failure message.
- **The a11y choice is right, and the brief's worry does not hold.** The announce region is visually
  clipped but **present and un-ignored in the tree**, so a sighted screen-reader user **can** still
  reach the sentence as static text — it is only not co-located. Reproduced in all three directions
  (2 un-ignored shipped → 4 exposed → exactly 2 restored). One visible `role="status"` line would be
  the cleaner end state; **changing the shipped live region inside a gating fix round was not.**
- **The null-impossibility has a real control on the same board**: a hand-built deduced hint throws,
  while the real path on that same board, clues and solution still returns the exhausted null.
- **Legible at 1280/1440** — the sentence reads cleanly beside the title, the tint is perceptible,
  the usage paragraph names the ladder. Caveats: **typographically subordinate and far from the
  button**, and the captures cover **only the two deducible rungs** — none of the exhausted board, of
  Check, or of any narrow width.

### Nine things measured wrong — including one of the reviewer's own suspicions

1. **F-12: the phone IS in the ellipsis band.** The 5.859 px inline figure re-derives and the own-row
   rule is a real improvement, **but at 358 px every rung-2 sentence (508–594 px) and the exhausted
   rung-3 reveal are ellipsised at 390 px.** Only rung 1, the exhausted sentence (350.984 px, 7 px
   spare) and Check fit. **And there is no phone capture — F-4's shape, one band over.**
2. **F-13: the own-row rule pushes the board out of a 900 px viewport around 700–820 px wide** —
   917.297 px bottom against 878.969 without. **That is the exact failure mode the gap placement was
   rejected for**, and it was checked at 390×844 only.
3. The +6.328 row's named test is **wrong and unstable** — the count reproduces but the name does not,
   and it is 3 under a narrower selection.
4. **"the whole page has 4.187 px of vertical slack"** — the page already scrolls 178 px at
   1280×720; **the 4.187 belongs to the board's bottom edge**, not the page.
5. **"6 of 73,500 px at 1 level / 23"** does not reproduce (16 at 2, and 20); the region size is exact.
6. **The 22.32 px near-miss does not reproduce in the shipped placement** — it describes a placement
   no longer in the tree.
7. The node-id set is called "the five changed files"; **it is six.**
8. **The 18-file set and its 750 collected are not reproducible** — the files were never named; the
   reviewer's own derivations collect 845 and 911. **Its skip attribution is nonetheless exactly
   right.**
9. **The reviewer's own suspicion was wrong and the round was right**: the longest-sentence figure
   re-derives at 593.875 and really is the longest the page can produce.

**Node ids 138 → 145, +7/0/0**, re-derived once the set is identified. **Skips: 4, verified by name**,
all `db_required` methods of one class, file untouched by the branch. No load figure.

- [Review 2/3] Score: 8.5 ✓ certified, +3.0 improvement, 0 gating
- [Gate] Merge gate next. **F-12 and F-13 go to a successor card**, per the reviewer's own
  recommendation — they are player-facing at widths this card never claimed, not defects in what it
  shipped.

---

## Merge gate round 1 — **RED on one test**, and fix round 3 paid the bookkeeping

Gate at `414c6b4b`: **1 failed, 9883 passed, 27 skipped, 1 xfailed** in 23:59. AC/EC by node id
**88 passed, 0 skipped**; `src`+`tests` clean against the gated commit.

The single failure was
`test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured`
— **35 node ids added to the browser family and never registered.** `ADDED_SINCE_BEFORE` maps node id
→ (card, reason), and its own comment states the design: *"Adding a browser test therefore means
adding its node id here with a card and a reason… **Neither is free, and that is the point.**"*

**No review cycle could have caught it** — that module is outside this card's impact radius. **The
merge gate is what did**, for the second time in an hour on this board, after CARD-314 hit the same
shape against a different frozen registry.

### Fix round 3 — `414c6b4b` → `88570da3`, one file, +331/−0

**Derived, not transcribed from the gate log.** Base `8762beed` = `git merge-base main HEAD`, chosen
because it is also the **main-side parent of the gate's merge**, so no unrelated commit can leak in —
`main`'s tip was one kanban commit further on and was deliberately not used. The family was globbed
**the way the guard's own `_family_files()` globs it**, in both trees, and collected with the same
`--collect-only` the guard's child run uses.

| | family ids | `test_puzzle_solver_hint.py` |
|---|---|---|
| base `8762beed` | 505 | 25 |
| HEAD `414c6b4b` | 540 | 60 |

**35 added, 0 removed, 0 renamed** — so nothing belongs in the renames table and no deletion decision
arises. The other four files the branch touched **changed content, not coverage**.

**Proved both ways**, out of tree: one of the 35 made uncollectable, needle asserted unique first. The
derivation then answers **34**, dropping exactly that id, **with removed still 0** — so it saw "one of
the 35 is gone", not "a base test disappeared". *"A count would not have told those trees apart; this
does."*

### The register was written as a register, not as 35 rows of boilerplate

**118 entries now, 118 distinct reasons, shortest 9 words.** Nine of the 35 are recorded explicitly as
**another test's control**, which is the register's own precedent. Grouped by AC with two provenance
comments, including one marking fix round 2's seven and **why they are phrased against the visible
sentence rather than the live region.**

The reasons carry real content — one records that a parametrized case *"asserts the highlight is not
the ladder's old one rather than that it is empty, which is the one of the six that cannot be written
like the others"*; another records the instrument's both-directions proof and **why** it is needed
(*"so a difference reported below is the page and not the element screenshot scrolling its target into
view"*); another states the exhausted-board residual **and what a future card changing it would
break.** The module's own
`test_every_allowlist_entry_is_attributed_and_not_already_recorded` is the cell that would have caught
boilerplate, and it is green.

**Checked independently of the suite**: importing the edited module and set-comparing its CARD-269 keys
against the derived file gives **35 == 35, none extra, none missing.**

### Every sibling census in that module reported, which is the CARD-314 lesson applied

**30 passed, 0 failed, 0 skipped** over the whole file — all six censuses green, including the five
that were never red: the profiling census, the poll-interval pair, the four other cells of the
`NoTestAddedOrRemoved` class (its both-directions baseline test, the attribution cell, and both rename
cells), the order-independence set, the per-file isolation set, the alone-and-record pair, and the
no-cascade cell.

### Two figures it measured wrong, both mine

1. **The card's "+29 from the implementation" is one too many.** Measured per-commit, and cross-checked
   per id with `git log -S`: **28 from the implementation, 7 from fix round 2 = 35.** Corrected below.
2. **The "4 skips, all `db_required`" does not belong to this round, and my brief applied it as if it
   did.** The round measured that **none of the 12 files the branch changed contains a `db_required`
   reference** — the 4 are real in the *review's* 18-file run set, which included an untouched file
   that carries them. **0 is the honest number for everything this round ran**, and the two figures
   are about different scopes rather than disagreeing.

**Node-id delta for the round: 0 added, 0 removed, raw and net**, proved three ways — the module
collects 30 before and after, the diff contains no added or removed `def test`/`class`/`parametrize`
line, and it is 331 insertions with 0 deletions.
