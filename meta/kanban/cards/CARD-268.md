# CARD-268: Probe mode — hypothesis marks in their own tint, abandoned or committed as one transaction

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** `card/268-player-probe-mode`
**Worktree:** — (removed at merge; 61 worktree-only files — the mutation harnesses, raw verdicts, run logs and the renders — preserved at `~/Documents/nonogram-reviews/CARD-268/`, 82 files in all)
**Source:** quick — owner decision 2026-10-22 (player-convenience session, option 2: "for puzzles that need contradiction-probing add another color for probing cells", shaped in the same session into a transaction, not just a color); no handoff increment
**Idea:** —
**Wave:** 69 <!-- STAMPED 2026-10-30 at dispatch. Owner decision: "we agreed before to take 309+268". Its drafting-time conflict note named CARD-267 (crosshair) as the card it would serialize against -- CARD-267 merged `4b4a26e7` in wave 63, so that contention is gone. Against CARD-309 the measured Touches intersection is EMPTY. -->
**Depends on:** —
**Touches:** src/nonogram/admin/static/solver_state.js, src/nonogram/admin/static/solver.js, src/nonogram/admin/static/admin.css, src/nonogram/admin/templates/puzzle_solve.html, tests/test_puzzle_solver_probe.py, tests/test_puzzle_solver_resume.py, tests/test_puzzle_solver_page.py, tests/test_admin_design_tokens.py, tests/test_browser_fixture_scope.py (the `tokens.css` this line predicted was NOT touched — the marker is derived in `admin.css` from design tokens, which is the precedent CARD-267's crosshair and CARD-269's hint line both set; `page.py` and `browser_fixture_scope.py` are the two frozen censuses the suite enforces, added at review cycle 1 F-006)
**Review score:** **9.0 (cycle 2/3) — CERTIFIED**, 0 critical / 0 important; cycle 1 **7.5 NOT certified** on two owner-decided findings, one fix round between, plus **one build-fix round before review** and **one post-certification census fix at the merge gate**. Final gate **9967 passed / 27 skipped / 1 xfailed / 0 failed in 22:21**, exit 0.
**Started:** 2026-10-30T11:58:28Z
**Closed:** 2026-10-30T20:08:38Z
**Actual:** 1.0d
**Merge commit:** `2d9793e5` (gated tree `056bb48c`)
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
  checkpoint" would have carried the redo the player had then. The cost is
  bounded and reachable exactly one way — undo PAST the checkpoint while a
  probe is open, after which a redo that was pending is not restorable from a
  reload; the live player's redo is untouched. In every other case the cost is
  zero, because `record` has already dropped the redo stack itself, and
  opening a probe writes no save at all. Tested, both halves:
  `TestSolverResume_AReloadAbandonsTheOpenProbe::test_an_open_probe_saves_no_redo_stack`.
  **The REASON moved in fix round 1 and the divergence did not, and that is
  recorded rather than quietly left standing.** It used to be an
  impossibility: "the probe is one number, and from one number an open probe's
  own undone strokes cannot be told from strokes undone before it". F-002's
  fix makes the probe the strokes that predate it, so
  `undone.filter((stroke) => before.has(stroke))` IS exactly the redo stack
  the checkpoint had and carrying it became possible. It is still not
  carried — rule 9 asks for the save as of the checkpoint, AC-6's own control
  measures that it holds no redo stack, the cost is unchanged, and flipping it
  is a behaviour change plus a node-id rename in a frozen census. Recorded as
  a candidate follow-up for another card, not as a defect of this one.
- **Rule 10 is inconsistent with itself, and "as today" won.** It says Reset
  "behaves as today" AND that it "clears the board, the history and any open
  probe". Today's Reset does *not* clear the history: it records one undoable
  `resetStroke` through `record`, which is what makes "Undo brings them back"
  true (the confirmation says so). Shipped: the open probe is closed and the
  board is cleared by that same one undoable stroke, so the history behaves
  exactly as today. Closing the probe is also the only sane reading — a reset
  stroke left INSIDE the probe would make Contradiction un-reset the board.
  Tested by
  `TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_a_reset_clears_the_open_probe`,
  which is the test that actually holds this rule: it asserts the probe
  closes, every marker clears, the reset stays ONE undo step, and undoing it
  does not reopen the probe. (It was cited as
  `TestSolverProbe_CountersSeeProbeMarksAsMarks` — which merely resets between
  its two runs — "and the mutant `E2` below", and NO mutant E2 has ever
  existed on this card: the reference was written at `fe8ec27d` for a table
  that was never committed. Review cycle 1 F-003/F-004. The class the test
  lives in is named for commit and not for reset, which is wrong and is left
  wrong on purpose: the node id is registered in
  `tests/test_browser_fixture_scope.py`, and a rename is churn in a frozen
  census for no behavioural gain. Attribute by test, not by class name.)
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
  **The OPEN-probe half of the same edge was the one that mattered, and this
  bullet did not mention it** (review cycle 1 F-002): a stroke made before the
  probe, undone, and redone while the probe is still OPEN joined it, because
  the checkpoint was clamped with `Math.min` and a redo raises
  `done.length`. That is not a divergence to record — it contradicts rule 6's
  own words — and the owner fixed it (2026-10-30). It is no longer an edge at
  all: the probe holds the strokes that predate it, so there is no arithmetic
  to get wrong, and a redo of such a stroke can never make it a member. Four
  named `_RULE_CASES` entries hold rule 6's redo letter in both directions (a
  pre-probe stroke redone inside a probe stays out; the probe's own undone
  stroke redone inside it stays in; undoing past the open position and
  redoing; and the two in one sequence), where before it had none and ten
  anonymous corpus sequences asserted the wrong behaviour as correct.
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
  unpaid, which crosses a row mid-drag and reds 4 of the **6** cases of
  `tests/test_puzzle_solver_marking.py
  TestSolverMarking_KeyboardAndLabels::test_each_tool_acts_on_a_single_key_press`
  (Black, White and Clear by Enter and Space — `--collect-only` says 6, and
  "the 8 cases" was invented here and in four other places on this card:
  review cycle 1 F-003);
  (c) the same shift reds `tests/test_puzzle_solver_zoom.py
  TestSolverZoom_ZoomKeepsTheViewCentre` at 390 x 844 (a 30 x 30 at 300 % put
  the stage's own centre at 848.8 past a 844 px window, so
  `elementFromPoint` answered null);
  (d) paying for the row in `--player-chrome-h` — otherwise exactly the right
  property — also feeds the CELL CLAMP, whose height term binds at 1280 x 720:
  it takes a 15 x 15's cell from 23.4 px to 21.1 px and reds fit and
  geometry tests, the largest board's own fit among them (the count "five"
  that stood here has no node ids recorded beside it and is struck — the cell
  size is what is checkable, and it is enough to reject the alternative). So
  this alternative was rejected, and what pays is the TOOLBAR'S OWN
  `margin-top` — the sentence that used to end this line, "so the stage's cap
  pays and the board's fit does not", belonged to the unshipped `max-height`
  draft and contradicted the correction nine lines above it (review cycle 1
  F-003);
  (e) BELOW the board is worse, not better: a focusable control under the fold
  is reached by the same Tab walk and Chromium scrolls the page 233 px to
  reveal it, reddening the same keyboard test harder. (That test has 6 cases,
  not 8; the "5" recorded here has no case names behind it and is not
  re-derivable from this record, so it is struck rather than restated — what
  is checkable is the 233 px, and it is enough. Review cycle 1 F-003.)
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
  `tests/test_puzzle_solver_*.py` files run unedited, except for **two**, and
  no existing test BODY is edited in either:
  `test_puzzle_solver_resume.py`, which only gains AC-6's new test, and
  `test_puzzle_solver_page.py`, which only gains this file's mandatory
  `PAGE_ISOLATION` entry — a FROZEN CENSUS the suite itself enforces
  (`tests/test_browser_fixture_scope.py` asserts `PAGE_ISOLATION`'s keys
  against the family on disk, so the suite reds without it), and a census
  entry is not a test edit. Amended at review cycle 1 (F-006: the guardrail
  was violated in letter and held in substance, and a guardrail whose letter
  is quietly wrong stops being read). The same applies to
  `tests/test_browser_fixture_scope.py`'s own `ADDED_SINCE_BEFORE`, which
  every new node id of this card is registered in.
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

## [Owner decisions 2026-10-30, on review cycle 1's two gating findings]

Cycle 1 scored **7.5** and did not certify: two open Important findings, both
put to the owner because the card itself said to surface rather than pick.

### F-001 — the probe's membership moves to a DIFFERENT CHANNEL, not a stronger tint

**Owner's choice**, over "stronger tint, same channel". The reasoning the choice
rests on: a different channel cannot collide with **any** background tint —
crosshair, hover, or a fourth added later — whereas re-tuning the mix is a
tuning exercise against today's palette that a future tint re-opens.

The finding is a **shipped miss**, not a coverage gap, and the measurement
reproduces exactly (orchestrator, independently, from the shipped tokens):

| | value | |
|---|---|---|
| probe light | `color-mix(in srgb, #855d00 14%, #fffdf8)` | **(238, 231, 213)** |
| crosshair | `--color-surface-hover` `#f1ebdd` | **(241, 235, 221)** |
| | ΔRGB (−3, −4, −8) | **ΔE76 = 2.55** |

2.55 is at the just-noticeable-difference threshold — for two small
non-adjacent grid cells it is the same colour. **A token swap does not rescue
it:** `--color-warning-tint` (`#f6ecd4`) is only **ΔE 5.36** from the crosshair.
The FILLED variants are plainly apart (probe-ink vs cross-ink 27.4), so the
defect is confined to unknown/empty/maybe — which is the bulk of what a probe
paints.

**THE CHANNELS ARE CROWDED, and this is the constraint the fix must solve
rather than discover.** Measured on `admin.css`'s `.player-cell` rules:

- **`background`** — <!-- CORRECTED 2026-10-30 at cycle 2's F-003. The
  orchestrator wrote "9 claimants: the four `data-state` looks, …" and that was
  an uncounted tally — the very defect class (figures stated without the rows)
  this card's F-003 was closing. Counted from the rules by the fix round and
  re-counted independently by cycle 2's reviewer: **six** `.player-cell` rules
  declare a background (`admin.css` 529, 647, 1206, 1207, 1271, 1272), because
  only two of the four `data-state` looks declare one — the empty mark's is an
  `::after` and is counted on its own line below. Plus the probe's two before
  this card's fix = 8; after it, back to six. The correction is made HERE, at
  the claim, rather than only in the fix-round section ~230 lines down, which is
  what cycle 2 flagged: a stale figure left standing where a reader meets it is
  still a false claim however well it is corrected elsewhere. -->
  **six** `.player-cell` rules declared one before this card
  (`admin.css` 529, 647, 1206, 1207, 1271, 1272 — only two of the four
  `data-state` looks, since the empty mark's is an `::after`, below), plus the
  probe's own two while it still used the channel. **The probe's fix takes it
  back to six**, because the probe now declares no background at all.
- **`outline`** — taken by `.player-cell.is-hinted` (CARD-183/269).
- **`box-shadow`** — taken twice: `[data-state="filled"]`'s own division
  (CARD-270) and `.is-hinted`.
- **`::after`** — taken twice: the empty mark's dot and the maybe mark's.

So there is no unclaimed channel to take. **A candidate worth pricing first,
because it sidesteps ΔE entirely:** distinguish by **shape rather than
colour** — e.g. a *dashed* outline against the hint's *solid* one. Two
outlines that differ in style are distinguishable at any colour distance,
which makes the whole ΔE question moot for this pair instead of moving it.
Whatever is chosen, the separation gets **a test that measures it**, so mutant
**T1** (the tint at 1%, visually absent) stops surviving — today the only
boundary the suite holds is *string equality* of the computed value, which
ΔE 2.55 sails straight through.

**This is player-visible, so the standing rule applies: it needs a rendered
eyeball, not green tests.** Produce a render under
`~/Documents/nonogram-reviews/CARD-268/` showing a probe open **under a hovered
row**, which is the exact state F-001's scenario describes, plus the hint line
in the same frame since that is the other neighbour.

### F-002 — rule 6 is FIXED to match its own text, not recorded as a divergence

**Owner's choice**, over recording the shipped behaviour. Rule 6 says *"a probe
never contains strokes made before it started"*, and the shipped code
contradicts it: `nextProbe(..., "change")` is `Math.min(probe, done.length)`,
which can only **lower** the checkpoint — so a **redo raises** `done.length`,
the checkpoint stays, and `probeCells` adopts the redone stroke.

Reachable in five inputs: **mark A, mark B, Undo, Probe, Redo** → B comes back
wearing the probe marker, and Contradiction then takes away a mark the player
made **before** opening the probe. That is the behaviour the owner rejected:
restoring an earlier mark is not part of the hypothesis.

**The oracle shares the bug, and that is the sharpest part of the finding.**
`_oracle`'s redo branch encodes the same reading, so this card's strongest
mechanism — an independent second implementation — was defeated by a shared
assumption. **10 of the 300** corpus sequences reach the shape and pass,
asserting the wrong behaviour as correct. So the fix is in **two** places and
the oracle is the one that proves the fix: a corrected module against an
uncorrected oracle must red.

Add a named `_RULE_CASES` entry for the five-input sequence so rule 6's letter
has a control of its own, which it did not have.

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
    3 of the **6** cases of
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
    "4 of the cases ... with the stage 23 px lower" was true and misleading: it
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
  | **B1** | the pull-up rule -> `margin-top: 0` | no-ground class **3/3** red on **assertion 1** ("the toolbar's margin-top is 0 …") — premise reached and falsifiable; **siblings red: 4 of the 6 keyboard cases** (`White-Enter`, `White-Space`, `Clear-Enter`, `Clear-Space`) **and the solved-banner test** |
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

- **[CLOSED by review cycle 1's fix round, below]** The two findings this
  round left open are both closed by the next section: the unchecked
  distinctness claim became F-001 and is now measured, and the `Touches`
  deviation became F-006's second half and is now stated on the line itself.

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

### Fix round 1 of review cycle 1 (F-001 .. F-007; cycle 1 scored 7.5, no certification)

- **[F-001 — the channel, and the measurements that chose it]** The owner's
  decision of 2026-10-30 was *a different channel, not a stronger tint*. What
  ships: the marker is a **DASHED OUTLINE**, and the probe declares no
  `background` at all.
  - The defect reproduces exactly. Probe light
    `color-mix(in srgb, --color-warning 14%, --grid-paper)` resolves to
    **(238, 231, 213)**; the crosshair's `--color-surface-hover` to
    **(241, 235, 221)**; ΔRGB (−3, −4, −8), **ΔE76 2.55** — the JND. Probe vs
    the hint line 9.83, probe vs paper 10.32, `--color-warning-tint` vs the
    crosshair 5.36. Every figure re-derived in Chromium from canvas-resolved
    bytes.
  - **The channel census, counted from the RULES in `admin.css` and not from
    a tally** (the brief's "9 claimants" is itself a figure with no row count
    behind it; the real number is 8, and 6 of those are not this card's):
    `background` — **six** `.player-cell` rules declare one (the paper the
    cell starts on, a filled cell's ink, and the light/filled pair of each of
    `.is-crossed` and `.is-hint-line`), plus the probe's own two made eight;
    `outline` — **one**, `.player-cell.is-hinted`; `box-shadow` — **two**, a
    filled cell's division and `.is-hinted`'s paper ring; the cell's
    `::after` — **two**, the white dot and the "?". Only `background` had a
    queue.
  - **Alternatives priced, each on a measurement:**
    (a) *a stronger tint in the same channel* — rejected as the owner
    rejected it, and the measurement says why it would always be marginal:
    the binding ground is the crosshair, and the mix only clears a ΔE floor
    of 20 somewhere between **36 %** (18.92, red) and **38 %** (20.47, green)
    — mutants T1e/T1f below. An answer two percentage points from failing,
    against today's palette only.
    (b) *the cell's `::before`* — the one channel on `.player-cell` with
    **zero** claimants (CARD-188's circles are on `.player-clue-num::before`,
    a different element). Priced and rejected: it needs `position: relative`
    on the cell and pushes four bare keywords (`absolute`, `""`, `0`,
    `border-box`) through the token sweep, and it buys nothing the outline
    does not — an outline with a negative `outline-offset` costs no layout
    either, so this round's geometry (A2/B2) is untouched either way.
    (c) *`background-image` hatching* — rejected on the owner's own test: it
    is a sub-property of the shorthand six rules already spell, so any later
    `background:` on a cell wipes it silently. "Cannot collide with any
    background tint, present or future" is exactly what it fails.
    (d) *taking `outline` and letting the hint lose* — rejected on the
    cascade, measured: `.player-cell[data-probe]` and
    `.player-cell.is-hinted` are both specificity 0-2-0, file order hands the
    whole shorthand to the probe, and the cell that is both is REACHABLE
    (rung 3's reveal inside a probe records through the same `commit`). A
    third rule, `.player-cell.is-hinted[data-probe] { outline-color:
    var(--color-accent); }`, keeps the hint's colour and the probe's dash on
    that one cell — both signals, one channel.
  - **Shipped values and what they measure.** `--player-probe` is 86 % of the
    warning hue into the paper, rgb(150, 115, 35); `--player-probe-ink` is
    42 % into the paper, rgb(204, 186, 144), for a filled cell. Measured on a
    real page, one case per ground a probe cell can have: **66.26** on paper,
    **58.46** under the crosshair, **64.23** under the hint line, **71.47** on
    a filled cell, **56.85** on a filled crossed cell, **51.19** on a filled
    hint-lined cell. Floor **20** — **8.7x** the JND of 2.3, and **2.56x**
    inside the smallest shipped separation (51.19). Both ratios divided out,
    because a ratio asserted beside the numbers it is a ratio of is this
    card's own F-003 class: "a fifth" was wrong in the first draft of this
    very section, in `admin.css`, on the floor's own docstring and here.
  - **A claim this round found wrong in its own first draft.** The sentence
    "a filled cell's ground is `--grid-ink` and would swallow the dark ring"
    was never measured: it is **3.57:1**, past WCAG 2.2 1.4.11's 3:1 floor.
    The filled rule exists because 3.57 is the worst pairing on the board and
    the light variant takes it to **8.22:1** — a doubling, not a rescue. All
    six pairings as contrast: 4.33 / 3.70 / 3.75 (dark ring on paper /
    crosshair / hint line) and 8.22 / 5.19 / 4.01 (light ring on ink /
    crossed ink / hint-lined ink).
  - **What the fix also bought, and is now asserted:** the crosshair and the
    hint line keep their grounds on a probed cell. The two arms that used to
    assert the probe WON that tie now assert the pair COMPOSES — the ring is
    byte-identical to an uncrossed member's and the ground is the crosshair's.

- **[F-002 — rule 6 fixed in both places, and the oracle is the evidence]**
  - **`solver_state.js`.** The probe stops being one number. It is the frozen
    set of strokes the history already held — **on both stacks** — when it
    opened, so rule 6's sentence is true by construction and there is no
    clamp to get wrong. One number provably cannot carry it: an open probe's
    own undone stroke and a stroke undone before it opened leave
    `done.length` at the same value, so no arithmetic on it can tell which a
    redo is bringing back. `nextProbe("open")` takes the snapshot;
    `nextProbe("change")` now has **nothing to do**, which is why `solver.js`
    is unchanged by this fix. A new pure `probeStart(history, probe)` derives
    the old checkpoint back out as a PREFIX walk. `probeCells`,
    `abandonProbe` and `checkpointHistory` filter by stroke identity, which
    survives every history move (`undo` moves the same frozen stroke object
    onto `undone`; `redo` wraps that same object in a fresh entry).
  - **The oracle, fixed independently.** It does not count strokes at all: it
    MINTS an identity per mark and the probe is the set of identities that
    already existed. It reports the TOTAL number of pre-probe strokes still
    on the undo stack where the module derives a PREFIX length — so a
    sequence that broke the module's own prefix invariant shows up as a
    disagreement instead of as nothing.
  - **The demonstration, both directions.**
    *Corrected module against the uncorrected oracle REDS:* 2 of the 5 AC-9
    arms (`test_the_named_rule_cases_match_the_oracle`,
    `test_a_seeded_corpus_matches_the_oracle`), with **4 of the 4 new named
    rule cases** wrong and, in the corpora, **3 of 300** (seed 268) and
    **5 of 300** (seed 2680) sequences disagreeing on the member set.
    *Uncorrected module against the corrected oracle REDS:* mutant **R1**
    below re-injects the shipped defect at its single point and reds 3 arms.
    Reconciling with cycle 1's count: **3 of 300 and 7 of 300 sequences REACH
    the shape** (a redo of a pre-probe stroke inside an open probe) — ten
    across the two corpora, which is the reviewer's "10 of its 300"; the
    smaller numbers above are the ones still disagreeing at the END of their
    sequence.
  - **Four named `_RULE_CASES` entries**, where rule 6's redo letter had
    none: a pre-probe stroke redone inside a probe stays out; the probe's own
    undone stroke redone inside it stays in; undoing past the open position
    and redoing; and the two in one sequence. `_RULE_CASES` is 13 -> 17 and
    the count assertion inside the test moved with it.
  - **The `### Divergences` asymmetry is fixed in the record**: the
    closed-probe bullet now carries the open-probe half it never mentioned,
    says it was a contradiction of rule 6 rather than an ambiguity, and names
    the four controls. Rule 9's divergence bullet keeps the divergence and
    **changes its reason**, which is a declaration this fix invalidated: it
    used to rest on an impossibility ("from one number the two cannot be told
    apart") that is now false. Carrying the pre-probe redo stack became
    possible and is NOT taken — recorded as a follow-up for another card,
    with the reason (AC-6's control pins no redo stack, the cost is unchanged,
    and flipping it is a behaviour change plus a node-id rename in a frozen
    census).

- **[F-003 — the defect CLASS, not the four instances]** The class is *a
  figure summarising rows, stated without the rows*. Every such figure on the
  card and in `admin.css` was swept, not only the four named:
  - the keyboard test has **6** cases (`--collect-only`: Black/White/Clear x
    Enter/Space), and "the 8 cases" is corrected in all five places — card
    (b), card (e), the fix round's diagnosed-cause note, mutant B1's row, and
    `admin.css`'s own bullet;
  - alternative (d)'s closing sentence ("so the stage's cap pays and the
    board's fit does not") contradicted the correction nine lines above it
    and is replaced by what pays: the toolbar's own `margin-top`;
  - `CARD-268.md:109`'s "the mutant `E2` below" cited a mutant that has never
    existed on this card; rule 10's divergence is re-pointed (see F-004);
  - `admin.css`'s "a 6.6:1 ink" is **5.80:1**, re-derived;
  - **two more of the same class that nobody had flagged**: "five fit and
    geometry tests red" (alternative (d), repeated in `admin.css`) and
    "5 of 8 cases" (alternative (e)) have **no node ids recorded beside
    them** and are not re-derivable from the record, so both are struck and
    replaced by what IS checkable (the cell going 23.4 -> 21.1 px; the 233 px
    page scroll). A count with no rows behind it is struck, not restated;
  - and one this round found in its OWN new prose: the token test's docstring
    claimed the filled rule's existence assertion was "the only thing holding
    that rule". Measured by deleting the rule (T5): it reds that line **and**
    `test_the_four_states_stay_apart_under_the_tint`, and nothing else. The
    docstring now says both.

- **[F-004 — re-pointed, not renamed]** Rule 10's divergence bullet now cites
  `TestSolverProbe_CommitKeepsCellsAndDropsTheTint::test_a_reset_clears_the_open_probe`,
  which is the test that actually holds the rule, instead of
  `CountersSeeProbeMarksAsMarks` and the nonexistent `E2`. The class name is
  left wrong on purpose and the bullet says so: the node id is registered in
  `tests/test_browser_fixture_scope.py` and a rename is churn in a frozen
  census for no behavioural gain. Attribute by test, not by class name.

- **[F-005 — rule 3's hint clause now has a control]**
  `TestSolverProbe_MarksCarryTheTint::test_a_hint_revealed_inside_a_probe_belongs_to_it`
  drives the ladder to rung 3 with three real presses inside an open probe
  and asserts the revealed cell is a member beside a mark the player made,
  that it wears the hint's colour with the probe's dash, and that
  Contradiction takes it back, hint ring and all.

- **[F-006 — the guardrail's letter]** G-7 now names **both** exceptions and
  why `page.py`'s is structural (a frozen census the suite enforces, so the
  suite reds without it), and extends the same reading to
  `test_browser_fixture_scope.py`'s `ADDED_SINCE_BEFORE`. No existing test
  BODY is edited in either. The `Touches` line is corrected on the line
  itself: `tokens.css` was predicted and never touched (the marker derives in
  `admin.css` from design tokens, the precedent both neighbours set), and the
  two census files are added.

- **[F-007 — the open-probe focus scroll, measured; the margin is the
  finding]** `TestSolverProbe_AnOpenProbeKeepsTheFocusScrollInsideAHalfCell`
  measures `#puzzle-player`'s focus scroll with a probe OPEN. It holds, and
  thinly: **1280 x 720 — 11 px closed, 11 px open, half-cell 11.18 px**;
  **390 x 844 — 0 px closed, 7 px open, half-cell 7.1953 px**. So an open
  probe spends almost the whole tolerance at the width where the bar wraps.
  Shrinking the open bar is a design change (the wrap is deliberate), so it
  is recorded for the owner rather than acted on here; what this round buys
  is that the margin is now a number the next geometry change trips over.

- **[Mutant table]** Each mutant applied to the WORKING TREE (this round is
  not committed, so a byte copy taken before the mutation is the restore, not
  `git checkout HEAD --`), the target SHA-256'd before and after and the
  restore refused unless they match; `PYTHONDONTWRITEBYTECODE=1`, `*.pyc` and
  `__pycache__` swept before and after each. Harness in
  `scratchpad/card268fix2/` (never the shared scratchpad root). Every row
  names the CLAIM that fired, because a test short-circuits at its first
  failing assert.

  | id | mutation | what died, per claim |
  |----|----------|----------------------|
  | **T1** (the brief's headline) | `--player-probe` mix 86 % -> **1 %** (the marker visually absent) | ring class **3/6** red, all on **claim 3** (the ΔE floor): `paper` 0.72, `crosshair` 7.15, `hint-line` 6.62. The three `-ink` cases survive (they spend the other property) and so does the token sweep (1 % is still token-only) — which is exactly why the string-equality boundary cycle 1 had let this through at `39 passed` |
  | **T1g** (the value cycle 1 actually shipped) | mix 86 % -> **14 %** | ring class **3/6** red on **claim 3**: `crosshair` **2.36**, `paper` 10.20, `hint-line` 9.65. So the control reds the defect itself and not merely a caricature of it. The 2.36 against the 2.55 of cycle 1's own measurement is ROUNDING — the test reads the unrounded computed value where cycle 1 read canvas-rounded bytes — and both are an order of magnitude under the floor |
  | **T1e** (the claim's edge) | mix 86 % -> **36 %** | ring class **1/6**: `crosshair` alone, on **claim 3**, at **18.92** against the floor of 20. `paper` (26.8) and `hint-line` (24.9) survive — the floor is sharp on the BINDING ground, and the binding ground is the crosshair, which is the exact pair F-001 is about |
  | **T1f** (the other side of the edge) | mix 86 % -> **38 %** | **nothing** — 7/7 green at 20.47. T1e and T1f bracket the floor to two percentage points, so the floor is a boundary and not a restatement of the shipped value |
  | **T2** | the ring's width -> `0` | ring class **6/6** red on **claim 2** ("the ring is drawn at all"). Claim 3 is never reached: a colour cannot be seen through a ring that is not there |
  | **T3** | `dashed` -> `solid` | ring class 6/6 on **claim 2**, the SHAPE test on its **claim 3** (solid-vs-dashed), `test_the_four_states_stay_apart_under_the_tint` on the one-style assertion, `test_a_hint_revealed_inside_a_probe_belongs_to_it` on the dash, and `test_the_probe_tint_comes_from_tokens` on the strip's own control — **10 red** |
  | **T4** | delete `.player-cell.is-hinted[data-probe]` | **3 red**: the SHAPE test on its **claim 4** (the shared cell keeps the hint's colour), the F-005 arm on the same, and the token sweep on the rule's existence. The six ground cases SURVIVE — they never visit a hinted cell, which is what the two hint-aware controls are for |
  | **T5** | delete `.player-cell[data-probe][data-state="filled"]` | **2 red**: the token sweep's existence assertion and `test_the_four_states_stay_apart_under_the_tint`'s last line. The `ink` ΔE case SURVIVES at 69 — dE76 is dominated by lightness, so the floor does not bind there and the CONTRAST (3.57 vs 8.22) is the reason that rule exists. Recorded rather than papered over |
  | **R1** (the shipped F-002 defect, re-injected at its single point) | `nextProbe("open")` takes `done` only, not `done` + `undone` | pure-module class **3/5** red: the named rule cases, the seeded corpus, and the checkpoint-prefix arm — the corrected ORACLE against an uncorrected module, which is the other half of this round's evidence |
  | **R2** (edge) | `probeStart` returns `probe.length` instead of walking the prefix | **4 red**: the same three plus `TestSolverProbe_UndoClampsTheCheckpoint`. The prefix walk is not decoration — a set size overstates the checkpoint the moment a pre-probe stroke is undone |
  | **R3** | `abandonProbe` drops its membership guard (undo to empty) | **4 red**: both AC-2 arms and two pure arms |
  | **A2** (re-fired, unchanged) | air -> half a pixel | air class **2/4**: `phone-closed`, `phone-open` red; `desktop-closed`, `desktop-open` **SURVIVE**; no-ground class 3/3 red. **Exactly the recorded behaviour** — the board's top fraction at 1440 x 900 is `.797`, so `floor()` absorbs the half |
  | **B2** (re-fired, unchanged) | the pull-up -> `-8 px` | no-ground class **3/3** red; **both siblings survive** (6 keyboard cases + the solved-banner test, 7 passed). **Exactly the recorded behaviour** |
  | **S1** | the probe bar's `gap` doubled (a taller bar only where it WRAPS) | focus-scroll class **1/2**: `390x844` red on **claim 2** (scroll 15 px against a half-cell of 7.1953), `1280x720` survives; the air and no-ground classes **both survive 7/7** — so the new control is the only thing in the gate that catches a taller OPEN bar |

- **[Per-assertion / per-claim measurement of the multi-arm controls]**
  - `test_the_ring_is_apart_from_the_ground_it_is_drawn_on` — 6 cases, 3
    claims each (premise: a member, a non-member, the same state, the same
    ground; the ring is drawn; the ΔE floor). Claim 1 is reached and
    falsifiable: with the pointer left where a click put it, the `paper` and
    `ink` cases silently measured the CROSSHAIR's tint instead — caught by
    claim 1's own `(crossed, lined)` equality while the harness was being
    written, and fixed by moving the pointer off the board. Claim 2 is fired
    by T2, claim 3 by T1/T1e.
  - `test_the_ring_is_apart_from_the_hints_outline_by_SHAPE` — 4 claims;
    claim 3 fired by T3, claim 4 by T4.
  - `test_a_hint_revealed_inside_a_probe_belongs_to_it` — 3 claims; the
    composite claim fired by T4, the dash claim by T3.
  - `test_the_scroll_stays_inside_a_half_cell` — 2 claims per viewport; claim
    2 fired by S1 at 390 px only.
  - The two geometry classes are unchanged and re-measured: A2 and B2 above.

- **[The render — the owner's eyeball, F-001's exact scenario]** In
  `~/Documents/nonogram-reviews/CARD-268/`, desktop (1280 x 720) and phone
  (390 x 844), at `device_scale_factor=2`, stage crop and full page for each:
  `01-*` plain marks, `02-probe-open-*`, `03-probe-crosshair-hintline-*`,
  `04-probe-with-revealed-cell-*`. **What `03` shows** — the frame F-001 asks
  for: a probe open, the pointer on row 6 so the crosshair tints that whole
  row and column 12, and the hint ladder's highlighted line (rung 2, pale
  green) on row 0 in the same frame. Row 6 carries nine members — four
  filled, three white dots, two "?" — each wearing the dashed amber ring,
  plainly legible BOTH on the crosshair's warm ground and on a filled cell's
  ink; row 7's four filled members wear it on plain paper; row 1's eight
  filled marks and row 2's two white dots, made before the probe, wear
  **nothing**, so member and non-member are told apart at a glance in the
  state where the old tint could not be. `04` shows the one cell where the
  hint and the probe share a channel: the revealed cell at (0, 0) wears the
  hint's green ring **dashed**, with the hint's paper ring inside it. Console
  and page errors: none at either viewport.

- **[Gate, on this round's tree]** Every `tests/test_puzzle_solver_*.py` (all
  fifteen files) plus `tests/test_admin_design_tokens.py`: **591 passed,
  0 failed, 0 skipped** (412.57 s). `tests/test_browser_fixture_scope.py`:
  **31 passed, 0 failed, 0 skipped** (79.07 s). The previous round's figure
  over the same set was 581; +10 is exactly this round's ten new node ids,
  all registered in `ADDED_SINCE_BEFORE`.
  **Skips attributed: there are none to attribute.** Every file in the family
  is a browser file and the browser fixtures `pytest.fail` with the install
  instruction rather than skipping when Chromium is absent (ADR-0038/R8);
  `test_admin_design_tokens.py`'s one `skipif` is on `meta/design/` being
  present, and it is (that file reports 14 of 14 run). The only skips this
  suite has anywhere are `DATABASE_URL`-gated and no file in this gate has
  one.
  After that run, four TEXT-only corrections were made — three ratio claims
  and one set description, all of them this round's own F-003 class found in
  its own new prose — in `admin.css`'s comment, two docstrings of
  `test_puzzle_solver_probe.py` and this card. No rule, no selector and no
  line of JS moved. The two files that READ those texts were re-run on the
  final tree: `tests/test_puzzle_solver_probe.py` +
  `tests/test_admin_design_tokens.py`, **49 passed, 0 failed, 0 skipped**.
  The full suite was NOT run and no flock was taken on
  `meta/kanban/.full-suite.lock` (it did not exist at any point in this
  round; no foreign worktree held it).
