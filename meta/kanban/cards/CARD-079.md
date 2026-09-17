# CARD-079: Threshold binarisation for silhouettes behind a switch, mid-tone classifier, corpus rendered both ways for the owner's eye

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false  _(revised 2026-09-17 at the owner's word — see Revision)_
**Skill:** python-pro
**TDD:** red -> green -> mutation check (4 mutants, all caught)
**Branch:** card/079-threshold-binarisation-gated
**Worktree:** ../PythonProject4-CARD-079
**Source:** meta/architecture/handoff.md#increment-12
**Idea:** —
**Wave:** 1
**Depends on:** ~~CARD-072~~ (released 2026-09-17 — see Revision), CARD-075 (done), CARD-076 (done)
**Touches:** src/nonogram/sourcing/image.py (binarize switch, MIDTONE_SHARE_THRESHOLD + band, classifier, module rationale rewrite), src/nonogram/orchestrator.py (Puzzle carries `binarisation`), tests/test_sourcing_image.py, tests/property/test_binarisation.py (new), meta/ops/binarisation_review.py (new — renders the corpus both ways), docs/GENERATION_ALGORITHM.md (§4.3 one row, §11), meta/architecture/decisions/adr/0006-*.md (History touch). _Export files dropped from this card — see Revision._
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-17
**Closed:** 2026-09-17
**Actual:** 1d
**Merge commit:** 97dc287
**Blocked by:** —

## Revision — 2026-09-17, at the owner's word ("open a card for CARD-079")

Three things had moved since the card was written on 2026-09-12. Two are
corrections of fact; one is the owner's decision.

**1. The corpus is on disk and tracked.** The card and ADR-0026 both say
`pictures/` is "currently not on disk — the owner's own trial folder". It is
tracked, 25 files, since `f3ba719`; CARD-096 swept it in full. The
skip-cleanly-when-absent behaviour stays (it is still the owner's folder and
still not restructured, G-7), but AC-127 and the gate render are live rather
than conditional. ADR-0026's Status line carries the same stale parenthetical
and is corrected with it.

**2. AC-127 must count regressions, not only gains** — CARD-096's
recommendation 3, verbatim: "Its AC-127 must now also count **regressions on
pictures dither already makes**, which its current text does not ask for." As
written, "more first-solve-unique and no more nudges" is a pair of totals, and
totals can improve while individual conversions that work today break. CARD-075
was accepted on exactly this shape — 18 rescued **and** 0 regressions, the
second half checked case by case — and AC-127 is amended to match. Its baseline
is also re-taken: the nudge counts it compares against must be the mask-driven
nudge's (CARD-075, merged `bb35762`), not the retired 2x2 ranking's.

**3. The export field is dropped from this card (owner's call).** Item 3 and
AC-B move to CARD-072, which touches the same metadata for `strategies`. The
reason is the card's own sequencing note — "one more version bump at most" —
which CARD-079 could not honour while CARD-072 was still open: CSV's decoder
rejects unknown keys, so each field costs a `SCHEMA_VERSION` bump and a pass
over every export test. The path taken is still recorded **on the `Puzzle`
aggregate** for image mode, which is what the gate render reads; only the
export half waits. **This releases the CARD-072 dependency** — nothing else in
this card needed it — so CARD-079 no longer waits on a card whose own item 1 is
blocked on the difficulty-rescoring ADR.

**4. Shape confirmed, not changed (owner's call).** The card ships both paths
behind `DEFAULT_BINARISATION`, default `dither`, and stops at the visual gate —
rather than CARD-096's measure-only shape with the threshold path living in a
`meta/ops` script. The owner chose the switch: a path that has been measured
belongs in the module, tested on both branches, with the flip a one-line
follow-up. G-1 is unchanged and binding — flipping the default is never this
card's commit.

**The review render** goes in `meta/ops/binarisation_review.py`, beside
`image_abandonment_sweep.py` and `nudge_ranking_contact_sheet.py`, rather than
in a new `tools/` directory the repository does not have. Same house style,
same JSON-plus-sheets output, and its numbers are directly comparable to the
two runs already taken.

## Why

Floyd-Steinberg dithering preserves average density, not contour: on a
silhouette it seeds isolated cells and ragged edges along the boundary —
exactly the one-cell runs and 2x2 switching blocks that make a nonogram
non-unique and that the nudge then repairs one cell at a time. ADR-0026
(DEC-032, **Proposed**) chooses an inclusive 50% ink-coverage threshold
after the LANCZOS resize for CON-013 silhouette input; ADR-0028 (DEC-033,
Accepted but inert until ADR-0026 is) recognises genuinely greyscale input
by the mid-tone share of the source histogram and keeps it on the dither
path. The hypothesis — more first-solve-unique conversions, fewer nudges —
is measured by AC-127, but the gate is the owner's eye on rendered grids
(memory: image-pipeline changes need a rendered-grid eyeball, not green
tests).

**The gate (FR-027 _meta.gate, binding):** this card ends when the
side-by-side render of every corpus picture is in front of the owner with
AC-127's two numbers per picture. Flipping ADR-0026 to Accepted and the
switch's default to threshold is the owner's action, not the card's. Until
then the default stays dither.

**Sequencing.** Last card of wave 2 and owner-gated. After CARD-075 (AC-127
counts nudges — the mask-driven nudge must be the one measured), after
CARD-076 and CARD-072 (export schema touched in order: guess value,
`strategies`, then `binarisation` — one more version bump at most). The
corpus `pictures/` is the owner's own trial folder and is not on disk at
the time of writing (memory: layout undecided, do not restructure) — the
render script and the AC-127 test skip cleanly when it is absent, like the
existing corpus tests in `tests/test_sourcing_image.py`.

## What to implement

1. **Named switch, both paths exist.** `sourcing/image.py`'s `binarize`
   gains a `BinarisationPath` (`threshold` | `dither`) selected by a
   module-level default (`DEFAULT_BINARISATION = "dither"` until the owner
   flips it) plus the classifier below; both paths are callable so the
   review render and AC-127 can run each explicitly. Threshold:
   `Image.point` at 128 on the resized "L" image producing mode "1" —
   ink coverage >= 50% fills (ADR-0026/R1; the AC-126 fixture pins the LUT
   cut-point against Pillow's LANCZOS rounding). Dither: today's
   `convert("1", dither=FLOYDSTEINBERG)`, unchanged.
2. **Mid-tone classifier (ADR-0028/R1).** On the "L" image
   `load_greyscale` returns — after EXIF transpose and alpha-onto-white,
   BEFORE trim/crop/resize — the share of pixels in the closed band
   `[64, 191]` (one `Image.histogram()` pass). Share >=
   `MIDTONE_SHARE_THRESHOLD` (provisional 0.10) -> genuinely greyscale ->
   dither; else silhouette -> threshold. Constants live beside
   `INK_THRESHOLD`. Pure function of the file: no rng, no request field,
   no per-upload override. **Calibration-owed:** record the mid-tone share
   of every corpus picture in Worktree notes so the owner can set the
   constant on data; do not tune it on this card.
3. **`binarisation` recorded on the aggregate, not inferred:** the path
   taken is set on the `Puzzle` for image mode; `None` for random and
   library, which have no binarisation to record. That is what the gate
   render reads. **The export half is deferred to CARD-072** (Revision 3):
   `binarisation: threshold | dither` in the JSON/CSV metadata, decided by
   ADR-0023/R2's own rule, in the same `SCHEMA_VERSION` change that carries
   `strategies` — one bump instead of two.
4. **Review render — `meta/ops/binarisation_review.py`** (Revision, not
   `tools/`: the repository has no such directory and two comparable
   scripts already live in `meta/ops`). Converts every picture under
   `pictures/` both ways at the batch's predicted extent (`derive_extent`,
   the CARD-061/064 presets) and writes, per picture, a side-by-side
   rendered grid (source, threshold, dither) plus AC-127's numbers
   (first-solve unique? nudges needed? made or abandoned?) — sheets into
   `~/Documents/nonogram-reviews/CARD-079/` (memory: renders never live
   beside the repo or inside it), a JSON row set beside them for the
   totals. Skips cleanly when `pictures/` is absent, as the corpus tests
   in `tests/test_sourcing_image.py` do — though it is present now
   (Revision 1).
5. **Docs and ADR touches:** the module rationale "dither before
   threshold, not instead of it" (`image.py:133-136`) is rewritten to
   describe both paths and the switch; `docs/GENERATION_ALGORITHM.md` §4.3
   step 8 row and §11; ADR-0006 History touch ("Pillow does the dithering"
   narrows to the greyscale path). FR-003's statement and AC-007's test
   name are re-worded **only after** the gate passes — not on this card
   (ADR-0026 Negative).
6. **Stop at the gate.** Put the review folder and the per-picture numbers
   in front of the owner (Worktree notes carry the folder path and the
   AC-127 totals). The card is done when that is in front of the owner;
   the owner's confirmation flips ADR-0026's Status and
   `DEFAULT_BINARISATION` in a follow-up commit that is theirs to ask for.

## Acceptance criteria

- **AC-124** — given a resized cell with 80% ink coverage (grey 51), when
  binarised under the threshold path, then the cell is filled.
  *test:* `TestBinarize_ThresholdFillsCellAtOrAboveHalfInkCoverage`
- **AC-125** — given 49% coverage, then the cell is empty.
  *test:* `TestBinarize_ThresholdLeavesCellEmptyBelowHalfInkCoverage`
- **AC-126** — given exactly 50% coverage, then the cell is filled (the
  boundary is inclusive).
  *test:* `TestBinarize_ExactlyHalfCoverageIsFilled` (ADR-0026/R1's check
  ref — goes live with this card)
- **AC-127** *(amended 2026-09-17 — Revision 2)* — given the corpus under
  `pictures/`, each converted by both paths, when the first-solve
  uniqueness verdicts, nudge counts and outcomes are compared, then
  (a) the threshold path's count of first-solve-unique conversions is >=
  the dither path's, (b) its total nudges is <= the dither path's, and
  (c) **every conversion the dither path makes, the threshold path also
  makes** — counted case by case, not as a total. Nudge counts are the
  mask-driven nudge's (CARD-075, `bb35762`), not the retired ranking's.
  **Where each clause is checked, and why they are split.** The suite test
  carries (a) at 25x25 and skips cleanly when `pictures/` is absent — ~7 s,
  disclosed in the test file, against a module that otherwise runs in under a
  second. Clauses (b) and (c) need both paths driven through
  `orchestrator.generate`, which costs ~32 s, ~30 s of it one picture
  (`butterfly.png`) running out the request deadline on the dither path; they
  live in `meta/ops/binarisation_review.py`, which sweeps five sizes instead
  of one and is where the owner's gate reads them anyway. Nothing is weakened
  by the split — (c) over five sizes is strictly more than (c) over one — but
  the suite does not pay 30 s per run for a deadline it already knows about.
  *test:* `TestBinarize_ThresholdCorpusNeedsNoMoreNudgesThanDither` (a);
  `meta/ops/binarisation_review.py` (b, c)
- **AC-A** (classifier) — a silhouette fixture (mid-tone share well below
  0.10) classifies `threshold`; a greyscale-gradient fixture (share well
  above) classifies `dither`; the classification is identical on repeated
  loads and reads the source image, not the resized one.
  *test:* `TestBinarize_ClassifierIsDeterministicAndReadsSourceHistogram`
- **AC-B** (recorded path) *(halved 2026-09-17 — Revision 3)* — an
  image-mode puzzle carries `binarisation` on the aggregate; random and
  library puzzles carry `None`. **The export half — the field in JSON and
  CSV, round-tripping EC-002 style — moves to CARD-072** and is not
  asserted here.
  *test:* `TestBinarize_RecordsBinarisationPathOnPuzzle`
- **AC-C** (default unchanged until the gate) — with the shipped default,
  every existing image-mode test in `tests/test_sourcing_image.py` and
  `tests/test_nudge.py` passes unchanged in assertion (the dither path is
  still what ships).
- **AC-D** (the gate, handoff checkpoint) — a side-by-side render of every
  corpus picture (threshold vs dither, at the batch's predicted extent) is
  in front of the owner with AC-127's two numbers per picture; Worktree
  notes record the folder, the totals and each picture's mid-tone share.

## Engineering constraints

- **EC(ADR-0028/R1)** — the path choice is a pure function of the decoded
  source image against `MIDTONE_SHARE_THRESHOLD`: same file, same path, on
  every load and every host; no rng, request field or override enters it.
  *test:* `PropertyTest_Binarize_ClassifierPureFunctionOfSourceImage`
  (seeded synthetic images: silhouettes with varying anti-alias width,
  gradients with varying mid-tone share)
- **EC(ADR-0026/R1, gated)** — under the threshold path, for any resized
  grey value g: filled iff g <= 127; never applied before the resize;
  never error diffusion.
  *test:* `PropertyTest_Binarize_ThresholdIsInclusiveHalfCoverageOnResizedImage`

## Guardrails

- G-1: The shipped default stays `dither` on this card; flipping
  `DEFAULT_BINARISATION` and ADR-0026's Status to Accepted is the owner's
  action after the visual gate — never this card's commit.
- G-2: Pipeline order unchanged (ADR-0022/R3): trim, ink-box aspect guard,
  centred crop, LANCZOS resize, THEN binarisation, then `to_grid`, then
  the orchestrator's uniqueness check and the FR-013 nudge. The classifier
  reads the source image before trim/crop/resize (ADR-0028).
- G-3: No new runtime dependency (ADR-0006/R1); Pillow primitives only.
- G-4: Image mode stays rng-free (ADR-0015); no request field or CLI/web
  option selects the path (ADR-0028 rejected `--binarize`).
- G-5: Stored image puzzles are never re-converted (Migration: on-touch).
- G-6: No edits under `src/nonogram/solver/`, `difficulty.py`; the nudge
  mechanism (CARD-075) and the recovery loop (CARD-074) untouched; the
  oracle and `tests/property/test_solver_uniqueness.py` untouched.
- G-7: Do not restructure or commit the owner's picture corpus
  (`pictures/`, `pic1/` — memory: experiments, layout undecided); the
  review folder is untracked output.
- G-8: FR-003's statement and AC-007's test name are not re-worded here
  (post-gate follow-up).
- G-9: Commit only your own files — explicit pathspecs.
- G-10 _(added by Revision 3)_: nothing under `src/nonogram/export/`
  changes on this card, and `SCHEMA_VERSION` is not bumped — the
  `binarisation` field is CARD-072's to add.

## System contract

- ADR-0026/R1 (GATED — intent under test until Status flips; review must
  not flag the shipped dither against it) — inclusive 50% ink-coverage
  threshold on the resized grey value, never before the resize, never
  error diffusion (check: TestBinarize_ExactlyHalfCoverageIsFilled)
- ADR-0028/R1 — path choice is a pure function of the source histogram
  against MIDTONE_SHARE_THRESHOLD; path recorded as `binarisation` (check:
  TestBinarize_RecordsBinarisationPathOnPuzzleAndExport)
- ADR-0022/R3 — trim, aspect guard, centred crop, resize order unchanged
  (check: tests/test_sourcing_image.py, tests/property/test_image_fit.py)
- ADR-0006/R1 — dependency baseline: stdlib + Pillow + NumPy (+ reportlab
  per CARD-057) — nothing new (check: review-lens)
- ADR-0023/R1, ADR-0023/R2 — _not exercised by this card since the export
  field moved to CARD-072 (Revision 3); the export surface is untouched
  here, which is itself the check._
- ADR-0015 — image mode draws nothing from the rng (check: review-lens)
- CON-013 — image sourcing scoped to high-contrast silhouettes; greyscale
  is tolerated via the dither path, not promoted to a mode (check:
  review-lens)
- ADR-0007 — no lateral imports (check: test_every_import_in_the_package_points_inward)

## Architecture context

- **FR:** FR-027 (AC-124..AC-127), FR-003 (amended; re-worded post-gate),
  FR-013 (nudge runs after either path)
- **CON:** CON-013
- **ADR:** ADR-0026 (Proposed, R1 gated), ADR-0028 (R1), ADR-0022,
  ADR-0006 (History touch), ADR-0023 (metadata field), ADR-0015
- **Decisions:** DEC-032 (gate), DEC-033
- **Components:** COMP-003 (sourcing/image), COMP-002 (aggregate field),
  COMP-007 (metadata)
- **Trace:** meta/architecture/trace.yml (FR-027 row)

**Checkpoint (handoff, verbatim):** A side-by-side render of every corpus
picture (threshold vs dither, at the batch's predicted extent) is in front
of the owner, with AC-127's two numbers per picture; the owner says which
path ships. Until then the default is unchanged (dither).
**Collapses:** FR-027, the "dither creates the ambiguity the nudge then
repairs" hypothesis, ADR-0028's mid-tone constant (calibrated on the corpus
rather than guessed), DEC-032's gate.
**Rollback:** On-touch: the switch default reverts to dither; stored image
puzzles are never re-converted.

## Worktree notes

### Delivered to the gate, 2026-09-17 — _decided the same day, see **The owner's decision** at the end_

**What shipped.** `sourcing/image.py` gained `THRESHOLD`/`DITHER`,
`MIDTONE_BAND`, `MIDTONE_SHARE_THRESHOLD`, `DEFAULT_BINARISATION`,
`midtone_share`, `classify_binarisation`, `binarisation_for`, and a `path=`
argument on `binarize`. `Puzzle.binarisation` records which path an image-mode
run took (`None` for random and library), resolved once per request beside the
extent and the deadline. **`DEFAULT_BINARISATION` is pinned to `dither`**
(G-1), and it carries three states — a path name, or `None` meaning "ask the
classifier", which is what the owner's flip sets.

**AC-127, all three clauses, over 25 pictures x sizes 10,15,20,25,30**
(`meta/ops/binarisation_review.py`):

| | threshold | dither |
|---|---:|---:|
| conversions made | **116** of 125 | 109 of 125 |
| uniquely solvable at the first solve | **99** | 80 |
| nudges spent | **36** | 53 |
| failed (abandoned or timed out) | **9** | 16 |

**(c) regressions — conversions dither makes and threshold does not: 0.**
Counted case by case, which is what the Revision amended the criterion to ask
for. The seven gains are `cat_Mouse` at 10/15/20/25, `duck2` at 30, `zebra` at
15 and 30.

**ADR-0028's owed calibration, taken.** Mid-tone share of all 25 pictures: 24
of them between **0.0021** (`duck.png`) and **0.0652** (`wolf_2.png`), and one
— `zebra.png`, the only photograph — at **0.1647**. Nothing between 0.066 and
0.164, so the provisional **0.10 sits in the middle of an empty gap** and any
value in roughly [0.07, 0.16] classifies this corpus identically. Left at 0.10.
Caveat: one picture on the dither side means the constant is calibrated against
a single positive example.

### The gate, and the thing the numbers hide

Sheets: `~/Documents/nonogram-reviews/CARD-079/`, one PNG per picture — source,
threshold grid, dither grid, at 25x25, each labelled with its outcome and nudge
count. Plus `binarisation_review.json`.

**The threshold path is dramatically better on silhouettes.**
`eagle-silhouette1.jpg` is the case the ADR was written for: threshold gives a
clean, solid, recognisable bird; dither gives a chequerboard. `konek.png` (a
seahorse) is cleaner under threshold too, though it costs 3 nudges where dither
needed 0 — a nudge count, not a fidelity loss.

**And it fails on line art, in a way AC-127 scores as a win.** A coverage
threshold keeps *filled areas*; line art has none, only thin strokes, so the
cut erases it. `cat_Mouse.png` converts to **two small blobs** (the cat's eyes)
on an otherwise empty 25x25 grid — and because an almost-empty grid is
uniquely solvable, it is *made*, and counts as four of the seven gains above.
Dither abandons it, which is the honest outcome.

The same mechanism has a worse form: a washed-out picture with no pixel below
`INK_THRESHOLD` (`ink_bounding_box` then falls back to the whole frame)
thresholds to a **wholly blank grid**, which is scored, marked
`ready_for_export` and exported. Dither refuses it. Pinned as
`test_the_threshold_path_turns_an_inkless_picture_into_a_blank_grid`, recorded
as finding 11 in `docs/GENERATION_ALGORITHM.md`, and written into ADR-0026's
History as **a precondition of accepting the ADR**.

So the trade the owner is being asked about is not "more conversions" — it is:

> the threshold path converts more pictures and converts silhouettes far
> better, at the cost of sometimes shipping a blank or near-blank page where
> the dither path refuses.

For a printed book the second is the worse failure, which is why this card
stops here rather than flipping anything. **What the flip should probably carry
with it:** refuse an all-empty or all-filled conversion, or fall back to the
dither path for one. That is a product decision adjacent to CARD-078 ("refuse
density 0 and 100") and is not invented here.

### Tests

**Full suite: 3,447 passed, 0 failed, 26 skipped**, with the two admin-markup
tests that already fail on `main` deselected.

Mutation check — four mutants, restored from a saved copy, never `git
checkout`: the inclusive cut moved off its boundary (caught by AC-126 and the
ADR-0026 property test), the classifier's two answers swapped (caught by AC-A
and the ADR-0028 property test), the shipped default flipped to threshold
(caught by 12 tests — G-1 is the best-guarded thing here), and the mid-tone
band made exclusive at the top (caught by the property test's re-derived
share). All four caught on the first pass.

`tests/test_sourcing_image.py` 129 (was 118): AC-124..AC-127, AC-A, AC-B, the
identity-resize premise guard, the shipped-default guardrail, the two-level
switch, and the blank-grid finding. New `tests/property/test_binarisation.py`
carries ADR-0026/R1 and ADR-0028/R1 over seeded synthetic silhouettes and
gradients. **AC-C holds: every pre-existing test in the module passes unchanged
in assertion** — the shipped path did not move.

AC-127's clause (a) is the suite's, at 25x25 (~7 s); clauses (b) and (c) are
`meta/ops/binarisation_review.py`'s, because driving both paths through
`orchestrator.generate` costs ~32 s of which ~30 s is `butterfly.png` running
out the request deadline on the dither path. The split is written into the AC.

### Guardrails

G-1 default unchanged and pinned by a test. G-2 pipeline order untouched; the
classifier reads the source before trim/crop/resize. G-3 no new dependency —
`Image.point`, a Pillow primitive (ADR-0006 History touch). G-4 image mode
still rng-free; no request field or CLI option selects the path. G-5 stored
puzzles never re-converted. G-6 nothing under `solver/` or `difficulty.py`;
the nudge and recovery loops untouched. G-7 `pictures/` read only; renders went
to `~/Documents/nonogram-reviews/CARD-079/`. G-8 FR-003 and AC-007 not
re-worded. G-9 explicit pathspecs. G-10 (Revision) nothing under
`src/nonogram/export/`; `SCHEMA_VERSION` unchanged.

### Also updated

`docs/GENERATION_ALGORITHM.md` §4.3 (step 7 and the two-path note), §10
(finding 11), §11; ADR-0026 Status corrected and two History entries;
ADR-0028 History with the calibration; ADR-0006 History scope note;
`meta/architecture/trace.yml` FR-027 row. `check_doc_references.py`: 227
resolved, 0 failed.

### The owner's decision — flip the default, add the blank-grid guard (2026-09-17)

Owner: "flip the default and add the blank-grid guard". G-1 ("never this card's
commit") is superseded by that instruction: the flip is on this card's branch
at the owner's word, which is the follow-up G-1 reserved for them.

**The flip.** `DEFAULT_BINARISATION = None` — the classifier chooses per
picture. ADR-0026 is **Accepted** (conditional on the guard, recorded in its
History); ADR-0028 is live.

**The guard, and two choices made in building it** — both stated because the
instruction named the guard, not its shape:

1. **Fall back to dither, not refuse.** A threshold conversion outside
   `USABLE_INK_SHARE` is redone on the dither path. Dither is what every
   picture got before the flip, so a fallback can never turn a picture the
   tool used to convert into an error; a refusal could. It also needs no new
   error type, exit code or message. On the two live cases the outcome is
   identical anyway — the dither path abandons both, as it always did. A
   degenerate *dither* conversion stands: there is nothing to fall back to.
2. **The floor is 5%, not 10%.** The corpus gap is wide (line art at
   1.0–2.7%, the next conversion at 18.0%), and 10% was my first cut. A test
   caught it: `tests/fixtures/landscape.png`, a thin horizon — sparse but a
   real picture — converts at **9.0%**, and a 10% floor sent it to dither for
   no reason. 5% sits in the narrower gap [2.7%, 9.0%]. The ceiling mirrors it
   at 95% and nothing on hand triggers it (densest conversion 82.0%).

**A design flaw found and fixed while doing it.** `binarize(path=None)` used to
resolve the default itself, but the guard lives one level up in the new
`convert`, so any caller of `binarize` got an *unguarded* conversion while
`generate` got a guarded one — two answers to "what does this picture convert
to". FR-022's trim tests were such callers and showed a false regression (worst
blank edge 11). `path` is now **required** on `binarize`, and `convert` is the
only place a path is chosen. `binarisation_for` now takes the extent and
converts to answer, because the guard makes the path depend on the result —
~4 ms a picture, against a solve of tens to thousands of ms.

**AC-127, re-worded to what the decision rests on — shipped vs dither
everywhere** (comparing the raw paths credited the threshold with pictures the
guard sends back). 25 pictures × sizes 10,15,20,25,30:

| | shipped | dither everywhere |
|---|---:|---:|
| conversions made | **110** of 125 | 109 |
| unique at the first solve | **91** | 80 |
| nudges spent | **39** | 53 |
| **(c) dither makes, shipped loses** | **0** | — |

107 of the 110 took the threshold path, 3 took dither. The one gain is
`duck2.png` at 30. At 25×25 alone (the suite's clause (a)): **17 against 16**.

So the honest size of the win: **one extra conversion in 125**, **11 more
unique first time**, **14 fewer pixels of owners' pictures changed**, and
silhouettes that look like silhouettes. Raw threshold's "116 made" was
inflated by `cat_Mouse`'s four blank-page "gains" and by `zebra`, which the
classifier correctly keeps on dither. The re-rendered sheets (same folder,
columns now *shipped* and *dither*) show `cat_Mouse` refused on both.

**Pins the flip moved — all re-measured, each recorded where it lives:**

| where | was | now | why |
|---|---|---|---|
| FR-022 AC-086 (requirements.yml + test) | 17 of 19 fixed, 2 residual, 23/25 | **16, 3, 22/25** | `duck2.png` thresholds and gains one blank line at its right edge |
| FR-022 AC-089 | near-white 6 vs mid-grey 2 | **7 vs 3** | the same picture, both sides; the gap the criterion is about holds |
| FR-022 AC-088 `dear1.jpg` edges | [0,0,0,2] | [0,0,1,2] | deepest edge unchanged at 2 |
| FR-022 AC-091 `wolf1.jpeg` | before == after | deepest 3 both sides | trim now takes one line off an edge that was never the problem |
| AC-127(a) at 25×25 | raw 19 vs 16 | **shipped 17 vs 16** | re-worded to shipped vs dither |

The AC-086 test keeps its `17_of_the_19` function name — it is the pytest
spelling of the trace id, and ids stay stable across an amendment.

**New criterion:** FR-027 **AC-173** (checked free; AC-172 is CARD-075's) —
a threshold conversion outside 5%..95% ink is redone on the dither path and
no near-empty threshold grid is scored or exported. Tests
`test_binarize_guard_sends_degenerate_threshold_conversion_to_dither_*`: the
washed-out picture, `cat_Mouse` at 25 (skips without the corpus),
`landscape.png` left alone, and a degenerate dither conversion left standing.

**Also updated:** FR-027 in requirements.yml (decision recorded, gap resolved,
AC-127 re-worded, AC-173 added); trace FR-027 → `done`;
`docs/GENERATION_ALGORITHM.md` §4.3 rewritten for what ships, finding 11
closed, §11 row; ADR-0026 Accepted; ADR-0028 History (live; and the recorded
path can differ from the classifier's choice when the guard fires); ADR-0006
and ADR-0028 History entries put back in oldest-first order. The review script
gained `--from-rows`, because its report crashed after a 25-minute sweep on a
variable my own edit left behind, and re-reporting from the saved rows beat
re-running it.

### After the flip — what else moved, and the suite

**Pins outside FR-022 that the flip moved** (all re-measured, each recorded in
its own docstring):

| pin | was | now | why |
|---|---|---|---|
| `test_nudge.py` real-image recovery | `owl1.png` 10x10, 1 nudge | **`bird2.jpg` 14x14**, 1 nudge | `owl1.png` now takes the threshold path and converts at *every* size 10..30, so it has no cap case left; the pair moved together to keep one photograph doing both jobs |
| `test_nudge.py` real-image cap + its CLI end | `owl1.png` 24x24 | **`bird2.jpg` 16x16** | made at 14x14 and 15x15, abandoned at 16x16, made again at 17x17 — the extent is plainly the only variable |
| `test_nudge_reporting.py` AC-040 plural line | `owl1.png` 15x15, 2 nudges | **20x20**, 2 nudges | a fresh 10..30 sweep puts 2 at 19, 20, 24, 27 |
| `property/test_grid_dimensions.py` decode count | bare 2, explicit 1 | **bare 3, explicit 2** | `binarisation_for` decodes once per request; renamed `..._exactly_three_times` |
| `test_nudge.py` API-surface pin | 12 names | 24 names | the binarisation vocabulary |

A fixture sweep over 10..30 found eight fixtures that still reach the cap, so
the cap case is not scarce — `bird2.jpg` was chosen for the adjacent-size
contrast, not for being the only one.

**A second design leak, found by a test.** The orchestrator asked
`binarisation_for` for *every* image-mode run, including runs whose grid comes
from a scripted source — so it opened the uploaded file through a channel the
source never used, and `tests/test_naming.py`'s image-stem test (which uploads
an empty placeholder `cat.png`) failed with `UnreadableImage`. The field
records which path *a conversion* took, and a grid no conversion produced has
none, so it is now recorded only when the real image module is the source in
use. Pinned by `test_a_grid_no_conversion_produced_records_no_binarisation`.

**Mutation check on the flip and the guard** — four more mutants, restored from
a saved copy: guard removed (8 failures), guard applied to the dither path too
(**survived** — re-dithering a dither grid returns the same grid, so it was
invisible in the result; the test now counts conversions and catches it), floor
raised back to 10% (caught by the `landscape.png` case), flip reverted (9
failures).

**Full suite: 3,451 passed, 0 failed, 26 skipped.** `check_doc_references.py`:
230 resolved, 0 failed.

**One environmental note for the owner, not a card issue.** A local PostgreSQL
18 is now listening on 5432. The suite's DB tests skip when Postgres is
unreachable and had skipped all day; with it up, the full run hangs in
`tests/test_admin_regrade.py` (10+ minutes, one leaked connection, ~1 s of CPU).
That file passes in about a second on its own on **both** `main` and this
branch, and the full suite completes normally in 97 s once Postgres is
unreachable again — so it is an inter-test interaction that the running server
exposes, present on `main`, and nothing to do with this card. It is worth its
own card.

