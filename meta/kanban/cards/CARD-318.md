# CARD-318: FR-029's strategies criteria are ten unwritten tests reading as mechanically checked — the board's one real coverage gap

**Status:** review
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
**Review score:** 9.0 (cycle 3 of 3 — CERTIFIED; 7.0 → 8.5 → 9.0)
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

## [Cycle 1's two orchestrator-caused findings, closed 2026-10-31]

Review cycle 1 scored **7.0** on three Important findings. **Two were the
orchestrator's, both caused by the AC-142 demotion**, and both are closed here.

### F-001 — the demotion ADDED a warning, and the count hid it

AC-6 demands *"no warning of any kind added"*. The first demotion's `then` read
*"the unknown value is reported to the admin and then ignored, and every puzzle
is listed"*, and the validator flagged it: **`'then' bundles several outcomes —
split into separate acceptance criteria (one behaviour each)`**. The rule is
`then.count(" and ") >= 2`, and that sentence named **two observables** — a flash
appears, and the listing is unfiltered.

**The count concealed it.** The demotion cleared AC-142's dead ref (**−1**) and
added the bundling warning (**+1**), so the total stayed at **91** while the set
changed. A figure read off the summary line rather than the rows was therefore
*correct and useless* — exactly the trap this card family exists to remove,
landing on the card's single most load-bearing figure.

**The fix is not a reword around the count.** Dropping one ` and ` for a ` so `
would satisfy the heuristic and still bundle two outcomes. So the second
observable was **removed from the criterion** instead: AC-142's `then` now states
the one outcome the negative case is about — what happens to the listing — and
the flash, still asserted by the same test at `tests/test_strategies.py:521`, is
named in a comment as a second observable that would need its own criterion
rather than being silently dropped.

### F-002 — the demotion never reached `trace.yml`

`trace.yml` still listed `TestPuzzleReview_RejectsUnknownStrategyFilter` (**no
definition**) and still said AC-142 was *"held open on an owner decision"*, which
`3a4052a4` had settled. Two model artefacts contradicted each other and **the
wrong one is what a trace-matrix reader reaches first**.

Both are fixed, and the mechanism is recorded in `trace.yml` itself because it is
the same one that produced the original ten: **the validator does not check
`trace.yml`'s `tests:` entries at all**, so a name there can name nothing and
nothing says so. Cycle 1 caught it only by resolving the names by `ast`
definition instead of trusting the file.

### AC-6's figure, re-measured FROM THE SETS

Validator of record (`forge_1`'s, per `config.yml:38`), at the merge-base
`ef242847` in a throwaway worktree versus this HEAD, warnings compared as **sets**:

| | |
|---|---|
| merge-base | 0 errors, **100** warnings |
| HEAD | 0 errors, **90** warnings |
| difference | **10 REMOVED, 0 ADDED** |

The ten removed are exactly FR-029's AC-136..AC-143 and EC-017/EC-018 check-ref
warnings. **So AC-6 is satisfied** — and the card's own "9 removed" **understated
it**: the demotion bought the tenth after all. The same stale read made the card
understate its achievement and overstate its cleanliness at once.

**F-003 is closed by fix round 1**, in the section below. It was the card's
own: the M6/M9 spy discriminated `-> []` but not `-> ['simple_overlap']`, so
its predicate was "truthy and within `STRATEGY_NAMES`" rather than identity
with that puzzle's list, which is what AC-139's wording demands. It needed an
assertion, not a re-measurement, and all four of cycle 1's mutants were
re-fired on the result.

## [Fix round 1 — F-003 closed, 2026-10-31]

Cycle 1's third Important finding, and the only one that was this card's own.
The reviewer confirmed the M6/M9 spy watches the right boundary; the gap was
the **predicate**. It asserted *truthy **and** a subset of `STRATEGY_NAMES`* —
never identity with that puzzle's own list — so a hardcoded in-vocabulary
constant passed both the row check and the hand-off check at both call sites
(the reviewer's R3/R4, which survived symmetrically).

### What the assertion is now

Both arms assert **equality** against `_strategies_from_grid(grid)`: the clues
recomputed from that puzzle's own grid, a fresh solve, and `_strategies_of`'s
native statement of FR-029's rule. The spy records the **grid** beside the
list, which is what makes the puzzle identifiable without asking its caller
anything.

**Why that expectation is independent (G-5).** It is not fetched from the code
under test. The code under test is the admin's hand-off —
`batch_generator.py:474` and `app.py:1993` — and the value it is compared
against is re-derived in the test tree from the stored grid, by the same
second-implementation route `_strategies_of` already was in cycle 1. Measured
before relying on it: over **250** candidates (10 at `MIN_SIZE`, 50 at 18x18,
160 at 20x20, 30 at 22x22) and both call sites, the re-derivation reproduced
the handed-over list **250 of 250 times**, and the image half reproduces it
identically on repeated runs. The alternative the brief allows — a known
fixture with its strategies written into the test — was **not** needed, and is
not what was done.

### Both arms, because each is blind to what the other sees

- The **row** arm is AC-139's own sentence and cannot see an empty hand-off at
  all: `add_puzzle` derives the list from its own uniqueness proof when handed
  one, so the row is right while the caller is wrong. That is why M6/M9
  survived in the first place.
- The **hand-off** arm sees that, and with identity it also sees a hand-off
  that is non-empty, in-vocabulary and wrong.

Measured, the row arm is the one that reds for R3/R4 — the store *echoes* a
non-empty list, so the wrong value reaches the row and is seen there first.
That left the hand-off **identity** assertion without a mutant of its own, so
it has one (R5): a store that stops echoing plus a constant hand-off, the one
shape in which only the hand-off can see the defect. Stated rather than
claimed by proximity.

### Mutant table — one cell per node id, with the assertion that fired

Harness `scratchpad/card318fix/final_mutants.py`, fired on the **committed**
code (`29a3066a`). Protocol: SHA-256 of every target asserted before each
plant and after each restore (**all 10 `restore=ok`**, every target pristine
afterwards, `git status --porcelain -- src/ tests/` empty),
`PYTHONDONTWRITEBYTECODE=1` with a `*.pyc`/`__pycache__` sweep before **and**
after each run, restore from the in-memory original, and the **collected count
asserted to be exactly 1** on every one of the 13 runs.

| # | plant | site | node | verdict | the assertion that fired |
|---|---|---|---|---|---|
| R1 | `strategies_used=[]` | `batch_generator.py:474` | AC-139 random | **FAILED** | `:531` hand-off is non-empty |
| R1 | " | " | AC-139 image | PASSED | correct discrimination — the plant is in the random path only |
| R2 | `strategies_used=[]` | `app.py:1993` | AC-139 random | PASSED | correct discrimination — the plant is in the image path only |
| R2 | " | " | AC-139 image | **FAILED** | `:531` hand-off is non-empty |
| R3 | `strategies_used=['simple_overlap']` | `batch_generator.py:474` | AC-139 random | **FAILED** | `:518` row == that puzzle's re-derived list |
| R3 | " | " | AC-139 image | PASSED | correct discrimination, as R1 |
| R4 | `strategies_used=['simple_overlap']` | `app.py:1993` | AC-139 random | PASSED | correct discrimination, as R2 |
| R4 | " | " | AC-139 image | **FAILED** | `:518` row == that puzzle's re-derived list |

**R1 and R2 still die; R3 and R4 now die too** — which is the round's
deliverable. Counted from the rows: **8 cells, 4 FAILED, 4 PASSED**, and every
PASSED cell is a cross-site cell, i.e. the mutant is not in the path that node
drives. Cycle 1 measured R3/R4 as SURVIVED on the same two lines.

### The lines the fix added also carry controls

| # | plant | node | verdict | the assertion that fired |
|---|---|---|---|---|
| R5a | `puzzle_review.py:946` `if not strategies_used:` → `if True:` (store always derives), call sites pristine | AC-139 random | PASSED | no spurious red — nothing fired |
| R5b | R5a **plus** `batch_generator.py:474` → `['simple_overlap']` | AC-139 random | **FAILED** | `:532` hand-off == re-derived list |
| R6 | `LADDER_EXTENT` → `MIN_SIZE` | AC-139 random | PASSED | **not a control** — see below |
| R7 | second picture → `owl1.png`, whose ladder is measured equal to `bird1.jpg`'s | AC-139 image | **FAILED** | `:621` the two ladders differ |
| R8 | `search.py:629` → ladder truncated to its first rung | AC-139 random | **FAILED** | `:571` at least one ladder is longer than one rung |

**R6 is recorded as a failed mutant, not as a passing test.** It was written to
red the random half's non-degeneracy floor by putting the extent back to
`MIN_SIZE`, and it **passed** — which disconfirmed the figure the fix's own
comment carried ("every 10x10 candidate solves with the single rung", read off
one batch and eight density-40 seeds). Re-measured **from the candidates**: at
10x10 density 50, **89 of 100** candidates are single-rung and **4 of 10** whole
batches are single-rung throughout — so `MIN_SIZE` blinds the identity
assertion about two batches in five, not always, and a mutant that reds 40% of
the time is not a control. The comment now states the measured rates and the
floor's control is R8, which truncates every ladder in the solver and therefore
reds at **any** extent (twice out of two). R8 is also the discriminating plant:
the identity arms stay green under it, because they re-derive through the same
solver, so a truncated ladder is still that puzzle's list — the failure is at
`:571` and nowhere earlier.

### The corpora, and why they changed

- **Random half: `MIN_SIZE` → 20x20.** Figures above. At 20x20, density 50 —
  the density `orchestrator.generate_batch` gives every random candidate, not a
  number chosen here — **134 of 160** candidates carry a longer ladder, **0 of
  16** batches were single-rung throughout, nothing was abandoned, nothing
  timed out, and a batch of ten costs 0.3-0.7s. The batch RNG cannot be seeded
  from outside (`orchestrator.generate` draws its seed from
  `secrets.randbits`, `generate_batch` builds an unseeded `random.Random`), so
  non-degeneracy is **asserted per arm** (`:571`) rather than arranged — this
  suite's own style for a corpus it cannot seed. At the measured single-rung
  rate, ten draws miss the floor with probability ~1e-8.
- **Image half: `bird2.jpg` beside `bird1.jpg`.** The image path draws nothing
  from the RNG, so each picture's ladder is fixed: `bird1.jpg` solves with
  `('simple_overlap',)` and `bird2.jpg` with `('simple_overlap', 'line_dp',
  'probe_contradiction')`, identical on repeated runs. Two ladders that differ
  is what makes **every** constant fail the identity assertion on this half,
  which the random half can only make overwhelmingly likely — and it is
  asserted (`:621`), with R7 as its control.

### The docstring says what is asserted

The sentence F-003 named — *"what has to be observed is the value the generator
handed over"*, true of the observation and silent about the predicate — is
gone. The class now states the predicate (identity against an independent
re-derivation), names both arms and what each is blind to, and says which plant
reds which arm. That was the defect, so it is not reproduced in new wording.

### A harness trap worth the next card's attention

The first run of this round's harness passed `-o "addopts=''"` inside a
subprocess argv — the quotes are *data* there, so pytest read an `addopts` of
`''`, which contributed an empty path argument and collected **10,016** tests
instead of 1. Two runs of that were killed part-way (SIGTERM at ~5 min; the
`.full-suite.lock` was free and unheld throughout, no foreign holder existed,
and none was written). It is the `addopts` trap in a new disguise: `-o addopts=`
is the correct spelling, and **every run of the final harness asserts its
collected count is exactly 1**, which is what caught it.

### Gate — impact set, every skip attributed

`-o addopts= -rs`, the six files the round's brief names, on the committed code:

| file | collected |
|---|---|
| `tests/test_solver_strategies.py` | 16 |
| `tests/property/test_solve_strategies.py` | 5 |
| `tests/test_batch_generator.py` | 16 |
| `tests/test_strategies.py` | 17 |
| `tests/test_puzzle_review_book_filter.py` | 20 |
| `tests/test_puzzle_review_bulk_read.py` | 35 |
| **total, counted from the rows** | **109** |

**109 passed, 0 failed, 0 skipped** in 21.8s, twice, with `grep -c '^SKIPPED'`
= **0** — so there is no skip to attribute, and in particular no DB-mode test
skipped silently for want of `nonogram_test` (G-7). The brief's "299 passed"
and this card's earlier "707 passed" are both *wider* sets than these six
files; 109 is this set counted from its own rows, and the sum of the per-file
counts equals the run's total.

`meta/architecture/requirements.yml` and `trace.yml` are **untouched** by this
round (`git diff` of both against `7845cb5c` is empty), so the AC-6 figure
recorded above — merge-base `ef242847` 0 errors / 100 warnings → HEAD 0 errors
/ 90 warnings, 10 removed / 0 added as sets — is unmoved and was not
re-measured. CARD-317 and CARD-316 keep their queue position on that file.

### Still open, and not this round's

F-004 and F-005 (both **low**) are untouched: F-004 is the shared-file
etiquette sentence's own undercount (five changed values naming `AC-142.then`,
six comment blocks), F-005 is AC-142's second clause not being asserted by the
named test. Both live in `requirements.yml`/this card's prose, which this round
deliberately did not open. F-006/F-007/F-008 are info and belong to other
cards, as the sections below already record.

> **Superseded by fix round 2 — and this paragraph is itself the finding.**
> Review cycle 2 raised the F-005 wording above as **F-009** (high) and
> **ADR-0039/R3**: AC-142 had *no* second clause left to assert, because this
> very round's predecessor commit `7845cb5c` had already removed the clause the
> named test did cover. So the exemption was granted against a text that no
> longer existed, and what remained was a criterion verified by nothing. Both
> F-004 and F-005/F-009 are closed in *Fix round 2* below. Left standing here
> as the record of what was claimed when.

## [Fix round 2 — F-009 closed, 2026-10-31]

Review cycle 2 scored **8.5** (`min_score: 8` met) but left F-009 open at
**high**, so the card could not certify. This round closes it, and F-004 with
it. One finding, one assertion; `src/`, `requirements.yml` and `trace.yml` were
not opened.

### F-009 — AC-142's criterion had no control, and the cause was a commit of ours

AC-142's `then` says an unknown strategy filter is *"ignored and every puzzle
is listed — the CARD-066 status-filter pattern, not a refusal"*. Its named test,
`test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value`,
asserted four things: `/puzzles` is 200; `id="strategy"` renders;
`value="probe_contradiction"` renders; and the unknown request is 200 with
`"Unknown strategy"` in the body. **None of those is a claim about what is
listed.** So the one clause that distinguishes the demotion from the refusal it
replaced was the clause nothing checked — this card's own defect class
(a criterion whose `test:` resolves, so the validator counts it live and
nothing warns, while the test does not verify the stated outcome) re-created on
the card's own deliverable, and on the one criterion the owner personally ruled
on.

**The inversion was caused by this round's predecessor commit `7845cb5c`, not
by the implementer, and the card records it that way.** Cycle 1's F-005 was
written against a `then` with two clauses, one of which the named test *did*
cover. `7845cb5c` removed that clause — correctly: it was the second observable
that triggered the validator's `'then' bundles several outcomes` warning, which
is what AC-6's 10-removed figure is made of. What it left behind is exactly the
clause the test does not assert. Fix round 1 then exempted F-005 as "still
open, and not this round's" **while describing it in its pre-`7845cb5c`
form** — so the exemption was granted against a text its own predecessor commit
had already replaced. That is the whole mechanism, and it is a sequencing
failure in the fix rounds, not an oversight in the implementation.

### What the assertion is now

The test seeds **two** puzzles with different ladders into the app's own
in-memory store, fetches `/puzzles` and `/puzzles?strategy=LineLogic`, and
asserts **both pages list exactly those two**:

```python
assert listed(body) == {plain, guessy}
...
assert listed(unknown_body) == {plain, guessy}
```

The listing is read **off the response, not out of the store** — the store is
not what AC-142 is about. `_puzzle_table.html` gives every row a thumbnail at
`/api/puzzle/<id>/grid`, so the ids in those urls *are* the listing.

One detail in `listed()` is load-bearing and is commented as such: the id
pattern is `[\w-]+`, **not** `[^/]+`. The same page also carries the detail
modal's *script*, which builds that url from a JS template
(`${escapeAttr(puzzle.id)}`), and that literal is in the body whether or not a
single row is listed. With `[^/]+` the set is non-empty on an empty page, which
would have defeated the control the helper exists to be — and it was measured,
not reasoned about: the first run of the assertion failed on exactly that extra
member before the pattern was tightened.

**What was deliberately not done.** The `then` is *correct as written*; what
was missing is a control, so `requirements.yml` was not reopened. In
particular the `then` was **not widened** to put the second observable back: a
second `" and "` re-triggers the bundling warning the demotion was escaping and
would red AC-6. And F-009 was **not** closed by re-pointing at the flash —
under Y1 the flash still appears *and* the filter still applies, so
`"Unknown strategy"` is satisfied by both semantics. `monkeypatch.delenv(
"DATABASE_URL")` is kept: the test stays in-memory (its own comment records
that leaving it ambient once stalled the test for ten minutes against a local
Postgres), and no production database was contacted (G-8).

### Y1 re-fired — the acceptance condition for this round

Cycle 2's own plant, re-fired by `scratchpad/card318fix/y1_control.py` under the
protocol `final_mutants.py` established (SHA-256 asserted before the plant and
after the restore, restore from the in-memory original, `__pycache__` swept both
ends, `PYTHONDONTWRITEBYTECODE=1`, the plant located **by text** with an
asserted single occurrence, `-o addopts=` unquoted in the argv, and the
collected count asserted on every run). Y2/Y3 are in
`scratchpad/card318fix/y_discrimination.py`.

| cell | plant | target | verdict | fires at |
|---|---|---|---|---|
| — | *unmutated baseline* | named node | **1 passed** | — |
| — | *unmutated baseline* | the four files cycle 2 used | **88 passed** | — |
| **Y1** | `strategy = None` → `pass`, `app.py:2284` | named node | **FAILED — KILLED** | `test_strategies.py:560` `assert listed(unknown_body) == {plain, guessy}` |
| **Y1** | same | the four files | **1 failed, 87 passed** | same line |
| Y2 | `status = None` → `pass`, `app.py:2272` — the *unrelated* CARD-066 branch, three lines up | named node | **PASSED**, as required | — |
| Y3 | the flash's wording changed, the reset **kept**, `app.py:2281` | named node | **FAILED** | `test_strategies.py:557` `assert "Unknown strategy" in unknown_body` |

Y1 was measured **SURVIVING** by cycle 2 at the same site with the same
spelling; it is now killed, and the baseline it is matched against is the
identical **88 passed** figure cycle 2 recorded. Y2 and Y3 are there because a
control that reds on *any* edit to this route would be no evidence about the
strategy filter: Y2 breaks the neighbouring branch of the same shape and the
node stays green, and Y3 keeps the reset while moving only the flash — so the
flash assertion reds at `:557` and the listing assertion stays green. The two
assertions observe different things and neither absorbs the other. `app.py`'s
sha256 is `403fb957…4ce4` before every plant and after every restore, and
`git status --porcelain -- src/ tests/ meta/architecture/` is empty.

### Gate — node ids, impact set, untouched files

**G-6, nothing deleted, renamed, skipped or merged.** Derived by `ast` from each
revision's own source, not read off a summary: `tests/test_strategies.py` yields
**17** test node ids at `2ee0be38` and **17** after, identical as sorted sets
(nothing added, nothing removed), **zero decorators** on any of them — so no
`parametrize`, no `skip`, no `xfail`. `tests/test_solver_strategies.py` is
**unchanged** and stays at **16**. pytest agrees: **33 collected** across the
two, before and after. The round extends an existing test in place and adds no
node id; the new `listed()` helper is nested inside that test and is not one.

*(Note for the record: cycle 2's G-7 table attributes 16 to `test_strategies.py`
and 17 to `test_batch_generator.py`. Re-derived here the two are the other way
round — `test_strategies.py` 17, `test_batch_generator.py` 16 — and fix round
1's own table above already had them that way. The total, 109, is unaffected.)*

**Impact set**, `-o addopts= -rs`, on the committed code, per-file counts
derived separately and summing to the run's total:

| file | collected |
|---|---|
| `tests/test_strategies.py` | 17 |
| `tests/test_solver_strategies.py` | 16 |
| `tests/property/test_solve_strategies.py` | 5 |
| `tests/test_puzzle_review_book_filter.py` | 20 |
| `tests/test_puzzle_review_bulk_read.py` | 35 |
| `tests/test_batch_generator.py` | 16 |
| **total, counted from the rows** | **109** |

**109 passed, 0 failed, 0 skipped**, `grep -c '^SKIPPED'` = **0** — so there is
no skip to attribute, and in particular no DB-mode test skipped green for want
of a `nonogram_test` database: the `[db]` parametrizations in
`test_puzzle_review_bulk_read.py` appear by name in the run and really ran
(G-7).

**Untouched, and verified rather than asserted.** `git diff ef242847..HEAD
-- src/` is **empty** — nothing under `src/` changed on the whole branch, so the
shipped behaviour at `app.py:2277-2284` is as it was and the defect really was
in the verification. `git diff 7845cb5c..HEAD -- meta/architecture/` is
**empty**, so `requirements.yml` and `trace.yml` are untouched by both fix
rounds: AC-6's figure — merge-base `ef242847` 0 err / 100 warn → HEAD 0 err /
90 warn, **10 removed / 0 added as sets** — is unmoved and was not re-measured,
and CARD-317/CARD-316 keep their queue position on that file.

### F-004 closed, with the figures re-derived

Cycle 2 accepted F-004 at low and said correcting it was optional. It is
corrected, because this round was already in the card: the *Shared-file
etiquette* section's counts are now **five changed values** (naming which five)
and **six comment blocks**. The basis is stated there and is my own derivation,
not the review's numbers — both revisions parsed with `yaml.safe_load` and
flattened to leaf paths keyed by `id` rather than by list index (0 keys added,
0 removed, 5 changed leaves), and the comment figure from `difflib`
`SequenceMatcher` opcodes over the two line lists (62 added lines, 57 of them
comments, in 6 runs of consecutive line numbers). It reproduces cycle 2's
structural figures exactly.

### Still open after fix round 2

**F-006, F-007, F-008** — all `info`, all carried unchanged and all belonging to
other cards: the `PropertyTest_*` ref population (a convention card sequenced
after CARD-317/CARD-316), the review-YAML dead-ref silencing (whose fix is a
one-line change in forge_1's `symbol_exists`, which is read-only from here, plus
a `meta/review/` sweep), and FR-029's intake-era `evidence` block (flagged in
place, because `trace.yml` is auto-generated). The sections below already record
all three. **F-005 is closed by F-009's fix**: it was the same criterion's
missing assertion, and RC-1 is the cause of both.

## Worktree notes

### The premise, re-derived — and disconfirmed

Step 1 was a walk of `src/`, not a read of this card's table. **FR-029's
behaviour is not missing.** CARD-072 (done) shipped all of it and covered it in
`tests/test_strategies.py` (521 lines, 17 tests) under its own card-local names
(`test_strategies_*`). The registry's `test:` refs were written against the
pre-implementation design and were never re-pointed, so ten criteria named
symbols no definition in `tests/` ever had while reading as mechanically
checked.

Seams found in `src/`, all live:

| seam | where |
|---|---|
| the solve's ladder | `solver/search.py:629` `rungs=tuple(...)`, `SolveSignals.rungs` |
| `guess` appended off `branch_nodes` | `orchestrator.py:1302` (`record_difficulty`) — the one place it happens |
| a second, independent derivation | `admin/regrade.py:486` `_strategies_used` |
| random batch persistence | `admin/batch_generator.py:474` `strategies_used=list(puzzle.strategies)` |
| image batch persistence | `admin/app.py:1993`, same value, different call site |
| JSON export | `export/json_export.py:117` write, `:222` decode |
| the strategy filter | `admin/puzzle_review.py:1687` (in-memory), `:1793` (SQL), vocabulary pinned at `:29` `STRATEGY_NAMES` |
| unknown-value handling | `admin/app.py:2279` — flashes, then **ignores** |
| the detail page | `templates/generated_puzzles.html:62` `<ol class="strategies">`, `/api/puzzle/<id>/details` |

`requirements.yml`'s `evidence:` block for FR-029 is the 2026-09-12 **intake**
state and is now wrong in every particular (it says the column is written as
`[]` and the export carries no strategies). Flagged in place with a comment;
not deleted, because it is a record of what was true when the FR was written.

### Verdicts — all eleven, nothing unclassified (AC-1, ADR-0039/R2)

The brief and this card both say **ten**. Measured, it is **eleven**: AC-135's
ref `TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve` is equally absent
from `tests/`, and does not warn only because the validator's check is a text
search and the name occurs in **9** review YAMLs and **79** kanban cards (counted
from `grep -rl`, not from a truncated listing — the first pass of this very note
said "8 and 10", read off a `head -20`). Two of those
YAMLs state it "exists and passes" (`20260924T104859Z-CARD-145-cycle3.yml`,
`20260930T123942Z-CARD-139-cycle1.yml`). This is the masking the memory note
"Review YAMLs revive dead check refs" predicts, now measured on a second ref.

| criterion | behaviour in `src/`? | verdict |
|---|---|---|
| AC-135 | yes | implemented-and-tested, ref misnamed **+ the `given` does not generate** |
| AC-136 | yes | implemented-but-untested (no clock injection existed) |
| AC-137 | yes | implemented, tested only at the aggregate; untested through a real branching solve |
| AC-138 | yes | implemented-and-tested, ref misnamed |
| AC-139 | yes, **both** paths | random tested; **image path untested** |
| AC-140 | yes | implemented-and-tested, ref misnamed; order never pinned |
| AC-141 | yes | implemented-and-tested, ref misnamed |
| AC-142 | **yes, but the opposite of what the AC says** | **[BLOCKER] owner decision** |
| AC-143 | yes | API order tested; **rendered order untested** |
| EC-017 | yes | property untested; the branched arm was unreachable from a random corpus |
| EC-018 | yes | determinism half tested; **end-to-end-preserved half untested** |

**Partition.** implemented-but-untested (or under-tested) → **10**, repaired by
test. not-implemented → **0**. behaviour present but contradicting its AC → **1**
(AC-142, blocked). **orphaned by the CARD-106 renumbering → 0.**

### Step 5 — the orphan hypothesis is false

CARD-106 ("AC-122 through AC-143 each mean two different things", done) decided
**explicitly not to renumber**: "Both runs are cited by tests and by closed
cards." Its deliverable was a note in `requirements.yml` and a banner on each
wave-0 card. The `# NB CARD-034/035/037 ... (CARD-106)` comments on FR-029 *are*
that note. Measured: `requirements.yml` holds each of AC-135..AC-143 exactly
once (and EC-017/EC-018 once each). The collision is with the wave-0 web-UI
cards' **own local** AC numbering — CARD-034 owns 135-138, CARD-035 owns
139-142, CARD-037 owns 143, which is exactly what the `# NB` lines attribute.
**Nothing was orphaned and no id was reused in the registry.**

### [BLOCKER] owner decision needed: AC-142 — build or demote?

AC-142's `then` is *"the request is refused on the CARD-066 error branch and no
puzzles are listed"*. The shipped route (`admin/app.py:2279`) flashes
`Unknown strategy {value!r} — showing every strategy instead` and then **sets
the filter to `None`**, listing every puzzle. That is deliberate and its comment
says why: filtering on a name outside the vocabulary "would show an empty list
that reads as 'nothing matches your other filters'". It is also exactly what
CARD-066 did for the status filter, which AC-142 cites as its model — so the AC
appears to have mis-stated the very pattern it names.

Two honest outcomes, and both are the owner's:

1. **Demote the AC** — rewrite the `then` to "reported and then ignored; every
   puzzle is listed" and point it at the existing
   `tests/test_strategies.py::test_the_puzzle_list_route_offers_the_filter_and_ignores_an_unknown_value`.
   Zero code change. Makes the registry describe the product.
2. **Build the refusal** — change the route to refuse. That is a **product
   behaviour change** on a live admin page, in a tech-debt card. G-2 forbids
   doing it silently.

**Left dead and untouched pending that call.** Writing a test for whichever
side is easier to assert is precisely the defect this card family exists to
remove (G-1). The dead-ref count therefore moves **9**, not 10 — see AC-6 below.

### TDD — red→green, one line per criterion

`TDD: true`, but every criterion's behaviour **predates** its test (that is the
card's finding). So "red first" cannot mean "red because the feature is
missing". The red of record is the AC-3 mutant: each test was written from the
AC's `then` clause, run, and then shown red on a mutant in the behaviour it
covers and green on restore. Two tests were additionally red on their first run
for reasons that were real findings, not typos:

- `AC-136: TestSolveStrategies_SameCluesSameListUnderDilatedClock red→green` —
  **red on first run** at `assert slow.reads > 0`: the solver reads **no clock
  at all** when `deadline is None`, so the dilated clock was not an input and
  the test would have been vacuous. Fixed by passing a far deadline; the
  measurement is now `reads=3`, apparent elapsed `3.0` vs `150.0`.
- `AC-140: TestExport_JSONCarriesStrategiesInOrder red→green` — **red on first
  run**: `ExportPayload` is slots-based and has no `__dict__`; switched to
  `dataclasses.replace`.
- `AC-135: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve red→green` (M1/M3)
- `AC-137: TestSolveStrategies_GuessPresentWhenSearchBranched red→green` (M1)
- `AC-138: TestSolveStrategies_GuessAbsentForLineSolvable red→green` (M1 discriminates: correctly PASSES)
- `AC-139: TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage red→green` (M6 random, M9 image)
- `AC-141: TestPuzzleReview_FiltersListByStrategy red→green` (M5)
- `AC-143: TestPuzzleReview_DetailShowsStrategiesInOrder red→green` (M7)
- `EC-017: TestPropertySolveStrategies_GuessIffSearchBranched red→green` (M1, M2)
- `EC-018: TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd red→green` (M3, M8)

### Mutant table (AC-3)

Harness `scratchpad/card318/mutate.py`. Protocol: SHA-256 of the target
asserted **before each mutant and after each restore** (all 9 `restore=ok`),
restore from the in-memory original rather than `git checkout --` (which
restores to HEAD and would have reverted the work, not the mutant),
`PYTHONDONTWRITEBYTECODE=1` with a `*.pyc`/`__pycache__` sweep before and
after each, `-o addopts=''`, and **one cell per node id** — a file-level verdict
would hide an arm that never ran.

| # | kind | target | node | verdict |
|---|---|---|---|---|
| M1 | deletion | `orchestrator.py` — the `guess` append | AC-137 aggregate | **FAILED** |
| M1 | " | " | AC-138 aggregate | PASSED — correct discrimination: deleting an append cannot change a list that never had `guess` |
| M1 | " | " | EC-017 corpus | **FAILED** |
| M2 | deletion | `regrade._strategies_used` — the guess branch | EC-017 corpus | **FAILED** |
| M2 | " | " | EC-017 hand-set counts | **FAILED** |
| M3 | deletion | `json_export` — the `strategies` key | AC-140 written | **FAILED** |
| M3 | " | " | AC-140 decoded | **FAILED** |
| M3 | " | " | AC-140 reordered | **FAILED** |
| M3 | " | " | EC-018 end-to-end | **FAILED** |
| M4 | replacement (order only) | `json_export` — `sorted(...)` | AC-140 written | **FAILED** |
| M4 | " | " | AC-140 reordered | PASSED — see below |
| M5 | deletion | `puzzle_review` in-memory strategy filter | AC-141 | **FAILED** |
| M6 | deletion | `batch_generator` — `strategies_used=[]` | AC-139 random | **FAILED** |
| M7 | replacement (order only) | `generated_puzzles.html` — `|reverse` | AC-143 rendered | **FAILED** |
| M8 | replacement (clock becomes an input) | `search.py` — ladder dropped when the solve *looks* slow | AC-136 | **FAILED** |
| M8 | " | " | EC-018 dilated clock | **FAILED** |
| M9 | replacement | `app.py` image route — `strategies_used=[]` | AC-139 image | **FAILED** |
| M9 | " | " | AC-139 random | PASSED — correct discrimination: the mutant is in the image path only |

Three mutants **survived on their first run** and each was a real defect, in my
tests or in the mutant. All three are recorded rather than quietly re-rolled:

- **M6 and M9 survived.** `add_puzzle` **derives** the list whenever its caller
  hands it an empty one, so a generator passing `[]` still produces rows whose
  column holds a real list — the store's safety net was hiding both call sites,
  and a row-only assertion could not tell the two apart. The two tests now also
  **spy on the hand-off**. Both mutants red after that fix — but the predicate
  on the hand-off was only "truthy and in-vocabulary", which cycle 1 measured
  as weaker than AC-139's wording (F-003). Since **fix round 1** both arms
  assert the handed and stored lists **equal** that puzzle's own re-derived
  list, and R1-R4 in the fix-round section are the re-fired measurement.
- **M8 survived twice.** First version read `time.monotonic` from the `time`
  module directly, which the tests do not patch (they patch
  `solver.propagate.time`); second version sliced the ladder by a parity, which
  cannot discriminate when the ladder has **one** rung — and `_settled_grid()`
  produces exactly `('simple_overlap',)`. Third version drops the ladder when
  the apparent elapsed time crosses a threshold, which the 1x/50x pair
  separates deterministically (3.0 vs 150.0). A bad mutant looks exactly like a
  strong test; only re-deriving it caught this.

**M4's PASSED cell corrected a false claim in my own docstring.** The test had
claimed it caught a sorting renderer. It does not: `sorted(reversed(STRATEGIES))`
*is* `reversed(STRATEGIES)` for this fixture. The sorting mutant is caught one
test up. The docstring now states what was measured instead of what was assumed
— which is the same class of defect as the dead refs themselves.

M4, M7, M8 and M9 are **replacements, not deletions**: a deletion cannot express
"the order changed" or "elapsed time became an input", because neither is
removable. Stated rather than passed off as deletion-only (AC-3's wording).

### G-3 — the ref instrument, proven in both directions

`scratchpad/card318/resolve_refs.py` resolves a ref by **`ast` definition**
(`ClassDef`/`FunctionDef`) over `tests/**/*.py`, never by `git grep -lw`
(`\b` is undefined in POSIX ERE and silently matches nothing). Proven on every
run: it finds a known class (`TestComponentMap_EveryComponentIsListedExactlyOnce`),
a known function (`test_reports_unique_solution`) and rejects a nonsense name
(`NonsenseControl_ZZZ`). 9,742 distinct definition names indexed.

### G-9 — the validator figure, with its binary

Binary of record, from `meta/kanban/config.yml:38`:
`/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py --root meta/architecture --phase all`
(**not** the plugin cache copy, whose single ADR-0025 error is a regex artefact).

| | errors | warnings |
|---|---|---|
| branch at start (== main) | **0** | **100** |
| branch, committed | **0** | **91** |

Warning **sets** diffed line by line, review YAMLs untouched and therefore
equal on both sides: **9 removed, 0 added.** The nine are AC-136, AC-137,
AC-138, AC-139, AC-140, AC-141, AC-143, EC-017, EC-018.

**AC-6 reads 9, not 10.** The tenth is AC-142, held open for the owner above.
A tenth could only be bought by asserting a behaviour the owner has not chosen.

One mechanism worth recording for the next card: the validator's check is
`git grep`, which **only searches tracked files**. The nine warnings did not
move until the new tests were committed. A figure taken from an uncommitted
tree is meaningless here.

### G-7 — skip attribution, by name

**Zero skips** across the impact set (`-rs`, `-o addopts=''`): `707 passed` with
no `SKIPPED` line. Specifically, no DB-mode test skipped silently for want of
`nonogram_test` — the memory note's "DB tests skip silently" failure mode did
**not** fire here, because both database-touching arms are pinned to a real
SQLite file (`_sqlite_scope`, per G-8) rather than reading `DATABASE_URL`:

- `EC-018 :: test_the_aggregate_the_stored_row_and_the_export_hold_one_list` — real SQLite file, a real `strategies_used` column.
- Every Flask-driven test deletes `DATABASE_URL` via `monkeypatch.delenv` before `create_app`, so none can reach `nonogram_poc` (G-8).

### G-6 — nothing deleted, renamed, skipped or merged

Proven by `git diff main --name-status -- tests/`: **two files, both `A`
(added)**. No pre-existing test file was touched at all, so no node id —
`parametrize` ids included — can have moved. The new files collect **21 node
ids** across **10 classes**, verified by `--collect-only -q` with
`-o addopts=''`.

That verification is not a formality. `pyproject.toml` leaves `python_classes`
at pytest's default `Test*`, so the registry's `PropertyTest_*` naming is
**structurally uncollectable**: such a class never runs, with no skip and no
error. EC-017/EC-018 are therefore named `TestPropertySolveStrategies_*` and
`requirements.yml` is re-pointed at those names.

### Belongs to another card

1. **The `PropertyTest_*` refs across `requirements.yml` resolve only by
   docstring text.** Counted from the rows: **38** `test:`/`ref:` lines carry a
   `PropertyTest_*` value, over **45** distinct such names in the file. Measured: `grep -rn "^class PropertyTest_\|^def PropertyTest_" tests/`
   returns **zero** definitions, yet most of those refs do not warn — including
   FR-006's mandatory `PropertyTest_Solver_NeverFalsePositiveUniqueness`, which
   the validator resolves against line 3 of `tests/property/test_solver_uniqueness.py`'s
   **module docstring**. The tests behind them are real and do run under
   `test_*` names; the *refs* are soft. Not fixed here: it is a board-wide
   convention change, well outside a tech-debt card's scope, and it touches the
   file CARD-317 and CARD-316 are queued on.
2. **Two review YAMLs assert a test exists and passes when it does not** —
   `20260924T104859Z-CARD-145-cycle3.yml` ("exists and passes") and
   `20260930T123942Z-CARD-139-cycle1.yml` ("green in the full suite"), both for
   `TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve`. Worth a pass over
   the review corpus for the same shape.
3. **FR-029's `delivery: CARD-072` and its `evidence:` block** disagree with the
   code by a whole card. Commented in place here; a sweep for other FRs whose
   intake evidence outlived its intake belongs elsewhere.

### `trace.yml`

FR-029's row lists the same eleven names. The two property names are renamed to
match, and a dated note records that the row's prose is the 2026-09-12 intake
state and is now wrong in detail — it still lists `cross_line` as a rung (ADR-0029
dropped it), still describes the `[]` writes and the hardcoded sample, and still
says an unknown filter value is "refused", which never shipped. The file is
marked auto-generated (`/forge:architect-synthesis --trace-only`), so the prose
is flagged rather than rewritten by hand.

### Shared-file etiquette

`meta/architecture/requirements.yml` is shared with CARD-317 and CARD-316, which
rebase onto this. Changes are **additive and local to FR-029**: **five
changed values** — AC-135's `given`, AC-142's `then` *and* its `test:`, and
EC-017's and EC-018's `test:` — and **six comment blocks**. No untouched entry
was reflowed, no key reordered, no id renumbered. `yaml.safe_load` parses the
result.

Those two counts were wrong until fix round 2 (review cycle 2, F-004): the
sentence said "three `test:` values, one `given`, and four comment blocks",
omitting AC-142's `then` and two blocks. Both figures are **re-derived here,
not copied from the review**: both revisions of the file parsed with
`yaml.safe_load` and flattened to leaf paths keyed by `id` rather than by list
index (so a reordered list cannot read as a change), then compared —
`ef242847` → `2ee0be38` gives **0 keys added, 0 keys removed, 5 changed
leaves**, exactly the five named above. The comment figure is text-level,
because comments are not in the parsed tree: `difflib.SequenceMatcher` opcodes
over the two line lists give **62 added lines, 57 of them comments, forming 6
runs of consecutive line numbers**. The substantive half of the claim — nothing
reflowed, nothing reordered, nothing renumbered, still parses — is what the 0/0
confirms, and that is the half CARD-317 and CARD-316 depend on.

## Review cycle 3 — CERTIFIED at 9.0, and the two residues it routes

Cycle 3 is the last `max_cycles` allows, and it certifies: `min_score` met with
**no open Critical or Important**. Every prior finding was re-derived on the
reviewer's own instruments rather than accepted from the fix round's report —
F-004's figures by a route that **uses no YAML parser at all** (a `-U0` diff
with each removed line paired to the added line carrying the same key), which
independently reproduces 5 changed values / 62 added lines / 57 comments / 6
blocks, with `git diff --numstat` agreeing at 62/5.

Y1/Y2/Y3 all re-fired: Y1 **killed** at `tests/test_strategies.py:560`, Y2
**survives** (so the control is not a blanket red on any edit to the route),
Y3 **killed** at `:557` (so the flash assertion stays a live, separate control
and neither absorbs the other). The load-bearing regex was measured both ways:
on a page listing nothing the committed `[\w-]+` gives `set()` while `[^/]+`
gives `{'${escapeAttr(puzzle.id)}'}` — the looser pattern really would have
defeated the control.

**Two Minor findings are routed, not fixed, and neither blocks the merge.**

- **F-010 — the admin list route's strategy wiring has no positive control.**
  Nulling `strategy=strategy` in the `PuzzleFilter` construction at
  `src/nonogram/admin/app.py:2304` stops the dropdown filtering **entirely**
  and all 109 FR-029 tests stay green. The hole is *between* criteria rather
  than inside one: AC-142 is about the *unknown* value, which is true by
  construction under that plant; Y1 cannot reach it because its own site
  becomes dead code; and AC-141's "exactly the 3 puzzles are listed" is
  verified at the **service** seam (`service.filter_puzzles`), never at the
  route. **Pre-existing** — `src/` is a 0-line diff across this whole branch —
  and not an AC violation as worded. Owed by whichever card next touches the
  admin list route: one `?strategy=guess` route-level assertion using the same
  response-side helper, then kill the plant.
- **F-011 — a committed instrument is blind.** `scratchpad/card318fix/probe_listing.py:37`
  matches `[0-9a-fA-F-]+`, which cannot match `puzzle_000001`; run on this head
  it prints `rows=[]` for all three queries on a page it then shows contains
  both ids, with no positive control — the "cannot distinguish zero from blind"
  shape ADR-0039/R4 rules out. **Not an R4 violation**, because the card cites
  this file nowhere, so no committed figure rests on it, and the claim it
  explored is independently true. Hygiene: fix the pattern with both controls,
  or delete it.

**Out-of-scope, recorded for the convention card after CARD-317/CARD-316:**
ADR-0029 carries two `check:` refs in the `Property`/`Test_` family and
**neither has a definition anywhere** — they resolve only through index lines in
test-file *docstrings*. So the deterministic lens reports `dead_check_ref: []`
while two ADR-0029 rules are mechanically unverified in substance. This is
F-006's mechanism with fresh evidence, and it is the same shape as CON-019's
ref, which is why it belongs with that family rather than here.

**One measurement corrects a standing orchestrator note.** The "no `nonogram_test`
database ⇒ DB-mode tests skip green" hazard, which this card's briefs carried
three times, is **stale for this box**: CARD-244's `tests/db_name.resolve_test_database_url`
derives a **per-worktree** database, and the 15 `[db]` node ids in
`tests/test_puzzle_review_bulk_read.py` give **15 passed, 20 deselected, 0 skipped**.
Confirmed independently by the orchestrator. The instruction (assert zero skips)
was right; the stated cause was wrong, and a wrong cause sends the next round
looking in the wrong place.
