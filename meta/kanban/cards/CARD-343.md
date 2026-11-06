# CARD-343: A whole-file `pdf_pages` render comes back blank under the probe while the per-page path yields real pixels in the same run

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/343-guide-page-blank-render
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-343
**Source:** Raised as F-2 by CARD-336's round, 2026-11-04, and routed here at the decompose station on the owner's re-cut instruction. CARD-336's round found it while checking that card's own second UNMEASURED PREMISE, stopped rather than guessing, and said so: "Why a whole-file pdf_pages render comes back blank while puzzle_frame's per-page interior_images path yields real pixel readings in the same run is unmeasured. It is not the frame-centre oracle's, whatever it is, and it needs its own owner." This card is that owner.
**Idea:** —
**Wave:** 79
**Created wave:** 74
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_guide_page.py, tests/helpers/page_ink.py
**Review score:** —
**Started:** 2026-11-06T18:56Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## The observation, and it is an observation rather than a diagnosis

Under `scratchpad/card338/probe_five_kinds.py` (CARD-338's five-kind probe), measured by
CARD-336's round on 2026-11-04:

- `tests/test_book_guide_page.py` reports `AssertionError: only 0 pages carried a measurable
  drawing` — `drawing_of` raises `ValueError` on **every** page, so the placed-edge comparison
  further down is never reached at all.
- An independent scratchpad render of the same book through the same path
  (`pdf_pages(export.interior…)`) under the probe reports `ValueError: the page carries no ink
  at all` for **every** page.
- **In the same probe run**, `tests/test_book_puzzle_frame.py`'s per-page `interior_images`
  path yields real pixel readings and only 4 reds.

So two page-source paths disagree completely about whether there is ink on the page, under one
probe, in one run. **Which one is wrong is not established.** That is this card's question.

**This card's premise is an observation, not a mechanism.** Do not start by fixing anything.
Start by establishing which path is lying and why.

## Why this matters beyond one module

`tests/test_book_guide_page.py` also gains **four unrelated reds** under the five-kind filter
(an `IndexError`, an `assert 0 == 1`, "interior page 2 is not titled the guide's own title",
and "no 20-row puzzle page found"). Whether those are the same cause or four more is unknown.
A blank whole-file render would explain some and not others — which is itself a useful test of
any hypothesis.

CARD-336's round originally inherited a routing of this module's single placed-edge cell on an
arithmetic reading (a 2.9449 px residual against a 2 px bound). **That routing is refuted**:
under the five-kind filter that cell is red at a different line by a different mechanism, and
the arithmetic never applies. The card has been re-cut to drop the module.

## What to implement

1. **Determine which path is correct.** Compare what `pdf_pages` and `interior_images` each
   hand to the ink reader, for the same book, in the same probe run. Derive the divergence;
   do not infer it from the error strings.
2. **State whether the probe causes it.** CARD-338's probe rebinds
   `book_pdf_generator.NO_DOWNSTREAM_WRITERS` to `book_interior_vector.DOWNSTREAM_WRITERS`. A
   plausible reading is that the whole-file path assembles pages the probe leaves vector while
   the per-page path rasterises. **If the probe is the cause, this is a probe finding and the
   instrument's refusal set is incomplete** — CARD-338 built it to refuse by name rather than
   read green over a tree it did not change, so a blank render it does not refuse is a gap in
   that guarantee. Report it to CARD-338's mechanism, do not patch around it.
3. **Then, and only then, decide what the four unrelated reds are.** Same cause or separate;
   say which, with evidence per red.

## Acceptance criteria

- **AC-1** *Given* the two page-source paths, *then* the card states which one yields no ink
  under the probe and **why**, derived rather than inferred from the exception text.
  (evidence: the card's own measurement)
- **AC-2** *Given* the finding, *then* it is attributed: either the probe (a CARD-338
  instrument gap, reported there), the module's own fixture, or the generator. One of the
  three, named, with the measurement that distinguishes it.
  (test: named by the implementation; state it)
- **AC-3** *Given* the four unrelated reds in `tests/test_book_guide_page.py`, *then* each is
  classified as the same cause or its own, with per-red evidence, and anything not closed here
  is carded with an owner.
  (check: review-lens)
- **AC-4** *Given* the fix, *then* a plant that makes a page genuinely blank still **reds** —
  the "no ink" reading must remain able to fail for the claim as stated (ADR-0039/R1).
  (test: named by the implementation; state it)

## Guardrails

- **G-1** — **Do not rebuild CARD-338's probe.** Run it. If it is the cause, that is a finding
  reported to the mechanism, not a licence to fork the instrument. Three cards describing one
  instrument is how CARD-309 happened.
- **G-2** — No tolerance is widened to make a blank page acceptable. A page with no ink is a
  real failure; the question is whether this page has no ink.
- **G-3** — No new runtime dependency (ADR-0006/R1).
- **G-4** — Take no timing measurements and report no durations; other work shares the machine.
- **G-5** — **G-8 standing: do not connect to the production database.** `nonogram_poc` is
  never created, dropped, connected to or truncated.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived, not hand-written; where none exists it defaults to
  deny (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)

[Author round, commit `69a52536`] Verified by the orchestrator by git facts only: tip `69a52536`, one commit over the cut `397a80a8`, worktree clean; ONE file, `tests/test_book_guide_page.py` (53 insertions, 2 deletions); `tests/helpers/page_ink.py`, `src/`, `meta/` untouched; no added bare early `return`, skip or xfail. Not re-run by me. Author-reported (all figures the author's, measured this session): PREMISE CHECK on the cut: unlifted 0 red / 49 passed; probed 2 red / 47 passed; fidelity E0 0, E1 7, E2 2, probe 2. **The card's observation was NOT true at this tip**: no whole-file `pdf_pages` render is blank under the probe (20 pages are produced, drawings measured on 11 or more, none of the old symptoms `drawing_of` ValueError / "only 0 pages" / "no ink at all"); the old four unrelated reds (IndexError, `assert 0 == 1`, "page 2 not titled", "no 20-row puzzle page") are also gone since other cards merged (not bisected; the card's old state was not reproduced). The two probed reds were the module's own: (1) `TestGuidePage_TitledHowToSolveNonograms::test_the_search_finds_the_old_title_on_the_old_page` (`assert 0 == 1`): the `old_export` fixture patches `BookPDFGenerator.create_guide_page`, which the page walk calls only when `page_medium(GUIDE)` is RASTER, so with GUIDE vector the "old" export carried the NEW guide; (2) `TestGuidePage_ExtraPageShiftsEverythingByOneKeepingParity::test_every_pages_parity_still_equals_its_own_position` (`(3, 160.5)`), two stacked causes: (a) page 3 (guide page 2) has ruled diagrams that make `drawing_of` return a "drawing" at columns 1081..1790 in the vector medium while the bitmap raises ValueError ("frame but no ruled grid") and was silently skipped; (b) with (a) fixed, the 2.9449 px against the 2 px bound that CARD-336 described reappears: `Drawing.left` is an ink extent and a PDF rasteriser's mitred frame corner puts it 3 px further out, so `(left + grid_right) / 2` moves 1.5 px (raster reading 0.94 px off, vector 2.94 px): the 2 px bound is right for the placement, the READER was medium-dependent. FIX: `old_export` patches `book_pdf_generator.page_medium` to answer RASTER for `PageKind.GUIDE` only and delegate for every other kind (a no-op unlifted); the parity test skips `GUIDE_INTERIOR_PAGES` by name and reads the centre through a new module-level helper `drawing_centre_x` (left boundary from `frame_centre_of(...).frame_left`, right boundary the centre of the border's own measured run; new readings raster 59.5 / -58.5 and vector 58.5 / -59.5 against 59.055 expected, both within 0.55 px); bounds UNCHANGED (`<= 2`, `checked >= 12`, the sign assertion); the only added control flow is one `continue` for guide pages. Node ids 49 -> 49, empty set difference. Mutants (as edited copies, deleted afterwards; each run on the two tests that can react, plain / probed): blank render, drawing 3 px off, mirrored pages, reversed page order, a reader that reads the first page only, a stray black bar right of the border: each reds the parity test in both media; drawing 1 px off: no red either way (inside the 2 px bound, expected); guide-page skip removed: none / parity; old-fixture seam dead: none / old-title test; old page draws the new title or blank: old-title test in both. Counts: tests/test_book_guide_page.py 49 passed unlifted and 49 passed probed; the 13 census modules passed unlifted (test_suite_profile 450, impact_set 34, check_ref_resolution 26, cli 138, kanban_review_record 68, collected_names 13, guard_integrity 167, shared_fixture_controls 62, full_suite_lock 41, browser_fixture_scope 31, naming 40, fixture_integrity 8, card_349_cold_database 25 + 3 skipped). **Inconsistency to resolve at review: the report says fidelity "E2 now 1 red" yet it did NOT re-run the fidelity script after the final edit** (probed pytest 49 passed is its evidence); the probed census modules were NOT run; the other `page_ink.py` importers were not run (the helper is unchanged). Finding for CARD-322: nothing left over from this module per the author (re-check E2). Not done by the author: full suite, `test_kill_matrix`, timings. Not yet reviewed.