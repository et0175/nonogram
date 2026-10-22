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
**Review score:** —
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
- **AC-4's own two expectations**, through
  `tests/property/test_book_export_interior._expected_drawing_left_mm` on that corpus's first
  case: left-hand **20.4500 mm**, right-hand **30.4500 mm**, **10.0000 mm** apart.
  **This re-derivation caught a wrong figure before commit:** the first draft of
  `PARITY_GUTTER_MM`'s docstring said the two parities were "5.0 mm apart … half the 10.0 mm
  difference each side, since FR-032 centres the drawing". That is wrong — parity moves the
  usable area sideways and never changes its size, so centring leaves each side the same spare
  and the **whole** `gutter - outside` lands on the left edge. The docstring now states
  10.0 mm and names the function it was measured through.
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
  first puzzle page: folio "6" and the QR icon at the bottom **left**, the drawing against the
  outside margin with the gutter on its right.
- `spread-guide-pages-2-and-3.png` — pages 2 and 3 side by side: the guide really does face
  itself now (AC-368's premise, which is what CARD-229 depends on).
- `spread-divider-5-and-puzzle-6.png` — the "Easy" divider on 5 and the first puzzle page on 6.

### Honest bounds

- **The AST guard's reach.** `TestBookPdfStructure_NoPositionCountsTheGuideWithoutTheTitlePage`
  enumerates every expression that loads `GUIDE_PAGE_COUNT` (7 sites) and requires each to load
  `TITLE_PAGE_COUNT` too, and that no integer constant in one of them is other than 0 or 1. It
  catches a guide-derived position that forgot the page in front of it. It is **blind** to a
  position written as a bare literal with no constant in it at all — `first_page = 4` would
  satisfy it vacuously. That second shape is covered behaviourally by
  `test_each_position_is_counted_from_the_constant_not_a_literal` (M3 is exactly it). Stated in
  the test's own docstring.
- **What the monkeypatch case cannot see.** `puzzle_pages`' and `puzzle_section`'s **default**
  `first_page` arguments are bound at import time, so moving `TITLE_PAGE_COUNT` at run time does
  not reach them. Production never relies on either (`section_plan` passes its own
  `first_page`); their value is read by the AST guard instead. Stated in the test's docstring.
- **`book_baseline_card206.json` has no control page** — the first recording in that chain for
  which that is true. Every page differs from CARD-224's recording shifted by one, because every
  page's folio reads one number higher and moves to the opposite bottom corner (the folio sits
  in the bottom *outer* corner, and the grid-size label and QR group mirror with it). The
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
