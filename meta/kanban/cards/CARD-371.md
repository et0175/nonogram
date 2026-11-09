# CARD-371: The new WCAG contrast helper has no reference anchor — a formula error would move all six figures together and pass

**Status:** skipped
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-348's cycle-1 review, 2026-11-04 — IMP-2. Non-gating; explicitly not filed by the reviewer, routed here instead.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** CARD-348
**Touches:** tests/test_public_player_agreement.py, tests/test_puzzle_solver_maybe.py, tests/test_puzzle_solver_probe.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 tech-debt triage. No work is owed here.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The gap

`relative_luminance` and `contrast_ratio` are both new in
`tests/test_public_player_agreement.py` (present only on the `+` side of CARD-348's diff), used in
exactly one arm, and consumed only through `>= 3.0` thresholds. **Nothing in the tree pins either to
a known value.** A formula error would move all six contrast figures together, and because the arm
only ever compares against a threshold, it could silently pass *or* silently fail the floor.

**Mitigated in fact, not by the tree.** CARD-348's reviewer wrote an independent WCAG 2.1
implementation under `python -I` with no import of the module and got agreement to the last digit:
15.444 / 13.209 / 12.978 / 1.190 / 1.169 / 1.018, with dot-on-White-paper 6.144. That is evidence
about today's code, not a control that will fire tomorrow.

**It is the third unanchored copy.** `tests/test_puzzle_solver_maybe.py`'s `_contrast` and
`tests/test_puzzle_solver_probe.py` already carry their own, equally unpinned.

This is CLAUDE.md's own test-style rule — *prefer an independent second implementation over
re-deriving a value with the same function you're testing* — applied to the helper rather than to
the thing it measures.

## Acceptance criteria

- **AC-1** — Each copy is pinned to values computable by hand from the WCAG 2.1 definition:
  `contrast_ratio("#000000", "#ffffff") == 21.0`, `relative_luminance("#ffffff") == 1.0`,
  `relative_luminance("#000000") == 0.0`. Exact equality, not a threshold.
- **AC-2** — A plant proves the anchor can fail: perturb a coefficient in the sRGB linearisation and
  assert the named red. Plant by text with the occurrence count asserted `== 1`, SHA-256 both ends,
  restore from captured content.
- **AC-3** — Decide, and state the reason, whether the three copies should converge on one shared
  helper. **They probably should not**: CLAUDE.md's layering rule has capability modules reimplement
  rather than import laterally, and the precedent is `solver/propagate.py`'s `mask_runs`. Anchor each
  copy independently instead of creating a shared dependency — but say so deliberately.
- **AC-4** — No `src/` change. Run with `-rEfs` and assert `0 skipped` on the impact-scoped baseline.

## Worktree notes

(none yet)

## RETIRED 2026-11-09 — tech-debt triage

Its target, the old public-player test modules, was deleted when CARD-399 retired play.js (87766ed4).
