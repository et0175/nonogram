# CARD-330: The 0.169 mm the two media disagree by is 2 raster pixels — measure which one is at the specified margin before calling it a convention

**Status:** review
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/330-edge-offset-is-two-device-pixels`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-330
**Source:** CARD-309's implementation round, 2026-10-30, as the decisive one of the four causes that blocked its AC-1 — re-measured by the orchestrator at the decompose station, where the framing changed (see below).
**Idea:** —
**Wave:** 70 <!-- STAMPED 2026-10-31 at dispatch, into the slot CARD-309 freed at merge. It could not start earlier: this card and CARD-329 both touch tests/test_book_pdf.py, which CARD-309 also touched, so all three conflicted and CARD-318 opened the wave instead. Measured free of CARD-318 (requirements.yml/trace.yml/solver tests vs page_ink/test_book_pdf/adr-0042 -- intersection EMPTY), which is why the wave runs one vector card beside one generator/solver card. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/helpers/page_ink.py, tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** 2026-10-30T23:16:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists — and why it is NOT the card CARD-309's round asked for

CARD-309 implemented the puzzle-page conversion in full and measured that it reds
**189 failures + 75 errors across 22 modules**. Root-caused, the decisive cause was
this: the raster and vector media place the same grid **2 device pixels apart on all
four edges**, re-derived on CARD-295's own `Twin` fixture — ink `grid_left/right`
**963/1849** against stream **965/1851** — while `tests/test_book_pdf.py:121` sets
`EDGE_TOLERANCE_MM = 0.1`. Since **0.169 > 0.1**, every placed-edge expectation in
the tree changes value with the medium.

That round proposed a **convention decision** and routed it to CARD-312.
**Both halves of that routing are wrong, and this card exists because of it:**

1. **CARD-312 does not own it.** Measured 2026-10-30: CARD-312's text mentions no
   tolerance, no offset and no `page_ink` site. Its item 2 partitions the 321
   pixel-reading sites into classes — including "an independent **oracle** R6 exempts
   by name", which is what these instruments are — so it owns **whether a site must
   convert**. It does not own **what a placed-edge expectation means when both media
   are legal and disagree**. That question was unowned until this card.
2. **"Convention" may be the wrong word entirely.** The orchestrator re-derived the
   figure at the decompose station: **2 px at 300 dpi is 0.1693 mm**, and 300 dpi is
   the interior's own render DPI. The gap is **exactly two raster pixels** — the size
   of a rounding step, not of a design difference. The raster path quantises the
   grid's edge to whole pixels; the vector path writes an exact coordinate. So the
   two numbers are not two opinions about where the grid goes: **one of them is a
   quantisation of the other.**

**Which makes the first question a product question, not a test question**, and it
must be answered before any tolerance is touched: the assertions compare against
**specified** values (`25.45` mm and friends — a margin the board chose, see
`tests/test_book_pdf.py:606`). So: **which medium actually puts the grid at the
specified margin?** If the vector does and the raster is 0.169 mm off, then the
raster has always been 0.169 mm wrong, `EDGE_TOLERANCE_MM = 0.1` was tuned to
accommodate its own error, and widening it to admit the vector would be **loosening
a bound to make room for the more accurate medium**. That is the one outcome this
card must not ship by accident.

**This is a hypothesis, not a finding.** It is written down so it is tested rather
than discovered, per the board's wrong-but-declared rule. It may be false — the
vector writer may genuinely be placing the grid 2 px off, in which case this is a
defect in the vector writer and the tolerance was right all along.

## [Owner steer 2026-10-30] Vector is the destination; do not spend the card fixing raster

*"I think let's aim at switching on vector for the interior (not dividers) — don't
spend much time on fixing-updating raster."*

**This narrows the card, and the narrowing is the point.** The card was written to
*reconcile* the two media — three outcomes, one of which was "the raster is the
inaccurate one". That third branch now has a disposition attached rather than an
open question:

- **If the vector is at the specified margin and the raster is 0.169 mm off**
  (the measured hypothesis), **do not fix the raster.** Pin its expectations as
  legacy, state in one line that they encode a 2-device-pixel quantisation the
  vector does not have, and let **CARD-322's conversion retire them**. Re-tuning a
  medium the interior is leaving is exactly the work the owner has ruled out.
- **If the vector is the one off spec**, that is still a finding and still stops the
  card — a vector writer placing the grid wrong is a defect the destination medium
  carries forward, and it is cheap now and expensive after CARD-322.
- **If the offset is not uniform**, unchanged: the premise is wrong and that is the
  result.

**What this does to item 2 (the geometry instruments).** `page_ink.py`'s `drawing_of`
and `two_up_ink` stay pixel oracles — G-2 is unchanged — but their disposition is now
**medium-pinned rather than medium-aware**: pin each placed-edge expectation to the
medium it was measured in, so the raster rows keep passing untouched until the
conversion removes them. That is less work than making both media satisfy one
expectation, and it is the honest shape: the two numbers are a quantisation of one,
not two opinions, so one expectation for both was always going to encode the
rounding.

**What this does NOT change.** The measurement in item 1 still has to happen, and
`EDGE_TOLERANCE_MM` still may not be widened without its exemption and control
(G-1). "Don't invest in raster" is not "accept any figure" — it is a decision about
*which medium gets the effort*, and the effort still has to establish which one is
right. **The one outcome the steer forbids outright is widening the bound to admit
the more accurate medium**, which was already this card's named hazard.

### And the device floor is the same arithmetic, now scoped to one medium

The 0.169 mm this card measures **is ADR-0037/R2's device floor** — 2 device pixels
at 300 DPI, the figure R2's 2026-10-17 amendment set as the thin-rule minimum. So
this card's question and the interior's furniture-floor question are one measurement
seen from two sides, and the owner's steer settles the harder half: **the interior is
going vector, so the floor question is vector-only.** ADR-0042/R7 already says the
device floor is *inapplicable to the interior* because a content-stream line has no
device pixel to clear — while ADR-0037/R2 says furniture that must not drop out on
press is held to that same floor "for the dropout reason directly". **Those two
collide, and nothing on the board owns the collision.**

Two cards wait on it — **CARD-208** (ruled boxes for clue numbers) and **CARD-226**
(a two-up page split by a *light rule*); **CARD-215 was the third and is now
postponed**. Both of the remaining two also quote a **superseded** R2 in their System
contract rows and need that re-derived whatever is decided.

**This card is the right place to produce the figure and the wrong place to decide
the policy**: R7's own caveat says the owner judged *renders, not paper*, that dot
gain at 0.1058 mm and whether 35% grey reads as guidance are *measured by nobody*,
and that the revisit trigger is **the first printed book or proof**. So: measure the
offset here and state what it implies for a vector hairline; leave the floor's
*policy* to the owner at the proof, and record in ADR-0042 that R2-vs-R7 is
unresolved for interior furniture rather than letting a reader infer a floor that
neither rule grants.

**Dividers stay raster** — unchanged by all of this. ADR-0042/R2 declares the divider
an exception by scheduling, not technique, and CARD-231 redesigns the page to be
*born* vector rather than converted.

## What to implement

1. **Decide the question above, by measurement, before touching anything.** For a
   seeded corpus of trims and page counts, compute where the grid's edges *should*
   be from the page spec alone (the specified margin arithmetic, derived — not read
   from either renderer), then compare **both** media against it. Report three
   numbers per edge: specified, raster, vector. **One of these is the answer:**
   - the vector is at the specified position and the raster is 2 px off → the raster
     is the inaccurate medium; the expectation stays, and the raster's own assertions
     are the ones carrying an undeclared 2 px slack;
   - the raster is at the specified position and the vector is off → **a defect in
     the vector writer**, and this card becomes a bug report, not a convention;
   - both are off, or the offset is not uniform → say so; the premise is wrong and
     that is the finding.
2. **Then, and only then, dispose of the geometry instruments.**
   `tests/helpers/page_ink.py`'s `drawing_of` and `two_up_ink` are **independent
   oracles** — they read pixels deliberately, as a second implementation, which is
   why R6 exempts that class by name. They are not file readers to convert. What they
   need is to be **medium-aware or medium-pinned**, and which one follows from item 1.
3. **Do not widen `EDGE_TOLERANCE_MM` as the fix.** If the answer to item 1 makes a
   wider tolerance correct, the widening ships **with its exemption and that
   exemption's control in the same commit** (the standing rule), and the ADR records
   why a bound moved. A bound widened without that record is how a medium's error
   becomes the board's convention.
4. **Record the decision in ADR-0042**, as a note on R6 or a new rule, naming which
   medium is canonical for a placed-edge claim and why. CARD-312, CARD-322 and
   CARD-329 all read this decision; it must exist in one place.
5. **Do NOT convert any page and do NOT flip R1 or R6.** This card decides a
   measurement's meaning. The conversions are CARD-322's and the readers are
   CARD-329's.

## Acceptance criteria

- **AC-1** (the three numbers exist, per edge, derived): *Given* a seeded corpus
  spanning trims, interior **page numbers at both parities** and both arms of
  FR-032's vertical placement, *then* for every edge of every case the test
  reads **specified / raster / vector** in millimetres, the card records the
  **relation** those three stand in — in millimetres, with one worked case
  carrying the per-edge figures — the specified value is derived from the page
  spec rather than read from either renderer, and a minimum case count is
  asserted inside the test **against the enumerated span rather than against
  the generator that built the corpus**. (test:
  `TestEdgeOffset_TheThreeNumbersAreDerivedPerEdge`)
  <!-- AMENDED 2026-10-31, fix round 1, cycle 1's F-103: this read "spanning
  trims and page counts" and "the card records specified / raster / vector in
  millimetres". Page *count* is not a swept variable and never was — the
  corpus sweeps 24 interior page NUMBERS, whose parity is the geometrically
  operative part, and asserts that parity as a set equality. And what the card
  records is the relation, with the per-edge millimetre figures living in the
  test; one worked case is now in the table below so a reader does not have to
  run it. The final clause is new in the same round, from F-001: a floor read
  off the generator is not a minimum. -->
- **AC-2** (the offset is characterised, not assumed): *Given* those numbers, *then*
  the card states whether the gap is **uniformly 2 px at the render DPI** on all four
  edges and across the corpus, or is not — and if it is not uniform, that is recorded
  as the finding and AC-3 is answered against the real shape. (test:
  `TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels`)
- **AC-3** (the question is answered and written down): *Given* AC-1's numbers,
  *then* ADR-0042 records which medium is at the specified margin, which is
  canonical for a placed-edge claim, and why — in one place, named by CARD-312,
  CARD-322 and CARD-329. (test: `TestEdgeOffset_TheAdrRecordsTheCanonicalMedium`)
- **AC-4** (no bound is loosened silently): *Given* the branch, *then* either
  `EDGE_TOLERANCE_MM` is **unchanged**, or it changed **together** with a declared
  exemption naming what it now admits and a control that reds if the exemption is
  widened further. **Two mutants:** one inside the claimed region, one at its edge.
  (test: `TestEdgeOffset_ATolerenceChangeCarriesItsExemption`)
- **AC-5** (the oracles stay oracles): *Given* the disposition of item 2, *then*
  `drawing_of` and `two_up_ink` still read pixels as an independent second
  implementation — they are **not** rewritten to read the content stream, because an
  oracle that shares the subject's mechanism has stopped being one. (test:
  `TestEdgeOffset_ThePixelOraclesStillReadPixels`)
- **AC-6** (nothing converted, nothing flipped): *Given* the branch, *then* no
  interior page's medium changed, `_RASTER_DECLARATIONS` is untouched, and neither
  ADR-0042/R1 nor R6 is flipped. (test: the existing
  `test_no_declaration_outlives_the_cards_that_remove_it`, run unmodified)

## Guardrails

- **G-1: do not widen `EDGE_TOLERANCE_MM` without its exemption and control**
  (AC-4). This is the card's whole hazard.
- **G-2: do not convert `drawing_of` or `two_up_ink` to stream readers.** They are
  R6's named exempt class — independent oracles. Converting them destroys the
  cross-check, which is CLAUDE.md's stated reason for having two implementations.
- **G-3: convert no page, flip no rule.** CARD-322 owns the conversions and R1;
  CARD-312 owns R6's flip.
- **G-4: do not edit `src/nonogram/admin/book_*.py`** unless item 1's answer is "the
  vector writer is placing the grid wrong" — in which case **stop and raise it**, do
  not fix it here. A defect in the writer is a different card with different
  baselines, and CARD-309's worktree is still open on those files.
- **G-5: do not lower a corpus minimum**, and regenerate nothing under
  `tests/fixtures/**`.
- **G-6: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference with `-o addopts=''`).
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT` —
  `meta/profiling/rank_durations.py` greps `tests/**` for render idioms and
  `tests/test_suite_profile.py` asserts the set as an equality).

## System contract

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream, with the independent oracles exempt by name (check: **review-lens**; CARD-299 owes the flip; this card disposes of two of those oracles)
  <!-- CORRECTED 2026-10-31, fix round 1, cycle 1's F-105: this row read
  "(check: CARD-299's)", which reads as mechanically checked. Re-derived from
  the ADR: R6's block carries `check: {kind: review-lens}`, and its own
  comment records that CARD-299 was dispatched to flip the check to the
  planned test and deliberately did NOT — the lens MUST survive CARD-299 by
  the same decision, and the flip is CARD-312's. The board's standing rule is
  the one being met: a planned test ref reads as mechanically checked, so use
  review-lens plus a named card owing the flip. -->
- ADR-0042/R1 — interior pages are operators (check: review-lens — **this card does not flip it**)
- ADR-0037/R2 — the device floor (check: review-lens; the 2 px figure is a device fact and R2's own subject)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-4's mutant pair)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-2's not-uniform arm)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)

## Architecture context

- **FR:** FR-030, FR-032, FR-040
- **NFR:** NFR-008
- **ADR:** ADR-0042/R1, R6, ADR-0037/R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** `trace.yml` carries no ADR-0042 rule rows (re-checked 2026-10-29 by CARD-309's round); no row is re-stamped here.

## Worktree notes

### [Item 1's answer: the card's third branch — the premise is false, and neither medium is off spec]

**Measured 2026-10-31.** Corpus: 24 puzzle pages, hand-built with
`random.Random(330 + index)`, over three trims (8.5x11, 7.5x9.25, 6x9 in), both
parities, both arms of FR-032's vertical placement (`ratio` and `footer`), every
page framed. **96 grid-edge readings.** `tests/test_book_pdf.py::TestEdgeOffset_*`,
**25 tests** (24 at cycle 1, one added in fix round 1), all green.

The minimum is asserted inside the test, and **fix round 1 is what made that
sentence true**: at cycle 1 the floor was the same constant the fixture counted
with, so `len(corpus) >= _MIN_EDGE_CASES` was satisfied by construction for any
value of it — re-measured, lowering it to 3 left all 24 tests green with 87.5 %
of the corpus gone. The floor is now the literals `_MIN_EDGE_CASES = 24` and
`_MIN_EDGE_READINGS = 96`, asserted **equal to the enumerated span** AC-1 names
(3 trims x 2 parities x 2 vertical bounds x 2 draws, and 24 x `len(_GRID_EDGES)`),
with the fixture counting from a separate `_EDGE_CASE_COUNT`. See the fix-round
section below for the mutants.

**Instruments, with their domains** — this is the whole finding:

| instrument | what it reads | at |
|---|---|---|
| `_specified_grid_mm` | the page spec's own arithmetic, in exact millimetres; reads no renderer, no `compute_layout`, no `book_page_spec` | — |
| `_stream_grid_mm` | the written PDF's `m ... l S` operands at 1.3 pt, flipped on the page's **MediaBox** | the file |
| `page_ink.drawing_of` on `BookPDFGenerator._blank_page` | Pillow's bitmap, the **first inked pixel line** of each rule | 300 DPI |
| `page_ink.drawing_of` on `pdf_vector.rendered_page` | **poppler**'s raster of the same page, same reading | 300 DPI |

**The three numbers per edge.** Uniform over all 24 cases and all four edges —
these are set equalities in the tests, not averages:

| reading | where it lands | mm from the boundary |
|---|---|---|
| **specified** (derived) | the boundary | 0 — it *is* the boundary |
| **vector**, content stream | the boundary, worst gap **1.0 px** over the corpus | ≤ **0.0847** |
| raster rule **centreline** (`Layout.position`) | the boundary | 0.0000, to the pixel |
| **raster**, ink (`drawing_of`) | boundary **- 2 px** | **-0.1693** |
| vector, ink (poppler 300 DPI) | boundary **- 3 px** | **-0.254** |

1 device pixel at the interior's own 300 DPI is `25.4 / 300` = **0.084667 mm**,
which is where every figure in the `mm` column comes from.

**And one worked case, per edge, in millimetres** — F-103 asked for this
rather than the relation alone. Derived, not retyped: printed by
`scratchpad/card330/one_worked_case.py 0`, which calls the test module's own
`_edge_case`. Case 0 is `29x12 d1 page 6 on 216x279 mm`, vertical bound
`ratio`, framed. The content stream carries no `drawing_*` operand — a framed
drawing's outer edge is the `re`, not a grid rule — so that column is blank by
construction and not by omission:

| edge | specified | stream | raster ink | vector ink |
|---|---|---|---|---|
| `grid_left` | 19.050 | 19.050 | 18.881 | 18.796 |
| `grid_right` | 203.200 | 203.200 | 203.031 | 202.946 |
| `grid_top` | 85.657 | 85.683 | 85.513 | 85.429 |
| `grid_bottom` | 161.857 | 161.883 | 161.713 | 161.629 |
| `drawing_left` | 12.700 | — | 12.700 | 12.446 |
| `drawing_top` | 79.307 | — | 79.333 | 79.079 |

Read off that one case: `19.050 - 18.881 = 0.169` mm (2 px) on the grid's left
edge, a further 0.085 mm (1 px) to the vector's ink, and `12.700 - 12.446 =
0.254` mm (3 px) on the drawing's own left edge — the three figures of the
table above, in one page's numbers.

and on the drawing's own outer edges — `Drawing.left`/`top`, which is what every
25.45 mm assertion in `tests/test_book_pdf.py` actually reads:

| reading | where it lands | mm from the margin |
|---|---|---|
| **specified** | the margin | 0 — it *is* the margin |
| **raster**, ink | the margin, within **0.5437 px** (sub-pixel rounding only) | ≤ **0.0460** |
| vector, ink | the margin **- 3 px** | **-0.254** |

The raster figure was "within 1.0 px" at cycle 1, which was the *derived*
ceiling and not a measurement; fix round 1 measured the worst case over the
corpus at **0.5437 px** (`16x25 d5 page 13 on 190x235 mm`, `drawing_left`) and
the test now asserts 0.6 px rather than 1.5 (F-003).

**Re-derived on CARD-309's own fixture, so the card's own figure is not taken on
trust:** ink `grid_left/right` **963/1849**, stream **965/1851** — exactly as
CARD-309 reported. **And the raster page's own `Layout` places those two borders
at 965 and 1851 too** (heavy rule 6 px). So the raster's rule is centred on 965;
963 is where its ink begins.

**So: which medium is at the specified margin? BOTH.** The specified boundary,
the vector stream's operand and the raster's rule centreline are one number. The
2 px is `drawing_of`'s leading-ink-edge reading of a rule *centred* on that
boundary, differenced against a path coordinate — an ink extent against a
coordinate, two instruments with different domains. **There was never a
convention to hold.** `G-4` is not triggered; no `[BLOCKER]` is raised; the
vector writer is not placing the grid wrong.

### [The reframing in the brief was half right, and the half that was wrong matters]

The brief (and the card) say the 0.169 mm "is ADR-0037/R2's device floor" and
that this "is not a coincidence". **Measured, it is a coincidence of two
different constants.** The offset is `(rule width - 1) // 2`, and the raster
book border is 6 px because `PageSpec.min_thin_rule_mm = 0.25` mm is 2.95 px
rounded **up** to 3 and the heavy rule is exactly twice the thin one. R2's floor
is `RASTER_RULE_FLOOR_PX = 2` — a floor on a rule's *thickness*. One is half a
rule, the other is a minimum rule. They happen to be the same two pixels.

The control that separates the two readings is in the suite, not in prose: the
**thin** rule's own ink edge is `(3 - 1) // 2 = 1` px out, so the offset tracks
the rule's weight. A quantisation of the grid's *position* would not.

The brief's "2 px at 300 dpi is 0.1693 mm" arithmetic is correct and was
re-derived (`2 * 25.4 / 300 = 0.169333`). What it is the size of is not a
rounding step.

### [What CARD-322 inherits, read ink against ink]

One oracle, one resolution, one page — the only like-for-like comparison there
is:

* the grid's four edges: **1 device pixel, 0.0847 mm**, uniform. The two media
  stroke different widths by design (R2's declared 1.3 pt = 5.4167 px against
  COMP-007's proportional 6 px). **Inside** `EDGE_TOLERANCE_MM = 0.1`.
* `Drawing.left` / `Drawing.top`: **3 device pixels, 0.254 mm**, uniform.
  **Outside** it. Cause: a framed drawing is one stroked `re`, whose outer
  corner a PDF rasteriser **mitres** half a rule beyond the path, where Pillow
  strokes four butt-capped lines and the frame's top-side group begins two rows
  above where its left side starts. Both writers put that side at the same
  coordinate — it is a corner, not a placement.

**So the figure that will actually red CARD-322's conversion is 3 px / 0.254 mm
on the drawing's outer edges, not 2 px / 0.169 mm on the grid's.** The fix is an
oracle that reads a frame rule's **centre** rather than its first inked line —
still a pixel oracle, so still R6-exempt (G-2) — and it belongs with the
conversion, not here.

### [Disposition applied: medium-pinned, derived rather than declared]

Per the owner's steer, the raster is not fixed and its expectations are not
re-tuned. They are **pinned**, and the pin is mechanical so that a conversion
cannot slip past it: `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium`
walks this module with `ast`, finds every function that names
`EDGE_TOLERANCE_MM`, and requires each to read its page through `drawing_of` and
none through a content-stream reader. Default-DENY per ADR-0039/R2. **Three**
named exemptions (sites that assert the bound or compare two media rather than
measuring a page), and a second test asserts every exempted name still exists,
so the list cannot rot into a blanket exemption. `EDGE_TOLERANCE_MM` itself
carries the one-line statement of which medium it was measured in and which card
retires it.

**Fix round 1 made the walk's key unique, and that is what makes the
default-DENY sentence above true.** At cycle 1 the map was keyed on the bare
function name, and this module holds two different tests called
`test_the_drawing_sits_25_45_mm_from_the_left_trim_edge` — one on the
right-hand page, one on the left. One of the two was overwritten and never
checked, so the guard's verdict depended on `ast` walk order rather than on the
code: converting the right-hand site to a content-stream reader left all four
pin assertions green, while the identical change to the left-hand one red two.
The key is now the **class-qualified** name, the walk returns a list so the key
count can be asserted equal to the site count, both members of that collision
are named in `_COLLIDING_SITES` and asserted present, and the exemption
register matches on the function part. Neither test was renamed (G-6).

**Re-derived counts, with the basis stated** — the figure differs by basis and
the defect does not, so both are recorded:

| basis | naming functions | distinct keys |
|---|---|---|
| the guard's own walk (`ast.Name` id is `EDGE_TOLERANCE_MM`), bare key | **15** | **14** |
| the same set, class-qualified key | **15** | **15** |
| `test_`-prefixed functions whose source *text* mentions it, bare key | **17** | **16** |

Exactly one site is lost on either basis, and it is the same one.

### [`EDGE_TOLERANCE_MM`: unchanged]

`0.1`, untouched. `EDGE_TOLERANCE_EXEMPTIONS` is new, **empty**, and asserted
empty through `_tolerance_is_declared`, which refuses: a widening without its
exemption, an exemption without its widening, and a *narrowing* (the third shape
default-DENY has to cover). The arm AC-4 leaves open — a widening that ships with
its exemption — is asserted to be admitted, so the predicate is not a constant
`False`.

### [Mutant table — 8 mutants, 8 killed, 0 survivors]

Protocol: committed at `9100372b` **before** mutating; SHA-256 asserted before
each mutant and after each `git checkout --` restore; `*.pyc`/`__pycache__`
swept before and after each; driver `scratchpad/card330/mutate.py`,
`PYTHONDONTWRITEBYTECODE=1`, `-o addopts=''`. Every anchor asserted unique
before substitution.

| # | target | mutation | region | verdict | what red |
|---|---|---|---|---|---|
| M1 | `tests/test_book_pdf.py` | `EDGE_TOLERANCE_MM` 0.1 -> **0.3** | inside | KILLED | 1 failed |
| M2 | `tests/test_book_pdf.py` | `EDGE_TOLERANCE_MM` 0.1 -> **0.1001** | edge | KILLED | 1 failed |
| M3 | `src/nonogram/admin/book_page_spec.py` | `min_thin_rule_mm` 0.25 -> **0.5** (border 12 px, offset 5) | inside | KILLED | 2 failed |
| M4 | `src/nonogram/admin/book_page_spec.py` | `min_thin_rule_mm` 0.25 -> **0.2541** (3.0012 px, the smallest floor that rounds up to 4) | edge | KILLED | 2 failed |
| M5 | `tests/test_book_pdf.py` | a new function naming the bound and reading no page | inside | KILLED | 1 failed |
| M6 | `tests/test_book_pdf.py` | one character off an exempted site's name | edge | KILLED | 2 failed |
| M7 | `tests/helpers/page_ink.py` | the oracle imports `pdf_vector` | inside | KILLED | 1 failed |
| M8 | `tests/helpers/page_ink.py` | `drawing_of` builds its own mask instead of `_dark` | edge | KILLED | 1 failed |

Only `mutate.py` is committed under `scratchpad/card330/`. The two exploratory
probes that preceded the tests were **deleted rather than kept**, and the reason
is worth one line because it is a trap: both flipped the stream's y against the
**stored trim** (235 mm) instead of the page's **MediaBox** (2774 px =
234.86 mm), a 1.6 px error that made the vertical edges of one trim in three
read 3 px out instead of 2 — an instrument error that looks exactly like a
medium disagreeing, in the same card that exists because of one. The measurement
now lives in the tests, where the flip is against the MediaBox and said so in
`_stream_grid_mm`'s docstring.

M1/M2 are AC-4's named pair. M3/M4 are the pair for the 2 px claim and they are
the interesting ones: the claim is not "2 px", it is "half the rule", so the
mutant that moves the rule's width by one pixel has to red it — and does.

### [Runs, and the skip attribution]

All with `-o addopts=''`, `-p no:randomly`, cwd the worktree, and
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python` (this
worktree has no venv). `meta/kanban/.full-suite.lock` absent throughout; none
written. **The full suite was not run.**

| run | result | skips |
|---|---|---|
| baseline, pre-change: `test_book_pdf` + `test_book_export_interior_cover` + `test_suite_profile` | **671 passed** | **0** |
| post-change, those three plus `test_book_page_frame`, `test_book_puzzle_page_vector`, `test_book_pdf_two_up` | **834 passed** | **0** |
| `test_check_ref_resolution` | **23 passed** | **0** |
| the remaining 16 `page_ink` readers (`tests/property/test_book_export_interior`, `test_book_pairing`, `test_book_pdf_geometry`, `test_book_cell_size`, `test_book_difficulty_dots`, `test_book_divider_pages_option`, `test_book_guide_page`, `test_book_pdf_band`, `test_book_pdf_ink_mode`, `test_book_pdf_memory`, `test_book_proof_pages`, `test_book_puzzle_frame`, `test_book_qr_slot`, `test_book_solved_answer_key`, `test_book_solved_page`, `test_book_grid_rules`) | **1025 passed** | **1** |
| `test_book_pdf.py` whole module, post-refactor | **112 passed** | **0** |

**Skip attribution — one skip, named, and it is not mine.**
`tests/test_book_pdf_memory.py:1297`, the `setrlimit(RLIMIT_AS)` cell: *"cannot
bound a process on this platform — the kernel refuses it"*. A **platform** gate,
pre-existing, in a module this card touches only through a comment in
`page_ink`, and its own skip message names the test that carries AC-2's executed
half instead. **Not** one of the suite's 27 `DATABASE_URL`-gated skips, none of
which is in this impact set.

`tests/test_book_puzzle_page_vector.py`'s `needs_poppler` marks did **not**
skip — poppler is installed on this host (`/opt/homebrew/bin/pdftoppm`,
`pdftotext`) — and CARD-330's own `_needs_poppler` is the same gate, so on a
host without poppler its 24 tests would skip *and say so* rather than pass
quietly. That is a real exposure of this card's measurement: on a poppler-less
host AC-1 and AC-2 do not run, which `-rs` would report by name.

Node-id set difference on `tests/test_book_pdf.py`, `--collect-only -q`:
**88 -> 112, 0 removed, 24 added** (G-6). The whole diff to that file is
insertions.

### [ADR-0042: two additions, and the second is a non-decision on purpose]

1. **A note on R6** naming the **content stream** canonical for a placed-edge
   claim — because its coordinate *is* the specified boundary, not by
   preference — with the instrument table, the figures above, and why the bound
   was not widened. CARD-312, CARD-322 and CARD-329 all read this; none needs to
   re-measure it.
2. **`## What this does NOT decide` gains "the device floor for interior
   furniture"**, recorded as **unresolved**. ADR-0037/R2 holds dropout-critical
   furniture to 2 device pixels; ADR-0042/R7 makes the floor inapplicable to the
   interior "because a content-stream line has no device pixel to clear".
   **Measured, R7's premise is true of the stream and false of the device the
   stream is printed on:** poppler renders the 0.3 pt cell line, at its declared
   35% grey (grey 89, never diluted by coverage), as

   | resolution | 0.3 pt is | device pixels inked |
   |---|---|---|
   | 150 DPI | 0.625 px | **1** |
   | 300 DPI | 1.25 px | **2** |
   | 600 DPI | 2.5 px | **2** |
   | 1200 DPI | 5.0 px | **5** |

   So at the interior's own 300 DPI a vector hairline clears R2's floor
   *exactly*, by the rasteriser's stroke adjustment and not by anything the
   writer declared — and fails to clear it at 150. **No floor is invented
   here.** R7's caveat stands: the owner judged renders, not paper; dot gain and
   whether 35% grey reads as guidance are measured by nobody; the revisit
   trigger is the first printed book or proof. The two cards waiting on it
   (**CARD-208**, **CARD-226**; **CARD-215** postponed) still quote a superseded
   R2 and still need it re-derived whichever way the owner goes.

No rule flipped, no page converted, `_RASTER_DECLARATIONS` untouched; AC-6's
evidence is the existing `test_no_declaration_outlives_the_cards_that_remove_it`
run unmodified, green in the 834-passed run above.

### [Fix round 1 — two guards stop asserting a strength they do not have]

**Cycle 1 scored 7.5** (min_score 8) and did not dent the conclusion: the
reviewer re-derived the premise-false finding from scratch, found the raster
renderer's own `Layout` placing the vertical borders at **965 / 1851** —
identical to the stream's operands, ink at 963 / 1849, no residual anywhere in
the chain — and confirmed both retractions from source. **Nothing in this round
changes a measured figure.** What it changes is two controls whose prose said
closed and whose mechanism was open, plus three cheap documentation gaps.
`src/` is still untouched (`git diff --name-only db366763..HEAD -- src/` is
empty), no page is converted, no rule is flipped, and the ADR diff is still
**zero deletions** (160 insertions now, 12 of them this round).

**F-001 — the corpus floor was self-referential, and it enforced 3, not 24.**
The fixture built the corpus as `range(_MIN_EDGE_CASES)` and the guard then
asserted `len(corpus) >= _MIN_EDGE_CASES`; `_MIN_EDGE_READINGS` restated the
same tautology. Both sides read one constant, so neither assertion could fail
for any value of it. The floor is now the literals 24 and 96, asserted **equal
to the enumerated span AC-1 names** — `len(_EDGE_TRIMS) * len(_EDGE_PARITIES) *
len(_EDGE_BOUNDS) * _EDGE_DRAWS_PER_COMBINATION`, and `_MIN_EDGE_CASES *
len(_GRID_EDGES)` — and the fixture counts with its own `_EDGE_CASE_COUNT`.
Dropping a span dimension reds the floor; shrinking the corpus reds the floor;
lowering the floor reds the span equality. This is **CLAUDE.md's test style**
in terms, not merely ADR-0039/R1: *"'property' tests instead build large seeded
corpora by hand with stdlib `random.Random`, asserting a minimum case count
inside the test itself so the corpus can't silently shrink. Prefer an
independent second implementation over re-deriving a value with the same
function you're testing."* The span is enumerated; it is not the generator
re-read. **G-5 is honoured in the direction it points: no minimum was lowered,
one was made real.**

**F-002 — the medium pin dropped a site instead of failing.** Keyed on
`node.name`, and this module holds two different tests named
`test_the_drawing_sits_25_45_mm_from_the_left_trim_edge` (right-hand page, and
left-hand page, in two classes). The key is now class-qualified, the walk
returns a list so the key count is asserted equal to the site count, both
colliding keys are named and asserted present, and `_BOUND_ONLY_SITES` matches
on the function part. **No test was renamed** (G-6) — renaming was the obvious
shortcut and is the one the guardrail forbids. See the counts-by-basis table
above; the defect is exactly one lost site on every basis.

**F-003 — AC-1's only control was 1.5 px, which is 0.127 mm.** Wider than the
0.1 mm this card refused to widen, and the reviewer measured both 1.05 and
12.0 passing, so that one constant decided AC-1's answer. There are now **two**
live bounds, both measured rather than derived: `_SPEC_MEASURED_PX = 1.05` on
the grid edges (measured worst **1.0 px** exactly) and
`_SPEC_DRAWING_MEASURED_PX = 0.6` on the drawing's own edges (measured worst
**0.5437 px**). `_SPEC_ROUNDING_PX = 1.5` stays as the *documented* derived
ceiling and is asserted to be a ceiling; the span test also asserts
`_SPEC_MEASURED_PX / PX_PER_MM < _STATED_EDGE_TOLERANCE_MM`, so the
derivation's bound can never drift back out past the placed-edge bound it is
not. **F-003 was not permission to widen anything, and nothing was widened:
`EDGE_TOLERANCE_MM` is still `0.1` and `EDGE_TOLERANCE_EXEMPTIONS` is still
empty (G-1).**

**F-105** — the System contract's R6 row said "check: CARD-299's". Re-derived
from the ADR: R6 carries `check: {kind: review-lens}` and its own comment
records that CARD-299 was dispatched to flip it and deliberately did not. The
row now says review-lens with CARD-299 owing the flip.

**F-103** — AC-1 said "page counts" where the corpus sweeps page *numbers* and
their parities, and said the card records the three numbers in millimetres
where the `mm` column was empty in three of five rows. AC-1 is amended and the
tables above now carry the millimetre figures plus **one worked case**, derived
by `scratchpad/card330/one_worked_case.py` rather than retyped.

#### [Fix-round mutants — 8 planted, matched pre and post]

Protocol as cycle 1's: committed **before** mutating (`90d300ae`; for the
`pre` phase the fix sat in `git stash`, not in the working tree, so
`git checkout --` could not discard it), anchors located by **text** and
asserted unique in both phases, SHA-256 before each plant and back to the
identical digest after restore, `*.pyc`/`__pycache__` swept before and after
each, `PYTHONDONTWRITEBYTECODE=1`, `-o addopts=` with `-p no:randomly`, and a
**non-zero count asserted on every run** (a `-k` that selects nothing exits 0).
Driver `scratchpad/card330/mutate_fixround.py`, committed beside cycle 1's.

| # | finding | mutation | region | **pre** (54e9e553) | **post** (90d300ae) | what reds now |
|---|---|---|---|---|---|---|
| R1 | F-001 | the corpus shrinks to 3 cases, floor untouched | inside | **SURVIVED** 24 passed, 1.39 s | **KILLED** 3 failed | the span test + both uniformity floors |
| R2 | F-001 | 24 -> 23: the smallest shrink there is | edge | **SURVIVED** 24 passed, 6.49 s | **KILLED** 3 failed | the same three |
| R3 | F-001 | the **floor** halved to 12 | edge | **SURVIVED** 24 passed, 3.65 s | **KILLED** 1 failed | the span equality |
| R4 | F-002 | the **first** colliding site reads a content stream | inside | **SURVIVED** 4 passed | **KILLED** 2 failed | the raster-oracle and no-stream pins |
| R5 | F-002 | the **second** of the pair, identical change | edge | **KILLED** 2 failed | **KILLED** 2 failed | the same two — the matched control that makes R4 a measurement |
| R6 | F-002 | the key reverts to the bare function name | inside | *no anchor* (it mutates the fix) | **KILLED** 1 failed | the new collision control |
| R7 | F-003 | the derived column moves 0.3 px (worst gap 1.3 px) | inside | **SURVIVED** 24 passed | **KILLED** 2 failed | both derivation arms |
| R8 | F-003 | 0.06 px: the smallest move the measured bound catches | edge | **SURVIVED** 24 passed | **KILLED** 1 failed | the grid-edge arm |

The nodes each one reds, by id (all under `tests/test_book_pdf.py`):

* R1, R2 — `TestEdgeOffset_TheThreeNumbersAreDerivedPerEdge::test_the_corpus_spans_trims_parities_and_both_vertical_bounds`, `TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels::test_the_rasters_ink_is_two_device_pixels_outside_the_stream_on_every_edge`, `…::test_the_two_media_ink_differs_by_one_device_pixel_not_two`
* R3 — the span test alone (the floor's own control, which is the point)
* R4, R5 — `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium::test_every_site_reads_its_page_through_the_raster_ink_oracle` and `…::test_no_site_reads_a_content_stream`
* R6 — `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium::test_no_two_sites_collapse_into_one_key`
* R7 — `TestEdgeOffset_TheThreeNumbersAreDerivedPerEdge::test_the_specified_position_is_where_the_content_stream_puts_the_grid` and `TestEdgeOffset_TheGapIsUniformlyTwoDevicePixels::test_the_drawings_own_edge_is_where_the_media_pass_the_tolerance`
* R8 — the grid-edge arm alone

**R1/R2/R3 are the control F-001 said was missing**: a plant that shrinks the
corpus, or lowers the floor, with nothing else touched. All three were absorbed
silently before this round and all three red now.

#### [Fix round 1 — node ids, and the run]

`ast` set difference on `tests/test_book_pdf.py`, test-prefixed functions,
class-qualified, cross-checked against `--collect-only -q` with `-o addopts=`:

| from | to | ast ids | removed | added | collected |
|---|---|---|---|---|---|
| `db366763` (the cut) | `90d300ae` | 84 -> 109 | **0** | **25** | 88 -> 113 |
| `54e9e553` (cycle 1) | `90d300ae` | 108 -> 109 | **0** | **1** | 112 -> 113 |

The one added id is
`TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium::test_no_two_sites_collapse_into_one_key`.
The 4-id gap between the `ast` count and the collected count is the module's 3
pre-existing `parametrize` decorators and is the same on both sides. **G-6
holds: nothing deleted, renamed, skipped or merged.**

| run | result | skips |
|---|---|---|
| `tests/test_book_pdf.py` whole module | **113 passed** | **0** |
| the 9-module impact set (`test_book_pdf`, `test_book_puzzle_page_vector`, `test_book_page_frame`, `test_book_pdf_two_up`, `test_book_export_interior_cover`, `test_book_grid_rules`, `test_book_pdf_memory`, `test_suite_profile`, `test_check_ref_resolution`), `-rs` | **941 passed** | **1** |

**Skip attribution — the same one skip, and it is still not this card's.**
`tests/test_book_pdf_memory.py:1297`, the `setrlimit(RLIMIT_AS)` cell: a
**platform** gate whose own message says the kernel refuses every soft limit on
this host. Pre-existing, in a module this card touches only through a comment in
`page_ink`. **Zero skips introduced by this round.** `meta/kanban/.full-suite.lock`
absent throughout and never written; `NONOGRAM_IGNORE_FULL_SUITE_LOCK` never
set; the full suite was not run (impact scope).

#### [Routed residue — real, and not this card's]

* **F-101 → CARD-322.** The pin has no honest exemption class for a site
  *legitimately* converted to the stream, which is the direction ADR-0042/R6
  mandates. The only pre-built hatch is `_BOUND_ONLY_SITES`, whose declared
  meaning is "names the bound without measuring a page" — a converted site does
  measure a page, so adding it there would make that register's own
  documentation false. **Measured as part of this round**: the register has 3
  names, every one asserted to exist, and the pin's predicate is "every
  non-exempt site names the raster", not "every site names exactly one medium
  and which one is recorded". The honest move is the second predicate, or a
  separately-named `_STREAM_PINNED_SITES` with its own exists-control. It
  belongs with the conversion: CARD-322 owns it, and the pin reds on arrival
  by design so the medium has to be restated deliberately.
* **F-102 → CARD-322.** `_specified_grid_mm`'s **vertical** arm re-implements
  the renderer's clearance *algorithm* rather than the specification:
  `-(-_RASTER_HEAVY_PX // 2) + -(-_furniture_px // 2) + 1`, with a hard-coded
  `_furniture_px = 3` and a "+1 makes clear strict" pixel. So it can inherit
  the same mistake, and the anti-copy control
  (`…is_not_either_mediums_ink_reading`) only proves the column is not a
  renderer *reading*, not that it is not a renderer *rule transcribed*. The
  **horizontal** arm is genuinely spec-derived (trim/gutter/outside/band/cell,
  written out in this module rather than imported) and was confirmed as such.
  **The card's conclusion does not rest on the vertical arm**: it rests on
  `Layout.position == stream operand` and `ink = position - (w-1)//2`, both
  verified without the derived column at all. Recorded here rather than
  repaired, because narrowing the derivation is work on the geometry CARD-322
  converts.
* **F-104 — pre-existing and out of scope, deliberately not repaired.**
  CON-019's check ref resolves to no `def` or `class` line anywhere in the
  repository; its hits are two docstrings, three registry files and **two
  previously synced review YAMLs**, so the validator's text search is currently
  satisfied by prose. That is the dead-ref family CARD-316 / CARD-317 /
  CARD-319 own. **No review YAML was edited in this round**, which is the one
  move that would make the ref look alive again.
* **F-106 / F-107 — confirmations, nothing to do.** The reviewer independently
  reproduced both incidental findings (`pdf_vector.rendered_page` defaulting
  `out_dir` to the cwd; `test_book_grid_rules.py:210`'s own fallback) and the
  documented instrument error (the stored 235 mm trim against the 2774 px
  MediaBox = 1.64 px), and judged both dispositions correct.

#### [Declarations re-derived in this round]

* **F-001** — the Worktree notes' "minimum asserted inside the test … so it
  cannot silently shrink" and the span test's own docstring both now say what
  the code does, and say what it did before. AC-1 gained the clause that a
  floor is asserted against the span and not the generator.
* **F-002** — the pin class's "Default-DENY per ADR-0039/R2" docstring now also
  covers a site that cannot be *told apart*, and the disposition section says
  the key is class-qualified and why. The exemption count in that section was
  "two"; it is three, re-counted off the register.
* **F-003** — `_SPEC_ROUNDING_PX`'s own comment says it is the derivation's
  ceiling and no longer a live bound; ADR-0042's three-number table gained a
  zero-deletion amendment recording the measured 1.0 px / 0.5437 px and the
  asserted 1.05 px / 0.6 px, because the ADR's `< 1.5 px` row was the looser
  fact a reader would have inherited. The card's own two tables carry the
  figures.
* **F-105 / F-103** — the card's System contract row and AC-1, both corrected
  against the artefact they describe rather than reworded.
* **No `src/` declaration changed**, because no `src/` behaviour did.

### [Findings for other cards]

* **CARD-322** inherits the pin and the 0.254 mm. The conversion will red
  `Drawing.left`/`top` assertions, not `grid_*` ones, and the repair is an
  oracle reading a rule's centre — not a wider tolerance. The pin reds on
  arrival, by design, so the medium has to be restated deliberately.
* **CARD-312** owns the per-site disposition of the 321 pixel-reading sites.
  One datum for it: `page_ink.drawing_of` and `two_up_ink.drawings_of` are not
  merely "oracles R6 exempts" — their readings are **ink extents**, so a site
  that differences one against a stream coordinate is measuring half a rule
  whatever its disposition. That is now stated on `Drawing` itself.
* **CARD-309's routing was wrong in a third way** nobody had noticed: it
  compared `page_ink`'s `grid_left` against a stream coordinate, which no
  tolerance can reconcile because the two are not the same quantity. The
  existing cross-medium seam in
  `tests/test_book_puzzle_page_vector.py::test_the_ink_and_the_stream_rule_the_same_grid`
  already knew this — it asserts the offset is one value and `|offset| * 2 <=
  heavy`, i.e. *at most half a heavy rule* — and it has been green all along.
* **`pdf_vector.rendered_page` defaults `out_dir` to the current directory**,
  so a caller that forgets it writes `vector.pdf` and `page-1.png` into the repo
  root. This card's first draft did, and `git status` caught it. Measured on the
  tree: all five existing call sites pass an `out_dir`, and one of them
  (`tests/test_book_grid_rules.py:210`) passes `self._tmp_path or Path(".")`, so
  it falls back to the cwd if its own fixture is unset. A default of `None`
  meaning "the repo root" in a helper used under pytest is worth a line in
  whichever card next touches that file.

- **[The reframing is the card's main contribution, and it was the orchestrator's,
  not the implementation round's.]** CARD-309's round delivered the measurement
  (963/1849 vs 965/1851) and called it a convention question. At the decompose
  station the arithmetic was re-derived — 2 px at 300 dpi is 0.1693 mm, and 300 dpi
  is the interior's own render DPI — which makes the gap exactly one rounding step
  and the two values **not two opinions but a quantisation of one**. Re-derive both
  the measurement and the arithmetic before building on either.
  - **[RETRACTED 2026-10-31 by the implementation round, which did re-derive
    both, as this note asked.]** The measurement holds to the pixel
    (963/1849 vs 965/1851) and the arithmetic holds
    (`2 * 25.4 / 300 = 0.169333`). **The conclusion does not.** The two values
    are not a quantisation of one: the raster page's own `Layout` places those
    borders at **965 and 1851** as well, so both media put the grid at the same
    pixel, and 963/1849 is where the *ink* of a 6 px rule centred on 965 begins.
    The 2 px is `(rule width - 1) // 2` — half a rule — which the thin rule's
    own 1 px offset proves, and it is therefore not a rounding step and not
    ADR-0037/R2's device floor arriving by another road. See the sections above.
- **[Why P1 when nothing is broken]** It blocks CARD-322, which blocks the whole
  vector interior phase from reaching a reader, and it is the one of CARD-309's four
  causes that no existing card owned. The other three are CARD-329, CARD-331 and a
  re-derivation CARD-309 already did.
