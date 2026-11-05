# CARD-356: `tests/test_book_pdf_band.py` — 25 reds across four mechanisms, and two of its claims the seam BREAKS

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** architectural
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
**Touches:** tests/test_book_pdf_band.py
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

**26 reds under the five-kind probe; this card owns 25.** The other is **M3b** —
`book_pdf_generator.py: RuntimeError: … 'Χιονονιφάδα' (U+03A7) is not in the interior's cp1252
encoding` — a **product behaviour change** that only appears once the page is drawn as
operators. It is **CARD-322's** and G-1 forbids this card from touching it.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M7d** in-module `ContentStream` read | **11** | `AttributeError: 'ContentStream' object has no attribute {'width'\|'tobytes'\|'crop'\|'convert'}` |
| **M10** medium-blind empty read | **6** | a residual — see below |
| **M7** `page_ink` read | **6** | `page_ink.py: AttributeError: 'ContentStream' object has no attribute 'convert'` |
| **M11** fixture write-counter | **2** | `ERROR at setup: assert 5 == (14 + 1)` |

**This is the most contended file in the family** — before module-slicing it would have needed
five separate cards to edit it, which is why the partition axis was changed.

## Two claims where the seam is the CAUSE, not the repair

Measured by CARD-337's round, by planting the `interior_images` seam and reading the survivors:

- **`test_the_rules_are_pure_black_and_not_anti_aliased`** asserts `greys <= {0, 255}` and reads
  **`[0, 89, 255]`** after the seam, because **poppler anti-aliases a vector rule**. The seam
  does not fail to fix it; the seam causes it.
- **`test_every_fifth_rule_is_wider_than_every_rule_between_them`** fails on the raster thin-rule
  floor, and **its own docstring says it measures "the RASTER path's floor, which is what this
  page is drawn on"**.

**Both are medium-specific claims, and ADR-0042/R6 disposal is the only route** — re-express
against the content stream, or retire with a named survivor. **A card that applies the seam here
without deciding these two makes the module worse.**

## Two further measured facts about this module

- **The seam closes 7 of its 26 reds (27%)**, measured: 26 → 19 with the seam planted,
  `0 skipped` both runs, SHA-256 identical after restore. CARD-329's comparable ratio was 80%.
- **Byte-identity reds APPEAR after the seam.** The unplanted cross-tab shows **zero** M9 here;
  the planted survivors show **three**. So this module's post-repair mechanism census differs
  from its pre-repair one, and **you must re-census after your repair, not only before.** That
  is also why CARD-337's old AC-2 enumeration ("byte identity is `pdf_levels` and `pdf_two_up`")
  was incomplete before it started.
- ~8 of the survivors are the module's **glyph-template text search**, trained on the raster
  font. A different mechanism again, and unnamed by any card.

## What to implement

1. **Decide the two medium-specific claims first** (anti-aliasing purity, raster rule floor).
   Nothing else in this module is safe to touch until they have a disposition.
2. Apply the seam **only** where it does not break a claim, and say where that is.
3. **Re-census after the repair** and report what appeared that was not there before.
4. Dispose of M7, M7d, M10 and M11 per site, stating re-expression or retirement-with-survivor.

## Acceptance criteria

- **AC-1** *Given* the two medium-specific claims, *then* each carries a stated disposition —
  re-expressed against the stream, or retired with a **named survivor** — asserted rather than
  commented.
  (check: review-lens)
- **AC-2** *Given* the repair, *then* the module is re-censused **after** it, and any mechanism
  that appeared post-repair is reported and routed.
  (test: named by the implementation; state it)
- **AC-3** *Given* the five-kind probe, *then* the red count is stated before and after, and the
  M3b product red is **still present and attributed to CARD-322**, not absorbed.
  (test: named by the implementation; state it)
- **AC-4** *Given* each repaired site, *then* a plant re-breaks it, matched control green in the
  same run, `0 skipped`, and the node-id count each plant moves is stated.
  (test: named by the implementation; state it)
- **AC-5** *Given* the glyph-template text search, *then* it is either dispositioned here or
  named with an owner — it is a mechanism no card currently holds.
  (check: review-lens)

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
