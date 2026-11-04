# CARD-373: AC-4's six-pair contrast table is durable only inside a failure message, which a green run never prints

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-348's cycle-1 review, 2026-11-04 — MIN-3. Non-gating; explicitly not filed by the reviewer, routed here instead.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** CARD-348
**Touches:** tests/test_public_player_agreement.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The gap

CARD-348's AC-4 asked for the contrast figures to be **recorded**. Four of the six are not durable
anywhere a later reader will find them:

- the commit message carries 6.144, 1.190 and the three-by-paper / three-by-marks statement
- `~/Documents/nonogram-reviews/CARD-348/computed.txt` carries the computed colours but **no ratios**
- **the six-pair table exists only inside a failure message** — so a green run never prints it, and
  the figures vanish the moment the test passes

CARD-348's review YAML carries them in the meantime, and that YAML is gitignored.

An AC that says "recorded" is satisfied by a value a reader can retrieve without re-running the
suite and without reading a diff. This one is not.

## Acceptance criteria

- **AC-1** — The six pairs and their ratios (15.444 / 13.209 / 12.978 / 1.190 / 1.169 / 1.018, plus
  dot-on-White-paper 6.144) are appended to
  `~/Documents/nonogram-reviews/CARD-348/computed.txt`, which guardrail G-4 already makes gate
  evidence.
- **AC-2** — The figures are **re-derived** from `tokens.css` when written, not copied from this
  card, CARD-348, or its review YAML. A figure carried forward is a carried figure.
- **AC-3** — State whether a green run should emit them at all. It probably should not — a passing
  test printing six numbers is noise, and the durable record belongs in the artefact — but say so
  deliberately rather than by omission.
- **AC-4** — No `src/` change.

## Worktree notes

(none yet)
