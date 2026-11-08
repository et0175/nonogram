# CARD-415: The test PDF rasteriser stops asking poppler for PNG — raw gray pages, pixel-identical, about nine minutes off the gate

**Status:** done
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
**Review score:** 8.6 (cycle 1/3 - CERTIFIED)
**Started:** —
**Closed:** 2026-11-08T08:49Z
**Actual:** —
**Merge commit:** ff5621811384fb1ea52d3025ea9740717d1ac83c
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

Author notes (CARD-415, 2026-11-08; all figures from commands run in this worktree on a contended host, load average 4 to 8):

* Edit: `tests/helpers/pdf_vector.py::rendered_page` drops `-png`, globs `pg{N}-*.pgm`, parses `P5\nW H\n255\n`, returns `np.frombuffer(...).reshape(h, w).astype(np.int16)` (same dtype as the PNG path). Comment text only in `test_book_pdf_band.py` and `test_book_pdf_memory.py`. `_poppler_alone` stays PNG.
* AC-1 (identity): recorded one-shot script, no new test (the existing `TestBookPdfMemory_TheSharedReaderReadsEachPageForItself` already holds `rendered_page` against an independent PNG render). Old function (merge-base copy) vs new, every page, 72/100/150/300 dpi: baseline interior 14 pages, landscape 15, odd trim 15, square 15, cover 1 (the baseline carries the raster divider pages): 0 mismatches of shape, dtype and bytes. Control: a page rendered at the wrong dpi (100 vs 150, and 100 vs 101) differs. Not covered: a book with uploaded dividers.
* AC-2 (time): median `pdf_pages` on the baseline interior, 3 runs each, interleaved twice: before 3.64 s and 3.09 s, after 1.19 s and 0.81 s. Five heaviest files solo, before to after: property/test_book_pdf_geometry 281 s to 113 s; test_book_pdf 163 s to 101 s; test_book_export_interior_cover 157 s to 102 s; test_book_pdf_two_up 82 s to 26 s; property/test_book_export_interior 91 s to 34 s (another author ran modules concurrently throughout).
* Net collected node ids: 0.

[Review 1/3] Score: 8.6 (threshold 8.0 reached; 0 blockers; PASS; certified). The reviewer re-derived pixel identity: 643 comparisons, 0 mismatches, including uploaded dividers, the Play page, proof sheets, rotated and alpha pages, 72 to 600 dpi. Carried lows, recorded here and not carded: (1) no test pins the int16 dtype of the return value (a uint8 regression would go unnoticed); (2) the stale-file cleanup glob is untested (reproduced by the reviewer: a leftover pg1-01.pgm from a 14-page document can be returned for a later 1-page document in the same directory; the old code had the same untested gap); (3) malformed headers other than bad magic, maxval or length raise ValueError, not the RuntimeError the docstring promises; (4) concurrent calls on one prefix and directory can read a half-written PGM (no caller is concurrent); (5) the `Image` import in pdf_vector.py is now unused (the repo does not lint it).

[Closing note, merge gate, merged `ff5621811384fb1ea52d3025ea9740717d1ac83c` (branch tip `ae7fc52f`; main already contained the branch base, `git merge main` was a no-op; staged --no-ff merge into main)] What the merge delivers: `tests/helpers/pdf_vector.py::rendered_page` no longer asks poppler for PNG; it reads raw gray PGM pages (P5 header parse, RuntimeError on bad magic, maxval or length, int16 return as before), pixel-identical; comment-only edits in `tests/test_book_pdf_band.py` and `tests/test_book_pdf_memory.py`. Net collected node ids 0. Size datum: `git diff --shortstat` branch vs merge-base 4ee37522: 4 files changed, 27 insertions(+), 10 deletions(-) (3 test-tree files: 21 insertions, 9 deletions; the fourth is the card file). Estimate 1c against 1 review cycle = ratio 1.0 (no wall-clock Actual, by the owner's call).
Gate: impact_set answered SELECTION (5712 of 11705 collected, 75 test files, 43 always-on; 4 lifted marked files). Run 1 (`-m "not wave_close_only"` over the selection, armed with the per-worktree test database): 1 failed, 5696 passed, 1 skipped, 13 deselected, 1 xfailed in 1502.92 s (0:25:02). Run 2 (`-m wave_close_only` over the 4 lifted files): 9 passed, 167 deselected in 205.91 s. The one red was `tests/test_web_server.py::TestWebServer_BindsLoopbackOnlyByDefault::test_the_port_stays_free_on_every_other_interface` (`_port_is_free_on('192.168.0.106', 62555)` was False): an ephemeral port taken on the LAN interface by another process while the host ran other pytest runs; green alone (166 passed for the file, then 6 passed twice more); the card touches no server code. Environmental, not the tree. The one skip is the setrlimit(RLIMIT_AS) platform skip in `test_book_pdf_memory.py`. 4 `wave_close_only` tests remain owed at the wave close. The fast sanity set before the long run was green (1419 passed, 1 skipped). Tree hash of the staged merge before and after the run: e798a984a308d01752c2cf0621004c73d5182b24 both times.
Measured saving (the owner's measurement): the selection is not the full suite, so wall clock against the quiet 3516 s bare run is NOT comparable (25:02 + 3:25 vs 58:36 covers 5708 of 11705 tests). The comparable figure is per file against `gate-card395-rerun-per-file.md`: over the 74 files that ran in both, 2381.7 s -> 1697.4 s, i.e. 684 s (11.4 minutes) less, nearly all of it in the book PDF family (property/test_book_pdf_geometry 275.0 -> 124.6, test_book_pdf 158.7 -> 103.4, test_book_export_interior_cover 148.6 -> 95.4, test_kill_matrix 120.3 -> 53.1, property/test_book_export_interior 87.6 -> 36.9, test_browser_fixture_scope 81.3 -> 35.3, test_book_pdf_two_up 79.3 -> 26.2, test_book_cell_size 67.6 -> 24.0); files that do not rasterise are unchanged within noise (test_public_player_probe 425.7 -> 427.6). The host was not quiet: load average 3.5 to 7.8 throughout, one to two foreign pytest processes seen at times (the lock watch is in gate-card415-lockwatch.txt), so the second figure is an upper-bound-noisy one; the saving is real and of the predicted size (~9 minutes), on a gate that ran only the selection. Artefacts: ~/Documents/nonogram-reviews/suite-profile-2026-11-07/gate-card415-durations.txt, gate-card415-run2.txt, gate-card415-per-file.md, gate-card415-lockwatch.txt.

Gate block (verbatim head; the `run 1:` line is the 75-file selection command and the selection list follows it in the printed block, both unchanged here for length):
```
IMPACT GATE
answer: SELECTION -- run the commands below (marked tests are deferred: see marker)
tests: 5712 of 11705 collected (48.8%)
tests at this gate: 5708 of 11705
files: 75 test files, 43 of them always-on
marker: wave_close_only -- 13 marked tests in 6 files; 9 run at this gate (lifted files); 4 owed at the wave close (marked tests in files not lifted), of which 4 sit in files this gate selects and are deselected there
lift: 4 marked file(s), their marked tests run at this gate (rule S, subject edge)
run 2: python -m pytest -m wave_close_only tests/property/test_book_export_interior.py tests/property/test_book_pairing.py tests/property/test_book_pdf_geometry.py tests/test_book_export_interior_cover.py
exit code: 0
after those: nothing more is owed AT THIS GATE; 4 marked tests (wave_close_only) are owed at the wave close
```
