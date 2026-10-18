# CARD-223: The QR code moves into the footer's outer corner, with a caption and a typed link

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/223-qr-in-the-footer
**Worktree:** ../PythonProject4-card-223
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — issue 1 ("The QR square moves around... because it goes to the gutter side, it sits near the spine, where the page curves and a phone struggles to scan it") and "The rules behind it": QR code
**Idea:** —
**Wave:** 45
**Depends on:** CARD-222 (the footer this card puts the QR into)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf.py, tests/test_book_puzzle_frame.py, tests/test_book_qr_slot.py, tests/fixtures/book_baseline_card223.json, tests/helpers/two_up_ink.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** 2026-10-17T22:41:59Z
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
  each is drawn, *then* the QR's box lies in the footer at the **outer** edge — **right on a
  right-hand (odd) page, left on a left-hand (even) page** — and its outer edge is inside the
  usable area.
  _[CORRECTED 2026-10-18. As written this parenthetical was **inverted** and named the
  **gutter** — the very thing this card exists to move the QR away from — and so contradicted
  its own AC-2 ("never the spine"). ADR-0036 is explicit: the gutter sits "on the left of
  right-hand (odd) pages and on the right of left-hand (even) pages", and the codebase follows
  it (`_draw_folio`: an ODD right-hand page lands `drawing_right` on `usable_right`;
  `InteriorFrame.label_x` puts the gutter left on ODD). Caught by the implementation agent,
  which checked the convention instead of following the AC literally and implemented **outer**;
  had it obeyed the AC, this card would have shipped the owner's complaint back to them. The
  implementation is correct and this wording now matches it.]_
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

- **[AC/EC/G gate] PASSED on evidence, with AC-1's evidence checked by hand because its wording
  had been inverted.** All eight named test classes confirmed present
  (`TestBookQrSlot_SitsAtTheOuterBottomCorner`, `_NeverPlacesInkOnTheGutterSide`,
  `_CarriesItsCaptionAndLink`, `_IsTwoCentimetresSquare`, `_YieldsRatherThanCollide`,
  `_IsStillThePlaceholderGlyph`, `_TheGutterSidePlacementIsGone` in `tests/test_book_qr_slot.py`,
  plus `TestBookPageNumbers_EveryInteriorPageShowsItsOwnNumber`).
  **I read AC-1's test rather than trusting the name**, because the criterion it answers to was
  the one I had to correct. It holds up better than the AC did:
  * it opens with `assert outside_px != gutter_px, "the fixture must have unequal margins to
    prove anything"` — a precondition that reds if someone later makes the fixture symmetric and
    quietly turns the proof back into an identity;
  * it asserts **both** `trim - odd.right == outside_px` *and* `!= gutter_px` (and the mirror for
    EVEN), so reading the wrong margin fails rather than coincidentally passing;
  * it asserts a true reflection, `odd.left == trim - even.right`;
  * and the sibling identity-recording test carries
    `assert _px(GUTTER_MM) == _px(OUTSIDE_MM), "CON-018's amendment made these equal; if they ever
    differ again, the Book 1 case becomes evidence and this test should say so"` — **a guard that
    invalidates itself** when its own premise stops holding. That is the shape the rest of this
    board's identity caveats should copy.

- **[Owner decision 2026-10-18 — the two-up lower slot is NOT deferred]** Put to the owner as
  four measured options; they chose a **shared footer strip carrying both puzzles' links**, carded
  as **CARD-248** (P1, architectural, depends on this card). Two of my own assumptions died in the
  measurement and are recorded there: `folio_reserve_px` reserves *horizontal* outer-margin room,
  not vertical (at 0/108/236/353 px the lower slack stays **0** and the cell does not move), and
  the vertical cost is far smaller than I implied when offering the option — the spare height
  already exists as a gap *between* the slots (1090 / 1046 / 691 px against the 353 px needed),
  so the strip is **free** for most pairs.
  **Merge plan, owner-approved:** this card merges once re-gated, and CARD-248 is dispatched
  immediately after. That leaves a short window in which `main` prints a two-up page with one
  link rather than two, so **no book should be generated for KDP in that window** — stated plainly
  rather than left implicit, because the owner's instruction was that the link "definitely should
  not be lost".

- **⚠ [AC-1's own wording was INVERTED, and following it would have shipped the owner's complaint
  back to them.]** AC-1's parenthetical read "right on a left-hand page, left on a right-hand one".
  That names the **gutter**, not the outer edge — the precise thing this card exists to move the QR
  away from — and it contradicted its own AC-2 ("never the spine"). Verified against the model, not
  argued: ADR-0036 states the gutter sits "on the left of right-hand (odd) pages and on the right of
  left-hand (even) pages", and the code follows it (`_draw_folio`: an ODD right-hand page lands
  `drawing_right` on `usable_right`; `InteriorFrame.label_x` puts the gutter left on ODD). **The
  implementation agent caught it by checking the convention instead of obeying the AC, implemented
  *outer* (ODD→right, EVEN→left), and flagged the AC rather than editing the card.** Exactly the
  right division of labour. AC-1 is corrected above with the defect recorded in place.
  **Worth carrying:** this is the second card this wave whose own stated criterion contradicted its
  purpose (CARD-224's AC-6 vs AC-2 is the other, still open). Both came from the same owner artifact
  and both invert a left/right or above/below relation — a decompose-station check for parity and
  ordering claims would have caught them on paper.

- **[Implemented; mirroring proved where it is observable]** On `_unequal_spec()` — Book 1's trim with
  **gutter 19.0 mm, outside 7.0 mm**, differing by 12 mm (142 px, far more than the 20 mm icon). ODD:
  `trim - icon.right == outside_px` **and** `!= gutter_px`; EVEN: `icon.left == outside_px` **and**
  `!= gutter_px`; plus a true mirror (`odd.left == trim - even.right`). A sibling test records
  explicitly that on the default profile `_px(GUTTER_MM) == _px(OUTSIDE_MM)`, so the *distance* claim
  there is an identity and only the *side* claim has teeth — the CARD-222 pattern, reused as briefed.
  AC-2 is additionally proved on **measured ink**: `_qr_ink()` diffs a page against the same page with
  the placeholder suppressed, so the mask is the glyph's own pixels, and a control asserts the retired
  gutter-side box really does land in the forbidden half, so the claim can fail.

- **[The behaviour change to carry to CARD-226]** A two-up page's **lower slot now carries no QR at
  all** (it had one before, in the gutter margin). Its drawing's bottom edge *is* the bottom margin on
  every two-up page, so there is no room, and that corner is exactly where the page's fallback folio
  prints. The baseline book now prints **3 links for 4 puzzles**, and the test derives the missing one
  from the page plan rather than hardcoding it. The card anticipated this, but it is a **loss of
  coverage**, so CARD-226 owns deciding whether a lower slot should get one. The 10×10 cm minimum trim
  also carries no QR now (it used to use the side margin); **no KDP trim is affected** — the full
  sweep 12.70×20.32 / 13.97×21.59 / 15.24×22.86 / 21.59×27.94 cm × sides 10..30 keeps the icon
  everywhere, recorded as tests.

- **[Deliberately NOT taken]** `INTERIOR_FOOTER_MM` keeps its three rows. CARD-222's docstring said
  that once the icon moved the footer line "can drop onto the icon's row and this band becomes the
  artifact's own 23.175 mm" — doing that would shorten the band, move `area_bottom`, and therefore
  move **every grid on every page**. That is CARD-224's subject, and the docstring now says so. Right
  restraint: this card is the QR's position, not the band's height.

- **[Outside `Touches`, flagged not assumed]** `meta/profiling/rank_durations.py` (the frozen
  render-set guard went red because `test_book_qr_slot.py` now calls `interior_stream`; path added,
  31 now, with a dated note — direct precedent, CARD-222's own `88c93b5`). The agent explicitly
  **did not** dodge the grep by spelling the call through a sibling API, which is the silent divergence
  that guard exists to catch. And `meta/profiling/suite-hotspots-20261015.md`, where — unlike
  CARD-222's case — this file *is* in the 2026-10-15 recording, so the render row's **test count**
  moves 1079→1091 and the derived ms/test 181→179. **Every measured second and every share is
  unchanged** (that file's tests all recorded 0.00 s), the durations artefact is untouched and its
  sha256 citation still valid.

- **[Dead code this card creates, for a follow-up]** `src/nonogram/admin/book_proof.py` was correctly
  left unedited (outside `Touches`), but its CARD-204 comment and the
  `if icon.top == placement.drawing_top` branch in `_fallback_spots` are now **unreachable** — no icon
  anchors at the drawing's top any more. Its tests pass. Needs a follow-up to delete the branch and the
  comment rather than leaving a live-looking branch nothing can enter.

- **[The DB caveat, and the fix proving itself]** In one intermediate combined run the agent included
  `tests/test_book_floor.py`, which carries `[db]`-parameterised tests, against my instruction not to
  run DB selections while a sibling was active. It passed, and **no harm was possible** — because
  CARD-244 had already isolated itself onto its own derived database. So the hardening card prevented
  a real collision *during its own development*, which is the most direct evidence available that it
  works. Three DB-mode render-heavy files (`test_book_scaffolding.py`,
  `test_book_export_interior_cover.py`, `test_book_finalise_gutter.py`) were deliberately not run;
  statically none reconstructs a page frame, references the QR, or asserts a pixel digest, and the
  merge gate covers them.

- **[Still owed at the architect station]** FR-040's "and only when" amendment, which should now be
  written against the **outer-corner** placement and against the fact that a two-up lower slot no
  longer carries the slot at all.

- [This is the card that frees CARD-224] The owner's own note says it: the flush-right and
  flush-left placement "was what freed the gutter-side strip for the QR. Once the QR has its
  own footer, centring is the calmer choice." So this card comes before CARD-224 — move the
  QR out of the gutter strip first, then stop needing the strip.
