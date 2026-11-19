# Book page packing: how many puzzles and solutions share a page

This is the one place the book's packing rule is written down (owner ruling
2026-11-07: "1 puzzle per page for big, 2 for small, solutions 4"). The
constants block and the three tables below are **generated from the code** and
held to it by `tests/test_book_page_packing_doc.py` (CARD-232 AC-8): a constant
or a planner change that moves a figure reds that test until the blocks are
re-recorded with

```
PYTHONPATH=src python -m tests.test_book_page_packing_doc
```

Everything outside a `BEGIN`/`END` block is prose and is not generated.

## Constants

<!-- BEGIN packing-constants -->
| Constant | Value | Defined in |
|---|---|---|
| `TWO_UP_MIN_CELL_MM` | 7.000 | `src/nonogram/export/layout.py` |
| `MIN_CELL_MM` | 2.000 | `src/nonogram/export/layout.py` |
| `SOLVED_TILE_CAPACITIES` | (2, 4) | `src/nonogram/export/layout.py` |
| `SOLVED_TILE_GAP_MM` | 4.000 | `src/nonogram/export/layout.py` |
| `SOLVED_TILE_MAX_CELL_MM` | 6.000 | `src/nonogram/export/layout.py` |
| `INTERIOR_FOOTER_MM` | 9.878 | `src/nonogram/export/layout.py` |
| `RUNNING_HEAD_MM` | 9.000 | `src/nonogram/admin/book_pdf_generator.py` |
| `PACKED_MAX_WIDTH` | 30 | `src/nonogram/admin/book_answer_key.py` |
| `PACKED_MAX_HEIGHT` | 30 | `src/nonogram/admin/book_answer_key.py` |
| `BOOK1_PROFILE.band_mm` | 12.000 | `src/nonogram/admin/book_page_spec.py` |
| `BOOK1_PROFILE.cell_cap_mm` | 7.500 | `src/nonogram/admin/book_page_spec.py` |
<!-- END packing-constants -->

## Puzzle pages: one, or two that fit

Two puzzles share a page only when all of these hold (FR-040, INV-010):

- they are **neighbours** in the book order, and the walk is greedy and
  forward-only: it offers puzzle *i* with *i+1*, and if the pair is refused it
  prints *i* alone and offers *i+1* with *i+2* (`BookPDFGenerator.puzzle_pages`);
- they are the **same level** (a readable tier). A puzzle with no readable
  tier never pairs, and no pair straddles a level divider;
- they **fit together** at a shared cell of at least `TWO_UP_MIN_CELL_MM`
  (`compute_pair_layout`), each under its own band, both above the footer
  strip. The pair prints at the smaller of the two puzzles' book cells
  (CARD-225), capped at `BOOK1_PROFILE.cell_cap_mm`.

Otherwise each puzzle gets its own page. Never more than two.

**The footer strip is reserved on every puzzle page (CARD-485).** A two-up
page fits its drawings above the footer strip, and so does a single-puzzle
page: `compute_layout`'s `footer_reserve_px` is passed by the generator's
single-puzzle page and by `book_page_spec.book_cell_mm`, so the cell a
puzzle is listed at is the cell it prints at, with the grid above the footer
rule. The behaviour is held by `tests/test_book_page_numbers.py`'s
`TestBookPageNumbers_FolioNeverCollidesWithTheGrid`
(`test_every_single_page_draws_its_footer_group_on_the_owners_profile`,
`test_no_single_page_of_the_extent_sweep_reaches_below_the_footer_rule`);
this document only states it.

Whether two puzzles fit depends on their **clue depth**, not only their size,
and on the trim. The table gives, for two same-level neighbours of one size,
the deepest clue depth at which they still share a page. "Depth *d*" means
every row and every column clue holds *d* numbers (or as many as the line
can hold); "1" means they never share a page at any depth.

<!-- BEGIN puzzles-per-page -->
| Size (w x h) | 8.5x11 in (default) | 8x10 in | 6x9 in | A4 |
|---|---|---|---|---|
| 10x10 | 2 up to depth 5 | 2 up to depth 3 | 2 up to depth 2 | 2 up to depth 5 |
| 12x12 | 2 up to depth 3 | 2 up to depth 1 | 1 | 2 up to depth 4 |
| 15x10 | 2 up to depth 8 | 2 up to depth 3 | 2 up to depth 2 | 2 up to depth 8 |
| 15x15 | 1 | 1 | 1 | 2 up to depth 1 |
| 15x20 | 1 | 1 | 1 | 1 |
| 20x10 | 2 up to depth 7 | 2 up to depth 3 | 1 | 2 up to depth 6 |
| 20x15 | 1 | 1 | 1 | 2 up to depth 1 |
| 20x20 | 1 | 1 | 1 | 1 |
| 25x25 | 1 | 1 | 1 | 1 |
| 30x10 | 1 | 1 | 1 | 1 |
| 10x30 | 1 | 1 | 1 | 1 |
| 30x30 | 1 | 1 | 1 | 1 |
<!-- END puzzles-per-page -->

Each row models a book of just those two puzzles. In a real book a pair is
also capped at the smallest cell of its grid size across the whole book
(`_pair_cell_mm`, CARD-225), so a deeper-clued puzzle of the same size
elsewhere in the book can stop a pair the table shows as fitting.

So on the default 8.5x11 trim, "small" (two to a page) in practice means
10x10 to 12x12 and wide-but-short grids with shallow clues; 15x15 and larger
always print one to a page.

## Solution pages: every solution is a tile, four to a page

- **Every solution is a tile** in a 2 x 2 grid, each tile carrying its clues,
  its header and its caption (CARD-232, owner ruling 2026-11-07). Every size
  the book supports qualifies (`PACKED_MAX_WIDTH` x `PACKED_MAX_HEIGHT`).
- `plan_small_answer_pages` walks the answers in puzzle-number order and cuts
  each **level's run** into pages of four. A page never holds two levels.
- **A short last page keeps the 2 x 2 positions**: the one to three answers
  left at the end of a level sit where the first ones of a full page would,
  at the tile size of a full page (CARD-232 AC-4, owner 2026-11-09).
- The walk reads extents only. The degrade pass after it
  (`book_pdf_generator._degrade_infeasible_packed_pages`) checks each page
  with the real clue depths: if four tiles cannot reach `MIN_CELL_MM`, the
  page becomes two 2-up pages (`SOLVED_TILE_CAPACITIES`' 2), and a pair that
  still cannot reach it prints one answer per page.

Tile geometry (`compute_packed_solved_layout`), on the answer page's own
usable area (`answer_section_spec`: the trim less the margins, less
`RUNNING_HEAD_MM` at the top for the running head and `INTERIOR_FOOTER_MM`
at the bottom for the folio):

```
rows         = capacity / 2                                 (2 on every planned page, 1 when degraded to 2-up)
tile width   = (usable width  - SOLVED_TILE_GAP_MM) / 2
tile height  = (usable height - (rows - 1) x SOLVED_TILE_GAP_MM) / rows
drawing room = tile height - band_mm                        (each tile keeps its own header band)
cell = min(SOLVED_TILE_MAX_CELL_MM, the largest cell at which every answer on the page fits its tile)
```

One cell for the whole page; each drawing is centred in its tile below its
band (owner's option B, 2026-11-09). The tables give the page the first of
four same-size, same-level answers lands on, and its cell: at a typical clue
depth of 3, and at the deepest clues the size can have.

Typical clues (depth 3):

<!-- BEGIN solutions-per-page-typical -->
| Size (w x h) | 8.5x11 in (default) | 8x10 in | 6x9 in | A4 |
|---|---|---|---|---|
| 10x10 | 4 at 6.00 mm | 4 at 6.00 mm | 4 at 4.73 mm | 4 at 6.00 mm |
| 12x12 | 4 at 6.00 mm | 4 at 5.79 mm | 4 at 4.10 mm | 4 at 6.00 mm |
| 15x10 | 4 at 5.18 mm | 4 at 4.83 mm | 4 at 3.42 mm | 4 at 5.02 mm |
| 15x15 | 4 at 5.18 mm | 4 at 4.83 mm | 4 at 3.42 mm | 4 at 5.02 mm |
| 15x20 | 4 at 4.49 mm | 4 at 3.94 mm | 4 at 3.39 mm | 4 at 4.87 mm |
| 20x10 | 4 at 4.05 mm | 4 at 3.78 mm | 4 at 2.67 mm | 4 at 3.93 mm |
| 20x15 | 4 at 4.05 mm | 4 at 3.78 mm | 4 at 2.67 mm | 4 at 3.93 mm |
| 20x20 | 4 at 4.05 mm | 4 at 3.78 mm | 4 at 2.67 mm | 4 at 3.93 mm |
| 25x25 | 4 at 3.33 mm | 4 at 3.10 mm | 4 at 2.20 mm | 4 at 3.23 mm |
| 30x10 | 4 at 2.83 mm | 4 at 2.63 mm | 1 per page | 4 at 2.74 mm |
| 10x30 | 4 at 3.13 mm | 4 at 2.75 mm | 4 at 2.36 mm | 4 at 3.40 mm |
| 30x30 | 4 at 2.83 mm | 4 at 2.63 mm | 1 per page | 4 at 2.74 mm |
<!-- END solutions-per-page-typical -->

Deepest clues (every line as full of numbers as it can be):

<!-- BEGIN solutions-per-page-deepest -->
| Size (w x h) | 8.5x11 in (default) | 8x10 in | 6x9 in | A4 |
|---|---|---|---|---|
| 10x10 | 4 at 6.00 mm | 4 at 5.79 mm | 4 at 4.10 mm | 4 at 6.00 mm |
| 12x12 | 4 at 5.18 mm | 4 at 4.83 mm | 4 at 3.42 mm | 4 at 5.02 mm |
| 15x10 | 4 at 4.05 mm | 4 at 3.78 mm | 4 at 2.67 mm | 4 at 3.93 mm |
| 15x15 | 4 at 4.05 mm | 4 at 3.78 mm | 4 at 2.67 mm | 4 at 3.93 mm |
| 15x20 | 4 at 3.44 mm | 4 at 3.02 mm | 4 at 2.60 mm | 4 at 3.74 mm |
| 20x10 | 4 at 3.11 mm | 4 at 2.90 mm | 4 at 2.05 mm | 4 at 3.01 mm |
| 20x15 | 4 at 3.11 mm | 4 at 2.90 mm | 4 at 2.05 mm | 4 at 3.01 mm |
| 20x20 | 4 at 3.11 mm | 4 at 2.90 mm | 4 at 2.05 mm | 4 at 3.01 mm |
| 25x25 | 4 at 2.45 mm | 4 at 2.29 mm | 1 per page | 4 at 2.38 mm |
| 30x10 | 4 at 2.07 mm | 1 per page | 1 per page | 4 at 2.01 mm |
| 10x30 | 4 at 2.30 mm | 4 at 2.01 mm | 2 at 3.82 mm | 4 at 2.49 mm |
| 30x30 | 4 at 2.07 mm | 1 per page | 1 per page | 4 at 2.01 mm |
<!-- END solutions-per-page-deepest -->

On the default trim every tabulated size stays four to a page even at its
deepest clues; among the tabulated trims the degrade pass fires only on the
smaller ones (the owner prints
8.5x11 for now; narrow-trim effects are recorded, not gated).

## What the tables are made from

- The planner calls are the export's own, in its order
  (`BookPDFGenerator.interior_stream`): `puzzle_pages` with the book's
  `cell_sizes`; `plan_small_answer_pages`, then the degrade pass on
  `answer_section_spec`, then `compute_packed_solved_layout` on the same spec.
- The margins are the Book 1 profile's (`BOOK1_PROFILE`); the trims are the
  panel's "Common sizes". The panel accepts any trim from 10 cm up; those are
  not tabulated.
- The puzzles are synthetic: an all-filled grid of the size with uniform clue
  depth, because the planner reads only extents and clue depths. Real pictures
  have uneven clues; the deepest line is what counts.

## Not covered here

- Page-count estimates before export (`book_kdp.unpaired_interior_page_count`
  deliberately stays an un-packed upper bound; CARD-202's notes say why).
- The Arrangement screen's page breaks: they come from the same
  `section_plan` call, so they follow this rule, but the screen is not
  described here.
- What a tile draws (header, caption, clue boxes): CARD-233 and CARD-208.

## History

- CARD-134: the first packed answer key, grid-only answers six or four to a
  page by a 20-cell longest-side switch, with a 5 mm answer cap.
- CARD-198: replaced it with one full solved page per puzzle, with clues.
- CARD-202 (owner 2026-10-08): answers up to 15 wide and 20 tall packed two
  or four to a page with their clues; larger ones kept a full page.
- Owner ruling 2026-11-07: "1 puzzle per page for big, 2 for small,
  solutions 4". CARD-209's three-to-a-page tiling for wide-but-short answers
  was withdrawn and retired into CARD-232.
- Owner decisions 2026-11-09 (CARD-232): every size up to 30x30 packs; a
  level's short last page keeps the 2 x 2 positions; grids are centred in
  their tiles below their bands; `MIN_CELL_MM` stays 2.0 and the degrade
  pass stays.
- CARD-485 (2026-11-19): a single-puzzle page reserves the footer strip as a
  two-up page does.
- CARD-232 AC-8/AC-9 (2026-11-19): this document; the retired rule removed
  from FR-042 and the book requirement docs.
