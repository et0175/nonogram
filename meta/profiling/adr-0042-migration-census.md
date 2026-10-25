# ADR-0042 — the interior migration surface, counted

Taken 2026-10-25 on main at `c12c33ce`, during the architect pass that followed
ADR-0042's acceptance. Written so the phase's cards cite a measured set rather
than re-deriving one, and so the next orchestrator can tell which part of the
phase is actually expensive.

## The headline, and it corrects the spike

CARD-293's §6 priced the test migration as **"21 files, incremental"**. Derived
here instead of estimated: **32 test files** combine a pixel-reading idiom with
an interior subject, across **315 pixel-reading sites**.

The gap is not a contradiction — the spike said 21 and did not say how it
counted, and some of the 32 below are genuinely out of scope (see "What is not
in the set"). But the honest range is **21–32 files**, and the load-bearing
number is the one nobody had: **315 sites**.

**This makes the test migration the dominant cost of the phase, not the font and
not the writer.** The spike's own numbers say the mechanism is cheap — 163 lines
for the font, a 41-line stream assertion replacing 168 lines of pixel
archaeology. What it did not count is how many times that replacement has to be
made.

## How the set was derived

Two regexes over `tests/**/*.py`, requiring **both** to hit in one file:

* a surface **reading** idiom — `getpixel`, `.load()`, `np.asarray`,
  `np.array(`, `same_page`, `.getdata()`, `ImageChops`, `tobytes()`,
  `.convert("L")`
* an interior **subject** — `interior`, `book_pdf`, `BookPDFGenerator`,
  `solved_puzzle_page`, `guide_page`, `create_guide`, `puzzle_pages`,
  `export_book`, `proof_page`, `answer_page`, `toc`

Requiring both is what keeps the CLI/web exporters out. It is a detector, not a
verdict: a file in the table is a file to *look at*, and the second column is
the size of the look.

## The set

| px sites | interior refs | file |
|---:|---:|---|
| 47 | 230 | `tests/test_book_solved_answer_key.py` |
| 41 | 104 | `tests/test_book_pdf_band.py` |
| 34 | 330 | `tests/test_book_export_interior_cover.py` |
| 34 | 288 | `tests/test_book_pdf_memory.py` |
| 15 | 67 | `tests/test_book_pdf_levels.py` |
| 14 | 40 | `tests/test_book_proof_pages.py` |
| 12 | 50 | `tests/test_book_qr_slot.py` |
| 10 | 116 | `tests/test_book_pdf_ink_mode.py` |
| 10 | 123 | `tests/test_book_pdf_two_up.py` |
| 10 | 3 | `tests/test_layout_page_spec.py` |
| 8 | 98 | `tests/property/test_book_export_interior.py` |
| 8 | 67 | `tests/test_book_difficulty_dots.py` |
| 8 | 51 | `tests/test_book_guide_page_type.py` |
| 8 | 263 | `tests/test_book_toc.py` |
| 7 | 2 | `tests/helpers/pdf_pages.py` |
| 7 | 48 | `tests/test_book_puzzle_frame.py` |
| 5 | 96 | `tests/test_book_interior_face.py` |
| 4 | 41 | `tests/test_book_answer_key.py` |
| 4 | 114 | `tests/test_book_pdf.py` |
| 4 | 1 | `tests/test_export_image.py` |
| 4 | 14 | `tests/test_layout_answer_tiles.py` |
| 3 | 2 | `tests/helpers/shared_fixture_controls.py` |
| 3 | 20 | `tests/test_book_cover.py` |
| 2 | 106 | `tests/helpers/book_corpus.py` |
| 2 | 2 | `tests/helpers/page_ink.py` |
| 2 | 36 | `tests/test_book_cell_size.py` |
| 2 | 77 | `tests/test_book_guide_page.py` |
| 2 | 132 | `tests/test_book_page_frame.py` |
| 2 | 1 | `tests/test_shared_fixture_controls.py` |
| 1 | 1 | `tests/property/test_book_layout.py` |
| 1 | 1 | `tests/property/test_book_two_up.py` |
| 1 | 61 | `tests/test_book_solved_page.py` |

## What is not in the set, and must stay out

ADR-0042/R6 retires pixel reading **for interior pages only**. Three groups in
the table above are detections, not work, and a card that converts them is a
card that broke something:

* **`tests/test_book_cover.py`** and `same_page(cover_page, expected_cover)` at
  `tests/property/test_book_export_interior.py:652` — the **cover is raster** by
  ADR-0042/R2. It is a photograph; measuring its pixels is the only way to
  assert anything about it.
* **The section dividers** — raster for now by owner decision 2026-10-25.
  `tests/test_book_pdf_levels.py`'s divider assertions and
  `tests/test_book_interior_type_floor.py`'s `divider` face keep today's
  reading until CARD-231 lands, at which point the new design is born vector
  and the exception expires with it (ADR-0042/R2's own clause).
* **The independent oracles** — `Sheet` and its kind, which R6's statement
  exempts explicitly. The spike confirmed `Sheet`'s role survives intact. An
  oracle that recomputes the page independently and is compared against is not
  "measuring ink to recover a number the generator stated"; it is the second
  implementation the project's test style asks for.
* **`tests/test_export_image.py`** (4 px, **1** interior ref) and
  `tests/test_layout_page_spec.py` (10 px, **3**) — the low interior-ref counts
  are the tell. These are COMP-007's CLI/web surface, which **CON-019** holds
  byte-identical and ADR-0042 does not reach at all.

## What this implies for the card plan

Two things, both about shape rather than size.

**1. The migration does not want to be one card.** Thirty-two files at
`dispatcher.max_overlap: 0.3` would serialize against most of the board, and
four of the files are already somebody's: `test_book_export_interior_cover.py`
is CARD-276's (in flight), CARD-287's (344.29 s, the suite's dearest class) and
CARD-292's; `test_book_toc.py` is CARD-219's, just landed. A single migration
card collides with all of them. Spreading each file's conversion into the card
that owns its page kind keeps the impact sets small and lets the phase pipeline.

**2. The three heaviest files are the three the board already wants to cheapen.**
`test_book_solved_answer_key.py` (47), `test_book_pdf_band.py` (41),
`test_book_export_interior_cover.py` (34) and `test_book_pdf_memory.py` (34)
together hold **156 of the 315 sites, 49.5%**. CARD-287, CARD-288 and CARD-292
are all about the cost of exactly this neighbourhood, and the spike measured the
stream assertion at **4.1× smaller** than the ink one it replaces. The
conversion and the cheapening are the same work done once — which is an argument
for sequencing those three cards *with* the phase rather than before or after it.

`test_book_pdf_memory.py` deserves its own note: its subject is
`PAGE_BITMAP_BYTES = 2550 * 3300 * 3` (`:210`) and page-bitmap retention. The
spike measured interior retention falling from **1.00 to 0.000246** page
bitmaps, so most of that file's premise does not survive the phase. It is a
rewrite, not a retarget, and nobody has priced it.

## Provenance

Derived by two regexes over `tests/**/*.py` on main at `c12c33ce`, 2026-10-25.
Counts are idiom occurrences, not assertions — a site may need no change, and
one site may carry several claims. Re-derive rather than trusting the table if
the tree has moved; the regexes are quoted above in full so the derivation is
repeatable, per ADR-0039/R2's preference for a derived set over a written one.
