# CARD-228: Difficulty becomes three dots, filled by tier — one glyph the whole book reuses

**Status:** review
**Priority:** P1
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/228-difficulty-dots
**Worktree:** ../PythonProject4-card-228
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "Header: difficulty right (three dots plus the word)"; the guide's "difficulty legend reuses the dots from the puzzle headers, so readers learn them here once"; the openers' and solution tiles' dots
**Idea:** —
**Wave:** 42
**Depends on:** —
**Touches:** src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_difficulty_dots.py, tests/test_book_interior_type_floor.py
**Review score:** 8.0 (cycle 1/3 — meets min_score 8, 0 critical, 2 important; severity gate open)
**Started:** 2026-10-16T17:04:17Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

A small card with wide reach: **one** function that draws a tier as three dots — filled for
the tier's rank, outlined for the rest — and four callers that stop inventing their own.

The artifact uses the dots in four places:

1. The puzzle page header, beside the word (CARD-207).
2. The guide's key strip, where "readers learn them here once" (CARD-229).
3. Each section opener (CARD-231).
4. Each solution tile's header (CARD-233).

Because four later cards depend on it, cut it first and keep it tiny. The artifact's own
mockup shows the shape: filled circles with a stroke, an outlined circle for the remainder,
at the header's optical centre beside the tier's word.

**What to check before writing.** `Tier` and `tier_of_record` live in `nonogram.difficulty`,
and `TIERS` in `book_plan`. The dots' count and order must come from that existing tier
order, never from a second list — a second ordering of the tiers is the kind of duplicate
this project has been bitten by (`strategy_counter.py` once carried a second classifier on
its own literals; see CARD-155).

## Acceptance criteria

- **AC-1** (happy, one dot per rank): *Given* each tier in `TIERS`, *when* its dots are drawn,
  *then* the number of filled dots equals that tier's 1-based rank and the total is always
  three. (test: `TestDifficultyDots_FilledCountIsTheTierRank`)
- **AC-2** (guard, one source of the order): *Given* the drawn dots, *then* the order and
  count come from `TIERS` — proved by a test that would fail if a second list were introduced
  (e.g. by driving the assertion from `TIERS` itself and asserting its length).
  (test: `TestDifficultyDots_ReadsTheProjectsTierOrder`)
- **AC-3** (happy, filled vs outlined): *Given* a middle tier, *then* the filled dots are
  solid and the remainder are outlined with the same stroke, measured off the ink.
  (test: `TestDifficultyDots_FilledAndOutlinedAreDistinguishable`)
- **AC-4** (happy, one function, four callers): *Given* the four call sites, *then* each draws
  its dots through this one function — asserted structurally, the way `tests/test_cli.py`'s
  import guard walks the tree with `ast`. (test: `TestDifficultyDots_HasExactlyOneDrawingSite`)
- **AC-5** (edge, the smallest place it appears): *Given* the smallest box any caller gives it
  (a solution tile's header), *then* the three dots fit without touching the text beside them
  or the tile's own rule. (test: `TestDifficultyDots_FitsTheSmallestHeader`)
- **AC-6** (edge, a puzzle with no tier of record): *Given* a puzzle whose tier cannot be read,
  *then* no dots are drawn at all — not three outlined ones, which would read as "easy".
  (test: `TestDifficultyDots_UntieredDrawsNothing`)

## Guardrails

- G-1: No new drawing primitive — circles go through the existing draw object (ADR-0036/R2).
- G-2: The dots are not text, so CON-020's 10 pt floor does not apply to them; the **word**
  beside them is text and does (test: `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-3: A puzzle's tier is read, never written (ADR-0033/R1).
- G-4: Out of scope — what each caller puts beside the dots; those are CARD-207, CARD-229,
  CARD-231 and CARD-233.
- G-5: This card changes no page's geometry on its own. It adds a function and its tests; the
  callers adopt it. If adopting it moves ink, that belongs to the adopting card's baseline.

## System contract

- CON-020 — reader-facing interior text at or above 10 pt; the dots are not text (check:
  `TestInteriorType_EveryFaceHoldsTheFloor`)
- ADR-0033/R1 — book assembly never changes a puzzle's tier (check: review-lens)
- ADR-0036/R2 — geometry from COMP-007 (check: review-lens)
- ADR-0037/R1 — a puzzle page's band carries number + tier only; the dots *are* the tier, so
  this stays inside R1 rather than widening it (check: review-lens)

## Architecture context

- **FR:** FR-033 (what the interior labels carry), FR-043.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1, ADR-0033/R1.
- **Components:** COMP-007, COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
  its own 0.5d card is what stops four agents inventing four slightly different dots — the
  shape of defect this project already carries in its own architecture model, where one rule's
  check names a test that does not exist and another names one that cannot test it.

### Implementation (agent, 2026-10-16)

**What was built — two halves, because ADR-0036/R2 splits them.**

1. `src/nonogram/export/layout.py` (COMP-007) gained the *measurement*:
   `difficulty_dots(left, top, right, bottom, *, filled, total) -> DifficultyDots | None`,
   the frozen `DifficultyDots` value it returns, and the four ratios it is cut from
   (`DIFFICULTY_DOT_RATIO` 0.3 of the box's height as a cap, `DIFFICULTY_DOT_GAP_RATIO`
   0.5 of a dot, `DIFFICULTY_DOT_STROKE_RATIO` 1/8, `MIN_DIFFICULTY_DOT_MM` 1.0).
   The size is `min(height cap, width fit)` — the module's own `min(cap, page fit)`
   shape — and the row is then centred in the box. It takes **two ints and a box, no
   tier**: ADR-0007 forbids COMP-007 from importing COMP-006, and the tier *order* is
   further out still (`admin.book_plan`), so there is no ladder in `export/` that could
   drift from `TIERS`. `DifficultyDots.__post_init__` refuses six rows that could
   not say what they mean — an empty row, a rank outside `1..total`, a stroke of zero,
   dots of unequal size, dots not on one line, dots that overlap **or touch**, and a
   stroke of half the diameter or more (which would close the ring and make an outlined
   dot identical to a filled one). AC-3 and AC-6's "not three outlined dots" are
   therefore partly *structural*: those values are unconstructible.

   **Corrected in review cycle 1 (F-002).** As first shipped, only two of those
   refusals — the `filled` range and the ring-closing stroke — had a test, and they are
   exactly the two AC-3 and AC-6 lean on, so the structural claim above held. The
   broader sentence did not: "refuses a row that cannot say what it means" was true of
   the code and untrue of the *tests*, which is the shape of defect the three cards
   before this one failed on. The reviewer disabled each of the other four and all 186
   tests stayed green. Each now has its own `pytest.raises` case, and each disabled
   refusal is now red — see the fix notes at the foot of this card.

2. `src/nonogram/admin/book_pdf_generator.py` (COMP-009) gained the *one drawing site*:
   `_draw_difficulty_dots(draw, stored_tier, left, top, right, bottom)`. It reads the
   tier through `difficulty.tier_of_record` (ADR-0033/R1 — read, never written), takes
   `total=len(TIERS)` and `filled=TIERS.index(tier) + 1` from `book_plan.TIERS` and
   from nothing else, and strokes the circles on the draw object it was handed
   (`draw.ellipse`, G-1 — no new primitive, no new surface). It returns the geometry it
   drew so a caller can set its word beside the ink, and returns `None` — drawing
   nothing at all — for a row with no tier of record, for a tier absent from `TIERS`,
   and for a box the measurement declined.

**G-5 held: no page's geometry moved.** Nothing calls `_draw_difficulty_dots` yet. The
four callers (CARD-207/229/231/233) adopt it, and no existing page gained or lost a
pixel — `git diff` touches only additions in the two source files, and the whole suite
is unchanged.

**One AC per test:**

- AC-1 `TestDifficultyDots_FilledCountIsTheTierRank` — rank per tier, total always
  `len(TIERS)`, the rank re-counted off the *rendered ink* (solid middles) rather than
  read back, and swept over the corpus.
- AC-2 `TestDifficultyDots_ReadsTheProjectsTierOrder` — the assertions are driven from
  `TIERS`, with three controls that give the guard its discriminating power:
  shortening `TIERS` to two shortens the glyph (**caught**), reversing it reverses every
  rank (**caught**), and a tier the ladder does not carry draws nothing (**not caught** —
  the complement). Plus a completeness test for the set the guard consults
  (`tuple(TIERS) == tuple(Tier)`, every member once) and an *independent* second source
  of the same order (COMP-006's `TIER_BANDS`, sorted by band floor), so a reordered
  `TIERS` fails here instead of printing a glyph that grades Hard as one dot.
- AC-3 `TestDifficultyDots_FilledAndOutlinedAreDistinguishable` — measured off the ink:
  solid middles vs paper middles, the ring run on each dot's middle row equal to the
  reported `stroke`, one silhouette shared by filled and outlined dots, the middle third
  of an outlined dot all paper. Control: the type refuses a ring-closing stroke.
- AC-4 `TestDifficultyDots_HasExactlyOneDrawingSite` — an `ast` walk of
  `src/nonogram/**/*.py` modelled on `tests/test_cli.py`'s import guard, with
  `_round_mark_sites(sources, methods)` taking its sources as an argument exactly as
  `_outward_imports` does, so the rule runs against fabricated packages too. Controls:
  a second site in another module, a second site in the same module, a method and a
  nested helper (innermost enclosing function reported), a module-level call — all
  **caught**; a flat shape (`rectangle`/`line`/`text`/`polygon`), an attribute *read* of
  `.circle`, and a bare `ellipse(...)` function call — all **not caught**. The set the
  guard consults has its own completeness test *against Pillow's API*: every public
  `ImageDraw.ImageDraw` method is classified into exactly one of `ELLIPSE_METHODS`,
  `ROUND_ENOUGH_METHODS` or `FLAT_METHODS`, so a Pillow release that adds a method fails
  that line until this project decides which kind it is.
- AC-5 `TestDifficultyDots_FitsTheSmallestHeader` — the box is *measured*, not invented:
  the narrowest of a packed solution tile's own bands at the 10 cm minimum trim.
  `SOLVED_TILE_CAPACITIES` is `(2, 4)`, so there are **six** such bands, and the
  narrowest measures **474 x 142 px** — the narrowest header this project can measure
  today. (Review cycle 1, F-005 corrected "313 x 141 px, four answers to a page"; the
  test was always right, because it measures the box rather than hardcoding it. F-007
  corrected "any caller will hand the glyph" to "any caller that exists today".)
  Asserts the glyph
  is produced, keeps paper on all four sides, never reaches the tile's own rule at
  `drawing_top`, lands its rendered ink exactly inside the reported box, and leaves more
  width beside it than the widest tier label needs at the band's own shrink floor
  (`_MIN_BAND_FONT_RATIO`). Control: a box one dot too short is **declined** (`None`,
  zero ink) — paired with a test that the decline is not a blanket rule.
- AC-6 `TestDifficultyDots_UntieredDrawsNothing` — ten unreadable stored values each
  leave a blank page; "not even three outlined dots" is asserted by pixel count against
  a page a real glyph *did* ink; the readable spellings are the control; `"guess"` still
  reads as Hard through the one reader; and the zero-filled row is shown to be
  unconstructible in both halves.
- The invariants: `TestDifficultyDots_GeometryHoldsOverASeededCorpus` — a hand-built
  seeded `random.Random(228)` corpus of 700 boxes x 3 tiers = 2100 cases, with **two**
  floors asserted inside the tests (`CORPUS_MIN_CASES` 2100 cases,
  `CORPUS_MIN_GLYPHS` 1800 of them actually producing a glyph — the second is the
  load-bearing one, since 2100 declined boxes would satisfy the first and measure
  nothing) and an assertion that *some* boxes are still declined, so the declining
  branch is swept too. Invariants named then checked: one line of equal circles; no two
  dots touch; strictly inside the box; centred in it; at least a fifth of a dot of white
  at each end (the bound the docstring quotes); the diameter under both of its two
  bounds; the footprint independent of the tier; the measurement pure.

**G-2 is now falsifiable** (`tests/test_book_interior_type_floor.py`, in `Touches`):
`TestInteriorType_DifficultyDotsAreNotText` shows the glyph makes **no** `draw.text`
call at all — so CON-020's floor cannot reach it *and* nothing can evade the floor by
hiding a caption inside it — with the same spy seeing the band's word as the control.
`TestInteriorType_EveryFaceHoldsTheFloor` is untouched and still green.

**Edge mutants run against the finished tests** (each reverted): `total=3` literal for
`len(TIERS)`; a second literal tier-to-rank dict; untiered falling back to `TIERS[0]`;
the half-dot width reservation dropped; a ring-closing stroke; a left-aligned instead of
centred row; outlined dots filled with ink; the minimum-dot floor removed; a rogue
`draw.ellipse` added to `export/png.py`; a rogue `draw.regular_polygon` added to
`admin/grid_renderer.py`. **All ten were caught** — ten is the evidenced figure, named
one by one above; the hand-back for this card said eleven, and that number is withdrawn
as unevidenced (review cycle 1, F-005). The reviewer independently re-ran the rogue
`draw.ellipse` and confirmed it still kills.

**Invariants the card did not name, found while building:**

- *The glyph's footprint must not depend on the tier.* If the row's size or position
  moved between Easy and Hard, every adopting caller's header would shift between two
  puzzles on facing pages. It holds by construction (only `filled` varies) and is swept
  (`test_the_footprint_does_not_depend_on_the_tier`, `test_only_which_dots_are_filled_changes_between_tiers`).
- *A tier absent from `TIERS` has no rank.* The card's AC-6 is about a tier that cannot
  be *read*; there is a second route to the same place — a tier the ladder does not
  carry — and it must take the same exit. It does (`tier not in TIERS` returns `None`),
  and that is also AC-2's "not caught" control.
- *An outlined dot needs white inside it, which bounds the stroke.* The card asks for
  "the same stroke" but not for an upper bound on it; without one, a large enough stroke
  silently turns all three dots into filled ones. Now refused by the type.
- *The row must not be flush with its box.* "Beside the word" is a property of the
  geometry, not of the caller's care, so the width fit reserves one more half-dot than
  the row occupies. This is why AC-5's "does not touch the text beside them" can be
  asserted at all without knowing CARD-207/229/231/233's typography (G-4).

No `SCOPE+` entries: every file changed is in the card's own `Touches`.
No blockers. No new runtime dependency (stdlib + Pillow only, as already declared).

**How AC-4 was read, since G-5 says this card adds no caller.** "Given the four call
sites, then each draws its dots through this one function" cannot be asserted against
four call sites that do not exist yet, and building them would be exactly the scope
growth G-4/G-5 forbid. So the criterion is asserted in its forward-compatible,
*structural* form — the package contains **exactly one** function that puts a round mark
on a page, and the walk covers `src/nonogram/**/*.py` rather than a list of files. That
is the assertion that actually binds CARD-207/229/231/233: whichever module each of them
ends up drawing from, a second dot **drawn by one of the four guarded routes** is a
failing test on their branch rather than a discovery on a printed proof. (As first
shipped the guard covered one route while claiming four cards could not "each grow their
own circles"; review cycle 1, F-001, planted three second glyphs that survived it. The
routes it guards and the routes it cannot see are both named now — see the fix notes at
the foot of this card.) (All four callers' own `Touches` name only
`admin/book_pdf_generator.py`, so the one site is reachable from each of them —
`export/pdf.py`'s `_draw_header` is the single-puzzle CLI/web path CON-019 freezes, and
no caller needs to draw from there.)

### Review cycle 1 fixes (agent, 2026-10-16)

Cycle 1 scored **8.0** with no Critical findings: no correctness bug, no page's ink moved,
the geometry verified correct under independent analysis. Every finding had the same root
cause (RC-1) — **a guard's or a type's stated coverage was wider than the mechanism that
enforced it**. The mechanisms were real; their stated reach overshot. So the rule this
cycle worked by is the one the three cards before it produced: *a claim about coverage
needs a control that can fail*, and every coverage claim below is followed by the control
that was run, in its own fresh process (running mutants sequentially from one parent
produced false KILLED verdicts for the reviewer, so each one here is a separate
invocation of `pytest`, with the mutated file restored and `shasum -c`-verified after).

The loop: `pytest tests/test_book_difficulty_dots.py tests/test_book_interior_type_floor.py
tests/test_cli.py` — **198 green** (was 186; +12 tests, −1 removed). `tests/test_suite_profile.py`
(the repo-wide structural guard over `src/` and `tests/`) was also run and is green, since
this cycle adds `ast` walks of its own.

**F-001 — the round-mark guard's partition.** The guard now covers **four** routes instead
of one, and names the routes it cannot cover.

*What the finding got right, and what it got wrong.* It was right that the partition
contradicted its own rationale (`polygon` binned flat while the strictly weaker
`regular_polygon` was binned round) and right that three planted glyphs survived. Its
proposed fix was partly wrong, and the error mattered: it said moving `polygon`, `point`
and `bitmap` into `ROUND_ENOUGH_METHODS` "costs nothing today" because "the file already
asserts these are called nowhere in the package". **That premise is false.**
`draw.polygon` is called at `book_pdf_generator.py:1895` (the arrow head between two
boxes of the proof sheet's pipeline diagram, three vertices), and `point` is called twice
in `sourcing/image.py` — as `Image.point`, a per-pixel value map, which the walk could
not tell from a draw call because it matched any attribute call of that name. Moving
either would have turned `test_no_module_approximates_a_round_mark_another_way` red on
honest code, and "fixing" that by weakening the assertion is the move this card is not
allowed to make. So only `bitmap` moved for free; the other two got a mechanism.

1. **`bitmap` → `ROUND_ENOUGH_METHODS`** (a blitted mask is as round as its mask, and
   nothing calls it). *Control:* planted `draw.bitmap((0, 0), image, fill=INK)` in
   `export/png.py` → `test_no_module_approximates_a_round_mark_another_way` **red**;
   reverted, hash verified.
2. **`polygon` and `point` → a new `VERTEX_BOUNDED_METHODS`, guarded by a vertex bound,
   not by absence.** `test_no_module_draws_a_round_mark_out_of_vertices` asserts every
   draw-object call to either passes a *countable literal* list of at most
   `MAX_FLAT_VERTICES` (4) points. A list this walk cannot count is a **failure**, not a
   pass, so the blind spot shows itself instead of swallowing a glyph. *Controls:*
   cycle 1's H2 (a 32-gon in `export/png.py`) → **red**; cycle 1's H3 (a filled disc via
   `draw.point([(x, y) for x in range(9) for y in range(9)])`) → **red** (unmeasurable
   list); the real three-vertex arrow head and `Image.point`'s two calls → **pass**, with
   the fabricated counterparts pinned as not-caught controls
   (`test_a_three_vertex_arrow_head_is_not_caught`,
   `test_a_point_call_on_an_image_is_not_a_draw_call`).
3. **Telling a draw object from an image, measurably.** `_draw_calls` filters on the
   receiver (`_is_draw_receiver`: the bare name `draw`, or an inline `ImageDraw.Draw(...)`),
   which is what excludes `greyscale.point(...)` honestly rather than by exception. The
   receiver set is not assumed: `test_every_draw_object_in_the_package_is_spelled_draw`
   walks the package and asserts every assigned `ImageDraw.Draw(...)` and every parameter
   annotated `ImageDraw.ImageDraw` carries that one name. *Control:* planted a second
   spelling (`canvas = ImageDraw.Draw(image)` plus a disc drawn on it) in `export/png.py`
   → that completeness test **red**. The widened blind spot fails a test rather than
   hiding a dot.
4. **The `text` route closed — wider than the finding asked, because the narrow form
   misses the realistic case.** The finding asked for "no `draw.text` call passes a string
   literal containing a geometric-shape codepoint". That would **not** catch CARD-207's
   cheapest route: its header string is built at the *caller* and handed to `_set_band`,
   so the literal is nowhere near a `draw.text` call. `test_no_module_types_a_round_mark_as_a_character`
   therefore asserts that **no string literal anywhere in `src/nonogram/`** holds a
   `ROUND_DINGBATS` codepoint (U+25A0–U+25FF, U+2022, U+2219), docstrings included.
   *Controls:* cycle 1's H1 (`draw.text(xy, "●●○")` in `export/png.py`) → **red**; the
   f-string-at-the-caller form and a `draw.text` argument both caught in fabricated
   sources; `'PUZZLE 12  MEDIUM'`, `'...'` and `'Easy / Medium / Hard'` pinned as
   not-caught.
   *One exemption, and it is earned rather than granted:* `admin/pdf_generator.py` (the
   legacy ReportLab generator) carries three U+2022 bullets in a prose paragraph about
   the difficulty levels. `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`
   asserts the exempt set is **exactly** the set of modules carrying such a codepoint
   today, and that the one module in it makes no draw-object call at all and contains no
   `ImageDraw` — so it cannot reach a Pillow page however its prose is spelled. The
   exemption cannot quietly grow to a module that draws, nor quietly outlive its reason.
5. **The three overshooting statements narrowed to what the walk measures.**
   `FLAT_METHODS` is now the residue after four guarded sets, described as such, instead
   of "none of them can draw a circle". `ROUND_ENOUGH_METHODS`' comment now says "the
   four methods the package calls nowhere" instead of implying there is no other route.
   The class docstring now lists the four guarded routes **and** the routes this
   instrument cannot see, next to the `getattr` hole it already admitted: anything
   outside `ImageDraw` entirely (`Image.paste` of a circular mask, `ImageDraw.floodfill`,
   a pre-rendered PNG asset, a circle arriving inside an imported image), a dynamically
   dispatched draw call, an uncountable vertex list (which fails rather than passes), and
   a draw-object spelling the package does not use (which fails its own completeness
   test). **Stated and not made falsifiable:** the `Image.paste`/asset routes. The set of
   watched methods comes from `dir(ImageDraw.ImageDraw)`, and nothing in this card's
   instrument can reach past it; closing that would be a card of its own, not a line here.
   It is written down as a named limit rather than left as a confident sentence.

**F-002 — the four unexercised refusals.** `test_the_type_refuses_every_row_it_documents_as_impossible`
constructs `DifficultyDots` directly with a zero stroke, two dots of different diameters,
two dots on different tops and two overlapping dots. *Controls, one mutant per fresh
process, each reverted and hash-verified:* disabling `layout.py`'s `self.stroke < 1`,
`len(diameters | heights) != 1`, `len(tops) != 1` and the spacing refusal each turn that
test **red** (each previously survived with 186 green). The reviewer's two confirmations
are kept and remain true: `difficulty_dots` is still the sole constructor,
`dataclasses.replace` re-runs `__post_init__`, `_draw_difficulty_dots` constructs none —
so the refusals cannot be bypassed — and the two refusals AC-3 and AC-6 lean on were
already pinned, so the "unconstructible rather than merely untested" claim held for those
two ACs and still does. Only the broader sentence in these notes was wrong; it is
corrected above.

**F-003 — `DIFFICULTY_DOT_RATIO`'s derivation pinned, by a second measurement.**
`test_the_dot_is_the_cap_height_of_the_band_it_sits_on` measures the dot at a box
`HEADER_BAND_MM` deep (142 px) and wide enough that the height cap decides, and compares
it against the **rendered** cap height of a capital in the face the band is really
lettered in at `HEADER_FONT_MM` type — 43 px, against the dot's 42 — with two pixels of
tolerance. The bound comes from the two font/band constants and the real font, never from
the constant under test, which is the anti-pattern CLAUDE.md names and which
`test_a_dot_never_outgrows_its_share_of_the_box` commits (it is left alone: it bounds the
*width* term usefully, and the height term is now pinned here). The docstring's 0.7-em
rule of thumb is asserted separately and more loosely. *Controls:* 0.3 → **0.45 is now
red** (it survived cycle 1); 0.3 → 0.32 is still **green**, so the pin is on the
derivation and not on a bit pattern (0.29–0.32 passes, 0.45 and 0.9 do not).

**F-004 — the spacing refusal matches the invariant.** `left <= right` → `left <= right + 1`,
message "two dots of the row overlap or touch". *Controls:*
`test_the_type_refuses_two_dots_that_merely_touch` pairs the touching row (refused) with
the row one pixel wider (accepted), and reverting the bound to `left <= right` turns it
**red**. The corpus never produced a touching row (the gap is at least 6 px at the 12 px
minimum dot), so no page's geometry changes — this closes a claim/mechanism gap, not a
defect.

**F-005 — the card's prose corrected** (above): AC-5's box is 474 × 142 px, not
313 × 141, and there are six tile bands at capacities `(2, 4)`, not four. Re-measured
through the test's own fixture; all six bands are 474–475 × 142 and the narrowest is the
right-hand column's at either capacity. The test needed no change — it measures. The
mutant count stands at the **ten** these notes name one by one; the hand-back's "eleven"
is withdrawn as unevidenced.

**F-006 — the two near-tautological tests, judged and acted on.** The ratio test's middle
clause (`0 < DIFFICULTY_DOT_RATIO < 1` — what let F-003 through) is **replaced** by
F-003's derivation assertion; the test keeps only the two clauses that are genuinely
bounds. `test_the_real_packages_one_site_is_the_dot_drawer_itself` is **removed**, and its
one real check moved into `test_the_walk_actually_sees_the_package`, which now resolves
both halves of `THE_DRAWING_SITE` against the source on disk (`f"def {THE_DRAWING_SITE[1]}"`)
rather than against a hardcoded name. *Control:* a typo in `THE_DRAWING_SITE`'s function
name is caught **twice** after the removal (`test_the_walk_actually_sees_the_package` and
`test_the_package_draws_a_round_mark_in_exactly_one_function`), so dropping the test loses
nothing. Nothing was padded in its place.

**F-007 — the superlative softened to what can be measured.** AC-5's class docstring now
claims "the narrowest header this project can measure today" and says why the superlative
is not yet checkable (only CARD-233's box exists; CARD-229's key strip and CARD-231's
section opener are unbuilt and could be narrower), alongside the property that does carry
over: a box too small is declined rather than overflowed. **Not done here:** adding an
AC-5 re-check to CARD-229's and CARD-231's acceptance criteria — those are other cards
under `meta/`, which this agent does not own.

**G-5 re-verified after the fix:** `grep -rn "_draw_difficulty_dots" src/` finds the
definition and no call. No page's geometry moved; `export/layout.py` still imports nothing
from `nonogram` (ADR-0007, the COMP-007/COMP-009 split), and its import surface is
untouched. Every file changed is in the card's own `Touches`; `tests/test_book_interior_type_floor.py`
needed no change, because the dingbat guard belongs beside the AC-4 walk rather than
beside CON-020's floor.

### Orchestrator log

- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
- [Scope] src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_difficulty_dots.py, tests/test_book_interior_type_floor.py — exactly the card's Touches:, no drift, no SCOPE+. Components touched are COMP-007 and COMP-009, exactly the card's slice, so the scope gate sees no growth. Noted for the retrospective rather than as a finding: 1579 insertions on a 0.5d card, 1144 of them one new test file — volume in the tests, not scope in the source.
- [Guard] G-5 verified mechanically in the main repo, not taken on the agent's word: `grep -rn` over src/ shows `_draw_difficulty_dots` has no caller anywhere, so no existing page gains or loses ink. The four adopting cards (CARD-207/229/231/233) are what wire it.
- [Build gate] cycle gate is the full suite (review.test_scope: full). Queued behind CARD-213's run on meta/kanban/.full-suite.lock — the agent's own `pytest tests/ --ignore=tests/e2e -x` is not the gate.
- [Build gate] cycle 1: **7557 passed, 9 skipped, exit 0 in 877.93s** — full suite in the worktree,
- [Review 1/3] spawned. Briefed NOT to run the full suite (I already have its result, and CARD-213's
- [Review 1/3] **score 8.0**, risk LOW, 7 findings, 0 critical, 2 important. Meets min_score 8, so
- [Review 1/3] **AC-4's reinterpretation is ACCEPTED** by the reviewer, and on the stronger of the two
- [Review 1/3] F-001, the finding that matters, and I confirmed its premise myself before acting on it:
- [Review 1/3] F-002: four of the five `__post_init__` refusals survive being disabled with 186 tests
- [Review 1/3] what the review CONFIRMED rather than merely passed: the COMP-007/COMP-009 split is real,
- [Review 1/3] **METHODOLOGY FINDING, and it reaches past this card — feed it to the retrospective.**
- [Fix 2] dispatched. On F-001 I chose to do all three remedies rather than pick one: widen where free
- [Fix 1] applied as `b3ba400`, all 7 findings marked fixed, loop 198 green (was 186). **And the fix agent found a premise in MY brief false, checked it, and refused the instruction — which is what I asked for and the right call.** Cycle 1's report said moving `polygon`/`point` into ROUND_ENOUGH was "free" because the file asserts they are called nowhere; I propagated that into the fix brief without checking it. It is wrong, and I have now confirmed it myself: `draw.polygon` is called at book_pdf_generator.py:1895 (the proof sheet's arrow head) and `.point(` twice in sourcing/image.py (as `Image.point`, a pixel value map the old walk could not tell from a draw call). Moving either would have reddened a test on honest code, and the only way to 'fix' that would have been to weaken the assertion. Only `bitmap` moved for free; the other two got a real mechanism (VERTEX_BOUNDED_METHODS held to MAX_FLAT_VERTICES, with an uncountable vertex list treated as a FAILURE rather than a pass, so the blind spot announces itself).
- [Fix 1] the agent also closed the `text` route WIDER than I asked, with a reason I accept: my suggested form — no `draw.text` call passing a dingbat string literal — would **not** catch CARD-207, because its header string is built at the caller and handed to `_set_band`, so no literal sits anywhere near a `draw.text` call. The shipped rule is that no string literal anywhere in src/nonogram/ holds a ROUND_DINGBATS codepoint, and its caught-control covers the f-string-at-the-caller form specifically. I verified the exemption's shape myself: `DINGBAT_EXEMPT_MODULES` is held to an **equality** against the modules actually carrying such a codepoint, and the one exempt module is additionally asserted to make no draw call and contain no `ImageDraw` — so the exemption cannot grow to cover a module that draws, nor outlive its reason. That is CARD-238's promoted pattern applied correctly rather than cited.
- [Review 2/3] dispatched as ADVERSARIAL verification of the fix, not a fresh review. The fix introduced three new sets and three new claims (VERTEX_BOUNDED_METHODS, `_is_draw_receiver`, ROUND_DINGBATS + its exemption), and CARD-238 needed five cycles precisely because four of them fixed the named instances while minting the next cycle's finding in the same mechanism. The reviewer was told that checking for exactly that is the whole assignment, pointed at the specific holes worth probing (an uncountable vertex list passing silently; whether `_is_draw_receiver`'s completeness test fails on a NEW receiver spelling or only on a changed known one; whether `_dingbat_literals` sees f-string format specs, implicit concatenation, `chr()` and module-level constants later interpolated), and told explicitly NOT to treat cycle 1's report as ground truth, since it contained a factual error that propagated into the fix brief.
