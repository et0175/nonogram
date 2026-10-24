# CARD-289: `interior_stream` decides two page positions and carries neither, so the tests re-spell them — and a re-spelling cannot witness the thing it re-spells

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/289-carry-the-positions-the-walk-decided
**Worktree:** —
**Source:** CARD-219's implementation round raised it under G-5 (a finding it was forbidden to fix); CARD-219's review cycle 1 found the mechanism and ruled it "a successor card to CARD-219, not CARD-220's"; the orchestrator measured it at the fix pre-gate. 2026-10-24.
**Idea:** —
**Wave:** —
**Created wave:** 57
**Deferred waves:** 0
**Depends on:** CARD-219
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_toc.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

### The defect, measured on both arms of CARD-219's diff

`BookPDFGenerator.interior_stream` is the seam that "splits the interior into the
part that **decides** and the part that **draws**, and does all of the first
before any of the second". It decides two positions eagerly and then **throws
both away**:

* **`first_answer_page`** — computed at `book_pdf_generator.py:6718` and read only
  at `:6734`, `:6786`, `:6976` and `:6978`, all inside the method. It is on no
  returned value.
* **`toc_entries`** — the rows the walk actually lists, built locally in the same
  method and likewise returned to nobody.

`InteriorStream` carries `page_count`, `unpaired_page_count`,
`answer_page_count`, `paired_only_page_count` and `pages`. **Neither position is
among them.**

**The consequence is not aesthetic, and CARD-219 measured it.** A test that wants
to assert a *position* has no pure surface to read it from, so it re-derives the
term — and a test-side re-derivation of a production term **cannot witness that
term being wrong**. CARD-219 converted seven positional tests in
`tests/test_book_toc.py` to read the plan, and its `_planned_rows` had to
**supply** the solutions page to `structural_toc_entries`, supplying
`_solutions_divider_page(decided)` — **a test-side re-spelling of
`first_answer_page`**, where production builds the same rows at `:6786` with its
own. Two mutants, each run on both arms:

| mutant | base cells | after conversion | lost |
|---|---|---|---|
| off-by-one in `first_answer_page` (`:6718`) | **4** | **3** | `TestBookToc_PageNumbersMatchTheWalk::test_each_row_points_at_the_page_the_walk_planned` |
| off-by-one in the TOC page walk (`:6923`, `range(toc_page_count + 1)`) | **21** | **14** | **exactly the seven converted tests** |

Nothing escapes today, because the drawn tie survives in **three tests and
nowhere else** — the three CARD-219 fenced onto CARD-220. But the reason the
conversion cost anything at all is this missing surface: **the position the test
wanted was decided, and discarded, three lines before the test could ask for
it.**

### The scale, so this card is not mistaken for a tidy-up

`TITLE_PAGE_COUNT` — one of the terms a front-matter position is summed from — is
re-spelled **107 times across six test files, one helper and one fixture**:

| file | occurrences |
|---|---|
| `tests/test_book_export_interior_cover.py` | **56** |
| `tests/test_book_pdf_memory.py` | 24 |
| `tests/test_book_toc.py` | 15 |
| `tests/test_book_page_numbers.py` | 9 |
| `tests/test_book_solved_answer_key.py` | 1 |
| `tests/property/test_book_export_interior.py` | 1 |
| `tests/helpers/book_corpus.py` | 1 |
| `tests/fixtures/book_baseline_card206.json` | 1 |

**This card does not retire 107 re-spellings.** It builds the surface and
converts the three that CARD-219's measurement proved load-bearing. The rest
belong to whoever is already in those files — notably CARD-287, which owns the
file holding 56 of them. Said explicitly because the tempting shape here is a
`tests/**` card, and that is CARD-220's charter, not this one's.

### What to do

1. **Carry the two positions on `InteriorStream`.** Add `first_answer_page: int`
   and the TOC rows the walk listed (a tuple, not a list — the class is
   `frozen=True`/`slots=True` and the rest of its fields are values). Set them
   from the terms already computed at `:6718` and in the TOC block; **compute
   nothing new** — if a field needs a fresh derivation, that is the signal the
   position is not actually decided there, and it is a finding.
2. **Document them the way the class documents the rest** — `InteriorStream`'s
   docstring already explains each field and explicitly says `pages` is a
   single-use generator that holds nothing. The two new fields are *decided*
   values and must say so, because the whole point is that reading them draws
   nothing.
3. **Convert the three carriers in `tests/test_book_toc.py`** to read the
   positions off the returned value instead of re-spelling them, and **delete the
   test-side `_solutions_divider_page` re-spelling** CARD-219 had to write.
4. **Re-run both mutants above, on both arms, and record the cell counts.** The
   card is done when the `first_answer_page` mutant reds **at least the 4 cells it
   red before CARD-219**, with the positional tests among them — i.e. the
   coverage CARD-219 paid is bought back, not merely relocated.

## Acceptance criteria

<!-- Every `test:` names something that exists or will exist in this card; every
**gate** states the measurement run. Written under the F-003 rule from CARD-218's
review cycle 1: eight fictional `TestCuration_*` verifiers were once named across
three cards and none existed. -->

- **AC-1** (happy): *Given* a book, *when* `interior_stream(...)` returns, *then*
  `first_answer_page` and the TOC rows it listed are on the returned
  `InteriorStream`, and reading them draws **no page**. (test:
  `TestInteriorStream_CarriesThePositionsItDecided` — the no-draw half asserted
  with a counter on the page-producing methods, not a stopwatch.)
- **AC-2** (happy, agreement with the walk): *Given* any book, *when* the stream's
  pages **are** walked, *then* the divider actually yielded at
  `first_answer_page - 1` is the page the field names, and the rows drawn are the
  rows the field lists. (test:
  `PropertyTest_InteriorStream_TheCarriedPositionsAreThePagesDrawn` — seeded
  corpus, stdlib `random.Random`, minimum case count asserted inside the test,
  **no `hypothesis`**.)
- **AC-3** (guard, the coverage is bought back — this is the card's point):
  *Given* an off-by-one injected into `first_answer_page` (`:6718`), *when* the
  converted tests run, *then* they fail. (**gate**: re-run the mutant on both
  arms and record the cells; **at least 4 cells must red, with the positional
  tests among them**, against the 3 CARD-219 left behind. A standing test cannot
  know "before this card".)
- **AC-4** (guard, no test-side re-spelling left in the converted three): *Given*
  the three carriers, *then* none of them computes a page position from a sum of
  production constants — each reads it off the returned value. (**gate**: the
  three named by node id, each with the line it reads its expectation from.
  `_solutions_divider_page` is gone or no longer used by them.)
- **AC-5** (guard, no coverage loss): *Given* the touched files, *then* their
  collected node-id set is unchanged. (**gate**: set difference with
  `-o addopts=''`, **removals 0**; additions permitted and each named. Baseline:
  `tests/test_book_toc.py` collects **53**.)
- **AC-6** (edge, the empty book): *Given* a book with no puzzles, *then*
  `first_answer_page` is still well defined and the carried rows are empty, and
  nothing raises. (test: `TestInteriorStream_TheEmptyBookStillHasPositions`)
- **AC-7** (guard, the exports are untouched): *Given* any generation request,
  *when* the CLI or web UI writes a PNG, SVG or PDF, *then* the bytes are
  identical. (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`,
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` — both existing, both G-4.)

## Guardrails

- **G-1: add a surface, do not move a decision.** The positions are already
  decided at `:6718` and in the TOC block. This card **carries** them; it does
  not recompute, relocate or re-derive them. A second derivation of a page
  position is the defect this card exists to remove, not a way to implement it.
- **G-2: `pages` stays lazy and single-use.** `InteriorStream.pages` is a
  generator that "holds none of them — a page is built when it is asked for"
  (CARD-145, and the shape the deployed panel was OOM-killed by before it). A new
  field must not force the walk, materialise a page, or make the class hold one.
  Assert it: AC-1's no-draw half.
- **G-3: no test deleted, renamed, skipped or merged** (AC-5).
- **G-4 untouchable:** `PropertyTest_Solver_NeverFalsePositiveUniqueness`
  (CON-005/EC-001), `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`
  (ADR-0036/R1), `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  (CON-019).
- **G-5: the three fenced carriers are not retired here.** CARD-220 carries the
  fence; this card's job is to make their coverage **expressible on the plan**, at
  which point retiring one becomes a decision with evidence instead of a guess.
  Until AC-3's cell count is recorded, they stay.
- **G-6: out of scope — the other ~104 re-spellings.** Named above with their
  files so nobody re-derives the census. `tests/test_book_export_interior_cover.py`
  holds 56 and belongs to CARD-287.
- **G-7: do not buy the mutant's cells by weakening a corpus or narrowing a
  selection.** AC-3 is a cell count on the whole file.
- **G-8: no new runtime dependency** (ADR-0006/R1: stdlib + Pillow + NumPy). **No
  `hypothesis`** — AC-2's property test builds a seeded corpus by hand.

## Architecture context

- **FR:** FR-030 (the book's page count), FR-040/FR-041 (pairing and the level
  dividers), FR-042/FR-043 (the answer key and page numbering) — **no requirement
  changes**; this card adds a read surface to a value the pipeline already decides.
- **ADR:** ADR-0036/R2 (geometry is COMP-007's; this card touches positions, not
  geometry — do not let a page *position* field drift into carrying a *layout*
  value). CARD-145's lazy-interior decision is the constraint behind G-2.
- **CON:** CON-019 (AC-7), CON-005 (G-4).
- **Components:** COMP-009 (`book_pdf_generator.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- **Scheduling.** `src/nonogram/admin/book_pdf_generator.py` is a declared
  `conflict.hotspots` entry, so the dispatcher serializes this against CARD-207,
  CARD-208, CARD-209 and CARD-289's other hotspot neighbours regardless of overlap
  score. `Depends on: CARD-219` because this card converts the three tests
  CARD-219 created and fenced — dispatch it after that merge, or the diff is
  written against a file that is about to change.
- **Why this is not CARD-220's.** CARD-220 retires tests whose coverage another
  test already provides, and has **no `src` mandate**. The defect here is a
  missing production surface; retiring a test would hide it. Ruled by CARD-219's
  review cycle 1 and recorded on CARD-220.
- **The one honest risk.** Adding fields to a `frozen=True, slots=True` dataclass
  that the export path constructs is a small change with a wide blast radius —
  every constructor call site must pass them. Find the call sites by AST, not by
  grep, and say how many there were.
