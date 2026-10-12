
# CARD-204: Puzzle and two-up pages drop FR-032's centred placement for right-alignment, and gain a 2x2cm QR-code slot linking to the (not-yet-public) solver

**Status:** review
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
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/property/test_book_layout.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_two_up.py, tests/property/test_book_workflow.py, tests/property/test_book_export_interior.py, tests/test_answer_page_layout.py, tests/test_book_pdf.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_two_up.py, tests/test_book_puzzle_frame.py, tests/test_book_solved_page.py, tests/test_layout_answer_tiles.py, tests/test_layout_two_up.py, tests/test_export_pdf.py, tests/test_export_image.py, tests/fixtures/make_fixtures.py, pyproject.toml (only if the owner approves a new runtime dependency — see "What to implement" step 2)
**Review score:** 4.0/10 (cycle 2, new gating finding — fix in progress)
**Started:** 2026-10-10T05:08:27Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

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
- **AC-7** (negative, byte-identity elsewhere): *Given* any book, *when* every page
  that is not a puzzle/two-up/answer page (the guide, dividers) is compared against the
  pre-card baseline, *then* it is byte-identical — this card changes horizontal drawing
  placement and adds a QR slot only on pages that carry a drawing.
  *test: TestBookPdfMemory_NonDrawingPagesAreByteIdentical*
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
- G-5: INV-010 (two-up pairing eligibility: same tier, adjacent, both fit at a shared
  cell) is untouched — this card repositions a pair's slots, it does not change which
  puzzles pair.
- G-6: FR-031's 4.8mm floor check and NFR-006's orientation/cap logic are untouched —
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

## System contract

_Not yet assembled — run `python3
~/.claude/plugins/cache/adverax/forge/2026.8.17/skills/architect-validate/scripts/system_rules.py
--card CARD-204 --format md` once the Touches list is stable (after the two owner
mechanism-level decisions above are resolved and this card's Touches list stops
moving); assembling it now against a Touches list this card itself flags as
provisional would produce a System contract section the card's own next revision
would immediately invalidate._
