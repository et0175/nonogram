# CARD-069: Up to three size options per picture, one puzzle per size

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/069-size-options-per-picture
**Worktree:** —
**Source:** owner, 2026-09-12: "possibilities to add/remove sizes (and corresponding predicted outputs) — actually, we need to have 3 possible options per picture: min, max and fixed"
**Idea:** —
**Wave:** —
**Depends on:** CARD-067 (same page and the prediction endpoint)
**Touches:** src/nonogram/admin/image_manager.py (a picture carries a list of size options), src/nonogram/admin/app.py (preview save, the generate loop, the batch size record, the results lines), src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/generate_batch.html, tests (CARD-058/061/062/064/065 all assert against a single size)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why and decision (owner, 2026-09-12)

A picture currently carries exactly one size (`size_mode` + `size_value`)
and the batch makes exactly one puzzle from it. The owner wants up to three
options per picture — min, max and fixed — each with its own predicted
output, and **one puzzle per selected size**: a picture with two options
ticked yields two puzzles in the batch.

Naming, per the owner: either a name per option, or the size appended to the
generated name. Default to appending the size (e.g. "c11 (15x10)") and let a
typed name win, so two puzzles from one picture are never
indistinguishable.

This is the one item of the 2026-09-12 review that changes the data model,
which is why it is last and on its own.

## What to implement

1. **A picture carries a list of size options**, not one. Each option is a
   `(mode, value)` pair as today (`fixed` with a value, `short` with a
   value, `min`, `max`), with at most one option per mode. The default for a
   freshly uploaded picture stays exactly one option, the batch preset's, so
   nothing changes for a user who doesn't touch it.
2. **Per-option predicted output.** Each option shows its own extent, fit
   status and note (CARD-064's fits / moved-to-Large / cannot-fit), through
   CARD-067's prediction endpoint.
3. **Add and remove options** on the preview card, capped at the three
   modes. Removing the last option is the same as removing the picture from
   the job (CARD-067) — decide whether to block it or to treat it as a
   removal, and say which.
4. **Generation: one puzzle per option.** The batch loop iterates
   `(picture, option)` pairs. Per option, everything CARD-062 and CARD-064
   established applies unchanged: the ±1 retry on abandonment, the move to
   Large, the skip, and the result lines — each naming the picture *and* the
   size, since a picture can now appear several times.
5. **Everything downstream that assumed one puzzle per picture** has to
   follow: the batch's `sizes` record, the "Generated N puzzle(s) from M
   image(s)" line (N is no longer bounded by M), the confirmation page's
   one-row-per-picture table, and the generated-puzzles page, where puzzles
   from one picture should read as a group.
6. **The older tests assert a single size** (CARD-058, CARD-061, CARD-062,
   CARD-064, CARD-065 and `test_image_batch_size_fix`). Update them
   deliberately to the single-option default, with replacements, never by
   deletion.

## Acceptance criteria

- **AC-1** — a picture with fixed 20 and min ticked produces two puzzles in
  one batch, at the two predicted extents, with distinguishable names.
- **AC-2** — each option shows its own predicted output and status on the
  preview and the confirmation pages, including one option that fits and one
  that moves to Large on the same picture.
- **AC-3** — a picture with one option behaves exactly as today: same
  extent, same name, same result lines (pin the current behaviour first, so
  the regression is visible).
- **AC-4** — per option, CARD-062's ±1 retry and CARD-064's move/skip act
  independently: one option can be skipped while another generates from the
  same picture, and the results say which size was skipped.
- **AC-5** — at most one option per mode; adding a duplicate mode is
  refused or replaces the existing one (state which); the UI cannot exceed
  three options.
- **AC-6** — the batch's recorded sizes and the generated count match what
  was actually produced, with more puzzles than pictures.
- **AC-7** — names never collide for one picture: two options give two
  distinct names, and a typed name is kept (with the size still
  distinguishing them).

## Guardrails

- G-1: The sizing rules themselves do not change. `size_fit()`,
  `MIN_KEPT_SHARE`, `SIZE_PRESETS`, `derive_extent` and the retry stay as
  they are; this card changes how many of them run per picture.
- G-2: A picture with one option is byte-identical in behaviour to today
  (AC-3) — this is the regression risk that matters.
- G-3: Do not delete or weaken the existing single-size tests; update them
  with replacements.
- G-4: Admin-only; no edits under `sourcing/`, `orchestrator.py`, `cli.py`
  or the web adapter.
