# CARD-257: Cut the guard's prose to what its 22 lines actually claim

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Complexity:** trivial
**Estimate:** 0.25d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-254 review cycle 3's closing answer — "the mechanism: yes, emphatically. The prose around it: no — and here is what I'd cut."
**Idea:** —
**Wave:** 50 (queued)
**Depends on:** CARD-254 (merged `9e8aad6d`)
**Touches:** tests/test_db_engine_lifecycle.py, src/nonogram/db/session.py (docstring only)
**Review score:** —
**Started:** — · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — the arithmetic, which is the whole case

CARD-254 set out to retire ~400 lines and keep ~55. Measured at its merge:

```
tests/test_db_engine_lifecycle.py  1415 → 919 → 1062 → 1177
src/nonogram/db/session.py          327 → 368 →  376 →  384
                                   base  shrink  cyc1   cyc2
```

**The shrink removed 496 lines; the two review cycles put 258 back — 52 %** — as controls and as
prose *about* controls. Net **−181 (−10.4 %)**. The part that catches things is **~22 executable
lines**: two regexes, a 6-line counter, a 6-entry dict, a 14-line tree-wide equality. Prose to
mechanism in what survives is **1.69 : 1**, and `reset_engine()`'s docstring is **126 lines for a
6-line body — 21 : 1**.

Nothing here is wrong. That is what makes it worth a card: every one of those lines was added to
satisfy a legitimate finding, and the sum is still a file nobody will read.

## What to cut — three cuts, ~135 lines, no measured property lost

1. **Single-source the convention (~100 lines).** It is currently written twice "in the same words" —
   the guard class's docstring and `reset_engine()`'s. Keep `reset_engine()`'s (it is what a
   maintainer of the production module opens) and replace the class's copy with a cross-reference
   plus its `Controls:` list. **This is the cut that retires a rule with no control**: *"the same
   words in two places" is itself a claim, and nothing reds if they drift* — a doubling already paid
   three times (cycle 1 edited both, cycle 2 edited both, and two of cycle 3's Minors live in text
   that would need correcting in both).
2. **Delete control A's arm 2 (~10 lines, zero coverage).** It is a strict duplicate of arm 1's
   `setattr` iteration: the two probes differ only in the probe *function's name*, which a text scan
   cannot see. Measured: identical `Counter` under every mutant, and **no mutant kills one without
   the other**.
3. **Stop narrating review history in shipped docstrings (~25 lines).** Both of cycle 3's prose
   Minors are wrong about *cycles*, not about the mechanism — "those comparisons were true for every
   possible probe value" (one of them reds under SETATTR-DEL) and "two generations of this control"
   (there was one; two of the **family**). The mutant-per-arm table belongs on the card; a docstring
   needs the property and the mutant that reds it. This closes the surface where this family kept
   reappearing — **three cycles running, and in cycle 3 it shipped inside the code rather than on the
   card.**

**Also fix while there** (cycle 3's remaining Minor): arm 2b's position assertion lacks the
two-`setattr(` precondition. `rindex` returns the *last* occurrence, so on a one-call probe the
assertion is trivially green. It discriminates today — the probe has two, at offsets 49 and 122 — but
the same file asserts every other probe precondition explicitly.

## Acceptance criteria

- **AC-1** *Given* the single-sourced convention, *then* the blind-to list, the counting rule and the
  bound appear **once**, and the other site carries a pointer. No sentence is lost: diff the two
  copies before cutting and show every clause survives somewhere.
- **AC-2** (the control that replaces the duplication rule) *Given* the convention text, *then* a
  test holds that the production docstring and the guard agree on the **mechanism's own parameters**
  — the three global names and the two spellings — derived from the code rather than quoted. The old
  rule relied on two humans editing in step; this one reds.
- **AC-3** *Given* arm 2's deletion, *then* the per-assert kill matrix is unchanged for every
  remaining arm, measured with the line-count-preserving instrument CARD-254's cycle 3 used.
- **AC-4** *Given* arm 2b, *then* its probe's two-`setattr(` precondition is asserted, as the file's
  other probes assert theirs.
- **AC-5** (guard) *Given* all cuts, *then* the tree sweep is unchanged — **9 sites, 6 pairs,
  dict-equal, zero matches elsewhere** — and `session.py`'s docstring-stripped AST still hashes to
  `bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c`.

## Guardrails

- G-1: **No mechanism change.** The two regexes, the counter, the dict and the equality are untouched;
  this card moves and deletes prose and one duplicate arm.
- G-2: No test retired without a named survivor; arm 2's survivor is arm 1 and the measurement above
  is the evidence.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated.
- G-4: No new runtime dependency.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This card deletes prose that was each added to close a real finding. The failure mode
  is cutting a sentence that is the *only* statement of a bound — the blind-to list especially, which
  is the card's declared limit and not decoration. Diff before and after and show every clause
  survives somewhere, which is what AC-1 is for.
- **[The second trap]** Do not replace the duplication rule with a *new* claim about the two texts
  agreeing. AC-2 asks for an equality over the mechanism's parameters, derived from the code — not a
  string comparison of two docstrings, which would be the same uncontrolled rule with a test attached.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR
  files **case-insensitively** for the reach-limit idiom — this card is entirely about ADR-0039/R1.
