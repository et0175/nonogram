# CARD-295 AC-5 — the vector puzzle page, priced

Derived by `meta/profiling/card295_puzzle_page_price.py` on 2026-10-26, in the
`card/295-puzzle-page-as-operators` worktree at `075b31d9` plus this card's
changes. **Every figure below is printed by that script**; none is transcribed
from CARD-293's spike or from ADR-0042. Re-run it rather than trusting the
table if the tree has moved.

> **The tree has moved, and §§2–3 are superseded in part.** `5d84976c` —
> merged into this branch at `a7f33021`, after everything below was derived —
> memoises the compressed face, which **inverts §3's prescription**. Sections
> 1–3 are left exactly as derived: they are the honest pre-cache record, and
> §3 item 2 predicted the post-cache figure to within one per cent. The
> correction is the dated **post-cache addendum** at the end of this document,
> and §3 should not be acted on without it. §1's bytes are unaffected — the
> cache returns the same compressed bytes.

The machine was **not idle** — the board runs several agents — so the load
average is recorded at both ends of each measurement (CARD-292's AC-6
convention) and the **minimum** of the runs is the headline, with the median
beside it. A busy machine inflates both arms of an interleaved A/B, which is
why the ratio is the figure to read and the absolute milliseconds are not.

## The arm, stated before any result (CARD-292's G-4)

    book                   corpus_book() — CON-018's Book 1 profile
    puzzles                24, from corpus_puzzles() in print order
    pages                  24 (0 two-up: the corpus is 18x18 and 20x20, which
                           compute_pair_layout refuses to pair on this trim)
    grid sizes             18x18 x10, 20x20 x14
    trim                   2550 x 3300 px at 300 DPI
    interior bitmap mode   "L"

**The two arms are not symmetrical, and the asymmetry favours the raster arm's
page rather than this card's.** The raster arm is `_blank_page` — the real
shipped page, with the interior frame's two rules, the footer's grid-size
label, the folio and two QR icons with their captions on it. The vector arm is
`vector_puzzle_page`, which draws the grid, the frame, the clue digits and the
band and **not** that furniture (see `book_puzzle_vector`'s docstring: no card
in the phase draws it yet). The missing marks are about six operators and
~200 bytes on a ~6,100-byte stream; the raster arm's QR icons are a few
thousand black squares, which is real ink a JPEG has to carry. So the byte
ratio below is **generous to the vector arm by a few per cent and generous to
the raster arm by rather more**, and the honest statement is that it is the
same order as the spike's, not that it is more precise than it.

## 1. Bytes — `card295_puzzle_page_price.py bytes`

| | vector | raster | ratio |
|---|---:|---:|---:|
| 24-page interior | **408,366 B** | **9,899,067 B** | **24.2x** |
| per page | 17,015 B | 412,461 B | |
| per page, less the face | 1,205 B | 412,461 B | 342x |

The face is **379,441 B Flate-compressed, once per file** (ADR-0042/R5), which
is 92.9 % of the vector interior at 24 pages and falls to 29 % at 150. The
per-page figure that extrapolates is the one net of it: **1,205 B**.

**Against the spike** (ADR-0042's Context: 407,976 B against 9,157,535 B, 22.4x
for 24 pages): same order, same direction, both arms slightly larger. The
vector arm is 390 B bigger because this page is drawn from the production call
and the spike's prototype hoisted a few constants; the raster arm is 741,532 B
bigger because this arm is the **real** `_blank_page` and the spike's was a
probe that drew no QR icon and no footer. **No regression.**

## 2. Generation time — `card295_puzzle_page_price.py time --runs 7`

Interleaved vector/raster/vector/raster, 7 runs each, same process.

| | min | median | ms/page (min) |
|---|---:|---:|---:|
| vector | 0.0474 s | 0.0518 s | **1.975** |
| raster | 0.4032 s | 0.4166 s | **16.8** |
| **speed-up on min** | | | **8.51x** |

    loadavg start  6.65 / 4.54 / 4.93
    loadavg end    6.92 / 4.63 / 4.96

**Against the spike's 8.5x (1.37 ms against 11.7 ms per page): the ratio is the
same to two significant figures.** Both absolute figures are higher here and
both for the same reason — these arms are the production calls, which compute
their own `Layout` per page, and the spike's arms were handed a list of
layouts computed outside the timed region. 1.975 ms/page decomposes as 0.57 ms
of drawing (which *is* `compute_layout` plus the operators) and 1.15 ms/page of
one-off face compression amortised across the 24 pages.

## 3. The number nobody had: what a CONVERTED ASSERTION costs

`meta/profiling/interior-raster-share-20261026.txt` ends by saying the spike's
**4.1x is a LINE ratio, not a time ratio**, and that "no one has measured a
converted test's wall clock, and CARD-295/296/297 are the first chance to".
This is that measurement.

One claim — *every fifth grid rule is wider than the rules between them, and
the page carries exactly two rule widths* — asserted four ways on the same
page, interleaved, 7 runs. All four agree before any is timed: the ink arm
reads `[3, 6]` device pixels, the three stream arms read `[0.72, 1.44]` points,
which is the same two rules.

| arm | min | median | against ink | page bitmaps |
|---|---:|---:|---:|---:|
| **ink** — `_blank_page` + `page_ink.drawing_of` + a scanline | 20.58 ms | 20.75 ms | 1.00x | **1.0** |
| **stream, a PDF per assertion** | 29.17 ms | 29.45 ms | **0.71x** | 0.0 |
| **stream, one interior written once** | 2.47 ms | 2.59 ms | **8.33x** | 0.0 |
| **stream, no file at all** | 0.66 ms | 0.72 ms | **31.2x** | 0.0 |

    loadavg start  3.53 / 4.10 / 4.71
    loadavg end    3.53 / 4.10 / 4.71

### The finding, and it is the one the phase needs

**A naive conversion makes the suite SLOWER — 1.42x slower on this claim.** The
whole of that is one term:

    draw the page (vector)                     0.57 ms
    write a one-page PDF                      28.04 ms
      of which: Flate the embedded face       27.71 ms   (98.8 %)
      of which: Flate the page's own stream     0.14 ms
    read the stream back out                   0.25 ms
    draw the page (raster)                     6.74 ms

ADR-0042/R5 embeds the **whole** 757 KB face and compresses it at `zlib` level
9 **once per file**. That is free across a 24-page interior and is the entire
cost of a one-page one. So the saving a converted assertion makes is decided
not by the medium but by **how often it writes a PDF**:

* a test that writes one interior and makes several claims about it: **8.3x**;
* a test that writes a one-page PDF per claim: **0.71x — a regression**;
* a test that asserts on `ContentStream.operators` without writing a file at
  all: **31x**, but ADR-0042/R6 says the claim is made against *the written
  file*, so this is the bound, not the recommendation.

### What follows for CARD-298 and CARD-299

1. **A converted test must share its written PDF**, at class or module scope,
   exactly as `tests/test_book_pdf_band.py` already shares its rendered
   interior (CARD-218's conversion). Written per assertion it is slower than
   what it replaces. This card's own module does the former and says so.
2. **Caching the compressed face would remove the choice.** `write_vector_pdf`
   calls `zlib.compress(interior_face_bytes(), 9)` on every call with the same
   379,441-byte result; memoising it turns the 28.04 ms one-page write into
   ~0.3 ms and the naive arm into ~14.7x rather than 0.71x. It is one
   `lru_cache` in `nonogram.admin.book_vector` — **CARD-294's merged module**,
   so it is raised here and deliberately not taken: it costs 379 KB of
   resident memory for the process's lifetime, which is a decision for the
   card that owns that module's memory story, and the phase's baselines are
   CARD-298's to record once.
3. **The 34.92 % share is not reachable from the three files this card
   touches.** `interior-raster-share-20261026.txt` attributes 498.02 s of
   convertible suite time to 28 files; the three in this card's `Touches` hold
   **13.60 s of it (2.7 %)** — `test_book_pdf_band.py` 6.43 s,
   `test_book_cell_size.py` 4.74 s, `test_book_puzzle_frame.py` 2.43 s — while
   `test_book_export_interior_cover.py` alone holds 344.29 s (69.1 % of the
   convertible share). Whatever the phase saves, it is saved in that file, and
   it is CARD-276's / CARD-287's / CARD-292's, not a page card's.

## Addendum, 2026-10-26 — after `5d84976c`, the face cache

Everything above was derived at `075b31d9` plus this card's changes. The
branch then merged main at `a7f33021`, which brought `5d84976c` —
`@lru_cache(maxsize=1)` on `book_vector._flate_face`. Re-measured by **review
cycle 1** with the same instrument (`claim --runs 7`, `time --runs 7`, load
average **7.05 / 5.53 / 4.83 identical at both ends**):

| arm | min | against ink | above |
|---|---:|---:|---:|
| **ink** | 22.39 ms | 1.00x | 1.00x |
| **stream, a PDF per assertion** | **1.54 ms** | **14.54x** | 0.71x |
| **stream, one interior written once** | 2.62 ms | **8.55x** | 8.33x |
| **stream, no file at all** | 0.71 ms | 31.54x | 31.2x |

Generation (§2) moves the same way: vector **0.833 ms/page** against raster
**17.621**, i.e. **21.14x**, where §2 records 1.975 / 16.8 / 8.51x.

**Control**: removing the `lru_cache` from `_flate_face` in the same session
and re-running `claim --runs 5` returns the per-assertion arm to **0.69x**,
reproducing the pre-cache 0.71x. So the sign change is the cache and not the
host.

### What is retracted

Two statements above are **false on `a7f33021`** and must not be carried
forward:

1. §3's headline, *"A naive conversion makes the suite SLOWER — 1.42x slower
   on this claim"*.
2. "What follows for CARD-298 and CARD-299" item 1, *"A converted test must
   share its written PDF … Written per assertion it is slower than what it
   replaces"*.

**The inversion runs the opposite way from what item 1 assumed.** It is not
merely that the per-assertion arm became affordable: the **shared** arm is now
the *slower* of the two file-writing arms, because it re-extracts a 24-page
PDF's content streams on **every** assertion while the per-assertion arm
writes one page and extracts one page.

### What survives, and for CARD-299

The guidance is narrower than item 1's and is about **extraction**, not about
the file:

* **Parse a shared PDF once per fixture.** A converted test may write its own
  one-page PDF per assertion — that is 14.54x now — but it must not re-extract
  a whole interior per assertion. `tests/test_book_puzzle_page_vector.py`'s
  `_read_back_together` is the shape: one write and one extraction for sixty
  pages, with the parsed marks held per stream.
* §3 item 2 is **discharged**, by somebody else: it raised the cache as
  CARD-294's module's decision and predicted "~0.3 ms" and "~14.7x rather than
  0.71x". Measured: 14.54x, within 1 %. The prediction is the reason this
  addendum could be written without re-deriving the decomposition.
* §3 item 3 (the 34.92 % share is not reachable from this card's three files)
  is untouched by the cache.

Nothing in this addendum was measured by the fix round: the box it ran on was
at load average 12–19, which `tests/README.md` says "tells you nothing at
all". Every figure here is review cycle 1's, taken with the load average
recorded identical at both ends and with the cache-removal control above.

## Provenance

* Instrument: `meta/profiling/card295_puzzle_page_price.py`, subcommands
  `bytes`, `time --runs 7`, `claim --runs 7`.
* The post-cache addendum's figures: **review cycle 1**
  (`meta/review/20261026T104006Z-CARD-295-cycle1.yml`, findings F-002 and the
  brief corrections), same instrument and same subcommands at `a7f33021`, with
  the `_flate_face` cache-removal control. Not re-derived by CARD-295's fix
  round, which had no quiet box.
* Shares and file times in §3.3: `meta/profiling/interior-raster-share-20261026.txt`,
  which is itself joined from a profile taken at `ae164099` and is ~104 tests
  light against today's tree — order-of-magnitude honest, second decimal not.
* The spike's figures quoted for comparison: ADR-0042 Context and Consequences,
  from `meta/profiling/card-293-vector-interior-comparison.md`.
