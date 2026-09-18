# CARD-098: Retire the Guess tier — three score bands, and branching stays a strategy

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/098-retire-the-guess-tier
**Worktree:** —
**Source:** owner, 2026-09-18 — "let's go further without a guess tier", after CARD-072 found the tier unreachable from random generation
**Idea:** —
**Wave:** 1
**Depends on:** CARD-072 (merged 50996b6) — `strategies` must already be recorded, since `guess` survives there
**Touches:** src/nonogram/difficulty.py (Tier, classify, bands), src/nonogram/solver/__init__.py (a home for the `guess` strategy name), src/nonogram/orchestrator.py (GUESS_STRATEGY, the classify call, Puzzle.difficulty_tier), src/nonogram/admin/regrade.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py (label map, tier counts, filter), src/nonogram/admin/templates/** + static/*.css (the fourth badge), src/nonogram/cli.py and src/nonogram/web/handler.py (the `--difficulty` vocabulary), meta/architecture/decisions/adr/0025-*.md (superseded) and a new ADR, meta/architecture/requirements.yml (EC-015 and the tier ACs), meta/architecture/trace.yml, docs/GENERATION_ALGORITHM.md §7
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

The owner's decision, 2026-09-18. The evidence behind it is that the tier has
never once been assigned:

- ADR-0029's measurement: **0 of 6,620** generated puzzles.
- CARD-076's: **0 of 462**.
- CARD-072's, found by a mutant that survived: no random draw in the supported
  range branches at all, so `guess` is not reachable through `generate` — a
  corpus test could only ever assert half of the "iff" rule.
- This project's own admin database: **0 of 16** stored rows (Medium 15,
  Hard 1).

**The counter-argument is on the record and is being overruled, not
overlooked.** `difficulty.Tier`'s docstring and ADR-0025's History both say the
tier is kept *deliberately* despite the zero rate — "the product promise stated
as a fact, and a safety net for a future source or extent that does produce a
branching grid". That is a real argument: image mode, the library, or a future
extent could produce one, and then a Guess puzzle would silently be filed as
Hard. The owner has weighed it and chosen a three-band scale. This card
therefore has to leave the *fact* reachable even though the tier is gone —
which is what keeps `guess` as a strategy (below).

## What to implement

1. **`Tier` becomes three members.** `EASY`, `MEDIUM`, `HARD`; `GUESS` is
   removed, and with it `band`'s `None` case. `classify(score, branch_nodes)`
   becomes `classify(score)` — every caller already has the score, and three of
   the five call sites pass `branch_nodes` for no other reason.

2. **Branching stays reportable, as a strategy.** FR-029's list keeps `guess`:
   "this solve had to branch" is still true of a puzzle and is still worth
   printing in a book's difficulty note. Its *name* currently comes from
   `Tier.GUESS.value` (`orchestrator.GUESS_STRATEGY`), which cannot survive the
   enum, so it needs a home: put it beside the rung names in
   `nonogram.solver` (say `STRATEGY_GUESS`), documented as **not a rung** — the
   solver already refuses to put it in `SolveSignals.rungs` for exactly that
   reason, and this only names it in the same place.

   The append rule changes shape with the tier. Today three call sites ask
   `classify(...) is Tier.GUESS` rather than reading `branch_nodes`, because
   ADR-0025/R2 allowed only one reader of that rule. With the tier gone there
   is no rule to concentrate: `branch_nodes > 0` is simply what "needed a
   guess" means, and all three read it directly.

3. **Stored rows: map, do not migrate.** A row whose `difficulty_tier` is
   `guess` must not crash a page or a decode. Reading one yields `HARD` — the
   nearest true statement, since a branching puzzle is at least as hard as the
   hardest band — and nothing rewrites stored data. There are no such rows in
   this project's admin DB, but **the production database has not been checked
   and must not be** (CARD-077 G-1), so the read path carries the mapping
   regardless. A later re-grade (CARD-077's action) will reassign such a row on
   its own terms.

4. **The adapters' vocabulary.** `--difficulty guess` stops being accepted:
   `parse_tier` rejects it like any other unknown word, and the CLI's and web
   form's option lists lose it. Note that the error message for an unknown
   tier is user-facing, so its wording is covered by the existing AC.

5. **The admin.** The fourth badge and its CSS token go; the tier filter's
   options, `app.py`'s label map (`"guess": "Guessing (trial and error)"`) and
   the `tier_counts[Tier.GUESS]` summary go with them.
   **`tests/test_difficulty_tiers.py::test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own`
   is one of the two standing suite failures this project deselects** — it is
   this card's to delete, and doing so removes a standing red rather than
   leaving it.

6. **The model.** ADR-0025 is **superseded** by a new ADR (next free number is
   0031) which records the measurements above, the counter-argument, and the
   owner's decision; ADR-0025 gets `Status: Superseded by ADR-0031` and a
   History entry. `EC-015` ("`Tier.GUESS` is a fact about the solve, not a
   score band") is retired, and the FR-008 acceptance criteria that name four
   tiers are amended. `trace.yml`'s rows follow.

## Acceptance criteria

- **AC-1** — `difficulty.Tier` has exactly three members and every one of them
  has a score band; `classify` takes the score alone and returns one of the
  three for every finite score.
  *test:* `TestTiers_ThreeBandsAndNoFourthTier`
- **AC-2** — a puzzle whose solve branched still reports `guess` among its
  strategies, and its tier is whichever band its score falls in.
  *test:* `TestTiers_BranchingIsAStrategyNotATier`
- **AC-3** — a stored row whose `difficulty_tier` is `"guess"` reads back as
  Hard: the admin list renders it, the detail page renders it, and nothing
  raises. No stored value is rewritten by this card.
  *test:* `TestTiers_LegacyGuessRowReadsAsHard`
- **AC-4** — `--difficulty guess` is refused with the same message any other
  unknown tier gets, at the CLI and in the web form.
  *test:* `TestTiers_GuessIsNoLongerARequestableTier`
- **AC-5** — the suite's two standing failures become one: the fourth-badge
  test is gone rather than deselected, and no test is deselected on its
  account.

## Guardrails

- G-1: **No production database is read or written** (CARD-077 G-1). The stored
  mapping is a read path, not a migration, and no backfill runs.
- G-2: `guess` survives as a strategy name and in `strategies_used` values
  already stored — this card removes a *tier*, not a fact about a solve.
- G-3: The score formula, the ladder and the rung vocabulary are untouched
  (ADR-0029): only the classifier's fourth answer goes.
- G-4: The solver is not edited beyond adding a name; `SolveSignals.rungs`
  still never contains `guess`.
- G-5: ADR-0025 is superseded, never deleted or silently edited — its Status,
  a History entry, and the new ADR carry the reversal.
- G-6: Commit only your own files — explicit pathspecs.

## System contract

- ADR-0025 — superseded by this card; until the new ADR is Accepted, review
  should read ADR-0025's rules as historical (check: the new ADR's Status)
- ADR-0029/R1, R2 — the ladder and "one derivation from the one verifying
  solve" are unchanged (check: tests/property/test_difficulty_ladder.py)
- CON-004 — a tier is a bucket a scored candidate fell into, never a
  construction target (check: review-lens)
- ADR-0023/R2 — no export schema version moves: `difficulty` is not carried in
  either serialized document (check: tests/property/test_export_roundtrip.py)

## Architecture context

- **FR:** FR-008 (tier selection — ACs amended), FR-029 (strategies — unchanged
  in substance, `guess` stays)
- **EC:** EC-015 (retired)
- **ADR:** ADR-0025 (superseded), ADR-0031 (new), ADR-0029 (unchanged)
- **Components:** COMP-006 (difficulty), COMP-002, COMP-001/COMP-008 adapters,
  the admin panel
- **Trace:** meta/architecture/trace.yml (FR-008, FR-029 rows)

## Worktree notes

—
