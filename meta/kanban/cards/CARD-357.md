# CARD-357: `tests/test_book_export_interior_cover.py` — 15 reds, and 2 are a DPI nobody passed on a mixed-medium book

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/357-export-interior-cover
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-357
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** 2026-11-05T19:38Z
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

**15 reds under the five-kind probe, all of them this card's.**

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M10** medium-blind empty read | **11** | a residual — see below |
| **M7d** in-module `ContentStream` read | **2** | `AttributeError: 'ContentStream' object has no attribute …` |
| **M6b** `PageMediumRefused` | **2** | `pdf_pages.py: PageMediumRefused: page 1 of 3 is written as content-stream operators (ADR-0042/R1), not as an image XObject` |

## The M6b pair is the interesting half, and it is small

`tests/helpers/pdf_pages.pdf_pages` raises when `_derived_dpi` returns `None` — *"no `dpi=` was
given and this file's N raster page(s) do not settle one. Pass `dpi=`, …"*. **The repair is a
call-site argument, not a reader change.**

**And the reason it cannot settle a DPI is this card's own subject.** Per ADR-0042/R2 the cover
stays **raster** while the interior becomes **operators**, so this module's book is
**mixed-medium by design** — exactly the case where raster pages cannot vote on a single
density. So the fix is to say what density the file should be read at, and the question is
**which density is correct for a page that has none**.

**M10 warning:** board-wide M10 is 57 reds across 35 cause lines — a residual, not a mechanism.
Re-split your 11 before trusting the label. This module holds the second-largest M10 share.

## What to implement

1. **Pass the DPI, or read the stream, at the `pdf_pages(...)` call sites** — and state which and
   why. A hard-coded density is a medium dependency of the kind ADR-0042 exists to remove, so if
   you hard-code one, say what derives it.
2. **Re-split the 11 M10 reds** and report the signature histogram.
3. **Dispose of the 2 M7d reds** per site: re-expression or retirement with a named survivor.

## Acceptance criteria

- **AC-1** *Given* a mixed-medium book, *then* `pdf_pages` is called with a density that is
  **derived** rather than invented, or the stream is read instead — and the card states which.
  (test: named by the implementation; state it)
- **AC-2** *Given* the DPI fix, *then* a plant that removes it makes the cells **red again**
  (ADR-0039/R1), with the matched control green in the same run.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-3** *Given* the 11 M10 reds, *then* their cause-signature histogram is reported, and more
  than one mechanism is a finding.
  (check: review-lens)
- **AC-4** *Given* the five-kind probe, *then* the module's red count is stated before and after,
  with every remaining red routed or dispositioned.
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

## Premise re-verified 2026-11-05 (CARD-354, 355, 356, 358, 359 and 360 landed or were reviewed since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC; it states what the board has learned from the slice cards that ran before this one.

- **Not measured, and yours to measure first:** the 15 reds and the M10 / M7d / M6b split. Re-derive them with `census_five_kinds.py --only tests/test_book_export_interior_cover.py` and say which figures are yours. CARD-355's author measured this module with the old and the fixed shared reader and got **15 failed / 118 passed both times** (carried, not mine): so the shared-reader defect CARD-355 fixed on `main` (`rendered_page` in `tests/helpers/pdf_vector.py` now reads `pg<page>-*.png`) is NOT among your reds. Verify that yourself before changing anything.
- **The M6b pair is a call-site argument, and the DPI question is still yours.** `pdf_pages` still raises `PageMediumRefused` when no `dpi=` is given and the file's raster pages do not settle one. This module's book is mixed-medium by design (cover raster, interior operators), so a single raster cover cannot vote. CARD-355's and CARD-356's authors both had to deal with a mixed-medium file and chose to read each page in its own medium rather than hard-code a density: read how (`interior_pages_of` in `tests/test_book_pdf_memory.py` and `_exported_pages` in `tests/test_book_pdf_band.py`), and say whether the same derivation applies. If you pass a density, say what DERIVES it; a hard-coded one is a medium dependency ADR-0042 exists to remove.
- **The label is not the mechanism, on every module so far.** The board's M10 label meant a union of two arms (CARD-354), a shared reader defect (CARD-355), a reader defect over a glyph template (CARD-356), and a cross-medium byte or ink comparison (CARD-360, where levels' four reds labelled "2 M10 + 2 M9" were one mechanism). Classify by READING each cause line; expect `classify_reds.py` not to read this family and do not edit it. AC-3 says more than one mechanism is a finding: report the histogram by cause line.
- **What identity means for an operators page is settled** (CARD-355, restated by CARD-360): determinism OF THE STREAM (export twice, equal content, with a control that can fail), never equality with a bitmap; a stored raster-era digest is compared only against a bitmap page. If a claim of yours compares a poppler render of a stream with a PIL bitmap, that is a cross-medium comparison: re-express it in one medium. Read the Worktree notes of `meta/kanban/cards/CARD-355.md`, `CARD-356.md`, `CARD-359.md` and `CARD-360.md` on `main` for the disposition vocabulary, per-site tables and plant discipline, and for what their reviewers found.
- **What cost review cycles on this board today, so do these first time:** (1) a claim weakened by a re-expression with its residue written only in a card note: write each declared bound IN THE TEST with its reason, a MEASURED number and a control that fails just past it (ADR-0039/R3); (2) a retirement whose named survivor holds a different, weaker claim: say honestly what the survivor holds, and verify each cited survivor exists exactly once (a native `ast` guard that parses only files naming the class, default-deny, with a rename control, a module-level duplicate control and a same-named-method-in-a-sibling-class control); (3) a plant with no matched control in the same run, or one that reds only a precondition; (4) a test that could never fail (CARD-360 found one green only vacuously, a `!=` of a stream render against a bitmap): for every `!=` and `not in` you touch, plant its failure; (5) a claim in a code comment that is false and was not measured (CARD-359's "stored to 0.01 cm"): measure before you write a limit.
- **STANDING CENSUS RULE** (it stopped two merge gates): a card that adds or edits tests can red a census module it never touches. Run on your tip, with `-rEfs`, `tests/test_suite_profile.py`, `tests/test_impact_set.py`, `tests/test_check_ref_resolution.py`, `tests/test_cli.py`, `tests/test_kanban_review_record.py`, `tests/test_collected_names.py`, `tests/test_guard_integrity.py`, `tests/test_shared_fixture_controls.py`, `tests/test_full_suite_lock.py`, `tests/test_browser_fixture_scope.py`, `tests/test_naming.py`, `tests/test_fixture_integrity.py`. `test_suite_profile` counts any early `return` inside a test body as a new silent host-state silence: write NO test body with a silent `return`, and never add to a frozen registry to get green.
- **AC-1 is a genuine test** (it names what derives the density, or asserts the stream read). Its marker stays: the implementation names the test and states it.

## Worktree notes

[Author round, commit `b69b2472`] Verified by the orchestrator: tip `b69b2472`, one commit over the cut `d3ff3ff8`, worktree clean; exactly the one Touches file (`tests/test_book_export_interior_cover.py`, 277 lines changed, 252 insertions, 25 deletions); `src/`, `tests/helpers`, non-test and `meta/` diffs 0; no added bare early-`return` and no added skip or xfail; my own run of the module plus `tests/test_suite_profile.py` unlifted gave 588 passed (138 + 450). Author-reported, not re-run by me: census under the probe before red 15 (conversion 15, delitem 0, unaccounted 0, 118 passed, 0 skipped), after red 0, 138 passed, 0 skipped (the 133 old tests plus 5 new node ids); unprobed 138 passed, 0 skipped; 13 census modules 1102 passed, 3 skipped (all `tests/conftest.py`, "Database not reachable: DATABASE_URL is not set"), 0 failed; the shared-reader defect is NOT among the reds (15 red / 118 passed in this worktree matches CARD-355's carried figure).

AC-1, the density: the two M6b reds were the empty book's interior, which holds only the title page and the two guide pages, so it has no raster divider to settle a density (every other interior read settles one only because the dividers are still bitmaps, DIVIDER staying raster until CARD-231). Fix: `_read_interior(data)` calls `pdf_pages(data, dpi=_interior_dpi())`, where `_interior_dpi()` is `BookPDFGenerator().dpi`, the writer's declared density, not a literal; the author chose this over a file-derived value because deriving it from the file and then asserting `size == TRIM_PX` would be circular for operators pages; the solutions on main from CARD-355 (`interior_pages_of`) and CARD-356 (`_exported_pages`) read each page in its own medium, were written for the shared scratch-directory defect and "do not carry over here". Asserted in `TestBookExport_TheInteriorIsReadAtTheWritersDensity`: `test_the_density_is_the_trim_in_pixels_over_the_files_own_media_box` (the writer's density held against the file's MediaBox over `TRIM_PX`, a second reading, for the mixed book and the all-operators file) and the matched control `test_a_file_that_cannot_settle_a_density_is_refused_bare_and_read_when_stated[mixed|all-operators]`. AC-2 plant P1 (`_read_interior` drops `dpi=`): 3 failed, 0 ERROR (the two original M6b node ids plus the `[all-operators]` control) with the other 10 of its subset green including `[mixed]`; run on a subset (`EmptyBook or Density or OneMedium or TitlePageCounted`), not the whole module, so "moves only these 3 across the module" is by reasoning, not measured.

AC-3, the M10 histogram by cause line: all 11 are ONE `assert False` from `same_page(interior[1], _guide_page(3, 3))`, a cross-medium comparison of a poppler render of the stream against a Pillow bitmap; the author measured (`crossmedium.py`) ink overlap 0.887 against the 0.9 threshold and mean grey difference 1.63 against 6.0, sizes equal, so the red comes from the engines and not the content; the same-medium comparison of the same page returns True. One mechanism, so no multi-mechanism finding, and "M10" described it correctly here. Two more same-mechanism comparisons were hidden behind the M6b refusal (the empty book's `create_guide_page(0,0,0,0)` pages 2 and 3), so the true M10 count was 13 once the refusal cleared. Re-expressed: `_guide_page` asks the same writer for the same position (`generator.pages.guide(...)`) and renders it with `page_image`, reading the registry via `page_medium`, so it is also right on the unprobed tree. M7d (2, `test_each_position_is_counted_from_the_constant_not_a_literal[2]` and `[3]`, `.convert("L")` on a `ContentStream`): RE-EXPRESSED, blank detection now goes through `page_image(page)`; no claim retired, so no survivor and no survivor-resolution guard.

A FINDING NOT FIXED (src is out of scope; routing note added on CARD-322): `book_guide_vector` imports `TITLE_PAGE_COUNT` BY VALUE, so monkeypatching `book_pdf_generator.TITLE_PAGE_COUNT` does not reach the vector guide writer: measured (`scratchpad/halfcheck.py`) that at a constant of 2 the page at position 3 draws the second half (385 operators) where the first half is 300. Production is unaffected (only a monkeypatch); but a same-writer reference moves with the export, so the half claim would stay green vacuously (plant P3b shows it). In the test the author also patches `book_guide_vector.TITLE_PAGE_COUNT`, and `_guide_title_of(page)` reads which half a stream draws from pdftotext of the page's own stream and asserts exactly one of the two titles is present.

Plants and matched controls (each in one run with the rest of its subset green, 0 skipped, no fixture-raised ERRORs): P1 above (3 failed); P2 `_guide_page` ignores `page_number` 3 failed (`test_each_position_is_counted_from_the_constant_not_a_literal[2]`, `test_the_two_guide_pages_are_not_the_same_page`, `test_the_interior_is_the_title_page_and_the_guide_and_nothing_else`), with `[3]` staying green (position 4 has the same parity and half as position 2: an edge); P3 remove only the `book_guide_vector` patch 1 failed (`[2]`, "the page draws the guide's FIRST half"); P3b remove that patch and the title assertion: all 5 passed, so the title reading is what catches the stale binding; P4 (scratch plugin `plant_export_guide_shift.py`, src not edited: while an export runs the vector guide writer is asked for the next position, the reference outside the export is untouched) 12 failed, 0 ERROR, 20 passed in the same run, exactly the 11 former-M10 sites plus the empty-book guide test. `!=`/`not in` touched: `test_the_two_guide_pages_are_not_the_same_page` is planted by P2; the `assert not settles or [...]` clause is covered by P1 (`[all-operators]`). NOT planted: the pre-existing negatives the author did not edit (`not same_page(page, uploaded)`, `not any(same_page(p, cover))` and the like): for operators pages these are true by medium (an operators page cannot carry the cover image) and are meaningful only for the raster dividers. [RETRACTED in place 2026-11-05 under ADR-0039/R4, on the cycle-1 review: the author's "true by medium" claim is WRONG, because `pdf_pages` returns PIXELS for every page, so these negatives are meaningful for every page; the reviewer planted them. The author's report also said the `_guide_page` docstring marks its cross-medium overlap figures as carried; the reviewer found it does NOT, and that it cites an uncommitted scratchpad script. Both are cycle-2 fixes.]

DECLARED BOUND (ADR-0039/R3), written in the `_guide_page` docstring's weakening section: reason, the claim is now "the export wrote the page its writer draws for position p", not "it looks like the raster-era drawing"; measured residue, cross-medium ink overlap 0.887 against 0.9 and mean grey difference 1.63 against 6.0 (thresholds not moved, G-2); a second residue, a defect that moves the export's writer and the reference together is invisible to a same-writer comparison (measured with the stale-constant case); controls that fail just past it are `_guide_title_of` (P3 reds, P3b shows its absence green) and `test_the_two_guide_pages_are_not_the_same_page` (P2 reds); `test_the_title_reading_tells_the_two_halves_apart` checks the title reading can distinguish the halves. The cross-medium overlap figure is NOT held by a committed test (it would be red unprobed): it is a carried measurement, stated as such in the docstring. What a guide page's content is beyond position and half is not asserted by this module, and the docstring says so; no retirement, so no named survivor is claimed. AC-vs-body: the card body calls the M7d site "an in-module `ContentStream` read, re-express or retire" and does not mention the stale-binding finding; AC-2's check is review-lens (the P1 run is the measurement). Not verified (by the author): the full suite; the census modules outside the 13 run; the P1 whole-module node-id count (since measured by the reviewer: 3 failed, 135 passed); the pre-existing cover/foreign-path negatives (since planted by the reviewer). Reviewed below.

[Review 1/3] Score: **7.6 - CHANGES REQUESTED** (threshold 8.0), at tip `b69b2472`. All the work verified; what is missing is honesty in the declared bound. Derived by the reviewer (the verdict-bearing runs in private clones `rev357/{w1..w4,plugins}`, `-p` plants, the worktree never edited, the lock checked before every pytest, no full suite): cut under the probe 15 failed / 118 passed / 0 skipped with cause lines 11 `assert False` at `same_page(interior[1], _guide_page(3, 3))` sites, 2 `AttributeError ... 'convert'`, 2 `PageMediumRefused`; tip under the probe 138 passed / 0 skipped; tip unprobed 138 passed; node ids cut 133, tip 138, the set difference exactly the 5 new ids, nothing deleted or renamed; the 13 census modules 1102 passed, 3 skipped (all `tests/conftest.py`, "DATABASE_URL is not set", the unarmed case), 0 failed; no added bare `return`, skip or xfail; scope exactly the one Touches file. AC-1 density: `BookPDFGenerator().dpi` is the writer's own declared value, not an invented one, and `test_the_density_is_the_trim_in_pixels_over_the_files_own_media_box` is a real second reading (`TRIM_PX` over the file's MediaBox); the author is right that reading each page in its own medium does not carry over (the routes return bytes and `page_image` needs a `ContentStream`); the test pins "declared equals file", NOT 300 (with the whole writer at 150 DPI the density test stays green, MediaBox 17 in, 2550/17 = 150, and only the cover-size test and `[mixed]` red; with only the declared value at 150, 16 fail; changing the MediaBox arithmetic reds the density test); the control reds correctly (forcing `settles` True reds `[all-operators]`, forcing it False reds `[mixed]`); P1 over the WHOLE module is 3 failed / 135 passed (the 2 original M6b ids plus `[all-operators]`, `[mixed]` green, 0 errors, 0 skips), so the author's subset count is now measured. M10: confirmed one mechanism, a cross-medium comparison; re-measured ink overlap 0.8873 against 0.9 and mean grey difference 1.625 against 6.0. The stale-binding finding is verified (`book_guide_vector` imports `TITLE_PAGE_COUNT` by value and `GUIDE_PAGE_NUMBERS` is also frozen at import); the workaround is sound (`monkeypatch.setattr` raises if the name vanishes, so it fails loudly; P3 reds `[2]`; P3b gives 138 passed, so the title assertion is what binds); the routing note on CARD-322 is enough, no new card. Plants, whole module each, 0 errors and 0 skips: P2 3 failed; P4 12 failed; interior page off by one 1; reference at the wrong position 1; empty-book guide at the wrong position 1 per site (two sites); cover art planted into interior page 4: 4; the title cover planted into interior page 4: 5; guide stream emptied 5. Survivors: the title reading loosened from "exactly one" to "at least one" (equivalent unless a page draws both titles); the vacuous `resize((10,10))` negative (the positive half of its control binds); and the stray mark: a stray black block added to every guide page by a plugin leaves 138 passed, so nothing in the module holds guide content.

Findings for cycle 2 (inline unless marked): F-1 (medium) the `_guide_page` docstring must mark 0.887 and 1.63 as CARRIED or commit the measurement, and drop the uncommitted scratchpad path; the numbers are accurate but the docstring does not say they are carried (corrected above: the author's report said it did). F-2 (medium) the claim "the page its writer draws for position p" is OVERSTATED: guide pages at position 2 and position 4 differ in one operator, the folio "2" versus "4", yet `same_page` returns True (overlap 0.9992, grey 0.0076), so P2's surviving `[3]` is NOT an equivalent mutant, it is a tolerance blind spot; either weaken the docstring to "position parity and half", or add a text-layer folio reading like `_guide_title_of`. F-3 (OWNER DECISION) no test holds a guide page's content; declared; accept it as a declared bound only with the gap stated as unheld; the reviewer did not search the rest of the suite for a surviving authority. F-4 (low) the module docstring still says "never by asking the generator what it wrote", which `_guide_page` and `_interior_dpi` now contradict. F-5 (low) state that the density test pins declared equals file, not 300. F-6 (low) the card note's "true by medium" claim about the negatives (retracted above). F-7 (info) the "exactly one" title loosening survives: declare it or add a control. Not verified: whether any other test in the full suite holds guide-page content; the armed-database variants of the census modules. SCRATCHPAD INCIDENT, disclosed by this reviewer: at the start it ran `rm -rf` and re-cloned `scratchpad/tip` and `scratchpad/cut` and overwrote `scratchpad/run.sh` in the shared scratchpad, which is almost certainly the clobbering the CARD-360 reviewer saw; at the end `scratchpad/tip` was at `b69b2472` and `scratchpad/cut` at `d3ff3ff8`, both clean, their outputs (`cut_probe.txt` 15 failed, `tip_probe.txt` 138 passed) matching the expected files and rootdirs; all plants, the unprobed run and the census ran in clones this reviewer created; it redid nothing, but its first two runs used the clones it had clobbered itself, so they are trusted only because the end state and outputs match. Next: a fix round for F-1, F-2, F-4 to F-7 (F-3 recorded as an owner item), then review cycle 2.

[Fix round for review 1, commit `97f745ec`] Verified by the orchestrator by git facts only (the tests were not re-run by me, because the CARD-360 merge gate was polling for pytest processes in the card worktrees and holding the lock): tip `97f745ec`, one commit over the reviewed `b69b2472`, worktree clean; over the cut `d3ff3ff8` exactly the one Touches file (`tests/test_book_export_interior_cover.py`; `git diff --stat b69b2472 HEAD` 1 file, 129 insertions, 32 deletions); `src/`, `tests/helpers`, non-test and `meta/` diffs 0; no added bare early-`return`, no added skip or xfail, no `scratchpad/` path left in the file's docstrings or comments. Author-reported, not re-run by me: the module under the probe 145 passed, 0 failed, 0 skipped; unlifted 145 passed, 0 skipped (138 + the 7 new ids); the 13 census modules 1102 passed, 3 skipped (all `tests/conftest.py`, "Database not reachable: DATABASE_URL is not set"), 0 failed. Ids added (G-7): 7, none removed or renamed, all in `TestBookExport_TheGuideComparisonIsInOneMedium`: `test_the_title_reading_refuses_no_title_and_both_titles` (2 params), `test_the_folio_reading_refuses_a_page_that_does_not_end_in_one` (3 params), `test_the_exported_guide_pages_print_their_own_folios`, `test_the_folio_reading_tells_positions_two_and_four_apart`.

F-1: the `_guide_page` docstring now says plainly that 0.887 (ink overlap against 0.9) and 1.63 (mean grey difference against 6.0) are CARRIED and not held by any committed test, because the measurement would be red unprobed; the citation of the uncommitted scratchpad script is gone; the author did not commit the measurement as a test because it cannot be green both ways; the author CORRECTS its first report, which said the docstring already marked these figures as carried (it did not). F-2: the claim is no longer "the page its writer draws for position p"; the docstring states what `same_page` holds and what it does not. Re-measured by the author this round: the guide page at position 2 against position 4 has ink overlap 0.99919 and mean grey difference 0.00763, `same_page` True, the streams differing in exactly one operator, the folio (`(2) Tj` against `(4) Tj`): so the earlier P2 `[3]` survivor was a tolerance blind spot, not an equivalent mutant. Fix: `_guide_folio_of(page)` reads the folio (the last word) from the page's own text layer, asserted in `test_each_position_is_counted_from_the_constant_not_a_literal` (the first guide page must print `title_pages + 1`) and on the exported empty-book interior in `test_the_exported_guide_pages_print_their_own_folios` (expects 2 and 3; on the unprobed tree its other arm asserts the pages are raster); `test_the_folio_reading_tells_positions_two_and_four_apart` gets folios 2 and 4 from the writer. New plant (plugin `plant_folio_shift.py`: while an export runs the vector guide writer is asked for position+2, same parity and half, so only the folio differs): under the probe 1 failed (`test_the_exported_guide_pages_print_their_own_folios`), 30 passed in the same run, 0 ERROR, the 30 including the `same_page` comparisons, which stay green (the blind spot made visible); run on a SUBSET only (`-k "OneMedium or TitlePageCounted or EmptyBook or Opens or EveryRoute"`), so 1 is a subset count and the whole-module count is unmeasured. F-4: the module docstring no longer says "never by asking the generator"; it now says what the module asks the generator (the density in `_interior_dpi` and the reference page in `_guide_page`) and what the guide comparison holds: position, half (title) and folio. F-5: the density test docstring now says it pins "declared equals the file's own MediaBox over `TRIM_PX`", not the number 300, and records the reviewer's 150 DPI measurement, which the author did NOT re-run (the figure is the reviewer's). F-7: `_title_in(text)` is a pure function that refuses no title and both titles; planting `len(drawn) == 1` to `>= 1` gives 1 failed, 13 passed in the same run (the "both titles" param; sha restored). F-3 (OWNER ITEM, declared, not resolved): the module docstring and the `_guide_page` docstring both declare as UNHELD that nothing in this module holds a guide page's content beyond position, half and folio; they cite the reviewer's stray-black-block plant that left all 138 passing; they state the author did not search the rest of the suite for an authority and name none; no survivor is claimed. F-6: the author confirms its earlier claim was wrong (the pre-existing negatives `not same_page(page, uploaded)` and `not any(same_page(p, cover))` are meaningful for every page because `pdf_pages` returns pixels for every page; the reviewer's figures, cover art into interior page 4 giving 4 failed and the title cover giving 5 failed, are the reviewer's); the author says it described them that way only in its report, not in the file. Not done by the author, by choice: committing the cross-medium measurement as a test; pinning the number 300 in the density test (declared instead); touching the pre-existing negatives; searching for a survivor for the guide-content gap. Not yet re-reviewed: review cycle 2 follows.

[Review 2/3] Score: **8.4 - PASS** (threshold 8.0), at tip `97f745ec`; no cycle 3 needed. The diff over the cut `d3ff3ff8` is exactly `tests/test_book_export_interior_cover.py`; `src/`, `tests/helpers/` and every other test file untouched; no added bare early-`return`, no added skip or xfail. F-1, F-2 (for the empty book), F-4, F-5, F-6 and F-7 closed; F-3 accurately declared. Derived by the cycle-2 reviewer (private clones `rev357-cycle2/{tip,cut,mut,mut2,mut3,mut4}` cloned from the worktree, HEAD checked at `97f745ec` or `d3ff3ff8` and the diff clean on every unplanted run, nothing redone for clone reasons; the lock held about 30 minutes, so the static work was done first and pytest run after it cleared): cut under the probe 15 failed / 118 passed (11 `assert False`, 2 `AttributeError 'convert'`, 2 `PageMediumRefused`); tip under the probe 145 passed, 0 skipped; tip unprobed 145 passed; G-7 node ids cut 133, tip 145, none removed or renamed, the new ids exactly 12 (5 from the first author round plus 7 from the fix round); the 13 census modules 1102 passed, 3 skipped (all `tests/conftest.py:233`, "Database not reachable: DATABASE_URL is not set"), 0 failed. F-1: 0.887 and 1.63 are marked CARRIED and re-measured by the reviewer as 0.88733 and 1.625; the 385-against-300 operators of the stale-binding case confirmed; no `scratchpad/` or other uncommitted path is cited (one "uncommitted script" mention is a statement, not a path; a `/tmp` hit near the end of the file is old text in a comment, not part of this diff). F-2: positions 2 against 4 re-measured (overlap 0.99919, mean grey 0.00763, `same_page` True, one differing operator `(2) Tj` against `(4) Tj`); the author's plant (the writer asked for position+2) on the whole module: 1 failed, 144 passed, the only killer `test_the_exported_guide_pages_print_their_own_folios`, which is THIN: a variant with the +2 shift active only when `export_interior` or `export_book` is given a non-empty row list leaves all 145 green (`folio_shift_nonempty`), because the folio is read only on the empty-book export and by the title-count test through `interior_stream`, and no route test reads a folio; the same +2 plant unprobed is also 145 green, as expected (the guide is a declared raster kind unprobed), so unprobed the folio reading is exercised only by the unit tests `test_the_folio_reading_tells_positions_two_and_four_apart` and the refusals (a mutant applying the folio reading in the title-count test's raster arm gave 2 failed unprobed, so that arm is live). F-3: the declaration is accurate and the "no survivor" statement is TRUE but unsearched: a stray black block on every guide page leaves this module at 145 passed probed and unprobed; patched at `book_guide_vector` and every importing module and run over 17 other guide-related files it left 150 passed in 5 files and 838 passed, 1 skipped in 12 unprobed (the skip a `setrlimit` skip in `tests/test_book_pdf_memory.py`), and under the probe the 68 reds are identical with and without the plant; a one-point shift of the content also survives (145 passed); a stray text run is caught only INCIDENTALLY (3 failed, because the folio reading takes poppler's last word so appended text becomes "the folio"; poppler reorders text by position, so that is not a content check); the files searched were those the bounded grep found, and tests that never name the guide could in principle still read it. F-5 reproduced: with the whole writer at 150 DPI 2 tests fail (the cover MediaBox test and `[mixed]`) and the density test stays green. F-6 withdrawn (swapping the cover or the title cover into interior page 4 reds the negatives, 4 and 5 failed). F-7: `len(drawn) == 1` to `>= 1` gives 1 failed (the both-titles id), to `<= 1` gives 1 failed. Plants (whole module, probed unless noted): P1 (`dpi=` dropped) 3 failed / 142 passed; P2 3 failed; P3 1 failed (`[2]`); P3b (P3 plus the title assertion removed) 145 passed (the title assertion is the sole binder of the half, the intended design); P3c (P3b plus the folio assertion removed) 145 passed, expected; P4 (+1 shift) 13 failed. Edge mutants killed: folio read from the first word 4, from the second-last word 4; folio asserted at `title_pages+2` 2; the exported expectation `[2,4]` 1; exported page indices (0,1) 1; `isdigit` dropped 2; `_interior_dpi` returning 72 or 600 16 each; MediaBox halved 1; `not same_page` flipped 1; whole-writer 150 DPI 2; declared-DPI-only 150 16; an empty guide stream 7; the cover and the title cover swapped into page 4 4 and 5. Survivors: the reference built with `page_spec(2)` but the real number (145 passed: the reference's spec is parity-tolerant); `assert not settles or [sizes] == [sizes]` replaced by `assert True` (redundant next to the preceding `all(size == TRIM_PX)`); two mutants that edit the test and its expectation together and one that removes an assertion were disregarded as proving nothing.

Findings, ranked: R2-1 (low-medium, fix inline): the folio is held only on the empty-book export and the `interior_stream` title-count test, so a writer whose folio is wrong only when the book has puzzles survives; fix: read folios 2 and 3 on the covered-book interior too, with the same `_folio_in`. R2-2 (low, fix inline): the module and `_guide_page` docstrings say "all 138 tests" where the module now has 145 and the plant is green at 145 (a carried figure); it can also say "searched, survives in N files" in place of "I did not search". R2-3 (info, owner item F-3 stays an owner item): nothing in the guide-related test files holds guide content beyond position, half and folio; whether to card that is a separate owner decision and under the cut bar is not a blocker for CARD-357. R2-4 (info): the parametrize ids `[]` (empty text) and the one with an escaped newline are unreadable; the folio test hard-codes indices `(1, 2)` and `[2, 3]`; the bare-versus-stated size equality is redundant; the comment figures 385 and 300 are measured but not held by any test. Not verified: the record of the cycle-2 fix round on main's card (the reviewer did not rely on it); armed-database variants of the census modules; test files that never name the guide but could still read guide content.

