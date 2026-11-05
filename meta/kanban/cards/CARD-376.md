# CARD-376: dog_in_house.py emits SyntaxWarning: invalid escape sequence on any ast walk of src/ — harmless today, an error in a future Python

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** general-purpose
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** Noticed by CARD-349's round, 2026-11-04, while walking `src/` with `ast` to derive the indirectly-exposed set. Pre-existing and unrelated to that card; reported rather than absorbed.
**Idea:** —
**Wave:** —
**Created wave:** 78
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/sourcing/templates/dog_in_house.py, tests/test_cli.py
**Review score:** n/a — **RETIRED AS A CARD AND FIXED INLINE** under the owner's cut bar, 2026-11-05. No review cycle was run and none was warranted.
**Started:** —
**Closed:** 2026-11-05
**Actual:** fixed inline, no card cycle. **6** invalid escape sequences escaped in one file (value byte-identical, sha256 `909f22fee09b108e` before and after, 12 backslashes preserved), plus a **2-test** guard class with its own discriminating control in `tests/test_cli.py`. Against the **68-line, five-AC card** this replaced.
**Merge commit:** —
**Blocked by:** —

## The warning

`src/nonogram/sourcing/templates/dog_in_house.py` contains a string literal with `\,`, which is not a
valid escape sequence. Python currently emits:

```
SyntaxWarning: "\," is an invalid escape sequence
```

on any `ast` walk or import of `src/`. It is harmless today — the literal evaluates to `\,` as
intended — but Python has announced this becomes a **`SyntaxError`**, at which point the module stops
importing.

## Why it is worth a card rather than a silent fix

Two reasons, and the second is the real one:

1. It is noise in every tool that walks `src/`, and this board walks `src/` routinely — the structural
   import guard in `tests/test_cli.py`, the layering check, and now CARD-349's exposed-set
   derivation. Noise in a derivation is how a real finding gets missed.
2. **A warning nothing fails on is the shape this board has filed five waves running.** Nothing in
   the suite asserts that `src/` walks cleanly, so this has sat here accumulating no pressure at all.
   Fixing the literal without adding that assertion leaves the next one equally invisible.

## Acceptance criteria

- **AC-1** — The literal is corrected so the intended string is unchanged. Assert the **value**, not
  the source text.
- **AC-2** — A test fails if **any** module under `src/` emits a `SyntaxWarning` on compilation. The
  set of modules is derived by walking the tree, not listed (ADR-0039/R2).
- **AC-3** — A plant proves AC-2 can fail: reintroduce an invalid escape in a different module and
  assert the named red; restore from captured content.
- **AC-4** — Check whether other invalid escapes exist before claiming this is the only one. Report
  the count derived, not assumed — and if there are more, fix all or declare the residue with its
  reason (ADR-0039/R3).
- **AC-5** — Decide whether the guard should cover `DeprecationWarning` too, and give the reason. It
  probably should not: that is a much larger set with third-party noise in it, and a guard that must
  be suppressed to pass is worse than none.

## Worktree notes

(none yet)

## Retired and fixed inline — and the card contained the check I skipped

**This card is the owner's proof case for the cut bar**, and retiring it is the point. It was a
68-line card with five acceptance criteria for what I described to the owner as "a one-character
fix". Both halves of that were wrong, in opposite directions.

**The card was too big.** The fix is six escaped characters and a two-test guard. No decision was
needed, nothing was blocked, and the diff is smaller than the card describing it.

**And my "one character" was too small.** I claimed a single `r` prefix. Measured:

- a raw-string prefix would have been **wrong** — lines 7–11 carry `\\,`, which currently evaluates
  to a *single* backslash, so `r'''` would have doubled them and **changed the rendered art**;
- the file held **six** invalid escapes across **four** kinds (`\)` ×2, `\_` ×2, `\-`, `\|`), not one.

**I found the second one only because the first fix did not silence the warning** — Python reports
these as it encounters them, and my census had counted *modules emitting a warning* while I read it
as *invalid escapes*. That is the exhaustiveness failure recorded in the board's brief rules the same
night: **I confirmed the member, not the complement.**

**The sharp part: this card's own AC-4 was the check I skipped.** It read *"check whether other
invalid escapes exist before claiming this is the only one — report the count derived, not
assumed."* The card I was retiring as over-ceremony contained the one instruction that would have
caught me. That is a real argument **for** writing ACs, and it belongs on the record next to the
argument against writing this card.

**The honest reading of both:** the ACs were worth thinking, and the card was not worth filing. The
cut bar is right that a finding whose fix is smaller than its card gets fixed inline — and the
discipline the card would have imposed has to come with it, not be dropped along with the paperwork.

## What landed

- **The fix**, value-preserving and proven so: ART's sha256 is `909f22fee09b108e` before and after,
  321 characters, 12 backslashes in the value both ends. Six source sequences changed, zero value
  change.
- **The guard** (this card's AC-2), in `tests/test_cli.py`'s structural-guard home per CLAUDE.md:
  `TestSourceHygiene_NoModuleUnderSrcCompilesWithAWarning`. The module set is **walked, not listed**
  (ADR-0039/R2), with a `>= 20` floor so it cannot pass by finding nothing, and a control
  (AC-3) that plants an invalid escape and asserts the guard fires, plus a matched clean case so it
  discriminates.
- **AC-4 satisfied properly**: zero invalid escapes remain in that file and **zero SyntaxWarnings
  across all of `src/`**, both re-derived after the fix.
- **AC-5 answered as the card proposed**: the guard is scoped to `SyntaxWarning` only.
  `DeprecationWarning` is a larger set carrying third-party noise, and a guard that must be
  suppressed to pass is worse than none.
