# Backlog

## Deferred from Nonogram Generator brainstorm (2026-08-27)
- [ ] Support color/multi-value nonograms (not just black/white)                    @feature
- [ ] Interactive/playable puzzle output (web or local UI to solve the puzzle)      @feature

## Surfaced during delivery (Wave 7, 2026-08-29)
- [ ] Retune difficulty score weights/cutoffs (ADR-0005/ADR-0013) — `--difficulty hard`
      is unreachable and `medium` is hard to hit with real generated grids (measured
      ceiling ~43 vs. the Hard floor of 66, across 10x10-25x25 at 45-55% density).
      ADR-0005's own Consequences section predicted exactly this and deferred the
      numbers pending real distributions — CARD-010 (Wave 7) produced the first ones.
      Needs an ADR-0005/ADR-0013 revision (new weights and/or cutoffs), not a code
      change.                                                                       @tech-debt

## Surfaced during delivery (Wave 8, 2026-08-29)
- [ ] **Decision needed:** a non-ASCII `--name` (e.g. `кот`, `café`) renders as `.notdef`
      tofu boxes in the PDF header — Pillow's bundled default font is an ASCII-only
      subset (verified: identical bitmap to an unassigned codepoint). CARD-011 keeps
      `--name` verbatim (AC-044) and CARD-014 could not fix this without breaking a
      guardrail: shipping a font reopens ADR-0006/G-1 (closed dependency baseline),
      mangling the name contradicts AC-044. Filenames are unaffected (sanitization is
      already Unicode-aware) — only the PDF header text is impacted. Options: (a) ship
      a small TTF as package data and accept the dependency-baseline exception, (b)
      document ASCII-only PDF headers as a known limitation, (c) reject non-ASCII
      `--name` at the CLI boundary when `--export pdf` is requested. Needs a product
      call, not a code fix.                                                        @tech-debt
- [ ] `tests/test_export_image.py::test_the_png_contains_the_clues` is vacuous —
      asserts `crop(...).getbbox() is not None` on an ink-on-white RGB image, which is
      always true (white is non-zero), so the gutters are never actually checked for
      ink. Found while building CARD-014 (whose own tests use a real `_has_ink`
      predicate instead). Fix belongs in CARD-012's test file.                     @tech-debt
- [ ] `README.md`'s Status section is stale since CARD-007 and now four export formats
      out of date (JSON/PNG/SVG/CSV/PDF all shipped; README still describes an earlier
      state). Flagged repeatedly across CARD-010/011/014 with no owner yet.         @tech-debt
- [ ] PDF pages embed their raster as lossy JPEG (Pillow's default for an RGB page),
      producing measurable pixel drift on white background (up to 45/255 on some
      pixels) — invisible at print size, no AC/NFR currently governs it, but worth
      checking `quality=95` or an alternate save path if crisp reproduction ever
      matters more than file size.                                                 @tech-debt
