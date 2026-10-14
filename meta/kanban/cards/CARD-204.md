
# CARD-204: Puzzle and two-up pages drop FR-032's centred placement for right-alignment, and gain a 2x2cm QR-code slot linking to the (not-yet-public) solver

**Status:** blocked
**Priority:** P2
**Category:** feature
**Estimate:** 2.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/204-puzzle-right-align-qr
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-CARD-204
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 3: "Puzzles - please make them right-aligned and add a small icon for qr code (2*2 cm) with the link for the solver. It can be on the left or on the bottom depending on how the Puzzles are placed"); owner clarification 2026-10-08 via AskUserQuestion — "right-aligned" means a full reversal of FR-032's centred placement (not a narrower QR-icon-only adjustment), and the QR code should be drafted now with a placeholder/TODO link, wired to a real public solver URL once one exists.
**Idea:** —
**Wave:** 37
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/property/test_book_layout.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_two_up.py, tests/property/test_book_workflow.py, tests/property/test_book_export_interior.py, tests/test_answer_page_layout.py, tests/test_book_pdf.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_two_up.py, tests/test_book_puzzle_frame.py, tests/test_book_solved_page.py, tests/test_layout_answer_tiles.py, tests/test_layout_two_up.py, tests/test_export_pdf.py, tests/test_export_image.py, tests/fixtures/make_fixtures.py, pyproject.toml (only if the owner approves a new runtime dependency — see "What to implement" step 2)
**Review score:** 8.5/10 (cycle 4); cycle 5 on Fix 7 alone = **6.5/10, 1 CRITICAL** — not mergeable; family-regression escalation to the owner
**Started:** 2026-10-10T05:08:27Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** escalated — implementation: cycle-5 CRITICAL (a clamped packed caption overprints the folio on a standard KDP trim) plus the fifth family regression in one mechanism; owner decision requested on narrow fix vs closing the family

## What to implement

**Both mechanism-level decisions are now resolved (2026-10-10), via rendered
side-by-side samples (`~/Documents/nonogram-reviews/CARD-204/`, 8 PNGs: current-
centered / reading-a / reading-b / reading-c, each an odd+even page pair of the
same puzzle on Book 1's trim, produced by monkeypatching `compute_layout`'s
centring formula per reading — no source file touched for the render pass) plus a
direct AskUserQuestion for the QR policy:**

1. **Alignment reading: (b), mirrored by parity — CONFIRMED.** Flush right on odd
   (right-hand) pages, flush left on even (left-hand) pages — the geometric mirror
   of today's centering. The renders showed reading (a) visibly jamming the grid
   against the spine-side margin on every even page (confirmed numerically: anchor
   lands exactly at `usable_right` for an even page, which is the gutter side) —
   confirming the risk this card's own draft flagged. Reading (b) is the only one
   where the anchor side itself changes between facing pages, and that is the
   owner-accepted tradeoff.
2. **QR code: placeholder now, real QR later — CONFIRMED.** Draw a visibly-fake
   QR-shaped icon reserving the 2x2cm layout slot; no new runtime dependency, no
   ADR-0006 revision this card. A follow-up card swaps in real QR pixels once a
   dependency is chosen and the public solver exists to link to.

Implement per these two confirmed decisions — see "What to implement" step 1 for
reading (b)'s exact formula and step 2 for the placeholder QR icon's spec.

**Coordination note:** CARD-203 (solved-page caption reposition) also touches
`tests/test_book_solved_page.py` and has already implemented+committed in its own
worktree (not yet merged as of this card's start) — expect that file to carry
CARD-203's changes once it merges; this card's own edits to it should be additive/
independent (different test classes), but check for rebase conflicts if CARD-203
merges first.

**Current behaviour (verified by reading the code).**

- FR-032 (`meta/architecture/requirements.yml`, amended 2026-09-22 (c), BK-1 placement,
  owner decision) is the explicit, named rule this card reverses: *"Horizontally the
  drawing is centred across the usable width of its page — between the gutter and
  outside margins as mirrored for the page's parity (FR-030) ... so its left edge moves
  with the parity and its top edge does not."* This is not an accidental default — it
  was itself an owner decision, amended once already, with its own ACs (AC-274..AC-276)
  and property test (EC-032). This card's own job is to replace that statement's
  horizontal-placement clause, not merely to tweak a rendering detail under it.
- The centring is implemented in **exactly two places**, both inside
  `src/nonogram/export/layout.py`, both the *same one-line formula* applied to
  different call shapes (not a cross-module duplication — CLAUDE.md's
  reimplement-rather-than-import-across rule is about capability-module boundaries;
  this is one file, two call sites for two page kinds):
  1. `compute_layout`'s placed-page branch, line 1576:
     `left = usable_left_px + max(spare, Fraction(0)) / 2` — where `spare =
     usable_width_px - drawing_columns * pitch` (line 1575). The comment immediately
     above it (lines 1572-1574) already documents the one existing exception: *"Only
     when the MIN_CELL_MM floor has made the drawing wider than the usable area does it
     anchor at the usable area's left edge instead, overflowing to the right"* — i.e.
     `max(spare, Fraction(0))` already collapses to 0 and `left` to `usable_left_px`
     when `spare` is negative (floor overflow). This degenerate case needs its own
     re-reasoning under right-alignment (see step 1 below).
  2. `_slot_layout` (the two-up page's per-slot layout, line 1869-onwards), line 1901:
     the identical formula, `left = usable_left_px + max(spare, Fraction(0)) / 2`, fed
     a cell and pitch already chosen by the pairing walk rather than fitted locally.
  Both produce a `PagePlacement` (`usable_left`/`usable_right`/`drawing_left`/
  `drawing_right`) that every renderer downstream (`_stroke_drawing`, `_write_clues`,
  `_set_band`, `solved_puzzle_page`'s caption, CARD-203's forthcoming right-aligned
  caption) reads positions from — change the two `left = ...` lines and every
  consumer repositions itself automatically; **no renderer computes its own x
  position independently of `Placement`** (confirmed by grep: every `draw.*` call in
  `book_pdf_generator.py` reads `layout.*`/`placement.*` fields, never re-derives an
  x coordinate from `usable_width_px` itself).
- **The gutter mirrors by parity, and this is the actual hard sub-question** (see
  `PageSpec.left_margin_mm`/`right_margin_mm`, `export/layout.py` lines 531-539,
  already read in full): *"The gutter margin is on the binding side: left on a
  right-hand (ODD) page, right on a left-hand (EVEN) page."* So `usable_right` is **not**
  consistently "the outer edge" or "the spine edge" across parities — on an ODD page
  `usable_right` is the outer margin; on an EVEN page `usable_right` is the gutter
  (spine) margin. A literal, parity-blind "always hug `usable_right`" reading would
  jam the drawing against the spine on every left-hand page — exactly the outcome
  FR-030's mirrored-margins rule exists to prevent for readability/binding reasons.
  This is the single biggest open question in this card (see "Owner decisions still
  needed," item 1).
- **No QR-code generation exists anywhere in this codebase.** Grepped
  `src/nonogram/**` and `pyproject.toml` for `qr`/`QR`/`qrcode` — zero hits beyond this
  card's own drafting. The project's dependency baseline is closed to exactly stdlib +
  Pillow + NumPy (ADR-0006/R1, `pyproject.toml`'s `dependencies = ["Pillow>=10.0",
  "numpy>=1.24"]`, CLAUDE.md: *"adding a third-party runtime dependency requires
  revisiting that decision, not just editing pyproject.toml"*). A real, scannable QR
  code is not something this card can reasonably hand-roll from raw pixels (QR
  encoding needs Reed-Solomon error correction, version/format tables, mask-pattern
  scoring — a correct implementation is itself a small subsystem, and a broken one
  produces an icon that LOOKS like a QR code but does not scan, which is worse than
  not shipping one). This is the second open question (see item 2 below).
- **No public solver exists to link to.** `meta/kanban/backlog.md`'s "Features and UX
  (not carded yet)" section already names this gap in its own words: *"Online solver,
  public phase: hosting, the URL namespace for per-puzzle QR codes, and the persisted
  puzzle-number mapping (raw-requirements Delta 2026-09-24 (a)); the admin POC ships
  the solution inside the page, which a public solver must not."* CON-021 (confirmed by
  reading its full entry) restates this precisely: interactive play exists **only**
  behind the admin panel's door (CON-015 loopback bind / CON-016 credentialed-hostname
  mode), the admin POC's page ships the puzzle's *solution* to the browser (acceptable
  there only because the page is admin-only), and *"a public player must not"* do
  either of those things. The owner's own clarification already settled this at the
  policy level: draft the QR icon's layout slot now, with a placeholder/TODO URL, and
  wire the real link once the public-solver project (an un-carded idea today) exists.
  This card must not accidentally point the QR at the admin player's URL (that would
  either 404 for a public reader with no credential, or — far worse — if the admin
  panel's door is ever opened wider than intended, expose the solution-shipping admin
  page to the public; CON-021/ADR-0038/R6 forbid this outright). The placeholder must
  be visibly inert (see AC-8).

## Owner decisions (RESOLVED 2026-10-10 — see confirmation note at the top of "What to implement")

1. **What "right" means across the mirrored gutter.** Three readings, each internally
   consistent but materially different on the page:
   - (a) **Hug `usable_right` on every page, both parities** (the literal, simplest
     reading of "right-aligned," matching this card's one-line-formula-change
     simplicity) — but this jams the drawing against the spine on every EVEN
     (left-hand) page, which FR-030's own mirrored-margin rationale exists to avoid.
   - (b) **Hug the *outer* margin, mirrored by parity** (the geometric mirror-image of
     today's rule: anchor the drawing at the far side from the gutter, flush right on
     ODD pages, flush left on EVEN pages) — the architecturally consistent choice
     given FR-030, but it means the grid's "right-aligned" edge physically **flips
     sides** between two facing pages of an open book spread, which may not be the
     visual the owner pictured when writing "right-aligned."
   - (c) **Hug the physical right edge of the trimmed page itself**, ignoring
     parity/gutter mirroring for this placement decision specifically (gutter widening
     still reserves its own margin band, but the drawing anchors at the page's own
     physical right edge rather than at `usable_right`) — closest to "a reader opens
     the book and the puzzle is always on the right of its own page," but it is a
     **new** placement concept FR-030/FR-032 do not currently describe (today margins
     mirror but placement never reads "this page's physical side," only
     `usable_left`/`usable_right`, which already encode the mirroring) — this is more
     invasive than (a) or (b): it needs a new field or a parity-aware override, not a
     one-line formula edit.
   **Recommendation:** (b) — it is the only option that does not reintroduce a
   binding-adjacent grid on half the book's pages, and it is the smallest real change
   (same formula shape, `left = usable_left_px + max(spare, Fraction(0))` reversed in
   sign per parity, i.e. flush to whichever side `usable_right` names for that page).
   But this is the owner's call, not this card's to assume silently (CARD-198's own
   precedent: three owner-visible defaults were flagged, not guessed, before merge) —
   **render all three readings side by side on a short sample book before
   implementation begins**, the same way CARD-198 rendered old-vs-new before merge.
2. **Whether a new runtime dependency may be added for real QR generation.** Candidates
   exist (e.g. a small, pure-Python, dependency-free QR encoder) but picking one and
   adding it to `pyproject.toml`'s `dependencies` is explicitly an ADR-0006 revision
   per CLAUDE.md's own rule — outside a kanban card's authority to decide alone.
   Options, for the owner/architect station to choose between:
   - **(a) Add a small pure-Python QR-generation dependency** (no C extension, no
     transitive dependencies) and revise ADR-0006 alongside this card — the only path
     to a real, scannable code drawn at render time.
   - **(b) Draw a visibly fake/placeholder QR-shaped icon** (a generic grid-of-squares
     glyph, never claiming to scan, perhaps captioned "QR code — coming soon") so this
     card can ship its *layout slot* (the 2x2cm reserved space, its left-or-bottom
     position per page shape) without touching the dependency baseline at all, and a
     **follow-up card** swaps in real QR pixels once (1) a dependency decision is made
     and (2) the public solver exists to link to.
   **Recommendation:** (b) for *this* card, matching the owner's own "draft the QR
   now, wire the link later" answer at the pixel level too, not just the URL level —
   ship the reserved layout slot and a clearly-a-placeholder icon, defer both the real
   QR encoding and the real URL to the follow-up once the public solver project is
   carded. This also avoids drawing a technically-well-formed-looking QR code that
   silently encodes a dead admin-only URL, which a curious reader might actually try
   to scan.

## What to implement (confirmed — reading (b) + placeholder QR)

1. **`export/layout.py`'s two centring call sites.** Per the owner's confirmed reading
   (item 1 above), rewrite the `left = usable_left_px + max(spare, Fraction(0)) / 2`
   line in both `compute_layout` (line 1576) and `_slot_layout` (line 1901) to anchor
   at the chosen edge instead of the midpoint. Re-derive the MIN_CELL_MM floor-overflow
   case (today: centring degrades to left-anchored-overflowing-right when `spare < 0`;
   under right-alignment the equivalent degenerate case needs its own, explicitly
   reasoned direction — don't assume it falls out of the formula unchanged).
2. **The QR-code reserved slot.** A `2x2 cm` icon area (`cm` -> `mm` -> device px via
   this module's own `_mm_to_px`/`_exact_px`, not a new unit conversion), placed per
   the doc's own words — *"on the left or on the bottom depending on how the Puzzles
   are placed"* — i.e. this card must derive its own rule for which side, consistent
   with wherever the drawing ends up anchored (e.g. if the drawing hugs the right, an
   icon slot naturally reads well in the newly-freed left gutter margin; if a two-up
   page's slots leave no side margin, the bottom slack is the fallback — the same kind
   of slack-or-omit reasoning `solved_puzzle_page`'s caption already uses). Draw a
   placeholder glyph (option 2(b) above), not real QR pixels, with a clearly inert
   target (see AC-8).
3. **`book_pdf_generator.py`'s renderers** — confirm (not re-derive; the investigation
   above already established this) that no renderer needs its own edit beyond reading
   the now-repositioned `Placement` fields; the only genuinely new drawing code is the
   QR placeholder glyph itself (new helper, analogous to `_set_band`/`_write_clues` in
   shape: reads a `Placement`, draws within it, has no page-kind-specific logic beyond
   where its slot sits).
4. **Does this reach the answer section too?** CARD-197/198's `solved_puzzle_page`
   calls `compute_layout` the same way an unsolved puzzle page does (confirmed by
   CARD-198's own AC-9 — "the same cell, the same frame" — and this card's own reading
   of `solved_puzzle_page` step 1-2). A right-alignment change to `compute_layout`'s
   placed-page branch therefore repositions answer pages too, automatically, unless
   explicitly scoped out — the owner's doc separates "Puzzles" (item 3) from
   "Solutions" (item 4, CARD-202) as two different sections, but says nothing about
   whether the *answer* pages should also move. **Flag, don't silently decide**: either
   confirm answer pages right-align too (for visual consistency across the whole book,
   the simplest and this card's default reading), or special-case
   `solved_puzzle_page`/CARD-202's packed layout to keep centring — the latter is more
   code, not less, so absent an owner objection this card's default is "yes, the
   change is global, consistent with reusing one shared formula."

## Acceptance criteria

- **AC-1** (happy, single puzzle page): *Given* a book's puzzle page at any supported
  trim, *when* its layout is computed, *then* the drawing anchors at the owner-chosen
  edge (not the usable-width midpoint) and the previous centred-placement assertions in
  `tests/property/test_book_layout.py`/`test_book_pdf_geometry.py` are replaced by
  equivalent right-alignment assertions, never silently deleted.
  *test: PropertyTest_BookLayout_DrawingAnchorsAtTheChosenEdge*
- **AC-2** (happy, two-up page): *Given* a two-up page, *when* both slots are laid out,
  *then* each slot's drawing anchors the same way AC-1 pins for a single page, and the
  pair's shared band/rule geometry (INV-010) is otherwise unaffected.
  *test: PropertyTest_BookTwoUp_SlotsAnchorAtTheChosenEdge (in tests/property/test_book_two_up.py)*
- **AC-3** (boundary, MIN_CELL_MM floor overflow): *Given* a grid whose floor-enforced
  cell makes the drawing wider than the usable area, *when* its layout is computed,
  *then* the floor-overflow direction is the one this card's "What to implement" step 1
  re-derives (not an accidental inheritance of today's left-anchored-overflowing-right
  behaviour) and is asserted explicitly, not left to coincidence.
  *test: TestLayout_FloorOverflowDirectionUnderRightAlignment*
- **AC-4** (happy, mirrored parity): *Given* a right-hand (ODD) and a left-hand (EVEN)
  page of the same puzzle, *when* both are laid out, *then* the drawing's position
  relative to the gutter/outer margin follows the owner's confirmed reading (item 1) —
  consistently, not by accident of which margin happened to be wider.
  *test: PropertyTest_BookLayout_ParityMirroringHoldsUnderTheNewAnchor*
- **AC-5** (happy, QR slot placement): *Given* any puzzle page, *when* it is rendered,
  *then* a 2x2cm icon area is reserved at the side the owner's chosen rule names
  (left margin or bottom slack), never overlapping the grid, the band, or (on an answer
  page) the caption.
  *test: TestBookPdf_QrSlotReservedWithoutOverlap*
- **AC-6** (boundary, no room for the icon): *Given* a page shape where the chosen slot
  has insufficient slack for a 2x2cm icon (e.g. a near-floor two-up pair with no spare
  margin), *when* the page is rendered, *then* the icon is omitted rather than
  overlapping other content — the same omit-rather-than-overlap discipline
  `solved_puzzle_page`'s caption already uses.
  *test: TestBookPdf_QrSlotOmittedWhenNoRoomRatherThanOverlapping*
- **AC-7** (negative, byte-identity elsewhere) — **AMENDED at the decompose station,
  2026-10-14.** Original text: "*Given* any book, *when* every page that is not a
  puzzle/two-up/answer page (the guide, dividers) is compared against the pre-card
  baseline, *then* it is byte-identical — this card changes horizontal drawing placement
  and adds a QR slot only on pages that carry a drawing. *test:
  TestBookPdfMemory_NonDrawingPagesAreByteIdentical*". Two things were wrong with it, both
  found downstream rather than here: the AC/EC gate found the **guide pages are not
  byte-identical** (a bounded sub-pixel scatter — their worked examples borrow
  `compute_layout`'s placed branch, which this card rewrote), and Fix 7 found that the
  named test had silently **widened the AC to pages 11-13**, which this card does not
  touch and main's CARD-203 moves. Amended wording, per Fix 7's proposal (it is the
  better one — the original AC already excluded answer pages by its own text, so CARD-203
  never falsified its scope; the mis-attribution lived entirely in the test):
  - **AC-7a**: *Given* any book, *when* the TOC and every divider page — the pages that
    carry neither a drawing nor a caption — are compared against
    `book_baseline_card200.json`, *then* each is byte-identical. The three answer pages are
    outside this criterion: this card moves nothing on them and main's CARD-203 moves all
    three, so their byte-identity is owed to `book_baseline_card203.json` instead.
    *test: TestBookPdfMemory_NonDrawingPagesAreByteIdentical* (and
    `test_the_three_answer_pages_moved_under_card203_not_this_card`, which measures the
    attribution rather than asserting it)
  - **AC-7b** (the bound the original AC was missing; owner decision 2026-10-13, "bound it
    with a test, then merge"): *Given* any book, *when* guide pages 1-2 are compared
    against the pre-card baseline, *then* they are not required to be byte-identical, but
    the differing pixels are under 1% of the page and every one of them lies within 1 px
    of displacement — asserted, not described in prose.
    *test: TestBookPdfMemory_NonDrawingPagesAreByteIdentical::test_the_guide_pages_scatter_is_bounded_to_one_pixel_of_displacement*
- **AC-8** (negative, placeholder inertness): *Given* the QR slot's drawn glyph, *when*
  it is inspected, *then* it is visibly a placeholder (per the owner's confirmed
  option 2(b)) and encodes/links to nothing live — it must not be mistaken for a real,
  scannable code pointing at an admin-only or dead URL.
  *test: TestBookPdf_QrPlaceholderIsVisiblyNotARealCode*

## Guardrails

- G-1: `export/layout.py`'s vertical placement rule (the top edge fixed at
  `top margin + band` on every page and parity, FR-032's other clause) is unchanged —
  this card touches only the horizontal anchor.
- G-2: CARD-197/198's `solved_puzzle_page` drawing steps (fill, gray re-stroke between
  filled cells, clue digits, band, caption) are not edited beyond what automatically
  follows from `Placement`'s repositioned fields (step 4) — no new drawing logic added
  to that method by this card beyond the QR slot, which is itself a page-level
  addition, not a `solved_puzzle_page`-specific one.
- G-3: CON-021/ADR-0038/R6 (no public solver, no solution shipped outside the admin
  door) are not weakened — the QR placeholder must never carry a working link to the
  admin panel's player page.
- G-4: ADR-0006/R1 (closed dependency baseline) is not silently crossed — no
  `pyproject.toml` edit ships with this card unless the owner/architect station has
  explicitly approved a specific QR-generation dependency (item 2 of "Owner decisions
  still needed").
- G-5: **AMENDED at the decompose station, 2026-10-13 (owner decision).** Originally:
  "INV-010 (two-up pairing eligibility: same tier, adjacent, both fit at a shared cell)
  is untouched — this card repositions a pair's slots, it does not change which puzzles
  pair." The owner's 2026-10-12 "fixed universal reserve" decision supersedes the second
  clause: it accepts that the reserve participates in the pairing verdict, so this card
  DOES change which puzzles pair (~5% of otherwise-pairing pairs are refused, measured
  twice independently in cycle 4). The owner reaffirmed this on 2026-10-13 after being
  shown that cost, choosing "it stands — 4 digits". The guardrail's surviving, binding
  clause: INV-010's own structure is untouched — eligibility remains same tier, adjacent,
  both fit at one shared cell of at least 7.0 mm capped at 7.5, and the verdict remains a
  pure function of the pair's geometry plus ONE fixed compile-time constant (the same
  category as `TWO_UP_MIN_CELL_MM`). Nothing page-, book- or payload-derived may reach it
  — that half of the guardrail is what F-1/F-5/F-7 were about and it still holds.
  Amended here, never in the worktree: a guardrail is weakened only at this station.
- G-6: **AMENDED at the decompose station, 2026-10-14 (owner decision), second clause
  only.** SURVIVING and binding: FR-031's 4.8 mm floor check and NFR-006's
  orientation/cap logic are untouched — evidenced by the AC/EC gate (no diff hunk reaches
  `_placed_cell_mm`'s body, `MIN_CELL_MM`, `OrientationPolicy` or `cell_cap`;
  `test_book_floor.py` 77, the membership-floor property 7, the cell-size property 6, all
  green). SUPERSEDED: "this card changes where a drawing sits, never its size" is false of
  two-up pairs under Fix 4 — the fixed folio reserve re-fits the shared cell against a
  narrower usable width, so ~9% of pairs commit a smaller cell and ~5% are refused. That
  is the same owner-decided mechanism that superseded G-5's second clause (decided
  2026-10-12, reaffirmed 2026-10-13 with the measured cost in hand). Amended here, never
  in the worktree.
- G-6 (original text, retained for the record): FR-031's 4.8mm floor check and NFR-006's orientation/cap logic are untouched —
  this card changes where a drawing sits, never its size.

## Architecture context

- **FR:** FR-032 (this card is the one that formally reverses its horizontal-placement
  clause — the requirements-text edit itself is architect-station work, see "Not in
  this card" below), FR-030 (mirrored margins — the mechanism this card's anchor
  choice must respect), FR-031 (4.8mm floor, untouched), FR-040 (two-up pairing,
  untouched by pairing eligibility, touched by slot placement), FR-042/FR-198's
  successor state (answer pages, touched per step 4 unless scoped out).
- **ADR:** ADR-0006/R1 (dependency baseline — G-4), ADR-0036/R2 (layout functions
  place, nothing else does — this card's two one-line edits are exactly the kind of
  change ADR-0036/R2 anticipates living in `export/layout.py` alone).
- **CON:** CON-021 (public-solver prohibition — G-3), CON-020 (10pt floor — a QR
  placeholder is an icon, not text, so likely exempt like the clue digits, but confirm
  whether a caption/label beside it is subject to the floor if one is added).
- **Components:** COMP-007 (layout functions, the two edited call sites), COMP-009
  (`book_pdf_generator.py`, the new QR-slot renderer).
- **Trace:** meta/architecture/trace.yml — not updated by this card (no edit under
  `meta/`); revisit once the architect station amends FR-032's statement and adds
  whatever FR/CON covers the QR placeholder and the eventual public-solver link.

## Design context

- **Output:** every puzzle page, two-up page, and (pending step 4's confirmation)
  every solved answer page in the book's interior PDF.
- **Owner-visible defaults this card picks (need confirmation before implementation,
  not just before merge — this card is larger and riskier to redo than a typical
  owner-visible-default card):**
  - Which of the three "right" readings (item 1) is correct.
  - Real QR encoding now vs. a placeholder now + real QR later (item 2).
  - Whether answer pages right-align too (step 4).
- **Renders:** before any code is written, render a short sample book (a handful of
  puzzles, at least one two-up pair, at least one answer page) three ways — reading
  (a), (b), and (c) from item 1 — side by side, the same comparison discipline CARD-198
  used for its old-packed/new-solved renders, so the owner is judging real pixels, not
  a verbal description of "right-aligned."

## Worktree notes

- [Origin] Owner's Google Doc "Nonograms - Print layout1", 2026-10-08, item 3. Drafted
  directly (not through a sub-agent) after two AskUserQuestion rounds with the owner:
  (1) confirmed "right-aligned" means a full reversal of FR-032's centred placement,
  not a narrower QR-icon-only change; (2) confirmed the QR code should be drafted now
  with a placeholder/TODO link, wired to a real public solver once one exists (the
  public-solver project itself is still an un-carded backlog idea, see
  `meta/kanban/backlog.md`'s "Features and UX (not carded yet)" section).
- [Why `Revision pending: true`] Both of the owner's answers settled *policy*
  ("reverse it fully" / "placeholder now") without settling *mechanism* (which edge is
  "right" across the mirrored gutter; real QR vs. placeholder pixels). Drafting this
  card any further (a specific line-by-line diff, specific test rewrites) before those
  two mechanism-level calls are made would very likely mean redoing real work — this
  card is marked revision-pending exactly because of that risk, not because the
  investigation itself is incomplete.
- [Verified facts the implementer must not re-derive]
  - `export/layout.py`: the two centring call sites are `compute_layout` line 1576 and
    `_slot_layout` line 1901, both the identical formula
    `left = usable_left_px + max(spare, Fraction(0)) / 2`. `PageSpec.left_margin_mm`/
    `right_margin_mm` (lines 531-539) is where the gutter-mirrors-by-parity rule lives.
    No renderer in `book_pdf_generator.py` computes an x-position independently of a
    `Placement`'s fields (grepped clean).
  - No QR-generation code exists anywhere in `src/nonogram/**` (grepped clean) and the
    dependency baseline (`pyproject.toml`) is closed to Pillow + NumPy (ADR-0006/R1).
  - No public solver exists; CON-021 explicitly names the admin-only door
    (CON-015/CON-016) as the only place interactive play may live today, and
    `backlog.md` already carries "Online solver, public phase: hosting, the URL
    namespace for per-puzzle QR codes..." as an open, un-carded idea — this card's QR
    slot is deliberately decoupled from that project, not a dependency on it (the
    placeholder ships without waiting for it; only the *real* link waits).
  - Blast radius: grepped the test tree for `centred`/`centered`/`usable_width_px`/
    `spare` — about twenty files reference this geometry in some form (full list in
    Touches above is the ones most likely to assert the *exact* centred position
    pixel-for-pixel, found by a closer read of each; the broader grep hit list is wider
    and the implementer should re-grep rather than trust this list as exhaustive).
  - This is, by a wide margin, the single most invasive card drafted from this
    revision of the owner's doc — CARD-200/201/202/203 are additive or narrowly
    scoped; this one reverses a named, amended, tested architectural rule
    (FR-032/EC-032) across every page kind that draws a puzzle.
- [Not in this card] Formalising FR-032's requirements-text reversal (amending its
  statement, retiring/rewriting AC-274..AC-276 and EC-032), authoring whatever
  FR/CON covers the QR placeholder and (later) the real public-solver link, and
  `meta/architecture/trace.yml` — all architect-station `/forge:architect` delta work
  for after this card's mechanism-level decisions are made and, likely, after an
  initial implementation lands. This card edits nothing under `meta/` except its own
  file.
- [Not in this card, either] The public online solver itself (hosting, a public URL
  namespace, the persisted puzzle-number mapping) — a separate, not-yet-carded
  project this card's QR slot anticipates but does not build toward beyond leaving
  room for it.

- [Implementation, 2026-10-10] Both owner mechanism-level calls were taken as
  resolved for this pass, per the orchestrator's instruction: reading (b) (flush
  with the usable area's *outer* margin, mirrored by parity) for item 1, and
  option 2(b) (a drawn placeholder glyph, no real QR encoding, no dependency
  change) for item 2. Line numbers in the card's own "Verified facts" had already
  drifted (CARD-200/201/202/203 merges): `compute_layout`'s centring line is now
  1581 (not 1576) and `_slot_layout`'s is 2023 (not 1901) at the point this card
  branched; re-grepped rather than trusted, as the card itself warned.

  **STRUCTURE: the anchor formula has no `max(spare, 0)` clamp.** Reading (b) is
  implemented as `left = usable_left_px if parity is EVEN else usable_left_px +
  spare` in both `compute_layout` and `_slot_layout` — no clamp at all, unlike the
  centred formula it replaces. Re-derived, not inherited: pinning flush to the
  outer edge is algebraically exact whether `spare` is positive or negative, so
  the MIN_CELL_MM floor-overflow case needs no special branch — it falls out of
  the same formula, spilling toward the *gutter* margin on both parities (ink
  beyond the outer trim edge is cut away at the guillotine; ink in the gutter
  margin only encroaches on the binding allowance — the deliberately safer
  direction). AC-3's test (`test_TestLayout_FloorOverflowDirectionUnderRightAlignment`)
  pins this explicitly.

  **STRUCTURE: the QR icon's geometry is a COMP-007 function, not a renderer
  decision.** `export/layout.py` gains `QR_SLOT_MM` (20.0, the owner's 2x2cm),
  `QrSlot` (a plain box) and `qr_slot(layout) -> QrSlot | None` — the same
  "measured here, drawn by the renderer" split `header_band` already uses for
  the same reason (ADR-0036/R2). Rule, in order: (1) the gutter-side margin slot
  — flush with the usable area's gutter-side edge, top aligned with the
  drawing's own top — if it is at least 20mm wide and the drawing is at least
  20mm tall there; (2) failing that, the slack below the drawing, flush with the
  usable area's bottom *and* the gutter side (so it never reaches for the
  folio's own outer corner); (3) failing both, `None` (AC-6's omit-rather-than-
  overlap). The gutter side is *always* where the right-alignment change leaves
  slack (a direct, provable consequence of the flush formula having no clamp),
  which is why the icon's own rule can be purely geometric with no new
  "which side has room" heuristic.

  **STRUCTURE: the QR icon is drawn on Puzzle pages only, never on Solutions.**
  The owner's doc lists the QR icon under item 3 ("Puzzles") and says nothing
  about it under item 4 ("Solutions", CARD-202's own item). `qr_slot()` itself
  is page-kind-agnostic (it would compute a box for any placed `Layout`,
  including a solved one), but the actual drawing call is wired only into
  `export/png.py`'s `render_image` (reached by `_blank_page` via `render_pages`)
  and `book_pdf_generator.py`'s `_two_up_page` — never into `_draw_solved_slot`/
  `solved_puzzle_page` or `_packed_answer_page`. This is a scope decision, not a
  technical constraint; flagged here as the one place this card's own default
  ("if ambiguous, make it global, matching the shared-formula precedent step 4
  itself recommends for right-alignment") was *not* followed, because the doc's
  own item split gave an actual, specific textual signal the right-alignment
  question didn't have.

  **STRUCTURE: step 4 (does right-alignment reach the answer section) — yes,
  globally, confirmed.** `solved_puzzle_page` calls the same `compute_layout`
  an unsolved page at that position would, so it repositions automatically with
  no edit to that method (G-2 held). Measured directly on the baseline book:
  pages 7/9 (single puzzle pages) and page 5 (two-up) move; of the three
  answer pages, only page 13 (Snowflake's own full, unpacked page) *could* move
  by this mechanism, and on this specific book it happens not to (see the two
  discovered exceptions below) — pages 11/12 (CARD-202's packed answers) were
  never in scope for this clause at all (different, tile-local formula).

  **The QR placeholder glyph.** A 2px-bordered square around a plain 5x5
  alternating checkerboard (`(row + column) % 2 == 1`), reimplemented
  independently in `export/png.py` and `book_pdf_generator.py` (the project's
  own native-reimplementation convention for drawing primitives, matching
  `_stroke_drawing`'s precedent) — deliberately not a real QR module pattern
  (no finder squares, no encoded data, identical regardless of the puzzle or
  page it sits on) and containing no URL string anywhere (verified by direct
  source inspection in `tests/test_book_qr_slot.py`'s own AC-8 tests), so CON-021/
  G-3 cannot be weakened by it — there is nothing in the glyph that points
  anywhere.

  **Two discovered, narrow exceptions to byte-identity (AC-7), both measured, not
  guessed, documented in `tests/test_book_pdf_memory.py::TestBookPdfMemory_NonDrawingPagesAreByteIdentical`
  and in `tests/helpers/book_corpus.py`'s own history comment:**
  1. The two guide pages (1, 2) move by a small, sub-pixel rounding scatter
     (~15000 px of a 2550x3300 page — rule edges shifting at most 1 device
     pixel). `example_line_layout`/`guide_icon_layout` reuse `compute_layout`'s
     placed-page branch purely to borrow this book's own cell/rule sizing
     (ADR-0036/R2) — the diagrams themselves are cropped tight to their own ink
     and pasted at a fixed, card-independent position (`frame.left`), never at
     the layout's own `left` — but `_boundaries` rounds each grid boundary
     independently, and that rounding depends on the *absolute* anchor's
     fractional part, which this card's formula necessarily changes. This is
     the same shape of "page 1 moved for a reason unrelated to its own content"
     the baseline chain already absorbed twice (CARD-149, CARD-167) — flagged
     for the owner/architect, not treated as this card's to eliminate (doing so
     would give those two helpers their own placement arithmetic, which G-3
     forbids them).
  2. **CARD-200's page-number folio is now permanently omitted on every two-up
     page, on both parities, for every puzzle — not just a tight-fit one.**
     Under reading (b), `drawing_right == usable_right` exactly on every ODD
     (right-hand) page and `drawing_left == usable_left` exactly on every EVEN
     one, algebraically, regardless of the puzzle's own spare (see the
     no-clamp formula above). The lower two-up slot's vertical slack is *also*
     always zero (`PairLayout`'s own, pre-existing invariant). `_draw_folio`'s
     existing "omit rather than collide" check (CARD-200, review cycle 1/F-1)
     therefore now fires on every two-up page, deterministically — this is
     `_draw_folio` working exactly as designed, not a bug, but it is a real,
     visible, permanent loss of a shipped feature (the page number) on every
     two-up page of every book, which the owner has not been asked about.
     `tests/test_book_page_numbers.py` is updated to assert this new, correct
     behaviour (`test_two_up_page_s_folio_is_now_always_omitted`,
     `test_every_page_of_a_book_holding_one_of_every_kind_is_numbered`'s
     own carve-out) — **flagged here explicitly for the owner's render review:
     repositioning the folio (e.g. to the gutter-side corner, where this
     card's own slack now collects) would restore it, but that is a new
     placement decision this card does not make unilaterally.**

  **SCOPE+ edits beyond the card's own Touches list** (the card itself warned
  the list was not exhaustive): `tests/test_layout_page_spec.py` (a direct
  `render_image`/book `PageSpec` test, not originally listed, needed both the
  flush-left-edge numbers and a QR-icon allowance), `tests/test_book_proof_pages.py`
  and `src/nonogram/admin/book_proof.py` (ADR-0037's proof-page annotation
  feature — not in the Touches list at all — had its own `_fallback_spots`
  hard-coded to "outer side strip", which right-alignment makes read exactly
  backwards; fixed to read the gutter side instead, and its fallback-note
  placement now steps around the QR icon's own margin slot too), and
  `tests/test_book_page_numbers.py` (the folio exception above).

  **Fresh test evidence (this implementation, run against the venv at
  `/Users/omelnikova/PycharmProjects/PythonProject4/.venv`):**
  - `tests/property/test_book_layout.py` — 10 passed (incl. new
    `test_PropertyTest_BookLayout_DrawingAnchorsAtTheChosenEdge` AC-1,
    `test_TestLayout_FloorOverflowDirectionUnderRightAlignment` AC-3,
    `test_PropertyTest_BookLayout_ParityMirroringHoldsUnderTheNewAnchor` AC-4).
  - `tests/property/test_book_two_up.py` — 7 passed (incl. new
    `test_PropertyTest_BookTwoUp_SlotsAnchorAtTheChosenEdge` AC-2).
  - `tests/property/test_book_pdf_geometry.py` — 11 passed.
  - `tests/property/test_book_export_interior.py` — 2 passed.
  - `tests/test_book_pdf.py` — 44 passed.
  - `tests/test_book_puzzle_frame.py` — 68 passed.
  - `tests/test_layout_two_up.py`, `tests/test_layout_page_spec.py` — all passed.
  - `tests/test_book_solved_page.py` — all passed.
  - `tests/test_book_page_numbers.py` — 15 passed.
  - `tests/test_book_pdf_memory.py` — 42 passed, 1 skipped (incl. new
    `TestBookPdfMemory_NonDrawingPagesAreByteIdentical`, AC-7).
  - `tests/test_book_proof_pages.py` — 111 passed (against the new
    `proof_baseline_card204.json`).
  - `tests/test_book_qr_slot.py` (new file) — 12 passed, covering AC-5, AC-6
    and AC-8 by the card's own named test classes
    (`TestBookPdf_QrSlotReservedWithoutOverlap`,
    `TestBookPdf_QrSlotOmittedWhenNoRoomRatherThanOverlapping`,
    `TestBookPdf_QrPlaceholderIsVisiblyNotARealCode`).
  - `tests/test_export_pdf.py`, `tests/test_export_image.py` — confirmed
    unaffected (no parity-carrying `PageSpec` anywhere in either file): 124
    passed between them, CON-019 untouched.
  - A full `pytest -q` run of the whole suite was also taken; the only
    failures at any point were the ones enumerated above, each traced to its
    root cause and fixed or (the two exceptions above) documented rather than
    papered over.

  **New fixtures:** `tests/fixtures/book_baseline_card204.json` (supersedes
  `book_baseline_card200.json`, which stays, per the project's own
  never-regenerate convention) and `tests/fixtures/proof_baseline_card204.json`
  (supersedes `proof_baseline_card172.json`, same convention). Both carry their
  own `why_a_new_baseline`/`changed_pages_note` explaining exactly which pages
  moved and why, cross-checked against a direct git-stash diff of the renderer
  before writing either file — not assumed from the formula alone.

  **Renders.** No owner-facing render pass was produced by this implementation
  pass — per the task's own instruction, that is handled separately before
  merge. Pages were rendered and pixel-diffed extensively during
  implementation (saved to this session's own scratchpad and `/tmp`, not
  committed) purely to debug the specific regressions above; none of that is
  the "three readings side by side" comparison the card's own Design Context
  section asks for before owner sign-off.

  **Not touched, confirmed out of scope:** `tests/fixtures/make_fixtures.py`
  (the card's own Touches list included it; it is the *synthetic sourcing*
  fixture generator — `bands.png`/`landscape.png`/`portrait.png` — unrelated to
  book baselines, and nothing in this card touches it). `_packed_tile_layout`/
  `compute_packed_solved_layout`/`compute_answer_page_layout` (CARD-202's/
  FR-042's tile-local centring formulas) — investigated and confirmed to be a
  *different* formula FR-032's page-wide clause was never about; untouched,
  and measured to be genuinely byte-identical.

- [Fix 1, 2026-10-10] Owner decision implemented: **"Reserve folio room"** for
  the two-up folio-loss exception the implementation pass flagged. Puzzles on
  two-up pages stay flush to the outer edge, but the lower slot's drawing now
  leaves a small, exact, guaranteed gap at its own bottom-outer corner —
  sized per-page from the real folio text width (`_folio_reserve_px`, 27px at
  300 DPI for a 1-digit page), never an arbitrary constant — instead of being
  100% flush. The upper slot and every single-puzzle/answer page keep the
  unmodified flush rule. Two kw-only parameters added: `compute_pair_layout`'s
  `folio_reserve_px` (re-fits the shared cell slightly smaller only when the
  lower slot's own natural spare can't already hold the reserve — the common
  case pays nothing) and `_slot_layout`'s `outer_reserve_px` (shifts the lower
  slot's flush anchor toward the gutter by that many pixels, clamped so it
  can never worsen the pre-existing MIN_CELL_MM floor-overflow case).
  **A real bug found by the property-test oracle, not by inspection**: the
  first pass's natural-spare check read the lower puzzle's column-clue gutter
  depth instead of its row-clue depth, undetected by manual spot-checks
  (which happened to use symmetric-depth puzzles) until
  `tests/property/test_book_pairing.py`'s independent 900-case `cell_mm`
  oracle caught the one case where they disagree — fixed to read the correct
  depth. Confirmed empirically on both parities (Duck+Owl pair, page 5/6):
  folio now reliably draws with a 27px gap on each side. Six test files
  updated (not loosened): `test_book_page_numbers.py`,
  `test_book_export_interior.py`, `test_book_puzzle_frame.py`,
  `test_book_pdf_memory.py` (one whole-page comparison split into per-slot
  comparisons — a real structural finding, not a tolerance fudge, since the
  reserve's gutter-ward shift mirrors by parity), `test_book_pdf_two_up.py`,
  `test_book_pairing.py` (the oracle itself, updated to the same rule — this
  is what caught the bug). Baseline fixture regenerated in place (only
  interior page 5 moves, +296 bytes); `proof_baseline_card204.json` confirmed
  to need no change (proof pages never call `compute_pair_layout`).
  **Test evidence**: 17 touched/related test files run together, 0 failed (1
  pre-existing unrelated skip). **Orchestrator's own independent full-suite
  confirmation: 6853 passed, 9 skipped, 0 failed, 0 errors** (1112.15s).

- [Review] forge:review cycle 1 started (background agent, first review —
  no cycle happened before Fix 1, since the folio issue was caught and
  resolved via direct owner decision before the normal review gate).
- [Review 1/3] Score **4.5/10**. 1 Critical, 2 Minor/Info. Do not merge as-is.
  - **F-1 (Critical, reproduced by direct execution):** Fix 1's
    `folio_reserve_px` makes the two-up pairing accept/refuse decision
    (`compute_pair_layout`) depend on the PAGE NUMBER's own digit count, not
    on puzzle geometry alone — violating INV-010/G-5 and directly
    contradicting Fix 1's own documented claim ("a tiny, consistent gap...
    never more"). Concrete counterexample: two identical 25x6 puzzles (depth
    2) pair successfully at `cell_mm=7.00mm` on page 99 (2-digit folio,
    reserve=54px) but `compute_pair_layout` returns `None` (refuses to pair)
    for the IDENTICAL pair on page 100 of the same book (3-digit folio,
    reserve=81px) — same puzzles, same shapes, same tier, different only in
    page-number length. Untested: `test_book_pairing.py`'s 900-case oracle
    caps synthetic books at 8 puzzles (page numbers never reach 3 digits),
    structurally unable to catch this — and this project's own market
    research targets ~120-page books, where 3-digit folios are the norm, not
    an edge case. Real-world consequence: adding/removing a puzzle anywhere
    earlier in a book shifts every later page number, which could silently
    flip later pairing decisions and change the book's total page count,
    purely from page-number digit length.
  - **Verified clean** (investigated in the depth the task asked for): the
    MIN_CELL_MM floor-overflow case under the new no-clamp flush formula
    (both parities, verified algebraically); the reserve math's cap-vs-fit
    interaction (initially suspected a second bug, disproved by direct
    execution + a general algebraic proof); reserve-boundary exactness
    (no off-by-one); the QR slot's omit-vs-overlap geometry; the QR
    placeholder's inertness (AC-8, confirmed by direct source read — no
    URL/hostname/qrcode import anywhere); the guide-page sub-pixel rounding
    scatter (bounded, <1% of pixels, ≤1px shifts, same shape as CARD-149/
    167's already-absorbed precedent).
  - **Minor/Info:** `_slot_layout`'s docstring overstates what its
    floor-overflow clamp protects against (unreachable for two-up slots,
    given `compute_pair_layout`'s own 7.0mm gate); FR-032's `requirements.yml`
    text still says "centred" while code/tests implement right-alignment —
    already an explicitly declared architect-station deferral, not a hidden
    gap.
  - Mutation check (8f) and baseline-acceptance (8g) deferred per the
    cost-ladder rule (gating finding present) — run on the stable cycle once
    F-1 is fixed.
  - Review report synced: `meta/review/20261010T174853Z-CARD-204-cycle1.yml`.
  - **Verdict: cycle 1 does not meet the bar** — routing to forge:fix for F-1
    (decouple the pairing decision from `folio_reserve_px`, add a property
    test reaching 3-digit page numbers), cycle 2.

- [Fix 2, 2026-10-11] F-1 (Critical) and F-2 (Minor) fixed. Full writeup in
  the branch's own `[Fix 2]` worktree-notes entry (commits `5891969`/
  `0783434`). **F-1**: `_folio_reserve_px` changed from measuring one
  specific page's own folio width to a book-level worst-case bound
  (`max_page_number`'s own digit count times the widest digit this font
  draws) — `puzzle_section` computes it once for the whole book and passes
  the same value to every level's `puzzle_pages` call, so a pair's
  verdict/cell-size can no longer depend on which page it lands on.
  Reproduced the review's exact numbers (1-digit pairs at 7.0885mm, 2-digit
  at 7.0038mm, 3-digit refuses) before fixing, then proved the invariant
  end-to-end: the same pair gets an identical verdict whether placed early
  or late in an otherwise-identical book. New permanent regression test
  `test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
  (hand-derived expected values, independent of the production formula)
  sweeps 1/2/3-digit book-scale regimes, closing the review's own F-3 test-
  coverage gap too. **F-2**: `_slot_layout`'s docstring overclaim corrected.
  **Test evidence**: all touched test files green (test_book_pairing.py 3,
  test_book_page_numbers.py 15, test_book_puzzle_frame.py 66, etc.);
  `pytest tests/ -k "book"` exit 0. **Orchestrator's own independent
  full-suite confirmation: 6854 passed, 9 skipped, 0 failed, 0 errors**
  (1483.71s) — exactly 1 more than the prior 6853 (pre-Fix-2) count.
  **Process note**: the full-suite run initially appeared to hang for 5+
  hours on an unrelated pre-existing slow property test
  (`test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages`,
  220 full book-interior renders, normally ~2min, right at the 120s
  hang-guard threshold) — diagnosed via the project's own hang-guard stack
  dump plus an isolated clean rerun (1 passed in 119.54s) as severe
  Microsoft Defender CPU contention on this machine (a known, previously-
  documented issue this session), not a code defect. Confirmed harmless and
  unrelated to this fix before proceeding.

- [Review] forge:review cycle 2 started (confirmation pass, background agent).
- [Review 2/3] Score **4.0/10**. 1 NEW Critical, 1 carried informational
  (F-4, non-gating). Do not merge. Confirmed good: F-1's literal cycle-1
  reproduction (page 99 vs 100) is genuinely fixed; F-2 (docstring) and F-3
  (test-coverage gap) are genuinely closed; `puzzle_section`'s book-level
  bound is mathematically a safe upper bound (cross-checked against
  `interior_page_count`'s own reasoning) — no new unsafe-value bug there.
  - **F-5 (Critical, NEW — found via the adversarial re-derivation this
    cycle's task explicitly demanded, not by trusting the fix's own
    narrative):** Fix 2 did not remove the coupling between the pairing
    accept/refuse decision and a non-geometric digit-count quantity — it
    only moved it from PER-PAGE granularity to PER-BOOK-SCALE granularity.
    INV-010's own canonical statement
    (`meta/architecture/domain/aggregates.yml:83-91`) defines "fit" purely
    by tier equality + adjacency + shared cell >= 7.0mm — nothing about the
    book's own overall page count. Reproduced directly (the same pair
    cycle-1 used, unreserved cell 7.1731mm): identical pair, pairs at
    7.0038mm in a book whose own worst-case page number is 2 digits,
    refused outright in a book whose own worst-case is 3 digits — and the
    project's own market research cites a ~120-page median book, making the
    3-digit regime the COMMON case, not an edge case. This isn't a hidden
    regression — the fix's own new test bakes this exact behavior in as
    *expected* (`test_book_pairing.py:676-680`, regime `(98, 3, False,
    None)`), and the Fix 2 worktree notes assert "a legitimate dependency"
    without amending INV-010's own text or routing the drift to
    architect-station — unlike this same card's own F-4, which explicitly
    deferred its own text gap the correct way. G-5 (this card's own
    guardrail: "does not change which puzzles pair") is violated for the
    same reason it was in cycle 1.
  - **Suggested remedy** (the reviewer's own, both named, (a) preferred):
    (a) decouple the accept/refuse decision AND the committed cell size
    from `folio_reserve_px` entirely — decide pairing from the unreserved
    cell first, and make the reserve a purely cosmetic, best-effort
    adjustment applied only at drawing time: if the committed (unreserved)
    cell size happens to leave enough slack at a specific page's own
    corner, draw the folio; if not, omit it for that one page — the same
    "omit rather than collide" precedent CARD-200's own `_draw_folio`
    already established elsewhere, generalized here rather than invented;
    or (b) get the owner/architect-station to explicitly amend INV-010 to
    permit a book-scale term, recorded the same documented way F-4 was.
    Orchestrator's own read: (a) is clearly the better engineering path —
    it fully satisfies the existing invariant with no exception needed,
    costs only an occasional single omitted folio (a strictly smaller,
    already-precedented, page-local degradation) instead of changing
    whether two puzzles share a page at all, and needs no owner escalation
    since it's a technical fix, not a product tradeoff.
  - System contract: 56 rules checked, 8 ✓ holds, 46 ⚠ unchecked (carried),
    2 ✗ violated (INV-010, G-5).
  - Mutation check / baseline-acceptance deferred again (new gating finding
    this cycle).
  - Review report synced: `meta/review/20261012T140501Z-CARD-204-cycle2.yml`.
  - **Verdict: NOT ready to merge** — routing to forge:fix for F-5, cycle 3
    (implementing remedy (a): reserve becomes cosmetic/best-effort, never
    load-bearing for the pairing or cell-size decision).

- [Fix 3, 2026-10-12] F-5 (Critical) fixed. Full writeup in the branch's own
  `[Fix 3]` worktree-notes entry (commits `d68ca29`/`3831bb5`). **Root
  cause**: both prior fixes let `folio_reserve_px` participate in
  `compute_pair_layout`'s accept/refuse verdict and committed cell size —
  Fix 2 only moved the dependency from per-page to per-book-scale, still
  letting a non-geometric digit-count quantity decide whether two puzzles
  share a page. **Fix**: removed `folio_reserve_px`/`outer_reserve_px`
  entirely from `compute_pair_layout`/`_slot_layout` — both back to pure
  geometry-only arithmetic. Folio placement on two-up pages is now decided
  cosmetically, after pairing/cell-size are committed, via the pre-existing
  `_draw_folio` "omit rather than collide" check (no new code needed
  there). The gutter-ward shift was concluded unnecessary entirely and
  removed, not just made cosmetic — net change is -315 lines, a
  simplification. **Invariant re-proven**: the same pair now pairs at the
  identical cell size (7.173148148148148mm) across 1/2/3-digit book-scale
  regimes; the cycle-2-flagged test rewritten to assert this instead of the
  wrong prior expectation. **Baseline**: regenerated, -1191 bytes, an exact
  reversion to the pre-Fix-1 value (confirms this is a true behavioral
  reversion, not a new behavior). **Test evidence**: 6 touched files 169
  passed, 1 skipped (pre-existing); 4 more files all green; `pytest tests/
  -k "book"` exit 0. **Full suite: 6854 passed, 9 skipped, 0 failed, 0
  errors** (986.13s) — identical count to Fix 2's own run, consistent with
  a pure simplification.

- [Review] forge:review cycle 3 started (confirmation/final pass per
  max_cycles:3, background agent).
- [Review 3/3 — FINAL CYCLE, ESCALATION] Score **4.0/10**. 1 NEW Critical
  (F-7), 1 Minor (F-8, pre-existing/orthogonal), F-4 carried unchanged.
  **F-5/INV-010 confirmed cleanly and structurally resolved** — the
  reviewer independently re-derived (not just re-ran the new test) that
  `compute_pair_layout`/`_slot_layout` carry no parameter, default, or
  closure variable through which any page-number/book-scale quantity could
  reach the accept/refuse verdict or cell size; the baseline fixture's 13
  page digests are byte-identical to the original pre-Fix-1 commit
  (`0299bf1`), confirmed programmatically; a targeted mutation on the
  rewritten `_slot_layout` formula was killed (9 tests failed), confirming
  the tests actually pin this cycle's own change.
  - **F-7 (Critical, NEW — this exact cycle's own delta, not carried):**
    removing the reserve mechanism to fix F-5 silently **reintroduced the
    original pre-Fix-1 regression**: the folio is lost on **every** two-up
    page, not just tight-fit ones — verified with a deliberately asymmetric
    pair (25 vs 10 columns), confirming the outer-corner gap is exactly 0
    in both parities regardless of extent (algebraic: the flush formula's
    "+spare" term only ever lands on the gutter side, never the outer
    corner where the folio sits). **This is the identical finding this
    card's own pre-Fix-1 Worktree notes already proved** (search "permanently
    omitted on every two-up page... algebraically, regardless of the
    puzzle's own spare") — the exact finding that led to the owner's own
    "Reserve folio room" decision before Fix 1 was ever written. Fix 3
    silently reverts that owner decision without re-consulting them, and
    its own commit message/two docstrings (`layout.py:2072-2077`,
    `book_pdf_generator.py:3538-3544`) mischaracterize this as an
    occasional, pair-dependent "tight natural slack" case — contradicted by
    this cycle's own new regression test's own docstring, which correctly
    states the universal nature. The corpus-wide AC-1 test was narrowed to
    carve out the one two-up page rather than fixing or escalating.
  - **F-8 (Minor, non-gating):** a pre-existing, orthogonal exact-equality
    boundary gap in `TWO_UP_MIN_CELL_MM`'s `<`/`<=` comparison
    (`layout.py:1999`) — predates CARD-204 entirely, no covering test.
  - System contract: 56 rules checked, 9 ✓ holds (incl. INV-010, G-5 — both
    now genuinely resolved), 46 ⚠ unchecked (carried), 1 card-level AC
    violated (CARD-200's AC-1, not in the 56-rule registry, reported for
    visibility).
  - Review report synced: `meta/review/20261012T151720Z-CARD-204-cycle3.yml`.
  - **Verdict: NOT ready to merge. Review-budget escalation point reached**
    — this is cycle 3 of `max_cycles: 3`, and the card is still not clean.
    Per this project's own rule, continuing past this point requires
    explicit owner sign-off, not an automatic cycle 4. F-5 itself is
    cleanly and structurally fixed — the remaining problem is a genuine
    product tradeoff the owner already decided once (and this fix silently
    reversed without asking): whether every two-up page keeps its folio
    (their original "Reserve folio room" answer) is in direct tension with
    making the pairing decision purely geometry-based (INV-010). Routing to
    the owner for an explicit decision before any further fix cycle.

- [Owner decision, 2026-10-12] **"Fixed universal reserve."** Reserve a
  small, constant amount of room for the folio on every two-up page — the
  SAME fixed pixel amount for every book, never derived from any specific
  book's page count or page number (sized for up to 4 digits, covering any
  realistically-sized book this software could ever produce). This
  satisfies both standing requirements at once: `compute_pair_layout`'s
  accept/refuse verdict and cell size still depend only on the pair's own
  geometry plus one fixed, compile-time constant — the same category as the
  existing `TWO_UP_MIN_CELL_MM` constant already baked into this exact
  invariant, not a page/book-specific measurement — while every two-up page
  keeps its guaranteed folio room, restoring the owner's original "Reserve
  folio room" intent (Fix 1) without reopening F-1/F-5/F-7's bug class.
  Review-budget escalation cleared by this explicit sign-off — proceeding
  with one more fix cycle (Fix 4), within the now owner-authorized
  extension past `max_cycles: 3`.


- [Notes sync 2026-10-13T10:16Z] Fix 3 agent notes pulled one-way from the
  worktree copy (CARD SYNC PROTOCOL step 2), verbatim:

   [Fix 1, 2026-10-10] Owner decision received for the folio-loss exception the
   implementation pass flagged: **"Reserve folio room."** Puzzles on two-up
   pages stay flush to the outer edge, but the lower slot's drawing now leaves
   a small, exact, guaranteed gap at its own bottom-outer corner — just enough
   for CARD-200's folio, never more — instead of being 100% flush. The upper
   slot and every single-puzzle/answer page keep the unmodified flush rule.

   **The geometry change, precisely.** Two edits, both in
   `src/nonogram/export/layout.py`, both scoped to the two-up path only
   (`compute_layout`'s single-page branch is untouched — AC-3/G-6's
   floor-overflow reasoning there stands exactly as recorded above):
   1. `compute_pair_layout` gained a kw-only `folio_reserve_px: int = 0`.
      **Revised once already, within this same fix** (see the "discovered
      bug" note below): the shared cell is fit *normally* first (the plain,
      pre-Fix-1 `_placed_cell_mm` call, no widening) — the common case,
      verified against `tests/property/test_book_pairing.py`'s own
      independent 900-case corpus, leaves `cell_mm` identical to FR-040's
      unwidened formula in the overwhelming majority of pairs. Only when the
      **lower** slot's own natural spare at that cell (`usable_width_px -
      lower_drawing_columns * pitch`) already reads below
      `folio_reserve_px` does it re-fit a smaller cell, this time as though
      the usable width were `folio_reserve_px` narrower (a widened
      `outside_mm` fed to the fit step only, never to either slot's own
      placement) — which guarantees (algebraically, from `chosen_cell <= fit
      <= width_fit`, not by luck) that the re-fit cell leaves the lower slot
      at least `folio_reserve_px` of real headroom. Paying a smaller cell is
      therefore the exception, not the rule, and only ever as much smaller
      as the reserve actually needs.
   2. `_slot_layout` gained a kw-only `outer_reserve_px: int = 0`, passed only
      into the **lower** slot's own call. It shifts the flush anchor
      `outer_reserve_px` toward the gutter — `usable_right - drawing_right`
      (ODD) or `drawing_left - usable_left` (EVEN) becomes that many pixels
      instead of exactly zero — clamped to `max(spare, 0)` so it can only
      ever *reduce* how far the drawing reaches toward the gutter margin,
      never push it past `usable_left`/`usable_right`: the pre-existing
      MIN_CELL_MM floor-overflow corner (AC-3, G-6) cannot be made worse by
      this reserve, because step 1's headroom guarantee already covers every
      other case.

   **A real bug, found by the property-test oracle, not by inspection.**
   The first pass at step 1 widened the fit *unconditionally* on every
   two-up page, which `tests/property/test_book_pairing.py`'s own
   `cell_mm`-exactness assertion (an independent, 900-case re-derivation of
   FR-040's formula, predating this fix) correctly rejected as too broad a
   change. Narrowing step 1 to "only re-fit when the lower slot's own
   natural spare is insufficient" fixed most of the corpus but still left
   one real mismatch — which turned out to be a genuine bug, not a
   tolerance problem: the natural-spare check computed
   `lower_drawing_columns` as `_gutter_depth(lower_columns) +
   len(lower_columns)` (the *column* clues' own gutter depth — the puzzle's
   **top** gutter, used nowhere else for a width measurement) instead of
   `_gutter_depth(lower_rows) + len(lower_columns)` (the *row* clues'
   gutter depth — the **left** gutter, which is what actually makes up the
   drawing's width alongside the grid, exactly as the pair's own `across`
   calculation two lines above it already does). The two agree whenever a
   puzzle's row- and column-clue depths happen to be equal — true of every
   square, symmetric-depth puzzle this fix's own manual spot-checks used
   (Duck/Owl, the tight-fit fixtures), which is exactly why the bug passed
   every check run before the property test's own asymmetric-depth corpus
   caught it. Fixed to read `lower_rows`.

   **Sizing: re-derived, not an arbitrary constant.** The caller
   (`book_pdf_generator.py`'s new `_folio_reserve_px(page_number, dpi)`)
   measures *this exact page's own* folio text at `_draw_folio`'s own font
   (`FOLIO_PT`, `_band_font`, `font.getlength`), `math.ceil`'d to the nearest
   whole pixel — the same figure `_draw_folio`'s own horizontal-clearance
   check already computes internally, not reinvented. `puzzle_pages` passes
   it to `compute_pair_layout` per two-up page, so a 1-digit folio reserves
   less than a 3-digit one, never a worst-case guess. Measured on the
   baseline book: 27 px at 300 DPI for a 1-digit page number.

   **Why purely horizontal, confirmed by re-deriving the geometry rather than
   assuming it.** `_draw_folio`'s own check only reaches its horizontal
   clearance test when vertical room already reads zero
   (`bottom - content_bottom < line_height`) — which is unconditionally true
   for a two-up page's lower slot (`PairLayout`'s own invariant). Once there,
   the *only* thing that decides whether the folio collides is
   `content_right <= right - text_width` (ODD) or the mirror for EVEN — a
   purely horizontal test. No vertical change was needed or made; `top`/
   `bottom`/`band_top`/`slot_bottom` in `_slot_layout` are untouched.

   **Interaction with the QR placeholder slot: no blocker, confirmed by
   reading `qr_slot()` in full before writing any code.** The QR icon's first
   choice is the *gutter*-side margin strip, and its fallback is the slack
   *below* the drawing, flush with the usable area's bottom **and** its
   gutter side — `qr_slot()`'s own docstring states it never reaches for the
   folio's own (outer) corner. The reserve this fix adds eats into the same
   gutter-side slack the QR icon's first-choice strip draws from (on the
   **lower** slot only), which can in principle make that lower slot's icon
   fall back to its second strip (or omit) a little sooner than before — a
   real, accepted, measured consequence (the trade-off is a few more pixels
   of lower-slot gutter slack spent on the folio instead of the icon), never
   a corner the two marks fight over, since they are always on opposite
   sides of the page by construction.

   **Confirmed empirically, both parities, on the baseline book's own
   Duck+Owl pair (interior page 5, 10x10 puzzles, Book 1 trim):**
   - ODD (ad-hoc page 5): `usable_right - drawing_right` moves from `0` to
     `27` px for the lower slot only; the upper slot's own `0` is unchanged;
     `_two_up_page` now draws the folio (`"5"`, anchor `"rb"`) where it was
     previously omitted every time.
   - EVEN (ad-hoc page 6, same puzzles): `drawing_left - usable_left` moves
     from `0` to `27` px for the lower slot only; folio draws (`"6"`, anchor
     `"lb"`).
   - The pair's shared `cell_mm` was unchanged in this specific case (height,
     not width, was the binding fit constraint for these two puzzles), and
     both slots' `fits` held `True` throughout — the reserve bought the gap
     without shrinking the printed cell at all here. The property-test
     corpus below confirms the general case: `cell_mm` is unchanged for the
     overwhelming majority of pairs, and the narrow set where it does shrink
     (the lower puzzle is itself the pair's width-binding member, with no
     natural spare at the unwidened cell) now does so by exactly as much as
     the reserve needs — never more, confirmed to the fitting's own exact
     fraction, not approximated.

   **Tests updated, not papered over — six files in total.**
   `tests/test_book_page_numbers.py`: the "every page... carries exactly one
   folio" assertion drops its two-up-page carve-out, and
   `test_two_up_page_s_folio_is_now_always_omitted` is replaced by
   `test_two_up_page_s_folio_now_has_reserved_room`, which pins the exact
   reserved gap (`usable_right - drawing_right == reserve_px`) geometrically,
   not just "a folio call was made."
   `tests/property/test_book_export_interior.py`'s `_expected_drawing_left_mm`
   gained an independent `reserve_px` term (its own re-derivation of the same
   effect, in millimetres, not imported from `export/layout.py`), applied
   only to a two-up page's lower slot.
   `tests/test_book_puzzle_frame.py`'s `_expected_pair_boxes` gained the same,
   independently re-derived.
   `tests/test_book_pdf_memory.py`'s two `_reference()` helpers
   (`EveryPageAfterTheGuideIsByteIdenticalShiftedByOne` and
   `ContentAboveTheFooterBandIsUnchanged`) now pass their own page number's
   `_folio_reserve_px` into their own `compute_pair_layout` calls, so the
   "reference" geometry they build for comparison matches what production
   actually draws; **and** `ContentAboveTheFooterBandIsUnchanged`'s own
   whole-page ink-bbox comparison had to be split into an upper-slot
   comparison and a lower-slot comparison at the pair's own (parity-
   independent) midline — a real, investigated finding, not a tolerance
   fudge: cropping the *whole* pair to one bounding box silently compared one
   page's upper slot against the other (opposite-parity) page's lower-slot
   offset, because the reserve's "toward the gutter" direction mirrors by
   parity exactly as the flush edge itself does, so the lower slot sits
   27 px *left* of the upper slot's edge on an ODD page and 27 px *right* of
   it on the EVEN page being compared against — a structural mismatch no
   amount of tolerance should have hidden, not something Fix 1 introduced
   into the content itself.
   `tests/test_book_pdf_two_up.py`'s `_reference_band` gained an optional
   signed `shift_px`, applied at its two lower-slot call sites (pages 5 and
   6 of its own fixtures): `header_band`'s own `center_x` is centred *on the
   drawing*, not the usable width, so the lower slot's band — like its
   grid — now sits `folio_reserve_px` off a single page's own (unshifted)
   band position, a direct and correct consequence of step 2 above, not a
   defect.
   `tests/property/test_book_pairing.py`'s `Sheet.shared_cell_mm` gained an
   optional `page_number`, re-deriving (independently, not importing
   `compute_pair_layout`, preserving this module's own stated independence)
   the identical "only re-fit when the lower candidate's natural spare can't
   hold the reserve" rule step 1 above now applies — **this is the oracle
   that actually caught the `lower_drawing_columns` bug** described above:
   its 900-case corpus disagreed with production's `cell_mm` in exactly one
   case before the bug was found, and zero after.

   **Baseline fixture regenerated, in place (same filename — a revision of
   this card's own fixture, not a new card superseding it):**
   `tests/fixtures/book_baseline_card204.json`. Measured directly (page-by-
   page digest diff against this file's own pre-Fix-1 recording): **only
   interior page 5 moves** (the two-up page) — `interior_bytes` moves from
   3439483 to 3439779 (+296 bytes, the new folio glyph's own ink). No other
   page moves: pages 7/9 (single-puzzle) are placed by `compute_layout`,
   untouched by this fix; pages 11-13 (answer pages) never call
   `compute_pair_layout`. `font_fingerprint`/`font_dependent_pages` unchanged.
   `tests/helpers/book_corpus.py`'s own running history comment is updated
   with the same reasoning. **`tests/fixtures/proof_baseline_card204.json`
   needs no regeneration** — confirmed by reading `src/nonogram/admin/book_proof.py`
   in full: the proof pages call `compute_layout` only, never
   `compute_pair_layout`, so Fix 1 cannot reach them.

   **Fresh test evidence (this fix, run against the venv at
   `/Users/omelnikova/PycharmProjects/PythonProject4/.venv`), final pass
   after the `lower_drawing_columns` bug fix above:**
   - `tests/property/test_book_layout.py`, `tests/property/test_book_two_up.py`,
     `tests/property/test_book_pdf_geometry.py`,
     `tests/property/test_book_export_interior.py`,
     `tests/property/test_book_pairing.py`, `tests/test_book_pdf.py`,
     `tests/test_book_pdf_two_up.py`, `tests/test_book_puzzle_frame.py`,
     `tests/test_layout_two_up.py`, `tests/test_layout_page_spec.py`,
     `tests/test_book_solved_page.py`, `tests/test_book_qr_slot.py`,
     `tests/test_book_page_numbers.py`, `tests/test_book_pdf_memory.py`,
     `tests/test_book_proof_pages.py`, `tests/test_book_solved_answer_key.py`,
     `tests/test_book_pdf_ink_mode.py` — all 17 files run together, 0
     failed (one `test_book_pdf_memory.py` case skipped, pre-existing and
     unrelated — the font-fingerprint carve-out `TestBookPdfMemory_PagesAreUnchanged`
     already names).
   - Full project suite (`.venv/bin/python -m pytest -q` from the worktree
     root): **0 failed, 0 errors** — no `FAILED`/`ERROR` line anywhere in
     the output and exit code 0, run to completion (not interrupted; a
     first attempt was cut short by this session's own 30-minute command
     cap while two full suites ran concurrently on the same machine — the
     tool's own completion notification arrived, but the captured log's
     very last summary line was lost to that cap, so this entry cites the
     absence-of-FAILED/exit-0 evidence instead of quoting a final count
     line verbatim). This full run is also what caught both
     `test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly`
     and `tests/test_book_pdf_two_up.py`'s two band-position tests — neither
     was in this fix's own original touch-list guess, both genuinely broken
     by Fix 1's geometry change, both fixed above (not skipped, not loosened).

   [Fix 2, 2026-10-11] Review cycle 1's gating finding (F-1, Critical) and its
   companion (F-2, Minor) fixed.

   - **F-1 (Critical, fixed) — the pairing decision depended on the page
     number's own digit count.** Root cause: `_folio_reserve_px(page_number,
     dpi)` measured *that one page's own* folio text width and fed it
     straight into `compute_pair_layout`'s pairing/cell-sizing decision —
     the review reproduced directly that the identical pair of puzzles
     paired at a 2-digit page and refused outright at a 3-digit page of the
     same book, violating INV-010. **Fix**: `_folio_reserve_px` now takes
     `max_page_number` — a book-level worst-case bound, never one specific
     page's own number — and returns the widest single digit this font ever
     draws (measured over all ten, not assumed) times that bound's own digit
     count, a safe over-estimate. `puzzle_pages` derives this once per call
     from its own worst case when not told a value; `puzzle_section`
     computes it **once for the whole book** and passes the *same* value
     into every level's `puzzle_pages` call, so splitting the walk at a
     level boundary never gives two levels of one book two different
     reserves. `compute_pair_layout`/`_slot_layout` themselves are
     unchanged — only their docstrings now state the caller contract (the
     value must be page-number-independent).
   - **Invariant verified, not assumed.** Reproduced the review's exact F-1
     numbers directly against `compute_pair_layout` (confirmed: 1-digit
     reserve pairs at 7.0885mm, 2-digit at 7.0038mm, 3-digit refuses —
     matching the review's own cited figures exactly), then proved the fix
     end-to-end: the *same* borderline pair, placed early vs. late in an
     otherwise-identical book (different actual page numbers/parities), now
     gets an *identical* verdict and cell_mm every time — the verdict only
     changes when the *book's own total scale* crosses a digit boundary, a
     legitimate dependency, never from where the pair happens to land.
   - **New permanent regression test**:
     `tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
     — sweeps three enumerated regimes (1/2/3-digit book scales), each
     checked both early- and late-placed, with hand-derived expected
     `cell_mm` values (an independent second implementation per CLAUDE.md,
     not re-derived from this module's own oracle, which already shares the
     fix's own formula and so could not itself catch a regression in it).
     This closes the review's own F-3 gap too (the existing 900-case oracle
     caps books at 8 puzzles, never reaching a 3-digit page number).
   - **F-2 (Minor, fixed)** — `_slot_layout`'s docstring overclaimed that its
     reserve clamp guards the MIN_CELL_MM floor-overflow case; corrected to
     state that case is unreachable for a two-up slot (`compute_pair_layout`'s
     own 7.0mm gate already excludes it) and the clamp is kept only for
     defensive symmetry.
   - **Test files updated, re-verified against the new semantics (not left
     green by luck)**: `test_book_pairing.py` (oracle + new test),
     `test_book_export_interior.py` (oracle was failing before this fix:
     expected 27px, production now correctly uses 54px for a 4-puzzle book —
     fixed the oracle, not the assertion), `test_book_pdf_memory.py` (new
     `_book_folio_reserve_px` helper independently reimplementing
     `puzzle_section`'s formula, replacing a per-page re-derivation that
     would have silently reintroduced page-number dependence into the test
     itself), `test_book_page_numbers.py`/`test_book_puzzle_frame.py`/
     `test_book_pdf_two_up.py` (docstrings corrected; no logic changes
     needed — confirmed numerically that their small books' book-level and
     per-page bounds coincide at 1 digit).
   - **Baseline fixture regenerated in place**: `tests/fixtures/book_baseline_card204.json`
     — only interior page 5's digest moves (`interior_bytes`: 3439779 →
     3440674, +895 bytes), because the baseline book's own worst-case bound
     is 2 digits vs. Fix 1's page-5-specific 1 digit; confirmed by diffing
     all 13 page digests programmatically — pages 1-4/6-13 and
     `font_fingerprint` byte-identical to Fix 1's own recording.
   - **Test evidence:** `test_book_pairing.py` 3 passed; `test_book_page_numbers.py`
     15 passed; `test_book_puzzle_frame.py` 66 passed; `test_book_pdf_two_up.py`
     all passed; `test_book_export_interior.py` 2 passed; `test_book_pdf_memory.py`
     40 passed, 1 skipped (pre-existing, unrelated); `test_book_qr_slot.py` 12
     passed; `pytest tests/ -k "book"` exit 0, [100%], no F/E (confirmed twice).
   - **Orchestrator's own investigation note**: the mandated full-suite run
     initially appeared to hang for 5+ hours on
     `test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages`.
     Diagnosed via this project's own hang-guard stack dump and an isolated
     reproduction: **not a bug** — this is a legitimately slow pre-existing
     property test (220 full book-interior renders) that normally takes
     ~2 minutes, right at the 120s hang-guard threshold, and stretched to
     hours under this machine's documented severe Microsoft Defender CPU
     contention (`wdavdaemon_unprivileged` spiking 100-500%+ CPU). Confirmed
     by a clean isolated rerun: 1 passed in 119.54s, no contention. Unrelated
     to this fix.

   [Fix 3, 2026-10-12] Review cycle 2's gating finding (F-5, Critical) fixed.

   - **F-5 root cause:** Fix 1 (per-page) and Fix 2 (book-level) both let
     `folio_reserve_px` — a non-geometric quantity derived from a page
     number's or a book's own digit count — participate in
     `compute_pair_layout`'s accept/refuse verdict and its committed cell
     size. The identical 25x6 pair paired at 7.0038mm in a 2-digit-page-
     number book and was refused outright in a 3-digit one — INV-010 and
     guardrail G-5 violated, just at a coarser granularity than cycle 1's
     F-1.
   - **The fix — new decision order.** `folio_reserve_px`/`outer_reserve_px`
     removed ENTIRELY from `compute_pair_layout`/`_slot_layout`
     (`export/layout.py`) — both are back to pure, geometry-only arithmetic,
     structurally incapable of being influenced by any page-number or
     book-scale quantity. `_folio_reserve_px()` (`book_pdf_generator.py`)
     deleted outright, along with all its plumbing through
     `puzzle_pages`/`puzzle_section`. Folio placement on two-up pages is now
     decided purely cosmetically, AFTER pairing/cell-size are committed, by
     the pre-existing `_draw_folio` `content_right`/`content_left`
     "omit rather than collide" check — no new code needed there, since it
     already reads each slot's natural (unshifted) geometry. Concluded the
     Fix-1-style gutter-ward shift is no longer needed at all (not just
     "made cosmetic") — once it can't affect pairing/cell-size, the folio
     either fits in whatever natural slack the geometry-only cell leaves, or
     it doesn't and is correctly omitted; removed rather than kept as dead
     weight.
   - **Invariant proof, tested not assumed:** the same pair (unreserved cell
     7.173148148148148mm) now pairs at the IDENTICAL cell size across 1/2/3-
     digit book-scale regimes, early- and late-placed alike — confirmed by
     direct script execution against `compute_pair_layout`/`puzzle_pages`
     before writing the test.
     `test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
     rewritten: `REGIMES` now asserts all three regimes pair identically
     (previously it asserted the 3-digit regime refuses — exactly the wrong
     expectation cycle 2 caught).
   - **Test files re-derived from the new/correct behavior, not patched to
     pass:** `test_book_pairing.py` (oracle simplified to pure geometry, test
     rewritten), `test_book_export_interior.py` (reserve term dropped),
     `test_book_pdf_memory.py` (reserve helper removed; baseline
     regenerated), `test_book_page_numbers.py` (two-up folio-omission
     carve-out correctly reinstated — the baseline Duck+Owl pair is
     page-fit-bound on width, natural slack 0, folio omitted again, as it
     was before Fix 1 ever existed), `test_book_puzzle_frame.py`/
     `test_book_pdf_two_up.py` (shift logic dropped from expected-geometry
     helpers).
   - **Baseline fixture:** `tests/fixtures/book_baseline_card204.json`
     regenerated in place — only interior page 5 moves, `interior_bytes`
     3440674 → 3439483 (a -1191-byte reversion to the exact pre-Fix-1 value,
     confirming the fix is a true behavioral reversion to "no reserve",
     not a new, different behavior).
   - **Test evidence:** six touched files together 169 passed, 1 skipped
     (pre-existing, unrelated), 0 failed; `test_layout_two_up.py` +
     `test_book_two_up.py` + `test_book_arrange_page_breaks.py` +
     `test_book_qr_slot.py` all green; `pytest tests/ -k "book"` exit 0,
     [100%], no FAILED. **Full suite: 6854 passed, 9 skipped, 0 failed, 0
     errors** (986.13s) — identical pass count to Fix 2's own full-suite run,
     consistent with this being a net code simplification (10 files,
     +353/-668) rather than new functionality.
   - Re-verified unaffected: MIN_CELL_MM floor-overflow (`compute_layout`'s
     single-page branch untouched by any fix); the QR slot's own
     gutter-first/below-fallback/omit rule (never coupled to the folio
     reserve in the first place).

- [Dispatch] wave 37, 2026-10-13T10:16:42Z — pipeline RESUMED by `/forge:kanban run`
  (owner decision 2026-10-13: resume in this wave). State found: HEAD at Fix 3's
  notes commit `3831bb5`, with Fix 4 UNCOMMITTED in the worktree (9 files,
  +706/-296 — `compute_pair_layout` regains a `folio_reserve_px` keyword with a
  fixed default, i.e. the owner's "fixed universal reserve"). A fix agent is
  resuming it: verify the uncommitted work against the owner decision, commit,
  then review cycle 4 (owner-authorized extension past `max_cycles: 3`).
- [Review sync] 2 report(s) → meta/review/

- [Touches drift] 2026-10-13T10:40Z — 25 files changed, 13 outside the declared
  `Touches:`: CHANGELOG.md, src/nonogram/admin/book_proof.py,
  src/nonogram/export/png.py, tests/fixtures/book_baseline_card203.json,
  tests/fixtures/book_baseline_card204.json,
  tests/fixtures/proof_baseline_card204.json, tests/helpers/book_corpus.py,
  tests/property/test_book_pairing.py, tests/test_book_page_numbers.py,
  tests/test_book_proof_pages.py, tests/test_book_qr_slot.py,
  tests/test_book_solved_answer_key.py, tests/test_layout_page_spec.py.
  Not an error: the placement change ripples into the proof-page renderer and
  the recorded baselines. Recorded for `forge:retrospective`'s Touches
  calibration (Step 4e).
- [Scope] 2026-10-13T10:40Z — the mechanical sibling-poach check fires on this
  card (its diff covers 2/5 of CARD-205's and 3/6 of CARD-206's `Touches:`),
  but this is NOT poaching: both siblings were cut knowing they depend on this
  card's rewrite of `book_pdf_generator.py`/`layout.py`, and both carry a
  predicted conflict edge to it. No action — they start after this card merges,
  from a target branch that already holds it.

- [Full-suite lock gap] 2026-10-13T10:50Z — two full suites are running
  concurrently on this host: CARD-204's worktree (`pytest -p no:warnings -rf`,
  its SECOND full run of this fix — scratchpad `full2.log`) and CARD-214's
  (`pytest -q -p no:warnings`). cmd-start-review's FULL-SUITE LOCK
  (`meta/kanban/.full-suite.lock`) is an orchestrator-side mechanism and the
  implementation agents do not take it themselves, so nothing serialized them.
  Not killed — both runs are 8+ minutes in and killing them wastes the time
  already spent. Consequence to weigh when the results land: wall-clock per run
  is inflated, and any UNEXPECTED failure in the admin/DB-touching tests should
  be re-run serialized before it is believed.

- [Fix 4] 2026-10-13 — fix agent finished and COMMITTED `f496bf5` (12 files,
  +898/-297, nothing under `meta/`). Orchestrator-verified independently of the
  agent's report: the commit exists with that shape, and the worktree's own
  full-suite log records **6857 passed, 9 skipped, 0 failed, 1037.45s** (+3 tests
  vs Fix 3's 6854 — the three the fix added). Agent-reported mechanism, to be
  judged by review cycle 4, not taken as established here: a fixed
  `_folio_reserve_px(dpi)` = widest digit x `FOLIO_RESERVE_DIGITS = 4` = 108 px
  at 300 DPI, passed to the lower slot only, with the cell re-fit only when the
  lower slot's natural spare cannot already hold it. Four gaps it reports
  closing: `test_book_pdf_memory.py`'s three unreserved `compute_pair_layout`
  helpers (a tolerance-based comparison was absorbing a real 108 px
  displacement), a missing corpus-wide universality test (F-7's actual
  complaint), a raise-instead-of-decline on a reserve wider than the page, and
  stale Fix-2 figures in the baseline fixture's own note. Claims the
  carve-out narrowing is reverted (corpus-wide AC-1 restored).
  Owner-visible cost it measured: on a 900-case adversarial sweep, 9 of 176
  otherwise-pairing pairs (5%) are now refused — inherent to the owner's
  decision, now in `TWO_UP_MIN_CELL_MM`'s category.
- [Build gate] 2026-10-13 — full suite green from the worktree (6857/0). Note
  the run overlapped CARD-214's suite (see the lock-gap note above); it passed
  clean, so no re-run is needed.
- [Review] cycle 4/3+1 (owner-authorized extension) starting 2026-10-13 —
  reviewer must judge Fix 4 against the owner decision AND against the F-1/F-5/F-7
  family: this is the fourth attempt at the same mechanism.

- [Notes sync 2026-10-13, post-Fix-4] agent notes pulled one-way from the
  worktree copy (CARD SYNC PROTOCOL step 2), verbatim:

  - [Fix 1, 2026-10-10] Owner decision received for the folio-loss exception the
    implementation pass flagged: **"Reserve folio room."** Puzzles on two-up
    pages stay flush to the outer edge, but the lower slot's drawing now leaves
    a small, exact, guaranteed gap at its own bottom-outer corner — just enough
    for CARD-200's folio, never more — instead of being 100% flush. The upper
    slot and every single-puzzle/answer page keep the unmodified flush rule.

    **The geometry change, precisely.** Two edits, both in
    `src/nonogram/export/layout.py`, both scoped to the two-up path only
    (`compute_layout`'s single-page branch is untouched — AC-3/G-6's
    floor-overflow reasoning there stands exactly as recorded above):
    1. `compute_pair_layout` gained a kw-only `folio_reserve_px: int = 0`.
       **Revised once already, within this same fix** (see the "discovered
       bug" note below): the shared cell is fit *normally* first (the plain,
       pre-Fix-1 `_placed_cell_mm` call, no widening) — the common case,
       verified against `tests/property/test_book_pairing.py`'s own
       independent 900-case corpus, leaves `cell_mm` identical to FR-040's
       unwidened formula in the overwhelming majority of pairs. Only when the
       **lower** slot's own natural spare at that cell (`usable_width_px -
       lower_drawing_columns * pitch`) already reads below
       `folio_reserve_px` does it re-fit a smaller cell, this time as though
       the usable width were `folio_reserve_px` narrower (a widened
       `outside_mm` fed to the fit step only, never to either slot's own
       placement) — which guarantees (algebraically, from `chosen_cell <= fit
       <= width_fit`, not by luck) that the re-fit cell leaves the lower slot
       at least `folio_reserve_px` of real headroom. Paying a smaller cell is
       therefore the exception, not the rule, and only ever as much smaller
       as the reserve actually needs.
    2. `_slot_layout` gained a kw-only `outer_reserve_px: int = 0`, passed only
       into the **lower** slot's own call. It shifts the flush anchor
       `outer_reserve_px` toward the gutter — `usable_right - drawing_right`
       (ODD) or `drawing_left - usable_left` (EVEN) becomes that many pixels
       instead of exactly zero — clamped to `max(spare, 0)` so it can only
       ever *reduce* how far the drawing reaches toward the gutter margin,
       never push it past `usable_left`/`usable_right`: the pre-existing
       MIN_CELL_MM floor-overflow corner (AC-3, G-6) cannot be made worse by
       this reserve, because step 1's headroom guarantee already covers every
       other case.

    **A real bug, found by the property-test oracle, not by inspection.**
    The first pass at step 1 widened the fit *unconditionally* on every
    two-up page, which `tests/property/test_book_pairing.py`'s own
    `cell_mm`-exactness assertion (an independent, 900-case re-derivation of
    FR-040's formula, predating this fix) correctly rejected as too broad a
    change. Narrowing step 1 to "only re-fit when the lower slot's own
    natural spare is insufficient" fixed most of the corpus but still left
    one real mismatch — which turned out to be a genuine bug, not a
    tolerance problem: the natural-spare check computed
    `lower_drawing_columns` as `_gutter_depth(lower_columns) +
    len(lower_columns)` (the *column* clues' own gutter depth — the puzzle's
    **top** gutter, used nowhere else for a width measurement) instead of
    `_gutter_depth(lower_rows) + len(lower_columns)` (the *row* clues'
    gutter depth — the **left** gutter, which is what actually makes up the
    drawing's width alongside the grid, exactly as the pair's own `across`
    calculation two lines above it already does). The two agree whenever a
    puzzle's row- and column-clue depths happen to be equal — true of every
    square, symmetric-depth puzzle this fix's own manual spot-checks used
    (Duck/Owl, the tight-fit fixtures), which is exactly why the bug passed
    every check run before the property test's own asymmetric-depth corpus
    caught it. Fixed to read `lower_rows`.

    **Sizing: re-derived, not an arbitrary constant.** The caller
    (`book_pdf_generator.py`'s new `_folio_reserve_px(page_number, dpi)`)
    measures *this exact page's own* folio text at `_draw_folio`'s own font
    (`FOLIO_PT`, `_band_font`, `font.getlength`), `math.ceil`'d to the nearest
    whole pixel — the same figure `_draw_folio`'s own horizontal-clearance
    check already computes internally, not reinvented. `puzzle_pages` passes
    it to `compute_pair_layout` per two-up page, so a 1-digit folio reserves
    less than a 3-digit one, never a worst-case guess. Measured on the
    baseline book: 27 px at 300 DPI for a 1-digit page number.

    **Why purely horizontal, confirmed by re-deriving the geometry rather than
    assuming it.** `_draw_folio`'s own check only reaches its horizontal
    clearance test when vertical room already reads zero
    (`bottom - content_bottom < line_height`) — which is unconditionally true
    for a two-up page's lower slot (`PairLayout`'s own invariant). Once there,
    the *only* thing that decides whether the folio collides is
    `content_right <= right - text_width` (ODD) or the mirror for EVEN — a
    purely horizontal test. No vertical change was needed or made; `top`/
    `bottom`/`band_top`/`slot_bottom` in `_slot_layout` are untouched.

    **Interaction with the QR placeholder slot: no blocker, confirmed by
    reading `qr_slot()` in full before writing any code.** The QR icon's first
    choice is the *gutter*-side margin strip, and its fallback is the slack
    *below* the drawing, flush with the usable area's bottom **and** its
    gutter side — `qr_slot()`'s own docstring states it never reaches for the
    folio's own (outer) corner. The reserve this fix adds eats into the same
    gutter-side slack the QR icon's first-choice strip draws from (on the
    **lower** slot only), which can in principle make that lower slot's icon
    fall back to its second strip (or omit) a little sooner than before — a
    real, accepted, measured consequence (the trade-off is a few more pixels
    of lower-slot gutter slack spent on the folio instead of the icon), never
    a corner the two marks fight over, since they are always on opposite
    sides of the page by construction.

    **Confirmed empirically, both parities, on the baseline book's own
    Duck+Owl pair (interior page 5, 10x10 puzzles, Book 1 trim):**
    - ODD (ad-hoc page 5): `usable_right - drawing_right` moves from `0` to
      `27` px for the lower slot only; the upper slot's own `0` is unchanged;
      `_two_up_page` now draws the folio (`"5"`, anchor `"rb"`) where it was
      previously omitted every time.
    - EVEN (ad-hoc page 6, same puzzles): `drawing_left - usable_left` moves
      from `0` to `27` px for the lower slot only; folio draws (`"6"`, anchor
      `"lb"`).
    - The pair's shared `cell_mm` was unchanged in this specific case (height,
      not width, was the binding fit constraint for these two puzzles), and
      both slots' `fits` held `True` throughout — the reserve bought the gap
      without shrinking the printed cell at all here. The property-test
      corpus below confirms the general case: `cell_mm` is unchanged for the
      overwhelming majority of pairs, and the narrow set where it does shrink
      (the lower puzzle is itself the pair's width-binding member, with no
      natural spare at the unwidened cell) now does so by exactly as much as
      the reserve needs — never more, confirmed to the fitting's own exact
      fraction, not approximated.

    **Tests updated, not papered over — six files in total.**
    `tests/test_book_page_numbers.py`: the "every page... carries exactly one
    folio" assertion drops its two-up-page carve-out, and
    `test_two_up_page_s_folio_is_now_always_omitted` is replaced by
    `test_two_up_page_s_folio_now_has_reserved_room`, which pins the exact
    reserved gap (`usable_right - drawing_right == reserve_px`) geometrically,
    not just "a folio call was made."
    `tests/property/test_book_export_interior.py`'s `_expected_drawing_left_mm`
    gained an independent `reserve_px` term (its own re-derivation of the same
    effect, in millimetres, not imported from `export/layout.py`), applied
    only to a two-up page's lower slot.
    `tests/test_book_puzzle_frame.py`'s `_expected_pair_boxes` gained the same,
    independently re-derived.
    `tests/test_book_pdf_memory.py`'s two `_reference()` helpers
    (`EveryPageAfterTheGuideIsByteIdenticalShiftedByOne` and
    `ContentAboveTheFooterBandIsUnchanged`) now pass their own page number's
    `_folio_reserve_px` into their own `compute_pair_layout` calls, so the
    "reference" geometry they build for comparison matches what production
    actually draws; **and** `ContentAboveTheFooterBandIsUnchanged`'s own
    whole-page ink-bbox comparison had to be split into an upper-slot
    comparison and a lower-slot comparison at the pair's own (parity-
    independent) midline — a real, investigated finding, not a tolerance
    fudge: cropping the *whole* pair to one bounding box silently compared one
    page's upper slot against the other (opposite-parity) page's lower-slot
    offset, because the reserve's "toward the gutter" direction mirrors by
    parity exactly as the flush edge itself does, so the lower slot sits
    27 px *left* of the upper slot's edge on an ODD page and 27 px *right* of
    it on the EVEN page being compared against — a structural mismatch no
    amount of tolerance should have hidden, not something Fix 1 introduced
    into the content itself.
    `tests/test_book_pdf_two_up.py`'s `_reference_band` gained an optional
    signed `shift_px`, applied at its two lower-slot call sites (pages 5 and
    6 of its own fixtures): `header_band`'s own `center_x` is centred *on the
    drawing*, not the usable width, so the lower slot's band — like its
    grid — now sits `folio_reserve_px` off a single page's own (unshifted)
    band position, a direct and correct consequence of step 2 above, not a
    defect.
    `tests/property/test_book_pairing.py`'s `Sheet.shared_cell_mm` gained an
    optional `page_number`, re-deriving (independently, not importing
    `compute_pair_layout`, preserving this module's own stated independence)
    the identical "only re-fit when the lower candidate's natural spare can't
    hold the reserve" rule step 1 above now applies — **this is the oracle
    that actually caught the `lower_drawing_columns` bug** described above:
    its 900-case corpus disagreed with production's `cell_mm` in exactly one
    case before the bug was found, and zero after.

    **Baseline fixture regenerated, in place (same filename — a revision of
    this card's own fixture, not a new card superseding it):**
    `tests/fixtures/book_baseline_card204.json`. Measured directly (page-by-
    page digest diff against this file's own pre-Fix-1 recording): **only
    interior page 5 moves** (the two-up page) — `interior_bytes` moves from
    3439483 to 3439779 (+296 bytes, the new folio glyph's own ink). No other
    page moves: pages 7/9 (single-puzzle) are placed by `compute_layout`,
    untouched by this fix; pages 11-13 (answer pages) never call
    `compute_pair_layout`. `font_fingerprint`/`font_dependent_pages` unchanged.
    `tests/helpers/book_corpus.py`'s own running history comment is updated
    with the same reasoning. **`tests/fixtures/proof_baseline_card204.json`
    needs no regeneration** — confirmed by reading `src/nonogram/admin/book_proof.py`
    in full: the proof pages call `compute_layout` only, never
    `compute_pair_layout`, so Fix 1 cannot reach them.

    **Fresh test evidence (this fix, run against the venv at
    `/Users/omelnikova/PycharmProjects/PythonProject4/.venv`), final pass
    after the `lower_drawing_columns` bug fix above:**
    - `tests/property/test_book_layout.py`, `tests/property/test_book_two_up.py`,
      `tests/property/test_book_pdf_geometry.py`,
      `tests/property/test_book_export_interior.py`,
      `tests/property/test_book_pairing.py`, `tests/test_book_pdf.py`,
      `tests/test_book_pdf_two_up.py`, `tests/test_book_puzzle_frame.py`,
      `tests/test_layout_two_up.py`, `tests/test_layout_page_spec.py`,
      `tests/test_book_solved_page.py`, `tests/test_book_qr_slot.py`,
      `tests/test_book_page_numbers.py`, `tests/test_book_pdf_memory.py`,
      `tests/test_book_proof_pages.py`, `tests/test_book_solved_answer_key.py`,
      `tests/test_book_pdf_ink_mode.py` — all 17 files run together, 0
      failed (one `test_book_pdf_memory.py` case skipped, pre-existing and
      unrelated — the font-fingerprint carve-out `TestBookPdfMemory_PagesAreUnchanged`
      already names).
    - Full project suite (`.venv/bin/python -m pytest -q` from the worktree
      root): **0 failed, 0 errors** — no `FAILED`/`ERROR` line anywhere in
      the output and exit code 0, run to completion (not interrupted; a
      first attempt was cut short by this session's own 30-minute command
      cap while two full suites ran concurrently on the same machine — the
      tool's own completion notification arrived, but the captured log's
      very last summary line was lost to that cap, so this entry cites the
      absence-of-FAILED/exit-0 evidence instead of quoting a final count
      line verbatim). This full run is also what caught both
      `test_PropertyTest_BookPairing_InOrderSameTierFittingNeighboursOnly`
      and `tests/test_book_pdf_two_up.py`'s two band-position tests — neither
      was in this fix's own original touch-list guess, both genuinely broken
      by Fix 1's geometry change, both fixed above (not skipped, not loosened).

  - [Fix 2, 2026-10-11] Review cycle 1's gating finding (F-1, Critical) and its
    companion (F-2, Minor) fixed.

    - **F-1 (Critical, fixed) — the pairing decision depended on the page
      number's own digit count.** Root cause: `_folio_reserve_px(page_number,
      dpi)` measured *that one page's own* folio text width and fed it
      straight into `compute_pair_layout`'s pairing/cell-sizing decision —
      the review reproduced directly that the identical pair of puzzles
      paired at a 2-digit page and refused outright at a 3-digit page of the
      same book, violating INV-010. **Fix**: `_folio_reserve_px` now takes
      `max_page_number` — a book-level worst-case bound, never one specific
      page's own number — and returns the widest single digit this font ever
      draws (measured over all ten, not assumed) times that bound's own digit
      count, a safe over-estimate. `puzzle_pages` derives this once per call
      from its own worst case when not told a value; `puzzle_section`
      computes it **once for the whole book** and passes the *same* value
      into every level's `puzzle_pages` call, so splitting the walk at a
      level boundary never gives two levels of one book two different
      reserves. `compute_pair_layout`/`_slot_layout` themselves are
      unchanged — only their docstrings now state the caller contract (the
      value must be page-number-independent).
    - **Invariant verified, not assumed.** Reproduced the review's exact F-1
      numbers directly against `compute_pair_layout` (confirmed: 1-digit
      reserve pairs at 7.0885mm, 2-digit at 7.0038mm, 3-digit refuses —
      matching the review's own cited figures exactly), then proved the fix
      end-to-end: the *same* borderline pair, placed early vs. late in an
      otherwise-identical book (different actual page numbers/parities), now
      gets an *identical* verdict and cell_mm every time — the verdict only
      changes when the *book's own total scale* crosses a digit boundary, a
      legitimate dependency, never from where the pair happens to land.
    - **New permanent regression test**:
      `tests/property/test_book_pairing.py::test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
      — sweeps three enumerated regimes (1/2/3-digit book scales), each
      checked both early- and late-placed, with hand-derived expected
      `cell_mm` values (an independent second implementation per CLAUDE.md,
      not re-derived from this module's own oracle, which already shares the
      fix's own formula and so could not itself catch a regression in it).
      This closes the review's own F-3 gap too (the existing 900-case oracle
      caps books at 8 puzzles, never reaching a 3-digit page number).
    - **F-2 (Minor, fixed)** — `_slot_layout`'s docstring overclaimed that its
      reserve clamp guards the MIN_CELL_MM floor-overflow case; corrected to
      state that case is unreachable for a two-up slot (`compute_pair_layout`'s
      own 7.0mm gate already excludes it) and the clamp is kept only for
      defensive symmetry.
    - **Test files updated, re-verified against the new semantics (not left
      green by luck)**: `test_book_pairing.py` (oracle + new test),
      `test_book_export_interior.py` (oracle was failing before this fix:
      expected 27px, production now correctly uses 54px for a 4-puzzle book —
      fixed the oracle, not the assertion), `test_book_pdf_memory.py` (new
      `_book_folio_reserve_px` helper independently reimplementing
      `puzzle_section`'s formula, replacing a per-page re-derivation that
      would have silently reintroduced page-number dependence into the test
      itself), `test_book_page_numbers.py`/`test_book_puzzle_frame.py`/
      `test_book_pdf_two_up.py` (docstrings corrected; no logic changes
      needed — confirmed numerically that their small books' book-level and
      per-page bounds coincide at 1 digit).
    - **Baseline fixture regenerated in place**: `tests/fixtures/book_baseline_card204.json`
      — only interior page 5's digest moves (`interior_bytes`: 3439779 →
      3440674, +895 bytes), because the baseline book's own worst-case bound
      is 2 digits vs. Fix 1's page-5-specific 1 digit; confirmed by diffing
      all 13 page digests programmatically — pages 1-4/6-13 and
      `font_fingerprint` byte-identical to Fix 1's own recording.
    - **Test evidence:** `test_book_pairing.py` 3 passed; `test_book_page_numbers.py`
      15 passed; `test_book_puzzle_frame.py` 66 passed; `test_book_pdf_two_up.py`
      all passed; `test_book_export_interior.py` 2 passed; `test_book_pdf_memory.py`
      40 passed, 1 skipped (pre-existing, unrelated); `test_book_qr_slot.py` 12
      passed; `pytest tests/ -k "book"` exit 0, [100%], no F/E (confirmed twice).
    - **Orchestrator's own investigation note**: the mandated full-suite run
      initially appeared to hang for 5+ hours on
      `test_PropertyTest_BookLayout_DrawingFitsUsableAreaUnderStandardCell_pdf_pages`.
      Diagnosed via this project's own hang-guard stack dump and an isolated
      reproduction: **not a bug** — this is a legitimately slow pre-existing
      property test (220 full book-interior renders) that normally takes
      ~2 minutes, right at the 120s hang-guard threshold, and stretched to
      hours under this machine's documented severe Microsoft Defender CPU
      contention (`wdavdaemon_unprivileged` spiking 100-500%+ CPU). Confirmed
      by a clean isolated rerun: 1 passed in 119.54s, no contention. Unrelated
      to this fix.

  - [Fix 3, 2026-10-12] Review cycle 2's gating finding (F-5, Critical) fixed.

    - **F-5 root cause:** Fix 1 (per-page) and Fix 2 (book-level) both let
      `folio_reserve_px` — a non-geometric quantity derived from a page
      number's or a book's own digit count — participate in
      `compute_pair_layout`'s accept/refuse verdict and its committed cell
      size. The identical 25x6 pair paired at 7.0038mm in a 2-digit-page-
      number book and was refused outright in a 3-digit one — INV-010 and
      guardrail G-5 violated, just at a coarser granularity than cycle 1's
      F-1.
    - **The fix — new decision order.** `folio_reserve_px`/`outer_reserve_px`
      removed ENTIRELY from `compute_pair_layout`/`_slot_layout`
      (`export/layout.py`) — both are back to pure, geometry-only arithmetic,
      structurally incapable of being influenced by any page-number or
      book-scale quantity. `_folio_reserve_px()` (`book_pdf_generator.py`)
      deleted outright, along with all its plumbing through
      `puzzle_pages`/`puzzle_section`. Folio placement on two-up pages is now
      decided purely cosmetically, AFTER pairing/cell-size are committed, by
      the pre-existing `_draw_folio` `content_right`/`content_left`
      "omit rather than collide" check — no new code needed there, since it
      already reads each slot's natural (unshifted) geometry. Concluded the
      Fix-1-style gutter-ward shift is no longer needed at all (not just
      "made cosmetic") — once it can't affect pairing/cell-size, the folio
      either fits in whatever natural slack the geometry-only cell leaves, or
      it doesn't and is correctly omitted; removed rather than kept as dead
      weight.
    - **Invariant proof, tested not assumed:** the same pair (unreserved cell
      7.173148148148148mm) now pairs at the IDENTICAL cell size across 1/2/3-
      digit book-scale regimes, early- and late-placed alike — confirmed by
      direct script execution against `compute_pair_layout`/`puzzle_pages`
      before writing the test.
      `test_PropertyTest_BookPairing_ReserveIsTheBookSOwnScaleNotAPageNumber`
      rewritten: `REGIMES` now asserts all three regimes pair identically
      (previously it asserted the 3-digit regime refuses — exactly the wrong
      expectation cycle 2 caught).
    - **Test files re-derived from the new/correct behavior, not patched to
      pass:** `test_book_pairing.py` (oracle simplified to pure geometry, test
      rewritten), `test_book_export_interior.py` (reserve term dropped),
      `test_book_pdf_memory.py` (reserve helper removed; baseline
      regenerated), `test_book_page_numbers.py` (two-up folio-omission
      carve-out correctly reinstated — the baseline Duck+Owl pair is
      page-fit-bound on width, natural slack 0, folio omitted again, as it
      was before Fix 1 ever existed), `test_book_puzzle_frame.py`/
      `test_book_pdf_two_up.py` (shift logic dropped from expected-geometry
      helpers).
    - **Baseline fixture:** `tests/fixtures/book_baseline_card204.json`
      regenerated in place — only interior page 5 moves, `interior_bytes`
      3440674 → 3439483 (a -1191-byte reversion to the exact pre-Fix-1 value,
      confirming the fix is a true behavioral reversion to "no reserve",
      not a new, different behavior).
    - **Test evidence:** six touched files together 169 passed, 1 skipped
      (pre-existing, unrelated), 0 failed; `test_layout_two_up.py` +
      `test_book_two_up.py` + `test_book_arrange_page_breaks.py` +
      `test_book_qr_slot.py` all green; `pytest tests/ -k "book"` exit 0,
      [100%], no FAILED. **Full suite: 6854 passed, 9 skipped, 0 failed, 0
      errors** (986.13s) — identical pass count to Fix 2's own full-suite run,
      consistent with this being a net code simplification (10 files,
      +353/-668) rather than new functionality.
    - Re-verified unaffected: MIN_CELL_MM floor-overflow (`compute_layout`'s
      single-page branch untouched by any fix); the QR slot's own
      gutter-first/below-fallback/omit rule (never coupled to the folio
      reserve in the first place).

  - [Fix 4, 2026-10-13] Owner decision of 2026-10-12 — **"fixed universal
    reserve"** — implemented, closing cycle-3's F-7 escalation. This was a
    *recovery* run: Fix 4 was found UNCOMMITTED in the worktree (9 files,
    +706/-296, HEAD at Fix 3's notes commit `3831bb5`), written but never
    verified by anyone. Verified it against the owner decision in full, kept
    it (it is sound — not rewritten for taste), and closed the four gaps it
    still had. Everything below is measured, not inferred.

    **What the uncommitted work already did (verified correct, kept).**
    `compute_pair_layout` regains a kw-only `folio_reserve_px: int = 0` and
    `_slot_layout` an `outer_reserve_px: int = 0` (lower slot only). The fit
    is taken *unreserved* first; only when the **lower** slot's own natural
    spare at that cell reads below the reserve is the cell re-fit against a
    usable width `folio_reserve_px` narrower (a widened `outside_mm` fed to
    the fit step alone, never to either slot's placement), which guarantees
    algebraically that the committed cell leaves the lower slot at least the
    reserve of real headroom; below `TWO_UP_MIN_CELL_MM` it still declines.
    `_slot_layout` then keeps `reserved = min(outer_reserve_px, max(spare,
    0))` out of the flush shift, so the outer corner carries exactly that
    gap. The value comes from `book_pdf_generator._folio_reserve_px(dpi)` —
    the widest decimal digit this font draws (all ten measured, not assumed)
    times the new `FOLIO_RESERVE_DIGITS = 4` constant, `math.ceil`'d: **108 px
    at 300 DPI** (27 px/digit × 4). `puzzle_pages` passes it on every
    `compute_pair_layout` call; `puzzle_section` needs no reserve plumbing at
    all any more.

    **(a) The verdict and the cell are the pair's geometry plus one constant.**
    `_folio_reserve_px` takes only `dpi`, and `BookPDFGenerator.__init__`
    sets `self.dpi = DPI` unconditionally (read, not assumed —
    `book_pdf_generator.py:2608`), so the function returns the identical
    integer for every call this codebase can make: no `page_number`, no
    `max_page_number`, no `payloads`, no page count reaches it. Inside
    `compute_pair_layout` the only inputs are the two clue sets, the
    `PageSpec` and that integer — the same category as `TWO_UP_MIN_CELL_MM`.
    Measured, not argued: a 900-case seeded sweep of random pair geometries
    on Book 1 (both parities, reserve 108) produced **0** verdict
    disagreements and **0** cell disagreements between ODD and EVEN, and the
    committed gap was exactly 108 px in all 167 pairs that paired. The new
    corpus property test below pins the same thing permanently over 1500
    random specs × 2 fixed reserves.

    **(b) Every two-up page keeps its folio room.** The baseline book's own
    Duck+Owl pair (interior page 5, the pair that lost its folio before):
    `usable_right - drawing_right` moves from `0` to `108` px on the ODD
    page and `drawing_left - usable_left` from `0` to `108` on the EVEN one,
    with the committed cell unchanged at 7.5 mm (height, not width, binds
    this pair) — so the folio glyph is the only new ink. `_draw_folio`'s
    clearance test is `content_right <= right - font.getlength(text)`; the
    font measures `"9999"` at exactly 108.0 px, so the fixed reserve covers
    every page number up to 4 digits inclusive, with the 4-digit case
    landing exactly on the `<=` boundary (measured all ten digits: 27.0 px
    each; `"5"` 27, `"99"` 54, `"888"` 81, `"9999"` 108, `"10000"` 135 —
    beyond the owner's stated ceiling and correctly degrading to the
    pre-existing omit-rather-than-collide path).

    **Proof that the same pair pairs identically whatever the book's scale or
    the page number** (direct execution against `puzzle_pages`, the
    production walk, not the unit function): the same Duck+Owl pair, offered
    early and late in books of 2 / 3 / 8 / 100 / 602 puzzles, lands on
    interior pages 3, 3, 4, 6, 52 and 303 — 1-, 2- and 3-digit folios — and
    in every single case `paired=True`, `cell_mm=7.500000000000000` and the
    reserved gap `=108`. Nothing in the digit-count column predicts anything.
    The borderline case is covered the other way round in
    `tests/property/test_book_pairing.py`: a 24-column pair pairs at the
    identical reserve-shrunk `7.0973461538461535` mm in all three regimes,
    and a tighter 25-column pair (whose unreserved cell is 7.1731 mm, but
    6.8345 mm once the fixed 9.144 mm reserve is subtracted) is refused in
    **all** three regimes — the invariant holds in its "always refuses"
    shape too, which is the shape F-1/F-5 broke.

    **What the fixed reserve actually costs, measured (owner-visible).** On a
    900-case seeded sweep of random pair geometries (5-30 cells per side,
    clue depths 1-3) on Book 1's own trim, of the 176 pairs that pair
    *without* a reserve: **152 (86%) keep the identical committed cell**, 15
    (8.5%) pay a slightly smaller one, and **9 (5%) are refused where they
    would otherwise have paired**. That last column is the inherent price of
    the owner's decision — a reserve that is allowed to decide the verdict at
    all can refuse a pair — but it is now in the same category as
    `TWO_UP_MIN_CELL_MM`: the refusal depends only on the pair's own geometry
    and one compile-time constant, so it is identical in every book and on
    every page, which is exactly what F-1/F-5 were not. (The sweep is
    deliberately adversarial: real book puzzles mostly pair at the 7.5 mm cap,
    where the reserve changes nothing — the baseline book's own Duck+Owl pair
    is one such case.)

    **Four gaps in the uncommitted work, found and closed by this run.**
    1. `tests/test_book_pdf_memory.py` was not in the uncommitted set at all,
       and its two `_reference()` helpers plus `_qr_boxes()` still built their
       comparison geometry by calling `compute_pair_layout` **without** the
       reserve. The suite passed anyway — i.e. the comparison was *tolerating*
       a real 108 px displacement of production's own lower slot instead of
       checking it (and masking the QR icon at the wrong x). All three now
       pass `_folio_reserve_px(generator.dpi)`, exactly as Fix 1/Fix 2's own
       versions did, so the reference is production's geometry again. Still
       green, now honestly.
    2. **No corpus-wide test pinned the reserve's *universal* nature** — the
       one thing F-7 gated this card for. Added
       `test_PropertyTest_BookTwoUp_LowerSlotKeepsTheWholeFixedReserve`
       (`tests/property/test_book_two_up.py`): 1500 random specs × two
       *different* fixed reserves (27 and 108, so a formula that only works
       for one magic number cannot pass), asserting per case that the lower
       slot's outer-corner gap is **exactly** the reserve (not "≥ 0", not
       "usually"), that the upper slot is still dead flush, that ODD and EVEN
       agree on both verdict and cell, and that the cell equals an
       independently re-derived expectation (`_expected_shared_cell_mm` of
       either the plain spec or a spec the reserve narrower). It asserts its
       own minimum case counts (≥200 pairs per reserve, ≥20 cases that
       actually take the re-fit branch) per CLAUDE.md, so the corpus cannot
       silently shrink. **Mutation-checked**: forcing `reserved = 0` in
       `_slot_layout` fails this test plus three in
       `tests/test_book_page_numbers.py` (including the restored corpus-wide
       AC-1 folio test) — the tests do pin this cycle's own change.
    3. `compute_pair_layout` could **raise** instead of declining for a
       reserve at least as wide as the usable area (`replace(outside_mm=…)`
       then builds a `PageSpec` with a negative usable width, which `PageSpec`
       rejects with its own `ValueError`). Unreachable from production (one
       fixed ~9.1 mm constant), but it breaks the function's "return `None`
       when the geometry does not work out, never raise" contract for a
       *fixed* value a caller may legitimately pass. Guarded (declines) and
       pinned by
       `TestPairLayout_RefusesSpecsThatNeverPair::test_a_folio_reserve_wider_than_the_page_is_none_not_an_error`.
    4. Two stale/dead pieces of documentation, both of the kind F-7 itself was
       about: `tests/fixtures/book_baseline_card204.json`'s
       `interior_bytes_note` still described **Fix 2's** figures (3440674 /
       +895 / "54 px, this book's own 2-digit worst-case bound") under Fix 4's
       own byte count — rewritten to state Fix 4's actual numbers and to say
       explicitly that the figure is no longer a per-book measurement; and
       `tests/property/test_book_pairing.py`'s `_RESERVE_PX = 108` was
       defined but never used, even though both hand-derived expected cells
       in that file are computed from it — now asserted against
       `_folio_reserve_px(DPI)` at the top of the test, so a font whose
       widest digit measured differently fails in one readable line instead
       of as an obscure `cell_mm` mismatch. `FOLIO_RESERVE_DIGITS`'s own
       comment also claimed CON-018's trims leave a book's page count
       "several orders of magnitude under four digits", which is simply not
       true of a ~120-page book — reworded to the accurate claim, plus what
       actually happens past 9999 pages (the five-digit folio does not clear
       `_draw_folio`'s own width check and is omitted, the pre-existing
       behaviour, not a crash).
       Also documented (not changed) why
       `test_two_up_page_omits_the_folio_when_the_lower_slots_corner_has_no_room_either`
       still builds its pair with `folio_reserve_px=0`: it is now a
       deliberately synthetic layout kept to keep `_draw_folio`'s defensive
       branch covered, since no page a real book prints reaches it any more.

    **No test was narrowed, and the carve-out F-7 flagged is gone.**
    `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber::test_every_page_of_a_book_holding_one_of_every_kind_is_numbered`
    is corpus-wide again (`set(folios) == set(range(1, drawn + 1))`, no
    `- {two_up_page}` exception), and Fix 3's
    `test_two_up_page_s_folio_is_once_again_always_omitted` is replaced by
    `test_two_up_page_s_folio_now_has_reserved_room`, which pins the exact
    reserved gap on **both** parities and that the folio is actually drawn,
    plus a new
    `test_the_fixed_reserve_is_identical_across_book_scales` that runs the
    same pair through a 2-puzzle and a 1202-puzzle book (3-digit folios) and
    asserts the identical gap. Every expected-geometry helper that had its
    reserve term stripped by Fix 3 re-derives it again independently, in
    millimetres, in each test module
    (`test_book_export_interior.py`'s `_expected_drawing_left_mm`/
    `_shared_cell_mm`, `test_book_puzzle_frame.py`'s `_expected_pair_boxes`/
    `_shared_cell_mm`, `test_book_pdf_two_up.py`'s `_reference_band`
    `shift_px`, `test_book_pairing.py`'s `Sheet.shared_cell_mm(reserve=True)`
    oracle) — never by importing `compute_pair_layout`.

    **Baseline fixture.** `tests/fixtures/book_baseline_card204.json`
    re-recorded in place (fourth revision of this card's own fixture, same
    filename, same convention): **`interior_bytes` 3439483 → 3440084,
    +601 bytes**, and exactly one page digest changes (interior page 5, the
    two-up page) — the +601 is page 5's folio glyph drawn again, since the
    pair's committed cell does not move. Pages 1-4 and 6-13,
    `font_fingerprint` and `font_dependent_pages` are byte-identical to
    Fix 3's recording. `proof_baseline_card204.json` needs no change (proof
    pages never call `compute_pair_layout`; `tests/test_book_proof_pages.py`
    re-run green against it).

    **Test evidence.**
    - `tests/property/test_book_two_up.py` — 8 passed (incl. the new
      corpus-wide reserve property test).
    - `tests/test_layout_two_up.py` — 30 passed (incl. the new decline-rather-
      than-raise contract test).
    - `tests/property/test_book_pairing.py` — 3 passed (900-case oracle with
      the reserve, plus the scale-regime sweep).
    - `tests/test_book_page_numbers.py`, `tests/test_book_pdf_two_up.py`,
      `tests/test_book_puzzle_frame.py`,
      `tests/property/test_book_export_interior.py` — 127 passed together.
    - `tests/test_book_pdf_memory.py` — 40 passed, 1 skipped (the
      pre-existing, unrelated font-fingerprint carve-out), with the
      corrected reserve-aware references.
    - `tests/test_book_qr_slot.py`, `tests/test_book_proof_pages.py`,
      `tests/test_book_pdf.py`, `tests/property/test_book_layout.py`,
      `tests/property/test_book_pdf_geometry.py` — 179 passed together,
      exit 0 (the QR slot's gutter-first rule is unaffected by the lower
      slot's 108 px shift, confirmed rather than assumed).
    - **Full suite from the worktree (`pytest -p no:warnings -rf`):
      **6857 passed, 9 skipped, 0 failed, 0 errors** in 1037.45s
      (0:17:17), exit 0 — three more than Fix 3's own 6854, which are
      exactly the three tests added above.

- [Review] cycle 4/3+1 complete 2026-10-13 — **score 8.5** (cycle 3: 4.0, so
  +4.5; clears `min_score: 8`). 0 Critical, **1 Important**, 4 Minor. Report
  synced: `meta/review/20261013T111113Z-CARD-204-cycle4.yml`.
  **The family question is answered: Fix 4 escapes F-1/F-5/F-7 on the coupling
  half.** The reviewer's distinction, which is the one that matters for the
  record: F-1/F-5 were never about the reserve's size but its *provenance* —
  both measured it off the artefact being laid out (this page's number, this
  book's worst-case page count), which made pairing circular (pairing decides
  page count decides reserve decides pairing) and made the same pair get
  different verdicts in different places. A compile-time constant has neither
  property. Verified independently of the fix agent: one production call site,
  no page/book/payload path into the reserve argument; 900 random pairs x both
  parities with 0 verdict and 0 cell disagreements; 1800 adversarial pairs with
  the lower-slot gap exactly 108 px and the upper slot exactly flush every
  time; and the headroom guarantee proven algebraically tight (if
  `natural_spare < R` the re-fit is necessarily width-bound, so `spare == R`
  exactly).
  Mutation check RAN (not deferred): 5 mutants, 4 killed, 1 survived (F-11).
  All mutations reverted from byte-exact captures; `git diff f496bf5` empty.
  System contract: 56 rules, 11 holds, 45 unchecked, 0 violated. Card
  guardrails G-1/G-2/G-3/G-4/G-6 hold; **G-5 violated** (see below).
- [Severity gate] 2026-10-13 — **BLOCKS merge**: one Important finding remains
  (F-9), although the score clears the threshold. The remaining work is
  declarative only — the reviewer's explicit recommendation is that a fix agent
  **must not touch** `compute_pair_layout`, `_slot_layout` or
  `_folio_reserve_px`: four cycles of churn on that mechanism ended correctly,
  and F-9 asks for what was decided to be written down, not decided again.
  **F-9, in full:** FR-040's clause is bidirectional ("when, *and only when*
  ... both fit at one shared cell of at least 7.0 mm. The shared cell is *the
  largest cell*...") and EC-027 states a puzzle that *could* pair is "never
  left alone ... for every order, not only the measured examples". Fix 4
  falsifies both: ~5% of pairs that fit at >= 7.0 mm are now refused, and ~9%
  commit a smaller-than-largest cell. The suite itself pins a production
  counterexample (`_tight_pair`: two 25x6 depth-2 puzzles, unreserved cell
  7.1731 mm, asserted `pair is None` through `puzzle_pages`), and mutant M5
  proves EC-027's own oracle was updated to match the code — i.e. the drift was
  absorbed rather than declared. Four gaps, none of them code: (1) FR-040 /
  AC-242..249 / EC-027 unamended with no architect-station deferral recorded,
  unlike this card's own F-4 precedent for FR-032; (2) card guardrail G-5 still
  reads "does not change which puzzles pair"; (3) `layout.py:1918-1965`'s
  docstring omits the refusal cost and claims refusals happen "exactly as the
  unreserved path already would be"; (4) the owner-visible consequence is
  stated nowhere.
- [Owner-visible cost, measured twice independently] 2026-10-13 — the reserve
  refuses ~5% of pairs that would otherwise pair (reviewer: 10/193; fix agent:
  9/176) and shrinks the cell on ~9% more. Fewer two-up pages means a LONGER
  interior: more pages, and on KDP more pages means a higher print cost per
  copy. That consequence is not recorded in any layer of the model, and the
  owner made the 2026-10-12 "fixed universal reserve" decision without this
  measurement in hand — it did not exist until this cycle. Routed to the owner
  before merge.

- [Decompose station] 2026-10-13 — guardrail **G-5 amended** (see the Guardrails
  section) to record that the owner's 2026-10-12 reserve decision superseded its
  "does not change which puzzles pair" clause, and that the owner reaffirmed it on
  2026-10-13 with the measured ~5% refusal cost in hand ("it stands — 4 digits").
  The binding half of G-5 — geometry + one compile-time constant, nothing page- or
  book-derived — is unchanged and still holds. This closes F-9's gap (2).
- [Architect-station deferral, recorded 2026-10-13] F-9 gaps (1): **FR-040's
  "and only when" clause, AC-242..249 and EC-027 are now FALSE of this
  implementation** and must be amended at the architect station, not here (kanban
  cards only read `meta/architecture/`). The deltas needed: FR-040's bidirectional
  clause must admit the fixed folio reserve as a second refusal reason and drop
  "the largest cell" as an absolute; EC-027's "never left alone … for every order"
  must carry the same exception; and EC-027's oracle change (mutant M5 proved it
  load-bearing) must be declared rather than absorbed. Owner decision 2026-10-13:
  close this card on the doc-only fix and carry the requirements delta as an
  explicit deferral — the same precedent this card already set for F-4/FR-032.
  **Route: `/forge:architect` (delta on requirements.yml), folding F-4 and F-9
  into one pass.** Both are listed in the card's own notes; neither blocks merge
  by owner decision.
- [Fix 5] 2026-10-13 — doc-only cycle spawned (owner decision: "doc-only cycle 5,
  then merge"). The fix agent is forbidden from touching `compute_pair_layout`,
  `_slot_layout` or `_folio_reserve_px` — the reviewer's explicit recommendation
  after four cycles of churn on that mechanism ended correctly. No code change, no
  full-suite re-run.

- [Merge gate] 2026-10-13 — **FAILED: 4 failed, 6871 passed, 9 skipped** on the
  merged tree (branch + main). This is the integration CARD-204's own suite could
  never see: CARD-203 (solved-page caption right-aligned to `drawing_right`,
  merged to main AFTER this branch was cut) meets CARD-204 (the drawing flush to
  the outer margin).
  1. **A real defect, not a stale expectation —**
     `test_book_solved_page.py::TestBookSolvedPage_CaptionMovedCloserToTheDrawing::test_the_caption_is_still_strictly_inside_the_usable_area`:
     on an EVEN page the caption's leftmost ink lands at column **111** against
     `usable_left = 113` — the caption **overhangs the usable area by 2 px**.
     Mechanism: CARD-203 right-aligns the caption at `drawing_right`; a caption
     wider than its own grid therefore extends left past `drawing_left`. While
     the drawing was centred that overhang fell into the page's spare and stayed
     inside the usable area; with CARD-204's flush alignment `drawing_left ==
     usable_left` on an even page, so it crosses the boundary. Ink in the trim
     margin is a print defect.
  2-3. `TestBookPdfMemory_PagesAreUnchanged::test_every_page_is_pixel_identical_to_the_recorded_one`
     and `::test_the_interior_file_is_the_length_it_was_recorded_with`: interior
     page 11's digest differs from `book_baseline_card204.json`, because that
     baseline was recorded in this worktree BEFORE main's CARD-203 arrived, so it
     carries no caption move.
  4. `TestBookPdfMemory_NonDrawingPagesAreByteIdentical::test_the_toc_and_every_divider_still_match_the_card200_baseline`:
     asserts page 11 "carries no drawing, so CARD-204 must leave it
     byte-identical to the CARD-200 baseline" — now false, and **attributed to
     the wrong card**: page 11 moved under CARD-203, which is already on main.
     AC-7a's wording inherits the same mis-attribution.
- [Process failure, mine] 2026-10-13 — **I merged this branch into main before
  reading the gate result, and had to undo it.** The background suite command
  ended with `tail`, so the harness reported the SHELL's exit code (0), not
  pytest's; and I put `tail` and `git merge` in a single command, so the merge ran
  regardless of what the tail showed. Merge commit `2adc11f` was created on main
  and then removed with `git reset --hard 6ed3749`; the branch was untouched, no
  other commit intervened, and nothing was pushed. Main is back at `6ed3749` and
  verified green-by-construction (it is the pre-merge tree). Corrected practice
  for the rest of this run: the suite's own exit code is written INTO the log as
  its last line, and reading the log is a separate command from any merge.

- [Notes recovered 2026-10-14] pulled one-way from the worktree copy after a
  `git reset --hard` in the main repo discarded this card's uncommitted
  bookkeeping (see the incident note below). Agent-authored content, verbatim:

  - [Fix 7] 2026-10-14 — **merge-gate cycle on the merged tree (branch + main's
    CARD-203). Code + test + baseline; not a doc cycle.** All four gate failures
    fixed, and the first of them was misdiagnosed in the gate entry — the
    correction is the first thing below, because it changes what the "real defect"
    is. (That `[Merge gate]` entry lives in the main repo's working copy of this
    card, which this worktree copy predates; I did not edit the main repo. The four
    failures it lists are quoted where each one is answered below.)

    **1a. What the failing AC-3 test was actually failing on — not the caption.**
    `test_the_caption_is_still_strictly_inside_the_usable_area` scanned the WHOLE
    slack band (`drawing_bottom` .. `usable_bottom`, full page width) for dark
    columns and required every one of them to sit inside
    `[usable_left, usable_right]`. The ink it found at column 111 against
    `usable_left` 113 is **the drawing's own bottom border rule**, not the
    caption: `_stroke_drawing` strokes the grid's heavy outer border centred on
    the boundary, so it overhangs the drawing's edges by about half a rule — 2 px
    — and the band's first rows are that overhang. Measured on the failing page:
    the border's ink runs columns 111..1444, the caption's runs columns 986..1398,
    i.e. 127 px clear of `usable_left` on the inside. The same 2 px bleed is
    already documented and tolerated by this card's own twin test
    (`TestBookSolvedPage_CaptionReadsThePictureName::test_the_caption_is_drawn_inside_the_usable_area_only`,
    `bleed = 2`, with a comment saying CARD-204's flush edge makes it reachable);
    CARD-203's AC-3 twin arrived from main without that tolerance and never met
    the flush drawing until the merge. So failure 1 is a **test-partition defect**:
    the test's band includes ink the test's own claim is not about. Fixed by
    splitting the band — the drawing's border rows keep AC-5's documented 2 px
    bleed, and the caption's own rows (everything below the overhang, where the
    caption and the folio are) keep the strict claim with **no** tolerance at all,
    which is stronger than copying AC-5's blanket tolerance would have been. The
    narrowing trick is the one the sibling test in the same class already uses
    (`overhang = 5`).

    **1b. The real defect the gate entry described is nonetheless real — just not
    what that test catches, and it is now fixed and pinned.** CARD-203 right-aligns
    the caption at `placement.drawing_right`; a caption **wider than its own grid**
    therefore extends left past `drawing_left`. A caption is as wide as the
    picture's name — free text from the Arrangement step, nothing bounds it — while
    a grid is as wide as the puzzle, so the two are not ordered. While the drawing
    was centred the overhang spent the page's own horizontal spare; with this card's
    flush alignment an EVEN page has `drawing_left == usable_left`, so it crosses
    into the trim margin. Measured before the fix, on the same 10x10 cap-bound
    shape the AC-3 test uses: a 65-character picture name (caption 1705 px against a
    1328 px drawing) puts the caption's leftmost ink at column **0** against
    `usable_left` 113 — 9.6 mm into the margin and running off the page edge — and a
    133-character name (caption 3032 px, wider than the 2287 px usable area itself)
    does the same on the ODD page too. The corpus never produced it: this book's four
    captions measure 321-459 px.

    **The fix, and what it is not.** `export/layout.py` gains `caption_slot(layout,
    text_width) -> CaptionSlot | None`, a third additive measurement over an
    already-computed `Layout` beside `header_band` and `qr_slot` (same shape, same
    ADR-0036/R2 reason: the renderer measures its own text because only it knows the
    face; where that width may sit is COMP-007's call). It reports the caption's box:
    `right` is `drawing_right` whenever the text fits between that edge and
    `usable_left` — every caption a real book prints, so CARD-203's right-alignment is
    bit-for-bit untouched — and is pushed right by **exactly** the overhang and no
    more when it does not, so an over-wide caption's left edge lands *on*
    `usable_left`. `measure` is the usable width, and a caption wider than that (no x
    keeps it inside) is clipped to it by the renderer with `_clipped_to`, the TOC's
    own ellipsis loop, extracted unchanged from `create_toc_page` and now shared with
    the caption (the TOC's bytes are unmoved — baseline page 3 is still byte-identical
    to CARD-200's recording, which is the proof). `compute_pair_layout`, `_slot_layout`
    and `_folio_reserve_px` are untouched, as required. `_draw_solved_slot` now reports
    the clamped right edge back to `solved_puzzle_page`, so CARD-203's own
    caption-vs-folio collision check sees where the caption really is.

    **Rejected, with reasons.** (a) *Shrink the caption's type to fit its grid* —
    **not available at all**, not a judgement call: `ANSWER_TEXT_FONT_MM` is literally
    `10 * 25.4 / 72`, i.e. CON-020's 10 pt floor for reader-facing interior text, and
    `TestBookSolvedPage_TextHoldsTheTenPointFloor` asserts it; any shrink violates
    CON-020 on the first pixel, so there is no "floor that might bind" to check — the
    caption is already standing on it. This is also why no owner decision is needed
    here: the option that would have required one does not exist. (b) *Truncate every
    over-wide caption* — rejected as the primary fix (a clipped picture name on the
    answer page the reader turned to is worse than a shifted one), but kept as the last
    resort for the one case geometry cannot answer, where the alternatives are clipping
    or printing in the margin. (c) *Pull the drawing itself in by half a rule so no ink
    ever leaves the usable area* — rejected: it re-opens this card's accepted flush
    formula, moves every drawing page and every geometry expectation in the suite, and
    the 2 px border bleed it would remove is a decision this card already took and
    documented (AC-5's `bleed = 2`). (d) *Left-align the caption on EVEN pages* —
    rejected: it discards CARD-203's shipped decision on every page instead of only
    where the margin forces it.

    **The new test, and its pre-fix failure.**
    `tests/test_book_solved_page.py::TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin`
    — both parities, both regimes (wider than its grid, wider than the whole usable
    area), the premises asserted so they cannot go vacuous, the clamp's exactness
    pinned (left edge on `usable_left`, not merely inside), the parity asymmetry pinned
    (the same caption needs no clamp on an ODD page, whose flush edge is the other
    one), the clip pinned on the drawn string itself ("Puzzle N" survives, the name
    loses its tail), and a negative control that a book-length caption is neither
    clamped nor clipped. **Pre-fix: 8 of its 13 tests fail** (`git stash` of the two
    source files only, test file kept): both `no_caption_ink_leaves_the_usable_area`
    parity x regime cases that can reach the margin, all three clamp-exactness cases,
    and both clip cases; the premises and the negative control pass, as they must.
    Plus `tests/test_layout_page_spec.py::TestCaptionSlot_NoWidthEverLeavesTheUsableArea`
    — the geometry's own total claim, swept over 4 shapes x 2 parities x 13 widths
    (104 cases, count asserted) from -10 px to 20000 px, including the page-fit-bound
    30x30 where the flush edge and the margin coincide: no width on any shape or parity
    yields a box outside the margins.
    Plus the **packed** half of the same claim, which is not a duplicate of the
    full-page one:
    `tests/test_book_solved_answer_key.py::TestBookSolvedAnswerKey_PackedCaptionWiderThanItsTileStaysInside`.
    A packed slot's `PagePlacement` carries its **tile's** box as the usable area
    (`_packed_tile_layout`), and a tile is half a page wide, so an over-wide caption
    is both likelier there and bounded by a different rectangle — and
    `_draw_solved_slot` must ask `caption_slot` about the *slot* it was handed, not
    the page. Measured pre-fix on both parities: the packed caption's ink starts at
    column 0 against a tile whose `usable_left` is 113, i.e. 113 px outside its own
    tile and across the gutter. **Pre-fix: 2 of its 6 tests fail** (both
    `no_caption_ink_leaves_the_tile` parities); its premise and negative-control
    tests pass, as they must. Post-fix: 6 passed. A future edit that handed
    `caption_slot` the whole page instead of the slot fails here while every
    full-page test stays green.

    **2. Baseline re-recorded (`tests/fixtures/book_baseline_card204.json`, fifth
    revision in place, same filename and convention).** `interior_bytes` 3440084 ->
    3441912 (+1828), and **exactly three page digests move: 11, 12 and 13 — all three
    under main's CARD-203, none under Fix 7.** They are this book's three
    caption-drawing pages (Duck+Owl packed, Tree packed alone, Snowflake full), and
    CARD-203 right-aligns their caption and lifts it to a fixed 2 mm gap. The
    attribution is measured, not asserted in prose: the recorder script verified
    before writing that those three pages now equal `book_baseline_card203.json`'s own
    digests exactly and differed from the Fix 4 recording, and the +1828 bytes are the
    identical delta CARD-203's own recording added over CARD-200's on this same book
    (3420073 -> 3421901) on main, with none of this card's changes present. **Fix 7's
    own change moves no page of this corpus**: the clamp fires only above a caption
    width this book never reaches, and the export is byte-identical with and without it
    (3441912 either way, measured both ways) — so this fixture is deliberately NOT the
    clamp's evidence; the new test class above is. Pages 1-10 are byte-identical to the
    Fix 4 recording; `font_fingerprint` (reproduced on this machine first) and
    `font_dependent_pages` are unchanged. `interior_bytes_note` rewritten — it had
    still described Fix 4's figures. No earlier fixture touched, none deleted;
    `book_corpus.py`'s chain comment carries the new bullet, and its two contradictory
    leftover count lines ("thirteen"/"twelve") are now one accurate line (fourteen
    files, since CARD-203 joined the chain between this card's Fix 4 and Fix 7).

    **3. The mis-attributed expectation, repartitioned.**
    `TestBookPdfMemory_NonDrawingPagesAreByteIdentical` claimed all eight non-drawing
    pages "carr[y] no drawing, so CARD-204 must leave [them] byte-identical to the
    CARD-200 baseline". False of pages 11-13 and blaming the wrong card. Fixed by doing
    **both** honest repairs, because each alone leaves a hole: `STRICTLY_UNCHANGED_PAGES`
    is now the TOC and the four dividers (3, 4, 6, 8, 10), which still owe CARD-200
    byte-identity and still deliver it (0 px differ); a new `CARD203_CAPTION_PAGES`
    (11, 12, 13) owes the same strict digest identity to `book_baseline_card203.json`,
    the last recording taken before this branch's changes and the first that holds the
    caption move (new `test_the_three_answer_pages_still_match_the_card203_baseline`,
    with an assertion that none of those pages is machine-lettered, so the comparison
    needs no face gate); and the attribution itself is now measured by
    `test_the_three_answer_pages_moved_under_card203_not_this_card` — those pages
    differ from CARD-200 *and already differed in CARD-203's own recording*, which is
    what makes "CARD-203 moved them" a fact about the fixtures. Dropping them from the
    comparison was rejected (a page nobody compares is a page with no evidence). The
    class's partition-completeness assertion is kept and strengthened (the union covers
    every baseline page, and the group sizes sum to the page count, so no page can sit
    in two groups), and both negative controls are kept
    (`test_every_drawing_page_actually_moved` for 5/7/9, the guide-page scatter bound
    for 1/2).

    **AC-7's wording — needs amending, but not for the reason the gate entry gave.**
    AC-7 already excludes answer pages by its own text ("every page that is not a
    puzzle/two-up/answer page (the guide, dividers)"), so CARD-203's caption move does
    **not** falsify its scope — the mis-attribution was entirely in the test, which had
    silently widened the AC to pages 11-13. What AC-7 does still get wrong predates
    Fix 7: it promises byte-identity for "the guide, dividers" when the two guide pages
    are a known, measured exception (the sub-pixel scatter), and the test it names
    asserts they *differ*. Proposed amendment, for the decompose station: *"**AC-7**
    (negative, byte-identity elsewhere): Given any book, when the TOC and every divider
    page — the pages that carry neither a drawing nor a caption — are compared against
    `book_baseline_card200.json`, then each is byte-identical. The two guide pages are
    the documented exception: they borrow `compute_layout` only for their worked
    examples' cell pitch and rule widths, and differ by a bounded sub-pixel scatter
    only (AC-7b). The three answer pages are outside this AC: this card moves nothing on
    them, and main's CARD-203 moves all three, so their byte-identity is owed to
    `book_baseline_card203.json`."* Separately, **"AC-7b" appears in the test file and in
    this card's Fix 6 notes but was never written into the Acceptance criteria section** —
    the owner's 2026-10-13 "bound it with a test, then merge" decision should become its
    own AC bullet there.

    **Test evidence.**
    - `tests/test_book_solved_page.py` — 50 passed (13 of them the new class).
    - `tests/test_book_solved_answer_key.py` — the new packed class: 6 passed.
    - `tests/test_layout_page_spec.py` — 110 passed (5 of them the new class).
    - `tests/test_book_pdf_memory.py::TestBookPdfMemory_NonDrawingPagesAreByteIdentical`
      — 6 passed (two of them new).
    - `tests/test_book_pdf_memory.py`, `tests/test_book_solved_answer_key.py`,
      `tests/property/test_book_export_interior.py`, `tests/test_book_toc.py`,
      `tests/test_book_solved_page.py`, `tests/test_layout_page_spec.py` together —
      270 passed, 1 skipped (the pre-existing font-fingerprint carve-out), exit 0.
    - **Full suite from the worktree (`pytest -p no:warnings -rf`): `6901 passed,
      9 skipped in 1227.47s (0:20:27)`, exit 0** (pytest's own exit code written
      into the run's log as its last line, `PYTEST_EXIT=0`, and read in a separate
      command from any other action — the corrected practice this card's own
      process-failure note records).
      **The count reconciles exactly**: the merge gate ran 4 failed + 6871 passed
      = 6875 tests; this run is 6875 + 26, and the 26 are precisely the tests this
      fix adds — 13 (`TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin`)
      + 6 (`TestBookSolvedAnswerKey_PackedCaptionWiderThanItsTileStaysInside`)
      + 5 (`TestCaptionSlot_NoWidthEverLeavesTheUsableArea`) + 2 (the two new
      attribution tests in `TestBookPdfMemory_NonDrawingPagesAreByteIdentical`).
      0 failed, and the 9 skips are the gate's own 9, unchanged.

- [LEDGER RESTORED 2026-10-14] The records below were written during the run, then
  destroyed by the `git reset --hard 6ed3749` described in the incident note above:
  that reset reverted every TRACKED file in the main repo, and this card's bookkeeping
  was uncommitted. Re-authored here from the session's own record and committed
  immediately. The agents' own note blocks were recovered separately from the worktree
  copy (see "[Notes recovered]"). What was lost and is now back: the Fix 5 verification,
  both AC/EC gate verdicts, the merge authorization, the AC-7 split and the G-6
  amendment (the last two re-applied in their own sections above, with Fix 7's improved
  AC-7 wording). **Lesson applied: the ledger is committed as it is written, not held
  uncommitted across a destructive git operation.**
- [Fix 5 verified] committed `1552b06`; both modules' logic byte-identical to `f496bf5`
  with docstrings stripped (AST comparison), so the doc-only constraint held mechanically.
- [AC/EC check, first pass] BLOCKED on two declarative items — AC-7 (guide pages not
  byte-identical, bound only in prose) and G-6 (its "never its size" clause falsified by
  the reserve's cell re-fit). Everything else evidenced over 637 passing targeted tests:
  AC-1..AC-6, AC-8, G-1..G-5, the cross-card CARD-200 AC-1 (corpus-wide again, carve-out
  confirmed gone), CON-019 and ADR-0036/R1.
- [AC/EC check, closed] Both blocking items closed: AC-7b now carries Fix 6's bounding
  assertion (teeth-checked against the exact regression shape the old assertions missed),
  and G-6 was amended at this station with its surviving clause already evidenced.
- [Merge authorized] owner 2026-10-13: "merge both when the fixes land" — the merge
  proceeds on that authority once the gate passes, with the gate itself NOT waived.
- [Fix 7 verified] committed `cb0c206` (8 files, +835/-34, `meta/` clean). Full suite
  **6901 passed, 9 skipped**, with `PYTEST_EXIT=0` written as the log's last line and read
  in a separate command — the corrected practice from the incident note. Count reconciles:
  the failed gate ran 6875 tests, this run is 6875 + 26, and 26 is exactly what Fix 7
  added.
- [Correction, mine] **My diagnosis of the gate's first failure was wrong**, and Fix 7
  corrected it with measurements. I reported that the caption's ink was 2 px into the
  margin. The ink at column 111 is the **drawing's own bottom border rule**, which
  `_stroke_drawing` strokes centred on the grid boundary so it overhangs by ~2 px — a
  bleed this card's own twin test already documents and tolerates (`bleed = 2`), and which
  CARD-203's imported twin lacked. The caption's own ink on that page runs columns
  986..1398, 127 px INSIDE `usable_left`. So failure 1 was a test-partition defect: the
  test scanned a band containing ink its claim was not about. **The defect I described is
  real anyway, and far worse than 2 px** — just invisible to that test: measured pre-fix, a
  65-character picture name puts the caption's leftmost ink at column 0, i.e. 9.6 mm into
  the margin with the remainder clipped off the sheet, and a 133-character name does it on
  the odd page too. This corpus never produced it (its captions are 321-459 px), which is
  why nothing caught it before.

- [Review] cycle 5 (narrow: `aa761f8..cb0c206`, Fix 7 only) — **score 6.5**, risk
  MEDIUM. **1 CRITICAL, 1 Important, 1 Minor. NOT safe to merge.** Report synced:
  `meta/review/20261014T053042Z-CARD-204-cycle5.yml`. This review existed because
  Fix 7 was new production code written after cycle 4 and after the AC/EC gate; the
  merge gate's full suite was GREEN and no test covers what it found.
  **CRITICAL — `book_pdf_generator.py:4181`: a clamped packed caption overprints the
  folio.** Fix 7 told the full-page consumer about the caption's new right edge
  (`solved_puzzle_page` passes `content_right = caption_right`) but not the packed
  one: `_packed_answer_page` still passes `content_right =
  corner_placement.drawing_right`, and its own comment asserts the premise Fix 7 just
  falsified ("the caption's right edge coincides with it"). Packed tiles are CENTRED
  in their tile, so the clamp pushes the caption to the tile's `usable_right`, which
  on the corner column of a right-hand page IS the folio's corner; `_draw_folio` reads
  the stale figure, passes its clearance test, and draws. Reproduced by
  render-minus-reference on **21.59 x 27.94 cm (8.5" x 11", a standard KDP trim)**,
  KDP-min margins, page 9, a capacity-4 packed page of four 10x13 answers with a long
  name: `drawing_right` 2418, `caption_slot.right` 2475 = `frame.right`, folio drawn,
  **40 px of caption ink inside the folio's glyph box**. Short title: 0 px. 4 hits in
  a 6x5x2x21x21 sweep. The fix is one line mirroring the full-page call site, deleting
  the false comment, and a clamped case in the existing collision test.
  **Important — `layout.py:1226`:** the `min(..., usable_right)` stop SURVIVED mutation
  (M3, 224 passed) because the 104-case sweep is all `fits == True` layouts, and the
  stop is production-reachable: a 30x30 on a 10.0/10.16 cm trim at min margins has
  `fits = False`, `drawing_right` 1138 vs `usable_right` 1106, so a 300 px caption that
  fits easily still moves 32 px / 2.7 mm. `layout.py`'s own comment discloses this
  honestly; `book_pdf_generator.py:3751-3756` DENIES it ("the two are the same pixel,
  so CARD-203's right-alignment is untouched"). One `SHAPES` entry + one assertion
  closes it.
  What verified exactly, re-derived rather than inherited: the test-partition
  diagnosis; the real defect's figures (column 0 ink on both parities, 113 px out of a
  packed tile); the clamp arithmetic as total on both parities and for a tile; the
  `_clipped_to` extraction as behaviour-preserving (proved harder than claimed — a
  full corpus export byte-identical pre/post, same sha256); **the baseline
  re-recording's attribution, to the byte** (+1828 == CARD-203's own delta over
  CARD-200; only pages 11-13 moved; Fix 7 moves no page at all, so no regression is
  being blessed); and 10 of the 26 new tests failing pre-fix. CON-019, ADR-0036/R1,
  G-1..G-6 all hold. CON-020's floor literally IS `ANSWER_TEXT_FONT_MM = 10 * 25.4 /
  72`, confirming "shrink the type" was never available and no owner decision was owed.
- [Family regression] 2026-10-14 — `review.family_regression: on`, and this is the
  detector's shape, stated by the reviewer better than the config does: **"the same
  two call sites, the same asymmetry, one card later."** CARD-203 cycle 1 (F-001)
  fixed the caption/folio corner on the full page and missed the packed page; its
  cycle 2 (F-101) fixed the packed page and got the parity gate wrong; Fix 7 fixed the
  caption's right edge on the full page and missed the packed page. Root cause named:
  `_draw_solved_slot`'s return tuple has **two consumers that must be changed
  together, and nothing in the code or the tests says so.** This is the fifth time
  this card's own loop has produced a finding seeded by its previous fix (F-1 -> F-5 ->
  F-7 -> cycle-5 critical). Escalating to the owner rather than spending a sixth
  cycle on reflex: the narrow fix is genuinely one line, but whether to also close the
  family is a judgement about this product's print risk, not mine to take.
- [Correction, mine] I told the owner the caption's ink sat "127 px inside
  `usable_left`", quoting Fix 7's note. The reviewer re-measured: the caption band is
  986..**1438** and 986 is **873 px** clear of `usable_left`, not 127. Immaterial to
  the defect, but it was stated as a measurement and it was wrong.
## System contract

_Not yet assembled — run `python3
~/.claude/plugins/cache/adverax/forge/2026.8.17/skills/architect-validate/scripts/system_rules.py
--card CARD-204 --format md` once the Touches list is stable (after the two owner
mechanism-level decisions above are resolved and this card's Touches list stops
moving); assembling it now against a Touches list this card itself flags as
provisional would produce a System contract section the card's own next revision
would immediately invalidate._
