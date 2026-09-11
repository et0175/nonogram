# CARD-061: Admin "small" preset — 10 is the short side, the long side follows the picture

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Decision (owner, 2026-09-11)

- `MIN_SIZE = 10` stays the lower bound for **both** sides, project-wide.
  Nothing smaller than 10 on either axis, ever. Core `sourcing/` arithmetic
  and ADR-0022/R4 are **not** revised.
- Admin's **"small" preset changes meaning**: 10 is the grid's **short** side
  and the long side follows the picture's ratio (capped at `MAX_SIZE`).
- "medium" (20) and "large" (30) keep today's meaning: the preset value is the
  **long** side, the short side is derived (`derive_extent`), floored at 10.

Worked on the owner's `c11.jpg` (ink bbox 229x149, 1.54:1):

| preset | today | after this card |
|---|---|---|
| small | 10x10 (forced square, 65% kept) | **15x10** (~98% kept) |
| medium | 20x13 | 20x13 (unchanged) |
| large | 30x20 | 30x20 (unchanged) |

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
  e.g. `(20, 13)` / `(30, 20)` for the 1.54:1 fixture).
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
- G-3: "medium" and "large" behaviour is unchanged (AC-3 is the check).
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
