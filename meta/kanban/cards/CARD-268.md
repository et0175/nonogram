# CARD-268: Probe mode — hypothesis marks in their own tint, abandoned or committed as one transaction

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/268-player-probe-mode
**Worktree:** —
**Source:** quick — owner decision 2026-10-22 (player-convenience session, option 2: "for puzzles that need contradiction-probing add another color for probing cells", shaped in the same session into a transaction, not just a color); no handoff increment
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py, tests/test_admin_design_tokens.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why a transaction and not a fifth cell state

What a solver actually does when probing is make a *group* of marks under one
hypothesis, then either revert them all (contradiction found) or keep them all
(hypothesis confirmed). During a probe the player places both filled **and**
empty (and maybe) marks, so one extra color cannot carry it — "probing" is a
layer orthogonal to the mark, never a fifth entry in `CELL_STATES`. The painful
part of probing by hand is the revert: finding and clearing exactly the marks
that belonged to the hypothesis. If the player cannot do that in one action,
the color is cosmetic. The template's own comment warns that "every selector,
save and test keyed on those [data-state] values" depends on the four states —
probe membership must therefore live beside `data-state`, not inside it.

## Declared semantics (decided before code, owner-approved 2026-10-22)

The stroke history (`solver_state.js`: `{board, done: [{stroke, before}],
undone: [stroke]}`) is the foundation. A **probe is a checkpoint in that
history**; probe membership is *derived from history*, never stored per cell.

1. **Depth 1.** At most one probe is open at a time. No nested probes — that
   is a debugger, not a puzzle.
2. **Start.** A "Probe" control opens a probe at the current history position.
3. **While open**, every mark made (any brush: filled, empty, maybe; hint
   strokes too) belongs to the probe and renders in the probe tint — a tinted
   variant of each mark's look, with all four `data-state` looks still
   distinguishable under it.
4. **Abandon** ("contradiction"): one action undoes back to the checkpoint —
   the board is exactly as at probe start — and closes the probe. Redo after an
   abandon follows the existing history rules (the undone probe strokes sit on
   `undone` like any other undos; a redone stroke that lands past a *closed*
   probe's old checkpoint is a normal stroke — closing a probe forgets it).
5. **Commit** ("confirmed"): the marks lose the tint and become normal; the
   probe closes. Nothing else changes — commit touches no cell.
6. **Undo/redo during a probe** work exactly as today (LIFO, so probe strokes
   pop first). Undoing *past* the checkpoint clamps it: a probe never contains
   strokes made before it started, it can shrink to empty and stay open, and
   further marks still belong to it.
7. **Solved while probing commits.** `isSolved` compares against the solution,
   so a probe that reaches the solved state was correct — the probe commits
   and the solved banner/lock behave exactly as today.
8. **Error count, progress, circles: unchanged.** They read the board as it
   is, probe marks included — this card does not touch their semantics, so no
   shipped AC-3xx is amended.
9. **The save never contains probe strokes** (leaving the page abandons the
   open probe). While a probe is open, `serializeState` serializes the history
   as of the checkpoint; a reload resumes at the probe's start. The page says
   so where the probe controls are, in one short line.
10. **Reset** behaves as today: it clears the board, the history and any open
    probe (a cleared history has no checkpoint to keep).
11. **Probe open/closed is player state** and belongs in the pure module like
    Region's flag (ADR-0038/R4): checkpoint arithmetic, membership, clamp,
    commit/abandon transitions and their interaction with `record`/undo/redo
    are pure functions in `solver_state.js`; the buttons and the tint are
    rendering in `solver.js`. Rendering marks membership on the cell (e.g.
    `data-probe` on `td.player-cell`), **never** by changing `data-state`.

## What to implement

**Current behaviour (verified by reading the code).**

- `solver_state.js` holds the four `CELL_STATES`, frozen boards, strokes and
  the history value; `record` applies a stroke, undo/redo move along it.
  Strokes already carry an optional flag (`hint: true` in `savedStroke`) —
  precedent for stroke-level metadata, though this card's membership is
  positional (the checkpoint), not a per-stroke flag, so a save written
  mid-probe does not need one.
- `serializeState` replays from a blank board: it refuses a history not
  starting blank, and saves `done`/`undone` as stroke lists. `deserializeState`
  rebuilds by replay. Save key: `saveKey(payload.id)`; CARD-185 / AC-360..365 /
  CON-021 govern it.
- Region (CARD-211) is the precedent for a boolean of player state kept in the
  pure module while its button lives in `solver.js`.
- The brush menu and tool row live in `puzzle_solve.html` (`.player-tools`);
  `data-player-tool` buttons, Region toggle, History group, Zoom group.

**What changes.**

1. `solver_state.js`: the probe value and its pure transitions (open at a
   position, membership of a history, clamp on undo-past, commit, abandon =
   the undo-to-checkpoint composition, auto-commit on solved), each a function
   of its arguments, testable from the browser suite via
   `await import('/static/solver_state.js')`.
2. `serializeState`/the save path: while a probe is open, the serialized
   history is the checkpoint prefix (semantics rule 9). `deserializeState` is
   unchanged — a save never holds a probe, so there is nothing new to parse,
   and **every save written by today's player still loads** (G-5).
3. `solver.js` + template: a "Probe" toggle in the player tools; while open,
   "Keep" (commit) and "Contradiction" (abandon) actions and the one-line
   leaving-abandons note; `data-probe` on member cells, repainted on every
   history change (a repaint already happens per stroke/undo/redo).
4. `tokens.css`/`admin.css`: the probe tint, tokens only, distinct from the
   crosshair tint (CARD-267) and from CARD-188's circles.
5. Accessibility: the probe controls are real buttons with accessible names
   and pressed state on the toggle; the tint itself adds no per-cell ARIA.

## Acceptance criteria

- **AC-1** (happy): *Given* an open probe, *when* marks are made with the
  filled, empty and maybe brushes, *then* each cell keeps its normal
  `data-state` and additionally carries the probe marker, and cells marked
  before the probe carry none. (test: `TestSolverProbe_MarksCarryTheTint`)
- **AC-2** (happy, abandon): *Given* a probe with N strokes over a pre-probe
  board B, *when* Abandon is pressed, *then* the board equals B cell for cell,
  the probe is closed, and no probe marker remains. (test:
  `TestSolverProbe_AbandonRestoresTheCheckpointBoard`)
- **AC-3** (happy, commit): *Given* a probe with marks, *when* Keep is
  pressed, *then* every cell's `data-state` is unchanged, every probe marker is
  gone, and the probe is closed. (test:
  `TestSolverProbe_CommitKeepsCellsAndDropsTheTint`)
- **AC-4** (edge, undo during probe): *Given* an open probe, *then* undo pops
  probe strokes first and their markers clear with them; *given* undo past the
  checkpoint, *then* the checkpoint clamps, the probe stays open and empty, and
  the next mark belongs to it. (test:
  `TestSolverProbe_UndoClampsTheCheckpoint`)
- **AC-5** (edge, depth 1): *Given* an open probe, *then* the Probe control
  cannot open a second one (pressing it is either disabled or a no-op with the
  pressed state unchanged — pick one and test that one). (test:
  `TestSolverProbe_OnlyOneProbeAtATime`)
- **AC-6** (edge, save): *Given* an open probe with marks, *then* the
  localStorage save equals the save as of the checkpoint — reloading the page
  shows the pre-probe board, no probe open, and the pre-probe undo history
  intact. (test: `TestSolverResume_AReloadAbandonsTheOpenProbe`, in
  `tests/test_puzzle_solver_resume.py`)
- **AC-7** (edge, solved): *Given* a probe whose marks complete the solution,
  *then* the solved banner and lock appear exactly as today and no probe
  marker remains (auto-commit). (test:
  `TestSolverProbe_SolvingCommitsTheProbe`)
- **AC-8** (edge, counters unchanged): *Given* probe marks, *then* the error
  count, Progress % and clue circles read exactly as they would for the same
  marks made without a probe. (test:
  `TestSolverProbe_CountersSeeProbeMarksAsMarks`)
- **AC-9** (edge, pure module + tokens): *Given* the shipped code, *then* the
  probe transitions live in `solver_state.js` as pure functions with no DOM
  reference, `CELL_STATES` still has exactly today's four members, and the
  tint's colors come from tokens with a per-rule check. (tests:
  `TestSolverProbe_StateIsPureAndStatesAreFour`,
  `test_the_probe_tint_comes_from_tokens`)

## Guardrails

- G-1: Hand-written JS/CSS only — no framework, no build step, no vendored
  library (ADR-0038/R1).
- G-2: No request per mark, probe actions included — open, mark, commit,
  abandon make no network request (ADR-0038/R2; test:
  `TestSolverMarking_NoRequestPerMark`).
- G-3: Play state stays browser-local: the probe never reaches a server, a
  database or any storage beyond the existing localStorage save (CON-021).
- G-4: `CELL_STATES` is not extended and `data-state` values are not changed —
  probe membership is a separate attribute (the template comment's "every
  selector, save and test keyed on those values" is the reason).
- G-5: Save compatibility both ways: a save written by today's player loads
  unchanged, and a save written by this card's player (no probe open at write
  time, which rule 9 makes always true) loads in today's player. No
  `SAVE_VERSION` bump without an escalation.
- G-6: Styling from tokens only (test:
  `test_the_stylesheet_uses_tokens_not_literals`, plus the per-rule check in
  AC-9).
- G-7: Existing player behaviour outside the probe is untouched — the existing
  `tests/test_puzzle_solver_*.py` files run unedited, except
  `test_puzzle_solver_resume.py`, which only gains AC-6's new test.
- G-8: The Maybe brush keeps its current meaning and is not repurposed as the
  probe tint — both exist, independently.

## System contract

- ADR-0038/R1 — hand-written JS/CSS, no framework or build step (check:
  review-lens)
- ADR-0038/R2 — no network request per mark (check:
  `TestSolverMarking_NoRequestPerMark`)
- ADR-0038/R4 — state logic is a pure module, separate from rendering (check:
  review-lens)
- ADR-0038/R6 — only the admin player, behind the CON-015/CON-016 door, ships
  the solution to the browser; the probe adds no new consumer of it (check:
  review-lens)
- CON-021 — play state persists only in this browser's localStorage, per
  puzzle; nothing server-side (check: review-lens)

## Architecture context

- **FR:** FR-044 (the player). Like Hint, Maybe, circles, progress and resume
  before it, this is an owner-decided player feature that will warrant an
  FR-044 amendment with its own AC range; the owner decision of 2026-10-22
  goes through `inputs/raw-requirements.md` on the architect side — this card
  does not edit `requirements.yml`, and its ACs above are the card-local
  statement the gate holds onto (quick-card rule).
- **ADR:** ADR-0038/R1–R4, R6.
- **CON:** CON-015/CON-016, CON-017, CON-021.
- **Components:** COMP-009 (admin panel: static JS/CSS, template).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Design context

- **Design system:** `static/tokens.css` + `static/admin.css`; every value is
  a token (G-6).
- **UI components:** `.player-tools` gains the Probe toggle and the two
  probe-open actions; `td.player-cell` gains the `data-probe` attribute looks
  for each of the four states.
- **Screens:** `/puzzles/<id>/solve`.
- **Standards:** real buttons with accessible names, `aria-pressed` on the
  toggle (Region is the in-file precedent); the tint is never the only carrier
  of the probe's meaning for the controls (the toggle's state is); owner
  validates the look on a real puzzle render before merge.

## Named tests resolved before the card started (drafting, 2026-10-22)

**Already exist** (run them, do not rewrite them):

| name | resolves to |
|------|-------------|
| `TestSolverMarking_NoRequestPerMark` | `tests/test_puzzle_solver_marking.py:1377` |
| `test_the_stylesheet_uses_tokens_not_literals` | `tests/test_admin_design_tokens.py:219` |

**To be written by this card** (in `tests/test_puzzle_solver_probe.py`, except
AC-6's, which joins `tests/test_puzzle_solver_resume.py`, and the token check,
which joins `tests/test_admin_design_tokens.py`) — none exists yet; report
them as written, never as passing before they exist:
`TestSolverProbe_MarksCarryTheTint`,
`TestSolverProbe_AbandonRestoresTheCheckpointBoard`,
`TestSolverProbe_CommitKeepsCellsAndDropsTheTint`,
`TestSolverProbe_UndoClampsTheCheckpoint`,
`TestSolverProbe_OnlyOneProbeAtATime`,
`TestSolverResume_AReloadAbandonsTheOpenProbe`,
`TestSolverProbe_SolvingCommitsTheProbe`,
`TestSolverProbe_CountersSeeProbeMarksAsMarks`,
`TestSolverProbe_StateIsPureAndStatesAreFour`,
`test_the_probe_tint_comes_from_tokens`.

## Worktree notes

- **[Semantics first]** The "Declared semantics" block above is the decided
  contract (CARD-262's lesson applied at drafting time rather than mid-card):
  if the implementation needs to diverge from any numbered rule, record the
  divergence beside the block and say why — never edit the block to match the
  code.
- **[AC-4's redo edge]** Rule 4's parenthetical decides redo-after-abandon by
  reference to the existing history rules; if the implementation finds those
  rules ambiguous for a redone stroke landing past a closed probe's old
  checkpoint, that is a real finding — surface it, don't pick silently.
- **[Conflict note]** CARD-267 (crosshair) touches `solver.js`, `admin.css`,
  `tokens.css` and the template too; the dispatcher's overlap prediction will
  serialize the pair if they land in one wave. CARD-267 is the smaller card
  and has no `solver_state.js` footprint — either order works.
