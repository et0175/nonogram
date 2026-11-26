# CARD-548: CARD-277's 225-cell zoom drag: reproduce it, or measure that it does not reproduce

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/548-reproduce-zoom-drag
**Worktree:** ../PythonProject4-card-548
**Source:** roadmap wave 23, cut 2026-11-26 on the owner's "card CARD-277's reproduction and carry on". This splits out step 1 of CARD-277 ("Reproduce it first ... This is the whole card"), plus the path capture of step 2.
**Idea:** —
**Wave:** 102
**Created wave:** 102
**Deferred waves:** 0
**Depends on:** —
**Touches:** nothing in `src/`; a scratch harness and instrumentation outside the tree (the scratchpad or `/tmp`-style location), and this card's notes. `tests/test_puzzle_solver_zoom.py` only if a run needs a temporary probe, and that probe is reverted before commit.
**UI surface:** —
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-26T14:02Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-277 records one observation from CARD-270's fix round (2026-10-22). A mouse drag at 200% zoom marked **225 cells instead of 5**: every cell of the 15×15 board. Two tests in `tests/test_puzzle_solver_zoom.py` failed together:
- `test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line`
- `test_marks_zoom_and_circles_survive_crossing_both_ways`

It did not reproduce in four later runs. CARD-277 names three suspects, each needing a different fix:
1. a redraw mid-drag: a real bug in `solver.js`;
2. under-stepped synthetic mouse moves: a test artifact;
3. scroll skew under `elementFromPoint`: could be either.

CARD-277 forbids writing a fix against a suspect. This card does only the reproduction, so the fix card starts from a measured fact.

## What to implement

1. **Declare the budget before running.** Default:
   - 50 runs of the two tests alone, by node id;
   - 10 runs of the zoom file with `tests/test_puzzle_solver_page.py` and the other browser files of the solver family. CARD-277 says the one failure was in a multi-file run. Re-derive the twelve-file set from CARD-270's notes if it can be identified; otherwise state the set used.

   Run under `caffeinate -i`. A run that overlaps a sleep in `pmset -g log` is excluded and counted separately, because Playwright's timers count time asleep.
2. **Instrument so a hit is diagnosable.** Before the loop, add instrumentation that would capture, for each `pointermove` of the drag:
   - `gesture.path` (or the stroke's cell list);
   - the board's scroll offset and bounding rect;
   - whether a `redraw()` fired.

   For example, a page-side `addInitScript` hook or a temporary console log read by the test. The instrumentation must not change behaviour.
3. **If it reproduces:** record the captured path and say which of CARD-277's three suspects it selects, and why: a contiguous sweep, a jump, or a superset. **Do not fix anything.** The fix is CARD-277's.
4. **If it does not reproduce:** record the run count, the selections, the zoom level, the load average, and the instrumentation that would have caught it.
5. Leave nothing behind. `src/` is unchanged and any temporary test probe is reverted. The commit carries only this card's notes, and the net test count is 0.
6. Do not run load processes to provoke it. If you judge load necessary, cap it at 8 processes, start and kill them in the same command with a trap, and say so.

## Acceptance criteria

- AC-1: the budget is declared in the notes before the first run, and the result is reported against it: N runs per selection, hits, excluded sleeps, and load. A "0 of N" result is a valid outcome.
- AC-2: the instrumentation's ability to see a hit is shown, not asserted. Demonstrate on one deliberately broken run that the capture records a path; for example, a forced `redraw()` mid-drag injected only in the scratch harness, or an under-stepped drag. Then remove it.
- AC-3: `git diff --name-only main...HEAD` lists only `meta/kanban/cards/CARD-548.md`.
- AC-4: if it reproduces, the captured path and the suspect it selects are recorded. If it does not, the notes give CARD-277 a recommendation: keep it, adding the permanent count detector of its AC-4, or close it as unreproduced.

## Worktree notes

### Implementation round 1 (2026-11-26)

**Budget, declared before the first run (AC-1).** Reduced from the card's default to keep the card's
wall clock under about 90 minutes:
- **Selection A, the two tests alone by node id:** 50 runs, as the card asks.
- **Selection B, the family set:** **6 runs, reduced from 10**, and stopped early at 60 minutes of B wall
  clock if a run takes longer than estimated (about 650 browser tests per run, est. 6-8 min each).
  The set is 13 files: CARD-270's failing selection re-derived from its notes, which is the eleven
  `test_puzzle_solver_*.py` files that existed on 2026-10-22 other than that card's own two (`fifth_rule`, new,
  and `page`, edited): `brush_menu clues hint marking maybe mirror percent phone progress resume zoom`, plus
  `tests/test_puzzle_editor_ui.py` (491 tests then). `test_puzzle_solver_page.py` is added, as this card asks,
  which also makes the set a superset of CARD-270's 558-test "twelve-file set" reading. Files added to the
  family after 2026-10-22 (`crosshair line probe solved_reveal fifth_rule`) are left out.
- **Uncounted:** the AC-2 demonstration runs (deliberately broken, see below). They are not in A or B.
- Zoom level: 200 % (the drag test) and 150 % (the redraw test), as the tests set them. No load processes.

**Verdict: did not reproduce. 0 hits in 50 runs of the two tests alone, and 0 in 6 runs of the family set,
with no sleep exclusions.** A reading of `solver_state.js`, described under "What the 225 can and cannot be"
below, also shows that none of CARD-277's three suspects can produce 225 marked cells by itself.

**Results against the budget (AC-1).** Every run used `-o addopts= -rfs -p no:cacheprovider`, explicit node
ids or files, and `caffeinate -i`. Each run was serial. `PYTHONPATH` pointed at this worktree's `src`, and the
probe printed `nonogram` resolving there on every run. `NONOGRAM_FULL_SUITE_LOCK` pointed at a scratch path,
and `DATABASE_URL` was unset.

| selection | runs | collected / run | passed | failed | skipped | hits | sleep-excluded | wall clock |
|---|---|---|---|---|---|---|---|---|
| A: the two tests by node id | 50 | 2 | 100 | 0 | 0 | **0** | 0 | 14:08:21Z to 14:10:19Z, 2.1 to 3.1 s per run |
| B: the 13-file family set | 6 | 648 | 3888 | 0 | 0 | **0** | 0 | 14:10:31Z to 14:57:22Z, 402 to 491 s per run |

- **Sleep check.** `pmset -g log` showed the last Sleep or DarkWake at 08:42:49 +0200 (06:42Z) and the last
  Wake at 08:50:21 +0200. No run overlapped a sleep, so nothing was excluded.
- **Load.** There were no load processes of my own. The machine has 11 cores, and another session was active.
  The 1-minute load average sampled around each run was 3.08 to 12.75 for A and the demos, and 4.33 to 8.44
  for B.
- **Zoom.** The drag test ran at 200 %, the zoom it sets itself. The redraw test ran at 150 %, crossing 1440 to
  phone width and back.
- **Capture of every counted drag (56, from A's 50 and B's 6).** The start cell was `(0, 0)`. The path was
  exactly `(0,1) (0,2) (0,3) (0,4)`, and 5 cells were marked. During the gesture there was one `drawBoard` and
  one live table, with no redraw and no table replacement. There were 0 scroll events mid-gesture, and the
  stage scroll was `[0, 0]` throughout.

**Instrumentation.** The probe is a scratch pytest plugin, `card548_probe.py`, loaded with `-p`. It lives outside
the tree, and no test or `src` file was touched.
- **The hook.** It wraps Playwright's `BrowserContext.new_page`, so every page any test opens gets one
  `add_init_script`.
- **The listeners.** These are passive listeners on `window` in the capture phase, for
  `pointerdown`/`pointermove`/`pointerup`/`pointercancel`, plus `scroll` and `resize` while a button is down.
- **What it records per event.** For each event it records:
  - the cell under `elementFromPoint(clientX, clientY)?.closest("td.player-cell")`;
  - the stage's `scrollLeft`/`scrollTop` and rect;
  - the board's rect;
  - the `nonogram-player-board-draw` mark count, one per `drawBoard`, which is the redraw signal;
  - an identity number for the live `table.player-board`, so a replaced table shows;
  - `--player-zoom`, the page scroll and the viewport.
- **Why the path equals `gesture.path`.** The cell call is `cellUnder`'s own, made at the same coordinates in
  the same dispatch. Applying the pointermove handler's rule (push only when the cell differs from the last)
  to the recorded cells therefore gives exactly `gesture.path`.
- **Why it does not change behaviour.** The handler makes the same `elementFromPoint` call on the same event,
  so the probe adds no new layout work.
- **How it is read.** At the end of each test's call phase, every open page is read and the marked count is
  logged to JSONL.

**AC-2: the capture sees a hit, demonstrated on deliberately broken runs.** These ran with `CARD548_BREAK`, in the
scratch harness only, on the drag test alone. They are not counted in A or B, and the plugin was not loaded
in any other way. In each case the break fired on the 2nd pressed pointermove.

| break | test | marked | captured path |
|---|---|---|---|
| `zoom:-2`: two zoom-out clicks from JS (`element.click()`) | **failed** | 7 | `(0,1) (0,2) (0,4) (0,6)` |
| `zoom:4`: four zoom-in clicks | **failed** | 4 | `(0,1) (0,2) (1,2) (1,3)` |
| `understep`: `Mouse.move` forced to `steps=1` | passed | 5 | `(0,4)` |

- **`zoom:-2`.** The path is a jump: the zoom fell from 2 to 1.5 and the board rect shrank from 764 to 616 px
  wide, while the pointer kept its CSS coordinates.
- **`zoom:4`.** The path left the row, with the zoom at 3, the stage scroll at `[35, 40]`, and a stage `scroll`
  event logged mid-gesture. This is the signature of suspect 3.
- **`understep`.** The path is one jump. It passed only because `dragLine` fills the span.
- **Draws and table across all three.** The draw count and the table identity stayed at 1, so a button zoom
  does not redraw a 15 x 15. Against that, the probe's draw and table fields are the redraw detector for
  suspect 1.

The plugin's break code exists only in the scratchpad.

**What the 225 can and cannot be.** This section is code reading, cited by name, at `d90753df` (the board as it
stood on 2026-10-22, the observation's day) and at HEAD.
- **A drag stroke is capped at 15 cells.** `dragStroke` is `makeStroke(dragLine(start, path), tool)`, and
  `dragLine` emits only cells on the start cell's row or on its column.
  - At `d90753df`, off-line path cells were skipped.
  - Since 2026-11-17 they are projected onto the line.
  - Either way, one drag stroke on a 15 x 15 covers **at most 15 cells**, whatever `gesture.path` holds.
- **What that rules out.** CARD-277's "225 marked cells means the path genuinely accumulated 225 distinct cells"
  does not hold. All three suspects act through path content, so each can produce a *wrong line*: the jump and
  off-row paths above produced 7 and 4 cells. None of them can produce the whole board.
- **The twin failure.** It was `test_marks_zoom_and_circles_survive_crossing_both_ways`, and that test makes no
  drag at all. It uses `_set`, zoom buttons and viewport changes on a 30 x 12 board. A common cause of both
  failures therefore cannot be in the drag handler.
- **Remaining candidates.** These are unmeasured and not diagnosed. They lie outside the stroke: board state
  present before the drag, a page or board other than the intended one, or the reading of the failure. "225"
  may be an inference from a pytest dict diff, which CARD-270's note does not quote.

**AC-4 recommendation for CARD-277: close it as unreproduced.** Do not adopt its AC-4 count detector as written,
for three reasons:
1. **The measured result.** It is 0 of 50 alone and 0 of 6 in the family set (3,888 test executions). The
   capture would have caught a jump, a sweep or a redraw.
2. **No suspect fits.** On both the 2026-10-22 code and HEAD, none of the three suspects can produce 225 cells
   through `dragStroke`.
3. **The count detector duplicates what exists.** The existing assertion is an exact marked set, and pytest
   already prints its size difference.

If the owner wants a cheap detector to outlive this card, the one that would separate the remaining
candidates is a pre-drag assertion. It would go into the existing
`test_a_mouse_drag_at_200_percent_still_marks_along_the_dragged_line`, as one line before `_drag`, and would
not be a new test class: the board's marked set is empty before the press. That would name "state before the
drag" if this recurs. The probe in the scratchpad (`card548_probe.py`, `loop.py`) can be lifted into a card if
it does recur.

**Left behind: nothing.** `src/` is unchanged and no test file was edited, so the net test count is 0. AC-3: this card's commit
carries only `meta/kanban/cards/CARD-548.md`. The check is `git diff --name-only main...HEAD`, run after the
commit.

### Review cycle 1 (2026-11-26)

[Review 1/3] Score: 9.5, CERTIFIED. Nothing gating. Every claim the verdict rests on was re-derived.
- **Claim 1 holds at d90753df and at HEAD.** `dragStroke` is `makeStroke(dragLine(start, path), tool)`, and `dragLine` emits only cells of the start cell's row or column. At d90753df it skipped off-line path cells; at HEAD it projects them. The stroke is applied to `history.board` (preview and commit alike), so one drag adds at most one line, 15 cells, to what was already there. Attempts to break it found nothing: every board-changing site in `solver.js` at HEAD was listed. The anchor tap is `dragStroke(from, [done.start])`, in line only. The line view's stroke is one line. Click, hint and mark strokes are one cell each. `resetStroke` sets every cell to undecided, which `_marked` does not count. `pointercancel` only reverts the preview. No path through `pointermove`, `pointerup` or `dragStroke` marks a second line.
- **Claim 2 holds at both revisions.** `test_marks_zoom_and_circles_survive_crossing_both_ways` uses `_set`, which calls `setBoard`, plus `_zoom_to` button clicks and `set_viewport_size`. It has no mouse, drag or pointer call.
- **Claim 3: the counts match.** I recounted from the JSONL with my own script. The two tests: 50 runs, 100 passed, 0 failed, 2 collected each. The family set: 6 runs, 3888 passed, 0 failed, 648 collected each. All 56 drag captures show the path `(0,1)..(0,4)`, 5 marked, and no redraw or scroll mid-gesture. `pmset`'s last sleep ended at 08:50:21 +0200, before the first run at 14:06Z.
- **Claim 4 (AC-2): re-run once, not counted.** `zoom:-2` on the drag test alone gave 1 failed, 7 marked, and the path `(0,1) (0,2) (0,4) (0,6)`, which matches the notes' row.
- **Claim 5 (AC-3).** `git diff --name-only main...HEAD` lists only this card.
- **ADR-0039/R4 holds.** The other 5 rules (CON-005, CON-009, CON-010, CON-011, CON-012) are unchecked: no_eligible_fact.

Findings:
- F-001 (low, non-gating) The 0-of-56 figure was measured on HEAD's drag test, not on the one that failed. HEAD's version gained CARD-404's `scrollIntoView` and 150 ms wait before the drag, and `dragLine` now projects off-line cells. These are the conditions suspect 3 depends on, and the notes do not say the test text changed. It does not move the verdict, because the structural argument holds at both revisions.
- F-002 (low, non-gating) Two more AC-2 demos ran and are not reported: `redraw` and `scroll`. Both passed with no effect: the redraw break redrew nothing, and the scroll break left the stage at `[0, 0]`. The probe's docstring still says `redraw` "redraws the board". The draw and table fields are called the redraw detector without being shown to rise. They do rise in the counted family data: `test_the_highlight_survives_a_redraw` and `test_a_one_pixel_resize_keeps_the_highlight_on_the_same_cell` show draws 2 to 4 and table 1 to 2, in 6 of 6 runs. The claim is true, but its evidence is not in the notes.
- F-003 (info, for CARD-277) `_marked` keeps every cell that is not undecided. So "225 marked" means no undecided cell was left: black or white, not 225 black. That fits a board set or restored whole better than any painted path. pytest prints the size difference ("Left contains 2 more items" in this review's re-run), which supports the notes' remark that 225 may have been read off that diff.

**Recommendation, judged: agree.** Close CARD-277 as unreproduced, and do not build its AC-4 count detector as specified. Its mechanism section rests on "225 marked cells means the path genuinely accumulated 225 distinct cells", and that is false at both revisions: a path cannot produce the whole board through `dragStroke`. So none of its three suspects can explain the symptom, and a detector aimed at them targets a refuted mechanism. The existing exact-set assertion already reports the size. A recurrence belongs on a new card, starting from state that exists outside the stroke. The optional pre-drag "board is empty" line is a cheap way to name that.

Verdict: CERTIFIED.
