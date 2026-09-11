# CARD-058: Surface a note when admin silently substitutes the predicted puzzle size

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/058-predict-size-substitution-note
**Worktree:** —
**Source:** meta/review/20260911T112249Z-CARD-048-cycle2.yml (out-of-scope observation)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/image_manager.py, src/nonogram/admin/templates/image_preview.html
**Review score:** —
**Started:** —
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
