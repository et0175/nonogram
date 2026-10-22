# CARD-270: Filled cells merge across the heavy fifth rules — ink-on-ink hides the cell divisions

**Status:** in_progress
**Priority:** P2
**Category:** ops
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/270-fifth-rule-divisions
**Worktree:** ../PythonProject4-card-270
**Source:** quick — owner bug report 2026-10-22: "Regions around wider lines (5x cell number) don't have gray cell divisions around black cells"; no handoff increment
**Idea:** —
**Wave:** 54
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, tests/test_puzzle_solver_fifth_rule.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** 2026-10-22T17:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect, with its mechanism verified in the code

**Symptom (owner).** Around the heavier every-fifth rules, runs of black cells
show no gray cell divisions — adjacent filled cells merge into one blob, so
the player cannot count cells exactly where the heavy rule exists to help them
count.

**Mechanism.** A filled cell's background and the heavy rules are the same
token:

- `.player-cell[data-state="filled"] { background: var(--grid-ink); }`
  (`admin.css:575`)
- the heavy rules are `var(--player-rule-major) solid var(--grid-ink)` — on
  `.major-right`/`.major-below` (every fifth line, assigned in `solver.js`
  `drawBoard` at `:557-558`), on the board's outer edges
  (`admin.css:530-531`), and on the clue-gutter edges
  (`.player-clue.is-col`/`.is-row`, `admin.css:525-527`).

The *thin* dividers are `var(--player-thin)` (gray), so between two filled
cells across an ordinary border the division reads. Wherever the divider is a
major rule, it is ink on ink: invisible between filled cells. The defect class
is **any ink-colored rule adjacent to an ink-colored fill** — the fifth lines
the owner reported, and equally the outer border and the gutter edges when the
run of filled cells touches them.

## What to implement

Make the cell division between filled cells legible across every major rule,
without weakening the major rules against paper. Recommended mechanism, to be
confirmed by the owner on a render:

1. **An inner hairline on filled cells** — an inset `box-shadow` (or inset
   outline) of `var(--player-thin)` at `var(--player-rule)` width on
   `.player-cell[data-state="filled"]`, so every filled cell carries its own
   visible boundary and divisions read uniformly: across thin rules, major
   rules, the outer border and the gutter edges, with no neighbor-dependent
   CSS. `.is-hinted`'s inset box-shadow is the in-file precedent for drawing
   inside a cell without moving layout.
2. Alternatives to show beside it only if the hairline disappoints on the
   render: a filled-cell ink one step off the rule ink (two tokens instead of
   one), or neighbor-conditional borders via `:has()` (rejected by default:
   per-segment rules, and it dims the major rule itself between filled
   cells).
3. Whatever mechanism wins: values from tokens only, no layout shift (the
   cell's box must not change size), and the solved-flash animation and
   `prefers-reduced-motion` behaviour unchanged.

This is a stylesheet card: no JS change, no state change, no template change
expected. If the chosen mechanism turns out to need one, that is a finding to
surface, not to absorb silently.

## Acceptance criteria

- **AC-1** (happy): *Given* a board with two adjacent filled cells on either
  side of a fifth-line major rule (both axes), *then* the two cells are
  visually separated — the mechanism's marker (e.g. the inset hairline) is
  asserted present on filled cells, and a pixel sample across the shared edge
  of the rendered board finds a non-ink band between the two ink fills.
  (test: `TestSolverFifthRule_FilledCellsDivideAcrossMajorRules`)
- **AC-2** (edge, board edges): *Given* filled cells touching the board's
  outer border and the clue-gutter edge, *then* the division between fill and
  rule reads the same way there. (test:
  `TestSolverFifthRule_EdgesAndGuttersToo`)
- **AC-3** (edge, nothing else moves): *Given* the fix, *then* cell geometry
  is unchanged (same `--player-cell` sizes, no layout shift measured on a
  drawn board), the major rules against paper are exactly as before, and the
  empty-dot and "?" marks are untouched. (test:
  `TestSolverFifthRule_GeometryAndOtherMarksUnchanged`)
- **AC-4** (edge, tokens + motion): *Given* the shipped stylesheet, *then*
  every new value comes from tokens with a per-rule check, and
  `prefers-reduced-motion` still disables all board animation. (tests:
  `test_the_filled_cell_division_comes_from_tokens`,
  `TestSolverHint_ReducedMotion` unedited)

## Guardrails

- G-1: Player CSS only — no change under `src/nonogram/export/**` or to the
  book/print pipeline; the CON-019 byte-identity tripwires run unedited.
- G-2: Hand-written CSS, tokens only (ADR-0038/R1; test:
  `test_the_stylesheet_uses_tokens_not_literals`).
- G-3: No JS or state change: `solver.js` and `solver_state.js` are not
  edited; `data-state` values and all existing player tests run unedited.
- G-4: The owner sees a rendered board (a real puzzle with filled runs
  crossing fifth lines, edges and gutters) before merge and picks between the
  hairline and any alternative — a green suite does not close this card
  (standing practice: visual changes get an eyeball).

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R4 — state logic is a pure module, separate from rendering; this
  card touches rendering only (check: review-lens)
- CON-021 — interactive play only in the admin panel's player (check:
  review-lens)

## Architecture context

- **FR:** FR-044 (the player's board rendering; the every-fifth heavy rule is
  CARD-212/CARD-193-era rendering behaviour).
- **ADR:** ADR-0038/R1, R4.
- **CON:** CON-015/CON-016, CON-021.
- **Components:** COMP-009 (admin panel: static CSS).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; the fix adds at
  most one token (the hairline) — reuse `--player-thin`/`--player-rule` where
  they already say the right thing.
- **UI components:** `.player-cell[data-state="filled"]` only.
- **Screens:** `/puzzles/<id>/solve` (and the editor's board, which shares the
  stylesheet — check it on the render too).
- **Standards:** no layout shift; both the division and the major rule must
  survive at the phone cell sizes (14 px cells — a hairline that rounds to
  0 px there is a miss, state what it measures at 14 px).

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |
| `TestSolverHint_ReducedMotion` | `tests/test_puzzle_solver_hint.py:886` |

**To be written by this card** (in `tests/test_puzzle_solver_fifth_rule.py`,
new file, except the token check, which joins
`tests/test_admin_design_tokens.py`) — none exists yet; report them as
written, never as passing before they exist:
`TestSolverFifthRule_FilledCellsDivideAcrossMajorRules`,
`TestSolverFifthRule_EdgesAndGuttersToo`,
`TestSolverFifthRule_GeometryAndOtherMarksUnchanged`,
`test_the_filled_cell_division_comes_from_tokens`.

## Worktree notes

- **[Pixel assertion honesty]** AC-1's pixel sample must state its domain: a
  screenshot at a declared viewport and zoom, sampling a declared edge —
  not a general claim about every rendering. The mechanism assertion is the
  regression net; the pixel sample is the one check that the mechanism
  actually produces a visible band.
- **[Conflict note]** Touches overlap CARD-267/268/269 on `admin.css` and
  `tokens.css`; the dispatcher serializes same-wave overlaps. This card has
  no JS footprint, so it composes with any of them in either order.
