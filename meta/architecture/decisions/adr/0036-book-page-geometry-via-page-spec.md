# ADR-0036: Book page geometry is a page spec passed to compute_layout

**Status:** Accepted
**Date:** 2026-09-22
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-030 requires the book PDF to size each puzzle's cell for the book's own trim and margins. The usable area is the trim minus the outside, gutter, top and bottom margins, minus the 12 mm title band. The cell is computed from the puzzle's real clue depth, capped at the 7.5 mm standard cell, with the top edge at a fixed position and the page always portrait (FR-032, NFR-008, CON-018). FR-031 needs the same per-puzzle cell size on the selection tiles, to flag puzzles below the 4.75 mm floor.

Today COMP-007's `export/layout.py` has one entry point, `compute_layout(row_clues, column_clues)`. It hard-codes A4 with 12 mm margins, NFR-005's comfort-cap curve (9.0 → 6.5 mm) and NFR-006's rule of turning the sheet whichever way prints the larger cell. A guardrail in its docstring (G-1, from the card that built it) says "no second paper size". The admin panel (COMP-009) renders every book page through `export.pdf.render_pages`, so books print on A4 geometry inside an 8.5×11 page.

CON-019 requires the CLI and web UI PNG/SVG/PDF to stay byte-for-byte unchanged. ADR-0007's layering and the import guard in `tests/test_cli.py` allow `admin/` (a rank-0 adapter) to import `export/`, but never the reverse. ADR-0033 keeps Book assembly in CTX-001, so print vocabulary in COMP-007 crosses no context boundary.

## Decision

We will give COMP-007 a `PageSpec` value object and make it an optional parameter of `compute_layout`, whose default reproduces today's A4 behaviour exactly. `PageSpec` carries:
- the page size and the four margins;
- the reserved title band;
- the orientation policy: NFR-006's "larger cell wins", or portrait only;
- the cell-cap policy: NFR-005's comfort curve, or a flat cap.

The book builds a `PageSpec` from its stored trim and margins (CON-018): 8.5×11 in, gutter 0.5 in, outside/top/bottom 0.375 in, 12 mm band, portrait only, flat 7.5 mm cap. The book PDF and FR-031's selection tiles both call the same function with it. The CLI and web UI never pass one.

This keeps one implementation of cell fitting, clue gutters, grid-line placement and the every-5th rule, all of which are already tested. It turns CON-019 into one mechanical guarantee, pinned by a golden-byte test on the default path. The tile's cell size and the PDF's cell size cannot disagree, because they come from the same call. The G-1 guardrail is retired: COMP-007 now knows more than one sheet, but only through an explicit `PageSpec`, never by guessing.

## Alternatives considered

### Book-owned geometry in the admin panel
COMP-009 would compute the cell, gutters and placement itself and hand COMP-007 a finished layout to draw. COMP-007 would publish its drawing helpers (`_gutter_depth`, `_axis_lines`, `_rule_widths`). The A4 path would stay literally untouched. Rejected: it creates a second cell-fitting implementation that must be kept consistent through a cross-check test. It widens COMP-007's public API anyway. And it puts more logic into an adapter that ADR-0007 intends to be thin.

### A sibling entry point in export
`export/book_layout.py` with `compute_book_layout(row_clues, column_clues, page)` would share export's private helpers, leaving `compute_layout` unedited. Rejected: it retires G-1 just the same, and two entry points over one set of helpers can drift in how they place the band and gutters. One function with an explicit default is the smaller surface.

## Consequences

### Positive
- One geometry implementation for the CLI, the web UI, the book PDF and the selection tiles. A fix to cell fitting or line placement reaches all of them.
- CON-019 holds by construction and is proven by a golden-byte test: the default `PageSpec` is today's constants, and the A4 path's output is pinned.
- FR-031's floor check and the printed book use the same numbers, so a tile marked "4.9 mm" prints at 4.9 mm.

### Negative
- COMP-007's contract grows: print-production concepts (gutter margin, flat cap, portrait-only) become `PageSpec` fields, and the shared function carries branches only the book exercises.
- The layout module's docstring guardrail G-1 must be rewritten, and its extensive measurements (A4 sweeps over 441 extents) describe only the default spec. Book-spec behaviour needs its own measured tests.
- `render_pages` and the PDF sink must thread the spec through, so their signatures change too (optional, defaulted).

### Neutral
- NFR-005 and NFR-006 are unchanged for the default spec. The book spec opts out of them explicitly: flat 7.5 mm cap, portrait only. NFR-008 is the book's own range (4.75–7.5 mm).
- ADR-0007 needs no revision: admin → export is already a legal import, and nothing in export learns about the admin panel.
- DEC-039 (what the band shows and the line thresholds) builds on this spec: the title band's height is a `PageSpec` field.

## Clarifications (2026-09-22)

### Two-up pages
FR-040 lets two small puzzles share a page at one shared cell of at least 7.0 mm. COMP-007 gains a pair-aware call that takes both clue sets and the book's `PageSpec`, computes the one cell both slots use, and returns both layouts with their positions on the page. The admin panel still fits no cells itself (R2). A single puzzle keeps using `compute_layout` as above.

### Gutter margin and page count
KDP's minimum gutter grows with page count, and page count depends on the layout. To avoid a loop, the book always lays out with its stored gutter margin; for Book 1 that is 0.5 in, which KDP accepts up to 300 pages. Finalising a book refuses when the actual page count needs a larger gutter than the one stored.

### Mirrored margins
A bound book puts the gutter margin on the binding side: on the left of right-hand (odd) pages and on the right of left-hand (even) pages. The book's `PageSpec` therefore carries the page's parity, and the drawing is centred across the usable width between the two side margins. The top edge stays fixed (FR-032). The default A4 spec has no parity and is unchanged. Parity counts from interior page 1, the guide page, which is right-hand; the cover is exported as a separate file and never counts (FR-043).

## References

- DEC-035 (resolved by this ADR)
- CTX-001; COMP-007 (Export Renderers), COMP-009 (admin panel); CAP-005, CAP-006
- FR-030, FR-031, FR-032, NFR-005, NFR-006, NFR-008, CON-018, CON-019, CON-006
- ADR-0007 (layering, unchanged), ADR-0033 (Book in CTX-001)
- src/nonogram/export/layout.py (`compute_layout`, `_fit_cell`, `_orientation_for`), src/nonogram/export/pdf.py, src/nonogram/admin/book_pdf_generator.py

## History

- 2026-10-17: **The cell floor restated 4.8 → 4.75 mm, decision unchanged** — the
  owner-approved NFR-008 amendment of the same day (CARD-225 owns the requirement; the
  propagation pass that followed carried `requirements.yml`, `aggregates.yml`, CAP-006,
  `glossary.yml` and `trace.yml`). This ADR stated the number in two present-tense places —
  FR-031's tile flag in the Context, and "NFR-008 is the book's own range" in the
  Consequences — and both now read 4.75 mm. **Nothing here was re-decided:** this ADR owns
  *who computes page geometry*, not where the band's ends sit, so a moved endpoint is a
  restatement and not a revision. The 4.9 mm tile example in the Consequences is left as it
  was: it is above both the old floor and the new one, so it still demonstrates the property
  it was written for.
- 2026-10-17: **R3's reach widened, decision and statement unchanged** — CARD-243, the other
  half of the narrowing recorded below. R3's render check read ink at one hard threshold, grey
  128, and the package draws its solved grid at grey 160: a difficulty dot stroked in the book's
  own grey had no region to measure, so the rule's declared check passed green with eighteen
  undeclared grey dots on the pages. Measured twice independently at CARD-241's review (F-001).
  The check now reads at **grey 208** — the midpoint of the gap between the lightest tone the
  package draws and paper, derived from the package's own palette on disk rather than chosen —
  so R3 covers a round mark at any darkness the book prints at, and the *darkness* bound is
  struck from the rule's comment in the same diff that closed the route
  (`test_the_struck_bound_and_the_closed_route_agree`, red in both directions).
  **What that cost, measured rather than assumed:** the book's own margin to the closest
  legitimate mark falls from 1.8855 tolerances to 1.8182 and changes hands from `fill` to
  `aspect`; both tolerances keep their values, because the re-measurement against the wider
  population says so (`fill`'s own room on the book is unchanged at 1.8855 — it was 1.8859 at
  both thresholds until CON-018's amended margins printed the block that sets it one row
  taller, which is a fourth-decimal move and no change of hands). `aspect`'s own room moved
  under those margins too, at the widened threshold only: 47.1809 → **46.5789**, because the
  guide-page rule that sets it is 980 x 95 on the narrowed text block rather than 981 x 94;
  at the black threshold it is **unchanged at 2.2727**, set by a 6 x 11 stem whose ratio the
  page width cannot touch. **Neither tolerance's own value was altered to keep any of this
  green** — `ROUND_FILL_TOLERANCE` is still 0.12 and `ROUND_ASPECT_TOLERANCE` still 0.2 —
  and all four figures are re-derived on the amended margins by
  `test_each_tolerances_own_room_on_the_book_is_measured`. Reading the pages
  at two thresholds rather than one is recorded in `meta/profiling/card-243-two-threshold-cost.md`.
  **What is left open** is one half of a sentence rather than two: a round mark in one of
  CARD-228's six recorded spellings, drawn on a surface nobody renders. Three narrower bounds
  replace the struck one — a tone lighter than grey 208, a colour whose *luminance* is lighter
  (pure yellow reads 226), and ink composited above that tone — and none of them is a tone the
  package draws, which is the difference between this residue and the bound that was struck.
- 2026-10-17: **Rules added (R3, R4), decision unchanged** — CARD-241, which owns the same
  subject as CARD-228 and was asked to decide this. CARD-228 introduced two standing
  constraints on the whole of `src/nonogram/**` and declared both *only inside a test file*:
  exactly one function may put a round mark on a page, and no string literal anywhere in the
  package (docstrings included) may hold a geometric-shape codepoint. Both bind every module,
  the second cannot absorb a drawing module through its one exemption, and neither was visible
  to a reader of the model. They are written down here as R3 and R4.
  **Why here, and the alternative that was rejected:** this ADR is about who owns page
  geometry (R2 already says the admin panel does not place marks itself), so "the page's round
  mark is drawn in exactly one place" is the same decision one level down, and CARD-241's
  Architecture context names this ADR as the candidate. The honest alternative — a new ADR, or
  a CON in `requirements.yml`, on the grounds that a package-wide literal ban is not a
  *geometry* decision — was rejected only as the more expensive move from an implementation
  card, not as the worse home. If the architect station prefers to relocate R4, nothing depends
  on its address: both rules name their own checks.
  **Reach, stated rather than implied** (ADR-0039/R1): R3 is held by two instruments that do
  not contain each other. The static `ast` walk reads every module on disk, including code no
  test renders, and sees four spellings of a round mark; CARD-241's render check reads the ink
  on the pages the book actually renders and is blind to spelling altogether. What is open to
  both is a round mark spelled in one of CARD-228's six recorded ways **and** drawn either on a
  surface nobody renders **or** in ink lighter than the render check's own threshold: that
  check discriminates on *silhouette* alone, so darkness, colour and opacity are open to it by
  construction, and the package already draws the solved grid at grey 160 against a threshold
  of 128. Both halves of that residue are stated in the rule's comment and carry a control;
  closing the grey route is a follow-up card's, not this one's. R4 is about string *literals*:
  a computed string (`chr(0x25CF)`) is
  not one, and is closed by R3's render check instead, because a typed dot is still ink.
  *(The grey half of that residue was closed by CARD-243, recorded above; this paragraph is
  left as CARD-241 wrote it, because it is the record of what that card decided.)*
- 2026-09-22: Created — book geometry is an optional `PageSpec` on `compute_layout`, defaulting to today's A4; layout.py's "no second paper size" guardrail (G-1) retired.
- 2026-09-22: Clarified (owner, same session; FR-040) — two-up pages come from a pair-aware COMP-007 call with one shared cell; the book lays out with its stored gutter margin and finalise checks it against KDP's page-count minimum. Decision unchanged.
- 2026-09-22: Clarified (owner) — margins are mirrored by page parity and the drawing is centred across the usable width. Decision unchanged.
- 2026-09-22: Clarified (owner; FR-043) — parity counts from interior page 1 (the guide page, right-hand); the cover is a separate file and never counts. Decision unchanged.

## Rules

```yaml
- id: ADR-0036/R1
  statement: >-
    compute_layout called without a PageSpec produces exactly today's A4
    geometry; CLI and web output are byte-for-byte unchanged by any
    book-only PageSpec field.
  scope: {code: ["src/nonogram/export/**"]}
  check: {kind: test, ref: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden}
  severity: mandatory
- id: ADR-0036/R2
  statement: >-
    Book page geometry is computed only by COMP-007's layout functions
    (compute_layout, and the pair-aware call for two-up pages) with the
    book's PageSpec; the admin panel does not fit cells or place grid lines
    itself.
  scope: {code: ["src/nonogram/admin/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0036/R3
  statement: >-
    Exactly one function in src/nonogram/** puts a round mark on a page. A
    second one is a defect whatever Pillow call it is written with: four cards
    print the same difficulty glyph, and four slightly different dots cannot be
    fixed once a book is on paper.
  scope: {code: ["src/nonogram/**"]}
  check: {kind: test, ref: test_the_books_own_pages_carry_no_undeclared_round_mark}
  # tests/test_book_difficulty_dots.py (CARD-241, widened by CARD-243). Two
  # instruments, neither inside the other, and the rule is only as wide as
  # their union:
  #   * the ast walk (TestDifficultyDots_HasExactlyOneDrawingSite) reads every
  #     module on disk -- code no test renders included -- and sees four
  #     spellings: an ellipse-family call, an unrecognised draw receiver, an
  #     unrecognised .Draw(...) binding form, a dingbat literal;
  #   * the render check (the TestRoundMarkOnThePage_* classes, named above)
  #     renders the book's interior and asserts every round region on it was
  #     declared by the one drawing site. Blind to spelling, and blind to WHICH
  #     TONE the mark is printed in across the range the package prints at: a
  #     mark begins at grey 208 (round_ink.py's MARK_LEVEL, the midpoint of the
  #     gap between the lightest tone the package draws and paper), so the
  #     solved grid's own grey 160 is a mark and a dot stroked in it is caught
  #     on the real pages it is planted on. What bounds it is SILHOUETTE plus
  #     that one range: it discriminates on a region's shape, and on nothing
  #     about the mark except that some pixel of it reaches grey 208.
  #     Concretely -- every bound carrying a control that fails if the reach
  #     widens, and every verdict derived by execution in
  #     MEASURED_MARK_BOUNDS, which test_each_bound_list_carries_exactly_the_
  #     open_bounds holds this list to:
  #       BOUND: lightness   -- a flat tone at grey 208 exactly; one level
  #                             darker is found, and nothing the package draws
  #                             is on the far side
  #       BOUND: colour      -- luminance, not colour: pure yellow reads 226
  #                             and is missed, pure red reads 76 and is found
  #       BOUND: opacity     -- ink composited to a tone above 208 (alpha 40
  #                             lands at 215 and is missed, 64 at 191 is found)
  #       BOUND: hollow      -- a mark drawn only as rings
  #       BOUND: touching    -- a mark merged with other ink into one region
  #       BOUND: footprint   -- a footprint outside ROUND_ASPECT_TOLERANCE
  #       BOUND: resolution  -- under 7 px across, where the verdict is the
  #                             raster's accident and not monotone in diameter
  #       BOUND: unrendered  -- a surface nobody renders (a cover, a proof
  #                             sheet, a CLI PNG export)
  #     DARKNESS is no longer among them. It was CARD-241's widest bound --
  #     grey 128 was where ink began, the package drew the solved grid at grey
  #     160, and eighteen undeclared grey dots left this check green -- and
  #     CARD-243 closed it. The bound is struck here and in round_ink.py's own
  #     list in the diff that closed it;
  #     test_the_struck_bound_and_the_closed_route_agree is red if either half
  #     ever moves without the other.
  # Open to BOTH: a round mark in one of CARD-228's six recorded spellings,
  # drawn on a surface nobody renders. (Before CARD-243 the second half of
  # that sentence read "or in ink lighter than INK_LEVEL"; that route is
  # closed, and the one unrendered surface is what the union has left.)
  # Stated, not implied (ADR-0039/R1).
  severity: mandatory
- id: ADR-0036/R4
  statement: >-
    No string literal anywhere in src/nonogram/** -- docstrings included --
    holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is
    drawn, never typed: the cheapest way to print a difficulty dot is to append
    a bullet to a header string, and that route bypasses the one drawing site
    and CON-020's type floor at once.
  scope: {code: ["src/nonogram/**"]}
  check: {kind: test, ref: test_no_module_types_a_round_mark_as_a_character}
  # tests/test_book_difficulty_dots.py (CARD-228). One earned exemption
  # (admin/pdf_generator.py's prose bullets) held to an equality against the
  # modules that carry such a codepoint today, plus a second assertion that the
  # exempt module makes no draw-object call -- so it cannot grow to cover a
  # drawing module (ADR-0039/R3, whose own check is that exemption's control).
  # Reach: string LITERALS. A computed string -- chr(0x25CF), a decoded bytes
  # literal, unicodedata.lookup -- is not one and is left to R3's render check,
  # which measures the ink a typed dot leaves and does not care how the string
  # was made. Non-.py assets are outside both.
  severity: mandatory
```
