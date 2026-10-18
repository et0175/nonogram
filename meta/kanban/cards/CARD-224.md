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

### [Review 1/3] Score: 7.5 — FAIL (threshold 8)

Report: `meta/review/20261018T082931Z-CARD-224-cycle1.yml` (copied to main before the worktree
goes). **No criticals.** Two importants, both verified by the orchestrator before the fix was
briefed. The reviewer's own summary is worth keeping: *"This is a careful card."*

**What the review tried hardest to break and could not** — recorded because this is the card
that reverses CARD-204, and the named trap has five regressions behind it:

- **The `_draw_solved_slot` trap is PROVABLY clean, not argued clean.** `book_pdf_generator.py`
  and `book_proof.py` are **AST-identical to `cc4430b` with docstrings normalised**, so the slot's
  return value and *both* its consumers (`solved_puzzle_page`, `_packed_answer_page`) are
  untouched. What moved underneath them was checked too: packed tiles do not move at all, and
  the full answer page's caption guard has 353 + 0.58·spare px of slack against a 73 px
  requirement, so no caption is newly dropped — and answer pages never call `_draw_page_frame`,
  so there is no footer rule for a lowered caption to cross.
- **G-1 is provable from the diff**: `compute_pair_layout`'s fit/re-fit block and accept/refuse
  path are untouched, and the verdict is taken **before** any changed line runs. Pairing cannot
  have moved.
- **`header_band`'s claim is real, with numbers**: read off `drawing_top` the band would be
  30.7 mm for a 15×15 and **52.8 mm** for a 10×10, whose centred type lands at row 311 against a
  header rule at row 289 — i.e. type inside the puzzle area. `band_bottom == drawing_top` for
  slots and tiles holds by construction.
- **Three of the four re-aimed tests were judged STRENGTHENED, not weakened** — the dimension I
  briefed as the highest-risk area in the diff. Two moved to unequal-margin books and now assert
  *every* drawing-carrying page and the *magnitude* of the offset, which the old versions could
  not. The third genuinely cannot carry the signal in the drawing any more and reads parity off
  the footer's 2 cm QR block instead, with an explicit assertion that the drawing's side gaps are
  now equal — documenting why the old signal is gone rather than quietly dropping it.
- **7 of 8 mutants died**, including `GRID_SPARE_ABOVE` → 50/100, centring → flush on both the
  page and the slot, `band_bottom` → `ys[0]`, the degraded branch, `vertical_bound` → `"ratio"`,
  and `_puzzle_area_px` dropping the footer strip.

#### ⚑ F-001 (important) — the clearance term's guarantee is not the guarantee it buys

`src/nonogram/export/layout.py:2527`. **Arithmetic confirmed by the orchestrator.** The guard is
`spare < 2 * clearance`, but only `GRID_SPARE_ABOVE` (**0.42**) of the spare lands *above* the
drawing. So passing the guard yields `gap_above >= 0.84 * clearance` — **less than the single
clearance it exists to buy.** It survives today only because `clearance` is a pixel more generous
than the real need, and `0.84 * (need + 1) >= need` holds only while `need <= 5.25`.

- **Measured margin is sub-pixel**: 0.555 px at a 200 mm trim, **0.659 px** on Book 1 at 39×35
  with maximal clue depths. AC-3's claim is that the clearance makes this "arithmetic and not
  luck"; at 0.555 px it is luck.
- **It breaks outright at a 14 px heavy rule.** `PageSpec(cell_cap=…)` is a public COMP-007 field
  with **no upper bound**; at `cell_cap=18.0 mm` there are **126 (trim, extent) pairs** that put
  ratio-branch ink *on* the header rule. **Not a live print defect** — no `PrintProfile` reaches
  it (BOOK1 is 7.5 mm, `comfort_cap_mm` maxes at 9.0) — so it is a false *claim* plus an uncovered
  line, and it is briefed that way rather than as an emergency.
- **The threshold has no test, and the two oracles the docstring NAMES cannot see it.** The
  mutant `spare < 2 * clearance` → `spare < clearance` **survived all four selections**.
  `test_book_pdf_geometry.py:166`'s `Sheet.drawing_top_mm` deliberately accepts **both** candidate
  rows inside `CLEARANCE_WINDOW_MM = 2.0 mm` (**23.6 px**) — *wider* than the implementation's own
  12 px threshold — and `test_book_puzzle_frame.py`'s `_expected_top_mm` uses `spare <= 0`. So the
  docstring cites as its boundary proof two oracles that are structurally incapable of it. That is
  the ADR-0039/R1 failure in its most expensive form: not a missing control, but a **named** one
  that cannot fail.

#### ⚑ F-002 (important) — AC-287's class became three identities, and names a survivor nobody wrote

`tests/test_book_pdf.py:664-760`. On the amended profile `gutter == outside`, so
`_expected_left_mm(right_hand=True)` and `(right_hand=False)` return the **identical** number, and
all three parity tests became identities. One is **inverted relative to its own name**:
`test_it_is_not_the_left_hand_page_a_miscount_would_give_it` went from
`abs(left_mm - left_hand) > EDGE_TOLERANCE_MM` to `< EDGE_TOLERANCE_MM` — it now asserts the
drawing **is** where the miscount would put it. Revert the interior-page-1 offset so the first
puzzle page counts as EVEN — *the exact miscount the class is named for* — and every test still
passes.

**The honest half is recorded too, because it changes what the fix is.** This was not done
silently: the docstring explains the identity and the code asserts it explicitly
(`assert abs(GUTTER_MM - OUTSIDE_MM) < 1e-9`). The defect is that the docstring then says *"The
page's parity is therefore asserted where it is still visible: the usable area's own edges"* —
**and that replacement is not written anywhere in the class.** A stated survivor that does not
exist is worse than an admitted gap, because it stops the next reader looking. And the card got
this right **twice** in the same diff, by moving the sibling tests to unequal-margin books.

#### F-004 and F-005 are the orchestrator's, not the card's

`test_book_pdf_geometry.py:674` still claims AC-252 "still asserts", is "owed at the architect
station", and that a "strict xfail carries it" — all three stale. `test_layout_two_up.py:9` and
`:197` still name a class renamed at `:183`. **`e1cbb35` retargeted the class NAME on that very
line and left the claims around it standing** — an incomplete pass of exactly the kind it existed
to clear. The fix brief says to sweep for the retired name and the xfail rather than fix only the
lines listed, because a list of instances is how the first pass missed these.

**Minors routed into the fix cycle:** F-003 (AC-4's depth guard is **vacuous** — `_area_ink_box`
crops at `round(area_bottom * PX_PER_MM)` so `ink_bottom` saturates at 1396 while the real drawing
bottom is 1749 px), F-006 (`ParityNeverMovesTopEdge`'s parity *premise* was replaced by its own
negation), F-007 (AC-252's **named survivor** promises "112 px … not a tolerance" and asserts only
`>`), F-008 (an undocumented third `vertical_bound` case where the area *does* hold the drawing yet
the page reports `"footer"`, whose footer-group agreement holds only because `2*clearance` is
smaller than the band's lift — **a `band_mm` coupling nothing records**), F-009 (the proof baseline
has no unmoved digest as its own control, unlike the book baseline), F-010..F-012 (spliced and
stale docstrings), F-013 (the card's own notes still claim the xfail exists and AC-252 is owed, and
**never mention the clearance term at all** — the one mechanism AC-3's whole claim rests on).

**Declared out of scope for the fix:** AC-3's text says "every grid size the book admits and every
trim" while the sweep covers 10..30 on four sheets, and the reviewer's worst-margin geometry is
outside that range. The **claim** is to be narrowed to what is swept, with the gap noted — not the
corpus grown. Growing a corpus to meet a sentence is how a cheap card becomes an expensive one.

### [Fix 1/3] both importants closed; the clearance term now tests the quantity its claim is about

Commit `85b6e45` — 8 files, +681/−87.

**Three claims verified by the orchestrator rather than taken on report:**

1. **`book_baseline_card224.json` is NOT in the commit**, so no book fixture was re-recorded;
   `proof_baseline_card224.json` is **+39/−0** — the new control block only, formatting preserved.
   G-5 holds without a re-recording, which is the right outcome for a cycle that was supposed to
   fix a *claim*.
2. **The new condition** is `gap_above = GRID_SPARE_ABOVE * spare; gap_below = spare - gap_above;
   if gap_above < clearance or gap_below < clearance`. `gap_below` is spelled as the subtraction
   rather than `(1 - GRID_SPARE_ABOVE) * spare` — identical in exact `Fraction` arithmetic, and it
   keeps "the two gaps sum to the spare" true **by construction**. The binding threshold becomes
   `clearance / 0.42` = **2.381** clearances (14.286 px at Book 1's cell), not 2.
3. **`book_pdf_generator.py` and `book_proof.py` are STILL AST-identical to `cc4430b` with
   docstrings normalised.** I verified this with my own AST comparison, stripping docstrings from
   both trees and diffing `ast.dump` — not with the agent's script. So after four commits the
   five-regression `_draw_solved_slot` trap is still **provably** clean, and that is the single
   most reassuring fact about this card.

**The headline result: cycle 1's surviving mutant now dies.** `spare < clearance` → `1 failed`.
So do the halved form, the pre-fix `spare < 2 * clearance`, `spare <= 0`, dropping the
clearance's `+ 1`, and the degraded branch. The new test walks a trim height in **0.05 mm steps**
(41 specs over 2 mm), asserts **exactly one verdict flip**, derives the clearance **inside the
test** from rule weights written out as points rather than importing the constant, and asserts
the case immediately below the boundary has a **positive** spare — which is precisely what a
`spare <= 0` oracle cannot say and why cycle 1's named oracles could not see the boundary.

**`cell_cap = 18 mm`: the claim is now true rather than bounded.** 0 violations under the new
condition where the retired one had some, and the arithmetic is unconditional — `clearance >=
thick/2 + furniture/2 + 1` and `gap_above >= clearance`, so the ink clears for **every** rule
weight after `_boundaries`' single half-pixel rounding. The docstrings that named two oracles
incapable of seeing the boundary are corrected, and both now point at the new test.

**F-002's miscount is caught again, and the red-check is recorded**: flipping `_parity` to
`(page_number + 1) % 2` — the cover rejoining the numbering, the exact miscount the class is
named for — gives **3 failed, 3 passed** where before the fix *all* passed. Book 1's identity
moved to its own test, where it is the **subject** rather than the evidence. `book_page_spec.py`
was restored and is not in the commit.

#### The geometry this cycle moved, stated as a number and not as a reassurance

**No stored page moves** — 0 of 33 baseline placements, 0 of 9 proof sheets. Across the whole
admissible space, **28 of 55,140** placements change: spare 12.41–14.14 px, each drawing moving
**down 12–13 px (1.0–1.1 mm)** from the 42% row onto the band's foot, and **all 28 omit their
footer group** (`qr_slot(...) is None`, 0 exceptions) — so none of them gains a rule to cross,
which is the only way this change could have created the defect it exists to prevent.

#### Three corrections the fix makes to the review's figures, and one addition that matters more

The corrections are all in the review's **numbers**, not its findings — the findings stood.

- **F-007's "112 px" is 113 px.** The review repeated the docstring's own 112 without challenging
  it, and asserting 112 would have been **red**. Measured on `test_layout_two_up.py`'s own
  `BOOK1_ODD` (which stores `top_mm=9.525` — this module's profile, *not* CON-018 as amended):
  single page 367, upper slot 254, gap **113** px at both parities. Now pinned *and* derived from
  `interior_frame`'s rule rows, so the figure is checked two ways instead of restated. **A review
  that inherits a figure from the docstring it is auditing is auditing nothing** — that is the
  transferable lesson, and it is the same shape as the orchestrator's own CARD-248 trim error.
- **F-008's "8.1 mm" is the `qr_slot` bound, not the sweep's.** The two predicates turn on
  different quantities: the sweep's includes the drawing's 3 px heavy-rule overhang, `qr_slot`'s
  does not. Retired threshold: 6.1 mm (sweep) / 8.13 mm (`qr_slot`); new threshold: 7.65 mm /
  **9.68 mm**. The binding one is `qr_slot`'s. **And the fix narrows this margin itself** — from
  5.7 px of headroom to **3.4 px** (17.72 px lift against a 14.29 px threshold) — which is why it
  is pinned by an assertion rather than only documented. Flagged for cycle 2 to judge.
- **The "126 (trim, extent) pairs" count was not reproduced**; a coarser scan found 4 violations
  under the retired condition. The fix says it does not doubt the finer sweep and reports the 4
  only so it is not read as a contradiction. Honest, and the direction is what mattered.

**The addition is the one worth keeping.** The AC-3 sweep's `_clears` predicate compares
`ink_top_mm > area_top` — against the rule's **row**, not its ink extent — so **the sweep could
not have detected cycle 1's sub-pixel margins in either direction.** Cycle 1 measured 0.555 px
against the rule's *ink*; that measurement was never in the sweep's reach. So the 484-case sweep
is weaker than cycle 1's own numbers implied, and the new threshold test — which compares against
each rule's outermost ink row — is strictly stronger than it. The fix deliberately left `_clears`
alone, on the grounds that tightening it is a second geometry claim this cycle does not need.
That is the right call and it is recorded as a residue rather than absorbed.

**Also fixed:** F-003 (AC-4's premise now asserts *that the crop saturates*, so the reason is in
the test, then measures depth off the layout with a 25 mm floor against a real ~30 mm), F-006 (a
real parity premise from the footer QR block at each end), F-008 (case (iii) named with its
`band_mm` coupling and pinned), F-009 (`unmoved_control_page_px`, checked against both the
recorder's pages and trim arithmetic restated in the test, so a recorder that changed its DPI or
its orientation fails there while the digests would only say "everything moved"),
F-010..F-013, and **F-004/F-005 — the orchestrator's own incomplete pass** — with a sweep for
`AC-252`, `xfail`, `twice over`, `2 * clearance` and both retired class names across `src/`,
`tests/` and `docs/` rather than a fix of the listed lines.

**The fix also found a logic error in the docstring it was extending**: it claimed the ratio is
refused because it "would put ink further past the footer rule than the alternative does", which
is **false for case (iii)** — there the band's foot is the *lower* row and is taken anyway, to
keep the **header** rule clean. Now stated as the trade it actually is.

### [Review 2/3] Score: 8.5 — PASS (threshold 8, improvement +1.0 against a 0.5 floor)

Report: `meta/review/20261018T121230Z-CARD-224-cycle2.yml`. Both thresholds met, so the card is
**cleared to merge on score**. One new important, and a third cycle is being run anyway — the
reason is below, and it is the same judgment as on CARD-245: a score that passes does not settle
whether something should merge.

**F-001 closed in substance, verified three ways none of which was a re-run of the fix's own
script:** zero violations of either rule's ink across **11,028 placements per parity** on Book 1
(extents 5..40 × 5..40, every clue depth), with the worst drawing-ink-to-header-ink margin now
**3 px** against cycle 1's **0.659 px**; at the `cell_cap = 18.0` class cycle 1 named, **8**
violating (trim, extent) pairs under the retired condition and **0** under the shipped one; and
cycle 1's surviving mutant M5 is dead along with three others. "Exactly one flip" was judged
non-degenerate on its merits — the straddle grid is width-bound so the drawing's height is
constant across the 41 trim heights, spare is strictly monotone, and both verdicts are asserted
to occur with ≥ 15 cases each.

**F-002 closed, and the red-check was reproduced independently rather than taken on report:**
post-fix `3 failed, 3 passed`; **pre-fix, the same mutant gave `7 passed`** — every test in both
re-aimed classes survived the miscount before this fix. F-003, F-006, F-007, F-008 and F-009 all
closed with their controls shown to bite. **Nothing is covered-in-name-only any more**; both of
cycle 1's entries are gone and no vacuous control survives.

**All three of the fix cycle's corrections to cycle 1's figures were judged right**, including
that cycle 1's "112 px" was two errors at once — it was the *float* (0.42 × spare = 112.14 px),
not the inter-row gap, and it was computed on a profile that module does not use. The lesson is
recorded as a standing one: **a review that inherits a figure from the docstring it is auditing
is auditing nothing.** The "126 pairs" figure is explicitly **not carried forward** — three
scans produced 126, 8 and 4 over three unpublished search spaces; the direction is the fact.

#### ⚑ F2-001 (important, new) — the fix created a defect class that did not exist before it

**I reproduced this myself, and my numbers match the review's row-for-row.** On a 160 mm trim
with a 23×9 grid behind depth-5 clue gutters:

| `band_mm` | `vertical_bound` | `drawing_top` | `drawing_bottom` | ink | `footer_rule.y` | group drawn |
|---|---|---|---|---|---|---|
| 8.5 | ratio | 261 | 1386 | 1389 | 1396 | yes — clear |
| **9.0** | **footer** | **271** | **1396** | **1399** | **1396** | **yes — ink 3 rows past a DRAWN rule** |
| 9.676 | footer | 279 | 1404 | 1407 | 1396 | no — omitted, nothing to cross |
| 12.0 (BOOK1) | footer | 307 | 1432 | 1435 | 1396 | no — clear |

So the framing on the card was wrong, and that matters more than the count: this is **not** a
"narrowed margin". The flip point **moved outward** from 8.128 mm to **9.676 mm**, and the newly
crossed strip is **populated** — 17 defective pages at `band_mm = 9.0` and 2 at 8.5, against
**zero** for the retired condition. Below ~8.13 mm the class is pre-existing and not this card's.

Two consequences, and the second is why it cannot be left as a note:

- `_draw_page_frame`'s *"they agree by construction, which is what makes 'no drawing ink crosses
  a rule that is drawn' true of every page"* is now **false** below 9.68 mm. What makes them
  agree is the value of a `PrintProfile` field. The coupling sentence was added **next to**
  "by construction" without striking it.
- **Nothing can catch it.** The new coupling test asserts `lift > threshold` on one sheet at the
  *test module's own* `BAND_MM = 12.0`, not `BOOK1_PROFILE.band_mm`; all four AC-3 sweep sheets
  are at 12 mm; and the only module that varies `band_mm` asserts `drawing_top`'s row and never
  `qr_slot`. Lowering the profile to 9 mm would red **exactly one** test — the one pinning the
  constant — and it says nothing about the footer rule.

**Why it is being fixed rather than recorded.** It is unreachable through the only stored
`PrintProfile` — but **that is the same reachability status the fix used to justify correcting
F-001 in the first place**, so declining it on those grounds would be incoherent. And the
scenario is ordinary: the owner shallows the title band from 12 mm to 9 mm on a small trim, and
some pages print a footer hairline with the grid's heavy border stroked three rows past it. Net
the cycle is still a clear improvement — it trades an unreachable hole for a larger unreachable
one and buys a **4.5×** real-margin gain in the geometry that actually prints — but a card does
not merge having *created* a class it could have closed.

#### The two claims the review graded as "true but near-vacuous", which is the right grade

- **"No stored page moves" is true and proves little.** Enumerated through the real recorders:
  the baseline book makes **33** placement calls, the proof recording **81** (9 per trim, not 9
  total), and **0 of 114** differ. But all 114 are in the `ratio` branch, the nearest **19×**
  the threshold clear, so the claim would have held for almost any threshold the fix could have
  picked — and **the two fixtures give the degraded branch zero coverage.** A fixture set that
  cannot see the branch a change is about is not evidence about that change.
- **"All 28 omit their footer group" is exact, 0 exceptions** — reproduced to the placement, with
  `drawing_bottom` exceeding `area_bottom` by 4–5 px on all 28, which is *why* the renderer
  refuses the group. One framing caveat: 28 is the count for those five sheets, **not a bound** —
  a 216×180 mm sheet alone yields 90, all still with the group omitted.

**Minors routed into the third cycle:** F2-002 (the docstring rewritten *this cycle specifically
to state its own corpus honestly* states it **three ways and none is true** — 484 claimed, **968**
actually run, "441" in the same paragraph), F2-003 (`_clears`'s row-vs-ink blind spot is
undocumented and **actively contradicted** by the two docstrings around it), F2-004
(`layout.py:1567` states the retired fixed top edge **in production prose, in the present tense**,
as the live rationale for the very constant this card's `band_mm` coupling is built on), F2-005,
F2-006 (two surviving mutants are **provably equivalent** — `gap_below` can never bind at a 42/58
split — so the docstring must stop presenting both disjuncts as load-bearing; a third, `<` → `<=`,
**is** a real gap), F2-007, F2-008.

**F2-009 is the orchestrator's to fix at the merge, and it is sharper than reported.**
`trace.yml:1713` names `TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage`, which this branch
deletes as a class. I checked: the name survives in `tests/test_book_pdf.py` **only as prose**
(two docstring references recording what replaced what), so **a name-grep trace lens would
falsely pass** — the dangling row would not be caught by the check that exists to catch it. I
also over-called this at first as two dangling names; the property test
`PropertyTest_BookPdf_PortraitWithFixedTopEdgeForEveryExtent` **does** survive, as
`test_PropertyTest_…`, so EC-022 keeps its control. Registry amendment owed at the merge, not
now — removing the row while main still defines the class would make main the inconsistent one.
