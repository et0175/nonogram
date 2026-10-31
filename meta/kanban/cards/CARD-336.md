# CARD-336: The frame-centre oracle — one boundary-reading mechanism for the 39 placed-edge cells five modules read as first-inked-line

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** split from CARD-322 at the decompose station, 2026-10-31, on the owner's re-cut instruction. CARD-322 was 1d, priced against "five page kinds plus one test module"; re-measured here the conversion's residue is 154 reds and the placed-edge family is the single largest mechanism in it, named by ADR-0042/R6's own comment ("what the 0.254 mm reading needs is an oracle that reads the frame rule's CENTRE rather than its first inked line … that belongs with the conversion, i.e. to CARD-322") and by CARD-329's AC-6 disposition for `property/test_book_pdf_geometry.py` ("the frame-centre oracle is the only thing that closes them without a widening").
**Split from:** CARD-322
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** CARD-329, CARD-330
**Touches:** tests/helpers/page_ink.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/test_book_puzzle_frame.py, tests/test_book_guide_page.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is not a sub-item of the conversion

**It is one mechanism serving five modules, and the modules were measured.** Re-derived
at the decompose station on 2026-10-31 under CARD-329's own probe
(`scratchpad/card329/measure_probe.py`, `probe_puzzle_operators.py`, run on `b26bdd62`),
the whole 20-module census reproduces that card's figures to the digit — **17 of 20 red,
151 failed+error, 1224 passed, 1 skipped** — and inside the 151 the placed-edge family is:

| module | reds | what they are |
|---|---|---|
| `tests/test_book_pdf.py` | **30** of its 38 | the raster-pinned 25.45 mm placed-edge family and its neighbours, each reading its page through `page_ink`'s oracle (CARD-329 enumerated the 38 as 6 registry + 30 these + 2 of its own) |
| `tests/property/test_book_pdf_geometry.py` | **4** | every node id of the module, at **2.07x / 2.36x / 3.40x / 5.46x** the bound its own site carries |
| `tests/test_book_puzzle_frame.py` | **4** | `TwoUp` stroke-weight and placed-edge claims |
| `tests/test_book_guide_page.py` | **1** | the mirrored-centring offset, `assert 2.944881889763778 <= 2` |
| **total** | **39** | one mechanism |

**The bound is not one number and that is the point.** `property/test_book_pdf_geometry.py`
defines `PX_PER_MM = 300 / 25.4` and `HALF_PIXEL_MM = 0.5 / PX_PER_MM` = **0.042333 mm**
at `:69-70` and **mentions `EDGE_TOLERANCE_MM` zero times** (`grep -c EDGE_TOLERANCE` = 0);
each of its four sites is bound by a *different multiple* of `HALF_PIXEL_MM` (3/3/2/1), so
there is deliberately **no single range** over them and a widening normalised against one
of them is normalised against nothing. `tests/test_book_pdf.py`'s own bound is
`EDGE_TOLERANCE_MM = 0.1` behind a biconditional and `EDGE_TOLERANCE_EXEMPTIONS` is empty
and asserted empty. **Both figures are CARD-330's and neither is this card's to move.**

**What the oracle is.** `tests/helpers/page_ink.py`'s `Drawing` carries a comment that
states this card's whole subject: *"EVERY FIELD ABOVE IS AN INK EXTENT, NOT A BOUNDARY …
a grid rule is centred on the boundary it closes, and each `grid_*` above is the FIRST
inked pixel line of its rule — so the reading sits `(rule width - 1) // 2` outside the
boundary the page spec states … Compare ink with ink, or compare a coordinate with a
coordinate."* Every one of the 39 cells above compares an ink extent with a coordinate.
The oracle this card builds is the third option the comment does not offer: a reading
whose fields **are** boundaries, derived from the rule's own measured width on the page
rather than from a constant, so it is correct in **both** media and the 39 cells stop
being medium-dependent at all.

## This card lands BEFORE any page converts, and that is what makes it judgeable

Like CARD-312 and CARD-329, it is a test-side mechanism, not a conversion. Its judgement
is complete without a converted tree:

* on a **raster** page the new reading must agree with `Layout`'s own coordinate, which
  CARD-330 already measured to the pixel (the raster page's `Layout` places the two
  borders at **965 and 1851**, where `drawing_of` reports 963 and 1849 — the first inked
  line of a 6 px rule, `(6-1)//2 = 2` px outside);
* on a **vector** page it must agree with the content stream's own operand, which
  CARD-330 measured as sitting at the boundary within **1.0 px exactly** (0.0847 mm);
* and the two readings of the same page in the two media must then agree **with each
  other**, which is the claim the 39 cells are making and currently cannot.

So the oracle is verified against a coordinate in both media, and the 39 re-expressions
are verified under the conversion probe. **Both halves exist on `main` today** — see
*The probe, and why the one on main is not enough* below.

## What to implement

1. **The boundary reading, in `tests/helpers/page_ink.py`, beside the ink reading and not
   replacing it.** `Drawing`'s ink extents are load-bearing for every claim that is
   genuinely about ink (CARD-331's raster arm accounts them, and ADR-0042/R6 exempts the
   independent oracles by name). Add; do not convert in place. The rule width must be
   **read off the page**, not taken from a constant: the two media stroke different
   widths by design (ADR-0037/R2's declared 1.3 pt against COMP-007's proportional 6 px),
   which is exactly why a hard-coded `(6-1)//2` would be a second medium-dependency
   wearing the fix's clothes.
2. **Re-express the 39 cells, derived per module rather than listed.** The population is
   the cells that compare a `page_ink` extent against a coordinate. Derive it; a cell the
   walk cannot classify is a **FAILURE** per ADR-0039/R2, not a silent pass.
3. **`tests/test_book_pdf.py`'s pin must survive the re-expression, and it is the one
   thing here that can go silently wrong.** `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium`
   derives every site comparing against `EDGE_TOLERANCE_MM` and requires it to read its
   page through `drawing_of` and through **no** stream reader. A boundary oracle that
   reaches poppler is a stream reader, so re-expressing a pinned site through it is
   exactly the crossing the pin exists to catch. **Decide explicitly whether the new
   reader joins `_stream_readers()`' derived set or stays outside it, and say why** —
   and note that `_stream_readers()` is **derived, not listed** (CARD-329's F-002), so a
   new public reader in `page_ink.py` that the derivation does not recognise *reds*,
   which is the behaviour to want.
4. **Do not widen anything.** `EDGE_TOLERANCE_MM` stays `0.1`, `EDGE_TOLERANCE_EXEMPTIONS`
   stays empty and asserted empty, and `HALF_PIXEL_MM`'s four multiples stay 3/3/2/1. If
   a cell cannot be closed by reading the boundary, that is a **finding to raise with its
   measurement**, not a tolerance.

## The probe, and why the one on `main` is not enough

`scratchpad/card329/probe_puzzle_operators.py` lifts **`PageKind.PUZZLE` alone**, and its
own docstring says lifting the other four kinds "would measure a REFUSAL, not a converted
page". **Measured 2026-10-31 at the decompose station, that is no longer true and the
extension is two lines:** the refusal comes from `BookPDFGenerator.__init__` defaulting
`pages` to `NO_DOWNSTREAM_WRITERS`, and `book_interior_vector.DOWNSTREAM_WRITERS` is the
filled set, so rebinding the module-level default makes every `BookPDFGenerator(book)` in
the test tree an assembled generator. With all five temporary declarations lifted the
tree writes a real vector interior and nothing refuses — verified on
`tests/test_book_interior_face.py`, which is **green under the PUZZLE-only probe and red
at 2 under all five**.

**Two traps in that extension, both measured here, both yours to inherit rather than
rediscover:**

* **A test that lifts a declaration itself collides with the probe.** Derived by `ast`,
  **three** modules reference `_RASTER_DECLARATIONS` directly with **17** `monkeypatch.delitem`
  sites, and only two of them (`tests/test_book_pdf.py:5670` and `:5794`, CARD-329's own)
  pass `raising=False`. Every other site raises `KeyError: <PageKind.TITLE: 'title'>` at
  `_pytest/monkeypatch.py:302` when the probe has already removed the key — which presents
  as a red and is an **artefact of the instrument**, not of the conversion. Measured on
  `tests/property/test_book_export_interior.py` with only the four non-puzzle kinds lifted:
  **6 failed, of which 5 are that KeyError and 1 is genuine.** Build the probe so the two
  are distinguishable before you count anything.
* **`tests/test_book_interior_type_floor.py` is in neither of CARD-329's populations and
  is red at 3 under CARD-329's own probe** — see CARD-337, which owns it. Mentioned here
  because it is the proof that the 20-module census is not the whole disturbed set.

## Acceptance criteria

- **AC-1** (the reading is a boundary, in both media, against a coordinate): *Given* one
  page written in each medium, *then* the new reading equals the boundary `Layout` /
  the content stream states, and the two media's readings of the same page agree with
  each other — each asserted against a **coordinate**, never against the other medium's
  ink. **The class does not exist in the tree today; this card writes it**, so this AC is
  a review-lens on the round's own evidence until it does, owned by this card.
- **AC-2** (the ink reading survives untouched): *Given* `tests/helpers/page_ink.py`,
  *then* every existing `Drawing` field still reports the first inked line, byte for byte
  in its result, and `TestEdgeOffset_ThePixelOraclesStillReadPixels` is green
  **unmodified**. ADR-0042/R6 exempts the independent oracles by name and CARD-331's
  raster arm accounts their extents; a card that converted them in place would destroy
  the cross-check CLAUDE.md requires. (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)
- **AC-3** (the 39 are closed, derived not listed): *Given* a run under the
  five-declaration probe, *then* every placed-edge cell of the four modules in `Touches`
  passes, the population is **derived** by the comparison it makes rather than enumerated,
  and a cell the walk cannot classify is a FAILURE (ADR-0039/R2). **The 39 is a dated
  reading at `b26bdd62`, not a target**: state the number the round measures and the
  filter that produced it, and a different number is the finding.
- **AC-4** (nothing was widened, and it is asserted rather than claimed): *Given* the
  branch, *then* `EDGE_TOLERANCE_MM == 0.1`, `EDGE_TOLERANCE_EXEMPTIONS` is empty and
  asserted empty, `HALF_PIXEL_MM`'s four site multiples are unchanged at 3/3/2/1, and the
  pin class `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium` still reports a
  crossing — fired as a plant, not read as green. (test: the pin's own cells, plus AC-5's
  plant)
- **AC-5** (the change can fail): **Four plants minimum.** (a) the boundary reading
  returns the ink extent again — every re-expressed cell must red; (b) the rule width is
  taken from a constant instead of read off the page — the vector arm must red while the
  raster arm stays green, which is the cell that proves the derivation is load-bearing;
  (c) a re-expressed pinned site reaches a stream reader without saying so — the pin must
  red (this is CARD-329's MUT-13/MUT-16 shape re-aimed at this card's reader, and its
  closed walk is what must catch it); (d) the boundary reading is correct in one medium
  only — the cross-medium agreement cell must red. Each with its matched control measured
  green **in the same run**, and `0 skipped` asserted. (evidence: the plant table in
  `## Worktree notes`)

## Engineering constraints

- **EC(ADR-0039/R2):** the population of re-expressed cells is **derived** and the
  partition is total — every placed-edge cell in the four modules lands in exactly one
  class (re-expressed · already a coordinate comparison · a declared device-fact claim
  R6 exempts) and an unclassifiable one fails.
- **EC(ADR-0042/R6):** the new reading is a pixel oracle and therefore stays inside R6's
  first declared exemption (independent second-implementation oracles); it must not be
  used to recover a width the generator stated, which is R6's own discriminator.

## Guardrails

- **G-1: widen no bound.** `EDGE_TOLERANCE_MM`, `EDGE_TOLERANCE_EXEMPTIONS` and
  `HALF_PIXEL_MM`'s multiples are CARD-330's and are inherited closed. CARD-330 was cut
  to prevent exactly the widening that would close all 39 of these at once.
- **G-2: convert no page and flip no rule.** `_RASTER_DECLARATIONS` is untouched and no
  `src/` file changes. CARD-322 owns the conversions and ADR-0042/R1; CARD-312 owns R6's
  flip.
- **G-3: do not convert the ink reading in place.** Add beside it. See AC-2.
- **G-4: do not touch `tests/test_book_difficulty_dots.py` or `tests/helpers/round_ink.py`**
  — CARD-331's, and the arm re-point is CARD-322's.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference by `ast` over the five `Touches` paths — **not**
  `--collect-only`, which prints no node ids under this project's `addopts = "-q"`).
- **G-6: do not edit `tests/test_cli.py`'s structural layering guard.**
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`), and **commit no
  measurement dump**: the validator's check-ref search is a text search over tracked
  files excluding only `meta/architecture` and `*.md`, so a census pasted into a tracked
  `.txt` *revives* dead refs. CARD-329's `ref_pollution_check.py` is the instrument and
  the convention; this hazard is live on `main` across ~245 files and is carded as
  **CARD-335**.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream, with the independent oracles declared exempt (check: review-lens → **CARD-312 flips it, not this card**)
- ADR-0042/R2 — a raster page is declared with a reason (check: `test_every_raster_page_is_declared_with_its_reason`)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-5's plants)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-3)
- ADR-0039/R3 — an exemption is a claim and carries a control for what it must NOT absorb (check: AC-4)
- ADR-0037/R2 — the grid's rule weights, 0.3 / 0.8 / 1.3 pt bound to the vector medium; the reason a rule width cannot be a constant here (check: review-lens)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte

## Architecture context

- **FR:** FR-030, FR-032, FR-033
- **ADR:** ADR-0042/R6, ADR-0037/R2, ADR-0039/R1-R3
- **Components:** none in `src/` — `tests/helpers/` and four test modules
- **Trace:** not updated by this card. ADR-0042/R6's comment currently assigns the
  frame-centre oracle to **CARD-322** by name; **this card owns the amendment** that
  re-points that sentence here, and it is the only `meta/architecture` edit in scope.

## Worktree notes

- **[Why this is its own card — the re-cut's reasoning, 2026-10-31]** CARD-322 was 1d,
  priced against "five page kinds plus one test module". The measured residue is 154
  reds, and splitting followed CARD-309's own stated principle — *"one kind at a time,
  each removal complete… what makes this card incremental rather than all-or-nothing"* —
  applied to **mechanisms** rather than kinds, because the mechanisms are what is
  separately judgeable here: this card's judgement ("does the reading report the
  boundary, in both media, against a coordinate") is complete with no page converted,
  which is the same property that made CARD-312 and CARD-329 closable. The alternative —
  leaving it inside the conversion — reproduces CARD-309 exactly: a card holding four
  unrelated causes, which measured 189 failures + 75 errors and could not close.
- **[The estimate, and the calibration behind it]** 2d, by analogy with CARD-329, which
  was **2d estimated and 4.1h actual** for a comparable shape (one shared helper, five
  module repairs, 24 plants, a probe harness). This card is one shared helper, four
  module repairs, four plants and the same probe extended. The board's estimates in this
  family run long; 2d is the honest ceiling rather than a prediction.
- **[UNMEASURED PREMISE, stated as unmeasured]** *That reading the boundary closes all 39
  cells.* It is measured for **four** of them —
  `property/test_book_pdf_geometry.py`'s residuals are 2.07x–5.46x past multiples of
  `HALF_PIXEL_MM`, and CARD-330 measured the two media's ink-against-ink disagreement at
  1 px (grid edges) and 3 px (the drawing's own mitred left/top), which brackets them —
  and it is an **inference** for the other 35. **What would measure it:** re-express one
  cell per module first, under the five-declaration probe, and report the four before/after
  figures before touching the rest. That is this card's first job, and if a module's cells
  do not close, it is a finding with a measurement, not a tolerance (G-1).
- **[UNMEASURED PREMISE, stated as unmeasured]** *That `tests/test_book_guide_page.py`'s
  one red is this family.* Its site differences `drawing.left` — the mitre-affected edge,
  3 px / 0.254 mm by CARD-330's reading — against `page.width` and compares to a **2 px**
  bound, and it fails at **2.944881889763778 px**; the residual and the mitre agree to
  within a pixel, which is why it is routed here rather than to CARD-337. **What would
  measure it:** read the same page's boundary with the new oracle and show the offset
  falls inside 2 px. Until then the routing is a reading of the arithmetic, not a
  measurement.
- **[The fifth bucket's other half is NOT here, and not CARD-312's either]**
  `tests/test_book_arrange_page_breaks.py`'s red is `ValueError: too many values to
  unpack (expected 1, got 2)` at `:753` — `(alone,) = drawings_of(page)` finding **two**
  connected ink regions where one is expected. That is a question about the oracle's
  **region segmentation**, not about where an edge is, so the boundary reading does not
  touch it. CARD-329's F-004 routed both unplaced reds to "CARD-312's per-site
  disposition and CARD-322's frame-centre oracle"; the CARD-312 half is wrong — read at
  the decompose station, that card is a **static guard** that *classifies* sites and
  partitions the independent pixel oracles as **exempt**, and it states in as many words
  that it "can land before any page converts". A site it classes exempt is a site it does
  not repair. The segmentation red is **CARD-337's**.
- **[Expect the merge gate to find a frozen registry]** This card adds public functions to
  `tests/helpers/page_ink.py` and changes node ids in four modules. `_stream_readers()`
  derives over **both** owner helpers' public surface and `_MEDIUM_BLIND_READERS` is the
  hand-written other half of that partition, so a new public reader lands in one of them
  or the completeness cell reds. Derive which registries your diff touches and run them
  before the gate does — two cards in one hour on 2026-10-30 went red at the gate on
  exactly this, and `review.test_scope: impact` is structurally unable to see it.
- **[Do not paste the number a frozen baseline prints when it reds.]** Re-derive the
  symmetric difference, assert **nothing left**, and resolve each entrant to a real
  `def`/`class` line read off the line. A class that *shrinks* because a review report was
  synced in is signal loss, not a repair.
