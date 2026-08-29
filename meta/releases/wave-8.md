# Wave 8 — 2026-08-29   (tag: wave-8)

Single-card wave: CARD-014 ships the last of Increment 2's five export formats. Zero
fix cycles — cleared cycle 1 at 9.2/10.

## Shipped
- CARD-014 (feature): Two-page PDF export with answer key — a fifth renderer riding
  Pillow's existing `save_all`/`append_images` multi-page save (no new dependency,
  ADR-0006/G-1). Page 1 reuses CARD-012's PNG raster unmodified; page 2 reveals the
  solution grid over the same layout. Both pages carry a `"<name> — <difficulty>"`
  header. PDF gets its own filename convention, `<name>-<difficulty>.pdf` (ADR-0016),
  via a generalization of CARD-011's per-run filename stem to be per-format-aware.
  score 9.2 (cycle 1/3)   FR-016, INV-002, CON-002, CON-006, ADR-0006, ADR-0007,
  ADR-0016, ADR-0017

## Requirements closed
- FR-016 (PDF export) — closes Increment 2's export surface. All five formats named in
  the original spec (JSON, PNG, SVG, CSV, PDF) now ship.

## Design decision worth recording
CARD-011 (Wave 6) had already generalized `orchestrator.py` so every export format
shares one filename stem derived from the puzzle's name. CARD-014 needed PDF alone to
use a *different* stem (`<name>-<difficulty>` instead of bare `<name>`) without
disturbing the other four formats. Rather than special-casing PDF inside the export
loop, the implementer factored the existing sanitizer out into a shared
`_sanitized_component` helper and added one format-aware dispatch function
(`_stem_for_format`) that both the name and the new tier suffix route through — one
sanitization rule instead of two, and the base stem is still computed exactly once per
run (its unnamed-aggregate fallback reads the clock, so recomputing it per format could
have let a run straddling a minute boundary write mismatched filenames across formats).
JSON/CSV/PNG/SVG were verified provably unaffected: the dispatch is a single identity
check against the PDF format constant.

## A genuine judgment call, resolved by the reviewer rather than deferred
Pillow's bundled default font cannot render an em dash ("—") — it produces the same
`.notdef` glyph as a permanently-unassigned codepoint. Every fix available inside this
card's guardrails was worse than the problem: shipping a font reopens the closed
dependency baseline (ADR-0006/G-1), and substituting a plain hyphen changes the header
text AC-046 specifies. The implementer drew the em dash as a stroked rule instead of a
glyph — visually indistinguishable from a properly set em dash, since an em dash's
glyph *is* a horizontal rule. The reviewer treated this as a genuinely debatable AC
question rather than nodding it through: does "a header *reading* `cat — Medium`"
require the exact drawing primitive, or the string a human reads off the page? Ruling:
the latter — and the inverted test settles it, since the "literal" implementation
(drawing the actual glyph) is the one that would put a tofu box in the middle of every
PDF this tool produces, i.e. the one that does *not* read `cat — Medium`. Not escalated;
recorded here because the reasoning generalizes past this one card.

## A related gap that WAS escalated — a real product decision, not a code question
The same font limitation has a sibling the reviewer would not let by quietly: a
**non-ASCII `--name`** (`кот`, `café`, `日本語` — all valid per CARD-011/AC-044) sets as
tofu boxes in the PDF header, because there is no rule-substitution available for an
arbitrary Cyrillic or CJK glyph the way there was for one specific dash character.
Every in-card fix breaks a guardrail the same way the em dash did (a font package
reopens G-1; mangling the name breaks AC-044's verbatim requirement), so this was
correctly not decided inside the card. **Backlogged for a user decision**, not left in
worktree notes to die with the branch: ship a bundled font and accept the dependency
exception, document ASCII-only PDF headers as a known limitation, or reject non-ASCII
`--name` at the CLI boundary specifically when `--export pdf` is requested.

## Review process notes
- Cleared cycle 1 outright (9.2, zero Critical/Important findings). The reviewer
  independently decoded the emitted PDF bytes rather than trusting the tests: verified
  the embedded raster against `png.render_image`'s own output via full raw-buffer
  equality (not sampled pixels), verified page 2's revealed cells against the puzzle's
  actual solution grid on an asymmetric test corpus, and confirmed the font's `.notdef`
  claim by comparing bitmaps against a known-unassigned codepoint.
- Two pre-existing test files needed a small, flagged edit: the placeholder name for
  "a format this build doesn't have" was `"pdf"` in two tests, same as `png` was until
  CARD-012 and `csv` until CARD-013 — now `"xlsx"`, since PDF is the last planned
  format. No behaviour changed, only the placeholder string.
- The reviewer also caught and correctly declined to fix a pre-existing gap the
  implementer had already found and flagged: CARD-012's `test_the_png_contains_the_clues`
  asserts `crop(...).getbbox() is not None`, which is vacuously true on any ink-on-white
  image — the gutters are never actually checked. Backlogged, not fixed here (G-2
  territory).

## Convergence
- FR-016 ✓ converged. Increment 2's export surface is now fully shipped (FR-011,
  FR-012, FR-016 across five formats).

## Known gaps / escalations
- AC-037 — still tracked via `xfail`, CARD-018 unchanged, untouched this wave.
- **New, needs a decision:** non-ASCII `--name` produces an unreadable PDF header — see
  above, backlogged.
- Minor, backlogged: a vacuous PNG-gutter test (CARD-012's file), lossy JPEG page
  embedding in the PDF (measurable but invisible-at-print-size pixel drift), and the
  now-four-cards-stale `README.md` Status section, flagged again with still no owner.

## Migrations
- none
