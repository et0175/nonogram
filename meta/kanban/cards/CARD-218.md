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
