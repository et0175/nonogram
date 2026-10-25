# CARD-293: SPIKE — one book rendered both ways, so the raster-vs-vector interior is decided on measurements

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/293-vector-interior-spike
**Worktree:** —
**Source:** owner, 2026-10-25 — *"I'm thinking about pdf generation and tests - maybe it makes sense to use another libraries for it or another technique?"* and, on the cost of change, *"sometimes the earlier we introduce changes - the better"*. The orchestrator's answer was that the test-cost half is a test-design problem already being solved, and the PDF half is a real question whose strongest argument is print quality the owner was already refused.
**Idea:** —
**Wave:** —
**Created wave:** 58
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/profiling/card-293-vector-interior-comparison.md, scripts/**
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## THIS CARD SHIPS NOTHING

It answers one question with measurements and stops. **It does not touch
`src/**` at all** — not the generator, not the layout, not the exporters. Its
whole output is a comparison document and whatever throwaway script produced it,
and its success condition is that a decision can be made from the numbers rather
than from anyone's argument.

A spike that quietly becomes an implementation is the failure mode here. If the
answer turns out to be "yes, go vector", that is a **phase** with its own ADR and
its own cards; this card's job ends at the document.

## The question

**Should the book interior be emitted as vector PDF, with the cover left raster?**

Today every interior page is a **2550 × 3300 RGB bitmap — 25,245,000 bytes** —
which Pillow's `save_all` concatenates into the PDF
(`book_pdf_generator.py:252`, `app.py:6141`, `book_proof.py:789`). A printed page
is therefore a JPEG photograph of line art. A nonogram is grid lines, flat fills
and digits: the worst case for a lossy raster format and the natural case for
vector.

**The owner's own framing of the split is what to test:** *the cover is a raster,
the interior is a vector.* A cover is a photograph and belongs in raster; the
interior is line art. PDF carries both in one file, and the interior is where all
the cost and all the quality pain sits.

## Why this is not a library question — read before reaching for `reportlab`

**`src/nonogram/export/svg.py` already emits vector, hand-written, with no
dependency**, and its own docstring (`:13`) says `svgwrite` or `cairosvg`
*"would buy nothing here and would reopen a dependency baseline"*. It consumes
the same `Layout` COMP-007 returns and already has the exact primitive a vector
PDF needs: `_line(x1, y1, x2, y2, width, major)` at `:88`.

So the live option is **"emit vector PDF the way `svg.py` already emits vector
SVG"** — continuing an existing pattern with **ADR-0006/R1's baseline closed** —
not adding a renderer. The spike should price that option first. If it concludes a
library is needed anyway, that is a finding and an ADR-0006 revisit, stated with
the reason.

**And the tests are out of scope as a motive.** The suite's render cost is a
test-design problem the board is already solving correctly: CARD-219 took one
file **−68 %** by asserting against the page plan instead of rendering it, using
a seam that already existed (`interior_stream` "does all of the deciding before
any of the drawing"), and CARD-288 will take ~20 s more by walking that stream
lazily. **No renderer change produces those numbers; a different test target
does.** Cheaper tests may well *fall out* of vector output — see §3 — but they are
not the argument for it.

## The argument that actually motivates it: a design the owner asked for and was refused

ADR-0037/R2's 2026-10-17 amendment records it plainly. The owner's "Puzzle page
layout" artifact specified **0.3 pt grey cell lines, 0.8 pt every-fifth, 1.3 pt
border**. Set against the ADR that broke it **three ways**, and the one nobody had
noticed was the minimum: **0.3 pt is 0.1058 mm, which at 300 DPI is a ONE-PIXEL
line — 2.4× under the floor, and thinner than the 0.17 mm this ADR had explicitly
rejected** as "exactly where faint lines hurt most", on the evidence of 7 of 17
reviews of the 450-puzzle book complaining of faint grid lines. It shipped
0.48/1.28/2.08 pt instead.

Then the consequence, recorded the same day: *"once CARD-227 implements the three
weights, the grid's thinnest cell line is 0.48 pt = 2 px, and the footer hairline
is also 2 px. They become the same width. Furniture can no longer be made lighter
than grid ink by width, because **width has reached the device floor**"* — so the
distinction "now rests on tone".

**In vector there is no device floor.** 0.3 pt is 0.3 pt and the press RIP
renders it at its own resolution. **The spike's most important deliverable is a
printed proof at the owner's original weights**, because if those look right the
whole chain of compromises above unwinds, and if they don't, the raster floor was
protecting something real.

## The cost of delay — the owner's own point, measured

*"Sometimes the earlier we introduce changes - the better."* That is correct here
and it is quantifiable, which is why this card exists now rather than later:

| what a vector interior would have to migrate | today |
|---|---|
| test files measuring **ink** (`drawing_of`, `drawings_of`, `page_ink`, `two_up_ink`, `round_ink`) | **21 files** |
| the heaviest call sites | `test_book_pdf.py` **32**, `test_book_puzzle_frame.py` **26**, `test_book_proof_pages.py` **16**, `test_book_pdf_two_up.py` **15**, `test_book_cell_size.py` **14** |
| files in the frozen render-heavy set | **33** |
| **print-layout cards still queued, every one `ready`** | **12** — CARD-207, 208, 209, 215, 216, 226, 227, 229, 230, 231, 232, 233 |

**Every one of those 12 adds more pixel-measuring tests**, and several of them
exist *because* of the raster floor — CARD-227 is literally "the printed grid's
rules get three weights", the weights the ADR had to compromise. So the migration
cost is monotonically increasing, and some of that queued work would be **written
twice**: once against measured ink, once against a content stream.

**The scheduling consequence, which matters more than this card's priority
letter:** *decide this before dispatching the 12.* That is not a `Depends on`
relationship in either direction — none of them blocks this spike and this spike
blocks none of them technically — but dispatching them first is choosing to pay
the larger bill.

## What to measure

Render **one real book** — the same book, same puzzles, same page spec — both
ways, and publish the table. Not a synthetic page: a book the tree can already
produce, so the comparison is of the thing that ships.

1. **File size**, total and per page.
2. **Generation wall clock**, interleaved A/B/A/B rather than two blocked batches,
   with min and median and the raw runs (the board's own rule after CARD-218
   measured a ~1 s effect on a box with 0.20 s reproducibility).
3. **Peak RSS**, `/usr/bin/time -l`, and **stated as the weaker instrument it
   is** — CARD-218 measured its own fix *removing* a 192.6 MiB retention while the
   peak went **up**, because peak RSS is allocation-order dependent. The exact
   figure is the **retention**, and the honest unit is this project's own
   `PAGE_BITMAP_BYTES = 2550 * 3300 * 3 = 25,245,000`.
4. **A printed proof** — the deliverable, not a footnote. Same page at the owner's
   original 0.3/0.8/1.3 pt and at the shipped 0.48/1.28/2.08 pt, vector and
   raster, on real paper. **Renders go to `~/Documents/nonogram-reviews/CARD-293/`,
   never beside the repo.**
5. **What a vector test would assert**, demonstrated on exactly one claim: take one
   existing ink-measuring test and show the content-stream assertion that replaces
   it, side by side. The point is whether the replacement is *more exact* — today
   `drawing_of()` **reconstructs by measuring ink** a cell size the generator knew
   precisely — or merely different.
6. **The font question, scoped honestly.** Lines and fills are simple PDF
   operators; **embedding a TrueType subset for the clue digits and headers is the
   one genuinely hard part**, and `export/fonts/DejaVuSans.ttf` already ships.
   Say how big that job is, or say you could not tell and why. **A spike that
   skips the hard part has not answered the question.**

## What to report as costs, because they are large and the decision needs them

* **Every byte-identity tripwire breaks**: CON-019 (CLI and web exports
  byte-identical whatever the book geometry), ADR-0036/R1's
  `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`, the baseline digests, and
  `tests/test_export_a4_golden.py`. Those are deliberate and regenerating them
  runs against the standing rule that **`tests/fixtures/**` is never
  regenerated** — an owner decision, not an implementation detail.
* **The ink-measurement apparatus mostly retires**, and some of it is the **only**
  proof the renderer consumes the layout's numbers rather than deriving its own
  (ADR-0036/R2). That needs *replacing*, not deleting — name what would replace it.
* **Pillow does not leave**: the cover, uploaded-image fitting and the PNG export
  all still need it. This is not a dependency removal.
* **Scope**: if the answer is yes, this is a phase. Say roughly how many cards,
  and which of the 12 queued ones would want rewriting rather than writing.

## Acceptance criteria

- **AC-1** (the question is answered from numbers): *Given* the comparison
  document, *then* it carries file size, interleaved wall clock with raw runs,
  retention in page-bitmap units, and the printed-proof verdict — each with the
  instrument that produced it and its domain. (**gate**: the document; no new
  standing test, because this card ships no mechanism.)
- **AC-2** (the owner's weights are the headline): *Given* the printed proof,
  *then* the 0.3/0.8/1.3 pt vector page is shown beside the 0.48/1.28/2.08 pt
  raster page, and the card states whether the original design is printable.
  (**gate**: renders handed over at `~/Documents/nonogram-reviews/CARD-293/`.)
- **AC-3** (the baseline stays shut, or the reason is stated): *Given* the
  prototype, *then* it is hand-rolled after `export/svg.py`'s precedent and adds
  **no runtime dependency** — or the card states exactly what forced a library and
  that ADR-0006/R1 needs revisiting. (**gate**: `pyproject.toml` unchanged,
  verified.)
- **AC-4** (the test replacement is demonstrated, not asserted): *Given* one
  existing ink-measuring test, *then* the card shows the content-stream assertion
  that would replace it and says whether it is **more exact or merely different**.
  (**gate**: the pair, side by side, in the document.)
- **AC-5** (the hard part is priced): *Given* font embedding, *then* the card
  states the size of that job with what it is based on, or states that it could
  not be determined and why. (**gate**: recorded.)
- **AC-6** (nothing ships): *Given* this card's branch, *then*
  `git diff <fork>..HEAD -- src/ tests/ pyproject.toml` is **empty**. (**gate**:
  the literal output.)

## Guardrails

- **G-1: do not edit `src/**`, `tests/**` or `pyproject.toml`.** The prototype
  lives in `scripts/` or the scratchpad. AC-6 is the check. **This is the
  guardrail that keeps a spike a spike.**
- **G-2: do not regenerate any fixture or golden**, even to see what would
  happen. `tests/fixtures/**` is untouched; if the comparison needs a golden's
  bytes, read them.
- **G-3: do not build the real thing.** A prototype that renders one page
  convincingly is the deliverable; a second generator is not. If the prototype
  starts growing a page-plan walk, stop — that is the phase, and it needs the ADR
  first.
- **G-4: measure both arms under one machine state.** Interleaved A/B/A/B, load
  average recorded at both ends. This board lost an hour on 2026-10-24 to a
  comparison whose two arms were taken hours apart under different load, and
  another to two arms that were not the files they were believed to be — **print
  what each arm is before reading its result** (see CARD-292).
- **G-5: a figure is a claim and its control is recomputation.** Re-derive every
  number before the card closes, and name the door it came through.
- **G-6: no timing claim on a single run**, and peak RSS is declared as the weak
  instrument it is.
- **G-7: recommend, do not decide.** The card ends with a recommendation and the
  numbers behind it. **Whether to spend the phase is the owner's**, and the card
  says so in those words.

## Architecture context

- **ADR:** **ADR-0006/R1** (the dependency baseline is closed — AC-3 exists to
  keep it that way); **ADR-0037/R2** and its 2026-10-17 amendment (the device
  floor, and the owner's refused weights — the motive); **ADR-0036/R1** and
  **CON-019** (the byte-identity tripwires a migration would break);
  **ADR-0036/R2** (geometry is COMP-007's, which is why `svg.py` and a vector PDF
  can share one `Layout`).
- **FR/CON:** FR-016, FR-033 (the rule weights, whose open question CARD-227
  answers under the raster floor), CON-018/NFR-008 (the cell floor).
- **Components:** COMP-007 (`export/layout.py` — the shared geometry),
  COMP-009 (`book_pdf_generator.py` — what a phase would eventually change).
  **This card changes neither.**
- **Trace:** not applicable; no requirement's verifying test changes.

## Worktree notes

- **Why a spike and not a card that does it.** The orchestrator's view, offered
  2026-10-25 and recorded so it can be disagreed with: vector interior is
  *probably* right, the motive is print quality rather than cost, and the costs
  are large enough that the decision should rest on a proof the owner can hold
  rather than on an argument. The owner's reply — *"I don't like much changes
  myself, but sometimes the earlier we introduce changes - the better"* — is the
  reason it is being asked now rather than after the 12.
- **The one thing most likely to kill it**, so the spike tests it early: font
  embedding. Everything else in a nonogram page is `re`/`m`/`l`/`S`/`f`/`rg`.
  **Do that first** — if a clue digit cannot be placed, the rest of the
  comparison is moot.
- **Related and deliberately not merged into this:** CARD-288 (3,820 pages drawn
  to read 1,033 — a *test*-side saving that stands whatever this decides),
  CARD-292 (the per-test ceiling), CARD-287 (344 s in one file). None of them
  waits on this and this waits on none of them.
