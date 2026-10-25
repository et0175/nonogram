# ADR-0042: The book interior is drawn as PDF operators; the cover stays raster

**Status:** Accepted

**Date:** 2026-10-25
**Decided by:** the owner, on CARD-293's measurements
**Supersedes:** nothing. **Constrains:** ADR-0037/R2's device floor, for the interior only — see "What this does NOT decide".

## Context

Every page of a book interior is today a **2550 × 3300 RGB bitmap — 25,245,000
bytes** — drawn with Pillow and written into the PDF as a JPEG image XObject
(`book_pdf_generator.py:252`, `app.py:6141`, `book_proof.py:789`). A printed
interior page is therefore a photograph of line art, in a lossy format, at a
fixed device resolution.

A nonogram page is grid lines, flat fills and digits. Raster is the wrong
representation for it, and the project has been paying for that in four separate
places:

**Print quality, which is the motive.** ADR-0037/R2's 2026-10-17 amendment had to
**refuse the owner's own design**. The "Puzzle page layout" artifact specified
0.3 pt grey cell lines, 0.8 pt every-fifth and 1.3 pt border; **0.3 pt is
0.1058 mm, which at 300 DPI is a ONE-PIXEL line** — under the floor that ADR had
set after 7 of 17 reviews of the 450-puzzle book complained of faint grid lines.
The same amendment records the consequence: *"width has reached the device
floor"*, so furniture can no longer be made lighter than grid ink by width and
the distinction "now rests on tone". **That whole constraint is an artefact of
rasterisation.**

**Memory.** A page bitmap is 25.2 MB. CARD-145 exists because the deployed panel
was OOM-killed by materialising a list of them; its `del page`, its 2.00-vs-1.00
retention equality and `interior_stream`'s one-page-at-a-time contract are all
scaffolding around that number. CARD-218 found 433.4 MiB retained to session
end; CARD-288 found 2.71 GiB peak in one test file.

**File size.** Measured on a real 24-page interior: **9,157,535 B raster against
407,976 B vector — 22.4×.** Extrapolated to the 450-page book the complaints came
from: **171.7 MB against 0.92 MB.**

**Test honesty.** 21 test files measure *ink* — they recover geometry by counting
dark pixels, which is a **reconstruction of numbers the generator knew exactly**
(`drawing_of`'s own docstring: `columns` is "how many columns the grid is drawn
with, **counted from its vertical rules**"). Worse,
`TestBookProof_StrokesMeetBookMinimum`'s docstring records that the DCT round
trip greys a 3-px rule's edges, **so the test reads an in-memory page upstream of
the PDF**: today's pure-black assertion cannot be made against the file that
actually ships.

**And the plumbing already exists.** `_write_pdf` has driven PDF object structure
by hand through `PIL.PdfParser` since CARD-145 — object ids, catalog, page
objects, content streams, xref, trailer (`:379`, `:7105`). A vector interior
replaces **one of the three objects a page writes**. It is not a new capability;
it is a different content stream in a writer the project already owns.

## Decision

**DEC-048 — the book interior is drawn as PDF content-stream operators, and the
cover stays a raster image.**

Interior pages — **puzzle pages, answer pages, the table of contents and the
guide** — are emitted as PDF operators (`m`/`l`/`re`/`c`/`S`/`f`/`g`/`rg`/`w`,
and text through an embedded font). No such page carries an image XObject. **The
cover remains raster**, because a cover is a photograph and raster is the right
representation for it.

**Section dividers are deliberately left raster for now** (owner, 2026-10-25),
and the reason is scheduling rather than technique. **CARD-231 redesigns the
divider page outright** — "a section opener names its section in large type, with
dots, range and a line of what to expect" — against today's page, whose own
docstring is *"one word on the book's trim, one page"*. Converting a page that is
about to be replaced is throwaway work; **the new design can be born vector
instead**, with stream assertions from its first commit rather than
ink-measuring tests written and then retargeted.

That makes dividers the **second declared instance** of R2 rather than the first
being the cover alone — which is better for the rule than a theoretical escape
hatch, because it proves per-page mixing is a worked end state and gives the
"declared with a reason" requirement something real to hold.

**The whole interior, not a carve-out.** Scoping this to puzzle and answer pages
only would mean maintaining a raster page writer, its ink-measuring tests and the
DCT workarounds **permanently**, for the two page kinds that are *cheapest* to
convert: the TOC is text and rules, and the guide's primitives are lines,
rectangles, text, text measurement and **five arcs**. The only new primitive
across the entire interior is the **arc** (four Bézier `c` curves), and the one
element the guide pastes as an image is a **round mark** — which as four Bézier
curves is crisper than its rasterisation, and which ADR-0036/R4 already forbids
typing as a character precisely because of rendering.

**Text is the embedded font, not a substitute.** `DejaVuSans.ttf` is **379,441 B
FlateDecode, once per PDF — less than ONE raster page at 381,564 B** — so the
whole font is embedded and **glyph subsetting is deliberately not done**: it is
the expensive half of font work and it would save ~365 KB against a 9 MB file. A
PDF base-14 face is rejected because every `type_px` / `_band_font` /
`_guide_face` measurement in this tree is DejaVu's.

**Assertions read the written file.** An interior-page claim is made against the
content stream of the PDF that ships, not against a rendered bitmap. This is the
rule that retires ink measurement, and it is written as a rule so it cannot drift
back: measured on one test, the replacement is **41 lines against 168, 4.1×
smaller**, it needs no `pytest.approx`, no `CELL_PITCH_SLACK_MM`, no
`_RULE_SHARE`, and it **discriminates** — it passes at 0.48 pt and fails at
0.3 pt. `Sheet`'s independent-oracle role is untouched: it works in millimetres
and imports no geometry, so only the right half of the pairing changes, and it
gets *more* precise by losing `PX_PER_MM` rounding.

**Mixing is permitted per page, and is a stable end state rather than a
migration artefact.** Each PDF page is its own content stream, so a page that
turns out not to be worth converting may stay raster — declared, with its reason.
That is the sanctioned fallback if the pipeline diagram or the difficulty legend
proves gnarlier than measured.

## What this does NOT decide

**It does not set the rule weights, and ADR-0037 is not revised here.**

ADR-0037/R2's amended floor — "every thin grid rule is at least 0.169 mm" — was
set *because of* rasterisation, and this ADR makes it **inapplicable to the
interior**: in vector there is no device floor, and poppler measures the owner's
0.3 pt line at **2 px / grey 89 at 300 DPI and 5 px / grey 89 at 1200 DPI**, the
declared tone exact at both while the width scales with the device.

**But the owner has not yet seen the printed proof**, and ADR-0037 says in its own
words that these figures "become final only after the owner has seen them on
printed proof pages". Two things nobody can judge from a screen: **dot gain on
real uncoated stock**, and whether 35 % grey reads as *light guidance* or
*faded*.

So the separation is deliberate and it protects this decision:

* **The structural decision — draw the interior with operators — does not depend
  on the proof.** It is 22× smaller, 8.5× faster, allocates no page bitmap, and
  lets tests read the shipped file. Those hold whatever the proof shows.
* **The weights decision does depend on it**, and stays open. **CARD-227 is the
  card that holds it**, and its own arithmetic changes rather than just its
  tests: its 0.48/1.28/2.08 pt are the owner's figures ×1.6 *purely to clear
  2 px*, a correction with no meaning once there is no pixel to clear.
* **If the proof looks wrong, nothing in this ADR needs undoing.** Only the
  weights question stays closed, and the interior is still vector.

**Print `~/Documents/nonogram-reviews/CARD-293/card293-AC2-side-by-side.pdf` at
100 %** — the same 30×30 corner four ways at 1:1 — before ADR-0037 is revised.

## Alternatives considered

### A PDF library — reportlab, fpdf2, weasyprint (DEC-048)

Rejected, and the reason is that it was never needed. `export/svg.py` already
emits vector by hand with the docstring *"svgwrite or cairosvg would buy nothing
here and would reopen a dependency baseline"*, and — the load-bearing fact —
**`_write_pdf` already writes PDF object structure by hand** through
`PIL.PdfParser`. CARD-293's prototype produced a full 30×30 page with all 540
clue digits, rendered correctly by **poppler**, importing stdlib + Pillow +
`nonogram.export.layout` and nothing else. **ADR-0006/R1's baseline stays
closed.** A library would also have added a second geometry model beside
COMP-007's.

### Glyph subsetting (DEC-048)

Rejected on a measurement, not on effort. The whole font Flate-compresses to
379,441 B — **less than one raster page** — so a true subset's ~15 KB saves
~365 KB against a 9 MB file, for the `loca`/`glyf` rebuild and composite-glyph
closure that are the expensive half of font work. A table-stripped sfnt
(321,426 B, −58 KB, 28 lines) remains available and is also not worth it today.

### A base-14 font, needing no embedding (DEC-048)

Rejected: 0 bytes, but **the typeface changes**, and every type measurement in
this tree — `type_px`, `_band_font`, `_guide_face`, CON-020's 10 pt floor — is
DejaVu's. The saving is one font object against re-deriving every type figure in
the book.

### Vector for puzzle and answer pages only, raster for TOC and guide (DEC-048)

Rejected, and this was the owner's own open question on 2026-10-25. It keeps a
raster page writer, its ink-measurement apparatus and the DCT workarounds alive
**permanently**, to avoid converting the two **cheapest** page kinds. The
measured gap for the whole interior is one new primitive. Per-page mixing stays
available as a fallback (see the Decision), which is what this alternative was
really reaching for.

### Keep raster and live with the floor (DEC-048)

The status quo, and it has a real case: it ships, it is proven, and 171.7 MB
interiors are tolerable because KDP accepts them. Rejected because the floor is
not a cost but a **constraint on the product** — it already forced the refusal of
the owner's design, and the 2026-10-17 amendment records that it has removed the
one remaining lever (width) for distinguishing furniture from grid ink.

## Consequences

### Positive

- **The owner's design becomes printable.** 0.3 / 0.8 / 1.3 pt is expressible,
  measured exact in tone at 300 and 1200 DPI.
- **22.4× smaller interiors** (0.92 MB against 171.7 MB at 450 pages) and **8.5×
  faster generation** (1.37 ms/page against 11.7).
- **No page bitmap is ever allocated.** Retention falls from **1.00** to
  **0.000246** `PAGE_BITMAP_BYTES`. CARD-145's `del page`, its 2.00-vs-1.00
  equality and the OOM story become **vacuous rather than satisfied** on the
  interior.
- **Tests read the file that ships**, exactly, and are ~4× smaller. The
  in-memory-page workaround the DCT round trip forced goes away.
- **The TOC's page numbers become real text** — searchable for a reader, and
  machine-checkable against the plan without a render.
- Output is resolution-independent, so a change of trim or DPI stops being a
  re-rasterisation.

### Negative

- **The 21 `tests/fixtures/book_baseline_card*.json` recordings change.** This is
  routine rather than an owner decision: the board's practice, taken **twenty
  times**, is to record a NEW baseline superseding the old and naming what it
  supersedes (`card206 ← card224 ← card248 ← card223 ← card222 … ← card145`), so
  `tests/fixtures/**` is still never regenerated.
- **A phase of 5–7 cards behind this ADR**, of which the first should be the
  **guide** — it holds the only unpriced primitive, and a surprise belongs in
  card one rather than card six.
- **Of the 12 queued print-layout cards, 4 are rewritten** — CARD-227 (its
  decision, not just its test), CARD-208, CARD-215 (its AC literally says *"the
  dot is at least 1 device pixel across"*), CARD-226 — **6 are written with
  retargeted tests** (207, 209, 229, 230, 232, 233), **1 is untouched** (216),
  and **CARD-231 is written BORN VECTOR**: it redesigns the divider page, so it
  writes stream assertions from its first commit and retires R2's divider
  exception as it lands. That is cheaper than the retarget it would otherwise
  have been, and it is the owner's call of 2026-10-25 that made it so.
- **The non-puzzle pages were deliberately not priced** by CARD-293 (its G-3
  forbade building them). Lines, rectangles, text and five arcs is what a source
  reading suggests; **a call-level tally is owed and is the first card's job.**
- Pillow's `PdfParser` is a private-ish module. That risk is **already taken**
  since CARD-145, not newly incurred — but it is now load-bearing for more.

### Neutral

- **Pillow does not leave.** The cover, uploaded-image fitting, the PNG export,
  the CLI's PDF and the cover title face all still need it. This is not a
  dependency removal.
- **One or two rasterising smoke tests remain**, because a valid content stream
  can still be a broken PDF — a bad resource dictionary, a missing font. One or
  two, against 21 files today.
- **CON-019 is not at risk**, which was an early misreading worth recording: its
  statement covers *"the CLI's or the web UI's exports: for any generation
  request the PNG, SVG and PDF files **COMP-007** writes"*. A vector book
  interior is COMP-009 and touches no COMP-007 renderer.
  `tests/fixtures/a4_golden/` likewise captures `compute_layout` with **no
  PageSpec** plus the **CLI's** bytes, so ADR-0036/R1's golden is not reached.
- `ADR-0036/R2` is unchanged and becomes more important: a new writer is exactly
  where geometry gets re-derived by accident, which is why R3 below restates it.

## References

- **CARD-293** — the spike, its comparison document
  (`meta/profiling/card-293-vector-interior-comparison.md`) and its deliverables
  in `~/Documents/nonogram-reviews/CARD-293/`.
- **ADR-0037/R2** and its 2026-10-17 amendment — the device floor and the refused
  weights; **the motive, and the ADR this one constrains without revising**.
- **ADR-0036/R1, R2, R3, R4** — the A4 golden, geometry ownership, the round
  mark.
- **ADR-0006/R1** — the dependency baseline, which stays closed.
- **CARD-145** — `interior_stream`'s one-page-at-a-time contract and the
  hand-written `_write_pdf` this builds on.
- **CON-019**, **CON-018/NFR-008**, **CON-020**.

## History

- 2026-10-25: **Created.** Resolves DEC-048 (the book interior is drawn as PDF
  operators; the cover stays raster; the whole interior rather than a carve-out;
  the whole embedded font rather than a subset; assertions read the written
  file). Decided by the owner on CARD-293's measurements. **The rule weights are
  deliberately NOT decided here** — they wait on a printed proof, and ADR-0037's
  revision is a separate act. Three costs stated in CARD-293's brief were wrong
  in the project's favour and are corrected in this ADR: CON-019 and the A4
  golden are not at risk, the shipped rule widths are COMP-007's 3 px / 6 px
  rather than CARD-227's unlanded 0.48/1.28/2.08 pt, and the load-bearing
  precedent is `_write_pdf` itself rather than `export/svg.py`.

- 2026-10-25: **R7 discharged the same day it was written — the owner looked at
  the proof and chose their own 0.3 / 0.8 / 1.3 pt.** R7 deferred the grid's rule
  weights to a printed proof; the owner read `card293-proof-vector.pdf`
  (*"I looked at the pdf and I like it (vector versions)"*) and picked page 1,
  their artifact's unscaled figures, over page 2's x1.6-scaled 0.48 / 1.28 /
  2.08 pt. ADR-0037/R2 is amended with them. R7's statement was rewritten rather
  than left standing, because both of its operative clauses — "the weights wait"
  and "until ADR-0037 is revised, the interior ships the weights COMP-007
  computes today" — became false, and a rule that reads false is worse than one
  that is silent.

  **Two things worth keeping visible.** First, the ratios never moved: 1 : 2.667 :
  4.333 were the owner's in both candidates, and the x1.6 between them was an
  arithmetic correction for a device floor, not a design opinion — so removing it
  overturned no judgement. Second, the decision was made **on screen**, while
  ADR-0037's Decision section asks for paper; dot gain at 0.1058 mm and whether
  35% grey reads as guidance in print are still unmeasured, and that caveat now
  lives in ADR-0037's History with the first printed book as its revisit trigger.

- 2026-10-25: **Section dividers carved out of the interior scope before this ADR
  was committed** (owner, same session). Not a technique judgement: **CARD-231
  redesigns that page outright**, so the new design is born vector and the old
  one is never converted. Recorded here because it gave R2 its second declared
  instance and turned CARD-231 from a retarget into a born-vector card, and
  because the exception **expires when CARD-231 lands** — a declaration whose
  reason has gone is itself a defect under R2.

## Rules

```yaml
- id: ADR-0042/R1
  statement: >-
    Puzzle pages, answer pages, the table of contents and the guide are
    written as PDF content-stream operators. None of those pages references
    an image XObject, on any export path — the interior PDF, the proof sheet,
    or any future one. The cover and the section dividers are the declared
    raster exceptions and are governed by R2.
  scope: {code: ["src/nonogram/admin/**", "tests/**"]}
  check: {kind: review-lens}
  # PLANNED TEST, owed by the phase's first card:
  #   tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject
  # Flip this check to `kind: test` with that ref when the card lands, on
  # CON-020's precedent (2026-10-06, "was `kind: review-lens` ... CARD-184 wrote
  # it"). Held as a lens until then because a `kind: test` ref naming a test that
  # does not exist is read as mechanically checked by system_rules.py and
  # forge:review Step 8h: a card violating R1 would draw NO flag, which is
  # strictly worse than a lens, which at least makes a human look.
  severity: mandatory
- id: ADR-0042/R2
  statement: >-
    A page may be raster only where this ADR or a successor declares it with
    a reason. Two are declared: the COVER, because it is a photograph; and
    the SECTION DIVIDERS, because CARD-231 redesigns that page and the new
    design should be born vector rather than the old one converted. Per-page
    mixing is a sanctioned end state, not a migration artefact — each PDF
    page is its own content stream. A page that is raster without a
    declaration is a defect, and so is a declaration whose reason has expired:
    once CARD-231 lands, the divider's exception goes with it.
  scope: {code: ["src/nonogram/admin/**", "tests/**"]}
  check: {kind: review-lens}
  # PLANNED TEST, owed by the phase's first card (see R1's note on why this is a
  # lens and not a dead `kind: test` ref):
  #   tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason
  # Per ADR-0039/R2 that test must be DERIVED and default-DENY: a page whose
  # medium it cannot classify is a FAILURE, never a silent pass. The declared set
  # it checks against is {cover, section dividers} and shrinks to {cover} when
  # CARD-231 lands — the expiry in the statement above is the test's business.
  severity: mandatory
- id: ADR-0042/R3
  statement: >-
    The vector writer consumes positions and derives none. Every coordinate,
    width and tone it emits comes from COMP-007's Layout (or the pair-aware
    call for two-up pages) with the book's PageSpec; it computes no geometry
    of its own. This restates ADR-0036/R2 for the new writer, because a fresh
    renderer is exactly where geometry is re-derived by accident.
  scope: {code: ["src/nonogram/admin/**", "src/nonogram/export/**", "tests/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0042/R4
  statement: >-
    The PDF is written by hand through the object structure book_pdf_generator
    already drives, with no new runtime dependency. ADR-0006/R1's baseline —
    stdlib plus Pillow plus NumPy — stays closed; no PDF or font library is
    added. A library becomes necessary only by a new ADR.
  scope: {code: ["src/nonogram/**", "pyproject.toml"]}
  check: {kind: test, ref: "tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed"}
  severity: mandatory
- id: ADR-0042/R5
  statement: >-
    Interior text is the project's own DejaVuSans, embedded whole and
    FlateDecoded once per file. Glyph subsetting is deliberately not done (it
    saves ~365 KB against a file that was 9 MB), and a PDF base-14 substitute
    is forbidden because every type measurement in this tree — type_px, the
    band face, the guide face, CON-020's floor — is DejaVu's.
  scope: {code: ["src/nonogram/admin/**", "src/nonogram/export/**", "tests/**"]}
  check: {kind: review-lens}
  # PLANNED TEST, owed by the card that writes the font embedding (see R1's note):
  #   tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face
  severity: mandatory
- id: ADR-0042/R6
  statement: >-
    A claim about an interior page's geometry, rule widths or tone is asserted
    against the content stream of the written PDF, not against a rendered
    bitmap. Measuring ink to recover a number the generator stated exactly is
    forbidden for interior pages: it is a reconstruction, it needs tolerances,
    and today's pure-black assertions cannot even be made against the shipped
    file because the DCT round trip greys a rule's edges. Independent
    second-implementation oracles (Sheet and its kind) are unaffected and
    still compared against — only the reading of the artefact changes.
  scope: {code: ["tests/**"]}
  check: {kind: review-lens}
  # PLANNED TEST, owed by the card that converts the last interior pixel reader
  # (see R1's note on why this is a lens and not a dead `kind: test` ref):
  #   tests/test_book_pdf.py::test_no_interior_claim_is_made_by_measuring_ink
  # Derived and default-DENY per ADR-0039/R2 — it enumerates the interior pixel
  # idioms over tests/** rather than holding a hand-written list, and a test
  # shape it cannot classify is a FAILURE. Measured 2026-10-25, the live set it
  # must drive to empty: tests/property/test_book_export_interior.py (FR-043/
  # EC-034) at :731 `min() == 255`, :734 and :736 `same_page` on an INTERIOR
  # page, :848 the ink scan; tests/property/test_book_layout.py:364 and
  # tests/property/test_book_two_up.py:682, one `getpixel` probe each.
  # NOT in the set and must stay out of it: :652's `same_page` on the COVER,
  # which is raster by R2, and the independent oracles R6's statement exempts.
  severity: mandatory
- id: ADR-0042/R7
  # DISCHARGED 2026-10-25, hours after this ADR was accepted. This rule said
  # the weights "wait on a printed proof the owner has seen"; the owner looked
  # at the CARD-293 proof the same day, chose their own 0.3 / 0.8 / 1.3 pt over
  # CARD-227's x1.6-scaled 0.48 / 1.28 / 2.08 pt, and ADR-0037/R2 was amended
  # accordingly (see that ADR's History, 2026-10-25). The statement is rewritten
  # rather than left standing, because "the weights wait" and "until ADR-0037 is
  # revised, the interior ships the weights COMP-007 computes today" are both
  # now false, and a rule that reads false is worse than one that is silent.
  # One honest caveat carried forward: the owner judged the RENDERS, not paper.
  # Dot gain at 0.1058 mm and whether 35% grey reads as guidance in print are
  # still measured by nobody; the revisit trigger is the first printed book or
  # proof, and that lives in ADR-0037 now, not here.
  statement: >-
    This ADR does not set the grid's rule weights itself. What it does is make
    ADR-0037/R2's device floor inapplicable to the interior -- because a
    content-stream line has no device pixel to clear -- and nothing more. The
    weights are ADR-0037/R2's to state, and as of 2026-10-25 that rule states
    the owner's 0.3 / 0.8 / 1.3 pt, bound to the vector medium: the same
    figures through a raster generator round to 1 / 3 / 5 px, the one-pixel
    cell grid R2's 2026-10-17 amendment refused. So this ADR's removal of the
    floor is what made those figures available, and R2 is where they live.
  scope: {code: ["src/nonogram/export/**", "src/nonogram/admin/**"]}
  check: {kind: review-lens}
  severity: mandatory
```
