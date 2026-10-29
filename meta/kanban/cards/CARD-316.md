# CARD-316: Seven acceptance criteria name tests that were never meant to exist — rejected alternatives, retired features and one forward declaration, each reading as mechanically checked

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29, which found that the board's real dead-ref population is bare class names rather than node ids. CARD-307 was cut; this is one of its four successors. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Seven entries in `requirements.yml` carry a `test:` key naming a test that **nobody
should ever write**, because the thing the AC describes was rejected, retired, or has
not been built yet. Each one produces a `DEAD check ref` warning, and — worse — each
one reads as *mechanically checked* to `forge:status` and to anything judging
readiness.

They are already marked, in comments, as not-to-be-built. The comment says one thing
and the `test:` key says another. **The key is the part the machine reads.**

| entry | `requirements.yml` | the marker already there | the test it names |
|---|---|---|---|
| AC-129 | `:1802` | `# alternative: allow_degenerate_grids` | `TestGenerateRandom_AcceptsDegenerateDensityAsUniqueEasyPuzzle` |
| AC-134 | `:1810` | `# alternative: allow_degenerate_grids` | `TestGenerateRandom_DegenerateGridScoresEasy` |
| AC-206 | `:2969` | `# alternative: fixed_research_mix_30_45_25` | `TestBookCreate_DefaultSplitIsResearchMix30_45_25` |
| AC-207 | `:2976` | `# alternative: derived_from_audience` | `TestBookCreate_DefaultSplitDerivedFromAudience` |
| AC-191 | `:2424` | `# RETIRED 2026-09-22 (b) unimplemented — the wide-grid flag is dropped` | `TestBookSelect_FlagsWideGrid` |
| AC-192 | `:2432` | `# RETIRED 2026-09-22 (b) unimplemented — no wide-grid flag exists to be absent` | `TestBookSelect_SquareAndTallGridsNotFlaggedWide` |
| AC-379 | `:3594` | `# OWED by CARD-226, which splits the two-up page into two equal slots` | `TestTwoUpSlots_EachSlotFloatsAtFortyTwoPercentOfItsOwnSpare` |

**Three different situations, two different repairs.**

**The four alternatives and the two retired ACs (six)** describe behaviour the project
chose *against*. AC-206/207 are the clearest: they assert the default split is
**30/45/25**, while the chosen criterion AC-205 — six lines above, with a live test —
says **40/40/20**, and `src/nonogram/admin/book_plan.py:345` says
`Split(40, 40, 20)`. AC-191/192 assert a wide-grid flag whose own comment says it was
dropped, and the surviving test is `TestBookSelect_WideGridAboveFloorCarriesNoFlag`,
which asserts the *opposite*. For these six the repair is to drop the `test:` key, per
the validator's own advice: *"write the test, or drop the `test:` … an honest gap is
fixable, a phantom one is not."*

**AC-379 is different and must not be lumped in.** It is an honest forward
declaration — CARD-226 genuinely owes it. The defect is only that `kind: test` makes
an owed test read as a performed one. This is exactly the
`adr-check-refs-must-be-honest` pattern. It becomes a **`review-lens` naming
CARD-226**, and flips back to `kind: test` when that card lands.

## What to implement

1. **Derive the set, do not copy the table above.** Walk `requirements.yml` for
   entries whose `test:` names a symbol with no `class`/`def` definition in `tests/`,
   and partition them by the marker in the comment lines directly above the entry
   (`# alternative:`, `# RETIRED`, `# OWED`). **Per ADR-0039/R2 an entry the walk
   cannot classify is a FAILURE, never a silent omission** — if an eighth appears, the
   card grew and must say so rather than quietly covering it.
2. **For the six: remove the `test:` key.** Keep the AC. Keep the comment. An AC
   without a `test:` is an honest unverified example; an AC with a phantom one is a
   lie with a green tint. Do **not** delete the ACs — they record what was considered
   and rejected, which is why the alternatives were written down in the first place.
3. **For AC-379: convert to `review-lens`, naming CARD-226** as the card that owes
   the flip back, and add the flip to CARD-226's own acceptance criteria so the
   obligation is carried by a card rather than by a comment.
4. **Say what the warning count did, measured on the validator of record**, with the
   binary named. Expect **100 → 93**. Diff the warning **sets** line by line, not the
   counts — a count that moves by seven can hide seven arrivals and fourteen
   departures.

## Acceptance criteria

- **AC-1** (the set is derived): *Given* `requirements.yml`, *then* the seven entries
  are produced by a walk that reads definitions from `tests/`, not from a list in this
  card, and an unclassifiable entry fails rather than being skipped.
- **AC-2** (no phantom key survives): *Given* the branch, *then* no `test:` key in
  `requirements.yml` names a symbol with no definition in `tests/` — asserted by a
  test, so the property holds for entries added later.
- **AC-3** (the six keep their ACs): *Given* the branch, *then* AC-129, AC-134,
  AC-191, AC-192, AC-206 and AC-207 still exist with their `given`/`when`/`then` and
  their comments intact — only the `test:` key is gone.
- **AC-4** (AC-379's obligation is carried by a card): *Given* the branch, *then*
  AC-379 is `kind: review-lens` naming CARD-226, **and** CARD-226 carries an
  acceptance criterion requiring the flip back. A demotion with no card owing the
  flip is how a shim becomes an end state.
- **AC-5** (the count moved, and only downward): *Given* `main` and the branch, *then*
  the validator of record reports **93 warnings against main's 100**, the departing
  seven are exactly the seven named here, and **no warning of any kind is added** —
  sets diffed, not counts.

## Guardrails

- **G-1: do not write a test to retire a warning.** Six of these describe behaviour
  that does not exist. A test asserting rejected behaviour is worse than the warning.
- **G-2: do not delete the acceptance criteria.** The rejected alternatives are a
  record of a decision. Removing them loses why 40/40/20 was chosen.
- **G-3: do not touch AC-205.** It is the live, correct, tested criterion and the
  control that AC-206/207 are the rejected pair.
- **G-4: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.)
- **G-5: do not compare this branch's warning count to main's without holding the
  review YAMLs equal.** `meta/review/**` is inside the validator's ref-resolution
  domain, so a tree with different reports in it resolves differently. Swap the files
  inside one worktree and re-run. **And do not validate a `git archive` copy** — a
  copy has no `.git`, so staleness and drift checks fall silent (measured: 77 against
  a worktree's 102).
- **G-6: name the validator binary beside every figure.** The plugin-cache copy
  reports a phantom `[ERROR] ADR-0025 circular supersession` from a regex bug; the
  copy of record is the `forge_1` one named in `meta/kanban/config.yml`.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer; the RULE is tested at `tests/test_export_pdf.py:1249`** — verify the substance; the pointer repair is **CARD-317's**)

## Architecture context

- **ADR:** ADR-0039/R2
- **Components:** none in `src/` — this is the requirements registry
- **Trace:** six ACs lose a `test:` key and one becomes a lens; `trace.yml` rows for
  FR-028, FR-032, FR-035 and FR-040 must be re-read afterwards, because an AC that no
  longer claims a test may change its requirement's coverage status.
