# CARD-293: SPIKE — one book rendered both ways, so the raster-vs-vector interior is decided on measurements

**Status:** done
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/293-vector-interior-spike
**Worktree:** — (removed at merge)
**Source:** owner, 2026-10-25 — *"I'm thinking about pdf generation and tests - maybe it makes sense to use another libraries for it or another technique?"* and, on the cost of change, *"sometimes the earlier we introduce changes - the better"*. The orchestrator's answer was that the test-cost half is a test-design problem already being solved, and the PDF half is a real question whose strongest argument is print quality the owner was already refused.
**Idea:** —
**Wave:** 59
**Created wave:** 58
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/profiling/card-293-vector-interior-comparison.md, scripts/**
**Review score:** —
**Started:** 2026-10-25
**Closed:** 2026-10-25
**Actual:** 1d (spike; measurement only, nothing shipped to src/ or tests/)
**Merge commit:** ef49d656
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
* **The ink-measurement apparatus mostly retires, and the replacement is
  SMALLER and STRONGER — not like-for-like.** This bullet said "needs replacing,
  not deleting" and implied comparable effort; the owner challenged it on
  2026-10-25 — *"but do we need measure ink for vector?"* — and was right.

  Everything `drawing_of` recovers, it recovers **by counting pixels**: its own
  docstring says `columns` is *"how many columns the grid is drawn with, counted
  from its vertical rules"* and `grid_right` is *"measured at the same edge of
  the rule as `grid_left`"*. Those are **reconstructions of numbers the generator
  knew exactly**. A vector content stream **states** them —
  `0.48 w 100 200 m 100 900 l S` is a line of width 0.48 between two points —
  with no inference, no anti-aliasing and no JPEG ringing to reason about.

  **The requirement survives; the instrument changes.** The artefact must still
  be checked against the plan, because asserting only on `Layout` proves the
  geometry computes and nothing about whether the drawing used it (ADR-0036/R2).
  But the check becomes an **exact read of the shipped file** rather than a lossy
  measurement of a photograph of it.

  **And the pattern CLAUDE.md actually cares about is untouched**: `Sheet`, the
  independent geometry reimplementation, stays as it is — compared against the
  content stream instead of against measured ink. "Prefer an independent second
  implementation" is preserved; only the reading of the artefact changes.

  **What genuinely stays raster is small**: the **cover** (a photograph, where ink
  measurement is the right instrument), and **one or two "does this PDF actually
  render" smoke tests**, because a valid content stream can still be a broken PDF
  — a bad resource dictionary, a missing font. One or two, against the 21 files
  and 100-plus call sites today. **And some of it disappears outright rather than
  migrating**: the JPEG round trip has nothing to round-trip, and the ink-mode
  tests get *easier* (a `g` versus `rg` operator rather than pixel levels).

  **So this is a smaller cost than the cost-of-delay table above implies, which
  strengthens the case rather than weakening it.** AC-4 is where the spike has to
  show it rather than assert it.
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
  that would replace it and says whether it is **more exact or merely different**
  — **and states the line count of each side**, because the claim being tested is
  that the replacement is *smaller and stronger*, not merely possible. Pick a test
  that reads several of `Drawing`'s fields, so the comparison is of a real
  reconstruction and not of one number. (**gate**: the pair side by side, with
  both line counts, in the document.)
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
## Worktree notes — implementation round, 2026-10-25

**Outcome: go vector for the interior, keep the cover raster. The decision is
the owner's (G-7).** The comparison document is
`meta/profiling/card-293-vector-interior-comparison.md` (written in the
scratchpad and handed back for a `main` commit, since `meta/` cannot commit from
a worktree). The prototype is `scripts/card293_vector_probe.py`. AC-6's diff is
empty.

**The finding that reframed the card: the PDF writer is already hand-rolled.**
`book_pdf_generator._write_pdf` (`:7047`) has not called `Image.save(save_all=)`
since CARD-145 — it drives `PIL.PdfParser` directly, writing the object table,
catalog, each page, each contents stream, xref and trailer by hand. A vector
interior replaces one of the three objects a page writes
(`q W 0 0 H 0 0 cm /image Do Q` becomes operators), drops the JPEG XObject, and
adds three font objects **once per file**. Everything else is untouched. So the
card's "this is not a library question" is stronger than it knew: the PDF
plumbing already ships inside the file that would change.

**AC-5 — font embedding is not the blocker.** DejaVuSans.ttf is 757,076 B raw,
**379,441 B deflated, once per PDF** — less than one raster page (381,564 B).
Subsetting (the genuinely hard half: `loca`/`glyf` rebuild + composite closure)
would save ~365 KB and is **not worth doing**. The job is **163 code lines**:
105 for an sfnt metrics reader over `head`/`hhea`/`maxp`/`OS/2`/`hmtx`/`cmap`
(stdlib `struct`), 33 for the three PDF font objects, 25 for a centred-text
operator. Proved by rendering a real 30x30 book page with all 540 clue digits and
reading it back with **poppler**, an engine that did not write it.

**AC-1 — the numbers** (24 real corpus pages on CON-018 Book 1, same `Layout`,
raster arm written by the production `_write_pdf` in its streaming shape,
interleaved A/B/A/B x7, run twice):

* size 407,976 B vs 9,157,535 B = **22.4x**; per page excluding the one-time font
  1,189 B vs 381,564 B = **321x**. A 450-page interior: ~0.9 MB vs ~172 MB.
* wall clock median **0.0329 s vs 0.2810 s** (run 2: 0.0329 / 0.2816) = **8.5x**.
  Load recorded at both ends of both runs.
* retention **0.000246 vs 1.00 page bitmaps**. CARD-145's `del page`, its
  2.00-vs-1.00 equality and the 512 MB OOM story become **vacuous** for the
  interior. Peak RSS reported too (69 vs 123 MiB) and declared the weak
  instrument CARD-218 caught lying.

**AC-2 — the owner's weights are printable, and better.** Four 1:1 panels at
`~/Documents/nonogram-reviews/CARD-293/card293-AC2-side-by-side.pdf`. Poppler
measures the vector 0.3 pt cell line at **2 px at 300 DPI and 5 px at 1200 DPI,
both at the declared grey 89** — the width scales with the device, the tone does
not move. That is "no device floor", measured. The raster control at the same
weights is a **one-pixel** line: the dropout ADR-0037/R2's amendment rejected.
**Verdict: printable, and the best of the four panels — but dot gain on real
stock is the owner's eyes, as ADR-0037 itself says.**

**AC-4 — the replacement is smaller and stronger, demonstrated.** Replacing
`TestBookProof_StrokesMeetBookMinimum`: **168 code lines -> 41** (4.1x), or 59 ->
41 if `page_ink.py` is amortised. The stream assertions were **written and run**:
they pass on the 0.48 pt page and **fail on the 0.3 pt page**, so they
discriminate. The strongest single point is one the card had not made: today's
pure-black assertion *cannot be made against the file that ships* — the class
docstring says the DCT round trip greys a 3-pixel rule's edges, so it reads an
in-memory page upstream of the PDF. A stream assertion reads the printer's file.
**`Sheet`'s oracle role survives untouched**: it works in millimetres and imports
no geometry; only the right half of the comparison moves from measured ink to a
stated coordinate, and it gets *more* precise because the `PX_PER_MM` rounding
and the explicit tolerances go.

**AC-3 — baseline shut.** stdlib + Pillow only; no NumPy on the vector path.
Nothing forced a library. ADR-0006/R1 does **not** need revisiting.

### Two corrections to this card's own cost column

1. **"It shipped 0.48/1.28/2.08 pt instead" is wrong.** Those are **CARD-227's**
   weights and CARD-227 has not landed. What ships today is COMP-007's
   proportional two-weight rule: on the Book 1 profile `compute_layout` returns
   `thin_rule = 3 px` (0.72 pt = 0.254 mm) and `thick_rule = 6 px`. The proof
   sheet therefore carries **three** readings, not two. Related: "0.3 pt is 2.4x
   under the floor" is against R2's **retired** 0.25 mm floor; against the
   amended 0.169 mm minimum it is 1.6x under.
2. **CON-019 and the a4 golden are NOT broken.** CON-019's statement is about
   *the CLI's and the web UI's* PNG/SVG/PDF exports, and
   `tests/fixtures/a4_golden/` holds `compute_layout` with **no PageSpec** plus
   SHA-256 of the **CLI's** files. A vector book interior lives in
   `admin/book_pdf_generator.py` and changes no COMP-007 renderer — the prototype
   demonstrates exactly that. What does break is the **21
   `book_baseline_card*.json`** recordings, and those are not regenerated: the
   board's own move, taken twenty times, is to **record a new baseline beside the
   old one naming what it supersedes**. So the byte-identity cost is one new
   recording, not four tripwires and a standing-rule conflict.

### Scope, if the owner says yes

**5-7 cards** behind one ADR. The one **not** priced here (G-3 forbade it) is the
non-puzzle pages — guide, TOC, dividers, answer tiles, pipeline diagram,
difficulty legend — redrawn as operators. That is the real unknown.

Of the 12 queued print-layout cards: **4 would be rewritten** — **CARD-227**
(its 0.48/1.28/2.08 is the owner's figures scaled x1.6 purely to clear 2 px, and
the arithmetic is moot in vector), **CARD-208** (thin rules at clue-box scale),
**CARD-215** (its AC literally says "at least 1 device pixel"), **CARD-226**
(a "light rule" is the furniture-vs-grid problem ADR-0037/R2 says width can no
longer solve); **7 written with retargeted tests** (207, 209, 229-233); **1
untouched** (216).

## [SPIKE VERDICT — 2026-10-25, orchestrator] The measurements are in, and three of the brief's costs were MINE and wrong

Comparison document: `meta/profiling/card-293-vector-interior-comparison.md`.
Prototype: `scripts/card293_vector_probe.py` (1099 lines, the branch's only
file). **AC-6 re-verified by me: `git diff c0a6ac54..HEAD -- src/ tests/
pyproject.toml` is 0 bytes.** `pyproject.toml` untouched, so **ADR-0006/R1 did
not need revisiting and no library was forced.**

### The numbers

| | vector | raster | |
|---|---|---|---|
| 24-page interior | **407,976 B** | **9,157,535 B** | **22.4×** |
| per page, excl. one-time font | **1,189 B** | 381,564 B | **321×** |
| generation, median of 7 interleaved, run twice | **1.37 ms/page** | 11.7 ms/page | **8.5×** |
| retention, in `PAGE_BITMAP_BYTES` | **0.000246** | **1.00** | structural |

450 pages — the book the faint-line reviews came from — **0.92 MB against
171.7 MB.** And the retention figure is not an optimisation: **no page bitmap is
ever allocated**, so CARD-145's `del page`, its 2.00-vs-1.00 equality and the
512 MB OOM story become **vacuous rather than satisfied** on the interior.

### Font embedding was not the blocker, and the reason is a number nobody had

I told the round this was "the one genuinely hard part" and to price it first. It
priced it and dissolved it: **`DejaVuSans.ttf` is 379,441 B FlateDecode, once per
PDF — less than ONE raster page at 381,564 B.** So glyph subsetting, the
expensive half, buys ~365 KB against a 9 MB file and **is not worth doing**. The
job is **163 code lines**, and the estimate rests on working code rather than a
guess: 105 for an sfnt metrics reader, 33 for the three font objects, 25 for a
centred-text operator. Proved rather than asserted — a 30×30 page with **all 540
clue digits**, rendered by **poppler, an engine that did not write it**.

### AC-2: the owner's refused weights, measured

poppler on a file it did not write, the owner's **0.3 pt** grey cell line:

```
at  300 DPI : 2 px at grey 89 ; fifth line 4 px at grey 0
at 1200 DPI : 5 px at grey 89 ; fifth line 14 px at grey 0
```

`grey 89 = round(255 × 0.35)` — **the declared tone exact at both resolutions,
with the width scaling ×4 with the device.** That is "no device floor" as a
measurement rather than an argument. The raster control at the same weights is
the **one-pixel line** ADR-0037's amendment refused.

**Sheet to print: `~/Documents/nonogram-reviews/CARD-293/card293-AC2-side-by-side.pdf`
at 100 %** — the same 30×30 corner four ways at 1:1.

**Two things the round says it cannot judge, and it is right:** dot gain on real
uncoated stock, and whether 35 % grey reads as "light guidance" or "faded". ADR-0037
itself says those "become final only after the owner has seen them on printed
proof pages". **The judgement is the owner's.**

### AC-4: smaller, stronger, and run rather than asserted

`TestBookProof_StrokesMeetBookMinimum` — **168 lines today** (38 test bodies + 21
in-file + **109** in `tests/helpers/page_ink.py`) against **41** (19 + 22).
**4.1× smaller.** It **passes on the 0.48 pt page and fails on the 0.3 pt page**,
so it discriminates. Width comes from `0.48 w` instead of counted dark pixels;
tone from `0.35 G` instead of a chosen `INK_LEVEL = 128`; no `pytest.approx`, no
`CELL_PITCH_SLACK_MM`, no `_RULE_SHARE = 0.9`.

**And the strongest argument on this card is one neither I nor the card had
made:** today's pure-black assertion **cannot be made against the file that
ships**. The class's own docstring says the DCT round trip greys a 3-px rule's
edges, so the test reads an **in-memory page upstream of the PDF**. A stream
assertion reads *the printer's file*.

**`Sheet`'s independent-oracle role survives intact** — it works in millimetres
and imports no geometry, so a migration changes only the right half of the
pairing, and the comparison gets *more* precise by dropping `PX_PER_MM` rounding
and explicit tolerances.

### THREE CORRECTIONS TO MY OWN BRIEF, one of which would have changed the decision

**(a) "It shipped 0.48/1.28/2.08 pt instead" is false.** Those are **CARD-227's**
proposed weights and **CARD-227 is `ready`, not landed** — verified. What ships
is COMP-007's proportional two-weight rule: on Book 1, `thin_rule = 3 px`
(0.72 pt) and `thick_rule = 6 px`. So there are **three** readings to compare and
the proof sheet carries all three. Relatedly I quoted "**2.4× under the floor**"
without saying that floor was **retired the same day** by the amendment I was
citing — against the 0.169 mm that replaced it, 0.1058 mm is 1.6× under.

**(b) "Every byte-identity tripwire breaks" overstated the cost by three of four,
and this is the error that mattered** — because the owner had said *"I don't like
much changes myself"*, so a false blocker in the cost column would have pushed
them away from a change the measurements support. **Verified:** CON-019's
statement is about *"the CLI's or the web UI's exports: for any generation
request the PNG, SVG and PDF files **COMP-007** writes"* — a vector book interior
is COMP-009 and touches no COMP-007 renderer. `tests/fixtures/a4_golden/`
captures `compute_layout` with **no PageSpec** plus the **CLI's** bytes, so
ADR-0036/R1's golden is not reached either. **Only the 21 book baselines move,
and the board's own practice is to record a NEW baseline superseding the old —
done twenty times** (`card206 ← card224 ← card248 ← card223 ← card222 … ←
card145`). `tests/fixtures/**` is still never regenerated. **Not an owner
decision; a routine move.**

**(c) I pointed at the wrong precedent.** I sent the round to `export/svg.py`,
which is the *stylistic* precedent. The **load-bearing** one is
**`book_pdf_generator._write_pdf` itself**, which has driven PDF object structure
by hand through `PIL.PdfParser` since CARD-145 — verified at `:379` (`from PIL
import … PdfParser`) and `:7105`. **The PDF plumbing already ships inside the
very file that would change**, which closes the "is a library needed?" question
before it is asked, and means the Pillow-internal-module risk is **already taken
rather than newly incurred.**

### Scope, and the one thing deliberately not priced

**A phase of 5–7 cards behind one ADR.** Of the 12 queued print-layout cards:
**4 rewritten** — CARD-227 (its 0.48/1.28/2.08 is the owner's figures ×1.6
*purely to clear 2 px*, so in vector its **decision** changes, not just its
test), CARD-208, CARD-215 (its AC literally says *"the dot is at least 1 device
pixel across"*), CARD-226 — **7 written with retargeted tests** (207, 209, 229,
230, 231, 232, 233), **1 untouched** (216).

**Not priced, because G-3 forbade it: the non-puzzle pages** — guide, TOC,
dividers, answer tiles, the pipeline diagram, the difficulty legend — redrawn as
operators. **That is the real unknown and the first thing the ADR should scope.**
The prototype also skips two-up pages (a `PairLayout`, not a `Layout`) and the QR
glyph and difficulty dots. One page, drawn convincingly, no page-plan walk — G-3
respected.

### Verdict

**The spike recommends vector interior with the cover left raster, and I agree
with its reasoning.** Every figure it rests on is measured, re-derived in a second
run, and taken with the arms printing their own identity first. **The decision is
the owner's**, and the one input they cannot get from this card is the printed
sheet.
