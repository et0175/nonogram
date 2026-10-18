# CARD-224: The grid goes back to centred, sitting at 42% of the puzzle area's spare height

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/224-grid-centred-again
**Worktree:** ../PythonProject4-card-224
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 2 ("Grids are pushed to one edge and pinned to the top. On most pages the lower third of the page is empty (pp. 28, 75, 125), so the page looks unbalanced") and "Puzzle area" + the artifact's own note on reversing CARD-204
**Idea:** —
**Wave:** 46
**Depends on:** CARD-222 (the area), CARD-223 (the QR must be out of the gutter strip before the strip stops existing)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/fixtures/book_baseline_card224.json, tests/helpers/two_up_ink.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** 2026-10-18T05:09:31Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Read this first: this card deliberately reverses the central decision of CARD-204, which
merged on 2026-10-14 after 12.2 days and 8 fix cycles.** The owner knows, and says so in the
artifact: *"This reverses the flush-right and flush-left placement from CARD-204 back to
centring. That alignment was what freed the gutter-side strip for the QR. Once the QR has its
own footer, centring is the calmer choice."* Treat CARD-204 as a decision the product has
outgrown, not as work to be undone carelessly: it also delivered the QR slot, the two-up
folio reserve and `export.layout.caption_slot`, **and all three of those stay**.

**Current behaviour (verified by reading the code).**

- A puzzle page's drawing sits **flush to the page's outer edge, mirrored by parity** (right
  on right-hand pages, left on left-hand ones) — CARD-204's placement, which made FR-032's own
  "centred" statement false. **The amendment logged for that in `backlog.md` was CANCELLED, not
  applied** (2026-10-17, commit `91609aa`), precisely because this card restores the centring:
  FR-032's "centred" clause stands as originally written and is correct again.
- The drawing is **pinned to the top** of its area under the band (FR-032's "fixed top edge"),
  which is what leaves the lower third of a page empty on pp. 28, 75 and 125.

**What changes.**

1. The grid is **centred horizontally** in the puzzle area again. Parity stops moving it.
2. Vertically it sits at **42% of the spare height** — the artifact's figure, with the
   artifact's reason: *"which looks centred once the header sits above it."* So 42% is an
   optical decision, not an arithmetic one. Declare it once, named, with that sentence as its
   docstring, and do not silently "improve" it to 50%.
3. The spare height is measured against CARD-222's puzzle area (header rule to footer rule),
   so the grid can never land on either rule.
4. Keep what CARD-204 built that this does not contradict: `caption_slot` (it bounded a real
   defect — a 65-character picture name putting ink 9.6 mm outside the page), the two-up folio
   reservation, and the QR (now in the footer, CARD-223).

**One trap, named because this family has already produced five regressions.** CARD-204's own
retro lesson is in `backlog.md`: `_draw_solved_slot`'s return value has **two** consumers,
`solved_puzzle_page` and `_packed_answer_page`, which must change together, and nothing in the
code enforces it. The same asymmetry produced a gating defect in CARD-203 cycle 1, CARD-203
cycle 2, CARD-204 Fix 7 and CARD-204 cycle 5. If this card changes anything a slot returns,
change both consumers in the same commit and say so.

## Acceptance criteria

- **AC-1** (happy, centred): *Given* a left-hand page and a right-hand page holding the same
  puzzle, *when* both are drawn, *then* the drawing's left and right margins within the puzzle
  area are equal to within a pixel, and the two pages place it identically — parity no longer
  moves it. (test: `TestBookPuzzleFrame_GridIsCentredOnBothParities`)
- **AC-2** (happy, the 42%): *Given* a puzzle area with spare height `s`, *when* the grid is
  placed, *then* the gap above it is `0.42 * s` and the gap below `0.58 * s`, measured off the
  drawn ink. (test: `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`)
- **AC-3** (guard, never on a rule): *Given* every grid size the book admits and every trim,
  *when* a page is drawn, *then* no grid or clue ink touches the header rule or the footer
  rule. (test: `TestBookPuzzleFrame_GridClearsBothRules`)
- **AC-4** (edge, the tallest grid): *Given* the tallest grid that fits at all, *then* the
  42% rule degrades to "as low as it fits" rather than pushing ink past the footer rule, and
  the page says which rule bound it. (test: `TestBookPuzzleFrame_TallestGridYieldsToTheFooter`)
- **AC-5** (guard, CARD-204's survivors): *Given* a 65-character picture name, *when* the
  answer page is drawn, *then* `caption_slot` still bounds it inside the usable area — the
  defect CARD-204 Fix 7 and Fix 8 closed does not come back with centring.
  (test: the existing caption-slot classes in `tests/test_book_solved_page.py`)
- **AC-6** (happy, the lower third): *Given* the corpus pages the owner named (28, 75, 125),
  *when* they are drawn, *then* the empty band below the grid is **0.58 of the puzzle area's
  spare height and the band above it 0.42** — so the spare is split in the 42/58 ratio instead
  of all of it falling below a top-pinned grid, and the band below is at most **1.4x** the band
  above. That is the measured form of "the page looks unbalanced": today the lower band is the
  *whole* spare. (test: `TestBookPuzzleFrame_NoEmptyLowerThird`)
  **Corrected 2026-10-17 (registry delta):** this criterion previously read "the empty band
  below the grid is no larger than the band above it", which **contradicts AC-2** — AC-2 puts
  0.42 of the spare above and 0.58 below, so the band below is deliberately the larger one.
  FR-032 was amended per AC-2 and the owner's artifact (AC-366/AC-367), so AC-6 was the wrong
  one and is corrected here rather than left to gate the card against a false claim.

## Guardrails

- G-1: FR-040's pairing behaviour is unchanged — this card moves a grid inside its slot, it
  does not change which puzzles share a page (test: the existing pairing tests).
- G-2: The two-up folio reservation CARD-204 added still holds: every two-up page keeps its
  folio (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-3: `caption_slot` is not removed or widened.
- G-4: Out of scope — the cell size (CARD-225), the slot split (CARD-226), the header's
  content (CARD-207).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-224 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-032 — settled on 2026-10-17 (commit `91609aa`), and not the way a mechanical pass would
  have settled it. Two clauses pull opposite ways and only one of them moved:**
  1. **CANCELLED, not applied** — the amendment CARD-204 had logged against the "horizontally
     the drawing is centred across the usable width" clause. Because this card *reverses*
     CARD-204's flush-by-parity placement, the centred clause is **correct again and stands as
     originally written**; writing CARD-204's logged amendment would have made the registry
     wrong in the opposite direction. The cancellation is recorded against the logged request
     in `meta/kanban/backlog.md`.
  2. **AMENDED** — the **fixed top edge** clause, which is what this card actually breaks. The
     drawing now **floats at 42% of the puzzle area's spare height** (gap above = 0.42 ×
     spare, gap below = 0.58 × spare), measured off the drawn ink. AC-190 is **retired** with
     its test `TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage`; **AC-366** and **AC-367**
     state the new truth, and EC-022's "one fixed offset … never varies between puzzle pages"
     is restated as the 42% ratio (instances now AC-189, AC-240, AC-366, AC-367).
  AC-366/AC-367 name this card's own planned test
  `TestBookPuzzleFrame_GridSitsAtFortyTwoPercentOfTheSpare`, which does not exist yet.
  **Nothing is owed at the architect station** — do not re-apply CARD-204's pending amendment.
- **Mirrored margins are now a geometric no-op on Book 1** (gutter == outside == 12.700 mm,
  CON-018 as amended 2026-10-17). FR-030's AC-272 and AC-273 now hold the same span
  (12.700..203.200 mm) and FR-032's AC-274/AC-275 the same left edge (25.45 mm), so on the
  default profile **a passing parity assertion about the usable area or a margin width is an
  identity, not evidence** that mirroring works. The mirroring rule (FR-030's last sentence,
  TERM-034) and EC-032's "gutter minus outside" formula stay true with a zero difference and
  still bite on any book storing **unequal** margins — the only configuration in which
  mirroring is actually under test. Owner decision 2026-10-17: record this, do not restore the
  asymmetry by changing a margin. An assertion about *which side* something sits on (left vs
  right by parity) still has teeth; one about *how wide* the margin is does not.
  For this card that lands on **AC-1**: "parity no longer moves it" is the right claim, but on
  Book 1 the before-and-after left edges coincide anyway (25.45 mm at both parities), so AC-1
  proves the centring, not the removal of the mirroring. A book with unequal margins is what
  makes the second half of that claim observable.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-032 (both clauses above — settled 2026-10-17, commit `91609aa`: the "centred"
  clause stands and CARD-204's logged amendment is cancelled; the fixed-top-edge clause became
  the 42% float, with AC-190 retired and AC-366/AC-367 added), FR-040 (pairing, unchanged).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1.
- **Components:** COMP-009, COMP-007.
- **Trace:** not updated by this card.

## Worktree notes

- [On reversing 12 days of work] CARD-204 cost 12.2d against a 2.5d estimate and found three
  real print defects on the way (a caption 9.6 mm outside the page, a caption overprinting a
  folio, two-up pages losing their folios). Those findings are *why* this reversal is cheap:
  the tests they left behind are the ones that will catch this card if it gets the geometry
  wrong. Reverting the placement is not reverting the card.

## Implementation notes (worktree, CARD-224)

- **The placement.** `compute_layout`'s placed branch is centred again
  (`usable_left + max(spare, 0) / 2`) and its top edge comes from a new
  `_placed_drawing_top(spec, band_bottom, drawing_height, thick_rule)`.
  `GRID_SPARE_ABOVE = Fraction(42, 100)` is declared once, in
  `export/layout.py`, with the owner's sentence ("which looks centred once the
  header sits above it") as its docstring, and is read in exactly one place.
- **One definition of the puzzle area.** `_puzzle_area_px(spec)` was extracted
  from `interior_frame`, which now calls it; the placement reads the same
  function, so the region a page *draws* and the region a drawing is *placed
  in* cannot drift.
- **Two new `PagePlacement` fields, all three constructors changed in the same
  commit** (`compute_layout`, `_slot_layout`, `_packed_tile_layout`):
  `band_bottom` (the band's foot, which `header_band` now reads instead of
  `drawing_top` — otherwise the band's type would drift down the page with the
  float, under the header rule) and `vertical_bound` (`"ratio"` / `"footer"` /
  `"slot"`), which is how "the page says which rule bound it" (AC-4) is
  answered.
- **The named trap: `_draw_solved_slot`'s return value is unchanged.** Nothing
  about the caption box `(caption_bottom, caption_right)` moved, so both
  consumers (`solved_puzzle_page`, `_packed_answer_page`) are unchanged too.
  What did change under them is where `compute_layout` puts the drawing the
  caption hangs below; `caption_slot`'s clamp (G-3) is untouched and still
  binds — centring restores half the page's spare, so the caption width at
  which it fires moved, and `tests/test_book_solved_page.py` now carries a
  title in each of the three regimes instead of one that had quietly stopped
  reaching the margin.
- **The two-up slot keeps its own vertical position** (its slot's band foot):
  splitting the page's puzzle area between two slots is CARD-226's (G-4). Both
  slots *are* centred horizontally, and `_slot_layout`'s `outer_reserve_px`
  parameter is gone with the anchor it corrected; `folio_reserve_px` still
  narrows `compute_pair_layout`'s *fit*, so FR-040's accept/refuse verdict and
  committed cell are bit-for-bit CARD-204's (G-1).
- **Owed at the architect station (not edited from this worktree): AC-252.**
  "The upper puzzle's drawing on a two-up page starts on the same pixel row as
  a 20x20 single puzzle's" is falsified by this card — the single page floats,
  the slot does not. The 2026-10-17 propagation pass retired AC-190 and
  restated EC-022 but did not reach AC-252. Its own test
  (`TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge::test_the_upper_slot_and_the_single_page_share_a_top_pixel_row`)
  is marked `xfail(strict=True)` with that reason, so it fails loudly if
  anyone "fixes" it by pinning a single page's drawing back to the band's foot.
  EC-022's own amended text also names "the upper puzzle's on a two-up page",
  which stays unimplemented for the same reason (CARD-226).
- **A measured, declared exception to AC-3.** A two-up page's *lower* slot has
  its drawing's bottom edge exactly on the footer rule — CARD-248 reserves one
  footer strip out of the pair's height, so the boundary and the hairline are
  the same row. That is the pairing geometry's, not this card's, and
  `TestBookPuzzleFrame_GridClearsBothRules` asserts the coincidence instead of
  skipping the page.

### Orchestrator: the scope gate, and the architect station (2026-10-18)

**[Touches drift]** 20 files changed; three are not named by the `Touches` field, and none is
scope growth:

| file | verdict |
|---|---|
| `src/nonogram/admin/book_proof.py` | consequence of centring — its `_fallback_spots` side strip was a *forced* choice when the drawing was flush and is now a real choice (both sides carry spare), and half as wide, so the corner fallback wins on more trims. COMP-009, already in the card's slice via `book_pdf_generator.py`. |
| `tests/test_layout_page_spec.py` | COMP-007's own tests, already in the slice via `export/layout.py`; the `Touches` globs covered `tests/test_book_*.py` but not `tests/test_layout_*.py`. |
| `tests/test_layout_two_up.py` | same. |

So **zero new components** beyond the slice — the scope gate's trigger (a diff growing ≥2
components beyond its slice, or covering a ready sibling's `Touches`) is **not** met. The large
overlap with CARD-225, CARD-226 and CARD-227 is not poaching: those cards were serialized
behind this one by design at dispatch, for exactly these hotspots.

### ⚑ Architect station: AC-252 retired, AC-378 added, AC-379 owed, EC-022's scope corrected

The implementation agent reported that **AC-252** is falsified by this card and that nothing
was owed at the architect station for it, and marked its test `xfail(strict=True)` rather than
editing `meta/architecture/**` from a worktree. Both calls were right. Settled on main with
**0 validator errors**; `requirements.yml` and `trace.yml` both amended.

- **AC-252 RETIRED.** It is the *same* retired claim as AC-190 — the fixed top edge — seen
  from the two-up page. **The cause is recorded, not just the retirement:** the 2026-10-17
  propagation pass retired AC-190 and restated EC-022 under FR-032 but never reached AC-252,
  because AC-252 lives under **FR-040**. A propagation pass that follows one requirement's
  clause cannot see the same claim restated under another requirement, and this is the second
  time on this board that a criterion survived a pass that should have taken it (the first was
  AC-244's off-by-one, which CARD-222's deferral was hiding).
  It also **cannot be rescued by CARD-226 floating the upper slot**: a slot's spare is not a
  page's spare, so 42% of each still lands on different rows. The claim is **wrong, not merely
  early** — which is why it is retired rather than deferred.
- **AC-378 added** — the truth this card produces: the single page floats at 42% of its area's
  spare while the upper slot is held at the foot of its own slot's band, so the two top rows
  **differ by design and the difference is asserted rather than tolerated**. Test
  `TestBookPdf_TwoUpUpperSlotDoesNotShareTheSinglePagesTopRow`, which replaces the xfail —
  **a card must not merge carrying a strict xfail that encodes a retired claim**, because a
  strict xfail is *green* in a suite, so the gate would pass while the test still asserts the
  old geometry. That is the CARD-172 shape exactly.
- **AC-379 declared OWED to CARD-226** — each slot floats at 42% of its *own* spare once the
  page is split. The agent's point 2 is now a criterion that card inherits instead of a
  sentence in a docstring.

**EC-022's scope was wrong, and the error was the orchestrator's, not the card's.** The
2026-10-17 restatement read "the gap between the top of the puzzle area and the top of the
drawing — **the upper puzzle's on a two-up page** — is 42% of that area's spare height". That
clause claimed the two-up half **one card early**: this card's own G-4 defers the slot split to
CARD-226, so no card in flight was ever going to deliver it. The tell was visible in the
registry and nobody read it — **none of EC-022's four instances (AC-189, AC-240, AC-366,
AC-367) was a two-up criterion**, so the clause stood with nothing instantiating it, which is
an EC clause with no instance. EC-022 now states the single-page rule as the live one,
attributes the two-up ratio to CARD-226 and AC-379, and names AC-378 as the control that the
two are deliberately different today. The clause is **kept and attributed, not dropped** — the
rule was right about where the design is going and wrong about when.

This is wave 44's recorded defect with the sign flipped. There, an architect amendment landing
mid-card invalidated an exemption a card had written correctly against the pre-amendment rule.
Here the amendment was written *ahead* of the card that implements it, so the card could only
satisfy it by doing a sibling's work. **Lesson for the next propagation pass: an amendment must
name the card that will make it true, and if that card is not the one in flight, the clause is
scoped to the future card from the moment it is written.**

**Three residues the card records rather than absorbing** (all three stated by the agent, all
three verified as genuine):

- A two-up page's **lower slot sits exactly ON the footer rule** — its heavy border and the
  hairline share a row. This is CARD-248's reserve, not this card's placement, and repacking
  two slots is CARD-226's job. `TestBookPuzzleFrame_GridClearsBothRules` **asserts the
  coincidence** rather than skipping the page, so it fails if it ever becomes a gap or an
  overlap. This is the obligation CARD-226 already carried on this board and it is now pinned
  by a test instead of a note.
- `folio_reserve_px` is still taken out of `compute_pair_layout`'s **fit**, deliberately, so
  FR-040's accept/refuse verdict and committed cell stay bit-for-bit CARD-204's (G-1). Centring
  has subsumed its *purpose* — both sides now carry half the spare — but removing it from the
  fit would move page counts and per-copy print cost. **This is the same reserve as the open
  backlog question from CARD-248's render** (18 pairs refuse only because of it, including the
  25×10). The two are now one question, and it is a pricing decision, not a geometry one.
- **Guide pages 1–2 scatter again** by the known ≤1 px rounding of `example_line_layout`'s
  borrowed pitch. CARD-204 recorded exactly this; eliminating it would give those helpers their
  own placement arithmetic, which G-3 forbids. The existing bound test passes unmodified.

**Independently confirmed, and worth recording because two agents found it separately:** this
card's agent and CARD-245's both discovered that `pyproject.toml:89` sets `addopts = "-q"`, so
adding `-q` yields `-qq` and pytest prints **no summary line at all**. Two independent
discoveries in one wave is why this is filed as a board-level `@ops` item rather than a note.
