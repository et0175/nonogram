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
**Wave:** 38
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
  clue digits CON-020 exempts. (test: `TestInteriorType_EveryFaceHoldsTheFloor`
  — `tests/test_book_interior_type_floor.py:303` — and the four classes of
  `tests/test_book_guide_page_type.py`: `TestGuidePage_TypeIsBookSized`,
  `TestGuidePage_TextFitsTheUsableFrame`, `TestGuidePage_PointSizeIsIndependentOfDpi`,
  `TestGuidePage_LeadingClearsTheType`)
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
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed` and
  `::test_the_font_ships_as_package_data_and_not_as_a_dependency`.
  **`TestDependencyBaseline_IsExactlyPillowAndNumpy` is the architecture model's name for
  this rule and resolves to no test** — it appears only inside a comment block in
  `tests/test_export_pdf.py` that maps it to the two real tests above. Already logged in
  `backlog.md` under the architecture model's dead `check:` refs; corrected here so this
  card cannot inherit it.)
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

## Named tests resolved before the card started (decompose station, 2026-10-14)

Every backticked test name in this card was resolved against the test tree before an
agent saw it — the check CARD-205's gate showed was missing, where a fabricated guardrail
name survived drafting, implementation, a review and three fix cycles.

| name | resolves to |
|------|-------------|
| `TestInteriorType_EveryFaceHoldsTheFloor` | `tests/test_book_interior_type_floor.py:303` |
| `TestBookPdfMemory_PagesAreUnchanged` | `tests/test_book_pdf_memory.py:1230` |
| `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` | `tests/property/test_book_export_interior.py:582`, as `test_PropertyTest_…` (this project's property-test naming) |
| `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` | `tests/property/test_cli_exports_byte_identity.py`, same convention |
| `test_the_gaps_leave_the_folio_its_line_on_every_trim_kdp_admits` | `tests/test_book_toc.py:1166` |
| `test_the_shortest_trim_still_prints_its_folio_with_the_gaps_in_place` | `tests/test_book_toc.py:1309` |
| `TestBookGuidePageType_*` | **did not exist** — corrected above to the four real `TestGuidePage_*` classes in `tests/test_book_guide_page_type.py` |
| `TestDependencyBaseline_IsExactlyPillowAndNumpy` | **resolves to nothing** — corrected above to the two real tests it maps to |
| `TestBookInterior_GeometryIsIdenticalWithAndWithoutHostFonts` (AC-1) | **to be written by this card.** It does not exist and is not expected to: it is the new determinism test. Say so when you report it; do not report it as passing before you have written it |

AC-6 names no test on purpose — it is verified by review against the measurements this
card records.

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

---

### Implementation agent's own records (verbatim, synced from the worktree 2026-10-14)

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


### Implementation, 2026-10-14 (agent)

**[What was changed]** `_guide_face` (`src/nonogram/admin/book_pdf_generator.py:1093`) now
returns the packaged DejaVu Sans — `ImageFont.truetype(BytesIO(_band_font_bytes()),
size=size)`, the same bytes `_band_font` reads through `importlib.resources` — instead of
the host's Arial by path with Pillow's built-in face as a fallback. No escape hatch: the
interior's whole repertoire is ASCII plus U+00B7, U+2014, U+2013 and U+2026, and the
packaged face carries all four (asserted glyph by glyph). Uncached, as the call it
replaces was, because the guide title's fit loop probes many sizes.

**[The measurement that makes the swap worth it]** Exactly the seven pages that lettered
through `_guide_face` moved (1, 2 guide; 3 TOC; 4, 6, 8, 10 dividers); the other six are
byte-identical to CARD-205's digests. Interior bytes 3,498,430 -> 3,369,113.

#### Every measurement taken

| what | Arial (host, before) | Pillow built-in (off-host, before) | packaged DejaVu (after) |
|------|------|------|------|
| TOC row, 10 pt (asc+desc @42 px) | 48 px | 51 px | **49 px** |
| TOC title line (asc+desc @92 px + 150 px gap) | 254 px | 262 px | **258 px** |
| folio line (`_band_font` @42 px) | 49 px | 49 px | 49 px (unchanged — always packaged) |
| TOC capacity, Book 1 (3075 px frame) | 42 rows | 40 rows | **41 rows** |
| TOC capacity, 10.00 cm (956 px frame) | 10 rows | 9 rows | **9 rows** |
| TOC capacity, 10.10 cm (967 px frame) | 10 rows | 9 rows | **10 rows** |
| 8 rows + 4 gaps headroom @10.00 cm | 59 px (ok) | 27 px (folio dropped) | **47 px (folio dropped, 2 px short)** |
| same @10.10 cm | 70 px (ok) | 38 px (dropped) | **58 px (ok)** |
| 381-height sweep, heights that fail | 0 | 2 (10.00, 10.10) | **1 (10.00 only)** |
| guide page 2 captions form, Book 1 | bottom 3115 / frame 3188 (fits) | 3119 (fits) | **3192 (overflows by 4 px)** |
| guide page 2 chosen form, Book 1 | captions | captions | **labels** |
| guide page 2 last form, 10.00 cm | 93 px under the frame (folio drawn) | — | **18 px (folio omitted)** |
| ink-to-em, "Hg" cap-to-descender @400 px | 0.9275 | — | 0.9375 |
| ink-to-em, "dg" ascender-to-descender | — | — | 0.9675 |
| "1" digit top-to-baseline / em | 0.72 | — | 0.730 |
| guide pages vs the CARD-200 stored JPEGs | — | — | 7.596% / 11.442% of pixels differ; 254,766 / 581,547 not explained by a 1 px displacement |

Largest group gap the packaged face fits at 10.00 cm: **8.2 pt (34 px, 51 px headroom)**;
8.0 pt (33 px) restores a 6 px margin, which is the owner's own "largest that fits, less a
margin" rule applied to the new metrics. Not applied — G-6.

#### Gates removed, each with the measurement that retires it

- `tests/helpers/book_corpus.py`: **`font_fingerprint()` and `MACHINE_FACE_SIZES` deleted.**
  Condition (interior pixels depend on the host's fonts) is gone: `tests/test_book_interior_face.py`
  exports the baseline book and the 10x10 cm book twice in one process, with the host's
  Arial available and with `ImageFont.truetype` refusing every host path, and finds every
  page digest, the page count, the interior byte length and the KDP gutter band identical.
- `tests/test_book_pdf_memory.py`: both `same_face` fixtures, every `if ... not same_face:
  continue`, the `pytest.skip` on the byte-length test, and the `warnings.warn` about
  incomplete evidence. All 13 pages are now compared on every machine (was 6 off-host).
- `tests/test_book_toc.py`: `_lettered_as_recorded()` and the two figure gates it carried.
- `tests/fixtures/book_baseline_card221.json`: `font_dependent_pages` is `[]` (kept as an
  explicit empty list, not dropped, so a future host lookup has to declare itself);
  `font_fingerprint`/`font_fingerprint_note` are absent.
- **Deleted, not re-anchored:** `test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement`
  plus `_one_pixel_displacement_outliers`, `_GUIDE_SCATTER_SHARE_CEILING`,
  `_GUIDE_SCATTER_GREY_TOLERANCE`. It bounded CARD-204's *sub-pixel* scatter against the
  CARD-200 recording; across a face change the deviation is 7.6%/11.4% of the page with
  254k/581k pixels no 1 px displacement explains. Re-anchoring at this card's own pages
  was tried first and is impossible by that test's own design: its `moved > 0` assertion
  exists to stop the bound being measured against nothing. Replaced by the new baseline's
  own per-page digests (stronger, and unconditional). The two JPEG fixtures stay (G-5) and
  are still read by `test_the_guide_pages_are_the_documented_exception_not_an_unbounded_one`,
  which inherited their integrity check.

#### Gates kept or added, with what is still host-dependent

- **Added, one:** `host_offers_a_second_face()` in `tests/test_book_interior_face.py` gates
  the negative control `test_the_comparison_can_tell_the_pre_card_face_from_this_one`. That
  test restores the pre-card lookup and asserts the interior's pages *differ* between a
  host with Arial and one without; on a machine with no host Arial (the Linux image, or
  this suite under the off-host plugin) both runs resolve the same face and there is
  nothing to contrast. The gate is above every assertion in that test because the whole
  test is the contrast. Everything else in the file is ungated.
- **Still host-dependent, outside this card:** `BookPDFGenerator.create_cover_page` asks
  the host for Arial at 72 px for a *generated* title cover. The cover is a separate file
  (INV-013), no baseline digests it, and `MACHINE_FACE_SIZES` deliberately never covered
  its 72 px. Two machines will still produce different generated covers. Recorded below as
  work outside this card.
- Pillow's own embedded face (clue digits, `ImageFont.load_default`) is a dependency's
  package data, not the host's; every fixture in the chain already treated it as
  machine-independent, and `pyproject.toml`'s unbounded `Pillow>=10.0` is the only way it
  could move.

#### Mutants

| # | mutant | killed by | what it shows |
|---|--------|-----------|---------------|
| M1 | `_guide_face` restored to the Arial-by-path lookup (inside the claim) | `test_book_interior_face.py` 3 of 10 tests (both determinism tests + the no-host-path watch) and 5 in `test_book_pdf_memory.py` | the new file's claims are about the real face, not a tautology |
| M2 | packaged face at `size + 1` — still deterministic, wrong size (the claim's **edge**) | `test_book_pdf_memory.py` (5), `test_book_interior_type_floor.py` (1), `test_book_guide_page_type.py` (3) — and **not** `test_book_interior_face.py`, which stays green | the new file claims host-independence and not correctness of the size; names which tests hold the other half |
| M3 | `BAND_SEPARATOR` -> U+2E0E, a glyph DejaVu lacks (inside the repertoire claim) | `test_the_recorded_repertoire_is_what_the_interior_draws` | the repertoire list is read off a real export, not transcribed |
| M3b | `BAND_SEPARATOR` -> U+2022, a glyph DejaVu **has** (the claim's edge) | same test | an unlisted character fails even when the face covers it, which is what makes the coverage test exhaustive |
| M4 | `TOC_GROUP_GAP_PT` 8.5 -> 9.0 (inside the folio claim) | the sweep and the new 10.10 cm rendered test | the new green folio guard has teeth |
| M4b | `TOC_GROUP_GAP_PT` 8.5 -> 8.2 (the blocked claim's edge) | both strict `xfail`s report `XPASS(strict)` -> red | the escalation self-corrects the moment the owner moves the constant |

M4b first flipped only one of the two markers: the rendered one kept failing on its pinned
47 px, so its "strict" promise was false. Fixed in the follow-up commit by moving that
figure into the 10.10 cm test; re-run of M4b then flipped both. Every mutant reverted with
`git checkout --` and `git status --porcelain -- src tests` verified empty after each.

#### What this card could NOT close (two owner decisions, both measured)

1. **Book 1's guide page 2 loses six lines of text, over 4 px.** The packaged face is ~10%
   wider, one paragraph wraps into one more line, and the captions form's last mark lands
   at 3192 px against a frame bottom of 3188 — so `create_guide_page`'s ladder drops to the
   labels form and the reader loses the worked example's four captions, the two technique
   notes and the difficulty box's three sentences. Rendered for the owner (see below); the
   page now ends a quarter of the way up the sheet. Carried by a strict `xfail` on
   `tests/test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyBox::test_the_difficulty_box_carries_its_three_sentences_verbatim`.
   G-1 forbids this card the wording, the sizes' derivation and the layout. Options for the
   owner: accept the shorter page; a sixth ladder level between captions and labels
   (dropping the difficulty sentences alone buys 234 px and fits with room to spare); or a
   narrower packaged face, which is an ADR-0006/R1 question, not a code one.
   **Note while this is red:** `test_a_wrong_difficulty_sentence_does_not_match` has no
   teeth — nothing on the page matches either box now.
2. **AC-4 cannot be met at the 10.00 cm trim: 2 px.** 47 px of headroom against the folio's
   49. One height of 381 (10.10 cm clears it at 58). `TOC_GROUP_GAP_PT` <= 8.2 pt closes
   it; G-6 forbids it. Two strict `xfail`s carry it, and the sweep still asserts, ungated,
   that 10.00 cm is the *only* failing height and that its deficit is exactly 2 px.

#### Also true, outside this card

- The **generated title cover** still reads the host's Arial at 72 px
  (`create_cover_page`). Same defect class, different file; worth its own card.
- `fits_width` is false for *every* fallback form of guide page 2 at the 10x10 cm trim on
  both faces — the loop exhausts the ladder and draws the last form anyway. Pre-existing,
  not touched here.
- `GUIDE_PAGE_COUNT` (test_book_pdf_memory), `page_digest` (test_book_guide_page),
  `Sequence` (test_book_guide_page_type) and `InkMode` (book_pdf_generator) are imported
  and unused on `main`; left alone.
- **Candidate ADR, as the card flags:** "the interior's typography is deterministic — every
  face it measures comes from packaged data, never from a host lookup". The cover is the
  one place that rule is not yet true, which is an argument for writing it down.

#### Renders for the owner

`~/Documents/nonogram-reviews/CARD-221/` — 16 PNGs, `<trim>__<page>__<face>.png`, at
one third scale. Both trims (Book 1 21.59x27.94 cm, minimum 10.00x10.00 cm), both guide
pages, the Easy divider and the contents page, each in `packaged-dejavu` (what ships now)
and `host-arial-before` (what this Mac printed before). The two pairs that matter:
`book1-21.59x27.94cm__guide-page2__*` (the six lost lines) and
`min-10.00x10.00cm__contents__*` (the "3" in the bottom corner, present before, gone now).

- [Implementation complete, with two owner blocks] 2026-10-14 — `9862ecd` (the swap) and
  `4c0dc26` (a fix-up a mutant exposed) on `card/221-packaged-interior-face`.
  **The card's purpose is achieved:** `_guide_face` returns the packaged DejaVu Sans, there is
  no escape hatch (the interior's repertoire is ASCII + U+00B7/U+2014/U+2013/U+2026 and the
  packaged face carries all four, asserted glyph by glyph), and AC-1 proves determinism by
  exporting the same books twice in one process — host Arial available, then
  `ImageFont.truetype` refusing every host path — with all 13 page digests, the page count, the
  byte length and the KDP gutter band identical. Exactly the seven pages lettered through
  `_guide_face` moved (1, 2 guide; 3 TOC; 4, 6, 8, 10 dividers); the other six are byte-identical
  to CARD-205's digests. `interior_bytes` 3,498,430 -> 3,369,113. Impact scope: **on-host 2515
  passed / 1 skipped / 3 xfailed; off-host 2514 / 2 skipped / 3 xfailed** — the same tree, the
  same result, on both faces, which is the whole point of the card.
- [Gating machinery removed, with measurements] `font_fingerprint()`, `MACHINE_FACE_SIZES`, both
  `same_face` fixtures and every skip they drove, `_lettered_as_recorded()`;
  `font_dependent_pages` is now `[]`. `TestBookPdfMemory_PagesAreUnchanged` compares all 13 pages
  unconditionally. One gate **added** where a condition genuinely remains
  (`host_offers_a_second_face()`, above the one negative control that needs two distinguishable
  host faces), and one place left host-dependent and flagged rather than silently swept in:
  **`create_cover_page` still reads the host's Arial at 72 px** for a generated title cover —
  separate file, no baseline digests it. That is the one spot where the card's candidate ADR
  ("the interior's typography is deterministic") would not yet be true, and it wants its own card.
- [Removed rather than re-anchored, and why] `test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement`
  and its instrument are gone. It bounded a **sub-pixel** scatter (CARD-204's 0.183% / 0.192%,
  0 displacement outliers); across a face change the deviation is 7.596% / 11.442% with 254,766 /
  581,547 unexplained pixels, and the test's own `moved > 0` anti-vacuity assertion makes
  re-anchoring impossible. Deleting a guardrail needs saying out loud, so: this one measured a
  property that no longer exists, not a property that stopped being checked.
- [Correction to this card's own text] The card says `main` shows "10 failures off-host, all in
  `test_book_finalise_gutter.py`". That figure was taken **before CARD-205 merged**. On `main` as
  merged, `test_book_finalise_gutter.py` is already 126/126 off-host — CARD-205's structural TOC
  removed those page-count failures by construction — and the 3 remaining off-host failures are
  all in `tests/test_book_toc.py` (the two folio tests, plus
  `test_a_nearly_full_row_still_gets_the_dots_that_do_fit`, whose premise held only by Arial's
  metrics). The card was accurate when written and is stale now; the branch fixes all three.
- [Two type-floor probes were wrong, not the type] Two `TestGuidePage_*` classes went red on the
  new metrics because their **measuring probes** under-measure: a cap-to-descender `"Hg"` probe
  under-reads on any face whose ascender clears cap height (the body read 11.52 pt while set at
  11), and the folio's digits under-read against an ascender probe (10.00 pt read as 9.79).
  Fixed with `ASCENDER_TO_DESCENDER_PROBE` and a new `folio_reference()` / `folio_band()`, so
  each band is now measured against the probe of the line that actually drew it. Worth keeping in
  mind for CARD-227 and CARD-233: a type measurement is only as good as its probe, and these two
  had been green for the wrong reason since CARD-184.
- [BLOCKED 1 — G-1 breached at Book 1 by 4 px, and it costs the guide its teaching]
  The packaged face is ~10% wider; one paragraph of guide page 2 wraps onto one more line; the
  captions form's last mark lands at **3192 px against a frame bottom of 3188**, so the drawing
  ladder drops to the labels form. Carried by `xfail(strict=True)` at
  `tests/test_book_guide_page.py:1138`. **Checked by eye against the renders, and the summary
  "six lines of text" understates it** — comparing
  `book1-21.59x27.94cm__guide-page2__host-arial-before.png` with `…__packaged-dejavu.png`, what
  is lost is: technique 1's explanation ("The one-cell region cannot hold 2 or 3."), technique 2's
  note ("Compare"), **all three difficulty descriptions** (so the difficulty box becomes three
  bare words, EASY / MEDIUM / HARD, in an otherwise empty ruled box), the worked example's intro
  line, and **all four step explanations** — "1. The clue" where the Arial page reads "1. The clue
  3 1 means a run of 3 filled squares, then at least one empty square, then a run of 1." The page
  then ends a quarter of the way up the sheet. The guide stops teaching and looks unfinished.
  **This collides with a card cut the same day:** CARD-230 specifies "the worked example runs as
  four small steps, **each with one line saying what changed**" — exactly the four lines this
  drops. Accepting the loss would ship a page that the next card in the queue has to undo.
  Measured option: dropping the difficulty box's three sentences alone buys **234 px** against a
  4 px deficit, and CARD-229 moves the difficulty legend into the guide's key strip anyway, which
  makes those three sentences the most redundant text on the page.
  While the test is red, `test_a_wrong_difficulty_sentence_does_not_match` has no teeth.
- [BLOCKED 2 — AC-4 at the 10.00 cm trim, 2 px] On the packaged face the shortest storable trim's
  eight rows and four 8.5 pt gaps leave **47 px** where the folio needs **49**, so that one page
  prints unnumbered **on every host**. 380 of the 381 swept heights clear it (10.10 cm at 58 px).
  The sweep is now **ungated** and asserts exactly that 10.00 cm is the only failing height and
  the deficit is 2 px; the blocked claim is split into two `xfail(strict=True)` tests
  (`tests/test_book_toc.py:1341` and `:1415`) with the measurement in the reason, and a new green
  guard covers the tightest trim that does work (10.10 cm, 58 px). `TOC_GROUP_GAP_PT <= 8.2 pt`
  closes it; **8.0 pt restores a 6 px margin — which is the owner's own rule from 2026-10-14
  ("the value that leaves ~10 px over the folio's need") re-applied to the new metrics.** G-6 put
  that constant out of scope, so it is the owner's to move.
- [Both blocks, one root cause] The only packaged face is ~10% wider than Arial. Both are
  escalated with strict, self-correcting markers: fix the cause and the markers `XPASS(strict)`
  and fail, so neither can be forgotten.
- [Mutants] 6 run (M1, M2, M3, M3b, M4, M4b), all reverted, `git status --porcelain -- src tests`
  empty after each. Worth recording: **M4b first flipped only one of the two strict markers** —
  the rendered one kept failing on a pinned 47 px figure, which made its "strict" promise false.
  `4c0dc26` moved that figure into the 10.10 cm test so both flip together. A strict xfail that
  cannot pass is a worse guard than no guard.
