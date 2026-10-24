# CARD-208: Printed clue numbers sit in ruled boxes, like the player's clue cells

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/208-printed-clue-boxes
**Worktree:** —
**Source:** owner's Google Doc "Nonograms - Print layout", 2026-10-13 (under "## Puzzle page header": "Have clue numbers in box:" followed by a sample image)
**Idea:** —
**Wave:** —
**Depends on:** CARD-204, CARD-222
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/property/test_book_pdf_geometry.py, tests/property/test_book_layout.py, tests/test_book_pdf_ink_mode.py, tests/test_book_interior_type_floor.py
<!-- DECOMPOSED 2026-10-24 (orchestrator, owner request "decompose 208 so the
shading has ACs"). `Depends on:` gained CARD-222 as the 2026-10-14 amendment
instructed and nobody had applied; both CARD-204 (`cd641df`) and CARD-222 are
`done`, so the field was stale, not blocking. `Touches:` gained
tests/test_book_pdf_ink_mode.py (AC-12 corrects a claim that lives there) and
tests/test_book_interior_type_floor.py (AC-7 and AC-11 are measured at the type
floor, and the file is already CARD-207's too — they serialize). See the
`## Decomposition 2026-10-24` section at the end: SEVEN ACs became THIRTEEN, and
the card was deliberately NOT split. -->

**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**Read this first — one inference the card rests on.** The doc line is
"Have clue numbers in box:" followed by an image the card drafter could not
read (Google Docs serves the doc as text; the image is not in it). The reading
taken here is the one the surrounding text supports and the one the player
already implements: **each clue number sits in its own ruled cell-sized box, so
the clue gutters read as a continuation of the grid** (`admin.css`
`.player-clue.is-col` / `.is-row` draw exactly that on screen). If the owner
meant something else by the image — a single box around the whole clue, say —
this card is re-sliced at the decompose station rather than reinterpreted in the
worktree.

**Current behaviour (verified by reading the code).**

- `export.layout.ClueEntry` (`layout.py:752`) already places one *conceptual*
  box per clue number: `value`, `line`, `depth` (0-based from the outer edge,
  right-aligned for rows / bottom-aligned for columns) and the box's centre.
- Nothing rules those boxes. `_write_clues` (`book_pdf_generator.py:1193`)
  draws the digits only; `_stroke_drawing` (`:1118`) strokes the **grid's**
  lines plus `slot.frame`, whose own added ink is "its left and top sides, the
  outer edges of the two clue gutters" — so the gutters today have an outer
  edge and an inner edge (the grid's border) and nothing between them.
- So a printed puzzle's clue numbers float in an unruled gutter, while the
  same puzzle's clues on screen sit in boxes.

**What changes.**

1. **Geometry in COMP-007** (ADR-0036/R2 — the admin panel may not place
   things): `Layout` gains the clue gutters' own ruled lines — the
   cross-gutter boundaries at every `depth` step, in both gutters, with the
   same every-5th weighting rule the grid uses where it applies (the lines
   continuing the grid's own row/column boundaries are the heavy ones that are
   already heavy on the grid, so a clue box lines up with its row/column).
   Express them in the same shape `vertical_lines`/`horizontal_lines` already
   use (`GridLine`: position + width), so the renderer consumes positions and
   derives nothing.
2. **Drawing in COMP-009**: `_stroke_drawing` strokes the new lines with the
   existing thin/heavy order (thin first, heavy last — the overlap rule its
   docstring states), pure `INK`, no new weight (ADR-0037/R2).
3. **Scope: book pages only, for now.** CON-019 makes the CLI's and web UI's
   PNG/SVG/PDF exports byte-identical regardless of book geometry, and
   `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` pins the A4 golden. The
   new lines are therefore emitted **only under a book `PageSpec`**, and the
   default spec's layout stays byte-identical. Record in the Worktree notes
   that the owner may want the single-puzzle exports to match later — that is a
   separate card with a golden refresh, not a quiet widening here.
4. Both a single puzzle page and each two-up slot get the boxes (a two-up slot
   is a puzzle page).

## Acceptance criteria

- **AC-1** (happy): *Given* a puzzle printed on a book page, *when* the page is
  drawn, *then* every clue number is enclosed by four rules — the gutter's
  outer edge or a cross-gutter rule on each side, and the grid's border or a
  cross-gutter rule on the others — forming one cell-sized box per number.
  (test: `TestBookPuzzleFrame_EveryClueNumberIsBoxed`)
- **AC-2** (happy, alignment): *Given* any book puzzle page, *when* it is
  drawn, *then* each clue box's inner boundary coincides exactly with its own
  row's or column's grid boundary — a clue box is never half a cell out of
  register with the row it belongs to. (test:
  `PropertyTest_BookLayout_ClueBoxesRegisterWithTheirLines`)
- **AC-3** (happy, weights): *Given* any book puzzle page, *when* it is drawn,
  *then* a clue-gutter rule continuing a heavy (every-5th or border) grid line
  is heavy and every other is thin, both at the PageSpec's own widths.
  (test: `TestBookPuzzleFrame_ClueRuleWeightsFollowTheGrid`)
- **AC-4** (happy, two-up): *Given* a two-up page, *when* it is drawn, *then*
  both slots carry boxed clues. (test: `TestBookPdfTwoUp_BothSlotsBoxTheirClues`)
- **AC-5** (edge, zero clue): *Given* a line whose clue is `(0,)`, *when* the
  page is drawn, *then* its single `0` is boxed like any other number.
  (test: `TestBookPuzzleFrame_ZeroClueIsBoxed`)
- **AC-6** (guard): *Given* any generation request, *when* the CLI or web UI
  writes a PNG, SVG or PDF, *then* the bytes are identical to before this card.
  (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`,
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`)
- **AC-7** (edge, digit legibility): *Given* the smallest cell a book may print
  (CON-018/INV-006's floor), *when* a page is drawn, *then* the clue digits
  still sit inside their boxes with clearance on both sides — the boxes do not
  clip the digits. (test: `TestBookInteriorTypeFloor_ClueDigitsFitTheirBoxes`)

### The shading — AC-8..AC-13, added 2026-10-24

<!-- The 2026-10-14 amendment put the 5% grey clue-area shading into this card's
scope and then added not one acceptance criterion for it, so the card's gate
could have passed with the shading absent. These six close that. They are
APPENDED rather than renumbered: CARD-227, CARD-288 and the 2026-10-17 registry
delta all refer to this card's ACs, and renumbering would silently re-point
them. -->

- **AC-8** (happy, the shading exists and is bounded by the boxes): *Given* a
  puzzle printed on a book page, *when* the page is drawn, *then* **every clue
  number's box is filled with the clue tone**, and the fill stops at the box's
  own rules — no tone outside the two clue gutters, none inside the puzzle grid,
  none under the header band or in the margins. (test:
  `TestBookPuzzleFrame_EveryClueBoxIsShaded`, with the complement asserted in
  the same class as a named control: `test_no_tone_outside_the_clue_gutters`)
- **AC-9** (happy, tone ordering — not a literal colour): *Given* a drawn book
  puzzle page, *when* its levels are read off the ink, *then* **paper is lighter
  than the clue tone, the clue tone is lighter than every rule on the page, and
  the clue digits are the darkest thing in the gutter** — asserted as an
  ordering over measured levels, never as one literal RGB triple. (test:
  `TestBookPuzzleFrame_ClueToneSitsBetweenPaperAndInk`) *This is CARD-227's
  AC-2 idiom deliberately reused: that card asserts its grey cell lines the same
  way, and ADR-0037's 2026-10-17 note records why tone is now load-bearing —*
  "the furniture/grid distinction now rests on **tone**, not weight, because
  width has reached the device floor".
- **AC-10** (guard, one named tone, one function, three downstream callers):
  *Given* the clue tone, *then* it is **a single named module-level constant in
  COMP-007 and the shading is drawn by exactly one function**, which CARD-209,
  CARD-229 and CARD-232 call rather than re-implement. (test:
  `TestBookPuzzleFrame_TheClueToneHasOneDefinition` — an AST guard, **default-deny
  per ADR-0039/R2**: it refuses any literal tone triple or fill call in the
  clue-area code path that is not the named constant / the one function, instead
  of looking for the spellings it already knows. ADR-0039/R1 applies: it ships
  with a control that FAILS — a second literal reintroduced in a *different*
  spelling must red it, or the claim narrows to the spellings it checks.)
- **AC-11** (edge, legibility at the floor, measured): *Given* the smallest cell
  a book may print (CON-018/INV-006's floor) **and** the clue digits at CON-020's
  exemption, *when* a page is drawn, *then* **the digits' contrast against the
  clue tone is measured and recorded**, and the tone is light enough that the
  digits read. (test: `TestBookInteriorTypeFloor_ClueDigitsReadAgainstTheirTone`
  — the same file as AC-7, so the floor is measured once.) **Recorded as a
  figure, which makes it a claim: re-derive it before the card merges.**
- **AC-12** (guard, the claim this card falsifies): *Given* this card ships a
  mid-tone into the interior's content, *then* the two copies of the sentence
  **"The interior's content has always been pure black and white: COMP-007 draws
  `INK = (0, 0, 0)` on `BACKGROUND = (255, 255, 255)` and nothing else"** —
  `tests/test_book_pdf_ink_mode.py:21` and
  `src/nonogram/admin/book_pdf_generator.py:322` — **are corrected in the same
  commit**, and the card records whether `_SOLVED_GRID_GRAY = (160, 160, 160)`
  (`:1544`, CARD-197's solved-page gridline tone) had already falsified them
  before this card. (**gate**: both copies read at HEAD; a claim may only change
  together with what makes it true. Not a standing test — no test can know a
  docstring is honest.)
- **AC-13** (guard, the tone survives the ink mode, and where it is measured):
  *Given* a book whose `interior_ink_mode` is greyscale, *when* its pages are
  composed, *then* the clue tone converts **identically** — `(v, v, v) → v`, the
  identity the existing G-2 assertions already require — and every page still
  carries pure black while interior page 1 stays blank. (test: the existing
  `tests/test_book_pdf_ink_mode.py` assertions at `:350`–`:370`, re-run and named
  by node id; this AC adds no new mechanism, it **pins that the shading does not
  break one that exists**.) **Measure the tone on the page bitmap COMP-009
  returns, not on the written PDF**: the interior is JPEG-encoded, so the tone
  rings near the digits and rules after encoding and a post-encode equality is
  not available. If the card wants to claim anything about the *file*, it
  measures and records the JPEG deviation rather than asserting equality.

## Guardrails

- G-1: The puzzle grid's own lines, frame and cell fitting are unchanged — this
  card adds gutter rules and nothing else (test:
  `PropertyTest_BookPdfGeometry_GridUnchangedByClueBoxes`).
- G-2: CLI and web-UI exports stay byte-identical (CON-019, ADR-0036/R1).
- G-3: No geometry computed in `book_pdf_generator.py` — every position comes
  from `export/layout.py` (ADR-0036/R2).
- G-4: Do not change puzzle-page placement or the QR slot — owned by CARD-204.
- G-5: Out of scope — the answer/solution pages' clue rendering (CARD-197's
  solved layout) is not touched by this card.
- **G-6: the shaded rectangle's bounds come from COMP-007, not from the
  renderer.** `ClueEntry` (`layout.py:934`) carries `center_x`/`center_y` and a
  0-based `depth` but **no extent**, so there is nothing to fill yet. Add the
  extent in COMP-007 and have COMP-009 consume it. A renderer deriving the box
  from `center_x ± cell // 2` is geometry computed in the admin panel —
  ADR-0036/R2 and this card's own G-3. Carry `major` on the new gutter rules the
  way `GridLine` already does (`:907`, "the *reason* for the width, so a renderer
  may say so without re-deriving the modulo"), so CARD-227's weights and tones
  need no second derivation either.
- **G-7: do not ship the artifact's figure literally** — see
  `## The 5% is provenance, not a specification` below. ADR-0037/R2's 2026-10-17
  amendment is the precedent and the warning: the *same* owner artifact's
  0.3 pt grey cell line broke that rule **three ways at once** (ratio, colour and
  minimum), and shipping it as written "would have re-opened the single
  complaint this ADR exists to close, and would have done it quietly, inside a
  card scoped as something else".
- **G-8: the shading is not a second mechanism for the boxes.** One pass over the
  clue area produces both the rules and the fills, from one set of COMP-007
  bounds. If the card finds itself with two independent notions of where a clue
  box is, that is the split condition — stop and say so rather than keeping them
  in step by hand.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-208 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-016 (the printable puzzle page), FR-031/NFR-008 (the book's cell
  floor, which AC-7 measures against).
- **ADR:** ADR-0036/R1, ADR-0036/R2, ADR-0037/R2.
- **CON:** CON-018, CON-019, CON-020.
- **Components:** COMP-007 (`export/layout.py` — the new line positions),
  COMP-009 (`book_pdf_generator.py` — stroking them).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

—

## Amendment 2026-10-14 — the owner's "Puzzle page layout" artifact

The artifact names this card by number — *"Clue areas shaded 5% grey, with each number in its
own box (CARD-208)"* — and adds the shading to its scope:

- **The clue areas are shaded 5% grey**, in addition to each number sitting in its own box.
  Both belong here because both are drawn by the same clue-area code; splitting them would put
  two cards in one function.
- The **line weights** (0.3 pt cells grey, 0.8 pt every fifth, 1.3 pt outer border) are
  **CARD-227**, not this card.
- The grey boxes are reused by three later cards — the guide's examples (CARD-229), the solution
  tiles (CARD-232) and CARD-209's wide-short pages. So expose the shading through the same
  function all of them call, not as a literal repeated per page kind.
- **Depends on:** CARD-222 (the frame). Update the card's `Depends on:` field at dispatch.
- The card's own body rests on a doc image the orchestrator could not read; the artifact's
  mockups now show the intent, so re-read them before implementing rather than guessing.

## Decomposition 2026-10-24 — the shading now has acceptance criteria

Owner request: *"decompose 208 so the shading has ACs"*, after CARD-288's
scheduling section recorded that the 2026-10-14 amendment put the 5 % grey
shading into this card's scope and **none of its seven ACs covered it** — so the
card's AC/EC/G gate could have passed green with the shading absent.

**Seven ACs became thirteen.** AC-8..AC-13 above are appended, not renumbered:
CARD-227, CARD-288 and the 2026-10-17 registry delta all cite this card's ACs by
number, and renumbering would silently re-point them.

### The card is deliberately NOT split, and here is the argument

`sizing.max_estimate` is `1d` and step 6a of decompose splits anything above it.
Thirteen ACs across COMP-007 and COMP-009 looks like a split. It is not, for one
measured reason: **the shading reuses the boxes' own geometry.** G-6 adds the
clue box's extent to `ClueEntry`, and once that extent exists the shading is one
fill loop over the same bounds the rules are stroked from. The marginal work over
the boxes alone is a fill, a named tone, and the tone decision below — not a
second mechanism. The 2026-10-14 amendment said the same thing in fewer words
("both are drawn by the same clue-area code; splitting them would put two cards
in one function") and that reading survives contact with the code.

**The split condition is written down instead, as G-8**: if the round ends up
with two independent notions of where a clue box is, it stops and says so. That
is a condition a round can check, unlike an estimate.

What is *already* split, correctly, and stays split: **CARD-227 owns the three
line weights and the grey cell lines** (and says so itself — "This card owns the
three line weights only"); **CARD-209/229/232 own their own page kinds** and call
the one function AC-10 requires this card to expose. This card is the **puzzle
page** — single and two-up — plus that function.

### The 5 % is provenance, not a specification

The whole surviving specification of the shading is **one quoted sentence**:
*"Clue areas shaded 5% grey, with each number in its own box (CARD-208)"*. The
owner's 2026-10-14 "Puzzle page layout" artifact is **not in this repo** — only
that line, quoted here and in CARD-227 — and this card's own body already records
that its box reading rests on a doc image the drafter could not read. **Checked
at decompose: there is no mockup in `meta/design/` to re-read.** The amendment's
instruction to "re-read them before implementing" cannot be followed as written,
and saying so is better than a round discovering it.

**That does not block the card**, because this board already has the precedent
for exactly this and it is in ADR-0037 itself. The 2026-10-17 amendment to
ADR-0037/R2 took the *same* artifact's 0.3 pt grey cell line, measured it, found
it broke the rule three ways — ratio, colour, **and** a one-pixel line 2.4× under
the floor the ADR had explicitly rejected — and shipped 0.48/1.28/2.08 pt
instead, keeping the owner's figures quoted as provenance. CARD-227's body then
says outright: **"Do not 'restore' the artifact's figures if you notice the
mismatch: it is deliberate."**

So the obligation here is the same shape. **5 % grey is 242 of 255.** Settle it,
do not type it:

* **It must be distinguishable from paper after print, not only on screen.**
  A 5 % tint is at the low end of what print-on-demand reproduces predictably,
  and dot gain moves it the other way. The card records what it chose and why.
* **It must not be confusable with CARD-227's grey cell lines**, which land in
  the same gutters' neighbourhood. AC-9's ordering is the mechanism; the two
  cards must not independently pick two near tones. Whichever lands first names
  the constant AC-10 requires, and the second reads it.
* **The project has no grey convention to inherit.** The only existing tone is
  `_SOLVED_GRID_GRAY = (160, 160, 160)` (`book_pdf_generator.py:1544`), whose own
  comment records that the author looked "for an existing gray convention first —
  there is none". The one grey *fill* precedent is the retired
  `_draw_difficulty_box` (`:2472`, CARD-201), whose grey-filled highlight became
  a plain bordered box. Neither is a convention; this card establishes one, which
  is why AC-10 insists on one named constant and one function.
* **The owner's figure is kept quoted in `Source` and in the amendment**, as
  ADR-0037/R2 did. Do not quietly overwrite it with the shipped value.

**One owner question, non-blocking, worth asking before the renders rather than
after:** whether "clue areas shaded" means *each number's own box is filled*
(the reading taken, consistent with the sentence's second clause and with the
player's `.player-clue` cells) or *the whole gutter band is filled behind
unruled numbers*. The ACs are written for the first. If the owner means the
second, AC-8's complement control is what fails, and the card is re-sliced here
rather than reinterpreted in a worktree — the same rule the card's own body
already sets for the box reading.

### The claim this card falsifies, which is why AC-12 exists

Two places in the tree assert the interior has no mid-tone at all:
`tests/test_book_pdf_ink_mode.py:21` and
`src/nonogram/admin/book_pdf_generator.py:322`, both reading *"The interior's
content has always been pure black and white: COMP-007 draws `INK = (0, 0, 0)`
on `BACKGROUND = (255, 255, 255)` and nothing else."*

**Checked at decompose: no standing test enforces that sentence, so the shading
does not red the suite.** `test_book_pdf_ink_mode.py`'s G-2 assertions
(`:350`–`:370`) require the greyscale conversion to be the *identity on the
page's own levels*, that pure black and pure white counts match, that every page
carries pure black and that interior page 1 is blank — all of which a flat tint
satisfies. The sentence is **prose**, and prose is where this board's claims rot:
it is already arguably false for the solved pages' `_SOLVED_GRID_GRAY`, and this
card makes it false beyond argument. AC-12 corrects both copies in the same
commit and asks the card to record whether CARD-197 got there first.

### Scheduling — three cards share this file set, and none of it is a dependency

* **CARD-227** (three line weights, grey cell lines) and this card both work the
  clue gutters' neighbourhood and both pick a tone. They must not run
  concurrently, and whichever lands first owns the named constant. Not a
  `Depends on:` in either direction — AC-3 reads "at the PageSpec's own widths",
  so it is weight-agnostic by construction — but note that **AC-3's "heavy/thin"
  is a two-weight wording and CARD-227 makes the grid three-weight**, so if 227
  lands first AC-3 is restated in its terms at dispatch.
* **CARD-288** (the geometry file's 3,820 renders) shares
  `tests/property/test_book_pdf_geometry.py`. They serialize. If this card lands
  first, CARD-288 converts five tests instead of four; if CARD-288 lands first,
  **this card's brief must say to write its new
  `PropertyTest_BookPdfGeometry_GridUnchangedByClueBoxes` on the lazy
  `interior_stream` walk**, not on `interior_pages`, or CARD-288's work is partly
  undone here. That obligation is recorded on both cards.
* **CARD-207** shares `tests/test_book_interior_type_floor.py` and
  `tests/test_book_pdf.py`. Serialize.
* `src/nonogram/export/layout.py` and
  `src/nonogram/admin/book_pdf_generator.py` are both declared
  `conflict.hotspots`, so the dispatcher serializes this card against anything
  else touching them regardless of overlap score.
