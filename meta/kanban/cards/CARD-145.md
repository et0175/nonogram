# CARD-145: The book PDF is written a page at a time, so a real book fits in memory

**Status:** done
**Priority:** P0
**Category:** bug
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/145-stream-the-book-pdf
**Worktree:** ../PythonProject4-CARD-145
**Source:** owner, 2026-09-24 ("render crashes when I try to generate pdf")
**Idea:** —
**Wave:** 26
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/app.py, tests/test_book_pdf_memory.py
**Review score:** 9.0 (cycle 3/3)
**Started:** 2026-09-24
**Closed:** 2026-09-24
**Actual:** 1d
**Merge commit:** 554c437 (branch head 7b092b8; the dispatcher merges)
**Blocked by:** —

## What to implement

`interior_pages` builds every page as a full-resolution `Image` and returns them as a list
(book_pdf_generator.py:1028, 1141-1182); `_save_pdf` then hands the whole list to Pillow
(1201-1222). At 300 DPI an 8.5x11 page is 2550 x 3300 px RGB = **24.1 MB**, so peak memory
is 24 MB x the page count, plus whatever the PDF encoder buffers:

| pages | held at once |
|-------|--------------|
| 10    | 0.24 GB |
| 20    | 0.47 GB |
| 50    | 1.18 GB |
| 150   | 3.53 GB |

The deployed panel has 512 MB. A book of ~20 pages exhausts it and the worker is OOM-killed
— no traceback, which is why the owner saw a crash rather than an error. A 150-page Book 1,
the product's actual target (120-190 pages, CON-018), was never within reach on any
instance size this project would pay for. It works locally only because a laptop has 30-60x
the memory.

This is the export's shape, not a leak: no amount of instance is the fix, and neither is
tuning. **A page must be written and released before the next is built.**

1. **Stream the pages.** Rework the export so peak memory is O(one page), not O(the book).
   `reportlab` is already an installed dependency of the panel and can write a page and
   move on; Pillow's `save_all` cannot. Whatever the mechanism, the constraint is the one
   the test pins: peak resident memory must not grow with page count.
2. **Keep the page images identical.** Pages are still drawn exactly as they are drawn today
   — same layout calls, same geometry, same ink. This card changes *when a page is released*,
   not what is on it. A page rendered before and after this card must be pixel-identical.
3. **Both files.** The interior and the separate cover file (INV-013) both go through the
   new path; the cover is one page and is not the problem, but it must not keep the old one
   alive beside the new.
4. **Report progress, do not block silently.** A 150-page book takes real time to write; the
   route must not appear hung. Reuse the batch screen's existing progress convention rather
   than inventing one, or — if that is too large here — say so on the card and leave a
   note, but do not ship a route that looks dead for two minutes.

Out of scope: reducing the per-page bitmap (bit depth, DPI, compression) — worth doing and
worth its own card, but it only moves the cliff, it does not remove it; changing what is on
a page; and the answer-key packing (CARD-134's).

## Acceptance criteria

- New: peak memory while exporting does not grow with the page count — a 150-page book's
  peak is within a small constant of a 10-page book's.
  test: TestBookPdfMemory_PeakDoesNotGrowWithPageCount
- New: a 150-page book exports successfully under a memory cap that the current code fails.
  test: TestBookPdfMemory_RealBookExportsUnderTheCap
- New: every page of an exported book is pixel-identical to the same page before this card.
  test: TestBookPdfMemory_PagesAreUnchanged
- New: the interior and cover are still two files, with the interior starting at the guide
  page and holding no cover page.
  test: TestBookPdfMemory_InteriorAndCoverStillSeparate

## Guardrails

- G-1: Page content is unchanged. Every existing book-PDF test stays green unedited —
  CARD-116's geometry, CARD-117's bands, CARD-127's pairing, CARD-134's answer key.
- G-2: INV-013 — the interior holds no cover page, starts at the guide page, and parity
  counts from interior page 1.
- G-3: CON-019 — CLI and web output are untouched; `src/nonogram/export/**` and
  `tests/fixtures/a4_golden/**` must not be edited by this card.
- G-4: ADR-0006/R1 — no NEW runtime dependency. `reportlab` is already installed for the
  panel; adding anything else needs the ADR revisited, not a line in requirements.txt.

## Architecture context

- **FR:** FR-041, FR-043 (interior and cover)
- **NFR:** the deployed panel's memory envelope — this card is the first thing in the
  project to state one
- **INV:** INV-013
- **ADR:** ADR-0036, ADR-0006 (dependency baseline)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## System contract

Assembled at review time by `architect-validate/scripts/system_rules.py --card CARD-145`
(44 rules applicable to this card's scope). The card as cut carried no such section — a
decompose gap, noted rather than back-filled by hand — so this list is the fresh set from
the model, not a projection frozen at decompose time.

- ADR-0006/R1
- ADR-0019/R1
- ADR-0022/R1
- ADR-0022/R3
- ADR-0022/R4
- ADR-0024/R1
- ADR-0024/R2
- ADR-0024/R3
- ADR-0024/R4
- ADR-0024/R5
- ADR-0027/R1
- ADR-0027/R2
- ADR-0029/R1
- ADR-0029/R2
- ADR-0029/R3
- ADR-0029/R4
- ADR-0029/R5
- ADR-0032/R1
- ADR-0032/R2
- ADR-0033/R1
- ADR-0035/R1
- ADR-0036/R1
- ADR-0036/R2
- ADR-0037/R1
- ADR-0037/R2
- CON-005
- CON-009
- CON-010
- CON-011
- CON-012
- CON-015
- CON-016
- INV-001
- INV-002
- INV-003
- INV-005
- INV-006
- INV-007
- INV-008
- INV-009
- INV-010
- INV-011
- INV-012
- INV-013

## Failure matrix

Declared before the code was written; every numeric bound below was then measured on
this machine (Book 1 profile, 300 DPI, the 150-puzzle corpus in
`tests/helpers/book_corpus.py`, which yields a **179-page** interior).

| # | Boundary | Failure mode | Declared behaviour | Numeric bound |
|---|----------|--------------|--------------------|---------------|
| F-1 | `export_interior` — memory envelope (`export_book`'s own is F-6) | peak bytes held while exporting an N-page book | **Before:** every page built into a list, then written. Peak = N x one page bitmap + the file. **After:** **no page survives the call that builds the next one**, so the panel *retains* **exactly 1** x page bitmap however long the book is. The **process** holds one more, and it is named here rather than rounded away: COMP-007's `render_pages` draws a blank page *and* a solved page from one payload, and `_blank_page` binds `blank, _ = render_pages(...)`, so that discarded page is alive until the frame returns. It is a **constant** — every puzzle page pays it, none accumulates it — and it is the merge-base's code untouched (G-1). Process peak = 2 x page bitmap + the file written so far. Not O(1) — the file is a real linear term and is named as one. | page bitmap = 2550x3300x3 = **25,245,000 B**; written file = **0.457 MB/page** (measured, 179 pages → 81,856,812 B). Before, N=179: 179 x 25.245 MB = **4.52 GB** (+ file) against a 512 MB instance. After, N=179: **retained** 25.2 MB; **process** 50.5 MB of bitmap + 81.9 MB of file = **132.3 MB**, about a quarter of the instance (26 % on the decimal-MB reading that made the earlier one-bitmap figure 107.1 MB / 21 %). The second bitmap is measured, not inferred: registering both pages `render_pages` returns gives a peak of **50,490,000 B = 2.00 page bitmaps** with **10** pages registered on the 8-page book and **329** on the 179-page one — the *same* bytes at 22x the length, which is what says it is a constant. The **retained** figure is asserted as an **equality**: peak live page bitmaps **== 1 x 25,245,000 B** on the 8-page book and on the 179-page one (a ≤ 2-page cap is kept beside it, but it is not what pins the property — the shape one `del` away measures 2.00 exactly and passes a `≤ 2` cap). Tests: `TestBookPdfMemory_PeakDoesNotGrowWithPageCount::test_neither_book_holds_more_than_one_page_bitmap`, `TestBookPdfMemory_RealBookExportsUnderTheCap::test_its_peak_page_memory_is_one_page_bitmap`. Mutation-proved: removing the `del page` in `_write_pdf`'s loop, in `_as_planned` or in `produce()` each raises the measured peak to exactly 2.00 and fails these two. Those `del`s are **this** row's mechanism and only this one — they hold between *consecutive pages of a multi-page walk*; they do nothing for a one-page file and are not what keeps the cover apart from the interior (see F-6). **The whole-process bound is also executed, not only instrumented:** `TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under` exports this book in a spawned interpreter under a **807,840,000 B (32 page bitmaps)** process-level cap — the streaming shape finishes and reports 179 pages read back out of the file it wrote, peaking at **150.8-169.9 MB** resident over five runs; the list shape is killed by the cap at 828 MB after 0.89 s. `::test_the_same_pair_under_an_address_space_cap_the_kernel_enforces` is the same pair under `setrlimit(RLIMIT_AS)` and **skips on macOS** (see the `[AC-2, executed vs arithmetic]` note). |
| F-2 | `_write_pdf` — a page fails to render at page *k* of *N*, with *k-1* pages already in the output buffer | streaming means bytes exist before the export is known to succeed | The exception propagates unchanged (`RuntimeError: puzzle <id> could not be drawn: ...`). **No partial or truncated PDF can reach a caller or a route.** Mechanism: the output `BytesIO` is a **local of `_write_pdf`** and is returned only after `write_xref_and_trailer()`; on a raise the frame dies and the partial bytes go unreferenced. There is no `finally` that flushes, no buffer passed in, no attribute holding it. | Measured: a failure at page 6 of 8 leaves **5 pages** of real bytes in the buffer and the caller receives an exception and no file — `TestBookPdfMemory_NothingHalfWrittenEscapes::test_a_page_that_fails_at_page_6_of_8_hands_the_caller_nothing`. |
| F-3 | `_write_pdf` — the producer yields **fewer** pages than the plan declared | the object table is pre-allocated, so a short stream leaves the page tree pointing at image/page/contents ids that were never written — a structurally corrupt PDF | `_as_planned` raises `RuntimeError: interior has {produced} pages, its page plan says {planned}` at the end of the walk, **before** `write_xref_and_trailer()`. The trailer is never written, so the corrupt file cannot even be closed, let alone returned. | Exact equality, no tolerance: produced == planned. Test: `test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer`. |
| F-4 | `_write_pdf` — the producer yields **more** pages than the plan declared | the surplus page has no object id; writing it would emit objects nothing references and a page count that lies | `_as_planned` raises `RuntimeError: interior has at least {produced} pages, its page plan says {planned}` **in place of** the surplus page — it is refused before it is written, which is strictly earlier than the old `len(pages) != planned` check could refuse it. | Exact equality. Test: `test_a_producer_that_yields_too_many_is_refused_before_the_extra_page` (asserts the 4th page was asked for and then refused). |
| F-5 | the three existing `interior()` tripwires | one of them can no longer run over a list | `the page plan prints ...` — **unmoved**, still eager, raises from `interior_stream` before any writer exists. `the answer key holds ...` — **moved earlier**: it used to run after every puzzle page was drawn, it now runs beside the other tripwire, before anything is drawn. Safe: it is a check over `interior_stream`'s own *input* (the surviving payloads) and the key walk's output, neither of which a drawn page can change; moving it earlier can only make it fire sooner. `interior has N pages, its page plan says M` — **moved into `_as_planned`**, from a `len()` over the finished list to a count taken as the pages go past. Safe and stricter: the under-count message is unchanged and still fires before the trailer, and the over-count now fires *before* the extra page is written instead of after. | Tests: `test_the_plan_tripwires_still_run_before_a_byte_is_written` (new), plus the two unedited guards in `tests/test_book_pdf.py::TestBookPdf_PagePlanGuardIsLive`, which still assert the exact strings `interior has 4 pages, its page plan says 5` and `the page plan prints [1, 2], not puzzles 1..3`. |
| F-6 | `export_book` — both files, and the cover in particular | the cover must not keep a page alive beside the interior's (card item 3) | The cover goes through the same `_write_pdf` as the interior, and **nothing in `export_book` ever holds a page**: `_write_pdf` retains no page after writing one and returns a `BytesIO`, and `BookExport.cover` is that `BytesIO`, not an `Image`, so the cover page does not outlive the `export_cover` call. `export_book` finishes the interior file before the cover page is built, but **that order is not what the bound rests on** — and neither is `_cover_page`'s laziness. This row therefore claims **no ordering and no laziness property**: the cover half rests on nothing holding the page. What a test does catch is `export_book` binding a page itself. The four `del page` sites pin the **interior** half (F-1), consecutive pages of a multi-page walk; for a one-page file they do nothing. | Measured on `export_book` itself, not inferred from `export_interior` (`export_book` does not delegate to it — it has its own `interior_stream` + `_write_pdf` pair): over the 8-page baseline book, **9 pages pass the instrument** (8 interior + 1 cover) and the peak is **exactly 1 x 25,245,000 B**. Test: `TestBookPdfMemory_InteriorAndCoverStillSeparate::test_the_whole_book_holds_one_page_bitmap_at_a_time`. **Positive control** — the shape this row is about, and the evidence the measurement has teeth: `export_book` binding the page itself (`cover_page = self.create_cover_page(...)` before the interior write, written afterwards) measures **2.00** and fails that test. **Mutants that do *not* move it, each 1.00 with 25 tests passing:** the two statements swapped so the cover is built first; folded back into one `BookExport(cover=..., interior=...)` call with `cover=` evaluated first; `_cover_page` made eager *and* the cover built first. Cover-first with `_write_pdf`'s `del page` neutralised measures **2.00**, not 3.00 — the cover is provably already dead before the interior walk begins. The other old mutant still holds: an `export_book` that materialises the interior (the old list shape) measures **9.00** and fails. `PAGE_FACTORIES` is an **instrument** property, not a production mechanism — it is what lets a test *see* a page held outside the writer, which the positive control's failure proves; `::test_a_page_built_outside_the_writer_is_still_seen` is its non-vacuity check. |
| F-7 | the file itself (G-1, CON-019 in spirit) | a change of writer changes the bytes | The new writer mirrors `PdfImagePlugin._save`'s `mode == "RGB"` path object for object. The only difference between the old file and the new is the two `Info` timestamps. | Both halves now **asserted**, not only recorded: **byte length identical, 2,210,622 B** — `TestBookPdfMemory_PagesAreUnchanged::test_the_interior_file_is_the_length_it_was_recorded_with` against the fixture's `interior_bytes` — and all 8 pages' decoded pixels identical by sha256 — `::test_every_page_is_pixel_identical_to_the_recorded_one`. Both against `tests/fixtures/book_baseline_card145.json`, recorded at the merge-base `b4c523d`. A machine that letters the guide page and the divider in another face skips **those two pages** and the byte-length half, and still compares the other six (fixture: `font_dependent_pages`). |
## Worktree notes

- [Origin] Owner, 2026-09-24, on the deployed panel: "render crashes when I try to generate
  pdf". No traceback in the logs, which is the signature of an OOM kill rather than an
  exception. Diagnosed by arithmetic: 2550 x 3300 x 3 bytes per page x the page count,
  against a 512 MB instance.
- [Why P0] This blocks the product's actual deliverable on the only deployment there is.
  Every other book card is upstream of a PDF nobody can generate.
- [Scheduling] Runs FIRST in wave 26 and alone, before CARD-128: both restructure
  book_pdf_generator.py, and CARD-128's divider pages should be written against the
  streaming path rather than retrofitted into it.
- [Workaround while this is open] Generate locally against the deployed database
  (`DATABASE_URL=<Render external URL>`), where memory is not the constraint.
- [Env] forge unknown (no executing plugin manifest at
  `~/MyProjects/forge_1/.claude-plugin/plugin.json`); no `meta/.skills.yml`, so no
  `min_version` to compare against and no skew gate to apply. Defaults in force:
  review on, min_score 8, max_cycles 3, min_improvement 0.5, build_fix_attempts 2,
  scope_gate on, tdd false, standards on, no models block (agents spawned without
  an explicit model).
- [Card defect] No `## Failure matrix` section on the card as cut, though
  `Complexity: architectural` requires one. Not stalled on: the implementation agent
  was told to DECLARE the matrix in the worktree copy before writing code, with the
  memory envelope (peak bytes per N-page book, before and after) as the failure mode
  to reason about, plus the three boundaries streaming actually introduces — a page
  that fails to render after k pages are already in the output buffer, a producer
  that yields fewer pages than the pre-allocated object table declares, and which of
  `interior()`'s existing plan tripwires still run before the first byte is written.
- [Spike] Orchestrator ran two spikes against b4c523d before dispatching, to settle
  the mechanism rather than pay a review cycle for it:
  (1) **reportlab, which the card suggests, is a trap here.** It writes an
  unsuppressible comment inside the PDF trailer dictionary
  (`reportlab/pdfbase/pdfdoc.py:189`), and Pillow's `PdfParser` — what
  `tests/helpers/pdf_pages.py` reads book PDFs with — raises `PdfFormatError` on it.
  Every existing test that reads book pages would fail, and the only way past it is
  editing the shared helper: a G-1 problem, not a solution.
  (2) **Pillow's own `PdfParser` writer streams.** `PdfImagePlugin._save` needs the
  whole page list only because it pre-allocates three object ids per page before the
  catalog — and the page count is already known here before a page is drawn. Measured
  on a 4-page document: every image, page and contents object byte-identical to
  today's `save_all` output, filter still `DCTDecode`, `tests/helpers/pdf_pages.py`
  reads it unedited; the only difference was the `Info` object's two timestamps.
- [Measured] Book 1 profile, 20x20 easy puzzles, on this machine: page bitmap
  2550 x 3300 RGB = 25.2 MB (the card's 24.1 MiB); ~0.015 s to render a page and
  ~0.013 s to write it; written PDF ~0.25-0.47 MB/page. So a 190-page book is a few
  seconds of work, not the two minutes card item 4 feared — the implementation agent
  was asked to measure a real 150-puzzle export end to end and let that number decide
  item 4 rather than assume it.

### Structural decisions

- STRUCTURE: **`interior_stream(puzzles) -> InteriorStream` is the new lazy core; `interior()`
  and `interior_pages()` become the materialising convenience over it** — because the card's
  two obligations pull in opposite directions. The export must never hold a list; a dozen
  existing tests (`test_book_pdf.py`, `test_book_pdf_two_up.py`, `test_book_pdf_band.py`,
  `test_book_proof_pages.py`, and `test_book_export_interior_cover.py`, which monkeypatches
  `interior_pages` by name) must keep working unedited. One walk with two endings satisfies
  both: `interior()` is now three lines over `interior_stream`, so the two cannot drift.
- STRUCTURE: **`InteriorStream` carries the three page counts *and* the generator** — rather
  than a counts-only object plus a separate `pages()` call. `export_book` has to report
  `interior_page_count`, `unpaired_interior_page_count` and `answer_page_count` without
  materialising anything, and all three are the page plan's own arithmetic, known before a
  pixel exists. Putting them on the same value as the producer is what makes "do not
  materialise to count" the obvious thing to write rather than a discipline to remember.
- STRUCTURE: **the page producer is a closure (`produce()`) inside `interior_stream`, not a
  seventh private method** — it needs the plan, the key, the payloads, the ids, the tier
  counts and the titles, and passing six of those through a signature would be a private
  method existing only to be given its own locals back. The closure also makes the
  eager/lazy split visible in one screen: everything above `def produce()` runs before the
  method returns; everything inside it runs one page per `next()`.
- STRUCTURE: **no page outlives the yield that hands it on** — a page is either yielded as
  an expression or bound, yielded and immediately `del`eted; `_as_planned` and the writer's
  loop do the same. This is load-bearing, not style: it is the difference between a peak of
  1.00 and 2.00 page bitmaps, and CARD-128 must keep it when it adds divider pages.
- STRUCTURE: **no `yield` sits inside the `except Exception` that names an undrawable
  puzzle** — the page is built inside the `try` and handed on outside it. A `yield` under
  that handler would also catch anything a consumer threw back into the suspended walk and
  report it as an undrawable puzzle.
- STRUCTURE: **`_as_planned(pages, page_count)` is a module-level generator, and the
  streaming replacement for the `len(pages) != planned` check** — placed both on
  `interior_stream`'s producer (so `interior()` keeps the tripwire too) and inside
  `_write_pdf` (so the writer validates whatever iterable it is actually given, including
  the cover's). Two integer increments per page; the object table it protects is the
  writer's own.
- STRUCTURE: **`_save_pdf(list)` becomes `_write_pdf(pages, page_count)` + `_write_page(...)`**
  — the page count is a *parameter*, not a hint, because the PDF's object table is laid out
  from it before anything is drawn. `_write_page` is `PdfImagePlugin._write_image` plus the
  body of its `_save` loop for an RGB image, inlined because the plugin only offers them
  behind a call that wants every page at once.
- STRUCTURE: **no component, no arrow, no diagram change.** This is an internal
  restructuring of COMP-009 (`meta/architecture/c4/components-CTX-001.puml` unchanged).
  ADR-0036/R2 is untouched by construction: not one line of geometry moved. `_write_page`
  computes a `MediaBox` from `page.width` and `self.dpi`, which is the same arithmetic
  `PdfImagePlugin` did on the same numbers; no cell is fitted and no grid line is placed
  here, before or after.
- SCOPE: `src/nonogram/admin/app.py` was **not** touched. It calls `export_interior` /
  `export_cover`, whose signatures and return types are unchanged, and item 4 (the only
  thing that would have changed a route) is deferred — see below. Two files outside the
  card's `Touches` are new, not edited: `tests/helpers/book_corpus.py` and
  `tests/fixtures/book_baseline_card145.json`.

### Measured numbers

All on this machine, Book 1 profile at 300 DPI, the 150-puzzle corpus
(`tests/helpers/book_corpus.corpus_puzzles`) → a **179-page interior**
(1 guide + 150 puzzle pages + 1 divider + 27 answer pages). One page bitmap =
2550 x 3300 x 3 = 25,245,000 B (24.1 MiB).

| | before (merge-base `b4c523d`) | after |
|---|---|---|
| peak live page bitmaps, 179-page book | 179 pages = **4.52 GB** | **25.2 MB** = exactly **1.00 page bitmap** |
| peak live page bitmaps, 8-page book | 8 pages = 202 MB | 25.2 MB = 1.00 page bitmap |
| written interior file | 81.9 MB (0.457 MB/page) | 81.9 MB (0.457 MB/page) — unchanged |
| whole envelope (bitmaps + file), 179 pages | 4.52 GB + 81.9 MB | **107.1 MB** — 21 % of the 512 MB instance |
| process `ru_maxrss` delta over the export | — | 95.4 MB (informational only; RSS is not what the tests assert on) |
| wall clock, 179-page book, render + write | 6.44 s | **3.42 s** (the old shape also paid for allocating 4.5 GB) |
| baseline book's interior file | 2,210,622 B | 2,210,622 B, all 8 pages pixel-identical |

- [Instrument] Measured as **live page-bitmap bytes**: a `weakref.finalize` per page against
  its `width*height*len(mode)`, sampled each time a new page is produced, with the probe
  interposed on the real `_write_pdf` seam so what is measured is `export_interior` as a
  route calls it. Both obvious alternatives were tried and rejected with numbers, recorded
  in the test module's docstring and kept live as tests: **`tracemalloc` is blind here** —
  four 2550x3300 RGB images cost 100,980,000 B of bitmap and moved its traced total by
  **35,421 B** (0.03 %), because Pillow allocates in C; **RSS** does see them (`ru_maxrss`
  +134 MB for the same four) but is allocator- and platform-dependent and not a number a
  test can assert on. The instrument is proved non-vacuous by running it over the old shape
  (`interior_pages`, still a list) and asserting the peak rises by exactly one page bitmap
  per page.
- [AC-2, judgement call] **The criterion as written cannot be tested honestly, and the test
  implements the honest version.** "…under a memory cap that the current code fails" has a
  second half that cannot be executed once the current code is gone, and the only way to
  make a cap actually bite — `setrlimit(RLIMIT_AS)` under pytest — is a platform-dependent
  flake that takes the whole session down rather than one test. What
  `TestBookPdfMemory_RealBookExportsUnderTheCap` does instead, all of it real: exports a
  genuine 150-puzzle book end to end and reads 179 pages back out of the PDF (the page count
  is never faked); asserts measured peak ≤ 2 page bitmaps; derives the **old** shape's peak
  for that same book from the instrument's own measured per-page constant (179 x 25,245,000
  = 4.52 GB) and asserts it exceeds the 512 MB envelope by more than 8x; and measures and
  states the residual linear term. The reasoning is written into the class docstring.
- [Residual linear term, stated not hidden] Peak is **O(one page) + O(the written file)**,
  not O(1). The PDF accumulates in the returned `BytesIO` at 0.457 MB/page, so a 179-page
  book still holds ~82 MB of compressed output at the end. That is 55x better than 25.2 MB
  a page and it fits the envelope with the request around it, but the failure matrix and
  `test_the_residual_linear_term_is_the_written_file_and_it_is_small` say it rather than
  claim a constant the code does not have. Removing it too would mean streaming to the
  response socket instead of a `BytesIO` — a real option, but it changes the return type
  that existing tests call `.getvalue()` on, so it is a card of its own, not this one.
- [Deferred] **Card item 4 (progress reporting) is deferred, on the measurement.** A real
  179-page book — larger than CON-018's 120–190 target — exports end to end in **3.42 s**
  (it was 6.44 s before this card). The card feared "a route that looks dead for two
  minutes"; the real number is single-digit seconds, and a progress bar for a 3-second
  request is worse than none. The card explicitly permits this note in place of the work.
  The measurement is kept live rather than left here to rot:
  `test_a_real_book_exports_in_seconds_not_minutes` fails if a book ever takes over a
  minute, which is the trigger to revisit the decision. Nothing in `app.py` was touched as
  a result.
- [Mechanism, and why not ReportLab] ReportLab is a legal choice (it is an installed
  `admin`-extra dependency since 2026-09-11, ADR-0006 history) but it writes an
  unsuppressible `% ReportLab generated PDF document` comment *inside the PDF trailer
  dictionary*, and Pillow's `PdfParser` — which `tests/helpers/pdf_pages.py` reads every book
  PDF with — raises `PdfFormatError: name not found in trailer` on it. Using it would have
  meant editing a shared test helper to accommodate a self-inflicted format change, which is
  a G-1 problem rather than a solution. Pillow's own `PdfParser` is already an incremental
  writer; `PdfImagePlugin._save` needs the whole page list only to pre-allocate object ids,
  and the page count is known here before anything is drawn. No new dependency (G-4 holds):
  `PIL.PdfParser` was already imported by the test helper.
- [G-1 evidence] The baseline was recorded **first**, in its own commit (`7cdea7a`), from the
  untouched merge-base, and verified reproducible twice in one process and twice in separate
  processes before it was written. It is per-page `sha256(Image.tobytes())` taken from the
  pages decoded back **out of the exported PDF**, so it covers draw → JPEG-encode → write →
  parse → decode, and the comparison is exact rather than `same_page`'s tolerant one. After
  the restructure the interior file's **length is identical to the byte** (2,210,622) and
  every page's digest matches. The one machine dependency is the system face the guide page
  and the divider are lettered in (`ImageFont.truetype("…/Arial.ttf")` with a
  `load_default()` fallback) — a pre-existing property of those two pages, not something
  this card introduced. The fixture carries a fingerprint of that face and the test skips
  with an explicit message on a machine that letters them differently, rather than pretending
  to compare.
- [Test cost] `tests/test_book_pdf_memory.py`: **22 tests, 4.59 s**. The 179-page corpus is
  exported once for the whole module (a module-scoped fixture) and shared by AC-1 and AC-2.
- [For CARD-128] Divider pages must be `yield`ed from `produce()` inside `interior_stream`,
  as expressions, and their count must be added to `interior_page_count` — `_as_planned` will
  refuse the export the moment the two disagree, in either direction, so a divider added to
  the walk without a term in the plan fails loudly at the first export rather than shipping a
  corrupt page tree. Nothing may bind a page to a local across a `yield`.
- [Owner] Nothing to eyeball: the pages are proved pixel-identical to the merge-base's, so
  there is no rendered-grid change to look at. What is worth knowing is the deployment
  outcome — a 179-page book now peaks at ~107 MB against the panel's 512 MB, so the OOM kill
  that produced "render crashes when I try to generate pdf" should be gone. That is the one
  thing only the deployed panel can confirm.

### Summary

The export now decides everything before it draws anything, then draws, writes and releases
one page at a time. `interior_stream` returns the three page counts (known from the page
plan, without a pixel) and a one-shot generator; `_write_pdf` pre-allocates the object table
from that count, writes the header and catalog, and pulls one page per iteration.
Measured peak over a 179-page book fell from 4.52 GB to 25.2 MB — exactly one page bitmap —
with the written file (82 MB) as the named residual term. The file itself is unchanged: same
`DCTDecode` streams, same geometry, byte-identical length, every page pixel-identical to the
merge-base's. Item 4 is deferred on a 3.42 s measurement.

- [Build gate] PASSED (full, 257s) — 5027 passed, 26 skipped, 0 failed, run under the
  repo-wide full-suite lock (`fcntl.flock` on `meta/kanban/.full-suite.lock`; macOS has no
  `flock(1)`) with this pipeline's own `--basetemp`. The one known pre-existing failure
  (`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  red since before the book cards) was deselected; nothing else failed. Not vacuous: 5027
  tests executed. `tests/test_book_pdf_memory.py` alone: 22 passed in 4.59 s, **no skips** —
  the font-fingerprint skip the implementation built into AC-3 did not trigger on this
  machine, so the pixel-identity evidence is live rather than skipped.
- [Scope] src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_memory.py,
  tests/helpers/book_corpus.py (new), tests/fixtures/book_baseline_card145.json (new).
- [Scope gate] IN_SCOPE. Measured against the MERGE-BASE (b4c523d), not `main`. Two files
  sit outside `Touches` and both are NEW files under a directory the scope already covers
  (`tests/`), which SCOPE DISCIPLINE allows; no existing file outside `Touches` was edited.
  `src/nonogram/admin/app.py` was predicted but not needed (item 4 deferred) — under-use,
  not growth. Guardrail globs clean: nothing under `src/nonogram/export/**` and nothing
  under `tests/fixtures/a4_golden/**` (the new fixture is `tests/fixtures/book_baseline_card145.json`,
  a sibling of that directory, not inside it). comp_spread: COMP-009 only.
- [System contract] The card carried no `## System contract` section; the fresh set was
  assembled from the model at review time (44 rules) and written onto the card above, so the
  review is judged against what the model says today rather than against nothing.

- [Review 1/3] Score: 7.0 — crit: 0, imp: 3. Report:
  `meta/review/20260924T091248Z-CARD-145-cycle1.yml`. The reviewer re-derived the card's
  central claims independently rather than reading them off the card: it extracted the
  merge-base tree with `git archive b4c523d`, exported the same book with the untouched
  code and diffed the files — **2,210,622 bytes both ways, 4 differing bytes, all of them
  the two `Info` timestamps** — and re-measured the memory claim with its own gc-based
  instrument under `gc.disable()`, getting exactly 1 live page bitmap per page. It also ran
  one deliberate mutant. Step 8h: 44 rules, 8 ✓ holds, 36 ⚠ unchecked (no_eligible_fact),
  0 ✗ violated.
- [Review sync] 1 report(s) → meta/review/

- [Adversarial] 3 of 3 gating findings verified by independent skeptics (fresh context, given
  the finding and the diff but NOT the reviewer's reasoning), run READ-ONLY and in parallel
  so no two could mutate the same file at once — each experimented on a copy or by in-process
  monkeypatching:
  - F-001 (`PEAK_CAP_IN_PAGES = 2` is a page too loose) **CONFIRMED** — reproduced on a copy:
    unmutated peak is exactly 1.00 page bitmap on both an 8-page and a 179-page book;
    `del page` → `pass` at book_pdf_generator.py:1748 gives exactly 2.00 and all 22 tests
    still pass. Mechanism confirmed too: every frame but `_write_pdf`'s drops its page on
    resume, so that one `del` is the whole difference. Correction carried to the fix: the
    mutant's peak **equals** the cap, so it survives only on `<=`; and the docstring's
    justification describes the mutant's shape, not the shipped code's.
  - F-002 (the cover-download tripwire is dead) **REFUTED — dropped from the count.** The
    guard at tests/test_book_export_interior_cover.py:527 exercises the COVER route, which
    never went through `interior_pages` at HEAD *or* at the merge-base; the "export_book does
    not trip it" behaviour the finding demonstrates predates this card (it changed at
    CARD-127, ed8d20e). A route-level spy shows the cover download at HEAD draws 1 page and
    never enters `interior`/`interior_stream`, and the test's own live assertions
    (`(page,) = pdf_pages(...)` + `same_page(page, cover_art)`) are non-vacuous. G-1's
    behavioural half is NOT breached by this diff. Residual, recorded not fixed: that
    `monkeypatch.setattr(..., "interior_pages", ...)` line is now inert on every export path
    — but re-aiming it means editing an existing test this card is forbidden to touch, so it
    is a handover, not a fix.
  - F-003 (F-6's bound is not measured by the test it names) **CONFIRMED**, and the skeptic
    found the finding's own reason is the weaker one: simply moving the fixture inside the
    probe would NOT catch F-6's stated failure mode, because `LivePageBytes` only sees pages
    that pass through `_write_pdf`, so a cover built *before* the writer is invisible to it
    (mutant run: cover built first and held across the whole interior write — still measures
    1.00, 76 tests green). What a measured `export_book` *would* catch is the list-shape
    regression: materialising the interior inside `export_book` measures 9.00 page bitmaps on
    an 8-page book (~4.5 GB extrapolated — the card's own defect) with **134 tests green**.
    `export_book` does not delegate to `export_interior`, so the measured coverage of one
    does not protect the other. Also carried to the fix: failure-matrix row **F-1 over-claims
    the same way** — it names `export_interior`/`export_book` but its cited test measures
    only `export_interior`.
- [Severity gate 1/3] Score 7.0 < min_score 8, and 2 confirmed important findings after
  adversarial verification (0 critical) — the success path is closed; into the fix loop.

- [Fix 1] declarations: 5 updated, 0 confirmed, 4 none. Fix pre-gate PASSED — all 9 tests the
  fix named exist and pass (7.44 s), and the `matrix F-N updated` claims were cross-checked
  against the card's own diff (rows F-1, F-6 and F-7 really changed; the fix agent does not
  get to claim a re-derivation it did not do). **Baseline integrity checked separately and
  by hand, because this is the one thing that must never happen quietly:** the fix
  re-recorded the fixture's `font_fingerprint` (it now covers the three sizes those two
  pages are lettered at, not just 48). `git diff tests/fixtures/book_baseline_card145.json`
  confirms that field, its note, and two NEW fields are the whole change — **not one page
  digest moved**, so AC-3 is still measured against the merge-base's recorded truth.
  F-001 fixed by asserting the real value (`peak == 1 x 25,245,000 B`) instead of the loose
  `<= 2`; proved to have teeth by five mutants on scratchpad copies (each of the four `del
  page` sites removed, and `export_book` materialising its interior) — every one now fails
  at least one test, and every one passed all 22 before. F-003 fixed by EXTENDING the
  instrument (it now also wraps the six page factories, keyed on `id(page)`) rather than
  re-wording the row, so F-6's declared bound is one a test can actually observe; the
  `export_book` interior/cover ordering is now two statements instead of two keyword
  arguments of one call, which is what the bound rests on. Minors F-004..F-009 also fixed.
  The refuted finding was correctly left alone and recorded as a [Handover].
- [Build gate] PASSED (full, 262s) — 5030 passed (+3), 26 skipped, 0 failed, under the
  full-suite lock, same deselection. Book suites targeted: 226 passed across seven files,
  every existing one unedited.

- [Review 2/3] Score: 8.5 — crit: 0, imp: 1 (new). Report:
  `meta/review/20260924T100246Z-CARD-145-cycle2.yml`. Confirmation mode. Δscore +1.5,
  Δcrit+imp −1 — the loop is progressing, not stalling. The reviewer re-derived cycle 1's two
  confirmed findings at full depth and ran **7 mutants** of its own on a sandbox copy: all
  four `del page` sites individually killed (2.00 page bitmaps, 3 tests fail each), the
  `export_book`-materialises-the-interior mutant killed at 9.00, and the real F-6 mode
  (cover built eagerly and held across the interior) killed at 2.00. So the cycle-1 fix's
  teeth are independently verified, not self-reported. Step 8h: 44 rules re-derived fresh
  (nothing carried — every rule's scope globs intersect the delta), 0 ✗ violated.
- [Review sync] 1 report(s) → meta/review/
- [Severity gate 2/3] Score 8.5 ≥ 8 but 1 important finding — the success path stays closed.
- [Family] The one new finding is about the previous fix's own work — the cycle-1 fix added a
  production docstring and a failure-matrix clause asserting a mechanism the code does not
  have. Streak 1 (a family regression escalates at 2), recorded here so the retrospective
  sees it: the truth the fixes keep circling is **what actually keeps two page bitmaps from
  being alive at once** — it is the four `del page` sites and `_cover_page`'s laziness, not
  the order of two statements.

- [Adversarial] F-101 (F-6's ordering claim is refuted by mutation) **CONFIRMED** by an
  independent skeptic — which also found the *reviewer's own proposed replacement* is partly
  wrong, so the correction had to be verified before it was written, not after. Five mutants
  on a copy: swapping the two statements → 1.00 page bitmaps, 25 passed; folding them back
  into one `BookExport(cover=..., interior=...)` call with `cover=` first (the docstring's own
  named counterexample) → 1.00, 25 passed; an **eager** `_cover_page` with cover-first
  ordering → 1.00, 25 passed, so laziness is not load-bearing either; `export_book` itself
  holding the page (positive control) → 2.00 and
  `test_the_whole_book_holds_one_page_bitmap_at_a_time` FAILS, so the instrument does have
  teeth for the shape that matters; and cover-first with `_write_pdf`'s `del page` neutralised
  → 2.00 rather than 3.00, proving the cover is already dead before the interior walk begins.
  The accurate statement is narrower than either the docstring or the review: the cover page
  never escapes the `export_cover` call at all — `_write_pdf` retains no page after writing
  one and returns a `BytesIO`, and `BookExport.cover` is a `BytesIO`, not an `Image`. The four
  `del page` sites pin the **interior** half (F-1); the page-factory seam is an instrument
  property, not a production mechanism.
- [Severity gate 2/3] Orchestrator's call on severity: the reviewer filed this Important, the
  skeptic argued Minor (no code defect, no behaviour change, no test weakness, no user-visible
  risk — `export_book` returns the same `BookExport` and measures 1.00 under every ordering
  tried). I am treating it as **gating anyway and fixing it now** rather than downgrading it
  to clear the gate: this is an architectural card whose declared purpose is to set the
  structure CARD-128 copies, and a production docstring plus a failure-matrix row that assert
  a causal mechanism the code does not have is exactly the artefact that misleads the next
  card. It is documentation-only, so the fix is three sentences and carries no regression
  risk of its own.

- [Fix 2] declarations: 2 updated, 3 confirmed, 3 none. Fix pre-gate PASSED — both named tests
  pass (F-101 and F-103 are honest `test: n/a`, doc-only). Cross-checked on disk rather than
  taken on trust: the false clauses are gone from `book_pdf_generator.py` (grep for
  `left-to-right|reordering two kwargs` → 0 hits), the `[Ordering made explicit]` note is
  replaced, and rows F-1 and F-6 really changed in the card's diff. The replacement text
  claims **less** than the old one, which is the right outcome: F-6 now states that the cover
  half rests on no ordering and no laziness property at all — nothing in `export_book` holds a
  page, because `_write_pdf` retains none and `BookExport.cover` is a `BytesIO`, not an
  `Image` — and names the positive control (`export_book` binding a page itself → 2.00, test
  fails) as the evidence the bound has teeth, plus the three mutants that do NOT move it. F-1
  was re-derived and found correct, gaining only a clause scoping the four `del page` sites to
  consecutive pages of a multi-page walk.
- [Build gate] PASSED (full, 252s) — 5031 passed (+1, F-104's new instrument-coverage guard),
  26 skipped, 0 failed, under the full-suite lock. Book suites: 227 passed across seven files.

- [Review 3/3] Score: 9.0 ✓ threshold reached + no critical/important. Report:
  `meta/review/20260924T104859Z-CARD-145-cycle3.yml`. A FULL review, not a confirmation pass
  (cycle 2 raised a new finding, which is that mode's own exit condition). Trajectory across
  the loop: 7.0 → 8.5 → 9.0, gating findings 2 → 1 → 0, never stalled. This cycle re-derived
  everything: it re-verified from `git diff 7cdea7a` that **no page digest, page count or
  interior_bytes was ever re-recorded** in the baseline fixture (only the machine-face
  fingerprint plus two additive descriptive fields), ran 7 more mutants of its own (6 killed),
  traced the produced-vs-planned page-count contract on both sides and found it double-guarded,
  and read the writer against Pillow 12.3.0's `PdfImagePlugin._save` object for object —
  including checking that Pillow's own comment string carries no version substring, which was
  the most plausible source of byte divergence. Step 8h: 44 rules, **41 ✓ holds, 3 ⚠ unchecked
  (check_ref_missing), 0 ✗ violated**, every check ref grepped for before a ✓ was written.
  Existing tests, unedited: 1007 pre-existing book tests and 167 property tests green.
- [Review sync] 1 report(s) → meta/review/
- [Severity gate 3/3] Score 9.0 ≥ 8 and 0 critical / 0 important — the success path is open.
  The reviewer explicitly declined to inflate any of its four Minors, and said why: the
  largest has no code defect, no behaviour change and no AC impact, and calling it Important
  would have been the third repetition of the declaration family rather than a real
  escalation. That is the right call, and it is recorded here because a reviewer choosing NOT
  to inflate is as much a judgement as one choosing to escalate.

- [8h spot-check] The ✓ half of Step 8h gates the merge as hard as the ✗ half, and nothing
  had checked it — the coverage guard proves the rules were enumerated, not that any was
  looked at. Three re-derivations, fresh context, read-only and concurrent:
  - **ADR-0036/R2 (the panel fits no cell and places no grid line) — REPRODUCED**, and this
    was the closest call in the whole review, since the card rewrote the panel's PDF writer.
    The verifier classified every arithmetic expression the card added: all of it is
    PDF-container arithmetic (`page.width * 72.0 / self.dpi` for the MediaBox and the
    content-stream `cm` matrix), checked expression-by-expression against Pillow 12.3.0's
    `_save`, on the same inputs the old call passed. The set, arguments and ORDER of COMP-007
    calls are unchanged and every page-drawing method body is untouched — only its call site
    moved into the generator. It then re-derived byte-identity itself by running the old
    `_save_pdf` and the new `_write_pdf` over the same pages: 2,210,622 bytes each, identical
    after masking the two timestamps. Independent pass over every added line containing a
    digit found no margin, cell size, grid line, trim constant or centring offset.
  - **ADR-0019/R1 (import layering) — REPRODUCED.** The named guard exists, passes, and
    genuinely walks `src/nonogram/**/*.py` on disk via `rglob` rather than a hardcoded list,
    so it covers the card's new code; it uses `ast.walk`, so function-local imports are
    covered too. The verifier additionally AST-scanned all 78 function-local imports in the
    package and found no inward- or laterally-pointing edge.
  - **ADR-0006/R1 — INELIGIBLE, my selection error.** I put it in the spot-check pool, but
    cycle 3 reported it `⚠ unchecked (check_ref_missing)`, not `✓ holds`, and the protocol
    verifies fresh holds only — an `⚠ unchecked` line already declares its gap by typed
    reason, so the danger it closes is confidence, not candor. Recording the mistake rather
    than the tidy version. The verification ran anyway and was worth having: it confirms the
    reviewer's ⚠ status was the honest call, and confirms the card's own delta is clean
    (`pyproject.toml` and `requirements.txt` blob-identical to b4c523d; the only added imports
    are stdlib `time`/`typing` and `PdfParser` from the already-declared Pillow). It also
    found one sentence of the reviewer's supporting prose is false — "no reportlab import
    anywhere in src/" — because `src/nonogram/admin/pdf_generator.py:6-11` has imported
    reportlab since before the merge-base. Pre-existing, not this card's, and G-4 still holds
    because the card adds no dependency. See the [Handover] below: the rule has no live check
    matching its own wording.
  - **ADR-0036/R1 (CON-019's golden A4 tripwire) — REPRODUCED**, and this is the one the
    project cares most about. `git diff b4c523d -- src/nonogram/export tests/fixtures/a4_golden`
    is empty and all five files under `tests/fixtures/a4_golden/` hash byte-for-byte to their
    blobs at the merge-base, so **the golden was not regenerated** (G-3's sharpest edge). The
    verifier found the named class is defined in TWO files and ran both — 129 tests green —
    and demonstrated the tripwire's teeth in both directions on a scratchpad copy: shifting
    `PAGE_MARGIN_MM` by 0.5 mm turned 126 of 129 red (the 3 survivors correctly insensitive to
    a uniform shift), and bumping one golden value red-lined exactly its own case. It then
    hunted for indirect leakage into `export/` during a shared pytest session — conftest, the
    new module's class-level monkeypatches (all on `BookPDFGenerator`, all restored in
    `finally`), PIL globals, `sys.modules`, autouse fixtures — and ran the new tests FIRST in
    one session with the tripwire after: 155 green, no leakage.
  **3 of 3 eligible holds reproduced (ADR-0036/R2, ADR-0019/R1, ADR-0036/R1).**

- [AC/EC check] Failed: AC-2 ⚠ partial. 7 of 8 items ✓ demonstrated (AC-1, AC-3, AC-4, G-1,
  G-2, G-3, G-4), nothing contradicted, nothing unverified, no guardrail breached. The gate
  ran 9 pytest invocations with **zero skips anywhere** — including the check that most
  needed it: `TestBookPdfMemory_PagesAreUnchanged`'s machine-font gate did NOT fire, verified
  three independent ways (the byte-length test that would have skipped actually ran and
  passed; a re-run under `-W error::UserWarning` raised no "G-1 evidence incomplete" warning;
  and the fingerprint was recomputed outside pytest and matched), so all 8 pages' pixel
  evidence is real rather than skipped. It also re-checked the baseline's provenance itself:
  `git diff b4c523d 7cdea7a --name-only -- src/` is empty, so the fixture was recorded
  against production code identical to the merge-base. G-1: 299 pre-existing book-PDF tests
  green across 11 suites, none edited, none deleted or renamed. G-3: all **14** tracked files
  under the guarded globs compared blob-by-blob to b4c523d — zero differ.
  **AC-2's gap, precisely:** the "exports successfully" half holds in full (a genuine
  150-puzzle book exports to a real 179-page PDF, page count read back out of the file, peak
  measured at exactly one page bitmap, 107.1 MB total against a 512 MB envelope). The half
  that does not hold as written is "**under a memory cap that the current code fails**": no
  cap is ever *enforced* — there is no `setrlimit`, no cgroup, no process-level bound — and
  the old shape's failure is *arithmetic* over the instrument's measured per-page constant
  (179 x 25,245,000 = 4.52 GB), never an executed failure. The property is real; the
  criterion's literal second half was not executed.

- [AC/EC check] All criteria/constraints ✓ (evidence) — re-run after the AC-2 fix, all eight
  items verified against the state on disk:
  AC-1 ✓ demonstrated — `TestBookPdfMemory_PeakDoesNotGrowWithPageCount` 4 passed, 0 skipped;
    `big.peak == small.peak` as an equality over a real 8-page and a real 179-page export,
    `peak == 1 x 25,245,000 B` on both, with the old-shape probe as the non-vacuity control.
  AC-2 ✓ demonstrated — `TestBookPdfMemory_RealBookExportsUnderTheCap` 7 passed, 1 skipped.
    **Both halves are now executed under one 807,840,000 B cap in spawned (not forked)
    interpreters, with the cap installed before PIL is imported**: the streaming 150-puzzle
    book exports and reports 179 pages read back out of the PDF it wrote, at 148-173 MB
    resident; the old list shape is **killed at exit 91 with the sentry's `OVER THE CAP`
    marker after 0.89 s**. The verifier reproduced all of it outside pytest and then tried to
    make it pass for the WRONG reason — a bogus shape, a typo'd import, a stripped PYTHONPATH,
    a kernel OOM-kill — and every one of those fails the `returncode == 91` + marker + no-report
    triple rather than passing it.
  AC-3 ✓ demonstrated — 5 passed, 0 skipped; the machine-font gate did NOT fire (fingerprint
    recomputed independently and matched), so all 8 pages' digests were really compared, and
    `git diff 7cdea7a` on the fixture shows only `font_fingerprint` plus additive descriptive
    fields — no digest, no page count, no `interior_bytes`.
  AC-4 ✓ demonstrated — 6 passed, 0 skipped.
  G-1 ✓ demonstrated — no pre-existing test file modified (`tests/helpers/pdf_pages.py` absent
    from the diff), `--diff-filter=DRC` empty (nothing deleted, renamed or copied), 320
    pre-existing book tests green.
  G-2 ✓ demonstrated — INV-013's three properties each asserted by a named passing test.
  G-3 ✓ demonstrated — all **14** tracked files under the guarded globs byte-compared to their
    b4c523d blobs: 0 mismatches, 0 extra, 0 missing; 66 golden/byte-identity tests green.
  G-4 ✓ demonstrated — `pyproject.toml` and `requirements.txt` unchanged; the only production
    imports added are stdlib `time`, `typing.Iterable/Iterator`, and `PdfParser` from the
    already-declared Pillow.
- [AC-2, what is executed and what is not] Stated here because the distinction is the honest
  part of this card and a later reader deserves it without digging: **executed** — a real
  150-puzzle/179-page book exports under an enforced process-level cap, and the old shape
  really dies under that same cap. **Not executed** — (a) the *deployed* 512 MB number, which
  is still reached only by arithmetic over the measured per-page constant; the executed cap is
  807.8 MB, chosen so neither verdict turns on the interpreter's footprint. The verifier found
  the sharpest possible vindication of that choice: at 512 MB the streaming test's own 3x
  headroom assertion would be **failing today** (173.4 x 3 = 520 MB), which is exactly the
  flake this card was told not to ship. (b) The **kernel-enforced** variant: `setrlimit`
  (RLIMIT_AS) is refused by this Darwin kernel at every soft limit below 1 TiB — independently
  re-verified (`RLIMIT_AS == RLIMIT_RSS == 5`; 807.8 MB and 4 GiB both `ValueError`, 1 TiB
  accepted and useless) — so that test ships and SKIPS here, gated on a **measurement** rather
  than a `sys.platform` check, and will run for real on the Linux deployment image. (c) The
  shipped enforcement is a cooperative resident-set sentry, and a broken sentry fails the test
  rather than passing it.

### Cycle-1 review fixes

- [F-001, the cap was one page too loose] `PEAK_CAP_IN_PAGES = 2` let the defect back in: the
  real peak is **1.00** page bitmap, and replacing the `del page` in `_write_pdf`'s loop with
  `pass` measures **2.00** — inside a `≤ 2` cap, with every test still green. The bound is now
  an **equality** (`PEAK_IN_PAGES = 1`, `peak == 25,245,000 B`) on the 8-page book, the
  179-page book and `export_book`; the `≤ 2` cap stays beside it as a second bound and is
  explicitly documented as *not* the thing that pins the property. Mutation-proved three ways
  on a copy of the module (never on the worktree file): removing the `del` in `_write_pdf`'s
  loop, in `_as_planned` or in either of `produce()`'s two sites each measures exactly 2.00 and
  fails `test_neither_book_holds_more_than_one_page_bitmap` and
  `test_its_peak_page_memory_is_one_page_bitmap`. The docstring that justified the cap of two
  was half wrong and is rewritten: "the writer holds the page it is encoding" described the
  **mutant**, not the shipped code — `del page` is exactly what removes that reference.
- [F-003, F-6 claimed a bound no test measured] `TestBookPdfMemory_InteriorAndCoverStillSeparate`
  called `export_book` outside the probe, and `export_book` does not delegate to
  `export_interior`, so **no test measured its memory at all**. Fixed by measuring it — and the
  instrument had to be **extended** first, because simply moving the fixture inside the probe
  would not have caught F-6's own failure mode: a cover built before the writer and held across
  the interior never passes `_write_pdf`'s producer and would have measured a perfect 1.00.
  `_measured` now also wraps every page **factory** (`PAGE_FACTORIES`) and registers what it
  returns; `LivePageBytes.track` keys on `id(page)` so a page seen both ways is counted once.
  `test_a_page_built_outside_the_writer_is_still_seen` holds exactly that cover and measures
  2.00, which is the non-vacuity proof. What the measured `export_book` buys beyond F-6:
  materialising its interior (the old list shape) measures **9.00** page bitmaps on the 8-page
  book — the card's own defect, which had **134 green tests** over it before.
- [F-101, the ordering claim was false — the row now claims less] Cycle 1 split `export_book`'s
  `BookExport(...)` call into two statements; cycle 2 wrote down *why*, and the why was wrong.
  The claim — that the interior-then-cover order, and `_cover_page`'s laziness, are what keep a
  cover page from being alive beside an interior page — is refuted by mutants, run twice
  independently. Cover built first: **1.00** page bitmaps, 25 passed. Folded back into one
  `BookExport(cover=..., interior=...)` call with `cover=` evaluated first — the docstring's own
  named counterexample: **1.00**, 25 passed. `_cover_page` made eager (returning
  `[self.create_cover_page(...)]`) *and* the cover built first: **1.00**, 25 passed, so the
  laziness is not load-bearing either. The real mechanism is narrower and survives all three:
  no page escapes the `export_cover` call — `_write_pdf` retains no page after writing one and
  returns a `BytesIO`, and `BookExport.cover` is that `BytesIO`, not an `Image`. So F-6 now
  names no ordering property and no laziness property; the cover half rests on nothing holding
  the page, which is a claim a mutant can still refute and none of the five did. What a test
  *does* catch is `export_book` binding a page itself: the positive control
  (`cover_page = self.create_cover_page(...)` before the interior write) measures **2.00** and
  fails `test_the_whole_book_holds_one_page_bitmap_at_a_time` — which is also the evidence that
  the instrument has teeth for the shape that matters, and that `PAGE_FACTORIES` is an
  instrument property rather than a production one. The four `del page` sites belong to the
  **interior** half (F-1) alone: cover-first with `_write_pdf`'s `del page` neutralised measures
  2.00, not 3.00, so the cover is already dead before the interior walk starts, and for a
  one-page file that `del` does nothing at all. The two statements stay — they read better than
  two kwargs — but nothing rests on their order, and the docstring and F-1's row say so too.
- [F-004..F-008, minors] The fixture's `interior_bytes` is asserted (F-7's byte-length half was
  recorded and never checked). Two assertions that could not fail are gone — one restated a
  constant defined 150 lines above it, the other checked that `ru_maxrss` is positive — and the
  page-size premise is now cross-checked against the baseline fixture's own recorded page
  instead. `test_the_corpus_covers_every_page_kind_the_interior_has` identifies each kind
  **positively** (guide and divider against the pages the generator draws; the 30x30 and 15x15
  single-puzzle pages' grids read back off their ink; each half of the two-up page carrying its
  own 10x10 grid; the three answer pages by the solid blocks of ink a filled cell leaves, which
  no other page kind has anywhere) — dropping the divider for a fourth answer page used to keep
  all eight pages distinct and the test green. The three class-scoped fixtures are
  `@classmethod`s, so `PytestRemovedIn10Warning` is gone and they survive pytest 10.
- [F-009, the font skip cost six pages of evidence] The fingerprint mismatch skipped **all
  eight** pages' G-1 comparison over a face only interior pages 1 and 5 use — on the project's
  own Linux image, where Arial is not at that path, six pages of pixel evidence would have
  vanished into a skip. The fixture now records `font_dependent_pages: [1, 5]`, the comparison
  skips only those two and asserts that at least six pages were really compared, and
  `font_fingerprint` covers all three sizes those pages are lettered at (48, 28, 60) instead of
  48 alone — a face can differ at 60 and agree at 48, which would have let page 5 be compared
  when it cannot be. **The fixture's `font_fingerprint` value is the one field re-recorded**
  (machine evidence, not code evidence); every page digest is still the merge-base's and still
  matches, which is what says the pages did not move.
- [Handover, not fixed here] `tests/test_book_export_interior_cover.py:527` monkeypatches
  `BookPDFGenerator.interior_pages` to force a failure, and since this card no export path goes
  through `interior_pages` — the line is **inert**: the guard passes because the cover route it
  exercises never called `interior_pages` at HEAD or at the merge-base either, so it is not a
  regression and the test is not lying about its subject. But the monkeypatch no longer does
  anything on any route, and re-aiming it means editing an existing book-PDF test, which G-1
  forbids this card from touching. A later card should re-aim it at `interior_stream` (or drop
  it) — CARD-128 is the natural place, since it restructures the same producer.

- [For CARD-128] Divider pages must be `yield`ed from `produce()` inside `interior_stream`,
  as expressions, and their count must be added to `interior_page_count` — `_as_planned` will
  refuse the export the moment the two disagree, in either direction, so a divider added to
  the walk without a term in the plan fails loudly at the first export rather than shipping a
  corrupt page tree. Nothing may bind a page to a local across a `yield`.
- [Owner] Nothing to eyeball: the pages are proved pixel-identical to the merge-base's, so
  there is no rendered-grid change to look at. What is worth knowing is the deployment
  outcome — a 179-page book now peaks at **~132 MB** of bitmap and file against the panel's
  512 MB (measured end to end, a child process exporting it peaks at 150.8-169.9 MB resident
  including the interpreter), so the OOM kill that produced "render crashes when I try to
  generate pdf" should be gone. That is the one thing only the deployed panel can confirm.

### Cycle-3 review fixes

- [AC-2, the gate's "⚠ partial" — the cap is now enforced, not multiplied] The verification gate
  passed AC-2's "exports successfully" half in full and failed the rest closed: **no cap was ever
  enforced** (the "cap" was a pytest assertion over one instrumented allocation category) and
  "that the current code fails" was **derived arithmetically**, 179 x 25,245,000 = 4.52 GB. Both
  are now executed in child processes — see the rewritten `[AC-2, executed vs arithmetic]` note
  above for the mechanism, the measured cap derivation and the platform verdict. In short: one
  807,840,000 B cap, two spawned interpreters, the streaming shape finishing with 179 pages read
  back out of its own file and the list shape killed at 828 MB. **No existing assertion was
  removed** — the arithmetic derivation stays as always-on evidence, and it is still the only
  one that reaches the deployed 512 MB number. `setrlimit(RLIMIT_AS)` was tried first and
  **does not work on macOS 26.6.2**: the kernel refuses every soft limit below 1 TiB with EPERM
  (`RLIMIT_AS` and `RLIMIT_RSS` are the same constant there, `ulimit -v` fails identically, and
  `RLIMIT_DATA` too), so that test ships beside the working one and **skips with the kernel's own
  refusal in the message** rather than being quietly dropped or faked.
- [F-201, the "exactly one page bitmap" claim was one bitmap short — prose only] The card, the
  production module docstring and three test docstrings all stated the export holds "exactly one
  page bitmap" and gave the envelope as 25.2 + 81.9 = 107.1 MB / 21 %. Re-measured: `_blank_page`
  calls COMP-007's `render_pages`, which builds **two** full-size bitmaps (`blank`, and the solved
  page it discards) and is bound as `blank, _ = ...`, so the discarded page lives until the frame
  exits; `render_pages` is a module-level function of `nonogram.export.pdf`, not a
  `BookPDFGenerator` method, so it is outside `PAGE_FACTORIES` and the probe never saw it.
  Registering both pages it returns measures **10 pages / 50,490,000 B = 2.00 page bitmaps** on
  the 8-page book and **329 pages / the same 50,490,000 B** on the 179-page one. **No AC moves**:
  the extra term is a constant, not a per-page one (equal bytes at 22x the length is the proof),
  AC-1 is about growth, and the 179-page export still fits the envelope at ~132 MB. **No code
  changed** — `_blank_page` is byte-for-byte the merge-base's, and `PAGE_FACTORIES`, the
  instrument and every assertion are untouched, because what they pin (the panel retains 1.00
  pages, killed by four `del` mutants) is true and load-bearing. What changed is the English:
  "retains one page bitmap across the call that builds the next" everywhere the claim appears,
  plus the transient second bitmap and the **~132 MB / ~26 %** envelope stated with their measured
  numbers, in F-1, the measured-numbers table, the `[Instrument]` note, the `[Owner]` note, the
  Summary, the production module docstring and the test module's docstring, `PEAK_IN_PAGES` note
  and four test docstrings.

- [Docs step] No README written, deliberately. Of the four directories this card touched only
  `tests/` has a README, and it is a stale "Admin Panel Test Suite - Wave 1" document that
  enumerates a different set of files and never mentions the book tests, helpers or fixtures —
  stale before this card and not stale *because* of it, since nothing this card did changed
  the structure or purpose that document describes. Creating new READMEs for
  `src/nonogram/admin/`, `tests/helpers/` and `tests/fixtures/` would be a documentation
  artifact this repo does not keep, added to a finished P0. The canonical documentation in
  this project is the module docstring (CLAUDE.md: `src/nonogram/__init__.py`'s docstring is
  the canonical map), and `book_pdf_generator.py`'s was rewritten by this card and corrected
  twice under review. [Handover] `tests/README.md` is broadly stale and wants its own card.
- [Commit] 7b092b8 — `fix(admin): CARD-145 — the book PDF holds one page, not the book`.
  Four files, explicit pathspecs, nothing under `meta/` staged (verified before committing):
  `src/nonogram/admin/book_pdf_generator.py`, `tests/test_book_pdf_memory.py`,
  `tests/helpers/book_corpus.py`, `tests/fixtures/book_baseline_card145.json`.
  Committed inline by the orchestrator rather than by a commit agent — one mechanical step
  where the standing rule is "explicit pathspecs, never `git add -A`", against a repo with a
  large pre-existing untracked set. `[Inline fallback] commit`.
- [Handover] For CARD-128, which restructures this same producer next:
  1. Divider pages must be `yield`ed from `produce()` inside `interior_stream`, **as
     expressions** — nothing may bind a page to a local across a `yield`, and no `yield` may
     sit inside the `except Exception` that names an undrawable puzzle (it would also catch
     anything a consumer threw back into the suspended walk). Every one of the four `del page`
     sites is individually mutation-killed; removing any one doubles the measured peak.
  2. A new page kind must add its term to `interior_page_count`. `_as_planned` refuses the
     export in either direction the moment the plan and the walk disagree, so a divider added
     without a plan term fails loudly at the first export instead of shipping a corrupt page
     tree.
  3. A new page-returning method must be added to `PAGE_FACTORIES` — there is a test that
     every method annotated `-> Image.Image` is in that list, so this one fails loudly too.
  4. `tests/test_book_export_interior_cover.py:527`'s `monkeypatch.setattr(...,
     "interior_pages", ...)` is now inert on every export path (`interior_pages` has no
     production caller). It was already inert on the cover route at the merge-base, so this
     card did not break it and G-1 forbade editing it — but it should be re-aimed at
     `interior_stream` or dropped.
- [Handover] For the architect station, two model gaps this card surfaced but did not touch
  (nothing under `meta/architecture/` was edited):
  1. **The memory envelope is not an NFR.** This card is the first thing in the project to
     state one, and the 512 MB figure lives only on this card and as `ENVELOPE_BYTES` in the
     test module. `grep` over `requirements.yml` for memory/envelope/512/OOM finds nothing.
     It should be registered as an NFR so later cards inherit it.
  2. **ADR-0006/R1's check ref is dead**, and the rule as worded has no live check. Its
     `check.ref: TestDependencyBaseline_IsExactlyPillowAndNumpy` exists nowhere as a test; the
     live substitute (`tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)
     parses only `[project].dependencies`, so it pins the declared core list, not the
     "installed dependencies" the rule names — reportlab, Flask, gunicorn, psycopg2, SQLAlchemy
     and alembic are all installed via the admin extra. Pre-existing and out of this card's
     scope; a mandatory rule with a dead ref is unverifiable, not satisfied. Cycle 3 reported
     the same for INV-008 and INV-012.
- [Handover] Two Minors this card measured and consciously did not act on:
  1. **File fidelity is asserted as length + pixels, so a same-length byte change passes.**
     A surviving mutant: dropping `dpi=` from the JPEG save leaves all tests green (the JFIF
     density changes, the length does not — 133,107 B either way). Cheap fix, and it would
     double as the tripwire for Pillow's PDF writer changing under an unbounded `Pillow>=10.0`,
     which is the card's one real dependency risk: `_write_pdf` is built on Pillow internals
     (`PdfParser.next_object_id`/`write_catalog`/`write_page`/...).
  2. **The cover bound is measured only for the generated title cover**, never for the route's
     uploaded one. An RGBA upload measures 1.33 page bitmaps (`_write_page`'s `convert("RGB")`
     holds a second bitmap beside it) — one page of a one-page file, identical to the
     merge-base's conversion, so no regression; but it is the one path where an arbitrary user
     bitmap enters this export and it has no matrix row.
- [Note] `forge:fix` did not write `status: fixed` back into the cycle-3 review YAML (the
  review directory was outside the scope it was given). Left as-is rather than hand-edited:
  editing review evidence by hand is worse than a missing status field.

- [Done] Merged 554c437 on 2026-09-24. Review 9.0 across 3 cycles (7.0 -> 8.5 -> 9.0, gating
  findings 2 -> 1 -> 0, never stalled). Four full-suite runs; final 5032 passed, 0 failed.
  AC/EC/G 8/8 demonstrated. Golden tripwire byte-compared across all 14 files under
  export/** and a4_golden/**, 0 differ, never regenerated. Full suite green on the merge.
- [Result] A 179-page book peaked at ~4.3 GB and now peaks at ~132 MB, against the deployed
  512 MB. Pages are proved pixel-identical to a baseline recorded in its own commit BEFORE
  any production change, and the interior byte length is unchanged (2,210,622).
- [Mechanism, and why NOT reportlab] The card suggested reportlab; the implementation used
  Pillow's own writer instead, mirrored object-for-object. reportlab's trailer comment
  breaks the shared test helper's PdfParser, which would have forced a G-1 edit — i.e. the
  suggested mechanism would have required weakening an existing test. The card's stated
  constraint (peak memory must not grow with page count) was met without it.
- [Memory test] Measures live page-bitmap bytes through weakref — not RSS (platform
  dependent) and not tracemalloc (blind to Pillow's C allocations: it saw 0.03% of 100 MB).
  18 mutants across 5 agents; all four `del page` sites individually killed. This is the
  honest version of AC-1/AC-2: the deployed 512 MB figure stays arithmetic, because at
  512 MB the test's own headroom assertion would fail today — exactly the flake to avoid.
- [Failure matrix] The card as cut had none — a decompose gap, stated rather than stalled
  on. Seven rows were declared before code and re-derived twice under review; the memory
  envelope is F-1.
- [Item 4 deferred on measurement, dispatcher accepts] Progress reporting is NOT carded: a
  179-page book exports in 3.42 s, not the two minutes the card feared, and a test fails
  the export past 60 s. There is nothing for the owner to wait through.
- [Handover -> CARD-128] Yield pages as expressions, add the plan term, add to
  PAGE_FACTORIES, and re-aim the now-inert interior_pages monkeypatch.
- [Minors consciously left] A same-length byte change would pass the byte-length assertion,
  and the uploaded cover's RGBA path is unmeasured.
