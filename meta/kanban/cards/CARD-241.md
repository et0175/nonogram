# CARD-241: One round mark on the page, proved by rendering it rather than by reading the source

**Status:** done
**Priority:** P1
**Category:** enabler
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/241-round-mark-render-proof
**Worktree:** ../PythonProject4-card-241
**Source:** CARD-228's escalation, 2026-10-16 — owner decision at the architect station, option (b) of three. Every figure in this card was measured during CARD-228's three review cycles; nothing here needs re-deriving.
**Idea:** —
**Wave:** 43
**Depends on:** CARD-228 (it owns the glyph and the four-route static guard this card supersedes as the universal check)
**Touches:** tests/test_book_difficulty_dots.py, tests/helpers/ (a new roundness helper), meta/architecture/decisions/ (ADR-0036 delta, if the owner takes the declaration here)
**Review score:** 9.0 (cycle 2/3)
**Started:** 2026-10-17T05:05:12Z
**Closed:** 2026-10-17T09:53:22Z
**Actual:** 0.6d
**Merge commit:** 099864b
**Blocked by:** —

## What to implement

CARD-228 cut one function that draws a tier as three dots, and four later cards
(CARD-207/229/231/233) are supposed to reuse it rather than each inventing their own. The
guarantee that they *must* reuse it was attempted as a static `ast` walk over `src/nonogram/**`.
**Three review cycles proved that instrument cannot hold it.** This card replaces the instrument.

### Why the static walk failed, stated once so it is not re-attempted

The walk discriminates by **syntactic form**, and **no authority enumerates the forms.**
`dir(ImageDraw.ImageDraw)` is a genuine authority for *which methods* can draw — that half is sound
and must be kept — but Python's grammar offers nothing importable that lists every way to write a
vertex list or name a receiver. So each cycle closed the named routes and the next cycle found a new
family one level down:

| cycle | glyphs landed | the family |
|---|---|---|
| 1 | 3 | `draw.text` with bullets, a 32-gon `polygon`, a `point` disc |
| 2 | 2 | a **starred** vertex literal, an **annotated** draw receiver |
| 3 | 3 | **`draw.line`** polylines, ink **accumulated across calls**, a **stored bound method** |

Cycle 2's default-deny inversion was the right move and is kept — it closed receivers and binding
forms for good — but it moves the frontier rather than closing it.

### The instrument this card uses instead

**Render a page, find the ink, test it for roundness.** Blind to spelling altogether, and it is what
CARD-207's printed proof does anyway.

1. A helper that takes a rendered page and returns its connected ink regions with, per region, the
   measurements that distinguish a disc from everything else. CARD-228's cycle-3 review established
   the metric works and is cheap — a few lines of NumPy, on the dependency baseline already
   (stdlib + Pillow + NumPy, ADR-0006/R1, **no new dependency**).
2. The measurements to use, all taken during CARD-228's cycles: `draw.ellipse` at a given radius
   inks **1313 px**; the `draw.line` 240-ray fan that evaded the static guard inks **1329 px** at
   **41×41 px, aspect 1.000**; the `draw.point` loop disc inks **1257 px**. A metric that cannot
   separate those three from each other is the *right* answer — they are all discs, and all three
   must be **caught**, which is the point. What the metric must separate is a disc from the
   package's legitimate marks: rules, frames, glyph text, the proof sheet's arrow head.
3. The guard: render the pages the book actually produces, and assert that every round region on
   them is accounted for by the one drawing site. A round mark nobody declared is a failure.

### What must NOT be thrown away

CARD-228's static guard **stays**. It is fast, it runs on every commit, and it catches the four
routes it does see before a render is even attempted. This card adds the universal check; it does
not delete the cheap one. Keep its "true by mechanism" / "named limits" split, and strike from its
limits list exactly those routes this card's render check now closes — **the equality must go red
if a limit is struck without being closed, and that is the card's own self-test.**

## Acceptance criteria

- **AC-1** (happy, the three known evasions die): *Given* CARD-228's three cycle-3 survivors —
  `draw.line` as a ray fan, a loop of in-bound `draw.point` calls, a stored bound method — *then*
  each is caught by the render check, demonstrated by planting and reverting each one.
  (test: `TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee`)
- **AC-2** (guard, legitimate marks are not caught): *Given* the pages the book really produces,
  *then* the check passes on every one of them unmutated — rules, frames, the proof sheet's arrow
  head and all glyph text included. Paired with AC-1, so the check is shown to discriminate rather
  than merely to fire. (test: `TestRoundMarkOnThePage_PassesOnTheRealBook`)
- **AC-3** (guard, blind to spelling): *Given* one dot glyph written four different ways —
  `ellipse`, a `line` fan, a `point` loop, a `polygon` — *then* the check's verdict is the same for
  all four, because it reads ink and not syntax.
  (test: `TestRoundMarkOnThePage_SameVerdictForEverySpelling`)
- **AC-4** (edge, the metric's own boundary): *Given* a mark that is **nearly** round (a hexagon, a
  rounded rectangle at a small corner radius) *then* the check's verdict is **stated and tested**
  at that boundary rather than left to chance, and the threshold is justified by a measurement, not
  chosen. (test: `TestRoundMarkOnThePage_TheBoundaryIsMeasured`)
- **AC-5** (guard, the static guard's limits list shrinks honestly): *Given* CARD-228's named-limits
  list, *then* exactly those routes this card closes are struck from it, and the list's equality
  goes **red** if a route is struck without being closed or closed without being struck.
  (test: CARD-228's own limits equality, extended)
- **AC-6** (edge, cost): *Given* the render check, *then* its wall-clock cost is **measured and
  recorded**, and if it is too slow for every commit it is marked so that it runs where the project
  already pays for rendering — stated explicitly, not discovered at a merge gate.
  (test: a recorded measurement, in the card and in `meta/profiling/`)

## Guardrails

- G-1: **do not delete CARD-228's static guard.** It is the cheap first line. This card supersedes
  it only as the *universal* check.
- G-2: no new runtime dependency (ADR-0006/R1). NumPy and Pillow are already in the baseline; the
  helper belongs under `tests/helpers/`, which is where this project puts independent second
  implementations.
- G-3: **no `hypothesis`.** Seeded stdlib corpora with an asserted minimum case count, per CLAUDE.md.
- G-4: do not change the glyph. `difficulty_dots`, `_draw_difficulty_dots` and their geometry are
  CARD-228's and are done; this card only measures what they draw.
- G-5: do not re-measure or regenerate `meta/profiling`'s frozen artefacts. If this card's new test
  file would enter `test_suite_profile.py`'s render-heavy set, **say so and handle it deliberately**
  — CARD-228's fix cycle hit exactly that and backed out rather than commit under `meta/`; the
  third option it missed was splitting the matched literal, and it is recorded here so this card
  does not rediscover it.
- G-6: every claim this card makes about what the check catches carries a control that can fail —
  the standing rule from CARD-238, and the one CARD-228's three cycles kept testing.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static assets (fonts and similar data files) may ship as package d… (check: `TestDependencyBaseline_IsExactlyPillowAndNumpy`)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass sil… (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose co… (check: `test_the_control_for_each_spelling_depends_on_the_set`)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysab… (check: `test_the_guard_sets_are_derived_and_not_hand_written`)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and… (check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: `PropertyTest_Solver_NeverFalsePositiveUniqueness`)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system… (check: `TestWebServer_BindsLoopbackOnlyByDefault`)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request tar… (check: `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the… (check: `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory… (check: `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore`)

## Architecture context

- **FR:** FR-033, FR-043.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2, ADR-0006/R1. ⚑ **An ADR delta may be owed here:** CARD-228 introduced a
  package-wide constraint — no string literal anywhere in `src/nonogram/` may hold a codepoint in
  U+25A0–U+25FF, U+2022 or U+2219, docstrings included — which is currently declared *only* inside
  a test file. It binds every module and its single exemption cannot absorb a drawing module. The
  owner may want it in ADR-0036 instead; decide that here, since this card owns the same subject.
- **Components:** COMP-007, COMP-009.
- **Trace:** to be updated if the ADR delta is taken.

## Failure matrix

| boundary | what can fail | how this card handles it |
|---|---|---|
| materialising a whole interior at once (`interior_pages`) — the only resource boundary the instrument crosses | peak memory: 13 pages for the baseline book, **measured at ~31–35 MB each, +398..455 MB** over the process before the call (CARD-145's own note quotes ~25 MB a page and calls this list "the shape the deployed panel was OOM-killed by"); the measurement that follows adds +38..92 MB on top | bounded by construction, not by a retry: the guard renders the **baseline** book (13 pages, fixed) and a **9-puzzle** seeded book (20 pages, measured), never the 150-puzzle corpus — and one interior at a time, so the peak is one interior's and not twelve. A `MemoryError` here is a test failure to be read as one, not caught. Measured peak for the whole new class: see AC-6 below. |
| nothing else | — | the measurement itself is a pure function of a page's pixels: no disk, no clock, no network, no concurrency, no retries, and no cache of its own. The three `lru_cache`s the render path carries (`_band_font_bytes`, `_band_font`, `default_toc_frame`) are pure functions of their arguments and are identical in both halves of every plant/revert pair, so no cache has to be cleared between halves (CARD-221's trap does not apply: this harness adds ink, it does not simulate a different environment — and the empty-plant control in the same process proves no page is cached). |

## Worktree notes

- [Why architectural, and why TDD] It replaces a verification instrument that four cards depend on,
  and every AC is of the form "a check that fires on X and not on Y" — which cannot be evidenced
  without driving each one red against the current code first. Same reason CARD-238 and CARD-239
  carry `TDD: true`.
- [Read CARD-228's three review reports before starting] `meta/review/*CARD-228-cycle{1,2,3}.yml`.
  They contain the measured ink counts, the exact evasions, and the reasoning for why enumeration
  cannot converge — all of it measured, none of it needing to be re-derived. Re-deriving it is how
  this card costs 2d instead of 1d.
- [The trap this card must not fall into] Writing a render check whose *stated* reach exceeds what
  it measures. That is the same family as the static guard's, one abstraction over. State what the
  metric separates, measure the boundary (AC-4), and name what it does not catch.

- STRUCTURE: the instrument is **two layers, not one**. `tests/helpers/round_ink.py` measures
  *ink* only — connected ink regions and, per region, the two numbers that separate a disc from
  everything else — and knows nothing about dots, books or `DifficultyDots`. The **accounting**
  ("which round marks are declared") lives in `tests/test_book_difficulty_dots.py`, because
  "declared" means "returned by `_draw_difficulty_dots`", which is CARD-228's vocabulary. Why:
  CARD-207/229/231/233 each need the measurement, and only this card's guard needs the
  accounting; a helper that knew about tiers would have to be edited by all four.
- STRUCTURE: regions are **4-connected runs under union-find**, implemented here rather than
  taken from a library — `scipy.ndimage.label` is the obvious tool and is not on the baseline
  (G-2, ADR-0006/R1). 4-connectivity is the conservative choice: it splits ink that only touches
  diagonally and never merges unrelated marks, and a filled disc is solid, so it is never split.
- STRUCTURE: the roundness metric is **aspect + fill**, both measured against the region's own
  bounding box, and **no size floor is imposed by hand**. A hand floor would have been an
  unjustified narrowing: measured over 33 real pages (13 baseline + a 20-page picture corpus,
  7458 ink regions) *no* region passes the metric at any size, so nothing needs one — and a
  floor at the glyph's own minimum dot (12 px) would have hidden a rogue mark smaller than the
  glyph can draw. **The metric has a floor of its own, though** (cycle 1, F-002): `fill` cannot
  resolve a disc under 7 px, and the verdict there is not monotone — 4 and 5 px read round,
  2, 3 and 6 px do not, and 1 px inks nothing. That is now a recorded table swept from 1 px
  (`DISC_VERDICT_BELOW_THE_SMALLEST_DOT`,
  `test_the_metrics_own_size_floor_is_where_the_raster_puts_it`) and a named bound, instead of
  a claim that the metric has no floor at all.
- STRUCTURE: the plant lands through a **hook on `_set_band`**, not by editing `src/`. Every AC-1
  route is drawn into the band of every page a real book prints, during a real
  `interior_pages` render, and both module attributes are restored in a `finally` — so
  "planted and reverted" is two measurements in one process rather than a note. The declared
  side is a spy wrapped around `_draw_difficulty_dots` itself, so *declared* means "returned by
  the one drawing site" and not "a geometry the test re-derived".
- STRUCTURE: **the two instruments are kept side by side and neither is called the wider one.**
  The `ast` walk reads every module on disk, including code no test renders, and sees four
  spellings; the render check sees any spelling, on the pages it renders and nowhere else. The
  residue of the pair — a mark in one of the six recorded spellings drawn on a surface nobody
  renders — is stated in both places (G-1, G-6).

### AC by AC, each test driven red first

- AC-1: tests `TestRoundMarkOnThePage_CatchesWhatTheWalkCannotSee::test_a_survivor_of_the_static_walk_is_caught_on_the_page[L1 line fan | PT1 point loop | BM1 bound method]`,
  `::test_the_walk_lets_the_same_route_through[...]`, `::test_reverting_the_plant_leaves_the_book_clean`
  — **red→green**. Red with the roundness predicate stubbed to `False`:
  "L1 line fan drew 6 glyphs of 2 filled dots each, so at least 12 round marks were expected,
  found 0" (the plant had landed: 6 bands, 3240 ink regions measured).
  The revert test was rewritten in cycle 1 (F-008): it plants first, asserts both hooked module
  attributes are the captured originals again, and only then renders the clean book itself — so
  the half that says "the revert happened" can fail, and the property no longer depends on a
  warm `_MEASURED` and pytest's declaration order (run alone with `-k reverting`, the first
  version measured a book that had never been planted). Its old `plants == 0` assertion was a
  tautology — an unplanted render never wraps `_set_band` — and is gone.
- AC-2: tests `TestRoundMarkOnThePage_PassesOnTheRealBook::test_the_books_own_pages_carry_no_undeclared_round_mark`,
  `::test_the_closest_the_book_comes_to_a_round_mark_is_measured`,
  `::test_the_glyph_the_one_site_draws_is_found_and_accounted_for`,
  `::test_the_accounting_is_an_exact_multiset`,
  `::test_a_seeded_corpus_of_pictures_draws_no_round_mark` — **red→green**. The two "no round
  mark" tests pass trivially under the stub and are worthless alone, which is why the
  discrimination test is in the same class: it was red under the stub (the declared glyph was
  not found) and is what makes AC-2 a measurement of *separation* rather than of silence.
  Cycle 1 corrected what this class *says* about its margin (F-003): measured **1.8859**, not
  "over 2", carried by `fill` **alone** — the closest region is a 99 x 94 px filled block at
  `(144, 1266, 242, 1359)` whose aspect, 1.0532, is already inside the aspect tolerance, so
  doubling both tolerances makes it round and reds AC-2. The asserted floor went from 1.5 to
  **1.8**, and *which* tolerance carries the margin is now asserted too, off a `BookInk.closest`
  the measurement carries. The accounting also became per **page** (F-009), with a control for
  a mark at a declared box on another page.
- AC-3: tests `TestRoundMarkOnThePage_SameVerdictForEverySpelling::test_every_spelling_is_caught`,
  `::test_every_spelling_is_caught_the_same_number_of_times`,
  `::test_every_spelling_is_caught_in_the_same_places`,
  `::test_the_walk_sees_two_of_the_four_and_the_page_sees_all_four`,
  `::test_a_typed_dot_measures_the_same_as_a_stroked_one` — **red→green**.
- AC-4: tests `TestRoundMarkOnThePage_TheBoundaryIsMeasured::test_a_disc_measures_round_at_every_diameter_it_can_be_drawn`,
  `::test_the_fill_tolerance_sits_in_a_measured_gap`, `::test_the_aspect_tolerance_sits_in_a_measured_gap`,
  `::test_the_rounded_rectangle_boundary_is_where_the_measurement_puts_it`,
  `::test_a_hollow_mark_is_not_measured_as_round`, `::test_a_mark_that_touches_other_ink_is_not_measured_as_round`,
  `::test_a_diagonal_touch_is_not_a_merge`, `::test_the_guard_only_measures_the_surfaces_it_renders`
  — **red→green**. Cycle 1 added two more bounds to the same class, each driven red before it
  was green: `::test_a_mark_lighter_than_the_ink_level_is_not_measured_at_all` (F-001 — red with
  the grey disc asserted as *found*, and red again under a mutant that drops `INK_LEVEL` to 200
  so the grey becomes ink) and `::test_the_metrics_own_size_floor_is_where_the_raster_puts_it`
  (F-002 — red against the recorded table under a widened `ROUND_FILL_TOLERANCE`, and red if the
  sweep stops reaching 1 px).
- AC-5: tests `TestRoundMarkOnThePage_TheNamedLimitsListShrinksHonestly::test_the_table_is_the_six_routes_cycle_3_left_open`,
  `::test_the_walk_really_is_blind_to_every_route_in_the_table`, `::test_the_walks_own_predicate_can_fire`,
  `::test_every_route_the_table_says_is_closed_is_caught_on_the_page`, `::test_the_marker_can_fire`,
  `::test_the_limits_list_is_exactly_the_routes_no_instrument_closes` — **green→red→green**, which
  is the card's own self-test and was run in that order on purpose: the six limits were first
  *marked* in CARD-228's docstring (`**LIMIT:** <mutant>`) while the metric was still stubbed —
  equality **green**, correctly, because nothing was closed; implementing the metric turned it
  **red** (all six closed, all six still carried); striking the six markers turned it **green**.
- AC-6: measured, recorded in `meta/profiling/card-241-render-check-cost.md` and below. **Not
  marked, because it does not need to be**: 4.80 s for 33 tests, 0.5 % of the suite's 930.81 s
  (4.63 s for the 31 this card first shipped).

### AC-6, the numbers

**33** new tests (31 when first measured, +2 in the fix cycle) in **4.80 s** wall (the file:
1.65 s → 6.33 s, 88 → 121 tests). The fix cycle's own cost, measured as a before/after pair on
one host with the pre-fix file restored from a byte copy, is **+0.4 s** (4.28–4.39 s → 4.70–4.91 s
over three runs each) for one extra interior render — the revert test now renders the clean book
itself (F-008) — and two canvas tests; the card's original 4.63 s reproduces in the "before"
column. **12 interiors and 163 pages** rendered and measured, plus one cover page; ~15 ms to
render a page and ~20 ms to measure it; peak RSS **836 MB** (835–851 MB re-measured, unchanged
by the fix because interiors are rendered one at a time), which is `interior_pages` materialising
13 pages at a measured ~31–35 MB each — the render adds +398..455 MB against the measurement's
own +38..92 MB — and not the measurement. The slowest single test is 0.79 s. Full table, host and
command in `meta/profiling/card-241-render-check-cost.md`.

### Mutants (each its own fresh pytest process; file restored and `shasum`-verified after)

| # | mutant | verdict |
|---|---|---|
| M1 | `ROUND_FILL_TOLERANCE` 0.12 → **0.40** (widened past the book's own filled cells) | **KILLED**, 9 failed — AC-2's three, the corpus sweep, the declared-glyph accounting, and all three AC-4 gap tests |
| M2 | `ROUND_FILL_TOLERANCE` 0.12 → **0.025** (the claim's edge: the sweep's least circular disc reads `fill` 0.961 — re-measured in cycle 1; the 0.968 first recorded here is not a figure the sweep produces, and a 12 px disc reads 0.990) | **KILLED**, 9 failed — the disc sweep, both gap tests, AC-3's counts, AC-5's equality |
| M3 | `ROUND_ASPECT_TOLERANCE` 0.2 → **0.08** (the claim's edge: only the hexagon changes verdict) | **KILLED** by exactly `test_the_aspect_tolerance_sits_in_a_measured_gap`, 1 failed |
| M4a | region merging disabled (`if False`) — every run its own region | **KILLED**, 13 failed |
| M4b | corner-touching runs merged (8-connected) | **SURVIVED** 117 green at first — the 4-connectivity claim had no control. Added `test_a_diagonal_touch_is_not_a_merge`; re-run → **KILLED**, 1 failed, by that test alone |
| M5 | `fill` measured against the box instead of the inscribed ellipse | **KILLED**, 11 failed |
| M6 | `_unaccounted` becomes a set instead of a multiset | **KILLED** by exactly `test_the_accounting_is_an_exact_multiset` |
| M7 | the drawing site declares nothing (`declared.extend` → a dead list) | **KILLED** by exactly `test_the_glyph_the_one_site_draws_is_found_and_accounted_for` |
| M8 | a route the page closes carried in the table as `closed_on_the_page=False` | **KILLED** by exactly `test_every_route_the_table_says_is_closed_is_caught_on_the_page` |
| M9 | a closed route put back on the static guard's list (`**LIMIT:** L1 line fan`) | **KILLED** by exactly the limits equality — direction A: closed but not struck |
| M10 | a route claimed as `seen_by_the_walk=True` | **KILLED** by exactly `test_the_walk_really_is_blind_to_every_route_in_the_table` |
| M11 | the predicate returns `False` while all six limits stay struck | **KILLED** by the limits equality — direction B: struck but not closed |

M4b is the one that changed the deliverable: it is recorded because it *survived*, not because
it was expected to die. Two mutants per claim, as the standing rule asks — one inside the
claimed region (M1, M4a, M5) and one at the claim's edge (M2, M3, M4b, M6–M11).

### Mutants of the cycle-1 fix itself (same discipline; each file restored and `shasum`-verified)

| # | mutant | verdict |
|---|---|---|
| M12 | `INK_LEVEL` 128 → **200**, so the package's grey is ink | **KILLED** by `test_a_mark_lighter_than_the_ink_level_is_not_measured_at_all` — its premise assertion, which is the bound's own statement |
| M13 | `ink_mask`'s threshold widened to 250 with `INK_LEVEL` left at 128 (the premise holds, the grey becomes ink) | **KILLED** by the same test's substantive half: the grey disc now has a region `(100,100,140,140)` |
| M14a | `_disc_sweep()` put back to `range(MIN_DOT_PX, 61)` | **KILLED** by `test_the_metrics_own_size_floor_is_where_the_raster_puts_it` — "the sweep no longer reaches every diameter the table records" |
| M14b | the recorded table's `6: False` → `True` | **KILLED** by the same test, against the measurement |
| M14c | `ROUND_FILL_TOLERANCE` 0.12 → **0.30** (the floor moves) | **KILLED** by the same test: 2 and 3 px now read round |
| M15a | `ROUND_FILL_TOLERANCE` doubled to **0.24** — the docstring's own claim | **KILLED**, 2 failed: the margin test *and* `test_the_books_own_pages_carry_no_undeclared_round_mark`. So "doubling both tolerances makes that block round and AC-2 reds" is measured, not argued |
| M15b | `_distance_from_round` scaled by 0.9 (the margin eroded a tenth) | **KILLED** by the margin test at 1.6973 — and it is **above** the old 1.5 floor, which is exactly what raising the floor to 1.8 bought |
| M15c | the margin measured on `aspect` alone | **KILLED** by the margin test (0.0000) |
| M15d | `ROUND_ASPECT_TOLERANCE` 0.2 → **0.02** | **SURVIVED**, correctly: the closest region is still fill-carried (a perfectly square filled cell, `aspect` exactly 1.000), so the asserted property still holds. Recorded because it shows the "carried by fill" claim is not falsifiable by a tolerance — the book's ink is made of filled rectangles |
| M15e | `BookInk.closest` reports the **farthest** region, `margin` left correct | **KILLED** by exactly the "carried by fill" assertion, with the floor assertion still green — the control M15d could not be |
| M16 | the `finally` in `_interior_ink` no longer restores `_set_band` | **KILLED** by `test_reverting_the_plant_leaves_the_book_clean`: "the plant's hook on _set_band was not restored". Under the old version of that test this mutant was invisible |
| M17 | `_unaccounted` matched on the box alone, page dropped | **KILLED** by exactly the new cross-page case in `test_the_accounting_is_an_exact_multiset` |

Order-independence of the revert test was checked the way the finding found it: `-k reverting`
alone now renders **2 interiors** (the plant, then the clean book) and passes, where before it
rendered one and measured a book nothing had been planted in.

### What the instrument does not catch, with the control for each

Stated here as well as in `tests/helpers/round_ink.py`, because a render check whose stated
reach exceeds what it measures is the static guard's defect one abstraction up:

They are six readings of **one** sentence, and the sentence is the useful part because it
predicts the next gap instead of patching this one: **this instrument discriminates on
silhouette only, so every non-silhouette property of ink — darkness, colour, opacity — is open
to it by construction.**

1. **a mark lighter than `INK_LEVEL`** (cycle 1, F-001) — `ink_mask` thresholds at grey 128,
   and the package itself draws the solved page's grid at grey 160 (`_SOLVED_GRID_GRAY`), so a
   dot in the book's own grey has no region at all and ADR-0036/R3's check passes green with it
   on the page. Measured: a grey-160 disc gives 0 ink regions and 0 round marks, the same disc
   in `INK` gives 1 of each. Control:
   `test_a_mark_lighter_than_the_ink_level_is_not_measured_at_all`. Closing the route is a
   follow-up card's; this card's job was to stop claiming it was closed.
2. **a hollow mark** — a ring reads `fill` 0.15..0.28. Control: `test_a_hollow_mark_is_not_measured_as_round`
   (and its paired control, the same silhouette filled, which is round). `DifficultyDots`
   cannot express an all-outlined row, so the glyph itself always leaves a filled dot.
3. **a mark that touches other ink** — regions are connected. Controls:
   `test_a_mark_that_touches_other_ink_is_not_measured_as_round` (orthogonal touch: missed; one
   pixel clear: found) and `test_a_diagonal_touch_is_not_a_merge` (corner touch: still found).
4. **a footprint that is not nearly square** — an oval beyond ±0.2. Control:
   `test_the_aspect_tolerance_sits_in_a_measured_gap`.
5. **a mark under 7 px across** (cycle 1, F-002) — `fill`'s own resolution, not a chosen floor,
   and not monotone: a 4 px disc is round, a 6 px one is not. Control:
   `test_the_metrics_own_size_floor_is_where_the_raster_puts_it`, against a table recorded from
   a sweep that now starts at 1 px.
6. **a surface nobody renders** — it is the interior's 13 pages; a cover, a proof sheet or a CLI
   PNG export is outside. Control: `test_the_guard_only_measures_the_surfaces_it_renders`, which
   finds the dot on a cover and then shows the guard's page set does not include it.

### Decisions this station took

- **ADR delta: TAKEN.** `meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md`
  gains **ADR-0036/R3** (exactly one function in `src/nonogram/**` puts a round mark on a page,
  `check:` this card's `test_the_books_own_pages_carry_no_undeclared_round_mark`, with both
  instruments' reach and the residue of the pair in the rule's comment) and **ADR-0036/R4**
  (CARD-228's package-wide dingbat-literal ban, `check:` `test_no_module_types_a_round_mark_as_a_character`,
  with its exemption and the computed-string limit named). Decision unchanged, History entry
  added. The rejected alternative is recorded in the ADR itself: a new ADR or a CON in
  `requirements.yml` is arguably the better *home* for R4, since a package-wide literal ban is
  not a geometry decision — it was rejected only as the more expensive move from an
  implementation card, and the delta says so, so relocating it costs nothing. Validator:
  `validate.py --root meta/architecture` reports **0 errors, 86 warnings** both before and after
  the delta (identical to `main`), and the `## Rules` block parses with both new `check:` refs
  naming tests that exist.
  **Cycle 1 narrowed R3's stated reach rather than widening the metric** (F-001). The rule's
  comment and the History entry now name a fifth bound — ink **darkness**: `INK_LEVEL` is grey
  128 and the package draws the solved grid at grey 160, so the residue open to *both*
  instruments is a mark in one of CARD-228's six spellings drawn either on an unrendered surface
  **or** in ink lighter than the threshold. Both halves carry a control. The two remedies that
  were weighed and rejected: parameterising the ink threshold (the solved grid's grey cells
  would become ink, which re-opens the whole legitimate-marks corpus and the margin analysis)
  and naming the solved grid an ADR-0039/R3 exemption (wave 42 spent two cards learning to
  distrust that construct). Closing the grey route is a follow-up card's.
- **`meta/profiling` (G-5): nothing re-measured, one new file.**
  `meta/profiling/card-241-render-check-cost.md` is AC-6's record. No frozen artefact was
  regenerated, and `tests/test_suite_profile.py` only discovers `suite-durations-*.txt` and its
  matching `suite-hotspots-*.md`, so a new `card-241-*.md` is invisible to it (as `card-235-*`
  already is) — verified by running that file: 399 passed.
- **The render set (G-5), handled deliberately rather than discovered.** The new tests *do*
  render, and at 0.15 s/test they sit in the band the 2026-10-15 profile measures for the
  render-heavy set — but `tests/test_book_difficulty_dots.py` still does not match
  `RENDER_API_PATTERN`, because the call it makes (`interior_pages`) is not one of that
  pattern's eight names. Two things were needed to keep that true and both are recorded in the
  code: a local helper first named `_measure_interior` matched the pattern's *interior-followed-
  by-parenthesis* name and reddened
  `test_the_frozen_render_set_still_matches_the_grep_that_defines_it` (so it is `_interior_ink`),
  and then the docstring **explaining** that matched it too (so the sentence spells the name out
  instead of quoting it — CARD-228's missed third option, its review's F-204, used here rather
  than rediscovered). Re-freezing `RENDER_HEAVY_SNAPSHOT` to add this file is a `meta/` commit
  and is **not** this card's: it is recorded for the next profiling run in
  `meta/profiling/card-241-render-check-cost.md`.
- **No cache had to be cleared between plant and revert.** The harness does not simulate a
  different environment (CARD-221's trap): it adds ink. The render path's three `lru_cache`s are
  pure functions of their arguments and identical in both halves, and the empty-plant control
  measured in the same process (`test_reverting_the_plant_leaves_the_book_clean`) is the proof
  that no page is cached.

META EDIT: meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md, meta/profiling/card-241-render-check-cost.md, meta/kanban/cards/CARD-241.md

- NOT DONE, and flagged rather than done quietly: `meta/architecture/trace.yml`'s FR-033/FR-043
  rows do not list this card's test classes. The card's header says "Trace: to be updated if the
  ADR delta is taken", and the delta *was* taken — but the trace's rows are per requirement and
  editing them is the architect station's surface, not an implementation card's; the two new
  rules carry their own `check:` refs, which is what `--verify-refs` reads. Orchestrator's call.
- [Scope] tests/helpers/page_ink.py, tests/helpers/round_ink.py, tests/test_book_difficulty_dots.py
- [Review sync] pulled the worktree's `## Failure matrix` + `## Worktree notes` (165 added lines) into the main copy
- [Scope gate] IN_SCOPE, with one recorded drift. Committed diff is `tests/` only — no `src/` file in it at all, so G-4 (do not change the glyph) holds structurally. Uncommitted: the ADR-0036 delta (inside `Touches`) and `meta/profiling/card-241-render-check-cost.md`, which is OUTSIDE `Touches`.
- [Touches drift] meta/profiling/card-241-render-check-cost.md — **not** a G-5 violation, and the reason is the card's own text: AC-6 requires the cost "measured and recorded ... in the card and in `meta/profiling/`", so the card was cut to write that file and `Touches` simply failed to list the directory (a prediction defect, fixed here, not a contract breach). Verified rather than argued: G-5 guards *re-measuring or regenerating frozen artefacts*, and this file is new; `test_suite_profile.py` discovers only `suite-durations-*.txt` plus a matching `suite-hotspots-*.md` (`tests/test_suite_profile.py:103/:108`), which this name matches neither of; and `meta/profiling/card-235-*.md` is existing precedent for a card-scoped note in that directory. `RENDER_HEAVY_SNAPSHOT` was deliberately NOT re-frozen.
- [System contract] section stale — refreshed from the live lens before review: 3 rules → 13. +ADR-0036/R1, ADR-0038/R7, ADR-0038/R8, ADR-0039/R1, ADR-0039/R2, ADR-0039/R3, CON-005, CON-009, CON-010, CON-011, CON-012 / −CON-020 (the lens no longer scope-matches it to this card; the card's own ADR-0036/R4 text still reasons about CON-020's type floor, and `TestInteriorType_EveryFaceHoldsTheFloor` was run green by the implementer, so the reviewer verifies it rather than inheriting it). ⚠ **ADR-0039/R3's own check test, `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`, lives in `tests/test_book_difficulty_dots.py:1990` — the file this card rewrote (+1316 lines). A card editing the check of a mandatory standing rule is the sharpest thing in this review.
- [Build gate] PASSED (full, 898s; 7758 passed, 9 skipped, 0 failed, 0 errors, exit 0). Not vacuous: 7767 tests executed. Ran under `meta/kanban/.full-suite.lock`, released immediately. Cross-checks against the wave's other gate: base `main` is 7727 (CARD-239's recorded merge-gate figure), +31 from this card's new tests = 7758, and CARD-242's concurrent gate showed 7727 + 40 = 7767 — both runs agree on the same base.
- [Review 1/3] Score: 7.5 — crit: 0, imp: 3 (all one root cause, RC-1: reach sentences written ahead of the measurement), medium: 1, low: 6, info: 3. Risk MEDIUM, lane DEEP. Report: `meta/review/20261017T074900Z-CARD-241-cycle1.yml` (passes `yaml.safe_load`).
- [Review sync] 1 report → meta/review/
- [Review 1/3] Step 8h coverage: **13/13** card rules carry a verdict line (10 ✓ holds, 2 ⚠ unchecked `no_eligible_fact` for ADR-0038/R7+R8, 1 ✗ violated: ADR-0039/R1). CON-020 — which the lens dropped but the card's new R4 text reasons about — was verified rather than inherited: `TestInteriorType_EveryFaceHoldsTheFloor` 4 passed on this head.
- [Review 1/3] **The sharpest question came back clean**: ADR-0039/R3's own check test is untouched. No `def test_` in lines 1–2438 is modified; the 1292 added lines are the module docstring, the import block, three docstring hunks and a pure append after :2438. The card edited the file holding a mandatory rule's check without weakening that rule's control.
- [Review 1/3] Independently corroborated rather than accepted: `ink_regions` cross-checked against a BFS 4-connected labeller over 400 seeded masks (incl. degenerate 1×N) — **0 mismatches** on `(left, top, right, bottom, ink)`; M4b's story reproduced (the 8-connected mutant is killed by exactly `test_a_diagonal_touch_is_not_a_merge`, and under the mutant the merged region reads 137×41 and the guard reports *neither* mark); AC-5's equality red in both directions, direction A re-derived by re-adding `**LIMIT:** L1 line fan` in memory; G-1's static guard intact and firing (29 passed).
- [Severity gate 1/3] Score 7.5 below min_score 8 AND 3 important findings — fix mandatory.
- [Adversarial] **Deviation from the unconditional-skeptic rule, recorded as such.** Two of the three gating findings were verified by the orchestrator's own measurement instead of by a skeptic subagent, and the third was accepted as reported. Reason: an account rate limit had already destroyed two agents' in-flight work this session, and these findings are deduction and arithmetic rather than a contested model (unlike CARD-242's F-002, where a skeptic was essential and overturned the prescription). What was measured here directly:
  - **F-001 CONFIRMED, deductively and empirically.** `tests/helpers/page_ink.py:62` sets `INK_LEVEL = 128`; `src/nonogram/admin/book_pdf_generator.py:1341` sets `_SOLVED_GRID_GRAY = (160, 160, 160)`, which is lighter than the threshold and therefore not ink. Measured: a grey-160 disc yields **0 ink regions and 0 round marks**, while the identical disc in black yields 1 of each. So a difficulty dot drawn in the package's own grey is invisible to the instrument, and ADR-0036/R3's declared check passes green with it on the page.
  - **F-002 CONFIRMED, and my own summary of it was WRONG in a way the fix cycle corrected.** What I measured: `fill` 1.273 @2 px, 0.707 @3 px, 0.849 @6 px (not round), round at 7 px (0.961) — and from those six points I inferred "there IS a floor, it is 7 px". **That inference was false, and the fix agent refused it with the measurement I had not taken**: 4 px reads 0.955 ✓ and 5 px reads 1.070 ✓, while 6 px reads 0.849 ✗. Re-verified here independently: d=1 inks nothing, 2 ✗, 3 ✗, **4 ✓, 5 ✓**, 6 ✗, and every diameter 7..142 ✓. So the verdict is **non-monotone below 7 px** — the raster's accident, not a floor — and the honest statement is the one that shipped, not mine. `_disc_sweep()` starting at `MIN_DOT_PX`=12 (nothing controlling the range below it) was the correct half of the finding, and the sweep now starts at 1 px with the 1..11 verdicts recorded in a table, so the non-monotonicity is asserted rather than narrated. Noted because this is the same defect class the card is about: I wrote a reach sentence ("there IS a floor, it is 7 px") that went one step past what I had measured.
  - **F-003 accepted as reported** (margin 1.8859, not the docstring's "over 2", carried by `fill` alone; closest region a 99×94 block at `(144,1266,242,1359)`, aspect 1.0532, fill 1.2263). Not independently re-measured: it needs the rendered baseline pages. It is a correction in the conservative direction and its remedy — restate the measured numbers and raise the asserted floor from 1.5 to ~1.8 so erosion reds the test — is right whichever figure stands.
- [Owner decision 2026-10-17] F-001's remedy chosen: **narrow ADR-0036/R3's stated reach and name the darkness bound with a control** — R3 promises "silhouette only, in black ink". Rejected with reasons on the record: parameterising the ink threshold (the grey solved-grid cells become ink, forcing the legitimate-marks corpus and the whole margin analysis — already the card's tightest number at 1.886 fill-tolerances — to be re-measured, pushing the card past 1d), and naming the solved grid as an ADR-0039/R3 exemption (wave 42 spent two cards learning to distrust the exemption as an escape hatch). Closing the grey route is carded as **CARD-243**, which inverts this card's control rather than deleting it.
- [Fix 1] dispatched on that basis: F-001 (darkness bound + its failing control + the silhouette-only generalisation, in both the code's bound list and R3's comment), F-002 (the floor is 7 px, emergent not chosen; sweep extended below `MIN_DOT_PX` against a recorded table), F-003 (margin restated as measured, carried by `fill` alone, asserted floor raised 1.5 → ~1.8 so erosion reds the test), plus six minors. The fix agent was told to re-measure F-003 rather than copy the figure, and to report a disagreement rather than silently adopt either number.
- [Fix 1] 9 of 12 findings FIXED (F-001..F-009), each with a DECLARATIONS line; F-010/F-011/F-012 left `open` in the review YAML as info/out-of-scope (trace.yml, `RENDER_HEAVY_SNAPSHOT`, R4's home). **Fix pre-gate PASSED**: every named test resolves and runs green — `-k RoundMarkOnThePage` **33 passed, 0 failed, exit 0** (was 31).
- [Fix 1] declarations: 9 updated, 1 confirmed-unchanged, 0 none. The fix re-derived the statements its edits invalidated rather than re-wording them — the bound list went 4 → 6 bullets, ADR-0036/R3's comment names DARKNESS and widens its residue to "an unrendered surface OR ink lighter than `INK_LEVEL`", and the AC-4 class table, the profiling note and the card's own AC lines were all brought to the new reach.
- [Fix 1] **It found a stale figure of its own card's by re-measuring rather than copying**: `round_ink.py`'s disc-fill range read 0.968..1.004 and measures 0.961..1.008. That is the CARD-221 pattern (a narrated figure drifting while the asserted one stays true), caught by the rule that a fix must re-derive the declarations it touches.
- [Fix 1] **AC-2's margin independently re-measured and AGREES exactly**: 1.8859, closest region `(144,1266,242,1359)`, 99×94 on interior page 1, aspect 1.0532, fill 1.2263, ink 8963 — carried by `fill` alone (0.2263/0.12), its aspect distance only 0.266; next family the letter stem at 2.2727. The picture corpus measures the same. Asserted floor raised 1.5 → **1.8**, and "carried by fill alone" is now asserted off a new `BookInk.closest` field instead of written in prose.
- [Fix 1] mutants: 12 planted (M12–M17), **11 killed, 1 survived and the survival is the point**. M15d (`ROUND_ASPECT_TOLERANCE` → 0.02) SURVIVED *correctly* — the book's closest ink is filled rectangles at aspect exactly 1.000, so the "carried by fill" claim is not falsifiable by an aspect tolerance; rather than leave an uncontrolled claim, the fix added M15e (`closest` reports the farthest region while `margin` stays correct), which **is** killed by exactly that assertion. A claim whose first control could not fail, given the control that can. Also notable: M15b (`_distance_from_round` ×0.9) died at 1.6973 — *above* the old 1.5 floor, which is precisely what raising it to 1.8 bought, measured rather than asserted.
- [Fix 1] G-1 re-verified mechanically: a byte-copy diff of lines 1–2470 (CARD-228's whole static-walk region, including ADR-0039/R3's check test) shows **only two added imports** (`_SOLVED_GRID_GRAY`, `INK_LEVEL`). `NAMED_LIMITS`/AC-5 untouched, deliberately — adding a grey route to that table would make it something other than "the six routes cycle 3 left open".
- [Fix 1] ⚠ **Timing correction worth carrying into the next card, and a warning about my own numbers.** The fix agent's first before/after pair was taken while CARD-242's full suite held the repo lock and read 7.15 s → 8.92 s. Re-measured on a quiet host, 3 runs each: selection 4.28–4.39 s → 4.70–4.91 s, whole file 5.86–6.02 s → 6.18–6.48 s, i.e. **+0.4 s**, not +1.8 s. The card's original 4.63 s/6.41 s reproduce in the "before" column. The same caveat applies to this card's own build-gate wall-clock figures (898 s pre-fix, and CARD-242's 879 s → 1659 s) — those were measured with a sibling card active and are concurrency, not cost.
- [Build gate] PASSED post-fix (full, 955s; **7760 passed**, 9 skipped, 0 failed, 0 errors, exit 0). Arithmetic cross-checks exactly: 7727 base + 33 (the card's file went 88 → 121 tests).
- [Scope gate 2/3] IN_SCOPE — `tests/helpers/round_ink.py`, `tests/helpers/page_ink.py`, `tests/test_book_difficulty_dots.py` committed, plus the two uncommitted `meta/` artefacts already recorded as `[Touches drift]`. **No `src/` file is in the diff at all**, so G-4 (do not change the glyph) holds structurally.
- [Review 2/3] Entering **confirmation mode** (differential): cycle > 1, cycle 1 parsed cleanly, the changes since the reviewed state are the fix for its named findings, scope IN_SCOPE, and cycle 1 raised no gating finding beyond the three the fix addresses. Fix delta vs `2a6c321`: `tests/test_book_difficulty_dots.py` (+418/−?), `tests/helpers/round_ink.py` (+75), `tests/helpers/page_ink.py` (+6), the ADR (+75).
- [Review 2/3] Score: **9.0** ✓ threshold reached + no critical/important (0 crit, 0 imp, 5 minor, 3 out-of-scope carried as info). Confirmation mode, risk LOW, lane FAST. Improvement +1.5 ≥ 0.5; gating findings 3 → 0. Report: `meta/review/20261017T090957Z-CARD-241-cycle2.yml` (passes `yaml.safe_load`).
- [Review sync] 1 report → meta/review/
- [Review 2/3] Step 8h: **13 rules checked, 11 ✓ holds, 2 ⚠ unchecked (`no_eligible_fact`: ADR-0038/R7+R8, both re-checked rather than carried because their `tests/**` scope intersects the delta), 0 ✗ violated.** 3 carried, 10 re-verified. **ADR-0039/R1 — the rule RC-1 violated — now HOLDS**, re-verified in full and explicitly not carried. The five CONs carry no `scope:` key, so they were re-run fail-closed rather than carried (36 + 5 + 32 passed).
- [Review 2/3] Step 8f mutation check **RUN** (the deferred certification, on stable code): **10 mutants, 10 killed, 0 survivors** — including M-1 (`_distance_from_round` ×0.9) dying at 1.6973, *above* the retired 1.5 floor, which is exactly what raising it to 1.8 bought; M-10 (`ink_mask` → `< 255` with `INK_LEVEL` untouched), the faithful reach-widening mutant for the new darkness bound; and M-6 (the floor table recording 6 px as round).
- [Review 2/3] **The M15d survivor, judged rather than accepted — and the judgement cut both ways.** The reviewer verified the fix's *reasoning* is correct, including its sub-claim: under that mutant the closest region becomes a 56×56 perfectly square filled cell at aspect exactly 1.000000, fill 1.2732, margin 2.2770 — still fill-carried, so "the carried-by-fill claim is not falsifiable by an aspect tolerance" is true and M15e is the right compensating control. **But the recorded verdict is wrong**: at the selection scope the table's sibling rows use, M15d is KILLED by `test_the_aspect_tolerance_sits_in_a_measured_gap` (the hexagon at 1.083..1.167 escapes a 0.02 tolerance). It survives only the narrower `PassesOnTheRealBook` class, which the row does not say. So the card **under-states its own coverage** — the same family it spent a cycle on, pointed the other way. Filed Minor.
- [8h spot-check] **2/2 sampled holds reproduced** — again by the orchestrator's own measurement rather than a skeptic subagent (recorded deviation, same reason as before).
  - **ADR-0039/R3 reproduced, with better evidence than the line-range diff the reviewer used.** My first attempt compared the static-walk region against `main` and showed many changes, which looked alarming and was simply the wrong question — `main` predates this card's own cycle-1 docstring rewrites. Re-done at the **AST level**, which is immune to line drift and docstring edits: of every pre-existing function in the file, **not one body changed and not one was removed**, and `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw` — the mandatory rule's own check — is **byte-identical to `main`**. The static-walk class and the dingbat rule run green. A card rewrote 1316 lines of the file holding a mandatory rule's check without touching a single existing test body.
  - **ADR-0039/R1 reproduced.** Falsifying the new floor table (recording 6 px as round) reds exactly `test_the_metrics_own_size_floor_is_where_the_raster_puts_it`, against a clean shadow baseline of 0 — so the non-monotone floor is asserted, not narrated, and the claim has a control that fails.
  - **ADR-0039/R2's hold accepted on its reasoning, recorded as such rather than measured**: the delta's one new hand-written collection is a *golden record* (keys held to an equality against the executed sweep, values compared to a fresh measurement), not a set the guard consults to decide a verdict — the same distinction cycle 1 drew for `NAMED_LIMITS`. The equality-against-execution is what makes it safe, and it is checked.
- [AC/EC check] **All criteria/constraints ✓** (evidence) — AC-1..AC-6 and G-1..G-6 demonstrated, after two rounds at this station. The gate's independent corroboration is worth keeping: it instrumented `interior_pages` and measured each of the nine planted routes at `plants=6 found=12 declared=0 unaccounted=12` on real interior pages `{4,10,11,12}` (not a synthetic canvas); it reproduced the margin to four decimals (1.8859, closest `(144,1266,242,1359)`, 99×94, aspect 1.0532, fill 1.2263, aspect-distance 0.2660 against fill-distance 1.8859); it **planted a real second drawing site in `src/nonogram/export/png.py`** and confirmed CARD-228's static guard fires on it (`Extra items in the left set: ('nonogram.export.png', '_rogue_second_site')`); and it corroborated the AST result by SHA-256 of each function body — 103 → 163 functions, **none removed, no pre-existing body changed**, R3's check byte-identical. 18 mutants, 16 killed, 2 survivors both deliberate and recorded.
- [AC/EC check] **The gate caught two things, and the first was the orchestrator's own omission.** (1) **The entire cycle-1/cycle-2 fix was UNCOMMITTED.** HEAD `2a6c321` was the pre-fix 31-test state: `test_a_mark_lighter_than_the_ink_level_is_not_measured_at_all` and `test_the_metrics_own_size_floor_is_where_the_raster_puts_it` existed only in the working tree, `_disc_sweep` was still `range(MIN_DOT_PX, 61)`, and the margin floor was still the 1.5 cycle 1 found too slack. Every gate and both review cycles had measured the working tree, so the evidence was sound — but merging from HEAD would have shipped a card whose merged state was not its reviewed state. Committed as `b292b25`. The sibling card's fix was committed; this one was not, and nothing but this gate would have noticed.
- [AC/EC check] (2) **G-6 ⚠ partial on one sentence, fixed.** `TestDifficultyDots_HasExactlyOneDrawingSite`'s closing paragraph stated the pair's residue as "spelled in one of the six ways above **and** drawn on a surface nobody renders". False and uncontrolled: a PA1 pasted mask in grey 160 **on a page the book really prints** is open to both instruments — the walk is blind to a paste at any colour, the render check to anything lighter than `INK_LEVEL`. The same cycle got it right in three other places (ADR-0036/R3's comment, `round_ink.py`'s docstring, the card's notes), so this was one stale sentence the narrowing did not reach — a coverage claim wider than its measurement, which is exactly the ADR-0039/R1 family G-6 exists for. Corrected to the ADR's disjunction, with the second disjunct marked as not optional and the grey instance named. Verified it does not trip `RENDER_API_PATTERN` (the trap this card already hit twice): frozen-set guard 16 passed.
- [Merged] `099864b` (merge commit) over impl `a58e07e` + fix `b292b25`, rebased onto `main` after CARD-242 landed. **Merge gate on the exact tree that ships: full suite 7814 passed, 9 skipped, 0 failed, exit 0** — arithmetic exact (7781 after CARD-242 + 33 from this card's file going 88 → 121).
- [Merged] META EDITs carried into the main repo: ADR-0036's R3+R4 and History entry, `meta/profiling/card-241-render-check-cost.md`, and both review reports. ⚠ **A sequencing lesson worth keeping, found by checking a figure instead of trusting it:** carried BEFORE the merge, `validate.py` reported **87** warnings against the card's claimed 86 — a dead-check-ref on ADR-0036/R3, because `git grep` could not yet see `test_the_books_own_pages_carry_no_undeclared_round_mark` in `main`. The card's 86 was measured in the worktree, where both the ADR and the test exist, and was correct. After the merge the validator returns **0 errors / 86 warnings** with that warning gone — predicted, then verified. **Carry `meta/` after the merge, not before**, or a live rule reads as dead for the length of the window.
