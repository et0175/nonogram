# CARD-343: A whole-file `pdf_pages` render comes back blank under the probe while the per-page path yields real pixels in the same run

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** Raised as F-2 by CARD-336's round, 2026-11-04, and routed here at the decompose station on the owner's re-cut instruction. CARD-336's round found it while checking that card's own second UNMEASURED PREMISE, stopped rather than guessing, and said so: "Why a whole-file pdf_pages render comes back blank while puzzle_frame's per-page interior_images path yields real pixel readings in the same run is unmeasured. It is not the frame-centre oracle's, whatever it is, and it needs its own owner." This card is that owner.
**Idea:** —
**Wave:** —
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_guide_page.py, tests/helpers/page_ink.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The observation, and it is an observation rather than a diagnosis

Under `scratchpad/card338/probe_five_kinds.py` (CARD-338's five-kind probe), measured by
CARD-336's round on 2026-11-04:

- `tests/test_book_guide_page.py` reports `AssertionError: only 0 pages carried a measurable
  drawing` — `drawing_of` raises `ValueError` on **every** page, so the placed-edge comparison
  further down is never reached at all.
- An independent scratchpad render of the same book through the same path
  (`pdf_pages(export.interior…)`) under the probe reports `ValueError: the page carries no ink
  at all` for **every** page.
- **In the same probe run**, `tests/test_book_puzzle_frame.py`'s per-page `interior_images`
  path yields real pixel readings and only 4 reds.

So two page-source paths disagree completely about whether there is ink on the page, under one
probe, in one run. **Which one is wrong is not established.** That is this card's question.

**This card's premise is an observation, not a mechanism.** Do not start by fixing anything.
Start by establishing which path is lying and why.

## Why this matters beyond one module

`tests/test_book_guide_page.py` also gains **four unrelated reds** under the five-kind filter
(an `IndexError`, an `assert 0 == 1`, "interior page 2 is not titled the guide's own title",
and "no 20-row puzzle page found"). Whether those are the same cause or four more is unknown.
A blank whole-file render would explain some and not others — which is itself a useful test of
any hypothesis.

CARD-336's round originally inherited a routing of this module's single placed-edge cell on an
arithmetic reading (a 2.9449 px residual against a 2 px bound). **That routing is refuted**:
under the five-kind filter that cell is red at a different line by a different mechanism, and
the arithmetic never applies. The card has been re-cut to drop the module.

## What to implement

1. **Determine which path is correct.** Compare what `pdf_pages` and `interior_images` each
   hand to the ink reader, for the same book, in the same probe run. Derive the divergence;
   do not infer it from the error strings.
2. **State whether the probe causes it.** CARD-338's probe rebinds
   `book_pdf_generator.NO_DOWNSTREAM_WRITERS` to `book_interior_vector.DOWNSTREAM_WRITERS`. A
   plausible reading is that the whole-file path assembles pages the probe leaves vector while
   the per-page path rasterises. **If the probe is the cause, this is a probe finding and the
   instrument's refusal set is incomplete** — CARD-338 built it to refuse by name rather than
   read green over a tree it did not change, so a blank render it does not refuse is a gap in
   that guarantee. Report it to CARD-338's mechanism, do not patch around it.
3. **Then, and only then, decide what the four unrelated reds are.** Same cause or separate;
   say which, with evidence per red.

## Acceptance criteria

- **AC-1** *Given* the two page-source paths, *then* the card states which one yields no ink
  under the probe and **why**, derived rather than inferred from the exception text.
  (evidence: the card's own measurement)
- **AC-2** *Given* the finding, *then* it is attributed: either the probe (a CARD-338
  instrument gap, reported there), the module's own fixture, or the generator. One of the
  three, named, with the measurement that distinguishes it.
  (test: named by the implementation; state it)
- **AC-3** *Given* the four unrelated reds in `tests/test_book_guide_page.py`, *then* each is
  classified as the same cause or its own, with per-red evidence, and anything not closed here
  is carded with an owner.
  (check: review-lens)
- **AC-4** *Given* the fix, *then* a plant that makes a page genuinely blank still **reds** —
  the "no ink" reading must remain able to fail for the claim as stated (ADR-0039/R1).
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — **Do not rebuild CARD-338's probe.** Run it. If it is the cause, that is a finding
  reported to the mechanism, not a licence to fork the instrument. Three cards describing one
  instrument is how CARD-309 happened.
- **G-2** — No tolerance is widened to make a blank page acceptable. A page with no ink is a
  real failure; the question is whether this page has no ink.
- **G-3** — No new runtime dependency (ADR-0006/R1).
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.
- **G-5** — **G-8 standing: do not connect to the production database.** `nonogram_poc` is
  never created, dropped, connected to or truncated.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived, not hand-written; where none exists it defaults to
  deny (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
