# CARD-228: Difficulty becomes three dots, filled by tier — one glyph the whole book reuses

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/228-difficulty-dots
**Worktree:** ../PythonProject4-card-228
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Header: difficulty right (three dots plus the word)"; the guide's "difficulty legend reuses the dots from the puzzle headers, so readers learn them here once"; the openers' and solution tiles' dots
**Idea:** —
**Wave:** 42
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_difficulty_dots.py, tests/test_book_interior_type_floor.py
**Review score:** —
**Started:** 2026-10-16T17:04:17Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

A small card with wide reach: **one** function that draws a tier as three dots — filled for
the tier's rank, outlined for the rest — and four callers that stop inventing their own.

The artifact uses the dots in four places:

1. The puzzle page header, beside the word (CARD-207).
2. The guide's key strip, where "readers learn them here once" (CARD-229).
3. Each section opener (CARD-231).
4. Each solution tile's header (CARD-233).

Because four later cards depend on it, cut it first and keep it tiny. The artifact's own
mockup shows the shape: filled circles with a stroke, an outlined circle for the remainder,
at the header's optical centre beside the tier's word.

**What to check before writing.** `Tier` and `tier_of_record` live in `nonogram.difficulty`,
and `TIERS` in `book_plan`. The dots' count and order must come from that existing tier
order, never from a second list — a second ordering of the tiers is the kind of duplicate
this project has been bitten by (`strategy_counter.py` once carried a second classifier on
its own literals; see CARD-155).

## Acceptance criteria

- **AC-1** (happy, one dot per rank): *Given* each tier in `TIERS`, *when* its dots are drawn,
  *then* the number of filled dots equals that tier's 1-based rank and the total is always
  three. (test: `TestDifficultyDots_FilledCountIsTheTierRank`)
- **AC-2** (guard, one source of the order): *Given* the drawn dots, *then* the order and
  count come from `TIERS` — proved by a test that would fail if a second list were introduced
  (e.g. by driving the assertion from `TIERS` itself and asserting its length).
  (test: `TestDifficultyDots_ReadsTheProjectsTierOrder`)
- **AC-3** (happy, filled vs outlined): *Given* a middle tier, *then* the filled dots are
  solid and the remainder are outlined with the same stroke, measured off the ink.
  (test: `TestDifficultyDots_FilledAndOutlinedAreDistinguishable`)
- **AC-4** (happy, one function, four callers): *Given* the four call sites, *then* each draws
  its dots through this one function — asserted structurally, the way `tests/test_cli.py`'s
  import guard walks the tree with `ast`. (test: `TestDifficultyDots_HasExactlyOneDrawingSite`)
- **AC-5** (edge, the smallest place it appears): *Given* the smallest box any caller gives it
  (a solution tile's header), *then* the three dots fit without touching the text beside them
  or the tile's own rule. (test: `TestDifficultyDots_FitsTheSmallestHeader`)
- **AC-6** (edge, a puzzle with no tier of record): *Given* a puzzle whose tier cannot be read,
  *then* no dots are drawn at all — not three outlined ones, which would read as "easy".
  (test: `TestDifficultyDots_UntieredDrawsNothing`)

## Guardrails

- G-1: No new drawing primitive — circles go through the existing draw object (ADR-0036/R2).
- G-2: The dots are not text, so CON-020's 10 pt floor does not apply to them; the **word**
  beside them is text and does (test: `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-3: A puzzle's tier is read, never written (ADR-0033/R1).
- G-4: Out of scope — what each caller puts beside the dots; those are CARD-207, CARD-229,
  CARD-231 and CARD-233.
- G-5: This card changes no page's geometry on its own. It adds a function and its tests; the
  callers adopt it. If adopting it moves ink, that belongs to the adopting card's baseline.

## System contract

- CON-020 — reader-facing interior text at or above 10 pt; the dots are not text (check:
  `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0033/R1 — book assembly never changes a puzzle's tier (check: review-lens)
- ADR-0036/R2 — geometry from COMP-007 (check: review-lens)
- ADR-0037/R1 — a puzzle page's band carries number + tier only; the dots *are* the tier, so
  this stays inside R1 rather than widening it (check: review-lens)

## Architecture context

- **FR:** FR-033 (what the interior labels carry), FR-043.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1, ADR-0033/R1.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
  its own 0.5d card is what stops four agents inventing four slightly different dots — the
  shape of defect this project already carries in its own architecture model, where one rule's
  check names a test that does not exist and another names one that cannot test it.
- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
