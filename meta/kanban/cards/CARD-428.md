# CARD-428: Landscape: the zoom control wraps onto two rows (− and 100% on one, + alone below)

**Status:** review
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.5d)
<!-- The strip is a 2-column grid and the zoom group has three members; the fix is a span or a reflow of that one group. The cost is re-pinning CARD-402's landscape geometry, which several cells measure. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/428-landscape-zoom-row
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-428
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 5. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/static/admin.css, tests/test_puzzle_solver_zoom.py
<!-- Derived 2026-11-11 from `admin.css`'s CARD-402 block (`@media (max-height: 500px) and (orientation: landscape)`), whose `.player-toolbar` is `grid-template-columns: repeat(2, 44px)` with `.player-zoom` as `display: contents` — so its three children flow into the 2-wide grid. `tests/test_puzzle_solver_phone.py` holds CARD-402's own landscape cells; name it in the brief. Conflict edge: CARD-424 and CARD-426 also edit `admin.css` — serialize. -->
**Review score:** 9.0 (cycle 2)
**Started:** 2026-11-11T18:20:00Z
**Closed:** 2026-11-11T19:10:00Z
**Actual:** 2 review cycles + 1 fix round + 1 orchestrator prose edit (wall clock excluded, owner ruling)
**Merge commit:** c902fae0
**Blocked by:** —

## Why this card exists

Measured on production in landscape, at both 844x390 and 874x402:

```
rows = 2   tops = [240, 292]
  −      x=40  y=240  44x44
  100%   x=92  y=240  44x44
  +      x=40  y=292  44x44
```

The owner's words: *"zoom button gets awkwardly in 2 lines (+, number and -)"*. The mechanism is CARD-402's side strip: `.player-toolbar` is `grid-template-columns: repeat(2, 44px)` and `.player-zoom` is `display: contents`, so its **three** children flow into a **two**-column grid and wrap 2 + 1. The readout ends up beside the minus and the plus is orphaned on the next row — so the two steppers, which are a pair, are the two things not next to each other.

This is cosmetic in the sense that nothing is unreachable, and not cosmetic in the sense that `−` and `+` reading as a pair is what makes a stepper a stepper.

## Decision owed before implementation (owner)

**D1:** which of the three shapes? (a) `−` and `+` side by side on one row with the readout spanning both columns below (the readout is also the Fit control, so it is the one that can take a full-width row); (b) all three in one row by letting the zoom group break out of the 2-column grid; (c) the readout dropped to a tooltip in landscape, leaving a clean pair. **Default if unanswered:** (a) — it keeps every target 44 px, keeps the pair adjacent, and spans the member that is already full-width-friendly elsewhere in the strip (the brush slot and the counters already span both columns).

## What to implement

1. The chosen shape, in CARD-402's own landscape block, keyed on the same selectors it already uses. Every control stays at least 44 x 44 px (CARD-423's floor, which this block already sets explicitly).
2. Re-measure the landscape strip and the board beside it at 844x390 and 874x402, and re-pin whatever CARD-402's cells measure in `tests/test_puzzle_solver_phone.py` — in the dated form those lines already carry.

## Acceptance criteria

- **AC-1** (the steppers are a pair, on one row): at 844x390 and 874x402, `−` and `+` share a row (equal rounded `top`) and are horizontally adjacent, and the zoom group occupies no more rows than the chosen shape allows. (test: changed cell in `tests/test_puzzle_solver_zoom.py`; plant: revert the rule and the cell reds.)
- **AC-2** (nothing shrank): every control in the landscape strip is still at least 44 x 44 px. (test: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar`, unchanged — it already asserts this at 844x390.)
- **AC-3** (the board kept its room): the stage's box beside the strip at 844x390 is unchanged, or changed by exactly the measured amount, recorded in Worktree notes. (test: CARD-402's existing landscape geometry cells, re-pinned if they move.)
- **AC-4** (portrait untouched): at 390x844 the zoom group's geometry is unchanged. (test: the existing portrait cells.)

**Net test count: 0 added.**

## Worktree notes

- **[Env]** forge version unresolved (no `.claude-plugin/plugin.json` at the executing path; no `meta/.skills.yml` in this project, so no `forge.min_version` comparison and no `models:` block — agents inherit the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`. That command is **exit 127 in a worktree** (none has a `.venv`): use `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`, or `make test-gate PY=<main>/.venv/bin/python`. Fork point `8ecb8758`, interactive mode.
- **[Impact scope]** Derive with `scripts/impact_set.py --gate --against main`, never from a standing note: CARD-423 shipped two criticals past a hand-picked 10-module set the script would have caught.
- **[Concurrency, LIVE]** **CARD-426 is `in_progress` in `PythonProject4-card-426` and is editing `src/nonogram/admin/static/solver.js` and `src/nonogram/admin/static/admin.css` right now.** The two cards own different regions — 426 the brush menu's rules and `openMenu`/`closeMenu`, this card the CARD-402 landscape block — and different test modules (`test_puzzle_solver_brush_menu.py` vs `test_puzzle_solver_zoom.py`). Whichever merges second rebases. Keep every edit inside the CARD-402 block and additive; anything outside it is a `SCOPE+` line.
- **[Owner ruling]** D1 was **not** answered; the card's recorded default applies — shape (a), `−` and `+` side by side with the readout spanning both columns below. The owner said only "start 428 too", which is not a ruling on the shape, so the default is taken as the card wrote it and the author does not invent a different one.

### Implementation round, 2026-11-11 (wave 79)

**The shape is D1's recorded default**, the owner having answered only "start 428 too":
`−` and `+` side by side on row 1, the readout spanning both columns on row 2. It held —
no measurement refuted it, so there is no `[BLOCKER]` and no switch to (b) or (c).

**The rule** (`admin.css`, inside CARD-402's `@media (max-height: 500px) and (orientation:
landscape)` block, additive, placed directly after the block's own
`.btn, .player-zoom-readout` sizing rule): `.player-zoom` is no longer left to the
`display: contents` grouped rule above it — it is overridden to `display: grid` with
`grid-column: 1 / -1` and `grid-template-columns: repeat(2, 44px)`, i.e. it spans the strip
the way `.player-slot` and `.player-counters` already do and lays its three members out
itself (`grid-area: 1 / 1` for `[data-player-zoom-action="out"]`, `1 / 2` for `…="in"`,
`2 / 1 / 3 / -1` for `.player-zoom-readout`). Nothing was reordered, regrouped or
reformatted: `.player-zoom` stays in the `display: contents` selector list and is
overridden by a later rule of equal specificity. The readout gives up only the fixed
`width: 44px` of the rule above (`width: auto`, so it fills its span) and keeps that rule's
`min-width: 44px` and `height: 44px` — so the Fit control it becomes while
`zoomFloor < ZOOM_MIN` cannot fall under CARD-423's floor. It stays centred by
`.player-zoom-readout`'s own `text-align: center`.

**`solver.js` was not touched** (CARD-426 owns it this wave). No `SCOPE+`.

#### ACs

- **AC-1: test `TestSolverZoom_TapTargetsAreAtLeast24px::test_zoom_buttons_and_300_percent_cells_are_at_least_24px_and_the_steppers_pair` red→green.**
  Red first, for the right reason and not a selector or fixture error: at 844x390 it read
  `out {x:312, y:292}`, `readout {x:260, y:344}`, `in {x:312, y:344}` and failed on
  `round(minus["y"]) == round(plus["y"])` (`292 == 344`) — the two steppers on different
  rows, which is the owner's finding. That red run IS the plant: it is the page with the
  new rule absent, so reverting the rule reds the same assertion.
- **AC-2: `tests/test_puzzle_solver_phone.py::TestSolverPhone_CompactToolbar::test_icons_only_when_compact`
  green, unchanged** (both cells, `[390-844-True]` and `[844-390-True]`): every one of the
  eleven controls still ≥ 44 x 44 px. The changed cell asserts the floor on the zoom
  group's three boxes again at both landscape viewports.
- **AC-3: the board kept its room — unchanged, nothing to re-pin.** The board's and the
  stage's boxes and the cell size are identical before and after at every viewport
  measured (figures below). The strip takes no size of its own here (`height: 0;
  min-height: 100%`), so one more row inside it is absorbed by its own scroll and never
  reaches the board. CARD-402's landscape geometry cell —
  `tests/test_player_public_mode.py::TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board`,
  which is the cell that measures the strip's place, its width, its clip and the board's
  box at 844x390 / 852x393 / 874x402 — passes **unchanged** (1 passed).
- **AC-4: portrait untouched.** At 390x844 every reading is byte-identical before and
  after: strip `[16, 204.1, 358, 207.8]`, board `[16, 427.9, 358.3, 309.8]`, stage
  `[16, 427.9, 358, 325.8]`, cell `130.5`, and the zoom group's three boxes
  `out [16, 308.1, 44, 44]`, `readout [64, 317.7, 38.5, 24.8]`, `in [106.5, 308.1, 44, 44]`
  (and, on the BIG board where the readout is the Fit control,
  `readout [64, 308.1, 44, 44]`). The portrait cells in both files are green.

#### Measured geometry (`[left, top, width, height]`, a tenth of a px)

Admin solve page (`_open`, 15x15 seed 19518 and `test_puzzle_solver_phone.BIG`):

| viewport | zoom group before | zoom group after |
| --- | --- | --- |
| 390x844 | out (16, 308.1) · readout (64, 317.7) · in (106.5, 308.1) | identical |
| 844x390 | out (312, 292) · readout (260, 344) · in (312, 344) | out (260, 344) · in (312, 344) · readout (260, 396) 96x44 |
| 874x402 | out (312, 292) · readout (260, 344) · in (312, 344) | out (260, 344) · in (312, 344) · readout (260, 396) 96x44 |

Public player (the phone's page, `SWEEP_GRID`): at 844x390, 852x393, 874x402 and 568x320
the group read out (8, 213.2) · readout (60, 213.2) · in (8, 265.2) before, and
out (8, 213.2) · in (60, 213.2) · readout (8, 265.2) 96x44 after — the same shape at all
four.

Unchanged at every viewport, both pages: the strip's own box, the board's box, the stage's
box and the cell size. At 844x390 public: board `[116, 8, 369.8, 301.6]`, stage
`[116, 8, 720, 317.6]`, cell `89.8`, strip `[8, 57.2, 96, 316.8]` — before and after.

**The one cost, stated plainly:** one more strip row, because `+` no longer shares its row
with the control after it. Public strip `scrollHeight` 317 → 331 against a 317 px
scrollport at 844x390 (so the strip now scrolls itself there by 14 px; it already did at
568x320), and the lowest control's bottom 309.2 → 361.2 against a clip of 374. On the admin
page, whose landscape strip already overflowed (386 against 297), 386 → 438. No assertion
anywhere reads those: the public cell's claim is `lowest <= clip`, which holds at all three
of its viewports, and at 568x320 its claim is that the strip scrolls ITSELF and its last
button can be scrolled into the window, which it still can.

#### Findings for the orchestrator

1. **The brief's premise about where CARD-402's landscape geometry lives does not hold.**
   `tests/test_puzzle_solver_phone.py` holds CARD-401/CARD-423's *compact toolbar* cell
   (`TestSolverPhone_CompactToolbar`), which measures control boxes at 844x390 but no strip
   or board geometry. CARD-402's landscape geometry — strip place and width, clip, board box
   idle/probing/at hint rung 2/confirming/solved — is
   `tests/test_player_public_mode.py::TestPublicMode_LandscapeToolStrip`. I ran that one
   node id as well (green, unchanged); it is one node, not the full suite or a gate.
   Attribute by test, not by file.
2. **Nothing needed re-pinning.** No landscape figure in any test moved, so no dated
   trailing comment was added anywhere and no claim changed.

#### Verification

`-o addopts= -rEfs`, the narrowed set only:
`tests/test_puzzle_solver_zoom.py tests/test_puzzle_solver_phone.py` → **61 passed**, 0
failed, 0 skipped (126.75 s), plus the one CARD-402 node id above → 1 passed. No full
suite, no `make test-gate`, no full-suite lock taken.

**Net test count: 0 added.** 61 node ids collected in the two files before and after; the
diff is exactly one `def test_` renamed (`…_at_least_24px` →
`…_at_least_24px_and_the_steppers_pair`, so the name still says what the cell asserts), no
new `parametrize`, the landscape arm being a loop over the two viewports inside the one
node. The class name `TestSolverZoom_TapTargetsAreAtLeast24px` is referenced by CARD-195,
CARD-211 and `tests/test_puzzle_solver_brush_menu.py` and was left alone.

Commit: `e97764b0` on `card/428-landscape-zoom-row` (explicit pathspecs:
`src/nonogram/admin/static/admin.css`, `tests/test_puzzle_solver_zoom.py`; no
`meta/**` staged).

### [Orchestrator] notes on the implementation

- **[Card defect, mine]** This card's `Touches:` comment and the brief both said CARD-402's landscape geometry is held by `tests/test_puzzle_solver_phone.py`. **It is not.** That module holds CARD-401/423's compact-toolbar control boxes only; CARD-402's strip place/width/clip and the board's box are `tests/test_player_public_mode.py::TestPublicMode_LandscapeToolStrip::test_the_tools_stand_in_a_strip_left_of_the_board`. The implementer found it, ran that one node id (1 passed, unchanged) and flagged doing so as its one deviation from the narrowed set — correctly: a change to the strip's row count that never met the test holding the strip's geometry would have been a gap, and it is the same class of miss that cost CARD-423 two criticals. The premise was mine; the correction is recorded here rather than left in a transcript.
- **[Build gate] DEFERRED, with the reason.** The derived selection for an `admin.css` change is 141 files / 7546 tests and takes the full-suite lock. **CARD-425 and CARD-426 have agents working in their own worktrees right now, and the lock's guard refuses every pytest from a worktree while a FOREIGN worktree holds it** — so running this gate now would not merely contend, it would break their verification runs at `pytest_configure`. The gate runs once both are idle, before this card merges, and the card does not close without it.
- **[Scope]** Diff is exactly the declared `Touches:` (`admin.css`, `tests/test_puzzle_solver_zoom.py`), additive inside CARD-402's block, nothing reordered, `solver.js` untouched, no `SCOPE+`. Verified by reading the diff, not from the report.
- **[Cost, recorded]** One more strip row: the public strip's `scrollHeight` goes 317 → 331 against a 317 px scrollport at 844x390 (it already scrolled at 568x320), and the admin strip, which already overflowed (386 vs 297), goes 386 → 438. CARD-402 designed the strip to scroll itself (`height: 0; min-height: 100%`), so the board's box is unchanged — measured, not assumed. No assertion reads those figures. Worth the owner's eye on a real phone: a strip that scrolls is by design, a strip that scrolls *more* is a judgement.

- [Review 1/3] Score: 7.5 — forge:review, `overall_verdict: fail`, `task_contract_verdict: fail`, `system_contract_verdict: pass` (52 rules, 6 ✓, 46 ⚠ `no_eligible_fact`, 0 ✗). **1 critical**, 0 important, 3 minor, 3 out-of-scope. Report `meta/review/20261111T164641Z-CARD-428-cycle1.yml`. **[Severity gate]** FAIL.
- **[Review 1/3] the critical, and the briefing failure is mine.** The renamed node (`…_at_least_24px` → `…_at_least_24px_and_the_steppers_pair`) sits inside `FAMILY_PREFIX = "tests/test_puzzle_solver"`, which `tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured` polices against CARD-217's committed artefact (`meta/profiling/suite-durations-20261015.txt`, which still holds the old id). Reproduced by the reviewer: *"tests added: [...] are collected in the browser family but recorded nowhere" — 1 failed in 1.80s*. It is NOT deferred to the wave close (`wave_close_marker.py` lists that class under `controls`), and `scripts/impact_set.py` selects that file for this diff — so it reds this card's own gate. **This is the exact class my standing note on frozen registries names, browser-family census included, and I briefed the impact-set lesson while leaving this one out.**
- **[Review 1/3] the fix is the house rule, not the cheaper option.** The board's standing **G-T** — carried verbatim by CARD-401, CARD-405, CARD-409 and CARD-413 — reads "No test is deleted, **renamed**, skipped or weakened to fit." So the rename was against convention and the remedy is to keep the original method name and let the widened class docstring carry the added subject, rather than to record the rename in `RENAMED_SINCE_BEFORE` and add a third path to `Touches:`. AC-1 names only the file; only the Worktree notes quoted the new name.
- **[Review 1/3] what it verified rather than accepted.** Its **own** mutation check ran (nothing deferred): reverting the four new rules is killed by the pair's shared-row assertion — the implementer's claimed plant, independently confirmed — and narrowing the readout's span is killed too. AC-2's floor on the readout holds in **both** `syncZoom` states and the reviewer showed it is structural rather than lucky: the landscape rule keys on `.player-zoom-readout` with no `[role]` predicate, `width: auto` drops only the fixed width, and the new rule is (0,4,0) against the old (0,3,0) so it wins regardless of order. `puzzle_edit.html` has `.player-stage`, not `.player-stage-wrap`, so the edit page is outside the blast radius.
- **[Review 1/3] a census worth carrying forward:** it built the full set of tests that render a landscape viewport (h ≤ 500, w > h) — **8 functions in 5 files** — and found two outside the implementer's run set, in `test_puzzle_solver_probe.py` (admin.css's #2 co-change peer, 10 of its last 25 commits) and `test_puzzle_solver_hint.py`. Both green. That census belongs in the next landscape card's brief; it is in the report's `notes.landscape_census`.
- **[Review 1/3] one surviving mutant, measured rather than assumed.** Dropping `grid-column: 1 / -1` leaves every covering cell green; the reviewer rendered the mutant and found it near-equivalent (the group's box becomes 44x96 and `in` overflows into exactly where the strip's second column already is, because the inner template duplicates the strip's own `repeat(2, 44px)` + `var(--space-2)`; `elementFromPoint` at the plus still returns the plus). Nothing is owed under the test budget; recorded so the next reader knows the hole is known and bounded.
- **[Out of scope, for the owner]** The one cost lands on the owner's primary landscape viewport: the public strip's `scrollHeight` goes 317 → 331 against a 316.8 px scrollport at **844x390**, so it now scrolls there where it did not before. The controls stay inside the clip (`TestPublicMode_LandscapeToolStrip`'s `lowest <= clip` green at all three viewports), so what falls below the fold is the counters' tail, reachable by scrolling the strip. If the owner dislikes a scrolling strip at that size, D1's shape (b) costs no row — their call, not a finding.

### [Fix round] review cycle 1, 2026-11-11 (wave 79)

Two findings taken: **F-001 (critical)** and **F-002 (minor)**. F-003 (the landscape Tab
order) and F-004 (the surviving `grid-column: 1 / -1` mutant) were left open on the
reviewer's own reasoning — F-003 is D1's shape, an owner call this card reserves, and the
reviewer *rendered* F-004's mutant and measured it near-equivalent, so nothing is owed
under the owner's test budget.

**F-001 — the rename is undone; the node id is the one CARD-217 recorded.** The
implementation round had renamed
`TestSolverZoom_TapTargetsAreAtLeast24px::test_zoom_buttons_and_300_percent_cells_are_at_least_24px`
to `…_at_least_24px_and_the_steppers_pair`. That node id is inside
`tests/test_browser_fixture_scope.py`'s `FAMILY_PREFIX` (`tests/test_puzzle_solver`), whose
frozen census — CARD-217's committed `meta/profiling/suite-durations-20261015.txt` — still
holds the old id, so the renamed one was "recorded nowhere" and reddened a control that is
NOT deferred to the wave close (`tests/wave_close_marker.py` lists
`TestBrowserFixtures_NoTestAddedOrRemoved::*` under `controls`) and IS selected for this
diff by `scripts/impact_set.py`. The remedy is the board's standing **G-T** — *"no test is
deleted, renamed, skipped or weakened to fit"* — not the registry: no entry was added to
`RENAMED_SINCE_BEFORE` or `ADDED_SINCE_BEFORE` and
`meta/profiling/suite-durations-20261015.txt` was not touched (`git diff main` over those
two paths is 0 lines). **Every assertion the round added stays** — the steppers-pair claim
is unchanged; it simply no longer appears in the method's name. The added subject is
carried in the class docstring (which now also states WHY the name stayed, naming G-T and
the control) and in the cell's own new docstring.

The control node, re-run on the fixed tree:

```
$ pytest -o addopts= -rEfs \
    "tests/test_browser_fixture_scope.py::TestBrowserFixtures_NoTestAddedOrRemoved::test_the_family_collects_exactly_what_card_217_measured"
tests/test_browser_fixture_scope.py .                                    [100%]
============================== 1 passed in 1.31s ===============================
```

**Net collected-node-id change: 0, and the node-id SET is identical to `main`'s** — which is
what the frozen census actually checks, so the stronger claim is the one that matters. Both
collections taken with `--collect-only -q` and sorted: `tests/test_puzzle_solver_zoom.py`
collects **39** node ids on this head and **39** on `main`, and `diff` over the two sorted
lists is empty. `tests/test_puzzle_solver_phone.py` is not in the diff at all (`git diff
main --stat` is two files: `admin.css`, `tests/test_puzzle_solver_zoom.py`), and the pair of
files runs 61 node ids as before. The only `def test_` change left against `main` is the
signature being wrapped over three lines — same name.

**F-002 — the source-order dependence is gone, and it was measured inert, not reasoned
inert.** `.player-zoom` was dropped from the landscape block's `display: contents` grouped
rule, so the group is now named by exactly ONE `display` declaration in that block instead
of two at identical (0,3,0) specificity where only document order decided. Nothing else in
the block relied on the group being `display: contents`: its three children are placed
explicitly by this card's own rule, and the group's base `.player-zoom` declarations
(`display: flex`, `gap: var(--space-1)`) are overridden by the landscape rule's `display:
grid` / `gap: var(--space-2)` at higher specificity regardless of order. Both the grouped
rule and this card's comment were updated to say so.

Measured before and after the removal on the admin solve page (15x15, seed 19518), reading
the zoom group's box and `getComputedStyle(group).display`/`gap`, each child's box, and the
strip / stage / stage-wrap / board boxes, the cell width and the strip's
`scrollHeight`/`clientHeight`, at a tenth of a px:

| viewport | before | after |
| --- | --- | --- |
| 844x390 (landscape) | group `[260, 344, 96, 96]` grid/8px · out `[260, 344, 44, 44]` · in `[312, 344, 44, 44]` · readout `[260, 396, 96, 44]` · strip `[260, 136, 96, 296.6]` scroll 438/297 · stage `[368, 80, 436, 294]` · board `[368, 80, 346.4, 293.7]` · cell 14.4 | **identical** |
| 874x402 (landscape) | group `[260, 344, 96, 96]` grid/8px · out `[260, 344, 44, 44]` · in `[312, 344, 44, 44]` · readout `[260, 396, 96, 44]` · strip `[260, 136, 96, 296.6]` scroll 438/297 · stage `[368, 80, 466, 306]` · board `[368, 80, 346.4, 293.7]` · cell 14.4 | **identical** |
| 390x844 (portrait) | group `[16, 308.1, 134.5, 44]` flex/4px · out `[16, 308.1, 44, 44]` · readout `[64, 317.7, 38.5, 24.8]` · in `[106.5, 308.1, 44, 44]` · strip `[16, 204.1, 358, 207.8]` scroll 223/208 · stage `[16, 427.9, 358, 325.8]` · board `[16, 427.9, 358.3, 309.8]` · cell 15.2 | **identical** |

The two JSON captures are byte-identical (`diff` empty), portrait included — so landscape
geometry did not move and portrait did not move. The probe that produced them was a
throwaway module, run and then deleted; it is not in the commit and added no node id.

#### Verification (the fix round's budget, not the gate)

`-o addopts= -rEfs`, nothing wider, no full suite, no `make test-gate`, no full-suite lock
taken (two foreign worktrees are active):

- the control node above → **1 passed** (1.31 s);
- `tests/test_puzzle_solver_zoom.py tests/test_puzzle_solver_phone.py` → **61 passed**, 0
  failed, 0 skipped (124.11 s) — AC-1's cell and AC-2/AC-4's cells on the fixed tree;
- `python -m py_compile tests/test_puzzle_solver_zoom.py` → clean.

`DECLARATIONS F-001 — the class docstring and the cell's new docstring carry the widened
subject and the reason the name stayed; the card's two quotations of the renamed node id
(AC-1's line and the net-test-count paragraph) were corrected, so the record no longer
describes a node that does not exist. DECLARATIONS F-002 — the landscape block's grouped
`display: contents` rule and this card's own comment both now state that the group is named
in one place; no bound, lifecycle or error classification changed.`

- [Review 2/3] Score: 9.0 — forge:review, all three verdicts `pass` (52 rules: 7 ✓, 45 ⚠, 0 ✗). **0 critical, 0 important**, 2 minor, 3 out-of-scope. Report `meta/review/20261111T170636Z-CARD-428-cycle2.yml`. **[Severity gate]** PASS, and `min_score: 8` met.
- **[Review 2/3] it settled a specificity question the orchestrator had left loose.** I had worried the fix won on source order; it does not. `.player-toolbar:has(~ .player-stage-wrap) .player-zoom` is **(0,3,0)** — `:has()` takes its most specific argument — against the base `.player-zoom`'s **(0,1,0)**, so the landscape rule wins on specificity, and the base rule is earlier in the file in any case. The F-002 removal was then confirmed inert by rendering the real stylesheet and its inverse mutant (M4, putting `.player-zoom` back in the `contents` list): **identical at all three viewports**. It also checked four ways that nothing else depended on the group being `contents` — no test or script pins that selector text, the block's sizing rule is a descendant selector that matches either way, `order: 1` still sorts the counters after the group, `:nth-child` matching is DOM-based so `contents` never affected it, and `solver.js` touches only the `--player-zoom` property.
- **[Review 2/3] the node-id SET claim verified independently**: 39 ids on this head and 39 on a clean main checkout (`-p no:cacheprovider`, `git status` clean first), both sorted, `diff` empty, cross-checked by an `ast` walk showing identical name sets; `git diff main..HEAD` over `tests/test_browser_fixture_scope.py` and `meta/profiling/suite-durations-20261015.txt` is 0 lines. It also read every assertion the rename-undo could have dropped and found all present — no regression dressed as a correction.
- **[Review 2/3] minor #2 corrects a sentence of the fix round's that a future card would act on.** The class docstring says a renamed node id in the family "is a node id recorded nowhere, and reds that control". That is **wrong about the mechanism**: `RENAMED_SINCE_BEFORE` exists for exactly that case — its own docstring calls a rename "a MOVE, `old id -> (card, new id, reason)`", `_recorded_node_ids` applies the table to CARD-217's artefact *before* anything is compared, and the CARD-247 entries are live precedent. A *recorded* rename does not red the control. The right reason to keep the name is **G-T**, which the sentence beside it already gives. This matters because that docstring is now the one place a future card touching this family will read to learn whether it may rename a cell — and my own brief contributed to the error by telling the author that a rename reds the census, when what forbids it is the house rule.
- **[Review 2/3] minor #1 is the CARD-261 drift class inside this diff's own blast radius:** the CARD-402 block's header comment still says the strip's groups "become its grid cells (display: contents)" and lists "the brush slot, the counters and the probe note" as the spanning members. After the fix round neither half holds for the zoom group — the grouped rule names only `.player-history` and `.player-probe`, and this card's rule makes the group a third spanning member. The fix round updated the grouped rule's comment and its own, but not the summary a reader meets first.
- **[Review 2/3] not reached, stated:** the card's absolute px figures were not re-derived on the real page — the reviewer's render was a bare document with no `tokens.css`, so `--space-2` resolves to `normal` there and absolute offsets are not comparable. It verified the shape and the cascade directly, and the absolute figures only indirectly through the AC cell passing.

- **[Build gate]** Worktree card file cleaned before rebasing (not left for git to autostash, which conflicted on CARD-425), then rebased onto main so the gate measured what merges. Derived selection: 141 files / 7546 tests, plus the two lifted `wave_close_only` files (`test_book_export_interior_cover.py`, `test_browser_fixture_scope.py` — rule S pulls in the census guard whose break started this card's critical). Result: run 1 **7508 passed, 30 skipped, 12 deselected, 1 xfailed, 1 failed** in 26:18; run 2 **6 passed**. The 30 skips are the expected unarmed count (29 bare-`DATABASE_URL` + 1 `setrlimit`), and the one red is the pre-existing `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses` host-calibration drift — identical figures to CARD-423's gate on the same selection. Lock held through `acquire()` and released.
- **[Done]** Merged `c902fae0` on the gates. Estimate 1c against 2 cycles, ratio 2.000 — and the overrun is not the CSS, which was four declarations. It is that a test rename (made for a good reason: the name saying what the cell asserts) collided with a frozen census and a house rule, and that the correcting docstring then had to be corrected itself. Third card today whose cost was carried by the record rather than the code.
