# CARD-287: One class is a quarter of the suite and two thirds of its growth — and it is not rendering anything

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/287-the-door-axis-guard-costs-a-quarter-of-the-suite
**Worktree:** — (removed at merge)
**Source:** the 2026-10-23 solo duration profile (`meta/profiling/suite-durations-20261023.txt`, commit `ae164099`), read against the 2026-10-15 one; CARD-218's implementation round, which measured this file read-only and reported that its own mechanism would not touch it; the orchestrator's 2026-10-24 breakdown, recorded below
**Idea:** —
**Wave:** 62
**Created wave:** 56
**Deferred waves:** 0
**Depends on:** CARD-276 <!-- NOT scheduling. CARD-276 rewrites the walker that costs the time (alias resolution as a fixed point), so optimising it first would both waste the work and FREEZE its current shape in cost-pinning tests. See "Why this waits on CARD-276", and the measurement CARD-276 is asked to take. -->
**Touches:** tests/test_book_export_interior_cover.py
**Review score:** 7.5 → 8.0 → **8.5 cycle 3/3 CERTIFIED**, zero gating
**Started:** —
**Closed:** 2026-10-28
**Actual:** —
**Merge commit:** `90c01386`
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
  optimisation may be committed before this table is on the card.
  (**recorded** — the table in the implementation section; no test asserts it.
  Re-derived by review cycles 1 and 2, and at fix round 2 from **one cProfile
  object per test** after cycle 2's F-C2-01.)
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
  more than a weakened guard. (**recorded** — the interleaved A/B table
  below; **no test asserts the delta**. `TestSuiteProfile_*` is real — three
  classes in `tests/test_suite_profile.py` — but it guards the *profiling
  artefact's* shape, which is **G-4's** gate and not this AC's: cycle 2's
  F-C2-07 as a class, audited over every test ref on this card.)
- **AC-3** (guard, the verdict set is unchanged — the one that matters):
  *Given* the class before and after, *when* each of its planted shapes is run,
  *then* **every plant's outcome is identical**, asserted as an equality over
  the full set of (plant, verdict, refusal-reason) triples captured before the
  change and compared after — not as "the tests still pass".
  (**recorded, not asserted by a named test** — a before/after **byte
  equality** over the capture artefacts `before.txt` / `after2.txt` and the
  257-section extended pair, which is the right instrument for a one-off
  *"unchanged by this change"* property and is a reviewer-run capture rather
  than a standing test. The test this AC used to name **never existed**
  (cycle 2, F-C2-07). What stands in CI over the same plants:
  `TestBookPdfStructure_*::test_every_door_shape_is_read_or_refused_and_never_silent`,
  `::test_every_planted_position_shape_is_caught_or_refused`,
  `::test_no_planted_shape_is_declared_silent`.)
- **AC-4** (guard, the cache cannot go stale): *Given* a memoised analysis (if
  AC-1 selects caching), *when* the analysed source changes, *then* the cached
  answer is not reused — proved by a control that **plants a change and fails
  if the stale answer is returned**. A cache keyed on anything other than the
  analysed text is a wrong answer waiting for a plant. (**NOT ENGAGED** — the
  precondition *"if AC-1 selects caching"* is unmet, and the test this AC used
  to name **never existed** (cycle 2, F-C2-07). What does stand, over
  CARD-292's existing memo:
  `TestSourceSegment_TheMemoIsTheStdlibAnswer::test_the_split_is_computed_once_per_distinct_text`
  (one split per **distinct text**, which is the key property) and
  `::test_a_seeded_corpus_of_the_real_module_segments_identically` (the
  stdlib equivalence).)
- **AC-5** (edge, no plant was dropped): *Given* the planted-shape inventory,
  *then* its **count and its node ids are asserted as an equality** against the
  pre-change set, so a saving cannot come from planting fewer shapes. A floor is
  not enough; it must be an equality in both directions. (**recorded** — the
  capture's full inventory equality; the test this AC used to name **never
  existed** (cycle 2, F-C2-07). The standing equality over the same inventory
  is `TestBookPdfStructure_*::test_every_door_shape_is_read_or_refused_and_never_silent`,
  which asserts the refusing labels **tuple** against `DOOR_SHAPE_LABELS` and
  `len(refusing) == len(DOOR_SHAPES)` — attributed by resolving the enclosing
  test of each assertion, not by the file it sits in.)
- **AC-6** (guard, the walker's reach): *Given* the production module the
  walker reads, *then* the set of call sites it classifies, and each one's
  classification, is identical before and after — **re-derived and compared, not
  cited**. ⚠ **The figures this AC used to name are stale**: CARD-262's
  *760 of 816 refusing* became **770 of 832** when CARD-295 added
  `vector_puzzle_pages`, and the cost sequence moved to 770 / 517 / 204 / 202.
  **Read the current figures off the module, not off this card** — that
  substitution is the whole point of the AC, and the card naming a superseded
  pair is itself an instance of the defect it guards against.
  (**recorded** — AC-6's re-derivation in the implementation section plus the
  capture; the test this AC used to name **never existed** (cycle 2, F-C2-07).
  The standing equality is
  `TestBookPdfStructure_*::test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`,
  which re-measures the cumulative sequence against `CALLEE_EXEMPTION_COST`.)
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
  optimisations**, and AC-3/AC-5/AC-6's three equalities **were taken as a
  before/after capture** to make each of them red. *Past tense deliberately
  (cycle 2, F-C2-07): those three equalities are a reviewer-run capture over
  kept artefacts, not standing tests. The standing tests that hold the same
  axes in CI are named beside each AC above.* If the only available saving requires weakening the guard, the
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

`cProfile`, **both arms profiled**. **Every cell below comes from ONE cProfile
object per test** — and that is now true of the headline cell, which it was
not: the `14.366 / 68.35 = 21.0 %` this table used to lead with took its
numerator from a `print_callers` dump and its denominator from a **different
run**, while the card claimed the opposite *"by construction"* (cycle 2,
F-C2-01, **major**). *The arithmetic that proves it needs no re-measurement:
within one run `get_source_segment`'s cumtime cannot be LESS than that of
`ast._splitlines_no_ff`, its only callee — yet 14.366 is less than
`ac1_A.txt`'s 14.490.* Re-derived at fix round 2 on arm A's blob `8741bd33`,
one `cProfile` object per test, numerator and denominator off that one object,
with the caller ≥ callee inequality **asserted inside the probe** (it holds in
all three runs):

| test | unprofiled wall | profiled Σtottime | **profiler factor** | **the stdlib split: `get_source_segment` cum** *(its callee `_splitlines_no_ff` cum)* | share *(of that same profiled Σ)* | **the planting idiom** | share |
|---|---|---|---|---|---|---|---|
| `…each_door_axis_arm…` | 28.47 s | 68.39 s | **×2.402** | **14.523 s** *(14.511 s)* | **21.2 %** *(one run; band **21.2–22.0 %**, mean 21.59 — see below)* | **0.065 s** | **0.09 %** |
| `…every_door_shape…` | 10.25 s | 26.35 s | **×2.570** | 4.800 s *(4.796 s)* | 18.2 % | 0.025 s | 0.09 % |
| `…every_planted_position…` | 5.76 s | 14.71 s | **×2.556** | 2.779 s *(2.776 s)* | 18.9 % | 0.006 s † | 0.04 % |

**The column header was also wrong and is relabelled** (cycle 2, F-C2-01):
rows 2–3 were read off `_splitlines_no_ff`, not off `get_source_segment`, so no
row said what the header claimed. Within one run the two are **the same number
to 0.01 s**, as they must be — one is the other's only caller — and both now
stand in the cell, which is what makes the relabel checkable rather than a
promise. *† the third test never calls `_plant`; its planting cell is
`Path.read_text` + `str.replace` (0.006 s on the round's run; `str.replace`
alone is 0.002 s on this one), and `_plant` is simply absent from that
profile.*

**The headline share is a BAND, not a point — cycle 3's F-C3-01.** Five
same-run readings across three stations span **21.2–22.0 %**, mean **21.59 %**:
the numerator is stable (14.175–14.523 s, 2.5 %) and **the denominator is not**
(64.835–68.39 s, **5.5 %**), so the share has genuine run-to-run spread and no
reading on this host is privileged. **The cell should be read as ~21.5 %
(21.2–22.0 % on this host).** Two stations each anchored on their own single
run: cycle 2 called the card's cross-run figure **1.0 pp** out and fix round 2
called it **0.2 pp** out, and *both distances are to that station's own
reading* — against the mean it is **0.57 pp**. Fix round 2's *"could not
establish cycle 2's 22.0 %"* is also too strong: cycle 3's third rep reads
**21.86 %**, so 22.0 is reachable. So the cross-run error was real but its
magnitude is **0.2–1.0 pp depending on the run**. *On a card whose subject is
instruments, three stations each quoting a point for a quantity with 5.5 %
spread in its denominator is the finding, not any one of the points.*

The original reading, for the record: **21.2 %** on this host at
fix round 2 — 14.523 / 68.39, one object — against the card's cross-run
**21.0 %** and cycle 2's own same-run **22.0 %** (14.383 / 65.32). *The three
disagree in the DENOMINATOR and not in the numerator: the stdlib split reads
14.37 / 14.38 / 14.52 s across the three runs while the profiled total reads
68.35 / 65.32 / 68.39. Which is the card's own lesson arriving on the card's own
first figure — a profiled total is a property of the run, so a share assembled
from two runs is not a share.* **The scope, stated precisely so it is not
overstated**: CARD-292's headline defect — a profiled numerator over an
**unprofiled** denominator — really **was** avoided here, which is what AC-1
demanded; what this one cell had was the smaller **cross-run** variant, and it
moves the figure by **0.2 percentage points** against this station's
re-derivation. The conclusion the table draws is untouched in every reading.

**A PROFILED second is not a wall-clock second, and no share in that table may
be read as one** (review cycle 1, F-05). The factor column is the ratio of the
table's own first two columns — the profiler inflates these tests by
**×2.40 / ×2.57 / ×2.56** on this station's own three runs (×2.37 / ×2.57 /
×2.56 on the round's), because it instruments 23.2 M `ast.walk` calls into the
denominator while the split is **one** instrumented call doing heavy
*un*instrumented work inside. So ~21 % understates the unprofiled share by
about a factor of two: the saving AC-2 actually measured on that test is
**45.5 %** of it, **2.15×** the re-derived profiled share (45.5 / 21.2) and
2.17× the cross-run one. The *unprofiled* domain is the one
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
at **`:1761`** — and **the other two kept calling the stdlib**: that method's
own `found.append` tail at **`:2938`** (the hot one) and
`_counting_expressions` at **`:1460`** (the cold one). **Three, not two**
(F-08), counted rather than read: a spy wrapped round the module-global
`_source_segment` reports **`{1761: 718, 2938: 24, 1460: 8}`** calls by caller
line. *Line numbers re-keyed at fix round 2 (cycle 2, F-C2-03): the
`:1750/:2927/:1449` this paragraph used to carry were the **superseded blob
`a2b950ca`'s**, and contradicted the mutant table's own 2938/1460 two screens
below. Re-derived through two doors on the committed blob — a static `ast`
pass (`_source_segment` call sites `[1460, 1761, 2938, 6501, 6546, 6590,
6627]`) and the spy — and unchanged by this round's own edit, which is 6 800
lines further down; S1 and S2 still red naming 2938 and 1460.* **And the 718
has a domain, which was missing:** it is **one PLANTED analysis** — the
7 334-line planted text the dear test runs, `DOOR_SHAPES[0]` — measured
through one spy over both texts in one process; the **real module's** analysis
makes **716** calls at that same site, with 24 and 8 unchanged. The figure the
rest of this card multiplies is the planted one, which is the right one, and
it now says so.

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
above** the place the round re-broke it, and the word is now gone from all four
tracked places. **The grep that actually reproduces** (cycle 2, F-C2-02 — the
one this paragraph used to offer does not, and the audit is the class rather
than the instance): `grep -c "whole source"` → **1**, line 1444, the retraction
itself. `grep -c whole` → **29**, of which **five** are in a source-splitting
context — 1106 and 6665 and 6735 **negate** the mechanism (*"it is **not** a
whole-source split"*, *"not the whole text"*), 1444 **retracts** it, and 1116 is
CARD-292's legitimate comparative (*"at half the constant a whole-source split
would carry"*) — while the other **24** are the ordinary English intensifier
(*"the whole point"*, *"a whole card"*, *"whole subject"*), 25 of the 29
predating this card at `4f160e62`. `grep -niE "entire|389 ?k"` → **1**, the
unrelated word *"entirely"* at line 788. **No occurrence asserts the
whole-source mechanism**, which is the substantive property, and that is now
the claim rather than a count that does not reproduce.

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
measured round-robin, medians). **That `cost(maxlines)` curve is NOT a second domain, and calling it one was
wrong** (cycle 2, F-C2-08). Timed at 11 points across the real bound range and
summed over **all 2 556 actual bounds** rather than over a mean it gives
**11.57 s**, 0.8 % away — but it shares the **timer, the process, the planted
text and the split function** with the instrument above, so what it controls is
the **aggregation** (whether a mean is a fair summary of a non-linear cost), not
the instrument. Agreeing to 0.8 % is the tell. **A genuine second domain
exists, and it is cycle 2's rather than this card's**: an in-situ wall clock
with no count × ms model in it at all — three interleaved arms over the same
108 analyses in one process, the two routed call sites sent back to
`ast.get_source_segment` **by caller line**, and a third arm measuring the
dispatcher's own overhead instead of assuming it. It measures the saving at
**12.20 s**, against which the bounded model (11.48 s) is **5.9 % LOW** and the
whole-source model (14.72 s) **20.7 % HIGH** — so F-287-01's correction had
real consequence. *Measured by review cycle 2, cited here as theirs; this
station did not retake it.* Cycle 1's own reading of that row was 11.80 s, i.e. 16.08 vs 15.19
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

**Why the equality means anything: the capture is SENSITIVE, and the measure of
that is SECTIONS, not lines** (cycle 2, F-C2-05 and F-C2-06 — a bound that was
closeable and is now closed). A divergence injected at each changed call site,
the capture recomputed, and the two texts compared **three ways**: index by
index, by `diff`'s own edit script, and **section by section** over the
capture's named sections. Re-derived at fix round 2 on the committed blob, three
injections of this station's own:

| injection at the changed site | capture lines | positional one-sided | `diff` one-sided | **sections whose content differs** |
|---|---|---|---|---|
| **hot**, one character *appended* | 1 752 | **75** (4.3 %) | 75 | **6 of 52** |
| **hot**, one character *dropped* | **1 744** | **1 543** (88.1 %) | 75 | **6 of 52** — *the same six* |
| **cold**, one character *appended* | 1 752 | **8** (0.5 %) | 8 | **1 of 52** |

Non-zero at **both** sites, so the capture really does read the output of both
changed call sites and **is not self-confirming** — and the six sections are
named rather than counted: `AC6 real/shipped sites`,
`AC6 real/no-door-arms sites`, `AC6 real/follow-terms sites`, and the
`PLANTED_LITERAL` / `DERIVED_INSTEAD` / `EXEMPTED_TERM` outcomes; the cold
site's one is `AC3 counting expressions (lineno, text)`.

**And this is how cycle 1's 1 535 and fix round 1's 75 are the SAME FACT.** A
positional line-by-line comparison of a `pprint`-formatted text **is not
invariant under a change in the text's line count**: a divergence that
*lengthens* each segment leaves the capture at 1 752 lines and moves only the
75 lines whose content changed, while one that *shortens* it re-wraps `pprint`
to 1 744 lines, after which almost every later line differs **positionally**
although the same six sections carry the change. Cycle 1's figure is
**reconstructed to within 8 lines** by a one-character drop — **1 543 of
1 752** against its 1 535, with the first changed line at index 2 exactly as
the append has it and the same six sections behind both — so
neither round measured wrongly and neither magnitude was a property of the
capture. *What the two rounds were missing was an instrument whose domain is
the answer rather than the formatting*, and two of them are invariant across
every injection above: **the section set — and only the section set** (cycle
3's F-C3-02). The `diff` claim was half right and is corrected here: the `>`
side **is** 75 either way, so the table's `diff` one-sided column is right,
but **the edit script as a whole is not invariant** — a one-character *drop*
really removes 8 lines and `diff` accounts for them (`<` = **83** against 75,
two-sided **158** against 150), and the per-line content count inside those
sections moves too (75 vs 103). Verified by cycle 3 with system `diff` **and**
`difflib` as an independent second implementation, agreeing exactly. *Fix
round 2's own log carries the disproof of its own sentence — `two-sided … =
158` — and reported it without noticing.* The paragraph's conclusion is
unaffected. The card now
leads with the sections.

On the **extended** capture the same hot injection reaches **69 of its 257
sections** and **793 of 11 936** lines (6.6 %), the cold one **1 of 257** and
**8** lines — re-derived here from the round's own saved outputs with this
station's own comparator. **Which settles the two figures the artefacts
disagreed on** (cycle 2, F-C2-06): `fix1-capture-equality.log`'s **1 586** and
**16** are `diff | grep -c '^[<>]'`, a **two-sided** count that reads **both**
sides of every changed line — exactly **2 × 793** and **2 × 8**. The card's
**793 / 8** is the right count; the log's pair is superseded and a note saying
so now sits beside it in the artefact directory.

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

### The mechanisms added, and the eleven mutants over them — **with a saved log**

`test_no_analysis_in_this_file_reaches_for_the_stdlib_splitter` makes the saving
**durable** — the stdlib and the memo return the same string, so a regression
would be invisible to every other control in the tree. Default-deny over an
enumerable authority (ADR-0039/R2): a two-sided set equality between the
outermost enclosing scope of every `*.get_source_segment` **call** and
`STDLIB_SEGMENT_SCOPES`, with **both** controls inline — it must rise on a call
planted in a foreign scope and must **not** rise on a mention.

All ten rows were **re-fired at fix round 1** — the eight original ones
because the derivation changed underneath them (F-07), plus two over the fix
round's own addition — and the run is now **logged**, which F-06 filed as
missing: `mutant-census-fix1.log` carries every mutant, the assertion that
fired *with its own message*, and the restore hash after each
(`4d9a8977…`, checked eleven times, `git status --porcelain` clean apart from
the fix edits themselves). **All eleven rows were re-fired again at fix round
2**, because that round changed the **plant** the last two rows run against:
`mutant-census-fix2.log`, same shape, restore hash `b34512e8…` checked twelve
times (the unmutated control first), and the eleventh row is **E1**, the edge
mutant cycle 2 fired and found surviving.

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
| **E1** *fix round 2* — **the EDGE of N1's own claim**: `node.lineno` → `node.end_lineno` | **killed** | the **positive control**: `assert [('Foo', 5)] == [('Foo', 4)]` |

**S1 and S2 now name different lines — 2938 against 1460 — which is F-07
closed:** before the fix they produced the identical message. **N1 proves the
line is load-bearing** and that the positive control is what pins it.
**E1 closes the matching EDGE, and it was a real gap**: with the single-line
plant fix round 1 wrote, `node.lineno` and `node.end_lineno` are the same
number, so swapping them was invisible to **every** assertion in the tree —
cycle 2 fired it and it **SURVIVED** (F-C2-04). The plant now spans two lines
(`lineno` 4, `end_lineno` 5) and the same equality asserts `[("Foo", 4)]`, so
it pins the line the call **opens** on; E1 reds it with
`[('Foo', 5)] == [('Foo', 4)]`. *A closeable bound CLOSED rather than
declared, and the inside/edge pair the board asks of a comment that says what
a test catches is now two runs rather than one.* **N2 is an honest declared
negative:** a failure *message* is only rendered on failure,
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
full-suite run is forbidden to the implementation station. **Both baselines,
stated separately, because the arrow mixed them** (cycle 2, F-C2-09): what is
**measured** is this round's **arm B, 70.62 s**; AC-8 **mandates** reporting it
against the card's own pre-round figure of **105.66 s**; and the round's own
**arm A on this host is 100.19 s**, ~5 % lower for the host reason this card
declares two paragraphs down. *"105.66 → 70.62 s is measured" was an arrow
whose two ends came from different host states.* The projection subtracts the
round's **own** delta, which is the honest construction and the arithmetic
actually used: **100.19 − 70.62 = 29.57 s** off 1270.34 s → **≈ 1240.8 s**,
file share **≈ 5.69 %** (was 8.32 %), class **≈ 2.66 %** (was 4.85 %).
*Re-derived at fix round 2 from the two figures themselves: the mandated
105.66 s baseline would instead give 1235.3 s, which is **not** the number on
this card, so the card's own arithmetic already used arm A.* CARD-292's
file-level prediction agreed with its suite gate to 1.7 %, which is the
precedent for the method — but **it stays a PROJECTION until the merge gate
measures it.**

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
| **F-08** | **three** analysis call sites, not two, everywhere | the spy's by-caller-line census, `{718, 24, 8}` — *keyed in this round's log to the superseded blob's lines `1750/2927/1449`; the committed blob's are **1761/2938/1460** and the 718 is a **planted** analysis's (cycle 2, F-C2-03, re-derived at fix round 2)* |

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

## [CYCLE 2 — 2026-10-28] **8.0, CERTIFIED**, zero gating

`meta/review/20261028T042701Z-CARD-287-cycle2.yml`, reviewed `eb2bbf81`.
**All eight of cycle 1's findings are closed**, each on evidence cycle 2
re-derived, and **G-1 HELD after the functional edit on a stronger instrument
than either round used.** Nine findings remain, **none gating** — one major and
eight minor, each a prose correction or a four-character control.

### PRIORITY ONE resolved: neither magnitude was wrong

The 20× sensitivity disagreement between cycle 1 (1 535 of 1 752) and fix round 1
(75 of 1 752) is **an artefact of the comparison, not of the instrument**: *a
positional line-by-line equality over a `pprint` text is not invariant under a
change in the text's line count.* Ten injections at three scopes:

| injection | lines | pos-diff | % | sections |
|---|---|---|---|---|
| hot, append 1 char (**fix round 1's**) | 1752 | **75** | 4.3 | **6/52** |
| hot, same-length swap | 1752 | 75 | 4.3 | 6/52 |
| hot, **drop 1 char** (**cycle 1's family**) | 1744 | **1543** | **88.1** | **6/52** |
| hot, append 10 chars | 1769 | 1606 | 91.7 | 6/52 |
| cold | 1752 | **8** | 0.5 | 1/52 |
| all three sites | 1758 | 631 | 36.0 | 8/52 |

**Cycle 1's figure is reconstructed**: a one-character *shortening* gives 1 543
against its 1 535 — same first-diff line, same sections. **Both of the
orchestrator's hypotheses were refuted** (scope gives 559/631, not 1 535), and
the hot site reaches **exactly the same 6 of 52 sections under every
injection** — so **the invariant measure was already in the round's own data**:
6/52 hot, 1/52 cold. The load-bearing conclusion — the capture reads both changed
sites and is **not self-confirming** — reproduces and is strengthened. Could not
establish: **the exact character cycle 1 injected**, which saved no script.

### F-C2-01 (major) — a cross-run share, and cycle 1's own verdict was wrong

AC-1's headline `14.366 / 68.35 = 21.0 %` takes **numerator and denominator from
two different cProfile runs**, while the card claims *"same profiled run …
avoided by construction"*. The same-run share is **22.0 %**. The proof is inside
the kept artefacts and the orchestrator re-verified it: `ac1_A.txt` records
`_splitlines_no_ff` cum **14.490**, `ac1_callers.txt` records
`get_source_segment` cum **14.366** — and since the latter *calls* the former,
14.366 < 14.490 is **impossible within one run**. The column header is also wrong
for rows 2–3: those are `_splitlines_no_ff` cum, not `get_source_segment`.

**Cycle 1 verified AC-1 and was wrong to**: it checked `ac1_profile.py`'s
*construction*, which does not produce the cell the card leads with. Note the
precise scope — CARD-292's profiled-over-unprofiled defect really **was** avoided;
what was introduced is the smaller cross-run variant, worth 1 percentage point.

### The other eight, all minor

**F-C2-02** the class audit is offered as a grep that does not reproduce
(`grep -c whole` → **29**; the grep returning 1 is `grep "whole source"`) — the
substance holds, no occurrence asserts the false mechanism. **F-C2-03** F-08's
`:1750/:2927/:1449` are the **superseded blob's** lines; the committed blob has
**1761/2938/1460**, which the card's own mutant table names — internally
inconsistent. **F-C2-04** the added mechanism has an inside mutant and **no edge
mutant**: `node.lineno → node.end_lineno` **SURVIVES** — **CLOSED at fix
round 2** (`83b7dcd2`), killed by the positive control over a two-line plant.
**F-C2-05** the
sensitivity magnitude was closeable and was declared instead. **F-C2-06** two
kept artefacts give **1 586** and **793** for the same measurement (the 1 586 is
a two-sided `diff | grep -c '^[<>]'` double count). **F-C2-07** AC-3/4/5/6 each
cite `(test: …)` for a test that **does not exist**, while the same file carries
`test_no_docstring_names_a_test_that_does_not_exist`. **F-C2-08** AC-2's declared
"second domain" shares timer, process, text and split function with instrument A
— it controls the **aggregation**, not the instrument. **F-C2-09** AC-8's "File
105.66 → 70.62 s is measured" mixes baselines, though the projection's arithmetic
correctly uses the round's own 100.19.

### What cycle 2 re-derived, and in which domain

- **Reach 81.1 / 43.1 / 96.7 %** — *new domain*: at the **stdlib boundary**,
  recording the `maxlines` CPython actually passes (the round recorded
  `node.end_lineno` at the caller). **Reproduced exactly**, zero unbounded calls.
- **The saving** — *new domain*: **in-situ wall clock**, no count×ms model, three
  interleaved arms plus a third measuring the dispatcher's own overhead:
  **12.20 s**. The bounded model (11.48 s) is **5.9 % low**; the **whole-source
  model (14.72 s) is 20.7 % high** — *F-287-01's correction had real
  consequence.* Its A 27.49 / B 15.07 reproduce the round's 27.88 / 15.19 to
  1.4 % / 0.8 %.
- **2 556** and `23×36 + 24×72` in two doors; `24×108 = 2 592` confirmed wrong.
  **AC-6** 832 / 770 / 0 and the cumulative sequence, live, two domains.
  **AC-7** 132 → 133 by its own `comm`. **G-1's capture equality** on its own
  loader, both arms, sha256 equal to `before.txt` and `after2.txt`. **The
  extended capture's seven axes audited section by section**
  (100/8/18/24/21/34 = 205 new; 52 + 205 = 257; 11 936 − 1 752 = 10 184),
  **nothing left as a bare `len()`**. The pre-gate's **blob identity** against
  its stale `HEAD:` cell.
- **G-5 run explicitly**: 606 passed, 0 skipped, exit 0, and
  `606 = 29 + 410 + 167` by per-file collect-only, **so the browser file really
  contributed** rather than being named and skipped.

### N1 and N2

**N1** is killed by the positive control **and only it**, and that is *correct
and sufficient for what N1 claims* — the positive control is the only assertion
that can see the lineno at all. But it is **insufficient for the mechanism**: the
plant is single-line, so it pins *that a line is reported*, not *that the right
line is*. **Unlike M1 this is not structurally unkillable** — a two-line plant
closes it, **and fix round 2 closed it**: E1 now reds the positive control
with `[('Foo', 5)] == [('Foo', 4)]`. **N2's reason is correct** (an assert's message operand is evaluated
only on failure) and cycle 2 confirmed un-observability with a **second** message
mutant of its own, so it is *a declaration with a control, not a claim wearing
one*; S1-vs-S2 is adequate evidence the message is right. One slight
overstatement: the un-killability is a property of the inline f-string **shape**,
not of the tree. **M1** survived the F-07 re-fire as declared; **S1/S2** killed
naming **2938** and **1460** separately — F-07 genuinely closed, verified here
rather than read from the log.

### The last mile — four characters — **TAKEN at fix round 2**

**Span the positive control's planted call over two lines so
`lineno != end_lineno`**, which kills cycle 2's **E1** and reds on nothing.
*"Nothing else in this review asks for code."* → done in `83b7dcd2`: E1
**killed** by the positive control, the guard class green, and both capture
equalities re-run. See the fix round 2 section below.

### Could not establish, in those words

The exact character cycle 1 injected; **when `prediction.txt` was written**; the
suite-wide figure (AC-8, the merge gate's); whether the other two tests' cProfile
readings reproduce (only the dear test's pair was retaken); whether the residual
~32.7 s is reducible (**CARD-303's**).

## [FIX ROUND 2 — 2026-10-28] `83b7dcd2` — the lineno claim gets its EDGE mutant, and eight prose corrections

Against `meta/review/20261028T042701Z-CARD-287-cycle2.yml` (**8.0, CERTIFIED,
zero gating**). **Cycle 2 asked for one thing in code and it was four
characters; everything else here is a figure or a label.** One file,
`tests/test_book_export_interior_cover.py`, **+18/−6**, blob `b34512e8`.
`src/` and `pyproject.toml` **zero diff** (G-2). Nothing changed behaviour
beyond the plant: no derivation, no authority, no assertion operand.

### F-C2-04 — the EDGE mutant, CLOSED rather than declared

Fix round 1's one mechanism had an **inside** mutant (N1, the lineno deleted)
and no **edge** one, and cycle 2 fired the edge: `node.lineno` →
`node.end_lineno` in `_stdlib_segment_scopes` **SURVIVED** the whole file,
because the positive control planted a **single-line** call, so
`lineno == end_lineno == 4`. All four of this file's own
`*.get_source_segment` calls are single-line too — `(6501, 6501)`,
`(6547, 6547)`, `(6623, 6623)`, `(6624, 6624)`, re-derived here as
`(lineno, end_lineno)` pairs — so the main set equality could not see it
either.

The plant now spans two lines — `ast.get_source_segment(\n            source,
node)`, `lineno` **4**, `end_lineno` **5** — and the equality still asserts
`[("Foo", 4)]`, so it pins the line the call **OPENS** on. **E1 is killed**,
by the positive control, with its own message:

> `AssertionError: the derivation does not rise on a call planted in a foreign
> scope, or does not report the line that call OPENS on, so its zero above says
> nothing (positive control)` — `assert [('Foo', 5)] == [('Foo', 4)]`

The docstring's mutant paragraph now names that edge row beside N1, so the
board's two-mutant rule for a comment that says what a test catches is met by
**runs** rather than by argument. *Unlike M1 — which is structurally
unkillable on this file — this bound was closeable, and a closeable bound is
closed.*

**The census, re-fired over the changed plant** (`mutant-census-fix2.log`):
**eleven mutants** plus the unmutated control, one node id at a time, **per
assertion**, line-count-preserving, each restored and checked with
`git hash-object` against `b34512e8` — **the committed blob**, twelve checks
all OK and `git status --porcelain` **empty** after the last restore. *The
census was fired once on an intermediate blob and then **re-fired whole** on
`b34512e8`, because a restore hash that names a blob the run did not use is
not a control; both runs give the same eleven verdicts.* S1 **killed**
naming **2938**, S2 **killed** naming **1460**, S3 killed, S4 survived (the
negative control), M1 survived **as declared**, M2/M3/M4 killed, N1 killed by
the positive control (`[('Foo', 0)]`), **E1 killed** (`[('Foo', 5)]`) where it
survived before, N2 survived **as declared**.

### G-1 — both capture equalities re-run after the edit, both arms

**Both arms, both captures, byte-identical — and the arms are the file's own
blobs, not a description of them.** Arm A is `4f160e62`'s blob `8741bd33`,
swapped in with `git show` and restored under `git hash-object` after every one
of the **six** swaps the capture/profile driver made — two arms, three
injections, and arm A once more for the profiles — each verified back to
`b34512e8` inside the driver, which exits non-zero on a mismatch; plus the
**eleven** in the census, checked the same way. `git status --porcelain`
clean at the end of both.

| capture | arm A (`8741bd33`) | fix round 2 (`b34512e8`) | result |
|---|---|---|---|
| the round's **52-section** capture | 1 752 lines, 52 sections | 1 752 lines, 52 sections | **`cmp` IDENTICAL**, sha256 `223019c2…` |
| the **257-section** extended capture | 11 936 lines, 257 sections | 11 936 lines, 257 sections | **`cmp` IDENTICAL**, sha256 `eb754d30…` |

Both sha256s also equal the round's own kept artefacts — `223019c2…` matches
`before.txt` **and** `after2.txt`, `eb754d30…` matches
`extended-capture_armA.txt` **and** `extended-capture_armBfix.txt` — so this
station's runs agree with fix round 1's and with cycle 2's. A second accounting
beside `cmp`, written for this round: **0 of 52** and **0 of 257** sections
differ in content, and the positional diff is **0** in both. **G-1 holds
through fix round 2.**

### The eight card and artefact corrections

| finding | what was wrong | what it says now, and the door |
|---|---|---|
| **F-C2-01** (major) | AC-1's headline `14.366 / 68.35 = 21.0 %` mixed **two cProfile runs** while the card claimed *"same profiled run … avoided by construction"* | the share **re-derived from one `cProfile` object per test**, the column **relabelled** (rows 2–3 were `_splitlines_no_ff` cum, not `get_source_segment`), and the scope stated: CARD-292's profiled-over-unprofiled defect **was** avoided; this was the smaller **cross-run** variant |
| **F-C2-02** | the class audit was offered as a grep that returns **29**, not 1 | the grep that reproduces is `grep -c "whole source"` → **1**; the 29 are counted and classified, 24 of them the ordinary English intensifier |
| **F-C2-03** | `:1750/:2927/:1449` were the **superseded blob's** lines | re-keyed to **1761/2938/1460** through two doors on the committed blob, and the `{718, 24, 8}` census given the **domain it was missing**: 718 is one **planted** analysis, 716 the real module |
| **F-C2-04** | an inside mutant and no edge mutant | **the one code item**, above |
| **F-C2-05** | the sensitivity magnitude was closeable and was declared | **resolved** — the disagreement is an artefact of the comparison, and the invariant measure is **sections**, re-derived here in three injections |
| **F-C2-06** | two kept artefacts give **1 586** and **793** for the same measurement | reconciled in the artefact directory: the 1 586 is a **two-sided** `diff \| grep -c '^[<>]'` double count; **793 / 8** is right |
| **F-C2-07** | AC-3/4/5/6 cited `(test: …)` for tests that **do not exist** | every `(test: …)` and `(recorded…)` ref on the card audited as a **class**; each AC now says what really verifies it |
| **F-C2-08** | AC-2's "second domain" controlled the **aggregation**, not the instrument | restated as such, and cycle 2's genuine second domain (in-situ wall clock, **12.20 s**) cited **as cycle 2's** |
| **F-C2-09** | AC-8's arrow mixed baselines | **both baselines stated**, the projection's own arithmetic re-derived, and AC-8 kept labelled a **PROJECTION** |

**The class behind F-C2-07, audited rather than the instance.** Every `test_*`
token on this card was resolved against the tree, not just the four cycle 2
named. **As cycle 2 left it**: 16 distinct tokens, of which five are file
stems (`test_book_export_interior_cover`, `test_browser_fixture_scope`,
`test_guard_integrity`, `test_kill_matrix`, `test_suite_profile`) and one a
config key (`review.test_scope`); of the **ten** real test references,
**four** named a test that exists nowhere — exactly AC-3's, AC-4's, AC-5's and
AC-6's — and six existed. AC-2's `TestSuiteProfile_*` is real (three classes)
but guards the *profiling artefact* rather than this card's delta, so it is
relabelled too. **Re-audited after the corrections**: the card again carries 16
tokens, the four dead names are gone, four live ones took their place
(`test_the_split_is_computed_once_per_distinct_text`,
`test_a_seeded_corpus_of_the_real_module_segments_identically`,
`test_no_planted_shape_is_declared_silent`,
`test_the_callee_arm_defaults_to_deny_and_every_exemption_pays_its_cost`), and
**all ten real references now resolve to a `def` in the tree** — nine in this
card's own file, one (`test_ac7_the_four_arm_grid_of_card_257_reproduces`)
elsewhere. *Attributed by resolving each assertion's **enclosing test**, not by
the file it sits in; no test was invented to satisfy a reference.*

### Pre-gate, fix round 2 — one invocation over the same derived radius of ten files

`pytest -o addopts='' -q -rs` over the same derived radius of ten files, with
`tests/test_browser_fixture_scope.py` **explicit** (G-5), subject blob
`b34512e8` — which is what `83b7dcd2` contains, and the log's `HEAD:` cell says
`83b7dcd2` this time rather than the previous commit.

- **collect-only: 1 051 collected**, exit 0 — and **every one of the ten files
  contributed**, counted off the collect output rather than assumed:
  410 + 167 + **133** + 126 + 76 + 41 + 34 + **29** + 22 + 13 = 1 051. The
  **29** is `test_browser_fixture_scope.py` (**G-5** — named *and* collected,
  not named and silent) and the **133** is this card's own file, AC-7's count
  unchanged by this round.
- **run: 1 051 passed, 0 failed, 0 errors, 0 skipped**, exit 0, **279.96 s**.
- `-rs` printed **zero `SKIPPED` lines and no short-test-summary section**, so
  **there is no skip to attribute**; no `s` appears in the progress line either.
- Host cells: **rival-pytest 0 at both ends** (`pgrep -f
  'MacOS/Python.*pytest' | wc -l`), load **4.35 → 4.85**,
  `$TMPDIR/nonogram-test-hang.txt` **0 bytes** — no per-test kill, against the
  120 s ceiling. **`NONOGRAM_TEST_HANG_SECONDS` was left unset in every run of
  this round** — the census, the seven capture runs, the three profiles, the
  two probes and this gate; it is set **nowhere**.
  `meta/kanban/.full-suite.lock` **absent at the start and the end of every
  run and never taken**; **the full suite was not run.**
- G-4 holds: no file added or removed under `tests/` or `meta/profiling/`, so
  the frozen render set cannot have moved, and `tests/test_suite_profile.py`
  ran explicitly inside this gate (410 of the 1 051).

### Could not establish, in those words, at fix round 2

- **The suite-wide figure.** AC-8 stays a labelled projection; the full suite
  was **not** run here, and `meta/kanban/.full-suite.lock` was **absent at both
  ends of every run and never taken**.
- **The exact character cycle 1 injected.** Unchanged: cycle 1 saved no
  injection script. What *is* now established is the **family** — a
  one-character shortening — and the **invariant** measure, which is sections.
- **When `prediction.txt` was written.** Unchanged from cycle 1, cycle 2 and
  fix round 1: no artefact readable here carries that ordering.
- **Whether N2 is killable** in its chosen shape. Unchanged, and cycle 2
  confirmed the reason with a second message mutant of its own.
- **Whether cycle 2's 12.20 s in-situ saving reproduces.** Not retaken at this
  station; it is cited as cycle 2's measurement, in cycle 2's domain.
- **Whether the residual ~32.7 s is reducible** — **CARD-303's**.

**Artefacts added at fix round 2**, at `~/Documents/nonogram-reviews/CARD-287/`:
`mutant-census-fix2.log` + `mutate3.py` (the re-fired census);
`fix2-capture-equality-and-ac1.log` + `driver-fix2.sh` + `compare-fix2.py`
(both capture equalities, the three injections, and the same-run profiles, with
every swap restored under `git hash-object`); `ac1_same_run-fix2.py`;
`f03_sites-fix2.py` + `fix2-f03-sites.txt` + `fix2-f03-determinism.txt`;
`fix2-F-C2-06-reconciliation.txt`; `pregate-fix2.txt`; `commit-fix2.msg`. None
tracked; none under `tests/` or `meta/profiling/`.

## [CYCLE 3 — 2026-10-28] **CERTIFIED at 8.5**, zero gating — the last cycle

`meta/review/20261028T061828Z-CARD-287-cycle3.yml`, reviewed `83b7dcd2`. Score
**up from 8.0**. `max_cycles` is spent; cycle 3's own words: *"No cycle 4 exists
without a fresh owner decision, and none is needed."*

### E1 confirmed killed — and verified the way a fix should be

Fired on the committed blob: killed by the **positive control**,
`assert [('Foo', 5)] == [('Foo', 4)]`, the main set equality running first and
not firing. **Then it fired the same mutant on the superseded blob `eb2bbf81`
and it SURVIVED** — so fix round 2's premise is **a run here, not a citation**.
Neighbours as declared: S3 killed naming `_attribute_callee_laundering`, S4
surviving as the negative control, M1 surviving, N1 killed, N2 surviving.

**The choice of pinning the opening line is right and was checked rather than
assumed**: it is the convention **both doors of the card's own census already
use**, and all seven `_source_segment` sites are single-line. The two-line plant
still exercises a **foreign** scope and returns the **class**, not the method.

### Both adjudications went against both previous stations

**The share is a BAND.** See AC-1 above: five same-run readings span
**21.2–22.0 %**, mean **21.59 %**, the denominator carrying **5.5 %** spread.
Cycle 2's "1.0 pp" and fix round 2's "0.2 pp" are each the distance to that
station's **own single run**; against the mean it is 0.57 pp. *Three stations
quoting a point for a quantity with that much spread is the finding.*

**The diff invariant is half right.** Only the **section set** is fully
invariant; the `>` side is 75 either way but the edit script as a whole is not,
and **fix round 2's own log carried the disproof and reported it without
noticing**.

### 716 vs 718 — confirmed, strengthened, and it moves nothing

Real module **716** at site 1761, planted `DOOR_SHAPES[0]` **718**, 24 and 8
unchanged — deterministic over **six** processes, three with hash randomisation
and three with fixed `PYTHONHASHSEED`, **nine readings of each**. And the
downstream check was made rather than argued: the 716/718 lives at the
already-memoised site, while `sum(len(sites))` over the dear test's 108 analyses
is **2 556** with distribution exactly `{24: 72, 23: 36}`, and the spy's count at
the **hot** site agrees — two doors, one run. **Bonus**: "7 334-line planted
module" looks like an off-by-one and is not — `len(ast._splitlines_no_ff(src))`
is 7 334 where `splitlines` gives 7 333, and **the splitter's count is the right
denominator** for the 81.1 % reach.

### Everything else re-derived or sampled

**G-1 held, re-run on both arms with cycle 3's own capture re-implementation** —
both 1 752 lines / 52 sections, `cmp` identical, sha256 `223019c2…`, equal to
`before.txt` **and** `after2.txt`, 0 of 52 sections differing. **All ten card
refs resolve to a real `def`** at `83b7dcd2`, attributed **by enclosing test**
via an AST pass, with the asserting line named for each. F-C2-02's grep
enumeration reproduces exactly, including that **25 of 29** predate the card by
`comm`. **AC-7** 133 by three doors. **G-5 run explicitly** (29 collected, 29
passed) and **G-4** too (410 passed). **G-7**: CARD-303 named at five places.

Two pieces of scepticism worth keeping: it noticed the **three pre-gate logs are
all exactly 150 584 bytes**, checked rather than assumed, and established they
are **three distinct runs** by sha256; and it confirmed the census log names the
**mutated** blob throughout, with twelve OK restore lines and no intermediate
hash.

### The four minors, and what was done with them

**F-C3-01** (the share needs a band) and **F-C3-02** (only the section set is
invariant) are **corrected above by the orchestrator** — one clause each.
**SHIPPED UNCERTIFIED**: `max_cycles` is spent, so no reviewer has seen these two
edits; they are prose on the card, they change no code, assertion or figure's
*derivation*, and the merge gate is what stands behind them. **F-C3-04** (two
kept probe scripts imported an `fload` that was not in the artefact directory, so
they could not be re-run as kept) is **closed** — `fload.py` copied in.

**F-C3-03 is left DECLARED, on cycle 3's own judgement that it is not wanted
before merge**: the lineno mapping is pinned at **one** point, so a
`node.lineno → 4` constant mutant survives, as does `node.lineno →
node.func.value.lineno` (a true equivalent mutant, M1's declared class). The
remedy named is a second planted call at a different line, four lines, killing
it and redding on nothing. **Available as a last mile; not required for the
certification.**

### What the merge gate owes

1. **The measured suite figure closing AC-8** (projected ≈ 1 240.8 s, file
   ≈ 5.69 %, class ≈ 2.66 %) — *the only item of substance; everything else on
   this card is measured.*
2. **The merge commit must not restate what two branch commit messages cannot
   unsay**: `8b908a73`'s whole-source reach, "two call sites", the 6.238/6.779 ms
   pair and "ten configurations"; and `eb2bbf81`'s grep claim and its
   `1750/2927/1449`. Standing from cycles 1 and 2, open by nature until merge.

### Could not establish, in those words

The exact character cycle 1 injected; **when `prediction.txt` was written**; the
suite-wide figure; whether cycle 2's 12.20 s in-situ saving reproduces (not
retaken, and **no claim rests on its exact value**); **which single run is "the"
same-run share** — bounded at 21.2–22.0 %, mean 21.59 %, with **no reading
privileged**; whether the 257-section capture re-runs identical from cycle 3's
own script (the kept pair was verified instead); whether the residual ~32.7 s is
reducible (**CARD-303's**).

## [MERGED — 2026-10-28] `90c01386` — AC-8 closed on the total, and stated with its limits

**Merge gate: 9379 passed, 27 skipped, 0 failed, 0 errors, 1222.22 s (20:22).**
Load **4.13 → 7.58**, rival-pytest **0 → 0**, hang dump **0 bytes**, both skips
attributed by name, **27 the baseline exactly**. **9379 is +1 on CARD-292's gate,
reconciling to AC-7's audited single addition.** The switch-name scan on the
merged tree is clean.

### AC-8, and the part that is not a win

| | |
|---|---|
| projected total | **1240.77 s** |
| measured total | **1222.22 s** |
| → the projection is | **1.5 % high** — *AC-8 closes on the figure it asked for* |

**But the apparent saving is 48.12 s against a projected 29.57 s — 1.63× — and
that excess is NOT attributable to this change.** The two gates were taken at
different host states (load-start **7.59** against **4.13**), a merge gate cannot
interleave arms, and *this card's own subject is that a wall-clock delta between
two runs at different host states is not a measurement*. **The attributable
figure remains the round's interleaved one** (class −42.8 %, file −29.5 %,
re-derived by cycle 2 at −43.9 % / in-situ 12.20 s).

Likewise the file share: `70.62 / 1222.22 = 5.78 %` against a projected 5.69 %
**mixes an isolated file measurement with a suite total** — exactly cycle 2's
**F-C2-09** defect — so it is recorded as **arithmetic, not as a measured
share**. A profiled suite run would be needed to close that half, and none was
taken.

### Why three cycles, in one sentence

**Every major finding in all three was the same rule: an instrument's reach
claimed rather than measured.** Cycle 1: a *"whole source"* claim reinstated in
tracked code 300 lines from its own retraction, and a 1.0 % "agreement" that was
two compensating errors. Cycle 2: a share mixing two cProfile runs, and a 20×
sensitivity disagreement resolved as an **accounting artefact** — a positional
diff over a `pprint` text is not invariant under a change in line count. Cycle 3:
only the **section set** is invariant, and the share is a **band** (21.2–22.0 %,
mean 21.59, denominator spread 5.5 %) because cycle 2 and fix round 2 had each
anchored on their own single run.

**What was never in doubt after cycle 1**: the code is correct, the saving is
real, and **G-1 held** — the same 108 analyses over the same planted texts under
the same arms, with a **byte-identical** verdict set across a 1 752-line capture
and a 257-section, 11 936-line extension of it, re-run on both arms by three
different stations.

### Open at merge, stated

- **F-C3-01 and F-C3-02 shipped UNCERTIFIED** — `max_cycles` spent, no reviewer
  saw them; prose on the card changing no code or derivation.
- **F-C3-03 left DECLARED**: the lineno mapping is pinned at **one** point, so a
  `node.lineno → 4` constant mutant survives, as does the equivalent-mutant class
  M1 declares. Remedy named — a second planted call at a different line, four
  lines, killing it and redding on nothing.
- **AC-8's file-share half** is arithmetic, not a measurement (above).
- **CARD-303** owns the super-linear walk this round declined: 19.4 M inner
  `called()` invocations for a module of 832 call nodes, where **the walk is the
  guard** and G-1 will bite as it did not here.
