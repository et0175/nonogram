# CARD-145: The book PDF is written a page at a time, so a real book fits in memory

**Status:** in_progress
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
**Review score:** —
**Started:** 2026-09-24
**Closed:** —
**Actual:** —
**Merge commit:** —
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
