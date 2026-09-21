# CARD-105: Check the two metadata algorithms actually agree, by running both

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/105-metadata-parity-by-execution
**Worktree:** —
**Source:** CARD-034's AC-137, which cannot be checked as written; deferred there
**Idea:** —
**Wave:** 1
**Depends on:** —
**Touches:** tests/test_web_metadata.py, possibly src/nonogram/web/static/metadata.js (a way to reach its functions)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

CARD-034's **AC-137** says the client-side and server-side metadata
calculations are identical for the same image. Nothing checks that. What
`TestAlgorithmParity` does is exercise the **Python** implementation —
`gcd`, `simplifyRatio`, the decimal rounding, the suggestion bounds — and then
grep the JavaScript for function names. Two implementations of one algorithm
are kept in step by review, which is the arrangement every other drift in this
repository has started from.

The numbers matter: `suggest_dimensions` and `suggestDimensions` both
brute-force every `(w, h)` in 10..30, sort by relative ratio error and take
three. Two sorts over 441 candidates agreeing on the top three is exactly the
sort of claim that is true until a tie-break changes.

## What makes this newly worth doing

CARD-034's re-cut said no JS engine is available and none can be, because
ADR-0006's baseline is stdlib + Pillow + NumPy. **That was wrong**, and the
correction is the reason for this card: `test_metadata_js_has_no_syntax_errors`
already shells out to `node --check` and **skips** when node is absent. An
opportunistic tool costs the baseline nothing — nothing requires it to be
there — so the same pattern can run the algorithm, not merely parse it.

## The obstacle, and the choice it forces

`metadata.js` is an IIFE. Its functions are closed over, and it reads
`document.currentScript` and `document.readyState` as it loads, so it cannot
simply be `require`d. Two ways out, and the card should pick one and say why:

- **(a) An export hook in the script.** Three lines at the end of the IIFE —
  `if (typeof module !== "undefined") module.exports = {gcd, simplifyRatio,
  suggestDimensions};` — plus guarding the two `document` reads so loading
  outside a browser does not throw. Honest and small, but it is production code
  carrying a seam that exists only for tests.
- **(b) A harness that evaluates it with a stubbed `document`.** No production
  change, but it has to reach inside the IIFE, which means either transforming
  the source or duplicating the functions — and a test that copies the code it
  is testing proves nothing.

**(a) is recommended.** A named export is a smaller lie than a test that
reconstructs its subject, and the `typeof module` guard is inert in a browser.

## Acceptance criteria

- **AC-1** — for a corpus of aspect ratios (including 1:1, 4:3, 16:9, 3:4 and
  at least one extreme), the JavaScript's three suggestions equal the Python's,
  in order.
- **AC-2** — the comparison covers the tie-break, not only the winner: a ratio
  where several `(w, h)` share a ratio error must agree on which comes first.
- **AC-3** — the test skips, and says why, when node is unavailable; it never
  fails for node's absence, and never silently passes either.
- **AC-4** — if the two disagree, the failure names the ratio and both lists,
  so the report is the bug report.

## Guardrails

- G-1: node stays undeclared. It is not added to `pyproject.toml`, not
  required by CI, and its absence skips rather than fails (ADR-0006's baseline
  is unchanged — that is the whole point of the opportunistic pattern).
- G-2: Do not change either algorithm to make them agree. A disagreement is a
  finding to report; which one is right is a separate decision.
- G-3: The test must not contain a third copy of the algorithm.
- G-4: Commit only your own files — explicit pathspecs.

## Architecture context

- **FR:** FR-017 (web UI)
- **ADR:** ADR-0006 (the baseline this deliberately does not touch)
- **Components:** COMP-008
- **Trace:** none
