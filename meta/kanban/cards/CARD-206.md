# CARD-206: The interior opens with a blank title / copyright page, ahead of the guide

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false (config default; this card is a geometry/position change with an existing suite)
**Branch:** card/206-interior-title-page
**Worktree:** ../PythonProject4-card-206
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("# Book structure — The generator should construct the PDF in this order: Front matter ├─ Title / copyright page ├─ How to Solve Nonograms ├─ Table of Contents [generated]"); owner decision 2026-10-13 via AskUserQuestion — the page is **reserved blank** (a template page), not populated: "Leave it blank (template page) — reserve the page in the page plan so counts and parity are right, print nothing on it; you add the copyright text in the PDF afterwards."
**Idea:** —
**Wave:** 52
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_page_numbers.py, tests/test_book_export_interior_cover.py, tests/property/test_book_export_interior.py, tests/test_book_toc.py, tests/helpers/book_corpus.py  _(the last entry added 2026-10-22, after the scope gate, for dispatch correctness only — see `[Touches corrected]`; the other 20 files this card really changed are deliberately NOT listed)_
**Review score:** 8.6 (cycle 2/3 — fix round 2 applied, cycle 3 pending)
**Started:** 2026-10-21T22:18:12Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The interior's first page is the guide: `interior_stream`'s `produce()` yields
  `create_guide_page` for `1 .. GUIDE_PAGE_COUNT` (`GUIDE_PAGE_COUNT = 2`,
  `book_pdf_generator.py:459`), then the TOC pages at
  `GUIDE_PAGE_COUNT + 1 + index`, then the puzzle section, then the SOLUTIONS
  divider and the answer pages.
- Every downstream page number is derived from that start:
  `section_plan`'s `first_page`, `interior_page_count`'s terms
  (`:2111`), and `book_kdp.unpaired_interior_page_count` (`book_kdp.py:484`).
- `INV-013` **no longer** says the interior starts at the guide page: it and
  FR-043 were amended on 2026-10-17 (commit `91609aa`) to say page 1 is the
  book's blank title / copyright page with the guide following on pages 2 and 3.
  The shipped code and
  `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` still
  encode the old statement, so they are what this card brings up to the
  registry. The cover stays a separate file (FR-043) and is unaffected.

**What changes.** One blank page is inserted as interior page 1, so the front
matter reads: title/copyright (blank) → How to Solve (2 pages) → TOC → EASY
divider → ….

1. Add a front-matter page count constant next to `GUIDE_PAGE_COUNT`
   (e.g. `TITLE_PAGE_COUNT = 1`) and yield that page first in `produce()`: a
   white page on `self.page_spec(1)`, nothing drawn — **no folio either** (a
   title page carries no page number in any printed book, and this one carries
   no ink at all).
2. Shift every subsequent position by that constant — the guide pages, the TOC
   pages, `section_plan`'s `first_page`, `interior_page_count` and
   `book_kdp.unpaired_interior_page_count`. Derive it from the constant in
   every one of those places; a literal `3` anywhere is the bug this card is
   most likely to ship.
3. Parity: inserting one page flips the parity of **every** page after it, which
   is what moves each puzzle page's gutter side (`book_page_spec`'s
   `PageParity`). That is the intended consequence, not a side effect — the
   guide now opens on a left-hand page 2. Check it against a rendered proof
   before claiming the card done (owner validates print changes visually).
4. The page is reserved by the page plan, so the exported PDF gains exactly one
   page and the KDP gutter table is consulted with that count.

**The architecture delta this card flagged has LANDED (2026-10-17, commit
`91609aa`) — nothing is owed at the architect station.** INV-013 and FR-043 were
amended as **one statement covering both claimants**, this card and CARD-229:
interior page 1 is the book's title / copyright page, a right-hand page carrying
no folio and no ink at all, and the guide follows as a facing spread on pages 2
(verso) and 3 (recto). The parity mechanism and the page count finalise checks
against KDP are unchanged. The card must therefore: implement that behaviour,
and update
`PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` — which
still encodes the retired statement — to the amended one. Build against AC-283
(page 1 blank, no ink of any kind), AC-286, AC-287 (re-measured: the first
puzzle page is now interior page 6, a left-hand page), AC-289 and EC-034.
Kanban cards only read `meta/architecture/**` — the same posture CARD-198/202
took for FR-042/INV-011.

## Acceptance criteria

- **AC-1** (happy): *Given* any book with at least one drawable puzzle, *when*
  its interior is exported, *then* page 1 is blank — no folio, no title, no
  rule, no ink of any kind — and page 2 is the guide's first page. (test:
  `TestBookExport_InteriorOpensWithABlankTitlePage`)
- **AC-2** (happy, counts): *Given* the same book, *when* the interior is
  exported, *then* its page count is exactly one more than before this card,
  and `interior_page_count` and `book_kdp.unpaired_interior_page_count` both
  report that same number. (test: `TestBookExport_TitlePageCountedEverywhere`)
- **AC-3** (happy, positions): *Given* the same book, *when* the TOC is drawn,
  *then* every TOC row's page number still points at the page it names (the
  guide, each level's divider, the SOLUTIONS divider) after the shift. (test:
  `TestBookToc_PageNumbersSurviveTheTitlePage`)
- **AC-4** (edge, parity): *Given* a book whose first puzzle page was a
  right-hand page before this card, *when* it is exported, *then* that page is
  now a left-hand page and its margins are the left-hand spec — i.e. parity is
  still the 1-based interior position, counted from the title page. (test:
  `PropertyTest_BookExport_ParityCountsFromTheTitlePage`)
- **AC-5** (edge, no cover in interior): *Given* a book with an uploaded cover,
  *when* it is exported, *then* the cover is still a separate file and the
  interior's page 1 is the blank title page, not the cover. (test:
  `TestBookExport_InteriorHoldsNoCoverPage`, extended)
- **AC-6** (edge, empty book): *Given* a book with no drawable puzzle, *when*
  the interior is exported, *then* the existing refusal/empty behaviour is
  unchanged — this card does not make a blank page the only page of an
  otherwise-empty book. (test: `TestBookExport_EmptyBookUnchanged`)

## Guardrails

- G-1: The cover is produced as a separate file and never enters the interior
  (FR-043, INV-013's surviving half; test:
  `TestBookExport_EveryRouteSeparatesInteriorAndCover`).
- G-2: Puzzle-page and answer-page geometry is untouched — only positions
  shift. Do not edit `src/nonogram/export/layout.py` (owned by CARD-204).
- G-3: The guide's own content and page count are unchanged (CARD-201's 2-page
  tutorial; test: `TestBookGuidePage_*`).
- G-4: Out of scope — no imprint/ISBN field, no author line, no owner-editable
  copyright text (explicit owner decision 2026-10-13; the page stays blank).
- G-5: CLI and web-UI exports stay byte-identical (CON-019) — this is a book
  interior change only.

## System contract

_Re-derived at dispatch (2026-10-21) by `system_rules.py --card CARD-206 --root meta/architecture`
(`card_scope: touches`), curated under `meta/kanban/curation.md`: **projection 42 → kept 14,
dropped 28**. A projection — fix the source artifact, never this list._

**Derivation, so a later reader can reproduce it:** keep every `check.kind: review-lens` rule (nothing
executes them, so a reviewer is the only enforcement), plus every `kind: test` rule belonging to an ADR
whose text declares a reach limit — the idiom *"reach, stated rather than implied"*, matched **in the ADR
files and case-insensitively**, because the lens output carries no comment text and ADR-0039 writes it in
capitals. That selects **ADR-0036, ADR-0037, ADR-0039**. The remaining 28 `kind: test` rules are
dropped: the suite executes them on every gate, so listing them adds a line a reviewer must read and
changes nothing about whether they hold.

**Sanity check (curation.md's own):** this card's `Touches` includes `src/nonogram/admin/**`, so ADR-0039 must be in the
kept set — it is (ADR-0039/R1, ADR-0039/R2, ADR-0039/R3). The previous contract on this card was assembled 2026-10-17 under the superseded "ship 6-14 by judgement" convention and **carried no ADR-0039 at all** — the precise failure curation.md records on CARD-250 and CARD-251 and nearly repeated on CARD-254/255. It listed 8 rules and dismissed 51 as "package-wide"; the key that made them look package-wide was removed from all 31 affected rules on 2026-10-19, so the projection is now 42 rather than 58.

**Review-lens — nothing executes these; the reviewer is the control** (8):

- **ADR-0022/R1** — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "size", and no source mode constructs a grid from one integer.
- **ADR-0033/R1** — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membership mirror (puzzles.book_id).
- **ADR-0036/R2** — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself.
- **ADR-0037/R1** — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only.
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the solution before the puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium (playwright install chromium) before running them; until then there is no CI, and that is a known gap, not a met clause.
- **CON-021** — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No other surface — the CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play state is never persisted on the server: no progress, marks, error count, score or solve time is written to a database, file or server, no network request is made per mark, and no user account exists for playing (CON-017). The one place play state may be kept is the browser's own localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it never leaves that browser. The admin player ships the puzzle's solution grid to the browser to compute the error count and the solved state; this is permitted for the admin panel only, and a public or reader-facing player must not send a puzzle's solution to the browser before the puzzle is solved.

**Reach-limited — the ADR itself states its checks do not reach code written later** (6):

- **ADR-0036/R1** — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. — check: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`
- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same difficulty glyph, and four slightly different dots cannot be fixed once a book is on paper. — check: `test_the_books_own_pages_carry_no_undeclared_round_mark`
- **ADR-0036/R4** — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print a difficulty dot is to append a bullet to a header string, and that route bypasses the one drawing site and CON-020's type floor at once. — check: `test_no_module_types_a_round_mark_as_a_character`
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be narrowed to what is measured or deleted. — check: `test_the_control_for_each_spelling_depends_on_the_set`
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3. — check: `test_the_guard_sets_are_derived_and_not_hand_written`
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and records whatever it still cannot see as a measured bound with its own failing control. — check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`

_Dropped (28), each executed by the suite on every gate: ADR-0006/R1, ADR-0022/R3, ADR-0022/R4, ADR-0027/R2, ADR-0032/R1, ADR-0032/R2, ADR-0035/R1, ADR-0038/R3, CON-005, CON-009, CON-010, CON-011, CON-012, CON-015, CON-016, CON-020, INV-001, INV-002, INV-003, INV-005, INV-006, INV-007, INV-008, INV-009, INV-010, INV-011, INV-012, INV-013._

## Architecture context

- **FR:** FR-043 (interior/cover split, folios, TOC) — amended by this card, see
  the delta note.
- **ADR:** ADR-0036 (book page geometry), ADR-0035/R1 (status gating untouched).
- **CON:** CON-018 (Book 1 trim profile), CON-019, CON-020.
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_kdp.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- **[Env]** forge 2026.8.17. No `meta/.skills.yml` in this project, so there is no `forge.min_version` to
  compare against and no `models:` block — agents inherit the session model. The note is written because it
  is what makes a later diagnosis of this card's evidence possible at all.
- **[Dispatched]** wave 52, 2026-10-21T22:18:12Z, alongside CARD-259 on the owner's wave-boundary decision. Verified
  disjoint from it on every file (see `dispatcher.state → wave_52`), so the two run genuinely in parallel.
- **[Do not take timing measurements]** another card shares this machine this wave.
- **[System contract re-derived at dispatch]** The contract this card carried was assembled 2026-10-17
  under the superseded convention and **contained no ADR-0039**. It does now. Read the new
  `## System contract` section, not a memory of the old one.

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The artifact (https://claude.ai/artifact/Wp4iGB27cyBAV62da5ACMP) puts the guide on interior
pages **2 and 3** so the two pages face each other. That is only possible if something occupies
page 1 — which is this card. So:

- This card is no longer only a nicety; **CARD-229 depends on it structurally.** "Facing" is a
  claim about parity, and two pages face only when the first of them is a verso.
- The **INV-013 amendment this card flagged LANDED on 2026-10-17** (commit `91609aa`), and
  landed the way this bullet asked for it: **as one statement covering both claimants**, this
  card and CARD-229 — interior page 1 is the blank title page, the guide is the facing spread on
  pages 2 (verso) and 3 (recto). Nothing is owed at the architect station any more.
- The page this card adds shifts every interior page number by one, which moves the TOC's rows,
  the KDP band and therefore the printed gutter. CARD-205 left a three-caller page-count
  cross-check in place (`TestBookToc_KdpAgreesWithTheExportedCount`,
  `tests/test_book_toc.py:595`) — that is the test which must stay green.
- ~~Still blocked in substance until the architect pass makes the INV-013 / FR-043
  amendment.~~ **Unblocked 2026-10-17:** that amendment landed in commit `91609aa`. The card is
  ready to start on the registry as it now stands.

## Worktree notes — implementation (2026-10-22)

**[Done]** Interior page 1 is now the blank title / copyright page. `TITLE_PAGE_COUNT = 1`
sits beside `GUIDE_PAGE_COUNT` in `book_pdf_generator.py`; `create_title_page` draws the trim
and nothing else (no folio, no ink); `interior_stream`'s `produce()` yields it first; and every
downstream position counts from the constant. The guide now opens on interior page 2 (a verso)
and closes on 3 (a recto), the contents is 4, the first level's divider 5 and the first puzzle
page **6, a left-hand page** (AC-287 as the registry re-measured it on 2026-10-17).

### AC → test → mutant

Every mutant was applied with `cp -p` + `shasum -a 256` backup and a `trap`-restored original,
line-count preserving, only ever against the worktree's own file.

| AC | test | mutant that killed it |
| --- | --- | --- |
| AC-1 | `TestBookExport_InteriorOpensWithABlankTitlePage` (`tests/test_book_export_interior_cover.py`) | **M1** `produce()`'s `range(1, TITLE_PAGE_COUNT + 1)` → `range(1, TITLE_PAGE_COUNT - 99)` (no title page at all) kills `test_page_one_carries_no_ink_of_any_kind`, `test_the_interiors_second_page_is_the_guides_first_page`, `test_the_interior_runs_title_guide_puzzles_divider_answers` and `test_the_generator_reports_the_interiors_own_page_count`. **EDGE M1b** — `create_title_page` → `self.create_divider_page(page_number, "")`, i.e. a folio and nothing else — kills `test_page_one_carries_no_ink_of_any_kind`, so "no folio, no ink of any kind" is measured and not narrated. **EDGE M1c** `"white"` → `(254, 254, 254)` kills it too, so the ink count is not a "nearly white" tolerance. |
| AC-2 | `TestBookExport_TitlePageCountedEverywhere` + `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage` (same file) | **M2** `interior_page_count`'s `TITLE_PAGE_COUNT` → `0 * TITLE_PAGE_COUNT` kills `test_every_figure_reports_the_interior_with_its_title_page[1,3,7]`. **M3** the title loop's `range(1, TITLE_PAGE_COUNT + 1)` → `range(1, 1 + 1)` (a literal where a derivation belongs — the card's own named defect) kills **only** `test_each_position_is_counted_from_the_constant_not_a_literal[2,3]`, which is the test written for exactly that shape. **M4** `section_plan`'s `first_page` → `1 + 1 + GUIDE_PAGE_COUNT + toc_page_count` kills the AST guard's `test_every_guide_counting_expression_counts_the_title_page`. **M5** the TOC position's `+ 1 +` → `+ 2 - 1 +` kills `test_no_literal_page_offset_survives_in_one_of_them`. |
| AC-3 | `TestBookToc_PageNumbersSurviveTheTitlePage` (`tests/test_book_toc.py`) | **M6** `structural_toc_entries`' guide row `TocEntry(GUIDE_TITLE, 1 + TITLE_PAGE_COUNT)` → `TocEntry(GUIDE_TITLE, 1)` kills `test_the_guide_row_points_at_the_guides_first_page`. **M7** `first_answer_page`'s `TITLE_PAGE_COUNT` → `0` kills `test_the_solutions_row_points_at_the_solutions_divider` **and** its own control `test_the_comparison_would_have_caught_a_one_page_drift`. |
| AC-4 | `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage` (`tests/property/test_book_export_interior.py`, 12 seeded cases, floor asserted) | **M8** = M1 (no title page) kills it. **M9** `page_is_right_hand`'s `% 2 == 1` → `% 2 == 0` kills it, so the parity clause is measured and not a restatement of the position clause. |
| AC-5 | `TestBookExport_InteriorHoldsNoCoverPage::test_page_one_is_the_blank_title_page_and_not_the_cover` (extended) | **M1b** (a folio on the title page) and **M1** both kill it. |
| AC-6 | `TestBookExport_EmptyBookUnchanged` | **M10** the guide loop's upper bound → `TITLE_PAGE_COUNT - 99` (the guide stops printing, so the blank page *would* be the only page — the one thing AC-6 forbids) kills `test_the_interior_is_the_title_page_and_the_guide_and_nothing_else` and `test_the_blank_page_is_not_the_only_page`. **M2** kills them too. |

**One more mutant, because a mechanism this card added had to be shown load-bearing (rule 4).**
`create_guide_page` no longer reads which half of the tutorial to draw off the page's raw
parity — the two stopped coinciding when the title page went in front — and counts it from
`TITLE_PAGE_COUNT` instead. **M11** `(page_number - TITLE_PAGE_COUNT) % 2 == 1` →
`page_number % 2 == 1` **survives** every test this card wrote (AC-1's and AC-6's expected guide
pages are built through the same mutated method, so they agree with it). It is killed by
`tests/test_book_guide_page.py` (6 tests, which read the printed titles and diagrams off the ink)
and by `TestBookPdfMemory_PagesAreUnchanged`'s pixel baseline. Recorded as a measured bound,
not papered over.

### Figures re-derived from the production path, at the end

- **Page counts**, through `BookPDFGenerator().export_interior(...)` read back with
  `tests.helpers.pdf_pages.pdf_page_count`: an easy-20x20 book of **0 → 3**, **1 → 8**,
  **3 → 12**, **7 → 20** pages. `book_pdf_generator.interior_page_count(n, n, n, min(1, n),
  toc_pages=…)` and `book_kdp.unpaired_interior_page_count(rows)` return the same number for
  each. `export_book([one puzzle], …).interior_page_count == 8`.
- **The baseline book**, through `tests.helpers.book_corpus.export_of` + `pdf_page_count`:
  **14 pages**, **3,468,586 bytes** (CARD-224's recording held 13 and 3,369,797). Both are what
  `tests/fixtures/book_baseline_card206.json` records and what `BASELINE_PAGE_COUNT` states.
- **AC-4's parity separation**, through
  `tests/property/test_book_export_interior._expected_drawing_left_mm` — **corrected in fix
  round 1, review F-101.** The figure this bullet used to carry (left-hand 20.4500 mm,
  right-hand 30.4500 mm) reproduces on **no** case of the corpus: swept over all 12 cases and
  both `is_lower` values the pair is 10.0000/20.0000 for nine cases, 16.7000/26.7000 for two
  (5 and 10) and 12.9500/22.9500 for one (7), because a drawing's left edge is that page's own
  side margin **plus half the drawing's own spare**, and the spare varies with the puzzle.
  What reproduces everywhere, bit-exactly, is the **difference**: `gutter - outside` =
  **10.0000 mm**, on all 24 (case, `is_lower`) readings, maximum deviation 0.0. That is the
  quantity the docstring now states and the one the test now asserts exactly.
- **The rendered first puzzle page**, through `tests.helpers.page_ink.drawing_of` on the
  wide-gutter render: left edge **9.991 mm** — the 10.0 mm *outside* margin, i.e. the left-hand
  spec, with the gutter on the right (AC-4's own clause, seen on paper).
- **AC-288's retuned corpus** (`tests/test_book_finalise_gutter.py`): with the title page the
  total is `7 + 2E + M + (M + 1) / 2` for `E` easy `alone`s and an odd `M` paired mediums, so
  150 needs `4E + 3M == 285` → **39 + 43**; one more medium is 151. Both are asserted against
  the live page plan by that module's own `test_the_scenario_really_…` tests, not by this
  arithmetic.
- **`SPILLING_PUZZLES` 71 / `SPILLING_PUZZLE_PAGES` 70** (`tests/test_book_interior_face.py`):
  150 pages with one TOC page and 151 with two, back on KDP's 150/151 band edge, asserted live
  by that test itself — re-tuned exactly as its own assertion message instructs a later card to
  do rather than relaxing the assertion.

### Renders (owner validates print changes visually)

Written to `/Users/omelnikova/Documents/nonogram-reviews/CARD-206/`:

- `interior-book1.pdf` — the whole 12-page interior of a 3-puzzle Book 1 book.
- `interior-widegutter.pdf` — the same book stored with a 2.00 cm gutter against a 1.00 cm
  outside margin, which is the only way a parity change is visible in the drawing at all
  (CON-018 as amended has the two equal).
- `book1-page1-blank-title.png`, `widegutter-page1-blank-title.png` — interior page 1: blank,
  trim-sized, 0 non-white pixels.
- `book1-page2-guide-first.png`, `widegutter-page2-guide-first.png` — interior page 2, the
  guide's first page, folio "2" at the bottom **left** (a verso).
- `book1-page6-first-puzzle.png`, `widegutter-page6-first-puzzle.png` — interior page 6, the
  first puzzle page: the QR icon at the bottom **left** and the grid-size label at the **inner**
  margin, the drawing against the outside margin with the gutter on its right. **Corrected in
  fix round 1, review F-103:** the folio on a puzzle page is **centred** and does *not* mirror —
  measured on `interior-book1.pdf`, dark-column clusters in the bottom 14% of each 2550 px page,
  folio at columns 1264–1284 on page 6 **and** 1264–1283 on page 7 (page centre 1275), against
  the QR group at 150–968 / grid label at 2244–2395 on 6 and their mirror images on 7. Read off
  the pixels and confirmed by eye on a crop of the band. The mechanism is CARD-222/CARD-223's:
  a page that carries the interior frame gives its outer corner to the QR icon, so `_draw_folio`
  is called with `centred_x` and sets the number on the trim's own centre.
- `spread-guide-pages-2-and-3.png` — pages 2 and 3 side by side: the guide really does face
  itself now (AC-368's premise, which is what CARD-229 depends on).
- `spread-divider-5-and-puzzle-6.png` — the "Easy" divider on 5 and the first puzzle page on 6.

### Honest bounds

- **The AST guard's reach — ~~blind to a bare literal~~ CLOSED in fix round 1 (review F-102).**
  The guide-counting half is unchanged: `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage`
  enumerates every expression that loads `GUIDE_PAGE_COUNT` (7 sites) and requires each to load
  `TITLE_PAGE_COUNT` too, and that no integer constant in one of them is other than 0 or 1. The
  bound this bullet used to declare — blind to a position written as a bare literal with no
  constant in it at all — was *wrong about its own cover*: it said that shape was "covered
  behaviourally by `test_each_position_is_counted_from_the_constant_not_a_literal`", and the
  reviewer refuted it (a position that reaches no byte of output is invisible to a monkeypatch
  that re-reads the written file). It is no longer declared; it is closed. `_page_position_sites`
  now derives the module's page positions from the one geometry door they must all reach
  (`page_spec`) and fails on any literal other than 0 or 1 in one of them. What it still cannot
  see is stated in the class docstring, and is a different set: a position carried in from
  another module, and a wrong position spelled 0 or 1.
- **What the monkeypatch case cannot see.** `puzzle_pages`' and `puzzle_section`'s **default**
  `first_page` arguments are bound at import time, so moving `TITLE_PAGE_COUNT` at run time does
  not reach them. Production never relies on either (`section_plan` passes its own
  `first_page`); their value is read by the AST guard instead. Stated in the test's docstring.
- **`book_baseline_card206.json` has no control page** — the first recording in that chain for
  which that is true. Every page differs from CARD-224's recording shifted by one, because every
  page's folio reads one number higher and because the marks against the page's edges change
  sides with the parity flip (**corrected in fix round 1, review F-104:** on a framed page — the
  three puzzle pages and the two-up page — the folio is *centred* and does not move at all; what
  mirrors there is the QR group and the grid-size label. On the guide, contents, divider and
  answer pages the folio is itself the bottom-outer mark and does mirror). The
  "nothing above the footer moved" half of the claim is therefore **not** carried by that file:
  it is carried by `TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`, which this card
  re-points at the pre-CARD-206 position (an odd shift, so the footer band is cropped and the
  mirrored marks masked), and by
  `TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`, which this card moves
  to an **even** shift (`toc_page_count + TITLE_PAGE_COUNT` = CARD-201's own shipped layout) so
  that its whole-page comparison keeps working at all. Both are written into the fixture's own
  `changed_pages_note` and into the two class docstrings.
- **`TestBookPdfMemory_NonDrawingPagesAreByteIdentical`'s live comparisons** now rest on
  CARD-206's own forward baseline, read at the live index, which for *this* card is close to
  self-matching; what still bites is the attribution chain between the stored fixtures and the
  newly-asserted *difference* from CARD-222's recording. That is the same pattern CARD-222 used
  when it moved all thirteen pages, and it is said out loud in the class docstring.
- **`is_divider`** (the ink heuristic in `tests/test_book_pdf_levels.py`) cannot tell a divider
  from a page with no ink at all, so the blank title page reads as a wordless divider. It is not
  widened: the one walk over the whole interior excludes that page by its **blankness** and
  asserts both that page 1 is blank and that no other page is. Recorded in `is_divider`'s own
  docstring.
- **EC-034's check name is now stale and a card may not fix it.** The registry and `trace.yml`
  both cite `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`; its *statement*
  was amended on 2026-10-17 to the title page. The function keeps the registry's name (renaming
  it would leave both files pointing at a symbol that does not exist) and the module docstring
  says the name is now read as "parity counted from interior page 1". **For the architect
  station, not this card.**
- **Pre-existing registry drift this card makes one page worse:** `requirements.yml`'s AC-274 and
  AC-275 still say "interior page 3 (right-hand)" and "interior page 4 (left-hand)" — numbers from
  before CARD-200/CARD-201. The tests keep the *parity* claim correct and now name interior pages
  7 and 6. Flagged, not edited.
- **Not measured by this card:** the owner's visual sign-off on the renders above. The card's
  own gates are green; the paper judgement is the owner's.
- **What was actually run.** The 123 test files under `tests/` whose names carry `book`,
  `admin`, `pdf`, `export`, `layout` or `card_`, plus the matching `tests/property/` files —
  the card's own scope and its whole neighbourhood: **4,120 outcomes, zero failures and zero
  errors**, in one run after the last change (pytest exit 0). **The full suite was deliberately
  not run**
  (another card shares this machine and the orchestrator owns the gates), so anything outside
  that set is unverified by this card. `puzzle_pages`' default `first_page` and the blank
  page's own `page_number` argument were the two shapes most likely to escape it, and both are
  covered: the first by `tests/property/test_book_pairing.py`, the second by the AST guard.

### SCOPE+ (files changed beyond the card's predicted `Touches`)

Every one of these is a consequence of "+1 interior page, parity flipped on every page after
it", which is the card's own stated intent — the same ripple CARD-200 and CARD-201 recorded as
SCOPE+ in these same files.

- `SCOPE+ tests/test_book_pdf.py` — AC-287's own test lives here and the registry re-measured it
  (interior page 6, left-hand). Added `FIRST_PUZZLE_PAGE`/`DIVIDER_PAGE` so the indices are named
  once; flipped the hand in AC-287's class and in the two unbuildable-puzzle tests; AC-274's
  right-hand illustration moves to the second puzzle (interior 7) because the first is a verso now.
- `SCOPE+ tests/test_book_pdf_levels.py` — every divider/puzzle position +1; `is_divider`'s
  blank-page bound recorded.
- `SCOPE+ tests/test_book_pdf_memory.py` — the pixel-baseline chain, the page-kind map, the two
  shifted-content classes, `PAGE_FACTORIES` (adds `create_title_page`), the half-written-failure
  page count.
- `SCOPE+ tests/fixtures/book_baseline_card206.json` (new) + `tests/helpers/book_corpus.py` —
  the forward baseline every card in this chain records, `BASELINE_PAGE_COUNT` 13 → 14,
  `CORPUS_PAGE_COUNT` + 1, and `GUIDE_INTERIOR_PAGES = (2, 3)` shared by the three files that
  letter, measure and compare the guide's pages.
- `SCOPE+ tests/test_book_guide_page.py`, `tests/test_book_guide_page_type.py` — `create_guide_page`
  is called at the guide's new interior positions (2 and 3) and the frames are read at those same
  numbers, because parity mirrors a page's side margins. G-3 holds: the guide's content and its
  2-page length are untouched; only where it sits moved.
- `SCOPE+ tests/test_book_finalise_gutter.py` — every KDP page-count figure +1, and AC-288's and
  CK-1's corpora retuned back onto the 150/151 band edge (the module's own instruction).
- `SCOPE+ tests/test_book_interior_face.py` — the band-edge witness retuned (71/70), and the
  face-dependent page list shifted.
- `SCOPE+ tests/test_book_solved_answer_key.py`, `tests/test_book_proof_pages.py`,
  `tests/test_book_pdf_ink_mode.py`, `tests/test_book_arrange_page_breaks.py`,
  `tests/test_book_cell_size.py`, `tests/property/test_book_pdf_geometry.py` — page positions and
  page counts +1; the two ink-mode non-vacuity assertions now exclude the blank page by asserting
  its blankness rather than by loosening.
- `SCOPE+ tests/test_book_pdf_two_up.py`, `tests/test_book_pdf_band.py`,
  `tests/test_book_puzzle_frame.py`, `tests/test_book_level_order.py`,
  `tests/property/test_book_pairing.py`, `tests/property/test_book_order.py` — the same ripple
  again: each file's own written-out page map (`_page_shapes`' first page, `print_plan`'s
  starting page, `TWO_UP_PAGE`/`SINGLE_PAGE`/`INTERIOR_PAGES`, `ONCE_PAGE_COUNT` and its band /
  answer page maps, the arrange screen's `data-page` labels, and the two property files' own
  page-count arithmetic) moves by one. `tests/property/test_book_pairing.py` also pins
  `puzzle_pages`' **default** `first_page`, which is now interior page 4 — the one place in the
  suite that reads the default the AST guard covers.

### Guardrails

- **G-1** green: `TestBookExport_EveryRouteSeparatesInteriorAndCover` passes, extended to assert
  page 1 is blank on every route.
- **G-2** held: no geometry function was edited, and `src/nonogram/export/layout.py` is untouched
  (CARD-204 owns it). The "only positions shift" claim is measured by
  `TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`, re-pointed at the pre-CARD-206
  position for exactly this purpose.
- **G-3** held: `create_guide_page`'s content and `GUIDE_PAGE_COUNT` are unchanged; the whole
  `TestGuidePage_*` family is green.
- **G-4** held: the page is blank. No imprint, ISBN, author line or owner-editable text.
- **G-5** green: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`,
  `TestCliExports_ByteIdenticalAfterBookGeometry` and
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` all pass unchanged.
- `TestBookToc_KdpAgreesWithTheExportedCount` (the three-caller cross-check CARD-205 left) is
  green without being edited.

### Environment notes

- **[Full-suite lock redirected]** Every pytest run in this worktree was made with
  `NONOGRAM_FULL_SUITE_LOCK=/tmp/card206-scratch.lock`, so the board's own
  `meta/kanban/.full-suite.lock` was never read or written.
- **[No timing measured]** Another card shares this machine this wave; no duration is reported
  anywhere in this card or in any comment it added.
- **[Card line references]** The card's `## What to implement` cites
  `book_pdf_generator.py:459`, `:2111` and `book_kdp.py:484`. All three are stale by the file's
  own growth — at the merge base `GUIDE_PAGE_COUNT` is at `:537`, `interior_page_count` at
  `:3443` and `unpaired_interior_page_count` at `book_kdp.py:365`. What each reference *claims*
  is correct; only the line numbers had drifted.

---

### [Scope gate] Fired on 12 ready siblings. Inspected, **not escalated** — and the real finding is the predictor

`review.scope_gate: on`. The card predicted **6** files in `Touches`; the commit `3a3dfc8f` is **27**.
Every one of the 6 predictions was hit, and **no unpredicted `src/` file was touched** — the only
source edits are `book_pdf_generator.py` and `book_kdp.py`, both declared. G-2 holds:
`src/nonogram/export/layout.py` (CARD-204's) is not in the diff.

**Trigger 1 — "≥2 components beyond its slice": does NOT fire.** The diff's source footprint is
COMP-009 only, which is the card's own slice. The other 21 files are tests, fixtures and one helper.

**Trigger 2 — "covers a ready sibling's Touches": fires, against twelve cards.** Measured from the
real diff rather than from the declaration:

| ready card | share of its `Touches` already edited here |
|---|---|
| CARD-219 | **8/8 — 100%** |
| CARD-218 | **8/9 — 89%** |
| CARD-207 | 3/4 — 75% |
| CARD-208 | 4/6 — 67% |
| CARD-229 | 7/13 — 54% |
| CARD-231 | 6/12 — 50% |
| CARD-209, CARD-232 | 44%, 42% |
| CARD-227, CARD-226, CARD-230, CARD-233 | 36%, 33%, 33%, 30% |

**Not escalated, and the reason is checked rather than assumed.** The gate exists to catch a card that
grew to absorb a sibling's slice. This card absorbed nobody's deliverable: the overlap is **page-number
ripple**. Verified on the sharpest case, CARD-207 (whose subject is the split header band): every
change in `tests/test_book_pdf_band.py` is a `+1` shift and the page-map prose —
`ONCE_PAGE_COUNT 13 → 14`, `ONCE_BAND_PAGES {1:5,2:5,3:7,4:7,5:9} → {1:6,2:6,3:8,4:8,5:10}`,
`HARD_ALONE_PAGE 9 → 10`, `TWO_UP_PAGE 5 → 6`. Nothing touches the band's layout. The card's own
`## What to implement` names this ripple as the intended consequence ("inserting one page flips the
parity of **every** page after it"), and these files already carry the same kind of `SCOPE+` for
CARD-200 and CARD-201.

**The finding worth more than the verdict: the conflict predictor is computed from a number that was
wrong by 4.5x.** `run` step 2b scores predicted overlap from `Touches`, and this card's `Touches` was
**6 of 27 — 22%** of what it actually touched. For wave 52 that cost nothing: CARD-206 and CARD-259
were disjoint in prediction *and* in fact. But had any of those twelve run concurrently:

- **CARD-207, 208, 209, 226, 227, 229, 230, 231, 232, 233 would still have serialised** — they all
  touch `src/nonogram/admin/book_pdf_generator.py`, which is in `conflict.hotspots`, and the hotspot
  rule serialises regardless of score. The hand-maintained hotspot list saves the predictor here.
- **CARD-218 and CARD-219 would NOT have.** Their footprints are `tests/**` only, they touch no
  declared hotspot, and their declared overlap with CARD-206's declared `Touches` is low — yet their
  real overlap with this diff is **89% and 100%**. Those two would have been dispatched as
  parallel-safe into a guaranteed collision.

`tests/helpers/book_corpus.py` is the single most-shared file: it appears in **9 of the 12** overlaps
and is in no hotspot. Candidate `conflict.hotspots` additions — an owner decision, since it changes
dispatch behaviour — are that file and, arguably, the book test suite as one hotspot. Recorded in
`meta/kanban/backlog.md` rather than applied here.

**Consequence for the queue, which is certain rather than hypothetical:** all twelve of those cards now
need a rebase onto main after this card merges, and the three sharing `book_pdf_generator.py` plus
`book_corpus.py` will need their page maps re-read, not just re-merged. CARD-218 and CARD-219 are the
two whose whole subject is those test files, so they are the ones to dispatch soonest or re-cut.

---

### [Touches corrected] One entry added after the scope gate, and only one

`tests/helpers/book_corpus.py` was added to `Touches` on the owner's instruction, after
`tests/helpers/book_corpus.py` became a `conflict.hotspots` entry in `cf79eea3`. The reason is narrow
and mechanical: **the hotspot rule serialises a pair only when both cards *declare* the path.** This
card edited the corpus without declaring it, so without this entry the ten ready cards that do declare
it would serialise against each other and not against this card — the exact pair that measured 89% and
100% real overlap (CARD-218, CARD-219) would still have been dispatched alongside it.

**Why one entry and not the twenty-one others this card actually changed.** `Touches` feeds two
mechanisms with opposite requirements: the **conflict predictor**, which wants the true footprint, and
the **scope gate**, which needs a *prediction* to measure growth against. Widening a card's `Touches`
to its finished diff buys the first by blinding the second — it would make the gate report no growth on
any card, which is the mechanism that produced this card's most useful finding. So the correction is
confined to the single path that is now a declared hotspot, for a dispatch decision, and the backlog's
`@ops` item carries the general problem.

**Nothing is lost by correcting it at this point in the card's life.** The scope gate already ran
against the original 6-file prediction and its verdict is recorded above in full, including the 27-file
measurement and the twelve-sibling table. A later cycle re-running the gate will see 7 declared against
27 actual rather than 6 against 27 — a 22% → 26% prediction, still growth, still detected.

**Residual, unchanged by this edit:** a card that touches the corpus *undeclared* is still invisible to
the hotspot rule. That is a property of predicting footprints, not of this card.

---

### [Build gate] RED on attempt 1, GREEN on attempt 2 — and the red was invisible to the implementer

**Attempt 1 (`3a3dfc8f`): 1 failed, 5906 passed, 16 skipped. EXIT=1.**

```
tests/test_puzzle_edit_routes.py:1101
assert (before, after) == (7, 8)      ->   assert (8, 9) == (7, 8)
```

An **absolute** pin on the interior page count, placed by an earlier card precisely so the interior
count and the puzzle count "cannot be confused for each other again". This card inserts one interior
page, so both figures move by one. The test's actual claim — `after - before == announced`, with
`announced == 1` — held unchanged through the shift, which is exactly the distinction the pin exists to
keep visible.

**The implementation agent could not have seen it, and reported truthfully.** It ran a hand-chosen
"123-file book/admin/pdf/export/layout neighbourhood" and recorded *4,120 outcomes, 0 failures* — true
of what it ran. `tests/test_puzzle_edit_routes.py` is not in that neighbourhood by name, is not in the
card's `Touches`, and reaches the changed modules only through the **src→src import graph**. It was
selected by `scripts/impact_set.py`, whose transitive reverse-reachability over that graph was added
the same day specifically to close a fail-open hole. Without it this gate would have been green and
the defect would have travelled to the merge gate or to main. *"The implementer ran tests"* and
*"the card's tests pass"* are different statements, and this is a clean instance — the board's own
backlog already argues implementation agents should not be asked to self-certify breadth.

**Repair, attempt 1 of 2 (`12de4ac2`).** The expected value is derived, not guessed: the card adds
exactly one interior page and the gate observed `(8, 9)` directly. The **class** was measured rather
than the site fixed — `_interior_page_count` appears four times in that file, three in deltas (safe)
and `:1101` the only absolute pin; a scan of every test file this card did not touch found no other
absolute pin on an interior count, the remaining candidates being `> 0` bounds or
`metadata.page_count`, a puzzles-per-page figure this card does not move, all of which passed.
The pin still can fail: reverting it to `(7, 8)` reds exactly that test, verified with the file
restored byte-identical.

`SCOPE+ tests/test_puzzle_edit_routes.py` — one pin and its comment, no mechanism. Deliberately **not**
added to `Touches`: it is not a conflict hotspot, and widening a declaration past what dispatch needs
blinds the scope gate.

**Attempt 2 (`12de4ac2`): 5907 passed, 16 skipped, 0 failed. EXIT=0.** Same 109-file selection,
re-derived rather than reused. The 16 skips are `db_required`/browser, green. Build-fix attempts used:
**1 of 2**. Clear for review.

---

### [Review 1/3] Score: 7.5 — 0 Critical, **2 Important (gating)**, 4 Minor. Both gating fixes are one-liners

Report: `meta/review/20261022T002400Z-CARD-206-cycle1.yml` (validated by `yaml.safe_load`, 14/14
system-contract verdict lines). Step 8f's certification half: `deferred(cost)` — two Important open, so
it runs on the stable cycle. No full suite (CARD-259 live). Five pytest subsets, all exit 0.

**F-102 (high) — the card predicted this bug by name, and it shipped.** The card says *"a literal `3`
anywhere is the bug this card is most likely to ship."* Confirmed by the orchestrator:
`src/nonogram/admin/book_pdf_generator.py` computes `first_answer_page` **twice** —

```
:6696   first_answer_page = 3 + len(section)                                    # bare literal
:6747   first_answer_page = (1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT
                             + toc_page_count + len(section) + 1)               # the one the card fixed
```

Nine statements apart, same name. **The site is pre-existing** (`27ca88c7:6625`), so the defect is not
new — **what is new is the claim.** `TITLE_PAGE_COUNT`'s own docstring says *"**Every** front-matter
position after it counts from here rather than from a literal"*, and this site is recorded nowhere.
That is ADR-0039/R3: an exemption is a claim, held to an equality against the sites that exist today.

**Neither control can see it, and the honest bound that said otherwise is refuted.** The AST guard only
visits expressions containing a `GUIDE_PAGE_COUNT` load, and this expression has neither constant —
which is honest bound 1, verbatim. But the bound also claimed that shape "is covered behaviourally by
the monkeypatch test", and it is not: the reviewer measured that the value reaches no byte of output
(`page_frame(page_spec(n))` is parity-invariant in size at 2196×2994, and
`_degrade_infeasible_packed_pages` returns the identical plan for `page_spec(1..15)`), so nothing
behavioural can red on it. It is a latent, not a live defect — and a latent whose claim says it cannot
exist.

**F-101 (high) — one quantity, three figures, and the card's own correction is also wrong.**
`tests/property/test_book_export_interior.py:941-942` states the parities as **20.4500 / 30.4500 mm,
10.0000 mm apart**, measured "through `_expected_drawing_left_mm`". Run that method on the named input
and it returns **10.0000 / 20.0000** — which is exactly `PARITY_OUTSIDE_MM` and `PARITY_GUTTER_MM`, the
file's own constants. The reviewer swept all 12 cases and both `is_lower` values: the pair is
10.0000/20.0000 for nine cases, 16.7000/26.7000 for two, 12.9500/22.9500 for one, and
**20.4500/30.4500 occurs nowhere**. And 85 lines down, `:1026` **still says the right-hand spec is
"5.0 mm away"** — the exact wrong figure the card claims it caught and corrected.

The *difference* — 10.0000 mm apart — is right and reproduces everywhere, which is why nothing reds:
the live asserts are `> 4.0` and `< 0.1`, so they pass under any of the three readings. This is the
wave-48 figure rule in its sharpest form yet on this board: the card presents the pair as a
**re-derivation** that caught an error, and the re-derivation is itself wrong while the error it caught
is still on disk.

**F-103/F-104 (minor) — and the orchestrator relayed this false claim to the owner.** The card's render
description and the new fixture's `changed_pages_note` both say page 6's folio is bottom-**left**.
Measured on the artefact: it is **centred** (columns 1264–1284, centre 1275) on page 6 *and* page 7, and
**does not mirror at all** — only the QR group and the grid-size label do. The orchestrator repeated
"folio and QR bottom left" in its report to the owner on the implementer's word, without measuring.
F-105: `tests/test_book_pdf_memory.py:3043`'s failure message still names `page_number - 1` while the
reference is built at `- 2`. F-106: `:1067`'s `assert page_is_right_hand(before_this_card)` is a
constant assertion; the premise is carried by its two live neighbours instead.

**What HELD, measured rather than assumed:**
- **Claim 1 otherwise holds.** The reviewer enumerated the module by AST — every page-ish assignment
  with an int constant, every page-ish kwarg literal, every page-ish parameter default, across
  `book_pdf_generator.py`, `book_kdp.py`, `book_page_spec.py` — and found **exactly one** surviving
  site. Everything the brief listed is derived, including both walk defaults and
  `book_kdp.unpaired_interior_page_count`, which states no front-matter term of its own and delegates.
- **The declared surviving mutant M11 is real, and G-3 is intact.** Reverting `create_guide_page`'s half
  to raw parity is **killed by 20 assertion nodes** in `tests/test_book_guide_page.py` — *domain:
  CARD-260's instrument, RECORDING pass over that file, 70 `ast.Assert` nodes, child instrumentation
  off, SHIPPED 0 FAIL of 70 reached, ANY-RED* — and **survives all 59 reached nodes** of
  `test_book_export_interior_cover.py`, exactly as declared. The guide's content selection does have a
  live failing control; the card re-pointed a pre-existing file without weakening it.
- **The shifted baselines hold** (the name/shift mismatch is owned in writing, the odd/even parity split
  is the right design, both keep live `test_the_comparison_has_teeth` controls) — only the failure
  message was left behind.
- **The re-tuned corpora hold, and nothing was relaxed:** filtering both files' diffs to lines
  containing `assert` yields exactly two changed assertions, both page-number shifts.
- **Every other figure reproduced**, several in a second domain: 0→3, 1→8, 3→12, 7→20 (cross-checked
  against an independently written formula *and* `unpaired_interior_page_count`); baseline 14 pages and
  **3,468,586 bytes** exactly; the wide-gutter left edge 9.991 mm via `page_ink.drawing_of` **and** an
  independent raw-column scan at 9.821 mm, the same edge less the 2 px frame rule; page 1 at **0
  non-white pixels across four artefacts**.
- **The renders confirm the card's substance.** Page 2 is the guide's first half, folio bottom left — a
  verso. Pages 2 and 3 **genuinely face**. The TOC's rows read 2 / 5 / 9 against real pages title 1,
  guide 2–3, TOC 4, Easy divider 5, puzzles 6–8, SOLUTIONS 9, answers 10–12 — AC-3 on paper. Page 6 is
  a verso with the drawing against the outside margin, and page 7 its exact mirror.
- **ADR-0036/R3 and R4 checked independently** rather than via the named tests: exactly one `.ellipse(`
  in `src/nonogram`, and an AST walk of every string literal finds the forbidden codepoints only at the
  declared `pdf_generator.py:321` exemption. **G-1..G-5 all hold**, G-3 by mutant rather than assertion.
- **The orchestrator's build-gate repair `12de4ac2` reviewed and sound** — its class claim re-derived
  (`_interior_page_count` at `:1089/:1094/:1122/:1132`, `:1101` the only absolute pin), the delta
  assertion untouched, green.

---

### [Fix round 1] Review cycle 1's six findings — two gating, all six closed

Both gating findings were claim-versus-control mismatches, the family that escalated a sibling card
this session by *adding a sentence* in each of two fix rounds. So the rule this round worked to was:
**prefer deleting or narrowing a claim; add one only with a mechanism that can fail and the mutant
to prove it, in the same commit.** Two claims were deleted outright, one figure was deleted because
it reproduces nowhere, one assertion was tightened rather than added, and the one genuinely new
mechanism — the widened AST guard — ships with three controls, one of them a mutant on the real file.

- **F-102: route taken = WIDEN THE GUARD** (the ADR-0039/R2 shape), not "narrow the claim and name an
  exemption". Both halves, with the measurement each rests on:

  *The derived value, and how what the probe needs was determined.* `interior_stream` computed
  `first_answer_page` twice; it computes it once now —
  `1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + toc_page_count + len(section) + 1` — hoisted to where the
  bare `3 + len(section)` was, with the duplicate nine statements later deleted. The value was **not**
  copied from `:6747` on faith: the degrade pass's own contract says it wants *a* placed spec, and that
  was measured. `page_spec(n)` over interior positions 1..20 differs in exactly **one** dataclass field,
  `parity`; the usable area is a single value (**190.500 × 253.492 mm**) and `page_frame` a single size
  (**2550 × 3300 px**) for every one of them; and `_degrade_infeasible_packed_pages` returns an
  identical plan on ODD and EVEN for a feasible 2-up, a 4-up that splits into singles and a 2-up that
  falls back to singles, and over `page_spec(1..20)` on the baseline book and on a nine-easy book. The
  probe needs a spec, not a position — so the honest fix is one assignment whose name is true for both
  readers, rather than a second derivation beside the first.

  *The guard.* `_page_position_sites` derives the module's page positions from the one geometry door
  they must all reach (`page_spec`/`book_page_spec`, ADR-0036/R2's "one door"): the vocabulary grows to
  a fixed point through parameters, arguments and copies, and every binding of a position name
  (assignment, `for` target, walrus, parameter default) and every expression handed to a door is a site.
  **Measured today: 6 names, 25 sites, 0 offenders** — against the old guard's 7 guide-counting
  expressions. What it newly reaches includes the title-page loop's `range(1, TITLE_PAGE_COUNT + 1)`,
  the TOC page's `TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1 + index`, the SOLUTIONS divider's
  `first_answer_page - 1` and both walk defaults.

  *The planted-literal control, in both states.* With the derived assignment reverted to
  `3 + len(section)` (line-count preserving, `cp -p` backup, restore verified), **exactly one assertion
  node reds** — `test_no_page_position_in_the_module_is_written_as_a_bare_literal`'s own assert,
  `tests/test_book_export_interior_cover.py:1479` at the time of the run (`:1481` after two
  docstring lines were added to that file later in the round) — *DOMAIN:
  `tests/kill_matrix.py` RECORDING pass over that file, 126 `ast.Assert` nodes, SHIPPED 0 FAIL of 125
  reached (pytest exit 0, 72 collected tests), child instrumentation off, aggregate ANY-RED;
  PLANTED_LITERAL exit 0, 125 reached, 1 FAIL.* Removed, SHIPPED is FAIL-free — so the guard reds on
  the defect and passes on the fix, and nothing else in that file can tell the difference, which is
  cycle 1's refutation reproduced rather than taken on trust. Two further controls live in the test:
  the enumeration run with **no door in its seed set reports nothing at all** (ADR-0039/R1's
  caught-with / missed-without, over the set member itself), and a planted literal in a source the test
  owns is reported as exactly `[('assignment', 'first_answer_page', [3])]` while its derived twin is not.

  *The claim.* `TITLE_PAGE_COUNT`'s docstring no longer asserts an unenforced universal: it names the
  control it is held to. The class docstring stops declaring the bare-literal bound (it is closed) and
  states the two things the enumeration genuinely cannot see — a position computed in another module,
  and a wrong position spelled `0` or `1`.

- **F-101: one quantity, one figure, and the figure now has a control.** Re-derived through
  `tests/property/test_book_export_interior._expected_drawing_left_mm` — the function the docstring
  names — over all 12 cases and both `is_lower` values, 24 readings:

  | reading | cases |
  | --- | --- |
  | 10.0000 / 20.0000 mm | 0, 1, 2, 3, 4, 6, 8, 9, 11 |
  | 16.7000 / 26.7000 mm | 5, 10 |
  | 12.9500 / 22.9500 mm | 7 |
  | **difference, every case** | **10.0000 mm, maximum deviation 0.0** |

  `20.4500 / 30.4500` occurs nowhere, which is what the review measured and this re-derivation confirms
  independently. **What the docstring says now is the difference and only the difference**, because no
  absolute pair describes the corpus: a drawing's left edge is that page's own side margin *plus half
  the drawing's own spare*, and the spare varies with the puzzle. The difference is `gutter - outside`
  by construction and reproduces bit-exactly. **It is no longer a figure with no control:** the
  separation assertion was tightened from a `> 4.0` floor to an exact equality against
  `PARITY_GUTTER_MM - PARITY_OUTSIDE_MM`, per case. MUTANT **MODEL_DRIFT** (`_expected_drawing_left_mm`'s
  right-hand margin `gutter_mm` → `gutter_mm + 5.0`) kills **exactly that assertion and nothing else** —
  *DOMAIN: `tests/kill_matrix.py` RECORDING pass over
  `tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_ParityCountsFromTheTitlePage`,
  52 `ast.Assert` nodes, SHIPPED 0 FAIL of 11 reached (pytest exit 0, 1 collected test), child
  instrumentation off, aggregate ANY-RED; MODEL_DRIFT exit 0, 11 reached, 1 FAIL at `:1122`.* The old
  `> 4.0` floor **survives** that mutant — which is precisely why one quantity could carry three
  readings for a whole cycle. `:1026`'s "5.0 mm away" is gone.

- **F-101's class sweep — every figure in this card's diff, with its door.** Reproduced through the
  production path: interior page counts **0→3, 1→8, 3→12, 7→20** (`export_interior` read back with
  `pdf_pages.pdf_page_count`, equal to `interior_page_count` and to `book_kdp.unpaired_interior_page_count`
  for every n); the baseline book at **14 pages / 3,468,586 bytes** (`book_corpus.export_of`, equal to
  `BASELINE_PAGE_COUNT` and to the fixture's own `page_count`); AC-288's **39 + 43 = 150** and **39 + 44
  = 151** (`7 + 2E + M + (M+1)/2`); the band edge at **71 puzzles / 70 pages = 150**; the parity
  difference above. Figures that carry their own live assertion, and so are controlled by recomputation
  rather than by prose: **25.45 mm** (`test_the_drawing_sits_25_45_mm_from_the_left_trim_edge`),
  **12.7 mm**, **287 pages** (`AC179_PAGES`, asserted against the panel's own counts three ways),
  **150 px** (`KNOWN_BARE_LEVEL_2_MAX_OVERFLOW_PX`), **0 non-white pixels** on page 1. **One more figure
  failed the sweep and was deleted:** `tests/test_book_pdf_memory.py`'s "measured while making this
  change: 1186 px against 1191 px on the two-up page". On this class's own book and corpus the
  ink-bbox crop is **(2251, 2948) at both parities and at both shifts** — the same width, not two — so
  the parenthetical was removed rather than restated, and the sentence narrowed to the part that is
  true (an odd shift puts the mirrored footer marks on the other side of the page). The *design* that
  sentence explains — the even shift, and its `test_the_comparison_has_teeth` control — was certified in
  cycle 1 and is untouched.

- **F-103 / F-104: the folio, measured off the artefact.** Method: dark-pixel column clusters in the
  bottom 14% of each page of `interior-book1.pdf` (2550 px wide, page centre 1275), then a visual check
  on a crop of the band at 85.5–90% page height. **Page 6 (verso):** QR icon 150–386, QR text 427–968,
  **folio 1264–1284**, grid label 2244–2395. **Page 7 (recto):** grid label 153–304, **folio 1264–1283**,
  QR text 1581–2123, QR icon 2164–2400. The folio sits at the page centre on both parities and **does
  not mirror at all**; the QR group and the grid-size label do. The crop confirms it by eye: "6" and "7"
  centred, "25 x 25" at the inner margin, QR in the outer corner. The pages that carry **no** frame do
  put the folio in the bottom-outer corner and do mirror it — guide page 2 at 153–172, contents 4 at
  152–173, dividers 5 and 9 at 2376–2395, answer page 10 at 155–200. Mechanism, from the code rather
  than inferred: `_draw_folio`'s own docstring — a framed page gives its outer corner to the QR icon
  (CARD-223), so the folio is drawn at `centred_x`, the trim's own centre (CARD-222). Corrected in the
  card's Renders bullet, in the card's honest-bounds bullet, in the fixture's `changed_pages_note` and
  `why_a_new_baseline`, in the `LIVE_OFFSET` comment and in `_reference`'s docstring.

- **F-105:** the shifted-content failure message interpolates
  `entry.page_number - plan.toc_page_count - TITLE_PAGE_COUNT` — the number the reference is actually
  built at, computed once on the line above and used in both places — and names **CARD-201's shipped
  layout** rather than the pre-CARD-201 one. A stale sibling comment in the same class (the SOLUTIONS
  divider's `first_answer_page` formula, which omitted `TITLE_PAGE_COUNT`) went with it. The class name
  is left alone, as the finding suggests.

- **F-106:** the constant assertion is **deleted**, not replaced. `page_is_right_hand(before_this_card)`
  is a pure function of the literal `5`; the obvious replacement — the same call on
  `decided.pages[0].page_number` — would have read a value the assertion two lines above already pins,
  so it would have been a second claim about the same fact rather than a control. The docstring now
  names the three live assertions that carry the premise instead, including F-101's tightened
  separation assertion, which can only hold if the two positions are opposite hands.

**Claims I wanted to write and did not, because nothing enforces them.** (1) The sweep's own
distribution — nine cases at 10.0/20.0, two at 16.7/26.7, one at 12.95/22.95 — is in this note and
*not* in `PARITY_GUTTER_MM`'s docstring: it is a property of one seeded corpus that no assertion reads,
and the next card to add a case would make it quietly false. (2) The widened guard's own size (6 names,
25 sites) is in this note and not in the test: the test asserts a floor well under it, because the
count is a figure no control could fail on. (3) "Parity never changes a page's usable size" is restated
nowhere new — the existing `_packed_page_is_feasible` and `book_page_spec` docstrings already say it,
and this round's contribution is the measurement above, not another sentence.

**Environment.** Every pytest and `kill_matrix` run in this round was made with
`NONOGRAM_FULL_SUITE_LOCK=/tmp/card206-fix1.lock`; `meta/kanban/.full-suite.lock` was never read,
written, created or deleted. The full suite was **not** run (CARD-259's fix round is live in the
sibling worktree). No timing measurement was taken and no duration is reported. Every mutation target
was a file inside this worktree, backed up with `cp -p` and restored by the instrument with `diff -q`
and `shasum -a 256` verification.

---

### [Fix 1] All six closed, none dismissed — and it took the harder route on F-102

Commit `91a51395`, 5 files, +438/−55. Agent's own impact run: 2074 passed, 5 skipped, 0 failed over 35
files, plus a 290-passed confirmation re-run over the edited files. The orchestrator's independent
109-file gate is recorded separately below.

**F-102 — route taken: WIDEN THE GUARD, not narrow the claim.** Of the two routes offered, this is the
one that makes the card's universal claim *enforced* rather than retracted.

- **The duplicate is gone.** `interior_stream` now computes `first_answer_page` **once** — the derived
  expression hoisted to where the bare `3 + len(section)` sat, the later duplicate deleted. Verified:
  one assignment at `:6718`, zero occurrences of the literal form.
- **The probe's requirement was measured, not assumed.** `page_spec(n)` over positions 1..20 differs in
  **exactly one dataclass field — `parity`**; usable area is one value (190.500 × 253.492 mm) and
  `page_frame` one size (2550 × 3300 px) for every n. `_degrade_infeasible_packed_pages` returns an
  identical plan on odd and even for all three of its branches, and over `page_spec(1..20)` on two
  books. So the probe needs **a placed spec, not a position** — which is why one honest assignment
  serving both readers is the right shape, rather than a second derivation beside the first. That is
  the question I told the fix to answer rather than copy `:6747` on faith, and it answered it.
- **The guard now derives its sites from the geometry door.** New `_page_position_sites` grows a
  vocabulary to a fixed point from `page_spec`/`book_page_spec` (ADR-0036/R2) through parameters,
  arguments and copies; sites are every binding of a position name plus every expression handed to a
  door. **6 names, 25 sites, 0 offenders**, where the old guard saw 7 guide-counting expressions.
  Newly reached: the title-page loop's `range(1, TITLE_PAGE_COUNT + 1)`, the TOC's
  `TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + 1 + index`, `first_answer_page - 1`, and both walk defaults.
- **The planted-literal control, in both states.** Reverting the derived assignment to
  `3 + len(section)` line-count-preservingly reds **exactly one assertion node** — the guard's own.
  *Domain: `tests/kill_matrix.py` RECORDING pass over `test_book_export_interior_cover.py`, 126
  `ast.Assert` nodes, SHIPPED 0 FAIL of 125 reached at pytest exit 0, child instrumentation off,
  ANY-RED; planted 125 reached, 1 FAIL.* No other assertion in that file sees it, which **reproduces
  cycle 1's refutation** of the old honest bound rather than arguing with it.
- **Two further controls make it ADR-0039/R1-shaped:** the enumeration with **no door in its seed set
  reports nothing at all** (caught-with / missed-without), and a planted literal in a source the test
  owns is reported as exactly `[('assignment','first_answer_page',[3])]` while its derived twin is not.
- `TITLE_PAGE_COUNT`'s docstring now names that control instead of asserting an unenforced universal,
  and the class docstring states what remains unseeable: a position from another module, and a wrong
  position spelled `0` or `1`.

**F-101 — the figure now has a control, and the decision about what to state is the right one.**
Re-derived through `_expected_drawing_left_mm` over all 12 cases × both `is_lower`: **10.0000/20.0000
for nine cases, 16.7000/26.7000 for two, 12.9500/22.9500 for one** — and `20.4500/30.4500` nowhere.
The **difference is 10.0000 mm on all 24 readings, maximum deviation 0.0**. So the docstring states
**only the difference**, because no absolute pair describes the corpus — a left edge is that page's own
margin plus half the drawing's own spare, which varies by case. `:1026`'s stale "5.0 mm away" deleted.

The assertion was **tightened from a `> 4.0` floor to an exact equality** — `:1123` now holds
`abs(abs(right_hand_mm - left_hand_mm) - separation_mm) < 1e-6` against
`PARITY_GUTTER_MM - PARITY_OUTSIDE_MM`, per case. Mutant `MODEL_DRIFT` (the `left_margin` right-hand
branch `gutter_mm → gutter_mm + 5.0`) kills **exactly that assertion and nothing else**; *domain:
RECORDING pass over the one parity test, 52 `ast.Assert` nodes, SHIPPED 0 FAIL of 11 reached, ANY-RED;
mutant 11 reached, 1 FAIL at `:1122`.* **The old floor survives that mutant** — which is precisely how
one quantity carried three readings for a whole cycle.

*Orchestrator note, since I raised it and was wrong:* `:1131`'s surviving `assert separation_mm > 4.0`
is **not** a reintroduced constant assertion. It is a precondition guard on the corpus's own
parameters — it reds if a future edit to `PARITY_GUTTER_MM`/`PARITY_OUTSIDE_MM` makes the two hands
indistinguishable, which is what its message claims — and the tightened equality above it is the
control for the measurement. Unlike F-106's deleted assert, it is falsifiable by an edit to the thing
it guards. Recorded because I checked it on suspicion and the suspicion did not survive the code.

**The class sweep found a SEVENTH bad figure, and deleted it rather than restating it.**
`tests/test_book_pdf_memory.py`'s "1186 px against 1191 px on the two-up page": measured, the ink-bbox
crop is **(2251, 2948) at both parities and both shifts**. The parenthetical is gone and the sentence
narrowed to what is true; the *design* it explained (even shift plus `test_the_comparison_has_teeth`)
was certified in cycle 1 and left untouched. Everything else reproduced: page counts 0→3, 1→8, 3→12,
7→20 with all three figures agreeing; baseline **14 pages / 3,468,586 bytes**; AC-288's 39+43 = 150 and
+1 medium = 151; the band edge's 71 puzzles / 70 pages = 150.

**F-103/F-104 — the folio was measured, with the method, and the mechanism explained from code.**
Dark-column clusters in the bottom 14% of the rendered interior, then a visual check on a band crop:
page 6 QR 150–386 / 427–968, **folio 1264–1284**, label 2244–2395; page 7 label 153–304, **folio
1264–1283**, QR 1581–2400. The folio is **centred and does not mirror**; only the QR group and the
grid-size label do. And the reason, from the code rather than from the pixels: a **framed** page gives
its outer corner to the QR, so `_draw_folio` is called with `centred_x` (CARD-222/223) — while
**unframed** pages do carry an outer-corner folio (guide 2 at 153–172, TOC 4 at 152–173, dividers 5/9
at 2376–2395, answer 10 at 155–200). Corrected in the card's Renders bullet and honest bounds, the
fixture's `changed_pages_note` and `why_a_new_baseline`, the `LIVE_OFFSET` comment and `_reference`'s
docstring — five texts for one measurement, which is the doubling this board keeps paying for.

**F-105** — the message now interpolates the real expression and names CARD-201's shipped layout; a
stale sibling comment (the SOLUTIONS-divider formula missing `TITLE_PAGE_COUNT`) was fixed with it.
**F-106** — the constant assertion **deleted, not replaced**, because the obvious replacement would
have re-read a value the assert two lines above already pins; the docstring names the three live
controls that carry the premise instead.

**Fixture integrity checked, and it answers whether new renders were owed:** only `why_a_new_baseline`
and `changed_pages_note` changed in `book_baseline_card206.json`; `pages`, `interior_bytes` and
`page_count` are byte-identical against HEAD by JSON comparison, and the memory suite's digest
comparisons are green. So the hoist changed no exported byte and **no new renders were owed**.

**Claims it wanted to write and did not:** the 9/2/1 case distribution and the guard's own size (6
names, 25 sites) are in these notes rather than in docstrings, because no assertion reads either.
"Parity never changes a page's usable size" was not restated anywhere new — the existing docstrings
already say it and this round added the measurement instead of another sentence.

---

### [Build gate — fix 1] PASSED: 5910 passed, 16 skipped, 0 failed, EXIT=0

Same 109-file selection as the pre-fix gate, re-derived rather than reused, at `91a51395`. **5907 →
5910**: the three added tests are the widened guard's own controls — the bare-literal scan, the
no-door-in-the-seed-set control, and the planted-literal-versus-derived-twin discrimination. The 16
skips are `db_required`/browser, green. Build-fix attempts remain **1 of 2** (the earlier repair);
this round needed none.

---

### [Review 2/3] Score: 8.6 — above the threshold, but **1 Important gates.** Certification ran. **Not escalated.**

Report: `meta/review/20261022T013915Z-CARD-206-cycle2.yml`. 1 high (gating), 3 low. 7.5 → 8.6. The
score clears `min_score: 8`; the **loop's success condition does not**, because it requires zero
surviving critical/important. Cycle 3 is required.

**[Family] The detector does NOT escalate, and I checked the arithmetic this time.** The reviewer
reported it as firing "unambiguously". Its *observation* is correct and important — cycle 1's gating
F-102 was a universal about page positions whose declared blind spot did not describe the real one, and
fix 1 closed that defect and then **reproduced its shape in the mechanism it built to close it**. But
`cmd-start-review.md:1596-1629` needs `family_regression_streak >= 2`, and the streak increments once
per cycle whose gating findings are fix-attributed: cycle 1's two were attributed to the implementation
(no prior fix existed), cycle 2's one is attributed to fix 1 — **streak 1**. One more such cycle would
escalate; this one does not. The reviewer's own recommendation agrees, for a different and good reason:
the sibling card escalated after *adding* a sentence in each of two rounds, whereas this round deleted
two claims, deleted a figure, tightened an assertion, and added one mechanism with three controls, two
of them certified here by mutant.

**F-201 (high, gating) — the widened guard fails OPEN, and the bound that should say so is wrong.**
This is ADR-0039/R2's **second** clause, which cycle 1 never reached: *a shape it cannot analyse is a
FAILURE, never a silent pass.* Cycle 1 checked only the first clause ("derived, not hand-written"),
which still holds.

The reviewer re-derived the reported triple exactly — **6 names, 25 sites, 0 offenders**, old walk still
7 expressions — then attacked the fixed point by planting nine line-count-preserving shapes into the
real module's own text (in memory; nothing on disk mutated), each hiding the literal `3`:

```
CAUGHT   V0  bare literal (the proven control)      ESCAPED  V1  list container + subscript
ESCAPED  V2  dict container                         ESCAPED  V3  tuple-unpack assignment
ESCAPED  V4  augmented assignment (+= 3)            ESCAPED  V5  functools.partial onto the door
CAUGHT   V6  keyword-only call into the door        ESCAPED  V7  comprehension target
ESCAPED  V8  attribute assigned in this module      ESCAPED  V9  starred call
```

**8 of 9 escape, with 0 offenders reported.** The causes are mechanical missing branches: `Assign` with
a Tuple target is skipped (Name-only), `AugAssign` is not in the site walk, an `ast.comprehension`
target is not either, and a value reached through `Subscript`/`Starred`/`Attribute`/`partial` never
becomes a `Name` and so never enters the vocabulary. Also ADR-0039/R3: the test asserts **floors**
(`>= 18`, `>= 4`) against a real 25 and 6, with no equality and no failing control for any bound.

And **one sentence of the declared bound is false.** It says *"where that attribute was set is a site in
its own right, but only if it was set in this module"* — V8 is `self.page_number = 3 + len(section)`,
set in this module, and it is **not** a site. The paragraph is headed "measured rather than assumed" and
measures nothing.

**No live defect**: the module has 0 offenders and all 25 sites are derived. What gates is that the
card's universal claim is over-broad **again**, in the mechanism built to make it true.

**What held, and two of them are better than fix 1 claimed:**
- **The parity equality holds on all 24 readings**, not only the common nine — 10.0/20.0 on nine cases,
  16.7/26.7 on two, 12.95/22.95 on one, distinct differences `{10.0}`, maximum deviation **0.0**. The
  figure is correct and narrow.
- **Bound (a) is honest and now has a number the card did not have:** an AST census finds **23**
  `page_spec`/`book_page_spec` calls across **5** modules, 18 of them inside the generator itself, and
  of the remaining five only `book_proof.py:767` passes a non-trivial position — `enumerate(PROOF_PUZZLES,
  start=1)`, a standalone proof document with no front matter. **No module outside the generator computes
  a front-matter-relative interior position today.**
- **The five-texts problem is resolved:** all six sites agree and none says bottom-left for a framed
  page. The two remaining "bottom left" strings are correct (one is the verbatim cycle-1 record, one is
  about unframed page 2), and the four "opposite bottom corner" assertion messages are all about
  unframed pages. The reviewer notes the structural point still stands: **one measurement, six prose
  homes, zero assertions reading any of them.**
- **Fix 1's src change strictly strengthened the card**, which neither I nor fix 1 had noticed:
  `first_answer_page` is now live in the exported output (`:6976`, `:6978`), so the behavioural
  monkeypatch case **can** now see it — cycle 1 had measured that it could not.
- All six of cycle 1's findings genuinely closed, each re-derived from code rather than from the
  `fix_note`. The reviewer **agrees with my reading of `:1131`** (not a reintroduced constant assertion)
  and adds that it is now logically *subsumed* by the exact equality above it — redundant, not wrong,
  deliberately not filed.

**Certification ran** — the deferred half, with the instrument, RECORDING pass, ANY-RED, child
instrumentation off, SHIPPED re-run and equal cell-for-cell between mutants. Baselines: 126 assert
nodes over the cover file (0 FAIL of 125 reached) and 52 over the parity test (0 FAIL of 11 reached).
Seven mutants: the literal-for-constant, the nearly-white page (**killed at 8 nodes**, including AC-1's
no-ink and AC-5), the planted literal (**exactly 1 node** — the guard's own), the seed-independence
control, the exemption's must-not-absorb control, the model-drift mutant reproducing fix 1's claim
independently, and a parity-blind production mutant.

**One domain caveat the reviewer surfaced rather than hid:** the literal-for-constant mutant read
**exit 1 with 119 reached and 0 FAIL** — a kill *outside* the assert matrix's domain, which is exactly
the ambiguity `tests/README.md` names. Re-run as plain pytest under a verified restore, the kill is
production's own page-count guard raising `RuntimeError: interior has 12 pages, its page plan says 14`.
Recorded in both domains rather than quoting a blank matrix.

**F-202 (low)** — the parity equality is an identity of the test's *own* model, so a parity-blinded
production mutant leaves it alone and is caught by the two ink arms instead. **F-203 (low)** —
`GEOMETRY_DOORS`' second member is **inert**: `book_page_spec(book, page_number=1)`'s `args[0]` is the
book, and `doors=("book_page_spec",)` alone yields **0 names / 2 sites**, so the door-removal control
cannot distinguish a member that carries everything from one that carries nothing. **F-204 (low,
pre-existing)** — four sites spell `GUIDE_PAGE_COUNT` as a bare `2` while the comment above writes the
constant.

---

### [Fix round 2] Review cycle 2's four findings — one gating, all four closed; the guard now fails closed

_Commit `eb5cbd5d`, 3 files, +735/−122. Test files only — no `src/` change, so no exported byte moved._

The rule this round worked to, from the sibling card's escalation: **prefer deleting or narrowing a
claim over adding one, and any claim added ships with its failing control in the same commit.** The
one genuinely new mechanism is a refusal, and it is asserted rather than described.

**All four closed, none dismissed.**

- **F-201**: the page-position walk now **fails closed** — binding occurrences derived from the
  module's own store contexts, a `(node, field)` string closure over the grammar, six loud refusal
  classes, equalities in place of all three floors, and one named exemption with its own control —
  *proved by* mutant **A3_TUPLE_UNPACK_SHAPE** (F-201's V3, which reported 0 offenders in cycle 2)
  now reddening `:2018` on disk, by **A2_SITE_ADDED** reddening the site-count equality and nothing
  else of 134 nodes, by **A4_DOOR_SLOT_REVERTED** reddening 10 nodes, and by the sixteen-row shape
  table in which **nothing escapes silently**.
- **F-202**: the separation comment narrowed to say it pins the test's **own model**, with the
  production parity claim re-credited to the two ink arms — *proved by* **B1_PARITY_BLIND**
  (production `_parity` always ODD) reddening `:1139` and `:1144` while `:1127` survives, and
  **B2_MODEL_DRIFT** reddening `:1127` alone.
- **F-203**: each door's position slot is now the index of `page_number` in **that door's own
  signature** (`book_page_spec` → slot 1, the book is slot 0), a door without such a parameter is a
  refusal, and `test_each_geometry_door_carries_a_site_of_its_own` asserts per member that the full
  set reports a site the set without it does not — *proved by* the per-member measurement
  (`("page_spec",)` loses `:3163`; `("book_page_spec",)` loses the five `door argument` sites) and
  by mutant **A4**.
- **F-204**: the four literal `2`s at `tests/test_book_pdf_memory.py:3073, :3095, :3469, :3480` are
  `GUIDE_PAGE_COUNT` — *proved by* the 129-file impact run staying green with the constant
  substituted (the value is identical at today's constants, which is exactly why it was invisible).

**F-201 (high, gating) — route taken: FAIL CLOSED, not eight more branches.**

Why not branches: the finding says it in one line — adding a branch per escaping shape makes V1–V9
caught and leaves V10 silent, which is the same defect one iteration later and the second instance of
the family. So the walk was rebuilt around two closures that have no "shape I thought of" in them:

- **The binding closure.** Sites are no longer produced from a list of statement kinds. Every
  *binding occurrence* of a position name is found from the module's own store contexts
  (`ast.Name`/`ast.Attribute`/`ast.Subscript` with a non-`Load` ctx, decomposed through `Tuple`/
  `List`/`Starred` targets), and the binder it sits in is looked up in `BINDERS_READ`. A binder that
  is not in that table is a **refusal** naming the line and the shape, not a pass.
- **The string closure.** Every node in the tree is scanned for a field holding a position name as a
  bare string; the `(node class, field)` pairs the walk reads are `STRING_FIELDS_READ`
  (`Name.id`, `Attribute.attr`, `keyword.arg`, `arg.arg`) and **everything else is a refusal**. That
  is what catches `MatchAs.name`, `alias.asname`, `Global.names`, `ExceptHandler.name` and anything
  else the grammar grows, without one of them being written down as a branch.

Four more refusals close the remaining ways a value can leave a position without a binding:
a geometry door **referenced without being called** (a `functools.partial` of it), a door **called
with nothing in its position slot**, a position **computed through a call the walk cannot follow**,
and a position that is a **parameter of something that is not a `def`** (a lambda).

And three reductions of refusal noise, each of which also closes one of F-201's shapes rather than
being added for comfort: an `Attribute` load is followed by its own name and an attribute **store**
of a position name is a site (so V8 is caught and the sentence that F-201 measured false is now
true); a `Subscript`/`Starred` is followed to its base, so a container and a star-call are
analysable instead of opaque; and a module-level name bound to an integer literal is read as that
literal unless it is one of the two declared `FRONT_MATTER_CONSTANTS`.
**The nine-shape table, re-run — and six more.** Every shape is planted line-count-preservingly
into a copy of `book_pdf_generator.py`'s own text held **in memory** (nothing on disk is mutated for
this), each hiding the literal `3` in a page position. It is
`TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage.PLANTED_SHAPES`, and
`test_every_planted_position_shape_is_caught_or_refused` asserts the outcomes as an exact table, so
an empty outcome — a silent pass — reds.

| shape | cycle 2 | now | how |
| --- | --- | --- | --- |
| V0 bare literal (the proven control) | CAUGHT | **CAUGHT** | offender `assignment/first_answer_page [3]` |
| V1 list container + subscript | ESCAPED | **CAUGHT** | subscript followed to its base; `_slots = [3 + len(section)]` is the site |
| V2 dict container | ESCAPED | **CAUGHT** | same, `assignment/_slots [3]` |
| V3 tuple-unpack assignment | ESCAPED | **CAUGHT** | binding closure, target decomposed through `Tuple` |
| V4 augmented assignment (`+= 3`) | ESCAPED | **CAUGHT** | `AugAssign` is a binder in `BINDERS_READ` |
| V5 `functools.partial` onto the door | ESCAPED | **REFUSED** | "a geometry door referenced without being called" |
| V6 keyword-only call into the door | CAUGHT | **CAUGHT** | offender `door argument/page_spec [3]` |
| V7 comprehension target | ESCAPED | **CAUGHT** | `ast.comprehension` is a binder; site is its `iter` |
| V8 attribute assigned in this module | ESCAPED | **CAUGHT** | attribute store of a position name is a site — which is what makes F-201's false sentence true |
| V9 starred call into the door | ESCAPED | **CAUGHT** | star followed to its base; `_args = [...]` is the site |
| V10 `match`/`case` capture | — | **REFUSED** | "a position name held in `MatchAs.name`" |
| V11 `import os as first_answer_page` | — | **CAUGHT + REFUSED** | offender on the next line **and** "held in `alias.asname`" |
| V12 `with … as` target | — | **CAUGHT + REFUSED** | `withitem` is a binder; the call it wraps is also refused |
| V13 lambda parameter default | — | **REFUSED** | "a position as a parameter of a `Lambda`" |
| V14 return value of a module function | — | **REFUSED** | "a position computed through a call this walk cannot follow" |
| V15 page count behind a module-level name | — | **CAUGHT** | `_HIDDEN_FRONT_MATTER = 3` read as its literal |

**Nothing escapes silently. Eight of V1–V9 did before this round; zero do now.** V10–V15 are shapes
the walk has no branch for and are caught by the closures, which is the point: V10, V13 and V14 are
each a shape I did not design a branch for, and each reds.
**What the walk follows and what it refuses, derived rather than remembered.** Neither list is prose
in a docstring: both are class data the walk reads, and the refusals are what the walk emits when a
shape is in neither.

- **Followed — binders** (`BINDERS_READ`, with the field each site is taken from): `Assign.value`,
  `AnnAssign.value`, `AugAssign.value`, `For.iter`, `AsyncFor.iter`, `comprehension.iter`,
  `NamedExpr.value`, `withitem.context_expr`. Binding occurrences are found from the module's own
  store contexts (`Name`/`Attribute`/`Subscript` with a non-`Load` ctx, decomposed through
  `Tuple`/`List`/`Starred`), **not** from this list — so the list is what is *read*, and anything
  else a store sits in is refused.
- **Followed — references**: a `Name` by its id, an `Attribute` by its own attr (so `plan.page_number`
  is analysed rather than exempted — the exemption F-201 predicted would be needed is not),
  a `Subscript` and a `Starred` by their base.
- **Followed — string fields** (`STRING_FIELDS_READ`): `Name.id`, `Attribute.attr`, `keyword.arg`,
  `arg.arg`. Measured: removing `arg.arg` from that set produces **14 refusals** on this module, so
  the set member is not decorative.
- **Refused, loudly, with file, line, shape and source segment** — six classes:
  1. a position bound in a binder `BINDERS_READ` does not name (V3/V4/V7/V12 would be here if the
     binder were missing; V10's `MatchAs` reaches class 2);
  2. a position name held as a bare string in a `(node, field)` pair `STRING_FIELDS_READ` does not
     name — `MatchAs.name`, `alias.asname`, `Global.names`, `ExceptHandler.name` (V10, V11);
  3. a geometry door **referenced without being called** (V5);
  4. a geometry door **called with nothing in its position slot**;
  5. a position **computed through a call the walk cannot follow** (anything that is not a builtin,
     V14);
  6. a position that is a **parameter of something that is not a `def`** (V13), and a door whose own
     signature has no `page_number` parameter to seed a slot from.

  On the module as it stands: **0 refusals.** The reviewer's predicted first exemption
  (`plan.page_number` at `:5401`) is not one — attributes are followed.

**The equalities that replaced the floors (ADR-0039/R3), and what reds.** `>= 18` sites and `>= 4`
names are gone, and so is the third floor in the same class that neither cycle filed (`>= 6`
guide-counting expressions):

| was | is | what reds |
| --- | --- | --- |
| `len(sites) >= 18` | `len(sites) == 23` (`POSITION_SITE_COUNT`) | a site appearing or vanishing — measured: mutant **A2_SITE_ADDED** |
| `len(vocabulary) >= 4` | `tuple(vocabulary) == POSITION_NAMES` (6 names, by name) | a position name appearing, vanishing or being renamed |
| `len(sites) >= 6` (guide-counting) | `== 7` | the same, on the older half of the guard |
| — | `refusals == []` | any shape the walk cannot follow |
| — | `_bare_literals(sites) == []` | a page count spelled as a literal anywhere in a position |
**The one exemption that remains, and its control in both states.** `EXEMPTION`: a term of a
position expression that is itself a **non-position** name or attribute (a local count, a parameter,
an attribute of a plan) is read for the literals written in the expression and **not** followed into
its own bindings. It is the only shape still allowed silently, and it is a parameter of the analyser
(`follow_terms`), not a comment:

- **Cost, measured and asserted, not declared**
  (`test_the_exemptions_cost_on_this_module_is_the_measured_one`): removing it reds on **5 of the
  module's 23 sites**, over exactly the four terms `index`, `pages`, `section`, `toc_page_count`.
  That is why it exists, and the figure is an equality so it cannot go stale behind the docstring.
- **Control, in both states** (`test_the_one_exemption_does_not_absorb_what_it_must_not`): a source
  the test owns puts the front-matter count behind a local — `hidden = 3; first_answer_page = hidden
  + len(section)`. With the exemption **removed** the walk reports
  `('assignment', 'first_answer_page', [('not followed', 'hidden'), ('not followed', 'section')])`;
  with it **in place** it reports nothing. Caught without, missed with — ADR-0039/R3's shape, on the
  exemption itself.

**F-203 — the second door now carries what it claims, and each member has a control that reds.**
`GEOMETRY_DOORS`' position slot is no longer a hard-wired `args[0]`; `POSITION_PARAMETER =
"page_number"` and each door's slot is the **index of that parameter in that door's own signature**,
read from the signature — the local `FunctionDef` for `page_spec` (slot 0 after `self`), and for
`book_page_spec` the `ImportFrom` in the module's own text resolved to
`src/nonogram/admin/book_page_spec.py` and parsed (slot **1**, because `args[0]` is the book). A door
whose signature has no such parameter is a **refusal**, so the set cannot hold an inert member
silently again.

Measured, per member:

| doors | names | sites | what the full set has that this does not |
| --- | --- | --- | --- |
| `("page_spec", "book_page_spec")` | 6 | **23** | — |
| `("page_spec",)` | 6 | 22 | `:3163 door argument book_page_spec` |
| `("book_page_spec",)` | 6 | 23 | the five `door argument page_spec` sites at `:4022 :4074 :6449 :6826 :6867` (reached, but as indirect `argument` sites rather than door arguments) |
| `()` | 0 | 0 | everything |

`test_each_geometry_door_carries_a_site_of_its_own` asserts, **per member**, that the full set
reports a site the set without that member does not. Mutant **A4_DOOR_SLOT_REVERTED**
(`POSITION_PARAMETER` → `"no_such_parameter"`) reds it, together with the two equalities and the
refusal assertion.

**F-202 — one narrowed sentence, no new mechanism.** The comment above
`tests/property/test_book_export_interior.py`'s separation assertion used to frame the quantity as a
property of production geometry. It now says what that assertion pins and what it does not: the
module's **own millimetre model**, both readings coming from `_expected_drawing_left_mm`, whose two
branches differ by `gutter - outside` whatever the puzzle — so it reds on a drift in that function or
in the two `PARITY_*` constants and **not** on a production parity failure. The production claim is
credited to the two ink arms below it, which read the page's own drawing.

**F-204 — the four literal `2`s are the constant.** `tests/test_book_pdf_memory.py:3073, :3095,
:3469, :3480` now read `1 + TITLE_PAGE_COUNT + GUIDE_PAGE_COUNT + plan.toc_page_count + …`, the
formula the comment above the first of them already wrote. `GUIDE_PAGE_COUNT` was already imported in
that file (`:159`), so nothing else changed.
**Certification, with the instrument — `tests/kill_matrix.py`, RECORDING pass, aggregate ANY-RED,
child instrumentation off, SHIPPED re-run between mutants.** Two groups, six mutants, every target a
file inside this worktree, every restore the instrument's own `cp -p` + `diff -q` + `shasum -a 256`
and confirmed afterwards by `git diff --stat` reading the same three files.

*Group A — DOMAIN: RECORDING pass over `tests/test_book_export_interior_cover.py`, **134
`ast.Assert` nodes**, SHIPPED **0 FAIL of 133 reached** (pytest exit 0, 76 collected tests).* One
node (`:621`) is NOT-REACHED on SHIPPED and on every mutant alike — a pre-existing unreached arm,
not moved by this round.

| mutant | what it changes | FAIL (exit 0, 133 reached) |
| --- | --- | --- |
| **A1_PLANTED_LITERAL** | production: the derived `first_answer_page` back to `3 + len(section)` | **4** — `:2018` the module's bare-literal check, `:1202` the guide-counting equality, `:2038` + `:2056` the shape table announcing its plant no longer applies |
| **A2_SITE_ADDED** | production: one extra `page_number = first_answer_page` on the same three lines | **1, exactly `:1966`** — the site-count equality, and nothing else in 134 nodes sees it. **This is the teeth the floor did not have.** |
| **A3_TUPLE_UNPACK_SHAPE** | production: F-201's **V3**, the shape fix 1's walk reported **0 offenders** for | **4** — `:2018` (the offender assertion), `:1202`, `:2038`, `:2056`. The silent shape now reds on disk, not only in memory. |
| **A4_DOOR_SLOT_REVERTED** | test: `POSITION_PARAMETER` → `"no_such_parameter"`, so no door can be seeded | **10** — `:1964` refusals, `:1965` the names, `:1966` the count, `:2001` the per-door control, `:2056` the table, `:2074`/`:2080` the planted-literal control, `:2105` the exemption control, `:2135`/`:2136` the exemption's cost |

*Group B — DOMAIN: RECORDING pass over
`tests/property/test_book_export_interior.py::test_PropertyTest_BookExport_ParityCountsFromTheTitlePage`,
**52 `ast.Assert` nodes**, SHIPPED **0 FAIL of 11 reached** (pytest exit 0, 1 collected test).*

| mutant | what it changes | FAIL (exit 0, 11 reached) |
| --- | --- | --- |
| **B1_PARITY_BLIND** | production `book_page_spec._parity` → `ODD` for every page | **2** — `:1139` and `:1144`, the two **ink arms**. `:1127` (the separation equality) **survives**, and so does `:1135`. |
| **B2_MODEL_DRIFT** | the test's own model, `gutter_mm` → `gutter_mm + 5.0` on the right-hand branch | **1** — `:1127` and nothing else |

So F-202's reading reproduces independently: the separation equality's domain is the model, the
production parity claim is carried by `:1139`/`:1144`, and the narrowed comment now says exactly
that. No mutant killed outside the assert matrix's domain this round (every reading is exit 0 with a
FAIL cell, so there is no second domain to record).
**Net prose change, measured.** Comment and docstring lines in the three edited files, HEAD against
this round (distinct lines, so a re-indent is not counted twice):
**+149 / −50, net +99** — all of it in `tests/test_book_export_interior_cover.py` (+139/−44) and
`tests/property/test_book_export_interior.py` (+10/−6); `tests/test_book_pdf_memory.py` is
prose-neutral. The split in the cover file: **+64/−6 `#:` attribute documentation** (every line of
it documenting a class datum the tests read — `BINDERS_READ`, `STRING_FIELDS_READ`,
`POSITION_PARAMETER`, `FRONT_MATTER_CONSTANTS`, `EXEMPTION`, `PLANTED_SHAPES`, `POSITION_NAMES`),
**+72/−33 docstrings**, **+30/−5 inline comments**. One trimming pass was made after the first
measurement (+116 → +99) specifically to delete prose that restated what a test already asserts.

So prose is **up**, and the round's own rule asks why. The answer is that the new mechanism is a
refusal and `PLANTED_SHAPES` is a sixteen-row table of measured outcomes, both of which are data the
tests read rather than claims about the code — and that every sentence added names one of them or a
test that reds. What was deleted is the part that had no control:

- **Deleted:** the universal "enumerates **every page position in the module**"; the whole paragraph
  headed "What this still cannot see, **measured rather than assumed**" — including the sentence
  F-201 measured **false** ("where that attribute was *set* is a site in its own right, but only if
  it was set in this module"), which V8 now makes true and which is gone anyway; and the comment
  "The count itself is not asserted: it is a figure no control could fail on", the reasoning F-201
  inverted.
- **Narrowed:** the class docstring's reach paragraph points at the data and the tests rather than
  describing a reach; the bound it still declares is two items, both outside the enumeration by
  construction. The F-202 comment was narrowed from a production claim to a model claim with the
  production claim re-credited to the two ink arms.

**Claims I wanted to write and did not.** (1) "The walk is complete over the grammar" — it is not,
nothing could enforce it, and what *is* enforced is that an incompleteness is a refusal; so that is
what the docstring says instead. (2) The per-door site diffs (which sites each member uniquely
contributes) are in this note and not in the test: the test asserts the difference is **non-empty**
per member, which is the part a control can fail on, and naming the five sites would be a figure
that moves with any edit to the module. (3) "No module outside the generator computes a
front-matter-relative interior position" — cycle 2 measured it (23 calls, 5 modules, `book_proof.py:767`
the only non-trivial one) and it stays in the orchestrator's own `[Review 2/3]` note and the card's
`### Honest bounds`, not in a docstring, because no assertion reads it.
**Impact run.** The 129 test files under `tests/` and `tests/property/` whose names carry `book`,
`admin`, `pdf`, `export`, `layout`, `card_` or `cli`, plus `tests/test_guard_integrity.py`,
`tests/test_suite_profile.py` and `tests/test_kill_matrix.py` (the instrument's own tests, because
this round used it): **4,830 passed, 12 skipped, 0 failed, 0 errors, pytest exit 0**, in one run
after the last change. The 12 skips are `db_required`/browser. The full suite was deliberately **not**
run; the orchestrator's own 109-file gate is the gate.

**No render is owed, and this is checkable rather than asserted.** Fix round 2 changes **test files
only** — `git diff --name-only 91a51395..` is three paths, all under `tests/`, and
`src/nonogram/**` and `tests/fixtures/book_baseline_card206.json` are untouched. So no exported byte
can have moved and the cycle-1 artefacts under
`/Users/omelnikova/Documents/nonogram-reviews/CARD-206/` still describe this head. G-2 holds for the
same reason (`src/nonogram/export/layout.py` is not in the diff), and the three CON-019 byte-identity
tripwires were neither edited nor red.

**Environment.** Every pytest and `kill_matrix` run in this round was made with
`NONOGRAM_FULL_SUITE_LOCK=/tmp/card206-fix2.lock`; `meta/kanban/.full-suite.lock` was never read,
written, created or deleted. No timing measurement was taken and no duration is reported. Every
mutation target was a file inside this worktree; the instrument's `cp -p` backup, `diff -q` +
`shasum -a 256` verification and `finally` restore did the mutating, and after each group
`git diff --stat` read the same three test files and a clean `src/`.

**Family, for the next cycle's arithmetic.** This round added **no** claim without a control in the
same commit, deleted two claims and one false sentence, replaced three floors with equalities, and
the one new mechanism (the refusal) ships with six measured refusal classes, a sixteen-row shape
table, a per-member door control, an exemption control in both states and an exemption-cost
equality — four of them fired by mutants A1–A4 above. If cycle 3 finds a gating finding of F-102's
family again, the streak reaches 2 and the card escalates; nothing in this round repeats the shape,
because the claim the mechanism makes is now narrower than the mechanism.

---

### [Fix 2] All four closed — and it chose closures over branches, which is the right answer

Commit `eb5cbd5d`, 3 files, +735/−122, **test files only**: `src/nonogram/**` and
`tests/fixtures/book_baseline_card206.json` untouched, so no exported byte moved and **no render is
owed**. Agent's own impact run: **4,830 passed, 12 skipped, 0 failed** over 129 files.

**F-201 — it did not add eight branches, which is what I asked for and the harder path.** The two causes
of the fail-open were structural, so both were replaced by closures that contain no "shape I thought
of":
- **Binding closure** — sites come from the module's own store contexts (`Name`/`Attribute`/`Subscript`
  with non-`Load` ctx, decomposed through `Tuple`/`List`/`Starred`), and the binder they sit in is
  looked up in `BINDERS_READ`. **A binder not in that table is a refusal.**
- **String closure** — every node is scanned for a field holding a position name as a bare string, and
  only the four `(class, field)` pairs in `STRING_FIELDS_READ` are read. **Everything else is a
  refusal** — which is how `MatchAs.name`, `alias.asname`, `Global.names` and `ExceptHandler.name` are
  covered without any of them being a branch.

**Six refusal classes**, each reddening with line, shape and source segment, and `refusals == []` is now
asserted. That is ADR-0039/R2's second clause satisfied where the ADR puts it.

**The nine shapes re-run, plus six the agent invented — and I verified a seventeenth it did not.**
8 of the 9 that escaped silently in cycle 2 are now CAUGHT, V5 is REFUSED, and **nothing escapes
silently at all**. Three of its own six (a `match`/`case` capture, a lambda parameter default, a module
function's return value) are shapes it wrote **no branch for** and the closures catch — which is the
whole point of the design.

**My independent check, because a table of shapes the author chose is not evidence that the closure
generalises.** I planted `setattr(self, "page_number", 3 + len(section))` — a position name hidden in a
**string constant** argument, a shape absent from all sixteen rows and from `STRING_FIELDS_READ`. Result:
**exit 1**, two tests red (`test_the_page_position_set_is_derived_from_the_one_geometry_door` and
`test_every_planted_position_shape_is_caught_or_refused`), line count preserved at 7216, file restored
byte-identical (`d8b9ece8…`, `diff -q` clean). **The closure holds on a shape nobody designed for.**

**The floors became equalities (ADR-0039/R3)** — `len(sites) == 23`, `tuple(vocabulary) ==
POSITION_NAMES` by name, and `== 7` on the older guide-counting half, **a third floor neither cycle had
filed**. Mutant `A2_SITE_ADDED` (one extra position binding in production, line-count-preserving) reds
**exactly one node of 134** — the site-count equality and nothing else. *That is the teeth the floor did
not have*, demonstrated rather than asserted.

**F-203 — the inert door now carries what it claims.** Each door's slot is the **index of
`page_number` in that door's own signature**, read from the local `FunctionDef` for `page_spec` and, for
`book_page_spec`, from the module's own `ImportFrom` resolved and parsed — **slot 1**, because `args[0]`
is the book. A door without that parameter is a refusal, and a per-member control asserts each door
contributes a site the set without it does not: `("page_spec",)` alone misses `:3163`,
`("book_page_spec",)` alone misses five sites, `()` misses everything.

**The one remaining exemption has its cost asserted, not declared:** a non-position term of a position
expression is read for its written literals and not followed into its own bindings. Removing it
(`follow_terms=True`) reds **5 of the 23 sites** over exactly `index`, `pages`, `section`,
`toc_page_count` — and its control is a test-owned source where the hidden term is **caught with the
exemption removed and missed with it in place**, which is ADR-0039/R3's shape.

**F-202** narrowed in one sentence: the separation equality pins the test's **own millimetre model**,
and the production claim is re-credited to the two ink arms. Confirmed by mutant `B1_PARITY_BLIND` —
blinding production's parity reds the two ink arms and leaves the equality alone, while `B2_MODEL_DRIFT`
reds the equality alone. **F-204** — the four bare `2`s now read `GUIDE_PAGE_COUNT`.

**Prose went UP, and the agent said so plainly rather than burying it: +149/−50, net +99.** It also made
a trimming pass specifically to cut prose restating what a test already asserts (+116 → +99). Its
argument, which I accept but flag for cycle 3: the new mechanism *is* a refusal plus a sixteen-row
measured table, both of which are **data the tests read**, and every added claim ships with its control
in the same commit (the shape table, the per-door control, the exemption's two states, the
exemption-cost equality, and mutants A1–A4). It **deleted** the universal "enumerates every page
position in the module", the entire "measured rather than assumed" paragraph including the sentence
cycle 2 measured false, and "the count itself is not asserted".

This is the correct distinction from the sibling card, and worth recording as such: CARD-259's
deletions-only rule applied because *that* card needed no new mechanism — its defect was purely claims
outrunning enforcement. Here new mechanism was required, so the rule becomes "every added claim ships
with its failing control", which is the same principle with the applicable part kept.

**Three claims it wanted to write and did not**, all in notes rather than docstrings: that the walk is
complete over the grammar (*"it is not and nothing could enforce it"* — the docstring says an
incompleteness is a refusal instead); the per-door unique-site diffs, because the test asserts the
difference is non-empty, which is the part a control can fail on; and cycle 2's 23-calls/5-modules
measurement, because no assertion reads it.

---

### [Build gate — fix 2] PASSED: 5914 passed, 16 skipped, 0 failed, EXIT=0

Same 109-file selection, re-derived at `eb5cbd5d` rather than reused. **5910 → 5914**: the four added
tests are fix 2's own controls — the sixteen-row shape table, the per-door site control, the exemption's
two states, and the exemption-cost equality. The 16 skips are `db_required`/browser, green. Build-fix
attempts remain **1 of 2**, from the original page-count-pin repair; neither fix round needed one.
