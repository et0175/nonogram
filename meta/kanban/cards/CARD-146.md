# CARD-146: The frame reaches the printed two-up page

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/146-two-up-frame
**Worktree:** —
**Source:** CARD-144 review gap, 2026-09-24 (owner's ruling: merge CARD-144 with the gap, close it here)
**Idea:** —
**Wave:** 27
**Depends on:** CARD-128, CARD-144
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/fixtures/book_baseline_card146.json, tests/helpers/book_corpus.py
**Review score:** 9.0 (1 cycle + fix)
**Started:** 2026-09-30T16:40:00Z
**Closed:** 2026-09-30T19:15:00Z
**Actual:** 0.1d
**Merge commit:** b9a17d3
**Blocked by:** — (cleared 2026-09-30: CARD-128 merged 557c7ac, CARD-144 merged e2a5b3b)

## What to implement

CARD-144 added a frame to book puzzle pages and it works on single-puzzle
pages. **A printed two-up page still has no frame.**

The cause is not a bug in CARD-144's geometry: `Layout.frame` is computed for
both slots of a pair, and CARD-144's tests confirm it. The two-up *page* is
composed by `src/nonogram/admin/book_pdf_generator._stroke_drawing`, which
deliberately reimplements grid stroking from `slot.vertical_lines` /
`slot.horizontal_lines` (the native-reimplementation convention this codebase
uses instead of importing across capability boundaries) — and therefore never
draws `slot.frame`.

CARD-144 could not close this: its G-4 guardrail put `src/nonogram/admin/**`
out of bounds, and CARD-128 was editing that same file concurrently. The
guardrail was correct; this card is where the work belongs.

Draw each slot's frame in `_stroke_drawing`, using the same heavy rule and the
same on-the-boundary placement CARD-144 chose for single pages, so a pair reads
as two framed puzzles rather than two bare grids.

**Measured evidence of the gap** (from CARD-144's implementation, not assumed):
interior page 3 of the baseline book — the two-up page — is byte-identical to
its pre-frame recording, while interiors 2 and 4 (single-puzzle pages) moved.

## Acceptance criteria

- **AC-1:** On a book whose print order pairs two puzzles onto one interior
  page, each of the two drawings carries its own closed frame — clue bands
  boxed, corner empty — matching a single-puzzle page's frame.
  *test: TestPuzzleFrame_PairIsFramedOnThePrintedPage*
- **AC-2:** Each frame rule on a two-up page is the heavy weight, at least
  twice the thin and pure black (ADR-0037/R2). No new stroke weight is
  introduced. *test: TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly*
- **AC-3:** Frame placement on a two-up page straddles its boundary exactly as
  a single page's does, so the two presentations agree.
  *test: TestPuzzleFrame_TwoUpStraddlesItsBoundaryLikeASinglePage*
- **AC-4:** Cell size, slot origin and page geometry are unchanged — this card
  adds ink only. CARD-127's and CARD-118's measured figures stay green.
  *test: TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame*

## Guardrails

- G-1: CON-019 — CLI and web A4 output stay byte-identical and
  `tests/fixtures/a4_golden/**` is NOT regenerated or edited.
- G-2: ADR-0037/R2 — no new stroke weight; reuse the heavy rule.
- G-3: Geometry is unchanged. Ink only; no cell fitting, gutter depth or origin
  may move.
- G-4: Do not change `src/nonogram/export/**`. CARD-144 already placed
  `slot.frame` there correctly; this card only consumes it.
- G-5: Do not regress CARD-145's streaming property — peak memory stays
  O(one page). `_stroke_drawing` runs inside the per-page path; do not
  accumulate.

## Architecture context

- **FR:** FR-041
- **ADR:** ADR-0036/R2 (the panel decides no geometry), ADR-0037/R2 (stroke weights)
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes
- [Env] forge 2026.8.17
- [Blocker cleared] Both dependencies merged: CARD-128 at 557c7ac, CARD-144 at e2a5b3b. The
  note's caveat that "the baseline this card's tests read must be the post-CARD-144 one" is now
  out of date in a way that matters — the live baseline is **`book_baseline_card149.json`**
  (CARD-149 re-recorded it on 2026-09-30 for the guide page's type), and `BASELINE_FIXTURE` in
  `tests/helpers/book_corpus.py:97` points there.
- [Card gap, ruled IN scope by the orchestrator] The card's `Touches` names only
  `book_pdf_generator.py` and `tests/test_book_puzzle_frame.py`. But drawing a frame on the
  two-up page **necessarily moves interior page 3's pixels**, which is exactly what the card's
  own "measured evidence of the gap" says is byte-identical today. So the baseline must be
  re-recorded — a new `book_baseline_card146.json` superseding CARD-149's, in its own commit,
  with `changed_pages: [3]`. `Touches` has been extended to name the fixture and
  `tests/helpers/book_corpus.py` (which holds `BASELINE_FIXTURE`). Without this the card would
  hit a red baseline assertion and the tempting wrong move would be to regenerate CARD-149's
  file, which its own `warning` field forbids.
- [Precedent to follow, not invent] CARD-149 did this correctly four commits ago: a new fixture
  under its own card number, in a commit of its own, `changed_pages` naming only the pages that
  actually moved, verified page by page against the superseded file rather than trusting the
  field. Its cycle-1 review called the discipline exemplary and judged the deliberately-red
  intermediate commit to be the point — it is the evidence the ink moved.

[Origin] Cut 2026-09-24 from CARD-144's implementation report. The owner chose
"merge CARD-144 with the gap recorded, close it in a follow-up" over escalating
CARD-144 back to the decompose station, so that the wave kept moving and the
guardrail was not weakened inside a worktree.

[Sequencing] Blocked on CARD-128 and CARD-144 because both edit
`book_pdf_generator.py` and the shared book baseline fixtures. Unblock once both
are merged; the baseline this card's tests read must be the post-CARD-144 one.
[Implementation, 2026-09-30] Done on `card/146-two-up-frame`, two commits.

**What changed.** `_stroke_drawing` (`src/nonogram/admin/book_pdf_generator.py`)
strokes `slot.frame` after its grid loop — four sides, pure `INK`,
`frame.width` (the heavy rule, no new weight), each side *on* its boundary
coordinate so Pillow centres it there, which is exactly what
`export/png._draw_frame` does for a single page. It consumes `slot.frame` and
re-derives nothing; `src/nonogram/export/**` is untouched (G-4); the stroking
stays in the per-page path with nothing accumulated (G-5); the module docstring
now says the frame is part of what the panel strokes.

**AC → test** (all four stated on the *printed page*, never on the layout
object — a criterion phrased over `slot.frame` would have been green the whole
time the pair printed bare):

| AC | Test |
|----|------|
| AC-1 | `TestPuzzleFrame_PairIsFramedOnThePrintedPage` (7 tests) |
| AC-2 | `TestPuzzleFrame_TwoUpUsesTheHeavyRuleOnly` (4 tests) |
| AC-3 | `TestPuzzleFrame_TwoUpStraddlesItsBoundaryLikeASinglePage` (2 tests) |
| AC-4 | `TestPuzzleFrame_TwoUpGeometryIsUnmovedByTheFrame` (5 tests) |
| — | `test_PropertyTest_TwoUpFrame_EveryPrintedPairIsTwoFramedPuzzles` — seeded corpus, 30 pairs over two trims and both parities, floor `assert pairs >= TWO_UP_CORPUS_PAIRS >= 24` |

19 tests added in `tests/test_book_puzzle_frame.py`; all execute, none skip
(nothing here touches a database). **Nine of them are red without the src
change** — at least one in each of the four AC classes — checked by stashing
the fix and re-running.

**Digests.** Interior page 3 moved and nothing else did. Verified page by page
against `book_baseline_card149.json`: ten of eleven digests are that file's
byte for byte. Interior file 2,680,175 bytes where it was 2,666,560 — the two
frames' ink. Font fingerprint `cfa57e76…ba30b`, CARD-149's value, unchanged
and reproduced on this machine *before* a byte of this card was written; this
card letters nothing, so `MACHINE_FACE_SIZES` stays `(92, 46, 60)`. Page 3 is
not font-dependent, so this card's evidence is checkable without Arial.

**Baseline discipline.** `tests/fixtures/book_baseline_card146.json` added in
its own commit (43b7a6b), superseding CARD-149's, with `changed_pages: [3]`
verified rather than asserted. No predecessor fixture was edited or
regenerated; `tests/fixtures/a4_golden/**` untouched (G-1). The fix commit
(a024b1b) is *deliberately red* on `TestBookPdfMemory_PagesAreUnchanged`'s two
assertions — that redness is the evidence the ink moved, per CARD-149's
precedent.

**Visual review** (`review.visual` is off, so this description is the record).
Renders in `~/Documents/nonogram-reviews/CARD-146/`:
`before-page3-two-up.png`, `after-page3-two-up.png`,
`after-page5-single.png`, `corner-before-above-after-below.png` (a 1:1 crop of
the upper slot's top-left corner, before above / after below), plus `-thumb`
reductions. **The pair now reads as two framed puzzles.** Before, each slot's
clue gutters ran off into white — the column-clue digits hung in the air with
no rule above or left of them and the corner was open on two sides. After,
each drawing is a closed rectangle: a heavy rule along the drawing's top edge
above the column clues, a heavy rule down its left edge outside the row clues,
both clue bands boxed off from the grid by the grid's own border, and the
corner where the two gutters meet a closed, empty box. The two slots read as
two separate framed puzzles, not one rectangle around the pair — nothing is
ruled across the strip between them. Side by side with interior page 5 (a
single-puzzle page), the two presentations are the same printed object at two
cells.

**Suite:** 5411 collected, 5402 passed, 2 failed, 7 skipped. The two failures
are the pre-existing ones named in the brief
(`tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`
and `tests/test_wave3_e2e.py::TestWave3UIIntegration::test_batch_creation_form_renders`);
neither touches the book PDF path. The collected count rose from 5392 to 5411
— the 19 test items this card adds.

Not committed from this worktree: nothing under `meta/` (the orchestrator owns
the card copy). The notes above are for the orchestrator to merge into the
canonical card.

### Cycle 1 review (2026-09-30)

- [Review 1/3] **9.0** · risk LOW · lane FAST ·
  `meta/review/20260930T183020Z-CARD-146-cycle1.yml` · 0 critical, 0 important, 2 minor.
  **Ready to merge.** Branch base verified first (`merge-base` == main's head). Nothing the
  orchestrator pre-verified was wrong.
- **The frame is exact, not merely close — including draw order.** `_stroke_drawing`'s new
  block is token-for-token `export/png._draw_frame`: same unpacking, same four side tuples in
  the same order, same `fill=INK` (and `INK` is *imported from* `export.png`, so it is literally
  the same constant), same `width=frame.width`. The reviewer checked something the card never
  claimed: the order relative to the clues also matches — `png.render_image` does grid → frame →
  clues, and here it is grid → frame, then `_write_clues`, then `_set_band`.
- **The tests are on the ink, verified.** None of the 19 items asserts the card's claim on the
  `Layout` object; every AC-class test reads back through `_dark(page)` / `drawings_of(page)`.
  And the measurer is genuinely independent: `page_ink._outer_rule_is_a_frames` decides `framed`
  by asking the found rules two questions, and **`page_ink.py` and `two_up_ink.py` are unchanged
  by this diff** — the measurer was not tuned to the card.
- **G-3 (ink only) proven three ways**, including one the orchestrator could not have checked
  cheaply: `_stroke_drawing` has exactly **one** src caller — the two-up page — so nothing else
  *could* move. Plus INV-009/010/011/013's thirty named tests green, and the +1 px mutants
  killed, so "consumes the coordinates verbatim" is enforced rather than merely written.
- **G-5 holds**: the function holds no state, creates no object, returns nothing; the frame block
  adds four int locals freed on return. Peak memory stays O(one page).
- **Mutation: 6 mutants + a control, run on `git archive` extractions so the reviewed worktree
  was never written to.** Dropping the top side → 12 kills; the width off `frame.width` → 12;
  dropping the left side → 14. Dropping the **right** side survived — and is an **equivalent
  mutant, not a gap**: `frame.right == grid_right` and the grid's own border is already stroked
  there at the same width over the same extent, which both docstrings state. The control
  (src reverted to main's) failed **exactly 9**, across all four AC classes plus the property
  test, confirming the implementation's "nine red" claim precisely.
- **The property test's floor can fail**, proved both ways: the corpus is `for _ in range(16)`
  per trim×parity, so `pairs` is data-determined at 30; lowering the constant 24→20 goes red,
  and shrinking the corpus goes red. Neither branch of CARD-149's vacuity defect is present.
- System contract: 45 rules — 15 ✓, 30 ⚠ no_eligible_fact, 0 ✗, and `--verify-refs` reports
  `dead_check_ref: []`. **CON-020 ✓** on its first outing — the diff draws no text and names no
  type size, corroborated by the unchanged fingerprint. CON-019 fell outside the assembled set,
  so the reviewer verified it directly as G-1 instead.
- One extra piece of evidence the orchestrator had not cited: **`before-page5-single.png` and
  `after-page5-single.png` are sha256-identical** — independent confirmation that the
  single-puzzle presentation did not move.
- Minor findings:
  - **F-001, folded in** (e45f3da): `TestBookPdfMemory_PagesAreUnchanged`'s docstring still said
    the fixture was "currently `book_baseline_card144.json`", succeeded "twice", with "two
    predecessors". There are four. The staleness entered with CARD-149 and belongs as much to
    that card; it was fixed here because this card updated the *other* narrative of the same
    chain (`book_corpus.py`, "Three recordings" → "Five recordings") meticulously and left this
    one behind. Prose only — the test reads the constant.
  - F-002 (left open) AC-3's own comparison does not discriminate a 1 px placement error; the
    kill comes from its sibling at 3.492 against a 3.0 slack, 0.49 px of margin. Structural
    rather than sloppy — `_STRADDLE_SLACK_PX` must absorb the fractional boundary and Pillow's
    even-width centring — and weighted low because a 1 px offset is not a plausible regression
    when the code binds coordinates verbatim, while the realistic regressions are killed 12–14
    items wide.
- **[Model defect, for the architect station]** ADR-0029/R4's `check.ref` is
  `test_every_import_in_the_package_points_inward` — the import-graph guard — but the rule is
  about overlap masks relative to a line's known cells. The ref exists, so `--verify-refs`
  cannot catch it; a check that cannot test its rule is the same disease as a dead one. This is
  the **third** check-ref defect found this week (ADR-0006/R1's missing ref, twice).
- [Review sync] 1 report → meta/review/

### Orchestrator gates (2026-09-30)

- [Build gate] PASSED on 43b7a6b, orchestrator's own run: **5411 collected, 5402 passed,
  2 failed, 7 skipped** — exactly the +19 the implementation added, and the two failures are
  the long-known stale-heading assertions.
- [Guard] Baseline claims verified independently, page by page, rather than read off the
  report: **only interior page 3's digest differs** from CARD-149's, and the `changed_pages: [3]`
  field agrees with what actually moved. `book_baseline_card144.json`, `card145`, `card128` and
  `card149` are all byte-identical on this branch. The font fingerprint is
  `cfa57e76…ba30b` before and after — unchanged, as it must be for a card that alters no type
  size.
- [Guard] Looked at the renders myself, in particular
  `~/Documents/nonogram-reviews/CARD-146/corner-before-above-after-below.png`. Before: the
  column-clue digits hang with no rule above or to the left and the corner is open on two sides —
  two bare grids with numbers floating beside them. After: a closed rectangle per slot, the
  corner where the gutters meet a closed empty box, and **nothing ruled across the strip between
  the two slots**, so the page reads as two framed puzzles rather than one box around the pair.
- [Note] The implementation warned that the worktree's committed card copy predates the
  orchestrator's notes and that the appended block should be taken rather than the file. It was
  synced before any cleanup — the CARD-149 lesson applied rather than repeated.
