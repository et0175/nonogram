# CARD-243 — what reading the page at two thresholds costs (AC-6)

CARD-241's round-mark check rendered the book's interior and measured its ink
at one threshold, grey 128. CARD-243 reads the same pages at **two** — grey 128
(`page_ink.INK_LEVEL`, the reading every geometry measurement uses and the one
whose figures on the book's own pages are recorded) and grey 208
(`round_ink.MARK_LEVEL`, the reading the guard's verdict comes from). AC-6 asks
for that cost **measured and compared against CARD-241's recorded figures**
rather than stated fresh.

**It is 2.2x the check and 1.9x the file, it costs no peak memory at all, and
it is not marked.** It runs with the rest of the file, on every commit.

## The run

* worktree `card/243-round-mark-sees-greys`, based on `main` @ `721fda8`
* host: the same Mac15,6 / macOS 26.7.1 / Python 3.14.3 / pytest 9.1.1 as
  `card-241-render-check-cost.md` and `suite-durations-20261015.txt`
* command, from the worktree root, three runs of each column:

```bash
/usr/bin/time -l ./.venv/bin/python -m pytest \
    tests/test_book_difficulty_dots.py -p no:randomly -k RoundMarkOnThePage
```

* the **before** column is this worktree with its three touched test files
  restored from `git checkout HEAD --`, i.e. CARD-241's state byte for byte,
  and restored afterwards from a byte copy taken first (`diff` clean)

Nothing in `meta/profiling`'s frozen artefacts was re-measured or regenerated
to produce this file (CARD-243 G-6): it is a new card-scoped record, taken with
the command above and nothing else.

## The host is comparable, which is what lets the comparison be made

CARD-241 recorded its own figures on this host and warned that a loaded host
inflated both halves of its first attempt by ~60 % while the delta survived.
So the before column was re-run here rather than quoted, and it reproduces:

| measurement | CARD-241 recorded | re-measured here (3 runs) |
|---|---|---|
| `-k RoundMarkOnThePage` | 4.80 s / 33 tests | **4.57–4.78 s** / 33 tests |
| the whole file | 6.33 s / 121 tests | **6.03–6.24 s** / 121 tests |
| peak RSS of the pytest process | 836 MB | **842–853 MB** |

Within 5 % on wall clock and within 2 % on peak RSS. The after column can
therefore be read against CARD-241's numbers directly.

## What it costs

| measurement | before (CARD-241) | after (CARD-243) | delta |
|---|---|---|---|
| `-k RoundMarkOnThePage`, wall clock | 4.57–4.78 s / 33 tests | **10.29–10.61 s** / 62 tests | **+5.8 s, x2.2** |
| the whole file | 6.03–6.24 s / 121 tests | **11.70–12.02 s** / 150 tests | +5.7 s, x1.9 |
| peak resident set of the pytest process | 842–853 MB | **863–870 MB** | **+17 MB, +2 %** |
| interiors rendered and measured | 12 | **14** | +2 (the two grey routes) |
| pages rendered and measured | 163 | **189** | +26 |
| share of `suite-durations-20261015.txt`'s 930.81 s | 0.5 % | **1.1 %** | +0.6 pt |

The card's own estimate was that measuring at two thresholds "roughly doubles
the measurement half and is still ~1% of the suite". Both halves of that hold,
and the first is exact: 2.2x, 1.1 % of the suite.

## Where the +5.8 s goes, measured rather than apportioned

Three slices, isolated by running subsets of the same file:

| slice | cost |
|---|---|
| the second threshold on the test set CARD-241 already had, plus every canvas boundary shape re-measured at both (AC-3) | **+3.7 s** (4.66 s → 8.40 s for `-k "RoundMarkOnThePage and not SeesTheGreys and not BoundList"`, 38 tests) |
| CARD-243's own new classes — two planted grey interiors, the palette walk, eight bound probes with a control each | **+2.0 s** (8.40 s → 10.44 s, 24 further tests) |

And per page, in a standalone process, three runs:

| point | peak RSS | time |
|---|---|---|
| after imports | 63 MB | — |
| after `interior_pages` (13 pages) | 517–519 MB | 0.20–0.22 s (15–17 ms/page) |
| after measuring all 13 at grey 128 (3222 regions) | 555–559 MB | 0.27–0.30 s (20–23 ms/page) |
| after measuring all 13 **again** at grey 208 (3222 regions) | **555–559 MB** | 0.24–0.25 s (18–19 ms/page) |

Two things that table says and the pytest-process figures above cannot:

1. **The second threshold is free in memory.** Peak RSS does not move at all
   when the pages are read a second time — 555–559 MB before and after — because
   the second read allocates the same transient arrays as the first and frees
   them, and the peak is still the materialising `interior_pages` call
   (+454 MB, ~35 MB a page). CARD-241's attribution survives this card
   unchanged: the render is roughly ten times the measurement, and the +17 MB
   the pytest process gained is the second `LevelInk` record per memoised
   interior, not a second page.
2. **A page costs ~19 ms to read a second time**, against ~21 ms for the
   first, the difference being the one `page.convert("L")` each read does for
   itself. 189 pages x 19 ms is 3.6 s, which is the +3.7 s slice above — so
   that slice is the second read and essentially nothing else.

The one cheap optimisation available, if this ever needs to be cheaper:
convert each page to `L` once and threshold the same array twice, which would
return about half of the 19 ms. It was not taken, because
`tests/helpers/page_ink.ink_mask` is the one place in the suite that says what
reading a page means, and a second entry point that takes an array instead of
a page would be a second answer to that question for 1.8 s across the suite.

## For the next profiling run

Unchanged from CARD-241's note, and now with a second reason: **this file
renders**, it is not in `RENDER_HEAVY_SNAPSHOT`, and it does not match
`RENDER_API_PATTERN`'s eight names, so it will not be added by a grep. At
11.83 s / 150 tests the file averages 79 ms a test, still inside the band
`suite-hotspots-20261015.md` measures for the render-heavy set (181 ms/test),
and it is now the file's render cost rather than its measurement cost that
would be worth streaming: a streaming render would cut the peak to about one
page, which is the same recommendation CARD-241 recorded and the same reason
it was not worth the obscurity at 13 pages.
