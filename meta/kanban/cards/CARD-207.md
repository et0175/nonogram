# CARD-207: A book puzzle page's header splits — "Puzzle 37" flush left, "MEDIUM" flush right, a rule beneath

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
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

- ADR-0037/R1 — a book puzzle page's band shows the puzzle number and the
  solver's tier only, never the picture's title (check: review-lens)
- ADR-0037/R2 — thin rule ≥ 0.25 mm, heavy = 2 × thin, pure black, default
  PageSpec strokes unchanged (check: review-lens)
- CON-020 — no reader-facing interior text below 10 pt except puzzle-page clue
  digits (check: `TestInteriorType_EveryFaceHoldsTheFloor`)
- CON-019 — book geometry never changes CLI/web exports (check:
  `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`)
- ADR-0036/R2 — only COMP-007's layout functions compute page geometry; the
  admin panel does not place things itself (check: review-lens)

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
