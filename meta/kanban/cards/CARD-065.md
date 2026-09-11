# CARD-065: Small follow-ups from CARD-061..064 — honest percentages, preset labels, stale tests

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
