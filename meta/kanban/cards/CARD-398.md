# CARD-398: The baseline book render is built once per session and shared — the bitmap-interior tests that are left after the claim audit

**Status:** skipped
**Priority:** P2
**Category:** ops
**Estimate:** 3c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner ruling 2026-11-07 ("I'd do a+c, after measurement"; memory gate-time-cuts-a-and-c): C = pure speed, NO coverage move, each saving proven by a before/after --durations on the file alone. Measurement: ~/Documents/nonogram-reviews/suite-profile-2026-11-07/gate-card388-durations.txt (contended full run; shares only). Prior art: CARD-218 (render once per module; meta/profiling/card-218-render-sharing.md: 11 renders removed of 45, memory regression found and fixed).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-387, CARD-395
**Touches:** tests/helpers/book_corpus.py, tests/conftest.py, tests/test_book_pdf.py, tests/test_book_pdf_two_up.py, tests/test_book_cell_size.py, tests/test_book_divider_pages_option.py, tests/test_book_pdf_levels.py
**Review score:** n/a — **CLOSED AS A RECORDED NULL** on 2026-11-08: the measurement (~/Documents/nonogram-reviews/CARD-398-measure/) found 16 to 28 s of removable duplicate rasterisation per full run before CARD-387 (0 to 10 s after), against the card's own 40 s floor; the card's premise (the listed files re-render the SAME baseline book) is false for 7 of the files (they build ad-hoc puzzles). No work was done and none is owed.
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

<!-- HOLD UNTIL CARD-387 MERGES AND RE-MEASURE. CARD-387 (20c) converts or retires the raster interior tests by the claim audit and deletes the bitmap interior path: it declares test_book_pdf, test_book_pdf_two_up, test_book_pdf_band, test_book_pdf_memory, test_book_export_interior_cover, tests/helpers/book_corpus.py and tests/conftest.py. A render cache written now is built over files that card deletes or rewrites. The Touches above are the likely survivors; the author re-derives them from the post-387 tree, and if the book family has dropped below the AC-1 floor the card closes as a recorded null. -->
## Why this card exists

The book-PDF family is 1810 s in the measured run (39.3 % of summed time, 78 files); in the heaviest of them the time is in CALL (test_book_pdf 227.5 s call / 10.9 s setup; test_book_export_interior_cover 206.1 / 4.5; two_up 118.4 / 0.0; cell_size 90.1 / 0.1): each test renders the same baseline book (`tests/helpers/book_corpus.py::baseline_puzzles`, twelve pages) again. CARD-218 shared the render per MODULE and bought 11 renders of 45 in two files, at a memory price it had to claw back. This card shares the baseline render per SESSION across the files that still render it after CARD-387, behind a bounded cache (page digests, not retained bitmaps), so the memory regression CARD-218 met cannot recur.

## What to implement

1. After CARD-387 merges, re-derive the render census: which tests still render `baseline_puzzles()` with identical arguments (a count by `ast`, as `meta/profiling/measure_raster_share.py` and `rank_durations.RENDER_API_PATTERN` do), and the seconds they spend. Record it in `meta/profiling/card-398-render-census.md`.
2. A session-scoped, read-only cache keyed by the full argument tuple (print spec, puzzle list, ink mode, density), returning immutable results; a test that mutates a returned object fails by construction (frozen / copied on read).
3. Convert only tests whose key is identical to an already-rendered one and whose assertions only READ the result.

## Acceptance criteria

* **AC-1** (a floor first): the census shows at least 40 s summed of repeated identical baseline renders after CARD-387, else the card closes as a recorded null.
* **AC-2** (nothing moves): converted tests' assertions byte-identical; node-id set difference empty; each converted test still reds on its existing plant. (test: the converted files' own plants plus node-id diff.)
* **AC-3** (the cache cannot return a stale or aliased render): a test that changes one key component (ink mode, density, a puzzle) gets a different render; a returned page object cannot be mutated by a test. (test: new cells; plants: a cache keyed on a subset of the arguments, a cache that returns the live object.)
* **AC-4** (memory): peak RSS of the converted files together does not exceed the CARD-218 post-fix figure recorded in `card-218-render-sharing.md`; `tests/test_book_pdf_memory.py` is unchanged and green.
* **AC-5** (measured): before/after `--durations` on each converted file alone, three runs each, host cells recorded; saving stated per file.

## Guardrails

* **G-1** No render is faked: a cache hit is a real earlier render of the same arguments, never a stored golden.
* **G-2** Does not touch the marked sweeps' bodies (CARD-395's registry names them).
* **G-3** `tests/helpers/book_corpus.py` and `tests/conftest.py` are hotspots; not beside CARD-387, CARD-390..393 or CARD-395.

## System contract

* CARD-218 AC-2 — the memory cost of sharing is measured, not assumed (check: AC-4)
* ADR-0042 — the interior is vector; the bitmap path is CARD-387's (check: AC-1 re-derivation)

## Worktree notes

(none yet)

## CLOSED AS A NULL 2026-11-08

Measured read-only (not pytest) on a contended host (upper bounds): one baseline export 0.07 s; one `pdf_pages` rasterisation of the 14 baseline pages 3.45 s (about 2.5 s of it is Python overhead around poppler: one process spawn per page, the Pillow parse, the numpy conversion; one `pdftoppm` over all pages takes 0.65 to 0.89 s). Removable duplicates: test_book_pdf_memory 5 of 6 identical rasters, test_book_solved_answer_key 1, test_book_interior_face 1 to 2 => about 21 to 28 s per full run contended, 16 to 27 s quiet (assumed), 0 to 10 s after CARD-387. Under the 40 s floor. A possible cheaper lever, NOT carded: the per-call Python overhead of `pdf_pages` (applies to every rasterisation, needs no cache invalidation): needs its own measurement of how many calls a full run makes.
