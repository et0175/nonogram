# ADR-0006: Dependency baseline — stdlib + Pillow + NumPy

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

Within the fixed Python-3.14 CLI frame (CON-001: no web/GUI, no network, single local process), the pipeline needs three things stdlib cannot provide on its own: raster image decoding, resize, and Floyd-Steinberg dithering for image-mode sourcing (FR-003); PNG raster rendering for export (FR-011); and dense boolean-matrix manipulation inside the solver's hot loop across the 10x10..50x50 grid range, under the generation-time bounds NFR-001 sets (and ADR-0001 now makes numeric — a 5s p95 cap at <=20x20, a 30s hard timeout up to 50x50).

Python's standard library covers none of the raster work: there is no stdlib PNG/JPEG decoder, no resize, and no dithering primitive. Something outside stdlib has to own image I/O. Separately, the solver's row/column line-logic runs repeatedly over grids as large as 50x50 inside that same time budget, which raises a second, independent question — whether grids should be represented as vectorized arrays or as plain Python structures (the latter deferred to DEC-012, but the dependency choice made here constrains what DEC-012 can pick from).

DEC-006 asks the project to pick one dependency baseline for both concerns at once: "stdlib + Pillow only," "stdlib + Pillow + NumPy," or "stdlib only" (hand-rolled codecs). It is a platform-axis (stack) decision, blocking both synthesis and decompose, and depends on DEC-007 (the internal module-boundary decision) to know where the dependency gets consumed.

## Decision

We adopt **stdlib + Pillow + NumPy** as the dependency baseline: Pillow owns image I/O (open/resize/convert("1") for dithering on the way in, ImageDraw for PNG rendering on the way out), and NumPy is added for grid representation and solver line operations — vectorized boolean-array masks for row/column intersection in the hot loop.

This departs from the recommended default of "stdlib + Pillow only." The default's own analysis is correct as far as it goes — Pillow alone is a smaller, cheaper baseline and NumPy's boolean-array masks are not obviously faster than Python ints-as-bitmasks at line lengths that fit in one machine word (<=50 bits). But the owner is deliberately trading that smaller footprint for headroom at the top of the supported range: NumPy makes the 50x50 upper bound (FR-001, AC-038) comfortably within the ADR-0001 time budget rather than resting on the assumption that pure-Python line logic will be fast enough, and it gives the solver a vectorized path to fall back on if profiling after FR-006 lands shows pure-Python integer bitmasks are not enough. A second heavyweight dependency for a personal tool is a real cost, but it is a cost paid once at install time, not a recurring one, and it is judged acceptable in exchange for not having to revisit this decision under time pressure if the pure-Python path turns out to be the bottleneck at 50x50.

## Alternatives considered

### pillow_only (recommended default — not chosen)

Stdlib + Pillow as the single runtime dependency: Pillow handles image open/resize/convert("1") for FR-003 and its ImageDraw renders the FR-011 PNG export; SVG is hand-written XML text and JSON/CSV use stdlib json/csv; grids stay pure-Python structures. This was the recommended default because one dependency keeps install trivial and audit surface tiny, `Image.convert("1")` gives Floyd-Steinberg dithering as a library call rather than an algorithm to write, and it covers both the image-in and image-out halves of the pipeline with a single library. It was not chosen because it leaves the solver's line-logic entirely pure-Python, which is a real risk against NFR-001's time bound at 50x50 (FR-006) — the owner preferred to buy vectorized headroom now rather than find out during profiling that the pure-Python path needs it anyway.

### stdlib_only

Zero third-party dependencies: hand-roll a minimal PNG encoder/decoder (zlib + struct), the resize, and the dithering. This was rejected outright — writing a correct PNG decoder for arbitrary user-supplied images (FR-003, AC-008's corrupt-file handling) is more work and more risk than the entire solver, it cannot read JPEG or other formats users will realistically hand it, and it reinvents a solved problem (image codecs) with no compensating benefit over either Pillow-based alternative. No aspect of this alternative was preferable to either option that includes Pillow.

## Consequences

### Positive
- Vectorized row/column mask intersection gives the solver hot loop materially faster line operations than pure-Python bitmasks would need to achieve on their own, making the 50x50 upper bound (FR-001, AC-038) comfortable against the ADR-0001 30s timeout rather than marginal.
- Direct, cheap conversion between a NumPy array and a Pillow image keeps the FR-003 (image-in) and FR-011 (image-out) boundary simple even with two libraries in play.
- FR-003's dithering and PNG decode/resize remain a Pillow library call, not a hand-written algorithm — none of NumPy's benefit is bought at the cost of reimplementing image codecs.
- De-risks NFR-001 compliance at the top of the supported grid-size range before any solver profiling exists, rather than betting the time budget on an unmeasured pure-Python assumption.

### Negative
- Second heavyweight (compiled-wheel) dependency for what is otherwise a personal hobby tool, with the install and audit-surface cost that implies.
- NumPy boolean arrays are plausibly SLOWER than Python ints-as-bitmasks at these specific line lengths (<=50 bits fits one machine word) — the performance benefit this decision is buying is not guaranteed until DEC-012 and actual solver profiling confirm it holds in practice.
- Introduces a second mental model for "what is a grid" (NumPy array vs. plain Python list/int) that DEC-012 must now resolve consistently across the codebase, rather than DEC-012 choosing freely from a blank slate.

### Neutral
- This ADR fixes the DEPENDENCY baseline only; how grids are actually represented internally (NumPy arrays end-to-end vs. NumPy only at the solver boundary vs. something else) is DEC-012's decision, which this ADR narrows but does not resolve.
- Should solver profiling after FR-006 lands show NumPy's vectorized masks are not in fact faster than integer bitmasks at 50x50, the dependency stays justified by the image-I/O half of the pipeline alone, but the solver-side rationale for it would need revisiting.

## References

- DEC-006 (resolved by this ADR)
- FR-003, FR-011 (image-in and image-out requirements Pillow satisfies)
- FR-006, NFR-001 (solver hot-loop requirements NumPy targets)
- ADR-0001 (the generation-time thresholds this dependency choice is defended against)
- DEC-007 (module boundaries that consume this dependency baseline)
- DEC-012 (grid-representation decision, narrowed but not resolved by this ADR)

## History

- 2026-08-27: Created — adopted stdlib + Pillow + NumPy over the recommended stdlib + Pillow-only default, trading a second dependency for vectorized solver headroom at the 50x50 upper bound.
