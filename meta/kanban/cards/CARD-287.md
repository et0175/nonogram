# CARD-287: One class is a quarter of the suite and two thirds of its growth — and it is not rendering anything

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/287-the-door-axis-guard-costs-a-quarter-of-the-suite
**Worktree:** —
**Source:** the 2026-10-23 solo duration profile (`meta/profiling/suite-durations-20261023.txt`, commit `ae164099`), read against the 2026-10-15 one; CARD-218's implementation round, which measured this file read-only and reported that its own mechanism would not touch it; the orchestrator's 2026-10-24 breakdown, recorded below
**Idea:** —
**Wave:** 62
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

> **⚠ REWRITTEN 2026-10-27 against measured figures — see
> `## [REWRITTEN]` at the foot of this card. CARD-292 took 81 % of this card's
> opportunity before it ran. Every figure in this section is from a run taken
> after that card merged; the superseded table is preserved in the REWRITTEN
> section rather than left here to be acted on.**

**The target class is 61.62 s of a 1270.34 s suite — 4.85 % — and it is 58.3 %
of its file.** Measured 2026-10-27 at `2fddaccc` with
`--durations=0 --durations-min=0` over this file alone, 132 passed in 107.80 s,
no rival pytest:

| | secs | share of file | tests | ms/test |
|---|---|---|---|---|
| `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage` | **61.62 s** | **58.3 %** | 23 | **2 679** |
| `TestDoorAxis_TheNextIndirectionIsNotSilentEither` | 13.36 s | 12.6 % | 34 | 393 |
| `TestSourceSegment_TheMemoIsTheStdlibAnswer` (CARD-292's own) | 8.74 s | 8.3 % | 5 | 1 748 |
| the file's other classes | 21.94 s | 20.8 % | 70 | 313 |
| **the file** | **105.66 s** | | **132** | **800** |

**And the residue is far more concentrated than the original problem was** —
one test is half of it:

| test | secs | share of class |
|---|---|---|
| `test_each_door_axis_arm_catches_a_shape_the_other_misses` | **30.25** | **49.1 %** |
| `test_every_door_shape_is_read_or_refused_and_never_silent` | 10.62 | 17.2 % |
| `test_every_planted_position_shape_is_caught_or_refused` | 6.02 | 9.8 % |
| the other **20** tests | 14.73 | 23.9 % |

Top three are **76.1 %** of the class. **Only two tests exceed 10 s and only
three exceed 5 s** — so this is no longer a class-wide cost problem. It is one
test, with two followers.

### What it is NOT, so no successor re-derives it

**It is not rendering.** CARD-218's implementation round instrumented this file
read-only on 2026-10-23: of what was then 344.29 s, **9.25 s is rendering at
all** and **2.52 s is recoverable duplicate** — 0.7 % of the file. Sharing a
render once per module, the mechanism CARD-218 carries, recovers under one
percent here. **Do not open this card by hoisting a fixture.**
*(Superseded denominator — the file is now 105.66 s. The conclusion is
unaffected and in fact strengthened: 9.25 s of rendering is the same absolute
figure against a file a third the size, so rendering is at most ~9 % of it and
still not the subject. Do not re-derive this.)*

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
it is **good** — **770 of 832** calls refusing with nothing exempted (CARD-262
measured 760 of 816; **CARD-295 moved both figures** when it added
`vector_puzzle_pages`). Its cost is the price of its evidence, and nobody has
ever looked at the bill.

### The cheap cause is GONE, and the dangerous one is what is left

This section used to open *"there is no memoisation anywhere in these 4,749
lines"* and offer two candidate causes. **CARD-292 settled both**, and not in
this card's favour.

**Candidate 1 — re-derivation of one identical analysis — is REFUTED for the
test that is half the residue.** CARD-292's review cycle 3 established, through
a wrapper capturing `_page_positions`' own arguments and again statically, that
**all 108 analyses** in `test_each_door_axis_arm_catches_a_shape_the_other_misses`
are over **planted** texts (32 distinct lengths, 389,122–389,385 characters),
that **none** is over the real module, and that **none** has `source is None`.
By construction: every one routes through `_plant`, which returns
`source.replace(DERIVED_POSITION, body) + extra`. So **there is no identical
analysis to cache** — the remedy this card called *"cheap, and it changes no
verdict by construction"* buys nothing on the dear test.

**Candidate 2 — the plants — is therefore the whole card**, and this card's own
words for it stand: *"that is where this card can do damage."* **G-1 is no
longer one guardrail among seven; it is the card's central constraint.**

**What CARD-292 did instead, so this card does not redo it.** It memoised the
line split inside `ast.get_source_segment`, which was re-splitting a prefix of
the source on **every** call — 649 splits per analysis re-scanning 50.5 % of the
module each time. That made each analysis **8.0×** cheaper (unprofiled, three
interleaved readings) without touching how many analyses run. The remaining
61.62 s is 108 genuinely distinct analyses that are each already 8× cheaper.
**A further saving has to come from running fewer or smaller analyses — which
is exactly the change that can weaken the guard.**

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

*This whole subsection is DISCHARGED and kept only as the record of why the card
waited: CARD-276 merged `f794d5a8` on 2026-10-25, and the precondition section
below carries what was measured instead. The figures in it — 327.94 s, ≈ 344 s —
are the pre-CARD-292 ones; a review cycle on this file now costs ≈ 106 s.*

**What CARD-276 is therefore asked to do, and this card records the request so
it is not lost:** take this class's per-test durations before and after its
change (`--durations=0 --durations-min=0` over this file alone is enough; it
needs no full suite and no lock) and write both into its card. If its fix makes
the class slower, that is not a reason to refuse the fix — the guard's
correctness was bought over four gating cycles across two cards — but it must
be a **measured** change, surfaced at its own merge gate rather than found by
the next profile.

### Why the saving still compounds — but it is now a P3 argument

`review.test_scope` is `impact`, so this file is not merely a merge-gate cost,
and that is the only part of the original argument that survives.

Re-derived: the 2026-10-24 measurement put the impact set for CARD-218's
two-test-file diff at **24 files, 448.77 s — 31.47 % of the suite — of which
344.29 s (77 %) was this one file**. With the file now at **105.66 s**, the same
set is ≈ **210.14 s**, which is **16.5 %** of today's 1270.34 s suite, and this
file is **50.3 %** of it rather than 77 %. So a book-adjacent card pays ≈ 106 s
per review cycle here, not ≈ 344 s.

**That is what re-ranks this card from P2 to P3.** The prize is the class's
61.62 s, of which a realistic target is the 30.25 s single test; at three cycles
per card that is worth having, but it no longer dominates any bill. Whether the
derivation *should* pull this file in at all is still **CARD-286's** question,
and the two cards still attack the same bill from opposite ends.

**It is also no longer the suite's ceiling risk.** CARD-292's review recorded
the suite's nearest approach to `hang_guard`'s 120 s per-test alarm as
`tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces`
at **56.92 s** — nearly twice this class's dearest test. This file was the
ceiling argument when its dearest test was 81.03 s; it is not any more.

## Acceptance criteria

- **AC-1** (happy, measure before fixing): *Given* the three tests that are
  **76.1 %** of the class, *when* their cost is attributed by function, *then*
  the card records where the **61.62 s** goes — each as seconds and a share,
  from `cProfile` cumulative time over named call sites, not from a guess. **Two
  answers are already known and must not be re-derived as if open**: candidate
  (a), re-derivation of an identical analysis, is **refuted** for the 30.25 s
  test (all 108 analyses are distinct planted texts — CARD-292 cycle 3), and the
  line-split cost is **already memoised**. So AC-1's real question is narrower:
  **of the 30.25 s, how much is the 108 analyses' irreducible work and how much
  is the planting idiom itself** (`source.replace(...) + extra` over a 389 k
  character string, 108 times). **Report `cProfile` figures with both arms
  profiled** — CARD-292's headline defect was a profiled numerator over an
  unprofiled denominator, so state the instrument beside every ratio. No
  optimisation may be committed before this table is on the card. (recorded,
  verified by review)
- **AC-2** (happy, the saving): *Given* the remedy AC-1's table selects, *then*
  the class's wall-clock falls by a figure the card **states in advance** and
  measures after, over three runs of each arm **interleaved** (not two blocked
  batches), with host cells at the start and end of each: load average **and**
  rival-pytest through `pgrep -f 'MacOS/Python.*pytest' | wc -l` — **not** a
  load average alone, which on this box reads 4–14 with nothing running at all,
  and **not** any other `pgrep` form (see `meta/kanban/config.yml`'s five-case
  truth table; three forms were tried and all three were blind, false-positive
  or both). **If the honest answer is that no remedy survives G-1, that is a
  result and the card may land on it** — this card's prize is 61.62 s, not
  327.94 s, and a refused optimisation recorded with its measurement is worth
  more than a weakened guard. (test: `TestSuiteProfile_*` records the artefact;
  the delta is recorded)
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
  classification, is identical before and after — **re-derived and compared, not
  cited**. ⚠ **The figures this AC used to name are stale**: CARD-262's
  *760 of 816 refusing* became **770 of 832** when CARD-295 added
  `vector_puzzle_pages`, and the cost sequence moved to 770 / 517 / 204 / 202.
  **Read the current figures off the module, not off this card** — that
  substitution is the whole point of the AC, and the card naming a superseded
  pair is itself an instance of the defect it guards against.
  (test: `TestBookPdfStructure_*::test_the_classified_call_sites_are_the_ones_card_262_measured`)
- **AC-7** (happy, collected count): *Given* the file, *then* its collected
  count is unchanged except for controls this card adds, each named on the card,
  and **no test is merged, parametrised away, skipped or deleted** — verified by
  set difference over sorted node ids, not by comparing two totals. (recorded)
- **AC-8** (happy, the suite figure): *Given* the next full-suite profile,
  *then* the card records this file's new seconds and share against the
  **measured** baseline in "What to implement" — **105.66 s, 8.3 % of a
  1270.34 s suite** (and the class at 61.62 s, 4.85 %) — **not** against the
  superseded 344.29 s / 24.14 %, and against the
  `meta/profiling/suite-hotspots-*.md` ranking its own guard regenerates.
  (recorded, not asserted)

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

## [Precondition settled — 2026-10-26, orchestrator] CARD-276 merged, and the measurement you asked for exists in a different form

**Your dependency is discharged: CARD-276 merged `f794d5a8` on 2026-10-25.**

### The contract conflict, recorded because nobody caught it in time

This card asked CARD-276 to *"take this class's per-test durations before and
after its change … and write both into its card"*. **CARD-276's own G-6 read
"Take no timing measurements and report no durations."** The two cards'
contracts contradicted each other outright, and neither station noticed: this
card's request was written at drafting, G-6 was written at drafting, and the
orchestrator flagged G-6's wording tension at CARD-276's **merge gate** without
connecting it to the sibling precondition it blocked. So the per-test form you
asked for was never taken, and could not have been without breaching G-6.

### What was measured anyway, and it answers your actual question

The question behind the request was *"CARD-276's fixed point is more analysis,
not less, and may make 327.94 s materially worse."* **It did not.** From two
independent runs, both already committed to `meta/kanban/suite-timing.log`:

| | file wall clock | tests | s/test |
|---|---|---|---|
| **before** this card's subject changed (main, 2026-10-23 solo profile) | **344.29 s** | 90 | **3.825** |
| **after** CARD-276 (its merge gate's whole-file run, quiet box) | **467.30 s** | 127 | **3.679** |

**Per-test cost FELL by 3.8 %.** The +123 s (+35.7 %) is **tests added, not tests
slowed** — CARD-276 added 37 collected tests to this file. So the fixed point
did not make the walker materially more expensive per assertion, which is the
thing you needed to know before pinning costs.

What is still **not** measured, and is yours if you want it: the **per-test
breakdown** (`--durations=0 --durations-min=0` over this file alone, ~8 min, no
lock needed). The two rows above are file totals. If your cost-pinning tests key
on individual tests rather than the file, take that run first — and take it on a
quiet box, for the reason in the next section.

### Something that got worse while you waited, and it strengthens this card

⚠ **REVERSED 2026-10-27 — this subsection's heading is no longer true, and it is
kept because the reasoning it records is still how the card was scheduled.** It
read: this file is measured at **24.14 % of attributed suite time — 344.29 s of
1426.16 s** on the 2026-10-23 profile, against the **327.94 s** this card was
written with. **CARD-292 then reversed it**: the file is **105.66 s** and the
class **61.62 s**, measured 2026-10-27 at `2fddaccc`. What got worse while this
card waited got better while it kept waiting. The 2026-10-26 join of that profile against ADR-0042's migration
census puts the whole convertible interior-raster surface at **498.02 s =
34.92 %** of attributed time, of which **this one file is two thirds**. Second
place is 21.60 s. So the opportunity this card exists for is more concentrated
than the card claims, not less.

### ⚠ THIS CARD CANNOT RUN CONCURRENTLY WITH ANYTHING

Not "should be serialized" — **cannot**. Its deliverable is a timing
measurement, and `tests/README.md` states the host rule in its own words:
concurrent runs inflate every number, two quiet-host runs of near-identical
suites a few hours apart differ by **~19 %**, and *"a contended run tells you
nothing at all."* Dispatching this card beside a live agent produces exactly the
contaminated figures **CARD-292** exists to expose.

**Run CARD-292 first.** It is P1 to this card's P2, it measures the per-test
ceiling that decides whether any single figure here is trustworthy, and it
touches this same file — so the two serialize on the file as well as on the host.
Also note CARD-292 declares `meta/kanban/config.yml`, which was edited
2026-10-26 (the review refire policy); rebase rather than assume.

## [REWRITTEN — 2026-10-27, orchestrator] CARD-292 took 81 % of this card's opportunity before it ran

The owner chose to rewrite this card against measured figures rather than
dispatch it on its original table. The measurement that forced it, taken at
`2fddaccc` over this file alone (132 passed, 107.80 s, no rival pytest):

| | this card recorded | measured 2026-10-27 | change |
|---|---|---|---|
| the target class | **327.94 s**, 95.3 % of file, 14 258 ms/test | **61.62 s**, 58.3 %, 2 679 ms/test | **−266.32 s, 5.3× cheaper** |
| the file | 344.29 s | **105.66 s** | −238.63 s |
| share of suite | 24.14 % of 1426.16 s | **4.85 %** (class) / 8.3 % (file) of 1270.34 s | |
| impact-set share | 448.77 s, 31.47 %, this file 77 % | ≈ 210.14 s, 16.5 %, this file 50.3 % | |

**CARD-292 did not set out to do this card's work.** It was dispatched to measure
an unmeasured per-test ceiling, found the ceiling was this tree's own
`hang_guard`, and on the way refuted the page-cache story it had been handed and
found the real cost: `ast.get_source_segment` re-splitting a prefix of the source
on **every** call, 649 splits per analysis each re-scanning 50.5 % of the module.
Memoising that made each analysis **8.0×** cheaper. Its merge gate then confirmed
the saving suite-wide — **1670.57 s → 1270.34 s, 400.23 s, 24.0 %** — against a
file-level prediction of 407.31 s, agreeing to **1.7 %**.

**What that leaves, and why the card is re-ranked P2 → P3 and 1d → 0.5d.** The
cheap remedy this card named is **gone twice over**: the line split is memoised,
and caching identical analyses is **refuted** for the dear test, because all 108
of its analyses are distinct planted texts. What remains is 61.62 s, **76.1 % of
it in three tests and 49.1 % in one**, reachable only through the plants — which
this card's own prose calls the place where *"this card can do damage."* So **G-1
is promoted from one guardrail to the card's central constraint**, and AC-2 now
says in terms that **"no remedy survives G-1" is an acceptable result**.

**Two stale figures found while rewriting, both now fixed in place.** AC-6 cited
CARD-262's *760 of 816*, which CARD-295 moved to **770 of 832**; and the
"no memoisation anywhere" fact is no longer true. A card that names a superseded
figure is an instance of the defect AC-6 exists to guard against, which is why
they are corrected here rather than left for the agent to trip over.

**What is NOT changed:** AC-3, AC-4, AC-5 and AC-7 — the verdict-preservation,
cache-staleness, plant-inventory and collected-count guards. Their shape never
depended on the cost figures, and they are the reason this card can be attempted
at all.

## [IMPLEMENTATION — 2026-10-28] `8b908a73` — a remedy survived G-1, and it never approached it

One file, `tests/test_book_export_interior_cover.py` (+141/−2), blob
`a2b950ca`. `src/` and `pyproject.toml` **zero diff** (G-2, verified from git).

**The class is 42.8 % cheaper and the file 29.5 %, with the number of analyses,
their texts, their arms and every one of their verdicts unchanged.** The card's
fear was that the only saving left required guarding less. It did not.

### AC-1 — the attribution table, taken BEFORE any edit, and it answers the narrowed question NO

`cProfile`, **both arms profiled**, every share's numerator and denominator from
the *same* profiled run — CARD-292's headline defect avoided by construction. The
unprofiled wall clock sits beside it and is **never** a denominator for a
profiled numerator.

| test | unprofiled wall | profiled Σtottime | **profiler factor** | stdlib `get_source_segment` cum | share *(of a profiled second)* | **the planting idiom** | share |
|---|---|---|---|---|---|---|---|
| `…each_door_axis_arm…` | 28.81 s | 68.35 s | **×2.37** | **14.366 s** | **21.0 %** | **0.062 s** | **0.09 %** |
| `…every_door_shape…` | 10.23 s | 26.32 s | **×2.57** | 4.804 s | 18.3 % | 0.025 s | 0.09 % |
| `…every_planted_position…` | 5.70 s | 14.59 s | **×2.56** | 2.736 s | 18.8 % | 0.006 s | 0.04 % |

**A PROFILED second is not a wall-clock second, and no share in that table may
be read as one** (review cycle 1, F-05). The factor column is the ratio of the
table's own first two columns — the profiler inflates these tests by
×2.37 / ×2.57 / ×2.56, because it instruments 23.2 M `ast.walk` calls into the
denominator while the split is **one** instrumented call doing heavy
*un*instrumented work inside. So 21.0 % understates the unprofiled share by
about a factor of two: the saving AC-2 actually measured on that test is
**45.5 %** of it, 2.17× the profiled share. The *unprofiled* domain is the one
that carried the prediction, and it is labelled as such wherever it appears.

**The plants are not the bill and never were** — 0.062 s of 68.35 s. `str.replace`
alone is 0.013 s over 216 calls; the disk reads 0.001 s. So the route this card
feared, and G-1 guards, was never the one worth taking. **That conclusion is
robust in either domain**, which is why it is the one AC-1 draws: `str.replace`
over the 389 k string is a single C call that no profiler inflates.

**What the bill actually was.** `print_callers` named the door:
**`_page_positions` itself calls stdlib `ast.get_source_segment` 2 556 times.**
CARD-292 memoised the line split and routed **one of this file's THREE**
analysis call sites through the memo — `_page_positions`' `segment()` closure
at `:1750` — and **the other two kept calling the stdlib**: that method's own
`found.append` tail at `:2927` (the hot one) and `_counting_expressions` at
`:1449` (the cold one). **Three, not two** (F-08), counted rather than read:
a spy wrapped round the module-global `_source_segment` over one analysis
reports `{1750: 718, 2927: 24, 1449: 8}` calls by caller line.

**What each of those calls re-splits is a BOUNDED PREFIX, not the whole
source** (F-287-01, gating). CPython 3.14 passes `maxlines=end_lineno+1` and
`ast._splitlines_no_ff` breaks out of its `finditer` there, so a call re-scans
the source *from its start up to its own node's end line*. **Re-derived at the
fix station**, through the same spy door extended to record every
`(caller line, node.end_lineno)` across all 108 analyses: over all **2 556**
routed splits the prefix is **mean 81.1 %** of the 7 334-line planted module,
**min 43.1 %, max 96.7 %**; over the 24 sites of a single analysis — cycle 1's
own sample — **81.3 / 43.2 / 96.7 %**, which reproduces it. **The cost claim
survives restated:** a prefix averaging four fifths of the module, 2 556 times,
is still the bill — **4.730 ms** per bounded split against **5.999 ms**
unbounded (`perf_counter`, unprofiled, five blocks with the two measured
round-robin, medians). This file already carried the correction **300 lines
above** the place the round re-broke it; the word is now gone from all four
tracked places, and a grep for `whole`/`entire`/`389 k` over the file leaves
exactly one occurrence — the retraction itself.

**2 556 is right; `24 × 108` is not** (F-04). `len(sites)` is **23 for 36** of
the 108 analyses and **24 for 72**, so the honest decomposition is
**23 × 36 + 24 × 72 = 2 556**, and 24 × 108 is **2 592**. The split count now
stands in three domains that agree: cProfile's `ncalls` of `_splitlines_no_ff`,
`sum(len(sites))` over the 108 analyses, and the fix station's spy count at the
hot call site — **2 556** in each.

**So the remedy is a pure substitution** of a function the tree *already*
asserts equal to the stdlib for every node (`TestSourceSegment_TheMemoIsTheStdlibAnswer`,
CARD-292's own control). Both call sites — the hot one and the cold one in
`_counting_expressions` — now route through `_source_segment`.

### AC-2 — predicted in advance from a different instrument, then measured interleaved

**Written to `prediction.txt` before any arm ran**, from `perf_counter` over 50
reps (a different domain from the cProfile that found the hotspot): dear test
**15.04 s**, class **36 ± 4 s**, file **76 ± 6 s**. *That 15.04 s is what the
file says and it is reported here as history: it was built with F-287-01's
whole-source instrument and on the superseded 30.25 s baseline. The honest
comparison is below.*

Three runs of each arm, **interleaved A B A B A B**, host cells at both ends of
every run; **rival-pytest 0 at both ends of all six**, `NONOGRAM_TEST_HANG_SECONDS`
unset throughout, the board's lock never created.

| | A median | B median | delta |
|---|---|---|---|
| the file | **100.19 s** | **70.62 s** | **−29.57 s, −29.5 %** |
| **the target class** | **57.70 s** | **32.98 s** | **−24.72 s, −42.8 %** |
| `…each_door_axis_arm…` | 27.88 s | 15.19 s | −45.5 % |
| `…every_door_shape…` | 10.17 s | 5.91 s | −41.9 % |
| `…every_planted_position…` | 5.76 s | 3.24 s | −43.7 % |
| the class's other 20 tests | 14.08 s | 8.32 s | −40.9 % |
| `TestDoorAxis_TheNextIndirection…` | 13.34 s | 7.70 s | −42.3 % |

**Prediction against measurement — the honest comparison, with both domains
named (F-287-02, gating).** The round's headline, *“15.04 predicted, 15.19
measured — 1.0 %”*, was **two compensating errors**: the predicted saving was
built with F-287-01's over-measuring whole-source instrument, **and** subtracted
from the card's **superseded 30.25 s** baseline (2.37 s high — the host gap this
card itself declares), while the 15.19 s it was set against came from the
round's **own arm A of 27.88 s**. A numerator and a denominator from two
different domains, which is CARD-292's headline defect in a new dress. The
arithmetic, kept visible so a reader can check it:

| instrument + baseline | arithmetic | agreement |
|---|---|---|
| as reported | 30.25 − 15.21 = **15.04** vs 15.19 | 1.0 % — **two errors cancelling** |
| the round's own instrument, the round's **own arm A** | 27.88 − 15.21 = **12.67** vs 15.19 | **16.6 % OUT** |
| **bounded** instrument, the round's **own arm A** | 27.88 − **11.48** = **16.40** vs 15.19 | **8.0 % out** |

The bottom row is the one that stands, and **its saving is re-derived here, not
taken from cycle 1**: 2 556 counted splits × **4.730 ms** bounded − 108 memo
misses × **5.693 ms** = **11.48 s** (`perf_counter`, unprofiled, five blocks
measured round-robin, medians). **A second domain for the same saving**, because
reproducing a figure with its own method only confirms the method: a
`cost(maxlines)` curve timed at 11 points across the real bound range and summed
over **all 2 556 actual bounds** rather than over a mean gives **11.57 s** —
0.8 % away. Cycle 1's own reading of that row was 11.80 s, i.e. 16.08 vs 15.19
= 5.9 %. **So the method lands 6–8 % out, the spread being the host's reading of
the two ms/call figures. Six to eight per cent is what it is worth. It is not
1.0 %, and the 1.0 % was never an agreement.** The same method run with the
whole-source instrument lands **13.3 %** out on this station's readings, which
is the measure of how much the instrument's *domain* mattered — and the lesson
the two gating findings share.

Class and file both landed inside their stated bands, which were quoted as
bands and are unaffected.

**A bound found and CLOSED rather than declared:** the six A/B runs were taken on
arm B's *first* blob, not the committed one. A fourth run on the **committed**
blob at `8b908a73` gives file **70.84 s**, class **32.70 s**, dear test
**15.21 s**, 133 passed — inside **0.3 %** of the B median. *The figures belong
to the commit.*

### G-1 — a byte-for-byte equality, re-run at fix round 1 over **257 sections**

**What the capture covers, in the numbers rather than in a superlative**
(F-287-03, gating — the round called it *“the guard's entire observable
answer”*, and it was not). The round's **1 752-line, 52-section** capture was
taken before and recomputed after, **identical (`cmp -s`)**, once against arm B
v1 and again against the committed blob. **Re-run at the fix station on both
arms after the fix edits: still identical**, sha256 `4acefd4c…`, and
byte-identical to the round's own `before.txt` *and* `after2.txt` once this
station's three loader banner lines are stripped. It holds, unsummarised:

- **Complete, and derived rather than asserted:** `len(DOOR_SHAPES) == 36`, and
  `DOOR_ARMS` has exactly **two** members, so AC-3's **4** arm configurations
  are the **complete powerset** of that axis, not a sample — 144 `(arm-config,
  plant, verdict, refusal-reason)` quadruples. **AC-5's** 36 labels, the 36-row
  shape table and **20 of the class's 33** upper-case attributes, as full
  equalities. Every `(lineno, text)` the `_counting_expressions` site feeds.
- **Narrower than the round said:** *“ten configurations”* is **false as
  written**. The capture makes **12** real-module `_page_positions` calls, of
  which **4** get sites + vocabulary + refusals in full, **2** get refusals
  only, and **6** get a single `len()`. Counted off the capture's own section
  index, not off the script.
- **What it omitted**, each axis named by AC-3/AC-5/AC-6's own words: the **20
  `PLANTED_SHAPES`** position-axis plants' sites / refusals / outcomes — the
  very inventory the third dear test runs; the **per-door leave-one-out**
  configurations, which are a *genuinely different* answer (**24 sites without
  `page_spec`, 23 without `book_page_spec`**, re-derived here); the six
  callee-exemption **refusal sets** (kept as one integer each); `EXEMPTED_TERM`
  under `follow_terms=True`; the position plants' **vocabularies**;
  `_door_position_slots` / `_bare_literals` / `_binder_source`; and the
  remaining **13 of 33** upper-case attributes.

**The gap is CLOSED, not declared.** An **extended capture** — the round's 52
sections plus all seven omitted axes — is **257 sections, 11 936 lines**, i.e.
**10 184 further lines** of observable answer. Run at the fix station against
**both arms** (file swapped to arm A's blob `8741bd33` with `git show`,
restored, `git hash-object`-checked): **byte-identical, sha256 `eb754d30…`**.
And the same sha256 came back from the run taken **before** these prose edits
against the committed blob `a2b950ca`, so the fix round moved nothing either.
`xcapture.py` and both arms' outputs are kept with the round's artefacts.

**Why the equality means anything: the capture is SENSITIVE, established, not
assumed.** One character appended to each non-`None` segment at each changed
call site, then the capture recomputed and compared position by position: the
**hot** site moves **793 of 11 936** lines of the extended capture (6.6 %) and
**75 of 1 752** of the round's (4.3 %); the **cold** site moves **8** lines in
both. Non-zero at **both** sites, so the capture really does read the output of
both changed call sites and **is not self-confirming**. *(Cycle 1 reached the
same conclusion with 1 535 / 8; its injected divergence was evidently a
different one from this station's single appended character, and **I cannot
establish** what exactly it injected. The conclusion is what reproduces, not
the magnitude.)*

**So G-1's conclusion stands on the extended set**, and the claim now states
what the artefact does.

**AC-6 re-derived off the module, not cited:** **832** `ast.Call` nodes, **770**
refusals with nothing exempted, **0** under the shipped default, and the declared
`CALLEE_EXEMPTION_COST` sequence reproduced step for step — **770 / 517 / 204 /
202 / 0 / 0**. The rewritten card's `770 of 832` is **correct as written**.

**AC-4 is NOT ENGAGED, and saying so is the honest answer.** The change adds no
cache; it routes two call sites — the two of this file's three that CARD-292
left on the stdlib — into CARD-292's existing memo, **whose key *is* the
analysed text** (`_SOURCE_LINE_CACHE.get(source)`), **which is why no new
control is owed**: a changed source is a different key, so no stale answer is
reachable, and the equivalence is already pinned by
`TestSourceSegment_TheMemoIsTheStdlibAnswer`. *Saying the memo “carries its own
staleness control” overstated it: there is no control, there is a key that makes
one unnecessary — cycle 1's wording note on AC-4, which it otherwise judged
honest.* AC-4's own precondition — *"if AC-1 selects caching"* — is unmet, so no
cache-key test was written rather than one being invented for a cache that does
not exist.

**AC-7:** set difference over sorted node ids, **132 → 133**, nothing removed,
merged, parametrised away, skipped or deleted. The one addition is named and
costs 0.04 s.

### The mechanisms added, and the ten mutants over them — **with a saved log**

`test_no_analysis_in_this_file_reaches_for_the_stdlib_splitter` makes the saving
**durable** — the stdlib and the memo return the same string, so a regression
would be invisible to every other control in the tree. Default-deny over an
enumerable authority (ADR-0039/R2): a two-sided set equality between the
outermost enclosing scope of every `*.get_source_segment` **call** and
`STDLIB_SEGMENT_SCOPES`, with **both** controls inline — it must rise on a call
planted in a foreign scope and must **not** rise on a mention.

All ten rows below were **re-fired at fix round 1** — the eight original ones
because the derivation changed underneath them (F-07), plus two over the fix
round's own addition — and the run is now **logged**, which F-06 filed as
missing: `mutant-census-fix1.log` carries every mutant, the assertion that
fired *with its own message*, and the restore hash after each
(`4d9a8977…`, checked eleven times, `git status --porcelain` clean apart from
the fix edits themselves).

| mutant | result | which assertion fired, and on what |
|---|---|---|
| **S1** revert the **hot** call site | **killed** | set equality — `[('TestBookPdfStructure_…', 2938)]` |
| **S2** revert the **cold** call site | **killed** | set equality — `[('TestBookPdfStructure_…', 1460)]` |
| **S3** *edge* — a stdlib call in a third scope the comments never name | **killed** | set equality — `[('_attribute_callee_laundering', 5487)]` |
| **S4** *edge, negative* — a bare *mention* in that scope | **survived, correctly** | nothing fired |
| **M1** the `ast.Call` requirement → bare `Attribute` | **survived — declared** | nothing fired |
| **M2** delete the attribute-name filter | **killed** | set equality — 33 scopes named |
| **M3** empty the declared authority | **killed** | set equality — the class's own four calls become offenders |
| **M4** delete the outermost-scope rule | **killed** | set equality — **method** names in place of the class |
| **N1** *fix round 1* — delete the `node.lineno` the derivation now carries | **killed** | the **positive control**, and only it: `[('Foo', 0)] != [('Foo', 4)]` |
| **N2** *fix round 1* — delete the lineno half of the **failure message** | **survived — declared** | nothing fired; see below |

**S1 and S2 now name different lines — 2938 against 1460 — which is F-07
closed:** before the fix they produced the identical message. **N1 proves the
line is load-bearing** and that the positive control is what pins it. **N2 is
an honest declared negative:** a failure *message* is only rendered on failure,
so while this file is green no assertion can observe its text; killing N2 would
need a test that asserts on another test's message, which this tree does not
do. Declared rather than papered over, and the evidence that the message is
right is S1-vs-S2 above.

**Three honest negatives, each recorded in the code rather than papered over:**

1. **M1 survived and the docstring says so**, instead of being given an invented
   mutant. The `ast.Call` requirement is **structural** — it is how `node.func`
   is reached — and is not independently killable on this file, because every
   `*.get_source_segment` attribute here is also called. **The first draft's
   docstring claimed the Call filter was what excluded a mention; that claim was
   false** (the exclusion is the `Attribute` match) and *the mutant census is
   what caught it*. Corrected in the committed text.
2. **An assertion the round wrote first SURVIVED its own deletion mutant**, the
   two-sided equality already failing on both an empty derivation and a dead
   authority row. It was **deleted** rather than kept as a claim with no control,
   and the comment left in its place says why.
3. The first S3 was **malformed** — an `ast` reference in a default-argument
   expression, evaluated at module scope where `ast` is unbound — giving **exit
   4, a collection `NameError`, and no verdict**. Re-run well-formed. *An exit
   code is not a verdict.*

The positive control also earned its keep during development: it caught a real
defect in the round's own derivation (BFS `setdefault` attributes a call to the
**outermost** scope, not the nearest).

**Declared bound on the new guard, in the code:** a stdlib reference bound to a
name and called through it — `f = ast.get_source_segment; f(...)` — is not a
`*.get_source_segment` call node and this derivation does not see it. That is the
alias family the big class spends two thousand lines on, and closing it here is
not this card's (**G-7**).

### Pre-gate — one invocation over a derived radius of ten files

Derived, not guessed: the files that read `tests/` or the tree as data, name the
env switches or `rank_durations`, name this test file, or enumerate node ids —
including `test_browser_fixture_scope.py` explicitly (**G-5**).

**Collected 1051, passed 1051, skipped 0, failed 0, errors 0**, exit 0, 279.74 s.
`-rs` printed **no skip lines at all**, so there is no skip to attribute. Host:
load 6.21 → 4.92, **rival-pytest 0 at both ends**, `$TMPDIR/nonogram-test-hang.txt`
**0 bytes** — no per-test kill, and the dearest test in this file is now 15.21 s
against the 120 s ceiling. The board's lock absent throughout; **the full suite
was not run**. G-4 holds: the frozen render set is unchanged and no tracked file
was added under `meta/profiling/`.

### Measured vs inferred, with the doors named

**Measured:** the 2 556 splits (**three** independent instruments agreeing —
cProfile `ncalls`, `sum(len(sites))`, and the fix round's spy at the hot call
site); the split cost, **with the instrument's own domain stated, because that
is where both gating findings came from** — the round's 6.238 ms per stdlib
split and 6.779 ms per memo miss were taken with `maxlines=None`, i.e. **over
the whole source, which is not the call the code makes** (F-287-01); the
bounded figures the code actually pays are **4.730 ms** per split against
**5.693 ms** per memo miss (`perf_counter`, unprofiled, five round-robin
blocks, medians), and the end-line prefix those bounds correspond to is
**81.1 %** of the module on average. Both readings are unprofiled and
deliberately not the cProfile domain that produced the 14.37 s. Every timing row
(three interleaved runs per arm, plus a fourth on the committed blob, medians
reported and all readings shown); 832 / 770 / 0 and the full cost sequence
(recomputed, then cross-checked against the tree's own declared constants);
AC-3/5/6 (recomputation, twice, as a byte comparison); every mutant row is a run
and every kill names its assertion.

**Inferred and labelled as such — AC-8 is a PROJECTION, not a measurement.** A
full-suite run is forbidden to the implementation station. File **105.66 → 70.62 s**
is measured; projected suite **≈ 1240.8 s**, file share **≈ 5.7 %** (was 8.3 %),
class **≈ 2.66 %** (was 4.85 %). CARD-292's file-level prediction agreed with its
suite gate to 1.7 %, which is the precedent for the method — but **it stays an
inference until the merge gate measures it.**

**A baseline difference declared rather than hidden.** The test file in the
worktree is byte-identical to `2fddaccc`, so the gap is host, not tree: arm A
re-derives **100.19 / 57.70 / 27.88** against the card's **105.66 / 61.62 /
30.25** — 5.2 % / 6.4 % / 7.8 % low, inside the ~19 % `tests/README.md` records
between quiet runs. **Every delta in the A/B table above uses the round's own
arm A as its denominator**, so no percentage *there* is inflated by that gap.
*The round's headline agreement figure did not, and this was the sentence a
reader would have checked it against — true of the table and false of the
figure the card led with, which is the more serious half of F-287-02.* The
corrected headline above is now taken against arm A as well, so the sentence is
true of every figure on the card and not only of the table.

### Could not establish, in those words

- **The suite-wide figure.** AC-8 is a projection; only the merge gate closes it.
- **Whether the remaining 32.70 s is reducible.** The residue is the walker's own
  traversal: 23.1 M `ast.walk` resumptions, 49.7 M `iter_child_nodes`, 63.1 M
  `iter_fields`, 131.8 M `isinstance`, and **19.4 M calls to `_page_positions`'
  inner `called()` for a module with 832 call nodes** — ~180 k per analysis,
  which **looks super-linear and is the next real prize**. Deliberately not
  pursued: it is the walk's algorithm, which is where G-1 bites and which **G-7**
  assigns elsewhere. → **CARD-303**.
- **`_source_lines`' 8-entry cap.** It clears at 8 while the dear test visits 36
  distinct texts, so 108 misses occur where 36 would do; raising it saves a
  further ≈ 0.45 s. Not pursued — it changes CARD-292's declared mechanism and
  the control pinning it, for under 1 % of the class.
- ~~**Call-site granularity of the new guard.**~~ **CLOSED at fix round 1**
  (F-07), and moved out of this list. The *authority* stays a **set of scopes**
  — cycle 1 agreed, and a per-call multiset would pin this class's own four
  legitimate stdlib calls and red on unrelated edits to them. But *“which path
  regressed”* was never a property of the authority; it is a property of the
  **message**. `_stdlib_segment_scopes` already visits every node, so it now
  returns `(scope, lineno)` pairs, the message prints the offending ones, and
  the comparison is **still** `set(scopes) == set(STDLIB_SEGMENT_SCOPES)`. It
  **reds on nothing**: the old scope-only derivation and the new pair
  derivation return the *same* scope list on both the committed blob and the
  patched file, verified side by side. S1 and S2 are now distinguishable
  failures (lines 2938 and 1460), and N1 is the mutant that proves the line is
  carried rather than claimed.

**Artefacts kept outside the worktree**, at
`~/Documents/nonogram-reviews/CARD-287/`: three cProfile outputs, the callers
dump, `prediction.txt` (written before the arms ran), all seven timing runs with
host cells, the 150 kB pre-gate log, the before/after captures, both node-id
lists, and every probe script. **Added at fix round 1:**
`mutant-census-fix1.log` (F-06 — ten mutants, the assertion that fired, the
restore hash after each); `xcapture.py` + `wload.py` and
`extended-capture_armA.txt` / `extended-capture_armBfix.txt` (the 257-section,
11 936-line extended capture under both arms);
`fix1-capture-equality.log`; `fix1-sensitivity.txt`; and the four re-derivation
logs `fix1-f01-reach.txt`, `fix1-f01-cost.txt`, `fix1-f02-prediction.txt`,
`fix1-f07-equivalence.txt`. **Recommendation, stated explicitly: the extended
capture SHOULD become part of this card's durable artefacts.** It is not in
`tests/`, so it costs the suite nothing and no guard enumerates it; it is the
only artefact that holds G-1's central evidence over **every axis AC-3, AC-5
and AC-6 name in their own words** — not over “the whole observable answer”,
which is the claim this round is correcting and which nothing can check —
rather than over a seventh of the lines; and a successor who widens the walk
will want the arm-A side of it to compare against. None tracked; none under
`tests/` or `meta/profiling/`.

## [CYCLE 1 — 2026-10-28] **7.5, NOT CERTIFIED**, 3 gating — and all three are claims, not code

`meta/review/20261028T032212Z-CARD-287-cycle1.yml`, reviewed `8b908a73`.
**The code change is correct, the saving is real and the reviewer reproduced it
in its own domain, and G-1 HOLDS — on stronger evidence than the round
produced.** No code change is owed. The distance is three prose/artefact fixes
and one recomputed sentence.

The reviewer's own figures, interleaved A B A B with class-isolation node-id runs
(a different selection domain from the round's whole-file runs): class **58.50 →
32.82 s, −43.9 %**; dear test **27.98 → 15.13 s, −45.9 %**. Rival-pytest **0 at
both ends of all four runs**, ceiling env unset, hang dump 0 bytes, board lock
absent. **Slightly better than the round claimed.**

### F-287-01 (gating) — the round reinstated a claim its own file retracts 300 lines above

The committed code says `ast.get_source_segment` *"re-splits the **whole**
source per segment"* in tracked places — **`:1441`, `:6653`, `:6748`** (the main
assertion's own failure message) — plus the card and the commit message.
**That is the claim CARD-292 measured as FALSE**, and this same file corrects it
at **`:1105-1112`**: *"it is **not** a whole-source split per call, which is what
the first draft of this comment said"* (stdlib passes
`maxlines=end_lineno+1`). Re-measured by the reviewer over the **24 sites this
change actually routes**: mean **81.3 %** of the module, min 43.2 %, max 96.7 %,
and a real per-call cost of **4.903 ms** against the **6.238 ms** whole-source
figure the round's prediction instrument used. Verified independently by the
orchestrator. **This is G-1's own family signature — a claim to a reach that was
not measured — in tracked code, 300 lines from its own retraction.**

### F-287-02 (gating) — the headline agreement is TWO COMPENSATING ERRORS

AC-2 leads with *"15.04 predicted, 15.19 measured — **1.0 %**"*. It is not an
agreement. The predicted saving (15.21 s) was built with F-287-01's
**over-measuring** instrument **and** subtracted from the card's **superseded
30.25 s** baseline, while the 15.19 s came from the round's own arm A of
**27.88 s**. Re-derived:

| | | |
|---|---|---|
| as reported | 30.25 − 15.21 = 15.04 vs 15.19 | **1.0 %** |
| on the round's **own arm A** | 27.88 − 15.21 = 12.67 vs 15.19 | **16.6 % OUT** |
| bounded instrument + own arm A | 27.88 − 11.80 = 16.08 vs 15.19 | **5.9 %** |

**The method survives; the number does not.** And the card's sentence *"every
delta above uses the round's own arm A as its denominator"* is **true of the A/B
table and false of the figure the card leads with** — which is the more serious
half, because it is the sentence a reader would check the claim against.

### F-287-03 (gating) — the capture is not "the guard's entire observable answer"

The reviewer did **not** just re-run `capture.py`. It reproduced the capture with
its **own** loader (byte-identical, 1 752 lines / 52 sections), then
**established its sensitivity** by injecting a one-character divergence into each
changed call site: the hot site moves **1 535** of 1 752 lines, the cold site
**8**. So the capture reads both changed sites and is **not self-confirming** —
the strongest thing that could have been said for it, and it is now established
rather than assumed.

**What is complete:** `len(DOOR_SHAPES) == 36`, and `DOOR_ARMS` has exactly two
members, so the 4 arm configurations are the **complete powerset**, not a sample.

**What is not:** *"ten configurations"* is **false as written** — the capture
makes 12 real-module `_page_positions` calls, of which **4** get
sites+vocabulary+refusals in full, **2** get refusals only, and **6** get a
single `len()`. Omitted axes that AC-3 and AC-6 name **in their own words**: the
**20 `PLANTED_SHAPES`** position-axis plants' sites/refusals/outcomes (the very
inventory the third dear test runs); the **per-door leave-one-out**
configurations, which are a genuinely different answer (**24 vs 23 sites**); the
six callee-exemption **refusal sets** (captured as one integer each);
`EXEMPTED_TERM` under `follow_terms=True`; the position plants' vocabularies;
`_door_position_slots` / `_bare_literals` / `_binder_source`; and **13 of the
class's 33** uppercase attributes.

**And the reviewer closed the gap rather than filing it**: **10 242 further lines**
of observable answer recomputed under **both** arms (file swapped, restored,
hash-checked) — **byte-identical**. *So the equality's conclusion stands and G-1
holds; what fails is the claim.* The bound was closeable in under a minute, which
is precisely when this board's rule says close it rather than declare it sound.

### Five minors

**F-04:** `24 × 108 = 2 556` is wrong twice over — `len(sites)` is **23** for 36
of the 108 and 24 for 72, and 24 × 108 = **2 592**. The headline 2 556 is right
(confirmed in the reviewer's own counting domain); the gloss is not.
**F-05:** the profiled-vs-unprofiled factor of ~2.4 goes unremarked.
**F-06:** no saved mutant-census log.
**F-07:** the closeable half of the granularity bound (below).
**F-08:** *"two analysis call sites"* — there are **three**.

### What the review verified rather than took

- **M1's declared survival is TRUE, not merely humble**, and verified a *second
  way* rather than by re-running it: by AST, the Attribute-based derivation
  returns a list **identical** to the Call-based one over this file, and the set
  of `*.get_source_segment` Attribute nodes that are **not** a Call's `func` is
  **empty**. The **corrected** docstring is also true.
- **S4 is a real plant, not a phantom** — anchor occurs once, lands in
  `_attribute_callee_laundering` (module scope, 5457–5494), a genuine third
  scope — and survives correctly.
- **The declared alias bound is true** (`f = ast.get_source_segment; f(...)` →
  `[]`) and is stated **in the code**.
- **The deleted assertion is gone** with its comment, and **nothing else in the
  test shares its property**: the reviewer built two new mutants — a
  self-confirming derivation (killed by the **positive** control only) and a
  mention-matching derivation (killed by the **negative** control only) — so both
  remaining controls are load-bearing.
- **AC-4 "not engaged" is HONEST**, and the inherited staleness obligation is
  discharged **by construction**, verified: the memo's key **is** the analysed
  source text (`_SOURCE_LINE_CACHE.get(source)`), so a changed source is a
  different key and no stale answer is reachable. The card should say *"keyed on
  the analysed text, which is why no new control is owed"* rather than *"carries
  its own staleness control"* — but the verdict is right.
- **AC-6** 832 / 770 / 0 and 770 / 517 / 204 / 202 / 0 / 0 — **all re-derived off
  the module**, correct, not stale. **AC-7** 132 → 133 re-derived by
  collect-only + `comm`. **Baseline byte-identity** verified at three revisions,
  so the 5–8 % gap really is host, not tree.
- **G-1 through G-7 all HELD**, G-2/G-4 mechanically from git, **G-5 run
  explicitly** (619 passed, 0 skipped, exit 0), and **G-7** confirmed: CARD-303
  exists on main and the card points at it by name.

### The granularity trade — sound as to the authority, half-closeable as to the diagnostic

Keeping the authority a **scope set** is correct: a per-call multiset would pin
the four legitimate stdlib calls in the control class and red on unrelated edits
there. But *"the guard says that a path regressed, not which"* is a property of
the **message**, not the authority — `_stdlib_segment_scopes` already visits each
node, so returning `(scope, lineno)` for the message while still comparing
`set(scopes)` distinguishes S1 from S2 and reds on nothing.

### Could not establish, in those words

**When** `prediction.txt` was written (its content matches the card exactly); the
suite-wide figure (AC-8, the merge gate's); whether the three per-test cProfile
readings reproduce (not retaken — not load-bearing for the remedy); whether the
residual 32.7 s is reducible (**CARD-303's**).

### Procedure

Full suite **not** run; `meta/kanban/.full-suite.lock` never taken and absent;
every measurement under `-o addopts=''` with skips attributed by `-rs`; worktree
restored and hash-checked to `a2b950ca` with `git status --porcelain` empty.

## [FIX ROUND 1 — 2026-10-28] `eb2bbf81` — three claims corrected, one bound closed, nothing re-engineered

Against `meta/review/20261028T032212Z-CARD-287-cycle1.yml` (7.5, 3 gating).
**Cycle 1 said no code change was owed and it was right: nothing in this round
changes behaviour.** One file, `tests/test_book_export_interior_cover.py`,
+95/−41, blob `4d9a8977`. `src/` and `pyproject.toml` untouched.

**What changed, and in which register.** Prose and figures in four tracked
places (F-287-01), the card's headline and glosses (F-287-02, F-04, F-05, F-08
and cycle 1's AC-4 wording note), a saved census log (F-06), and **one
functional edit** — F-07's, which changes a failure **message** and not what
the assertion pins.

| finding | closed by | the door the figure came through |
|---|---|---|
| **F-287-01** | the word *whole* replaced by the measured bound in all four tracked places; grep leaves one occurrence, the retraction | a recorder wrapped round module-global `_source_segment` logging `(caller line, node.end_lineno)` over all 108 analyses; `perf_counter`, unprofiled, five round-robin blocks, medians |
| **F-287-02** | the headline replaced by the three-row comparison, arithmetic visible; the *“own arm A as denominator”* sentence corrected | the bounded saving **re-derived**, 11.48 s, and cross-checked in a second domain (a `cost(maxlines)` curve summed over all 2 556 actual bounds) at 11.57 s |
| **F-287-03** | the claim restated in counts; the gap **closed** by a 257-section, 11 936-line extended capture run on both arms | file swapped to arm A blob `8741bd33` with `git show`, restored under `git hash-object`; **byte-identical**, sha256 `eb754d30` |
| **F-04** | the gloss replaced by `23 × 36 + 24 × 72 = 2 556` | the same spy, counting `len(sites)` per analysis |
| **F-05** | a profiler-factor column and a paragraph saying a profiled second is not a wall-clock one | arithmetic over AC-1's own two measured columns |
| **F-06** | `mutant-census-fix1.log` — ten mutants, the assertion that fired, the restore hash after each | eleven `git hash-object` checks against `4d9a8977` |
| **F-07** | **CLOSED** — `(scope, lineno)` pairs for the message, `set(scopes)` still the authority | the old and new derivations compared side by side on two blobs: same scope list |
| **F-08** | **three** analysis call sites, not two, everywhere | the spy's by-caller-line census, `{1750: 718, 2927: 24, 1449: 8}` |

**Nothing changed behaviour, and here is the check that proves it.** The
scope-only derivation and the pair derivation return the **identical** scope
list on both the committed blob `a2b950ca` and the fixed one, and the authority
comparison `set(scopes) == set(STDLIB_SEGMENT_SCOPES)` is `True` under both on
both. The guard class's six tests pass. And the **capture equality was re-run
after the edits**: the round's own 52-section capture is identical across arms
(sha256 `4acefd4c`) and byte-identical to the round's `before.txt` and
`after2.txt`; the extended capture is identical across arms (sha256
`eb754d30`) and identical to the pre-edit run against `a2b950ca`. **G-1 held
through the fix round.**

### Pre-gate, fix round 1 — one invocation over the same derived radius of ten files

`pytest -o addopts='' -q -rs` over the ten files, with
`tests/test_browser_fixture_scope.py` **explicit** (G-5), subject blob
`4d9a8977` — which is exactly what `eb2bbf81` contains.

- **collect-only: 1 051 collected**, exit 0.
- **run: 1 051 passed, 0 skipped, 0 failed, 0 errors**, exit 0, **294.18 s**.
- `-rs` printed **no skip lines at all** — zero `SKIPPED` lines and no short
  test summary section, so **there is no skip to attribute**.
- Host cells: **rival-pytest 0 at both ends** (`pgrep -f 'MacOS/Python.*pytest'
  | wc -l`), load **7.16 → 5.52**, `$TMPDIR/nonogram-test-hang.txt` **0 bytes**
  (no per-test kill), `NONOGRAM_TEST_HANG_SECONDS` **left unset in every run of
  this round, everywhere** — including the mutant census and all six capture
  runs. `meta/kanban/.full-suite.lock` **absent throughout and never taken**.
  **The full suite was not run.**
- The log's `HEAD:` cell reads `8b908a73` because the script started before the
  commit landed; the subject it ran is the blob, and the blob is `eb2bbf81`'s.
  Saved as `pregate-fix1.txt`.

### Could not establish, in those words, at fix round 1

- **What divergence cycle 1 injected** for its sensitivity figures (1 535 / 8).
  This station's own probe — one character appended per non-`None` segment —
  gives 793 / 11 936 and 8, and 75 / 1 752 and 8 on the round's capture. The
  *conclusion* reproduces in both domains; the magnitude does not, and I cannot
  establish why without the cycle's own script.
- **The suite-wide figure.** AC-8 stays a labelled projection; the merge gate
  owes it. The full suite was not run here and the lock was not taken.
- **Whether N2 is killable.** Deleting the lineno half of the *failure message*
  survives, and no assertion in this tree can observe another test's message
  while that test is green. Declared, with S1-vs-S2 as the evidence the message
  is right.
- **When `prediction.txt` was written** — unchanged from cycle 1's finding; no
  artefact readable here carries that ordering.
