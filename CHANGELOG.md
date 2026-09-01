# Changelog

## 2026-08-31
- CARD-026 (feature): Uploaded images are now fitted to the requested grid's shape — the largest centred crop with the grid's aspect ratio is taken and resized, instead of always cropping to a square. A request whose picture and grid differ in shape by more than 2x (keeping under half the picture) is refused with an explanatory error rather than silently cropped.

## 2026-08-30
- CARD-019 (enabler): Added a local web UI server — `nonogram serve` starts a loopback-only page exposing the same generation options as the CLI. No authentication; the 127.0.0.1 bind is the access control.
