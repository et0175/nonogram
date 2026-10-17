# CARD-243: The round-mark check sees the greys the book actually prints

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/243-round-mark-sees-greys
**Worktree:** ../PythonProject4-card-243
**Source:** CARD-241's review cycle 1 (2026-10-17), finding F-001 — measured there and confirmed independently by the orchestrator, then narrowed rather than closed by owner decision the same day, so CARD-241 could land with its promise matching its measurement
**Idea:** —
**Wave:** 44
**Depends on:** CARD-241 (it owns the instrument, the bound list and ADR-0036/R3's comment this card widens)
**Touches:** tests/helpers/round_ink.py, tests/helpers/page_ink.py, tests/test_book_difficulty_dots.py, meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-10-17T13:48:43Z
**Closed:** 2026-10-17T15:36:01Z
**Actual:** 0.2d
**Merge commit:** 1280085
**Blocked by:** —

## What to implement

CARD-241 proved the one round mark on the page by rendering it instead of reading the source, and that
instrument is sound **where it measures**. It measures a silhouette in ink, and "ink" is a hard
threshold: `INK_LEVEL = 128` (`tests/helpers/page_ink.py:62`). The book's own solved grid draws at
`_SOLVED_GRID_GRAY = (160, 160, 160)` (`src/nonogram/admin/book_pdf_generator.py:1341`) — **lighter
than the threshold, and therefore not ink at all.**

Measured twice, independently, at CARD-241's review:

```
a disc in grey 160  ->  0 ink regions, 0 round marks
the same disc in black  ->  1 ink region, 1 round mark
6 glyphs of difficulty dots planted in grey 160 on every band
    ->  plants=6 pages=13 found=0 unaccounted=0
```

So **ADR-0036/R3's declared check passes green with 18 undeclared grey dots on the pages.** The rule
says exactly one function in `src/nonogram/**` puts a round mark on a page; a second function drawing
its dots in the grey that is already a constant in the same module is invisible to the guarantee.

CARD-241 was narrowed rather than widened, by owner decision on 2026-10-17: it states the darkness
bound with a control and R3 promises "silhouette only, in black ink". **This card is the other half —
make the instrument see the greys the book really prints, so R3 can promise any round mark at any
darkness the book uses.**

The generalisation CARD-241's review drew, which is the reason this card is worth running rather than
leaving as a named bound: **the instrument discriminates on silhouette only, so every non-silhouette
property of ink — darkness, colour, opacity — is open by construction.** Grey is the instance that is
already a constant in the production module; it is not the only one.

### What makes this a card and not a one-liner

Lowering or parameterising the threshold is two lines. The work is everything that moves when it
changes, and CARD-241's own figures say how much:

- At a lighter threshold the grey **solved-grid cells become ink**, so the legitimate-marks corpus has
  to be re-measured. CARD-241's closest legitimate mark in black is a 99×94 filled block at aspect
  **1.0532**, fill 1.2263 — already inside the aspect tolerance and only **1.886 fill-tolerances**
  clear of being called round. Adding grey blocks to the population moves that margin, and it is
  already the card's tightest number.
- The two tolerances (`ROUND_FILL_TOLERANCE` 0.12, `ROUND_ASPECT_TOLERANCE` 0.2) were each set at the
  midpoint of a measured gap. A new ink population may move both midpoints, and AC-4's boundary
  measurements (hexagon round at 0.930-0.958, pentagon not at 0.822-0.870, the rounded rectangle
  flipping between r=14 and r=15) must be re-derived, not assumed to carry.
- Cost: CARD-241 measured 31 tests at 4.63 s with a render-dominated 836 MB peak (+455 MB render,
  +46 MB measure, ~35 MB/page). Measuring at two thresholds roughly doubles the measurement half and
  is still ~1% of the suite — but say the number rather than assume it.

## Acceptance criteria

- **AC-1** (happy, the grey route dies): *Given* a difficulty-dot glyph drawn in `_SOLVED_GRID_GRAY`
  on the pages the book really renders, *then* the check reports it as an undeclared round mark —
  demonstrated by planting and reverting, with the same plant shown MISSED by CARD-241's
  black-ink-only instrument so the card's own contribution is measured rather than asserted.
  (test: `TestRoundMarkOnThePage_SeesTheGreysTheBookPrints`)
- **AC-2** (guard, the real book still passes at the wider threshold): *Given* the interior pages and
  the seeded picture corpus, *then* the check passes on every one of them unmutated at the new
  threshold — grey solved-grid rules, grey filled cells, frames and glyph text included — and the
  margin to the closest legitimate mark is **re-measured and asserted**, not inherited from
  CARD-241's black-ink figure of 1.886.
  (test: CARD-241's `TestRoundMarkOnThePage_PassesOnTheRealBook`, extended)
- **AC-3** (edge, the tolerances are re-derived): *Given* the wider ink population, *then* both
  tolerances are re-measured against it and each is shown to sit at the midpoint of a measured gap, or
  moved with the measurement recorded. AC-4's boundary cases from CARD-241 (hexagon, pentagon, rounded
  rectangle crossing) are re-run and their verdicts restated. A tolerance that keeps its value because
  the measurement says so is a legitimate outcome; a tolerance that keeps its value because nobody
  looked is the defect.
- **AC-4** (guard, the darkness bound shrinks honestly): *Given* CARD-241's named darkness bound and
  its control (grey disc missed / black disc found), *then* the bound is struck from both the code's
  bound list and ADR-0036/R3's comment in the same diff that closes the route, and the control is
  inverted rather than deleted — the grey disc must now be FOUND, and a test must go red if the bound
  is struck without the route being closed or closed without being struck. Same mechanism as
  CARD-242's `test_the_struck_bound_and_the_closed_route_agree`, which is the precedent to copy.
- **AC-5** (edge, what is still open): *Given* the widened instrument, *then* the non-silhouette
  properties it still cannot see (colour at equal luminance, partial opacity, anti-aliased edges below
  the threshold) are recorded as measured bounds with a control each, in the shape CARD-241 and
  CARD-242 both use. R3's reach statement must say what it now covers and what it does not.
- **AC-6** (edge, cost): *Given* the two-threshold measurement, *then* its wall-clock and peak-memory
  cost are measured and recorded in `meta/profiling/`, and compared against CARD-241's recorded
  figures rather than stated fresh.

## Guardrails

- G-1: **do not delete CARD-228's static guard, and do not delete CARD-241's black-ink control.** The
  instrument gains a threshold; it does not lose the one whose numbers are already measured.
- G-2: do not change the glyph. `difficulty_dots`, `_draw_difficulty_dots` and their geometry are
  CARD-228's; CARD-241 only measured them and this card only measures them differently.
- G-3: no `src/**` change. If the production greys need naming, read them from the production module
  rather than copying the literals into the test tree.
- G-4: no new runtime dependency (ADR-0006/R1); no `hypothesis` (seeded stdlib corpora with an
  asserted minimum case count).
- G-5: do not weaken ADR-0039/R3's check test
  (`test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`). CARD-241 left it untouched
  while rewriting the file around it; keep that record.
- G-6: do not re-measure or regenerate `meta/profiling`'s frozen artefacts. A new card-scoped note is
  the convention (`card-235-*.md`, `card-241-*.md`); `RENDER_HEAVY_SNAPSHOT` is re-frozen only on a
  deliberate profiling run.
- G-7: every claim about what the widened check catches carries a control that can fail. This is
  ADR-0039/R1, and CARD-241 reached cycle 2 for breaking it three times in one root cause — reach
  sentences written ahead of the measurement.

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-243 --root meta/architecture` (15 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- Re-run the lens at `start` if time passes before this card is picked up: CARD-241's own
  section was stale by ten rules when it reached review, because ADR-0039 landed after the card
  was cut.

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static… (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same diffic… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the … (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra… (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named… (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH… (check: test: test_the_control_for_each_spelling_depends_on_the_set)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot a… (check: test: test_the_guard_sets_are_derived_and_not_hand_written)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is… (check: test: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correc… (check: test: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a… (check: test: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a n… (check: test: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to … (check: test: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decode… (check: test: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** FR-033, FR-043.
- **CON:** CON-020 (the dots are not text, but a lighter ink threshold brings the type floor's own
  greys into the measured population — check it rather than inherit it).
- **ADR:** ADR-0036/R3 (this card rewrites its reach statement), ADR-0036/R4, ADR-0039/R1, ADR-0006/R1.
- **Components:** COMP-007, COMP-009.
- **Trace:** CARD-241 left `trace.yml` untouched when it added R3 and R4, on the argument that trace
  rows are per-requirement and the rules carry their own `check:` refs (validator 0 errors / 86
  warnings, identical to `main`). Its reviewer agreed it does not gate, and noted one counter-precedent
  at `trace.yml:1671`, where an ADR-0036/R1 check test IS listed inside a requirement row. If this card
  changes R3's reach, settle that question once at the architect station rather than a third time here.

## Worktree notes

- [Why it is a separate card] Owner decision, 2026-10-17, at CARD-241's review cycle 1. Three options
  were measured: narrow R3's reach (chosen), parameterise the threshold (this card), or name the solved
  grid as an ADR-0039/R3 exemption (rejected — wave 42 spent two cards learning to distrust the
  exemption as an escape hatch). The narrowing kept CARD-241 near its 1d estimate and made its promise
  match its measurement; widening the instrument is real work with its own margin analysis.
- [Read before starting] `meta/review/20261017T074900Z-CARD-241-cycle1.yml` — F-001 with the planted
  measurement, and RC-1, which is the root cause all three of CARD-241's gating findings shared. Also
  CARD-241's own `meta/profiling/card-241-render-check-cost.md` for the cost figures to compare against.
- [The trap, inherited] CARD-241's notes named it and its review found it three times anyway: a check
  whose *stated* reach exceeds what it measures. This card widens the reach, which means every sentence
  about it has to be re-derived — the bound list, R3's comment, the AC-2 class docstring and the
  profiling note all state the black-ink-only reach today.

### Build pass, 2026-10-17 (implementation agent)

`META EDIT: meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md, meta/profiling/card-243-two-threshold-cost.md, meta/kanban/cards/CARD-243.md`

**What the instrument gained.** A second threshold, not a changed one.
`page_ink.ink_mask(page, level=INK_LEVEL)` takes the level as a parameter and keeps its default, so
`drawing_of` and `two_up_ink.py` read exactly the page they always did; `round_ink` gains
`MARK_LEVEL = 208`, `MEASURED_LEVELS`, `mark_regions(page)` and `round_marks(page, level=MARK_LEVEL)`.
`ink_regions(page)` still answers CARD-241's question at CARD-241's threshold with CARD-241's numbers
(3222 regions on the baseline 13 pages), and the guard's verdict comes from the wider reading.
The harness reads each page at both levels in one walk and returns a `LevelInk` per threshold, so
every claim about *which* instrument sees what is two readings of one render rather than two renders.

**Why 208, and why not 161.** 208 is `ceil((160 + 255) / 2)` — the midpoint of the gap between the
lightest tone the package draws and paper — and the threshold is **derived**, not chosen:
`_flat_tones` walks `src/nonogram/**` for module-level flat grey triples, finds exactly
`{0, 160, 255}`, and `test_the_mark_level_is_the_midpoint_of_the_palette_the_package_draws`
recomputes the number from them, so a production module that starts drawing in a lighter tone reds a
test. 161 was measured as the alternative (it keeps the margin at CARD-241's 1.8859 exactly) and
rejected: it sits one level above the production grey rather than in a gap, so a tone of 170 would
walk straight through it.

**What was measured before the design was chosen**, because this was the card's real risk:

| candidate | baseline 13 pages | picture corpus 20 pages |
|---|---|---|
| **cumulative, `< 208`** (chosen) | 0 round marks, margin 1.8182 | 0 round marks |
| cumulative, `< 161` | 0 round marks, margin 1.8859 | 0 round marks |
| **banded**, ink `[0,128)` + grey `[128,208)` | **28 round marks** | **40 round marks** |

The banded reading — one layer per tone, which looked like the principled design — reds honest pages:
clipping anti-aliased halos and grey rules against black ink leaves thousands of 2x2 fragments, and
28 of them read `aspect` 1.0000 / `fill` 0.9549. The cumulative reading has the opposite risk (the
solved grid's grey rules join the filled cells into one blob) and the measurement says that blob is
the grid's whole square lattice, far too sparse to read as a disc. **That is why the picture corpus
now comes back clean for a different reason than CARD-241 recorded**, and both readings are asserted:
4236 regions at grey 128, 4087 at grey 208 — fewer, because the cells merge.

**The re-measured tolerances and margin** (AC-2, AC-3), against CARD-241's figures:

| measurement | at grey 128 | at grey 208 | set by |
|---|---|---|---|
| margin (whichever tolerance binds) | 1.8859 | **1.8182** | 99x94 block `(144,1266,242,1359)` / 7x11 letter stem `(2181,477,2187,487)` |
| carried by | `fill` | **`aspect`** | |
| `ROUND_FILL_TOLERANCE`'s own room | 1.8859 | **1.8859** | the same 99x94 block |
| `ROUND_ASPECT_TOLERANCE`'s own room | 2.2727 | **47.1809** | letter stem / a 981x94 rule |

So the margin falls 3.6 % and changes hands, `fill`'s room on the book is **untouched** (the 99x94
block is a hard-edged rectangle with no grey edge to grow by), and `aspect`'s room *widens*, because
the stem that set it grew a grey pixel and left the fill tolerance altogether. **AC-2's 1.8 floor
holds at 1.8182** — 1 % of headroom, which is tight by construction and is what the floor is for;
mutant M8 kills it at exactly `1.7818 >= 1.8`. Both tolerances therefore **keep their values because
the measurement says so**, which AC-3 allows. AC-4's canvas boundary cases were re-run at both
thresholds and are **identical at each** — pentagon 0.8704 not round, hexagon 0.9584 round, the
rounded rectangle flipping exactly once between r=14 (1.1339) and r=15 (1.1127), the whole disc sweep
0.9614..1.0076, and the non-monotone sub-7 px table (1 none, 2 ✗, 3 ✗, 4 ✓, 5 ✓, 6 ✗, 7..11 ✓)
unchanged — because `ellipse`, `polygon` and `rounded_rectangle` do not anti-alias. That is now
asserted rather than assumed (`assert at_level[INK_LEVEL] == at_level[MARK_LEVEL]`).

**The residue, measured with a control each** (AC-5). `MEASURED_MARK_BOUNDS` is eight rows, every
verdict derived by execution and every row paired with the mark the check *does* report. `darkness`
is gone and three narrower rows replaced it, each a measured crossing:

| bound | missed | control, found |
|---|---|---|
| `lightness` | a flat tone at grey 208 | grey 207 — the crossing is **one level wide** |
| `colour` | pure yellow, luminance 226 | pure red, luminance 76. (Pure cyan, 179, was missed at grey 128 and is found now — a second instance this card closes) |
| `opacity` | black composited at alpha 40 → tone 215 | alpha 64 → tone 191 |
| `hollow`, `touching`, `footprint`, `resolution` | CARD-241's, unchanged | unchanged |
| `unrendered` | a disc on the cover, absent from the guard's verdict | the metric finds it on the cover |

`unrendered` is now the **only** respect in which CARD-228's static walk is the wider instrument.
**One candidate bound was refused by measurement**: "anti-aliased edges below the threshold" is not
reachable, because a typed `chr(0x25CF)` rasterises a fully black core at every face from 4 px to
40 px (darkest pixel 0; 7 of 10 pixels already under grey 128 at a 4 px face) —
`test_a_typed_mark_always_leaves_a_black_core` records that rather than the judgement.

**Mutants** (byte copies taken first, baseline confirmed green, every restore verified byte-identical):

| # | mutant | verdict |
|---|---|---|
| M1 | `MARK_LEVEL` 208 → 128 (the widening undone) | **KILLED** — 16 tests, incl. both AC-1 pairings and `test_the_struck_bound_and_the_closed_route_agree` (route reopened, record struck) |
| M2 | `MARK_LEVEL` → 161 (above the grey, not the midpoint) | **KILLED** by the palette derivation and by R3's reach test |
| M3 | `BOUND: darkness` reinstated in `round_ink.py` with the route closed | **KILLED** by the agreement test **and** the list equality — the other direction |
| M4 | `BOUND: darkness` reinstated in ADR-0036/R3 with the route closed | **KILLED**, same pair, per text |
| M5 | `round_marks` default back to `INK_LEVEL` | **KILLED** by the inverted control and two bound probes |
| M6 | `_flat_tones` drops the equal-components filter | **KILLED** — `GUIDE_BASIC_RULE_CLUE = (3,2,1)` is read as a colour |
| M7 | `BookInk.unaccounted` read at `INK_LEVEL` | **KILLED** by all four AC-1 tests and the agreement test |
| M8 | `_distance_from_round` x0.98 | **SURVIVED, then KILLED** — see below |
| M9 | `fill_headroom` over every region, not the aspect-inside ones | **KILLED** at `0.1035 == 1.8859` |
| M10 | the `lightness` probe drawn one level darker | **KILLED** at `True == False` |
| M11 | `widened_pixels` counted as zero | **KILLED** by both non-vacuity floors |
| M12 | the grey plants painted in `INK` | **KILLED** by the pairing — the black instrument would have found them |
| M13 | `mark_regions` reads at `INK_LEVEL` | **KILLED** by the inverted control |

**M8 found a real defect in my own fix, which is the one worth reading.** The three-number harness
(`margin`, `fill_headroom`, `aspect_headroom`) had inlined the two tolerance ratios, leaving
`_distance_from_round` referenced only by a docstring: a second definition of the formula whose
literal claim — "`margin` is `_distance_from_round` for the closest region" — was no longer true, and
a scaled mutant of the helper changed nothing. Fixed by one definition, `_off_tolerances`, that both
the margin and the two headrooms are derived from; M8 then kills at exactly `1.7818 >= 1.8`.

**Cost** (AC-6, `meta/profiling/card-243-two-threshold-cost.md`), as a before/after pair on this host
with CARD-241's state restored from `git checkout HEAD --` for the before column, three runs each —
and that column **reproduces** CARD-241's recorded figures (4.57–4.78 s vs 4.80 s; 6.03–6.24 s vs
6.33 s; 842–853 MB vs 836 MB), which is what lets the comparison be made at all:

* `-k RoundMarkOnThePage`: **4.66 s / 33 tests → 10.44 s / 62 tests** (+5.8 s, **x2.2**)
* the whole file: 6.13 s / 121 → **11.83 s / 150**
* peak RSS: 842–853 MB → **863–870 MB** (+17 MB, +2 %)
* share of the 930.81 s suite: 0.5 % → **1.1 %**
* attribution, measured rather than apportioned: **+3.7 s** is the second read plus the boundary
  shapes re-run at both thresholds (38 tests, 8.40 s), **+2.0 s** is this card's new classes. Per
  page the second read costs ~19 ms against the first's ~21 ms and **0 MB of peak** (555→555 MB in a
  standalone process) — the peak is still the materialising `interior_pages` call at ~35 MB a page,
  so CARD-241's attribution survives unchanged.

The card's own estimate ("roughly doubles the measurement half and is still ~1 % of the suite") holds
exactly. Not marked; it runs on every commit.

**Guardrails.** G-1 CARD-228's static walk and CARD-241's black-ink control are both intact — the
control is *inverted at the guard's level and kept whole at CARD-241's* (`ink_regions(grey) == []`
and `round_marks(grey, INK_LEVEL) == []` still assert the miss; `round_marks(grey)` now asserts the
find). G-2 the glyph is untouched. G-3 no `src/**` change at all; the plants read `_SOLVED_GRID_GRAY`
from the production module and the threshold is derived from the package's palette on disk. G-4 no
new dependency, no `hypothesis`; the one new corpus floor (`PICTURE_MIN_WIDENED_PIXELS`) is asserted
inside the test. G-5 `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw` is not in the
diff. G-6 nothing under `meta/profiling` was re-measured or re-frozen; the note is card-scoped.
G-7 every row of `MEASURED_MARK_BOUNDS` carries a control that can fail, and M10 shows one failing.

**Tests.** `tests/test_book_difficulty_dots.py` 121 → **150 passed**. Also green, unchanged:
`test_book_interior_type_floor.py`, `test_suite_profile.py`, `test_guard_integrity.py`,
`test_cli.py` (799 passed together), and the nine `page_ink`/`two_up_ink` consumers (424 passed).
CON-020 was checked rather than inherited: `test_book_interior_type_floor.py` reads no ink threshold
at all, so nothing there moves — what *did* enter the measured population is the type's own
anti-aliased greys, 76 347 pixels of them on the baseline interior, and the measurement says none of
them reads as round. **The full suite was not run** (owner's standing instruction; CARD-222 running
concurrently in a sibling worktree).

**Open for the merge gate / architect station.** `trace.yml` is still untouched, as CARD-241 left it.
This card changes R3's *reach* rather than adding a rule, and the Architecture-context note asks that
the trace question be settled at the architect station rather than a third time here — so it is not
settled here, deliberately.
- [Scope] tests/helpers/page_ink.py, tests/helpers/round_ink.py, tests/test_book_difficulty_dots.py, meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md, meta/profiling/card-243-two-threshold-cost.md
- [Scope gate 1/3] IN_SCOPE, with one recorded drift. **No `src/` file in the diff at all** (G-3 holds structurally), and the glyph is untouched (G-2). `meta/profiling/card-243-two-threshold-cost.md` is outside `Touches` — **not a breach**: AC-6 requires the cost "measured and recorded in `meta/profiling/`", so the card was cut to write it and `Touches` simply failed to list the directory. Identical prediction defect to CARD-241's, and recorded the same way.
- [Guard] ⚠ **The implementation committed `meta/kanban/cards/CARD-243.md` into the branch**, deviating from the brief. Caught before merge and reverted to the base version, so the branch no longer carries it. This mattered: the worktree's copy read `Status: ready`, `Wave: —`, `Started: —`, so merging it would have **reverted the orchestrator's stamps on main** — precisely the replay the "never commit `meta/` from a worktree" convention exists to prevent. The agent's reason for committing the *other* two meta paths is sound and they were kept: AC-4 requires the ADR edit to be in the same diff that closes the route, and a test reads the ADR text back. Its notes were extracted and synced by hand instead.
- [Build gate] PASSED (full, 952s; **7843 passed**, 9 skipped, 0 failed, 0 errors, exit 0). Arithmetic exact: 7814 (main after wave 43) + 29 (`test_book_difficulty_dots.py` 121 → 150). Ran under `meta/kanban/.full-suite.lock`, released immediately.
- [Verified by the orchestrator, not read] The threshold is **derived and pinned**, not picked: `ceil((160+255)/2) = 208` from the package's own flat-tone palette `{0,160,255}`, and the literal is held to that derivation by a test (`MARK_LEVEL == -(-(lightest_mark + paper) // 2)` over tones walked from `src/nonogram/**`). The route is closed and CARD-241's control survives: a grey-160 disc gives **0** round marks at `INK_LEVEL` 128 and **1** at `MARK_LEVEL` 208, while a black disc is found at **both** levels.
- [Review 1/3] Score: **9.0** ✓ threshold reached + no critical/important **on cycle 1** (0 crit, 0 imp, 3 minor, 4 out-of-scope). Risk LOW, lane FAST. Report: `meta/review/20261017T150301Z-CARD-243-cycle1.yml` (passes `yaml.safe_load`).
- [Review sync] 1 report → meta/review/
- [Review 1/3] Step 8h: **15 rules checked, 12 ✓ holds, 3 ⚠ unchecked (`no_eligible_fact`: CON-005, CON-009, CON-010), 0 ✗ violated.** All 12 test-kind `check:` refs verified live in the tree.
- [Review 1/3] Step 8f mutation check **RUN** (5 mutants, 5 killed, targeted on `MARK_LEVEL`'s derivation, `_off_tolerances` and the `MEASURED_MARK_BOUNDS` controls), on a green scratchpad copy with the baseline confirmed first.
- [Review 1/3] **The margin question was answered by measurement rather than deferred.** 1.8 is the right floor: the false-positive boundary is 1.0, the measured margin is 1.8182, and the book's population is **empty in between** — histogram at grey 208 reads 1.8182 ×16, 1.8859 ×1, 2.1749 ×84, 2.2770 ×878 — so the floor sits in a gap, not on a cliff. The hand-change from `fill` to `aspect` is **understood, not incidental**: the stem setting the aspect room at 128 is 6×11 (off-aspect 2.2727, fill inside tolerance), at 208 it is 7×11 (off-aspect 1.8182, off-fill 1.1675 — outside), so it stops setting the room and starts setting the margin, while the 99×94 block is literally unmoved (fill room 1.8859 and box identical at both thresholds). What can erode the remaining 0.018 is **not drift but a new raster** — the quantities are quantised, and one more pixel of stem width (8×11 → 1.364) reds the floor while the guard is still 36% clear of a false positive. With the interior-redesign amendments already on main, the next card touching page type will probably red it: that is the tripwire working, which is why F-001/F-003 only ask that it fail with the right message.
- [8h spot-check] **3/3 sampled holds reproduced** — by the orchestrator's own measurement rather than a skeptic subagent (recorded deviation, consistent with this wave). Shadow copy with `CLAUDE.md` included and its baseline confirmed green **before** any mutation. (i) All three load-bearing rules' check tests pass on this head: ADR-0036/R3's `test_the_books_own_pages_carry_no_undeclared_round_mark` (1 passed), ADR-0039/R1's `test_the_control_for_each_spelling_depends_on_the_set` (13 passed), ADR-0039/R3's `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw` (1 passed). (ii) **The holds depend on the card's mechanism, not on luck**: reverting `MARK_LEVEL` 208 → 128 reds **16 tests**, including both grey-route plants, `test_a_mark_in_the_books_own_grey_is_measured_and_was_not`, `test_the_black_ink_only_instrument_misses_the_same_plant`, the seeded picture corpus, the tolerance-room measurement and the `opacity` bound.
- [AC/EC check] **All criteria/constraints ✓** (evidence) — AC-1..AC-6 and G-1..G-7, **13/13 demonstrated**, no contradicted / partial / unverified. Scratchpad copy built with `git archive HEAD | tar -x` (CLAUDE.md included) and confirmed green at 150 passed before any mutant; every mutant reverted and `diff`-verified. Ten independent mutants, each red where it must be: plant tone, collapsed thresholds, broken `finally`, `MARK_LEVEL`→128, `MARK_LEVEL`→200, `BOUND: darkness` re-added to each text separately, a row's `caught` flipped, a row's control weakened to a mark that is missed, a row renamed off its marker, `_bounds_carried_by` neutered, tolerances loosened.
- [AC/EC check] Three verifications worth keeping, because a weaker gate would have accepted them instead:
  - **AC-3's premise was checked, not assumed.** Tone histograms enumerated per primitive: `ellipse`, `polygon`, `rounded_rectangle`, `line`, `point` all render exactly `[0, 255]` — no intermediate tone — so the canvas boundary cases genuinely are identical at 128 and 208 and the tolerances were re-derived against the right population. Noted honestly: the premise is **false for `draw.text`**, which anti-aliases, and the card does not claim otherwise (the typed-dot row is measured separately).
  - **The refused bound was judged, not inherited.** `chr(0x25CF)` measured at every face 1–40: darkest pixel 0 at every face ≥ 4, and 110 / 79 / 19 at faces 1–3 — still under grey 128. So there is no face at which a typed mark is *only* above-threshold anti-aliasing, including below the swept range; a LANCZOS-downscaled (genuinely anti-aliased, 7–41 tones) disc is found at both thresholds; and a disc whose whole raster is ≥ 208 is missed, which is the `lightness` row the refusal points at. Unreachable as phrased, nothing reachable dropped.
  - **G-5 at AST level**: all three mandatory-rule check tests byte-identical *and* AST-identical to `721fda8`, enclosing class byte-identical, and all eleven of CARD-228's walk helpers unchanged.
- [AC/EC check] AC-2's changed pass reason is **asserted, not narrated**: the picture corpus now passes because the grey rules merge the lattice (regions 4236 → 4087), and the claim is pinned as `ink.at[MARK_LEVEL].regions < ink.at[INK_LEVEL].regions`, which reds the moment that stops being true. Non-vacuity probed independently: loosening both tolerances reds 5 of the 6 AC-2 tests, so the book is quiet because of the measurement rather than because the guard cannot fire.
- [Docs] SKIPPED deliberately, same reason as CARD-242: the card changed `tests/` only, and rewriting `tests/README.md` (~20 waves stale) is an **open owner decision** in `meta/kanban/backlog.md` — "either make 'no per-directory READMEs' the convention and drop the step, or create them once". Not this card's to settle.
- [Minors carried, not fixed — 4 open, none gating] Deliberate choice: the gated tree is the tree that merges, so nothing was edited after the gate (the "merged state must equal the reviewed state" property this wave enforced on CARD-241). (1) `tests/test_book_difficulty_dots.py:3836` — the widened margin's box assertion pins one member of a **16-way tie** of 7×11 letter stems, so any text added ahead of it on page 0 flips the box and the failure reads "no longer carried by aspect", which is not what happened; assert the tie class instead. (2) `:3391` — `_flat_tones` collects only *equal* int triples, so an unequal module-level triple (e.g. `(230,225,235)`, luminance 227) would be invisible and the derivation test would not red; true on this head (verified: every 3-int literal in `src/nonogram` is `INK`, `BACKGROUND`, `_SOLVED_GRID_GRAY` or a non-colour) but a true claim whose guard would not notice it becoming false — CARD-241's F-001 shape, one class narrower. (3) `:3808` — the 1.8 floor's assertion message should make the expected failure mode legible (a drop to ~1.3–1.7 is a type-raster change to re-derive; only a drop toward 1.0 is a guard problem). (4) **`tests/helpers/round_ink.py:248-252`** — `ROUND_ASPECT_TOLERANCE`'s rationale still reads "a letter stem at 0.545" with no threshold named; that is the @128 figure, and at the deployed threshold the binding mark is a rule at aspect 10.436. **This fourth one is the card's own RC-1 family** and is the first to fold in whenever the file is next opened.
- [Merged] `1280085` (merge commit) over impl `e87abfc` (rebased from `9014b5d`). **Merge gate on the exact tree that ships: full suite 7843 passed, 9 skipped, 0 failed, exit 0** — identical to the build gate, because main's only movement in between was kanban bookkeeping with no test impact.
- [Merged] The ADR-0036 edit and the profiling note were carried **inside the commit**, not by hand: AC-4 requires the ADR text struck in the same diff that closes the route, and a test reads that text back. Validator after the merge: **0 errors / 92 warnings**, unchanged.
- [Merged] **The gated tree is the merged tree** — nothing was edited after the AC/EC/G gate, including the one Minor that is this card's own RC-1 family. That property is deliberate: CARD-241 earlier this session nearly merged a state its gates had never measured, and the lesson was not to re-introduce the gap for a two-line convenience.
