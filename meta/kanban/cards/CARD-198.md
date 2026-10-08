# CARD-198: The book's answer key becomes one full solved page per puzzle, replacing the compact 6-up grid

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/198-answer-key-one-page-per-puzzle
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-198
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-07 (owner decisions on the book's answer-key replacement)
**Idea:** —
**Wave:** 37
**Depends on:** CARD-197, CARD-199
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_answer_key.py, tests/test_book_finalise_gutter.py, tests/test_book_pdf_memory.py, tests/test_book_solved_answer_key.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card198.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code; CARD-197 not yet merged, read as its
drafted file).**

- `BookPDFGenerator.answer_key` (`book_pdf_generator.py:1897-1959`) packs every drawable
  puzzle's `Answer` (number, extent, level) through
  `book_answer_key.pack_answer_pages` (`book_answer_key.py:293-355`) into `AnswerPage`s —
  6-up while every answer is <=20 cells on its longest side, 4-up once one is longer
  (`page_capacity`, `SIX_UP`/`FOUR_UP`, `book_answer_key.py:172-182`), one page per level
  boundary even with room left (`AnswerPage.heading`, `level_heading`). `_answer_page`
  (`book_pdf_generator.py:1961-1993`) draws each packed page through
  `export.png.render_answer_page` — no clues, caption `answer_caption(number, title)` =
  `"Puzzle N — Title"` (`book_answer_key.py:219-239`, `CAPTION_SEPARATOR = " — "`).
  This is FR-042/INV-011, acceptance AC-261..AC-295, property EC-030/EC-031.
- `interior_stream` (`book_pdf_generator.py:2424-2630`) calls `self.answer_key(...)`
  eagerly at line 2494, **before** any page is drawn — a malformed (non-rectangular)
  solved grid raises there (`_answer_extent`, `book_pdf_generator.py:1393-1420`, wrapped
  as `RuntimeError("puzzle <id> could not be laid out: ...")` with the original
  `ValueError` as `__cause__`). The tripwire at lines 2518-2522 checks `key`'s own
  puzzle-number coverage against the payload count. `first_answer_page = 3 +
  len(section)` (line 2510). In `produce()` (lines 2603-2618), each packed
  `AnswerPage` is drawn via `_answer_page` and yielded, one bitmap at a time
  (CARD-145). `InteriorStream.answer_page_count = len(key)` (the **packed** count).
  `interior_page_count` (`book_pdf_generator.py:1255-1323`) takes `answer_pages` as a
  parameter and is otherwise generic — it needs **no code change**, only a different
  argument at the call site.
- **A second, independent production call site packs the same way**:
  `book_kdp.unpaired_interior_page_count` (`book_kdp.py:298-357`) imports `Answer`,
  `pack_answer_pages` (line 65) and calls `pack_answer_pages(answers)` at line 351 to
  get the sheet-free upper-bound page count Finalise shows when the book's stored print
  spec cannot even be laid out (CARD-129). `_grid_extent` (`book_kdp.py:360-383`) is its
  own reimplementation of the same rectangle check, which is what lets
  `app.py`'s `_is_an_unpackable_row` (`app.py:1018-1053`) detect a malformed-grid book
  independently of the generator's own abort shape.
- `app.py`'s `InteriorCounts`/`_interior_counts` (`app.py:837-975`) and
  `templates/book_finalize.html` (checked in full) are **generic**: they display
  whatever `stream.answer_page_count`/`unpaired_page_count`/`page_count` say, with no
  hardcoded "6-up"/"packed" wording anywhere in the template. They need no edit beyond
  what the numbers they read now mean.
- `book_proof.py` (checked in full) is **unrelated**: it renders two fixed, *unsolved*
  proof puzzles at fixed interior positions 1 and 2, through `page_spec`/`page_frame`/
  `render_pages` directly, with no dependency on the answer key at all. Not touched.
- **`book_kdp.py`'s own docstring already names the consequence this card creates**:
  `MAX_MODELLED_PAGE_COUNT = 300` (`book_kdp.py:95`, `KDP_GUTTER_BANDS[-1][0]`) is where
  `kdp_page_band` raises `KdpPageCountNotModelled` ("KDP gutter table not modelled
  above 300 pages") — the module's own comment calls going over 300 pages "far outside
  the ~120-190-page model the answer key exists to keep books inside" (lines 34-37).
  `tests/helpers/book_corpus.py`'s own documented large corpus (`corpus_puzzles`, 150
  puzzles) is today a 182-page interior with 27 **packed** answer pages; under this
  card the answer section becomes 150 pages (one per puzzle) instead of 27, taking that
  same book to roughly 305 interior pages — **over** the 300-page ceiling where
  Finalise now refuses outright with `KdpPageCountNotModelled`, for a book shape that
  finalised fine before this card. This is a real consequence of "roughly 6x more
  answer pages" beyond what CARD-197's render alone shows the owner, and it is not this
  card's job to extend KDP's table (that is a business fact this project has not
  recorded) — only to make sure Finalise still refuses cleanly rather than crashing or
  silently truncating (AC-8).

**Target.** Replace the packed 6-up/4-up key with one `solved_puzzle_page` call per
drawable puzzle, in book (print) order, reusing CARD-197's rendering primitive
unedited: `BookPDFGenerator.solved_puzzle_page(payload, puzzle_number, page_number,
title=None) -> Image.Image`.

1. **`book_pdf_generator.py`'s `interior_stream`.** Replace the eager
   `key = self.answer_key(...)` call (line 2494) with an eager validation pass over
   `payloads` that **keeps the same abort contract**: for each puzzle, read its grid's
   extent (reuse `_answer_extent` for the rectangle check — the number itself is no
   longer used for packing, only the validation matters now) and, on a `ValueError`,
   raise the same `RuntimeError("puzzle <id> could not be laid out: ...")` with that
   `ValueError` as `__cause__`, **before** any page is drawn. This is load-bearing:
   `app.py`'s `_is_an_unpackable_row` matches exactly that exception shape (G-6).
   Drop the "the answer key holds ..." tripwire (lines 2518-2522): with no packing walk
   to disagree with the plan, it is dead code — there is nothing left for it to catch.
   `first_answer_page = 3 + len(section)` is unchanged (line 2510 still correct: the
   SOLUTIONS divider still opens the section, nothing about where it sits changes).
2. **`produce()`'s answer-page loop** (lines 2603-2618). Replace the loop over packed
   `AnswerPage`s and `_answer_page` with a loop over `payloads` in order: for puzzle
   number `n` (1-based), call `self.solved_puzzle_page(payloads[n-1][1], n,
   first_answer_page + n - 1, title=answer_title(titles.get(str(payloads[n-1][0])),
   payloads[n-1][1].name))`, wrapped in the same `try`/`except Exception as e: raise
   RuntimeError(f"puzzle {_named_puzzles(ids, (n,))} could not be drawn: {e}") from e`
   the puzzle-page loop already uses. One bitmap alive at a time, `yield`ed and
   `del`eted exactly as today (CARD-145's two rules, restated in CARD-197's docstring,
   still hold — nothing about the memory discipline changes).
3. **`InteriorStream.answer_page_count`** becomes `len(payloads)` (the drawable puzzle
   count) instead of `len(key)`. **Delete `answer_key` and `_answer_page`** — nothing
   else calls them (grepped the whole of `src/nonogram`: the only other mention is a
   docstring cross-reference in `app.py:1027`, update its wording to point at the new
   per-puzzle loop instead of the method name).
4. **`book_kdp.py`'s `unpaired_interior_page_count`.** Drop the `Answer`/
   `pack_answer_pages` import (line 65) and the `pack_answer_pages(answers)` call
   (line 351). Keep the per-row `_grid_extent` rectangle check (it is still what lets
   `_is_an_unpackable_row` detect a malformed grid without a sheet) but stop building
   `Answer` objects from it — just validate and discard. Call `interior_page_count(
   len(ordered), puzzle_pages=len(ordered), answer_pages=len(ordered),
   level_dividers=dividers)` — `answer_pages` is now `len(ordered)` directly, because
   one-per-puzzle needs no sheet to count either (today only the packing term was
   sheet-free "for free"; after this card the *pairing* term is the only remaining
   upper bound here). Update the docstring's "the packed key" language to match.
5. **Level-boundary marker — decided here, since the owner only confirmed the page
   FORMAT, not a change to level grouping (INV-009).** The old packed key gave the
   *first* page of each level's run a small heading ("Easy"/"Medium"/"Hard") and no
   other page any level text. The new per-puzzle page already draws `band_identity
   (puzzle_number, tier)` — "Puzzle N · Tier" — via CARD-197's step 7, reused verbatim,
   on **every single** answer page, not just the first of a run. That is a stronger
   per-page signal than the old heading ever was (the old heading told you the level of
   the page you were looking at only on the first page of a run; every other page in
   the run carried no level text at all). **Decision: no separate level-heading or
   divider page inside the answer section.** The level is still visible on every page
   through its own band, and the book order (INV-009's grouping) still puts same-level
   puzzles' answer pages contiguously, exactly as the puzzle section already does — the
   grouping itself is unchanged, only the redundant once-per-run heading is dropped.
   An alternative considered and rejected: reuse `DividerPagePlan`/`create_divider_page`
   per level inside the answer section, mirroring the puzzle section's own dividers —
   rejected because it would add *more* pages on top of the already-large increase the
   owner accepted, for a signal every page already carries. **Flagged for the owner to
   confirm** (Design context below) since this is this card's own reading, not an
   owner-stated instruction.
6. **Page count and parity.** `interior_page_count`'s formula and code are unedited
   (point 1 above); only its `answer_pages` argument changes meaning. `page_count` and
   `unpaired_page_count` now differ **only** by the two-up pairing term — the "Before
   pairing" row on Finalise (`templates/book_finalize.html:134`,
   `pages_saved_by_pairing = unpaired_page_count - page_count`) no longer bundles the
   old packing saving, since there is none left to bundle. This is a real, owner-visible
   change to what that figure means (it used to mean "pairing + packing saved N pages";
   now it means "pairing saved N pages") — flagged in Design context, not silently
   absorbed. Page parity (FR-043/INV-013: page 1 right-hand, every later page's parity
   is its 1-based interior position) is **mechanical** and needs no code change — it
   already holds for any page count — but needs a test at the new, larger count (AC-7).

**ADR-0037/R1 cross-check.** Unaffected: the title/caption still print only on the
answer-key page (CARD-197 already established this is the existing exception, not a
new one), and this card changes nothing about *which* pages carry them, only how many
answer pages there are and what each one looks like.

## Acceptance criteria

- **AC-1** (happy): *Given* a book of N drawable puzzles, *when* the book PDF is
  generated, *then* the answer section (after the SOLUTIONS divider) holds exactly N
  pages, one puzzle per page, in book order 1..N.
  *test: TestBookSolvedAnswerKey_OnePagePerPuzzleInBookOrder (in tests/test_book_solved_answer_key.py)*
- **AC-2** (happy): *Given* any one of those N pages for puzzle number k, *when* it is
  inspected, *then* its clues, fill, title band (`band_identity(k, tier)`) and caption
  (`answer_caption(k, title)`) match what `solved_puzzle_page(payload, k, page_number,
  title)` would produce called directly with the same arguments — this pins that
  `interior_stream` calls CARD-197's primitive correctly per puzzle, not CARD-197's own
  pixel-level drawing (that is CARD-197's test suite's job).
  *test: TestBookSolvedAnswerKey_EachPageIsOnePuzzleSolvedWithClues*
- **AC-3** (happy): *Given* any book, *when* `InteriorStream.answer_page_count` and
  `interior_page_count`'s own tripwire (`_as_planned`) are checked, *then*
  `answer_page_count` equals the drawable-puzzle count (no packing), and a producer that
  yielded a different number of answer pages than planned still raises through
  `_as_planned`, unedited.
  *test: TestBookSolvedAnswerKey_PageCountIsOnePerPuzzleNotPacked*
- **AC-4** (boundary, level grouping): *Given* a book of 2 easy puzzles then 1 medium
  puzzle, *when* its answer pages are read, *then* pages 1-2's band reads "...· Easy"
  and page 3's reads "...· Medium" — level grouping is visible from book order and each
  page's own band — and no page in the answer section carries a separate heading line
  or sits on a dedicated level-divider page.
  *test: TestBookSolvedAnswerKey_LevelVisibleViaPerPageBandNoSeparateHeading*
- **AC-5** (negative, malformed grid preserved): *Given* a puzzle whose solution grid
  is not a non-empty rectangle, *when* the book PDF is generated, *then* the export
  aborts before any page is drawn with `RuntimeError("puzzle <id> could not be laid
  out: ...")` whose `__cause__` is the original `ValueError` — the same shape
  `app.py`'s `_is_an_unpackable_row` already matches.
  *test: TestBookSolvedAnswerKey_AMemberThatCannotBeMeasuredIsStillNamed*
- **AC-6** (negative, sheet-free count preserved): *Given* the same malformed-grid
  book with a print spec that cannot be laid out at all, *when*
  `unpaired_interior_page_count` is called, *then* it still raises `ValueError` —
  unaffected by removing `pack_answer_pages` from that function.
  *test: TestBookKdp_UnpairedCountStillRejectsAMalformedGrid*
- **AC-7** (boundary, parity): *Given* a book whose new one-per-puzzle answer section
  adds several pages beyond the old packed count, *when* every interior page's parity
  is read, *then* page 1 is right-hand and every later page's parity still equals its
  1-based position's odd/even-ness (FR-043/INV-013) — unchanged by the larger count.
  *test: TestBookSolvedAnswerKey_ParityHoldsAtTheNewPageCount*
- **AC-8** (boundary, the 300-page ceiling): *Given* a book whose interior now exceeds
  300 pages only because the one-per-puzzle answer section is longer than the old
  packed key would have made it (it was <=300 pages before this card), *when* the book
  is finalised, *then* it is refused with `KdpPageCountNotModelled`'s existing wording
  — not a crash, not a silently truncated count.
  *test: TestBookFinalise_AnswerSectionGrowthCanCrossTheThreeHundredPageCeiling (in tests/test_book_finalise_gutter.py)*
- **AC-9** (negative, byte-identity): *Given* any book, *when* every interior page up
  to and including the SOLUTIONS divider is compared against the pre-card baseline,
  *then* it is byte-identical; only pages after the SOLUTIONS divider differ.
  *test: TestBookPdfMemory_EveryPageUpToTheSolutionsDividerIsByteIdentical (in tests/test_book_pdf_memory.py, using the new tests/fixtures/book_baseline_card198.json)*
- **AC-10** (happy, Finalise display): *Given* the Finalise summary for a book, *when*
  "Answer pages" and "Before pairing" are read, *then* "Answer pages" equals the
  drawable-puzzle count and "Before pairing" reflects only the two-up pairing saving —
  both read off `InteriorStream`/`InteriorCounts` through the template, unedited.
  *test: TestBookFinalise_AnswerPageCountAndBeforePairingReflectNoPacking (in tests/test_book_finalise_gutter.py)*

## Guardrails

- G-1: CARD-197's `solved_puzzle_page` is reused verbatim — not edited by this card.
  `tests/test_book_solved_page.py` passes unedited.
- G-2: Every page before the SOLUTIONS divider (guide page, level dividers, one- and
  two-up puzzle pages) stays byte-identical to before this card — `create_guide_page`,
  `create_divider_page`, `_blank_page`, `_two_up_page` are not edited.
  `tests/test_book_pdf_band.py`, `tests/test_book_puzzle_frame.py`,
  `tests/test_book_pdf_two_up.py` and `tests/test_book_pdf_levels.py` pass unedited.
- G-3: FR-037's +/-3pp plan tolerance and puzzle selection are untouched — this card
  changes page layout, not which puzzles a book holds.
- G-4: ADR-0035/INV-012 (book status/membership rules) are untouched.
- G-5: `book_answer_key.py`'s pure functions (`pack_answer_pages`, `AnswerPage`,
  `Answer`, `page_capacity`, `SIX_UP`/`FOUR_UP`/`SIX_UP_LONGEST_SIDE`, `level_heading`)
  are left in the module, unedited, even though no production code calls
  `pack_answer_pages`/`AnswerPage`/`Answer` after this card — deleting them is an
  architecture-station decision (Worktree notes), not this card's. `answer_caption`/
  `answer_title` remain the only functions this card's production path calls.
- G-6: `app.py`'s `_is_an_unpackable_row`/`_interior_counts` abort-detection logic is
  not edited — the malformed-grid `RuntimeError(__cause__=ValueError)` shape it matches
  is preserved by this card exactly (AC-5/AC-6), not weakened.
- G-7: Black-and-white, no colour (CARD-147) — `solved_puzzle_page` already guarantees
  this; this card draws no ink of its own. `tests/test_book_pdf_ink_mode.py` passes
  unedited.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-198` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scala… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes uniq… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when th… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws n… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn; MIN… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on dens… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp < probe_contradiction… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the puzz… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a pur… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with th… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no attributi… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the gr… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle neve… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the book-membersh… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3 percent… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm toolcha… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a paramet… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, whos… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No ot… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) nev… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031, NFR… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's arrangement,… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5 mm… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is a… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns i… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the bo… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

## Architecture context

- **FR:** FR-042/INV-011 — this card makes its "6-up/4-up, packed, level heading on a
  run's first page" statement **false** by design; its ACs (AC-261..AC-295) and
  EC-030/EC-031 describe the format this card replaces and are not updated by this
  card (no edit under `meta/`). FR-043/INV-013 (page parity) and EC-034 (exact page
  count) must still hold at the new count (AC-7, AC-3).
- **ADR:** ADR-0036/R2 (layout functions read-only — unchanged, this card fits nothing
  new of its own, CARD-197's primitive already does), ADR-0037/R1 (title/caption only
  on the answer page — unaffected, confirmed by CARD-197 already).
- **CON:** CON-018 (KDP's gutter table — AC-8's 300-page ceiling is this table's own
  stated edge, not a new rule), CON-020 (10 pt floor — unaffected, CARD-197's primitive
  already holds it).
- **Components:** COMP-007 (layout functions, read-only), COMP-009 (both edited
  modules, `book_pdf_generator.py` and `book_kdp.py`, live here).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no edit under
  `meta/`); revisit once the architect station amends FR-042/INV-011.

## Design context

- **Output:** the book's answer-key section (after the SOLUTIONS divider) — now full
  solved pages instead of packed 6-up/4-up tiles.
- **Owner-visible defaults this card picks (need confirmation before merge):**
  - Dropping the per-level heading entirely (point 5 above) rather than keeping an
    equivalent marker some other way — the owner approved CARD-197's page format and
    accepted "~6x more answer pages," but was not asked specifically about the level
    heading disappearing.
  - The "Before pairing" Finalise figure now means something narrower than before
    (pairing saving only, not pairing + packing) — same label, quietly different
    arithmetic behind it.
  - The 300-page KDP ceiling (AC-8) can now make a book that used to finalise refuse to,
    purely because of this format change, with no workaround offered by this card.
- **Renders:** ~/Documents/nonogram-reviews/CARD-198/ (owner visual check before
  merge) — a small sample book of 3 puzzles across 2 levels (2 easy, 1 medium),
  rendered both ways: the answer section as it is today (packed, with the "Easy"
  heading) and as this card produces it (3 full solved pages, no heading), side by
  side, so the owner can see the page-count difference and judge whether the level
  boundary still reads clearly with only the per-page band to show it.

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", 2026-10-07, via CARD-197's
  drafted card (not yet merged at draft time — read its file directly, not implemented
  against a merged branch). This card wires CARD-197's `solved_puzzle_page` into the
  book's real answer-key packing, replacing it, which CARD-197 explicitly left undone.
- [Verified facts the implementer must not re-derive]
  - `book_pdf_generator.py`: `answer_key` L1897-1959, `_answer_page` L1961-1993 (both
    deleted by this card); `interior_stream`'s eager `key = self.answer_key(...)` at
    L2494, the now-dead "answer key holds" tripwire L2518-2522, `first_answer_page =
    3 + len(section)` L2510 (kept, correct unedited), the answer-page `produce()` loop
    L2603-2618; `interior_page_count` L1255-1323 (reused unedited — only its call-site
    arguments change); `_answer_extent` L1393-1420 (keep, validation only, no longer
    feeds packing); `_named_puzzles` L1326-1350 (reused for the new loop's own naming).
  - `book_answer_key.py`: `pack_answer_pages` L293-355, `AnswerPage` L242-291, `Answer`
    L115-169, `page_capacity`/`SIX_UP`/`FOUR_UP` L172-182/93-100 — all left in the
    module (G-5), no longer called by production. `answer_caption` L219-239,
    `answer_title` L200-216 — reused, already imported into `book_pdf_generator.py`
    (per CARD-197's own note).
  - `book_kdp.py`: `unpaired_interior_page_count` L298-357 is the **second** production
    call site packing the answers (imports `Answer`/`pack_answer_pages` L65, calls
    `pack_answer_pages` L351) — easy to miss if only `book_pdf_generator.py` is
    changed. `_grid_extent` L360-383 (keep, validation only). `MAX_MODELLED_PAGE_COUNT
    = 300` L95 / `KdpPageCountNotModelled` L102 / `kdp_page_band` L167-186 — the
    300-page ceiling AC-8 is about.
  - `app.py`: `InteriorCounts`/`_interior_counts` L837-975 and
    `templates/book_finalize.html` are generic — checked in full, no hardcoded
    "6-up"/"packed" wording anywhere, so neither needs an edit beyond what the numbers
    mean (point 6 of "What to implement"). `_is_an_unpackable_row` L1018-1053 is the
    consumer G-6 protects; its docstring at L1027 cross-references `answer_key` by
    name and needs its wording updated once that method is deleted.
  - `book_proof.py` — checked in full, unrelated (two fixed unsolved proof pages, no
    answer-key dependency at all). Not touched, not listed in Touches.
  - `tests/helpers/book_corpus.py`'s own docstring documents today's two fixture books'
    exact shapes: the small `baseline_puzzles` book (4 puzzles, 11 interior pages
    including "three answer pages of the packed key") and the large `corpus_puzzles`
    book (150 puzzles, "182-page interior ... 27 answer pages"). Both counts change
    under this card (the large book's answer section goes from 27 to 150 pages, the
    interior from 182 to roughly 305) — the docstring prose and the recorded digests
    both need updating, in the same commit as the new `tests/fixtures/book_baseline_card198.json`
    per the Touches rule (a new baseline, its own commit).
  - `tests/test_book_answer_key.py` (1320 lines) is almost entirely integration tests
    that render pages through `BookPDFGenerator.answer_key`/`_answer_page`/`interior`/
    `export_book` and assert the packed-key pixel behaviour this card deletes:
    `TestBookAnswerKey_SixUpInPuzzleNumberOrder`,
    `LargeAnswerThatWouldOverfillStartsNewPage`,
    `PageBecomesFourUpOnceItHoldsAnswerAbove20`, `LongestSideTwentyStaysSixUp`,
    `SixUpRuleKeepsTheAnswerCellAboveTheFloor`, `CaptionPuzzleNumberAndTitle`,
    `CaptionUsesCustomBookTitle`, `CaptionSeparatorIsADrawnGlyph`,
    `DefaultPlanTakesThirtyPages`, `EachLevelStartsNewAnswerPage`,
    `HeadingOnlyOnLevelFirstPage`, `SolutionsDividerPrecedesAnswerKey`,
    `ReportsItsAnswerPageCount`, `AMemberThatCannotBeMeasuredIsNamed`,
    `TheExtentReaderAgreesWithTheRenderer`, `EverySupportedSizePrints`. Each must be
    either retired (the behaviour it pinned no longer exists in production) or
    narrowed to what still holds (puzzle-number order, caption/custom-title text,
    malformed-grid naming, the SOLUTIONS divider, the reported `answer_page_count`) —
    this is most of this card's test-file work, not a side effect.
  - `tests/test_book_finalise_gutter.py`: `AC179_PAGES`/`AC271_ANSWER_PAGES` constants
    (used around L520-602) and a direct `BookPDFGenerator.answer_key` monkeypatch
    (L761-766, simulating a page-plan failure) both target the method this card
    removes and must be recomputed/retargeted.
  - `tests/test_book_pdf_memory.py`: L216 lists `"_answer_page"` among the private
    methods its memory instrumentation patches; L1532-1534 assert a baseline
    `answer_page_count == 3`; L1606-1622 monkeypatches `BookPDFGenerator._answer_page`
    to force a "could not be drawn" abort. All three need retargeting to the new
    per-puzzle loop (likely `solved_puzzle_page` itself, or a small seam around it).
- [Tension flagged, not resolved here] Dropping the per-level heading (point 5) is this
  card's own reading of "the owner only confirmed the format change." If the owner
  wants an equivalent marker kept (e.g. a per-level divider page, or a line added back
  onto each page), that is a small follow-up to this card's PR, not a blocker to
  drafting or implementing it this way first — the render set (3 puzzles, 2 levels)
  exists specifically to let the owner judge this before merge.
- [AC cross-check] Re-read AC-1..AC-10 against "What to implement"'s 6 numbered points:
  AC-1/AC-2/AC-3 map to points 1-3, AC-4 to point 5, AC-5/AC-6 to points 1/4's
  validation preservation, AC-7 to point 6's parity claim, AC-8 to the 300-page finding
  surfaced in "Current behaviour," AC-9 to G-2's byte-identity claim made testable,
  AC-10 to point 6's Finalise-display claim. No AC asks for an order or a case the body
  doesn't also describe.
- [Estimate] 1.5d, **above the brief's 1-day flag.** Split suggestion if it needs to
  divide: (a) production wiring — `book_pdf_generator.py`'s `interior_stream`/
  `produce()` replacement, `book_kdp.py`'s `unpaired_interior_page_count` update, the
  malformed-grid validation preservation (AC-5/AC-6), the page-count/parity tests
  (AC-1/AC-3/AC-7), the 300-page-ceiling test (AC-8), and the new baseline fixture
  (~0.75d); (b) the test-suite migration — retiring/narrowing
  `tests/test_book_answer_key.py`'s ~16 packed-key integration classes,
  retargeting `tests/test_book_finalise_gutter.py`'s constants/monkeypatch and
  `tests/test_book_pdf_memory.py`'s three touch-points, the new
  `tests/test_book_solved_answer_key.py` (AC-2/AC-4/AC-9/AC-10), and the two
  owner-visible renders (~0.75d). Kept as one card per the brief's instruction.
- [Not in this card] Formalising the requirements delta: amending FR-042/INV-011 to
  state the new one-per-puzzle format (and retiring or rewriting its AC-261..AC-295),
  confirming FR-043/INV-013's wording still matches (it does, unedited), and updating
  `meta/architecture/trace.yml` and the `book_baseline` fixture notes in `meta/` — all
  `/forge:architect` delta work for after this card merges, per the brief. This card
  edits nothing under `meta/`.
- [Owner decision] 2026-10-07 — drop the level-heading pages from the answer section (each page already names its tier in the band); keep both numbers (band "Puzzle N" above, caption "Puzzle N — Title" below). CARD-198 also depends on CARD-199 (raise the KDP gutter ceiling), which should land before or alongside this card so Finalise does not regress on larger books.
