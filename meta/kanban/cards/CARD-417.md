# CARD-417: The table of contents lists the Play online page

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2c (0.5d)
<!-- Basis: one row added to a count function that three places read (`structural_toc_entry_count`, with `play_online` threaded the way `interior_page_count` already takes it), one row added to `structural_toc_entries` from the plan's `play_page`, and the existing tests extended rather than new ones; the cost is the measurement (the 18 cases) and the frozen censuses, not the code. If the measurement crosses a TOC page boundary or a KDP gutter band, STOP and report: that is a re-price. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** owner request 2026-11-08 ("add a Play online in the toc"; "you can make card, but we don't need to move it first"), plus the ruling recorded below (the TOC stays after How to Solve).
**Idea:** —
**Wave:** —
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** CARD-390, CARD-205, CARD-322
<!-- CARD-205 (done) made the TOC list sections only; CARD-322 (done) made the interior vector; CARD-390 added the Play online page and its plan entry (`SectionPlan.play_page`). Queued after CARD-207 and CARD-416 by the owner's order: it changes existing TOC tests on the vector page, so it lands after CARD-416 has retired the TOC's raster twins and the placement cards have settled the band. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_toc_vector.py, src/nonogram/admin/book_kdp.py, meta/architecture/requirements.yml, meta/architecture/trace.yml, docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md, tests/test_book_toc.py, tests/test_book_play_online_page.py, tests/test_book_finalise_gutter.py, tests/test_book_pdf.py, tests/test_book_export_interior_cover.py, tests/test_book_interior_face.py, tests/test_book_interior_type_floor.py, tests/test_book_solved_answer_key.py, tests/test_book_arrange_page_breaks.py, tests/test_book_divider_pages_option.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card205.json, tests/test_book_vector_goldens.py, tests/test_check_ref_resolution.py
<!-- Derived 2026-11-08 by `git grep` over src/ and tests/ for `structural_toc_entry_count`, `structural_toc_entries`, `TOC_SOLUTIONS_LABEL`, `toc_page_stream`, `measured_toc_page_count` and `play_page`/`play_online`/`player_domain`; the author re-derives it and names any difference. The WHOLE tests tree is grepped, not only these files (see the lessons block). FR-043 is where the TOC's rows are stated in requirements.yml; trace.yml carries the AC-to-test rows. -->
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

The Play online page (CARD-390) is the one page a reader of the printed book is sent to with a phone, and it is the only page in the book the table of contents does not name. Since CARD-205 the TOC lists sections only: one `How to Solve Nonograms` row, for each non-empty level a heading row and a `Puzzles N-M` row against the level divider's page, and one `Solutions` row. The Play page prints after the last puzzle page (on a right-hand page, with one blank before it when the plan needs one) and before the SOLUTIONS divider, so it belongs in the TOC in that print order.

**OWNER RULING 2026-11-08 (recorded, do not reopen): the TOC does NOT move.** The owner considered putting the TOC before How to Solve and ruled no: the guide stays on pages 2-3 and the TOC follows it. The reason, the orchestrator's: the guide is a facing spread that must start on page 2 (a verso, facing page 3); moving a one-page TOC in front of it would cost a blank page in every book to keep the spread facing, and would move the KDP page count and so the gutter band. This card therefore adds a row and moves no page.

Facts carried from the owner's brief, each to be MEASURED or read by the author, not trusted:
* The TOC is about six rows on one page (carried: 40 / 31 / 27 rows per page on Book 1 / 6x9 / 5x8, via `_toc_entries_per_page`), so a page boundary is very unlikely to be hit; one more row must still be measured on every trim, not assumed.
* The TOC's length is a term in every later page number. It is decided ONCE from `structural_toc_entry_count` (`book_pdf_generator.py`) and read by THREE places that must never disagree: `BookPDFGenerator.section_plan`, `interior_page_count`'s sheet-free `toc_pages` default, and `nonogram.admin.book_kdp.unpaired_interior_page_count` (whose page count chooses KDP's gutter band); `interior_stream` closes the loop with a two-halved tripwire (the row count equals the count function's, then the re-measured page count equals the plan's).
* The Play page is planned in `section_plan`: `play_page` comes from the plan, `None` when the book has no stored valid player domain or no puzzle, and includes the recto-blank shift. The Play page's own notes (CARD-390), the CARD-392 footer pointer and CARD-229's guide sentence all read that same plan number. This card reads it from the plan and never recomputes it.

## What to implement

1. **The count.** `structural_toc_entry_count` takes the Play row into account (a `play_online` flag threaded the way `interior_page_count(play_online=...)` already is), so the count is `2 + 2 * level_count + 1` for a book with a Play page and unchanged otherwise, and still 0 for a book with no drawable puzzle. All three readers (`section_plan`, `interior_page_count`'s default, `unpaired_interior_page_count`) pass the same condition (`printable_player_domain(book) is not None` and at least one puzzle); they are changed in the same commit.
2. **The row.** `structural_toc_entries` appends a `Play online` row against `SectionPlan.play_page` (the page that actually carries the QR, not the blank before it), in print order after the last level's rows and before `Solutions`; no row when `play_page` is `None`. A constant for the label sits beside `TOC_SOLUTIONS_LABEL`. The vector writer (`book_toc_vector.py`) draws it like any numbered row; nothing is added to the raster side.
3. **The tripwire.** `interior_stream`'s row-count half stays as written and now catches a Play row built when the count function did not predict one (and the reverse).
4. **Measure** the 18 cases CARD-229 measured (its Worktree notes on branch card/229-guide-spread list them; they cover Book 1, 6x9 and 5x8, with and without a player domain, 30 puzzles and the baseline book; re-derive the exact set from there); report TOC rows, TOC pages, interior page count and the KDP gutter band before and after. Expected: identical page counts and bands. If a boundary is crossed, STOP and report.
5. **Docs and registry.** FR-043's TOC wording in `requirements.yml` and the how-it-works page 07 state the Play row; the AC ids this card adds are the next free on main AT DISPATCH (main's highest at this cut is AC-413; CARD-229 holds AC-414..417 on its branch): read the registry then, never pin a number now. `trace.yml` rows follow.

## Acceptance criteria

(The ids below are local labels; the registry ids are assigned at dispatch.)

- **AC-A** (happy, the row): *Given* a book with a stored player domain and puzzles, *when* it is exported, *then* the TOC carries exactly one `Play online` row, after the last level's `Puzzles N-M` row and before `Solutions`, and its page number equals the interior page that carries the QR read from the PDF, including the book whose last puzzle page is right-hand and the plan inserts a blank before the Play page (the row names the page after the blank). (test: extend `TestPlayPage_TocAndFoliosFollowTheInsertedPages` in `tests/test_book_play_online_page.py`; control: a row one page early, naming the blank, reds it.)
- **AC-B** (guard, no domain, no puzzle): *Given* a book with no stored valid player domain, or no printable puzzle, *then* it has no `Play online` row, and the no-puzzle book still has no TOC page. (test: extend `TestBookToc_ListsSectionsNotPuzzles` for the domain case and `TestBookToc_EmptyBookHasNoTocPage` for the empty book; control: the row printed for a book with no domain reds the first.)
- **AC-C** (guard, three places agree): *Given* the same book, *then* `section_plan`, `interior_page_count`'s sheet-free default and `unpaired_interior_page_count` all read one count that includes the Play row exactly when the book has a Play page, and `interior_stream`'s row-count tripwire holds. (test: extend `TestBookToc_KdpAgreesWithTheExportedCount` and `TestBookToc_TheRowCountIsWhatTheCountFunctionPredicts`; control: the count function dropping the Play term for one reader reds the first.)
- **AC-D** (guard, nothing after the TOC moves): *Given* the corpus with the TOC on one page, *then* the page numbers of every page after the TOC, the folios, the first answer page, the interior page count and the KDP gutter band are identical before and after. (test: extend `TestBookToc_PageNumbersMatchTheWalk` and `TestBookFinalise_PlayOnlinePageMovesTheBandAndIsStated`; the frozen baseline `tests/fixtures/book_baseline_card205.json` is re-derived by measurement, not re-recorded from the output.)
- **AC-E** (measured, the 18 cases): the table of AC 4 above is in the report, TOC rows per page stated per trim. (check: review-lens; no test pins it, the report is the evidence.)
- **AC-F** (registry): FR-043's TOC statement and the page-07 doc state the Play row and the order; trace rows name the extended tests above. (check: review-lens; the registry/trace consistency tests already in the tree are the gate.)

## Guardrails

- **G-1** Writes the vector page only: no raster writer, no raster test twin; retires the raster-twin tests of its own module. The TOC raster-twin group (class a/c ids in `tests/test_book_toc.py`, the "convert after" set) belongs to CARD-387/CARD-416, which lands BEFORE this card; this card adds no raster TOC test and converts none of them.
- **G-2** THREE-PLACE AGREEMENT: `section_plan`, `interior_page_count`'s default and `unpaired_interior_page_count` read one count from `structural_toc_entry_count`; a change to the entry rule lands in all three in one commit, and `interior_stream`'s two-halved tripwire stays (it is not loosened to make a row fit).
- **G-3** The Play row's number is `SectionPlan.play_page`, read from the plan; no second computation of the Play page anywhere (the CARD-390 notes, the CARD-392 footer pointer and CARD-229's guide sentence read the same number).
- **G-4** The TOC does not move and the guide stays on pages 2-3 (owner ruling above). No page is added to any book unless the measurement says a TOC boundary is crossed, and then the card stops and reports.
- **G-5** No bound widened, no corpus shrunk, no skip or xfail added; owner's test budget: change existing tests, add none beyond one control per AC that can fail, report the net test count.
- **G-6** CLI and web exports byte-identical (CON-019); the single-puzzle export has no TOC.

## System contract

- FR-043 (interior folios and the TOC's rows); CARD-205's rule that the TOC lists sections, extended by one section (check: AC-A to AC-D).
- ADR-0042: the interior is vector; the divider stays a bitmap, the cover stays raster (check: G-1; review-lens).
- ADR-0039: controls that can fail (check: the control named in each AC).

## Architecture context

- **FR:** FR-043. **Components:** the generator's section plan (`section_plan`, `structural_toc_entries`), the TOC vector writer, the KDP page count.
- **Decisions this follows:** CARD-205 (sections only), CARD-390 (the Play page and its plan entry), CARD-322 (vector interior).

## Lessons for the author (from CARD-392's gate and the board's own history)

* **Grep the WHOLE tests tree** for every name this card changes (`structural_toc_entry_count`, `structural_toc_entries`, the label constants, `play_page`, `play_online`, the TOC row counts), then run EVERY match ARMED (`DATABASE_URL` set to the worktree's own `*_test` database, never `nonogram_poc`). CARD-392's gate found a red in `tests/test_puzzle_edit_routes.py`, a file outside its Touches; the Touches list above is a starting point and not the boundary.
* **Frozen censuses are re-derived by measurement, never pasted:** the vector goldens (`tests/test_book_vector_goldens.py`), the check-ref digests (`tests/test_check_ref_resolution.py`), `RENDER_HEAVY_SNAPSHOT` (`meta/profiling/rank_durations.py` and its suite-profile test) and the dots floors. A row added to the TOC changes bytes in a golden by design: state which golden moved and why, and keep the control that distinguishes the intended change from drift.
* Acquire the advisory full-suite lock before any full or armed run (nothing writes it for you), and read `-rEfs` when counting reds.
* The TOC's raster-twin tests are CARD-387/416's; do not fix a raster reader here, and do not add a raster twin of any control you write.

## Worktree notes

## Triage 2026-11-09

Code built in 4b925232 (`TOC_PLAY_LABEL`, `_play_rows`, every page-count reader passes `play_row`). Left: tests that name the Play row and its page (AC-A, AC-B, AC-D), the 18-case measurement (AC-E), and the FR-043 / docs wording (AC-F).
