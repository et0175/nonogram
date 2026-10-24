# CARD-218: Each book renders once per module, not once per test

**Status:** done
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
**Review score:** 7.0 (cycle 2, NOT CERTIFIED; cycle 1 was 6.0) — merged on a recorded gate decision, see the merge note below
**Started:** 2026-10-23
**Closed:** 2026-10-24
**Actual:** 1d (dispatched 2026-10-23; implementation round + fix pre-gate + cycle 1 + fix round 1 + fix pre-gate + cycle 2 + fix round 2 + fix pre-gate + merge gate = aggregate round counter 6 of 6)
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
  files' own existing tests, unchanged in name and intent, plus the three
  render-count controls
  `test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_one_render_served_the_whole_module`,
  `test_book_pdf_band.py::TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_one_render_served_the_whole_module`
  and
  `test_book_pdf_band.py::TestBookPdf_EveryFifthGridLineWider::test_one_render_served_the_whole_class`
  — each of which answers **only for a run that collected every consumer of
  its fixture that it can see, and refuses otherwise**. The two qualifications
  are load-bearing: a narrowed selection makes the control refuse rather than
  pass (cycle 1 F-002), and a consumer taking the fixture through
  `request.getfixturevalue` is invisible to it, which is closed here only by an
  equality-to-zero AST check that these two files contain no such call and is
  otherwise CARD-219's (cycle 2 F-002).)
- **AC-2** (happy, measured): *Given* the two converted files, *when* they are
  measured before and after, *then* the card records a per-card profiling
  artefact holding the render counts, the interleaved wall-clocks and the
  retention figures. (artefact:
  `meta/profiling/card-218-render-sharing.md`, the accepted per-card form that
  `card-236-…`, `card-241-…` and `card-243-…` already use; guard:
  `tests/test_suite_profile.py::TestSuiteProfile_ArtefactExistsAndIsComplete`
  for the committed duration artefacts this one reads from. The deltas are
  recorded, not asserted.)
  <!-- THE SUITE-TOTAL CLAUSE IS STRUCK, review cycle 2, 2026-10-24. It read
  "the suite is profiled solo before and after … and the total is lower", and
  it is unshowable: the effect is ~1.5 s, each arm costs 1433 s of solo
  wall-clock, and a full suite's run-to-run spread is tens of seconds. The
  implementation round struck it for a DIFFERENT and wrong reason — it cited a
  "0.20 s solo-run reproducibility" against a 0.99 s gain five times larger
  than it, and the orchestrator's pre-gate repeated that figure without
  checking the argument it supported. The artefact clause was showable all
  along and simply had not been done. -->
- **AC-3** (guard, no coverage loss): *Given* the converted files, *when* the
  suite runs, *then* the collected test count for those files is unchanged —
  no test was merged, parametrised away, skipped or deleted by this card.
  (**gate**: set difference over sorted `--collect-only` node ids between the
  fork point and HEAD — `removals` must be 0; additions are permitted and each
  is named on the card. Measured at every station: 129 → 134 → 138 → 140, with
  removals 0 each time.)
  <!-- The ref this replaces named `TestCuration_ConvertedFilesKeepTheirTestCount`,
  which exists nowhere — one of EIGHT fictional `TestCuration_*` verifiers
  across CARD-218/219/220 (cycle 1 F-003). It cannot exist as a standing test:
  "unchanged from before this card" is a property of the DIFF, and a standing
  test that tried to hold it would be a hand-maintained count that the next
  card breaks. -->
- **AC-4** (edge, mutation): *Given* a shared rendered page, *when* one test
  mutates its copy, *then* the other tests in the module see the unmutated
  page. (test:
  `test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedInteriorIsNotMutated::test_the_shared_pages_are_handed_out_as_they_were_drawn`
  and
  `test_book_pdf_band.py::TestBookPdf_TheSharedSnowflakeInteriorIsNotMutated::test_the_shared_pages_are_what_the_fixture_drew`,
  each comparing every page against a digest taken **inside** the fixture
  before any test saw it. Guarantee bounded by cycle 2's F-002: it holds for
  every consumer the derivation can see, and a `request.getfixturevalue`
  consumer is not one — measured, CAUGHT as a parameter and MISSED that way.)
- **AC-5** (edge, memory): *Given* the converted files, *when* their modules
  are finalised, *then* no module-level accumulator either file adds retains a
  page bitmap. (test:
  `test_book_puzzle_frame.py::TestPuzzleFrame_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`
  and its band twin, each a **derived equality** — 32 B per page of the book it
  signed, 320 B and 256 B — with
  `::test_the_page_bitmap_unit_is_this_modules_own_page` cross-checking the
  unit against `test_book_pdf_memory.PAGE_BITMAP_BYTES` so neither can go stale
  alone.)
  <!-- REF REPLACED, NOT SUPPLEMENTED, review cycle 2, 2026-10-24. The old ref
  named `test_book_pdf_memory.py`'s peak assertions, which instrument THAT
  module's own `_live` dict and structurally cannot fail on bytes retained by
  another module — which is exactly how the implementation round shipped
  454,410,000 B (18.0 page bitmaps) held to the end of every session, through a
  review and a pre-gate, with no guard on the board able to see it (cycle 1
  F-001). SCOPE, stated because the AC's wording invites a bigger reading than
  the control supports: the subject is the ACCUMULATORS these two files add.
  `tests/test_book_pdf_band.py` also retains 25,192,439 B in two pre-existing
  `@lru_cache(maxsize=None)` stores — 0.9979 of one page bitmap — which is
  identical at the fork point `c7cca514` (25,192,183 B), is NOT this card's,
  is deliberately outside this control, and is backlogged on its own. The
  instrument's declared blind spots are numpy, an lru_cache store, a `Test*`
  class attribute, and nesting deeper than one container level; widening it is
  CARD-219's, with a review in front of it. -->
- **AC-6** (guard, stream semantics): *Given* any test that walks an
  `InteriorStream`, *when* it runs, *then* it walks a stream of its own — no
  fixture hands the same generator to two tests. **STRUCK HERE AND CARRIED TO
  CARD-219**, measured: `grep -c interior_stream` over both converted files is
  **0 and 0**, so this AC is vacuous for everything this card actually
  converted, while the idiom lives in `test_book_toc.py` (19),
  `test_book_solved_answer_key.py` (16), `test_book_pdf_memory.py` (9) and
  `test_book_finalise_gutter.py` (9) — three of which are in CARD-219's
  `Touches:`. (no control, and deliberately none: one confined to these two
  files would cover 2 of 30 render-heavy files and would make the ref *look*
  satisfied, which is the `check_ref_missing` shape cycle 1's F-003 was
  about.)

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
## Review notes -- cycle 2 (2026-10-24)

**7.0 — NOT CERTIFIED** against `min_score: 8`. Two gating findings, both in
code **fix round 1 wrote**, both the same root cause, both duplicated across
the two files: a derivation that answers from an authority narrower than the
one available to it at the same moment, and resolves the unmodelled case to a
silent **pass**. Everything the orchestrator certified reproduced; what fails
is what nobody had yet attacked — the new guards' own claims.

Tree reviewed: `60cbc0f0`, `tests/test_book_puzzle_frame.py`
`ad7cc1f2e1f954b7160829f665ed13667d1319ec77dac7c17e01250ea3e36d87`,
`tests/test_book_pdf_band.py`
`e5de8b9202209173ee49867d9d42d3f431da319bc7878b33c5fb6e186b18bba8` — verified
before and after every mutant. **All mutants were run in a separate detached
checkout outside this worktree**, so the tree under review was never edited;
its two hashes are unchanged.

Report: `meta/review/20261024T235219Z-CARD-218-cycle2.yml` (worktree; needs the
card sync to reach main).

### The score

```
10.0
 -1.0  F-001 high   AC-5's band retention control is 0.21 % from its own bound and cannot see it
 -1.0  F-002 high   the denominator guard is default-deny only over consumers in a test's own signature
 -0.5  F-003 medium "514 added lines are executable" does not reproduce -- it is 302
 -0.5  F-004 medium "no module under tests/ instruments the process's own memory at all" is false
 ----
  7.0           (F-005, F-006, F-007 are low and deduct nothing)
```

### F-001 (high) — the AC-5 retention control is at 99.79 % of its bound and its instrument reports 0.001 %

`TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap`
asserts `total < one page bitmap (25,245,000 B)` and its docstring states
**"Nothing this module leaves behind is as big as one page bitmap."** Its
instrument reports **256 B**.

What `tests/test_book_pdf_band.py` really leaves alive in `sys.modules` after
every fixture is finalised, measured by walking the two `@lru_cache` stores
with `gc.get_referents` (the store `functools` "does not expose" is three
lines of stdlib away):

| retained by | bytes | page bitmaps |
|---|---|---|
| `_set_once` lru_cache (`maxsize=None`, currsize **666**, ndarrays) | 24,435,107 | 0.9679 |
| `_font_bytes` lru_cache (`maxsize=None`, currsize 1, bytes) | 757,076 | 0.0300 |
| `_SHARED_SNOWFLAKE_DIGEST` | 256 | 0.0000 |
| **TOTAL** | **25,192,439** | **0.9979** |

The bound is `< 1.0000`. **Real headroom: 52,561 B — 0.21 %**, not the "five
orders of magnitude" the round's notes and the control's docstring claim.
Deterministic: two consecutive runs gave 24,435,107 B / 666 entries byte for
byte, and the band file **at the fork point `c7cca514`** gives the identical
figure — so this retention is **pre-existing and not CARD-218's**, which is
why this is high and not critical.

It gates on the orchestrator's own criterion. **ADR-0039/R3**: an exemption
must record "whatever it still cannot see as a **measured bound with its own
failing control**". It records prose, with no figure and no control. And "a
declared bound is acceptable only when it cannot hide a real instance" fails
on measurement: there is one, it is **98,400x** larger than everything the
instrument can see, and it sits at 99.79 % of the bound.

Three things make it more than bookkeeping:

* **The control's failure message prints the false total.** Verbatim, under the
  bytes-restored mutant: *"this module will leave 201,960,000 B (8.00 page
  bitmaps) alive after its fixtures are finalised"* — while the true figure in
  that arm is 226,395,083 B. A guard whose diagnosis is 24 MB wrong is the
  displaced-diagnosis shape this card's rule 2 exists to prevent.
* **The hiding channel is reachable with this module's own idioms.** Measured:
  `_bitmap_bytes(np.asarray(page)) = 0` while `arr.nbytes = 25,245,000`. A
  numpy array of page pixels is invisible — and that is exactly what `_scan`
  and `_set_once` produce. The **numpy channel is not in the declared
  blind-spot list at all**; nor is a bitmap on a Test class attribute
  (`_retained_bitmap_bytes({'TestX': Holder})` with `Holder.pages=[page]`
  returns `{}`).
* **The instrument's blindness is the single point of failure for all of
  AC-5**, shown with a mutant nobody had run (X2 below): neuter the
  container-summation branch of `_retained_bitmap_bytes` *and* put the bytes
  back, and the control goes **GREEN on 201,960,000 B retained**.

The frame file is clean here and the finding does not touch it:
`tests/test_book_puzzle_frame.py` has **no** `@lru_cache` (the only hit is the
docstring naming the channel), and an independent deep walk gives 320 B —
equal to its own control's figure. One file's declaration is honest; the
other's hides 25 MB.

**Fix:** widen `_bitmap_bytes` over numpy (`.nbytes` guarded on
`type(v).__module__`) and `_retained_bitmap_bytes` over
`functools._lru_cache_wrapper` via `gc.get_referents` — both stdlib, ADR-0006/R1
untouched — then **re-derive the bound**, because `< one page bitmap` cannot
survive the widening at 0.9979. ADR-0039/R3's own shape: a measured allowance
for the two pre-existing caches held to an **equality** (so a growing cache
reds), plus the strict accumulator bound on everything else. And strike both
universals: the class docstring's "Nothing this module leaves behind…" and the
message's "this module will leave {total} B alive" are false as written.
`_set_once`'s unbounded cache is a separate, pre-existing backlog item.

### F-002 (high) — the denominator guard is default-deny only over consumers written in a test's own signature

`_declared_consumers` reads `inspect.signature` over the module's `Test*`
classes' own `test_*` attributes; `_consumers_among` reads pytest's own
`item.fixturenames`. Two authorities, both available at the same moment, and
the guard defaults-deny on the **narrower** one. ADR-0039/R2: *"a shape it
cannot analyse is a FAILURE, never a silent pass."*

Enumerated and tested against the real helper (synthetic namespaces, run under
pytest):

| consumer shape | seen by `_declared_consumers`? |
|---|---|
| direct method | **yes** (baseline) |
| `@staticmethod` / `@classmethod` test | **yes** |
| indirect — takes it through another fixture | **NO** |
| `request.getfixturevalue("name")` | **NO — and invisible to `_consumers_among` too** |
| inherited method on a subclass | **NO** (`vars()` sees no inherited attr) |
| nested `Test*` class | **NO** (pytest collects it; the one-level walk does not) |
| method named `testX` (no underscore) | **NO** (pytest's prefix is `test`, the helper's `test_`) |
| `@pytest.mark.usefixtures` | **NO** to signature; yes in `fixturenames` |
| class aliased in the namespace | declared name can never be collected → **permanent red** |

**There is no instance today, and I measured that rather than assuming it.** An
independent `pytest_collection_finish` probe comparing the two authorities over
a whole-file run of both files reports `collected − declared = []` for all
three fixtures, with declared = collected = **22** (`pages`), **8**
(`snowflake_interior`), **4** (`page`) — which independently confirms the
round's three derived counts and the fifth-rule docstring's claim that only
`TestBookPdf_EveryFifthGridLineWider` declares `page` (all four names are in
that class).

**What gates is the consequence, with a control that can fail.** Two arms,
identical mutation, measured:

| arm | how the late class takes the shared render | cells |
|---|---|---|
| B | as a **parameter** (`def test(self, snowflake_interior)`) | **2 failed** — `::test_the_shared_pages_are_what_the_fixture_drew`, `::test_one_render_served_the_whole_module` — **CAUGHT** |
| A | via `request.getfixturevalue("snowflake_interior")` | **40 passed, 0 cells** — **MISSED** |

In arm A the shared render is drawn on **after** the mutation control has
already signed it off, and neither guard sees it: no signature, so the
denominator does not refuse; not in `fixturenames`, so the ordering guard
reports nothing later. **AC-4's guarantee is silently void for that consumer.**
And `request.getfixturevalue` is a live idiom in this tree — **9 sites**, one of
them literally `tests/test_puzzle_solver_page.py:671: return
request.getfixturevalue("page")`, the same fixture name as the band module's
class-scoped render.

The denominator's own asymmetry, measured with an added consumer:

| selection | verdict |
|---|---|
| deselect a **direct** consumer's class | **2 failed** (refuses — correct default-deny) |
| deselect an **indirect** consumer's class | **39 passed, 1 deselected** (accepts) |

**Fix (minimum for one round):** the transitive closure over the module's own
fixtures' signatures; `getattr(member, "pytestmark", ())` for `usefixtures`;
and `getfixturevalue`, which cannot be seen at all, as a **declared bound with
its own failing control** — an AST scan of the two files held to an equality
against the **0** sites that exist today. The inherited/nested/`testX` shapes
have no instance in this tree and can take the same equality-to-zero treatment.

### Rulings on risks 1–7

1. **Helper duplication — PROSE ONLY, no behavioural divergence. Not re-filed.**
   Re-derived independently with `ast` (each helper unparsed, docstrings
   stripped, re-unparsed, compared byte for byte): **8 of 9 identical**, and
   those 8 are 2+4+8+8+2+5+11+13 = **53 normalised executable lines** — the
   pre-gate's 53 reproduces exactly. All nine together are **61**. The ninth
   differs in exactly one token sequence. **One precision correction:** that
   token sequence is the f-string of `assert …, <msg>` — an *executable string
   literal*, not prose, so a docstring-stripping AST comparison still catches
   it (mine did). The drift is detectable by the cheapest possible guard, which
   is an argument for writing that guard on CARD-219. Behaviour is identical in
   every pass/fail outcome; the only per-copy difference in all nine is the
   intended one — `_consumers_among` and the ordering guard close over
   `__name__`, so the same source filters each module to its own items.
2. **Derivation blind spots — GATING, F-002.**
3. **Retention declaration — GATING, F-001.** The declared bound *does* hide a
   real instance, at **99.79 %** of the bound. Measured, not reasoned.
4. **The test-to-test import — SAFE, with two figure corrections.** No cycle
   (`test_book_pdf_memory.py` imports no `tests/test_*`; the two subject files
   import it, not each other). **No layering violation:** `tests/test_cli.py`'s
   structural guard walks `_PACKAGE_DIR.rglob("*.py")` with `_PACKAGE_DIR =
   <repo>/src/nonogram` (`:768`, `:781`) — scope is `src/nonogram/**`,
   **confirmed by reading it**, so `tests/**` is outside it entirely. Survives
   any selection (resolved at module import). Cost **+55 ms median**, not
   0.01 s (F-007). Impact-set blind spot real for band, non-existent for frame
   (F-006).
5. **Refusal vs real failure — DISTINGUISHABLE; none of the five could be
   mistaken for the other kind.** Judged on captured output, four families:
   *(DECLINE-1)* "this control cannot evaluate its own denominator: 1 of this
   module's 8 … Select at least every consumer listed … passing would be the
   vacuous green ADR-0039/R2 forbids"; *(DECLINE-2)* "this control reads the
   shared render before 6 test(s) that also take … move it below them, or run
   the file in its own order rather than naming node ids in another one";
   *(REAL-1)* "32 page digests were recorded for a book of 8 pages, **across a
   run that collected every consumer** of the module fixture: the book was
   drawn more than once"; *(REAL-2)* "a test in this module drew on the shared
   interior rather than on a copy of it: interior page(s) [8] no longer match
   the bytes the module fixture drew". **REAL-1 settles it** — the real
   failure's message explicitly asserts the condition the decline denies, so
   the two cannot be confused even by a reader who knows nothing about the
   mechanism. Two caveats, neither a finding: DECLINE-2 conflates "the file's
   class order is wrong" with "you named node ids out of order" (both
   operator-actionable, neither readable as a leak); and the whole diagnosis
   lives in the assertion message, so under `--tb=no` the summary is a bare
   `FAILED <nodeid>` and a decline and a leak **are** indistinguishable. The
   project's `addopts` is `-q` only, so this does not bite — **a gate must not
   add `--tb=no`.**
6. **Proportion — proportionate for what it buys, disproportionate as a
   pattern.** Corrected arithmetic: **302** new executable lines, not 514
   (F-003), of which **122** are the nine helpers written twice (61 × 2) and
   ~60 are the four new tests, against 11 renders and ~1.5 s. The 2 call sites
   + 1 import that close F-001 are unambiguously right; the ~240 lines of
   selection/ordering/retention machinery buy default-deny on three controls
   that cycle 1 measured returning *silent greens with their mechanism
   deleted*, which is what ADR-0039/R2 requires here — and I re-verified two of
   those mechanisms load-bearing with mutants nobody had run. Nothing misleads
   a reader about the **product**: all 302 lines are plainly CARD-218 controls,
   `src/**` untouched, no production docstring edited. Dead weight worth
   naming: the frame copy's `_retained_bitmap_bytes` docstring declares a blind
   spot for an `@lru_cache` channel the frame module **does not have** (zero
   lru_cache in that file), plus F-005's dead conjunct. What makes the pattern
   wrong going forward is the duplication, not the line count: 2 copies today,
   3 after CARD-219 — already backlogged.
7. **A mechanism neither mutated — found two, mutated both, both
   load-bearing.** Line-count preserving (1953 → 1953, printed), separate
   detached checkout, both hashes verified after every restore.

| # | mechanism DELETED (untouched by M1-M14 and Q1-Q6) | selection | cells |
|---|---|---|---|
| X1 | the fifth-rule control's `siblings_excepted=False` → `True` (the only site passing False, and the only one whose consumers **are** its classmates) | its class, control named FIRST | **6 passed** — the intact tree's **1 failed** VANISHES. Whole band file green in both arms, so only a reordered selection kills it |
| X2 | the container-summation branch of `_retained_bitmap_bytes` (`elif isinstance(value, (list, tuple, set, frozenset))` → a type pair that cannot match), **with the bytes restored at the store site** | band whole file | **1 failed** (the read-only control) vs **2 failed** with the branch intact — the AC-5 retention control goes **GREEN on 201,960,000 B retained** |

   Still unmutated and judged not worth a run, **with the reason**: the
   `__module__ == __name__` filter in `_consumers_among` (neutering it can only
   *enlarge* `collected`, and the guard asserts `declared − collected == set()`,
   so it cannot flip a verdict in the dangerous direction), and `_case_of`'s
   `originalname` collapse (a partially-selected parametrised consumer still
   leaves ≥ 4 executions of the fifth-rule fixture under the function-scope
   mutant — derived from 4 declared consumers and 6 collected items — so the
   count arm reds regardless).

### The four figures that did not reproduce

| claim | where | re-measured |
|---|---|---|
| "514 added lines are executable rather than prose" | pre-gate | **302** code lines of 709 added (143 frame + 159 band); 256 docstring + 58 comment + 93 blank. No definition yields 514: added-blank=616, added-docstring=453, added-blank-docstring=360. Whole card: 939 added, **393** code |
| "no module under `tests/` instruments the process's own memory at all" | both new retention docstrings | **false** — `tests/helpers/book_corpus.py:857` is `def resident_bytes()` reading `ru_maxrss`. The round verified the claim with a grep (`RLIMIT_AS|peak_rss|max_rss|tracemalloc`) **narrower than the claim**; `ru_maxrss` is the token that refutes it. The substance survives (it is a helper, not a guard asserting a shape, and the RLIMIT_AS cap is enforced in a child) — the universal does not |
| "a change to `test_book_pdf_memory.py` will not select these two files" | fix notes | **half wrong, in the safe direction**. `tests/test_book_puzzle_frame.py` **is** in that file's 24-file impact set, through shared `src` reach. The mechanism claim is right: the set is byte-identical with the two files at HEAD and reverted to base, so the import edge moves the derivation not at all. Only band is unselected |
| import cost "0.01 s" | fix notes | **+55 ms median** over five fresh-interpreter pairs (540 vs 482 ms, ranges overlapping); 82-103 ms for the memory module alone once `book_corpus` is warm. "Constants-only at module scope" is right — its module-level bitmap retention measures 0 B |

### One arm the round's "arms nothing reds" table misses (F-005)

`tests/test_book_puzzle_frame.py:3436` is
`assert len(_SHARED_DIGEST) == len(pages) == INTERIOR_PAGES` — a **chained**
comparison, two conjuncts, short-circuiting. M1 reds the first. The second,
`len(pages) == INTERIOR_PAGES`, is redded by nothing **and cannot be**:
`_book_pages()` already asserts it at `:902` before the fixture returns. So the
honest count is 3 arms of which one is unfailable. Worse, if it ever could
fail the message is wrong for it — it prints only the first two numbers and
concludes *"the book was drawn more than once, so the fixture is no longer
module-scoped"*, so a 12-page book with 12 digests would be diagnosed as a
scope regression. The message was added this round. The band twin has no chain
and is unaffected.

### Gates — all run, all green

| gate | result |
|---|---|
| derived cycle gate, `scripts/impact_set.py` → **24** files (array length printed, not hand-narrowed) | **2891 collected, 2880 passed, 0 failed, 0 errors, 11 skipped, exit 0, 458.73 s** |
| the 11 skips | **enumerated by node id** with `--collect-only -q -m db_required` over the derived array (the run's `-rs` prints only the aggregate): **9** in `tests/test_admin_binding.py::TestUndefinedTableReport_NamesWhatTheFailingConnectionWasTalkingTo`, **2** in `tests/test_db_engine_lifecycle.py`. One cause for all eleven: `tests/conftest.py:207` `Database not reachable: DATABASE_URL is not set`. Same 11 as cycle 1's and the round's |
| `tests/test_browser_fixture_scope.py` **explicitly** | `--collect-only -q` → **29 tests collected**; run → **29 passed, 0 skipped, 55.70 s**. Confirms the round's correction of cycle 1's and the adjudication's "17" |
| census guards (5 files) | **643 passed, 0 failed, 0 skipped, 89.33 s** — the same 643 |
| both subject files whole, with an independent `sessionfinish` probe attached | **138 collected, 138 passed, 0 skipped, 8.02 s** — reproduces 138 |
| scope gate | **PASS** — exactly 2 files, both in `Touches:`; zero intersection with CARD-219's; CARD-220's `tests/**` overlaps by construction and carries no signal. The new import names `tests/test_book_pdf_memory.py`, which is **also** in this card's `Touches:`. Zero added lines match `skip|xfail|pytest.mark` |

### System contract — 20 rules: 1 ✓ holds, 17 ⚠ unchecked, **2 ✗ violated**

`ADR-0039/R2 ✗` (F-002) and `ADR-0039/R3 ✗` (F-001). `ADR-0039/R1 ✓ holds`,
re-derived rather than carried — every claim the round makes about what its
controls catch has a control that can fail, including X1 and X2 above; the two
R1-adjacent defects here are claims that are **false** (F-001, F-004), filed
against R3 and as prose, not double-counted. `ADR-0038/R8 ✓
carried(cycle 1, delta-clean)`. The other 16 are `⚠ unchecked —
no_eligible_fact` or `check_ref_missing`, carried from cycle 1 with their ids,
all in the YAML's `system_contract.verdicts` verbatim.

### [Family] — YES, and it is the loop-feeding-on-itself shape

Both gating findings are attributable to fix round 1, are defects in code the
round **wrote**, share one root cause (RC-1: a derivation whose authority is
narrower than the one available to it, resolving an unmodelled case to a silent
pass), and each is duplicated across both files — **one function family, two
copies**. Waves 48-49 produced six consecutive gating findings each created by
the fix for the previous one, and both of wave 49's were in a control a fix had
just written; cycle 2 is that shape at one lower amplitude. `family_regression:
warn`, so this records and does not escalate. The score moved **6.0 → 7.0**, so
the loop is converging rather than spinning; `min_improvement` is `"off"` and no
escalation check ran.

### What round 6 — the last one — must do, and must not

**Must**, in this order, and nothing else:

1. Close **F-001**: widen `_bitmap_bytes` over numpy and
   `_retained_bitmap_bytes` over `functools._lru_cache_wrapper` (stdlib,
   ADR-0006/R1 untouched), then **re-derive the bound** — the strict `< one
   page bitmap` cannot survive the widening at 0.9979, so it becomes a measured
   allowance for the two pre-existing caches held to an **equality**, plus the
   strict accumulator bound on everything else. Narrow both universals.
2. Close **F-002** at least to: the transitive-fixture closure, `pytestmark`,
   and an equality-to-zero AST guard on `getfixturevalue` in these two files.
3. Correct the four figures and add F-005's arm to the arms table.
4. Re-run the three gates.

**Must not** hoist the nine helpers into a shared home. That is CARD-219's, it
is already backlogged, and doing it in round 6 would put a brand-new third
derivation in front of a review that no longer exists — the exact trade that
produced this cycle's two findings.

### For the orchestrator, on F-003 (yours, deliberately open)

Not re-reported. What this round **changes** about it: **AC-5's `test:` ref must
be replaced, not supplemented** — it names `test_book_pdf_memory.py`'s peak
assertions, which structurally cannot fail on another module's retention, and
the four new node ids are the real verifiers. **But do not write that ref until
F-001 is closed**: as it stands the band half of AC-5's new verifier asserts a
bound it cannot evaluate to within 0.21 %, so pointing the AC at it would mint
a ref that *looks* mechanically checked out of a control whose claim is false —
`check_ref_missing` one layer further in. **AC-1**'s ref should carry the
round's own wording ("each answers only for a run that collected every consumer
of its fixture, and declines otherwise"), and after F-002 it needs one more
clause: *every consumer it can see*. AC-3, AC-4 and AC-6 are unchanged by this
round.

## [CYCLE 2 ADJUDICATION 2026-10-24, orchestrator] 7.0 — both gating findings reproduced, the prescription DELIBERATELY NOT followed, and my own "514" was never a measurement

Score **7.0, NOT CERTIFIED** against `min_score: 8` —
`10 − 1 (F-001) − 1 (F-002) − 0.5 (F-003) − 0.5 (F-004)`, with F-005/F-006/F-007
low and undeducted. Report `meta/review/20261024T235219Z-CARD-218-cycle2.yml`
(parses, `cycle: 2`, `overall_score: 7.0`). 6.0 → 7.0; `min_improvement` is
`"off"`, so no escalation check ran.

I re-derived both gating findings before deciding how to spend the last round.
**Both reproduce.** One of them changes shape under measurement, and that
changed the prescription.

### F-001 reproduced to the byte — and the retention is PRE-EXISTING

My own `gc.get_referents` walk at `pytest_sessionfinish`, numpy and PIL sized
by `nbytes`/`tobytes`:

| `tests/test_book_pdf_band.py` retains | bytes | page bitmaps |
|---|---|---|
| `_set_once` lru_cache, `maxsize=None`, currsize **666** | 24,435,107 | 0.9679 |
| `_font_bytes` lru_cache, `maxsize=None`, currsize 1 | 757,076 | 0.0300 |
| `_SHARED_SNOWFLAKE_DIGEST` | 256 | 0.0000 |
| **total** | **25,192,439** | **0.9979** |

against a control that asserts `total < 25,245,000` and claims *"Nothing this
module leaves behind is as big as one page bitmap."* Headroom **52,561 B,
0.21 %** — not the five orders of magnitude the instrument reports.
`tests/test_book_puzzle_frame.py` is clean: **320 B**, no `@lru_cache` at all.

**And the fact that decides the fix, which I measured rather than inheriting:
the same walk at the fork point `c7cca514` gives 25,192,183 B** — identical but
for the 256 B of new digest — and both `@lru_cache(maxsize=None)` decorators
are already at `:1111` and `:1116` there. **CARD-218 did not create this
retention. It wrote a claim that is false about it.** The defect is the claim,
not the memory. That is why this is a narrowing job and not an instrument job.

### F-002 reproduced exactly, with the WITH/WITHOUT pair run here

An identical late class drawing on `snowflake_interior[0]`:

| arm | how it takes the fixture | cells |
|---|---|---|
| B | as a parameter | **2 failed — CAUGHT** |
| A | `request.getfixturevalue("snowflake_interior")` | **40 passed, 0 cells — MISSED** |

In arm A the shared render is mutated *after* the control signed it off and
neither half of the derivation sees it, so **AC-4's guarantee is void for that
consumer**. `getfixturevalue` is live here — **9 sites**, one of them
`tests/test_puzzle_solver_page.py:671`, `return request.getfixturevalue("page")`,
the same fixture name as band's class-scoped render. The review is also right
that there is **no instance in these two files today**: declared = collected =
22 / 8 / 4 for the three fixtures.

### Why the prescription was NOT followed, and this is the judgement the record needs

Cycle 2 asked round 6 to widen `_bitmap_bytes` over numpy and
`_retained_bitmap_bytes` over the lru_cache store, and to close F-002 with a
transitive-fixture closure. **Both are new derivations, and round 6 is the last
round — nothing reviews it.** Cycle 2 argues this itself, against the shared
hoist: *"a brand-new third derivation in front of a review that no longer
exists, which is the trade that produced both of this cycle's findings."* That
argument applies to its own two prescriptions with equal force, and the
aggregate round counter (5 of 6) is what makes it binding rather than
cautious.

**A false universal is fixed by making it true, not by enlarging the machine
until it is.** So round 6 narrows the claims to what the instruments measure,
records the pre-existing retention as a measured figure the control explicitly
does not cover, adds the two missing blind spots (numpy, and a bitmap on a
`Test*` class attribute), and closes F-002's one channel invisible to **both**
halves with an **equality-to-zero AST check** that neither file uses
`getfixturevalue` — three lines, no model of consumers, default-deny, scoped to
two files. The remaining shapes — indirect-via-fixture, inherited, nested
class, `usefixtures` — stay **open and routed to CARD-219**, where the nine
helpers are being hoisted into a shared home and a review will see the
closure. That routing is on CARD-219's `Touches:` line and in the backlog.

### [Family] — I accept the reviewer's YES, and it is the honest reading

Both gating findings are defects in code **fix round 1 wrote**, they share one
root cause — *a derivation whose authority is narrower than the one available
to it, resolving an unmodelled case to a silent pass* — and each is duplicated
across both files. Cycle 1's findings were about the conversion; cycle 2's are
about the guards written for cycle 1. `family_regression: warn`, so this is
recorded rather than escalated, and 6.0 → 7.0 says converging rather than
spinning. **But it is the second consecutive cycle whose gating findings were
created by the previous fix, and it is the reason round 6 adds nothing that
needs reviewing.**

### FIVE FIGURE CORRECTIONS, and the first is mine

1. **"514 added lines are executable rather than prose" was never a
   measurement.** I produced it with a regex that dropped blanks, `#` lines,
   lines opening `"""` and sentence-shaped lines — but **not docstring body
   lines** — labelled it "rough code volume" in the command, and then wrote it
   on this card and into cycle 2's own brief as a precise figure, where it
   sized the review. Re-derived: of **709** added lines, 93 blank, 58 whole-line
   comment, **256 docstring**, leaving **302 code** (143 frame + 159 band). No
   definition yields 514. **The round is 57 % prose by line, not 27 %** — which
   reframes the proportion question cycle 2 was asked to judge, in the
   direction of the round being more modest than I described it.
2. **"no module under `tests/` instruments the process's own memory at all"
   (both new docstrings) is false.** `tests/helpers/book_corpus.py:857` is
   `def resident_bytes()` reading `resource.getrusage(RUSAGE_SELF).ru_maxrss`.
   Confirmed here. The round verified that claim with a grep
   (`RLIMIT_AS|peak_rss|max_rss|tracemalloc`) **narrower than the claim it was
   checking**, and I repeated the grep rather than the claim. The substance
   survives — a helper, not a guard asserting a shape — the universal does not.
3. **"a change to `test_book_pdf_memory.py` will not select these two files" is
   half wrong, in the safe direction.** Re-derived:
   `scripts/impact_set.py tests/test_book_pdf_memory.py` returns 24 files and
   `tests/test_book_puzzle_frame.py` **is among them** via shared `src` reach;
   only `tests/test_book_pdf_band.py` is unselected.
4. **The new import costs +55 ms median, not 0.01 s** (cycle 2's five
   fresh-interpreter pairs).
5. **"two arms nothing reds" was three.** `tests/test_book_puzzle_frame.py:3436`
   is a chained comparison whose second conjunct is already guaranteed by
   `_book_pages()` at `:902`, so nothing can red it — and were it to fail, the
   message would misdiagnose it as a scope regression. Round 6 drops or splits
   it.

### What cycle 2 found that neither earlier round nor I had touched

Two mutants of its own, both load-bearing: the fifth-rule control's
`siblings_excepted=False` (intact 1 failed, mutant 6 passed under a reordered
class selection), and the container-summation branch of
`_retained_bitmap_bytes` neutered **with the bytes restored** — which leaves
the AC-5 control **green on 201,960,000 B retained**. Round 6's derived
equality must kill that one, and it is on the round's gate list.

Also accepted: the refusals **are** distinguishable from real failures by their
messages alone, with the real failure explicitly asserting the condition the
refusal denies — plus the caveat that the diagnosis lives in the assertion
message, so **a gate must not add `--tb=no`** or decline and leak become one
`FAILED <nodeid>` line. That goes into the merge gate's own method.

### Gates, cycle 2

Derived gate as derived: **24 files, 2891 collected, 2880 passed, 0 failed,
11 skipped, exit 0, 458.73 s** — the 2891 reproduces fix round 1's exactly.
All 11 skips named by node id, one cause: `tests/conftest.py:207`
`DATABASE_URL is not set` via `db_required`.
`tests/test_browser_fixture_scope.py` **29 collected, 29 passed** — confirming
the correction to cycle 1's "17", which I had repeated. Census guards **643
passed**. Both subject files whole: **138 passed**, retention **576 B**
reproduced by a deeper walk too. Scope gate **PASS**. System contract: 20 rules,
1 ✓, 17 ⚠ unchecked, **2 ✗** (ADR-0039/R2 and /R3, the two gating findings).

### Out of scope, and filed

`_set_once`'s `lru_cache(maxsize=None)` retains **24,435,107 B** for the rest of
every session that touches `tests/test_book_pdf_band.py`, and it is
**pre-existing** — identical at `c7cca514`. Not CARD-218's to fix and
deliberately not fixed here; backlogged with the measurement. One more item for
the board: the review skill resolves its own manifest at
`skills/review/../../.claude-plugin/plugin.json`, which does not exist on this
box — the real one is a level deeper, `forge/.claude-plugin/plugin.json`,
version 2026.8.17 — so a review following it literally records
`reviewer_version: unknown`.
## Fix round 2 notes (2026-10-24) -- the last round

Cycle 2 scored **7.0, NOT CERTIFIED** on two gating findings, both in code fix
round 1 wrote. This round closes F-001, F-002, F-004 and F-005 **by narrowing
claims to what the instruments measure**, and adds exactly one new mechanism:
a three-line AST check. Both subject files only; `src/**` untouched.

### The scope decision, and why it is narrower than cycle 2's prescription

Cycle 2 prescribed widening `_bitmap_bytes` over numpy and
`_retained_bitmap_bytes` over the lru_cache store, then re-deriving the bound
as an explicit allowance for the two pre-existing caches; and closing F-002
with a transitive-fixture closure over the module's own fixtures. **Both are
new derivations, and this is the last round: there is no cycle 3 to review
them.** Cycle 2's own risk_6 ruling warns against putting "a brand-new third
derivation in front of a review that no longer exists, which is the trade that
produced both of this cycle's findings". That warning applies to its own
prescription, so it was taken.

What decided F-001 is a measurement, re-derived here independently rather than
taken from the review. **The retention is pre-existing.** Walking this file's
module namespace at session end with `gc.get_referents` through both
`@lru_cache` wrappers (instrument kept outside `tests/`, in the session
scratchpad):

| retained by | bytes | page bitmaps |
|---|---|---|
| `_set_once` lru_cache, `maxsize=None`, currsize **666**, ndarrays | 24,435,107 | 0.9679 |
| `_font_bytes` lru_cache, `maxsize=None`, currsize 1 | 757,076 | 0.0300 |
| `_SHARED_SNOWFLAKE_DIGEST` | 256 | 0.0000 |
| **total** | **25,192,439** | **0.9979** |

and the identical walk against this file at the fork point `c7cca514`, in a
detached worktree, gives **25,192,183 B** -- identical but for the 256 B of new
digest, with both `@lru_cache(maxsize=None)` decorators already present at
`:1111` and `:1116`. **CARD-218 did not create this retention; it wrote a claim
that is false about it.** The defect is therefore the claim, not the memory, and
a false universal is fixed by making it true -- not by enlarging the machine
until it is. `tests/test_book_puzzle_frame.py` is clean on this point: no
`@lru_cache` at all, and an independent deep walk to depth 8 returns **320 B**,
equal to what its own instrument reports.

F-002 was closed the same way. The one channel invisible to **both** halves of
the guard -- `request.getfixturevalue` -- became a declared bound with its own
failing control (ADR-0039/R3), an equality-to-zero AST assertion scoped to
these two files. Measured, so the bound is real and not assumed: `getfixturevalue`
is at **9 sites** under `tests/` (one of them
`tests/test_puzzle_solver_page.py:671`, `return request.getfixturevalue("page")`
-- the same fixture name as band's class-scoped render) and at **0 sites** in
these two files. The transitive-fixture closure, `pytestmark`/`usefixtures`
handling, inherited methods and nested `Test` classes are **not** built here:
they stay open and are routed to **CARD-219**, where the helpers are being
hoisted into a shared home and a review will see them.

### What changed, claim by claim -- before and after

**1. Band's retention bound -> a derived equality (F-001).**

*Before* -- `assert total < unit`, i.e. "total retained bitmap bytes < one page
bitmap (25,245,000 B)". Real headroom 52,561 B = **0.21 %**.

*After* -- `assert total == expected` where `expected = 32 * len(snowflake_interior)`:
the accumulators hold exactly one 32-byte digest per page of the book they
signed. 32 is sha256's digest size written out by hand, not read back off
`_page_digest`, so it is a second statement of the digest's width rather than
that function run twice. Exact, not a threshold; it reds the instant any byte
comes back, and it cannot invite a comparison against a quantity the instrument
cannot see. The frame copy is the same with `32 * len(pages)` = 320 B. The
failure message still names the accumulator, its bytes and its page-bitmap
equivalent (now at 4 decimal places, because 2 was what printed "0.00 pages"
for a 1,536 B regression).

*An unplanned strengthening, measured:* the equality also reds the retention
control under the **scope** mutant, which the old bound never could --
1,536 B (band) and 6,400 B (frame) both sail under one page bitmap. See A3/A5
in the mutant table.

**2. The two false universals, narrowed in both copies.**

*Before* (class docstring): "Nothing this module leaves behind is as big as one
page bitmap." False by 0.21 %.
*After*: the class docstring's first line is "AC-5, with a verifier that can
fail on this module's **accumulators**", and a new **Scope** paragraph states
the three measured figures above, the fork-point comparison, that the two
caches are out of scope, and that they are backlogged. It claims nothing about
them. The test docstring's "Digests sail under it by five orders of magnitude"
is gone -- against what the module really retains it is 0.21 %.

*Before* (both files, identically): "no module under ``tests/`` instruments the
process's own memory at all". **False**: `tests/helpers/book_corpus.py:857` is
`def resident_bytes()` reading `resource.getrusage(RUSAGE_SELF).ru_maxrss`.
Round 1 verified this sentence with a grep (`RLIMIT_AS|peak_rss|max_rss|tracemalloc`)
**narrower than the claim it was checking**.
*After*: "no module under ``tests/`` *asserts a shape* on this process's own
memory (``tests/helpers/book_corpus.py``'s ``resident_bytes`` reads
``ru_maxrss``, but only as the quantity a child's cap is enforced against), and
the one module that instruments page memory at all measures its own live-page
dict". Verified with a grep covering **every token the new sentence claims
about** -- `ru_maxrss|getrusage|RLIMIT_AS|peak_rss|max_rss|tracemalloc|resident_bytes`
-- which returns exactly `tests/test_book_pdf_memory.py` and
`tests/helpers/book_corpus.py`. The grep string is written into the docstring
beside the sentence, so the next reader re-derives it rather than trusting it.

**3. The declared blind spots, each measured (F-001d).**

Added to both copies of `_retained_bitmap_bytes`:

* **numpy** -- `_bitmap_bytes(np.asarray(page))` is **0** while that array's
  `nbytes` is **25,245,000**. In band, numpy page arrays are what `_set_once`
  and `TestBookPdf_EveryFifthGridLineWider._scan` produce; in frame, `_dark` is
  `np.asarray(page.convert("L"))` thresholded, 8,415,000 B of mask per page.
* **`Test*` class attribute** -- the walk reads module-level names and a class
  body is not one (measured: `_retained_bitmap_bytes({'TestX': Holder})` with
  `Holder.pages = [page]` returns `{}`).
* **containers nested deeper than one level** (measured: `{'N': [[page]]}` -> `{}`).
* **`@lru_cache`** -- kept in band with the figure 25,192,183 B attached;
  **corrected in frame**, which declared the blind spot for a channel that file
  does not have (zero `@lru_cache` in it, 320 B measured both ways).

**4. The third unfailable arm (F-005).** `tests/test_book_puzzle_frame.py`'s
count control was `assert len(_SHARED_DIGEST) == len(pages) == INTERIOR_PAGES`
-- a chained comparison whose second conjunct `len(pages) == INTERIOR_PAGES` is
already asserted by `_book_pages()` at `:902` before the fixture returns, so
nothing could red it; and had anything been able to, the message would have
diagnosed a wrong page count as a scope regression. The dead conjunct is
**dropped**; the control is now `len(_SHARED_DIGEST) == len(pages)`, the same
shape as its band twin, and the docstring records why. Nothing is given up:
`test_the_shared_pages_are_handed_out_as_they_were_drawn` holds the digest
length to `INTERIOR_PAGES` in its own right.

**5. The one new mechanism (F-002).** `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
in each file: `ast.walk` over the module's own source, equality to zero on
`ast.Attribute` nodes named `getfixturevalue`. No model of consumers, no
runtime, default-deny. AST and not grep on purpose -- both new docstrings
discuss the idiom by name and do not self-match. Its message points at the
transitive-fixture closure as the real fix and names CARD-219.

The node id `::test_no_module_level_accumulator_retains_a_page_bitmap` is
**deliberately unchanged** in both files although the assertion is now stronger
than the name: the card's M7/M8 mutant rows and three sets of review notes are
keyed to it, and the name is still true, now as the weaker half of what is
asserted. Both docstrings say so.

### The complete arms table, and how it was derived

Derivation, in two steps, because a `FAILED` line says nothing about arms that
never ran. (1) The arms were **enumerated with `ast`**, not by eye: every
`ast.Assert` inside the controls in scope, plus every call to
`_refuse_unless_every_consumer_is_collected` / `_refuse_unless_nothing_takes_it_later`
(each of which is one assert, counted once under its own name). That walk
returns **14 arms in band and 10 in frame, 24 in all**. (2) Each arm was
attributed to a mutant **by the assertion message captured in the output**, not
by the node id, since several arms live in one node. Cells are test cells, never
exit codes.

| # | control | arm (line at HEAD) | redded by | cells |
|---|---|---|---|---|
| B1 | band retention `::test_the_page_bitmap_unit_is_this_modules_own_page` | `measured == {PAGE_BITMAP_BYTES}` (:1935) | A1 | 1 failed / 39 passed |
| B2 | band retention `::test_no_module_level_accumulator_retains_a_page_bitmap` | `total == expected` (:1980) **NEW** | R1, R3a, X2b, A3 | 1/39, 1/39, 2/38, 2/38 |
| B3 | band `::test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue` **NEW** | `not taken` (:1777) | R7 | 1 failed / 39 passed |
| B4 | band NotMutated `::test_the_shared_pages_are_what_the_fixture_drew` | denominator guard (:2030) | R4 | 2 failed / 36 passed / 2 deselected |
| B5 | " | ordering guard (:2031) | R5 | 2 failed / 7 passed |
| B6 | " | `assert _SHARED_SNOWFLAKE_DIGEST` (:2034) | **nothing -- unfailable** | -- |
| B7 | " | `assert not moved` (:2042) | A6 | 2 failed / 38 passed |
| B8 | band NotMutated `::test_one_render_served_the_whole_module` | denominator guard (:2070) | R4 | 2 failed / 36 passed |
| B9 | " | ordering guard (:2071) | R5 | 2 failed / 7 passed |
| B10 | " | `len(digest) == len(interior)` (:2074) | A3 | 2 failed / 38 passed |
| B11 | band FifthRule `::test_one_render_served_the_whole_class` | denominator guard (:895) | A8 | 1 failed / 4 passed / 1 deselected |
| B12 | " | ordering guard, `siblings_excepted=False` (:898) | R6 (= cycle 2's X1) | 1 failed / 5 passed |
| B13 | " | `_FIFTH_RULE_RENDERS == [self.PUZZLE]` (:901) | A4 | 1 failed / 39 passed |
| B14 | " | `drawing_of(page).columns == MAX_SIZE` (:905) | **nothing -- unfailable** | -- |
| F1 | frame retention `::test_the_page_bitmap_unit_is_this_modules_own_page` | `measured == {PAGE_BITMAP_BYTES}` (:3419) | A2 | 1 failed / 99 passed |
| F2 | frame retention `::test_no_module_level_accumulator_retains_a_page_bitmap` | `total == expected` (:3463) **NEW** | R2, R3c, A5, A7 | 1/99, 1/99, 3/97, 2/98 |
| F3 | frame `::test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue` **NEW** | `not taken` (:3271) | R7f | 1 failed / 99 passed |
| F4 | frame NotMutated `::test_the_shared_pages_are_handed_out_as_they_were_drawn` | denominator guard (:3514) | R4f | 2 failed / 94 passed / 4 deselected |
| F5 | " | ordering guard (:3515) | R5f | 2 failed / 24 passed |
| F6 | " | `len(_SHARED_DIGEST) == INTERIOR_PAGES` (:3518) | A5 | 3 failed / 97 passed |
| F7 | " | `assert not moved` (:3527) | A7 | 2 failed / 98 passed |
| F8 | frame NotMutated `::test_one_render_served_the_whole_module` | denominator guard (:3563) | R4f | 2 failed / 94 passed |
| F9 | " | ordering guard (:3564) | R5f | 2 failed / 24 passed |
| F10 | " | `len(_SHARED_DIGEST) == len(pages)` (:3567) | A5 | 3 failed / 97 passed |

**22 live arms, 2 declared unfailable, and the honest list is now complete.**
Round 1 named two unfailable arms, cycle 2 found a third (F-005). That third is
**gone** -- the dead conjunct was dropped, not merely documented -- so the frame
file has none. The two that remain are both in band and both stay, with the
reason:

* **B6**, `assert _SHARED_SNOWFLAKE_DIGEST`: the module fixture extends eight
  digests before any test in the module runs, so the list is never empty when
  this executes. The only mutation that empties it -- deleting the `extend` --
  reds **B10** and **B7** too, so B6 is dominated and can never be the arm that
  reports. Kept because it costs one line and documents the premise.
* **B14**, `drawing_of(page).columns == MAX_SIZE`: the class fixture always
  draws the 30x30 puzzle, and any mutation of *which* puzzle it draws reds B13
  first. Declared, not claimed to be live.

### Mutants -- every one line-count preserving, both files' sha256 verified after every restore

Restores come from pristine copies held **outside** the worktree, in the
session scratchpad, and the harness prints both files' sha256 and line count
after each restore. Fixed-revision hashes, constant across all 22 runs:
`test_book_pdf_band.py` **b3ba8032...1967** (2079 lines),
`test_book_puzzle_frame.py` **00797b25...b50b** (3572 lines). Baseline before
the round: band **e5de8b92...bba8** / frame **ad7cc1f2...6d87**, both verified
against the brief.

| id | mutation (deletion / substitution) | selection | cells | verdict |
|---|---|---|---|---|
| R1 | band `_page_digest` body -> `page.tobytes()` | band whole file | **1 failed** / 39 | B2 reds |
| R2 | frame, same | frame whole file | **1 failed** / 99 | F2 reds |
| R3a | band `_retained_bitmap_bytes` container branch -> `(complex, slice)` | band whole file | **1 failed** / 39 | B2 reds on 0 B |
| R3c | frame, same, + bytes restored | frame whole file | **1 failed** / 99 | F2 reds |
| **X2a** | band `_SHARED_SNOWFLAKE_DIGEST.extend(page.tobytes() ...)`, branch **intact** -- cycle 2's own mutant | band whole file | **2 failed** / 38 | reproduces cycle 2's "2 failed" |
| **X2b** | the same **plus** the container branch neutered -- cycle 2's X2 exactly | band whole file | **2 failed** / 38, **the retention control among them** | **X2 is killed.** Cycle 2 got 1 failed with the retention control GREEN on 201,960,000 B; the equality reds it on `0 B != 256 B` |
| R4 | band `_declared_consumers` -> `return set()` | band, `--deselect ::TestBookPdf_PuzzlePageCarriesNoPictureTitle` | intact **2 failed** / 36 / 2 desel; mutant **38 passed** | vacuous green returns -- B4, B8 load-bearing |
| R4f | frame, same | frame, `--deselect ::TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly` | intact **2 failed** / 94 / 4 desel; mutant **96 passed** | F4, F8 load-bearing |
| R5 | band ordering slice `items[mine + 1 :]` -> `items[:0]` | 4 class node ids, control class **first** | intact **2 failed** / 7; mutant **9 passed** | the reds vanish -- B5, B9 load-bearing |
| R5f | frame, same | 7 class node ids, control class **first** | intact **2 failed** / 24; mutant **26 passed** | F5, F9 load-bearing |
| R6 | band `siblings_excepted=False` -> `True` (cycle 2's X1) | fifth-rule control node id **first**, then its 5 classmates by node id | intact **1 failed** / 5; mutant **6 passed** | the red stops under a reordered class selection -- reproduces cycle 2's 1-vs-6 exactly |
| R7 | band: `assert _SHARED_SNOWFLAKE_DIGEST, ...` -> `request.getfixturevalue(SHARED_SNOWFLAKE)` | band whole file | **1 failed** / 39, message names line 2034 | B3 reds on the real channel |
| R8 | R7 **plus** `node.attr == "getfixturevalue"` -> `"getfixturevalue_X"` | band whole file | **40 passed** | the red in R7 is the AST check and nothing else |
| R7f | frame: `len(pages)` -> `len(request.getfixturevalue("pages"))` | frame whole file | **1 failed** / 99 | F3 reds |
| R8f | R7f plus the neutered attr name | frame whole file | **100 passed** | mechanism confirmed |
| A1 | band `_bitmap_bytes`: drop `* len(bands())` | band whole file | **1 failed** / 39, "measured [8415000] B against ... 25245000 B" | B1 |
| A2 | frame, same | frame whole file | **1 failed** / 99 | F1 |
| A3 | band `snowflake_interior` scope module -> function (`:274`) | band whole file | **2 failed** / 38 | B2 **and** B10 -- B2 on 1,536 B, which the old `< unit` bound could not see |
| A4 | band fifth-rule `page` scope class -> function (`:785`) | band whole file | **1 failed** / 39, "drawn 6 times for this class, not once" | B13 |
| A5 | frame `pages` scope module -> function (`:926`) | frame whole file | **3 failed** / 97 | F2 (6,400 B), F6 ("210 pages recorded, 10 drawn"), F10 ("220 page digests ... book of 10 pages") |
| A6 | band bytes-store (= X2a) | band whole file | **2 failed** / 38 | B7, by "drew on the shared interior" |
| A7 | frame bytes-store | frame whole file | **2 failed** / 98 | F7 and F2 |
| A8 | no mutation -- a selection | fifth-rule class, `--deselect ::test_the_grid_is_the_thirty_by_thirty_at_the_stated_cell` | intact **1 failed** / 4 / 1 desel; with R4 **5 passed** | B11 |

### Gates

1. **Both files whole: 140 passed** (138 before). The two additions, by node id:
   `tests/test_book_pdf_band.py::test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
   and
   `tests/test_book_puzzle_frame.py::test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`.
   Per file: band 40, frame 100.
2. **The derived gate.** `scripts/impact_set.py tests/test_book_puzzle_frame.py tests/test_book_pdf_band.py`
   returns **24 files**; running them: **2882 passed, 11 skipped in 456.73 s**.
   All 11 skips are `tests/conftest.py:207` "Database not reachable: DATABASE_URL
   is not set" via `db_required`, attributed by node id: **9** in
   `tests/test_admin_binding.py::TestUndefinedTableReport_NamesWhatTheFailingConnectionWasTalkingTo`
   (`::test_the_report_carries_the_four_groups`,
   `::test_the_report_names_the_database_the_failing_connection_was_on`,
   `::test_the_report_names_the_engine_its_pool_and_the_reset_count`,
   `::test_the_report_names_the_process_the_thread_and_the_werkzeug_question`,
   `::test_the_capture_answers_while_the_failing_connection_cannot`,
   `::test_the_original_traceback_is_intact_and_the_control_can_fail`,
   `::test_a_connection_on_the_wrong_database_is_a_one_line_proof`,
   `::test_the_verdict_does_not_call_a_correctly_bound_connection_a_mismatch`,
   `::test_the_report_survives_the_suites_own_quiet_option`) and **2** in
   `tests/test_db_engine_lifecycle.py`
   (`TestEngineLifecycle_TheRebuildLeavesNoEngineOlderThanTheSchema::test_no_engine_pool_or_backend_predating_the_rebuild_survives_it`,
   `TestEngineLifecycle_WhyTheHazardCannotBeForced::test_no_server_side_prepared_statement_is_ever_created`).
   The 344 s inside that total is `tests/test_book_export_interior_cover.py`,
   unrelated to this card (CARD-287).
3. `tests/test_browser_fixture_scope.py` explicitly: **29 passed**.
4. Census guards -- `test_browser_fixture_scope.py test_suite_profile.py
   test_guard_integrity.py test_impact_set.py test_fixture_integrity.py`:
   **643 passed**.
5. **The retention probe, before and after**, with the instrument held outside
   `tests/`: accumulators **256 B** (band) and **320 B** (frame) in both runs,
   deep totals **25,192,439 B** and **320 B** in both. The round changed the
   claims and not one byte of what is retained.
6. `rank_durations.py`'s render-idiom census is unchanged: frame **0** matches,
   band **23**, before and after. No instrument was added under `tests/` beyond
   the two test functions themselves.

### What stays open, and where it is routed

* The nine duplicated helpers, and now the tenth control, are two copies ->
  **CARD-219** (already backlogged by the round-1 pre-gate).
* The transitive-fixture closure, `pytestmark`/`usefixtures`, inherited methods,
  nested `Test` classes, and pytest's own `python_functions`/`python_classes`
  prefixes -> **CARD-219**. Measured today: no instance in either file
  (`collected - declared` empty for all three shared fixtures, declared =
  collected = 22 / 8 / 4).
* `_set_once`'s unbounded `@lru_cache(maxsize=None)` holding 24,435,107 B at
  currsize 666 for the rest of every session that collects
  `tests/test_book_pdf_band.py`, and `_font_bytes`'s 757,076 B -> **its own
  card**. Pre-existing (25,192,183 B at `c7cca514`), not CARD-218's, and this
  round deliberately claims nothing about it.
* The five figure corrections on this card (F-003's 302/393 executable lines,
  F-006's impact-set half-correction, F-007's +55 ms) are the **orchestrator's**
  and are not touched here.

### DECLARATIONS

* `DECLARATIONS F-001 -- updated.` The retention bound became an equality, so
  every statement of the old bound was re-derived from the code written: the
  class docstring's scope paragraph (new, with the three measured figures and
  the fork-point comparison), the test docstring, the assertion message, and
  the `#:` comment on `_SHARED_SNOWFLAKE_DIGEST` / `_SHARED_DIGEST`, which said
  the control "holds it to one page bitmap" and now says what it holds it to.
  The blind-spot list in `_retained_bitmap_bytes` was re-derived in both copies.
* `DECLARATIONS F-002 -- updated.` One new mechanism and one new declaration:
  the AST control's own docstring states the bound (0 sites), the measurement
  behind it (9 sites in the tree), and the shapes that remain open with their
  owner. No existing declaration about the guards' coverage became stale --
  the guards themselves are unchanged.
* `DECLARATIONS F-004 -- updated.` The census sentence was narrowed in both
  copies and the verifying grep string written in beside it.
* `DECLARATIONS F-005 -- updated.` The dead conjunct was dropped and the
  control's own docstring records the arm count and why the conjunct could not
  fail; the card's arms table above is re-derived with `ast`, not re-worded.
* `DECLARATIONS -- none (local branch)` for the frame copy's `@lru_cache`
  blind-spot correction: it removes a declaration rather than changing a
  mechanism.

### Two things in the record I believe are wrong, with the measurement

1. **Cycle 2's X2 cell count for the intact arm is right, but its claim that
   the retention control is the *only* thing standing between the suite and a
   silent 201,960,000 B is now false, and the mutant it built to show that no
   longer survives.** Measured above: X2b gives **2 failed** with the retention
   control among them, where cycle 2 recorded 1 failed and the retention
   control green. The reason is the fix, not a measurement disagreement -- an
   equality on 256 B reds on `0 B`, whereas `0 < 25,245,000` was true.
2. **Cycle 2's F-001 suggestion (b) would have made the control *less* able to
   fail, not more.** Its proposed `assert cached == PRE_EXISTING_CACHE_BYTES`
   pins 25,192,183 B as a constant. Measured: `_set_once`'s currsize is **666**
   and its content depends on which tests ran -- the figure is stable for a
   whole-file run and is **not** stable for a partial one, so that equality
   would have been a selection-dependent red in a control explicitly documented
   as selection-independent. Narrowing the claim avoids inventing that
   dependency. This is a disagreement with the prescription, not with any
   figure in the review: every figure cycle 2 reported about the retention was
   re-derived here and reproduced exactly (24,435,107 / 757,076 / 256 /
   25,192,439 / 25,192,183, and 0 for `_bitmap_bytes(np.asarray(page))`
   against 25,245,000 for its `nbytes`).

Everything else in cycle 2 that this round could check reproduced: the 9
`getfixturevalue` sites and the one at `tests/test_puzzle_solver_page.py:671`;
`declared = collected = 22 / 8 / 4`; `tests/helpers/book_corpus.py:857`
`resident_bytes`; `_book_pages()`'s `len(pages) == INTERIOR_PAGES` at `:902`;
X1's 1-vs-6; and the two-channel blind spots (`{'TestX': Holder}` -> `{}`,
`{'N': [[page]]}` -> `{}`).

## [FIX ROUND 2 PRE-GATE 2026-10-24, orchestrator] PASSED — cycle 2's X2 is dead, the equality is stronger than anyone predicted, and one correction of mine

Tree: the branch at `ed63caa1`. Files as shipped —
`tests/test_book_pdf_band.py` `316e85fe389be852cf067c905d9324439a6c20fa92f722cd624d123aeb36431e`,
`tests/test_book_puzzle_frame.py` `381440d4cdea3509c2604e82c7f0112edc19e7bff4324f000ffd29614d996f10`.
(The round reported `b3ba8032…` / `00797b25…`; those are its own hand-back
values, before the one correction below, and both are recorded so neither looks
like a mismatch later.)

### What reproduced

| claim | reproduced |
|---|---|
| 138 → **140** collected | **yes** — set difference: removals **0**, additions exactly the two `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue` checks |
| render-idiom census frame **0** / band **23** | **yes**, unchanged |
| retention unchanged by this round: 256 B / 320 B | **yes** |
| both files green | **140 passed** |

### Four mutants of my own, against what round 2 added

Line-count preserving, restored from pristine copies **outside** the worktree,
both hashes verified after each.

| # | mutant | cells |
|---|---|---|
| **Y1** | **cycle 2's X2 replayed** — bytes restored **and** the container-summation branch of `_retained_bitmap_bytes` neutered | **2 failed / 38**, and `TestBookPdf_TheSharedRenderLeavesNoBitmapBehind::test_no_module_level_accumulator_retains_a_page_bitmap` **is among them** |
| **Y2** | `snowflake_interior` scope `"module"` → `"function"` | **2 failed / 38** — the **retention** control reds beside the count control |
| **Y3** | a real `request.getfixturevalue("snowflake_interior")` consumer inserted | **1 failed / 40** — the AST check |
| **Y4** | the same consumer **plus** `node.attr == "getfixturevalue"` neutered | **41 passed** — so Y3's red is the AST check and nothing else |

**Y1 is the verification this round turned on.** Cycle 2's X2 left the old
control **green on 201,960,000 B retained** — the single point of failure for
all of AC-5. The derived equality reds it on `0 B != 256 B`. Dead.

**Y2 confirms the round's unpredicted strengthening, and it is real.** The
replaced bound `total < one page bitmap` could never see a fixture-scope
regression from the accumulator side; the equality reds on 1,536 B against
256 B. A narrowing that made the control *catch more* is worth naming, because
the intuition runs the other way.

### The round's disagreement with cycle 2's prescription — I side with the round

Cycle 2 asked for `cached == PRE_EXISTING_CACHE_BYTES`, pinning 25,192,183 B.
The round refused on a measurement: `_set_once`'s currsize is **666** and its
contents depend on which tests ran, so that equality is stable for a whole-file
run and **not** for a partial one — it would have introduced a
selection-dependent red into a control whose selection-independence is
documented and was the one good property of F-002's fix. Narrowing the claim
avoids inventing the dependency. Every retention figure cycle 2 reported
reproduced here exactly, so this is a disagreement with the remedy, not with
the evidence.

### FINDING (mine) — the round made its own verification irreproducible, and I corrected it

The new passage replacing F-004's false universal is held "to a grep over every
token it claims about",
`ru_maxrss|getrusage|RLIMIT_AS|peak_rss|max_rss|tracemalloc|resident_bytes`,
and records that it "returns exactly `tests/test_book_pdf_memory.py` and
`tests/helpers/book_corpus.py`". That was true when the round ran it. **It is
not true of the tree the round shipped**: writing the token list into the
docstring means the grep now returns **four** files — the two it names plus the
two this card converts, each matching itself. At `60cbc0f0` the band file had
**0** matches.

Harmless to the claim, costly to the next reader, who would run the quoted grep,
get four, and doubt either the sentence or themselves. And it is the **same
self-matching trap the round had just designed around** one paragraph earlier —
it chose `ast.walk` over grep for the `getfixturevalue` check *precisely* so the
prose discussing the idiom would not self-match.

Corrected in both copies, prose only, no assertion touched: the passage now
states the four, says two of them are the sentence talking about itself, and
gives the filter that shows the two that matter. Re-verified after:
**140 passed**, census frame 0 / band 23 unchanged, filtered grep returns
exactly `tests/test_book_pdf_memory.py` and `tests/helpers/book_corpus.py`.
I made this edit myself rather than spending a seventh round on prose, and it
changes no assertion, so the four mutants above still stand on the shipped
bytes.

### The arms table, and the two that remain unfailable

24 arms, **22 live, 2 declared unfailable**, each named with the mutant that
dominates it: band's `assert _SHARED_SNOWFLAKE_DIGEST` truthiness (the only
mutation that empties the list reds two other arms first) and
`drawing_of(page).columns == MAX_SIZE` (any change to which puzzle the class
fixture draws reds the render-count arm first). Cycle 2's third unfailable arm
is **deleted, not documented** — the chained conjunct was already guaranteed by
`_book_pages()` at `:902`, and its message would have misdiagnosed it. Round 1
reported two arms and the honest count was three; it is now two of 24, and the
frame file has none.

### Verdict

PASSED. Both gating findings closed, both closures certified load-bearing by my
own mutants, the one unplanned strengthening verified, and the round's refusal
of a bad prescription upheld on its measurement. Round 6 of 6 consumed — no
round remains, and nothing is left for one: what stays open is routed to
CARD-219 on its `Touches:` line, and the pre-existing 24.4 MB cache retention
is backlogged with an explicit instruction not to absorb it into this control.

Next: the merge gate. Two notes on its method, both earned this card —
the AC/EC/G selection takes the two subject files **whole** rather than by node
id, because a control that cannot evaluate its denominator refuses by design;
and the gate must **not** pass `--tb=no`, or a refusal and a real leak collapse
into the same `FAILED <nodeid>` line.

## [MERGE GATE 2026-10-24, orchestrator] GREEN — and the gate's own skip count was the finding

### AC/EC/G gate — 783 collected, 783 passed, **zero skips**, EXIT=0

Selected as **whole files**, deliberately, not by node id: `test_book_puzzle_frame.py`,
`test_book_pdf_band.py`, `test_suite_profile.py` (AC-2's guard),
`test_browser_fixture_scope.py` (29 tests, reachable by no scoped selection),
`test_guard_integrity.py`, `test_impact_set.py`, `test_fixture_integrity.py`.
**Two method notes this card earned, both recorded before the gate ran:**

* the subject files go in **whole**, because a control that cannot evaluate its
  own denominator **refuses** by design — so a gate naming the five controls by
  node id would report red on a correct tree, which is what this board's usual
  "explicit node ids, never `-k`" practice would have done;
* the gate must **not** pass `--tb=no`, or a refusal and a real leak collapse
  into the same `FAILED <nodeid>` line. The diagnoses live in the assertion
  messages.

Zero skips in this selection, which matters because green-with-skips reports the
same collected count and the same exit 0 as fully verified.

AC-2's artefact exists on the merged tree (`meta/profiling/card-218-render-sharing.md`,
10,357 B). AC-6 confirmed vacuous: `grep -c interior_stream` is **0 and 0**.

### The lock, demonstrated and not asserted

Written by this gate with `holder`, `why`, `worktree`, `commit`, `at`, and then
**shown to refuse**: `full_suite_lock.current_verdict()` asked from main's tree
returned `(False, …)` naming this holder, this worktree, this commit and an age
against the 21600 s staleness bound. `ps -Ao command | grep -c "[m] pytest"` was
**0** immediately before the run.

### Full suite — `8897 passed, 101 skipped, 0 failed, EXIT=0, 1447.44 s`

`/usr/bin/time -p`: real 1450.44, user 1078.28, sys 89.12. Load averages
5.28 / 5.44 / 5.76 at the end. 1447 s against the committed profile's 1433 s —
14 s of growth across a card that added 11 tests, main's commits and this run's
busier box.

**And the gate's real finding is in the skip count, not the failure count: 101,
against the committed profile's 27.** Exit 0 and no failures look identical
either way, which is why the number was summed rather than glanced at — by its
own bracketed counts, not by counting `SKIPPED` lines:

| file | skips | baseline? |
|---|---|---|
| `tests/test_print_specs.py` | 29 | **no** |
| `tests/conftest.py` (`:207`, `DATABASE_URL is not set`) | 26 | yes |
| `tests/test_puzzle_review_bulk_read.py` | 18 | **no** |
| `tests/test_wave3_image_generation.py` | 16 | **no** |
| `tests/test_book_trim_persistence.py` | 6 | **no** |
| `tests/test_wave3_e2e.py` | 4 | **no** |
| `tests/test_db_engine_lifecycle.py` | 1 | **no** |
| `tests/test_book_pdf_memory.py` (`setrlimit(RLIMIT_AS)`) | 1 | yes |

The baseline 27 are present intact — **26 + 1** — and the **74** others are one
cause: `psycopg2.OperationalError … port 5432 failed: timeout expired`, from
five files that build their own test database rather than going through the
conftest's `db_required` path, so `DATABASE_URL` being unset does not reach
them. **74 tests that executed in the committed profile did not execute here.**

**Resolved rather than argued away.** `pg_isready` afterwards: `localhost:5432 -
accepting connections`, 20 postgres processes — the timeouts were transient
under a load average near 5.8, not a configuration. The six affected files were
re-run with Postgres answering: **398 passed, 2 skipped**, and both remaining
skips are `conftest.py:207`, i.e. part of the baseline 26. So every one of the
74 passes on this tree. A second 24-minute suite would have measured the box.

### A defect of my own, found by the gate's own re-run

The re-run's output carried `tests/test_book_puzzle_frame.py:3375: SyntaxWarning:
"\|" is an invalid escape sequence` — from **my** fix-2 pre-gate correction,
which wrote `grep -v 'puzzle_frame\|pdf_band'` inside a non-raw docstring. Two
new warnings, one per file, **six occurrences in the full-suite log**. Rewritten
as `grep -vE 'puzzle_frame|pdf_band'`, which needs no backslash; both files now
compile with zero `SyntaxWarning` (`72438595`).

**The suite's result still carries, and it is checkable rather than asserted:**
with docstrings stripped, both files' ASTs are **identical** to the tree the
suite ran on. A docstring cannot change a test's behaviour and this proves the
change is confined to one — a far smaller claim than CARD-271's union argument
had to make. The AC/EC/G selection was re-run on the corrected bytes:
**783 passed, zero skips**.

### The merged tree IS the gated tree

`git diff c7cca514..main -- . ':(exclude)meta/'` was **empty** before the merge —
main's commits since the fork point are all `meta/` — so unlike CARD-271 this
card owes no coverage argument for main's movement. `main` was merged into the
branch before the suite ran, bringing `meta/profiling/suite-hotspots-20261023.md`'s
repair in properly, and the merge left both test files **byte-identical**
(`git diff --stat ed63caa1..HEAD -- tests/` empty).

The branch carried **no `meta/`** of its own: every note synced one-way into
main at each station, and the CARD SYNC PROTOCOL held across five agent
hand-backs and six commits.

## [GATE OVERRIDE 2026-10-24, orchestrator] Merged at 7.0 against `min_score: 8` — stated, not slipped

`review.min_score` is **8**. The last recorded score is **7.0, NOT CERTIFIED**
(cycle 2). This card merged anyway, on the orchestrator's decision, and the
reasoning belongs on the record rather than in a commit message.

**What the 7.0 is a score of.** Cycle 2 scored the tree at `60cbc0f0`. Its two
gating findings were then **closed** by fix round 2 (`ed63caa1`), and **no
review cycle has scored the tree that is merging.** That is exactly the
`max_cycles`-is-a-budget-not-a-last-mile-rule problem this board already wrote
down: *either leave a cycle unspent for the last mile, or state on the card
that the final edit shipped uncertified and what the merge gate alone
establishes about it.* The budget is spent — aggregate round counter **6 of 6**
— so this is the second branch, taken deliberately.

**What the merge gate alone establishes**, all of it in the sections above and
all of it the orchestrator's own measurement rather than an agent's report:

* **F-001 closed and its closure certified load-bearing.** Y1 replays cycle 2's
  X2 — bytes restored *and* the container-summation branch neutered — which had
  left the old control **green on 201,960,000 B retained**, the single point of
  failure for all of AC-5. It now reds. And Y2 shows the narrowing is *stronger*
  than the threshold it replaced: the equality also reds under the
  fixture-scope mutant, on 1,536 B, which `total < one page bitmap` could never
  see.
* **F-002's one channel invisible to both halves closed and certified.** Y3 reds
  on a real `request.getfixturevalue` consumer; Y4 shows that red is the AST
  check and nothing else (41 passed with it neutered).
* **F-003 closed by the orchestrator** — all six ACs now name something that
  exists or something that is run, and AC-5's ref is *replaced* rather than
  supplemented, because the one it replaced structurally could not fail.
* **The arms table is complete and honest**: 24 arms, 22 live, 2 declared
  unfailable with the mutant that dominates each. Cycle 2's third unfailable arm
  was deleted, not documented.
* **AC/EC/G 783 passed, zero skips.** **Full suite 8897 passed, 0 failed**, with
  all **101** skips attributed by file and cause, the baseline 27 identified
  intact, and every one of the **74** non-baseline skips — transient Postgres
  timeouts under load — **re-run green** (398 passed, 2 skipped, both baseline).
* **The final prose edit cannot change behaviour, proved not asserted**: with
  docstrings stripped, both files' ASTs are identical to the tree the suite ran
  on.

**What a cycle 3 would have cost and bought.** It would be round 7, past the
fatigue bound, on a card whose entire measured benefit is **11 renders removed
and ~0.7 s of wall clock**, against guard machinery of 302 executable lines —
and whose own conclusion, endorsed by **both** review cycles, is *close
CARD-218 rather than converting more files*. Cycle 2 itself argued against
putting new work in front of a review that no longer exists. A third cycle
would have had to be paid for with a seventh round of fixes it could not then
re-certify, which is the loop it also diagnosed.

**What is NOT being waved through.** The residue is routed with its
measurements, not dropped:

* the **instrument widening** (numpy, `functools._lru_cache_wrapper` via
  `gc.get_referents`) and the **transitive-fixture closure** (indirect
  consumers, inherited methods, nested `Test` classes, `usefixtures`) are on
  **CARD-219's `Touches:` line**, where the nine helpers get a shared home
  **with a review in front of them**;
* the **pre-existing 24.4 MB `_set_once` retention** — 25,192,439 B total,
  0.9979 of a page bitmap, identical at the fork point — is **backlogged** with
  an explicit instruction not to absorb it into this card's accumulator
  control;
* the **53 duplicated lines of guard logic**, and the one copy that has already
  drifted in its assertion message, are **backlogged** and pointed at CARD-219
  before a third copy exists;
* `forge:review`'s unresolvable manifest path is **backlogged** (it silently
  records `reviewer_version: unknown`).

**This is a revertible, test-only change.** `src/**` is byte-identical to the
fork point; nothing in the product moved. `Merge commit` is recorded below and
`/kanban revert CARD-218` undoes it in one step. **Flagged to the owner at the
merge** rather than left to be discovered in a retro: if the owner would rather
spend a seventh round and a third cycle on a 0.7 s saving, this merge is the
thing to revert.
