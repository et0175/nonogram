# CARD-358: `tests/test_book_interior_type_floor.py` — 7 reds, all M10, in the module that sat in neither of CARD-329's populations

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c (0.5d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/358-interior-type-floor-m10`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-358
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79 <!-- DISPATCHED 2026-11-05T06:23Z as wave 79's vector-slice card. Premise VERIFIED under the five-kind probe: 8 failed / 43 passed, 7 M10 (this card) + 1 M1 (CARD-322). First step of the ADR-0042 slice the owner reopened after eleven days. Cut off the stamping commit so it cannot un-stamp its own Wave. -->
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_interior_type_floor.py
**Review score:** —
**Started:** 2026-11-05T06:23Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

> **⚠ UNVERIFIED FIGURES, 2026-11-05.** This card quotes **57 M10 reds / 35 cause lines**. They are CARD-337's round's roll-up and **three readers have now tried and failed to verify them** (CARD-358's round, its review, and the orchestrator). The review's census aborted on its own gate at 14 of 20 modules — *the instrument working*, a zero-collect most plausibly caused by a foreign lock appearing mid-run, since the guard refuses in `pytest_configure`. **And one component has already moved:** CARD-356's module measures 26 reds, not its stated 25. **Do not quote the roll-up as fact; re-derive your own module's count at the start**, which is what scopes your card anyway.

## The population, from CARD-337's cross-tab

> **✓ PREMISE VERIFIED AT THE STATION, 2026-11-05 — it reproduces EXACTLY.** Run under this card's
> own stated condition, the five-kind probe (`pytest -p scratchpad.card338.probe_five_kinds`, the
> instrument CARD-338 landed): **8 failed / 43 passed**. Classified by re-running each failing node
> and reading its cause: **7 are M10 (this card's)** and **1 is M1 (CARD-322's)** — the
> `monkeypatch.py` `KeyError: <PageKind.TITLE: 'title'>` delitem site, on
> `test_lifting_a_declaration_makes_the_stream_arm_read_that_page`. The 8 = 7 + 1 split is exactly
> what the card claims.
>
> **Note for the round, because it will mislead you otherwise:** on `main` *without* the probe this
> module is **51 passed, 0 failed**. The reds are a property of the converted end state, not of the
> tree — so a bare `pytest tests/test_book_interior_type_floor.py` will tell you nothing and look
> like a refuted premise. The orchestrator made that mistake first and checked the condition before
> announcing it.

**8 reds under the five-kind probe; this card owns 7.** The other is **M1**
(`monkeypatch.py: KeyError: <PageKind.TITLE: 'title'>`, a `delitem` site) and is **CARD-322's**.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M10** medium-blind empty read | **7** | a residual — see below |

## Why this module matters out of proportion to its seven reds

**It is the 22nd module — the one that sat in NEITHER of CARD-329's populations.** It reaches
the medium hazard through **the medium decision itself**, which is a third population both of
that card's filters were structurally blind to. CARD-329's "the arithmetic closes" was true of
the 20 modules it chose and not of the tree, and this module is the counterexample.

**And it is the cleanest available test of whether M10 can be split at all.** This card's reds
are **pure M10** with no other mechanism mixed in, in one small module. Board-wide M10 is 57
reds across **35 cause lines** held together by a catch-rule with **25** top-level alternations (⚠ this card said *sixteen*; measured **25**, re-derived by the orchestrator with escape-aware depth tracking (my first two counts were wrong — escaped `\(`/`\)` were being read as groups) — ADR-0039/R4) — the
"other" bucket ADR-0039/R2 forbids, wearing a label. **If M10 is really several mechanisms, this
is the cheapest place to find out**, and the answer scopes CARD-354, CARD-355, CARD-356 and
CARD-357, which hold 45 M10 reds between them.

**So treat the split as this card's primary deliverable, not a precondition of it.** Report the
histogram even if the repair turns out trivial.

## Two taxonomy findings from CARD-337's round, which bear directly on your split

Measured while classifying its own single M10 red, and both are reasons the label is not a
diagnosis:

1. **M10's label is wrong for at least one member.** The rule's description is *"medium-blind
   read returns EMPTY"*, and CARD-337's M10 red is a read that returns a **full 2550×3300
   bitmap**. Nothing is empty. It matched M10 only via the alternation
   `'is the blank title page'` — a string from the cause line, not a mechanism. **So when you
   split your 7, expect the label to describe some members and not others, and say which.**
2. **M11 is keyed on a MODULE FACT standing in for a mechanism.** Its rule is anchored on the
   literal `test_book_pdf_band.py`, so CARD-337's red — *mechanically the identical
   `_write_page`-counter collapse* — could not match it and fell through to M10. Both routes
   happened to land on the card owning that module, so nothing mis-routed this time. **The next
   one will.** If your split finds a write-counter collapse, this is why it will not be labelled
   one.

**Recommend re-keying M11 by mechanism** rather than by module, and report whether your 7 contain
anything the taxonomy would mis-key the same way. `scratchpad/card338/classify_reds.py` holds the
rules; **CARD-338 is closed, so a change there is a finding with a measurement, not an edit you
make silently.**

## What to implement

1. **Split the 7 M10 reds by cause signature** and report the histogram. State whether they
   share a cause.
2. **Name the mechanism(s)** in terms a taxonomy could hold — `classify_reds.py`'s `RULES` is
   the authority, and if a rule should be added, propose it as a finding rather than editing
   CARD-338's instrument.
3. Repair or disposition each, per ADR-0042/R6.

## Acceptance criteria

- **AC-1** *Given* the 7 M10 reds, *then* their cause-signature histogram is reported and each is
  named as a mechanism or stated to share one — **this is the card's primary deliverable**.
  (check: review-lens)
- **AC-2** *Given* the finding, *then* the card states what it implies for the 45 M10 reds held
  by CARD-354/355/356/357 — a scoping statement, not a fix.
  (check: review-lens)
- **AC-3** *Given* the five-kind probe, *then* the module's red count is stated before and after,
  and the M1 red is **still present and attributed to CARD-322**.
  (check: review-lens — a stated count is not a test. **No card owes a flip**: the instrument that
  produces it lives in the worktree, and the force-add gate forbids tracking it, so no committed test
  can name it.)
  > **⚠ RESTATED 2026-11-05 on CARD-358's review (F-004).** It carried `(test: named by the
  > implementation; state it)`, but AC-3 is a stated count and AC-4 a mutation run — neither is
  > test-shaped, and `test_no_new_artefact_file_is_force_added_into_the_resolver_domain` makes a
  > committed test naming them impossible. A `(test:` marker on a claim no test can decide reads
  > as mechanically checked when it is not. **The substance of both held and the review verified
  > both.**
- **AC-4** *Given* each repair, *then* a plant re-breaks it with its matched control green in the
  same run and `0 skipped`.
  (check: review-lens — a mutation run is not a test; see AC-3's restatement. **No card owes a flip.**)

## How to measure, and the instrument is not yours to build

**Re-derive your own population before implementing anything.** The instruments are committed:

- `scratchpad/card338/census_five_kinds.py` — the driver (drives `probe_five_kinds.py`). **Run
  it, do not rebuild it.** CARD-338 owns, committed and refusal-proved it.
- `scratchpad/card338/classify_reds.py` — the mechanism taxonomy.
- `scratchpad/card337/cross_tab.py` — the mechanism × module table. It **imports** `RULES` /
  `classify` from `classify_reds.py` rather than restating the taxonomy; keep that property if
  you extend it.

**Two hazards in those instruments, both measured:**

1. **`classify_reds.py` is NOT filter-agnostic.** Faithful on the five-kind dump (143/143, exit
   0, no "other" group). On a `PUZZLE`-only dump of the same thirteen modules it leaves **13 of
   78 unclassified and exits 1** — loud, but only if you read the exit code. **Scope nothing
   from a `PUZZLE`-only reading.**
2. **A mechanism census of the UNPLANTED tree is not the census after a repair.** Measured:
   `pdf_band` shows **zero** byte-identity reds unplanted, and **three** among the survivors
   once the `interior_images` seam is planted. So your post-repair survivors may carry
   mechanisms your pre-repair census does not list. Re-census after your repair, not only
   before.

**And `-rfs` omits ERRORs — use `-rEfs`.** That matters more here than usual: **21 of the 40
M7d reds board-wide print as `ERROR at setup`**, fixture-raised, so one repair flips many node
ids at once and one plant can re-break many. Clear `addopts = "-q"` with `-o addopts=` as **two
argv items**. The worktree has no `.venv` — use
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`.

## Guardrails

- **G-1** — **No `src/` change.** Every product-behaviour red in this module family is routed to
  **CARD-322** (M1 delitem, M2 expected-side gap, M3 `Image`-arrived-as-vector, M3b the cp1252
  title refusal). If your measurement indicts the generator, that is a **finding and a routing**,
  not an edit.
- **G-2** — **Do not widen a bound or a tolerance to make a cell pass.** `EDGE_TOLERANCE_MM`,
  `EDGE_TOLERANCE_PX` and `HALF_PIXEL_MM` are not yours to move.
- **G-3** — **Stay inside your `Touches`.** The module partition is what makes these cards
  concurrently runnable; a card that reaches into a sibling's module destroys that property.
  Planting a mutant into another module and restoring it byte-identically is a measurement and
  is allowed — the SHA-256 pair is the proof — but leaving an edit there is the violation.
- **G-4** — No new runtime dependency (ADR-0006/R1): stdlib + Pillow + NumPy is closed.
- **G-5** — Take no timing measurements and report no durations; other work shares the machine.
- **G-6** — A full suite needs the board's lock (`meta/kanban/.full-suite.lock`, structured,
  identity is the **worktree**, no pid). **Never** set `NONOGRAM_IGNORE_FULL_SUITE_LOCK` and
  never redirect `NONOGRAM_FULL_SUITE_LOCK` — the guard fires in `pytest_configure` for **any**
  selection, so a redirect blinds a file-scoped run to a gate that *is* holding it.
- **G-7** — **G-8 standing: do not connect to the production database.** `conftest.py` refuses
  by URL text before connecting; do not widen or bypass `_refuse_unless_test_database`.

## System contract

- ADR-0039/R1 — a claim needs a control that can fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an authority the runtime can enumerate; where none
  exists it defaults to **deny** (check: review-lens)
- ADR-0039/R4 — a figure recomputed and refuted is retracted everywhere it was written
  (check: review-lens)
- ADR-0042/R1 — interior pages are operators (check: review-lens)
- ADR-0042/R6 — a claim that has no subject in the converted medium is re-expressed against the
  content stream or retired with a named survivor (check: review-lens)

## Worktree notes

[Fix round for cycle 1, commit `24fbeec8`] **F-001 and F-002 closed**, one tracked file
(`tests/test_book_interior_type_floor.py`, **+162/−40**). **Orchestrator-verified on the tip:** probe-scoped
**1F/52P** (the one red is CARD-322's M1 `test_lifting_a_declaration_makes_the_stream_arm_read_that_page`,
left untouched), unlifted **53P**, `src/` diff empty, nothing under `meta/` on the branch, worktree clean.
The round took no lock and ran no full suite.

[Fix round] **F-001: `worked_example = []` now reds this module, by a POSITIONAL signal.** Re-derived
first: before the change the plant left the module at 1F/51P, byte-identical to baseline, and the only
newly red nodes were the two the reviewer named in `test_book_guide_page_vector.py`
(`test_the_page_draws_every_diagram_through_that_one_routine`,
`test_an_engine_that_did_not_write_the_file_reads_the_digits_back`); `test_each_clue_digit_size_really_reaches_the_file`
stayed green, as the review said. **There is no per-diagram attribute** — `DrawnFace` carries only kind,
text and size, and `GuidePage.faces` is a flat tuple — so the round used position: the worked example is
the last diagram the page draws, so on a page whose `fallback_level[2] == 0` the last N clue-digit faces
must equal `WORKED_EXAMPLE_CLUE` repeated once per `WORKED_EXAMPLE_STEPS` entry. New helper
`guide_pages_for(book)`, and a new non-vacuity test, `test_a_book_keeps_the_worked_example_on_a_guide_page`,
so the position check cannot read green on every book at once. After the change the same plant reds
`TestInteriorType_OnlyPuzzleClueDigitsAreExempt::test_worked_example_digits_are_drawn_and_never_exempt[book1]`
with *"The worked example drew nothing, or something else now closes the page."*
**Two limits, stated by the round and worth keeping:** `[min-trim]` stays green, because that book's writer
fallback is `bare_level` 2, which drops the worked example from the page entirely — *the claim has nothing
to read there*; and the check would not notice a worked example replaced by a diagram with the **same digit
sequence**. The docstring now says "one of four" and names what position does and does not carry.

[Fix round] **⚠ A RETRACTION THAT IS THE REVIEW'S AND MINE: "on today's committed tree the raster branch is
specific" is FALSE.** The round measured it: planting an empty `worked_example_images` in
`BookPDFGenerator.create_guide_page` and running **unlifted gives 53 passed, zero reds.** The cause, which
the orchestrator verified: `WORKED_EXAMPLE` is the call name `draw_example_line`, and
`create_guide_page` calls it from several diagram families (three separate call sites), so a call-name
signal cannot isolate the worked example in either medium. The round could not use a tail reading on the
raster side either, because the raster call order is unstable (technique rows are re-drawn per fallback
attempt). **It left the raster branch as it was and disclosed that in the docstring.** I repeated the
review's sentence into this card and into the fix round's brief **without re-deriving it** — the same
omission as the "4 A reds". **Open for cycle 2, not decided here:** whether any other test in the repo
covers the raster worked example, which decides whether this is a gap on today's tree or only in this
module. The orchestrator has not checked.

[Fix round] **F-002: every citation re-verified by planting, and the review's measurement of one of them
was itself taken against the wrong plant.** All **14** cited classes resolve by `ast` against their
`ClassDef`. Per kind, each cited test marked *reds under the plant* or *corroboration only*, with the medium
it reads: **guide** — two vector-medium tests, both red. **Band** — three vector tests red,
`test_the_band_fits_the_way_the_raster_page_fits_it` corroboration only (geometry). **Footer label** —
`test_the_page_carries_all_four_pieces_of_furniture` and `test_the_reading_sees_each_piece_go_missing` red;
the PIL descender test and the two-up pair test corroboration only. **Answer caption** — two **vector**
survivors red (`test_the_caption_is_right_aligned_on_the_slot_comp_007_reports`,
`test_the_title_prints_only_on_answer_pages_across_a_corpus`), so **the converted medium is now covered**;
the raster `test_caption_reads_answer_caption_when_there_is_room` reds only under the raster plant;
`test_on_a_two_up_page_there_is_slack_and_the_caption_prints_at_the_floor` is green on both plants and is
corroboration only. The docstring says plainly that the raster survivor reads the raster medium only.

[Fix round] **⚠ THE REVIEW'S FOOTER-LABEL PLANT WAS NOT THE FOOTER LABEL.** Cycle 1's artefact names
`footer-label-never-lettered-vector` and describes it as *"book_sheet_vector's caption loop"*; the round
measured that the loop it describes is the **QR-links loop**, not the footer label. Planting that loop reds
`test_the_pair_carries_one_folio_two_links_and_no_size_label` **along with six other tests**; planting the
real footer-label plant (`size_label` never set) does **not** red it, **which is correct** — a two-up page
carries no label by design. So the review's "footer label 1/2" scorecard row was measured against the wrong
plant, and the round re-measured with the real one. **The orchestrator verified only that the artefact
describes the plant as a caption loop in `book_sheet_vector`; it did NOT verify which loop that is.**
**Also unreconciled:** the review counted **three of seven** survivors unable to fail, the round counts
**five of the first draft's eight** citations wrong (band_fits, footer_lines, the two-up test for the label,
and both answer-caption citations). Different denominators and different plants; **cycle 2 is asked to
reconcile them.** The docstring now says "five of the first draft's eight citations".

[Fix round] **Mutants.** The original nine all re-break their claims in the final run, **no new survivors**,
each by text with the count `== 1`, SHA-256 both ends, restored from captured content, matched control green,
`0 skipped`. `worked-example-draws-nothing` re-breaks at `[book1]` (its first run printed "NOT re-broken"
only because the expected-message string had the wrong capitalisation; fixed and re-fired alone). **The four
retirement plants sit in the runner with an EMPTY `must_red`**, so they print "re-broke: NOTHING" — the
round says that reflects the empty list and not a hole, because their real survivors are verified by a
separate `plant_runs.py`. **Both scripts stay untracked in the worktree; neither was force-added.** Note
for cycle 2: a runner entry with an empty `must_red` is **not a control that can fail**; the survivor table
is review-lens evidence, not a committed test.

[Review 1/3] Score: **7.5 — FAIL** (threshold 8.0). Artefact `meta/review/CARD-358-cycle1.yml`,
uncommitted. **Four small items for cycle 2**, two of them the round's and two mine.

[Review 1/3] **THE THREE-MECHANISM CLASSIFICATION IS UPHELD — do not re-cut the four cards.** All three
distinguishing measurements reproduced under CARD-338's probe: **A** the spy exempts **0** in both books
while the stream exempts **644** in each, kinds exactly `{answer, puzzle}`; **B**
`book_guide_vector.EXEMPT_KINDS == frozenset()` and the stream's one provenance is the mark, which means
exempt; **C** the spy's semantic reading collapses to `{'divider'}` for both books. The histogram holds
end to end: main under the probe **8F/43P**, branch **1F/51P**, the survivor being CARD-322's M1. The
reviewer then ran CARD-338's **own** `classify()` over its eight measured cause lines: all seven classify
M10 and the eighth M1, so there is **no taxonomy hole**. **Why three and not one with three symptoms**,
which is the question I asked: at the level of *cause* it is one thing — provenance keyed on the raster
medium goes quiet — but a taxonomy is tested by whether its partition predicts the *disposition*, and
on that axis there are three values with three different repairs (an equivalent exists, so union the
arms / it exists but means the opposite while another authority does / none exists, so retire with a
survivor in another vocabulary).

[Review 1/3] **⚠ ONE CORRECTION TO WHAT I PROPAGATED, and it is mine.** The block I wrote onto
CARD-354/355/356/357 said *"expect C to be the expensive one — B had an authority to fall back on."*
**That ordering does not survive measurement:** B's authority (`GuidePage.faces`, tagged `CLUE_DIGIT`)
is **coarser than the claim**, so B collapses into C in practice and **B is not cheaper than C.**
Corrected on all four cards, attributed to the review. And **"644" is PER BOOK** (1288 across both) —
corrected on all four, since the figure is quoted.

[Review 1/3] **F-001 (high) — the B re-expression's "drawn" half cannot fail for its own subject.**
Planting `worked_example = []` in `book_guide_vector` — the worked example draws **nothing at all** —
leaves the module at **1F/51P, byte-identical to baseline: zero new reds.** The guide lays out **four**
families of line diagram (`basic_rule`, `cell_states`, `worked_example`, `technique_rows`), **all four**
tag `CLUE_DIGIT`, and the technique rows alone keep `assert digits` satisfied (24 faces on book1, 8 on
min-trim). So the disclosure's load-bearing sentence — *"the worked example is the page's line diagram,
so the faces are the same faces"* — is **one of four**, not the whole. **My item 3 ruling from the
review: the narrowing is NOT acceptable as written.** The cited corroborating survivor
(`test_each_clue_digit_size_really_reaches_the_file`) has the same non-specificity and also stays green;
it merely sits beside the claim. What *does* catch the plant, and is **cited nowhere**:
`test_the_page_draws_every_diagram_through_that_one_routine` and
`test_an_engine_that_did_not_write_the_file_reads_the_digits_back`. The "never exempt" half is fine.
**Scope, stated honestly:** on today's committed tree GUIDE is raster so the raster branch runs and is
specific; **⚠ RETRACTED 2026-11-05 (ADR-0039/R4) — the raster branch is NOT specific: the fix round measured planting an empty `worked_example_images` in `BookPDFGenerator.create_guide_page` and running unlifted: 53 passed, zero reds. See the fix-round record below.** **the vacuum is in the converted end state — the state the card's reds live in and the repair
was written for.** ADR-0039/R1 violated.

[Review 1/3] **F-002 (high) — three of the seven retirement survivors cannot fail for the reason they
are cited.** All eight resolve by `ast` against their `ClassDef` (the round's correction holds). Four
plants: **band** — `test_every_band_the_section_shows_is_a_number_and_a_tier` reds ✓, the co-cited
`test_the_band_fits_the_way_the_raster_page_fits_it` stays **green** (ratio-constant parity and
`slot_room` arithmetic; it never reads what was lettered). **Footer label** —
`test_the_pair_carries_one_folio_two_links_and_no_size_label` reds ✓, the co-cited
`test_the_footer_lines_sit_where_the_raster_page_sets_them` stays **green** (a PIL descender claim).
**Answer caption — NEITHER cited survivor reds**; it is caught by two **uncited** tests,
`test_the_title_prints_only_on_answer_pages_across_a_corpus` and
`test_the_caption_is_right_aligned_on_the_slot_comp_007_reports`. **And the sharpest part: both cited
`answer caption` survivors read a RASTER PIL rendering via `gen._packed_answer_page` — for the one kind
whose retirement is justified BY its conversion to vector, no cited survivor reads the converted
medium.** Scorecard: guide 1/1 strong, band 1/2, footer label 1/2, answer caption **0/2** for the
converted medium. **Not Critical** because real coverage exists in every case (15/7/2/7 newly-red
nodes); *it is the citation that is wrong, and a citation is what the next card acts on.* ADR-0042/R6
**met in letter, not in force.**

[Review 1/3] **F-003 (medium) was mine and is retracted above** — "the 4 A reds" is 3. **F-004 (low) is
the ACs', restated above.** **F-005 (medium) is another card's and is routed, not fixed here:**
`tests/test_book_pdf_band.py` under the probe measures **16 failed + 10 errors = 26 reds** against
CARD-356's stated **25**; now noted on that card as reviewer-reported and unverified.

[Review 1/3] **Verified, no finding.** The non-vacuity assertion **has teeth**: `divider-declared-vector`
re-fired at **14F/38P/0S** with the guard's own phrase *"has gone vacuous"* in the output. **All nine of
the round's mutants re-break their claim**, controls green in the same run, `0 skipped` on the baseline
and all nine, every `src/` file SHA-identical both ends. **SCOPE+ (a)** vacuous exactly as claimed (the
old `not {"guide","divider","band"} <= kinds` is true whether or not band calls are dropped);
**(b)** reproduces exactly: pre-fix **10F/38P/2S** with `got empty parameter set` printed twice,
post-fix **12F/38P/0S**. **25 alternations** — a **third** independent derivation, cross-checked with
`re.compile(...).groups == 2`. Both taxonomy findings confirmed structurally. **Considered and rejected
as a finding:** the two-arm union being weaker than a per-kind medium dispatch — it is the module's
established idiom.

[Review 1/3] **THE BROWSER RED DOES NOT REPRODUCE on `adaac606`.** Full suite **unarmed**, the reviewer's
own lock held and released: **10376 passed / 0 failed / 0 errors / 30 skipped / 1 xfailed** of 10407
collected, reconciling exactly, FAILED/ERROR grep empty, and `test_reverse_order_passes` **PASSED in the
full suite**. Skips read off `-rEfs`: **29** × the bare-`DATABASE_URL` gate + **1** × `setrlimit` = **30**;
`db_required` **derived** at 29/10407. **So CARD-358 has a green full-suite on its tip.** **A mechanism the
round could not name, offered as a HYPOTHESIS and not measured:** the test spawns a child pytest under a
**90-second** timeout and that child's selection is a **Playwright** module, so a browser-launching
child under a parent full suite plus another worktree's Playwright work is a concrete way to time out.
It is not this card's and not pre-existing; the round was right to raise it and right not to clear it.
**Not carded**, under the cut bar: unreproduced, and nothing is blocked.

[Review 1/3] **57 / 35: ATTEMPTED, NOT COMPLETED — three readers have now failed.** The review's census
got through **14 of 20** modules and aborted on **its own** loud gate —
`tests/property/test_book_pdf_geometry.py: collected NOTHING — a green exit is not a pass`. That is the
instrument working: the module collects 4 tests on an immediate retry, so the zero-collect was
transient, most plausibly **a foreign lock appearing mid-census**, since the guard refuses in
`pytest_configure`, which yields exactly zero collected. The partial census is recorded in the
artefact and is what produced F-005. **Pointer added to every open card that quotes the roll-up.**

[Review 1/3] **A liveness hazard hit twice by the reviewer, worth keeping.** `pgrep -lf "m pytest"` matched
its **own zsh wrapper** (whose argv holds the whole script) and **missed** the real pytest, reading as
"the suite is dead"; a monitor's `grep -c "[-]m pytest"` reported `pytest_alive=2` with **one** real
pytest, reading as "a child pytest is running now". **It bites hardest on a test whose subject IS a
child pytest** — which is exactly what `test_reverse_order_passes` is. Resolved by `ps ax -o
pid,etime,command` plus the output file's mtime.

[Round, commits `95c25cb6` + `adaac606`] **Done, and the primary deliverable landed: M10 is THREE
mechanisms, not one.** Probe-scoped **8F/43P → 1F/51P**, the one remaining red being CARD-322's M1
delitem, left standing untouched — a card that repairs its neighbour's red hides which card the
repair belonged to. Unlifted: 51P → 52P, the extra node a new control. The orchestrator's 8 = 7 + 1
split reproduced exactly. **The three-mechanism finding is propagated onto CARD-354/355/356/357**,
which hold 45 M10 reds between them and whose disposition differs by mechanism.

[Round] Per-red disposition: the **3** **A** reds **re-expressed** *(⚠ this read "the 4 A reds" — RETRACTED, ADR-0039/R4: A is 3, B is 2, C is 2, and 3+2+2 = 7. The round's own header said 4 while listing three tests; I copied the header into this record without counting the list, and my own classification output earlier in the session showed three. CARD-358's review caught it.)* as a union of the two arms
(`TextCall.exempt` and `StreamFace.exempt`, neither keying on a face's size); the 2 **B** reds
**re-expressed** against `book_guide_vector`'s own per-face record with two structural bounds that
can fail, and **stated in the docstring as genuinely narrower** than what they replaced; the 2 **C**
reds **re-expressed plus 4 retirements with named survivors**, each survivor verified to exist and
each class name **resolved by `ast` against its enclosing `ClassDef`** rather than by text. The new
intersection is asserted **non-empty**, so the day `DIVIDER` stops being raster this reds and that
card owes a reading or a survivor.

[Round] **AC-4: 9/9 mutants re-broke their claim**, matched control green in the same run, `0 skipped`
asserted on the baseline **and on all nine mutant runs**. Five are named edge mutants, and the
non-vacuity one is the important one — `divider-declared-vector`: without it the repair reads green
over a claim that had ceased to exist. Every `src/` file restored **from captured content**,
SHA-256-identical both ends, `git status src/` clean.

[Round] **Two `SCOPE+` fixes under the owner's cut bar, both found by its own measurement and both
the right call.** First, the matched control for the claim it re-expressed **had gone vacuous under
the probe**: it asserted against a hard-coded triple that the *conversion itself* satisfies, so the
band could have gone on being drawn or stopped and the control read green either way — ADR-0039/R1
made that one its own. Second, **a derived parametrize that empties into a SKIP**: a mutant collapsed
the derivation and pytest reported `got empty parameter set`, giving **2 skipped in a module whose
baseline is 0**. A skip is not a deny (ADR-0039/R2); it now yields a named sentinel refused by name,
so it fails saying what happened. That mutant run went `10F/38P/2S → 12F/38P/0S`.

[Round] **A figure of the orchestrator's brief does NOT reproduce, and it is retracted here and on
CARD-354** (ADR-0039/R4): M10's catch-rule has **25** top-level alternations, not *sixteen*. The
round counted 25; the orchestrator re-derived 25 independently — **on the third attempt**, the first
two having been wrong because escaped `\(`/`\)` were being counted as groups. The enumeration is
legible and item 8 is the nested `IndexError: (…|…)`, correctly one. The companion figures
(57 reds, 35 cause lines) are CARD-337's round's and **neither the round nor the orchestrator has
re-derived them** — they remain unverified rather than confirmed.

[Round] **Two taxonomy findings for whoever owns the taxonomy.** M11's rule is anchored on the
literal `test_book_pdf_band.py`, a **module fact standing in for a mechanism** — it would have
excluded all seven of these reds regardless of mechanism, so nothing mis-routed this time but the
defect is confirmed structurally, and re-keying M11 by mechanism is the right call. And mechanism
**B has no rule at all**.

[Round] **A decision the round handed up, and the measurement makes it larger than its question.**
AC-4's instrument could not be committed: force-adding it red
`test_no_new_artefact_file_is_force_added_into_the_resolver_domain`, because the file spells
`ADR-0039/R2`, `ADR-0042/R6`, `CARD-296 AC-5`, `CARD-314 AC-3/AC-4` and more, and the check-ref
search is a **text** search. **That gate working, not failing.** The round un-tracked it
(`adaac606`) and the gate is green again. **The orchestrator's ruling: instruments stay in the
worktree and vanish with it; the findings live in the card record, which is what actually has to
survive.** Measured while deciding, and it is the uncomfortable part: **67 instruments under
`scratchpad/` are ALREADY tracked**, and they name test functions in bulk — `census-converted.txt`
alone spells **182**, `card329/mutate.py` 32, `card338/census_five_kinds.py` 21, `impact.txt` 27. The
gate never fired on them because, as its own docstring says, it is *"deny-by-default over the ignore
rules, not over the resolver's domain"* — so everything tracked **before** `scratchpad/` became
ignored is grandfathered and invisible. CARD-335 stopped the new pollution and the existing set
remains. **Not carded** under the cut bar: it is not blocking the vector slice, and the owner's
priority is finishing ADR-0042. Recorded here as the pointer.

[Round] **One full-suite red the round raised and explicitly declined to clear** — correctly, since
"I see no mechanism" is not a measurement: `tests/test_browser_fixture_scope.py::
TestBrowserFixtures_OrderIndependent::test_reverse_order_passes` passes file-scoped (31 passed, with
its own lock held, so the lock is not the cause) and reds only in the full suite. It spawns a **child
pytest**, so it is suite-interaction- or load-shaped. **Context the orchestrator added:** CARD-349's
gate ran an **armed** full suite hours earlier at **10402 passed / 0 failed**, so main was clean —
which makes this either this card's or a load artefact, and not a pre-existing red. **The merge gate
settles it on the merged tree**; it is not cleared here. The round's own suite was on `95c25cb6`,
before `adaac606`, so no suite yet describes the final commit.
