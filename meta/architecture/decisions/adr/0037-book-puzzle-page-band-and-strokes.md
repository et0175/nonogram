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

- 2026-10-28: **R2's figures implemented and its check upgraded from a lens to
  a test (CARD-227).** No decision changed; this entry records what became
  mechanically checked and what did not.

  **What landed.** The book `PageSpec` now carries the three weights as a
  `GridRules` value object — 0.3 pt grey cell lines, 0.8 pt every fifth,
  1.3 pt border — stated once at `book_page_spec.GRID_RULES` and reaching a
  page through `PageSpec.grid_rules`. A `GridLine` carries its tier
  (`cell`/`fifth`/`border`), the declared physical width and the declared
  tone beside the device width it already had; the vector writer strokes the
  declared pair, and the raster renderers keep reading the device width. So
  **every raster page in the book is byte-identical to before this card** —
  no baseline moved, which is why the card was sequenced before CARD-298's
  single recording.

  **The 2-device-pixel clause now has a mechanism, not just a sentence**,
  and the mechanism is `layout.refuse_rasterised_rule`, called per rule at
  **four call sites in three functions**, which is every raster grid stroke
  the book can reach: two in `book_pdf_generator._stroke_drawing` (the two-up
  and solved slots' lines, and their frame) and two in `export/png`
  (`_draw_grid`'s lines and `_draw_frame`) — the pair that rules the
  single-puzzle page and the packed answer page. It has three refusals, two of them regions and one a
  point: a width that is not whole positive pixels (every sheet); a declared
  sheet's rule below 2 device pixels; and a width that IS the declared
  figure's own device count, which is the mutant this card's AC-7 names. It
  therefore *admits* every integer at or above the floor that is not that one
  count, which is stated here because "default-deny" is satisfiable by a
  default-ALLOW predicate underneath (ADR-0039/R2).

  `layout.rasterise_rule_px` is the arithmetic plus the floor — 0.3 pt is
  1 px at 300 DPI and is refused, while the same figure at 1200 DPI is 5 px
  and is admitted, so the floor is a floor on the device rather than a ban on
  the weights. It is **not** a door the shipped code goes through: it has zero
  call sites in `src/`, because the raster renderers never convert a declared
  width at all — they read COMP-007's proportional device width. It is what a
  raster converter must come through on the day one is written (CARD-298), and
  what the tests measure R2's figures against. (Corrected in CARD-227 review
  cycle 1, F-002, which found it described as "the one door".)

  **Two figures this ADR had never had are now measured.** The 2026-10-25
  entry cited poppler on the *cell* line only (2 px at grey 89 at 300 DPI,
  5 px at grey 89 at 1200). Measured the same way, on a rendered vector book
  page (`pdf_vector.rendered_page`, one scanline, run lengths): the **0.8 pt**
  fifth line inks **4 px at 300 DPI and 14 px at 1200**, and the **1.3 pt**
  border **6 px and 22 px**, both at grey 0. The three spans are disjoint and
  ordered at both resolutions and at NFR-008's 4.75 mm floor (2 / 4 / 6 px at
  300 DPI on a 30x30 at clue depth 10, cell 4.7625 mm). Each span is wider
  than the declared width resolves to — 0.3 pt is 1.25 px at 300 DPI — because
  poppler antialiases a stroke that does not land on a pixel boundary, and the
  same phase moves each span by up to a pixel along a page. So "the pixel
  width scales with the resolution" is held as `declared <= span <= declared +
  2` at **each** resolution rather than as a span-to-span ratio: the cell
  line's ratio is 2.5 against the resolution's 4, and a band loose enough to
  admit 2.5 would admit almost anything. The exact x4 belongs to the declared
  width's own resolution (1.25 px -> 5 px) and is asserted there.

  **What this card deliberately did not decide.** The grid's stroke order is
  keyed on `GridLine.major`, which has two values where there are now three
  weights, so inside the heavy half the border and the fifths interleave and
  the page re-sets its width on each change (seven `w` operators on a 20x20,
  not three). It costs operators and nothing else — both heavy tiers are the
  same pure black, so no crossing looks different whichever is on top — and
  keying the order on the tier is a change to stroke order in four renderers.
  Flagged, not answered.

  **`min_thin_rule_mm` is scoped, not retired and not re-numbered.** The book
  profile still carries 0.25 mm, and both its docstrings now say what it is:
  the floor on a thin grid rule **on a raster surface**. Under this rule's
  amended wording the interior has no millimetre floor at all, so replacing
  0.25 with 0.1058 (0.3 pt in millimetres) was refused outright — a floor set
  *at* the figure it protects asserts nothing and reads as licence. It was
  scoped rather than dropped because the pages it governs are still here: the
  interior walk is raster until CARD-298 chooses a medium per page.

- 2026-10-25: **R2 amended again — the grid's three weights are the owner's own
  0.3 / 0.8 / 1.3 pt, and the 2-device-pixel clause is re-expressed rather than dropped.**
  Owner decision on the CARD-293 proof (*"I looked at the pdf and I like it (vector versions)"*,
  *"I also like card-proof-vector"*), page 1 of
  `~/Documents/nonogram-reviews/CARD-293/card293-proof-vector.pdf`. This discharges
  ADR-0042/R7's deferral and closes the question the 2026-10-17 amendment opened.

  **What changed and what did not.** The figures moved from 0.48 / 1.28 / 2.08 pt to
  0.3 / 0.8 / 1.3 pt. The **ratios did not move at all** — 1 : 2.667 : 4.333 were the owner's in
  both. The x1.6 between them was never a design choice: the 2026-10-17 amendment applied it
  "so the thinnest line is 2 device pixels at 300 DPI rather than one", and ADR-0042/R7 made that
  floor inapplicable to the interior by making the interior a content stream. So this amendment
  does not overturn a judgement; it removes an arithmetic correction whose premise expired.

  **The clause that had to be re-expressed, and why deleting it would have been wrong.** R2's
  statement carried "each of them at least 2 device pixels at the render resolution". That clause's
  *purpose* — no dropout — still binds. Its *mechanism* — a generator rounding a stroke to an
  integer pixel count — does not exist in a content stream. Measured by poppler on the rendered
  vector file (CARD-293 AC-2): the 0.3 pt cell line occupies **2 px at grey 89 at 300 DPI and 5 px
  at grey 89 at 1200 DPI** — grey 89 being `round(255 × 0.35)`, the declared tone hit exactly at
  both, with the width scaling ×4 and the tone not moving. That is what "no device floor in vector"
  means, measured. But the same figures through a **raster** generator round to **1 / 3 / 5 px**,
  which is precisely the one-pixel cell grid the 2026-10-17 amendment refused on the evidence of
  7 of 17 reviews. The refused configuration is therefore still refused, and R2 now says so by
  binding the figures to the medium: a raster puzzle grid keeps the 2-device-pixel floor and
  consequently cannot use these numbers at all.

  **Decided on screen, not on paper, and this ADR's own Decision section asked for paper** — it
  says the weights "become final only after the owner has seen them on printed proof pages". The
  owner judged the vector renders instead. Two things remain measured by nobody: dot gain on
  uncoated cream stock at 0.1058 mm, and whether 35% grey reads as light guidance or as faded in
  print. The owner accepted that by deciding now; the revisit trigger is the first printed book or
  proof, and a change there is an amendment here rather than drift.

  **What the 2026-10-17 entry below said that is now obsolete.** That entry recorded, as "a real
  loss of room and not a bookkeeping fix", that the grid's thinnest cell line and the footer
  hairline would both become 2 px — *"the same width"* — so that "width has reached the device
  floor" and "the furniture/grid distinction now rests on tone, not weight". **For the interior
  that is no longer true.** At 0.3 pt the cell line is physically *lighter* than a 0.4 pt
  hairline, so width is available again as a distinction. The entry's reasoning stands for any
  raster surface and for the record of why CARD-227 was ever scaled; it no longer describes the
  interior. **The furniture's own floor is NOT decided here** — nobody asked about it. R2 has
  never bound furniture (see that entry), CARD-222 / CARD-225 / CARD-248 all cite the
  2-device-pixel floor for furniture directly, and they keep today's figures until someone decides
  otherwise. Flagged, not answered.

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
  scope: {code: ["src/nonogram/admin/book_pdf_generator.py"]}
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
  # CHECK UPGRADED 2026-10-28 (CARD-227, its Obligation 1). It was
  # `review-lens` only — which cannot fail a build — and that was deliberate:
  # naming TestBookGridRules_HasThreeWeights before it existed would have been
  # a dead check-ref, read as *mechanically checked* by system_rules.py and
  # forge:review Step 8h. The test exists now, so the ref is live.
  #
  # WHAT THE REF EXECUTES, and what it does not, because a check-ref is read
  # as covering its rule's whole statement and this one does not:
  #   RUN  the three figures, read out of the content stream of a written PDF
  #        (TestBookGridRules_HasThreeWeights), with a control that reads the
  #        retired x1.6 figures back as themselves, so the reading is shown to
  #        discriminate rather than to agree;
  #   RUN  the ink ordering, as an ordering and not a byte
  #        (TestBookGridRules_CellLinesAreLighterThanTheFifths), and
  #        structurally: GridRules refuses a sheet whose cell line is pure
  #        black or no lighter than its fifths;
  #   RUN  "a raster grid cannot use these figures"
  #        (TestBookGridRules_TheseWidthsNeverReachARasterGrid) at BOTH
  #        raster grid strokers -- book_pdf_generator._stroke_drawing and
  #        export/png's _draw_grid/_draw_frame -- plus the advance arithmetic
  #        layout.rasterise_rule_px, each with a negative control (the same
  #        figure at 1200 DPI is admitted; the book's real raster width is
  #        admitted; the real book page draws through both strokers), so none
  #        of it reads as a blanket refusal. layout.rasterise_rule_px has NO
  #        call site in src/ and is not claimed as a door (F-002);
  #   NOT RUN  "the default PageSpec's strokes unchanged". That clause is
  #        ADR-0036/R1's own check
  #        (TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden) and is not
  #        re-executed here: this rule states it, that rule gates it.
  #   WAS an open bound, NOW RUN (CARD-227 review cycle 1, F-001): the
  #        floor on png._draw_grid, the other raster grid stroker. The
  #        premise that bound was declared on was FALSE. These figures DO
  #        reach that function -- _blank_page rules a book single-puzzle
  #        page's grid through render_pages -> png._draw_grid, and
  #        render_answer_page rules a packed answer tile through the same
  #        function; neither goes through _stroke_drawing, which rules only
  #        the two-up and solved slots. Measured by a spy on png._draw_grid
  #        and png._draw_frame -- DOMAIN: four _blank_page calls on four grid
  #        shapes (20x20, 30x30 at clue depth 10, 15x22, 5x5) = 159 strokes,
  #        plus one render_answer_page holding those four answers = 155, so
  #        314 in all -- and EVERY ONE of the 314 carried a width_pt of
  #        0.3 / 0.8 / 1.3 pt beside a device width of 3 or 6 px. Instrument
  #        controls (ADR-0039/R4): it rises (1 page 43, 4 pages 159), it reads
  #        0 when no page is drawn, and on a CLI sheet it reads 42 strokes of
  #        which 0 declare anything. So the unguarded stroker was the one that ruled
  #        the dominant interior page kind, and the control this comment said
  #        could not fail is
  #        test_the_other_raster_stroker_is_guarded_too_and_it_is_the_one_that_rules_a_book_page,
  #        which has three arms: the real book page draws, the mutant reds,
  #        and the shipped unguarded path drew the refused configuration
  #        silently (260,523 inked pixels, measured before the guard). No ink
  #        moved: three real book raster pages are pixel-digest-identical
  #        across the change (G-5).
  #
  # AMENDED AGAIN 2026-10-25 (owner decision on the CARD-293 proof) — the
  # figures are now the owner's own 0.3 / 0.8 / 1.3 pt, not the x1.6-scaled
  # 0.48 / 1.28 / 2.08 pt. The scaling existed for exactly one reason, "so the
  # thinnest line is 2 device pixels at 300 DPI rather than one", and
  # ADR-0042/R7 removed that reason by making the interior a content stream.
  # The ratios never changed: 1 : 2.667 : 4.333, the owner's throughout.
  #
  # THE 2-DEVICE-PIXEL CLAUSE IS RE-EXPRESSED, NOT DELETED, and this is the
  # load-bearing part of the amendment. Its PURPOSE — no dropout — still
  # binds. Its MECHANISM — a generator choosing an integer pixel count — does
  # not exist in a content stream, where the RIP resolves a declared width at
  # its own resolution. Measured by poppler on the rendered vector file
  # (CARD-293 AC-2): the 0.3 pt cell line occupies 2 px at grey 89 at 300 DPI
  # and 5 px at grey 89 at 1200 DPI — the declared tone hit exactly at both,
  # the width scaling with the device. A RASTER generator at the same figures
  # rounds to 1 / 3 / 5 px, which is the one-pixel cell grid the 2026-10-17
  # amendment refused on the evidence of 7 of 17 reviews. Hence the statement
  # now binds the figures to the medium instead of carrying a pixel minimum
  # that a vector writer cannot meaningfully satisfy or violate.
  #
  # DECIDED ON SCREEN, NOT ON PAPER. The Decision section above says these
  # weights "become final only after the owner has seen them on printed proof
  # pages"; what happened is that the owner judged the vector RENDERS. Dot
  # gain on uncoated cream stock, and whether 35% grey reads as guidance or as
  # faded on paper, remain measured by nobody. The owner accepted that by
  # deciding now; the revisit trigger is the first printed book or proof, and a
  # change there is an amendment to this rule, not drift.
  statement: >-
    Under the book PageSpec the puzzle grid has exactly three rule weights --
    0.3 pt ordinary cell lines in grey, 0.8 pt every fifth line on both axes,
    1.3 pt outer border -- with the cell lines lighter in ink than the fifth
    lines and the border, and the default PageSpec's strokes unchanged. These
    are PHYSICAL widths and they hold only where the grid is drawn as PDF
    content-stream operators (ADR-0042/R1), because only there does the
    renderer resolve a declared width and a declared tone at whatever
    resolution it runs. A generator that RASTERISES a puzzle grid rounds each
    stroke to an integer pixel count instead, and at 300 DPI these widths
    round to 1 / 3 / 5 px -- the one-pixel cell grid this rule's 2026-10-17
    amendment refused. So no puzzle grid is rasterised at these weights: a
    raster grid remains held to at least 2 device pixels per rule at its own
    render resolution, which at 300 DPI means it cannot use these figures at
    all.
  scope: {code: ["src/nonogram/export/layout.py", "src/nonogram/admin/book_page_spec.py"]}
  check: {kind: test, ref: TestBookGridRules_HasThreeWeights}
  severity: mandatory
```
