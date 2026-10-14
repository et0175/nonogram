# CARD-222: Every interior page gets one frame — new margins, a header rule and a footer rule

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/222-interior-page-frame
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 (https://claude.ai/artifact/Wp4iGB27cyBAV62da5ACMP) — "The rules behind it": Margins, Header, Puzzle area, Footer
**Idea:** —
**Wave:** —
**Depends on:** CARD-221 (re-records the interior baselines and owns the same drawing code; racing it would make two cards re-record the same fixtures)
**Touches:** src/nonogram/admin/book_page_spec.py, src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_page_spec.py, tests/test_book_puzzle_frame.py, tests/test_book_page_numbers.py, tests/test_book_finalise_gutter.py, tests/fixtures/book_baseline_card222.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

This card is the **container** every other card cut from the owner's artifact sits inside.
It changes the page's margins and gives the page a header rule and a footer rule, so that
"the puzzle area" becomes a named region with a fixed top and a fixed bottom on every page.

**Current behaviour (verified by reading the code).**

- `book_page_spec.py:215` carries the Book 1 profile: trim 21.59 x 27.94 cm, **gutter 1.27 cm
  (0.5 in), outside/top/bottom 0.95 cm (0.375 in)**, `band_mm=12.0`. CON-018 states those
  values and its reasoning (KDP needs 0.375 in up to 150 pages and 0.5 in for 151-300, and
  Book 1 straddles 150).
- A titled page reserves `HEADER_BAND_MM = 12.0` (`export/layout.py:345`) above the drawing
  and draws **one centred caption** into it — `f"Puzzle {n}{BAND_SEPARATOR}{tier.label}"`
  (`book_pdf_generator.py:1150`). There is **no rule** under it.
- The folio is drawn by `_draw_folio` at `FOLIO_PT = 10.0`, centred at the foot. There is
  **no footer rule** and **no grid-size label** anywhere on a puzzle page (grepped: no
  size label exists today — the artifact's "20 x 25" is new).

**What changes.**

1. **Margins** become gutter 0.75 in, outer 0.5 in, top 0.55 in, bottom 0.47 in, mirrored
   on left and right pages. CON-018 states the current four values, so this is a
   **CON-018 amendment owed at the architect station** — this card does not edit
   `meta/architecture/**`; it flags the delta here, the shape CARD-198/202/205 used.
   Record the consequence rather than discovering it later: every margin grows, so the
   usable area shrinks, so **every fitted cell size can only get smaller** and the page
   count can move. Measure the corpus's page count before and after and state it.
2. **The header** runs the full text width: a 0.6 pt rule beneath it, at the **same
   baseline on every page**. The content of the header (what sits left and right of it) is
   CARD-207's; this card owns the rule and the baseline.
3. **The footer** gets a hairline rule, with the **grid size** (e.g. `20 x 25`) on the
   *inner* side and the folio centred at the bottom. The QR that goes in the footer's outer
   corner is CARD-223's; this card owns the rule, the size label and the folio's place in it.
4. **The puzzle area** is everything between the header rule and the footer rule, exposed as
   one region (a frame) so the grid's placement (CARD-224), the two-up split (CARD-226) and
   the openers (CARD-231) all measure against the same thing instead of each re-deriving it.
5. Keep the measured split: nothing here hardcodes a page count. `interior_page_count` and
   `book_kdp.unpaired_interior_page_count` must keep agreeing with what the export writes —
   CARD-205 left a three-caller cross-check in place, and the margin change moves what they
   measure.

## Acceptance criteria

- **AC-1** (happy, margins): *Given* a book with no stored margins, *when* its page spec is
  built, *then* the gutter is 0.75 in, the outer margin 0.5 in, top 0.55 in and bottom
  0.47 in, and the gutter/outer pair swaps between a left-hand and a right-hand page.
  (test: `TestBookPageSpec_CarriesTheNewProfileMargins`)
- **AC-2** (happy, the header rule): *Given* any puzzle page, *when* it is drawn, *then* a
  0.6 pt rule spans the full text width under the header, and its y is identical on every
  puzzle page of the book — measured off the drawn pixels, not off the constant.
  (test: `TestBookPageFrame_HeaderRuleIsOnTheSameBaselineEverywhere`)
- **AC-3** (happy, the footer): *Given* any puzzle page, *then* a hairline rule spans the
  text width, the grid size reads `W x H` on the inner side (left on a left-hand page, right
  on a right-hand one), and the folio is centred below it.
  (test: `TestBookPageFrame_FooterCarriesSizeAndFolio`)
- **AC-4** (guard, the area is one region): *Given* the puzzle area, *when* two different
  page kinds measure it, *then* both read the same top and bottom from the same function —
  asserted by calling it, not by comparing two literals.
  (test: `TestBookPageFrame_PuzzleAreaHasOneDefinition`)
- **AC-5** (edge, the type floor survives): *Given* the shrunken usable area, *when* every
  interior face is measured, *then* none falls below CON-020's 10 pt floor.
  (test: `TestInteriorType_EveryFaceHoldsTheFloor`, `tests/test_book_interior_type_floor.py:303`)
- **AC-6** (edge, the page count still agrees): *Given* the 150-puzzle corpus, *when* the
  interior is exported, *then* all three `measured_toc_page_count` callers and
  `unpaired_interior_page_count` agree with what was written, at the new margins.
  (test: `TestBookToc_KdpAgreesWithTheExportedCount`, `tests/test_book_toc.py:595`)
- **AC-7** (edge, the shortest trim): *Given* the shortest trim `book_page_spec` lays out at
  all, *when* a page is drawn at the new margins, *then* the header rule, the puzzle area and
  the footer rule all still fit and the folio still prints.
  (test: `TestBookPageFrame_ShortestTrimStillHoldsTheFrame`)

## Guardrails

- G-1: One source for each figure. The four margins, the two rule weights and the puzzle
  area's bounds are each declared once and read everywhere; a second literal of the same
  number anywhere in the diff is a defect (test: a grep-style structural test, as
  `tests/test_cli.py`'s import guard does it).
- G-2: CON-019 — CLI and web-UI exports stay byte-identical. They draw no book page, but
  prove it (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-3: INV-013 — the interior still holds no cover page and parity is still the 1-based
  interior position (test: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`).
- G-4: A book that stores its own margins still gets them. The profile is a default, not a
  rule — CON-018's last sentence (test: `TestBookPageSpec_StoredMarginsWin`).
- G-5: Baselines are re-recorded as deliberate recordings naming this card and the pages that
  moved; **no earlier fixture in the chain is regenerated or deleted**.
- G-6: Out of scope — what the header says (CARD-207), the QR's new home (CARD-223), where the
  grid sits in the area (CARD-224), the cell size rule (CARD-225).

## System contract

- CON-018 — the Book 1 profile this card amends (check: review-lens; the amendment is owed at
  the architect station)
- CON-020 — no reader-facing interior text below 10 pt except clue digits (check:
  `TestInteriorType_EveryFaceHoldsTheFloor`)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- INV-013 — no cover page in the interior; parity from the first interior page (check:
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
- ADR-0036/R2 — page geometry comes from COMP-007's layout functions (check: review-lens).
  Note the standing tension already logged in `backlog.md`: `page_frame` lives in
  `book_pdf_generator.py`, not in COMP-007. This card adds a region to that same place; say
  so in the notes rather than quietly widening the breach.

## Architecture context

- **FR:** FR-032 (the puzzle page's placement — see CARD-224, which reverses CARD-204's
  amendment of it), FR-043 (folios and the interior's pages).
- **CON:** **CON-018 (amendment owed: all four margins)**, CON-019, CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1 (a puzzle page's band carries number + tier only — the
  rule and the footer label are new furniture around it, so R1 needs re-reading at the
  architect station too).
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_page_spec.py`, `book_kdp.py`),
  COMP-007 (`export/layout.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- [Why this is the first card of the set] Every other card cut from the owner's artifact
  places something *inside* this frame. Cutting the frame first means the margin change is
  measured once, with one baseline re-recording, instead of each later card discovering that
  the page it is drawing on moved under it.

## Measured at the decompose station, 2026-10-14 — the margins cost 4.9% of every cell

Run against the repo's own `_placed_cell_mm` with the shipped Book 1 spec and the artifact's
four margins, so this is a measurement and not an estimate. Usable width goes 193.68 -> 184.15 mm
(-4.9%); usable height 248.35 -> 237.19 mm. The fit is width-bound for every grid the book
admits, so **every cell that is not already at the 7.5 mm cap loses exactly 4.9%**:

| grid | clue depth | today | at the new margins |
|------|-----------|-------|--------------------|
| 15x15 | any | 7.50 (capped) | 7.50 (capped) |
| 20x20 | shallow | 7.50 (capped) | 7.50 (capped) |
| 20x20 | deep | 7.45 | 7.08 |
| 25x25 | deep | 5.87 | 5.58 |
| 30x30 | shallow | 5.53 | 5.26 |
| **30x30** | **deep** | **4.84** | **4.60 — below NFR-008's 4.8 mm floor** |
| **30x12** | **deep** | **4.84** | **4.60 — below the floor** |

Small grids are unaffected because they are already at the cap. The cost falls entirely on the
large, deeply-clued puzzles — which are the hard ones, printed for the readers most likely to
mark cells by hand. A deeply-clued 30x30 sits 0.04 mm above the floor today and crosses it at
the new margins, which raises FR-031's below-floor flag.

**This compounds with CARD-225.** Under a book-wide size per grid size, the deepest-clued
member decides for every puzzle of that size, so one deep 30x30 drags every 30x30 in the book
to 4.60 mm and raises the flag for all of them. The two cards are individually reasonable and
jointly push a whole grid size under the floor. **Surfaced to the owner as a decision before
either card starts.**
