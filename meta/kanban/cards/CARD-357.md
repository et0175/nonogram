# CARD-357: `tests/test_book_export_interior_cover.py` — 15 reds, and 2 are a DPI nobody passed on a mixed-medium book

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** —
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
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
> the lift: the spy exempted **0** faces while the stream exempted **644** by the writer's own
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
> *set-comparison*, not an empty read. *Disposition: expect this to be the expensive one — B had an
> authority to fall back on and C had none for three of five kinds.*
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
  (test: named by the implementation; state it)
- **AC-3** *Given* the 11 M10 reds, *then* their cause-signature histogram is reported, and more
  than one mechanism is a finding.
  (check: review-lens)
- **AC-4** *Given* the five-kind probe, *then* the module's red count is stated before and after,
  with every remaining red routed or dispositioned.
  (test: named by the implementation; state it)

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
