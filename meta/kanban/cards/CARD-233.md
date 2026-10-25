# CARD-233: A solution tile gets one header — number, picture name, dots — and the page a running head

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/233-solution-tile-header
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The tile header carries the puzzle number, the picture's name and the difficulty dots. That replaces today's two labels, 'Puzzle 1 · Easy' above and 'Puzzle 1 — Candy' below. A running head says which puzzles the page covers, so readers can find an answer without the table of contents."
**Idea:** —
**Wave:** —
**Depends on:** CARD-232 (the tiles), CARD-228 (the dots)
**Touches:** src/nonogram/admin/book_answer_key.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_solved_page.py, tests/test_book_solved_answer_key.py, tests/test_book_answer_key.py, tests/fixtures/book_baseline_card233.json, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** An answer page carries **two** labels for
one puzzle: the band above (`Puzzle 1 · Easy`, from the same `f"Puzzle {n}{BAND_SEPARATOR}{tier.label}"`
the puzzle pages use) and the caption below (`Puzzle 1 — Candy`, built by
`answer_caption(number, answer_title(custom_title, puzzle_name))` in `book_answer_key.py:205,224`).
The owner's artifact calls that out as a redundancy.

**What changes.**

1. **One** tile header per solution: the puzzle number, the picture's name, and the difficulty
   dots (CARD-228). The band above and the caption below collapse into it.
2. **A running head** on each answer page saying which puzzles the page covers (`Puzzles 1-4`),
   so a reader can find an answer without the TOC.
3. `answer_title` keeps deciding the name (custom title, else the picture's name) — CARD-200's
   AC-5 was "no second independent title lookup", and this card must not introduce one. Read the
   name through `answer_title`, nothing else.
4. CARD-209's wide-but-short pages take the same tile header and running head — the owner's own
   note says those pages "use the same tile header and running head, so those pages look like
   part of the same set."

**Read before you start:** `caption_slot` exists because a 65-character picture name put ink
9.6 mm outside the page (CARD-204 Fix 7), and the fix for that then let a clamped caption
overprint the folio (CARD-204 cycle 5, 1 critical). A tile header is **narrower** than the old
full-width caption, so the clamping problem gets *harder*, not easier. The long-name case is
this card's main edge.

## Acceptance criteria

- **AC-1** (happy, one header): *Given* a solution tile, *then* it carries exactly one label
  block — number, name, dots — and no band above or caption below it.
  (test: `TestSolutionTileHeader_ReplacesBothOldLabels`)
- **AC-2** (guard, no second title lookup): *Given* a puzzle with a custom title, *then* the
  header's name comes from `answer_title` and nothing else reads the picture's name — asserted
  structurally. (test: `TestSolutionTileHeader_ReadsTheNameThroughAnswerTitle`)
- **AC-3** (happy, the running head): *Given* an answer page, *then* a running head names the
  puzzles the page covers, matching the numbers of the tiles actually on it.
  (test: `TestSolutionRunningHead_NamesThePagesOwnPuzzles`)
- **AC-4** (edge, a 65-character name): *Given* the longest picture name in the corpus, *then*
  the header stays inside its tile, does not overprint the dots, the grid, the running head or
  the folio, and is clipped or wrapped by one stated rule.
  (test: `TestSolutionTileHeader_LongNameStaysInItsTile`)
- **AC-5** (edge, no name at all): *Given* a puzzle with neither a custom title nor a readable
  picture name, *then* the header carries number and dots only, with no empty separator left
  behind. (test: `TestSolutionTileHeader_NamelessPuzzle`)
- **AC-6** (edge, an untiered puzzle): *Given* a puzzle whose tier cannot be read, *then* the
  header draws no dots (CARD-228's AC-6) and the rest of the header is unchanged.
  (test: `TestSolutionTileHeader_UntieredDrawsNoDots`)
- **AC-7** (guard, CARD-209's pages too): *Given* the wide-but-short page, *then* it carries the
  same tile header and the same running head. (test: CARD-209's classes, extended)

## Guardrails

- G-1: FR-033's "titles only in the answer key" still holds — the puzzle pages do not gain a
  name (test: the existing FR-033 tests).
- G-2: `caption_slot`'s bound is not removed; if the header replaces the caption, the slot's
  guarantee moves with it and is re-proved at the 65-character case (AC-4).
- G-3: Every answer page keeps its folio, and the running head does not collide with it (test:
  `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-4: CON-020's floor holds for the header, the name and the running head (test:
  `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-5: Out of scope — the tiles themselves (CARD-232), the dots glyph (CARD-228).
- G-6: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

- FR-042 — the answer key's pages (check: the answer-key tests)
- FR-033 — titles only in the answer key (check: the FR-033 tests)
- CON-020 (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0033/R1 — nothing about the puzzle changes (check: review-lens)
- ADR-0036/R2 (check: review-lens)

## Architecture context

- **FR:** FR-042, FR-033. CARD-200's AC-5 ("no second independent title lookup") is the
  constraint AC-2 restates.
- **CON:** CON-020.
- **ADR:** ADR-0033/R1, ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Why the long name is the whole card] Two of CARD-204's eight fix cycles and its only
  CRITICAL finding were about a long picture name's caption: first ink 9.6 mm outside the page,
  then a clamped caption inside the folio's glyph box. This card moves that same string into a
  narrower box. Write AC-4 first.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** the design implemented on a raster interior, with its acceptance criteria
verified by measuring ink on a rendered bitmap.

**Should be:** the same design, unchanged — **the card's instrument moves, not its
decision**. CARD-293 §6 classifies this card as *written, tests retargeted*: a solution tile's single header — page composition and type.

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

