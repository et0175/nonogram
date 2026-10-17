# CARD-222: Every interior page gets one frame — new margins, a header rule and a footer rule

**Status:** review
**Priority:** P1
**Category:** feature
**Complexity:** architectural
**Estimate:** 1d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/222-interior-page-frame
**Worktree:** ../PythonProject4-card-222
**Source:** owner's artifact "Puzzle page layout", 2026-10-14 (https://claude.ai/artifact/Wp4iGB27cyBAV62da5ACMP) — "The rules behind it": Margins, Header, Puzzle area, Footer
**Idea:** —
**Wave:** 44
**Depends on:** CARD-221 (re-records the interior baselines and owns the same drawing code; racing it would make two cards re-record the same fixtures)
**Touches:** src/nonogram/admin/book_page_spec.py, src/nonogram/export/layout.py, src/nonogram/admin/book_pdf_generator.py, src/nonogram/admin/book_kdp.py, tests/test_book_page_spec.py, tests/test_book_puzzle_frame.py, tests/test_book_page_numbers.py, tests/test_book_finalise_gutter.py, tests/fixtures/book_baseline_card222.json
**Review score:** —
**Started:** 2026-10-17T13:48:43Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

This card is the **container** every other card cut from the owner's artifact sits inside.
It changes the page's margins and gives the page a header rule and a footer rule, so that
"the puzzle area" becomes a named region with a fixed top and a fixed bottom on every page.

**Current behaviour (verified by reading the code).**

- `book_page_spec.py:215` carries the Book 1 profile: trim 21.59 x 27.94 cm, **gutter 1.27 cm
  (0.5 in), outside/top/bottom 0.95 cm (0.375 in)**, `band_mm=12.0`. **CON-018 no longer states
  those values:** it was amended on 2026-10-17 (commit `91609aa`) to the four margins below, so
  the shipped code is now the thing that disagrees with the registry and this card is what
  closes that gap. CON-018's KDP reasoning is unchanged and still explains the gutter (KDP needs
  0.375 in up to 150 pages and 0.5 in for 151-300, and Book 1 straddles 150).
- A titled page reserves `HEADER_BAND_MM = 12.0` (`export/layout.py:345`) above the drawing
  and draws **one centred caption** into it — `f"Puzzle {n}{BAND_SEPARATOR}{tier.label}"`
  (`book_pdf_generator.py:1150`). There is **no rule** under it.
- The folio is drawn by `_draw_folio` at `FOLIO_PT = 10.0`, centred at the foot. There is
  **no footer rule** and **no grid-size label** anywhere on a puzzle page (grepped: no
  size label exists today — the artifact's "20 x 25" is new).

**What changes.**

1. **Margins** become **gutter 0.5 in (unchanged), outer 0.5 in, top 0.55 in, bottom 0.47 in**,
   mirrored on left and right pages. Note the gutter: the artifact draws 0.75 in, and the owner
   decided on 2026-10-14 to keep KDP's required 0.5 in instead — see the measurement and the
   decision at the foot of this card, and take the figures from there, not from the artifact.
   **The CON-018 amendment this card flagged has LANDED** (2026-10-17, commit `91609aa`):
   CON-018 now reads outside 0.5 in (1.27 cm), top 0.55 in (1.397 cm), bottom 0.47 in
   (1.1938 cm), with its gutter clause deliberately untouched at 0.5 in. **Nothing is owed at
   the architect station** — read CON-018 as the spec for this card, and note that the registry
   already carries the measured consequence (usable width 193.675 → 190.500 mm, -1.64%; usable
   height 260.35 → 253.492 mm, -2.63%). This card still does not edit `meta/architecture/**`.
   Record the consequence rather than discovering it later: every margin grows, so the
   usable area shrinks, so **every fitted cell size can only get smaller** and the page
   count can move. Measure the corpus's page count before and after and state it.
2. **The header** runs the full text width: a 0.6 pt rule beneath it, at the **same
   baseline on every page**. The content of the header (what sits left and right of it) is
   CARD-207's; this card owns the rule and the baseline.
3. **The footer** gets a hairline rule, with the **grid size** (e.g. `20 x 25`) on the
   *inner* side and the folio centred at the bottom. The QR that goes in the footer's outer
   corner is CARD-223's; this card owns the rule, the size label and the folio's place in it.
4. **The puzzle area** is everything between the header rule and the footer rule, exposed as
   one region (a frame) so the grid's placement (CARD-224), the two-up split (CARD-226) and
   the openers (CARD-231) all measure against the same thing instead of each re-deriving it.
5. Keep the measured split: nothing here hardcodes a page count. `interior_page_count` and
   `book_kdp.unpaired_interior_page_count` must keep agreeing with what the export writes —
   CARD-205 left a three-caller cross-check in place, and the margin change moves what they
   measure.

## Acceptance criteria

- **AC-1** (happy, margins): *Given* a book with no stored margins, *when* its page spec is
  built, *then* the gutter is **0.5 in (unchanged — owner's 2026-10-14 decision, not the
  artifact's 0.75 in)**, the outer margin 0.5 in, top 0.55 in and bottom 0.47 in, and the
  gutter/outer pair swaps between a left-hand and a right-hand page. The gutter and outer
  margin being equal is now deliberate, so the test must assert both and not one twice.
  (test: `TestBookPageSpec_CarriesTheNewProfileMargins`)
- **AC-2** (happy, the header rule): *Given* any puzzle page, *when* it is drawn, *then* a
  0.6 pt rule spans the full text width under the header, and its y is identical on every
  puzzle page of the book — measured off the drawn pixels, not off the constant.
  (test: `TestBookPageFrame_HeaderRuleIsOnTheSameBaselineEverywhere`)
- **AC-3** (happy, the footer): *Given* any puzzle page, *then* a hairline rule spans the
  text width, the grid size reads `W x H` on the inner side (left on a left-hand page, right
  on a right-hand one), and the folio is centred below it.
  (test: `TestBookPageFrame_FooterCarriesSizeAndFolio`)
- **AC-4** (guard, the area is one region): *Given* the puzzle area, *when* two different
  page kinds measure it, *then* both read the same top and bottom from the same function —
  asserted by calling it, not by comparing two literals.
  (test: `TestBookPageFrame_PuzzleAreaHasOneDefinition`)
- **AC-5** (edge, the type floor survives): *Given* the shrunken usable area, *when* every
  interior face is measured, *then* none falls below CON-020's 10 pt floor.
  (test: `TestInteriorType_EveryFaceHoldsTheFloor`, `tests/test_book_interior_type_floor.py:303`)
- **AC-6** (edge, the page count still agrees): *Given* the 150-puzzle corpus, *when* the
  interior is exported, *then* all three `measured_toc_page_count` callers and
  `unpaired_interior_page_count` agree with what was written, at the new margins.
  (test: `TestBookToc_KdpAgreesWithTheExportedCount`, `tests/test_book_toc.py:595`)
- **AC-7** (edge, the shortest trim): *Given* the shortest trim `book_page_spec` lays out at
  all, *when* a page is drawn at the new margins, *then* the header rule, the puzzle area and
  the footer rule all still fit and the folio still prints.
  (test: `TestBookPageFrame_ShortestTrimStillHoldsTheFrame`)

## Guardrails

- G-1: One source for each figure. The four margins, the two rule weights and the puzzle
  area's bounds are each declared once and read everywhere; a second literal of the same
  number anywhere in the diff is a defect (test: a grep-style structural test, as
  `tests/test_cli.py`'s import guard does it).
- G-2: CON-019 — CLI and web-UI exports stay byte-identical. They draw no book page, but
  prove it (test: `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`).
- G-3: INV-013 — the interior still holds no cover page and parity is still the 1-based
  interior position (test: `PropertyTest_BookExport_InteriorWithoutCoverAndParityFromGuidePage`).
- G-4: A book that stores its own margins still gets them. The profile is a default, not a
  rule — CON-018's last sentence (test: `TestBookPageSpec_StoredMarginsWin`).
- G-5: Baselines are re-recorded as deliberate recordings naming this card and the pages that
  moved; **no earlier fixture in the chain is regenerated or deleted**.
- G-6: Out of scope — what the header says (CARD-207), the QR's new home (CARD-223), where the
  grid sits in the area (CARD-224), the cell size rule (CARD-225).

## System contract

_Assembled 2026-10-17 by `system_rules.py --card CARD-222 --root meta/architecture` (60 rules, `card_scope: touches`) for the registry delta of the same day. A projection — fix the source artifact, never this list._

**Carried notes on these rules** (recorded context, not derivable from the registry):

- **CON-018 — the amendment this card flagged LANDED** on 2026-10-17 (commit `91609aa`):
  outside 0.375 → **0.5 in (1.27 cm)**, top → **0.55 in (1.397 cm)**, bottom → **0.47 in
  (1.1938 cm)**, and the **gutter clause deliberately untouched at 0.5 in** (the owner's
  2026-10-14 decision, which also keeps CON-018's own KDP reasoning intact). Measured
  consequence recorded in the entry: usable width 193.675 → 190.500 mm (-1.64%), usable height
  260.35 → 253.492 mm (-2.63%). **Nothing is owed at the architect station** — CON-018 now
  states exactly what this card builds, and the implementation agent should read it as the
  spec, not as the old profile.
- **Mirrored margins are now a geometric no-op on Book 1** (gutter == outside == 12.700 mm,
  CON-018 as amended 2026-10-17). FR-030's AC-272 and AC-273 now hold the same span
  (12.700..203.200 mm) and FR-032's AC-274/AC-275 the same left edge (25.45 mm), so on the
  default profile **a passing parity assertion about the usable area or a margin width is an
  identity, not evidence** that mirroring works. The mirroring rule (FR-030's last sentence,
  TERM-034) and EC-032's "gutter minus outside" formula stay true with a zero difference and
  still bite on any book storing **unequal** margins — the only configuration in which
  mirroring is actually under test. Owner decision 2026-10-17: record this, do not restore the
  asymmetry by changing a margin. An assertion about *which side* something sits on (left vs
  right by parity) still has teeth; one about *how wide* the margin is does not.
  For this card that lands on **AC-1**: the gutter/outer *swap* is unobservable on the default
  profile because the two values are equal, which is why AC-1 already requires asserting both
  margins by name rather than one twice. A test that wants to prove the swap needs a book
  storing unequal margins.
- **ADR-0036/R2** — the standing tension already logged in `backlog.md`: `page_frame` lives in
  `book_pdf_generator.py`, not in COMP-007. This card adds a region to that same place; say so
  in the notes rather than quietly widening the breach.

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: test: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin pa… (check: review-lens)
- ADR-0036/R3 — Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect whatever Pillow call it is written with: four cards print the same dif… (check: test: test_the_books_own_pages_carry_no_undeclared_round_mark)
- ADR-0036/R4 — No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: t… (check: test: test_no_module_types_a_round_mark_as_a_character)
- ADR-0037/R1 — A book puzzle page never prints the picture's title; its band shows the puzzle number and the solver's tier only. (check: review-lens)
- ADR-0037/R2 — Under the book PageSpec every thin grid rule is at least 0.25 mm and every heavy rule is twice the thin rule, in pure black; the default PageSpec's strokes are unch… (check: review-lens)
- CON-020 — No text the book's interior prints for the reader is set below 10 pt at the page's own resolution, except the clue digits drawn inside a puzzle page's clue cells, w… (check: test: TestInteriorType_EveryFaceHoldsTheFloor)

_53 further rules the lens returned are scoped `src/nonogram/**` (package-wide), so they match every card in the project and narrow to nothing. They are deliberately NOT listed: measured on this board, a ~53-rule contract produced 6-12 real verdict lines out of 53 (CARD-200/203/204), while the 10- and 13-rule contracts of CARD-242/CARD-241 produced 10 and 13 — full coverage. Owner decision 2026-10-17: ship the curated form. The package-wide scoping is the root cause and is recorded in `meta/kanban/backlog.md`._

## Architecture context

- **FR:** FR-032 (the puzzle page's placement — see CARD-224, which reverses CARD-204's
  placement; the amendment CARD-204 had logged against FR-032's "centred" clause was CANCELLED,
  not applied, on 2026-10-17), FR-043 (folios and the interior's pages).
- **CON:** **CON-018 (amended 2026-10-17, commit `91609aa` — outside 0.5 in, top 0.55 in,
  bottom 0.47 in, gutter unchanged at 0.5 in; nothing owed)**, CON-019, CON-020.
- **ADR:** ADR-0036/R2, ADR-0037/R1 (a puzzle page's band carries number + tier only — the
  rule and the footer label are new furniture around it, so R1 needs re-reading at the
  architect station too).
- **Components:** COMP-009 (`book_pdf_generator.py`, `book_page_spec.py`, `book_kdp.py`),
  COMP-007 (`export/layout.py`).
- **Trace:** `meta/architecture/trace.yml` — not updated by this card.

## Worktree notes

- **[Review 2/3] Score 9.0 — ✓ threshold reached. 0 Critical, 0 Important, 2 Minor.** Risk LOW,
  lane FAST. System contract 8/8 ✓ holds, 0 unchecked, 0 violated. F-001, F-002 and F-003 all
  **confirmed fixed adversarially**; F-004 was closed by the orchestrator (the residue record,
  written above). Deduction 10 − 0.5 (F-005) − 0.5 (F-006) = 9.0.
  **F-001's confirmation answered the question I actually cared about** — whether dropping the
  grid comparison lost anything load-bearing. It did not: the old control's second assertion
  (grid thin rule ≥ R2's floor) is independently held at **five** sites outside this diff
  (`test_book_puzzle_frame.py:545`, `test_layout_two_up.py:271`, `test_book_proof_pages.py:428`,
  `test_layout_answer_tiles.py:372`, `property/test_book_answer_tiles.py:161`), and the
  "furniture lighter than grid ink" claim is not merely unguarded but **false** — both measure
  2 px under the CARD-227 simulation. There is no claim left to guard.

- **[Review 2/3, mutation ladder — deferred from cycle 1, executed here: 11 mutants, 8 killed,
  3 survived, every one reverted and verified with `git diff --quiet`.]** Six green baselines
  established before any mutant; `^FAILED` lines counted, never progress characters. **The three
  survivors are the useful part:**
  * **M5 survived by design** — `min_thin_rule_mm` simulated at 0.1693 so the grid's thin rule
    measures 2 px (CARD-227's future state): the retargeted control is green, and the superseded
    one's assertions red exactly as cycle 1 predicted (`assert 2 < 2`). This is the fix's central
    claim, measured rather than argued.
  * **M7 survived → F-005**, the floor's loose lower pin. Carried to CARD-225, which owns
    AC-370, the missing pin.
  * **M9/M10 survived → F-006**, the count bound's overstated prose. Fixed in `e352368`.
  * **M1 is worth noting**: a 1 px shift of `footer_y` survived the *narrow* file (28 passed) and
    was only killed on the covering set, by `test_book_pdf_memory.py`'s pixel-identity and
    file-length assertions. A reviewer running only the obvious file would have called that line
    unguarded. It is guarded — just not where you would look.
  * **M8** closes the third failure shape on the migration guard (on-disk set), after cycle 1's
    two-head and merge cases.

- **[AC/EC/G gate] PASSED.** All seven ACs and all six guardrails carry a named test, and
  **every named test was confirmed to exist on disk** — 13 of 13. Two needed looking for rather
  than grepping: G-2's `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry` is a
  *registry label carried in a docstring*, implemented as
  `tests/property/test_cli_exports_byte_identity.py:154`'s
  `test_property_cli_exports_byte_identical_whatever_the_book_geometry`, and G-3's is
  `tests/property/test_book_export_interior.py:589`'s `test_PropertyTest_BookExport_...`. My
  first grep reported both as missing; **that was my pattern being too narrow, not a gap in the
  card** — recorded because the same false alarm will recur on any card citing a property test
  by its registry label.
  Evidence for each criterion is the merge-gate full-suite run below: if it is green, every
  named test passed, which is a stronger statement than re-running them individually.

- **[Review 1/3] Score 8.5 — clears the ≥8 target, but one Important finding gates the cycle.**
  Risk MEDIUM, lane DEEP. All seven ACs implemented and controlled; migration chain sound and
  the downgrade symmetric; eight system-contract rules checked with no substantive breach;
  G-1..G-6 hold. Step 8f's mutation ladder correctly emitted `deferred(cost)` — the tests it
  would certify are about to change with the fix. Report copied to `meta/review/`.
  Independently re-derived by the reviewer and confirmed: usable 190.5 × 253.492 mm, the cell
  at clue depth 10 = 4.7625 mm (0.0125 above the floor, admitted) and depth 11 = 4.6463 (below
  it), `INTERIOR_FOOTER_MM` 29.8778, the Book 1 frame's 2517 px drawing area and the 10 cm
  trim's 398 px, and the two-up frame identical on both parities so CARD-226/CARD-200 are
  untouched.

- **[Review 1/3, F-001 Important — CONFIRMED by the orchestrator, and caused by the
  orchestrator's own commit]** The footer hairline's new exemption and its ADR-0039/R3 control
  are written against a **retired** ADR-0037/R2. `db04c23` amended R2 the same day, from the
  same architect pass that lowered the floor this card does propagate — so the card was correct
  when written and was invalidated underneath it. Verified by direct measurement rather than
  accepted: `INTERIOR_FOOTER_RULE_PT = 0.4` is 1.667 px → **2 px = 0.1693 mm**, and amended R2's
  minimum is **2 device pixels = 0.1693 mm**. The hairline is *exactly at* the minimum, so the
  docstring's "at 0.169 mm it is deliberately under that minimum" is false and **the exemption
  does not exist**. The control passes today only because `min_thin_rule_mm` is still the
  retired 0.25 (thin rule 3 px): measured, `2 < 3 → True` and `0.254 >= 0.25 → True`, but once
  CARD-227 lands they become `2 < 2 → False` and `0.1693 >= 0.25 → False`. **Two of three
  assertions red, and the red would read as a CARD-227 regression** while actually asserting a
  property the amendment makes unsatisfiable.
  **Settled at the architect station rather than left to the fix agent** (ADR-0037 History,
  2026-10-17): R2 binds the **puzzle grid**, not page furniture — both the superseded wording
  ("every thin *grid* rule") and the amended one say grid. A footer hairline never needed an
  exemption. Furniture is held to the same 2 px floor for the **dropout** reason directly, not
  through R2.
  **The real loss, recorded because it is not bookkeeping:** after CARD-227 the grid's thinnest
  cell line is also 2 px, so hairline and cell line are **the same width**, and furniture can no
  longer be lighter than grid ink *by width* — width has hit the device floor, and 1 px is the
  dropout risk the amendment rejected. The distinction now rests on **tone**, which the design
  already supports (grey cells, dark fifths and border).

- **[Review 1/3, F-004 — recorded here by the orchestrator, which is what the finding asked
  for.]** The five residues all carry controls in tests (R3's requirement is met — the reviewer
  checked each), but they were not written down anywhere an owner would look; three code
  comments point at this card's notes for them. They are:
  1. **The guide page drops caption lines on Book 1.** Bounded by its own asserted set —
     `len(flush) <= 6`, with the docstring stating "a seventh fails here", so a widening reds.
  2. **Seven trims below 10.70 cm print their TOC page without a folio** — asserted as the
     *exact* set `['10.00' … '10.60']`, not a range, plus equalities on the 26 px deficit and
     the 75 px price. 10.70 cm is named as the boundary trim that still numbers its page.
  3. **A book at 8.25 × 8.25 in can no longer be proofed at all.** Moved into
     `REFUSED_TRIMS_CM` and **asserted refused** — `pytest.raises(ValueError, match="no room
     for the proof note")`, parametrised — so a later card that buys the room back reds the
     list instead of silently re-admitting the trim. This is the one I most wanted asserted
     rather than merely absent from a corpus, and it is.
  4. **The pairing window closes earlier**, with the borderline cell re-derived independently
     as `(190.5 − 9.144) / 25 = 7.25424`.
  5. **The bare_level-2 corpus gap widened** — magnitude and height bounded, **count not**;
     that is F-002 below and is going to the fix.
  **Reading of the set as a whole:** four of five are the amended margins taking room away at
  the small-trim end, and each is a *refusal or a degradation that is asserted*, not a test
  that stopped running — which is the distinction the earlier phantom-skip episode was really
  about. The owner validates renders after a merge; residues 1 and 2 are the two worth an
  eyeball on a small trim.

- **[Build gate] PASSED (full, 995s) — fix attempt 2/2, rebased onto `main`.**
  `7873 passed, 9 skipped, 0 failed` in 989.07s, run by the orchestrator under
  `meta/kanban/.full-suite.lock` on a quiet host. **7873 + 9 = 7882, which is exactly the
  worktree's collect-only count** — the figures reconcile, which the earlier gate's did not.
  The 9 are this suite's two documented host gates and nothing else: 8 × `conftest.py:171`
  "Database not reachable" and 1 × `test_book_pdf_memory.py:1256` `setrlimit(RLIMIT_AS)`
  unenforceable on macOS. Both skip messages name the non-skipping tests that carry their
  host-independent halves, so the evidence is placed rather than lost.

- **[Build gate, correction of the orchestrator's own finding] The "48 silently skipped tests"
  did not exist, and chasing them cost a fix-agent attempt.** The earlier gate reported
  `passed=7881 skipped=57`; I read it against a previous gate as +38 passed / +48 skipped and
  briefed the fix agent to account for 48 tests that had stopped running. Measured properly:
  **main collects 7852 and this worktree 7882, a delta of +30**, and collection does not vary
  with the DB environment (7882 both with `TEST_DATABASE_URL` unset and pointed at a refused
  port). `7881 + 57 + 1 failed = 7939` against a tree that collects 7882 — **the figures never
  reconciled with each other and I did not check that they added up.** The sound experiment is
  the fix agent's: two full suites under one *pinned* host condition, one per tree, agreeing
  **9/9** with the database up and **82/82** with it down, per-file identical. **Zero skips
  introduced by this card.** The geometry hypothesis I passed it was ruled out rather than
  merely unsupported: the diff adds no `pytest.skip`, `skipif`, `importorskip` or `add_marker`,
  and no skip reason in the suite is a geometry or fit condition. Lesson, recorded because it
  generalises: **a count that does not reconcile with its own total is not evidence**, and a
  skip delta measured across two runs whose DB state was not pinned measures the host.

- **[Build gate, root cause — a board-level defect, now the top backlog item]** The phantom 57
  came from the shared test database. `tests/conftest.py`'s `db_session` **TRUNCATEs
  `nonogram_test` before every test**, so two concurrently running cards do not merely contend —
  they destroy each other's data, presenting as **skips** when a run loses the database and as
  **failures** when it loses it mid-test. `meta/kanban/.full-suite.lock` serialises *full
  suites only*, so any narrower selection bypasses it. Demonstrated rather than theorised: a
  7-file DB selection run beside a full suite produced 2 failures in
  `test_book_trim_persistence` that are **200 passed in isolation**. CARD-236 was active
  throughout the earlier gate. 57 sits strictly between the two reproducible states
  (9 < 57 < 82) and 57 − 9 = 48 is not any subset-sum of the per-file DB skip counts
  (73/29/18/16/6/4), so it was *partial* reachability during that run, not a stable condition.

- **[Rebase] Clean onto `main` @ the architect pass — the predicted ADR-0036 conflict did not
  fire.** Git resolved the adjacent hunks. Verified **both** halves survived rather than
  assuming: `main`'s 4.75 propagation and new History entry, and this card's re-measured
  tolerance rooms (`fill` 1.8855, `aspect` 47.1809 → 46.5789 at grey 208). The branch carries
  no `meta/kanban/cards/*.md`, so it cannot revert these stamps at merge.

- **[Predicted conflict at the merge gate — recorded so it cannot be forgotten]** `main` moved
  under this worktree while its fix agent was running. `db04c23` (the architect-station pass:
  FR-033 closed, ADR-0037/R2 amended, the 4.75 floor propagated to the ADRs) edits
  `meta/architecture/decisions/adr/0036-book-page-geometry-via-page-spec.md`, and so does this
  card's working tree. The two hunks are **adjacent but disjoint**, and **both must survive**:
  * `main`'s: the Context's FR-031 floor reference and the Consequences' band, 4.8 → 4.75 mm,
    plus a **new History entry inserted at the top of `## History`** — immediately above the
    2026-10-17 CARD-243 entry.
  * this card's: inside that CARD-243 entry, the `fill` room re-measured 1.8859 → 1.8855
    because CON-018's amended margins print the block one row taller — a fourth-decimal move
    with no change of hands.
  Resolution is "keep both". The agent was told **not** to rebase mid-fix on attempt 2 of 2.
  This is logged as a *prediction*, not an observation, so it does **not** go in
  `conflict-history.yml` unless it actually fires — that file calibrates the predictor and
  must not be fed its own guesses. Worth noting for the retrospective that the predictor would
  not have caught this one either: it scores card-vs-card `Touches`, and this is
  card-vs-orchestrator, a class it does not model at all.

- [Why this is the first card of the set] Every other card cut from the owner's artifact
  places something *inside* this frame. Cutting the frame first means the margin change is
  measured once, with one baseline re-recording, instead of each later card discovering that
  the page it is drawing on moved under it.

## Measured at the decompose station, 2026-10-14 — the margins cost 4.9% of every cell

Run against the repo's own `_placed_cell_mm` with the shipped Book 1 spec and the artifact's
four margins, so this is a measurement and not an estimate. Usable width goes 193.68 -> 184.15 mm
(-4.9%); usable height 248.35 -> 237.19 mm. The fit is width-bound for every grid the book
admits, so **every cell that is not already at the 7.5 mm cap loses exactly 4.9%**:

| grid | clue depth | today | at the new margins |
|------|-----------|-------|--------------------|
| 15x15 | any | 7.50 (capped) | 7.50 (capped) |
| 20x20 | shallow | 7.50 (capped) | 7.50 (capped) |
| 20x20 | deep | 7.45 | 7.08 |
| 25x25 | deep | 5.87 | 5.58 |
| 30x30 | shallow | 5.53 | 5.26 |
| **30x30** | **deep** | **4.84** | **4.60 — below NFR-008's floor (4.75 mm since the 2026-10-17 amendment; 4.8 mm when this was measured — 4.60 is under both)** |
| **30x12** | **deep** | **4.84** | **4.60 — below the floor** |

Small grids are unaffected because they are already at the cap. The cost falls entirely on the
large, deeply-clued puzzles — which are the hard ones, printed for the readers most likely to
mark cells by hand. A deeply-clued 30x30 sits just above the floor today and crosses it at the
artifact's four margins, which raises FR-031's below-floor flag. (Figures as measured on
2026-10-14; the floor itself moved to 4.75 mm on 2026-10-17 — see the correction at the foot of
this card.)

**This compounds with CARD-225.** Under a book-wide size per grid size, the deepest-clued
member decides for every puzzle of that size, so one deep 30x30 drags every 30x30 in the book
to 4.60 mm and raises the flag for all of them. The two cards are individually reasonable and
jointly push a whole grid size under the floor. **Surfaced to the owner as a decision before
either card starts.**

## Owner decision 2026-10-14 — the gutter stays at 0.5 in

Presented with the measurement above, the owner chose **outer 0.5 in, top 0.55 in, bottom
0.47 in as drawn, but the gutter unchanged at KDP's required 0.5 in** rather than the
artifact's 0.75 in. Re-measured against `_placed_cell_mm` with the shipped spec:

| | usable width | deep 30x30 cell | deep 25x25 | deep 20x20 |
|---|---|---|---|---|
| today | 193.68 mm | 4.84 mm | 5.87 | 7.45 |
| **shipped by this card** | **190.50 mm** | **4.76 mm** | **5.77** | **7.33** |
| artifact as drawn (0.75 in gutter) | 184.15 mm | 4.60 mm | 5.58 | 7.08 |

The cost falls from 4.9% to **1.6%**, uniformly, on every cell not already at the 7.5 mm cap.
Usable height goes 248.35 -> 241.49 mm.

**Stated as it was presented to the owner on 2026-10-14:** a deeply-clued 30x30 or 30x12 lands
at 4.76 mm, which was then 0.04 mm under NFR-008's 4.8 mm floor, so FR-031's below-floor flag
fired for that case. The owner accepted that with the reasoning that the gutter is where the
page curves anyway, so width spent there is the least useful width on the page.

**Corrected 2026-10-17 (registry delta, commit `91609aa`) — that case is no longer under the
floor.** NFR-008's floor moved to **4.75 mm**, chosen precisely so the margin change costs no
grid a clue-depth step, and the case above re-measures to **4.7625 mm** on the amended margins
with the repo's own `_placed_cell_mm` — **0.012 mm above the floor, so the flag does not fire
for it.** The registry states exactly this as AC-370, "where the retired 4.8 mm floor would
have refused it". The residue moves one depth step deeper and is still real: on the amended
margins a 30x30 falls under 4.75 mm from **clue depth 11 (4.6463 mm)**, depth 12 gives
4.5357 mm, and random 30x30 grids at density 0.5 reach **depth 13 (4.4302 mm)** (NFR-008's own
sweep, reproduced here with `_placed_cell_mm`). So CARD-225 must still handle a grid size whose
shared size is under the floor (its AC-6) — but the example that makes it non-hypothetical is
now a depth-11-or-deeper 30x30, **not** the depth-10 case tabled above. This correction
re-measured the geometry, not the corpus: re-measure the corpus before claiming either way.

**So CON-018's gutter clause is NOT amended** — only its outer, top and bottom values. That
also keeps CON-018's own KDP reasoning intact (0.375 in up to 150 pages, 0.5 in for 151-300,
and Book 1 straddles 150), which the 0.75 in gutter would have left stranded.
- [Env] forge 2026.8.17 (no meta/.skills.yml — no min_version comparison)
- [Scope gate 1/3] **GROWN, not RUNAWAY — judged on the content, not the count.** 48 files against a predicted 9; **85% of the diff is outside `Touches`**, and three `conflict.hotspots` the card never declared are in it (`src/nonogram/admin/app.py`, `src/nonogram/db/**`, `migrations/**`). I read every excess file under `src/` before deciding, and the excess is overwhelmingly **necessary**: `admin.css` (4 lines), two templates (2 each) and `app.py` (2) are **comment and on-screen text** propagating the floor 4.8 → 4.75 — if the registry says 4.75, the admin panel's flag reading "Below the 4.8 mm floor" is wrong on screen — and `book_select_puzzles.html` re-derived its own worked example ("4.84 would read as 4.8" → "4.79"), so it is not a blind replace. ~30 test files changed because they assert geometry figures the margins moved; that is the blast radius of the change this card exists to make, which is why it is the chain head.
- [Scope gate 1/3] Two SCOPE+ items judged individually rather than waved through: **`FLOOR_MM` 4.8 → 4.75** is justified — the registry's re-measured AC-186 (4.7625 mm) is *admitted* at 4.75 and *refused* at 4.8, so leaving the code at 4.8 would ship a book that refuses a puzzle the registry admits; CARD-225 owns *how* the figure is chosen, not the band itself. **Migration 015** is justified and tightly scoped — one server default (`books.outside_margin_cm` 0.95 → 1.27), **no backfill** mirroring 011, on the stated reasoning that rewriting a stored margin would silently re-paginate a book somebody may have finalised, and noting that top/bottom have no columns so need no schema change.
- [Guard] ⚠ **`meta/kanban/cards/CARD-222.md` was committed into the branch** — the same deviation CARD-243 made. Reverted to base before the rebase, so it cannot replay the orchestrator's stamps onto main. (Second instance in one wave; worth a standing brief line.)
- [Touches drift] `migrations/versions/`, `src/nonogram/db/models.py`, `src/nonogram/admin/{app,book_manager,book_proof,print_specs}.py`, `src/nonogram/admin/static/admin.css`, two templates, `tests/helpers/{page_ink,two_up_ink}.py`, `meta/profiling/rank_durations.py` and ~30 test files. The migration directory missing from a card that changes durable state is the exact prediction defect `cmd-decompose` 6c source 3 describes.
- [Conflict] ⚠ **My predicted-conflict graph was WRONG.** It recorded CARD-222 ↔ CARD-243 as disjoint and dispatched them concurrently; they in fact collide on `tests/helpers/page_ink.py` and `tests/test_book_difficulty_dots.py`, because CARD-222's `Touches` listed neither. The rebase onto CARD-243's merge conflicted on one hunk. Recorded in `conflict-history.yml` for the retrospective's hotspot calibration.
- [Conflict] The hunk was a **semantic conflict where both sides were right**: CARD-243 had restructured the assertion to loop over both measured thresholds, CARD-222 had lowered the region floor because its margins shrink the usable area and merge ink. Resolved by keeping **both** claims — the per-level loop and a lowered floor — and the floor was then set from a **measurement of the combined tree**, which neither card could have taken: CARD-243 measured 3222 at both levels on the old margins, CARD-222 measured **2640** at one level on a tree where CARD-243's change did not exist, and the merged tree measures **3209**. CARD-222's 2640 would have left the floor **19% below the real figure — a tripwire that cannot trip.** `REGION_FLOOR = 3200` with the derivation recorded in the code.
- [Build gate] ⚠ **FAILED (attempt 1/2)** after the rebase: 3 failures in `tests/test_book_difficulty_dots.py`, all in CARD-243's `TestRoundMarkOnThePage_PassesOnTheRealBook` — `test_the_books_own_pages_carry_no_undeclared_round_mark`, `test_the_closest_the_book_comes_to_a_round_mark_is_measured`, `test_each_tolerances_own_room_on_the_book_is_measured`. **Two persist when the class runs alone and the third appears only in a full-file run**, so there is genuine breakage AND order dependence. Handed to the fix loop rather than resolved from the orchestrator, with the measurements below.
- [Build gate] ⚠ **Orchestrator error, caught and corrected mid-fix.** My conflict resolution was committed by the rebase in `9874661` **using** `REGION_FLOOR`, and I added the definition as a separate *uncommitted* edit. The three AssertionError failures were observed with it present; it was then lost (most likely the fix agent's own baseline reset, which is correct behaviour on its part), leaving the committed tree with `REGION_FLOOR` used at `tests/test_book_difficulty_dots.py:3775` and **defined nowhere** — a `NameError`, not the failures I had briefed. Corrected to the fix agent in flight, with the measurement (3209 regions at each level on the combined tree, 13 pages; floor 3200) and an explicit invitation to use its own figure if it measures differently. **The lesson is mine: a resolution committed half by `rebase --continue` and half by a loose working-tree edit is one edit, recorded twice, and the loose half is the one that disappears.** Commit the whole resolution or none of it.
- [Fix 1] **PASSED — and it corrected the orchestrator on three counts, all of them mine.** `tests/test_book_difficulty_dots.py` **150 passed**, the class alone 6 passed, `test_suite_profile.py` and `test_guard_integrity.py` green, no `src/` change in the fix.
  1. **`REGION_FLOOR = 3200` was wrong and would have failed permanently.** The combined tree measures **2640** regions at each level, not the 3209 I reported — so my floor sat *above* the real count. Set to **2600**, re-derived, with the whole fall (3222 on `main` → 2640 here) attributed to CON-018's narrower, shorter usable area merging ink that used to separate.
  2. **My 98×94 arithmetic was off by one on both axes.** Pillow's box is inclusive at both ends, so `(144,1072,242,1166)` is **99×95**. At 98×94 the fill reads 1.2520 (2.0996 tolerances), which is what made me conclude the block was *further* from round and the margin had *improved*; at the real 99×95 it is 1.2263 / **1.8855**, which is why it is the closest region. The margin moved 1.8859 → **1.8855** — a fourth-decimal move with **no change of hands**, not an improvement.
  3. **Order dependence was ruled out by measurement, not assumed away.** A standalone script and pytest agree to the digit on this tree, and the class alone and the full 150-test file produce the same three failures with the same messages. My "2 alone vs 3 in a full run" observation was an artifact of the undefined `REGION_FLOOR` raising `NameError` at different points.
- [Fix 1] ⚠ **Root cause of all three of my errors, recorded because it is a method defect, not bad luck: I measured with a bare `importlib` module exec instead of with pytest.** That harness does not reproduce the runner's environment, so it reported `main`'s figures (3209 regions, closest `(144,1266,242,1359)`, aspect room 47.1277) on a tree whose real figures are 2640 / `(144,1072,242,1166)` / 46.5789. I then "resolved" a contradiction between my own stale numbers and pytest's correct ones by inventing order dependence. **Measure with the runner that gates.** I have been briefing every agent this wave to establish a baseline before trusting a mutant, and then used an instrument that was not the gate.
- [Fix 1] The fix also replaced the box pins with **footprint pins** — CARD-243's own review finding F-001, now applied: `closest.box` / `fill_closest.box` assert `(width, height)` plus, for the fill block, that the *same region* sets fill's room at both thresholds. What that gives up is **position only**, which is exactly what a page-layout change is allowed to move. The tie it was pinning moved from 16 members to **11** on this tree, which is why the footprint and not the count is what is asserted. 5 mutants, 5 killed, including one that shifts the region a single row (`(99,96) == (99,95)` reds in both tests).
- [Fix 1] Carried over from the widening pass: **`_confirm_membership_change.html:51` still read "the 4.8 mm floor"** — this card edited that file and missed the line. Fixed here (one comment line); `grep` now finds no `4.8 mm floor` anywhere under `src/nonogram/admin/` or `src/nonogram/export/`.
- [Build gate] ⚠ **FAILED (attempt 2/2)** — full suite, 997s: **7881 passed, 1 failed, 57 skipped**, exit 1.
  - **The failure is the migration-chain guard doing its job**: `tests/test_batch_requested_tier.py::TestBatchRequestedTier_Migration014IsReversible::test_014_revises_013_and_is_the_only_head`. This card adds migration **015**, so 014 is no longer the only head. Legitimate consequence of a justified SCOPE+ migration; the test needs to know 015 exists.
  - ⚠ **The more serious signal is the skip count: 57 against this suite's usual 9.** Collected total rose 7852 → 7938 (+86), of which **+38 passed and +48 skipped**. CARD-222's own new files are clean — `test_book_page_frame.py` 28 passed, `test_book_interior_face.py` 17, `test_book_guide_page_type.py` 17, **zero skips between them** — so the 48 are elsewhere. One confirmed reason in a narrow selection: `tests/conftest.py:171: Database not reachable: DATABASE_URL is not set`, i.e. the silent-skip path this board already tracks, plausibly reached because migration 015 leaves the alembic chain inconsistent for anything that applies migrations. **48 tests that quietly stopped running is a larger evidence loss than one red test**, and it was invisible in the pass/fail line — it only surfaced by comparing skip counts against the previous gate.
- [Build gate] Diagnosis handed to the fix loop rather than guessed from here: the authoritative answer is a full-suite run with `-rs`, which belongs in the fix agent's own loop. My narrow selection (`-k "migration or batch_requested or db or admin_import"`) showed only 1 DB skip, so the remaining ~47 are in files this card modified and I will not speculate which.
