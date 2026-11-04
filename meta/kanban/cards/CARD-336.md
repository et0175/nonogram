# CARD-336: The frame-centre oracle — one boundary-reading mechanism for the 5 measured placed-edge cells in 2 modules

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/336-the-frame-centre-oracle`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-336
**Source:** split from CARD-322 at the decompose station, 2026-10-31, on the owner's re-cut instruction. CARD-322 was 1d, priced against "five page kinds plus one test module"; re-measured here the conversion's residue is 154 reds and the placed-edge family is the single largest mechanism in it, named by ADR-0042/R6's own comment ("what the 0.254 mm reading needs is an oracle that reads the frame rule's CENTRE rather than its first inked line … that belongs with the conversion, i.e. to CARD-322") and by CARD-329's AC-6 disposition for `property/test_book_pdf_geometry.py` ("the frame-centre oracle is the only thing that closes them without a widening").
**Split from:** CARD-322
**Idea:** —
**Wave:** 74
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** CARD-329, CARD-330, CARD-338
<!--CARD-338 ADDED 2026-10-31 by the orchestrator, answering the re-cut's own judgement call 3. The re-cut built the five-kind probe extension, ran the census, and then described the instrument in prose in this card, CARD-337 and CARD-322 rather than carding it. Three cards quoting the same undelivered instrument is how CARD-309 happened -- five `expires_with` entries nobody owned, four cards that built writers with zero call sites. CARD-338 owns it, and its deliverable is the measured floor this card's premise needs: CARD-329's probe lifts PageKind.PUZZLE ALONE, so every figure this card inherits is measured against one fifth of the conversion. -->
**Touches:** tests/helpers/page_ink.py, tests/property/test_book_pdf_geometry.py, tests/test_book_puzzle_frame.py
<!--RE-CUT 2026-11-04 on the owner's instruction, after this card's own round measured its population. tests/test_book_pdf.py REMOVED: its 30 placed-edge cells fail before any edge comparison and its own pin records that CARD-322's conversion RETIRES them rather than repairing them -- see CARD-342. tests/test_book_guide_page.py REMOVED: its one cell is 0 under the five-kind filter and what is red there is a different mechanism -- see CARD-343. -->
**Review score:** —
**Started:** 2026-11-04T03:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is not a sub-item of the conversion

**It is one mechanism serving two modules, and the modules were measured.** Re-derived
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

> **[RETRACTION 2026-11-04, AFTER MEASUREMENT — this supersedes the premise correction below,
> which was WRONG in its expectation. Read this first.]**
>
> **The orchestrator's premise correction predicted that the placed-edge population would GROW
> under the five-kind filter. It does not. The card's 39 was RIGHT, and the correction's
> expectation is refuted** (ADR-0039/R4: a figure recomputed and refuted is retracted
> everywhere it was written; this is that retraction).
>
> Measured by CARD-336's round under `scratchpad/card338/census_five_kinds.py`, `--causes`,
> `unaccounted=0` and `0 skipped` in both passes:
>
> | | `PUZZLE` only | all five kinds |
> |---|---|---|
> | placed-edge cells | **39** — reproduces the card exactly | **38** |
> | `tests/test_book_pdf.py`'s placed-edge share | 30 | **30, unmoved** |
>
> **Where the orchestrator's reasoning failed:** `tests/test_book_pdf.py`'s MODULE total does
> move 38 → 46 under five kinds, exactly as CARD-338 measured. But the placed-edge
> SUBPOPULATION inside it is 30 under both filters — the +8 is `delitem` residue and
> registry/divider/text cells, none of them this card's. The correction inferred movement in a
> derived subpopulation from movement in its parent total. **That is the same error shape as
> predicting a census would move because a declaration site was removed: the parent and the
> subpopulation are different quantities, and only one of them was measured.**
>
> **The figure was never the problem. The COMPOSITION is.** Of the 38, only **5** are cells a
> frame-centre oracle can close — 4 in `property/test_book_pdf_geometry.py`, 1 in
> `tests/test_book_puzzle_frame.py`. The other 33 split into 30 cells that fail *before* any
> edge comparison (a `ContentStream` reaching a pixel reader, no page-source seam) and 3
> stroke-weight readings that are a different mechanism. **So this card's title claim holds for
> 2 of its 4 modules and 5 of its 39 cells**, and the card is under re-cut rather than
> implementation. Its round implemented nothing, by design, and that was the correct call.

> **[PREMISE CORRECTION 2026-11-04, at the wave-74 station — read this before the table above.]**
>
> **The 39 is a `PageKind.PUZZLE`-ONLY figure**, and this card knows the distinction well
> enough to apply it twice below — `test_book_interior_face.py` 0 → 2, and
> `test_book_interior_type_floor.py` 3 → 8 — while never applying it to **its own headline
> population**. The table's `tests/test_book_pdf.py` row reads *"30 of its 38"*; CARD-338
> measured that module at **46** under the five-kind probe. So the placed-edge share of the
> real end state is **UNMEASURED**, and 39 is a lower bound on it, not the number.
>
> **This is stated as unmeasured rather than replaced by a guess**, which is this board's
> convention for the vector family: a premise about the converted tree can only be settled by
> standing the counterfactual up. **Item 0 settles it** — see "What to implement".
>
> **Also corrected:** the title and this section said *"five modules"*; the table lists
> **four**, and the re-cut that produced it reported four. The fifth was never named. The
> seventeen-module figure elsewhere in this card is a different population — the consumers of
> the ink-extent oracle, not the modules carrying placed-edge reds.

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

0. **Re-derive the placed-edge population under the FIVE-KIND probe before anything else.**
   The 39 in this card is a `PUZZLE`-only figure (see the premise correction above), so the
   first act of this round is to run `scratchpad/card338/census_five_kinds.py` — **run it, do
   not rebuild it** — and re-derive the per-module placed-edge counts against the end state
   this card's oracle actually has to serve. Expect the total to **grow**; `test_book_pdf.py`
   alone moves 38 → 46 across the whole module.
   **If it does not grow, that is a finding and this card's framing is wrong** — say so rather
   than reconciling it. Record both numbers side by side, the way CARD-338 recorded its own.
   **The estimate was priced against 39.** If the five-kind population is materially larger,
   raise it before implementing rather than absorbing the growth silently — scope that grows
   inside a round is the shape this board's scope gate exists to catch.



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

## The probe: CARD-338 built it, and this card runs it rather than extending it

<!-- REWRITTEN 2026-11-03 by CARD-338. This section used to describe the five-kind
     extension as two lines for THIS card to write, and carried a figure measured at the
     decompose station. CARD-338 owns the instrument, committed it, and re-derived every
     figure; the prose that told this card to build it is gone, because three cards
     describing one undelivered instrument is how CARD-309 happened. -->

**The instrument exists: `scratchpad/card338/probe_five_kinds.py`**, driven by
`scratchpad/card338/census_five_kinds.py`. Run it, do not rebuild it.
`scratchpad/card329/probe_puzzle_operators.py` lifts **`PageKind.PUZZLE` alone**;
CARD-338's lifts all five kinds whose `expires_with` names CARD-322 and rebinds
`book_pdf_generator.NO_DOWNSTREAM_WRITERS` to `book_interior_vector.DOWNSTREAM_WRITERS`, so
every `BookPDFGenerator(book)` in the tree is an assembled generator and the four
downstream kinds are drawn rather than refused. It refuses by name if any one of the five
declarations is already absent, if the rebinding target has been renamed, if the writer set
is partial, or if the constructor has stopped reading the global — proved against mutated
trees by `scratchpad/card338/prove_refusals.py`, so a run that reads green over a tree it
did not change is not a thing this instrument can do.

**The measured floor, re-derived by CARD-338 on 2026-11-03 at `f407c350`** (one file-scoped
run per module, `-o addopts=` as two argv items, `-rfs` as one flag, the full environment
inherited):

| over CARD-329's 20 modules | `PUZZLE` only | all five kinds |
|---|---|---|
| modules red | 17 / 20 | **18 / 20** |
| failed + error | 151 | **225** |
| passed | 1224 | 1150 |

`tests/test_book_interior_face.py` — one of the three modules CARD-329 reports as fully
green — is **0 under the PUZZLE-only probe and 2 under all five**, confirmed.

**Two things to inherit rather than rediscover, both re-derived:**

* **A test that lifts a declaration itself meets a key that is already gone.** By `ast`,
  **three** modules reference `_RASTER_DECLARATIONS` with **17** `monkeypatch.delitem`
  sites; **2** pass `raising=False` (`tests/test_book_pdf.py:5670`, `:5794`) and **15** can
  raise; of those 15, **two** name `DIVIDER`, which the probe does not lift — leaving **13
  sites that can raise**. **Separately measured, the census counts 13 reds** from them:
  `property/test_book_export_interior.py` **5**, `test_book_interior_type_floor.py` **1**,
  `test_book_pdf.py` **7**. **Two different quantities, neither derived from the other** —
  one literal site produces 5 reds alone, and two of the 15 (`test_book_pdf.py:3747`,
  `:3774`) sit inside `for kind in self._interior_kinds()` loops covering 4+ kinds each, so
  their agreeing on 13 is a coincidence of this tree. The component of the **+74** these
  reds account for is **+11**, not +13. **Do not price them out as the probe's shadow:**
  CARD-338 measured the identical `KeyError` on a tree whose five entries are deleted in
  `src/` with no probe loaded, so they are residue the conversion owns.
* **`tests/test_book_interior_type_floor.py` is in neither of CARD-329's populations** —
  CARD-338 derives it as a third population reaching the hazard through the medium
  decision itself. It is red at **3** under the PUZZLE-only probe and at **8** under five
  kinds. CARD-337 owns it; it is named here only as the proof that the 20-module census is
  not the whole disturbed set.

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
- **AC-3** (the 5 measured cells are closed, derived not listed): *Given* a run under the
  five-kind probe (`scratchpad/card338/probe_five_kinds.py`, CARD-338's, driven by
  `census_five_kinds.py`), *then* every placed-edge cell of the **two** modules in
  `Touches` passes — **4 in `tests/property/test_book_pdf_geometry.py` and 1 in
  `tests/test_book_puzzle_frame.py` (`drawing.left`)** — the population is **derived** by
  the comparison it makes rather than enumerated, and a cell the walk cannot classify is a
  FAILURE (ADR-0039/R2).
  **These 5 are the measured residue of a 38-cell family, and the other 33 are not this
  card's**: 30 fail before any edge comparison (no page-source seam; **their recorded disposition is
  CARD-322's conversion, which RETIRES them** — the pin in `tests/test_book_pdf.py` says so
  in its own docstring) and 3 are stroke-weight readings (CARD-342). **Re-derive the 5 rather than trusting this
  line** — it is a dated reading, and a different number is the finding.
  **Two figures this card's round measured that the implementation must respect** —
  *both of them corrections to what this AC said before, retracted here under ADR-0039/R4
  (a figure recomputed and refuted is retracted everywhere it was written, and an AC is
  the one place a later reader treats as binding); re-derived a third time at the merge
  gate, 2026-11-04, and reproducing to the digit:*
  - **The cell is `drawing.left`, not `drawing.top`.** That assertion fails on *both*
    fields under the probe — **left 2.5039 px, top 2.7323 px** against the 1.5 px
    `EDGE_TOLERANCE_PX` — and `left` asserts one line **above** `top` in
    `TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame::test_both_slots_sit_where_con_018s_millimetres_put_them`,
    so the **2.504 this AC used to carry was the LEFT residual attributed to TOP**. Both
    are re-expressed. (F-1.)
  - **The half-rule is 2.5 px, not 2.71 px.** The 2.71 was an *inference* from
    1.3 pt at 300 DPI = 5.4167 px. Measured, poppler inks that stroke as **six** pixel
    lines, exactly as Pillow strokes six — `left_rule_px == top_rule_px == 6` in **both**
    media — so the half rule is 2.5 px, and the ink-to-centre offset is **+0.5 px in
    raster and +2.5 px in vector** (for a boundary `c`, Pillow inks `c-2..c+3` and
    poppler `c-3..c+2`). **The implementation holds no half-rule constant at all** — it
    reports the run's own measured centre, which is why *any* constant, 3 or 2.71 or 2.5,
    is wrong in one medium. The inference was right that a hard-coded 3 would miss this
    cell; it was wrong about why. (F-2.)
- **AC-4** (nothing was widened, and it is asserted rather than claimed): *Given* the
  branch, *then* `EDGE_TOLERANCE_MM == 0.1`, `EDGE_TOLERANCE_EXEMPTIONS` is empty and
  asserted empty, `HALF_PIXEL_MM`'s site multiples are unchanged as the full multiset
  **`{2: x2, 3: x4, 4: x2}` across EIGHT constant-multiple sites, plus two bare
  mentions** — re-derive it with `ast`, and note that **no `1 x` multiple exists anywhere
  in that file**. An earlier wording here said "four site multiples unchanged at 3/3/2/1";
  that was the multiple carried by each of the four FAILING assertions, not the module's
  site count, and an assertion written against it would have asserted something untrue of
  the file (refuted by this card's own round, F-5, and re-derived independently at the
  station). And the
  pin class `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium` still reports a
  crossing — fired as a plant, not read as green. (test: the pin's own cells, plus AC-5's
  plant)
- **AC-5** (the change can fail): **Four plants minimum.** (a) the boundary reading
  returns the ink extent again — every re-expressed cell must red; (b) the rule width is
  taken from a constant instead of read off the page — **which arm reds depends on where
  the constant is anchored, and this AC's original wording ("the vector arm must red while
  the raster arm stays green") named only one of the two**: anchored on the drawing's own
  ink edge the **raster** arm reds and the vector arm is correct; anchored on the raster
  medium's +0.5 px offset the **vector** arm reds and the raster arm is correct. The card
  could not know that without the oracle, so the round planted **both** — (b1) and (b2) in
  the plant table — rather than picking the arm this text guessed. That is deliberately
  **more** than this AC asked for, not a correction to it: the claim as stated is *correct
  in both media*, and a claim with two directions needs a control that can fail in either
  (ADR-0039/R1). Either way it is the cell that proves the derivation is load-bearing;
  (c) a re-expressed pinned site reaches a stream reader without saying so — the pin must
  red (this is CARD-329's MUT-13/MUT-16 shape re-aimed at this card's reader, and its
  closed walk is what must catch it); (d) the boundary reading is correct in one medium
  only — the cross-medium agreement cell must red. Each with its matched control measured
  green **in the same run**, and `0 skipped` asserted. (evidence: the plant table in
  `## Worktree notes`)

  **Plants (c) and AC-4's pin both target `tests/test_book_pdf.py`, which the 2026-11-04
  re-cut REMOVED from `Touches`. That is deliberate and not a contradiction**, so it is
  stated here rather than left for a reviewer to read as a scope violation: `Touches`
  governs the files this card **changes as a deliverable**. A mutant is planted and then
  **restored from captured content**, so the file is byte-identical afterwards and nothing
  is delivered in it — the SHA-256 before plant and after restore is the evidence. Planting
  into a module outside `Touches` to measure a pin is a measurement, and this card's own
  round already did exactly that twice with the hashes recorded. **What is forbidden is
  leaving an edit there**, which AC-4's byte-identity check is what proves.

## Engineering constraints

- **EC(ADR-0039/R2):** the population of re-expressed cells is **derived** and the
  partition is total — every placed-edge cell in the two modules lands in exactly one
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
- **[The estimate, and the calibration behind it]** 2d, by analogy with CARD-329, on a
  comparable shape: one shared helper, five module repairs, 24 plants, a probe harness.
  This card is one shared helper, four module repairs, four plants and the same probe
  extended. **CARD-329's `Actual: 4.1h` is deliberately EXCLUDED from this estimate**
  under the owner's ruling of 2026-11-03 that wall-clock actuals measure the queue rather
  than the work; an earlier draft of this bullet rested on that 4.1h and the comparison
  has been re-grounded on the size datum above (helper + module-repair + plant counts),
  which is the substitute the ruling calls for. The board's estimates in this family run
  long; 2d is the honest ceiling rather than a prediction. **Item 0 may invalidate the
  size datum** — it re-derives the population the counts were taken against.
- **[UNMEASURED PREMISE, stated as unmeasured]** *That reading the boundary closes all 39
  cells.* It is measured for **four** of them —
  `property/test_book_pdf_geometry.py`'s residuals are 2.07x–5.46x past multiples of
  `HALF_PIXEL_MM`, and CARD-330 measured the two media's ink-against-ink disagreement at
  1 px (grid edges) and 3 px (the drawing's own mitred left/top), which brackets them —
  and it is an **inference** for the other 35. **What would measure it:** re-express one
  cell per module first, under CARD-338's five-kind probe, and report the four before/after
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
  `tests/helpers/page_ink.py` and changes node ids in two modules. `_stream_readers()`
  derives over **both** owner helpers' public surface and `_MEDIUM_BLIND_READERS` is the
  hand-written other half of that partition, so a new public reader lands in one of them
  or the completeness cell reds. Derive which registries your diff touches and run them
  before the gate does — two cards in one hour on 2026-10-30 went red at the gate on
  exactly this, and `review.test_scope: impact` is structurally unable to see it.
- **[Do not paste the number a frozen baseline prints when it reds.]** Re-derive the
  symmetric difference, assert **nothing left**, and resolve each entrant to a real
  `def`/`class` line read off the line. A class that *shrinks* because a review report was
  synced in is signal loss, not a repair.

### Implementation round, 2026-11-04 — what was measured and what it refutes

**The oracle.** `tests/helpers/page_ink.py` gains `FrameCentre` and
`frame_centre_of(page, drawing)`, **beside** `drawing_of` and replacing nothing: by
`ast`, the three top-level names are ADDED and **no existing definition or constant of
that file changed at all** (compared against `HEAD:tests/helpers/page_ink.py`; the only
other edit is a `#` comment, invisible to the AST). Its imports are still
`dataclasses`, `numpy`, `PIL` — no stream reader, no new dependency.

**F-1 — the population re-derives as 5, and the one the card names is the wrong one.**
AC-3 says "1 in `tests/test_book_puzzle_frame.py` (`drawing.top`)". The assertion that
actually reddens is **`drawing.left`**, one line above it, in
`TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame::test_both_slots_sit_where_con_018s_millimetres_put_them`.
Both fail under the probe (left 2.5039 px, top 2.7323 px against the 1.5 px
`EDGE_TOLERANCE_PX`) and the left one fires first, so the cell's reported residual —
**2.504 px, the exact figure the card and the brief carry** — is the LEFT residual
attributed to the TOP field. Both are re-expressed; the figure reproduces to the digit.

**F-2 — the 2.71 px half-rule is refuted by the built oracle; the figure is 2.5 px.**
The brief derived 1.3 pt at 300 DPI = 5.4167 px and inferred a 2.71 px half-rule, labelled
inference. Measured: poppler inks that stroke as **six pixel lines**, exactly as Pillow
does, so the width read off the page is 6 and the ink-to-centre offset is **2.5 px**
(measured 2.5039 against the millimetre arithmetic — the residual the card records). The
inference was right that a hard-coded 3 would miss the cell; it was wrong about why, and
the implementation never holds a half-rule constant at all: it reports the run's own
centre. **CARD-344's `_EDGE_OVERHANG = 3` comment ("the heaviest rule is 6 px, so 3 px is
the overhang, exactly") is exact in neither medium as a half-rule** — it is the
ink-to-COORDINATE offset in vector (3.000 px, measured) and 0 px in raster.

**F-3 — `Drawing.framed` and three of the four `grid_*` fields are unsafe on a revealed
answer page, and only `columns`/`rows` are documented as such.** Measured over
`tests/property/test_book_pdf_geometry.py`'s own corpus: **94 of 136 answer pages** report
`framed=False`, with `columns`/`rows` of 2, on pages that carry a frame. The first build of
this oracle gated on `drawing.framed` and raised there; the shipped one reads only
`left`, `top` and `grid_bottom` — the set that module already declares safe on either page
kind — and derives the frame structurally instead. **This also contradicts that module's
own comment**, which says `.cell` is "safe on either kind" nine lines before saying `.cell`
is "unsafe on a revealed answer page". Not this card's to fix; recorded — and now
**carded as CARD-351**, which owns both halves (the 94/136 reporting defect and the
module's nine-line `.cell` self-contradiction). The merge gate also **removed this
paragraph from ADR-0042/R6**, where the round had written it: a defect in a decision
record reads as a decision while no card owes the fix, so R6 now cites CARD-351 by id in
one sentence and keeps only the two facts that are about the oracle (the six-line width /
2.5 px half rule, and the reader-set decision of F-6).

**F-4 — one of the card's 5 cells cannot be closed, with the measurement.** The two-up
site in `..._two_up_pages` is bound by **one** `HALF_PIXEL_MM` — half a device pixel —
and that is below the quantisation of any reading of a binary ink mask. The frame rule
inks six lines, so its centre is a half-integer whose side is the rasteriser's (Pillow inks
`c-2..c+3`, poppler `c-3..c+2`). Over that corpus's 7 two-up pages:

| medium | ink | centre |
|---|---|---|
| raster | 0.54x | **1.54x** |
| vector | **5.46x** | 0.46x |

Neither reading is green in both media, and CARD-330's measured 1 px cross-medium floor is
above this bound either way. It is left on the ink (which keeps the tree as it stands
green) and **declared**, with those figures, in
`PLACED_EDGE_ON_THE_INK_BY_DECLARATION`. The remedy is the site's own multiple — 1 -> 2
admits both readings, at 0.77x and 0.23x — and that is **CARD-330's to move, not this
card's** (G-1). So the card's 5 closes as **4 + 1 declared finding**, and the vector
residual 5.46x is the card's own fourth figure, reproduced.

**F-5 — AC-4's corrected multiset reproduces exactly.** Re-derived with `ast`:
**8** constant-multiple sites, multiset **`{2: x2, 3: x4, 4: x2}`**, plus the definition
and one bare read, and **no `1 x` multiple anywhere**; `grep -c EDGE_TOLERANCE` in that
file is **0**. Pinned by `test_no_bound_was_widened`.

**F-6 — the frozen-registry hazard this card's own notes predicted does not apply as
stated.** `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium._stream_readers()`
derives over `_READER_OWNERS`, which is `tests/helpers/pdf_vector.py` and
`tests/helpers/pdf_pages.py` — **`page_ink.py` is not an owner**, so a new public reader
there joins neither the derived set nor `_MEDIUM_BLIND_READERS`, and the completeness cell
cannot see it. **Decision (item 3): the new reader stays outside that set**, because it
reaches no engine and reads a bitmap it was handed. What holds it to that is
`TestEdgeOffset_ThePixelOraclesStillReadPixels`, measured: plant (c1) imports `pdf_vector`
into `page_ink.py` and reds that class while leaving the placed-edge pin green, and plant
(c2) crosses inside a pinned site and reds the pin while leaving the oracle class green.
The two guards divide the work rather than overlap, and neither covers the other's half.

**F-7 — two re-expressed sites clear their bound with under 1% of margin.** Worst case over
136 cases of `..._MirroredMarginsCentreDrawingForEveryParity_pdf_pages`: the 2x left site
reads **1.992x** in vector and 1.983x in raster, and the 4x centring site **3.984x** and
3.965x. That is arithmetic, not luck — the centre carries half a pixel and the millimetre
figure rounds by up to half a pixel, so the worst case is the bound exactly — and it is
recorded here because a corpus change tips it. Stated rather than widened (G-1).
For contrast, what the **ink** reads on the same corpus: **6.992x** and 7.333x on the two
single-edge sites and **13.984x** on the spare site, all three RED in vector — the margin
is 0.4 %, and the alternative was 3.5x the bound. (Re-derived at the merge gate, both
media, 136 cases: reproduces to the digit.)

> **[Corrected at the merge gate, 2026-11-04 — this was prose where the card's own
> convention is a declaration.]** F-7 as written above was an argument in a card's notes.
> This card's convention for a residue it cannot improve is the one it built for F-4: a
> **measured, asserted declaration in the tree**, so that a corpus change, a poppler
> version or one differently-landing trim reds against an explanation instead of against
> nothing. The two sites and their figures, with the derivation that makes 2x and 4x the
> *exact* worst case (the centre carries +-0.5 px and the rounded millimetre coordinate a
> further +-0.5 px; one device pixel is 2 x `HALF_PIXEL_MM`, and the spare-margin site
> differences two such edges), are now written into
> `PLACED_EDGE_ON_THE_INK_BY_DECLARATION`'s own docstring in
> `tests/test_book_puzzle_frame.py` — deliberately **not** as mapping keys, since that
> mapping is held to sites still on the ink and these two are closed and green. **No bound
> moved** (G-1); widening would have broken it, which is the point the declaration records.

**F-8 — closing a placed-edge assert UNMASKS the next red, and two of them are a
page-SIZE family nobody has carded.** The card's "4 reds, one per node id, at
2.07x/2.36x/3.40x/5.46x" are *first-failure* attributions: a test aborts at its first
failing case, so closing that assert runs the loop further. Measured, per node id, under
the five-kind probe after the re-expression:

| node id of `tests/property/test_book_pdf_geometry.py` | now reds at | what it is |
|---|---|---|
| `..._DrawingFitsUsableAreaUnderStandardCell_pdf_pages` | `assert abs(page.size[1] - trim_height_px) <= 0.5`, measured **1.110 px** | a page-SIZE claim: poppler rasterises a 282.1 mm trim to **3333** px where 11.811 px/mm says 3331.890 |
| `..._PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` | **killed by the hang guard** — see F-9 | not an assertion at all |
| `..._MirroredMarginsCentreDrawingForEveryParity_pdf_pages` | `assert len({page.size for page in pages}) == 1`, measured **2** | the same family: one book's pages come back at two sizes, because the vector ones are poppler's raster and the rest are not |
| `..._PortraitWithFixedTopEdgeForEveryExtent_two_up_pages` | the **declared** `1 x HALF_PIXEL_MM` site, 25.7387 mm against 25.97 | F-4, exactly 5.46x, the card's own fourth figure |

So **every placed-edge assertion of both modules now passes under the probe except the one
declared site**, and the node ids that still red do so on three other mechanisms:
CARD-342's stroke weights (3 cells in `tests/test_book_puzzle_frame.py`), this page-size
family (**2 cells — unowned when this was written, and now CARD-350's**: it carries the
1.110 px over-rasterisation of a 282.1 mm trim and the two-sizes-in-one-book cell), and the
declared half pixel. `tests/test_book_puzzle_frame.py` under the probe moves **4 failed /
96 passed -> 3 failed / 110 passed, 0 skipped**.

**F-9 — one node id cannot be evidenced by a pytest run under the probe at all, and that
is true on `HEAD` too.** `..._PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` builds two
books of 126 puzzles; under the probe every interior page is rasterised by poppler, and
the corpus costs **124.9 s measured with no frame-centre reading in it at all** (120.5 s of
that inside `_interior`), against this project's **120 s per-test hang guard**. The test is
killed before it can report. On `HEAD` it "completes" in 76.7 s only because it aborts at
its own first failure. This card's reading adds **1.7 s to 124.9 s (1.4 %)**: 126.6 s with,
124.9 s without, same corpus, same medium. So the placed-edge evidence for that node id is
the direct measurement over its whole 252-page corpus — worst centre residual **0.0928 mm
in vector and 0.0770 mm in raster against a 0.1270 mm bound, with zero refusals, including
all 15 overflowing pages** — and the node id's own green is owed to whoever makes the
conversion affordable, not to this card.

**F-10 — AC-3's derivation has a blind spot, named rather than papered over.** The
population is keyed on each module's *own declared bound*, which is the shape
`TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium` uses over `EDGE_TOLERANCE_MM`.
It therefore does **not** see a placed-edge site bound by a literal — and one exists:
`assert drawing.left >= usable_left - 1`, which reds under the probe at `drawing.left` 133
against a usable edge of 135.827 (the mitred corner, 2.83 px outside the box) the moment
the site below it is closed. It is re-expressed (boundary 135.5, inside). Widening the
derivation to *every* resolved ink-extent read was tried and measured: **26 sites**, almost
all of them array indices (`dark[frame.top, layout.grid_left : ...]`) and ink-to-ink corner
readings, so a wider filter needs a classifier for those shapes before it can be a
partition rather than a blanket exemption. Not widened here; recorded — and now
**CARD-352's**, which the review cut after measuring that the blind spot is **three**
literal-bound sites rather than the one named above, and which also owns the second half
of the same defect: the classifier's `no_extent` fall-through, where ADR-0039/R2 wants a
failure rather than a silent class. **The gate did not build either** — both are a
derivation change to the partition this card's AC-3 is written against, and reopening it
at the gate would be a second implementation round under no review.

**One thing nothing in this card asserts, and it is carded rather than claimed closed.**
`frame_centre_of` reduces a bitmap to a mask and reaches no engine — F-6's decision rests
on that — but the only guard holding it there is
`TestEdgeOffset_ThePixelOraclesStillReadPixels`, i.e. **one of the two guards that hold
the old oracle**: the placed-edge pin's reader set derives over `pdf_vector.py` and
`pdf_pages.py` only, so it structurally cannot see `page_ink.py`. Plant (c1) measures that
the one guard fires; nothing measures the other half. That is **CARD-353**.

### The plant table (AC-5) — six plants, all with a measured unplanted baseline

Every plant: `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` swept at both ends, planted **by
text** with the occurrence count asserted to be exactly 1, restored from **captured
content**, SHA-256 taken before the plant and after the restore, `0 skipped` asserted, and
an **unplanted baseline run over the same node ids in the same medium** — because under the
probe some cells are already red for reasons that are not this card's, and a control is
green relative to that baseline. Harness: `scratchpad/card336/plants.py`.

| key | file | mutates | new reds | control green in the same run | skipped | sha256 before == after |
|---|---|---|---|---|---|---|
| **(a)** | `page_ink.py` | the boundary reading returns the ink extent again | `TestFrameCentre_TheReadingIsABoundaryInBothMedia::test_each_mediums_reading_is_the_boundary_the_layout_states`, `::test_the_two_media_read_the_same_page_as_the_same_boundary`, `TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame::test_both_slots_sit_where_con_018s_millimetres_put_them` | `TestFrameCentre_EveryPlacedEdgeSiteIsClassified`, `TestEdgeOffset_ThePixelOraclesStillReadPixels` | 0 | `d5573c01…48ab7a` both |
| **(b1)** | `page_ink.py` | the rule's extent taken as a CONSTANT six lines anchored on the drawing's ink edge | the AC-1 class's coordinate cell, its cross-medium cell **and** its refusal cell | same two | 0 | `d5573c01…48ab7a` both |
| **(b2)** | `page_ink.py` | the ink-to-centre offset taken as the **raster** medium's constant (+0.5 px) | the AC-1 coordinate cell and the cross-medium cell | same two | 0 | `d5573c01…48ab7a` both |
| **(c1)** | `page_ink.py` | the boundary oracle reaches the content-stream reader | `TestEdgeOffset_ThePixelOraclesStillReadPixels::test_neither_oracle_imports_the_content_stream_reader` | `TestFrameCentre_EveryPlacedEdgeSiteIsClassified`, and the placed-edge **pin stays green** | 0 | `d5573c01…48ab7a` both |
| **(c2)** | **`tests/test_book_pdf.py`** (outside `Touches`) | a PINNED placed-edge site reaches a stream reader without saying so | `TestEdgeOffset_EveryPlacedEdgeExpectationNamesItsMedium::test_no_site_reads_a_content_stream` **and** `::test_no_site_reaches_a_stream_reader_through_a_helper_either` | `TestEdgeOffset_ThePixelOraclesStillReadPixels` | 0 | `84a5e85f…8d6cd6` both — the byte-identity proof AC-5 asks for |
| **(d)** | `page_ink.py` | correct in ONE medium only: the top side reports its rule's first inked line | the AC-1 coordinate cell (vector arm) | same two | 0 | `d5573c01…48ab7a` both |

**What (b1) and (b2) together settle, and it corrects the card.** AC-5 (b) predicts "the
vector arm must red while the raster arm stays green". Which arm reds depends on **where**
the constant is anchored, and the card could not know that without the oracle: anchored on
the drawing's ink edge (b1) the raster arm reds and the vector arm is correct; anchored on
the raster medium's own +0.5 px offset (b2) the vector arm reds and the raster arm is
correct. Both were planted rather than one, so the claim as stated — *correct in both
media* — has a control that can fail in either direction (ADR-0039/R1).

**Why (c1) and (c2) are both here.** They catch different crossings and neither covers the
other's: a crossing hidden **inside** `page_ink.py` is invisible to the placed-edge pin,
whose reachability walk runs over `tests/test_book_pdf.py`'s own functions and whose reader
set derives over `pdf_vector.py` and `pdf_pages.py` only, and is caught by
`TestEdgeOffset_ThePixelOraclesStillReadPixels`; a crossing written **in a pinned site** is
caught by the pin and leaves the oracle class green. Measured both ways.
