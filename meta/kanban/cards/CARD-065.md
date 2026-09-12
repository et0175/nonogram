# CARD-065: Small follow-ups from CARD-061..064 — honest percentages, preset labels, stale tests

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/065-small-follow-ups
**Worktree:** —
**Source:** Minor review findings left open by CARD-061 (cycle 2), CARD-063 (cycles 1–2) and CARD-064 (cycle 2); owner asked for this card on 2026-09-11
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/batch_create.html, src/nonogram/admin/templates/puzzles_list.html, src/nonogram/admin/templates/book_select_puzzles.html, src/nonogram/admin/templates/image_selection.html (delete, if confirmed dead), tests/test_image_batch_size_fix.py, tests/test_card_064_thin_pictures.py, tests/test_card_061_small_preset_short_side.py, tests/test_card_063_limits.py
**Review score:** 9.5 (cycle 2/3)
**Started:** 2026-09-12T04:03:05Z
**Closed:** 2026-09-12T04:35:00Z
**Actual:** 0.02d
**Merge commit:** 18a2287
**Blocked by:** —

## Why

Each item is a Minor finding that was recorded rather than fixed, because
fixing it would have cost a third review cycle on an otherwise-passing card.
None changes what size a picture gets. They are about the admin telling the
truth, and tests that actually pin what they claim to.

## What to implement

1. **Percentages never round up across the threshold** (CARD-064, cycle 2).
   A share between 89.5% and 90% prints as "90%" in five places:
   - `app.py:387` — the skip line ("even Large keeps only …");
   - `app.py:446` — the moved-to-Large line ("would cut it (keeps …)");
   - `app.py:460` — the retry note ("; it keeps … of the picture"), which
     only appears *below* 90%, so "90%" there is plainly wrong;
   - `image_preview.html:110` and `:123` — the same two numbers on the
     preview.
   Show whole percentages rounded **down** (89.7% → "89%"), in one helper
   used by both `app.py` and the templates (e.g. a Jinja filter), so the
   pages and the results can't disagree. A share of exactly 90% still reads
   "90%".
2. **Preset labels say what the presets do**
   (`batch_create.html:59-62`, CARD-061 cycle 2). Medium reads
   "(15-25 cells)" and Large "(25-30 cells)". Since CARD-061/064 they are
   20 and 30 cells on the long side; Small already reads "10 cells on the
   short side". Word Medium and Large to match. Mention that a thin picture
   may move up to Large, but keep it short, since this is a dropdown.
3. **"Size (px)" → "Size (cells)"** on the two puzzle filters
   (`puzzles_list.html:58`, `book_select_puzzles.html:28`). They filter on
   grid cells, not pixels (CARD-063 cycle 1).
4. **Rebuild the two stale preset tests** in `tests/test_image_batch_size_fix.py`
   (from about line 195), CARD-061 cycle 2.
   - The small-preset test keeps its own copy of the preset table
     (`"small": (10, "fixed")`, `"large": (25, "fixed")` at line 212).
   - `test_page1_large_size_applied_to_images` hard-codes 25.
   - Both re-implement the route's loop instead of exercising the app, so
     they stay green whatever the app does.
   Drive them through the real upload route (`/batch/from-images` with
   `default_size`), or at least through `image_manager.SIZE_PRESETS`. Then
   assert the real outcome: Small → the "short" mode with 10; Large → fixed
   30.
5. **Pin the three-line cap on the moved-to-Large lines**
   (`app.py:482`, CARD-064 cycle 2). A mutant changing `[:3]` to `[:2]`
   survived the suite. Add a test with 4 moved pictures asserting 3 lines
   plus "... and 1 more pictures moved up to Large". The 2026-09-11
   spot-check did this by hand. The owner's set moves exactly 3 pictures at
   Medium, so the cap matters.
6. **Pin the "apply to all" hint** (`image_preview.html:36`, CARD-063
   cycle 2). A mutation to `{{ MIN_SIZE }}-{{ MIN_SIZE }}` passes the suite.
   Assert the rendered hint next to the `globalSizeValue` input reads
   `{MIN_SIZE}-{MAX_SIZE}`, in `tests/test_card_063_limits.py`'s
   rendered-page test.
7. **Make the corpus checks independent again** (CARD-064 cycle 2).
   `_kept` in `tests/test_card_064_thin_pictures.py:54` and `_retained` in
   `tests/test_card_061_small_preset_short_side.py:59` now use the same
   cross-product formula as `image_manager._kept_share`. Use
   `fractions.Fraction` instead, which is exact and a genuinely different
   computation.
8. **Remove the dead `image_selection.html`**, if confirmed dead. No route
   renders it (grep of `src/nonogram/admin/*.py`, 2026-09-11), and it
   carries its own copy of the S/M/L presets through a JavaScript
   `applyDefaultSize()`, which is exactly the kind of second preset table
   CARD-064 removed from `app.py`. Re-check for references first: routes,
   `{% include %}`/`{% extends %}`, links, tests. Keep it and write down why
   if anything uses it.

## Acceptance criteria

- **AC-1** — for a share of 0.897, every place that prints it (the three
  `app.py` lines and both preview-page spots) shows "89%". For exactly
  0.9 they show "90%". Unit-tested on the helper, and end to end on at
  least the retry note and the preview.
- **AC-2** — the rendered batch form's preset labels match what each preset
  does (Small: short side 10; Medium: long side 20; Large: long side 30),
  asserted against `image_manager.SIZE_PRESETS` rather than restated
  literals.
- **AC-3** — both filter labels read "Size (cells)".
- **AC-4** — the rebuilt preset tests fail if `SIZE_PRESETS` or the route's
  preset handling changes. Demonstrate by mutation, e.g. Large → 25 or
  Small → fixed.
- **AC-5** — the moved-line cap test fails with `[:2]` or `[:4]`; the
  apply-to-all hint test fails with the `MIN_SIZE`-`MIN_SIZE` mutation.
- **AC-6** — the corpus helpers use `Fraction`, and the AC-5 corpus tests
  of CARD-061 and CARD-064 still pass.
- **AC-7** — `image_selection.html` is either deleted with a recorded
  "no references" check, or kept with the reason written in the Worktree
  notes.

## Guardrails

- G-1: No behaviour change to sizing. `size_fit()`, `MIN_KEPT_SHARE`,
  `SIZE_PRESETS` values, `_kept_share` and the batch generate/skip logic
  stay exactly as they are; only how shares are *printed* changes.
- G-2: Do not weaken any existing assertion to make room. The two stale
  preset tests are rebuilt, not deleted.
- G-3: Admin-only. No edits under `sourcing/`, `orchestrator.py`, `cli.py`
  or the web adapter.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).
Built on `5fe1794`.

**1. Percentages (AC-1).** New `image_manager.floor_percent(share)` returns
a whole percent rounded down (`0.897` → `"89%"`). `app.py` uses it in all
three result lines (the skip line, the moved-to-Large line and the retry
note) and registers it as the Jinja filter `percent`, which
`image_preview.html` uses for both of its shares. One helper, so a page and
a results line can't disagree. The boundary still reads "90%", because
`floor_percent(0.9)` is `"90%"`.
- The CARD-064 retry test's expected text changes from "89%" to "88%": the
  10x29 grid keeps 88.69%, which is exactly the case the old rounding got
  wrong.

**2. Preset labels (AC-2).** `batch_create.html`: Medium is "20 cells on the
long side", Large "30 cells on the long side" (they read "15-25" and
"25-30"). Small already said "10 cells on the short side". The new test
builds the expected strings from `SIZE_PRESETS`, so changing the table
without the labels fails.

**3. Filter labels (AC-3).** "Size (px)" → "Size (cells)" in
`puzzles_list.html` and `book_select_puzzles.html`; they filter grid cells.

**4. The two stale preset tests (AC-4).** `test_image_batch_size_fix.py`'s
`TestImageBatchPage1Defaults` kept its own preset table (Small as fixed 10,
Large as 25) and re-implemented the route's loop, so it stayed green
whatever the app did. It now uploads through `/batch/from-images` with a
`default_size` and checks the result against `SIZE_PRESETS`: one
parametrised test over all four presets, plus Small landing 10 on the short
side (13x10 on a 4:3 picture) and Large landing 30 on the long side
(30x22 — `round(22.5)` is 22, the tie ADR-0022/R4's property test pins; I
first wrote 23 and the test caught it).

**5. The moved-line cap (AC-5).** New test: 4 pictures shaped like c5 at
Medium give 3 "moved up to Large" lines plus "... and 1 more pictures moved
up to Large". This is what the surviving `[:3]` → `[:2]` mutant needed.

**6. The apply-to-all hint (AC-5).** `test_card_063_limits.py`'s rendered
page test now also asserts `>10-30</small>`, the hint under the global size
input, which the `min`/`max` checks never saw.

**7. Corpus helpers (AC-6).** `_kept` (CARD-064) and `_retained` (CARD-061)
use `fractions.Fraction` on the two ratios — exact, and a different
computation from the module's integer cross-products, so the comparison is
independent again.

**8. `image_selection.html` deleted (AC-7).** 323 lines, rendered by no
route (`/batch/select-images` renders `batch_create.html`), included by no
template, referenced by no test — `test_wave3_image_generation.py`'s
`test_image_selection_page_loads` loads `/batch/select-images`, which is a
different page. It carried its own S/M/L preset copy in a JavaScript
`applyDefaultSize()`, the second preset table CARD-064 set out to remove.

**Red check:** against `main`'s `src/`, the new test file cannot import
`floor_percent`.

**Tests:** the new file plus `test_image_batch_size_fix`, the CARD-058/061/
062/063/064 tests, `test_puzzles_list_pagination`, `test_wave3_e2e`,
`test_wave3_image_generation`, `test_admin_image_uniqueness`,
`test_card_050`, `test_batch_generator`, `test_puzzle_review`,
`test_web_server` and `test_cli`: 463 passed, 20 skipped. Commit `9b28da6`.

[Review 1/3] Score: 9.0 — crit: 0, imp: 0, minor: 3
[Review sync] 1 report(s) → meta/review/ (20260912T042447Z-CARD-065-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review, independent agent): AC-1..AC-7 and G-1..G-3
all held.
- G-1: `size_fit()` outcomes identical to base over 6,750 cases.
- AC-6: the `Fraction` helpers are bit-identical to the module over
  7,384,545 cases, with 0 threshold straddles.
- AC-4: Large 30→25 kills 25 tests; Small short→fixed kills 5; a route
  ignoring `default_size` kills 11.
- AC-5: `[:2]`, `[:4]` and the MIN-MIN hint mutations are all killed.
- AC-7: no route, include, test or JS referenced the deleted template.
- Full suite: head 2789 passed / 38 failed vs base 2769 / 40; the one
  head-only failure is the known wave1 flake.
- The 90% boundary is safe: `0.9 * 100` is exactly 90.0, and no reachable
  share lands there through the float artifact below.
Minors, all fixed in the delta below:
- `floor_percent` truncated a float artifact one point low: an exact 0.58
  prints "57%" because `0.58 * 100` is 57.99999999999999. Measured at
  1,410 of 57,238,272 reachable share combinations (~0.0025%);
- 3 of the 5 converted percent sites survived reverting to round-to-nearest,
  because the inherited CARD-064 assertions use 60% and 69%, where both
  agree;
- the rebuilt preset tests uploaded one picture, so mutating the route to
  `get_all_images()[:1]` survived — and "the preset reaches *every* image"
  is what that test class is named for.

[Fix delta after cycle 1]
- `floor_percent` adds a 1e-9 epsilon before flooring, with the reason in
  its docstring. Unit tests pin 0.58 → "58%", 0.29 → "29%", 0.57 → "57%",
  alongside the existing cases and the 0.9 boundary.
- Two end-to-end tests use shares where rounding down and rounding to
  nearest disagree (85.714%): a 100x350 picture cannot fit (the skip line
  and the preview must read 85%, not 86%), and a 300x700 picture moves to
  Large (its chosen 10x20 keeps 85.714%, so the moved line and the preview
  must read 85%).
- The rebuilt preset tests upload two pictures again and assert both got
  the preset and the same predicted extent.
- Delta commit `e28799f`; the same suites: 468 passed, 20 skipped.
- Mutation check of the delta, in a scratch copy (the worktree untouched):
  all 6 mutants killed — no-epsilon `floor_percent` (3 tests fail), the skip
  line and the moved line back to round-to-nearest (1 each), the preview's
  `kept` and `chosen_kept` back to `|round|int` (1 and 2), and the route
  updating only the first image (5). The three that survived cycle 1 are
  among them.

[Review 2/3] Score: 9.5 — crit: 0, imp: 0, minor: 0 (confirmation mode, delta 9b28da6..e28799f)
[Review sync] 1 report(s) → meta/review/ (20260912T043732Z-CARD-065-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation, no findings. All three cycle-1 Minors
genuinely fixed.
- The epsilon is correct, not convenient: it is 1e-9 of a *percent*, and
  reachable shares are `p/q` with `q ≤ 30 × max(source dimension)`, so a
  true shortfall is at least `1/q` — defeating it would need a source
  dimension over 33M px. 0 mismatches against exact `Fraction` over 400k
  reachable combinations; the smallest real gap seen was 5.82e-06 percent,
  about 5,800× the epsilon. The 0.9 boundary is intact.
- Mutation: 9 of 9 killed (my 6 plus the 3 AC-4 mutants re-run because the
  delta rewrote their covering file).
- G-1: a 2,744-row `size_fit` corpus and 1,225 `_kept_share` values are
  byte-identical to a clean `5fe1794` export.
- G-2: 463 → 468 tests is exactly the 5 added; nothing weakened.
- Suite reproduced: 468 passed, 20 skipped.
Out of scope, recorded by the reviewer: `floor_percent(0.89999999999999)`
returns "90%" (unreachable — it needs a >33M px source), and one assertion
checks `"86%" not in body` across the whole page rather than the one line.
Severity gate OPEN. Cleared on cycle 2 of 3.

[8h spot-check] 1/1 sampled hold reproduced independently: `floor_percent`
agrees with exact rational flooring over 200,000 reachable
(source, extent) pairs — 0 mismatches — and `floor_percent(0.9)` is "90%".

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — unit table incl. the float-artifact cases; all five print sites mutation-pinned.
AC-2 ✓ demonstrated — labels built from `SIZE_PRESETS`; a 20→25 label mutation kills 26 tests.
AC-3 ✓ demonstrated — both templates and the rendered `/puzzles` say "Size (cells)".
AC-4 ✓ demonstrated — two pictures asserted; Large→25, Small→fixed and a route ignoring `default_size` each kill tests.
AC-5 ✓ demonstrated — `[:2]`/`[:4]` and the MIN-MIN hint mutations killed.
AC-6 ✓ demonstrated — `Fraction` helpers bit-identical to the module over millions of cases, 0 threshold straddles.
AC-7 ✓ demonstrated — template absent; no route, include, test or JS referenced it.
G-1 ✓ demonstrated — `size_fit`/`_kept_share` outcomes identical to base.
G-2 ✓ demonstrated — test diffs read line by line; no assertion weakened.
G-3 ✓ demonstrated — the diff touches only `admin/**` and `tests/`.

[Commit] 2 commits on the branch: 9b28da6 (implementation + tests),
e28799f (cycle-1 minors).
