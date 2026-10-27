# CARD-296: The guide page as operators — the worked example, the legend's dots and the diagram, the phase's one unpriced page

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/296-guide-page-as-operators
**Worktree:** — (removed at merge)
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 4 — *"This is the largest card and the one the spike deliberately did not price."* Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 61
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_difficulty_dots.py
**Review score:** 7.0 (cycle 3/3) — NOT CERTIFIED; cycle 3 put the distance to 8 at three edits, all of them prose or comment over mechanisms it measured load-bearing
**Started:** 2026-10-26
**Closed:** 2026-10-27
**Actual:** —
**Merge commit:** `d2255a58` (DECLARATION, not a certification)
**Blocked by:** — (un-parked 2026-10-26: CARD-295 cycle 2 supplied the evidence the park waited for, and it vindicates the retraction — see the UN-PARKED section. Worktree KEPT at `0b91ab18`.)

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

### Implementation, 2026-10-26

**What landed.** `src/nonogram/admin/book_guide_vector.py` — the guide drawn as
PDF content-stream operators: the title and body text in the embedded face, the
line diagrams (the basic rule, the three cell-state icons, every technique's
rows and CARD-167's four-step worked example) through **one** grid routine, the
pipeline diagram, the difficulty legend and the folio. All five fallback forms,
both halves of the tutorial, both book profiles. Controls in
`tests/test_book_guide_page_vector.py` (45 tests after review cycle 1's fixes,
35 as first written). Rendered and eyeballed:
`~/Documents/nonogram-reviews/CARD-296/`.

A **new module beside** `book_pdf_generator.py`, on CARD-294's precedent and
for the Worktree note's own reason: that file is a `conflict.hotspot` this card
shares with CARD-295, and nothing here needed to edit it.

**It is NOT wired into `interior_stream` — that is the split, and it is a
finding, not an omission.** The card invited it ("if this page turns out to be
two cards, that is a finding"). Substituting a vector guide into the interior
needs `_write_pdf` to write *mixed* media: it allocates three object ids per
page before anything is drawn (CARD-145's contract), so a page that writes two
objects instead of three corrupts the xref unless the page plan declares each
page's medium up front. That is a change to the interior writer, not to the
guide, and it is the same mechanism CARD-297 (TOC) and CARD-298 (R1's derived
test over *every* page kind) both need. Recommend one card for it, before or
beside CARD-297. Everything this card drew is ready for it: `guide_page()`
returns a `ContentStream` and `write_guide_pdf()` proves the pages write.

### Three places the card or the brief turned out to be wrong

**1. AC-3 has no subject, and satisfying it would break G-1.** The card calls
the difficulty legend's dots "the card's one genuinely new primitive". **The
legend has had no dots since CARD-221 fix 1**: the owner's 2026-10-14 decision
stopped printing the three sentences, the ruled box went with them, and
`_draw_difficulty_legend`'s only drawing call is a `draw.text` of three tier
names. The round mark the brief means is `_draw_difficulty_dots`, which has
**no production caller at all** — CARD-207, **CARD-229** (the guide's key
strip), CARD-231 and CARD-233 are the cards that will call it, and G-1 forbids
drawing CARD-229's design here. AC-3 is therefore **declined as unsatisfiable**
and `TestGuidePage_DifficultyDotsAreRoundAtTheStatedDiameter` is not written: a
test with that name asserting there are no dots would be a claim wider than its
control, from the other side. What is written instead is the tripwire —
`TestGuidePage_DifficultyLegendCarriesNoRoundShapeToday`.

**That tripwire's claim was wrong as first written, and review cycle 1 (F-1)
measured it wrong.** It said "the guide emits no `c` operator; PDF has no
circle operator, so no `c` is exactly no round shape". `ContentStream` also
carries `begin_path`/`line_to`/`close_path`/`paint` — an arbitrary polygon
builder emitting only `m`, `l`, `h` and a paint operator — so a 32-gon filled
disc planted beside each tier name passed **248 tests**, through the curve
assertion, through `round_mark(`, and through CARD-294's own alarm. A polyline
disc is *cheaper* than four Béziers, so it is the likelier route for CARD-229's
dots.

**Fix round 1 then closed that route with a vertex bound, and review cycle 2
measured that the bound cannot close it.** Two discs of shapes the bound was
not written against passed 264/264: a fan of 32 **three-point** triangles, and
a staircase of 24 filled `re` bands (which the counter does not count at all).
The reason is structural, not a figure to tune: the page's own arrow head is
three points and so is a triangle, so **no value of `MAX_PATH_POINTS` admits
this page and refuses a disc.** The same hole is in the `MAX_FLAT_VERTICES`
precedent the fix cited.

**So fix round 2 takes cycle 1's other option.** "No round shape" is stated as
the three routes it has to cover, each as what it really is:

* **a curve (`c`)** — closed, and the only closure claimed:
  `test_no_guide_page_emits_a_curve_operator`. "No `c`" is "no **Bézier**",
  exactly. (Measured by a plant of a different shape from the 32-gon: a
  `round_mark` call on the legend, 7 cells red.)
* **a straight-segment approximation** (long polyline, triangle fan, `re`
  staircase) — a **NAMED LIMIT with CARD-298 as owner**, which carries
  ADR-0042/R1's derived per-page-kind check and is where a round-shape rule
  belongs (ink, or a rule on filled subpaths — not a vertex count). The vertex
  counter and the bound are kept for the narrower thing they do say: the
  longest *single* subpath this page writes is the three-point arrow head.
  Measured on a third shape — a disc as 32 **two-point** stroked spokes, 265
  green — so the limit is recorded as open rather than asserted shut.
* **a round dingbat glyph** — closed on this page by the legend's own
  "nothing-else" equality plus the record-against-stream equality; the
  package-wide dingbat rule does walk this module but is **not** what catches a
  glyph in this medium (cp1252 bars the Geometric-Shapes codepoints outright,
  and U+00B7 was not in the set). U+00B0 was added to that set; U+00B7 is its
  named hole, because it is the package's own band separator.

**CARD-229 inherits AC-3**, and when it draws the dots it reds CARD-294's alarm
if it uses `round_mark` — and nothing in the tree if it approximates one, which
is now written down rather than claimed closed.

**2. AC-4 names a routine that does not exist yet.** "Drawn through CARD-295's
grid routine" — CARD-295 runs *after* this card (wave 61 is guide-first; the
N-2 routing note on this card says so in as many words). So this card writes
it: `draw_line_diagram`, which takes a `Layout` and a set of filled/crossed
cells and knows nothing about a guide page. **CARD-295 should consume it rather
than write a second one**, which is AC-4's actual intent and is what its guard
enforces here. The guard is derived from the module's AST and default-DENY: a
function reaching a `Layout`'s grid without a declared role is a FAILURE.

**3. AC-2's quotation of CON-020's sibling is slightly off.** The card quotes
`{"guide","divider","band","footer label","answer caption"} <= kinds` at
`:355`. The live assertion is `required = {"guide","divider","band"}`, with
`footer label` and `answer caption` added **only when the book is not
`min-trim`** (`tests/test_book_interior_type_floor.py`, the two `if book !=
"min-trim"` branches). The spirit the card asks for is carried across intact —
`REQUIRED_KINDS` here is per-profile for the same reason, and names why each
absence is the page behaving as designed rather than the writer omitting
something.

### Two defects this card's own work produced, and what now catches them

* **The title was recorded and never drawn.** The first draft appended a
  `DrawnFace(TITLE, ...)` and emitted no `Tf`/`Tj` for it. Caught by
  `pdftotext`, then given a control:
  `test_the_writers_record_is_exactly_what_the_stream_shows` holds the record
  against the file string-for-string and size-for-size. This is the half of
  AC-2's "and the check can see it" that matters: a record nobody checks
  against the file is a second source of truth.
* **Every cell-state icon drew an extra empty cell out in the margin.**
  `draw_example_line` draws into a full-page canvas and **crops**;
  `guide_icon_layout` drops the frame but keeps the horizontal rules, which run
  the whole width of the sheet. A content stream has nothing to crop, so the
  gutter rules shipped. **Every assertion in the file passed** — it was caught
  by looking at a render. Now clamped on the way out (`diagram_box`) and
  controlled by `TestGuidePage_EveryDiagramStaysInsideItsOwnBox`, which reds
  when the clamping is removed.

### The guard this card had to widen, and the one that caught it

`tests/test_book_difficulty_dots.py`'s receiver rule is default-DENY over every
written call to a draw-method name, and `stream.line` / `stream.rectangle` /
`stream.text` on a `ContentStream` are not Pillow draw calls at all — so the
first run of this module put 21 entries into it. **This is the fifth route
CARD-294's own measurements document predicted** (§5, finding one: "widening
the old guard is not this card's to do, because widening it means deciding
where the *vector* difficulty glyph lives, and that is CARD-295/296's"). The
decision is taken here: the guide's round mark is CARD-229's, so this card adds
a *receiver* route and widens no round-shape bin. A `ContentStream` receiver is
excused only for the methods it really carries, derived from the class and then
narrowed by subtracting every family that could be round — and the narrowing is
exercised against a stand-in surface that *does* carry them, because against
the real `ContentStream` the subtraction is a no-op and an assertion over it
passes whether it is written or not (measured: the first version of that
assertion survived its own mutation).

`tests/test_book_page_frame.py::TestBookPageFrame_EachFigureIsDeclaredOnce`
caught a `FLOOR_PT = 10.0` in the new module as a second name for
`INTERIOR_FOOTER_LINE_PT`. Removed rather than exempted: the module records
what it set and the floor is the control's to state.

### N-2 (`_cap_height`'s uncontrolled branches) — ACCEPTED, with a fix

Not declined. This page sets type on `cap_height`: DejaVu puts its decimal
digits at cap height, so a clue digit centred on a clue cell has its baseline
half a cap height below that centre — the number is load-bearing for every clue
digit on the guide.

* **The hole is closed.** `_cap_height` now reads `OS/2`'s `sCapHeight` only
  when it states something: `sCapHeight = 0` (and a negative one) falls through
  to `H`'s own `glyf` bounding box instead of returning a silent zero into
  `/CapHeight` and into that half-cap-height.
* **Every branch has a face.** `TestVectorCapHeight_EveryBranchHasItsOwnFace`
  builds synthetic sfnts holding only the four tables the function reads, one
  per path: `OS/2` v2 with a real `sCapHeight`, v2 too short to hold the field,
  v1, the short `loca`, and both raises — plus the control that the bundled
  face takes exactly one of them, read out of the face's own bytes.

## [IMPLEMENTATION PRE-GATE — 2026-10-26, orchestrator] PASSED, and the declined AC is verified sound

Re-derived rather than accepted.

| claim | my check |
|---|---|
| **AC-3's subject does not exist** | **CONFIRMED.** `_draw_difficulty_dots` is defined at `book_pdf_generator.py:1718` and has **no production caller anywhere** — the only other `src/` reference is a docstring cross-reference in the new module. `_draw_difficulty_legend`'s body draws text, no round shape. |
| **CARD-229 is AC-3's inheritor** | **CONFIRMED** from CARD-229's own text: its `:63` says the key strip "also carries the **difficulty legend** built from CARD-228's dots — the one place a reader learns them", `:85` repeats it, and `:157` records that **CARD-221 dropped the box**. Exactly the round's account. |
| **N-2's behaviour fix** | **CONFIRMED** at `book_vector.py:587` — `if stated > 0: return stated`, so `0` and negatives fall through to `H`'s `glyf` bbox instead of returning a silent zero. |
| **the renders** | **LOOKED AT**, vector against the raster page it replaces (`~/Documents/nonogram-reviews/CARD-296/`). A faithful port: same content, same order, same layout. The slight tightening is consistent with the round's own note that this medium states type in exact points (11.0) where `type_px` gives 11.04. |
| **SCOPE GATE** | **no sibling poaching.** The diff covers none of CARD-295/297/298/299/229/227's distinctive `Touches`. |

### Touches drift, and it went in a useful direction

Predicted: `book_pdf_generator.py`, `test_book_guide_page.py`,
`test_book_guide_page_type.py`, `test_book_difficulty_dots.py`.
Actual: `book_vector.py`, **`book_guide_vector.py` (new)**,
`test_book_difficulty_dots.py`, `test_book_pdf_vector_primitives.py`,
**`test_book_guide_page_vector.py` (new)**.

So four files outside the prediction and three predicted files untouched. **The
important one is `book_pdf_generator.py`: it was predicted and was NOT touched.**
By building a module beside it rather than inside it, this card never took the
`conflict.hotspot` every other card of the phase declares — so the collision the
wave plan was built around did not materialise, and CARD-295 is not waiting on
this file.

### The architectural finding, and it already has a card

The round recommends "one card for mixed-media `_write_pdf`, before or beside
CARD-297", because `_write_pdf` allocates **three object ids per page before
anything is drawn** (CARD-145's one-page-at-a-time contract), so a page writing
two objects corrupts the xref unless the page plan declares each page's medium
up front.

**That card exists: CARD-298**, "`_write_pdf` chooses a medium per page". The
real finding is therefore a *sequencing consequence nobody wrote down*: CARD-298
sits at wave 65 and depends on 295/296/297, so **every page card before it ships
a page that is not wired in and cannot be verified inside a real interior.** AC-1
here is asserted on the guide-only PDF, not on an interior, and CON-020's
existing floor check stays green rather than redding because only wiring would
trigger it. That is inherent to the phase's design rather than a defect of this
card — but it means **CARD-298 inherits the end-to-end verification for all
three page kinds**, and it should say so.

### Routed out, owned by nobody today

**The guide already overflows its bottom margin at the 10 cm trim, in the raster
path.** Measured by the round: raster ink reaches rows 1180 and 1102 against
`frame.bottom` 1040, so the page is clipped by the canvas edge. The vector page
reproduces the same content and is clipped by the MediaBox. Pre-existing, and
G-1 forbids redesigning it here. Needs a card.

## [Review cycle 1 fixes — 2026-10-26] Four gating findings, and what each one's mutant now reds

Cycle 1 broke three of this card's structural claims by planting exactly the
artefact the control named and watching the suite stay green. Each is now a
mechanism with a mutation beside it; the three touched test files run
**264 passed** (248 at `ef487a9a`), and the six-file blast radius is unchanged
at **580 passed**.

* **F-1 — "no `c` is exactly no round shape" was false.** Route **(a)**, close
  it: every subpath the page writes is counted off the written stream and
  bounded at 4 points (`MAX_PATH_POINTS`), with the page's real longest path —
  the pipeline's 3-point arrow head — asserted so the bound's slack is a
  measurement. Chosen over route (b) because the mechanism and the figure
  already exist one medium over (`MAX_FLAT_VERTICES` bounds `draw.polygon` for
  this exact reason), because the claim AC-3 was declined on is the one at
  stake, and because a *named limit* would have left the cheapest spelling of
  CARD-229's dots unwatched. The false sentence is corrected in all three places
  it was written: the test's docstring, the Worktree note above, and
  `tests/test_book_difficulty_dots.py`'s `VECTOR_RECEIVER_NAME` comment — and in
  a fourth, **merged**, place: CARD-294's
  `TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee` promised to red
  "the day a page card draws a vector dot", which is now stated as what it is,
  a tripwire on two *spellings*, with the polyline route's owner named.
  *Mutant:* the 32-gon disc in `draw_legend` → 3 cells red
  (`test_no_guide_page_builds_a_round_shape_out_of_straight_segments` on both
  profiles and `test_the_longest_path_the_page_writes_is_the_arrow_head`), where
  cycle 1 measured 248 green.
* **F-2 — AC-4's attribute set was hand-written with a false derivation.**
  `GRID_ATTRIBUTES` is now `Layout`'s own fields and properties minus an
  allow-list of 11 names, each with a reason class that is itself asserted:
  `"not ink"` (a count or sheet metadata) and `"shared name"` (`width`/`height`,
  which `PageFrame`, `_Mark`, `_Diagram` and `_PipelineGeometry` carry too, so
  the name walk cannot attribute them). That guards `grid_lines`, `clue_entries`, `row_clues`,
  `column_clues`, `cell` and `margin` **by construction**. `guide_page` and
  `_Diagram.pad` got the role cycle 1 asked for rather than the set being shrunk
  to stay green, and roles now declare *which* names each one may read, so a
  second grid cannot hide inside a function that already has a role. The
  `width`/`height` escape is closed from the other end: a receiver spelled as a
  `Layout` may be read only for a guarded name.
  *Mutants:* cycle 1's complete second grid via the synonyms → 2 cells red;
  a grid loop appended **inside** `guide_page` → only the per-role-names cell
  red; `layout.width` read in `diagram_box` → only the receiver cell red.
* **F-3 — the EC tone check could not see a text tone.** `ContentStream.text`
  emits its fill tone inline, so the line-anchored regex read none of them. The
  reader now lives in `tests/helpers/pdf_vector.py` (`tones`), so CARD-295/297/298
  inherit it, and the property test asserts a non-vacuity floor — at least one
  tone per `Tf`, which is the assertion that would have caught the blindness.
  *Mutant:* the body text at `grey=0.5` → the EC cell reds, where cycle 1
  measured 35/35 green.
* **F-4 — the `stream` receiver exemption was name-shaped.** The name now has
  the binding rules `draw` has (every `ContentStream(...)` binding that yields a
  name yields `stream`; every parameter that *is* one is spelled it; a
  *collection* of them is not; and no `ImageDraw` binding or annotation is), and
  — the half that does not depend on the name at all — the excuse is refused for
  a call that is not a call on that surface: it must **bind
  `inspect.signature(ContentStream.<method>)`** (the class as the authority,
  ADR-0039/R2) and must not pass Pillow's coordinate display, which
  `ContentStream.line`/`rectangle`/`text` never take. The display clause is the
  instrument `NON_DRAW_RECEIVER_SITES` already earns its exemption with; the
  signature clause is what catches a vertex list handed over as a *bare name*,
  which is how this package writes its real `draw.line` calls
  (`book_pdf_generator.py:1429`) and which the display clause alone would miss.
  *Mutants:* cycle 2's M2 under the name `stream` through `line`, in all three
  spellings (literal display, bare name, wholly positional) →
  `test_a_pillow_call_wearing_the_vector_name_is_caught` reds when **either**
  clause is deleted, each on a different plant; `canvas = ContentStream(...)` in
  production → the binding cell reds; a `surface: ContentStream` parameter →
  the same cell reds on the annotation half.

Minors: **F-5** the module docstring's "the one arithmetic … is translation" and
`_Diagram.translation`'s "the page itself never reads a `Layout`'s grid" are both
corrected (the second mechanically, by the role F-2 gave `guide_page`); **F-6**
the EC test now names what it does not reach (no coordinate operand) and where
coordinates are held instead; **F-7** the 10 pt floor runs over the 24-trim
corpus as its own cell, **and the measurement worth saying out loud: the
smallest face across all 24 trims is exactly 10.0 pt — the folio — so the margin
above CON-020 is zero and the next type change on this page breaks the
constraint somewhere in that sweep** (asserted, so the sentence cannot go
stale); AC-1 now runs at the minimum trim too — as a **new cell** rather than by
parameterising the two existing assertions, because G-6's gate is a node-id set
difference and a `parametrize` id is a node id, so parameterising them would
report two removed tests; **F-8**
the pipeline's declared extent now holds its ink, and `legend_extent`'s width is
recorded as the echo it is, with CARD-229 named as the card that gives the
legend a shape again.

**And the sentence the reviewer asked this card to carry about CARD-298**:
because the guide is not wired in, EC(CON-020)'s floor is asserted on a
guide-only PDF while CON-020's registry check stays green on the *raster* guide —
so for the duration of the phase **both** floor checks measure a page the book
does not ship. CARD-298 inherits that, with the end-to-end verification.

## [FIX ROUND 1 PRE-GATE — 2026-10-26, orchestrator] PASSED

| check | result |
|---|---|
| **F-1's closure, against MY OWN counterexample** | the 32-gon filled disc that measured **248 green** at cycle 1 now reds **3 cells**: `test_no_guide_page_builds_a_round_shape_out_of_straight_segments[book1]`, `[min-trim]`, and `test_the_longest_path_the_page_writes_is_the_arrow_head`. 3 failed / 261 passed. Restored, sha-verified. |
| **the merged overreach, corrected** | `book_vector.py`'s `round_mark` docstring went from "**The interior's only round shape**" to "**The interior's one round-shape primitive**", keeping a line that records what it used to say. |
| **the merged tripwire, restated** | `test_book_pdf_vector_primitives.py` names the polyline as a **named limit** and **CARD-298** as the owner of R1's per-page-kind check. |
| **`src/` diff of the fix** | **no production code** — 49 added lines, all docstring prose (I checked the 16 my first filter flagged; they are module-docstring text at two-space indent). |
| suite | three touched files **264 passed** (248 → 264, +16 cells, none removed); blast radius + `test_cli` **715 passed**. |
| **G-6** | node-id set difference on all three files: nothing removed, nothing renamed. |

### The round corrected my brief in four places, and two of them mattered

1. **F-4's remedy was insufficient, and the gap is this package's own idiom.** My brief (following cycle 1) stopped at the coordinate-display check. That still admits `stream.line(points, fill=1, width=3)` when `points` is a **bare name** — which is exactly how this package writes its real `draw.line` calls (`book_pdf_generator.py:1429`). Closed by binding `inspect.signature(ContentStream.<method>)`, with both clauses measured load-bearing on different plants.
2. **F-7's remedy would have broken G-6.** Parameterizing the two XObject assertions on `profile` **removes two node ids**, and this card's G-6 gate is a node-id set difference — measured, not reasoned. A new cell was added instead; coverage widened, gate kept clean.
3. **F-1's "three places" was four.** `ContentStream.round_mark`'s own docstring in **merged** `book_vector.py` carried the same false equivalence. I named three; the round found the fourth.
4. **F-8's legend extent is not holdable the way the pipeline's is** — the legend draws no path ink at all, so an ink-to-extent assertion there would have been vacuous. Narrowed to a declaration with CARD-229 named as the card that gives the legend a shape again.

It also removed a tautology it had written itself (`surface = GRID_ATTRIBUTES | ALLOWED` cannot fail) — the same self-catch discipline cycle 1 rewarded.

## [FIX ROUND 2 PRE-GATE — 2026-10-26, orchestrator] PASSED

Route (iii) taken: the claim is restated as **"no Bézier"** and the
straight-segment approximation is carried as a **named limit with CARD-298 as
owner** — and it is **declared open, not claimed closed**. That distinction is
the whole point of this round.

| check | result |
|---|---|
| **the restated claim, my own shape** | a round blob via the **raw `curve` operator** (two Béziers, not `round_mark`, not a polyline — a shape nobody in this chain has planted) reds exactly `test_no_guide_page_emits_a_curve_operator` on **both profiles**. 2 failed / 263 passed. |
| **the named limit, honestly open** | the round's own third shape — a disc as 32 two-point stroked spokes — measures **265 passed**, which is *expected*: a limit that is carried is a limit that is open, and the card now says so. |
| **the four sites + two more** | all six corrected, including both **merged** docstrings and `MAX_FLAT_VERTICES`' own comment — the precedent's identical hole is now stated at its definition (owner CARD-241) rather than cited as if it worked. |
| suite | **980 passed** across the three touched files and the blast radius. |
| **G-6** | AST name + parametrize-set per file: nothing removed or renamed; **one** cell added. |
| **`src/`** | still docstring-only, proved mechanically — `ast.unparse` with docstrings blanked is **identical** to HEAD for both modules. |

### The brief was mine and it was wrong in four places, three of them substantive

1. **U+00B7 is not addable to `ROUND_DINGBATS` at all.** I wrote "add the two codepoints if that is cheap and true". U+00B0 is free. U+00B7 appears in string literals in **three** `src` modules — including the puzzle band's own separator at `book_pdf_generator.py:466` — so adding it would need exemptions covering the band, **exactly where CARD-207's glyph would hide**. The rule would mean less than it does now. Added U+00B0, recorded U+00B7 as the named hole with that measurement and CARD-241 as the instrument for a raster band.
2. **N-2's annotation predicate cannot work.** I proposed pinning `cell`/`margin` as "lengths" — but both are annotated `int` in `Layout`, exactly like `rows` and `columns`, so no annotation predicate separates them. The round took my own parenthetical instead (a `getattr` arm plus transitively-rebound receivers), which pins all sixteen through the receiver rule.
3. **N-3's narrower option would have broken the package.** Requiring a scalar-shaped first positional excludes a bare `Name` — and `stream.line(left, y0, left, y1)` / `stream.text(title_text, …)` is how **21 of the package's real calls** are written.
4. N-1's "the named bound never binds" is true only on `book1`; at the minimum trim the `<= MAX_PATH_POINTS` cell is the only path-length assertion that runs.

### Two things it did that are worth keeping as practice

**It declared a cost rather than hiding it.** N-3's `ast.Call` arm is default-deny, so it also refuses an honest scalar written as a call (`stream.text(str(value), …)`). No call the package writes has that shape. Narrowing it would mean enumerating which calls return scalars — which ADR-0039/R2 says not to write — so the cost is in the helper's docstring instead.

**It reported its own slip.** It reverted its own F-5 edit mid-round with a stray `git checkout`, caught it by sha256, and re-applied it; every later plant/restore went through verified snapshots.

## [CYCLE 3 — 2026-10-26] 7.0, NOT CERTIFIED — and the card is PARKED on the owner's decision

`meta/review/20261026T074944Z-CARD-296-cycle3.yml`, reviewed `0b91ab18`.
**Three review cycles spent against `max_cycles: 3`; aggregate round counter
5 of 6.** The owner chose to **park** rather than spend the last round or merge.

**The disposition was judged RIGHT.** Cycle 3: retraction plus a carried named
limit owned by CARD-298 "is the only honest option once the bound is shown to
have zero headroom", the `FLAT_METHODS`/CARD-241 precedent is the right form, and
this round **carried it better than the precedent** — it went back to
`MAX_FLAT_VERTICES`' own definition and recorded the identical hole *there*
rather than leaving a citation that reads as proof. *"If the last round's only
job were the disposition, this card would be certifiable today."*

### What is open, and where it goes

- **F-301 (gating) — a SEVENTH site, and it is this card's own.**
  `tests/test_book_difficulty_dots.py:944`'s `VECTOR_RECEIVER_NAME` comment still
  says the polygonal disc is *"Bounded per page kind by the drawing card's own
  control"*. `git blame` puts that line on **`cf0db002` — fix round 1**, the
  round that named this very comment as one of three it was correcting.
  `test_book_pdf_vector_primitives.py:1292` now says *"closed **nowhere in the
  tree today**"*. **Two merged guard files contradict each other on this card's
  central claim**, at the constant that exists because CARD-294 deferred "where
  the vector difficulty glyph lives" to this card. Verified by the orchestrator.
- **F-302 (gating) — AC-4's declared residue is not the residue.** A frozen
  dataclass with one `sheet: Layout` field and a `stroke` method draws a
  **complete second ruled grid** and measures **265 passed / 715 passed**:
  `_layout_spellings`' annotation arm reads *function parameters* only, and the
  rebinding arm skips an `AnnAssign` with no value — which is what a dataclass
  field is. Five more escape at helper level (tuple unpack, a `Layout`-returning
  helper, walrus, comprehension target, `for` target, unannotated default).
  **None is one of the three declared limits**, and two of them falsify the
  paragraph's safety sentence. → **CARD-295**, which AC-4 exists to constrain and
  which runs next.
- **F-303 (major) / F-304 (minor)** — the sequence clause's residue is larger
  than declared (an inline comprehension escapes, because
  `_names_bound_to_a_sequence` counts `ListComp`/`SetComp`/`GeneratorExp` while
  `_passes_a_coordinate_display` tests `(List, Tuple)` only — three type names in
  one isinstance tuple), and "all 21" is **15**. → **CARD-298**, the named
  limit's owner.

### The carry-forward lesson, which is bigger than this card

Cycle 3's own words: *"this round retracted a claim honestly in six places and
then wrote **two new enumerations** — 'three routes remain', 'a subscript or an
attribute' — each falsified by a one-line variant of its own plant."*

**Stop enumerating residues. Name the limit by its shape, give the known entries
as examples, and let the owner card close it.** An enumeration is a claim with as
many edges as it has members; a shape has one. This is the third cycle in a row
where the mechanism was sound and the sentence beside it was not.

### Cycle 3 also closed

N-4 (U+00B7 verified unaddable — **11** offending literals across 3 modules, and
a 4th carries it in a `#:` comment the literal walk cannot see), N-5, N-6 (the
split discriminates: at `FOLIO_PT=11.0` the measurement passes and the identity
reds with its own sentence), F-5 (an independent `BinOp` walk returns exactly
`diagram_box` and `translation`; no third exists), and the tautology sweep over
both the new cell **and** the changed bodies — none.

## [UN-PARKED — 2026-10-26, orchestrator] The evidence the park waited for, and it vindicates the retraction

The park's condition was literal: *"Re-enter after CARD-295 runs: its round
exercises the same guards, so it supplies real evidence about whether F-302's
residue matters in practice."* CARD-295 cycle 2 ran. **The condition is met, and
the answer is not the one the orchestrator expected.**

### What CARD-295 measured

A 32-gon filled disc planted into `puzzle_page_stream` gives **7 failed / 14
errors** — the polygon route *is* closed on the puzzle page. The mechanism is
`marks_of` (`tests/test_book_puzzle_page_vector.py:328`), a whole-stream
**vocabulary default-deny** (ADR-0039/R2): five recognised operators — grey,
width, line, box, text — and a final `else: raise AssertionError` naming the
line. A Bézier's `c`, an XObject's `Do`, a clipping `W` and a bare `N g` fill
each stop the suite there.

### Why that does NOT transfer to this page, which is the real finding

The orchestrator's first reading was that CARD-296 should adopt `marks_of`'s
default-deny in place of the vertex bound. **That is wrong, and checking it
rather than asserting it is the only reason it is not now written into this
card as a remedy.** Two facts:

* `marks_of` is not a shared helper. It lives only inside CARD-295's own new
  test module and parses the puzzle page's vocabulary. Nothing of it is in
  `tests/helpers/pdf_vector.py`.
* **The puzzle page is closed because it writes no filled path at all.** An
  unsolved puzzle page is a grid and clue digits; `fill_grey`'s own spelling
  raises in that parser by design. Closure there is the *absence* of the
  vocabulary, not a stronger rule.

This page is not in that position, and it writes **both** of the vocabularies
cycle 2's defeating shapes were built from:

* `book_guide_vector.py:841-846` draws the worked example's arrow head as a
  **filled three-point polygon** — `fill_grey`, `begin_path`, two `line_to`,
  `close_path`, `paint("fill")`. So `m`/`l`/`h`/`f` are operators this page
  legitimately writes, and a 32-gon is the same operators with more `l` lines.
* `:581-589` fills the diagram's squares with `rectangle(..., paint="fill")`,
  which is `re` + `f`. That is **exactly** the vocabulary of cycle 2's second
  defeating shape, the staircase of 24 filled `re` bands.

So a vocabulary default-deny cannot separate the arrow head from a disc, nor the
diagram's squares from an `re` staircase, any better than a vertex count can.
**Both of cycle 2's counterexamples are built from operators this page has a
legitimate reason to emit** — the same structural fact cycle 2 established,
reached from the other direction.

### So the disposition stands, and is now evidenced rather than argued

Fix round 2's retraction — "no `c`" means "no **Bézier**", exactly, with the
straight-segment approximation carried as a **named limit owned by CARD-298** —
is correct, and cycle 3 said so in terms (*"THE DISPOSITION IS RIGHT"*). The
residue is **cross-page, not per-page**: no rule written in one page's test
module closes it, because the discriminator cannot be operator vocabulary or
vertex count. It has to be geometric — ink, or a rule on filled subpaths — which
is exactly ADR-0042/R1's derived per-page-kind check. **CARD-298 is the right
and only owner**, and CARD-295's round independently judged it not unowned in
practice: every page kind reaching a page before wave 65 has its own
artefact-side guard.

### This also sharpens cycle 3's first gating finding

F-301 is the stale comment at `tests/test_book_difficulty_dots.py:944`, which
still calls the polygonal disc route *"Bounded per page kind"*. It is worse than
stale: CARD-295 now shows that on the one page where the route really is shut,
it is not *bounded* at all — it is absent. The comment names a mechanism that
exists nowhere. Correcting it is still one line.

### State

**Un-parked to `ready`.** Cycle 3 put the distance to 8 at "three edits, two of
them one line of code each", and all three are prose or comment corrections over
mechanisms every one of which cycle 3 measured load-bearing. The review budget
(`max_cycles: 3`) is spent, so reaching a certified 8 needs an owner decision on
a fourth cycle; landing it as a declaration, as CARD-276 was, is the other
route. **The worktree at `0b91ab18` must not be removed** — see below.

### A loss this nearly caused, and the standing rule it breaks

`meta/review/20261026T074944Z-CARD-296-cycle3.yml` existed **only in the
worktree, untracked**. The standing practice is to remove a card's worktree at
merge; doing that here would have destroyed the cycle-3 review outright — the
one artefact that records why this card's disposition is right. This is the
**same defect as CARD-295's F-102**, in the same wave, from the same cause: the
round's artefacts are written where `meta/kanban` and `meta/review` are excluded
from the branch commit, so they survive only as untracked files in a directory
scheduled for deletion. Rescued and committed here. The orchestrator's own
copy of this card was also carrying fix round 2's **retracted** text — the
"route is now closed" paragraph that cycle 2 disproved — while the worktree held
the correction; main's copy is spliced to the honest version in this commit.

## [OWNER DECISION — 2026-10-27] Land it as a declaration, as CARD-276 was

The owner's words: *"let's land 296 as a declaration"*. Recorded as a **gate
decision**, not a certification: the card merges at **7.0 against
`min_score: 8`**, with `max_cycles: 3` spent, and the merge gate is what stands
behind it.

### The three edits cycle 3 put between 7.0 and 8 are made

Cycle 3's verdict named three, "two of them one line of code each", and was
explicit on the central question: ***"THE DISPOSITION IS RIGHT."*** All three
are done in `18d136ac`:

1. **F-301, the seventh site — closed.** `tests/test_book_difficulty_dots.py`
   still read *"a polygonal disc … Bounded per page kind"*, under a lead-in
   claiming each of the three routes *"is controlled elsewhere"* — the exact
   claim this card retracts 350 lines away. **Two merged guards contradicted
   each other on this card's central claim**, which is the worst form the defect
   could take, because each reads as corroboration of the other. Now: two of
   three are controlled, the third is a declared open limit, carrying cycle 2's
   measurement and CARD-295's complement.
2. **N-3 — closed, and at three sites rather than one.** Cycle 3 prescribed
   "three ast types in one isinstance tuple". The same blindness was also in the
   test's own two inline arms, so the question is now asked through one constant,
   `SEQUENCE_DISPLAYS`. **One residue kept deliberately and named**:
   `_names_bound_to_a_sequence` also counts `ast.Set` and this does not, so a set
   display is reported by neither. Cycle 3 prescribed and measured the three
   comprehension types; extending to `ast.Set` would have been an unmeasured
   widening of a guard on the way out the door.
3. **F-302 — corrected as a declaration, which is the only place it can be.**
   AC-4's residue **is larger than the three limits the round declared**. A
   complete second ruled grid is still drawable with the whole tree green —
   cycle 3 planted one as a frozen dataclass whose field is annotated `Layout`
   under a name `LAYOUT_SPELLINGS` does not seed, and measured **265 passed** on
   the three touched files and **715** on the blast radius. **Six such routes
   exist at helper level, none of them among the declared three**, and the
   round's generalisation — *"all three are the same shape: a receiver whose type
   a syntactic walk cannot establish"* — is **false for two of them**. The card
   now says that instead of the three-item enumeration.

### What is UNMET at merge, stated rather than implied

- **AC-4 is not met.** Its declared residue was wrong and is now declared
  correctly; the residue itself is open. The syntactic walk cannot enumerate its
  own escapes, which is the finding, not a gap in effort.
- **AC-3 was declined earlier in the card** and that decline is verified sound.
- **The cross-page residue is CARD-298's**, which holds ADR-0042/R1's derived
  per-page-kind check. CARD-295's round independently judged CARD-298 *not*
  unowned in practice: every page kind reaching a page before wave 65 has its own
  artefact-side guard.

### The last mile shipped UNCERTIFIED, and this is the board's own rule

`max_cycles` is a cycle budget, not a last-mile rule. **No reviewer has seen the
three edits above** — they were made by the orchestrator on cycle 3's own
prescription, and *"the reviewer told me to"* is not *"a reviewer saw the
result"*. What stands behind them is the **merge gate alone**, plus the fact that
F-301 and N-3 are a comment correction and a widened `isinstance` tuple
respectively, each verifiable by reading. F-302 changes no code at all.

**Deferred verification, declared.** At the time the edits were committed,
CARD-292 was measuring suite timings **solo** on this box, and a rival pytest is
precisely what invalidates its deliverable. So the two touched files, the blast
radius and the full merge gate were all deferred until CARD-292 handed back. The
gate result is recorded below when it runs; until then nothing here is claimed
green.

### The conflict resolution, because it decided whose claim survives

Main had moved four files this branch also touches, and two conflicted — both
where CARD-295's merged work meets this card's. The one that mattered:
`test_book_pdf_vector_primitives.py`'s class docstring, where **main's text was
taken over this branch's**, because CARD-295 cycle 1's F-004 had already
retracted the same claim with *three* measured escape routes where this card had
one, and named CARD-298 as owner. This card's 248-test 32-gon figure is kept
here on the card rather than in that docstring. The derived
`VECTOR_STREAM_METHODS` went the other way — this card's version survived
CARD-295's hand-written `frozenset({"line","rectangle","text"})`, because a set
derived from the class and narrowed by subtraction is the stronger guard.

## [MERGED — 2026-10-27] `d2255a58`, and the pre-check earned itself

**Merge gate: 9368 passed, 27 skipped, 0 failed, 0 errors, 1670.57 s (27:50).**
Host cells per AC-6: load **5.75 → 5.85**, rival-pytest **0 → 0** by `pgrep`.
All 27 skips attributed by name — **26 × `conftest.py:207`** (DATABASE_URL
unset) and **1 × `test_book_pdf_memory.py:1296`** (`setrlimit(RLIMIT_AS)`
refused by this kernel). 27 is the baseline exactly.

### Three failures the pre-check caught, and a per-file check would not

CARD-292's report landed hours earlier with the lesson that **files which pass
alone can red in company**. Running this card's three touched files *together*
on the **merged** tree found three failures before the 28-minute gate, not after.

**Two of them were one defect, and it is this board's own rule arriving as a
merge conflict.** CARD-295 and CARD-296 solved the same problem two different
ways and both landed: CARD-295 met `book_vector_draw`'s vector receivers by
adding **four named rows** to `NON_DRAW_RECEIVER_SITES`; this card met the same
receivers by **deriving the rule**. Auto-merge took both, so the table and the
predicate each claimed the same four calls — *widening a predicate and adding an
exemption are the same edit* (wave 49), and no textual merge can see it. The
four rows are **removed**, because this is an equality and a row that no longer
earns itself is a licence for whatever next takes that spelling.

**The third was this card's default-deny classifier doing its job on CARD-295's
new code.** `book_vector_draw.py:116` returns a freshly built `ContentStream`,
so the binding walk reported `unrecognised:Return` — a shape it had never met.
Added as a **named form**, not folded into `DRAW_BINDING_FORMS`, which carries an
obligation ("the name must be `stream`") that a return has nothing to satisfy it
with. The assertion stays an **equality**, so a second unbound construction reds.

### What is unmet, restated at merge

- **AC-4 is not met.** Its residue is open and **cross-page**, owned by
  **CARD-298**. The declaration is now correct; the hole is not closed.
- **AC-3 was declined** earlier in the card, and that decline is verified sound.
- **The last mile shipped UNCERTIFIED.** No reviewer saw cycle 3's three edits
  **or** the integration fix above. What stands behind them is this gate alone.
  The integration fix in particular was written by the orchestrator between the
  pre-check and the gate, which is the thinnest certification on this card.
- **One named residue inside a fix**: `SEQUENCE_DISPLAYS` deliberately omits
  `ast.Set` where `_names_bound_to_a_sequence` counts it, so a set display is
  reported by neither. Cycle 3 prescribed and measured the three comprehension
  types; widening further on the way out would have been unmeasured.
