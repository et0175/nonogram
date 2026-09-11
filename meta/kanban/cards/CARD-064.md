# CARD-064: Thin pictures — move up to Large instead of cropping, or say it can't be done

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/064-thin-pictures-bump-or-message
**Worktree:** —
**Source:** project owner, 2026-09-11: c5 (`christmas/balls`) at Medium "looks chopped" in the preview; owner's decision: "have it in large resolution with message that medium is not possible. If large is also not possible (e.g. for 50*10 images) — then just display message"
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py (size prediction), src/nonogram/admin/app.py (batch loop, cropped-preview route), src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/generate_batch.html, tests
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-11T18:19:20Z
**Closed:** 2026-09-11T18:55:00Z
**Actual:** 0.03d
**Merge commit:** be582ea
**Blocked by:** —

## Why

A bare size N puts N on the grid's long side and derives the short side,
floored at 10 cells (ADR-0022/R4). For a picture more elongated than N:10,
the floor makes the grid squarer than the picture, and the aspect-preserving
crop (ADR-0022/R3: "never by stretching") cuts off its ends. Nothing warns
the user. Measured 2026-09-11 on the owner's `christmas/balls` set at Medium
(20):

| picture | shape | Medium | kept | Large (30) | kept |
|---|---|---|---|---|---|
| c5 | 2.90:1 | 10x20 | **69%** | 10x30 | 97% |
| c9 | 2.36:1 | 10x20 | 85% | 13x30 | 98% |
| c4 | 2.26:1 | 10x20 | 89% | 13x30 | 98% |

All three generated at the Large extents in the same day's Large=30
measurement. The other 10 pictures keep 97–100% at Medium. A 5:1 picture
(e.g. 50x10) keeps only 60% even at Large (30x10), which is why some
pictures cannot be done at any supported size. At the proposed 90% threshold
the cut-off is about 3.3:1: Large's 30x10 keeps 3 ÷ ratio of the picture, so
a 4:1 picture (75%) is skipped too, at every preset. That includes Small,
whose CARD-061 over-the-cap fallback has been generating such pictures at
30x10 with a note.

Squeezing was considered and not chosen: ADR-0022/R3 forbids stretching,
and a 2.9→2 squeeze visibly deforms a thin silhouette.

## Decision (owner, 2026-09-11)

1. If the chosen size would crop the picture, generate it at **Large** and
   show a message that the chosen size was not possible.
2. If Large would also crop it, **do not generate that picture**; show only a
   message.

"Would crop" means the grid keeps less than a threshold share of the
picture's ink bounding box. It is a named constant, **proposed 90%**
(`MIN_KEPT_SHARE = 0.9`); the owner may change it. At 90% it flags exactly
c4, c5 and c9 at Medium on the owner's set.

Dry run of the rule on today's code (2026-09-11): the 13 balls pictures plus
3.2:1, 4:1, 5:1 and 1:5 synthetic shapes, at small, medium, large and auto —
68 cases:
- 52 fit;
- 4 move to Large: c4, c5, c9 and the 3.2:1 shape, all at Medium;
- 12 cannot fit: the 4:1, 5:1 and 1:5 shapes at every preset.

## What to implement

1. **One fit decision** next to `predict_size()` (`image_manager.py`),
   computed once per image, returning: the extent to use, the size the user
   chose, and a status —
   - `fits`: the chosen size keeps ≥ `MIN_KEPT_SHARE`;
   - `moved_to_large`: it doesn't, but Large does;
   - `cannot_fit`: even Large keeps less.
   "Large" is the Large preset's size (30 on the long side, `app.py`'s
   `size_mapping`), derived the same way the Large preset is, not a second
   hard-coded 30. The kept share is computed from the ink bounding box ratio
   against the grid ratio.
   - Applies to every size mode: medium, a custom fixed size from the preview
     page, auto/min/max, and small's short-side mode.
   - Judge the chosen size by its *own* extent. For small's short-side mode
     that is the ratio pair when its long side fits under 30. When it
     doesn't (beyond about 3:1), the chosen size is not possible. The Large
     extent is judged instead, so the picture is `moved_to_large` or
     `cannot_fit`. CARD-061's separate "too elongated" note goes away.
     Example: a custom short side of 15 on a 2.5:1 picture needs 38 cells;
     Large's 30x12 keeps 100%, so it is `moved_to_large` and the change is
     visible, not silent.
   - Large itself can only be `fits` or `cannot_fit`.
2. **This replaces the two earlier "silent substitution" paths** with the
   same decision:
   - CARD-058's `SizeTooSmallForSource` upward search (which accepted
     anything keeping ≥50%);
   - CARD-061's over-the-cap fallback note.
   Keep `size_substitution()`'s callers working, or replace them in the same
   change; don't leave two mechanisms that can disagree (the CARD-058
   rationale).
3. **Preview page** (`image_preview.html`): for `moved_to_large`, show the
   Large size with a note like "Medium would cut this picture (keeps 69%) —
   using Large (10x30)". For `cannot_fit`, show a message instead of a size,
   e.g. "Too elongated for any supported size (at most 30 cells; even Large
   keeps only 60%) — this picture will be skipped", and don't render a
   misleading cropped preview for it.
4. **Confirmation page** (`generate_batch.html`): the same two states as
   compact badges.
5. **Batch generation** (`app.py`): generate `moved_to_large` images at the
   Large extent. CARD-062's ±1 retry still applies. Skip `cannot_fit` images
   without calling `generate()`, and list them in the batch results, e.g.
   "c7.jpg skipped: too elongated for any supported size".
6. Make the threshold easy to find and change, as a module constant with
   one line explaining it. It is a product choice, not a range bound.

## Acceptance criteria

- **AC-1** — c5's shape (162x469) at Medium: the status is
  `moved_to_large`, the extent is 10x30, and the preview shows the "Medium
  would cut this picture" note with the kept share.
- **AC-2** — a 5:1 picture (e.g. 500x100) at Medium or Large: the status is
  `cannot_fit`; the preview shows the skip message and no size; the batch
  makes no `generate()` call for it and lists it as skipped; the other images
  in the batch still generate.
- **AC-3** — every picture that keeps ≥ `MIN_KEPT_SHARE` at its chosen size
  gets exactly today's extent (pinned on the fixtures used by CARD-058,
  CARD-061 and CARD-062), with no note.
- **AC-4** — the threshold is one constant. Tests reference it rather than
  a literal 0.9, and moving it moves which pictures are flagged (a test at
  two thresholds).
- **AC-5** — across a seeded corpus of shapes (1:1–8:1, both orientations,
  every size mode), the status is consistent with the kept share the
  returned extent actually achieves:
  - `fits` → the chosen extent keeps ≥ threshold;
  - `moved_to_large` → the chosen extent keeps less and the Large extent
    keeps ≥ threshold;
  - `cannot_fit` → the Large extent keeps less.
  No extent leaves 10..30.
- **AC-6** — the CARD-058/061 substitution tests are updated deliberately to
  the new messages (not deleted without replacement), and no second
  mechanism still computes a different substituted size.

## Guardrails

- G-1: Admin-only. Do not change `sourcing/`, `orchestrator.py`, `cli.py`
  or ADR-0022's rules — no stretching (R3), and the CLI's bare `--size`
  behaviour (R4) stays as is.
- G-2: Never generate a `cannot_fit` picture, and never crop below the
  threshold silently: every changed or skipped picture is visible in the
  preview and in the batch results.
- G-3: Pictures that already fit keep their exact current extents (AC-3).
- G-4: Coordinate with CARD-063 (shared `limits` module). Both touch
  `image_manager.py` and the admin templates. Whichever lands second uses
  the other's constants rather than reintroducing literals.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).
Built on `f45d460`, with CARD-063 already merged: every bound uses
`nonogram.limits`, so no literal 10/30 was reintroduced (G-4).

**Implementation** (`admin/image_manager.py`):
- **`MIN_KEPT_SHARE = 0.9`**: a module constant with one line of rationale.
- **`SIZE_PRESETS`**: the batch form's preset table, moved here from
  `app.py`. The batch route now uses it, so "Large" has one definition. The
  values are unchanged and still literal (CARD-063 G-4).
- **`SizeFit`** (frozen dataclass: `extent`, `status`, `kept`, `chosen`,
  `chosen_kept`) and a status of `FITS`, `MOVED_TO_LARGE` or `CANNOT_FIT`.
- **`ImageFile.size_fit()`** is the one fit decision.
  - It computes the chosen size's own grid, `_own_extent(mode, value,
    source)`. For "short" that is the ratio pair, or `None` when the long
    side would pass `MAX_SIZE`. For fixed/max/min it is
    `derive_extent(stated)`, or `None` on `SizeTooSmallForSource`.
  - If that grid keeps at least `MIN_KEPT_SHARE`, the status is `FITS`.
    Otherwise Large's grid is judged (the same `_own_extent` with the Large
    preset). The fallback to `(30, 10)` or `(10, 30)` applies only beyond
    6:1. The status is `MOVED_TO_LARGE` or `CANNOT_FIT`, and `extent` is
    Large's in both cases.
  - A degenerate `(0, 0)` shape gives `(10, 10)`, `FITS`, with no note
    (CARD-045 behaviour kept).
- **`predict_size()`** returns `size_fit().extent`, and **`to_dict()`** adds
  `size_status`.
- **Removed:** `size_substitution()`, `_predict_size_detailed()` and
  `_short_side_extent()`. CARD-058's upward search and CARD-061's
  over-the-cap note are replaced by the one decision (step 2); no second
  mechanism remains (AC-6).

**Batch route** (`app.py`): it calls `size_fit()` before generating. A
`CANNOT_FIT` picture is skipped, never passed to `generate()`, and the
batch results list it ("… skipped: too elongated for any supported size
(even Large keeps only 60%)", capped at 3 lines like the others). Other
pictures generate at `fit.extent`, which is Large for `MOVED_TO_LARGE`;
CARD-062's ±1 retry still applies.

**Templates:**
- `image_preview.html`:
  - `MOVED_TO_LARGE`: "⚠ The chosen size (10×20) would cut this picture
    (keeps 69%) — using Large (10×30)."
  - `MOVED_TO_LARGE` with no chosen grid: "The chosen size can't keep this
    picture's shape — using Large (…)".
  - `CANNOT_FIT`: "⛔ Too elongated for any supported size (at most 30
    cells a side; even Large keeps only N% of it) — this picture will be
    skipped." The size shows as "skipped", and a placeholder replaces the
    cropped image, so no misleading crop is requested.
- `generate_batch.html`: a "⚠ moved to Large" or "⛔ will be skipped" badge,
  and the size cell reads "skipped".

**Consequences worth knowing** (both follow from the rule as decided):
- At 90%, any picture beyond about 3.3:1 is skipped at every preset.
- A custom per-image **Fixed Size of 10** moves most non-square pictures to
  Large, because the 10-cell floor makes the fixed-10 grid square. Example:
  a 4:3 picture keeps 75% at 10x10 and moves to 30x22. The note shows. The
  Small preset avoids this through the short-side rule.

**Tests:**
- New `tests/test_card_064_thin_pictures.py`: AC-1 (c4/c5/c9 shapes, and
  short side 15 over the cap); AC-2 (5:1 at every setting, and `size_status`
  in `to_dict`); AC-3 (11 pinned fitting extents); AC-4 (monkeypatched
  threshold at 0.85 and 0.99); AC-5 (3000-case seeded corpus, ≥100 per
  status). Two Flask end-to-end tests: c5 shape at Medium stored 10x30; a
  5:1 strip skipped with no `generate()` call while the square generates.
- Updated deliberately (AC-6), not deleted:
  - `test_card_058_…` now asserts the skip marking and status;
  - `test_card_061_…` swaps substitution assertions for statuses and turns
    the 4:1 over-the-cap cases into `CANNOT_FIT`. Its two `(400, 100)`
    fixed pins (20x10 at 50%, 25x10 at 62%) moved to CARD-064's `CANNOT_FIT`
    coverage.
- Red check: against `main`'s code the new test file cannot import
  `CANNOT_FIT`.

**Also updated deliberately:** `tests/test_image_batch_size_fix.py`'s
size-persistence test. It asserted that fixed 10 gives a long side of 10 for
a 4:3 picture, which is the forced 10x10 crop this card removes. It now
asserts that the square picture fits at 10x10 and the 4:3 pictures move to
Large (30 on the long side).

**Tests run:** the new file plus the CARD-058/061/062/063 tests,
`test_image_batch_size_fix`, `test_card_047`, `test_wave3_e2e`,
`test_admin_image_uniqueness`, `test_card_050`, `test_web_server` and
`test_cli`: 387 passed, 4 skipped. Commit `9906e48`.

**Full-suite comparison (AC-5)**, the branch against a clean export of
`main` at `f45d460`: 37 failed, 2754 passed on the branch; 39 failed, 2728
passed on `main`.
- Failing only on the branch:
  `test_batch_history.py::TestBatchRetry::test_retry_batch_uses_same_parameters`.
  It is in the file whose tests fail differently from run to run, and it
  failed on both trees when CARD-063's spot-check ran the file on its own.
  Rerun alone just now, it fails on both the branch and `main`, so it is
  pre-existing.

[Review 1/3] Score: 8.0 — crit: 0, imp: 1, minor: 3
[Review sync] 1 report(s) → meta/review/ (20260911T184200Z-CARD-064-cycle1.yml)
Cycle 1 summary (forge:review, independent agent): the fit decision
itself held.
- AC-3: 20,000-case comparison with the base `predict_size()`; all 4,360
  fitting cases keep the base extent.
- Large always matches the Large preset's own derivation (0 of 5,000
  mismatches).
- 10 of 11 mutation variants caught.
- The template and flash percentages never disagree (0 of 100,001 values).
- The real-picture claims reproduced exactly.
- Item 2 judged a faithful application of the owner's decision, not
  overreach.
- Its full suite was deliberately not run; this card's own comparison
  above covers AC-5.
**Important (G-2 violated):** a picture moved to Large got no line in the
batch results. The preview said so, but the results page showed only
"Generated 1 puzzle(s)" and a 10×30 thumbnail.
Minors:
- float boundary: at exactly 90% the status depended on orientation (100x90
  gave 0.8999999999999999, 90x100 gave 0.9), and `>=` → `>` survived the
  tests;
- CARD-062's ±1 retry can land under 90% (e.g. 10x29 keeps 88.7%) with no
  mention of the share;
- ADR-0022's History still describes the removed substitution and fallback.
Also noted: the two removed `(400, 100)` pins were covered only by 5:1 pins
and the corpus, not an exact 4:1 pin, so the notes overstated this.
Severity gate CLOSED — fix cycle.

[Fix delta after cycle 1]
- Important fixed: the batch results list each picture moved to Large (only
  for stored puzzles), e.g. "c5.jpg: moved up to Large — the chosen size
  10x20 would cut it (keeps 69%)", or "… the chosen size can't keep its
  shape" when it had no grid. Capped at 3 lines like the others. The AC-1
  end-to-end test now asserts the line.
- Float boundary fixed: `_kept_share` compares integer cross-products, so a
  picture and its transpose get bit-identical shares. A new test pins 100x90
  and 90x100 at fixed 10 as exactly 0.9 → `FITS` (10x10); `>` instead of
  `>=` now fails it.
- Retry under the threshold: kept, and made visible. When a ±1 retry's grid
  keeps less than `MIN_KEPT_SHARE`, its result line adds "; it keeps N% of
  the picture". Refusing such retries was rejected: it would undo real
  rescues such as b3 at Small (10x11 keeps 89%). New end-to-end test:
  441x1442 at Small moves to Large 10x30; abandoning 10x30 stores 10x29
  with "… it keeps 89% of the picture". New `ImageFile.kept_share()` and
  `keeps_enough()` back it, reading `MIN_KEPT_SHARE` at call time.
- ADR-0022: a dated History line, no rule change.
- The exact 4:1 pins were added: (400, 100) at fixed 20 and 25 → chosen
  20x10/25x10 → `CANNOT_FIT` (30x10).
- The same boundary bug was in the tests. CARD-061's corpus helper
  `_retained` divided ratios and got 0.8999999999999999 for 200x60 at
  Large's 30x10, an exact 90% case the fixed code now correctly calls
  `MOVED_TO_LARGE`. Both corpus helpers (CARD-061's `_retained`, CARD-064's
  `_kept`) now use integer cross-products too: still independent of the
  module's code, and exact at the boundary.
- Red check against `9906e48`: exactly the three new behaviour tests fail
  (the 100x90 boundary, the moved-to-Large results line, the retry share).
  The 4:1 pins pass there, as expected, since that picture was already
  `CANNOT_FIT`.
- ADR validators: `--verify-refs` finds no dead refs; `validate.py` gives
  0 errors and the 2 old warnings.
- Delta commit `74648ac`; the CARD-064/058/061/062/063 tests,
  `test_image_batch_size_fix`, `test_card_047`, `test_wave3_e2e`,
  `test_admin_image_uniqueness`, `test_card_050`, `test_web_server` and
  `test_cli`: 392 passed, 4 skipped.

[Review 2/3] Score: 9.0 — crit: 0, imp: 0, minor: 3 (confirmation mode, delta 9906e48..74648ac)
[Review sync] 1 report(s) → meta/review/ (20260911T185253Z-CARD-064-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation, and every item re-verified; none could
be carried, because each item's scope intersects the delta.
- G-2 now holds: moved pictures are listed in the batch results, and a
  retry under 90% states its share.
- The 3-fail red check against `9906e48` reproduced.
- Over 362,800 cases the cross-product change alters no status away from
  the exact-90% line. On that line, 182 cases now correctly move to Large.
- The owner's 52 real cases are unchanged.
- The retry-share resolution was judged sound: G-2 forbids *silent* crops
  below 90%, and refusing would lose b3's real rescue at Small (10x11 keeps
  89.1%).
Minors, recorded and not fixed (a fix would need a cycle 3):
- `app.py:446,460`: shares from 89.5% to just under 90% print as "90%",
  e.g. "keeps 90% of the picture" on a line that only appears under 90%;
- 4 of 10 mutants in the new test file survived, notably the moved-line
  cap (`[:3]` → `[:2]`). The code is correct: see the spot-check;
- the corpus helpers now share the code's formula, so AC-5's share
  comparison is no longer independent (`fractions.Fraction` would restore
  that).
Question for the owner: a picture already moved to Large, then abandoned
there, whose ±1 neighbour keeps under 90%, is generated with a note. His
rule "if Large also cuts it, skip" could be read as skip.
Severity gate OPEN. Cleared on cycle 2 of 3.

[8h spot-check] 1/1 sampled hold reproduced independently: a real admin
batch of 4 pictures shaped like c5 (162x469) at Medium shows 3 "moved up to
Large" lines plus "... and 1 more pictures moved up to Large". This covers
the cap no test pins.

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — unit tests plus end-to-end: c5 shape at Medium → 10x30 stored, with the note on the preview, confirmation and results pages.
AC-2 ✓ demonstrated — 5:1 and 4:1 cannot fit at every setting; the batch makes no `generate()` call, lists the skip and shows a placeholder.
AC-3 ✓ demonstrated — 11 pinned fitting extents; the reviewer's 20,000-case base comparison; 0 off-boundary status changes over 362,800 cases.
AC-4 ✓ demonstrated — one constant, read at call time; tests at 0.85 and 0.99; the inclusive boundary is pinned in both orientations.
AC-5 ✓ demonstrated — 3000-case corpus; full suite with no failure attributable to the card.
AC-6 ✓ demonstrated — no references to the removed functions; old tests updated with replacements, including exact 4:1 pins.
G-1 ✓ demonstrated — `sourcing/`, `orchestrator.py`, `cli.py` untouched; ADR-0022 gains a History entry only; validators 0 errors.
G-2 ✓ demonstrated — every move and skip is shown in the preview, the confirmation page and the batch results; retries under 90% state their share.
G-3 ✓ demonstrated — see AC-3.
G-4 ✓ demonstrated — no 10/30 literals added; `nonogram.limits` used.

[Commit] 2 commits on the branch: 9906e48 (implementation + tests),
74648ac (cycle-1 fixes).
- Failing only on `main`: 3 tests from the same flaky files
  (`test_batch_history` ×2, `test_wave1_e2e` ×1).

No failure attributable to this card.

**Real pictures** (owner's `christmas/balls`, the worktree's code): exactly
c4 (89% → 13x30, 98%), c5 (69% → 10x30, 97%) and c9 (85% → 13x30, 98%) at
Medium are `MOVED_TO_LARGE`; the other 49 of 52 picture×preset cases fit
unchanged.
