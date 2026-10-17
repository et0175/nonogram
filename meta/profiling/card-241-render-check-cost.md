# CARD-241 — what the render check costs (AC-6)

The round-mark render check (`tests/helpers/round_ink.py` plus the five
`TestRoundMarkOnThePage_*` classes in `tests/test_book_difficulty_dots.py`)
renders the book's interior pages and measures their ink. AC-6 asks for that
cost to be **measured and recorded** rather than discovered at a merge gate,
and for the check to be marked if it is too slow to run on every commit.

**It is not too slow, and it is not marked.** It runs with the rest of the
file, on every commit.

## The run

* worktree `card/241-round-mark-render-proof`, based on `main` @ `b894e00`
* host: the same Mac15,6 Apple M3 Pro / macOS 26.7.1 / Python 3.14.3 / pytest
  9.1.1 as `suite-durations-20261015.txt`, solo on the host
* command, from the worktree root:

```bash
/usr/bin/time -l ./.venv/bin/python -m pytest \
    tests/test_book_difficulty_dots.py -k RoundMarkOnThePage --durations=12
```

Nothing in `meta/profiling`'s frozen artefacts was re-measured or regenerated
to produce this file (CARD-241 G-5): it is a new record of one new test class's
cost, taken with the command above and nothing else.

## What it costs

| measurement | value |
|---|---|
| the 33 new tests, wall clock | **4.80 s** (4.63 s when first measured, with the 31 of them this card shipped before review cycle 1 added two) |
| the same file without them (CARD-228's 88 tests) | 1.65 s |
| the whole file after this card | **6.33 s / 121 tests** (6.41 s / 119 before the cycle-1 fix) |
| the slowest single test | 0.79 s (`test_every_spelling_is_caught`, four interiors) |
| interiors rendered and measured | **12** — ten memoised by `_book_ink` (the book as it really is, plus one per planted route), one rendered fresh by `test_reverting_the_plant_leaves_the_book_clean`, and the picture corpus |
| pages rendered and measured | **163** = 11 interiors x 13 baseline pages + 20 picture-corpus pages; plus one cover page, which is rendered and measured but is not an interior |
| per page: render + measure | ~15 ms + ~20 ms |
| peak resident set of the pytest process | **836 MB** (835–845 MB over three runs after the fix cycle) |

Share of the suite: 4.80 s against the 930.81 s of
`suite-durations-20261015.txt` is **0.5 %**, and the whole file is 0.7 %.

## What the fix cycle changed, measured

Review cycle 1 added two tests — a control for a mark lighter than the ink
level, and the metric's own size floor — and one interior render:
`test_reverting_the_plant_leaves_the_book_clean` now plants first and renders
the clean book itself, instead of relying on a warm module cache and pytest's
declaration order (F-008).

Measured as a before/after pair on the same host, three runs of each, the
pre-fix file restored from a byte copy for the "before" column:

| | before the fix | after |
|---|---|---|
| `-k RoundMarkOnThePage` | 4.28–4.39 s / 31 tests | 4.70–4.91 s / 33 tests |
| the whole file | 5.86–6.02 s / 119 tests | 6.18–6.48 s / 121 tests |

**+0.4 s**, for one interior render and two canvas tests, and the original
4.63 s / 6.41 s above reproduce within 5 % in the "before" column. Peak RSS is
unchanged — 835–851 MB over four runs, still 836 MB in round terms — because
the interiors are rendered one at a time whatever their number. The conclusion
stands: not too slow, not marked.

One caveat, recorded because it nearly went into this file as a figure: the
first attempt at this pair was taken while another card's full suite held the
repo lock, and read **7.15 s → 8.92 s** — both halves inflated by ~60 %. The
delta survived the load; neither absolute figure did.

## Two things the next profiling run should know

1. **This file now renders.** At 0.15 s/test average (0.79 s at the worst), the
   new class sits in the band `suite-hotspots-20261015.md` measures for the
   render-heavy set (181 ms/test over 1079 tests), so
   `tests/test_book_difficulty_dots.py` belongs in `RENDER_HEAVY_SNAPSHOT` the
   next time that snapshot is retaken. It is **not** added by this card:
   `RENDER_API_PATTERN` greps for eight render-API names and the call this file
   makes (`interior_pages`) is not one of them, so the file does not match the
   grep that defines the set, and re-freezing the snapshot under `meta/` is
   exactly what CARD-228's fix cycle correctly refused to do from an
   implementation card (its review's F-204). Recorded here instead.
2. **The 836 MB peak is the materialising call, not the measurement.** Peak
   RSS at three points of one standalone process, over three runs:

   | point | peak RSS | added |
   |---|---|---|
   | after imports | 63 MB | — |
   | after `interior_pages` (13 pages) | 461–518 MB | **+398 to +455 MB**, ~31–35 MB a page |
   | after measuring all 13 (3222 regions) | 553–565 MB | **+38 to +92 MB** |

   The attribution holds — the render is roughly ten times the measurement —
   but neither sub-figure this note first carried does. A page costs ~31–35 MB
   measured here, against the ~25 MB quoted from CARD-145; and the
   measurement's own footprint is tens of MB, not the 8.4 MB of one page's
   boolean mask. That mask is one allocation of several: `ink_regions` also
   holds the padded copy, the int64 edge/start/end arrays, and then three
   Python int lists plus a `parent` list over every horizontal run of the page
   (`_ink_runs` ends in `.tolist()`). The recommendation is unchanged and the
   numbers under it are now measured rather than estimated: a streaming render
   would cut the peak to about one page, at the cost of writing the streaming
   call's name in a way the render-set grep does not match; it was not worth
   the obscurity at 13 pages, and is the first thing to change if this check is
   ever pointed at a 306-page corpus book.
