# CARD-248: A two-up page gets one footer strip carrying both puzzles' links

**Status:** ready
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/248-two-up-shared-footer
**Worktree:** —
**Source:** owner decision 2026-10-18 — "about qr code in the two-up page's lower slot - it definitely should not be lost", then chose the shared-footer design from four measured options
**Idea:** —
**Wave:** —
**Depends on:** CARD-223 (the footer strip and the QR group it builds; this card gives a two-up page one of them)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_qr_slot.py, tests/test_book_two_up.py, tests/test_book_page_numbers.py, tests/test_book_arrange_page_breaks.py, tests/property/test_book_pdf_geometry.py, tests/helpers/book_corpus.py, tests/helpers/two_up_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**The problem, stated as the owner stated it: a two-up page's lower puzzle must not lose its
scannable link.** CARD-223 moved the QR from the gutter strip (where it did not scan — the
owner's original complaint) to the footer's outer corner. A two-up page has **no footer**, so its
lower slot came out with no QR at all, and the baseline book printed **3 links for 4 puzzles**.

**The design the owner chose:** a two-up page reserves **one** footer strip and carries **both**
puzzles' links in it, side by side.

**All of the following is measured on this tree, not estimated. Re-derive it; do not trust it.**

**It fits horizontally, with room.** At the footer's own 10 pt face (42 px em at 300 DPI):

| | px | mm |
|---|---|---|
| `QR_CAPTION_TEXT` "Solve it online" | 300 | 25.4 |
| the typed link `nonogram.example/p/123` | 549 | **46.5** |
| the icon (`QR_SLOT_MM`) | 236 | 20.0 |
| **one group** (icon + 2 mm + widest line) | 809 | **68.5** |
| **two groups** | 1618 | **137.0** |
| usable width | 2250 | 190.5 |
| **spare** | 632 | **53.5** |

The **link line dominates the group width**, so a longer caption is free: `"Puzzle 123"` gives the
same 68.5 mm, and the fullest `"Puzzle 123 · Solve it online"` gives 70.0 mm a group, 140.0 mm for
two, still **50.5 mm spare**.

**It is free vertically for most pairs, because the room already exists.** The strip needs
`INTERIOR_FOOTER_MM` = 29.878 mm = **353 px**. Measured spare height per pair — and note **all of
it currently idles as a gap *between* the two slots**, with the bottom slack always 0:

| pair | cell | gap between slots | top | bottom | total spare | 353 px? |
|---|---|---|---|---|---|---|
| 25×10 | 7.33 mm | 948 px (80.3 mm) | 142 | 0 | **1090 px** | yes, free |
| 15×10 | 7.50 mm | 904 px (76.5 mm) | 142 | 0 | **1046 px** | yes, free |
| 10×10 | 7.50 mm | 904 px | 142 | 0 | **1046 px** | yes, free |
| 12×12 | 7.50 mm | 549 px (46.5 mm) | 142 | 0 | **691 px** | yes, free |
| 20×15 | 7.17 mm | 142 px (12.0 mm) | 142 | 0 | 284 px | **no, short 69 px** |
| 15×15 | 7.17 mm | 142 px | 142 | 0 | 284 px | **no, short 69 px** |

So the strip mostly claims spare that is already there. Only the tall 15-row pairs are short, by
**69 px (5.8 mm)**; spread over two slots of ~19 cell-heights each that is roughly **0.15 mm off
the cell (7.17 → ~7.02, about 2 %)**. **That last figure is arithmetic of mine, not a
measurement — measure it and state what you get.**

**`folio_reserve_px` is NOT the lever, and reusing it would be a mistake.** Measured: at every
reserve level (0, 108, 236, 353 px) the lower slot's bottom slack stays **0** and the cell size
does not move, because that parameter reserves **horizontal** room in the outer margin for
CARD-200's folio (`book_pdf_generator.py:1857`), not vertical room. `compute_pair_layout` packs
the two slots to fill the height exactly. This card needs a **vertical** reservation, which is a
new capability in that function.

**One warning from the same measurement:** the tight **25×10** pair is already **REFUSED** at
today's 108 px horizontal reserve. So a pair can already fail to be two-up, and a vertical reserve
must not quietly widen that set. Measure how many corpus pairs stop fitting, state the number, and
if any do, say what happens to them (they become two single pages — which is acceptable and is
option 1 from the owner's own choice set, but it must be stated, not discovered).

**A gain to claim deliberately, not by accident:** a two-up page today has no footer and therefore
**omits its page number** — `test_book_page_numbers.py` asserts exactly that for a slot with no
room on either axis. Giving the page a footer strip means its folio has somewhere to go. Assert
that two-up pages now carry their folio; it is a real improvement and it should not arrive
unmentioned.

## Acceptance criteria

- **AC-1** (happy, both links): *Given* a two-up page, *then* its footer strip carries **two** QR
  groups — icon, caption and typed link — one per slot, and the baseline book prints **4 links for
  4 puzzles** where it printed 3. (test: `TestTwoUpFooter_CarriesBothPuzzlesLinks`)
- **AC-2** (happy, each link is the right one): *Given* the two groups, *then* each group's typed
  link is **its own** slot's `qr_link(puzzle_number)` — upper's for the upper puzzle, lower's for
  the lower. The defect this catches is two groups both showing one puzzle's link.
  (test: `TestTwoUpFooter_EachGroupCarriesItsOwnSlotsLink`)
- **AC-3** (happy, the reader can tell which is which): *Given* that a stacked pair of puzzles maps
  to a **side-by-side** pair of links, *then* each group is identified by its puzzle number, so the
  correspondence is readable without counting. **State the convention you chose** (which side the
  upper puzzle's group takes, and why) — the measurement above shows caption length is free, so
  there is no cost argument against labelling.
  (test: `TestTwoUpFooter_EachGroupNamesItsPuzzleNumber`)
- **AC-4** (guard, never the spine): *Given* both parities, *then* no QR pixel and no caption pixel
  lands on the gutter side of the page — the owner's original complaint, which this card must not
  reintroduce on a new page kind. Prove it on **measured ink**, reusing CARD-223's `_qr_ink()`
  approach, with a control that fails. (test: `TestTwoUpFooter_NeverPlacesInkOnTheGutterSide`)
- **AC-5** (boundary, the cell cost): *Given* each pair in the corpus, *then* the measured cell
  size with the strip reserved is recorded against the figures above, and **no pair silently loses
  more than it must**. State the tall-pair cost you measure rather than inheriting ~2 %.
  (test: `TestTwoUpFooter_TheCellCostIsMeasuredAndBounded`)
- **AC-6** (edge, a pair that no longer fits): *Given* a pair for which the strip cannot be
  reserved, *then* it prints as **two single pages** rather than as a two-up page with a missing
  link, and the set of such pairs is **asserted as an exact set**, not a range — so a later card
  that widens it reds. (test: `TestTwoUpFooter_APairThatCannotFitSplitsIntoSinglePages`)
- **AC-7** (happy, the folio arrives): *Given* a two-up page, *then* it carries its page number in
  the new footer strip, where it previously had none.
  (test: `TestTwoUpFooter_TwoUpPagesNowCarryTheirFolio`)
- **AC-8** (guard, the strip is the same strip): *Given* a two-up page and a single page, *then*
  both use `INTERIOR_FOOTER_MM` and the same footer group geometry — one definition of what a
  footer is, not a second one for pairs.
  (test: `TestTwoUpFooter_UsesTheSameFooterGeometryAsASinglePage`)

## Guardrails

- G-1: **One definition of the footer.** Reuse CARD-222's `interior_frame` footer and CARD-223's
  `qr_slot` / `qr_caption` / `QR_CAPTION_TEXT` / `QR_LINK_TEMPLATE` / `qr_link`. Do **not** add a
  second footer geometry or a second link template — CARD-223 pinned the host string to exactly
  one literal in all of `src/nonogram/**` with an `ast` scan, so CARD-210 stays a one-line change.
- G-2: `folio_reserve_px` keeps its current meaning (horizontal outer-margin room). Add a separate
  vertical reservation rather than overloading it — one parameter, one job.
- G-3: Single-page behaviour is byte-for-byte unchanged. CARD-223's baselines are the control.
- G-4: The equal-slot invariant survives: both slots keep the same cell size as each other, which
  is what CARD-226 will build its "two equal slots, aligned bottoms" on.
- G-5: No new float constant without declaring it — `TestBookPageFrame_EachFigureIsDeclaredOnce`
  and its exemption list are live.
- G-6: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted. Expect
  `changed_pages` to include the two-up page and to **explain** every page it lists.
- G-7: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-18 by `system_rules.py --card CARD-248 --root meta/architecture` (60 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 11; 49 dropped and declared — and the curation here was done BY HAND, which is worth saying.** Owner decision 2026-10-17 allows 6–14 rules kept "where the rule's scope names a file the card touches or the card names the rule's artifact". On this card that criterion cannot be applied mechanically: the rules most worth keeping (ADR-0039's three) scope themselves to a list of **eleven** component globs, which together match every card in the project, so a scope-matching filter either drops them with the package-wide ones or keeps fifty. The eleven below were chosen as the rules this card can actually breach — page geometry ownership, the band's contract, control discipline, and the three constraints its own figures touch. The root cause remains the package-wide scoping, tracked in `meta/kanban/backlog.md`.

- **ADR-0036/R1** — compute_layout called without a PageSpec produces exactly today's A4 geometry;
  CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test:
  TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- **ADR-0036/R2** — Book page geometry is computed only by COMP-007's layout functions
  (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin
  panel does not fit cells or place grid lines itself. (check: review-lens)
- **ADR-0036/R3** — Exactly one function in src/nonogram/** puts a round mark on a page. A second
  one is a defect whatever Pillow call it is written with: four cards print the same difficulty
  glyph, and four slightly different dots cannot be fixed once a book is on paper. (check: test:
  test_the_books_own_pages_carry_no_undeclared_round_mark)
- **ADR-0037/R1** — A book puzzle page never prints the picture's title; its band shows the puzzle
  number and the solver's tier only. (check: review-lens)
- **ADR-0037/R2** — Under the book PageSpec the puzzle grid has exactly three rule weights -- 0.48
  pt ordinary cell lines in grey, 1.28 pt every fifth line on both axes, 2.08 pt outer border --
  each of them at least 2 device pixels at the render resolution, with the cell lines lighter in ink
  than the fifth lines and… (check: review-lens)
- **ADR-0039/R1** — A set a guard consults needs a completeness test written before the set, and any
  claim the guard makes about what it catches needs a control that can fail: caught WITH the set
  member present, missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage,
  and must be narrowed to … (check: test: test_the_control_for_each_spelling_depends_on_the_set)
- **ADR-0039/R2** — A guard's set is derived from an authority the runtime can enumerate, not hand-
  written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is
  a FAILURE, never a silent pass, and the unanalysable sites become named exemptions under
  ADR-0039/R3. (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- **ADR-0039/R3** — An exemption is a claim. Every exemption a guard grants carries a control for
  what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to
  an equality against the sites that exist today, and records whatever it still cannot see as a
  measured bound with its own… (check: test:
  test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- **CON-019** — Adding book-specific page geometry (a trim, margins, a title band, a portrait-only
  rule, the 7.5 mm standard cell) never changes the CLI's or the web UI's exports: for any
  generation request the PNG, SVG and PDF files COMP-007 writes are byte-for-byte identical to those
  written before the book ge… (check: test:
  PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- **CON-020** — No text the book's interior prints for the reader is set below 10 pt at the page's
  own resolution, except the clue digits drawn inside a puzzle page's clue cells, whose size follows
  the cell (its floor is CON-018 / INV-006); every other face — guide page and its worked example,
  dividers, bands, a… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)
- **CON-021** — Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044),
  served behind the door that guards every other admin page (CON-015, CON-016). No other surface —
  the CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never pe… (check: review-lens)

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **ADR-0036/R2 is the one this card is most likely to breach.** Book page geometry is computed only by COMP-007's layout functions with the book's PageSpec. The vertical reservation this card needs belongs in `compute_pair_layout`, **not** in `book_pdf_generator.py` — CARD-222 put `interior_frame` in `layout.py` for exactly this reason and a test asserts the only numeric literals in it are `{1, 2}`.
- **ADR-0036/R3 reaches the QR glyph.** Exactly one function in `src/nonogram/**` may put a round mark on a page. The placeholder is a checkerboard, not a round mark, so it is outside R3 today — but this card draws **two** of them per page for the first time, so if any part of the group becomes a disc, R3 binds it.
- **ADR-0037/R2, as amended 2026-10-17, binds the puzzle grid and NOT page furniture.** The footer strip and its two groups are furniture. Do not write a test comparing furniture ink to grid ink: after CARD-227 the grid's thinnest cell line is 2 px, the same as the footer hairline, so such a claim becomes false. CARD-223's retargeted control compares furniture with furniture only — follow it.
- **CON-021 is why the link host is `.example`** (RFC-2606 reserved). CARD-223 pinned that host string to exactly one literal in all of `src/nonogram/**` with an `ast` scan so CARD-210 stays a one-line change. Two groups must still read from that one constant.
- **ADR-0039/R1 and R3 are the discipline AC-6 lives or dies by.** The set of pairs that cannot fit the strip is an **exemption**, so it needs a control that fails and the residue recorded as a measured bound — an exact asserted set, not a range.
## Worktree notes

- **[Why this card exists, in the owner's words]** "about qr code in the two-up page's lower slot -
  it definitely should not be lost". It was framed to them as an open design choice and it is not:
  a puzzle printed without its scannable link is the feature failing for that puzzle. Four options
  were measured and put to them; they chose the shared footer.
- **[Read CARD-223's notes before starting]** It owns the QR group, the outer-corner placement, the
  `_unequal_spec()` mirroring pattern (**do not prove mirroring on the Book 1 profile — gutter and
  outside are both 12.700 mm there, so the claim is an identity**), and the `_qr_ink()` measured-ink
  technique. All four are reused here rather than reinvented.
- **[The measurement trap that cost time here]** A bare `python` in a worktree imports the **main
  repo's** package, because the venv's editable install points at the main checkout and only pytest
  gets `pythonpath = ["src"]`. Every figure in this card was re-taken after putting the worktree's
  `src` first and asserting `"card-223" in module.__file__`. Do the same, or you will measure the
  wrong tree and not know it.
- **[House rules]** `hypothesis` is not in the dependency baseline — seeded `random.Random` corpora
  with an asserted minimum case count. Prefer an independent second implementation over
  re-deriving with the function under test. Capability modules never import laterally
  (`tests/test_cli.py` has an `ast` guard). No timing measurements while a sibling card is active.
- **[What this card hands to CARD-226]** CARD-226 ("two equal slots split by a light rule, with
  aligned bottoms") inherits a two-up page that already reserves a footer and keeps both slots
  equal. Its divider rule and its aligned bottoms sit above this strip. If the two cards disagree
  about who owns the slot heights, this one is the earlier statement and CARD-226 amends it rather
  than re-deciding it.
