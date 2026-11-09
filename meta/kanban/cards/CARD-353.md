# CARD-353: Nothing asserts that `frame_centre_of` reduces a bitmap to a mask — the new oracle is held by one of the two guards that hold the old one

**Status:** skipped
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c (0.25d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Finding 8 of CARD-336's review cycle 1, 2026-11-04. The reviewer confirmed it by plant: plant (c1) reds `test_neither_oracle_imports_the_content_stream_reader` and leaves `test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask` GREEN. Correctly out of CARD-336's scope — its AC-2 forbids modifying that guard class — which is exactly why it needs an owner rather than a note.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-336
**Touches:** tests/test_book_pdf.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 board triage. No work is owed here.
**Started:** —
**Closed:** 2026-11-09
**Actual:** none — retired (see the closing note).
**Merge commit:** —
**Blocked by:** —

## The hole, confirmed by plant rather than by reading

Two guards protect the independent pixel oracles that ADR-0042/R6 exempts from the conversion:

| guard | what it holds | covers `frame_centre_of`? |
|---|---|---|
| `test_neither_oracle_imports_the_content_stream_reader` | `page_ink.py` **as a module** | **yes** — reds under plant (c1) |
| `test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask` | an **enumerated list**: `("tests/helpers/page_ink.py", "drawing_of")` and `("two_up_ink.py", "split_row")` | **no** — stays green under plant (c1) |

So CARD-336's new reader is covered by the module-level import guard and **not** by the one that
asserts a measuring function actually reduces a bitmap to a mask. Nothing says `frame_centre_of`
reads pixels at all.

**This matters because of what that oracle is for.** CLAUDE.md requires the independent pixel
oracles as a cross-check against the solver/renderer, and ADR-0042/R6 exempts them **by name**.
An oracle that stopped reducing a bitmap — that started reading a coordinate, say — would
satisfy the import guard perfectly while destroying the cross-check it exists to provide.

**Re-derive the enumerated list and the plant result.** Both are dated readings, and the list
is the thing this card changes.

## What to implement

1. **Derive the list instead of enumerating it.** The second guard hard-codes two
   `(path, name)` pairs. ADR-0039/R2 wants that set derived from an authority the runtime can
   enumerate — the public surface of the oracle helpers — so a **third** oracle added later is
   covered without anyone remembering. Measure whether that derivation is cheap; **if it is not,
   say so with the measurement and add the one pair**, which is the honest smaller fix.
2. **Either way, prove the new cell can fail.** Plant a `frame_centre_of` that returns a
   coordinate without touching pixels and show the guard reds.
3. **Do not weaken the first guard.** Both must still red under CARD-336's plant (c1) and
   (c2) respectively — the reviewer measured that neither covers the other's half, and that
   division is load-bearing.

## Acceptance criteria

- **AC-1** *Given* `test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask`, *then* it
  covers `frame_centre_of`, and a plant that makes that function stop reducing a bitmap **reds**
  it (ADR-0039/R1). Both states demonstrated.
  (test: `test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask`)
- **AC-2** *Given* the guard's set of measuring functions, *then* it is **derived** from the
  oracle helpers' public surface rather than hand-listed — or the card states the measured
  reason it cannot be, and names what a future third oracle would need (ADR-0039/R2).
  (test: named by the implementation; state it)
- **AC-3** *Given* `test_neither_oracle_imports_the_content_stream_reader`, *then* it is
  unchanged in effect and still reds under a plant that makes `page_ink.py` reach the
  content-stream reader — the two guards' division of labour survives.
  (test: `test_neither_oracle_imports_the_content_stream_reader`)
- **AC-4** *Given* `TestEdgeOffset_ThePixelOraclesStillReadPixels`, *then* every cell is green
  and the raster oracles still report the first inked line **byte for byte** — ADR-0042/R6
  exempts them by name and CLAUDE.md requires the cross-check.
  (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)

## Guardrails

- **G-1** — No `src/` change.
- **G-2** — Do not convert or modify the raster oracles themselves. This card changes a
  **guard's set**, not the thing guarded. AC-4 is the check.
- **G-3** — Do not remove or relax either existing guard to make the sets tidy. Both red under
  their own plant today; both must after.
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). Never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, and never
  redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed WITHOUT
  (check: `test_the_measuring_functions_still_reduce_a_bitmap_to_a_mask`)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate, not
  hand-written (check: review-lens)
- ADR-0042/R6 — the independent pixel oracles are exempt from the conversion by name
  (check: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)

## RETIRED 2026-11-09 — board triage

Both guards it names were deleted in the 2026-11-09 curation (6369f1ab); `frame_centre_of` has no caller left (noted on CARD-344 for removal).
