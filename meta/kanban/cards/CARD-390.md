# CARD-390: A "Play online" page after the last puzzle — a right-hand page whose QR opens the book's landing page, with the short address under it

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 4c (1.5d)
<!-- Over the 3c target on purpose and said so: a page kind, its placement with the parity rule, three page counters that must agree, and the drawn page are one deliverable (a plan without the drawn page, or the reverse, ships nothing). If the first cycle shows it does not fit, the split is: (a) kind + placement + counters with the page drawn as heading and typed address only, then (b) the QR on it. -->
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner decision 2026-11-07, "The Play online page": "a right-hand page after the last puzzle and before the solutions opener, which comes next. Readers reach it when they finish, or when they're stuck and about to look up an answer. The code opens the book's own landing page (/b/<slug>), which lists the puzzles in book order. The short address is printed for anyone who would rather type it." (owner artifact "One-QR Book Layout", version B).
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-388, CARD-389, CARD-311
<!-- CARD-311 is in progress and edits the same hotspots (book_pdf_generator.py, book_page_spec.py, app.py, templates/book_finalize.html, requirements.yml, ADR-0042): this card must start after it merges, or the two collide in the page plan and in the divider's folio decision. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, src/nonogram/admin/book_interior_vector.py, src/nonogram/admin/book_play_vector.py, src/nonogram/admin/book_sheet_vector.py, src/nonogram/export/layout.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, tests/test_book_play_online_page.py, tests/test_book_page_numbers.py, tests/test_book_toc.py, tests/test_book_finalise_gutter.py, tests/property/test_book_export_interior.py, meta/architecture/requirements.yml, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The interior has no page that points to the online player at all once the per-puzzle codes go (CARD-391). This card adds the one place a reader meets it: a new interior page kind, placed after the last puzzle and before the solutions, carrying the QR (CARD-388) for the book's landing address (CARD-389). It is the place the footer pointer ("Play puzzle 53 online · p. 167", CARD-391) and the guide's line (CARD-393) name, so the page number is decided here, from the page plan.

## What to implement

Read the code, not this list, for names; these are the anchors the architect read on 2026-11-07.

1. **A new `PageKind.PLAY`** beside TITLE, GUIDE, TOC, DIVIDER, PUZZLE, ANSWER in `book_pdf_generator.py`; `page_medium(PageKind.PLAY)` is VECTOR with no `RasterDeclaration` (ADR-0042/R1, R2). `page_medium` is default-deny on a kind it does not know, so the new kind is added there and in `interior_stream`'s `page_kinds` walk, which `_write_pdf` holds to the page count. ADR-0042's prose lists the interior kinds ("puzzle pages, answer pages, the table of contents and the guide"); add the Play page to its History in this delta (CARD-311 also edits that ADR; that is why the dependency).
2. **Placement.** After the last puzzle-section page, before the SOLUTIONS divider and the answer section. It is a RIGHT-HAND page (odd interior page number, FR-043: interior page 1 is the blank title page, odd pages are right-hand). When the last puzzle page is itself right-hand, the Play page would fall on a verso: insert ONE blank page before it so it is recto. The blank carries no ink and no folio (the blank title page's precedent, CARD-206). There is no recto-forcing mechanism in the code today (verified: no padding, no parity insertion exists; CARD-231, the section-opener card, would add one and is parked), so this card adds the smallest one, written so CARD-231 can reuse it, and does NOT move the SOLUTIONS divider: it follows the Play page directly, whatever its parity, exactly as today. (Owner question 3 in the architect report: confirm that, or have the divider forced recto too.)
3. **Gate.** The page, and the blank before it, exist only when the book has a stored player domain (`CARD-389`'s function returns an address). No domain: the interior is exactly today's, page for page.
4. **Counters stay one fact.** `interior_page_count`, `unpaired_interior_page_count` (`book_kdp.py`; it is an upper bound whose EC-034 cross-check equals the generator's `unpaired_page_count`), `section_plan` and the exported PDF's page count must agree. The KDP gutter band is read from the true total (`kdp_page_band`, `gutter_refusal`): one or two added pages can move a book across a band boundary and into a refused gutter; that is a real consequence to test, not to hide. `section_plan` gains the Play page's interior page number (or `None`); CARD-391 and CARD-393 read it from there and compute nothing.
5. **TOC and folios.** The TOC's "Solutions" page and every later folio shift by the added pages and must stay right. The TOC does not gain a Play row (owner question 4 in the architect report; recommendation: no, it is a back-matter page).
6. **The drawn page**, in a new `book_play_vector.py` (the page kinds are one module each): the interior frame's furniture and folio (`book_sheet_vector.py`), a large heading, the QR from `draw_qr` centred, the short address under the code in the book's interior face at or above the type floor (`tests/test_book_interior_type_floor.py` pins the floor), and one line of instruction. Positions come from a new function in `export/layout.py` (ADR-0036/R2: only COMP-007 places things), never from the writer. The code's side is chosen so the module size is at or above the minimum CARD-388 recorded; the author states the side in mm and the QR version. The exact copy of the heading and the instruction line is not fixed by the owner's text beyond the heading "Play online"; draft it from the artifact's table ("Turn to page N, scan, then tap the puzzle's number") and the owner reads it on the render.
7. **Finalise states it.** `book_finalize.html` shows one line: "Prints a Play online page at page N" or "No player domain set: this book prints no Play online page" (a silent omission is how a book goes to print without its code). The line reads `section_plan`.

## Acceptance criteria

- **AC-1** (happy, position): *Given* books whose last puzzle page falls on every parity and whose puzzle section ends two-up or single, *then* the page sequence is last puzzle page, [one blank], PLAY, SOLUTIONS divider, answer pages. (test: `TestPlayPage_SitsAfterTheLastPuzzleAndBeforeTheSolutions`)
- **AC-2** (happy, recto): *Given* the same corpus, *then* the Play page has an odd interior page number; a blank page precedes it exactly when the last puzzle page is odd; the blank has no ink and no folio. (test: `TestPlayPage_IsAlwaysARightHandPage`)
- **AC-3** (guard, one count): *Given* the corpus, *then* `interior_page_count`, `unpaired_interior_page_count`'s baseline, the exported page count and the page count the KDP band is read at are equal; and *given* a book whose count lands on a `KDP_GUTTER_BANDS` boundary, the band and the gutter refusal follow the TRUE total. (tests: `TestPlayPage_EveryCountAgrees`, `TestPlayPage_AddedPagesMoveTheKdpBand`)
- **AC-4** (happy, the code): *Given* a fixture book with a stored domain, *when* the interior is exported and the Play page is rendered, *then* the QR decodes (CARD-388's reader) to exactly the landing URL written as a literal in the test, and the typed short address on the page (read from the text layer) equals its literal. (test: `TestPlayPage_QrDecodesToTheLandingUrl`)
- **AC-5** (negative, no domain): *Given* a book with no stored domain, *then* the interior has no Play page and no blank, and its page count equals the same book's count on main before this card. (test: `TestPlayPage_NoDomainNoPage`)
- **AC-6** (guard, numbers follow): *Given* a book with the Play page, *then* the TOC's Solutions row and every later folio equal the real page numbers, read from the PDF. (test: `TestPlayPage_TocAndFoliosFollowTheInsertedPages`)
- **AC-7** (guard, medium): *Given* the page kinds, *then* `page_medium(PageKind.PLAY)` is VECTOR and no raster declaration names it; the page has no image XObject. (test: `TestPageMedium_PlayIsVector`)
- **AC-8** (edge, size and floor): *Given* every trim in CON-018's profile set, *then* the code's side leaves each module at or above CARD-388's recorded minimum, the code and the address fit inside the usable area, and the address is at or above the type floor. (test: `TestPlayPage_FitsEveryTrimAtAReadableModule`)
- **AC-9** (happy, Finalise): *Given* a book with and without a domain, *then* the Finalise screen shows the matching line with the real page number. (test: `TestFinalise_StatesThePlayPage`)
- **AC-10** (review-lens): the page's marks are placed by a new `export/layout.py` function and the writer adds no coordinates of its own. Evidence: the diff, and the same plant shape the sibling page tests use (move a mark in the writer, the placed-edge census reds). (ADR-0036/R2)

## Guardrails

- G-1: CLI and web exports stay byte-identical (CON-019): no new page kind reaches a single-puzzle export (`PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-2: No solution, grid or puzzle title on the page (ADR-0037/R1, ADR-0041/R2): the page carries a URL and words only.
- G-3: The SOLUTIONS divider is not moved or restyled here (CARD-231 and CARD-311 own openers and dividers).
- G-4: No stored slug, no migration (CARD-389 settled it).
- G-5: Expected page numbers and the URL are literals or come from the book, never from the function under test.

## System contract

- ADR-0041/R8 — one QR, one Play page, no domain no page (check: review-lens until CARD-391 flips it; this card's AC-4 and AC-5 are two of the evidence tests)
- ADR-0042/R1, R2 — interior pages are PDF operators; a raster page needs a declaration (check: the rules' own refs)
- ADR-0036/R2 — only COMP-007 places things (check: review-lens)
- ADR-0037/R1 — no picture title on a puzzle page (check: review-lens)
- CON-019 — CLI/web exports byte-identical (check: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)

## Architecture context

- **FR:** FR-043 (parity), FR-041 (guide), FR-045 (public player). This card adds an FR for the Play page to `requirements.yml` in the same delta (raw requirement: `meta/architecture/inputs/raw-requirements.md`, "Delta 2026-11-07"), after CARD-311 has merged its own edit of the file.
- **ADR:** ADR-0041/R8, ADR-0042, ADR-0036/R2.
- **Hazards the author must read:** CARD-231 (parked) wants the same recto insertion for openers; CARD-311 decides the divider's folio.

## Worktree notes

### Author round 1 (branch card/390-play-online-page)

Figures labelled **mine** were produced by a command in this worktree.

**Design.** `PageKind.PLAY` and `PageKind.BLANK` (the recto-forcing page: the title page's empty stream), both vector by `page_medium`'s default, so ADR-0042/R2's registry is unchanged. One rule, `recto_blank_pages(pages_before)` (a blank iff the last page laid is right-hand), used by `interior_page_count` (new `play_online` parameter, so the baseline and the KDP sheet-free count apply the rule to their OWN plan) and by `section_plan` (`SectionPlan.play_page`, `play_blank_page`, `play_page_count`); CARD-231 can reuse the rule. The generator reads the stored domain once (`self.player_domain`); the landing address is made downstream (`book_interior_vector.play_page_stream` -> `player_bundle.landing_address`) because `player_bundle` imports the generator; the page is reached through the new `InteriorPageWriters.play`. Placement is `export/layout.py` `play_page_layout` (+`PLAY_QR_MM` 40 mm, `PLAY_BLOCK_GAP_MM`); the writer `book_play_vector` adds only the centring offset of a string (its advance) and line steps. **Code side: 40 mm with its quiet zone** (0.98 mm a module for the 40-byte address, version 4). A sheet too short drops the instruction, then the heading, before the code (`qr_min_side_px` in `book_vector_draw`, so the layout refuses a side under the module floor); the shortest storable trim (10 x 10 cm) prints code plus address only, the address touching the footer rule. The address is tried at 12/11/10 pt and broken before `/b/` if 10 pt overruns. Wording is a draft: heading "Play online"; "Scan the code with your phone to play any puzzle in this book, then tap the puzzle's number."

**Gate (item 3).** No stored domain, or no puzzle: no page and no blank; every pre-existing test is unchanged and green.

**Counters (item 4), mine.** Books needing the blank (four singles: Play 13, blank 12; a pair and a single: blank 8, Play 9) and not (five singles; baseline; a pair): plan, kinds, exported pages and `unpaired_interior_page_count` agree (one test, literals worked by hand). KDP: the 150-page AC-288 book is 152 pages with a domain (blank 68, Play 69) and is refused at the 151-300 band at a 0.375 in gutter. `unpaired_page_count` baselines include the block, so `pages_saved` can read one less than the pairing saving when pairing changes the blank (never negative).

**Test budget, mine.** Net collected node ids **+6** (counted by reading the definitions; no parametrised node added): five in `tests/test_book_play_online_page.py` (plan+counts, no-domain, TOC+folios, QR decode, every trim) and one in `tests/test_book_finalise_gutter.py`; 0 added elsewhere (the golden gained a `play` digest inside the existing nodes, the type-floor and registry cells gained entries). The Finalise line and AC-411/412 share that one node. AC-7 (medium) is already asserted for every non-cover non-divider kind by `test_book_pdf.py`'s registry cell, which now covers PLAY and BLANK; AC-10 is review-lens (the diff).

**Frozen censuses restated deliberately.** `test_book_export_interior_cover.py`: callee table 879/595/220/217 -> 887/602/222/219 (+10 `ast.Call`, 957 -> 967, attributed one by one in the test); geometry doors 24 -> 25; counting expressions 9 -> 10; position sites 25 -> 35 (+10, listed), exemptions 5 -> 7. `test_check_ref_resolution.py`: CENSUS 575 -> 580, TRACE_TESTS 507 -> 512, DEFINED 411 -> 416 (the five FR-047 class refs, each against its class line). `test_book_pdf.py`: the writer-set cells know the fifth writer (`play`) and use a domain-bearing book so it is reached. `RENDER_HEAVY_SNAPSHOT` gained the new module (re-derived by `regrep_render_set`). Type-floor partition: `play` lettering, `blank` non-lettering. Golden re-recorded through the deliberate entry point: exactly one line added (`play`), no other digest moved.

**Docs.** FR-047 with AC-406..AC-412 in `requirements.yml`, a `trace.yml` row and CAP-006 membership; ADR-0042 History entry. Validator (`forge_1`, mine): main 0 errors / 89 warnings; branch 0 errors / 89 warnings with the new tests tracked, warning sets identical.

**Not done.** The pointers on puzzle pages (CARD-391), the guide's line (CARD-393), removal of the per-puzzle QR groups; no render of the guide/answer pages changed.
