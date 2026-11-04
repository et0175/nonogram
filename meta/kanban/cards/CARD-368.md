# CARD-368: Nothing guards the agreement of a card's estimate across its three copies — the board claimed CARD-363 did, and CARD-363 declines the surface

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-363's cycle-1 review, 2026-11-04, item 2 of its new-work list. It read `board.md`'s wave-75 close against the module it was reviewing and found the board asserting a guarantee the module explicitly refuses to make.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** CARD-363
**Touches:** tests/test_kanban_review_record.py, meta/kanban/board.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The measured gap

A card's `Estimate` is written in **three** places that can drift independently: the card file
(the authority), `board.md`'s wave-open header, and `dispatcher.state`'s wave entry.

CARD-337 drifted exactly this way. Its estimate was re-cut 2c → 1c at its re-scope (`38020145`),
the card file carried 1c throughout, and `board.md`'s header still said 2c — so a retrospective
reading the board rather than the card would have computed a ratio of **0.500** for a card priced
and delivered at **one** cycle. It was found **by hand** at CARD-337's merge gate, while that gate
was deriving its own `Actual:`.

**The board then claimed this was caught by design.** Its wave-75 close read:

> CARD-363 guards the agreement of exactly these two inputs and this is the disagreement it exists to catch

**CARD-363 does not.** Its module explicitly declines that surface and says so in its own text —
the disclosure is exemplary; the board line was the thing that went stale. The claim is now
**retracted in `board.md`** under ADR-0039/R4, which is what cut this card.

So the position is: the drift is **real and has happened once**, the detection was **manual**, and
**nothing on the board will catch the next one.**

## Acceptance criteria

- **AC-1** — A test derives each in-flight card's `Estimate` from all three sites that carry it and
  fails on disagreement. The card file is the authority; the other two are compared against it.
- **AC-2** — The guard's set of sites is **derived, not listed** (ADR-0039/R2), defaulting to deny:
  a fourth copy appearing in a new artefact must be caught, not silently skipped.
- **AC-3** — A plant proves the guard can fail: restore `board.md`'s 2c-against-1c disagreement for
  CARD-337 and assert the named red, then restore from captured content.
- **AC-4** — The guard must not red on an ordinary correct closure. State which of its assertions are
  floors and which are closure-invariant equalities, with the reason for each — this is CARD-363's
  F-001 and it is the defect most likely to recur here.
- **AC-5** — Run with `-rEfs` and assert `0 skipped` on the impact-scoped baseline.

## Worktree notes

(none yet)
