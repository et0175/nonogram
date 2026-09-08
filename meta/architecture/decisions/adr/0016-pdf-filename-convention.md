# ADR-0016: PDF export filename convention

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-016 requires that a finalized, uniqueness-confirmed puzzle be exportable as a single two-page PDF (blank puzzle + clues on page 1, answer key on page 2), with both pages showing the puzzle's name (FR-015) and difficulty tier as a header. FR-015 gives every puzzle a name — either auto-generated (a library key such as "cat", or a mode+timestamp such as "random-2026-08-27-1430") or explicitly set via `--name` — and separately assigns each puzzle a difficulty tier. Neither FR-015 nor FR-016 specifies what filename the exported PDF is written to on disk; the header content (name + difficulty, shown on the page itself) and the export filename (the path written by the CLI) are two distinct pieces of information that happen to draw from the same two puzzle attributes.

FR-011 and FR-012 already export the same puzzle (as PNG/SVG and as JSON/CSV, respectively) without this delta re-examining how those exports name their output files, so whatever filename convention is chosen for PDF export sits alongside — and should not gratuitously diverge from — however those other formats already resolve a file path from a puzzle's attributes. Because puzzle names can be reused across different generation runs (an auto-generated library key like "cat" is not guaranteed unique, and an auto-generated mode+timestamp name collides at minute granularity per DEC-018), two distinct puzzles can end up sharing the same name while differing in difficulty tier — the tier being the one other attribute FR-016 already requires on the page header. The filename question that remains open is precisely which of the puzzle's attributes name the PDF export file: the name alone, the name plus the difficulty tier, or a path supplied independently of the puzzle's own identifying attributes via a separate flag.

## Decision

We will name the PDF export file `<puzzle-name>-<difficulty>.pdf`, both components sanitized for filesystem-safe characters. This satisfies FR-016 because the filename is derived directly from the same two attributes (name and difficulty tier) already required to render on the PDF's own header, so the file on disk is self-describing without opening it, and it reduces the accidental-collision surface identified in DEC-017/DEC-018 by distinguishing exports of differently-tiered puzzles that happen to share an auto-generated name, at the small cost of a longer filename than the name alone.

## Alternatives considered

### name_only

Filename is `<puzzle-name>.pdf`, sanitized for filesystem-safe characters. This is the simplest option and matches the puzzle's display name most directly, but it was rejected because two puzzles that happen to share an auto-generated name — which FR-015's naming scheme does not guarantee to be unique, and which DEC-018 confirms can collide even within the same generation mode — would produce identical PDF filenames despite being different puzzles at different difficulty tiers. That collision surface is exactly what DEC-017's overwrite/error/auto-suffix policy then has to absorb, so leaving it unaddressed here pushes an avoidable problem downstream for no simplicity gained over the chosen alternative.

### explicit_output_flag

A separate `--output` flag controls the PDF path independently of `--name`. This fully decouples the display name from the file path and is the most flexible option, but it was rejected because it introduces an extra required flag/decision at export time that is inconsistent with how PNG/SVG (FR-011) and JSON/CSV (FR-012) export naming already works — a delta this ADR does not re-examine or override. Adding a bespoke, PDF-only naming mechanism would make the CLI's export surface asymmetric across formats without a demonstrated need for that extra flexibility, since the two-attribute convention already resolves the collision concern that motivated considering it.

## Consequences

### Positive
- The PDF filename is self-describing: seeing `cat-hard.pdf` on disk tells the user both the puzzle name and its difficulty tier without opening the file, mirroring the header FR-016 already puts on the page.
- Exports of differently-tiered puzzles that share an auto-generated name (a realistic case given FR-015's non-unique naming and DEC-018's same-minute timestamp collisions) no longer collide on filename before DEC-017's collision policy even has to run.
- No new CLI flag or export-time decision is introduced — the filename is derived deterministically from attributes the puzzle already carries, keeping the export command's surface as small as FR-011/FR-012's precedent.

### Negative
- The filename is longer and less predictable to type back on the command line than the bare puzzle name, since the user must also recall or look up the difficulty tier to reference the exact file.
- Two exports of the *same* puzzle (same name, same difficulty) still collide on filename; this convention narrows but does not eliminate the collision surface DEC-017 must handle.

### Neutral
- The sanitization rule applied to the puzzle name for filesystem-safe characters must now also be applied consistently to the difficulty tier label when composing the combined filename.
- This convention is scoped to PDF export (FR-016) only; it does not retroactively change how FR-011 (PNG/SVG) or FR-012 (JSON/CSV) name their output files, so those formats and PDF export can name files differently unless a future ADR unifies them.

## References

- DEC-016 (resolved by this ADR)
- CTX-001 (Puzzle Creation — the context owning puzzle name, difficulty tier, and PDF export)
- FR-011, FR-012 (existing export naming precedent this decision does not override)
- FR-015 (puzzle naming and difficulty tier as the two source attributes)
- FR-016 (PDF export requirement this decision resolves the filename for)
- DEC-017, DEC-018 (collision-handling and auto-name-precision decisions this filename convention narrows but does not replace)

## History

- 2026-08-27: Created — adopted `<puzzle-name>-<difficulty>.pdf` as the PDF export filename convention, to keep the on-disk file self-describing and to reduce (without eliminating) the collision surface between differently-tiered puzzles sharing an auto-generated name.
