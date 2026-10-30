# CARD-329: The one-image reader learns the content stream — AC-3's real content, separated from the three causes that were not readers

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-309's implementation round, 2026-10-30 — cause 1 of the four that blocked its AC-1, and **the only one of them that is actually a PDF reader**. Its AC-3 was written as though all of the breakage were this, which is why the card could not close.
**Idea:** —
**Wave:** —
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/helpers/pdf_pages.py, tests/test_book_pdf.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-309's AC-3 said *"every test module that reads a book interior passes — the 12
test modules that import `tests/helpers/pdf_pages.py`'s one-image reader"*. When the
conversion was implemented, 22 modules broke — and **root-causing them showed only
one cause was a reader**: `pdf_pages.py`'s one-image reader raising
`KeyError: b'XObject'` on a page that has no image XObject because it is now
operators. The other three causes were independent pixel oracles (**CARD-330**), an
accounting instrument monkeypatching a raster drawing site that a vector page never
calls (**CARD-331**), and frozen AST censuses CARD-309 re-derived itself.

**This card is cause 1 alone, and it is small.** Separating it is the point: bundled
with the other three it was unclosable, and the bundling is what made CARD-309 look
like a 1-day card.

## The populations, measured — and AC-3's blind spot, which this card inherits

CARD-309's round derived both by AST (`derive_readers.py`) and the figures are the
ones to re-derive here:

- **Population A = 12 modules** that import the one-image reader itself. This
  reproduces CARD-309's AC-3 exactly. (Its earlier figure of "14 modules plus 3
  helpers" did **not** reproduce: 18 files *mention* the string, 14 import *something*
  from the helper, and only 12 import the reader. `tests/helpers/book_corpus.py`
  imports only `pdf_page_count`, `tests/test_book_toc.py` only `same_page`, and
  `tests/property/test_book_pdf_geometry.py` imports it **zero** times — matching a
  grep only because three of its node ids end in `_pdf_pages`. A mention count is
  not a reader count.)
- **Population B \ A = 9 modules** that never import the reader but reach the same
  hazard through `.interior()` / `.interior_pages()` and use the returned pages as
  images — invisible to A's derivation. CARD-309 named 8 and the round found a 9th
  (`tests/helpers/book_corpus.py`).

**Both populations are in scope.** Per ADR-0039/R2 a module the walk cannot classify
is a **FAILURE**, not a silent pass.

## What to implement

1. **Give the one-image reader a medium-aware path.** A page that is operators has no
   image XObject; the reader must either read the stream or say clearly that the page
   is not a bitmap — **decide which, and state why**. A `KeyError` on a legal page is
   the current behaviour and is the defect.
2. **Keep it a reader, not an oracle.** `pdf_pages.py` is a convenience reader used by
   assertions; `tests/helpers/page_ink.py` holds the independent pixel oracles and is
   **CARD-330's, not this card's** (G-2). Do not fold them together — they exist
   separately on purpose.
3. **Classify population B per module, don't convert it wholesale.** Nine modules
   reach the hazard by a different road. For each, derive whether this card's change
   is enough or whether it needs its own edit, and **say which per module**. A module
   that needs more is a finding about scope, to be raised.
4. **Do not convert any page.** This card makes the readers survive a conversion that
   CARD-322 performs. It can be verified against a page written as operators by a
   test fixture without changing any production medium (CARD-309's branch shows the
   assembly point is already injectable for exactly this).

## Acceptance criteria

- **AC-1** (the reader survives an operators page): *Given* an interior page written
  as content-stream operators, *then* the one-image reader returns a usable result or
  refuses with a message naming the medium — **never `KeyError: b'XObject'`**. (test:
  `TestPdfPagesReader_AnOperatorsPageIsNotAKeyError`)
- **AC-2** (the reader still works on raster): *Given* a raster page — the cover and
  the divider stay raster by ADR-0042/R2 — *then* the reader behaves exactly as
  before, byte for byte in its result. (test:
  `TestPdfPagesReader_ARasterPageIsUnchanged`)
- **AC-3** (both populations are derived, not listed): *Given* the tree, *then* the
  card records population A and population B\A **derived by AST** with their counts,
  and every module is classified — nothing unclassified (ADR-0039/R2). The expected
  counts re-derive CARD-309's: **A = 12**, **B\A = 9**. A different number is a
  finding, and the derivation is what is asserted, not the number. (test:
  `TestPdfPagesReader_BothReaderPopulationsAreDerived`)
- **AC-4** (every reader in both populations passes): *Given* the change, *then* all
  21 modules pass, with **every skip attributed by name** — this suite's skips are
  `DATABASE_URL`-gated and the browser fixtures refuse loudly without Chromium
  (ADR-0038/R8), so green-with-skips must not read as verified. (test: the modules
  themselves, run by node id with `-o addopts=''`)
- **AC-5** (the change can fail): **Two mutants** — one that makes the reader return
  a wrong page for an operators page, one at the edge that makes it mis-handle the
  raster path — both killed. (evidence: the mutant table in `## Worktree notes`)

## Guardrails

- **G-1: convert no page and flip no rule.** CARD-322 owns the conversions and
  ADR-0042/R1; CARD-312 owns R6's flip.
- **G-2: do not touch `tests/helpers/page_ink.py`.** Its `drawing_of` and `two_up_ink`
  are the independent pixel oracles and are **CARD-330's** subject. Folding a reader
  and an oracle together destroys the cross-check CLAUDE.md requires.
- **G-3: do not touch `tests/test_book_difficulty_dots.py` or
  `tests/helpers/round_ink.py`** — **CARD-331's**.
- **G-4: do not lower a corpus minimum** and regenerate nothing under
  `tests/fixtures/**`. No baseline moves in this card.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference with `-o addopts=''`).
- **G-6: do not edit `src/nonogram/admin/**`.** CARD-309's worktree is open on
  `book_pdf_generator.py` and `book_interior_vector.py`; this card is test-side only
  and its `Touches` says so.
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0042/R2 — a raster page is declared with a reason; the cover and divider stay raster, which is why AC-2 exists (check: CARD-298's derived guard)
- ADR-0039/R2 — a guard's set is derived and an unanalysable shape is a FAILURE (check: AC-3)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-5's mutant pair)
- ADR-0038/R8 — a browser test refuses LOUDLY when Chromium is absent, never skips green (check: AC-4's skip attribution)
- CON-020 — the 10 pt interior type floor; CARD-314 marked the clue digits so the exemption survives by the mark rather than by the size (check: CARD-299's re-expressed test)

## Architecture context

- **FR:** FR-030, FR-032, FR-040
- **ADR:** ADR-0042/R2, R6, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** not updated by this card

## Worktree notes

- **[It is cause 1 of four, and the only reader]** The other three are CARD-330 (the
  pixel oracles and the 0.169 mm question), CARD-331 (the difficulty-dot accounting
  instrument) and a frozen-census re-derivation CARD-309 already completed. Keeping
  them apart is what makes each closable.
- **[Re-derive the two populations; do not trust the numbers above]** 12 and 9 are
  CARD-309's round's figures, and that round corrected an earlier "14 plus 3" that did
  not reproduce. A mention count is not a reader count — the lesson is in AC-3.
