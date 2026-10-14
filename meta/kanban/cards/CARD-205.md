# CARD-205: The table of contents lists sections, not puzzles — How to Solve, each level with its puzzle range, Solutions

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/205-structural-toc
**Worktree:** ../PythonProject4-CARD-205
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (item 1: "PDF book - Table of contents - let's don't not have individual puzzles in ToC - only How-to-Solve, Easy-medium-hard divisors and Solutions"; restated later in the same doc under "Add table of contents" with the same sample)
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_toc.py, tests/test_book_finalise_gutter.py, tests/property/test_book_export_interior.py
**Review score:** —
**Started:** 2026-10-14T06:33:20Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `BookPDFGenerator.interior_stream` builds **one TOC row per drawable puzzle**
  (`book_pdf_generator.py:4531` — `toc_entries`), labelled through
  `answer_caption(number, answer_title(...))` ("37. Ice skate") against that
  puzzle's own `PuzzlePagePlan.page_number`. A 150-puzzle book therefore prints
  150 rows: at `TOC_ENTRY_PT = 10.0` + `TOC_ENTRY_GAP_PT = 4.0`
  (`book_pdf_generator.py:479`) that is several TOC pages, split by
  `measured_toc_page_count` / `_toc_entries_per_page` (`:2079`, `:2036`).
- `create_toc_page` (`:3067`) draws a page's slice: label left (clipped with an
  ellipsis when too wide), page number right-aligned, **no leader dots**, title
  `TOC_TITLE = "Table of Contents"` repeated on every TOC page, folio at the
  bottom.
- `book_kdp.unpaired_interior_page_count` (`book_kdp.py:484`) calls
  `measured_toc_page_count(len(ordered), ...)` — the TOC page count that feeds
  KDP's gutter table is **derived from the puzzle count**. Changing the entry
  rule without changing this line makes the gutter margin and the real book
  disagree.

**What changes.** The TOC becomes a fixed, structural list — one row per
section, never per puzzle:

```
CONTENTS

How to Solve Nonograms ................ 3

Easy
Puzzles 1–60 .......................... 5

Medium
Puzzles 61–120 ....................... 37

Hard
Puzzles 121–150 ...................... 69

Solutions ............................ 86
```

1. Build the entries from the page plan the walk already has, not from a second
   source of truth: the guide's own first page (`1` today, `GUIDE_PAGE_COUNT`
   pages), each non-empty level's **divider** page number and the
   first/last puzzle *numbers* in that level (both already in
   `SectionPlan.pages` — `DividerPagePlan.level` and the `PuzzlePagePlan.numbers`
   that follow it), and the first answer page (the SOLUTIONS divider, the same
   `first_answer_page` arithmetic `interior_stream` already does).
2. A level heading (`Easy` / `Medium` / `Hard`, from `Tier.label`, the same
   source `DividerPagePlan.text` uses) is a row of its own with **no page
   number**; the `Puzzles N–M` row underneath carries the number. A level with
   no printable puzzle gets neither row — the same "only when there are
   puzzles" guard the divider and the answer section already apply.
3. Leader dots fill the gap between label and number, drawn to the measured gap
   (the repeated-`.` run is sized from `entry_font.getlength(".")`, clipped to
   the available width, never overlapping either side). An entry whose label
   leaves no room for a single dot simply gets none.
4. The structural list is ~6 rows, so `measured_toc_page_count` is now called
   with the **entry count of the structural list** — in both callers: the
   generator and `book_kdp.unpaired_interior_page_count`. Keep the measured
   split (do not hardcode "the TOC is one page"): the same arithmetic still
   decides, it is simply fed a different count.
5. `answer_caption`/`answer_title` stop being read by the TOC path. They stay
   exactly as they are for the answer pages (AC-5 of CARD-200 was "no second
   independent title lookup"; this card removes the TOC's lookup entirely, which
   satisfies it trivially).

## Acceptance criteria

- **AC-1** (happy, structure): *Given* a book with easy, medium and hard
  puzzles, *when* its interior is exported, *then* the TOC pages hold exactly
  one `How to Solve Nonograms` row, one heading + one `Puzzles N–M` row per
  non-empty level, and one `Solutions` row — and **no row naming an individual
  puzzle**. (test: `TestBookToc_ListsSectionsNotPuzzles`)
- **AC-2** (happy, numbers): *Given* any such book, *when* the TOC is drawn,
  *then* every row's page number equals the interior position of the page it
  names — the guide's first page, that level's divider page, and the SOLUTIONS
  divider page — measured against the same `interior_stream` walk that drew
  them. (test: `TestBookToc_PageNumbersMatchTheWalk`)
- **AC-3** (happy, ranges): *Given* a book whose levels hold 60/60/30 puzzles,
  *when* the TOC is drawn, *then* the three range rows read `Puzzles 1–60`,
  `Puzzles 61–120`, `Puzzles 121–150`. (test:
  `TestBookToc_RangeRowsFollowTheLevelRuns`)
- **AC-4** (edge, one level): *Given* a book whose members are all easy, *when*
  the TOC is drawn, *then* it carries one level heading and one range row, and
  no empty heading for medium or hard. (test:
  `TestBookToc_SkipsEmptyLevels`)
- **AC-5** (edge, page count): *Given* a 150-puzzle book, *when* the interior is
  exported, *then* the TOC occupies one page, and
  `book_kdp.unpaired_interior_page_count` reports the same TOC page count the
  export actually wrote. (test: `TestBookToc_KdpAgreesWithTheExportedCount`)
- **AC-6** (edge, leaders): *Given* an entry whose label and number leave at
  least one dot of room, *when* the row is drawn, *then* the dots lie strictly
  between the label's right edge and the number's left edge, touching neither.
  (test: `TestBookToc_LeaderDotsStayInsideTheGap`)
- **AC-7** (edge, empty book): *Given* a book with no drawable puzzle, *when*
  the interior is exported, *then* no TOC page is produced (unchanged from
  CARD-200). (test: `TestBookToc_EmptyBookHasNoTocPage`)

## Guardrails

- G-1: Every TOC page keeps its folio, including the one-page case — the
  folio-sized reservation in `_toc_entries_per_page` is load-bearing, not a
  margin (test: `TestBookPageNumbers_EveryInteriorPageCarriesAFolio`).
- G-2: No new text-layout primitive — rows are set with `_guide_face`/`type_px`
  and `page_frame` like every other page (ADR-0036/R2).
- G-3: `answer_caption` / `answer_title` behaviour unchanged — the answer pages'
  captions are not touched by this card (test: `TestBookSolvedPage_Caption*`).
- G-4: Do not edit `src/nonogram/export/layout.py` — owned by CARD-204 (and no
  page geometry changes here: the TOC is text on an existing frame).
- G-5: Out of scope — no change to the TOC's title, type sizes, or its position
  after the guide page.

## System contract

(Projection of the lens over this card's `Touches:`; the lens's own glob scope
is far wider — `src/nonogram/**` — so only the rules that bear on this
mechanism are listed, mandatory first.)

- CON-020 — no reader-facing interior text below 10 pt except puzzle-page clue
  digits (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- INV-013 — the interior holds no cover page and starts at the guide page as
  right-hand page 1; parity is the 1-based interior position (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- INV-009 — a book's order is grouped by tier, which is what makes a level's
  puzzle numbers a contiguous range at all (check:
  `PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence`)
- ADR-0036/R2 — page geometry comes from COMP-007's layout functions; the admin
  panel does not place things itself (check: review-lens)
- ADR-0033/R1 — book assembly never changes a puzzle's grid, clues, tier or
  strategies (check: review-lens)

## Architecture context

- **FR:** FR-043 (page numbers + table of contents, the statement CARD-200
  implemented). This card amends the TOC half of it: FR-043's acceptance
  criteria describe a per-puzzle listing. The amendment belongs at the
  architect station — this card does not edit `meta/architecture/**` (kanban
  cards only read it) and flags the delta here, the same shape CARD-198/202
  used for FR-042/INV-011.
- **ADR:** ADR-0036/R2 (layout owns geometry), ADR-0037/R1 (a puzzle page's
  band carries number + tier only — unaffected, the TOC is a different page).
- **CON:** CON-020 (10 pt floor), CON-018 (Book 1 profile, the frame measured).
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- [Env] forge 2026.8.17 (project declares no `forge.min_version`; no `.skills.yml` here)
- [Dispatch] wave 37, started 2026-10-14T06:33:20Z. Unblocked by CARD-204's merge (`cd641df`), which
  owned the `book_pdf_generator.py` / `export/layout.py` hotspots this card also needs.
  **Branch from a main that already holds CARD-204**, so the right-aligned placement,
  the QR slot, the folio reserve and `caption_slot` are all present — do not
  reintroduce or work around any of them. CARD-206 is queued directly behind this card
  on the same hotspot.
- [Inherited context worth knowing] CARD-204 spent 8 fix cycles in these files and its
  retro lesson is recorded in `backlog.md`: `_draw_solved_slot`'s return value has two
  consumers (`solved_puzzle_page` and `_packed_answer_page`) that must be changed
  together, and nothing in the code enforces it. If this card touches anything with
  more than one consumer, say so explicitly in the notes.

- [Implementation complete] 2026-10-14 — committed `d236115` (8 files, +1691/-319,
  `meta/` clean). Full suite **6959 passed, 9 skipped, 0 failed, `PYTEST_EXIT=0`** on
  the committed tree (main was 6938/9/0; +21 is this card's net test change).
  **It found a THIRD `measured_toc_page_count` call site the card did not name:**
  `interior_page_count`'s own sheet-free `toc_pages` default, which also derived from
  the puzzle count and would have kept describing a listing the code no longer has.
  Both the named ones (the export path and `book_kdp`'s gutter figure) are fed from the
  same new `structural_toc_entry_count`. That is exactly the two-consumers trap this
  card was briefed on, and it turned out to be three.
  Page-count consequences: the 150-puzzle corpus goes **310 -> 307** pages (TOC 4 -> 1);
  the baseline book stays 13 pages with exactly one page's ink moving, recorded as a new
  `book_baseline_card205.json` with the attribution asserted the same way CARD-203's
  answer pages are. Eight `test_book_finalise_gutter.py` constants were re-measured
  against the live plan rather than nudged.
  **Two pre-existing tests became unsatisfiable as written** (the structural TOC is one
  page on every KDP trim — swept across 381 heights from 10 to 48 cm) and were repaired
  by restating what each was really about, not by relaxing them: the "never under-count"
  pair kept `>=` and gained a direct check that the frame still reads the book's own
  stored height, and the multi-page-TOC parity test was renamed to the insertion it
  actually tests.
- [Correction to my own card] **The card's step-1 recipe was subtly wrong and the agent
  caught it.** Taking a level's range from "the `PuzzlePagePlan.numbers` that follow its
  divider" breaks on a book with untiered rows: `print_order` ranks those after all
  three levels and `puzzle_section` opens them no divider, so their pages sit behind
  Hard's indistinguishably and would have widened Hard's printed range (`Puzzles
  121-150` for a hard run ending at 140). It used `_level_runs(payloads)` instead,
  cross-checked against the section's dividers. Also: four line references in the card
  had drifted post-CARD-204 (`toc_entries` :4531 -> :4862, `create_toc_page` :3067 ->
  :3232, `measured_toc_page_count` :2079 -> :2244, `_toc_entries_per_page` :2036 ->
  :2201); only `book_kdp.py:484` was still accurate.
- [Owner decisions 2026-10-14] Both questions the agent flagged rather than deciding:
  **(a) ADD the blank lines between groups** — your sample has them. To be implemented
  as a fixed extra gap before each group heading, NOT as blank entries, so the row count
  stays exactly eight and `_toc_entries_per_page` does not become a second layout
  primitive (G-2). **(b) KEEP "Table of Contents"** rather than the sample's
  "CONTENTS" — the sample was a sketch of structure, not typography, and G-5 put the
  title out of scope. No guardrail amendment needed.
- [For CARD-206, from the agent] Four places move when a title page becomes interior
  page 1, three of them the same term; and a warning worth keeping: the TOC's **length**
  is unaffected (it is a function of the level count alone), and `interior_stream`'s TOC
  tripwire re-measures the page COUNT, not the numbers — so it will NOT catch an offset
  applied to the plan and not to the entries. AC-2's
  `test_the_named_pages_really_are_those_pages` is the test that would; keep it green
  rather than retuning it. Also: INV-013 and `page_is_right_hand` both state interior
  page 1 is the guide and is right-hand, so a title page is an architecture-model change.
- [For the architect station] FR-043's TOC half is now amended by implementation (its
  ACs still describe the per-puzzle listing) — the same shape CARD-198/202 used for
  FR-042/INV-011, to fold into the pass that already owes FR-040/EC-027 and FR-032.
  Separately: `src/nonogram/admin/pdf_generator.py` (the legacy reportlab generator, not
  the book path, and reportlab is not in the dependency baseline) still builds a
  per-puzzle `_create_table_of_contents`, so the repo now holds two contradicting
  statements of what a book's TOC is.
- [Fix 1] 2026-10-14 — spawned for the owner's spacer-row decision, before review, so
  the reviewer judges the final shape rather than one the owner has already changed.

- [Notes sync 2026-10-14] agent notes pulled one-way from the worktree copy,
  verbatim:

  ### Implementation, 2026-10-14 (branch `card/205-structural-toc`)

  **Shape.** The TOC's entries became a named type and two pure functions in
  `book_pdf_generator.py`, with the drawing left where it was:

  - `TocEntry(label, page)` — frozen dataclass; `page is None` is a level
    heading (`is_heading`). Replaces CARD-200's `(label, page_number)` tuple
    precisely because this card introduces a row with no page number, and a
    bare `(str, Optional[int])` makes every reader decide for itself whether
    the second slot is a page or a sentinel.
  - `structural_toc_entry_count(level_count, puzzle_count)` — `2 + 2 * levels`,
    `0` for a book with no drawable puzzle. **The single source for the TOC's
    length.**
  - `structural_toc_entries(section, payloads, solutions_page)` — the rows
    themselves, built from the page plan.
  - `toc_range_label(first, last)` — `Puzzles 1–60`, and `Puzzle 7` in the
    singular (decision, see below).
  - `TOC_SOLUTIONS_LABEL = "Solutions"`, `TOC_RANGE_DASH = "–"`.
  - `create_toc_page` now takes `List[TocEntry]`, skips the number and the
    leaders for a heading row, and draws a dot run clipped to the measured gap.

  **Per-AC evidence** (all in `tests/test_book_toc.py`, 24 tests, green):

  | AC | Test class | What it proves |
  |----|------------|----------------|
  | AC-1 | `TestBookToc_ListsSectionsNotPuzzles` | exactly 8 rows for a 3-level book; no puzzle name, no `answer_caption` em dash, no `Puzzle N` label reaches a row; a custom title set on a member reaches no row either (the card's step 5); only headings carry no number |
  | AC-2 | `TestBookToc_PageNumbersMatchTheWalk` | guide row → 1; each range row → that level's `DividerPagePlan.page_number` off the same `SectionPlan`; solutions row → the SOLUTIONS divider. A second test replays the walk and checks the *kind* of page at each named position (guide / `divider:Easy` / `divider:SOLUTIONS`), not just that two numbers agree; a third pins the numbers to `1 + GUIDE_PAGE_COUNT + toc_page_count` so a hardcoded offset fails |
  | AC-3 | `TestBookToc_RangeRowsFollowTheLevelRuns` | 60/60/30 reads `Puzzles 1–60` / `61–120` / `121–150`; a second test *parses the printed labels back* and asserts the ranges tile 1..150 exactly once (an independent reading, not a rebuild of the same arithmetic); a third pins the singular form |
  | AC-4 | `TestBookToc_SkipsEmptyLevels` | all-easy book lists one level; the TOC's headings equal the book's divider pages exactly; **and** an untiered tail gets no row *and* is not swept into Hard's range (see "finding" below) |
  | AC-5 | `TestBookToc_KdpAgreesWithTheExportedCount` | 150-puzzle book writes exactly 1 TOC page; `measured_toc_page_count` still splits when fed enough rows (so "1 page" is a verdict, not a literal); `unpaired_interior_page_count(rows, book) == stream.unpaired_page_count`, with a non-vacuity assertion that the *pre-card* rule would have made this book's TOC 4 pages; and `kdp_page_band(estimate) == kdp_page_band(real)` |
  | AC-6 | `TestBookToc_LeaderDotsStayInsideTheGap` | measures the three drawn runs per row off `ImageDraw.text` and asserts `dot_left > label_right`, `dot_right < number_left`, with ≥ `TOC_ENTRY_GAP_PT` clearance; a heading draws no dots; and a **sweep** over 41 label lengths asserts the run is *maximal* — drawn iff one more dot would not fit — which neither a short run nor an overrun satisfies |
  | AC-7 | `TestBookToc_EmptyBookHasNoTocPage` | empty book, and a book whose only row cannot build a payload, both draw no TOC page and report `toc_page_count == 0`; an empty book's interior is the guide alone |

  **G-1** (folio on every TOC page, single-page case included):
  `tests/test_book_page_numbers.py`'s
  `TestBookPageNumbers_EveryInteriorPageCarriesAFolio` and
  `TestBookPageNumbers_ParityHoldsWithTheTocInserted` both pass unchanged in
  substance; `_toc_entries_per_page`'s folio reservation was not touched at
  all. **G-2**: no new text-layout primitive — the dot run is sized from
  `entry_font.getlength(".")`, the same font-metric measuring the clip loop
  already did, on the same `page_frame`. **G-3**: `answer_caption`/`answer_title`
  are untouched and are now read only by the answer-page loop;
  `tests/test_book_solved_page.py` + `tests/test_book_solved_answer_key.py`
  (299 tests in that group) pass unchanged. **G-4**: `export/layout.py` not
  edited. **G-5**: `TOC_TITLE` is still `"Table of Contents"` (the owner's
  sample heads the block `CONTENTS`, which G-5 puts out of scope — flagged for
  the owner, not changed), type sizes unchanged, position unchanged.

  ### `measured_toc_page_count` has THREE consumers, not two — all changed

  The brief named two. There is a third, and leaving it would have made
  `interior_page_count`'s documented "called with the count alone, this is an
  upper bound" contract describe a listing the code no longer has:

  1. `BookPDFGenerator.section_plan` (`book_pdf_generator.py`) — the real
     export. Now `measured_toc_page_count(structural_toc_entry_count(named
     level runs, len(payloads)), ...)`.
  2. `book_kdp.unpaired_interior_page_count` — the KDP gutter-band figure. Fed
     by the *same* `structural_toc_entry_count`, imported across the existing
     `book_kdp → book_pdf_generator` edge, with `dividers` (already computed
     there for `level_dividers`) as the level term.
  3. `interior_page_count`'s own sheet-free `toc_pages` default — was
     `measured_toc_page_count(puzzle_count, …)`; now
     `structural_toc_entry_count(min(len(TIERS), puzzle_count), puzzle_count)`,
     bounded by the same `min(len(TIERS), …)` its `level_dividers` default uses.

  AC-5's test is the direct cross-check of (1) against (2), written so it
  cannot pass vacuously.

  **The circularity, and the tripwire that closes it.** The entries need page
  numbers; the page numbers need the TOC's length; so the *count* has to be
  settled before the entries exist. It can be, because it depends only on the
  level runs, which are readable from the payloads alone — that is why
  `structural_toc_entry_count` is a separate function and not
  `len(structural_toc_entries(...))`. `interior_stream` then re-measures the
  rows it actually hands the drawing and raises if they need a different page
  count than the plan was laid out on. Without that, a divergence would
  mis-number the entire back half of the book and show up in **no** render.

  ### Finding: the card's step-1 recipe is subtly wrong for an untiered tail

  The card says to take each level's first/last puzzle numbers from "the
  `PuzzlePagePlan.numbers` that follow it". That rule breaks on a book holding
  rows with no readable tier: `print_order` ranks them *after* all three levels
  and `puzzle_section` opens them no divider, so their puzzle pages sit in
  `section` directly behind Hard's with nothing structural between them. "Every
  puzzle page until the next divider" would print `Puzzles 121–150` under Hard
  for a book whose hard run ends at 140 — a wrong range, in ink, that no test
  of the dividers themselves would catch.

  `structural_toc_entries` therefore takes the divider page numbers and their
  order from `section` (the real plan) and the number ranges from
  `_level_runs(payloads)` (the same cut `puzzle_section` planned the dividers
  from), and cross-checks the two readings against each other — same count,
  same levels, same order — raising `RuntimeError` rather than printing a
  mis-attributed range. Covered by
  `TestBookToc_SkipsEmptyLevels::test_a_run_with_no_readable_tier_gets_no_row_and_no_range`.

  ### Decisions taken (flagged, not silently made)

  - **`Puzzle 7` for a one-puzzle level**, not `Puzzles 7–7`. Not in the card;
    reasoning in `toc_range_label`'s docstring, pinned by a test.
  - **The dot run is corrected in both directions**, not only trimmed. The
    `run // dot_width` division is a first estimate; a face with a kerning pair
    for `".."` (or floating-point drift) makes the measured run differ from
    count × advance. Trimming alone — the obvious half — would silently drop a
    dot on a face with *negative* kerning, which is exactly the sort of thing
    that differs between Arial and `_guide_face`'s own fallback, i.e. between
    one machine's render and another's. AC-6's maximality sweep is what makes
    the omission visible rather than quiet. Neither loop fires on this
    machine's Arial: the baseline fixture's page-3 digest is byte-identical
    before and after this correction, verified directly.
  - **No blank spacer rows between groups.** The owner's sample has blank lines
    between the sections. They are not reproduced: AC-1 counts rows exactly, and
    a spacer would either be a counted `TocEntry` (breaking "exactly one heading
    + one range row per level") or variable row leading, which
    `_toc_entries_per_page`'s uniform-row division cannot model without becoming
    a second layout primitive (G-2/G-5). The heading row with no page number
    already reads as a group header — see the render below. **For the owner.**
  - **`TOC_TITLE` kept as "Table of Contents"** though the sample reads
    `CONTENTS` — G-5 puts the title out of scope. **For the owner.**
  - **`TOC_SOLUTIONS_LABEL = "Solutions"`**, not the divider's own all-caps
    `"SOLUTIONS"`: the divider's string is that page's display, the TOC row sits
    in a sentence-case list. Nothing reads the new constant to draw the divider.

  ### Page-count consequences observed

  - **The baseline book (4 puzzles) does not change length** — 13 pages, as
    before: its TOC already fitted one page. Only page 3's *ink* changes.
  - **The 150-puzzle corpus falls from 310 to 307 pages** (TOC 4 → 1).
    `tests/helpers/book_corpus.py`'s `CORPUS_TOC_PAGE_COUNT` 4 → 1.
  - The structural TOC is **one page on every trim KDP admits** — swept, 381
    heights from 10.00 to 48.00 cm, in
    `TestBookFinaliseGutter_UnpairedPageCountNeverUnderCountsTheToc::test_the_structural_toc_is_one_page_on_every_trim_kdp_admits`.
    That made two *pre-existing* tests unsatisfiable as written, and both were
    repaired by checking the thing they were really about rather than relaxed:
    - the F-2 "smaller trim must not under-count" pair kept its `>=`, and the
      strict `>` (unreachable now) was replaced by a **direct** check that
      `_toc_frame_for` still reads the book's own stored height — otherwise an
      equality could as easily mean the trim is being ignored again;
    - `test_parity_holds_on_a_larger_book_whose_toc_spans_more_than_one_page`
      was renamed `…_across_the_toc_insertion` and its precondition restated
      (`toc_page_count == 1`, the TOC still between guide and section, the book
      still > 120 pages).
  - `tests/test_book_finalise_gutter.py`'s scenario constants, all re-measured
    against the live page plan, never hand-arithmetic:
    `AC179_PAGES` 289 → 286, `AC271_PAGES` 280 → 277,
    `AC271_PAGES_BEFORE_THE_KEY` 130 → 127, `AC271_TOC_PAGES` 4 → 1,
    `AC199_NEW_BAND_PAGES` 409 → 405, `AC199_CARD198_PAGES` 492 → 487,
    `AC8_PAGES` 681 → 671, and the screen's `data-unpaired-page-count` 309 → 306.
    Every one stays in the same KDP band it was chosen for.
    `AC288_CORPUS`/`CK1_OVER_CORPUS` were **retuned** (39+43 → 41+41 medium
    pairs, 39+44 → 41+42) because the 150-page boundary is what CK-1 is *about*
    and CK-1's premise needs an odd paired-tier count; the same discipline
    CARD-198/CARD-200/CARD-201 each applied to this corpus.

  ### New baseline fixture: `tests/fixtures/book_baseline_card205.json`

  A new file under this card's own number, not a re-recording of CARD-204's —
  the chain's own rule. Measured, not assumed: a page-by-page digest comparison
  against CARD-204's recording finds **exactly one** differing page, 3 (the
  TOC). `interior_bytes` 3441912 → 3491813 (+49901: the leader-dot runs carry
  more high-frequency ink than four plain caption rows, so the page's JPEG grows
  even though it holds fewer words). `font_fingerprint` and
  `font_dependent_pages` unchanged; `MACHINE_FACE_SIZES` unchanged (no new type
  size). `BASELINE_FIXTURE` now points here.

  `tests/test_book_pdf_memory.py`'s
  `TestBookPdfMemory_NonDrawingPagesAreByteIdentical` claimed page 3 was
  byte-identical to CARD-200's recording — true until this card. Page 3 moved
  out of `STRICTLY_UNCHANGED_PAGES` into `CARD205_TOC_PAGE`, compared just as
  strictly against the CARD-205 fixture, **and** the attribution is itself
  asserted (`test_the_toc_page_moved_under_card205_not_card204`: CARD-200's and
  CARD-205's recordings of that page differ, CARD-204's still agrees with
  CARD-200's). This is the same treatment that class already gives CARD-203's
  three answer pages; the four dividers keep the CARD-200 comparison.

  ### `Touches:` vs what was actually touched

  - As listed and changed: `book_pdf_generator.py`, `book_kdp.py`,
    `tests/test_book_toc.py`, `tests/test_book_finalise_gutter.py`.
  - **Listed but needed no change:** `tests/property/test_book_export_interior.py`
    — it derives its expectations from `interior_page_count`/`SectionPlan`
    rather than from literals, so it passes unchanged. That is the property
    test earning its keep, not a gap in it.
  - **Not listed but necessarily changed**, each for a reason given above:
    `tests/helpers/book_corpus.py` (`BASELINE_FIXTURE`, `CORPUS_TOC_PAGE_COUNT`),
    `tests/test_book_page_numbers.py` (one precondition the structural TOC
    makes unreachable), `tests/test_book_pdf_memory.py` (page 3's baseline
    group), and the new `tests/fixtures/book_baseline_card205.json`.
  - The card's line references had drifted; recorded for the next reader:
    `toc_entries` given as `:4531`, actually `:4862`; `create_toc_page`
    `:3067`, actually `:3232`; `measured_toc_page_count` `:2079`, actually
    `:2244`; `_toc_entries_per_page` `:2036`, actually `:2201`.
    `book_kdp.py:484` was accurate.

  ### Visual check

  The TOC page was rendered on the Book 1 trim with the 150-puzzle corpus's own
  entries and eyeballed against the owner's sample. It reads:

  ```
  Table of Contents

  How to Solve Nonograms ......................................  1
  Easy
  Puzzles 1–50 ...............................................   4
  Medium
  Puzzles 51–100 .............................................  55
  Hard
  Puzzles 101–150 ............................................ 106
  Solutions .................................................. 157
  ```

  (Owner's sample reproduced except for the two deliberate deviations above:
  the heading `Table of Contents` rather than `CONTENTS`, and no blank line
  between groups.)

  ### For CARD-206 (blank title page as interior page 1)

  Everything you need to move is in **four** places, and three of them are the
  same number:

  1. `structural_toc_entries` hardcodes the guide's own first page as `1`
     ("INV-013: the guide is right-hand page 1"). With a title page inserted
     first, that becomes `1 + TITLE_PAGE_COUNT` — and it is a literal in that
     function, deliberately named in a comment so it is greppable.
  2. `BookPDFGenerator.section_plan`: `first_page = 1 + GUIDE_PAGE_COUNT +
     toc_page_count`.
  3. `interior_stream`: `first_answer_page = 1 + GUIDE_PAGE_COUNT +
     toc_page_count + len(section) + 1`, and the TOC pages' own numbers
     `GUIDE_PAGE_COUNT + 1 + index` in `produce()`.
  4. `interior_page_count`'s formula (`GUIDE_PAGE_COUNT + toc + dividers +
     pages + …`), which the page-plan tripwire checks `interior_stream`'s own
     make-up against — so forgetting it fails loudly instead of shipping.

  The TOC's own **length** does not depend on any of that (it is
  `structural_toc_entry_count`, a function of the level count alone), so a
  title page shifts every number by a constant and changes no row's text —
  but it *does* change `TocEntry.page` on every row, and
  `interior_stream`'s TOC tripwire re-measures the page count, not the numbers,
  so it will not catch an offset applied to the plan and not to the entries.
  AC-2's `test_the_named_pages_really_are_those_pages` is the test that would:
  it replays the walk and checks the kind of page at each named position, so a
  title page numbered into the plan but not into the TOC's rows makes it say
  "the Easy range row points at page N, which is a guide page". Keep it green
  rather than retuning its expectations.

  Also note `page_is_right_hand`/INV-013 both say "interior page 1 is the guide
  and is right-hand". A blank title page as page 1 makes the guide page 2 —
  INV-013's own wording is an architecture-model change, not just code.

  ### Flagged for the architect station (this card edits no `meta/architecture/**`)

  - **FR-043's TOC half is now amended by implementation.** Its acceptance
    criteria describe a per-puzzle listing; the shipped TOC lists sections. Same
    shape CARD-198/202 used for FR-042/INV-011.
  - `src/nonogram/admin/pdf_generator.py` (the legacy reportlab generator, not
    the book export path, and reportlab is not in the dependency baseline) still
    builds a per-puzzle `_create_table_of_contents`. Out of this card's scope
    and untouched, but it is now a second, contradicting statement of what a
    book's TOC is.

- [Fix 1 complete] 2026-10-14 — committed `906583d` (4 files, `meta/` clean, verified).
  `TOC_GROUP_GAP_PT = 10.0` declared beside `TOC_ENTRY_PT`/`TOC_ENTRY_GAP_PT` in the same
  point idiom (42 px at 300 dpi), added to the pen before a heading row and **suppressed
  for a page's first row**. The entries list, `TocEntry`, both entry functions and the
  row count are untouched, so every row is still one line of `TOC_ENTRY_PT` and
  `_toc_entries_per_page` stays a uniform division (G-2 clean). `TOC_TITLE` unchanged per
  the owner's second answer.
  **The number was measured, not chosen.** A full blank line (65 px) would leave 4 px
  under the last row on the shortest trim that lays out at all (10 cm), where the folio
  needs 49 — so `_draw_folio` would have silently omitted the page number, which is
  exactly guardrail G-1. Three 42 px gaps leave 73 px.
  **Capacity kept exact rather than made heading-dependent**, with overflow proved
  impossible instead of guarded against: the structural list is at most 8 rows and 3
  gaps, and the shortest laid-out trim holds 10 rows — verified for all 381 trim heights
  from 10.00 to 48.00 cm, each asserting both a folio line of headroom AND
  `measured_toc_page_count(8, frame, DPI) == 1`. The rejected alternative is recorded in
  `_toc_entries_per_page`'s own docstring: dividing by `entry_height + group_gap` would
  charge every row a gap only headings get (Book 1: 42 rows becomes 25) and would move
  the figure for all three callers to pay for a split that never happens.
  Teeth: the constant at `0.0` fails exactly the two new inequality tests; a mutant that
  also gaps the top of a page fails exactly the suppression test. Baseline re-recorded in
  place, `interior_bytes` 3491813 -> 3504840, with a page-by-page comparison confirming
  **exactly one page differs (page 3)** and the other twelve byte-identical.
  Targeted evidence: 29 + 17 + 45/1skip + 120 + 25 passed, and a 166-passed post-commit
  re-run. Full suite deliberately not run — the merge gate owns that now.
- [Open owner question, flagged not guessed] The sample also puts a blank line before
  **`Solutions`**, but the decision as given was "a gap before each group HEADING", and
  `Solutions` is a numbered row rather than a heading — so it now sits one ordinary line
  under the Hard range row and reads as part of the Hard group. Separating it needs
  either a flag on `TocEntry` (which the decision said to leave exactly as it is) or
  `create_toc_page` recognising the last row. Rendered evidence for the owner's eye:
  `~/Documents/nonogram-reviews/CARD-205/fix1-toc-page3-top.png`.
