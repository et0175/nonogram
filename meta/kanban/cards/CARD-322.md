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
**Estimate:** 3c (1.5d) <!-- RESTATED in review cycles 2026-11-06 at the SPLIT, before any stamp (a waved card with no Nc term reddens tests/test_kanban_review_record.py, as CARD-325 did). Was `2d`, itself a re-cut of 1d. The premise pass priced the card as written at 5c (2.5d) against the board's sizing.max_estimate of 1d and the owner split it: the part that needs no src/ change and no owner decision is CARD-379 (about 2c); this is the FLIP card, about 3c. Basis: comparators of 29 to 33 reds at 2c landed in 1 cycle (CARD-355, 354, 356), 15 reds at 2c took 2 (CARD-357), 8 to 12 reds at 1c took 2 or 1 (CARD-358, 359, 360), CARD-324 took 3; the mean of this wave's ratios is 1.15. NOT priced: the owner decisions D1 to D8 in the premise note, any content oracle, waits behind gates, and the case where the difficulty-dot instrument has no raster page to measure. -->
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
**Depends on:** CARD-309, CARD-329, CARD-330, CARD-331, CARD-336, CARD-337, CARD-338, CARD-354, CARD-355, CARD-356, CARD-357, CARD-358, CARD-359, CARD-360, CARD-379
<!--TWO FINDINGS ROUTED HERE BY CARD-337'S ROUND, 2026-11-04, both measured and neither fixable under its G-1.
 (A) A PRODUCT CONSEQUENCE NOBODY HAS DECIDED: the conversion makes `books.interior_ink_mode` have NO EFFECT on 10 of 14 baseline interior pages, and 131 of 171 across the EC-1 corpus, because book_vector.ContentStream's entire colour vocabulary is stroke_grey/fill_grey -- there is no `rg`, so a converted page is DeviceGray whichever mode the book stored. The owner intake that module cites ("we may add colors for book2") is therefore foreclosed on every converted page. Same class as M3b's cp1252 refusal and routed the same way: a product behaviour change that only appears once the page is operators.
 (B) FOUR BASELINE FIXTURES CARRY PROSE THE CONVERSION REFUTES -- e.g. book_baseline_card147.json's "A reader checking the colour space must read it off the PDF's image XObjects." tests/fixtures/book_baseline_*.json is already in this card's Touches (item 5), so this is scope it holds and has not named. -->
<!--FINDING FOR THIS CARD'S DECOMPOSE PASS, 2026-11-04: its Touches reaches NONE of the four modules holding its own 10 five-kind reds -- pdf_memory (M3 2), pdf_band (M3b 1), interior_type_floor (M1 1), property/test_book_export_interior (M1 5 + M2 1). Whether that is a defect depends on which side closes them, and the two halves differ: M3 and M3b are product behaviours whose CAUSE is src/nonogram/admin/book_pdf_generator.py, which IS in Touches, so they may close from the generator side without touching the test modules. M1 (the monkeypatch delitem sites) and M2 (the expected-side gap) are TEST-side and would need those modules listed. So 7 of the 10 are plausibly out of reach. Resolve it at the decompose pass rather than widening blind -- and note this is the same shape as CARD-347's scope note naming four locations where its Touches reached two. -->
<!--WIDENED 2026-11-04: this card depended on CARD-337 when that card was all thirteen modules of the residue. CARD-337 was module-sliced on the owner's instruction into itself plus CARD-354..360, so the real prerequisite is the whole set -- 129 of the 143 five-kind reds. The remaining 14 are already this card's own (10: M1/M2/M3/M3b) plus CARD-352's 2 and CARD-343's 2. Without this widening the graph would have let the conversion land on twelve still-red modules. -->
<!-- MOVED OFF THE FIELD LINE 2026-11-03 at CARD-338's merge gate. It sat INSIDE the
     parsed `Depends on` value, and that field's consumer (`readiness_score.
     establish_dependencies_resolved`) TOKEN-SCANS the value with `CARD-\d+`, so every
     card id inside a comment becomes a dependency -- the mechanism main's `fd9cbdfa`
     repaired board-wide after it closed a real cycle (CARD-336's comment named
     CARD-337, which really depends on CARD-336). This card's own comment was measured
     INERT (it spells the chain as bare `338 -> 336 -> 337 -> 322`, so the only
     `CARD-NNN` tokens in it are already real edges, and both readings of the 340-card
     graph agree), but it was authored by CARD-338 AFTER main's repair and would have
     landed a field main had just cleaned. Normalised to main's own convention. The note
     it carried follows, unchanged, as its own comment. -->
<!-- CARD-338 ADDED 2026-11-03 at CARD-338's fix round 1 (cycle-1 F-007): the field and the body disagreed. This card's body says CARD-338 built the instrument and "Run it, do not rebuild it", and routes to scratchpad/card338/. The edge was already satisfied TRANSITIVELY through CARD-336 (338 -> 336 -> 337 -> 322, the chain CARD-338 declares), so this is not a scheduling change -- it makes the field say what the body already relies on. -->
<!-- WIDENED 2026-10-30 at CARD-309's re-cut, from `CARD-309` alone. CARD-309 implemented this card's conversion to measure it and reverted it: 189 failures + 75 errors across 22 modules, four causes. Three of them are now cards and every one of them is a PREREQUISITE, not a sibling -- CARD-329 (the one-image reader), CARD-330 (the 0.169 mm the media disagree by, which changes the VALUE of every placed-edge expectation), CARD-331 (the difficulty-dot instrument, which on a vector page measures a page the product no longer draws and does so SILENTLY). Converting before CARD-330 decides its question means re-deriving every edge expectation twice. WIDENED AGAIN 2026-10-31 at this card's own re-cut by CARD-336 (the frame-centre oracle) and CARD-337 (the twelve modules CARD-329's triage left owed, plus the one its filters could not see) -- both split OUT of this card, both land before any page converts, and both share a file with this one, so they are serialized ahead of it rather than run beside it. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/app.py, src/nonogram/admin/book_proof.py, src/nonogram/admin/pdf_generator.py, tests/test_book_pdf.py, tests/test_book_difficulty_dots.py, tests/test_book_solved_answer_key.py, tests/test_book_puzzle_page_vector.py, tests/fixtures/book_baseline_*.json, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
<!-- CORRECTED 2026-10-31 at the re-cut. REMOVED `book_guide_vector.py`, `book_toc_vector.py`, `book_answer_vector.py`: measured, the walk ALREADY reaches all four downstream writers through CARD-309's `InteriorPageWriters` (`book_pdf_generator.py:7885/7934/8031/8051`) and the title page through its own `vector_title_page` (`:5266`, gated at `:7863`), so no writer module is edited -- ~~the src/ change is the five registry entries~~ [WITHDRAWN, see the next comment]. ADDED the four files the re-cut's own items need: `book_puzzle_vector.py:43` (the F-307 docstring consumer), `test_book_difficulty_dots.py` (CARD-331's arm re-point), `test_book_solved_answer_key.py:3783` (CARD-297's clip divergence) and `test_book_puzzle_page_vector.py:1950` (the F-307 rename itself). -->
<!-- WITHDRAWN 2026-11-03 by CARD-338 (fix round 2, cycle-2 F-101a): the struck clause above, "the src/ change is the five registry entries", is FALSE AS MEASURED. Read §2's `[CORRECTION 2026-11-03, CARD-338]` and item 1 before reading this field: the walk reaches those four writers only through the writer set the generator was BUILT with, `BookPDFGenerator.__init__` defaults that set to `NO_DOWNSTREAM_WRITERS`, and `interior_generator` has zero call sites in `src/` -- so the `src/` change is the five entries PLUS a decision about the generator's default. The sentence is left standing, struck through, per this card's convention of carrying its corrections inline so the record shows what was claimed when. This was the THIRD site of that clause and the only one no earlier pass looked at, because it is a metadata field rather than a prose section. -->
<!-- MOVED OFF THE `Touches:` LINE 2026-11-03 by CARD-338 (fix round 2), and that is not cosmetic. `card_lint.parse_card_fields` strips no HTML comment and `card_lint.extract_touches` splits the field on COMMAS, so while the note above sat on the field's own line the parser read it as part of the VALUE: measured, 15 "globs" instead of 8, seven of them prose fragments, and the eighth was `...0042-...-raster.md <!-- CORRECTED 2026-10-31 at the re-cut. REMOVED `book_guide_vector.py`` as ONE glob -- which destroyed the ADR path this card declares. `compute_excess` then reported `meta/architecture/decisions/adr/0042-...md` as EXCESS although the field names it, on a card whose item 3 edits exactly that file. Measured both ways on this card: 15 globs -> 8, and the ADR leaves `excess` the moment the comment is on its own line. Keep every comment on its own line here. -->
<!-- WIDENED 2026-11-03 by CARD-338 (fix round 2, cycle-2 F-101b), by `src/nonogram/admin/app.py`, `src/nonogram/admin/book_proof.py` and `src/nonogram/admin/pdf_generator.py`. These three are live ONLY on option A of item 1's decision (moving the construction sites to `interior_generator`); option B (changing the generator's default) touches none of them. They are declared anyway, deliberately, in the conservative direction -- because this field is read MECHANICALLY and is read AT DISPATCH, before item 1's decision is made. Measured in forge's own `review_cycle_ops`: `compute_excess` penalizes UNDER-declaration only (a file edited and undeclared becomes `excess`, and the verdict degrades to `grown`/`runaway`) and costs nothing for a declared file left untouched, so over-declaring is the error that cannot red. `app.py` and `book_pdf_generator.py` are in `meta/kanban/config.yml`'s `conflict.hotspots`, which is what serializes this card intentionally rather than by arithmetic accident; `book_proof.py` and `pdf_generator.py` are NOT hotspots, and those two are where an undeclared edit would have been a silent collision. If item 1 settles on option B, narrow this field back and say so here. -->
<!-- CONFLICT EDGES, measured at the re-cut: this card INTERSECTS CARD-336 on `tests/test_book_pdf.py` and CARD-337 on `tests/test_book_solved_answer_key.py`, which is why both are `Depends on` rather than same-wave siblings. It intersects CARD-316's live worktree NOWHERE. -->
<!-- CONFLICT EDGES RE-DERIVED 2026-11-03 by CARD-338 (fix round 2), because the widening above changes the enumeration rather than merely extending it: this card now also intersects **CARD-332** on `src/nonogram/admin/app.py`, which CARD-332 declares in its own `Touches:` (wave 73, `in_progress` at this re-derivation). That edge is conditional on option A, and `app.py` is a declared hotspot, so the serialization is intentional rather than accidental. Note what does NOT catch this edge: `compute_poached` subtracts `conflict.hotspots` from the sibling's Touches FIRST, and only considers siblings whose `Status` is `ready` AND whose `Wave` equals this card's -- CARD-332 is `in_progress` and this card's `Wave` is `—`, so it is skipped twice over, and `app.py` would be subtracted even if it were not. This comment is the only place that edge is recorded, which is why it is recorded here. -->
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

### 2. ~~The src/ change is the five registry entries, and nothing else~~ [WITHDRAWN 2026-11-03, CARD-338 — see the correction blockquote below]

Measured by reading the walk: `book_pdf_generator.py` already reaches **all four**
downstream writers through CARD-309's `InteriorPageWriters` (`:7885`, `:7934`, `:8031`,
`:8051`) and composes the title page itself through `vector_title_page` (`:5266`), gated at
`:7863` by `page_medium(PageKind.TITLE) is PageMedium.VECTOR`. **So no vector writer module
is edited and the production conversion is the deletion of five dict entries.** `Touches`
is corrected accordingly. *Everything expensive about this card is on the other side of
that deletion*, which is the fact the 1d estimate was missing.

> **[CORRECTION 2026-11-03, CARD-338 — the claim above is FALSE as measured, and it is the
> one thing in this card that is not a test-side cost.]** The walk reaches the four
> downstream writers only *through the writer set the generator was built with*, and
> `BookPDFGenerator.__init__` defaults that set to `NO_DOWNSTREAM_WRITERS` — a full
> default-DENY. **`interior_generator`, the one call that builds an assembled generator,
> has ZERO call sites in `src/`**: production builds the generator at **seven** sites in
> `src/` outside `interior_generator` — four in `app.py`, one in `book_proof.py`, one
> inside `book_pdf_generator.puzzle_page_plan` and the bookless module-level
> `_pdf_generator = BookPDFGenerator()` in `pdf_generator.py` — six of them
> `BookPDFGenerator(book)` and the last that bookless singleton. **Item 1's table is the
> enumeration of record**, and it names each site by its spelling rather than its line
> (cycle-3 M-204: `main` moved `app.py` mid-review and two of the four line citations
> rotted). <!-- CORRECTED 2026-11-03 by CARD-338 (fix round
> 2, cycle-2 M-102): this blockquote first said "six", spelled `pdf_generator.py:344` as a
> `(book)` build (it is `_pdf_generator = BookPDFGenerator()`, evaluated at import) and
> omitted `book_pdf_generator.py:1912` altogether. See item 1's re-measured table, which is
> the enumeration of record. The conclusion is unchanged. -->
> And the `app.py` site whose next statement is `return generator.export_interior(puzzles)`
> is the download path, and the only one of the seven that writes an interior. So the day
> the `GUIDE`/`TOC`/`ANSWER` entries are deleted, that path hits `_drawn_downstream`'s
> refusal: *"a guide page is written as operators (ADR-0042/R1) and this generator was
> built with no downstream writer for it"*. **Measured, not reasoned:** CARD-338's
> `fidelity_to_the_end_state.py` ran `tests/test_book_interior_type_floor.py` against two
> on-disk trees — five entries deleted and nothing else (**25 reds**), versus the same plus
> the default writer set assembled (**8 reds**). **Seventeen reds in one module are that
> refusal.** The `src/` change is therefore the five dict entries **plus** either moving
> those **seven** construction sites to `interior_generator` or changing the generator's
> default — a decision this card has to make and did not know it had.
> <!-- CORRECTED 2026-11-03 at CARD-338's merge gate (cycle-3 M-201a): this sentence said
> "those six call sites" four lines after the same blockquote enumerated SEVEN, so the
> blockquote contradicted itself. Item 1's table is the enumeration of record and is right.
> "Six" is not defensible as "the six `(book)` spellings" either: `interior_generator(book=
> None, pages=None)` accepts no argument, so the bookless site converts too and all seven
> move under option A. --> It is also CARD-309's pattern
> repeating exactly as CARD-336's dependency note feared: *writers with zero call sites*.

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
(`property/test_book_export_interior.py` 2→7, `test_book_pdf.py` 38→46).
<!-- WITHDRAWN 2026-11-03 by CARD-338, in this card's own convention of carrying its
     corrections inline: "the instrument's artefact" is wrong in DIRECTION. Under the real
     end state the key is absent from the module's own dict, so the identical KeyError
     fires with no probe loaded -- measured on the E1 tree by
     scratchpad/card338/fidelity_to_the_end_state.py. These are this card's residue. The
     instrument-shaped share of the +74 is 0; had it existed it would have been +11, since
     13 is a SITE count and test_book_pdf.py already carries 1 of them PUZZLE-only. -->
In the **six** population-A modules with no `delitem` site at all — **seven**, re-derived
2026-11-03; ten carry no site and seven of them moved — the four extra kinds add
**+61 measured reds**:

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
and owned by **CARD-337**. The honest residue under the PUZZLE-only probe is **154**.
<!-- CORRECTED 2026-11-03 by CARD-338: the end-state figure below was 228 (225 + 3), which
     added this module's PUZZLE-only reading to the five-kind total. Under five kinds the
     module is 8, and the artefact share is 0, not ≤13 -- both re-derived, see item 0. -->
Under this card's end state it is **233** (225 + 8), **of which none is instrument
artefact**: the 13 `delitem` reds were measured identical on a tree with the five entries
deleted in `src/` and no probe loaded, so they are this card's residue.
Its population is **derived**, not listed, by
`scratchpad/card338/derive_medium_population.py`, whose filter is a module whose AST names
the medium decision itself and whose assertion reds when a module that should be in the
population is not.

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
  **Still unmeasured** — it remains an inference about a tree that does not exist until
  those two cards merge. **What is no longer unmeasured is the floor before they land:
  233** (CARD-338, `f407c350`, item 0 above). The instrument that measures the rest exists
  and is committed, so this premise is now one re-run away rather than one card away: run
  `scratchpad/card338/census_five_kinds.py --third` on the merged tree before converting
  anything.
* *That the +61 measured in the six uncontaminated modules is more cells of the mechanisms
  already named rather than new mechanisms.* **MEASURED 2026-11-03 by CARD-338 and the
  answer is yes, with two corrections.** All 233 reds are grouped by message into named
  mechanisms with an owning card each and **no "other" group**
  (`scratchpad/card338/classify_reds.py`); the expected-side gap sampled below is **1 red**,
  not a family. Correction one: it is **seven** uncontaminated modules that move, not six
  (ten population-A modules carry no `delitem` site; seven of them moved), and their deltas
  still sum to +61. Correction two: a mechanism nobody had named did turn up, and it is one
  red — `book_pdf_generator.py`'s `RuntimeError` for a glyph outside the interior's cp1252
  encoding, which **only becomes reachable once the page is drawn as operators**. That is a
  product behaviour change on this card's path, not a test repair. The cause sampled at the
  re-cut was:
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

0. **The floor is MEASURED — CARD-338 did it, and this item is now a re-run, not a
   derivation.** <!-- SATISFIED 2026-11-03 by CARD-338, which this card depends on. The
   instrument and the number are below; what is left here is one re-run on the merged
   tree, because the figure is dated to a tree, not to this card. -->
   The instrument is `scratchpad/card338/probe_five_kinds.py` with
   `scratchpad/card338/census_five_kinds.py`; it lifts the five kinds whose `expires_with`
   names this card (derived from the registry, not listed) and rebinds
   `book_pdf_generator.NO_DOWNSTREAM_WRITERS` to
   `book_interior_vector.DOWNSTREAM_WRITERS`. Measured at `f407c350` over CARD-329's 20
   modules **plus `tests/test_book_interior_type_floor.py`**:

   | | `PUZZLE` only | all five kinds |
   |---|---|---|
   | modules red | 18 / 21 | **19 / 21** |
   | failed + error | 154 | **233** |
   | passed | 1272 | 1193 |
   | skipped | 1 | 1 |

   **This card's floor is 233** — not the 228 this card's own re-cut carried, which added
   the 22nd module's *PUZZLE-only* 3 to the five-kind 225; under five kinds that module is
   **8**. The one skip is the `setrlimit(RLIMIT_AS)` platform gate at
   `tests/test_book_pdf_memory.py:1297`, attributed from `-rfs` as one flag; neither
   database gate fired. **Re-run the census on the merged tree before converting anything**
   and state the number you get; a different number is the finding.

   **The `monkeypatch.delitem` separation is done, and it goes the other way.** **13 reds**
   come from `delitem` sites meeting a key that is gone — a *census* figure, measured per
   module (`property/test_book_export_interior.py` **5**, `test_book_interior_type_floor.py`
   **1**, `test_book_pdf.py` **7**) — and `scratchpad/card338/`
   `fidelity_to_the_end_state.py` measured the identical count on a tree whose five entries
   are **deleted in `src/` with no probe loaded**, so **they are this card's residue and
   not the instrument's shadow**. The re-cut's "≤13 of 74 is artefact" is withdrawn: the
   artefact is **0**, and the instrument-shaped share of the +74 would have been +11 in any
   case. The probe's red count matches the on-disk end state **±0**.
   **Separately, there are 13 `delitem` SITES that can raise** — 17 sites, 2 with
   `raising=False`, 15 able to raise, 2 of those naming `DIVIDER` which is not lifted. **The
   two 13s are two quantities and neither is derived from the other:** one site produces 5
   reds alone and two (`test_book_pdf.py:3747`, `:3774`) are `delitem` calls inside
   `for kind in self._interior_kinds()` loops covering 4+ kinds each. Take the red count
   from `census_five_kinds.py` and the site count from `derive_delitem_sites.py`; never
   divide one into the other.

   **Every one of the 233 carries a mechanism and an owner, with no "other" group**
   (`scratchpad/card338/classify_reds.py`, which exits non-zero on an unmatched cause).
   This card's own families: the registry-derived guards (**7**), CARD-331's raster arm
   declaring itself dead (**2**), `_write_pdf`'s representation refusal reached (**2**), the
   expected-side gap (**1**), and the 13 above.
1. **One kind at a time, each removal complete — and there are FIVE.** For `TITLE`,
   `GUIDE`, `TOC`, `ANSWER` and `PUZZLE`: delete that kind's entry from
   `_RASTER_DECLARATIONS` and let `_write_pdf`'s representation refusal prove the removal —
   a kind whose declaration is gone but whose page is still a bitmap is **refused, not
   shipped**. **No vector writer *module* is edited** — the four downstream writers and the
   title page's own `vector_title_page` are reached as written — **but the five deletions
   alone do not ship a vector interior, and that is MEASURED and SETTLED here, not an open
   question.** Read §2's `[CORRECTION 2026-11-03, CARD-338]` before touching the registry:
   the walk reaches those writers only through the writer set the generator was **built**
   with, `BookPDFGenerator.__init__` defaults that set to `NO_DOWNSTREAM_WRITERS`, and
   `interior_generator` has **zero call sites in `src/`**, so the day the `GUIDE`/`TOC`/
   `ANSWER` entries go, the download path hits `_drawn_downstream`'s refusal — **17 reds in
   `tests/test_book_interior_type_floor.py` alone (E1 25 → E2 8)**. **So this item carries a
   decision and must make it: either move the generator's construction sites to
   `interior_generator`, or change the generator's default writer set.** That decision is
   **this card's**, in `src/`, alongside the five deletions — it is **not** a finding to
   raise about CARD-309, and re-raising it is precisely the inference-instead-of-measurement
   loop CARD-338 exists to close. A kind's page walk failing to reach its writer for some
   **other** reason — one CARD-338 did not measure — is still a finding about CARD-309,
   raised and not absorbed.

   <!-- CORRECTED 2026-11-03 by CARD-338 (fix round 2, cycle-2 M-102). The sentence above
        read "either move the six `BookPDFGenerator(book)` call sites (`app.py:841`,
        `:960`, `:5580`, `:5759`, `book_proof.py:764`, `pdf_generator.py:344`) to
        `interior_generator`" -- the withdrawn list, quoted as it was written and NOT
        re-pointed, because a quotation of a retracted sentence is history. Re-measured with `grep -rn 'BookPDFGenerator('` over `src/`,
        that list MISLABELS one member and OMITS another, and the count "six" was right
        only by coincidence. The enumeration below replaces it. -->

   **The construction sites, re-measured (this replaces the "six call sites" list this item
   first carried).** There are **seven** construction sites in `src/` outside
   `interior_generator`'s own `return BookPDFGenerator(...)`
   (`book_interior_vector.py:141`):

   <!-- CITED BY SPELLING, NOT BY LINE, 2026-11-03 at CARD-338's merge gate (cycle-3
        M-204). This table first carried `app.py:841 / :960 / :5580 / :5759`. CARD-332
        merged into `main` DURING CARD-338's cycle-3 review and moved `app.py` by +97
        lines: `:5580` became `:5673` and `:5759` became `:5852` — and `:5580` was the row
        marked "the one site that writes an interior", so the load-bearing citation was the
        one that rotted, silently. A line number rots without a sound; a spelling is stable
        across edits and self-verifying, which is this board's rule. The sites are therefore
        named by what the call is, re-derived on main at `fd9cbdfa` with
        `grep -rn 'BookPDFGenerator(' src/`; the "re-derive at dispatch" line below is now
        a convenience, not the only defence. -->

   | site | spelling | what it builds for |
   |---|---|---|
   | `app.py`, the `BookPDFGenerator(book).section_plan(list(puzzles))` one-liner | `BookPDFGenerator(book)` | `.section_plan(...)` — a page plan |
   | `app.py`, the build followed by the interior-count read | `BookPDFGenerator(book)` | interior counts |
   | `app.py`, **the build whose next statement is `return generator.export_interior(puzzles)`** | `BookPDFGenerator(book)` | **the download path, the one site that writes an interior** |
   | `app.py`, the build followed by `.section_plan(rows)` | `BookPDFGenerator(book)` | `.section_plan(rows)` — a page plan |
   | `book_proof.py`, in the proof-sheet build | `BookPDFGenerator(book)` | the proof sheet |
   | `book_pdf_generator.py`, inside `puzzle_page_plan` | `BookPDFGenerator(book)` | `puzzle_page_plan` — **omitted from the first list entirely** |
   | `pdf_generator.py`, the module-level `_pdf_generator = BookPDFGenerator()` | `BookPDFGenerator()` | **bookless, a module-level singleton evaluated at import** — not a per-request build, and not the `(book)` spelling the first list claimed |

   *Line numbers as of `main` `fd9cbdfa`, for convenience only and expected to rot:*
   `app.py:841`, `:960`, **`:5673`** (the interior write, `export_interior` at `:5677`),
   `:5852`, `book_proof.py:764`, `book_pdf_generator.py:1912`, `pdf_generator.py:344`.

   **Nothing in the conclusion moves, and two things in the costing do.**
   `interior_generator(book=None, pages=None)` accepts no argument, so the bookless site
   converts too; and `book_pdf_generator.py` is already in `Touches:`, so the omitted site
   widens the field no further. What does move: **only the `export_interior` site reaches a downstream
   interior write at all** — the other six build plans, counts or a proof sheet — so option A
   is a larger edit than the refusal strictly requires. Weigh that against option B before
   choosing, and take the count from this table, not from the withdrawn sentence.

   **Option A has two consequences the decision must name. Neither is a reason not to take
   it; both are reasons not to take it silently.** <!-- ADDED 2026-11-03 by CARD-338 (fix
   round 2, cycle-2 M-103 and F-101b). -->

   1. **It ends the leaf property — and that property is ASSERTED BY A LIVE TEST, not only
      claimed in prose.** `tests/test_book_pdf.py:3656`,
      `TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_nothing_in_the_package_imports_the_assembly_point`,
      asserts `importers == []` for `nonogram.admin.book_interior_vector`. Option A makes
      four `src/` modules import that module, so **that cell reds** — measured green at this
      writing (that class: 5 passed). Its own docstring calls this the "load-bearing" one of
      AC-5's three facts (*"without it a later card could import the assembly point from
      `app.py` and from `book_guide_vector`, and the cycle would be back with an extra
      module in it"*), so re-pointing or retiring it is an argument CARD-309's AC-5 is owed,
      not an edit to make in passing. `tests/test_book_pdf.py` IS in this card's `Touches:`,
      so the card may legally edit it — the point is that it must not do so quietly. No
      import CYCLE results (`app.py` and `book_proof.py` already import
      `book_pdf_generator`, which `book_interior_vector` sits downstream of), so the cost is
      the guard and the claim, not a loop. The prose statements of the same property are
      **CARD-338.md:42-43** and **CARD-309.md:597** — two cards, measured by
      `grep -rnE 'nothing in .?src/.? imports'` over `meta/kanban/cards/`, and neither of
      them is CARD-337, which states the rebinding and not the leaf.
   2. **It widens `Touches:` and the conflict edges**, which is why the field at the top of
      this card now declares `app.py`, `book_proof.py` and `pdf_generator.py` and records the
      **CARD-332** edge on `app.py`. Option B is what narrows them back; if you take it, say
      so in the field.
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

## [SPLIT 2026-11-06] — the pre-flip work moved to CARD-379; this card is the FLIP

On the owner's instruction after the premise pass below, the part of this card that can go green BOTH unlifted and under the probe with no `src/` change moved to **CARD-379** (`Depends on` now includes it, so this card is not ready until it is done): the 13 `delitem` reds (`tests/property/test_book_export_interior.py` 5, `tests/test_book_interior_type_floor.py` 1, `tests/test_book_pdf.py` 7), the M2 expected-side gap, the 2 M3 `_write_pdf` refusal reds in `tests/test_book_pdf_memory.py` and the 2 unowned `tests/test_book_interior_face.py` reds, plus a measure-only look at whether the difficulty-dot instrument would have a raster page. **What stays HERE:** the five registry deletions, the A-decision, the 32 raster-reading cells and 7 registry assertions in `tests/test_book_pdf.py` (to be retired with named stream-medium survivors under a second named G-5 exception), `tests/test_book_difficulty_dots.py` (29), the M3b refusal in `tests/test_book_pdf_band.py` (a PRODUCT decision, D4), the R1 flip, the clip divergence, the rename, the baselines record and the owner render. **This card is NOT to be stamped into a wave, and its items, ACs, Touches and G-5 are NOT yet re-cut:** that re-cut waits on the owner's rulings D3, D4, D6 and D8 in the premise note (D1, D2 and D7 have defaults the pass proposed), and on CARD-379's census, which will be the starting tree. The text of items 0 to 7 and the ACs below still describes the UNSPLIT card and must be read through this banner.

## Premise re-verified 2026-11-06 (all 14 dependencies are done; main tip 51bbf6cf at the pass)

Read against `main` by a READ-ONLY premise pass (every run in a private clone at `51bbf6cf`; the full report with its 43-row claim table is kept at `~/Documents/nonogram-reviews/CARD-322/premise-pass/REPORT.md`), then spot-checked by the orchestrator. **This section states facts; it changes no AC, Touches or estimate: those wait on the owner's rulings below.** Measured by the pass unless marked: every module is GREEN unlifted; under the five-kind probe **94 tests are red in 10 of 21 censused modules**, and the card's floor of 233 is superseded.

| module | red | cause lines | owner |
|---|---|---|---|
| `tests/property/test_book_export_interior.py` | 6 | 5 `KeyError: PageKind.TITLE` in `TestInteriorReadings_TheStreamArmIsReached`; 1 "interior page 2 is written as operators but no vector guide writer" | this card (M1 + M2) |
| `tests/test_book_interior_type_floor.py` | 1 | `KeyError: PageKind.TITLE` in `test_lifting_a_declaration_makes_the_stream_arm_read_that_page` | this card (M1) |
| `tests/test_book_pdf_memory.py` | 2 | "page 1 is a vector puzzle page, but arrived as Image" (the `_write_pdf` refusal) | this card (M3) |
| `tests/test_book_pdf_band.py` | 1 | the `'Χιονονιφάδα' (U+03A7) is not in the interior's cp1252 encoding` refusal on the full-corpus test | this card (M3b), a PRODUCT decision |
| `tests/test_book_pdf.py` | 46 | 32 cells reading interior pages as bitmaps (`'ContentStream' has no attribute 'convert'` x27, `.size` x3, `KeyError b'XObject'` x2); 7 `delitem` KeyErrors; 7 registry assertions | this card |
| `tests/test_book_difficulty_dots.py` | 29 | 27 `'ContentStream' ... 'convert'`; 2 "raster arm is DEAD" | this card |
| `tests/test_book_interior_face.py` | 2 | "pages that differ ... must be exactly the seven" (moved: [5, 7, 9, 11]); "no band was drawn" | **no card** (orchestrator-verified: 2 red under the probe, 17 passed unlifted; no open card's Touches names the module) |
| `tests/test_book_guide_page.py` | 2 | `assert 0 == 1`; `(3, 160.5)` | CARD-343 (`ready`; whether it owns both reds is unconfirmed) |
| `tests/test_book_puzzle_frame.py` | 3 | "a row through the grid shows weights [2, 4, 6]" | CARD-342 (`ready`) |
| `tests/test_book_pdf_two_up.py` | 2 | placed-edge `0.2313 <= 0.0423` | nominally CARD-352, which CANNOT close them: its Touches is `tests/test_book_puzzle_frame.py` only (orchestrator-verified) |
| `tests/property/test_book_pdf_geometry.py` | 4 | page-size and placed-edge asserts | CARD-350 / CARD-336 (declared half-pixel) / the hang guard; MEASURED only with `NONOGRAM_TEST_HANG_SECONDS=600` (167 s, 4 failed, not killed) |

Of the 94: 85 are this card's; 9 are CARD-342's 3, CARD-343's 2, the 2 `interior_face` reds nobody owns and the 2 `pdf_two_up` reds CARD-352 cannot close; the geometry module's 4 are reported separately. Every other censused module is green under the probe (`export_interior_cover`, `solved_answer_key`, `pdf_levels`, `ink_mode`, `proof_pages`, `pairing`, `divider_pages_option`, `cell_size`, `arrange_page_breaks`, `trim_persistence`). The 10 reds the card already knew about are exactly as described.

**Where the card is WRONG or silent (the pass's findings, to be corrected when the card is re-cut):** (1) the placed-edge cells have no owner: the card says the ~30 raster-reading cells in `tests/test_book_pdf.py` are CARD-336's, but CARD-336's re-cut removed that module from its scope, and ADR-0042/R5 and the module's own pin say THIS card's conversion retires them; G-5 forbids deleting, renaming or skipping any test, so G-5 needs a second named exception, "retire with a named stream-medium survivor, listed per node id". (2) The 19 baselines do NOT need re-recording to go green: the baseline-reading modules are green under the probe, because CARD-355 settled that a stored digest is compared only against a bitmap page; the count of 19 holds, but AC-4, AC-4b, item 6 and G-4 rest on a premise that has dissolved. (3) R1's flip would be marked checked while violated: R1's statement names the proof sheet, which is still a separate, entirely raster writer, pinned by `test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision` (orchestrator-verified: exists once, in `tests/test_book_pdf.py`), and the test the flip would name covers the interior plan only. (4) Option B for the generator default is CLOSED and option A is partial: `book_interior_vector` imports `book_pdf_generator` at module level and its docstring rules out lazy imports and registries, which B would need; under A the `puzzle_page_plan` site inside `book_pdf_generator.py` cannot call `interior_generator` without a hidden cycle, so only the download-path site writes an interior. (5) The difficulty-dot arm re-point may have NO target: it says re-point at the cover or divider, but a grep suggests neither draws difficulty dots (`_draw_difficulty_dots` is puzzle-page-only; unmeasured). (6) AC-3b (whole tree green) cannot hold unless CARD-342, CARD-343, the two M8 reds and the `interior_face` pair are resolved or declared as inherited residue. (7) M3b has no item and no AC: a book with a Greek, Cyrillic or Hebrew puzzle name would stop exporting its interior once converted; a product decision nobody has made. (8) The geometry module's `PortraitWithFixedTopEdge_pdf_pages` corpus costs about 125 s once its assertion is green (CARD-336's measurement, carried); after the real conversion every page is poppler-rasterised and that node would exceed the default 120 s hang guard and kill the whole pytest process; G-4 forbids shrinking the corpus; it needs a ceiling decision.

**Stale and to correct (a list, nothing applied):** line numbers (`_DECLARED_CLIP_DIVERGENCE` now near 4073, not 3783; the red message in `tests/property/test_book_export_interior.py` near 552, not 546; the `setrlimit` skip near 1722, not 1297; the `DATABASE_URL` skip at `conftest.py` 233 and 253, not 207; the four writer call sites in `book_pdf_generator.py` each off by one): cite by NAME; population C is 8 modules, not 4; the `tests/test_book_pdf.py` registry count is 7, not 6; the AC-3b skip counts (26 + 1) are stale (derive off `-rEfs`; the armed baseline today is 1 skip, the `setrlimit` gate); CARD-332 and CARD-316 are done, not in flight; the red message still names CARD-309 and `vector_guide_page`, which does not exist (the assembled path is `generator.pages.guide`); a third consumer of the F-307 rename, a docstring in `tests/test_book_pdf_band.py`, is not listed. Held up: all 11 named tests exist exactly once; every Touches path exists; the seven gated cards (CARD-207, 209, 229, 230, 232, 233, 288: orchestrator-verified, all `ready`) depend on this card; the F-307 rename targets are real. **The Estimate is `2d` with no review-cycle term: this card MUST NOT be stamped into a wave in that state (it reddens `tests/test_kanban_review_record.py`, as CARD-325 did).**

**Proposed, NOT applied, pending the owner:** the pass proposes `5c (2.5d)` for the card as written and strongly prefers splitting it, because the board's `sizing.max_estimate` is 1d: a PRE-FLIP card of about 2c that can go green both unlifted and probed with no src change (`export_interior` 6, `type_floor` 1, `memory` M3 2, `interior_face` 2, the 13 `delitem` sites, and the difficulty-dot arm re-point if feasible) and a FLIP card of about 3c (the five deletions, the `test_book_pdf.py` 46, the R1 flip, the clip divergence, the rename, the baselines record, the owner render). Basis: comparators of 29 to 33 reds at 2c landed in 1 cycle (CARD-355, 354, 356), 15 reds at 2c took 2 (CARD-357), 8 to 12 reds at 1c took 2 (CARD-358, 359) or 1 (CARD-360), and CARD-324 took 3; the mean of this wave's ten ratios is 1.15 and the median 1.0; about 85 reds plus a src flip is about 2.8 such slices. Not priced: the owner decisions, any content oracle, waits behind gates, and the case where the dot instrument has no raster page to measure.

**OWNER DECISIONS the card needs** (separate from the mechanical corrections): D1 the page-content oracle gap (CARD-356, 357 and 360 each declared it: guide content beyond position/half/folio, stray-mark coverage on the answer, ungraded and TOC pages, the levels drawing): accept as declared residue or fund an oracle; D2 the `TITLE_PAGE_COUNT` by-value binding in `book_guide_vector` (routed here by CARD-357): fix in src or keep the two-patch workaround; D3 the proof sheet: narrow R1's wording, convert the proof writer (a card), or flip R1 with a carve-out, which decides whether the flip may claim "mechanically checked"; D4 M3b: what an unrepresentable glyph in a puzzle name does once the interior is vector (refuse = current, transliterate, wider font); D5 ink mode (CARD-364, already carded): this card must not decide it but must record that the flip lands it; D6 the hang-guard ceiling for the geometry node after the conversion (and for `tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces`, which already sits at the ceiling armed); D7 baselines: keep as historical records (the pass's default) or re-record; D8 option A scope: the writing site only, or all seven (B is closed). Not verified by the pass: no full suite (skip counts, the `test_cli` layering guard, the validator count); geometry unlifted not re-run; the dependents of the baselines beyond the listed modules; whether the divider or cover carry difficulty dots; whether production has non-cp1252 puzzle names (the database is forbidden); the "4 fixtures with refuted prose" count (the pass found three); CARD-312 compatibility; hang-guard behaviour at the DEFAULT ceiling for the kill-matrix test; up to five pytest processes ran concurrently with no flaky result seen.

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
  signature failure. The number is **not** 225 minus 39 minus 68 — **and both subtrahends
  are now retracted** (ADR-0039/R4), which strengthens this warning rather than weakening
  it. **39** was CARD-336's `PUZZLE`-only placed-edge figure; that card measured **38**
  under five kinds and closed as **4 cells + 1 declared**, so the figure both reproduced
  and had the wrong composition. **68** was never CARD-337's arithmetic at all: every
  per-module figure it rolled up reproduces to the digit, but the roll-up double-counted a
  guide-page red the body hands to CARD-336 while omitting the 8 reds of `pdf_levels` and
  `pdf_two_up` the body claims by name. CARD-337's measured figures are **78**
  (`PUZZLE`-only) and **143** (five kinds). So the sum this sentence warns against was
  built from one figure with a wrong composition and one that was a wrong addition — which
  is a better argument for the warning than the warning made. The five-kind census
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

[Routing note from CARD-359's review, 2026-11-05; informational, not a Review marker] When this card closes the guide-page abort in `tests/property/test_book_export_interior.py`, the FIRST export_interior test will red at `_measured` and at its answer-page `drawing_of(page).left` reads, with `page 6 draws its puzzle at 12.446 mm, not 12.700 mm`: the 3 px (0.254 mm) ink-first-line gap against the 0.1 mm bound, the same family CARD-359 fixed in `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage` by reading `frame_centre_of(...).frame_left`. Measured by the CARD-359 reviewer in a scratch copy with the abort skipped; the pages there come through `pdf_pages`, which already rasterises, so it is NOT a `ContentStream.convert` AttributeError (CARD-359's author-round note said so and was corrected). Convert those reads to `frame_centre_of`, or expect the red. CARD-359 deliberately did not edit that test because it is one of this card's six reds.

[Routing note from CARD-357's author round, 2026-11-05; informational, not a Review marker, not carded] `book_guide_vector` imports `TITLE_PAGE_COUNT` BY VALUE, so a monkeypatch of `book_pdf_generator.TITLE_PAGE_COUNT` does not reach the vector guide writer: the CARD-357 author measured (`scratchpad/halfcheck.py` in its worktree, copied to `~/Documents/nonogram-reviews/CARD-357/instruments/`) that with the constant at 2 the page at position 3 draws the guide's second half (385 operators) where the first half is 300. Production is unaffected (only a monkeypatch of the constant does this), and CARD-357's test works around it by patching `book_guide_vector.TITLE_PAGE_COUNT` as well and reading which half a page draws from its own text. It matters to THIS card only if the arm re-point or the guide-writer change touches how the constant is read: if the writer's reads of `TITLE_PAGE_COUNT` change, the workaround in `tests/test_book_export_interior_cover.py` may become redundant or wrong.

