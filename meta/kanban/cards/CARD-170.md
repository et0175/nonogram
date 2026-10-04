# CARD-170: Prove from the PDF's pixels that a puzzle's band prints once ("Puzzle 5 · Hard" drawn twice?)

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/170-band-prints-once
**Worktree:** —
**Source:** roadmap wave 1, 2026-10-04 (wave-32 goal-check observation; IDEA-090, WSJF 16)
**Idea:** IDEA-090
**Wave:** 33
**Depends on:** —
**Touches:** tests/test_book_pdf_band.py, src/nonogram/admin/book_pdf_generator.py, tests/helpers/book_corpus.py, tests/fixtures/book_baseline_card170.json (new)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The wave-32 goal-check hooked text drawing during a book export. It saw the
band "Puzzle 5 · Hard" drawn twice. Nobody checked whether the printed PDF
shows it twice. This card settles that with evidence first. It fixes only if
the duplicate is real.

**What the code does today (read, not yet proven by a test).**

- "Puzzle 5 · Hard" is a **puzzle-page band**, not an answer-key band. Answer
  tiles are captioned "Puzzle N — Title" with an em dash
  (`book_pdf_generator.py:BookPDFGenerator._answer_page`, lines 1936-1968, via
  `book_answer_key.answer_caption`). Answer pages carry no band. The idea's
  wording ("answer-key band", "fitting loop") does not match the code.
- A puzzle that prints **alone** goes through `BookPDFGenerator._blank_page`
  (lines 1827-1842). It calls COMP-007's `export/pdf.py:render_pages`, which
  draws **two** pages from one payload, the blank page and the solved page.
  It sets the header on both (`export/pdf.py` lines 465-467:
  `for page in (blank, answer): _draw_header(...)`). `_blank_page` keeps the
  blank page and drops the solved one (`blank, _ = render_pages(...)`).
- So the second draw most likely lands on the **dropped solved page**, a
  scratch bitmap that never reaches `_write_page`. That explains "twice"
  without any printed duplicate. It also explains "highest tier": in a
  5-puzzle book with Easy and Medium pairs, the single Hard puzzle is the only
  one printed alone. Paired puzzles go through `_two_up_page`
  (lines 1970-2011), which calls `_set_band` once per slot. `_set_band`
  (lines 773-820) only measures with `font.getlength`; it calls `draw.text`
  once. `_draw_header` in `export/pdf.py` also measures with `getlength` and
  calls `draw.text` once per part. So "measuring before drawing" is not the
  cause: measuring draws nothing.
- The module docstring already records the dropped solved page as a known,
  constant memory cost (`book_pdf_generator.py` lines 213-224).

**Steps.**

1. **Establish the fact from the exported PDF.** Build a small book whose
   last puzzle is the only Hard one and prints alone (for example 2 Easy,
   2 Medium, 1 Hard, sized so the Easy and Medium pairs pair). Export the
   interior through the generator's normal path. Read the bytes back with
   `tests/helpers/pdf_pages.py:pdf_pages`. Assert from pixels:
   - exactly one page of the whole PDF carries the "Puzzle 5 · Hard" band;
   - on that page the band strip holds one copy of the line: its ink extent
     matches the width of one line set at the band's size (with a JPEG
     tolerance), so a second, offset copy fails;
   - no divider or answer page carries that band's ink.
   Also cover a two-up page: each slot's band appears once.
2. **Name where the second draw lands.** Record `ImageDraw.text` calls during
   the export (monkeypatch). Assert that every draw of the band text that
   lands on a page reaching `_write_page` happens once per written page. Do
   not assert "exactly two draws": that would pin the wasted solved-page
   render.
3. **Render for the owner.** Write the Hard puzzle's page, a two-up page and
   one answer page as PNGs (decoded from the exported PDF, not re-rendered)
   to `~/Documents/nonogram-reviews/CARD-170/`. Never write them beside the
   repo.
4. **Decide.** If steps 1-2 pass, record "not a defect" in Worktree notes with
   the evidence: the test names and the recorder's result. Change no
   production code. If they fail, fix the generator so the band prints once,
   and rebaseline under the book pixel-baseline rule (see Touches).

## Acceptance criteria

- **AC-1:** Given a book whose only Hard puzzle prints alone as Puzzle 5, when its interior PDF is exported and its pages are decoded, then exactly one page carries the "Puzzle 5 · Hard" band, and its band strip holds one copy of the line, not two.
  *test: TestBookPdf_BandPrintsOnceInTheExportedPdf (in tests/test_book_pdf_band.py) — fails if `_set_band` or `_draw_header` draws a second offset copy, or if any other page gets the band*
- **AC-2:** Given a two-up page in the same export, when its pages are decoded, then each slot's band ("Puzzle 1 · Easy", "Puzzle 2 · Easy") appears exactly once on that page and on no other page.
  *test: TestBookPdf_BandPrintsOnceInTheExportedPdf (in tests/test_book_pdf_band.py)*
- **AC-3:** Given the same export with `ImageDraw.text` recorded, when the band text's draws are matched to the images written to the PDF, then each written page received the band exactly once, and any other draw landed on an image that was never written.
  *test: TestBookPdf_ExtraBandDrawNeverReachesAWrittenPage (in tests/test_book_pdf_band.py)*
- **AC-4:** Given the export above, when the owner opens `~/Documents/nonogram-reviews/CARD-170/`, then it holds the Hard puzzle's page, a two-up page and an answer page decoded from the exported PDF, and the Worktree notes record the verdict (defect or not) with its evidence.
  *test: review-lens (renders exist; verdict recorded)*
- **AC-5:** Mutation check: a second offset `draw.text` added in `_set_band`, and an answer caption that reuses `band_identity`, each make AC-1/AC-2 fail.
  *test: review-lens (mutants run and reverted, recorded in Worktree notes)*

## Guardrails

- G-1: If no duplicate prints, no production file changes. `git diff main -- src/` is empty.
- G-2: Book PDF pixels do not change unless a printed duplicate is found. The existing baselines (`tests/fixtures/book_baseline_card167.json` and earlier) still pass unchanged.
- G-3: Do not change `export/pdf.py:render_pages`. Its two-page contract and CON-019's A4/CLI golden are COMP-007's. Removing the dropped solved page is a separate decision (see Worktree notes).
- G-4: The band's wording stays ADR-0037/R1's "Puzzle N · Tier"; `test_PropertyTest_BookPdf_BandIsPuzzleNumberAndTierForEveryPuzzle`, `TestBookPdf_PuzzlePageCarriesNoPictureTitle` and `TestBookPdf_AnswerKeyCarriesPictureTitle` stay green unedited.
- G-5: The one-page-retained memory equality in `tests/test_book_pdf_memory.py` stays green.
- G-6: The new tests read the PDF bytes, not the generator's in-memory pages. The pixel test must not call `_blank_page` or `render_pages` to get the page it checks.

## System contract

_Assembled 2026-10-04 by `system_rules.py --card CARD-170` (7 rules). A projection — fix the source artifact, never this list._

- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. CI installs Chromium… (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to… (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **Requirements:** FR-033 (AC-193 / AC-194: the title only on the answer key; the puzzle page band is "Puzzle N · Tier"), FR-040 (two-up pages, one band per slot), FR-042 (packed answer key: captions, no band).
- **ADRs:** ADR-0037/R1 (band wording), ADR-0036/R2 (COMP-007 lays out; the panel strokes).
- **Constraints:** CON-019 (CLI/A4 PDF golden; untouched).
- **Components:** COMP-009 (`src/nonogram/admin/book_pdf_generator.py`) is the subject. COMP-007 (`src/nonogram/export/pdf.py:render_pages`) is the likely site of the second draw, read-only here.
- **Trace:** FR-033 → COMP-009 `_blank_page` / `_two_up_page` → COMP-007 `render_pages` / `_draw_header` → tests/test_book_pdf_band.py.
- **See also:** meta/releases/wave-32.md, "Known gaps": "To check: the goal-check's PDF recorder saw the highest-tier answer-key band drawn twice …". Nothing in meta/kanban/retro.md.

## Design context

- **Output:** interior PDF: the Hard puzzle's page (printed alone), one two-up page, one answer page.
- **Renders:** ~/Documents/nonogram-reviews/CARD-170/ (owner visual check: one band per puzzle, nothing doubled or shadowed).

## Worktree notes

- [Touches] The last three Touches apply only if the duplicate proves real; otherwise the card commits tests/test_book_pdf_band.py alone (tests/helpers/pdf_pages.py is read, not changed). Listed in full so the dispatcher serializes this card with CARD-169 (shared book_pdf_generator.py).

- [Origin] Roadmap wave 1: IDEA-090 (tech-debt, P1, WSJF 16), "answer-key band drawn twice in an export (printed duplicate?)", from the wave-32 goal-check.
- [Verified 2026-10-04, read only] Likely cause: `render_pages` (`src/nonogram/export/pdf.py:423-468`) sets the header on the blank page **and** the solved page (lines 465-467). `BookPDFGenerator._blank_page` (`book_pdf_generator.py:1827-1842`) drops the solved page. So every puzzle printed alone has its band drawn twice, once on a bitmap that is never written. Paired puzzles (`_two_up_page`, 1970-2011) draw each band once. Callers: lines 2559 (`_blank_page`), 2563 (`_two_up_page`), 2584 (`_answer_page`).
- [Verified] "Measure then draw" is not the mechanism. `_set_band` (773-820) and `export/pdf.py:_draw_header` (322-405) measure with `font.getlength` and call `draw.text` once per piece.
- [Verified] The PDF has no text objects. Each page is one DCT image (`_write_page`, 2707-2776). So "printed twice" can only mean ink in the image. Two draws at the same spot would give the same pixels. The pixel test therefore looks for a second **copy** (another page, or an offset in the strip), and the recorder test (AC-3) separates written from unwritten images.
- [Reuse] `tests/test_book_pdf_band.py` already has `_book`, `_puzzle`, `print_plan`, `puzzle_page_number`, `answer_page_number` and `_band_strip`. `tests/helpers/pdf_pages.py:pdf_pages` decodes the exported bytes.
- [Owner decision, out of scope] Stop rendering `render_pages`' unused solved page for book puzzle pages? It costs one full-size bitmap and a full render per puzzle printed alone (docstring lines 213-224 already record this). It would mean a COMP-007 API change (a blank-only render), so it needs its own card. Suggest a backlog line rather than doing it here.
