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
**Review score:** cycle 1 **7.5 — did NOT certify** (2 open important, 0 critical) → **fix round 1 complete** (`180b64f0`, `src/` **comment-only**), cycle 2 running. **F-001's two false statements are gone and now have a control that cannot be theatre:** `TestRasterDeclarations_TheCommentAgreesWithTheRegistry`, 4 cells, **two-armed and chosen by data** — `set(PageKind) - set(_RASTER_DECLARATIONS)` decides whether a removal claim is *forbidden* or *required*, so CARD-322 changes its arm rather than editing it. Six mutants MF-1..MF-6, **0 survivors**, including one that **hollows the detector** and one that makes the **extractor vacuous**. **Verified by the orchestrator:** putting the false sentence back verbatim reds exactly `test_the_comment_claims_no_removal_the_registry_cannot_show`. It declined to quote the retracted sentences in the comment, reasoning a false claim quoted where it was removed from is one the next reader must re-adjudicate. **Two recorded reaches corrected UPWARD** — M8 reds 3 not 1, M11 reds **7** not 2 — traced to a round-1 harness that ran against the union of expected node ids instead of the whole impact set. **And it corrected a claim the orchestrator relayed:** the card's own M5 (`if False:`-wrapped) reds exactly its named cell; cycle 1's M5x (unguarded) dies at collection with 0 cells run. Two different plants, and the card was right about its own — what is wrong is the *implication*, since a real module-level cycle is un-plantable.
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

## Failure matrix

Declared before the code was written, one row per boundary x failure mode, each with a
numeric bound. **This card has no I/O concurrency** — PDF generation is in-process,
single-threaded, allocates no file handle and opens no socket — so every row below is a
*representation* or *composition* failure, which is the honest shape for it rather than a
one-line "no failure-bearing boundary": the card's whole subject is a new boundary between
the interior's page walk and the page writers downstream of it, and that boundary can fail.

| # | boundary / operation | failure mode | declared behaviour | numeric bound |
|---|---|---|---|---|
| F-1 | the walk asks `InteriorPageWriters` for a kind `page_medium` calls VECTOR | the field is `None` (a declaration was lifted without composing through the assembly point) | `_drawn_downstream` raises `ValueError` naming the kind **and** `nonogram.admin.book_interior_vector` | exactly **1** refusal, raised at the first page of that kind; **0** bytes of PDF reach any caller (the buffer is a local of `_write_pdf` until the trailer) |
| F-2 | same | a writer is present but bound to the wrong kind's field | the writer raises on the argument shape it was not written for, and the interior is never written | detectable in **1** interior write of a book holding >= 1 page of each lifted kind; measured as mutant M8, killed by `test_each_of_the_four_bindings_was_used` |
| F-3 | `_write_pdf`, per page | a page arrives in the other medium's representation from the one its kind declares | `TypeError` naming the page number, the kind and the type that arrived (unchanged by this card — G-6) | **0** bytes written; the refusal is at page *k* of *N* and takes its partial bytes with it |
| F-4 | the walk's per-kind medium gate | a gate is added, removed or asks something other than the decider | `page_medium` call tally over the module's AST is an equality | **5** calls in `produce` (TITLE, GUIDE, TOC, PUZZLE, ANSWER) and **1** in `_write_pdf`; DIVIDER has no gate and is held by F-3 instead |
| F-5 | `_RASTER_DECLARATIONS`, conversion direction | a kind goes vector and its entry stays | `_declaration_findings` reports it | <= **1** finding per entry, so <= `len(_RASTER_DECLARATIONS)` = the registry's own size |
| F-6 | `_RASTER_DECLARATIONS`, landing direction | every card an entry names reaches a terminal status and the entry is still here | `_landing_findings` reports it; a card whose status the board cannot give is **also** a finding (default-DENY) | <= **1** finding per entry; **0** cards on the board may have an unreadable status (asserted over **every** card file the board holds — a count, not a constant: **321** when this row was written, **330** when the card's own census was re-derived 670 lines below. The assertion is `== 0 unreadable`, which does not depend on the total, so the figure is the stale part and the claim is not) |
| F-7 | the import direction | an edge is added from the generator to a writer that imports it, at any depth, or a module imports the assembly point | one finding per offending module, by AST over `src/nonogram/**/*.py` | **0** allowed, out of the whole package the walk enumerates; a function-body import counts (mutant M6) |

Two rows are deliberately *not* here, and each for a measured reason rather than an
omission: **memory** (a content stream is 3-4 orders of magnitude smaller than the 25.2 MB
page bitmap CARD-145's bound is about, and the walk's `del page` is untouched), and
**partial files** (the buffer is `_write_pdf`'s local until the cross-reference table, which
is `tests/test_book_pdf_memory.py`'s `TestBookPdfMemory_NothingHalfWrittenEscapes`, not
this card's).

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

- **[scratchpad — the review settled it, and fix round 1 implemented the split]**
  Round 1 committed 13 files under `scratchpad/card309/` (11 `.py` probes plus
  `impact.txt` and `census-converted.txt`) and flagged "should these reach
  `main`?" as a review question. Review cycle 1 answered it on measured
  reasons, and the branch now carries the answer:
  - **KEPT on the branch, and so on `main`: `scratchpad/card309/impact.txt` and
    `scratchpad/card309/census-converted.txt`.** These two are *measurements*,
    not tooling: the 27-module impact set, and the per-module tally and every
    failing node id of the converted state (`189 failed / 1860 passed /
    1 skipped / 75 errors in 223.54s`). Nobody downstream can re-derive them,
    because the conversion that produced them is reverted — and the card's
    blocker argument cites them.
  - **MOVED OUT to `~/Documents/nonogram-reviews/CARD-309/`: all 11 `.py`
    probes, and every untracked file.** Exactly what moved is listed in
    *"[Fix round 1, 2026-10-30]"* at the end of this card. The reasons are the
    review's, each measured: (a) `main` carries **nothing** under `scratchpad/`
    and `scratchpad/` is **not** in `.gitignore`, so the commit was silently
    establishing a precedent, on a card that is not about tooling; (b) the
    probes are **host-pinned** — `render_for_owner.py:13` hardcodes this
    worktree's absolute path — so they do not run from a `main` checkout and
    become a dead ref the moment the worktree goes, which is the very thing
    committing them was meant to prevent; (c) `render_for_owner.py` as
    committed renders pages 2/4/6/9 only, so it is not even the script that
    made the committed p12 renders (F-007).
  - **The card-scoped directory was still right** (not the shared scratchpad
    root, which is CARD-284's measured defect). The defect was the commit, not
    the location.

- **[Fix round 1, 2026-10-30 — review cycle 1 closed, and what each correction was derived
  from]** Cycle 1 scored **7.5**, did not certify, two open Important and zero critical, and
  **every defect was in the record** rather than in the architecture (which the reviewer
  re-derived and confirmed). The round's full account, including the **corrected mutant
  table**, is *"[Fix round 1, 2026-10-30] Review cycle 1's findings, closed"* at the end of
  this card. The derivations, one line each:
  - **F-001** (the one defect that shipped in `src/`) — from `git diff main..HEAD`, which
    removes **0** `PageKind.` entries, and from importing `_RASTER_DECLARATIONS` at HEAD and
    on `main`: **7** entries both sides, with five moving from `("CARD-299","CARD-309")` to
    `("CARD-299","CARD-322")`. **Re-pointed five, removed none.** The corrected statement
    ships with `TestRasterDeclarations_TheCommentAgreesWithTheRegistry` (4 cells, mutated by
    MF-1..MF-6, 0 survivors), because a prose claim that is mechanically checkable and is not
    checked is this card's own finding repeating itself.
  - **F-002** — from `grep -rn "F-307\|NoSheetFurniture" meta/kanban/` and CARD-322's G-5
    line. The claim was about **another card's guardrail** and was false of it. Declining was
    right; the routing had failed, and it was closed at the decompose station on `main`.
  - **F-003 / F-007** — from `git ls-files scratchpad/` against
    `git ls-files --others --exclude-standard scratchpad/`: **13** tracked, **23** untracked,
    and every file the "all three runs are kept" sentence cited was in the untracked set.
  - **F-004** — from `git diff main..HEAD -- tests/test_book_pdf.py`, which touches the
    `_BOARD_STATUSES` frozenset **zero** times (the rebase took `main`'s strict superset), and
    from re-reading one `**Status:**` line per card file in the main working tree today:
    **330** files, zero with none and zero with two, `in_progress` **zero**.
  - **F-005** — from re-firing round 1's **exact** mutant plants against the **whole** impact
    set instead of the union of expected node ids, which is the harness defect that made both
    mis-statements possible. The reach column of the table is **counted from the rows**.
  - **F-006** — not this card's. Routed to CARD-322 / CARD-330 and to the owner's eye.

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
- **[BLOCKER] decomposition defect: AC-1 and AC-3 are not the same size.** The
  assembly point, the walk's four gates and the declaration re-point are **done**;
  the puzzle-page conversion is **not**, and the reason is measured rather than
  estimated — lifting PUZZLE's declaration reds **189 failures and 75 errors across
  22 test modules**, whose root causes are **four distinct instruments and not one
  reader**, three of which are ink oracles rather than readers of a PDF and one of
  which (the difficulty-dot accounting in `tests/test_book_difficulty_dots.py` with
  `tests/helpers/round_ink.py`) has **no vector twin carded anywhere on the board**.
  The decisive number: the two media place the same grid **2 device pixels, 0.169 mm**
  apart on all four edges, against a **0.1 mm** placed-edge tolerance, so every
  placed-edge expectation in the tree changes **value** with the medium — a per-site
  disposition, which ADR-0042/R6's own comment assigns to **CARD-312**. The full
  measurement, the per-module census and what a re-decomposition needs are in
  *"[CARD-309's round, 2026-10-30]"* at the end of this card. **CARD-314 is landed**
  (the clue-digit mark is live in the stream and in
  `tests/helpers/pdf_vector.marked_type_sizes`), so it is not what blocks this.
- **CARD-314's prerequisite is satisfied**, checked rather than assumed: a vector
  puzzle page written on this branch opens a `/ClueDigit BMC` sequence around its
  digits, so CON-020's exemption survives by its mark the day the kind converts.

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

## [CARD-309's round, 2026-10-30] What was built, what was measured, and the blocker

### STRUCTURE decisions — CARD-322 reads these as the local convention

- **STRUCTURE: the assembly point is `src/nonogram/admin/book_interior_vector.py`** — a new
  module downstream of all five page writers, named after the two things it joins (the
  *interior*, and the `book_*_vector` family). Why a new module and not a reshuffle of an
  existing one: `book_guide_vector`, `book_toc_vector` and `book_answer_vector` each import
  `book_pdf_generator` at module level for the constants, type sizes and frame helpers the
  pages are composed from (measured: `book_guide_vector:103`, `book_toc_vector:60`,
  `book_answer_vector:62`), so the walk inside `book_pdf_generator` cannot import them back.
  The two alternatives were rejected on the ladder, not on taste: making those three imports
  lazy is the same cycle with its direction hidden in a function body (and is a finding to
  `TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden`, mutant M6), and hoisting the ~70
  shared names out of `book_pdf_generator` into a leaf module is a reordering of a declared
  `conflict.hotspots` file that CARD-306 already declined.
- **STRUCTURE: the direction is resolved by a parameter, not by a registry or a lazy import.**
  `book_pdf_generator` declares the *shape* it needs — `InteriorPageWriters`, a frozen
  dataclass of four callables with the downstream writers' own signatures — and the walk calls
  through an instance. The generator imports no writer that imports it; the assembly point is
  the only module that can see all five writers at once, and **nothing in `src/` imports the
  assembly point**, which is what keeps the resolution a direction rather than a loop with a
  door in it (asserted, mutant M7). A module-level mutable registry that the assembly point
  registered into was rejected: it makes the medium a function of import order, which is a
  hidden global and the "workaround" the card forbids.
- **STRUCTURE: injection is on the generator, not on each export call.**
  `BookPDFGenerator(book, pages=...)`, read once in `__init__` beside `ink_mode` and
  `divider_pages` and for the same stated reason. `export_book`, `export_interior` and
  `interior` are one walk behind three doors; a keyword forwarded through all three would be
  three signatures carrying a fact that belongs to the generator, and the standards reject a
  layer that only forwards.
- **STRUCTURE: the puzzle page is deliberately NOT a field of the writer set.**
  `book_puzzle_vector` imports no generator, so `book_pdf_generator` already imports it and
  composes the page itself (`vector_puzzle_page`/`vector_two_up_page`). That is exactly why
  the split put the puzzle page in this card: converting it needs no assembly point, so the
  architecture and the conversion can be judged separately.
- **STRUCTURE: default-DENY at the new boundary.** A field left `None` is not a fallback to
  the bitmap. `_drawn_downstream` refuses, by kind, naming the assembly point — one step
  earlier than `_write_pdf`'s representation refusal, which is untouched (G-6) and still the
  thing that catches a bitmap handed in under a vector declaration.
- **STRUCTURE: no C4 change, no component-map row.** COMP-009 is one component
  (`components-CTX-001.puml:100`) and `tests/test_cli.py`'s layering guard and component map
  both work at *component* granularity, so a new module inside `admin/` needs neither. The
  guard passes **unmodified** (AC-5).

### [BLOCKER] decomposition defect: AC-1 and AC-3 are not the same size, and three of AC-3's four root causes are instruments nobody has carded

**Measured before it was written down.** The card's item 2 — convert the puzzle page and
delete PUZZLE's declaration — was implemented in full on this branch and the impact set run
against it: **189 failures and 75 errors across 22 test modules** (`tests/` impact set,
`-o addopts='' -p no:randomly`, census in `scratchpad/card309/census-converted.txt` — the
file that is **committed with this branch**, holding the per-module tally and every failing
node id, and the one artefact of the three runs that nobody downstream can re-derive because
the conversion is reverted; the raw pytest log it was distilled from is
`~/Documents/nonogram-reviews/CARD-309/runs/run_converted.txt`; the
unconverted tree runs the same set at 2122 passed / 1 skipped / 0 failed). The conversion was
then **reverted** and PUZZLE's declaration re-added with that measurement as its reason, so
what is shipped is the architecture and not a red tree. CARD-322 is named in all five
interior entries (the card's own item 3, and its explicit second option: *"it must re-point
the surviving entries at whatever card finishes the job, in the same commit. Say which,
explicitly."*).

**Why this is a decomposition defect and not an estimate miss.** AC-3 names *"the readers"*
and derives them from an import of one helper. Derived per module instead, the 264 red cells
have **four** root causes, and only the first is a reader of a PDF:

1. **`tests/helpers/pdf_pages.py`'s one-image reader** — `KeyError: b'XObject'`, because it
   loops **every** page asserting one `DCTDecode` image. This is AC-3's own subject and is a
   genuine reader conversion. Measured: 15 cells in `test_book_export_interior_cover.py`,
   9 in `test_book_pdf_ink_mode.py`.
2. **`tests/helpers/page_ink.py`'s `drawing_of` and `tests/helpers/two_up_ink.py`** —
   `'ContentStream' object has no attribute 'convert'`, the largest share (27 of
   `test_book_difficulty_dots.py`'s, 21 of `test_book_pdf_two_up.py`'s, all 20 of
   `test_book_cell_size.py`'s, 6 of `test_book_pdf_band.py`'s). These are **not** readers of a
   file: they are independent-oracle *geometry instruments* that recover a drawing from ink,
   and their stream twins are new instruments. **And a stream twin cannot simply replace
   them**, which is the measurement that settles this: re-derived here with
   `~/Documents/nonogram-reviews/CARD-309/probes/offset_probe.py` on CARD-295's own `Twin` fixture, **the raster and the
   vector media place the same grid 2 device pixels — 0.169 mm — apart on all four edges**
   (ink `grid_left/right` 963/1849 against the stream's 965/1851; `grid_top/bottom` 1126/2012
   against 1128/2014; one offset, all four edges, which is exactly what
   `TestPuzzlePage_AgreesWithTheRasterTwin` declares as Pillow's line-cap convention). The
   tree's placed-edge tolerance is `tests/test_book_pdf.py`'s **`EDGE_TOLERANCE_MM = 0.1`**.
   0.169 > 0.1, so **every placed-edge expectation in the tree changes value with the
   medium** — which is a per-site disposition with a convention question behind it
   ("which convention is the book's?"), not a reader swap. ADR-0042/R6's own comment assigns
   the *"321-site surface, a per-site disposition"* to **CARD-312**.
3. **`tests/test_book_difficulty_dots.py` with `tests/helpers/round_ink.py` (27 cells)** —
   the worst of the four and the one with no card at all. That instrument **monkeypatches the
   raster drawing site** `book_pdf_generator._draw_difficulty_dots`, records every dot it
   draws against the identity of the page image it drew on, and then accounts every round ink
   region on every page against that recording. On a vector page that site is never called
   and there is no page image to key on, so the instrument is not reading the wrong medium —
   **it is measuring a page the product no longer draws**. Its vector twin is CARD-241/243's
   spelling-blind instrument rebuilt for operators, and CARD-241's own module docstring
   records that three review cycles were needed to get the raster one right. Nothing on the
   board carries it.
4. **`tests/test_book_export_interior_cover.py`'s frozen AST censuses over
   `book_pdf_generator.py`** — these move with any additive edit to that module and are
   **re-derived in this card** (see below). Not a blocker; named because they are outside the
   impact radius and the merge gate finds them, not the review.

**What a re-decomposition needs, concretely.** (a) the one-image reader's conversion — AC-3's
real content, small; (b) a convention decision for the 0.169 mm offset, then CARD-312's
per-site disposition over the geometry instruments; (c) a card for the difficulty-dot
accounting instrument in the vector medium, which does not exist; (d) only then CARD-322's
four conversions and R1's flip. **Converting the puzzle page is downstream of (a), (b) and
(c), not of this card's architecture** — and the architecture is done, so CARD-322 inherits a
working assembly point whichever order the rest lands in.

**This card did not grow to cover (a)-(c)**, per the pipeline rule the brief states in the
strongest terms. It measured them, named them, and stopped at the line.

### AC by AC — what passes, what does not, and how it was verified

- **AC-1 — PARTIAL, and the half that is shipped is the half the merge gate reads.**
  PUZZLE's entry is **not** removed (see the blocker). **No declaration names CARD-309**: all
  five interior entries now read `("CARD-299", "CARD-322")`, verified by
  `tests/test_book_pdf.py::test_no_declaration_names_the_card_that_is_closing` (new; mutant
  **M10** — re-pointing one entry back to `("CARD-299", "CARD-309")` — killed it, and did
  **not** kill the landing guard, which is why the new cell exists: that guard reads the
  board and CARD-309 is `in_progress`, so it passes with CARD-309 named all over the
  registry). `test_no_declaration_outlives_the_cards_that_remove_it` is **green on this
  branch** (it was RED at HEAD — see the finding below). R1 is **not** flipped (item 4).
- **AC-2 — PASSES for the kinds it can be asked about.** The writer's representation refusal
  is untouched (G-6) and is still driven by
  `TestWritePdf_RefusesWhatItCannotWrite::test_a_bitmap_under_a_vector_declaration_is_refused`
  and `::test_a_stream_under_a_raster_declaration_is_refused`. The card's two mutants, one
  inside the region and one at its edge, are **M1** (the guide gate ignores the writer set
  and hands a bitmap over under a lifted declaration — killed by
  `test_every_interior_page_is_written_as_operators`) and **M2** (default-DENY removed, a
  missing writer falls through — killed by `test_a_generator_with_no_downstream_writer_refuses`
  **and** `test_a_partial_writer_set_refuses_only_the_kind_it_is_missing`).
- **AC-3 — NOT MET. See the blocker.** Both populations were derived rather than quoted
  (`~/Documents/nonogram-reviews/CARD-309/probes/derive_readers.py`, by AST): **A = 12** modules import the one-image
  reader (AC-3's own figure, reproduced exactly) and **B \ A = 9** files reach the hazard
  through `.interior()`/`.interior_pages()` — the card's eight test modules plus
  `tests/helpers/book_corpus.py`, which its table does not list because it is a helper. No
  module was left unclassified (ADR-0039/R2).
- **AC-4 — PASSES, with a count of ZERO.** **No baseline moved**, because no kind converted:
  `git status --porcelain tests/fixtures/` is empty, so all 21 `book_baseline_card*.json`
  files are byte-identical to HEAD and nothing under `tests/fixtures/**` was regenerated
  (G-4). CON-019's property test and the A4 golden are untouched and green —
  `tests/property/test_cli_exports_byte_identity.py`, `tests/test_export_a4_golden.py` and
  `tests/test_guard_integrity.py`: **233 passed** (G-3). **Interior size and generation time
  at both ends**, on a 16-page book (`~/Documents/nonogram-reviews/CARD-309/probes/render_for_owner.py`, the same book
  both ways, same process):

  | medium | bytes | B/page | ms | ms/page |
  |---|---:|---:|---:|---:|
  | raster (what this branch ships) | 4,786,226 | 299,139 | 333.6 | 20.85 |
  | vector (through the assembly point) | 607,106 | 37,944 | 91.7 | 5.73 |

  **7.9x smaller and 3.6x faster**, on 16 pages. Stated as the pair of integers beside the
  durations, per the board's prefer-a-counter rule; the byte counts are the integers and
  reproduce exactly, the milliseconds are one reading on one host. ADR-0042's own headline is
  22.4x on a 24-page interior and 8.5x in time — **this is a different book and a smaller
  one**, so it corroborates the direction and is not a reproduction of that figure.

  **[Review cycle 1 re-ran this, and the split it predicted is the split it got.]** The
  reviewer re-fired the same probe on its own host: the **bytes reproduced exactly** —
  4,786,226 / 607,106 B, 299,139 / 37,944 B/page, **7.9x**, 16 pages, every figure identical —
  and the **milliseconds did not**: 523.0 / 126.5 ms, **4.1x** against this row's 333.6 /
  91.7 and 3.6x. Nothing is restated in the table, because the table already says which half
  is reproducible and which is one reading on one host, and the host-dependence is now
  **confirmed by a second host** rather than asserted. The ratio moved 3.6x -> 4.1x in the
  *same* direction on a slower host, which is the shape a fixed per-page raster cost has.
- **AC-5 — PASSES, and it is the card.** `tests/test_cli.py`'s structural guard is
  **unmodified** (`git diff --stat` shows the file untouched) and green. The assembly point's
  own two classes, both new:
  - `TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden` — by AST over
    `src/nonogram/**/*.py`: the generator imports **none** of the three writers that import
    it *at any depth*; each of the three really does import the generator (the card's own
    premise, measured rather than quoted); the assembly point imports all four; and
    **nothing in the package imports the assembly point**. <!-- CORRECTED 2026-10-30 at review cycle 2's F2-001. This passage previously
    read: "Mutants M6 ... and M7 ... each killed exactly the cell that claims them. M5 (the
    same cycle at module level) also dies, but NOT THERE ... CPython refuses the import at
    collection, so the AST cell never runs and M6 is the cell's only real control."
    THREE OF THOSE ASSERTIONS ARE FALSE, and fix round 1 wrote them in the SAME COMMIT as the
    table that refutes them — ADR-0039/R4 (a figure recomputed and refuted is retracted
    EVERYWHERE it was written) broken in the AC verdict the merge gate reads. Measured twice,
    by the fix round and independently by cycle 2 over the whole 356-test impact set: the
    card's OWN M5 wraps the import in `if False:` and reds EXACTLY the named cell, 1 failed /
    355 passed. It is M5x -- cycle 1's DIFFERENT plant, the same import UNGUARDED -- that dies
    at collection with 0 cells run. Cycle 1 substituted a plant and then faulted this card's
    record for not describing the substituted one; the orchestrator relayed that. Only the
    CONCLUSION survived, and for a different reason than the one given. -->
    Mutants **M6** (a cycle inside a function body) and **M7** (another module imports the
    assembly point) each red the cell that claims them; **M7's reach is an expectation, not a
    measurement** — see the corrected table in *"[Fix round 1, 2026-10-30]"*. **M5** (the same
    cycle written at module level but wrapped in `if False:`) reds **exactly that cell too**,
    1 failed / 355 passed. So the cell is not hollow on any of the three.

    **What M5 does NOT prove, which is the real point:** its plant is an import the
    interpreter **never executes**, so M5 is evidence about the **AST reading**, not about a
    cycle. A genuine module-level cycle is **un-plantable** — unguarded, it dies in
    `conftest.py` at collection with **0 cells run** (that is M5x). **M6 is therefore the only
    mutant that plants an import the interpreter actually runs and is still caught by the
    cell**, which is why M6 — not M5 — is the cell's real control.

    **AC-5's wording is weaker than what M6 measured, and this is the stronger claim.** On
    M6, `tests/test_cli.py::test_every_import_in_the_package_points_inward` **PASSED** while
    the new cell reded. So the package-wide layering guard does **not** see a lateral import
    *inside* `admin/` — admin modules are peers in one layer and importing one from another
    points neither laterally across capabilities nor inward. AC-5's "the structural guard
    passes unmodified" is therefore **necessary but not sufficient**: it is the evidence that
    this card broke nothing, and it is *not* evidence that the direction is guarded. The
    direction is guarded only by
    `TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_the_generator_imports_none_of_the_writers_that_import_it`,
    which is work **nothing else in the tree does** — measured, by a mutant that passes one
    guard and reds the other.
  - `TestAssemblyPoint_TheDownstreamWritersAreReachable` — lifts **all five** interior
    declarations and writes a real interior through
    `book_interior_vector.interior_generator`: every interior page comes out as operators
    with no `/XObject`, the divider stays a bitmap (G-2), the face is embedded once
    (ADR-0042/R5), each kind is identified by **text only its own writer sets**, and each of
    the four bindings is **counted** at the binding. Mutants **M3** (the refusal fires on an
    incomplete set rather than on the kind), **M4** (every vector kind drawn by one writer)
    and **M8** (the packed-answer writer bound to the lone-answer field) all killed.
    **M8 is why the book is `((30, 30, 10), (10, 10, 3))`**: three 10x10s pack every answer,
    leave the lone-answer binding unexercised and let M8 survive — measured.
- **AC-6 — PASSES.** `~/Documents/nonogram-reviews/CARD-309/` holds `interior-raster.pdf`
  (what this branch ships), `interior-vector.pdf` (the same book through the assembly point,
  every interior kind as operators) and poppler renders of pages 2, 4, 6, 9 and 12 of both at
  150 DPI. **What the render shows**, looked at rather than asserted: the vector **guide**
  page is indistinguishable from its raster twin at 150 DPI bar a 1-2 px vertical offset; the
  vector **puzzle** page carries its band, frame, 0.3/0.8/1.3 pt grid, clue digits, folio,
  grid-size label and QR block with both caption lines — CARD-306's furniture is all there;
  the vector **answer** page carries its solved grid, caption and folio and, like its raster
  twin, **no** frame rules. The one thing worth the owner's eye is that this is the first
  time the whole interior has existed as operators in a file.

  **[Corrected in fix round 1 — which script made which render, F-007.]** The probe that
  renders pages 2/4/6/9 is the one that was committed; the **p12** pair in that directory was
  made by a run with page 12 added to the same loop, so the committed script is not the
  script that produced the whole committed set. Nothing about the renders changes; the record
  does. The probe has since moved to
  `~/Documents/nonogram-reviews/CARD-309/probes/render_for_owner.py` — beside the renders it
  made, which is where a host-pinned script belongs (it hardcodes this worktree's absolute
  path at line 13 and does not run from a `main` checkout at all). **It was not "fixed" to
  add page 12 and derive its root from `__file__`**, deliberately: it is evidence of a
  measurement already taken, not a tool anyone runs again, and editing it would have made the
  copy beside the renders no longer the thing that produced them.

  **[Routed, not fixed — F-006, the vector group rules read lighter at 150 dpi.]** The
  reviewer measured, inside the page-6 grid body at 150 dpi: raster **58** heavy columns /
  **47** heavy rows against vector **31** / **22** (a column or row counted heavy when >80%
  of its pixels in the body window are dark). The raster twin reads as a clean 5x5 block
  grid; the vector page reads as an almost uniform hairline grid. **The product is right** —
  page 6's content stream emits all three declared widths (`0.3 w` x1, `0.8 w` x2, `1.3 w`
  x4) — so this is a render-resolution artefact (the raster twin was drawn at 300 dpi and
  downsampled; the vector hairlines are rasterised at 150), not a missing feature and not
  this card's defect. **Routed to CARD-322 and CARD-330** (CARD-322 is the card that ships
  this page to a reader; CARD-330 owns the medium difference) **and to the owner's eye**, with
  the honest owner-facing sentence being *"the group rules are present but thinner at 150 dpi;
  judge them at print resolution"*. This card does not chase it.

### The impact set, and the one skip attributed by name

The impact set is the 27 modules in `scratchpad/card309/impact.txt`: this diff's own
modules, **both** reader populations AC-3 enumerates (A's 12 and B\A's 9), the interior
type-floor and vector-primitive modules, `tests/test_cli.py` (AC-5's guard),
`tests/test_collected_names.py` and `tests/test_suite_profile.py`. **No full-suite run was
taken** — a sibling card was running concurrently and the merge gate owns the full run.

`-o addopts='' -p no:randomly`: **2135 passed, 1 skipped, 0 failed** (386 s). The skip is
`tests/test_book_pdf_memory.py:1297` — `setrlimit(RLIMIT_AS)` refused by this kernel — and
it is **present at HEAD too** (the pre-change run of the same set: 2122 passed, 1 skipped),
so it is a host fact and not something this card silenced. Green-with-skips and fully
verified report the same total, which is why it is named rather than counted.

The same set was run **three** times on this branch: at HEAD **2122 passed / 1 skipped /
2 failed** (the two failures explained below — one is the board-status RED that predates this
card, the other was contamination from a concurrent edit to a file an AST guard reads from
disk, and both were re-measured in isolation); with the puzzle page converted,
**189 failed / 75 errors / 1860 passed**; as shipped, the figure above.

**[Corrected in fix round 1 — F-003.]** Round 1's sentence here said all three runs "are
kept", and that was **false of a checkout**: the three pytest logs, both node-id collections
and `readers.json` were all **untracked**, so none of them reached `main` and all of them die
with the worktree — a dead check ref one level down, which is the exact failure this card's
Mutants section names as its reason for committing anything at all. What is true, and is what
this card now cites:
- **the middle run's substance is on the branch**, in `scratchpad/card309/census-converted.txt`
  — the per-module tally and every failing node id of the converted state
  (`189 failed / 1860 passed / 1 skipped / 75 errors in 223.54s`). It is the blocker's
  evidence and the one measurement nobody downstream can re-derive, because the conversion is
  reverted. **The blocker argument is reproducible from the branch alone.**
- **the raw logs are kept outside the repo**, at
  `~/Documents/nonogram-reviews/CARD-309/runs/` — `run_base.txt`, `run_converted.txt`,
  `run_final1.txt`, `run_final2.txt`, `collect_base.txt`, `collect_now.txt`, `readers.json`.
  That is where cited evidence that is not a measurement the tree needs belongs, and it is
  where they now resolve from.

### G-5, measured rather than asserted

Node-id set difference over the impact set with `-o addopts=''` (an explicit `-q` would have
stacked to `-qq` and printed no node ids at all): **2125 collected at HEAD, 2136 now,
0 removed, 11 added** — the ten assembly-point cells and
`test_no_declaration_names_the_card_that_is_closing`, each verified **by node id** rather
than by a green total, so a class pytest silently never ran would show here as a missing id.
No test was deleted, renamed, skipped or merged; no `parametrize` id moved.

### Mutants fired, in one place

Harness: `~/Documents/nonogram-reviews/CARD-309/probes/mutate.py` (round 1) and
`.../fix-round1-harness/mutate.py` (fix round 1). Both were written under
`scratchpad/card309*/` while they ran — card-scoped, never the shared scratchpad root, which
is CARD-284's measured defect — and both were moved out of the tree before the commit.

**What is committed and what is not, corrected in fix round 1 (F-003).** Round 1 committed
the eleven probe scripts and claimed that committing them was what kept the evidence alive.
Review cycle 1 measured the opposite on three counts: `main` carries nothing under
`scratchpad/` and `scratchpad/` is not in `.gitignore`, so the commit was quietly setting a
precedent on a card that is not about tooling; the probes are host-pinned (an absolute
worktree path at `render_for_owner.py:13`) and so do not run from a `main` checkout at all,
which makes them a dead ref the day the worktree goes — the very outcome committing them was
meant to prevent; and the committed `render_for_owner.py` is not even the script that made
the committed p12 renders. **So the split is by what the artefact IS, not by where it was
written**: the two *measurements* — `scratchpad/card309/impact.txt` (the 27-module set) and
`scratchpad/card309/census-converted.txt` (the per-module tally and every failing node id of
the converted state) — stay on the branch and reach `main`, because the card's argument rests
on them and the reverted conversion cannot be re-measured. Every *probe* and every raw log
lives in `~/Documents/nonogram-reviews/CARD-309/`. A measurement cited from a path that
resolves nowhere from a checkout is a dead check ref one level down (CARD-298's F-004, and
recorded in ADR-0042/R2's own comment) — and a script committed to `main` that cannot run
from `main` is the same defect wearing the fix's clothes.

`PYTHONDONTWRITEBYTECODE=1`, `__pycache__`/`*.pyc` swept **before and after** every mutant,
the target file SHA-256'd against its baseline before *and* after each one, and the recorder
proved on a bare `assert x == y` (empty `AssertionError` message) before any zero was
believed. **11 mutants, 0 survivors.** M1-M2 are AC-2's pair; M3-M4 and M8 drive the runtime
half of AC-5; M5-M7 drive its structural half; M9-M10 drive the two board-facing cells;
M11 is the control for the census claim re-derived below.

### SCOPE+ and findings

- **SCOPE+ `tests/test_book_export_interior_cover.py` — three frozen figures re-derived.**
  Not in `Touches`, and unavoidable: that file holds an AST census of
  `src/nonogram/admin/book_pdf_generator.py` by equality, and this card adds to that module.
  Each delta is **attributed, not pasted**: `POSITION_NAMES` gains `toc_page_number` (the
  TOC's page number is now bound rather than spelled in the one call that used it, because
  the vector arm needs it twice; measured both ways — inline keeps the vocabulary and takes
  the guide-counting census 9 -> 11, bound keeps that census at 9 and adds one name);
  `CALLEE_EXEMPTION_COST` moves 841/567/213/211 -> 855/579/214/211, of which **+1 is this
  card's whole indirection cost** and the last two steps stay **0** (the shipped arm still
  refuses nothing); and the module-axis bound moves `inside == 19` -> `23`, one
  `self.page_spec` per gate, cross-checked by a plain text count of `self.page_spec(`
  (19 -> 23) and by `ast.Call` nodes (912 -> 932) in a second domain.
- **SCOPE+ `tests/test_book_pdf.py`'s `_BOARD_STATUSES` — a live RED on `main` this card
  found, and which `main` has since fixed. The diff no longer changes the set at all.** The
  set held `"in progress"` with a **space**; the dispatcher writes **`in_progress`**. Nothing
  could observe that on 2026-10-29 when the set was derived, because the board had no card in
  flight that day (`acd0a386`: *"wave 68 closes with no card in flight"*). Wave 69 opened two
  and `test_no_declaration_outlives_the_cards_that_remove_it` **reded at HEAD** with
  `['CARD-268', 'CARD-309']` — measured on this branch with the card's own src stashed, so it
  was never this diff. **This is a finding about the board's own gate**: the cell's verdict is
  a function of the *main* working tree's card directory, so dispatching any card reds every
  in-flight branch until the spelling is known. That is **CARD-310's** subject; nothing here
  is the hoist.

  **[Corrected in fix round 1 — F-004. Two figures and one claim here were written for the
  pre-rebase state.]** This card's rebase resolved the file in `main`'s favour, because
  `main`'s set is a strict **superset**: it had already added `in_progress` **and** `review`
  and dropped the dead space form. So `git diff main..HEAD` touches the frozenset **zero**
  times and only the comment above it is this card's. Three corrections:
  - *"The widening and its exemption ship together: `in_progress` joins the vocabulary"* —
    **false after the rebase.** `main` landed the widening; this card adds no spelling. What
    remains true, and is all the comment now claims, is that `in_progress` is deliberately
    **not** in `_TERMINAL_STATUSES` and that `CARD-90003` is the control for that arm.
  - *"six spellings, every card accounted for"* — **wrong in both directions**, which is why
    the comment now writes no vocabulary list at all (its own no-counts rule, which the list
    was violating). The frozenset holds **seven**; the list omitted `review`, which two cards
    carry today — CARD-309 itself being one of them — and asserted `in_progress`, which **no
    card in the live tree carries**.
  - *"the main working tree's 321 cards: `done` 274, `ready` 40, ... `in_progress` 2"* —
    stale. **Re-derived today from the main working tree, by reading one `**Status:**` line
    per card file** (330 files, zero with none and zero with two): `done` 275, `ready` 48,
    `blocked` 3, `review` 2, `skipped` 1, `parked` 1 — summing to 330, and **`in_progress`
    zero**. Stated here, where a card records what it measured and when, and deliberately
    **not** pasted back into the comment: a per-status count in a comment nobody re-reads was
    already two cells out within a day of being written, which is the drift the comment's own
    rule exists for.
- **FINDING for CARD-306's F-307, NOT done here, and the reason is G-5.**
  `tests/test_book_puzzle_page_vector.py`'s
  `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture` is named as this card's debt.
  Its **body** is already honest (CARD-306 re-pointed it at `book_puzzle_vector`'s own stream
  output, which really does draw no furniture); the debt is the **name**, and the only fix
  for a name is a rename. **G-5 forbids renaming a test** — node ids included — and G-5 is
  authoritative at the task level and may only be weakened at the decompose station. The
  class is also untouched by this card in substance, since no kind converted. **Declined, and
  routed to CARD-322**, which converts the kinds and will be in that file anyway.

  **[Corrected in fix round 1 — F-002. The decision was right; the hand-off claimed something
  that was not yet true.]** Round 1 wrote that CARD-322 "should carry the rename with a
  guardrail that permits it", in a tense that reads as a statement about that card. Measured
  at review cycle 1: CARD-322 had **zero** mentions of F-307 or the class name, and its G-5
  carried the **same unqualified prohibition** this card had just declined under — so the
  debt was owed by a card that did not know it, behind a guardrail that forbade it, and the
  loop was set up to run again. The declining was not the defect: **G-5 is authoritative at
  the task level and may be weakened only at the decompose station**, never in a worktree, so
  this card could not have granted itself the exemption. The *routing* was the defect. It has
  since been closed **at the decompose station, on `main`, not by this card**: CARD-322's G-5
  now carries one **named** exception for exactly this class
  (`tests/test_book_puzzle_page_vector.py:1950`), with the re-stamp obligation spelled out,
  and CARD-322 carries a section recording why the debt exists. `meta/kanban/cards/CARD-322.md`
  is **not** touched by this branch — it is not this card's file to edit, and the exemption is
  not this card's to grant. What this card owes, and now states, is the true sentence: it
  **declined** the rename under G-5 and **routed** it to CARD-322, where the exception was
  subsequently granted at the decompose station.
- **FINDING, measured, that retires CARD-306's other residual.** CARD-306 recorded *"guide,
  TOC and answer pages currently carry no frame at all"* as this card's. Measured here:
  `_draw_page_frame` has exactly **two** call sites in `book_pdf_generator.py` — `_blank_page`
  and `_two_up_page`, both puzzle pages. **The raster guide, TOC and answer pages carry no
  frame either**; each draws a folio and nothing else. So the vector twins are at **parity**
  with the pages that ship, and this is a product question about front matter rather than a
  conversion defect. It belongs to whoever owns the interior frame's scope (CARD-222's
  family), not to ADR-0042's conversion phase.
- **FINDING about CARD-299's completeness, as AC-3 asks.** CARD-299 left the *readings* in
  three sites medium-gated and the *readers* untouched, which its own prose says. What this
  card measured and CARD-299's prose does not reach: the surface is four instruments, three
  of them ink oracles rather than PDF readers, and one of those has no vector twin on the
  board at all (see the blocker, cause 3).
- **FINDING for CARD-288, confirming the card's own note.** CARD-288 optimises how four tests
  obtain their pages. Those tests obtain them through `interior_pages()`, which is cause 2
  above; the mechanism is unchanged by this card, so CARD-288 is **not** unblocked by it and
  still must run after whichever card converts the puzzle page.

### What `trace.yml` gets

Nothing. `trace.yml` carries **no ADR-0042 rule rows** (re-checked on this branch: two prose
mentions only), and no FR row's test moved, because no test was deleted, renamed or
re-pointed and no baseline changed. A Trace line promising a re-stamp here would be the
mistake CARD-298 inherited.

### [Fix round 1, 2026-10-30] Review cycle 1's findings, closed — and the mutant table re-derived from the rows

Cycle 1 scored **7.5** and did **not** certify (two open Important, zero critical). Its verdict
is worth restating because it shapes this round: **the architecture was re-derived rather than
accepted, and proved right** — no cycle anywhere, `tests/test_cli.py` 0 times in the diff,
`_write_pdf` byte-identical to `main`, the refusal unbypassable, all seven guardrails measured
passing, the three frozen figures re-derived from the rows, and AC-4's **byte** figures
reproducing exactly. **Every defect was in the RECORD**, and it has one cause: the prose was
written for the CONVERTED, pre-rebase state and was not fully re-derived after the revert and
the rebase. **One instance of that shipped in `src/`.** So this round changed no architecture.

#### F-001 (Important, gating) — a false claim in shipped `src/`, and the control it owes

`src/nonogram/admin/book_pdf_generator.py`'s `#:` comment on `_RASTER_DECLARATIONS` carried two
statements: *"the rest are CARD-298's findings, **one fewer since CARD-309**"* and *"No count of
them is written here on purpose — **CARD-309 removed one entry** and a number in this comment
would have been the drift CARD-261 found twice"*. **Both were false.** Re-derived here as well
as at the review: `git diff main..HEAD` removes **0** `PageKind.` entries, and the registry holds
**7** at HEAD — cover `()`, divider `('CARD-231',)`, and title/guide/toc/answer/puzzle each
`('CARD-299','CARD-322')`. On `main` those same five read `('CARD-299','CARD-309')`, so what the
card did is exactly **re-point five, remove none**.

**The shape of the error is the point**: the second sentence invoked **CARD-261's drift precedent
as its own justification while committing that drift** — and the same comment nominates this
mapping as *"the one honest reading of how far ADR-0042/R1 has actually got"*, so the false
statement sat on the one thing the comment claims is honest.

**Fixed, and the no-count policy kept** (that half was right and is CARD-261's lesson applied
correctly). The comment now says what happened — built the assembly point, **converted nothing**,
**re-pointed five entries** from itself at CARD-322 — records that two earlier sentences claimed
otherwise and were measured false, and justifies the no-count rule by the rule itself rather than
by a removal that did not occur. The retracted sentences are **not quoted** in the comment: a
false claim quoted where it was removed from is a claim the next reader has to re-adjudicate, and
it would also have had to be exempted from the control below. They are quoted here instead.

**The control, because a claim may change only with the test that proves the new one.**
`tests/test_book_pdf.py::TestRasterDeclarations_TheCommentAgreesWithTheRegistry` — **4 cells**,
and it holds the comment to the registry in **both** directions, so it does not need editing when
CARD-322 legitimately converts a kind; it changes arm:

- `test_the_comment_claims_no_removal_the_registry_cannot_show` — reads the contiguous `#:` block
  directly above the assignment, joins it to one line (the two false sentences were each wrapped
  across two), and scans it with a **9-pattern vocabulary** of already-happened removal claims.
  `set(PageKind) - set(_RASTER_DECLARATIONS)` decides the arm: nothing taken out → the comment may
  claim no removal; something taken out → it **must** say so, or it reads as further from done
  than it is, which is the mirror defect and the one CARD-322 walks into.
- `test_the_registry_lost_nothing_and_five_entries_name_the_converting_card` — the 7/5 shape the
  corrected prose asserts, **derived**: seven is written as
  `set(_RASTER_DECLARATIONS) == set(PageKind)` (no page kind has converted), not as a number; five
  is written once beside a second derivation (`declared - {COVER, DIVIDER}`) that writes no number
  at all, because a figure the comment states is a figure a cell owes. No entry may name CARD-309.
- `test_the_block_is_the_one_above_the_registry` — the extractor's own control, both polarities. A
  block the reading cannot find is a green suite that checked nothing.
- `test_the_reading_catches_the_claims_and_spares_the_honest_sentences` — guard-the-guard, **per
  sentence in both polarities**: 6 sentences that must be caught (the two verbatim false ones
  first) and 8 that must not, every one of the 8 either standing in this comment today or the true
  form of a retraction — *"CARD-322 is the card that removes these four"* (a FUTURE removal, which
  is the mapping's whole point), *"the shrink is guarded in two directions"*, *"CARD-309 removed no
  entry"*. Plus a floor: at least **4 distinct** patterns fire across the claims, so the
  vocabulary is not one regex doing all the work.

**Mutated, and measured per assertion** — harness
`~/Documents/nonogram-reviews/CARD-309/fix-round1-harness/mutate.py`, `PYTHONDONTWRITEBYTECODE=1`,
caches swept before and after each, target SHA-256'd before and after, **6 mutants, 0 survivors**:

| mutant | plant | reds |
|---|---|---|
| **MF-1** | the *"one fewer since CARD-309"* sentence put back verbatim | `…::test_the_comment_claims_no_removal_the_registry_cannot_show` (1 red, 5 passed) |
| **MF-2** | the *"CARD-309 removed one entry"* sentence put back verbatim | the same cell (1 red, 5 passed) |
| **MF-3** | the registry loses an entry — `PageKind.PUZZLE:` keyed as `PageKind.COVER:`, collapsing two keys into one — while the prose still says nothing was taken out | the **mirror arm** of that cell, `…::test_the_registry_lost_nothing_and_five_entries_name_the_converting_card`, and `test_no_declaration_outlives_the_cards_that_remove_it` (which asserts the cover's `expires_with == ()`, and the collapsed key gives it the puzzle's) — **54 red over the whole impact set**, of which those three are the attributed kills. <!-- CORRECTED 2026-10-30 at cycle 2's F2-002, and the correction is the same defect this round NAMED as its own root cause: round 1's `mutate.py` ran only "the union of the node ids it expected to red", so its "cells it reds" column was really "cells it was expected to red". The round fixed that in `refire.py` and LEFT `mutate.py` -- the harness that certified this very control -- still passing `(CONTROL,) + NEIGHBOURS`. So this row said "3 red" where the real reach is 54, understated 18x. AND THE PLANT'S DOMAIN WAS UNDECLARED: collapsing `PageKind.PUZZLE:` onto `PageKind.COVER:` leaves PUZZLE undeclared, so `page_medium(PUZZLE)` returns VECTOR and every puzzle page changes medium -- MF-3 is a SHIPPED-BEHAVIOUR mutant, not the clean prose-vs-registry isolate this row described, and its mirror-arm kill is confounded with 51 others. No cell attribution was wrong and 0 of 6 mutants survived; the reach figure and its domain were. ADR-0039/R4 again. --> |
| **MF-4** | TITLE re-pointed back to `("CARD-299", "CARD-309")` | the shape cell and `test_no_declaration_names_the_card_that_is_closing` — 2 red |
| **MF-5** | the reading hollowed out (`if re.search(...)` → `if False and …`) | `…::test_the_reading_catches_the_claims_and_spares_the_honest_sentences` — 1 red. The detector is **not** hollow. |
| **MF-6** | the extractor anchored on a name that is not in the file, so the block comes back empty | `…::test_the_block_is_the_one_above_the_registry` — 1 red. A vacuous green is **not** reachable. |

#### F-002 — closed as a record correction only; the routing was closed on `main`, not here

See *"FINDING for CARD-306's F-307"* above for the corrected sentence. In short: declining was
right (G-5 is weakened only at the decompose station), the **routing** had failed — CARD-322 had
zero mentions of F-307 and an unqualified G-5 — and that has since been fixed at the decompose
station **on `main`**: CARD-322's G-5 now carries one named exception for exactly that class, with
the node-id re-stamp obligation spelled out. `meta/kanban/cards/CARD-322.md` is **not** touched by
this branch. This card's own sentence now claims only what is true of this card: it **declined**
and **routed**.

#### The committed scratchpad — the split the review decided, implemented

Round 1 committed **13** files under `scratchpad/card309/` and left ~10 more untracked beside them.

- **STAYED on the branch (2 files):** `scratchpad/card309/impact.txt`,
  `scratchpad/card309/census-converted.txt`. They are *measurements*, the card cites them, and
  **nobody downstream can re-derive them** because the conversion they measure is reverted.
- **MOVED OUT to `~/Documents/nonogram-reviews/CARD-309/` (34 files):**
  - `probes/` — all **11** `.py`: `answer_mix.py`, `census_diff.py`, `census_diff2.py`,
    `cost_diff.py`, `derive_readers.py`, `dump_stream.py`, `mutate.py`, `offset_probe.py`,
    `refusals.py`, `render_for_owner.py`, `sitediff.py`.
  - `runs/` — the **7** untracked logs and derived files the card cited: `run_base.txt`,
    `run_converted.txt`, `run_final1.txt`, `run_final2.txt`, `collect_base.txt`,
    `collect_now.txt`, `readers.json`.
  - `notes/` — the **3** untracked drafting files: `card_notes.md`, `card_sections.md`,
    `notes_body.md`.
  - `review-cycle1-harness/` — the **13** untracked files of the reviewer's own mutant harness
    (`fire.sh`, `m2/m5/m6/m8/m8b/m11.py`, their `.out` logs, `measure.py`), which would otherwise
    have died with the worktree and are the evidence behind F-005.
  - `fix-round1-harness/` — this round's `mutate.py` and `refire.py`, moved out for the same
    reason before the commit.

  Every copy was `shasum -a 256`-compared against its source before the source was deleted: **0
  mismatches**.
- **The reasons are the review's, each measured:** (a) `main` carries **nothing** under
  `scratchpad/` today and `scratchpad/` is **not** in `.gitignore`, so the commit was silently
  establishing a precedent, on a card that is not about tooling; (b) the probes are
  **host-pinned** — `render_for_owner.py:13` hardcodes this worktree's absolute path — so they do
  **not** run from a `main` checkout and become a dead ref the moment the worktree goes, which is
  the very thing committing them was meant to prevent; (c) `render_for_owner.py` as committed
  renders pages 2/4/6/9 only, so it is not even the script that made the committed p12 renders.
- **The card-scoped directory was still the right place to write them** (never the shared
  scratchpad root, CARD-284's measured defect). The defect was the commit, not the location — and
  a script committed to `main` that cannot run from `main` is a dead ref wearing the fix's clothes.

#### The corrected mutant table — round 1's eleven, re-derived

**The root cause of both mis-statements is the harness, and it is worth naming:** round 1's
`mutate.py` ran only the **union of the node ids it expected to red**. A mutant's reach outside
that union was therefore invisible by construction, and the "cells it reds" column was really the
"cells it was expected to red" column. This round re-fired against **the whole impact set**
(`tests/test_book_pdf.py`, `tests/test_book_export_interior_cover.py`, `tests/test_cli.py` —
356 passed, 0 failed, **0 skipped** unmutated) and the reach column below is **counted from the
rows of that run**.

Re-fired: **M2, M5, M6, M8, M11**, each with round 1's *exact* plant copied from its harness
rather than paraphrased, `PYTHONDONTWRITEBYTECODE=1`, caches swept before **and** after each,
the target SHA-256'd against baseline before each and after restore (the guard earned its keep:
a concurrent invocation of the harness aborted on it rather than measuring against a planted
file). Baseline **356 passed / 0 failed / 0 skipped**; after all mutants restored, **356 passed
/ 0 failed / 0 skipped** again.

| mutant | plants | round 1's record | this round, counted from the rows |
|---|---|---|---|
| **M2** | default-DENY removed from `_drawn_downstream` (`if writer is None` → `if False`) | killed by `test_a_generator_with_no_downstream_writer_refuses` **and** `test_a_partial_writer_set_refuses_only_the_kind_it_is_missing` | **CONFIRMED, exactly those 2** and nothing else (2 failed / 354 passed) |
| **M5** | the cycle at module level, as round 1 planted it: `if False:` + `from nonogram.admin.book_guide_vector import guide_page` | "killed exactly the cell that claims it" | **1 red, and it is that cell** — `TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_the_generator_imports_none_of_the_writers_that_import_it`. **But see the row below: the plant is an import statement the interpreter never executes, so what it proves is narrower than the card implied.** |
| **M5x** | the **same** cycle at module level **unguarded** — a real one | not fired | **the suite does not collect at all.** `ImportError: cannot import name 'FOLIO_PT' from partially initialized module 'nonogram.admin.book_pdf_generator' (most likely due to a circular import)`, raised while loading `tests/conftest.py`, through `app.py:79 → book_kdp.py:105 → book_pdf_generator.py:402 → book_guide_vector.py:103`. **0 cells run, the named cell among them.** |
| **M6** | the same cycle **inside a function body** (`interior_stream`) | killed exactly the cell that claims it | **CONFIRMED, 1 red, that cell** (1 failed / 355 passed) — and the secondary result below, which is the useful one |
| **M8** | the packed-answer writer bound to the lone-answer field in `book_interior_vector.DOWNSTREAM_WRITERS` | killed by `test_each_of_the_four_bindings_was_used` | **3 red** — that cell **plus** `test_every_interior_page_is_written_as_operators` and `test_the_four_writers_each_drew_their_own_page`. Not a weaker kill; a **wider** one than recorded. |
| **M11** | the TOC gate calls the injected writer through a **local** instead of `_drawn_downstream`'s parameter | "reds two cells of this class" (the harness's `expect` list named 2) | **7 red — 3.5x the recorded reach.** Six in `tests/test_book_export_interior_cover.py::TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage`: the two named (`test_the_page_position_set_is_derived_from_the_one_geometry_door`, `test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`) plus `test_every_planted_position_shape_is_caught_or_refused`, `test_each_door_axis_arm_catches_a_shape_the_other_misses`, `test_the_door_axis_arms_reach_every_call_and_refuse_none_of_them`, `test_the_declared_blind_spots_are_still_silent` — and one in `tests/test_book_pdf.py`: `TestAssemblyPoint_TheDownstreamWritersAreReachable::test_a_partial_writer_set_refuses_only_the_kind_it_is_missing`. |
| **M1, M3, M4, M7, M9, M10** | AC-2's inside arm, the refusal on a set rather than a kind, one writer drawing every kind, the assembly point imported by another module, the board's unobserved spelling, an entry re-pointed back at CARD-309 | each killed the cell(s) round 1 names | **not re-fired this round, and the reach column for them is round 1's EXPECTATION, not a measurement** — stated plainly rather than carried as if measured. M10's shape *was* re-measured, as this round's MF-4, and reds `test_no_declaration_names_the_card_that_is_closing` plus the new shape cell. |

**M5, re-stated honestly, because the correction cuts both ways.** Round 1's sentence is true of
round 1's *plant*: the `if False:` guard makes a module-level `import` statement that the AST
reading sees and the interpreter never runs, so the named cell reds and nothing else does. What
the sentence invites a reader to believe, and what is **false**, is that this demonstrates the
cell catching a module-level cycle. **It cannot be demonstrated**: a real one (M5x) is
un-plantable — CPython refuses it while loading `conftest.py`, the suite collects zero tests, and
the cell never runs. So M5's evidence is about the **reading**, not about a cycle; **M6 is the
only mutant that plants an import the interpreter actually executes and is still caught by the
cell**, and the cell's own evidence is therefore M6's. The guard is not hollow either way — the
mutant does die — but the attribution was wrong and it mattered, because it was the cell's only
claimed control.

**M6's secondary result, which strengthens AC-5 beyond its own wording and was not recorded.**
On M6, `tests/test_cli.py::test_every_import_in_the_package_points_inward` **PASSED** while the
new cell reded. Measured again on M2, M5, M8 and M11: that guard is **GREEN on every one of the
five mutants re-fired**. So the package-wide layering guard does **not** see a lateral import
inside `admin/` — admin modules are peers in one layer, and one importing another points neither
across capabilities nor inward, which is exactly what `tests/test_cli.py`'s walk is built to
catch. AC-5's *"the structural guard passes unmodified"* is therefore **necessary but not
sufficient**: it is evidence that this card broke nothing, and it is **not** evidence that the
direction is guarded. The direction is guarded only by
`TestAssemblyPoint_TheDirectionIsResolvedAndNotHidden::test_the_generator_imports_none_of_the_writers_that_import_it`,
which does work **nothing else in the tree does** — and that is a stronger and more useful claim
about this card's contribution than the one AC-5 currently makes.

#### F-003, F-004, F-005, F-006, F-007 and AC-4's timings

- **F-003 — closed.** See *"The impact set"* above: the "all three runs are kept" sentence is
  replaced by what is true of a checkout. The blocker's evidence is on the branch
  (`census-converted.txt`); the raw logs are cited at `~/Documents/nonogram-reviews/CARD-309/runs/`.
- **F-004 — closed.** See the `_BOARD_STATUSES` SCOPE+ entry above. Both stale claims removed from
  the comment; the board census re-derived today (330 card files, `in_progress` **zero**) and
  recorded in the card rather than pasted back into the comment.
- **F-005 — closed.** The corrected mutant table above, plus AC-5's re-statement.
- **F-006 — routed, not fixed.** Recorded in AC-6 and routed to **CARD-322 / CARD-330** and to the
  owner's eye: the vector group rules read lighter at 150 dpi (p06 raster 58 heavy columns /
  47 heavy rows against vector 31 / 22) but the stream **does** emit `0.3/0.8/1.3 w`, so it is a
  render-resolution artefact, not a missing feature and not this card's defect.
- **F-007 — closed as a record correction.** AC-6 now says which script rendered which pages, and
  the probe moved beside the renders it made rather than being edited.
- **AC-4's timings — confirmed host-dependent, no figure changed.** The reviewer re-fired the probe
  and the **bytes reproduced exactly** (4,786,226 / 607,106 B, 299,139 / 37,944 B/page, 7.9x,
  16 pages); the milliseconds did not (523.0 / 126.5 ms, 4.1x against 333.6 / 91.7 and 3.6x). The
  table already framed the durations as one reading on one host with the integers beside them,
  which is this board's rule, so one sentence was added recording that a second host **confirmed**
  the split rather than a new figure being pasted in.

#### The gate, with skips attributed

Impact set, `-o addopts='' -p no:randomly` (an explicit `-q` would have stacked to `-qq` and
printed no count line at all): `tests/test_book_pdf.py`,
`tests/test_book_export_interior_cover.py`, `tests/test_cli.py` — **356 passed, 0 failed,
0 skipped** in 142.30 s, measured **after** every mutant was restored. The same set was
**356 passed / 0 failed / 0 skipped** before the mutants, so nothing moved across them.

**Skips: zero, and that is the measurement, not an absence of one.** Green-with-skips and fully
verified report the same total, so *passed* is the figure that distinguishes them: 356 collected,
356 passed, nothing to attribute. The one skip this card recorded for its own wider impact set
(`tests/test_book_pdf_memory.py:1297`, `setrlimit(RLIMIT_AS)` refused by this kernel) is in a
module **outside** this round's set and does not appear in it.

**The count moved by 4 and the four are named.** Round 1's figure for the same three modules is
352 (356 less this round's four); this round adds
`TestRasterDeclarations_TheCommentAgreesWithTheRegistry`'s four cells and nothing else.

**G-5 re-measured over the WHOLE tree, not asserted.**
`-o addopts='' -p no:randomly --collect-only -q tests/`, run on a clean `main` checkout and on
this working tree, node ids compared as sets: **branch 9971, 0 REMOVED, 15 ADDED** against a
main that read **9956 at the merge-base**. <!-- CORRECTED 2026-10-30 at cycle 3, and it is the
F-6 pattern one level up: 9956 was written as a fact about `main` when it was a DATED READING
of main at this branch's merge-base. Main has since moved -- 9995 today -- because CARD-268
merged and brought 39 node ids with it (35 in test_puzzle_solver_probe.py, 2 in
test_puzzle_solver_resume.py, 1 each in test_admin_design_tokens.py and
test_browser_fixture_scope.py), NONE of which is in this card's Touches. The branch did not
move; main did. The figure is now written so the claim is the DELTA -- which is what G-5
asserts -- and main's total is dated context rather than a standing fact that goes stale every
time any other card merges. -->
**The claim is the delta, not main's total**: no test was deleted, renamed, skipped or merged,
and the 15 added are accounted for one by one below.
The 15 are the 11 the review measured (the ten assembly-point cells plus
`test_no_declaration_names_the_card_that_is_closing`) **plus exactly** the four cells of
`TestRasterDeclarations_TheCommentAgreesWithTheRegistry`. So no test was deleted, renamed,
skipped or merged, no `parametrize` id moved, and the review's own 9956 -> 9967 is reproduced
and accounted for: 9967 + 4 = 9971.
