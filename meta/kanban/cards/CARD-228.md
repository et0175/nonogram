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
   drift from `TIERS`. `DifficultyDots.__post_init__` refuses a row that cannot say
   what it means — an empty row, a rank of zero, dots of unequal size, dots that
   overlap, and a stroke of half the diameter or more (which would close the ring and
   make an outlined dot identical to a filled one). AC-3 and AC-6's "not three outlined
   dots" are therefore partly *structural*: those values are unconstructible.

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
  a packed solution tile's own band at the 10 cm minimum trim, four answers to a page
  (313 x 141 px, the narrowest header any caller will hand the glyph). Asserts the glyph
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
`admin/grid_renderer.py`. **All ten were caught.**

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
ends up drawing from, a second dot is a failing test on their branch rather than a
discovery on a printed proof. (All four callers' own `Touches` name only
`admin/book_pdf_generator.py`, so the one site is reachable from each of them —
`export/pdf.py`'s `_draw_header` is the single-puzzle CLI/web path CON-019 freezes, and
no caller needs to draw from there.)

### Orchestrator log

- [Env] forge unknown (no .claude-plugin/plugin.json resolvable; no meta/.skills.yml, so no forge.min_version to compare against — no models: block either, so agents inherit the session model)
- [Scope] src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, tests/test_book_difficulty_dots.py, tests/test_book_interior_type_floor.py — exactly the card's Touches:, no drift, no SCOPE+. Components touched are COMP-007 and COMP-009, exactly the card's slice, so the scope gate sees no growth. Noted for the retrospective rather than as a finding: 1579 insertions on a 0.5d card, 1144 of them one new test file — volume in the tests, not scope in the source.
- [Guard] G-5 verified mechanically in the main repo, not taken on the agent's word: `grep -rn` over src/ shows `_draw_difficulty_dots` has no caller anywhere, so no existing page gains or loses ink. The four adopting cards (CARD-207/229/231/233) are what wire it.
- [Build gate] cycle gate is the full suite (review.test_scope: full). Queued behind CARD-213's run on meta/kanban/.full-suite.lock — the agent's own `pytest tests/ --ignore=tests/e2e -x` is not the gate.
- [Build gate] cycle 1: **7557 passed, 9 skipped, exit 0 in 877.93s** — full suite in the worktree,
  under the repo lock. Clean first attempt. Worth recording: 9 skips, the same number CARD-228's
  sibling gate showed, where CARD-234's gate saw 11 and CARD-235's 9 on identical code. That spread
  was the host-state coupling CARD-238 removed, so a stable 9 across two unrelated gates in one wave
  is the first positive evidence that CARD-238's fix holds.
- [Review 1/3] spawned. Briefed NOT to run the full suite (I already have its result, and CARD-213's
  re-gate is using the machine) and to scope mutation runs to the card's own test files plus
  tests/test_cli.py: review.test_scope is `full` here, so an unscoped Step 8f would cost 878s PER
  MUTANT. The reviewer was told to verify the agent's 11 claimed mutants rather than inherit them,
  and pointed at the four coverage-claim shapes this card turns on — AC-4's ast guard and its Pillow
  partition, AC-2's TIERS controls, G-2's no-draw.text discharge, and the __post_init__ "unconstructible
  rather than untested" claim. AC-4's forward-compatible reading was named as the single most
  important call in the review.
- [Review 1/3] **score 8.0**, risk LOW, 7 findings, 0 critical, 2 important. Meets min_score 8, so
  the SCORE gate passes and the SEVERITY gate does not — cycle 2 is for the two Importants plus three
  cheap Minors of the same family. Report synced to meta/review/20261016T181040Z-CARD-228-cycle1.yml.
  The reviewer ran **14 mutants of its own, none reused from the agent's list: 9 killed, 5 survived.**
- [Review 1/3] **AC-4's reinterpretation is ACCEPTED** by the reviewer, and on the stronger of the two
  available grounds: the card's literal wording is unsatisfiable while G-4/G-5 forbid building the four
  adopting cards, and "the package holds exactly one function putting a round mark on a page" binds
  those cards *prospectively* rather than asserting something about code that does not exist. The `ast`
  walk is the right instrument and its six controls genuinely discriminate.
- [Review 1/3] F-001, the finding that matters, and I confirmed its premise myself before acting on it:
  the partition is exhaustive against Pillow's API but **nothing checks the bins are right**, and three
  of them are wrong. `FLAT_METHODS` holds `point`, `polygon`, `text` and `bitmap`; `ROUND_ENOUGH` holds
  `regular_polygon`, which is strictly *less* general than the `polygon` in FLAT, and whose own
  docstring names "a 24-gon" as the route it exists to cover — the partition contradicts its own stated
  rationale. Three planted second dot-glyphs in export/png.py SURVIVED (`draw.text("●●○")`,
  a 32-gon `polygon`, a `point` disc); only the `ellipse` control was killed. The `text` route is not
  academic: I verified `draw.text` is called in four package modules including book_pdf_generator.py,
  the file all four adopting cards name in their Touches, and CARD-207's header already goes through
  `_set_band`'s draw.text — so appending "●●○" to the band string is the cheapest way for it to ship
  dots, bypassing the very guarantee this card exists to create, with CON-020's 10 pt floor passing a
  14 pt bullet happily.
- [Review 1/3] F-002: four of the five `__post_init__` refusals survive being disabled with 186 tests
  green. Partly good news though — the two refusals AC-3 and AC-6 actually lean on ARE pinned, so the
  card's "unconstructible rather than merely untested" claim **holds for AC-3 and AC-6**; only the
  broader notes sentence overreaches. And the refusals cannot be bypassed by the one caller.
- [Review 1/3] what the review CONFIRMED rather than merely passed: the COMP-007/COMP-009 split is real,
  not nominal (`export/layout.py` imports nothing from `nonogram` at all, so no tier ordering can reach
  it); the second independent source of tier order is non-tautological (TIER_BANDS floors 0.0/33.0/90.0
  are distinct, so it is not passing on sort stability) and there is even a third (enum declaration
  order); all four unnamed invariants genuinely hold, with the row-not-flush one verified analytically —
  worst observed clearance 0.2105 of a dot against an asserted 0.20, tight at odd diameters; the corpus
  floors are load-bearing (1944 of 2100 produce a glyph against CORPUS_MIN_GLYPHS 1800); system contract
  4 rules checked, 4 hold, 0 dead `check:` refs; G-1/G-2/G-3/G-5 all hold.
- [Review 1/3] **METHODOLOGY FINDING, and it reaches past this card — feed it to the retrospective.**
  Running several mutants sequentially from ONE parent process produced **false KILLED verdicts**: 11-12
  bogus failures in tests the mutant could not possibly affect (a `book_pdf_generator` fill= change
  failing a pure-layout.py corpus sweep). One mutant per process is reliable; batching is not. The
  reviewer's warning, which I am recording verbatim because of what it implies: *anything in this
  project's card records of the form "all N mutants caught" from a batched run is worth re-deriving.*
  That potentially touches every mutation claim this board has accepted as evidence — including
  CARD-234's "6 mutants each red by name" and this card's own "all ten caught". It is the same defect
  family the wave has been fighting, found this time in the REVIEW station's instrument rather than in
  a card's tests.
- [Fix 2] dispatched. On F-001 I chose to do all three remedies rather than pick one: widen where free
  (polygon/point/bitmap into ROUND_ENOUGH — already asserted called-nowhere, so it costs nothing),
  close the `text` route with a dingbat-codepoint assertion plus a control that fires, AND narrow the
  three over-claiming sentences to what an ast walk over `dir(ImageDraw.ImageDraw)` can measure, naming
  the routes outside it (Image.paste of a mask, floodfill, a pre-rendered asset) as the limit they are.
  Closing the text route has real forward value, which is the whole reason this card was cut first.
  The fix agent was also told, with the reasons, to run every mutant in a fresh process.
