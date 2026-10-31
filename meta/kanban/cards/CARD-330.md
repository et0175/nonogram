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
  spanning trims and page counts, *then* for every edge of every case the card
  records **specified / raster / vector** in millimetres, with the specified value
  derived from the page spec rather than read from either renderer, and a minimum
  case count asserted inside the test. (test:
  `TestEdgeOffset_TheThreeNumbersAreDerivedPerEdge`)
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

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream, with the independent oracles exempt by name (check: CARD-299's; this card disposes of two of those oracles)
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

- **[The reframing is the card's main contribution, and it was the orchestrator's,
  not the implementation round's.]** CARD-309's round delivered the measurement
  (963/1849 vs 965/1851) and called it a convention question. At the decompose
  station the arithmetic was re-derived — 2 px at 300 dpi is 0.1693 mm, and 300 dpi
  is the interior's own render DPI — which makes the gap exactly one rounding step
  and the two values **not two opinions but a quantisation of one**. Re-derive both
  the measurement and the arithmetic before building on either.
- **[Why P1 when nothing is broken]** It blocks CARD-322, which blocks the whole
  vector interior phase from reaching a reader, and it is the one of CARD-309's four
  causes that no existing card owned. The other three are CARD-329, CARD-331 and a
  re-derivation CARD-309 already did.
