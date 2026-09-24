# CARD-146: The frame reaches the printed two-up page

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** CARD-144 review gap, 2026-09-24 (owner's ruling: merge CARD-144 with the gap, close it here)
**Idea:** —
**Wave:** 27
**Depends on:** CARD-128, CARD-144
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** waiting on CARD-128 and CARD-144 to merge — both edit the files this card needs

## What to implement

CARD-144 added a frame to book puzzle pages and it works on single-puzzle
pages. **A printed two-up page still has no frame.**

The cause is not a bug in CARD-144's geometry: `Layout.frame` is computed for
both slots of a pair, and CARD-144's tests confirm it. The two-up *page* is
composed by `src/nonogram/admin/book_pdf_generator._stroke_drawing`, which
deliberately reimplements grid stroking from `slot.vertical_lines` /
`slot.horizontal_lines` (the native-reimplementation convention this codebase
uses instead of importing across capability boundaries) — and therefore never
draws `slot.frame`.

CARD-144 could not close this: its G-4 guardrail put `src/nonogram/admin/**`
out of bounds, and CARD-128 was editing that same file concurrently. The
guardrail was correct; this card is where the work belongs.

Draw each slot's frame in `_stroke_drawing`, using the same heavy rule and the
same on-the-boundary placement CARD-144 chose for single pages, so a pair reads
as two framed puzzles rather than two bare grids.

**Measured evidence of the gap** (from CARD-144's implementation, not assumed):
interior page 3 of the baseline book — the two-up page — is byte-identical to
its pre-frame recording, while interiors 2 and 4 (single-puzzle pages) moved.

## Acceptance criteria

- **AC-1:** On a book whose print order pairs two puzzles onto one interior
  page, each of the two drawings carries its own closed frame — clue bands
  boxed, corner empty — matching a single-puzzle page's frame.
  *test: TestPuzzleFrame_PairIsFramedOnThePrintedPage*
- **AC-2:** Each frame rule on a two-up page is the heavy weight, at least
  twice the thin and pure black (ADR-0037/R2). No new stroke weight is
  introduced. *test: TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly*
- **AC-3:** Frame placement on a two-up page straddles its boundary exactly as
  a single page's does, so the two presentations agree.
  *test: TestPuzzleFrame_TwoUpStraddlesItsBoundaryLikeASinglePage*
- **AC-4:** Cell size, slot origin and page geometry are unchanged — this card
  adds ink only. CARD-127's and CARD-118's measured figures stay green.
  *test: TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame*

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited.
- G-2: ADR-0037/R2 — no new stroke weight; reuse the heavy rule.
- G-3: Geometry is unchanged. Ink only; no cell fitting, gutter depth or origin
  may move.
- G-4: Do not change `src/nonogram/export/**`. CARD-144 already placed
  `slot.frame` there correctly; this card only consumes it.
- G-5: Do not regress CARD-145's streaming property — peak memory stays
  O(one page). `_stroke_drawing` runs inside the per-page path; do not
  accumulate.

## Architecture context

- **FR:** FR-041
- **ADR:** ADR-0036/R2 (the panel decides no geometry), ADR-0037/R2 (stroke weights)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Origin] Cut 2026-09-24 from CARD-144's implementation report. The owner chose
"merge CARD-144 with the gap recorded, close it in a follow-up" over escalating
CARD-144 back to the decompose station, so that the wave kept moving and the
guardrail was not weakened inside a worktree.

[Sequencing] Blocked on CARD-128 and CARD-144 because both edit
`book_pdf_generator.py` and the shared book baseline fixtures. Unblock once both
are merged; the baseline this card's tests read must be the post-CARD-144 one.
