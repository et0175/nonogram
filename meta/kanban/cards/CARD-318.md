# CARD-318: FR-029's strategies criteria are ten unwritten tests reading as mechanically checked — the board's one real coverage gap

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** `card/318-fr-029-strategies-criteria`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-318
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29, which found the board's real dead-ref population and partitioned it. CARD-307 was cut; this is the successor carrying the only genuine coverage work in it. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** 70 <!-- STAMPED 2026-10-30 at dispatch. Wave 70 opens on the owner's "start these cards together with cards for generator/solver" -- the vector interior path AND the generator/solver family in one wave. This card goes FIRST of the three that share `requirements.yml` (CARD-318 -> CARD-317 -> CARD-316, which mutually serialize at overlap 0.50-1.00), and it starts while CARD-309 is still in review because their Touches intersection is EMPTY -- unlike CARD-330 and CARD-329, which both collide with CARD-309 on tests/test_book_pdf.py and must wait for it to close. -->
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_solver_strategies.py (new or renamed), tests/test_batch_generator.py, tests/test_puzzle_review_*.py, tests/property/
**Review score:** —
**Started:** 2026-10-30T20:55:22Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Of the 23 dead check refs on this board, **ten belong to FR-029**, and unlike the
other thirteen they are not bookkeeping. They name tests that were **never written**,
for behaviour that in several cases **appears not to exist**. Every one reads as
mechanically checked to `forge:status` and to anything judging readiness.

| entry | `requirements.yml` | the test it names | `then` |
|---|---|---|---|
| AC-136 | `:1878` | `TestSolveStrategies_SameCluesSameListUnderDilatedClock` | the two strategies lists are identical element for element |
| AC-137 | `:1885` | `TestSolveStrategies_GuessPresentWhenSearchBranched` | the list contains `guess` |
| AC-138 | `:1892` | `TestSolveStrategies_GuessAbsentForLineSolvable` | the list does not contain `guess` |
| AC-139 | `:1899` | `TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage` | every stored row's `strategies_used` holds that puzzle's real non-empty list |
| AC-140 | `:1906` | `TestExport_JSONCarriesStrategiesInOrder` | the payload's `strategies` array equals the list in the same order |
| AC-141 | `:1913` | `TestPuzzleReview_FiltersListByStrategy` | exactly the 3 puzzles are listed |
| AC-142 | `:1920` | `TestPuzzleReview_RejectsUnknownStrategyFilter` | the request is refused on the CARD-066 error branch |
| AC-143 | `:1927` | `TestPuzzleReview_DetailShowsStrategiesInOrder` | the page shows line_dp then probe_contradiction, in that order |
| EC-017 | `:1934` | `PropertyTest_SolveStrategies_GuessIffSearchBranched` | (property) |
| EC-018 | `:1944` | `PropertyTest_SolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd` | (property) |

**Measured, not assumed:**

- `TestSolveStrategies_*` and `TestExport_*`: **no class with that prefix exists
  anywhere in `tests/`.**
- `TestPuzzleReview_*` exists — but only as `_SizeFilterLabelSaysLongestSide`,
  `_SizeFilterPagesItsOwnMembers`, `_SizeFilterUsesLongestSide` and the book-filter
  siblings. **There is no strategy filter among them.**
- `TestBatchGenerator_*` exists — but only as
  `_SaysOutLoudWhenTheStoreRefusedACandidate` (plus `TestBatchGeneratorSingleton`).
  **Nothing about persisting `strategies_used`.**

So the question this card must answer **before writing anything** is not "how do we
test this" but **"does this behaviour exist?"** All ten criteria carry a
`# NB CARD-0xx uses AC-1xx for a different criterion of its own (CARD-106)` comment —
an AC-id collision note — which suggests FR-029's numbering was reused during
CARD-106 and these criteria may be orphaned from a design that moved.

**Per ADR-0039, a demotion with a recorded reason is a success here, not a retreat.**
If the strategy filter was never built, the right outcome is ACs that say so — not
ten tests written to retire ten warnings.

## What to implement

1. **Establish, per criterion, whether the behaviour exists in `src/`.** Derived:
   walk for the seam each AC describes (the solver's strategies list, the batch
   generator's persistence, the export payload, the review filter and detail page).
   Record the verdict per AC. **Per ADR-0039/R2 a criterion the walk cannot classify
   is a FAILURE, never a silent omission.**
2. **Partition into: implemented-but-untested, not-implemented, and orphaned by the
   CARD-106 renumbering.** The three get different repairs and must not be blended.
3. **For implemented-but-untested: write the test**, TDD, and point the ref at it.
   `TDD: true` on this card is deliberate — a test written after the fact against
   behaviour you have just read tends to assert what the code does rather than what
   the AC says.
4. **For not-implemented: decide build-or-demote with the owner, and record it.** Do
   not build a strategy filter inside a tech-debt card without saying so — that is a
   feature, and `scope_gate: on` should catch it if it is attempted silently.
5. **For orphaned: say which card took the id and what became of the criterion.** The
   `# NB` comments name CARD-034, CARD-035, CARD-037 and CARD-106; read them.
6. **EC-017/EC-018 are property tests.** Per `CLAUDE.md` there is no `hypothesis` in
   the dependency baseline — a property test here builds a large seeded corpus by
   hand with stdlib `random.Random` and **asserts a minimum case count inside the test
   itself** so the corpus cannot silently shrink.

## Acceptance criteria

- **AC-1** (the partition is derived): *Given* FR-029's ten criteria, *then* each is
  classified as implemented-but-untested, not-implemented, or orphaned, by a walk of
  `src/` — not by reading this card's table — and an unclassifiable criterion fails.
- **AC-2** (no criterion keeps a phantom ref): *Given* the branch, *then* no FR-029
  criterion names a symbol with no definition in `tests/`. Each is pointed at a real
  test or demoted to `review-lens` with its reason.
- **AC-3** (the new tests can fail): *Given* each test written, *then* a mutant in the
  behaviour it covers reds it — shown, one mutant per test, deletion-only and
  line-count-preserving. A test written to retire a warning that cannot fail is the
  exact defect this card family exists to remove.
- **AC-4** (the property tests pin their corpus): *Given* EC-017/EC-018 if written,
  *then* each asserts its own minimum case count, so the corpus cannot shrink to zero
  and keep passing.
- **AC-5** (nothing is built in silence): *Given* the branch, *then* any behaviour
  newly implemented rather than merely tested is named in the card, with the owner's
  decision recorded. A tech-debt card that quietly grew a feature is a scope-gate
  escalation, not a bonus.
- **AC-6** (the count moves only downward): *Given* `main` and the branch, *then* the
  validator of record reports **ten fewer dead-ref warnings** and **no warning of any
  kind added** — warning **sets** diffed line by line.

## Guardrails

- **G-1: do not write a test to retire a warning.** If the behaviour is absent, the
  honest output is a demotion. AC-3 is the control on this.
- **G-2: do not build the strategy filter inside this card without the owner's
  decision recorded.** It is a feature; this is tech-debt. Escalate rather than absorb.
- **G-3: resolve refs by DEFINITION, never by `git grep -lw`.** **`\b` is undefined
  in POSIX ERE and silently matches nothing.** Prove any instrument in both
  directions before trusting it — it must find a known name and reject a nonsense one.
- **G-4: no `hypothesis`.** It is not in the dependency baseline (`CLAUDE.md`,
  ADR-0006/R1). Seeded stdlib corpora, with an asserted floor on the case count.
- **G-5: prefer an independent second implementation over re-deriving a value with
  the function under test** — the solver's two brute-force counters in
  `tests/helpers/brute_force_oracle.py` are the precedent, and that oracle must never
  import `nonogram.solver`.
- **G-6: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.)
- **G-7: attribute every skip by name.** DB-mode tests **skip silently** when
  `nonogram_test` is absent, so a green run on the review/batch-generator seams may
  have tested nothing. Say which skips were gates for this card.
- **G-8: do not connect to the production database.** The live panel runs on
  `nonogram_poc`; use `sqlite_session_scope` for regressions.
- **G-9: name the validator binary beside every figure**, and do not compare a
  branch's warning count to main's without holding the review YAMLs equal.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0039/R3 — an exemption is a claim and carries a control for what it must not absorb (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer; the RULE is tested at `tests/test_export_pdf.py:1249`** — verify the substance; the pointer repair is **CARD-317's**)

## Architecture context

- **ADR:** ADR-0039/R1-R3; ADR-0031 (the guess tier's retirement) is adjacent and its
  `::test_no_generated_puzzle_needs_a_branch` tripwire is the nearest live relative of
  AC-137/AC-138 — read it before writing either.
- **Components:** the solver's strategies reporting, the batch generator's
  persistence, the export payload, the puzzle-review filter and detail pages.
- **Trace:** FR-029's row is re-stamped once its criteria name live tests; it is
  currently one of the 43 entries warning `requirement has no tests yet (status:
  partial)`, which is a **separate and larger** population from the dead refs and is
  **not** this card's subject.
