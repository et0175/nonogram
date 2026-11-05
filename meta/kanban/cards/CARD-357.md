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

(none yet)
