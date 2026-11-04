# CARD-369: The upstream cycle counter double-counts a threshold-reached cycle — measured, 50 apparent disagreements collapse to 2 with zero regressions

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-363's cycle-1 review, 2026-11-04, item 1 of its new-work list, which measured the cause of the 50 disagreements the card had only counted. The measurement currently survives **only in a test docstring** in this repository.
**Idea:** —
**Wave:** —
**Created wave:** 76
**Deferred waves:** 0
**Depends on:** CARD-363
**Touches:** meta/kanban/retro.md, meta/architecture/decisions/open.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What was measured

CARD-363 counted **50** `done` cards whose `Review score` text names a cycle that disagrees with
their `[Review N/M]` marker count, and its prose said the two "cannot both be right". Its reviewer
measured the cause, and the cause **inverts** that reading:

- **49 of 50** have a marker count *greater* than the named cycle — never less.
- **48 of the 50 disappear** if you count distinct `[Review N/M]` **ordinals** instead of Score
  **lines**.
- **Zero** of the 50 currently-agreeing cards regress under that change: **50 → 2**
  (CARD-192, CARD-262 remain).
- The mechanism, read off the cards: upstream's sync point writes a Score line at **each of its
  three write sites**, so a cycle that *reaches its threshold* emits **two** lines. CARD-113, 125
  and 151 all carry a visibly duplicated ordinal.
- It is **one bounded era: CARD-113..CARD-192, nothing after.**

**So the cards were never inconsistent. The counting rule was.** No guard in CARD-363 is defective
— it is right to keep counting what the extractor counts, because that is the input it guards.

## Why this is a card and not a fix

The defective counter is `forge_1`'s retrospective skill (`cycles_used` ← "the COUNT of
`[Review N/M] Score:` lines"). **This board has a standing rule never to edit anything under
`/Users/omelnikova/MyProjects/forge_1`.** So the deliverable is a durable, exportable record — not
a patch.

Note the skill already warns against two *other* miscounts (the bare `[Review N/` prefix count, and
reading the last line's `N`). This is a **third**, in the direction it does not warn about, and its
own worked examples are consistent with it: CARD-091's 63 prefix lines / 20 Score lines.

## Acceptance criteria

- **AC-1** — The measurement is recorded where a retrospective will meet it: the figures (50 → 2,
  49-of-50 directional, the CARD-113..CARD-192 era bound), the mechanism, and the named survivors.
- **AC-2** — A decision is surfaced in `open.yml` for the counting rule, since changing it changes
  every historical `accuracy_ratio` this board has exported.
- **AC-3** — The two survivors (CARD-192, CARD-262) are each diagnosed or declared unexplained by
  name. No "probably".
- **AC-4** — Re-derive every figure in AC-1 from the cards rather than copying it from this card or
  from CARD-363's review YAML. A figure carried forward is a carried figure.
- **AC-5** — `forge_1` is not modified. State that it was not.

## Worktree notes

(none yet)
