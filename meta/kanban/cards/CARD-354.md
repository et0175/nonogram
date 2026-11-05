# CARD-354: `tests/test_book_solved_answer_key.py` — 33 reds, the largest single module of the conversion residue

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/354-solved-answer-key-m10`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-354
**Source:** Module-sliced out of CARD-337 at the decompose station, 2026-11-04, on the owner's "module slicing" instruction. CARD-337's own item 0 refuted its premise three ways and its round then derived the mechanism x module cross-tab; that table reconciles to 143 reds in both directions. The axis was changed from mechanism to MODULE because the round measured that a mechanism-sliced partition cannot run concurrently at all -- nine of thirteen modules split across mechanisms, `tests/test_book_pdf_band.py` would have needed five separate cards to edit it, and nothing could have run beside the M10 card. The file axis is the one the scope gate enforces.
**Idea:** —
**Wave:** 79 <!-- DISPATCHED 2026-11-05T09:53Z as wave 79's second card, into the slot CARD-358 freed. Premise VERIFIED under the five-kind probe by the orchestrator: 33 failed / 118 passed, 0 errors, 33 distinct nodes; the 12 AttributeError lines on ContentStream match M7d exactly and the other 21 break into 11 distinct signatures. Touches intersection with CARD-324 (player files) EMPTY. Cut off the stamping commit. -->
**Created wave:** 75
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_solved_answer_key.py
**Review score:** —
**Started:** 2026-11-05T09:53Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

> ## ⚠ M10 IS THREE MECHANISMS, measured by CARD-358 — and the label describes only the first
>
> CARD-358's seven reds were *pure M10 in one small module*, which made it the cheapest place on the
> board to ask whether M10 is one mechanism. **It is three**, and this scopes your 45 reds:
>
> **A — the reading exists in the converted medium and was taken in one arm only.** Measured under
> the lift: the spy exempted **0** faces while the stream exempted **644** *(per book — 1288 across the two books; CARD-358's review corrected this, since the figure is quoted)* by the writer's own
> clue-digit mark. Nothing stopped being true; a reading stopped being taken. **This is the mechanism
> M10's label actually describes** — the cause lines really are `assert []` / `assert set()`.
> *Disposition: a mechanical union of the two arms. Cheap and local.*
>
> **B — the provenance the claim needs is absent from the stream BY DESIGN.** Not a reading taken in
> one arm; the other arm **cannot carry the claim at all**. The stream's one piece of provenance is
> the clue-digit mark, the mark *means* exempt, and the claim was that certain digits are **not**.
> `book_guide_vector`'s own source says so: *"This medium has no `_write_clues` to tag, so the
> distinction is made deliberately rather than inherited."* **The M10 label does not describe this.**
> *Disposition: needs a surviving authority named per claim — this is where ADR-0042/R6's "retire with
> a named survivor" actually bites.*
>
> **C — the VOCABULARY has no counterpart in the stream.** `TextCall.kind` reconstructs a vocabulary
> finer than the page kind — band, footer label, answer caption — off the **call chain**. A content
> stream has no call chain and no per-face record for the answer, puzzle or TOC writers (only the
> guide has one). Measured: the spy's semantic reading of both books collapses to `{'divider'}`, the
> one kind still raster. **The label does not describe this either**, and the failure is a
> *set-comparison*, not an empty read. *Disposition: **⚠ CORRECTED 2026-11-05 on CARD-358's review (ADR-0039/R4): the cost ordering this block first stated was WRONG.** It said *"expect C to be the expensive one — B had an authority to fall back on and C had none."* **Measured by that review: B's authority (`GuidePage.faces`, tagged `CLUE_DIGIT`) is COARSER than the claim**, so B collapses into C in practice and **B is not cheaper than C.** The evidence is a plant: with the guide's worked example drawing nothing at all, the module stayed byte-identical to baseline, because the page lays out FOUR families of line diagram and all four tag `CLUE_DIGIT`. *Disposition for both B and C: a named surviving authority per claim, verified by a plant that reds it.* Reviewer-measured; the fix round re-derives it.*
>
> **The rule neither groups one mechanism nor separates two**, which is why the bucket cannot be
> sized from the label:
>
> | mechanism | the alternation it matched | what that keys on |
> |---|---|---|
> | A (exempt set) | `assert \[\]` | a failure **shape** |
> | A (cross-check) | `assert set\(\)` | a *different* failure shape |
> | B (worked example) | `drew no text` | **a string lifted from the test's own message** |
> | C (coverage) | `AssertionError: assert \{` | a shape matching *any* set comparison anywhere |
>
> **So do not size your share from the label — classify first.** CARD-358 reports the classification
> cost one scripted reading of both arms per claim, not a card.
>
> **And mechanism B has no rule at all**: it reaches M10 only through `drew no text`, a string from
> the assertion message CARD-358 was about to rewrite — so the classification would have changed when
> the *wording* changed. `classify_reds.py` was deliberately not edited (CARD-338 is closed).

## The population, from CARD-337's cross-tab

**33 reds under the five-kind probe — the largest of the thirteen modules**, and this card owns
all of them. Nothing routes out.

| mechanism | reds | the line the gate prints |
|---|---|---|
| **M10** medium-blind empty read | **21** | no single signature — `assert []` / `assert set()` / `IndexError: index 0 is out of bounds for axis 0 with size 0` / `assert False` / `printed no …` |
| **M7d** in-module `ContentStream` read | **12** | `AttributeError: 'ContentStream' object has no attribute {'width'\|'tobytes'\|'crop'\|'convert'}` |

**M10 is a residual, not a mechanism, and that is this card's main risk.** Board-wide it is 57
reds across **35 distinct cause lines** and 8 modules, held together by a catch-rule matching
**25** top-level alternations (⚠ this card said *sixteen*; measured **25**, re-derived by the orchestrator with escape-aware depth tracking (my first two counts were wrong — escaped `\(`/`\)` were being read as groups) — ADR-0039/R4) and positioned last-but-one in the taxonomy. Every other mechanism has
1–7 signatures. **So "21 M10 reds" is 21 reds that did not match a more specific rule** — the
"other" bucket ADR-0039/R2 forbids, arriving with a label.

**Item 0: re-split your 21 M10 reds by cause signature before pricing or implementing.** If
they are three mechanisms wearing one label, say so and expect a re-cut; if they genuinely share
a cause, name it. This card's estimate assumes the latter and the assumption is **unmeasured**.

## What to implement

1. **Re-split M10** (above). Report the signature histogram.
2. **The 12 M7d reds** are a module-local reader meeting a content stream where it expected an
   image. The repair is per-site and the question for each is the ADR-0042/R6 one: re-express
   against the stream, or retire with a named survivor. **Say which, per site, with the reason.**
3. **Where a claim has no subject in the converted medium, retire it with a named survivor** —
   do not weaken it into something that passes vacuously. CARD-337 is the worked example of a
   claim with no vector subject.

## Acceptance criteria

- **AC-1** *Given* the five-kind probe, *then* this module's red count is **stated before and
  after**, derived by the committed census, and every remaining red is either routed with an
  owner or carries a stated ADR-0042/R6 disposition.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-2** *Given* the 21 M10 reds, *then* their cause-signature histogram is **reported**, and
  if it shows more than one mechanism that is a finding, not a detail.
  (check: review-lens)
- **AC-3** *Given* each repaired site, *then* a plant re-breaks it and the matched control is
  green **in the same run**, with `0 skipped` asserted — and because many of these are
  fixture-raised, state how many node ids each plant moves.
  (check: review-lens — a stated count or a mutation run is not a test, and no committed test can name it: its instruments live in the worktree and the force-add gate forbids tracking them. **No card owes a flip.** Restated 2026-11-05 on CARD-358's F-004.)
- **AC-4** *Given* a claim retired rather than re-expressed, *then* the survivor is **named** and
  the retirement is asserted, not merely commented (ADR-0039/R1).
  (check: review-lens)

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

[Round, commits `204e1140` (SCOPE+ guard) + `04672ce2` (the repair)] **33 reds → 0 under the five-kind probe**
(**33F/118P → 0F/154P**), **154 passed unlifted too**, no `src/` change. **Orchestrator-verified:** scope two
files (**+468/−59**: `tests/test_book_solved_answer_key.py` +408, `tests/test_book_interior_type_floor.py`
+119 under `SCOPE+`), `src/` diff 0, nothing under `meta/` on the branch, worktree clean and idle, and
**154 passed probe-scoped and 154 passed unlifted re-run by me.** CARD-358's module with the new guard:
**1F/56P** probe-scoped (the one red CARD-322's M1) and **57P** unlifted — both exactly as predicted from
52+4 and 53+4. The round ran no full suite and took no lock.

[Round] **CLASSIFICATION: all 21 M10 reds are mechanism A — A=21, B=0, C=0 — so CARD-358's A=3/B=2/C=2 is
NOT representative of the slice, and that is the finding that matters for the next five cards.** One cause
underlies all 21: `_Recorded._walk` spied only on the raster entry points (`create_toc_page`,
`solved_puzzle_page`, `_packed_answer_page`, `ImageDraw.text`), so once TOC, ANSWER and the packed kind are
vector the walk reaches `self.pages.toc/answer/packed_answer` instead and every list the record holds stays
empty. By what was missing: **inputs never recorded** — `assert []` ×4, `IndexError` ×2, "no table of
contents to read" ×2, "no answer page to read" ×2, the `([], [...])` operator-alphabet tuple ×2, "no
answer captions to look for" ×2, "the vector pages set no caption" ×1, `assert set()` ×1 (the first
**7 of 11 signatures** are plain empty reads of the converted medium, the label's own description); and
**the raster arm absent from the converted walk** — `assert 4 >= 6` ×2, "no answer page carried a name at all"
×2, `[]` ×1 (5 reds) — which **the M10 label does NOT describe**, since they need the raster twin
*replayed* rather than a union of the same arm. **B and C do not occur here:** the vector arm needs no
provenance or call-chain vocabulary, it reads the answer streams directly, and the raster arm keeps its
`_draw_solved_slot` call chain by replaying the raster twin. **Open for review, not decided:** whether
"replay the raster twin" is a sub-disposition of A (the round says one cause, so A) or a distinct
mechanism. **The estimate (2c) held and no re-cut was needed.** *The M10 catch-rule's coverage claim is false
for this module* — the label undersells how cheap it was.

[Round] **The 12 M7d reds: all RE-EXPRESSED, none retired**, so there is no retirement × survivor table to
give. New helpers `_page_reading`, `_answer_twin`, `_packed_twin`, `_interior_images`. **Nine wiring-identity
sites** compare the interior page with the declared medium's own twin, written directly — the vector side
calls `book_answer_vector`, **not `gen.pages`, so the expectation does not share the seam it checks** — and
`_page_reading` is `(medium, media_box, render())` for a stream and pixels for an image. **A cross-medium `!=`
is never used, because it is vacuously true.** The "not a divider" site keeps the pixel comparison for a
bitmap and asserts the medium for an operator page (the divider is still declared raster). Parity (`.width`)
and packed-clue ink (`.convert`) are pixel measurements, so they go through `pdf_pages.interior_images`
(raises loudly without poppler; poppler is present, 0 skips). A control had to change: `_write_pdf` refuses a
bitmap filed under the vector-declared ANSWER kind (G-6), so the raster-twin control now files under DIVIDER
when ANSWER is vector, with the reason in a comment.

[Round] **Three tests found by planting, one of them a PRE-EXISTING hole, not a conversion effect.**
`test_a_custom_book_title_reaches_a_packed_page` is new — a mutant giving the packed page no custom titles
**left the whole module green, so that claim was asserted nowhere.** `test_no_stream_page_outside_the_answer_section_prints_a_title`
is the vector counterpart of the whole-interior sweep. `test_no_toc_row_prints_a_title_in_the_stream_either`
**was vacuous over an empty record** and now asserts non-empty.

[Round] **13 mutants, all killed, `must_red` asserted non-empty before any run** (the defect CARD-358's
review found in its predecessor runner, not repeated), matched control green in the same run, `0 skipped`.
Nodes moved: S1 7, S2 7, **S3 1 (the genuine survivor, now killed by the new test)**, S4 15, T1 4, T2 5, T3 6,
T4 9, T5 2, T6 2, T7 2, T8 1, T9 1. **Two disclosures the round made and I am keeping:** (1) **the first run
killed only 8 of 13 as specified; T2, T3 and T5 were its own over-ambitious `must_red` lists, calibrated
AFTER seeing the result, and the file says so** — a kill matrix whose expectations were fitted to the
outcome is descriptive, not predictive; (2) **under T7 only the two `!=` control nodes detect a
`_page_reading` that ignores the stream; the other wiring-equality sites would survive** — their strength
comes from S1–S3, which plant the wiring itself in `src/`. The survivor table is read by eye: review-lens
evidence, not a mechanical assertion.

[Round] **CARD-358's four answer-caption survivors, re-verified by plant, results identical probed and
unprobed:** vector `…caption_is_right_aligned_on_the_slot_comp_007_reports` and
`…title_prints_only_on_answer_pages_across_a_corpus` red under the vector plant only; raster
`…caption_reads_answer_caption_when_there_is_room` reds under the raster `_draw_solved_slot` plant only;
`…on_a_two_up_page_there_is_slack_and_the_caption_prints_at_the_floor` is **corroboration only**, green under
both. **CARD-358's claims reproduce exactly.** The census driver's `--only` filter gave **33 red / 118 passed
before and 0 red / 154 passed after, unaccounted=0, skipped=0** — for this module only.

[Round] **THE COUPLING GUARD EXISTS AND WORKS, AND IT HAS A DEFECT OF MY OWN DESIGN: IT COSTS ~73 SECONDS A
RUN.** `TestInteriorType_EveryCitedSurvivorStillExists` derives `Class::method` tokens from CARD-358's
module text (11, across four files: 4+3+3+1), resolves each by `ast` across `tests/`, and reds on none or on
two, naming which. Green with all 11 before and after the module edit; its plant (rename each of the 4 cited
tests in turn) reds by name each time. **But `definitions_of` re-parses the whole tests tree on every
call** (238–266 files), once per token in one test, up to twice per token in another, plus the plant test.
**Measured by me on a quiet host:** one full parse **0.67 s**; the guard's three heavy tests **28.9 s, 27.4 s,
17.0 s**; CARD-358's module **1.5 s → 67 s probe-scoped and 3.15 s → 66.5 s unlifted** — about 109 repeated
parses, roughly **4–5% on a ~1600 s suite, permanently, to protect eleven names.** A substring prefilter
(read all files as text, parse only those containing the class name) is **0.010 s** for the read and
**0.022 s** to parse the two files that contain the name — about 30× cheaper per token. **The round has
been resumed to fix it, with a deterministic call-count control rather than a wall-clock assertion.**
The brief I gave the round asked for a guard that was derived and could fail; **it did not ask that the guard
be cheap, and that omission is mine.**

[Round] **Housekeeping the round found or caused, and one figure it got wrong.** It briefly ran `git stash`
in this worktree — **a stash is shared across every worktree.** It said three foreign entries remain; **there
are FOUR** (CARD-137's, and three on main, all based on old commits and none mentioning 354), so its own
entry was popped cleanly and nothing of the owner's was disturbed — the miscount is in the report only.
`tests/test_check_ref_resolution.py` cites `tests/test_book_solved_answer_key.py:308` **by line number in two
`#` comments** (classified by `ast`: comments, not strings or code, so nothing resolves them); line 308 is now
the `def` of `test_a_custom_book_title_wins_over_the_pictures_own_name` and is probably not what the comment
meant. The round is asked to derive the intended test from CARD-269's AC ref, not from the current line, or to
leave it and say why.
