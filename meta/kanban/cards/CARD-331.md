# CARD-331: The difficulty-dot accounting instrument measures a page the product will stop drawing — it needs a vector twin, and nobody owned that

**Status:** in_progress
**Priority:** P1 <!-- RAISED P2 -> P1 2026-10-30, same reason as CARD-329: one of the three prerequisites of CARD-322, and the only one of CARD-309's four causes that had no owner at all before today. -->
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/331-difficulty-dot-instrument-vector`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-331
**Source:** CARD-309's implementation round, 2026-10-30 — cause 3 of the four that blocked its AC-1, and the round's own words about it: *"its vector twin is carded nowhere."* It was the one cause with no owner anywhere on the board.
**Idea:** —
**Wave:** 71 <!-- STAMPED 2026-10-31 at dispatch, opening wave 71 on the owner's pinned order. Measured free of CARD-317: tests/test_book_difficulty_dots.py + tests/helpers/round_ink.py against requirements.yml + trace.yml + two ADRs -- intersection EMPTY. Also free of CARD-329, which waits only because the cap is 2. One of CARD-322's four dependencies. -->
**Created wave:** 69
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_difficulty_dots.py, tests/helpers/round_ink.py
**Review score:** —
**Started:** 2026-10-31T02:39:21+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_book_difficulty_dots.py` with `tests/helpers/round_ink.py` accounts for
the difficulty dots on a puzzle page — **27 assertion cells**, measured by CARD-309's
round. The way it does it is the problem:

- it **monkeypatches `_draw_difficulty_dots`**, the *raster* drawing site, and
- it keys its accounting on **page-image identity**.

On a vector puzzle page that site **is never called**. So this is not an instrument
reading the wrong medium — which is CARD-329's and CARD-330's class of problem. It is
an instrument **measuring a page the product no longer draws**: once the puzzle page
converts, every one of those 27 cells passes or fails for reasons unrelated to
whether the dots are right, because the mechanism it hooks is dead code on that page.

**And that is the quiet half.** A monkeypatch on a function nobody calls does not
error — it simply never fires, and an accounting that never fires can read as
agreement. Per ADR-0039/R2 the right outcome is a **FAILURE**, not a silent pass, and
the current shape gives the silent pass.

**Nothing on the board owned this.** CARD-312 partitions the 321 pixel-reading sites
and would classify this one, but classifying is not building the twin. CARD-322
converts the pages. CARD-299 was test-side but is done. It surfaced only because
CARD-309 implemented the conversion and read the failures per module.

## What to implement

1. **Decide what the dots' claim actually is**, independent of how it is currently
   measured: that the right number of dots appear, at the right place, at the right
   size, for a given difficulty. Write that down first — the existing instrument's
   shape has been standing in for the claim, and a twin built from the shape rather
   than the claim inherits the coupling.
2. **Build the vector-medium accounting.** On a page written as operators the dots
   are drawing operators in the content stream; account for them there, per
   ADR-0042/R6. **Do not monkeypatch a drawing site to do it** — a hook on a
   production function is what tied the current instrument to one medium.
3. **Keep the raster arm working and keep it honest.** The cover and divider stay
   raster (ADR-0042/R2), and the raster puzzle page still exists until CARD-322
   lands. Both arms must be live, and **each must be able to fail on its own
   medium** — an arm that silently no-ops is the defect this card is about.
4. **Make the dead-mechanism case loud.** If a future page's medium changes under
   this instrument again, it must **red**, not pass. That is the card's standing
   contribution and it is AC-4.

## Acceptance criteria

- **AC-1** (the claim is stated before it is measured): *Given* the branch, *then*
  the dots' claim is written in the test module in terms of **what must be true of
  the page** — count, placement, size, per difficulty — not in terms of which
  function was called. (test: `TestDifficultyDots_TheClaimIsAboutThePageNotTheCall`)
- **AC-2** (the vector arm accounts for real dots): *Given* a puzzle page written as
  operators, *then* the dots are accounted from the **content stream** and the 27
  cells' equivalents hold — with the count derived, not listed. (test:
  `TestDifficultyDots_TheVectorArmReadsTheStream`)
- **AC-3** (the raster arm still holds): *Given* a raster puzzle page, *then* the
  existing accounting holds unchanged — and **without a monkeypatch on a production
  drawing site**, or with the monkeypatch's removal justified in one line if it must
  stay. (test: `TestDifficultyDots_TheRasterArmHoldsWithoutHookingTheProduct`)
- **AC-4** (a dead mechanism REDS — this is the card's point): *Given* an instrument
  arm whose mechanism the page no longer exercises, *then* the suite **fails** rather
  than passing quietly. **Two mutants, and they are the deliverable:** one that makes
  the vector arm's accounting source dead (it must red), and one at the edge that
  makes the raster arm's dead (it must red too). A guard that only catches one side
  catches none of the real cases. (test:
  `TestDifficultyDots_AnArmWhoseMechanismIsDeadFails`)
- **AC-5** (both arms can fail on their own medium): *Given* each arm, *then* a wrong
  dot count on that medium reds **that** arm — measured per assertion, because a test
  short-circuits at its first failing assert and a surviving mutant looks identical to
  a never-reached one. (evidence: the per-assertion table in `## Worktree notes`)
- **AC-6** (no page converted): *Given* the branch, *then* no interior page's medium
  changed and `_RASTER_DECLARATIONS` is untouched — the vector arm is verified against
  a page a fixture writes as operators, which the assembly point already makes
  injectable. (test: the existing `test_no_declaration_outlives_the_cards_that_remove_it`, unmodified)

## Guardrails

- **G-1: do not convert any page and flip no rule.** CARD-322 owns the conversions,
  CARD-312 owns R6's flip.
- **G-2: do not touch `tests/helpers/pdf_pages.py`** — **CARD-329's** — or
  `tests/helpers/page_ink.py` — **CARD-330's**. Three cards, three instruments, and
  they were tangled once already.
- **G-3: do not edit `src/nonogram/admin/**`.** If the dots' production drawing is
  wrong on either medium, **stop and raise it**: that is a writer defect with its own
  baselines, and CARD-309's worktree is open on those files.
- **G-4: do not lower a corpus minimum** and regenerate nothing under
  `tests/fixtures/**`.
- **G-5: no test deleted, renamed, skipped or merged**, `parametrize` ids included
  (gate: node-id set difference with `-o addopts=''`). The 27 cells may be
  **re-expressed**, but the node-id set is pinned — if a cell must go, that is an
  escalation, not an edit.
- **G-6: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract

- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0042/R2 — a raster page is declared with a reason, which is why the raster arm stays (check: CARD-298's derived guard)
- ADR-0039/R1 — a claim needs a control that CAN fail (check: AC-4, AC-5 — a silently no-op arm is a claim with no control)
- ADR-0039/R2 — an unanalysable shape is a FAILURE, never a silent pass (check: AC-4, which is this rule applied to a dead monkeypatch)
- COMP-009 — the book production component (check: review-lens)

## Architecture context

- **FR:** FR-030, FR-032, FR-040
- **ADR:** ADR-0042/R2, R6, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** not updated by this card

## Worktree notes

- **[Why this was invisible]** A monkeypatch on a function the page never calls does
  not error — it never fires. So the failure mode is a **silent pass**, and no gate
  could see it until a card actually converted the page and read the failures per
  module. CARD-309's round did that and named it; this card is the only one of its
  four causes that had no owner anywhere.
- **[The 27 is a measurement, not a target]** Re-derive it. The cells may be
  re-expressed into a different shape entirely, as long as G-5's node-id set holds
  and each arm can fail on its own medium.

### [The premise was half right, and the half that was wrong changed the design]

The card says the instrument **passes silently** on a vector puzzle page.
Measured, it does not — and the measurement is what this round is built on.

- **Lifting `PageKind.PUZZLE` out of `_RASTER_DECLARATIONS` reds 27 of the
  module's 155 cells** (`scratchpad/card331/probe_puzzle_vector.py`, a session
  plugin so the declaration is gone before any module imports). Every one of
  the 27 reds at the **same line with the same message**:
  `'ContentStream' object has no attribute 'convert'`, from
  `tests/test_book_difficulty_dots.py:3918`, which is `_interior_ink`'s render
  loop. The accounting never runs at all. So the 27 the card counted *are* the
  cells that fall, and ADR-0039/R2 is satisfied **today** — by accident, by a
  type error whose message names neither a dot nor a dead hook, and before the
  monkeypatch's not-firing can matter.
- **The silent pass is one patch away, and it is the patch a converting card
  will write.** With the declaration lifted *and* the page walk filtered to
  the bitmaps — the obvious medium-tolerant fix,
  `scratchpad/card331/probe_medium_tolerant.py` — **13 of the 27 stay red and
  14 go green**, on a book whose puzzle pages have left the measurement. The
  13 survivors are the floors the author wrote by hand (`plants >= 6`,
  `pages >= 13`, `REGION_FLOOR`). The 14 that go green include
  `test_every_spelling_is_caught`,
  `test_every_route_the_table_says_is_closed_is_caught_on_the_page` and
  `test_the_limits_list_is_exactly_the_routes_no_instrument_closes` — three
  claims about *what the instrument catches*, passing on four answer-page
  bands with nothing saying the puzzle pages are gone.

So the deliverable is **not** a louder exception for a type error. It is the
thing neither probe produced: an arm per `PageMedium`, each naming the
mechanism its reading comes out of, and a guard that reds when an arm's
mechanism stops being exercised — whatever the page object's type is on the
day it stops. With the declaration lifted, the new section's 34 cells report
**exactly 2 red**, both naming the raster arm, its mechanism and the remedy;
the vector arm's 32 are green on the converted tree.

### [AC-5: both arms fail on their own medium, measured PER ASSERTION]

A test short-circuits at its first failing assert, so a surviving mutant and a
never-reached assertion look identical. Each row below is a separate plant,
and the line it reds is the assertion it reached.

| arm | mutant | wrong how | assertion reached and red |
|---|---|---|---|
| raster | MUT-2 | the page arrives as operators | `liveness.alive` (`:6413`) — *"the raster arm … is DEAD: the puzzle page arrived as ContentStream, not a bitmap"* |
| raster | MUT-7 | one dot too few **declared** | `len(declared) == _rank(PLANTED_TIER)` (`:7446`) — the **count** assertion |
| raster | MUT-14 | declared boxes shifted 1 device px (counts still agree) | `_unaccounted(found, declared) == ()` (`:7454`) — the **verdict** assertion |
| vector | MUT-1 | the writer emits an empty stream | `liveness.alive` (`:6413`) — *"0 painted subpaths in the stream"* |
| vector | MUT-8 | one dot too few **declared** | `len(declared) == len(dots.dots)` (`:7080`) — the **count** assertion |
| vector | MUT-15 | declared boxes flipped about the wrong page height (counts still agree) | `_unaccounted(found, declared) == ()` (`:7087`) — the **verdict** assertion |

Both arms therefore reach **three distinct** assertions under three distinct
wrongnesses: liveness, count, verdict. MUT-7/MUT-8 alone would have left the
verdict assertion unmeasured, which is exactly the short-circuit AC-5 names.

### [The full mutant round: 14 killed, 1 declared negative control survived]

`scratchpad/card331/mutate.py`. Every plant located by text with its
occurrence count asserted to be exactly 1; every control measured green in the
same harness run *before* its plant; SHA-256 asserted before the plant and
after the restore; `__pycache__` swept before and after each run;
`PYTHONDONTWRITEBYTECODE=1`; the full environment inherited
(`dict(os.environ, …)`); `-o addopts=` passed as two argv items; and
**0 skipped asserted on the baseline** (189 passed, 0 skipped, 0 failed).

| # | the plant | node it reds |
|---|---|---|
| MUT-1 | the vector arm's source goes dead — an empty stream | `…AnArmWhoseMechanismIsDeadFails::test_each_arms_mechanism_is_still_exercised[vector]` |
| MUT-2 | **the claim's other arm**: the raster arm's source goes dead | `…::test_each_arms_mechanism_is_still_exercised[raster]` |
| MUT-3 | the corpus is shrunk by **one** page | `…TheVectorArmReadsTheStream::test_the_corpus_is_one_page_per_puzzle_of_both_books` |
| MUT-4 | the claim is restated as a statement about a call | `…TheClaimIsAboutThePageNotTheCall::test_the_claim_is_stated_about_the_page_and_names_no_function` |
| MUT-5 | the forbidden-name list is padded with a word that names nothing | `…::test_the_forbidden_names_are_things_that_really_exist` |
| MUT-6 | the raster arm starts hooking a production attribute | `…TheRasterArmHoldsWithoutHookingTheProduct::test_this_arm_hooks_no_production_attribute` |
| MUT-7 | AC-5 raster, count | `…::test_a_declared_glyph_is_found_as_ink_and_accounted_for` + `test_a_wrong_count_on_the_bitmap_reds_this_arm` |
| MUT-8 | AC-5 vector, count | `…::test_a_declared_glyph_is_found_in_the_stream_and_accounted_for` + `test_a_wrong_count_in_the_stream_reds_this_arm` |
| MUT-9 | the Bézier flattening coarsened 32 → 4 | `…::test_the_flattening_costs_far_less_than_the_tolerance_it_is_read_against` |
| MUT-10 | the reader stops refusing a shape it cannot analyse | `…::test_a_shape_the_reader_cannot_analyse_is_a_failure` |
| MUT-11 | the margin is declared (2.0) rather than derived | `…::test_the_closest_a_vector_page_comes_to_a_round_mark_is_derived` |
| MUT-12 | the arm set loses a member: both arms claim RASTER | `…::test_there_is_one_arm_per_medium_the_product_can_write` |
| MUT-13 | **declared negative control**: an arm is renamed and nothing else — it must SURVIVE, because the guard claims one arm per medium and not a set of spellings | (survived, as declared) |
| MUT-14 | AC-5 raster, verdict | `…::test_a_declared_glyph_is_found_as_ink_and_accounted_for` |
| MUT-15 | AC-5 vector, verdict | `…::test_a_declared_glyph_is_found_in_the_stream_and_accounted_for` |

### [The frozen render-heavy set: a hazard met and avoided, with the reason]

`meta/profiling/rank_durations.py`'s `RENDER_API_PATTERN` is a **text** grep
over `tests/**` for eight names, one of them `puzzle_pages` — a plain
substring, so `vector_puzzle_pages` matches it too. The first version of this
round built its corpus through the pairing walk and **reddened two cells of
`tests/test_suite_profile.py`**: `test_the_frozen_render_set_still_matches_
the_grep_that_defines_it` reported `added since freeze:
['tests/test_book_difficulty_dots.py']`, and a second cell re-ran the module
and saw it.

Re-freezing was measured and **declined**, because the blast radius is a
multi-document restatement this card has no measurement for: the file appears
450 times in `suite-durations-20261023.txt`, so adding it to
`RENDER_HEAVY_SNAPSHOT` moves the render-heavy row (554.47 s / 38.88 % / 1391)
and the two rows derived from it in **both** committed hotspots documents,
whose figures `test_hotspots_headline_figures_are_the_scripts_own_output` and
`test_hotspots_embeds_the_deciding_table_verbatim` re-derive — and would make
`suite-hotspots-20261023.md`'s own "render-set drift: none" false until
re-verified.

**CARD-223's precedent in that very list says "added rather than dodged", and
this is not that case.** CARD-223's file was newly rendering and its cost was
new. This file has rendered the interior since CARD-241, is render-heavy in
fact, does **not** match the grep, and its membership is an already-recorded,
owner-visible deferral — `_interior_ink`'s own docstring: *"CARD-241's notes
record why re-freezing the snapshot was not this card's to do (G-5) and what
the next profiling run should record instead."* Adding a second reason for the
file to be in the set while the first is still deferred improves no census; it
unfreezes a recording this round cannot re-derive.

So the corpus was **rebuilt**, not re-spelled: it no longer consults the
pairing walk at all. It composes one vector sheet per puzzle **row** through
`vector_puzzle_page`, from `FIRST_PUZZLE_PAGE` upwards. That is strictly
better on its own merits, which is why it is not a dodge:

- the **row count** becomes the corpus's authority, which is a stronger anchor
  than a pairing verdict — a dropped page is then a dropped puzzle and nothing
  else (MUT-3 reds on one page);
- the sweep grew from 11 pages to **13**;
- consecutive page positions put **both page parities** in it, asserted;
- and a paired sheet carries two bands, which this arm deliberately excludes
  (the two-up page is where the arm goes next, and it is not in this card).

`tests/test_suite_profile.py` is green on this branch (450 cells, 0 skipped)
and the grep finds **0** of the eight names in either touched file.

### [Figures derived this round, and how]

| figure | how |
|---|---|
| 27 red cells on a converted puzzle page | `probe_puzzle_vector.py`, whole module, one count |
| 13 red / 14 green under the medium-tolerant fix | `probe_medium_tolerant.py`, node sets diffed with `comm` |
| vector margin **2.276996** tolerances | derived as `(4/π − 1) / ROUND_FILL_TOLERANCE`; a filled rectangle's enclosed area **is** its box's, so its `fill` is exactly `4/π` at any size. Asserted as a derivation, with the setter's `aspect` asserted exactly 1.0 so the claim "the margin rests on `fill` alone" is measured |
| 13 pages / 588 painted subpaths / 182 shaped | `probe_floors.py`; floors set at 12 / 560 / 170 |
| 91 ink regions on one bitmap puzzle page | `probe_floors.py`, at both measured thresholds (an unsolved page draws no grey); floor 85 |
| Bézier flattening cost **3.96e-4** of the `fill` ratio | 0.999859 at 32 segments, 1.000255 at 256 where it has converged; 0.33 % of `ROUND_FILL_TOLERANCE`, and the test moves the segment count so the measurement is of the flattening |
| **1.1369e-13 pt** worst path-vs-declared disagreement | 200-case seeded sweep of dots on integer pixels; eleven orders inside the 1/1000 pt the stream writes at, which is why the accounting rounds to three places and matches **exactly** rather than tolerating a gap |
| outlined dot: `fill` **0.999851** in the stream, **0.4100** as ink | the two arms' one measured disagreement — a stroked circle's *path* encloses a disc, its *ink* is a ring. Asserted on one glyph, both ways |

### [What was NOT done, and why]

- **The legacy `_interior_ink` hooks stay.** AC-3 allows this with a one-line
  justification: the legacy harness measures the *interior walk*, which calls
  the drawing site itself and hands this file no caller whose return value
  could be read, so removing its spy means rebuilding the walk's accounting
  rather than the hook — which belongs to whichever card re-points those 27
  cells. The **new** raster arm needs no hook at all (it calls the site), and
  an `ast` detector over the arm's own named functions says so, with the
  legacy harness as the case the detector must report (MUT-6 kills it).
- **No page converted, `_RASTER_DECLARATIONS` untouched** (G-1, AC-6); the
  declaration lift exists only as a scratchpad session plugin.
  `tests/test_book_pdf.py` is green (113 cells).
- **No tolerance widened anywhere.** The vector accounting needed none:
  rounding both sides to the stream's own three places is lossless at 300 DPI
  (0.24 pt per pixel is an exact multiple of 0.001 pt), which is derived
  rather than assumed, so a DPI where it stops being true reds.
- **`tests/helpers/pdf_pages.py` and `tests/helpers/page_ink.py` untouched**
  (G-2). `tests/helpers/pdf_vector.py` is also untouched: the vector reader
  went into `round_ink.py`, the declared `Touches` file, and it imports no
  `nonogram`, which is what keeps it the independent second measurement.
- **The two-up sheet is not in the vector arm.** A paired sheet carries two
  bands, so the accounting would become a question about which band a plant
  landed in. Named as the arm's next step rather than half-built.
- **`RENDER_HEAVY_SNAPSHOT` not re-frozen** — see above.
