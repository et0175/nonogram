# CARD-052: Regression tests for real quality_score/recognizability values

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/052-quality-metrics-regression-tests
**Worktree:** —
**Source:** meta/review/20260910T170025Z.yml#F-008
**Idea:** —
**Wave:** —
**Depends on:** CARD-050
**Touches:** tests/test_batch_generator.py, tests/test_wave1_e2e.py, tests/integration_tests.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

No test in the suite checks `quality_score`/`recognizability`'s actual *value*
from a real generation call — every existing assertion round-trips a fixture
through storage (`quality_score=sample_puzzle['quality_score']` in
`test_wave1_e2e.py:87,116,147,199,232,264,302`), which is tautological with
respect to whether the production value is real or fake. `test_batch_generator.py`
has no `quality_score`-value assertion at all. `tests/integration_tests.py`
only checks `image_to_grid`'s grid *shape*, never quality/difficulty output.
This is why CARD-050's bug (hardcoded `75`/`"medium"`) shipped undetected, and
why it could recur silently after being fixed.

This card depends on **CARD-050** landing first — writing "assert it's not the
old fake value" tests before the fix exists would just pin the bug (green on
broken behavior); write real-value assertions against CARD-050's actual
implementation instead.

1. Add a test that generates a real puzzle via `orchestrator.generate_batch()`
   (random mode) through `BatchGenerator._generate_random_batch`, and asserts
   `quality_score`/`recognizability` reflect CARD-050's real measurement (or
   confirmed-`None` + updated UI, whichever CARD-050 chose) — not the retired
   hardcoded fallback.
2. Add a test calling the real image-mode generation path (post-CARD-049/050)
   with two different source images — one where the conversion should score
   well (a clean silhouette) and one where it should score poorly (a heavily
   degraded/mismatched conversion, if constructible) — and assert the
   `quality_score`s differ in the expected direction. Use the project's own
   `silhouette/animals/birds/*.jpg` corpus already used elsewhere in the test
   suite (see `tests/integration_tests.py`, `test_derive_shape.py`) rather than
   synthetic solid-color images, since the metric needs real image content to
   discriminate.
3. Add a boundary/negative case: confirm the batch UI's "Minimum Quality Score"
   filter (`app.py:350`) actually excludes a low-scoring puzzle and includes a
   high-scoring one, for whichever mode(s) CARD-050 gave a real metric to.

## Acceptance criteria

- **AC-1** — a test exists asserting `quality_score`/`recognizability` from a
  real `orchestrator`-driven generation are not the pre-CARD-050 hardcoded
  fallback values (`75` / `"medium"`), and this test would have failed before
  CARD-050 landed.
- **AC-2** — a test exists asserting the image-mode quality metric
  discriminates between a faithful and a degraded conversion of comparable
  source images.
- **AC-3** — a test exists exercising the "Minimum Quality Score" filter's
  actual discriminating behavior for whichever mode(s) now have a real metric.

## Engineering constraints

None beyond what's stated above — this card is test-only; if writing these
tests surfaces a gap in CARD-050's implementation, file it as a new finding
rather than silently loosening the test to pass.
