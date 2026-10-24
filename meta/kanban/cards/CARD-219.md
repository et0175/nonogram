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
