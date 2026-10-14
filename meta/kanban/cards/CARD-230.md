# CARD-230: The guide's worked example runs as four steps, and the rows/columns tip becomes a callout

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/230-guide-worked-example-steps
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The worked example runs as four small steps, each with one line saying what changed" and "The tip about switching between rows and columns moves to the foot of page 2 as a callout"
**Idea:** —
**Wave:** —
**Depends on:** CARD-229 (the spread and its two-column frame)
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py, tests/test_book_finalise_guide_preview.py, tests/test_book_finalise_guide_preview_layout.py, tests/fixtures/book_baseline_card230.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Two changes to the guide's content layout, both inside the spread CARD-229 builds.

1. **The worked example becomes four small steps**, each with **one line saying what changed**.
   Today the worked example is a single figure under `GUIDE_EXAMPLE_HEADING` (CARD-167 added it,
   CARD-201 turned the guide into two pages). Four steps means four small grids in sequence,
   each with its own one-line caption — and the captions are the teaching, so they are content
   constants, not drawing-code strings.
2. **The rows/columns tip moves to the foot of page 2 as a callout** — a distinct block, not a
   paragraph in the flow.

**Where the copy comes from.** The owner's instruction for the whole spread is "your current
text, lightly tightened". The four step captions are new sentences, so they are new constants
with the existing `GUIDE_*` naming, and the callout's text is the existing tip moved, not
rewritten. Say in the notes which strings are new and which moved, so a reviewer can tell
tightening from invention.

## Acceptance criteria

- **AC-1** (happy, four steps): *Given* the guide, *then* the worked example is drawn as four
  grids in reading order, each with exactly one caption line beneath it.
  (test: `TestGuideWorkedExample_RunsAsFourSteps`)
- **AC-2** (happy, each step changes something): *Given* consecutive steps, *then* each step's
  grid differs from its predecessor, and the difference is non-empty — a step that changes
  nothing is a defect in the lesson, and this is the assertion that catches it.
  (test: `TestGuideWorkedExample_EveryStepChangesTheGrid`)
- **AC-3** (happy, the caption describes its own step): *Given* each step, *then* its caption
  comes from a constant paired with that step, so steps and captions cannot drift apart.
  (test: `TestGuideWorkedExample_CaptionsArePairedWithSteps`)
- **AC-4** (happy, the callout): *Given* page 2, *then* the rows/columns tip is drawn as a
  callout at the foot — below the last technique, visually set apart (its own rule or panel),
  and not inside a technique's column. (test: `TestGuideCallout_SitsAtTheFootOfPageTwo`)
- **AC-5** (guard, the copy moved rather than changed): *Given* the callout's text, *then* it
  is the existing tip's constant. (test: `TestGuideCallout_UsesTheExistingTipText`)
- **AC-6** (edge, the four steps fit): *Given* the shortest trim the profile lays out, *then*
  the four steps and their captions fit inside page 2's column without crossing the callout or
  the footer rule. (test: `TestGuideWorkedExample_FitsTheShortestTrim`)
- **AC-7** (guard, the preview agrees): *Given* the Finalise screen's guide preview, *then* it
  shows the same four steps in the same order, because it reads the generator's own text.
  (test: `TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep`,
  `tests/test_book_finalise_guide_preview.py:403`)

## Guardrails

- G-1: CON-020's floor holds for the step captions and the callout (test:
  `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-2: The guide stays two pages. Four steps must fit the spread; they do not earn a third page
  (test: AC-6's class plus `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`).
- G-3: The example grids are drawn with the same primitives as the puzzle pages' grids, at the
  spread's single example cell size (CARD-229's AC-5).
- G-4: Out of scope — the spread, the key strip and the two-column frame (CARD-229).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- FR-041 — the guide's content (check: the guide tests)
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- INV-013 — the guide stays two pages, so parity after it is unchanged (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-041.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [AC-2 is the one that makes this a lesson rather than four pictures] "Each with one line
  saying what changed" is only true if something changed. Asserting the grids differ is cheap
  and it is the only assertion here that tests the teaching rather than the layout.
