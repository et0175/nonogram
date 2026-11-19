# CARD-232: Solutions become fixed tiles, four to a page in a 2x2 grid, each with its clues

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 2c
<!-- RESTATED in review cycles 2026-11-07 at the owner's page-packing ruling (was `1d`): the card now also lands the packing rule's documentation (docs/BOOK_PAGE_PACKING.md with generated tables and a test that holds them to the code) and drops the wide-but-short exception, so the same tile rule covers every solution. The owner lifted the 1d cap for deliverables on 2026-11-06. -->
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/232-solution-tiles-rest
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-232
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Solutions: fixed tiles, with clues"
**Idea:** IDEA-168
**Wave:** 82
**Depends on:** CARD-222 (the frame), CARD-225 (the cell size rule the tiles inherit), CARD-322
<!--ADDED 2026-10-30 on the owner's decision "move from raster to vector first", and it closes a MEASURED HOLE rather than encoding a preference. Re-derived that day: all 10 cards gated by the 2026-10-25 ADR-0042 pass had **zero open dependencies** -- every `Depends on` entry already `done` -- so the ONLY thing holding them was the `Revision pending: true` flag. A flag is cleared by decomposing, which means re-cutting any of these would have RELEASED it into the wave queue ahead of the conversion its tests are supposed to target. This card is one of the 6 whose tests retarget from measuring ink to reading the content stream, and that is a TECHNICAL dependency, not a sequencing preference: the pages must BE streams (CARD-322) and the placed-edge convention must be settled (CARD-330, which CARD-322 already depends on) before an AC here can name a value. Re-cut before that and these ACs get written against a convention that does not exist yet, then need re-cutting again. The board's standing rule is that a sequencing PREFERENCE must not be written as a dependency; this is the other case, so it is. -->
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_solved_answer_key.py, tests/test_book_solved_page.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card232.json, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/, docs/BOOK_PAGE_PACKING.md, tests/test_book_page_packing_doc.py, meta/architecture/requirements.yml, docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md
**Review score:** —
**Started:** 2026-11-19T17:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## [OWNER RULING 2026-11-07, page packing]

The owner said, after the page-packing measurement (`~/Documents/nonogram-reviews/page-packing-measurement/REPORT.md`): **"1 puzzle per page for big, 2 for small, solutions 4."** Consequences:

* **Solutions: always four to a page**, in a 2x2 grid of fixed-size tiles, for EVERY solution. The "small packs, large takes a full page" rule (CARD-202: width <= 15 and height <= 20) is withdrawn, and so is CARD-209's three-to-a-page tiling for wide-but-short solutions (**CARD-209 is retired into this card**). There is no 6-up and no 3-up. A leftover keeps the tile size and the tile positions (AC-4), it is not repacked as 2 + 1.
* **Puzzles: 1 per page for big puzzles, 2 for small.** This is already how the product behaves: two puzzles share a page when two same-level neighbours fit at a shared cell of at least 7.0 mm (`TWO_UP_MIN_CELL_MM`, FR-040), otherwise one per page. The orchestrator read the owner's "small" as that geometric fit, NOT a size-only cut (the measurement shows the verdict depends on clue depth and trim as well as size: on 8.5x11, 10x10 and 12x12 pair when their clues are shallow, 15x15 and larger never pair). The card documents it as a table by size and trim; if the owner wants a size-only cut instead, that is a different rule and a different card.
* **The rule is written down once**: `docs/BOOK_PAGE_PACKING.md`, with a constants block and the size-by-trim tables GENERATED from the code and held by a test (the QR-shape block in docs/deploy/player.md is the precedent: `tests/test_public_player_pages.py::test_the_qr_url_shapes_here_are_the_shipped_routes`), so the page cannot drift. The agent's outline (parts marked G are generated and held by a test, P are prose) is in the measurement report. The stale statements of the old rule are corrected in the same change: FR-042 and AC-261..266 in `meta/architecture/requirements.yml` (6-up/4-up by a 20-cell longest side, no clues, 5 mm cap, level headings), `07-book-assembly-and-the-admin-panel.md` (about its line 363), `docs/book_generation_req/book_generation_admin_panel.md` and `book_admin_ui_requirements.md` rule 12, and the `book_answer_key.py` module docstring; the dead `SIX_UP`, `SIX_UP_LONGEST_SIDE`, `page_capacity` and `pack_answer_pages` in `book_answer_key.py` (no production caller, measured) are removed or marked, with the reason, in the same change.
* **The physics the owner has not yet seen (inferred, NOT measured; AC-5 measures it):** a 2x2 tile on 8.5x11 is about 95 mm wide, so a 30x30 solution in a tile gets a cell of very roughly 2.5 to 3 mm (the 15x15 four-up cell is 5.18 mm today), where clue digits cannot meet the printed-type floor. The owner decides what a tile does about clues when the numbers are in front of them; this card must not decide silently.
* **Open for the owner, not blocking the card's start:** which trims the product promises to pack for (on 6x9 and smaller nothing pairs, today); whether ungraded puzzles keep their current behaviour (they never pair, but their answers pack together).

## What to implement

**The owner's requirement:** *"Each solution sits in a tile of the same size, four to a page in
a 2 x 2 grid, with its clues in the same grey boxes as the puzzle pages... Within a page, every
grid is centred in its tile, so the tiles line up even when grid sizes differ."*

**Current behaviour (shipped over three cards — read them before changing anything).**
CARD-197/198 put the solved grid, its clues and a caption on the answer pages; CARD-202 packs
**small** solutions (width<=15, height<=20) 2-or-4 to a page while others take a full page;
CARD-203 moved the caption closer to the grid and right-aligned it with it; CARD-204 added
`caption_slot` after a 65-character picture name put ink 9.6 mm outside the page, then fixed a
clamped caption overprinting the folio. All of that machinery is in
`book_answer_key.py` + `book_answer_vector.py`'s `draw_answer_slot` / `answer_page_stream` /
`packed_answer_page_stream` (the vector writers; the raster `_draw_solved_slot` /
`solved_puzzle_page` / `_packed_answer_page` they replaced are production-dead and are deleted by CARD-387's tail, not edited here).

**What changes.**

1. A solution sits in a **tile of fixed size**, four to a page in a **2x2 grid** — so tiling is
   the rule rather than a size-dependent exception. CARD-202's "small solutions pack, others
   take a page" becomes "every solution is a tile", with one exception the owner keeps
   explicitly: ~~wide-but-short solutions stay on CARD-209's one-column, three-row page~~ **[WITHDRAWN 2026-11-07 by the owner's ruling below: there is NO exception; CARD-209 is retired into this card.]**
2. Each tile carries **its clues**, in the same grey boxes as the puzzle pages (CARD-208).
3. **Every grid is centred in its tile**, so the tiles line up across differing grid sizes.
4. The tile header (number, name, dots) and the page's running head are **CARD-233**.

**The trap, named.** `draw_answer_slot`'s return value has **two** consumers,
`answer_page_stream` and `packed_answer_page_stream`, which must change together; nothing in the code
enforces it. That asymmetry produced gating defects in CARD-203 cycle 1, CARD-203 cycle 2,
CARD-204 Fix 7 and CARD-204 cycle 5 — "the same two call sites, the same asymmetry, one card
later", in the reviewer's words. It is in `backlog.md` as a standing retro item. This card
rewrites exactly that area: change both consumers in the same commit, and if the return value
can be made a value object both must take, do that and say so.

## Acceptance criteria

- **AC-1** (happy, 2x2): *Given* a book of solutions, *when* the answer pages are exported,
  *then* each full answer page holds four tiles in a 2x2 grid, all four tiles the same size.
  (test: `TestSolutionTiles_FourToAPageInTwoByTwo`)
- **AC-2** (happy, clues in every tile): *Given* each tile, *then* its clues are drawn in the
  grey boxes, on the same two sides as the puzzle pages.
  (test: `TestSolutionTiles_EveryTileCarriesItsClues`)
- **AC-3** (happy, centred in its tile): *Given* a page whose four solutions have different
  grid sizes, *then* each grid is centred in its own tile and the four tiles' boxes are
  identical. (test: `TestSolutionTiles_GridsAreCentredInIdenticalTiles`)
- **AC-4** (edge, a short last page): *Given* a solution count that is not a multiple of four,
  *then* the last page holds the remainder in the same tile positions — no resizing to fill.
  (test: `TestSolutionTiles_LastPageKeepsTheTileSize`)
- **AC-5** (no exception, the owner's ruling of 2026-11-07): *Given* a wide-but-short solution (30x10, 20x10, 10x30 and the like), *then* it is a tile like every other: four to a page in the 2x2 grid, the same tile furniture, and the cell it gets is whatever the tile fits. *Given* any size and any trim the panel offers, *then* the card MEASURES the cell and the clue-digit size in a tile (a table in the card's closing note) and STOPS to ask the owner if any tile's cell falls below `MIN_CELL_MM` (2.0 mm) or its clue digits fall below the printed-type floor (CON-020); the owner then chooses: drop the clues on such tiles, give that size a full page, or a larger tile. (test: `TestSolutionTiles_EverySolutionIsATile`, with a plant that gives one shape its own page and reds; the measurement table is recorded, not asserted)
- **AC-6** (guard, the caption defect stays fixed): *Given* a 65-character picture name, *then*
  no ink leaves the usable area and nothing overprints the folio, on the tiled page. (test: the existing `caption_slot` classes in `tests/test_book_solved_page.py`)
- **AC-8** (the rule is documented once and held): *Given* `docs/BOOK_PAGE_PACKING.md`, *then* its constants block equals the code's constants (`TWO_UP_MIN_CELL_MM`, `SOLVED_TILE_CAPACITIES`, `SOLVED_TILE_GAP_MM`, `SOLVED_TILE_MAX_CELL_MM`, `MIN_CELL_MM`, `INTERIOR_FOOTER_MM` and the others the outline lists) and its puzzles-per-page and solutions-per-page tables equal what the real planner produces for each documented size and trim, with a plant that changes a constant and one that edits a table cell and reds. (test: `tests/test_book_page_packing_doc.py`, named by the implementation)
- **AC-9** (the old rule is gone from the docs): *Given* FR-042 and the documents named in the ruling above, *then* none states the 6-up rule, the 20-cell longest-side threshold, grid-only tiles or a 5 mm answer cap; a grep-based cell with a plant holds it. (test: named by the implementation)
- **AC-7** (edge, the page count): *Given* the corpus, *then* the answer section's page count is
  recorded against CARD-202's packing and the change attributed, and
  `unpaired_interior_page_count` agrees with what was written.
  (test: `TestSolutionTiles_AnswerPageCountIsAttributed`)

## Guardrails

- G-1: INV-002 — a solution is only ever the stored, verified solution; nothing here recomputes
  one (check: review-lens).
- G-2: ADR-0033/R1 — book assembly never changes a puzzle's grid, clues, tier or strategies
  (check: review-lens).
- G-3: Both consumers of `draw_answer_slot`'s return value (`answer_page_stream`, `packed_answer_page_stream`) change together (G-3 of CARD-226,
  restated because this is the card that actually rewrites them).
- G-4: Every answer page keeps its folio (test:
  `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-5: Out of scope — the tile header and running head (CARD-233), the clue boxes' own drawing
  (CARD-208).
- G-6: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.
- G-7: Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module (solved_page + answer_key group, 103 ids, per CARD-387's recount; CARD-233 shares the group).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-232 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-002** — its own `check:` ref is dead; logged in `backlog.md` and unaffected by the
  2026-10-17 delta, so review-lens remains the check until that is fixed.

- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membe… (check: review-lens)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-042 (the answer key), FR-033 (titles only in the answer key).
- **INV:** INV-002.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0033/R1, ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [This card replaces a rule, not a figure] CARD-202's "small solutions pack, the rest take a
  page" was itself an owner decision (2026-10-08, no six-up) and CARD-209 was cut from the same
  doc. Read both cards' notes before changing the packing predicate: the owner has already
  ruled on tiling density twice, and this card narrows those rules to "always a tile" with
  CARD-209's page as the single exception.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** the design implemented on a raster interior, with its acceptance criteria
verified by measuring ink on a rendered bitmap.

**Should be:** the same design, unchanged — **the card's instrument moves, not its
decision**. CARD-293 §6 classifies this card as *written, tests retargeted*: solutions as fixed tiles four to a page — page composition.

**Delta:**
- The design is **not** reopened. Nothing about what the page should look like
  changes here.
- The acceptance criteria's verifying tests move from ink measurement to
  assertions against the written PDF's content stream (ADR-0042/R6). The spike
  measured that replacement at **168 -> 41 lines, 4.1x smaller**, strictly more
  exact, and still discriminating under mutation.
- Scheduled **after** the vector phase (CARD-294..CARD-299) so the card is written
  against a vector page from the start. That ordering is the whole reason the
  phase runs first: dispatching this card before it would mean writing
  pixel-measuring tests and then converting them.

## Triage 2026-11-09

Mostly built: every answer up to 30x30 packs four to a page with shaded clues and one shared cell. Left: a leftover page of one or two answers still drops to capacity 2 instead of keeping the 2x2 positions (AC-4), grids are top-aligned rather than centred in their tiles (AC-3), the packing doc and its test (AC-8), the old 6-up wording in requirements.yml and docs (AC-9), and what happens when four tiles cannot reach the minimum cell.

**Owner decisions, 2026-11-09 (later the same day).**
- AC-3: option B of three rendered mock-ups. Each grid is centred in the room between its own header band and the tile's foot, while the bands stay at the tile tops, so headers in a row share one line. Built in `export.layout._packed_tile_layout`, and the packed-answer goldens were re-recorded.
- Minimum cell: keep `MIN_CELL_MM = 2.0`. A page whose four tiles cannot reach it still falls back to two tiles, or a full page. That is no longer an open point.
- AC-4, agreed with the owner the same day: a level's last page of one to three answers keeps the 2x2 positions. `plan_small_answer_pages` cuts pages of up to four, all at capacity 4, and `PackedAnswerPage.capacity` is now a field (default 4) that only the degrade path sets to 2.
- Still open: the packing doc (AC-8) and the old 6-up wording (AC-9).

## Wave 82 scope (2026-11-19)

Re-read against main and the owner's live book (interior downloaded 2026-11-19): every answer page already prints four solutions in a 2x2 grid with shaded clues and one shared cell, centred per the owner's option B, and a level's short last page keeps the 2x2 positions. AC-1..AC-7 are built (Triage 2026-11-09 above). **This wave's scope is what is left:**

1. **AC-8**: `docs/BOOK_PAGE_PACKING.md` with its constants block and its puzzles-per-page / solutions-per-page tables generated from the code and held by a test (with the two plants the AC names). It must state CARD-485's rule: a single-puzzle page reserves the footer strip like a two-up page.
2. **AC-9**: the old rule (6-up, the 20-cell longest-side threshold, grid-only tiles, a 5 mm answer cap) gone from FR-042 and the named docs, held by a grep cell with a plant.
3. **IDEA-168** (folded in): CARD-202's eight dormant minors in the packed path, e.g. `_packed_tile_layout` setting `Layout.margin` to a tile's absolute y-offset and `interior_stream`'s stale "no longer used to pack anything" docstring. Re-verify each; fix the live ones inline, one line each in the notes for the dead ones.

Estimate restated from 4c to 2c for this remainder. The old branch name `card/232-solution-tiles` no longer exists and is not reused.


### Wave 82 implementation notes

**AC-8 (the rule documented once and held).** `docs/BOOK_PAGE_PACKING.md`: a constants block (`TWO_UP_MIN_CELL_MM`, `MIN_CELL_MM`, `SOLVED_TILE_CAPACITIES`, `SOLVED_TILE_GAP_MM`, `SOLVED_TILE_MAX_CELL_MM`, `INTERIOR_FOOTER_MM`, `RUNNING_HEAD_MM`, `PACKED_MAX_WIDTH`/`HEIGHT`, the profile's `band_mm`/`cell_cap_mm`), a puzzles-per-page table (deepest clue depth at which two same-level neighbours still pair) and two solutions-per-page tables (depth 3, deepest), each by 12 sizes x 4 trims (8.5x11, 8x10, 6x9, A4). Every block is regenerated at test time by `tests/test_book_page_packing_doc.py` from the export's own calls (`puzzle_pages` + `cell_sizes`; `plan_small_answer_pages` -> `_degrade_infeasible_packed_pages` on `answer_section_spec` -> `compute_packed_solved_layout`) and compared byte for byte (`test_the_packing_doc_states_the_codes_constants`, `test_the_packing_doc_tables_are_what_the_planner_produces`); the first also asserts the doc states CARD-485's footer rule. Re-record: `PYTHONPATH=src python -m tests.test_book_page_packing_doc`. The puzzles-per-page generator asserts pairing is monotone in depth before writing "up to depth d".
- Plant P1: `SOLVED_TILE_GAP_MM = 5.0` -> both AC-8 tests red (constants diff `5.000` vs `4.000`; 6x9 10x10 typical cell 4.69 vs 4.73).
- Plant P2: doc cell `4 at 4.73 mm` -> `4.74` -> `test_the_packing_doc_tables_are_what_the_planner_produces` red.

**AC-9 (the retired rule gone).** `test_the_retired_answer_key_rule_is_gone_from_the_requirements_and_docs` greps FR-042's parsed statement/given/when/then/EC statements (comments are history and are not read), the 07 how-it-works "The answer key" section and its `book_answer_key.py` bullet, BK-8's three lines in `book_generation_admin_panel.md`, rule 12 of `book_admin_ui_requirements.md`, and `book_answer_key`'s module docstring, for 6-up / six per page / longest side / <=20 / grid-only / 5 mm. Red before the rewrite (listed every hit), green after.
- Plant P3: rule 12 given "6 per page while all are ≤20 on the longest side" -> red (3 hits). Plant P4: FR-042 statement given "never above 5 mm" -> red.
- FR-042: statement, AC-261..267, 270, 290, 293..295, EC-030, EC-031 restated to the 2x2 key. Refs: the seven naming the retired clueless key's tests (`compute_answer_page_layout` / `pack_answer_pages`, no production caller) swapped for six that test today's tiles and walk (the doc table test for AC-262/265/294; the packed-clues class for AC-267; the two small-answer-packing properties for AC-295/EC-030; two packed-layout classes for EC-031); each entrant found as a def/class by an independent `ast` index. trace.yml's FR-042 row likewise. `tests/test_check_ref_resolution.py` baselines re-derived: CENSUS 597->596, TRACE_TESTS 512->511, DEFINED 472->471 (7 out, 6 in each). Validator of record (forge_1): 0 errors, 105 -> 105 warnings, finding sets identical modulo line numbers (base measured in a temporary worktree of HEAD).
- Also amended to match (not named by AC-9, same stale rule): INV-011's statement (aggregates.yml), CAP-006's description, the 07 doc's INV-011 location row.
- `book_answer_key`: module docstring rewritten; `SIX_UP`, `SIX_UP_LONGEST_SIDE`, `page_capacity`, `pack_answer_pages`, `AnswerPage`, `needs_four_up` marked retired with the reason (no production caller; `src/` names them only there and in history notes), not deleted, because `tests/test_book_answer_key.py` and `tests/property/test_book_answer_key.py` still exercise them.
- `meta/profiling/rank_durations.py`: the new test file matches `RENDER_API_PATTERN` (it calls `puzzle_pages`), so it is added to `RENDER_HEAVY_SNAPSHOT` rather than dodged (`test_the_frozen_render_set_still_matches_the_grep_that_defines_it` red until then).

**IDEA-168, CARD-202's eight minors.**
1. `_packed_tile_layout` `Layout.margin` = tile's y-offset: LIVE, fixed to the page's top margin as `_slot_layout` does; held by an added assertion in `TestPackedSolvedLayout_EverySurvivingSlotActuallyFitsItsOwnTile::test_the_four_up_capacity_still_works_for_shallow_gutters` (plant: old line restored -> red, `501.5 <= 0.5`).
2. `interior_stream` docstring "no longer used to pack anything": LIVE (the phrase wraps a line, so a one-line grep misses it), fixed, with the method's "one full solved page per puzzle" lines and the generator module's answer-section heading.
3. `compute_packed_solved_layout` twice per page: DEAD as stated. The feasibility call is on the first answer page's spec, the draw call on each page's own parity; the second is a different (mirrored) layout, not a repeat.
4. Packed ink check `<0.5 mm` vs `<0.1 mm`: LIVE, fixed to `< 0.1`; `test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` passes (1 passed, 23.5 s).
5. Clue-agreement check in three places: LIVE, not fixed by design: `book_kdp._grid_extent`'s copy is the deliberate independent second signal `app.py`'s `_is_an_unpackable_row` relies on (its own docstring, G-6); one copy at `_payload` would remove that independence. Its stale "six-up" sentence fixed.
6. `test_book_pairing.py` oracle has no degrade model: LIVE, not fixed: a corpus that reached the degrade path would red there loudly (the oracle counts 4-per-run pages), not pass silently; modelling it needs an independent packed-cell fit, beyond this card.
7. Degrade ladder in the generator, not `plan_small_answer_pages`: LIVE, not fixed by design: moving it would give the pure, PageSpec-free planner a geometry dependency, against its module's ADR-0036/R2 split.
8. `_packed_column_left_mm` split at the pixel midpoint: DEAD as stated (gutter = outside = 0.5 in on BOOK1 now, so the midpoint is the gap centre, 2 mm each side), but the split now uses the tile model's gap centre anyway (same test as 4).

**Tests.** Base 10701 -> branch 10704 collected (`--collect-only -q -o addopts= tests/`): +3, the doc file. Gate (files named book/layout/answer/solved/packing/pdf, test_cli, test_kanban_review_record, test_check_ref_resolution, test_suite_profile, every test reading requirements.yml or docs/): 3 failed, 5100 passed, 1 skipped (setrlimit, platform), 1 xfailed. The reds: the known `test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place`, and two in test_suite_profile from the render set (fixed above; test_suite_profile + test_cli + doc + check-ref + packed layout rerun after: 626 passed). Every test file reading requirements.yml, trace.yml, aggregates or capabilities.yml rerun after the late yml edits: 2247 passed, 1 xfailed, 0 failed.

**Not done / for the board.** AC-1..AC-7's test names in this card (`TestSolutionTiles_*`) are defined nowhere; the behaviour is tested under CARD-202's `TestBookSolvedAnswerKey_*` names. AC-291 still says only a level's first answer page is headed and names a test no def/class defines; every answer page carries a running head today; left alone because re-pointing it moves the honest-dead class. The retired clueless tiling's tests (`tests/test_layout_answer_tiles.py` and kin) are now unreferenced by FR-042.

**Fix round 1 (review cycle 1, 8.5, one gating finding), commit ab26b336.**
- F-1 (gating): FR-042 AC-291 restated: 8 easy + 1 medium 15x15 give answer pages 1-4, 5-8, 9, each with a running head naming its own level. Checked with `plan_small_answer_pages` + `book_answer_vector.running_head_text`: `(1-4) SOLUTIONS · EASY`, `(5-8) SOLUTIONS · EASY`, `(9) SOLUTIONS · MEDIUM`; `packed_answer_page` calls `draw_running_head` on every packed page. `test:` unchanged; `tests/test_check_ref_resolution.py` has no diff in this round (`git diff --stat` empty). trace.yml does not mirror AC-291's text, so it is unchanged. FR-041's statement ("a small heading at the top of each level's first answer page") and BK-7 ("small level headings") were the same stale rule: one line each now names the running head. FR-041's closed open_question gets a dated addendum. Validator: 0 errors, 105 warnings, finding set identical to base (a first wording of AC-291's `then` drew one "bundles several outcomes" warning, reworded).
- F-2: `test_the_packing_doc_tables_are_what_the_planner_produces` also reads `interior_stream(...).answer_page_count` for a book of four 6x9 10x30 puzzles, at depth 12 (against `_solution_cell`) and at the deepest depth (against the doc's printed cell); both must be 2 pages. A search over the planner found 10x30 on 6x9 at depths 9-13 is where the two specs disagree (answer spec 2 pages, plain page spec 1). Plant: the reviewer's (`interior_stream`'s degrade pass given `self.page_spec(first_answer_page)`) -> `test_the_packing_doc_tables_are_what_the_planner_produces` FAILED (1 failed, 2 passed); restored.
- F-3: the RETIRED banner now names its members (`SIX_UP_LONGEST_SIDE`, `SIX_UP`, `Answer.needs_four_up`, `page_capacity`, `level_heading`, `AnswerPage`, `pack_answer_pages`) and the live ones. `level_heading` is added to the retired list because its only caller is `pack_answer_pages`: `book_pdf_generator` names it only in its module docstring.
- F-4: the doc's tile height is `(usable height - (rows - 1) x gap) / rows`, rows = capacity / 2. F-5: the CARD-485 paragraph names `TestBookPageNumbers_FolioNeverCollidesWithTheGrid`'s two tests. F-6: the margin comment says the spec's top margin (on an answer page, `answer_section_spec`'s, running-head strip included). F-7: a sentence under the puzzles table: it models a two-puzzle book; in a real book `_pair_cell_mm` caps a pair at its grid size's smallest book cell.
- Tests: collected 10704 (unchanged, +3 over base). Run (50 files: the doc test, check_ref, suite_profile, test_cli, packed_solved, page_numbers, every answer/solved file, every test reading requirements.yml/trace.yml/aggregates/capabilities/docs): 3213 passed, 1 xfailed, 0 failed, 0 skipped.
