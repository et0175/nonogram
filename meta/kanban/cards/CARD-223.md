# CARD-223: The QR code moves into the footer's outer corner, with a caption and a typed link

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/223-qr-in-the-footer
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 1 ("The QR square moves around... because it goes to the gutter side, it sits near the spine, where the page curves and a phone struggles to scan it") and "The rules behind it": QR code
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the footer this card puts the QR into)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf.py, tests/test_book_puzzle_frame.py, tests/test_book_qr_slot.py, tests/fixtures/book_baseline_card223.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The owner's complaint, in their words:** the QR "sits top-left on one page, bottom-right on
the next, beside the grid on two-up pages (pp. 9, 28, 75, 125, 160). And because it goes to
the gutter side, it sits near the spine, where the page curves and a phone struggles to scan
it." That is a **functional** defect, not only a visual one: a code printed into the spine
does not scan.

**Current behaviour (verified by reading the code).**

- CARD-204 gave each puzzle page a `QR_SLOT_MM` (2x2 cm) slot in the strip its flush-aligned
  drawing frees — which is by construction the **gutter** side, mirrored by parity, and on a
  two-up page one slot per puzzle beside its grid (`book_pdf_generator.py:4254`).
- The glyph is a deliberate placeholder: `_draw_qr_placeholder` draws a 5-module alternating
  checkerboard, "deliberately not a real QR code (owner's confirmed option 2(b))"
  (`book_pdf_generator.py:1442`). CARD-210 makes it real and is blocked on infrastructure.
- There is no caption and no typed link anywhere near it.

**What changes.**

1. The QR sits at the **outer** bottom corner of its puzzle's slot — the page footer for a
   single puzzle, the slot's own bottom for two-up (CARD-226 owns the slots). Outer, not
   gutter: that is the whole point of the move, and it is the one thing a test must pin by
   parity.
2. Beside it, two lines: `Solve it online` and the short typed link, for a reader with no
   phone camera. Both stay **placeholders** until CARD-210 — the artifact's own note says
   `nonogram.example/p/052` is a stand-in "until the online solver has a real address". Do
   not invent a domain: take the placeholder from one named constant so CARD-210 changes one
   line.
3. The 2x2 cm size stands (the owner's figure, unchanged from CARD-204).
4. Delete the gutter-side slot and its parity mirroring. This is a **removal**, so prove the
   removal: no puzzle page may place QR ink on the gutter side of the page, at any parity.

## Acceptance criteria

- **AC-1** (happy, the outer corner): *Given* a left-hand page and a right-hand page, *when*
  each is drawn, *then* the QR's box lies in the footer at the **outer** edge — right on a
  left-hand page, left on a right-hand one — and its outer edge is inside the usable area.
  (test: `TestBookQrSlot_SitsAtTheOuterBottomCorner`)
- **AC-2** (guard, never the spine): *Given* every page kind that carries a QR (single, each
  slot of a two-up, every parity), *when* it is drawn, *then* **no QR pixel** lies in the
  gutter half of the page. (test: `TestBookQrSlot_NeverPlacesInkOnTheGutterSide`)
- **AC-3** (happy, the caption and the link): *Given* a puzzle page, *then* `Solve it online`
  and the typed link are drawn beside the QR, both at or above CON-020's floor, and the link
  comes from one constant. (test: `TestBookQrSlot_CarriesItsCaptionAndLink`)
- **AC-4** (happy, the size): *Given* any page carrying a QR, *then* the drawn box measures
  2x2 cm at the page's resolution. (test: `TestBookQrSlot_IsTwoCentimetresSquare`)
- **AC-5** (edge, no room): *Given* a slot too short to hold the QR and its two lines, *then*
  the page draws neither rather than overprinting the folio or the footer rule, and says so
  through the same "no room" path the folio reservation already uses.
  (test: `TestBookQrSlot_YieldsRatherThanCollide`)
- **AC-6** (edge, the placeholder is still obviously fake): *Given* the drawn glyph, *then* it
  is still the checkerboard placeholder and not a scannable code — the owner's 2026-10-13
  decision stands until CARD-210. (test: `TestBookQrSlot_IsStillThePlaceholderGlyph`)

## Guardrails

- G-1: The folio keeps its line on every page (test: `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
- G-2: The grid-size label and the QR do not collide — they share the footer (test: AC-3's
  class, asserting their boxes are disjoint).
- G-3: No new runtime dependency. A real QR encoder is CARD-210's problem and its own
  dependency decision (ADR-0006/R1).
- G-4: Out of scope — the real QR (CARD-210), the grid's own placement (CARD-224).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-223 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable sta… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-040 (the QR slot CARD-204 introduced — its "and only when" clause is already
  owed an amendment at the architect station; this card moves the slot, so that amendment
  should be made against the *new* placement, not the old one).
- **CON:** CON-018 (the footer lives inside its margins), CON-020.
- **ADR:** ADR-0036/R2, ADR-0006/R1.
- **Components:** COMP-009, COMP-007.
- **Trace:** not updated by this card.

## Worktree notes

- [This is the card that frees CARD-224] The owner's own note says it: the flush-right and
  flush-left placement "was what freed the gutter-side strip for the QR. Once the QR has its
  own footer, centring is the calmer choice." So this card comes before CARD-224 — move the
  QR out of the gutter strip first, then stop needing the strip.
