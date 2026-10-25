# CARD-294 — what the interior's round shape costs, measured

**A sibling of `card-293-vector-interior-comparison.md`, not an appendix to
it.** CARD-293's document is a closed spike report whose first line is "Spike.
Ships nothing", and its diff against `src/` is empty by its own AC-6. CARD-294
ships code. Folding a shipping card's measurements into that file would make it
a document about two different things with two different truth conditions, so
the pointer is at the foot of §6 there and the figures are here. The card's
item 3 offered exactly this choice.

**Every figure below is produced by `scripts/card294_curve_price.py`.** Re-run
it and this document reproduces. Nothing here is typed from memory: where a
number is also a test's business, the test re-derives it by a *different*
implementation, and that is said at each one.

---

## 0. The question, and why it was asked first

CARD-293 proved the vector mechanism cheap — 163 lines for font embedding,
22.4× smaller files, 8.5× faster per page — but it drew **one puzzle page**,
and its own §6 named what it had not priced. Reading its primitive table, the
gap was concrete: it drew **straight lines, rectangles, fills and text**. It
never drew a **round shape**.

PDF has no circle primitive. PostScript's `arc` does not survive into a
content stream, so every round mark in the interior — the difficulty dots, the
guide's key strip — is cubic Béziers through the `c` operator. That was the
only primitive in the whole interior nobody had emitted or measured, and the
phase's remaining four cards were scoped on the assumption that it is cheap.
CARD-294 was ordered first to find out, with "awkward and more expensive than
expected" declared in advance as a valid outcome.

**It is not awkward. The verdict is in §4.**

---

## 1. The price in lines of code

Counted mechanically by `ast` — blanks, comment lines and docstrings excluded —
the way CARD-293's §1 table was counted, over
`src/nonogram/admin/book_vector.py`.

| piece | code lines |
|---|---|
| `ContentStream.curve` (the bare `c` operator) | 5 |
| `ContentStream.begin_path` (`m`) | 2 |
| `ContentStream.close_path` (`h`) | 2 |
| `ContentStream.paint` (`S`/`f`/`B`) | 2 |
| `ContentStream.round_mark` (the four-Bézier circle) | 13 |
| **the round shape, total** | **24** |
| | |
| `ContentStream.line` (for scale) | 4 |
| `ContentStream.line_to` (for scale) | 2 |
| `ContentStream.rectangle` (for scale) | 6 |
| the straight-line vocabulary, total | 12 |
| the embedded face, total (CARD-293 estimated 163) | 171 |

**24 lines, of which 13 are the circle itself.** Read it against the two
numbers beside it: the whole straight-line vocabulary CARD-293 already proved
is 12 lines, and the font work it priced at 163 came in at 171. So the
unpriced primitive is **twice the straight-line vocabulary and a seventh of
the font work** — the smallest of the three pieces of this card, not the
largest.

The 13 lines are: a radius refusal, the kappa product, four coordinate names,
and then one `begin_path`, four `curve`s, a `close_path` and a `paint`. There
is no iteration, no geometry library and no special case. The reason it is so
small is that the four quadrants are the *same* four control-point expressions
with the signs permuted, which is a property of a circle and not of this
implementation.

---

## 2. The price in operators

Counted by a hand-written scanner in the script. The same counts are asserted
in `tests/test_book_pdf_vector_primitives.py` by
`TestVectorPrimitives_TheRoundMarkCostsSevenOperators`, which tokenises with a
regular expression instead — two implementations, because a price is a claim
(CLAUDE.md: prefer an independent second implementation over re-deriving a
value with the function under test).

| shape | operators | the tokens |
|---|---|---|
| straight line | 3 | `m l S` |
| rectangle (stroked) | 2 | `re S` |
| rectangle (filled) | 2 | `re f` |
| one string of text | 6 | `g BT Tf Td Tj ET` |
| a stroke width and a tone | 2 | `w G` |
| **round mark (filled)** | **7** | `m c c c c h f` |
| **round mark (outlined)** | **7** | `m c c c c h B` |
| one bare cubic | 2 | `m c` |

**Seven operators per round shape** — `m`, four `c`, `h`, and one paint — and
it is the same seven whichever way the mark is painted: the fill choice changes
the last token and nothing else, which is pinned by
`test_the_paint_operator_is_the_only_thing_the_fill_choice_changes`.

**Read against the rest of the vocabulary, a round mark is the most expensive
primitive by exactly one operator over a string.** That is the comparison the
"are curves awkward?" question needed, and it is asserted rather than narrated
(`test_pdf_offers_no_shorter_spelling_in_this_vocabulary`).

**In bytes**, measured on the real emitted stream at the radii that matter:

| shape | raw | deflated |
|---|---|---|
| straight line | 24 B | 30 B |
| round mark, r=6 px (the 1.0 mm floor dot) | 189 B | 85 B |
| round mark, r=21 px (the band cap) | 189 B | 88 B |
| round mark, r=60 px | 176 B | 94 B |
| **a three-dot difficulty glyph** | **528 B** | **168 B** |

A round mark is **176–189 B of raw stream** before Flate (six numbers per
curve, four curves) against **24 B for a straight line** — and note the line's
*deflated* size is larger than its raw size, which is the usual Flate overhead
on 24 bytes and the reason per-shape compression is only meaningful inside a
whole page. Against CARD-293's
measured 11,680 B raw / 1,339 B deflated for a whole 30×30 page, a three-dot
glyph is **4.5 % of one page's raw stream and 12.5 % of its deflated size** —
and it appears once per page, not 900 times. Nothing about the file-size
conclusion moves.

---

## 3. The accuracy, and one figure that is not the one usually quoted

Swept at 2,000,001 points over one quadrant of the unit circle, in closed form.

| kappa | signed radial error / r | max abs | bounding box |
|---|---|---|---|
| **`4*(sqrt(2)-1)/3` = 0.5522847498307936 (shipped)** | **[+0.0000e+00, +2.7253e-04]** | **2.7253e-04** | **exact** |
| 0.5519150244935105 (minimises the maximum) | [−1.9608e-04, +1.9608e-04] | 1.9608e-04 | **under** the declared diameter |

**The 1.96e-4 figure that circulates for "the four-Bézier circle" belongs to
the second row, not the first.** It is the minimax kappa, whose error
alternates in sign. The shipped kappa — the one that makes each cubic pass
exactly through the circle at its own midpoint — is **2.7253e-4, 39 % worse**,
and its error is **one-signed**: the curve bulges very slightly *outside* the
true circle and touches it exactly at eight places, so a mark is never drawn
smaller than it was asked for.

**That trade is deliberate and it is the right way round here.** The shipped
kappa keeps the mark's bounding box *exactly* the declared diameter, and
`nonogram.export.layout.difficulty_dots` states a diameter while
`DifficultyDots.__post_init__` reasons about whether two dots of a row touch
(`left <= right + 1` is a refusal, added in CARD-228's cycle 1 as F-004). A
mark 0.02 % under its stated diameter would not break that reasoning, but it
would make the stated number and the drawn number two different numbers for no
gain a reader could see. Exactness of the stated diameter is worth 0.8 parts in
a hundred thousand of radial error.

This was measured because it was measured, not assumed: the figure in the
module's own docstring was wrong on the first pass — it said 1.96e-4, copied
from the number everyone quotes — and the sweep corrected it.

---

## 4. The verdict, at the size the book actually prints

The dot sizes are **COMP-007's, not sizes chosen for a nice answer**. The floor
is `MIN_DIFFICULTY_DOT_MM` = 1.0 mm, below which `difficulty_dots` returns
`None` and nothing is drawn at all; the ceiling on a puzzle page is
`DIFFICULTY_DOT_RATIO` of a `HEADER_BAND_MM` band, asked of the function rather
than multiplied out.

The stream writes coordinates to 0.001 pt = **0.000353 mm**. That is the number
to read the error against.

| printed dot | radius | worst error | device px @ 300 | @ 600 | @ 1200 | @ 2400 |
|---|---|---|---|---|---|---|
| floor, 1.000 mm (below it nothing is drawn) | 0.5000 mm | 1.363e-04 mm | 0.00161 | 0.00322 | 0.00644 | 0.01288 |
| puzzle-page band cap, 3.556 mm | 1.7780 mm | 4.846e-04 mm | 0.00572 | 0.01145 | 0.02289 | 0.04579 |

**The verdict: four Béziers are accurate enough, and the margin is stated
rather than waved at.** At the largest dot the book prints, the worst the
approximation deviates from a true circle is **0.00048 mm — one forty-fourth
of a device pixel at 1200 DPI**, which is a press RIP, and one 175th of a pixel
at the 300 DPI the book is composed at. At the smallest dot it is 0.00014 mm,
one 155th of a 1200 DPI pixel. **No raster device in the pipeline can resolve
it**, which is the claim that matters and is the one these figures support.

**What is *not* claimed here, because this card has no measurement for it:**
how a printed dot looks on paper. Dot gain on uncoated stock is still measured
by nobody — ADR-0037's History records that gap, with the first printed book as
its revisit trigger — and whatever it turns out to be, it will be a spreading
of ink at the *edge* of the mark, not a deviation of the mark's path. The two
are independent, and this document settles only the second.

**And the honest half of that answer: at print size the curve is not the
limiting term — the number format is.** Measured on the *emitted* operands
rather than on the constant,
`TestVectorPrimitives_TheRoundMarkIsAccurateAtThePrintedDotSize` finds the
relative error at the **floor** dot is **3.457e-4** of the radius, *worse* than
the pure Bézier's 2.7253e-4, because at a 0.5 mm radius the stream's own
0.001 pt coordinate rounding stops being negligible beside it. The ranking of
the two terms inverts somewhere between the floor dot and the band cap. It
changes no conclusion — the total is still 0.008 of a device pixel at
1200 DPI — but it means a future card that wanted a *more* accurate round mark
would have to spend a decimal place in `_PLACES`, not a better kappa, and that
is worth knowing before someone optimises the wrong half.

---

## 5. What the card found that its own brief did not say

**One: `tests/test_book_difficulty_dots.py`'s "exactly one drawing site" guard
has a fifth route it cannot see.** `TestDifficultyDots_HasExactlyOneDrawingSite`
asserts that exactly one function in `src/nonogram/**` puts a round mark on a
page, and it does so by walking the tree for calls to Pillow's ellipse family
(`arc`, `chord`, `circle`, `ellipse`, `pieslice`) plus three other syntactic
families. Its own docstring is admirably careful about what it reaches: "the
claim is the width of the mechanism and no wider", with four routes guarded and
the rest listed as named limits. `ContentStream.round_mark` is outside all
four — it is not a Pillow call at all.

The guard is **not wrong today**: nothing calls `round_mark`, so there is still
exactly one round mark in the package, and
`TestVectorVocabulary_TheRoundMarkRouteTheOldGuardCannotSee` in this card's own
test file asserts that (`round_mark(` appears in no module but the vocabulary's
own, and the `c`-operator string is written in exactly one module) — a
**tripwire on the ordinary spelling, not a derived enumeration**, and its own
docstring says so rather than borrowing ADR-0039/R2's default-deny language it
does not earn. Widening
the old guard is **not this card's to do**, because widening it means deciding
where the *vector* difficulty glyph lives, and that is CARD-295/296's. What
this card can do, and has done, is make the route countable so the day a page
card draws a vector dot the decision is taken rather than slipped past: that
test goes red at exactly that moment, and the right response is to replace it
with a fifth route in the old guard rather than to relax it.

**Two: the card's brief says the guide's round mark is what ADR-0036/R4
forbids typing as a character.** That is right, and the new vocabulary closes
the other half of it by construction: `ContentStream.text` refuses any
character `/WinAnsiEncoding` cannot carry, by name, rather than substituting —
so a dot typed as `●` (U+25CF) is not merely discouraged, it raises. The
refusal and its control (`·`, `—` and `é`, all non-ASCII, all accepted) are in
`TestVectorVocabulary_RefusesWhatItCannotDraw`.

**Three: `Touches:` on the card named `book_pdf_generator.py` and nothing in
this change edits it.** The vocabulary landed as a new module beside it,
`src/nonogram/admin/book_vector.py`, which is what the card's own Worktree
notes asked for ("a new file beside `book_pdf_generator.py` moves with it in
the same `git mv`" when CARD-273 runs). There is nothing to wire into the
generator until a page card exists to call it, and wiring with no caller would
have been the scope growth G-1 forbids.

---

## 6. The door every figure came through

```
scripts/card294_curve_price.py                      — every number above
src/nonogram/admin/book_vector.py                   — the vocabulary measured
tests/test_book_pdf_vector_primitives.py            — the independent re-derivations
tests/helpers/pdf_vector.py                         — the poppler readers
tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face
                                                    — ADR-0042/R5's check, flipped
                                                      from review-lens by this card
pdftoppm / pdftotext (poppler)                       — the engine that did not
                                                      write the file
```

Every shape claim in the test file is made on a raster poppler produced, not on
a stream this project parsed. Where poppler is absent the tests **skip with
that reason named** rather than passing — a missing engine is a missing
control, and the figure above was taken on a host that had it.
