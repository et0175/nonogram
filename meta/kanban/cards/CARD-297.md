# CARD-297: The table of contents and the answer pages as operators — the solution tiles, their headers, and the QR slot

**Status:** in progress
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/297-toc-and-answer-pages-as-operators
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-297
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 4 (the non-puzzle pages, less the guide — CARD-296 — and less the dividers, which the owner left raster). Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 64
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-294, CARD-295, CARD-227
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_solved_answer_key.py, tests/test_book_toc.py, tests/test_book_answer_key.py, tests/test_book_qr_slot.py, tests/test_layout_answer_tiles.py
**Review score:** 7.0 cycle 1/3 (not certified; 6 important, fix round 1 running)
**Started:** 2026-10-29
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The two remaining vector page kinds ADR-0042/R1 names, now that the puzzle page
(CARD-295) and the guide (CARD-296) are done:

1. **The table of contents** — its rows, the puzzle numbers, names and folios,
   and its leader dots.
2. **The answer pages** — the solution tiles with their grids, each tile's band
   (number, picture name, difficulty), and the level headings.
   <!-- AMENDED 2026-10-29, review cycle 1 F-297-06: "and the SOLUTIONS divider's
   text" struck, because it contradicted this card's own G-2, which says to leave
   that path drawing as it does (CON-020's :355 sibling requires the face to keep
   being recorded). The implementation round followed G-2 and was right to. Also
   "header" -> "band", and "difficulty dots" -> "difficulty": measured, a tile's
   band prints the difficulty as a WORD -- band_identity composes "Puzzle 12 ·
   Hard" -- and no page in src/ prints dots at all. --> **The answer key is the only place the book prints a picture's
   title** (ADR-0037/R1, FR-033/AC-194) — that stays exactly true.
3. **The QR slot**, where the page reserves one. The QR *glyph* is a grid of
   black squares, so it is rectangles, not an image — but see G-4: making the QR
   codes real and scannable is CARD-210's, and it is blocked.

The answer tiles' grids should reuse CARD-295's grid routine rather than growing
a third copy — same reasoning as CARD-296's AC-4.

**Depends on CARD-295** and not only on CARD-294, because of that reuse: the tile
is a small puzzle grid, and the dependency is what stops this card reimplementing
one.

## Acceptance criteria

- **AC-1** (neither page kind carries a bitmap): *Given* an interior whose TOC
  and answer pages are written by this card, *then* no page of either kind
  references an image XObject. (test:
  `TestAnswerAndTocPages_CarryNoImageXObject`.)
- **AC-2** (the answer key still prints the title, and it is still the only place
  that does): *Given* a book, *then* a solution's **caption** carries the
  picture's name **wherever the trim leaves room for one**, and no puzzle page
  anywhere in the interior does. (test:
  `TestAnswerKey_IsTheOnlyPlaceTheTitleIsPrinted` — the second half is the half
  that can fail, and it must be asserted over the whole interior, not over the
  answer section. **The agreement must be asserted over the CLIPPED strings too,
  not only the unclipped set** — that is the one axis on which the two media can
  diverge, and cycle 1's F-297-03 measured the hole.)
  <!-- AMENDED 2026-10-29, cycle 1 F-297-06/F-297-03: "each solution tile's
  header" -> "a solution's caption wherever the trim leaves room", because the
  title is carried by the CAPTION, not the tile band, and because "each" is
  unsatisfiable against this card's own AC-6: CARD-197's AC-6 omits the caption
  rather than overlap the drawing, and a square trim leaves a full-page answer
  no slack at all (measured 0 px on the 10.0, 12.7 and 15.24 cm square trims).
  Measured on the 10x10 trim: of four titles, 1 prints, 1 is clipped, 2 are
  omitted -- so the original literal was false of the shipping book. -->
- **AC-3** (the tiles are the grid routine, not a third copy): *Given* the
  answer tiles, *then* they are drawn through CARD-295's grid routine, derived
  from the module's AST and default-DENY per ADR-0039/R2. (test:
  `TestAnswerTiles_ReuseTheGridRoutine`.)
- **AC-4** (the TOC's rows say what the page plan says): *Given* a book, *then*
  every TOC row's number, name and folio equals the page plan's, read from the
  **written PDF's content stream** and compared against the plan — not against a
  rendered bitmap. (test: `TestToc_EveryRowMatchesThePagePlan`.)
  **CARD-219 already moved this file's assertions off pixels and onto the page
  plan** — seven positional tests converted, `solved_puzzle_page` renders
  **1225 → 175 (−85.7 %)**, the file's AC-1 group down to **0.78 s**. Build on
  that; do not reintroduce a render to check a number the plan states.
- **AC-5** (the round primitive CARD-294 priced is exercised where a tile band
  would use it): *Given* the narrowest band a packed solution tile reserves,
  *then* the ladder COMP-007 measures for it renders as round shapes at the
  stated diameter, read back by poppler. (test:
  `TestAnswerTileHeader_DifficultyDotsAreRound` — the primitive CARD-294 priced.
  **It has no second user yet**, and nothing is wired onto a page: a tile band
  prints the difficulty as a word, so this criterion exercises the primitive
  rather than a shipping page, and `test_no_answer_page_draws_a_round_mark_today`
  is the test-shaped limit that makes CARD-233 red here instead of discovering
  it.)
  <!-- AMENDED 2026-10-29, cycle 1 F-297-06: the clause "the same primitive
  CARD-294 priced and CARD-296 first used; three users, one implementation" was
  FALSE in two parts, both measured. (a) `book_guide_vector.draw_legend` draws no
  round shape and says so in its own docstring -- CARD-296 measured this same
  claim false and DECLINED it, so there was no first user and there are not three
  users. (b) A tile band prints the difficulty as a word: `difficulty_dots` has
  one call site, from `_draw_difficulty_dots`, which has ZERO callers in src/ --
  dead code, pre-existing, recorded across CARD-228's three cycles, CARD-241's
  G-4 and CARD-296's pre-gate, and NOT this card's to fix. "header" -> "band"
  throughout. -->
- **AC-6** (the answer caption's face still holds the floor): *Given* the vector
  answer pages, *then* the answer caption holds CON-020's 10 pt floor, asserted
  against the stream's `Tf` sizes. (test:
  `TestAnswerPages_CaptionHoldsTheFloorInTheStream`. Note the caption is **omitted
  on the 10×10 cm minimum trim** — CARD-197's AC-6 omits it rather than overlap
  the drawing — so the assertion must be conditional on the profile exactly as
  `tests/test_book_interior_type_floor.py:369` already is, or it will fail on
  `min-trim` for the wrong reason.)

## Engineering constraints

- **EC(ADR-0042/R3):** neither writer derives geometry, across every book profile
  and every tile count per page. test:
  `TestPropertyTest_AnswerAndToc_WriterDerivesNoGeometry`.
  <!-- CORRECTED 2026-10-29, cycle 1 F-297-05: the ref named the unprefixed
  spelling, which is not a class that exists and which pytest could not collect
  if it did -- `pyproject.toml` sets no `python_classes`, so the default `Test`
  prefix applies and a bare `PropertyTest_...` class holds tests pytest silently
  never runs. The round's rename was correct and was declared rather than hidden.
  Worth keeping: `git grep -lw` for the OLD spelling exits 0, and the only thing
  making it do so is a docstring sentence the round itself wrote -- the same
  prose-revives-a-dead-ref mechanism measured on CARD-301 the same day. -->
- **EC(ADR-0037/R1):** across a seeded corpus of books, the picture's title
  appears on answer pages and nowhere else in the interior. test: AC-2's test
  extended over the corpus, with a minimum case count asserted inside it.

## Guardrails

- **G-1: do not redesign either page.** CARD-232 makes solutions fixed tiles four
  to a page in a 2×2 grid; CARD-233 gives a tile one header; CARD-209 packs
  wide-but-short solutions three to a page. **All three are queued and gated.**
  This card ports today's design to the new medium so those cards are written
  against a vector page from the start.
- **G-2: do not touch the SOLUTIONS divider's page as a raster surface.** The
  section dividers stay raster by the owner's 2026-10-25 decision and CARD-231
  redesigns them. The divider's *text* is a face CON-020's `:355` sibling
  requires to keep being recorded — leave that path drawing as it does.
- **G-3: do not touch the cover.** Raster by ADR-0042/R2.
- **G-4: do not make the QR codes real.** CARD-210 — *"Each puzzle's QR code
  becomes a real, scannable link"* — is **blocked**, waiting on the URL base
  CARD-285 produces. This card draws the slot as it is drawn today, in operators.
  A card that helpfully makes the QR scannable has taken a blocked card's scope.
- **G-5: this file holds the suite's largest pixel concentration — convert only
  this card's page kinds.** `tests/test_book_solved_answer_key.py` alone has **47
  pixel-reading sites**, the most of any file in the tree
  (`meta/profiling/adr-0042-migration-census.md`). Convert the answer/TOC ones;
  leave the rest to CARD-299, and do not reach into
  `tests/test_book_export_interior_cover.py` — it is CARD-276's (in flight),
  CARD-287's and CARD-292's at once.
- **G-6: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-7: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated.
- **G-8: probes stay OUT of `tests/`** — `RENDER_HEAVY_SNAPSHOT` greps
  `solved_puzzle_page` and `puzzle_pages` among its eight idioms, and
  `tests/test_book_toc.py` is already in its 33-entry snapshot.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject (check: review-lens → CARD-298)
- ADR-0042/R2 — a raster page needs a declaration with a live reason (check: review-lens → CARD-298)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0036/R2 — the answer tiles are laid out by COMP-007's layout with the book's PageSpec (check: review-lens)
- ADR-0037/R1 — the answer key is the only place the title is printed (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt at the page's own resolution (check: TestInteriorType_EveryFaceHoldsTheFloor)
- INV-013 — the interior holds no cover page and parity counts from interior page 1 (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived and default-DENY (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-033 (AC-194 — the title's one home), FR-042 (the answer key), FR-040, FR-041, FR-043
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R2, R3), ADR-0036/R2, ADR-0037/R1, ADR-0039/R1-R2
- **Components:** COMP-009; COMP-007's layout consumed
- **Trace:** meta/architecture/trace.yml

## [Implementation round 2026-10-29 — it converts ZERO pixel sites, and says so]

Branch `card/297-toc-and-answer-pages-as-operators`, 2 commits (`1a42e8d7`,
`85414ac7`), worktree clean. **Verified by the orchestrator rather than
relayed:**

- diffstat exactly **5 files, 3210 insertions, 0 deletions** — no existing line
  modified anywhere. Two new `src/` modules (`book_toc_vector.py` 334,
  `book_answer_vector.py` 657), `book_vector_draw.py` +214 additive,
  `tests/test_book_solved_answer_key.py` +1697, `tests/test_book_toc.py` +308
- **`src/nonogram/admin/book_pdf_generator.py` is byte-identical to main** (blob
  `7a515eea` on both sides) — the declared `conflict.hotspot` was not touched
- **G-6 holds exactly**: main **9570** → HEAD **9641**, `comm` giving **71
  added / 0 removed**, split 60 + 11 across the two test files.
  `9570 + 71 − 0 = 9641`

**The headline, and it is the round's own words rather than a gloss: this card
converts zero pixel-reading sites and its net is a cost, not a saving** — +70
page bitmaps and +298 Mpx in the answer-key file, against 0 → 0 bitmaps on the
TOC file's 11 new cells. Its argument is G-5's own reasoning: `_write_pdf`
chooses no medium per page until **CARD-298**, so the raster answer pages are
still what ships, and converting their assertions would drop the control on
what ships for a control on what does not. It attributes the +70 — **68 (97 %)**
to the two `_Recorded` raster-interior walks that AC-2's "over the whole
interior" half requires, **2** to AC-1's positive control, everything else zero.
Whether that is right sequencing or a different card delivered is with review
cycle 1 and ultimately the owner; it is **not** prejudged here.

### Three measured disagreements with this card, two of them with their supporting enumeration off

Checked independently with an `ast` call-census over `src/`:

1. **The QR conclusion holds; its enumeration does not.** None of
   `create_toc_page`, `_draw_solved_slot`, `solved_puzzle_page` or
   `_packed_answer_page` references `qr_slot`, `_draw_qr_placeholder` or
   `_draw_qr_caption` — so **item 3 of this card has nothing to port on these
   page kinds** and G-4 is honoured trivially. But the round said those
   functions are "reached only from `_blank_page` and `_draw_two_up_qr_groups`",
   and `qr_slot` in fact has **6** call sites, including `qr_caption()` and
   `qr_group_insets()` in `export/layout.py` and `render_image()` in
   `export/png.py`.
2. **AC-5's premise is false, and the truth is sharper than the round argued.**
   It reported the chain `difficulty_dots ← _draw_difficulty_dots ←
   _draw_difficulty_legend ← create_guide_page`. Measured: `difficulty_dots` has
   **1** call site ✓, `round_mark` has **0** in `src/` ✓ — but
   **`_draw_difficulty_dots` has ZERO callers**, its only mentions in `src/`
   being its own `def` at `book_pdf_generator.py:1739` and a docstring
   cross-reference. It looks like **dead code**, which strengthens the
   conclusion (no answer tile prints dots today — a tile header prints the
   difficulty as a word) while breaking the stated chain at one link.
3. **This card's body contradicts its own G-2.** Item 2 includes "the SOLUTIONS
   divider's text"; G-2 says to leave that path drawing as it does because
   CON-020's `:355` sibling requires it to keep being recorded. The round
   followed **G-2**. That is the AC-vs-body cross-check the drafting rules
   require and this card did not get.

### The EC's `test:` name does not match the class that exists

The EC(ADR-0042/R3) names `PropertyTest_AnswerAndToc_WriterDerivesNoGeometry`;
the shipped class is `TestPropertyTest_AnswerAndToc_WriterDerivesNoGeometry`.
**The rename is correct** — `pyproject.toml` sets no `python_classes`, so a bare
`PropertyTest_…` class holds tests pytest silently never collects — and the
round stated it rather than hiding it. What is worth recording: `git grep -lw`
for the card's name exits **0**, and the only thing making it do so is a
docstring line the round itself wrote at `test_book_solved_answer_key.py:3281`.
The ref is not in `meta/architecture/`, so the validator never reads it today —
but it is the same prose-revives-a-dead-ref mechanism measured on CARD-301 this
same day, in a file written an hour later.

### Also reported, for review to settle

AC-2's first half is substituted by **cross-medium agreement** because on a
square trim a full-page answer has **0 px** of slack and the title prints
nowhere (EC corpus: 18 print / 6 omit, both floors asserted). Both writers were
restructured **downstream of `book_pdf_generator`** after the generator-method
shape was measured to red two figures in `tests/test_book_export_interior_cover.py`
— a file G-5 forbids this card to touch. M4 survived its first round and the
hole was real (a tone reading could not see *which* boundaries were drawn);
M8/M8b are declared survivors with an argued unreachability proof.

## [Review cycle 1 — 7.0, not certified. No product-correctness defect; every finding is in the claims layer]

Report: `meta/review/20261029T030250Z-CARD-297-cycle1.yml` (8 findings — 6
important, 2 minor — `yaml.safe_load` clean). Cycle 1 ran its mutation work in
**three private detached worktrees under its own scratchpad**, never in the card
worktree, and removed all three clean.

**What reproduced exactly.** G-6 re-derived in two worktrees: 9570 → 9641, **71
added / 0 removed**, 60 + 11. The bitmap figures through a *broader* instrument
(hooking `Image.new`, `open` and `frombytes`, counting `ImageDraw.__init__`):
**+70 page bitmaps, +183 ImageDraw, +298.04 Mpx** — all three to the digit, with
the attribution exact (68 from the module-scoped `_Recorded` walk paid **once**
across four classes, 2 from AC-1's positive control) and the real cost **+1.39 s**
on that file. **All 13 of the round's mutants re-fired: 13/13 reproduce, 29 named
cells red across the 11 kills, zero misattributions**, blob-at-HEAD and
line-count-preservation verified for every pair. `book_pdf_generator.py`
byte-identical to main. Impact gate **1447 passed / 0 failed / 0 skipped** over
17 files.

**The five verdicts, one way each.** Zero-conversion / +70 bitmaps → **correct
sequencing**, and the deduction lands on *this card*: G-5 asks for a conversion
CARD-298 must precede, and all 20 pixel sites in the file are pre-existing
answer-page sites. AC-5 → mechanism **accepted**, bookkeeping **rejected** (see
the amendment above). AC-2's cross-medium substitution → **necessary** (the
literal is unsatisfiable by this card's own AC-6) **but blind on clipping**.
Downstream restructure → **right, and forced**: a planted four-call generator
method moves the door-axis walk's `inside` 17 → 21 and the cell reds, and it
also breaks the walk's last step 0 → 3, which the round missed. Scope growth →
**accepted**, and strictly more disciplined than the CARD-295 precedent it cites
(295: 4 declared / 11 shipped, +117 to the generator, 50 lines into the
now-forbidden file; 297: 5 files, 0 deletions, not one existing line modified).

### The two findings that matter

- **F-297-01 + F-297-04 — AC-3's guard reads as derived and is hand-listed, at
  two layers.** `_STROKERS = ("line", "rectangle")` is a literal tuple, and
  `_strokers_of` shares it so the stroker-set pin is blind too; the operator
  allow-list below it admits `c`, `h` and `B`. Cycle 1 built the real artefact
  and it passes with **zero violations** — `('0 G','1 w','24 228 m','24 12 l',
  '48 228 m','48 12 l','72 228 m','72 12 l','S')`, three ruled lines, a complete
  grid walk, through doors the guard does not watch. **Verified by the
  orchestrator, with a larger denominator than cycle 1 stated**: `ContentStream`
  has **16** public methods, of which **eight** can put a stroked line on a page
  (`line`, `rectangle`, `curve`, `begin_path`, `line_to`, `close_path`, `paint`,
  `round_mark`) — the guard watches **two**. This is verbatim the board's
  standing rule: *"default-deny is still satisfiable with a positive catalogue of
  write shapes underneath; the durable form is that the exemption set is derived,
  every entry machine-checked, and the controls are the shapes the guard was NOT
  written from."* The **exemption** half is sound and cycle 1 credits it.
- **F-297-02 — M8/M8b: right answer, wrong reason.** The declared bound's stated
  mechanism is **self-refuting**: summing `/Widths` and dividing once computes
  `(W·n)/1000`, which is precisely *not* `n·(W/1000)` in floating point. Cycle 1
  measured the identity failing at 56 of the first 200 counts, first at n=9, and
  at twelve counts inside the very 120–153 production range the docstring cites.
  (The orchestrator re-derived the pure arithmetic through a different door — the
  illustrative `318/1000` from the docstring's own prose rather than the real
  metric — and got 16 failures in 200, first at n=15, 3 inside 120–153: a
  different domain, so it confirms the *mechanism* without reproducing the
  *counts*.) **The loops are still legitimately dead**, by the argument cycle 1
  reached after correcting its own first reading: a 500k-run sweep over the
  reachable domain (0–2550 px, the widest stocked trim) fires them **0 times**.
  So the conclusion holds and the declared reason has to be replaced.

### Also owed to the fix round

Six of cycle 1's own thirteen mutants survive, clustered in the undeclared
`book_vector_draw.py` +214: of `draw_folio`'s four decisions, exactly **one**
has a control, and `x = left` makes **every right-hand folio print at the
gutter** while 596 cells pass. Eight figures in the round's account do not
reproduce, four of them new: "the title prints nowhere on the 10×10 trim" (it is
1 prints / 1 clipped / 2 omitted, though the committed cell is scoped honestly);
the "72.9 vs 73 px thresholds agree for every integer slack" claim has **no
committed assertion at all**; "13 mutants, all deletion" (M10 substitutes, M11
adds); and "225/163 asserts instrumented" are **pre-fix** figures (HEAD:
233/169).

### Credited in full

CARD-219's fence, all four parts, including that the structural cell really reds
when a drawn-page idiom is planted. G-2 (the divider recorded on both profiles,
4 node ids green). §6.6's raster leader-loop finding (exactly linear for n in
1..600 at every size 8..120 px). The QR conclusion. No third grid walk. The
no-new-import claim (0 added import lines).

### A standing observation, not this card's to fix

`_draw_difficulty_dots` is **genuinely dead in `src/`** — zero references of any
kind, the only dynamic-dispatch route being a test spy that restores itself. The
state is deliberate and pre-existing (CARD-228's three review cycles, CARD-241's
G-4, CARD-296's pre-gate). **Three separate cards have now independently
re-measured this same zero and each paid a round for it**, which is a candidate
for a standing rule rather than a fourth re-measurement.

## Worktree notes

- **CARD-219's work is the precedent to copy, not just respect.** It converted
  `tests/test_book_toc.py`'s positional assertions to read the page plan and
  measured the result: page bitmaps **2712 → 556 (−79.5 %)**, interleaved wall
  clock **17.86 → 5.65 s median (−68 %)**. It also left a fence —
  `test_the_drawn_tie_is_still_carried_here` — so a later card cannot quietly
  undo the conversion. Read that fence before touching the file.
- `src/nonogram/admin/book_pdf_generator.py` is a `conflict.hotspot`.

## [Reuse claim VERIFIED — 2026-10-26, orchestrator] AC-3 stands; CARD-295's round was wrong about its own routine

CARD-295's implementation round reported that this card's central reuse claim
does not reach: *"an `AnswerTile` is explicitly not a `Layout` and carries no
`GridLine`s … its tile grid needs either lines from COMP-007 or its own walk"*,
and recommended correcting AC-3 before dispatch. **That is false, and AC-3 needs
no correction.** Measured rather than read:

- **`AnswerTile` carries `GridLine`s.** `dataclasses.fields` gives it
  `vertical_lines: tuple[GridLine, ...]` and `horizontal_lines: tuple[GridLine, ...]`
  — the same two fields `Layout` has, alongside `thin_rule`, `thick_rule` and
  the four `grid_*` edges.
- **The routine does not take a `Layout`.** CARD-295 built
  `draw_grid_lines(stream, verticals: Sequence[GridLine], horizontals: Sequence[GridLine], *, grey)`,
  and `draw_ruled_grid(stream, layout, …)` is only the `Layout` convenience door
  onto it. It reads `line.start`, `line.end`, `line.position` and `line.width`
  and nothing else.
- **Driven functionally**: an `AnswerTile` built from a real layout's lines (11
  vertical, 11 horizontal) was passed straight to `draw_grid_lines` — *OK, no
  `Layout` involved*. (The probe then raised on my own counting code, which
  called `.count(' m')` on the `bytes` that `render()` returns; the drawing call
  itself succeeded.)

**The irony is worth keeping, because it is the wave's pattern inverted.** That
round *designed* the sequence-taking signature precisely so a non-`Layout` caller
could use it — "the split IS the consumability the dispatch asked for" — and then
reported that a non-`Layout` caller could not. Nine rounds on this board have
disagreed with their brief and been right; this is the first to disagree with
**itself** and be wrong, by **understating** its own work rather than overstating
it. Had the note been relayed and AC-3 "corrected", it would have **removed a
true requirement and licensed a third grid copy** — exactly what AC-3 exists to
prevent.

**Dispatch status: NOT dispatchable.** Two of three dependencies are unmet —
CARD-295 is `in_progress` (review cycle 1), CARD-227 is `ready` and unstarted.

## [Dependencies MET — 2026-10-29, orchestrator] superseding the line above; dispatched into wave 64

All three are `done` and merged, re-read from the card files rather than from
the board: **CARD-294** `b850bbbd`, **CARD-295** `ec6e4a06`, **CARD-227**
`8579094a` (wave 63, merged 2026-10-28). The reuse claim AC-3 rests on was
already verified above against CARD-295's real signature, and that signature is
now on main — so AC-3 is checkable, not predicted.

**Conflict graph, measured at dispatch rather than taken from the `Wave:`
comments.** CARD-301 is the wave's other card:
`CARD-301 ∩ CARD-297 = ∅` (3 paths vs 6, all nine present on disk), overlap
`0/min(3,6) = 0.000` against `max_overlap 0.3`. Hotspots: this card holds
`src/nonogram/admin/book_pdf_generator.py`, CARD-301 holds **none** of the
eight, so the shared-hotspot rule does not fire either. **Concurrent, under
the owner's cap of 2.** The `meta/architecture/requirements.yml` edge that
serialized CARD-301 against CARD-284 is moot — CARD-284 merged at `8492b63c`.
