# CARD-299: The interior's claims stop measuring ink — the registry's verifying tests move to the content stream, and the guard that keeps them there is derived

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/299-interior-claims-read-the-stream
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-299
**Source:** ADR-0042/R6 (DEC-048), 2026-10-25; CARD-293's spike §4 and §6 item 6; the surface counted in `meta/profiling/adr-0042-migration-census.md`. Cut by the architect/decompose pass that followed the ADR's acceptance.
**Idea:** —
**Wave:** 66
**Created wave:** 60
**Deferred waves:** 0
**Depends on:** CARD-298, CARD-276
**Touches:** tests/test_book_interior_type_floor.py, tests/property/test_book_export_interior.py, tests/test_book_pdf.py, tests/helpers/pdf_vector.py, meta/architecture/requirements.yml, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md <!-- NARROWED 2026-10-29 at the merge gate, against the gated diff rather than the plan. REMOVED, declared but never touched: tests/property/test_book_layout.py, tests/property/test_book_two_up.py, tests/test_book_pdf_memory.py (that last one is CARD-313's subject and this card deliberately left it alone). ADDED, touched but never declared: tests/helpers/pdf_vector.py (+45/-0). The declared set mattered to the conflict graph at dispatch, so an over-broad Touches serializes cards against files nobody edits -- which is what happened to this card once already. -->
**Review score:** 8.5 (cycle 2 of 3, CERTIFIED, no gating findings)
**Started:** 2026-10-29
**Closed:** 2026-10-29
**Actual:** 1d — cut and merged 2026-10-29; 2 review cycles, 1 fix round, 2 merge gates
**Merge commit:** 7e434c72
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
  (**gate**: a diff showing the statement unchanged and the `check:` ref
  **correctly NOT moved**. <!-- GATE CLAUSE CORRECTED 2026-10-29 at the merge
  gate. The clause said "a diff showing the `check:` moved". It did not move, and
  it must not: AC-1 requires both node ids preserved, so the re-expression had to
  happen INSIDE the existing class rather than beside it under a new name. A ref
  that did not move is this AC being MET, not an omission -- and it is what kept
  the ERROR-level trace gate-3 hazard from ever being armed. Measured at the gate:
  0 `statement:` lines and 0 `then:` lines changed in requirements.yml across
  cut..HEAD. -->)
- **AC-3** — **MOVED TO CARD-312 2026-10-29**, not met here and not owed here.
  <!-- NARROWED by owner decision. The AC asked for a guard enumerating interior
  pixel idioms "and the set is empty". Measured: the set is 321 sites across 34
  files, two of R6's own six named sites are not interior PDF readings, and an idiom
  COUNT cannot express "empty" without reddening correct conversions. The AC is not
  weakened, it is re-homed with the enumeration correction it needs. Original text
  kept below for CARD-312 to inherit. -->
  *Given* `tests/**`, *then* the guard enumerates interior pixel idioms and the set
  is empty, with every exemption declared and carrying its own control. (test:
  `tests/test_book_pdf.py::test_no_interior_claim_is_made_by_measuring_ink` — the
  node id ADR-0042/R6's comment names, so **CARD-312's** flip lands on a real test.
  **Two mutants**: reintroduce an ink scan on an interior page — it reds; and
  hand it a test shape it cannot classify — it **fails** rather than passing.)
- **AC-4** — **MOVED TO CARD-312 2026-10-29 with AC-3**, not met here and not owed
  here. <!-- Review cycle 1's F-005: AC-4 is a control over **the ink guard's**
  exemption list, and the ink guard is AC-3's subject -- which was already re-homed
  to CARD-312. Its named test `TestInkGuard_NoExemptionAbsorbsAnInteriorClaim` has
  **no definition in the tree**, so the AC was unachievable here the moment AC-3
  left. An AC whose subject has moved is not a gap, it is a mis-filing. Original
  text kept below for CARD-312 to inherit alongside AC-3. -->
  *Given* the guard's
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
  168 → 41 is the precedent, not the target.) <!-- CORRECTED 2026-10-29: round 1
  measured that the 4.1x CANNOT reproduce here and the replacement is necessarily
  LARGER (+272 and +361 lines -- **STALE, see the gate note below**). The spike's figure assumes the ink arm is DELETED,
  which requires the page to be vector; with all seven kinds raster both arms must
  coexist AND the stream arm needs its own non-dormancy controls. The reduction
  becomes available to CARD-309, when an arm can actually be removed. "Smaller" is
  therefore struck as a criterion; "no weaker" stands and was demonstrated by
  mutants. -->
<!-- AC-5 FIGURES RE-MEASURED AT THE MERGE GATE 2026-10-29, and they had gone
stale. The +272/+361 above were measured by review cycle 1, BEFORE fix round 1
added its derived refusal set and its non-vacuity controls. Measured on the gated
tree with `git diff --numstat 4ce84c30..HEAD -- tests/`:

  tests/helpers/pdf_vector.py                  +45  -0
  tests/property/test_book_export_interior.py +362  -11
  tests/test_book_interior_type_floor.py      +689  -2
  tests/test_book_pdf.py                       +18  -14

So the replacement is larger than the card says, not smaller -- which does not
change AC-5's disposition ("smaller" was already struck as a criterion and "no
weaker" is what stands, demonstrated by mutants), but the recorded figures no
longer describe the tree being merged. The deletion counts (11 and 2) are the
only two that survived unchanged, which is why the staleness was invisible to a
spot check. THE LESSON IS THE CARD'S OWN: a figure recorded in one round
describes that round's tree, and a later round in the same card can age it out
without touching the sentence that carries it. -->

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
- **G-9: ADR-0042/R6's lens MUST survive this card.** <!-- NARROWED 2026-10-29 by
  owner decision, after round 1 refused the flip with four measurements the
  orchestrator verified. This guardrail said the opposite -- "R6's lens must not
  survive" -- and it is inverted rather than dropped, because the reason is
  load-bearing and a later round must not "restore" the flip. R6 names SIX sites and
  TWO of them read a PNG and never produce a PDF (`test_book_layout.py:364`,
  `test_book_two_up.py:682` -- both call `getpixel`, neither mentions
  `BookPDFGenerator` at all), so a guard derived from that enumeration is derived
  from a wrong set. The census the guard would otherwise read gives 34 files / 321
  sites at HEAD against R6's 6, and it is four days stale IN THE WRONG DIRECTION
  (32/315 at c12c33ce). And an idiom count cannot measure "the set is empty": this
  round's own CORRECT conversion raised one module's occurrences 8 -> 13, so a guard
  ratcheting that count reds on the work it exists to encourage. Flipping a mandatory
  check onto such a guard is the `c12c33ce` defect -- a rule reading as mechanically
  checked by a test that cannot see its breach -- and is the same refusal CARD-298
  made on R1. **R6's flip moves to CARD-312**, with the enumeration correction. -->

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R6 — an interior claim is asserted against the content stream, not a bitmap; the oracles are exempt (check: **review-lens, and it SURVIVES this card** — the flip moves to **CARD-312** with the six-site enumeration corrected; see G-9)
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
DCTDecode`. <!-- CENSUS CORRECTED 2026-10-29 at the merge gate; the retired text
read "14 test modules and 3 helpers (`book_corpus`, `page_ink`, `pdf_vector`)" and
was wrong in both halves. Measured: **12 modules import the one-image reader**, and
of the three helpers only `tests/helpers/book_corpus.py:889` imports from
`pdf_pages` at all -- and it takes only `pdf_page_count`, not the reader.
`page_ink.py` and `pdf_vector.py` merely mention it in comments. The orchestrator's
original figure came from counting MENTIONS of the string as if they were imports;
`grep -rl pdf_pages tests/` returns **39** files, which is a third figure again and
measures a third thing. The number that carries the argument is the 12. -->
**12 test modules import that one-image reader**, and one helper
(`tests/helpers/book_corpus.py`) takes only `pdf_page_count` from the same module. CARD-298 now converts nothing, so this
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

**3. ~~FINDING — five raster declarations name this card as their expiry~~
RESOLVED, and this paragraph is stale. 2026-10-29: CARD-298's fix round retargeted
all five to `expires_with=("CARD-299", "CARD-309")` before it merged (verified at
`book_pdf_generator.py` lines 625/640/655/670/685, each `authority` naming CARD-309
explicitly), and CARD-309 was cut for the conversion. So there is nothing to
re-point and no card is missing. The orchestrator wrote this finding before that
fix landed and did not revise it when it did — CARD-299's own round caught the
staleness. Kept rather than deleted because the paragraph below is still the right
reading of this card's scope.** The original text: CARD-298 shipped
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

## [Implementation round 1 — 2026-10-29. Items 1–2 delivered; items 3, 4 and 5 refused with measurements. G-9 DELIBERATELY UNSATISFIED.]

Branch `card/299-interior-claims-read-the-stream` @ **`eed831ea`**, one commit,
6 files **+777/−27**, tree clean. `src/` **0 files**, `tests/fixtures/` **0 files**,
`pyproject.toml` untouched. Validator of record: main **0 errors / 102 warnings**,
branch **0 / 102**, warning sets **byte-identical** by `comm -3`.

### The measurement that shaped the card, verified by the orchestrator

**All seven `PageKind` members are still RASTER**, so `pdf_vector.type_sizes`
returns `[]` on every page of the baseline interior and the first stream is
`q … /image Do Q`. **A reading rewritten to ask the content stream *today* is
vacuously green over an empty list** — strictly worse than the ink assertion it
replaces, and the exact defect ADR-0039 exists for.

So every conversion is **medium-gated**: the bitmap arm is today's assertion
unchanged, the stream arm is R6's exact one, and an unclassifiable page is a
**FAILURE** per ADR-0039/R2. That is what finding 1 asked for, and the round
proved the stream arm is **not dormant** by lifting one `_RASTER_DECLARATIONS`
entry so production's own writer emits a vector page (`media[0] = vector`,
`type_sizes` called exactly once, and `pages=None` proving the bitmap arm was
never taken).

### Items 1 and 2 landed; the node ids did NOT move — and the brief was wrong to expect otherwise

CON-020's verifying test was **re-expressed inside the class**, so
`TestInteriorType_EveryFaceHoldsTheFloor::…` and
`::test_the_recording_covers_every_kind_of_interior_lettering` are **byte-identical
before and after**. 23 passed → **28** (the 5 new controls). Item 2 converted the
three real FR-043/EC-034 readings (`:731`, `:734`, `:736`); **`:652`'s cover
`same_page` untouched (G-1)**.

**The orchestrator's brief said "a rename is expected here" and that contradicted
this card's own AC-1 ("both node ids preserved") and AC-6.** The round followed the
card, which was right — and the consequence is the good one: **no ref died, CON-020's
`trace.yml` row needed no re-stamp, and the ERROR-level `_check_covered_tests`
gate-3 hazard was never armed.** The warning about that gate was sound in principle
and predicated on a rename the card forbids.

### The non-vacuity floor is carried across AND shown failing

Deleting the footer label's `draw.text` (line-count-preserving, blob asserted both
sides, `__pycache__` swept) reds **the sibling coverage assertion** while the floor
assertion stays green — precisely the control that would otherwise have been lost.
Deleting the DPI conversion (CARD-149's defect verbatim) reds the floor assertion in
two classes.

**One survivor, declared:** deleting the *band's* `draw.text` does not red the
coverage assertion, because `BAND_SETTERS` has two members so one deletion leaves
"band" covered. **Pre-existing, not introduced here.**

### THE SHARPEST FINDING — CON-020 becomes unverifiable on a vector puzzle page

Measured on a real vector puzzle page: **205 `Tf` operators, distinct sizes
`[8.64, 14.16]` pt, and 8.64 is below the 10 pt floor.** Those 8.64 pt digits are
**exactly the ones CON-020 exempts** — and the exemption is keyed on the **drawing
function** (`_draw_clues` / `_write_clues`), while **a content stream records no
provenance**. So a stream-read floor cannot tell an exempt clue digit from body
type.

`stream_faces` therefore **refuses every vector page that draws clue digits**
(default-DENY) rather than reporting 205 false violations, or exempting 8.64 pt *by
its value* — which would exempt a body face that happened to measure 8.64 pt.
<!-- WIDENED 2026-10-29: this paragraph was written one-kind, naming only the puzzle
page and only the raster drawers `_draw_clues`/`_write_clues`. Fix round 1 derived
the refusal set from `src/` instead of asserting it, and the set is TWO kinds,
`['answer', 'puzzle']` -- `book_answer_vector.py:403` calls
`book_vector_draw.draw_clue_digits` just as the puzzle writer does. The one-kind
wording was a claim about a set that is now measured, so it is corrected rather than
left as prose contradicting the test beside it. The derivation reads `src/` with
`ast` over Call nodes specifically because `book_guide_vector.py` DISCUSSES the clue
drawer in its comments without calling it, so a text search would have exempted the
guide page -- whose worked example is exactly the lettering CON-020 does not
exempt. --> **The converting
card owes the stream a way to mark its clue digits, and that is a `src/` change this
test-side card cannot make.** Without it, CON-020 is unverifiable the day the puzzle
page converts.

### Items 3, 4 and 5 refused, each with a measurement

**Item 3 is not deliverable as specified, and R6's own enumeration is wrong.** Both
named "stroke-weight probes" read a **PNG**, never a written PDF — verified
independently: `tests/property/test_book_layout.py:364` and
`tests/property/test_book_two_up.py:682` both call `getpixel` on a PIL image, and
**neither module mentions `BookPDFGenerator` even once**. No PDF ⇒ no content stream.
Both are COMP-007's drawing surface, which this card's G-4 and CON-019 put outside
ADR-0042's reach.

**Item 4 refused: R6's check stays a `review-lens`, so G-9 is unsatisfied.** Four
measurements: two of the six sites R6 enumerates are not interior PDF readings (as
above); the two cited authorities disagree by ~50× (R6 names **6**; the census's own
regexes read **34 files / 321 sites** at HEAD); the census is **4 days stale and
moved the wrong way** (32 files / 315 sites at `c12c33ce` → 34 / 321); and **an idiom
count cannot measure "the set is empty"** — the round's own *correct* conversion
raised one module's occurrences 8 → 13, so a guard ratcheting that count reds on the
work it exists to encourage. **Flipping a mandatory check onto a guard derived from a
wrong enumeration is worse than leaving the lens** — the same judgement CARD-298 made
on R1 and was right about.

**Item 5 is its own card, decided in the first hour as instructed.** R6's live
enumeration **does not name `tests/test_book_pdf_memory.py` at all**, and that file's
premise (`PAGE_BITMAP_BYTES`, page-bitmap retention) does not change until a page
converts — which happens in CARD-309, not here. The spike's 1.00 → 0.000246 measures
a vector interior that does not exist. File untouched: **54 passed, 1 skipped**.

### Node ids and skips

Over the six Touches modules: **172 → 180, +8 / −0**, every added id named, no
`parametrize` id reworded. Impact runs: 6 Touches modules **179 passed / 1 skipped**;
the five meta-guards **425 passed**; six vector/layout modules **545 passed**.
`_conditional_silences(<source>) == []` for all four changed files.

**Exactly one skip across every run** — `tests/test_book_pdf_memory.py:1297`,
`setrlimit` refused by the kernel. **The brief said `:1296`; it is `:1297`** — the
orchestrator's error.

### Four more corrections to the card and the brief, all measured

1. **AC-5's "168 → 41 lines, 4.1× smaller" did not reproduce and could not.** The
   replacement is **larger** (+272 and +361 lines), because the 4.1× assumes the ink
   arm is **deleted**, which needs the page to be vector. With all seven kinds raster
   both arms must coexist *and* the stream arm needs its own non-dormancy controls.
   **The 4.1× becomes available to CARD-309**, when an arm can actually be removed.
2. **The non-vacuity floor is conditional, not unconditional.** The brief quoted
   `{"guide","divider","band","footer label","answer caption"} <= kinds`; the code
   requires `{"guide","divider","band"}` and adds the other two **only when
   `book != "min-trim"`**. Carried across unchanged.
3. **CARD-295's work partly pre-empts item 1** —
   `tests/test_book_guide_page_vector.py::TestGuidePage_EveryFaceHoldsTheFloorInTheStream`
   already reads `Tf` sizes and asserts the floor with its own non-vacuity pairing.
   Item 1's prose reads as if no stream-side floor check existed.
4. **The ADR's History says "the baselines move when R6 lands"; they cannot** — R6
   is test-side. They move when a **page** converts. Measured: 0 of 21 moved here.

## [Review cycle 1 — 7.5, DOES NOT CERTIFY, 2026-10-29]

`min_score: 8`, cycle 1 of 3. **Two gating findings, both cheap, and the first is
this card's own standard turned on its own work.** Items 1–2 are really delivered and
the refusals are honestly recorded. Report synced.

Runs: the two changed modules **34 passed**; the floor module alone **28** (cut: 23 —
the round's 23 → 28 reproduced); the eight other `pdf_vector` consumers **640
passed**; the six meta-guards **835 passed**. Exactly **one** skip, by name:
`tests/test_book_pdf_memory.py:1297`.

### F-001, GATING — the clue-digit refusal is keyed on ONE page kind and the exempt faces live on TWO

Verified by the orchestrator. `tests/test_book_interior_type_floor.py:429` is
`assert kind.value != "puzzle"`. But joining every exempt face in the spy recording
to its page's `PageKind`:

```
exempt faces by (page kind, pt):   ('answer',10.56):64   ('answer',8.64):258
                                   ('puzzle',13.20):118  ('puzzle',8.64):204
sub-floor AND exempt:              ('answer',8.64):258   ('puzzle',8.64):204
```

**258 of the 462 exempt sub-floor faces are on ANSWER pages — more than the puzzle
page's 204** — drawn 322× per book through `book_pdf_generator._write_clues`, an
`EXEMPT_CALLER`. And the vector answer writer draws them too:
**`src/nonogram/admin/book_answer_vector.py:403` calls `draw_clue_digits(...)`**.

So the day `PageKind.ANSWER`'s declaration lifts, `stream_faces` does **not** refuse
— it reads the page and reports **258 false CON-020 violations**, the exact failure
the puzzle refusal exists to prevent. `StreamFace` has no exemption concept at all,
and its docstring points at a `:meth:`exempt`` that does not exist (F-007) — given
F-001, that absent member is the load-bearing one.

**The understatement propagated.** The finding was written as "a vector puzzle page"
in this card, in `requirements.yml` and in the ADR — and **CARD-314 was cut from it
with a one-kind brief.** CARD-314's scope is corrected on its own card with the
figures above; the fix round corrects the other three places.

### F-002, GATING — the converted module's own call site cannot survive the medium change

`tests/property/test_book_export_interior.py:807` does
`interior = pdf_pages(interior_bytes)`, and `tests/helpers/pdf_pages.py:34-40` loops
**every** page asserting one `DCTDecode` image. So with one real vector page the
property test dies at `:807` with `KeyError: b'XObject'` **before any gated helper
runs**, and the stream arms are reachable only by calling the helpers directly with
`pages=None`.

**That falsifies the diff's own central claim**, verbatim at `:425-427`:

> *"The declarations shrink underneath these helpers without the call sites changing,
> which is the only order that works…"*

Loud rather than silent, so not a correctness hole today — but **the prose is wrong
and CARD-309 will read it as a promise.** Scale, re-derived by the orchestrator:
**18 files read an interior through `pdf_pages`** (14 test modules + 4 helpers) and
**this card converted 2 of them**, one of which still routes through it.

### What survived, and is worth not re-reviewing

- **The `pages=None` discriminator is genuine** — the reviewer forced
  `page_media → [RASTER]` and called `_title_page_is_blank(data, None, …)`: it raises
  `TypeError`, because the bitmap arm's first act is `pages[0].convert("L")`.
- **The two arms cannot disagree destructively**: `below_floor_in_its_medium` is a
  **union**, so neither arm going quiet removes a face.
- **`_UNCLASSIFIABLE` is a real third branch, driven on real PDFs** at
  `tests/test_book_pdf.py:2318-2319`.
- **The refusal is a guard, not a gap** — it is an `assert` inside `stream_faces`, so
  the page does not drop out; CON-020's two verifying cells *error* with a message
  naming what the stream owes. And refusing by **kind** is the right default:
  exempting 8.64 pt by value would exempt a body face.
- **Item 4's refusal is justified**, with **three of its four measurements
  re-derived** by the reviewer using the census's own regexes: `c12c33ce` → **32
  files / 315 sites, exactly the census's recorded figures**; main and the cut →
  **34 / 321**; and `test_book_export_interior.py` **8 → 13**, accounting for the
  whole move. Item 3's premise independently re-derived: `grep -c BookPDFGenerator`
  is **0** in both probe modules.
- **Node ids byte-identical**: 172 → 180, **0 removals**, +8 all named, both
  parametrised ids character-for-character in both sets. `trace.yml` not in the diff,
  CON-020's seven listed tests all still resolve — **the ERROR-level gate-3 hazard
  was never armed, and the round was right to follow the card against the brief.**
- **The band survivor is pre-existing and narrower than declared** — the identical
  mutant at the cut gives the same verdict, and in *both* trees the failing cell is
  `TestInteriorType_DifficultyDotsAreNotText::test_the_spy_does_see_the_word_beside_them`.
  So the module is **not** blind to the band. The reviewer's judgement, which the
  orchestrator accepts: **acceptable, not a finding.**
- **G-6 is stronger than stated**: stripping `^\s*#` from both registry files gives a
  **zero-line diff**, and `yaml.safe_load(requirements.yml)` is `==` across the cut
  and HEAD — the registry is **semantically identical**.

### Non-gating findings

- **F-003 (medium)** — `LETTERING_KINDS` is a hand-written 5-string frozenset with no
  test tying it to `PageKind`, and `planned = LETTERING_KINDS & set(...)` makes an
  **unlisted** lettering kind a silent pass. Complete today by accident (7 enum
  members; COVER is not interior, TITLE is blank), not by derivation — so **not
  complete in ADR-0039/R2's sense.**
- **F-004 (medium)** — `test_dropping_a_page_kind_reds_the_medium_independent_assertion`
  is **pure set algebra**: `assert not planned <= (covered - {dropped})` for
  `dropped in planned` is true for any P, C and any d ∈ P. It contains **no call into
  the module under test** and passes on every possible implementation. AC-1's second
  mutant is not lost — the footer-label mutant is the real control — but one of its
  two advertised demonstrations is **empty**.
- **F-006 (low)** — `_no_interior_page_is_the_cover`'s vector arm restates its own
  branch condition and cannot fail; driven with `object()` as the cover, it passes.
  And **two of the three vector arms are driven by no test**, while the stream arm of
  `below_floor_in_its_medium` is never exercised with a non-empty list. The halves
  are each proven; the composition is not.

### Corrections to the orchestrator, and one to a correction of mine

- **My brief's "34 files / 321 sites at HEAD" is mislabelled** — 321 is the figure at
  the cut and on `main`; the branch's own HEAD is **34 / 326**. The round's ADR
  comment was right to say "on main at `4ce84c30`".
- **~~The `setrlimit` skip is `:1297`; my brief has had this wrong three times.~~
  WITHDRAWN 2026-10-29 — I was over-correcting and nobody was wrong.** Measured
  across commits: the `pytest.skip(` call is at **1296** at `f64112f2` and at
  **1297** from `1fd39bb1` onward, because CARD-298's merge changed that file by
  **+7/−2**. So every figure was right at its own commit — my `:1296` for a
  pre-merge tree, the rounds' `:1297` for a post-merge one, and CARD-308's reviewer's
  `:1296` for its own branch, which is cut from `f64112f2`. **I accepted two
  corrections without checking whether both could be true, and then recorded a tally
  of my own errors that was itself an error.** A line number is only a fact with a
  commit attached.
- **My unconditional quote of the sibling set was wrong** — at HEAD `:566-572`
  requires `{guide,divider,band}` and adds the other two only when
  `book != "min-trim"`.
- **My "FINDING 3 RESOLVED — nothing to re-point" is itself now inaccurate.** The five
  `expires_with=("CARD-299","CARD-309")` declarations name this card for a **reader**
  conversion that is **2 of 18 readers done**. Naming CARD-299 as an expiry implies it
  finishes the reader conversion, and it does not. **This is a correction to my own
  correction** and the fix round owes the right answer.
- AC-5's "+272/+361" are the `--stat` bars; `--numstat` reads 261/11 and 359/2 — same
  diff, two readings, and the card should say which.
- The Trace line still says the trace row "is re-stamped in this card"; **no re-stamp
  happened and none was needed.**

## [Fix round 1 — both gating findings taken, and the refusal set is DERIVED, 2026-10-29]

`eed831ea` → **`f0304cb9`**, one commit, 4 files **+558/−54**. `src/` **0 files**,
`tests/fixtures/` **0 files** across both commits; `meta/kanban/` and `meta/review/`
untouched. Validator at HEAD: **0 errors, 102 warnings**, and the round **isolated its
own meta delta** by swapping the two meta files back in the worktree and re-running —
also 102, warning set byte-identical under `comm -3`, so its change has **zero**
validator delta.

### F-001 — taken, and the set is derived rather than listed

The brief's figures reproduce exactly, including on `min-trim`. `assert kind.value !=
"puzzle"` is replaced by **two** derived assertions: a VECTOR page of a kind with **no
vector writer in `src/`** is a FAILURE naming what it owes (ADR-0039/R2), and
`kind.value not in CLUE_DIGIT_KINDS`.

**The derivation reads `src/` with `ast` over `Call` nodes, not with a text search —
and the reason is measured**: `book_guide_vector` *discusses* `_write_clues` at length
in its own comments (`:235-245`) without calling it, and the guide's worked example is
precisely the lettering CON-020 does **not** exempt. **A text search would have
exempted the guide page.** Derived output: `CLUE_DIGIT_KINDS = ['answer', 'puzzle']`.

**Its control is an independent second reading** off the **live spy recording**, keyed
on CON-020's own `EXEMPT_CALLERS` — different medium, different mechanism, no shared
code — asserting both say `{answer, puzzle}`. So a renamed drawer empties the AST
reading and **reds there** instead of quietly refusing nothing. Plus an ADR-0039/R3
non-absorption control and the R2 arm driven on `divider`.

**M1** (revert to `!= "puzzle"`) reds `test_a_vector_answer_page_refuses_too`; **M4**
(delete `book_answer_vector.py:403`'s `draw_clue_digits` call) reds **two** cells — the
derivation control *and* the answer refusal — proving the derivation really reads
`src/`.

**A consequence to carry forward, and it is CARD-231's:** a vector **divider** page
will now fail with *"no vector writer for that kind"*. `divider` has no
`book_divider_vector.py` and no `vector_divider_page`. That is R2 behaving as
specified, and CARD-231 — which makes the divider **born vector** — must either add
the writer or declare the kind.

### F-002 — taken, prose corrected, CARD-309 named

The finding reproduces (lift TITLE's declaration, export, `pdf_pages(data)` →
`KeyError: b'XObject'`). The claim at `:425-427` is replaced with the honest version:
the **helpers** are medium-agnostic, **this module's call site is not**, and the file
now states explicitly that **CARD-299 does not finish the reader conversion and no
`expires_with` naming it should be read as saying so** — same correction in the ADR.

### The cheap findings, all taken, each with a control that reds on the round-1 tree

- **F-003** — `LETTERING_KINDS` keeps its hand-written form and the round **says plainly
  it is not derived**, because there is no authority to derive "letters something" from.
  It gains `NON_LETTERING_KINDS` and a **partition** control over `PageKind`, so an
  unlisted kind is a failure. **M2** (`"toc"` deleted) reds 2 cells on the fix tree and
  **28 passed — a silent pass — on the round-1 tree.**
- **F-004** — the test now **drives the module**: the drop goes into the reading and
  `kinds_covered_in_their_medium` is asked again. **M3** reds 1 cell on the fix tree and
  **28 passed on the round-1 tree.** The set-algebra finding was right.
- **F-006**, all three parts — the cover arm now reads the premise it argues from (the
  cover's `RasterDeclaration` with `expires_with == ()`), so it reds if the cover gains
  an expiry, **and it reds under its own mutant**; the two undriven vector arms have
  tests; and the floor's stream arm is exercised with a **non-empty** list.
- **F-007** — `StreamFace`'s docstring no longer points at a nonexistent `exempt`; the
  absence is now the point, because a content stream carries no provenance to key one on.

**Node ids 172 → 188, removals 0**, the two parametrised ids byte-identical, `trace.yml`
not in the diff — **no re-stamp, no rename, the ERROR-level gate-3 hazard still never
armed.** Runs: the two changed modules **42 passed / 0 skipped**; nine other
`pdf_vector` consumers **653**; five meta-guards **743**; the G-4 tripwire plus
COMP-007's surface **177 / 0 skipped**. One skip across everything, named:
`tests/test_book_pdf_memory.py:1297` at `f0304cb9` — consistent with the withdrawn
over-correction.

### Five corrections to the orchestrator, and two of them land outside this card

1. **`_conditional_silences` is in `tests/test_suite_profile.py:2743`** — my brief
   asserted the reverse. **Fifth report to say so**; already corrected on CARD-315 and
   in memory.
2. **"18 files read an interior through `pdf_pages`" does not reproduce — it is 12.**
   Verified: 18 files **mention** the string, 14 import *something* from the helper, and
   only **12** import the one-image reader. `book_corpus.py` takes only
   `pdf_page_count`, `test_book_toc.py` only `same_page`, and
   `test_book_pdf_geometry.py` imports it **zero** times — it matched because **three of
   its node ids end in `_pdf_pages`**. **A mention count is not a reader count**, and
   the bad figure had already reached **CARD-309's AC-3**, which is corrected there.
3. **"The understatement propagated … in the ADR" does not reproduce** — the clue-digit
   finding was never in `0042-…md`. The round therefore **added** it in corrected
   two-kind form rather than correcting something absent. My claim was wrong and the
   outcome is what the finding wanted.
4. **`main` is now 100 warnings and the branch 102, and main is the dishonest one.**
   Verified by the orchestrator: `FR-045/AC-390` and `AC-391` have **no `def` on main**,
   and their **sole** resolver is `meta/review/20261029T130000Z-CARD-285-cycle1.yml` —
   **the file the orchestrator synced**, after checking it for CARD-285's endpoint
   landmine and **not** for CARD-308's dead-ref hazard. The wrong hazard on the right
   file. **So comparing a branch's warning count to main's is unsound unless the review
   YAMLs are held equal**, and a branch cut before a sync reads *louder* and looks like
   it added warnings. It self-heals when CARD-285 merges, since its fix round has the
   two `def`s.
5. **Validating a `git archive` copy is invalid** — 77 warnings against the worktree's
   102, because the copy has no `.git` and the staleness and drift checks fall silent.
   Worth knowing before another round tries it.

AC-5's `--stat`/`--numstat` labelling, the `:1297` skip line, the 258/204 figures and
`book_answer_vector.py:403` all checked out.


---

## Merge gate and AC/EC/G verification, 2026-10-29

**[AC/EC check] All criteria/constraints ✓** — run by **node id**, not by `-k`, because
a `-k` selection that collects nothing reads as a pass on this board and a bad node id
exits 4 instead of passing silently.

- **AC-1** — the seven node ids run explicitly: **7 passed, 0 skipped**, each named
  individually in the `-rA` listing.
- **AC-2** — **0 `statement:` lines and 0 `then:` lines changed** in
  `requirements.yml` across `4ce84c30..HEAD`, and CON-020's `check:` ref correctly
  **did not move**. The gate clause asking for a moved ref was itself wrong and is
  corrected above: AC-1 requires both node ids preserved, so the re-expression had to
  happen inside the existing class. **The ERROR-level trace gate-3 hazard was never
  armed, because nothing was renamed.**
- **AC-3 / AC-4** — re-homed to **CARD-312**, not owed here.
- **AC-5** — figures **re-measured at the gate and found stale**; see the note in the
  AC block. The recorded 272/361 were cycle 1's, before fix round 1 added more.
- **AC-6** — node-id set difference with `-o addopts=''` against the cut, in a
  throwaway worktree with `PYTHONPATH` asserted under it: **removals 0, additions 16**,
  all named. Matches the review's delta exactly.

**Merge gate: GREEN at `7e434c72` — 9736 passed, 27 skipped, 1 xfailed, 0 failed,
0 errors in 1373.75 s (22:53).** Lock written with an **absolute** `worktree:` line,
trap armed with it and disarmed in the same breath, file verified gone; **0 rival
pytest processes at both ends** (`ps -Ao comm=`, the executable name alone — a `ps`
piped through `grep -c` counts its own shell wrapper, which this board has reported
wrongly three times).

**Collection reconciles exactly: 9736 = main's 9720 + this card's 16 additions**, and
main's own full suite at `47905251` reads **9720 passed / 27 skipped / 1 xfailed / 0
failed** — the same 9720 as CARD-298's green gate at `1fd39bb1`.

### The first gate was RED, and one of the two failures was the orchestrator's

**Gate 1 at `060df4e2`: 2 failed, 9734 passed.** Neither failure was this card's, and
both arms were measured before attributing either.

**`test_no_declaration_outlives_the_cards_that_remove_it` — the orchestrator's,
introduced on `main` in `e861b261`.** Cutting CARD-307 put `Status: skipped` on the
board, a **sixth** status spelling, and `tests/test_book_pdf.py`'s board coupling reds
on exactly that by design. It reproduces identically on `main` alone at `3c3f20db`
**and** on this card's certified tip `f0304cb9`, because `_board_cards()` deliberately
reads the **main working tree's** board rather than the checkout's — so it would have
reded in any card's gate. Fixed on `main` in `47905251`, where widening the status set
alone would have been the **weaker** direction: forge:kanban defines `skip` as
unblocking dependents *"as if the dependency were done"*, so a parser reading
`skipped` as merely "not done" would keep every declaration naming it alive forever.
`_TERMINAL_STATUSES` landed with it, with four new synthetic-board arms as its control
and a killed mutant, because no declaration names a skipped card at HEAD and the real
board cannot witness the claim.

**`…PropertyBandIsExactlyItsMembers::…[db]` — FLAKY, by measurement, and routed to
CARD-320.** A float reaches `uuid.UUID` through `add_puzzle` → `_set_status`. **One
red, two greens** on the same code path: red at `060df4e2`, green at `7e434c72`, green
on `main` at `47905251`. It survived four narrowing attempts — alone on both arms, with
`test_book_export_interior.py` immediately before it, and under a **1018-test prefix
through its own file** (0 failed, 3:26), which clears everything collecting *before*
it. It also cannot have been caused by gate 1's other failure: `test_book_pdf.py`
collects **after** `test_book_arrange_size_filter.py`, so that test ran later.

**Not claimed:** that the flake is understood. One red and two greens establish
non-determinism and nothing more, which is why **CARD-320's AC-1 is to decide
determinism from two unchanged full runs** rather than to assume this card's single
green settled it.
