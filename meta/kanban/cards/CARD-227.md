# CARD-227: The printed grid's rules get three weights — cell, every fifth, outer border, at the owner's own figures

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/227-grid-rule-weights
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The rules behind it": Grid lines ("0.3 pt cells in grey, 0.8 pt every fifth line, 1.3 pt outer border"). **Confirmed by the owner 2026-10-25** on CARD-293's proof, after ADR-0042 removed the device floor that had forced these figures to be scaled.
**Idea:** —
**Wave:** 63
**Depends on:** CARD-222 (the frame these rules are measured inside), CARD-295 (the puzzle page must be drawn as operators before these widths are safe — see "Why this card waits")
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/test_book_pdf_band.py, meta/architecture/decisions/adr/0037-book-puzzle-page-band-and-strokes.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The printed grid gets the three-weight hierarchy the owner's artifact asked for,
stated in points so it is resolution-independent:

- **0.3 pt** for ordinary cell lines, in grey (not black).
- **0.8 pt** for every fifth line, both axes.
- **1.3 pt** for the outer border.

**These ARE the figures in the owner's artifact, and that is the change.** From
2026-10-17 to 2026-10-25 this card carried 0.48 / 1.28 / 2.08 pt — the same
ratios (1 : 2.667 : 4.333) scaled by **×1.6** so the thinnest line would be 2
device pixels at 300 DPI instead of one. **That scaling was never a design
opinion**; it was an arithmetic correction for a raster device floor, and
ADR-0042 removed the floor by making the interior a content stream. The owner
confirmed the unscaled figures on 2026-10-25 after reading
`~/Documents/nonogram-reviews/CARD-293/card293-proof-vector.pdf` — page 1, their
own numbers — against page 2's scaled version.

So the instruction that stood here for eight days, *"Do not 'restore' the
artifact's figures if you notice the mismatch"*, is **withdrawn**. The artifact's
figures are the decision. ADR-0037/R2 carries them as of 2026-10-25.

## Why this card waits for the vector phase — and must

**At these widths a raster grid is the refused configuration.** This is the one
thing not to get wrong, because the card looks like a stroke-width tweak and the
failure is silent.

Measured by poppler on the rendered vector file (CARD-293 AC-2):

```
0.3 pt cell line, vector :  2 px at grey 89 @ 300 DPI ;  5 px at grey 89 @ 1200 DPI
```

Grey 89 is `round(255 × 0.35)` — the declared tone, hit **exactly at both
resolutions**, with the width scaling ×4 and the tone not moving. A renderer
resolves a declared width at whatever resolution it runs.

A **raster** generator does not do that. It rounds each stroke to an integer
pixel count, and at 300 DPI these figures round to **1 / 3 / 5 px** — a
one-pixel grey cell grid, which is exactly what ADR-0037/R2's 2026-10-17
amendment refused on the evidence of **7 of 17 reviews** of the 450-puzzle book
complaining about faint grid lines. Shipping these widths onto a raster surface
would quietly re-open the single complaint ADR-0037 exists to close.

Hence `Depends on: CARD-295`, and hence R2's new statement binds the figures to
the medium rather than carrying a pixel minimum a vector writer can neither
satisfy nor violate. **If you find yourself able to apply these weights to a page
that is still a bitmap, stop — that is a finding, not a task.**

## What is already landed, and what this card still owes

- **ADR-0037/R2 carries the figures** (amended 2026-10-25; see that ADR's
  History). Its `check:` is still `{kind: review-lens}` and **this card upgrades
  it to its own test at landing** — see Obligation 1.
- **FR-033** was amended the same day; read it rather than this card's paraphrase.
- **ADR-0042/R7 is discharged** — its "the weights wait on a printed proof"
  clause was rewritten when the owner decided.

## Acceptance criteria

- **AC-1** (happy, three weights, read from the stream): *Given* a drawn grid,
  *when* its rules are read **from the content stream of the written PDF**, *then*
  ordinary cell lines are 0.3 pt, every fifth line is 0.8 pt and the outer border
  is 1.3 pt. (test: `TestBookGridRules_HasThreeWeights`.)
  **Not measured off ink** — ADR-0042/R6 forbids recovering by pixel-counting a
  number the generator stated exactly, and CARD-293's AC-4 demonstrated the
  replacement: **168 → 41 lines, 4.1× smaller**, strictly more exact, and it
  **discriminates** (it passed at 0.48 pt and failed at 0.3 pt). The runnable
  model is `~/Documents/nonogram-reviews/CARD-293/card293-ac4-stream-assertion.py`.
- **AC-2** (happy, grey cells): *Given* a drawn grid, *then* the cell lines are
  grey and the fifth lines and border are darker — asserted as an ink-value
  ordering, not as one literal colour. (test:
  `TestBookGridRules_CellLinesAreLighterThanTheFifths`.) The tone is `0.35`
  grey, which renders as grey 89; assert the ordering, not the byte.
- **AC-3** (happy, both axes): *Given* a non-square grid, *then* the every-fifth
  rule applies on rows and columns independently and counts from the border on
  each. (test: `TestBookGridRules_FifthLinesOnBothAxes`.)
- **AC-4** (edge, a grid whose side is not a multiple of five): *Given* a 22×13
  grid, *then* the last band is short and the border is still 1.3 pt — no
  half-weight line at the edge. (test: `TestBookGridRules_RaggedLastBand`.)
- **AC-5** (edge, the smallest cell): *Given* the smallest cell the book admits
  (NFR-008's floor, **4.75 mm**), *then* the three weights are still **distinct
  as declared widths**, and the hierarchy the design is after — light grey cell
  grid, clearly heavier fifth, clearly heavier border — still holds. (test:
  `TestBookGridRules_WeightsSurviveTheFloor`.)
  **Re-expressed from the raster version**, which said "each is at least one
  pixel and no two round to the same width". Pixel rounding is not how a content
  stream works, and the old phrasing would now be asserting a property of
  whichever renderer the test happened to use. Assert the declared widths and
  their ordering.
- **AC-6** (guard, resolution independence — now the sharpest control on the
  card): *Given* the same page rendered at **300 and 1200 DPI**, *then* each
  weight's physical width is unchanged, each one's *pixel* width scales with the
  resolution, and the **tone is identical at both**. (test:
  `TestBookGridRules_PointsNotPixels`.)
  This is the property that made the owner's figures available at all, and
  CARD-293 measured both arms of it: 2 px → 5 px for the cell line, grey 89 at
  both. A card that shipped these widths without this control would have no
  evidence that the thing which made them safe is actually true.
- **AC-7** (guard, the refused configuration stays refused): *Given* an attempt to
  draw a puzzle grid at these weights onto a **raster** surface, *then* it is
  refused or impossible, and a control demonstrates the refusal. (test:
  `TestBookGridRules_TheseWidthsNeverReachARasterGrid`.)
  **New on 2026-10-25, and the card's one genuinely new claim.** Per ADR-0039/R1
  it needs a control that CAN fail: the mutant is "let a raster page take the
  0.3 pt figure" and the control must red on it. Without this AC the card's whole
  medium argument is a comment.

### Which of these criteria read the stream, and which read a render — ADR-0042/R6

Three of this card's criteria measure a **render**, and that is correct rather
than a lapse. R6 gained a **second declared exemption** on 2026-10-25 for exactly
this card's shape: a claim about what the device does with a declared width or
tone is asserted on a render, because the content stream is precisely what it
does not test. Reading 0.3 pt back out of the operator that set it says nothing
about whether 0.3 pt is **visible** — and visibility is what this whole decision
rests on.

| criterion | reads | why |
|---|---|---|
| **AC-1** (the three weights) | **stream** | the widths are stated; recovering them from ink is the reconstruction R6 forbids |
| **AC-2** (grey ordering) | stream | the tones are stated |
| AC-3, AC-4 (axes, ragged band) | stream | positions and counts are stated |
| **AC-5** (distinct at the smallest cell) | **render** — exempt | "these two resolve differently" is a device fact |
| **AC-6** (300 vs 1200 DPI) | **render** — exempt | the pixel scaling and tone survival ARE the claim |
| **AC-7** (never reaches a raster grid) | both | reads the medium, then shows the refusal |

**The discriminator, because CARD-299's R6 guard is default-DENY over `tests/**`
and will see these tests:** what the assertion *concludes*. "These two render
differently" and "this tone survives" are device facts. "This line is 0.3 pt" is
a stated number and belongs to the stream. An exemption keyed on a test's name
or file rather than its conclusion is the defect CARD-299's AC-4 exists to catch,
and its mutant is built from AC-5.

**One figure nobody has measured, recorded so it is not mistaken for evidence:**
poppler measured the **cell line** (2 px at grey 89 at 300 DPI, 5 px at 1200).
The **0.8 pt and 1.3 pt** vector spans are measured by nobody. This card owes
those two measurements along with the tests — do not cite CARD-293 for them.

## Guardrails

- **G-1: the answer pages' grids follow the same weights** — the artifact wants
  the solutions to look like the puzzles. Note the ordering consequence: **this
  card now lands before CARD-297** (the answer tiles), so CARD-297 draws its
  tiles at these weights from the start rather than being retrofitted.
- **G-2: no new drawing primitive.** The weights go through the stroke path
  CARD-294 established and CARD-295 uses (ADR-0036/R2, ADR-0042/R3) — this card
  changes *numbers*, not the writer.
- **G-3: the cells' geometry does not change.** This card changes stroke widths,
  not positions.
- **G-4: out of scope** — the clue boxes and the 5 % shading (CARD-208), the cell
  size (CARD-225), and **the page furniture's own floor** (see the note below:
  deliberately not decided, and CARD-222 / CARD-225 / CARD-248 cite it).
- **G-5: do not re-record the book baselines here.** CARD-298 records them once,
  and this card is sequenced **before** it precisely so one recording captures
  both the medium change and these widths. A baseline refresh in this card means
  the phase pays for two.
- **G-6: ADR-0037/R2's lens must not survive this card** — Obligation 1 is part of
  the card, not a follow-up.

## System contract

_A projection — fix the source artifact, never this list. Re-derived at dispatch._

- **ADR-0037/R2** — the puzzle grid has exactly three rule weights, 0.3 pt grey cell lines, 0.8 pt every fifth, 1.3 pt border, cell lines lighter in ink than the fifths and the border; **physical widths that hold only where the grid is drawn as content-stream operators**, a raster grid staying held to 2 device pixels and therefore unable to use these figures. (check: review-lens — **this card upgrades it to its own test at landing**) _[re-projected 2026-10-25 after the owner's decision]_
- **ADR-0042/R1** — interior pages are operators; no image XObject (check: tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject, landed by CARD-298)
- **ADR-0042/R3** — the writer consumes positions and derives none (check: review-lens)
- **ADR-0042/R6** — an interior claim is asserted against the content stream, not a bitmap (check: review-lens → CARD-299)
- **ADR-0042/R7** — this ADR does not set the weights itself; R2 is where they live (check: review-lens)
- ADR-0036/R1 — `compute_layout` without a PageSpec produces today's A4 geometry; CLI and web output byte-for-byte unchanged by any book-only PageSpec field (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — book page geometry is computed only by COMP-007's layout functions with the book's PageSpec (check: review-lens)
- ADR-0037/R1 — a book puzzle page never prints the picture's title (check: review-lens)
- CON-018 / INV-006 — the printed cell never falls below 4.75 mm (check: TestBookCellSize_HoldsTheFloor)
- CON-020 — no interior text for the reader below 10 pt (check: TestInteriorType_EveryFaceHoldsTheFloor)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)

_53 further rules the lens returns are scoped `src/nonogram/**` (package-wide), so they match every card and narrow to nothing. Deliberately not listed — owner decision 2026-10-17, recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-033 (the threshold this card implements; amended 2026-10-25)
- **CON:** CON-018, CON-019, CON-020
- **ADR:** **ADR-0037/R2** (this card lands its check), ADR-0042/R1-R3-R6-R7, ADR-0036/R1-R2, ADR-0039/R1
- **Components:** COMP-007, COMP-009
- **Trace:** ADR-0037/R2's check becomes a live test ref here, so its trace row is re-stamped in this card.

## The two obligations this card carries at landing

1. **Upgrade ADR-0037/R2's `check`.** It is `{kind: review-lens}`, which cannot
   fail a build. It was left that way deliberately — naming
   `TestBookGridRules_HasThreeWeights` before it exists would be a dead
   check-ref, read as *mechanically checked* by `system_rules.py` and
   `forge:review` Step 8h. (That exact defect was found and repaired across
   ADR-0042's four planned checks and ADR-0032/R3 on 2026-10-25.) When your test
   exists, flip R2's check to it **in the same change**.
2. **`min_thin_rule_mm` in the code still says 0.25.**
   `src/nonogram/admin/book_page_spec.py:217` sets `min_thin_rule_mm=0.25` on
   `BOOK1_PROFILE`, and its docstring at `:144` cites "ADR-0037/R2's thinnest
   thin grid rule". **Both were wrong before this card and are wrong differently
   now.** Decide deliberately rather than substituting a number: under R2's new
   wording the interior has no millimetre floor at all (the medium carries the
   dropout guarantee), while any raster surface keeps the 2-device-pixel floor.
   So the honest change is probably to scope the field to the raster path or
   retire it for the book profile — **not** to replace `0.25` with `0.1058`,
   which would assert a floor *below* the figures it is meant to protect and read
   as licence rather than limit. Say which you chose and why.

## Worktree notes

- **[Historical, and read it as history]** The long record below of why the
  figures were scaled ×1.6, what the 0.25 mm minimum was, and why 0.3 pt was
  refused in 2026-10-17 is **audit trail, not instruction**. It explains how the
  card arrived at figures it no longer carries. The premise it all rests on — a
  raster interior at 300 DPI — stopped being true on 2026-10-25.

- **[One inherited note is now FALSE for the interior, and it is worth saying
  plainly]** CARD-222's episode left this card the note that *"after your three
  weights land, the grid's thinnest cell line is 2 px and the footer hairline is
  also 2 px — the same width. Furniture can no longer be lighter than grid ink by
  width, because width has hit the device floor."* At **0.3 pt** the cell line is
  **physically lighter** than a 0.4 pt hairline, so **width is available again**
  as a furniture/grid distinction on the interior. ADR-0037's History records this
  reversal. Two things that remain true: R2 has never bound furniture, and
  **the furniture's own floor is not decided by this card** — nobody asked about
  it, CARD-222 / CARD-225 / CARD-248 all cite the 2-device-pixel floor directly,
  and they keep today's figures until someone decides otherwise.

- **[Residue, recorded not waved past]** The three weights are **absolute
  points**, so they no longer scale with the cell — this supersedes COMP-007's
  proportional `cell / 30` rule under the book spec only. At NFR-008's 4.75 mm
  floor a 0.3 pt rule is 2.2 % of the cell; at the 7.5 mm cap 1.4 %. Large
  puzzles therefore get a *relatively* heavier grid than small ones, the opposite
  of the proportional rule's behaviour. Whether that reads well is a proof-page
  question.

- **[The caveat the owner accepted, carried here because this card is where it
  would bite]** The 2026-10-25 decision was made on the **vector renders**, not on
  paper — while ADR-0037's own Decision section asks that the weights "become
  final only after the owner has seen them on printed proof pages". Unmeasured by
  anyone: **dot gain** at 0.1058 mm on uncoated cream stock under offset or toner,
  and whether **35 % grey** reads as light guidance or as faded in print. The
  owner accepted that by deciding now. The revisit trigger is the first printed
  book or proof, and a change there is an ADR-0037 amendment rather than drift —
  so if the first printed book comes back with faint grid lines, **this card is
  not the bug; the amendment is the route.**

- **[Stale registry pointer, inherited and still open — not missing coverage]**
  AC-238 and AC-239's `test:` entries point at `tests/test_layout_page_spec.py`,
  whose fixtures still build the **retired** CON-018 sheet (`outside/top/bottom =
  9.525`, `BOOK1_USABLE_WIDTH_MM = 193.675`) and assert 4.97 / 4.61 — while the
  registry re-measured those criteria to **4.885 / 4.536**. It is *not* an
  unverified AC: both amended figures **are** asserted, at
  `tests/test_book_page_spec.py:249` and `:473`. What is stale is the registry's
  pointer plus two fixture docstrings. About **12 export-layer fixtures share that
  retired geometry**, so this is a propagation decision, not a one-line fix.
  Decide deliberately; do not edit twelve fixtures by reflex.

- **[Four lines restating the retired 0.25 mm thin minimum]**
  `tests/test_book_pdf_band.py:710`, `src/nonogram/export/layout.py:1861` and
  `:2166`, `src/nonogram/admin/book_page_spec.py:25`. These are claims about the
  rule this card changes, so they are this card's. Judge each: a line recording
  what the rule *used to* say is audit trail and stays (annotate it); a line
  stating the current minimum is wrong and must be restated. **Do not
  blanket-replace** — and note the 2026-10-25 twist, which makes this harder than
  it was: the interior now has no millimetre floor, so for several of these lines
  the correct edit is to say which *medium* the floor applies to, not to change
  the number.

---

## Historical record — how the ×1.6 scaling arose and why it is gone

_Preserved from the 2026-10-17 version of this card. Everything here was true of a
raster interior at 300 DPI._

- **[Why the artifact's figures were refused in 2026-10-17]** ADR-0037/R2 then
  required "every thin grid rule is at least 0.25 mm" and "in pure black". 0.3 pt
  is 0.1058 mm — a **one-pixel** line at 300 DPI, 2.4× under that floor, and
  *thinner than the 0.17 mm ADR-0037 itself rejected* as "exactly where faint
  lines hurt most" on the evidence of 7 of 17 reviews. Shipping the artifact
  literally onto a raster page would have re-opened the one complaint ADR-0037
  exists to close, inside a card scoped as a stroke-width tweak. **Settled then by
  the owner**: keep the ratios exactly, scale by 1.6 so the thinnest line is 2
  device pixels → 0.48 / 1.28 / 2.08 pt, rendering 2 / 5 / 9 px.
- **[Why rounding mattered then]** Two different point values can round to the
  same pixel width — 0.709 pt and 0.8 pt both round to 3 px at 300 DPI, which is
  why that compromise was rejected. **This reasoning does not transfer**: a
  content stream states a width and the renderer resolves it, so "which pixel
  width does it round to" is a question about the renderer, not the document.
- **[What changed on 2026-10-25]** ADR-0042 made the interior a content stream;
  ADR-0042/R7 made R2's device floor inapplicable to it; the owner read the proof
  and chose their own figures. The ×1.6 lost its premise, not an argument.
