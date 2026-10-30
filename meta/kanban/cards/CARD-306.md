# CARD-306: The vector puzzle page grows its sheet furniture — folio, frame rules, grid-size label and QR block — because a page with no number cannot ship

**Status:** done
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
**Touches:** src/nonogram/admin/book_sheet_vector.py (new, +489), src/nonogram/admin/book_pdf_generator.py (+194/−28, incl. a **raster**-path split of `_draw_two_up_qr_groups`), src/nonogram/admin/book_puzzle_vector.py, src/nonogram/admin/book_vector.py, tests/test_book_puzzle_page_vector.py, tests/test_book_grid_rules.py, tests/test_book_export_interior_cover.py, tests/test_book_interior_type_floor.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** 8.5 (cycle 1/3) — 0 gating findings, certifies: true; fix round 1 closed all five non-process findings
**Started:** 2026-10-29T19:33:56Z (wave 67 opened)
**Closed:** 2026-10-29T21:57:25Z
**Actual:** 0.3d — **2h 24m wall clock**, dispatch to merge, which is the instrument: 5 implementation commits (22:05–22:19 local), review cycle 1, fix round 1 (23:29), merge gate (21:34–21:56 UTC). Against a 1d estimate that is **0.3×**, the first card today to come in UNDER estimate — and the comparison is only sound against other cards measured the same way (CARD-308's 3.0× was wall clock too).
**Merge commit:** `8c81e00f` (gated tree `fca2fea1`)
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

## Implementation — `560d7e09` → `77b6998d`, 5 commits, 9 files, +2283/−83

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
It left all 61 tests green. **The round found a blind spot in its own guard and narrowed
it by one notch** with the call-argument arm; M5 now reds two cells. Looking for its own
blind spot unprompted is ADR-0039/R1 applied by a round to its own work — but the notch is
**not** closed, and the card said it was.

> **AMENDED by review cycle 1, F-301 (high).** The call-argument arm catches only a bare
> `ast.Constant` in an argument position. The reviewer planted `_QR_BORDER_PX = 2` at module
> level and used it as `to_points(_QR_BORDER_PX)` — the raster placeholder's own border
> weight, **one hop out, the exact transcription M5 was** — and **all three AC-3 cells
> passed**. Fourteen shapes are silent on both arms: local variable, module constant, tuple,
> list, starred tuple, dict value, f-string, default argument, `f(1+1)` — and **`f(-2)`,
> which is `UnaryOp(USub, Constant)` and not even one notch out**. The escape set is
> `{0, 1, 2, 0.0, 2.0}` through any expression that is not a bare `Constant`, **and it
> contains the one value the closure exists for**. Fix round 1 owns the choice: widen the
> guard over an enumerable set of shapes, or narrow the claim to what it checks and name the
> escapes. Leaving the wording as it stood was the one option not available.

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
- ~~**G-1's "21 book baselines" is not a named artefact.** The nearest is
  `book_corpus.BASELINE_PAGE_COUNT = 14`, and G-1 was discharged against what exists.~~
  **STRUCK by review cycle 1 — this correction was itself wrong, and it was the
  orchestrator's.** `ls tests/fixtures/book_baseline_card*.json | wc -l` is **exactly 21**,
  and the phrase is used in `handoff.md:7` and in **`ADR-0042:389`, the ADR this card
  edited**. `BASELINE_PAGE_COUNT = 14` is the page count of the one live baseline, a
  different quantity. G-1 holds either way — all 21 fixture files are byte-unchanged — but it
  was discharged against a population the round had told itself did not exist. The pattern is
  the day's own: a figure declared absent **by searching for the wrong artefact kind**, where
  the instrument's blindness and the quantity's absence read the same.

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

---

## Review cycle 1 — **8.5**, risk low, **0 gating findings**, certifies: true

`meta/review/20261029T210440Z-CARD-306-cycle1.yml`. Passes `min_score: 8` on cycle 1 of 3.
Impact set re-derived to 16 files: **774 passed, 0 failed, 0 skipped**, 3–4 min. Node ids
re-derived from two `git archive` trees with `${=MODS}`: **236 → 259, 23 added, 0 removed, 0
renamed** — matches the card. One skip in the blast radius, attributed by name:
`test_book_pdf_memory.py::…::test_the_same_pair_under_an_address_space_cap_the_kernel_enforces`
(macOS `setrlimit(RLIMIT_AS)`; that file is 0 lines changed by this card).

**Reproduced from scratch, not taken on the card's word:**
- **G-1's instrument.** All 14 raster interior pages byte-identical base vs head; shifting the
  centred folio 1 px at `book_pdf_generator.py:2453` in the **base** tree moves **exactly 3 of
  14** digests (pages 05, 07, 09). Also all **21** `book_baseline_card*.json` byte-unchanged.
- **The 47/13 footer split**, re-derived from COMP-007 independently of the test, then widened
  to an independent **240-page sweep (162/78)**. Both arms exercised, not hoped for.
- **The ADR-0037/R2 correction is exactly right.** ADR-0037:290 verbatim holds page furniture to
  the 2-device-pixel dropout floor and says it "must not claim" an exemption; 3 px (header,
  0.6 pt) and 2 px (hairline, 0.4 pt) at 300 DPI reproduce. **The vacuous-exemption precedent
  CARD-222 set is not repeated.**
- **`book_puzzle_vector` is AST-identical ignoring docstrings** — its re-pointed class is a
  genuinely narrowed claim with an in-test control, not a claim relocated to stay true.
- **The refusal is unreachable from production and the code says so.** Over all 300 pages,
  `qr_slot` non-None and footer-blocked **never co-occur**; `draw_sheet_furniture`'s docstring
  states that unreachability rather than implying coverage. Honest, not a finding.
- **The owner render supports "visually indistinguishable."** All four PNGs viewed against their
  raster twins; the only visible difference is the typed link a hair lower — the declared
  0.76 mm, visible in a full-res A/B and not at reading distance.

**Findings** (none gating): **F-301 high** — M5's closure is one notch narrower than claimed
(see the AMENDED block above). **F-302/F-303/F-304 medium** — a docstring states the link
residual as **35 px** where the test asserts and the reviewer re-measured **9**, and the
sentence is unfinished; the 2-px floor is attributed in **four places** (including ADR-0042's
new History entry) to `_pt_to_px_at_least`, which applies a **ceiling** —
`_pt_to_px_at_least(0.2) == 1` — so the floor is held by **the chosen point constants**.
**CORRECTED by fix round 1:** the review went one step further and said this card's new EC is
*the only thing in the tree* that would catch a future point constant below the floor, and
**that is wrong — measured.** Planting `INTERIOR_FOOTER_RULE_PT = 0.2` out of tree reds **four**
cells, two raster and two vector, one of them a pre-existing property test. The EC is the
**vector medium's** reading of a floor no function applies, not the only reading. The round had
already written the review's stronger wording into three sites **before** measuring it, and then
corrected all three — the day's own defect family, caught one layer in. The sub-floor band is
also *"at or below 0.24 pt"*, not *"below"*: `_pt_to_px_at_least(0.24) == 1` while `(0.2401) == 2`; and `_XOBJECT_PAINT`'s `[ \t]` class
covers **2 of PDF's 6** whitespace characters, so `"q\n/Im0 Do\nQ"` escapes, while
`(Scan Do now) Tj` **false-fires** — latent on a line **CARD-210 is scheduled to edit**.
**F-305 low** — the one AC-3 cell that reddened under the plant failed on its own
`assert planted != source`, its verbatim needle having vanished: it reads like a catch and is
not one. **F-306/F-307 low** — the Touches drift above, and a class name that now names a claim
false of the shipped page.

**Also measured wrong on the record:** the card's `+2275/−75` is **+2283/−83**; the "21
baselines" strike above; and ADR-0006/R1's named check
`TestDependencyBaseline_IsExactlyPillowAndNumpy` has **zero class definitions in the repo**. R1
holds in substance anyway (`pyproject.toml` diff empty; the only new import is stdlib `re`).
**That ref is not a new finding and is already owned by CARD-317**, which records it more
precisely than the review did: the rule *is* tested, at `tests/test_export_pdf.py:1249`, so this
is a phantom **pointer**, not an unverified rule, and twelve cards carry a hand-written
`**DEAD REF**` note about it. Re-verified here: the only `.py` occurrences are one comment at
`test_export_pdf.py:622` and two docstrings (`test_export_pdf.py:1250`,
`test_puzzle_editor_ui.py:1021`); the nearest real class is
`TestDependencyBaseline_SqlalchemyIsNotCapped` (`test_db_url_driver.py:332`), a different claim.
And the ref is a live demonstration of the mechanism this board has measured before:
`symbol_exists()` is a **text** search whose domain includes `meta/review/**`, where **over a
hundred** YAMLs name this symbol — so it resolves alive, raises no warning, and **would resolve
falsely even if ADR rule refs were checked, which they are not** (CARD-319).

- [Review 1/3] Score: 8.5 ✓ threshold reached (0 gating findings, certifies: true)
- [Fix 1] `5d95abc3` — see below. Dispatched on F-301, F-302, F-303, F-304, F-305 — four of the five are a refuted
  figure, a wrong mechanism attribution in four places including an ADR History entry, a
  pattern narrower than its own domain, or a control that reds for the wrong reason. The score
  cleared; ADR-0039/R4 still obliges the retraction.

---

## Fix round 1 — `77b6998d` → `5d95abc3`, 4 files, +510/−75

Cumulative `560d7e09..5d95abc3`: **9 files, +2718/−83** — same file set, so `Touches` above still
holds. Nothing pushed, rebased or stashed; `meta/kanban/cards/` untouched. The lock was checked
by absolute path three times and absent each time.

### F-301 — it widened the guard rather than narrowing the claim, and the choice is the right one

**2 of 14 shapes caught → 14 of 14.** The reason given for choosing option 1 is the one that
decides it: narrowing the claim would have satisfied honesty while leaving **the one value the
closure exists for** reachable by a one-line edit, and **AC-3's own words are "a second
transcription is a FAILURE"** — a narrowed claim does not satisfy that AC. Option 2's escape set
was enumerable but unbounded in practice; option 1's is two named shapes.

The cell keeps its name (G-3) and is now **two** default-DENY conditions: a **position** arm
(every numeric literal occupies one of a named position set — a zero field default, a comparison
against zero, an operand of `%`/`/`/`+` whose other side is not a literal; **`Assign` and
non-zero `AnnAssign` are not positions, which is what closes the binding**) and a **reach** arm
(no numeric literal inside a **method** call's arguments at any depth through any expression —
every mark the module makes is a method on `stream`, so this is the test's own name read
*transitively* rather than at one syntactic slot). **R2 is satisfiable in the form R2 asks for**:
the authority is the module's own census — **nine** literals in **three** position kinds, a
census the round *ran* rather than took from the review — and any other position is reported as
a failure naming the parent node instead of read as an absence.

Caught after the fix where they were missed before: module constant, local variable, tuple, list,
starred tuple, dict value, f-string, default argument, `f(1+1)`, `f(-2)`, class attribute,
comprehension. The **value** arm never rises on any of them, which is the point. **End-to-end
positive control**: the review's own plant now reds with
`[(229, 2, 'UNJUSTIFIED: inside Assign.value', None)]`. **Residual escape set is stated in the
cell's docstring** — a `0`/`0.0` field default later read as a coordinate, and an arithmetic
operand over a frame-read value whose result never passes a method call. Neither is a
transcription of a measured figure, and a *nudge* (`to_points(footer_rule.width + 2)`) is
measured **caught**.

### F-305 — and the review's own framing hid something

The plant is now an **AST** mutation and the anchor is located **structurally**, asserted as its
own named check. Measured both ways: with the binding planted and the anchor intact, the guard
cell reds on detection **and** the control cell reds on its own near-miss assertion — both real;
with the anchor replaced, the control cell reds **saying the anchor moved**, which is no longer
readable as a catch. That is precisely the fix: before, that red was the *only* one and it read
as a catch. **The anchor had to be narrowed because there are two `to_points(<…>.width)` calls in
the module** — `draw_page_rule`'s `rule.width` as well — which the review's single-needle framing
hid.

### F-304 — all six whitespace characters, and the string body handled rather than documented

`_XOBJECT_PAINT` now builds its boundary class from named `_PDF_WHITESPACE` (6 chars,
ISO 32000-1 §7.2.2) and `_PDF_DELIMITERS`, over a row whose string bodies have been blanked.
**18 shapes, 0 mismatches**; the per-character sweep fires on all six (was 2 of 6), including the
appended `q\n/Im0 Do\nQ` the old class missed. Silent on `/Im0Do`, `<446F>`, `(Done. Do) Tj`,
`(Dodo) Tj`, `(Do) Tj`, the escaped-delimiter form, and **`(Scan Do now) Tj`** — the false
positive. The round chose to **handle** the string-body case rather than caveat it, ~30 lines,
*"makes the docstring's existing sentence true instead of needing a caveat"*. Two limits are
stated in code rather than left implicit: a `%` comment is deliberately not interpreted (this
vocabulary writes none, and treating one as a comment would let a `Do` inside it pass), and a row
with an unterminated literal is refused outright if it contains `Do` at all.

**This also discharges the latent risk F-304 named**: CARD-210 edits the footer link line, and
`(Scan Do now)` is measured silent.

### F-302 / F-303 — the figures, and a third correction the review did not list

**F-302**: the unfinished *"35 px at the book's 300 DPI…"* is now *"9 device px, 0.76 mm, at the
book's 300 DPI — the face's own ink descent at the footer's size, 42 px of type whose declared
ascent/descent is (39, 10)"*, re-measured independently of the test with its own Pillow render
(`lb` vs `ls` ink rows): offset 0 for `001`, `20 x 25` and `Solve it online`, **offset 9** for the
typed link; 9/300 in = 0.762 mm. **And the review was wrong that 35 is not any figure in this
system** — `type_px(8.5, 300) == 35`, the interior clue type size, named in two places. The fix
names that provenance rather than calling 35 unattributable.

**F-303**: fixed in **three** code sites plus ADR-0042's History entry; the fourth place was the
card body and is corrected above.

**A third review claim measured wrong, and this one is the interesting one.** F-301's shape list
asserts that an attribute constant and a comprehension-built argument *do* rise under the old
guard. Both **MISSED**. The only thing that made any shape rise was a bare `Constant` sitting in
some call's args — so the old guard's reach was **narrower** than the review's own enumeration
implied, not wider. The review's enumeration was itself a claim about an instrument, made without
running it.

### Numbers

**Node ids 259 → 261**, +2, 0 removed, 0 renamed, no parametrize id moved — re-derived from a
`git archive` tree with `${=MODS}`, **both sides returning non-zero counts**, so the "0 tests, 0
removed, 0 added" shape did not occur. The two additions are the six-character sweep with its
five string-body negatives, and `test_the_writer_refuses_a_multi_line_appended_paint` — the row
the old class missed, end to end through the writer. **That second one is the cell that would
have been green before the fix, so it is what makes the widening load-bearing.**

Runs: impact at **18** modules (the review's 16 plus the two other `book_vector` consumers the
`Do` change reaches) → **1008 passed, 0 failed, 0 skipped**, 3–4 min; baseline consumers plus
touched modules → **366 passed, 1 skipped**, 25–35 s; `tests/test_cli.py`, the structural
layering and component-map guard → **135 passed**; the card's own module → **65 passed**.
**One skip, attributed by name** — `test_book_pdf_memory.py`'s
`test_the_same_pair_under_an_address_space_cap_the_kernel_enforces`, macOS `setrlimit(RLIMIT_AS)`,
that file 0 lines changed. **No load figure.** Mutants in copies outside the repository, each
deleted, `__pycache__` swept, no `.pyc` written in the worktree, **no `git stash`**.

### Owed, and not to this card

**F-307** — `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture` now names a claim that
is false of the shipped page. The class body is honest and controlled; the **name** is the debt,
and it belongs to **CARD-309**, which converts the page and will delete or re-point the class.
Recorded there.

- [Fix 1] `5d95abc3` — all five in-scope findings closed with measurement on both sides; the
  round re-measured and corrected its own prose once, and corrected the review three times.
- [Gate] Merge gate next. The round's verdict, which I accept: a cycle 2 would re-review prose
  that is now instrumented, and what it would **not** reach is the full suite, which is the
  gate's job.

---

## Merge gate — **GREEN**, merged `8c81e00f`

Gated commit **`fca2fea1`** (`main` merged into the branch; **clean, no conflict**). Lock taken
at the absolute main-checkout path with an absolute `worktree:` line, released on completion.

| arm | result |
|---|---|
| full suite | **9791 passed · 27 skipped · 1 xfailed · 0 failed** in **22:03** |
| AC/EC by node id (the six furniture classes) | **25 passed · 0 skipped** |
| coverage proof | `src` + `tests` **byte-identical** to the gated commit, both before the merge and on `main` after it |

**All 27 skips carry their reason in the log this time**, because the gate ran with `-rs` rather
than recovering them afterwards from the marker population: **26 `DATABASE_URL is not set`** plus
**1 `setrlimit(RLIMIT_AS)` the kernel refuses**. That matches the population derived on CARD-308's
gate exactly, and this is the first gate today where the figure is *read* rather than
reconstructed.

### The gate measured the card next door's thesis, live

Step 3's rival-pytest census read **4** processes matching `-m pytest`. Exactly **one** is a real
run (pid 25440). The other three are **CARD-304's review cycle 2 harness**: its `zsh -c` mutant
wrapper, and a `sleep 30 | grep -- '…Python -m pytest'` pipeline *with its grep* — the probe shape
whose argv carries the pattern. So the naive count **overstates by 3 against a ground truth of
1**, in my own gate, from a sibling worktree, while cycle 2 was reviewing the very instrument
that distinguishes them. CARD-304's corpus did not need another entry; it got one anyway.

### Two instrument defects of my own, in the gate harness

1. **The first gate run failed at step 1 and reported exit 0.** The merge aborted — the worktree
   held an untracked copy of the cycle-1 review YAML that `main` had since started tracking — and
   the script's `exit 1` was **masked because I piped it to `tail`**, so the pipeline returned
   `tail`'s status. The log is what caught it; the exit code said the gate passed. Same family as
   the day's other blind readings, this time in the harness built to measure with. Re-run with the
   status unmasked.
2. Before removing the worktree's copy I verified it **byte-identical** to `main`'s tracked one
   (sha256 `2740267f…`, 54676 bytes both) rather than assuming the duplicate was redundant.

### Closing figures

Cumulative `560d7e09..5d95abc3`: **9 files, +2718/−83**, one new module. **Node ids 236 → 261**
across the round and the fix (+25, 0 removed, 0 renamed). `Touches` was restated from the diff at
review time and held through the fix round — same file set.

**Not closed here, by design:** ADR-0042/R1 stays unflipped (G-4 — this card converts one piece of
one kind), guide/TOC/answer still carry no frame, and **F-307's class-name debt is recorded on
CARD-309**, which converts the page. **CARD-309's prerequisite is now discharged**: it can convert
the puzzle page without shipping pages that have no number.
