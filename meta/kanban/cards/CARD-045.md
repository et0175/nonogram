# CARD-045: predict_size() can crash a whole batch page on a degenerate image

**Status:** done
**Priority:** P1
**Category:** bugfix
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/045-predict-size-uncaught-value-error
**Worktree:** —
**Source:** meta/review/20260910T164426Z.yml#F-001,F-002,F-003
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py, tests/test_image_batch_size_fix.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-11T00:00:00Z
**Closed:** 2026-09-11T09:00:00Z
**Actual:** 1.1d
**Merge commit:** 2fc8094
**Blocked by:** —

## What to implement

`ImageFile.predict_size()` (`src/nonogram/admin/image_manager.py:68-121`, landed in
`ec18fb4`) calls `derive_extent(stated, None, src_width, src_height)` and catches
`SizeTooSmallForSource` and `NonogramError`, but `derive_extent` →
`_checked_extents` can also raise a plain `ValueError` (not a `NonogramError`
subclass) when the source shape has a non-positive axis. `src_width`/`src_height`
come from `_source_shape()` (lines 42-65), which falls back to `self.dimensions`
on any exception — and `self.dimensions` can genuinely be `(0, 0)`: `add_image()`
(lines 240-246) defaults it to `(0, 0)` and only overwrites it inside a bare
`except Exception: pass` around a second, independent `PILImage.open()` on the
copied temp file. If that second open fails (distinct from the upload-time
validation open, which already succeeded once), the image is still stored as
"successfully added" with `dimensions=(0, 0)`.

When that happens, `_source_shape()`'s own fallback also lands on `(0, 0)`, and
`derive_extent(stated, None, 0, 0)` raises an uncaught `ValueError`. This
propagates out of `predict_size()` into two **unprotected** `render_template()`
calls that loop over every image in the batch with no try/except around the
render:
- `app.py:289-292` (`preview_batch_images` GET — the page users land on right
  after upload)
- `app.py:307-310` (`generate_batch_puzzles` GET confirmation page)

One degenerate image in a batch of up to 200 would 500 the *entire* preview
page, not just the broken image. (The actual generation POST loop at
`app.py:332-373` already has a per-image `try/except Exception`, so it is not at
risk — this is specifically the two GET render paths.)

Separately: the `except NonogramError: return (stated, stated)` branch at line
120 is dead code and gives false confidence this case is handled. `stated` is
always pre-clamped into `[MIN_SIZE, MAX_SIZE]` at line 106 before the
`derive_extent` call, so `validate_extent(stated, stated)` inside `derive_extent`
can never raise, and the only other `NonogramError` subclass `derive_extent` can
raise (`SizeTooSmallForSource`) is already caught by the preceding `except`
clause — so this branch can never execute.

1. Add `ValueError` to the exception handling around the `derive_extent` call at
   `image_manager.py:109` (either an explicit `except ValueError:` returning a
   safe fallback like `(MIN_SIZE, MIN_SIZE)`, or validate `src_width > 0 and
   src_height > 0` in `_source_shape()` itself before returning, falling back to
   a safe minimum rather than propagating a bad shape onward).
2. Remove or repurpose the dead `except NonogramError` branch at line 120 so it
   actually covers a reachable case (or delete it if the `ValueError` fix above
   makes it redundant).
3. Add a regression test constructing an `ImageFile` with `dimensions=(0, 0)`
   (or an image whose second `PILImage.open()` can be made to fail) and asserting
   `predict_size()` returns a safe fallback tuple instead of raising.

## Acceptance criteria

- **AC-1** — given an `ImageFile` whose `dimensions` is `(0, 0)` (the documented
  reachable state from `add_image`'s silent second-decode failure), when
  `predict_size()` is called, then it returns a valid `(width, height)` tuple in
  `[MIN_SIZE, MAX_SIZE]` on both sides instead of raising `ValueError`.
  *test:* to be named by the implementer, in `tests/test_image_batch_size_fix.py`.
- **AC-2** — given the same degenerate image is included in a batch, when
  `GET /batch/preview-images` or `GET /batch/generate-puzzles` is requested, then
  the page renders successfully (200) for the whole batch, not just a 500.
  *test:* to be named by the implementer (Flask test client).
- **AC-3** — the `except NonogramError` branch at `image_manager.py:120` is
  either removed or demonstrably reachable (not dead code) after the fix.

## Guardrails

- G-1: Do not change `predict_size()`'s return contract for any already-working
  image (a real, positive-dimension picture) — this card only closes the
  degenerate-input gap, it must not touch the ink-bbox / `derive_extent` logic
  that CARD ec18fb4 just fixed.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. (check: test, ref TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair, never a scalar. (check: review-lens)

## Worktree notes

[Env] forge 2026.8.17 (no forge.min_version declared in .skills.yml — no comparison performed)
[System contract] assembled fresh via system_rules.py --scope 'src/nonogram/admin/**' (card had no section — added: ADR-0006/R1, ADR-0022/R1)
[Build gate] PASSED (full — python-pro has no testmon installed, no impact narrowing available; 40 pre-existing failures, identical set to a same-run baseline on main modulo known flakiness; none in fix_scope)
[Scope] src/nonogram/admin/image_manager.py, tests/test_image_batch_size_fix.py

--- Implementation agent notes (pulled from worktree) ---

Implemented the fix exactly as scoped, no files outside
`src/nonogram/admin/image_manager.py` and `tests/test_image_batch_size_fix.py`
touched.

**`src/nonogram/admin/image_manager.py`** (`predict_size()`, ~line 95-127):
- Added `except ValueError:` after the existing `except SizeTooSmallForSource:`
  clause around the `derive_extent(stated, None, src_width, src_height)` call,
  returning `(MIN_SIZE, MIN_SIZE)` — a safe fallback square, both sides
  trivially inside `[MIN_SIZE, MAX_SIZE]`. This is the plain `ValueError`
  `derive_extent` raises (not a `NonogramError` subclass) when
  `_source_shape()` reports a non-positive axis, e.g. the documented `(0, 0)`
  fallback from `add_image`'s silent second-decode failure.
- Removed the dead `except NonogramError: return (stated, stated)` branch
  (was unreachable per the card's own analysis: `stated` is pre-clamped
  before `derive_extent` runs, so `validate_extent(stated, stated)` can never
  raise, and the only other `NonogramError` subclass `derive_extent` can
  raise, `SizeTooSmallForSource`, is already caught by the preceding clause).
  Adjusted the `from nonogram.errors import ...` line accordingly (only
  `SizeTooSmallForSource` is still needed).
- Nothing else in `predict_size()`, `_source_shape()`, or `derive_extent`
  changed — the ink-bbox / aspect-fit logic for real, positive-dimension
  images is untouched (G-1).

**`tests/test_image_batch_size_fix.py`**: added three new test classes:
- `TestPredictSizeDegenerateInput` (AC-1) — `dimensions=(0, 0)` +
  unreadable `file_path`, asserts a safe in-range fallback tuple instead of
  raising; parametrized across all three `size_mode` values. Plus
  `test_predict_size_real_image_unaffected` (G-1 regression pin: a real
  200x100 picture at `size_value=20` still predicts exactly `(20, 10)`).
- `TestPredictSizeNonogramErrorBranchNotDead` (AC-3) — asserts the dead
  branch is gone from the source (`inspect.getsource`), not merely
  unreached.
- `TestBatchPreviewDegenerateImageIntegration` (AC-2) — real Flask test
  client against a batch containing a degenerate image; asserts
  `GET /batch/preview-images` and `GET /batch/generate-puzzles` both return
  200, including a mixed good+degenerate batch.

**Regression verification**: manually confirmed (via `git stash`) both new
integration tests fail pre-fix with the exact predicted
`ValueError: a source's own shape has a positive extent on both axes, got
0x0`, propagating as an uncaught 500 from the Jinja `predict_size()` call —
then pass post-fix.

**Test results**: `tests/test_image_batch_size_fix.py -v` → 17 passed.
`tests/ -k "admin or image"` → same 17 pre-existing failures before/after
(unrelated `pictures/` corpus gap in this worktree).

**AC/Guardrail verification**: AC-1/AC-2/AC-3 and G-1 all met — see test
names above. `.venv` created fresh in the worktree (gitignored, not
committed); `src/nonogram.egg-info/*` incidental changes from `pip install
-e` reverted before committing, to keep the commit scoped to the two
intended files.

[Review 1/3] Score: 9.0 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T073855Z-CARD-045-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): AC-1/AC-2/AC-3 and G-1 all independently
re-verified against the code (not just trusted from the implementation
agent's self-report). Both system-contract rules (ADR-0006/R1, ADR-0022/R1)
✓ holds. 1 Minor note (the `except ValueError` clause is broader than
strictly necessary, though traced and confirmed safe — not required to fix).
2 Out-of-scope notes (app.py's render loops remain structurally unprotected
against a future failure mode — candidate follow-up card; a pre-existing
unrelated `reportlab` dependency-baseline test failure). Risk: LOW, lane:
FAST. Zero Critical/Important — severity gate open, score 9.0 ≥ min_score 8.

[8h spot-check] 1/2 sampled holds reproduced (ADR-0022/R1); ADR-0006/R1 ✗ not
reproduced — its named check (TestDependencyBaseline_IsExactlyPillowAndNumpy)
fails on this worktree/on `main` independent of this diff: `reportlab>=4.0`
is already in `pyproject.toml` on `main` (commit 5d5eda8), so the "exactly
Pillow + NumPy" assertion the test makes cannot pass regardless of what this
card does — confirmed by an independent skeptic subagent, matching the
reviewer's own Out-of-scope note verbatim. `pyproject.toml` and
`tests/test_export_pdf.py` are outside this card's Touches/scope, so no
number of further review cycles on CARD-045 can make this check pass — the
defect is in ADR-0006/R1's own stale declared check (or in the ADR's
statement not being updated when `reportlab` was added), not in this card's
diff. Per the same "unverified is a contract defect, not a code defect"
reasoning the AC/EC gate applies (route to the station that owns the
contract, don't loop the fix agent against an unrelated file), I am treating
this as a structural, pre-existing model/check drift and proceeding to the
AC/EC/G gate rather than forcing a wasted cycle 2 — CARD-045's own diff does
not touch, and cannot fix, ADR-0006/R1's dependency baseline. Filed as
CARD-057 (see meta/kanban/cards/CARD-057.md) to fix the ADR/check drift
itself, separately.

[AC/EC check] All criteria/constraints ✓ (evidence):
AC-1 ✓ demonstrated — evidence: TestPredictSizeDegenerateInput::test_predict_size_zero_dimensions_returns_safe_fallback (+ parametrized size_mode variants) PASSED; reverting image_manager.py to pre-fix content makes all 4 fail with the exact predicted ValueError, confirming the test is non-tautological.
AC-2 ✓ demonstrated — evidence: TestBatchPreviewDegenerateImageIntegration::test_preview_batch_images_get_survives_degenerate_image and ::test_generate_batch_puzzles_get_survives_degenerate_image (real Flask test client) both PASSED, asserting status_code == 200; pre-fix code raises instead.
AC-3 ✓ demonstrated — evidence: TestPredictSizeNonogramErrorBranchNotDead::test_dead_nonogram_error_branch_removed PASSED (inspect.getsource confirms the branch and its now-unused import are gone, not merely unreached); reintroducing the branch makes the test fail as expected.
G-1 ✓ demonstrated — evidence: test_predict_size_real_image_unaffected (200x100 real image, size_value=20 → exactly (20, 10)) PASSED both pre- and post-fix; diff confirmed to touch only the import line and the final except clause — no line inside _source_shape(), the stated/quality_cap computation, derive_extent itself, or the SizeTooSmallForSource retry loop.

All four items independently re-verified by a fresh AC-check agent against
the code (not trusted from any prior self-report or review claim). Gate
passes.

[Docs] tests/README.md checked — scoped to Wave-1 feature tests only, does
not enumerate test_image_batch_size_fix.py, unaffected by this card's
additions; no update needed. src/nonogram/admin/ has no README. Nothing to
change.

[Commit] Implementation was already committed as 2786c7e
(fix(admin): catch ValueError from degenerate derive_extent in predict_size)
during implementation; nothing changed during review/fix/AC-gate (zero fix
cycles needed — cycle 1 passed clean), so 2786c7e stands as the final commit
for this card. Worktree confirmed clean (git status --short: only the
untracked meta/review/ report) before this note was written.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-045`.
