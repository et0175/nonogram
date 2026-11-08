# CARD-229: "How to Solve" becomes a facing spread on pages 2 and 3, in the puzzle pages' own frame

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 4c (1.5d)
<!-- RESTATED 2026-11-08 in review cycles: was `1d`; +2c for CARD-393 folded in (the Play-online sentence under the guide intro), and a refresh of the starting facts (the guide is a VECTOR page since CARD-322). -->
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/229-guide-spread
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-229
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "How to Solve, as a facing spread"
**Idea:** —
**Wave:** 79
**Depends on:** CARD-206 (the title page that makes page 1, so the guide can start on page 2 and face page 3), CARD-222 (the frame it borrows), CARD-228 (the dots its key strip teaches), CARD-322, CARD-390 (the Play online page: this card's folded-in sentence names its page number)
<!--ADDED 2026-10-30 on the owner's decision "move from raster to vector first", and it closes a MEASURED HOLE rather than encoding a preference. Re-derived that day: all 10 cards gated by the 2026-10-25 ADR-0042 pass had **zero open dependencies** -- every `Depends on` entry already `done` -- so the ONLY thing holding them was the `Revision pending: true` flag. A flag is cleared by decomposing, which means re-cutting any of these would have RELEASED it into the wave queue ahead of the conversion its tests are supposed to target. This card is one of the 6 whose tests retarget from measuring ink to reading the content stream, and that is a TECHNICAL dependency, not a sequencing preference: the pages must BE streams (CARD-322) and the placed-edge convention must be settled (CARD-330, which CARD-322 already depends on) before an AC here can name a value. Re-cut before that and these ACs get written against a convention that does not exist yet, then need re-cutting again. The board's standing rule is that a sequencing PREFERENCE must not be written as a dependency; this is the other case, so it is. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_finalise_guide_preview.py, tests/test_book_page_numbers.py, tests/property/test_book_export_interior.py, tests/fixtures/book_baseline_card229.json, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, src/nonogram/admin/static/admin.css, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/, src/nonogram/admin/book_guide_vector.py, src/nonogram/admin/book_interior_vector.py, docs/guides/how-to-solve-nonograms.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The owner's requirement:** *"The two guide pages should face each other, on pages 2 and 3,
so a reader sees the whole lesson at once. They use the same header rule, margins and grey
clue boxes as the puzzle pages, so the examples look like the puzzles they teach. Each
technique sits in two columns: a numbered heading and a short explanation on the left, its
example on the right."*

**Current behaviour (verified by reading the code).**

- `GUIDE_PAGE_COUNT = 2` and `GUIDE_TITLE = "How to Solve Nonograms"`
  (`book_pdf_generator.py:491,497`); `create_guide_page` draws them (`:3196`).
- The guide is set in its own type scale — `GUIDE_TITLE_PT = 22.0`, `GUIDE_BODY_PT = 11.0`,
  `GUIDE_LEADING_PT = 17.0`, `GUIDE_TITLE_GAP_PT = 36.0` — not in the puzzle pages' frame.
- Its content constants are already named and tested: `GUIDE_INTRO`,
  `GUIDE_CELL_STATES_HEADING` + `GUIDE_CELL_STATES` (the three marks, **as a vertical list**),
  `GUIDE_EXAMPLE_HEADING`, `GUIDE_CLOSING_HEADING`, `GUIDE_CLOSING`, `GUIDE_BASIC_RULE_TEXT`.
- **INV-013 used to say the interior starts at the guide page as right-hand page 1.** Pages 2
  and 3 can only face each other if something else is page 1 — which is exactly CARD-206's
  blank title page, and why this card depends on it. **That amendment LANDED on 2026-10-17**
  (commit `91609aa`), as one statement covering both claimants: INV-013 and FR-043 now say
  page 1 is the blank title / copyright page with the guide following as a facing spread on
  pages 2 (verso) and 3 (recto), and **AC-368** is the registry's criterion for the spread.
  Nothing is owed at the architect station; the shipped code and
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` are what still encode
  the retired statement.

**What changes.**

1. The guide occupies interior pages **2 and 3**, so they face. Page 2 is a verso and page 3 a
   recto: assert the parity, not just the numbers.
2. The two pages adopt CARD-222's frame — the same margins, the same header rule at the same
   baseline, the same footer — so the lesson looks like the puzzles it teaches.
3. Examples use the **grey clue boxes** of the puzzle pages (CARD-208's shading), one cell size
   for every example, and a heavier outline around the playable squares.
4. Each technique becomes **two columns**: a numbered heading and its short explanation on the
   left, its example on the right.
5. **The three marks become a key strip at the top**, replacing today's vertical
   `GUIDE_CELL_STATES` list, and the key strip also carries the **difficulty legend** built
   from CARD-228's dots — the one place a reader learns them.
6. The copy is *the owner's current text, lightly tightened*. Keep the existing constants as
   the source; if a string changes, change the constant, and do not move prose into the
   drawing code.

**Deliberately not in this card:** the worked example's four steps and the rows/columns
callout at the foot of page 2 — CARD-230, so that this card's diff is the spread and the frame.

## FOLDED IN 2026-11-08 (owner: "fold 393 into 229") — CARD-393's work: the Play online sentence in the guide

**STARTING FACTS ARE STALE; RE-DERIVE FIRST.** This card was written when the guide was drawn by the raster `create_guide_page` in `book_pdf_generator.py`. Since CARD-322 the guide is a VECTOR page written by `src/nonogram/admin/book_guide_vector.py` through `InteriorPageWriters.guide` (the 23 raster writers still exist in `src/` until CARD-387 deletes them: do not edit them). Before implementing, re-derive what each statement above names (constants, line numbers, `GUIDE_PAGE_COUNT`, type scale, the writer's inputs) from the tree you start from and say which statements changed. The owner's requirement text above stands. Owner test budget (2026-11-07, 'fewer tests'): change existing guide tests rather than add; one control per concern; report the net collected-node-id change. Dependencies: CARD-390 must have merged (the sentence names the Play page's number).

### Items from CARD-393 (verbatim; AC ids prefixed 393.)

1. The guide writer (`book_guide_vector.py`, called through `InteriorPageWriters.guide` from `book_pdf_generator.py`) takes the Play page's interior page number (`None` when the book prints no Play page) and sets one line under the guide's intro: `Every puzzle in this book can also be played online. Scan the code on page {X}.` At or above the interior type floor, in the guide's own face and column, position from the guide's layout (not a new coordinate in the writer).
2. No Play page (no stored domain): the line is absent, and the guide is exactly today's. The line never appears for a page that was not printed (ADR-0041/R8).
3. The guide stays two pages. If the line makes the intro overflow its page on any admitted trim, the intro's spacing yields, never the line, and the author states the margin that remains.
4. `docs/guides/how-to-solve-nonograms.md` is touched only if it is the text the writer reads; the author states whether it is, and if so the sentence appears there with the page number as a described variable.

### Acceptance criteria from CARD-393 (verbatim; ids prefixed)

- **AC-393.1** (happy): *Given* a book with a Play page at interior page 167, *then* the guide's text layer holds the sentence with `167` exactly, below the intro and above the first technique heading. (test: `TestGuidePage_NamesThePlayPage`)
- **AC-393.2** (guard, true number): *Given* books of several sizes, *then* the number in the guide equals the interior page number of the PLAY page in the exported PDF, read from the PDF. (test: `TestGuidePage_PlayPageNumberIsTheRealOne`)
- **AC-393.3** (negative, no domain): *Given* a book with no stored domain, *then* the guide has no such line and its text equals the guide on main before this card. (test: `TestGuidePage_NoPlayPageNoLine`)
- **AC-393.4** (edge, fit): *Given* every trim in CON-018's profile set, *then* the guide is still two pages and the line overlaps no other guide mark. (test: `TestGuidePage_TheLineFitsEveryTrim`)
- **AC-393.5** (guard, type floor): *Given* the line, *then* it is at or above the interior type floor. (test: `tests/test_book_guide_page_type.py` floor cell, extended to the new line)
- **AC-393.6** (guard, preview): *Given* the interior, *then* the first QR-bearing page is not within the first pages Amazon previews: the guide carries no code, only the sentence (this is a restatement of ADR-0041/R8 against this page). (test: `TestGuidePage_CarriesNoQr`)

## Acceptance criteria

- **AC-1** (happy, the spread): *Given* any non-empty book, *when* the interior is exported,
  *then* the guide is interior pages 2 and 3, page 2 is a verso and page 3 a recto, and they
  face. (test: `TestGuideSpread_SitsOnPagesTwoAndThree`)
- **AC-2** (happy, the borrowed frame): *Given* a guide page and a puzzle page of the same
  book, *then* their margins, header-rule y and footer-rule y are identical, measured off the
  ink. (test: `TestGuideSpread_SharesThePuzzlePagesFrame`)
- **AC-3** (happy, two columns): *Given* each technique, *then* its heading and explanation lie
  wholly in the left column and its example wholly in the right, with no ink crossing the
  column boundary. (test: `TestGuideSpread_EachTechniqueIsTwoColumns`)
- **AC-4** (happy, the key strip): *Given* page 2, *then* the three marks are drawn as one
  horizontal strip at the top — not as a vertical list — and the difficulty legend beside them
  uses CARD-228's dots. (test: `TestGuideSpread_MarksAndLegendAreAKeyStrip`)
- **AC-5** (happy, one example cell size): *Given* every example on both pages, *then* all are
  drawn at one cell size, and the playable squares carry a heavier outline than the cell lines.
  (test: `TestGuideSpread_ExamplesShareOneCellSize`)
- **AC-6** (guard, the copy is the stored copy): *Given* the drawn pages, *then* every sentence
  comes from an existing `GUIDE_*` constant — asserted by comparing drawn text against the
  constants, so prose cannot drift into the drawing code.
  (test: `TestGuideSpread_TextComesFromTheConstants`)
- **AC-7** (edge, the page count and parity): *Given* a book with and without puzzles, *then*
  the interior's page count and every page's parity still agree with
  `interior_page_count`, `unpaired_interior_page_count` and the TOC's own page numbers — the
  guide moving by one page moves every number after it.
  (test: `TestBookToc_PageNumbersMatchTheWalk`, `tests/test_book_toc.py:357`)

## Guardrails

- G-1: CON-020's 10 pt floor holds for every face on both pages, including the key strip's
  labels and the two-column body (test: `TestInteriorType_EveryFaceHoldsTheFloor`; and the four
  `TestGuidePage_*` classes in `tests/test_book_guide_page_type.py`).
- G-2: The Finalise screen's guide preview keeps agreeing with the printed pages — it reads the
  generator's own text (test: `tests/test_book_finalise_guide_preview.py`'s
  `TestFinaliseGuidePreview_ReadsTheGeneratorsText`).
- G-3: The TOC's own `How to Solve Nonograms` row still points at the guide's first page, which
  is now 2, not 1 (test: `TestBookToc_PageNumbersMatchTheWalk`).
- G-4: Out of scope — the worked example's steps and the callout (CARD-230), the title page
  itself (CARD-206).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.
- G-6: Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module. The guide_page group (58 ids in test_book_guide_page / test_book_guide_page_type per CARD-387's recount) retires with CARD-229/230.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-229 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-013 / FR-043 — the amendment this card flagged LANDED** on 2026-10-17 (commit
  `91609aa`), as **one statement covering both claimants** (this card and CARD-206), which is
  what the two cards asked for: interior page 1 is the blank title / copyright page and the
  guide is the facing spread on pages **2 (verso) and 3 (recto)**. **Nothing is owed at the
  architect station.** The registry's criterion for the spread is **AC-368**, which names this
  card's own planned test `TestGuideSpread_SitsOnPagesTwoAndThree` (it does not exist yet);
  AC-283/AC-286/AC-289 and EC-034 were reworded for the title page, and AC-287 was re-measured
  — the first puzzle page moves to interior page 6. The parity mechanism and the KDP
  page-count check are unchanged.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-041 (the guide), FR-043 (folios, the TOC's rows).
- **INV:** **INV-013 (amended 2026-10-17, commit `91609aa`, jointly with CARD-206 as one
  statement — guide on interior pages 2 and 3; nothing owed)**.
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [The dependency on CARD-206 is structural, not stylistic] "Facing" is a claim about parity.
  Two pages face only when the first is a verso, so the guide cannot face until something
  occupies page 1. Starting this card before CARD-206 would mean implementing the spread
  against a parity that is about to change.

### Author round 1 (branch card/229-guide-spread, cut from main 8fe13982 = a12c39dd plus this card's dispatch stamp; CARD-393 folded in)

Figures labelled **mine** were produced by a command in this worktree (`PYTHONPATH` at its `src`, the main venv's python); nothing here was carried from another card.

**Starting facts, re-derived (which statements of this card changed).**
- "`GUIDE_PAGE_COUNT = 2`, `create_guide_page` at `:3196`": the constants exist (now `book_pdf_generator.py:885`/`:847`, value unchanged), but the guide is NOT drawn by the raster method any more. Since CARD-322 it is `book_guide_vector.guide_page`, reached through `InteriorPageWriters.guide`; `create_guide_page` stays, untouched, until CARD-387.
- "The guide occupies interior pages 2 and 3, so they face" (AC-1, AC-7): ALREADY TRUE on main. CARD-206's title page is page 1, `GUIDE_PAGE_NUMBERS == (2, 3)`, and the page plan, TOC and KDP counts need no change. Measured (mine): 18 cases (Book 1, 6 x 9 in, 5 x 8 in; with and without a player domain; 30 puzzles and the baseline book) give byte-identical `page_count`, guide pages (2, 3), TOC page (4), first puzzle page (6), Play page and `unpaired_interior_page_count` on main and on this branch. **The spread adds no page (2 -> 2), moves no TOC offset and no KDP gutter band.**
- "Its own type scale (22 / 11 / 17 / 36 pt)": only the raster method reads `GUIDE_TITLE_PT` / `GUIDE_TITLE_GAP_PT` now. The vector page set the title at 22 pt on the frame's top; it is now set in the band at the band font (14.16 pt), body 11 pt and leading 17 pt unchanged.
- "Examples use the grey clue boxes of the puzzle pages (CARD-208's shading)": **CARD-208 is `ready` and unbuilt; there is no clue shading anywhere in the package.** Not drawn here (it is not one of the seven ACs); the examples stay black. Owner decision below.
- "The legend uses CARD-228's dots, the one place a reader learns them": the legend now draws them, but **no vector puzzle page prints dots** (CARD-322 drew none; the class that pinned it was `TestDifficultyDots_TheInteriorPagesCarryNoDotsYet`), so the reader learns a mark the puzzle pages do not carry yet. Owner decision below.
- "Inherited from CARD-221: the Finalise preview still shows the three difficulty sentences": already fixed by CARD-221 fix 1 (names alone). The preview and the page agree; both now print names (the page with dots).
- "`docs/guides/how-to-solve-nonograms.md`": NOT the text the writer reads (the strings are `GUIDE_*` constants in `book_pdf_generator.py`); untouched.

**Design (what changed).**
- `export/layout.py`: `guide_spread_layout` / `GuideSpreadLayout` / `guide_example_limit` (+ `GUIDE_COLUMN_GAP_MM` 6.0, `GUIDE_BODY_INSET_MM` 6.0, `GUIDE_EXAMPLE_MAX_SHARE` 55 %). Where the columns start, the title band and the body between the two frame rules are COMP-007's (ADR-0036/R2); the writer measures only how wide words set (a type fact) and passes the widest example and the longest word.
- `book_guide_vector.py` rewritten around that layout: the header rule, footer rule, margins and folio are the puzzle pages' (`interior_frame`, `draw_sheet_furniture`; no grid-size label, no pointer: the page names the Play page in words); the title is set in the band through `book_puzzle_vector.draw_band`; each technique is a row of two columns (heading and explanation left, example right); the three cell marks and the legend are a key strip; ONE cell for every example on both pages (`example_cell_spec`: a `PageSpec.cell_cap` stepped down 0.1 mm at a time from the book's 7.5 mm only while the widest example exceeds 55 % of the measure, never below the cell whose clue digits hold CON-020's floor, because the guide's digits are instruction text and are never exempt); a heavier outline (`Layout.thick_rule`) around each example's playable squares; the pipeline is now a column of four boxes (the row of four was 1600 px wide at 11 pt, wider than any example column).
- `book_vector_draw.draw_difficulty_dots`: the interior's one vector round-mark site (ADR-0036/R3, a History entry says "per medium"): it draws exactly `layout.difficulty_dots`' geometry, a stroke centred on radius `(d - s) / 2` so the outer silhouette is the box; solid dots inked, outlined ones filled with paper.
- The fit ladder is `GuideForm` / `_FORMS` (9 forms), ordered by what a reader loses least: worked-example step sentences, counts, row notes, framing prose, THEN the worked example, then the explanations, then multi-row reasoning and the pipeline, then pictures. The worked example outlasts the prose because FR-041 promises one and the CON-020 control over its digits needs one to read (`test_a_book_keeps_the_worked_example_on_a_guide_page`).
- CARD-393: `GUIDE_PLAY_SENTENCE` + `guide_play_sentence(page)` in `book_pdf_generator.py` (the owner's wording verbatim: "Every puzzle in this book can also be played online. Scan the code on page {X}."); the walk passes `decided.play_page` (None for no Play page) through `InteriorPageWriters.guide` and `book_interior_vector.guide_page_stream`; the sentence sits under the intro, at every form, and the intro (prose) yields before the sentence ever does. The Finalise preview shows the same sentence from the same plan figure and heads its pages "Page 2" / "Page 3" (it said 1 / 2).

**Copy.** One string added (the owner's Play sentence, above). No existing sentence was reworded. Facts refreshed, old -> new: Finalise preview page headings "Page 1 / Page 2" -> "Page 2 / Page 3" (read from `TITLE_PAGE_COUNT`/`GUIDE_PAGE_COUNT`); `DifficultyLabel` and `GUIDE_DIFFICULTY_LABELS` comments ("the preview still shows the sentences", "the text CARD-229 places in the key strip") -> what is true (names alone on both surfaces, the sentences unprinted); `docs/how-it-works/.../07-book-assembly-and-the-admin-panel.md` "interior page 1 is the guide page" -> blank title page, guide on 2 and 3. Registry: FR-047 statement + AC-414..AC-417 (the sentence; ids next-free on main at 8fe13982 was AC-414, check again at merge), AC-368's planned test now exists.

**Measured consequences (mine).**
- *Cell and forms per trim* (`example_cell_spec`; `guide_page` at the dispatch counts, form index into `GuideForm`'s ladder: 0 everything, 1 worked-example step sentences off, 2 counts off, 3 row notes off, 4 framing prose off, 5 worked example off, 6 explanations off, 7 multi-row reasoning and pipeline off, 8 pictures off):

  | trim | shared example cell | page 2 (form, last mark px) | page 3 (form, last mark px) |
  |---|---|---|---|
  | Book 1, 8.5 x 11 in | 7.5 mm (88 px; the book's own cell, unchanged) | 0, 2574 (everything, explanations included) | 4, 2834 (explanations and the worked example's labels; no prose, counts or notes) |
  | 6 x 9 in | 5.7 mm | 6, 1867 | 6, 1754 |
  | 5 x 8 in | 5.7 mm | 7, 1925 | 6, 1967 |
  | 10 x 10 cm (minimum) | 5.7 mm | 8, 1706 | 8, 904 |

  5.7 mm is the cell whose clue digits are 42 px = 10.08 pt: the CON-020 floor, and the guide's digits are instruction text, never exempt. The text column on 6 x 9 in is 608 px for an example column of 821 px; with the explanations on, page 2's last mark is at 3167 px against a body that ends at 2371 px, so **on 6 x 9 in and smaller the printed guide carries headings and diagrams, not explanations** (it did before this card too: the old page 2 of 6 x 9 in was `(False, True, 0)`, no captions). Book 1 now prints them.
- *Overflow at the smallest trims* (mine, 68 pages: widths 10..21.59 cm x heights up to 27.94 cm, both parities, last mark below `page_frame().bottom`): main 5 pages, worst 295 px; this branch 5 pages, worst 513 px (10 x 10 cm p. 2, 10 x 12 cm p. 2, 11 x 12 cm p. 2, 12 x 12 cm p. 2, 12 x 15 cm p. 2). Same set size, a deeper worst case: no form of the page fits a sheet that short, and the writer keeps the last form as it always did. Not fixed here; it needs a decision (below).
- *KDP / TOC:* none (see the first bullet above: 18 cases identical).
- *Speed:* `guide_page` 0.01-0.03 s per page (the cell search is cached per sheet).

**Owner decisions needed (nothing was invented; every option is listed).**
1. **Legend names.** The legend prints `GUIDE_DIFFICULTY_LABELS`' names as stored, `EASY / MEDIUM / HARD`; a puzzle page's band reads `Puzzle 12 · Easy`. Options: (a) keep upper case (as built); (b) title case to match the band (`Easy / Medium / Hard`, i.e. `Tier.label`). Changes one constant's three strings.
2. **Legend sentences.** `DifficultyLabel.text` (one sentence per tier, kept as data since CARD-221) is not printed: the strip carries the name beside CARD-228's dots, as today's page carries the name alone. Options: (a) as built; (b) print each sentence under its name (several lines of 11 pt each in the legend's zone; not measured here, it would cost page 2 height and so a form on the smaller trims).
3. **The dots the guide teaches are not on the puzzle pages.** No vector puzzle page prints dots (CARD-322 drew none; CARD-207 is unbuilt). Options: (a) leave it and let CARD-207 close the gap; (b) hold the legend's dots until CARD-207 prints them; (c) a card to draw them on the puzzle band first.
4. **Grey clue boxes** (this card's item 3, "CARD-208's shading"). CARD-208 is `ready`, not built, and this card does not depend on it; the examples are black. Options: (a) CARD-208 first, then re-record the guide golden; (b) drop the grey from this card's wording.
5. **Key strip placement.** Page 2 reads: intro, the Play sentence, then the key strip, then "The basic rule"; the strip is "at the top" of the page's body, below the framing sentences. Option: the strip first, then the intro and the sentence.
6. **Footer.** The guide carries the puzzle pages' footer rule and the centred folio and nothing in the footer line (no grid-size label: no grid; no pointer: the sentence says it in words). A book with a Play page could add the puzzle pages' "Play ... online - p. N" pointer here too.
7. **Type scale on small trims.** To print the explanations on 6 x 9 in the type would have to drop below 11 pt / 17 pt leading (CON-020's floor is 10 pt); how far is not measured here. Options: (a) as built (explanations on Book 1 only); (b) a smaller guide scale on trims under 8 in wide; (c) the explanations move to a third guide page (adds a page: the TOC offsets and the KDP band would move, which this card measured does not happen today).
8. **The smallest trims** overflow (above). Options: accept as before; refuse a guide on a sheet this short; or a last form that drops the key strip's captions.

**Retirements, each with its named survivor (ADR-0042/R6; G-6).** The raster guide-page group is the 41 test functions below (56 collected node ids), the whole of `tests/test_book_guide_page_type.py` (file deleted) and the raster-reading part of `tests/test_book_guide_page.py`. A node id is retired only with a survivor that exists exactly once and reads the written content stream (the survivors named are in `tests/test_book_guide_spread.py`, new, `tests/test_book_guide_page_vector.py`, `tests/test_book_interior_face.py`). Kept in `tests/test_book_guide_page.py` because they read no raster page (10 ids): `TestGuidePage_IsTwoPages::test_interior_page_count_adds_exactly_one_guide_page` (6), `TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity::test_the_page_count_is_exactly_one_more_than_before_this_card` and `::test_every_pages_parity_still_equals_its_own_position`, `TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_arrangement_comparison_is_verified_against_every_legal_placement`, and `TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample::test_the_four_steps_solve_the_line_from_the_clue_to_the_finished_line`. Also renamed (same body, the claim changed with the page): `TestDifficultyDots_TheInteriorPagesCarryNoDotsYet` (3 ids) -> `TestDifficultyDots_OnlyTheGuidesKeyStripCarriesDots`, `test_the_round_mark_primitive_is_defined_once_and_called_nowhere_yet` -> `..._called_from_the_one_dot_drawer`, `TestGuidePage_DifficultyLegendCarriesNoRoundShapeToday` -> `...CarriesTheTiersDots` (6 ids; two methods renamed).

| retired node id (module::class::method) | ids | survivor (module::class::method) |
|---|---|---|
| `test_book_guide_page.py::TestGuidePage_TitledHowToSolveNonograms::test_the_exported_interior_page_2_is_titled_how_to_solve_nonograms` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_SitsOnPagesTwoAndThree::test_the_guide_is_interior_pages_two_and_three_and_they_face` |
| `test_book_guide_page.py::TestGuidePage_TitledHowToSolveNonograms::test_the_old_title_appears_nowhere_on_the_guides_first_page` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_SitsOnPagesTwoAndThree::test_the_guide_is_interior_pages_two_and_three_and_they_face` |
| `test_book_guide_page.py::TestGuidePage_TitledHowToSolveNonograms::test_the_search_finds_the_old_title_on_the_old_page` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_SitsOnPagesTwoAndThree::test_the_guide_is_interior_pages_two_and_three_and_they_face` |
| `test_book_guide_page.py::TestGuidePage_IsTwoPages::test_the_exported_interior_opens_with_both_guide_pages_then_the_first_puzzle_or_divider` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_SitsOnPagesTwoAndThree::test_the_guide_is_interior_pages_two_and_three_and_they_face` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_the_basic_rule_is_3_2_1_on_8_squares_filled_and_crossed_as_the_guide_describes` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_the_three_cell_state_icons_are_unknown_filled_and_empty_in_that_order` | 3 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_complete_lines_fills_every_one_of_10_squares` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_squeeze_from_both_ends_pushes_left_then_right_then_keeps_the_certain_overlap` | 3 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_mark_spaces_crosses_the_cells_beside_a_completed_block` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageOneCarriesTheBasicTechniques::test_every_diagram_is_drawn_at_the_books_own_cell_pitch` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_ExamplesShareOneCellSize::test_every_example_is_drawn_at_one_cell_and_the_outline_is_heavier` |
| `test_book_guide_page.py::TestGuidePage_CellStateHeadingsSurviveBareLevel2::test_bare_level_2_really_drops_the_cell_state_pictures_here` | 1 | `test_book_guide_page_vector.py::TestGuidePage_EveryFaceHoldsTheFloorInTheStream::test_the_record_covers_every_kind_of_face_the_page_sets` |
| `test_book_guide_page.py::TestGuidePage_CellStateHeadingsSurviveBareLevel2::test_the_cell_state_heading_survives_with_its_picture_dropped` | 3 | `test_book_guide_page_vector.py::TestGuidePage_EveryFaceHoldsTheFloorInTheStream::test_the_record_covers_every_kind_of_face_the_page_sets` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_page_2_is_titled_when_the_puzzle_gets_harder` | 1 | `test_book_guide_page_vector.py::TestGuideSpread_SitsOnPagesTwoAndThree::test_the_guide_is_interior_pages_two_and_three_and_they_face` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_region_split_rules_out_cells_the_remaining_run_cannot_reach` | 2 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_arrangement_comparison_shows_three_placements_then_what_they_agree_on` | 4 | `test_book_guide_page_vector.py::TestGuideSpread_TextComesFromTheConstants::test_every_diagram_is_the_constants_diagram` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_assume_follow_breaks_proved_pipeline_draws_its_four_boxes_in_order` | 1 | `test_book_guide_page_vector.py::TestGuidePage_WorkedExampleReusesTheGridRoutine::test_the_page_draws_every_diagram_through_that_one_routine` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_last_pipeline_box_has_a_complete_unclipped_border` | 1 | `test_book_guide_page_vector.py::TestGuidePage_EveryDiagramStaysInsideItsOwnBox::test_the_pipeline_inks_nothing_outside_the_extent_it_declares` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_difficulty_legend_carries_its_three_labels_and_no_sentences` | 1 | `test_book_guide_page_vector.py::TestGuidePage_DifficultyLegendCarriesTheTiersDots::test_the_legend_sets_the_three_tier_names_and_nothing_else` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_a_wrong_difficulty_label_does_not_match` | 1 | `test_book_guide_page_vector.py::TestGuidePage_DifficultyLegendCarriesTheTiersDots::test_the_legend_sets_the_three_tier_names_and_nothing_else` |
| `test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyLegend::test_the_new_drawing_routines_tolerate_a_sizeless_fallback_face` | 1 | `test_book_interior_face.py::TestInteriorFace_NoFaceIsReadFromAHostPath::test_no_font_is_loaded_from_a_filesystem_path` |
| `test_book_guide_page.py::TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim::test_every_line_of_type_holds_10pt_on_both_pages` | 3 | `test_book_guide_page_vector.py::TestGuidePage_EveryFaceHoldsTheFloorInTheStream::test_every_type_size_in_the_stream_is_at_least_ten_points` |
| `test_book_guide_page.py::TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim::test_a_1_2_and_3_digit_clue_each_hold_10pt_on_each_page` | 3 | `test_book_guide_page_vector.py::TestGuidePage_WorkedExampleClueDigitsAreNotExempt::test_every_clue_digit_holds_the_floor` |
| `test_book_guide_page.py::TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim::test_a_regression_shrinking_a_boxs_label_text_is_still_caught_by_the_floor_check` | 1 | `test_book_guide_page_vector.py::TestGuidePage_EveryFaceHoldsTheFloorInTheStream::test_the_writers_record_is_exactly_what_the_stream_shows` |
| `test_book_guide_page.py::TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample::test_each_step_is_pixel_identical_to_a_fresh_render_of_the_same_call` | 1 | `test_book_guide_page_vector.py::TestGuidePage_WorkedExampleReusesTheGridRoutine::test_the_page_draws_every_diagram_through_that_one_routine` |
| `test_book_guide_page.py::TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample::test_the_shipped_guide_page_draws_these_same_four_steps_pixel_identical_on_page_2` | 1 | `test_book_guide_page_vector.py::TestGuidePage_WorkedExampleReusesTheGridRoutine::test_the_page_draws_every_diagram_through_that_one_routine` |
| `test_book_guide_page_type.py::TestGuidePage_TypeIsBookSized::test_the_titles_glyph_box_is_the_box_of_22pt_type` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_no_stroke_width_tone_or_type_size_is_invented` |
| `test_book_guide_page_type.py::TestGuidePage_TypeIsBookSized::test_the_titles_measured_point_size_is_22` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_no_stroke_width_tone_or_type_size_is_invented` |
| `test_book_guide_page_type.py::TestGuidePage_TypeIsBookSized::test_the_bodys_measured_point_size_is_11` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_no_stroke_width_tone_or_type_size_is_invented` |
| `test_book_guide_page_type.py::TestGuidePage_TypeIsBookSized::test_the_title_is_the_largest_type_on_the_page` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_no_stroke_width_tone_or_type_size_is_invented` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_every_mark_sits_inside_the_usable_area` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_it_fits_the_smallest_trim_a_book_may_be_stored_at` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_the_whole_corpus_of_trims_and_counts_fits` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_page_two_pipeline_and_difficulty_legend_align_at_book1` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_page_two_difficulty_legend_aligns_at_narrower_trims` | 2 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_a_diagram_shifted_left_by_pad_is_not_at_frame_left` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_a_tall_narrow_trim_does_not_overflow_the_pipeline_diagram_past_frame_right` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_TextFitsTheUsableFrame::test_the_pipeline_diagrams_own_canvas_never_exceeds_the_usable_width` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_PointSizeIsIndependentOfDpi::test_300_and_600_dpi_print_the_same_point_size` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_face_in_the_corpus_holds_the_ten_point_floor` |
| `test_book_guide_page_type.py::TestGuidePage_PointSizeIsIndependentOfDpi::test_the_pixels_do_change_with_the_resolution` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_face_in_the_corpus_holds_the_ten_point_floor` |
| `test_book_guide_page_type.py::TestGuidePage_LeadingClearsTheType::test_consecutive_lines_advance_by_at_least_1_4_of_the_body` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |
| `test_book_guide_page_type.py::TestGuidePage_LeadingClearsTheType::test_no_two_lines_ink_runs_together` | 1 | `test_book_guide_page_vector.py::TestPropertyTest_GuidePage_WriterDerivesNoGeometryAcrossTrims::test_every_mark_in_the_corpus_sits_inside_the_frame_and_the_lines_clear_the_type` |

**Tests, censuses, lock (final figures are in the last paragraph once the final batch ran).** New `tests/test_book_guide_spread.py` (one cell per AC: AC-1..AC-6 and AC-393.1/.2/.3/.4/.6; AC-7 is the existing `TestBookToc_PageNumbersMatchTheWalk`, AC-393.5 is `TestGuidePage_EveryFaceHoldsTheFloorInTheStream`, which now draws the sentence). Each new cell was shown to fail under a plant (uneven example cell, stacked columns, dots drawn nowhere, furniture drawn nowhere, wrong Play number, prose written in the drawing code, a changed diagram constant). Re-derived by measurement, old -> new: vector golden `guide_1`/`guide_2` digests only (every other page type unchanged); `CALLEE_EXEMPTION_COST` 831/561/210/207 -> 832/562/211/208 (+1 call, `GUIDE_PLAY_SENTENCE.format`, absorbed by the last class; module `ast.Call` 908 -> 909); render-heavy frozen set: `test_book_guide_page_type.py` gone, `test_book_guide_spread.py` added (new file, 0 s in both recordings), the two hotspots documents restate the render row (195.42 s -> 193.13 s, 554.47 s -> 552.06 s); ref census constants restated in `tests/test_check_ref_resolution.py` after the registry refs were re-pointed at live classes. Frozen-census lesson applied: a helper named `_interior(` joins the render grep, so the writer's own cells stay in a module that builds no interior.

**Final figures (mine; armed batches under the advisory lock, `DATABASE_URL` = this worktree's own `*_test` database, never `nonogram_poc`).** Net collected node ids over the 9 modules this branch touches (+ the new one), `pytest --collect-only -q`, the dispatch commit's files vs the branch: **634 -> 599, net -35** (56 raster ids retired and 1 file deleted; +19 in `test_book_guide_spread.py`, +1 vector corpus cell, +1 Finalise preview cell; 4 existing ids renamed, 0 added). Ref census, old -> new: `BOOKKEEPING_ONLY` 11 -> 10, `FALSELY_ALIVE` 155 -> 152, `DEFINED` 420 -> 424, `TRACE_TESTS` 512 -> 514 (`CENSUS` restated from the run). Extra armed files run beyond the Touches list, from a grep of the whole `tests/` tree for guide, page counts, TOC, gutter and `How to Solve` (46 files): run 3 passed all but the census/profile constants named above; the run that found them also found that the ref census reads `git ls-files`, so a new untracked test module is "defined nowhere" until it is committed. **Lock handling:** acquired per burst with `holder: card229-author`, released only when the file still named me; once my lock file was gone when I went to release it (someone else's release removed it), and I did not touch anyone's lock; waited out CARD-414's gates; the coordinator asked for a quiet host during CARD-414's re-gate and I started nothing but waiting loops. Renders for the owner: `~/Documents/nonogram-reviews/CARD-229/` -- `guide-spread-book1-8.5x11-with-domain.png`, `guide-spread-book1-8.5x11-no-domain.png`, `guide-spread-6x9-with-domain.png`, `guide-spread-6x9-no-domain.png`, `guide-spread-5x8-with-domain.png`, `guide-spread-5x8-no-domain.png` (pages 2 and 3 side by side) and the six interior PDFs of the same names.

### Fix round 1 (review cycle 1: 7.3, S1-S5)

Figures labelled **mine** were produced by a command in this worktree.

- **S1, stale fact.** `book_finalize.html` said "Pages 1-2 of the interior PDF - page 1 a right-hand page"; it now reads the page numbers from the same `guide_page_numbers` the headings use ("Pages 2-3 ... page 1 is the blank title page"). Leftovers fixed in code comments: `app.py` (pages 1-2 are the guide) and `book_page_spec.py` (interior page 1 is the guide page). **Leftovers found and NOT changed (list for the owner):** `book_pdf_generator.py` module docstring ("guide at interior pages 1-2 ... the first puzzle page is interior page 4", CARD-116's worked example); `meta/architecture/glossary.yml:382`, `requirements.yml:217,2249,2550,4064,4720` (historical amendment notes and FR-043/FR-030 prose), `handoff.md:366,400`, `domain/commands.yml:173`, `inputs/raw-requirements.md` (dated intake); `docs/book_generation_req/book_generation_admin_panel.md:66`; tests' docstrings `test_book_page_frame.py:459`, `test_book_arrange_page_breaks.py:499`, `test_book_pdf_memory.py` (2699, 3993, 4082, 4225), `property/test_book_pdf_geometry.py:1012`, the card-200 baseline note. They describe history or other cards' arithmetic; rewriting them is a documentation pass of its own.
- **S2, circular survivor.** `test_every_diagram_is_the_constants_diagram` (same node) now reads each example's filled and crossed column indices off the stream and holds them to literals written in the test (3 2 1 on 8, complete line of 10, the squeeze rows, mark spaces, the region split, the three placements of 3 on 5, the four worked steps) and to one brute force (the squeeze's "certain" row is the overlap of every placement of 8 on 10). Plants, mine: `GUIDE_BASIC_RULE_FILLED` 7 -> 6 now RED; the squeeze certain row `range(2,8)` -> `range(3,9)` now RED. Title: `TestGuideSpread_SharesThePuzzlePagesFrame` (same node) now holds the guide's title to a puzzle band's size and baseline (14.16 pt, same y), and `TestGuideSpread_SitsOnPagesTwoAndThree` holds the two titles as literals; plant, title font x 0.8: RED. `guide_spread_layout` now takes its band from `header_band` (on the sheet's probe layout) instead of re-deriving it.
- **S3 + S4, overflow and small trims.** (a) The legend's fallback width-checks each entry against its zone and stacks the entries when a name does not fit (no overprint). (b) New forms after the old last one: a lean form (body inset `GUIDE_LEAN_INSET_MM` 1 mm instead of 6 mm, gaps closed, key-strip captions and pictures off), then headings off, then the basic-rule block off, then the last technique off; the Play sentence is in every form and is the last thing to go. (c) `_ADD_BACK`: after the ladder settles, every dropped mark that still fits is offered back, most valuable first (the ladder only removed). (d) The basic-rule caption now stays until the multi-row reasoning goes (it was dropped with the row notes, which lost a line main printed on 6 x 9 in). Overflow table, **mine**, widths 10..21.59 cm x heights 10..27.94 cm (174 pages, both parities, gutter 0.95 / outside 0.64 cm, last mark below `page_frame().bottom`), the guide at the same counts, play page 170 on the branch:

  | tree | pages overflowing | worst px |
  |---|---|---|
  | main (no Play sentence exists) | 7 | 295 (10 x 10 cm p. 2) |
  | branch at the review's tip, with Play | 19 | 624 |
  | branch now, with Play | 1 | 110 (10 x 10 cm p. 2) |
  | branch now, no Play page | 0 | 0 |

  4 x 6 in (10.16 x 15.24 cm): main p. 2 / p. 3 last mark -203 / -564 px from the frame bottom (no overflow); branch now -137 / -271 with a Play page and -358 / -271 without: zero overflow either way. **Residual for the owner:** 10 x 10 cm with a Play page still runs 110 px past the frame (main 295 without one); the options are to accept it, to refuse a guide on a sheet that short, or to drop the sentence there (not done: the sentence must survive every form). 6 x 9 in and 5 x 8 in renders looked at (mine): 6 x 9 prints the basic-rule caption, the row notes on page 3 and the framing prose again; Book 1 page 3 now prints the row notes ("The one-cell region cannot hold 2 or 3.", "Compare"); the worked example's step sentences (about 1000 px) still do not fit on Book 1 page 3, so its crossed squares at 1 and 5 stay unexplained there; the worked example is still absent on 6 x 9 and 5 x 8 (as on main).
- **S5, nits.** AC-324's registry survivor holds the literal title (`TestGuideSpread_SitsOnPagesTwoAndThree`); AC-325's now reads the worked example back cell by cell, drawn whole (`TestGuideSpread_TextComesFromTheConstants`), and the registry/trace rows say so; AC-326 reworded to a single outcome (clears the validator's "bundles several outcomes"); the `GUIDE_PLAY_SENTENCE` comment block sits on its own constant again. Not done: pinning the example column's 1 px shift on a verso (no existing cell reads it).
- **Page counts and KDP:** the 18 main-vs-branch cases are still byte-identical after the leaner forms (mine). The vector golden `guide_2` digest was re-recorded again through the entry point (every other page type unchanged).
- **S6, one grid style (owner request 2026-11-08: "why don't we use light-grey lines?").** There was no principled reason: the guide predates CARD-227. `_stroke_layout` now calls the puzzle pages' own `draw_grid_lines` and `draw_frame` (`book_vector_draw`; an admin-level module, so the layering walk is unaffected) with the lines clamped to the diagram's box and translated, and the playable squares' outline takes the weight and tone of the layout's own border line instead of a chosen width. Nothing is hard-coded: the weights and tones are the layout's declared ones (ADR-0037/R2: cell 0.3 pt at grey 0.35, every fifth 0.8 pt, border 1.3 pt, black). The grid is drawn first, so the dark marks (filled squares, crosses, clue digits) sit on top of it and stay black. **Print risk, mine:** the cell weight is a physical weight, not scaled with the cell, so the 5.7 mm example cell on 6 x 9 in and smaller carries exactly the figures the puzzle pages carry; looked at on the 6 x 9 in page at 100 % (pdftoppm -r 100) and at 300 dpi (pdftoppm -r 300, the path the repo's tests use): the grey cell lines are visible in the empty cells ("Mark spaces", the squeeze rows) and as faint as on a puzzle page, no fainter; no weight or grey was chosen or raised for the guide. If the owner wants them heavier that is ADR-0037/R2's figure, for every page at once. Tests: the corpus widths/tones cell now allows the layouts' declared weights and tones (derived from `compute_layout`, as before); the example-outline reader picks the squares' outline from the frame stroked on the same row. **The light-grey clue background** (the owner's artifact: a pale fill behind the clue area) is CARD-208's (clue boxes, unbuilt) and is NOT built here; the guide's examples go through the same primitive, so they pick it up when CARD-208 lands: **CARD-208 note (recorded here only, CARD-208 itself not edited): "guide examples follow"**. Before/after renders: `~/Documents/nonogram-reviews/CARD-229/guide-spread-book1-8.5x11-before.png` / `-after.png` and `guide-spread-6x9-before.png` / `-after.png` (before = tip 67707e94 with black grids).
- **Legend heading and line: owner approved 2026-11-08, implemented.** `GUIDE_DIFFICULTY_HEADING` is "Difficulty"; under it `GUIDE_DIFFICULTY_LINE` (one constant in `book_pdf_generator.py`): "Easy puzzles need only direct deductions; Hard ones need contradiction through much of the grid." (short form only), then the three dot/name entries. The line is a `GuideForm` flag (`legend_line`): kept through the explanations and the basic-rule caption, dropped only in the lean forms, and always after the Play sentence (which no form drops). In the side-by-side strip the line is set across the measure under the strip (a quarter of the measure is too narrow for a sentence); in the stacked strip it sits under the heading. The Finalise preview prints the same heading and line and no per-tier sentence. `DifficultyLabel.text` is nothing's input now (the preview tests assert it is absent): the data is left in place. Test: the existing legend cell in `test_book_guide_page_vector.py` and the existing legend cell in `test_book_finalise_guide_preview.py` hold the heading and the line as literals; plant, "direct" -> "indirect": RED. Overflow table re-measured with the line in (above numbers unchanged: 1 page, 110 px, 10 x 10 cm with a Play page; none otherwise); on 6 x 9 in page 2 the row notes now give way to the line.
- **Owner decision pending (not implemented, not waited for):** (ii) An experiment: render 6 x 9 in and 5 x 8 in with the worked example removed from the design to see whether the explanations then fit. Neither is shipped.

## Inherited from CARD-221, 2026-10-14 — a disagreement this card is expected to close

CARD-221 dropped the difficulty box's three sentences from printed guide page 2 (the owner's
decision), but **the Finalise screen's preview still shows them**
(`src/nonogram/admin/templates/book_finalize.html`), so that screen and the page it previews now
disagree. `DifficultyLabel.text` is deliberately kept alive for this reason and for this card's
key strip.

CARD-221 left it rather than fixing it, correctly — its G-6 put the admin screen out of scope,
and this card rebuilds the block on **both** surfaces anyway. Recorded here so it cannot be lost
between the two: reconciling them is a one-line template change plus
`tests/test_book_finalise_guide_preview.py:622`. This card's G-2 already requires the preview to
keep agreeing with the printed pages, so the disagreement must be gone by the time it merges.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** the design implemented on a raster interior, with its acceptance criteria
verified by measuring ink on a rendered bitmap.

**Should be:** the same design, unchanged — **the card's instrument moves, not its
decision**. CARD-293 §6 classifies this card as *written, tests retargeted*: the "How to Solve" facing spread — page composition and type.

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

