# CARD-075: Image-mode nudge adds one cell per attempt from where the solver's witnesses disagree

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false  _(revised 2026-09-15 from CARD-096 — see Revision)_
**Skill:** python-pro
**TDD:** red -> green -> mutation check (5 mutants, 1 survived and drove a new test)
**Branch:** card/075-mask-driven-nudge
**Worktree:** ../PythonProject4-CARD-075
**Source:** meta/architecture/handoff.md#increment-9 (FR-013 amendment, split from CARD-074 by decompose)
**Idea:** —
**Wave:** 1
**Depends on:** CARD-073
**Touches:** src/nonogram/sourcing/image.py (next_nudge_cell, nudge; nudge_cells retired), src/nonogram/orchestrator.py (the nudge call site only — it keeps the attempt's chosen cells, as it keeps the repair lineage), tests/test_nudge.py, tests/property/test_nudge_mask.py (new), meta/architecture/requirements.yml (FR-013 AC-115/AC-116, EC-014 — amended by this card), docs/GENERATION_ALGORITHM.md (§8.4)
**Review score:** —
**Started:** 2026-09-17
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Revision — 2026-09-15, from CARD-096's measurement (owner: "revise CARD-075")

This card was written on 2026-09-12, before anyone had measured why image mode
abandons. CARD-096 measured it, and two of the choices below were wrong in a
way the data makes plain. **What changed, and why:**

1. **The source of cells is the witness-disagreement set, with the undecided
   mask as the fallback** — not the mask first. On the original conversion of
   every abandoned picture, the two witnesses disagreed on **4 cells in 27 of
   34** (one 2x2 block that can be drawn either way), while the undecided mask
   covered a median **35% of the grid** and up to 100%. Ranking inside a mask
   that size is guessing again; the disagreement set is the ambiguity itself.
2. **Each attempt adds one cell chosen from the previous attempt's verdict** —
   not the best n cells chosen once from the original conversion. Flipping one
   cell of an ambiguous block usually exposes the *next* ambiguity somewhere the
   original disagreement set never contained. Measured on the 36 dither failures,
   cap 5, both variants nested and exactly n cells from the picture:
   **static 9 of 36, adaptive 19 of 36** (CARD-096, *Follow-up measurement*).
   Today's nudge rescued 0 of those.

**What did not change:** the policy half. The cap is 5 (ADR-0002); POL-003
reports at the cap with the same message; every nudged grid is judged by the one
`judge_candidate` path; image mode never draws from the rng and never repairs.
And the user-facing promise FR-013's cumulative property exists for still
holds in full: **attempt n differs from the uploaded picture's conversion in
exactly n cells, and contains every cell attempt n−1 flipped** — no edit is ever
undone. What changes is only *which* cell each attempt adds.

**It cannot break a picture that works today.** The nudge runs only when the
conversion is not unique, so every puzzle made at the first solve is untouched.

**Sequencing with CARD-079** is unchanged — this card first. CARD-096 measured
the two together at 32 of 36, with no regression on the 89 conversions dither
makes today; CARD-079's AC-127 is taken after this lands.

**The owner question below** ("fewer than n cells in the mask") is superseded:
attempts no longer draw n cells from one fixed set. Its successor is AC-116's
fallback rule.

## Why

Today's nudge ranks cells by a 2x2 "switching block" heuristic
(`sourcing/image.py` `nudge_cells`) — a guess at where the ambiguity is
(CARD-016's recorded risk). CARD-073 makes the ambiguity locatable: the
solver reports the cells line logic left undecided and where the two
witnesses disagree. FR-013's 2026-09-12 amendment (mechanism half only)
has the nudge choose from that mask, nearest the ink boundary first. The
policy half is untouched: POL-002 bounded and automatic, POL-003 reports at
the cap, cap of 5 (ADR-0002), and the cumulative property "attempt n flips
the n best cells of the ORIGINAL conversion".

Split from CARD-074 by decompose: different module (`sourcing/image.py` vs
the orchestrator's recovery loop), different policy (POL-002 vs POL-006),
different test file, and a separate owner question (below). The handoff
lists it under Increment 9; it shares no code with the repair step beyond
the one call site in `orchestrator.py`.

**Sequencing.** After CARD-073 (needs the mask on the aggregate). Parallel
with CARD-074 is possible; the two share `orchestrator.py` only at the
nudge call site (conflict-graph matter). CARD-079's AC-127 nudge counts
are taken after this card lands, so this card precedes CARD-079.

**Owner question (FR-013 _meta.gaps, recorded not invented) — _superseded 2026-09-15, see Revision; kept for the record_:** what does
attempt n do when the mask holds fewer than n cells? EC-014 reads it as
"flip all min(n, |mask|) of them" — implement that reading and record it
in the module docstring; if the owner wants a secondary ranking instead,
that is a follow-up, not this card.

## What to implement

*(Revised 2026-09-15 — see the Revision section.)*

1. `sourcing.image.next_nudge_cell(grid, flipped, witnesses, undecided_mask)`
   returns the one cell attempt n adds, or `None`. `grid` is the grid the
   *previous* attempt judged (the original conversion for attempt 1); `flipped`
   is the set of cells already changed from the original. Candidates are the
   cells where the two witnesses differ, excluding `flipped`; if there are none,
   the undecided mask's cells, excluding `flipped`. Within the candidates, rank
   by Chebyshev distance to the nearest differently-valued neighbour (ink
   boundary) ascending, then (row, column). A pure function: no rng, no count,
   no state (INV-003 — `sourcing.image` counts nothing).
2. `sourcing.image.nudge(original, cells)` returns the original conversion with
   exactly `cells` flipped — the whole of nesting is that the caller passes
   attempt n−1's cells plus one. The 2x2 switching-block ranking
   (`nudge_cells`, `_switch_counts`, `_boundary_counts`) is retired.
3. The orchestrator's nudge call site keeps the chosen cells across attempts
   in its closure, as `attempt_candidate` keeps the repair lineage: each
   attempt reads the witnesses and mask `judge_candidate` stored for the
   *previous* candidate, asks `next_nudge_cell`, appends it, and judges
   `nudge(original, cells)`. When `next_nudge_cell` returns `None` the attempt
   has nothing to add and returns `None` — the counter still advances, so the
   cap and POL-003's report are reached exactly as today. Cap, counter,
   `run_bounded` exhaustion branch and POL-003 wording unchanged.
4. Re-pin `tests/test_nudge.py` to the mask-driven choice: the scripted
   sources gain a mask; real-image pins are re-taken honestly (CARD-070's
   convention: the docstring states the count and where it came from).
   The mechanism-agnostic tests (cap, failure message, CLI reporting —
   AC-034..AC-036, FR-014) must pass unchanged in assertion.
5. Rewrite the docstrings and `docs/GENERATION_ALGORITHM.md` §8.4's
   paragraph on cell choice; keep `meta/ops/check_doc_references.py` passing.
6. Amend FR-013's AC-115/AC-116 and EC-014 in `meta/architecture/requirements.yml`
   to the revised rule (below), with a `_meta` note citing CARD-096.
7. Re-run `PYTHONPATH=src python meta/ops/image_abandonment_sweep.py` and record
   the before/after in Worktree notes.

## Acceptance criteria

- **AC-115** *(revised)* — given a candidate the solver reported MANY for, whose
  witnesses disagree on a set D, when the next nudge attempt is built, then the
  one cell it adds is a member of D not already flipped.
  *test:* `TestNudge_AddsACellWhereTheWitnessesDisagree`
- **AC-116** *(revised)* — given a MANY candidate whose witness-disagreement
  cells are all already flipped (or absent), when the next attempt is built,
  then the added cell comes from that candidate's undecided mask; and given
  neither holds an unflipped cell, then the attempt adds nothing and returns no
  candidate, and the counter still advances. Within either source the cell
  nearest the ink boundary is chosen, then (row, column).
  *test:* `TestNudge_FallsBackToTheMaskThenStops`, `TestNudge_PrefersCellsNearestInkBoundary`
- **AC-117** *(unchanged in substance)* — given attempts 1, 2 and 3 with flipped
  sets S1, S2, S3, when compared to the ORIGINAL conversion, then
  S1 ⊂ S2 ⊂ S3 and S3 differs from the original in exactly 3 cells.
  *test:* `TestNudge_MaskDrivenAttemptsRemainCumulativeFromOriginalConversion`
- **AC-172** *(new — the measured effect)* — the corpus sweep
  (`meta/ops/image_abandonment_sweep.py`, all 25 pictures, sizes 10..30) makes
  **at least 19 more** of the 36 conversions that dithering fails today than it
  did before this card, and **every** conversion made before is still made.
  The second half holds by construction (the nudge runs only on a non-unique
  conversion); the first is CARD-096's adaptive, nested measurement, and a
  result below it is reported rather than shipped. Numbers, not a test: the
  corpus is not in the suite's time budget.
- **AC-034 / AC-035 / AC-036** unchanged and green
  (`TestNudge_AttemptsBoundedRecovery`, `TestNudge_ReportsFailureAtCap`,
  `TestNudge_FailureMessageSuggestsRetry`); FR-014 nudge-count reporting
  tests unchanged.

## Engineering constraints

- **EC-014** *(revised)* — For any uploaded image whose conversion reports MANY
  and any attempt number n in 1..5 that adds a cell, the set of cells attempt n
  flips has exactly one more member than attempt n−1's, contains every cell
  attempt n−1 flipped, and its new cell belongs to the witness-disagreement set
  of attempt n−1's candidate or, when that holds no unflipped cell, to that
  candidate's undecided mask — for every image and every n. The grid attempt n
  judges differs from the ORIGINAL conversion in exactly those cells. The cap of 5 and the
  re-verification of every nudged grid by the real solver (CON-005) are
  unchanged. Seeded corpus of scripted grids + masks, minimum case count
  asserted in the test, no hypothesis.
  *test:* `PropertyTest_Nudge_FlippedCellsSubsetOfUndecidedMaskAndNested`

## Guardrails

- G-1: `MAX_NUDGE_ATTEMPTS` (5), POL-002's `when`, POL-003's report-at-cap
  reaction and its message wording are unchanged (ADR-0002, AC-035/036).
- G-2: Every nudged grid is still judged through the one `judge_candidate`
  path (CON-005, INV-002); image mode never repairs (ADR-0024/R5) and
  never draws from the rng (ADR-0015).
- G-3: No edits under `src/nonogram/solver/`, `difficulty.py`,
  `export/**`, `web/**`, `admin/**`; `orchestrator.py` changes are limited
  to the nudge call site.
- G-4: Do not alter fixtures other than as CARD-070 permits
  (`tests/fixtures/bands.png`); `landscape.png` byte-identical.
- G-5: Do not touch the random-mode recovery loop (CARD-074).
- G-6: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0002 — pixel-nudge cap is 5 (check: TestNudge_ReportsFailureAtCap)
- ADR-0024/R5 — image mode recovers by POL-002 only, never repairs (check:
  review-lens)
- ADR-0015 — image mode stays rng-free (check: review-lens)
- INV-002 / CON-005 — nudged grid accepted only on a fresh solver verdict
  of 1 (check: tests/test_nudge.py)
- INV-003 — one counter home in the orchestrator; `sourcing.image` counts
  nothing (check: tests/test_orchestrator.py)
- ADR-0007 — `sourcing/` imports no capability module; the mask arrives
  as a parameter from the orchestrator (check:
  test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-013 (amended 2026-09-12; AC-115..AC-117), FR-024 (consumer),
  FR-014 (unchanged)
- **EC:** EC-014
- **ADR:** ADR-0002, ADR-0015, ADR-0024 (R5), ADR-0007
- **Domain:** POL-002 (mechanism note), POL-003, EVT-006 (carries the mask)
- **Components:** COMP-003 (sourcing/image), COMP-002 (call site)
- **Trace:** meta/architecture/trace.yml (FR-013 row)

**Checkpoint (from the Increment 9 checkpoint, the nudge half, revised):** the
nudge tests are re-pinned to the disagreement-driven choice and green; every
nudge attempt adds one cell from the previous candidate's disagreement set (mask
fallback); the corpus sweep's before/after is in Worktree notes.
**Collapses:** FR-013's "which cell to flip is a guess" risk (CARD-016);
EC-014.
**Rollback:** revert the branch — `nudge_cells` returns to the 2x2
heuristic; no stored data changes.

## Worktree notes

### Delivered 2026-09-17

**The mechanism.** `sourcing/image.py` gained two functions and lost three.
`next_nudge_cell(grid, flipped, *, witnesses, undecided_mask)` returns the one
cell the next attempt adds, or `None`; `nudge(original, cells)` applies a set of
cells to the original conversion and decides nothing. `nudge_cells`,
`_switch_counts`, `_boundary_counts` and `_NUDGE_SPACING` are gone. Neither new
function is told which attempt it is on, which is INV-003 as an API rather than
as a comment — `test_the_image_module_counts_nothing_itself` pins both
signatures.

`_boundary_distances` computes the ranking key for the whole grid in one pass —
two multi-source BFS over the eight-neighbourhood, which on an open grid is
exactly Chebyshev — rather than scanning outward per candidate. That matters
only for the fallback region, which CARD-096 measured at a median 35% of the
grid and up to 100%.

**The call site** keeps the chosen cells and the last judged grid in the
closure, the same shape as `attempt_candidate`'s repair lineage. An attempt that
finds no cell returns `None` without solving anything: the counter has already
advanced, so the cap and POL-003's report arrive exactly as before.

**Measured — the corpus, `meta/ops/image_abandonment_sweep.py`, 25 pictures x
sizes 10,15,20,25,30.** Before is CARD-096's run on `main`.

| | before | after |
|---|---:|---:|
| engine, conversions made | 89 of 125 | **107 of 125** |
| made at the first solve (no nudge) | 76 | 76 |
| abandoned | 34 | 17 |
| timed out | 2 | 1 |
| admin loss, small / medium / large / auto (of 25) | 3 / 5 / 7 / 7 | **2 / 2 / 3 / 3** |

**18 of the 36 failures rescued, 0 regressions.** The regression half is
by construction — the nudge runs only on a conversion that is not unique — and
the sweep confirms it: the "made at the first solve" column is identical, and a
case-by-case diff of the two runs shows an empty regression set.

**AC-172 asked for at least 19 and this is 18 — reported, per the AC's own
instruction, not quietly shipped.** The missing case is one picture at one size
(`frog1.jpeg` at 30), and the cause is known exactly. CARD-096's experiment
ranked candidates by reading order ("the crudest rule, first differing cell",
its Threats section); AC-116 as written ranks them by distance to the ink
boundary first. Both variants were re-run on the 36 failures at the sweep's own
extents:

| ranking | rescued |
|---|---:|
| ink-boundary, then (row, column) — AC-116 as written | 18 |
| (row, column) only — CARD-096's experiment | 19 |
| cells rescued only by ink-boundary | none |
| cells rescued only by (row, column) | `frog1.jpeg` at 30 |

So the ink-boundary rule costs exactly one conversion and gains none on this
corpus. Rendered for the owner by `meta/ops/nudge_ranking_contact_sheet.py`
(36 sheets, `~/Documents/nonogram-reviews/CARD-075/`: source, conversion with
the undecided cells tinted, then the two rules' results with the flipped pixels
in blue). A third measurement taken alongside them, since the sheets raise the
question: **the two rules choose identical cells in 22 of the 35 cases that do
not time out**, and of the 13 where they differ, only `frog1.jpeg` at 30 ends
differently. Where both succeed the flip counts are a wash — `dear.png` at
14x15 is 3 flips under ink-boundary against 4 under reading order, `dear1.jpg`
at 14x20 is 4 against 3.

The corpus therefore does not separate the two rules on yield or on economy;
it separates them by one picture. It is shipped anyway, because AC-116 mandates it and because the reason
it exists is fidelity rather than yield: a flip buried in a solid expanse plants
a stray dot or splits a run, and the owner's gate on image work is visual. The
trade is one conversion in 125 against that — **the owner's call, and it is
open**: dropping the distance term from the one `min()` key in
`next_nudge_cell` is the whole of the alternative, and
`test_nudge_prefers_cells_nearest_the_ink_boundary` is the test that would go
with it.

**Tests.** `tests/test_nudge.py` 37 (was 36): the mechanism half rewritten, the
AC/policy half unchanged in assertion. New `tests/property/test_nudge_mask.py`
carries EC-014 over 192 seeded ambiguous grids and 738 attempts, with both
floors asserted in the tests.

Real-image pins re-taken by this module's own 10..25 sweep recipe, in three
files — the same picture moving by one nudge shows up in each:

| pin | was | now |
|---|---|---|
| `test_nudge.py` recovery case, `owl1.png` | 10x10, 2 nudges | 10x10, **1** nudge |
| `test_nudge.py` cap case, `owl1.png` | 15x15 | **24x24** (15x15 is now made in 2) |
| `test_nudge_reporting.py` AC-040 plural line | `--size 10`, 2 nudges | **`--size 15x15`**, 2 nudges |
| `property/test_grid_dimensions.py` decode count | asserts 2 nudges | asserts **1** |

The last two are the ones a careless run would have missed: AC-040 asserts the
*plural* wording, and at 10x10 the run now prints the singular line that the
test below it owns — so it moved to a size where owl1 still needs two, rather
than having its assertion weakened. The decode-count property only needs both
runs to retry *at all*; its number moved, its premise did not.

**Mutation check** — five mutants, restored from saved copies, never
`git checkout`:

| mutant | caught by |
|---|---|
| regions swapped (mask before disagreement) | AC-115 + both property tests |
| `flipped` not excluded from the candidates | nesting tests + both property tests |
| ink-boundary term dropped from the ranking key | `..._prefers_cells_nearest_the_ink_boundary` |
| nudges the previous grid, not the original conversion | `..._stops_altering_the_image` |
| an exhausted mechanism re-judges the last grid | `..._when_there_is_nothing_left_to_add` |

The last one **survived the first pass** and is why that test exists: with
`next_nudge_cell` exhausted, re-judging the unchanged grid raises the same error
after the same five attempts. Only the solve count tells them apart, so the test
counts solves (1, not 5) as well as nudges (0).

**Full suite:** 3,431 passed, 0 failed, 26 skipped, with the two admin-markup
tests that already fail on `main` deselected
(`test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own`,
`test_size_configuration_applied`).

**Guardrails.** G-1 cap/POL-003 wording untouched (AC-034..AC-036 pass
unchanged in assertion). G-2 one `judge_candidate` path; image mode still never
repairs and never draws from the rng. G-3 nothing under `solver/`,
`difficulty.py`, `export/`, `web/`, `admin/`; `orchestrator.py` changed only at
the nudge call site and in the module docstring. G-4 no fixture altered. G-5 the
random-mode recovery loop untouched. G-6 explicit pathspecs.

**Also updated:** FR-013's statement, AC-115/AC-116 and EC-014 in
`requirements.yml` (with the 2026-09-12 gap recorded as dissolved rather than
answered, and AC-172 recorded as a meta/ops measurement); the FR-013 row in
`trace.yml`, now `done`; `docs/GENERATION_ALGORITHM.md` §8.4
(`check_doc_references.py`: 212 resolved, 0 failed).
