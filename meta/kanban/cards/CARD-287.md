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
