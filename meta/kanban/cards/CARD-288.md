# CARD-288: The suite's dearest file draws 3,820 pages to read 1,033 — and materialises the book its own docstring calls the OOM shape

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/288-walk-the-stream-not-the-book
**Worktree:** —
**Source:** orchestrator, 2026-10-24, from CARD-219's dispatch: the owner asked whether CARD-208 should run before CARD-219, which sent me to read the four tests CARD-219 had fenced out. They are pixel claims and CARD-219's G-1 protects them, so the cost is not recoverable by *that* card's mechanism — but it is recoverable, by a different one, and this card is it.
**Idea:** —
**Wave:** —
**Created wave:** 57
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/property/test_book_pdf_geometry.py, meta/profiling/card-288-page-census.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

### The premise, measured before the card was written

`tests/property/test_book_pdf_geometry.py` is **51.82 s in four tests** on
`suite-durations-20261023.txt` — **3.63 % of a 1426.16 s suite at 12,955
ms/test**, the densest file in it. All four assert **pixel** claims: they render
the book and measure the ink (`drawing_of` / `drawings_of`), comparing it against
`Sheet` (`:124`), a deliberate independent re-implementation of the page geometry
inside the test file. **Those claims are correct, load-bearing and stay exactly
as they are.** This card does not convert a single assertion.

What it changes is **how the pages are obtained.** Measured 2026-10-24 with a
page census — a counter, not a stopwatch — wrapping
`BookPDFGenerator.interior` and the two ink readers, run from outside `tests/`
(artefact: `meta/profiling/card-288-page-census.md`):

| test | calls | pages drawn | pages ink-measured | secs | ms/page |
|---|---|---|---|---|---|
| `…MirroredMarginsCentreDrawingForEveryParity_pdf_pages` | 136 | 1768 | 544 | 22.28 | 12.6 |
| `…DrawingFitsUsableAreaUnderStandardCell_pdf_pages` | 216 | 1512 | 216 | 20.47 | 13.5 |
| `…PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` | 2 | 494 | 252 | 9.12 | 18.5 |
| `…PortraitWithFixedTopEdgeForEveryExtent_two_up_pages` | 1 | 46 | 21 | 0.84 | 18.2 |
| **total** | | **3820** | **1033** | **52.71** | **13.8** |

**3,820 pages drawn; 1,033 ink-measured — 27.0 %.** The 52.71 s reproduces the
committed artefact's 51.82 s within 1.7 %.

Not all of the other 2,787 are waste, and the difference between the tests is
the whole design of this card:

* **`DrawingFitsUsableArea` wastes no render.** It asserts
  `page.size` on **every** page — "every page of the book's PDF is the trim"
  (EC-019), `:392–:395` — so all 1,512 are genuinely read. 1512/216 = **7 pages
  per case**. Its saving is memory only.
* **`MirroredMargins` draws 13 pages per call and reads 4.** `:640` builds
  `{number: drawing_of(pages[number - 1]) for number in page_numbers}` over
  exactly four page numbers; the other nine per call are touched only by
  `len(pages)` at `:625`. **1,224 pages drawn for a length check**, ≈15.4 s.
* **`PortraitWithFixedTopEdge_pdf_pages` draws 494 and reads 252.** It loops the
  puzzle pages (`:495`, `pages[3 + toc_page_count + index]`); the title page,
  guide, TOC, dividers, SOLUTIONS and answer pages are drawn and never touched.
  **242 pages**, ≈4.5 s.
* **`…two_up_pages` draws 46 and reads 21.** Walks from `5 + toc_page_count`;
  **25 pages** never touched, ≈0.46 s.

**Measured ceiling: 1,491 pages are drawn and never read at all, ≈20.4 s of the
file's 52.71 s — 38.6 %, and 1.43 % of the whole suite.** State the instrument's
domain honestly: that 20.4 s is derived from each test's own
seconds-per-page-drawn, which attributes *all* of a test's time to drawing —
including the ink scan and the oracle arithmetic, which are not free. **So 20.4 s
is an UPPER BOUND from a single instrument, and re-deriving it is AC-5 and this
card's first job**, before any conversion is designed around it.

### And the memory, which is the half with a card behind it

`/usr/bin/time -l` over the file: **maximum resident set size 2,909,667,328 B =
2,909.7 MB = 2.71 GiB.** In this project's own unit (`PAGE_BITMAP_BYTES` =
2550·3300·3 = 25,245,000 at `tests/test_book_pdf_memory.py:210`) that is
**115.3 page bitmaps for one test file** — six times the 433.4 MiB retention
that scored CARD-218 a 6.0.

All four tests call **`interior_pages(...)`, which returns a `List[Image.Image]`
— every page of the book alive at once.** Its own docstring (`:6485`) says so
and says what it costs:

> "**A list of pages, and therefore not what an export uses.** Since CARD-145
> the export path walks `interior_stream` instead, one page alive at a time…
> On a book of any size that list is 25.2 MB a page, so calling it *is* the
> shape the deployed panel was OOM-killed by."

So the test suite's most expensive file is holding the exact shape a production
card was cut to remove. One case of `MirroredMargins` materialises **13 pages =
328 MB**; the file's peak is ~9× that, and **the surplus is unattributed — do
not assume it is the lists.** Peak RSS is allocation-order dependent (CARD-218
measured its own fix making a peak go *up* while removing the retention
entirely), so **the peak is NOT this card's load-bearing claim.** The integers
are: 3,820 drawn, 1,033 read, 13 alive where 1 suffices.

### The mechanism — and it needs no production change

`interior_stream(...)` already exists and already does it.
`InteriorStream.pages` is an `Iterator[Image.Image]`, documented at `:2789` as
"the interior's pages in print order, drawn **one at a time, on demand**. A
generator… it holds none of them — a page is built when it is [asked for]".
`section_plan(...)` is already called by every one of the four tests for
`toc_page_count`, so the page numbers each test needs are known **before** a
page is drawn.

So each test becomes: take the plan, walk the stream, handle each page as it
goes by, drop it, and **stop after the last page it needs** — pages past that
are never drawn at all. That is where the 1,491 go. It costs **no coverage**:
every assertion that runs today still runs, on the same page, against the same
`Sheet` expectation.

**Do not buy the saving by sampling a claim.** An earlier sketch of this card
(orchestrator, same day) proposed sampling `DrawingFitsUsableArea`'s every-page
trim assertion across cases. The lazy walk makes that unnecessary — the page is
size-checked as it passes and then dropped — and sampling would trade coverage
for a saving the stream gives for free. If a round concludes sampling is needed
anyway, that is a finding to raise with its measurement, not a change to make.

## Acceptance criteria

<!-- Written 2026-10-24 under the F-003 rule from CARD-218's review cycle 1:
every `test:` names something that EXISTS, or the AC says **gate** and states
the measurement the gate runs. Six of CARD-219's ACs had to be rewritten because
they named verifiers that were never built; none here names an unwritten class.
Note which ACs are diff properties — "unchanged from before this card" — because
no standing test can know "before this card", and a hand-maintained census of it
is the artefact class this board's guardrails forbid. -->

- **AC-1** (guard, nothing is converted): *Given* the four tests, *when* the card
  is reviewed, *then* **every assertion present at the fork point is still
  present with the same expectation** — this card changes page *acquisition*
  only. (**gate**: parse the file with `ast` at the fork point and at HEAD and
  compare the multiset of `ast.Assert` nodes **at any depth**, normalised by
  unparsing with docstrings stripped; the diff must be empty except for
  assertions the card names on itself. Not a standing test: it is a diff
  property.)
- **AC-2** (happy, the integer): *Given* the page census re-run on HEAD, *then*
  **pages drawn falls to the number of pages actually read, and pages
  ink-measured is unchanged at 1,033** — the saving is entirely in pages nothing
  looked at. (**gate**: re-run the census plugin and record the per-test table
  beside the fork point's; `measured` must be identical per test, `drawn` must
  fall. Recorded, not asserted — the plugin lives outside `tests/`.)
- **AC-3** (guard, derived, standing test): *Given* this file, *when* the suite
  runs, *then* **no test in it materialises the interior** — it holds no call to
  `interior_pages` or `interior`, and obtains pages only through
  `interior_stream`. (test: a new AST guard **in this file**, default-deny: it
  walks `ast.Call` nodes and refuses any attribute call whose name is not in a
  derived allow-set, rather than looking for the two names it knows. Per
  ADR-0039/R2 it must come with a control that FAILS — a mutant reintroducing
  `interior_pages` must red it, and a mutant reaching the pages by a *third*
  route must red it too, or the claim narrows to the two names.)
- **AC-4** (guard, one page alive): *Given* a walk in this file, *when* it runs,
  *then* **at most one page is alive at a time** — no test binds the stream's
  pages to a list, a dict, a set or a module-level accumulator. (test: extend
  AC-3's guard; **and** a measured control in the style of CARD-218's retention
  probe, read at `pytest_sessionfinish` with the module still in `sys.modules`,
  asserting a bound **derived** from the page bitmap unit rather than a
  threshold. Declare what the walk cannot see — CARD-219 carries the open holes
  in that instrument and this card must not claim more than its own instrument
  measures.)
- **AC-5** (happy, measured, and the first thing the round does): *Given* the
  20.4 s upper bound above, *when* the round starts, *then* it **re-derives it in
  a second domain** before designing around it, and records both figures with
  their instruments. (**gate**: recorded. The bound is a single-instrument
  derivation that attributes all of a test's time to drawing; the wave-50 rule
  applies — reproducing a figure with its original method only confirms the
  method.) Wall clock is reported as **interleaved** pairs (A,B,A,B,A,B) with
  min and median and the raw runs, never two blocked batches.
- **AC-6** (guard, no corpus shrink): *Given* the converted tests, *then* **no
  corpus minimum is lowered and no declared-uncertainty bound is loosened**:
  `checked >= 200` (`:432`), `at_cap >= 20` (`:437`), `below_book_floor >= 20`
  (`:438`), `counted >= 150` (`:535`), `shared_binds >= 1` (`:546`),
  `checked >= 100` (`:727`), `counted == len(puzzles)` (`:851`),
  `two_up >= 5` (`:853`), `single >= 5` (`:854`), and the windowing bounds
  `windowed * 10 <= checked` (`:435`, `:538`),
  `windowed * 10 <= checked * 4` (`:732`), `two_up_tops.isdisjoint(single_tops)`
  (`:848`). (**gate**: each named line read at HEAD and compared; AC-1's AST
  multiset covers it too, and this list is the explicit cross-check.)
- **AC-7** (guard, no test lost): *Given* the file, *then* its collected node-id
  set is unchanged. (**gate**: set difference over sorted node ids between the
  fork point and HEAD with `-o addopts=''`; **removals must be 0**, additions
  permitted and each named on the card. Baseline: **4 node ids**.)

## Guardrails

- **G-1: every pixel claim stays a pixel claim.** Nothing in this file becomes a
  plan or layout assertion. This is the line between this card and CARD-219:
  that card asserts the plan *instead of* the pixels, and its own G-1 forbids
  converting `pdf_pages` round trips. **This card keeps the round trip and
  changes only how the pages arrive.** A round that finds itself replacing
  `drawing_of(page)` with a `compute_layout` reading has left its scope.
- **G-2: `Sheet` stays independent.** The oracle at `:124` is a deliberate second
  implementation of the geometry (CLAUDE.md: "prefer an independent second
  implementation"; the `brute_force_oracle.py` precedent). It is never replaced
  by, or re-derived from, calls into `export/layout.py`. Losing that
  independence would make the file's four tests tautologies over the function
  they verify.
- **G-3: no test deleted, renamed, skipped or merged; no assertion removed or
  weakened** (AC-1, AC-7).
- **G-4: corpus minimums are never lowered** (AC-6).
- **G-5: do not edit `src/**`.** `interior_stream` already provides what this
  card needs. If a walk turns out to need a seam that does not exist, that is a
  finding to raise with its measurement, not a production change to make in a
  test-only card. In particular: **do not "fix" `interior_pages`** — it has
  callers and its docstring already states its cost.
- **G-6: do not buy time by guarding less.** No sampling of a claim, no reducing
  a corpus, no `--tb=no`, no narrowing a selection to make a figure look better.
- **G-7: out of scope** — CARD-208's clue-box geometry and the new test its G-1
  adds to this file; CARD-219's six files; the `Sheet` oracle's own shape.

## The census trap this file is one docstring line away from

`meta/profiling/rank_durations.py:45` defines the render-heavy set by grepping
eight idioms over `tests/**/*.py`, and `tests/test_suite_profile.py:482` asserts
that live grep **equal** to the 33-entry `RENDER_HEAVY_SNAPSHOT`. This file is in
the snapshot — and **its entire membership rests on a single mention, in a
docstring**: `:563`, a Sphinx cross-reference to
`…BookPDFGenerator.solved_puzzle_page` inside `MirroredMargins`' own docstring.
Every other idiom count in this file is **zero**.

So **editing that docstring — which a card rewriting this test's mechanism is
very likely to do — silently drops the suite's most expensive render-verified
file out of the render-heavy census and reds `test_suite_profile.py`.** Check it
before committing.

The good news runs the other way: the mechanism this card adopts is
`interior_stream`, which **is itself one of the eight idioms**, so a converted
test keeps the file in the census by its own new code. Note on the card which
idiom holds membership after the change, so the next reader is not relying on a
docstring reference again. And heed `rank_durations.py:126`'s standing caveat:
the set is a **mention** grep by construction, so after this card the file's
membership says nothing about how much it renders.

## Scheduling — this card and CARD-208 serialize, and either order is allowed

`tests/property/test_book_pdf_geometry.py` is also in **CARD-208**'s `Touches:`
(printed clue numbers in ruled boxes), and CARD-208's G-1 adds a **new** test to
this very file (`PropertyTest_BookPdfGeometry_GridUnchangedByClueBoxes`). The two
cards must not run concurrently. `Depends on:` is deliberately left empty so the
order stays the owner's, and each order carries one obligation:

* **CARD-208 first** (cleaner): this card then converts five tests in one pass.
  **Resolved 2026-10-24, same day:** CARD-208 was decomposed on the owner's
  request and is now dispatch-ready — seven ACs became **thirteen** (AC-8..AC-13
  cover the 5 % grey shading, which previously had none, so its gate could have
  passed green with the shading absent), `Depends on:` gained CARD-222 as its own
  amendment had instructed, and the missing mockup is recorded as settled by
  measurement under ADR-0037/R2's precedent rather than as a blocker. One
  non-blocking owner question is flagged on it (whether "clue areas shaded" means
  each number's box or the whole gutter band).
* **This card first:** then **CARD-208's brief must say to write its new test on
  the lazy walk**, not on `interior_pages`, or this card's work is partly undone
  by the next one. Write that into CARD-208 at dispatch, not afterwards.

CARD-208 is **not** a prerequisite for the saving and never was — the record of
why is in CARD-219's `[DISPATCH]` §9, which withdraws my earlier claim that it
was.

## Architecture context

- **FR:** none changed. The file verifies FR-030 (page count / cell fitting),
  EC-019's PDF half (every page is the trim) and AC-276's top-edge figure; this
  card changes none of those statements.
- **ADR:** ADR-0036/R2 (the layout functions own geometry — which is why `Sheet`
  must stay an independent oracle rather than becoming a second reader of
  `compute_layout`), ADR-0039/R1 and R2 (AC-3/AC-4's guard and its controls).
- **CON:** CON-018, CON-020 — untouched.
- **Components:** none. Test tree only; it consumes COMP-009's existing lazy
  seam (`interior_stream`, CARD-145).
- **Trace:** not applicable.

## Worktree notes

- **Related cards, so the residue is not re-derived a third time.** CARD-219
  (in flight, wave 57) converts positional claims in six *other* files and is
  fenced out of this one; CARD-220 retires redundant tests with a named
  survivor; CARD-287 takes `tests/test_book_export_interior_cover.py`
  (344.29 s, 24.4 % of the suite); CARD-286 takes the derivation behind it.
  **This card is none of those**: it neither converts a claim nor retires a
  test. It stops drawing pages nothing reads.
- The census plugin that produced this card's table is
  `card_288_page_census.py` in the dispatching session's scratchpad. It is
  **deliberately not in the repo**: a probe under `tests/` joins the frozen
  render census by its own text. Rebuild it from the table above rather than
  importing it; the shape is a `pytest_runtest_call` wrapper plus wrappers on
  `BookPDFGenerator.interior`, `page_ink.drawing_of` and
  `two_up_ink.drawings_of`. Note that the test module does
  `from tests.helpers.page_ink import drawing_of`, so it holds its **own**
  reference and the module globals must be rebound after collection — patching
  only the helper module silently counts zero.
