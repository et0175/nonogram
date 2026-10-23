# CARD-287: One class is a quarter of the suite and two thirds of its growth — and it is not rendering anything

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/287-the-door-axis-guard-costs-a-quarter-of-the-suite
**Worktree:** —
**Source:** the 2026-10-23 solo duration profile (`meta/profiling/suite-durations-20261023.txt`, commit `ae164099`), read against the 2026-10-15 one; CARD-218's implementation round, which measured this file read-only and reported that its own mechanism would not touch it; the orchestrator's 2026-10-24 breakdown, recorded below
**Idea:** —
**Wave:** —
**Created wave:** 56
**Deferred waves:** 0
**Depends on:** CARD-276 <!-- NOT scheduling. CARD-276 rewrites the walker that costs the time (alias resolution as a fixed point), so optimising it first would both waste the work and FREEZE its current shape in cost-pinning tests. See "Why this waits on CARD-276", and the measurement CARD-276 is asked to take. -->
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**`tests/test_book_export_interior_cover.py` is 344.29 s of a 1426.16 s suite —
24.14 % — and 95.3 % of that is one class.** Every figure below is from the two
committed duration artefacts and is reproducible by parsing their
`<secs>s <phase> <nodeid>` records; none of it is an estimate.

| | 2026-10-15 | 2026-10-23 | change |
|---|---|---|---|
| the file | 14.09 s, 55 tests | **344.29 s**, 90 tests | **+330.20 s** |
| per test | 256 ms | **3 825 ms** | **×14.9** |
| share of attributed | 1.53 % | **24.14 %** | |
| the whole suite (attributed) | 920.63 s | 1426.16 s | +505.53 s |

**So this one file is 65.3 % of everything the suite's cost grew by.** The test
count grew 1.64×; the cost grew 24.4×.

Inside the file, the concentration is sharper still:

| | secs | share of file | tests | ms/test |
|---|---|---|---|---|
| `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage` | **327.94 s** | **95.3 %** | 23 | **14 258** |
| the file's other **14** classes | 16.35 s | 4.7 % | 67 | 244 |

The file's phase split is `call` **342.24 s**, `setup` **2.05 s**, `teardown`
**0.00 s** — so this is not fixture cost and there is no teardown to reclaim.
Its ten most expensive tests, all in that one class: **81.03, 67.08, 44.69,
41.13, 24.85, 19.11, 13.45, 8.98, 7.05, 6.68 s**.

### What it is NOT, so no successor re-derives it

**It is not rendering.** CARD-218's implementation round instrumented this file
read-only on 2026-10-23: of 344.29 s, **9.25 s is rendering at all** and
**2.52 s is recoverable duplicate** — 0.7 % of the file. Sharing a render once
per module, the mechanism CARD-218 carries, recovers under one percent here.
**Do not open this card by hoisting a fixture.**

**It is not setup, either**, which is worth stating because the board has
already acted once on the belief that setup is where suite time lives: 2.05 s
of this file's 344.29 s is `setup`, and suite-wide the split is setup 6.79 % /
call 91.79 % / teardown 1.42 %.

**And it is not a slow product.** This class contains no product assertions
about a rendered book. It is an in-tree **static-analysis guard**: a ~2 100-line
AST walker (`_page_positions`, with nested `resolve`/`feed`/`receiver_seen`
resolvers) that proves every page-position count in
`src/nonogram/admin/book_pdf_generator.py` goes through one derivation, plus a
planting harness (`_plant`, `_plant_refusals`, `_outcome`) that writes mutated
source variants and re-runs the walker to prove each shape is caught or
explicitly refused. It is the guard CARD-206 opened and CARD-262 declared, and
it is **good** — 760 of 816 calls refusing with nothing exempted. Its cost is
the price of its evidence, and nobody has ever looked at the bill.

### The one thing that is certainly wrong, and is a fact rather than a theory

**There is no memoisation anywhere in these 4 749 lines.** Grepped
2026-10-24: zero `functools.lru_cache`, zero `functools.cache`, zero
`@cache`, and **zero fixtures of `module`, `class` or `session` scope in the
entire file**. Against that: **20 call sites of `_page_positions`**, 7 of
`_plant`, 9 of `_plant_refusals`, 7 of `_outcome`, 11 of `_bare_literals`,
3 of `_counting_expressions`, 3 of `_door_position_slots`.

That is a shape, not yet a cause — which is why AC-1 is to measure, not to fix.
The two candidate causes need different remedies and the split between them is
unknown:

1. **Re-derivation of one identical analysis.** Every unplanted call of
   `_page_positions` over the same module is the same computation, and there
   are up to 20 entry points. If this dominates, the remedy is caching keyed on
   the source text — cheap, and it changes no verdict by construction.
2. **The plants.** Each planted variant is a genuinely different input, so no
   cache helps. If this dominates, the remedy is a cheaper planting idiom or a
   smaller planted module — and **that is where this card can do damage**, so
   it is fenced by G-1 below.

### Why this waits on CARD-276

CARD-276 is `ready`, its dependency (CARD-262, `faea50a5`) is merged, its
`Touches:` is **this same file**, and its subject is **this same class** — it
rewrites the walker's alias resolution into a fixed point. So:

* optimising the walker now would be thrown away, and worse, the cost-pinning
  tests this card adds would **freeze the shape CARD-276 must change**;
* CARD-276's own fix — following aliases to a fixed point instead of one step —
  is more analysis, not less, and may make 327.94 s materially worse;
* and CARD-276 will pay this cost itself: its impact-scoped cycle gate runs this
  file, so **every one of its review cycles spends ≈ 344 s here**.

**What CARD-276 is therefore asked to do, and this card records the request so
it is not lost:** take this class's per-test durations before and after its
change (`--durations=0 --durations-min=0` over this file alone is enough; it
needs no full suite and no lock) and write both into its card. If its fix makes
the class slower, that is not a reason to refuse the fix — the guard's
correctness was bought over four gating cycles across two cards — but it must
be a **measured** change, surfaced at its own merge gate rather than found by
the next profile.

### Why the saving compounds — the figure that makes this a P2 and not a P3

`review.test_scope` is `impact`, so this file is not merely a merge-gate cost.
Measured 2026-10-24 for CARD-218's two-test-file diff: the derived impact set is
**24 files, 448.77 s — 31.47 % of the suite — of which 344.29 s (77 %) is this
one file**, for a diff whose own two files cost 8.86 s. Every book-adjacent
card now pays ≈ 344 s per review cycle for this class, and this board runs up
to three cycles per card. (Whether the derivation *should* pull it in at all is
CARD-286's question, not this one's; the two cards attack the same bill from
opposite ends and neither waits on the other.)

## Acceptance criteria

- **AC-1** (happy, measure before fixing): *Given* this class, *when* its cost
  is profiled per test and attributed by function, *then* the card records what
  share of 327.94 s is (a) re-derivation of an identical analysis, (b) distinct
  planted analyses, (c) anything else — each as seconds and a share, from
  `cProfile` cumulative time over named call sites, not from a guess. No
  optimisation may be committed before this table is on the card. (recorded,
  verified by review)
- **AC-2** (happy, the saving): *Given* the remedy AC-1's table selects, *then*
  the class's wall-clock falls by a figure the card states in advance and
  measures after, over three runs of each arm **interleaved** (not two blocked
  batches), with load averages recorded at the start and end of each.
  (test: `TestSuiteProfile_*` records the artefact; the delta is recorded)
- **AC-3** (guard, the verdict set is unchanged — the one that matters):
  *Given* the class before and after, *when* each of its planted shapes is run,
  *then* **every plant's outcome is identical**, asserted as an equality over
  the full set of (plant, verdict, refusal-reason) triples captured before the
  change and compared after — not as "the tests still pass". (test:
  `TestBookPdfStructure_*::test_every_plants_verdict_is_what_it_was_before_card_287`)
- **AC-4** (guard, the cache cannot go stale): *Given* a memoised analysis (if
  AC-1 selects caching), *when* the analysed source changes, *then* the cached
  answer is not reused — proved by a control that **plants a change and fails
  if the stale answer is returned**. A cache keyed on anything other than the
  analysed text is a wrong answer waiting for a plant. (test:
  `TestBookPdfStructure_*::test_the_analysis_cache_is_keyed_on_the_source_it_read`)
- **AC-5** (edge, no plant was dropped): *Given* the planted-shape inventory,
  *then* its **count and its node ids are asserted as an equality** against the
  pre-change set, so a saving cannot come from planting fewer shapes. A floor is
  not enough; it must be an equality in both directions. (test:
  `TestBookPdfStructure_*::test_the_planted_shape_inventory_is_the_declared_one`)
- **AC-6** (guard, the walker's reach): *Given* the production module the
  walker reads, *then* the set of call sites it classifies, and each one's
  classification, is identical before and after — the measurement CARD-262
  landed (760 of 816 refusing, nothing exempted) re-derived and compared, not
  cited. (test: `TestBookPdfStructure_*::test_the_classified_call_sites_are_the_ones_card_262_measured`)
- **AC-7** (happy, collected count): *Given* the file, *then* its collected
  count is unchanged except for controls this card adds, each named on the card,
  and **no test is merged, parametrised away, skipped or deleted** — verified by
  set difference over sorted node ids, not by comparing two totals. (recorded)
- **AC-8** (happy, the suite figure): *Given* the next full-suite profile,
  *then* the card records this file's new seconds and share against 344.29 s /
  24.14 %, and against the `meta/profiling/suite-hotspots-*.md` ranking its own
  guard regenerates. (recorded, not asserted)

## Guardrails

- **G-1: do not buy time by guarding less.** This is the whole risk of this
  card. The guard's reach cost four gating review cycles across CARD-206 and
  CARD-262, and its family's signature is *claiming a reach it has not
  measured*. Fewer plants, a narrower walk, a shallower receiver resolution, a
  shorter depth bound or a widened exemption are **regressions dressed as
  optimisations**, and AC-3/AC-5/AC-6's three equalities exist to make each of
  them red. If the only available saving requires weakening the guard, the
  correct outcome of this card is to **say so and close** — a slow guard that
  holds beats a fast one that does not.
- **G-2:** do not edit `src/**`. The analysed module is the subject of the
  guard, not of this card; changing production code to make the walk cheaper
  would invalidate every figure above and is a different card.
- **G-3:** do not move the class to a different file, mark it, or make it opt-in
  (no `-m slow`, no env gate, no `skipif`). The board's rule is that a test
  fails or skips **loudly**; a guard that does not run in the default suite is
  not a guard, and `tests/test_guard_integrity.py`'s silence census covers
  `tests/`. Making this cost invisible is not making it smaller.
- **G-4:** the frozen render set in `meta/profiling/rank_durations.py` is
  defined by grepping eight idioms over `tests/**/*.py`, and
  `tests/test_suite_profile.py` asserts the set as an **equality**. This file is
  in it. Do not remove the file's last occurrence of any of those eight names,
  and do not add a new test file that contains one, without re-deriving that
  snapshot — and that snapshot lives under `meta/`, which is never committed
  from a worktree. Run `tests/test_suite_profile.py` explicitly; the impact
  derivation does select it, but confirm rather than assume.
- **G-5:** run `tests/test_browser_fixture_scope.py` explicitly too. It names
  none of this card's selectors and reaches its subject through a
  `--collect-only` subprocess, so no scoped selection finds it — which is how
  CARD-271 reached its merge gate with 27 unregistered node ids after four
  clean scoped gates.
- **G-6:** no new dependency (ADR-0006/R1). `functools` and `ast` are stdlib;
  a profiler used to produce AC-1's table is a dev-time tool invoked by hand,
  not an addition to `pyproject.toml`.
- **G-7:** out of scope — the guard's **correctness** (CARD-276 owns it, and
  this card waits on it), whether the impact derivation should select this file
  at all (CARD-286), retiring subsumed tests anywhere (CARD-220), and the
  file's other 14 classes, which are 16.35 s between them and not worth a line
  of churn.

## Architecture context

- **FR:** — (test-suite cost; the guarded property belongs to FR-042's page plan
  and is CARD-262's, not this card's)
- **ADR:** ADR-0039/R1 (a claim needs a control that can fail — AC-3, AC-4,
  AC-5, AC-6 are all two-sided equalities for that reason), ADR-0039/R2
  (a guard set derived from an enumerable authority is default-deny — the
  planted inventory and the classified call-site set are both such sets, which
  is why AC-5 and AC-6 are equalities and not floors), ADR-0006/R1 (no new
  dependency).
- **CON:** —
- **Components:** none (tests only).
- **Trace:** not applicable.

## Worktree notes

—
