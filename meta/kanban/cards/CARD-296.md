# CARD-296: The guide page as operators — the worked example, the legend's dots and the diagram, the phase's one unpriced page

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/296-guide-page-as-operators
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-296
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 4 — *"This is the largest card and the one the spike deliberately did not price."* Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 61
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_difficulty_dots.py
**Review score:** —
**Started:** 2026-10-26
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Read this first: this is the card the spike refused to price

CARD-293's §6 named it twice. Item 4 of its scope list — *"The non-puzzle pages …
**This is the largest card and the one the spike deliberately did not price**
(G-3): the prototype draws one puzzle page, not a page plan"* — and again in the
recommendation: *"a phase of 5–7 cards, of which **one** … is not priced here and
could be large."*

**So the estimate on this card is a guess, and that is stated rather than
hidden.** Two consequences the implementation agent should act on:

1. **CARD-294 prices the curve primitive before this card starts** (its AC-3),
   because the difficulty-legend dots are the one interior shape nobody has
   emitted. Read CARD-294's recorded figure before planning this page. If curves
   turned out expensive, say so and raise it — do not absorb the cost silently.
2. **If this page turns out to be two cards, that is a finding, not a failure.**
   Raise it at the decompose station (`scope_gate` is `on`, and a card whose diff
   grows past its slice escalates here by design) instead of running six review
   cycles on an over-stuffed card. Splitting is cheap at kilometre zero and
   expensive at cycle four.

## What to implement

The guide — the book's "How to Solve" page, today a raster bitmap — drawn as PDF
content-stream operators. Its parts, as the page stands now:

1. **The worked example** — the small grid, its clues, and the marks the example
   fills in. This is a miniature of CARD-295's puzzle page and should reuse that
   card's grid drawing rather than growing a second copy of it.
2. **The difficulty legend's dots** — the round shapes. **This is the card's one
   genuinely new primitive**, and CARD-294 priced it. A dot is not a rectangle:
   PDF has no circle operator, so it is cubic Béziers via `c`.
3. **The explanatory body text** and headings, in the embedded face.
4. **The pipeline diagram**, if the page still carries one — lines, arrowheads
   and labels.

Everything positioned from COMP-007's `Layout` with the book's PageSpec
(ADR-0042/R3). The guide is a page of the interior like any other.

## Acceptance criteria

- **AC-1** (the guide carries no bitmap): *Given* an interior whose guide is
  written by this card, *then* the guide page references no image XObject. (test:
  `TestGuidePage_CarriesNoImageXObject`.)
- **AC-2** (every face still holds the 10 pt floor — and the check can see it):
  *Given* the vector guide, *then* every face it prints for the reader is at
  least 10 pt, **asserted against the content stream's `Tf` sizes**. (test:
  `TestGuidePage_EveryFaceHoldsTheFloorInTheStream`.)
  **This is the card's sharpest obligation, because the existing guard goes
  blind here.** CON-020's `TestInteriorType_EveryFaceHoldsTheFloor` works by
  spying on `ImageDraw.ImageDraw.text` (`tests/test_book_interior_type_floor.py:233,
  :261`) and a vector guide makes no such call. Its floor assertion at `:353` is
  `below_floor(...) == []`, which is **vacuously true on an empty recording**.
  What saves it is the sibling at `:355` asserting
  `{"guide","divider","band","footer label","answer caption"} <= kinds`: the
  moment `guide` stops being drawn, **that test reds loudly**. Expect it to fail,
  and understand before you touch it that the red is the tripwire working. The
  registry-level rewrite of CON-020's check is **CARD-299's**; this card's job is
  to make the *guide's* floor assertable in the new medium and to leave that
  sibling's non-vacuity floor intact for the kinds still raster.
- **AC-3** (the dots are round, at the size the legend states): *Given* the
  difficulty legend, *then* each dot renders as a filled round shape of the
  stated diameter, read back by an **independent** engine (poppler). (test:
  `TestGuidePage_DifficultyDotsAreRoundAtTheStatedDiameter`.)
- **AC-4** (the worked example is the same grid drawing, not a second one):
  *Given* the worked example's grid, *then* it is drawn through CARD-295's grid
  routine, and a structural check shows no second grid implementation in the
  file. (test: `TestGuidePage_WorkedExampleReusesTheGridRoutine` — derived per
  ADR-0039/R2 from the module's AST, default-DENY: a drawing path it cannot
  classify is a FAILURE, not a pass.)
- **AC-5** (a clue digit on the guide is NOT exempt from the floor): *Given* the
  worked example's clue digits, *then* they hold the 10 pt floor. CON-020's
  clue-digit exemption is **exactly** `png._draw_clues` and
  `book_pdf_generator._write_clues` (CARD-184 AC-3) — *"a worked-example clue
  digit on the guide page is NOT exempt"*, in the constraint's own words. (test:
  `TestGuidePage_WorkedExampleClueDigitsAreNotExempt`.)

## Engineering constraints

- **EC(ADR-0042/R3):** the guide writer derives no geometry, in any book profile
  — including the 10×10 cm minimum trim, where the page has least slack and a
  fallback is most tempting. test:
  `PropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims`.
- **EC(CON-020):** every reader-facing face on the vector guide holds 10 pt at
  both the Book 1 profile and the minimum trim. test: AC-2's test over both
  profiles (the two books `tests/test_book_interior_type_floor.py` already
  parameterizes as `book` and `min-trim`).

## Guardrails

- **G-1: do not redesign the guide.** CARD-229 makes it a facing spread on pages
  2 and 3; CARD-230 runs the worked example as four steps. **Both are queued and
  both are gated.** This card ports **today's** design to the new medium,
  unchanged, so that those two cards are then written against a vector page from
  the start — which is the whole reason the phase runs before them.
- **G-2: do not touch the dividers.** Raster by owner decision 2026-10-25 —
  *"I'd left dividers out for now - I think I can come out with a 'nicer' design
  for them"*. CARD-231 redesigns that page and is born vector. Note the
  consequence for AC-2: `divider` is one of the kinds the `:355` sibling requires,
  and it must keep being drawn and recorded.
- **G-3: do not touch the cover.** Raster by ADR-0042/R2 — a photograph.
- **G-4: do not edit `src/nonogram/export/**`.** The `Layout` is consumed.
- **G-5: do not rewrite CON-020's registry check.** That is CARD-299's, and doing
  it here splits one re-expression across two cards. Make the guide's floor
  assertable; leave the constraint's `check:` alone.
- **G-6: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-7: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated.
- **G-8: probes stay OUT of `tests/`** — the `RENDER_HEAVY_SNAPSHOT` grep
  (`meta/profiling/rank_durations.py:45`, asserted equal to a 33-entry snapshot at
  `tests/test_suite_profile.py:482`) reds the suite on a new `tests/` file naming
  `create_guide_page`. Use `scripts/` or the scratchpad.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject (check: review-lens → CARD-298)
- ADR-0042/R2 — a raster page needs a declaration with a live reason; the dividers' expires with CARD-231 (check: review-lens → CARD-298)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt; the clue-digit exemption is two named functions and does NOT reach the guide's worked example (check: TestInteriorType_EveryFaceHoldsTheFloor)
- INV-013 — the guide spread's page positions and the interior/cover separation (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived and default-DENY; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-038, FR-043 (the interior without the cover; the guide's page position)
- **NFR:** NFR-005, NFR-006
- **ADR:** ADR-0042 (R1, R2, R3), ADR-0036/R2, ADR-0039/R1-R2
- **Components:** COMP-009; COMP-007's layout consumed
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- **INV-013 has a dead test ref in the model** — it names seven tests, of which
  `TestGuideSpread_SitsOnPagesTwoAndThree` does not exist (the validator reports
  it). It is CARD-229's to write. Do not write it here to clear a warning: this
  card does not move the guide to a spread (G-1), so a test asserting it sits on
  pages 2 and 3 would be asserting CARD-229's design.
- `src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot` — this card
  and CARD-295 share the same wave and will serialize on it.

## [Routed in from CARD-294 cycle 2 — 2026-10-26, N-2] `_cap_height`'s uncontrolled branches — yours, because you run first

**This was first written onto CARD-295 and that was wrong.** The orchestrator
routed it there calling CARD-295 "the first card that centres strings on
`FontMetrics`". Wave 61 is ordered **guide-first**, so you run before CARD-295,
and your own item 3 draws *"the explanatory body text and headings, in the
embedded face"* — so you are the first consumer both by schedule and by what you
draw. The note is corrected here and CARD-295 now points at you. Recorded rather
than silently moved, because a control that drifts to the card that runs second
is a control the first card ships without.

CARD-294 fixed a real **10.8 %** error in `_cap_height`
(`src/nonogram/admin/book_vector.py`): `font_metrics` fell back to
`0.7 × ascender`, and the bundled DejaVuSans ships `OS/2` **version 1, 86 bytes,
with no `sCapHeight` at all**, so the fallback was *always* what shipped —
**650**/1000 em where FreeType measures **729**. It now reads `H`'s own
`glyf`/`loca` bounding box and reproduces FreeType exactly. The pre-existing
poppler control had absorbed the error because its tolerance is 15 % and the
error was 12.2 % — worth knowing before you trust a tolerance of your own.

**What CARD-294 did NOT control**, measured by its cycle 2: the function has
three reachable paths and the shipped face exercises exactly one (`OS/2` v1;
`indexToLocFormat` **1**, long `loca`). Uncontrolled are the **`OS/2 ≥ 2`
branch** — which CARD-294's card *states* as behaviour, "version ≥ 2 still wins
where a face has it" — the **short-`loca`** branch, and **both raises**. All were
judged correct on review, so this is missing controls rather than missing
behaviour. One residual hole is real: **a v2+ face with `sCapHeight = 0` returns
0 with no fallback and no error** — a silent zero in the number your headings
are set against.

If you set type on `cap_height`, the cheapest honest control is a synthetic face
per branch (a v2 `OS/2` carrying a real `sCapHeight`, one carrying `0`, and a
short-`loca` face) rather than a comment asserting the branches work. CARD-294's
own cycle-1 critical finding was a control that could not fail, and its cycle-2
N-1 was a figure whose scope was hand-held; this is the same family twice over.

**If you decline these controls, say so with a reason and name who owns them** —
CARD-295 is the obvious inheritor — rather than passing them on silently.
