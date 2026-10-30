# CARD-309: The assembly point, and the puzzle page becomes operators — the half of the conversion that is architecture rather than repetition

**Status:** review
**Priority:** P2
**Category:** enabler
**Estimate:** 1.5d <!-- unchanged. The card was re-cut at the decompose station on 2026-10-30 rather than re-estimated: the work it NOW claims (the assembly point) is what it actually did, and it came in at roughly this. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/309-assembly-point-and-puzzle-operators`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-309
**Source:** CARD-298's review cycle 1, F-002, 2026-10-29 — which measured that **no card on the board converts the interior pages at all**. Cut by the orchestrator on owner decision the same day. The work is what CARD-298 was originally cut to do, minus the mechanism CARD-298 kept.
**Idea:** —
**Wave:** 69 <!-- RE-STAMPED 2026-10-30 at dispatch, 68 -> 69. The field records the wave a card RAN in, and this card never ran in 68: wave 68 closed with CARD-220 (`cb5856dc`) and CARD-314 (`8762beed`) merged while this card sat `ready`. Leaving the old stamp is what made the board read waves 67 and 68 as unclosed. Dispatched with CARD-268; measured Touches intersection with it is EMPTY (overlap 0.0), and the one hotspot this card touches (`book_pdf_generator.py`) is not in CARD-268's set, so no conflict edge. -->
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-299, CARD-306, CARD-314 <!-- all done; unchanged by the re-cut -->
**Split into:** CARD-309 (this card: the assembly point + the puzzle page) and **CARD-322** (the remaining four kinds, R1's flip, CARD-297's divergence)
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_interior_vector.py, tests/test_book_pdf.py, tests/test_book_export_interior_cover.py <!-- NARROWED 2026-10-30 at the decompose station. The four vector writers and tests/fixtures/book_baseline_*.json are OUT: no kind converts here, so no baseline moves. book_interior_vector.py is IN and is new. -->
**Review score:** cycle 1 **7.5 — does NOT certify** (2 open important, 0 critical) → **fix round 1 running**. The verdict is unusual and worth keeping: **the architecture is right and was proved right** — no cycle anywhere, `tests/test_cli.py` 0 times in the diff and 135 passing, `_write_pdf` byte-identical to main, the refusal unbypassable, all seven guardrails measured passing, the three frozen figures re-derived from the rows, and the byte figures reproducing **exactly** (4,786,226 / 607,106 B, 7.9×). **Every defect is in the RECORD**, residue of reverting the conversion and then being rebased without re-deriving the prose. **F-001 ships in `src/`:** the `_RASTER_DECLARATIONS` docstring says *'one fewer since CARD-309'* and *'CARD-309 removed one entry'* — it removed **none** (7 entries at HEAD, 0 removed by the diff, re-derived by the orchestrator) — and the same sentence **invokes CARD-261's drift precedent as its justification while committing that drift**, on the one thing the comment calls *'the one honest reading of how far ADR-0042/R1 has actually got'*. **F-002 was a routing hole, now fixed on `main` by the orchestrator:** CARD-322 had **zero** mentions of the F-307 rename it was owed and its G-5 carried the same unqualified prohibition CARD-309 had just declined under — declining was right, the routing failed, and CARD-322 now carries a **named G-5 exception** granted at the decompose station.
**Started:** 2026-10-30T11:58:28Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**It was the hole in the board's own graph.** ADR-0042/R1 says puzzle pages, answer
pages, the TOC and the guide **are** written as content-stream operators. Four
cards built the writers — CARD-295/296/297 and CARD-294's vocabulary — and every
one of them still has **zero real call sites in `src/`**. CARD-298 was the wiring
card until its review narrowed it to the mechanism, and CARD-299 is test-side only:
measured, its `Touches` names six test modules plus `requirements.yml` and the ADR,
**not one file under `src/`**.

So as of 2026-10-29 the phase had: a medium decision point, five vector writers, a
set of readers about to be converted, a declaration registry — and **nobody who
turns a single page into operators.** CARD-298's cycle 1 found it by asking who
discharges five `expires_with` entries, and the answer was nobody.

This card is that work, and the five declarations CARD-298 ships name **this card**
as the one that removes them.

## [SPLIT 2026-10-30, on owner decision] This card is now the first half

**Why it was split.** The card was estimated **1d** and contained: an assembly point that **does not
exist**, five kind conversions, 21 baselines, ADR-0042/R1's flip, CARD-297's clip divergence, and a
reader population measured at **12 modules plus 8 more its own AC-3 cannot see**. CARD-308 had the
same shape today — architectural, with a frozen artefact to move — and came in at **3.0×**.

**The split follows the card's own design rather than overriding it.** Its item 1 already said *"one
kind at a time, each removal complete… that refusal is the mechanism CARD-298 built and it is what
makes this card incremental rather than all-or-nothing."* The seam was already there.

**This card takes the architecture; CARD-322 takes the repetition.** The puzzle page is the only
writer the interior's walk can already reach, and both of its prerequisites have landed —
**CARD-306** gave it its sheet furniture, so it no longer ships pages with no folio, and **CARD-314**
marked its clue digits so CON-020 stays verifiable by the mark rather than by the size.

### THE CONSTRAINT THAT SHAPES THIS CARD — read before planning

`tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it` is **live**, and its
own docstring says it is *"the cell that reds **the day CARD-309 is marked done**"* if its
declarations remain. **All five kinds currently name CARD-309 in `expires_with`** — measured:
TITLE, GUIDE, TOC, ANSWER and PUZZLE each carry `('CARD-299', 'CARD-309')`.

**So this card cannot be marked done while four of those declarations still name it.** That is a
**shipped-code obligation, not card bookkeeping**, and it is this card's to pay:

- **remove PUZZLE's declaration** (its kind converts here), and
- **re-point TITLE, GUIDE, TOC and ANSWER to `('CARD-299', 'CARD-322')`**, with a comment saying the
  conversion was split and why.

**Get this wrong and the merge gate finds it, not the review** — that guard is outside this card's
impact radius, exactly like the two frozen registries that reddened CARD-314's and CARD-269's gates
within one hour today.

## [RE-CUT 2026-10-30 at the decompose station] This card is now the assembly point, and nothing else

**It escalated with `[BLOCKER] decomposition defect` and this is the re-cut.** The
implementation round built the assembly point, measured why the puzzle-page
conversion cannot land with it, and **reverted the conversion rather than absorbing
it** — which is the behaviour the pipeline wants and the reason this re-cut is cheap.

**What this card now claims** (all of it already implemented and green on the branch,
commits `9fc8651f` and `37e1a093`):

- `src/nonogram/admin/book_interior_vector.py` — the assembly point, downstream of
  all five writers. The direction is a **parameter** (`InteriorPageWriters`, frozen,
  four callables) rather than a registry or a lazy import, injected on the generator
  and read once in `__init__`, so three export doors are one walk.
- PUZZLE's declaration **stays**, and all five interior declarations are re-pointed
  to `("CARD-299", "CARD-322")` — so no declaration names this card and
  `test_no_declaration_outlives_the_cards_that_remove_it` is green on the day it is
  marked done.
- `_write_pdf`'s representation refusal untouched, plus a `_drawn_downstream` refusal
  by kind one step before it (default-DENY, naming the assembly point).
- **ADR-0042/R1 is NOT flipped.** It is true only when all four remaining kinds are
  operators too. CARD-298 and CARD-299 each refused this flip on their own initiative
  and were each right; so does this card. R1's flip is **CARD-322's**, with the last
  conversion.

**What left this card, and where it went.** The round root-caused the conversion's
**189 failures + 75 errors across 22 modules** into four causes, and only one was a
PDF reader:

| cause | now owned by |
|---|---|
| 1. `tests/helpers/pdf_pages.py`'s one-image reader (`KeyError: b'XObject'`) — the only actual reader | **CARD-329** |
| 2. `tests/helpers/page_ink.py`'s independent pixel oracles, and the 0.169 mm the two media disagree by against `EDGE_TOLERANCE_MM = 0.1` | **CARD-330** |
| 3. `tests/test_book_difficulty_dots.py` + `tests/helpers/round_ink.py` (27 cells) — monkeypatches the raster drawing site, so on a vector page it measures a page the product no longer draws. **Was carded nowhere.** | **CARD-331** |
| 4. frozen AST censuses in `tests/test_book_export_interior_cover.py` | re-derived on this branch; **stays here** |
| the conversion itself, the four remaining kinds, the 21 baselines, R1's flip | **CARD-322** |

**One routing the round got wrong, corrected here.** It assigned cause 2's convention
question to CARD-312. Measured 2026-10-30: CARD-312's text mentions no tolerance, no
offset and no `page_ink` site — it owns *whether a site must convert*, not *what a
placed-edge expectation means when both media are legal and disagree*. That question
was **unowned**, which is why CARD-330 exists. CARD-330 also reframes it: 2 px at
300 dpi is 0.1693 mm and 300 dpi is the interior's own render DPI, so the gap is
exactly one rounding step and the two values are **a quantisation of one**, not two
opinions — making the first question "which medium is at the specified margin?"

### The honest statement of what this card does NOT achieve

**Nothing in `src/` imports the assembly point, so it ships with zero production call
sites** — verbatim the condition this card was cut to end (*"four cards built the
writers and every one still has zero real call sites in `src/`"*). The conversion
would have been that call site, and the conversion is CARD-322's now. So the phase's
hole — *nobody who turns a page into operators* — **is still open after this card
merges**, and this card is the fifth artefact waiting for a caller.

That is recorded because it is true, not because the work was wrong: the blocker is
real, well measured, and the alternative was to grow the card past its own scope gate.
**CARD-322 is now the card that closes the phase**, and it inherits a built assembly
point whichever order the rest lands in.

## What to implement

1. **Build the assembly point. This is the card.** `book_guide_vector`, `book_toc_vector` and
   `book_answer_vector` **all import `book_pdf_generator` at module level**, while
   `book_pdf_generator` imports `book_puzzle_vector`. So the interior's page walk can call the puzzle
   writer and **cannot call the other three without a cycle**. Three of five kinds need an assembly
   point **downstream of all of them, and it does not exist.** **Design it, do not work around it** —
   an import-direction violation is a structural guard failure in `tests/test_cli.py`, not a style
   question. **CARD-306 already built `book_sheet_vector.py` kind-agnostic for all five kinds**, with
   an import set asserted by set equality precisely to avoid this cycle; the furniture is ready and
   the assembly point is what is missing.
2. **Convert the puzzle page**, delete PUZZLE's entry from `_RASTER_DECLARATIONS`, and let
   `_write_pdf`'s representation refusal prove the removal is complete — a kind whose declaration is
   gone but whose page is still a bitmap is **refused, not shipped**.
3. **Re-point the other four declarations to CARD-322** (see the constraint above).
4. **Do NOT flip ADR-0042/R1.** R1 is true only when all four remaining kinds are operators too.
   CARD-298 and CARD-299 each refused this flip on their own initiative and were each right; so must
   this card. **R1's flip is CARD-322's, with the last conversion.**
5. **The readers the puzzle page's conversion reaches.** AC-3's twelve are derived from the import of
   the one-image reader; **eight further modules reach the same hazard through
   `.interior()`/`.interior_pages()`** and are invisible to that derivation — see the section below.
   **Derive which of both populations this kind's conversion actually breaks**, per module, and fix
   those. Per ADR-0039/R2 a module the walk cannot classify is a **FAILURE**, not a silent pass.
6. **The baselines this kind moves, enumerated.** Puzzle pages are most of a book, so most of the 21
   move here. **List them file by file** so a reviewer can count them without running anything, and
   record the interior's size and generation time at both ends.

## Acceptance criteria

> **RE-CUT 2026-10-30.** AC-1 holds in its second half only (the declarations are
> honest and name CARD-322; PUZZLE's entry **stays**). **AC-3 is CARD-329's** and
> is not verified here. AC-4's count is **zero** — no kind converted, so no baseline
> moved, and `git status tests/fixtures/` is empty. **AC-5 is this card's core** and
> passed with the guard unmodified. AC-2 and AC-6 hold as written. Read the
> re-cut section above before judging any of them.

- **AC-1** (the puzzle page is operators, and the declarations are honest): *Given* a written
  interior, *then* **no puzzle page references an image XObject**, PUZZLE's entry is **gone** from
  `_RASTER_DECLARATIONS`, and the four remaining entries **name CARD-322**, not this card — so
  `test_no_declaration_outlives_the_cards_that_remove_it` is green on the day this card is marked
  done. **R1's flip is NOT this card's** (see item 4).
- **AC-2** (each removal is complete, proved by refusal): *Given* a kind whose
  declaration is removed, *then* a bitmap handed in for that kind is **refused by
  the writer**. (**Two mutants per ADR-0039/R1**, one inside the region and one at
  the edge: the last kind converted, and a kind converted while its declaration is
  left behind.)
- **AC-3** (the readers survive): *Given* the converted interior, *then* every test
  module that reads a book interior passes — the **12 test modules** that import
  `tests/helpers/pdf_pages.py`'s one-image reader. <!-- CORRECTED 2026-10-29 by
  CARD-299's fix round: this said "14 modules plus 3 helpers", which was the
  orchestrator's figure and does not reproduce. Measured: 18 files MENTION the
  string, 14 import something from the helper, and only 12 import the one-image
  reader itself -- `tests/helpers/book_corpus.py` imports only `pdf_page_count`
  (which asserts nothing about images), `tests/test_book_toc.py` only `same_page`,
  and `tests/property/test_book_pdf_geometry.py` imports it ZERO times, matching a
  grep only because THREE OF ITS NODE IDS END IN `_pdf_pages`. A mention count is
  not a reader count. --> A module that needs a further edit here is a **finding about
  CARD-299's completeness**, to be raised, not absorbed.
  <!-- AC-3's DERIVATION HAS A BLIND SPOT, measured 2026-10-30 — see the section
  "AC-3 counts readers by an import name" below. The twelve are derived from the
  IMPORT of the one-image reader, and EIGHT further modules reach the same hazard
  by a different route: they call `.interior()`/`.interior_pages()` and use the
  returned pages as images. They are invisible to this AC as written. Read AC-3 as
  covering both populations. -->
- **AC-4** (the baselines move once, enumerated): *Given* the branch, *then* the
  re-recorded baselines are listed file by file in the card, the count is stated,
  and **CON-019's property test and the A4 golden are untouched and green**.
- **AC-5** (the assembly point is real architecture, not a workaround): *Given* the branch, *then*
  the three downstream writers are reachable from the interior's page walk **with no import-direction
  violation** — asserted by `tests/test_cli.py`'s structural guard, which must pass **unmodified**.
  A card that edits that guard to accept its own layering has removed the thing that was checking it.
- **AC-6** (an owner render exists): *Given* the converted interior, *then* a
  rendered interior is produced under `~/Documents/nonogram-reviews/CARD-309/`.
  **Standing rule: image-pipeline changes need a rendered eyeball, not just green
  tests** — and this card changes every interior page.

## Engineering constraints

- **EC(ADR-0042/R1):** across a seeded corpus spanning page counts, trims and tier
  mixes, no interior page of a converted kind carries an image XObject, with a
  minimum case count asserted inside the test.
- **EC(ADR-0042/R2):** across the same corpus, the set of raster pages equals the
  set of declared raster pages — neither direction slack — and that set shrinks to
  the cover plus the divider.

## Guardrails

- **G-1: do not convert the cover.** Its declaration is permanent (`expires_with:
  ()`); a photograph is correctly raster.
- **G-2: do not convert the divider.** It is CARD-231's, by the owner's 2026-10-25
  decision that the new design should be born vector rather than the old one
  converted.
- **G-3: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  or the A4 golden.** Neither is a book interior. If either reds, that is a
  **finding to raise**, not a baseline to refresh.
- **G-4: do not lower a corpus minimum**, and regenerate nothing under
  `tests/fixtures/**` beyond the baselines item 4 enumerates.
- **G-5: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-6: do not weaken `_write_pdf`'s representation refusal to let a conversion
  land.** It is the thing that makes a partial conversion safe; a card that
  loosens it to get green has removed its own safety net.
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators (check: review-lens → **this card flips it**, and only with the last conversion)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard, plus the landing-direction half CARD-298's fix round 1 adds)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0036/R1 — the A4 golden's byte identity for the no-PageSpec default path (check: the A4 golden)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- CON-020 — the 10 pt interior type floor (check: CARD-299's re-expressed test)
- INV-013 — the interior holds no cover page; parity counts from interior page 1
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; a guard's set is derived and an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **DEAD REF** — zero definitions in this repo; verify the substance, see CARD-307)

## Architecture context

- **FR:** FR-030, FR-032, FR-033, FR-040, FR-041, FR-042, FR-043
- **NFR:** NFR-008
- **ADR:** **ADR-0042** (R1 flips here; R2's set shrinks), ADR-0036/R1-R2, ADR-0037/R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** `trace.yml` carries **no ADR-0042 rule rows at all** — measured 2026-10-29, only two prose mentions at `:1813` and `:1853`. So no rule row is re-stamped here; the FR rows whose tests move are. Do not write a Trace line promising to re-stamp a row that does not exist, which is the mistake CARD-298 inherited.

## Worktree notes

- **[Escalated]** 2026-10-30T13:08:14Z — `[BLOCKER]` decomposition defect: AC-1's conversion
  reds 189 failures + 75 errors across 22 modules, four causes, only one of them
  AC-3's subject · station: **decompose** · route: `/forge:kanban decompose`
  CARD-309, or an owner narrowing to the delivered half (the CARD-298 / CARD-218
  precedent). **Worktree and branch kept** — there is real, green, unmerged work
  on the branch.

- **[Orchestrator verification, 2026-10-30T13:08:14Z]** The implementation's
  structural claims were re-derived independently rather than taken from its
  report, because this card's whole subject is an import direction:
  - `tests/test_cli.py` is in the diff **zero** times — AC-5's core claim holds.
  - An `ast` walk over every `src/nonogram/admin/book_*.py` on the branch finds
    **no cycle anywhere** in the `book_*` graph. `book_interior_vector` imports
    `book_answer_vector`, `book_guide_vector`, `book_toc_vector`,
    `book_pdf_generator` and `book_vector` — genuinely downstream of all of
    them — and `book_pdf_generator` names it only in comments, never in an
    `import`. The direction is right.
  - **AND THAT IS ALSO THE CARD'S OWN COMPLAINT, NOW TRUE OF ITS OWN
    ARTEFACT.** Nothing in `src/` imports `book_interior_vector`, so it has
    **zero production call sites** — which is verbatim the condition this card
    was cut to end ("four cards built the writers and every one still has zero
    real call sites in `src/`"). The conversion would have been that call site,
    and the conversion was reverted. So the phase's actual hole — *nobody who
    turns a page into operators* — **is still open**, and the artefact that was
    supposed to close it is now the fifth thing waiting for a caller. This is
    not a defect in the implementation (the blocker is real and well measured);
    it is the fact the owner's narrow-or-re-cut decision turns on, and it is
    recorded here because a report that says "the assembly point is done" is
    true and, on its own, misleading.
  - Not verified by the orchestrator, and left for the review station: the
    0.169 mm figure, the 189/75 census, the four-cause root-cause split, the
    reader populations (12 and 9), and the 7.9×/3.6× size and time figures.

- **[scratchpad committed to the branch — a review question, flagged not fixed]**
  The branch commits ten probe scripts under `scratchpad/card309/`. The brief
  asked for the harness to live there (not at the shared scratchpad root, which
  is CARD-284's measured defect), and it does. Whether those files should reach
  `main` is a separate question the review or the narrowing decision should
  settle — the evidence they carry is worth keeping somewhere, and `main` may
  not be that somewhere.

- **[Env]** forge `2026.8.17` (executing manifest `forge_1/forge/.claude-plugin/plugin.json`).
  The project declares no `meta/.skills.yml`, so there is no `forge.min_version` to compare
  against and no `models:` block — the implementation agent inherits the session model rather
  than resolving a class. Recorded because a later diagnosis needs the version the procedures
  came from, not because a gate fired.

- **This card finishes a phase that has been built backwards**, and that is worth
  knowing rather than rediscovering: the writers came first (CARD-294/295/296/297),
  the mechanism second (CARD-298), the readers third (CARD-299), the furniture
  fourth (CARD-306), and the wiring — the only part a reader of a shipped book can
  see — last. Nothing shipped to a reader across the whole phase until this card.
- **The incremental path exists only because CARD-298's refusal is default-DENY.**
  Without it, converting one kind would mean converting all five in one commit to
  keep the suite green. Do not trade that away for convenience (G-6).

## [Added 2026-10-29 after CARD-298's review cycle 2 — five declarations name this card, and a cell reds the day it closes]

Review cycle 2's amendment 3: this card's body never mentioned
`_RASTER_DECLARATIONS`, yet **five of ADR-0042/R2's raster declarations name
CARD-309 in their `expires_with`** — TITLE, GUIDE, TOC, ANSWER and PUZZLE, each
paired with CARD-299.

**So there is a test that reds the day this card is marked `done`.**
`tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it`
walks the board's card files and fails when **every** card named in an entry's
`expires_with` has reached `done` while the entry is still present. CARD-299 and
CARD-309 are the pair; the cell fires when the **last** of them closes.

Two consequences for this card's round, neither optional:

1. **Removing a kind's declaration is part of converting it, not a follow-up.**
   Item 1 already says each removal must be complete; this is the mechanical
   consequence — close this card with any of the five entries still in the registry
   and that cell reds on `main`. The paired refusal in `_write_pdf` is what makes
   the removal safe to do one kind at a time.
2. **If this card converts only some kinds, it must not be marked `done`** — or it
   must re-point the surviving entries at whatever card finishes the job, in the
   same commit. Say which, explicitly. An `expires_with` is a claim about who
   removes the exception, and cycle 1 of CARD-298 was gated for getting exactly
   that claim wrong.

**And one thing this card inherits rather than discovers.** The landing check's
verdict is a function of the **main working tree's** card directory, not of a
commit (CARD-298's F2-001, measured: imposing ordinary-checkout semantics reds it
with *"Left contains one more item: 'CARD-309'"*). That is a false RED and never a
false green, and CARD-298 states the bound honestly in the docstring. **The
direction worth taking — hoisting the check into the board's own gate, where the
board is the subject rather than a neighbour — is NOT this card's**, and a
conditional skip would be an ungated door. **It is now carded as CARD-310**, which
also decides the general pattern: a card's *name* is a structural fact that may be
walked from `tests/`, a card's *status* is a board-time fact that may not. Raise
anything CARD-310 has not covered rather than absorbing it.

## [CARD-314 is a PREREQUISITE for the puzzle page, added 2026-10-29]

CARD-299's round measured the thing that makes this ordering non-negotiable. On a
real vector puzzle page written by `BookPDFGenerator.vector_puzzle_page`:

```
Tf operators: 205     distinct sizes (pt): [8.64, 14.16]     below the 10 pt floor: [8.64]
```

**The 8.64 pt faces are exactly the ones CON-020 exempts — and a content stream
records no provenance.** CON-020's exemption is keyed on the *drawing function*
(`_draw_clues` / `_write_clues`), so a stream-read floor cannot tell an exempt clue
digit from body type. CARD-299's guard therefore **refuses a vector puzzle page by
name**, which is correct and is a hole with a date on it: **the day this card
converts the puzzle page, CON-020 has no verifying reading for it.**

That is worse than a warning. **CON-020 is a `status: covered` row in `trace.yml`
whose `tests:` list `_check_covered_tests` actually reads, and its gate 3 — a listed
test with no definition — is `Severity.ERROR`.**

**So CARD-314 lands before this card converts the puzzle page**, not after. It is the
one card in the phase that touches `src/`, and it exists to make the conversion safe
for CON-020 by marking the clue digits in the stream so the exemption survives **by
its mark, never by its size** — exempting 8.64 pt by value would exempt any body face
that happened to measure 8.64 pt.

**If this card converts the puzzle page with CARD-314 unlanded, raise it rather than
proceeding.** Converting the other four kinds first is a legitimate order; converting
the puzzle page is not.

## [Added 2026-10-29 from CARD-306's review — one class name becomes false the day this card lands]

CARD-306 gave the vector puzzle page its sheet furniture, and its review's **F-307** names a debt
that is **this card's to clear, not CARD-306's**:

`tests/test_book_puzzle_page_vector.py`'s
`TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture` **now names a claim that is false
of the shipped page.** CARD-306 re-pointed the class at `book_puzzle_vector`'s own **stream
output** rather than at the composed page, which is a genuinely narrowed claim and not one
relocated to stay true — the reviewer confirmed the module is **AST-identical ignoring
docstrings**, the narrowing is stated in prose, and the class carries an in-test control
(`len(composed) > len(shown)`). So the body is honest. **The name is the debt.**

When you convert the puzzle page, that class either goes or is re-pointed, and its name must stop
saying *"no sheet furniture"* about a page that draws folio, frame rules, grid-size label and QR
block. Per the board's standing rule, the name is not a cosmetic fix: a class name is a claim, and
this one will read true while being false.

Also worth carrying, both measured on CARD-306's branch and relevant here:
- `book_guide_vector:103`, `book_toc_vector:60` and `book_answer_vector:62` **all import
  `book_pdf_generator` at module level**, so none can be called from its page walk without a
  cycle. CARD-306's new `src/nonogram/admin/book_sheet_vector.py` was deliberately built
  **kind-agnostic for all interior kinds** and imports only `book_vector`, `book_vector_draw` and
  `export.layout` — the minimum set that breaks that cycle, asserted by set equality. **Its
  furniture is ready for the other four kinds; the assembly point is the thing that is missing**,
  and that is this card's work.
- Guide, TOC and answer pages currently carry **no frame at all**. CARD-306 declared that a
  residual and named it as this card's.

## [Added 2026-10-30] AC-3 counts readers by an import name, and eight modules arrive by another road

**Raised from an owner question about CARD-288's relevance, and measured rather than assumed.**

AC-3's twelve are derived from *"modules that import `tests/helpers/pdf_pages.py`'s one-image
reader"*. That derivation is correct about what it measures and **blind to a second population
that hits the same wall**: modules that never parse a written PDF at all, because they call
**`BookPDFGenerator.interior()` / `.interior_pages()`** and consume the result directly.
`interior_pages` is declared `-> List[Image.Image]`. **The day a kind converts, it stops being
that**, and `_write_pdf`'s own representation refusal already says so in the form these modules
will meet it: *"… page, but arrived as `<type>`"*.

**Derived 2026-10-30** by walking `tests/**/*.py` for the reader import and for `.interior(` /
`.interior_pages(` call sites:

| set | count |
|---|---|
| **A** — imports the one-image reader (AC-3's derivation) | 14 modules |
| **B** — calls `.interior()` / `.interior_pages()` | 14 modules |
| **A ∩ B** | 6 |
| **B \ A — consume generator page objects and AC-3 cannot see them** | **8** |

| module in B \ A | image-shaped uses of the returned pages | `len(pages)` checks |
|---|---:|---:|
| `tests/test_book_puzzle_frame.py` | 35 | 7 |
| `tests/test_book_pdf_two_up.py` | 22 | 16 |
| `tests/property/test_book_pdf_geometry.py` | 17 | 2 |
| `tests/test_book_difficulty_dots.py` | 14 | 1 |
| `tests/test_book_cell_size.py` | 12 | 0 |
| `tests/test_book_divider_pages_option.py` | 2 | 1 |
| `tests/test_book_pdf_levels.py` | 2 | 2 |
| `tests/property/test_book_pairing.py` | 1 | 3 |

"Image-shaped uses" counts `.size`/`.crop`/`.convert`/`.getpixel`/`.load`/`.resize`/`.getbbox`,
`np.asarray(...)` and the ink readers. **All eight use the pages as images.**

**What is measured and what is not.** Measured: the eight modules, the two sets, and that every one
of them treats the returned pages as images. **Not measured: which of them actually breaks.** That
depends on *which page kinds each one indexes* and whether those kinds convert — a module that only
reads the cover or the dividers is unaffected, and several take `len(pages)` only. **Deriving that
per-module is this card's job, and it should be done before the first kind converts, not after the
first red.** Per ADR-0039/R2, a module the walk cannot classify is a FAILURE, not a silent pass.

**The one worked example, because it is the suite's densest file.**
`tests/property/test_book_pdf_geometry.py` indexes **puzzle pages specifically**
(`pages[3 + toc_page_count + index]`) and calls `drawing_of` on them. It imports the one-image
reader **zero** times — CARD-299's fix round was right to strike it from the count — and it is in
`B \ A` with 17 image-shaped uses. CARD-314's round measured the shape it will meet: lifting the
puzzle page's raster declaration gives *"page 6 is a vector puzzle page, but arrived as Image"*.

**Why the oracle does not save it.** ADR-0042/R6 declares *"independent second-implementation
oracles (`Sheet` and its kind) are unaffected and still compared against — **only the reading of
the artefact changes**"*. `Sheet` lives in that file at `:124`. So R6 **protects the assertions and
explicitly requires the reading to change** — which is the work AC-3 is about, for a module AC-3
cannot see.

**Scheduling consequence for CARD-288**, which is what prompted this. CARD-288 optimises *how those
four tests obtain their pages* — 3820 drawn to read 1033. **It must run AFTER this card**, or the
optimisation is designed against a page-obtaining mechanism this card replaces, and the work is
done twice. CARD-288 is otherwise intact: its subject file is untouched since its 2026-10-24
census, all four tests are present by name, and its headline figure carries an **independent
corroboration within 1.7%** — which is exactly what CARD-220's review found the 20261023 rankings
lack elsewhere (overstated **4.8×–10.3×** as a small selection).
