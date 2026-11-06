# CARD-379: The pre-flip reds that can go green BOTH ways — carved out of CARD-322 so the flip card is not 5c

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/379-pre-flip-green-both-ways
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-379
**Source:** CARD-322's premise pass, 2026-11-06 (report kept at `~/Documents/nonogram-reviews/CARD-322/premise-pass/REPORT.md`), split on the owner's instruction "split it and start the pre-flip card". CARD-322 as written priced at `5c (2.5d)` against the board's `sizing.max_estimate` of 1d; the part of it that needs NO `src/` change and NO owner decision is this card, and it follows the module-slice pattern of CARD-354 to CARD-360.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/property/test_book_export_interior.py, tests/test_book_interior_type_floor.py, tests/test_book_pdf_memory.py, tests/test_book_interior_face.py, tests/test_book_pdf.py
**Review score:** —
**Started:** 2026-11-06T04:28Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-322 flips ADR-0042/R1 and converts the last five interior kinds. Its premise pass (2026-11-06) measured that, under the five-kind probe, 94 tests are red in 10 of 21 modules while EVERY module is green unlifted, and that part of CARD-322's residue is the same kind of work CARD-354 to CARD-360 did: tests that can be made to go green BOTH on today's tree and on the end-state tree, with no `src/` change. Doing that first (a) shrinks the flip card to what genuinely needs the flip, (b) lets the flip card's census start from a tree where these reds are already gone, and (c) is the only part of CARD-322 that needs none of the owner's open decisions.

**This card does not flip anything.** It must leave every module green UNLIFTED (as today) and green under the five-kind PROBE, for the sites it owns.

## The population it owns (18 reds, measured by the premise pass at `51bbf6cf`, a carried figure until you re-derive it)

| site | reds | cause | where |
|---|---|---|---|
| `monkeypatch.delitem` meeting a key the probe already removed | 5 | `KeyError: PageKind.TITLE` in `TestInteriorReadings_TheStreamArmIsReached` | `tests/property/test_book_export_interior.py` |
| the same, one site | 1 | `KeyError: PageKind.TITLE` in `test_lifting_a_declaration_makes_the_stream_arm_read_that_page` | `tests/test_book_interior_type_floor.py` |
| the same, 7 reds | 7 | `delitem` KeyErrors | `tests/test_book_pdf.py` (ONLY those; see Guardrails) |
| expected-side gap (M2) | 1 | "interior page 2 is written as operators but no vector guide writer" in `test_PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage` | `tests/property/test_book_export_interior.py` |
| `_write_pdf` representation refusal (M3) | 2 | "page 1 is a vector puzzle page, but arrived as Image" in `test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer` and `test_a_producer_that_yields_too_many_is_refused_before_the_extra_page` | `tests/test_book_pdf_memory.py` |
| unowned (no card named them) | 2 | "pages that differ ... must be exactly the seven" (moved: [5, 7, 9, 11]) and "no band was drawn" | `tests/test_book_interior_face.py` |

The `delitem` figures are a CENSUS count of REDS; the SITE count is a different quantity (17 sites in the tree, 2 with `raising=False`, 15 able to raise, 2 of those naming `DIVIDER`, which is not lifted; two sites in `tests/test_book_pdf.py` are `delitem` calls inside `for kind in self._interior_kinds()` loops covering 4+ kinds each, so one site is more than one red). Take the red count from `scratchpad/card338/census_five_kinds.py` and the site count from `scratchpad/card338/derive_delitem_sites.py`; never divide one into the other. `scratchpad/card338/fidelity_to_the_end_state.py` measured the same 13 `delitem` reds on a tree whose five registry entries are deleted in `src/` with no probe loaded, so they are CARD-322's end-state residue and not the instrument's shadow.

## What to implement

1. **The `delitem` sites (13 reds: 5 + 1 + 7).** Make each `delitem` site safe when the key is already gone AND still meaningful when it is present: the pattern CARD-354 to CARD-360 used for tests that read both media. Say per site which you chose and why (for example `raising=False` only where the test's claim is about the key being absent afterwards; a lift through a fixture where the claim needs the key present first). A site whose claim is "removing this kind's declaration makes the stream arm read that page" (`test_lifting_a_declaration_makes_the_stream_arm_read_that_page`) must keep its meaning under the probe, where the declaration is already lifted: re-express it, do not weaken it, and plant its failure. Two `delitem` sites name `DIVIDER`, which is not lifted: they are not red today and must stay meaningful.
2. **M2, the expected side.** The expected page for the guide comes from the assembled path (`generator.pages.guide`; the `vector_guide_page` the red message names does not exist, and the message still names CARD-309). **CARD-359's review measured that when the guide-page abort closes, the FIRST `export_interior` test reds at `_measured` and at its answer-page `drawing_of(page).left` reads with `page 6 draws its puzzle at 12.446 mm, not 12.700 mm`: a 3 px (0.254 mm) ink-first-line gap against the 0.1 mm bound, the same family CARD-359 fixed in `test_PropertyTest_BookExport_ParityCountsFromTheTitlePage` with `frame_centre_of(...).frame_left`.** Convert those reads to `frame_centre_of`. Do not widen the 0.1 mm bound (G-2). Record each declared bound's residue IN THE TEST.
3. **M3, the `_write_pdf` refusal in `tests/test_book_pdf_memory.py`.** The two tests hand `_write_pdf` a producer whose first page is a vector puzzle page that arrives as a bitmap. Make them green both ways with the SAME test names and the module's single `setrlimit(RLIMIT_AS)` skip still exactly one. The premise pass suggested filing the bitmap under `DIVIDER` as CARD-354 did: CARD-354's record mentions that once; READ it and say whether it applies, do not assume it.
4. **`tests/test_book_interior_face.py`, the 2 unowned reds.** Read each cause line (the pass measured them as moved page indices and a missing band under the probe, 17 passed unlifted); re-express against the content stream or retire with a NAMED survivor (ADR-0042/R6), each with a plant and a matched control. They are not CARD-322's and no open card owns them: this card does.
5. **MEASURE ONLY, decide nothing: the difficulty-dot instrument.** `tests/test_book_difficulty_dots.py` (29 reds, the flip card's) re-points a raster arm at "the cover or divider", but a grep suggests `_draw_difficulty_dots` is puzzle-page-only. Measure whether the cover or the divider draws difficulty dots at all, and whether the dot instrument would have ANY raster page to measure once the five kinds are vector. Put the answer in your report; the flip card's author will need it. Edit nothing in that module.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* the red count is stated before and after for each of the five modules and every remaining red is routed or dispositioned; the 13 `delitem` reds, the M2, the 2 M3 and the 2 `interior_face` reds are gone, and the reds that remain in `tests/test_book_pdf.py` are exactly the flip card's (32 raster-reading cells, 7 registry assertions).
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.**)
- **AC-2** *Given* the five modules this card touches, *then* each is green UNLIFTED and green under the PROBE for the sites it owns, with every skip attributed by reason (the one `setrlimit` platform skip in `tests/test_book_pdf_memory.py` stays exactly one).
  (check: review-lens)
- **AC-3** *Given* the end state (the five entries deleted in `src/`, no probe, in a private clone), *then* `scratchpad/card338/fidelity_to_the_end_state.py` reports 0 `delitem` reds in the modules this card owns.
  (check: review-lens)
- **AC-4** *Given* the guide page's expected side and the first `export_interior` test, *then* each is read from the assembled path and measured with `frame_centre_of`, and the test that holds it is named in your report.
  (test: named by the implementation; state it)
- **AC-5** *Given* the two `_write_pdf` refusal tests, *then* they keep their names and are green both ways.
  (test: `test_a_producer_that_yields_too_few_pages_never_reaches_the_trailer`)
- **AC-6** *Given* the 2 `interior_face` reds, *then* each has a stated disposition, a plant that re-breaks it and a matched control green in the same run, with `0 skipped`.
  (check: review-lens)
- **AC-7** *Given* the difficulty-dot question (item 5), *then* the report states, measured, whether the cover or the divider draws dots and whether the dot instrument would have a raster page.
  (check: review-lens)

## How to measure, and the instruments are not yours to build

**Re-derive your own population before implementing anything** (`-rEfs`; the probe is `scratchpad/card338/probe_five_kinds.py` loaded with `-p`; `scratchpad/card338/census_five_kinds.py --only <module>` per module; `derive_delitem_sites.py` for the sites; `fidelity_to_the_end_state.py` for AC-3; do not rebuild them, and do not edit `classify_reds.py`, CARD-338 is closed). **`tests/test_kill_matrix.py::test_ac7_the_four_arm_grid_of_card_257_reproduces` sits at the 120 s hang-guard ceiling armed: never run that module under the default ceiling, and read an exit 1 with no summary as the guard first.** A killed run leaves `tests/test_db_engine_lifecycle.py` mutated: check `git status` and restore that one file before the next run.

## Guardrails

- **G-1** — **No `src/` change.** If your measurement indicts the generator, that is a finding and a routing, not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass** (`EDGE_TOLERANCE_MM`, `EDGE_TOLERANCE_PX`, `HALF_PIXEL_MM`, the 0.1 mm parity bound).
- **G-3** — **Stay inside your `Touches`.** In `tests/test_book_pdf.py` edit ONLY the 7 `delitem` reds' sites (and whatever a site's own helper needs): the 32 raster-reading cells and the 7 registry assertions are CARD-322's. Do not edit `tests/helpers/*` (`page_ink.py` belongs to CARD-342 and CARD-343). Planting a mutant into another module and restoring it byte-identically (SHA-256 pair) is a measurement and is allowed.
- **G-4** — No test deleted, renamed, skipped or merged, parametrize ids included (derive the node-id set difference with `-o addopts=` against the cut and report it), except a retirement under ADR-0042/R6 with a named survivor listed per node id in your report.
- **G-5** — No new runtime dependency (ADR-0006/R1).
- **G-6** — A full suite needs the board's lock; never set `NONOGRAM_IGNORE_FULL_SUITE_LOCK`, never redirect `NONOGRAM_FULL_SUITE_LOCK`; you do not run the full suite.
- **G-7** — Do not connect to the production database.
- **G-8** — Take no timing measurements and report no durations.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none exists it defaults to **deny** (check: review-lens)
- ADR-0039/R3 — a declared bound carries a reason and a measured residue, written in the test (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the content stream or retired with a named survivor (check: review-lens)

## Worktree notes

(none yet)
