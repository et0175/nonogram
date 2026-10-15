# CARD-219: Positional assertions read the page plan instead of rendering pixels

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/219-assert-the-plan-not-the-pixels
**Worktree:** —
**Source:** owner request 2026-10-13 ("make cards for tests curation"); the structural half of the dispatcher's cost analysis
**Idea:** —
**Wave:** —
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-217, CARD-205, CARD-206, CARD-207, CARD-208, CARD-209
**Touches:** tests/test_book_pdf_levels.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/test_book_pdf_two_up.py, tests/test_book_solved_answer_key.py, tests/test_book_finalise_gutter.py, tests/property/test_book_export_interior.py, tests/helpers/book_corpus.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The seam already exists in production code.** The export path splits
deciding from drawing, deliberately and completely:
`BookPDFGenerator.interior_stream` settles the print order, the level cut, the
pairing walk, the answer-section plan and all three page counts **before a
pixel exists** — its own docstring says "an export that is going to be refused
is refused before its file has a first byte". `SectionPlan`, `PuzzlePagePlan`,
`DividerPagePlan`, `AnswerPage`/`PackedAnswerPage`, `InteriorStream`'s counts
and `interior_page_count` are all pure, sheet-free values.

**Many tests ignore that seam and render instead.** A test whose claim is
*positional* — "the SOLUTIONS divider is interior page N", "a level's divider
immediately precedes its first puzzle page", "the TOC occupies one page", "this
pair shares a page", "the answer section takes N pages" — can be settled from
the plan. Rendering a book to prove it costs 25 MB-class bitmaps per page to
assert an integer.

**What to do.**

1. Take CARD-217's hotspot ranking. For each of the slowest render-heavy tests,
   classify its claim:
   - **positional / arithmetic** (page numbers, ordering, counts, parity,
     which puzzles share a page, which page a divider opens) → convert it to
     assert against `section_plan(...)` / `interior_stream(...)`'s counts /
     `plan_small_answer_pages(...)` / `interior_page_count(...)`, with no
     render at all;
   - **geometric** (a cell's size in mm, a rule's width, a clue's centre, the
     folio's corner) → convert it to assert against the `Layout` /
     `PairLayout` / `PackedSolvedLayout` the layout functions return — still no
     render: COMP-007 returns device-pixel numbers, which is what these tests
     actually mean;
   - **pixel** (ink is where it should be, the baseline digests, the
     colour space, the JPEG round trip, "the grid lines remain visible through
     the filled cells") → **leave it rendering.** These are the tests that
     justify the suite's cost, and this card must not convert them.
2. Convert in descending order of measured cost; stop when the remainder is not
   worth the churn. Record which tests were converted, which were classified
   pixel and left alone, and the measured delta per file.
3. **Keep at least one rendering test per mechanism.** A mechanism whose every
   test became a plan assertion has lost its proof that the plan is what gets
   drawn. For each file converted, name in the card the surviving rendering
   test that ties plan to pixels (often the baseline digest test or a
   `pdf_pages` round-trip).
4. Re-profile solo (CARD-217's command) and record before/after.

## Acceptance criteria

- **AC-1** (happy): *Given* a converted positional test, *when* it runs, *then*
  it asserts the same fact about the same book with no page rendered, and it
  fails if the plan changes. (test: the converted tests themselves, names
  unchanged)
- **AC-2** (guard, plan-to-pixel tie): *Given* each file this card converts,
  *when* the card is reviewed, *then* it names a surviving rendering test in
  that file's mechanism, and that test is still present and green. (test:
  `TestCuration_EveryConvertedMechanismKeepsARenderingTest`)
- **AC-3** (guard, mutation): *Given* a deliberate off-by-one injected into the
  page-plan arithmetic (`interior_page_count`, the divider's position, the
  answer-section count), *when* the suite runs, *then* the converted tests
  fail — the plan assertions are real coverage, not tautologies over the same
  function. (test: the card's own mutation evidence, recorded per
  `review.mutation_check`)
- **AC-4** (guard, no coverage loss): *Given* the converted files, *when* the
  suite runs, *then* their collected test count is unchanged — conversion never
  deletes or merges a test. (test:
  `TestCuration_ConvertedFilesKeepTheirTestCount`)
- **AC-5** (happy, measured): *Given* a solo profile before and after, *then*
  the card records both wall-clocks and the per-file deltas. (recorded, not
  asserted)
- **AC-6** (edge, no second implementation): *Given* a converted geometric
  test, *when* it computes its expectation, *then* it reads the layout
  function's own returned numbers and does not re-derive them with a copy of
  the formula under test. (test:
  `TestCuration_NoReDerivedGeometryInConvertedTests`)

## Guardrails

- G-1: Pixel-claim tests stay rendering — the baseline digest tests, the
  `pdf_pages` round trips, the colour-space tests and the
  grid-through-fill tests are not converted (test: AC-2's tie check).
- G-2: No test deleted, renamed, skipped or merged (AC-4).
- G-3: Property tests' corpus-minimum assertions are not lowered (same rule as
  CARD-218 G-3).
- G-4: `PropertyTest_Solver_NeverFalsePositiveUniqueness` (CON-005/EC-001),
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (ADR-0036/R1) and
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` (CON-019) are
  untouched.
- G-5: Do not edit `src/**`. If a plan value a test needs is not reachable
  without a production change, that is a finding to raise, not a change to
  make here.
- G-6: Out of scope — fixture scoping (CARD-218) and deleting redundant tests
  (CARD-220).

## Architecture context

- **FR:** FR-040, FR-042, FR-043 (the pairing, answer-key and page-numbering
  statements whose tests this card re-aims at the plan) — no requirement
  changes; only how its tests are expressed.
- **ADR:** ADR-0036/R2 (layout functions own geometry, which is exactly why
  geometric claims can be asserted on their return values), ADR-0036/R1.
- **CON:** CON-005, CON-019 (G-4), CON-020.
- **Components:** none (test tree only; it consumes COMP-007/COMP-009's
  existing pure seams).
- **Trace:** not applicable.

## Worktree notes

- Scheduling: same reason as CARD-218 — it edits the book test files that
  CARD-205..209 extend, so it waits for all five.

## Re-pointed 2026-10-15 by CARD-217's measurement

CARD-217 profiled the suite solo and **neither hypothesis this card was cut on is where the time
is**. Measured shares of a 930.81 s run: the browser family `tests/test_puzzle_solver_*.py`
**39.78%**, the render-heavy set **21.23%**, `tests/property/*` **15.23%** — and over half the
property time is itself render-heavy, so the corpus hypothesis was largely a restatement of the
render one rather than a rival. A browser test costs 868 ms against everything else's 83 ms.

So this card is **no longer the biggest prize**, and `meta/profiling/suite-hotspots-20261015.md`
is now its source of truth rather than the counts in its own body. **CARD-235** takes the
browser family and is P1 ahead of it.

The profile points this card at one file above all others:
**`tests/property/test_book_pdf_geometry.py`, 48.66 s in four tests** — the densest spot in the
suite and exactly the shape this card exists for (positional claims paid for in rendered pixels).
Start there and measure the saving by `rank_durations.py` on a solo run.
