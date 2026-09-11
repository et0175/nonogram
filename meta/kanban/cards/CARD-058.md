# CARD-058: Surface a note when admin silently substitutes the predicted puzzle size

**Status:** review
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/058-predict-size-substitution-note
**Worktree:** ../PythonProject4-CARD-058
**Source:** meta/review/20260911T112249Z-CARD-048-cycle2.yml (out-of-scope observation)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py, src/nonogram/admin/templates/image_preview.html, src/nonogram/admin/templates/generate_batch.html
**Review score:** 8.5 (cycle 1/3)
**Started:** 2026-09-11T15:55:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-048's review (both cycles) surfaced a real, live divergence between
`ADR-0022/R4`'s refusal-and-message clause and admin's actual behavior:
`ImageFile.predict_size()`
(`src/nonogram/admin/image_manager.py:108-119`) hits `SizeTooSmallForSource`
exactly when the CLI would refuse the request and tell the user the smallest
`--size N` that would work unclamped — but instead of refusing, admin
silently searches upward for a workable N and uses that, with no indication
anywhere in the UI that the puzzle was generated at a different size than
requested.

This was deliberately decided as acceptable UX (see conversation on
2026-09-11: the project owner prefers admin's forgiving auto-substitute
behavior over CLI-style hard refusal for this interactive, preview-driven
workflow — refusing would just be a dead-end requiring the user to
resubmit the whole batch form). **This card does not change that
behavior.** It only makes the substitution visible, so a user isn't left
wondering why their requested size and the puzzle's actual predicted size
differ.

1. `ImageFile.predict_size()` (or a thin wrapper/property alongside it)
   should expose whether a substitution happened — e.g. return or make
   available the originally-`stated` N alongside the actually-derived
   `(width, height)`, or a boolean/reason flag, without changing
   `predict_size()`'s existing return contract in a way that breaks its
   current callers (check all call sites first — `to_dict()`,
   `image_preview.html`'s template loop, `generate_batch.html`'s template
   loop, and any others found by a fresh grep for `predict_size(`).
2. In `image_preview.html` (and/or `generate_batch.html`, if it also
   renders a per-image size), add a small, unobtrusive note next to an
   image whose predicted size required substitution — e.g. "Requested N
   was too small for this picture's shape; using N' instead" — visible
   without requiring the user to compare the requested-size field against
   `predicted_width`/`predicted_height` by eye.
3. Do NOT change `SizeTooSmallForSource`'s handling, the CLI's refusal
   behavior, or anything in `sourcing/`, `cli.py`, or `orchestrator.py` —
   this card is admin-UI-only, matching the deliberate CLI/admin behavioral
   split confirmed in the CARD-048 discussion.

## Acceptance criteria

- **AC-1** — given an uploaded image whose ink-bounding-box ratio requires
  `predict_size()`'s `SizeTooSmallForSource` substitution path, when the
  batch preview or generate-confirmation page renders that image, then a
  visible note distinguishes the substituted size from the originally
  requested size.
- **AC-2** — given an uploaded image that does NOT hit the substitution
  path (the common case), when the same pages render, then no note
  appears and the existing display is unchanged (no regression to the
  common case).
- **AC-3** — `predict_size()`'s behavior (the actual `(width, height)` it
  returns) is unchanged for every image — this card only adds visibility,
  it does not change what size gets used.

## Guardrails

- G-1: Do not touch `SizeTooSmallForSource` handling, `cli.py`,
  `orchestrator.py`, or anything under `sourcing/` — the CLI's
  refuse-with-message behavior (ADR-0022/R4) is deliberately different
  from admin's auto-substitute behavior and this card must not blur that
  line in either direction.
- G-2: Do not change `predict_size()`'s returned `(width, height)` value
  for any image — this is a visibility-only card.

## Worktree notes

**Implementation:** refactored `predict_size()`'s `SizeTooSmallForSource`
handling into a shared private `_predict_size_detailed()` helper
returning `((width, height), substitution_info)`. `predict_size()`
itself just unpacks the first element — its signature and return value
for every image are unchanged (G-2). Added a new public
`size_substitution()` method returning `None` for the common case (and
the degenerate `(0, 0)`-dimension `ValueError` fallback, which is a
different failure mode, not a real substitution) or
`{"requested": N, "used": N'}` when the fallback path was taken.
Sharing one implementation between the two public methods was a
deliberate choice — a second, independent reimplementation of the
`SizeTooSmallForSource` logic would risk the exact kind of silent
two-copies-disagree drift CARD-057 found in ADR-0006/R1's own check.

**Templates:** `image_preview.html`'s "Predicted Output" alert now
shows a small warning line when `image.size_substitution()` is
truthy. `generate_batch.html`'s compact summary table (space-
constrained) shows a small "⚠ size adjusted" badge with the full
requested/used explanation in its `title` tooltip instead of inline
text.

**AC-1/AC-2 verified:** 9 new tests in
`tests/test_card_058_predict_size_substitution_note.py` — unit tests
for `size_substitution()` (triggered case, common case, degenerate-
image non-false-positive case) plus Flask-integration tests for both
templates, with and without substitution. Red→green verified via
`git stash`: all 5 substitution-dependent tests fail against the pre-
fix code (`size_substitution()` doesn't exist), the 4 "no note"
negative-case tests correctly stay green either way (proving they're
not tautological). One test-writing wrinkle: the raw HTML source wraps
"too small" across a newline+indentation inside `image_preview.html`'s
multi-line note — fixed by normalizing whitespace before substring-
matching in the test, which is also the more correct check (matches
what a browser actually renders, not incidental template indentation).

**AC-3 verified:** `predict_size()`'s return value is unchanged for
both the substitution case (`(30, 10)` for a 2000x100 image at
`size_value=10`) and the common case (`(20, 20)` for a 500x500 image) —
matches pre-existing test expectations exactly.

**Regression check:** new file + `test_image_batch_size_fix.py` +
`test_wave3_e2e.py` + `test_card_047_eager_source_shape.py` +
`test_admin_image_uniqueness.py` + the structural import guard —
48/48 pass, 4 pre-existing skips. Full suite: 36 failures, all in the
previously documented flaky/corpus-dependent classes, none touching
`image_manager.py` or either changed template.

**Note (unrelated to this card, raised mid-implementation and
deliberately not touched):** the project owner independently found,
while testing this feature, that admin's smallest size preset ("small",
N=10) forces almost every non-square image into a square grid,
discarding real content — because `MIN_SIZE` (10) is both the floor
`derive_extent` applies AND the smallest allowed `N`, so at `N=10` the
derived short side has no room to be anything but 10. Verified against
a real image (`c11.jpg`, 229x149 ink-bbox, 1.54:1): N=10 → forced 10x10
(65% retained), N=20 → genuine 20x13 (~100% retained). This is core
`sourcing/random_grid.py` arithmetic shared by the CLI, not an admin-UI
concern — explicitly out of this card's scope (G-1) and CARD-058's own
`size_substitution()`/note mechanism does not cover it (that mechanism
only fires on the `SizeTooSmallForSource` *refusal* path, not this
*floor* behavior, which succeeds without raising anything). Flagged for
the user to decide direction on separately; not addressed here.

## System contract

- ADR-0022/R4 — "never silently clamped" is contradicted by admin's own scoped behavior (pre-existing, not introduced by this card; flagged by review as an out-of-scope observation — the owner-approved carve-out is recorded only in this card's prose, not in the ADR itself).

[Review 1/3] Score: 8.5 — crit: 0, imp: 0
[Review sync] 1 report(s) → meta/review/ (20260911T132732Z-CARD-058-cycle1.yml)
[Adversarial] no gating findings to verify (0 critical, 0 important)
Cycle 1 summary (forge:review): independently walked all three
predict_size() branches (success, substitution-found, loop-exhausted)
plus the ValueError fallback, confirming byte-identical return values
pre/post-diff by direct code comparison, not trusting the Worktree
notes' claim. Judged the degenerate (0,0)-image "not a substitution"
call as semantically defensible (different exception, different
reason — no real requested-vs-derived comparison exists for a
nonexistent picture) while noting it as a narrower, pre-existing
version of the same visibility gap (out of scope, not a regression).
Confirmed G-1 held via git diff --name-only AND the structural
import-boundary test. Ran all 9 new tests plus the full claimed
regression set (48/48, 4 skips) fresh. Zero Critical/Important; 2
Minor (test_dead_nonogram_error_branch_removed now inspects a 1-line
wrapper rather than the moved logic — cheap to redirect, not required
by this card's Touches; predict_size()/size_substitution() each
independently call the shared helper rather than caching one result
per request — harmless at current scale). One significant out-of-scope
observation: ADR-0022/R4 is now more visibly contradicted by admin's
own scoped behavior than before this card (since the divergence is no
longer silent) — the owner's approval of this UX carve-out lives only
as prose in this kanban card, not in the ADR itself; reviewer
recommends a future forge:architect-adr-writer pass to record it
formally. Risk: LOW, lane: FAST. Score 8.5 ≥ min_score 8, zero
Critical/Important — severity gate OPEN. Cleared on cycle 1 of 3.

[8h spot-check] 2/2 sampled holds reproduced — independently re-ran
the AC-3 branch-comparison tests fresh (2/2 pass) and re-confirmed the
diff touches exactly the 3 declared files + the new test file.

[AC/EC check] All criteria/guardrails ✓ (evidence):
AC-1 ✓ demonstrated — evidence: integration tests confirm the note renders on both pages for a substitution-triggering image, with correct requested/used values.
AC-2 ✓ demonstrated — evidence: integration tests confirm no note renders on either page for a non-substituting image.
AC-3 ✓ demonstrated — evidence: unit tests pin predict_size()'s exact return value for both cases; reviewer's independent branch-by-branch code comparison confirms byte-identical pre/post-diff values.
G-1 ✓ demonstrated — evidence: git diff --name-only shows only the 3 declared files (+ new test file); structural import-boundary guard passes.
G-2 ✓ demonstrated — evidence: same as AC-3.

All five items independently re-verified across implementer, reviewer,
and this gate. Gate passes.

[Docs] No README under src/nonogram/admin/ carries a method-level
inventory needing an update. The ADR-0022/R4 documentation gap
(out-of-scope observation above) is real but explicitly outside this
card's Touches (G-1) — flagged for a future card, not fixed here.

[Commit] Final state is 1 commit on the branch: 7e1c400 (implementation
+ tests). Nothing further needed — cycle 1 cleared cleanly.

CYCLE 1 COMPLETE — SUCCESS. Ready for `/kanban done CARD-058`.
