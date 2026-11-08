# CARD-415: The test PDF rasteriser stops asking poppler for PNG — raw gray pages, pixel-identical, about nine minutes off the gate

**Status:** in_progress
**Priority:** P1
**Category:** enabler
**Estimate:** 1c (0.5d)
<!-- Small in code; the cost is the CARD-268 budget claim ('the bar is paid for above the toolbar, so the board sits where it sat'), which the larger buttons break and which must be re-paid, not relaxed. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-08 ("measure pdf_pages overhead then") and its measurement (~/Documents/nonogram-reviews/pdf-pages-overhead/analysis.md): the carried premise "2.5 s of Python overhead per call" was WRONG; 88 % of a `pdf_pages` call is `pdftoppm`'s PNG deflate (about 0.14 s per page), not spawn or Python. Dropping `-png` (raw gray PGM) is pixel-identical and 3.8x to 5x faster.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/helpers/pdf_vector.py, tests/test_book_pdf_memory.py
<!-- Derived from the tree at drafting time (2026-11-07), by reading which files hold the named behaviour; the author re-derives after the Depends-on cards merge, and the full-suite census of frozen registries (trace.yml, browser-family lists, tests/test_browser_fixture_scope.py) is named in the brief, not assumed. The accessible names 'Keep' and 'Contradiction' are used by tests that find buttons by role and name and by the `data-player-probe-action` attributes (the attributes are the stable handle and do not change). Serialize after CARD-410 (same bar) if both are in flight. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/helpers/pdf_vector.py::rendered_page` is the one place the tests rasterise a PDF page through poppler: it runs `pdftoppm -r DPI -f N -l N -gray -png`, one process per page, and re-reads the PNG with Pillow. Measured on a private clone (3 runs, interleaved shadow timings; a contended host): of 3.05 s per `pdf_pages` call on the 14-page baseline interior, `pdftoppm` is 2.70 s (88 %), the PNG read-back 0.29 s, everything else under 0.1 s. Process spawn is only 0.03 s; poppler's PNG compression is about 0.14 s per page; a single call over all pages is no faster (3.25 s PNG vs 0.67 s PGM). Writing raw gray (PGM) instead is pixel-identical on every fixture tried (baseline 14 pages, landscape, odd trim, square, a bitmap divider, the cover: 148 pages at 72/100/150/300 dpi, 0 differences) and 3.8x to 5x faster. Over the 32 test files that use the helpers an instrumented run counted 3067 `pdftoppm` calls = 787 s and measured 558 s saved by PGM: about 9.3 minutes, 15.9 % of the gate's attributed time.

## What to implement

1. In `rendered_page`: drop `-png`, write `pg{N}-*.pgm`, parse the `P5\nW H\n255\n` header, build the array with `np.frombuffer(...).reshape(h, w)` to the same dtype/shape the PNG path returned; change the stale-file glob/cleanup (`pg{N}-*.png`) to `.pgm`, keeping the CARD-355 shared-directory behaviour; fix the docstring and the two comments that say PNG (`test_book_pdf_memory.py`, `test_book_pdf_band.py` mention `page-*.png`: text only).
2. Keep the per-page process shape (do NOT render all pages in one call: no gain, and 14 pages at 300 dpi is about 118 MB of files).
3. `tests/test_book_pdf_memory.py::_poppler_alone` is an independent PNG control and STAYS PNG: it is the PNG-vs-PGM cross-check. If no existing test already asserts `rendered_page` equals an independent PNG render, add ONE small comparison cell (owner test budget: fewer tests); otherwise add none.
4. Check by name that `tests/test_book_pdf.py` (~line 5680, a source-text scan asserting `"rendered_page"` is among the readers it finds) and every census that scans helper source still pass.

## Acceptance criteria

- **AC-1** (identity): *Given* the baseline interior, a landscape book, an odd-trim book, a square book, a bitmap divider page and the cover, *when* rendered with the old (PNG) and the new (PGM) path, *then* every page has the same size, mode and bytes; shown by the one comparison cell or by a recorded one-shot script whose output is in the closing note. (test: the existing PNG control or the one cell.)
- **AC-2** (time): the closing note states the median `pdf_pages` seconds on the baseline interior before and after (target about 3.4 s to about 0.9 s on the same host) and the wall seconds of the five heaviest helper-using files (`property/test_book_pdf_geometry.py`, `test_book_pdf.py`, `test_book_export_interior_cover.py`, `test_book_pdf_two_up.py`, `property/test_book_export_interior.py`) before and after, solo. (review-lens, evidence: the numbers.)
- **AC-3** (nothing else moves): no test file other than the helper changes except comments; no test is added unless AC-1 needs it; the net collected-node-id change is 0 or +1.
- **AC-4** (censuses): the call and position censuses (`test_book_export_interior_cover.py`), `test_admin_binding` unanalysable calls, `RENDER_HEAVY_SNAPSHOT`, the source-text scan above and the impact-set tests are green; any figure that moves is re-derived and attributed, never pasted.

## Guardrails

* **G-1** Pixel identity is the claim: if any page differs, STOP and report (do not loosen a tolerance).
* **G-2** Edit the helper only; no corpus shrunk, no bound widened, no test skipped.
* **G-3** `pdftotext` (`extracted_text`, 512 calls, 19 s) is out of scope.

## System contract

* ADR-0039 — controls that can fail (check: the comparison cell or the recorded script with its plant: a page rendered at the wrong dpi must differ)

## Worktree notes

(none yet)
