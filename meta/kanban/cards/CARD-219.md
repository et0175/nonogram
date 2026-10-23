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

<!-- DEAD `test:` REFS RESOLVED 2026-10-24, orchestrator, from CARD-218's review
cycle 1 (F-003) and the orchestrator's follow-up count. The finding: EIGHT
distinct `TestCuration_*` verifiers are named across CARD-218, CARD-219 and
CARD-220, and ZERO of them exist — there is no `tests/test_curation.py` and no
class whose name begins `TestCuration` anywhere under `tests/`. A planned
shared guard module was never written and three cards' ACs were written against
it, which reads as mechanically checked and is not (`check_ref_missing` in the
ADR-0039 sense).

The resolution, taken once for all three cards rather than three times: SIX of
the eight are **diff properties, not test properties** — "the count is
unchanged", "no minimum was lowered", "these paths are untouched", "this
mechanism keeps a rendering test" all compare the tree BEFORE the card with the
tree after it, and no standing test can know "before this card". A standing
test that tried would be a hand-maintained census that every later card breaks,
which is the artefact class this board's guardrails forbid. Those six move to
the AC/EC/G gate station as explicit gate-time measurements, which is what both
CARD-218 rounds actually did. The two that ARE derivable keep a test, named
below. No AC's substance changed; only what verifies it, and each now names
something that exists or something that will be run. -->

- **AC-1** (happy): *Given* a converted positional test, *when* it runs, *then*
  it asserts the same fact about the same book with no page rendered, and it
  fails if the plan changes. (test: the converted tests themselves, names
  unchanged)
- **AC-2** (guard, plan-to-pixel tie): *Given* each file this card converts,
  *when* the card is reviewed, *then* it names a surviving rendering test in
  that file's mechanism, and that test is still present and green. (**gate**: the card names the
  surviving rendering test per converted mechanism by node id and the gate runs
  each one -- recorded, not asserted; "converted" is card knowledge that no
  standing test has)
- **AC-3** (guard, mutation): *Given* a deliberate off-by-one injected into the
  page-plan arithmetic (`interior_page_count`, the divider's position, the
  answer-section count), *when* the suite runs, *then* the converted tests
  fail — the plan assertions are real coverage, not tautologies over the same
  function. (test: the card's own mutation evidence, recorded per
  `review.mutation_check`)
- **AC-4** (guard, no coverage loss): *Given* the converted files, *when* the
  suite runs, *then* their collected test count is unchanged — conversion never
  deletes or merges a test. (**gate**: set difference over sorted
  node ids between the fork point and HEAD -- removals must be 0; additions are
  permitted and must each be named on the card. A standing test cannot know the
  pre-card count; see the resolution note above.)
- **AC-5** (happy, measured): *Given* a solo profile before and after, *then*
  the card records both wall-clocks and the per-file deltas. (recorded, not
  asserted)
- **AC-6** (edge, no second implementation): *Given* a converted geometric
  test, *when* it computes its expectation, *then* it reads the layout
  function's own returned numbers and does not re-derive them with a copy of
  the formula under test. (**gate**: reviewed per
  converted test, each named on the card with the call site it reads its
  expectation from. A tree-wide derived version of this check is possible and is
  its own card, not this one's.)

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

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-219 --root meta/architecture` (14 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same diffic… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the … (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra… (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH… (check: test: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot a… (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is… (check: test: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to … (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

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
