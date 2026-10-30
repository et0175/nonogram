# CARD-230: The guide's worked example runs as four steps, and the rows/columns tip becomes a callout

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 1d
**Revision pending:** true
**Skill:** python-pro
**TDD:** —
**Branch:** card/230-guide-worked-example-steps
**Worktree:** —
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 — "The worked example runs as four small steps, each with one line saying what changed" and "The tip about switching between rows and columns moves to the foot of page 2 as a callout"
**Idea:** —
**Wave:** —
**Depends on:** CARD-229 (the spread and its two-column frame), CARD-322 <!-- ADDED 2026-10-30 on the owner's decision "move from raster to vector first", and it closes a MEASURED HOLE rather than encoding a preference. Re-derived that day: all 10 cards gated by the 2026-10-25 ADR-0042 pass had **zero open dependencies** -- every `Depends on` entry already `done` -- so the ONLY thing holding them was the `Revision pending: true` flag. A flag is cleared by decomposing, which means re-cutting any of these would have RELEASED it into the wave queue ahead of the conversion its tests are supposed to target. This card is one of the 6 whose tests retarget from measuring ink to reading the content stream, and that is a TECHNICAL dependency, not a sequencing preference: the pages must BE streams (CARD-322) and the placed-edge convention must be settled (CARD-330, which CARD-322 already depends on) before an AC here can name a value. Re-cut before that and these ACs get written against a convention that does not exist yet, then need re-cutting again. The board's standing rule is that a sequencing PREFERENCE must not be written as a dependency; this is the other case, so it is. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page.py, tests/test_book_finalise_guide_preview.py, tests/test_book_finalise_guide_preview_layout.py, tests/fixtures/book_baseline_card230.json, tests/test_book_*.py, tests/property/test_book_*.py, tests/helpers/book_corpus.py, tests/helpers/page_ink.py, tests/fixtures/
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Two changes to the guide's content layout, both inside the spread CARD-229 builds.

> **CORRECTED 2026-10-17 at the decompose station — half of item 1 is already shipped.** This
> section claimed "today the worked example is a single figure under `GUIDE_EXAMPLE_HEADING`".
> That is **false, and has been since CARD-167**: `WORKED_EXAMPLE_STEPS`
> (`book_pdf_generator.py:735`) has held **exactly four** `ExampleStep` entries, each pairing a
> caption with its own grid, since commit `205c5e1` — verified by counting the entries at
> `205c5e1` (CARD-167), `5bd85c6` (CARD-201) and `HEAD`: **four at all three**. CARD-201 did not
> change the count. The likely cause of the error is CARD-167's own title, "guide page becomes
> 'How to Solve Nonograms' **with a worked example**" — singular, which reads like one figure
> and is not. The card was written from the title rather than the code.
>
> This matters because it moved four of seven acceptance criteria from "the card's deliverable"
> to "already true" — see the re-cut note under **Acceptance criteria**.

1. **The four steps are already there; this card RE-LAYS them inside CARD-229's two-column
   spread.** What is genuinely yours: their position and reading order within page 2's column,
   that each caption still sits beneath its own grid after the re-layout, and that all four fit
   the shortest trim under CON-018's amended (narrower) margins. **Do not rewrite
   `WORKED_EXAMPLE_STEPS`, do not renumber the steps, and do not re-author the captions** —
   they are shipped teaching copy and G-6..G-8 assert they survive you.
2. **The rows/columns tip moves to the foot of page 2 as a callout** — a distinct block, not a
   paragraph in the flow. **This is the card's real new work.** Today the tip is
   `GUIDE_SWITCHING_HEADING` (:909) and it is **page 1's closing item, text only, no diagram**
   — CARD-201's own comment says exactly that. Moving it and setting it apart is unshipped.

**Where the copy comes from.** The owner's instruction for the whole spread is "your current
text, lightly tightened". **Correction to this paragraph as originally written:** it said "the
four step captions are new sentences, so they are new constants". They are not new — they are
shipped constants, and inventing replacements would both lose the teaching copy and quietly
break G-7. The callout's text is likewise the existing tip **moved, not rewritten**. So on this
card, *every* string should be a move or a tightening and **none should be an invention**; if
you find yourself writing a new sentence, say which and why in the notes, because the default
expectation here is now zero.

**On the estimate.** It stays at 1d and is deliberately not cut, even though item 1 turned out
largely shipped: the re-layout inside a spread that does not exist yet, the callout, and the
fit-at-shortest-trim measurement under narrower margins are the bulk of the risk, and the four
constants were never the expensive part. Flagged here so the retrospective can see the scope
moved without the estimate moving, rather than inferring a mis-estimate.

## Acceptance criteria

> **RE-CUT 2026-10-17 at the decompose station, before dispatch — read this before writing a
> test.** As originally written, **four of this card's seven acceptance criteria described
> behaviour that is already shipped**, and would have gone green on cycle 1 without the card
> changing anything. That is not evidence of this card's work; it is fake coverage, the exact
> shape ADR-0039/R1 exists to forbid (*a coverage claim needs a control that can fail*), and it
> is what the wave-43 retrospective found every gating finding reduced to.
>
> **What is actually on disk today**, verified by reading
> `src/nonogram/admin/book_pdf_generator.py` rather than inferred:
> * `WORKED_EXAMPLE_STEPS` (:735) already holds **exactly four** `ExampleStep` entries, each
>   pairing a caption with its own grid, and the grids already progress — filled
>   `{}` → `{1,2}` → `{1,2,3}` → `{1,2,3,5}`, crossed `{}` → `{}` → `{0,4}` → `{0,4}`, so
>   every consecutive pair already differs. The old AC-1, AC-2 and AC-3 were therefore true
>   before the card began.
> * the generator already draws one line per step (:3666) and the Finalise preview already
>   `zip`s the same constants (:3850) — the old AC-7 was true too, and even cited an
>   *existing* test (`test_book_finalise_guide_preview.py:403`) as its evidence.
> * **the callout is the genuinely new work.** The rows/columns tip exists as
>   `GUIDE_SWITCHING_HEADING` (:909) but is **page 1's closing item, text only, no diagram**
>   (CARD-201's comment says so in those words). Moving it to the foot of page 2 and setting
>   it apart is real, unshipped work.
>
> So the four steps are **not** this card's deliverable. What this card actually does is
> **re-lay that shipped content inside the two-column spread CARD-229 builds, and move the
> tip**. The shipped properties are still worth protecting — CARD-229 rewrites the page under
> them — but they are **guardrails against regression, not acceptance criteria**, and they are
> written below as G-6..G-8 instead.
>
> **One thing I did not verify and you must**: whether the *rendering* puts exactly one caption
> beneath each grid is a layout question I did not measure, only the constants. Measure it;
> do not inherit this note's word for it.
>
> **Every AC below must be shown red before it is green, against a mutant of _your_ diff** —
> not of the shipped code. An AC that cannot be made to fail by breaking something this card
> wrote is misfiled as a guardrail.

- **AC-1** (happy, the steps survive the re-layout in reading order): *Given* the guide's page 2
  as CARD-229's two-column spread lays it out, *then* the four shipped steps are drawn **in
  reading order within the column**, each with exactly one caption line beneath it, and none
  overlapping another. The claim is about **position in the new layout**, which is new; the
  existence of four steps is not.
  (test: `TestGuideWorkedExample_RunsAsFourStepsInTheSpread`)
- **AC-2** (happy, the callout): *Given* page 2, *then* the rows/columns tip is drawn as a
  callout at the foot — below the last technique, visually set apart (its own rule or panel),
  and not inside a technique's column. (test: `TestGuideCallout_SitsAtTheFootOfPageTwo`)
- **AC-3** (negative, it left page 1): *Given* the guide's page 1, *then* the rows/columns tip
  is **no longer** drawn there — the tip moved, it was not duplicated. Without this, a card
  that draws the callout on page 2 and leaves the original in place passes AC-2 while shipping
  the text twice. (test: `TestGuideCallout_NoLongerOnPageOne`)
- **AC-4** (guard, the copy moved rather than changed): *Given* the callout's text, *then* it is
  the existing `GUIDE_SWITCHING_HEADING` constant, read and not retyped.
  (test: `TestGuideCallout_UsesTheExistingTipText`)
- **AC-5** (edge, the four steps fit): *Given* the shortest trim the profile lays out, *then*
  the four steps and their captions fit inside page 2's column without crossing the callout or
  the footer rule. **State the trim you measured**, and say what the margin is — "it fits" with
  no figure is not evidence, and CON-018's amended margins (CARD-222) make the column narrower
  than the shipped page's.
  (test: `TestGuideWorkedExample_FitsTheShortestTrim`)

## Guardrails

- G-1: CON-020's floor holds for the step captions and the callout (test:
  `TestInteriorType_EveryFaceHoldsTheFloor`).
- G-2: The guide stays two pages. Four steps must fit the spread; they do not earn a third page
  (test: **AC-5's** class plus `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`).
  _(Renumbered by the 2026-10-17 re-cut: this said "AC-6's class", and AC-6 no longer exists.)_
- G-3: The example grids are drawn with the same primitives as the puzzle pages' grids, at the
  spread's single example cell size (CARD-229's AC-5).
- G-4: Out of scope — the spread, the key strip and the two-column frame (CARD-229).
- G-5: Baselines re-recorded with provenance; no earlier fixture regenerated or deleted.

**G-6..G-8 are the three claims demoted from the acceptance criteria by the 2026-10-17 re-cut.**
They are shipped properties, so they prove nothing about this card's diff and cannot be
acceptance criteria. They are still worth asserting, because **CARD-229 rewrites the page
underneath them and this card re-lays its content** — so each is a live regression risk, and
each must be red if the re-layout drops it. If you find one of these cannot be made to fail by
breaking your own diff, say so in the notes rather than claiming it as evidence.

- G-6: The worked example still has **exactly four** steps after the re-layout, and each
  consecutive grid still differs from its predecessor by a non-empty change — a step that
  changes nothing is a defect in the lesson. Shipped as `WORKED_EXAMPLE_STEPS`
  (`book_pdf_generator.py:735`), filled `{}` → `{1,2}` → `{1,2,3}` → `{1,2,3,5}`
  (test: `TestGuideWorkedExample_EveryStepChangesTheGrid`).
- G-7: Each caption still comes from the constant **paired with its own step**, so steps and
  captions cannot drift apart. Shipped via the `ExampleStep` dataclass (:714), which is what
  makes the pairing structural rather than positional — do not replace it with two parallel
  sequences (test: `TestGuideWorkedExample_CaptionsArePairedWithSteps`).
- G-8: The Finalise screen's guide preview still shows the same four steps in the same order,
  because it reads the generator's own constants rather than its own copy. Shipped at
  `book_pdf_generator.py:3850` (`zip(WORKED_EXAMPLE_STEPS, worked_example_images)`), and
  already covered by `tests/test_book_finalise_guide_preview.py:403` — **so the existing test
  is the control here, and the honest move is to check it still passes rather than to write a
  new test that claims the credit** (test:
  `TestFinaliseGuidePreview_ShowsTheWorkedExampleStepByStep`).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-230 --root meta/architecture` (58 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **INV-013** — the guide is still two pages, so parity after it is unchanged. As of
  2026-10-17 (commit `91609aa`) those two pages are interior **2 and 3**, not 1 and 2:
  CARD-206's title page occupies page 1 and the guide is a facing spread (CARD-229).

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_52 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-041.
- **CON:** CON-020.
- **ADR:** ADR-0036/R2.
- **Components:** COMP-009.
- **Trace:** not updated by this card.

## Worktree notes

- [AC-2 is the one that makes this a lesson rather than four pictures] "Each with one line
  saying what changed" is only true if something changed. Asserting the grids differ is cheap
  and it is the only assertion here that tests the teaching rather than the layout.
- [Pre-dispatch defect, found at the 2026-10-17 widening pass] ⚠ **This card's "current behaviour" is factually wrong, and the error makes the card look bigger than it is.** It states that the worked example is today "a single figure under `GUIDE_EXAMPLE_HEADING`". Verified against the source: `WORKED_EXAMPLE_STEPS` (`src/nonogram/admin/book_pdf_generator.py:735`) already holds **four** `ExampleStep` entries with captions, `:3666` already draws one per step, `:2410`'s own comment calls them "the four original worked-example steps", and the Finalise preview already renders them step by step (`app.py:4716` exposes `guide_steps`; `book_finalize.html:151-161` renders an `<ol class="guide-steps">` with `.guide-step-caption` styled in `admin.css:333-335`). So **AC-1, AC-3 and AC-7 look like they pass against shipped code**, and the genuine delta is the callout at the foot of page 2 plus the fit at the shortest trim. This is the "an AC can be true, green and evidence nothing, when an earlier card already delivered its outcome" pattern the board already tracks (CARD-221's AC-2). Re-cut the ACs at the decompose station before dispatch, so the card evidences what it actually changes; its `Touches` was widened only 5 → 10 for this reason.

## Architecture revision (2026-10-25)

**Reason:** ADR-0042 (DEC-048) accepted 2026-10-25 — the book interior is written
as PDF content-stream operators; the cover stays raster because it is a
photograph, and the section dividers stay raster for now by owner decision the
same day. The phase that converts the interior is CARD-294..CARD-299 (waves
60-64), and this card is scheduled after it.

**Was:** the design implemented on a raster interior, with its acceptance criteria
verified by measuring ink on a rendered bitmap.

**Should be:** the same design, unchanged — **the card's instrument moves, not its
decision**. CARD-293 §6 classifies this card as *written, tests retargeted*: the guide's worked example as four steps — page composition and type.

**Delta:**
- The design is **not** reopened. Nothing about what the page should look like
  changes here.
- The acceptance criteria's verifying tests move from ink measurement to
  assertions against the written PDF's content stream (ADR-0042/R6). The spike
  measured that replacement at **168 -> 41 lines, 4.1x smaller**, strictly more
  exact, and still discriminating under mutation.
- Scheduled **after** the vector phase (CARD-294..CARD-299) so the card is written
  against a vector page from the start. That ordering is the whole reason the
  phase runs first: dispatching this card before it would mean writing
  pixel-measuring tests and then converting them.

