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
assertions.** Across the test tree there are 110 `interior(...)` call sites, 68
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
