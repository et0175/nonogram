# CARD-376: dog_in_house.py emits SyntaxWarning: invalid escape sequence on any ast walk of src/ — harmless today, an error in a future Python

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
**Source:** Noticed by CARD-349's round, 2026-11-04, while walking `src/` with `ast` to derive the indirectly-exposed set. Pre-existing and unrelated to that card; reported rather than absorbed.
**Idea:** —
**Wave:** —
**Created wave:** 78
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/sourcing/templates/dog_in_house.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
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
