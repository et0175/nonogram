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
**Review score:** —
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
