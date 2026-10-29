# CARD-306: The vector puzzle page grows its sheet furniture — folio, frame rules, grid-size label and QR block — because a page with no number cannot ship

**Status:** in progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/306-vector-puzzle-page-furniture
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-306
**Source:** `src/nonogram/admin/book_puzzle_vector.py`'s own module docstring, which raises the gap and names CARD-298 for it; CARD-295's handoff; confirmed by CARD-298's implementation round, 2026-10-29. Cut by the orchestrator on owner decision after CARD-298 hit the scope gate.
**Idea:** —
**Wave:** 67
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-299
**Touches:** src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/book_vector.py, tests/test_book_puzzle_page_vector.py, tests/test_book_pdf.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**No card owns this, and three cards have now each discovered it.**
`book_puzzle_vector`'s own docstring states the gap and names CARD-298 as the
card that will close it — *"the card that makes the medium real per page is
CARD-298, and it cannot land a vector puzzle page that has no page number on
it."* CARD-298 was narrowed to the mechanism card on 2026-10-29 and **cannot**
close it. CARD-295 made the same attribution. So the gap has been correctly
identified twice and assigned twice to a card that does not own it.

Measured on `main` after CARD-298's round: `book_puzzle_vector` draws the puzzle
grid and its clues and **no sheet furniture at all** — no folio (page number), no
frame rules, no grid-size label, no QR block. The raster path draws all of it in
`book_pdf_generator`: `_draw_page_frame` (whose footer is **all-or-nothing**),
`_draw_qr_caption`, and the QR checkerboard.

**The ordering constraint that makes this a separate card rather than a clause.**
A vector puzzle page cannot ship before (a) CARD-298's per-page medium exists —
done — and (b) CARD-299's readers stop asserting one image XObject per page. Until
both land, furniture code written here is unreachable, and unreachable drawing
code cannot be reviewed against a render. CARD-298's round declined to write it
for exactly that reason (~400 lines behind a blocker), and that judgement is
adopted rather than re-litigated.

## What to implement

1. **The folio.** The page number, in the position and face the raster path uses.
   Derive the position from the same `PageSpec`/layout source the raster footer
   reads — do **not** transcribe coordinates. `_draw_page_frame`'s footer is
   all-or-nothing, so the vector version must be too: a page with a frame and no
   number, or a number and no frame, is a defect, not a degraded state.
2. **The frame rules**, at the **2-device-pixel dropout floor** (NOT ADR-0037/R2 — see the correction below). These
   already have property tests reading drawn ink
   (`tests/property/test_book_layout.py:364`,
   `tests/property/test_book_two_up.py:682`) which CARD-299 re-expresses against
   the stream — so this card's rules must satisfy the **re-expressed** versions,
   not today's pixel ones.
3. **The grid-size label.**
4. **The QR block.** The checkerboard is the part most likely to be approximated;
   it is a bitmap by nature. **Decide explicitly** whether the QR stays an image
   XObject on an otherwise-vector page — which CARD-298's machinery permits only
   via a declaration with a reason and an `expires_with` — or becomes drawn
   rectangles. Either is defensible; an undeclared one is not, and
   `page_medium`'s default-DENY will refuse the page rather than ship it.
5. **One definition per piece of furniture, not two.** The raster and vector paths
   must not each carry their own copy of the footer's geometry. Follow CARD-298's
   precedent in `book_vector.py` (`write_face_objects`/`write_vector_page` were
   made public precisely so the mixed writer did not transcribe the
   `/FontDescriptor` a second time).

## Acceptance criteria

- **AC-1** (the furniture is on the page): *Given* a vector puzzle page written
  through `_write_pdf`, *then* its content stream carries the folio, the frame
  rules, the grid-size label and the QR block — each asserted by its own operators
  in the stream, not by a rendered bitmap.
- **AC-2** (the footer stays all-or-nothing): *Given* a page where the folio is
  suppressed, *then* the frame is too, and vice versa — **both directions**, with a
  mutant for each.
- **AC-3** (one definition): *Given* the module AST, *then* the geometry of each
  piece of furniture is read from a single source shared with the raster path,
  derived and default-DENY per ADR-0039/R2 — a second transcription is a FAILURE.
- **AC-4** (the QR's medium is declared): *Given* the written page, *then* the QR
  block is either operators, or an image XObject covered by a live
  `_RASTER_DECLARATIONS`-style declaration with a reason and an `expires_with`.
  An undeclared XObject on a vector page must be **refused by the writer**, not
  merely reported.
- **AC-5** (an owner render exists): *Given* the converted page, *then* a rendered
  puzzle page is produced under `~/Documents/nonogram-reviews/CARD-306/` for the
  owner's visual check. **Standing rule: image-pipeline changes need a rendered
  eyeball, not just green tests.**

## Engineering constraints

- **EC(furniture dropout floor):** across a seeded corpus spanning trims, page counts
  and tier mixes, every frame rule on a vector puzzle page meets the stroke-weight
  floor read from the stream, with a minimum case count asserted inside the test.
- **EC(all-or-nothing footer):** across the same corpus, the count of pages
  carrying a folio equals the count carrying a frame.

## Guardrails

- **G-1: do not change the raster puzzle page's bytes.** Until this card's own
  conversion card flips the declaration, the shipped puzzle page is raster, and
  the 21 book baselines must not move. A baseline that reds here is a **finding**.
- **G-2: do not transcribe coordinates.** A magic number copied from
  `_draw_page_frame` is the defect AC-3 exists to catch.
- **G-3: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-4: do not flip ADR-0042/R1.** R1 is true only when all four interior kinds
  are operators; this card converts one piece of one kind. R1's flip belongs to
  whichever card lands last. CARD-298 and CARD-299 each refused this flip for the
  same reason.
- **G-5: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators (check: review-lens — NOT this card's to flip)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ~~ADR-0037/R2, FR-033 — stroke weights (check: CARD-299's re-expressed stream readings)~~ — **BOTH HALVES WRONG, see the correction below**: R2 does not bind page furniture, and CARD-299 re-expressed neither named test.
- ADR-0039/R1 — a claim needs a control that CAN fail; two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- CON-020 — the 10 pt interior type floor (check: CARD-299's re-expressed test)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: **DEAD REF** — `TestDependencyBaseline_IsExactlyPillowAndNumpy` has zero definitions in this repo; verify the SUBSTANCE and see CARD-307)

## Architecture context

- **FR:** FR-033, FR-043, FR-030
- **NFR:** NFR-008
- **ADR:** ADR-0042 (R1, R2, R3), ADR-0039/R1-R2 — **ADR-0037/R2 removed**, see the correction below
- **Components:** COMP-009
- **Trace:** no row is re-stamped here; R1's flip is a later card's.

## Worktree notes

- The puzzle page is the **only** interior kind the generator can already call:
  `book_pdf_generator:400` imports `book_puzzle_vector`, while
  `book_guide_vector:103`, `book_toc_vector:60` and `book_answer_vector:62` all
  import `book_pdf_generator` at module level and so cannot be called from its
  page walk without a cycle. That asymmetry is why the puzzle page is first and
  why the other three need a different assembly point — a fact worth carrying into
  whichever card converts them.


---

## Implementation — `560d7e09` → `77b6998d`, 5 commits, 9 files, +2275/−75

**It built `src/nonogram/admin/book_sheet_vector.py` for EVERY interior page kind, not
just this one** — importing only `book_vector`, `book_vector_draw` and `export.layout`,
so `book_pdf_generator` can import it exactly as it already imports `book_puzzle_vector`,
**without the module-level cycle that keeps guide/toc/answer out of that generator's page
walk.** It wired it to the puzzle page and the two-up page only; the other three kinds
still carry no frame, and it says so — *"that is the card that converts those three kinds,
not this one."* `book_puzzle_vector` is **unchanged as a drawer**, and the class asserting
it draws no sheet furniture stayed true by being re-pointed at its own stream output
rather than the composed page, so its node ids stayed put.

**No coordinate is written in the module**, held two ways over its own AST, both
default-DENY: a set equality against a 5-literal allowlist each with its reason, and —
because of M5 below — **no numeric literal reaches any drawing call as an argument.**

### M5 is the result to read

| mutant | result |
|---|---|
| M1 delete the centred folio's draw | 8 failed |
| M2 footer rule unconditional — *a frame with no number* | 6 failed |
| M3 centred folio unconditional — *a number with no frame* | 4 failed |
| M4 transcribe `frame.folio_x` → `1275` | 5 failed |
| **M5** `to_points(footer_rule.width)` → `to_points(2)` | **first run: 0 failed** |

**M5 is numerically identical on a book page**, so no reading of the page can see it — and
`2` *has* to be on the value allowlist (the chequer's parity, a centred string's halving).
It left all 61 tests green. **The round found a blind spot in its own guard and closed
it** with the call-argument arm; M5 now reds two cells. That is ADR-0039/R1 applied by a
round to its own work, unprompted.

**The all-or-nothing coupling** is one branch of one `if` on `footer_is_clear`, using
`_draw_page_frame`'s own expression on the same two figures, and a request carrying QR
groups for a page with no footer is **refused**, not half-drawn. The corpus exercises
**both** arms rather than hoping to: **47 of 60 pages carry a footer, 13 do not.**

**G-1 measured, not assumed, and the instrument proved**: PDF bytes are useless because
`_write_pdf` stamps two timestamps, so it compared **page bitmaps** — all 14 raster
interior pages byte-identical — and proved the reading discriminates by shifting a centred
folio 1 px in the base worktree and watching **exactly 3 of 14** digests move.

**AC-4 decided the QR's medium as operators**, and made the other half a **refusal**:
`write_vector_page` now raises on a stream carrying a `Do` operator, because leaving
`/XObject` out of the resources only makes an image unreachable to a *viewer* — it does not
stop the operator being written. Pattern written as an explicit character class, **not
`\b`**, with a negative control.

**Renders at `~/Documents/nonogram-reviews/CARD-306/`** — vector single and two-up **with
their raster twins beside them** for direct comparison; the round looked at all four and
reports them visually indistinguishable. **Node ids 236 → 259: 23 added, 0 removed, 0
renamed, 0 skipped.** One skip in the blast radius and it is not this card's.

## THE CARD AND THE ORCHESTRATOR'S BRIEF WERE BOTH WRONG ABOUT ADR-0037/R2

The card claimed `ADR-0037/R2` in **four** places and the orchestrator's brief repeated it
(*"stroke weights are pinned by ADR-0037/R2 and FR-033 — use the pins"*). **ADR-0037's own
History settles the opposite**, at `0037-…md:290`:

> *R2 binds the **puzzle grid's** rules and nothing else. Page furniture — the interior
> header rule, the footer hairline, a divider — is NOT a grid rule and never was … so it
> needs no exemption from R2 and **must not claim one**.*

**And that History entry exists because CARD-222 read it exactly the way this card did**
(*"SCOPE, clarified 2026-10-17 after CARD-222's review read it the other way"*) and then
wrote a formal exemption that was **measured vacuous.** So the card, and the brief, walked
into the precedent the ADR was amended to prevent — and the round refused the pins,
holding its EC against the **real** authority instead: the 2-device-pixel dropout floor
applied inside `interior_frame` by `_pt_to_px_at_least`, measured at **3 px** (header,
0.6 pt) and **2 px** (hairline, 0.4 pt) at 300 DPI, claiming **no R2 exemption**. The four
claims are struck above; the correction is recorded in ADR-0042's History at `67633853`.

### Two more card figures measured wrong

- **CARD-299 re-expressed neither named property test.** The card says
  `test_book_layout.py:364` and `test_book_two_up.py:682` are *"re-expressed against the
  stream by CARD-299, so this card's rules must satisfy the re-expressed versions."* Both
  are **still pixel readings** of the **raster** page's grid area — unaffected by vector
  furniture, both green. **There was no re-expressed version to satisfy.**
- **G-1's "21 book baselines" is not a named artefact.** The nearest is
  `book_corpus.BASELINE_PAGE_COUNT = 14`, and G-1 was discharged against what exists.

### A new instrument trap, same family as the day's others

`MODS="a.py b.py"; pytest $MODS` — **zsh does not word-split an unquoted variable**, so it
becomes ONE argument naming a file that does not exist; pytest exits 4 with *"no tests
collected"*, and a node-id diff computed from it reads **"0 tests, 0 removed, 0 added."**
The round's first delta came back `base=0 head=0` for exactly that. **This board has hit
this before** — an earlier fix round used `${=MODS}` for the same reason — so it is a
recurrence, not a discovery, and belongs beside `\b`, the `^`-anchor, macOS `timeout` and
`-q` stacking in every brief.

### It also repaired an expired declaration reason

`_RASTER_DECLARATIONS` is untouched (CARD-309's and CARD-231's), **but the PUZZLE entry's
reason** said *"book_puzzle_vector draws no sheet furniture at all … so a vector puzzle
page would print with no page number on it"* — true this morning, **false now.** The round
corrected the reason to name the reader conversion as what remains, leaving `expires_with`
alone, on the ground that *"a declaration whose reason has expired is precisely what that
registry's own `_landing_findings` has a class for."*

### Three residuals declared, each measured

The typed QR link sits **9 device px (0.76 mm)** lower in vector than raster — Pillow's
`"lb"` anchor is the *ink box's* bottom where this package's vector convention takes the
row as the **baseline**; identical to the pixel for the folio and the two labels, only the
link descends, and the property that matters (ink lands inside the footer strip, clear of
the margin) is asserted instead. Pillow paints rectangles **inclusively** and a PDF `re`
does not, so a raster chequer module's ink is 1 device px wider — the test compares module
**boxes** and explicitly does not claim ink equality. And guide/toc/answer still carry no
frame, which is the converting card's work.

**CARD-309's prerequisite is discharged**: it can now convert the puzzle page without
shipping pages that have no number, and `vector_two_up_page` is covered too.
