# CARD-337: The twelve modules CARD-329's triage left owed — the seam for nine, and a stated disposition for the four mechanisms that are not a seam

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2d
**Complexity:** moderate
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** split from CARD-322 at the decompose station, 2026-10-31, on the owner's re-cut instruction. This is the list CARD-322's scope-gap section said "does not exist yet" and CARD-329's AC-6 round produced: the nine modules its triage reports as needing their own edit, plus the residue of the five it edited but could not repair. CARD-329's own words: *"Within this card's seven `Touches` paths that is unreachable, and the measurement says where the rest lives."*
**Split from:** CARD-322
**Idea:** —
**Wave:** —
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** CARD-329, CARD-336
**Touches:** tests/test_book_pdf_band.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_ink_mode.py, tests/property/test_book_export_interior.py, tests/test_book_export_interior_cover.py, tests/test_book_proof_pages.py, tests/test_book_solved_answer_key.py, tests/test_book_divider_pages_option.py, tests/property/test_book_pairing.py, tests/test_book_arrange_page_breaks.py, tests/test_book_pdf_levels.py, tests/test_book_pdf_two_up.py, tests/test_book_interior_type_floor.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What this card is handed, measured, and re-derived at the decompose station

**The whole 20-module census was re-run on `b26bdd62`** under CARD-329's own probe
(`scratchpad/card329/measure_probe.py` + `probe_puzzle_operators.py`) and reproduces that
card's figures to the digit: **17 of 20 red, 151 failed+error, 1224 passed, 1 skipped** —
the one skip attributed by `-rs` to `tests/test_book_pdf_memory.py:1297`'s
`setrlimit(RLIMIT_AS)` platform gate, not to either database gate. **So the 151 is
honest** and so is its five-bucket decomposition (66 + 2 + 38 + 29 + 16).

**This card owns 68 of the 151, plus 3 the census never looked at.**

### The nine routed modules — one seam each, 66 reds

CARD-329 standardised the shape across five modules and named these nine as needing the
identical one-line edit (`interior_images` at the module's one page-source function),
explicitly outside its own `Touches`:

| module | reds | population |
|---|---|---|
| `tests/test_book_pdf_band.py` | 23 (13 failed + 10 error) | A |
| `tests/test_book_pdf_memory.py` | 23 (10 failed + 13 error) | A |
| `tests/test_book_pdf_ink_mode.py` | 10 | A |
| `tests/property/test_book_export_interior.py` | 2 | A |
| `tests/test_book_export_interior_cover.py` | 2 | A |
| `tests/test_book_proof_pages.py` | 1 | A |
| `tests/test_book_solved_answer_key.py` | 1 | A |
| `tests/test_book_divider_pages_option.py` | 3 | B |
| `tests/property/test_book_pairing.py` | 1 | B |
| **total** | **66** | |

### The residue of the five CARD-329 edited — 16 reds, four of which are this card's

CARD-329's AC-6 disposition table: `test_book_cell_size.py` **REPAIRED** (20 → 0), and
four **"EDITED, NOT REPAIRED"** at 4 each. Of those four, **two are CARD-336's** (the
frame-centre oracle: `property/test_book_pdf_geometry.py` and
`tests/test_book_puzzle_frame.py`) and **two are this card's**:

* **`tests/test_book_pdf_levels.py`, 4** — "the four survivors compare a page
  byte-for-byte with `expected_puzzle_page`, a **raster** page the module composes by
  hand. Cross-medium byte identity cannot hold; the expectation needs composing in the
  page's own medium, which re-opens what its independent form is." **That is a second
  mechanism, not a seam**, and it is the one with a design question in it: the
  hand-composed expectation is a deliberate independent second implementation
  (CLAUDE.md's standing preference), so re-composing it in the vector medium must keep it
  independent of the writer under test. A re-composition that calls the production writer
  has deleted the cross-check rather than moved it.
* **`tests/test_book_pdf_two_up.py`, 4** — "two survivors are the same byte-identity
  family as above; two are pixel-row claims about the upper slot's top edge." The
  byte-identity pair is the mechanism above; the two pixel-row claims read through
  CARD-336's oracle, which is why this card **depends on** CARD-336 rather than racing it.

### The fifth bucket's segmentation half — 1 red, and it is not an edge question

`tests/test_book_arrange_page_breaks.py:753` fails `ValueError: too many values to unpack
(expected 1, got 2)` on `(alone,) = drawings_of(printed[pages[3] - 1])` — **`drawings_of`
finds two connected ink regions on a converted page where one is expected.** That is a
**third mechanism**: the oracle's region segmentation, not where an edge sits. Reading the
boundary does not touch it, so CARD-336 does not close it.

**CARD-329's F-004 routed this red (and `test_book_guide_page.py`'s) to "CARD-312's
per-site disposition and CARD-322's frame-centre oracle". The CARD-312 half is wrong and
the correction is this card's existence.** Read at the decompose station, CARD-312 is a
**static guard over `tests/**`** that *classifies* the 321 pixel-reading sites and
partitions the independent pixel oracles as **exempt** (its own item 2 and G-2), and it
states that it "can land before any page converts". A site it classes exempt is a site it
does not repair. So CARD-312 could never have closed either red. The guide-page red goes
to CARD-336 by its arithmetic; this one lands here.

### The 22nd module — 3 reds the census never looked at

**`tests/test_book_interior_type_floor.py` is in neither population A nor population B,
and is red at 3 under CARD-329's own probe.** Measured here, 2026-10-31:

```
3 failed, 48 passed      (PageKind.PUZZLE lifted)
```

The three, with their causes read off a `--tb=line` run:

* `TestInteriorType_EveryFaceHoldsTheFloor::test_the_recording_covers_every_kind_of_interior_lettering[book1]`
  — the recorded set of lettering kinds is no longer a superset of the claim;
* `TestInteriorType_TheStreamArmIsReached::test_lifting_a_declaration_makes_the_stream_arm_read_that_page`;
* `TestInteriorType_TheStreamArmIsReached::test_the_refused_kinds_are_derived_and_agree_with_the_spy`
  — `AssertionError: ['answer']`, a **derived** refused-kind set disagreeing with the spy.

**This is CON-020's type-floor arm** — CARD-299's medium-gated reading with CARD-314's
clue-digit mark — and it is in CARD-322's system contract. It reaches the hazard through
neither of CARD-329's two filters: it is not a reader of `pdf_pages` and it does not
obtain a page from `interior_pages`; it references the **medium decision itself**
(`_RASTER_DECLARATIONS`), which is a **third population** the census's filters cannot see.
Derived by `ast` at the decompose station, that population is **4 modules**
(`property/test_book_export_interior.py`, `test_book_difficulty_dots.py`,
`test_book_interior_type_floor.py`, `test_book_pdf.py`) of which **one** — this module —
is outside the 21-file census.

**So CARD-329's closing claim, "the arithmetic closes, so nothing is left for a reader to
discover", is true of the 20 modules it chose and not of the tree.** Raised as a finding
about that card's derivation, not absorbed: the defect is the filter, and the fix is this
card's population-C sweep.

## The probe this card needs, and the two traps in extending it

`scratchpad/card329/probe_puzzle_operators.py` lifts **`PageKind.PUZZLE` alone**, and its
docstring says lifting the other four kinds "would measure a REFUSAL, not a converted
page". **Measured 2026-10-31, that is no longer true and the extension is two lines:** the
refusal comes from `BookPDFGenerator.__init__` defaulting `pages` to
`NO_DOWNSTREAM_WRITERS`, so rebinding that module-level default to
`book_interior_vector.DOWNSTREAM_WRITERS` makes every `BookPDFGenerator(book)` an
assembled generator, and the tree then writes a real five-kind vector interior with
nothing refusing. `src/` is read, never edited — the mutation is to imported module
objects for one process.

**Trap 1 — a test that lifts a declaration itself collides with the probe.** Derived by
`ast`: **three** modules reference `_RASTER_DECLARATIONS` directly with **17**
`monkeypatch.delitem` sites, and only two (`tests/test_book_pdf.py:5670`, `:5794`,
CARD-329's own) pass `raising=False`. The rest raise
`KeyError: <PageKind.TITLE: 'title'>` at `_pytest/monkeypatch.py:302` once the probe has
removed the key — a red that is an **artefact of the instrument**. Measured on
`tests/property/test_book_export_interior.py` with the four non-puzzle kinds lifted:
**6 failed, 5 of them that KeyError and 1 genuine.** Two of the three colliding modules are
in this card's `Touches`. **Make the two distinguishable before counting anything**, and
state the mechanism you chose.

**Trap 2 — what the five-kind probe says about the scale, and what it does not.** Run over
the same 20 modules at the decompose station, the five-declaration probe puts population A
at **176** reds where the PUZZLE-only probe puts it at 102, while **population B is
unchanged module for module** (`pdf_geometry` 4→4, `cell_size` 0→0, `difficulty_dots`
29→29, `divider_pages_option` 3→3, `pdf_levels` 4→4). Part of the +74 is Trap 1's
artefact, and part is real: in the **six** population-A modules that contain no
`delitem` site at all, and where therefore no artefact can account for it, the four extra
kinds add **+61** measured reds —

| module | PUZZLE only | all five | delta |
|---|---|---|---|
| `tests/test_book_solved_answer_key.py` | 1 | **33** | +32 |
| `tests/test_book_export_interior_cover.py` | 2 | **15** | +13 |
| `tests/test_book_pdf_memory.py` | 23 | **29** | +6 |
| `tests/test_book_guide_page.py` | 1 | **5** | +4 |
| `tests/test_book_pdf_band.py` | 23 | **26** | +3 |
| `tests/test_book_interior_face.py` | **0 (green)** | **2** | +2 |
| `tests/test_book_arrange_page_breaks.py` | 1 | **2** | +1 |

**`tests/test_book_interior_face.py` is one of the three modules CARD-329 reports as fully
green under the probe, and it is red at 2 under the real end state.** That is the clearest
statement available of what the PUZZLE-only probe cannot see, and it is why this card
verifies under the five-kind probe and not CARD-329's.

## What to implement

1. **The seam, for the nine.** The same shape CARD-329 landed in five modules:
   `interior_images` at the module's own page-source function. **Nine, derived per module
   rather than applied by rote** — CARD-329's own finding is that the seam was *necessary
   in all five and sufficient in one*, so a module that is still red after it is the
   normal case, not a surprise.
2. **The byte-identity family, for `test_book_pdf_levels.py` and
   `test_book_pdf_two_up.py`.** Compose the expectation in the page's own medium, and
   **keep it an independent second implementation**: the point of `expected_puzzle_page`
   is that it is not the writer under test. State what the independent vector form is and
   why it is still independent.
3. **The segmentation question, for `test_book_arrange_page_breaks.py`.** Derive **why**
   a converted page reads as two connected regions where the raster page reads as one,
   and dispose of it per ADR-0042/R6 — re-expressed against the content stream, or
   re-expressed as an ink claim that is medium-durable, or retired with a named survivor.
   **Do not loosen the unpacking to accept any count**: a claim that accepts 1 or 2
   drawings has stopped being the claim.
4. **Population C's sweep, and `test_book_interior_type_floor.py`'s three.** Derive the
   modules that reach the hazard through the **medium decision** rather than through a
   reader or a page source — CARD-329's two filters are blind to them — and repair the
   one outside its census. Per ADR-0039/R2 a module the walk cannot classify is a
   **FAILURE**.
5. **Verify under the five-kind probe, not CARD-329's.** See the two traps above.
   Record the red count **before changing anything**; that number is this card's floor
   and its absence is what made CARD-329's AC-4 vacuous as first written.

## Acceptance criteria

- **AC-1** (the nine are repaired, with a disposition each): *Given* a run under the
  five-declaration probe, *then* each of the nine routed modules passes, and the card
  states **per module** which of three dispositions it took and why — the seam sufficed,
  the module needed more, or a claim was retired with a named survivor. **A module left
  green only because the probe does not reach it is not repaired, and saying so is the
  AC.** (test: the nine modules by node id, under the probe, with `-o addopts=''`)
- **AC-2** (the four non-seam mechanisms each have a stated disposition): *Given* the
  branch, *then* `test_book_pdf_levels.py`'s and `test_book_pdf_two_up.py`'s
  byte-identity survivors, `test_book_arrange_page_breaks.py`'s segmentation red and
  `test_book_interior_type_floor.py`'s three each carry a disposition naming the
  mechanism, not a repair naming the symptom. **The byte-identity half additionally
  states how its expectation stays independent of the writer under test.**
- **AC-3** (the populations are derived and total, including the one the census missed):
  *Given* `tests/**`, *then* populations A, B and **C** (the medium-decision references)
  are derived by `ast` with their filters stated in one sentence each, nothing is
  unclassified (ADR-0039/R2), and **every module of the union is green under the
  five-kind probe except the ones another card owns by name** — `tests/test_book_pdf.py`
  (CARD-322's registry assertions and CARD-336's placed-edge family),
  `tests/property/test_book_pdf_geometry.py` and `tests/test_book_puzzle_frame.py`
  (CARD-336), `tests/test_book_difficulty_dots.py` (CARD-322's arm re-point),
  `tests/test_book_guide_page.py` (CARD-336). Each exclusion is **named with its owner**,
  not left as a residue.
- **AC-4** (the measurement is the instrument's, and the instrument is controlled):
  *Given* the five-kind probe, *then* the round records the red count before and after,
  **every skip attributed by name from `-rfs` as ONE flag** (two database gates coexist
  here and `-rf -rs` as two flags silences the first), and the probe's own
  `monkeypatch.delitem` collision is separated from genuine reds with the separation
  shown. A figure read off the brief rather than off a run is the defect this board has
  hit five times.
- **AC-5** (the change can fail): **one plant per repaired module**, each re-breaking that
  module's own repair, each killed, each with its matched control measured green **in the
  same run** and `0 skipped` asserted. **A repair with no plant is a claim, not a fix.**
  Where a module holds no green node to be a matched control, declare the survivor and
  say why — CARD-329's MUT-11 is the precedent, not an excuse. (evidence: the plant table
  in `## Worktree notes`)

## Engineering constraints

- **EC(ADR-0039/R2):** the three populations' union is a **partition** of the modules that
  read or decide an interior page's medium — derived, with nothing unclassified, and a
  module the walk cannot classify fails.
- **EC(ADR-0042/R6):** every repaired reading is asserted against the medium its page was
  written in, as a **runtime** property of the reading and not a static fact about the
  module — the shape CARD-299 landed and CARD-329 reused.

## Guardrails

- **G-1: convert no page and flip no rule.** `_RASTER_DECLARATIONS` is untouched, no
  `src/` file changes, and ADR-0042/R1's `check:` stays a lens. CARD-322 owns both.
- **G-2: do not touch `tests/helpers/page_ink.py`, `tests/helpers/two_up_ink.py` or
  `tests/helpers/round_ink.py`.** The independent pixel oracles are CARD-330's and
  CARD-331's subjects, and the boundary reading is **CARD-336's** — this card *consumes*
  it. Folding a reader and an oracle together destroys the cross-check CLAUDE.md requires.
- **G-3: do not touch `tests/test_book_pdf.py`.** Its 38 reds are 6 registry assertions
  (CARD-322's, moving with the registry and its comment), 30 placed-edge (CARD-336's) and
  2 of CARD-329's own — **none of them is a seam**. And the house-style seam is exactly
  what CARD-329's F-001 measured as able to silently retire CARD-330's pin over 30 of
  those 38; that walk is now closed (`_closed_sites()`, a fixed point at 4 rounds, with a
  class-qualified exemption register matched on the whole key), but the right move here is
  still not to add the seam to a file whose reds belong to two other cards.
- **G-4: do not touch `tests/test_book_difficulty_dots.py`** — CARD-331's design, and its
  29 reds under the probe are CARD-322's arm re-point. **G-3 of CARD-322 excludes it for
  the same reason.**
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included (gate:
  node-id set difference by `ast` over the thirteen `Touches` paths — **not**
  `--collect-only`, which prints no node ids under this project's `addopts = "-q"`).
- **G-6: do not lower a corpus minimum** and regenerate nothing under `tests/fixtures/**`.
  **No baseline moves in this card** — the 19 live book baselines are CARD-322's and
  re-recording them twice is what G-6 exists to stop.
- **G-7: do not widen a tolerance to close a red.** `EDGE_TOLERANCE_MM` is CARD-330's and
  stays `0.1`; `EDGE_TOLERANCE_EXEMPTIONS` stays empty. Widening would close most of this
  card's residue and is exactly what CARD-330 was cut to prevent.
- **G-8: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`), and **commit no
  measurement dump**: the validator's check-ref search is a text search over tracked files
  excluding only `meta/architecture` and `*.md`, so a census pasted into a tracked `.txt`
  *revives* dead refs — the hazard carded as **CARD-335**. CARD-329's
  `ref_pollution_check.py` is the instrument and the convention: instruments are `.py`,
  numbers live in the card.
- **G-9: do not connect to the production database.** The live panel runs on
  `nonogram_poc`; `conftest.py` refuses by URL text, before connecting, any database not
  ending in `_test`.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's medium-gated reading; **CARD-312 flips the rule, not this card**)
- ADR-0042/R2 — a raster page is declared with a reason (check: `test_every_raster_page_is_declared_with_its_reason`)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-5's plants)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-3)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: AC-4's skip attribution)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte
- CON-020 — the 10 pt interior type floor, clue digits exempt **by their mark** — the rule `test_book_interior_type_floor.py`'s three reds are about (check: CARD-299's re-expressed test with CARD-314's mark)
- INV-013 — the interior holds no cover page; parity counts from interior page 1
- EC-019 — every page of the book's PDF is the trim; the claim that loses its `.size` when a page becomes a content stream

## Architecture context

- **FR:** FR-030, FR-032, FR-040, FR-043
- **ADR:** ADR-0042/R2, R6, ADR-0039/R1-R2, ADR-0038/R8
- **Components:** none in `src/` — thirteen test modules
- **Trace:** not updated by this card.

## Worktree notes

- **[Why this is its own card — the re-cut's reasoning, 2026-10-31]** CARD-322's
  scope-gap section asked **that** card to choose a per-module disposition for eleven
  modules, and then recorded honestly that the list "does not exist yet". CARD-329's AC-6
  round produced it. This card is that list plus the three mechanisms CARD-329 could not
  reach inside its own `Touches` plus the module its filters could not see. It is cut out
  of the conversion because its judgement — *"every module that reads or decides an
  interior page's medium is green under a five-kind probe, or is named with its owner"* —
  is complete with no page converted, which is the property that made CARD-312 and
  CARD-329 closable and whose absence made CARD-309 unclosable at 189 failures + 75 errors.
- **[The estimate, and the calibration behind it]** 2d. CARD-329 did **five** seam edits,
  a shared helper, 24 plants and a probe harness at **2d estimated / 4.1h actual**. This
  card does **nine** seams plus four non-seam mechanisms plus a population sweep, with
  the probe harness already designed (two lines past CARD-329's) and the seam shape
  already proven. The nine seams are the cheap two-thirds; the four mechanisms are the
  expensive third, and the byte-identity one carries a design question
  (*what is the independent vector form of a hand-composed page?*) that could alone run a
  day. 2d is the honest ceiling.
- **[UNMEASURED PREMISE, stated as unmeasured]** *That the nine routed modules' 66 reds
  are all closed by the seam.* It is CARD-329's **inference**, recorded as "Each needs the
  same one-line seam edit", and that card's own measurement contradicts the strong form of
  it: the seam was *necessary in all five and sufficient in one*. **What would measure it:**
  apply the seam to the three biggest (`pdf_band` 23, `pdf_memory` 23, `pdf_ink_mode` 10)
  first and report before/after per module before touching the other six. If the ratio
  resembles CARD-329's (80 → 16), this card's residue is ~13 reds and they are the finding.
- **[UNMEASURED PREMISE, stated as unmeasured]** *That the four extra kinds add no new
  mechanism to the nine, only more cells of the same ones.* The five-kind census measures
  the **counts** (+61 in the six uncontaminated population-A modules) and not the
  **causes**, and the one cause sampled at the decompose station is new: with the four
  non-puzzle kinds lifted, `property/test_book_export_interior.py:546` reds with *"interior
  page 2 is written as operators but no vector guide writer is reachable from
  BookPDFGenerator, so this reading has nothing to compare the shipped page against — the
  card that converts the guide page (CARD-309) owes the expected side here"*. That is an
  **expected-side gap**, not a reader seam, and its message names a stale card. **What
  would measure it:** run the five-kind probe over the nine with `--tb=line` and classify
  the reds by message before estimating the repair. If the expected-side family is large,
  it is a fourth mechanism and a finding about this card's own scope.
- **[The `solved_answer_key` figure is the one to watch]** 1 red under PUZZLE-only, **33**
  under all five, and no `delitem` site in the module — so the jump is real and it is the
  ANSWER page's. That module also holds CARD-297's `_DECLARED_CLIP_DIVERGENCE` at
  `tests/test_book_solved_answer_key.py:3783`, which is **CARD-322's** item (AC-5 there).
  **This card and CARD-322 both edit this file**, which is the one conflict edge between
  them and the reason CARD-322 depends on this card rather than running beside it.
- **[Expect the merge gate to find a frozen registry]** Thirteen modules change node ids.
  Derive which censuses your diff touches — `trace.yml` refs, the browser-family register,
  `ADDED_SINCE_BEFORE`-style snapshots — and run them before the gate does;
  `review.test_scope: impact` is structurally unable to see a cross-card census, and two
  cards in one hour on 2026-10-30 went red at the gate on exactly that.
- **[Do not paste the number a frozen baseline prints when it reds.]** Re-derive the
  symmetric difference, assert **nothing left**, and resolve each entrant to a real
  `def`/`class` line read off the line.
- **[Environment traps, all of which fail silently]** Worktrees share the main venv, so
  always `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest`.
  `-rfs` as ONE flag. `addopts = "-q"` stacks to `-qq` and prints no count line; pass
  `-o addopts=''` and locate counts by pattern. `-k` selecting nothing exits 0, and a
  nodeless pytest call collects the whole suite. `python_classes` is matched as a prefix,
  not a glob. A stripped `PATH` makes platform-gated tests skip, which reads as success —
  inherit the environment and assert the skip count. Poppler is at
  `/opt/homebrew/bin/pdftoppm`.
