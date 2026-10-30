# CARD-268: Probe mode — hypothesis marks in their own tint, abandoned or committed as one transaction

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** `card/268-player-probe-mode`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-268
**Source:** quick — owner decision 2026-10-22 (player-convenience session, option 2: "for puzzles that need contradiction-probing add another color for probing cells", shaped in the same session into a transaction, not just a color); no handoff increment
**Idea:** —
**Wave:** 69 <!-- STAMPED 2026-10-30 at dispatch. Owner decision: "we agreed before to take 309+268". Its drafting-time conflict note named CARD-267 (crosshair) as the card it would serialize against -- CARD-267 merged `4b4a26e7` in wave 63, so that contention is gone. Against CARD-309 the measured Touches intersection is EMPTY. -->
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/static/tokens.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py, tests/test_admin_design_tokens.py
**Review score:** cycle 1 **7.5 — did NOT certify** (2 open important, 0 critical) → **fix round 1 complete**, cycle 2 running. **F-001 closed by MOVING CHANNEL** on the owner's decision: the marker is a **dashed outline** and the probe declares **no `background` at all**. Separations against every ground a probe cell can have — paper 66.26, crosshair 58.46, hint line 64.23, ink 71.47, crossed ink 56.85, hint-lined ink 51.19 — against a floor of 20, **8.7× the JND**. **Verified by the orchestrator re-firing its own probe:** the marker made visually absent now reds 3 cells on `TheMarkerIsMeasurablyApartFromItsGround` where the identical mutant previously passed **39/39**. **F-002 closed in both places**, and the insight is that **one number provably cannot carry rule 6** — an open probe's own undone stroke and a stroke undone before it leave `done.length` identical — so the probe became a frozen **set of stroke identities**, with the oracle rewritten independently and the demonstration run **both directions**. Its own honest negative: **T5** shows the filled-variant rule's real justification is **contrast** (3.57:1 → 8.22:1), not ΔE, because ΔE76 is lightness-dominated. Gate **591 passed / 0 skipped** (+10 = exactly its ten new node ids). **It also corrected a figure in the orchestrator's brief** (`background` claimants: 9 asserted, **6** counted from the rules).
**Started:** 2026-10-30T11:58:28Z
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

### Divergences from the block above, recorded at implementation

The eleven rules are the contract and are **not edited**. These are the places
the shipped code departs from them, or decides something they left open, each
with the reason and the test that holds it.

- **Rule 9, in the REDO STACK only.** While a probe is open the save is the
  history as of the checkpoint *with no redo stack*, where "the save as of the
  checkpoint" would have carried the redo the player had then. The probe is one
  number, and from one number an open probe's own undone strokes cannot be told
  from strokes undone before it (undo a probe stroke and it sits on `undone`
  exactly as a pre-probe stroke would), so the only answer that can never save
  a probe stroke is to save no redo stack. The cost is bounded and reachable
  exactly one way — undo PAST the checkpoint while a probe is open, after which
  a redo that was pending is not restorable from a reload; the live player's
  redo is untouched. In every other case the cost is zero, because `record`
  has already dropped the redo stack itself, and opening a probe writes no save
  at all. Tested, both halves:
  `TestSolverResume_AReloadAbandonsTheOpenProbe::test_an_open_probe_saves_no_redo_stack`.
- **Rule 10 is inconsistent with itself, and "as today" won.** It says Reset
  "behaves as today" AND that it "clears the board, the history and any open
  probe". Today's Reset does *not* clear the history: it records one undoable
  `resetStroke` through `record`, which is what makes "Undo brings them back"
  true (the confirmation says so). Shipped: the open probe is closed and the
  board is cleared by that same one undoable stroke, so the history behaves
  exactly as today. Closing the probe is also the only sane reading — a reset
  stroke left INSIDE the probe would make Contradiction un-reset the board.
  Tested by `TestSolverProbe_CountersSeeProbeMarksAsMarks` (which resets
  between its two runs) and by the mutant `E2` below.
- **AC-5's either/or: DISABLED, not a no-op.** While a probe is open the
  toggle carries `aria-disabled="true"` and keeps `aria-pressed="true"`; the
  handler returns early as Reset's does. That is the discipline every other
  control on this page already follows, and it tells the player why rather
  than looking broken. Tested by
  `TestSolverProbe_OnlyOneProbeAtATime::test_a_second_press_opens_nothing`.
- **Rule 4's flagged redo edge is NOT ambiguous** (the card asked for a
  finding if it were). Membership is a function of `(history, probe)` and
  `probe` is `null` once the probe closes, so a stroke redone past a *closed*
  probe's old checkpoint is a normal stroke by construction — there is no
  second place that could still believe it belongs to the probe. Tested by
  `TestSolverProbe_AbandonRestoresTheCheckpointBoard::test_a_stroke_redone_after_an_abandon_is_a_normal_stroke`.
- **Design context, not a numbered rule: where the controls are.** The card's
  Design context put the Probe toggle and the two actions inside
  `.player-tools`. They ship as a group of their own on the TOOLBAR'S LAST
  FLEX LINE. **The three sentences that stood here about what pays for that
  line were measured wrong and are corrected by the fix round** (see the fix
  round's note at the end of this card, and the bullet in `admin.css` that
  now carries the numbers): the line is **24 px**, not 47; `.player-stage`'s
  `max-height` pays nothing, because that draft never shipped and no `:has`
  rule on the stage exists; and the line is paid for by the toolbar's own row
  gap (8 px) plus all but one pixel of the toolbar's own bottom margin
  (16 px) — with the **residual 9 px taken out of the 16 px between the page
  head and the toolbar**, which is what keeps the board's top at today's
  number. The measurements below are the ALTERNATIVES the implementation
  round rejected, all written out in `admin.css` beside the rules; (b) is the
  one it then under-read, and the fix round's note says by how much:
  (a) at 1280 x 720 the toolbar's first row is exactly full (980 px of content
  in a 980 px row; `.player-tools` is itself 208 px of content inside its own
  13rem floor), and `.player-tools > button` / `.player-history > button` are
  the selectors two standing tests read one-row-ness through;
  (b) **the board may not move DOWN**, because `#puzzle-player` is a scroll
  container and so sits in the Tab order: Chromium smooth-scrolls it into view
  when the brush menu's keyboard test tabs the whole ring, 11 px today at
  1280 x 720 — just inside half a cell (11.7 px) — and 34 px with the row
  unpaid, which crosses a row mid-drag and reds 4 of the 8 cases of
  `tests/test_puzzle_solver_marking.py
  TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press`;
  (c) the same shift reds `tests/test_puzzle_solver_zoom.py
  TestSolverZoom_ZoomKeepsTheViewCentre` at 390 x 844 (a 30 x 30 at 300 % put
  the stage's own centre at 848.8 past a 844 px window, so
  `elementFromPoint` answered null);
  (d) paying for the row in `--player-chrome-h` — otherwise exactly the right
  property — also feeds the CELL CLAMP, whose height term binds at 1280 x 720:
  it takes a 15 x 15's cell from 23.4 px to 21.1 px and reds five fit and
  geometry tests, the largest board's own fit among them. So the stage's cap
  pays and the board's fit does not;
  (e) BELOW the board is worse, not better: a focusable control under the fold
  is reached by the same Tab walk and Chromium scrolls the page 233 px to
  reveal it, reddening the same keyboard test harder (measured: 5 of 8 cases).
  Net effect of what shipped, measured in the fix round at 1280 x 720 (the
  figures that stood here — stage bottom 729.6 against 730.6, focus scroll 10
  against 11 — belong to the unshipped `max-height` draft and are struck):
  the stage's top 238.796875 and its bottom 730.796875, both **today's
  numbers exactly**, the focus scroll 11 px, today's, the document 898 px
  tall, today's, the toolbar's top 139 against today's 148, and 1 px of air
  between the probe bar and the board at 1280 x 720, 1440 x 900 and 390 x 844
  alike.

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

- **[Env]** forge `2026.8.17` (executing manifest `forge_1/forge/.claude-plugin/plugin.json`).
  The project declares no `meta/.skills.yml`, so there is no `forge.min_version` to compare
  against and no `models:` block — the implementation agent inherits the session model rather
  than resolving a class. Recorded because a later diagnosis needs the version the procedures
  came from, not because a gate fired.

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

### Fix round 1 of 2 (build-fix, not a review cycle)

- **[Diagnosed cause — one defect, five red tests]** The gate was red on five
  browser tests, not the one the round was briefed on, and all five come from
  the same decision: the probe bar's flex line was paid for out of the
  toolbar's bottom margin *alone*. That did two things at once.
  - It left the bar's bottom edge **exactly** on `.player-board`'s top edge —
    measured, the same number to the 1/64 px at every viewport the suite
    samples: 246.796875 at 1280 x 720, 210.796875 at 1440 x 900, 502.0625 at
    390 x 844, air 0 in all three. A Playwright **element** screenshot clips
    the page raster to the enclosing whole-pixel rect,
    `[floor(top), ceil(bottom))`, so a board whose top is at `y.797` is
    captured from `y.0` and **row 0 of every `.player-board` capture held the
    bottom 0.797 px of the Probe button**. Measured on the failing arm: row 0
    read `(127,117,95)` across x = 3..54 (the button's bottom border blended
    with paper) where the same board with the bar hidden reads
    `(245,240,230)` = `--grid-paper` for the whole row. That is what
    `test_the_rules_against_paper_are_untouched` reported as "a hairline is
    reaching cells that are not filled": **no cell had a `box-shadow` at
    all** — all 400 computed `none` in both of its readings — and the 4
    differing pixels (x = 1, 2, 55, 56, by 1 per channel) were the button's
    own antialiased corners. It was not the injected style either: capture A
    against B with *nothing* injected differs on exactly those 4 pixels,
    while B vs C and C vs D (shadow off) are byte-identical, so the arm was
    comparing the first paint of a composited button edge against every
    later one.
  - It moved the board **8 px down**, and that reddened the other four:
    3 of the 8 cases of
    `tests/test_puzzle_solver_marking.py
    TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press`
    (`White-Enter`, `White-Space`, `Clear-Enter`) and
    `tests/test_puzzle_solver_progress.py
    TestSolverProgress_SolvedWhenBlacksMatch::test_the_banner_takes_the_tools_place_and_the_board_does_not_move`.
    **Measured identically at 8 px (the implementation round's commit
    `bc43eda5`) and at 9 px, so they pre-date the fix round's own change.**
    The keyboard cases fail because `#puzzle-player`'s focus scroll goes
    11 px -> 19 px, past the half-cell (11.7 px) the card's own `admin.css`
    bullet names as the tolerance, and the drag then lands a row off. The
    solved-banner case fails by a **second mechanism nobody had looked for**:
    the board 8 px lower puts that test's last filled cell under the fold,
    Playwright scrolls the **page** 5 px to click it, and the test's
    before/after `bounding_box()` sees the board move 5 px
    (247.796875 -> 242.796875) across a stroke that changes the toolbar's
    height not at all — the whole page moved. So the `admin.css` bullet's
    "4 of the 8 ... with the stage 23 px lower" was true and misleading: it
    implied 8 px was free. **"The board may not move down" has no slack in
    it; it is zero.**

- **[What changed]** Two CSS rules and nothing else — no JS, no template, no
  token, no sibling test.
  - `.player-toolbar:has(.player-probe) { margin-top: calc(-1 * var(--space-2) - var(--border-width)); }`
    — the line is paid for ABOVE the toolbar now, out of the 16 px between
    the page head and the toolbar. `:has` because `puzzle_edit.html`
    (CARD-246) draws its board under the same `.player-toolbar` and is
    offered no probe; keyed on the bar's PRESENCE rather than
    `:not([hidden])` so the pull-up is constant for the page's whole life.
  - `.player-probe`'s `margin-bottom` goes
    `calc(-1 * var(--space-4))` -> `calc(-1 * var(--space-4) + var(--border-width))`
    — one hairline of air, which is sharp for every viewport and zoom rather
    than for the ones measured, because `floor(t) > t - 1` for every `t`.
  - The arithmetic is forced, not chosen, and it is written out in
    `admin.css`: with the bar `h` px tall the board moves `8 + mt + h + mb`
    and the air below it is `16 + mb`, so `air >= 1` and `movement = 0`
    together need `mt = 7 - h` — `-17 px` for a 24 px row, which would put
    the bar 9 px inside the toolbar's first line. There is no third margin on
    the bar to spend, which is why the toolbar pays.
  - Result, measured: below the toolbar the page is today's geometry exactly
    (stage top 238.796875 / 202.796875 / 494.0625, focus scroll 11 px,
    document 898 px), so nothing downstream had to be re-measured.

- **[Controls added]** Both in this card's own file (G-7 holds: no
  `test_puzzle_solver_*.py` sibling was edited), seven node ids, all
  registered in `tests/test_browser_fixture_scope.py`'s `ADDED_SINCE_BEFORE`.
  - `TestSolverProbe_TheBarStaysOutOfTheBoardsCapture::test_the_bar_ends_above_the_boards_first_capture_row`
    — 4 cases (desktop/phone x probe closed/open). Assertion 1 is the
    premise (the bar is visible and is a line of its own below
    `.player-tools`); assertion 2 is the claim
    (`barBottom <= floor(boardTop)`).
  - `TestSolverProbe_TheBarCostsTheBoardNoGround::test_the_probe_line_leaves_the_boards_top_where_it_was`
    — 3 cases (1280 x 720, 1440 x 900, 390 x 844). Assertion 1 is the premise
    (the toolbar's margin-top is negative and the bar is visible);
    assertion 2 compares the board's top with the board's top in a page whose
    two CARD-268 geometry rules are both switched off. It exists because the
    two unedited siblings only go red at 8 px, and 1 px is the error a reader
    of the pull-up rule would make.

- **[Mutant table]** Each applied to `admin.css` at HEAD (clean-tree asserted
  by `git diff --quiet HEAD` before each), restored with
  `git checkout HEAD --` and the restore verified by SHA-256 both ways;
  `PYTHONDONTWRITEBYTECODE=1`, `*.pyc`/`__pycache__` swept before and after
  each. Harness in `scratchpad/card268fix/` (never the shared scratchpad
  root). Every row names the ASSERTION that fired, because a test
  short-circuits at its first failing assert.

  | id | mutation | what died, per assertion |
  |----|----------|--------------------------|
  | **A1** | air -> 0 (`margin-bottom: calc(-1 * var(--space-4))`, i.e. exactly what `bc43eda5` shipped) | air class **4/4** red, all on **assertion 2** ("the probe bar's bottom edge (201.796875) is inside the first whole pixel row…"); no-ground class 3/3 red on assertion 2 (board 1 px high); **sibling `test_the_rules_against_paper_are_untouched` red** |
  | **A2** (edge) | air -> half a pixel (`+ var(--border-width) / 2`) | air class **2/4**: `phone-closed`, `phone-open` red on **assertion 2**; `desktop-closed`, `desktop-open` **SURVIVE** — the board's top fraction at 1440 x 900 is `.797`, so `floor()` absorbs the half, where at 390 x 844 it is `.0625` and it does not. This is why both viewports are swept, and the claim in `admin.css` and in the docstring says exactly this rather than "half a pixel fails". no-ground class 3/3 red on assertion 2 (board 0.5 px high) |
  | **P1** (premise of the air class) | `.player-probe { flex-basis: 100% }` -> `auto`, so the bar folds onto the toolbar's first row | air class `desktop-closed` red on **assertion 1**, with the premise's own numbers (`barTop 131`, `toolsBottom 177.78`) — so assertion 1 is reached and falsifiable, not decoration; no-ground 1440x900 + 390x844 red on assertion 2 (board 9 px high: the pull-up now over-pays) |
  | **B1** | the pull-up rule -> `margin-top: 0` | no-ground class **3/3** red on **assertion 1** ("the toolbar's margin-top is 0 …") — premise reached and falsifiable; **siblings red: 4 of the 8 keyboard cases** (`White-Enter`, `White-Space`, `Clear-Enter`, `Clear-Space`) **and the solved-banner test** |
  | **B2** (edge) | the pull-up -> `-8 px` (`calc(-1 * var(--space-2))`, the one-pixel error) | no-ground class **3/3** red on **assertion 2** (board 1 px low, all three viewports). The two siblings **survive** — which is the whole reason this control exists: they are sharp at 8 px, it is sharp at 1 |

- **[Defect-class audit, not just the sibling named]** The class is *anything
  painted flush against an element's box edge leaks into that element's
  element screenshot, because the clip is the enclosing whole-pixel rect*.
  Four files in the family take screenshots; the audit covers all of them.
  `tests/test_puzzle_solver_fifth_rule.py` is the only one that takes an
  element screenshot of `.player-board` and compares two of them byte for
  byte — that is the one that reddened.
  `tests/test_puzzle_solver_hint.py`'s `_SEEN_REGIONS` takes element
  screenshots of `.player-board`, `#puzzle-player-controls` (which
  **contains** the probe bar, so the bar is legitimately part of that capture
  and is static across the press it compares) and `#puzzle-player-explain`
  (in `.page-head`, nowhere near the bar) — measured green at `bc43eda5`
  already and green now. `tests/test_puzzle_solver_clues.py` takes 3 x 3
  page-clip samples inside the board, far from its top edge;
  `tests/test_puzzle_solver_maybe.py` takes full-page shots and thresholds
  the difference at > 24 per channel, which a 1-per-channel edge artefact
  cannot reach. Nothing else of this card's is flush with a captured edge:
  the bar's own TOP is flush with `.player-tools`'s bottom, and no test
  captures `.player-tools`.

- **[Finding for another card / for review — the comment's figures]** Three
  claims in the CARD-268 `admin.css` block were measurably wrong and are
  corrected in place, with the correction labelled: the bullet count ("four"
  over five bullets), the line's height ("47 px" over a 24 px line), and the
  tolerance claim that implied 8 px of downward movement was free. A fourth
  described a rule that **does not exist**: a paragraph said "the stage rule
  is keyed on `:has(.player-probe)` … so its stage keeps the cap it had",
  but the only `.player-stage` rule this card adds is the unconditional
  declaration of the two custom properties — the `max-height` giveback it
  describes was a draft that never shipped (it is the same draft the card's
  Divergences block credited with 24 px and a 729.6 px stage bottom). All
  four are now stated as what the code does.

- **[Finding, not fixed here — a claim with nothing checking it]** The card's
  Design context requires the probe tint to be **distinct from CARD-267's
  crosshair tint and CARD-188's circles**. `admin.css` argues it at length
  (`--color-surface-hover` is the crosshair's, `--color-accent-tint` is the
  hint line's) and `TestSolverProbe_MarksCarryTheTint` has arms for the
  crosshair and the hint line *not repainting a probe cell* — but nothing
  measures the three tints apart as colours. Left as a finding rather than
  widened into this round, per the fix round's scope.

- **[Finding, not fixed here — `Touches` vs reality]** The card predicted it
  would touch `tokens.css`; it did not, and the probe tint is derived in
  `admin.css` from `--color-warning` and `--grid-paper` with `color-mix()`.
  Defensible (it does not widen the global token surface for a feature-local
  tint, which is the precedent the crosshair and the hint line set) but it is
  a deviation from `Touches`. The fix round adds no token either.

- **[Gate, final run on the fix round's tree]**
  `tests/test_puzzle_solver_*.py` (every file in the family) plus
  `tests/test_admin_design_tokens.py`: **581 passed, 0 failed, 0 skipped**
  (414.98 s). `tests/test_browser_fixture_scope.py`: **31 passed, 0 failed,
  0 skipped** (79.95 s) — which is the meta-test the round was briefed on
  (`test_the_riskiest_tests_pass_alone[test_puzzle_solver_fifth_rule]`) plus
  the registry equality that now accounts for all seven new node ids.
  **Skips attributed: there are none to attribute.** Every file in this gate
  is a browser file and the browser fixtures `pytest.fail` with the install
  instruction rather than skipping when Chromium is absent (ADR-0038/R8); the
  only skips this suite has anywhere are `DATABASE_URL`-gated, and no file in
  this gate has one. Counts for the record: the round started from
  `bc43eda5` with **5 failed / 574 passed** over the same set (1 named in the
  brief + 4 the brief did not know about) and ends with 0 failed.
  The full suite was NOT run (no flock taken on
  `meta/kanban/.full-suite.lock`; CARD-328 is under review in a parallel
  worktree). Every failure in this round was reproduced in isolation first,
  so none of the five was contention.
