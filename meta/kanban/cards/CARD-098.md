# CARD-098: Retire the Guess tier — three score bands, and branching stays a strategy

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** red -> green -> mutation check (3 mutants, all caught)
**Branch:** card/098-retire-the-guess-tier
**Worktree:** —
**Source:** owner, 2026-09-18 — "let's go further without a guess tier", after CARD-072 found the tier unreachable from random generation
**Idea:** —
**Wave:** 1
**Depends on:** CARD-072 (merged 50996b6) — `strategies` must already be recorded, since `guess` survives there
**Touches:** src/nonogram/difficulty.py (Tier, classify, bands), src/nonogram/solver/__init__.py (a home for the `guess` strategy name), src/nonogram/orchestrator.py (GUESS_STRATEGY, the classify call, Puzzle.difficulty_tier), src/nonogram/admin/regrade.py, src/nonogram/admin/puzzle_review.py, src/nonogram/admin/app.py (label map, tier counts, filter), src/nonogram/admin/templates/** + static/*.css (the fourth badge), src/nonogram/cli.py and src/nonogram/web/handler.py (the `--difficulty` vocabulary), meta/architecture/decisions/adr/0025-*.md (superseded) and a new ADR, meta/architecture/requirements.yml (EC-015 and the tier ACs), meta/architecture/trace.yml, docs/GENERATION_ALGORITHM.md §7
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-18
**Closed:** 2026-09-18
**Actual:** 1d
**Merge commit:** 0df8d63
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

### Delivered 2026-09-18

**The tier is gone; the fact is not.** `Tier` has three members, each with a
band. `classify` takes the score alone. A solve that branched reports the
`guess` **strategy** — named now by `solver.STRATEGY_GUESS`, beside the rung
vocabulary, because its old name was `Tier.GUESS.value` and could not outlive
the enum.

**The append rule got simpler, not more complex.** Three call sites used to ask
`classify(...) is Tier.GUESS` rather than read `branch_nodes`, because
ADR-0025/R2 reserved that comparison to one place. With the tier retired there
is no rule to concentrate — `branch_nodes > 0` is simply what "needed a guess"
means — so all three read it directly, and the `ast` guard that policed the
comparison **lost its second half instead of gaining three exemptions.** That
is the part of this change I'd point at: retiring the tier removed a rule, a
guard clause and an argument, rather than trading them for special cases.

**Stored rows read, nothing migrates.** `tier_of_record("guess")` answers
`HARD`. That is not defensive: `tests/test_admin_regrade.py`'s own fixture
notes record commit `bb1d5f6` putting **a real `guess` row in the production
database**, which I found mid-card and which turns the read path from a
precaution into a requirement. `None` would have been worse than wrong — it
means "not a tier at all", and such a row would vanish from every count and
filter silently. The admin badge keeps a branch for the word so the row is
drawn in Hard's red rather than the unknown-value grey.

### The standing failure is gone

The suite deselected **two** tests all session. One was
`test_the_admin_puzzle_list_gives_the_fourth_tier_a_badge_of_its_own`, which
this card deletes along with the badge it guarded. **3,447 passed, 0 failed,
one deselection** (`test_size_configuration_applied`, unrelated and still
failing on `main`).

### Scale, and what it touched

73 references across 20 test files and 12 source files. The mechanical part
was `classify(score, branch_nodes)` → `classify(score)`; the judgement was in
deciding, per test, whether it described the *tier* (delete) or the *fact*
(re-point at `branch_nodes`). Re-pointed rather than deleted, because the
grids they run on are hard-won:

| test | was | now |
|---|---|---|
| `test_guess_is_on_the_list_exactly_when_the_tier_says_so` | `("guess" in strategies) == (tier is GUESS)` | `== (branch_nodes > 0)` — renamed `..._when_the_solve_branched` |
| `test_requires_guessing_iff_search_branched` (property) | the tier iff branching | `test_the_tier_is_a_function_of_the_score_alone` |
| `test_no_real_generated_puzzle_is_classified_guess` | no puzzle is Guess | `test_no_generated_puzzle_needs_a_branch` — the measurement kept as the tripwire |
| `test_export_round_trips_a_guess_tier_puzzle` (JSON, CSV) | a Guess-tier puzzle | a *branching* puzzle; JSON now also pins that `strategies` survives the trip |

`GUESS_GRID` in the regrade tests — a 9x9 found by seeded search, the only
fixture in the tree whose solve actually branches — is untouched and now
carries the strategy assertions.

**Deleted rather than re-pointed** (they existed only to describe the fourth
tier): its band being `None`, no score reaching it, the admin badge and filter
option, the PDF filename and header cases, the guide page's fourth count,
`--difficulty guess` being requestable, AC-120/AC-121/EC-015.

### Model

ADR-0031 written and Accepted; ADR-0025 `Superseded by ADR-0031` with a
History entry — its argument for keeping the tier is quoted and answered, not
dropped. FR-008's statement is three tiers; AC-120, AC-121 and EC-015 are
retired with a note saying what replaced them and why a criterion that changes
what it is about is a new criterion (AC-174). `trace.yml`'s FR-026 row records
the reversal. `docs/GENERATION_ALGORITHM.md` §7 rewritten;
`check_doc_references.py` 229 resolved, 0 failed.

**Mutation check** — three mutants, restored from saved copies: a stored
`guess` row no longer reading as Hard, `guess` no longer appended to the
strategies, and the fourth tier coming back. All three caught.

### One mistake worth recording

I deleted `"guess": "Guessing (trial and error)"` from `admin/app.py` while
sweeping, reading it as a tier label. It is a **strategy** label, and `guess`
survives as a strategy — so the line had to come back. Two tests caught it
immediately. It is the exact error this card is most likely to invite: the
word means two things now, and only one of them was retired.

### Out-of-scope observation

`tests/property/test_difficulty_ladder.py::test_no_generated_puzzle_needs_a_branch`
is now the tripwire for this decision: if a future source (image mode, the
library, a new extent) starts producing branching grids, it fails, and
ADR-0031's Negative says that is the moment to revisit. Worth knowing that the
safety net ADR-0025 wanted is now a *test* rather than a tier.
