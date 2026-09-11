# CARD-064: Thin pictures — move up to Large instead of cropping, or say it can't be done

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
| c5 | 2.90:1 | 10x20 | **69%** | 10x30 | 96% |
| c9 | 2.36:1 | 10x20 | 85% | 13x30 | 98% |
| c4 | 2.26:1 | 10x20 | 89% | 13x30 | 98% |

All three generated at the Large extents in the same day's Large=30
measurement. The other 10 pictures keep 97–100% at Medium. A 5:1 picture
(e.g. 50x10) keeps only 60% even at Large (30x10), which is why some
pictures cannot be done at any supported size.

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
   - Small's short-side mode never crops up to about 3:1. Beyond that its
     current over-the-cap fallback (CARD-061, "too elongated" note) is the
     Large extent anyway, so it lands in `fits`-at-Large, or in
     `cannot_fit`.
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
