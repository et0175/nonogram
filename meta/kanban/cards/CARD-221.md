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

### Implementation agent's own records (verbatim, synced from the worktree 2026-10-14, all cycles)

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
- **`tests/test_book_interior_type_floor.py` — kept whole, and it is the one file this
  inventory missed in cycle 0** (review cycle 1, F-007). It has no gate: `without_arial`
  (`:261`) is a helper, not a skip, and nothing in the file is conditional. But since the
  swap that helper cannot change anything the interior draws, so
  `TestInteriorType_FloorHoldsWithoutArial` (`:326`) now measures the same recording as
  `TestInteriorType_EveryFaceHoldsTheFloor` (`:303`). Kept as deliberate redundancy and
  said so in its own docstring: it costs one export per book and it is what fails first
  if a host lookup returns *to the drawing*, where this card's structural watch only sees
  `ImageFont.truetype`'s argument. `test_arial_really_is_unavailable` is still a real
  test of the helper.
- **What no gate covers, on any machine** (review cycle 1, F-005): the Pillow/FreeType
  build. `pyproject.toml` floors Pillow at `>=10.0` with no ceiling and every figure in
  this card comes off `getmetrics()`, so a FreeType bump can still move a row's height
  and with it a page count — the same lever Arial pulled. AC-1 therefore guarantees
  "identical on one Pillow/FreeType build with the host's font paths refused", not
  "identical on any machine", and both `_guide_face`'s docstring and
  `tests/test_book_interior_face.py`'s now say exactly that. What would catch such a move
  is the baseline: all thirteen pages are compared digest-for-digest with no face gate
  left to skip them, so it reds the suite on the machine that bumped it. Bounding Pillow
  (or recording the metrics) is an ADR-0006/R1 question for the architect station.

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

#### What this card could NOT close — three, all now ruled on by the owner

*(Written in cycle 0 with two open items; both were ruled on 2026-10-14 and are recorded
as closed here rather than left describing a branch that no longer exists. The third was
found by review cycle 1 and is the only one still standing — accepted, not fixed.)*

1. **CLOSED by the owner.** Book 1's guide page 2 lost six lines of text over 4 px (the
   captions form's last mark at 3192 px against a frame bottom of 3188, so the ladder
   dropped a whole level). Ruling: drop the difficulty box's three sentences — 234 px
   against that 4 px — and everything else prints again. See "Fix cycle 1, Block 1".
2. **CLOSED by the owner.** The 10.00 cm trim's TOC page was 2 px short of its folio at
   8.5 pt. Ruling: `TOC_GROUP_GAP_PT` 8.5 → 8.0, which is their own "largest gap that
   fits, less a margin" re-measured on the packaged face. 55 px, 6 px clear, no failing
   height. See "Fix cycle 1, Block 2".
3. **OPEN, AND ACCEPTED BY THE OWNER (2026-10-14): at the 10.00 cm minimum trim this card
   takes the folio off GUIDE page 2.** Raised by review cycle 1 as F-002; I had the
   measurement in cycle 0's table and failed to escalate it beside its own sibling, the
   TOC page at the same trim, which became Block 2.

   **The measurement.** Same book (one 20x20 puzzle at the 10x10 cm trim), same process,
   only `_guide_face` swapped:

   | face | interior pages | folios drawn | missing |
   |---|---|---|---|
   | host Arial (pre-card) | 7 | **[2, 3, 4, 6]** | [1, 5, 7] |
   | packaged (HEAD) | 7 | **[3, 4, 6]** | [1, 2, 5, 7] |

   The arithmetic behind it: at that trim *no* fallback form of page 2 fits, so the ladder
   exhausts and draws its last (bare level 2) regardless — which ends **18 px** inside the
   frame on the packaged face where it ended 93 px inside on Arial, against the **49 px**
   `_draw_folio` needs for its own line. 75 px of that 93 is what the wider face costs.
   Two renders a reader can check it against, both already in
   `~/Documents/nonogram-reviews/CARD-221/`:
   `min-10.00x10.00cm__guide-page2__host-arial-before.png` carries a "2" in its
   bottom-left corner and `min-10.00x10.00cm__guide-page2__fix1-packaged-dejavu.png` does
   not. Recorded in the suite as a fact rather than a bound:
   `tests/test_book_page_numbers.py`'s min-trim test asserts the missing set **exactly**
   (`== {1, 2, blank_puzzle_page, answer_page}`), where it was a `<=` bound before.

   **The 8.0 pt ruling does not recover it, and could not have.** That constant is the
   TOC's group gap; it never reaches a guide page. And at 10 cm the ladder had already
   fallen to its bare form, which never printed the difficulty sentences either — so
   Block 1's 234 px buys nothing here. Measured on HEAD, after both rulings: still 18 px.

   **Why the owner accepted it, in their own terms.** The guide is already unprintable at
   that trim on both faces, and in two independent ways, both measured at HEAD: no fallback
   form of page 2 passes `fits_width` there (all five fail, so the ladder exhausts and
   draws its last regardless of the horizontal overflow), and page 1's chosen form ends
   **212 px past the bottom margin** — 111 px of actual ink past it — on either face. So
   the folio this card drops sits on a page no book can ship at that trim either way, and
   Book 1, the real product, is untouched. The honest one-line framing: *a 10 cm book's
   guide pages were already broken, and this card also takes page 2's number.*

   (Two measures are in play and they are not interchangeable: the 18 px / 93 px / 212 px
   figures are the ladder's own `bottom` — the last mark's box, which is what
   `_draw_folio` is handed as `content_bottom` and what decides the folio — while the
   111 px is where ink actually lands. The folio decision uses the first.)

   **Recorded beside it, because it may come back and it is not this card's to do:** the
   owner was also offered **raising the profile's minimum storable trim from 10.00 cm to
   10.10 cm**, where everything fits — 66 px of folio clearance on the TOC page, and the
   guide's own ladder measured at the next height up. They turned it down for now. It is
   worth keeping on the record because it would make *both* folio problems at that trim
   stop existing, including the one Block 2 moved `TOC_GROUP_GAP_PT` for, and because it
   is a one-constant change to CON-018's floor (`MIN_TRIM_CM`) — which belongs at the
   **architect station**, not in this card.

#### Also true, outside this card

- The **generated title cover** still reads the host's Arial at 72 px
  (`create_cover_page`). Same defect class, different file; carded as CARD-234. Review
  cycle 1 (F-009) sharpened what that card is for, and the sharper version is the one to
  carry: its fallback at `:3262` is a **bare `load_default()` with no size**, so off host
  the cover's title is lettered at Pillow's 10 px em where 72 px was asked for — the
  CARD-149 defect verbatim, not merely "a different face". The two `_guide_face` siblings
  were given sized fallbacks cards ago; this one never was.
- `fits_width` is false for *every* fallback form of guide page 2 at the 10x10 cm trim on
  both faces — the loop exhausts the ladder and draws the last form anyway. Pre-existing,
  not touched here.
- `GUIDE_PAGE_COUNT` (test_book_pdf_memory), `page_digest` (test_book_guide_page),
  `Sequence` (test_book_guide_page_type) and `InkMode` (book_pdf_generator) are imported
  and unused on `main`; left alone.
- **Candidate ADR, as the card flags:** "the interior's typography is deterministic — every
  face it measures comes from packaged data, never from a host lookup". The cover is the
  one place that rule is not yet true, which is an argument for writing it down. If it is
  written, it should say *packaged data on a pinned rasteriser*: `pyproject.toml` floors
  Pillow at `>=10.0` with no ceiling, and a FreeType bump moves `getmetrics()` the same
  way a missing Arial used to (review cycle 1, F-005). The baseline comparison is what
  would catch it; bounding Pillow is the architect station's call.
- **Raising `MIN_TRIM_CM` from 10.00 to 10.10 cm** would retire both folio problems at the
  minimum trim at once — the TOC page Block 2 moved a constant for, and the guide page
  item 3 accepts. Offered to the owner and declined for now; a one-constant change to
  CON-018's floor, so it belongs at the architect station. Recorded in full under item 3.

#### Renders for the owner

`~/Documents/nonogram-reviews/CARD-221/` — 24 PNGs, `<trim>__<page>__<face>.png`, at one
third scale. Both trims (Book 1 21.59x27.94 cm, minimum 10.00x10.00 cm) x both guide
pages, the Easy divider and the contents page x three states: `host-arial-before` (what
this Mac printed before the card), `packaged-dejavu` (the face swap alone, before the
owner's rulings) and `fix1-packaged-dejavu` (what ships). The three that matter:
`book1-21.59x27.94cm__guide-page2__*` — the six lines lost in the middle state and back
in the last, less the three difficulty sentences and their rule;
`min-10.00x10.00cm__contents__*` — the "3" in the bottom corner, present before, gone in
the middle state, back at 8.0 pt; and `min-10.00x10.00cm__guide-page2__*` — the "2" in
the bottom-left corner, present before and gone in both later states, which is the
accepted item 3 above.

### Fix cycle 1, 2026-10-14 (agent) — the owner ruled on both blocks

Both blocks were decided by the owner, not by this card, and neither by accepting the
loss. Recorded here as decisions carried out, not as guardrails overridden: G-6 put
`TOC_GROUP_GAP_PT` out of scope and the owner has now moved it, and G-1's "the text the
interior prints is unchanged" is satisfied by the owner choosing which text changes.

#### Block 1 — the guide page keeps everything but the difficulty sentences

`GUIDE_DIFFICULTY_LABELS`' three glosses stop being printed. 234 px bought against a 4 px
deficit, so page 2's captions form fits again and the reader gets back both technique
notes ("The one-cell region cannot hold 2 or 3.", "Compare"), the worked example's intro
line and all four step explanations — the four CARD-230 specifies as "four small steps,
each with one line saying what changed". Verified by re-rendering and reading the page's
own draw calls: 16 lines on page 2 where the pre-ruling render had 11.

**The rule goes with the sentences — my decision, stated as asked.** A `measure`-wide
ruled rectangle holding three words (about a seventh of its own area), directly under a
heading that promises an explanation, reads as a table whose contents failed to draw; that
is the "unfinished" failure the ruling warned against, and it is worse than no rule.
Nothing else on either guide page borders anything it does not enclose — the pipeline's
four boxes each hold a word and an icon, every line diagram's frame holds a grid. Three
names in a row under their own heading read as the legend they are, which is also the
shape CARD-229 moves into the key strip. Rendered both ways before deciding
(`~/Documents/nonogram-reviews/CARD-221/`).

Two consequences of dropping the rule, both handled rather than left:

- `_draw_difficulty_box` is renamed `_draw_difficulty_legend` — a function named for a box
  it no longer draws is the kind of false claim this project does not keep — and loses the
  `spec`, `leading` and `with_text` parameters it only needed for the rule and the
  sentences.
- **The labels are now flush with the measure.** With the border gone, the box's `pad` of
  inner margin would have left EASY indented 46 px from a left edge nothing draws, out of
  line with the heading directly above it and with every other line on the page. The
  columns keep their pitch and start at the measure's own left edge; the `pad` of white
  above and below stays, because that is the one piece of the box's geometry still doing a
  job. Caught by eye on the render, not by a test.

**Tests whose subject this moved, each handled by name rather than deleted:**

| test | what happened |
|------|----------------|
| `test_the_difficulty_box_carries_its_three_sentences_verbatim` (the strict xfail) | converted to an ordinary passing `test_the_difficulty_legend_carries_its_three_labels_and_no_sentences` (`tests/test_book_guide_page.py:1189`), which asserts **both** directions: the three labels print, and the bordered sentence box prints nowhere on the page |
| `test_a_wrong_difficulty_sentence_does_not_match` | re-aimed, not retired: `test_a_wrong_difficulty_label_does_not_match` (`:1245`) — the verbatim claim lives on the labels now, so its negative control follows it. It also asserts that changing a *sentence* changes nothing drawn, which is the new fact stated from the other side |
| `test_a_regression_shrinking_a_boxs_label_text_is_still_caught_by_the_floor_check` (F-4's control) | re-aimed at `_draw_pipeline_diagram`, the guide's remaining bordered drawing with text inside it, and made two-sided (6 pt reads below the floor, the page's real 11 pt reads above it). Keeping it aimed at a drawing the module had stopped making would have been the quieter failure |
| `test_page_two_pipeline_and_difficulty_box_align_at_book1`, `test_page_two_difficulty_box_aligns_at_narrower_trims`, `test_a_diagram_shifted_left_by_pad_is_not_at_frame_left` (F-11's three) | the legend is still an image pasted `needs_pad=False`, so F-11's claim still covers it; only the *measurement* had to move, because an unruled block is a band of type rather than a diagram. New `legend_ink_extent`/`assert_legend_is_flush` find it by its own ink and assert exactly one line of type has that extent. Diagram counts 12 → 11 (Book 1) and 3 → 2 (narrow trims) |
| `drawn` fixture (`tests/test_book_guide_page.py`) | 12 → 11 bands, with the reason and the index shift recorded in its own message |

**Flagged, not fixed (out of scope, G-6):** the Finalise screen's preview
(`templates/book_finalize.html`) still shows the three sentences, so that screen and the
page it previews now disagree. `DifficultyLabel.text` is deliberately kept for exactly that
reason plus CARD-229's key strip. **CARD-229 must reconcile the two surfaces** — if the
owner wants them in step sooner it is a one-line template change plus
`test_the_difficulty_box_carries_the_three_sentences_verbatim` in
`tests/test_book_finalise_guide_preview.py:622`.

#### Block 2 — `TOC_GROUP_GAP_PT` 8.5 → 8.0 pt (owner decision)

The owner's own rule — "the largest gap that fits, less a margin" — re-measured on the
face the book is actually printed in. Re-run of the 381-height sweep on the packaged face:

| constant | px | worst-case headroom (10.00 cm) | margin over the folio's 49 px | heights that fail |
|---|---|---|---|---|
| 8.5 pt (into this card) | 35 | 47 px | **-2** | 1 of 381 |
| 8.2 pt (largest that fits) | 34 | 51 px | +2 | 0 |
| **8.0 pt (shipped)** | **33** | **55 px** | **+6** | **0 of 381** |

Rendered figures beside the arithmetic: the 10.00 cm page leaves 55 px under its last row
and draws its folio; 10.10 cm leaves 66 px. Both pinned.

**Markers converted (all three strict xfails are gone; none deleted silently):**

| marker | now |
|---|---|
| `tests/test_book_toc.py` `test_the_shortest_storable_trim_leaves_its_folio_a_line_too` | ordinary passing test, kept as its own test rather than folded back into the sweep, with the cycle recorded in its docstring |
| `tests/test_book_toc.py` `test_the_shortest_trim_still_prints_its_folio_with_the_gaps_in_place` | ordinary passing test; its docstring records that it was an expected failure for one cycle |
| `tests/test_book_guide_page.py` `test_the_difficulty_box_carries_its_three_sentences_verbatim` | converted and renamed, see Block 1 |
| `test_the_shortest_trim_the_shipped_gap_numbers_prints_its_folio` (10.10 cm, added while the above was red) | kept green beside them; the pair now pins the two tightest storable heights, 66 px against 55 px |

The sweep's own assertions move from "exactly one height fails, by 2 px" to "no height
fails; the worst case is 55 px, 6 px clear" — ungated, on every host.

#### Baselines

`tests/fixtures/book_baseline_card221.json` **re-recorded in place** for this card's own
fix cycle (the shape CARD-204 Fix 1 and CARD-205 Fix 2 both used; a new file is for a new
card). Measured page by page against its own pre-fix recording before rewriting:
**pages 2 and 3 move, nothing else does.** Against CARD-205 the changed set is still
exactly the seven `_guide_face` pages. `interior_bytes` 3369113 → **3464123** (+95010;
CARD-205's was 3498430). No earlier fixture in the chain is touched.

#### Fix-cycle-1 mutants (all reverted; `git status --porcelain -- src tests` empty after each)

| # | mutant | killed by | what it shows |
|---|--------|-----------|---------------|
| M5 | `TOC_GROUP_GAP_PT` 8.0 → **8.2** (the largest gap that merely *fits*) | the 381-height sweep, on the figure: "the worst-case headroom is 51 px, recorded as 55"; plus 4 baseline/TOC-page tests | **8.0's margin is pinned, not just sufficient.** The inequality (`short == []`) is still satisfied at 8.2 — 51 ≥ 49 — so only the recorded figure catches the loss of the owner's 6 px. This is the mutant the coordinator asked for, and it is the one that shows why the figure is asserted and not only the inequality |
| M6 | `_draw_difficulty_legend` prints each gloss under its name again (unruled) | 8 tests across 3 files, incl. `test_a_wrong_difficulty_label_does_not_match`, the Book 1 type-floor check, the smallest-trim fit, two F-11 alignment checks and the baseline | the page-fit claim is pinned: restoring the sentences puts page 2 over again and the suite says so |
| M6 (first run) | the same mutant, before the test was strengthened | **slipped past** `..._three_labels_and_no_sentences` | its "no sentences" half only knew the *bordered* box, so an unruled reprint matched nothing. Fixed in commit `0153281`: the three sentences' first three words are now probed in the page's own body face anywhere on page 2 (0 occurrences on the real page, 1 each under M6, measured both ways). **A mutant finding a hole in the test written in the same cycle — recorded because that is the point of mutating** |
| M7 | the legend keeps the box's inner `pad`, so the labels indent 46 px again (the flush-left decision's **edge**) | the three F-11 alignment tests, on the premise assertion ("51 px of a 46 px em is not a side bearing"), plus the baseline | the flush-left half of the rule decision is held by a test, not only by my eye; and it is held by the *alignment* tests rather than by the content test, which is the right separation — M7 leaves "what the legend says" untouched and only moves it |

Carried in from CARD-212's review (the same shape as this card's own M4b finding): a strict
`xfail` that cannot pass makes its own promise false. All three of this card's markers are
now ordinary passing tests, so there is none left to get wrong.

#### Fix-cycle-1 runs

Impact scope (`tests/test_book_*.py`, `tests/property`, `test_export_pdf`,
`test_layout_page_spec`, `test_layout_two_up`, `test_admin_tier_surfaces`,
`test_admin_error_text`, `test_cli`), run on both faces as before:

- on host (Arial present): **2518 passed, 1 skipped, 0 failed, 0 xfailed**
- off host (`ImageFont.truetype` refusing every host path): **2517 passed, 2 skipped**
  — the extra skip is this card's own gated negative control, which needs two
  distinguishable host faces to have anything to contrast.

Renders refreshed into `~/Documents/nonogram-reviews/CARD-221/` as
`*__fix1-packaged-dejavu.png`, beside the two earlier sets (`*__packaged-dejavu.png`, the
pre-ruling state, and `*__host-arial-before.png`, what this Mac printed before the card) —
24 PNGs, so the owner can see all three states of every page side by side.

### Fix cycle 2, 2026-10-14 (agent) — review cycle 1 (7.5/8, 0 critical, 3 Important, 6 minor)

The review confirmed the substance on every point it set out to attack — the off-host
simulation (it went around my test with a process-wide plugin applied before collection:
330 passed / 0 failed), the guardrail deletion's premise, both type probes (it swept every
printable ASCII glyph to confirm "dg" is the real ceiling), all four re-aimings and both
halves of my M6 account. What gated was prose and two consequences that landed outside the
owner's decision list.

#### F-001 — four records that are only narrated still described the pre-ruling branch

All four were **figures that are not also assertions**, which is exactly why the fix cycle
missed them: every figure a test reads was updated and correct. Root cause of my own, worth
recording: fix cycle 1's first edit script bundled a docstring rewrite and an assertion
rewrite behind one `assert old in s`; the assertion half did not match (one word of
drift), the script raised, and **neither** edit was written — I verified the assertions
afterwards by running the test and never re-read the docstring. The second script used a
bare `str.replace` with no guard, which silently did nothing to the fixture field. Both
scripts "succeeded". I now edit one claim at a time and grep for the old text after each.

| record | was | now |
|---|---|---|
| `tests/test_book_toc.py` AC-4 sweep docstring | "**At the shipped 8.5 pt the 10.00 cm trim is 2 px short, and this test says so by failing**", "which is why the constant is 8.5 pt", "CARD-221 is forbidden that change (its G-6)" | the 8.0 pt figures (55 px, 6 px clear, no failing height), with the 8.5 pt state and the one cycle it was an expected failure in the past tense the rest of the file uses |
| `book_baseline_card221.json` `why_a_new_baseline` (**the field AC-5 points at**) | "TWO MEASURED CONSEQUENCES THE CARD COULD NOT CLOSE", the labels-form page 2, 47 px, "the two strict xfail markers" — all three false of HEAD and contradicting `interior_bytes_note`/`changed_pages_note` in the same file | "THREE MEASURED CONSEQUENCES OF THE EXTRA WIDTH, ALL RULED ON BY THE OWNER", with the 234 px / 4 px, the 8.0 pt / 55 px, the accepted guide-page folio, and "no strict xfail marker survives" |
| `tests/helpers/book_corpus.py:443` | `interior_bytes 3498430 -> 3463959` (164 bytes off; introduced by the fix cycle, correct at `9862ecd`) | `-> 3464123`, the figure the fixture, the card and `test_the_interior_file_is_the_length_it_was_recorded_with` all carry |
| `tests/test_book_pdf_memory.py` (×2, the scatter-deletion justification) | page 2 "11.442%, 581,547 outliers" — the pre-fix-cycle page | **re-measured at HEAD**: 10.531% and 478,630, by re-implementing the deleted 3×3 instrument in the scratchpad to count them. Page 1 is unchanged at 7.596% / 254,766. The argument is untouched: both are an order of magnitude past the 1% ceiling |

#### F-003 — the preview now shows the page it previews (fixed here, not deferred)

I had priced this and routed it to CARD-229 on scope. The coordinator and the reviewer both
disagreed, on my own Block-1 argument: a drawing must not make a claim it no longer
honours, and a preview is a claim about a page — a green test certifying it is that defect
one layer down. `book_finalize.html` drops `<p data-guide-difficulty-text>`; the three
preview tests move with it:

- `test_the_difficulty_box_carries_the_three_sentences_verbatim` →
  `test_the_difficulty_legend_carries_the_three_labels_the_page_prints`, which asserts the
  names **and** that each column's `text` is absent — the sentences are still in the
  constant for CARD-229, so "the preview does not show them" needs asserting.
- `test_the_difficulty_sentences_appear_nowhere_else_in_contradictory_wording` →
  `..._appear_nowhere_on_the_screen`: the count it asserts goes from 1 to **0**, anywhere in
  the rendered screen. Same intent (no description the page does not carry), stronger fact,
  and it covers a sentence rendered somewhere the file's parser does not tag.
- `test_sentinels_on_the_new_constants_render_live`: the difficulty sentinel rides on
  `name` instead of `text`, the field the block still renders. Its claim (nothing
  hard-coded in the template) is unchanged.

`DifficultyLabel.text` is kept, as instructed. **Left for CARD-229 and recorded here:** the
screen's own `.guide-difficulty-box` rule in `admin.css` still boxes the three names — that
is screen styling (G-6), and CARD-229 rebuilds the block.

#### F-002 — accepted by the owner; written up in "What this card could NOT close" as item 3

Not a fix-cycle bullet: it is in the same section as the other two, with the folio table
(`[2,3,4,6]` → `[3,4,6]`, same book, only the face swapped), the 18 px against 49 px
arithmetic, why the 8.0 pt ruling cannot reach it, the two renders that show it, and the
owner's mitigation. The 10.00 → 10.10 cm minimum-trim option they turned down is recorded
beside it as an **architect-station** question, since it would retire both folio problems
at that trim and is a one-constant change to CON-018's floor.

#### The five minors, each with what I did

| # | finding | decision |
|---|---|---|
| F-004 | the no-host-path watch walked one book shape | **Taken.** Parametrized over all three shapes the module builds (Book 1, min-trim, 150-puzzle), ×3 tests. It is the claim that cannot be fooled by two runs agreeing, so breadth is worth three lines |
| F-005 | the determinism claim is one notch wider than the card proved | **Taken, in three places.** `_guide_face`'s docstring, AC-1's module docstring and the gates inventory now say "this repository's font data **and the installed Pillow/FreeType**", name the unbounded `Pillow>=10.0` as the remaining lever, and name what would catch it: the baseline comparison, ungated, all thirteen pages. Bounding Pillow is carded to the architect station, not decided here |
| F-006 | `_both_faces` took an unused `monkeypatch` | **Taken.** Dropped, with the reason it must stay dropped (the on-host half must run with nothing patched; one shared context is how this comparison would become self-fulfilling). Three callers lost the fixture with it |
| F-007 | `TestInteriorType_FloorHoldsWithoutArial` is now a duplicate; the file was missing from the gate inventory | **Kept, and said so.** Its docstring now states it is deliberate redundancy: it costs one export per book and it is what fails first if a host lookup returns *to the drawing*, where the structural watch only sees `truetype`'s argument. Added to the gates inventory as a file with **no** gate |
| F-008 | the re-aimed F-4 control measures with the generic probe | **Documented, not changed.** It understates, which is the safe direction for a floor; the docstring now records that, and the 1.05 pt margin, so a later card tightening CON-020 reads it as probe slack rather than headroom |

#### Mutants — the set the review asked for, on `_toc_entries_per_page`, `folio_band` and `host_offers_a_second_face`

| # | mutant | result |
|---|--------|--------|
| N1 | `_toc_entries_per_page` drops `- folio_space` from the capacity | **SURVIVED**: 217 passed across test_book_toc + test_book_finalise_gutter + test_book_pdf_memory. Every existing test of the split feeds it the eight-row structural list, which never fills a page, so the capacity could be wrong by a row unnoticed. Measured the claim it broke: packed to capacity, 0 of 381 heights lose the folio **with** the reservation and **185 lose it without**, from 10.30 cm (24 px against 49). Closed by `TestBookToc_APagePackedToCapacityStillCarriesItsFolio` (sweep + the 10.30 cm page rendered and spied); N1 re-run after it → **KILLED**, both tests, the rendered page drawing no folio at all |
| N2 | `_draw_folio` returns without drawing | KILLED by `folio_band`'s bottom-edge assertion ("the page's last band of ink runs to row 3135 … the folio is anchored at 3188"), on both trims |
| N3 | the folio is drawn centred instead of in the outer corner | KILLED by `folio_band`'s outer-corner assertion (ink 1272..1289 inside 150..2438) |
| N4 | the folio prints `"page N of this book"` at the same corner | KILLED by `folio_band`'s width assertion (402 px against four digit-heights) — so all three of its structural assertions are live |
| N5a | `host_offers_a_second_face` → always `False` | **SURVIVED** before this cycle: a gate that closes wrongly takes its test with it and reds nothing. Closed by `TestInteriorFace_TheOneHostGateDiscriminates`, which pins the logic in both directions host-independently; re-run → KILLED |
| N5b | `host_offers_a_second_face` → always `True` | KILLED by the same class's refused-path half |

Every mutant reverted with `git checkout --`; `git status --porcelain -- src tests` verified
empty after each, and after the last.

#### Fix-cycle-2 runs

Same impact scope, both faces, after every fix above:

- on host (Arial present): **2525 passed, 1 skipped, 0 failed, 0 xfailed**
- off host (`ImageFont.truetype` refusing every host path): **2524 passed, 2 skipped**

(+7 on each side against fix cycle 1: 2 for the packed-page reservation, 3 for the host
gate's own logic, 2 more parametrizations of the no-host-path watch. The single
host-dependent skip is still the one gate this card adds, and the second off-host skip is
still that same gate closing.)

- [Fix cycle 2 complete] 2026-10-14 — `b876736`, `6e8b151`, `62a70f8`. All three gating findings
  closed, all five minors decided with a stated reason each, and the fuller mutation set run.
  Impact scope both faces: **on host 2525 passed, 1 skipped, 0 failed, 0 xfailed; off host 2524
  passed, 2 skipped.** No `pytest.mark.xfail` remains anywhere in `tests/test_book_*.py`. The
  agent kept its heavy runs backgrounded while CARD-212's merge gate had the machine.
- [Fix cycle 2 — the mutation set found two real holes, which is why it was worth asking for]
  - **N1: `_toc_entries_per_page` dropping `- folio_space` SURVIVED 217 tests.** Every existing
    test of the split feeds it the eight-row structural list, which never fills a page. The
    agent then measured what the mutant actually breaks: packed to capacity, **0 of 381 heights
    lose the folio with the reservation and 185 lose it without**, starting at 10.30 cm (24 px
    against the folio's 49). Closed with a new sweep plus a rendered 10.30 cm page; the mutant
    now dies to both.
  - **N5a: `host_offers_a_second_face()` forced to `False` SURVIVED** — a gate that closes
    wrongly takes its own test with it and reds nothing. Closed by a class that pins the gate's
    logic host-independently (refuse every path -> it must close; a face that really differs ->
    it must open) with a non-vacuity check that the sample discriminates. Both directions now die.
  - N2/N3/N4 confirm all three of `folio_band`'s structural assertions are live.
- [Fix cycle 2 — the agent's own root cause, recorded because it generalises] F-001's four stale
  figures came from **edit scripts that "succeeded" while writing nothing**: the first bundled a
  docstring rewrite and an assertion rewrite behind one `assert old in s`; the assertion half
  missed by a word, the script raised, and *neither* edit landed — and the agent then verified by
  running the test, which passed, and never re-read the prose. A second used a bare
  `str.replace` with no guard on a fixture field. Its own corrective — edit one claim at a time
  and grep for the old text afterwards — is what found that the first docstring rewrite had never
  landed at all.

- [Review cycle 2 — held until the machine is free] 2026-10-14 — the card is ready for it, and
  it is deliberately not started yet. CARD-212's merge gate began at 19:01:33 UTC on a quiet
  host, having waited for one; a reviewer's targeted runs and mutants on top of it are the same
  load that produced the first gate's false failure and the CARD-195 `page.goto` artefact. The
  gate's signal is the thing standing between CARD-212 and merging, so it gets the machine.
  CARD-221's review starts when the gate reports.
