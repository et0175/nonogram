# CARD-221: The book interior letters in the packaged face, so its geometry stops depending on the host

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/221-packaged-interior-face
**Worktree:** ../PythonProject4-CARD-221
**Source:** CARD-205 review cycle 1 finding F-004, then a dedicated measurement round (2026-10-14); owner decision 2026-10-14 — keep CARD-205's 8.5 pt and card the root cause instead, having confirmed that book PDFs are generated **both** locally and through the deployed panel
**Idea:** —
**Wave:** 37
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-205
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/export/fonts/, tests/test_book_toc.py, tests/test_book_pdf_memory.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_interior_type_floor.py, tests/test_book_finalise_gutter.py, tests/helpers/book_corpus.py, tests/fixtures/
**Review score:** —
**Started:** 2026-10-14T14:20:00Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The defect, stated as a fact about the product rather than about tests: the same book
can get a different page count — and therefore a different printed KDP gutter margin —
depending on which machine finalises it.**

`_guide_face` resolves Arial **by path on the host** (`ImageFont.truetype(".../Arial.ttf")`
with a `load_default` fallback), and every reader-facing interior face except the band
goes through it: the guide pages, the dividers, the TOC rows. The folio's own reservation,
by contrast, comes from the **packaged** face. So the interior's row geometry is a
function of what fonts the machine happens to have, while the space reserved for the page
number is not.

**Measured consequences (2026-10-14, by rendering with `ImageFont.truetype` made to
refuse the Arial path so `_guide_face` takes its documented fallback):**

- TOC rows-per-page capacity is **42 on Arial and 40 on the fallback** for Book 1's trim
  (9 vs 10 at the 10.00 cm trim).
- On `main`, where the TOC lists one row per puzzle, an 83-row TOC therefore takes **2
  pages on Arial and 3 on the fallback**. Since the interior page count chooses the gutter
  band, **main's printed gutter decision is face-dependent.**
- `main`'s own suite shows it: **10 failures off-host**, all in
  `test_book_finalise_gutter.py`, all page-count scenario constants off by exactly one
  page (151 vs 150, 493 vs 492, 682 vs 681) plus the gutter-band and refusal wording that
  follows from the count.
- CARD-205 removes the TOC's share of this by construction (its list is 8 rows and one
  page on both faces at every trim — 3 off-host failures instead of 10), but the guide
  pages, the dividers and the type floor are untouched by it.
- The owner confirmed on 2026-10-14 that books are finalised **both** locally (Arial
  present) and through the deployed panel (this repo's own notes record Arial as absent
  from the Linux image), so the two paths can legitimately disagree today.

**What to do.** Letter every reader-facing interior face in the **packaged** font that
already ships in `src/nonogram/export/fonts/` — the one the band and the folio already
use — so that every measurement the interior makes is deterministic:

1. Replace `_guide_face`'s host lookup with the packaged face. Keep one deliberate
   escape hatch only if a glyph genuinely is not covered, and if so name the glyph and
   the fallback in a docstring rather than leaving a silent `try`.
2. **Re-verify CON-020's 10 pt floor against the new metrics.** The packaged face's
   advance widths and ascent/descent differ from Arial's, so every fitted face in the
   interior must be re-measured against the floor —
   `tests/test_book_interior_type_floor.py` is the test that holds it, and
   `TestBookGuidePageType_*` holds the guide's own derived sizes. A face swap that
   silently pushes a fitted size under 10 pt would be a worse defect than the one this
   card fixes.
3. **Re-record the affected baselines**, as deliberate recordings with provenance naming
   this card and the pages that moved. Every `font_dependent_pages` entry moves by
   definition. Do NOT delete or regenerate any earlier fixture in the chain.
4. **Shrink the host-gating machinery it makes unnecessary.** `font_fingerprint`,
   `font_dependent_pages` and `MACHINE_FACE_SIZES` exist because interior pixels depend
   on the host (the mechanism dates to CARD-146/147). State explicitly, in the card's
   notes and in the tests' docstrings, which gates can now go and which must stay —
   anything still genuinely host-dependent (e.g. a face the packaged font does not
   cover) keeps its gate. Removing a gate whose condition still holds would make the
   suite red on some machine; leaving one whose condition is gone is dead weight that
   hides the next real gap.
5. **Re-run the two off-host sweeps CARD-205 built** and report them: the 381-height
   folio-clearance sweep and the page-count agreement across the three
   `measured_toc_page_count` callers. After this card, CARD-205's own two red-off-host
   tests should be green on both faces at the shipped 8.5 pt — that is the cleanest proof
   this card worked, and it is why this card depends on CARD-205 rather than racing it.

## Acceptance criteria

- **AC-1** (happy, determinism): *Given* any book in the corpus, *when* its interior is
  exported with the host's Arial available and again with `ImageFont.truetype` refusing
  that path, *then* every page's digest, the interior's page count and the chosen gutter
  band are identical between the two runs. (test:
  `TestBookInterior_GeometryIsIdenticalWithAndWithoutHostFonts`)
- **AC-2** (happy, the gutter): *Given* the gutter scenarios in
  `test_book_finalise_gutter.py`, *when* they run with the host's Arial refused, *then*
  all of them pass — the 10 page-count failures `main` shows off-host are gone. (test:
  `test_book_finalise_gutter.py`, run under the off-host plugin)
- **AC-3** (guard, the type floor): *Given* every face the interior fits, *when* it is
  measured on the packaged font, *then* none is below CON-020's 10 pt floor except the
  clue digits CON-020 exempts. (test: `TestInteriorType_EveryFaceHoldsTheFloor`,
  `TestBookGuidePageType_*`)
- **AC-4** (happy, CARD-205's sweeps): *Given* the 381-height folio-clearance sweep and
  the three-caller page-count agreement, *when* each runs on both faces, *then* both pass
  on both — including the 10.00 and 10.10 cm trims that drop the folio today. (test:
  `test_the_gaps_leave_the_folio_its_line_on_every_trim_kdp_admits`,
  `test_the_shortest_trim_still_prints_its_folio_with_the_gaps_in_place`)
- **AC-5** (happy, baselines): *Given* the re-recorded fixtures, *when* the baseline
  comparison runs, *then* it passes, each recording names this card and the pages that
  moved, and no earlier fixture in the chain is modified. (test:
  `TestBookPdfMemory_PagesAreUnchanged`)
- **AC-6** (happy, the gating shrinks honestly): *Given* the host-gating machinery, *when
  the card is reviewed*, *then* every removed gate is justified by a measurement showing
  its condition no longer holds, and every retained gate names what is still
  host-dependent. (verified by review against the recorded measurements)

## Guardrails

- G-1: The text the interior prints is unchanged — this card changes the FACE, never the
  wording, the sizes' derivation rule, or the layout (test: the guide-page content tests).
- G-2: CLI and web-UI exports stay byte-identical (CON-019). They draw no guide page, but
  prove it rather than assume it (test:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-3: `src/nonogram/export/layout.py` is not edited — this is a face decision, not a
  geometry one (ADR-0036/R2 keeps placement in COMP-007, and placement is not changing).
- G-4: No new runtime dependency and no new font file beyond what already ships in
  `src/nonogram/export/fonts/` (ADR-0006/R1). Packaged font data is package data, not a
  dependency — that distinction is already in ADR-0006/R1's own text.
- G-5: No earlier baseline fixture is regenerated or deleted; the chain's "NEVER
  regenerate" warnings stand (CARD-217's finding: the superseded recordings are
  referenced only from docstrings and cost no runtime).
- G-6: Out of scope — CARD-205's 8.5 pt constant (the owner kept it deliberately), and
  the admin panel's own screen typography (this card is the printed interior).

## System contract

- CON-020 — no reader-facing interior text below 10 pt except puzzle-page clue digits
  (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- CON-018 — the Book 1 trim profile the figures are measured on (check: review-lens)
- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy; non-executable
  static assets may ship as package data and that is not a dependency change (check:
  `TestDependencyBaseline_IsExactlyPillowAndNumpy`)
- ADR-0036/R2 — page geometry is computed only by COMP-007's layout functions (check:
  review-lens)
- INV-013 — the interior holds no cover page; parity is the 1-based interior position
  (check: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)

## Architecture context

- **FR:** FR-043 (the interior's pages and folios), FR-016 (the printable page), NFR-008
  / FR-031 (the cell floor the type floor sits beside).
- **NFR:** CON-020's floor is the reader-facing constraint this card must not breach.
- **ADR:** ADR-0036/R2, ADR-0006/R1. **Candidate for a new rule:** "the interior's
  typography is deterministic — every face it measures comes from packaged data, never
  from a host lookup." If review agrees, that belongs in an ADR rather than in this
  card's notes, and the architect station already owes a pass for FR-040/EC-027,
  FR-032 and FR-043's TOC half.
- **CON:** CON-018, CON-019, CON-020.
- **Components:** COMP-009 (`book_pdf_generator.py`), COMP-007 only insofar as the
  packaged font data lives under `export/` (no layout change — G-3).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- [Why this is P1 rather than tidy-up] The owner confirmed on 2026-10-14 that books are
  finalised BOTH locally and through the deployed panel. Two machines, two faces, and a
  page count that selects the printed gutter: a book proofed here and the same book
  generated on Render can disagree about their gutter margin. CARD-205 narrows that to
  the non-TOC pages; this card closes it.
- [Depends on CARD-205 deliberately] CARD-205's two off-host red tests are the cleanest
  available proof that this card worked — they fail precisely where a contents page would
  print unnumbered on the fallback face, and they should go green on both faces at the
  shipped 8.5 pt once the interior letters deterministically. Racing CARD-205 would lose
  that signal and collide in the same file.

