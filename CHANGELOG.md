# Changelog

## 2026-09-11
- CARD-050 (bugfix): `quality_score`/`recognizability` are now real measurements instead of hardcoded fakes. Image-mode puzzles get them from an actual comparison against the source picture (`nonogram.analysis.quality_metric.measure_quality()`); random-mode puzzles get `None` (there's no source picture to measure fidelity against) instead of an unconditional `75`/`"medium"`. Also fixed a fragile `src.`-prefixed import in `random_generator.py` that was silently hiding a real ADR-0007 lateral-import violation, resolved by natively reimplementing the one function it needed.
- CARD-049 (bugfix): Admin panel's image-mode puzzle generation now routes through the real solver-verified pipeline — every stored image-derived puzzle is guaranteed uniquely solvable, with real difficulty scoring instead of a grid-size-only estimate.
- CARD-045 (bugfix): Fixed `predict_size()` crashing the entire batch-preview/generate-puzzles page with an uncaught `ValueError` when a batch contained an image with degenerate `(0, 0)` dimensions.
