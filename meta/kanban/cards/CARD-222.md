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
  (0.5 in), outside/top/bottom 0.95 cm (0.375 in)**, `band_mm=12.0`. **CON-018 no longer states
  those values:** it was amended on 2026-10-17 (commit `91609aa`) to the four margins below, so
  the shipped code is now the thing that disagrees with the registry and this card is what
  closes that gap. CON-018's KDP reasoning is unchanged and still explains the gutter (KDP needs
  0.375 in up to 150 pages and 0.5 in for 151-300, and Book 1 straddles 150).
- A titled page reserves `HEADER_BAND_MM = 12.0` (`export/layout.py:345`) above the drawing
  and draws **one centred caption** into it — `f"Puzzle {n}{BAND_SEPARATOR}{tier.label}"`
  (`book_pdf_generator.py:1150`). There is **no rule** under it.
- The folio is drawn by `_draw_folio` at `FOLIO_PT = 10.0`, centred at the foot. There is
  **no footer rule** and **no grid-size label** anywhere on a puzzle page (grepped: no
  size label exists today — the artifact's "20 x 25" is new).

**What changes.**

1. **Margins** become **gutter 0.5 in (unchanged), outer 0.5 in, top 0.55 in, bottom 0.47 in**,
   mirrored on left and right pages. Note the gutter: the artifact draws 0.75 in, and the owner
   decided on 2026-10-14 to keep KDP's required 0.5 in instead — see the measurement and the
   decision at the foot of this card, and take the figures from there, not from the artifact.
   **The CON-018 amendment this card flagged has LANDED** (2026-10-17, commit `91609aa`):
   CON-018 now reads outside 0.5 in (1.27 cm), top 0.55 in (1.397 cm), bottom 0.47 in
   (1.1938 cm), with its gutter clause deliberately untouched at 0.5 in. **Nothing is owed at
   the architect station** — read CON-018 as the spec for this card, and note that the registry
   already carries the measured consequence (usable width 193.675 → 190.500 mm, -1.64%; usable
   height 260.35 → 253.492 mm, -2.63%). This card still does not edit `meta/architecture/**`.
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
  built, *then* the gutter is **0.5 in (unchanged — owner's 2026-10-14 decision, not the
  artifact's 0.75 in)**, the outer margin 0.5 in, top 0.55 in and bottom 0.47 in, and the
  gutter/outer pair swaps between a left-hand and a right-hand page. The gutter and outer
  margin being equal is now deliberate, so the test must assert both and not one twice.
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

_Assembled 2026-10-17 by `system_rules.py --card CARD-222 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **CON-018 — the amendment this card flagged LANDED** on 2026-10-17 (commit `91609aa`):
  outside 0.375 → **0.5 in (1.27 cm)**, top → **0.55 in (1.397 cm)**, bottom → **0.47 in
  (1.1938 cm)**, and the **gutter clause deliberately untouched at 0.5 in** (the owner's
  2026-10-14 decision, which also keeps CON-018's own KDP reasoning intact). Measured
  consequence recorded in the entry: usable width 193.675 → 190.500 mm (-1.64%), usable height
  260.35 → 253.492 mm (-2.63%). **Nothing is owed at the architect station** — CON-018 now
  states exactly what this card builds, and the implementation agent should read it as the
  spec, not as the old profile.
- **Mirrored margins are now a geometric no-op on Book 1** (gutter == outside == 12.700 mm,
  CON-018 as amended 2026-10-17). FR-030's AC-272 and AC-273 now hold the same span
  (12.700..203.200 mm) and FR-032's AC-274/AC-275 the same left edge (25.45 mm), so on the
  default profile **a passing parity assertion about the usable area or a margin width is an
  identity, not evidence** that mirroring works. The mirroring rule (FR-030's last sentence,
  TERM-034) and EC-032's "gutter minus outside" formula stay true with a zero difference and
  still bite on any book storing **unequal** margins — the only configuration in which
  mirroring is actually under test. Owner decision 2026-10-17: record this, do not restore the
  asymmetry by changing a margin. An assertion about *which side* something sits on (left vs
  right by parity) still has teeth; one about *how wide* the margin is does not.
  For this card that lands on **AC-1**: the gutter/outer *swap* is unobservable on the default
  profile because the two values are equal, which is why AC-1 already requires asserting both
  margins by name rather than one twice. A test that wants to prove the swap needs a book
  storing unequal margins.
- **ADR-0036/R2** — the standing tension already logged in `backlog.md`: `page_frame` lives in
  `book_pdf_generator.py`, not in COMP-007. This card adds a region to that same place; say so
  in the notes rather than quietly widening the breach.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-032 (the puzzle page's placement — see CARD-224, which reverses CARD-204's
  placement; the amendment CARD-204 had logged against FR-032's "centred" clause was CANCELLED,
  not applied, on 2026-10-17), FR-043 (folios and the interior's pages).
- **CON:** **CON-018 (amended 2026-10-17, commit `91609aa` — outside 0.5 in, top 0.55 in,
  bottom 0.47 in, gutter unchanged at 0.5 in; nothing owed)**, CON-019, CON-020.
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
| **30x30** | **deep** | **4.84** | **4.60 — below NFR-008's floor (4.75 mm since the 2026-10-17 amendment; 4.8 mm when this was measured — 4.60 is under both)** |
| **30x12** | **deep** | **4.84** | **4.60 — below the floor** |

Small grids are unaffected because they are already at the cap. The cost falls entirely on the
large, deeply-clued puzzles — which are the hard ones, printed for the readers most likely to
mark cells by hand. A deeply-clued 30x30 sits just above the floor today and crosses it at the
artifact's four margins, which raises FR-031's below-floor flag. (Figures as measured on
2026-10-14; the floor itself moved to 4.75 mm on 2026-10-17 — see the correction at the foot of
this card.)

**This compounds with CARD-225.** Under a book-wide size per grid size, the deepest-clued
member decides for every puzzle of that size, so one deep 30x30 drags every 30x30 in the book
to 4.60 mm and raises the flag for all of them. The two cards are individually reasonable and
jointly push a whole grid size under the floor. **Surfaced to the owner as a decision before
either card starts.**

## Owner decision 2026-10-14 — the gutter stays at 0.5 in

Presented with the measurement above, the owner chose **outer 0.5 in, top 0.55 in, bottom
0.47 in as drawn, but the gutter unchanged at KDP's required 0.5 in** rather than the
artifact's 0.75 in. Re-measured against `_placed_cell_mm` with the shipped spec:

| | usable width | deep 30x30 cell | deep 25x25 | deep 20x20 |
|---|---|---|---|---|
| today | 193.68 mm | 4.84 mm | 5.87 | 7.45 |
| **shipped by this card** | **190.50 mm** | **4.76 mm** | **5.77** | **7.33** |
| artifact as drawn (0.75 in gutter) | 184.15 mm | 4.60 mm | 5.58 | 7.08 |

The cost falls from 4.9% to **1.6%**, uniformly, on every cell not already at the 7.5 mm cap.
Usable height goes 248.35 -> 241.49 mm.

**Stated as it was presented to the owner on 2026-10-14:** a deeply-clued 30x30 or 30x12 lands
at 4.76 mm, which was then 0.04 mm under NFR-008's 4.8 mm floor, so FR-031's below-floor flag
fired for that case. The owner accepted that with the reasoning that the gutter is where the
page curves anyway, so width spent there is the least useful width on the page.

**Corrected 2026-10-17 (registry delta, commit `91609aa`) — that case is no longer under the
floor.** NFR-008's floor moved to **4.75 mm**, chosen precisely so the margin change costs no
grid a clue-depth step, and the case above re-measures to **4.7625 mm** on the amended margins
with the repo's own `_placed_cell_mm` — **0.012 mm above the floor, so the flag does not fire
for it.** The registry states exactly this as AC-370, "where the retired 4.8 mm floor would
have refused it". The residue moves one depth step deeper and is still real: on the amended
margins a 30x30 falls under 4.75 mm from **clue depth 11 (4.6463 mm)**, depth 12 gives
4.5357 mm, and random 30x30 grids at density 0.5 reach **depth 13 (4.4302 mm)** (NFR-008's own
sweep, reproduced here with `_placed_cell_mm`). So CARD-225 must still handle a grid size whose
shared size is under the floor (its AC-6) — but the example that makes it non-hypothetical is
now a depth-11-or-deeper 30x30, **not** the depth-10 case tabled above. This correction
re-measured the geometry, not the corpus: re-measure the corpus before claiming either way.

**So CON-018's gutter clause is NOT amended** — only its outer, top and bottom values. That
also keeps CON-018's own KDP reasoning intact (0.375 in up to 150 pages, 0.5 in for 151-300,
and Book 1 straddles 150), which the 0.75 in gutter would have left stranded.
