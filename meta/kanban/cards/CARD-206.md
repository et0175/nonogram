# CARD-206: The interior opens with a blank title / copyright page, ahead of the guide

**Status:** in_progress
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
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_page_numbers.py, tests/test_book_export_interior_cover.py, tests/property/test_book_export_interior.py, tests/test_book_toc.py
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
