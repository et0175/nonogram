# CARD-144: A frame around the puzzle on book pages — the clue bands boxed, the CLI untouched

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/144-book-puzzle-frame
**Worktree:** —
**Source:** owner, 2026-09-23 ("I'd add a frame around puzzle, around the top and left sides"), shape and scope settled by AskUserQuestion the same day
**Idea:** —
**Wave:** 26
**Depends on:** CARD-141
**Touches:** src/nonogram/export/layout.py, src/nonogram/export/png.py, src/nonogram/export/pdf.py, tests/test_book_puzzle_frame.py
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-09-24T18:09:15Z
**Closed:** 2026-09-25T05:22:29Z
**Actual:** —
**Merge commit:** e2a5b3b
**Blocked by:** —

## What to implement

A book puzzle page draws the clue bands as bare numbers beside the grid. The owner asked for
the classic framed look: one rectangle around the whole block, with the clue bands boxed off
from the grid and an empty corner box.

    +---+-------+
    |   | 2   1 |      <- column clue band, boxed
    |   | 1   3 |
    +---+-------+
    | 1 | | | | |
    | 2 | | | | |      <- row clue band, boxed
    | 3 | | | | |
    +---+-------+

1. **Book pages only.** The owner chose this over framing standalone exports, so CON-019
   stands and the golden A4 fixtures are not touched. Carry it as a new optional `PageSpec`
   field defaulting to *off*, so `compute_layout` called without a PageSpec produces exactly
   today's A4 geometry and ink (ADR-0036/R1). The book's PageSpec turns it on; the CLI and
   web paths never do.
2. **The frame is ink, not geometry.** Draw it on the boundaries the layout already computes
   — the outer edge of the clue gutters and the grid's existing outer border, which already
   serves as the divider between band and grid. The cell size, the drawing's position and
   the gutter depths must not move by a single pixel: every measured figure stays as it is
   (4.97 mm on the 30x30 with 9-deep clues, 7.5 mm on the 15x15, the two-up 7.39 mm pair).
   If a cell figure changes, the implementation has gone wrong.
3. **Weights follow ADR-0037/R2.** The frame uses the heavy rule — the same weight as the
   grid's outer border, twice the thin rule, pure black. It must not introduce a third
   weight.
4. **Both trims.** The owner likes 6x9 and 8.5x11 alike, so the frame must sit correctly on
   any stored trim and on both page parities, and on a two-up page it frames each puzzle of
   the pair separately, not the pair as a whole.

Out of scope: framing answer-key tiles (they are a packed grid of their own and the owner
did not ask), the guide, divider or cover pages, and any change to the band that carries
"Puzzle N · Tier".

## Acceptance criteria

- New: on the book PageSpec a puzzle page carries a closed rectangle around clues and grid,
  with the clue bands boxed and the corner empty.
  test: TestPuzzleFrame_BookPageCarriesTheFrame
- New: `compute_layout` without a PageSpec, and every CLI/web export, are byte-identical to
  before this card.
  test: TestPuzzleFrame_DefaultPageSpecIsUnchanged
- New: the cell size and drawing origin on the book PageSpec are unchanged by the frame, for
  a 30x30 with 9-deep clues and a 15x15.
  test: TestPuzzleFrame_GeometryIsUnmovedByTheFrame
- New: every frame rule is the heavy weight, at least twice the thin rule, in pure black.
  test: TestPuzzleFrame_UsesTheHeavyRuleOnly
- New: on a two-up page each puzzle is framed separately.
  test: TestPuzzleFrame_PairIsFramedPerPuzzle

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical, and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited. The tripwire must not move at
  all. test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden,
  PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry
- G-2: ADR-0037/R2 — thin rules at least 0.25 mm, heavy exactly twice the thin, pure black.
  No new stroke weight.
- G-3: Geometry is unchanged. This card adds ink only; no cell fitting, gutter depth or
  origin may move. CARD-116's and CARD-118's measured figures stay green.
- G-4: Do not edit `src/nonogram/admin/**` — the panel decides no geometry (ADR-0036/R2).

## Architecture context

- **FR:** — (untraced: owner intake, `meta/architecture/inputs/raw-requirements.md:265`, 2026-09-23 — NOT FR-041, which is the level-divider and print-order requirement; see F-002 in the notes below)
- **CON:** CON-019 (byte-identity), CON-018 (margins)
- **ADR:** ADR-0036 (PageSpec, geometry ownership), ADR-0037 (stroke weights)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23, reviewing the CARD-118 proof renders on both trims. The frame
  shape was chosen from three sketches (boxed clue bands, one plain outer rectangle, or an
  open top-and-left L) and the scope from two (book pages only, or everywhere). The owner
  took the boxed clue bands, book pages only — explicitly keeping CON-019 intact rather than
  amending it and regenerating the goldens.
- [Why it waits for CARD-141] Both edit `src/nonogram/export/layout.py`.

- [What shipped] `PageSpec` gains an optional `frame: bool | None = None` and a
  resolved `PageSpec.framed`; `Layout` gains `frame: PuzzleFrame | None = None`,
  built by one helper that both `compute_layout`'s placed path and
  `_slot_layout` (two-up) call. `png._draw_frame` strokes it after the grid.
  `pdf.py` needed no code — both its pages are the PNG raster, so the frame
  arrives on the blank page and on the revealed one for free; only its
  docstrings changed. New file `tests/test_book_puzzle_frame.py`, 45 tests.

- [Frame vs boundary — the decision, and where it is pinned] The frame is drawn
  **on** its four boundaries, so Pillow centres each stroke there and half a
  heavy rule (3 px of 6, 0.25 mm) falls outside the drawing box on every side.
  That is the same thing the grid's own outer border already does — it hangs
  3 px right of `grid_right` — and the frame's right and bottom sides *are*
  that border, so an inset frame would sit a full rule out of step with the two
  sides it continues. Measured on a rendered page, the frame's left rule
  occupies offsets `-2..+3` about the drawing's left edge and the grid's right
  border the identical `-2..+3` about `grid_right`.
  `TestPuzzleFrame_UsesTheHeavyRuleOnly.test_the_frame_straddles_its_boundary_exactly_as_the_grids_border_does`
  requires those two offset lists to be equal and to straddle zero, so an
  inset frame and a half-rule-out-of-step frame both fail it.

- [Deviation from the card: what turns the frame on] The card says "the book's
  PageSpec turns it on", but the book's `PageSpec` is built in
  `src/nonogram/admin/book_page_spec.py`, which guardrail G-4 forbids editing.
  The frame is therefore defaulted rather than set: `frame=None` (the default)
  means *a placed page is framed, a drawing-sized image is not*, which is
  "book pages only" stated in COMP-007 — the component ADR-0036/R2 says owns
  print geometry — instead of in the panel. `DEFAULT_PAGE_SPEC.framed` is
  False, so CON-019 is untouched, and an explicit `frame=True/False` still
  overrides either way. No file under `src/nonogram/admin/**` was edited.

- [Known gap, and it is G-4's] A **two-up** page is composed by
  `admin/book_pdf_generator._stroke_drawing`, which deliberately reimplements
  the grid stroking from `slot.vertical_lines`/`slot.horizontal_lines` and so
  does not draw `slot.frame`. The pair geometry *is* framed per puzzle —
  `compute_pair_layout` gives each slot its own `PuzzleFrame` on its own
  drawing box, which `TestPuzzleFrame_PairIsFramedPerPuzzle` pins — but nothing
  yet strokes it, so a printed two-up page has no frame. Closing it is one line
  in `_stroke_drawing` (stroke `slot.frame` after the lines), in a file G-4 put
  out of bounds for this card. Measured, not assumed: interior page 3 of the
  CARD-145 baseline book (the two-up page) is byte-identical to its
  pre-frame recording, while interiors 2 and 4 (the single-puzzle pages) moved.
  **A follow-up card is needed for the two-up rendering.**

- [Geometry] Unmoved, as the card requires: the 30x30 with 9-deep clues still
  prints at 4.97 mm and the 15x15 at the 7.5 mm cap, and
  `replace(framed_layout, frame=None) == unframed_layout` holds field for
  field over a seeded corpus of 240 cases across three trims (8.5x11, 6x9,
  7x10) and both parities. Every CARD-116/CARD-118 measurement stayed green
  once the ink measurer was taught about the frame (below).

- [SCOPE+ — test helpers and the book baseline] The frame is ink, so everything
  that measures a book page off its ink had to learn it exists:
  - `SCOPE+ tests/helpers/page_ink.py` — `drawing_of` counts grid rules by
    counting full-extent ink runs, and the frame's left and top sides are two
    more of those, so `columns`, `rows` and therefore the measured cell were
    all one out. It now tells the frame from the grid the way it tells
    everything else — by where it is: the leftmost full-height rule is the
    frame's exactly when its own ink covers the point the horizontal rules
    start from. No call site changed.
  - `SCOPE+ tests/helpers/two_up_ink.py` — `split_row` cut at the widest gap
    between rule rows, and on a framed single page the frame-top-to-grid-top
    gap (a whole clue gutter, 4 cells) is wider than the 12 mm band that
    separates two slots, so a one-puzzle page was being cut through its own
    gutter. The cut now goes through the widest gap **no vertical rule
    crosses**, which is a real property of the page rather than a ratio, and
    `_GAP_RATIO` is gone.
  - `SCOPE+ tests/fixtures/book_baseline_card144.json` (new),
    `tests/fixtures/book_baseline_card145.json` (+2 fields),
    `tests/helpers/book_corpus.py`, `tests/test_book_pdf_memory.py`
    (docstring) — CARD-145 recorded a per-page pixel baseline of the book's
    interior. This card deliberately changes two of those eight pages, which
    is exactly the case that fixture's own `warning` provides for: "a later
    card that deliberately changes a page's content records a NEW baseline in
    a commit of its own, with its own card number, and says so here." Done as
    written — new fixture under this card's number naming the two changed
    pages and why, `BASELINE_FIXTURE` repointed, the old file left otherwise
    unedited with a `superseded_by`/`superseded_note` pair. No digest was
    rewritten to make a test fail less.

- [G-1] `tests/fixtures/a4_golden/**` untouched;
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` and
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` were run
  first and stayed green throughout.

- [The stale FR-042 formula at requirements.yml:3295] Not depended on. Answer
  tiles are out of this card's scope, nothing here sizes anything from that
  formula, and `compute_answer_page_layout` was not touched — a test asserts
  an answer tile carries no frame. The staleness CARD-141's review found is
  still there for whichever card owns it.

- [Proof renders] `~/Documents/nonogram-reviews/CARD-144/` — the CARD-118
  proof pages on both trims (8.5x11 and 6x9), now framed, plus interior pages
  2, 3 and 4 of the baseline book, which show the framed single pages beside
  the still-unframed two-up page.

[Touches drift] tests/fixtures/book_baseline_card144.json, tests/fixtures/book_baseline_card145.json, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/helpers/two_up_ink.py, tests/test_book_pdf_memory.py — 6 files beyond Touches, all declared SCOPE+
[Runtime conflict] OBSERVED, not predicted: CARD-144 and CARD-128 are both editing tests/fixtures/book_baseline_card145.json, tests/helpers/book_corpus.py and tests/test_book_pdf_memory.py. Neither card's Touches named them, so the conflict graph could not serialize them. Both are independently re-recording CARD-145's per-page book baseline for their own change. Merge order matters and the second card must re-record, not resolve textually.
[Unmet AC] The "two-up framed per puzzle" AC passes as GEOMETRY only. A printed two-up page carries NO frame: admin/book_pdf_generator._stroke_drawing composes it from slot.vertical_lines/horizontal_lines and never draws slot.frame. Measured, not assumed — interior page 3 is byte-identical to its pre-frame recording while pages 2 and 4 moved. The fix is one line in a file G-4 put out of bounds, and which CARD-128 is editing right now.

- [Rebased onto CARD-128, baseline re-recorded] CARD-128 merged first (557c7ac), by
  the owner's ruling, and this branch was rebased onto `main` at 3c7b7dd rather than
  resolving the shared files textually. Three files collided; each was combined, none
  taken wholesale:
  - `tests/helpers/book_corpus.py` (CONFLICT) — CARD-128's numbers are the new truth
    and were kept exactly: `BASELINE_PAGE_COUNT = 11`, `CORPUS_PAGE_COUNT = 182`, the
    module docstring's eleven-page/182-page interiors, and the corpus data itself
    (the four baseline rows, their deliberately-not-in-print-order arrangement and
    `corpus_puzzles`) untouched. Only `BASELINE_FIXTURE` is this card's: it now names
    `book_baseline_card144.json`, and its comment records the whole chain — 145 (the
    merge-base's eight pages) → 128 (eleven, level dividers) → 144 (framed) — with
    all three files kept and none regenerated.
  - `tests/test_book_pdf_memory.py` (CONFLICT) — every strengthened assertion of
    CARD-128's survives unweakened: `machine_face == {1, 2, 4, 6, 8}` (five
    dividers/guide, not one), the eight answer-ink-free pages `(1..8)`, the three
    answer pages `(9, 10, 11)`, the `> 16 * small.seen` premise, the level-divider
    identifications and the interior-5/7 parity measurement. **No count needed
    changing for the frame**: the frame is ink on pages that already carried a
    drawing, so no page changed kind. Only the `TestBookPdfMemory_PagesAreUnchanged`
    docstring is this card's, restating the chain of recordings.
    `big.peak == small.peak` and `PEAK_IN_PAGES == 1.00` were not touched.
  - `tests/fixtures/book_baseline_card145.json` (auto-merged, and wrong) — the
    textual auto-merge left **two `superseded_by` keys** in one object, this card's
    at the top and CARD-128's below, because they landed in different places. Fixed
    back to `main`'s version exactly: this file is now byte-identical to `main`, zero
    additions and zero deletions. CARD-145's successor is CARD-128, and the chain is
    followed from there; the pre-rebase note here was also stale (it named interiors
    2 and 4, the pre-divider numbering).

- [The re-recorded baseline] `tests/fixtures/book_baseline_card144.json` was recorded
  again from the rebased tree, through the same two calls the test makes
  (`export_of(BookPDFGenerator(corpus_book()), baseline_puzzles())`, then
  `pdf_pages`), and it now describes an interior that is **both** eleven pages with
  level dividers **and** framed — which neither predecessor described. Against
  `book_baseline_card128.json`: same page count (11), same font fingerprint, same
  `font_dependent_pages` `[1, 2, 4, 6, 8]`, `interior_bytes` 2,614,114 → 2,637,748
  (+23,634, the two frames' JPEG cost), and exactly **two digests moved: interior 5
  (the 15x15 Medium) and interior 7 (the 30x30 Hard)**, the book's two single-puzzle
  pages. The other nine digests are CARD-128's own, byte for byte. The fixture carries
  `why_a_new_baseline`, `changed_pages`/`changed_pages_note`, and a
  `recorded_from_commit` of **3350c2a**, the rebased commit itself and the first tree
  that reproduces these digests — the pre-rebase tip 7288f2e writes eight pages and
  CARD-128's 407c0cc writes eleven unframed ones, so neither can. A commit cannot
  carry its own hash, so the SHA is filled in by 672e23a, the one commit that
  immediately follows, which edits that field and its note alone and therefore
  exports the same eleven pages. That avoids CARD-128's own review finding, where the
  field named a tree that produces a different page count. `book_baseline_card128.json` **is** superseded and says so in
  a single added `superseded_by` line; not one of its digests was rewritten
  (`git diff main` on it: 1 insertion, 0 deletions).

- [Two-up gap re-confirmed after the rebase — still CARD-146's, still open] CARD-128
  moved which pages are two-up, so it was re-measured rather than assumed. Reading
  every interior page's ink off the rebased export with `two_up_ink.drawings_of`:
  interior 3 is the two-up page and reports `framed=[False, False]` for both slots,
  and its digest is identical to CARD-128's recording; interiors 5 and 7, the single
  puzzle pages, report `framed=[True]` and are the only two digests that moved.
  Interiors 1, 2, 4, 6 and 8 carry no ruled drawing at all (guide and the four
  dividers) and 9-11 are the packed answer key, whose digests are also unchanged —
  FR-042's tiles are out of scope. So the gap is still exactly and only the printed
  two-up page, `admin/book_pdf_generator._stroke_drawing` still never strokes
  `slot.frame`, and nothing under `src/nonogram/admin/**` was edited (G-4).

- [Guardrails after the rebase] G-1 holds: `tests/fixtures/a4_golden/**` untouched,
  and `tests/test_export_a4_golden.py` plus
  `tests/property/test_cli_exports_byte_identity.py` are green. G-2 and G-3 are
  unaffected by the rebase — no production file of this card changed in it; the whole
  resolution was in the test tree. Full suite from the worktree root: one failure,
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`,
  which is the known pre-existing one.

[Rebase] Rebased onto main after CARD-128 merged, per the owner's merge-order ruling. Tip 672e23a.
[Rebase] THE AUTO-MERGE WAS MANGLED, which vindicates re-recording over resolving textually: git silently produced TWO superseded_by keys in one JSON object (CARD-144's and CARD-128's at different line positions, so neither side conflicted). CARD-144's pair was also stale on its face — it named "interior 2 and interior 4", the pre-divider numbering. Reverted to main's version exactly.
[Rebase verified by orchestrator] book_baseline_card145.json diff vs main: 0 lines, digests intact. book_baseline_card128.json: 1 insertion, 0 deletions — superseded_by only, no digest rewritten. tests/fixtures/a4_golden/** absent from the diff. tests/test_book_pdf_memory.py diff vs main is docstring-only — every strengthened CARD-128 assertion survives verbatim (machine_face == {1,2,4,6,8}, the 8 answer-ink-free pages, big.seen > 16 * small.seen), and big.peak == small.peak / PEAK_IN_PAGES == 1 are untouched.
[Rebase] Re-recorded baseline describes an interior that is BOTH 11 pages with dividers AND framed — which neither predecessor described. Exactly two digests moved (interior 5 and 7, the single-puzzle pages); the other nine are CARD-128's byte for byte. interior_bytes +23,634.
[Rebase] recorded_from_commit is 3350c2a, the first tree that reproduces these digests, written in by the following commit 672e23a — avoiding the provenance defect CARD-128's reviewer filed.
[Two-up gap] Re-measured after the rebase, not assumed, since CARD-128 moved which pages are two-up: interior 3 (two-up) is framed=[False, False]; interiors 5 and 7 (single) are framed=[True] and are the only digests that moved. The gap is still exactly and only the printed two-up page. CARD-146 owns it.
[Review 1/3] score 7.5 — 0 critical, 1 important, 3 minor. Risk MEDIUM. Production code clean; G-1 verified by the reviewer running the 66 tripwire tests itself.
[Review sync] 1 report -> meta/review/
[Mutation] 16 mutants, 16 killed, 0 survived — including two on EACH rewritten measurement helper, which was the worst case to rule out. Restores proved by sha256.
[Review] F-001 (important): page_ink.drawing_of's new frame heuristic MISFIRES on the packed answer-key pages. An answer tile has no clue gutter, so the tile's own edge IS its grid's border — the heuristic's positive condition. It then drops a real rule from each axis: interior 10 reads 14x14 instead of 15x15, interior 11 reads 29x29 instead of 30x30. Breaks no test today (the only answer-page assertions read .left and .grid_right, both computed before the drop) and is DATA-DEPENDENT, not systematic — interior 9 escapes because its heading changes which group is topmost. Drawing.framed answers True for pages carrying no frame.
[Review] two_up_ink.py PASSES: the new "widest gap no vertical rule crosses" is strictly stronger and pitch-independent; measured separation is 42-120 crossing columns inside a drawing vs exactly 0 across the inter-slot strip. Removing _GAP_RATIO lost no guard doing real work.
[Review] G-4 "defaulted not set" deviation RULED ACCEPTABLE, no blocker owed: book_page_spec.py:271 is the ONLY parity-bearing PageSpec construction in src/, so "placed => framed" is equivalent to "book => framed" today; and putting the verdict in export/layout.py is MORE ADR-0036/R2 compliant than the card's own wording, which would have had the panel state print geometry.
[Review] The 3 px frame overhang collides with nothing — measured on the real export: 2 px into a 148-450 px margin, 5 px with 108-411 px to the trim edge, 47 px clearance below the band's lowest ink. The grid's own border already hung the same amount before this card.
[Review] AC "two-up framed per puzzle" is MET AS GEOMETRY, NOT END-TO-END. Reviewer's note: the owner should see that sentence. Already surfaced; owner ruled 2026-09-24 to merge with the gap and close it in CARD-146.
[TRACEABILITY DEFECT — architect station] F-002: the frame is cited to FR-041 at ~15 sites, but FR-041 is the LEVEL-DIVIDER requirement (CARD-128's) — requirements.yml:3082-3125 is entirely about easy/medium/hard ordering and divider pages, and trace.yml:1834 lists its components as COMP-009/010, not COMP-007. NO FR, AC or EC anywhere mentions a frame. The frame is owner intake recorded at raw-requirements.md:265 that was never formalised, so this card implements unformalised scope wearing another FR's id.
[Owner note] book_proof.py:513 renders proof pages on a parity spec, so PROOF PAGES ARE NOW FRAMED TOO. Correct — they are proofs of book pages, and the renders show them framed — but a second consumer the card's "book pages only" wording never names.
[Fix 1 — recovered] The fix agent STALLED and was killed by a watchdog before verifying, committing or reporting. Its uncommitted work was checked and committed by the orchestrator as 837075b after confirming the baselines changed by prose only and layout.py was docstring-only, then re-verified (66 tripwire tests, full suite). Cycle 2 was told to treat it as unreviewed code.
[Review 2/3] score 9.0 — 0 critical, 0 important, 2 minor. CONVERGING, family-regression rule does NOT fire.
[Review 2/3] F-001 closed with independent evidence: interiors 10 and 11 back to 15x15 and 30x30 with framed=False; all nine unframed pages field-for-field identical to main; interiors 5 and 7 correct at framed=True. Interior 9 now rejected by the NEW weight test rather than by the heading accident that saved it before. 1,770 synthetic pages (5 trims x 2 parities x 11 extents x 5 clue depths, raw and JPEG-decoded, single and multi-tile answer pages, proof pages, two-up, default A4) — zero wrong verdicts. Sweeping _RULE_SHARE 0.50-0.99 and INK_LEVEL 64-224 changes no verdict.
[Review 2/3] The fix round changed executable code in exactly ONE file — AST comparison with docstrings stripped shows layout.py, pdf.py, png.py, two_up_ink.py, book_corpus.py and test_book_pdf_memory.py all code-identical; only page_ink.py differs. No production logic changed at all.
[F-101 fixed by orchestrator] 3c679ae — the ast guard matched only PageSpec(...), so replace(DEFAULT_PAGE_SPEC, parity=...) — the idiom layout.py itself uses on this type — would have passed silently, the sheet acquiring a frame with the a4_golden tripwires blind to it (they only exercise DEFAULT_PAGE_SPEC). Widened to match replace by name; verified green on the clean tree and failing when a replace-shaped producer is added. Neither existing replace in src/ carries a parity.
[F-102 fixed by orchestrator] The card's Architecture context said FR: FR-041. Replaced with the honest untraced attribution naming the intake line.
[Handover to CARD-146] The two-up page still carries no frame — confirmed unchanged (0 admin edits, interior 3 framed=[False, False]).
[Latent, not filed] page_ink.py:214 — the GUIDE page now satisfies both frame conditions on its H axis from TEXT runs rather than rules; only the V axis rejects it. Had both passed, drawing_of would raise a misleading "carries a frame but no ruled grid inside it". No test measures interior 1 with drawing_of and create_guide_page draws no grid, so it is latent only.
