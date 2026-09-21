# CARD-052: Regression tests for real quality_score/recognizability values

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** green from the start (the behaviour was correct); 4 mutants on the filter, all caught
**Branch:** card/052-quality-metrics-regression-tests
**Worktree:** ../PythonProject4-CARD-052
**Source:** meta/review/20260910T170025Z.yml#F-008
**Idea:** —
**Wave:** —
**Depends on:** CARD-050
**Touches:** tests/test_card_052_quality_filter_discriminates.py (new); none of the three files the card originally named — see the re-cut
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-21
**Closed:** 2026-09-21
**Actual:** 0.25d
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-21 — two of the three landed with CARD-050 itself

Checked against `main` at `be2be14`. This card was written *before* CARD-050
and deliberately deferred to it ("write real-value assertions against
CARD-050's actual implementation instead"). CARD-050 then shipped with tests
that answer two of the three criteria, so what is left is narrower than the
card reads.

**AC-1 — done.** `tests/test_card_050_quality_recognizability.py` asserts that
an image-mode batch stores the *independently measured* value
(`puzzle["quality_score"] == independent.quality_score`, an `int` in 1..100),
and that random mode yields **`None`, not the retired `75`**. That is the
"confirmed-`None` + updated UI" branch this card anticipated, and the test
would indeed have failed before CARD-050.

**AC-2 — done.** `test_ac1a_faithful_and_degraded_conversions_of_same_image_
score_differently` converts one image faithfully and degraded and asserts not
only the direction but a **margin of at least 20 points**, which is stronger
than this card asked for.

**AC-3 — not done, and it is the interesting one.** Nothing anywhere exercises
the "Minimum Quality Score" filter *discriminating*. The only two hits for
`quality_filter` in the suite are `test_create_batch_invalid_quality_filter`,
which checks the parameter is validated, and CARD-050's own test that a random
batch (all `None`) is no longer dropped or crashed by it. **No test puts a
low-scoring and a high-scoring puzzle through the same filter and watches one
survive.**

The filter is a single line —

```python
if quality_score < quality_filter:
    continue
```

— in the image generate loop (`app.py:1426`), and a comparison with nothing
either side of it is exactly the kind of line that inverts without anyone
noticing.

### The motivation paragraph is historical now

The Why below describes the round-tripped assertions in `test_wave1_e2e.py`
that made CARD-050's hardcoded `75` invisible. Those files still exist and
those assertions are still tautological, but they are no longer the *only*
coverage: CARD-050's file is the real-value test the card asked for. Left as
written, because it records why this card was opened.

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

### Delivered 2026-09-21

**AC-3 only.** AC-1 and AC-2 landed with CARD-050 itself, as recorded in the
re-cut above; writing them again would have been duplication dressed as
coverage.

`tests/test_card_052_quality_filter_discriminates.py`, 3 tests, driving the
real admin path — upload, generate, read the stored puzzles.

**The threshold is derived from the picture, not guessed.** The first
generation runs unfiltered to learn what `bird1.jpg` actually scores (38 on
this machine), and the assertions bracket that: admitted at `score - 1`,
admitted at exactly `score` (the rule is `<`, so the boundary belongs to the
puzzle), excluded at `score + 1`. A hardcoded threshold would pass wherever the
score happened to fall the convenient side of it, and fail on a machine where
the metric moved.

**One picture, three thresholds** — not two pictures. Two could differ for any
number of reasons; the claim under test is about the *threshold*, so only the
threshold moves.

The two bracketing tests (`quality_filter=0` and `=100`) exist for the
direction of the comparison: an inverted `<` can satisfy any single threshold
that sits the convenient side of the score, and cannot satisfy both ends.

### Why this was worth doing

The filter is one line — `if quality_score < quality_filter: continue` —
with, until now, nothing either side of it. Its failure mode is an **empty
batch**, which reads as "none of those pictures were good enough" rather than
as a bug. That is the kind of defect that survives a long time.

**Mutation check — 4 mutants, all caught:** `<` becoming `<=` (the off-by-one,
caught by the exact-score case alone), the comparison inverted, the filter
removed entirely, and the threshold replaced by a constant.

**Full suite: 3,694 passed, 0 failed.**
