# CARD-219: Positional assertions read the page plan instead of rendering pixels

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/219-assert-the-plan-not-the-pixels
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-219
**Source:** owner request 2026-10-13 ("make cards for tests curation"); the structural half of the dispatcher's cost analysis
**Idea:** —
**Wave:** 57
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-217, CARD-205, CARD-206, CARD-207, CARD-208, CARD-209
**Touches:** tests/test_book_pdf_levels.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/test_book_pdf_two_up.py, tests/test_book_solved_answer_key.py, tests/test_book_finalise_gutter.py, tests/property/test_book_export_interior.py, tests/helpers/book_corpus.py
<!-- SHARED CURATION HELPERS ARE THIS CARD'S TO CREATE, added 2026-10-24 from
CARD-218's fix-round pre-gate. CARD-218's fix round 1 had to put nine helper
functions in BOTH of its two files -- 8 of the 9 byte-identical in code, 53
executable lines, nothing asserting the copies agree, and the ninth's assertion
message already prescribing two different remedies for one condition. The cause
was a scope fence: the orchestrator fenced tests/conftest.py out of that round,
although it sits in CARD-218's own Touches and the tree already imports a
shared helper from it (tests/test_card_156_db_fixture.py:14). This card
converts SIX more files and needs the same machinery, so it is where the third
copy would appear and where the shared home belongs -- tests/conftest.py (a
declared conflict hotspot, so this card serializes against anything else
touching it) or tests/helpers/. Take the two existing copies with it rather
than adding a third, and give the result the agreement guard they lack. The
helpers: _page_digest, _case_of, _declares, _declared_consumers,
_consumers_among, _refuse_unless_every_consumer_is_collected,
_refuse_unless_nothing_takes_it_later, _bitmap_bytes, _retained_bitmap_bytes.
Backlogged in full under @tech-debt.

AND TWO OPEN HOLES IN THOSE HELPERS COME WITH THEM, from CARD-218's review
cycle 2 (2026-10-24), both reproduced by the orchestrator:

(1) THE DENOMINATOR GUARD IS DEFAULT-DENY ONLY OVER CONSUMERS WRITTEN IN A
TEST'S OWN SIGNATURE. `_declared_consumers` reads `inspect.signature` and
`_consumers_among` reads `item.fixturenames`; a consumer taking the fixture
through `request.getfixturevalue` is invisible to BOTH. Measured with an
identical late class drawing on a shared page: taken as a parameter it is
CAUGHT (2 cells), taken via `getfixturevalue` it is MISSED (40 passed, 0
cells) -- so AC-4's no-mutation guarantee is void for that consumer. The idiom
is live in this tree: 9 sites, one of them tests/test_puzzle_solver_page.py:671
`return request.getfixturevalue("page")`, the same fixture name as band's
class-scoped render. CARD-218's fix round 2 closed only that one channel, and
only in its own two files, with an equality-to-zero AST check that neither file
uses `getfixturevalue`. STILL OPEN and this card's to close when it builds the
shared home: the transitive-fixture closure (a consumer that takes the fixture
via another fixture), an inherited consumer on a subclass, a consumer in a
nested Test class, and `@pytest.mark.usefixtures` / `pytestmark`. A false
negative in a default-deny guard is the one direction ADR-0039/R2 does not
tolerate, so this is not optional polish.

(2) `_retained_bitmap_bytes` CANNOT SEE A BITMAP REACHED THROUGH NUMPY, behind
an `@lru_cache`, on a `Test*` class attribute, or nested deeper than one
container level. `_bitmap_bytes(np.asarray(page))` is 0 while `arr.nbytes` is
25,245,000, and a numpy page array is exactly what band's `_scan`/`_set_once`
produce. CARD-218 narrowed its control's claim to the module-level
accumulators it really walks and declared all four channels rather than
widening the instrument -- deliberately, because round 6 had no review left
after it. When the shared home is built WITH a review in front of it, widen the
walk over numpy and `functools._lru_cache_wrapper` via `gc.get_referents`
(stdlib, ADR-0006/R1 untouched) and derive the bound rather than asserting a
threshold. Note before you do: band's two pre-existing caches hold 25,192,439 B
= 0.9979 page bitmaps, so a `< one page bitmap` bound CANNOT survive the
widening -- it becomes a measured allowance held to an equality plus a strict
bound on everything else. That retention is pre-existing (identical at
c7cca514) and backlogged separately; do not let this card absorb it. -->
**Review score:** —
**Started:** 2026-10-24
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

## [DISPATCH 2026-10-24 — wave 57, orchestrator]

Fork point **`808cf51f`** (main, CARD-218 closed). Branch
`card/219-assert-the-plan-not-the-pixels`, worktree
`../PythonProject4-card-219`. Nothing else in progress; no full-suite lock held.

### 1. The dependency override, and what it actually costs

`Depends on:` names six cards. **CARD-217, CARD-205, CARD-206 are `done`;
CARD-207, CARD-208, CARD-209 are `ready` and undispatched.** The owner
dispatched this card anyway — the same standing scheduling override that put
CARD-218 into wave 56 ("we can take 218 and 219 to work", then "dispatch 219").
Recorded here rather than left implicit, because unlike CARD-218's override this
one has a measured price and it is paid in two specific places:

| ready sibling | file it shares with this card | measured | why it is not merely a merge conflict |
|---|---|---|---|
| CARD-209 | `tests/test_book_solved_answer_key.py` | 4.33 s / 67 tests | CARD-209 **changes the answer-section page arithmetic** (wide-but-short solutions pack 3 to a page). That arithmetic is exactly what a positional conversion here would assert, so the conversion would be rewritten by 209, not merged with it. |
| CARD-209 | `tests/helpers/book_corpus.py` | 0.00 s | declared `conflict.hotspots` entry; 209 edits it. |
| CARD-208 | `tests/property/test_book_pdf_geometry.py` | **51.82 s / 4 tests** | CARD-208 **changes `layout.py`** (printed clue numbers in ruled boxes) — the geometry this file asserts. |

**Decision: all three are fenced out of this card.** The first two cost 4.33 s
and are an easy call. **The third is not**, and is stated plainly below because
it is the biggest single number on this card.

### 2. The card is aimed at a file it does not declare, and that file is the prize

The `Re-pointed 2026-10-15` section says "this card is no longer the biggest
prize" and sends it to **`tests/property/test_book_pdf_geometry.py`, 48.66 s in
four tests** — "the densest spot in the suite and exactly the shape this card
exists for". That figure is **live**: recomputed from
`suite-durations-20261023.txt` it is **51.82 s in 4 tests = 3.63 % of the suite
at 12,955 ms/test**, the two largest being
`test_PropertyTest_BookPdf_MirroredMarginsCentreDrawingForEveryParity_pdf_pages`
(21.11 s) and `test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages`
(20.45 s) — both *geometric* claims paid for in rendered pixels, i.e. branch two
of this card's own classification.

**That file is not in this card's `Touches:` line.** A card re-pointed at a file
it never declared is a card whose scope fence and whose plan disagree, and this
board's `scope_gate: on` resolves that disagreement mechanically and expensively:
a diff that covers a ready sibling's `Touches` **escalates to the decompose
station** on cycle 1. Taking the 51.82 s here buys an escalation to be told what
is already written down.

So it is **left for a successor cut after CARD-208 lands**, and the owner has a
scheduling fact to act on: *the largest prize in CARD-219's subject is behind
CARD-208, and CARD-208 is `ready` and undispatched.* Dispatching 208 unblocks
more of this card's value than anything inside this card does.

### 3. The premise, recomputed before a line is converted — the CARD-218 lesson applied

From `suite-durations-20261023.txt`, parsed from its own
`<secs>s <phase> <nodeid>` records. Attributed total **1426.16 s over 8981
tests** → suite mean **158.8 ms/test**; phase split **setup 6.79 % / call
91.79 % / teardown 1.42 %**. (The total and the phase split reproduce CARD-218's
recorded figures exactly, which is how the parse below was caught being wrong —
see the correction note at the end of this section.)

| | secs | tests | % suite | ms/test |
|---|---|---|---|---|
| the 8 declared `Touches:` files | 54.82 | 326 | 3.84 % | 168.2 |
| **in scope after the fence (6 files)** | **50.49** | **259** | **3.54 %** | **194.9** |
| `tests/test_book_toc.py` | 16.76 | 53 | 1.18 % | 316.2 |
| `tests/property/test_book_export_interior.py` | 17.71 | 3 | 1.24 % | 5903.3 |
| `tests/test_book_finalise_gutter.py` | 7.47 | 126 | 0.52 % | 59.3 |
| `tests/test_book_pdf_two_up.py` | 4.15 | 45 | 0.29 % | 92.2 |
| `tests/test_book_pdf_levels.py` | 2.50 | 15 | 0.18 % | 166.7 |
| `tests/test_book_page_numbers.py` | 1.90 | 17 | 0.13 % | 111.8 |

**Two files hold 34.47 s of the 50.49 s — 68.3 %. The other four are 16.02 s
over 203 tests = 78.9 ms/test, half the suite mean.** Those four are not worth a
conversion round on cost grounds and the round is authorised to say so; CARD-218
closed on exactly this shape and both of its review cycles endorsed the closure.

Unlike CARD-218, though, **this card's declared subject is NOT below the suite's
per-test mean** — 168.2 ms against 158.8 — and that is worth stating in the
direction it actually points: the cost is not spread thin over many cheap tests,
it is concentrated in **eight tests** (toc's seven at 1.69–1.81 s and
export_interior's one at 16.16 s) that together are **27.34 s, 54 % of the
in-scope total**. A card converting eight tests has a far better churn-per-second
ratio than CARD-218's did. That is the argument for dispatching this at all, and
it is the one the round should test first.

> **Correction, same section, 2026-10-24.** The first version of this table read
> 1413.18 s / 8139 tests / mean 173.6 ms, and said the eight `Touches:` files
> were "below the mean". Both were artefacts of **my own parser**: its node-id
> group was `(\S+)$`, which cannot match a parametrised id **containing a
> space** — and this tree has 842 of them. It silently dropped 842 tests and
> 12.98 s, inflating the suite mean by 9.3 % and **reversing the direction** of
> the only comparison drawn from it. Found by reconciling one file: pytest
> collected 126 ids in `test_book_finalise_gutter.py` where the parse reported
> 124, and the two missing were
> `…test_the_screen_names_the_reason_and_points_to_print_setup[gutter_margin_cm-0.60-book gutter_margin_cm is 0.6 cm, …]`
> and its `trim_width_cm` twin. The corrected parse agrees with the live collect
> exactly (259 = 259) and with CARD-218's committed total to the cent. Recorded
> because it is the wave-50 rule in its own words — *a figure committed to a card
> is a claim and its control is recomputation* — and because the cheap check that
> caught it (collect the files and compare cardinality against the artefact) is
> now a standing step for anything derived from these artefacts.

Where the two real targets are, named so the round does not have to find them:

* **`test_book_toc.py`** — seven tests at 1.69–1.81 s *call* each, **11.18 s of
  the file's 16.76 s (67 %)**, and every one of the seven is a pure positional /
  arithmetic claim by its own name: `test_each_row_points_at_the_page_the_walk_planned`,
  `test_a_hundred_and_fifty_puzzles_take_one_toc_page`,
  `test_the_ranges_tile_the_book_with_no_gap_or_overlap`,
  `test_the_rows_are_exactly_the_books_sections`,
  `test_no_row_names_an_individual_puzzle`,
  `test_kdp_reports_the_same_toc_length_the_export_wrote`,
  `test_the_three_ranges_are_the_cards_own_sample`.
* **`tests/property/test_book_export_interior.py`** — **one test is 16.16 s of
  the file's 17.71 s**: `test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`.
  A parity/page-count claim, i.e. positional. G-3 applies: its corpus minimum is
  not lowered to make it cheap.

### 4. The trap this card walks into by succeeding — `RENDER_HEAVY_SNAPSHOT`

`meta/profiling/rank_durations.py:45` defines the render-heavy set by grepping
eight idioms (`interior\(|solved_puzzle_page|interior_stream|render_pages|puzzle_pages|export_book|create_guide_page|proof_pages`)
over `tests/**/*.py`, and `tests/test_suite_profile.py:482` asserts the live grep
**equal** to the 33-entry `RENDER_HEAVY_SNAPSHOT`. **All six in-scope files are
in that snapshot**, with 9–44 idiom mentions each (two_up 44, toc 21, levels 16,
page_numbers 12, finalise_gutter 10, property/export_interior 9).

Two consequences, in opposite directions, and the round must check both:

1. **A file converted thoroughly enough to lose its last mention drops out of the
   live grep and reds `test_suite_profile.py`.** `page_numbers` (12) and `levels`
   (16) are the plausible ones. The remedy is to update the snapshot in the same
   commit with a restated reason — `rank_durations.py` is **not** in this card's
   `Touches:` and is hereby added for that purpose only.
2. **More likely, the opposite:** the conversion target *is* `interior_stream`,
   which is itself one of the eight idioms — so a converted file keeps its
   snapshot membership while losing its render cost, and the snapshot goes on
   claiming it as render-heavy *cost*. `rank_durations.py:126` already carries
   exactly this note for CARD-251 ("neither mention draws… a share computed from
   this file's whole runtime over-states it"). Record the same for every file
   converted here. **The set is a MENTION grep by construction**; do not read it
   as a cost set after this card.

### 5. The shared helper home — the half of this card that is NOT blocked

The `SHARED CURATION HELPERS` mandate above (nine functions, 53 executable
lines, 8 of 9 byte-identical, duplicated across CARD-218's two files) and its two
open holes are **unblocked by 207/208/209** and carry the review value here:
hole (1) is a **false negative in a default-deny guard**, the one direction
ADR-0039/R2 does not tolerate.

Two constraints the mandate does not state, derived at dispatch:

* **Prefer a new module under `tests/helpers/` over `tests/conftest.py`.** Both
  `tests/conftest.py` and `tests/helpers/book_corpus.py` are declared
  `conflict.hotspots`; `tests/helpers/` is an importable package
  (`tests/helpers/__init__.py` exists) and the nine functions are plain
  module-level helpers, not fixtures, so they need no conftest injection. This
  avoids a hotspot for no loss.
* **The new helper module must not name any of the eight render idioms, in code
  or in a docstring** — `tests/helpers/` is under `tests/`, so a mention there
  *adds* a file to the live grep and reds the same equality from the other side.
  This is the trap CARD-218 designed around by keeping its render counter outside
  `tests/` entirely.
* Importing the shared home from `tests/test_book_puzzle_frame.py` (CARD-208's
  `Touches`) and `tests/test_book_pdf_band.py` (CARD-207's) is **allowed here**
  and expected to raise a scope-gate flag. The adjudication is written in advance
  so cycle 1 rules rather than escalates: the edit is nine function *deletions*
  plus one import line per file, it covers neither sibling's subject (207's band
  header split, 208's ruled clue boxes), and the alternative is a **third copy**
  of the defect this card exists to remove.

### 6. Scope as dispatched

**In:** `tests/test_book_toc.py`, `tests/property/test_book_export_interior.py`,
`tests/test_book_finalise_gutter.py`, `tests/test_book_pdf_two_up.py`,
`tests/test_book_pdf_levels.py`, `tests/test_book_page_numbers.py`,
a new shared-helper module under `tests/helpers/`, the two CARD-218 files for
the de-duplication import only, and `meta/profiling/rank_durations.py` for the
snapshot restatement only.

**Out, with the reason recorded:** `tests/test_book_solved_answer_key.py` and
`tests/helpers/book_corpus.py` (CARD-209), `tests/property/test_book_pdf_geometry.py`
(CARD-208 — and the largest prize on the card), `src/**` (G-5).

### 7. AC-4's baseline, captured at the fork point

`pytest -o addopts='' --collect-only -q` over the six in-scope files at
`808cf51f` collects **259 node ids**: toc 53, property/export_interior 3,
finalise_gutter 126, two_up 45, levels 15, page_numbers 17. Saved sorted to
`/private/tmp/claude-501/-Users-omelnikova-PycharmProjects-PythonProject4/f7b1d54a-8309-4e9b-8cf1-e8633015b556/scratchpad/card-219-nodeids-forkpoint.txt`
and re-derivable at the gate from the fork point. `test_book_finalise_gutter.py`
runs **126 passed, zero skips** solo in 7.72 s, so AC-4's set difference is being
taken over a baseline with no skip ambiguity in it.

Note the `-o addopts=''`: `pyproject.toml:89` already supplies `-q`, a second one
stacks to `-qq`, and `--collect-only -q` then prints **no node ids at all** — a
set difference that silently returns 0.

### 8. The worktree

`../PythonProject4-card-219` at `808cf51f`, with `.venv` symlinked to the main
checkout's so the configured `./.venv/bin/python -m pytest` works verbatim.
Verified: 15 tests collected from `tests/test_book_pdf_levels.py`, matching the
artefact.

### 9. CORRECTION to §2, 2026-10-24, same day — the fenced "prize" is not this card's prize at all

The owner asked whether CARD-208 should run before this card, since §2 above
said the largest prize in CARD-219's subject sits behind it. **I had not read
the four tests when I wrote that. Having read them, the claim is wrong and the
recommendation it implied is withdrawn.**

All four tests in `tests/property/test_book_pdf_geometry.py` render the book and
then **measure the ink**: each calls `generator.interior_pages(...)` and reads
its expectations out of the rendered bitmap through
`drawing_of(page: Image.Image)` (`tests/helpers/page_ink.py:326`), recovering
`drawing.columns/rows/cell/left/top/grid_right/grid_bottom`. Those measurements
are then compared against **`Sheet`** (`:124`), a deliberate *independent
re-implementation* of the page geometry inside the test file — the project's
documented style ("prefer an independent second implementation", CLAUDE.md), the
same precedent as `brute_force_oracle.py`.

So the claim these tests make is **"the ink actually lands where an independent
geometry says it should"**, asserted on pixels, over 220 cases. That is a
**pixel** claim in this card's own taxonomy, and **this card's G-1 protects
exactly this shape**: *"the baseline digest tests, the `pdf_pages` round trips…
are not converted"*. Every one of the four is named `*_pdf_pages` /
`*_two_up_pages`.

Converting them would replace an independent-oracle-against-ink comparison with
a layout-against-layout comparison, discarding the only proof that the renderer
consumes the numbers `compute_layout` returns. **That is a weakening, not a
conversion.** §2's framing — "exactly the shape this card exists for", inherited
from the 2026-10-15 re-pointing and repeated by me without checking — is
withdrawn. **The 51.82 s is expensive; it is not recoverable by this card's
mechanism.** The fence stands, and now for the right reason: not "CARD-208 owns
it" but **"this card's own G-1 forbids it"**.

**And CARD-208 would make the file dearer, not cheaper.** Six of its seven ACs
are pixel claims (clue numbers enclosed by four rules, rule weights following the
grid, both two-up slots, the `(0,)` clue boxed, digits clearing their boxes at
the type floor), and its **G-1 adds a new test to this very file**
(`PropertyTest_BookPdfGeometry_GridUnchangedByClueBoxes`). It adds ink and adds
render-verified tests to the most expensive render-verified file in the suite.

**Where the real saving in that file is**, recorded so the next reader does not
re-derive it: each case calls `interior_pages(...)` for the **whole book** —
`6 + toc_page_count` pages — and measures the drawing on **one** of them. The
other pages are rendered to assert their pixel dimensions ("every page of the
book's PDF is the trim", EC-019). That claim is uniform across page kinds and is
re-asserted 220 times, so **sampling it** (every page for a sample of cases, the
puzzle page for the rest) would preserve its coverage shape and remove the large
majority of the renders without touching a single geometry assertion. That is a
**coverage-narrowing-with-a-named-survivor** move, i.e. **CARD-220's mechanism,
not this card's**, and it is worth a card of its own. If the saving needs the
generator to yield one page without building the book, that is a G-5 finding to
raise, not a change to make in a test-only card.
## Worktree notes — implementation round (2026-10-24, wave 57)

**The worktree's copy of this card had no `[DISPATCH 2026-10-24]` section** (252
lines, ending at the 2026-10-15 re-pointing). Main's copy has it at line 254 of
457. Read from main; the prompt summary and the dispatch agree throughout, so
nothing was guessed.

### 0. The premise, re-measured before a line was converted

Solo, `-o addopts='' -p no:randomly --durations`, fork point `808cf51f`:

| | measured here | artefact figure |
|---|---|---|
| toc + export_interior + levels + page_numbers | 39.13 s / 88 tests | — |
| the seven named toc tests | **11.82 s** (1.61–1.79 s each) | 11.18 s |
| `test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` | **16.69 s** | 16.16 s |
| finalise_gutter + two_up | 11.66 s / 171 tests, **slowest test 0.15 s** | 11.62 s |

So the dispatch's premise reproduces. **Seven of the eight concentrated tests
were worth converting; the eighth was not, and that is a classification
disagreement, recorded in §4.** The other four files are confirmed not worth a
round: no single test in finalise_gutter or two_up exceeds 0.15 s.

### 1. Half B — the shared home

`tests/helpers/shared_fixture_controls.py` (new), as the dispatch preferred:
`tests/helpers/` is already a package, the nine are plain functions rather than
fixtures, and both `tests/conftest.py` and `tests/helpers/book_corpus.py` are
declared `conflict.hotspots`. **0 of the eight render idioms appear in it or in
its control module** (re-derived from `RENDER_API_PATTERN`; see §5).

Two renames were forced by the move and are the only API changes: `__name__`
was a module global in `_consumers_among` and `_refuse_unless_nothing_takes_it_later`,
so the module is now taken from `request.module.__name__` (pytest's own
authority) and passed explicitly to `consumers_among`.

**The edit to the two fenced files** is nine deletions + one aliased import +
three things the card's own mandate forces: the duplication-rationale comment
block (it claimed the copies were deliberate and cross-checked by the comment —
now false), the retention control's body and docstring (hole 2 changes what the
instrument returns), and two stale `:func:` cross-references to the deleted
locals. Two now-unused imports (`hashlib`, `inspect`) went with the nine. The
aliases keep every call site byte-identical.

**The ninth's two remedies are one.** `_refuse_unless_nothing_takes_it_later`
said "move it below them" in band and "move its class to the end of the file"
in frame. One condition, one message: *move this control's class below every
test that takes the fixture.*

**The agreement guard** is `TestSharedControls_TheCopiesCannotComeBack`: it
derives the shared names by introspecting the module, derives the importer set
by parsing every `tests/**/*.py` for the import, and refuses any importer that
also defines one of those names (underscore-stripped, because CARD-218's copies
were private). Non-vacuity is asserted on both sets. Controls: M21/M23 put a
copy back and it reds; M22 is the edge (`_case_of_the_band` must *not* red) and
does not; M20 shows the check is silent when there is nothing to catch.

### 2. Hole 1 — what the denominator now catches, and what it still cannot see

**The framing the dispatch did not state, and it matters.** All four remaining
shapes are **declared-side** under-counts. `item.fixturenames` is pytest's own
*full* closure, so the collected half already sees a transitive, inherited,
nested or `usefixtures` consumer. The damage is to the denominator a default-deny
guard divides by: a selection that omitted such a consumer was not refused.
`getfixturevalue` is the only shape invisible to **both** halves, which is why
it alone can let a late mutating consumer through.

Closed, each with a found-now / missed-by-CARD-218's-reading pair:

| shape | kills | mutant |
|---|---|---|
| through another fixture (transitive closure) | `[transitive]` | M4 |
| inherited from a base class (MRO walk) | `[inherited]` | M1 |
| nested `Test` class (recursion) | `[nested]` | M2 |
| `usefixtures` on function/class/module | `[usefixtures]`, `[module pytestmark]` | M3 |

The closure is resolved **per class, innermost first**, as pytest resolves
names. Resolved flat it would have declared one class's `through()` a consumer
because *another* class's `through(shared)` is — an over-counted denominator,
which reds every whole-file run. M6 is that mutant and it kills.

**Declared bounds.** (a) `request.getfixturevalue` cannot be seen statically;
it is held to zero across every importer instead, and the bound has its own
failing control. (b) A transitive chain whose middle link is defined **outside**
the namespace (a `conftest.py` or plugin fixture) is not closed — it can only
make the set smaller, the collected half does see it, and it is stated in
`_implying_fixtures`. (c) The fixture graph depends on pytest's own fixture
marker, which pytest has already renamed once (`_pytestfixturefunction` →
`_fixture_function_marker` in 9.0). A rename does not raise, it **empties the
graph and thins the denominator**, i.e. it makes the guard pass. Both names are
read, and `TestSharedControls_TheFixtureGraphReadsPytestsOwnMarker` fails rather
than thinning (M5).

**Measured no-op on today's tree**, which is the point: declared = collected =
**22 / 8 / 4** for `pages` / `snowflake_interior` / `page`, exactly CARD-218's
cycle-2 figures, through a different instrument.

### 3. Hole 2 — the derived bound and the allowance it had to admit

`retained_bitmap_bytes` now returns a **split**, walked with `gc.get_referents`
(stdlib; ADR-0006/R1 untouched): `by_name` is everything reachable from a
module-level name *without* entering a cache, at any container depth, through
numpy arrays and through `Test` class attributes; `by_cache` is what is inside
each `@lru_cache` store.

Measured at session end, 2026-10-24, through this instrument:

```
tests/test_book_pdf_band.py    by_name  _SHARED_SNOWFLAKE_DIGEST       256 B  (= 32 x 8)
                               by_cache _set_once              24,435,107 B
                                        _font_bytes               757,076 B
                                        ------------------------------------
                                                               25,192,183 B
tests/test_book_puzzle_frame.py by_name _SHARED_DIGEST                 320 B  (= 32 x 10)
                                by_cache (none; this file has no @lru_cache)
```

**Second-domain corroboration.** CARD-218 recorded the band caches at
25,192,183 B at fork point `c7cca514` and a 25,192,439 B total today. This deep
walk gives 25,192,183 B of cache plus 256 B of digest = 25,192,439 B — to the
byte, from `gc.get_referents` rather than from that card's one-level walk plus
an ad-hoc probe. Frame's 320 B likewise reproduces its recorded figure.

**The bound, derived rather than thresholded.** `sum(by_name) == 32 B x pages
signed` — the same equality as before, now over a walk three channels wider.
The caches are an **exemption**, and it ships with its controls in the same
commit: band asserts `lru_cache_names(globals()) == {"_font_bytes", "_set_once"}`
and `set(by_cache) <= that`; frame asserts both are empty. The allowance asks
**which names**, never how many bytes — `_set_once`'s `currsize` is content- and
selection-dependent, and the class's claim is documented
selection-*independent*, so a byte assertion would red any narrow selection
that left a cache cold. **The 25.19 MB retention itself is pre-existing and is
not touched or "fixed" here.**

Load-bearing in the real files, not only synthetically: M24 parks a page as a
numpy array in band, M25 parks one two containers deep in frame, M26 parks one
on a frame `Test` class attribute — each reds exactly
`test_no_module_level_accumulator_retains_a_page_bitmap`, and each was invisible
to CARD-218's walk.

**A defect of mine, found by my own mutants.** The split was first written with
*two* exclusions — `enter_caches=False` and a skip of the cache names — and each
made the other unnecessary, so M11 and M11b both **survived**. Neither was
load-bearing; the pair was. The name skip is gone, and M11c now kills in three
cells including band's real control. This is the CARD-225 shape caught before
hand-back rather than after.

### 4. Half A — per file

**`tests/test_book_toc.py` — seven converted, all seven of the dispatch's.**

| node id (class::test) | claim | reads instead |
|---|---|---|
| `TestBookToc_ListsSectionsNotPuzzles::test_the_rows_are_exactly_the_books_sections` | row labels/order | `_planned_rows` |
| `TestBookToc_ListsSectionsNotPuzzles::test_no_row_names_an_individual_puzzle` | row labels | `_planned_rows` |
| `TestBookToc_PageNumbersMatchTheWalk::test_each_row_points_at_the_page_the_walk_planned` | row page numbers | `_planned_rows` + `InteriorStream` counts |
| `TestBookToc_RangeRowsFollowTheLevelRuns::test_the_three_ranges_are_the_cards_own_sample` | range labels | `_planned_rows` |
| `TestBookToc_RangeRowsFollowTheLevelRuns::test_the_ranges_tile_the_book_with_no_gap_or_overlap` | range labels parsed back | `_planned_rows` |
| `TestBookToc_KdpAgreesWithTheExportedCount::test_a_hundred_and_fifty_puzzles_take_one_toc_page` | one page, eight rows | `toc_page_count` + `measured_toc_page_count` |
| `TestBookToc_KdpAgreesWithTheExportedCount::test_kdp_reports_the_same_toc_length_the_export_wrote` | TOC length | `SectionPlan.toc_page_count` |

Two helpers added: `_planned_rows` (`section_plan` + `structural_toc_entries`,
both pure) and `_solutions_divider_page`, which replaces a five-term formula
that three tests in this file each spelled out inline.

**The one conversion that could have gone wrong silently.** A plan reading has
to *supply* the solutions page to `structural_toc_entries`, so comparing the
solutions row back against that same term asserts nothing — AC-6's tautology
reached from the positional side. It is compared against
`page_count - answer_page_count` off `InteriorStream`'s own counts instead (the
last page that is not an answer page is the divider that opens them): two pure
derivations sharing no term. M17b (off-by-one in `interior_page_count`) reds it.

**Measured delta, interleaved A,B,A,B,A,B, both arms 53 passed / 0 skips:**

- **page bitmaps allocated at trim size (2550x3300): 2712 → 556, −2156 (−79.5 %).**
  Identical integer on all three runs of each arm — a counter, not a stopwatch.
  Secondary counter, all `Image.new` calls: 3953 → 1503.
- wall clock, raw: base `[19.67, 17.97, 18.03]` → min **17.97** median **18.03**;
  converted `[7.21, 6.43, 7.21]` → min **6.43** median **7.21**. Median delta
  **−10.82 s (−60 %)**.

**AC-3, the surviving plan-to-pixel tie in this file:**
`tests/test_book_toc.py::TestBookToc_PageNumbersSurviveTheTitlePage::test_each_range_row_points_at_its_own_levels_divider`
(and its three classmates, `…test_the_guide_row_points_at_the_guides_first_page`,
`…test_the_solutions_row_points_at_the_solutions_divider`,
`…test_the_comparison_would_have_caught_a_one_page_drift`). They render the whole
book and compare the page at each row's own number against an independently
drawn page. **This is not ceremony: M15 (off-by-one in `interior_stream`'s
`first_answer_page`) is caught by those tests and by
`…test_the_named_pages_really_are_those_pages`, and by nothing else — the plan
cross-checks do not see it, because `page_count` does not read
`first_answer_page`.** A file whose every test had been converted would have
lost that. `_rows_of` (the spy on `create_toc_page`) also survives at 13 call
sites, so "the rows the drawing was handed" is still observed.

**`tests/property/test_book_export_interior.py` — classified PIXEL, left
rendering. This is a disagreement with the dispatch** (§3 there calls
`test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` "a
parity/page-count claim, i.e. positional"). Read whole, its 16.69 s buys mostly
pixel claims, on 28 cases through four real export routes: `same_page` against
the cover, `np.asarray(...).min() == 255` on the blank title page, `same_page`
against an independently built guide page, "no interior page is the cover" on
every page, leftmost-ink millimetre measurements per parity for single and
two-up pages, and per-column ink scans on packed answer pages. Its positional
assertions — `len(interior) == expected_count`,
`pdf_page_count(interior_bytes) == expected_count`, and the Finalise figures —
are *deliberately* taken from the written PDF: EC-034 is "the page count
Finalise checks equals the interior PDF's **own** page count", and reading it
off the plan would delete the claim rather than convert it. G-3 was never in
play: no corpus minimum was touched.

**`tests/test_book_finalise_gutter.py`, `test_book_pdf_two_up.py`,
`test_book_pdf_levels.py`, `test_book_page_numbers.py` — not converted, on
cost.** 171 + 32 tests, 11.66 s + 4.56 s, and the **slowest single test in any
of them is 0.15 s** (finalise_gutter/two_up) / 0.71 s (page_numbers) / 0.26 s
(levels). There is no concentration left to convert; a round over them is churn.
Same reasoning CARD-218 closed on, and both of its cycles endorsed.

### 5. `RENDER_HEAVY_SNAPSHOT` — checked in all three directions, no restatement

1. **A file losing its last mention:** did not happen. `test_book_toc.py` has
   **25** mentions (`interior_stream`, `create_guide_page`) against the
   dispatch's 21 — it *gained* some, because the conversion names
   `interior_stream` in prose and calls it once for its counts.
2. **Membership kept, cost lost:** this is the live one, and the note is
   recorded at `meta/profiling/rank_durations.py`, beside the
   `tests/test_book_toc.py` entry, with the 2712 → 556 figure. Nothing else in
   that file changed; the snapshot list is byte-identical.
3. **A new file adding to the grep:** checked before committing.
   `tests/helpers/shared_fixture_controls.py` and
   `tests/test_shared_fixture_controls.py` have **0** mentions of the eight.

`tests/test_suite_profile.py` runs **405 passed** against the live grep (33
entries, live == snapshot). `tests/test_book_puzzle_frame.py` has 0 mentions and
was never in the set.

### 6. AC-4 and skips

`pytest -o addopts='' --collect-only -q` over the six in-scope files: **259 node
ids, set-identical to the fork point.** Removals 0, additions 0.

Additions elsewhere, each named: **25 node ids in the new
`tests/test_shared_fixture_controls.py`** — `TestSharedControls_TheCopiesCannotComeBack`
(5), `…TheDenominatorSeesEveryConsumerShape` (7: 5 parametrised + 2),
`…TheFixtureGraphReadsPytestsOwnMarker` (2),
`…TheDynamicChannelIsABoundAndNotAGap` (2),
`…TheRetentionWalkSeesEveryChannel` (5: 4 parametrised + 1),
`…TheCacheAllowanceIsAnExemptionWithAControl` (4). No test deleted, renamed,
skipped or merged anywhere (G-2); four tests lost an unused `monkeypatch`
parameter, which changes no node id.

Gate run — six in-scope files + the two CARD-218 files + the new control module
+ `test_suite_profile.py` + `test_cli.py`: **964 passed, 0 failed, 0 skipped**
in 75.17 s. Every skip attributed by name: there are none.

### 7. Mutants

| # | deletes | reds | passes |
|---|---|---|---|
| M1 | the MRO walk (inherited tests) | `[inherited]` | 23 |
| M2 | the nested-class recursion | `[nested]` | 23 |
| M3 | the `usefixtures`/`pytestmark` reading | `[usefixtures]`, `[module pytestmark]` | 22 |
| M4 | the transitive closure | `[transitive]`, `test_one_class_s_helper…` | 22 |
| M5 | pytest 9's fixture-marker name | `test_the_graph_names_the_fixtures…`, `[transitive]`, `test_one_class_s_helper…` | 21 |
| M6 | per-class fixture resolution (resolve flat) | `test_one_class_s_helper…` | 23 |
| M7 | the numpy arm of `bitmap_bytes` | `[numpy array]` | 23 |
| M8 | the `@lru_cache` arm of the walk | `[lru_cache store]`, `test_the_exemption_admits…`, `test_the_two_halves…` | 61 |
| M9 | the `Test`-class arm of the walk | `[Test class attribute]` | 23 |
| M10 | the walk past one level | `[nested two deep]`, `[lru_cache store]`, + 2 | 20 |
| **M11** | the cache-name skip | **SURVIVED — vacuous: `enter_caches=False` made it unnecessary** | 64 |
| **M11b** | `enter_caches=False` (with the skip still there) | **SURVIVED — the skip made it unnecessary** | 65 |
| **M11c** | the exclusion, now one mechanism | band's `test_no_module_level_accumulator…` + 2 controls | 162 |
| **M12a** | the walk's `return []` default | **SURVIVED — a module is still opaque** | 25 |
| **M12b** | `ModuleType` from `_OPAQUE` | **SURVIVED — the default is still `[]`** | 25 |
| **M12c** | both of the above (they are in series) | `test_the_walk_does_not_leave_the_module_s_own_data` | 24 |
| **M16** | the namespace/module agreement guard | **SURVIVED — unfailable before its control existed** | 140 |
| **M16b** | the same, with the control added | `test_a_denominator_read_off_another_module_is_refused` | 164 |
| M20 | the agreement guard's clash check | **SURVIVED — nothing to catch; M21/M23 are its positive controls** | 25 |
| M21 | *adds* `_case_of` back to band | `test_no_importer_defines_its_own_copy…` | 24 |
| M22 | *adds* `_case_of_the_band` (edge, near-miss) | **GREEN, as required** | 25 |
| M23 | *adds* `page_digest` (edge, no underscore) | `test_no_importer_defines_its_own_copy…` | 24 |
| M24 | *adds* a numpy page at band module level | band's `test_no_module_level_accumulator…` | 39 |
| M25 | *adds* a page two containers deep in frame | frame's `test_no_module_level_accumulator…` | 99 |
| M26 | *adds* a page on a frame `Test` class attribute | frame's `test_no_module_level_accumulator…` | 99 |
| M13 | `_toc_entries_per_page(...) - 1` | 1 cell, **not a converted test** — too weak to move a 1-page TOC either before or after conversion | 52 |
| M14 | off-by-one in the TOC range label | 8 cells, **3 of them converted tests** | 45 |
| M15 | off-by-one in `first_answer_page` | 3 cells, **all rendering tests** — see AC-3 above | 50 |
| **M17** | a default on `interior_page_count`'s parameter | **SURVIVED — my mutant changed no arithmetic** | 53 |
| **M17b** | off-by-one in `interior_page_count`'s return | 15 cells, incl. `test_each_row_points_at_the_page_the_walk_planned` | 34 |
| M18 | `_toc_entries_per_page` → 1 row per page | 6 cells, **both converted KDP tests** | 47 |
| M19 | `starts_group` on a level heading | 3 cells | 50 |

All `src/**` mutants were applied to a copy-restored tree and reverted; `src/`
is untouched in the commit (G-5). Mutants M13 and M17 are recorded as *failed
mutants of mine*, not as coverage gaps.

### 8. Findings raised rather than fixed

- **G-5 / `InteriorStream` does not expose the TOC rows.** `interior_stream`
  computes `toc_entries` and `first_answer_page` locally and carries neither on
  the returned `InteriorStream`. A positional claim about the solutions row
  therefore has to re-derive the front-matter sum (which is why three tests in
  this file had it inline) or cross-check through `page_count -
  answer_page_count` as this round now does. Exposing `toc_entries` and
  `first_answer_page` on `InteriorStream` would make the claim direct. Not
  changed here.
- **An over-stated docstring in `test_the_named_pages_really_are_those_pages`**
  (pre-existing, left alone): it says "the walk is replayed page by page and
  each named position is checked against what was actually yielded there", and
  the body builds its `kind_of` map from `section_plan`, never from a yielded
  page. The real drawn-page comparison is
  `TestBookToc_PageNumbersSurviveTheTitlePage`'s. Left for CARD-220's pass over
  this file rather than widening this diff.
- **The two per-file `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
  tests are now redundant** with the shared home's
  `test_no_importer_reaches_for_a_fixture_at_run_time`, which covers every
  importer. G-2 forbids deleting them and they are harmless; CARD-220's subject.

## [FIX PRE-GATE on `6677cbf0` — 2026-10-24, orchestrator] PASSED WITH ONE OPEN FINDING

Verdict stated that way on purpose. CARD-218's pre-gate was certified a flat
PASSED while one measurement was routed to the cycle instead of taken, and that
was accepted afterwards as the wrong verdict. Everything below reproduced; one
thing did not, and it is a **real loss of coverage in a converted test**, so the
verdict carries it rather than hiding it behind a green exit code.

### What reproduced, independently

| claim | hand-back | orchestrator | |
|---|---|---|---|
| AC-4 node ids, six in-scope files | 259, set-identical | **259 = 259, 0 removed, 0 added** | ✅ |
| new module | 25 tests | **25 collected** | ✅ |
| gate sweep (11 files) | 964 passed, 0 skipped | **964 passed, 0 failed, 0 skipped**, 81.92 s | ✅ |
| `rank_durations.py` touched for comment only | "snapshot list byte-identical" | **diff is 16 lines, every one an addition; zero deletions** | ✅ |
| the two new modules name no render idiom | 0 | **0 and 0** | ✅ |
| `test_book_toc.py` idiom mentions | 25 | **25** | ✅ |

**The headline integer, re-derived through a different door.** The round counted
`Image.new` at trim size (2712 → 556, −79.5 %). The orchestrator instead wrapped
the book-**producing methods** of `BookPDFGenerator` — a counter on the API, not
on the allocator:

| entry point | base | HEAD | |
|---|---|---|---|
| `solved_puzzle_page` | **1225** | **175** | **−1050, −85.7 %** |
| `create_toc_page` | 80 | 73 | −7 |
| `interior_stream` | 34 | 28 | −6 |
| `puzzle_pages` | 106 | **109** | **+3 — see the open question below** |

Two instruments, two doors, same direction and the same order of magnitude. The
dominant term is `solved_puzzle_page` at 1225 calls, which no figure on this card
had named before: **the TOC file's cost was answer-page rendering**, and that is
what the conversion removed.

**Wall clock, re-measured interleaved (base, conv, base, conv, base, conv):**
base `17.86 / 18.72 / 17.36` → median **17.86 s**; converted `5.65 / 6.21 / 5.57`
→ median **5.65 s**. **Median delta −12.21 s, −68.4 %** — larger than the round's
own −10.82 s. Base spread 1.36 s = 7.6 % of median, so the effect is **nine
spreads wide**. (Contrast CARD-218, whose −0.74 s was roughly one spread. That
card's claim needed the integer; this one's does not, and has it anyway.)

**A second instrument that turned out to be blind, recorded so nobody reaches
for it again.** CARD-218 corroborated its render count with the
`datetime.utcnow()` `DeprecationWarning` count. Here it is **490 in both arms**,
unchanged. It is not a contradiction: that warning fires in
`book_manager.py:2301` on a book being written, not on a page being drawn, and
the converted tests still build the same books. **The warning counter measures
book objects, not renders**, and it is a null instrument for this claim.

### The mutants — six, all deletion-shaped, all restored from pristine copies kept OUTSIDE the worktree

| # | what it deletes | cells red | verdict |
|---|---|---|---|
| Q1 | hole 2's numpy widening (`hasattr(value, "dtype")` → never fires, line-count preserving) | 1 — `TestSharedControls_TheRetentionWalkSeesEveryChannel::test_the_channel_is_measured_now_and_was_invisible_before[numpy…]` | ✅ kills, and **only** the numpy parametrisation, which is the branch deleted |
| Q2 | band stores raw pages instead of digests | 2 — `test_no_module_level_accumulator_retains_a_page_bitmap`, `test_the_shared_pages_are_what_the_fixture_drew` | ✅ kills, in the **real** file |
| Q3 | hole 1: a late band consumer takes the shared fixture via `request.getfixturevalue` | 2 — band's own `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue` **and** `TestSharedControls_TheCopiesCannotComeBack::test_no_importer_reaches_for_a_fixture_at_run_time` | ✅ kills **twice**. This is CARD-218 cycle 2's exact finding; it is now caught in two independent places |
| Q4 | the agreement guard: a third copy of `_case_of` put back into band | 1 — `test_no_importer_defines_its_own_copy_of_a_shared_helper` | ✅ kills |
| Q5 | vacuity: `_importers()` returns empty | 1 — `test_the_importer_set_is_not_empty` | ✅ kills — the non-vacuity control is not decorative |
| Q6 | **src**: off-by-one in `interior_stream`'s `first_answer_page` (`:6718`) | **3 on HEAD, 4 on base** | ⚠️ **the finding** |

Q1–Q5 are the `src/`-free half and they are clean. Both CARD-218 holes are
closed, each with a control that fails when its mechanism is deleted, and the
agreement guard and its vacuity control both bite.

### THE OPEN FINDING — one converted test lost a defect it used to catch

Q6 injects an off-by-one into `first_answer_page` and the two arms disagree:

* **base tree (fork point): 4 cells red** — `TestBookToc_PageNumbersMatchTheWalk::{test_each_row_points_at_the_page_the_walk_planned, test_the_named_pages_really_are_those_pages}` and `TestBookToc_PageNumbersSurviveTheTitlePage::{test_the_solutions_row_points_at_the_solutions_divider, test_the_comparison_would_have_caught_a_one_page_drift}`
* **converted tree: 3 cells red** — the same, **minus** `test_each_row_points_at_the_page_the_walk_planned`

**That lost cell is one of the seven converted tests.** Before this card it caught
an off-by-one in `first_answer_page`; after the conversion it does not.

**Two things follow, and only the second is a defect.**

1. **No defect escapes.** The mutant is still killed, in 3 cells, two of them in
   `TestBookToc_PageNumbersSurviveTheTitlePage` — precisely the surviving
   rendering class the round nominated for AC-3. So the round's claim that the
   tie test "is not ceremony" is **confirmed by measurement, and it is the thing
   standing between this conversion and a silent coverage hole.** That is the
   strongest evidence on this card that AC-3 was worth having.
2. **The converted test's docstring over-claims.** It ends *"Both are pure and
   neither draws; **an off-by-one in either reds this.**"* My off-by-one does not
   red it. The sentence is true of the two terms it names —
   `page_count` and `answer_page_count` — and **false of the third term the test
   used to cover**, because neither of those two reads `first_answer_page`. A
   narrowed claim written as a general one is the ADR-0039/R1 shape this board
   gates on, and AC-1's *"it fails if the plan changes"* is false for this test
   on this plan change.

**Not fixed by me, and routed to cycle 1 with the measurement.** The remedy is
cheap and is the round's own G-5 finding read forwards: `InteriorStream` carries
neither `toc_entries` nor `first_answer_page`, which is exactly why the test
could not cross-check that term. So either the claim narrows to the terms it
covers and names the tie test for the rest, or `first_answer_page` gets exposed
on `InteriorStream` — and that is a `src/` change this card may not make.

### Two defects of my own, both in the brief, both found by the round

1. **I classified `tests/property/test_book_export_interior.py` as positional. It
   is pixel, and the round was right to refuse it.** Verified line by line:
   `:652` `same_page(cover_page, expected_cover)`, `:731`
   `np.asarray(interior[0].convert("L")).min() == 255`, `:734` `same_page` against
   an independently built guide page, `:736` "no page is the cover" on every page,
   `:848` `np.asarray(crop.convert("L")) < 128` leftmost-ink scans. Its positional
   assertions are `len(interior)`, `pdf_page_count(interior_bytes)` and the
   Finalise figures — and `pdf_page_count` reads the **written PDF** deliberately,
   because EC-034 is *"the count Finalise checks equals the interior PDF's own
   count"*. Reading that off the plan **deletes** the claim rather than converting
   it. G-1 covered this file all along and my brief pointed at it anyway.
2. **So the premise figure I put in the brief and on this card is wrong in a way
   that would have mis-sized a successor.** I wrote "eight concentrated tests =
   27.34 s = 54 % of the in-scope total". **16.16 s of that 27.34 s — 59 % — was
   in a test that must not be converted.** The honest figure is **seven tests,
   11.18 s (the round measured 11.82 s)**, and what the round actually removed is
   **≈12.2 s of the 50.49 s in scope (24 %), 0.86 % of the suite.** Corrected
   here, in §3's terms, at the round's own request.

### Open questions for cycle 1 (not findings — measurements I did not finish)

* **`puzzle_pages` rose 106 → 109.** A render-named entry point moving *up* is
  the opposite direction to this card's claim. It may be a plan-only method, it
  may be test ordering; I did not attribute it, and three calls cannot account
  for any of the saving. Attribute it.
* The two per-file `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
  tests are now genuinely redundant — **Q3 reds both of them and the shared
  one.** The round flagged this and G-2 forbids deleting them. Confirmed, harmless,
  CARD-220's.
* The round's byte agreement (`25,192,183 + 256 = 25,192,439`, CARD-218's
  hand-measured total) was **not** re-derived by me. It is a second-domain
  agreement to the byte and I accepted it on the round's measurement.

### Housekeeping

* **The worktree's card copy is stale and my brief sent the round to it.** `meta/`
  is never committed from a worktree, so the worktree's `CARD-219.md` is frozen at
  the fork point and has no `[DISPATCH]` section. The round noticed, read main's
  copy, and lost nothing — but the brief was wrong and the next one should point
  at main's path explicitly.
* **Ten untracked files sit at the worktree root** (`admin.css`, `solver.js`,
  `test_book_pdf_band.py`, `test_book_puzzle_frame.py`, `test_puzzle_editor_ui.py`,
  `test_puzzle_solver_{clues,fifth_rule,phone,zoom}.py`), all stamped 07:51, none
  in main, three of them differing from their `tests/` counterparts including one
  this card never touched. **Not the card's**: not staged, not in `6677cbf0`'s six
  files, and `pyproject.toml:88` sets `testpaths = ["tests"]` so they cannot be
  collected even by a bare `pytest`. Left in place rather than deleted — they are
  not mine to remove — and flagged to the owner.

## [CYCLE 1 ADJUDICATION — 2026-10-24, orchestrator] 6.0, NOT CERTIFIED, all four gating findings reproduced

Report: `meta/review/20261024T053055Z-CARD-219-cycle1.yml` (synced to main; passes
`yaml.safe_load`; 6 findings, 5 gating, score 6, `certified: false`).
**Aggregate round counter: 3 of 6** — implementation (1), fix pre-gate (2),
cycle 1 (3). So **fix round 1 is round 4, its pre-gate 5, and cycle 2 is round
6**: this is the only fix round this card can afford before its last cycle, and
the brief is written accordingly.

**I reproduced every gating finding independently before authorising a round.**
Two of my reproductions came out differently from the reviewer's and both
differences are recorded below, because each one changes what the fix must do.

### F-001 — the retention walk's claim is universal and false. CONFIRMED, and narrowed to the right three shapes.

The reviewer's R1 mutant parked pages in a live file; mine asks the walk directly,
which removes the confounding my first attempt had (see below). One page bitmap
is 25,245,000 B:

| where the page is parked | walk reports | |
|---|---|---|
| instance `__dict__` (plain non-`Test` object attribute) | **0 B** | ** invisible ** |
| `collections.deque` | **0 B** | ** invisible ** |
| `@lru_cache` bound **inside a list** (never bound to a name) | **0 B** | ** invisible ** |
| `Test*` class attribute | 25,245,000 B | SEEN ✅ |
| plain list (the documented shape) | 25,245,000 B | SEEN ✅ |

So **three further hiding places hold 75,735,000 B = 3.00 page bitmaps invisibly**
— and the two channels the card *declared* are genuinely closed. **This is an
over-claim, not a broken channel**, which is the ADR-0039/R1 family this board
has gated on fifteen times running. The false sentences are `Retention.by_name`'s
*"however deeply nested and whatever form the pixels are in"* and
`tests/test_book_pdf_band.py:1789`'s *"a page parked anywhere that is not a
cache… reds"*.

**My first attempt at this mutant was confounded and I am recording it as the
trap it is.** I appended a probe class that took `snowflake_interior`, which made
it a *new consumer* — so the ordering and denominator guards fired (2 cells) and
the retention control never got to be the thing under test. The identical trap
bit me on CARD-218's Q5. **A mutant aimed at one guard must not also trip the
guard in front of it**; asking the mechanism directly, outside pytest, is the
cheap way out.

### F-002 — the denominator cannot see an `autouse` fixture. CONFIRMED, and it is worse than the finding says in one direction and milder in another.

Reproduced twice, in a probe module kept outside `tests/`:

1. **The denominator empties.** With `@pytest.fixture(autouse=True) def _always(shared)`, pytest's own `request.fixturenames` contains `shared` (**True**) while `declared_consumers(globals(), "shared")` returns **`[]`**.
2. **And therefore the DECLINE never fires.** Narrowed to the control alone — `-k one_render_served`, **1 passed, 2 deselected** — the control **passed** with `_RENDERS=[1]` and no refusal. That is **CARD-218 cycle 1's F-002 defect exactly**, the one this whole default-deny mechanism was built to prevent, reappearing in the **pass** direction, which is the direction ADR-0039/R2 does not tolerate.

**Milder than stated, in one respect that matters for the fix.** `autouse` is live
in four modules — `test_admin_serving.py`, `test_admin_auth.py`,
`test_card_037_upload_retry.py`, `test_card_044_preview_after_submit.py` — and
**none of them is band or frame**, and **`tests/conftest.py` injects no autouse
fixture**. So the shipped controls are not false *today*. What is false today is
the module's **declared bound** at `:301`, which enumerates what the guard cannot
see and does not mention autouse. The defect is live as a **claim**; the false
negative is **latent**, and it arms itself the day anyone adds an autouse fixture
to either file — or one to `tests/conftest.py`, which would arm it for every
module at once.

The remedy is executable and the reviewer verified the handle: the fixture marker
the module **already reads** carries `.autouse`. The second half —
`python_functions` is unconfigured so pytest's default `test` *prefix* collects
`def testCamelCase(self, shared)`, which a hard-coded `test_` misses — is the same
ADR-0039/R2 point: `config.getini` is an enumerable authority and the guard
hand-wrote the prefix instead.

### F-003 — the agreement guard is blind to an alias. CONFIRMED, and my first mutant was weaker than the reviewer's.

The card's headline Half-B deliverable is the guard CARD-218's two copies never
had. It reads only `tree.body` and only `FunctionDef`/`AsyncFunctionDef`/
`ClassDef` — the one spelling it was written from. All three of its own controls
(M21/M22/M23) are `def` shapes.

* My first attempt bound an alias to a **broken** stub (a constant digest) →
  1 cell red, but in `test_no_module_level_accumulator_retains_a_page_bitmap`,
  an unrelated control tripping on the broken semantics. **The agreement guard
  itself stayed green.**
* Re-run with a **faithful** copy — `def _probe_own_digest(page): return hashlib.sha256(page.tobytes()).digest()` then `_page_digest = _probe_own_digest`, so every call site uses the third copy → **65 passed, 0 cells.**

**A byte-for-byte third copy of a shared helper ships completely green.** The
reviewer's mutant was the sharper one and the lesson is mine: *a mutant that also
breaks behaviour cannot tell you whether the guard saw the structure.*

### F-004 — a sibling of the pre-gate's own finding, in the same file. CONFIRMED to the cell.

`M29`, line-count preserving at `book_pdf_generator.py:6923`
(`range(toc_page_count)` → `range(toc_page_count + 1)`, so the walk yields one
TOC page more than planned): **base 21 red cells, HEAD 14** (4 errors in **both**
arms, so not introduced here). **The 7 lost cells are exactly the seven converted
tests.**

**Six of those seven losses are the fair price of a plan assertion and are not
defects** — a test that reads the plan cannot witness a drawn count, which is
what conversion *means*, and the mutant is still killed **14 times**. The defect
is the one test that **claimed** to have kept the tie:
`test_a_hundred_and_fifty_puzzles_take_one_toc_page` says *"the same call at the
same two arguments. The two agreeing is what the drawn count used to witness"* —
and it is not, because `section_plan` (`src:6450`) makes the same call, so the
pair can only witness `structural_toc_entry_count` against
`structural_toc_entries` and `dpi == DPI`.

So this card now has **two** false tie-claims of the identical shape — F-004's and
the pre-gate's F-006 — which is one defect **class**, not two incidents. Per the
wave-50 rule, the fix brief names the class and not the two instances.

### F-006 — the pre-gate's open finding: I accept the reviewer's ruling, and it found the mechanism I had missed

My pre-gate said the remedy was to narrow the claim. The reviewer agrees that
narrowing satisfies AC-1 **but only with a fence**, and supplies the part I did
not have: `_planned_rows` must *supply* the solutions page, and it supplies
`_solutions_divider_page(decided)` — **a test-side re-spelling of production's
`first_answer_page`** (`src:6718`, used by production at `:6786` to build the same
rows). The row therefore carries a test-authored number, and **that**, not the
docstring, is why Q6 escapes. The term is carried on no returned value, so it is
unreachable from any pure surface — which is the round's own G-5 finding read
forwards.

Accepted in full, including the fence and including its scoping: exposing
`toc_entries`/`first_answer_page` on `InteriorStream` is **a successor card to
CARD-219, not CARD-220's** (CARD-220 has no `src` mandate), and CARD-220 must be
told which three tests are the sole carriers **because it is chartered to prune
this very file for redundancy**.

### F-005 — minor, accepted on inspection

Band's `set(retained.by_cache) <= _lru_cache_names(globals())` cannot fail by
construction: both sides come from `_caches_of` on the same namespace. Its sibling
conjunct `caches == {…}` *is* failable and did bite in the reviewer's spy arm. This
is the **same unfailable-conjunct shape CARD-218 cycle 2 deleted** — and this card
wrote a test to prevent it, then shipped one. Delete the conjunct, keep the
sibling.

### Both of my open questions closed by the reviewer, and one of them beautifully

* **`puzzle_pages` 106 → 109: fully attributed, and it is not a render.**
  `puzzle_pages` (`src:6040`) returns `List[PuzzlePagePlan]` — pure, draws
  nothing — and is called once per level from `puzzle_section`. On the single node
  id `test_each_row_points_at_the_page_the_walk_planned`: base `section_plan=3,
  puzzle_pages=9, create_toc_page=1, solved_puzzle_page=150` → HEAD
  `section_plan=4, puzzle_pages=12, create_toc_page=0, solved_puzzle_page=0`. The
  converted test makes **one more `section_plan` call**, and on a three-level book
  that is **exactly +3 `puzzle_pages`**. The whole tree-wide delta, from one test,
  with no render in it. My concern is answered and the entry point is misleadingly
  named rather than mis-measured.
* **The 25,192,439 B byte-agreement — the one figure on this card nobody had
  re-derived — is now verified in a second domain with no `gc` in it at all:** a
  call-time recorder on `_set_once` summing each returned array's own `.nbytes`
  gives 666 distinct keys at currsize 666 = **24,435,107 B**, and
  `len(_font_bytes())` = **757,076 B**. All four figures hold to the byte.

### What the reviewer did not check, carried forward rather than dropped

`mutation_check` Step 8f was **`deferred(cost)`** — correct per the cost ladder,
since four findings rewrite the bodies it would certify; it runs in cycle 2. No
per-assertion recording instrument was built, so all cells above are plain-pass:
for R1 we know *neither* retention assert fired, not which would have fired
first. The four declined files were not re-profiled, the eight render idioms were
not independently re-grepped, and **whether `_set_once`'s boolean ink masks are
the right unit for the exemption's 24.4 MB figure was not examined** — that last
one is a live question about what the exemption's number *means* and it goes into
the fix brief.

### Scope gate: NO ESCALATION, and cycle 2 may not re-open it

The reviewer ruled all three extra edit shapes inside the nine-helper subject,
with hunk evidence (band `:48/:79/:252/:1594-1999`, frame
`:89/:130/:905/:3095-3477` — the docstring/import block, the digest helper, the
control section). The comment block asserted a now-false claim, so leaving it
would itself have been the ADR-0039/R1 defect; the control-body change is forced
by `retained_bitmap_bytes` returning a `Retention` split, which this card's own
mandate assigns here; the added `_lru_cache_names` assertion is the ADR-0039/R3
control the exemption requires. Nothing touches CARD-207's band-header split or
CARD-208's clue boxes. **Agreed and recorded as settled.**
## Worktree notes — fix round 1 (2026-10-24, wave 57)

Cycle 1's five gating findings, in the brief's order. Every mechanism named in a
claim has a mutant that **deletes** it below, and the two that could not be
killed are recorded as mine rather than hidden.

### FIX 1 — F-003, the agreement guard was blind to an alias

`test_no_importer_defines_its_own_copy_of_a_shared_helper` now reads
`_locally_defined_names(source)`: every `def`/`async def`/`class` **and** every
`ast.Name` in a store context, at **any** depth, which is the grammar's own
notion of a binding and therefore covers `x = ...`, `x: T = ...`, `x += ...`,
`for x in ...`, `with ... as x` and `(x := ...)` without listing statement
kinds. An `import ... as` binding is deliberately *not* a definition (it is an
`ast.alias`, not a stored `Name`) — it is the spelling this module asks
importers to use, nine names each in band and frame.

The controls are the spellings the guard was **not** written from (ADR-0039/R1),
paired against `_as_the_guard_first_read_it`, which is CARD-219's first reading
written out again as the missed-WITHOUT arm:

| row | caught now | missed before |
|---|---|---|
| faithful alias (cycle 1's F-003 mutant verbatim) | ✅ | ✅ |
| annotated alias (`_case_of: object = None`) | ✅ | ✅ |
| alias bound in a `try` | ✅ | ✅ |
| alias bound in an `if` | ✅ | ✅ |
| a method of a class | ✅ | ✅ |
| a function inside a function | ✅ | ✅ |

and three at the claim's **edge**, which must stay green in both readings: the
sanctioned import alias, a near miss (`_case_of_the_band`), and an alias to
something that is not a shared helper.

**Depth-blindness has a cost and the docstring states it:** a local variable or
a method that happens to carry a shared helper's name is reported too.
Measured 2026-10-24 over the whole tree: zero such names, and the remedy in the
message (rename it) is cheap.

| # | deletes | reds | passes |
|---|---|---|---|
| A1 | the stored-`Name` arm (assignments) | 4 cells: faithful alias, annotated alias, alias in a try, alias in an if | 47 |
| A2 | the any-depth walk (back to `tree.body`) | **all 6** caught rows | 45 |
| A4 | vacuity: the clash reading reports every name | 3 edge rows + the real-tree guard | 45 |
| **E3** | **cycle 1's F-003 mutant verbatim** — a faithful third copy of `_page_digest` appended to the real band file, every call site using it | `test_no_importer_defines_its_own_copy_of_a_shared_helper` | 90 |

E3 is the one that matters: the same mutation was **65 passed, 0 cells** in
cycle 1 and is now caught, in the real file, with nothing else disturbed.

### FIX 2 — F-002, the denominator could not see an `autouse` fixture

Both halves closed, each with a found-now/missed-before pair:

* `_autouse_fixtures(namespace)` reads `.autouse` off the marker the module
  already reads. An autouse fixture that (transitively) implies the shared
  fixture makes **every test in its scope** a consumer, resolved per class
  (module-level autouse covers the module; a class's own covers that class and
  its nested classes).
* `python_functions` / `python_classes` come from `config.getini` at the guard,
  with `DEFAULT_FUNCTION_PATTERNS`/`DEFAULT_CLASS_PATTERNS` as the fallback for
  callers with no config. pytest's matching is prefix **or** fnmatch, so both
  arms are reproduced; `def testCamelCase(self, shared)` is now in the
  denominator.

| # | deletes | reds | passes |
|---|---|---|---|
| B1 | the `autouse` reading | `[autouse]`, `test_an_autouse_fixture_on_a_class_covers_only_that_class` | 49 |
| B2 | the **guard's** `getini` (fall back to the defaults) | `test_the_guard_itself_reads_the_rules_off_the_config` | 50 |
| B3a | the fnmatch arm of the name matching | `[glob]` parametrisation | 51 |
| B3b | the prefix arm | 12 cells (every shape, both configured arms, the stub guard) | 40 |
| B3c | pytest's glob-character condition on the fnmatch call | **SURVIVED, and the docstring says so** | 52 with the control that could not fail, 51 without it |
| B4 | the patterns argument (hard-code `test_`/`Test`) | `[configured name prefix]`, both configured arms, the stub guard | 46 |

**B3c is the second dead mechanism I found in my own work, and the control I
first wrote for it could not fail either.** I had reasoned that `fnmatch` on a
plain prefix would fold case on this filesystem and over-count the denominator,
wrote a control asserting it does not, and the mutant survived: on POSIX
`os.path.normcase` is the identity (measured), so `fnmatch` with a glob-free
pattern is exact equality and the prefix arm already covers it. pytest's own
reason for the condition is cost, not semantics — its comment says so. The
unfailable control is deleted and the condition stays with "no mutant kills
this" written next to it, because copying pytest's matcher exactly is still
worth more than a matcher of mine that happens to agree.

**B2 is the one worth reading.** Today's tree configures neither option, so a
guard that went back to a hard-coded prefix would behave identically on it and
no run over this tree could tell — the `getini` call was a mechanism no mutant
could kill. `test_the_guard_itself_reads_the_rules_off_the_config` hands the
guard a **stub request** whose config says `check`, in both directions, which is
the only way to put the two apart. Without it I would have shipped a derived-set
claim with no control, which is the CARD-225 shape.

**Still not closed, as four numbered bounds in `declared_consumers`' own
docstring** (the enumeration cycle 1 found incomplete — it did not mention
autouse at all):

1. `request.getfixturevalue` — the fixture name is a run-time expression; held
   to zero across every importer instead, with its own failing control.
2. a transitive chain whose middle link is defined outside the namespace (a
   `conftest.py` or plugin fixture). The collected half does see it.
3. **an `autouse` fixture defined outside the namespace** — a `conftest.py` or
   plugin one. pytest resolves such a fixture's arguments against the
   *requesting* item, so a `conftest.py` autouse fixture taking `pages` would
   make every test in every module a consumer and this reading would not know.
   Measured 2026-10-24: `tests/conftest.py` declares **no** autouse fixture, and
   the four modules in this tree that do (`test_admin_serving.py`,
   `test_admin_auth.py`, `test_card_037_upload_retry.py`,
   `test_card_044_preview_after_submit.py`) declare theirs locally, where bound
   1's arm reads them.
4. a name bound into the namespace later than this reading runs
   (`globals()[name] = ...` after import).

The declared enumeration now matches reality: autouse is listed, in both
directions (closed locally, open through a conftest), and nothing else changed
about what the two halves can see.

### FIX 3 — F-001, the retention walk's claim was universal and false

**First, every universal phrasing is gone.** The three:

1. `Retention.by_name`'s *"anything they reach, however deeply nested and
   whatever form the pixels are in"*;
2. `tests/test_book_pdf_band.py`'s *"a page parked anywhere that is not a
   cache … reds"*;
3. **the third, found as the brief asked:** `tests/test_book_puzzle_frame.py`'s
   class docstring saying the control's subject and *everything this module
   leaves behind* "happen to coincide" — a universal about all retention,
   asserted from one walk plus one depth-8 probe. It now says two instruments
   agree, names their shared blind side, and points at `_step`.

`_step`'s own docstring is the single place the walk's reach is written down:
the edges it follows and the edges it declines.

**Then the widening — and it is smaller than the brief asked for, on purpose.**
The brief said to enter `collections.abc.Collection` and an instance's `vars()`.
I wrote exactly that, and **two of my own mutants survived**:

| # | deletes | verdict |
|---|---|---|
| C6b | `types.FunctionType` from the `_OPAQUE` fence | **SURVIVED** — reading an instance with `vars()` never reaches `__globals__`, so the fence's function entry was dead |
| C8 | the measured-leaf gate (`if bitmap_bytes(value): return []`) | **SURVIVED** — `gc.get_referents` returns `[]` for a numpy view *and* for an object array, so there was no `.base` edge for it to block |

That is the M11/M11b shape this card already paid for once: several spellings of
one exclusion, each making the others unnecessary. So the walk is now **the
collector plus three edits**, and no container type is named anywhere in it:

1. **the fence** — `_OPAQUE` (module, function, method, builtins) is not
   entered. A function's referents include its `__globals__`, and a module *is*
   a namespace.
2. **the exemption** — an `@lru_cache` wrapper is entered on the `by_cache`
   pass, and on the `by_name` pass **only when `namespace` does not name it**,
   because an unnamed cache is nobody's declared allowance. The exemption is by
   object id, not by name: a cache the walk meets inside a container has no
   module-level name, so a name-based skip would have exempted it silently.
3. **classes** — read with `vars()`, dunders excluded, when `python_classes`
   would collect the name or the module being walked defined it.

Everything else is one `gc.get_referents` call. That closes the three channels
cycle 1 measured at 0 B, plus `__slots__` for free, and makes the fence
load-bearing:

| # | deletes | reds | passes |
|---|---|---|---|
| C1 | the collector fallback (every other edge) | **11 cells**: `[lru_cache store]`, `[nested two deep]`, `[deque]`, `[instance attribute]`, `[slotted instance]`, `[unnamed lru_cache]`, 3 exemption controls, **and both real files'** `test_no_module_level_accumulator_retains_a_page_bitmap` | 180 |
| C3 | the routing of an unnamed cache into `by_name` | `[unnamed lru_cache]` | 190 |
| C4 | the exemption itself (enter every cache) | 2 exemption controls + **band's real control** | 188 |
| C5 | the module's-own-class arm | `[a plain class of the module's own]` | 50 |
| C5b | the `python_classes` arm of the class edge | `[Test class attribute]` | 50 |
| C6a | `ModuleType` out of the fence | `test_the_walk_does_not_leave_the_module_s_own_data`, `[an instance holding a module]` | 49 |
| C6b | `FunctionType` out of the fence (**after** the collapse) | **7 cells**, incl. `[a function's own globals]` and three exemption controls | 44 |
| C7 | the declared bound closed (enter every class) | `[an imported class]` — the bound's own control fails when the bound closes | 50 |
| C9 | vacuity: the `_SCALAR` short-circuit | **SURVIVED, and the docstring says so** — the collector reports no referents for those types either, so it is a frontier-length optimisation and not a mechanism. Recorded as dead rather than claimed. |

**The fence, extended as the brief required.** The old
`test_the_walk_does_not_leave_the_module_s_own_data` is unchanged (same node
id), and `test_the_fence_holds_at_each_edge_that_could_leave_it` adds three
arms, one per edge, parametrised rather than three asserts in one body — a
plain pass stops at its first failure, so three arms in one test would make a
surviving mechanism and an unreached assert look identical. Both carriers
really hold a page (a probe module with a page in its namespace; a function
compiled into a globals dict holding one), because pointing them at this module
would have made them **unfailable** — the F-005 shape, avoided by construction
and proved by C6a/C6b/C7 killing one arm each.

**Still not closed, declared in `_step`:**

* a class attribute of an **imported** class whose name no pattern collects
  (edit 3's bound; its own control is `[an imported class]`, which C7 kills);
* anything reachable only through a function, a method or a module (the fence,
  deliberately);
* a numpy array's contents — a view's uncropped `.base` and an object-dtype
  array's elements. **Not a choice but a measured limit:**
  `gc.get_referents` returns `[]` for both, which
  `test_the_bound_on_a_numpy_arrays_contents_is_the_collectors` asserts as the
  premise, so the day numpy changes it, the bound reds and can be closed;
* anything a C extension exposes to neither the collector nor `vars()`.

**Band's and frame's figures are unchanged by the widening**, measured through
the same session-end instrument before and after: band `by_name`
`_SHARED_SNOWFLAKE_DIGEST` 256 B, `by_cache` `_font_bytes` 757,076 B and
`_set_once` 24,435,107 B; frame 320 B and no cache. The collapse to the
collector reproduces all four figures to the byte through a different code
path.

### The open question cycle 1 named and did not answer: the exemption's unit

Answered by measurement, not by argument. At session end on 2026-10-24,
`_set_once`'s 666 cached values are **all `dtype('bool')`** — cropped ink
masks at one byte a **cell**, while a page of this book is 2550x3300 **RGB** at
three bytes a **pixel**. So "0.9979 of a page bitmap", which three docstrings
carried, divided 1-byte cells by 3-byte pixels. Every instance of that ratio is
gone; the figures stay, in the one unit the instrument has — *bytes of image or
array memory*.

**And the figure is not the ceiling it reads like.** Each cached mask is a numpy
**view** of an uncropped mask (`_cropped` is a basic slice), and the 666
distinct bases those views keep alive measure **110,882,067 B — 4.5x the
24,435,107 B reported**. The walk cannot see them (the collector offers no
edge), so this is a declared bound with an asserted premise rather than a
silent one. The exemption's *mechanism* is untouched, as the brief required;
only what its number means is now written down.

### FIX 4 — F-004 + F-006, one class: a converted test claiming a tie it does not have

**Every one of the seven converted tests was checked, not the two cycle 1
found.** Five made no tie claim and now say which terms they cover; two
claimed a tie they do not have and are narrowed:

| converted test | claim before | claim after |
|---|---|---|
| `…MatchTheWalk::test_each_row_points_at_the_page_the_walk_planned` | "Both are pure and neither draws; **an off-by-one in either reds this**." | names the two terms it covers (`page_count`, `answer_page_count`), states that the third term the pre-conversion test covered — `first_answer_page` — leaves it **green**, with the 4-vs-3 measurement and the mechanical reason |
| `…KdpAgrees::test_a_hundred_and_fifty_puzzles_take_one_toc_page` | "the same call at the same two arguments. **The two agreeing is what the drawn count used to witness**" | states that `section_plan` (`src:6450`) makes the same call so the pair is not independent, and narrows the claim to the two unshared terms (`structural_toc_entry_count` against `structural_toc_entries`, and the frame/`dpi`) |
| `…KdpAgrees::test_kdp_reports_the_same_toc_length_the_export_wrote` | "the two totals agreeing is **exactly** the statement that they agree about the TOC" | narrowed to what it is: the two **call sites** (`book_kdp.py:544`, `book_pdf_generator.py:6450`) agree, which is one arithmetic called twice — so it says nothing about whether that arithmetic is right (the second assertion is what does), and "wrote" now means "planned to write" |
| `…ListsSections::test_the_rows_are_exactly_the_books_sections` | — | names `_rows_of`'s eleven tests for the builder/drawing tie and `DRAWN_TIE_CARRIERS` for the plan/pixel one |
| `…ListsSections::test_no_row_names_an_individual_puzzle` | — | same |
| `…RangeRows::test_the_three_ranges_are_the_cards_own_sample` | — | same |
| `…RangeRows::test_the_ranges_tile_the_book_with_no_gap_or_overlap` | — | same |

`_solutions_divider_page` now says in its first sentence that it **re-spells a
production term**, names `first_answer_page` (`src:6718`-`:6720`, used by
production at `:6786`), records 4 cells on base against 3 here, and says why it
is re-spelled rather than read (the term is on no returned value).
`_planned_rows` states the two ties a plan reading gives up.

**The fence, as a test and not as prose.** `DRAWN_TIE_CARRIERS` is a
module-level constant naming the three node ids, and
`tests/test_book_toc.py::test_the_drawn_tie_is_still_carried_here` (the one node
id this round adds to an in-scope file) holds each one to (a) resolving on the
module and (b) still reaching a drawn page by one of
`DRAWN_PAGE_IDIOMS = ("_rows_of", "_same_page", "rendered")`. The second is a
name check and not a proof, and says so, but it reds on the edit that matters.

**Both pairs re-measured, in both arms, with the fork point's own copy of the
file placed by `git show` and `src` restored from a pristine copy kept outside
the worktree:**

| mutant | base (`808cf51f` tests) | HEAD | lost |
|---|---|---|---|
| M29 (`:6923`, `range(toc_page_count + 1)`) | **21 failed + 4 errors** | **14 failed + 4 errors** | exactly the seven converted tests, name for name |
| Q6/M15 (`:6718`, `first_answer_page + 1`) | **4 failed** | **3 failed** | `test_each_row_points_at_the_page_the_walk_planned` |

Cycle 1's figures reproduce to the cell. **One correction to cycle 1's reading:**
under M29 the four `TestBookToc_PageNumbersSurviveTheTitlePage` node ids are
**errors, not failures**, in both arms — their shared rendering fixture raises
before any assertion. An error is a kill and not a pass, but it is not a failure
cell, so of the three carriers two kill M29 by erroring and one
(`test_the_named_pages_really_are_those_pages`) by failing. The brief's phrasing
"the 7 lost are exactly the seven converted tests" is confirmed; "the
`PageNumbersSurviveTheTitlePage` renders are among the 14" would not have been,
and the docstring says what is actually true.

| # | deletes | reds | passes |
|---|---|---|---|
| E4 | a carrier pruned (renamed) away | `test_the_drawn_tie_is_still_carried_here` | 53 |
| E5 | a carrier converted to a plan reading (`_rows_of` → `_planned_rows`) | `test_the_drawn_tie_is_still_carried_here` | 53 |

**Raised, not made (G-5).** `interior_stream` computes `toc_entries` (`:6786`)
and `first_answer_page` (`:6718`) locally and `InteriorStream` carries neither.
Exposing them would make the solutions-row claim direct and would let
`test_each_row_points_at_the_page_the_walk_planned` cover the term it lost. It
is a `src/` change this card may not make, and per cycle 1's ruling it is a
**successor card to CARD-219**, not CARD-220's (which has no `src` mandate).

### FIX 5 — F-005, an unfailable conjunct

Band's `set(retained.by_cache) <= _lru_cache_names(globals())` is deleted: both
sides come from `_caches_of` on the same namespace, so the subset holds by
construction. The failable sibling (`caches == {"_font_bytes", "_set_once"}`)
stays.

**The brief asked me to check the frame file and the shared home for others of
the shape, and frame had one.** `retained.by_cache == {}` beside
`_lru_cache_names(globals()) == set()`: `by_cache` is built *from*
`_caches_of`, so an empty name set makes it empty by construction. Deleted; the
name-set equality stays. Audited the rest of the new code for the same shape:
the control module's remaining multi-conjunct asserts
(`test_the_exemption_admits_exactly_the_cache_stores`,
`test_the_walk_does_not_leave…`, `test_the_two_halves_do_not_double_count`,
the fence arms) are each failable in both halves — C1/C4/C6a/C6b/C7 kill one
half or the other.

| # | adds | reds | passes |
|---|---|---|---|
| E1 | a third `@lru_cache` in band | band's `test_no_module_level_accumulator_retains_a_page_bitmap` (the kept conjunct) | 90 |
| E2 | an `@lru_cache` in frame, whose allowance is empty | frame's `test_no_module_level_accumulator_retains_a_page_bitmap` | 150 |

### The gate

* **Impact set** (the eleven files): **991 passed, 0 failed, 0 skipped** in
  73.96 s, against the brief's 964 baseline (+27 = +26 in the control module,
  +1 in `test_book_toc.py`). Every skip attributed by name: there are none.
* **The denominator closures are a measured no-op on today's tree**, which is
  what cycle 1 said they would be (the false negative is latent, not live):
  declared = collected = **22 / 8 / 4** for frame's `pages`, band's
  `snowflake_interior` and band's `page`, with `declared - collected` empty in
  all three — the same figures CARD-218 cycle 2 recorded, now through a reading
  that also sees `autouse` and the configured name prefix. So nothing in either
  file is over-counted by the widening.
* **AC-4**: the six in-scope files collect **260** node ids against the fork
  point's **259** — the set difference is one-directional: **removals 0**, one
  addition, `tests/test_book_toc.py::test_the_drawn_tie_is_still_carried_here`
  (FIX 4's fence).
* **Additions, each named**: `tests/test_shared_fixture_controls.py` 25 → 51
  (+26) and `tests/test_book_toc.py` 53 → 54 (+1,
  `test_the_drawn_tie_is_still_carried_here`). The 26:
  `TheCopiesCannotComeBack` +9 (6 caught spellings, 3 edge rows),
  `TheDenominatorSeesEveryConsumerShape` +2 (`[autouse]`,
  `[configured name prefix]`), `TheCollectedNameRulesComeFromTheConfig` +6 (new
  class: fallback-vs-config, 2 configured arms, the stub guard, 2 autouse
  scoping controls), `TheRetentionWalkSeesEveryChannel` +8 (4 channels:
  `[deque]`, `[instance attribute]`, `[slotted instance]`,
  `[unnamed lru_cache]`, `[a plain class of the module's own]` — 5 — plus 3
  fence arms), `TheCacheAllowanceIsAnExemptionWithAControl` +1 (the numpy
  bound).
* **G-5**: `git diff 808cf51f..HEAD -- src/` is empty. `src/` mutants were
  applied to the worktree and restored from a pristine copy outside it;
  sha256 verified identical afterwards.
* **G-2**: no test deleted, renamed, skipped or merged. The two redundant
  per-file `getfixturevalue` tests are still there.
* **Trap 9**: `tests/helpers/shared_fixture_controls.py` and
  `tests/test_shared_fixture_controls.py` name **0** of the eight render
  idioms. `tests/test_book_toc.py` went 25 → 27 mentions (two more
  `interior_stream` in prose), so its membership in the grep set is unchanged;
  `test_suite_profile.py` passes inside the gate.

## [FIX ROUND 1 PRE-GATE on `f418f3e6` — 2026-10-24, orchestrator] PASSED

Clean this time, and the verdict is a flat PASSED because the one thing the last
pre-gate had to route onward is closed and nothing new is open.

### Cycle 1's three gating mechanisms, re-run with MY OWN unchanged instruments

Not the round's mutants — the exact probes I used to reproduce cycle 1 before
authorising the round, re-pointed at `f418f3e6` without a character changed. That
is the only arrangement in which "fixed" means something, because an instrument
rewritten alongside the fix measures the fix's opinion of itself.

| finding | at cycle 1 | at `f418f3e6` |
|---|---|---|
| **F-003** — a **faithful** third `_page_digest` appended to the real band file, bound by alias, every call site using it | **65 passed, 0 cells** | **reds `TestSharedControls_TheCopiesCannotComeBack::test_no_importer_defines_its_own_copy_of_a_shared_helper`** ✅ |
| **F-002a** — `declared_consumers(globals(), "shared")` with an `autouse` consumer | **`[]`** (while pytest's own `fixturenames` said `True`) | **`['TestProbe_A::test_one', 'TestProbe_A::test_two', 'test_what_the_two_halves_see']`** ✅ |
| **F-002b** — the consequence: the DECLINE under `-k one_render_served`, 2 deselected | **1 passed** — the control passed with `_RENDERS=[1]`, no refusal | **1 failed** at `shared_fixture_controls.py:554` ✅ |
| **F-001** — the retention walk asked directly about six hiding places | **3 of 6 invisible** (75,735,000 B hideable) | **6 of 6 SEEN** ✅ |

F-001's table in full, each at 25,245,000 B — and note the fourth row, which
**nobody asked for**: the round replaced the type-by-type walk with the
collector plus three edits, and `__slots__` closed as a side effect, which is
the shape of a real fix rather than a patched enumeration.

| where a page is parked | cycle 1 | now |
|---|---|---|
| instance `__dict__` (plain non-`Test` object) | 0 B | **25,245,000 B** |
| `collections.deque` | 0 B | **25,245,000 B** |
| `@lru_cache` bound inside a list, never named | 0 B | **25,245,000 B** |
| `__slots__` instance (**not in any finding**) | — | **25,245,000 B** |
| `Test*` class attribute | 25,245,000 B | 25,245,000 B |
| plain list | 25,245,000 B | 25,245,000 B |

### The gate, AC-4, and G-5

* **Impact set, eleven files: 991 passed, 0 failed, 0 skipped**, 77.37 s. Baseline
  964 + 27. **Zero `SKIPPED` lines**, so there is nothing to attribute — the
  `DATABASE_URL` skip at `tests/conftest.py:207` never fires in this set.
* **AC-4 over the six in-scope files: 260 collected against the fork point's 259.
  Removals 0.** The single addition is named: `tests/test_book_toc.py::test_the_drawn_tie_is_still_carried_here`, FIX 4's fence. The control module went 25 → **51**.
* **G-5: `git diff 808cf51f..HEAD -- src/` is 0 lines.** Verified by me, not taken
  from the report. Working tree holds **only** the modified card.
* **No mutant residue.** The round flagged that a cancelled mutation run had left
  a mutant in the tree and reverted a later edit; it says it repaired both. I
  grepped for every marker either of us used — the only hits are
  `_probe_own_digest` **inside string literals in the new control module**, which
  is the fixture source for the alias controls, not live code. Clean.

### The round's own best finding, verified to the byte — and it corrects two cards

Cycle 1 asked whether `_set_once`'s boolean ink masks are the right unit for the
exemption's 24,435,107 B. They are not, and the answer is worse than a unit slip.
Measured independently at session end over `tests/test_book_pdf_band.py`:

```
currsize: 666    values_found: 666    dtypes: {'bool': 666}
direct_nbytes:  24,435,107      distinct_bases: 666
base_nbytes:   110,882,067      → 4.54x
```

1. **The unit was apples to oranges.** All 666 values are `dtype('bool')` —
   cropped ink masks at **one byte a cell** — while a page bitmap is 2550×3300
   **RGB at three bytes a pixel**. So **"0.9979 of one page bitmap", a figure
   CARD-218's card, this card and the backlog all quoted, divided 1-byte cells by
   3-byte pixels.**
2. **And 24.4 MB is not the retention — it is the part of it the views can see.**
   Each cached mask is a numpy **view**; its 666 distinct bases hold
   **110,882,067 B**. The floor this one test module charges every full suite is
   **~111 MB**, because `maxsize=None` keyed by page geometry holds whole
   uncropped arrays to serve cropped slices of them.

**Neither CARD-218 nor this card is falsified**, and the reason is a decision I
argued for against CARD-218's cycle 2: both exemption controls ask **which cache
names** are exempt and **never how many bytes**. A byte-valued control would have
been wrong by 4.5× and nobody would have known. Backlog item corrected (`be17e42d`)
with the remedy that falls out of it — storing a `.copy()` of the crop cuts 78 %
before any bound is considered. Still pre-existing; still not this card's.

### Three mutants survived, all three declared, and two were the round's own dead mechanisms

This is the part I would have gated on if the round had hidden it, so it is
recorded as the round's credit rather than buried:

* **B3c** — the round copied pytest's glob-character condition onto the
  `fnmatch` call and justified it by case-folding. Wrong: `os.path.normcase` is
  the identity on POSIX, so `fnmatch` on a glob-free pattern is exact equality,
  which the prefix arm already covers. **The mutant survived AND the control the
  round wrote to kill it passed either way** — the exact F-005 unfailable-conjunct
  shape it had just been sent to delete. Control deleted; the condition kept with
  "no mutant kills this, pytest's reason is cost" written beside it.
* **C9** (`_SCALAR` short-circuit) — same treatment, recorded as a
  frontier-length optimisation and not a mechanism.
* **C8 / C6b** — the brief's own FIX 3 prescription ("enter `abc.Collection` and
  an instance's `vars()`") **produced two mechanisms that could not fail**:
  reading an instance with `vars()` never reaches `__globals__`, so the fence's
  `FunctionType` entry was dead, and `gc.get_referents` returns `[]` for both a
  numpy view and an object array, so the measured-leaf gate had no `.base` edge to
  block. **My prescription was the defect**; the round replaced it with the
  collector plus three edits, which makes the fence load-bearing (7 cells), closes
  `__slots__` for free, and reproduces band's and frame's figures to the byte
  through a different code path.

### And one correction to cycle 1 that I accept

The four `TestBookToc_PageNumbersSurviveTheTitlePage` node ids in the M29 arms are
**errors, not failure cells**, in *both* arms — their shared rendering fixture
raises before any assertion. An error is still a kill, so M29 remains killed and
the 21-vs-14 counts stand. But "those renders are among the 14 failure cells"
would have been a false claim, and two of the three fenced carriers now say they
kill M29 **by erroring** and one **by failing**. Exactly the distinction this
board's "an exit code is not a verdict; the failure cells are" rule exists for,
caught one level deeper than the rule states it.
