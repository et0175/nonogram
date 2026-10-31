# CARD-322: The last five interior kinds become operators, and ADR-0042/R1 flips with the final conversion

<!-- TITLE CORRECTED 2026-10-31 at the re-cut: "four" -> "five". Measured, every
     one of the FIVE temporary `_RASTER_DECLARATIONS` entries -- TITLE, GUIDE,
     TOC, ANSWER **and PUZZLE** -- carries `expires_with=("CARD-299", "CARD-322")`,
     and CARD-299 is done. CARD-309 did NOT convert the puzzle page; its own
     registry comment says so in as many words ("**CARD-309 built the assembly
     point and did NOT convert a kind.**"). This card's AC-1 already said five;
     its title, its "Why this card exists" section and item 1 said four. See the
     re-cut section below. -->

**Status:** ready
**Priority:** P1 <!-- RAISED P2 -> P1 2026-10-31 at the re-cut: this card is the terminal node of the ADR-0042 interior phase and SEVEN ready cards wait on it (CARD-207, CARD-209, CARD-229, CARD-230, CARD-232, CARD-233, CARD-288), with CARD-273 behind them. Its two new prerequisites are P1 for the same reason. -->
**Category:** enabler
**Estimate:** 2d <!-- RE-CUT 2026-10-31 from 1d. The 1d was priced against "five page kinds plus one test module"; the measured residue is 225 reds under a probe of this card's own end state. Two mechanisms were split out (CARD-336, CARD-337) and what is left here is still not 1d: five conversions, 19 live baselines, R1's flip, CARD-331's arm re-point with its set DERIVED, CARD-297's clip divergence, CARD-306's F-307 rename and the owner render. See the re-cut section. -->
**Complexity:** architectural <!-- RAISED from `standard` at the re-cut: this is the first and only flip of ADR-0042/R1, it is the first production call site of CARD-309's assembly point, it spans src/ + tests/ + fixtures/ + meta/architecture, and its `expires_with` interaction with a live board guard makes the landing order itself load-bearing. -->
<!-- NOTE: `moderate` (CARD-329/CARD-331's value) is not in the skill's enum; `architectural` is the honest one here and resolves the implementation agent to the quality profile. -->

**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** split from CARD-309 on owner decision, 2026-10-30. CARD-309 was estimated 1d and held an assembly point that does not exist, five kind conversions, 21 baselines, R1's flip, CARD-297's clip divergence and a reader population of 12+8 modules. The split follows the card's own item 1 — *"one kind at a time, each removal complete… what makes this card incremental rather than all-or-nothing"*.
**Split from:** CARD-309
**Idea:** —
**Wave:** —
**Created wave:** 68
**Deferred waves:** 0
**Depends on:** CARD-309, CARD-329, CARD-330, CARD-331, CARD-336, CARD-337 <!-- WIDENED 2026-10-30 at CARD-309's re-cut, from `CARD-309` alone. CARD-309 implemented this card's conversion to measure it and reverted it: 189 failures + 75 errors across 22 modules, four causes. Three of them are now cards and every one of them is a PREREQUISITE, not a sibling -- CARD-329 (the one-image reader), CARD-330 (the 0.169 mm the media disagree by, which changes the VALUE of every placed-edge expectation), CARD-331 (the difficulty-dot instrument, which on a vector page measures a page the product no longer draws and does so SILENTLY). Converting before CARD-330 decides its question means re-deriving every edge expectation twice. WIDENED AGAIN 2026-10-31 at this card's own re-cut by CARD-336 (the frame-centre oracle) and CARD-337 (the twelve modules CARD-329's triage left owed, plus the one its filters could not see) -- both split OUT of this card, both land before any page converts, and both share a file with this one, so they are serialized ahead of it rather than run beside it. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_puzzle_vector.py, tests/test_book_pdf.py, tests/test_book_difficulty_dots.py, tests/test_book_solved_answer_key.py, tests/test_book_puzzle_page_vector.py, tests/fixtures/book_baseline_*.json, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md <!-- CORRECTED 2026-10-31 at the re-cut. REMOVED `book_guide_vector.py`, `book_toc_vector.py`, `book_answer_vector.py`: measured, the walk ALREADY reaches all four downstream writers through CARD-309's `InteriorPageWriters` (`book_pdf_generator.py:7885/7934/8031/8051`) and the title page through its own `vector_title_page` (`:5266`, gated at `:7863`), so no writer module is edited -- the src/ change is the five registry entries. ADDED the four files the re-cut's own items need: `book_puzzle_vector.py:43` (the F-307 docstring consumer), `test_book_difficulty_dots.py` (CARD-331's arm re-point), `test_book_solved_answer_key.py:3783` (CARD-297's clip divergence) and `test_book_puzzle_page_vector.py:1950` (the F-307 rename itself). -->
<!-- CONFLICT EDGES, measured at the re-cut: this card INTERSECTS CARD-336 on `tests/test_book_pdf.py` and CARD-337 on `tests/test_book_solved_answer_key.py`, which is why both are `Depends on` rather than same-wave siblings. It intersects CARD-316's live worktree NOWHERE. -->
<!-- `expires_with` NEEDS NO EDIT AT THIS SPLIT, and that is deliberate: all five temporary entries name ("CARD-299", "CARD-322") and this card still removes all five, so `test_no_declaration_outlives_the_cards_that_remove_it` -- which reds when EVERY card an entry names has reached a terminal status while the entry remains -- stays green through CARD-336's and CARD-337's merges. Splitting the CONVERSION by kind instead would have forced a per-kind `expires_with` re-point in `src/` and a second re-recording of the 19 live baselines; see the re-cut section for why that was rejected. -->
<!-- `tests/fixtures/book_baseline_*.json` is 23 FILES but 19 LIVE BASELINES: 21 `.json` of which `card128` and `card145` carry `superseded_by`, plus 2 `.jpg` (`card200_guide_page1/2`). The 5 `tests/fixtures/proof_baseline_*.json` are ALL LIVE and ADR-0042/R1 names the proof sheet as an export path it governs -- item 5 must decide them explicitly rather than inherit "21". -->
<!-- All four original dependencies are `done` (CARD-309, CARD-329 `9db10da6`, CARD-330, CARD-331), verified against the card files at the re-cut; the two new ones are `ready` and themselves unblocked. -->

**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## [RE-CUT 2026-10-31] — read this first; four of the claims below it are superseded

**Re-cut at the decompose station on the owner's instruction, after CARD-329 landed
(`9db10da6`).** This card was `ready` at **1d**, priced against "five page kinds plus one
test module". Three orchestrator corrections had since been written onto its body and its
last dependency had landed with a measured residue. The re-cut's measurements, all taken
on `b26bdd62` and all re-derived rather than carried:

### 1. This card converts FIVE kinds, not four

Every one of the five temporary `_RASTER_DECLARATIONS` entries — `TITLE`, `GUIDE`, `TOC`,
`ANSWER` **and `PUZZLE`** — carries `expires_with=("CARD-299", "CARD-322")`, and CARD-299
is `done`. **CARD-309 did not convert the puzzle page**, and its own registry comment says
so: *"**CARD-309 built the assembly point and did NOT convert a kind.** Its AC-1 asked for
`PageKind.PUZZLE`'s entry to go; the card measured why it cannot go yet and re-pointed all
five entries at CARD-322 instead."* CARD-288's body already reads it correctly (*"After
CARD-322 converts title, guide, TOC, answer **and puzzle**"*) and so does this card's own
AC-1 (*"no page of any of the **five** converted kinds"*). What was wrong was the title,
the "Why this card exists" paragraph below and item 1. **Corrected in the title; the
paragraph below is left standing with this pointer, per this card's convention of carrying
its corrections inline so the record shows what was claimed when.**

### 2. The src/ change is the five registry entries, and nothing else

Measured by reading the walk: `book_pdf_generator.py` already reaches **all four**
downstream writers through CARD-309's `InteriorPageWriters` (`:7885`, `:7934`, `:8031`,
`:8051`) and composes the title page itself through `vector_title_page` (`:5266`), gated at
`:7863` by `page_medium(PageKind.TITLE) is PageMedium.VECTOR`. **So no vector writer module
is edited and the production conversion is the deletion of five dict entries.** `Touches`
is corrected accordingly. *Everything expensive about this card is on the other side of
that deletion*, which is the fact the 1d estimate was missing.

### 3. The residue is 225 reds, not 151 — and the 151 is nonetheless honest

The brief this re-cut was given carried **151** in five buckets. **Re-derived here, that
figure is exactly right for the instrument that produced it:** CARD-329's probe
(`scratchpad/card329/measure_probe.py` + `probe_puzzle_operators.py`) over its 20 modules
reproduces **17 of 20 red, 151 failed+error, 1224 passed, 1 skipped**, every per-module
number matching, and `66 + 2 + 38 + 29 + 16 = 151` closes. The one skip is attributed by
`-rs` to `tests/test_book_pdf_memory.py:1297`'s `setrlimit(RLIMIT_AS)` platform gate —
neither database gate fired.

**But that probe lifts `PageKind.PUZZLE` ALONE**, and its own docstring says lifting the
other four "would measure a REFUSAL, not a converted page … that is a different
experiment". **Measured at the re-cut, that is no longer true and the extension is two
lines:** the refusal comes from `BookPDFGenerator.__init__` defaulting `pages` to
`NO_DOWNSTREAM_WRITERS`, so rebinding that module-level default to
`book_interior_vector.DOWNSTREAM_WRITERS` makes every `BookPDFGenerator(book)` in the test
tree an assembled generator. With all five declarations lifted the tree writes a real
vector interior and nothing refuses. Over the identical 20 modules:

| | PUZZLE only | all five |
|---|---|---|
| modules red | 17 / 20 | **18 / 20** |
| failed+error | 151 | **225** |
| passed | 1224 | **1150** |
| skipped | 1 | 1 |

**Population B is unchanged module for module** (`pdf_geometry` 4→4, `cell_size` 0→0,
`difficulty_dots` 29→29, `divider_pages_option` 3→3, `pdf_levels` 4→4, `pdf_two_up` 4→4,
`puzzle_frame` 4→4, `pairing` 1→1): the whole **+74** is in population A, which is where
the guide, TOC, answer and title pages are read.

**How much of the +74 is the instrument and how much is the conversion, bounded rather
than guessed.** Derived by `ast`, **three** modules reference `_RASTER_DECLARATIONS`
directly with **17** `monkeypatch.delitem` sites, and only two
(`tests/test_book_pdf.py:5670`, `:5794`, CARD-329's own) pass `raising=False`; the rest
raise `KeyError: <PageKind.TITLE: 'title'>` at `_pytest/monkeypatch.py:302` once the probe
has removed the key, which presents as a red and is the instrument's artefact. Only two of
those three modules are in the census, and they account for **+13** of the +74
(`property/test_book_export_interior.py` 2→7, `test_book_pdf.py` 38→46). In the **six**
population-A modules with no `delitem` site at all — where no artefact can account for
anything — the four extra kinds add **+61 measured reds**:

| module | PUZZLE only | all five | delta |
|---|---|---|---|
| `tests/test_book_solved_answer_key.py` | 1 | **33** | +32 |
| `tests/test_book_export_interior_cover.py` | 2 | **15** | +13 |
| `tests/test_book_pdf_memory.py` | 23 | **29** | +6 |
| `tests/test_book_guide_page.py` | 1 | **5** | +4 |
| `tests/test_book_pdf_band.py` | 23 | **26** | +3 |
| `tests/test_book_interior_face.py` | **0 — green** | **2** | +2 |
| `tests/test_book_arrange_page_breaks.py` | 1 | **2** | +1 |

**`tests/test_book_interior_face.py` is one of the three modules CARD-329 reports as fully
green under the probe, and it is red at 2 under this card's actual end state.** That single
row is the clearest available statement of what the PUZZLE-only probe cannot see.

### 4. A 22nd module, in neither population, red at 3 under CARD-329's own probe

**`tests/test_book_interior_type_floor.py`** — CON-020's type-floor arm, which is in this
card's own system contract — is red at **3** (`3 failed, 48 passed`) under the PUZZLE-only
probe and appears in **neither** of CARD-329's populations. It reaches the hazard through
the **medium decision itself** (`_RASTER_DECLARATIONS`), which is a third population both
of that card's filters are blind to. Derived by `ast`, that population is 4 modules and
this is the one outside the 21-file census. **So CARD-329's closing claim — "the
arithmetic closes, so nothing is left for a reader to discover" — is true of the 20
modules it chose and not of the tree.** Raised as a finding about that card's derivation,
and owned by **CARD-337**. The honest residue under the PUZZLE-only probe is **154**, and
under this card's end state **228** (225 + 3), of which at most 13 can be instrument
artefact.

### 5. What was split out, and why those seams

Two mechanisms left this card, each because its judgement is complete **with no page
converted** — the property that made CARD-312 and CARD-329 closable and whose absence made
CARD-309 unclosable at 189 failures + 75 errors:

* **CARD-336 — the frame-centre oracle.** 39 placed-edge reds across four modules
  (`test_book_pdf.py` 30 of its 38, `property/test_book_pdf_geometry.py` 4,
  `test_book_puzzle_frame.py` 4, `test_book_guide_page.py` 1), one mechanism:
  `page_ink.Drawing`'s fields are ink extents and the cells compare them against
  coordinates. ADR-0042/R6's comment assigns this oracle to **this card** by name;
  **CARD-336 owns the amendment that re-points that sentence.** 2d.
* **CARD-337 — the twelve modules CARD-329's triage left owed, plus the 22nd.** The nine
  routed modules' 66 seam reds, the byte-identity family in `test_book_pdf_levels.py` and
  `test_book_pdf_two_up.py`, `test_book_arrange_page_breaks.py`'s region-segmentation red,
  and `test_book_interior_type_floor.py`'s three. 2d.

**What was deliberately NOT split: the conversion itself, by kind.** Converting PUZZLE in
one card and the other four in another is tempting — it is `_RASTER_DECLARATIONS`' own
seam, it is CARD-309's stated principle, and the PUZZLE residue is the fully-measured
half. It was rejected on two measurements. (a) **The baselines would be re-recorded
twice.** There are 19 **live** book baselines (21 `.json` less `card128` and `card145`,
which carry `superseded_by`) plus 2 `.jpg` and 5 live proof baselines; every one is a
snapshot of a whole interior, so both conversions move all of them, and CARD-222's own
dependency note states the rule — *"racing it would make two cards re-record the same
fixtures"*. (b) **`expires_with` would need a per-kind re-point in `src/`.**
`test_no_declaration_outlives_the_cards_that_remove_it` reds when **every** card an entry
names has reached a terminal status while the entry remains; with all five naming
`("CARD-299", "CARD-322")` and this card removing all five, no `expires_with` edit is
needed at this split at all, and the guard stays green through CARD-336's and CARD-337's
merges. Splitting by kind would have put a `src/` registry edit on the critical path of a
board guard, for no measurement gained.

### 6. The three corrections this card was never estimated for, each resolved

* **RE-POINT, DO NOT RETIRE** — confirmed against the code, not the prose. The raster arm's
  own `remedy` string reads *"RE-POINT this arm at a page kind `_RASTER_DECLARATIONS` still
  declares raster — the cover and the divider … and move the 27 cells of this module that
  read the interior as bitmaps with it. Retiring the arm is NOT one of the options while
  `PageMedium` keeps `RASTER`"*, and a sibling cell asserts that exact sentence is present
  *"because CARD-322 reads that string as its work order"*. **And the derive-the-set
  obligation is real and measured:** `RASTER_ARM_FUNCTIONS` at
  `tests/test_book_difficulty_dots.py:6996` is a hand-written 5-tuple, and its only guard
  asserts `set(_raster_arm_sources()) == set(RASTER_ARM_FUNCTIONS)` — i.e. that every
  **listed** name has a source. It cannot catch a name that should be listed. **Adding your
  new function to the list is the defect repeating.** See item 2 of *What to implement*.
* **The eleven-module scope gap** — delivered by CARD-329's AC-6 and **removed from this
  card**, into CARD-337. Do not redo it and do not re-derive it.
* **The closure trap resolves to the FIRST branch: CARD-329 landed it, so this card
  inherits it.** Verified on `main`: `tests/test_book_pdf.py` holds `_closed_sites()`
  (`:5034`), which follows every name a site mentions into that callable's body to a
  **fixed point** — measured at **4** rounds, 121 reachable names — and the exemption
  register `_BOUND_ONLY_SITES` (`:5113`) is now matched on the **class-qualified** key with
  a cell (`test_the_exemption_lookup_does_not_strip_the_class`) that reds if a consulting
  cell degrades back to `_bare`. **The card's old conditional is discharged**; the next
  reader is not left holding it. Note that it changes nothing about this card's own work,
  because **none of `test_book_pdf.py`'s 38 reds is a seam**: 6 are registry assertions
  (this card's), 30 are placed-edge (CARD-336's) and 2 are CARD-329's own new raster-only
  cells. This card adds no `interior_images` seam anywhere.

### 7. Premises stated as UNMEASURED, with what would measure each

* *That the residue this card still faces after CARD-336 and CARD-337 land is small.*
  **Unmeasured, and unmeasurable today** — it is an inference about a tree that does not
  exist until those two cards merge, which is this card family's signature failure mode.
  **What would measure it:** re-run the five-kind probe over the 20 modules plus
  `test_book_interior_type_floor.py` on the merged tree, before converting anything, and
  record the count. That is this round's first job, and the number is this card's floor.
* *That the +61 measured in the six uncontaminated modules is more cells of the mechanisms
  already named rather than new mechanisms.* **Unmeasured — the census measures counts, not
  causes.** The one cause sampled at the re-cut was new:
  `property/test_book_export_interior.py:546` reds with *"interior page 2 is written as
  operators but no vector guide writer is reachable from `BookPDFGenerator`, so this
  reading has nothing to compare the shipped page against — the card that converts the
  guide page (CARD-309) owes the expected side here"* — an **expected-side gap**, not a
  reader seam, whose message additionally names a stale card. **What would measure it:**
  classify the five-kind reds by message with `--tb=line` before pricing any repair.
* *That the 5 live `proof_baseline_*.json` move with this conversion.* **Unmeasured.**
  ADR-0042/R1 governs the proof sheet by name (*"on any export path — the interior PDF, the
  proof sheet, or any future one"*) and `tests/test_book_proof_pages.py` is red at 1 under
  both probes, which is consistent with either answer. **What would measure it:** read a
  proof baseline back on a converted tree and report the diff. Item 5 must state the
  answer; **inheriting "21" is not an answer**.

## Why this card exists

<!-- SUPERSEDED 2026-10-31 by the re-cut above, item 1: CARD-309 did NOT convert the
     puzzle page, and this card converts FIVE kinds. Left standing rather than
     rewritten so the record shows what was claimed when. -->

**CARD-309 builds the assembly point and converts the puzzle page.** This card converts the four that
remain — **TITLE, GUIDE, TOC and ANSWER** — removes their declarations, and **flips ADR-0042/R1 with
the last one**.

It is the repetition half by design, and it is genuinely cheaper **only if CARD-309's assembly point
is real**. `book_guide_vector`, `book_toc_vector` and `book_answer_vector` all import
`book_pdf_generator` at module level, so none can be called from its page walk without a cycle;
CARD-309 owns that problem. **If you arrive and the assembly point turns out to be a workaround
rather than a design, raise it rather than building a second one.**

## The declarations will name this card, and a live guard enforces it

`tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it` **reds the day a card
named in `expires_with` is marked done while its declaration remains.** CARD-309 re-points TITLE,
GUIDE, TOC and ANSWER from `CARD-309` to **`CARD-322`** precisely so that guard stays honest across
the split.

**So this card cannot be marked done until all four entries are gone.** Verify on arrival that the
re-pointing actually happened — if CARD-309 shipped without it, that is a **finding about CARD-309**,
raised, not absorbed.

## [Added 2026-10-30 at CARD-309's re-cut] This card now closes the phase, and the conversion has been measured once already

**CARD-309 implemented this card's conversion, measured it, and reverted it.** That
measurement is this card's most valuable inheritance and must be re-derived, not
trusted: the conversion reds **189 failures + 75 errors across 22 test modules**,
with **four** causes of which only one is a PDF reader.

Three are now prerequisites (`Depends on` widened accordingly):

- **CARD-329** — `tests/helpers/pdf_pages.py`'s one-image reader raises
  `KeyError: b'XObject'` on an operators page. The small, genuine reader conversion.
- **CARD-330** — the raster and vector media place the same grid **0.169 mm** apart
  (**2 px at the interior's own 300 dpi** — one rounding step) against
  `EDGE_TOLERANCE_MM = 0.1`. **Every placed-edge expectation in the tree changes
  value with the medium**, so converting before that question is answered means
  deriving every edge expectation twice and probably loosening a bound by accident.
- **CARD-331** — the difficulty-dot accounting instrument monkeypatches the *raster*
  drawing site, so on a vector page it measures a page the product no longer draws —
  and a monkeypatch on an uncalled function **passes silently** rather than erroring.

The fourth cause (frozen AST censuses in `tests/test_book_export_interior_cover.py`)
CARD-309 re-derived on its own branch.

**What this card inherits ready-made:** the assembly point,
`src/nonogram/admin/book_interior_vector.py` — downstream of all five writers, the
direction a **parameter** (`InteriorPageWriters`) rather than a registry or a lazy
import, with **no cycle anywhere** in the `book_*` graph (verified by an independent
`ast` walk at the decompose station) and `tests/test_cli.py`'s structural guard
passing **unmodified**. Copy that convention; do not re-litigate it.

**What this card alone owns:** the four remaining conversions, the **21 baselines**,
CARD-297's declared clip divergence, and **ADR-0042/R1's flip — with the last
conversion, not before.** CARD-298, CARD-299 and CARD-309 each refused that flip on
their own initiative and each was right.

**And this card is what finally gives the phase a reader.** CARD-309 ships the
assembly point with **zero production call sites**, which is verbatim the condition
it was cut to end. The conversion is the call site. Until this card lands, nothing in
`src/` turns an interior page into operators.

## [Added 2026-10-30 at CARD-309's review] This card owes CARD-306's F-307 rename, and until now nothing said so

CARD-309's review cycle 1 raised this as its **F-002**, and it was a real routing
hole rather than a disagreement: CARD-309's record claims it hands the rename to
this card *"with a guardrail that permits it"*, and measured, **this card had
zero mentions of F-307 or the class name**, while its G-5 carried the same
unqualified prohibition CARD-309 had just declined under. So the rename was
owed by a card that did not know it, behind a guardrail that forbade it.

**CARD-309 was right to decline.** G-5 is task-level authoritative and is
weakened only at the decompose station. What failed was the routing, and it is
fixed in two places: G-5 above now carries the one named exception, and this
section records why the debt exists.

**The debt itself:** `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`
says the vector puzzle page draws **no** sheet furniture. CARD-306 then gave it
folio, frame rules, a grid-size label and a QR block — so the name is now the
opposite of the truth while the assertions underneath are correct. A test whose
name contradicts its body is this board's most-cited defect family, and it is
sitting in the file this card has to edit anyway.

## [Owner steer 2026-10-30] This card is the destination

*"Let's aim at switching on vector for the interior (not dividers) — don't spend much
time on fixing-updating raster."*

So this card is the one the phase is aimed at, and the steer changes what it inherits
rather than what it does. **CARD-330 will pin the raster placed-edge expectations as
legacy instead of re-tuning them**, so this card's conversion is what *retires* them —
expect to delete raster expectations here, not satisfy them. Same for **CARD-331**'s
raster arm of the difficulty-dot accounting: its lifetime ends with this card.

<!-- ORCHESTRATOR CORRECTION 2026-10-31, measured during CARD-331's review cycle 1
     (F-005) and verified here. THE SENTENCE ABOVE IS HALF FALSE, AND THIS CARD'S
     OWN NEXT PARAGRAPH REFUTES IT: "Dividers stay raster, unchanged."

     CARD-331's accounting now carries one arm per PageMedium, and PageMedium keeps
     RASTER for the cover and the divider. The arm is enumerated on the MEDIUM, not
     on the puzzle page, so the medium survives this conversion and the arm must
     survive with it. Deleting the arm REDS CARD-331's arm-per-medium cell
     (tests/test_book_difficulty_dots.py, the TheVectorArmReadsTheStream /
     AnArmWhoseMechanismIsDeadFails classes).

     THE INSTRUCTION THIS CARD INHERITS, stated once: RE-POINT, DO NOT RETIRE.
     Keep the raster arm; change its kind from PageKind.PUZZLE to a kind
     `_RASTER_DECLARATIONS` still declares raster, and move with it the 27 cells of
     that module which read the interior as bitmaps.

     AND ONE OBLIGATION, routed here by CARD-331's cycle 3 (its N-1) because that
     card cannot edit this one's body: WHEN YOU RE-POINT THE ARM, DERIVE
     `RASTER_ARM_FUNCTIONS`' COMPLETENESS RATHER THAN EXTENDING THE LIST. The guard
     over that set checks that every listed name has a source; it CANNOT catch a name
     that should be listed. That is the exact hole a cycle-1 mutant survived in before
     CARD-331's F-004 extended the list -- which closed the instance and not the
     mechanism. This card is the imminent exposure, being the next card to touch that
     arm, and the hazard cannot bite before one does. Deriving the set is the fix;
     adding your new function to the list is the defect repeating.

     Expect ONE deliberate red on arrival, by design, not by drift:
     `test_each_arms_mechanism_is_still_exercised[raster]` is built to fail the day
     this card converts the puzzle page, and its message is a work order naming the
     arm, its mechanism and the remedy. Satisfy it by re-pointing. DO NOT WIDEN IT.

     CARD-331's F-005 also fixed its own remedy string, which had offered
     "retire this arm" -- an option its own guard forbids -- so the work order you
     will read is now the corrected one. This card owes the repair of the sentence
     above; it is left in place rather than rewritten so the record shows what was
     claimed when. -->

**Dividers stay raster**, unchanged: ADR-0042/R2 makes the divider an exception by
scheduling rather than technique, and CARD-231 redesigns that page to be *born* vector.
So "switch the interior to vector" means the four remaining kinds **and not the
divider**, which is exactly the scope this card already carries — and R1's flip is
still only legal once the five temporary entries are gone, which ADR-0042's own Rules
comment states.


## [Scope gap] — eleven test modules break this way; this card declares one

**Measured 2026-10-31 by the orchestrator**, read-only census over `tests/**/*.py`:
the modules that **both** read ink with a raster reader (`drawing_of`, `drawings_of`,
`ink_regions`, `page_ink`, `two_up_ink`) **and** obtain pages from `interior_pages`
or `interior(`. Those two together are the failure: `interior_pages` returns
`List[Union[Image.Image, ContentStream]]`, so converting a kind hands a content
stream to a pixel reader, and CARD-331 measured the result —
`'ContentStream' object has no attribute 'convert'`. A page's `.size` is gone the
same way, which is how EC-019's every-page-is-the-trim claims fail.

| module | raster readers | page sources | owned? |
|---|---|---|---|
| `tests/test_book_pdf.py` | 72 | 5 | **declared by this card** |
| `tests/test_book_puzzle_frame.py` | 37 | 2 | — |
| `tests/test_book_proof_pages.py` | 21 | 1 | — |
| `tests/test_book_pdf_two_up.py` | 20 | 1 | — |
| `tests/test_book_cell_size.py` | 18 | 1 | — |
| `tests/property/test_book_pdf_geometry.py` | 12 | 4 | CARD-288, **premise dissolved, now gated** |
| `tests/test_book_pdf_band.py` | 11 | 2 | — |
| `tests/test_book_difficulty_dots.py` | 10 | 2 | CARD-331, **deliberately** |
| `tests/test_book_pdf_memory.py` | 7 | 6 | — |
| `tests/test_book_divider_pages_option.py` | 6 | 2 | — |
| `tests/property/test_book_pairing.py` | 5 | 1 | — |

**1 of 11 declared — but "the other ten are unowned" is WRONG, and the correction
changes what this card has to do.** Re-measured 2026-10-31, same session, by `ast`
over the import graph rather than by the declaration list:

- **4 of the 11 are CARD-329's population A** — they import `tests/helpers/pdf_pages.py`,
  so **CARD-329's medium-aware reader fix reaches them at the helper**, not here:
  `test_book_pdf.py`, `test_book_proof_pages.py`, `test_book_pdf_band.py`,
  `test_book_pdf_memory.py`.
- **7 are CARD-329's population B** — they never import the reader and reach the same
  hazard through `interior_pages` / `interior` with their own pixel readers. **CARD-329's
  item 3 owns their TRIAGE**, explicitly: *"Classify population B per module, don't
  convert it wholesale … derive whether this card's change is enough or whether it needs
  its own edit, and say which per module. A module that needs more is a finding about
  scope, to be raised."*

**MEMBERSHIP CORRECTED AGAIN 2026-10-31, by CARD-329's review cycle 1 — this is the
third correction to this section and the figures below are the measured ones.** The
orchestrator's census agreed with CARD-329 on the *count* and was wrong on the *set*:

- **`tests/helpers/page_ink.py` is NOT in population B.** It never *obtains* a page; it
  is *handed* one (`drawing_of(page: Image.Image)`), and a grep for `interior_pages` /
  `.interior` over it returns **nothing**. Under AC-3's own filter — obtains a page **and**
  uses it as an image — it cannot be in B. It is in B's **indirect half, as a consumer**,
  which is precisely what puts `property/test_book_pairing.py` in. Same for `round_ink.py`.
- **And the orchestrator's own list of seven was wrong in a second place**: it carried
  `test_book_arrange_page_breaks.py` and **dropped `test_book_pdf_ink_mode.py`**, which is
  red at 10 and does belong. **CARD-329's list of seven is the correct one.**

**THE VERIFIED RESIDUE THIS CARD INHERITS** — every one re-measured still red under
CARD-329's probe *after* that card's round, so these are not stale:

| module | reds | population |
|---|---|---|
| `tests/test_book_pdf_band.py` | 23 | A |
| `tests/test_book_pdf_memory.py` | 23 | A |
| `tests/test_book_pdf_ink_mode.py` | 10 | A |
| `property/test_book_export_interior.py` | 2 | A |
| `tests/test_book_export_interior_cover.py` | 2 | A |
| `tests/test_book_proof_pages.py` | 1 | A |
| `tests/test_book_solved_answer_key.py` | 1 | A |
| `tests/test_book_divider_pages_option.py` | 3 | B |
| `property/test_book_pairing.py` | 1 | B |
| **`tests/test_book_arrange_page_breaks.py`** | **1** | A — **lands in no bucket** |
| **`tests/test_book_guide_page.py`** | **1** | A — **lands in no bucket** |

**The last two are CARD-329's F-004 and they are the ones to read twice.** They are not
`ContentStream`-attribute reds, not the seven seam edits, not G-3's exclusion and not
"by design": `arrange_page_breaks` fails `ValueError: too many values to unpack` on a
`two_up_ink` reading finding two drawings where one is expected, and `guide_page` fails a
geometric assertion (`2.944881889763778 <= 2`). Both are pixel-oracle readings of a
converted page — **CARD-312's family, not this card's seam** — so they need a disposition
of their own rather than the one-line edit the other nine take.

<!-- CORRECTED 2026-10-31 at the re-cut: "CARD-312's family" is WRONG, and the two
     reds are not even one family. Read at the decompose station, CARD-312 is a
     STATIC GUARD over tests/** that CLASSIFIES the 321 pixel-reading sites and
     partitions the independent pixel oracles as EXEMPT (its item 2, its G-2), and
     it states that it "can land before any page converts". A site it classes
     exempt is a site it does not repair, so CARD-312 could never have closed
     either red. Routed at the re-cut, measured:
       * `test_book_guide_page.py`'s 1 -> CARD-336. Its site differences
         `drawing.left` -- the mitre-affected edge, 3 px / 0.254 mm by CARD-330's
         reading -- against `page.width` and compares to a 2 px bound, failing at
         2.944881889763778 px; residual and mitre agree to within a pixel. (Stated
         as a reading of the arithmetic, not a measurement: see CARD-336's
         unmeasured-premise note.)
       * `test_book_arrange_page_breaks.py`'s 1 -> CARD-337. `:753` is
         `(alone,) = drawings_of(page)` and `drawings_of` finds TWO connected ink
         regions where one is expected. That is the oracle's REGION SEGMENTATION,
         not where an edge sits, so reading the boundary does not touch it. -->

**And a trap this card must not walk into, measured by CARD-329's review:** the
placed-edge pin's site walk collects names **from the body of the `EDGE_TOLERANCE_MM`-
bearing function only** and does not close over the call graph. A plant of the *same*
medium crossing at a module's own page-source helper **survives with the fix in place**.
That is exactly the one-line seam shape CARD-329 standardised across five modules and
exactly where this card would put it — so **applying the house style to
`tests/test_book_pdf.py` would silently retire CARD-330's pin over 30 of the 38 reds the
pin protects.** CARD-329's fix round owns closing the walk; if it lands before this card,
inherit it. If it does not, this card must not add that seam to `test_book_pdf.py`
without closing the walk first.

<!-- CONDITIONAL DISCHARGED 2026-10-31 at the re-cut -- IT RESOLVES TO THE FIRST
     BRANCH. Verified on `main` at `b26bdd62`: `tests/test_book_pdf.py` holds
     `_closed_sites()` (:5034), following every name a site mentions into that
     callable's body to a FIXED POINT (measured at 4 rounds, 121 reachable names),
     and `_BOUND_ONLY_SITES` (:5113) is matched on the CLASS-QUALIFIED key with
     `test_the_exemption_lookup_does_not_strip_the_class` reddening if a consulting
     cell degrades back to `_bare`. CARD-329's F-001 and F-008. So the walk is
     closed and this card inherits it; the next reader is NOT left holding the
     conditional.

     And it changes nothing about this card's work, because NONE of
     `test_book_pdf.py`'s 38 reds is a seam: 6 are registry assertions (this
     card's), 30 are the placed-edge family (CARD-336's) and 2 are CARD-329's own
     new raster-only cells. THIS CARD ADDS NO `interior_images` SEAM ANYWHERE --
     the nine modules that need one are CARD-337's. -->

**So the per-module disposition this section originally asked THIS card to choose is
CARD-329's output, not this card's job.** Do not redo it. **Run CARD-329 first and
consume its per-module classification**; what remains for this card is the modules
CARD-329's triage reports as needing their own edit. That list does not exist yet,
which is the honest state — the repairs are unowned *until CARD-329 reports*, which is
a different thing from unowned.

<!-- RESOLVED 2026-10-31 at the re-cut. CARD-329 reported (its AC-6 table and its
     scope finding), the list EXISTS, and it is no longer this card's: it went to
     **CARD-337** entire -- the nine routed modules' 66 seam reds, the byte-identity
     family in `test_book_pdf_levels.py`/`test_book_pdf_two_up.py`,
     `test_book_arrange_page_breaks.py`'s segmentation red, and the 22nd module
     `tests/test_book_interior_type_floor.py` that CARD-329's two filters could not
     see (red at 3 under its own probe, in NEITHER population). The placed-edge
     mechanism went to **CARD-336**. What is left here is the conversion and the
     things that move WITH the registry: see `## What to implement`. -->


The original claim in this section ("eight have no card at all") was the orchestrator's,
made from CARD-322's declaration list without reading CARD-329's scope. It is retracted
here rather than deleted, because this card's estimate was being re-priced against it.

This is the subset of CARD-309's measured **189 failures + 75 errors across 22
modules** that fails specifically by handing a content stream to a pixel reader —
so the figure is not new, but its distribution across *cards* is.

**What this does to the estimate.** This card is 1d, budgeted as five page kinds plus
one test module. The measured consequence is eleven. **Price that before starting**,
and decide explicitly which of the three dispositions each undeclared module gets:
converted to a stream reader, retired with a named survivor, or pinned as legacy —
the choice CARD-330 already made for the placed-edge expectations it owns.

<!-- PRICED 2026-10-31 at the re-cut, which is what this paragraph asked for. The
     answer is **2d for this card, after splitting two mechanisms out at 2d each**:
     6d where the board had 1d. The measurement is in the re-cut section above --
     225 reds under this card's own five-kind end state against the 151 the
     PUZZLE-only probe reports, plus 3 in a module neither probe's census covers.
     The three dispositions this paragraph names were all taken, per module, by
     CARD-329's AC-6 and this re-cut's routing; nothing is left for this card to
     choose. -->


**Two of the eleven are already handled and are the pattern to copy, not re-derive:**

- **`test_book_difficulty_dots.py` (CARD-331)** does the right thing by design. Its
  `test_each_arms_mechanism_is_still_exercised[raster]` is **built to red the day this
  card converts the puzzle page**, and its message is a work order naming the arm, its
  mechanism and the remedy. **Expect that red; satisfy it by re-pointing. Do not widen
  it.** See the correction above: *re-point, do not retire.*
- **`test_book_pdf.py` (CARD-330)** pinned its placed-edge expectations to the raster
  medium rather than re-tuning them for both, precisely so this card's conversion is
  what retires them. Its `EDGE_TOLERANCE_MM` stays `0.1` behind a biconditional, and
  the figure that will red here is **3 px = 0.254 mm on `Drawing.left`/`top`** — a
  rasteriser mitring a stroked `re`'s corner — **not** the grid's own edges, which sit
  at 1 px = 0.0847 mm, inside the bound. **The repair is a centre-reading oracle, not a
  wider tolerance.**

## What to implement

<!-- REWRITTEN 2026-10-31 at the re-cut. Items 1-5 below replace the five this card
     carried; the two they shed (the reader population, which was item 4, and the
     per-module disposition) are CARD-336's and CARD-337's. Item 0 is new and is
     the thing whose absence made CARD-329's AC-4 vacuous. -->

0. **Measure first, before a line of the tree changes.** Stand up the five-declaration
   probe — CARD-329's `probe_puzzle_operators.py` plus the two lines that rebind
   `book_pdf_generator.NO_DOWNSTREAM_WRITERS` to `book_interior_vector.DOWNSTREAM_WRITERS`
   — run it over CARD-329's 20 modules **plus `tests/test_book_interior_type_floor.py`**,
   and record the red count on the merged tree. **That number is this card's floor**, and
   its absence is how an AC in this family passed review while being satisfiable by an
   empty diff. Separate the probe's own `monkeypatch.delitem` collision from genuine reds
   and show the separation; the re-cut bounded the artefact at ≤13 of 74 and did not
   eliminate it.
1. **One kind at a time, each removal complete — and there are FIVE.** For `TITLE`,
   `GUIDE`, `TOC`, `ANSWER` and `PUZZLE`: delete that kind's entry from
   `_RASTER_DECLARATIONS` and let `_write_pdf`'s representation refusal prove the removal —
   a kind whose declaration is gone but whose page is still a bitmap is **refused, not
   shipped**. **No vector writer module is edited**: the walk already reaches all four
   downstream writers through CARD-309's `InteriorPageWriters` and composes the title page
   through its own `vector_title_page`. Re-verify that on arrival; if a kind's page walk
   turns out not to reach its writer, that is a **finding about CARD-309**, raised, not
   absorbed.
2. **Re-point CARD-331's raster arm, and DERIVE `RASTER_ARM_FUNCTIONS` rather than
   extending it.** `test_each_arms_mechanism_is_still_exercised[raster]` is built to red
   the day this card converts the puzzle page, and its `remedy` string is the work order:
   re-point the arm at a kind `_RASTER_DECLARATIONS` still declares raster — the cover or
   the divider — and move the **27 cells** of that module which read the interior as
   bitmaps with it. **Retiring the arm is forbidden by its own sibling cell** and would red
   `test_there_is_one_arm_per_medium_the_product_can_write`, because the arms are
   enumerated on the **medium** and `PageMedium` keeps `RASTER`. **Do not widen the work
   order.** And `RASTER_ARM_FUNCTIONS` (`tests/test_book_difficulty_dots.py:6996`) is a
   hand-written 5-tuple whose only guard asserts that every **listed** name has a source:
   it cannot catch a name that *should* be listed, which is the hole a cycle-1 mutant
   survived in, and CARD-331's own fix closed the **instance** and not the **mechanism**
   (that card's N-1 routes the mechanism here, and names this card as the imminent
   exposure). **Derive the set from the arm's own reachable surface; adding your new
   function to the list is the defect repeating.** The derivation needs its own plant: a
   function added to the arm and *not* listed must red.
3. **Flip ADR-0042/R1 here, and only with the last kind.** Not before. A test asserting
   *"every page is the medium its kind declares"* **passes while R1 is violated**, as long
   as any interior kind is still a declared exception — which is why CARD-298 and CARD-299
   each refused this flip and were each right. ADR-0042's own Rules comment states the
   condition: *"Flip this check when the statement is true of a shipped interior, i.e. when
   the five temporary entries in `_RASTER_DECLARATIONS` are gone."* **Spell the ref as a
   BARE TEST NAME, not as a `file::name` node id** — measured twice in this very ADR (R2's
   and R5's comments), the validators' `split_check_ref` splits on commas only, so a node-id
   ref is handed to `git grep -lw` as one literal symbol and reports as a **DEAD check
   ref**: R2's note records the node-id spelling taking the tree from 107 to 108 warnings
   while the bare name left the warning set byte-identical. Diff the warning **sets** with
   `comm` in both directions, never the totals.
4. **Resolve CARD-297's `_DECLARED_CLIP_DIVERGENCE`** (`tests/test_book_solved_answer_key.py:3783`)
   when the answer page converts — delete it with the measurement that justifies it, or keep
   it with a new argument that names the converted page. **Silence is not an option.** The
   standing position, recorded on CARD-298 and CARD-299 and still unchallenged: once the
   answer page is vector there is **one** answer-page writer, and the book clips by
   `/Widths`, the measure the reader's own viewer uses — so the declaration becomes a
   statement about a page nobody prints. **Verify the argument against a converted page
   before acting on it; it has never been tested against one** — and note that this module
   goes from **1** red to **33** under the five-kind probe, so the answer page is where the
   conversion's weight actually lands.
5. **Rename `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`** — G-5's one
   named exception, granted at the decompose station. Its two consumers are
   `tests/test_book_puzzle_page_vector.py:1950` (the class) and
   `src/nonogram/admin/book_puzzle_vector.py:43` (a docstring naming it); both move in the
   same commit, and a renamed class is a node-id change, so any frozen snapshot naming it
   moves with it or the gate finds them.
6. **The baselines these kinds move, enumerated file by file**, with the count stated and
   the interior's size and generation time recorded at both ends. **The figure is 19 live
   book baselines, not 21**: `tests/fixtures/book_baseline_*.json` is 21 files of which
   `card128` and `card145` carry `superseded_by` and are historical records, plus 2 `.jpg`
   (`card200_guide_page1/2`). **And decide the 5 live `proof_baseline_*.json` explicitly**:
   ADR-0042/R1 governs the proof sheet by name (*"on any export path — the interior PDF,
   the proof sheet, or any future one"*), so inheriting the number "21" is not an answer.
7. **The owner render.** See AC-6; this is the render the owner has been waiting for since
   the phase opened, and the standing rule is that image-pipeline changes need a rendered
   eyeball and not just green tests.

## Acceptance criteria

- **AC-1** (R1 is true and checked): *Given* a written interior, *then* **no page of any of the five
  converted kinds** references an image XObject, `_RASTER_DECLARATIONS` holds **only the cover and
  (until CARD-231) the divider**, and **ADR-0042/R1's `check:` is a live node id naming the test that
  proves it.**
  <!-- "live node id" CORRECTED 2026-10-31 at the re-cut: a BARE TEST NAME, not a
       node id. R2's and R5's comments in this same ADR each measured the node-id
       spelling reporting as a DEAD check ref (107 -> 108 warnings) while the bare
       name left the warning set byte-identical; `split_check_ref` splits on commas
       only. The test the ref names already EXISTS and is green --
       `test_no_interior_page_carries_an_image_xobject` -- so what flips is the
       `check:` kind, not the test. Diff the warning SETS with `comm` in both
       directions, never the totals: main reads 0 errors / 88 warnings, re-derived
       at the re-cut with the validator of record. -->
  <!-- ALSO at the re-cut: AC-1 said FIVE all along and was right; the card's title,
       its "Why this card exists" paragraph and its item 1 said four. See re-cut
       item 1. The five are TITLE, GUIDE, TOC, ANSWER and PUZZLE. -->
  <!-- AND the landing-direction guard is part of this AC in practice:
       `test_no_declaration_outlives_the_cards_that_remove_it` reds when every card
       an entry names has reached a terminal status while the entry remains. All
       five entries name ("CARD-299", "CARD-322") and CARD-299 is done, so this card
       CANNOT be marked done until all five are gone -- verified at the re-cut by
       reading `_landing_findings`, which is the one implementation of that
       direction. -->
- **AC-1b** (CARD-331's arm is re-pointed and its set is DERIVED): *Given* the converted
  puzzle page, *then* `test_each_arms_mechanism_is_still_exercised[raster]` is green
  **because the arm was re-pointed at a kind that is still declared raster**, not because
  the cell was widened or the arm retired; the 27 cells that read the interior as bitmaps
  moved with it; and **`RASTER_ARM_FUNCTIONS` is derived from the arm's own reachable
  surface rather than listed**, with a plant that adds a function to the arm and omits it
  from the set reddening. **A listed set with one more entry is this AC failing, however
  green the suite is.** (test: `test_each_arms_mechanism_is_still_exercised` and
  `test_there_is_one_arm_per_medium_the_product_can_write`, both existing and unmodified,
  plus a new completeness cell this card writes — **review-lens on the round's evidence
  until that cell exists**, owned by this card.)
- **AC-2** (each removal is complete, proved by refusal): *Given* a kind whose declaration is removed,
  *then* a bitmap handed in for that kind is **refused by the writer**. **Two mutants per
  ADR-0039/R1**, one inside the region and one at the edge: **the last kind converted**, and **a kind
  converted while its declaration is left behind**.
- **AC-3** (the readers survive, both populations): *Given* the converted interior, *then* every test
  module that reads a book interior passes — **derived across both routes, not listed**, and a module
  needing a further edit is a **finding to raise, not absorb**.
  <!-- NARROWED 2026-10-31 at the re-cut. "Both routes" is now THREE populations and
       the first two are other cards' deliverables: A (the one-image reader, 12
       modules) and B\A (page source used as an image, 9) are CARD-329's derivation,
       repaired by CARD-337; the placed-edge mechanism inside them is CARD-336's.
       **Population C is the one this card must derive itself** -- the modules that
       reference the MEDIUM DECISION (`_RASTER_DECLARATIONS`, `page_medium`,
       `PageMedium`, `RasterDeclaration`, `InteriorPageWriters`,
       `NO_DOWNSTREAM_WRITERS`, `interior_generator`, `DOWNSTREAM_WRITERS`), because
       those are the modules the REGISTRY EDIT disturbs rather than the conversion.
       Derived by `ast` at the re-cut: **4 modules** --
       `property/test_book_export_interior.py`, `test_book_difficulty_dots.py`,
       `test_book_interior_type_floor.py`, `test_book_pdf.py`. Three are this card's
       or CARD-337's by name; re-derive the set rather than trusting this list, and a
       fifth member is the finding. Per ADR-0039/R2 a module the walk cannot classify
       is a FAILURE, not a silent pass. -->
- **AC-3b** (the whole tree is green, and the three modules another card owns are named
  rather than excused): *Given* the merged tree, *then* the full suite is green at the
  merge gate, with **every skip attributed by name from `-rfs` as ONE flag** — on current
  `main` that is **26** from the bare `DATABASE_URL` check at `tests/conftest.py:207` plus
  **1** from the `setrlimit(RLIMIT_AS)` platform gate at
  `tests/test_book_pdf_memory.py:1297`, and the per-worktree `*_test` resolution gate does
  **not** fire. **A figure recalled rather than read off `-rfs` is the defect**; two gates
  coexist here.
- **AC-4** (the baselines move once, enumerated): *Given* the branch, *then* the re-recorded baselines
  are listed file by file, the count is stated, and **CON-019's property test and the A4 golden are
  untouched and green**.
  <!-- FIGURE CORRECTED 2026-10-31 at the re-cut: **19 live book baselines**, not 21.
       `tests/fixtures/book_baseline_*.json` is 21 files, of which `card128` and
       `card145` carry `superseded_by` and are historical records that are not
       re-recorded; plus 2 `.jpg` (`card200_guide_page1/2`). The 5
       `proof_baseline_*.json` are ALL LIVE and ADR-0042/R1 names the proof sheet as
       an export path it governs, so AC-4 must state their disposition too --
       "21" was a FILE COUNT and reads as a baseline count. See item 6. -->
- **AC-4b** (the conversion's cost is recorded at both ends): *Given* the re-recorded
  baselines, *then* the interior's **byte size and generation time** are stated before and
  after, per the item-6 requirement, because the whole ADR-0042 phase was argued partly on
  file size (ADR-0042/R5's note: "~365 KB against a file that was 9 MB") and nobody has
  measured the converted interior's. **Not a gate, a record**: a regression here is a
  finding for the owner, not a reason to widen anything.
- **AC-5** (the clip divergence is resolved, not inherited): *Given* the converted answer page, *then*
  `_DECLARED_CLIP_DIVERGENCE` is either deleted with the measurement that justifies it, or kept with a
  new argument naming the converted page.
- **AC-6** (an owner render exists): *Given* the converted interior, *then* a rendered interior is
  produced under `~/Documents/nonogram-reviews/CARD-322/`. **Standing rule: image-pipeline changes
  need a rendered eyeball, not just green tests** — and after this card **every interior page but the
  divider is vector**, which is the render the owner has been waiting for since the phase opened.

## Engineering constraints

- **EC(ADR-0042/R1):** across a seeded corpus spanning page counts, trims and tier mixes, **no
  interior page of a converted kind carries an image XObject**, with a minimum case count asserted
  inside the test.
- **EC(ADR-0042/R2):** across the same corpus, the set of raster pages **equals** the set of declared
  raster pages — neither direction slack — and that set shrinks to **the cover plus the divider**.

## Guardrails

- **G-1: do not convert the cover.** Its declaration is permanent (`expires_with: ()`); a photograph
  is correctly raster.
- **G-2: do not convert the divider.** It is CARD-231's, by the owner's 2026-10-25 decision that the
  new design should be **born** vector rather than the old one converted.
- **G-3: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` or the A4
  golden.** Neither is a book interior. If either reds, that is a **finding to raise**, not a baseline
  to refresh.
- **G-4: do not lower a corpus minimum**, and regenerate nothing under `tests/fixtures/**` beyond the
  baselines item 5 enumerates. <!-- item 5 -> **item 6** after the re-cut's renumbering. -->
- **G-3b: do not widen a tolerance to close a red, anywhere.** `EDGE_TOLERANCE_MM` stays
  `0.1`, `EDGE_TOLERANCE_EXEMPTIONS` stays empty and asserted empty, and
  `property/test_book_pdf_geometry.py`'s four `HALF_PIXEL_MM` multiples stay 3/3/2/1.
  These are CARD-330's and CARD-336's, inherited closed. CARD-330 was cut to prevent
  exactly the widening that closes most of this family's residue at once.
- **G-3c: do not touch `tests/helpers/page_ink.py`, `tests/helpers/two_up_ink.py`,
  `tests/helpers/round_ink.py` or `tests/helpers/pdf_pages.py`.** The independent pixel
  oracles are CARD-330's and CARD-331's, the boundary reading is CARD-336's and the
  one-image reader is CARD-329's. **This card consumes all four and edits none** — folding
  a reader and an oracle together destroys the cross-check CLAUDE.md requires. If a
  conversion cannot be read without changing one of them, that is a **finding about the
  card that owns it**, raised.
- **G-3d: do not re-do CARD-336's or CARD-337's work, and do not force their residue
  green.** If either lands with a declared residue, inherit the declaration. A red those
  cards declared and this card silently repairs is scope growth the SCOPE GATE is there to
  catch; a red they declared and this card *widens* is the hazard CARD-330 exists for.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids
  included. **ONE NAMED EXCEPTION, granted at the decompose station 2026-10-30**
  (a guardrail is weakened here and nowhere else — never in a worktree):
  `tests/test_book_puzzle_page_vector.py:1950`'s
  `class TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`
  **may be renamed**, and only it. Its *body* is honest; its **name** became
  false when CARD-306 gave the vector puzzle page exactly the sheet furniture
  the name denies (folio, frame rules, grid-size label, QR block). CARD-306
  raised it as F-307; CARD-309 examined it, found the only fix is a rename, and
  **correctly declined** under this very guardrail — see its round's findings.
  The rename is this card's because this card converts the kind and will be in
  that file anyway. Spell the replacement for what the class now asserts, and
  re-stamp every consumer of the old node ids in the same commit: a renamed
  class is a node-id change, so `ADDED_SINCE_BEFORE`, any `_SEEN_REGIONS`-style
  census and any frozen snapshot naming it move **with** it or the gate finds
  them.
- **G-6: do not weaken `_write_pdf`'s representation refusal to let a conversion land.** It is the
  thing that makes a partial conversion safe; a card that loosens it to get green has removed its own
  safety net.
- **G-7: do not edit `tests/test_cli.py`'s structural layering guard.** If a writer cannot be reached
  without violating it, that is CARD-309's assembly point failing, and it is a finding.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators (check: review-lens → **this card flips it**, with the last conversion)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard, plus the landing-direction half)
- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0036/R1 — the A4 golden's byte identity for the no-PageSpec default path (check: the A4 golden)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte
- CON-020 — the 10 pt interior type floor, clue digits exempt **by their mark** (check: CARD-314's)
- INV-013 — the interior holds no cover page; parity counts from interior page 1
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0039/R4 — a figure's instrument is part of the figure (check: **executing**, CARD-304)

## Architecture context

- **ADR:** ADR-0042/R1-R2-R6, ADR-0039
- **Components:** COMP-009 and the four vector page writers
- **Trace:** ADR-0042/R1's `check:` is re-stamped here, from a lens to a node id.
  <!-- CORRECTED 2026-10-31 at the re-cut, twice. (1) **A BARE TEST NAME, not a node
       id** -- see AC-1's note and this ADR's own R2/R5 comments, which each
       measured the node-id spelling reporting as a DEAD check ref. (2) **No
       `trace.yml` row moves.** CARD-312's Trace line records the measurement: at
       2026-10-29 `trace.yml` held NO ADR-0042 rule rows at all, prose only at
       `:1813` and `:1853`, and it names "do not write a Trace line promising one"
       as the mistake CARD-298 inherited. Re-verify before writing anything to
       `trace.yml`; the ADR's own Rules block is the artefact this card edits. -->
  <!-- Also at the re-cut: ADR-0042/R6's comment assigns the FRAME-CENTRE ORACLE to
       this card by name ("that belongs with the conversion, i.e. to CARD-322").
       **CARD-336 owns the amendment that re-points that sentence**, and it is the
       only `meta/architecture` edit in that card's scope. Do not also edit it here. -->

## Worktree notes

- **Expect the merge gate to find a frozen registry this card moves.** Two cards in one hour on
  2026-10-30 went red at the gate on cross-card censuses that `review.test_scope: impact` is
  structurally unable to see — CARD-314 on the ref census (three `trace.yml` additions, and **a third
  baseline hidden behind the one that short-circuited**) and CARD-269 on the browser-family register
  (35 unregistered tests). **This card re-stamps `trace.yml` and moves baselines. Derive which
  registries your diff touches and run them before the gate does.**
- **Do not paste the number a frozen baseline prints when it reds.** Both guards say so themselves:
  re-derive the symmetric difference, assert **nothing left**, and resolve each entrant to a real
  `def`/`class` line read off the line. A class that *shrinks* because a review report was synced in
  is signal loss, not a repair.
- **CARD-288 depends on this phase.** Its four tests obtain pages from `interior_pages()`, which is
  declared `-> List[Image.Image]` and stops being that here. It is correctly sequenced after.

### The re-cut's own reasoning, 2026-10-31 — why three cards and not one, and not five

- **[The principle applied, and the axis it was applied on]** CARD-309's own item 1 —
  *"one kind at a time, each removal complete… what makes this card incremental rather
  than all-or-nothing"* — is a statement about **separately judgeable deliverables**, and
  the re-cut applied it on the axis where this family's deliverables actually separate:
  **mechanisms, not kinds.** CARD-336's judgement (*does the reading report the boundary,
  in both media, against a coordinate?*) and CARD-337's (*is every module that reads or
  decides an interior page's medium green under a five-kind probe, or named with its
  owner?*) are each complete with **no page converted** — the property that made CARD-312
  and CARD-329 closable, and whose absence is why CARD-309 measured 189 failures + 75
  errors and could not close. This card's judgement is the one that genuinely needs a
  converted tree, so it goes last and alone.
- **[Why NOT split by kind, which is the tempting seam]** Two measurements killed it, and
  both are recorded in the re-cut section above: the **19 live book baselines would be
  re-recorded twice** (CARD-222's own dependency note states the rule — *"racing it would
  make two cards re-record the same fixtures"*), and `expires_with` would need a
  **per-kind re-point in `src/`** to keep
  `test_no_declaration_outlives_the_cards_that_remove_it` green, putting a registry edit
  on the critical path of a live board guard for no measurement gained. As cut, **no
  `expires_with` edit is needed at all**: all five entries name
  `("CARD-299", "CARD-322")`, this card still removes all five, and the guard reds only
  when *every* card an entry names is terminal.
- **[Why this card stayed CARD-322 rather than becoming a new terminal card]** **Seven
  `ready` cards depend on CARD-322** — CARD-207, CARD-209, CARD-229, CARD-230, CARD-232,
  CARD-233 and CARD-288, with CARD-273 behind them — and every one of them is gated on
  *"the conversion its tests are supposed to target"*, which is still exactly what this
  card does. Keeping the terminal deliverable on this id means **not one dependent edge
  moves**, and the owner's steer (*"this card is the destination"*) stays literally true.
  The two new cards were inserted **upstream** of it instead.
- **[The estimate, and the calibration behind it]** 2d here, 2d + 2d upstream: **6d where
  the board had 1d.** The board's estimates in this family run long against actuals —
  CARD-329 was 2d estimated and **4.1h actual** — so 6d is an honest ceiling rather than a
  prediction, and `sizing.max_estimate` is `1d` with a single 2d precedent (CARD-329),
  which is why nothing here is priced above 2d. The scope that drives it is not the
  conversion: the `src/` change is **five dict entries**. It is the 19 baselines with
  size and time at both ends, R1's flip with a `comm`-diffed validator reading, the arm
  re-point with its set **derived**, the clip divergence against a module that goes 1 → 33
  reds, the rename with its two consumers, population C's own derivation, and the owner
  render.
- **[A reader-facing warning about this card's biggest single unknown]** The residue this
  card faces *after* CARD-336 and CARD-337 land is **unmeasured and unmeasurable today** —
  it is an inference about a tree that does not exist yet, which is this family's
  signature failure. The number is **not** 225 minus 39 minus 68: the five-kind census
  measures counts and not causes, and the one cause sampled at the re-cut was a mechanism
  nobody had named (an **expected-side gap** at
  `property/test_book_export_interior.py:546`, whose own message names a stale card). Item
  0 exists to replace that inference with a measurement before any conversion is made.
- **[CARD-288's disposition under the re-cut: UNCHANGED, and the reason is now sharper]**
  `Revision pending: true` with "premise dissolved by CARD-322" still holds, and
  `Depends on: CARD-322` is still the right edge: its own unblocking condition says *"Do
  not clear this flag on CARD-322's merge. Re-cut the card after CARD-322, against
  whatever `tests/property/test_book_pdf_geometry.py` then is"*, and that file is now
  **CARD-336's** (all four of its node ids, at 2.07x–5.46x their own bounds). So the
  successor CARD-288's own note anticipates — *"the successor to this card is most likely
  whatever CARD-329's triage names"* — resolves to CARD-336, and CARD-288's re-cut should
  read that card's round, not this one's. **The edge was left pointing here** rather than
  re-pointed at CARD-336, because the premise that dissolves it is the *bitmap count* and
  the bitmaps go when the **declarations** go, which is this card. Re-pointing it at
  CARD-336 would gate it on a card that converts nothing.
