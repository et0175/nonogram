# CARD-351: `Drawing.framed` reports False on 94 of 136 framed answer pages, and the module that reads it contradicts itself about which fields are safe

**Status:** skipped
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as F-3 by CARD-336's implementation round, 2026-11-04, and carded on the owner's instruction. The round met it the hard way: its FIRST build of the frame-centre oracle gated on `drawing.framed` and raised there, so it had to find out why before it could ship. It then routed around the field rather than fixing it, which was correct for that card's scope and leaves this.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** CARD-336
**Touches:** tests/helpers/page_ink.py, tests/property/test_book_pdf_geometry.py
**Review score:** n/a — **RETIRED** on the owner's 2026-11-09 board triage. No work is owed here.
**Started:** —
**Closed:** 2026-11-09
**Actual:** none — retired (see the closing note).
**Merge commit:** —
**Blocked by:** —

## Part 1 — the field is wrong on the majority of the pages it describes

`tests/helpers/page_ink.py` declares `framed: bool = False`, documented as *"Whether the
drawing is closed off by a book page's frame"*.

**Measured by CARD-336's round over `tests/property/test_book_pdf_geometry.py`'s own corpus:
94 of 136 answer pages report `framed=False`, with `columns`/`rows` of 2 — on pages that
carry a frame.**

**Re-derive that before implementing.** The instrument is
`scratchpad/card336/probe_framed.py`, committed by that round — **run it, do not rebuild it**,
and if the ratio differs, that is the finding. It is a dated reading over one module's corpus
and does not claim to be the whole tree; **say what population you measured**.

A default of `False` on a boolean that means "I could not tell" is the shape that makes this
survivable: every consumer that reads it as "this page has no frame" gets a plausible answer.
That is the same false-green direction `_BOARD_STATUSES` defaults *against*, one file over.

**What CARD-336 did instead, and why this card is not just "fix the field":** the shipped
oracle reads only `left`, `top` and `grid_bottom` — the set that module declares safe on either
page kind — and **derives the frame structurally**: the leftmost full-height rule must hold
`Drawing.left`, which also rejects an unframed drawing without being told. So a working
alternative to the field already exists in the tree and is worth reading before you decide
whether `framed` should be repaired, derived, or retired.

## Part 2 — the module contradicts itself about `.cell`, in the same file

Verified at the decompose station, both present on `main`:

- one passage states that `.cell` and its neighbours **"are safe on either kind and are what
  this test actually needs"**
- about a hundred lines later, another states **"(`page_ink.py`'s own caveat: unsafe on a
  revealed answer page)"** about the same field

So the module asserts both, and a reader meets whichever comes first. This is the
CARD-261 shape — two copies of one claim, drifted — and the precedent there was to **retire the
duplicate to one checkable place** rather than reconcile the wording.

**Which one is true is the card's question, not its premise.** Measure it.

## What to implement

1. **Establish what `framed` can actually be computed from**, and decide between three
   outcomes, saying which and why the others are wrong:
   - **repair** it, so it reports the frame correctly on both page kinds;
   - **derive** it, replacing the stored flag with the structural reading CARD-336 shipped
     (the leftmost full-height rule holding `Drawing.left`);
   - **retire** it, if no consumer needs a flag once the structural reading exists — and then
     the field goes, rather than staying as a trap with a comment.
   **A default that means "could not tell" is not one of the three.** If the answer is genuinely
   unknowable for some pages, it must be representable as unknown and must **fail loudly** at
   the point of use (ADR-0038/R8), not read as `False`.
2. **Derive the consumer set.** Who reads `framed`? Enumerate by `ast`, not grep, and report the
   count. The fix's shape depends on it, and a retirement is only safe once the set is known.
3. **Settle the `.cell` contradiction** by measurement, then retire the losing copy to one
   place — CARD-261's precedent — rather than editing both to agree.
4. **Do not re-expand CARD-336's oracle.** It reads three fields deliberately. If this card
   makes more fields safe, that is a finding to report and a possible follow-up, not a
   widening to perform here.

## Acceptance criteria

- **AC-1** *Given* the answer-page corpus, *then* `framed` is correct on every page, or is
  derived, or is gone — and the card states which, with the measured population and the
  instrument that produced it.
  (test: named by the implementation; state it)
- **AC-2** *Given* a page whose frame state cannot be determined, *then* it **fails loudly**
  rather than defaulting to `False` (ADR-0038/R8, and ADR-0039/R2's deny-by-default). If no
  such page exists in the corpus, say so and say how you established it.
  (test: named by the implementation; state it)
- **AC-3** *Given* the consumer set of `framed`, *then* it is **derived** by `ast` rather than
  listed, its size is stated, and every consumer still holds after the change.
  (test: named by the implementation; state it)
- **AC-4** *Given* the `.cell` safety claim, *then* the module states it **once**, the statement
  is the measured one, and the losing copy is retired rather than reworded.
  (check: review-lens)
- **AC-5** *Given* the change, *then* `TestEdgeOffset_ThePixelOraclesStillReadPixels` is green
  **unmodified** — ADR-0042/R6 exempts the independent pixel oracles by name and CLAUDE.md
  requires the cross-check they provide.
  (test: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)
- **AC-6** *Given* a plant that flips the frame state of one page, *then* something **reds** —
  whatever replaces `framed` must be load-bearing in a way a test can see (ADR-0039/R1). If
  nothing reds, the field was dead and should be deleted, which is itself a finding.
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — No `src/` change. This is a test helper's model of a page, not the generator.
- **G-2** — Do not convert the raster oracles. AC-5 is the guard.
- **G-3** — Do not reconcile the two `.cell` claims by editing both to agree. Measure, keep one,
  retire the other; two copies of a claim is the defect (CARD-261).
- **G-4** — No new runtime dependency (ADR-0006/R1).
- **G-5** — Take no timing measurements and report no durations. Note this module carries a node
  id that exceeds the project's **120 s per-test hang guard** under the five-kind probe
  (CARD-336's F-9) — a known condition, not yours.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). Never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, and never
  redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection.

## System contract

- ADR-0038/R8 — tests fail or skip loudly, never silently (check: review-lens)
- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where
  none exists it defaults to **deny** (check: review-lens)
- ADR-0042/R6 — the independent pixel oracles are exempt from the conversion by name
  (check: `TestEdgeOffset_ThePixelOraclesStillReadPixels`)

## RETIRED 2026-11-09 — board triage

Subject gone: framed answer pages no longer exist (vector answer pages, `BOOK_PUZZLE_FRAME = False`), and no test reads `Drawing.framed`. The dead frame helpers in tests/helpers/page_ink.py are noted on CARD-344.
