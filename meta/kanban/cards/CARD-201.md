# CARD-201: The guide page becomes a 2-page "How to Solve a Nonogram" tutorial, sourced from the owner's reference guide

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 2d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/201-guide-page-how-to-solve
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-201
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 2: how-to-solve section + difficulty-label description, content from docs/guides/how_to_solve_nonograms_v2.pdf)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/app.py, src/nonogram/admin/templates/book_finalize.html, src/nonogram/admin/static/admin.css, docs/guides/how_to_solve_nonograms_v2.pdf, tests/test_book_guide_page.py, tests/test_book_guide_page_type.py, tests/test_book_interior_type_floor.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_ink_mode.py, tests/test_book_finalise_guide_preview.py, tests/test_book_finalise_gutter.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card201.json (new)
**Review score:** —
**Started:** 2026-10-08T14:32:38Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- The interior's guide page is exactly one page, drawn by
  `BookPDFGenerator.create_guide_page` (`book_pdf_generator.py:1556-1671`),
  titled `GUIDE_TITLE` = "How to Solve Nonograms" (`:436`), with
  `GUIDE_INTRO` (`:446-451`), a puzzle-count breakdown, `GUIDE_EXAMPLE_HEADING`
  (`:455-458`), the four-step `WORKED_EXAMPLE_STEPS` worked example (clue
  `3 1` on 6 squares, `:491-519`) and `GUIDE_CLOSING` (`:463-465`). It is drawn
  in one of three fallback forms — full, captions-only, labels-only
  (`set_page(full, captions)`, `:1628-1662`) — whichever is the first to fit
  above the bottom margin; this exists because a small trim cannot hold the
  full text on one page, and the page is contractually always exactly one
  page (FR-041's own statement, see below).
- This is CARD-167 (retitled the page, added the worked example) and
  CARD-169 (made the Finalise screen's preview read the same constants, so
  the two can't drift). **Both cards explicitly deferred this card.**
  CARD-167's own "What to implement" says verbatim: *"The full 1–2 page
  tutorial the owner's design doc describes is NOT this card. It waits for
  the page layout to be final and gets its own requirement."* FR-041's own
  amendment (2026-10-04 (a)) says the same: *"The full 1-2 page tutorial is
  deferred to its own requirement."* This card is that requirement.
- The worked example's line diagrams are drawn by `example_line_layout`
  (`:1191-1212`, calls `compute_layout` with `WORKED_EXAMPLE_CLUE`/
  `WORKED_EXAMPLE_LENGTH` as a one-row puzzle on the book's own `PageSpec` —
  the cell pitch, rules, frame and clue size of a real puzzle page) and
  `draw_example_line` (`:1215-1244`, takes that `Layout` plus one
  `ExampleStep`'s `filled`/`crossed` 0-based square sets and returns a
  cropped image: fills, crosses at the thin rule, then `_stroke_drawing`/
  `_write_clues` over them). **Both are hard-wired to the one module-level
  clue/length pair** (`WORKED_EXAMPLE_CLUE = (3, 1)`, `WORKED_EXAMPLE_LENGTH
  = 6`) shared by all four existing steps — the new content needs several
  *different* clues and lengths on different lines (a 10-cell complete line,
  two 8-cell squeeze lines, a 3-on-a-line mark-spaces example, a "2 3" clue
  split by known empties, three short comparison lines), so this card must
  generalise these two functions to take their clue/length as parameters
  rather than reading the module constants — a real, in-scope refactor, not
  a drive-by.
- The Finalise screen's "Guide page" preview card
  (`templates/book_finalize.html:46-79`) renders the **same** constants the
  PDF prints — `guide_title`, `guide_intro`, `guide_example_heading`,
  `guide_steps` (each with a `.guide-strip` of `.guide-strip-cell[data-state]`
  spans), `guide_closing` — read at request time from
  `book_pdf_generator.GUIDE_*` / `WORKED_EXAMPLE_*` in `app.py:4668-4673`
  (the Finalise GET handler's context dict), styled by `.guide-preview`/
  `.guide-steps`/`.guide-strip`/`.guide-strip-cell` in `admin.css:326-338`.
  CARD-169 built this specifically so the printed page and the owner-facing
  preview cannot drift — this card must keep that contract, not bypass it by
  adding a second, independently-worded preview.
- **The page-count ripple is centralised in one place.**
  `interior_page_count` (`book_pdf_generator.py:1277-1353`) is the single
  function every page-count consumer calls — the `_as_planned` tripwire
  inside `interior_stream`, `book_kdp.unpaired_interior_page_count`
  (`book_kdp.py:355-416`, via its own call into this same function at
  `:416`), and the Finalise screen's own counts. Its return statement,
  verbatim:
  ```python
  return 1 + dividers + pages + (answers + 1 if puzzle_count else 0)
  ```
  The leading `1` is the guide page's own term — the ENTIRE ripple of this
  card's page-count change is this one literal becoming `2` (or a named
  constant, the implementer's call — `GUIDE_PAGE_COUNT = 2` beside
  `GUIDE_TITLE` reads better than a bare `2` in the formula). Its own
  docstring ("one guide page, one divider per non-empty level...") needs the
  matching one-line correction.
  The two places that assume `first_page=2` (meaning "the guide takes
  exactly page 1, puzzles start at page 2") are `puzzle_pages`'s and
  `puzzle_section`'s own default parameter (`book_pdf_generator.py:2155` and
  `:2267`), both consumed through `section_plan`'s unparameterised call
  `self.puzzle_section(payloads, ids=ids)` (`:2411-2437` body, call at the
  `pages=` line) — this default must become `3`. `interior_stream`'s own
  `first_answer_page = 3 + len(section)` (`:2642`) must become `4 +
  len(section)` (one more for the guide's second page). The guide itself is
  drawn by one `create_guide_page(..., page_number=1)` call inside
  `produce()` (`:2684-2690`) — this becomes two calls (or one call returning
  two images), `page_number=1` and `page_number=2`, each yielded and
  `del`eted exactly as every other page is (CARD-145's two rules, restated
  in CARD-198's own docstring, still hold).
- `tests/test_book_interior_type_floor.py` already instruments
  `create_guide_page` by name (`:169-170`, `_is_a_guide_call`) and requires
  the `{"guide", "divider", "band"}` set of observed call kinds
  (`:301`) — whatever this card names its new drawing helper(s), this file's
  face-classifier needs to recognise them too, or the floor check silently
  stops covering the guide page's new text and diagrams.

**Content to reproduce (owner-supplied, `docs/guides/how_to_solve_nonograms_v2.pdf`,
2 pages, currently untracked in git — `git add` it as part of this card's
commit).** The owner's note "I like your format, (fonts etc..)" means: redraw
this content in the book's own established type sizes (`GUIDE_TITLE_PT`,
`GUIDE_BODY_PT`, `GUIDE_LEADING_PT`) and diagram style (the puzzle's own
cell/rule/clue drawing via `compute_layout`+`_stroke_drawing`+`_write_clues`,
the same primitives `draw_example_line` already uses) — NOT a pixel-faithful
reproduction of the source PDF's own typesetting (its own headings, grey
boxes and three-column layout are that document's own design, not this
book's).

Page 1 — "How to Solve a Nonogram" (or keep today's `GUIDE_TITLE` text,
see owner-decision flag below):
1. Intro line ("Read the clues. Fill what must be black. Mark what must be
   empty.").
2. "The basic rule": a clue is a run of consecutive filled cells, in order,
   with >= 1 empty gap between runs — worked with a "3 2 1" line example
   (a new, different clue/length pair from today's worked example).
3. "Use three cell states": three small icons/labels — Unknown (blank
   square), Filled (black square), Empty (crossed square) — each with its
   one-line caption.
4. "Start with certainty", three numbered techniques each with a one-line
   diagram: (a) "Complete lines" — clue `10` fills a 10-cell line entirely;
   (b) "Squeeze from both ends" — clue `8` on an 8-cell line shown pushed
   left, then pushed right, with the overlap marked "certain"; (c) "Mark
   spaces around a completed block" — a completed run of 3 with the cells
   beside it crossed.
5. Closing callout, "Keep switching between rows and columns" (text only,
   no diagram).

Page 2 — "When the puzzle gets harder":
1. Intro line.
2. Three numbered techniques, each with a one-line diagram: (a) "Use what
   you already know" — clue `2 3` on a line with some cells already known
   empty, splitting it into regions, one too small for either run; (b)
   "Keep what every arrangement agrees on" — three candidate arrangements of
   one line compared, with a "compare" label; (c) "Assume, and watch it
   break" — a 4-step ASSUME -> FOLLOW -> BREAKS -> PROVED pipeline (this one
   is NOT a puzzle-line diagram — scope it as a simple 4-box sequence with
   an arrow between each, book typography, no new iconography invented
   beyond what the source PDF already shows), plus the closing italic line
   "This is not guessing: erase the temporary trial and keep only what the
   contradiction proves."
3. **"What the difficulty labels mean"** — a highlighted box, three columns:
   EASY ("Squeezing and direct deductions are enough from start to
   finish."), MEDIUM ("Needs deeper line logic and may need contradiction
   for part of the grid."), HARD ("Contradiction reasoning is needed through
   much of the grid."). **This box alone is the doc's entire "description of
   what our difficulty levels are about" ask — carry its three sentences
   verbatim; there is no separate difficulty-description requirement to
   invent.**
4. Closing line, "One solution. No guessing." + the sentence "Every puzzle
   in this book is checked by the solver before publication. There is
   exactly one solution, and no puzzle that requires guessing is included."
   (consistent with CON-005/the mandatory uniqueness property — a true,
   already-enforced claim about this project's solver, safe to print
   verbatim).

**Target.**

1. Generalise `example_line_layout`/`draw_example_line` to take an explicit
   clue and line length instead of reading `WORKED_EXAMPLE_CLUE`/
   `WORKED_EXAMPLE_LENGTH` — every existing call site (the four current
   worked-example steps) passes the same two constants explicitly, so this
   is a signature change with zero behavioural diff at the four existing
   call sites (a guardrail, not just a target).
2. Add the new content's module-level constants and diagrams beside the
   existing `GUIDE_*`/`WORKED_EXAMPLE_*` ones, each line diagram built
   through the generalised helpers from (1); the three-cell-state icons,
   the three-arrangements comparison and the 4-step pipeline need their own
   small drawing routines (no existing primitive fits them directly) —
   simple boxes/labels in the book's own ink/rule style, not a new visual
   language.
3. `create_guide_page` (or a new sibling method — implementer's call,
   document the choice) draws **two** pages instead of one: page 1 holds
   today's intro-rule-states-techniques-closing content (section above),
   page 2 holds the harder-techniques + difficulty-box + closing content.
   The three-fallback-form mechanism (full / captions-only / labels-only)
   must still exist per page — a 2-page tutorial is MORE text, not less, so
   the smallest supported trims need this fallback at least as much as
   today's single page does; measure honestly whether the owner's existing
   trim corpus (CARD-167's "10 cm minimum trim" case) still fits even in the
   labels-only form across 2 pages, and flag it if it does not (see
   ambiguity below — don't silently assume it fits).
4. `interior_page_count`'s leading `1` becomes `2` (point above); its
   docstring sentence corrected to match. `puzzle_pages`/`puzzle_section`'s
   `first_page` default becomes `3`. `interior_stream`'s
   `first_answer_page` becomes `4 + len(section)`. `produce()`'s single
   `create_guide_page(..., page_number=1)` call becomes two calls (pages 1
   and 2), each `yield`ed and released exactly as today's one page is
   (CARD-145/CARD-198's "no page outlives the yield that hands it on" rule,
   unchanged).
5. `app.py`'s Finalise context dict (`:4668-4673`) and
   `templates/book_finalize.html`'s guide-preview card (`:46-79`) gain
   whatever new constants/steps page 2 introduces, read live from
   `book_pdf_generator` exactly as today's do (CARD-169's "one source of
   text" contract) — including the new difficulty-label box, so the
   Finalise screen's own existing "Difficulty levels" presentation (if any
   elsewhere on that screen — check `book_finalize.html` in full for a
   second, independent difficulty-count display that might now duplicate or
   contradict this box) stays consistent. The footnote "Page 1 of the
   interior PDF — a right-hand page — before the first puzzle."
   (`book_finalize.html`, right after the guide card) needs rewording for 2
   pages.
6. `docs/guides/how_to_solve_nonograms_v2.pdf` is committed (`git add`) as
   the recorded source-of-truth reference for this content, even though no
   code reads the PDF file itself at runtime (the content is hand-transcribed
   into Python constants, same pattern as every other hard-coded guide-page
   string) — note in Worktree notes that the PDF is documentation/
   provenance, not a runtime asset.

## Acceptance criteria

- **AC-1** (happy): *Given* any book, *when* the interior PDF is generated,
  *then* the guide section is exactly 2 pages (interior pages 1 and 2), both
  right before the first puzzle/divider page, and `interior_page_count`'s
  return value (and `_as_planned`'s own check against it) reflects 2 guide
  pages for any puzzle/divider/answer-page combination.
  *test: TestGuidePage_IsTwoPages (in tests/test_book_guide_page.py)*
- **AC-2** (happy, page 1 content): *Given* the book of AC-1, *when*
  interior page 1 is read, *then* it carries the basic-rule explanation, the
  three-cell-states icons/captions, and all three "start with certainty"
  technique diagrams (complete line, squeeze-from-both-ends with its
  "certain" overlap, mark-spaces-around-a-block), each diagram drawn at the
  book's own cell pitch/rule widths/clue face (matching a real puzzle page's
  `compute_layout` output at the same `PageSpec`).
  *test: TestGuidePage_PageOneCarriesTheBasicTechniques*
- **AC-3** (happy, page 2 content): *Given* the book of AC-1, *when*
  interior page 2 is read, *then* it carries the region-splitting example
  (clue "2 3" with known-empty cells), the three-arrangements comparison,
  the 4-step assume/follow/breaks/proved pipeline, and the "What the
  difficulty labels mean" box with its EASY/MEDIUM/HARD sentences verbatim
  from the source PDF.
  *test: TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyBox*
- **AC-4** (boundary, type floor): *Given* every stored book trim this
  project's corpus already tests the guide page at (Book 1, 6x9, and the
  narrowest supported trim), *when* both guide pages are read at each trim,
  *then* every line of type and every diagram's clue digits hold CON-020's
  10 pt floor, using whichever of the (now per-page) fallback forms is the
  first to fit above the bottom margin.
  *test: TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim*
- **AC-5** (boundary, page-count/parity ripple): *Given* a book of 3 easy,
  2 medium and 1 hard puzzle, *when* the interior PDF's page count and every
  later page's parity are read, *then* the SOLUTIONS divider and every
  answer page sit exactly one page later than before this card (interior
  page `N` becomes interior page `N+1`), and every page's parity still
  equals its 1-based position (FR-043/INV-013), unchanged by the extra page.
  *test: TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity*
- **AC-6** (negative, byte-identity): *Given* any book, *when* every
  interior page from the first puzzle/divider page onward is compared
  against the pre-card baseline at the SAME print position shifted by one,
  *then* it is byte-identical — only the guide's own 2 pages differ from the
  pre-card single page.
  *test: TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne
  (in tests/test_book_pdf_memory.py, using a new
  tests/fixtures/book_baseline_card201.json)*
- **AC-7** (happy, Finalise preview sync): *Given* the Finalise screen for
  any book, *when* the "Guide page" preview card is rendered, *then* it
  shows both pages' content (not just page 1's), read live from
  `book_pdf_generator`'s constants (CARD-169's contract — a monkeypatched
  sentinel on any new constant must appear in the rendered preview, the same
  proof `TestFinaliseGuidePreview_ReadsTheGeneratorsText` already uses for
  the existing constants), and the difficulty-label box's three sentences
  appear nowhere else on the screen in contradictory wording.
  *test: TestFinaliseGuidePreview_ShowsBothPages (in
  tests/test_book_finalise_guide_preview.py)*
- **AC-8** (boundary, generalised example-line helpers): *Given*
  `example_line_layout`/`draw_example_line` called with the ORIGINAL
  `WORKED_EXAMPLE_CLUE`/`WORKED_EXAMPLE_LENGTH` arguments (now passed
  explicitly rather than read from the module), *when* the four original
  worked-example steps are drawn, *then* the output is pixel-identical to
  before this card's refactor — the generalisation changes the function
  signature, not what the original call produces.
  *test: TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample*

## Guardrails

- G-1: The original 4-step "3 1 on 6 squares" worked example's content,
  wording and pixel output are unchanged — it is one of several worked
  examples on the 2-page tutorial now, not replaced (AC-8).
- G-2: Every interior page from the first puzzle/divider page onward keeps
  the same content it had before this card — only its page number shifts by
  one (AC-6). No puzzle-page, two-up, divider, or answer-page drawing
  function (`_blank_page`, `_two_up_page`, `create_divider_page`,
  `solved_puzzle_page`) is edited.
- G-3: `export/**` (COMP-007's layout functions) is not edited — every new
  diagram is built through `compute_layout`/`_stroke_drawing`/`_write_clues`
  calls from `book_pdf_generator.py`, the same layer CARD-167's worked
  example already uses (ADR-0036/R2).
- G-4: CON-020's 10 pt floor holds on both guide pages at every stored trim
  (AC-4) — no new text or diagram label is drawn below it.
- G-5: The interior stays black-and-white (CARD-147, DeviceGray) — no new
  diagram introduces colour (the source PDF's grey highlight boxes are
  rendered in the book's own ink/paper tones, not a new grey ink colour).
- G-6: `interior_page_count`'s three OTHER terms (`pages`, `answers`,
  `dividers`) and their own call sites are not edited — only the guide
  term changes (1 -> 2).
- G-7: CARD-169's "one source of text" contract holds for every new
  constant this card adds: the Finalise preview reads it from
  `book_pdf_generator` at request time, never a copy in `app.py`/the
  template (AC-7).

## System contract

_Assembled 2026-10-08 by `system_rules.py --card CARD-201` (53 rules). A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single… (check: review-lens)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio… (check: test: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives… (check: test: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0024/R1 — A repaired random-mode grid is accepted only after a fresh solver run on its own re-derived clues reports solution_count exactly 1. The orchestrator never assumes… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound)
- ADR-0024/R2 — Repairs and redraws advance the same RetryCounter bounded by MAX_RETRY_ATTEMPTS (30 since ADR-0002/R1; 20 when this rule was written). K, the consecutive-repair limit… (check: test: TestRecovery_RepairAttemptsCountAgainstRetryBound)
- ADR-0024/R3 — A repair flips exactly one filled cell and one empty cell of the parent grid, both inside the witness-disagreement set (falling back to the undecided mask only when… (check: test: TestRecovery_RepairKeepsFilledCountExact)
- ADR-0024/R4 — The repair's pair choice is a deterministic function of the grid and the solver's witnesses — the region's filled and empty cells ranked by (row, column) — and draws… (check: review-lens)
- ADR-0024/R5 — The repair policy (POL-006) fires only for random mode. Library mode recovers by POL-001 redraw and image mode by POL-002 pixel nudge; neither ever repairs. (check: review-lens)
- ADR-0027/R1 — The valid requested density for random generation is 1..99 inclusive. Density 0 and 100 are refused as InvalidDensity by validate_density before any grid is drawn;… (check: test: TestGenerateRandom_RefusesDensityZeroAndHundred)
- ADR-0027/R2 — The verdict on a requested density is made only at the validate_density seam. No later pipeline stage (uniqueness, difficulty, export, batch) rejects a request on… (check: test: TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam)
- ADR-0029/R1 — The difficulty of a line-solvable puzzle is derived from the rung of the hardest technique its verifying solve required (simple_overlap < line_dp <… (check: test: TestScoreDifficulty_DeeperLineReasoningScoresHigher)
- ADR-0029/R2 — Technique classification and the strategies list are computed inside the one verifying solve, never by re-solving; the ordered rung list the solver reports IS the… (check: test: TestGenerate_StrategiesRecordedFromTheOneVerifyingSolve)
- ADR-0029/R3 — No clock reading — elapsed_seconds or any other — and no size or density term enters the difficulty score, the tier decision or the strategies list; the score is a… (check: test: PropertyTest_ScoreDifficulty_IndependentOfElapsedTime)
- ADR-0029/R4 — The overlap masks that define the simple_overlap rung are computed relative to the line's already-known cells (the leftmost and rightmost placements consistent with… (check: test: test_every_import_in_the_package_points_inward)
- ADR-0029/R5 — Rung attribution is reported only for a clue set with exactly one solution; a clue set with 0 or >= 2 solutions is not a puzzle, has no grade, and carries no… (check: test: PropertyTest_SolveStrategies_RungsInvariantUnderTransposition)
- ADR-0032/R1 — Every puzzle stored through the admin panel has been proved uniquely solvable by the solver at the storage boundary itself. add_puzzle re-derives the clues from the… (check: test: TestStorageBoundary_AsksTheSolverNotTheCaller)
- ADR-0032/R2 — quality_score is an integer 1..100 when the conversion was measured and None when there was nothing to measure; None means unknown, not zero. An unmeasured puzzle… (check: test: TestUnmeasuredQuality_SurvivesTheFilter)
- ADR-0033/R1 — Book assembly references puzzles by id and never changes a puzzle's grid, clues, difficulty tier or strategies; the only puzzle field it may write is the… (check: review-lens)
- ADR-0035/R1 — No book leaves draft (to any other status) unless it has a stored plan and every longest-side x tier cell's count, divided by the planned total, is within +/-3… (check: test: TestBookStatus_EveryExitFromDraftIsGatedOnThePlan)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin… (check: review-lens)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unchanged. (check: review-lens)
- ADR-0038/R1 — The puzzle player's client is hand-written JavaScript and CSS served as static files by the admin panel. There is no front-end framework, no build step, no npm… (check: review-lens)
- ADR-0038/R2 — Marking, undo, redo, the error count and the solved check run entirely in the browser. A loaded player page issues no network request per mark. (check: test: TestSolverMarking_NoRequestPerMark)
- ADR-0038/R3 — The player page's clues are embedded as JSON from compute_clues of the stored grid (the one encoder). The client never re-derives clues from the solution. (check: test: TestSolverPage_ShowsTheClues)
- ADR-0038/R4 — The player's state logic (board, strokes, undo/redo history, error count, solved predicate) lives in a pure module with no DOM access, separate from rendering. (check: review-lens)
- ADR-0038/R6 — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution grid to the browser. A public or reader-facing player must not send the… (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- CON-015 — The admin panel's own entry point binds its listening socket to 127.0.0.1 (loopback) only and runs with the debugger off. The bind address is a constant, not a… (check: test: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-016 — The admin panel serves a request through exactly one of two mutually exclusive doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does… (check: test: TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, whos… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-021 — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served behind the door that guards every other admin page (CON-015, CON-016). No… (check: review-lens)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: test: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: test: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF, TestRecovery_RecoveredGridIsReverifiedBySolver)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) nev… (check: test: PropertyTest_Recovery_AcceptedGridsHaveRealVerdictsWithinOneBound, TestNudge_ReportsFailureAtCap, TestRecovery_RepairAttemptsCountAgainstRetryBound, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-005 — A book's distribution plan has an easy/medium/hard split summing to exactly 100% and a per-bucket plan of non-negative integer counts (FR-034). (check: test: PropertyTest_BookPlan_PrefillTotalsMatchGeneralPlan, TestBookCreate_StoresDefaultPlanThatSumsTo100, TestBookPlan_RejectsSplitNotSummingTo100)
- INV-006 — A puzzle whose cell on the book's trim is below the 4.8 mm floor is a member of the book only together with an explicit override stored for that puzzle id (FR-031,… (check: test: PropertyTest_BookMembership_BelowFloorOnlyWithStoredOverride, TestBookAddPuzzlesByIds_RefusesBelowFloorWithoutOverride, TestBookAddPuzzles_AcceptsBelowFloorWithOverrideAndRecordsIt, TestBookAddPuzzles_RefusesBelowFloorWithoutOverride)
- INV-007 — A book reaches the ready status only when every longest-side x tier cell of its selection is within +/-3 percentage points of its plan (FR-037). (check: test: PropertyTest_BookReady_GateIffEveryCellWithinTolerance, TestBookReady_AcceptsWhenEveryCellWithinTolerance, TestBookReady_ExactlyThreePointsAccepted, TestBookReady_RefusedBeyondThreePoints)
- INV-008 — A published book's puzzle membership changes only after an explicit confirmation of that change (FR-038). (check: test: TestBookPublished_ConfirmedPuzzleChangeApplied, TestBookPublished_PuzzleChangeRequiresConfirmation, TestBookPublished_UnconfirmedChangeKeepsStatus)
- INV-009 — A book's order is grouped by tier — every easy puzzle before every medium one, every medium before every hard one; within a level the order is the owner's… (check: test: PropertyTest_BookOrder_GroupedByTierUnderAnyEditSequence, TestBookAddPuzzles_PlacesNewPuzzleInsideItsLevel, TestBookArrange_MoveAcrossLevelBoundaryRefused, TestBookArrange_MoveWithinLevelKeepsOwnerOrder, TestBookPdf_DifficultyOrderWithDividerPerLevel, TestBookPdf_LegacyMixedArrangementPrintsGroupedByLevel)
- INV-010 — A book page holds two puzzles only when their tiers are equal, they are adjacent in the book order and both fit at one shared cell of at least 7.0 mm (capped at 7.5… (check: test: PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly, TestBookPdf_DifferentTiersNeverPair, TestBookPdf_FifteenPlusTwelveDoesNotPair, TestBookPdf_OddPuzzleOutPrintsAlone, TestBookPdf_PairFailingWidthAtTwoUpMinimumDoesNotShare, TestBookPdf_PairJustAboveTwoUpMinimumShares, TestBookPdf_PairJustBelowTwoUpMinimumDoesNotShare, TestBookPdf_PairingNeverReordersToFindAPartner, TestBookPdf_TwelvePairSharesPageBelowStandardCell, TestBookPdf_TwoSmallSameTierNeighboursShareAPage)
- INV-011 — The book's answer key holds every member puzzle's answer exactly once, in puzzle-number order; an answer-key page holds at most 6 answers while every answer on it is a… (check: test: PropertyTest_BookAnswerKey_OrderAndCapacityForAnyBook, TestBookAnswerKey_DefaultPlanTakesThirtyPages, TestBookAnswerKey_DefaultPlanThreeLevelsTakesThirtyOnePages, TestBookAnswerKey_EachLevelStartsNewAnswerPage, TestBookAnswerKey_LargeAnswerThatWouldOverfillStartsNewPage, TestBookAnswerKey_LongestSideTwentyStaysSixUp, TestBookAnswerKey_PageBecomesFourUpOnceItHoldsAnswerAbove20, TestBookAnswerKey_SixUpInPuzzleNumberOrder)
- INV-012 — A book outside draft holds exactly the puzzle membership that last passed the plan check (INV-007): adding or removing a puzzle on a book that has left draft returns… (check: test: PropertyTest_BookMembership_ChangedMembershipOutsideDraftNeverPersists, TestBookAddPuzzlesByIds_NonDraftReturnsToDraft, TestBookMembership_AddOnNonDraftReturnsToDraft, TestBookMembership_RemoveOnNonDraftReturnsToDraft, TestBookPublished_ConfirmedChangeReturnsToDraft, TestBookReady_ReturnedToDraftIsCheckedAgainOnNewMembership)
- INV-013 — The book's interior PDF holds no cover page and starts at the guide page as a right-hand page 1; each page's parity is its 1-based position in the interior, and the… (check: test: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage, TestBookExport_EveryRouteSeparatesInteriorAndCover, TestBookExport_FirstPuzzlePageParityCountsFromInteriorPage1, TestBookExport_InteriorHoldsNoCoverPage, TestBookExport_InteriorStartsAtGuidePage, TestBookExport_NoUploadedCoverStillSeparatesGeneratedCover)

_(No check — excluded as narrative, not rules: CON-004, CON-006, CON-007, CON-008, CON-013, CON-017, CON-018. Card scope: `touches`, narrowed to the `Touches:` globs above.)_

## Architecture context

- **FR:** FR-041 (this card fulfils its own deferred "full 1-2 page
  tutorial" clause; the "stays exactly one page" sentence becomes false by
  design — architect-station follow-up to amend it, not this card's job);
  FR-043/INV-013 (page 1 parity, unaffected in its own terms); CON-020 (10
  pt floor).
- **ADR:** ADR-0036/R2 (layout functions place, nothing else does — every
  new diagram reuses `compute_layout`, no new placement logic).
- **Components:** COMP-007 (layout functions, read-only), COMP-009 (admin
  panel: both edited modules, `book_pdf_generator.py` and the Finalise
  route/template, live here).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no
  edit under `meta/`); revisit once the architect station amends FR-041.

## Design context

- **Output:** the interior PDF's pages 1-2 (the guide/tutorial section),
  and the Finalise screen's "Guide page" preview card.
- **Design system:** meta/design/ — the existing `.guide-preview`/
  `.guide-steps`/`.guide-strip`/`.guide-strip-cell` tokens-only rules in
  `admin.css:326-338` are the precedent for any new preview markup (reuse,
  extend — do not invent a new visual language for the Finalise screen's
  side of this card). If a new reusable preview pattern earns a name (e.g.
  a 4-box pipeline strip, a 3-column difficulty box), add a short entry to
  `meta/design/components.md` (SCOPE+, same as CARD-169 flagged its own
  `.guide-strip` entry).
- **Renders:** ~/Documents/nonogram-reviews/CARD-201/ (owner visual check
  before merge) — both new guide pages at Book 1 trim and at the narrowest
  supported trim (same corpus CARD-167 rendered against), plus the
  Finalise-screen preview screenshot, so the owner can judge whether the
  fallback form at the narrowest trim is still legible with twice the
  content.

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", revision read
  2026-10-08 (item 2). This is the explicitly deferred "full 1-2 page
  tutorial" both CARD-167 and FR-041's own 2026-10-04 amendment named and
  left for later — see "What to implement" above for the exact quotes.
- [Content source] `docs/guides/how_to_solve_nonograms_v2.pdf` (2 pages,
  currently untracked — `git status` confirms it is a new file at this
  exact path, not yet committed). Full content transcribed into "What to
  implement" above; re-read the PDF directly before implementing in case a
  later owner edit changes it before this card starts (drafted 2026-10-08).
- [Sibling card, no ordering dependency declared but a real one exists]
  CARD-200 (page numbers + table of contents, drafted the same day) needs
  final page positions for its table of contents, which only settle once
  THIS card's page-count shift (guide: 1 -> 2 pages,
  `interior_page_count`'s leading term) is in. CARD-200 is drafted with
  `Depends on: CARD-201` for this reason — confirm that is still set when
  both are scheduled.
- [Owner decision needed before merge, item 1 of 2] **Exact page-1 title
  wording.** The source PDF's own heading is "HOW TO SOLVE A NONOGRAM" (all
  caps, singular "a Nonogram"); the book's existing, already-shipped
  `GUIDE_TITLE` constant is "How to Solve Nonograms" (title case, plural).
  This card's own reading: keep the existing `GUIDE_TITLE` unchanged (it is
  already an owner-approved, shipped title from CARD-167; the source PDF's
  capitalisation is that document's own design, not a wording instruction)
  — flagged rather than silently assumed, since the two differ in a way a
  careless transcription could "fix" without being asked to.
- [Owner decision needed before merge, item 2 of 2] **Whether all ~7 new
  diagrams fit 2 pages at every already-supported trim, including the
  narrowest.** This drafting pass did not measure pixel budgets (that is
  implementation work) — CARD-167's own narrowest-trim case already needed
  its weakest fallback form (short labels, no captions) for ONE worked
  example; this card's page 2 alone adds three more technique diagrams plus
  a three-column text box, which is substantially more content for the same
  page budget. If the narrowest stored trim cannot hold even the
  labels-only form of everything within CON-020's floor, the implementer
  must say so explicitly (with measurements) and bring a concrete option
  back (e.g. drop a diagram from the smallest trim's fallback, widen the
  trim's own page-count tolerance, or confirm the owner is fine with that
  trim no longer supporting the full tutorial) rather than silently
  shrinking type below the floor or quietly omitting content.
- [Verified facts the implementer must not re-derive] See "What to
  implement" above for exact line numbers: `create_guide_page`
  (`book_pdf_generator.py:1556-1671`), `GUIDE_*`/`WORKED_EXAMPLE_*`
  constants (`:406-519`), `example_line_layout`/`draw_example_line`
  (`:1191-1244`), `interior_page_count`'s formula (`:1277-1353`, the
  leading `1`), `puzzle_pages`/`puzzle_section`'s `first_page=2` defaults
  (`:2155`, `:2267`), `section_plan`'s call site (`:2411-2437`),
  `interior_stream`'s `first_answer_page = 3 + len(section)` (`:2642`) and
  the single `create_guide_page(..., page_number=1)` call in `produce()`
  (`:2684-2690`). `app.py`'s Finalise context dict (`:4668-4673`) and
  `templates/book_finalize.html`'s guide card (`:46-79`, footnote right
  after it) are the CARD-169 preview-sync surface. `admin.css:326-338` is
  the existing preview styling to extend, not replace.
  `tests/test_book_interior_type_floor.py:169-170,301` is the face-
  classifier that must recognise whatever this card's new drawing
  helper(s) are named, or the 10 pt floor check silently stops covering
  the guide page's new content.
- [Not in this card] Formalising the requirements delta: amending FR-041 to
  drop its "the guide page stays exactly one page" clause and state the new
  2-page tutorial, and updating `meta/architecture/trace.yml` — architect-
  station follow-up, per the same pattern CARD-198 used for FR-042/INV-011.
  This card edits nothing under `meta/architecture/**`.
- [Estimate] 2d, above the brief's 1d sizing guideline (`config.yml
  sizing.max_estimate`). Split suggestion if it needs to divide: (a) the
  `example_line_layout`/`draw_example_line` generalisation + the new
  diagram-drawing routines + both pages' content, at every fallback form
  (~1d); (b) the page-count ripple (`interior_page_count`, `first_page`
  defaults, `first_answer_page`, the two-call `produce()` change) + the
  Finalise preview sync + the full existing-test migration
  (`test_book_guide_page.py`, `test_book_guide_page_type.py`,
  `test_book_interior_type_floor.py`, `test_book_pdf_memory.py`,
  `test_book_pdf_ink_mode.py`, `test_book_finalise_guide_preview.py`,
  `test_book_finalise_gutter.py`, the new baseline fixture) (~1d). Kept as
  one card per the brief's instruction (one coherent change — splitting the
  content from its page-count consequence would leave either half
  unshippable on its own).
- [Env] forge 2026.8.17 (no `meta/.skills.yml` → no `forge.min_version` to
  compare against; version still resolved and noted per protocol).
- [Pin gate] n/a — no `meta/.skills.yml` → `legacy.enabled` unset, gate
  skipped.
- [Drift gate] n/a — no `meta/drift-pending.yml`, gate skipped.