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

- 2026-10-29: **The medium is now chosen per page, and the declared set is
  seven rather than two** (CARD-298). `_write_pdf` takes one `PageKind` per
  planned page and asks `page_medium` — the module's single decision point,
  held to one place by an AST guard — so the object table is laid out per
  medium, the face is embedded once per file and only when some page is
  vector, and a page that arrives in the other medium's representation is
  refused rather than written. Mixed files work and are measured.

  **What this card could not do, and why it matters to the phase's order.**
  No interior page ships as operators, because three things block it and all
  three were measured rather than estimated (R1's note below carries the
  figures): the test tree's readers require a DCTDecode image on every page of
  every book PDF, so converting even the blank title page reds 112 cells —
  that conversion is R6's, owned by CARD-299, which means **R1's card depends
  on CARD-299 and not the reverse**; `book_puzzle_vector` draws no sheet
  furniture, so a vector puzzle page would print with no page number;
  and three of the four vector page writers import `book_pdf_generator`, so
  the interior's own walk cannot call them. **The 21 book baselines therefore
  did not move**, which is the opposite of what CARD-298's brief predicted and
  is recorded here because the next card will predict it again: the baselines
  move when R6 lands, not when the medium decision does.

  **One gap AC-1 named and this card did not close**: the proof sheet
  (`book_proof.render_proof_pdf`) writes through `Image.save(save_all=True)`,
  a second writer with no page kinds behind it, so it is outside the medium
  decision. Held where it can be seen —
  `tests/test_book_pdf.py::test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision`
  asserts both halves, so the note cannot go stale.

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
  # The test now EXISTS and is green:
  #   tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject
  # **CARD-298 deliberately did NOT flip this check, and the reason is a
  # measurement.** That test asserts the equivalence "every page is the medium
  # its kind declares", page by page over the plan, and it is derived and
  # default-DENY. It is NOT the statement above: as of CARD-298 every interior
  # page kind is a DECLARED raster exception (see R2 and
  # `book_pdf_generator._RASTER_DECLARATIONS`), so the sentence "puzzle pages,
  # answer pages, the table of contents and the guide are written as PDF
  # content-stream operators" is false of every book this product ships.
  # Flipping the check would mark a rule as mechanically checked by a test that
  # passes while the rule is violated — the exact defect repaired in `c12c33ce`
  # and again in ADR-0032/R3, arrived at from the other direction.
  #
  # Three blockers, each measured by CARD-298, and the first is the one that
  # fixes the ordering:
  #
  #   1. **The readers.** `tests/helpers/pdf_pages.py` asserts "a book page is
  #      exactly one image" and requires a DCTDecode XObject on EVERY page of
  #      every book PDF; 60 call sites across 14 test modules read a book
  #      interior through it. Converting the single cheapest page kind — the
  #      blank title page, whose two media draw the same page by construction —
  #      reds **59 failures and 53 errors, 112 cells**, in the impact-scoped set
  #      alone (measured 2026-10-29 on this branch, `KeyError: b'XObject'` and
  #      `'ContentStream' object has no attribute 'tobytes'`). That conversion
  #      is R6's, owned by CARD-299. **So R1's own card depends on CARD-299 and
  #      not the other way round**, which is the opposite of the order the
  #      kanban cut them in.
  #   2. **The puzzle page's furniture.** `book_puzzle_vector` draws no sheet
  #      furniture at all — no folio, no frame rules, no grid-size label, no QR
  #      block — which that module's own docstring raises as a gap "not drawn by
  #      any card in the ADR-0042 phase". A vector puzzle page today prints with
  #      no page number on it.
  #   3. **The layering.** `book_guide_vector`, `book_toc_vector` and
  #      `book_answer_vector` all import `book_pdf_generator` at module level,
  #      so the interior's own page walk — which lives in that module — cannot
  #      call three of the four vector page writers. The assembly point for a
  #      vector interior is downstream of all of them and does not exist yet.
  #
  # Flip this check when the statement is true of a shipped interior, i.e. when
  # the five temporary entries in `_RASTER_DECLARATIONS` are gone.
  severity: mandatory
- id: ADR-0042/R2
  statement: >-
    A page may be raster only where it is declared with a reason, on a named
    authority, and with the card that removes it. The declarations are
    `nonogram.admin.book_pdf_generator._RASTER_DECLARATIONS` — that mapping is
    the authority, and this rule's business is that every bitmap page in a
    written file matches a live entry in it. Two entries are this ADR's own:
    the COVER, because it is a photograph, permanently; and the SECTION
    DIVIDERS, because CARD-231 redesigns that page and the new design should be
    born vector rather than the old one converted. Per-page mixing is a
    sanctioned end state, not a migration artefact — each PDF page is its own
    content stream. A page that is raster without a declaration is a defect,
    and so is a declaration whose reason has expired: once CARD-231 lands, the
    divider's exception goes with it.
  scope: {code: ["src/nonogram/admin/**", "tests/**"]}
  check: {kind: test, ref: test_every_raster_page_is_declared_with_its_reason}
  # FLIPPED FROM review-lens 2026-10-29 by CARD-298, in CARD-298's own feature
  # commit — the precedent R5 sets in this same file (CARD-294, `0c63a328`) and
  # CARD-227's ADR-0037/R2 flip in `7d86a869`. Both flipped in the commit that
  # wrote the test; neither waited for a merge. The ref is written as the BARE
  # test name for the reason R5's note measures at length: the validators'
  # `split_check_ref` splits on COMMAS only, so a `file::name` ref is handed to
  # `git grep -lw` as one literal symbol and resolves to nothing. Re-measured
  # on this very edit, on this branch, with the validator's own pathspec:
  #   git grep -lw "tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason" \
  #     -- . ":(exclude)meta/architecture" ":(exclude)*.md"   -> rc=1, 0 files
  #   git grep -lw "test_every_raster_page_is_declared_with_its_reason" \
  #     -- . ":(exclude)meta/architecture" ":(exclude)*.md"   -> tests/test_book_pdf.py
  # and end to end through the validator of record: the node-id spelling took
  # this tree from 107 warnings to 108, the added one being "ADR-0042/R2 ...
  # DEAD check ref"; the bare name leaves the warning SET byte-identical at 107.
  # So the node-id spelling would have flipped the lens into something strictly
  # worse than a lens, and this spelling is the honest one.
  #
  # The test EXISTS and is green, derived and default-DENY per ADR-0039/R2
  # (a page whose medium it cannot classify is a FAILURE, never a silent pass).
  # The three node ids, spelled here in the COMMENT where no search reads them:
  #   tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason
  # with the expiry clause as its own criterion —
  #   tests/test_book_pdf.py::test_a_declaration_whose_reason_expired_is_a_defect
  # and swept over a seeded corpus by
  #   tests/test_book_pdf.py::test_PropertyTest_Interior_RasterPagesEqualDeclaredRasterPages
  # This ref resolves and the test checks exactly this statement, so unlike R1's
  # the flip is honest.
  #
  # What the ref does NOT reach, stated because the rule's own clause depends on
  # it: the guard sees a declaration go stale in TWO directions, and they were
  # closed by two different cards. The CONVERSION direction (a page became
  # vector while its declaration stayed) is `test_a_declaration_whose_reason_
  # expired_is_a_defect`, CARD-298's original work. The LANDING direction — this
  # statement's own wording, "once CARD-231 lands, the divider's exception goes
  # with it" — was UNGUARDED at CARD-298 review cycle 1 and is closed by
  #   tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it
  # with its control over a synthetic board at
  #   tests/test_book_pdf.py::test_a_declaration_outliving_its_done_card_is_a_defect
  # which read the expiry card's `**Status:**` out of meta/kanban/cards/. What
  # that reads is that the CARD is done, not that the CONVERSION happened: a card
  # closed without converting its page still reds (which is the mis-attribution
  # cycle 1 found), and a page converted by a card that is still open is caught
  # by the conversion direction instead. Between them the two directions are
  # total over the ways an entry can go stale; neither alone is.
  #
  # **The statement was amended by CARD-298, and the amendment is the finding.**
  # It used to read "Two are declared"; the registry holds SEVEN. The five
  # additions are the interior kinds this ADR means to be vector and which
  # measurably cannot be yet — see R1's note for the three blockers, each of
  # which is named in the reason of every entry it blocks. The count is
  # deliberately not restated as a number in this statement: the registry is
  # the authority, the entries carry their own reasons and owners, and a count
  # in prose beside a mapping in code is the drift CARD-261 found twice.
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
  check: {kind: test, ref: test_the_interior_embeds_the_projects_own_face}
  # The node id is tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face.
  #
  # FLIPPED FROM review-lens 2026-10-25 by CARD-294, the card that wrote the
  # font embedding, in the same change as the test — on CON-020's precedent
  # (2026-10-06, "was `kind: review-lens` ... CARD-184 wrote it"). The lens
  # was a placeholder for exactly this card, and merging with it in place
  # would have shipped a rule whose delivery card was closed and whose check
  # was still a placeholder (CARD-294 G-8).
  #
  # WRITTEN AS THE BARE TEST NAME, not as the `file::name` node id the lens's
  # old comment named, and the difference is not cosmetic: the validators'
  # `split_check_ref` splits a ref on COMMAS only, so a `file::name` ref is
  # searched for by `git grep -w` as one literal symbol and finds nothing —
  # which reports the rule as a DEAD check ref, the state the model treats as
  # strictly worse than a lens. Measured on this very edit: the node-id
  # spelling added exactly that warning, the bare name clears it. Every other
  # live `kind: test` ref in this model is a bare name for the same reason.
  # (R4 above is spelled as a node id and is *not* flagged — by coincidence,
  # and CARD-294 round 1 understated how wide the coincidence is. Measured
  # under the validator's own pathspec, `code_search` excluding the arch root
  # and all `*.md`:
  #   git grep -lw "tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed" \
  #     -- . ":(exclude)meta/architecture" ":(exclude)*.md"
  # returns 54 TRACKED files — meta/kanban/backlog-scored.yml, four
  # meta/profiling/*.txt, 48 meta/review/*.yml and tests/test_admin_serving.py
  # — and 55 with `--untracked`, the extra being CARD-294's own cycle-1 review
  # report, which was untracked when the reviewer measured it. NONE of them is
  # a definition: the only `def` is tests/test_export_pdf.py:1249, and the
  # node-id spelling does not resolve to it.
  # The latent harm is a false *alive*: delete or rename
  # `test_the_dependency_baseline_is_still_closed` and R4 goes on reading as a
  # live, mechanically-checked ref forever — the standing rule about honest
  # check refs seen from the other side, on AC-5's own declared check. The fix
  # is deleting the 26-character `tests/test_export_pdf.py::` prefix. It was
  # left outside CARD-294 and is recorded here for whoever next touches R4.)
  #
  # What the ref reaches, and what it does not. The test makes R5's three
  # claims — embedded, embedded ONCE per file, and no base-14 reference —
  # against a PDF written by `nonogram.admin.book_vector`, comparing the
  # embedded bytes to the face `importlib.resources` returns. The per-page
  # slope those claims rest on (a face embedded per page would also be
  # "exactly one per page") is
  # tests/test_book_pdf_vector_primitives.py::TestPropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts,
  # and the control that each claim can fail is
  # tests/test_book_pdf.py::test_the_face_check_above_can_fail.
  #
  # That node id was DEAD as first written. CARD-294's review cycle 1 (F-1)
  # measured the class it named — then spelled `class PropertyTest_…` — as
  # collecting ZERO tests, because this repository configures no
  # `python_classes` and pytest's default `Test*` applies. The slope, the
  # 24-book corpus and the corpus's own "a per-page face would be caught"
  # control all silently did not run, and the ref read as live. The class is
  # now `TestPropertyTest_…` (the spelling
  # tests/test_print_specs.py::TestPropertyTest_TrimInchesShown_InsideLimitsAndAccepted
  # already uses), the file collects 52 tests where it collected 35, and
  # tests/test_collected_names.py is the guard that makes the next
  # uncollectible test-declaring name in tests/** FAIL instead of pass. The
  # node id above was verified by running it, not by a green total.
  #
  # It does NOT yet reach a real interior page, because no page is drawn with
  # this vocabulary yet — CARD-295/296/297 are the page cards. When the first
  # of them lands, this ref should be re-read against the shipped interior
  # rather than against the vocabulary's own file; the rule is unchanged, the
  # artefact it is asserted on grows.
  severity: mandatory
- id: ADR-0042/R6
  statement: >-
    A claim about an interior page's geometry, rule widths or tone is asserted
    against the content stream of the written PDF, not against a rendered
    bitmap. Measuring ink to recover a number the generator stated exactly is
    forbidden for interior pages: it is a reconstruction, it needs tolerances,
    and today's pure-black assertions cannot even be made against the shipped
    file because the DCT round trip greys a rule's edges. Two kinds of claim
    are DECLARED EXEMPT, and each is exempt for a reason that names what it
    could not otherwise assert. First, independent second-implementation
    oracles (Sheet and its kind) are unaffected and still compared against —
    only the reading of the artefact changes. Second, a claim about what the
    DEVICE does with a declared width or tone — that two distinct declared
    widths resolve to distinguishable rendered widths, that none drops out,
    that a declared tone survives — is asserted on a render, because the
    content stream is precisely the thing it does not test: reading 0.3 pt back
    out of the operator that set it says nothing about whether 0.3 pt is
    visible. Such a claim must state the resolution it was measured at and must
    not be used to recover a width the generator stated.
  scope: {code: ["tests/**"]}
  check: {kind: review-lens}
  # CARD-299 (2026-10-29) was dispatched to flip this check to the planned test
  # named below and DID NOT, and the refusal is four measurements rather than
  # caution. CARD-298 refused R1's flip for the same class of reason and was
  # right; this is the same refusal one rule along.
  #
  #   1. **Two of the six sites this comment names are not interior PDF
  #      readings at all.** `tests/property/test_book_layout.py:364` renders
  #      through `nonogram.export.png.render_image`, and
  #      `tests/property/test_book_two_up.py:682` builds a bare `PIL.Image` and
  #      calls `png._draw_grid` / `png._draw_clues` directly. Neither writes a
  #      PDF, so neither has a content stream to be asserted against, and both
  #      are COMP-007's drawing surface — which CARD-299's own G-4 and CON-019
  #      put outside ADR-0042's reach. A guard built from this enumeration
  #      would be built from a wrong set.
  #   2. **The enumeration disagrees with the census by 50x.** Re-derived with
  #      `meta/profiling/adr-0042-migration-census.md`'s own two regexes on
  #      main at `4ce84c30`: **34 files, 321 sites**. This comment names 6.
  #      Both are cited as this rule's authority and they are not the same set.
  #   3. **The census is stale in the direction that matters.** It records
  #      **32 files / 315 sites** at `c12c33ce` (2026-10-25); the same
  #      derivation reads **34 / 321** at `4ce84c30` four days later. The
  #      migration surface GREW by 2 files and 6 sites during the phase that
  #      exists to shrink it.
  #   4. **An idiom count cannot measure "the set is empty".** CARD-299's own
  #      correct conversion of this comment's three real sites RAISED
  #      `tests/property/test_book_export_interior.py` from **8 to 13** idiom
  #      occurrences — the medium-gated helpers and their non-dormancy controls
  #      are themselves matches — while making the assertions exact. So the
  #      census idiom count moves the wrong way on a conversion, and a guard
  #      ratcheting it would red on the work it exists to encourage.
  #
  # What CARD-299 landed instead, and why it is the instrument this rule wants:
  # the three real sites are now read in the medium `page_medium` declares for
  # the page's kind (bitmap arm = today's assertion, stream arm = R6's exact
  # one), with a page the classifier cannot classify a FAILURE per ADR-0039/R2,
  # and with the stream arm proved non-dormant on a real vector page written by
  # production's own writer. The same shape landed on CON-020's floor check.
  # That is a RUNTIME property — "this claim was read in the medium its page
  # was written in" — and it is why a static enumeration over `tests/**` is the
  # wrong instrument: which page a `getpixel` lands on is not an AST fact.
  #
  # Flip this check when a card owns the guard as its subject. It is its own
  # card: a 321-site surface, a per-site disposition, and the conclusion-keyed
  # device-fact discriminator below (the `==`-against-a-declared-width versus
  # bracketing distinction, which is decidable but is a static-analysis card of
  # its own) are not a sub-item of a reader conversion.
  #
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
  #
  # SECOND EXEMPTION ADDED 2026-10-25, when the owner's grid weights landed.
  # FR-033/AC-374 and CARD-227's AC-5/AC-6 assert that the three declared
  # widths resolve to distinguishable rendered widths, that none drops out, and
  # that grey 89 survives at 300 and 1200 DPI. Those claims CANNOT be made
  # against the content stream — reading 0.3 pt back out of the operator that
  # set it says nothing about whether 0.3 pt is visible — and they are the
  # claims the whole 0.3/0.8/1.3 decision rests on. They are therefore exempt,
  # and the exemption is declared here rather than left for the guard's author
  # to discover, because CARD-299's R6 guard is default-DENY over tests/** and
  # would otherwise fail on `TestBookGridRules_WeightsSurviveTheFloor` and
  # `TestBookGridRules_PointsNotPixels`.
  # Per ADR-0039/R3 an exemption is a claim and carries a control for what it
  # must NOT absorb: this one must not absorb a test that reads a STATED width
  # off a render. The discriminator is what the assertion concludes — "these two
  # render differently" and "this tone survives" are device facts; "this line is
  # 0.3 pt" is a stated number and belongs to the stream.
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
