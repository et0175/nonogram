# CARD-204: Puzzle and two-up pages drop FR-032's centred placement for right-alignment, and gain a 2x2cm QR-code slot linking to the (not-yet-public) solver

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 2.5d
**Complexity:** architectural
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/204-puzzle-right-align-qr
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout1", 2026-10-08 (item 3: "Puzzles - please make them right-aligned and add a small icon for qr code (2*2 cm) with the link for the solver. It can be on the left or on the bottom depending on how the Puzzles are placed"); owner clarification 2026-10-08 via AskUserQuestion — "right-aligned" means a full reversal of FR-032's centred placement (not a narrower QR-icon-only adjustment), and the QR code should be drafted now with a placeholder/TODO link, wired to a real public solver URL once one exists.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/property/test_book_layout.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_two_up.py, tests/property/test_book_workflow.py, tests/property/test_book_export_interior.py, tests/test_answer_page_layout.py, tests/test_book_pdf.py, tests/test_book_pdf_memory.py, tests/test_book_pdf_two_up.py, tests/test_book_puzzle_frame.py, tests/test_book_solved_page.py, tests/test_layout_answer_tiles.py, tests/test_layout_two_up.py, tests/test_export_pdf.py, tests/test_export_image.py, tests/fixtures/make_fixtures.py, pyproject.toml (only if the owner approves a new runtime dependency — see "What to implement" step 2)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**This card cannot be implemented as drafted — two sub-decisions are still open and
are named explicitly below, each with a recommendation.** `Revision pending: true` is
set for exactly that reason: this is a complete, investigated draft, not a stalled one,
but it carries two blocking questions the owner's two AskUserQuestion answers
("full reversal" / "draft the QR now, wire the link later") settled at the *policy*
level without settling the *mechanism* level. Both are flagged under "Owner decisions
still needed before implementation starts" below. Do not start this card's
implementation before they are resolved.

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

## Owner decisions still needed before implementation starts

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

## What to implement (once the above are confirmed)

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

## System contract

_Not yet assembled — run `python3
~/.claude/plugins/cache/adverax/forge/2026.8.17/skills/architect-validate/scripts/system_rules.py
--card CARD-204 --format md` once the Touches list is stable (after the two owner
mechanism-level decisions above are resolved and this card's Touches list stops
moving); assembling it now against a Touches list this card itself flags as
provisional would produce a System contract section the card's own next revision
would immediately invalidate._
