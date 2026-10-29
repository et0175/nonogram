# CARD-309: The five interior page kinds become operators — each declaration removed by the card that earns it, and ADR-0042/R1 flips when the last one lands

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-298's review cycle 1, F-002, 2026-10-29 — which measured that **no card on the board converts the interior pages at all**. Cut by the orchestrator on owner decision the same day. The work is what CARD-298 was originally cut to do, minus the mechanism CARD-298 kept.
**Idea:** —
**Wave:** 68
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-299, CARD-306
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_guide_vector.py, src/nonogram/admin/book_toc_vector.py, src/nonogram/admin/book_answer_vector.py, src/nonogram/admin/book_puzzle_vector.py, tests/test_book_pdf.py, tests/fixtures/book_baseline_*.json, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
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

## What to implement

1. **One kind at a time, each removal complete.** For each of TITLE, GUIDE, TOC,
   ANSWER and PUZZLE: wire the vector writer into the interior's page walk, delete
   that kind's entry from `_RASTER_DECLARATIONS`, and let `_write_pdf`'s
   representation refusal prove the removal is complete — a kind whose declaration
   is gone but whose page is still a bitmap is **refused**, not shipped. That
   refusal is the mechanism CARD-298 built and it is what makes this card
   incremental rather than all-or-nothing.
2. **The assembly point the layering currently forbids.** `book_guide_vector`,
   `book_toc_vector` and `book_answer_vector` **all import `book_pdf_generator` at
   module level** (`:103`, `:60`, `:62`), while `book_pdf_generator:400` imports
   `book_puzzle_vector`. So the interior's page walk can call the puzzle writer and
   **cannot call the other three without a cycle**. Three of the five kinds need an
   assembly point downstream of all of them, and **it does not exist**. Design it,
   do not work around it: an import-direction violation is a structural guard
   failure in `tests/test_cli.py`, not a style question.
3. **ADR-0042/R1 flips here, and only when the last kind lands.** Not before.
   CARD-298 and CARD-299 each refused this flip on their own initiative and were
   each right: a test asserting "every page is the medium its kind declares" passes
   **while R1 is violated** as long as any interior kind is a declared exception.
   R1's check becomes a live node id in the same commit as the final conversion.
4. **The 21 baselines move here — this is the card that owns the byte-identity
   cost.** It is the scoped, enumerated exception to the standing
   never-regenerate rule, withdrawn from CARD-298 when that card was narrowed.
   Enumerate them file by file in the worktree notes so a reviewer can count them
   without running anything, and record the interior's size and generation time
   with the load average at both ends (CARD-292's AC-6 convention).
5. **Delete CARD-297's `_DECLARED_CLIP_DIVERGENCE` when the answer page converts.**
   Round 1's position, recorded on CARD-298 and CARD-299 and still unchallenged:
   once the answer page is vector there is **one** answer-page writer, and the book
   clips by `/Widths` — the measure the reader's own viewer uses — so the
   declaration becomes a statement about a page nobody prints. **It should be
   deleted by this card, not inherited.** Verify the argument before acting on it;
   it has never been tested against a converted page.

## Acceptance criteria

- **AC-1** (R1 is true and checked): *Given* a written interior, *then* no page of
  the five converted kinds references an image XObject, `_RASTER_DECLARATIONS`
  holds only the cover and (until CARD-231) the divider, and **ADR-0042/R1's
  `check:` is a live node id naming the test that proves it**.
- **AC-2** (each removal is complete, proved by refusal): *Given* a kind whose
  declaration is removed, *then* a bitmap handed in for that kind is **refused by
  the writer**. (**Two mutants per ADR-0039/R1**, one inside the region and one at
  the edge: the last kind converted, and a kind converted while its declaration is
  left behind.)
- **AC-3** (the readers survive): *Given* the converted interior, *then* every test
  module that reads a book interior passes — the 14 modules plus 3 helpers that
  went through `tests/helpers/pdf_pages.py`'s one-image assertion before CARD-299
  converted them. A module that needs a further edit here is a **finding about
  CARD-299's completeness**, to be raised, not absorbed.
- **AC-4** (the baselines move once, enumerated): *Given* the branch, *then* the
  re-recorded baselines are listed file by file in the card, the count is stated,
  and **CON-019's property test and the A4 golden are untouched and green**.
- **AC-5** (the clip divergence is resolved, not inherited): *Given* the converted
  answer page, *then* `_DECLARED_CLIP_DIVERGENCE` is either deleted with the
  measurement that justifies it, or **kept with a new argument that names the
  converted page** — silence is not an option.
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
conditional skip would be an ungated door. If it has been carded by the time this
runs, that card is the owner; if not, raise it rather than absorb it.
