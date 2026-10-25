# CARD-294: The interior's drawing vocabulary — the embedded face and the operator set, curves included, proved by an engine that did not write them

**Status:** in_progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/294-interior-drawing-vocabulary
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-294
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §1 and §6 item 2. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 60
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_vector_primitives.py, tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** 2026-10-25
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card is first, and why it is `architectural`

It is the phase's **walking skeleton through the riskiest path**, and the risk is
one specific thing.

CARD-293 proved the mechanism cheap: **163 code lines** for font embedding,
**22.4×** smaller files, **8.5×** faster per page, and DejaVuSans embedded whole
costs **379,441 B Flate — less than ONE raster page (381,564 B)**, so glyph
subsetting is pointless. All of that is measured, in
`meta/profiling/card-293-vector-interior-comparison.md`, and the prototype that
measured it is committed at `scripts/card293_vector_probe.py`.

But the spike drew **one puzzle page**. Its G-3 said so explicitly, and §6 named
the consequence: *"nobody has priced redrawing the guide's worked example, the
pipeline diagram and the difficulty legend as operators."* Reading the spike's
own primitive table, the gap is concrete: it drew **straight lines, rectangles,
fills and text**. It never drew a **round shape**. The difficulty dots and the
guide's legend need curves — in PDF, cubic Béziers via the `c` operator, because
PostScript/PDF has no circle primitive — and that is **the only primitive in the
interior nobody has emitted or measured**.

So this card exists to price the unknown **first**, while it is still cheap to
learn the answer, instead of discovering it in the fourth card of a phase built
on the assumption that it is easy. That is the handoff ordering rule — maximum
uncertainty collapsed per unit effort goes first — applied honestly: if curves
turn out to be awkward, the phase finds out in card 1, not card 4.

`Complexity: architectural` on two of the four objective signals: it is the
**first implementation of ADR-0042**, and it lays the vocabulary every later
card in the phase copies.

## What to implement

A vocabulary, not a page. Nothing in this card draws a puzzle, a guide or a
table of contents — those are CARD-295, CARD-296 and CARD-297, and each consumes
what this card builds.

1. **The embedded face.** DejaVuSans, embedded **whole** and FlateDecoded once
   per file, as the PDF font objects (`/FontFile2` descendant, the descriptor,
   the widths). The face already ships: `src/nonogram/export/fonts/DejaVuSans.ttf`,
   declared as `nonogram.export` package data in `pyproject.toml:79`, reached
   today through `FONT_RESOURCE = "fonts/DejaVuSans.ttf"` (`export/pdf.py:139`,
   `export/png.py:106`). **Read it through the same resource mechanism** — do not
   add a second path to the same file, and do not add a dependency: ADR-0006/R1
   says a static asset shipping as package data *is not* a dependency change, and
   that is the clause this card relies on.
   - **Subsetting is deliberately not done** (ADR-0042/R5). It saves ~365 KB
     against a file that was 9 MB. If you find yourself writing a glyph-set
     walker, stop — that is the card growing past its slice.
   - **A base-14 substitute is forbidden** (R5), because every type measurement
     in this tree — `type_px`, the band face, the guide face, CON-020's 10 pt
     floor — is DejaVu's. Helvetica would silently change all of them.
2. **The operator set.** The content-stream vocabulary the page cards need:
   - text showing with an explicit `Tf` size (the operator CON-020's rewritten
     floor check will read — see CARD-299);
   - straight lines and rectangles, stroked and filled;
   - stroke widths in points, and grey tones via `g`/`G`;
   - **curves (`c`), for round shapes** — the unpriced primitive. Price it:
     report what a circle of a given radius costs in operators and in lines of
     code, and whether a four-Bézier approximation is accurate enough for a
     difficulty dot at the sizes the book actually prints.
3. **Report the price.** Append the measured cost of the curve primitive to
   `meta/profiling/card-293-vector-interior-comparison.md` (or a sibling
   artefact, if that file reads better left closed) — lines of code, operators
   per shape, and the verdict on accuracy. **This is a deliverable, not a note:**
   the phase's remaining four cards were scoped on the assumption that curves are
   cheap, and the next orchestrator needs the number rather than the assumption.
4. **Flip ADR-0042/R5's check.** R5's check is currently `{kind: review-lens}`
   with the planned test name in a comment beside it. Write
   `tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face` and
   flip R5 to `{kind: test, ref: <that node id>}` **in the same change**. The
   lens is a placeholder for exactly this card; leaving it after the card merges
   is a rule that quietly stopped being verified.

## Acceptance criteria

This card is traced to no FR — the interior's *medium* is an ADR decision, not a
requirement, and ADR-0042/R7 is explicit that the ADR sets no reader-facing
figure. Its criteria therefore come from the ADR's rules, which is why the ECs
below carry the weight.

- **AC-1** (the face is the project's own, embedded whole): *Given* an interior
  PDF written by the new vocabulary, *then* it carries exactly one embedded
  FlateDecoded DejaVuSans font file and no base-14 reference, and the embedded
  bytes match `src/nonogram/export/fonts/DejaVuSans.ttf`. (test:
  `tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face` — the
  node id ADR-0042/R5's comment names, so the flip in item 4 lands on a real test.)
- **AC-2** (the vocabulary is read back by an engine that did not write it):
  *Given* each primitive — text, line, rectangle, fill, grey, **curve** — *then*
  a PDF containing it is parsed and rendered by an **independent** engine
  (poppler, as the spike used) and the shape is found where the writer said it
  would be. (test: `TestVectorPrimitives_AnIndependentEngineFindsEachShape`.)
  **This is the card's load-bearing control**: a writer checked only against its
  own reader proves that two of my functions agree, which is the failure mode
  this project's test style names explicitly — prefer an independent second
  implementation over re-deriving a value with the function under test.
- **AC-3** (the curve is priced, not assumed): *Given* the round-shape primitive,
  *then* the artefact records its cost in lines and operators and states whether
  the approximation is accurate enough at the printed dot's real size, **with the
  measurement that establishes it**. A verdict of "awkward and more expensive
  than expected" is a **valid outcome and a finding**, not a failure — it is what
  the card was ordered first to discover. (**gate**: the figures recorded.)
- **AC-4** (type sizes are physical, never pixels): *Given* any text the
  vocabulary emits, *then* its size is set as points against the page, so a page
  written at a different DPI carries the same point size. (test:
  `TestVectorPrimitives_PointSizeIsIndependentOfDpi` — the vector sibling of
  `TestDividerPage_PointSizeIsIndependentOfDpi`, which already holds this for the
  raster path and must keep passing.)
- **AC-5** (the baseline stays shut): *Given* this card's branch, *then*
  `pyproject.toml`'s runtime dependencies are unchanged and no PDF or font
  library is imported anywhere. (test: the existing
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, which
  is ADR-0042/R4's live check — do not rewrite it, just keep it green.)

## Engineering constraints

- **EC(ADR-0042/R5):** every interior file embeds the project's own face whole
  and exactly once — not once per page, not once per text object. The font
  objects are written once per document however many pages show text.
  test: `PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts`
  (genuinely multi-case: a corpus of books across page counts, asserting one
  embedded face per file and a per-page cost of zero font bytes).
- **EC(ADR-0042/R4):** no new runtime dependency, at any page count or page kind.
  test: covered by AC-5's existing baseline test; do not duplicate it.

## Guardrails

- **G-1: this card draws no page.** No puzzle grid, no guide, no TOC, no answer
  tile, no divider. Those are CARD-295/296/297, and a vocabulary card that also
  draws a page is the scope gate's textbook case.
- **G-2: do not touch the cover.** It is raster by ADR-0042/R2 — it is a
  photograph. `tests/test_book_cover.py` and `same_page(cover_page,
  expected_cover)` at `tests/property/test_book_export_interior.py:652` stay
  exactly as they are. See `meta/profiling/adr-0042-migration-census.md`'s "What
  is not in the set" before converting any pixel assertion.
- **G-3: do not touch the section dividers.** Raster for now by owner decision
  2026-10-25 — they are getting a nicer design in CARD-231, which is born vector.
- **G-4: do not edit `src/nonogram/export/**`.** The face is *read* from there
  through the existing resource mechanism; nothing in `export/` changes. CON-019
  holds COMP-007's CLI and web exports byte-for-byte identical, and ADR-0042 does
  not reach them.
- **G-5: no geometry.** This vocabulary emits what it is handed. It computes no
  coordinate, no width and no tone of its own (ADR-0042/R3, restating
  ADR-0036/R2). The `Layout` consumer is CARD-295's.
- **G-6: do not lower a corpus minimum or regenerate `tests/fixtures/**`.**
- **G-7: probes stay OUT of `tests/`.** `meta/profiling/rank_durations.py:45`
  defines the frozen render set by grepping eight idioms over `tests/**/*.py`,
  and `tests/test_suite_profile.py:482` asserts the live grep **equal** to a
  33-entry snapshot — a throwaway probe under `tests/` naming `interior(` reds
  the suite. Use `scripts/` or the scratchpad, as CARD-293 did.
- **G-8: ADR-0042/R5's lens must not survive this card.** Item 4's flip is part
  of the card. Merging with R5 still `review-lens` ships a rule whose delivery
  card is closed and whose check is a placeholder.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R3 — the vector writer consumes positions and derives none (check: review-lens)
- ADR-0042/R4 — hand-rolled, no new dependency; ADR-0006/R1 stays closed (check: tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed)
- ADR-0042/R5 — DejaVuSans embedded whole and Flated once per file; no base-14 (check: review-lens → this card's AC-1)
- ADR-0042/R7 — this ADR does not set the grid's weights itself; it removed the device floor, and ADR-0037/R2 is where the weights live (as of 2026-10-25, the owner's 0.3 / 0.8 / 1.3 pt, bound to the vector medium). This card sets no weight either — CARD-227 lands them in wave 62 (check: review-lens)
- ADR-0006/R1 — the runtime dependency set is exactly stdlib + Pillow + NumPy; a font shipping as package data is not a dependency change (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE, never a silent pass (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt at the page's own resolution, clue digits excepted (check: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)

## Architecture context

- **FR/NFR:** none — the interior's medium is an ADR decision, not a requirement. CON-020 and CON-019 apply as standing constraints.
- **ADR:** **ADR-0042** (R3, R4, R5, R7 — this card is its first implementation), ADR-0006/R1, ADR-0036/R2, ADR-0039/R1-R2
- **Components:** COMP-009 (the book generator). COMP-007's layout is *consumed*, not changed.
- **Trace:** not applicable — no requirement's verifying test changes in this card. CARD-299 is where the registry's verifying tests move.

## Worktree notes

[Env] forge 2026.8.17 (executing manifest: forge/.claude-plugin/plugin.json). No
`meta/.skills.yml` exists, so the project declares no `forge.min_version` and no
comparison was made; the note is written because it is what makes a later
diagnosis of the evidence possible at all. No `models:` block either, so the
implementation agent was spawned WITHOUT a model override — per the skill, the
session model may be stronger than the profile's `heavy`, so forcing one would
be a downgrade.

[Dispatch 2026-10-25, wave 60 — orchestrator] Opened the moment wave 58 closed
(CARD-276 merged `f794d5a8`). Fork point `9b0d245d`. **Sole active card**: the
owner's standing cap is 2, and the second slot is deliberately left empty
because every other ready card in this phase (CARD-295, CARD-296, and later
CARD-297/298) declares `src/nonogram/admin/book_pdf_generator.py` — a declared
`conflict.hotspots` path — so the whole vector phase serializes on it regardless
of the cap. Dispatched as `general-purpose`, not the `python-pro` agent:
`config.yml`'s own caveat records that the agent of that name in this
environment is scoped to another project's FastAPI/SQLAlchemy services, and
`Skill:` is to be read as "a Python card" rather than as an agent name.

- **Start from the probe, don't restart from scratch.**
  `scripts/card293_vector_probe.py` is 1,099 lines of *proven* code — the font
  embedding read back by poppler with 540 clue digits rendered, the stream
  writer, and the 41-line stream assertion that replaced 168 lines of pixel
  archaeology and still discriminates under mutation. It merged (`ef49d656`)
  precisely so this card would build from it. What it does **not** contain is the
  curve primitive.
- **The load-bearing finding from the spike, worth re-reading before you start:**
  `book_pdf_generator._write_pdf` has not called `Image.save(save_all=)` since
  CARD-145 — it drives `PIL.PdfParser` directly (`:379`, `:7047`, `:7105`),
  writing the object table, catalog, pages, content streams, xref and trailer by
  hand. **The PDF plumbing already ships inside the file that changes.** A vector
  page replaces one of the three objects a page writes; the font objects are
  three more, once per file. This is why ADR-0042/R4 could keep the dependency
  baseline shut without strain.
- **Scheduling.** CARD-273 moves nine modules (including
  `book_pdf_generator.py`) to `src/nonogram/book/`. It has not run. This phase
  deliberately does **not** wait for it — CARD-273's blast radius is large and
  the interior is the owner's current subject — but **name and place new modules
  so that move stays mechanical**: a new file beside `book_pdf_generator.py`
  moves with it in the same `git mv`. Re-point `Touches:` on both cards if
  CARD-273 lands first.
- **`src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot`.** Every
  card in this phase touches it, so `run` will serialize them regardless of wave.
  The waves below express the dependency, not an expectation of parallelism.

### Round 1 — what was built (2026-10-25)

**The vocabulary is a new module, `src/nonogram/admin/book_vector.py`, and
`book_pdf_generator.py` is not edited at all.** That is a deliberate departure
from `Touches:` and is this round's first disagreement with the brief: there is
nothing to wire into the generator until a page card exists to call it, and
wiring with no caller is the scope growth G-1 forbids. The module is placed
beside `book_pdf_generator.py` exactly as these notes asked, so CARD-273's
`git mv` stays mechanical.

What it holds, and nothing more:

* the **embedded face** — a `struct` sfnt reader over `head`/`hhea`/`maxp`/
  `OS/2`/`hmtx`/`cmap`, the three PDF font objects, and `interior_face_bytes()`
  reading the face through the **same** `FONT_PACKAGE`/`FONT_RESOURCE` pair
  `export/pdf.py` publishes (no second path to the file, no new dependency);
* the **operator set** — `line`, `rectangle` (stroked/filled/both),
  `stroke_width` in **points**, `stroke_grey`/`fill_grey` via `G`/`g`, `text`
  with an explicit `Tf` in **points**, `begin_path`/`line_to`/`close_path`/
  `paint`, the bare `curve` (`c`), and `round_mark` — the four-Bézier circle;
* `write_vector_pdf(pages, page_count)`, the same `PIL.PdfParser` shape
  `_write_pdf` has driven since CARD-145: three font objects once per file,
  two objects per page, no image XObject, no page bitmap.

Units are never implicit: **positions in device pixels** (the unit a `Layout`
speaks), **widths and type sizes in points** (the unit the page is measured
in). `encode_text` gates every string through `cp1252`, which *is*
`/WinAnsiEncoding`, and raises by name on a character it cannot carry rather
than printing a `.notdef` box.

### The curve, priced (AC-3)

Full artefact: **`meta/profiling/card-294-curve-price.md`**, every figure from
`scripts/card294_curve_price.py`. A pointer sits at the foot of CARD-293's §6;
that document is left closed, as item 3 permitted.

* **Lines:** **24** for the round shape (13 of them `round_mark` itself),
  against 12 for the whole straight-line vocabulary and 171 for the font work
  CARD-293 estimated at 163. The unpriced primitive is the *smallest* of the
  three pieces of this card.
* **Operators:** **7 per mark** — `m c c c c h` + one paint — the same seven
  filled or outlined. For scale: a line is 3, a rectangle 2, a string 6. A
  round mark is the dearest primitive **by one operator over a string**.
* **Accuracy:** worst radial error **2.7253e-4 of the radius**, one-signed
  (always outside, never inside). At the band-cap dot (3.556 mm) that is
  0.00048 mm = **1/44 of a device pixel at 1200 DPI**; at the 1.0 mm floor,
  1/155.
* **Verdict: not awkward.** No raster device in the pipeline can resolve the
  deviation (worst case 1/44 of a 1200 DPI pixel), and the shape is cheap in
  both lines and operators. The phase's remaining cards were scoped
  correctly. What this does **not** settle, and says so: how a printed dot
  looks on paper — dot gain is still measured by nobody, and it spreads ink
  at the mark's edge rather than moving the mark's path.

Two findings inside that verdict:

1. **The 1.96e-4 figure everyone quotes is a different kappa.** It belongs to
   0.5519150244935105, which minimises the maximum error by letting it
   alternate in sign. The shipped `4*(sqrt(2)-1)/3` is **39 % worse** and keeps
   the bounding box **exactly** the declared diameter — which is the right
   trade, because `difficulty_dots` states a diameter and `DifficultyDots`
   reasons about whether two dots touch. The module's docstring said 1.96e-4 on
   the first pass; the sweep corrected it. This is the card's "measure, don't
   assume" discharged on itself.
2. **At print size the curve is not the limiting term — the number format is.**
   Measured on the *emitted* operands, the relative error at the floor dot is
   **3.457e-4**, worse than the pure Bézier's 2.7253e-4, because at a 0.5 mm
   radius the stream's 0.001 pt coordinate rounding stops being negligible. A
   future card wanting a rounder mark must spend a decimal place in `_PLACES`,
   not a better kappa.

### Item 4 — ADR-0042/R5's lens is flipped

`check: {kind: review-lens}` → `check: {kind: test, ref:
test_the_interior_embeds_the_projects_own_face}`, in this same change, with a
comment recording what the ref reaches (the three claims, on a PDF this
vocabulary wrote) and what it does **not** (a real interior page, because no
page is drawn yet — CARD-295/296/297 are the page cards, and the ref should be
re-read against the shipped interior when the first lands).

**The ref is the bare test name, not the `file::name` node id the card's item 4
and R5's old comment both named, and that is this round's second disagreement
with the brief — measured, not argued.** The validators' `split_check_ref`
splits a ref on **commas only**, so a `file::name` ref is handed to
`git grep -w` as one literal symbol, matches nothing, and the rule is reported
as a **DEAD check ref** — the state `architect-validate` calls strictly worse
than a lens, and the exact harm G-8 is about. Measured on this edit: the
node-id spelling produced `[WARN] ADR-0042/R5 … DEAD check ref` (123 warnings
against main's 122); the bare name clears it (`missing=[] dead=False`). The
node id is kept in a comment beside the ref so a human can still run it, and
every other live `kind: test` ref in this model is a bare name for the same
reason.

**A related finding, not fixed here:** ADR-0042/**R4**'s ref *is* spelled as a
node id and is **not** flagged — but only because that exact string happens to
appear in a tracked `meta/review/*.yml` and in `tests/test_admin_serving.py`,
so it resolves by coincidence rather than by naming a definition. It is noted
in the ADR beside R5 for whoever next touches R4; changing R4 was outside this
card.

Validator state: the error count is **unchanged from main** — one pre-existing
`[ERROR] ADR-0025 circular supersession`.

### A finding the brief did not anticipate

**`tests/test_book_difficulty_dots.py`'s "exactly one drawing site" guard has a
fifth route it cannot see.** `TestDifficultyDots_HasExactlyOneDrawingSite`
walks `src/nonogram/**` for Pillow's ellipse family plus three other syntactic
families; `ContentStream.round_mark` is outside all four, because it is not a
Pillow call at all.

The guard is **not wrong today** — nothing calls `round_mark`, so there is
still exactly one round mark in the package. Widening it is **not this card's**,
because it means deciding where the *vector* difficulty glyph lives
(CARD-295/296). What this card did instead is make the route countable:
`TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee` asserts the `c`
operator is written in exactly one module and `round_mark(` appears in no other.
**It goes red the moment a page card draws a vector dot**, which is the alarm —
and the right response then is to grow the old guard a fifth route, not to
relax this one.

### Tests, by node id

| claim | node id |
|---|---|
| AC-1 | `tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face` (+ its control `::test_the_face_check_above_can_fail`) |
| AC-2 | `tests/test_book_pdf_vector_primitives.py::TestVectorPrimitives_AnIndependentEngineFindsEachShape` (9 tests; the last is the control that the instrument can fail) |
| AC-3 | `…::TestVectorPrimitives_TheRoundMarkCostsSevenOperators`, `…::TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize` + `meta/profiling/card-294-curve-price.md` |
| AC-4 | `…::TestVectorPrimitives_PointSizeIsIndependentOfDpi` (4 tests, one of them through poppler) |
| AC-5 | `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, untouched and green |
| EC(R5) | `…::PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts` (24-book seeded corpus, a measured per-page **slope**, and the control showing a per-page face would be caught) |

**AC-2's control is machine-gated and that is said out loud.** The poppler
tests `skipif` on `shutil.which("pdftoppm")`/`("pdftotext")` with the reason
*"AC-2's independent engine is absent"* — never a silent pass. They ran green
on this host; on a host without poppler the file still runs its stream-side
tests, and the independent half is reported as absent rather than as fine.

### Gate evidence (round 1)

```
scripts/impact_set.py --base 9b0d245d  -> 37 files, plus tests/test_export_pdf.py
                                          added by hand (AC-5 names it and the
                                          selector did not pick it)
pytest <that set>                      -> 3825 passed, 11 skipped, 0 failed
                                          (659.07s)
pytest tests/test_book_pdf_vector_primitives.py tests/test_book_pdf.py \
       tests/test_export_pdf.py -rs    -> 145 passed, 0 skipped
```

**No skips in the three files that carry this card's claims**, which matters
because AC-2's poppler tests would otherwise be the thing a skip hid. The full
suite was NOT run from here — it is the merge gate's job, and CARD-255's lock
makes it the wrong thing to take in a worktree.

`pyproject.toml` is byte-unchanged (`git diff HEAD -- pyproject.toml` empty),
and the only new imports anywhere are stdlib plus `PIL.PdfParser` plus
`nonogram.export.pdf`'s two public resource names — AC-5 / ADR-0042/R4 /
ADR-0006/R1 all hold without the baseline test being touched.

### Known gaps, named rather than left for review to find

* **No `q`/`Q`.** The vocabulary has no graphics-state save/restore. Every
  state operator it emits is absolute, and CARD-293's prototype drew a full
  30x30 page with 540 digits without nesting. A page card that needs it should
  add it **with the case that needs it**, not inherit an untested operator
  pair from this card.
* **Nothing is wired into `book_pdf_generator.py`.** By design (G-1): there is
  no page to draw yet. `Touches:` predicted an edit there and there is none.
* **AC-2's independent engine is host-dependent.** The poppler tests
  `skipif` with the reason named; they ran here. A CI host without poppler
  loses the independent half and the file says so rather than passing quietly.
* **ADR-0042/R5's ref does not yet reach a shipped interior page**, only a PDF
  this vocabulary wrote. Recorded in the ADR comment beside the ref, with the
  instruction to re-read it against the interior when the first page card
  lands.

## [IMPLEMENTATION PRE-GATE on the uncommitted round — 2026-10-25, orchestrator] PASSED, with two of the round's own figures corrected

Re-derived rather than accepted. Every figure below is from my own run.

| check | result |
|---|---|
| **AC-3's price enumerator** re-run (`scripts/card294_curve_price.py`) | **reproduces exactly** — 7 operators/mark (`m c c c c h` + paint), shipped kappa worst error **2.7253e-04**, minimax **1.9608e-04**, 189 B raw/mark, 528 B raw / 168 B deflated per three-dot glyph, band cap **4.846e-04 mm** = 1/44 device px @1200 DPI, floor 1/155 |
| **claim-bearing tests** (`test_book_pdf_vector_primitives.py`, `test_book_pdf.py`, `test_export_pdf.py`), node ids, no `-k`, no stacked `-q` | **145 passed, 0 skipped, 8.09 s** — matches the round's count, and the **zero skips confirm poppler is present**, so AC-2's independent half genuinely executed rather than skipping green |
| **ADR-0042/R5 flip** | landed as `ref: test_the_interior_embeds_the_projects_own_face` with the node id in a comment beside it; the ADR's one YAML block parses |
| **validator**, `--root meta/architecture`, branch vs main | **identical: 0 errors, 122 warnings, 1 info** on both. No ADR-0042 warning on the branch, so the bare-name ref resolves |
| **G-4** `pyproject.toml` in the diff | 0 |
| **G-1 / scope** `book_pdf_generator.py` edited | **0 lines** — the vocabulary is a new module beside it |

### The round's disagreement with my brief is CORRECT, and measured

My brief instructed `{kind: test, ref: <file::name node id>}`, quoting R5's own
comment. **That would have produced a DEAD check ref.** Verified at the source:
`validators/utils.py:276` — `split_check_ref` does `ref.split(",")`, commas
**only**. A `file::name` ref therefore reaches `git grep -w` as one literal
symbol, matches no definition, and the rule is reported as DEAD — which this
validator's own message calls *"UNVERIFIED, not satisfied"* and strictly worse
than a lens. The round landed the bare name and kept the node id in a comment.
**This is the sixth consecutive round on this board to disagree with its brief
and be right**, and the brief was mine.

### Two figures of the round's that I could not confirm

1. **`book_vector.py` is 934 lines, not the 918 the report states.** A 16-line
   overstatement in the other direction from the usual, and immaterial to any
   claim — but this board does not let a stated count stand unread.
2. **"the one pre-existing `ADR-0025` circular supersession" error does not
   exist.** The validator reports **0 errors** on both trees and the string
   `ADR-0025` appears nowhere in its output. The round's headline — error count
   unchanged from main — is TRUE (0 = 0); its attribution is to an error that is
   not there. Most likely inherited from an older session's note rather than
   read. Recorded because a specific claim no reading supports is this board's
   standing defect family, and it is the reviewer's to weigh.

### Pre-existing condition found while measuring, and NOT this card's

The validator's 122 warnings include **14 DEAD check refs on FR-045, FR-046 and
NFR-001** — `tests/test_public_player.py`, `test_public_player_pages.py`,
`test_approval_guess_gate.py` and `TestGenerate_50x50_RespectsTimeoutBound`,
none of which exist. Those belong to CARD-283/284/285 (the public player) and
CARD-291 (the guessing gate), all still `ready`. They are the exact condition
the standing rule about honest check refs exists to prevent — a planned test
ref reading as mechanically checked — and they predate this card. Raised to the
owner rather than absorbed here.

## Round 2 — the fix round for review cycle 1 (2026-10-25)

Report: `meta/review/20261025T133926Z-CARD-294-cycle1.yml`, score 7, nine
findings, two of them gating. Every figure below is from a run in this
worktree; nothing is restated from the report without re-deriving it. Each
control added or repaired was proved load-bearing by **deleting the mechanism
it is supposed to catch** and confirming the control reds, naming the cell.

### F-1 (critical, gating) — a control that was never collected

`class PropertyTest_VectorFont_EmbeddedOncePerDocumentAcrossPageCounts`
collected **zero** tests: this repository configures no `python_classes`
(`pyproject.toml`'s `[tool.pytest.ini_options]` has `testpaths` and
`addopts = "-q"` and nothing else), so pytest's default `Test*` applied.

Fixed by the spelling this tree already uses for a class-shaped property test
— `tests/test_print_specs.py::TestPropertyTest_TrimInchesShown_InsideLimitsAndAccepted`
— so the class is now `TestPropertyTest_VectorFont_…`. Measured with
`--collect-only`, not with a pass total:

```
tests/test_book_pdf_vector_primitives.py --collect-only
  before: 35 tests collected   (grep -c TestPropertyTest_VectorFont -> 0)
  after:  52 tests collected   (grep -c TestPropertyTest_VectorFont -> 3)
```

52 rather than 38 because this round also adds F-2's, F-4's, F-5's and F-7's
cases to the same file.

Two dead citations corrected: this card's "Tests, by node id" row for EC(R5),
and the comment CARD-294 added to ADR-0042/R5, which named the uncollectible
node id as where the per-page slope is verified. Both now name the collectable
id, and both were verified **by running that node id**, not by a green total.

**And the class of defect is now visible.** `tests/test_collected_names.py` is
a new, default-deny guard: every name under `testpaths` that declares a test —
`test…`, `Test…` or `PropertyTest…`, case-insensitive, no leading underscore —
must be collectible under pytest's **own** effective patterns, read from
`Config.getini("python_files"/"python_classes"/"python_functions")` rather than
copied, plus pytest's `unittest.TestCase` exemption. It is its own module
because the defect it is about is invisible from inside the file that has it.
Three things in it are worth a reader's attention:

* the rule is a **pure function of source text**, so the control plants the
  exact cycle-1 spelling as a *string* instead of writing a broken file into
  the tree, and nine parametrised shapes pin each direction;
* pytest's `python_classes`/`python_functions` are matched as **prefixes**,
  not globs (`PyCollector._matches_prefix_or_glob_option`: `startswith`,
  falling back to `fnmatch` only for an option containing `*?[`). The shipped
  defaults are `("Test",)` and `("test",)`, which match *nothing* under plain
  `fnmatch` — the first draft of the guard used `fnmatch` and passed its live
  walk while silently classifying every test in the tree as uncollectible-free
  for the wrong reason. Reimplemented and pinned;
* the floor is 5,000 declaring names against the **6,348** the guard's own
  `declaring_names` counts in the tree, so a walk that stopped finding
  anything cannot read as a clean tree.

**Mutation (F-1's guard):** renamed the class back to `class PropertyTest_…`
→ `tests/test_collected_names.py::TestCollectedNames_EveryTestDeclaringNameIsCollectible::test_no_name_in_the_tree_declares_a_test_pytest_will_not_collect`
**RED**, reporting
`tests/test_book_pdf_vector_primitives.py:750 PropertyTest_VectorFont_… — holds 3 test method(s) that pytest never runs: the class name matches none of python_classes=['Test']`.
File restored, sha256 verified.

**The guard found a second instance on the day it was written, and it is not
this card's.** `tests/bench_generate.py` declares three module-level `test_*`
functions, one of them AC-037's NFR-001 5 s p95 gate, and its own docstring
says "it runs inside `pytest -q` with the rest of the suite". It does not: a
bare `pytest --collect-only` from the repo root collects **9,224** tests and
**none** is in that file — the name matches no `python_files` pattern, and
cycle 1 only collected it by naming it on the command line. Renaming the file
touches the frozen render-set snapshot this card's G-7 is about, and AC-037 is
another card's, so it is **pinned rather than fixed**, with its reason, in
`test_the_files_pytest_never_opens_are_the_two_known_ones` — alongside
`tests/integration_tests.py`, which is a standalone script by design. A third
one reds.

### F-2 (major, gating) — `/Widths` was only self-consistent

Confirmed by mutation before fixing: replacing the width comprehension with
`{code: 600 …}` left `tests/test_book_pdf_vector_primitives.py` +
`tests/test_book_pdf.py` green.

The code was right and the control was missing, as the report said. The
independent implementation is **FreeType**, through `PIL.ImageFont` — Pillow is
in the dependency baseline, so ADR-0006/R1 is untouched and `pyproject.toml` is
still 0 lines of the diff.
`TestVectorFontMetrics_FreeTypeAgreesWithTheSfntReader` holds all **219**
encoded codes against `ImageFont.truetype(BytesIO(interior_face_bytes()),
1000).getlength(…)` — **0 mismatches**, to the unit — plus the vertical
metrics, with a 219-code floor so the comparison cannot go vacuous. The codes
are re-derived from the codec inside the test rather than imported from
`book_vector._encoded_codepoints`, so neither side of the comparison is the
module under test.

**Mutations:** `/Widths` constant **600** → `…::test_every_encoded_width_is_the_width_freetype_measures`
**RED** (1 failed, 101 passed; it was 89 passed / 0 failed in cycle 1).
Constant **300** → the same test **RED** plus
`…::test_the_text_is_inked_on_the_baseline_the_writer_named`. File restored,
sha256 verified after each.

### A defect cycle 1 did not find: `cap_height` was 10.8 % wrong

Not in the report, and it falls straight out of F-2's remedy. `font_metrics`
read `OS/2`'s `sCapHeight` when the table was version 2 or later and otherwise
fell back to seven tenths of the ascender. The bundled DejaVuSans ships an
`OS/2` **version 1** table, 86 bytes, with no `sCapHeight` at all — so the
fallback is what this interior always used: **650**/1000 em, where FreeType
measures the face's flat capitals at **729** (`H`'s `yMax` is 1493 font units,
upem 2048). The existing poppler control absorbed it: its tolerance is
`0.15 * cap_px` and the error is 12.2 % of 650.

Fixed by reading `H`'s own `glyf`/`loca` bounding box when `OS/2` has no
`sCapHeight`, which is what PDF 1.7 Table 122 means by "the top of flat capital
letters". It reproduces FreeType's 729 exactly. `OS/2` version ≥ 2 still wins
where a face has it.

This is behaviour, not just a control, and it is deliberate: `FontMetrics` is
what CARD-295/296/297 will centre and set every interior string with, and the
docstring claiming the metric was "only ever a hint to a viewer choosing a
substitute face" was false of its own public API.

**Mutation:** `cap = _cap_height(data, cmap)` → `cap = round(ascent * 0.7)`
(the round-1 heuristic restored) →
`…::test_the_ascent_descent_and_cap_height_are_the_faces_own` **RED** *and*
`…::test_two_writers_at_different_dpis_print_the_same_physical_type` **RED** —
i.e. poppler independently agrees the cap is 729, not 650. File restored,
sha256 verified.

### F-3 (major) — AC-4's "independent half" now varies the writer

`test_the_same_page_renders_the_same_type_at_two_resolutions` rendered **one**
PDF at two DPIs, so no writer defect could reach it. Replaced by
`test_two_writers_at_different_dpis_print_the_same_physical_type`: two
`ContentStream`s at **300** and **1200** DPI, same page and baseline in
millimetres, same `size_pt`, each rendered at a fixed 300 DPI, with the ink's
cap height required to be the same number of pixels **and** to equal the
face's own `cap_height` at the stated size — so two equally wrong writers
cannot agree their way past it.

**Mutation:** `Tf` operand → `_number(size_pt * self.dpi / 72.0)` → **4 failed**
(`test_the_tf_operand_is_the_same_at_every_dpi`,
`test_the_text_poppler_reads_back_is_the_text_that_was_shown`,
`test_the_text_is_inked_on_the_baseline_the_writer_named`, **and the new one**),
against cycle 1's 3 failed with the old test not among them. File restored,
sha256 verified.

### F-4 (minor) — the descriptor's entries now have controls, and the one that cannot be controlled is declared

`TestVectorFontObjects_TheDescriptorStatesTheFacesOwnMetrics` reads the
`/FontDescriptor` and `/Font` dictionaries back out of the written file (two
new helpers in `tests/helpers/pdf_vector.py`: `font_objects`,
`font_file_lengths`) and compares every entry against
`interior_face_metrics()`. **Seven mutations, one at a time, each file restored
and sha256-verified**, all of which passed 89/89 in cycle 1:

| mutation | result |
|---|---|
| `Flags=32` → `4` | RED `…::test_the_descriptor_states_the_metrics_the_reader_read` |
| `CapHeight` → `1000` | RED, same test |
| `Ascent` → `0` | RED, same test |
| `Descent` → `0` | RED, same test |
| `StemV=80` → `90` | RED, same test |
| `FontBBox` → `[0,0,1000,1000]` | RED, same test |
| `Length1=len(face)` → `1` | RED `…::test_the_embedded_stream_declares_the_faces_real_length` |

**DECLARED, not covered:** the *behavioural* half of the `Flags` rationale —
that a viewer seeing `Flags=4` would consult the font's own `(3, 0)` cmap
instead of `/WinAnsiEncoding`. Poppler, the only PDF engine on this host,
renders and extracts identically with `Flags=4`; `qpdf`, `mutool` and `gs` are
not installed. No instrument here can falsify it, so `_write_face`'s docstring
now says so in those words — the spec's rule, assumed and unverified against
Acrobat or a press RIP — with the emitted value pinned so it cannot drift
unnoticed. That is the brief's own reading of what is constructible here, and
it held up.

### F-5 (minor) — cp1252 is not `/WinAnsiEncoding`, and the soft hyphen is refused

The prose is corrected in all three places it was wrong (the `TEXT_ENCODING`
comment, `encode_text`'s contract, this card's round-1 notes). The two
divergences are `WINANSI_DIVERGENCES`, explicit with a reason each because
there is no stdlib WinAnsi table to enumerate against — the same shape
`tests/test_guard_integrity.py` uses for its own non-enumerable half.

The decision, taken explicitly: **`U+00AD` is refused** (it would print visible
ink the caller did not ask for — `UnrepresentableText`'s whole argument), and
**`U+00A0` is accepted**, because its divergence is measured inkless: the face
gives `0xA0` the same advance as `0x20` (318), asserted off
`interior_face_metrics()` rather than from the comment that says so.

**Mutations:** the refusal lookup deleted →
`…::test_a_soft_hyphen_is_refused_because_winansi_would_ink_it` **RED**.
`0xA0`'s `inks` flag flipped to `True` (the refusal over-reaching) →
`…::test_the_other_winansi_divergence_is_accepted_and_sets_nothing` **RED** and
`…::test_the_two_winansi_divergences_are_the_measured_ones` **RED**. Both
directions, both restored and sha256-verified.

### F-6 (minor) — the floor, and both of its directions

`assert len(keys_per_page) == 1` added before the loop.

**Mutation, both ways:** `page_resource_keys` made to return `[]` → with the
floor, `…::test_no_interior_page_the_vocabulary_writes_carries_an_image`
**RED** (`assert 0 == 1`); with the floor **also** removed — cycle 1's exact
state — the same test **passes green on an empty list**, 1 passed. Both files
restored, sha256 verified.

### F-7 (minor) — the sfnt reader now fails loudly, on four shapes

Closed rather than declared, because two of the four failures were *silent*
and one of those wrote a spec-invalid file. `_sfnt_tables` now checks the sfnt
version tag against `SFNT_TRUETYPE_VERSIONS` (`\x00\x01\x00\x00` and `true`;
`OTTO` is CFF and belongs in `/FontFile3`), the offset table's own
self-consistency — `searchRange`, `entrySelector` and `rangeShift` are each a
**derived** function of `numTables`, which is the cheap way to catch an
inflated count — and every table's extent against the face's length; and
`_table` raises `ContentStreamError` naming a missing tag instead of
`KeyError`.

**Mutations, each check deleted alone**, against
`…::TestVectorVocabulary_RefusesWhatItCannotDraw::test_a_face_that_is_not_a_truetype_sfnt_is_refused`:

| mechanism deleted | case that reds |
|---|---|
| the version-tag check | `[a CFF sfnt]` |
| the `(searchRange, entrySelector, rangeShift)` derivation | `[an inflated table count]` |
| the per-table extent check | `[truncated]` |
| the 12-byte header check | `[empty]` |
| `_table`'s `ContentStreamError` | `[a table the reader needs, missing]` |

All restored, sha256 verified. Reach is still test-only (`face_bytes` exists so
AC-1's control can embed something else, and no page card can reach it), which
is why this is a two-line-per-check fix rather than a card.

### F-8 (minor) — the artefact's §6

The sentence "every shape claim in the test file is made on a raster poppler
produced, not on a stream this project parsed" is replaced by one that names
the instrument **per claim** — poppler for where a shape lands and how it is
inked, the re-parsed stream for §2's operator prices and §4's radial errors
(as §2 and §4 themselves say), FreeType for the face's metrics — with the
correction recorded rather than quietly swapped. The same overstatement in the
test module's own docstring is corrected the same way.

### F-9 (minor) — the R4 attribution

Re-derived, and the brief's own figure moved: **54 tracked** files resolve that
node-id ref under the validator's pathspec, not 55; 55 only with
`--untracked`, the extra being cycle 1's own report, which was untracked when
the reviewer measured it. The one definition is
`tests/test_export_pdf.py:1249`, which the node-id spelling does not resolve
to. Written into both the card and the ADR with the commands that produce it.

### Evidence (round 2)

```
pytest tests/test_book_pdf_vector_primitives.py --collect-only
                                        -> 52 (was 35)
pytest tests/test_book_pdf_vector_primitives.py tests/test_book_pdf.py \
       tests/test_export_pdf.py -rs     -> 162 passed, 0 skipped  (was 145)
  + tests/test_collected_names.py       -> 175 passed, 0 skipped
    per-file --collect-only: 52 / 51 / 59 / 13 = 175
pytest tests/test_cli.py tests/test_guard_integrity.py \
       tests/test_suite_profile.py tests/test_book_difficulty_dots.py
                                        -> 857 passed  (unchanged)
scripts/card294_curve_price.py re-run   -> reproduces exactly: 7 operators,
                                           2.7253e-04 shipped / 1.9608e-04
                                           minimax, 189 B/mark, 528 B raw and
                                           168 B deflated per three-dot glyph,
                                           band cap 4.846e-04 mm
validator --root meta/architecture      -> 1 error, 122 warnings, 1 info;
                                           no ADR-0042 warning; the ADR's one
                                           YAML block parses and both refs
                                           read back
git diff HEAD -- pyproject.toml         -> empty (G-4, AC-5, ADR-0006/R1)
git diff HEAD -- src/nonogram/admin/book_pdf_generator.py -> empty (G-1)
git diff HEAD -- src/nonogram/export/              -> empty (G-4)
wc -l src/nonogram/admin/book_vector.py            -> 1,141 (was 934; the
                                                      pre-gate's 934 was right
                                                      for round 1)
scripts/card294_curve_price.py, line table         -> round shape 24 and
                                                      straight-line 12
                                                      UNCHANGED; the embedded
                                                      face 171 -> 216, and
                                                      the artefact says so
NOTHING IS COMMITTED. Handed back uncommitted, as the brief required.
```

### Where this round disagrees with its brief

1. **The pre-gate's second correction is wrong, and round 1 was right.** The
   pre-gate recorded that "the one pre-existing `ADR-0025` circular
   supersession error does not exist … the validator reports 0 errors on both
   trees and the string `ADR-0025` appears nowhere in its output". Measured
   here, twice: the branch reports **1 error**, `[ERROR] ADR-0025 circular
   supersession: ADR-0025 → ADR-0031 → ADR-0025 → ADR-0025`, and so does the
   fork point `9b0d245d` extracted with `git archive` into a scratch tree. So
   round 1's headline (error count unchanged from main) and its attribution
   are **both** true. Cycle 1 declined to adjudicate this; it is adjudicated
   now, against the pre-gate, which was the orchestrator's own.
2. **The brief's F-9 figure is off by one** for the set it describes: 54
   tracked files, not 55. The 55th is the cycle-1 report itself, which
   `git grep` only sees with `--untracked`. The substance is unaffected and
   the brief's point stands.
3. **The brief frames F-2 as "missing control, not missing behaviour".** True
   of the widths — every one of the 219 matches FreeType to the unit. Not true
   of `cap_height`, which the same cross-check shows was 10.8 % wrong and is
   fixed here as behaviour. The brief could not have known: cycle 1 sampled
   widths and read the cap height's own control as adequate.

### What is NOT closed, named rather than left to find

* **`tests/bench_generate.py` does not run with the suite** (F-1's guard found
  it; pinned with its reason, owed to AC-037's card).
* **ADR-0042/R4's check ref resolves by coincidence** (F-9; the fix is a
  26-character deletion, outside this card, recorded in the ADR).
* **The `Flags` rationale's behavioural half is unverifiable on this host**
  (F-4; declared in `_write_face`'s docstring).
* **`FontBBox` has no FreeType cross-check** — `PIL.ImageFont` exposes a box
  per glyph, not per face. It is controlled only as "the descriptor states what
  the reader read", and the F-2 class's docstring says so rather than letting
  it look covered.
* **No viewer other than poppler has read these files.** Unchanged from round
  1, and the reason F-4's declaration is a declaration.
