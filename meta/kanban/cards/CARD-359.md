# CARD-359: The `page_ink` reader meets a content stream — 6 reds, one cause signature, four modules nobody else touches

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/359-page-ink-reader
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-359
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_divider_pages_option.py, tests/property/test_book_pairing.py, tests/test_book_proof_pages.py, tests/property/test_book_export_interior.py
**Review score:** —
**Started:** 2026-11-05T16:07Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The population, from CARD-337's cross-tab

**6 reds, and all six print the SAME line** — which makes this the cleanest card of the set:

```
page_ink.py: AttributeError: 'ContentStream' object has no attribute 'convert'
```

| module | M7 reds | exclusively this card's? |
|---|---|---|
| `tests/test_book_divider_pages_option.py` | 3 | **yes** |
| `tests/property/test_book_pairing.py` | 1 | **yes** |
| `tests/test_book_proof_pages.py` | 1 | **yes** |
| `tests/property/test_book_export_interior.py` | 1 | **no** — CARD-322 holds its other 6 (M1 5, M2 1) |

**One mechanism, one signature, three exclusive modules.** The only shared file is
`property/test_book_export_interior.py`, where CARD-322 owns 6 of the 7 reds — so **this card
and CARD-322 must not run concurrently**, and CARD-322 runs last by design anyway.

## What this actually is

`tests/helpers/page_ink.py`'s reader is handed a page and calls `.convert(...)` on it. On a
vector page that object is a `ContentStream`, which has no `convert`. **The reader is
medium-blind at the point of the call** — it does not ask what it was given.

**CARD-336 built the precedent for the answer**: its `frame_centre_of` reads a boundary in
**both** media and holds no medium constant, and `TestEdgeOffset_ThePixelOraclesStillReadPixels`
keeps the raster oracles reading pixels byte for byte. ADR-0042/R6 exempts those independent
pixel oracles **by name**, so the route here is not to convert them — it is to make the call
site state which medium it needs, or to re-express the claim against the stream.

**Do not convert `page_ink.py`'s raster oracles.** That is CARD-336's AC-2 and CLAUDE.md's
cross-check requirement, and this card's `Touches` deliberately excludes `page_ink.py` itself.

## What to implement

1. **Decide, per call site, whether the claim needs pixels or needs a coordinate.** Four sites,
   one signature — if they split, that is a finding.
2. Where a claim needs pixels on a page that has none, **retire it with a named survivor**
   (ADR-0042/R6). Where it needs a coordinate, re-express against the stream.
3. **Do not edit `tests/helpers/page_ink.py`** — not in `Touches`, and its oracles are exempt by
   name. If the honest fix requires changing it, that is a finding and a routing.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* all four modules' M7 reds are closed or carry a
  stated ADR-0042/R6 disposition, and the count is stated before and after.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-2** *Given* the four call sites, *then* the card states per site whether the claim needs
  pixels or a coordinate — and if they are not all the same, says so.
  (check: review-lens)
- **AC-3** *Given* `tests/helpers/page_ink.py`, *then* it is **unchanged** (`git diff` empty) and
  `TestEdgeOffset_ThePixelOraclesStillReadPixels` is green **unmodified**.
  (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)
- **AC-4** *Given* `property/test_book_export_interior.py`, *then* its 6 CARD-322 reds (M1 5,
  M2 1) are **still present and attributed**, not absorbed.
  (check: review-lens — the claim is that six REDS in a module this card does not own are still red under the
  probe; a committed test cannot assert a red, and a census count is an instrument run whose instruments live
  in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05,
  the same disposition CARD-358's F-004 gave the sibling cards' markers.)
- **AC-5** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
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

## Premise re-verified 2026-11-05 (CARD-354, CARD-355 and CARD-324 landed since this card was written)

Read against current `main`, by the orchestrator. Nothing here changes an AC except the AC-4 marker restated above.

- **Not measured, and yours to measure first:** the six reds and their one signature. Re-derive them with
  `census_five_kinds.py --only <module>` for each of the four modules before implementing anything, and say which
  figures are yours. The signature was last read by CARD-337's round.
- **The shared-reader defect is FIXED on `main`** (CARD-355, merge `e4849464`: `rendered_page` in
  `tests/helpers/pdf_vector.py` now reads the page it was asked for, where it used to return the first
  `page-*.png` in a shared directory). Two of your four modules import `pdf_pages`
  (`tests/test_book_proof_pages.py` and `tests/property/test_book_export_interior.py`). The CARD-355 author measured
  both under the probe, old helper against fixed: **no change in either** (`test_book_proof_pages` 1 failed and
  `property/test_book_export_interior` 7 failed, both before and after; carried, not mine). So these M7 reds are
  not that defect. It does mean a vector page you read through `pdf_pages` after the first now reads as itself, so
  re-check any claim in these modules that was green while reading a vector page through it.
- **The label is not the mechanism, twice over.** CARD-355 and CARD-356 each found that their M10 and M7 buckets were a
  reader defect plus a template, and that the classifier's rules key on a failure shape or a string, not a cause.
  Here the single signature `page_ink.py: AttributeError: 'ContentStream' object has no attribute 'convert'` is a
  better key than most, but classify per call site by reading it, not by the label, and expect `classify_reds.py`
  not to read this family (it was not filter-agnostic and CARD-338 is closed; do not edit it).
- **`page_ink` appears on 1 + 1 + 3 + 1 LINES of your four modules** (`grep -c`, so imports and comments count:
  `test_book_divider_pages_option` 1, `property/test_book_pairing` 1, `test_book_proof_pages` 3,
  `property/test_book_export_interior` 1). That is a count of mentions, not of call sites: read each to see whether it
  is a call, an import or a comment before you say "four sites". The card says four sites; the mention count is six.
  Reconciling the two is the first thing to do (AC-2).
- **AC-3's test is in a file this card does not touch.** `TestEdgeOffset_ThePixelOraclesStillReadPixels` lives in
  `tests/test_book_pdf.py`, not in `Touches`: run it unmodified, as the AC says, and do not edit that file.
- **Sequencing stands:** `tests/property/test_book_export_interior.py` is shared with CARD-322, which runs last and
  must not run concurrently with this card.
- **Precedent for the disposition vocabulary:** CARD-355 and CARD-356 each landed with per-site tables of
  re-expression versus retirement-with-named-survivor, a stated-after-the-fact census, and plants with matched
  controls. Read their records on `main` (`meta/kanban/cards/CARD-355.md`, `CARD-356.md`) before writing yours.

## Worktree notes

(none yet)
