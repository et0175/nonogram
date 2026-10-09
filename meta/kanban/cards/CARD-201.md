# CARD-201: The guide page becomes a 2-page "How to Solve a Nonogram" tutorial, sourced from the owner's reference guide

**Status:** review
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

- [Implementation complete, autonomous background pass] Both pages
  implemented, all 8 ACs passing with fresh evidence (below), both owner-
  decision flags answered, SCOPE+ recorded, renders saved. No blocker.

- [Owner decision 1 of 2 — ANSWERED] **Title wording: kept `GUIDE_TITLE`
  unchanged** ("How to Solve Nonograms", title case, plural), per this
  card's own drafted recommendation. The source PDF's "HOW TO SOLVE A
  NONOGRAM" is that document's own all-caps design convention, not a
  wording instruction; the shipped title is already owner-approved
  (CARD-167) and nothing about this card's content requires changing it.
  Page 2's new title, `GUIDE2_TITLE = "When the Puzzle Gets Harder"`, is
  title-cased to match rather than shouting the source's own all-caps
  heading, for the same reason.

- [Owner decision 2 of 2 — ANSWERED, with measurement] **The narrowest
  stored trim (10 cm minimum width) does NOT fit the 2-page tutorial in the
  original 3-tier fallback (full / captions-only / labels-only) — measured,
  not assumed.** At 10 cm wide, even the labels-only form (every heading,
  every diagram, no captions) overflows the usable frame on both pages: a
  2-page tutorial carrying 3 new techniques on page 1 (the basic rule, 3
  cell-state icons, 3 "start with certainty" techniques) and 4 more on page
  2 (2 harder techniques, the assume/follow/breaks/proved pipeline, the
  worked-example recap, the difficulty box) is simply more content than the
  one worked example CARD-167's 3-tier fallback was built to shrink to.
  Chosen option (of the three the drafting pass asked for): **extended the
  fallback system from 3 tiers to 5**, via a new `bare_level: int` parameter
  (0/1/2) alongside the existing `(full, captions)` pair:
  - level 0 is the original labels-only form, unchanged;
  - level 1 drops a multi-row technique's reasoning rows, keeping only the
    row that states its conclusion (the squeeze's "certain" overlap, the
    region split's final ruled-out state, the arrangement comparison's
    agreement row), and drops page 2's pipeline diagram and the
    worked-example recap (both a restatement of material page 1 or an
    earlier worked example already taught in full);
  - level 2 additionally drops page 1's 3 purely-illustrative cell-state
    pictures (the heading alone still names "Unknown"/"Filled"/"Empty") and
    page 1's "mark spaces" diagram, and tightens inter-section gaps.
  All 5 levels are tried in order (full -> ... -> level 2), the first whose
  last mark clears the bottom margin is drawn — exactly `create_guide_page`
  did before, just with 2 more rungs on the ladder. **No level ever drops a
  line of type or a clue digit below CON-020's 10 pt floor** (G-4) — only
  which diagrams and which gaps are drawn change; this was verified by
  measurement (`TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim`,
  evidence below), not assumed. Measured: Book 1 (8.5 x 11 in) and 6 x 9 in
  both fit the original labels-only form (level 0) on both pages, unchanged
  from before; only the 10 cm minimum trim needs level 1 or 2 (which level
  depends on the book's chosen height — a 10 x 20 cm book needs level 1 on
  page 2, a 10 x 10 cm square needs level 2). This was the option that kept
  every stored trim shippable with the floor and all content intact, rather
  than widening a trim's own tolerance or dropping a technique outright —
  flagged here, with renders, for the owner to review the tightest case.

- [STRUCTURE] `create_guide_page`'s existing `page_number` parameter now
  also selects which half of the tutorial to draw (`page_one = page_number
  % 2 == 1`) rather than gaining a second parameter for it: the two always
  coincide (the guide is always interior pages 1 and 2, FR-043's own
  parity rule), so a second parameter could only ever agree with the first
  or be a bug — see the function's own docstring for the fuller reasoning.
- [STRUCTURE] Every new diagram is built through the **same two calls**
  CARD-167's worked example already used — `example_line_layout`/
  `draw_example_line` for every clue/length/fill/cross diagram (the basic
  rule, all 5 new techniques, the worked-example recap) — plus one new,
  narrower call for the 3 cell-state icons (`guide_icon_layout`, a bare 1x1
  cell with no clue and no frame) and two genuinely new drawing routines
  for the two shapes no existing helper could produce: `_draw_pipeline_diagram`
  (4 bordered boxes + arrows, no clue/grid at all) and `_draw_difficulty_box`
  (a bordered N-column text box). All three new routines are reached only
  through `compute_layout`/`_stroke_drawing`/`_write_clues` the same way the
  existing ones are (G-3, ADR-0036/R2) — no inline placement arithmetic.
- [STRUCTURE, production bug fixed] Every diagram image is now pasted at
  `frame.left - pad` (`pad` = the layout's own heavy-rule width), not
  `frame.left` unadjusted. `draw_example_line`'s own crop starts a heavy
  rule's width *before* its logical left edge (its own docstring: "minus a
  heavy rule of white"); the original single-diagram page never reached any
  stored trim's right edge so this went unnoticed, but a 10-cell line with
  a 3-digit clue at the 10 cm minimum trim now does, overflowing the usable
  area by about 13 px. Fixed by shifting the paste left by `pad`, so only
  the universal, by-design ~2-3 px heavy-rule bleed every framed drawing on
  this book has (`_stroke_drawing`'s own docstring) remains.
- [STRUCTURE] Content is hand-transcribed from
  `docs/guides/how_to_solve_nonograms_v2.pdf` into named module constants
  (`GUIDE_BASIC_RULE_*`, `GUIDE_CELL_STATES`, `GUIDE_TECHNIQUES_1`/`_2`,
  `GUIDE_ASSUME_*`, `GUIDE_DIFFICULTY_LABELS`), the same pattern every
  existing guide constant already uses — no code reads the PDF at runtime.
  The difficulty-label sentences are carried verbatim (this card's own
  "Target"); the basic-rule worked line uses a different clue/length
  (`3 2 1` on 8 cells) from the original worked example's `3 1` on 6 (G-1:
  that example is untouched, not reused for the new material).
- [SCOPE+, production] `src/nonogram/admin/book_pdf_generator.py:741-749` —
  one `GuideRow.note` capitalised `"compare"` -> `"Compare"`. An x-height-
  only word (no capital, no ascender) undercounts by nearly a quarter under
  this test suite's own cap-height-to-baseline floor measurement
  (CARD-149's convention) even though it is drawn at the correct 11 pt —
  the same class of defect CARD-167 fixed by rewording its own copy
  ("'way.' no longer wraps onto its own line"). Verified it is a
  measurement artefact, not a real floor violation, by measuring the same
  word at the same point size in isolation before changing it (see AC-4
  evidence below).
- [SCOPE+, test files outside the Touches list — all fixed, all passing]
  Inserting the guide's 2nd page shifts every later interior page's number
  by +1 and **flips its parity** (odd<->even) — an unavoidable,
  documented consequence of FR-043/ADR-0036's mirrored margins, not a bug.
  This broke page-number/parity assumptions in 14 test files outside the
  Touches list, each fixed and re-verified green:
  `tests/test_book_pdf.py`, `tests/test_book_pdf_band.py`,
  `tests/test_book_puzzle_frame.py`, `tests/test_book_pdf_levels.py`,
  `tests/test_book_pdf_two_up.py`, `tests/test_book_solved_answer_key.py`,
  `tests/test_book_level_order.py`, `tests/test_book_arrange_page_breaks.py`,
  `tests/test_book_export_interior_cover.py`, `tests/test_book_proof_pages.py`,
  `tests/property/test_book_export_interior.py`,
  `tests/property/test_book_order.py`, `tests/property/test_book_pairing.py`,
  `tests/property/test_book_pdf_geometry.py`. Two KDP-boundary corpora in
  `test_book_finalise_gutter.py` (already Touches-listed) needed their
  puzzle-count *composition* recomputed, not just a +1, to keep pinning the
  same exact 150-page external KDP gutter-band boundary.

- [AC-6 note] AC-6's own wording ("byte-identical ... shifted by one") is
  **not achievable as literal byte/digest identity**: a page inserted
  before the puzzle section flips every later page's parity, and
  FR-043/ADR-0036's mirrored margins (G-3, protected, untouched by this
  card) genuinely move a page's ink by a few hundred thousand pixels when
  that happens, even though its logical content is unchanged. Verified
  empirically before deciding how to test it (`_blank_page` at interior
  page 2 vs. page 3 for the same payload differ in ~416,000 of ~8.4M
  pixels). `TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`
  (`tests/test_book_pdf_memory.py`) instead re-invokes the unedited
  production page-drawing functions directly at each page's own new
  position and compares their *content* (ink bounding-box cropped, then a
  tolerant mean-diff + high-diff-pixel-fraction comparison, not
  `tests/helpers/pdf_pages.same_page`'s `.reduce(6)` downsampling, which
  measured too coarse for this — overlap 0.776 on genuinely identical
  content) — with a negative control proving the comparison has teeth.
  `tests/fixtures/book_baseline_card201.json` (new) is this card's AC-6
  evidence file, superseding `book_baseline_card198.json`; it records the
  current, correct 13-page truth, not a diff.

## CARD-201 — acceptance criteria evidence (fresh run, this pass)

- **AC-1** `TestGuidePage_IsTwoPages` (`tests/test_book_guide_page.py`) —
  `interior_page_count`'s guide term is 2 for every combination tried, and
  an exported interior opens with both guide titles on pages 1-2 and
  neither on page 3.
- **AC-2** `TestGuidePage_PageOneCarriesTheBasicTechniques` — the basic
  rule, all 3 cell-state icons and all 3 "start with certainty" techniques
  (including the squeeze's 3-row diagram) are drawn, each verified by
  re-rendering the exact expected content through the project's own
  painters and matching it against the page (see this file's own docstring
  for why decoding pixels directly does not generalise past the original
  worked example) — plus a cell-pitch check against a real puzzle page.
- **AC-3** `TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyBox`
  — the region split, the 3-arrangement comparison, the 4-box pipeline and
  the difficulty box (its 3 sentences matched verbatim — a wrong sentence
  provably does not match, AC-3's own negative control) all verified the
  same way.
- **AC-4** `TestGuidePage_BothPagesHoldTheTypeFloorAtEveryStoredTrim` — CON-
  020's 10 pt floor holds for every line of type on both pages, and for a
  1-, 2- and 3-digit clue sample, at Book 1, 6x9 and the 10 cm minimum
  trim.
- **AC-5** `TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity` — a
  3-easy/2-medium/1-hard book's page count is exactly the pre-card formula
  plus one, and every page's parity still equals its own 1-based position.
- **AC-6** `TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne`
  (`tests/test_book_pdf_memory.py`) — see the AC-6 note above.
- **AC-7** `TestFinaliseGuidePreview_ShowsBothPages`
  (`tests/test_book_finalise_guide_preview.py`) — both pages' content shown,
  read live from `book_pdf_generator` (a monkeypatched sentinel on a new
  constant renders), the difficulty sentences appear nowhere else in
  contradictory wording. Visually confirmed too: `~/Documents/nonogram-
  reviews/CARD-201/finalise-preview-page1.jpg` and
  `finalise-preview-pipeline-difficulty.jpg` (live Flask dev server,
  in-memory book, screenshotted).
- **AC-8** `TestGuideHelpers_GeneralisedSignatureReproducesTheOriginalWorkedExample`
  — the original 4-step worked example, called through the generalised
  `example_line_layout(spec, clue, length)` signature with the ORIGINAL
  `(3, 1)`/`6` arguments, is pixel-identical (`np.array_equal`, not a
  tolerant match) both to a fresh re-render of the same call and to where
  the shipped page 2 recap actually draws it.

Full suite run, this pass: all 7 Touches-listed test files green —
`test_book_guide_page.py` 41 passed, `test_book_guide_page_type.py` 11
passed, `test_book_interior_type_floor.py` 21 passed, `test_book_pdf_memory.py`
31 passed + 1 skipped (DB-mode test, skips silently without a `nonogram_test`
database per this project's own convention), `test_book_pdf_ink_mode.py` 39
passed, `test_book_finalise_guide_preview.py` 25 passed,
`test_book_finalise_gutter.py` 113 passed. The full project-wide suite
(`./.venv/bin/python -m pytest`) was run to confirm no other regression;
see this pass's own final message for its result.

Renders saved to `~/Documents/nonogram-reviews/CARD-201/`: both pages at
Book 1 (`guide-book1-page1.png`/`page2.png`, plus `-with-usable-frame`
variants showing the margin box), both pages at the 10 cm minimum trim
(`guide-min-10cm-page1.png`/`page2.png`, plus `-with-usable-frame`
variants — page 2 here is the fallback-level-1 form, the owner-decision-2
evidence), and the Finalise screen's live preview
(`finalise-preview-page1.jpg`, `finalise-preview-pipeline-difficulty.jpg`,
`finalise-guide-preview.html`).

- [Build gate] Orchestrator's own independent full-suite run (not the
  implementer's claim) — `./.venv/bin/python -m pytest` in the CARD-201
  worktree, under the `meta/kanban/.full-suite.lock`: **6725 passed, 9
  skipped, 0 failed, exit 0** (1009.69s). The 9 skips match this project's
  known platform/DB-mode skip set (no `nonogram_test` database,
  `RLIMIT_AS` memory-cap tests), unrelated to this card.
- [Review] forge:review cycle 1 started 2026-10-08T17:28Z (background
  agent `@code-review`).
- [Review 1/3] Returned 10 findings, most-severe first (this skill
  invocation ran standalone — via ad hoc Skill("review") rather than the
  full dispatcher procedure — so it reported findings without a numeric
  overall score; orchestrator's own severity read below, not the
  reviewer's own label, since the report didn't assign one):
  - **F-1 (Critical — content correctness)** `book_pdf_generator.py:729`,
    `GUIDE_TECHNIQUES_2`'s "Keep what every arrangement agrees on" worked
    example: shows only 3 of the 8 legal placements of clue `(3,)` on a
    blank 10-cell line (starts 0, 1, 5) and concludes cell 4 is "certainly
    empty in every arrangement" — false, since placements starting at 2, 3,
    4 all cover cell 4. **Independently re-verified by the orchestrator**:
    legal starts for a length-3 run on a 10-cell line are 0..7 (8 total);
    start `s` covers index 4 iff `s ∈ {2,3,4}` — all three exist among the
    8, so cell 4 is filled in at least 3 of 8 arrangements, not empty in
    all. Confirmed real, not a reviewer error. This is new content the
    implementer invented (the source PDF's own version of this diagram is
    an image, not machine-readable text, so no clue/placement numbers were
    available to transcribe verbatim) — ships a false logical deduction, in
    the implementer's own words, as the book's signature technique for
    exactly the AC-3 content this card was built to add. Gating.
  - **F-2 (Important/Critical — crash risk)** `book_pdf_generator.py:1233`,
    `_draw_pipeline_diagram`/`_draw_difficulty_box` read `.size` directly
    off a `_guide_face()` font; that function's own docstring says the
    returned face is "unsized" (no `.size` attribute) whenever Arial isn't
    found (hardcoded to a macOS-only path — always true on a non-macOS
    host) AND Pillow is below 10.1 — a combination `pyproject.toml`'s
    unbounded `Pillow>=10.0` floor still permits. This project's admin
    panel is deployed on a real non-Mac service (see memory: Render-hosted,
    Postgres-backed production instance, distinct from local dev) — not a
    hypothetical platform. If that deployment's Pillow happens to be
    10.0.x, every book export crashes on this new code path with
    `AttributeError`. Gating — needs either a version floor bump
    (`Pillow>=10.1`, an ADR-0006-adjacent decision) or (preferred, smaller)
    making the two new drawing routines degrade the same way
    `test_book_interior_type_floor.py`'s existing guard already expects
    elsewhere in this file.
  - **F-3 (Important — visible rendering defect)**
    `book_pdf_generator.py:1246`, `_draw_pipeline_diagram` draws the last
    pipeline box's right border at `x + box_w`, exactly the canvas's pixel
    width (one past the last valid pixel) — Pillow clips it, so the
    "PROVED" box ships with no right border on every exported book's guide
    page 2 (confirmed by the reviewer's own direct Pillow rendering test).
    The same off-by-one also places every non-final box's right border 1px
    into the arrow gutter. Gating — a shipped visual defect on every book.
  - **F-4 (Important — test-coverage blind spot)**
    `tests/test_book_guide_page.py:267`, AC-4's CON-020 floor sweep
    classifies a whole ink band as a non-text diagram whenever any row has
    a long horizontal run; the new bordered boxes
    (`_draw_pipeline_diagram`/`_draw_difficulty_box`) draw a border
    touching every row, merging their own label/prose text into that
    "ruled" classification — so a future regression shrinking either box's
    label text below CON-020's 10pt floor would NOT be caught by
    `test_every_line_of_type_holds_10pt_on_both_pages`, despite that being
    the test's one stated job. Gating (CON-020 is a mandatory system-
    contract rule; this quietly narrows its only automated check).
  - **F-5..F-10 (Minor/moderate, not gating this cycle, fix opportunistically
    if cheap):** a previously-dead `_stroke_drawing` branch
    (`frame is None`) is now live via `guide_icon_layout`, contradicting its
    own "callers can't take this branch" docstring (:1121); stale
    singular-"page 1 is the guide page" comments in `app.py:806` and
    `book_pdf_generator.py` not updated for `GUIDE_PAGE_COUNT=2`; the
    fallback ladder stacks two independent trimming mechanisms
    (full/captions booleans + bare_level 0/1/2) rather than one
    data-driven scheme (:2198); `bare_level`'s `[-1:]` truncation is
    positional, not content-marked, so it only coincidentally picks "the
    conclusion row" for today's 5 techniques (:2262); `book_finalize.html`
    duplicates the guide_techniques_1/2 Jinja block byte-for-byte except
    one attribute name (:76,:99); `_draw_difficulty_box` is rebuilt from
    scratch on every fallback attempt (up to 5x) instead of cached like
    every sibling image (:2323).
  - One candidate investigated and explicitly excluded by the reviewer
    (judged a reasoned, justified tradeoff, not a defect):
    `test_book_pdf_ink_mode.py`'s retirement of
    `TestBookInk_ColourInteriorIsUnchanged`'s positional-fixture checks —
    the guide's page-count bump breaks every downstream page's
    position/parity, making the old fixture-based check a guaranteed false
    positive; the replacement's docstring justifies this and a live
    cross-check test still covers the AC's core intent.
  - **Verdict: cycle 1 does not meet the bar** (4 gating findings: 1
    content-correctness, 1 crash-risk, 1 visible-defect, 1 test-blind-spot)
    — routing to forge:fix for F-1..F-4, cycle 2.

- [Fix 1] Review cycle 1's 4 gating findings (F-1..F-4), all fixed in this
  worktree. The full review write-up with line numbers lives in this card's
  copy on `main` (this worktree's own copy predates review cycle 1, so it is
  not duplicated here) — this entry records the fixes and their fresh test
  evidence, not the findings themselves.

  - **F-1 (content correctness) — FIXED.** `GUIDE_TECHNIQUES_2`'s "Keep what
    every arrangement agrees on" worked example (`book_pdf_generator.py`
    ~line 728) used clue=(3,), length=10, showing only 3 of its 8 legal
    placements (starts 0, 1, 5) and claiming cell 4 was "certainly empty in
    every arrangement" — false: starts 2, 3 and 4 (none of them shown) all
    cover cell 4. In fact a clue (3,) on a 10-cell line has NO invariant cell
    at all (every index 0-9 is reachable by some start; no index is covered
    by all 8). Fixed by changing the line to clue=(3,), length=5, where a
    run of 3 has exactly `length - clue + 1 = 3` legal placements — the
    three rows shown are now literally ALL of them, not a chosen subset —
    and cell 2 is the one index covered by every one of the 3. The full
    verification against every legal placement is written into a code
    comment directly on the constant (not just this note), so a future edit
    can't silently reintroduce the same class of error. Test evidence:
    `tests/test_book_guide_page.py::TestGuidePage_PageTwoCarriesTheHarderTechniquesAndDifficultyBox::test_the_arrangement_comparison_shows_three_placements_then_what_they_agree_on`
    (updated to the corrected content) and the new
    `::test_the_arrangement_comparison_is_verified_against_every_legal_placement`
    (an independent brute-force cross-check that recomputes every placement
    from scratch rather than reading the constant under test) — both pass.

  - **F-2 (crash risk) — FIXED.** `_draw_pipeline_diagram`/`_draw_difficulty_box`
    (`book_pdf_generator.py` ~1253/1299) read `.size` directly off a
    `_guide_face()` font, which can be an "unsized" face with no `.size`
    attribute at all on a non-macOS host with Pillow < 10.1 — a combination
    `pyproject.toml`'s unbounded `Pillow>=10.0` floor still permits. Fixed by
    passing the font's own requested pixel size explicitly as a new
    parameter (`label_size`/`text_size`) instead of reading it back off the
    font object — the same approach every other `_guide_face` caller in this
    file already uses (`create_guide_page`'s title/body fonts measure with
    `getlength`/`getmetrics`; `create_divider_page`'s with `draw.textbbox`;
    neither ever reads `.size`). Both call sites and both pre-existing tests
    that called these functions directly were updated to pass the size.
    Test evidence: new
    `...::test_the_new_drawing_routines_tolerate_a_sizeless_fallback_face` —
    drives both routines with a stand-in face that genuinely lacks `.size`
    (a `__getattr__` double delegating every other method to a real font),
    with a negative-control assertion proving the double has teeth
    (`sizeless.size` itself raises `AttributeError`), and confirms neither
    routine crashes. Passes.

  - **F-3 (visible rendering defect) — FIXED.** `_draw_pipeline_diagram`
    drew each box's right border at `x + box_w`, one pixel past the box's
    own right edge — for the last box, exactly the canvas's pixel width, so
    Pillow clipped it and "PROVED" shipped with no visible right border;
    every earlier box's border landed 1px into the arrow gutter instead of
    on the box. Fixed to `x + box_w - 1`. Test evidence: new
    `...::test_the_last_pipeline_box_has_a_complete_unclipped_border` —
    renders the diagram directly (not through the full page), locates every
    box's border columns structurally (full-image-height ink runs) rather
    than assuming coordinates, and pixel-checks all 4 boxes for a complete,
    un-clipped 4-sided rectangle — confirming the last box's right border
    now lands on the canvas's own last column and that no border overlaps an
    arrow. Passes.

  - **F-4 (test-coverage blind spot) — FIXED.** `tests/test_book_guide_page.py`'s
    `type_bands`/`is_ruled` helper (the AC-4 CON-020 10pt-floor sweep)
    classified an ENTIRE bordered box — border, labels and sentences alike —
    as "ruled"/diagram whenever any one row had a long horizontal run,
    because a box's border touches every row of its own bounding area; this
    silently excluded the box's own label/prose text from the floor check.
    Fixed `type_bands` to look *inside* an otherwise-ruled band for a
    genuinely bordered box's own structure: it finds the box's full-height
    border columns (ink on literally every row of the band — something no
    line of text, however dense, produces), groups them into left/right
    pairs per box, and only rows that are *solidly* inked between one box's
    own pair (the true top/bottom border rows) stay excluded; every other
    row — including a genuinely blank row between two lines of the box's own
    text, which still separates them into their own bands — is checked like
    text anywhere else. (First attempt used a per-row run-length threshold
    instead of this structural check and produced false splits/nonsense
    measurements on real label text, e.g. "FOLLOW"/"PROVED" — caught by
    running the real AC-4 test before trusting the fix, then corrected to
    the structural approach above.) Negative-control test evidence (per the
    brief's own requirement): new
    `...::test_a_regression_shrinking_a_boxs_label_text_is_still_caught_by_the_floor_check`
    — builds the difficulty box directly with a deliberately shrunk (6pt)
    label font (never shipped in production — `GUIDE_DIFFICULTY_LABELS`/
    `GUIDE_BODY_PT` are untouched) and confirms the fixed classifier now (a)
    still finds type inside the box at all and (b) correctly measures it
    below the floor — proving the old blind spot is closed, not just
    plausible. Passes, together with the real AC-4 floor test across all 3
    stored trims
    (`test_every_line_of_type_holds_10pt_on_both_pages[book1|6x9|10cm-wide]`),
    confirming the fix introduces no false positives on real, correctly-sized
    content.

  - **Fixture regenerated.** `tests/fixtures/book_baseline_card201.json`:
    F-1's corrected worked example and F-3's border fix both change guide
    page 2's own ink, so its digest and `interior_bytes`/
    `colour_interior_bytes` moved. Diffed before writing: every other page's
    digest, `page_count` (13) and `font_fingerprint` are unchanged. A new
    `re_recorded_for_review_cycle_1_fix` field documents this re-recording —
    the one case the fixture's own "never regenerate to make a test fail
    less" warning allows: real news about a deliberate, reviewed content
    change, not noise silenced away.

  - **Opportunistic items.** Fixed: the stale singular "page 1 is the guide
    page" docstrings in `app.py`'s `_printed_places` (~line 806) and
    `book_pdf_generator.py`'s `export_book` (~line 2476) now say "pages
    1-2". Fixed: `_stroke_drawing`'s docstring updated and its now-inaccurate
    `# pragma: no cover` removed from the `frame is None` branch —
    `guide_icon_layout` (this card) genuinely exercises that branch via
    `draw_example_line` (a bare cell icon has no frame), so it is live code,
    not dead. Not touched, as instructed: the fallback ladder's two
    trimming mechanisms, `bare_level`'s positional truncation,
    `book_finalize.html`'s duplicated Jinja block, `_draw_difficulty_box`
    being rebuilt on every fallback attempt.

  - **Test evidence, this pass.** `tests/test_book_guide_page.py` alone: 45
    passed. The full touched-file subset —
    `tests/test_book_guide_page.py tests/test_book_guide_page_type.py
    tests/test_book_interior_type_floor.py tests/test_book_pdf_memory.py
    tests/test_book_pdf_ink_mode.py tests/test_book_finalise_guide_preview.py
    tests/test_book_finalise_gutter.py` — exit code 0, no failures (the
    tail-captured summary line was truncated by this environment's own known
    quirk, documented in this project's CLAUDE.md; the process exit code is
    unambiguous). **The full project suite's own confirmation is the
    orchestrator's responsibility, not this pass's**: an in-worktree full-
    suite run was started during this pass but killed before completion at
    the orchestrator's instruction, to avoid two full suites competing for
    CPU while the orchestrator runs its own independent gate from its side —
    that is this project's standing practice (the orchestrator always
    re-confirms with a fresh run rather than trusting the implementer's
    in-flight one). See the orchestrator's own record for that result.

  - **No blocker.** None of F-1..F-4 turned out to be wrong, and none
    required an owner-level judgment call beyond what the brief already
    anticipated — F-1 used the brief's option (a)/(b) hybrid: same clue,
    shrunk line so the shown placements are genuinely exhaustive, rather
    than inventing an unrelated illustration.
- [Build gate] PASSED (attempt 2, after F-1..F-4 fixes). Orchestrator's
  own independent full-suite run — `./.venv/bin/python -m pytest` in the
  CARD-201 worktree, under the `meta/kanban/.full-suite.lock`: **6729
  passed, 9 skipped, 0 failed, 0 errors, exit 0** (1292.97s). Gate clear —
  proceeding to forge:review cycle 2 (confirmation cycle).
- [Review] forge:review cycle 2 started (background agent `@code-review`,
  confirmation pass over F-1..F-4's fixes plus the whole diff).
- [Review 2/3] F-1..F-4 (cycle 1) all re-verified independently and
  confirmed correctly fixed (two separate finder angles re-derived each
  one from source with no discrepancies). One NEW finding surfaced,
  gating:
  - **F-11 (Important — visible misalignment, zero test coverage)**
    `book_pdf_generator.py:2439`, the guide page's image-paste loop
    subtracts `pad = icon_layout.thick_rule` from every pasted mark's
    x-offset uniformly — but that correction only belongs to images built
    via `draw_example_line`/`example_line_layout` (which bake in a left
    bleed-margin of exactly that width, the fix for cycle 1's F-3).
    `_draw_pipeline_diagram` and `_draw_difficulty_box` draw their own
    border flush at column 0 with no such margin, so page 2's pipeline
    diagram and difficulty box ship shifted left by one heavy-rule width
    relative to every other mark on the page — confirmed by reading the
    source directly (`:2439-2444` vs. `:1242-1316`/`:1324-1370`),
    independently found by two finder angles. On Book 1 this lands in the
    inner gutter margin on a right-hand page; on the 10cm minimum trim it
    eats further into an already-tight margin budget. **Zero test
    coverage**: `TestGuidePage_TextFitsTheUsableFrame`'s margin-fit tests
    (`tests/test_book_guide_page_type.py:500`) never pass `page_number=2`
    to `create_guide_page` (default is 1), so page 2 — the only page with
    these two diagrams — is never checked against `frame.left`/
    `frame.right` at any trim; the FFT-based diagram-presence tests are
    deliberately x-position-agnostic, so nothing in the suite catches
    this. Gating — both the misalignment and its own missing coverage.
  - **F-12..F-19 (Minor/moderate, not gating):** `create_guide_page`
    unconditionally builds all diagram images for both pages on every
    call, discarding half (:2223); technique diagrams and the difficulty
    box are rebuilt from scratch on every one of up to 5 fallback-level
    retries (:2376); the 5-tier `bare_level` ladder is scattered
    conditionals, not a general priority-shedding mechanism (:2251); F-2's
    fix (explicit size param) is a docstring convention, not a structural
    guard — nothing stops a future caller reading `.size` directly again
    (:1259); new `GuideRow` duplicates `ExampleStep`'s shape, wrapped into
    throwaway `ExampleStep`s at every call site (:613); the X-cross icon
    idiom is duplicated across `_draw_pipeline_diagram`,
    `draw_example_line`, and twice in `admin.css` (:1301); duplicated
    Jinja technique-list block in `book_finalize.html` (:76, same finding
    as cycle 1's F-9, still not required); `_guide_rule_width` recomputes
    a probe-clue layout `page_frame` already computed, called 3x per guide
    render (:1230).
  - **Verdict: cycle 2 does not meet the bar** (1 new gating finding) —
    routing to forge:fix for F-11, cycle 3 (the max allowed — if cycle 3
    finds a NEW gating issue, this escalates per protocol rather than
    looping further).

- [Fix 2] Review cycle 2's one new gating finding (F-11), fixed in this
  worktree (review cycle 3, the last allowed). This entry records the
  finding, the fix, the new test coverage and fresh evidence.

  - **F-11 (Important — visible misalignment, zero test coverage) — FIXED.**
    `book_pdf_generator.py`'s guide-page paste loop (`:2439` at review time,
    now in `create_guide_page`'s `set_page`/paste-loop closures) subtracted
    `pad = icon_layout.thick_rule` from **every** pasted image's x-offset
    uniformly. That correction belongs only to an image built via
    `draw_example_line`/`example_line_layout`, which bakes in a left
    bleed-margin of exactly that width (cycle 1's own F-3 fix was
    compensating for it) — `_draw_pipeline_diagram` and `_draw_difficulty_box`
    draw their own border flush at column 0, with no such margin, so
    applying the same correction shifted both one heavy-rule-width too far
    left: into the inner gutter margin on Book 1's right-hand page, and
    further into the already-tight 10 cm minimum trim's margin.

    **Mechanism chosen:** each mark the page builds now carries its own
    `needs_pad: bool` flag alongside its `(y, image_or_text)` pair — `marks`
    is a list of `(y, mark, needs_pad)` triples instead of `(y, mark)`
    pairs. `picture(img, gap, *, needs_pad: bool = True)` defaults to
    `True` (every existing call site — the basic rule, the cell-state
    icons, every technique's line diagrams, the worked-example recap — is
    a `draw_example_line` image and keeps the correction unchanged); the
    two call sites that build the pipeline diagram and the difficulty box
    now pass `needs_pad=False` explicitly. The paste loop reads the flag
    per mark: `x = frame.left - pad if needs_pad else frame.left`. This
    was the option that fit the existing shape best — the loop already
    iterated one list of marks uniformly, so tagging each mark was less
    invasive than giving the two new drawing functions a different return
    convention or threading a second list through `set_page`.

    **New test coverage** (`tests/test_book_guide_page_type.py`,
    `TestGuidePage_TextFitsTheUsableFrame`, the exact class/location F-11's
    own finding named): the class's 3 existing margin-fit tests
    (`test_every_mark_sits_inside_the_usable_area`,
    `test_it_fits_the_smallest_trim_a_book_may_be_stored_at`,
    `test_the_whole_corpus_of_trims_and_counts_fits`) all defaulted to
    `page_number=1` and so never rendered page 2 at all — the only page
    carrying these two diagrams. The first two are now extended to loop
    over `page_number in (1, 2)`, re-reading `page_frame` per page number
    (page 2's frame is genuinely different from page 1's: FR-043/ADR-0036
    mirror margins by parity). The whole-corpus test is deliberately **not**
    extended to page 2: doing so surfaces a real but separate, pre-existing
    gap — at some points of that test's full continuous
    `MIN_TRIM_CM..MAX_TRIM_WIDTH_CM x MAX_TRIM_HEIGHT_CM` corpus, page 2
    overflows its frame by ~150 px even on the pre-F-11 code (confirmed by
    reverting this fix and re-running) — which is the fallback ladder's own
    coverage gap (it was only ever measured against 3 named stored trims:
    Book 1, 6x9, 10 cm minimum — see "Owner decision 2" above), not the
    F-11 misalignment this pass fixes. Flagged below rather than silently
    widened past or silently absorbed into this fix.

    Three new tests were added, all in the same class: the class gained a
    `diagram_bands` helper (page's `ink_bands` minus `type_bands` —
    independently reimplemented from `tests/test_book_guide_page.py`'s own
    `drawn_bands`/`type_bands` pair, per CLAUDE.md's "prefer an independent
    second implementation") and a module-level `band_ink_extent` helper
    (the leftmost/rightmost inked column inside a band's own rows — a
    bordered diagram's border is always the widest ink in its band, so this
    is its own left/right edge).
    - `test_page_two_pipeline_and_difficulty_box_align_at_book1`: Book 1's
      full fallback form draws all 12 of page 2's diagrams (pinned by a
      `len(bands) == 12` guard, the same assumption
      `tests/test_book_guide_page.py`'s own AC-3 `drawn` fixture already
      makes); the pipeline (index 6) and the difficulty box (index 7) must
      each start exactly at `frame.left` and never cross `frame.right`.
    - `test_page_two_difficulty_box_aligns_at_narrower_trims` (parametrized
      `6x9`/`10cm-wide`): both trims fall back far enough (measured) that
      the pipeline and the worked-example recap are dropped, leaving
      exactly 3 diagram bands (2 single-row techniques + the difficulty
      box, pinned by a `len(bands) == 3` guard); the difficulty box (always
      drawn, at every fallback level) is the last band, and must start at
      `frame.left` and end at exactly `frame.right - 1` (its own canvas is
      built exactly `measure` px wide).
    - `test_a_diagram_shifted_left_by_pad_is_not_at_frame_left` (negative
      control): crops the real, correctly-placed difficulty box out of a
      freshly rendered page, re-pastes that same crop `pad` pixels further
      left (reproducing the OLD, uniform paste), and asserts
      `band_ink_extent` reports a left edge that is NOT `frame.left` —
      proving the measurement the tests above rely on actually has teeth.

    **Proof the new tests would have caught the original bug.** Reverted
    `book_pdf_generator.py` to the pre-fix version in this same worktree
    (`git stash` on just that file) and re-ran
    `tests/test_book_guide_page_type.py`: all 4 new/F-11-targeted tests
    failed, each reporting the exact `pad`-sized left offset (e.g. "the
    difficulty box starts at x=107, not frame.left=113"; `pad` is 6 px at
    every stored trim this module measures). Restored the fix (`git stash
    pop`) and re-ran: all 15 tests in the file pass. This is the same
    revert-then-restore discipline review cycle 1's own negative controls
    used, done directly against the real production code path rather than
    only against a synthetic double.

    **Fixture re-recorded.** `tests/fixtures/book_baseline_card201.json`:
    the fix moves the pipeline diagram and the difficulty box right by
    `pad` on guide page 2, which moves that page's ink. Only interior page
    2's digest, `interior_bytes` (3,484,099 -> 3,483,012) and
    `colour_interior_bytes` (3,986,224 -> 3,985,305) changed; every other
    page's digest, `page_count` (13) and `font_fingerprint` are unchanged
    (diffed before writing, same discipline as cycle 1's re-recording). A
    new `re_recorded_for_review_cycle_2_fix` field documents this, naming
    F-11 and the mechanism, alongside the existing
    `re_recorded_for_review_cycle_1_fix` field (left untouched).

    **Test evidence, this pass (implementer's own):**
    `tests/test_book_guide_page.py tests/test_book_guide_page_type.py
    tests/test_book_interior_type_floor.py tests/test_book_pdf_memory.py
    tests/test_book_pdf_ink_mode.py tests/test_book_finalise_guide_preview.py
    tests/test_book_finalise_gutter.py` together: **289 passed, 1 skipped,
    0 failed** (the one skip is the known DB-mode test). The fix agent also
    ran the full project suite to completion itself this time and waited
    for it: **6733 passed, 9 skipped, 0 failed, 0 errors** (1286.65s) —
    exactly 4 more passing tests than the prior confirmed build-gate run
    (6729), matching the 4 new/extended test items added, same 9 skips.

  - **No blocker.** F-11 was confirmed correct by reading the source
    directly (the paste loop really did apply one `pad` correction
    uniformly to every mark) and reproduced by measurement before fixing
    it; the fix needed no owner-level judgment call — it is a
    straightforward "the correction belongs to some images, not all of
    them" bug, and the chosen mechanism (a per-mark flag) follows the
    existing code's own shape rather than introducing a new pattern.

- [Build gate] PASSED (attempt 2, after F-11's fix). Orchestrator's own
  independent full-suite run — `./.venv/bin/python -m pytest` in the
  CARD-201 worktree, under the `meta/kanban/.full-suite.lock`: **6733
  passed, 9 skipped, 0 failed, 0 errors, exit 0** (1197.78s) — exactly the
  implementer's own self-reported count, no discrepancy. Gate clear —
  proceeding to forge:review cycle 3 (the final allowed cycle).
- [Review] forge:review cycle 3 started (background agent `@code-review`,
  final allowed cycle — confirmation pass over F-11's fix plus the whole
  diff).
- [Review 3/3] F-11 held, but 10 findings surfaced re-scanning the whole
  diff — this is the card's LAST allowed cycle (`config.yml
  review.max_cycles: 3`), so new gating findings here are an escalation
  point, not an automatic cycle 4. Orchestrator's own severity read:
  - **F-20 (Important — reproduced visual overflow, zero coverage)**
    `book_pdf_generator.py:1269`, `_draw_pipeline_diagram`'s canvas width
    is derived only from label-text widths and fixed constants, never
    checked against the page's usable `measure`; the fallback loop
    (`:2431-2440`) only checks VERTICAL fit, never horizontal. Reproduced
    on a valid KDP trim, 10cm wide x 25cm tall (`MIN_TRIM_CM`, 25.0): ink
    reaches column 1180 on a 1181px canvas with `frame.right=1031` —
    149px past the usable frame, one pixel short of the physical page
    edge. This trim passes the loop's only (vertical) check at
    `bare_level 0`, so the oversized diagram is never dropped or
    shrunk — no test catches it (existing tests only probe 3 named
    stored trims, none this narrow-and-this-tall together). Gating.
  - **F-21 (Important — orphaned heading, contradicts own docstring, on
    a real stored trim)** `book_pdf_generator.py:2348`, at `bare_level
    >= 2` the cell-state block's `pass` branch drops BOTH the picture
    AND `paragraph(cell_state.heading)` — contradicting
    `create_guide_page`'s own docstring promise that "the heading alone
    still names Unknown/Filled/Empty" at this level. The sibling
    technique one entry later gets this right (keeps the heading
    paragraph unconditional, only gates the diagram via
    `draw_diagram=not(...)`); the cell-state block is the one place an
    all-or-nothing `pass` was used instead. **This fires on the 10cm
    minimum trim** — the card's own Fix-1 notes already say this trim
    needs exactly bare_level 1 or 2 — so the printed book ships an
    orphaned "Use three cell states" heading immediately followed by the
    next section's heading, on a real, already-tested stored trim.
    Gating.
  - **F-22 (Important — new, real, visible bug, preview-only)**
    `admin.css:369`, `.guide-pipeline-step + .guide-pipeline-step::before`
    attaches the arrow pseudo-element INSIDE the (column-flex) box itself,
    not as a connector between boxes, so the Finalise screen's live HTML
    preview shows a stray arrow glyph stacked above each later box's own
    label instead of sitting between boxes. The exported PDF is
    unaffected (`_draw_pipeline_diagram` draws its own arrows directly) —
    preview-only, but new, real, and visible. Gating (cheap CSS fix).
  - **F-23 (Moderate, not gating but worth a decision):** `tests/test_book_pdf_ink_mode.py`'s
    `TestBookInk_ColourInteriorIsUnchanged` had its byte-for-byte
    comparison against independently-recorded historical baselines
    (`book_baseline_card146/167/184.json`) replaced with a same-run
    consistency check only (colour vs. this run's own black-and-white),
    with no new historical baseline recorded for the 2-page guide. The
    retirement is justified (the guide's extra page invalidates every old
    page position) but leaves the colour path's independent-of-today's-
    code verification weaker than before. Not gating (no shipped defect),
    but flagged for a decision: record a fresh historical baseline now, or
    accept the narrower same-run check going forward.
  - **F-24 (already disclosed, re-surfaced, not new):** the full-corpus
    page-2 fit-coverage gap Fix cycle 2 already flagged explicitly ("fails
    at some untested points... even on the pre-F-11 code") — F-20 above is
    very likely a concrete instance of exactly this already-accepted risk,
    not a new, separate finding.
  - **F-25..F-29 (Minor, not gating):** `needs_pad: bool` is a narrow,
    one-bit mechanism that will need a third ad-hoc flag for a future
    diagram with a different bleed convention (`:2300`); several diagram
    images are built unconditionally for both page branches and half are
    always discarded (`:2223`); `technique_rows` is rebuilt from scratch
    on every one of up to 5 fallback attempts instead of cached like its
    siblings (`:2217`); the pipeline diagram's filled/crossed icon
    reimplements `draw_example_line`'s same two ink primitives instead of
    sharing them, acknowledged in its own docstring (`:1297`);
    `GUIDE_PAGE_COUNT` is presented as a general formula term but
    `page_one = page_number % 2 == 1` silently breaks (re-renders page 1
    twice) if it's ever bumped past 2, with no assertion guarding the
    assumption (`:2176`).
  - **Verdict: cycle 3 does NOT meet the bar** (3 new gating findings:
    F-20/F-21 real shipped visual defects on valid/already-tested trims,
    F-22 a new preview-only bug) — but this is the card's LAST allowed
    review cycle. Per the dispatcher's own escalation protocol, this is
    an ESCALATION POINT, not an automatic cycle 4: routed to the owner
    for a decision rather than silently exceeding `max_cycles: 3`.
  - **Owner decision, 2026-10-09:** fix all 3 (F-20/F-21/F-22), then one
    more confirmation pass — the review budget is extended by one cycle
    for this card specifically, since every prior cycle converged on
    fewer/smaller issues, not more, and all 3 findings are narrow and
    well-diagnosed rather than architectural.