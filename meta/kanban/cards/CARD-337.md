# CARD-337: `pdf_ink_mode` asks what colour space the FILE declares, and a vector page declares none — the claim has no subject in the converted medium

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/337-the-twelve-modules-the-triage-left-owed`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-337
**Source:** split from CARD-322 at the decompose station, 2026-10-31, on the owner's re-cut instruction. This is the list CARD-322's scope-gap section said "does not exist yet" and CARD-329's AC-6 round produced: the nine modules its triage reports as needing their own edit, plus the residue of the five it edited but could not repair. CARD-329's own words: *"Within this card's seven `Touches` paths that is unreachable, and the measurement says where the rest lives."*
**Split from:** CARD-322
**Idea:** —
**Wave:** 75
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** CARD-329, CARD-336, CARD-338
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
**Touches:** tests/test_book_pdf_ink_mode.py
<!--RE-CUT TWICE 2026-11-04. The first re-cut named three modules that hold ZERO of this card's reds -- the orchestrator joined a mechanism count and a module list from two tables of one report as if they shared a key, and they are orthogonal. Corrected to ONE module on the cross-tab: pdf_ink_mode holds all 9 M6 reds plus 1 M10, and is owned by no other proposed card. See the CORRECTION block. -->
**Review score:** 8.5 (cycle 1 of 3 — CERTIFIED)
**Started:** 2026-11-04T08:33Z
**Closed:** 2026-11-04T13:56Z
**Actual:** A **derived size datum, and the wall-clock figure is excluded.** Landed on main: **13 files, 2224 insertions / 94 deletions** — the one product module `tests/test_book_pdf_ink_mode.py` **769/93**, the census re-derivation in `tests/test_check_ref_resolution.py` **30/1**, and **11 instruments** under `scratchpad/card337/` **1425/0** — with **0 lines of `src/`** (G-1, verified on the merged tree). The sharper datum is the ratio of assertion to apparatus: of the 2224 insertions, **799 are the two test modules** and **1425 are the instruments that establish which 799**, i.e. **64% of this card's diff is measurement rather than deliverable** — which is the shape of a card whose subject was *what the file declares*, where every claim had to be measured in two media before it could be re-expressed. The deliverable itself is small and countable: **3 test functions / 13 cases added** (39 → 52), **0 removed, 0 renamed**, five claims re-expressed against the content stream and one retired with a named survivor, each of the six plants killed. **The wall-clock figure is excluded** under the owner's standing ruling that wall-clock actuals are unusable for estimate calibration because the clock measures the **queue** rather than the work: this gate ran the full suite **twice** (31m07s then 33m41s) because attempt 1 carried a browser flake that had to be re-measured rather than relayed, and `main` advanced underneath it once more (`0a4e5074`, kanban-only) — none of which is work done on this card. The size datum above substitutes for it, and this sentence is here so a reader **meets** the exclusion rather than noticing an omission. **Estimated 1c and certified on cycle 1 of a 3-cycle budget, so the cycle ratio is 1 / 1 = 1.000 — EXACT.** That is the **fourth exact estimate on this board** — CARD-278 (1c, cycle 1), CARD-336 (1c, cycle 1), CARD-339 (2c, cycle 2) and now this one — against CARD-335's 0.500, which stands as honest pricing of a card re-opened on a second measured harm rather than as a miss. **The estimate of record is 1c, and this needed checking rather than assuming:** `meta/kanban/board.md`'s wave-75 header still prices this card at **2c**, the figure it was opened with, because the header was written at the wave open (`550ff481`) and the card was **deliberately re-estimated to 1c at the re-cut** (`38020145`, "re-cut to the reader seam — 11 reds of 143, three modules, 1c") when its scope fell from thirteen modules to one. The card field is the authority and the board header is stale; a retrospective reading the board rather than the card would compute 0.500 for a card that was priced, and delivered, at one cycle. **The header is corrected in the same commit as this close** so the two inputs CARD-363 guards cannot disagree.
**Merge commit:** `830fa5d9` — merged `--no-ff` onto `0a4e5074`, **one kanban-only commit past the `163455ab` the gated tree was rebased onto** (`board.md`, `CARD-335.md`, `CARD-366.md`); all three are `.md`, so they touch no `tests/`, no `src/` and — because `.md` is excluded from the resolver's domain by suffix — cannot move the artefact census either, so the gated baseline is unaffected and no re-run was owed. Gated tree `f6a3982a`; merge-base `163455ab`. **The rebase took NO conflict — not in the card file, not anywhere** — because the branch never committed under `meta/kanban/**`: INV-023 holding (measured as 0 such paths on the branch side of a three-dot diff), rather than a gate working around it. **Full suite on the frozen gated tree, `DATABASE_URL` armed, `-o addopts=` as two argv items and `-rEfs` as ONE flag, under the board's own lock held as this worktree: 10294 passed / 0 failed / 0 errors / 1 skipped / 1 xfailed, exit 0, 2021.04s.** **Not vacuous:** passed + skipped + xfailed = 10294 + 1 + 1 = **10296 = the collected count exactly**. **Skip attributed by name from `-rEfs`, never recalled, and it is 1 rather than an unarmed run's 27:** the `setrlimit(RLIMIT_AS)` platform gate in `tests/test_book_pdf_memory.py`. No `Database not reachable` skip appeared at all, which is the positive evidence that the arming took — the 26 tests that skip unarmed were **executed**. **Neither CARD-349 hazard was live, checked BEFORE the run rather than diagnosed after:** the derived database `…_card_337_fd6a13723de9_test` already existed, and its `alembic_version` was **018** against a single migration head of **018**. **G-9 honoured** — the URL names a `*_test` database on localhost, never `nonogram_poc`. **This gate took TWO full-suite attempts and did not relay the first.** Attempt 1 returned `1 failed, 10293 passed` with a `Page.goto: Timeout 30000ms exceeded` in `test_puzzle_solver_brush_menu.py::TestSolverRegion_DoesNotChangeTheBrush::test_pressing_and_releasing_region_keeps_the_brush[Maybe]`, through `test_puzzle_solver_page.py`'s `_open` — the same failure and the same code path this board already diagnosed twice (CARD-271, CARD-238). It was **established as a flake, not assumed**, to CARD-271's own standard: this card changes zero `src/` lines and nothing the browser module imports, so it has no mechanism to reach a solver page; **only 1 of 4 parametrize cases failed** while `Black`, `White` and `Clear` passed in the same run against identical code, which no real regression can do; the class ran green in isolation **three consecutive times** on the gated tree (5.62s / 4.53s / 4.41s) and green on `main`; and host load was **6.75 / 7.69** on the 5- and 15-minute averages, the condition both prior cards name as the cause. Attempt 2 on the same frozen commit under `caffeinate -i` is the figure above, with that test passing. **Node-id delta, two instruments agreeing on the SET and not merely the total: 34 → 37 nodes and 39 → 52 cases, 0 lost and 0 renamed**, the 13 gained cases being 9 + 3 + 1 across three new cells in `TestBookInk_TheStreamReaderReadsOutsideStrings`. Instrument A is the round's `node_id_diff.py` (`ast`, both git blobs); instrument B is whole-module pytest collection with `-o addopts=` on both sides, which names the same set and nothing else. **G-1/G-2 on the merged tree:** `git diff --name-only 0a4e5074 HEAD -- src/` empty and `git status --porcelain src/` clean. **The force-add census on merged `main` measures 488 / `f36a57d4f39f3a48` with `scratchpad/card337: 11`, equal to the baseline this card re-derived**, and the whole of `tests/test_check_ref_resolution.py` is **26 passed** there — the figure main carried before the merge, so no other class moved.
**Blocked by:** —

> **[CORRECTION 2026-11-04 — the first re-cut was WRONG and this supersedes the block below it.]**
>
> **The orchestrator's first re-cut named `pdf_band`, `solved_answer_key` and
> `property/test_book_pairing`. Those three hold ZERO of this card's reds.** Measured on the
> cross-tab: **M6's 9 reds are entirely in `tests/test_book_pdf_ink_mode.py`** and **M6b's 2 are
> entirely in `tests/test_book_export_interior_cover.py`**.
>
> **How the error was made, because the shape is new:** the round's report contained two tables —
> a mechanism census (M6 + M6b = 11) and a seam-applicability classification (S1 = those three
> modules, *where `interior_images` can be placed*). The orchestrator **joined them on a key
> they do not share**. "Where the seam can go" and "where the seam's reds are" are orthogonal
> questions, and here the two answers are **disjoint**. Both tables were correct; the join was
> invented.
>
> **It gets sharper, and it retires this card's own name.** Both real modules are class **S3** —
> no medium-declared page source anywhere in their AST — so `interior_images` is **structurally
> inapplicable in both**, and neither red is a seam placement. "The reader seam" was never this
> card's subject.
>
> **And the two remaining repairs are unrelated to each other**, so keeping both would reproduce
> CARD-309 (one card holding unrelated causes, 189 failures, could not close). This card takes
> **one module**:
>
> **`tests/test_book_pdf_ink_mode.py` — 10 reds (M6 9 + M10 1), owned by no other proposed card.**
> Its own `pdf_image_objects` helper reads `resources[b"XObject"]` and reports the `ColorSpace`
> **as the file declares it**, and its docstring says it exists *beside* `tests/helpers/pdf_pages.py`
> deliberately, because that helper ends in `.convert("RGB")` — *"which normalises away the one
> thing this card changes"*. **A vector page has no image XObject and no `ColorSpace`, so the
> claim — grayscale versus RGB as declared — has no subject in the converted medium.** That is
> an ADR-0042/R6 re-expression against the content stream, or a retirement with a named
> survivor. It is a design question, not a repair, and it is why 1c may still be the wrong
> price.
>
> **`export_interior_cover`'s M6b (2 reds) is routed out**: `pdf_pages` raises when
> `_derived_dpi` returns `None` (*"no `dpi=` was given and this file's N raster page(s) do not
> settle one"*), so the repair is a **call-site argument**, not a seam. That module carries 15
> reds across three mechanisms and belongs to a module-sliced card.

> **[RE-CUT 2026-11-04 on the owner's instruction, AFTER the refutation below. Read this first.]**
>
> **This card is now the reader seam and nothing else: M6 + M6b, 11 of the 143 reds**, in the
> three modules where a module-level page source exists to wrap (`tests/test_book_pdf_band.py`,
> `tests/test_book_solved_answer_key.py`, `tests/property/test_book_pairing.py`). 2c → **1c**,
> thirteen modules → **three**.
>
> **The re-cut is based on the MECHANISM census, not on seam-applicability**, and that is the
> change that makes the card closable. The round classified all 143 with `classify_reds.py`,
> no "other" group and no shortfall, and the decomposition is:
>
> | mechanism | reds | owner after this re-cut |
> |---|---|---|
> | M10 medium-blind empty read | **57** | **CARD-354** |
> | M7d in-module `ContentStream` read | **40** | **CARD-355** |
> | M7 `page_ink` + M7b `two_up_ink` | **14** | **CARD-356** |
> | **M6 unprotected `KeyError: b'XObject'` + M6b `PageMediumRefused`** | **11** | **THIS CARD** |
> | M9 byte identity + M11 fixture write-counter | **9** | **CARD-357** |
> | M1 delitem / M3 / M3b cp1252 / M2 expected-side gap | **10** | **CARD-322** (already) |
> | M8 placed-edge | **2** | **CARD-352** — CARD-336 closed, so these needed re-routing |
>
> **Why the old shape could not close, measured rather than argued:** the seam closes **10 of
> 59** reds on the two largest modules where it applies (`pdf_band` 26 → 19,
> `solved_answer_key` 33 → 30) — **17 %**, against CARD-329's 80 %. It is structurally
> **inapplicable** in five of thirteen modules, whose pages come from `pdf_pages(data)` over
> exported bytes with no page object to wrap. And in two families **the seam is the cause**: a
> purity test reads `[0, 89, 255]` because poppler anti-aliases a vector rule, and the
> thin-rule-floor test's own docstring says it measures *the raster path's floor*. **A card
> asked to make thirteen modules green could not have, under its own G-1.**
>
> **Three corrections this card now carries rather than asserting the old claims:**
> 1. **The byte-identity family includes `pdf_band`** (3 cells), which the old AC-2 assigned
>    only to `pdf_levels` and `pdf_two_up`. Its enumeration was incomplete before it started.
>    → CARD-357.
> 2. **`arrange_page_breaks`'s five-kind reds are a BLANK rasterised page**
>    (`two_up_ink.py: ValueError: the page carries no ink at all`), not the region-segmentation
>    failure this card was partly named for. That segmentation question is an artefact of the
>    narrower `PUZZLE`-only probe. The blank-page mechanism is **CARD-343's**.
> 3. **One red in `pdf_band` is a product behaviour change G-1 forbids this card from touching** —
>    `book_pdf_generator.py` refuses a Greek title outside cp1252 once the page is drawn as
>    operators. It is **CARD-322's** (M3b).
>
> **One tooling hazard to know before pointing an instrument at a narrower dump:**
> `classify_reds.py` is **not filter-agnostic**. On the five-kind dump it is faithful (143/143,
> exit 0). On a `PUZZLE`-only dump of the same thirteen modules it leaves **13 of 78
> unclassified and exits 1** — loud, but only if the exit code is read. CARD-338 built it for
> the five-kind frame and it is correct for that frame; a card pointing it elsewhere must check
> the exit code, not the report.

> **[ITEM 0 RAN AND THE PREMISE FAILED — 2026-11-04. Read this before anything below it.]**
>
> The round ran item 0 under CARD-338's committed census, **implemented nothing and reported**,
> which was correct. Three independent refutations:
>
> **1. The scope moved UP, not sideways: 78 → 143 (+65, 1.83×)** across the thirteen modules
> under the five-kind filter. No direction was predicted and none was assumed.
>
> **2. The 68 is RETRACTED, and it was never a wrong measurement — it was a wrong ROLL-UP of
> correct measurements.** Every per-module figure in this card reproduces **to the digit** under
> the filter it was taken with: the nine routed modules sum to exactly 66, `arrange_page_breaks`
> is 1, `pdf_levels` and `pdf_two_up` are 4 each, the 22nd module is 3. What the body claims by
> name is **66 + 1 + 4 + 4 + 3 = 78**. The only route to 68 is **66 + 2** — the whole 2-bucket,
> which double-counts the guide-page red the body explicitly hands to CARD-336, while omitting
> the 8 reds of `pdf_levels` + `pdf_two_up` the body claims by name. **The figures are 78
> (`PUZZLE`-only) and 143 (five kinds).** Retracted in `meta/kanban/cards/CARD-322.md` too,
> where it appeared as "not 225 minus 39 minus 68".
>
> **This is the MIRROR IMAGE of CARD-336's defect and it needed a different check to catch.**
> There the figure reproduced exactly and the *composition* was wrong. Here every *component*
> reproduces and the *sum* does not. A brief that says "re-derive the figure" catches CARD-336's
> defect; **only re-deriving the ARITHMETIC over a card's own stated buckets catches this one.**
>
> **3. The seam closes 17%, measured on the repair rather than classified.** Planting the
> `interior_images` seam and measuring: `pdf_band` 26 → 19 (7 closed), `solved_answer_key`
> 33 → 30 (3 closed) — **10 of 59, 17%**, on the two largest modules where the seam applies at
> all. CARD-329's ratio was 80 → 16, **80% closed**. And the seam is **structurally
> inapplicable in five of thirteen modules** (42 five-kind reds) because they have no page
> object to wrap — their pages come from `pdf_pages(data)` over exported bytes, and that helper
> has read both media since CARD-329. CARD-329's routing sentence, "the identical one-line edit
> at the module's one page-source function", holds for **three of thirteen**.
>
> **Worse than inapplicable in two families: the seam is their CAUSE.**
> `test_the_rules_are_pure_black_and_not_anti_aliased` reads `[0, 89, 255]` after the seam
> because poppler anti-aliases a vector rule, and the thin-rule-floor test's own docstring says
> it measures *"the RASTER path's floor"*. The card's item 1 has no disposition for a claim the
> seam breaks.
>
> **The card needs a re-cut and 2d is not a ceiling for this shape.** The round's own reading:
> the seam is a three-module item worth ~17% of those modules' reds; five modules need a
> different mechanism entirely; and at least four survivor families each carry a per-module
> ADR-0042/R6 design question of the kind this card already prices at "could alone run a day"
> for one of them. **The scope decision is the orchestrator's and the round did not absorb it.**

## What this card is handed, measured, and re-derived at the decompose station

> **[PREMISE NOTE, wave-75 station, 2026-11-04 — read before the figures below.]**
>
> **The 151 and this card's 68 are `PageKind.PUZZLE`-ONLY readings**, taken at `b26bdd62`
> under CARD-329's `probe_puzzle_operators.py`, which lifts that one kind. CARD-338 measured
> the five-kind floor of the same 20 modules at **225**. So every figure this card inherits is
> measured against one fifth of the conversion — **the identical defect CARD-336 carried**, and
> the reason that card was re-cut mid-wave.
>
> **Whether the 68 moves under five kinds is UNMEASURED, and this note deliberately does NOT
> predict a direction.** At the wave-74 station the orchestrator wrote into CARD-336 that its
> population would GROW under the five-kind filter; the round measured it and it **shrank by
> one** (39 → 38), because the module totals moved while the *subpopulation* did not. A parent
> total and a subpopulation of it are different quantities. **Item 0 below measures this card's
> own population. Do not expect growth, do not expect stability, and report what you measure.**
>
> **What CARD-336's round did establish about this family, which you should read before
> trusting any inherited figure:** the *figure* reproduced exactly while its *composition* was
> wrong — of 38 placed-edge cells only 5 were closable by the mechanism the card was named for,
> 30 failed before any edge comparison, and 3 were a different mechanism entirely. **So a
> figure reproducing is not the premise holding.** Check what the population is made of.

### Item 0 — measure this card's population before implementing anything

Run **`scratchpad/card338/census_five_kinds.py`** (the driver; it drives
`probe_five_kinds.py`). **Run it, do not rebuild it** — CARD-338 owns, committed and
refusal-proved that instrument, and three cards describing one undelivered instrument is how
CARD-309 happened. Re-derive, for the 13 modules in `Touches`:

1. the **total** red count under `PUZZLE`-only and under all five kinds, side by side;
2. this card's **own 68**, derived by the mechanism each red actually exhibits rather than by
   the module it sits in — CARD-336's round classified by the *cause line the gate printed*,
   which is the technique to copy;
3. the **composition** of that 68: how many are the seam this card is named for, and how many
   are something else. **If the seam share is materially smaller than 68, say so and stop** —
   that is the finding, and it is what re-cut CARD-336.

**The estimate was priced against 68 and against "nine seams plus four non-seam mechanisms".**
If item 0 refutes either, raise it before implementing rather than absorbing it.



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

## The probe this card runs — CARD-338 built it — and what it measures

<!-- REWRITTEN 2026-11-03 by CARD-338. This section used to describe the five-kind
     extension as two lines for THIS card to write, and called the delitem KeyErrors an
     artefact of the instrument. CARD-338 owns the instrument, committed it, re-derived
     every figure, and MEASURED that the KeyError framing was wrong in direction. -->

**The instrument exists: `scratchpad/card338/probe_five_kinds.py`**, with
`scratchpad/card338/census_five_kinds.py` as its census and
`scratchpad/card338/classify_reds.py` as its triage. Run it; do not rebuild it. It lifts
the five kinds whose `expires_with` names CARD-322 — derived from the registry, not listed
— and rebinds `book_pdf_generator.NO_DOWNSTREAM_WRITERS` to
`book_interior_vector.DOWNSTREAM_WRITERS`, so every `BookPDFGenerator(book)` in the tree is
assembled and the four downstream kinds are drawn rather than refused. `src/` is read,
never edited: both mutations are to imported module objects for one process.

**It is faithful to the end state, measured rather than asserted.**
`scratchpad/card338/fidelity_to_the_end_state.py` stands the end state up a second way — a
copy of `src/` with the five entries deleted on disk and the default writer set assembled,
imported via `-o pythonpath=` — and the probe's red count matches it **exactly (±0)** on
both modules tested. It also refuses by name rather than measuring nothing: five
kind-already-absent cases, a renamed rebinding target, a partial writer set, and a
constructor that has stopped reading the global, all proved against mutated trees by
`scratchpad/card338/prove_refusals.py`.

**Trap 1 is not a trap, and that is a correction this card inherits.** By `ast`, **three** modules reference `_RASTER_DECLARATIONS` with **17**
`monkeypatch.delitem` sites; **2** pass `raising=False` and **15** can raise; of those 15,
**two** name `DIVIDER`, which the five-kind probe does not lift — leaving **13 sites that
can raise** (`scratchpad/card338/derive_delitem_sites.py`). **Separately measured, the
census counts 13 reds** from them: `property/test_book_export_interior.py` **5**,
`test_book_interior_type_floor.py` **1**, `test_book_pdf.py` **7**. **Those are two
different quantities and neither is derived from the other** — one literal site produces 5
reds by itself, and two of the 15 (`test_book_pdf.py:3747`, `:3774`) are `delitem` calls
inside `for kind in self._interior_kinds()` loops covering 4+ kinds each, printed as
`LOOP:kind` by the derivation because `ast` cannot know the kind. Their agreeing on 13 is a
coincidence of this tree; quote each from its own instrument. (The re-cut's original
"≤13 artefact cap" had no stated step at all: 17 − 2 = **15**, not 13.) The two `raising=False` sites are
`tests/test_book_pdf.py:5670` and `:5794`. The share of the **+74** these reds account for
is **+11**, not +13, because `test_book_pdf.py` already carries one of them PUZZLE-only.
**And they are not the instrument's shadow.** CARD-338 measured the identical `KeyError`
count on the E1 tree — five entries deleted in `src/`, no probe loaded at all — so these
are reds the **conversion** produces and owns. Two of the three colliding modules are in
this card's `Touches`; price them as work, not as noise.

**Trap 2 — the scale, re-derived 2026-11-03 at `f407c350`.** Over CARD-329's 20 modules the
five-kind probe reads **18/20 red, 225 failed+error, 1150 passed, 1 skipped** against the
PUZZLE-only probe's **17/20, 151, 1224, 1**; the one skip is the `setrlimit(RLIMIT_AS)`
platform gate at `tests/test_book_pdf_memory.py:1297`, attributed from `-rfs`, and neither
database gate fired. **Population B is unchanged module for module** (`pairing` 1→1,
`pdf_geometry` 4→4, `cell_size` 0→0, `difficulty_dots` 29→29, `divider_pages_option` 3→3,
`pdf_levels` 4→4, `pdf_two_up` 4→4, `puzzle_frame` 4→4), so the whole +74 is in population
A. **Seven** population-A modules with no `delitem` site move, and their deltas sum to
**+61** — the figure this card carried, with one correction: it is seven modules, not six
(ten population-A modules have no `delitem` site at all; seven of them moved).

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
green under the probe, and it is red at 2 under the real end state.** Re-derived by
CARD-338 and confirmed to the digit. That is the clearest statement available of what the
PUZZLE-only probe cannot see, and it is why this card verifies under the five-kind probe
and not CARD-329's.

**The third population, and the number this card inherits for it.**
`tests/test_book_interior_type_floor.py` is in neither of CARD-329's populations;
`scratchpad/card338/derive_medium_population.py` **derives** it rather than listing it — the
filter is a module whose AST names the medium decision itself (`page_medium`, `PageMedium`,
`_RASTER_DECLARATIONS`), four modules name it and this is the one outside the census — and
the derivation reds when a module that should be in that population is not. It reads **3**
under the PUZZLE-only probe and **8** under five kinds. **So the end-state residue over the
21 modules is 233, not the 228 that was carried here**: the 228 added this module's
PUZZLE-only 3 to the five-kind 225.

**All 233 reds carry a mechanism and an owner, with no "other" group**
(`scratchpad/card338/classify_reds.py`, which exits non-zero on an unmatched cause rather
than bucketing it). The two largest families this card owns are the medium-blind read that
returns empty (**64**) and the pixel oracle handed a `ContentStream` (**38** through
`tests/helpers/page_ink.py`, **23** in the test modules themselves, **27** in CARD-331's
module, **2** through `tests/helpers/two_up_ink.py`); the reader seam proper is **11**
unprotected `KeyError: b'XObject'` plus **2** of CARD-329's named `PageMediumRefused`.
**One caution about the instrument:** `-rfs` leaves ERRORs out of the short summary and
`--tb=line` prints them in another shape, so a census that reads only `--tb=line` saw 210
of the 233. The missing 23 are fixture-raised ERRORs (`pdf_band` 10, `pdf_memory` 13),
resolved with `-rEfs` and all of mechanisms already named. Use `-rEfs`.

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

> **[RESTATED 2026-11-04 for the re-cut scope, on the owner's instruction — and the provenance
> matters, so read it before the criteria.]**
>
> **These were written AFTER the implementation round ran**, because the re-cut shrank the card
> from thirteen modules to one and nobody restated its criteria at the time. **So they are not
> what that round was aiming at**, and a reader judging it against them should know that. They
> are derived from the **re-cut's own scope statement** — one module, its 10 reds, and the
> ADR-0042/R6 question — and not from the round's report; writing criteria out of a report is
> grading the homework that produced it.
>
> **The superseded set is preserved verbatim below**, because it is the record of what the
> thirteen-module card required and of where each of its clauses went. **Every clause of the old
> AC-1, AC-2 and AC-3 is now owned by another card** — CARD-354 … CARD-360 by module, plus
> CARD-322, CARD-343 and CARD-352 by mechanism — so nothing in it was dropped, only re-homed.

- **AC-1** (the module's reds are closed, with a route stated per claim): *Given* a run under
  CARD-338's five-kind probe, *then* `tests/test_book_pdf_ink_mode.py` carries **zero** reds, the
  count is stated **before and after**, and **each affected claim names its ADR-0042/R6 route** —
  re-expressed against the content stream, or retired with a named survivor — **with the
  measurement that chose it.** A module left green because the probe does not reach it is not
  repaired, and saying so is the AC.
  (test: the module by node id, under the probe, with `-o addopts=` as two argv items)
- **AC-2** (the medium split is measured, not assumed): *Given* the interior, *then* the
  **per-page** raster/vector split is derived at runtime from the file rather than inferred from
  `_RASTER_DECLARATIONS` alone, and a page the reader cannot classify is a **FAILURE**
  (ADR-0039/R2). **This is the AC the re-cut most needed and did not have:** the orchestrator's
  brief asserted that a vector page declares no colour space *and therefore the claim has no
  subject*, which is true per page and **false of the interior**, because at least one interior
  kind is still declared raster. A card that accepted the brief would have retired a claim with a
  live subject.
  (test: named by the implementation; state it)
- **AC-3** (a re-expression is not weaker than what it replaces): *Given* each claim taken by
  route 1, *then* the card states **what it asserted before and what it asserts now**, and shows
  the new form is **at least as strong** — a re-expression that admits something the old form
  caught is a weakening and a finding against the card.
  **(check: review-lens)** — *corrected 2026-11-04: this clause was labelled `(test: …)`, which
  reads to the next reader as mechanically checked. It is a judgement over two forms of a claim
  and there is no test that decides it. The board's own "ADR check refs must be honest" rule
  applies to my own acceptance criteria, which is where it had not been applied.*

  Where the new form rests on a **forbidden set**, that set is **derived from an authority the
  runtime can enumerate** — **or**, where no such authority exists, it is an **ADR-0039/R3 named
  exemption**: the external authority is named, its **completeness** is stated, and **each member
  is shown able to fail**.
  *Corrected 2026-11-04, and this is a finding against my own wording rather than against the
  round.* The clause previously read "derived and not hand-listed (ADR-0039/R2)", unconditionally
  — but R2 conditions it: *"Where no such authority exists, the guard defaults to deny … named
  exemptions under ADR-0039/R3."* A forbidden set drawn from a **file-format specification** has
  no runtime-enumerable authority, and deriving it from the writer under test would be circular —
  it would make the very operator a plant emits part of the permitted vocabulary and therefore
  not forbidden. So AC-3 as I wrote it forced either a false claim of derivation or an
  unachievable implementation. **The honest form is an R3 exemption**, and a set that satisfies
  it is satisfying this AC.
  (check: review-lens, plus the per-member failability each exemption must demonstrate)
- **AC-4** (a retirement has a survivor that can fail): *Given* each claim taken by route 2,
  *then* its survivor is **named and asserted** — not commented — and **a plant that empties the
  surviving arm makes the module RED**, demonstrated. **A retirement whose survivor cannot fail is
  a deletion**, and this AC is the only thing separating the two.
  (test: named by the implementation; state it)
- **AC-5** (the repair holds in both media): *Given* the module, *then* it is green **under the
  five-kind probe AND on the committed raster tree**, both stated. A repair green in one medium is
  the defect ADR-0042/R6 exists to prevent.
  (test: the module, both ways)
- **AC-6** (the change can fail, and the post-repair census is re-run): *Given* the repair, *then*
  **at least one plant per route**, each killed, each with its matched control measured green **in
  the same run** and `0 skipped` asserted; any plant into `src/` restored **byte-identically**
  with the SHA-256 pair shown. **And the module is re-censused AFTER the repair** — `pdf_band`
  gained three byte-identity reds only once its seam was planted, so a pre-repair census is not a
  statement about the post-repair tree.
  (evidence: the plant table in `## Worktree notes`)
- **AC-7** (the measurement is the instrument's): *Given* the five-kind probe, *then* every skip
  is attributed **by name from `-rEfs` as ONE flag** — two database gates coexist here, `-rf -rs`
  as two flags silences the first, and **`-rfs` omits ERRORs**, which matters because a large
  share of this family's reds are fixture-raised. A figure read off a brief rather than off a run
  is the defect this board has now hit six times.
  (evidence: the run output)

### Superseded set — the thirteen-module card's criteria, preserved

- **[SUPERSEDED] AC-1** (the nine are repaired, with a disposition each): *Given* a run under
  CARD-338's five-kind probe (`scratchpad/card338/probe_five_kinds.py`), *then* each of
  the nine routed modules passes, and the card
  states **per module** which of three dispositions it took and why — the seam sufficed,
  the module needed more, or a claim was retired with a named survivor. **A module left
  green only because the probe does not reach it is not repaired, and saying so is the
  AC.** (test: the nine modules by node id, under the probe, with `-o addopts=''`)
- **[SUPERSEDED] AC-2** (the four non-seam mechanisms each have a stated disposition): *Given* the
  branch, *then* `test_book_pdf_levels.py`'s and `test_book_pdf_two_up.py`'s
  byte-identity survivors, `test_book_arrange_page_breaks.py`'s segmentation red and
  `test_book_interior_type_floor.py`'s three each carry a disposition naming the
  mechanism, not a repair naming the symptom. **The byte-identity half additionally
  states how its expectation stays independent of the writer under test.**
- **[SUPERSEDED] AC-3** (the populations are derived and total, including the one the census missed):
  *Given* `tests/**`, *then* populations A, B and **C** (the medium-decision references)
  are derived by `ast` with their filters stated in one sentence each, nothing is
  unclassified (ADR-0039/R2), and **every module of the union is green under the
  five-kind probe except the ones another card owns by name** — `tests/test_book_pdf.py`
  (CARD-322's registry assertions and CARD-336's placed-edge family),
  `tests/property/test_book_pdf_geometry.py` and `tests/test_book_puzzle_frame.py`
  (CARD-336), `tests/test_book_difficulty_dots.py` (CARD-322's arm re-point),
  `tests/test_book_guide_page.py` (CARD-336). Each exclusion is **named with its owner**,
  not left as a residue.
- **[SUPERSEDED] AC-4** (the measurement is the instrument's, and the instrument is controlled):
  *Given* the five-kind probe, *then* the round records the red count before and after,
  **every skip attributed by name from `-rfs` as ONE flag** (two database gates coexist
  here and `-rf -rs` as two flags silences the first), and the probe's own
  `monkeypatch.delitem` collision is separated from genuine reds with the separation
  shown — **and the separation now has a measured answer to start from: those 13 reds are
  the conversion's, not the probe's** (CARD-338 measured them identical on a tree with the
  five entries deleted in `src/` and no probe loaded). A figure read off the brief rather than off a run is the defect this board has
  hit five times.
- **[SUPERSEDED] AC-5** (the change can fail): **one plant per repaired module**, each re-breaking that
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
  the probe harness **already built and committed by CARD-338**
  (`scratchpad/card338/`) rather than merely designed, and the seam shape already proven. The nine seams are the cheap two-thirds; the four mechanisms are the
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
  would measure it:** done by CARD-338 — `scratchpad/card338/classify_reds.py` groups all
  233 reds by message into named mechanisms with no "other" bucket. **The expected-side
  family is 1 red, not a fourth mechanism**, and its site is
  `tests/property/test_book_export_interior.py:546`, whose expected side looks for a
  `BookPDFGenerator.vector_guide_page` **method** that CARD-309 never created (it injects
  the writer as `self.pages.guide`). The large families are the medium-blind empty read
  (64) and the pixel oracle handed a `ContentStream` (90 across four sites).
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

### Merge gate, 2026-11-04 — review cycle 1 record and the plant table AC-6 names

[Review 1/3] Score: 8.5 — CERTIFIED on cycle 1 of a 3-cycle budget. 0 critical, 3 important (F-001 main moved during the cycle and carried a new artefact-census guard with it; F-002 the "derived" forbidden set is really an ADR-0039/R3 named exemption; F-003 three refusal arms asserted and never demonstrated, carded as CARD-365), 4 minor (F-004 a plural where the margin is 1 of 14; F-005 a byte count in prose the cells never assert; F-006 dead code in an instrument; F-007 the round's suite figure predates main's movement) — F-001/F-002/F-004/F-005/F-006/F-007 all dispositioned at this gate, F-003 carded.
Review artefact: meta/review/CARD-337-cycle1.yml.

**AC-6's plant table, transcribed here because this is the location AC-6 names and it was empty.**
The round ran the six plants and the **reviewer independently re-planted all six**; the record
lived only in the review YAML, which main's `.gitignore` now keeps untracked, so an AC whose
stated evidence is "the plant table in `## Worktree notes`" had no evidence at its stated
address. Figures are the reviewer's re-planted run, not the round's self-report.

Method: `scratchpad/card337/mutation_runs.py`, all six keys, `PYTHONDONTWRITEBYTECODE=1`,
`__pycache__` swept both ends, `occurrence` asserted `== 1`, SHA-256 both ends, restore from
captured content, `-o addopts=` as two argv items, `-rEfs` as ONE flag, `0 skipped` asserted,
and the matched control measured green **in the same run**. `git status --porcelain` empty
afterwards.

| plant | what it breaks | outcome |
|---|---|---|
| **MUT-1** | the medium gate in `pdf_page_declarations` | **KILLED** — 9 failed / 43 passed; 3 cover controls green |
| **MUT-2** | the raster-write ordinal translation | **KILLED** — 1 failed / 51 passed, only the write-ordinal cell; 3 file-reading controls green |
| **MUT-3** | `ContentStream.fill_grey` emits `rg` instead of `g` | **KILLED, and the decisive one** — 6 cells red across 5 functions, 46 passed, while `test_no_mark_moves_on_any_page_bitmap`, the module's ONLY bitmap-side reading, stayed **green in the same run**. A real DeviceRGB regression on a vector page, invisible to every XObject reading and caught only by the re-expressed operator claim — so route 1 is a re-expression, not decoration |
| **MUT-4** | a vector page's stream becomes export-dependent | **KILLED** — 1 failed (the baseline-pair cell), the EC-1 cell green |
| **MUT-4b** | the same defect on every second render | **KILLED** — 1 failed (the EC-1 cell), the baseline-pair cell green. Each variant reaches a cell the other cannot |
| **MUT-5** | `DIVIDER` stops being a declared bitmap, emptying the raster arm | **KILLED** — 4 failed + **7 errors**, 41 passed. The module fails LOUDLY rather than passing vacuously, so the retirement's survivor can fail: a disposition, not a deletion (AC-4) |

Every row totals **52**, the module's case count (9+43, 1+51, 6+46, 1+51, 1+51, 4+7+41) — an
internal cross-check that each plant's run saw the whole module and not a subset.
**`src/` restored byte-identically after every plant:** `book_vector.py`
`686dd387…1b20` and `book_pdf_generator.py` `691d1952…1b24`, identical before and after
(G-1), re-verified at this gate as `git diff --name-only <main>...HEAD -- src/` empty.
