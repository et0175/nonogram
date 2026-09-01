# Changelog

## 2026-09-01
- CARD-032 (feature): A puzzle named in Cyrillic, Greek or accented Latin now prints its name in the PDF header instead of a row of empty boxes — the package ships its own Unicode font (DejaVu Sans) rather than relying on Pillow's ASCII-only default. Installing the tool pulls in nothing new; the font travels inside the package. Names in Chinese, Japanese, Korean, Thai or Devanagari are still unsupported, and Hebrew or Arabic names render but without the joining those scripts need.

## 2026-08-31
- CARD-026 (feature): Uploaded images are now fitted to the requested grid's shape — the largest centred crop with the grid's aspect ratio is taken and resized, instead of always cropping to a square. A request whose picture and grid differ in shape by more than 2x (keeping under half the picture) is refused with an explanatory error rather than silently cropped.
- CARD-025 (feature): Printed cell size is now `min(comfort cap, page fit)` rather than a flat 6.5 mm ceiling — a 10x10 puzzle prints a 9 mm cell instead of the 6.52 mm that every grid from 10x10 through 25x25 used to get. Page fit still wins whenever the two disagree, which from about 20 cells a side is always.
- CARD-023 (feature): Narrowed the supported grid range to 10..30 cells per side, project-wide and for every source mode. The limit is print legibility, not performance: past about 30 the printed cell falls under ~6 mm and stops being comfortable to mark by hand.
- CARD-022 (tech-debt): Repaired the web adapter's claims about itself and the guards cited as evidence for them — four import/behaviour guard loops could pass without executing their bodies and now assert a non-empty subject, and the package docstring no longer describes orchestrator imports and request mapping it does not do. No behaviour change.

## 2026-08-30
- CARD-019 (enabler): Added a local web UI server — `nonogram serve` starts a loopback-only page exposing the same generation options as the CLI. No authentication; the 127.0.0.1 bind is the access control.
