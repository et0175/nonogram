# CARD-218: Each book renders once per module, not once per test

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/218-render-once-per-module
**Worktree:** —
**Source:** owner request 2026-10-13 ("make cards for tests curation"); the render-duplication half of the dispatcher's cost analysis
**Idea:** —
**Wave:** 56
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-217, CARD-205, CARD-206 <!-- CARD-207, CARD-208 and CARD-209 REMOVED 2026-10-23 by owner decision. The dependency was SCHEDULING, not functional -- this card's own Architecture context says so ("it edits the same book test files that CARD-205..209 add tests to") -- i.e. it existed to avoid a rebase, not because anything here needs those three to have shipped. The owner chose to take the suite-cost work first, on the measurement that this card's subject (setup, paid once per test) is where the time actually is: 160 ms/test today against 131 ms/test on 2026-10-15. THE COST OF THE OVERRIDE, stated so it is not discovered later: CARD-207, CARD-208 and CARD-209 are drafted with acceptance criteria naming tests in the CURRENT shape, so each must be re-read at the decompose station before dispatch or it gates against a claim that moved -- the CARD-172 failure shape. Same for CARD-219. -->
**Touches:** tests/conftest.py, tests/helpers/book_corpus.py, tests/test_book_pdf_memory.py, tests/test_book_solved_answer_key.py, tests/test_book_puzzle_frame.py, tests/test_book_proof_pages.py, tests/test_book_pdf_band.py, tests/test_book_guide_page.py, tests/test_book_finalise_gutter.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The duplication this card removes is duplicated WORK, not duplicated
assertions.**
<!-- DO NOT ACT ON THE COUNTS IN THIS PARAGRAPH. Re-counted twice, 2026-10-23
(implementation round) and 2026-10-24 (fix pre-gate): the 110 is approximately
right for the idiom the tree actually uses (`_interior(` = 120 sites), and it
is IRRELEVANT either way -- the three files holding 77 of the tree's 151
render call sites cost 0.96 % of the suite between them. Size any successor on
measured duplication, never on a census. Both re-counts, and the card's real
4.90 s ceiling, are in the pre-gate section at the end of this card. -->
Across the test tree there are 110 `interior(...)` call sites, 68
`solved_puzzle_page`, 48 `interior_stream`, 34 `puzzle_pages`, 30 `export_book`,
30 `create_guide_page` and 25 `proof_pages`. Each `interior(...)` materialises
every page of a book as a bitmap (the production code's own docstrings put a
book page at ~25 MB), and many of those call sites sit in the *same file*,
rendering the *same* corpus book (`book_corpus.baseline_puzzles` and friends)
once per test function, so that each test can assert one thing about one page.

**Work from CARD-217's rankings, not from this list.** CARD-217 commits
`meta/profiling/suite-hotspots-<date>.md`: the 50 slowest tests, the 20 slowest
files with wall-clock shares, and the render-heavy files' total share. Convert
the top offenders in descending order of measured cost and stop when the
remaining candidates are not worth the churn — this card is explicitly allowed
to convert fewer files than its `Touches:` lists, and must say which it left
and why.

**How to convert a file.**

1. Identify the renders a file repeats with identical inputs. The giveaway is
   N test functions each calling `generator.interior(puzzles)` /
   `export_book(...)` on the same corpus and asserting on different pages.
2. Hoist that render into a **module-scoped** fixture (`@pytest.fixture(scope="module")`)
   in the file, or into `tests/conftest.py` when two or more files share the
   same inputs. Prefer module scope over session scope: session scope keeps a
   whole book's bitmaps alive for the rest of the run, and this project cares
   about peak memory (`test_book_pdf_memory.py` exists precisely because a page
   alive while the next is built was a real defect, CARD-145).
3. **A shared render must be read-only.** Pillow images are mutable and
   `Image.tobytes()`-digesting tests are order-sensitive. Any test that draws
   on, crops, or otherwise mutates a page must take a copy, or keep its own
   render — note which tests were kept unshared and why.
4. **Never share a generator or a stream.** `InteriorStream`'s generator is
   single-use and holds no page by design (CARD-145); a fixture that hands the
   same generator to two tests makes the second one silently see an exhausted
   walk. Share the *materialised* pages, or re-create the stream per test.
5. Where a file's tests only need the page PLAN rather than pixels, do not
   build a fixture — that is CARD-219's conversion, and the two cards must not
   fight over the same test. Leave it for CARD-219 and note it.

**Report the result as a measurement.** Re-run the profiling command from
CARD-217 (solo), and record the before/after wall-clock in the card and in
`meta/profiling/`. A conversion that does not move the number is churn and
should be reverted rather than argued for.

## Acceptance criteria

- **AC-1** (happy): *Given* a converted file, *when* its tests run, *then* the
  book is rendered once for the module, and every assertion that previously
  held still holds — same test names, same assertions. (test: the converted
  files' own existing tests, unchanged in name and intent)
- **AC-2** (happy, measured): *Given* the suite, *when* it is profiled solo
  before and after, *then* the card records both wall-clocks and the per-file
  deltas for every converted file, and the total is lower. (test:
  `TestSuiteProfile_ArtefactExistsAndIsComplete` for the new artefact; the
  delta is recorded, not asserted)
- **AC-3** (guard, no coverage loss): *Given* the converted files, *when* the
  suite runs, *then* the collected test count for those files is unchanged —
  no test was merged, parametrised away, skipped or deleted by this card.
  (test: `TestCuration_ConvertedFilesKeepTheirTestCount`)
- **AC-4** (edge, mutation): *Given* a shared rendered page, *when* one test
  mutates its copy, *then* the other tests in the module see the unmutated
  page. (test: `TestCuration_SharedRenderIsNotMutatedAcrossTests`)
- **AC-5** (edge, memory): *Given* the converted files, *when*
  `test_book_pdf_memory.py`'s peak-memory assertions run, *then* they still
  hold — the fixture must not keep more pages alive at once than the
  single-test path did. (test: `test_book_pdf_memory.py`'s existing peak
  assertions)
- **AC-6** (guard, stream semantics): *Given* any test that walks an
  `InteriorStream`, *when* it runs, *then* it walks a stream of its own — no
  fixture hands the same generator to two tests. (test:
  `TestCuration_NoSharedInteriorStream`)

## Guardrails

- G-1: No test is deleted, renamed, skipped or merged — this card changes WHERE
  a render happens, never WHAT is asserted (test: AC-3's count check).
- G-2: The baseline comparison keeps using the single loaded fixture
  (`book_corpus.BASELINE_FIXTURE`) and no fixture file is regenerated — every
  file in `tests/fixtures/` carries a "NEVER regenerate" warning.
- G-3: Property tests' corpus-minimum assertions are not lowered. The project's
  style puts a minimum case count inside the test so the corpus cannot silently
  shrink; speeding a test up by shrinking its corpus is the one optimisation
  this card may not make.
- G-4: `PropertyTest_Solver_NeverFalsePositiveUniqueness` (CON-005/EC-001),
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (ADR-0036/R1) and
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` (CON-019) are
  not touched by any curation card.
- G-5: Do not edit `src/**` — a test-infrastructure card that changes
  production code to be more testable has become a different card; raise it as
  a finding instead.
- G-6: Out of scope — converting pixel assertions into plan assertions
  (CARD-219), deleting redundant tests (CARD-220), and any parallel-execution
  or new-plugin work.

## Architecture context

- **FR:** — (test infrastructure)
- **ADR:** ADR-0036/R1 (the A4 golden — G-4), ADR-0006/R1 (no new dependency).
- **CON:** CON-005, CON-019 (both named in G-4 as untouchable).
- **Components:** none (test tree only).
- **Trace:** not applicable.

## Worktree notes

- Scheduling: this card edits the same book test files that CARD-205..209 add
  tests to, which is why it depends on all five. Starting it earlier guarantees
  a rebase conflict in `tests/test_book_*.py`.

## Re-pointed 2026-10-15 by CARD-217's measurement

CARD-217 profiled the suite solo and **neither hypothesis this card was cut on is where the time
is**. Measured shares of a 930.81 s run: the browser family `tests/test_puzzle_solver_*.py`
**39.78%**, the render-heavy set **21.23%**, `tests/property/*` **15.23%** — and over half the
property time is itself render-heavy, so the corpus hypothesis was largely a restatement of the
render one rather than a rival. A browser test costs 868 ms against everything else's 83 ms.

So this card is **no longer the biggest prize**, and `meta/profiling/suite-hotspots-20261015.md`
is now its source of truth rather than the counts in its own body. **CARD-235** takes the
browser family and is P1 ahead of it.

This card's own ground is real and still worth doing — the render-heavy set is 21.23%, the second
largest group — but size it against that figure, not against a hypothesis. The densest single
spot the profile found is **`tests/property/test_book_pdf_geometry.py`: 48.66 s in four tests**,
which is this card's and CARD-219's shared territory and the obvious first target.

## Worktree notes -- implementation (2026-10-23)

### Headline: the card's premise does not survive today's profile, and the measurement says so

**The card's own census of its subject is wrong by up to 50x against the tree it
would run on.** Re-counted in this worktree (branched from `c7cca514`):

| API the card counts | card's body says | measured 2026-10-23 |
|---|---|---|
| `interior(` | 110 call sites | **2** |
| `solved_puzzle_page` | 68 | 36 |
| `interior_stream` | 48 | 39 |
| `puzzle_pages` | 34 | 12 |
| `export_book` | 30 | 9 |
| `create_guide_page` | 30 | 27 |
| `proof_pages` | 25 | 29 |

The card was cut in wave 37; the tree moved under it. Its body already carries
the 2026-10-15 re-point, which told it to work from the rankings instead of
these counts -- that instruction was right, and the counts should be struck.

**The nine files' combined share, as the brief asked be stated before starting:
69.79 s of 1426.16 s attributed = 4.89 %, over 529 tests at 131.9 ms/test** --
*below* the suite's 160 ms/test mean. Two files carry 60 % of that
(`test_book_pdf_memory.py` 21.60 s, `test_book_guide_page.py` 20.25 s); the
other five together are 27.94 s. `tests/conftest.py` and
`tests/helpers/book_corpus.py` contribute no timings of their own.

**And the prize inside that 4.89 % is not what the card thinks.** The card's
mechanism recovers exactly one thing: render time spent on inputs already
rendered in the same module. That quantity was measured directly, by wrapping
every page-building entry point on `BookPDFGenerator`, digesting
`(method, book, args)` with construction timestamps erased, and summing the
time of every call whose digest had already been computed in that module:

| file | render time | **recoverable duplicate** | render calls | repeats |
|---|---|---|---|---|
| test_book_pdf_memory.py | 7.11 s | 1.53 s | 33 | 20 |
| test_book_finalise_gutter.py | 3.64 s | 1.02 s | 73 | 17 |
| test_book_pdf_band.py | 4.83 s | 0.92 s | 51 | 9 |
| test_book_solved_answer_key.py | 2.89 s | 0.86 s | 88 | 19 |
| test_book_puzzle_frame.py | 0.50 s | 0.40 s | 5 | 4 |
| test_book_guide_page.py | 1.79 s | 0.17 s | 16 | 1 |
| test_book_proof_pages.py | 0.11 s | 0.00 s | 1 | 0 |
| **total** | **20.87 s** | **4.90 s** | 267 | 70 |

**4.90 s is this card's entire ceiling -- 0.34 % of the suite** -- and three of
those seven rows are not even collectable:

* `test_book_pdf_memory.py`'s 1.53 s is the `export_interior` of the
  byte-identity and peak-memory classes. AC-5 and the card's own rule 2 forbid
  holding that book's pages module-wide; that file exists because a page alive
  while the next is built was a real defect (CARD-145). Declined.
* `test_book_finalise_gutter.py`'s 1.02 s is **`interior_stream` used for its
  page plan, not its pixels** -- the method's own docstring says "None of it
  draws a pixel". That is the card's rule 5 verbatim: CARD-219's conversion,
  not this one's. Declined and handed over. (It could not be shared anyway:
  every consumer goes through the function-scoped `panel` fixture, which
  depends on `monkeypatch`.)
* `test_book_guide_page.py`'s 0.17 s is a **false duplicate**: `new_export` and
  `old_export` render the same book, but `old_export` does it under a
  `MonkeyPatch` of `create_guide_page`. The digest cannot see a monkeypatch.
  Every duplicate group was read before being believed; this is the one the
  instrument got wrong, and it is recorded so the next card does not trust the
  instrument further than it can be read.

That leaves **2.35 s genuinely in scope**, and the honest conversion is the
narrow one taken below.

### Where the money actually is in these files: analysis, not rendering

`test_book_guide_page.py` is the clearest case, and it matters because it is the
card's second-largest file. The render is **already hoisted** -- the file has had
module-scoped `new_export` / `old_export` / `new_pages` / `old_pages` fixtures
and class-scoped `generator` / `spec` / `page_mask` fixtures since before this
card. cProfile over its two most expensive classes (10 tests, 10.79 s):

* `occurrences()` -- the numpy template search in the test bodies -- **9.69 s
  cumulative over 9 calls (1.08 s each)**;
* `export_of` / `export_interior` -- the render -- **0.670 s over 3 calls**.

The render is 6 % of that file's cost. Hoisting it recovers nothing, because it
is already hoisted. 82 % of the file sits in five tests doing full-page template
matching. **That is a real, large, un-carded saving (cache the probe templates
and the page masks, not the render) and it is nobody's card today.**

### What was implemented, and why only this

Two conversions, taken in descending order of measured recoverable cost among
the groups that are shareable, read-only, and not another card's:

**1. `tests/test_book_puzzle_frame.py` -- 0.40 s, the largest single
identical-input duplicate anywhere in the nine files.** Four classes each had
`@pytest.fixture(scope="class") def pages(cls): return _book_pages()`, and a
fifth test called `_book_pages()` inline -- so the same three puzzles were laid
out and drawn **five times**. The four class fixtures are deleted and replaced
by one module-scoped `pages` fixture; the inline caller takes it. This is the
card's mechanism exactly, and note what it tells us: the mechanism had already
been applied at *class* scope, and the card's remaining delta in this file was
class -> module. Nothing here was function-scoped to begin with.

**2. `tests/test_book_pdf_band.py` -- 0.68 s in two groups.**
   * `TestBookPdf_EveryFifthGridLineWider._page()`, a `@staticmethod` that five
     tests in that class called (0.389 s), becomes a **class**-scoped `page`
     fixture. Class and not module because this page is read by that class
     alone: narrower scope, same saving, bitmap released sooner -- the card's
     rule 2 reasoning carried one step further than its wording.
   * `TestBookPdf_PuzzlePageCarriesNoPictureTitle` and
     `TestBookPdf_AnswerKeyCarriesPictureTitle` are two readings of one printed
     book, and four tests across them drew it again each time (0.286 s). One
     **module**-scoped `snowflake_interior` fixture now serves all four -- module
     scope because the duplication crosses a class boundary. The fixture asserts
     both classes' `NAME` equals the book it draws, so a rename goes red at the
     fixture rather than leaving one class silently measuring the other's book.

Left unconverted, each with its reason: `test_book_pdf_memory.py` (AC-5),
`test_book_finalise_gutter.py` (plan not pixels -> CARD-219),
`test_book_solved_answer_key.py` (0.86 s in four small class-local groups;
every one of its byte-identity classes compares `tobytes()` against a page
built beside it, so it is convertible, but at 0.86 s for four separate edits in
a 2019-line file it is below the churn line this card is told to draw),
`test_book_guide_page.py` (already converted; residual is analysis),
`test_book_proof_pages.py` (0.00 s duplicate measured), `tests/conftest.py` and
`tests/helpers/book_corpus.py` (nothing to hoist: no duplication crosses files).

### Prediction vs measurement

**Predicted before the edits: 1.09 s** (0.400 + 0.389 + 0.286, from the table
above). **Measured: 0.99 s.** Same command, same machine, three runs each,
taken back to back:

| | run 1 | run 2 | run 3 | median | load at start / end |
|---|---|---|---|---|---|
| before | 8.79 s | 8.67 s | 8.84 s | **8.79 s** | 2.85 3.97 4.52 / 3.22 3.95 4.49 |
| after | 7.87 s | 7.80 s | 7.74 s | **7.80 s** | 3.98 4.02 4.36 / 3.40 3.88 4.30 |

`-0.99 s, -11.3 %` on the two converted files, **while adding 5 tests**. The
0.10 s shortfall against the prediction is those 5 tests' own cost plus the
`tobytes()` digesting the controls do. Command:
`pytest tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py`
(no `-q`: `pyproject.toml:89` already sets it and a second one suppresses the
count line; paths explicit, never `-k`; file list built as a zsh array and its
length printed, because an unquoted joined string reaches pytest as one path).

**In suite terms: 0.99 s of 1433.47 s = 0.069 %.** Which is the finding. The
card may not be worth more rounds than this one.

### Collected-count delta: +5, every one deliberate

`test_book_puzzle_frame.py` 95 -> 97, `test_book_pdf_band.py` 34 -> 37; nothing
renamed, merged, parametrised away, skipped or deleted (G-1, AC-3). The five are
the controls AC-4 and AC-6 ask for, and they exist because **a claim needs a
control that can fail**: the converted files' own 129 tests pass at *any*
fixture scope, so without these there is nothing in the diff that reddens when
the conversion is undone.

* `TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn`
* `TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_one_render_served_the_whole_module`
* `TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_the_shared_pages_are_what_the_fixture_drew`
* `TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module`
* `TestBookPdf_EveryFifthGridLineWider::test_one_render_served_the_whole_class`

### Mutation table -- one row per claimed mechanism (ADR-0039/R1)

Every mutant deletes the mechanism, is line-count preserving, and the file's
sha256 was re-verified after restore. The cells are the verdict, not the exit
code.

| # | mechanism deleted | mutant | failure cells |
|---|---|---|---|
| M1 | `pages` is module-scoped (puzzle_frame) | `scope="module"` -> `"function"` | 2 failed / 95 passed: `TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn` + `::test_one_render_served_the_whole_module` |
| M2 | the shared pages are read-only (puzzle_frame) | a consumer draws a 9 px line on `pages[0]` | 1 failed / 96 passed: `::test_the_shared_pages_are_handed_out_as_they_were_drawn` |
| M3 | `snowflake_interior` is module-scoped | `scope="module"` -> `"function"` | 1 failed / 36 passed: `TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module` |
| M4 | the shared snowflake pages are read-only | a consumer draws on `snowflake_interior[0]` | 1 failed / 36 passed: `::test_the_shared_pages_are_what_the_fixture_drew` |
| M5 | `page` is class-scoped (pdf_band) | `scope="class"` -> `"function"` | 1 failed / 36 passed: `TestBookPdf_EveryFifthGridLineWider::test_one_render_served_the_whole_class` |
| M6 | the fixture asserts both classes name one picture | `TestBookPdf_AnswerKeyCarriesPictureTitle.NAME` -> `"Iguanodon"` | 31 passed / **6 errors**, all four sharing tests plus both controls |

sha256 after restore: `tests/test_book_puzzle_frame.py`
`4e1512828e03fa5631391965d138f4b1d959655c47cac15e03936e33f4c53e76`,
`tests/test_book_pdf_band.py`
`959bdff36b91b13ab604860e27c87ad53097c620210c07bde2b65f9b505d289c` -- both
match the pre-mutation values.

### Census guards -- every one enumerated, none assumed

Run explicitly (not reachable from an impact-scoped selection):
`pytest tests/test_browser_fixture_scope.py tests/test_suite_profile.py tests/test_guard_integrity.py tests/test_impact_set.py tests/test_fixture_integrity.py`
-> **2 failed, 641 passed**, and both failures are **pre-existing on main**
(see below).

* **`tests/test_browser_fixture_scope.py` -- PASS.** My diff adds, removes and
  renames no browser node id and changes no browser fixture's scope, so the
  CARD-217 artefact and the `ADDED_SINCE_BEFORE` allowlist are untouched. Run
  anyway, because that guard is why CARD-271 went red at its merge gate.
* **`tests/test_suite_profile.py` -- the `RENDER_HEAVY_SNAPSHOT` check PASSES.**
  Verified directly as well: `regrep_render_set(tests/) == RENDER_HEAVY_SNAPSHOT`,
  added `[]`, gone `[]`. This was a live risk and it constrained the diff: the
  set is defined by *grepping* `interior\(|solved_puzzle_page|interior_stream|render_pages|puzzle_pages|export_book|create_guide_page|proof_pages`
  over every `tests/**/*.py`, the snapshot lives in `meta/profiling/rank_durations.py`,
  and `meta/` is never committed from a worktree -- so **no new test file could
  be added that names any of those eight, and no conversion could remove a
  file's last occurrence of one.** `test_book_pdf_band.py` keeps 21 of its 25
  matches; `test_book_puzzle_frame.py` has 0 matches before and after (see the
  next note).
* **`tests/test_guard_integrity.py` -- PASS.** Its silence census covers
  `tests/` and `meta/profiling/`; this diff adds no `skip`, `skipif` or
  conditional silence of any kind.
* **`tests/test_impact_set.py` -- PASS.** Its subject is every
  `tests/**/*.py`, which includes both converted files.
* **`tests/test_fixture_integrity.py` -- PASS.** Nothing under
  `tests/fixtures/` was read, written or regenerated (G-2). The
  `book_baseline_card200/203/204/205.json` files that
  `TestBookPdfMemory_NonDrawingPagesAreByteIdentical` loads at runtime are
  untouched -- `test_book_pdf_memory.py` is not in this diff at all.
* Also run: the nine `Touches:` files plus `test_book_toc.py` and
  `test_book_pdf_ink_mode.py` -> **625 passed, 1 skipped**. The one skip is
  attributed: `test_book_pdf_memory.py:1296`, `setrlimit(RLIMIT_AS)` cannot
  bound a process on this kernel. Pre-existing, self-documenting in its own
  skip message, and one of the 27 skips the committed profile reports.
* Nothing imports either converted module (the five cross-references found are
  prose in docstrings), so the reverse-dependency set is empty.

### Found wrong, with the measurement

1. **`main` is red right now, at `c7cca514`, and it is not this card.** Two
   tests fail in a pristine main checkout with none of my changes:
   `TestSuiteProfile_ArtefactExistsAndIsComplete::test_hotspots_headline_figures_are_the_scripts_own_output[suite-durations-20261023.txt]`
   and `TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog::test_the_outcomes_are_identical_with_and_without_the_log`
   (the second cascades from the first -- it asserts every outcome in the module
   is PASSED). Cause, measured: that guard requires each cost family's
   `<secs> s` / `<share> %` pair to appear on a **markdown table row** (a line
   starting with `|`). `meta/profiling/suite-hotspots-20261015.md` has **22**
   such rows; `meta/profiling/suite-hotspots-20261023.md` has **0** -- it states
   the families as a fixed-width block in the digest's own format
   (`353.06s  24.76%`, no space before the unit). Its sibling check,
   `test_hotspots_embeds_the_deciding_table_verbatim`, passes on exactly that
   block, so the new document satisfies one half of the pair and not the other.
   **This blocks the merge gate for whichever card reaches it first**, and it is
   AC-2's own named guard. Not fixed here: it is `meta/`, never committed from a
   worktree, and not this card's subject.
2. **`tests/test_book_puzzle_frame.py` is not in the render-heavy frozen set**
   (0 matches for the defining grep) -- yet it is one of this card's nine files
   and it held the single largest genuinely-shareable render duplicate in all of
   them. The card sizes itself against "the render-heavy set is 38.88 %", a set
   that does not contain the file where its mechanism works best. Size the next
   curation card on measured duplication, not on set membership.
3. **The dependency-override comment on this card's `Depends on:` line names the
   wrong half of the suite.** It justifies running now on "this card's subject
   (setup, paid once per test) is where the time actually is". Today's profile
   splits attributed time **setup 6.79 % / call 91.79 % / teardown 1.42 %**.
   Setup is 96.78 s of 1426.16 s. The override's *conclusion* survives -- there
   was no functional dependency -- but its stated reason is false, and this
   card's mechanism in fact moves work **out of `call` and into `setup`**, which
   is the opposite direction. (It also mis-states 160 ms/test as belonging to
   setup; 160 ms/test is the whole-suite per-test figure.)
4. **AC-2's "the total is lower" cannot be shown by this card at suite scale.**
   0.99 s on 1433.47 s is 0.069 %, against a best-case solo-run reproducibility
   of 0.20 s between two runs of the same commit. The per-file delta
   (-11.3 % on the two converted files) is the measurement that is actually
   above the noise, and it is what is recorded.
5. **AC-3 and AC-4 are in tension as written.** AC-3 wants the converted files'
   collected count unchanged; AC-4 wants a control proving a mutated copy does
   not leak, which can only live where the shared fixture does. Read AC-3 as its
   own words say -- "no test was merged, parametrised away, skipped or deleted"
   -- and the +5 controls satisfy both. Worth fixing in CARD-219's and
   CARD-220's copies before they are dispatched, since they share the wording.

### For the sibling cards

* **`tests/test_book_export_interior_cover.py` (24.14 % of the suite, 344.29 s)
  would NOT be fixed by this card's mechanism, measured.** Not touched -- the
  measurement is read-only. Instrumented the same way: total render time in that
  file is **9.25 s**, of which **2.52 s is recoverable duplicate** -- 0.7 % of
  the file's 344.29 s. 335 s of it is not rendering at all. Its four most
  expensive tests (81.03 s, 67.08 s, 44.69 s, 41.13 s) are
  `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage`'s
  door/arm guard-matrix tests. Whatever that card's fix shape is, it is not
  "render once per module".
* **CARD-219 inherits `test_book_finalise_gutter.py`** (1.02 s of repeated
  `interior_stream` *plans*, 73 calls, 17 repeats) and, more valuably, the
  template-matching cost in `test_book_guide_page.py` (9.69 s of `occurrences()`
  in 10 tests) -- which is plan-vs-pixel territory and ~10x this card's whole
  ceiling.
* One incidental: the 2026-10-23 profile's own `TestBookPdfMemory_TheInstrumentWrapsEveryPageFactory::test_every_page_returning_method_is_in_page_factories`
  fails under any wrapper applied to `BookPDFGenerator`'s page factories. That
  is the guard working, not a defect; noted so the next person who instruments
  the generator is not surprised by it.

## [FIX PRE-GATE 2026-10-24, orchestrator] PASSED — every claim re-derived, two record figures corrected, and the mechanism re-measured as an INTEGER

Every number below was taken in this worktree by the orchestrator, not read off
the round's notes. Tree: `4ae0d825`, both files at the sha256 the round
recorded (`4e151282…` / `959bdff3…`, verified before and after every mutant).

### The diff, independently characterised

`git diff --numstat c7cca514..HEAD` is two files, `+163/−17` and `+98/−22`.
No `src/`, no `tests/fixtures/` (G-2, G-3), and **zero** added lines matching
`skip|xfail|pytest.mark` — so nothing in this diff can go green by going
silent.

### AC-3 / G-1 — the collected set, by set difference and not by count

| | base `c7cca514` | HEAD | delta |
|---|---|---|---|
| `test_book_puzzle_frame.py` | 95 | 97 | +2 |
| `test_book_pdf_band.py` | 34 | 37 | +3 |
| both | **129** | **134** | **+5** |

`comm` over the sorted node-id sets: **removed = 0**, added = exactly the five
controls the round names, no third set. Nothing was renamed, merged,
parametrised away, skipped or deleted. (Collected with `-o addopts=''`: this
repo's `pyproject.toml:89` already supplies `-q`, and a second one takes
`--collect-only -q` silent — my own first attempt returned 0 node ids to this
trap.)

### The conversion is byte-neutral — the one thing the round did not assert

This is the only way the mechanism can go wrong *quietly*: four tests that used
to render their own book now read a shared one, so if the shared book is not
the book they were rendering, they measure something else and still pass.
Probed directly (probe deleted after):

* `_puzzle()` — the fixture's book — is dict-**equal** to `_puzzle(name=NAME)`
  for both `TestBookPdf_PuzzlePageCarriesNoPictureTitle` and
  `TestBookPdf_AnswerKeyCarriesPictureTitle`, so the fixture's `NAME`
  assertion is not the only thing holding them together; the whole payload
  matches.
* the shared interior's **8 pages are byte-identical** to the interior each
  class builds for itself (sha256 per page, both classes).
* both render helpers are deterministic across two calls —
  `band._interior` and `frame._book_pages`.

### The mechanism, re-measured as an integer instead of a stopwatch

The round's only positive claim was a wall-clock delta of ~1 s on a box whose
own solo-run reproducibility is 0.20 s. But the mechanism it claims is a
**count**: how many times each module lays out and draws its book. Counted
with a 40-line pytest plugin that wraps the two render entry points (plugin
kept out of `tests/`, deliberately — a file in `tests/` naming `interior(`
would have joined `rank_durations.py`'s frozen render set and reddened
`test_suite_profile.py`):

| render entry point | base | HEAD | removed |
|---|---|---|---|
| `test_book_pdf_band._interior` | 40 calls, 4.451 s | 33 calls, 3.534 s | **7 calls, 0.917 s** |
| `test_book_puzzle_frame._book_pages` | 5 calls, 0.811 s | 1 call, 0.176 s | **4 calls, 0.635 s** |
| total | 45, 5.262 s | 34, 3.710 s | **11 calls, 1.552 s** |

**11 renders removed, 24 % of these two files' renders**, and the figure is
noise-free. It is corroborated by a second instrument that is also a pure call
counter and immune to load: the `datetime.utcnow()` `DeprecationWarning` these
renders emit falls **274 → 252**, i.e. 11 fewer document builds — the same
integer, reached two ways.

### The wall clock — the round's figure is at the optimistic edge

The round reported `8.79 s → 7.80 s`, **−0.99 s / −11.3 %**, from three runs
of each arm taken in two blocks. Re-measured as three **interleaved pairs**
(base, head, base, head, base, head — which controls for drift within the
measurement rather than between two blocks of it), plus three more of each
unpaired:

| | runs (pytest wall) | min | median |
|---|---|---|---|
| base | 9.30 8.53 8.54 9.15 8.89 8.91 | 8.53 | **8.90** |
| HEAD | 7.96 8.82 7.94 8.04 8.27 8.57 | 7.94 | **8.16** |

Paired deltas: **−1.11, −0.62, −0.34 s**. Median delta **−0.74 s (−8.3 %)**;
on user time, −0.79 s. The five new controls cost **0.1–0.15 s** of that
(HEAD with them deselected: 8.44 / 8.01 / 7.84 s), so they are not what eats
the saving — run-to-run variance is, at load averages 4.3–5.2 throughout.

**So: −0.99 s is inside the range I measure, and its two decimal places are
not supportable on this box.** That is the round's own AC-2 argument — "0.99 s
on 1433 s is below a 0.20 s reproducibility floor" — turned on its own
per-file figure. Record **11 renders and ~1.55 s of rendering removed, for a
wall-clock gain of 0.6–1.1 s**, and let the integer carry the claim.

### Six mutants — mine, not the round's, and one of them is the vacuity check

Every mutant deletes a mechanism, is line-count preserving (3120 → 3120 and
1596 → 1596, printed each time), and both files' sha256 were re-verified after
each restore. The cells are the verdict, never the exit code.

| # | mechanism deleted | failure cells |
|---|---|---|
| P1 | `pages` module → function | 2 failed / 95 passed — `TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn` + `::test_one_render_served_the_whole_module` |
| **P2** | **the digest is never taken** (`_SHARED_DIGEST.extend` → `pass`) | **2 failed / 95 passed — the same two cells** |
| P3 | `snowflake_interior` module → **class** | 1 failed / 36 passed — `TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module` |
| P4 | fifth-rule `page` class → function | 1 failed / 36 passed — `EveryFifthGridLineWider::test_one_render_served_the_whole_class` |
| P5 | the two classes stop naming one picture (`AnswerKey.NAME = "Iguanodon"`) | 31 passed / **6 errors** — both sharing classes' four tests and both controls |
| P6 | a consumer **draws** on the shared page | 2 failed / 35 passed — the consumer itself **and** `::test_the_shared_pages_are_what_the_fixture_drew` |

**P2 is the one that mattered to run**, and it is the check the PG-3 family on
CARD-271 was invented for: `test_the_shared_pages_are_handed_out_as_they_were_drawn`
compares the pages against a digest, so if the digest were never populated the
`zip` would be empty and the control would pass on nothing. It does not — the
`len(_SHARED_DIGEST) == INTERIOR_PAGES` precondition reds first, with its own
diagnosis. The control cannot pass vacuously.

**P3 checks a claim the round asserted and did not test.** Both fixtures'
docstrings say narrowing the scope *or* widening it reds the control; the round
mutated only toward `function`. Module → **class** also reds. The claim holds
in both directions.

### Census guards — all green, and the round's two reds were mine

The round reported `2 failed, 641 passed` and attributed both to main being
red at `c7cca514`. Correct, and it was my own `c7cca514` that broke it; fixed
on main in `5be7508e`. With main's repaired
`meta/profiling/suite-hotspots-20261023.md` in this worktree:

`pytest tests/test_browser_fixture_scope.py tests/test_suite_profile.py tests/test_guard_integrity.py tests/test_impact_set.py tests/test_fixture_integrity.py`
→ **643 passed, 0 failed, 0 skipped**, 86.6 s.

So the round's diagnosis is confirmed from both ends: red before the fix, green
after, same 643-test set. The repaired document sits in the worktree
**uncommitted** — `meta/` is never committed from a worktree — and main comes
in properly at the merge gate.

Territory re-run: the seven runnable `Touches:` files plus `test_book_toc.py`
and `test_book_pdf_ink_mode.py` → **625 passed, 1 skipped**, the skip being
`test_book_pdf_memory.py:1296` (`setrlimit(RLIMIT_AS)` refused by this kernel,
self-documenting, one of the committed profile's 27).

### The premise re-derivation — exact, to the hundredth

Recomputed from `meta/profiling/suite-durations-20261023.txt` by my own parse
of its `<secs>s <phase> <nodeid>` records, not from the round's notes:

* attributed total **1426.16 s**; **setup 6.79 % / call 91.79 % / teardown 1.42 %**;
* the nine `Touches:` files: **69.79 s, 529 tests, 4.89 %, 131.9 ms/test**.

Both reproduce the round's figures exactly. The premise-killing measurement is
sound, and so is finding 3 against the dependency-override comment: setup is
96.78 s of 1426.16 s, and this card's mechanism moves work *out* of `call` and
*into* `setup`, which is the opposite direction from the one the override's
stated reason assumes.

### CORRECTION — the headline "wrong by up to 50×" is wrong on the row it headlines

The round's census table reproduces **exactly** on four of its rows
(`solved_puzzle_page` 36, `interior_stream` 39, `puzzle_pages` 12,
`export_book` 9) and within one on a fifth. Its instrument was right. But the
row it put the headline on is the one it got wrong:

| | card body | round | re-counted 2026-10-24 |
|---|---|---|---|
| bare `interior(` | — | **2** | 2 |
| `_interior(` — **the tree's actual idiom** | — | not counted | **120** |
| what the card calls "`interior(...)` call sites" | **110** | "2, wrong by 50×" | **122** |

`tests/` reaches a book's bitmaps through a per-file `_interior(...)` wrapper,
not through `generator.interior(...)`, so the card's 110 was approximately
**right** for the thing its sentence describes ("each `interior(...)`
materialises every page of a book as a bitmap"). The round counted the public
method and declared the card's census dead on it.

### …and the conclusion survives anyway, now for a better reason

Re-pointing the corrected census at cost kills it from the other side. The
three files holding the most `_interior(` call sites — **none of them in this
card's `Touches:`** — are:

| file | `_interior(` sites | measured cost | ms/test |
|---|---|---|---|
| `tests/test_book_pdf.py` | 30 | 4.84 s | 98.8 |
| `tests/test_book_pdf_two_up.py` | 24 | 4.15 s | 92.2 |
| `tests/test_book_cell_size.py` | 23 | 4.74 s | 110.2 |
| the three | **77 of 151** | **13.73 s = 0.96 %** | 100.2 |

Half the tree's render call sites cost under one percent of the suite. **The
census is a bad proxy for cost in BOTH directions** — too low as the round
counted it, irrelevant as the card counted it. The card's premise is dead
because its measured ceiling is **4.90 s**, which the round established and
this pre-gate reproduced; it is not dead because anybody miscounted. Striking
the counts from the card body is still right, and now for a reason that
survives being checked.

### Verdict: PASSED

Nothing in the diff is wrong, nothing is unproven, and no fix round is owed.
The two corrections are to figures — one of the round's and one of the card's —
and both are recorded above rather than quietly amended, because a review
cycle would otherwise inherit them. Next station: review cycle 1.
## Review notes -- cycle 1

**Verdict: NOT CERTIFIED. Score 6.0 / 10 against `min_score: 8`.**
Report: `meta/review/20261024T223738Z-CARD-218-cycle1.yml` (worktree; `meta/` is
never committed from here, so the merge station must sync it).
Arithmetic: `10 - 2 (F-001, critical) - 1 (F-002) - 1 (F-003) = 6.0`. The four
`low` findings carry no deduction.

### The headline: nobody measured the card's own stated risk, and it is real

Rule 2 prefers module scope over session scope *because* this project cares
about peak memory. Three rounds have now reasoned about that rule and none of
them put a number on it. Measured, base `c7cca514` vs HEAD `4ae0d825`, in two
detached scratch worktrees so this tree was never touched:

| | peak RSS base | peak RSS HEAD | delta |
|---|---|---|---|
| `tests/test_book_puzzle_frame.py` | 657.5 MB | 958.1 MB | **+300.6 MB (+45.7 %)** |
| `tests/test_book_pdf_band.py` | 1215.9 MB | 1569.0 MB | **+353.2 MB (+29.0 %)** |
| both, one run | 1327 / 1356 MB | 1781 / 1719 MB | **+~400 MB (+30 %)** |

And read straight out of `sys.modules` at `pytest_sessionfinish`, **after both
module fixtures have been finalised** (probe plugin kept outside `tests/`, so it
could not join `rank_durations.py`'s frozen render set):

```
tests.test_book_puzzle_frame._SHARED_DIGEST:       10 entries, 252,450,000 B (240.8 MB)
tests.test_book_pdf_band._SHARED_SNOWFLAKE_DIGEST:  8 entries, 201,960,000 B (192.6 MB)
tests.test_book_pdf_band._FIFTH_RULE_RENDERS:       1 entry, 0 B
```

**433.4 MB alive for the rest of the session**, because pytest keeps test
modules in `sys.modules`. In this project's own unit — `test_book_pdf_memory.py`
line 38 records 25,245,000 B per 2550x3300 page, exactly the per-entry size
above — that is **18.0 page bitmaps retained permanently**, in a repo whose
memory module accepts a peak of **2.00** page bitmaps and exists because a page
alive while the next is built was a real defect (CARD-145).

So the conversion chose module scope to avoid holding bitmaps alive for the rest
of the run, and then held an equal volume of the same bytes alive for the rest of
the run by another route. Both fixture docstrings say *"Module, not session (the
card's rule 2): a session fixture would hold this book's page bitmaps alive for
the rest of the run"* — the fixture does not; the module-level list the fixture
populates does.

**AC-5 is substantively failed and has no live control.** Its named verifier is
`test_book_pdf_memory.py`'s peak assertions, and that file says at line 84 that
its measured peak *"is not the process's peak, and this module does not claim it
is"* — it instruments its own `_live` dict (line 420). It cannot fail on a
retention in two other modules. Nothing else guards process memory either:
`grep RLIMIT_AS|peak_rss|max_rss|tracemalloc` over `tests/` hits that one file,
whose `RLIMIT_AS` test is the skip this kernel refuses. The regression is
invisible to every guard on the board.

**The fix is one line per file and is strictly better.** The controls compare
bytes for equality, so a `hashlib.sha256(page.tobytes()).digest()` is an
equivalent witness at 32 B instead of 25 MB: 18 x 32 B = 576 B against
454,410,000 B. `hashlib` is stdlib (ADR-0006/R1 untouched), every control keeps
its discriminating power, and the docstrings' "module, not session" claim becomes
true of everything the fixture leaves behind rather than only of its return value.

### The controls are sound under the gate's selection and vacuous under three others

4 x 10 matrix: three line-count-preserving scope mutants plus the intact tree,
each under ten selections, driven by a script, both files' sha256 re-verified
after every restore (`4e151282…` / `959bdff3…`). Cells, never exit codes.

| mutant | whole-file | control-class | control-node |
|---|---|---|---|
| `pages` module -> function | 2 failed **KILL** | 1 failed **KILL** | 1 passed **VACUOUS** |
| `snowflake_interior` module -> class | 1 failed **KILL** | 2 passed **VACUOUS** | 1 passed **VACUOUS** |
| fifth-rule `page` class -> function | 1 failed **KILL** | 1 failed **KILL** | 1 passed **VACUOUS** |
| intact | green | green | green |

Plus, with `-k one_render` on `test_book_pdf_band.py` (2 selected, 35
deselected): the class-scope mutant and the function-scope mutant **both pass**.

**No spurious reds anywhere** — the intact tree is green under all ten
selections, including the two files in reverse order and the `-k` subset. That is
why this is Important and not Critical. But each control's docstring makes a
universal claim it does not hold (*"Put the scope back to function and there are
five, and this goes red"*), and under `-k one_render` — the most natural way a
human re-checks a control called `test_one_render_served_the_whole_module` — the
answer is a silent green where ADR-0039/R2 wants default-deny. The mechanism:
all three assert an equality on a counter only the *selected* tests increment, so
narrowing the selection narrows the denominator with it. Count fixture
executions **and** consumer takings, held to a derived consumer count, and a
narrowed selection reds with a message saying why.

Related: the pre-gate's P3 claim that "the claim holds in both directions" is
true only of the whole-file selection — row 2 above shows module -> class
surviving a single-class run.

### AC-vs-body: adjudicated, not inherited

**AC-3 / AC-4 are NOT in tension — the round's framing is wrong.** AC-3's
headline ("the collected test count for those files is unchanged") and its gloss
("no test was merged, parametrised away, skipped or deleted") say different
things: the first is a count equality, the second a removals check. The gloss is
operative — AC-3's own label is *no coverage loss*, and adding tests cannot lose
coverage. So the round reached the right answer, but the defect is AC-3's
**wording**, not a conflict with AC-4. For CARD-219/220, replace the headline
clause with what both the round and the pre-gate actually measured: *"no node id
collected before the change is absent after it (set difference, removals = 0);
additions are permitted and must be named."* Unambiguous, stronger, and already
the practice.

**AC-2: the suite-total clause is unshowable — sustained, for a corrected
reason. The artefact clause is showable and was not done.**
The round's argument rests on "a best-case solo-run reproducibility of 0.20 s",
which has no provenance (`grep reproducib|0.20 s` over `meta/profiling/` and
CARD-217 returns nothing) and is self-refuting as used: if a 1433 s suite really
reproduced to +/-0.20 s, a 0.99 s gain would be 5x the floor and AC-2 *would* be
showable. The pre-gate's own six base runs settle it the other way — 8.53-9.30 s
on an 8.90 s selection, an 8.7 % spread, which at suite scale is tens of seconds.
A ~1.55 s effect is two orders of magnitude under it. Same correction the round
made to the Depends-on comment and the pre-gate made to the census headline.
Separately, the card body and AC-2 both require the result recorded *"in the card
and in `meta/profiling/`"*, and no `card-218-*` artefact exists there — while
`card-236-admin-local-subprocess-cost.md`, `card-241-render-check-cost.md` and
`card-243-two-threshold-cost.md` show the accepted per-card form costs almost
nothing. AC-2's named test (`TestSuiteProfile_ArtefactExistsAndIsComplete`)
guards the *hotspots* document, so it cannot verify AC-2's clause either.

**And a third problem neither the round nor the pre-gate caught: three of the six
ACs name verifiers that exist nowhere in the tree.**
`TestCuration_ConvertedFilesKeepTheirTestCount` (AC-3),
`TestCuration_SharedRenderIsNotMutatedAcrossTests` (AC-4) and
`TestCuration_NoSharedInteriorStream` (AC-6) return no file from a grep over
every `*.py` under `tests/`. They are `check_ref_missing` in the ADR-0039 sense:
they look mechanically checked and are not. AC-3 is held by a one-off
measurement with no standing guard; AC-4 is genuinely tested, under a different
name, with F-002's caveat; **AC-6 has no control of any kind** and is satisfied
by inspection only (both fixtures return `list[Image.Image]` — true, verified,
and exactly what the AC said a test would do). The notes say *"the five are the
controls AC-4 and AC-6 ask for"*, which renames one verifier silently and claims
another among five tests none of which touches a stream. Decide this once before
CARD-219/220 are dispatched, or three cards will invent three names.

### What I agree with

* **Close CARD-218 after this lands.** The 4.90 s ceiling is single-instrument
  and was *not* independently re-derived (the pre-gate reproduced the premise
  figures — 1426.16 s, 69.79 s, 4.89 % — not the duplicate table), and the one
  subset that was cross-checked suggests it reads ~18 % low (it predicted 1.32 s
  for the two converted files where the call counter measured 1.552 s removed).
  None of that matters: even at 3x, the card's whole subject is 1.03 % of the
  suite. The conclusion rests on the figure's order of magnitude, not its
  hundredths, and it is safe.
* **All three declined files are declined for stated and correct reasons**, each
  verified independently: `test_book_pdf_memory.py` — AC-5 forbids it (and
  F-001 is the proof that the concern was the right one);
  `test_book_finalise_gutter.py` — `src/nonogram/admin/book_pdf_generator.py:6603`
  does say *"None of it draws a pixel"*, so rule 5 hands it to CARD-219, and its
  `panel` fixture (line 378) takes `monkeypatch` and so cannot be widened
  anyway; `test_book_guide_page.py` — four module-scoped fixtures already exist
  at lines 253-272, so "already converted" is true.
* **Nothing outside the two files reads their module-level state.** Verified
  independently: all three accumulator names grep only inside their own files;
  the outside references to either module are prose in docstrings plus the module
  *path* as a string literal in `meta/profiling/rank_durations.py:113`.
* **Record the integer, not the stopwatch** — 11 renders / ~1.55 s removed, with
  the `utcnow()`-warning count as the second instrument. The round's
  −0.99 s / −11.3 % should not be the card's headline.

### Gate, scope gate, and the pre-gate's misses

`scripts/impact_set.py tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py`
re-derived in this worktree -> the same 24 files, run as derived, plus
`tests/test_browser_fixture_scope.py` which the derivation does not select:
**2916 collected, 2905 passed, 0 failed, 0 errors, 11 skipped, exit 0, 526.21 s.**
`test_browser_fixture_scope.py` — 17 tests, all green, confirmed not hoped.

All 11 skips attributed by node id (enumerated with `--collect-only -m
db_required`, not inferred from the count): **nine** in
`tests/test_admin_binding.py::TestUndefinedTableReport_NamesWhatTheFailingConnectionWasTalkingTo`
(`test_the_report_carries_the_four_groups`,
`…_names_the_database_the_failing_connection_was_on`,
`…_names_the_engine_its_pool_and_the_reset_count`,
`…_names_the_process_the_thread_and_the_werkzeug_question`,
`test_the_capture_answers_while_the_failing_connection_cannot`,
`test_the_original_traceback_is_intact_and_the_control_can_fail`,
`test_a_connection_on_the_wrong_database_is_a_one_line_proof`,
`test_the_verdict_does_not_call_a_correctly_bound_connection_a_mismatch`,
`test_the_report_survives_the_suites_own_quiet_option`) and **two** in
`tests/test_db_engine_lifecycle.py`
(`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema::test_no_engine_pool_or_backend_predating_the_rebuild_survives_it`,
`TestEngineLifecycle_WhyTheHazardCannotBeForced::test_no_server_side_prepared_statement_is_ever_created`).
One cause for all eleven: `tests/conftest.py:207`, `DATABASE_URL is not set`, via
the `db_required` marker. Environmental, pre-existing, untouchable by this diff.
Neither prior round attributed them, because neither ran the *derived* set.

**Scope gate: PASS.** Two files, both in `Touches:`. No `src/`, no
`tests/fixtures/`, no `tests/conftest.py`, no `tests/helpers/book_corpus.py`.
Zero intersection with CARD-219's `Touches:`; CARD-220's is `tests/**` and so
carries no signal either way. Zero added lines match `skip|xfail|pytest.mark`
(re-derived).

**System contract:** 20 rules assembled by `system_rules.py --card CARD-218
--verify-refs`; 2 ✓ holds (ADR-0039/R1 with the F-002 qualification,
ADR-0038/R8), 18 ⚠ unchecked (16 `no_eligible_fact`, 5 of those also
`check_ref_missing` on ADR-0041/R1-R6's player-bundle tests), 0 ✗.

**What the pre-gate got wrong or missed** — it certified PASSED without
measuring the one risk its own rule 2 exists for (F-001); it did not check the
ACs' named tests against the tree (F-003); it repeated an unsourced
reproducibility figure its own data refutes (F-004); it wrote that it
"reproduced" the 4.90 s ceiling, which it did not; its P3 bidirectionality claim
holds only for whole-file selections; and its "0 skipped" belongs to the census
set, not to the derived gate, which has 11.

### What has to be true for cycle 2 to certify

1. F-001 fixed: digest the pages, do not store them; re-measure peak RSS and
   record the figure. Then the card's rule 2 has been checked with a memory
   measurement for the first time.
2. F-002: the controls must red, not pass, on a selection they cannot analyse,
   and their docstrings narrowed to what they measure.
3. F-003: the three dead AC `test:` refs resolved — written once as a shared
   curation guard, or struck and replaced with what is actually relied on —
   before CARD-219/220 are dispatched on the same wording.

## [CYCLE 1 ADJUDICATION 2026-10-24, orchestrator] All three gating findings reproduced, the prescribed fix verified before being handed on, and FOUR corrections owed to my own pre-gate

Score **6.0, NOT CERTIFIED** against `min_score: 8` — `10 − 2 (F-001 critical)
− 1 (F-002) − 1 (F-003)`. Report:
`meta/review/20261024T223738Z-CARD-218-cycle1.yml` (parses, `overall_score`
present, `cycle: 1` agrees with its filename). Risk LOW→MEDIUM.

I re-derived every gating finding before authorising a fix round, as on
CARD-271. **All three reproduce. None was overstated.**

### F-001 reproduced exactly — and the hard measurement is the RETENTION, not the peak

My own probe plugin at `pytest_sessionfinish`, after every fixture is
finalised, kept outside `tests/` (a probe there naming `interior(` would join
`rank_durations.py`'s frozen render set):

```
_SHARED_DIGEST            10 entries, 252,450,000 B (240.8 MiB)
_SHARED_SNOWFLAKE_DIGEST   8 entries, 201,960,000 B (192.6 MiB)
_FIFTH_RULE_RENDERS        1 entry,             0 B
TOTAL                        454,410,000 B = 433.4 MiB = 18.0 page bitmaps
```

Both modules still in `sys.modules`, so the lists outlive the fixtures that
filled them. `tests/test_book_pdf_memory.py:210` defines
`PAGE_BITMAP_BYTES = 2550 * 3300 * 3` = 25,245,000 — and the per-entry size is
that figure **exactly**, so "18.0 page bitmaps" is the project's own unit, not
a conversion. The review's central point stands on its own: both fixture
docstrings justify module scope over session scope by saying a session fixture
"would hold this book's page bitmaps alive for the rest of the run", and the
module-level list the fixture populates does precisely that, by the same
volume.

**One qualification, and it changes what the fix must be certified on.** The
review's per-file peak-RSS figures do not all reproduce here:

| `/usr/bin/time -l` max RSS | base | HEAD | review's HEAD delta | my delta |
|---|---|---|---|---|
| `test_book_puzzle_frame.py` | 669.1 MB | 965.9 MB | +300.6 MB | **+296.7 MB** ✓ |
| `test_book_pdf_band.py` | 1320.2 MB | 1396.3 MB | +353.2 MB | **+76.1 MB** ✗ |
| both | 1294.3 MB | 1661.0 MB | ≈+400 MB | **+366.7 MB** ✓ |

Band's base peak is already 1320 MB, set by its own renders, so its 192.6 MB
digest largely fits under an existing high-water mark; frame's base peak is
669 MB, so its 240.8 MB digest pushes the mark up almost in full. Peak RSS is
therefore **allocation-order dependent and noisy** — under my trial fix below,
band's peak went *up*, to 1491.9 MB. **So AC the fix on the retention, which is
exact and reproducible, not on peak RSS, which is a stopwatch.** Same lesson as
the pre-gate's render counter, in a second guise.

### The prescribed fix verified, not relayed

A reviewer's prescription is not a reviewed result (the brief rules' own
`max_cycles` clause). Applied as a throw-away trial and reverted,
sha256-digesting each page instead of storing its bytes:

* retention **454,410,000 B → 576 B**, all three accumulators;
* **134 passed**, unchanged;
* the controls still kill: my P2 (digest never taken) reds both frame controls,
  my P6 (a consumer draws on a shared page) reds the consumer and the band
  control. So the fix does not buy memory with discriminating power.
* `hashlib` is stdlib — ADR-0006/R1 untouched.

Both files restored and verified at `4e151282…` / `959bdff3…`.

### F-002 reproduced exactly, with the mechanism DELETED (module → class)

| selection | cells |
|---|---|
| whole file | **1 failed** — KILL |
| the control class alone | **2 passed** — VACUOUS |
| the single control node id | **1 passed** — VACUOUS |
| `-k one_render` (2 selected / 35 deselected) | **2 passed** — VACUOUS |

Confirmed, including the review's point that **no selection produces a
spurious red** — which is why this is Important and not Critical. The defect is
the universal claim in the docstrings ("Put the scope back to `function` and
there are five, and this goes red"), true only of the whole-file selection,
and `-k one_render` is the obvious way a human re-checks a control called
`test_one_render_served_the_whole_module`.

### F-003 reproduced — and it is a clean miss by my pre-gate

Grepped every `*.py` under `tests/`:

| AC | named verifier | exists? |
|---|---|---|
| AC-3 | `TestCuration_ConvertedFilesKeepTheirTestCount` | **nowhere** |
| AC-4 | `TestCuration_SharedRenderIsNotMutatedAcrossTests` | **nowhere** |
| AC-6 | `TestCuration_NoSharedInteriorStream` | **nowhere** |
| AC-2 | `TestSuiteProfile_ArtefactExistsAndIsComplete` | `tests/test_suite_profile.py` |

Three of four AC `test:` references are dead. The AC-vs-body cross-check is in
this board's own brief rules and my pre-gate did not run it.

### FOUR corrections to my own pre-gate, all of which the review is right about

1. **I wrote that the pre-gate "reproduced" the 4.90 s ceiling. It did not.**
   It reproduced the *premise* figures — 1426.16 s attributed, 69.79 s / 4.89 %
   / 131.9 ms-per-test over the nine files, the phase split — and the two
   converted files' render counts. The nine-file recoverable-duplicate table
   is still **single-instrument**. The review's cross-check suggests that
   instrument reads ≈18 % low (it predicted 1.32 s for the two files where my
   call counter measured 1.552 s removed). Immaterial to the conclusion — at
   3× the ceiling this card's whole subject is ~1 % of the suite — but
   "reproduced" was the wrong word for what I did, and it is the same family of
   error I corrected in the round's census headline two sections above.
2. **The "0.20 s solo-run reproducibility" is a full-suite figure and I applied
   it to an 8.9 s measurement.** It is real — two solo runs of the whole suite
   agreed to 0.20 s (1433.27 / 1433.47) — but it is not committed anywhere a
   reviewer could find, and it is the wrong floor for a two-file arm, whose
   spread I had myself measured at 8.53–9.30 s on an 8.90 s median, **8.7 %**.
   Worse, the argument it was supporting is backwards: the round wrote that
   0.99 s is small "against a best-case reproducibility of 0.20 s", and
   0.99 > 0.20. AC-2's suite-total clause is unshowable because a *full suite's*
   run-to-run spread is tens of seconds and detecting a 1.5 s effect costs
   1433 s per arm — not because 0.99 s is below 0.20 s.
3. **My P3 claim "the direction holds in both ways" is true only whole-file.**
   Module → class reds on the whole file and passes on a single-class
   selection, which is row 2 of the review's matrix.
4. **My "0 skipped" belonged to the census set, not to the derived gate.**
   The derived 24-file gate has **11** skips; neither the round nor the
   pre-gate had run that set, so neither attributed them. The review did:
   nine in `tests/test_admin_binding.py::TestUndefinedTableReport_*` and two in
   `tests/test_db_engine_lifecycle.py`, one cause for all eleven —
   `tests/conftest.py:207`, `DATABASE_URL is not set`, via the `db_required`
   marker. Environmental and pre-existing.

A fifth criticism I accept with a qualification: the review says the pre-gate
"certified PASSED without measuring the one risk its own rule 2 exists for".
I identified that risk and routed it to this cycle as question 1 rather than
measuring it, which is why the cycle found it — but a pre-gate that names an
unmeasured risk and returns PASSED has passed an unmeasured risk. The verdict
should have been PASSED-WITH-ONE-OPEN-MEASUREMENT, or I should have spent the
twenty seconds the probe took.

### Gate, scope gate, and the derived set's price

The review re-derived the impact set independently and got **the same 24
files**: **2916 collected, 2905 passed, 0 failed, 0 errors, 11 skipped, exit 0,
526.21 s** (against my 448.77 s price, on a busier box;
`test_book_export_interior_cover.py` is 77 % of it and is unrelated to this
diff — the figure that became CARD-287). `tests/test_browser_fixture_scope.py`,
which the derivation does not select, run explicitly: **17 tests green**.
Scope gate **PASS** — two files, both in `Touches:`, no `src/`, no
`tests/fixtures/`, no `tests/conftest.py`, no `tests/helpers/book_corpus.py`,
zero intersection with CARD-219's `Touches:`, and zero added lines matching
`skip|xfail|pytest.mark`, re-derived rather than taken from the pre-gate.

### The two adjudications that travel to CARD-219 and CARD-220

Both rounds flagged the AC wording; the review ruled on it, and the ruling is
the one that ships:

* **AC-3 and AC-4 are NOT in tension.** The round's framing was wrong. AC-3's
  label is *no coverage loss*, and additions cannot lose coverage, so its gloss
  is operative and its headline count-equality is simply mis-worded. The
  replacement wording, to be applied to all three cards: *"no node id collected
  before the change is absent after it (set difference, removals = 0);
  additions are permitted and must be named."* That is what both rounds in fact
  measured.
* **AC-2 splits in two.** The suite-total clause is struck (unshowable, for
  correction 2's reason, not the round's). The artefact clause stays and **was
  not satisfied**: no `meta/profiling/card-218-*` document exists, while
  `card-236-…`, `card-241-…` and `card-243-…` show the accepted per-card form
  costs almost nothing. AC-2's named test guards the *hotspots* document and so
  cannot verify its own clause.

**These edits wait for cycle 2.** Rewriting an AC under a card in flight is the
CARD-172 shape; the wording goes into CARD-219 and CARD-220 before they are
dispatched, and into this card when it closes.

### Verdict and route

NOT CERTIFIED, **fix round 1 authorised** on F-001, F-002 and F-003. The card's
own recommendation — land these two conversions and close CARD-218 rather than
converting the other five — is **endorsed by the review**, with all three
declines independently verified, so the fix round is the last code round this
card gets. Aggregate round counter after it: 4 of 6.

Two items the review orphans by that closure, and it is right that they need
cards: `test_book_guide_page.py`'s **9.69 s in `occurrences()`** over ten tests
— template matching, roughly twice this card's entire ceiling — and
`test_book_export_interior_cover.py`, now **CARD-287** (`d5795d86`).
## Fix round 1 notes (2026-10-24)

**F-001 and F-002 closed, both certified on exact integers. F-006 fell out of
F-002's rework and is closed with it. F-007 is declined, with the reason.
F-003 is the orchestrator's; the final node id of every control this card
leaves behind is listed at the end of these notes so the refs can be made
true.**

Final sha256 of the two files this round touched:
`tests/test_book_puzzle_frame.py`
`ad7cc1f2e1f954b7160829f665ed13667d1319ec77dac7c17e01250ea3e36d87`,
`tests/test_book_pdf_band.py`
`e5de8b9202209173ee49867d9d42d3f431da319bc7878b33c5fb6e186b18bba8`.
Nothing else under `tests/` or `src/` is in this diff.

### The discipline this round held itself to, restated because a brief is acted on

1. **Every mutant below deletes a mechanism one of my claims names**, not
   something I added. Where the only available mutant would be a
   control-on-the-addition, it is labelled as such, and a *selection* carries
   the real proof instead (the two ordering guards).
2. **The kill instrument was run over my own additions before hand-back.** The
   four new tests and the two new guards each have a row, and two of those
   rows exist only because a mutant of my own work was run: M9/M10 (the
   retention bound's unit) and M11-M14 (the two guards).
3. **Arms are counted per assertion.** Every control here now carries three or
   four; the table says which mutant or selection reds which arm, and names
   the one arm nothing reds.
4. Mutants are line-count preserving, and both files' sha256 is re-verified
   after every restore. Restores come from pristine copies kept **outside the
   worktree** — `git checkout -- <path>` restores the *index*, and the index
   here is HEAD, which does not carry this round's uncommitted work; it would
   have reverted the fix silently between two mutants. That trap is in the
   brief and it would have fired.
5. Cells, never exit codes. Every table below is failure cells.
6. Every figure was recomputed in this round, including the ones cycle 1 and
   the adjudication had already measured. Four of them did not reproduce; they
   are in "Found wrong" at the end.
7. The claims rest on counters — 454,410,000 B -> 576 B, 18.0000 page bitmaps
   -> 0.0000, 134 -> 138 collected, removals 0 — never on wall clock or peak
   RSS.

### F-001 — the retention, measured before and after

Probe plugin at `pytest_sessionfinish`, after every fixture is finalised, kept
**outside `tests/`** (a probe there would join `rank_durations.py`'s frozen
render set). Selection: both converted files, one session.

| | entries | bytes | page bitmaps |
|---|---|---|---|
| **before** `_SHARED_DIGEST` | 10 | 252,450,000 | 10.0000 |
| **before** `_SHARED_SNOWFLAKE_DIGEST` | 8 | 201,960,000 | 8.0000 |
| **before TOTAL** | 18 | **454,410,000** | **18.0000** |
| **after** `_SHARED_DIGEST` | 10 | 320 | 0.0000 |
| **after** `_SHARED_SNOWFLAKE_DIGEST` | 8 | 256 | 0.0000 |
| **after TOTAL** | 18 | **576** | **0.0000** |

`134 passed` before, `138 passed` after. The before figure reproduces the
review's and the adjudication's to the byte; the after figure reproduces the
adjudication's throw-away trial to the byte. `_FIFTH_RULE_RENDERS` holds tuples
of three ints and contributes 0 B in both arms — my instrument walks it and
reports nothing for it, which is the same verdict by a second route.

The fix is `hashlib.sha256(page.tobytes()).digest()` behind a `_page_digest`
helper, at two call sites per file (the fixture that fills the accumulator and
the comparison in the mutation control). `hashlib` is stdlib: ADR-0006/R1's
baseline is untouched.

**Peak RSS, recorded and explicitly not relied on.** `/usr/bin/time -l`, base
`4ae0d825` against the same tree with the fix — i.e. *the fix's* delta, not the
conversion's, which is what the review and the adjudication measured:

| max RSS | HEAD `4ae0d825` | HEAD + this fix | delta |
|---|---|---|---|
| `tests/test_book_puzzle_frame.py` | 954 MB | 729 MB | **-225 MB** |
| `tests/test_book_pdf_band.py` | 1476 MB | 1504 MB | **+28 MB (UP)** |
| both, one run | 1478 MB | 1348 MB | -131 MB |

Band's peak went **up** under a fix that removes 192.6 MB of retention, which
is the adjudication's point confirmed by a third measurement (its own trial saw
band rise too). Peak RSS here is allocation-order dependent; the retention is
exact. Nothing in this round rests on the table above. My frame HEAD figure
(954 MB) also cross-checks the review's 958.1 MB and the adjudication's
965.9 MB — the three agree within 1.2 %, so the *HEAD* column is sound and it
is the *delta* that is not a usable instrument.

### AC-5's missing control, and how its bound is derived

AC-5's named verifier is `test_book_pdf_memory.py`'s peak assertions, which
instrument that module's own `_live` dict (its line 420) and say at line 84
that the figure "is not the process's peak, and this module does not claim it
is". They cannot fail on bytes retained by two other modules, so AC-5 had no
control at all and a 433.4 MB regression passed a round and a pre-gate. Two
tests per converted file now hold it:

* `TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`
* `TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page`
* `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`
* `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page`

**The bound, and which derivation was chosen and why.** The brief offered two
honest idioms — import `PAGE_BITMAP_BYTES` from `test_book_pdf_memory.py`, or
re-derive `2550 * 3300 * 3` with the geometry stated. **Neither on its own; both,
in different roles.** The bound the assertion uses is
`_bitmap_bytes(pages[0])` — the geometry of a page *this module actually
drew*, so it cannot go stale behind a change of trim or resolution. The
project's constant is imported and used as the **second instrument**: the first
of the two tests asserts the drawn page equals `PAGE_BITMAP_BYTES` exactly.
That is the project's own test style (prefer an independent second
implementation over re-deriving a value with the function under test) pointed
at a constant rather than a function, and it is why the pair is two tests and
not one assertion: a test short-circuits, and the unit check must be able to
fail on its own.

Measured cost of the import: `test_book_pdf_memory` is constants-only at module
scope and costs **0.01 s** on top of a converted module's own 0.67 s import.
One declared consequence: the derived impact set does **not** model test-to-test
imports, so a change to `test_book_pdf_memory.py` will not select these two
files. The coupling is a single integer and the unit cross-check reds the
moment it stops describing the drawn page, so the blind spot is self-detecting
in the direction that matters — but it is a blind spot and it is stated here
rather than left to be found.

**The bound is strict: total retained bitmap bytes < one page bitmap.** The
digests are 576 B against a 25,245,000 B bound (five orders of magnitude of
headroom); the bytes they replaced were 10.00 and 8.00 of those units. The
bound separates the two without being tuned to either.

**The diagnosis is named.** Under M7 (the bytes put back), verbatim:

```
AssertionError: this module will leave 252,450,000 B (10.00 page bitmaps) alive
after its fixtures are finalised: _SHARED_DIGEST 252,450,000 B (10.00 pages).
pytest keeps a test module in sys.modules for the rest of the session, so a
module-level accumulator outlives the module-scoped fixture that filled it --
the retention module scope was chosen to avoid (CARD-218 AC-5, F-001). Store a
32-byte `_page_digest(page)`, not `page.tobytes()`.
```

Which accumulator, how many bytes, in how many pages' worth — all three.

**What the instrument covers, stated rather than left to be discovered.** It
walks this module's own globals: a module-level image or bytes object, and one
level inside a module-level list, tuple, set or dict — which is where a hoisted
render lands and where F-001's bytes were. It does **not** see a bitmap behind
an `@lru_cache` (this is a real channel: `test_book_pdf_band.py` has two such
functions, `_font_bytes` and `_set_once`; `functools` exposes no store to walk),
nor containers nested deeper than one level. Both limitations are in the
helper's docstring. The control is **selection-independent** — it needs no
denominator, because an accumulator holding a page-sized entry is a page-sized
entry whatever ran, so a single node id of it reds the regression.

**One correction to the review's prescription.** It wrote "the fix is one line
per file and is strictly better". It is two call sites plus an import per file,
and — far more importantly — a fix of exactly that size would have closed
F-001 while leaving AC-5 with no control, which is the condition that let the
433 MB through in the first place. The review's own AC-5 paragraph is the
refutation of its own "one line"; the round took the paragraph, not the line.

### F-002 — the tension, resolved explicitly

The defect: all three "one render served…" controls assert an equality on a
counter that only the *selected* tests increment, so a narrowed selection
narrows the denominator with it. With one consumer selected, *one render* and
*one render per test* are the same observation and the control passes whatever
the fixture's scope is.

**The tension the brief names, and the resolution.** The board's gates run
whole files; a human debugging runs one node id. A control that reds on every
single-node-id run is noise; one that passes vacuously is the defect.
Information-theoretically there is no third option: under a one-consumer
selection the two hypotheses are indistinguishable, so the control must either
guess or decline. **It declines**, and the cost is bounded in four ways that
together make it the right trade:

1. the red is confined to the control's **own node id** — no other test in
   either file reds under any selection, which the matrix below shows for all
   sixteen selections of the intact tree;
2. a human who runs an unrelated single node id never sees it, because the
   control is not selected;
3. the message says exactly what could not be evaluated and names every
   consumer that was missing, so the red is a direction, not a puzzle;
4. the denominator is the fixture's **own scope**, not "the whole file":
   `TestBookPdf_EveryFifthGridLineWider`'s class-scoped control is green when
   that class alone is selected (and kills M5 there), because its four
   consumers are its classmates. Only a selection narrower than the shared
   render's own scope declines.

So "no spurious red" is read as: no red that misdiagnoses, and no red in any
test other than the control. A decline is the control refusing to answer, and
it is labelled **DECLINE** in the matrix rather than counted as a kill.

**One correction to the review's prescribed shape.** It asked for "fixture
executions *and* consumer takings, held to a derived count of the consumers".
The denominator is taken instead from pytest's **collection**, not from a
runtime takings counter: `request.session.items` already says which consumers
this run will run, and `inspect.signature` over the module's own test functions
says which consumers exist. Same default-deny behaviour, and it avoids three
costs the prescribed shape carries — a third module-level accumulator (more
retained state, in the round that exists to remove retained state), an autouse
fixture on every test in both files, and a counter that is itself untested. The
derived counts, read off the live modules: `pages` **22** consumers,
`snowflake_interior` **8**, `page` **4**.

**F-006 is closed by the same rework, and it was under-scoped in the review.**
The review named the two read-only controls' reliance on "this class is last in
the file and pytest collects in file order". The same unasserted premise is in
the *fifth-rule count control's* docstring — "Last in the class, so every test
above has taken the fixture by now" — and it is load-bearing there: run that
control first under function scope and it would see one entry and pass. All
three controls now assert it off this run's collected order
(`_refuse_unless_nothing_takes_it_later`), and the proof it is live is a
selection, not a mutant: name the control class first and its consumers after,
and the control declines (2 cells); delete the guard and the decline disappears
(M13/M14 below).

**F-007 declined.** `snowflake_interior` asserting its two consumer classes'
`NAME` still turns one rename into 8 errors across 4 classes (was 6 across 3;
the retention class adds two). It did not fall out of this work: moving the
check into the consumers would duplicate it twice and lose the "fails at the
divergence" property the fixture's docstring argues for, and the adjudication
found the diagnosis message good. The count rose because the fix added
consumers, so the finding is marginally worse than cycle 1 measured it — stated
so the figure is not stale, not argued away. The card closes; if a successor
wants it, the shape is a session-scoped parametrised check over the two
classes, and it is not worth a round of its own.

### The full before/after selection matrix

Driven by a script in both arms; the "before" arm is a detached worktree at
`4ae0d825` whose two files hash to `4e151282…` / `959bdff3…`, i.e. the values
the brief records. Cells are failure cells. **KILL** = the mechanism's deletion
is detected. **VACUOUS** = deleted and green. **DECLINE** = red because the
control refuses the selection (mechanism intact or not — it cannot tell).

#### `snowflake_interior` module -> class (the review's reproduced row)

| selection | before | after |
|---|---|---|
| band whole file | 1 failed **KILL** | 1 failed **KILL** |
| band control class alone | 2 passed **VACUOUS** | 2 failed **DECLINE** |
| band count-control node id | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| band read-only control node id | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| band `-k one_render` (2 sel / 37 desel) | 2 passed **VACUOUS** | 2 failed **DECLINE** |
| both files, frame first | 1 failed **KILL** | 1 failed **KILL** |
| both files, band first | 1 failed **KILL** | 1 failed **KILL** |

#### `pages` module -> function

| selection | before | after |
|---|---|---|
| frame whole file | 2 failed **KILL** | 2 failed **KILL** |
| frame control class alone | 1 failed **KILL** | 2 failed (1 KILL + 1 DECLINE) |
| frame count-control node id | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| frame read-only control node id | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| frame `-k one_render` (1 sel / 98 desel) | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| both files, either order | 2 failed **KILL** | 2 failed **KILL** |

#### fifth-rule `page` class -> function

| selection | before | after |
|---|---|---|
| band whole file | 1 failed **KILL** | 1 failed **KILL** |
| fifth-rule class alone | 1 failed **KILL** | 1 failed **KILL** |
| fifth-rule control node id | 1 passed **VACUOUS** | 1 failed **DECLINE** |
| band `-k one_render` | 2 passed **VACUOUS** | 2 failed **DECLINE** |
| both files, either order | 1 failed **KILL** | 1 failed **KILL** |

#### the intact tree, all sixteen selections

| selection | before | after |
|---|---|---|
| frame whole file | 97 passed | **99 passed** |
| band whole file | 37 passed | **39 passed** |
| both files, frame first | 134 passed | **138 passed** |
| both files, band first | 134 passed | **138 passed** |
| fifth-rule class alone | 6 passed | **6 passed** |
| frame control class alone | 2 passed | 2 failed **DECLINE** |
| band control class alone | 2 passed | 2 failed **DECLINE** |
| each of the four control node ids alone | 1 passed each | 1 failed each **DECLINE** |
| frame `-k one_render` | 1 passed | 1 failed **DECLINE** |
| band `-k one_render` | 2 passed | 2 failed **DECLINE** |
| band control class FIRST, consumers after | n/a (class absent before) | 2 failed **DECLINE** (ordering) |
| frame control class FIRST, consumers after | n/a | 2 failed **DECLINE** (ordering) |
| the derived 24-file gate | see the gate section | see the gate section |

**Every after-DECLINE is a control refusing its own selection, and every
after-cell that is not a DECLINE is identical to its before-cell.** No test
other than a control changed verdict under any selection. The property the
brief required to survive — no spurious red with the mechanism intact —
survives in that reading, and the reading is stated rather than assumed.

### Mutation table — one row per mechanism DELETED

Line-count preserving; sha256 re-verified after every restore; both values
matched every time.

| # | mechanism DELETED | mutant | selection | failure cells |
|---|---|---|---|---|
| M1 | frame `pages` is module-scoped | `scope="module"` -> `"function"` | frame whole file | **2 failed** / 97 passed: `TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn` + `::test_one_render_served_the_whole_module` |
| M2 | the shared frame pages are read-only | a consumer draws a 9 px line on `pages[0]` | frame whole file | **1 failed** / 98 passed: `::test_the_shared_pages_are_handed_out_as_they_were_drawn` |
| M3 | band `snowflake_interior` is module-scoped | `scope="module"` -> `"class"` | band whole file | **1 failed** / 38 passed: `TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module` |
| M4 | the shared snowflake pages are read-only | a consumer draws on `snowflake_interior[0]` | band whole file | **1 failed** / 38 passed: `::test_the_shared_pages_are_what_the_fixture_drew` |
| M5 | band fifth-rule `page` is class-scoped | `scope="class"` -> `"function"` | band whole file | **1 failed** / 38 passed: `TestBookPdf_EveryFifthGridLineWider::test_one_render_served_the_whole_class` |
| M6 | the fixture asserts both classes name one picture | `TestBookPdf_AnswerKeyCarriesPictureTitle.NAME` -> `"Iguanodon"` | band whole file | 31 passed / **8 errors**: the four sharing tests, both retention tests, both module controls |
| M7 | **frame: a digest is stored, not the bytes** (F-001) | both `_page_digest(page)` sites -> `page.tobytes()` | frame whole file | **1 failed** / 98 passed: `TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap` |
| M8 | **band: a digest is stored, not the bytes** (F-001) | both `_page_digest(page)` sites -> `page.tobytes()` | band whole file | **1 failed** / 38 passed: `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap` |
| M9 | frame: the bound is the project's page unit | `import PAGE_BITMAP_BYTES` -> `import ENVELOPE_BYTES as PAGE_BITMAP_BYTES` | frame whole file | **1 failed** / 98 passed: `TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page` |
| M10 | band: the bound is the project's page unit | same | band whole file | **1 failed** / 38 passed: `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page` |
| M11 | frame: the denominator guard (F-002) | `_declared_consumers(namespace, fixture)` -> `(namespace, "never_a_fixture")` | frame count-control node id | **0 cells, 1 passed** — cycle 1's VACUOUS green returns, so the guard is what reds |
| M12 | band: the denominator guard (F-002) | same | band count-control node id; and band `-k one_render` | **0 cells**, 1 passed / 2 passed — both of cycle 1's VACUOUS greens return |
| M13 | frame: the ordering guard (F-006) | `items[mine + 1 :]` -> `items[len(items) :]` | frame control class first, 6 consumer classes after | **0 cells, 26 passed** — intact, the same selection gives **2 failed** |
| M14 | band: the ordering guard (F-006) | same | band control class first, 3 consumer classes after | **0 cells, 9 passed** — intact, the same selection gives **2 failed** |

M9-M14 are mutants of this round's own additions, run because a control nobody
has tried to break is a claim. M11-M14 are the two that matter: they are the
*only* evidence that F-002's and F-006's fixes are load-bearing rather than
decorative, and they were run before hand-back, not after a reviewer asked.

### Arms, per assertion — including the one nothing reds

| control | arms | what reds each |
|---|---|---|
| frame `::test_the_shared_pages_are_handed_out_as_they_were_drawn` | 4: denominator / ordering / digest-was-taken / nothing-moved | narrowed selection; reordered selection; M1; M2 |
| frame `::test_one_render_served_the_whole_module` | 3: denominator / ordering / one book's digests | narrowed selection; reordered selection; M1 |
| band `::test_the_shared_pages_are_what_the_fixture_drew` | 4: denominator / ordering / digest-was-taken / nothing-moved | narrowed selection; reordered selection; **nothing** (see below); M4 |
| band `::test_one_render_served_the_whole_module` | 3: denominator / ordering / one book's digests | narrowed selection; reordered selection; M3 |
| band `::test_one_render_served_the_whole_class` | 4: denominator / ordering / one render / the page is the 30x30 | narrowed selection; reordered selection; M5; **nothing** |
| frame + band `::test_no_module_level_accumulator_retains_a_page_bitmap` | 1 | M7 / M8 |
| frame + band `::test_the_page_bitmap_unit_is_this_modules_own_page` | 1 | M9 / M10 |

**Two arms nothing in this round reds, named rather than left for a reviewer to
find.** (a) band's `assert _SHARED_SNOWFLAKE_DIGEST, "the shared-render digest
was not taken"` is a truthiness check that the count control's own arm
subsumes, so no mutant distinguishes it; frame's equivalent arm is a *length*
check and M1 does red it. (b) `assert drawing_of(page).columns == MAX_SIZE` in
the fifth-rule control is a pre-existing premise check on the shared page's
identity, not a control on this card's mechanism, and no mutant of a CARD-218
mechanism reaches it. Neither was added this round; both are stated because a
`FAILED` line says nothing about the arms that never ran.

### Why the machinery is written twice

`_case_of`, `_declares`, `_declared_consumers`, `_consumers_among`, the two
guards and the two retention helpers are reimplemented natively in each file
(~90 lines each) rather than hoisted. The two converted files are this card's
whole subject; a shared helper would be a third file outside it, and
`tests/helpers/book_corpus.py` is one of the files the scope gate forbids. The
house precedent for two places needing the same small check is to write it
twice — CLAUDE.md, `solver/propagate.py`'s `mask_runs`. **The honest cost,
stated: nothing cross-checks the two copies against each other**, so a
correction to one can be forgotten in the other. A successor that wants a
third converted file should hoist all of it into one guard at that point, and
that is the moment to do it, not now.

### Gates

All five, with `-o addopts=''` wherever the output is the measurement
(`pyproject.toml:89` already sets `-q`, and a second one suppresses the count
line). File lists built as zsh arrays with their length printed; never `-k` for
a gate.

**1. Both converted files, green, with every addition named.**
`pytest tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py` ->
**138 collected, 138 passed, 0 failed, 0 skipped** (frame 99, band 39, run
separately as well). 134 -> 138 by set difference, removals 0, the four
additions named in the section below.

**2. The derived cycle gate, run as derived.**
`scripts/impact_set.py tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py`
-> **24 files**, the same 24 the review derived, re-derived here after the diff
(the new cross-module import does not move the set: the derivation models
`src/nonogram` reach, not test-to-test imports — see the AC-5 section's
declared blind spot). Run as derived, not hand-narrowed:

**2891 collected, 2880 passed, 0 failed, 0 errors, 11 skipped, exit 0,
454.78 s.** The same 24 files at base `4ae0d825` collect **2887**, so the
delta is +4 and is exactly this round's four controls.

All **11** skips attributed by node id, enumerated with
`--collect-only -q -m db_required` over the derived set rather than inferred
from the count: **nine** in
`tests/test_admin_binding.py::TestUndefinedTableReport_NamesWhatTheFailingConnectionWasTalkingTo`
(`test_the_report_carries_the_four_groups`,
`test_the_report_names_the_database_the_failing_connection_was_on`,
`test_the_report_names_the_engine_its_pool_and_the_reset_count`,
`test_the_report_names_the_process_the_thread_and_the_werkzeug_question`,
`test_the_capture_answers_while_the_failing_connection_cannot`,
`test_the_original_traceback_is_intact_and_the_control_can_fail`,
`test_a_connection_on_the_wrong_database_is_a_one_line_proof`,
`test_the_verdict_does_not_call_a_correctly_bound_connection_a_mismatch`,
`test_the_report_survives_the_suites_own_quiet_option`) and **two** in
`tests/test_db_engine_lifecycle.py`
(`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema::test_no_engine_pool_or_backend_predating_the_rebuild_survives_it`,
`TestEngineLifecycle_WhyTheHazardCannotBeForced::test_no_server_side_prepared_statement_is_ever_created`).
One cause for all eleven: `tests/conftest.py:207`,
`Database not reachable: DATABASE_URL is not set`, via the `db_required`
marker. Environmental, pre-existing, untouchable by this diff. The 11 is the
same set the review attributed, re-enumerated rather than inherited.

`tests/test_book_export_interior_cover.py` is again most of the price and is
unrelated to this diff (CARD-287).

**3. `tests/test_browser_fixture_scope.py`, explicitly.** No scoped selection
reaches it — it names none of this card's selectors and reaches its subject
through a `--collect-only` subprocess, which is how CARD-271 arrived at its
merge gate red after four clean scoped gates. Run on its own:
**29 collected, 29 passed, 0 skipped, 49.90 s.** Not 17 — see "Found wrong".

**4. The census guards, explicitly.**
`pytest tests/test_browser_fixture_scope.py tests/test_suite_profile.py tests/test_guard_integrity.py tests/test_impact_set.py tests/test_fixture_integrity.py`
-> **643 collected, 643 passed, 0 failed, 0 skipped, 80.34 s** — the same 643
the brief records before the change. Each one checked for the specific hazard,
not assumed:

* **`tests/test_suite_profile.py`'s `RENDER_HEAVY_SNAPSHOT` check.** Verified
  directly as well: `regrep_render_set(tests/) == RENDER_HEAVY_SNAPSHOT`,
  added `[]`, gone `[]`. This constrained the diff. `tests/test_book_puzzle_frame.py`
  has **0** matches for the defining grep before and after, and it must stay
  at 0 — so every docstring added to it avoids all eight idioms, `interior(`
  included (the word "interior" appears, never followed by a parenthesis).
  `tests/test_book_pdf_band.py` keeps 23 matches.
* **`tests/test_guard_integrity.py`'s silence census.** Zero added lines match
  `skip|xfail|pytest.mark`, re-derived over the diff. The four
  `# pragma: no cover` comments the first draft carried were **removed**: this
  repo configures no coverage tool, so they decorated nothing, and a coverage
  pragma in a diff a silence census reads is a question nobody should have to
  answer.
* **`tests/test_fixture_integrity.py`.** Nothing under `tests/fixtures/` was
  read, written or regenerated (G-2).
* **`tests/test_impact_set.py`** and **`tests/test_browser_fixture_scope.py`** —
  both green, see above.

**5. The retention probe, before and after** — the table in the F-001 section:
454,410,000 B -> 576 B, 18.0000 -> 0.0000 page bitmaps, instrument kept outside
`tests/`.

**Scope gate.** Two files, both in `Touches:`. No `src/`, no `tests/fixtures/`,
no `tests/conftest.py`, no `tests/helpers/book_corpus.py`, no
`meta/profiling/`, and no other `Touches:` file. The card's
`## Acceptance criteria` section is **not** edited, in either tree (F-003 is
the orchestrator's). `meta/` is not committed from this worktree.

**One census the first draft broke and the final diff does not.** The review's
own diagnostic for "no guard on the board can see process memory" is
`grep -rE 'RLIMIT_AS|peak_rss|max_rss|tracemalloc' tests/`. The first draft of
the retention classes' docstrings *named those four tokens* while making that
claim, so the grep returned **three** paths instead of one and the prose
falsified itself. Measured, caught before hand-back, and rewritten: the grep is
back to `tests/test_book_pdf_memory.py` alone.

**One cosmetic change declined, and why it is recorded.** The ordering guard's
set comprehension is awkwardly indented in both files. A whitespace-only
reformat was written, measured green, and then **reverted**: it moved both
files' sha256, which would have turned every figure in this section — the
24-file gate, the census set, the sixteen-selection matrix and all fourteen
mutants — into a claim about bytes no longer on disk. Re-running the lot costs
about fifteen minutes to buy indentation. The bytes the evidence was taken
against are the bytes that ship, and the two hashes at the top of these notes
are the ones on disk.


### Collected count, and every addition by node id

**134 -> 138**, by set difference over `--collect-only -q` node ids in the base
worktree and in this one, not by subtracting counts:

* **removals: 0** (AC-3, G-1 — and this is the measurement AC-3's gloss asks
  for, which still has no standing guard; see F-003 below);
* **additions: 4**, all four deliberate controls, none a test of the product:
  * `tests/test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page`
  * `tests/test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`
  * `tests/test_book_pdf_band.py::TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_the_page_bitmap_unit_is_this_modules_own_page`
  * `tests/test_book_pdf_band.py::TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`

No test was renamed. Five existing controls gained guard calls and a `request`
parameter; no assertion any of them already made was removed or weakened.

### Found wrong, with the measurement

1. **`tests/test_browser_fixture_scope.py` has 29 tests, not 17.** The review
   wrote "17 tests, all green, confirmed not hoped"; the adjudication repeated
   "17 tests green"; the fix brief repeats it as gate 3. Measured here:
   `--collect-only -q` gives **29 tests collected** in both the base worktree
   and this one, and run explicitly it is **29 passed, 0 skipped**. The
   review's *other* figure is the one that confirms it: the derived 24-file set
   collects **2887** at base (measured), and 2887 + 29 = **2916**, which is
   exactly the review's reported total. So the review ran the right set and
   mis-stated that file's size by 12; its gate total was never wrong.
2. **The review's citation of `test_book_pdf_memory.py` line 38 for the
   25,245,000 B figure is wrong.** Line 38 is about `ru_maxrss` and four
   Pillow buffers. The figure is prose at **line 14** and the constant at
   **line 210** (`PAGE_BITMAP_BYTES = 2550 * 3300 * 3`), which is the line the
   adjudication cites correctly. The review's other two citations in the same
   paragraph (line 84, line 420) are both right.
3. **"The fix is one line per file and is strictly better" understates it by
   an order of magnitude** — see the AC-5 section. Two call sites plus an
   import per file, and a fix of literally that size would have shipped F-001
   closed with AC-5 still uncontrolled.
4. **The review's per-file peak-RSS deltas are not an instrument**, which the
   adjudication already said for band. Third measurement, from a different
   base: under this fix band's peak goes **up** 28 MB while 192.6 MB of
   retention is removed. Recorded above; nothing rests on it.
5. **F-006 is under-scoped as written.** It names the read-only controls; the
   same unasserted file-order premise is in the fifth-rule count control's
   docstring and is load-bearing there. All three are fixed.

Nothing else in the review or the adjudication failed to reproduce. In
particular: the 454,410,000 B retention, its exact per-entry equality with
`PAGE_BITMAP_BYTES`, the four F-002 cells for `snowflake_interior`, the three
dead AC refs, and the 24-file derived set all reproduce exactly.

### For F-003 — the final node id of every control this card leaves behind

The orchestrator owns the AC `test:` refs. What exists on disk when this round
ends, so the refs can be made true rather than guessed:

| AC | what it claims | the control that holds it, after this round |
|---|---|---|
| AC-1 | the book is rendered once per module | `tests/test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_one_render_served_the_whole_module`; `tests/test_book_pdf_band.py::TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module`; `tests/test_book_pdf_band.py::TestBookPdf_EveryFifthGridLineWider::test_one_render_served_the_whole_class` — **each answers only for a run that collected every consumer of its fixture, and declines otherwise**, which is the wording an AC ref should carry |
| AC-2 | the wall-clock is recorded | `tests/test_suite_profile.py::TestSuiteProfile_ArtefactExistsAndIsComplete` guards the *hotspots* document and cannot verify AC-2's own clause; unchanged by this round, and the `meta/profiling/card-218-*` artefact the adjudication asks for is not mine to commit from a worktree |
| AC-3 | no node id collected before is absent after | **still no standing guard anywhere.** `TestCuration_ConvertedFilesKeepTheirTestCount` exists nowhere. Held this round by the set difference above (removals 0, additions 4 named). A standing guard would be a new shared file outside this card's two-file subject, so it was not written |
| AC-4 | a mutated copy does not leak | `tests/test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn`; `tests/test_book_pdf_band.py::TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_the_shared_pages_are_what_the_fixture_drew`. `TestCuration_SharedRenderIsNotMutatedAcrossTests` exists nowhere |
| AC-5 | the fixture keeps no more pages alive | the four new node ids listed above. The AC's current ref — `test_book_pdf_memory.py`'s peak assertions — is the one that could not fail, and should be *replaced*, not supplemented |
| AC-6 | no fixture hands one `InteriorStream` to two tests | **no control of any kind, in this round or before.** `TestCuration_NoSharedInteriorStream` exists nowhere. Deliberately not written: a control confined to these two files would cover 2 of the tree's 30 render-heavy files and would make the ref *look* satisfied while it was not — the exact `check_ref_missing` shape F-003 is about. Verified by inspection only, as cycle 1 found: both shared fixtures return `list[Image.Image]`, so neither hands out a generator |

### DECLARATIONS

* `DECLARATIONS F-001` — **re-derived and corrected in the same diff.** Both
  shared fixtures' docstrings claimed module scope avoids holding "this book's
  page bitmaps alive for the rest of the run"; the claim is now true of
  everything the fixture leaves behind, and the accumulators' own `#:` comments
  say "a sha256 per page", not "the bytes". `_page_digest`'s docstring carries
  the measurement (10 and 8 page bitmaps) and the reason the 32 B is equivalent.
  Nothing in `docs/` or `meta/architecture/` states anything about these
  fixtures; the card's AC-5 ref is wrong and is F-003's to fix, listed above.
* `DECLARATIONS F-002` — **re-derived and corrected.** All three controls'
  docstrings asserted a universal ("Put the scope back to `function` and there
  are five, and this goes red"). Each now states the scope of its claim — a run
  that collected every consumer — names cycle 1's measured vacuous selections,
  and says what happens instead. Both control classes' "it runs last" prose is
  now "it says so to pytest rather than to the reader".
* `DECLARATIONS F-006` — folded into F-002's declarations above; the premise is
  asserted, so the prose stating it is no longer an unchecked claim.
* `DECLARATIONS F-007` — none (declined; the finding's own count is restated
  here as 8 errors across 4 classes, up from cycle 1's 6 across 3, because the
  fix added two consumers).
* No config field, parameter or timeout acquired a second job. No blast radius,
  error classification or lifecycle changed. `src/**` is untouched.

## [FIX ROUND 1 PRE-GATE 2026-10-24, orchestrator] PASSED — every new mechanism certified against a mutant of my own, and two findings that are mine, not the round's

Tree: the worktree's uncommitted fix, `tests/test_book_puzzle_frame.py`
`ad7cc1f2e1f954b7160829f665ed13667d1319ec77dac7c17e01250ea3e36d87` and
`tests/test_book_pdf_band.py`
`e5de8b9202209173ee49867d9d42d3f431da319bc7878b33c5fb6e186b18bba8` — the
values the round recorded, verified before and after every mutant. Restores
came from **pristine copies outside the worktree**: the round is right that
`git checkout -- <path>` restores the *index*, which here holds the pre-fix
file, and would have silently reverted the fix between two mutants.

`+374/−17` and `+335/−14` against `4ae0d825`; 514 added lines are executable
rather than prose.

### What reproduced

| claim | reproduced |
|---|---|
| retention 454,410,000 B → **576 B** (320 + 256) | **yes**, to the byte, by my own `sessionfinish` probe |
| 134 → **138** collected | **yes**, by set difference: **removals 0**, additions exactly the 4 named AC-5 controls, no renames |
| frozen render set: frame 0 matches, band 23 | **yes**, exactly |
| census guards | **643 passed, 0 failed, 0 skipped** |
| both files green | **138 passed** |

### Six mutants of my own, against the mechanisms the round ADDED

Line-count preserving (3441 → 3441, 1953 → 1953, printed each time), cells and
never exit codes.

| # | mechanism deleted | selection | cells |
|---|---|---|---|
| Q1 | frame: `_page_digest(page)` → `page.tobytes()` at the **store** site only | frame whole file | **2 failed** / 97 — the AC-5 retention control **and** `::test_the_shared_pages_are_handed_out_as_they_were_drawn` |
| Q2 | band: the same | band whole file | **2 failed** / 37 — the band twins |
| Q3 | frame: the **denominator** guard (`_declared_consumers(namespace, fixture)` → `(namespace, 'nope')`) | the count control's node id | **1 passed — cycle 1's VACUOUS green RETURNS** |
| Q4 | band: the denominator guard | band `-k one_render` | **2 passed — both of cycle 1's vacuous greens return** |
| Q5 | band: the **ordering** guard (`items[mine + 1 :]` → `items[len(items) :]`) | the 4 consumer classes with the controls named FIRST | **9 passed — the 2 reds VANISH** (intact, same selection: **2 failed**) |
| Q6 | frame: the project's page unit (`PAGE_BITMAP_BYTES` redirected to 99) | frame whole file | **1 failed** / 98 — `::test_the_page_bitmap_unit_is_this_modules_own_page` alone |

**Q3 / Q4 / Q5 are the ones that mattered**: they are the only evidence the
F-002 and F-006 fixes are load-bearing rather than decorative, and all three
behave. Q5 took two attempts and the first was worthless — selecting only the
control class plus one consumer let the **denominator** guard fire before the
ordering guard could be evaluated, so the reds I saw were not the mechanism I
was testing. The honest version names every consumer and reorders them, and
that is the run recorded above. An instrument that reds for the wrong reason
reads exactly like one that reds for the right one.

Q1/Q2 differ from the round's M7/M8 by design and both are correct: the round
changed **both** `_page_digest` sites so only the retention control reds; I
changed the **store** site alone, so the comparison site disagrees too and the
read-only control reds beside it. Two cells, not a contradiction — and it shows
both controls bite on that line.

### FINDING A (mine): the DECLINE design reds the controls under `--lf` and under any `--deselect` — including this board's own gate idiom

The round resolved F-002 by making a control that cannot evaluate its
denominator **fail** rather than pass, which is ADR-0039/R2's default-deny and
is the right call. It bounded the cost as "a human running an unrelated node id
never sees it". That is **true** — but the bound was not measured at its edges.
Measured here:

| selection | verdict |
|---|---|
| one unrelated consumer node id | **green** ✓ |
| an unrelated class (`TestBookPdf_EveryFifthGridLineWider`) | **green** ✓ |
| whole file **minus one consumer** (`--deselect`) | **2 failed** |
| `pytest --lf` after any earlier failure | **2 failed** |

The specific consequence, which nobody has written down: **this board's AC/EC/G
gate practice — "selected by explicit node id, never by `-k`" — now reds these
five controls.** CARD-271's gate named eighteen node ids; a gate that named
these would report red on a correct tree.

**Not a reason for round 5.** The design is principled, the diagnosis names the
remedy, no gate on this board uses `--lf` or `--deselect`, and the alternative —
skipping instead of failing — is the green-with-skips shape this board forbids.
What it changes is **how this card is gated**: the two files are selected
**whole**, and a DECLINE is read as *not evaluable under this selection*, never
as a pass and never as a failure of the subject. Recorded here so the merge
gate's own output is not misread.

### FINDING B (mine, and the cause is my own scope fence): a card about removing duplication ends by duplicating 53 lines of guard logic

Nine helpers were added to **both** files. AST-normalised with docstrings
stripped, **8 of 9 are byte-identical** — `_page_digest`, `_case_of`,
`_declares`, `_declared_consumers`, `_consumers_among`,
`_refuse_unless_every_consumer_is_collected`, `_bitmap_bytes`,
`_retained_bitmap_bytes` — **53 normalised executable lines in two places**,
and nothing asserts the copies agree.

**The ninth has already drifted.** `_refuse_unless_nothing_takes_it_later`
differs only in its assertion message, and the two copies prescribe different
remedies for the same condition: *"move its class to the end of the file"*
against *"move it below them"*. Harmless today; it is the first millimetre of
the class that cost CARD-261 (both copies of the component map drifted, in
different places) and that CARD-281 exists to mechanise.

**The cause is my own fix brief, not the round's judgement.** I fenced
`tests/conftest.py` out of this round's scope — and `tests/conftest.py` is in
this card's own `Touches:`, and the tree already imports a shared helper from
it (`tests/test_card_156_db_fixture.py:14`,
`from tests.conftest import _refuse_unless_test_database`). So a precedented
home existed and I closed it off. The round took the only option left.

Filed rather than fixed, and the decisive reason is forward-looking: **CARD-219
converts six more files and needs the same machinery, which would make a third
copy.** That is where the shared home should be created, with the agreement
guard the two existing copies lack. Backlogged, and named on CARD-219.

### Verdict

PASSED. F-001 closed and certified on the **retention**, which is exact — the
round confirms from a third measurement that peak RSS is unusable here (band's
peak *rises* 1476 → 1504 MB while 192.6 MB of retention is removed). F-002 and
F-006 closed and certified load-bearing by Q3/Q4/Q5. F-007 declined with a
re-measurement rather than an argument (its mutant now errors 8 tests across 4
classes, worse than cycle 1's 6 across 3, because the retention controls add
two consumers) — accepted.

**A correction to my own cycle-1 adjudication, which the round caught:**
`tests/test_browser_fixture_scope.py` holds **29** tests, not 17. The review
said 17 and I repeated it without checking. Verified: 29 collected in both
trees, the file is unchanged between them, and the review's own gate total
settles it — the 24-file set collects 2887 at base and 2887 + 29 = **2916**,
exactly what cycle 1 reported. So the review ran the right set and mis-stated
one file's size; its gate figure was never wrong. The round's other two
corrections also hold: the 25,245,000 B figure is prose at
`test_book_pdf_memory.py:14` and the constant at `:210` (the line I cited), not
`:38`; and "one line per file" understated the fix, because a fix of that size
would have closed F-001 while leaving AC-5 with no control — the condition that
let 433 MB through in the first place.

Next: review cycle 2 on the 514 new executable lines — nine helpers, four new
tests and three reworked controls that no reviewer has yet seen. Aggregate round
counter after it: 5 of 6.
