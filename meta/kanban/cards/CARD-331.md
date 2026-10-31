# CARD-331: The difficulty-dot accounting instrument measures a page the product will stop drawing — it needs a vector twin, and nobody owned that

**Status:** in_progress
**Priority:** P1 <!-- RAISED P2 -> P1 2026-10-30, same reason as CARD-329: one of the three prerequisites of CARD-322, and the only one of CARD-309's four causes that had no owner at all before today. -->
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/331-difficulty-dot-instrument-vector`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-331
**Source:** CARD-309's implementation round, 2026-10-30 — cause 3 of the four that blocked its AC-1, and the round's own words about it: *"its vector twin is carded nowhere."* It was the one cause with no owner anywhere on the board.
**Idea:** —
**Wave:** 71 <!-- STAMPED 2026-10-31 at dispatch, opening wave 71 on the owner's pinned order. Measured free of CARD-317: tests/test_book_difficulty_dots.py + tests/helpers/round_ink.py against requirements.yml + trace.yml + two ADRs -- intersection EMPTY. Also free of CARD-329, which waits only because the cap is 2. One of CARD-322's four dependencies. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_difficulty_dots.py, tests/helpers/round_ink.py
**Review score:** —
**Started:** 2026-10-31T02:39:21+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_book_difficulty_dots.py` with `tests/helpers/round_ink.py` accounts for
the difficulty dots on a puzzle page — **27 assertion cells**, measured by CARD-309's
round. The way it does it is the problem:

- it **monkeypatches `_draw_difficulty_dots`**, the *raster* drawing site, and
- it keys its accounting on **page-image identity**.

On a vector puzzle page that site **is never called**. So this is not an instrument
reading the wrong medium — which is CARD-329's and CARD-330's class of problem. It is
an instrument **measuring a page the product no longer draws**: once the puzzle page
converts, every one of those 27 cells passes or fails for reasons unrelated to
whether the dots are right, because the mechanism it hooks is dead code on that page.

**And that is the quiet half.** A monkeypatch on a function nobody calls does not
error — it simply never fires, and an accounting that never fires can read as
agreement. Per ADR-0039/R2 the right outcome is a **FAILURE**, not a silent pass, and
the current shape gives the silent pass.

**Nothing on the board owned this.** CARD-312 partitions the 321 pixel-reading sites
and would classify this one, but classifying is not building the twin. CARD-322
converts the pages. CARD-299 was test-side but is done. It surfaced only because
CARD-309 implemented the conversion and read the failures per module.

## What to implement

1. **Decide what the dots' claim actually is**, independent of how it is currently
   measured: that the right number of dots appear, at the right place, at the right
   size, for a given difficulty. Write that down first — the existing instrument's
   shape has been standing in for the claim, and a twin built from the shape rather
   than the claim inherits the coupling.
2. **Build the vector-medium accounting.** On a page written as operators the dots
   are drawing operators in the content stream; account for them there, per
   ADR-0042/R6. **Do not monkeypatch a drawing site to do it** — a hook on a
   production function is what tied the current instrument to one medium.
3. **Keep the raster arm working and keep it honest.** The cover and divider stay
   raster (ADR-0042/R2), and the raster puzzle page still exists until CARD-322
   lands. Both arms must be live, and **each must be able to fail on its own
   medium** — an arm that silently no-ops is the defect this card is about.
4. **Make the dead-mechanism case loud.** If a future page's medium changes under
   this instrument again, it must **red**, not pass. That is the card's standing
   contribution and it is AC-4.

## Acceptance criteria

- **AC-1** (the claim is stated before it is measured): *Given* the branch, *then*
  the dots' claim is written in the test module in terms of **what must be true of
  the page** — count, placement, size, per difficulty — not in terms of which
  function was called. (test: `TestDifficultyDots_TheClaimIsAboutThePageNotTheCall`)
- **AC-2** (the vector arm accounts for real dots): *Given* a puzzle page written as
  operators, *then* the dots are accounted from the **content stream** and the 27
  cells' equivalents hold — with the count derived, not listed. (test:
  `TestDifficultyDots_TheVectorArmReadsTheStream`)
- **AC-3** (the raster arm still holds): *Given* a raster puzzle page, *then* the
  existing accounting holds unchanged — and **without a monkeypatch on a production
  drawing site**, or with the monkeypatch's removal justified in one line if it must
  stay. (test: `TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct`)
- **AC-4** (a dead mechanism REDS — this is the card's point): *Given* an instrument
  arm whose mechanism the page no longer exercises, *then* the suite **fails** rather
  than passing quietly. **Two mutants, and they are the deliverable:** one that makes
  the vector arm's accounting source dead (it must red), and one at the edge that
  makes the raster arm's dead (it must red too). A guard that only catches one side
  catches none of the real cases. (test:
  `TestDifficultyDots_AnArmWhoseMechanismIsDeadFails`)
- **AC-5** (both arms can fail on their own medium): *Given* each arm, *then* a wrong
  dot count on that medium reds **that** arm — measured per assertion, because a test
  short-circuits at its first failing assert and a surviving mutant looks identical to
  a never-reached one. (evidence: the per-assertion table in `## Worktree notes`)
- **AC-6** (no page converted): *Given* the branch, *then* no interior page's medium
  changed and `_RASTER_DECLARATIONS` is untouched — the vector arm is verified against
  a page a fixture writes as operators, which the assembly point already makes
  injectable. (test: the existing `test_no_declaration_outlives_the_cards_that_remove_it`, unmodified)

## Guardrails

- **G-1: do not convert any page and flip no rule.** CARD-322 owns the conversions,
  CARD-312 owns R6's flip.
- **G-2: do not touch `tests/helpers/pdf_pages.py`** — **CARD-329's** — or
  `tests/helpers/page_ink.py` — **CARD-330's**. Three cards, three instruments, and
  they were tangled once already.
- **G-3: do not edit `src/nonogram/admin/**`.** If the dots' production drawing is
  wrong on either medium, **stop and raise it**: that is a writer defect with its own
  baselines, and CARD-309's worktree is open on those files.
- **G-4: do not lower a corpus minimum** and regenerate nothing under
  `tests/fixtures/**`.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference with `-o addopts=''`). The 27 cells may be
  **re-expressed**, but the node-id set is pinned — if a cell must go, that is an
  escalation, not an edit.
- **G-6: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0042/R2 — a raster page is declared with a reason, which is why the raster arm stays (check: CARD-298's derived guard)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-4, AC-5 — a silently no-op arm is a claim with no control)
- ADR-0039/R2 — an unanalysable shape is a FAILURE, never a silent pass (check: AC-4, which is this rule applied to a dead monkeypatch)
- COMP-009 — the book production component (check: review-lens)

## Architecture context

- **FR:** FR-030, FR-032, FR-040
- **ADR:** ADR-0042/R2, R6, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** not updated by this card

## Worktree notes

- **[Why this was invisible]** A monkeypatch on a function the page never calls does
  not error — it never fires. So the failure mode is a **silent pass**, and no gate
  could see it until a card actually converted the page and read the failures per
  module. CARD-309's round did that and named it; this card is the only one of its
  four causes that had no owner anywhere.
- **[The 27 is a measurement, not a target]** Re-derive it. The cells may be
  re-expressed into a different shape entirely, as long as G-5's node-id set holds
  and each arm can fail on its own medium.
