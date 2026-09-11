# Changelog

## 2026-09-11
- CARD-049 (bugfix): Admin panel's image-mode puzzle generation now routes through the real solver-verified pipeline — every stored image-derived puzzle is guaranteed uniquely solvable, with real difficulty scoring instead of a grid-size-only estimate.
- CARD-045 (bugfix): Fixed `predict_size()` crashing the entire batch-preview/generate-puzzles page with an uncaught `ValueError` when a batch contained an image with degenerate `(0, 0)` dimensions.
