# Nonogram book format research

*Date: 2026-09-15 · Market: Amazon.com, KDP paperback, black-and-white interior · [Ukrainian version](book-format-research.uk.md)*

The owner's working assumptions going in:

- **Format:** close to A5 or US Letter, maybe smaller. The owner had also heard that big books (about A4, 200+ puzzles) sell well.
- **Size mix:** four buckets by cell count:
  - small, 100–200 cells: 15%
  - 201–400 cells: 35%
  - 401–625 cells: 35%
  - big, 600–900 cells: 15%
- **Difficulty mix:** 70% easy, 20% medium, 10% hard.

This document checks each assumption against printing costs, page geometry, and a snapshot of the 30 best-selling nonogram books on Amazon.com.

## 1. Summary

| Question | Assumption | Finding |
|---|---|---|
| Format | A5 / Letter; big A4 books sell | **8.5×11 in or 8×10 in.** A5 doesn't appear among the top 30 and can't fit 25×25+ grids. Big books sell, but don't dominate. |
| Book size | 200+ puzzles | **100–150 puzzles, ~120–190 pages, $9.99–12.99** for a first book |
| Size mix | 15 / 35 / 35 / 15 by cell count | Buckets overlap; bucket by **longest side** instead. A 30×30 cap is small for experienced solvers. |
| Difficulty | 70 / 20 / 10 | Only makes sense for a book labelled "beginner". For a mixed book: ~30 / 45 / 25, or a series of single-level books. |
| Very large grids (40×40–50×50) | Worth offering? | **Yes, but not in Book 1.** Challenge books advertise them and they show off image-based pictures, but cells drop to ~3–3.7 mm and the generator stops at 30×30 today (section 7). |
| Easy puzzles in big books | Maybe not needed | **Yes, about 25%.** Reviewers of big books asked for *more* easy puzzles. What they punish is wrong difficulty labels, guessing, multiple solutions and poor print quality (section 5). |

The admin panel's default book trim changed from 6×9 in to **8.5×11 in** as a result. (The old default was 15.24 × 22.86 cm, which is 6×9 in, not A5.)

## 2. Format: what fits on the page

A nonogram needs room for the grid plus its clues. For picture puzzles the clue band is roughly 30% of the grid side, so the drawing is about **1.3 × N cells** across. Width runs out first. Cell width after margins:

| Grid | A5 / 6×9 (~125 mm usable) | 8×10 in (~178 mm) | 8.5×11 in (~190 mm) |
|---|---|---|---|
| 15×15 | 6.3 mm ✅ | 9.0 mm | 9.7 mm |
| 20×20 | 4.7 mm ⚠️ | 6.8 mm ✅ | 7.3 mm ✅ |
| 25×25 | 3.8 mm ❌ | 5.5 mm ✅ | 5.8 mm ✅ |
| 30×30 | 3.2 mm ❌ | 4.6 mm ⚠️ | 4.9 mm ⚠️ |

Standard squared paper uses 5 mm cells, about the smallest you can comfortably write in with a pencil. **Any size mix where half the puzzles are 20×20 or larger rules out A5 and 6×9.** Format and size mix are one decision.

## 3. Cost and profit (KDP US, black-and-white, 2026)

- **Regular trim** (≤ 6.12 in wide and ≤ 9 in tall): $2.30 flat for 24–110 pages; $1.00 + $0.012/page above that.
- **Large trim** (e.g. 8×10, 8.5×11): $2.84 flat for 24–110 pages; $1.00 + $0.017/page above that.
- **Royalty:** 60% of list price at **$9.99 and above**, 50% at $9.98 and below. Royalty = rate × price − print cost.

| Book | Pages | Print cost | Price | Royalty per sale |
|---|---|---|---|---|
| 6×9, 100 puzzles up to 15×15 | ~124 | $2.49 | $9.99 | $3.50 |
| **8.5×11, 120 puzzles** | ~146 | $3.48 | $12.99 | **$4.31** |
| 8.5×11, 250 puzzles, 1 per page | ~300 | $6.10 | $14.99 | $2.89 |
| 8.5×11, 250 puzzles, small ones 2 per page | ~225 | $4.83 | $14.99 | $4.16 |

(Page counts assume solutions at 6 per page plus a few front pages.)

A 200+ puzzle book doesn't earn more per sale unless you raise the price. It needs twice as many good pictures, and pictures are the real bottleneck, not generation.

## 4. Market snapshot: top 30 nonogram books on Amazon.com

**Method.** 8 searches in Amazon Books, first 2 result pages each: "nonogram puzzle book", "nonograms", "griddlers book", "hanjie puzzle book", "picross puzzle book", "nonogram large print", "nonogram book hard", "nonogram book easy". That gave 170 results; 149 were nonogram titles, and 138 of those had a Best Sellers Rank (BSR; lower = more sales). Sorted by BSR, top 30 kept.

**Caveats.**
- BSR is a single-day snapshot, and new books get a short launch spike (#1 has 1 rating).
- Puzzle counts and grid sizes are parsed from product descriptions and may be incomplete.
- Prices may include temporary discounts.
- #14 is a mixed Christmas puzzle book that slipped into the list.
- Books none of the 8 searches returned are missing.

### Aggregates

| | Finding |
|---|---|
| Niche size | Small. #1 ranks ~#47,000 in Books and #30 ~#495,000. Very roughly, 5–10 sales/day at the top and one every few days at #30. |
| Trim (top 30) | 8.5×11: 12 · 8×10: 7 · 6×9 or smaller: 7 · 7×10: 2 · 7.5×8.7: 2 · **A5: 0** |
| Trim (all 138) | 8.5×11: 65 · 8×10: 45 · 6×9 or smaller: 15 · 7×10: 10 · other: 3 |
| Pages | median 120 (range 46–316) |
| Puzzles per book | mostly 80–150; four books have 300–450 |
| Price | mostly $9.99–12.99; big books $15.99–29.99 |
| Reviews | median 25 ratings, so newcomers can compete |
| Color nonograms | 5–6 of the top 30 |
| No sales rank at all | 11 books, mostly 2026 "large print" launches |

### Top 30 table

| # | BSR | Trim (in) | Pages | Price | Ratings | Puzzles | Grid sizes / levels (from description) | Title |
|---|---|---|---|---|---|---|---|---|
| 1 | 47,022 | 6×9 | 154 | $14.99 | 1 | – | master | Murdograms Crime Scene Investigation: Murder Mystery Nonogram Puzzles |
| 2 | 65,299 | 6×9 | 151 | $11.99 | 15 | 225 | 10×10–35×35; beginner–hard | Nonogram Puzzle Book (Travel-Size) |
| 3 | 138,054 | 7×10 | 110 | $9.99 | 30 | 88 | 5×5–25×30; easy–hard | Nonograms for Everyone: 88 Nonogram Logic Puzzles |
| 4 | 142,734 | 8×10 | 316 | $29.99 | 290 | 406 | 10×15–30×40; intermediate, challenging | The Big Book of Picross Hanjie Griddlers Nonograms: 4 volumes in 1 |
| 5 | 151,778 | 8.5×11 | 85 | $5.99 | 88 | 80 | 20×20–50×50; easy–hard | Nonogram Puzzle Book: Easy To Hard, From 20x20 to 50x50 Grids |
| 6 | 165,993 | 8.5×11 | 91 | $10.99 | 25 | 150 | beginner–master | Nonogram Puzzle Book: From Beginner to Master With 150+ Puzzles |
| 7 | 193,600 | 8.5×11 | 219 | $13.99 | 0 | 320 | expert · **color** | Color Nonogram Puzzle Book: 320 Picture Logic Puzzles |
| 8 | 230,659 | 8.5×11 | 282 | $19.99 | 56 | 400 | easy, challenging | Nonogram Puzzle Book: 400 Challenging Puzzles |
| 9 | 232,584 | 8.5×11 | 191 | $15.99 | 32 | 300 | beginner–master | Nonogram Puzzle Book: From Beginner to Master With 300+ Nonograms |
| 10 | 236,581 | 7.5×8.7 | 128 | $8.99 | 6 | 100 | easy–difficult · **color** | Picture Cross Around the World: 100+ Nonogram Logic Coloring Puzzles |
| 11 | 246,778 | 6×9 | 116 | $10.00 | 159 | 100 | from 5×5; beginner | 100 Nonogram Puzzles for Beginners |
| 12 | 275,945 | 8.5×11 | 141 | $11.99 | 5 | 100 | 20×20–30×30; easy, medium; large print | Nonogram Puzzle Book for Adults and Seniors: 100 Large Print |
| 13 | 278,624 | 8.5×11 | 194 | $9.99 | 0 | 150 | up to 50×50; expert | Nonograms Challenge: Animals: 150 Expert Puzzles |
| 14 | 294,315 | 5.75×7.5 | 128 | $7.99 | 4 | 100 | mixed puzzle types | Christmas Puzzles – Holly Jolly Mixed Puzzles |
| 15 | 326,814 | 8×10 | 46 | $10.00 | 55 | – | advanced | Griddlers Logic Puzzles Advanced Vol. 1 |
| 16 | 340,842 | 8×10 | 94 | $12.99 | 1 | 100 | 10×10–35×45; easy · **color** | Nonograms Multicolor vol. 1 |
| 17 | 355,861 | 8.5×11 | 120 | $9.99 | 6 | 200 | 5×5–20×20; easy | 200 Easy Nonogram Puzzle Book For Beginners |
| 18 | 400,194 | 8.5×11 | 311 | $19.99 | 65 | 450 | beginner–master | Nonogram Puzzle Book: From Beginner to Master With 450+ Puzzles |
| 19 | 400,606 | 7.5×8.7 | 128 | $8.99 | 9 | 100 | easy–difficult · **color** | Picture Cross Cats & Dogs: 100+ Nonogram Logic Coloring Puzzles |
| 20 | 401,854 | 6×9 | 154 | $11.99 | 50 | 209 | 10×15–30×30 | Picross Hanjie Griddlers Nonograms: 200++ Black and White |
| 21 | 412,704 | 8×10 | 79 | $7.49 | 35 | 60 | up to 50×50 | Nonogram Puzzle Book for Adults: 60 Large Griddlers |
| 22 | 428,203 | 8×10 | 87 | $12.99 | 10 | 100 | 15×15–40×50; easy · **color** | Nonograms Multicolor vol. 2 |
| 23 | 434,109 | 8.5×11 | 119 | $9.99 | 21 | 100 | expert, hard | Ultimate Nonogram Challenge: 100 Expert-Level Puzzles |
| 24 | 448,390 | 6×9 | 113 | $7.99 | 5 | 101 | 5×5–20×20; easy | Nonograms for Beginners: 101 Small and Easy |
| 25 | 454,702 | 8×10 | 61 | $8.99 | 124 | 50 | 20×25–35×35; easy–hard | Hanjie Puzzles: 50 fun picture-forming logic puzzles |
| 26 | 459,127 | 8.5×11 | 106 | $9.99 | 2 | 80 | 30×30–50×50; medium, hard | Nonogram Puzzle Book: 80 Brain-Training Nonogram Grids |
| 27 | 471,288 | 6×9 | 176 | $10.00 | 37 | 101 | 15×15; easy | 101 Easy Nonogram puzzles book 1 |
| 28 | 489,238 | 8×10 | 89 | $12.99 | 3 | 100 | 10×10–35×40; easy · **color** | Nonograms Multicolor vol. 3 |
| 29 | 490,156 | 7×10 | 120 | $8.25 | 45 | 52 | challenging | Hanjie Puzzles For Adults Volume II |
| 30 | 495,512 | 8.5×11 | 119 | $9.99 | 0 | 100 | 35×35–50×50; master | Master Nonogram Puzzle Book for Adults Volume 5 |

Outside the top 30: Djape's *The Massive Book of Picross* (600+ puzzles, 440 pages, 8×10, $39.99) ranks ~#1,000,000, so it barely sells now.

### What the data says

1. **Format.** Large trims win: 19 of the top 30 are 8.5×11 or 8×10. That's less than the "92%" some KDP blogs claim. 6×9 is real as a travel or beginner book (#2, #11). A5 is absent.
2. **Big books: mixed evidence.** The most-reviewed book is a 406-puzzle, $29.99 compilation (#4, 290 ratings). The 400- and 450-puzzle books rank #8 and #18, and the 600-puzzle *Massive Book* barely sells. Big books are one viable shelf, not the main one.
3. **A 30×30 cap is small for experienced solvers.** Adult books usually advertise grids up to 35×35–50×50. Only beginner and large-print books stop at 20–30 (#12, #17, #24).
4. **Difficulty: both approaches sell.**
   - Easy-only: #11, #17, #24, #27.
   - Expert-only: #13, #23, #30.
   - Mixed "Beginner to Master" (most common among recent launches): #2, #6, #9, #18.
   - Series are common: Multicolor vol. 1–3, Master vol. 5, Nonograms for Everyone vol. 2.
5. **Color is a real segment.** 5–6 of the top 30 are color nonograms. The generator is black-and-white only, and color interiors cost much more on KDP. A possible later niche.
6. **Crowding and themes.** 11 books launched in 2026, mostly "large print", have no sales rank yet. Themed books do stand out: a murder mystery is #1; "Around the World", "Cats & Dogs" and "Animals" also chart.

## 5. Reader reviews of big books

**Question:** do big books need easy puzzles, or do easy puzzles feel like filler to the people who buy 300+ puzzles?

**Method.** Written reviews of the four big books in the top 30, collected 2026-09-15: #4 The Big Book of Picross (406 puzzles, 4.7★), #8 400 Challenging Puzzles (4.6★), #9 Beginner to Master 300+ (4.0★), #18 Beginner to Master 450+ (3.9★). That's 50 reviews: 12, 11, 10 and 17.

**Caveats.**
- Amazon shows only ~10–17 written reviews per book, a mix of top and critical ones, so this is not a random sample.
- Several 5★ reviews of #9 and #18 look unreliable: generic wording, many posted on the same day, some in Spanish. The critical reviews carry more weight here.

### Difficulty

| Book | What reviewers said |
|---|---|
| #4 Big Book (406) | 1★ "Not enough small puzzles." 1★ only the small puzzles are doable, and there aren't many. 1★ "Far too easy", all levels "as easy as each other". 2★ wants a hint page for when "even seasoned players get stuck". 4★ notes some small ones are "real simple", without complaint. |
| #8 400 puzzles | A 4★ reviewer counted **96 easy / 90 medium / 90 hard / 124 expert (24 / 22 / 22 / 31%)** and called the levels reasonable. Easy: 10×10–20×20, 6 per page. Expert: 40×40+, one per page. 2★ "Not enough easy ones." An experienced 5★ solver used the easy ones as "time killers". |
| #9 300+ puzzles | 1★ "WAY too easy… regardless of level": simple symmetric pictures, and labels that don't match. The same review and a 3★ complain about puzzles that need guessing, with "no starting points". |
| #18 450+ puzzles | Difficulty is barely mentioned. The low rating comes from print quality. |

### Puzzle quality and print

| Complaint | Where | Reviews |
|---|---|---|
| Faint grid lines, hard to count squares | #18 | 7 of 17 |
| Tiny squares; "less puzzles but enlarged" would be better | #18 | 2 |
| A puzzle with more than one solution | #18 | 1 (1★) |
| Puzzles that need guessing | #9 | 2 |
| 5×5 guide lines not thicker than the rest | #8 | 1 |
| Misprinted clues, duplicated puzzles | #8 | 2 |
| Thin paper, ink bleeds through | #4 | 2 |
| Picture name printed on the puzzle page "feels like a cheat" | #4 | 1 |

### What the reviews say

1. **Easy puzzles don't hurt a big book.** Three reviews asked for more easy or small puzzles. The two "too easy" complaints were about labels that don't match the puzzles, not about the share of easy ones. #8's split of roughly a quarter per level drew no complaints about the mix.
2. **Labels must match the real difficulty.** Grading by what the solver needs, not by grid size, answers exactly this.
3. **Guessing is a dealbreaker.** "You should not have to guess in these puzzles." Keep guess-tier puzzles out of books.
4. **One solution per puzzle is a selling point.** The generator's solver already guarantees it; say so on the cover and in the description.
5. **Print quality drives the worst ratings.** Dark grid lines, bold 5×5 guides and a minimum cell size matter more than the difficulty mix.

## 6. The assumptions, reviewed

### Size mix (15 / 35 / 35 / 15 by cell count)

- **The buckets overlap.** 20×20 (400 cells) is in both b and c; 600–625 cells is in both c and d. And 30×20 (600) lands in c while 25×25 (625) lands in d, although the 30-wide grid is harder to fit.
- **Cell count is the wrong measure.** Page fit depends on the longest side, because that sets the width of the clue band. 10×20 and 14×14 both have ~200 cells but lay out very differently.
- **Size and difficulty aren't independent.** A 10×10 is almost never hard, and a 30×30 "easy" is tedious rather than easy. Plan them together (section 7).

Suggested mix for an 8.5×11 book, by longest side:

| Longest side | Share |
|---|---|
| ≤15 | 15% |
| 16–20 | 40% |
| 21–25 | 30% |
| 26–30 | 15% |

Wide grids go on the page in portrait (e.g. 20 wide × 30 tall). For an enthusiast book, extend to 35×35–40×40 and cut the small grids.

### Difficulty mix (70 / 20 / 10)

- Beginners tend to buy books labelled "easy" or "for beginners". A mixed book is mostly bought by people who already know nonograms, and 70% easy risks "too easy" reviews. The big-book reviews (section 5) show the opposite risk too: readers complain when there are too *few* easy puzzles. About a quarter is the safe range.
- Titles advertise difficulty as a selling point ("Upper Intermediate to Hard", "Beginner to Master"). "Mostly easy" isn't something titles brag about.
- "Easy / medium / hard" should come from what the solver measures, not from grid size: solvable by line logic alone (easy), needs shallow lookahead (medium), needs deeper lookahead (hard).

## 7. Very large grids: 40×40 to 50×50

**Question:** should books go beyond 30×30, up to 40×40–50×50?

**Short answer:** worth doing, but not in Book 1. They belong in a challenge book, or in the hardest section of a big book.

### For

- **Experienced solvers expect them.** Challenge books in the top 30 advertise grids up to 50×50: #5 (20×20–50×50), #13 (up to 50×50), #21 (up to 50×50), #26 (30×30–50×50), #30 (35×35–50×50). #8 prints its 40×40+ expert puzzles one per page, and its reviewer liked them best for the "more complex, satisfying image".
- **Pictures get better.** A 1★ review of #9 complained about "simple symmetric pictures". Image-based pictures look far better at 40×40 than at 20×20, which is this generator's strength; a 30×30 cap hides it.

### Against

**Cells get small.** Same model as section 2: the drawing is ~1.3 × N cells across ~190 mm of usable 8.5×11 width.

| Grid | Cell on 8.5×11 | Fit |
|---|---|---|
| 35×35 | 4.2 mm | ⚠️ |
| 40×40 | 3.7 mm | ❌ |
| 45×45 | 3.2 mm | ❌ |
| 50×50 | 2.9 mm | ❌ |

That's below the ~5 mm pencil threshold, and exactly what #18's 2★ "Very tiny squares. Not good for older people" review complains about. It rules these sizes out for beginner and large-print books. For experienced solvers with a fine pencil it's workable, but only with dark grid lines and clearly bolder 5×5 guides; at this size those decide whether a puzzle can be counted at all.

**It's an engineering change, not a setting.**
- `src/nonogram/limits.py` caps grids at `MAX_SIZE = 30`, and every layer checks against it.
- The solver can take seconds on random mid-density 40×40+ grids, and its cooperative timeout isn't enforced yet. The generator retries up to 30 times per puzzle, and large pictures fail the one-solution check more often.
- Difficulty grading was calibrated inside the current 10–30 range.
- The PDF cell-size table (`src/nonogram/export/layout.py`) stops at 30×30. The 2 mm floor would still hold, but nothing is tuned for 35–50.

### If you do it

- **Tall rather than square.** Width is the tight side of a portrait page, so keep width at 35–40 and let height go to 45–50. A 40×50 prints at the same cell size as a 40×40 and still fits the page height.
- **Keep them to the hardest section:** about 20–30% of a challenge book, one per page, never in a beginner or large-print book.
- **Test first:** print one 40×40 and one 50×50 page at 8.5×11 and solve them with a pencil.
- **Engineering order:** raise `MAX_SIZE`, then enforce the solver timeout, then recalibrate difficulty grading for the new sizes, then extend the PDF layout table to 35–50.

## 8. Recommendation

**Book 1:** 8.5×11 in (or 8×10), 100–150 puzzles, one per page, ~120–190 pages, $9.99–12.99, with a theme rather than a generic title.

**Choose the audience before the size mix:**

- *Beginners / large print:* 10×10 to 30×30, roughly 40% easy / 40% medium / 20% hard.
- *Enthusiasts:* extend to 35×35–40×40, fewer small grids, roughly 30% easy / 45% medium / 25% hard.

Size × difficulty matrix for a mixed book (each cell is % of the book):

| Longest side | Easy | Medium | Hard |
|---|---|---|---|
| ≤15 | 10 | 5 | – |
| 16–20 | 15 | 20 | 5 |
| 21–25 | 5 | 15 | 10 |
| 26–30 | – | 5 | 10 |

**Rules for every book** (from the reviews):
- No guess-tier puzzles; every puzzle has exactly one solution, and the description says so.
- Difficulty labels come from the solver, not from grid size.
- Dark grid lines, clearly bolder 5×5 guide lines, and a minimum cell size.
- Picture titles only in the answer key, not on the puzzle page.

**Later:**
- A big book (250–400 puzzles, $14.99–16.99) only once Book 1 sells. Mix: ~25% easy (10×10–20×20, 2–4 per page), ~40% medium (20×20–25×25), ~35% hard (25×25–30×30+, one per page), in labelled sections ordered by difficulty.
- A challenge book for experienced solvers: 8.5×11, up to 40 wide × 50 tall, with 40×40+ puzzles as the hardest 20–30%, one per page. Needs the engineering steps in section 7 first.
- A 6×9 pocket edition with easy/medium puzzles up to 15×15.
- Color nonograms as a separate product line.

**Cheap checks before committing:**
- Print one 25×25 page at 6×9 and at 8.5×11 and try solving it with a pencil.
- Print one 40×40 and one 50×50 page at 8.5×11 and solve them with a pencil before building larger sizes.
- Re-run the Amazon snapshot in a month to see which 2026 launches stayed ranked.

## Sources

- [Cambric: KDP printing cost 2026](https://cambric.pub/guides/kdp-printing-cost-guide/)
- [KDPEasy: puzzle book interior formatting](https://www.kdpeasy.com/blog/puzzle-book-interior-formatting-kdp) (marketing blog, figures unverified)
- [BookPublisherTools: puzzle book trim size and page count](https://www.bookpublishertools.com/puzzle-book-trim-size-and-page-count/)
- [Djape: The Massive Book of Picross specs](https://djape.net/book/the-massive-book-of-picross-hanjie-griddlers-nonograms-9781979082396/)
- [Conceptis: Pic-a-Pix books](https://www.conceptispuzzles.com/index.aspx?uri=book/100001)
- Amazon.com product pages for the 30 titles above, collected 2026-09-15; ASINs and raw fields in [amazon-nonogram-top30-2026-09-15.csv](amazon-nonogram-top30-2026-09-15.csv)
