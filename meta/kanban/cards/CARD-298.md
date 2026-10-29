# CARD-298: `_write_pdf` chooses a medium per page at one named decision point, and the raster exceptions are declared, derived and default-DENY

<!-- NARROWED 2026-10-29 by owner decision after implementation round 1 hit the scope gate. This card was cut expecting to ALSO convert interior pages to vector (ADR-0042/R1) and re-record the 21 baselines. Both belong to CARD-299: `tests/helpers/pdf_pages.py:34-40` asserts one image XObject per page for EVERY page, so a single vector page breaks all 14 test modules that read a book interior, and that reader conversion is ADR-0042/R6 = CARD-299 — which declares `Depends on: CARD-298`. The slice, not the implementation, was wrong. This card is now the MECHANISM card; R1's flip and the baselines move to CARD-299, which breaks the cycle because CARD-298 no longer needs it. -->

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
**Touches:** src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_vector.py, tests/test_book_pdf.py, tests/test_book_solved_answer_key.py, tests/test_book_export_interior_cover.py, tests/test_book_pdf_memory.py, tests/test_book_puzzle_page_vector.py, tests/test_book_pdf_vector_primitives.py, tests/helpers/book_corpus.py, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md <!-- AMENDED 2026-10-29 on narrowing: `tests/fixtures/book_baseline_*.json` REMOVED — zero baselines move here (see AC-5). Added the eight files round 1 was forced into: `book_vector.py` (so the mixed writer emits a vector page and its font objects through ONE definition rather than a second transcription of the /FontDescriptor), the four `_write_pdf` call sites the required `kinds=` keyword forced, `test_book_solved_answer_key.py` (F2-01, explicitly owed to this card), `test_book_export_interior_cover.py` (four CARD-206/262 AST pins re-derived row by row), and one docstring rename. --> <!-- CORRECTED 2026-10-29 at dispatch: the declared path was `tests/fixtures/book_baselines/**`, and **no such directory exists**. The real layout is FLAT, in `tests/fixtures/` itself: **21 `book_baseline_*.json` files** (~1.0 MB with their companions), plus **2 `book_baseline_card200_guide_page{1,2}.jpg`** which are card200’s guide-page images, not JSON baselines. So the card body’s and AC-5’s figure of **21 is CORRECT** — the orchestrator first counted 23 by including those two jpgs, which is the wider domain, not a discrepancy. AC-5 says "exactly the 21": if a re-record also moves either jpg, that is a finding to raise, not a number to adjust. -->
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
2. **The medium-agreement guard** — every page is the medium its kind
   declares, in **both** directions: a bitmap handed in where operators were
   declared is refused, and a content stream under a raster declaration is
   refused. Write
   `tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject`.
   **ADR-0042/R1's flip does NOT happen here** <!-- NARROWED 2026-10-29: R1
   states that *puzzle pages, answer pages, the TOC and the guide are written as
   content-stream operators*. While all four are declared raster exceptions, a
   test asserting "every page is the medium its kind declares" passes **while R1
   is violated** — marking a rule mechanically checked by a test that cannot see
   its breach, the exact defect repaired in `c12c33ce` and again in ADR-0032/R3.
   R1 stays a `review-lens` until CARD-299 converts the readers and the pages.
   Round 1 refused this flip on its own initiative; that judgement is adopted. -->
3. **ADR-0042/R2's derived guard** — every raster page is declared with a
   reason. Write
   `tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason`
   and flip R2's check likewise. **Per ADR-0039/R2 this test is DERIVED and
   default-DENY: a page whose medium it cannot classify is a FAILURE, never a
   silent pass.** The declared set is **seven**, not two <!-- CORRECTED
   2026-10-29: the card predicted `{cover, section dividers}`. Measured, it is the
   two ADR entries plus the five interior kinds that cannot convert until
   CARD-299: COVER (permanent), DIVIDER (expires with CARD-231), and TITLE /
   GUIDE / TOC / ANSWER / PUZZLE (each expiring with CARD-299). Every entry
   carries a reason, an authority and an `expires_with`, so the set shrinks by
   deletion as each converting card lands — which is precisely what AC-3's expiry
   check exists to force. The figure was NOT adjusted to fit the implementation:
   the guard reads the registry rather than any pair, as item 3 itself requires,
   and seven is what the repo's own blockers produce. --> — so the test must read
   the declaration rather than hard-code any set, and **a declaration whose reason
   has expired must fail too** (R2's clause: *"once CARD-231 lands, the divider's
   exception goes with it"*).
4. **The book baselines do NOT move, and that must be demonstrated rather
   than assumed.** <!-- NARROWED 2026-10-29: the card predicted all 21 would be
   re-recorded. They do not move here, because nothing converts here — the
   prediction was about CARD-299's conversion and now belongs to it. -->
   - **Exactly 0 of the 21 `tests/fixtures/book_baseline_*.json` are
     re-recorded**, and neither of the two `book_baseline_card200_guide_page*.jpg`
     files moves. `tests/fixtures/**` is touched not at all, so this card needs
     **no exception to the standing never-regenerate rule**.
   - **CON-019 does NOT break.** Its property —
     `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` — holds
     COMP-007's **CLI and web** exports byte-identical, and ADR-0042 does not
     reach them. Do not touch it.
   - **The A4 golden does NOT break.** ADR-0036/R1's golden captures the
     **no-PageSpec default path** plus the CLI's bytes — neither is a book
     interior.
   Record the interior's size and generation time with the load average at
   both ends (CARD-292's AC-6 convention) and say in the card what changed and
   by how much — which, if nothing converts, is **nothing**, stated as a
   measurement rather than left blank. <!-- NARROWING RESIDUE, fixed 2026-10-29
   after review cycle 1's A-5: this said "Record the new baselines", which the
   narrowing had already made impossible — there are no new baselines. The
   load-average convention still applies, to the size/time readings AC-5 asks
   for, not to a re-record. Round 1 did take those readings (3,468,586 B and
   0.277 s on main vs 0.283 s on the branch, load stated at both ends, and the
   whole written interior sha256-identical with Pillow's two /Info dates
   masked), so AC-5's figures ARE discharged — the card just no longer asks for
   them under a heading about baselines. -->

## Acceptance criteria

- **AC-1** (every page is the medium its kind declares, derived over every page
  kind): *Given* any interior PDF the medium decision governs, *then* no page of a
  **vector** kind references an image XObject and no page of a **raster** kind is
  a content stream — both directions, refused before the buffer exists. <!--
  NARROWED 2026-10-29: this is NOT ADR-0042/R1's statement, and the card must not
  read as though it were. R1 says the four interior kinds ARE operators; this AC
  says each page matches whatever its kind declares, which is satisfiable (and
  satisfied) while all five interior kinds are declared raster. R1 is CARD-299's.
  Also measured: "any export path" does **not** reach the proof sheet —
  `book_proof.render_proof_pdf` writes through `Image.save(format="PDF",
  save_all=True)`, a second writer with no page kinds behind it, pinned by
  `test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision`, which asserts
  it by AST because both writers stamp the same `% created by Pillow PDF driver`
  comment. -->
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
- **AC-5** (nothing moves, and that is measured in two domains): *Given* this
  card's branch, *then* **exactly 0** of the 21 book baselines and 0 of the 2
  guide-page jpgs are re-recorded, `tests/fixtures/**` shows a 0-file diff,
  **CON-019's property test and the A4 golden are untouched and green**, and the
  before/after interior size and generation time are recorded with the load
  average at both ends. (**gate**: `git diff --name-only <cut>..HEAD --
  tests/fixtures/` is empty; every baseline-reading module runs green — a per-page
  digest set and a whole-file hash are **different domains**, so both readings are
  required; `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` and the
  A4 golden pass.) <!-- NARROWED 2026-10-29: was "exactly the 21 baselines are
  re-recorded". The baselines move in CARD-299. Note the gate's direction is now
  the inverse: a baseline that DOES move is a finding. -->

## Engineering constraints

- **EC(ADR-0042/R1):** across a seeded corpus of books spanning page counts,
  trims and tier mixes, no interior page of a vector kind carries an image
  XObject. test: `PropertyTest_Interior_NoVectorPageCarriesABitmap` (minimum case
  count asserted inside the test).
- **EC(ADR-0042/R2):** across the same corpus, the set of raster pages equals the
  set of declared raster pages — neither direction slack. test:
  `PropertyTest_Interior_RasterPagesEqualDeclaredRasterPages`.

## Guardrails

- **G-1: convert no page at all — not the cover, not the dividers, and not the
  five interior kinds.** They are the declared exceptions this card exists to
  *declare*, not to remove; the conversions belong to CARD-231 (dividers) and
  CARD-299 (the five interior kinds), and each declaration's `expires_with` names
  its owner. <!-- NARROWED 2026-10-29: was "the cover or the dividers". --> Converting them would
  make the guard vacuous and pre-empt both ADR-0042/R2's expiry clause and the
  owner's 2026-10-25 decision on divider design.
- **G-2: do not touch `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  or the A4 golden.** They do not break here (see item 4), and "it failed so I
  updated it" on a byte-identity tripwire is how a real regression gets absorbed.
  If either reds, that is a **finding to raise**, not a baseline to refresh.
- **G-3: do not lower a corpus minimum, and do not regenerate
  `tests/fixtures/**` at all.** <!-- NARROWED 2026-10-29: the scoped exception for
  21 baselines is withdrawn — nothing converts here, so nothing may be
  re-recorded. The standing never-regenerate rule applies without exception, and a
  baseline that reds is a finding to raise. The exception moves to CARD-299. -->
- **G-4: do not edit `src/nonogram/export/**`.**
- **G-5: no test deleted, renamed, skipped or merged — `parametrize` ids
  included.** (**gate**: node-id set difference with `-o addopts=''`.)
- **G-6: ADR-0042/R2's lens must not survive this card — and R1's MUST.** <!--
  NARROWED 2026-10-29: was "R1's and R2's". R2's derived guard is real here and
  its ref resolves, so R2 flips. R1 does NOT: flipping it would mark a rule
  mechanically checked by a test that passes while the rule is violated, which is
  the very defect `c12c33ce` and ADR-0032/R3 repaired. R1's flip is CARD-299's,
  and a round that flips it here is to be reverted, not praised. The reason is
  written into R1's own note in the ADR. -->
- **G-7: probes stay OUT of `tests/`** (`RENDER_HEAVY_SNAPSHOT`, see
  `meta/profiling/rank_durations.py:45`).

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R1 — interior pages are operators; no image XObject, on any export path (check: review-lens → **CARD-299's**, NOT this card's; AC-1 here is the weaker medium-agreement statement and must not be mistaken for it)
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
- **ADR:** **ADR-0042** (R2 lands here; R1 and R6 land in CARD-299; R3 and R7 stay lenses by design), ADR-0036/R1-R2, ADR-0039/R1-R2
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml — **R2's** check becomes a live test ref here, so only its trace row is re-stamped in this card. R1's row stays as it is until CARD-299.

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
- **`tests/fixtures/**` is untouchable here, with no exception to enumerate.**
  <!-- NARROWING RESIDUE, fixed 2026-10-29 after review cycle 1's A-6: this
  demanded that "item 4's scoped exception must be enumerated file by file",
  but the narrowing WITHDREW that exception (G-3), so the instruction asked for
  a list of something that must not exist. The reviewer should be able to see
  `git diff --name-only <cut>..HEAD -- tests/fixtures/` return nothing, which
  is the whole of the accounting. The enumeration obligation moves with the
  exception, to whichever card re-records the baselines. -->

## [Implementation round 1 — HELD AT THE SCOPE GATE, 2026-10-29, orchestrator]

Branch `card/298-per-page-medium-and-the-raster-declaration` @ **`283164a9`**, one
commit on the cut `8b307c22`, tree clean, not pushed, not merged. **10 files,
+1860/−79** — measured against the real cut base. (The round reported its diffstat
against `fb2ecb40`, which is *not* an ancestor of this branch; that reading showed
`meta/kanban/**` as changed because it reverses the orchestrator's own wave-65
commit. Against `8b307c22` **nothing under `meta/kanban/` or `meta/review/` is
touched** and `tests/fixtures/` is 0 files, as the round claimed.)

**The mechanism the card asks for is built and gated.** Verified independently:
node-id difference vs main **+23 / −0** (20 in `tests/test_book_pdf.py`, 3 in
`tests/test_book_solved_answer_key.py`, nothing moved or removed);
`_RASTER_DECLARATIONS` holds **7** entries, each with a non-empty reason, an
authority and an `expires_with` (`COVER` permanent, `DIVIDER` → CARD-231, and
`TITLE`/`GUIDE`/`TOC`/`ANSWER`/`PUZZLE` → CARD-299); `page_medium` returns RASTER
**iff** the kind is a key, so a new kind is vector by default.

**AC-5's answer is 0, and that is a fact about the slice, not a shortfall.** All
six baseline-reading test modules run **389 passed, 1 skipped** on the branch (the
skip is `tests/test_book_pdf_memory.py:1297`, `setrlimit`, pre-existing), so the
21 baselines did not need to move. The card's "the 21 baselines move / that is the
whole of the byte-identity cost" is a prediction about **CARD-299**, not about this
commit.

### Why R1 could not land here — three blockers, all confirmed structurally

1. **`tests/helpers/pdf_pages.py:34-40`** loops `for ref in parser.pages` and
   asserts `len(xobjects) == 1, "a book page is exactly one image"` **and**
   `Filter == DCTDecode` for **every page**. So one vector page in an interior
   breaks every reader of that interior — zero-or-all follows from the helper's own
   loop, not from an estimate. **14 test modules + 3 helpers** (`book_corpus`,
   `page_ink`, `pdf_vector`) read an interior through it. That conversion is
   **ADR-0042/R6, owned by CARD-299**.
2. **The puzzle page has no sheet furniture** — no folio, frame rules, size label
   or QR block — and `book_puzzle_vector`'s own docstring raises it as a gap **no
   card owns**.
3. **Layering, and the asymmetry is the point.** `book_guide_vector:103`,
   `book_toc_vector:60` and `book_answer_vector:62` all import
   `book_pdf_generator` at module level, while `book_pdf_generator:400` imports
   `book_puzzle_vector`. So the one page the interior's walk *can* call is the
   puzzle page — precisely the one with no furniture — and the other three cannot
   be called from it without a cycle.

### The scope gate fires, and the dependency graph has a cycle

`CARD-299` is `Status: ready` and declares **`Depends on: CARD-298`**, while this
card's R1 half depends on CARD-299. This commit covers **3 of CARD-299's 8
declared Touches** (`tests/test_book_pdf.py`, `tests/test_book_pdf_memory.py`,
`adr/0042-*.md`), which is `scope_gate: on`'s second clause — *covers a ready
sibling's Touches* → **escalate to the decompose station, do not polish in the
review loop.** Review cycle 1 was therefore NOT dispatched: the card's R1
contract cannot be met in this order, and a reviewer would only rediscover that.

**The round refused to flip R1 and flipped only R2 — that was the right call.** Its
AC-1 test is green but asserts *"every page is the medium its kind declares"*,
which is **not** R1's statement (*"puzzle pages, answer pages, the TOC and the
guide are written as PDF content-stream operators"*) while all five of those are
declared exceptions. Flipping R1 would have marked a rule mechanically checked by a
test that passes **while the rule is violated** — the defect repaired in `c12c33ce`
and again in ADR-0032/R3. R2's ref resolves and its flip is honest.

### F2-01 is delivered, with its control, and the table overstates one row

`_public_members` now reads `dir(cls)` (`tests/test_book_solved_answer_key.py:2751`)
with three control cells in the same commit. Independently killed: reverting to
`vars(cls)` reds `test_an_inherited_drawing_door_is_watched` and
`test_the_derivation_is_not_simply_returning_everything`. **M13 kills 2 of the 3
cells, not 3** — `test_the_derivation_is_unmoved_on_the_shipped_class` asserts the
`dir()` and `vars()` readings *agree* as a set on the shipped class, so it cannot
red under that mutant by construction. Not a defect in the test; its job is
different. The round's mutant table should read 2.

### Carried forward, not decided here

- **CARD-297's declared clip divergence is still unreached.** `page_medium(ANSWER)`
  is RASTER and `book_answer_vector` still has zero real call sites in `src/`, so
  nothing was silently inherited. The round's position for the card that *does*
  reach it: once the answer page is vector there is one answer-page writer, the
  book clips by `/Widths` — the measure the reader's viewer uses — so
  `_DECLARED_CLIP_DIVERGENCE` becomes a declaration about a page nobody prints and
  **should expire with the conversion and be deleted by the converting card**.
  Recorded for CARD-299; CARD-297's declaration is untouched and still true of the
  two writers as they stand.
- **The vector puzzle-page furniture needs a card**, cut after CARD-299. CARD-295
  names CARD-298 for it; CARD-298 cannot close it.
- **AC-1's "any export path" is not reachable over the proof sheet.**
  `book_proof.render_proof_pdf` writes through `Image.save(format="PDF",
  save_all=True)` — a second writer with no page kinds behind it. Declared and
  pinned by `test_the_proof_sheet_is_the_one_pdf_outside_the_medium_decision`,
  which asserts it by AST because **both writers stamp the same `% created by
  Pillow PDF driver` comment**.
- ADR-0006/R1 was **not** reported as verified by
  `TestDependencyBaseline_IsExactlyPillowAndNumpy` (zero definitions in this repo);
  the substance was checked instead — `pyproject.toml` unchanged, new imports are
  stdlib `enum` plus internal `book_vector` names.

## [Review cycle 1 — 7.0, DOES NOT CERTIFY, 2026-10-29]

`min_score: 8`, cycle 1 of 3. **Two findings block**, both small to fix, and both
verified independently by the orchestrator before a fix round was dispatched.
Everything else the reviewer called cycle-2-at-9 quality, and the two things the
dispatch most doubted — the four default-DENY claims and the four AST pins — both
survived its own measurement.

Impact gate (the reviewer's own, wider than the round's): import closure over the
two changed `src` modules, the changed helper and the two call doors whose
signature changed → **48 modules, 2365 passed, 5 skipped, 0 failed, 355 s**. Skips
all attributed: 1 × `test_book_pdf_memory.py:1297` (`setrlimit`, pre-existing) +
4 × `tests/conftest.py:207` (`DATABASE_URL` unset). Guardrail run
(`test_cli_exports_byte_identity`, `test_export_a4_golden`,
`test_guard_integrity`, `test_suite_profile`): **643 passed, 0 skipped**.
Mutation `deferred(cost)` per Step 8f's ladder, correctly — gating findings this
cycle.

### F-001, GATING — G-6 is not met: ADR-0042/R2's check is still `review-lens`

Confirmed at `adr/0042-…md:403`: `check: {kind: review-lens}`, with a comment
**directly beneath it** saying *"The test now EXISTS and is green"* and naming
three node ids. That is the defect shape this board has repaired twice — a rule
reading as checked while its `check:` is a placeholder.

The round justified it with *"CARD-298 leaves the flip to the merge, as this board
does"*. **That convention does not exist, and the two counter-precedents are the
only two comparable cards.** Measured by `git log -S`:
- CARD-227's ADR-0037/R2 flip is in **`7d86a869 feat(book): CARD-227 …`**
- CARD-294's ADR-0042/R5 flip is in **`0c63a328 feat(book-export): …`**

Both flipped in their **own feature commit**. Neither waited for a merge. Fix is
one line, and the named test exists and passed in the reviewer's gate.

Owed with it: the card's **Trace** line is unactionable — `trace.yml` carries **no
ADR-0042 rule rows at all** (only two prose mentions, at `:1813` and `:1853`;
`0042/R2` and `0042/R5` return nothing). Not the commit's fault, and the line was
inherited from the pre-narrowing card.

### F-002, important — the five expiries name the wrong card, AND the guard cannot notice

Both halves verified. CARD-299's `Touches` names six test modules plus
`requirements.yml` and the ADR — **not one file under `src/`** — so it converts no
page; and a board sweep for `book_pdf_generator` finds **no non-done card** owning
the interior conversion (CARD-231 is the divider only).

**The question the dispatch asked has a worse answer than expected: NO, AC-3's
mechanism will NOT red when CARD-299 lands.** `_declaration_findings`
(`tests/test_book_pdf.py:1607-1613`) fires the expiry finding only on
`declaration is not None and _RASTER not in media` — **only when a page's medium
actually changed**. CARD-299 changes no medium, so the pages stay raster, the
declarations stay matched, findings stay empty, and the five entries go **silently
stale on the day their own `expires_with` is satisfied**.

Independently confirmed: `expires_with` is read in exactly **two** places in the
whole tree — the finding's message text, and a `re.fullmatch(r"CARD-\d+")`
**format** check. **Nothing reads a card's status.** So the field is documentation
in a guard's clothes, and R2's own clause — *"once CARD-231 lands, the divider's
exception goes with it"* — is unguarded in the **landing** direction. The
registry docstring's claim that AC-3 "exists to force" the shrink is half-true: it
forces the **conversion** direction only, and that half should be stated rather
than left to read as both.

### F-004 — a tracked comment cites a path that resolves nowhere

`tests/test_book_export_interior_cover.py:3651` cites
`scratchpad/card298/ast_delta.py` for the +42 `ast.Call` cross-check. **Correction
to the reviewer, which said the file exists nowhere:** it does exist — in this
session's scratchpad, at an absolute path outside the repo — but the comment cites
it *relatively*, so it resolves nowhere from the repo and the file dies with the
session. The finding stands and its wording does not. Either move the census under
`meta/profiling/` or restate the one-line derivation inline; a tracked claim must
not rest on an ephemeral path.

### F-005 — M8's second reading is adequate as a control, overstated as independence

The "different door" is the **same door**: `interior_stream` itself calls
`self.section_plan(puzzles)` (`:7102`) and reads `decided.pages` (`:7112`), and the
test calls the same method on the same objects; the kind discrimination is the same
`isinstance(entry, DividerPagePlan)` predicate, transcribed twice. What **is**
independent is the **ordering authority** — `entry.page_number` against enumeration
order — a real second fact, and because the test owns its own transcription a
production-only kind-mapping mutant does die. But the docstring's claim that the
readings *"share nothing about which kind sits at which position"* is one step too
strong, and the shared predicate is unnamed. Also unnamed: the answer tail is not
production-equivalent (production guards the SOLUTIONS divider on `if payloads:`,
the test only on `generator.divider_pages`) — unexercised, but a restatement that
diverges.

### What survived, and is worth not re-reviewing in cycle 2

- **All four default-DENY claims are real, four for four.** `_UNCLASSIFIABLE` is a
  genuine third outcome, proved by building the two probe pages out of tree and
  running three classifiers: both two-branch spellings misclassify **both** probes
  (image-first → raster/vector; font-first → vector/raster), so the control kills
  either. The probes are built in-memory into a `BytesIO`; the diff adds **no
  file** under `tests/`.
- **The four AST pins were RE-DERIVED, not bumped — all four re-derived by the
  reviewer** by running each instrument on the **base** source as well as HEAD's,
  which a bump fails immediately. `inside` 17→18 (the extra call is
  `self.page_spec(page_number)` at `:5013`); `POSITION_SITE_COUNT` 24→25 with a
  row-set diff of exactly one added row and none removed; guide-counting 8→9 with
  the added site character-identical to `produce()`'s own range;
  `CALLEE_EXEMPTION_COST` 776/522/204/202 reproducing from the old source and the
  step deltas summing with **no remainder**, cross-checked at +42 `ast.Call`.
- **The widened `zigzag` assertion is a WIDENING, unambiguously** — still an
  equality, now over nine names instead of one, with `unclassified == ("zigzag",)`
  preserved verbatim. The only loss is tuple ordering, which is immaterial because
  `_public_members` is `sorted`. The reviewer also checked the one thing that would
  have made `dir()` unsafe: **no metaclass leakage** in CPython 3.14
  (`'mro' not in dir(ContentStream)`), so F2-01 is a true no-op at HEAD.

### C-1 — and this one is about the board's instrument, not the card

The reviewer measured **main 106, branch 107** and reached the right conclusion:
**107 is the honest count and main's 106 is the depressed one.** The extra warning
is **not this card's** — it is FR-046/AC-395's dead check ref, which `main`
silenced when it acquired CARD-291's cycle-1 review YAML in `93d04a50`, and which
this branch (cut earlier) still reports. **Third measured instance of CARD-308's
mechanism, and the first where a card branch reads WORSE than `main` because of
it.** Consequence for this card's merge gate: a naive branch-vs-main warning
comparison would read as *CARD-298 adds a warning*, which is false. Compare
against a `main` without that YAML, or compare the warning **sets** and attribute
each difference. Recorded on CARD-308.

### Three narrowing residues — the orchestrator's own misses, fixed above

Review cycle 1 caught three places where today's narrowing pass left stale text:
item 4 still said *"Record the new baselines"*, the worktree note still demanded
the **withdrawn** fixtures exception be enumerated file by file, and AC-5's
size/time readings were asked for under a heading about re-recording. All three
corrected in place with the reason marked. The size/time figures themselves **were**
taken by round 1 (3,468,586 B; 0.277 s on main vs 0.283 s on the branch, load
stated at both ends, whole interior sha256-identical with Pillow's two `/Info`
dates masked), so AC-5 is discharged — the card had simply stopped asking for them
coherently.
