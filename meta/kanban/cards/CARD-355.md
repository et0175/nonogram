# CARD-355: `tests/test_book_pdf_memory.py` — 27 reds, and its one seam site would change what the test measures

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/355-pdf-memory-tests
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-355
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_pdf_memory.py, tests/helpers/pdf_vector.py (SCOPE+, decided by the orchestrator after the cycle-1 review: the shared-reader fix below)
**Review score:** —
**Started:** 2026-11-05T11:41Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

> ## ⚠ M10 IS THREE MECHANISMS, measured by CARD-358 — and the label describes only the first
>
> CARD-358's seven reds were *pure M10 in one small module*, which made it the cheapest place on the
> board to ask whether M10 is one mechanism. **It is three**, and this scopes your 45 reds:
>
> **A — the reading exists in the converted medium and was taken in one arm only.** Measured under
> the lift: the spy exempted **0** faces while the stream exempted **644** *(per book — 1288 across the two books; CARD-358's review corrected this, since the figure is quoted)* by the writer's own
> clue-digit mark. Nothing stopped being true; a reading stopped being taken. **This is the mechanism
> M10's label actually describes** — the cause lines really are `assert []` / `assert set()`.
> *Disposition: a mechanical union of the two arms. Cheap and local.*
>
> **B — the provenance the claim needs is absent from the stream BY DESIGN.** Not a reading taken in
> one arm; the other arm **cannot carry the claim at all**. The stream's one piece of provenance is
> the clue-digit mark, the mark *means* exempt, and the claim was that certain digits are **not**.
> `book_guide_vector`'s own source says so: *"This medium has no `_write_clues` to tag, so the
> distinction is made deliberately rather than inherited."* **The M10 label does not describe this.**
> *Disposition: needs a surviving authority named per claim — this is where ADR-0042/R6's "retire with
> a named survivor" actually bites.*
>
> **C — the VOCABULARY has no counterpart in the stream.** `TextCall.kind` reconstructs a vocabulary
> finer than the page kind — band, footer label, answer caption — off the **call chain**. A content
> stream has no call chain and no per-face record for the answer, puzzle or TOC writers (only the
> guide has one). Measured: the spy's semantic reading of both books collapses to `{'divider'}`, the
> one kind still raster. **The label does not describe this either**, and the failure is a
> *set-comparison*, not an empty read. *Disposition: **⚠ CORRECTED 2026-11-05 on CARD-358's review (ADR-0039/R4): the cost ordering this block first stated was WRONG.** It said *"expect C to be the expensive one — B had an authority to fall back on and C had none."* **Measured by that review: B's authority (`GuidePage.faces`, tagged `CLUE_DIGIT`) is COARSER than the claim**, so B collapses into C in practice and **B is not cheaper than C.** The evidence is a plant: with the guide's worked example drawing nothing at all, the module stayed byte-identical to baseline, because the page lays out FOUR families of line diagram and all four tag `CLUE_DIGIT`. *Disposition for both B and C: a named surviving authority per claim, verified by a plant that reds it.* Reviewer-measured; the fix round re-derives it.*
>
> **The rule neither groups one mechanism nor separates two**, which is why the bucket cannot be
> sized from the label:
>
> | mechanism | the alternation it matched | what that keys on |
> |---|---|---|
> | A (exempt set) | `assert \[\]` | a failure **shape** |
> | A (cross-check) | `assert set\(\)` | a *different* failure shape |
> | B (worked example) | `drew no text` | **a string lifted from the test's own message** |
> | C (coverage) | `AssertionError: assert \{` | a shape matching *any* set comparison anywhere |
>
> **So do not size your share from the label — classify first.** CARD-358 reports the classification
> cost one scripted reading of both arms per claim, not a card.
>
> **And mechanism B has no rule at all**: it reaches M10 only through `drew no text`, a string from
> the assertion message CARD-358 was about to rewrite — so the classification would have changed when
> the *wording* changed. `classify_reds.py` was deliberately not edited (CARD-338 is closed).

> **⚠ UNVERIFIED FIGURES, 2026-11-05.** This card quotes **57 M10 reds / 35 cause lines**. They are CARD-337's round's roll-up and **three readers have now tried and failed to verify them** (CARD-358's round, its review, and the orchestrator). The review's census aborted on its own gate at 14 of 20 modules — *the instrument working*, a zero-collect most plausibly caused by a foreign lock appearing mid-run, since the guard refuses in `pytest_configure`. **And one component has already moved:** CARD-356's module measures 26 reds, not its stated 25. **Do not quote the roll-up as fact; re-derive your own module's count at the start**, which is what scopes your card anyway.

## The population, from CARD-337's cross-tab

**29 reds under the five-kind probe; this card owns 27.** The other 2 are **M3**
(`book_pdf_generator.py: TypeError: page 1 is a vector puzzle page, but arrived as Image`) and
are **CARD-322's** — a product behaviour, which G-1 forbids this card from touching.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M7d** in-module `ContentStream` read | **15** | `AttributeError: 'ContentStream' object has no attribute {'width'\|'tobytes'\|'crop'\|'convert'}` |
| **M10** medium-blind empty read | **7** | a residual — see the warning below |
| **M9** byte identity | **5** | `AssertionError: assert b'\xff…' == b'\xff…'`, `interior page N is not the page it was`, `stored page N is …` |

## The thing that makes this card a design question and not a repair

**This module's single seam site is inside a test about peak bitmap memory** — "202 MB of live
bitmap". Wrapping it in `interior_images` would change **what the test measures**: from
generator-produced bitmaps to poppler-rasterised ones. The number it asserts would then be a
fact about poppler, not about the generator.

**So the obvious repair silently changes the subject.** That is an ADR-0042/R6 disposition
question — re-express the memory claim against the operator stream (which has no bitmap to
measure), or retire it with a named survivor — and **it must be decided before any wrapping.**

**This module also holds the suite's only `setrlimit(RLIMIT_AS)` skip**, the 1 skip every
armed gate on this board reports. Do not remove it and do not let it become a skip-of-two.

**M10 warning:** board-wide M10 is 57 reds across 35 cause lines — a residual, not a mechanism.
Re-split your 7 before trusting the label.

## What to implement

1. **Decide the memory test's disposition first**, and state it with the measurement. Everything
   else in this module is cheaper than this one question.
2. **The 15 M7d reds**: per-site re-expression or retirement with a named survivor; say which
   and why, per site.
3. **The 5 M9 byte-identity reds**: a byte comparison across a medium change is a claim about
   determinism, not about pixels. State what identity means once a page is operators.
4. **Re-split the 7 M10 reds** and report the histogram.

## Acceptance criteria

- **AC-1** *Given* the memory test, *then* the card states its disposition — re-expressed or
  retired with a named survivor — and the decision is **asserted**, not commented.
  (check: review-lens)
- **AC-2** *Given* the five-kind probe, *then* the module's red count is stated before and after,
  and every remaining red is routed with an owner or carries a stated disposition. The 2 M3 reds
  are **CARD-322's** and must still be present and attributed, not absorbed.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-3** *Given* the `setrlimit(RLIMIT_AS)` skip, *then* it is **still exactly one skip** and
  still attributed by name from `-rEfs`.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-4** *Given* each repaired site, *then* a plant re-breaks it with its matched control green
  in the same run and `0 skipped` asserted; state how many node ids each plant moves, since many
  are fixture-raised.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)

## How to measure, and the instrument is not yours to build

**Re-derive your own population before implementing anything.** The instruments are committed:

- `scratchpad/card338/census_five_kinds.py` — the driver (drives `probe_five_kinds.py`). **Run
  it, do not rebuild it.** CARD-338 owns, committed and refusal-proved it.
- `scratchpad/card338/classify_reds.py` — the mechanism taxonomy.
- `scratchpad/card337/cross_tab.py` — the mechanism × module table. It **imports** `RULES` /
  `classify` from `classify_reds.py` rather than restating the taxonomy; keep that property if
  you extend it.

**Two hazards in those instruments, both measured:**

1. **`classify_reds.py` is NOT filter-agnostic.** Faithful on the five-kind dump (143/143, exit
   0, no "other" group). On a `PUZZLE`-only dump of the same thirteen modules it leaves **13 of
   78 unclassified and exits 1** — loud, but only if you read the exit code. **Scope nothing
   from a `PUZZLE`-only reading.**
2. **A mechanism census of the UNPLANTED tree is not the census after a repair.** Measured:
   `pdf_band` shows **zero** byte-identity reds unplanted, and **three** among the survivors
   once the `interior_images` seam is planted. So your post-repair survivors may carry
   mechanisms your pre-repair census does not list. Re-census after your repair, not only
   before.

**And `-rfs` omits ERRORs — use `-rEfs`.** That matters more here than usual: **21 of the 40
M7d reds board-wide print as `ERROR at setup`**, fixture-raised, so one repair flips many node
ids at once and one plant can re-break many. Clear `addopts = "-q"` with `-o addopts=` as **two
argv items**. The worktree has no `.venv` — use
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`.

## Guardrails

- **G-1** — **No `src/` change.** Every product-behaviour red in this module family is routed to
  **CARD-322** (M1 delitem, M2 expected-side gap, M3 `Image`-arrived-as-vector, M3b the cp1252
  title refusal). If your measurement indicts the generator, that is a **finding and a routing**,
  not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass.** `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move.
- **G-3** — **Stay inside your `Touches`.** The module partition is what makes these cards
  concurrently runnable; a card that reaches into a sibling's module destroys that property.
  Planting a mutant into another module and restoring it byte-identically is a measurement and
  is allowed — the SHA-256 pair is the proof — but leaving an edit there is the violation.
- **G-4** — No new runtime dependency (ADR-0006/R1): stdlib + Pillow + NumPy is closed.
- **G-5** — Take no timing measurements and report no durations; other work shares the machine.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). **Never** set `NONOGRAM_IGNORE_FULL_SUITE_LOCK` and
  never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection, so a redirect blinds a file-scoped run to a gate that *is* holding it.
- **G-7** — **G-8 standing: do not connect to the production database.** `conftest.py` refuses
  by URL text before connecting; do not widen or bypass `_refuse_unless_test_database`.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the
  content stream or retired with a named survivor (check: review-lens)

[Author round, commit `0bb1f7f1`] Verified by the orchestrator: tip `0bb1f7f1`, one commit over the cut `b3d04d8c`, `tests/test_book_pdf_memory.py` only (+735/-69), `src/` diff 0, no non-test file; module 65 passed + 1 skipped unlifted (the skip is the `setrlimit(RLIMIT_AS)` platform gate). Author-reported: the memory test re-expressed in two halves, never rasterised (class `TestBookPdfMemory_TheMemoryClaimsDisposition`): a bitmap page keeps the exact `peak == one page bitmap` equality, a `ContentStream` page costs zero bitmap bytes and its retention is checked by the medium-blind `LivePageBytes.peak_pages == 1`; `test_the_rasteriser_tripwire_is_live` is the control for the refusal to substitute poppler-rasterised bitmaps. The old "202 MB" figure is RETRACTED by the author (never re-derived).

[Review 1/3] Score: **8.4 - PASS** (threshold 8.0), at tip `0bb1f7f1`. Derived by the reviewer: merge-base module under the probe 16 failed + 13 errors = 29 reds, 25 passed, 1 skipped; after, 2 failed / 63 passed / 1 skipped; unlifted 0 failed / 65 passed / 1 skipped. The 2 remaining reds are the M3 reds `test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer` and `test_a_producer_that_yields_too_many_is_refused_before_the_extra_page` (`TypeError: page 1 is a vector puzzle page, but arrived as Image`), CARD-322's, present before and after. All 11 author plants re-fired and killed (node ids moved 3, 5, 4, 6, 9, 7, 2, 3, 1, 1, 3); the reviewer's 9 edge mutants were all killed, one by only a single test (F-002 below). AC-4's "0 skipped" cannot hold here because AC-3 forces the one `setrlimit` skip; `skipped == 1` was asserted instead and the reviewer agrees. Card-text corrections, ADR-0039/R4: (1) the body said this module's single seam site is in a test about peak bitmap memory and that wrapping it in `interior_images` would change the subject: **the module never used `interior_images`**; the real seam was `LivePageBytes.track`, shared by every export route and behind 13 of the 15 M7d reds (all fixture-raised); the memory-test question was decided anyway. (2) The "7 M10 / 5 M9" bucketing came from the classifier: the author's derivation is 7 mechanism D (a shared reader returning the wrong page) + 4 true M9 + 1 other (`test_a_page_that_fails_at_page_12_of_14_hands_the_caller_nothing`, a `Failed: DID NOT RAISE` atomicity test the classifier's M9 rule wrongly catches; the reviewer confirmed it; `classify_reds.py` is closed under CARD-338, so this is a routing note and no card). The reviewer did not reproduce the author's layer-E figures (30x30 mean 10.2, 6.2% beyond 50 levels vs thresholds 8.0 and 3%; carried), and the thresholds were not moved (G-2).

THE SHARED-READER DEFECT, MEASURED. `tests/helpers/pdf_pages.py::pdf_pages` rasterises every operators page into one scratch directory and `tests/helpers/pdf_vector.py::rendered_page` returns `sorted(glob("page-*.png"))[0]`, so every operators page after the first comes back as the first one's render (the blank title page, 0 ink): on the baseline book under the probe, all 10 operators pages give one sha and 0 ink, whereas poppler's per-page ink is 0, 483451, 437745, 48950, 291191, 242015, 468261, 252230, 175372, 669849; the 4 raster pages are right. On the unlifted tree every page is raster, so the defect is dormant there. Blast radius, from the reviewer's local plant (a per-page output prefix) over 16 importer modules under the probe: **no hollow green** (nothing green at baseline went red), and **five reds turned green**: `test_every_page_the_screen_names_carries_what_it_says` and `test_the_interior_is_as_long_as_the_plan_the_screen_showed` (`tests/test_book_arrange_page_breaks.py`), `test_the_exported_interior_opens_with_both_guide_pages_then_the_first_puzzle_or_divider`, `test_every_diagram_is_drawn_at_the_books_own_cell_pitch` and `test_the_exported_interior_page_2_is_titled_how_to_solve_nonograms` (`tests/test_book_guide_page.py`). Not measured: `tests/property/test_book_pdf_geometry.py` under the probe (its 120 s per-test hang guard kills the run at the first test in baseline and plant alike; unlifted it gave 4 passed, helper unreachable); and whether the reds that remain in the other modules are red for the right reason. DECISION (orchestrator, under the cut bar: the fix is smaller than a card, is measured, and blocks the sibling cards' own repairs): the two-line fix lands INSIDE this card as the declared SCOPE+ file `tests/helpers/pdf_vector.py`, with a regression test, and the author re-measures all importer modules before the gate. Findings fixable inline, author resumed: F-002 `test_a_content_stream_page_costs_no_bitmap` costs an EMPTY stream, so a probe costing a stream by `len(operators)` passes it (killed by only `test_the_same_instrument_sees_the_old_shape_grow`); F-003 the `interior_pages_of` docstring says "the five raster pages are right" where the reviewer measures 4 raster + 10 vector pages in the baseline book; F-004 `interior_pages_of` still calls the defective `pdf_pages(data)` over the whole file; F-006 M9 determinism-only identity passes a stream that is stable but wrong (operators-page content is held by sibling modules and the shifted-by-one and above-footer references: state it).

[Fix round for review 1, commits `dbe18aa1` (SCOPE+ helper alone) and `5701c57f` (module)] Verified by the orchestrator at tip `5701c57f`: worktree clean; over the cut `b3d04d8c` two files changed, `tests/helpers/pdf_vector.py` (+13, the declared SCOPE+) and `tests/test_book_pdf_memory.py`; `src/` and `meta/` diffs 0, no other non-test file. The helper diff is the intended one: `rendered_page` now writes `pg<page>-*.png` into the directory, removes stale files of that prefix first, and reads back only that prefix, instead of the shared `page-*.png` glob; signature and the "wrote no image" RuntimeError kept. My own run of `tests/test_book_pdf_memory.py`, `tests/test_book_arrange_page_breaks.py` and `tests/test_book_guide_page.py` unlifted: 136 passed, 1 skipped (the `setrlimit(RLIMIT_AS)` platform gate). Author-measured, not re-run by me: the 16 importer modules probe-scoped baseline (old helper restored by sha) vs fixed: 5 reds turn green (the five the reviewer listed), 0 green turns red, in either mode; the unfixed remaining reds are unchanged; `tests/property/test_book_pdf_geometry.py` unlifted 4 passed, NOT measured under the probe; memory module unlifted 68 passed / 1 skipped, probe-scoped 2 red / 66 passed / 1 skipped (the 2 M3 reds, CARD-322's). Regression test: class `TestBookPdfMemory_TheSharedReaderReadsEachPageForItself` (a two-operators-page PDF, page 2 differs from page 1 and equals a direct `pdftoppm` render of page 2; its matched control is green on the defective helper too); re-planting the old behaviour by text moved 2 node ids red with the control green. F-002 the control stream now carries operators (a `len(operators)` costing plant moves 3 node ids red); F-003 the docstring says 4 raster + 10 vector pages and "nine after the first"; F-004 `interior_pages_of` simplified to `pdf_pages` plus the file's media, default-deny, which removed the module's own per-page reader (the first round's shared-scratch plant no longer applies; the new regression class covers that defect); F-006 `raster_digests` now states that determinism does not check content and names where operators-page content is held. Not re-run after the F-004 simplification: the first round's other plants (module green in both modes). Not measured: any module outside the 16 importers plus geometry that reaches `rendered_page` (a grep found no other caller globbing `page-*`). Not re-reviewed after this round: it goes to the merge gate, whose armed full suite is the check on the unlifted tree.

