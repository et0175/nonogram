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

_Assembled 2026-10-17 by `system_rules.py --card CARD-230 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-013** — the guide is still two pages, so parity after it is unchanged. As of
  2026-10-17 (commit `91609aa`) those two pages are interior **2 and 3**, not 1 and 2:
  CARD-206's title page occupies page 1 and the guide is a facing spread (CARD-229).

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

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
