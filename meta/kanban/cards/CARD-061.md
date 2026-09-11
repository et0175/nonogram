# CARD-061: Admin "small" preset — 10 is the short side, the long side follows the picture

**Status:** done
**Priority:** P2
**Category:** bugfix
**Estimate:** 0.25d
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/061-small-preset-short-side
**Worktree:** —
**Source:** project owner, 2026-09-11, while visually testing CARD-058 on real pictures ("picture preview depends on the selected puzzle size ... small size — it's trimmed and not squeezed"; later: "main difficulty in generation of small (10*10) puzzles — they mostly look bad")
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py, src/nonogram/admin/app.py (the `size_mapping` preset table), src/nonogram/admin/templates/batch_create.html (preset label only, if it changes), meta/architecture/decisions/adr/0022-grid-extent-and-size-range.md (one History note, no rule change)
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-11T13:59:54Z
**Closed:** 2026-09-11T14:33:00Z
**Actual:** 0.02d
**Merge commit:** 3cf8517
**Blocked by:** —

## Decision (owner, 2026-09-11)

- `MIN_SIZE = 10` stays the lower bound for **both** sides, project-wide.
  Nothing smaller than 10 on either axis, ever. Core `sourcing/` arithmetic
  and ADR-0022/R4 are **not** revised.
- Admin's **"small" preset changes meaning**: 10 is the grid's **short** side
  and the long side follows the picture's ratio (capped at `MAX_SIZE`).
- "large" moves from 25 to **30** (owner, 2026-09-11, after this card found
  it was 25, not the 30 both the card and the owner had assumed).
- "medium" (20) and "large" (30) keep today's meaning: the preset value is the
  **long** side, the short side is derived (`derive_extent`), floored at 10.

Worked on the owner's `c11.jpg` (ink bbox 229x149, 1.54:1):

| preset | today | after this card |
|---|---|---|
| small | 10x10 (forced square, 65% kept) | **15x10** (~98% kept) |
| medium | 20x13 | 20x13 (unchanged) |
| large | 25x16 | **30x20** (preset 25 → 30) |

Portrait pictures get the transposed grid (10 wide x 15 tall for a 1.54:1
portrait) — the long side lands on the axis the *picture* is longer on,
same convention as `_derived_extent`.

Why this is the right shape of fix: ADR-0022/R4 already says a token carrying
**both** dimensions "specifies the grid exactly and the source is fitted to
it" — so admin computing the small rectangle itself and handing the core an
explicit `(width, height)` is squarely inside the ADR. The CLI's `--size 10`
is untouched. Why only "small": the floor only bites where
`round(N * short/long) < 10`, i.e. essentially at N=10 (see "Background");
flipping medium/large to short-side semantics too would make them collapse to
the same 30xN grid for most real pictures (medium at 20-short already needs a
30-long side at 1.5:1), so the ladder would stop being a ladder.

## What to implement

1. In `ImageFile._predict_size_detailed()` (`image_manager.py:124`), add the
   small-preset path. Suggested representation: a new `size_mode` value
   (e.g. `"short"`) with `size_value` = the short side, so `app.py:217`'s
   table becomes `"small": (10, "short")` and the existing `"fixed"` path for
   medium/large is untouched. Arithmetic for `"short"`:
   - `long = round(size_value * long_edge / short_edge)`;
   - if `long <= MAX_SIZE`: the extent is `(long, size_value)` for landscape,
     `(size_value, long)` for portrait — a **full** pair, not a bare N;
   - if `long > MAX_SIZE` (picture more elongated than 3:1): do **not** clamp
     (a clamp crops, which is the harm this card removes). Fall back to
     today's rule at the top of the range — `derive_extent(MAX_SIZE, None,
     …)`, which yields 30x10 for 3:1..6:1 — and report it through the
     existing `size_substitution()` channel (CARD-058) so the preview says the
     picture was too elongated for "small". Beyond 6:1 the existing
     `SizeTooSmallForSource` handling already covers it.
2. Confirm the full pair actually reaches generation as an explicit extent:
   trace `predict_size()`'s `(width, height)` through `to_dict()` and the
   batch-generation path (CARD-049's solver-verified route) into
   `GenerationRequest`, and make sure nothing downstream re-derives from a
   single N. `validate_extent` and the CARD-026 aspect fit (>2x mismatch
   refusal) apply as usual; a ratio-derived pair is within 2x by
   construction, so the fit never refuses on this path.
3. Keep `update_image_size()` (`image_manager.py:385`) and
   `apply_size_to_all()` accepting the new mode; its "10..30" validation of
   `size_value` still holds (the short side is 10).
4. `batch_create.html:59` — the label "Small (10-15 cells)" becomes literally
   true for pictures up to 1.5:1; reword only if it now misleads (up to 3:1
   the long side can reach 30).
5. ADR-0022: add a History entry (no rule change) recording (a) the
   success-path consequence of the floor — at the minimum N the derived side
   is forced to `MIN_SIZE` and the grid stops following the source — and
   (b) that admin's "small" preset uses R4's explicit-pair clause to sidestep
   it, with the decision above. Do not touch R4's statement.

## Acceptance criteria

- **AC-1** — given a ~1.5:1 landscape fixture at the "small" preset, when
  `predict_size()` runs, then it returns `(15, 10)`; the same fixture rotated
  to portrait returns `(10, 15)`.
- **AC-2** — given a square fixture at "small", then `(10, 10)`; given a
  picture more elongated than 3:1 (e.g. 4:1), then the extent equals
  `derive_extent(30, None, …)`'s answer (30x10) and `size_substitution()`
  is non-`None`, so the CARD-058 note appears in the preview.
- **AC-3** — given the "medium" and "large" presets, when `predict_size()`
  runs on every existing test image, then the returned extents are
  byte-identical to before this card (pin with the existing expectations,
  e.g. `(20, 13)` / `(25, 16)` for the 1.54:1 fixture). The "large" preset
  itself maps to fixed 30 (owner decision, 2026-09-11), so that fixture
  gives `(30, 20)` at large.
- **AC-4** — no returned extent has a side under 10 or over 30, on a seeded
  corpus of ratios from 1:1 to 6:1 in both orientations (hand-built
  stdlib-`random` corpus with an asserted minimum case count, per the
  project's test style).
- **AC-5** — the generated puzzle for a "small" image is actually 15x10
  (end-to-end through the batch route, not just the prediction), i.e. the
  explicit pair reaches the pipeline.
- **AC-6** — ADR-0022 carries the History note from step 5; `system_rules.py
  --verify-refs` and `validate.py --phase all` still pass.

## Guardrails

- G-1: Do not touch `sourcing/`, `cli.py`, `orchestrator.py`, `MIN_SIZE`,
  `MAX_SIZE`, `validate_size`, or anything under `tests/property/`. The
  10..30 bound on both sides is owner-confirmed and untouched.
- G-2: Never clamp the long side to 30 on the "small" path — fall back to
  `derive_extent(MAX_SIZE, …)` instead. A clamp would reintroduce the exact
  crop this card exists to remove, one step over.
- G-3: "fixed"-mode arithmetic and the "medium" preset are unchanged (AC-3
  is the check). "large" changes only its preset value, 25 → 30, by the
  owner's decision of 2026-09-11 (revised from "large unchanged" after
  review cycle 1).
- G-4: ADR-0022/R4's statement is not edited; only a History entry is added.
- G-5: Keep the two causes separate in the write-up: this fixes the *shape*
  of small puzzles, not their resolution — a 10x10 of a square picture is
  still 100 cells. Don't claim more than a side-by-side shows.

## Background (the finding, kept for the record)

ADR-0022/R4 (`0022-grid-extent-and-size-range.md:121-151`): a bare N is the
grid's **longer** side, the shorter side is `round(N * short/long)` floored at
`MIN_SIZE` — `_derived_extent`, `random_grid.py:218`:

```python
derived = max(MIN_SIZE, round(stated * shorter_edge / longer_edge))
```

`MIN_SIZE` is 10 and, since CARD-023, 10 is also the smallest allowed N. At
`N = 10` the derived side is `max(10, ≤10)` = 10 for *every* source, so the
smallest puzzle is forced square regardless of the picture's shape and crops
it — the "trimmed, not squeezed" the owner saw. Nothing raises (this is the
floor path succeeding, not the `SizeTooSmallForSource` refusal path), so
CARD-058's note could not cover it. The effect fades as N grows:

| N | source ratios that still track exactly | c11 (1.54:1) retained |
|---|---|---|
| 10 | none — every non-square source → 10x10 | 65% |
| 12 | up to 1.2:1 | 78% |
| 15 | up to 1.5:1 | ~98% |
| 20 | up to 2:1 | ~100% |

Options considered before the decision above: **A** accept and document;
**B** retarget the "small" preset (chosen, in the short-side form); **C** a
CARD-058-style warning when the floor forced a square; **D** decouple the
floor from the smallest N (allow 10x7) — rejected by the owner: 10 stays the
lower bound on both axes.

"10x10 puzzles look bad" has two causes and only one is fixed here: the
forced-square crop (this card) and plain resolution (100 cells is coarse for
any picture). Measure them separately when judging the result.

## Worktree notes

[Env] forge 2026.8.17 (no `meta/.skills.yml`, so no min_version comparison).

**Implementation.** New size mode `"short"` on `ImageFile`
(`size_value` = short side). `_predict_size_detailed()` routes it to a new
`_short_side_extent()`: `long = round(short * long_edge / short_edge)`;
if `long <= 30` the result is a full `(W, H)` pair on the picture's own
orientation, else it falls back to `derive_extent(30, None, …)` (and to
`(30, 10)`/`(10, 30)` beyond 6:1) with
`size_substitution() == {"requested": long, "used": 30, "reason":
"too_elongated"}`. Degenerate `(0, 0)` shape → `(10, 10)`, `None`, same as
the existing fallback. `app.py`: `"small": (10, "short")`; the preset loop
passes the mapped mode through instead of hard-coding `"fixed"`; the batch
record's `sizes` treats `"short"` like `"fixed"`. `update_image_size()`
stores `size_value` for `"short"` too. Generation needed no change — it
already passes `predict_size()`'s pair as `GenerationRequest(width,
height)`, so the full pair reaches the pipeline (AC-5 proves it end to
end). `sourcing/`, `cli.py`, `orchestrator.py`, `MIN_SIZE`/`MAX_SIZE`
untouched (G-1).

**SCOPE+ `image_preview.html`, `generate_batch.html`** (beyond the
predicted `batch_create.html` label): the over-the-cap note needed its own
wording — CARD-058's "Requested N was too small …" would read backwards
("requested 40 … using 30"), so both templates branch on
`substitution.get('reason')`.

**Found and fixed on the way — required, not opportunistic.** The preview
page's per-image mode `<select>` rendered with no `selected` option, and
its submit handler posts each dropdown's current value. So saving that page
resubmitted every image as its first option ("fixed"): a "short" image would
silently turn back into fixed-10 — the forced square this card removes. The
options now carry `selected` from `image.size_mode`, and the JS shows the
size input for `"short"` as well as `"fixed"`. Side effect worth knowing:
the same bug was already silently converting the **"auto" preset** (`max`
mode) into fixed-20 whenever the preview page was saved; that now survives
too. Guarded by
`test_preview_page_keeps_the_short_mode_through_its_save_round_trip`.

**Card fact corrected.** The card originally said "large" = 30 (and the
owner described large as 30x20 on 2026-09-11). It is `(25, "fixed")` at
`app.py:219`, so c11 is 25x16 at large, not 30x20. Left unchanged per G-3;
flagged to the owner.

**Tests.** `tests/test_card_061_small_preset_short_side.py`, 23 tests.
Red→green: run against `main`'s unchanged code (copied to the scratchpad, so
the editable install resolved to `main`'s `src/`), 12 fail — every
AC-1/AC-2/AC-4/AC-5 test and the page tests — and the 11 that pass there are
the "must stay unchanged" pins (8 fixed-mode extents, the medium/large
preset mapping, the degenerate shape). AC-4's corpus: 3000 seeded cases,
ratios 1:1–5.9:1, both orientations, short side 10–30; asserts range,
orientation, ≥95% retained when followed, ≥50% when falling back, and ≥300
cases on each branch.

**Regression.** New file + `test_card_058_…`, `test_image_batch_size_fix`,
`test_card_047_…`, `test_wave3_e2e`, `test_admin_image_uniqueness`,
`test_derive_shape`, the structural import guard: all pass except 4 in
`test_derive_shape.py`, which need `pictures/cat.jpg` — `pictures/` does not
exist on `main` either, and the same 4 fail there. Pre-existing, not this
card.

**AC-6.** `system_rules.py --verify-refs`: `check_refs_verified: true`, no
dead refs. `validate.py --phase all`: 0 errors, 2 pre-existing warnings
(ADR-0006 Migration value, missing `trace.yml`).

**Visual check on the owner's pictures** (memory: the owner validates on
real pictures). All 13 of `christmas/balls/*.jpg` at "small" before/after,
generated through the real pipeline:
`scratchpad/card061_small_before_after.png`. Shapes now follow the picture
(c11 sleigh 10x10 → 15x10, c5 candle 10x15 → 10x29, c4/c8/c9 candles, c15
tree) and read clearly better.

**Finding the owner needs to decide on — abandonment.** Generation is
deterministic (5 runs each: always 5/5 or 0/5). At "small", **3 of 13
pictures that generated as forced squares are now abandoned** at their true
shape (not uniquely solvable after 5 pixel nudges): b3 10x12, c12 17x10,
c14 10x13. b4 is abandoned both before and after. All three are rescued by
one cell on the long side: b3 at 10x11, c12 at 16x10 or 18x10, c14 at
10x12 or 10x14; b4 fails at 10x11–10x13 too. In an admin batch an abandoned
image is recorded as an error and skipped (CARD-049), so without a fallback
those pictures drop out of "small" batches. Candidate follow-up (not in this
card's scope): on `GenerationAbandoned`, admin retries long side ±1 before
giving up, noting the change like CARD-058 does.

**Browser check not possible.** The worktree admin ran on
`127.0.0.1:5061` and answered `curl` (HTTP 200), but Chrome's requests never
reached it (no hits in the server log, error page in the tab), so the JS
toggle was verified by the rendered-HTML/Flask tests and by reading the
code, not in a browser.

[Review 1/3] Score: 8.5 — crit: 0, imp: 0, minor: 2
[Review sync] 1 report(s) → meta/review/ (20260911T141819Z-CARD-061-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review, independent agent): re-derived AC-1..AC-6
and G-1..G-5, all held. It ran five in-memory wrong implementations,
including a clamp, and all were caught by the AC-4 corpus. It confirmed the
dropdown bug against the JS and the POST handler, confirmed the 4
`test_derive_shape` failures reproduce on an export of the base commit, and
confirmed the ADR numbers (65.1% vs 97.6%; fallback threshold between 3.05:1
and 3.06:1). Minor 1: the over-the-cap note claimed "part of its length is
cropped", which is false for a short side above 10 (250x100 at short 15 →
30x12, nothing cropped) and for pictures beyond 6:1 (generation refuses
them). Minor 2: the dropdown fix changes "auto" in practice (on the owner's
pictures its long side goes from about 20 to 30); no test pinned it and 30
was unmeasured. Out of scope: at short side 10 the fallback always equals
what a clamp would give (G-2 only matters above 10); the batch `sizes`
record stores the short side for small but the long side for other
presets; the `apply_size_to_all` docstring was stale. Abandonment (item 6):
follow-up, not a gate — now CARD-062. Severity gate OPEN.

[Owner delta, after cycle 1] Owner asked for "large" = 30 (2026-09-11).
The card's Decision, G-3 and AC-3 were revised to match; `app.py` maps
`"large": (30, "fixed")`, and the preset test pins 30. Also fixed: Minor 1
(the note now says only what is true in every case: the long side stopped at
the 30 cap), Minor 2 (a save round-trip test for "auto"/max), and the stale
`apply_size_to_all` docstring. Not changed: the `sizes` record, which is
informational.
Measured on the owner's 13 pictures, one deterministic run each: at large
25, 7 are abandoned (b1, b3, b4, c5, c8, c11, c14 — the 25x16 c11 is among
them); at large 30 only b3 is abandoned. "auto" gives the same extents as
large 30 on all 13, so the auto side effect lands on the better-measured
size. Every generation took ≤0.1s.

[Review 2/3] Score: 9.0 — crit: 0, imp: 0, minor: 2 (confirmation mode, delta 7adb841..06d68a9)
[Review sync] 1 report(s) → meta/review/ (20260911T142943Z-CARD-061-cycle2.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 2 summary: pure confirmation. It re-verified AC-1..AC-5 and all
guardrails against the revised card, and carried AC-6 (the delta touches
nothing under `meta/`). The new note wording held on an 85-case sweep
(short side 10–30, both orientations, ratios 1:1–10:1). It reproduced the
7-of-13 (large 25) vs 1-of-13 (large 30) abandonment figures exactly.
Test file: 26 passed. Regression set: 54 passed, 4 skipped, plus the 4
known pre-existing `test_derive_shape` failures.
Unaddressed Minors (recorded, not fixed — a fix would need a cycle 3):
(1) for pictures beyond 6:1 the note says the grid uses 30 cells, but
generation then refuses the picture (`ImageNeedsManualCrop`). CARD-058's
note for the other modes has the same gap. (2) The "large = 30" decision
reached only `app.py`: `batch_create.html:61` still reads "Large (25-30
cells)", and `tests/test_image_batch_size_fix.py:204-258` keeps its own
stale copy of the preset table ("Large applies size 25"), which stays green
without exercising the app. Informational: a dead copy of the preset table
(large 25) sits in `image_selection.html:294`, rendered by no route.
Severity gate OPEN. Cleared on cycle 2 of 3.

[8h spot-check] 2/2 sampled holds reproduced independently: `app.py:219` is
`"large": (30, "fixed")`; 250x100 at short side 15 → `(30, 12)` with
`{"requested": 38, "used": 30, "reason": "too_elongated"}` (G-2: a clamp
would give 30x15).

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — (15,10)/(10,15)/c11 → 15x10 tests; red on base, green on head.
AC-2 ✓ demonstrated — square → 10x10; 4:1 → (30,10) = derive_extent(30); the note renders on both pages.
AC-3 ✓ demonstrated — fixed-mode pins identical on base and head; the large preset → 30 per the revised card.
AC-4 ✓ demonstrated — 3000-case seeded corpus, ≥300 per branch; the cycle-1 reviewer's 5 wrong implementations were all caught.
AC-5 ✓ demonstrated — end-to-end batch route stores a 15x10 grid; red on base.
AC-6 ✓ demonstrated — History-only ADR change; verify-refs clean; validate.py 0 errors.
G-1..G-5 ✓ demonstrated — structural `git diff --name-only` checks plus the behavioural tests above, each re-verified in cycle 2.

[Commit] 2 commits on the branch: 7adb841 (implementation + tests),
06d68a9 (owner delta + cycle-1 minors).
