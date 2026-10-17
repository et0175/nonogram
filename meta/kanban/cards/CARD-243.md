# CARD-243: The round-mark check sees the greys the book actually prints

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-241's review cycle 1 (2026-10-17), finding F-001 — measured there and confirmed independently by the orchestrator, then narrowed rather than closed by owner decision the same day, so CARD-241 could land with its promise matching its measurement
**Idea:** —
**Wave:** —
**Depends on:** CARD-241 (it owns the instrument, the bound list and ADR-0036/R3's comment this card widens)
**Touches:** tests/helpers/round_ink.py, tests/helpers/page_ink.py, tests/test_book_difficulty_dots.py, meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
