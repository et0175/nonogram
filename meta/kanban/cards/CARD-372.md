# CARD-372: A plant anchor over-fires: calc(var(--player-cell) * 0.6) occurs twice in admin.css under a bare css.replace()

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-348's cycle-1 review, 2026-11-04 — MIN-1, widened from F-1's sweep to every plant anchor in the two live sheets. Non-gating; explicitly not filed by the reviewer, routed here instead.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** CARD-348
**Touches:** tests/test_public_player_maybe.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The defect

CARD-348's F-1 correctly fixed one over-firing plant anchor and swept the obvious siblings
(`28%`, `border-radius: 50%`, `data-state="empty"`). CARD-348's reviewer **widened the sweep to every
plant anchor in the two live sheets — ten, counted by script — and found one still standing.**

`MAYBE_PLANTS`' entry *"the admin cell glyph is drawn half the size"* anchors on
`calc(var(--player-cell) * 0.6)`, which occurs **twice** in `admin.css`: once as `.player-grid`'s
`font-size` and once as the Maybe cell glyph. It is applied with a bare `css.replace()` — **no count,
no `_exactly_once`** — so it rewrites both sites.

**The arm passes today only because the collateral rule is not a compared fact.** That is a property
of the census, not of the plant, and it can change without anyone touching this test.

Pre-existing: this is CARD-339's plant, not CARD-348's. Its three table-siblings already route
through `_exactly_once`, so the fix is to make this one match them.

## Acceptance criteria

- **AC-1** — The anchor is selector-qualified and routed through `_exactly_once`, exactly as its
  three table-siblings are.
- **AC-2** — A plant proves the fix was needed: assert the pre-fix anchor matches **2** occurrences
  and the post-fix anchor matches **1**. Both directions, in the same run.
- **AC-3** — Re-run the ten-anchor census the reviewer scripted rather than trusting its count, and
  state the figure derived rather than carried. If more than one anchor over-fires, fix all of them
  or declare each residue with its reason (ADR-0039/R3).
- **AC-4** — No `src/` change; `admin.css` SHA-256 identical before and after every plant. Run with
  `-rEfs` and assert `0 skipped`.

## Worktree notes

(none yet)
