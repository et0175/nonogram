# CARD-200: The book's interior PDF gets a visible page number on every page and a table-of-contents page

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/200-page-numbers-and-toc
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 1: "Please add page numbers and a table of content")
**Idea:** —
**Wave:** —
**Depends on:** CARD-201
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_toc.py, tests/test_book_page_numbers.py, tests/test_book_finalise_gutter.py, tests/test_book_guide_page.py, tests/test_book_pdf_levels.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_ink_mode.py, tests/test_book_arrange_page_breaks.py, tests/test_book_solved_answer_key.py, tests/property/test_book_export_interior.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card200.json
**Review score:** 10.0/10 (cycle 3, final)
**Started:** 2026-10-09T13:58:53Z
**Closed:** 2026-10-09T18:45:18Z
**Actual:** 4.77h
**Merge commit:** e899369
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).** No page of the book's interior
PDF ever draws a visible page number. `page_number` is pervasive *internal*
bookkeeping — `PageFrame`/`Layout.page` (`Placement`) carry it, `page_is_right_hand`
(`book_pdf_generator.py:1266-1277`), `interior_page_count` (`:1277-1323`) and every
page-drawing method (`create_guide_page`, `create_divider_page`, `_blank_page`,
`_two_up_page`, `solved_puzzle_page`) take a `page_number` argument *only* to resolve
`self.page_spec(page_number)` — the mirrored-margin `PageSpec` for that position
(FR-030/FR-032) — never to print it. Confirmed by reading every one of those methods in
full and grepping `draw.text` in the module: nothing writes a folio. There is also no
table-of-contents page anywhere — `interior_stream`'s `produce()`
(`book_pdf_generator.py:2665-2743`) yields exactly: the guide page (page 1), the puzzle
section (a `DividerPagePlan` per non-empty level + each `PuzzlePagePlan`, one or two
puzzles), the SOLUTIONS divider, then one `solved_puzzle_page` per puzzle. I confirmed
by grepping `meta/architecture/requirements.yml` for "page number"/"table of content"/
"footer"/"folio" that no FR/AC states either rule today — this is new ground, not a
reversal of an existing owner decision (unlike CARD-201's guide-page replacement or
the sibling "right-align the puzzles" ask from the same doc, which I am flagging to
the owner separately rather than carding blind — see the project's current board
notes).

**The one reusable seam every page kind already shares.** `page_frame(spec)`
(`book_pdf_generator.py:1168-1188`) calls `compute_layout` with a throwaway one-cell
probe clue set and reads back `layout.page` (a `Placement`), returning a `PageFrame`
whose `left/top/right/bottom` are that placement's `usable_left/top/right/bottom` —
the mirrored-margin usable area, for *any* `PageSpec`, independent of what the page
actually draws. `create_guide_page` and `create_divider_page` already use exactly this
to place their own text inside the same usable area every grid page's `Placement` also
reports (`placement.usable_bottom` is the same field `solved_puzzle_page`'s caption
sits above, step 8, `book_pdf_generator.py:2111-2150`, already read in full for
CARD-198). This means a footer page-number needs **no new layout-placement concept**
(ADR-0036/R2: COMP-007's layout functions are the only things that place geometry) —
every page already has a `PageFrame`-shaped usable-bottom to anchor a footer against,
whether it was reached via `page_frame()` (guide, divider) or via `compute_layout`'s
own `Layout.page` directly (one-up, two-up, solved-answer pages).

**The one real collision to resolve, not invent a workaround for silently.** On a
solved-answer page, the caption (`answer_caption`) already occupies the slack between
`placement.drawing_bottom` and `placement.usable_bottom`, horizontally centred, and is
*omitted* outright when that slack is smaller than one line (CARD-197's own
documented limit, step 8's comment). A footer sharing the same slack must not collide
with that caption. **Decision this card makes, flag for owner confirmation before
merge (Design context below):** the footer sits in the same bottom slack as the
caption but anchored to the opposite side — caption horizontally centred, folio
flush with the usable area's **outer** edge (the side away from the gutter, i.e.
`usable_right` on a right-hand/odd page, `usable_left` on a left-hand/even page — the
conventional book-footer position, and incidentally the same side item 5's sibling
card (CARD-203) is independently moving the caption's own alignment towards, so the
two should not end up visually fighting on the same page — coordinate with that
card's implementer if both are in flight at once). A page whose slack is too small for
even a single small folio line should print no folio rather than overlap the grid —
same "omit rather than collide" discipline CARD-197 set for the caption, not a new
rule invented here.

**What to implement, four parts:**

1. **A small shared footer helper.** Add one function (module scope, beside
   `_set_band`/`_write_clues` which are its closest siblings — same "draw something
   generic at a geometry-derived position" shape) — suggested name
   `_draw_folio(draw, frame_or_placement, page_number, dpi)` — that: formats the folio
   as a plain decimal (`str(page_number)`, no "Page" prefix, no leading zeros — a
   plain book-style folio), measures it at a font size that is **at or above CON-020's
   10 pt floor** (reuse `type_px`/`_band_font` exactly as `solved_puzzle_page`'s
   caption does, do not invent a second font-sizing path), and draws it anchored to
   the usable area's bottom-outer corner with `anchor` chosen so it never crosses the
   usable-area's edge (Pillow's `"rb"`/`"lb"` anchor on a right/left hand page
   respectively, by `page_is_right_hand(page_number)`). Takes either a `PageFrame` or
   the `.page` `Placement` off a `Layout` — both already expose the same four
   `usable_*` fields by name, so one function signature covers every caller without a
   branch on page kind.
2. **Call it from every page-drawing method**, right before each one returns its
   `Image.Image` — `create_guide_page` (`:1556-1673`), `create_divider_page`
   (`:1673-1698`, covers both the level dividers and the SOLUTIONS divider — same
   method, same call site), `_blank_page` (`:1881-1929`, the one-up puzzle page),
   `_two_up_page` (`:1929-1972`, draw it once per page using `pair.upper`'s
   `Placement` — the page is one physical sheet; do not draw it twice from each
   slot's own placement), `solved_puzzle_page` (`:1972-2151`, after the caption step,
   same slack, opposite corner per the collision rule above). **The cover page is
   never numbered** (`create_cover_page`, FR-043's own stated rule: "The cover file is
   never numbered (FR-043)," already a docstring comment at `:1517-1522` — do not add
   a footer there).
3. **A table-of-contents page.** New method, e.g. `create_toc_page(self, entries,
   page_number) -> Image.Image`, drawn the same way `create_guide_page`/
   `create_divider_page` are (`page_frame(self.page_spec(page_number))`, plain text,
   `wrap_words`/`_guide_face`/`type_px` reused — no new text-layout primitive). Each
   entry is one puzzle: its resolved title (reuse `answer_title`/`custom_titles()`
   exactly as the answer section already resolves them — do not re-derive) or, absent
   one, "Puzzle N" alone (same fallback `answer_caption` already uses when `title` is
   `None`), right-dot-leadered or simply right-aligned against its **puzzle page's**
   `page_number` — read directly off `section_plan(puzzles).pages`, filtered to
   `PuzzlePagePlan` entries, whose `.numbers`/`.page_number` already carry exactly
   this mapping (`book_pdf_generator.py:881-906`, `section_plan` at `:2353-2441` —
   this is the *same* seam the Arrangement screen (CARD-140) and this card's own
   `interior_stream` already read; do not build a second puzzle-number-to-page-number
   walk). If the TOC itself needs more than one page (a large book), the simplest
   correct rule is: split entries across as many TOC pages as needed, same as the
   guide page's own "set in the first of three forms that fits" pattern
   (`create_guide_page`'s `set_page`, `:1628-1661`) — but flag this as a real open
   question (Design context) rather than silently picking a page-count-per-entry
   number, since the owner has not seen how many puzzles-per-page a TOC reads well at.
4. **`interior_stream`'s page-count arithmetic — the real architectural cost of this
   card. CORRECTED 2026-10-09 by the orchestrator, after both CARD-201 and CARD-202
   merged** (this card was drafted against the pre-CARD-201/202 formulas, which no
   longer exist — re-verified against the real, current merged code before `start`,
   not left for the implementer to discover): the `first_answer_page = 3 + len(section)`
   this card's draft cites is gone. There are now, by design, **two separate
   `first_answer_page`-named values in `interior_stream`** (both already in the merged
   code, not something this card invents) — read `interior_stream` in full before
   touching it, do not assume either is the one you need without checking:
   - An EARLY one (`first_answer_page = 3 + len(section)`, pre-CARD-201 value,
     deliberately left over from before CARD-201 merged) used ONLY to build a
     *representative* `PageSpec` (`self.page_spec(first_answer_page)`) for
     CARD-202's packing-feasibility check (`_degrade_infeasible_packed_pages`),
     before any tripwire or the real page count is known. The code's own comment
     explains why the exact value doesn't matter here: usable WIDTH (what the
     feasibility check needs) is parity-invariant — mirrored margins swap which
     *side* the gutter is on, never the usable width's own size — so a stale page
     number is harmless for this one, narrow purpose. **Do not "fix" this value to
     include a TOC term** — it would be a no-op at best and confusing at worst;
     leave this early assignment exactly as-is.
   - The REAL, final one, a few lines later: `first_answer_page = 1 +
     GUIDE_PAGE_COUNT + len(section) + 1` (`GUIDE_PAGE_COUNT = 2`, a module
     constant CARD-201 added) — **this** is the one that governs the SOLUTIONS
     divider's page number (`create_divider_page(first_answer_page - 1)`,
     already written as an expression, not a literal) and the answer-page loop
     (`for index, entry in enumerate(answer_plan): page_number =
     first_answer_page + index`). **This is the one that needs a `toc_pages`
     term**: `first_answer_page = 1 + GUIDE_PAGE_COUNT + toc_page_count +
     len(section) + 1`.
   `interior_page_count` (module-level function, not a method — read its current
   docstring in full, it already explains CARD-201's and CARD-202's own terms in
   detail) takes `puzzle_count`/`puzzle_pages`/`answer_pages`/`level_dividers` and
   already uses `GUIDE_PAGE_COUNT` as its own leading term (not a hardcoded `1`) —
   this card adds one more parameter, `toc_pages` (or folds it into an existing
   additive term if that reads cleaner — implementer's call, document which and why),
   and every call site (there are at least two — `interior_stream` itself and
   `book_kdp.unpaired_interior_page_count`, same two-call-site shape CARD-198/
   CARD-202 both had to keep in sync) must pass it.
   `page_is_right_hand`/every puzzle and divider page's own `page_number` argument
   shift by `toc_page_count` automatically, as long as they keep reading it off the
   same `section`/`first_answer_page` arithmetic rather than a page_number computed
   some other way. **This is the same shape of ripple CARD-198/201/202 each already
   produced** (a new front-matter or packing concept pushes every later page's number
   and/or parity) — expect a comparable or larger SCOPE+ footprint across hard-coded
   page-count/page-index test fixtures; the Touches list above was built by grepping
   the PRE-merge codebase and is stale in its exact line numbers (not its file list) —
   re-grep for `first_answer_page`/`GUIDE_PAGE_COUNT`/`answer_plan`/"interior page 1"
   fresh against the current merged code, and expect MORE affected files than either
   this list or the grep predicts, the same caveat CARD-198's own notes gave and
   CARD-201's own merge just re-confirmed (a clean-looking merge of unconflicted code
   can still be semantically stale — see CARD-201's own Worktree notes, "[Merge]"
   entry, for a worked example of exactly this trap).

## Acceptance criteria

- **AC-1** (happy, folio present): *Given* a book's interior PDF, *when* every page
  after the cover (guide, TOC, divider, one-up, two-up, solved-answer) is read, *then*
  each one carries its own 1-based interior page number, printed as a plain decimal,
  at the usable area's bottom-outer corner (the side away from the gutter, by that
  page's own parity) — except a page whose bottom slack is too small to fit one line,
  which prints none.
  *test: TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber (in tests/test_book_page_numbers.py)*
- **AC-2** (negative, cover excluded): *Given* the same book, *when* the generated
  cover file is read, *then* it carries no page number anywhere on it (FR-043's
  existing "never numbered" rule, now made visibly true rather than merely
  uncontradicted).
  *test: TestBookPageNumbers_CoverIsNeverNumbered*
- **AC-3** (happy, correct number not just present): *Given* a book of 2 easy and 1
  medium puzzle, *when* the SOLUTIONS divider and the first answer page are read,
  *then* their printed folios equal `2 + toc_page_count + len(section)` and
  `first_answer_page` exactly as `interior_stream` computes them — a folio that is
  present but wrong (e.g. off by the TOC's own length) must fail this test, not just
  AC-1's presence check.
  *test: TestBookPageNumbers_FoliosMatchInteriorStreamsOwnArithmetic*
- **AC-4** (happy, TOC content and order): *Given* a book of N drawable puzzles across
  two or more levels, *when* its table-of-contents page(s) are read, *then* every
  puzzle appears exactly once, in book (print) order, each against the exact interior
  page number its own puzzle page (`PuzzlePagePlan.page_number`) carries — a paired
  two-up page's two puzzles both point at the *same* page number.
  *test: TestBookToc_ListsEveryPuzzleAgainstItsRealPageNumber (in tests/test_book_toc.py)*
- **AC-5** (happy, title resolution reused): *Given* a book where one puzzle has a
  custom Arrangement-step title and another has none, *when* the TOC is read, *then*
  the first row shows the custom title and the second shows "Puzzle N" alone — the
  exact same resolution `answer_title`/`custom_titles()` already produce for the
  answer section, not a second, independent title lookup.
  *test: TestBookToc_TitleResolutionMatchesTheAnswerSections*
- **AC-6** (boundary, overflow): *Given* a book with enough puzzles that the TOC does
  not fit one page, *when* the interior is read, *then* the TOC spans as many pages as
  it needs, every entry still appears exactly once, and every page number after the
  TOC (divider/puzzle/answer pages) is still consistent with `interior_stream`'s own
  arithmetic at that length (AC-3 holds at this larger `toc_page_count` too).
  *test: TestBookToc_OverflowsToASecondPageWithoutLosingAnEntryOrBreakingLaterNumbering*
- **AC-7** (negative, type floor): *Given* any interior page's folio, *when* its font
  size is measured, *then* it is never below 10 pt at the page's own resolution
  (CON-020) — covered automatically by the existing
  `TestInteriorType_EveryFaceHoldsTheFloor` once the folio becomes one more
  `draw.text` call that test's instrumentation records; this AC is the statement that
  the new draw call must not be exempted or special-cased out of that walk.
  *test: TestInteriorType_EveryFaceHoldsTheFloor (in tests/test_book_interior_type_floor.py, unedited — passes once the footer is a plain draw.text call)*
- **AC-8** (negative, byte-identity outside scope): *Given* any book, *when* every mark
  on the page **above** the new footer band is compared against the pre-card baseline
  at the same trim, *then* it is unchanged — the grid, clues, band and (on answer
  pages) the caption keep their exact pre-card pixels; only the new bottom-corner folio
  and the page-count-driven shift in *which* content sits on *which* page number are
  new.
  *test: TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged (in tests/test_book_pdf_memory.py, against a new tests/fixtures/book_baseline_card200.json)*
- **AC-9** (boundary, parity preserved): *Given* a book whose page count grows by
  `toc_page_count` pages, *when* every interior page's parity is read, *then* page 1 is
  still right-hand and every later page's parity still equals its own 1-based interior
  position (FR-043/INV-013) — the TOC page(s) are ordinary interior pages for parity
  purposes, not an exception.
  *test: TestBookPageNumbers_ParityHoldsWithTheTocInserted*

## Guardrails

- G-1: `ADR-0036/R2` — the footer and the TOC page use only the existing layout
  primitives (`page_frame`, `compute_layout`'s own `Placement`) to find where to draw;
  neither adds a second, independent geometry system. No new field is added to
  `PageSpec`/`Layout`/`Placement` by this card.
- G-2: The cover page (`create_cover_page`) is never numbered (FR-043) — not edited to
  carry a footer by this card.
- G-3: Every existing page's *content above the footer band* stays byte-identical
  (AC-8) — `_stroke_drawing`, `_write_clues`, `_set_band`, the answer-page caption
  logic, and `draw_example_line`/the guide page's worked example are not edited by
  this card.
- G-4: CON-020's 10 pt floor applies to the new folio text exactly as to every other
  interior face — no exemption is added for it.
- G-5: FR-032's horizontal-centring rule and FR-030's mirrored-margin rule are read,
  not changed, by this card — the footer's *position* (outer-bottom-corner) is a new
  decision this card makes, not a change to where the *drawing itself* sits.
- G-6: The puzzle section's own numbering (`band_identity`, one-based puzzle numbers,
  INV-009's level grouping) is untouched — this card adds a page number and a TOC, it
  does not renumber puzzles.

## System contract

_Assembled 2026-10-08 by `system_rules.py --card CARD-200` (53 rules — the same
Touches-derived scope as CARD-198's, confirmed identical rule-id set). A projection —
fix the source artifact, never this list._

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

- **FR:** FR-030/FR-032 (mirrored margins, horizontal centring — read, not changed);
  FR-041/FR-042 (guide page, answer section — both gain a footer, neither's own
  content rule changes); FR-043/INV-013 (parity, "cover never numbered" — this card is
  the first thing that makes that second clause visibly checkable). No FR today states
  a page-number-visible-to-the-reader rule or a TOC rule — this card does not edit
  `meta/architecture/**` to add one (architect-station work, see "Not in this card"
  below), matching the pattern CARD-198 used for its own FR-042 staleness.
- **ADR:** ADR-0036/R2 (layout functions place, nothing else does — G-1 holds this).
- **CON:** CON-018 (KDP gutter table — a few extra interior pages from the TOC nudge
  every book's page count up by `toc_page_count`, worth a one-line awareness note but
  not a new risk class the way CARD-198's answer-section growth was, since a TOC is at
  most a handful of pages even for a large book).
- **Components:** COMP-007 (layout functions, read-only, G-1), COMP-009
  (`book_pdf_generator.py`, the only module this card edits).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card (no edit under
  `meta/`); revisit once the architect station records the new page-numbering/TOC
  rule as its own FR.

## Design context

- **Output:** every interior page gains a small folio in its bottom-outer corner; a
  new TOC page (or pages) is inserted after the guide page and before the puzzle
  section.
- **Owner-visible defaults this card picks (need confirmation before merge):**
  - The TOC's position (right after the guide page, before the first puzzle/divider)
    — the doc did not say where it goes, only that it should exist.
  - The folio's own position (bottom-outer-corner, plain decimal, no "Page" word, no
    rule/ornament) — a plausible default book convention, not an owner instruction.
  - On a solved-answer page, the folio sits in the same bottom slack as the caption,
    opposite corner — this needs to be checked against CARD-203's caption-repositioning
    work (same page, same slack) in a real render before either merges, not assumed
    compatible from the text description alone.
  - Whether the TOC and the guide page itself carry a visible folio of their own (this
    card's reading: yes — only the **cover** is exempt, per FR-43's existing wording;
    front matter inside the interior is still interior).
- **Renders:** ~/Documents/nonogram-reviews/CARD-200/ (owner visual check before
  merge) — a small sample book (3-4 puzzles across 2 levels) exported both before and
  after this card, so the owner can see the new folio on every page kind (guide,
  TOC, divider, one-up, two-up, solved-answer) and the TOC page's own layout, and
  specifically judge the folio/caption coexistence on a solved-answer page.

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", revision read 2026-10-08
  (the same document CARD-197/CARD-198/CARD-199 were drafted from on 2026-10-07, now
  carrying five new numbered items; this card is item 1 only). Items 2, 4 and 5 are
  drafted as sibling cards (CARD-201, CARD-202, CARD-203) in the same batch; item 3
  (right-align the puzzle pages + a QR-code icon linking to "the solver") is
  deliberately **not** carded yet — it reverses FR-032's explicit, owner-decided
  horizontal-centring statement (amended 2026-09-22 (c)) and its QR target (a public,
  reader-facing solver) does not exist yet (CON-021 restricts interactive play to the
  admin panel; "online solver, public phase" is still an uncarded backlog line) — both
  need the owner's direct confirmation before any card is drafted for it, not a
  drafting agent's guess.
- [Why `Depends on: CARD-201`] **CARD-201 has since merged** (and CARD-202 merged
  before it) — this dependency is satisfied; build this card on `main` at its current
  HEAD, not on any stale assumption from before either merged. CARD-201 replaced the
  guide page's content with a 2-page "How to Solve a Nonogram" tutorial:
  `GUIDE_PAGE_COUNT = 2` is now a real module constant, and `produce()` yields it via
  `for guide_page_number in range(1, GUIDE_PAGE_COUNT + 1): ... create_guide_page(...,
  page_number=guide_page_number)` — two real calls, two real images, not one call
  producing two pages internally. This card's TOC sits immediately after the guide
  page(s) and must read `GUIDE_PAGE_COUNT` (not assume `1`, and not hardcode `2`
  either — read the constant) to know where it starts.
- [Verified facts the implementer must not re-derive]
  - `page_frame` (`:1168-1188`), `PageFrame` (`:1135-1160`) — the generic
    usable-area reader every non-grid page (guide, divider, TOC) already uses.
  - `create_guide_page` (`:1556-1673`), `create_divider_page` (`:1673-1698`) —
    both page-frame-based, both the TOC's closest siblings in style.
  - `_blank_page` (`:1881-1929`), `_two_up_page` (`:1929-1972`), `solved_puzzle_page`
    (`:1972-2151`, its caption placement at step 8, `:2111-2150`, already read in full
    for CARD-198) — the three grid-based page kinds, whose `Placement.usable_*`
    fields are named identically to `PageFrame`'s.
  - `interior_stream` (`:2537-2757`) and `produce()` (`:2665-2743`) — the single
    generator every page flows through; `first_answer_page = 3 + len(section)`
    (`:2642`), the SOLUTIONS divider's own `2 + len(section)` (`:2725`),
    `interior_page_count(...)` (`:2663`) are the three places whose arithmetic needs a
    `toc_page_count` term.
  - `PuzzlePagePlan`/`DividerPagePlan`/`SectionPlan` (`:881-991`), `section_plan`
    (`:2353-2441`) — the puzzle-number-to-page-number mapping the TOC reads, already
    computed once per export, reused rather than re-derived.
  - `custom_titles` (`:1901-1928`), `answer_title`/`answer_caption` (imported from
    `book_answer_key.py`, line 325) — the title-resolution the TOC reuses verbatim.
  - CON-020's `TestInteriorType_EveryFaceHoldsTheFloor` (`tests/test_book_interior_type_floor.py`)
    already walks every `draw.text` call on a baseline interior — confirmed by reading
    its docstring — so it needs no edit to cover the new folio, only to keep passing
    once there is one more call for it to see.
  - Grepped `tests/` for `first_page=2`/`first_answer_page`/"interior page 1": hits in
    `tests/fixtures/book_baseline_card149.json`, `book_baseline_card167.json`,
    `tests/helpers/book_corpus.py`, `tests/property/test_book_export_interior.py`,
    `tests/test_book_arrange_page_breaks.py`, `tests/test_book_finalise_gutter.py`,
    `tests/test_book_guide_page.py`, `tests/test_book_pdf_ink_mode.py`,
    `tests/test_book_pdf_levels.py`, `tests/test_book_pdf_memory.py`,
    `tests/test_book_solved_answer_key.py` — each likely needs its fixed page-count/
    page-index recomputed once `toc_page_count` is real, same SCOPE+ shape CARD-198
    hit. The grep is a floor, not a ceiling, on the real blast radius — CARD-198's own
    notes made the same caveat and still found more than its own grep predicted.
- [Open question, not resolved here] How a multi-page TOC should split long lists —
  by a fixed entry count, by remaining vertical space (mirroring the guide page's own
  "three forms, whichever fits" pattern), or something else. Flagged for the owner/
  implementer rather than guessed; AC-6 only requires that overflow behave correctly,
  not any particular split rule.
- [Not in this card] Formalising a new FR/AC for visible page numbers and the TOC in
  `meta/architecture/requirements.yml`, and updating `trace.yml` — architect-station
  work, after this card merges, per the same pattern CARD-198 left its own FR-042
  staleness for.
- [AC cross-check] AC-1/AC-2/AC-7/AC-8 map to "What to implement" points 1-2 (the
  footer helper and its six call sites, the cover's exemption, the type-floor and
  byte-identity preservation). AC-3/AC-9 map to point 4 (the arithmetic ripple,
  parity preserved at the new count). AC-4/AC-5/AC-6 map to point 3 (the TOC page
  itself, its title resolution, its overflow behaviour). No AC asks for a case the
  body does not also describe.
- [Estimate] 1.5d, matching CARD-198's own estimate for a comparable "new front-matter
  page, ripple every downstream offset, recompute the hard-coded test fixtures"
  shape. Split suggestion if it needs to divide: (a) the footer helper + its six call
  sites + the arithmetic ripple + the new baseline fixture (~0.75d); (b) the TOC page
  itself + its own tests + the SCOPE+ fixture recomputation across the Touches list's
  test files (~0.75d).
- [Env] forge 2026.8.17 (no `meta/.skills.yml` → no `forge.min_version` to
  compare against; version still resolved and noted per protocol).
- [Pin gate] n/a — no `meta/.skills.yml` → `legacy.enabled` unset, gate
  skipped.
- [Drift gate] n/a — no `meta/drift-pending.yml`, gate skipped.

- [Implementation complete, 2026-10-09]

  **STRUCTURE decisions:**

  - `_draw_folio(draw, left, top, right, bottom, page_number, dpi, content_bottom=None)`
    — deviates from the card's own suggested `(draw, frame_or_placement, page_number,
    dpi)` signature, **and this is a correction to the card's own draft, not a free
    choice**: the card's text claims `PageFrame` and a grid page's `PagePlacement`
    "already expose the same four `usable_*` fields by name" — read in full,
    `PageFrame` (`book_pdf_generator.py`) actually names its four edges
    `left`/`top`/`right`/`bottom` (no `usable_` prefix at all), while `PagePlacement`
    (`export/layout.py`) names them `usable_left`/`usable_top`/`usable_right`/
    `usable_bottom`. Duck-typing on "the same field names" would have raised
    `AttributeError` the first time a guide/divider/TOC page's frame was handed to a
    helper written against `PagePlacement`'s names. Every call site therefore reads its
    own object's fields and passes four plain ints across — G-1 still holds (no field
    is added to either class to make the names agree; `_draw_folio` places nothing
    itself, it only draws at coordinates its caller already has).
  - `content_bottom: Optional[int] = None` on `_draw_folio` — generalises CARD-197's
    "omit rather than collide" rule for the answer caption to every page kind, but
    **only where a real competing mark exists**: `solved_puzzle_page` and
    `create_guide_page` pass their own measured content-bottom (the same
    `usable_bottom - drawing_bottom` slack the caption already uses, and the guide's
    own chosen-fallback-form `bottom`, respectively); `_blank_page`, `_two_up_page` and
    `_packed_answer_page` pass none, because nothing else is drawn in that exact
    corner on those page kinds (verified against `PairLayout`'s own construction: a
    two-up page's *lower* slot has **zero** slack by design — "whatever height the
    pair leaves spare falls between the two slots" — so treating that zero as a
    collision, as a naive generalisation would, would silently omit the folio from
    every two-up page in the book; `pair.lower.page`, not `pair.upper.page` as the
    card's own draft suggested, is also what supplies the two-up page's true
    bottom-outer corner, since `upper.page.usable_bottom` is the *midline* between the
    two slots, not the page's own margin — another correction to the card's own text,
    found by reading `compute_pair_layout`'s real arithmetic rather than trusting the
    prose).
  - `interior_page_count` gains `toc_pages` as a **new, separate parameter**, not
    folded into `level_dividers` or any existing term: the TOC is a distinct
    front-matter page kind (like `GUIDE_PAGE_COUNT`), not a divider or an answer page,
    and folding it into an unrelated term would make the formula's own terms stop
    naming what they count. Its default (when omitted) is `_toc_page_count` measured
    on `_default_toc_frame()` (CON-018's Book 1 profile) — **not** a count-only guess
    like `level_dividers`'s `min(3, n)`, because the TOC's split genuinely needs a
    usable height to divide entries by, which no pure function of `puzzle_count` alone
    can stand in for safely in both directions. This default had to be exactly this
    (not merely "a reasonable one") to keep `tests/test_book_export_interior_cover.py`'s
    pre-existing **exact**-equality assertions (`interior_page_count(3) == written`,
    at the "all defaults" call) holding at Book 1's own profile.
  - `SectionPlan` gains a `toc_page_count: int = 0` field, and `section_plan` computes
    it once (off the book's own `page_frame(self.page_spec(1))`, parity-invariant per
    `book_page_spec`'s own code — extended here from CARD-200's own established
    width-invariance precedent to height too, verified against the real function body)
    and threads the TOC-shifted `first_page` into `puzzle_section` itself. This means
    `app.py`'s `_printed_places` (the Arrangement screen's own page-number display,
    CARD-140) needed **zero changes** for CARD-200: it already calls `section_plan`
    and reads `page.page_number` off the same plan `interior_stream` draws from, so it
    picked up the TOC's shift automatically, the same "decided once, read twice"
    discipline `section_plan`'s own docstring already promises for the pairing walk.
  - `create_toc_page`'s own per-page entries budget (`_toc_entries_per_page`) reserves
    **one folio line's height up front**, not just a rounding remainder: unlike
    `create_guide_page` (where AC-8 forbids reshaping the existing fallback-fitting
    loop to leave footer room), the TOC is new content with no byte-identity
    constraint, so it can and should guarantee every TOC page — including a
    fully-packed one — has its own slack for the folio. Found and fixed during this
    card's own test-writing (`tests/test_book_toc.py`'s
    `test_the_toc_itself_carries_a_folio_on_every_one_of_its_pages`), not assumed safe.
  - `book_kdp.unpaired_interior_page_count` needed **no functional edit** — it already
    omits `toc_pages`, picking up `interior_page_count`'s own Book-1-profile default —
    only a docstring addition explaining that reliance explicitly (the card's own
    warning about "the exact shape of gap CARD-202's review cycle had to fix once
    already" is about a *silent* reuse; this one is examined and stated, with its one
    known imprecision named: a book stored on a smaller-than-Book-1 trim could in
    principle need one more TOC page than this sheet-free estimate states, the one
    place this function's otherwise-upper-bound contract is approximate rather than
    provably safe — acceptable because this function only fires when the book's own
    stored spec cannot be laid out at all).

  **Multi-page TOC split (the card's own open question, resolved):** real,
  measured-geometry entries-per-page (`_toc_entries_per_page`), not a fixed
  entry-count guess — the same font/metric calls (`_guide_face`, `_band_font`,
  `type_px`) every other page's own fitting already reads, applied to **this book's
  own trim** (`page_frame(self.page_spec(1))`, parity-invariant) inside
  `section_plan`/`interior_stream`, and to CON-018's Book 1 profile
  (`_default_toc_frame`) only for the sheet-free default path (bare
  `interior_page_count` calls, `book_kdp`'s estimate). Every TOC page repeats
  `TOC_TITLE` ("Table of Contents"), so the per-page budget is uniform across the
  whole TOC regardless of how many pages it takes — no first-page-special-casing.
  Overflow (AC-6) is a plain `ceil(entry_count / entries_per_page)` page count,
  computed once and reused verbatim by `produce()`'s own slicing loop — one source of
  truth for the split, never two.

  **Owner-visible defaults (need confirmation before merge):**

  1. **TOC position: right after the guide page(s), before the first divider/puzzle
     page.** Implemented as the card's own reading. See the TOC render,
     `03-toc.png`, below.
  2. **Folio style: bottom-outer-corner, plain decimal (`"3"`, `"12"`), no "Page"
     word, no rule or ornament.** Implemented as the card's own reading. Visible on
     every render below.
  3. **Solved-answer page: folio and caption share the bottom slack, opposite
     corners (caption centred, folio at the outer edge).** Implemented, and
     **actually rendered and looked at**, not just reasoned about: see
     `12-answer-or-solutions.png` (Puzzle 3 — Tree, a full/unpacked answer page) and
     `11-answer-or-solutions.png` (Puzzle 1/2 — Duck/Owl, a packed 2-up answer page)
     below — the caption sits centred above the slack's midline, the folio flush at
     the opposite (outer) corner, no visual collision at either page's own trim. This
     is the one item CARD-203 (independently moving the caption's own alignment) may
     still interact with if both are in flight at once — coordinate before either
     merges, per the card's own note.
  4. **The TOC and the guide pages themselves carry a visible folio (only the cover
     is exempt).** Implemented as the card's own reading. See `01-guide.png`/
     `02-guide.png` (both guide pages carry a folio) and `03-toc.png` (the TOC page
     carries one too) below.

  **SCOPE+ files** (beyond the card's own Touches list, each a genuine downstream
  ripple from the TOC's page-count/page-number shift, not scope creep):

  - `tests/test_book_export_interior_cover.py` — `STANDARD_BOOK_PAGES`/`_interior_pages`
    gained a `toc_pages` term; two hard-coded page-count assertions recomputed.
  - `tests/test_book_interior_type_floor.py` — `PAGE_COUNTS` picked up the new
    `BASELINE_PAGE_COUNT` automatically (via `tests/helpers/book_corpus.py`); the
    divider-face-count assertion doubled (word + folio, two `draw.text` calls now) and
    the DPI-independence test's own expected-sizes list gained the folio's own entry
    (with its own whole-pixel-rounding note — 10.0 pt rounds to 10.08 pt at 300 DPI,
    not exactly 10.0, same as the divider's own exact 14.4 pt does *not* round).
  - `book_pdf_generator.py` (within Touches, but the ripple's exact shape wasn't
    predicted by the card's own grep): `_packed_answer_page` (CARD-202's packed
    small-answer page) needed its own folio call — not named in the card's "What to
    implement" point 2's five-method list at all, since CARD-202 postdates the card's
    original Touches grep.
  - `tests/property/test_book_export_interior.py` — the packed-answer-page column-ink
    measurement (`test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`)
    cropped the **full page height** to find each half's leftmost ink; the new folio
    (flush with the usable area's outer edge, which on a left-hand page is the same
    side a packed tile's own left edge is near) landed inside that crop and corrupted
    the measurement on at least one generated case. Fixed by cropping above
    `BOTTOM_MM + 6mm` (comfortably more than one folio line, comfortably less than
    where any packed tile's own ink ever reaches) before the ink scan — a test-only
    fix, not an implementation change.
  - `test.db` — an unrelated, pre-existing, mistakenly-tracked sqlite artifact (from
    a much older book-scaffolding card) was removed from the tree as a side effect of
    running the local test suite during this card's work; incidental, not a CARD-200
    decision, noted here only so the diff's provenance is honest.

  **AC / guardrail evidence (fresh, this session, from the implementation worktree —
  orchestrator's own independent gate below is the authoritative confirmation):**

  - AC-1/AC-2/AC-3/AC-9: `tests/test_book_page_numbers.py` —
    `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`,
    `TestBookPageNumbers_CoverIsNeverNumbered`,
    `TestBookPageNumbers_FoliosMatchInteriorStreamsOwnArithmetic`,
    `TestBookPageNumbers_ParityHoldsWithTheTocInserted` — 7 tests, all passing.
  - AC-4/AC-5/AC-6: `tests/test_book_toc.py` —
    `TestBookToc_ListsEveryPuzzleAgainstItsRealPageNumber`,
    `TestBookToc_TitleResolutionMatchesTheAnswerSections`,
    `TestBookToc_OverflowsToASecondPageWithoutLosingAnEntryOrBreakingLaterNumbering`
    — 7 tests, all passing.
  - AC-7: `tests/test_book_interior_type_floor.py::TestInteriorType_EveryFaceHoldsTheFloor`
    — unedited in its own AC-1 class, passes with the folio as one more walked
    `draw.text` call; 21 tests in the file, all passing (2 updated for the new call
    shape, see SCOPE+ above).
  - AC-8: `tests/test_book_pdf_memory.py::TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`
    against the new `tests/fixtures/book_baseline_card200.json` — 6 tests (every
    puzzle/divider page, both guide pages, the SOLUTIONS divider, every answer page,
    a negative control that a genuinely different puzzle still fails the comparison,
    and a control that the crop really does remove a folio) — all passing.
  - Guardrails: G-1 (no new `PageSpec`/`Layout`/`Placement` field — confirmed, zero
    edits to `export/layout.py`), G-2 (`create_cover_page` untouched — confirmed, no
    diff to that method), G-3 (confirmed structurally — `_stroke_drawing`,
    `_write_clues`, `_set_band`, `_draw_solved_slot`'s caption logic and
    `draw_example_line` all have zero diff against the pre-card commit — and
    behaviourally, by AC-8's own content-comparison test above), G-4 (`FOLIO_PT`/
    `TOC_ENTRY_PT` = 10.0, CON-020's floor exactly, held by AC-7's test), G-5 (no
    edits to `export/layout.py`, so FR-032/FR-030 are read, not changed), G-6 (no
    edits to `band_identity`, `puzzle_pages`'s pairing/numbering logic, or
    `puzzle_section`'s level-grouping — only the `first_page` input each already took
    as a parameter shifted).

  **Renders:** `~/Documents/nonogram-reviews/CARD-200/` — a 4-puzzle, 3-level sample
  book (`tests/helpers/book_corpus.baseline_puzzles`: Duck/Owl easy-paired two-up,
  Tree medium one-up, Snowflake hard one-up), every interior page exported as its own
  PNG (`00-cover.png` through `13-answer-or-solutions.png`) at 50% scale, plus the
  full `interior.pdf`/`cover.pdf`. Covers every page kind the card asked for: guide
  (`01`/`02`), TOC (`03`), divider (`04`/`06`/`08`), two-up (`05`), one-up (`07`/`09`),
  SOLUTIONS divider (`10`), packed answer (`11`), full answer (`12`/`13`).

  **Blockers:** none. All 9 acceptance criteria pass with fresh evidence; all 6
  guardrails hold; both explicitly-flagged open design questions (multi-page TOC
  split, the four owner-visible defaults) are resolved with stated reasoning above,
  not silently guessed.

- [Process note — subagent overspawn, same session] This card's implementation agent
  independently spawned 10 nested child agents (7 "fork", 3 "general-purpose") over
  ~40 minutes to parallelize test verification — far more than this card's own scope
  warranted. One child, several levels removed, messaged the orchestrator directly as
  if a peer collaborator, and the top-level agent itself separately believed a
  distinct "main" agent was concurrently implementing the same card — both were
  actually observing echoes of the same shared worktree through the nested fork tree.
  No repo corruption resulted (git history stayed linear throughout, confirmed at
  every check), but it produced real, avoidable cost: up to ~13 concurrent `pytest`
  processes against the same worktree/test database at once, which (a) wasted
  significant compute, (b) produced at least one genuinely flaky full-suite failure
  downstream (`TestBookPdfMemory_RealBookExportsUnderTheCap`'s memory-margin
  assertion, confirmed via two clean isolated re-runs to be resident-memory
  measurement noise from system-wide memory pressure, not a real regression), and (c)
  meant neither the implementer nor its children ever obtained a trustworthy
  whole-repo test run themselves — every "full suite" claim from that side of this
  card's work is, by its own admission, a per-file isolation result, not a true
  merge-gate run. The orchestrator identified this mid-task (via `ListAgents`,
  unprompted by the user), sent explicit stop instructions to all 10 descendants
  individually once it became clear a single message to the one agent that happened
  to make contact was not reaching the others, and ran its own independent,
  authoritative full-suite gate only once the environment was confirmed quiet. Filed
  as process feedback (not a CARD-200 defect) for the pipeline itself to learn from.

- [Build gate, attempt 1] Orchestrator's own independent full-suite run — first
  attempt failed to even start (used a relative `./.venv/bin/python`, but this
  worktree, unlike CARD-201/202's, never had its own `.venv` — a worktree/venv
  setup gap, not a code issue; fixed by using the main repo's venv by absolute
  path, the same path every background agent process was already using). Once
  actually running: **6820 passed, 9 skipped, 1 failed, exit 1** (954.44s). The one
  failure, `TestBookPdfMemory_RealBookExportsUnderTheCap::test_one_cap_the_streaming_shape_survives_and_the_list_shape_dies_under`,
  is a real-process memory-margin assertion (measured resident memory must stay
  under `CHILD_CAP_BYTES / CHILD_HEADROOM`, `CHILD_HEADROOM = 3`) — failed by a
  razor-thin margin (measured 275.0 MB against a ~269.3 MB threshold, ~2% over).
  Investigated rather than dismissed: re-ran the same test class twice, in true
  isolation, with the full-suite lock released and zero other pytest processes
  running (confirmed via `ps aux`) — both re-runs passed clean (7 passed, 1
  skipped). This confirms the single failure was resident-memory measurement
  noise from this session's own extreme, unprecedented concurrent-process load
  (the subagent-overspawn incident above), not a reproducible CARD-200 regression
  — the two tests this session had independently flagged as possibly flaky under
  load (`test_book_order.py`, `test_book_pdf_geometry.py`) both passed clean in
  this same run, further corroborating "contention noise", not "code bug".
- [Build gate, attempt 2 — FINAL] Orchestrator's own independent full-suite
  re-run, environment confirmed quiet beforehand: **6821 passed, 9 skipped, 0
  failed, 0 errors, exit 0** (952.98s) — one more passing test than attempt 1,
  exactly the previously-flaky memory-margin test, now stable. Gate clear —
  proceeding to forge:review cycle 1.
- [Review] forge:review cycle 1 started (background agent `@code-review`).
- [Review 1/3] 4 findings, most-severe first (standalone skill invocation,
  no numeric score returned — orchestrator's own severity read below):
  - **F-1 (Critical — reproducible visual defect: folio overlapping puzzle
    ink)** `book_pdf_generator.py:3300` (`_blank_page`), `:3401`
    (`_two_up_page`), `:3690` (`_packed_answer_page`): all three call
    `_draw_folio` unconditionally, with no `content_bottom`, so the
    collision check treats the ENTIRE usable height as free room instead
    of the grid's real bottom/right edge. Reproduced by the reviewer
    directly calling `compute_layout`: a 30x30 puzzle with row-clue depth
    1 / column-clue depth 10 on Book 1's default trim gives
    `usable_bottom - drawing_bottom == 0` and `usable_right -
    drawing_right == 8px`, while the folio digit is 27-81px wide — the
    page number prints directly on top of the puzzle's own grid border
    and clue digits. Contradicts `_blank_page`'s own docstring claim that
    the grid "is centred well inside its margins in practice" (empirically
    false for a page-fit-bound grid) and AC-1's own "too small a slack,
    omit" rule. `solved_puzzle_page` already gets this right (reuses the
    caption's own `drawing_bottom` slack check) — the other three page
    kinds need the same treatment. Gating.
  - **F-2 (Important — contract violation, narrow but real physical-print
    risk)** `book_kdp.py:457`, `unpaired_interior_page_count` omits
    `toc_pages`, falling back to `interior_page_count`'s Book-1-profile
    TOC estimate regardless of the book's own (possibly smaller) trim —
    already disclosed in the implementer's own docstring as "could in
    principle need one more TOC page than this estimate states," but the
    reviewer correctly escalates this past a disclosed-limitation note:
    this function's own contract is "upper bound, never an under-count,"
    and its return value feeds the KDP gutter-band lookup for exactly the
    one case (an unreadable/unlayable stored spec) where there is no real
    sheet to cross-check the estimate against — an under-count here can
    select a laxer (too-narrow) gutter band than the book will actually
    need once its trim is fixed, a real binding/print-margin risk, not
    just an imprecise number. Gating.
  - **F-3 (Minor, not gating):** `puzzle_pages`'s default `first_page:
    int = 1 + GUIDE_PAGE_COUNT` (`:3698`) was not updated for the TOC
    offset — stale, but self-consistent with `test_book_pairing.py`'s own
    unchanged direct-call assertion (both equally stale, nothing breaks
    today); a future caller trusting the default would get a wrong page
    number with no error. Worth a docstring note or an update, not urgent.
  - **F-4 (Minor, not gating):** `TOC_ENTRY_GAP_PT` (`:3070`) is documented
    only as a vertical leading constant but is reused for the horizontal
    label/page-number gap in `create_toc_page` — undocumented double duty,
    a future vertical-spacing retune would silently also change horizontal
    spacing.
  - **Verdict: cycle 1 does not meet the bar** (2 gating findings: F-1 a
    reproducible visual defect, F-2 a KDP-gutter contract violation) —
    routing to forge:fix for F-1/F-2, cycle 2.
- [Fix 1] F-1/F-2 fixed in the worktree (full details in that branch's own
  `[Fix 1]` entry, commits `b2a1aed`/`8cf5490`/`c616faf`). **F-1**: reproduced
  the reviewer's exact page-fit-bound scenario first, then found the same
  defect already latent (masked by a loose tolerance) in the card's own
  `_min_trim_book` test fixture. `_draw_folio` gained optional
  `content_right`/`content_left`, consulted only when `content_bottom`
  already shows no vertical room, so a real corner collision can be told
  apart from a one-axis false positive. `_blank_page` now recomputes its own
  puzzle's real `Layout` for a true `content_bottom`; `_two_up_page` reads
  all four figures off `pair.lower.page` (confirmed — not `pair.upper.page`
  — the true bottom-outer slot); `_packed_answer_page` identifies whichever
  tile can physically reach the folio's own corner, passing no content
  figures when that corner was left unfilled. New test class
  `TestBookPageNumbers_FolioNeverCollidesWithTheGrid` (7 tests) plus an
  update to the pre-existing min-trim test. Evidence:
  `test_book_page_numbers.py` 14 passed; combined related-file run 508
  passed, 1 skipped (pre-existing unrelated platform skip); full suite 6833
  passed, 9 skipped, 0 failed (12 more passing than the prior gate, matching
  the 12 new tests added). **F-2**: `unpaired_interior_page_count` now
  measures its TOC estimate against the book's own stored `trim_height_cm`
  (via a synthetic stand-in carrying `BOOK1_PROFILE`'s safe width/margins
  through the real `book_page_spec` validator), falling back to the Book 1
  profile only when truly nothing can be measured — never smaller than the
  old default. `_toc_page_count`/`_default_toc_frame` made public as
  `measured_toc_page_count`/`default_toc_frame` (renamed, not just
  un-prefixed, to dodge a real `UnboundLocalError` against `section_plan`'s
  own same-named local). New test class
  `TestBookFinaliseGutter_UnpairedPageCountNeverUnderCountsTheToc` (5 tests).
  F-3/F-4 left untouched, per the review's own explicit scope.
- [Build gate, attempt 3] Orchestrator's own independent full-suite
  confirmation of the Fix 1 commits, environment quiet beforehand: **6833
  passed, 9 skipped, 0 failed, 0 errors, exit 0** (952.98s) — matches the fix
  agent's own reported evidence exactly. Gate clear — proceeding to
  forge:review cycle 2.
- [Review 2/3] Confirmation cycle, differential re-review of the fix delta
  (standalone skill invocation). **Verdict: both F-1 and F-2 hold** — risk
  LOW, lane FAST, score **8.5/10**. 0 Critical, 1 Important, 1 Minor, 2
  Out-of-scope. Adversarially re-derived (not just re-running the fix
  agent's own new tests): re-derived the two-up/packed-answer geometry
  directly against `PairLayout`/`PackedSolvedLayout`, confirmed the two-up
  page's *upper* slot structurally cannot reach the folio corner, traced
  `book_kdp`'s one real production call site (`app.py:944`) plus confirmed
  the second, unmodified call site (`app.py:1069`) is genuinely unaffected,
  and ran a capped 3-mutant mutation check (capture/mutate/test/restore, all
  restores verified byte-clean). Result:
  - **F-001 (Important)**: the mutation check found a real, reachable gap —
    `plan_small_answer_pages`'s "single leftover puzzle on a right-hand
    page" shape (where the packed-answer page's corner slot is left empty)
    isn't exercised by the new F-1 regression tests, which only ever built
    fully-filled packed pages; a mutant flipping the corner-slot gate's `<`
    to `<=` survived against that test file alone (though caught
    incidentally by 8 unrelated files, and confirmed via a direct scratch
    probe that the real, unmutated code already handles the case correctly
    — a test-coverage gap, not a live bug).
  - **F-002 (Minor)**: a stale docstring reference to the pre-rename private
    function name in `tests/test_book_arrange_page_breaks.py:123`, missed
    by F-2's rename — cosmetic only.
  - System contract: 53 rules checked, 8 ✓ holds, 45 ⚠ unchecked (44
    `no_eligible_fact`, 1 pre-existing `check_ref_missing` on ADR-0006/R1,
    unrelated model drift), 0 ✗ violated.
  - F-3/F-4 not re-flagged, per instruction.
- [Fix 2] F-001/F-002 fixed in the worktree (full details in that branch's
  own `[Fix 2]` entry, commits `0254401`/`d2706db`) — **test-only change, no
  production code touched**. Added
  `test_packed_answer_page_with_one_leftover_answer_still_draws_the_folio`
  to the same class: a capacity-2 `PackedAnswerPage` with exactly one
  leftover answer, landing in the folio's own corner slot (empty) on a
  right-hand page — the one shape where `<` and `<=` disagree. Mutation-probe
  discipline run directly: captured the file's SHA-256, reproduced the exact
  mutation, confirmed the two pre-existing tests still miss it (2 passed),
  confirmed the new test now fails on it (`IndexError: tuple index out of
  range`, exactly as predicted), reverted, re-checked SHA-256 identical —
  byte-clean restore. F-002's docstring updated to the real current name
  (`measured_toc_page_count`); `_toc_entries_per_page` confirmed correctly
  untouched by the rename. Evidence: `test_book_page_numbers.py` +
  `test_book_arrange_page_breaks.py` 34 passed; full suite 6834 passed, 9
  skipped, 0 failed (exactly one more than the prior gate). F-3/F-4 remain
  untouched.
- [Build gate, attempt 4] Orchestrator's own independent verification of the
  Fix 2 commits (test-only change — a full 16-minute suite rerun judged
  unnecessary given the change's minimal risk surface): targeted run of both
  touched test files, **34 passed, 0 failed, exit 0**, matching the fix
  agent's reported evidence. Diff confirmed test-only via `git diff --stat`
  (2 test files + card notes, no production file touched). Gate clear —
  proceeding to forge:review cycle 3.
- [Review 3/3 — FINAL] Confirmation cycle, differential re-review of the
  tiny test-only fix delta (standalone skill invocation). Independently
  re-derived the F-001 mutation probe rather than trusting the fix agent's
  self-report: reproduced the exact mutation, got the exact same 7-passed/
  1-failed split with the identical `IndexError`, reverted, confirmed a
  byte-identical restore via SHA-256 — plus independently traced
  `PackedSolvedLayout`'s own construction arithmetic to confirm the test's
  geometry claim is correct, not just empirically passing. F-002 confirmed
  correct against the real current function names. **Verdict: 0 Critical, 0
  Important, 0 Minor, 0 Out-of-scope — score 10.0/10. Card is ready to
  merge.** System contract: 53 rules checked, 8 ✓ holds (carried forward,
  scope doesn't intersect this delta), 45 ⚠ unchecked (1 carried
  `check_ref_missing`/ADR-0006/R1, 7 freshly re-verified `no_eligible_fact`
  for touched test-file scope, 37 carried `no_eligible_fact`), 0 ✗ violated.
  Review reports synced from worktree to main: `meta/review/
  20261009T174945Z-CARD-200-cycle2.yml`, `meta/review/
  20261009T193000Z-CARD-200-cycle3.yml` (no cycle-1 YAML was ever found to
  sync — that cycle's standalone invocation did not produce one before
  handing back; noted, not fixed retroactively).
- [Merge gate] Merged to `main` (`--no-ff`, commit `e899369`). `CARD-200.md`
  itself conflicted with the branch's own copy (the branch had the original
  implementation notes plus `[Fix 1]`/`[Fix 2]` headers written directly to
  its own worktree copy, already incorporated above in bullet form) —
  resolved by keeping main's authoritative copy (`git checkout --ours`), no
  information lost. Independent full-suite merge-gate run on `main`
  post-merge: 6761 passed, 82 skipped, 0 failed, 0 errors, exit 0 (1028.91s)
  — same total test count as every prior gate this card (6843), but 73 more
  skips than the stable 9-skip baseline. Investigated rather than waved
  through: traced the skip cluster to `tests/test_print_specs.py` and
  neighbors via progress-line position, confirmed Postgres and
  `nonogram_test` were both up, then reran the suspect files in isolation —
  **264 passed, 0 skipped, 0 failed**, clean. Transient environmental
  flakiness (same class as this session's earlier documented Postgres-
  contention and memory-margin flakes), not a CARD-200 regression — the
  actual correctness signal (0 failed, 0 errors) was already clean on the
  first run. Gate clear.
