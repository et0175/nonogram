# CARD-331: The difficulty-dot accounting instrument measures a page the product will stop drawing — it needs a vector twin, and nobody owned that

**Status:** review
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
**Review score:** 8.5 (cycle 3 of 3 — CERTIFIED; 8.5 → 8.0 → 8.5, two fix rounds)
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
  `'ContentStream' object has no attribute 'convert'`, raised from the
  `page.convert("L")` of **`_interior_ink`'s own render loop** — cited by name,
  because the line number moves and this sentence used to cite one that never
  held it. **What `:3918` actually holds was itself stated wrongly here and is
  corrected 2026-10-31 (cycle 3's F-013):** it is `def banded(...)` at HEAD —
  `return dots` is `:3916` — and `_draw_difficulty_dots = site` at `308bbded`
  and `9a070e26`. The contents claim is **dropped** rather than re-stated at a
  third value, because it is load-bearing for nothing: what matters is that
  `:3918` never held the render loop, which holds at every commit. (Cycle 2's
  own YAML asserted the `_draw_difficulty_dots` reading *at HEAD*, also false —
  so this round inherited a wrong number from the review that filed the
  finding, and the fix is to stop citing contents by line at all.) The
  load-bearing citations do re-derive: `_interior_ink` opens at `:3862`, the
  render loop is `tests/test_book_difficulty_dots.py:3960` at HEAD and `:3942`
  at `308bbded`, and 27 of 27 reds land at `:3960` (fix round 2, F-012 — a line
  number used as a citation fifty lines above this card's own
  explanation of why that does not work). The accounting never runs at all. So the 27 the card counted *are* the
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
day it stops. With the declaration lifted, the new section reports **exactly 2
red**, both naming the raster arm, its mechanism and the remedy, and every
other cell of it green on the converted tree.

> **Fix round 2 (F-011).** That sentence used to read "the new section's **34**
> cells report exactly 2 red … the vector arm's **32** are green". Fix round 1
> added six cells and falsified it, and nothing re-derived it — F-002's root
> cause surviving *outside* AC-5's table. The substance held; the figures are
> **derived** now rather than retyped, and the derivation is the point:
>
> - The section is the **node-id set difference against the merge base**:
>   **195** collected at HEAD, **155** at `b18fd397`, so **40 added, 0
>   removed** (both collected file-scoped, `-o addopts= --collect-only -q`, the
>   base from a `b18fd397` worktree; this is also G-5's own measurement).
> - `scratchpad/card331/probe_puzzle_vector.py` then reports **29 failed / 166
>   passed**, and intersecting its 29 failing node ids with the two sets splits
>   them with nothing left over: **27** are among the 155 pre-existing cells —
>   the bitmap readers of the interior, which is the same 27 the premise
>   correction above counts — and **2** are among the 40 added:
>   `…AnArmWhoseMechanismIsDeadFails::test_each_arms_mechanism_is_still_exercised[raster]`
>   and `…AnArmWhoseMechanismIsDeadFails::test_each_arms_probe_reports_death_when_its_mechanism_goes`.
> - So the section is **40 cells / 2 red / 38 green**, and 27 + 2 = 29 is why
>   the probe's total is 29. All six cells fix round 1 added are in the 38.

> **Fix round 1 (F-006).** That sentence was half true when it was written:
> the mechanism-still-exercised cell carried arm + mechanism + remedy, and its
> sibling — the probe-reports-death cell — red on its live-state loop with
> `f"the {arm.name} arm is not alive"` and nothing else. The second message now
> carries both, and the claim is **machine-checked** rather than restated:
> `…AnArmWhoseMechanismIsDeadFails::test_both_reds_of_this_section_name_the_mechanism_and_the_remedy`
> reads both cells' assert messages off their own source with `ast` and reds if
> either drops `arm.mechanism` or `arm.remedy` (MUT-23).

### [AC-5: both arms fail on their own medium, measured PER ASSERTION]

A test short-circuits at its first failing assert, so a surviving mutant and a
never-reached assertion look identical. Each row below is a separate plant,
and the assertion it reaches is the assertion it reds.

**The table is this module's own data, not this file's prose** (fix round 1,
F-002). `AC5_PER_ASSERTION` in `tests/test_book_difficulty_dots.py` carries
these six rows, and two cells of
`TestDifficultyDots_AC5ReachesADistinctAssertionPerWrongness` derive the claim
off the cells themselves. Each row cites the **cell by name** and the
**assertion by its own source text**, normalised through `ast.unparse` — never
by line number. The first version of this table cited lines, and three commits
later 4 of its 5 distinct line numbers pointed at other code (`:7446` at a
message string, `:7454` at `) -> None:`, `:7080` at `assert margin > 1.0`,
`:7087` at a `filled=` kwarg), because the table was transcribed out of a
`--tb=line` run and the commit that renamed a cell shifted every line below it.
AC-5's substance was never in doubt; its *evidence* rotted, with nothing
re-deriving it. That is the shape CARD-317's F-003 made a standing rule: a
criterion verified only by prose is a visibility regression.

| arm | mutant | wrong how | cell it reds | assertion reached |
|---|---|---|---|---|
| raster | MUT-2 | the page arrives as operators | `…AnArmWhoseMechanismIsDeadFails::test_each_arms_mechanism_is_still_exercised[raster]` | `liveness.alive` — *"the raster arm … is DEAD: the puzzle page arrived as ContentStream, not a bitmap"* |
| raster | MUT-7 | one dot too few **declared** | `…TheRasterArmHoldsWithoutHookingTheProduct::test_a_declared_glyph_is_found_as_ink_and_accounted_for` | `len(declared) == _rank(PLANTED_TIER)` — the **count** assertion |
| raster | MUT-14 | declared boxes shifted 1 device px (counts still agree) | the same cell | `_unaccounted(found, declared) == ()` — the **verdict** assertion |
| vector | MUT-1 | the writer emits an empty stream | `…AnArmWhoseMechanismIsDeadFails::test_each_arms_mechanism_is_still_exercised[vector]` | `liveness.alive` — *"0 painted subpaths in the stream"* |
| vector | MUT-8 | one dot too few **declared** | `…TheVectorArmReadsTheStream::test_a_declared_glyph_is_found_in_the_stream_and_accounted_for` | `len(declared) == len(dots.dots)` — the **count** assertion |
| vector | MUT-15 | declared boxes flipped about the wrong page height (counts still agree) | the same cell | `_unaccounted(found, declared) == ()` — the **verdict** assertion |

Both arms therefore reach **three distinct** assertions under three distinct
wrongnesses: liveness, count, verdict. MUT-7/MUT-8 alone would have left the
verdict assertion unmeasured, which is exactly the short-circuit AC-5 names —
and that is now derived rather than told:
`test_the_count_and_the_verdict_are_two_assertions_not_one` requires the count
and the verdict to be **two distinct assert statements of one cell** with the
count strictly **earlier**, so a fused `assert count and verdict` reds (MUT-22)
instead of satisfying every row.

### [The full mutant round: 23 killed, 1 declared negative control survived]

`scratchpad/card331/mutate.py`. Every plant located by text with its
occurrence count asserted to be exactly 1; every control measured green in the
same harness run *before* its plant; SHA-256 asserted before the plant and
after the restore; `__pycache__` swept before and after each run;
`PYTHONDONTWRITEBYTECODE=1`; the full environment inherited
(`dict(os.environ, …)`); `-o addopts=` passed as two argv items; and
**0 skipped asserted on the baseline** (**195** passed, 0 skipped, 0 failed; 189 before fix round 1 added six cells). **28 plants, 27 killed, 1 declared survivor** — MUT-25 to MUT-28 are fix round 2's.

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
| MUT-13 | **declared negative control**: an arm is renamed and nothing else — it must SURVIVE, because the guard claims one arm per medium and not a set of spellings. That is **half** the reason. The other half, and the one that makes the survival unambiguous rather than a claim narrowed to fit: `InstrumentArm.name` feeds the `ids=` of this class's two parametrized cells, so a rename moves a node id from `[raster]` to the new spelling — caught by **G-5's node-id gate**, a different instrument at a different layer. A rename is caught; it is caught *there* rather than here, and the cell's own docstring now says so | (survived, as declared) |
| MUT-14 | AC-5 raster, verdict | `…::test_a_declared_glyph_is_found_as_ink_and_accounted_for` |
| MUT-15 | AC-5 vector, verdict | `…::test_a_declared_glyph_is_found_in_the_stream_and_accounted_for` |
| MUT-16 | the page extent the vector accounting flips y about drifts from the stream's own | `…::test_the_page_extent_this_arm_flips_y_about_is_the_streams_own` |
| MUT-17 | **the control's own control**: the raster arm's probe stops noticing that the medium has moved | `…::test_each_arms_probe_reports_death_when_its_mechanism_goes` |
| MUT-18 | **F-004, the reviewer's own M10 re-fired**: the arm hooks a production attribute inside its *plant* function — it SURVIVED cycle 1 at 189 passed | `…TheRasterArmHoldsWithoutHookingTheProduct::test_this_arm_hooks_no_production_attribute` |
| MUT-19 | **F-003**: the reader goes back to *ignoring* `cm`/`Do`/`sh` — the committed cycle-1 behaviour | `…TheVectorArmReadsTheStream::test_an_operator_the_reader_would_misread_is_refused_not_ignored` |
| MUT-20 | **F-003, the binding itself**: the *writer* grows an operator the reader refuses (`stroke_width` emits a `cm`). Reds at the **equality** assertion, `:7497` `emitted == WRITER_OPERATORS_RECORDED` — the writer's surface moving hits that first; **not** at the `collides` assertion, which is where fix round 1 said it died (fix round 2, F-009's class) | `…::test_the_readers_vocabulary_covers_every_operator_the_writer_emits` |
| MUT-21 | **F-003, the other direction**: an operator is recorded as a pass-over the writer does not emit — how that list would absorb the next `cm`. Because the operator planted is `cm`, which is **refused**, it reds at the refused-vs-pass-over **disjointness** assertion, `:7514`, and never reaches `stale` at `:7533` (fix round 2, F-009). MUT-28 is the plant that reaches `stale` | `…::test_the_readers_vocabulary_covers_every_operator_the_writer_emits` |
| MUT-22 | **F-002**: the raster count and verdict are fused into ONE assert — the short-circuit AC-5 exists to measure | `…AC5ReachesADistinctAssertionPerWrongness::test_each_wrongness_ac5_names_reaches_its_own_assertion` + `test_the_count_and_the_verdict_are_two_assertions_not_one` |
| MUT-23 | **F-006**: the second red's message goes back to naming the arm and nothing else | `…::test_both_reds_of_this_section_name_the_mechanism_and_the_remedy` |
| MUT-24 | **F-005**: the raster remedy offers "retire this arm" again | `…::test_no_arms_remedy_offers_an_option_this_section_forbids` |
| MUT-25 | **F-008's other side**: `q`/`Q` are **added** to the refused set, so the non-refusal is measured as load-bearing rather than merely safe. Killed at the row loop's names-its-own-operator assertion, not at the `q`/`Q` box control — with `q` refused, the `Do` row's stream raises on its own `q` | `…TheVectorArmReadsTheStream::test_an_operator_the_reader_would_misread_is_refused_not_ignored` |
| MUT-26 | **F-008 re-fired**: **only** `Do` is dropped from the refused set. Cycle 2 measured this **SURVIVING at 1 passed**; it now reds with *"an external object (Do) passed this reader silently; it reported 0 marks"* | `…::test_an_operator_the_reader_would_misread_is_refused_not_ignored` |
| MUT-27 | **F-008's structural half**: the refusal **stays** and its message stops naming the operator, which is the state that let the `Do` row pass | `…::test_an_operator_the_reader_would_misread_is_refused_not_ignored` |
| MUT-28 | **F-009**: `gs` is recorded as a pass-over the writer does not emit. Unlike MUT-21's `cm` it is in no refused set, so every disjointness assertion passes and `stale` is the one that reds | `…::test_the_readers_vocabulary_covers_every_operator_the_writer_emits` |

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

### [One claim this round wrote and then had to narrow, with the measurement]

The first version of `test_the_page_extent_this_arm_flips_y_about_is_the_streams_own`
was called `test_the_recomputed_layout_is_the_page_the_writer_wrote` and said
that if the recomputed layout drifted, *"every declared dot below would be in
the wrong place and the accounting would still balance"*. Two measurements say
that is wider than the test:

- **the glyph's box does not land on paper.** The band box carries **855 ink
  pixels** on the bitmap and one stroked subpath crosses it in the stream (the
  header rule, at y 722.64 pt ≈ device row 289, which is below the dots at
  rows 215..256 and does not touch them). So a "the box is clear" check — the
  obvious way to hold the recomputation — is simply false here, and the
  accounting does not need it.
- **a page-number drift is invisible to this test.** Taking the spec for the
  next interior position instead leaves the band's centre and the glyph's box
  **bit-identical** (`band_center 1275,236`, `box (154, 165, 438, 306)` on both
  page 4 and page 5): the trim is the same on both parities and
  `header_band`'s `center_x` is `width / 2`.

So the claim was narrowed to the one figure the test really holds — the page
**extent** the y-flip is done against, which MUT-16 reds on a one-pixel drift
and MUT-15 shows matters to the accounting — and the docstring now says out
loud what it does **not** see.

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
- **`RASTER_ARM_FUNCTIONS`' completeness is still underived** (fix round 2,
  N-1). Fix round 1's F-004 extended a **list**, not the mechanism: the guard
  checks that every name listed has a source, and it cannot catch a name that
  *should* be listed — which is exactly the hole cycle 1's M10 used to survive
  (MUT-18 is that hole re-fired, inside a function that *was* listed). Cycle 2
  filed this as a note rather than a finding because cycle 1 had already ruled
  on the shape, and lowered its own confidence accordingly. **CARD-322 is the
  imminent exposure**, being the next card to touch this arm: a function it
  adds to the arm and forgets to list is unguarded, and nothing here says so.
- **The refused set deliberately carries no `cm`/`Do`/`sh` row in the BOUNDS
  cell, and the reason is structural rather than merely defensible** (fix round
  2, N-2). The bounds cell asserts `all(bound.caught is False …)` at `:5780`,
  and a refused operator **is** caught — so adding a `cm`, `Do` or `sh` row
  there reds that cell. Written down because a later reader would otherwise
  "helpfully" add the rows for symmetry, and the red would arrive without its
  reason.

## Fix round 1 — cycle 1 scored 8.5, three Important and four Minor

The review reproduced both halves of this round's premise correction (29/160
and 15/174), confirmed the floors are not self-referential, the node ids
155 → 189 with 0 removed, the validator set-identical, and no tolerance
widened. Its three Important findings were all about **declarations**, not
about the work: two of them one root cause — prose in this diff still carrying
a claim the round's own measurements had retired.

### [F-003 — the reader's vocabulary is bound to an enumeration now, and three operator classes refuse]

The finding's measurement, re-run against the reader **as committed**, and
reproduced exactly:

| stream | the reader, before | the reader, after |
|---|---|---|
| `10 10 20 20 re f` | accepted, 1 mark, box (10,10,30,30) | accepted, 1 mark, box (10,10,30,30) |
| the same rect under `2 0 0 2 0 0 cm` | **accepted, 1 mark, the UNTRANSFORMED box** — bit-identical to no transform | **refused** `StreamShapeError` |
| `q /Im0 Do Q` | **accepted, 0 marks, silent** | **refused** `StreamShapeError`, naming `'Do'` |
| `/Sh0 sh` | **accepted, 0 marks, silent** | **refused** `StreamShapeError` |
| `BI /W 1 /H 1 … ID … EI` | accepted, 0 marks, silent | **refused** `StreamShapeError` |
| `q 10 10 20 20 re f Q` (control) | accepted, 1 mark | accepted, 1 mark, the same box |
| `0 g 0 G 1 w BT … Tj ET /ClueDigit BMC … EMC` (control) | accepted, 1 mark | accepted, 1 mark, the same box |
| `10 10 m 20 20 30 30 v f` | refused | refused |
| `0 0 10 re f` (starved) | refused | refused |

`q`/`Q` are deliberately **not** in the refused set, and that is an argument
rather than an omission. Cycle 2 endorsed the non-refusal and found the
argument **weaker than the truth**, so it is restated at full strength here
and in the reader's own comment: the first version said a saved state moves an
operand only if something moved the CTM *in between*. The "in between"
qualifier is unnecessary — `cm` is refused at **any** position, and `cm` is
PDF's **only** in-stream CTM operator, so for every stream this reader
finishes the CTM is provably the identity from the first token to the last.
The three other routes by which an operand could land somewhere else are each
refused too: a Form XObject's `/Matrix` (reached only by `Do`), an inline
image's unit-square map (`BI`), and a shading (`sh`). So refusing `cm` closes
the `q`/`Q` dependency outright — two of the three facts the reader used to
*depend on* collapse into one refusal, and the third (`write_vector_page`
refuses a `Do`) stops being a dependency at all. And the non-refusal is
load-bearing, not merely safe: adding `q`/`Q` to the set is **KILLED**
(MUT-25).

**The vocabulary is bound to the enumerable authority** (ADR-0039/R2):
`_DOOR_EMITS` from `tests/test_book_solved_answer_key.py`, which *drives* every
public `ContentStream` member and reads what comes out. Its union is 17
operators; `_UNCLASSIFIED_DOORS == ()` is restated here because this claim
rests on it. Every one of the 17 must be **understood**, **refused**, or a
**recorded pass-over**, the three sets held disjoint — and the pass-over list
is held down as well as up, because an entry naming an operator the writer does
not emit is exactly how that list would absorb the next `cm` (**MUT-28**, `gs`
recorded as a pass-over, which is the plant that reaches that assertion;
MUT-21 plants `cm`, which is refused, so it reds one assertion earlier at the
disjointness — fix round 2, F-009).

**Home: `tests/test_book_difficulty_dots.py`, not the co-change peer.** The
reviewer suggested `tests/test_book_pdf_vector_primitives.py` (this diff's one
unguardrailed co-change peer, 5 of 12 months) and the judgement went the other
way, for **four** reasons — cycle 2 ruled the judgement right and supplied the
fourth, which this card had not made: **that module does not reference
`stream_marks` at all**, so the guard would have sat in a module that never
calls the thing it guards (measured: `grep -c stream_marks
tests/test_book_pdf_vector_primitives.py` is 0). The failure mode is an **under-measurement of this
card's accounting** — the vector arm is `stream_marks`' only consumer, and the
symptom is a dot the arm cannot see while liveness stays green on 588 grid-rule
subpaths. Every instrument that would catch a regression in it is pointed at
this module: G-5's node-id gate, the 195-cell baseline, and the mutant harness.
A cell in the peer module would sit outside all three — which is precisely
F-002's defect in a different costume, and sharper than "outside": cycle 2
called this reason accurate because `scratchpad/card331/mutate.py` hard-codes
`MODULE = "tests/test_book_difficulty_dots.py"`, so a peer cell **literally
cannot be a target of this harness**. The cross-module import this costs is
ordinary rather than novel, and fix round 1 understated how ordinary: **93
import statements across 46 files** under `tests/` name a peer `test_*` module
(an `ast` walk over `tests/**/*.py` counting `Import`/`ImportFrom` nodes; 45 of
those files are modules other than this one — which brackets cycle 2's
independently measured 45 files / 95 lines, the residue being statements
counted against lines). And the cell it widens, the
`PAINTS_THAT_FILL`-is-a-subset cell, is already in this module's vector-arm
class, so the general guard sits beside the narrow one it generalises.

### [F-005 — the cross-card contradiction, and what CARD-322 must do]

The raster arm's remedy offered "retire this arm, or re-point it…". **The
first option is not available**, and the card's own guard forbids it:
`PageMedium` has exactly two members and the cover and divider stay raster
under ADR-0042/R2, so an arm set that loses `RASTER` reds
`test_there_is_one_arm_per_medium_the_product_can_write`.

And the contradiction is sharper than the remedy string. `CARD-322.md:118-121`
reads: *"expect to delete raster expectations here, not satisfy them. Same for
**CARD-331**'s raster arm of the difficulty-dot accounting: its lifetime ends
with this card."* So CARD-322 is told to **delete** the arm, this card's guard
reds if it does, and this card's own remedy offered deletion as an option. Two
cards, two instructions, and one of them unbuildable.

**Which half of CARD-322's sentence is false, and why.** The *puzzle page's*
raster expectations do end with CARD-322 — that half is right, and the 27
bitmap-reading cells are exactly what it retires. What does not end is the
**medium**: `PageMedium` keeps `RASTER` because the cover and the divider keep
their bitmaps under ADR-0042/R2 (CARD-322's own text says "**Dividers stay
raster**, unchanged" four lines later, which is the sentence that refutes the
one above it). The arm is an accounting **per medium**, not per page kind, and
the axis it is enumerated on is the thing that survives the conversion.

**The instruction CARD-322 inherits, stated once:** *re-point*, do not retire.
Concretely — keep the raster arm, change its `kind` from `PageKind.PUZZLE` to a
page kind `_RASTER_DECLARATIONS` still declares raster (the cover or the
divider), and move the 27 bitmap-reading cells of this module with it.
CARD-322 is the card that owes the correction to its own line 118-121; it is
not edited from here, because another card's body is its own record. The remedy
string now says only this, and
names the forbidden option as forbidden, so a reader of the red cannot pick it
by accident. `test_no_arms_remedy_offers_an_option_this_section_forbids`
**derives** the forbiddenness — dropping any arm leaves a medium the product
can write unarmed — and then holds every remedy to it (MUT-24).

### [Out-of-scope answers the next card inherits]

- **CARD-227, not CARD-223, is the nearer precedent for the render-set
  refusal — and the refusal survives it.** CARD-227 added a file to
  `RENDER_HEAVY_SNAPSHOT` whose grep match was "a false positive by the grep's
  purpose" anyway, "because the file genuinely renders and the set is there to
  find the files that do" — a criterion `tests/test_book_difficulty_dots.py`
  also meets. What CARD-227 never faced is the **450 occurrences of this file
  in `suite-durations-20261023.txt`**: adding it moves the render-heavy row
  (554.47 s / 38.88 % / 1391) and the two rows derived from it in *both*
  committed hotspots documents, whose figures two cells re-derive, and makes
  `suite-hotspots-20261023.md`'s own "render-set drift: none" false until
  re-verified. CARD-227's file carried no such census. Recorded here so a later
  reader who hits CARD-227 first does not read it as unanswered.
- **The arm never reads a pairing-walk sheet.** Rebuilding the corpus to
  compose one vector sheet per puzzle **row** was strictly better on its own
  merits (a dropped page is a dropped puzzle; 11 pages → 13; both parities in
  the sweep), and it gave up one thing explicitly: no sheet in this corpus
  came through the pairing walk. The two-up arm — correctly not built here,
  because a paired sheet carries two bands and the accounting would become a
  question about which band a plant landed in — inherits that gap as well as
  the two-band question.

### [Figures re-derived in fix round 1, with their bases]

| figure | base |
|---|---|
| **195 passed / 0 skipped** on `tests/test_book_difficulty_dots.py` | the whole module, `-o addopts=`, `-rs`; 189 before this round, +6 cells |
| **27 killed / 1 declared survivor** over 28 plants | `scratchpad/card331/mutate.py`, every control green in the same run (23/24 before fix round 2 added MUT-25 to MUT-28) |
| the writer's measured surface: **17 operators** | the union of `_DOOR_EMITS`, which drives all 18 public `ContentStream` members |
| the validator: **0 err / 90 warn** | `meta/architecture/` is byte-identical to `b18fd397` (`git diff b18fd397..HEAD -- meta/architecture/` is empty), so set-identity is a property of the diff and not of a run. `meta/kanban/config.yml` has since been **re-dated on main** (fix round 2, N-3): it now states 90 as current, re-measured 2026-10-31 after CARD-318 closed ten dead refs, with the stale 2026-10-29 reading of 102 kept and dated beside it. The figure and the file now agree |

## Fix round 2 — cycle 2 scored 8.0, one Important inside F-003's own closure

Cycle 2 closed all seven of cycle 1's findings, each by measurement, and did
not certify because F-003's closure had shipped a refusal row **with no control
that can fail**. It also endorsed three non-actions and corrected three
attributions; the corrections are folded into the sections above rather than
restated here, and the four Minors it filed are fixed in place.

### [F-008 — the `Do` refusal had no control that could fail]

The refusal cell loops over four streams, one per refused operator. The `Do`
row's stream was `q 100 0 0 100 0 0 cm /Im0 Do Q` — **it carries a `cm`**,
which is itself refused, so that stream raised whether or not `Do` was in
`_REFUSED_STATE_OPERATORS`. **`Do`'s refusal was never measured.** Cycle 2
proved it with this harness's own discipline: dropping only `BI` kills,
dropping only `sh` kills, **dropping only `Do` survived at 1 passed** — and
`Do` is one of the three classes cycle 1 measured as *silently* passing
(`/Im0 Do` → 0 marks, nothing raised). A future edit dropping `Do` would have
re-opened exactly that silent pass with the suite green. It is this card's own
AC-5 thesis — a surviving mutant and a never-reached assertion look
identical — turned on the cell fix round 1 wrote, which is why it is Important
and not Minor (ADR-0039/R1).

**The reader was correct; only the test's stream was wrong.** `q /Im0 Do Q`
refuses, naming `'Do'`. That is the row now, and **MUT-26 flipped from
SURVIVED at 1 passed to KILLED**, reading:

> `test_book_difficulty_dots.py:7617: AssertionError: an external object (Do)`
> `passed this reader silently; it reported 0 marks [], and a silent pass is`
> `what ADR-0039/R2 refuses`

**And the structural fix, not just the one-line fix.** Each row now carries its
own operator and asserts the refusal's message **names it**, so a stream
carrying a *second* refused operator cannot stand in for the one the row is
about. All four rows are per-case controls **by construction**, and the next
row added cannot repeat F-008. The plant for that is **MUT-27**: the refusal
stays in place and its message goes generic — killed at `:7609`, *"a transform
(cm) was refused, but by something else in the same stream … and names no
'cm'"*. **MUT-25** is the third plant here: `q`/`Q` added to the refused set,
killed — so the non-refusal is measured as load-bearing rather than merely
safe.

### [The four Minors]

| # | what it was | what it is | what holds it |
|---|---|---|---|
| F-009 | `CARD-331.md` and `mutate.py` credited **MUT-21** with reaching the `stale` assertion. It does not: it plants `cm`, which is refused, so it reds at the refused-vs-pass-over disjointness (`:7514`) one assertion earlier | both attributions corrected, and the assertion is no longer unplanted: **MUT-28** records `gs` as a pass-over the writer does not emit — in no refused set, so every disjointness passes and `stale` (`:7533`) is what reds | MUT-28, red at *"['gs'] are recorded as pass-overs the writer emits, and it does not emit them"* |
| F-010 | `round_ink.py`'s refusal comment claimed *"every other token it does not recognise only sets state"* | **refuted and narrowed.** Measured: `W` clips, so `q 0 0 5 5 re W n 10 10 20 20 re f Q` reads as the **unclipped** (10,10)–(30,30) box; `gs` can set `/ca 0` or an `/SMask`, so an **invisible** mark is reported as a mark. Both *wrong*, not short — this set's own criterion. Neither is **added** to the refused set, and the comment now says why: the vocabulary guard holds the writer's measured surface *equal* to `WRITER_OPERATORS_RECORDED`, which contains neither, so the day the writer can emit one that cell reds before any corpus is read | the equality assertion at `:7497`, which is where MUT-20 dies |
| F-011 | *"the new section's **34** cells report exactly 2 red … the vector arm's **32** are green"* — falsified by fix round 1's own +6 cells, and nothing re-derived it | **derived**: 40 / 2 red / 38 green, from the node-id set difference (195 − 155) intersected with the probe's 29 failing ids. The derivation is written beside the claim | the G-5 collection and `probe_puzzle_vector`, both re-run this round |
| F-012 | `tests/test_book_difficulty_dots.py:3918` cited as `_interior_ink`'s render loop. It **never** carried it at any commit on this branch — `:3918` is `return dots` inside the legacy spy at HEAD and at both earlier commits | cited **by name** (`_interior_ink`'s `page.convert("L")`), with the line dated: `:3960` at HEAD, `:3942` at `308bbded` | nothing mechanical — it is prose, and the remedy is to stop asking a line number to be a citation |

### [Figures, fix round 2, with their bases]

| figure | base |
|---|---|
| **195 passed / 0 skipped** on `tests/test_book_difficulty_dots.py` | the whole module, `-o addopts=`, `-rs`; unchanged by this round, which added no cell |
| **27 killed / 1 declared survivor** over **28** plants | `scratchpad/card331/mutate.py`, baseline asserted at 195 passed / 0 skipped / 0 failed, every control green in the same run |
| **G-5: 155 → 195, 40 added, 0 removed** | node ids collected file-scoped at HEAD and in a `b18fd397` worktree, `-o addopts= --collect-only -q`, sorted and `comm`-differenced. This also settles that the pre-card module was exactly 155 and this card's section is exactly **40** — the number fix round 1's prose had as 34 |
| the new section under the converted tree: **40 / 2 red / 38 green** | `probe_puzzle_vector` reports 29 failed / 166 passed; the 29 intersect the base set in **27** and the added set in **2**, with nothing left over |
| **346 passed / 0 skipped** over the impact set | the set is the **two** test modules that import the changed helper — `grep -E '^(from\|import).*round_ink'` over `tests/` matches `tests/test_book_difficulty_dots.py` (195) and `tests/test_book_solved_answer_key.py` (151), and nothing else; `tests/helpers/page_ink.py` names `round_ink` only in prose. Skips: **zero**, asserted rather than assumed. Cycle 2's own figure was 962 over its own six modules; this is this round's set and its own total, not a reconciliation |
| the cross-module import precedent: **93 statements / 46 files** | an `ast` walk over `tests/**/*.py` counting `Import`/`ImportFrom` nodes that name a peer `test_*` module; 45 of the 46 files are modules other than this one |

### Cycle 3's residue, recorded rather than left implied

Cycle 3 **certified at 8.5** with no Critical and no Important, and filed three
Minors — all prose or comment, none touching a test outcome, a guard, a tolerance or
a figure anything rests on. Their shared root cause is the one this card exists to
fix, which is worth stating plainly rather than filing quietly:

- **F-013** — fix round 2's *correction* to F-012 named the wrong contents for
  `:3918`, at all three commits. Corrected above, and the contents claim **dropped**
  rather than re-stated: citing a line's contents is what failed twice.
- **F-014** — a **shipped** comment claimed `_BEZIER_SEGMENTS` was "reachable from 21
  test modules through the `page_ink` hop". There is no hop; reachability is **2**.
  Retracted in place in the module. The irony is the finding: the refuting measurement
  was made by this same round, three lines away, to justify its impact set.
- **F-015** — the impact-scope basis named round_ink's importers and so covered one of
  the **two** changed files; `tests/test_book_pdf_vector_primitives.py:1453` imports
  `ALL_DRAW_METHODS, VECTOR_STREAM_METHODS` from the changed module and sat outside the
  stated set. Cycle 2 included it; cycle 3 ran it **green**. The basis is corrected
  here: the impact set is *the importers of every changed module*, not of one of them.

**Three rounds of this card produced a wrong line-number or reachability claim, each
time in prose that no control covers.** The pattern is not carelessness — it is that a
figure written into prose has no instrument behind it, which is exactly what AC-5's own
F-002 fix addressed by making its evidence derived data instead of a table. The rule
this card leaves behind: **a number in prose needs either a derivation beside it or no
number at all.**
