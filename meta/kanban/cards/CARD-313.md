# CARD-313: `test_book_pdf_memory.py` stops measuring a bitmap that is no longer retained — the rewrite its premise has been waiting for a page conversion to justify

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-299's item 5, which that card's round escalated in its first hour with two measurements rather than absorbing it — `scope_gate: on`'s designed route. Cut on owner decision 2026-10-29.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-309
**Touches:** tests/test_book_pdf_memory.py, meta/profiling/adr-0042-migration-census.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is NOT CARD-299's

CARD-299's item 5 said of this file: *"If this turns out to be its own card, say so
and raise it."* Its round did, **in its first hour, before writing any code**, on two
measurements:

1. **ADR-0042/R6's live enumeration does not name this file at all.** R6 names
   `tests/property/test_book_export_interior.py` four times plus two PNG probes. This
   file is not in the rule CARD-299 was delivering.
2. **Its premise does not change until a page converts.** The subject is
   `PAGE_BITMAP_BYTES = 2550 * 3300 * 3` (`:210`) and page-bitmap retention, across
   **34 pixel sites**. CARD-299 changed no `src/` file and converted no page — and
   measured that **all seven `PageKind` members are still RASTER**. The spike's
   headline, interior retention falling **1.00 → 0.000246**, is a measurement of a
   **vector interior that does not exist yet**.

So rewriting it inside CARD-299 would have been writing a test for a state the repo
has not reached. **That is why this card depends on CARD-309** — the card that
actually converts the pages — rather than on CARD-299.

## What to implement

1. **Re-derive the retention figure against a real converted interior.** Do not
   inherit 0.000246 from the spike: measure it, at the commit you measure it on, and
   record the derivation. A number carried across a phase is how this board's figures
   went stale three times in one day.
2. **Decide what the file's subject becomes.** `PAGE_BITMAP_BYTES` is a claim about a
   bitmap page's cost. Once an interior page is a content stream there may be no page
   bitmap to retain, so the question is whether the file measures a **vector** page's
   cost, keeps measuring the **cover** (permanently raster), or is largely retired
   with a named survivor. **Say which, with the measurement.** Per CARD-220's standing
   rule, a test is retired only with a **named survivor**.
2. **The streaming shape must stay guarded.** `test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`
   is a resident-set sentry and it carries AC-2's **executed** half on this box,
   because the `setrlimit(RLIMIT_AS)` cell cannot run here. Whatever the rewrite
   does, the generator must still be prevented from materialising the whole book.
3. **The one skip in this file is load-bearing and must not be made to disappear.**
   `tests/test_book_pdf_memory.py:1297` skips because the kernel refuses
   `setrlimit(RLIMIT_AS, …)` on this machine — *"current limit exceeds maximum
   limit"*. It is **1 of only 2 non-DB skips in the whole suite** and it is honest: it
   says the address-space version of the cap is **not run here**. **Do not delete it
   to tidy the skip count**, and if the rewrite makes it meaningless, say so and
   retire it with its reason recorded.

## Acceptance criteria

- **AC-1** (the figure is measured, not inherited): *Given* a converted interior,
  *then* the retention ratio is re-derived at a named commit with its derivation
  recorded, and the spike's 0.000246 is cited as the **prior** reading rather than
  the current one.
- **AC-2** (the subject is decided and stated): *Given* the rewritten file, *then* it
  says what it now measures and why, and every retired test has a **named survivor**
  (CARD-220's rule).
- **AC-3** (the streaming shape is still caught): *Given* the generator made to
  materialise the whole book, *then* a test reds. (**Two mutants per ADR-0039/R1**,
  one inside the claim and one at its edge.)
- **AC-4** (the skip is handled honestly): *Given* the suite on this box, *then*
  either the `setrlimit` skip is still present with its reason, or it is retired with
  the reason recorded — **never silently absent**. (**gate**: the suite-wide non-DB
  skip count stated before and after, by name.)
- **AC-5** (the 34 pixel sites are accounted for): *Given* the file, *then* every one
  of the 34 pixel-reading sites is either converted, declared out of scope with its
  reason, or gone with its survivor named — derived from the file, not listed here.

## Guardrails

- **G-1: do not lower a memory cap or a corpus minimum to make a test pass.** The
  caps are the subject.
- **G-2: do not delete the `setrlimit` skip to tidy the skip count** (see item 3).
- **G-3: no test retired without a named survivor** (CARD-220).
- **G-4: do not touch the cover's retention claims** — the cover is permanently
  raster (`expires_with: ()`), so a bitmap-cost claim about it stays true.
- **G-5: no test deleted, renamed, skipped or merged except where AC-2/AC-5 retires
  one with its survivor named, and then say so by name.** (**gate**: node-id set
  difference with `-o addopts=''`.)

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — an interior claim is asserted against the content stream (check: review-lens → CARD-312's)
- NFR-008 — the generator streams rather than materialising the book
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; a derived set, and an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **DEAD REF** — verify the substance; see CARD-307)

## Architecture context

- **NFR:** NFR-008
- **ADR:** ADR-0042 (R6's neighbourhood, but not its delivery), ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** no ADR-0042 rule row exists to re-stamp (measured 2026-10-29).

## Worktree notes

- **Triggered by CARD-309, not by CARD-299.** If CARD-309 converts only some kinds,
  this card's subject is partially real — check which kinds are vector before
  deciding the rewrite's shape, and say so.
- CARD-299's round left this file **completely untouched** (54 passed, 1 skipped), so
  there is no partial rewrite to inherit or reconcile.
