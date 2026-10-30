# CARD-220: Retire tests whose coverage another test already provides — only with a named survivor

**Status:** in progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/220-retire-subsumed-tests
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-220
**Source:** owner request 2026-10-13 ("make cards for tests curation") — the deletion half, deliberately cut last and narrowest of the four
**Idea:** —
**Wave:** 68 <!-- STAMPED 2026-10-30: owner sequenced this AFTER CARD-304. Encoded as a later wave rather than a `Depends on: CARD-304` edge, because there is no technical dependency -- 220 needs only CARD-217 (done). A sequencing preference written as a dependency would pollute the graph the dispatcher reasons over. -->
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-217 <!-- DISPATCH NOTE 2026-10-30: dispatched alongside CARD-314 while CARD-304 sits at its merge gate rather than merged. The wave-68 comment below records the owner's 'after CARD-304' sequencing; 304's implementation, two review cycles and two fix rounds are all complete and only the gate remains, so the sequencing is honoured in substance. Measured before dispatching: CARD-220 shares NO declared path with CARD-314 (Jaccard 0.00) and one with CARD-309 (`tests/test_book_pdf.py`, 0.09) -- both under `max_overlap: 0.3`, and neither is a conflict hotspot, while `book_pdf_generator.py`, which IS one, is touched by 309 and by neither of these two. -->
**Touches:** tests/test_book_pdf_band.py, tests/test_book_puzzle_frame.py <!-- ACTUAL, re-derived from `git diff --name-only 4d164f62..a58284bb` at implementation. The declared footprint below was `tests/test_book_export_interior_cover.py, tests/test_book_pdf.py, tests/helpers/book_corpus.py, meta/profiling/` and NOT ONE of those was touched -- the round widened with its reason, which the narrowing note itself sanctions, and flagged it rather than widening silently. `meta/profiling/` was deliberately left alone per AC-6's "recorded, not asserted". --> ORIGINAL DECLARATION: tests/test_book_export_interior_cover.py, tests/test_book_pdf.py, tests/helpers/book_corpus.py, meta/profiling/ <!-- NARROWED 2026-10-30 on owner decision, from `tests/**`. Two reasons, both measured. (1) `tests/**` overlaps essentially every open card, so under `dispatcher.max_overlap: 0.3` this card could only ever run ALONE and would block its whole wave. (2) The narrowing matches the card's OWN method: step 1 already restricts candidates to tests that are 'both expensive (in the top-50 list or a top-20 file) and suspected subsumed', so a repo-wide footprint was always wider than the work. The paths named here are where the measured cost actually is -- `test_book_export_interior_cover.py` alone is 29.8% of the suite's wall clock (90 -> 127 tests, 344.29s -> 467.30s standalone). THIS IS A FOOTPRINT NARROWING, NOT A SCOPE CUT: the deletion rule, the three never-touch classes and the per-pair mutation proof are untouched. If a proven-subsumed pair turns up outside these paths, widen the field with the reason -- do not delete outside the declared footprint silently. -->
**Review score:** — (implemented `a58284bb`, review cycle 1 running)
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**This is the only curation card that deletes anything, and it is deliberately
the most constrained.** 3795 test functions across 198 files, 116 846 lines.
The accumulation is real: 20+ waves of cards, each adding directed tests named
after its own ACs, plus the review cycles' regression tests, plus per-card
baselines. Some of that is now genuinely subsumed — a later card restated a
mechanism and tested it better, and the earlier card's test asserts a weaker
form of the same thing.

**But most apparent duplication here is load-bearing, and deleting it is the
expensive mistake.** Three classes must never be touched:

1. **Independent second implementations.** `tests/helpers/brute_force_oracle.py`
   holds two independent brute-force counters that cross-check each other, and
   `solver/propagate.py`'s `mask_runs` is deliberately reimplemented rather
   than imported so the test tree can cross-check it against
   `clues.encode_line`. These look like duplication and are the correctness
   mechanism (CLAUDE.md states both as project policy).
2. **Per-card AC evidence.** A card's directed tests are what its AC/EC gate
   read as proof. Deleting them removes the traceability a later review
   depends on, even when a property test covers the same ground more broadly.
3. **Corpus minimums.** The project's property tests assert a minimum case
   count inside the test "so the corpus can't silently shrink". Lowering one
   is not curation; it is coverage reduction wearing curation's clothes.

**The rule this card works under — one sentence:** no test is deleted without
naming, in the diff, the surviving test that still covers its claim, and
proving by mutation that the survivor actually fails when that claim is broken.

**What to do.**

1. Start from CARD-217's rankings: candidates are tests that are both
   **expensive** (in the top-50 list or a top-20 file) and **suspected
   subsumed**. Cost alone is never a reason to delete — an expensive test with
   unique coverage is the suite earning its keep.
2. For each candidate, identify its claim (usually an `AC-N` in its docstring —
   this codebase's tests cite them) and search for the test that also makes it.
   Record the pair.
3. **Prove subsumption by mutation, per pair.** Break the production behaviour
   the claim is about; confirm the survivor fails. If the survivor passes while
   only the candidate fails, the candidate is NOT subsumed — keep it, and note
   the finding (the pair looked redundant and was not; that is a useful
   result).
4. Delete only the proven-subsumed ones. In the commit message and the card,
   one line per deletion: `removed <test> — claim <AC-N> covered by <test>
   (mutation: <what was broken, which survivor failed)`.
5. Where two tests are near-identical but neither subsumes the other (different
   edge, same body), prefer **parametrising** them into one test with two cases
   over deleting either — the case count stays, the code shrinks.
6. Re-profile solo (CARD-217's command) and record before/after, plus the
   collected-test-count delta, which must equal the number of deliberate
   deletions and nothing more.

**Expect a small number.** If this card deletes dozens of tests, something has
gone wrong with the subsumption bar — stop and escalate rather than continue; a
large deletion set means the proof step is being skipped.

## Acceptance criteria

<!-- DEAD `test:` REFS RESOLVED 2026-10-24, orchestrator, from CARD-218's review
cycle 1 (F-003) and the orchestrator's follow-up count. EIGHT distinct
`TestCuration_*` verifiers are named across CARD-218, CARD-219 and CARD-220 and
ZERO exist — there is no `tests/test_curation.py` and no class whose name begins
`TestCuration` anywhere under `tests/`. A planned shared guard module was never
written and three cards' ACs were written against it, which reads as
mechanically checked and is not.

Resolved once for all three cards: SIX of the eight are **diff properties, not
test properties**. "The count equals the pre-card count minus the deletions",
"no minimum was lowered", "these paths are untouched" all compare the tree
before the card with the tree after it, and no standing test can know "before
this card" — one that tried would be a hand-maintained census that every later
card breaks, the artefact class this card's own G-rules forbid. Those six move
to the AC/EC/G gate station as explicit gate-time measurements, each stated as
the derivation that produces it. No AC's substance changed; only what verifies
it, and each now names something that will actually be run.

This card is the one where the distinction bites hardest: its whole subject is
a DELETION LIST, so every one of its guards is a before/after comparison by
nature. Read AC-2, AC-3 and AC-4 as gate obligations on the card's own diff. -->

- **AC-1** (happy): *Given* each deleted test, *when* the card is reviewed,
  *then* the diff names its surviving covering test and the mutation that
  proved the survivor fails on the broken behaviour. (test: the card's recorded
  mutation evidence, per `review.mutation_check`)
- **AC-2** (guard, accounted count): *Given* the suite, *when* it runs, *then*
  the collected test count equals the pre-card count minus exactly the
  enumerated deletions (parametrised merges keep their case count). (**gate**: set difference over
  sorted node ids between the fork point and HEAD -- the removed set must equal
  the card's enumerated deletion list exactly, in both directions, and the added
  set must be empty. A standing test cannot know the pre-card count; see the
  resolution note above.)
- **AC-3** (guard, protected classes): *Given* the diff, *when* it is
  reviewed, *then* it touches none of: `tests/helpers/brute_force_oracle.py`,
  `tests/property/test_solver_uniqueness.py`, the `mask_runs` cross-check, the
  A4 golden test, or `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`.
  (**gate**: `git diff --name-only <fork>..HEAD` intersected with the
  protected set must be empty, and the two protected node ids must be present
  and green. This is a property of the DIFF, which no standing test observes.)
- **AC-4** (guard, corpus minimums): *Given* every property test, *when* the
  diff is reviewed, *then* no asserted minimum case count is lower than before
  the card. (**gate**: every integer literal
  compared against a corpus length is collected by `ast` at the fork point and
  at HEAD and the two sets compared -- no value may fall. Derived, not
  hand-listed; a property of the diff, so not a standing test.)
- **AC-5** (edge, failed subsumption): *Given* a candidate pair where the
  survivor passes the mutation, *when* the card finishes, *then* the candidate
  is still present and the card records why the pair was not redundant. (test:
  recorded in the card, verified by review)
- **AC-6** (happy, measured): *Given* a solo profile before and after, *then*
  both wall-clocks and the deletion list are recorded. (recorded, not asserted)

## Guardrails

- G-1: No test is deleted without a named survivor and mutation proof (AC-1) —
  this is the card's whole contract, not a preference.
- G-2: The three protected classes above are untouched (AC-3).
- G-3: Corpus minimums are never lowered (AC-4).
- G-4: Do not edit `src/**` — if a test can only be retired by changing
  production code, it is not a redundant test.
- G-5: Do not regenerate or delete anything under `tests/fixtures/**` — every
  fixture carries a "NEVER regenerate" warning, and the superseded golden books
  are deliberately-kept provenance that cost no runtime (verified 2026-10-13:
  only `book_corpus.BASELINE_FIXTURE` is loaded; the other 13 appear solely in
  docstrings).
- G-6: Run this card on a quiet board. Its footprint is `tests/**`, which the
  dispatcher's conflict graph cannot usefully narrow — any other card in flight
  will collide with it.
- G-7: Out of scope — fixture scoping (CARD-218), plan-vs-pixel conversion
  (CARD-219), and rewriting `tests/README.md` (its own backlog item).

## Architecture context

- **FR:** — (test infrastructure)
- **ADR:** ADR-0006/R1 (no new dependency), ADR-0036/R1 (the A4 golden — G-2).
- **CON:** CON-005 (the one mandatory correctness property, protected by
  AC-3/G-2), CON-019.
- **Components:** none (test tree only).
- **Trace:** not applicable.

## Worktree notes

—

## Correction inherited 2026-10-15, before this card starts

This card's premise includes CARD-217's finding that the superseded baseline recordings are
"referenced only from docstrings and cost no runtime". **That is no longer true.**
`book_baseline_card200/203/204/205.json` are loaded and compared at runtime by
`TestBookPdfMemory_NonDrawingPagesAreByteIdentical`
(`tests/test_book_pdf_memory.py:1715/:1731/:1747/:1764`) — proved at CARD-221's AC/EC/G gate by
a mutant that regenerates CARD-205's TOC-page digest and kills 2 tests.

So the fixtures are **live attribution evidence**, not inert provenance. Re-measure which
fixtures are actually read before proposing to retire anything that touches them, and treat
"nothing reads this" as a claim needing a measurement like any other — this is the second time
that particular claim has been wrong on this chain.

## Re-pointed 2026-10-15 by CARD-217's measurement

CARD-217 profiled the suite solo and **neither hypothesis this card was cut on is where the time
is**. Measured shares of a 930.81 s run: the browser family `tests/test_puzzle_solver_*.py`
**39.78%**, the render-heavy set **21.23%**, `tests/property/*` **15.23%** — and over half the
property time is itself render-heavy, so the corpus hypothesis was largely a restatement of the
render one rather than a rival. A browser test costs 868 ms against everything else's 83 ms.

So this card is **no longer the biggest prize**, and `meta/profiling/suite-hotspots-20261015.md`
is now its source of truth rather than the counts in its own body. **CARD-235** takes the
browser family and is P1 ahead of it.

**This card's cost premise is dead, and it should not be run as a performance card.** The profile
is explicit: **6057 tests finish under 0.1 s and hold 7.4% of the suite between them**, the top
50 tests hold 32.1%, and CARD-217's own recommendation is "**no single test is worth
deleting**". Retiring subsumed tests will not measurably speed anything up.

Two things follow. First, if this card is kept, it must be re-justified on **maintenance** terms
— duplicate coverage is a cost when a behaviour changes and five tests must be edited — and its
acceptance criteria rewritten accordingly, because they currently promise time that is not there.
Second, it already carries a correction from CARD-221's gate: the superseded baseline fixtures it
was told are inert **are loaded and compared at runtime**. Both corrections point the same way.

**Recommend: park it** until CARD-235, CARD-218, CARD-219 and CARD-236 have run, and re-cut it
from whatever duplication is still irritating then. Owner's call.

## Re-measured and re-pointed 2026-10-23, on the owner's request to curate tests

The owner asked for the suite to stop "testing everything several times"
(2026-10-23), which re-opens this card. Measured before re-cutting it, on
merged main at `ae164099` with the board's full-suite lock held:

| | 2026-10-15 (CARD-217, solo) | 2026-10-23 (solo) | move |
| --- | --- | --- | --- |
| wall clock | 930.81 s | **1433 s** | +54 % |
| tests | 7082 timed / 7073 passed | **8981 collected / 8954 passed** | +27 % |
| ms per test | 131 | **160** | **+21 %** |
| browser family | 366.19 s, 422 tests, 868 ms, 12 files | **474 s, 646 tests, 734 ms, 18 files** | grown 53 %, **15 % cheaper per test** |

**The per-test regression is real and not contention.** The 2026-10-23 run had
3 s of wall-clock overhead against pytest's own 1433 s and load averages
falling from 3.78/6.64/11.85 to 5.44/4.36/5.96; the same tree measured earlier
the same evening under load average 18 lost 555 s to the box and is recorded
in `suite-timing.log` as measuring the machine. So the suite costs 21 % more
per test than it did eight days ago, **while the browser family — the one
thing CARD-235 attacked — got 15 % cheaper per test.** CARD-235 worked and
something else grew. Where, is what the top-N rankings of
`meta/profiling/suite-durations-20261023.txt` are for; the digest regenerated
by `rank_durations.py --verify-render-set` is the source of truth for this
card from here, replacing the 2026-10-15 document.

### What today measured about the *kind* of waste, and it is not duplicate claims

Three findings from CARD-271, all with figures, all pointing away from
deleting tests:

1. **The cost that bit was SETUP, not assertions.** One fixed capture settle
   in `tests/test_puzzle_solver_fifth_rule.py` costs **13.5 s in a single
   file** — 27.35 s with it against 13.84/13.40/12.96 s without, three runs —
   and about +4 % on a 17-file selection. Deleting it is not an option (the
   file gets *flakier*), the obvious cheaper shape was refuted (the first
   capture of a test is not exempt, because `set_viewport_size` itself fires
   `resize`), and the one deterministic cheaper form is to poll the draw count
   until two reads agree. Backlogged. That is this card's thesis in one file:
   **the suite pays for setup, and assertions are nearly free.**
2. **The maintenance pain was hand-maintained CENSUSES, not duplicate
   coverage.** CARD-271 had to teach a selector-list equality about a new rule
   and register 27 node ids in the browser-fixture family's registry — 25 of
   which had been owed since its implementation commit, discovered only by a
   24-minute suite at the merge gate. That is duplicate *records of the tree*,
   which is a different cost from duplicate tests and is **not this card's**:
   it belongs to CARD-286 (reachability) and the registry's own @ops item
   (shape).
3. **The browser family is no longer the largest prize.** It was 39.78 % at
   868 ms/test; it is now 474 s of 1433 s — **33 %** — at 734 ms. Still the
   biggest single group, but CARD-235 took the easy half and the remaining
   per-test cost is page lifecycle, not teardown.

### The re-justification this card was told it needs

Its 2026-10-15 correction says the cost premise is dead and the card must be
re-justified on **maintenance** terms or parked. Today supplies the first real
maintenance figure: CARD-271 changed one CSS file and two JS functions and had
to edit **seven** test files plus a registry, and four of those seven were
outside its drafted `Touches`. None of that was duplicate coverage — each file
held a different claim — so even the maintenance case does not point at
deletion. It points at **where a claim lives**: a card that changes one
mechanism should not have to visit seven files to keep the tree honest.

So this card's honest scope is now narrower than its title: **retire what a
mutant proves is covered twice, and nothing else** — and the board already
owns the arbiter for that, `tests/kill_matrix.py`, which answers "do these two
tests die to the same mutant set" instead of "do they look alike". Everything
else the owner's request touches is cost, and cost is CARD-218, CARD-219 and
the setup items above.

### Park conditions, as of 2026-10-23

Of the four cards this card was told to wait for: **CARD-235 done**,
**CARD-236 done**, **CARD-218 and CARD-219 still `ready`**. CARD-218 is
dispatched into wave 56 on the owner's decision to override its scheduling
dependency on CARD-207/208/209 (the override is recorded on CARD-218, and
CARD-219 plus those three must be re-read against the refactored shape before
any of them dispatch). So this card stays parked until CARD-218 and CARD-219
land, and should then be re-cut from whatever duplication is still irritating —
measured against `suite-durations-20261023.txt`, not against the counts in
this card's own body, which are from wave 37 and are now wrong in both
directions (3795 test functions then, 5131 now; 198 files then, 218 now).

## DO NOT RETIRE THESE THREE — fence added 2026-10-24 from CARD-219's review cycle 1

CARD-219 converted seven positional tests in **`tests/test_book_toc.py`** from
rendering a book to reading the page plan. That conversion is correct and it
merged with a measured cost: **a plan assertion cannot witness a drawn count.**
Measured both ways, on both arms of the diff:

* an off-by-one in `interior_stream`'s `first_answer_page`
  (`src/nonogram/admin/book_pdf_generator.py:6718`) reds **4 cells before the
  conversion and 3 after**;
* an off-by-one in the TOC page walk (`:6923`, `range(toc_page_count)` →
  `range(toc_page_count + 1)`) reds **21 cells before and 14 after**, and **the
  7 lost cells are exactly the seven converted tests**.

Nothing escapes, because the drawn tie survives in **three tests and nowhere
else**. After CARD-219 these are the sole carriers, and **this card is the one
most likely to delete them**, because it is chartered to retire tests whose
coverage another test already provides — and seven tests in that file now *look*
like they cover the same ground while no longer carrying the tie:

- `tests/test_book_toc.py::TestBookToc_PageNumbersSurviveTheTitlePage::test_the_solutions_row_points_at_the_solutions_divider`
- `tests/test_book_toc.py::TestBookToc_PageNumbersSurviveTheTitlePage::test_the_comparison_would_have_caught_a_one_page_drift`
- `tests/test_book_toc.py::TestBookToc_PageNumbersMatchTheWalk::test_the_named_pages_really_are_those_pages`

**None of the three may be retired by this card**, and a "named survivor" that is
one of the seven converted tests is **not** a survivor for this coverage —
that is precisely the substitution the measurement above rules out. If this card
wants to retire one anyway, the test is the mutants above: re-run both, on both
arms, and show the cell count does not fall.

Also inherited from CARD-219, and **not this card's to fix**: `InteriorStream`
carries neither `toc_entries` nor `first_answer_page`, so the tie cannot be
re-expressed on a pure surface. Exposing them is a **successor card to
CARD-219** with a `src/` mandate; this card has none. Two further items CARD-219
raised and could not touch under G-2 are genuinely this card's:

- `TestBookToc_PageNumbersMatchTheWalk::test_the_named_pages_really_are_those_pages`
  carries a **pre-existing over-stated docstring** — it says "the walk is
  replayed page by page and each named position is checked against what was
  actually yielded there", and the body builds its map from `section_plan` and
  never looks at a yielded page. Note the tension: it is **one of the three
  carriers above**, so narrow the claim, do not retire the test.
- The two per-file `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
  tests in `tests/test_book_pdf_band.py` and `tests/test_book_puzzle_frame.py`
  are now redundant with the shared home's every-importer version
  (`tests/test_shared_fixture_controls.py`). Verified redundant: a mutant adding
  a `getfixturevalue` consumer reds **both** the per-file guard and the shared
  one. CARD-219's G-2 forbade deleting them; retiring them here needs the shared
  version named as the survivor.

---

## Implementation — `4d164f62` → `a58284bb`, 1 commit, 2 files, +66/−92

**Outcome: 2 deletions, both proven by mutation. No escalation** — the card's trigger is
"dozens", and the subsumption bar held, rejecting every other candidate including the expensive
ones. Worktree clean, nothing pushed or rebased, `meta/kanban/cards/` untouched. The lock was
checked by absolute path before every run batch and was **clear every time**, so no run collapsed
to 0 collected.

### What was deleted, and what proved it

Both copies of `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue` — in
`test_book_pdf_band.py` and `test_book_puzzle_frame.py`. **Survivor:**
`test_shared_fixture_controls.py::TestSharedControls_TheCopiesCannotComeBack::test_no_importer_reaches_for_a_fixture_at_run_time`,
which applies the **identical bound** over **every importer** of the shared home. Importer set
measured by `ast` = exactly **3**: band, puzzle_frame, **and `test_book_puzzle_page_vector.py`,
which never had a per-file copy** — so the survivor already covered **strictly more** than the two
copies did.

**The decisive methodological step was mutating one file at a time**, because with both planted the
survivor short-circuits on the first importer and names only band — which would have left the
second pair unproven:

| mutant | band's guard | frame's guard | survivor |
|---|---|---|---|
| none (negative control) | PASS | PASS | PASS |
| consumer planted in **band only** | FAIL | PASS | **FAIL**, naming band's line |
| consumer planted in **frame only** | PASS | FAIL | **FAIL**, naming frame's line |
| near-miss: the word in a docstring only | PASS | PASS | PASS |

**The near-miss is the instrument's negative control and it earns its place**: a grep instrument
would have fired **7 times per file** on that tree. The bound is an AST reading, not a text match.
The survivor is **not skip-gated** on this host — stated explicitly, because a skipped survivor
would have failed the bar.

Also removed as the deletion's own debris: band's now-unused `import ast` and `from pathlib import
Path`, measured to zero remaining references. Frame keeps both (`ast` used 10× elsewhere). **Each
deletion site carries a comment naming the survivor and the mutation**, so the rule is satisfied
**in the diff**, not only in a report.

### AC-5 satisfied by a pair that was NOT subsumed

The suite's two most expensive tests in its #1 file look like the same 36-row table walked twice.
Mutating the shared table, **both failed — on different assertions about different claims**: one
died on the *coverage* claim (a shape came back silent), the other on a **bookkeeping/consistency**
assertion and **never reached its coverage measurement at all**. So neither subsumes the other, and
both are kept. **A pair that looked redundant and was not is the card's own named success case.**

Three further groups were rejected without mutation, each with its reason — including one pair
where the second test **is the first's negative control** (*"the negative has teeth"*), so deleting
either would destroy an instrument proof.

### AC-2 / AC-3 / AC-4 as measurements against `4d164f62`, each with its instrument proved

- **AC-2**: fork point **9819** → HEAD **9817**. Removed set = exactly the two enumerated
  deletions; **added set empty**; equality in **both directions**. Positive control: the diff rises
  by the right amount. Negative control: HEAD vs a second independent collect yields 0/0, so no
  spurious ordering diff. **Both collects returned non-zero counts, so neither was a 0-collected
  run** — the trap that would have been catastrophic for this card specifically.
- **AC-3**: changed files = the two test modules; intersection with the protected set **EMPTY**
  (independently re-derived here from `git diff --name-only`). Protected node ids green, 66 passed,
  0 skipped. Its negative control is the good one: `test_book_puzzle_frame.py` mentions "A4" in
  prose and **a text search would have pulled it in** as the A4 golden test — membership is by
  path, so it correctly does not count.
- **AC-4**: an `ast` collector keying every `len(...) >= N` floor, including literals reached
  through a module-level constant, **with `lineno` deliberately excluded** because deleting a test
  shifts every later line and would make every site look changed. Fork point **286** sites, HEAD
  **286**, **0 fallen, 0 lost, 0 new**. **4 positive controls all rise and 5 negative controls all
  correctly do not** — this is the instrument that would otherwise have reported "no minimum fell"
  while blind.

### Cost: the honest answer is that there isn't one

BEFORE **13.47–14.75 s** (257 passed), AFTER **12.72–13.27 s** (255 passed), 3 reps each,
`__pycache__` swept, lock clear. **The ranges barely clear each other and no performance claim is
defensible**: the two deleted tests measured **0.01 s and 0.02 s**, so ~0.03 s is the honest
saving and the rest is run-to-run noise. **This confirms CARD-217's own recommendation that no
single test is worth deleting.** The value delivered is maintenance — one bound in one place
instead of three near-copies, and the third importer now covered where no per-file copy ever
covered it. **Zero skips in every run**, `-rs` used.

### THREE FINDINGS ABOUT THIS CARD — the second is structural and blocks a re-cut

1. **Both deletions are OUTSIDE the narrowed `Touches`**, and not one of the four declared paths
   was touched. The narrowing note sanctions exactly this (*"if a proven-subsumed pair turns up
   outside these paths, widen the field with the reason — do not delete outside the declared
   footprint silently"*), and the round flagged it rather than widening quietly. `Touches` corrected
   above.
2. **The card's step-1 cost gate and its 2026-10-24 fence contradict each other.** Step 1 requires
   a candidate be *"both expensive and suspected subsumed"*. The two tests the fence assigns to this
   card are **not expensive by any reading** — band is file #42 at 0.189 s/test, frame #76 at
   0.026 s/test, and the tests themselves cost 0.01 s and 0.02 s. **So the only deletions this card
   authorises fail its own cost gate, and the only cost-qualifying candidates are ones it must not
   delete.** The round took the later specific fence over the earlier general filter, which is the
   right reading, but **this must be resolved before the card is ever re-cut.** Also measured: of
   the four declared paths, `test_book_pdf.py` is **0.099 s/test with zero top-50 members** — inside
   CARD-217's "6057 tests under 0.1 s" class — and `helpers/book_corpus.py` has **no node ids at
   all**, so **only one of the four could ever host a cost-qualifying candidate.**
3. **The 20261023 rankings overstate that file's two most expensive tests by 5–10×** when they run
   as a small selection: **81.03 s → 16.34 s** and **67.08 s → 6.43 s**, same host, lock clear.
   Likely a per-text source-segmentation memo amortising differently, plus full-suite contention.
   **The ~255 s the digest attributes to five tests is not ~255 s of recoverable time**, and anyone
   re-cutting a curation card from those numbers must re-measure first. **That is a figure whose
   domain was never stated — this week's dominant family, in the profiling data this time.**

One deviation stated rather than chosen silently: the card's step 6 asks for a **solo re-profile**,
which means the full suite; the brief reserves that for the merge gate. The round profiled the
affected scope instead **and said so**.
