# CARD-207: A book puzzle page's header splits — "Puzzle 37" flush left, "MEDIUM" flush right, a rule beneath

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/207-split-header-band
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 ("## Puzzle page header — `Puzzle 37                                      MEDIUM` / `─────────────────────────────────────────────────────`")
**Idea:** —
**Wave:** —
**Depends on:** CARD-204
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf_band.py, tests/test_book_pdf.py, tests/test_book_interior_type_floor.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Current behaviour (verified by reading the code).**

- `band_identity(number, stored_tier)` (`book_pdf_generator.py:944`) composes
  **one** line: `"Puzzle 12 · Easy"` (`BAND_SEPARATOR`), or `"Puzzle 12"` alone
  when `tier_of_record` reads no tier off the row.
- `_set_band` (`:1214`) draws that one piece **centred** on the band's
  `center_x`/`center_y` (`export.layout.header_band`), shrinking once if it
  would not fit the usable width. Its docstring is explicit that a one-piece
  header has "no separator to stroke".
- `export.pdf.render_pages` / `_draw_header` is the *other* renderer of a band
  — the single-puzzle CLI/web PDF, which carries the picture's name. CON-019
  makes those exports byte-identical regardless of book geometry, so that path
  must not change.
- CARD-204 (in review) is rewriting puzzle-page placement (right/left by parity)
  and adding the 2×2 cm QR slot in the same files. This card depends on it so
  the two do not fight over the band/page-frame code.

**What changes.** On **book** puzzle pages (single and two-up slots) the header
becomes two pieces plus a rule:

1. `Puzzle N` set flush with the slot's usable **left** edge; the tier set flush
   with its usable **right** edge, in **upper case** (`MEDIUM`) as the doc's
   sample shows — the casing is a band-only presentation choice, so derive it
   from `Tier.label` (`.upper()`) at the drawing seam and leave `Tier.label`
   itself alone (the TOC, dividers and answer headings keep title case).
2. A horizontal rule immediately below the band, spanning the slot's usable
   width, at the thin-rule weight the book PageSpec already defines
   (ADR-0037/R2: thin ≥ 0.25 mm, heavy = 2 × thin, pure black). Reuse the
   PageSpec's stroke widths — do not invent a third weight.
3. The rule's vertical position and the two pieces' baselines must come from
   `header_band`'s measured strip (its `height`, `center_y`, `font_size`). If
   the rule needs room the strip does not have, the room is added in
   `export/layout.py`'s band measurement — **not** by drawing into the
   drawing's own space. (Coordinate with CARD-204: if it has already changed
   that function, extend rather than revert.)
4. A row with no tier of record still prints `Puzzle N` alone (today's
   behaviour, kept) — and still gets the rule.
5. Keep the existing fit/shrink behaviour per piece: `Puzzle 150` and `MEDIUM`
   are both short, but the shrink step must not be dropped, and the two pieces
   must never overlap — if their combined width exceeds the usable width at the
   floor, shrink both to the same size rather than eliding either (the number
   is what the answer key is looked up by; the tier is the only grade on the
   page).

## Acceptance criteria

- **AC-1** (happy): *Given* a medium puzzle printed as puzzle 37, *when* its
  book page is drawn, *then* `Puzzle 37` begins at the slot's usable left edge
  and `MEDIUM` ends at its usable right edge, both inside the measured band.
  (test: `TestBookPdfBand_NumberLeftTierRight`)
- **AC-2** (happy, rule): *Given* any book puzzle page, *when* it is drawn,
  *then* a single black rule spans the slot's usable width below the band, at
  the PageSpec's thin-rule width, above the puzzle's own drawing and touching
  neither it nor the band's glyphs. (test: `TestBookPdfBand_RuleUnderTheBand`)
- **AC-3** (happy, two-up): *Given* a two-up page, *when* it is drawn, *then*
  each of the two slots carries its own split header and its own rule, aligned
  to that slot's usable edges. (test: `TestBookPdfTwoUp_EachSlotHasItsOwnRule`)
- **AC-4** (edge, no tier): *Given* a row whose stored tier reads as no tier,
  *when* its page is drawn, *then* the band shows `Puzzle N` alone, flush left,
  nothing on the right, and the rule is still drawn. (test:
  `TestBookPdfBand_UntieredRowPrintsNumberAndRuleOnly`)
- **AC-5** (edge, type floor): *Given* any book trim in CON-018's profile set,
  *when* a page is drawn, *then* both band pieces are set at or above CON-020's
  10 pt floor. (test: `TestInteriorType_EveryFaceHoldsTheFloor`, extended with
  the two pieces)
- **AC-6** (guard, other renderers): *Given* any generation request, *when* the
  CLI or web UI exports a PDF, *then* its header is byte-identical to before
  this card. (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)

## Guardrails

- G-1: A book puzzle page never prints the picture's title (ADR-0037/R1) — this
  card must not slip the name into the freed right-hand side (test:
  `TestBookPdf_BandCarriesNumberAndTierOnly`).
- G-2: `export.pdf._draw_header`'s single-puzzle path and its 3-step
  fit/elide behaviour are unchanged (CON-019; test:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-3: `Tier.label` itself is not re-cased — the TOC rows, level dividers and
  answer-page headings keep title case (test: `TestBookPdfLevels_DividerText`).
- G-4: Do not change the puzzle grid's own placement or the QR slot — owned by
  CARD-204 this wave.
- G-5: Rule weights come from the book PageSpec (ADR-0037/R2); no new stroke
  constant.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-207 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_51 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-016 (the titled page's band), FR-032 (puzzle-page placement — being
  amended by CARD-204), FR-009 (the tier is the solver's grade).
- **ADR:** ADR-0037/R1, ADR-0037/R2, ADR-0036/R2.
- **CON:** CON-018, CON-019, CON-020.
- **Components:** COMP-009 (`book_pdf_generator.py`), COMP-007
  (`export/layout.py`) **only if** the band strip needs more measured height —
  see step 3, and coordinate with CARD-204.
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The artifact's "Header" rule is more specific than this card was, and splits the work:

- The header is **"Puzzle 52" left, difficulty right (three dots plus the word)**. So this card
  gains the **dots**, and therefore a dependency on **CARD-228** (the one glyph four cards
  share). Do not draw dots here.
- The **0.6 pt rule under the header across the full text width, at the same baseline on every
  page**, moves to **CARD-222**, which owns the frame. This card owns what sits *in* the header.
- The artifact confirms the rest of this card as written: the centred `Puzzle 7 · Easy` caption
  is the owner's issue 5 ("there is no consistent top edge to the page").
- **Depends on:** CARD-222 (the header region and its rule), CARD-228 (the dots). Update the
  card's `Depends on:` field at dispatch.
- ADR-0037/R1 says a puzzle page's band carries number + tier only. Dots *are* the tier, so the
  split header stays inside R1 — say so rather than assuming it.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** the design implemented on a raster interior, with its acceptance criteria
verified by measuring ink on a rendered bitmap.

**Should be:** the same design, unchanged — **the card's instrument moves, not its
decision**. CARD-293 §6 classifies this card as *written, tests retargeted*: a book puzzle page's header split — page composition and type, not stroke weight.

**Delta:**
- The design is **not** reopened. Nothing about what the page should look like
  changes here.
- The acceptance criteria's verifying tests move from ink measurement to
  assertions against the written PDF's content stream (ADR-0042/R6). The spike
  measured that replacement at **168 -> 41 lines, 4.1x smaller**, strictly more
  exact, and still discriminating under mutation.
- Scheduled **after** the vector phase (CARD-294..CARD-299) so the card is written
  against a vector page from the start. That ordering is the whole reason the
  phase runs first: dispatching this card before it would mean writing
  pixel-measuring tests and then converting them.

