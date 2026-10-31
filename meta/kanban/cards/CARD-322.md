# CARD-322: The last four interior kinds become operators, and ADR-0042/R1 flips with the final conversion

**Status:** ready
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** split from CARD-309 on owner decision, 2026-10-30. CARD-309 was estimated 1d and held an assembly point that does not exist, five kind conversions, 21 baselines, R1's flip, CARD-297's clip divergence and a reader population of 12+8 modules. The split follows the card's own item 1 — *"one kind at a time, each removal complete… what makes this card incremental rather than all-or-nothing"*.
**Split from:** CARD-309
**Idea:** —
**Wave:** —
**Created wave:** 68
**Deferred waves:** 0
**Depends on:** CARD-309, CARD-329, CARD-330, CARD-331 <!-- WIDENED 2026-10-30 at CARD-309's re-cut, from `CARD-309` alone. CARD-309 implemented this card's conversion to measure it and reverted it: 189 failures + 75 errors across 22 modules, four causes. Three of them are now cards and every one of them is a PREREQUISITE, not a sibling -- CARD-329 (the one-image reader), CARD-330 (the 0.169 mm the media disagree by, which changes the VALUE of every placed-edge expectation), CARD-331 (the difficulty-dot instrument, which on a vector page measures a page the product no longer draws and does so SILENTLY). Converting before CARD-330 decides its question means re-deriving every edge expectation twice. -->
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_guide_vector.py, src/nonogram/admin/book_toc_vector.py, src/nonogram/admin/book_answer_vector.py, tests/test_book_pdf.py, tests/fixtures/book_baseline_*.json, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

**CARD-309 builds the assembly point and converts the puzzle page.** This card converts the four that
remain — **TITLE, GUIDE, TOC and ANSWER** — removes their declarations, and **flips ADR-0042/R1 with
the last one**.

It is the repetition half by design, and it is genuinely cheaper **only if CARD-309's assembly point
is real**. `book_guide_vector`, `book_toc_vector` and `book_answer_vector` all import
`book_pdf_generator` at module level, so none can be called from its page walk without a cycle;
CARD-309 owns that problem. **If you arrive and the assembly point turns out to be a workaround
rather than a design, raise it rather than building a second one.**

## The declarations will name this card, and a live guard enforces it

`tests/test_book_pdf.py::test_no_declaration_outlives_the_cards_that_remove_it` **reds the day a card
named in `expires_with` is marked done while its declaration remains.** CARD-309 re-points TITLE,
GUIDE, TOC and ANSWER from `CARD-309` to **`CARD-322`** precisely so that guard stays honest across
the split.

**So this card cannot be marked done until all four entries are gone.** Verify on arrival that the
re-pointing actually happened — if CARD-309 shipped without it, that is a **finding about CARD-309**,
raised, not absorbed.

## [Added 2026-10-30 at CARD-309's re-cut] This card now closes the phase, and the conversion has been measured once already

**CARD-309 implemented this card's conversion, measured it, and reverted it.** That
measurement is this card's most valuable inheritance and must be re-derived, not
trusted: the conversion reds **189 failures + 75 errors across 22 test modules**,
with **four** causes of which only one is a PDF reader.

Three are now prerequisites (`Depends on` widened accordingly):

- **CARD-329** — `tests/helpers/pdf_pages.py`'s one-image reader raises
  `KeyError: b'XObject'` on an operators page. The small, genuine reader conversion.
- **CARD-330** — the raster and vector media place the same grid **0.169 mm** apart
  (**2 px at the interior's own 300 dpi** — one rounding step) against
  `EDGE_TOLERANCE_MM = 0.1`. **Every placed-edge expectation in the tree changes
  value with the medium**, so converting before that question is answered means
  deriving every edge expectation twice and probably loosening a bound by accident.
- **CARD-331** — the difficulty-dot accounting instrument monkeypatches the *raster*
  drawing site, so on a vector page it measures a page the product no longer draws —
  and a monkeypatch on an uncalled function **passes silently** rather than erroring.

The fourth cause (frozen AST censuses in `tests/test_book_export_interior_cover.py`)
CARD-309 re-derived on its own branch.

**What this card inherits ready-made:** the assembly point,
`src/nonogram/admin/book_interior_vector.py` — downstream of all five writers, the
direction a **parameter** (`InteriorPageWriters`) rather than a registry or a lazy
import, with **no cycle anywhere** in the `book_*` graph (verified by an independent
`ast` walk at the decompose station) and `tests/test_cli.py`'s structural guard
passing **unmodified**. Copy that convention; do not re-litigate it.

**What this card alone owns:** the four remaining conversions, the **21 baselines**,
CARD-297's declared clip divergence, and **ADR-0042/R1's flip — with the last
conversion, not before.** CARD-298, CARD-299 and CARD-309 each refused that flip on
their own initiative and each was right.

**And this card is what finally gives the phase a reader.** CARD-309 ships the
assembly point with **zero production call sites**, which is verbatim the condition
it was cut to end. The conversion is the call site. Until this card lands, nothing in
`src/` turns an interior page into operators.

## [Added 2026-10-30 at CARD-309's review] This card owes CARD-306's F-307 rename, and until now nothing said so

CARD-309's review cycle 1 raised this as its **F-002**, and it was a real routing
hole rather than a disagreement: CARD-309's record claims it hands the rename to
this card *"with a guardrail that permits it"*, and measured, **this card had
zero mentions of F-307 or the class name**, while its G-5 carried the same
unqualified prohibition CARD-309 had just declined under. So the rename was
owed by a card that did not know it, behind a guardrail that forbade it.

**CARD-309 was right to decline.** G-5 is task-level authoritative and is
weakened only at the decompose station. What failed was the routing, and it is
fixed in two places: G-5 above now carries the one named exception, and this
section records why the debt exists.

**The debt itself:** `TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`
says the vector puzzle page draws **no** sheet furniture. CARD-306 then gave it
folio, frame rules, a grid-size label and a QR block — so the name is now the
opposite of the truth while the assertions underneath are correct. A test whose
name contradicts its body is this board's most-cited defect family, and it is
sitting in the file this card has to edit anyway.

## [Owner steer 2026-10-30] This card is the destination

*"Let's aim at switching on vector for the interior (not dividers) — don't spend much
time on fixing-updating raster."*

So this card is the one the phase is aimed at, and the steer changes what it inherits
rather than what it does. **CARD-330 will pin the raster placed-edge expectations as
legacy instead of re-tuning them**, so this card's conversion is what *retires* them —
expect to delete raster expectations here, not satisfy them. Same for **CARD-331**'s
raster arm of the difficulty-dot accounting: its lifetime ends with this card.

<!-- ORCHESTRATOR CORRECTION 2026-10-31, measured during CARD-331's review cycle 1
     (F-005) and verified here. THE SENTENCE ABOVE IS HALF FALSE, AND THIS CARD'S
     OWN NEXT PARAGRAPH REFUTES IT: "Dividers stay raster, unchanged."

     CARD-331's accounting now carries one arm per PageMedium, and PageMedium keeps
     RASTER for the cover and the divider. The arm is enumerated on the MEDIUM, not
     on the puzzle page, so the medium survives this conversion and the arm must
     survive with it. Deleting the arm REDS CARD-331's arm-per-medium cell
     (tests/test_book_difficulty_dots.py, the TheVectorArmReadsTheStream /
     AnArmWhoseMechanismIsDeadFails classes).

     THE INSTRUCTION THIS CARD INHERITS, stated once: RE-POINT, DO NOT RETIRE.
     Keep the raster arm; change its kind from PageKind.PUZZLE to a kind
     `_RASTER_DECLARATIONS` still declares raster, and move with it the 27 cells of
     that module which read the interior as bitmaps.

     Expect ONE deliberate red on arrival, by design, not by drift:
     `test_each_arms_mechanism_is_still_exercised[raster]` is built to fail the day
     this card converts the puzzle page, and its message is a work order naming the
     arm, its mechanism and the remedy. Satisfy it by re-pointing. DO NOT WIDEN IT.

     CARD-331's F-005 also fixed its own remedy string, which had offered
     "retire this arm" -- an option its own guard forbids -- so the work order you
     will read is now the corrected one. This card owes the repair of the sentence
     above; it is left in place rather than rewritten so the record shows what was
     claimed when. -->

**Dividers stay raster**, unchanged: ADR-0042/R2 makes the divider an exception by
scheduling rather than technique, and CARD-231 redesigns that page to be *born* vector.
So "switch the interior to vector" means the four remaining kinds **and not the
divider**, which is exactly the scope this card already carries — and R1's flip is
still only legal once the five temporary entries are gone, which ADR-0042's own Rules
comment states.

## What to implement

1. **One kind at a time, each removal complete.** For TITLE, GUIDE, TOC and ANSWER: wire the vector
   writer into the interior's page walk through CARD-309's assembly point, delete that kind's entry
   from `_RASTER_DECLARATIONS`, and let `_write_pdf`'s representation refusal prove the removal —
   a kind whose declaration is gone but whose page is still a bitmap is **refused, not shipped**.
2. **Flip ADR-0042/R1 here, and only with the last kind.** Not before. A test asserting *"every page
   is the medium its kind declares"* **passes while R1 is violated**, as long as any interior kind is
   still a declared exception — which is why CARD-298 and CARD-299 each refused this flip and were
   each right. **R1's `check:` becomes a live node id in the same commit as the final conversion.**
3. **Delete CARD-297's `_DECLARED_CLIP_DIVERGENCE` when the answer page converts** — or keep it with
   a new argument that names the converted page. **Silence is not an option.** The standing position,
   recorded on CARD-298 and CARD-299 and still unchallenged: once the answer page is vector there is
   **one** answer-page writer, and the book clips by `/Widths`, the measure the reader's own viewer
   uses — so the declaration becomes a statement about a page nobody prints. **Verify the argument
   against a converted page before acting on it; it has never been tested against one.**
4. **The readers these four kinds reach**, derived per module across **both** populations — the
   twelve that import the one-image reader and the **eight** that consume `.interior_pages()`
   directly (see CARD-309's section on AC-3's blind spot). Per ADR-0039/R2 a module the walk cannot
   classify is a **FAILURE**, not a silent pass.
5. **The baselines these kinds move, enumerated file by file**, with the count stated and the
   interior's size and generation time recorded at both ends.

## Acceptance criteria

- **AC-1** (R1 is true and checked): *Given* a written interior, *then* **no page of any of the five
  converted kinds** references an image XObject, `_RASTER_DECLARATIONS` holds **only the cover and
  (until CARD-231) the divider**, and **ADR-0042/R1's `check:` is a live node id naming the test that
  proves it.**
- **AC-2** (each removal is complete, proved by refusal): *Given* a kind whose declaration is removed,
  *then* a bitmap handed in for that kind is **refused by the writer**. **Two mutants per
  ADR-0039/R1**, one inside the region and one at the edge: **the last kind converted**, and **a kind
  converted while its declaration is left behind**.
- **AC-3** (the readers survive, both populations): *Given* the converted interior, *then* every test
  module that reads a book interior passes — **derived across both routes, not listed**, and a module
  needing a further edit is a **finding to raise, not absorb**.
- **AC-4** (the baselines move once, enumerated): *Given* the branch, *then* the re-recorded baselines
  are listed file by file, the count is stated, and **CON-019's property test and the A4 golden are
  untouched and green**.
- **AC-5** (the clip divergence is resolved, not inherited): *Given* the converted answer page, *then*
  `_DECLARED_CLIP_DIVERGENCE` is either deleted with the measurement that justifies it, or kept with a
  new argument naming the converted page.
- **AC-6** (an owner render exists): *Given* the converted interior, *then* a rendered interior is
  produced under `~/Documents/nonogram-reviews/CARD-322/`. **Standing rule: image-pipeline changes
  need a rendered eyeball, not just green tests** — and after this card **every interior page but the
  divider is vector**, which is the render the owner has been waiting for since the phase opened.

## Engineering constraints

- **EC(ADR-0042/R1):** across a seeded corpus spanning page counts, trims and tier mixes, **no
  interior page of a converted kind carries an image XObject**, with a minimum case count asserted
  inside the test.
- **EC(ADR-0042/R2):** across the same corpus, the set of raster pages **equals** the set of declared
  raster pages — neither direction slack — and that set shrinks to **the cover plus the divider**.

## Guardrails

- **G-1: do not convert the cover.** Its declaration is permanent (`expires_with: ()`); a photograph
  is correctly raster.
- **G-2: do not convert the divider.** It is CARD-231's, by the owner's 2026-10-25 decision that the
  new design should be **born** vector rather than the old one converted.
- **G-3: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` or the A4
  golden.** Neither is a book interior. If either reds, that is a **finding to raise**, not a baseline
  to refresh.
- **G-4: do not lower a corpus minimum**, and regenerate nothing under `tests/fixtures/**` beyond the
  baselines item 5 enumerates.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids
  included. **ONE NAMED EXCEPTION, granted at the decompose station 2026-10-30**
  (a guardrail is weakened here and nowhere else — never in a worktree):
  `tests/test_book_puzzle_page_vector.py:1950`'s
  `class TestPuzzlePage_DrawsTheDrawingAndTheBandAndNoSheetFurniture`
  **may be renamed**, and only it. Its *body* is honest; its **name** became
  false when CARD-306 gave the vector puzzle page exactly the sheet furniture
  the name denies (folio, frame rules, grid-size label, QR block). CARD-306
  raised it as F-307; CARD-309 examined it, found the only fix is a rename, and
  **correctly declined** under this very guardrail — see its round's findings.
  The rename is this card's because this card converts the kind and will be in
  that file anyway. Spell the replacement for what the class now asserts, and
  re-stamp every consumer of the old node ids in the same commit: a renamed
  class is a node-id change, so `ADDED_SINCE_BEFORE`, any `_SEEN_REGIONS`-style
  census and any frozen snapshot naming it move **with** it or the gate finds
  them.
- **G-6: do not weaken `_write_pdf`'s representation refusal to let a conversion land.** It is the
  thing that makes a partial conversion safe; a card that loosens it to get green has removed its own
  safety net.
- **G-7: do not edit `tests/test_cli.py`'s structural layering guard.** If a writer cannot be reached
  without violating it, that is CARD-309's assembly point failing, and it is a finding.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators (check: review-lens → **this card flips it**, with the last conversion)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard, plus the landing-direction half)
- ADR-0042/R6 — a claim about an interior page is asserted against the content stream (check: CARD-299's)
- ADR-0036/R1 — the A4 golden's byte identity for the no-PageSpec default path (check: the A4 golden)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte
- CON-020 — the 10 pt interior type floor, clue digits exempt **by their mark** (check: CARD-314's)
- INV-013 — the interior holds no cover page; parity counts from interior page 1
- ADR-0039/R1-R2 — a claim needs a control that CAN fail; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0039/R4 — a figure's instrument is part of the figure (check: **executing**, CARD-304)

## Architecture context

- **ADR:** ADR-0042/R1-R2-R6, ADR-0039
- **Components:** COMP-009 and the four vector page writers
- **Trace:** ADR-0042/R1's `check:` is re-stamped here, from a lens to a node id.

## Worktree notes

- **Expect the merge gate to find a frozen registry this card moves.** Two cards in one hour on
  2026-10-30 went red at the gate on cross-card censuses that `review.test_scope: impact` is
  structurally unable to see — CARD-314 on the ref census (three `trace.yml` additions, and **a third
  baseline hidden behind the one that short-circuited**) and CARD-269 on the browser-family register
  (35 unregistered tests). **This card re-stamps `trace.yml` and moves baselines. Derive which
  registries your diff touches and run them before the gate does.**
- **Do not paste the number a frozen baseline prints when it reds.** Both guards say so themselves:
  re-derive the symmetric difference, assert **nothing left**, and resolve each entrant to a real
  `def`/`class` line read off the line. A class that *shrinks* because a review report was synced in
  is signal loss, not a repair.
- **CARD-288 depends on this phase.** Its four tests obtain pages from `interior_pages()`, which is
  declared `-> List[Image.Image]` and stops being that here. It is correctly sequenced after.
