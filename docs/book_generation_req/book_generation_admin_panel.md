# Requirements for Book 1 (from book-format-research)

*Source: [docs/research/book-format-research.md](../research/book-format-research.md) (2026-09-15). This document turns its Book 1 recommendation into requirements the admin panel's book pipeline (Steps 1–4) must meet.*

Book 1: 8.5×11 in (or 8×10), 100–150 puzzles, one per page, ~120–190 pages, $9.99–12.99, with a theme rather than a generic title.

## 1. Book 1 profile

| Parameter | Value | Why |
|---|---|---|
| Trim | **8.5 × 11 in** (21.59 × 27.94 cm) — the admin panel's default since migration 008 | Dominant trim in the Amazon top 30; the only one that prints 25×25–30×30 at a usable cell (research §2, §4) |
| KDP margins | Gutter **0.5 in** (1.27 cm), outside / top / bottom **0.375 in** (0.95 cm), no bleed | KDP requires 0.375 in gutter up to 150 pages and 0.5 in for 151–300; Book 1 straddles 150, so the gutter is fixed at 0.5 in and never moves the cell size. 0.375 in outside leaves room for trim variance above KDP's 0.25 in minimum |
| Usable page | **193.7 mm wide × 260 mm tall**; **248 mm** for the puzzle once a 12 mm title band is reserved | Trim minus the margins above |
| Puzzles | 100–150, **one per page**; two small puzzles share a page where they fit (BK-6) | Research §3, §8 |
| Solutions | Answer section after the puzzles: up to **6 per page** while every answer on the page is ≤20 on the longest side, **4 per page** once one is bigger (BK-8) | Keeps the book at ~120–130 pages (research §3 assumed 6 per page) |
| Pages | ~120–190 | Cover, guide, puzzles, solutions |
| Price | $9.99–12.99 | 60% royalty tier starts at $9.99 (research §3) |
| Title | Themed, not generic | Themed books chart (research §4) |
| Difficulty labels | Easy / Medium / Hard **from the solver's tier**, never from grid size | Reviews punish wrong labels (research §5) |

## 2. Size × difficulty matrix with shorter side and printed cell size

The research matrix buckets puzzles by **longest side** only. Width is the tight axis of a portrait page, so a 30-tall × 15-wide grid prints a far larger cell than a 30×30. Each longest-side row is therefore split by **shorter side**; the difficulty shares stay at the longest-side level (they are the research values, unchanged) and the sub-rows add the printed cell size.

Cell size is the page-fit value on the 8.5×11 trim with the margins in §1, at the top of each bucket (worst case), held under a **standard cell of 7.5 mm**: the drawing is ≈ 1.3 × N cells across (the clue band is ~30% of the side), so

```
cell = min( 7.5 mm,  193.7 mm / (1.3 × shorter side),  248 mm / (1.3 × longest side) )
```

| Longest side | Share (E / M / H, % of book) | Shorter side | Cell (mm) | Fit |
|---|---|---|---|---|
| ≤15 | 10 / 5 / – | ≤15 | 7.5 | ✅ cap |
| 16–20 | 15 / 20 / 5 | ≤15 | 7.5 | ✅ cap |
| | | 16–20 | 7.4 | ✅ |
| 21–25 | 5 / 15 / 10 | ≤15 | 7.5 | ✅ cap |
| | | 16–20 | 7.4 | ✅ |
| | | 21–25 | 6.0 | ✅ |
| 26–30 | – / 5 / 10 | ≤15 | 6.4 | ✅ |
| | | 16–20 | 6.4 | ✅ |
| | | 21–25 | 6.0 | ✅ |
| | | 26–30 | 5.0 | ⚠️ near floor |

Totals by difficulty: 30% easy / 45% medium / 25% hard. Totals by longest side: 15 / 40 / 30 / 15.

Notes:

- **Standard cell: 7.5 mm** (owner's decision). Page fit alone would print a 15×15 at 9.9 mm — large-print territory, and a jump from 9.9 to 7.4 between consecutive pages reads as inconsistent. With the cap, every puzzle up to 25 long and 20 wide prints at the same ~7.4–7.5 mm (about 70% of the book); only the 21–25-wide, the 26–30-long and the 30×30 puzzles step down (6.0 / 6.4 / 5.0).
- **Empty space.** The cap leaves white around small and narrow puzzles: a 15×15 draws 146 × 146 mm on the 194 × 248 mm usable page (~44%), and a 30-tall × 15-wide grid at 6.4 mm draws a 125 × 250 mm strip with ~35 mm of white each side. The puzzle's top edge sits at the same position on every page rather than being centred, so the book reads consistently. Small puzzles share a page where two fit (BK-6), which removes most of the empty space on the ≤15 pages. A frame or decoration around the page is a later decision.
- **Floor: 4.8 mm** (owner's decision: 4.8–4.9 is fine, 4.6 is too small). Standard squared paper is 5 mm.
- **Height binds for tall grids.** Any 26–30-tall puzzle up to 20 wide prints at 6.4 mm whatever its width; making it narrower buys nothing, making it wider than 20 starts to cost.
- **26–30 × 26–30 is only 0.2 mm above the floor.** The 1.3× model assumes a ~9-entry row-clue band. A 30-wide puzzle with a 9-entry band draws 39 cells across → 4.97 mm ✅; with a 12-entry band it draws 42 → 4.61 mm ❌. The floor must therefore be checked **per puzzle on its real clue depth**, not per bucket (BK-1, BK-2).
- **Widest grid at the 4.8 mm floor: 31 cells** with these margins (31 → 4.81 mm, 32 → 4.66 mm); 32 cells at KDP's bare minimum margins (0.25 in outside, 0.375 in gutter → 200 mm usable). Height would allow ~39, but `src/nonogram/limits.py` stops every grid at 30 either way.
- The CLI layout has its own cap curve (9.0 mm at ≤10 cells down to 6.5 at 30); the book uses the flat 7.5 mm above instead, and the book's cap wins inside the book.
- For comparison, the renderer today sizes cells for **A4** with 12 mm margins (186 mm usable): a 30×30 gets 4.77 mm there — below the floor — which is why the trim-aware computation in BK-1 matters.

## 3. Print-fit requirements for the admin panel

- **BK-1 Trim-aware cell size.** The book PDF computes each puzzle's cell for the **book's trim and margins**, not A4: usable width = trim width − outside margin − gutter margin; usable height = trim height − top − bottom − title band. Margins are read from the book's `gutter_margin_cm` / `outside_margin_cm` (Book 1 defaults 1.27 / 0.95 cm), with KDP's page-count minimum as a lower bound: the book always lays out with its stored gutter, and finalise refuses if the actual page count needs a larger one. The clue gutters are the puzzle's **real** clue depth (`max(len(clue))` per axis, as `export/layout.py`'s `_gutter_depth` measures it), not the 1.3× estimate. The result is capped at the **7.5 mm standard cell**, and the puzzle's top edge is placed at the same position on every page. Margins are **mirrored**: the gutter margin is on the left of right-hand (odd) pages and on the right of left-hand (even) pages, and the drawing is centred across the usable width.
- **BK-2 Cell floor 4.8 mm.** A puzzle whose cell would print below 4.8 mm on the book's trim is flagged in puzzle selection (Step 2) with its computed cell size, and cannot be added to Book 1 without an explicit override. The book summary (Step 4) lists how many puzzles sit below the floor.
- **BK-3 Pictures print upright.** The page is always portrait and a puzzle is never turned: a turned picture is harder to recognise. A wide grid simply prints at the cell its width allows (20 wide → 7.45 mm, 25 wide → 6.0 mm, 30 wide → ~5.0 mm) and is covered by the floor check (BK-2); there is no separate "wide grid" flag.
- **BK-4 Target vs actual mix.** Puzzle selection shows the matrix in §2 as target vs actual (count and % per longest-side × difficulty cell, plus the shorter-side breakdown). A book can be marked ready only when every cell is within ±3 percentage points of its target.
- **BK-5 Print quality** (from the reviews, research §5): pure black grid lines, thin rule at least **0.25 mm**, every 5th line **twice** as heavy (book only; today's code prints 0.17 mm on cells under ~6.4 mm), confirmed on printed proof pages (one 30×30, one 15×15) before a book is finalised; picture titles only in the answer key, never on the puzzle page — the band above a puzzle shows **"Puzzle N · Tier"** (e.g. "Puzzle 12 · Easy"); every puzzle has exactly one solution, and the book description says so; no guess-tier puzzles.
- **BK-6 Two small puzzles per page.** Two puzzles share a page when both fit at one shared cell of at least **7.0 mm** (each with its own band): the pair's combined drawing height — grid rows plus column-clue rows of both — times the cell, plus two 12 mm bands, fits the 260 mm usable height. In practice: 10 + 10 tall at 7.5 mm, 12 + 12 at 7.4 mm, 15 + 10 at 7.0 mm; 15 + 12 and 15 + 15 do not pair. Only puzzles of the same tier that are next to each other in the book order are paired, so numbering stays in sequence. Roughly 27 small puzzles fit on ~14 pages instead of 27.
- **BK-8 Answer key.** Answers show the filled grid only (no clues), in puzzle-number order, each captioned "Puzzle N — Title" (the only place the picture's title appears). A page holds up to **6** answers (2 × 3) while every answer on it is ≤20 on the longest side, and becomes a **4**-answer page (2 × 2) as soon as it would hold one bigger than 20. That keeps every answer cell at about 3 mm or more (20 cells in a 6-up tile → 3.7 mm; 30 cells in a 4-up tile → 3.1 mm). For the default plan (90 puzzles ≤20, 60 bigger) the answer key is about 30 pages instead of 150 at one per page.
- **BK-7 Ordered by difficulty.** The book runs easy → medium → hard, with a short divider page before each level ("Easy", "Medium", "Hard"), so a "beginner to expert" book shows its progression. A puzzle added later goes to the end of its level; the answer key keeps puzzle-number order with small level headings (no divider pages); a book arranged before this rule prints grouped by level, keeping its order within each level.

## 4. Gap against the current implementation

| Needed by | Today | Gap |
|---|---|---|
| BK-1 | `admin/book_pdf_generator.py` hard-codes 8.5×11 pages at 300 DPI, but every puzzle page comes from `render_pages()` → `export/layout.py`, which sizes the cell for **A4** (210×297 mm, 12 mm margins). `trim_width_cm` / `trim_height_cm` are passed in as "informational, for metadata" and ignored; the margin columns from migration 004 are not read at all | Layout must take the page size and margins from the book, or the book generator must own its own page-fit computation |
| BK-2 | No cell-size check anywhere in the book flow; `layout.py`'s floor is 2 mm and is a backstop, not a print rule | Per-puzzle cell computation and a 4.8 mm flag in Step 2 and the Step 4 summary |
| BK-3 | `layout.py` turns the *sheet* (landscape) when that prints a larger cell — fine for a loose A4 printout, wrong inside a bound portrait book | Portrait only in the book; pictures never turned |
| BK-4 | Step 2 has a selection counter and difficulty filter, no target matrix | Matrix view with target vs actual and the ±3 pp readiness check |
| BK-5 | Every-5th bold rule exists in `layout.py` (proportional, 0.17 mm thin under ~6.4 mm); titles are drawn on the puzzle page by the PDF header band | Book stroke minimum; band shows "Puzzle N · Tier"; title only in the answer key |
| BK-6 | One puzzle per page, always | Pairing of small puzzles and a two-slot page |
| BK-7 | Arrangement order is free; no divider pages | Difficulty order and divider pages |
| BK-8 | One full answer page per puzzle (`book_pdf_generator.py`) — a 150-puzzle book passes 300 pages | 6-up / 4-up answer pages by size |
| BK-1 placement | Same margins on every page | Mirrored margins (gutter on the binding side), drawing centred |

This table is the scope of a follow-up kanban card; nothing in it is delivered by this document.

## 5. Out of scope for Book 1

- Solution hints (e.g. "Hint for 12: row 7 has cells 4–11 filled", from the solver's first line-logic deductions): a future feature, not Book 1.

- Grids above 30×30 (35×35–50×50): challenge book only, after the engineering steps in research §7.
- Three or more puzzles per page (e.g. 2–4 small ones as in the research's big-book plan, §8): later big book only; Book 1 pairs at most two (BK-6).
- Color nonograms: separate product line.
- 6×9 / A5 pocket edition.
