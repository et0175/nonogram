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
**Review score:** 8.0 (c1) → 8.5 (c2) → 8.0 (c3/3) — min_score met every cycle; severity gate FAILED every cycle; min_improvement missed at c3
**Started:** 2026-10-16T17:04:17Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** — (escalation resolved 2026-10-16 by owner decision; see the AC-4 amendment below)

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
- **AC-4** (happy, one drawing site — **amended 2026-10-16 by owner decision; see the amendment
  section below**): *Given* the package, *then* exactly one function draws a round mark through any
  of the four routes a static walk can see — an **ellipse-family method**, an **unrecognised draw
  receiver**, an **unrecognised `.Draw(...)` binding form**, or a **dingbat string literal** — and
  the routes the walk cannot see are named, each with a mutant that demonstrates it is open.
  (test: `TestDifficultyDots_HasExactlyOneDrawingSite`)
  *This replaces the original wording ("given the four call sites, then each draws its dots through
  this one function"), which was unsatisfiable while G-4/G-5 forbid building CARD-207/229/231/233,
  and whose forward-compatible reading — a universal negative over Python syntax — three review
  cycles of a static `ast` walk did not hold. The universal guarantee moves to CARD-241.*
- **AC-5** (edge, the smallest place it appears): *Given* the smallest box any caller gives it
  (a solution tile's header), *then* the three dots fit without touching the text beside them
  or the tile's own rule. (test: `TestDifficultyDots_FitsTheSmallestHeader`)
- **AC-6** (edge, a puzzle with no tier of record): *Given* a puzzle whose tier cannot be read,
  *then* no dots are drawn at all — not three outlined ones, which would read as "easy".
  (test: `TestDifficultyDots_UntieredDrawsNothing`)

## AC-4 amendment — 2026-10-16, owner decision at the architect station

**Decision: narrow AC-4 to what the guard actually holds, land this card, and move the universal
guarantee to its own card (CARD-241).** Option (c)-then-(b) of the three put to the owner.

### What the three cycles established

The glyph is correct and was never in question: AC-1, AC-2, AC-3, AC-5 and AC-6 are green, the
geometry was verified independently in cycles 1 and 2 (including the row-not-flush bound, measured
at 0.2105 of a dot against an asserted 0.20), G-5 holds with zero callers, G-1..G-5 hold, the
system contract is 4 of 4, and both exemption sets rejected every absorption probe cycle 3 threw
at them. The cycle-2 structural fix was real work: cycle 3 confirmed all three of cycle 2's
survivors are dead, the composition claim holds, and both named limits really are open.

What did not hold is AC-4's **forward-compatible reading** — that no second round mark can be
written anywhere in the package. Three cycles of a static `ast` walk landed 3 glyphs, then 2,
then 3, **a new syntactic family each time**: receiver → binding form → call shape and cross-call
ink. The root cause is stable and worth stating once more, because it is the generalisable part:
**these guards discriminate by syntactic form, and no authority enumerates the forms.**
`dir(ImageDraw.ImageDraw)` is a real authority for the *method* half — which is why that half is
sound — but Python's grammar offers nothing to import that lists every way to write a vertex list
or name a receiver. So enumeration cannot converge, and cycle 2's default-deny inversion, while
right, only moves the frontier rather than closing it.

### Why not the other two options

**(a) Move `line` into the vertex-bounded set — rejected as blocked, not merely expensive.**
Verified at this station: `FLAT_METHODS`' stated reason for leaving `line` unguarded ("a straight
line has no vertex list to hide a dot in") is **factually false**. Pillow's own docstring reads
*"Draw a line, or a connected sequence of line segments"*, the method calls `draw_lines`, and
`joint="curve"` rounds the joints. The package already hands it computed lists at
`book_pdf_generator.py:1429` (`ends`), `:1441` (`list(side)`), `png.py:186` and `:217` — those are
computed by construction and **cannot** pass a countable display, so each would need an exemption.
That is the same regress the cycle-2 fix was right to refuse for receivers, arriving one level down.

**(d) Land with the three evasions recorded as bounds — rejected.** That ending (CARD-238 →
CARD-239) suits a mechanism that converged with honestly-named residue. Here the bounds would
**swallow the AC**: "no second round mark, except via `draw.line`, except via a loop of
`draw.point`, except via a stored bound method" is not a promise CARD-207/229/231/233 can build
on, and those four cards are the entire reason this one was cut first.

### What this card must now do — and it is small

1. **Narrow the AC-4 wording in the test's own docstring** to the four routes the walk sees, exactly
   as the amended AC above states, and keep the existing "true by mechanism" / "named limits" split
   that cycle 2 introduced — it is sound and cycle 3 verified both directions of it.
2. **Add cycle 3's three survivors to the named-limits list**, each with the mutant that
   demonstrates it is open, in the same style as the `getattr` and `chr()` limits already carried:
   `draw.line` polylines, ink accumulated across calls, and a stored bound method. A named limit
   with a surviving-mutant demonstration is honest; the same route left implied is not.
3. **Correct the two over-reaching sentences cycle 3 found**, which are wording, not mechanism:
   `_unrecognised_draw_receivers` does **not** collect "every written call to a draw-method name
   whatever its receiver" — `_draw_method_calls` requires `isinstance(node.func, ast.Attribute)`,
   so `stamp(circle)` is collected by nothing; and route 3's "a circle built out of vertices is
   held to `MAX_FLAT_VERTICES`" is false, because the bound is **per call**.
4. **Point the limits list at CARD-241** as the card that closes them, so a reader of this guard
   learns where the universal guarantee lives.
5. **Fix `FLAT_METHODS`' false rationale for `line`** — say it is unguarded and *why that is a
   known hole*, not that it cannot hide a dot. Leaving a false reason in place is how the next
   reader concludes the route is safe.
6. Optional, cheap, cycle 3's two Minors: keep the function names in `DRAW_OBJECT_UNBOUND_SITES` by
   splitting the literal to defeat a *textual* grep (`"render" + "_pages"` with a comment), which
   was the third option the fix cycle missed; and widen that limit's wording to "moved **or
   replaced** within one module+form".

### Guardrails on the amendment

- **GB-1: no new guard mechanism.** This is a wording-and-limits pass plus one false rationale
  corrected. The instrument change is CARD-241's, not this card's. If closing a route looks
  tempting, that is CARD-241.
- **GB-2: do not weaken what cycle 2 built.** The three default-deny mechanisms and both exemption
  equalities stay exactly as they are — cycle 3 probed them and they held.
- **GB-3: every named limit carries a mutant that demonstrates it is open.** A limit asserted
  without that demonstration is the same defect in a new costume.
- **GB-4: `src/` stays untouched** except `FLAT_METHODS`' rationale if it lives there (it does
  not — it is in the test file). G-5 must still hold: zero callers for `_draw_difficulty_dots`.

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

### Review cycle 2 fixes (agent, 2026-10-16)

Cycle 2 scored **8.5** — improvement met, no Critical, and **one new Important
finding in the fix itself** (F-101): two of the four limits the widened round-mark
guard stated about itself were false, and the reviewer landed a second dot glyph
twice with 198 green. Root cause RC-1, named by the reviewer and accepted here:
**the guards discriminated by syntactic form, and their completeness tests
enumerated only the forms in current use — so a new spelling evaded the guard and
its completeness test together.**

Worked in two steps on purpose, and the first was landed before the second was
attempted (`dc8d2df`, then `56cec05`), so a true narrow sentence was on disk at
every point.

**The distinction this cycle actually delivers.** The guard's limits are now
sorted into two kinds, and the class docstring says which is which:

*True by mechanism* — each has a control that fires through the real check:

1. **An uncountable vertex argument fails.** `_uncountable_vertices` enumerates
   the one shape it understands (a list or tuple display of countable elements)
   and complains about everything else: no positional argument, a bare name, a
   call, a comprehension, a conditional, a display holding a starred unpack, and
   a countable display over `MAX_FLAT_VERTICES`.
2. **An unrecognised draw receiver fails.** `_unrecognised_draw_receivers`
   collects every written call to a draw-method name *whatever* its receiver, and
   a receiver that is not a draw object as this package spells one must be a named
   exemption. It judges a parameter by the draw method written on it rather than
   by how it was typed, which is what closes the unannotated-parameter route.
3. **An unrecognised `.Draw(...)` binding form fails.** `_draw_object_bindings`
   classifies every `.Draw(...)` call by the form it sits in — assignment,
   annotated assignment, walrus, receiver, argument — and reports anything else as
   its own `unrecognised:<NodeType>`, which breaks an equality instead of
   contributing nothing.

*Named limits* — written down because this instrument genuinely cannot reach
them, each confirmed by a mutant that **survives**:

4. Anything outside `ImageDraw` entirely (`Image.paste` of a circular mask,
   `ImageDraw.floodfill`, a pre-rendered asset, a circle inside an imported
   image). The watched set comes from `dir(ImageDraw.ImageDraw)` and nothing here
   sees past it. Not mutated — unchanged from cycle 1, still a card of its own.
5. A dynamically dispatched draw call. **G1** `getattr(draw, "ellipse")(box)`
   planted in `export/png.py` → **SURVIVED**.
6. A round mark **computed** into a string rather than written as one. **D1**
   `chr(0x25CF)*rank + chr(0x25CB)*(3-rank)` into `draw.text` → **SURVIVED**
   (F-102). The dingbat rule's own sentence was already exact — it is about string
   *literals* — so claim and mechanism agreed; only the limit list was asymmetric.
7. `DRAW_OBJECT_UNBOUND_SITES` carries a count per module+form rather than the
   enclosing function names. One of those functions is named by
   `meta/profiling`'s frozen `RENDER_API_PATTERN`, so writing it out adds this
   file to `test_suite_profile.py`'s render-heavy set and reddens a guard with
   nothing to do with this card — and the snapshot that would then have to be
   restated lives under `meta/`, which this card may not commit. What the count
   gives up is noticing a site *moving* between two functions of one module.

**Why not "add the missing spellings".** CARD-238 escaped this family by
deriving its set from an **authority** (`dir(os)`, `dir(os.path)`, `dir(glob)`,
`dir(pathlib.Path)`). The *method* half of this guard already has that authority
(`dir(ImageDraw.ImageDraw)`) and it is sound. But there is no authority that
enumerates "every way to write a vertex list" or "every way to name a draw
receiver" — Python's grammar has no such list to import — so adding shapes is an
infinite regress, which is how CARD-238 burned cycles 1 through 4. Inverting the
default converges instead: the guard never predicts the next spelling, it
recognises the present one and refuses the unknown.

**Exemptions, earned rather than granted** — the shape `DINGBAT_EXEMPT_MODULES`
already uses: an equality against what exists today, plus a second assertion that
each exempt site cannot actually draw a round mark. **No bin was widened to make
an honest call pass** (the move cycle 1's report recommended and this card
refused):

- `NON_DRAW_RECEIVER_SITES` — the two `Image.point` calls in `sourcing/image.py`.
  The second assertion pins the discriminating property: `Image.point` takes a
  lookup table or a lambda and *never a coordinate display*, so a future card
  writing coordinates on an excused receiver reds
  `test_the_non_draw_receiver_exemptions_cannot_draw_a_round_mark` rather than
  inheriting the excuse. It also asserts neither name is ever bound to a draw
  object anywhere in the package, so the excuse cannot be borrowed by rebinding.
- `DRAW_OBJECT_UNBOUND_SITES` — the inline `ImageDraw.Draw(probe).text(...)`
  metric (`receiver`) and the three draw objects handed straight to a function
  (`argument`). The three are safe **not** because this line says so but because
  the callee's own parameter is then a receiver and mechanism 2 covers it whatever
  it is called. The two mechanisms compose; neither is trusted alone.
- The real three-vertex arrow head at `book_pdf_generator.py:1895` needed no
  exemption at all — it passes the vertex bound as it stands, with
  `test_a_three_vertex_arrow_head_is_not_caught` as the not-caught control.

**Controls, each caught with its entry and missed without it** (the CARD-238
standard the dingbat exemption already met):

- `test_a_starred_vertex_literal_is_caught` — the complaint fires, *and* the two
  clauses cycle 1 relied on are shown passing the same source (`isinstance(List)`
  is true, `len(elts) == 1 <= MAX_FLAT_VERTICES`), so the complaint can only come
  from the new starred clause.
- `test_a_second_receiver_spelling_is_caught` — M2's complaint fires, *and* the
  two older mechanisms are shown blind to it (`_draw_calls(...) == []`,
  `_draw_object_bindings(...) == []`, `_imagedraw_annotated_parameters(...) == []`).
- `test_an_annotated_draw_assignment_is_caught` — M3b caught twice (binding name
  and receiver), *and* shown to produce no `assignment`-form binding and no
  annotated *parameter*, which is why cycle 1's collector saw nothing.
- `test_an_unrecognised_draw_binding_form_is_caught` — attribute, tuple and loop
  targets each reported as their own unrecognised form.
- `test_the_one_honest_spelling_is_not_caught` — the package's own form passes, so
  the inverted default is a discrimination and not a ban.
- `test_a_vertex_list_passed_by_name_is_caught` — the bare-name and keyword-only
  forms, with the exact complaint text asserted.
- `test_a_many_sided_polygon_is_caught` and `test_a_disc_drawn_point_by_point_is_caught`
  were rewritten to fire **through** `_uncountable_vertices` instead of
  re-implementing the bound inline, so a control can no longer pass while the real
  check is broken.

**Mutants — every one its own fresh `pytest` process**, `export/png.py` restored
from a byte copy and `shasum -c`-verified after each (cycle 1 found that batching
from one parent yields false KILLED verdicts). Loop:
`tests/test_book_difficulty_dots.py tests/test_book_interior_type_floor.py
tests/test_cli.py` — **207 green** (was 198; +9 tests), and **548 green** with
`tests/test_suite_profile.py` added.

Cycle 2's survivors, now dead:

| mutant | verdict | killed by |
|---|---|---|
| M1 `draw.polygon([*points], fill=INK)`, 32-gon, canonical receiver | **KILLED** | `test_no_module_draws_a_round_mark_out_of_vertices` |
| M2 unannotated receiver `canvas`, 32 literal vertices, fed the real draw object | **KILLED** | `test_every_receiver_of_a_draw_method_is_a_draw_object` (+ the exemption test) |
| M3b `canvas: ImageDraw.ImageDraw = ImageDraw.Draw(image)` + a 9-gon | **KILLED** | the receiver test, the exemption test *and* `test_every_draw_object_in_the_package_is_spelled_draw` |

Three further evasions this agent invented against its own new mechanism, to
check it was not merely patched to the two the reviewer happened to try:

| mutant | verdict | killed by |
|---|---|---|
| M6 draw object returned from a helper, bound as `pen` | **KILLED** | receiver + binding-form rules |
| M7 `self.canvas = ImageDraw.Draw(image)`, 32-gon on `self.canvas` | **KILLED** | receiver + binding-form rules |
| V1 `draw.polygon(points)` — vertices by bare name | **KILLED** | `test_no_module_draws_a_round_mark_out_of_vertices` |

Cycle 1's controls re-run after the rewrite, so nothing was traded away: **C1**
`draw.bitmap` → KILLED, **C3** ten literal vertices → KILLED, **C4**
`draw.ellipse` → KILLED, **M3** plain `canvas = ImageDraw.Draw(image)` → KILLED.

**F-102 — the dingbat guard's limit list.** The computed-string route
(`chr()`, a decoded bytes literal, `unicodedata.lookup`) is now named in the
class docstring beside the vertex analogue, together with the non-`.py` assets the
walk never opens. Nothing about the mechanism changed, because nothing was wrong
with it: the test's sentence is about string *literals* and that is exactly what
`_dingbat_literals` reads. The fix commit's "closed package-wide" overshot by one
`chr()` call and is not repeated — the phrasing is now "every string literal in
the package, docstrings included", and D1 above is the mutant that holds that
wording honest.

**F-103 — the refusal pointer.** `export/layout.py`'s `__post_init__` docstring
named only `TestDifficultyDots_UntieredDrawsNothing` for all seven refusals; the
ring-closing stroke — the one AC-3 leans on — lives in
`TestDifficultyDots_FilledAndOutlinedAreDistinguishable::test_the_type_refuses_a_stroke_that_closes_the_ring`.
Both classes are named now. This is the cycle's only change to `src/`, and it is a
docstring: `export/layout.py`'s import surface is untouched (ADR-0007, the
COMP-007/COMP-009 split), and no page's geometry moved.

**F-104 — the relocated tautology, dropped.**
`assert getattr(book_pdf_generator, THE_DRAWING_SITE[1]) is _draw_difficulty_dots`
could only fail by `ImportError` at collection, and on the one input that could
break it (a typo in the literal) the `f"def {THE_DRAWING_SITE[1]}" in sources[...]`
line above it fails first. Removed, with the reason in a comment beside the line
that keeps all of its discriminating power. Cycle 1's T1 control is unaffected:
the typo still reds `test_the_walk_actually_sees_the_package` and
`test_the_package_draws_a_round_mark_in_exactly_one_function`.

**The out-of-scope note, resolved rather than implemented.** `TEXT_METHODS`'
docstring now says it is a **classification only, consulted by no guard** — the
dingbat rule ignores methods entirely and reads every string literal in the
package, so there is no method-scoped text guard to go looking for. The set stays
because `test_the_method_classification_covers_every_pillow_draw_method`'s
partition must be exhaustive. **No new guard was built to justify the set.**

**One further honest limit found while fixing, not papered over.**
`_imagedraw_annotated_parameters` asserts a *floor* of thirteen annotated draw
parameters rather than an equality: thirteen exist today, and a card that adds a
fourteenth is doing nothing wrong. The floor is there only so the rule cannot
pass by finding nothing.

**G-5 re-verified after the fix:** `grep -rn "_draw_difficulty_dots" src/` finds
the definition at `book_pdf_generator.py:1515` and no call. Every file changed is
in the card's own `Touches`; `tests/test_book_interior_type_floor.py` and
`src/nonogram/admin/book_pdf_generator.py` needed no change this cycle. Nothing
under `meta/` is committed.

### Orchestrator log

- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
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
- [Review 2/3] **score 8.5** (8.0 → 8.5, min_improvement 0.5 met). Severity gate **FAILS**: one new
- [Review 2/3] cycle 1's seven findings: **six CLOSED by execution**, one partially. F-002's four
- [Review 2/3] **the new Important (F-101): two of the four limits the widened guard states about
- [Review 2/3] bound on F-101 that keeps it Important rather than Critical, and the reviewer stated
- [Review 2/3] the dingbat rule came out **wider than I expected and its claim matches its
- [Review 2/3] the reviewer **re-derived the refusal of my own false premise independently**, rather
- [Review 2/3] OWED AT THE ARCHITECT STATION, new: the package-wide dingbat constraint is undeclared
- [Fix 2] **both steps landed** — `dc8d2df` (the floor: the two false limit sentences deleted, three Minors) then `56cec05` (the structural fix), in the order the brief required, so a true sentence was on disk at every point. Loop 207 green in the three-file set, 548 with test_suite_profile.py. Verified by me rather than accepted: **G-5 still holds** (zero callers in src/); the only `src/` change this cycle is a **docstring** hunk in export/layout.py (F-103's pointer correction — I read the diff line by line); `Touches:` respected; export/layout.py's import surface untouched.
- [Fix 2] the fix accepted RC-1 as named and **inverted the guard's default to deny**, which is the only shape that converges: `dir(ImageDraw.ImageDraw)` is a genuine authority for the *method* half, but no authority enumerates every way to write a vertex list or name a draw receiver, so adding spellings is the regress that burned CARD-238's cycles 1-4. Now an uncountable vertex argument, an unrecognised receiver and an unrecognised `.Draw(...)` binding each FAIL rather than pass, and honest existing sites became **earned exemptions under equalities** rather than widened bins — which is the move cycle 1's report recommended and this card twice refused.
- [Fix 2] the agent self-reported a limit it hit and backed out of, and I want it judged rather than accepted: `DRAW_OBJECT_UNBOUND_SITES` carries a **count** per module+form, not the enclosing function names, because writing the names out literally pulled this file into test_suite_profile.py's render-heavy set (one name matches meta/profiling's frozen RENDER_API_PATTERN) and restating that snapshot would mean committing under meta/, which the card may not do. Stated cost: the equality still catches additions but cannot notice a site *moving* between two functions of one module. Backing out of a change that would have forced a meta/ commit is the right instinct; whether the count is as strong as claimed is cycle 3's call.
- [Review 3/3] dispatched — **the last cycle before this card escalates**. The brief makes one thing the review and everything else secondary: *try to land a second dot glyph*. Cycle 1 found three evasions and cycle 2 found two more, and each time the previous cycle believed the route closed, so the only evidence that default-deny worked is a genuine adversarial attempt that fails. It was given a list of forms not yet tried (a draw object through a dict/list/attribute chain, a walrus or `as` rebinding, `functools.partial` or a stored bound method, itertools/numpy vertices splatted, a module `_package_sources()` does not reach, `from PIL.ImageDraw import Draw` aliased, a chained or subscripted `Draw` result) and told that finding one outranks everything else in the report. It was also told to check the limit split in BOTH directions — a 'named limit' that is actually closed is harmless, a 'true by mechanism' claim that is actually open is the family defect again — and to probe whether an exemption can absorb a newly-added drawing site. Closing instruction: choose explicitly between land it / land it with recorded bounds plus a follow-up card / escalate, and that I would rather have an honest escalate at cycle 3 than a generous pass that CARD-207 discovers on a printed proof.
- [Review 3/3] **score 8.0** — min_score 8 met, **severity gate FAILS**, and min_improvement missed
  (8.5 → 8.0 needed >= 9.0). The score did not fall because the code got worse; it did not. It fell
  because a deeper probe found the same number of landed glyphs as cycle 1 did.
- [Review 3/3] **three more complete second dot glyphs landed, each at 548 green, through a route
  family neither prior cycle named** — and the marks are genuinely round, measured outside the guard
  with standalone Pillow + numpy: the `draw.line` fan is 41x41 px, aspect 1.000, **1329 ink px against
  `draw.ellipse`'s 1313** at the same radius. Indistinguishable on a printed proof.
  * **L1** `draw.line` — a 240-ray fan for filled dots, a closed 33-point polyline for outlined ones.
  * **PT1** `draw.point` in a loop OUTSIDE the call, one 2-element display per call — so the vertex
    bound is per-call and says nothing about ink accumulated across calls.
  * **BM1** `stamp = draw.ellipse` then `stamp(circle, fill=INK)` — a stored bound method, written
    syntax, not the named `getattr` limit.
- [Review 3/3] **I verified the central claim myself before escalating, because it decides which
  options are even available.** `FLAT_METHODS`' stated reason for leaving `line` unguarded — "a
  straight line has no vertex list to hide a dot in" — is **factually false**: Pillow's own docstring
  reads "Draw a line, or a connected sequence of line segments" and it calls `draw_lines`;
  `joint="curve"` even rounds the joints. And the package already hands it computed lists at
  book_pdf_generator.py:1429 (`ends`) and :1441 (`list(side)`), plus png.py:186 and :217. The blind
  spot is even blessed by a control — `test_a_flat_shape_is_not_caught` pins
  `draw.line([(0,0),(1,1)])` as deliberately not-caught.
- [Review 3/3] what the cycle-2 fix DID hold, and it is real work: cycle 2's three survivors are
  genuinely dead (M1 starred 32-gon, M2 unannotated receiver, M3b annotated assignment — 1/2/3
  failures each, by exactly the tests the card names); both exemption sets **rejected every absorption
  probe** (a new `argument`-form `.Draw(...)` and a duplicate exempt `scaled.point` tuple were both
  caught); the composition claim holds (an aliased `Draw` bound to `pen` was killed); a brand-new
  module drawing `draw.ellipse` was killed; and both "named limits" really are open, so that split is
  honest. Guardrails G-1..G-5 all hold; system contract 4 of 4.
- [Review 3/3] where the wording still overshoots its mechanism: `_unrecognised_draw_receivers`
  claims to collect "every written call to a draw-method name whatever its receiver", but
  `_draw_method_calls` requires `isinstance(node.func, ast.Attribute)`, so `stamp(circle)` is
  collected by nothing. And route 3's "a circle built out of vertices is held to MAX_FLAT_VERTICES"
  is false, because PT1 is inside the guarded method set, on the canonical receiver, with every call
  in bounds.
- [Review 3/3] the self-reported count-vs-names trade: premise **verified independently** (the four
  unbound sites sit in `_blank_page`, `sample`, `pdf.py::_titled` and `pdf.py::render_pages`, and
  `render_pages` is matched by rank_durations.py:44's RENDER_API_PATTERN, applied to the *text* of
  every file under tests/), so the meta/ refusal was right. Two corrections: a third option existed
  and is cheap — keep the names and defeat a *textual* grep by splitting the literal — and the limit
  is slightly narrower than stated, since it also cannot see a site *replaced* by a different one in
  the same module+form.
- [Escalated] 2026-10-16T19:45Z — **max_cycles 3 reached with the severity gate still open, +
  min_improvement missed, + family regression for the third consecutive cycle** (cycle 2's Important
  was attributed to cycle 1's fix; cycle 3's are attributed to cycle 2's — receiver → binding form →
  call shape and cross-call ink, one syntactic level down each time). · station: **architect/owner**
  · route: the owner picks the instrument, then funds ONE cycle against it — see the three options in
  the escalation note below. Worktree and branch KEPT at `b3ba400`..`56cec05`.
- [Escalated] why this is NOT the CARD-238/CARD-239 ending, which was my first instinct: that ending
  is for a mechanism that **converged** with honestly-named residue. Writing these three into the
  limits list instead of fixing them would record bounds that **swallow the AC** — "no second round
  mark, except via draw.line, except via a loop of draw.point, except via a stored bound method" is
  not a promise CARD-207/229/231/233 can build on, and those four cards are the entire reason this
  card was cut first.

### AC-4 narrowing pass (agent, 2026-10-16) — the amendment's six items

One bounded pass under GB-1..GB-4. **No guard mechanism was added or weakened**: the three
default-deny mechanisms and both exemption equalities are byte-identical to `56cec05`, `src/` is
untouched (`git status --short src/` clean, verified after every mutant), and G-5 still holds —
`grep -rn '_draw_difficulty_dots' src/` returns the definition at `book_pdf_generator.py:1515` and
nothing else. Only `tests/test_book_difficulty_dots.py` changed. Loop green throughout:
`pytest tests/test_book_difficulty_dots.py tests/test_book_interior_type_floor.py tests/test_cli.py
tests/test_suite_profile.py` → **548 passed**, the same count as at `56cec05` (this pass adds no
test; it corrects claims and adds six demonstrated limits).

**The final limit split — this pass's whole deliverable.**

*True by mechanism* (unchanged in substance; one of the three had its stated reach corrected):

1. **An uncountable vertex argument fails.** A bare name, a call, a comprehension, a conditional, a
   keyword-only `xy=`, a display holding a starred unpack — all complaints, each with its own
   control. Unchanged.
2. **An unrecognised draw *receiver* fails** — but only for a call *written as an attribute*. The
   docstrings said "every written call to a draw-method name whatever its receiver"; that was wider
   than `_draw_method_calls`, which requires `isinstance(node.func, ast.Attribute)`. Corrected in
   three places (`_draw_method_calls`, `_unrecognised_draw_receivers`, the class docstring's limit
   #2): the attribute form is now stated as a **precondition**, and the route it overstated is named
   limit 6 below.
3. **An unrecognised `.Draw(...)` binding form fails.** Unchanged.

*Named limits* — six now, each with the mutant that demonstrates it is open. Every mutant is a
complete second three-dot glyph planted in `src/nonogram/export/png.py` (PA1 excepted: it takes the
`Image`, not the draw object), each run in **its own fresh `pytest` process** over the four-file
loop, each file restored from a byte copy and `shasum`-verified afterwards (`png.py`
`b43169cc…`, `pdf.py` `d332130b…`). Verdicts observed in this pass:

| # | Limit | Mutant | Verdict |
|---|---|---|---|
| 1 | Anything outside `ImageDraw` entirely | **PA1** — each dot an `Image.new("L")` mask filled by `putdata` from `x²+y²≤r²` and composited with `Image.paste`; no draw object, no `ImageDraw` call | **SURVIVED**, 548 passed |
| 2 | A dynamically dispatched draw call | **G1** — `method = getattr(draw, "ellipse")`, then `method(circle, fill=INK)` | **SURVIVED**, 548 passed |
| 3 | A round mark *computed* into a string | **D1** — `draw.text` handed `chr(0x25CF) * rank + chr(0x25CB) * (3 - rank)` | **SURVIVED**, 548 passed |
| 4 | A **polyline** (`draw.line`, unbounded) | **L1** — each filled dot a 240-segment radial fan, each outlined dot one closed 33-point polyline | **SURVIVED**, 548 passed |
| 5 | Ink **accumulated across calls** (the vertex bound is per *call*) | **PT1** — the glyph stamped pixel by pixel by a nested `for` loop of `draw.point((x, y))`, every call a 2-element display inside `MAX_FLAT_VERTICES` | **SURVIVED**, 548 passed |
| 6 | A draw method held in a **local**, called as a bare name | **BM1** — `stamp = draw.ellipse`; `stamp(circle, fill=INK)` / `stamp(circle, outline=INK, width=2)` — `ELLIPSE_METHODS` on the canonical receiver | **SURVIVED**, 548 passed |

Limits 1–3 were already named but carried no demonstration in the file; GB-3 says a limit without one
is the same defect in a new costume, so PA1/G1/D1 were run here too rather than cited from the
cycle-3 YAML. Limits 4–6 are cycle 3's three survivors (F-201/F-202/F-203), now written down in the
same style. **All six point at CARD-241** — render a page, find the ink, measure it for roundness —
which is named in the class docstring, on `FLAT_METHODS`, on `_draw_method_calls`, on
`_unrecognised_draw_receivers` and on the flat-shape control, so a reader of this guard learns where
the universal guarantee lives from whichever end they arrive.

**Roundness measured independently of the guard**, with a standalone Pillow script that imports no
`nonogram` module (`.venv/bin/python -I`, so the main repo's `src/` cannot be picked up):
`draw.ellipse` at r=20 is 41x41 px, aspect 1.000, 1313 ink px. L1's fan: 41x41, aspect 1.000, 1272
px (0.969 of the ellipse). L1's ring: a 43x41 annulus, 207 px. PT1's disc: 41x41, aspect 1.000, 1257
px (0.957). On a printed page these are the same mark. (Cycle 3 reported 1329 px and a 43x43 ring for
its own variants; my figures are from my own runs and are what the file now quotes.)

**`FLAT_METHODS`' false rationale for `line` — corrected (item 5).** It claimed a straight line "ha[s]
no vertex list … to hide a dot in". Verified false, independently of the review: Pillow's own
docstring reads *"Draw a line, or a connected sequence of line segments"*, `ImageDraw.line` hands its
`xy` straight to `draw_lines`, and `joint="curve"` rounds the joints with `pieslice`. The comment now
says `line` is **unguarded and why that is a known hole**, with the four uncountable lists the package
already hands it (`draw.line(ends, …)` at `book_pdf_generator.py:1429` and `export/png.py:186`,
`draw.line(list(side), …)` at `book_pdf_generator.py:1441`, `draw.line(list(ends), …)` at
`export/png.py:217` — all four re-grepped here), which is why a bound would buy an exemption table
rather than a closed route. `test_a_flat_shape_is_not_caught` keeps `draw.line([(0,0),(1,1)])` as a
deliberate not-caught control, and its docstring now says the call is not caught **because the walk
does not watch `line` at all** — explicitly not because a line cannot be round.

**`DRAW_OBJECT_UNBOUND_SITES` (item 6, both Minors).** The function names are **back**, by splitting
the one literal that a *textual* grep would match (`"render" + "_pages"`, with the reason in the
comment above it) — cycle 3's third option. The table is now `(module, enclosing function, form)`:
`_blank_page`/argument, `sample`/receiver, `pdf.py::_titled`/argument, `pdf.py::render_pages`/argument
— each re-derived here with an independent `ast` walk and confirmed unbound by reading the four lines.
The file still contains **zero** matches for `meta/profiling`'s render-API pattern, so
`test_suite_profile.py`'s frozen render set is untouched and no `meta/` snapshot had to be restated.
The equality is strictly stronger than the count it replaces, demonstrated rather than asserted:
*mutant R1* — the `_titled` site moved into a new helper in the same module, same `argument` form, so
the per-module+form count is unchanged — was **KILLED** (1 failed / 547 passed,
`test_every_draw_object_in_the_package_is_spelled_draw`), where the old count would have passed. With
the names back there is no "moved or replaced within one module+form" limit left to widen: the
amendment's wording for it would now be *false*, so the comment states the strengthening instead.
`from collections import Counter` became unused and was dropped.

**One amendment item not done, and why.** Nothing else. F-205 (a bare `Draw(image)` from an aliased
import is classified as nothing) is left open and carried to CARD-241: its one-clause fix changes a
guard's classification rule, which GB-1 assigns to CARD-241, and the finding itself records that the
exposure is F-201's — composition already kills the aliased-import route on its own (cycle 3's mutant
A1). Cycle-3 statuses set in `meta/review/20261016T193822Z-CARD-228-cycle3.yml` (uncommitted, as is
this card): F-204 and F-206 `fixed`; F-201, F-202, F-203 and F-205 `deferred`, each with the reason
and CARD-241 named.

### Orchestrator log

- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
- [Cut first, deliberately] Four cards in this set draw difficulty dots. Cutting the glyph as
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
- [Review 2/3] **score 8.5** (8.0 → 8.5, min_improvement 0.5 met). Severity gate **FAILS**: one new
- [Review 2/3] cycle 1's seven findings: **six CLOSED by execution**, one partially. F-002's four
- [Review 2/3] **the new Important (F-101): two of the four limits the widened guard states about
- [Review 2/3] bound on F-101 that keeps it Important rather than Critical, and the reviewer stated
- [Review 2/3] the dingbat rule came out **wider than I expected and its claim matches its
- [Review 2/3] the reviewer **re-derived the refusal of my own false premise independently**, rather
- [Review 2/3] OWED AT THE ARCHITECT STATION, new: the package-wide dingbat constraint is undeclared
- [Fix 2] **both steps landed** — `dc8d2df` (the floor: the two false limit sentences deleted, three Minors) then `56cec05` (the structural fix), in the order the brief required, so a true sentence was on disk at every point. Loop 207 green in the three-file set, 548 with test_suite_profile.py. Verified by me rather than accepted: **G-5 still holds** (zero callers in src/); the only `src/` change this cycle is a **docstring** hunk in export/layout.py (F-103's pointer correction — I read the diff line by line); `Touches:` respected; export/layout.py's import surface untouched.
- [Fix 2] the fix accepted RC-1 as named and **inverted the guard's default to deny**, which is the only shape that converges: `dir(ImageDraw.ImageDraw)` is a genuine authority for the *method* half, but no authority enumerates every way to write a vertex list or name a draw receiver, so adding spellings is the regress that burned CARD-238's cycles 1-4. Now an uncountable vertex argument, an unrecognised receiver and an unrecognised `.Draw(...)` binding each FAIL rather than pass, and honest existing sites became **earned exemptions under equalities** rather than widened bins — which is the move cycle 1's report recommended and this card twice refused.
- [Fix 2] the agent self-reported a limit it hit and backed out of, and I want it judged rather than accepted: `DRAW_OBJECT_UNBOUND_SITES` carries a **count** per module+form, not the enclosing function names, because writing the names out literally pulled this file into test_suite_profile.py's render-heavy set (one name matches meta/profiling's frozen RENDER_API_PATTERN) and restating that snapshot would mean committing under meta/, which the card may not do. Stated cost: the equality still catches additions but cannot notice a site *moving* between two functions of one module. Backing out of a change that would have forced a meta/ commit is the right instinct; whether the count is as strong as claimed is cycle 3's call.
- [Review 3/3] dispatched — **the last cycle before this card escalates**. The brief makes one thing the review and everything else secondary: *try to land a second dot glyph*. Cycle 1 found three evasions and cycle 2 found two more, and each time the previous cycle believed the route closed, so the only evidence that default-deny worked is a genuine adversarial attempt that fails. It was given a list of forms not yet tried (a draw object through a dict/list/attribute chain, a walrus or `as` rebinding, `functools.partial` or a stored bound method, itertools/numpy vertices splatted, a module `_package_sources()` does not reach, `from PIL.ImageDraw import Draw` aliased, a chained or subscripted `Draw` result) and told that finding one outranks everything else in the report. It was also told to check the limit split in BOTH directions — a 'named limit' that is actually closed is harmless, a 'true by mechanism' claim that is actually open is the family defect again — and to probe whether an exemption can absorb a newly-added drawing site. Closing instruction: choose explicitly between land it / land it with recorded bounds plus a follow-up card / escalate, and that I would rather have an honest escalate at cycle 3 than a generous pass that CARD-207 discovers on a printed proof.
- [Review 3/3] **score 8.0** — min_score 8 met, **severity gate FAILS**, and min_improvement missed
- [Review 3/3] **three more complete second dot glyphs landed, each at 548 green, through a route
- [Review 3/3] **I verified the central claim myself before escalating, because it decides which
- [Review 3/3] what the cycle-2 fix DID hold, and it is real work: cycle 2's three survivors are
- [Review 3/3] where the wording still overshoots its mechanism: `_unrecognised_draw_receivers`
- [Review 3/3] the self-reported count-vs-names trade: premise **verified independently** (the four
- [Escalated] 2026-10-16T19:45Z — **max_cycles 3 reached with the severity gate still open, +
- [Escalated] why this is NOT the CARD-238/CARD-239 ending, which was my first instinct: that ending
- [Fix 2, the AC-4 narrowing pass] `5859bbb`, ONE file (tests/test_book_difficulty_dots.py, +199/-48), 548 passed — the same count as `56cec05`, because the pass adds no test. All six amendment items done. Verified at this station: **GB-4 holds** (`git diff 56cec05..HEAD --stat` touches only that test file — zero `src/` change); **G-5 holds** (zero callers); and item 6's names-back change did NOT pull the file into meta/profiling's frozen render set — I ran the pattern against it myself (**0 matches**) and `tests/test_suite_profile.py` passes.
- [Fix 2] **the final limit split, which is this pass's whole deliverable.** TRUE BY MECHANISM (3): an uncountable vertex argument fails; an unrecognised draw receiver fails **for a call written as an attribute** (the old wording claimed 'whatever its receiver', which was wider than `_draw_method_calls`' `ast.Attribute` precondition — corrected in all three places); an unrecognised `.Draw(...)` binding form fails. NAMED LIMITS (6), **each with a mutant the agent ran in its own fresh process and observed SURVIVE**: outside ImageDraw entirely via an Image.paste mask; dynamic dispatch via getattr; a round mark computed into a string via chr(); `draw.line` polylines; ink accumulated across calls; a draw method held in a local. All six name CARD-241 as the card that closes them, from five entry points.
- [Fix 2] it re-ran the three limits that were ALREADY named but carried no demonstration in the file, rather than citing cycle 3's YAML — because GB-3 makes an undemonstrated named limit the same defect in a new costume. That is the right reading of the guardrail and it was not the cheap path.
- [Fix 2] it also corrected cycle 3's figures with its own standalone measurement (run with `-I` and importing no `nonogram`) and quotes **its own**: `draw.ellipse` r=20 is 41x41, aspect 1.000, 1313 ink px; the `draw.line` fan 1272 px (0.969); the `draw.point` disc 1257 px (0.957). Cycle 3 had reported 1329 px and a 43x43 ring. And it corrected MY card's shorthand: png.py:217 is `list(ends)`, not `list(side)`.
- [Fix 2] **one deliberate divergence from the amendment's literal wording, and the agent is right.** Item 6 asked for two things — put the function names back, AND widen the limit's wording to 'moved or replaced within one module+form'. It did the first and refused the second, because with the names back there IS no moved-or-replaced limit left, so writing that sentence would be **false** — the exact defect family this pass exists to remove. The amendment's two halves are mutually exclusive once the first is done, which I did not see when I wrote it. It stated the strengthening in a comment instead, and **demonstrated** rather than asserted it: mutant R1 moves the `_titled` site into a new helper in the same module and same form, so a per-module+form count would be unchanged — KILLED, where the old count would have passed.
- [Fix 2] F-205 (a bare `Draw(image)` from an aliased import classifies as nothing) carried to CARD-241 rather than fixed, correctly: its one-clause fix changes a guard's classification rule, which GB-1 assigns to CARD-241. And the cycle-3 statuses use **`deferred`, not `dismissed`** — a distinction that matters, because `dismissed` findings feed the cross-project `review_false_positives` signal and these are not false positives.
- [AC/EC/G gate] dispatched. Briefed that **AC-4 now has two halves and the second is as binding as the first** — the four routes guarded, AND the unguarded routes named with a demonstration each — and that limits 4, 5 and 6 must be verified first-hand, since those are the three cycle 3 found. Also asked to judge the item-6 divergence explicitly, with the instruction that a fix agent declining a literal instruction because following it would write a false claim is the behaviour this card's history has been trying to produce and must not be scored as non-compliance.
- [AC/EC/G gate] **PASS — every item demonstrated**: AC-1..AC-6 (AC-4 in its amended form, both
  halves), G-1..G-5, GB-1..GB-4, and all four System contract rules. **17 mutants**, each in its own
  fresh process, every mutated file restored from a byte copy and shasum-verified, tree clean after.
  Three results worth keeping:
  * **AC-4's first half holds under five probes**, not just the obvious one: a second `draw.ellipse`
    glyph, the same glyph on an unannotated receiver, a list-element `.Draw(...)` binding form, a
    `"●●○"` literal into `draw.text`, and — the interesting one — **A1, F-205's own route**: an
    aliased `from PIL.ImageDraw import Draw` with `pen = Draw(image)`. A1 was KILLED by the receiver
    rule, which **proves the composition claim** the pass leans on to defer F-205 to CARD-241. That
    deferral is therefore evidenced rather than hopeful.
  * **AC-4's second half holds too, and in the honest direction**: all six named limits were re-run
    by the gate and all six SURVIVED. None was closed-and-mis-named, and none lacked a working
    demonstration. The gate also re-measured roundness independently (standalone Pillow, `-I`, no
    `nonogram` import) and **every figure matches the file's quoted numbers exactly**.
  * **GB-1 verified structurally rather than by reading**: an AST comparison with docstrings
    stripped, `56cec05` vs HEAD, found **exactly two** code-level changes — the
    `DRAW_OBJECT_UNBOUND_SITES` data and one assertion. No guard function added or altered, so "no
    new mechanism" is a measured fact, not a promise.
- [AC/EC/G gate] it judged the item-6 divergence as asked and **sided with the fix agent**, having
  run the mutant itself: R1 (the `_titled` site moved into a new helper of the same module and form)
  is KILLED where the per-module count it replaced would have passed, and the failure message proves
  it — the sorted lists differ only in the function name while `pdf.py` still holds two `argument`
  sites. Its verdict: declining the literal instruction to avoid asserting a limit that no longer
  exists is the better of the two readings and must not be scored as non-compliance.
- [Fix, gate notes] the gate raised two Minor wording notes and **one of them was a false claim this
  pass itself introduced** — so I fixed both before the merge gate rather than carrying them, on the
  grounds that merging a known-false sentence into the file whose subject is claims exceeding
  mechanisms would be the wrong note to end on. `fb50a40` (rebased `1702b55`), loop still 548:
  * The names-back comment claimed the equality catches a site "moved **or replaced** in the same
    module and form". The gate's **mutant R2 SURVIVED**: an unbound site replaced by a different one
    *inside the same function* leaves the triple unchanged. The comment now claims only what R1
    proved, and states the residue with the reason it is not an open route.
  * Mechanism 3's precondition was unstated — `_draw_object_bindings` reads **attribute-form**
    `.Draw(...)` only. Its sibling got exactly this correction under item 3; the amendment named only
    two sentences, so this one was inside the letter of the pass and outside its list.
- [Merge gate] rebased cleanly onto main `09748b4`; 7 commits, 4 files. Running ALONE on a quiet
  machine. ⚠ **My own slip, recorded:** clearing the worktree's synced review reports before the
  rebase I used `rm -f meta/review/*.yml`, which globbed the whole **tracked** 251-file review
  history rather than this card's three. `git checkout -- .` restored it before the rebase and both
  trees verified at 251 files and clean — but the right command was a targeted pathspec, and the
  only reason this was free is that the files were tracked.
