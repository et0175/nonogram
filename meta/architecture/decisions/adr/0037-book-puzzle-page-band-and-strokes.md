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

COMP-007 draws lines in black, thin = cell / 30 rounded to whole pixels at 300 DPI, heavy = 2 × thin. Measured on the book's cell range (NFR-008, 4.75–7.5 mm), that gives a 0.17 mm thin rule for cells below about 6.4 mm (the 26–30 puzzles and 21–25 squares) and 0.25 mm above. Following ADR-0036, book geometry is a `PageSpec` passed to `compute_layout`, so a book-only rule can live in the spec without changing CLI or web output (CON-019).

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
- A fixed 0.25 mm thin rule is a larger share of a 4.75 mm cell (about 5%) than of a 7.5 mm one, so large puzzles look denser. The proof page decides whether that is acceptable.
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

- 2026-10-17: **R2's scope clarified — it binds the puzzle grid, not page furniture — and a
  consequence of the amendment above is recorded.** No decision changed. CARD-222's review
  surfaced that the card had read R2 as binding the interior footer's hairline and had written
  it a formal **exemption** with an ADR-0039/R3 control. R2 does not bind it: the superseded
  wording said "every thin **grid** rule" and the amended wording says "the puzzle **grid** has
  exactly three rule weights". A footer hairline is furniture. The exemption was unnecessary
  under the old rule and is **vacuous** under the new one — measured: the hairline is 0.4 pt =
  1.667 px → **2 px = 0.1693 mm**, which is *exactly* the amended minimum, not under it. The
  card's claim "at 0.169 mm it is deliberately under that minimum" was true against the retired
  0.25 mm and is false against the amendment, which landed the same day from the same pass.
  **The consequence worth recording, because it is a real loss of room and not a bookkeeping
  fix:** once CARD-227 implements the three weights, the grid's thinnest cell line is 0.48 pt =
  **2 px**, and the footer hairline is also **2 px**. They become *the same width*. Furniture
  can no longer be made lighter than grid ink by width, because **width has reached the device
  floor** — and the step below, 1 px, is precisely the dropout risk the amendment above rejected
  for the grid. So the furniture/grid distinction now rests on **tone**, not weight, which the
  design already supports: the grid's cell lines are grey while its fifths and border are dark.
  Anything that wants to read lighter than a cell line must be lighter in *ink*, and there is
  no room left underneath in width. Stated here so the next card reaches for tone rather than
  rediscovering the floor.
  **What this obliges of CARD-222** (recorded on that card): drop the false exemption claim and
  retarget its control onto what is actually load-bearing and falsifiable — the hairline sits at
  the 2 px dropout floor, and the header rule is heavier than it (3 px against 2 px), which is
  what makes the pair read as a heading rule and a hairline. As written, two of that control's
  three assertions go red when CARD-227 lands, and the red would read as a CARD-227 regression
  while actually asserting a property the amendment makes unsatisfiable.
- 2026-10-17: **R2 amended — the grid gets three weights, the cell lines go grey, and the thin
  minimum drops 0.25 → 0.169 mm (owner decision, CARD-227).** The Decision's two-weight stroke
  minimum is superseded; everything else in this ADR stands.
  **What was wrong.** The owner's artifact "Puzzle page layout" (2026-10-14) specifies
  0.3 pt grey cell lines, 0.8 pt every fifth line and 1.3 pt outer border. Set against R2 as
  written, that artifact broke it **three** ways at once, of which the card had recorded only
  one: the ratios (2.67x and 4.33x against "twice the thin rule"), the colour (grey against
  "pure black"), and — the one nobody had noticed — the **minimum**. 0.3 pt is 0.1058 mm,
  which at 300 DPI is a **one-pixel** line: 2.4x under R2's floor, and *thinner than the
  0.17 mm this ADR had explicitly rejected* as "exactly where faint lines hurt most", on the
  evidence of 7 of 17 reviews of the 450-puzzle book complaining of faint grid lines
  (research section 5). Shipping the artifact literally would have re-opened the single
  complaint this ADR exists to close, and would have done it quietly, inside a card scoped as
  a stroke-width tweak.
  **What was decided.** The owner's **ratios are kept exactly** — 1 : 2.667 : 4.333 — and the
  figures scaled by 1.6 so the thinnest line is **2 device pixels** at 300 DPI:
  0.48 / 1.28 / 2.08 pt = 0.1693 / 0.4516 / 0.7338 mm, rendering 2 / 5 / 9 px. All three
  rendered widths are distinct, so the weights stay distinguishable even at NFR-008's 4.75 mm
  floor, and 0.1693 mm is the same 0.17 mm the package already prints at its small cells
  today — so this is not a regression against shipped behaviour, only against R2's aspiration.
  **The middle path was ruled out by arithmetic, not skipped.** Lifting only the cell line to
  R2's old 0.25 mm floor (0.709 pt) puts it at 2.95 px against the fifth line's 0.8 pt =
  3.33 px, and both round to **3 px** — two of the three weights would be indistinguishable,
  failing the card's own "no two round to the same width" criterion. There is no reading of a
  three-weight hierarchy that satisfies R2 as written, which is why this is an amendment
  rather than a card-level clarification.
  **Reach, stated rather than implied** (ADR-0039/R1). The amended R2 is held by a
  `review-lens` only, which cannot fail a build — the same weakness that made the wave-43
  retrospective's headline a negative result. That is temporary and deliberate: naming
  CARD-227's `TestBookGridRules_HasThreeWeights` before the card writes it would be a dead
  check-ref, the exact defect a `meta/` carry produced earlier this wave. CARD-227 upgrades
  this check to that test as part of landing, and the obligation is recorded on the card.
  **What is left open and measured, not waved past:** the weights are now absolute points, so
  they no longer scale with the cell. At the 4.75 mm floor a 0.48 pt rule is 3.6 % of the cell
  and at the 7.5 mm cap 2.3 % — large puzzles get a *relatively* heavier grid than small ones,
  the opposite of the proportional rule's behaviour, and the Consequences' "about 5%" note
  above describes the superseded two-weight scheme. Whether that reads well is a proof-page
  question, and the proof page is already required before a book is finalised.
- 2026-10-17: **The cell floor restated 4.8 → 4.75 mm; both measured figures re-derived and
  unchanged** — the same NFR-008 amendment recorded in ADR-0036. Two statements here quote
  the band, and because both carry *measurements* taken across it, neither was carried over
  on trust:
  • the Context's "0.17 mm thin rule for cells below about 6.4 mm, 0.25 mm above" is
  **re-derived at the new floor and holds exactly** — COMP-007's thin rule is cell/30 rounded
  to whole device pixels at 300 DPI, so a 4.75 mm cell gives 1.870 px → 2 px = 0.169 mm, the
  same 2 px the old 4.8 mm floor gave (1.890 px); the ~6.4 mm breakpoint is also unmoved
  (6.35 mm → 2 px, 6.40 mm → 3 px). The lower floor extends the low end of the band without
  crossing a rounding boundary, which is why the figures survive.
  • the Consequences' "0.25 mm is a larger share of the smallest cell (about 5%)" is
  re-derived as 5.26% at 4.75 mm against 5.21% at 4.8 mm — still "about 5%", and still
  3.33% at the 7.5 mm cap.
  **One figure is deliberately NOT updated and is owed.** The Decision's proof page is
  described as "one 30×30 (a 4.8–5.0 mm cell)". That is a *measurement of what a 30×30
  prints at*, not a restatement of the floor, and it moved for a different reason — CON-018's
  amended margins (outside 0.5 in, top 0.55 in, bottom 0.47 in) shrink the usable area, and
  the registry already records 30×30 cells falling to 4.536–4.646 mm under them. Those
  margins are in flight on CARD-222's branch and are not merged, so the honest figure cannot
  be measured yet and has not been guessed. Re-measure it against the merged tree once
  CARD-222 lands; until then this parenthesis understates how small the proof page's cell is.
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
  # AMENDED 2026-10-17 (owner decision, CARD-227) — see this ADR's History.
  # Was: "every thin grid rule is at least 0.25 mm and every heavy rule is
  # twice the thin rule, in pure black". Three things changed: the grid has
  # THREE weights rather than two, the cell lines are GREY rather than pure
  # black, and the thin minimum is 2 device pixels (0.169 mm at 300 DPI)
  # rather than 0.25 mm. Under the book spec the weights are ABSOLUTE POINTS,
  # which supersedes COMP-007's proportional cell/30 rule quoted in the
  # Context above — that rule still governs the default spec.
  # SCOPE, clarified 2026-10-17 after CARD-222's review read it the other way:
  # R2 binds the **puzzle grid's** rules and nothing else. Page furniture --
  # the interior header rule, the footer hairline, a divider -- is NOT a grid
  # rule and never was, under this wording or the superseded one ("every thin
  # *grid* rule"). Furniture that must not drop out on press is held to the
  # same 2-device-pixel floor, but for the dropout reason directly and not
  # through R2, so it needs no exemption from R2 and must not claim one.
  # The check is `review-lens` only until CARD-227 lands the measuring test;
  # naming TestBookGridRules_HasThreeWeights before it exists would be a dead
  # check-ref. CARD-227 upgrades this check to that test as part of its
  # landing — recorded on the card, not left to memory (ADR-0039/R1: a
  # coverage claim needs a control that can fail).
  statement: >-
    Under the book PageSpec the puzzle grid has exactly three rule weights --
    0.48 pt ordinary cell lines in grey, 1.28 pt every fifth line on both
    axes, 2.08 pt outer border -- each of them at least 2 device pixels at the
    render resolution, with the cell lines lighter in ink than the fifth lines
    and the border; the default PageSpec's strokes are unchanged.
  scope: {contexts: [CTX-001], code: ["src/nonogram/export/layout.py", "src/nonogram/admin/book_page_spec.py"]}
  check: {kind: review-lens}
  severity: mandatory
```
