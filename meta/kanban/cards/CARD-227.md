# CARD-227: The printed grid's rules get three weights — cell, every fifth, outer border

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/227-grid-rule-weights
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The rules behind it": Grid lines ("0.3 pt cells in grey, 0.8 pt every fifth line, 1.3 pt outer border")
**Idea:** —
**Wave:** —
**Depends on:** CARD-222 (the frame these rules are measured inside)
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_puzzle_frame.py, tests/test_book_pdf.py, tests/fixtures/book_baseline_card227.json, src/nonogram/admin/book_page_spec.py, src/nonogram/admin/book_proof.py, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The printed grid gets the same three-weight hierarchy the player's board has, stated in points
so it is resolution-independent:

- **0.48 pt** for ordinary cell lines, in grey (not black).
- **1.28 pt** for every fifth line, both axes.
- **2.08 pt** for the outer border.

**These are NOT the figures in the owner's artifact, and the difference is the point.** The
artifact says 0.3 / 0.8 / 1.3 pt. Those **ratios are kept exactly** (1 : 2.667 : 4.333); the
figures are scaled by 1.6 so the thinnest line is **2 device pixels** at 300 DPI instead of
one. Owner decision, 2026-10-17, at the architect station. Why, measured rather than argued:
0.3 pt is 0.1058 mm = 1.25 px, a **one-pixel grey line** that can dither or drop out on press,
and it is *thinner than the 0.17 mm ADR-0037 explicitly rejected* as "exactly where faint lines
hurt most" on the evidence of 7 of 17 reviews of the 450-puzzle book complaining about faint
grid lines. 0.48 pt = 0.1693 mm = exactly 2 px, the same 0.17 mm the package already prints at
its small cells today. Rendered 2 / 5 / 9 px at 300 DPI, all distinct.
**Do not "restore" the artifact's figures** if you notice the mismatch: it is deliberate, it is
recorded in ADR-0037's History and in FR-033's comment, and the `Source` field above is left
quoting the owner's original words on purpose, as provenance.

**What to check before writing anything.** FR-033 already says "bolder 5th lines, dark lines
(threshold unstated — open question)" — the threshold was left open in the architecture and
this card is the answer to it. So this is not a new rule but the **closing of a stated open
question**, which means the figures belong in FR-033's acceptance criteria and an amendment is
**still owed at the architect station**. The registry delta of 2026-10-17 (commit `91609aa`)
did **not** touch FR-033 — it carried CON-018, NFR-008, FR-030, FR-031, FR-032, FR-043 and
INV-013 only, and this card's amendment was explicitly out of its scope. Do not read that
delta as having settled the rule weights. Read FR-033 before implementing and say in the notes
whether the shipped behaviour already has one of these weights.

**One figure the artifact gives that belongs to another card:** "Clue areas shaded 5% grey,
with each number in its own box (CARD-208)" — the shading and the boxes are CARD-208's, which
has been amended to carry them. This card owns the three line weights only.

## Acceptance criteria

- **AC-1** (happy, three weights): *Given* a drawn grid, *when* its rules are measured off the
  ink, *then* ordinary cell lines are 0.48 pt, every fifth line is 1.28 pt and the outer
  border is 2.08 pt, at the page's own resolution. (test: `TestBookGridRules_HasThreeWeights`)
- **AC-2** (happy, grey cells): *Given* a drawn grid, *then* the cell lines are grey and the
  fifth lines and border are darker — asserted as an ink-value ordering, not as one literal
  colour. (test: `TestBookGridRules_CellLinesAreLighterThanTheFifths`)
- **AC-3** (happy, both axes): *Given* a non-square grid, *then* the every-fifth rule applies
  on rows and columns independently and counts from the border on each.
  (test: `TestBookGridRules_FifthLinesOnBothAxes`)
- **AC-4** (edge, a grid whose side is not a multiple of five): *Given* a 22x13 grid, *then*
  the last band is short and the border is still 2.08 pt — no half-weight line at the edge.
  (test: `TestBookGridRules_RaggedLastBand`)
- **AC-5** (edge, the smallest cell): *Given* the smallest cell the book admits (NFR-008's
  floor, **4.75 mm** since the 2026-10-17 amendment), *then* the three weights are still
  distinguishable — each is at least one
  pixel and no two round to the same width. (test: `TestBookGridRules_WeightsSurviveTheFloor`)
- **AC-6** (guard, resolution independence): *Given* two resolutions, *then* each weight
  scales with the page's dpi and the ordering holds at both.
  (test: `TestBookGridRules_PointsNotPixels`)

## Guardrails

- G-1: The answer pages' grids follow the same weights — the artifact wants the solutions to
  look like the puzzles (test: the answer-page frame tests).
- G-2: No new text-layout or drawing primitive: the weights go through the existing stroke
  path (ADR-0036/R2).
- G-3: The cells' *geometry* does not change — this card changes stroke widths, not positions
  (test: a geometry test asserting cell boxes are unchanged against the previous baseline).
- G-4: Out of scope — the clue boxes and the 5% shading (CARD-208), the cell size (CARD-225).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-227 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **FR-033 — STILL OWED, and explicitly out of scope of the 2026-10-17 delta.** That pass
  carried CON-018, NFR-008, FR-030, FR-031, FR-032, FR-043 and INV-013 — **not** FR-033. Its
  "dark lines (threshold unstated — open question)" is therefore still open, this card is still
  the answer to it. **LANDED 2026-10-17** at the architect station: FR-033's `open_question`
  is closed, its `statement` now carries the three weights, and **AC-372..AC-375** were written
  for them (three weights measured off ink, the grey ordering, survival at NFR-008's floor,
  resolution independence) — they name this card's four corresponding tests. The figures
  settled are **0.48 / 1.28 / 2.08 pt**, not the artifact's 0.3 / 0.8 / 1.3.
  AC-195 was checked and **survives unchanged**: indices 0 and 30 are now the border and
  5/10/15/20/25 the fifths, and both are still wider than the cell lines between them.
  **Still owed, and not this card's to invent**: AC-195's `given` says "printed at 4.97 mm",
  which predates CON-018's amended margins and is stale; the honest figure cannot be measured
  until CARD-222 merges. Annotated in `requirements.yml`, not guessed. Do not read the 2026-10-17 amendments as having settled this one: nothing about
  rule weights was decided that day. Read FR-033 before implementing and say in the notes
  whether the shipped behaviour already has one of these weights.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec the puzzle grid has exactly three rule weights — 0.48 pt ordinary cell lines in grey, 1.28 pt every fifth line on both axes, 2.08 pt outer border — each of them at least 2 device pixels at the render resolution, with the cell lines lighter in ink than the fifth lines and the border; the default PageSpec's strokes are unchanged. (check: review-lens — **this card upgrades it to its own test at landing**, see the obligation in Worktree notes) _[re-projected 2026-10-17 after the amendment this card's own defect note triggered]_
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-033 (the open threshold this card closes).
- **CON:** CON-018, CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Smallest card of the set, and the one most likely to be mis-measured] Rounding decides
  whether two weights are distinguishable at all, which is why AC-5 and AC-6 exist: the figures
  are only meaningful if they survive the smallest cell and both resolutions. **This is exactly
  what killed the artifact's original figures** — 0.3 pt at 300 dpi is 1.25 px, i.e. one pixel.
  The decided weights round to **2 / 5 / 9 px**, all distinct. Measure in device pixels, not in
  points, when you assert distinguishability: two different point values can round to the same
  pixel width, and the obvious compromise was rejected for precisely that reason (0.709 pt and
  0.8 pt both round to 3 px at 300 DPI).
- [Pre-dispatch defect, found at the 2026-10-17 widening pass] **RESOLVED 2026-10-17 at the architect station, before dispatch.** The defect as recorded: this card's figures contradicted ADR-0037/R2 in its own `## System contract`, 0.8 pt being 2.67x the thin rule and 1.3 pt being 4.33x against R2's "every heavy rule is twice the thin rule". That was correct as far as it went. **Two further contradictions were found when it was settled, and one of them mattered more than the ratio:**
  1. **The minimum.** R2 also required "every thin grid rule is at least 0.25 mm". 0.3 pt is 0.1058 mm — a **one-pixel** line at 300 DPI, 2.4x under R2's floor, and *thinner than the 0.17 mm ADR-0037 itself rejected* as "exactly where faint lines hurt most" on the evidence of 7 of 17 reviews of the 450-puzzle book. Shipping the artifact literally would have re-opened the one complaint ADR-0037 exists to close, quietly, inside a card scoped as a stroke-width tweak.
  2. **The colour.** R2 required "in pure black"; this card wants grey cell lines (AC-2). The original note did not mention this one either.
  **Settled by the owner**: keep the owner's ratios exactly, scale by 1.6 so the thinnest line is 2 device pixels. Figures are now **0.48 / 1.28 / 2.08 pt**, rendering 2 / 5 / 9 px. ADR-0037/R2 is amended (three weights, grey cells, minimum 0.25 -> 0.169 mm) with its reasoning and residue in that ADR's History; FR-033's `open_question` is closed and AC-372..AC-375 written. **No contradiction remains between this card and its own system contract**, so it no longer gates on cycle 1.

- [Two obligations this card carries at landing — do not skip them] ⚠
  1. **Upgrade ADR-0037/R2's `check`.** It is `{kind: review-lens}`, which cannot fail a build. It was left that way deliberately: naming `TestBookGridRules_HasThreeWeights` before you write it would be a dead check-ref, the exact defect a premature `meta/` carry produced earlier this wave. When your test exists, change R2's check to it. ADR-0039/R1 — a coverage claim needs a control that can fail — and the wave-43 retrospective's headline was precisely that this rule "existed and did not bite".
  2. **`min_thin_rule_mm` in the code still says 0.25.** `src/nonogram/admin/book_page_spec.py:217` sets `min_thin_rule_mm=0.25` on `BOOK1_PROFILE`, and its docstring at :144 cites "ADR-0037/R2's thinnest thin grid rule". Both are now wrong. Prefer expressing the minimum in device pixels over a millimetre literal, since the decision was made in pixels and the mm figure is a consequence of 300 DPI. Note `src/nonogram/admin/book_page_spec.py` was added to R2's `scope.code` for this reason.

- [Third obligation at landing, found by CARD-222's review cycle 2026-10-17] ⚠ **Four lines
  still restate the retired 0.25 mm thin minimum**, and they are yours because they are claims
  about the rule you are changing: `tests/test_book_pdf_band.py:710`,
  `src/nonogram/export/layout.py:1861` and `:2166`, and
  `src/nonogram/admin/book_page_spec.py:25`. CARD-222's review scoped them out as pre-existing
  and its fix deliberately did not widen into them. Judge each: a line recording what the rule
  *used to* say is audit trail and stays (annotate it), a line stating the current minimum is
  wrong and must be restated. **Do not blanket-replace 0.25 with 0.169** — the two are not
  interchangeable: 0.25 mm was a millimetre literal and the amended floor is *2 device pixels*,
  which is 0.1693 mm only at 300 DPI. Prefer the pixel form, since that is how the decision was
  made.

- [What CARD-222 already settled for you — do not re-derive it] ADR-0037/R2 **binds the puzzle
  grid, not page furniture.** CARD-222 wrote its footer hairline a formal exemption from R2 and
  a control for it; both were unnecessary, and the episode is recorded in ADR-0037's History.
  The consequence that reaches your card: after your three weights land, the grid's thinnest
  cell line is 2 px and **the footer hairline is also 2 px** — the same width. Furniture can no
  longer be lighter than grid ink by width, because width has hit the device floor and 1 px is
  the dropout risk your own figures were scaled up to avoid. **Expect no test to assert
  `furniture < grid ink`**; CARD-222's retargeted control deliberately compares furniture with
  furniture only, and was verified green under a simulation of your 2 px thin rule. If you find
  a test that compares the two, it is a defect you inherited, not one you caused.

- [Fourth item, from CARD-222's review cycle 2 — a stale registry *pointer*, not missing
  coverage] AC-238 and AC-239's `test:` entries point at `tests/test_layout_page_spec.py`, whose
  fixtures still build the **retired** CON-018 sheet (`outside/top/bottom = 9.525`,
  `BOOK1_USABLE_WIDTH_MM = 193.675`) and assert 4.97 / 4.61 — while the registry re-measured
  those criteria to **4.885 / 4.536**. **Read this correctly before acting:** it is *not* an
  unverified AC. Both amended figures **are** asserted, at `tests/test_book_page_spec.py:249`
  and `:473`. What is stale is the registry's pointer plus two fixture docstrings claiming
  "CON-018's Book 1 profile" and "FR-030's usable width". About **12 export-layer fixtures share
  that retired geometry**, so this is a propagation decision rather than a one-line fix — the
  same class as the four 0.25 mm lines above, which is why both are parked here. Decide
  deliberately: repoint the registry at the tests that actually assert the amended figures, or
  migrate the fixtures. Do **not** edit twelve fixtures by reflex; say which you chose and why.

- [Residue, recorded not waved past] The three weights are **absolute points**, so they no longer scale with the cell — this supersedes COMP-007's proportional `cell / 30` rule under the book spec only. At NFR-008's 4.75 mm floor a 0.48 pt rule is 3.6 % of the cell; at the 7.5 mm cap 2.3 %. Large puzzles therefore get a *relatively* heavier grid than small ones, the opposite of the proportional rule's behaviour. ADR-0037's Consequences note about "about 5%" describes the superseded two-weight scheme. Whether this reads well is a proof-page question, and a proof page is already required before a book is finalised.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**This card's DECISION changes, not just its tests.**

**Was:** three rule weights at 0.48 pt / 1.28 pt / 2.08 pt — the owner's own
1 : 2.667 : 4.333 ratios, scaled x1.6 "so the thinnest line is 2 device pixels at
300 DPI rather than one". ADR-0037/R2 refused the owner's actual design
(0.3 / 0.8 / 1.3 pt) because 0.3 pt = 0.1058 mm = a ONE-PIXEL line at 300 DPI.

**Should be:** re-decided. ADR-0042/R7 makes ADR-0037/R2's device floor
**inapplicable to the interior** — a content-stream line has no device pixel to
clear — so the x1.6 scaling has no reason behind it any more, and the owner's own
numbers are available. CARD-293 measured them: the 0.3 pt line renders at
**2 px / grey 89 at 300 DPI and 5 px / grey 89 at 1200** (tone exact, width
scaling), and on the printed proof it is **the best of the four panels**.

**Delta:**
- The thresholds are an OPEN QUESTION again, not a closed one. FR-033's
  `resolved_question` was rewritten 2026-10-25 to stop recording the device-floor
  rationale as live, and to record the figures as DECIDED but UNLANDED.
- **Blocked on the owner, not on code.** ADR-0042/R7 is explicit that the weights
  wait on a printed proof: dot gain on real stock, and whether 35% grey reads as
  guidance, cannot be judged from a screen. The proof is at
  `~/Documents/nonogram-reviews/CARD-293/card293-AC2-side-by-side.pdf` and must be
  printed at 100%.
- Once the owner has seen it, ADR-0037 is revised (that is an architect-station
  step) and only then is this card rewritten against the revised rule.
- The spike's AC-4 replacement test **passes at 0.48 pt and fails at 0.3 pt**, so
  whichever figures win, the assertion that checks them already discriminates.
