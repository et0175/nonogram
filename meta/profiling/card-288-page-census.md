# CARD-288 — the page census: 3,820 pages drawn to read 1,033

Measured 2026-10-24 by the orchestrator while cutting CARD-288, so the card was
sized on a measurement rather than on a census of call sites. Recorded here
because the instrument is deliberately **not** in the repo and the figures are
the card's premise.

## Host and tree

* `/Users/omelnikova/PycharmProjects/PythonProject4` at **`aa6e556e`** (main,
  CARD-218 merged and closed, CARD-219 dispatched to a worktree). The file under
  measurement, `tests/property/test_book_pdf_geometry.py`, is **unchanged since
  `ae164099`**, the commit `suite-durations-20261023.txt` was taken at — so the
  artefact's figure and these runs measure the same text.
* Mac15,6 Apple M3 Pro, 11 cores, 18 GB, macOS 26.7.1 (Darwin 25.6.0 arm64),
  Python 3.14.3, pytest 9.1.1 — the same host as `suite-durations-20261015.txt`,
  `suite-durations-20261023.txt`, `card-218-render-sharing.md`,
  `card-241-render-check-cost.md` and `card-243-two-threshold-cost.md`.
* Command, with `-o addopts=''` because `pyproject.toml:89` already supplies
  `-q` and a second one suppresses the count line:

```bash
CARD288_OUT=<scratchpad>/card-288-census.json PYTHONPATH=<scratchpad>:. \
  ./.venv/bin/python -m pytest -o addopts='' -p card_288_page_census -q \
  tests/property/test_book_pdf_geometry.py
```

Nothing under `meta/profiling/` was re-measured or regenerated; the two frozen
duration artefacts are read-only inputs and the only figure taken from them
(51.82 s) was recomputed by parsing their own `<secs>s <phase> <nodeid>` records.

## The instrument, and where it lives

A pytest plugin, `card_288_page_census.py`, kept **outside `tests/`** on purpose:
`rank_durations.py:45` defines the frozen render set by grepping eight idioms over
`tests/**/*.py` and `tests/test_suite_profile.py:482` asserts that set as an
**equality**, so a probe file under `tests/` naming a render idiom reds the suite.
(CARD-218 hit this and recorded it; this is the same precaution.)

It wraps three things and counts:

* `BookPDFGenerator.interior` → `len(result.pages)` per call = **pages drawn**
  (`interior_pages` is `interior(...).pages`, so this catches both);
* `tests.helpers.page_ink.drawing_of` and
  `tests.helpers.two_up_ink.drawings_of` → **pages ink-measured**;
* a `pytest_runtest_call` hookwrapper for per-test attribution and seconds.

**One trap worth recording, because it fails silently and returns zero:** the
test module does `from tests.helpers.page_ink import drawing_of`, so it holds its
**own** reference. Patching the helper module alone counts **0 measured pages** —
indistinguishable from a test that measures nothing. The plugin rebinds the test
module's globals in `pytest_collection_finish` as well.

## 1. Pages drawn versus pages read — the measurement that is an integer

| test | calls | pages drawn | pages ink-measured | secs | ms/page drawn |
|---|---|---|---|---|---|
| `…MirroredMarginsCentreDrawingForEveryParity_pdf_pages` | 136 | 1768 | 544 | 22.28 | 12.6 |
| `…DrawingFitsUsableAreaUnderStandardCell_pdf_pages` | 216 | 1512 | 216 | 20.47 | 13.5 |
| `…PortraitWithFixedTopEdgeForEveryExtent_pdf_pages` | 2 | 494 | 252 | 9.12 | 18.5 |
| `…PortraitWithFixedTopEdgeForEveryExtent_two_up_pages` | 1 | 46 | 21 | 0.84 | 18.2 |
| **total** | | **3820** | **1033** | **52.71** | **13.8** |

**27.0 % of the pages this file draws are ink-measured.** The 52.71 s total
reproduces `suite-durations-20261023.txt`'s **51.82 s** within **1.7 %**, which
is the cross-check that the instrument did not change what it measured.

## 2. How much of the remainder is actually waste — per test, because they differ

Pages drawn but never ink-measured are **not** all waste: one test asserts
`page.size` on every page, which is a real claim (EC-019, "every page of the
book's PDF is the trim").

| test | drawn | read at all | drawn and never read | ≈ secs |
|---|---|---|---|---|
| `DrawingFitsUsableArea` | 1512 | **1512** (every page size-asserted, `:392`–`:395`) | **0** | 0 |
| `MirroredMargins` | 1768 | 544 (four named page numbers, `:640`) | **1224** | 15.42 |
| `PortraitWithFixedTopEdge_pdf_pages` | 494 | 252 (the puzzle pages, `:495`) | **242** | 4.48 |
| `…two_up_pages` | 46 | 21 (puzzle pages from `5 + toc`) | **25** | 0.46 |
| **total** | **3820** | **2329** | **1491** | **20.36** |

**1,491 pages — 39.0 % of everything this file draws — are drawn and nothing
ever looks at them.** At each test's own measured per-page rate that is
**≈20.4 s of the file's 52.71 s (38.6 %), and 1.43 % of the whole suite.**

`MirroredMargins` is the extreme: 13 pages per call, four read, **nine drawn so
that `len(pages)` at `:625` can be compared with `12 + toc_page_count`** — a
page-count claim that `section_plan(...)`'s own arithmetic already answers, and
which the test already calls for `toc_page_count` two lines earlier.

### The domain of the 20.4 s, stated so no successor treats it as settled

The seconds column is **derived**, not directly measured: it is each test's own
`secs / pages drawn`, which attributes **all** of that test's time to page
drawing — including the ink scan in `drawing_of` (which walks the bitmap) and
the `Sheet` oracle's arithmetic, neither of them free. **20.4 s is therefore an
UPPER BOUND from a single instrument.** The wave-50 rule applies: reproducing it
with the same method would only confirm the method, so CARD-288's AC-5 requires
re-deriving it in a second domain before any conversion is designed around it.

## 3. The memory, and why it is not this card's load-bearing claim

```
/usr/bin/time -l ./.venv/bin/python -m pytest -o addopts='' -q \
    tests/property/test_book_pdf_geometry.py
→ 4 passed in 51.22s;  52.15 real, 48.29 user, 2.33 sys
→ maximum resident set size  2,909,667,328
```

**2,909,667,328 B = 2,909.7 MB = 2.71 GiB for one test file.** Against this
project's own unit — `PAGE_BITMAP_BYTES = 2550 * 3300 * 3 = 25,245,000`
(`tests/test_book_pdf_memory.py:210`) — that is **115.3 page bitmaps**, six times
the 433.4 MiB retention that scored CARD-218 a 6.0 in its first review cycle.

All four tests reach their pages through **`interior_pages(...)`, which returns a
`List[Image.Image]`** — the whole book alive at once. Its own docstring
(`src/nonogram/admin/book_pdf_generator.py:6485`) states both the fact and the
cost: *"A list of pages, and therefore not what an export uses. Since CARD-145
the export path walks `interior_stream` instead, one page alive at a time… On a
book of any size that list is 25.2 MB a page, so calling it **is** the shape the
deployed panel was OOM-killed by."*

**Attribution is open and must not be assumed.** One `MirroredMargins` case
materialises 13 pages = **328 MB**; the file's peak is ~9× that, and the surplus
is unexplained by the lists alone. **Peak RSS is allocation-order dependent** —
CARD-218 measured its own fix *removing* a 192.6 MiB retention entirely while the
measured peak went **up** — so the peak is recorded here as context and is
explicitly **not** the card's claim. The claims are the integers: **3,820 drawn,
1,033 read, 1,491 never read, 13 alive where 1 suffices.**

## 4. What was NOT measured

* **No feasibility probe was run.** Nobody has yet walked
  `interior_stream(...).pages` in these tests and timed it. The 20.4 s is what
  the census says is available, not what a conversion delivered.
* **The peak's attribution** (above) — unmeasured on purpose.
* **Pages "read at all"** in §2 is derived by reading the code at the four line
  numbers cited, not by instrumenting `page.size` access. The ink-measured
  column is instrumented; the size-asserted column is not.
* The file has **not** been re-profiled solo against
  `suite-durations-20261023.txt`'s conditions; the 52.71 s / 51.22 s runs above
  are solo single-file runs, which is a different arm from a whole-suite run.
