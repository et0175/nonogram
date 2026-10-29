# CARD-298: `_write_pdf` chooses a medium per page, the two raster exceptions are declared and guarded, and the book baselines are re-recorded once

**Status:** in progress
**Priority:** P2
**Category:** enabler
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/298-per-page-medium-and-the-raster-declaration
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-298
**Source:** ADR-0042 (DEC-048), 2026-10-25; CARD-293's spike §6 item 5. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 65
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-295, CARD-296, CARD-297, CARD-227
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_pdf.py, tests/fixtures/book_baseline_*.json, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md <!-- CORRECTED 2026-10-29 at dispatch: the declared path was `tests/fixtures/book_baselines/**`, and **no such directory exists**. The real layout is FLAT, in `tests/fixtures/` itself: **21 `book_baseline_*.json` files** (~1.0 MB with their companions), plus **2 `book_baseline_card200_guide_page{1,2}.jpg`** which are card200’s guide-page images, not JSON baselines. So the card body’s and AC-5’s figure of **21 is CORRECT** — the orchestrator first counted 23 by including those two jpgs, which is the wider domain, not a discrepancy. AC-5 says "exactly the 21": if a re-record also moves either jpg, that is a finding to raise, not a number to adjust. -->
**Review score:** —
**Started:** 2026-10-29
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The three page kinds are vector (CARD-295/296/297) and two are still raster. This
card makes that split **explicit, declared, and mechanically guarded** — and
re-records the baselines the change moves.

1. **Per-page medium selection in `_write_pdf`.** The writer already drives
   `PIL.PdfParser` by hand (`:379`, `:7047`, `:7105`) — it has not called
   `Image.save(save_all=)` since CARD-145. Each PDF page is its own content
   stream, so **per-page mixing is a sanctioned end state, not a migration
   artefact** (ADR-0042/R2's own words). Make the choice of medium a named,
   single decision point rather than a condition scattered across the page loop.
2. **ADR-0042/R1's derived guard** — no interior page references an image
   XObject. Write
   `tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject` and
   **flip R1's check from `review-lens` to that node id** in the same change.
3. **ADR-0042/R2's derived guard** — every raster page is declared with a
   reason. Write
   `tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason`
   and flip R2's check likewise. **Per ADR-0039/R2 this test is DERIVED and
   default-DENY: a page whose medium it cannot classify is a FAILURE, never a
   silent pass.** The declared set is exactly `{cover, section dividers}`, and
   it shrinks to `{cover}` when CARD-231 lands — so the test must read the
   declaration rather than hard-code the pair, and **a declaration whose reason
   has expired must fail too** (R2's clause: *"once CARD-231 lands, the divider's
   exception goes with it"*).
4. **Re-record the book baselines, once.** State the scope precisely, because
   this was overstated earlier in the phase's own history and the correction
   matters:
   - **The 21 book baselines move.** That is the whole of the byte-identity cost,
     and it is the board's most-rehearsed move — the baselines have been
     superseded **20 times already**.
   - **CON-019 does NOT break.** Its property —
     `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` — holds
     COMP-007's **CLI and web** exports byte-identical, and ADR-0042 does not
     reach them. Do not touch it.
   - **The A4 golden does NOT break.** ADR-0036/R1's golden captures the
     **no-PageSpec default path** plus the CLI's bytes — neither is a book
     interior.
   Record the new baselines with the load average at both ends (CARD-292's AC-6
   convention) and say in the card what changed and by how much.

## Acceptance criteria

- **AC-1** (no interior page is a bitmap, derived over every page kind): *Given*
  any interior PDF on any export path — the interior, the proof sheet, any
  future one — *then* no page of a vector kind references an image XObject.
  (test: `tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject`
  — the exact node id ADR-0042/R1's comment names, so item 2's flip lands on a
  real test. **Derived**: it enumerates the interior's pages from the page plan,
  not from a written list.)
- **AC-2** (every raster page is declared, and the guard cannot silently pass):
  *Given* the written PDF, *then* each raster page matches a live declaration
  with a reason, an undeclared raster page FAILS, **and a page whose medium the
  test cannot determine also FAILS**. (test:
  `tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason`.
  **Two mutants required per ADR-0039/R1** — one inside the claimed region: make
  a puzzle page raster and watch it red; one at the claim's **edge**: remove the
  divider's declaration while the divider is still raster, and watch it red.)
- **AC-3** (the expired declaration is caught): *Given* a declaration whose
  reason has expired — the divider's, simulated as though CARD-231 had landed and
  the page were vector — *then* the guard reds on the stale declaration rather
  than ignoring it. (test:
  `test_a_declaration_whose_reason_expired_is_a_defect`. This is the clause most
  likely to rot, because nothing else will notice it the day CARD-231 merges.)
- **AC-4** (the medium decision has one home): *Given* the writer, *then* the
  choice of medium per page is made at exactly one place, derived from the
  module's AST and default-DENY. (test:
  `TestWritePdf_TheMediumIsChosenInOnePlace` — per ADR-0039/R2; a branch it
  cannot classify is a failure.)
- **AC-5** (the baselines move once, and nothing else does): *Given* this card's
  branch, *then* exactly the 21 book baselines are re-recorded, **CON-019's
  property test and the A4 golden are untouched and green**, and the before/after
  interior size and generation time are recorded. (**gate**: the baseline diff
  enumerated; `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` and
  the A4 golden run and pass; figures recorded with the load average at both ends.)

## Engineering constraints

- **EC(ADR-0042/R1):** across a seeded corpus of books spanning page counts,
  trims and tier mixes, no interior page of a vector kind carries an image
  XObject. test: `PropertyTest_Interior_NoVectorPageCarriesABitmap` (minimum case
  count asserted inside the test).
- **EC(ADR-0042/R2):** across the same corpus, the set of raster pages equals the
  set of declared raster pages — neither direction slack. test:
  `PropertyTest_Interior_RasterPagesEqualDeclaredRasterPages`.

## Guardrails

- **G-1: do not convert the cover or the dividers.** They are the two declared
  exceptions this card exists to *declare*, not to remove. Converting them would
  make the guard vacuous and pre-empt both ADR-0042/R2's expiry clause and the
  owner's 2026-10-25 decision on divider design.
- **G-2: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  or the A4 golden.** They do not break here (see item 4), and "it failed so I
  updated it" on a byte-identity tripwire is how a real regression gets absorbed.
  If either reds, that is a **finding to raise**, not a baseline to refresh.
- **G-3: do not lower a corpus minimum, and do not regenerate
  `tests/fixtures/**` beyond the 21 book baselines named in item 4.** The
  standing rule is that `tests/fixtures/**` is never regenerated; this card holds
  the one scoped, enumerated exception, and it must be enumerated in the card.
- **G-4: do not edit `src/nonogram/export/**`.**
- **G-5: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-6: ADR-0042/R1's and R2's lenses must not survive this card.** Both flips
  are part of the card. Merging with either still `review-lens` ships a rule
  whose delivery card is closed and whose check is a placeholder — the exact
  defect repaired in commit `c12c33ce` and again in ADR-0032/R3.
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`, see
  `meta/profiling/rank_durations.py:45`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject, on any export path (check: review-lens → this card's AC-1)
- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: review-lens → this card's AC-2)
- ADR-0042/R3 — the writer consumes positions and derives none (check: review-lens)
- ADR-0042/R5 — the face is embedded whole, once per file (check: tests/test_book_pdf.py::test_the_interior_embeds_the_projects_own_face)
- ADR-0036/R1 — the A4 golden's byte identity for the no-PageSpec default path (check: the A4 golden)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)
- CON-019 — book geometry never changes the CLI's or web UI's exports, byte-for-byte (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- INV-013 — the interior holds no cover page; parity counts from interior page 1 (check: PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage)
- ADR-0039/R1 — a claim needs a control that CAN fail; a comment saying what a test catches needs two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline is exactly stdlib + Pillow + NumPy (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)

## Architecture context

- **FR:** FR-043 (the interior without the cover), FR-030, FR-032
- **NFR:** NFR-008
- **ADR:** **ADR-0042** (R1, R2, R3, R5 — this card lands two of its three outstanding checks), ADR-0036/R1-R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml — R1's and R2's checks become live test refs here, so the trace rows for them are re-stamped in this card.

## [Premise RE-MEASURED at dispatch — 2026-10-29, orchestrator]

**Dependencies: all four done.** CARD-295 `ec6e4a06`, CARD-296, CARD-297
`73fa5cb2`, CARD-227 `8579094a` — read from the card files, not the board.

**This is the card that makes CARD-297's work reach a reader, and that is worth
stating plainly because CARD-297 deliberately did not.** Measured on main after
its merge: `book_toc_vector` and `book_answer_vector` have **zero call sites
anywhere in `src/`**, `book_pdf_generator.py` imports neither, and only the two
test files import them. So the TOC and answer pages exist as writers and reach no
artefact a reader receives. **Everything CARD-297 declared latent becomes
reachable here**, including its declared clip divergence: on the 10×10 cm trim the
two writers clip a caption **one character apart** (Pillow's `getlength` reads
491.98 px and the `/Widths` sum 492.87 px across the same 492 px measure), which
is declared and machine-checked as `_DECLARED_CLIP_DIVERGENCE` on the argument
that neither medium is wrong. The moment `_write_pdf` chooses the vector medium
for an answer page, that divergence stops being latent.

**The baseline layout was mis-declared and is corrected above** — flat
`tests/fixtures/book_baseline_*.json`, 21 of them, not a `book_baselines/`
directory.

**Inherited, not created here, and the gate cannot see it:** this card's system
contract names `ADR-0006/R1 — the dependency baseline ... (check:
TestDependencyBaseline_IsExactlyPillowAndNumpy)`. That ref has **zero
definitions anywhere in the repo** and is text-resolved by **110+ files** (the
scored backlog, ~107 review YAMLs, and two prose mentions in `tests/`), so the
rule reads as mechanically checked and is not checked at all. Measured while
gating CARD-297. **Do not take it on** — but do not report ADR-0006/R1 as
verified by that ref either; check the substance instead (`pyproject.toml`
unchanged, and no third-party import added).

### Owed to this card by CARD-297's review cycle 2 — F2-01

CARD-297's AC-3 guard derives its watched set from `ContentStream` by `vars(cls)`,
so **a drawing door inherited from a base class is invisible to it**. Cycle 2
built that case — a mixin ahead of `ContentStream`, the own surface left at 16 —
and a `stream.hatch` grid walk was **ADMITTED** with both guard cells green and
`_UNCLASSIFIED_DOORS` empty. It is **not live at HEAD**, because today's class
inherits only `object` and `dir()`/`vars()` agree on its 16 members, so this is a
durability gap rather than an open route. It was deliberately **not** taken on
CARD-297's last cycle for a reason that applies to whoever fixes it: **it changes
the guard's own derivation, and a merge gate does not mutate** — a `dir()`-based
version that silently returned everything would pass exactly as a correct one
would. **It must ship with its control in the same commit.**

## Worktree notes

- **This card is where ADR-0042 stops being a decision and becomes a checked
  rule.** Four of its seven rules shipped as `review-lens` on 2026-10-25 because
  their tests did not exist (commit `c12c33ce`); R5 flips in CARD-294, R1 and R2
  flip here, and R6 flips in CARD-299. R3 and R7 stay lenses by design — R3 is a
  "derives none" prohibition and R7 is a scope statement, neither of which a test
  can own.
- **`tests/fixtures/**` is otherwise untouchable**, so item 4's scoped exception
  must be enumerated file by file in the worktree notes when it is done. A
  reviewer should be able to count the re-recorded baselines without running
  anything.
