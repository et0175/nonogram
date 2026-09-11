# Changelog

## 2026-09-11
- CARD-045 (bugfix): Fixed `predict_size()` crashing the entire batch-preview/generate-puzzles page with an uncaught `ValueError` when a batch contained an image with degenerate `(0, 0)` dimensions.
