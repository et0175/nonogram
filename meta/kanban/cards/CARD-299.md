# CARD-299: The interior's claims stop measuring ink — the registry's verifying tests move to the content stream, and the guard that keeps them there is derived

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/299-interior-claims-read-the-stream
**Worktree:** —
**Source:** ADR-0042/R6 (DEC-048), 2026-10-25; CARD-293's spike §4 and §6 item 6; the surface counted in `meta/profiling/adr-0042-migration-census.md`. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 66
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-276
**Touches:** tests/test_book_interior_type_floor.py, tests/property/test_book_export_interior.py, tests/property/test_book_layout.py, tests/property/test_book_two_up.py, tests/test_book_pdf.py, tests/test_book_pdf_memory.py, meta/architecture/requirements.yml, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

ADR-0042/R6: *a claim about an interior page's geometry, rule widths or tone is
asserted against the content stream of the written PDF, not against a rendered
bitmap.* Cards 295–297 converted the assertions about **their own** page kinds.
This card closes the rest, lands R6's own derived guard, and moves the
**registry's** verifying tests — the part no page card could do, because a
constraint belongs to no single page.

The spike measured why this is worth doing rather than merely necessary: the
replacement is **168 → 41 lines, 4.1× smaller**, **strictly more exact**, and it
**discriminates under mutation** (it passes at 0.48 pt and fails at 0.3 pt). And
for the first time the assertion is made against **the file that actually ships**
rather than an in-memory page upstream of the JPEG — today's pure-black
assertions *cannot* be made against the shipped file at all, because the DCT
round trip greys a rule's edges.

1. **CON-020's verifying test, re-expressed.** `TestInteriorType_EveryFaceHoldsTheFloor`
   works by spying on `ImageDraw.ImageDraw.text`
   (`tests/test_book_interior_type_floor.py:233`, `:261`). A vector interior makes
   no such call. Re-express it to read the written PDF's text-showing operators
   and their `Tf` sizes.
   **The part that must survive is the non-vacuity floor.** The floor assertion
   at `:353` is `below_floor(...) == []` — **vacuously true on an empty
   recording**. What makes the constraint real is the sibling at `:355`:
   `{"guide","divider","band","footer label","answer caption"} <= kinds`. Carry
   that floor across unchanged in spirit: the rewritten test must still fail if a
   kind of interior lettering stops being covered. **`divider` stays raster**, so
   the rewritten recording is deliberately mixed-source — it reads `Tf` sizes for
   the vector kinds and keeps today's reading for the divider.
   Then **flip CON-020's `check:`** in `requirements.yml` to the re-expressed
   test, in the style of its own 2026-10-06 precedent (*"was `kind: review-lens`
   … CARD-184 wrote it"*). Its **statement does not change** — a 10 pt
   reader-facing floor is a physical measure and is medium-independent.
2. **FR-043/EC-034's four interior readings**, in
   `tests/property/test_book_export_interior.py`, by line: `:731`'s
   `min() == 255` on the blank title page, `:734`'s `same_page` against the
   expected **guide**, `:736`'s `not same_page` against the cover, and `:848`'s
   ink scan. Its page-count assertions already read the written PDF and stay.
   **`:652`'s `same_page(cover_page, expected_cover)` compares the COVER and must
   NOT be converted** — see G-1.
3. **The two stroke-weight probes** at `tests/property/test_book_layout.py:364`
   and `tests/property/test_book_two_up.py:682`. Note the attribution, because the
   architect pass got it wrong first and the correction is recorded in
   `raw-requirements.md`: these sit in
   `test_PropertyTest_BookLayout_StrokesAtLeastQuarterMillimetreHeavyTwiceThin_pixels`
   and `..._two_up_pixels` — **stroke-weight tests belonging to ADR-0037/R2 and
   FR-033**, not to EC-019/EC-022/EC-032/EC-028, whose own property tests read
   millimetres and page sizes and never read drawn ink.
4. **R6's own derived guard.** Write
   `tests/test_book_pdf.py::test_no_interior_claim_is_made_by_measuring_ink` and
   **flip R6's check from `review-lens` to that node id**. Per ADR-0039/R2 it
   **enumerates the interior pixel idioms over `tests/**`** rather than holding a
   hand-written list, and **a test shape it cannot classify is a FAILURE, never a
   silent pass**. The regexes that derived the census are quoted in full in
   `meta/profiling/adr-0042-migration-census.md` precisely so this guard can be
   built from a repeatable derivation.
   **It must NOT absorb** (ADR-0039/R3 — an exemption is a claim and carries a
   control for what it must not absorb): the cover's readings, the dividers'
   readings, the independent oracles R6's statement exempts by name (`Sheet` and
   its kind), and COMP-007's CLI/web surface.
5. **`tests/test_book_pdf_memory.py` — a rewrite, not a retarget, and unpriced.**
   Its subject is `PAGE_BITMAP_BYTES = 2550 * 3300 * 3` (`:210`) and page-bitmap
   retention. The spike measured interior retention falling **1.00 → 0.000246**,
   so most of that file's premise does not survive the phase. 34 pixel sites.
   **If this turns out to be its own card, say so and raise it** rather than
   absorbing it here — `scope_gate` is `on` and escalation to the decompose
   station is the designed route.

## Acceptance criteria

- **AC-1** (CON-020 is verified again, and the floor cannot go vacuous): *Given*
  the re-expressed test, *then* every reader-facing interior face holds 10 pt read
  from the stream's `Tf` sizes, **and** the test fails if any kind of interior
  lettering stops being covered. (test: the re-expressed
  `TestInteriorType_EveryFaceHoldsTheFloor` plus its non-vacuity sibling, both
  node ids preserved. **Two mutants** per ADR-0039/R1: set one face to 9 pt — it
  reds; and stop drawing one covered **kind** — the sibling reds. The second
  mutant is the one that matters, because it is the control that would have been
  lost.)
- **AC-2** (the registry's check is honest): *Given* `requirements.yml`, *then*
  CON-020's `check:` names the re-expressed test, its **statement is
  byte-identical** to today's, and no other requirement's statement changed.
  (**gate**: a diff showing the `check:` moved and the statement unchanged.)
- **AC-3** (no interior claim measures ink, derived and default-deny): *Given*
  `tests/**`, *then* the guard enumerates interior pixel idioms and the set is
  empty, with every exemption declared and carrying its own control. (test:
  `tests/test_book_pdf.py::test_no_interior_claim_is_made_by_measuring_ink` — the
  node id ADR-0042/R6's comment names, so item 4's flip lands on a real test.
  **Two mutants**: reintroduce an ink scan on an interior page — it reds; and
  hand it a test shape it cannot classify — it **fails** rather than passing.)
- **AC-4** (the exemptions did not swallow the subject): *Given* the guard's
  exemption list, *then* a control shows each exemption does **not** absorb what
  it must not — the cover's readings stay asserted, the dividers' stay asserted,
  `Sheet`'s oracle role stays intact and compared against, **and the
  device-fact exemption (G-3b) does not admit a test that reads a STATED width
  off a render**. (test: `TestInkGuard_NoExemptionAbsorbsAnInteriorClaim` —
  ADR-0039/R3.) The device-fact arm is the one with a live mutant available:
  take `TestBookGridRules_WeightsSurviveTheFloor`, change its conclusion from
  "these two render differently" to "this line measures 0.3 pt", and the guard
  must stop exempting it. An exemption keyed on the test's *name* or *file*
  instead of its *conclusion* will pass that mutant, which is the whole reason
  this AC exists.
- **AC-5** (the replacement is smaller and no weaker): *Given* the converted
  assertions, *then* the line count before and after is recorded, and each
  converted claim is shown to still discriminate — a mutant that the ink version
  caught is still caught. (**gate**: the figures recorded; the spike's own
  168 → 41 is the precedent, not the target.)
- **AC-6** (no test deleted, renamed, skipped or merged — `parametrize` ids
  included): *Given* the touched files, *then* the collected node-id set loses
  nothing. (**gate**: set difference with `-o addopts=''`; removals 0, additions
  named. **A reworded param id is a deleted node id.**)

## Guardrails

- **G-1: the cover's pixel assertions stay.** The cover is raster by
  ADR-0042/R2 — it is a photograph, and measuring its pixels is the only way to
  assert anything about it. `tests/test_book_cover.py` and `:652`'s
  `same_page(cover_page, expected_cover)` are **not** in scope. A card that
  converts every `same_page` in that file uniformly has broken R2.
- **G-2: the dividers' pixel assertions stay.** Raster by owner decision
  2026-10-25; CARD-231 redesigns them and is born vector. `divider` is also one
  of the kinds AC-1's non-vacuity floor requires.
- **G-3: do not convert the independent oracles.** R6's statement exempts them by
  name: *"Independent second-implementation oracles (Sheet and its kind) are
  unaffected and still compared against — only the reading of the artefact
  changes."* An oracle that recomputes the page independently is the second
  implementation this project's test style asks for, not ink archaeology.
- **G-3b: do not convert the DEVICE-fact tests, and expect your guard to want
  to.** R6 gained a **second declared exemption** on 2026-10-25 when the owner's
  grid weights landed: a claim about what the device does with a declared width
  or tone — that two distinct declared widths resolve to distinguishable
  rendered widths, that none drops out, that grey 89 survives — is asserted on a
  **render**, because the content stream is precisely what it does not test.
  Reading 0.3 pt back out of the operator that set it says nothing about whether
  0.3 pt is *visible*, and that visibility is what the whole 0.3 / 0.8 / 1.3
  decision rests on.
  **Concretely, your default-DENY guard will flag these and must not:**
  `TestBookGridRules_WeightsSurviveTheFloor` (FR-033/AC-374) and
  `TestBookGridRules_PointsNotPixels` — both CARD-227's, both landing in wave 62,
  before you. **The discriminator to encode** is what the assertion *concludes*:
  "these two render differently" and "this tone survives" are device facts;
  "this line is 0.3 pt" is a stated number and belongs to the stream. Per
  ADR-0039/R3 this exemption carries a control for what it must **not** absorb —
  a test that reads a **stated** width off a render is still a violation, and
  AC-4 must prove the exemption cannot swallow one.
- **G-4: do not touch COMP-007's CLI/web surface.** `tests/test_export_image.py`
  (4 pixel sites, **1** interior reference) and
  `tests/test_layout_page_spec.py` (10 sites, **3**) are that surface — the low
  interior-reference count is the tell. CON-019 holds it byte-identical and
  ADR-0042 does not reach it.
- **G-5: do not edit `src/**`.** This is a test-and-registry card. A production
  change needed here is a finding to raise — the writer is CARD-295/296/297/298's.
- **G-6: do not change a requirement's statement.** Only CON-020's `check:`
  moves. The delta that authorized this is explicit that no statement changes and
  no ID is created.
- **G-7: corpus minimums are never lowered;** `tests/fixtures/**` is never
  regenerated (CARD-298 holds the one scoped baseline exception).
- **G-8: probes stay OUT of `tests/`** — `RENDER_HEAVY_SNAPSHOT`
  (`meta/profiling/rank_durations.py:45`, asserted equal to a 33-entry snapshot at
  `tests/test_suite_profile.py:482`) reds the suite on a new `tests/` file naming
  one of its eight idioms. Several files this card touches are **in** that
  snapshot.
- **G-9: ADR-0042/R6's lens must not survive this card.** Item 4's flip is part
  of the card.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — an interior claim is asserted against the content stream, not a bitmap; the oracles are exempt (check: review-lens → this card's AC-3)
- ADR-0042/R1 — interior pages are operators; no image XObject (check: tests/test_book_pdf.py::test_no_interior_page_carries_an_image_xobject)
- ADR-0042/R2 — a raster page is declared with a reason (check: tests/test_book_pdf.py::test_every_raster_page_is_declared_with_its_reason)
- ADR-0039/R1 — a claim needs a control that CAN fail; two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE, never a silent pass (check: review-lens)
- ADR-0039/R3 — an exemption is a claim and carries a control for what it must NOT absorb (check: review-lens)
- CON-020 — no interior text for the reader below 10 pt at the page's own resolution, clue digits excepted (check: TestInteriorType_EveryFaceHoldsTheFloor → re-expressed here)
- CON-019 — book geometry never changes the CLI's or web UI's exports (check: PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry)
- ADR-0036/R2 — book page geometry is COMP-007's `compute_layout` with a PageSpec (check: review-lens)

## Architecture context

- **FR:** FR-043 (EC-034), FR-033 (the stroke-weight probes' real owner), FR-030, FR-032, FR-040
- **NFR:** NFR-008
- **ADR:** **ADR-0042/R6** (this card is its delivery), ADR-0039/R1-R2-R3, ADR-0036/R2
- **Components:** none in `src/` — the test tree and the registry
- **Trace:** meta/architecture/trace.yml — CON-020's check ref moves here, so its trace row is re-stamped in this card. <!-- VERIFIED 2026-10-29 at the wave-66 slot decision: this line is ACTIONABLE, unlike the one CARD-298 inherited, and the obligation is stronger than it reads. CON-020 is a real row at `status: covered` with SEVEN tests listed, and `validators/trace.py::_check_covered_tests` gates all three of its checks on `status == "covered"` -- so this row's `tests:` list is one of the few the validator actually reads. Gate 3, a listed test with no definition, is **Severity.ERROR**, not a warning. FOUR of the seven live in `tests/test_book_interior_type_floor.py`, which is this card's FIRST declared Touches file: TestInteriorType_EveryFaceHoldsTheFloor (the one item 1 re-expresses), TestInteriorType_FloorHoldsWithoutArial, TestInteriorType_OnlyPuzzleClueDigitsAreExempt and TestDividerPage_PointSizeIsIndependentOfDpi. All seven resolve to real definitions today. **So renaming the re-expressed test without re-stamping this row turns the validator RED at error level, not warning level** -- the strongest gate on this board, and the one place a dead ref breaks the build. Re-stamp it in the same commit as the rename, and verify the new name by its `def`/`class` line rather than by `git grep` exiting 0, because gate 3 uses the same text search and so carries the same false-alive hole. -->

## Worktree notes

- **Why this card depends on CARD-276.**
  `tests/test_book_export_interior_cover.py` holds **34 pixel sites** and is
  simultaneously **CARD-276's** (in flight, F-2 and F-3 still owed, round counter
  6 of 6), **CARD-287's** (344.29 s, 24.4 % of the suite) and **CARD-292's**.
  This card must not open it while CARD-276 is live. If CARD-276 is abandoned
  rather than merged, re-point this dependency instead of inheriting a stale one.
- **Read CARD-287 and CARD-292 together with this card before dispatching it.**
  The census found the four heaviest files hold **156 of the 315 sites (49.5 %)**,
  and they are the same neighbourhood those two cards exist to cheapen. The spike
  measured the stream assertion at **4.1× smaller** than the ink one, so **the
  conversion and the cheapening are one piece of work done once** — doing them
  separately pays the serialization cost on a hotspot file twice.
- **The attribution error recorded in item 3 is the method lesson.** The architect
  pass joined *file* → requirement instead of *test* → requirement, and so
  attributed two `getpixel` probes to four ECs that never read ink. Co-location is
  not ownership. When this card decides which claim a converted assertion
  belongs to, read the enclosing test, not the enclosing file.

## [Dependency order RESOLVED — 2026-10-29, orchestrator, after CARD-298 round 1]

CARD-298's round hit the scope gate and the owner narrowed CARD-298 to the
**mechanism** card. Three facts about this card fall out, and the third is a
finding this card's round must resolve rather than inherit.

**1. `Depends on: CARD-298` is now correct and the graph is acyclic.** It was
briefly a cycle: CARD-298 was cut to wire the vector writers into the interior,
and wiring even one page breaks every reader, because
`tests/helpers/pdf_pages.py:34-40` loops **every** page and asserts
`len(xobjects) == 1, "a book page is exactly one image"` plus `Filter ==
DCTDecode`. 14 test modules and 3 helpers (`book_corpus`, `page_ink`,
`pdf_vector`) read an interior through it. CARD-298 now converts nothing, so this
card is unblocked by it rather than blocked on it.

**2. This card's readers must be MEDIUM-AGNOSTIC, driven off CARD-298's
`page_medium(kind)`, not off an assumption that the interior is vector.** Item 1
already commits to this for one kind — *"`divider` stays raster, so the rewritten
recording is deliberately mixed-source"* — and the measured state is that **all
seven kinds are raster at CARD-298's HEAD**, including the five this card's prose
treats as vector. So the generalisation is: read each page by the medium
`page_medium` declares for its kind, and let the declaration shrink underneath you
without the test changing. Written that way this card lands **before** any page
converts, which is the only order that works.

**3. FINDING — five raster declarations name this card as their expiry, and this
card cannot discharge them.** CARD-298 shipped
`_RASTER_DECLARATIONS` with `expires_with=('CARD-299',)` on **TITLE, GUIDE, TOC,
ANSWER and PUZZLE**. But this card is **test-side only**: items 1–5 convert
assertions and readers, and nothing here writes a page. The pages themselves are
still written by `book_pdf_generator`, and **no card on the board converts them**
— CARD-295/296/297 built `book_guide_vector`, `book_toc_vector`,
`book_answer_vector` and `book_puzzle_vector`, all of which still have **zero real
call sites in `src/`**, and CARD-298 was the wiring card until it was narrowed.
So either those five `expires_with` values are wrong, or this card's scope is. Do
not quietly adopt either reading: **re-point them at the cards that actually
convert each kind, and raise the fact that those cards are not cut.** AC-3's
expiry check is exactly the mechanism that will red if this is left wrong, which
is the one piece of good news.

**What this card does NOT inherit, stated so a round does not take it on:**

- **ADR-0042/R1's flip is not this card's either.** R1 says puzzle pages, answer
  pages, the TOC and the guide **are** operators. That is true only once all four
  convert, which happens in cards not yet cut. CARD-298 correctly refused the flip
  (its AC-1 is the weaker medium-agreement statement); refusing it here is equally
  correct. R1 stays a `review-lens` until the last conversion lands. R6's flip,
  item 4, **is** this card's.
- **The 21 book baselines do not move here.** They move when a page's **bytes**
  change, i.e. in the conversion cards. CARD-298 measured 0 of 21 moving and
  `tests/fixtures/**` untouched; the same should hold here, and a baseline that
  moves on a test-side card is a **finding**, not a re-record. The scoped
  never-regenerate exception stays withdrawn.
- **CARD-297's declared clip divergence** (`_DECLARED_CLIP_DIVERGENCE`) is still
  unreached — `page_medium(ANSWER)` is RASTER and `book_answer_vector` has no real
  call sites. Round 1's position, recorded for whoever converts the answer page:
  once that page is vector there is **one** answer-page writer, and the book clips
  by `/Widths`, the measure the reader's own viewer uses — so the declaration
  becomes a statement about a page nobody prints and **should be deleted by the
  converting card**, not inherited. Not this card's to act on.

**Also owed to the phase, now cut as its own card:** the vector puzzle page draws
no folio, frame rules, grid-size label or QR block — see **CARD-306**. A vector
puzzle page cannot ship without it, and CARD-295 wrongly named CARD-298 for it.
