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

| test | unprofiled wall | profiled Σtottime | stdlib `get_source_segment` cum | share | **the planting idiom** | share |
|---|---|---|---|---|---|---|
| `…each_door_axis_arm…` | 28.81 s | 68.35 s | **14.366 s** | **21.0 %** | **0.062 s** | **0.09 %** |
| `…every_door_shape…` | 10.23 s | 26.32 s | 4.804 s | 18.3 % | 0.025 s | 0.09 % |
| `…every_planted_position…` | 5.70 s | 14.59 s | 2.736 s | 18.8 % | 0.006 s | 0.04 % |

**The plants are not the bill and never were** — 0.062 s of 68.35 s. `str.replace`
alone is 0.013 s over 216 calls; the disk reads 0.001 s. So the route this card
feared, and G-1 guards, was never the one worth taking.

**What the bill actually was.** `print_callers` named the door:
**`_page_positions` itself calls stdlib `ast.get_source_segment` 2 556 times.**
CARD-292 memoised the line split and routed **one** of this file's two analysis
call sites through the memo — `_page_positions`' `segment()` closure — and **the
other, the `found.append` at the function's tail, kept calling the stdlib**,
which re-splits the whole 389 k source **once per segment**. 24 segments ×
108 analyses = **2 556 splits, each re-scanning the entire module**. The split
count was taken two ways that agree: cProfile's `ncalls` of `_splitlines_no_ff`,
and `sum(len(sites))` over the 108 analyses — different domains, same number.

**So the remedy is a pure substitution** of a function the tree *already*
asserts equal to the stdlib for every node (`TestSourceSegment_TheMemoIsTheStdlibAnswer`,
CARD-292's own control). Both call sites — the hot one and the cold one in
`_counting_expressions` — now route through `_source_segment`.

### AC-2 — predicted in advance from a different instrument, then measured interleaved

**Written to `prediction.txt` before any arm ran**, from `perf_counter` over 50
reps (a different domain from the cProfile that found the hotspot): dear test
**15.04 s**, class **36 ± 4 s**, file **76 ± 6 s**.

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

**Prediction against measurement: dear test 15.04 predicted, 15.19 measured —
1.0 %.** Class and file both inside their stated bands.

**A bound found and CLOSED rather than declared:** the six A/B runs were taken on
arm B's *first* blob, not the committed one. A fourth run on the **committed**
blob at `8b908a73` gives file **70.84 s**, class **32.70 s**, dear test
**15.21 s**, 133 passed — inside **0.3 %** of the B median. *The figures belong
to the commit.*

### G-1 — verified as a byte-for-byte equality, twice

A **1 752-line, 52-section canonical capture** of the guard's entire observable
answer, taken before and recomputed after: **identical (`cmp -s`)**, once against
arm B v1 and again against the committed blob. It holds, unsummarised: **AC-3's
144 `(arm-config, plant, verdict, refusal-reason)` quadruples** (36 door shapes ×
4 arm configurations) plus the position-axis plants and every `(lineno, text)` the
`_counting_expressions` site feeds; **AC-5's** 36 labels and every upper-case
table on the class; **AC-6's** `sites`/`vocabulary`/`refusals` in full under **ten**
configurations.

**AC-6 re-derived off the module, not cited:** **832** `ast.Call` nodes, **770**
refusals with nothing exempted, **0** under the shipped default, and the declared
`CALLEE_EXEMPTION_COST` sequence reproduced step for step — **770 / 517 / 204 /
202 / 0 / 0**. The rewritten card's `770 of 832` is **correct as written**.

**AC-4 is NOT ENGAGED, and saying so is the honest answer.** The change adds no
cache; it routes two call sites into CARD-292's existing memo, already keyed on
the analysed text and already carrying its own staleness control. AC-4's own
precondition — *"if AC-1 selects caching"* — is unmet, so no cache-key test was
written rather than one being invented for a cache that does not exist.

**AC-7:** set difference over sorted node ids, **132 → 133**, nothing removed,
merged, parametrised away, skipped or deleted. The one addition is named and
costs 0.04 s.

### The one mechanism added, and the eight mutants over it

`test_no_analysis_in_this_file_reaches_for_the_stdlib_splitter` makes the saving
**durable** — the stdlib and the memo return the same string, so a regression
would be invisible to every other control in the tree. Default-deny over an
enumerable authority (ADR-0039/R2): a two-sided set equality between the
outermost enclosing scope of every `*.get_source_segment` **call** and
`STDLIB_SEGMENT_SCOPES`, with **both** controls inline — it must rise on a call
planted in a foreign scope and must **not** rise on a mention.

| mutant | result |
|---|---|
| **S1** revert the **hot** call site | **killed** |
| **S2** revert the cold call site | **killed** |
| **S3** *edge* — a stdlib call in a third scope the comments never name | **killed** |
| **S4** *edge, negative* — a bare *mention* in that scope | **survived, correctly** |
| **M1** the `ast.Call` requirement → bare `Attribute` | **survived — declared** |
| **M2** delete the attribute-name filter | **killed** (33 scopes named) |
| **M3** empty the declared authority | **killed** |
| **M4** delete the outermost-scope rule | **killed** |

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

**Measured:** the 2 556 splits (two independent instruments agreeing); 6.238 ms
per stdlib split vs 6.779 ms per memo miss (`perf_counter`, unprofiled —
deliberately not the cProfile domain that produced the 14.37 s); every timing row
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
between quiet runs. **Every delta above uses the round's own arm A as its
denominator**, so no percentage is inflated by that gap.

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
- **Call-site granularity of the new guard.** S1 and S2 fire the same assertion,
  because the authority is spelled as a scope and both sites live in one class.
  The guard says *that* an analysis path regressed, not *which*. Tightening it to
  a per-call multiset would pin the four legitimate stdlib calls in the control
  class and red on unrelated edits there; judged a worse trade and declared.

**Artefacts kept outside the worktree**, at
`~/Documents/nonogram-reviews/CARD-287/`: three cProfile outputs, the callers
dump, `prediction.txt` (written before the arms ran), all seven timing runs with
host cells, the 150 kB pre-gate log, the before/after captures, both node-id
lists, and every probe script. None tracked; none under `tests/` or
`meta/profiling/`.
