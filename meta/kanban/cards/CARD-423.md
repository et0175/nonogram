# CARD-423: Portrait phone tap targets are 44 x 36 px — the compact toolbar sets a width floor and no height floor

**Status:** done
**Priority:** P2
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The CSS is one declaration beside the `min-width: 44px` rules it joins. The cost is the three parts that are not CSS: widening `_LABEL_BOXES` to the four of the nine it cannot currently see, and re-measuring the four viewports because the toolbar gets taller and the board absorbs it. The owner ruled D1 below at drafting time, so no decision is outstanding. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/423-portrait-tap-targets
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-423
**Source:** my own measurement of the live site (https://nonogram.adverax.io) on 2026-11-11, at the owner's "check the live site on my phone", carded on their "card the 44px portrait touch targets". **Measured under Playwright device emulation (iPhone UA, touch, DPR 3), not on a physical phone** — the geometry is the page's, but no finger has tested it.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_phone.py
<!-- Derived 2026-11-11 by reading which file holds the measured behaviour: the compact block in admin.css ("Compact toolbar", CARD-401) and the one test that asserts the 44 px claim. `src/nonogram/admin/static/tokens.css` is read, not edited (`--control-h: 36px` stays: it is the whole panel's control height, not the player's). Nothing under `player/` changes — `admin.css` is in `COPIED_FROM_ADMIN`, so the public player gets this by the build-time copy and the byte-identity check carries it. Conflict edges: none open (CARD-400..422 are all `done`). -->
**Review score:** 8.5 (cycle 3)
**Started:** 2026-11-11T13:20:00Z
**Closed:** 2026-11-11T15:05:00Z
**Actual:** 3 review cycles + 4 fix rounds (wall clock excluded, owner ruling)
**Merge commit:** 40f12185
**Blocked by:** —

## Why this card exists

On production at 390x844, 852x393 and 874x402 (portrait), **nine toolbar controls are under the 44 px floor in height**: the brush trigger (Black), the Region toggle, Undo, Redo, Reset, Hint, `-`, `+` and Probe. Seven of them measure 44 x 36; **the two zoom steppers measure 44 x 38.78** (their text glyph's line box is taller than `--control-h`) — corrected by the implementation's own measurement, which also found the admin page carries an eighth at 36 (Check). The drafting figure said 36 for all nine; it was read off the CSS token rather than off the steppers. Either way the floor is missed and the fix is the same.

The mechanism is in `admin.css`'s compact block (`@media (max-width: 600px), (max-height: 500px)`): `.player-tool-trigger`, `.player-history > .btn`, `.player-zoom .btn` and `.player-probe > .btn` each get `min-width: 44px` and **no height floor**, so the height falls through to `.player-toolbar .btn`'s `min-height: var(--control-h)`, which `tokens.css` sets to 36px.

Two things in the tree say 44 px was meant in both dimensions rather than in width alone. `.player-zoom-readout[role="button"]`, in that same compact block, already carries `min-height: 44px`. And CARD-402's landscape side-column block sets `height: 44px; min-height: 44px` on every `.btn` — which is exactly why the same measurement at 844x390 found **no** control under 44 px and portrait found nine. Portrait is the one path where the floor was written in one dimension.

**CARD-401 is not in breach.** Its AC-6 reads "at least 44 px wide and `--control-h` tall", so 36 px tall satisfied it as written, and its test asserts `box["button"] >= 44` on the width alone. The gap is in the rule, not in the implementation of it — which is why this is a new card and not a regression on a closed one.

The cost is not the declaration. Raising the floor makes the portrait toolbar taller: four rows at 44 px instead of 36 px predicted about +32 px of chrome; **measured, it is +24.0 px** (183.8 -> 207.8 at 390x844) — three of the four control rows gain the full 8 px and the fourth is absorbed by the counters line above the probe row, which was already taller than its contents. The board absorbs it rather than the page overflowing — `solver.js`'s `measureStageTop` writes the measured `--player-stage-top`, which both the stage's cap and the cell-height term read — so what actually gets smaller is the cell, and on the owner's 30x30 class of board that cell is already 9.1 px. That trade is a decision, not a measurement. Separately, `_LABEL_BOXES` only finds buttons that carry a `.player-btn-label`, so the brush trigger, Region, `-` and `+` — four of the nine — are outside the existing assertion entirely.

**[OWNER RULING 2026-11-11]** **D1: 44 px tall for all nine, and the board gives up the portrait height it costs (predicted ~32 px, measured 24).** Declined: keeping 36 px, and raising only the controls where a mis-tap is expensive (Reset, Probe). So the floor is ONE rule at every compact viewport — which is what the compact block's own comment and CARD-402's landscape block already state — and the author implements it without re-asking, recording what the cell size became (AC-2). If the 30x30's cell turns out to be unusable at the new size, that is CARD-406/407's Fit question, not a reason to lower this floor.

## What to implement

1. **A height floor in the compact block,** on the same selectors that already carry `min-width: 44px`, so one condition governs both dimensions. The comment's line "Every button is at least 44 px wide and `--control-h` tall" becomes "at least 44 x 44 px": that sentence *is* the rule, so it moves with it. `--control-h` itself does not change — it is the whole panel's control height, and the player is not the only thing that reads it.
2. **Re-measure and record** the portrait toolbar's rows and height, the stage's measured top and the resulting cell size, and that no horizontal page scroll appeared. Landscape should not move at all; if it does, CARD-402's block has been reached and that is a finding, not a re-pin.
3. **Nothing in `player/`.** No public-mode duplicate cell is added (owner test budget, 2026-11-07): the behaviour is verified once on the admin page and the copy's byte-identity check carries it to the public player.

## Acceptance criteria

- **AC-1** (the floor holds in both dimensions): at 390x844 and 844x390, every control inside `.player-toolbar` — the brush trigger, the Region toggle, Undo, Redo, Reset, Hint, Check (admin only), Probe, `-`, `+` and the zoom readout — has a border box at least 44 px wide **and** at least 44 px tall. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar::test_icons_only_when_compact`, **changed**: `_LABEL_BOXES` widens from `.player-btn-label` holders to every visible button in the toolbar and returns height beside width, and the docstring's "at least 44 px wide" is retired for the two-dimensional claim. **Plant:** drop the new `min-height` and the 390x844 cell reds while 844x390 stays green — one control, which also proves the two media blocks are independent.)
- **AC-2** (the board absorbs it, the page does not): at 390x844 on a 30x30 board there is no horizontal page scroll, and the cell size after the change is recorded in Worktree notes as the figure it became. (test: the existing `TestSolverPhone_BoardFitsThePhoneWidth` and `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit` cells, which read the measured stage top, pass unchanged — a changed cell size that reds them is the signal that the fit formula, not the toolbar, needs the card.)
- **AC-3** (desktop and landscape unmoved): at 1280x720 and 1440x900 the toolbar geometry is unchanged, and at 844x390 CARD-402's side-column measurements are unchanged. (test: the existing brush-menu slot-geometry, percent and maybe cells, plus CARD-402's own cells.)

**Net test count: 0 added** — one existing parametrised cell gains a dimension; no new module, class or node id.

## Requirements

No AC in `meta/architecture/requirements.yml` pins a tap-target minimum — the word "compact" does not appear there, and the only 24 px figure is a *cell* floor in FR-044's deep-row-clue criterion. So this card **amends no requirement**: the rule stays where CARD-401 put it, in the compact block's comment and in the one test. If the owner wants it in the registry instead, that is a new line under FR-044 and the author asks for the id rather than inventing one (ADR check refs must be honest).

## Verification

Measured in a browser, not asserted from CSS, and recorded in Worktree notes with the numbers: **390x844**, **844x390**, **1280x720**, **1440x900**, each on a 15x15 board and on a 30x30 stored grid. For each: every toolbar control's two dimensions, the toolbar's height and row count, the stage's measured top, the cell size, and no horizontal page scroll.

## Worktree notes

- **[Env]** forge version unresolved: no `.claude-plugin/plugin.json` at the executing path, and this project has no `meta/.skills.yml`, so no `forge.min_version` comparison ran and no `models:` block exists (agents spawn without a `model:` override, inheriting the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`, command `./.venv/bin/python -m pytest`. **But that command is exit 127 in a worktree** — no card worktree has a `.venv` (the path is relative). The gate in this worktree runs as `make test-gate PY=/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`, or that absolute interpreter directly for a single module.
- **[Impact scope]** Player card: the gate is the player/solver test set (`tests/test_puzzle_solver_*.py`, `tests/test_player_*.py`), not the generator or book suites. The full suite runs at the merge gate; acquire `meta/kanban/.full-suite.lock` before any full run.

### [Implementation] CARD-423 — the floor is one declaration; the measurements are the work

* **AC-1:** test `TestSolverPhone_CompactToolbar::test_icons_only_when_compact[390-844-True]` red → green (the `[844-390-True]` cell green throughout — the plant's own proof that the two media blocks are independent).
* **AC-2:** tests `TestSolverPhone_BoardFitsThePhoneWidth`, `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit`, `TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit` green → green (unchanged, no re-pin); cell recorded below, no horizontal page scroll.
* **AC-3:** desktop (1280x720, 1440x900) and landscape (844x390) measured identical before and after; the brush-menu slot, percent and maybe cells green → green. CARD-402's block was not reached.
* Re-pinned (not an AC, and not weakened): `TestSolverPhone_MirroredGutterSticks`'s two scrollport figures, red → green on the measured new geometry.

**The change.** Two files, as predicted by `Touches:`.

* `src/nonogram/admin/static/admin.css`, the "Compact toolbar" block
  (`@media (max-width: 600px), (max-height: 500px)`): one new declaration,
  `.player-toolbar .btn { min-height: 44px; }` — written on the *same
  selector* whose `min-height: var(--control-h)` it overrides, so the floor
  and the thing it replaces read as one rule rather than as a scatter of
  per-group overrides. It was NOT added to the three `min-width: 44px` rules
  individually (`.player-tool-trigger`, and `.player-history > .btn,
  .player-zoom .btn, .player-probe > .btn`), because those three do not cover
  the Region toggle — `.player-region` lives in `.player-tools` and takes its
  44 px width from its own content, not from a `min-width` — nor the Reset
  dialog's two buttons. One selector covers all of them. `tokens.css` was
  read, not touched: `--control-h` is still 36px.
* The comment bullet "Every button is at least 44 px wide and `--control-h`
  tall" is now "at least 44 x 44 px", with the measured before/after beside
  it. That sentence IS the rule, so it moved with the code.
* `tests/test_puzzle_solver_phone.py`: `_LABEL_BOXES` is now
  `_CONTROL_BOXES` — it selected `.player-btn-label` holders, which is why
  four of the nine offending controls were invisible to it. It starts from
  `.player-toolbar button, .player-toolbar [role="button"]` and returns
  `height` beside `button` (width). `_UNLABELLED` / `_CONTROLS` name the
  widened expected set, so the measurement cannot silently stop seeing a
  control again.

**Naming the readout.** The zoom readout is a `<span>` the player gives
`role="button"` whenever there is a Fit to go to, so AC-1 is right that it is
a control. Its `aria-label` carries the live zoom ("Zoom 100%. Fit the whole
board" / "Zoom: Fit. Back to the last zoom"), so `_CONTROL_BOXES` keys it on
its own `data-player-zoom-readout` hook instead — otherwise the name
assertion would pin which zoom the board happened to open at. Measured, not
assumed: the 30 x 30 opens at **100%**, not at Fit, in both compact cells.

**AC-1: test `TestSolverPhone_CompactToolbar::test_icons_only_when_compact`
red -> green.** The plant ran first, as TDD asks: with the test widened and
the CSS untouched, `[390-844-True]` red on `assert (44 >= 44 and 36 >= 44)`
for the brush trigger — a height, not a selector or fixture error — and
`[844-390-True]` green in the same run. Re-run after dropping the new
`min-height` again: same split. That is AC-1's plant and it also proves the
two media blocks are independent (portrait's floor is this card's; landscape's
is CARD-402's).

**AC-2: the existing cells pass unchanged** —
`TestSolverPhone_BoardFitsThePhoneWidth` (both cells, all three boards),
`TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit` (its 14.39 px pin)
and `TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit` all
green, no re-pin. No horizontal page scroll at any viewport measured.

**Two other cells DID move, and were re-pinned rather than weakened** —
`TestSolverPhone_MirroredGutterSticks::test_both_bands_are_in_view_at_every_corner`
(600x844) and `::test_a_390px_phone_keeps_its_cells_rather_than_its_row_clues`
(390x844). Neither is an AC-2 cell: they pin CARD-271's *scrollport*
geometry — how much the stage overflows and how far it scrolls — which is
exactly the quantity this card spends. Measured, not inferred:

* 600x844: the compact toolbar draws **two** control rows and grew
  111.8 -> 119.8 px (+8), so the stage's cap is 8 px shorter: vertical
  overflow 87 -> **95**, and the matching `scroll` figure with it.
* 390x844: **four** control rows, 183.8 -> 207.8 px (+24), so the
  scrollport is 424 -> **400** px tall and its overflow 159 -> **183**.

Both lines already carried the same kind of dated history (CARD-403,
CARD-406, CARD-409, CARD-411 each moved them); this card's figures are
appended in the same form, naming the mechanism. The claim each test makes —
the bands stay in view where there is room, and at 390 px the cells win over
the row band — is untouched: `keeping` is still `[False, True]`, the band is
still 272.2 px, a right-hand cell still takes its own tap.

**AC-3: desktop and landscape unmoved** — every number at 1280x720, 1440x900
and 844x390 is byte-identical before and after (table below). CARD-402's
block was NOT reached: at 844x390 every control measured 44 x 44 px *before*
this card too.

### Measured, in the browser (admin solve page, Chromium under Playwright, this host)

Toolbar rows = distinct control-row tops. "stage top" is the measured
`--player-stage-top` solver.js writes. Nothing below was asserted from CSS.

| viewport | board | toolbar rows x height | stage top | cell | h-scroll |
|---|---|---|---|---|---|
| 390x844 | 15x15 | 4 x 183.8 -> **4 x 207.8** | 403.88 -> **427.88** (`404px` -> `428px`) | 14.391 -> **14.391** | no |
| 390x844 | 30x30 | 4 x 183.8 -> **4 x 207.8** | 403.88 -> **427.88** | 14.391 -> **14.391** | no |
| 390x844 | 15x15 fit-bound\* | 4 x 183.8 -> **4 x 207.8** | 403.88 -> **427.88** | 16.359 -> **16.0** | no |
| 600x844\*\* | 30x30 | 3 x 111.8 -> **2 x 119.8** | 331.88 -> **339.88** | 14.391 -> **14.391** | no |
| 844x390 | 15x15 | 6 x 296.58 (unchanged) | 80 (unchanged) | 14.391 (unchanged) | no |
| 844x390 | 30x30 | 6 x 296.58 (unchanged) | 80 (unchanged) | 14.391 (unchanged) | no |
| 1280x720 | 15x15 | 2 x 98.58 (unchanged) | 253.58 (unchanged) | 20.656 (unchanged) | no |
| 1280x720 | 30x30 | 3 x 98.58 (unchanged) | 253.58 (unchanged) | 14.391 (unchanged) | no |
| 1440x900 | 15x15 | 2 x 62.58 (unchanged) | 217.58 (unchanged) | 28.0 (unchanged) | no |
| 1440x900 | 30x30 | 2 x 62.58 (unchanged) | 217.58 (unchanged) | 16.25 (unchanged) | no |

\*\* 600x844 is not one of the card's four viewports; it was measured because
it is the width `TestSolverPhone_MirroredGutterSticks` asserts at, and it is
compact (`max-width: 600px` matches at exactly 600). Its *control-row* count
drops from 3 to 2 only as an artefact of how rows are counted here (distinct
control tops): the zoom readout was already 44 px tall and so sat 3 px above
the 36 px controls beside it; at 44 px they line up. The toolbar is two rows
either way, 8 px taller.

\* `GRIDS_SINGLE_DIGIT_COLS["15x15"]`, added to the measurement because
neither `GRIDS["15x15"]` nor `BIG` can show the trade: both are bound by
CARD-196's column-numeral floor (14.4 px for a two-digit column clue), which
the stage's top does not enter, so **their cell does not move by a single
pixel**. Only a fit-bound board pays, and it pays 0.359 px. The two 1440 px
figures are `DESKTOP_CELL`'s own pins (28.0 / 16.25), unchanged.

Control dimensions at 390x844 (every control the toolbar draws, admin page):

| control | before | after |
|---|---|---|
| Brush (`Brush: Black`) | 44 x 36 | **44 x 44** |
| Region | 49 x 36 | **49 x 44** |
| Undo / Redo / Reset / Hint / Check | 44 x 36 | **44 x 44** |
| Probe | 44 x 36 | **44 x 44** |
| `-` / `+` (Zoom out / Zoom in) | 44 x 38.78 | **44 x 44** |
| zoom readout | 44 x 44 | 44 x 44 (its own rule, since CARD-401) |

At 844x390 all eleven measured 44 x 44 before and after. At 1280x720 and
1440x900 nothing moved (controls 38.78 px tall, labelled widths 60.94-151).

**Two figures in the card's body are corrected by the measurement, and the
correction is the card's own prediction, not a defect in it:**

1. "nine toolbar controls measure 44 x 36 px" — the count is right for the
   public player (admin adds Check, a tenth), but **two of the nine were 44 x
   38.78, not 44 x 36**: `-` and `+` carry a text glyph whose line box is
   taller than `--control-h`. Still under the floor, so the fix is the same.
2. "about +32 px of chrome" (four rows x 8 px) — the toolbar actually grew
   **+24.0 px** (183.8 -> 207.8). Three of the four control rows gained the
   full 8 px; the fourth row's growth is absorbed by the counters line that
   sits above the probe row, which was already taller than its contents. The
   board gave up 24 px of stage cap, not 32.

**Nothing in `player/` changed**, so the public player gets this by
`assemble.py`'s byte-identical `COPIED_FROM_ADMIN` copy of `admin.css`; no
public-mode duplicate cell was added (owner test budget 2026-11-07).

### Verification

Narrowed impact set only (never the full suite / `make test-gate` — the
advisory lock at `meta/kanban/.full-suite.lock` has no writer):

```
tests/test_puzzle_solver_phone.py tests/test_puzzle_solver_brush_menu.py
tests/test_puzzle_solver_hint.py tests/test_puzzle_solver_zoom.py
tests/test_puzzle_solver_probe.py tests/test_puzzle_solver_maybe.py
tests/test_puzzle_solver_percent.py tests/test_puzzle_solver_page.py
tests/test_player_shared_ui_site.py tests/test_public_player_pages.py
```

**414 collected, 414 passed, 0 skipped, 0 failed** — the collected count was
summed independently (`--collect-only -q`) and matched the 414 progress
characters of the run, all of them dots: read as output, not as a tally, per
the standing warning that this suite can skip silently. The first run of the
set, before the two re-pins above, was the same 414 with exactly those two
reds. `tests/test_kanban_review_record.py` run alone after the card edit: 68
passed.

Not run here, deliberately: the full suite and `make test-gate` (one full run
per card at the merge gate; the advisory lock at
`meta/kanban/.full-suite.lock` has no writer). The one blast-radius question
the narrowed set cannot answer — whether a test outside it pins compact
player geometry in absolute pixels — was checked by reading rather than by
running: `grep` for `--player-stage-top`/`stageTop` across `tests/` hits only
`test_puzzle_solver_phone.py` and `test_puzzle_solver_zoom.py` (both in the
set), and the two other player files that use a 390 px viewport
(`test_puzzle_solver_clues.py`, `test_puzzle_solver_mirror.py`) compare a
page against itself (`_GEOMETRY` before/after) or against the cell, which
this change does not move on their boards.

**Net change in collected node ids: 0.** `tests/test_puzzle_solver_phone.py`
collects 22 ids before and after; the diff adds no `def test_`, no
`parametrize` entry and no class. One existing parametrised cell gained a
dimension and two existing cells had a measurement re-pinned, as the card's
budget line asked.

### [Orchestrator] gates, cycle 1

- **[Build gate]** Impact set (`tests/test_puzzle_solver_{phone,brush_menu,hint,zoom,probe,maybe,percent,page}.py`, `tests/test_player_shared_ui_site.py`, `tests/test_public_player_pages.py`), run in the worktree with the main checkout's interpreter: **414 passed, 0 failed, 0 skipped**, 433 s. Independently equal to the implementer's own 414 — not inherited from it. Figure derived with `-o addopts=`: this project's `addopts = "-q"` plus a second `-q` makes `-qq`, which suppresses pytest's summary line entirely, so the first run reported nothing but exit 0 and a silent skip would have been indistinguishable from a pass.
- **[Scope]** Diff touches exactly the declared `Touches:` set and nothing else (`src/nonogram/admin/static/admin.css`, `tests/test_puzzle_solver_phone.py`). No `## Guardrails` section exists, so no structural guardrail applies; growth beyond the card's slice: 0 components. `tokens.css` was read and not edited, as the card required. Nothing under `player/`.
- **[Review 1/3]** forge:review dispatched on the two-file diff, `min_score: 8`, `mutation_check: true`. Its first question is the one real risk in this diff: whether the two re-pinned `TestSolverPhone_MirroredGutterSticks` figures are a legitimate measurement move or a weakened gate.

- [Review 1/3] Score: 3.5 — forge:review, `overall_verdict: fail` — 2 critical, 2 important, 3 minor, 2 out-of-scope. Report `meta/review/20261111T130233Z-CARD-423-cycle1.yml`, parser verdict `accepted` (`security: n/a`, reasoned). **[Review sync]** 1 report → `meta/review/`.
- **[Severity gate]** FAIL — critical findings stand, so the card cannot close regardless of score. Both verified by the orchestrator independently before any fix was dispatched: `tests/test_player_base_css.py::test_the_project_stylesheet_matches_the_real_bootstrap[390]` and `tests/test_puzzle_solver_clues.py::TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` at `[390x844]` and `[600x844]` — **3 failed, 5 passed** on this head.
- **[Build gate] CORRECTION, and the mistake is the orchestrator's.** The 414-passed figure above was measured over 10 modules I selected from the board's standing note on player-card impact scope. **The repo ships the derivation: `scripts/impact_set.py src/nonogram/admin/static/admin.css tests/test_puzzle_solver_phone.py` selects 141 modules, and it selects both of the modules that red.** I wrote the 10-module set into the implementation brief and into the review brief, so the implementer's blast-radius check inherited my narrowing and its grep for `--player-stage-top`/`stageTop` could not have found either pin (neither module names those tokens). The standing note is for choosing BETWEEN suites; it is not a substitute for running the script. Lesson for the next player card: derive the set, never recall it.
- **[Frozen registry]** `tests/test_player_base_css.py`'s `FROZEN[390]` is the third instance of the known class on this board — a frozen census that reds at a gate because a card legitimately moved the thing it records. `PROVENANCE["recorded"]` already names CARD-401/403/404/409/411/412/413/280. It is NOT in `tests/wave_close_marker.py`'s registry, so it runs at every merge gate.

### [Fix round] CARD-423 review cycle 1 — the consequences the floor did not carry

Five of the cycle's six findings. `tests/test_player_base_css.py` (F-001)
was excluded by the orchestrator and stays red: re-recording `FROZEN[390]`
needs the owner's uncommitted `bootstrap.min.css`, which is not on this
machine. Nothing below touches that module, its `FROZEN` table or its
`PROVENANCE` dict — but what it measures DID move again in this round: the
`.player-region` and `.player-toolbar .btn` rules are unchanged, so its 52
differences are the same 52 the review recorded, and its re-record owes
nothing to this round beyond the CSS comment text (which the census does
not read).

* **F-002 (critical) — the re-pinned figures' second home.**
  `tests/test_puzzle_solver_clues.py`
  `TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted::ROOMS`:
  the `390x844` and `600x844` rows re-pinned, with the dated history
  comment appended in the form CARD-406 / CARD-409 / CARD-411 used (each of
  which moved both homes together), naming the CARD-423 mechanism and the
  other home. **Measured here, not carried** (`-o addopts= -rEfs`, the two
  cells red before the edit with these actuals in the assertion message):
  * `390x844`: overflow `[346, 159] -> [346, 183]`, port `[358, 424] ->
    [358, 400]`;
  * `600x844`: overflow `[136, 87] -> [136, 95]`, port `[568, 496] ->
    [568, 488]`.
  Every CLAIM stood: `keeping` is `[False, True]` / `[True, True]` as
  before, the band is `[272.2, 135.4]` at both viewports, and the
  re-derivation from `STICK_MAX_SHARE` passes. So this was a re-pin and not
  a behaviour change — no `[BLOCKER]`.
  Test: `TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted` —
  **5 passed** (was 2 failed, 3 passed).

* **F-004 (important) — the growth rule, corrected in both prose homes, and
  the card's own account corrected with it.** The comment in `admin.css`'s
  compact block and the re-pin comments in
  `TestSolverPhone_MirroredGutterSticks` said "one 8 px step per control
  row it draws", which its own parenthetical refutes (four rows x 8 = 32,
  not the +24 measured; two x 8 = 16, not +8). All three now state the
  measured mechanism: **a control row pays the 8 px step only where its
  tallest control was still under 44 px, and a row holding the zoom readout
  pays nothing** — the readout has carried its own `min-height: 44px` in
  that block since CARD-401.
  **This refutes the explanation in the Implementation notes above**
  ("the fourth row's growth is absorbed by the counters line that sits
  above the probe row"). Derived, not reasoned: the toolbar's controls were
  read off the live admin solve page at both viewports with the new
  `min-height` on and then overridden back to `--control-h`, grouped by
  their rounded `top`:
  * `390x844`, floor off — rows at 36, 36, **44** (the readout; its two
    steppers 38.78 px, 3 px below it), 36; toolbar **183.8**.
    Floor on — 44, 44, 44, 44; toolbar **207.8**. So +8, +8, **+0**, +8 =
    **+24**: the zoom row, not the counters line, is the row that did not
    pay.
  * `600x844`, floor off — one row of ten controls whose tallest is the
    **44 px** readout, plus the probe row at 36; toolbar **111.8**. Floor
    on — both 44; toolbar **119.8**. So +0, +8 = **+8**, and the 3 -> 2
    control-row count is the readout's 3 px offset disappearing, as the
    Implementation notes said.
  Secondary, same finding: the comment and the
  `TestSolverPhone_CompactToolbar` docstring called the before state
  "44 x 36 px" for a group that includes **Region at 49 x 36** (it takes
  its width from its content; the other eight are reached by the compact
  block's `min-width: 44px` rules). Both now state the FLOOR and the two
  measured heights (36, and 38.78 for the steppers) instead of a box.
  Tests: `TestSolverPhone_CompactToolbar` + `MirroredGutterSticks` —
  **6 passed**.

* **F-005 (minor) — three prose homes that named `--control-h` as the
  phone's source of the height.** Corrected to name the compact block's
  44 px floor as the phone's source, `--control-h` as the labelled
  toolbar's: `.player-region`'s comment in `admin.css`,
  `tests/test_admin_design_tokens.py::test_the_region_toggles_pressed_look_comes_from_tokens`'s
  docstring, and
  `tests/test_puzzle_solver_brush_menu.py::TestSolverBrushMenu_RegionIsItsOwnToggle::test_it_keeps_a_tap_target_and_the_toolbars_button_pattern_on_a_phone`'s
  docstring (whose "no toolbar button reaches 44" was false at its own
  390 x 844 viewport). **No assertion changed** — the brush-menu test's
  `>= 24` and `round(height) == round(undo height)` both still hold on the
  44 px floor, which is why only prose moved. Tests:
  `tests/test_admin_design_tokens.py` — **14 passed**; the brush-menu cell
  — **1 passed**.

* **F-006 (minor) — the non-compact arm of `test_icons_only_when_compact`.**
  `assert box["label"] > 1` is now guarded by `if box["name"] in
  _LABELLED`, the way the compact arm guards its icon assertion, because
  the five controls in `_UNLABELLED` carry no `.player-btn-label` at any
  width and their `0` is the right reading. Defended in one sentence in the
  class docstring. The arm stays dead on both compact cells, so this buys
  the next card that adds a desktop cell a red that means something.
  Test: `TestSolverPhone_CompactToolbar` — **3 passed**.

* **F-007 (minor) — an unnamed toolbar button named `''`.**
  `_CONTROL_BOXES`'s name falls back to `button.textContent` before `''`,
  so the reset dialog's "Reset board" / "Keep marks" (`.btn` inside
  `.player-toolbar`, no label span, no `aria-label`) would name themselves
  in the set assertion's failure instead of adding a row called `''`.
  `textContent` and not `innerText`: Chromium applies `text-transform` to
  `innerText`. The measured states draw none of them, so the two cells read
  the same names as before — **3 passed**.

* **F-003 — not closed here.** Its prose half is the paragraph above (the
  derived selection, `scripts/impact_set.py` on the two changed files, is
  what finds `test_player_base_css.py` and `test_puzzle_solver_clues.py`;
  the hand-listed 10-module set could not). Its other half — running that
  selection rather than a hand-list — is the round's gate and belongs to
  the orchestrator, so the finding is left `open` rather than marked fixed
  by a round that did not run it.

**Verification (this round's budget, not the gate).** `py_compile` on the
four edited test modules, then exactly the named tests:
`-o addopts= -rEfs` over
`TestSolverClues_TheRoomForAStuckBandIsMeasuredNotPredicted`,
`TestSolverPhone_CompactToolbar`, `TestSolverPhone_MirroredGutterSticks`,
`tests/test_admin_design_tokens.py` and the brush-menu cell:
**27 passed, 0 failed, 0 skipped, 1 warning in 14.22s** (the SQLAlchemy
`MovedIn20Warning`, pre-existing). The full suite and `make test-gate` were
NOT run here — one gate per round, the orchestrator's.

**Net change in collected node ids: 0.** `git diff -U0` over `tests/` and
`src/` adds no `def test_`, no `parametrize` entry and no class; the four
edited modules collect **171** ids, all of them pre-existing.

- **[Fix 1] declarations** — F-002, F-004, F-005, F-006, F-007 `fixed` in `8affd504`; F-001 excluded by the orchestrator, F-003 left `open` because its other half is this round's gate and the round does not run its own gate. Net collected node ids: 0 (four edited modules collect 171, all pre-existing).
- **[Fix 1] the round corrected the card, not only the code.** The Implementation notes' explanation of the +24 px — "the fourth row's growth is absorbed by the counters line above the probe row" — is **refuted by measurement**: the row that pays nothing is the **zoom row**, whose readout has carried its own `min-height: 44px` since CARD-401. Derived by reading the controls off the live page grouped by rounded `top`, with the floor on and overridden back off. The rule is now stated as measured in all three prose homes: a control row pays the 8 px step only where its tallest control was still under 44 px.
- **[Review sync]** 1 report → `meta/review/` (F-002/F-004/F-005/F-006/F-007 `status: fixed`; F-001, F-003 open).
- **[Impact gate] DERIVED, not recalled.** `scripts/impact_set.py --gate --against main` → **SELECTION, 141 test files, 7546 tests of 10630 collected (71.0%)** at this gate, plus a second run for 2 lifted `wave_close_only` files (rule S, subject edge: `test_book_export_interior_cover.py` and `test_browser_fixture_scope.py`), and 7 marked tests owed at the wave close. This is the round's one `[Build gate]` and it runs once, on the final state — after F-001. The advisory lock at `meta/kanban/.full-suite.lock` has no writer, so the orchestrator writes it before a run this size.

### [Orchestrator] the round's one gate, and the AC/EC/G verdicts

- **[Build gate]** The DERIVED selection (`scripts/impact_set.py --gate --against main`: 141 files, 7546 of 10630 tests), run once on the final state `a23cd7b6`, lock held through the module's own `acquire()`:
  - run 1 (`-m "not wave_close_only"`): **1 failed, 7508 passed, 30 skipped, 12 deselected, 1 xfailed**, 27:13.
  - run 2 (the 2 lifted marked files): **6 passed, 176 deselected**, 1:16.
  - The one red is **pre-existing on main**, verified there rather than assumed: `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses::test_an_export_that_retains_a_fraction_of_the_book_fails` fails identically at `9fd6576e` — `on this host the bound first bites at 16.2 retained pages of 198; this test's 20 is no longer the modest regression it is written to be`. A host-calibration guard that has drifted; CARD-421's gate recorded the same red. Nothing in this card reaches PDF memory.
  - **30 skips is the expected UNARMED count** (29 bare-`DATABASE_URL` + 1 `setrlimit` the kernel refuses here), so nothing was newly skipped — the figure that matters after a layout change.
- **[Lock]** Two corrections the board should keep: CARD-370 landed `acquire()`/`release()` in `tests/full_suite_lock.py`, so the lock must be taken through the API — a hand-written file with no `worktree:` line is refused by its own author's run, which killed the first launch of this gate at `pytest_configure`. And `release()` takes **no** argument (it releases the module's held lock), so `release(path)` raises and leaves the file behind.
- **[AC/EC check]** Fresh evidence, run by the orchestrator rather than read off the implementer's notes — 127 passed in one run:
  - **AC-1 ✓ demonstrated** — `TestSolverPhone_CompactToolbar::test_icons_only_when_compact` green at both compact viewports over the widened `_CONTROL_BOXES` (every `.player-toolbar button, [role="button"]`, both dimensions ≥ 44). **Plant re-run by the orchestrator:** with `.player-toolbar .btn { min-height: 44px; }` stripped, `[390-844-True]` **FAILED** and `[844-390-True]` **passed** in the same run — the card's one control, and the independence of the two media blocks, demonstrated rather than asserted. `git checkout` restored the file; `git status` clean after.
  - **AC-2 ✓ demonstrated** — `TestSolverPhone_BoardFitsThePhoneWidth`, `TestSolverPhone_FallsBackToMirrorWhenDoublingWouldNotFit` and `TestSolverPhone_BoardFitsWithoutScrollingWhenColumnsStaySingleDigit` green unchanged (they read the measured stage top), plus `TestSolverPhone_MirroredGutterSticks` green on the re-pinned scrollport. Cell recorded in the measurement table: 14.391 px before and after on both column-floor-bound boards; 16.359 → 16.0 on the fit-bound one.
  - **AC-3 ✓ demonstrated** — `TestSolverPhone_DesktopSizingUnchanged`, the brush-menu slot geometry, percent and maybe cells all green unchanged, and `tests/test_player_base_css.py` green at `[1280]` as well as the re-recorded `[390]`.
  - **EC / G** — the card states no `## Engineering constraints` and no `## Guardrails`, so neither class applies; no criterion was inferred from `## What to implement`.
- **[Dependency gate]** Not applicable and not configured: no `done.dependency_gate` key, no `make audit` target, and the diff adds no dependency (one CSS declaration, comment prose, test-helper changes).

- [Review 2/3] Score: 7.5 — forge:review, `overall_verdict: fail` — 0 critical, **2 important**, 2 minor, 2 out-of-scope. Report `meta/review/20261111T141346Z-CARD-423-cycle2.yml`. **[Severity gate]** FAIL: important findings block regardless of score. The mutation check cycle 1 deferred under the cost ladder RAN this cycle and the result is worth keeping: `min-height: 44px → 43px` kills `test_icons_only_when_compact[390-844-True]` alone, `→ 45px` kills `MirroredGutterSticks::test_a_390px_phone_keeps_its_cells_rather_than_its_row_clues` — **the value is pinned from both sides**, not merely asserted.
- **[Review cycle 2 note]** both findings are one mechanism measured in one page state and then written as a universal law — the third refinement of the same sentence in this card.** The card predicted +32 px uniformly; the implementation measured +24 and blamed the counters line; fix round 1 refuted that and blamed the zoom readout; cycle 2 now shows the readout clause holds only while `solver.js` gives it `[role="button"]`, which it does only when a Fit exists — on a 10x10 that fits at 100% the readout is 38.53 x 24.8 with no role and its row pays **5.22 px**. The true rule is `44 px − the row's tallest`. Separately, `7b7c7b96` replaced a TRUE bullet ("at least 44 px wide and `--control-h` tall") with a FALSE universal ("Every button is at least 44 x 44 px"): the brush menu's four `.player-tool-item` buttons are **142 x 36 px** inside `.player-toolbar` at all three compact viewports, and the diff's own `_CONTROL_BOXES` returns them when the menu is open. `violates: ADR-0039/R1` — a claim whose control cannot fail must be narrowed or deleted.
- **[Review cycle 2 note]** what cycle 2 verified rather than accepted:** the `FROZEN[390]` re-record absorbs nothing unrelated — recomputed against main, the changed fields are **only** `y` (9), `height` (20) and `min-height` (23), no colour, padding, `x` or `width`, no row added or removed, `FROZEN[1280]` untouched; `PROVENANCE`'s platform matches `sw_vers` and its browser matches the launched Chromium's own version string.

- **[Build gate, final head `c10f29e7`] SCOPED DELIBERATELY, and the scoping is the orchestrator's judgement rather than the script's.** The delta from the gated head `a23cd7b6` is comment-and-docstring only — checked mechanically, not asserted: the CSS diff `a23cd7b6..HEAD` carries **zero** lines containing `{`, `}` or `;`. Re-running the derived 141-file / 7546-test selection for a diff with no declaration in it would cost 27 minutes to re-prove an unchanged stylesheet, so instead the nine modules that can actually see CSS text or computed styles ran on the final head: `test_player_base_css.py`, `test_player_shared_ui_site.py`, `test_public_player_pages.py`, `test_puzzle_solver_phone.py`, `test_puzzle_solver_clues.py`, `test_admin_design_tokens.py`, `test_puzzle_solver_brush_menu.py`, `test_puzzle_solver_zoom.py`, `test_player_public_mode.py` — **372 passed, 0 failed, 0 skipped**, 9:22. The full derived selection's authority stands at `a23cd7b6`; what is unproven at `c10f29e7` is only whatever a comment could break outside those nine, which is nothing a comment can reach.

- [Review 3/3] Score: 8.5 — forge:review, `overall_verdict: pass`, `task_contract_verdict: pass`, `system_contract_verdict: pass` (57 rules assembled, 6 ✓, 51 ⚠ `no_eligible_fact`, 0 ✗). **0 critical, 0 important**, 3 minor, 2 out-of-scope. Report `meta/review/20261111T143734Z-CARD-423-cycle3.yml`. **[Severity gate]** PASS — nothing gating, and the score clears `min_score: 8`. **[Review sync]** 3 reports → `meta/review/`.
- **[Review cycle 3 note]** two claims were upgraded from "measured" to "derivable", which is the stronger thing.** The step formula `44 px − the row's tallest` checks out against `FROZEN[390]` row by row and against the steppers' own box arithmetic (6.4×2 padding + 1×2 border + 24 px line box = 38.78, so "their glyph's line box" is the right mechanism, not a guess). And the menu options' `142 x 36 px` is derivable from CSS rather than carried: `.player-tool-menu`'s `min-width: 10rem` − 2×8 px padding − 2×1 px border = 142, viewport-independent, with `.player-tool-item`'s `min-height: var(--control-h)` = 36 and `FROZEN[390]`'s four `button player-tool-item` rows carrying `36px` on both sides of the diff. The +21.2 px public-surface figure was re-derived the same way: 8 + 5.22 + 8 = 21.22 against a measured 21.20.
- **[Review cycle 3 note]** the selector was re-argued on the markup and upheld.** Broadening `.player-toolbar .btn` to `button` would raise four controls D1's ruling did not name and grow the popover by 32 px. The current selector also reaches the reset dialog's two `.btn` children (36 → 44), a benefit recorded in `FROZEN[390]`.
- **[Review cycle 3 note]** cycle 3 refuted one of fix round 3's own judgements** — round 3's DECLARATIONS re-read `.player-region`'s comment ("as tall as every other toolbar button at either size") and recorded it "still correct". It is false in compact, by the vocabulary the compact block itself establishes: the four `.player-tool-item` buttons are 36 px. Fifth instance of this card's defect family, and the first one found inside a declaration that claimed to have checked it.

### [Fix round 2] CARD-423 — F-001: `FROZEN[390]` re-recorded, and certified against the real Bootstrap

The cycle's last open finding but F-003 (whose other half is the
orchestrator's gate). One file changed: `tests/test_player_base_css.py` —
**27 rows of `FROZEN[390]`** (the 52 field-level differences the review
measured), plus `PROVENANCE` and the comment above it. `admin.css`,
`player/shared-ui-base.css` and the round-1 fixes are untouched.

**The real file was available.** The owner's point: the Bootstrap the table
was recorded from is what the admin panel loads, and
`src/nonogram/admin/templates/base.html` pins
`https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css`.
Fetched from that pinned URL: 232914 bytes, sha256
`7f1d37f0…8496c2a` — **byte-identical to `PROVENANCE["sha256"]`**, verified
with `shasum -a 256` before anything relied on it. It was referenced only
through `NONOGRAM_REAL_BOOTSTRAP` and never copied into the repository.

**Why the documented recipe cannot re-record a stale table.** In
`test_the_project_stylesheet_matches_the_real_bootstrap`, the sha-matched
branch asserts `differences(FROZEN[width], live) == []` *before* the
`NONOGRAM_PRINT_FROZEN` print, so with a stale table the run dies on that
assert and prints nothing. The recipe only works from an already-correct
table. Two steps instead:

1. **Patch from the measured actuals** (no env var, so `expected` is
   `FROZEN` and `actual` is this tree's live measurement). The assertion
   message truncates to `problems[:5]`, so the full set came from a
   throwaway `frozen_literal(width, actual)` dump, guarded by a temporary
   env-var branch that was removed again before anything was committed —
   the committed file differs from its merge-base copy in the 27 `FROZEN`
   rows, `PROVENANCE` and that comment, and in nothing else (`diff`
   against a pristine copy: 27 lines out, 27 lines in, plus the prose).
   Only rows that actually differed were rewritten; `FROZEN[1280]` was not
   touched at all.
2. **Certify against the real file.** With `NONOGRAM_REAL_BOOTSTRAP` set
   and the sha matching, the assert of step 1's obstacle becomes the proof:
   it asserts the patched `FROZEN[390]` equals the real Bootstrap's live
   measurement. **Both width cells passed** (`2 passed` in 17.22 s, and
   `3 passed` in 26.08 s over the whole module on the final committed
   state). **Negative control, so the gate is not vacuous:** the same
   real-file run against the *pre-fix* table dies on
   `AssertionError: FROZEN no longer equals the real file's measurement` —
   stale table reds, patched table passes.

**`[1280]` did not move**, as expected: the compact block does not match at
1280 px, and `test_..._matches_the_real_bootstrap[1280]` passed before the
patch (the pre-fix run was `1 failed, 1 passed`) and after it.

**The plant still reds when it should.**
`test_a_changed_stylesheet_reds_the_fidelity_check` passed — i.e. dropping
the `[hidden]` rule and widening `.btn` padding still both produce
differences. It compares against `FROZEN[1280]`, which this round did not
change, so its subject is unchanged.

**Browser and platform.** The run reports **Chromium 151.0.7922.34**, the
same build `PROVENANCE` recorded, so this is a same-browser re-record and
the frozen text widths keep their meaning. `platform` did move by one patch
version (macOS 26.7.1 -> 26.7.2) and is recorded as measured; no rectangle
difference was attributable to it, since every residual difference against
the real file is zero.

**DECLARATIONS F-001 —** `PROVENANCE["recorded"]` re-dated to 2026-11-11
with CARD-423 appended to the card list in the existing form (what it
moved: the compact controls 36 -> 44 px tall and the control block and
board they reflow); `platform` corrected; `sha256` re-verified and
**unchanged**. The comment above `PROVENANCE` called the real file "the
owner's spike copy of Bootstrap 5.3, never committed" — a declaration this
round refutes: it now names the pinned `bootstrap@5.3.0` URL in `base.html`
and says a re-record needs no local spike copy. The module docstring's
caveat about font fallbacks and the `NONOGRAM_PRINT_FROZEN` recipe in the
failure message were re-read and are still correct as written, so they were
left alone (the recipe's precondition — a table that is already correct —
is now stated in these notes rather than in the module).

**Verification (this round's budget, not the gate).** `py_compile` on the
one edited module, then exactly the named tests: `tests/test_player_base_css.py`
with `-o addopts= -rEfs -v` — **3 passed, 0 failed, 0 skipped in 17.73 s**
(both width cells and the plant), and **3 passed in 26.08 s** with
`NONOGRAM_REAL_BOOTSTRAP` set. The full suite, `make test-gate` and any
impact-scoped substitute were NOT run here — one gate per round, the
orchestrator's.

**Net change in collected node ids: 0** — `tests/test_player_base_css.py`
collects the same **3** ids (`[390]`, `[1280]`, the plant); the diff adds no
`def test_`, no `parametrize` entry and no class.

### [Fix round 3] CARD-423 review cycle 2 — the floor's prose says what was measured and no more

All four findings are prose. **No CSS declaration and no test assertion
changed** — `git diff HEAD` over `src/` and `tests/` is comments and one
docstring only, and the 44 px floor, `_CONTROLS`' membership and every
re-pinned figure are byte-identical.

* **F-201 (important) — the floor's rule statement was universal and false.**
  Both sentences 7b7c7b96 wrote are narrowed to the eleven controls AC-1
  enumerates, with the brush menu named as the stated exception:
  * `admin.css`'s compact-block bullet now opens on "the eleven controls
    CARD-423's AC-1 enumerates ... are at least 44 x 44 px: the `.btn` floor
    here plus the readout's own rule below", says that is the set
    `_CONTROLS` names and the only set the floor is held to, and then states
    the exception — the brush menu's four options (`.player-tool-item`,
    `role=menuitemradio`) are `<button>`s and no `.btn`, keep
    `min-height: var(--control-h)` and measure **142 x 36 px** at 390x844,
    600x844 and 844x390, reached by neither this floor nor CARD-402's block;
    raising them is an owner call (D1 named nine controls) on a follow-up
    card. The same paragraph's landscape sentence now reads "set both on the
    same eleven ... no landscape `.btn` under 44 px (the menu's four options
    are 36 px tall there too)".
  * `TestSolverPhone_CompactToolbar`'s docstring: "for every control the
    toolbar draws, at every compact viewport" becomes "for the eleven
    controls AC-1 enumerates — the ones `_CONTROLS` names and this cell
    measures — at every compact viewport", with the same menu exception in
    one clause; its "Landscape's own block (CARD-402) already pinned both
    dimensions" gains "on those same eleven".
  * Re-derived here rather than carried: `puzzle_solve.html` draws the four
    `<button class="player-tool-item">` inside `.player-tool-menu` inside
    `.player-tools` inside `.player-toolbar`, and the only height rule that
    reaches them is `.player-tool-item { min-height: var(--control-h) }` —
    36 px. `tests/test_player_base_css.py`'s `FROZEN[390]` rows
    "05..08 button player-tool-item" carry `36px` in the `min-height` field
    on both sides of this card's diff, which is the same fact in a second,
    independent record.
* **F-202 (important) — "a row holding the zoom readout pays nothing" held
  only while the readout is a control.** The general law is restated in both
  general homes as **`44 px minus the row's tallest control`** (8 px where
  that control was 36 px, **5.22 px** for a row of bare 38.78 px steppers),
  and the readout clause is conditioned on the readout BEING one: its rule is
  `.player-zoom-readout[role="button"]`, and `solver.js`'s `syncZoom` adds
  that role only while `zoomFloor < ZOOM_MIN` — a board that fits at 100%
  leaves a role-less span. Edited: `admin.css`'s mechanism paragraph (which
  now also names the state its +24 / +8 figures were measured in — the admin
  solve page's BIG board, where the readout IS a control — and scopes "the
  BOARD gives that up, not the page" to that page), and
  `TestSolverPhone_MirroredGutterSticks`'s 600x844 re-pin comment. The
  per-row figures in both re-pin comments and the two ROOMS comments in
  `tests/test_puzzle_solver_clues.py` are accurate about their own rows and
  were left exactly as they stand. The round-1 note in `## Worktree notes`
  that "refutes" the Implementation notes' counters-line explanation is
  corrected in place: the refutation holds **for the BIG board that round
  measured, and there only** — on a board that fits at 100% the readout has
  no role, its row pays the steppers' 5.22 px and the counters-line gap IS
  the absorber (cycle 2's 390x844 10x10 measurement, quoted there).
* **F-203 (minor) — `_CONTROLS` is exact for one state.** One comment block
  beside `_CONTROLS` says so: it is a STATE PIN, exact for a freshly opened
  board with no popover open that does NOT fit at 100%, and names the five
  states that change the NAME set without touching the floor (menu open,
  reset confirmation, open probe, solved, and a board that fits at 100% —
  where "Zoom readout" is absent). No assertion touched; none of those
  states is reachable from this cell's own driving.
* **F-204 (minor) — the one public-surface figure is now in the record.** A
  paragraph in the measurement table above, before the control-dimensions
  table: the CARD-386 shared-UI preview's page grows **583.69 -> 604.89
  (+21.2 px)** at 390 px (`FROZEN[390]`'s `html` row, with
  `02 div puzzle-player-controls` 103.8 -> 125), while its board row
  `25 div puzzle-player` keeps its 362.08 px height and only moves down
  (183.28 -> 204.48) — so **there the page grows and the board gives up
  nothing**, and AC-2's "the board absorbs it, the page does not" is the
  admin solve page's answer alone. Both halves of the difference are derived
  from the table itself: the preview's content is 604.89 px in an 844 px
  viewport, so the stage's
  `max-height: max(calc(100svh - var(--player-above)), 5rem)` cap is nowhere
  near binding; and +21.2 rather than +24 is F-202's mechanism — three
  control rows, not four, with a role-less readout, so 8 + 5.22 + 8 = 21.2
  (its two stepper rows 38.78 -> 44, the probe row below shifted +13.2).

**DECLARATIONS F-201 —** the mechanism did not change; what changed is its
two STATEMENTS, which are the declarations. Both narrowed, and the one other
place in this card that said "every control the toolbar draws" (the
control-dimensions table's caption in `## Worktree notes`) narrowed with
them. Re-read and confirmed still correct: `_CONTROL_BOXES`' own comment
(it describes the query, not a floor), the `.player-region` comment and the
two docstrings F-005 corrected, and CARD-401's AC-6 wording quoted in "Why
this card exists" (a historical quote, true as written).
**DECLARATIONS F-202 —** the step formula and the readout's conditionality
are declarations in three places; two were general and are fixed
(`admin.css`, the 600x844 re-pin), the third (the round-1 notes) is
corrected in place. The per-row records in `tests/test_puzzle_solver_clues.py`
(both ROOMS rows) and the 390x844 re-pin comment were re-derived against the
measured rows and are correct as written, so they stand.
**DECLARATIONS F-203 —** none (local branch): a comment naming the state an
existing assertion is exact for; no behaviour, bound or lifecycle changed.
**DECLARATIONS F-204 —** AC-2's scope is now stated where it is read: the
`## Worktree notes` measurement table carries the public surface's own figure
and says AC-2's claim is the admin page's. `COPIED_FROM_ADMIN`'s
byte-identity check is unchanged and still the thing that carries the copy.

**Verification (this round's budget, not the gate).** `py_compile` on
`tests/test_puzzle_solver_phone.py`; a comment/brace balance check on
`admin.css` (103 `/*` : 103 `*/`, 456 `{` : 456 `}` with comments stripped,
and the floor declaration still present verbatim); then exactly the tests
whose files this round edited, `-o addopts= -rEfs -v`:
`TestSolverPhone_CompactToolbar` + `TestSolverPhone_MirroredGutterSticks` —
**6 passed, 0 failed, 0 skipped in 9.78 s** (one pre-existing SQLAlchemy
`MovedIn20Warning`). The full suite, `make test-gate` and any impact-scoped
substitute were NOT run here — one gate per round, the orchestrator's.

**Net change in collected node ids: 0.** No test was added:
`tests/test_puzzle_solver_phone.py` collects **22** ids
(`--collect-only -q`), the same 22 the Implementation notes recorded, and
`git diff -U0 HEAD` over `tests/` and `src/` adds no `def test_`, no
`parametrize` entry and no class (grep count 0).

### [Fix round 4] CARD-423 review cycle 3 — the last three sentences that overreach

All three findings are prose, in two files. **No CSS declaration, no assertion
and no test node id changed**: `git diff HEAD` over `src/` and `tests/` carries
**zero lines with `{` or `}`** (measured), and the three `;` it does carry are
prose semicolons inside a CSS comment.

* **F-301 (minor) — the compact block's before-state counts were the PUBLIC
  player's.** Two edits in `admin.css`'s compact-block CARD-423 paragraph:
  Check is now marked **ADMIN ONLY** in the enumeration (naming `solver.js`'s
  `PUBLIC_ABSENT`, which removes `[data-player-action="check"]` in public
  mode), and the three counts are now stated for the admin solve page this
  file styles, with the public player's as the one-lower clause.
  **Re-derived here from `puzzle_solve.html`'s toolbar markup and the compact
  block's own `min-width` rules, not carried from the review:**
  * **under the floor in height: TEN** of the eleven — every control but the
    readout, which has carried `min-height: 44px` via
    `.player-zoom-readout[role="button"]` since CARD-401.
  * **at 36 px: EIGHT** — brush trigger, Region, Undo, Redo, Reset, Hint,
    Check, Probe (the height falling through to `.player-toolbar .btn`'s
    `min-height: var(--control-h)`); the two zoom steppers were 38.78 px.
  * **min-width-reached: NINE** — `.player-tool-trigger` (1); the five
    `.btn` DIRECT children of `.player-history`, i.e. Undo, Redo, Reset, Hint
    and **Check** (the `.player-confirm` dialog sits between them and is no
    `.btn`, so `.player-history > .btn` reaches five, not four); the two
    `.player-zoom .btn` steppers; and `.player-probe > .btn`'s Probe (its
    three siblings Keep / Wrong guess / Show grid are `hidden` in the measured
    state). Region is the one NOT reached — 49 px from its content.
  * Public player: **nine / seven / eight**, Check being absent. So the old
    nine/seven/eight was the public set's, in the file that styles the admin
    page; the paragraph also no longer contradicts itself (eleven enumerated
    minus the already-44 px readout is ten).
* **F-302 (minor) — two universal quantifications.**
  * (a) The floor bullet's "are at least 44 x 44 px" now carries the
    condition its own paragraph states ~25 lines later: the readout's rule is
    keyed on `[role="button"]`, so the readout is in the set only while there
    is a Fit to go to, and a board that fits at 100% leaves it a role-less
    24.8 px span with the set being the other ten. The bullet and the
    mechanism paragraph no longer disagree.
  * (b) `.player-region`'s comment said the toggle is "as tall as every other
    toolbar button at either size". **Re-derived against the markup rather
    than re-read:** `puzzle_solve.html` draws four
    `<button class="player-tool-item">` inside `.player-tool-menu` inside
    `.player-tools` inside `.player-toolbar`, and `.player-tool-item`'s own
    rule sets `min-height: var(--control-h)` — 36 px — with nothing in the
    compact block reaching it, while Region takes the compact block's 44 px
    `.btn` floor. So the sentence was FALSE in compact. It now names
    `.player-toolbar .btn` (with Undo as the instance the brush-menu test
    actually asserts against) and states the menu options as the explicit
    non-member. Fix round 3's DECLARATIONS block had re-read this home and
    recorded it "still correct"; cycle 3 refuted that, and this round's own
    declarations below were derived from the markup for exactly that reason.
* **F-303 (minor) — `_CONTROLS`' STATE PIN read as a closed list.** The
  comment beside `_CONTROLS` in `tests/test_puzzle_solver_phone.py` now opens
  the list with "e.g." AND names the sixth state: a brush other than Black
  picked RENAMES the trigger, because `solver.js`'s `syncTrigger` writes
  `aria-label` = `` `Brush: ${label}` `` and `_UNLABELLED` pins
  `"Brush: Black"` — so what that entry pins is the brush, not the control.
  The pin itself is untouched and still sound: its stated precondition, a
  freshly opened board, excludes the state.

**DECLARATIONS F-301 —** the three counts are declarations about a past state,
and both their value and their SUBJECT (which page) are now stated; each was
re-derived from `puzzle_solve.html` and the block's `min-width` rules above,
not copied from the finding. The card's control-dimensions table in these
notes already records Check at 44 x 36, which is the same fact in a second
record. Nothing forward-looking moved: the floor, the rule it states, and the
measured +24 / +8 figures are untouched.
**DECLARATIONS F-302 —** both sentences ARE declarations, and both are
narrowed to what the selectors do. Re-derived against the markup this round,
not re-read for plausibility (the failure mode of round 3's declaration):
`.player-tool-item`'s only height rule is `min-height: var(--control-h)`
(36 px), `.player-zoom-readout`'s 44 px rule carries the `[role="button"]`
key, and `.player-toolbar .btn`'s compact floor is the 44 px one. The
mechanism paragraph's own conditional wording (fix round 3, F-202) and
`_CONTROLS`' comment were the two homes that already said this; the bullet
and `.player-region` are now the third and fourth.
**DECLARATIONS F-303 —** none (local branch): a comment is widened from a
closed list to an open one plus the missing member; no behaviour, bound,
assertion or lifecycle changed.

**Verification (this round's budget, not the gate).** Mechanical on the CSS:
comment delimiters **103 `/*` : 103 `*/`**, braces with comments stripped
**456 `{` : 456 `}`** (both unchanged from fix round 3), the floor declaration
`.player-toolbar .btn { min-height: 44px; }` still present **verbatim**, and
**zero lines carrying `{` or `}`** in this round's whole `src/`+`tests/` diff.
`py_compile` on `tests/test_puzzle_solver_phone.py`, then exactly the test of
the one test file touched, `-o addopts= -rEfs -v`:
`TestSolverPhone_CompactToolbar` — **3 passed, 0 failed, 0 skipped in 6.16 s**
(one pre-existing SQLAlchemy `MovedIn20Warning`). The full suite,
`make test-gate` and any impact-scoped substitute were NOT run here — one gate
per round, the orchestrator's.

**Net change in collected node ids: 0.** `tests/test_puzzle_solver_phone.py`
collects **22** ids (`--collect-only -o addopts= -q`), the same 22 every prior
round recorded; the diff adds no `def test_`, no `parametrize` entry and no
class.

- **[Done]** Merged `40f12185` on the gates, per the owner's standing rule (merge on gates, not on an eyeball). Estimate was **1c**; actual **3 cycles**, ratio 3.000 — the worst on this board and worth the retrospective's attention: the CSS was one declaration, as the estimate assumed, but the card was never about the declaration. Three of the four fix rounds and all eleven findings were about *consequences and prose* — two homes of a re-pinned measurement, a frozen census, and five instances of one sentence stated more broadly than it was measured. An estimate that reads the production diff will underestimate any card whose subject is a recorded figure.
- **[Follow-up]** CARD-424 drafted `ready`: the brush menu's four `.player-tool-item` options are 142 x 36 px, the one tap target this floor does not reach (not a regression — they were 36 px before). Raised as out-of-scope by all three review cycles and carded only at the close. It carries **no default**: D1 ruled on nine named controls, and nobody has asked the owner about these four.
