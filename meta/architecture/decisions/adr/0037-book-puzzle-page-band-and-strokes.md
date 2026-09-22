# ADR-0037: A book puzzle page shows its number and tier, with print-weight lines

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-033 (BK-5) bans picture titles from the puzzle page, which leaves the 12 mm title band reserved by CON-018 (TERM-028) with no stated content. FR-033 also asks for "dark" grid lines and a "clearly bolder" every-5th line, with no measurable threshold. The top complaint in the big-book reviews was faint grid lines, in 7 of 17 reviews of the 450-puzzle book (research §5).

COMP-007 draws lines in black, thin = cell / 30 rounded to whole pixels at 300 DPI, heavy = 2 × thin. Measured on the book's cell range (NFR-008, 4.8–7.5 mm), that gives a 0.17 mm thin rule for cells below about 6.4 mm (the 26–30 puzzles and 21–25 squares) and 0.25 mm above. Following ADR-0036, book geometry is a `PageSpec` passed to `compute_layout`, so a book-only rule can live in the spec without changing CLI or web output (CON-019).

The owner also wants a "beginner to expert" book to tell the solver each puzzle's level (2026-09-22). The research says difficulty labels sell as long as they match the solver's tier.

## Decision

We will print **"Puzzle N · Tier"** in the band above each puzzle, for example "Puzzle 12 · Easy". N matches the puzzle's answer-key entry, and the tier is the solver's (FR-009, never grid size). The book's `PageSpec` carries a stroke minimum: thin rule ≥ 0.25 mm (3 device pixels at 300 DPI), heavy rule = 2 × thin, pure black (#000). It applies only to the book spec, so the default A4 path keeps today's strokes byte for byte.

The final numbers are confirmed on printed proof pages before a book is finalised: one 30×30 (a 4.8–5.0 mm cell) and one 15×15 (7.5 mm), checked by the owner by eye, following the owner-validates-visually practice. The number and the tier together serve the answer key and the "beginner to expert" promise. The stroke minimum directly addresses the most common print complaint, at the sizes where today's proportional rule is thinnest.

## Alternatives considered

### Number in the band, current strokes kept
"Puzzle 12" with COMP-007's proportional strokes, with FR-033's thresholds written down as today's values. Rejected: it leaves 0.17 mm thin lines on the largest puzzles, exactly where faint lines hurt most. It also doesn't show the level the owner wants shown.

### Blank band, book-specific strokes
The band stays empty space and the book uses its own strokes. Rejected: a puzzle page with no number makes the answer key harder to use.

### Number, size and tier in the band
For example "12 · 25×20 · Medium", with current strokes. Rejected: the size is visible on the grid itself, so it adds text without adding information. It also keeps the thin strokes.

## Consequences

### Positive
- Solvers can find each answer by number and see each puzzle's level, which supports a "beginner to expert" title.
- Every line in the book is at least 0.25 mm, whatever the cell, removing the faint-line risk on 26–30 puzzles.
- CLI and web output are unchanged: the minimum is a `PageSpec` field that only the book sets.

### Negative
- Printing the tier invites "too easy / too hard" comparisons, so the solver's grading has to hold up (ADR-0029). A mislabelled puzzle is now visible on its own page.
- A fixed 0.25 mm thin rule is a larger share of a 4.8 mm cell (about 5%) than of a 7.5 mm one, so large puzzles look denser. The proof page decides whether that is acceptable.
- A proof-print step is added before finalising a book. It is manual and can't be automated.

### Neutral
- The band text uses the tier's display name (Easy / Medium / Hard, three tiers per ADR-0031).
- Ordering the book by difficulty with a divider page per level, two-puzzle pages, and keeping pictures upright are new owner requirements from the same discussion. They are formalised through a raw-requirements delta, not decided here.
- Solution hints are a deferred future requirement and don't affect the band.

## References

- DEC-039 (resolved by this ADR)
- CTX-001; COMP-007, COMP-009; TERM-028
- FR-009, FR-033, CON-018, CON-019, NFR-008
- ADR-0029 (strategy ladder grading), ADR-0031 (three tiers), ADR-0036 (PageSpec)
- docs/research/book-format-research.md §5 (reader reviews)

## History

- 2026-09-22: Created — book puzzle pages print "Puzzle N · Tier" in the band; book-only stroke minimum of 0.25 mm thin, heavy = 2 × thin, pure black, confirmed on printed proofs.

## Rules

```yaml
- id: ADR-0037/R1
  statement: >-
    A book puzzle page never prints the picture's title; its band shows the
    puzzle number and the solver's tier only.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/book_pdf_generator.py"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0037/R2
  statement: >-
    Under the book PageSpec every thin grid rule is at least 0.25 mm and every
    heavy rule is twice the thin rule, in pure black; the default PageSpec's
    strokes are unchanged.
  scope: {contexts: [CTX-001], code: ["src/nonogram/export/layout.py"]}
  check: {kind: review-lens}
  severity: mandatory
```
