# CARD-248: A two-up page gets one footer strip carrying both puzzles' links

**Status:** done
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/248-two-up-shared-footer
**Worktree:** ../PythonProject4-card-248
**Source:** owner decision 2026-10-18 — "about qr code in the two-up page's lower slot - it definitely should not be lost", then chose the shared-footer design from four measured options
**Idea:** —
**Wave:** 45
**Depends on:** CARD-223 (the footer strip and the QR group it builds; this card gives a two-up page one of them)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_qr_slot.py, tests/test_book_pdf_two_up.py, tests/test_book_page_numbers.py, tests/test_book_arrange_page_breaks.py, tests/property/test_book_pdf_geometry.py, tests/helpers/book_corpus.py, tests/helpers/two_up_ink.py, tests/fixtures/, tests/test_book_page_frame.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf_memory.py, tests/test_book_finalise_gutter.py, tests/property/test_book_pairing.py, tests/property/test_book_export_interior.py <!-- AMENDED 2026-10-18 at the hand-back: `tests/test_book_two_up.py` does not exist and never did (the file is `tests/test_book_pdf_two_up.py`), and six more test files had to move because a vertical reserve changes every pinned pair height. Every one of the six is a consequence of this card's own geometry change, not a second slice; `tests/helpers/two_up_ink.py` was listed and needed no change. -->
**Review score:** 8.5 (cycle 1/3, ✓ threshold reached)
**Started:** 2026-10-18T00:29:15Z
**Closed:** 2026-10-18T02:55:46Z
**Actual:** 0.3d
**Merge commit:** 1256982
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

### Findings at the hand-back, 2026-10-18 — re-measured by the orchestrator, not taken on report

- **[The ~2 % tall-pair cell cost in this card's body is WRONG, and in the worse direction.]**
  The card said the tall 15-row pairs lose "roughly 0.15 mm off the cell, about 2 %", and flagged
  that figure as the orchestrator's arithmetic. It is not a 2 % cost: those pairs **stop being
  two-up pages at all**. The arithmetic error is traceable and worth recording, because the same
  mistake is available to the next card that reads a spare-height column: every "spare" figure in
  the table above is the real free slack **plus the two 12 mm bands** (142 px each), which the pair
  needs and the strip cannot take. It decomposes exactly — 1090 = 806 + 284, 1046 = 762 + 284,
  691 = 408 + 284, 284 = 0 + 284 — so "short 69 px" is 353 − 284 where that 284 was two bands. A
  15-row depth-1 pair's real free slack is **0**: it is already height-bound, so the shortfall is
  the whole 353 px and the pair is refused.

  Measured independently of the implementation agent, on Book 1, depth-1 equal pairs
  (`compute_pair_layout`, `folio_reserve_px=108`, `footer_reserve_px=353`):

  | combined cells | cell before | cell after | verdict |
  |---|---|---|---|
  | 18–26 (h=8..12) | 7.5000 mm | 7.5000 mm | free — the strip comes out of the gap that idled between the slots |
  | 28 (h=13) | 7.5000 mm | **7.1287 mm** | **−0.3713 mm, −4.95 %** — the worst *surviving* cost, a band this card's table never mentions |
  | 30, 32 (h=14,15) | 7.5000 / 7.1716 mm | **refused** | prints as two single pages |

- **[The exact newly-refused set, reproduced.]** `{29, 30, 31, 32}` combined cells, at any width —
  independently swept over 17×17×2 = 578 unequal-height pairs and matching the implementation's
  `NEWLY_REFUSED_PAIR_CELLS` exactly. The odd members matter: an equal pair's total is always even,
  so a sweep of equal pairs alone reports `{30, 32}` and *looks* like agreement while missing half
  the set. On the depth-1 equal-pair sweep, **30 of the 90** pairs that paired before stop pairing.

- **[A second, horizontal refusal — and this one costs more than the vertical one.]** Two groups
  need `2·pitch − gap` = 1774 px = **150.1987 mm** of usable width at the four-digit worst case, so
  at Book 1's own side margins a trim needs **175.60 mm / 6.913 in** of width before a two-up page
  is possible at all. Measured per KDP trim **at Book 1's own margins (12.700 mm gutter + 12.700 mm
  outside, CON-018 as amended)** — the column is stated because it matters, see the correction below:

  | trim | usable width | cells before → after | two groups fit | headroom | two-up still possible |
  |---|---|---|---|---|---|
  | 5 × 8 | 101.60 mm (1200 px) | 20 → 16 | no | −574 px | no (none before either) |
  | 5.5 × 8.5 | 114.30 mm (1350 px) | 22 → 18 | no | −424 px | **no — lost** |
  | 6 × 9 | 127.00 mm (1500 px) | 24 → 20 | no | −274 px | **no — lost** |
  | 6.14 × 9.21 | 130.60 mm (1543 px) | 26 → 22 | no | −231 px | **no — lost** |
  | 7 × 10 | 152.40 mm (1800 px) | 28 → 24 | yes | **+26 px** | yes — the narrowest that survives |
  | 7.5 × 9.25 | 165.10 mm (1950 px) | 26 → 22 | yes | +176 px | yes |
  | 8 × 10 | 177.80 mm (2100 px) | 28 → 24 | yes | +326 px | yes |
  | 8.5 × 11 (Book 1) | 190.50 mm (2250 px) | 32 → 28 | yes | +476 px | yes |

  **[Correction — the orchestrator's own figures were measured on the wrong margins.]** An earlier
  revision of this note gave the threshold as "176.2 mm / 6.94 in" and 7 × 10's usable width as
  1793 px with 19 px of headroom. Those came from sweeping with **gutter 19.0 / outside 7.0 mm** —
  CARD-223's `_unequal_spec`, which exists to prove *mirroring* and is not Book 1's profile. At
  Book 1's own 12.700/12.700 the figures are 1800 px, **+26 px**, and **175.60 mm / 6.913 in**; the
  difference is exactly the 0.6 mm by which the two margin pairs differ in total. The
  implementation agent reported 175.6/6.91 and the orchestrator wrongly called it off by a rounding
  — the reverse was true. **No verdict moves either way**: both margin sets give the same fit/refuse
  per trim and the same cells before → after, so 6 × 9 loses two-up under both. Recorded because a
  figure that is right for the wrong sheet is the error class this board keeps paying for.

  **Book 1 is unaffected in kind** — it keeps two-up pages, 28 cells instead of 32. But **6 × 9 is a
  common nonogram-book trim and loses two-up pages entirely.** That is a scope consequence of the
  owner's chosen design, it was not in the option set they chose from, and it is stated here rather
  than discovered by a later book. The horizontal gate reads
  `_qr_group_line_px(dpi)` — the page-independent ceiling, the twin of `_folio_reserve_px` — so
  neither refusal lets a page number or a book's scale decide whether two puzzles pair (INV-010).

- **[FR-040's registry ACs are owed a re-measurement, and two of them now state the wrong
  VERDICT, not just a stale number.]** Measured on the same fixtures the registry describes
  (row-clue depths reconstructed, which the registry does not always name — so treat the
  reconstruction as indicative for AC-244 and exact for AC-242/243):

  | AC | registry says | before this card | after this card |
  |---|---|---|---|
  | AC-242 (28 cells) | 7.5 mm, shares a page | 7.5000 mm ✓ | **7.1287 mm** — newly stale, caused by this card |
  | AC-243 (32 cells) | 7.39 mm, shares a page | 7.1716 mm (already stale) | **refused — two single pages**, so the verdict flips |
  | AC-244 (33 cells) | 7.16 mm, shares a page | refused already | refused — **pre-existing**, CARD-222's known deferral |
  | AC-245 (34 cells) | two separate pages | separate ✓ | separate ✓ |
  | AC-246 (36 cells) | two separate pages | separate ✓ | separate ✓ |

  **AC-244's defect is sharper than "stale", and the sharper reading is the useful one:**
  7.1716 mm is the **32**-cell value, so AC-244 pairs a **33**-cell fixture with the 32-cell
  figure. That is a pre-existing off-by-one in the registry, not margin drift — 33 cells has
  measured 6.9543 mm (below the 7.0 mm two-up minimum, i.e. refused) since before this card
  touched anything. So part of this table is CARD-222's deferral, part is an arithmetic slip
  older than either card, and part is new; the table separates them so the architect station does
  not have to re-derive which is which.

  **The whole amendment reduces to one measured fact**, which is why it is small:

  | | before | after |
  |---|---|---|
  | usable height | 253.492 mm | 253.492 mm |
  | two bands | 24.000 mm | 24.000 mm |
  | footer strip | — | **29.878 mm** |
  | **two-up height budget** | **229.492 mm** | **199.614 mm** |
  | largest pair clearing 7.0 mm | **32 cells** (7.1716) | **28 cells** (7.1291; 29 → 6.8832) |

  So the refusal is still FR-040's own 7.0 mm two-up minimum doing the work. The **budget**
  shrank; the rule did not. That is the sentence the amendment should turn on.
  The implementation re-chose the *test* fixtures so the tests still pass, which means **the tests
  no longer verify what the registry says**; that is the gap, and it is an ADR-0039/R1 gap, not a
  cosmetic one. **Landing obligation, recorded below.**

- **[CARD-223's "gutter half of the sheet" is arithmetically impossible for two groups, and the
  narrowing is declared rather than glossed.]** A row of two groups needs 1682 px of ink against
  the 1125 px the outer half of Book 1's trim offers, at any arrangement. The forbidden region is
  therefore narrowed to the gutter margin plus the icon-wide strip CARD-204 actually used, with the
  residue recorded as a measured bound: **240 px (20.3 mm) of clearance** beyond that strip for the
  worst number the face can ever set. The implementation deliberately did *not* claim the gutter
  quarter or "both icons in the outer half" — both are true at two digits and **false** at four
  (the inner icon's left edge moves 1285 → 1258 against a midline of 1275), so either would have
  been a claim a longer book breaks.

- **[AC-3's convention, as chosen.]** The upper puzzle's group is the one a reader meets **first
  reading left to right** — the *inner* group on an odd (right-hand) page, where the row packs
  rightward from the outer margin, and the *outer* group on an even one. The puzzle number is the
  primary cue (`"Puzzle N · Solve it online"`) and the ordering is the redundant second one.

- **[Scope-gate note, not an escalation.]** Six test files moved that the card's `Touches` did not
  name, plus one whose name in `Touches` did not exist. All seven are the same component's test
  files and every change is a consequence of this card's own pinned pair heights moving; no sibling
  card's acceptance criteria were implemented. CARD-224/225/226/227 all carry
  `tests/test_book_*.py` and `tests/fixtures/` as wildcards in their own `Touches`, so the
  wildcard collision is by construction and is not evidence of poaching. `Touches` amended above
  rather than left to be rediscovered.

### Build gate, 2026-10-18 — green on the SECOND run, and both runs are recorded

| run | HEAD | exit | result |
|---|---|---|---|
| 1 | `5c5d0aa` | **1** | 8039 passed, **1 failed**, 1 skipped |
| 2 | `5c5d0aa` | **0** | **8040 passed**, 0 failed, 1 skipped, 796.91 s |

Same commit, same command, same derived database, same 8040 tests. The failure is therefore
**non-deterministic**, which is what settles attribution — it is not this card's.

The failure was
`tests/test_book_arrange_size_filter.py::TestArrangeSizeFilter_PlanLineShowsLeftAndOver::test_the_line_reads_left_over_and_on_plan_per_level[db]`,
inside `puzzle_review._set_status`'s `db.query(Puzzle).…first()`, raising
`AttributeError: 'float' object has no attribute 'replace'` from `uuid.UUID(hex=inf)` — **a UUID
column read back as the float `inf`**. `puzzles` has **no float column at all**
(`src/nonogram/db/models.py:56-88`), so misalignment *within* the table cannot explain it.
Diagnosis, now a backlog `@ops` item: `tests/conftest.py:433` rebuilds the schema
(`DROP SCHEMA public CASCADE` → `CREATE SCHEMA public` → `alembic upgrade head`) on **its own**
engine and disposes that engine, while `src/nonogram/db/session.py:183` keeps a **module-global
`engine`/`SessionLocal`** cached on `_engine_url` that **no fixture ever disposes** — its pooled
connections outlive the DROP, and a statement past psycopg's auto-prepare threshold can return
rows shaped for the dropped table's OIDs. It is **the cost of the gate-condition change**: with
`DATABASE_URL` unset that global engine was never created during a gate run, so the hazard was
unreachable until two gates ago. Candidate fix is one line in that fixture plus a control that
fails. Passed 38/38 in isolation and in two combinations with this card's changed predecessors.

**The operating rule this establishes, because it will recur:** a single red `[db]` test in a file
the card does not touch must be **re-run before it is believed, and the re-run recorded**. A gate
that is green only on its second attempt is not the same evidence as a gate green on its first,
and writing down only the green run would be the phantom-48-skip error in a new costume.

### Review cycle 1, 2026-10-18 — **8.5 / 10, PASS** (threshold 8)

No critical findings; 10 of 12 targeted mutants killed. The reviewer's own words for the shape of
it: the implementation **refutes its own card's arithmetic** rather than inheriting it.

**Two important findings. One is being fixed, one is routed.**

- **F-1 (fixed in cycle 1's fix) — AC-6's horizontal refusal had no boundary and two live
  mutants.** `layout.py:1410`. Verified by the orchestrator rather than taken on report: pitch is
  906 px, so two groups need **1774 px**, and a **7 × 10 in** trim has **1800 px** of usable width
  — **26 px of headroom**. Drop the `- gap` term and the predicate reads `1812 > 1800`, so **every
  pair in every 7 × 10 book silently stops pairing**, with the suite green. 7 × 10 is the narrowest
  trim that keeps two-up pages at all, so the surviving mutant sits exactly on the boundary that
  matters. AC-6 asked for an exact set "so a later card that widens it reds"; it got that on the
  vertical axis and not the horizontal one. `>` → `>=` survived vacuously for the same reason.
  (Headroom corrected: **+26 px at Book 1's own margins**, not the 19 px the orchestrator first
  measured off CARD-223's asymmetric spec — see the correction in the findings above. M1 reads
  `1812 > 1800` and unpairs every 7 × 10 pair either way, so the finding is unaffected.)
- **F-2 (routed to the architect station) — FR-040's AC-242..AC-246.** Already measured above and
  independently of the review: the reviewer declared it had **not** re-read `requirements.yml` and
  rested the finding on the diff's docstrings, so the measured table above is the stronger
  evidence and is what the amendment will be built from.

**Minors fixed in the same cycle:** F-3 (AC-4's measured-ink proof ran only on Book 1, where
`gutter_mm == outside_mm`, so *which* margin the row anchors to was proved as geometry and never
as ink — the owner's original complaint class); F-7 (the pairing corpus grew 900 → 3600 while its
guards still read `books >= 850` / `pages >= 3000` — **no minimum was lowered**, the guard merely
read stale); F-8 (`qr_group_caption`'s docstring claims it uses `band_identity`'s form while it
re-spells `f"Puzzle {n}"`).

**Residues carried rather than absorbed** — each is a measured bound, not a shrug:

- **F-4** `layout.py:3195`. AC-8's "the drawing stops on the rule the frame strokes, by
  construction" is **margin-dependent, not structural**: the reserve round-trips px → float mm →
  Fraction → rounded px and the two boundaries round independently. Measured at
  `bottom_mm = 9.525`: drawing_bottom 2834 against a footer_rule.y of 2835. Unreachable today
  (`BOOK1_PROFILE.bottom_in` is a single `Decimal("0.47")`). **Routed to whichever card makes the
  bottom margin per-profile**, where it becomes live: at a value where the slack rounds to 352 the
  whole book's pairs split silently — fail-safe in direction, silent in manner.
- **F-5** `book_pdf_generator.py:5050`. `_draw_two_up_qr_groups` raises rather than degrading above
  four-digit puzzle numbers. Pre-existing in kind — `_folio_reserve_px` carries the same bound —
  but the docstring's "unreachable from `puzzle_pages`" is new and is true only below 10 000.
- **F-6** The centred folio's horizontal clearance from the inner group's words is **10 px at two
  digits and 1 px at four**. They do not collide only because the folio's baseline (2885) sits one
  footer gap above the icon row (2923). Structural, but the single-page analogue of that claim is
  tested and the two-up one is not.
- **For CARD-226, which inherits this page:** the lower drawing's bottom now sits exactly **on**
  `footer_rule.y`, i.e. at the `<=` boundary of the frame's footer condition. Its divider rule and
  aligned bottoms must not consume any of the 353 px strip.

### Fix cycle 1, 2026-10-18 — four findings fixed, and the fix station found four more

**F-1 fixed, and both mutants now die.** Three new tests in `tests/test_book_qr_slot.py`: the row
fits at exactly `count·pitch − gap` of usable width and refuses one device pixel under
(parametrized over `count ∈ {1,2,3}` × both parities), the card's own 150.2 mm threshold is pinned,
and the boundary is restated on a **real** 7 × 10 trim so the synthetic sheet cannot read as a
hypothetical. Derived by hand from `QR_SLOT_MM` / `INTERIOR_FOOTER_GAP_PT` / `MM_PER_POINT` and
cross-checked against `_qr_group_line_px`, never against `qr_group_insets`. Verified by
hand-applied mutants, each reverted: **M1** (drop `- gap`) → exit 1, 8 failures; **M2** (`>` → `>=`)
→ exit 1, exactly the 6 boundary cases and nothing else, which is the direct proof that M2 was
vacuous before these tests existed.

The figures the boundary now pins: icon 236 px, gap 38 px, ceiling line 594 px
(`qr_group_caption(9999)` at 593.98, wider than `qr_link(9999)` at 575.98), pitch 906 px, rows
868 / **1774** / 2680 px for one / two / three groups, and two groups needing **150.1987 mm**
usable → **175.60 mm / 6.913 in** of trim at Book 1's margins.

**F-3, F-7, F-8 fixed.** The measured-ink proof and its control now run on `("book1", "unequal")` ×
both parities; the corpus guards were **raised** to `books >= 3595` / `pages >= 15000` against a
measured 3600 / 15994 (both still fail at 900, so the corpus still cannot shrink); the
`qr_group_caption` docstring now states that it is the **fifth** site spelling `f"Puzzle {n}"`,
that its earlier claim to use `band_identity`'s form was never true, and why coupling it to
`band_identity(n, None)` was rejected — that branch exists to report a *missing grade* and its
"Unrated" alternative would silently rewrite a caption a baseline pins. A false coupling traded
for a real one.

**Four things the fix station found that were not on its list** — all four worth keeping:

1. **The AC-4 control was rendering both parities onto page 5.** `book_page_spec` takes the frame's
   parity from the **page number**, so the EVEN case drew an ODD frame around an EVEN pair.
   Invisible on Book 1 (symmetric margins) and a real 12 mm mismatch on the asymmetric profile —
   i.e. it would have made the *new* unequal-profile control bogus, which is the worst kind of
   silent failure: a control that cannot fail, added in the act of fixing a control that could not
   fail. Fixed with parity-matched page numbers (ODD→5, EVEN→6), and `_ink_render` now **asserts**
   that the book's own `interior_frame` matches the profile the pair was fitted on rather than
   assuming it.
2. **Parametrising the strip test over both profiles does not by itself close the hole the review
   named.** Demonstrated with a 141 px (= gutter − outside) drawer-side translation: on an EVEN
   unequal page it moves the ink *inward from the outer edge* and stays clear of the retired gutter
   strip, so the strip test still passed on ODD. Hence a new anchor-in-ink test asserting the
   extreme footer-group ink column is one **outside** margin (83 px) in and not one **gutter**
   (224 px). This is the part of the fix that earns it; the parametrisation alone would have been
   theatre.
3. **The card's own 176.2 mm / 6.94 in was 0.6 mm loose** — same root cause as the orchestrator's
   correction above, and the test pins the measured 175.60 mm while asserting the card's figure
   only as a loose upper bound, rather than copying a wrong number into a test.
4. **`assert paired >= 100` now has only 6 cases of slack** (measured `paired = 106` at 3600 books).
   Not lowered and not touched, per instruction — but it is now the tightest floor in that test and
   the next card that shaves the pairing share will red it. Flagged before it bites.

### Merged — `1256982`, 2026-10-18T02:55:46Z. **0.3d against 1d (0.31x).**

Merge gate on `ff50725`: **8054 passed, 1 skipped, 0 failed in 784.07s**, `DATABASE_URL` set.
`git diff ff50725 HEAD -- src/ tests/ migrations/ pyproject.toml` is empty, so main's code tree is
byte-identical to the gated tree. ms/test 100 → **98**: the suite got faster while gaining 55 tests,
for the second wave running. Worktree and branch removed; review report copied to `meta/review/`
before the worktree went, since that is where the retrospective reads it from.

**This closes the KDP window.** `main` no longer prints a two-up page with one link for two
puzzles, so the standing "no book is to be generated for KDP" caveat is lifted.

**Rendered for the owner:** `~/Documents/nonogram-reviews/CARD-248/` — page 5 (the two-up page,
the one to look at), a crop of its footer strip, and pages 7 and 9 as **controls** (single-puzzle
pages, which must look exactly as CARD-223 left them). The exported interior is **3354646 bytes**,
matching `book_baseline_card248.json`'s recorded `interior_bytes` exactly — an independent
confirmation that main reproduces the recorded baseline byte for byte. Eyeballed by the
orchestrator: both groups present and correct, "Puzzle 1 · Solve it online / nonogram.example/p/001"
inner and "Puzzle 2 · …/p/002" outer on the odd page (AC-3's convention as chosen), the folio
centred, the gutter side clear. **The icons are still checkerboard placeholders, not scannable QR
codes** — by design, ADR-0036/R3; CARD-210 is the one-line change to a real host.

### Architect station, done at the merge rather than deferred

FR-040 amended in `requirements.yml` and `trace.yml` (validator: **0 errors**):

- the **statement** gains the footer strip in clause (a) and a new clause **(c)**, the width gate;
- **AC-242** re-measured 7.5 → **7.13 mm**, and re-kinded `happy` → `boundary`, because 28 cells is
  now the top of the paired range rather than a comfortable interior case;
- **AC-243's verdict flipped** — it said the pair shares a page; 32 cells is 6.24 mm, under the
  7.0 mm minimum;
- **AC-244 corrected** for the pre-existing off-by-one (7.1716 mm is the **32**-cell value against a
  **33**-cell `given`), so it has been refusing since before either card;
- **AC-245/AC-246** verdicts hold, parenthetical figures restated;
- **AC-376** (new) pins the exact refused set `{29,30,31,32}` — without it nothing in the registry
  pinned the new boundary at all, since AC-243..AC-246 now all read "two separate pages";
- **AC-377** (new) states the width gate, without which a 6 × 9 book silently has no two-up pages
  and the registry does not say why.

One dangling reference caught and fixed before it landed: the first draft of clause (a) cited
**FR-045**, which does not exist (the registry stops at FR-044). The interior frame genuinely has
no requirement of its own — a gap this registry already records at FR-032 — so the clause now names
that gap instead of inventing a pointer to nothing.

### One thing the render found that no test did

The lower slot sits **108 px short** of the outer edge the upper slot is flush against: that is
`_folio_reserve_px`, reserving the bottom-outer corner for CARD-200's folio. But this card moved a
two-up page's folio **into the footer**, and AC-7's test asserts it is *not also in the corner* — so
on any page that is actually two-up, the reserved corner is never used. **Measured cost: 18 of the
sweep's equal pairs refuse *only* because of that reserve**, including the **25 × 10** pair this
card's own body singles out as "already REFUSED at today's 108 px horizontal reserve"; it would pair
at 7.3269 mm. Filed as a backlog question rather than a finding, because the reserve's fallback is
real and documented (`book_pdf_generator.py:2097`: where `content_bottom` reaches below the footer
rule, the rule, the label and the centred folio are **all** omitted and the page keeps the corner
folio). What has to be proved first is that the fallback is unreachable **for a two-up page**, with
a control that fails — ADR-0039/R3's rule for exactly this shape.
