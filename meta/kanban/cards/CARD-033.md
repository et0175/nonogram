# CARD-033: A bare `--size N` derives the shorter side from the source's shape

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/033-bare-size-derives-shorter-side
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-7
**Idea:** —
**Wave:** 20
**Depends on:** CARD-027
**Touches:** src/nonogram/orchestrator.py, src/nonogram/sourcing/image.py, src/nonogram/sourcing/library.py, tests/test_orchestrator.py, tests/test_sourcing_image.py, tests/property/test_grid_dimensions.py
**Review score:** 9.0 (cycle 2; cycle 1 7.5)
**Started:** 2026-09-02T13:30:00Z
**Closed:** 2026-09-02T14:05:00Z
**Actual:** 0.1d
**Merge commit:** 0d215d24552392b091d924581a8f7536df29ea2d
**Blocked by:** —

## What to implement

`--size 30x20` keeps meaning exactly 30 by 20 — untouched by this card. A **bare**
`--size 30` sets the grid's LONGER side to 30 and derives the other from the
source's own shape: `round(N * short/long)` over image mode's ink bounding box
(FR-022), library mode's template ratio, and — for random, which has no shape of
its own — a square.

**Clamp at the bottom only, never at the top.** `N <= MAX_SIZE` already keeps both
sides in range, and that is precisely why "longer side" is the correct reading of
a bare N: a top clamp would crop content, the harm this line of work exists to
prevent. Do not add one "for safety" — its presence would be a bug, not a belt.

**The refusal is the interesting half.** Because of the bottom clamp the grid
stops tracking the source at `N:10`, so a source more elongated than `N/5 : 1`
cannot be reached by that N — 2:1 at `--size 10`, 4:1 at `--size 20`, 6:1 at
`--size 30`. That is exact arithmetic, not a sampled figure. Rather than silently
clamp, refuse — **and name the smallest `--size N` that would take the source
unclamped.** FR-021's existing message tells the user to crop the picture
themselves; that is the wrong remedy here and must not be reused verbatim, because
cropping is not what fixes it.

**Counter-intuitive consequence to preserve rather than smooth over:** asking for
a SMALLER puzzle refuses pictures a larger one accepts. It is stated in FR-023 and
belongs in the message, not hidden.

## Acceptance criteria

- **AC-092** (happy) — test: `TestDeriveShape_ImageBareSizeDerivesFromInkBoundingBoxRatio`
  - **given** eagle-silhouette1.jpg (563x980, ratio 0.574) and a bare `--size 25` request
  - **when** the request is parsed and fitted
  - **then** the derived grid is 14 wide by 25 tall (round(25 * 563/980) = 14), retaining ~97% of the source under FR-020's crop, versus ~57% for the previous 25x25 square reading
- **AC-093** (boundary) — test: `TestDeriveShape_CorpusMeanRetentionRisesTo99Percent`
  - **given** the 25-image corpus committed under pictures/, each fitted at a bare `--size 25`
  - **when** each picture's derived shape is compared against the previous 25x25 square reading
  - **then** mean retained content rises from 76% (square) to 99% (derived), and the count of pictures retaining under 90% falls from 20 of 25 to 0
- **AC-094** (boundary) — test: `TestDeriveShape_LibraryTemplateRatioAppliesSquareToday`
  - **given** the built-in library key "cat" (a 16x16 square template) and a bare `--size 25` request
  - **when** the request is parsed
  - **then** the derived grid is 25x25, because the template's own ratio is 1:1 today
- **AC-095** (happy) — test: `TestDeriveShape_RandomSourceStaysSquare`
  - **given** a random-mode request with a bare `--size 20`
  - **when** the request is parsed
  - **then** the derived grid is 20x20, since a random source has no shape of its own
- **AC-096** (boundary) — test: `TestDeriveShape_ExplicitNxMBypassesDerivation`
  - **given** an explicit `--size 15x30` request
  - **when** the request is parsed
  - **then** the grid is exactly 15 wide by 30 tall as given, and the derivation rule does not apply
- **AC-097** (boundary) — test: `TestDeriveShape_WidestAcceptedRatioIsExactlyNOverFiveToOne`
  - **given** three bare-size requests, `--size 10`, `--size 20`, `--size 30`, each paired with a source whose long:short ratio is exactly N/5 (2:1, 4:1, 6:1 respectively)
  - **when** each request is parsed and fitted
  - **then** each derives a grid whose short side lands exactly on MIN_SIZE (10) — the bottom clamp reached exactly at the boundary, not short of it — and is accepted, not refused
- **AC-098** (negative) — test: `TestDeriveShape_RefusesBeyondCeilingNamingSmallestWorkingSize`
  - **given** a source image with long:short ratio 5:1 and a bare `--size 15` request (ceiling at N=15 is 15/5 = 3:1)
  - **when** the request is parsed
  - **then** the request is refused, and the error states the picture needs `--size 25` or larger rather than telling the user to crop it themselves

## Engineering constraints

- **EC-009** (verbatim, kind: consistency) — For any bare `--size N` with N in 10..30 and any source aspect ratio r = short/long (0 < r <= 1), in every source mode: the derived long side always equals N (never clamped above MAX_SIZE); the derived short side equals round(N * r) whenever that value is >= MIN_SIZE (10); and whenever round(N * r) would fall below MIN_SIZE — equivalently, whenever the source's long:short ratio exceeds N/5 — the request is refused rather than silently clamped, with the refusal naming the smallest N for which round(N * r) >= MIN_SIZE. This holds for every N and every source ratio, not only the measured examples.
  test: `PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused`

## Guardrails

- G-1: `--size NxM` behaviour is unchanged — both sides still specified directly
  (test: the FR-018 criteria CARD-027 landed)
- G-2: Random mode still produces N x N for a bare N; library mode does too while
  all four registered templates are 16x16. Neither is special-cased — both fall
  out of "the source's own shape", and a rectangular template later must work
  without further change.
- G-3: No clamp at the top. The derived side is `<= N` by construction; adding an
  upper clamp would mask a defect rather than prevent one.
- G-4: FR-021/CON-012's >2x guard keeps its meaning and its ink-box subject
  (ADR-0022/R3, revised earlier the same day). This card changes which grid shape
  is requested, never how the guard judges one.
- G-5: Do not edit `src/nonogram/export/**` — page orientation and the cell-size
  rule are CARD-034's this wave.
- ~~G-6: Do not edit `src/nonogram/cli.py` — `--size` PARSING is CARD-027's and is
  already done; this card works inward of the CLI, per ADR-0010.~~
  **SUPERSEDED 2026-09-02 (cycle-1 review, finding F-003) — not breached by
  oversight.** `cli._extent_token("30")` returns `(30, None)` instead of
  `(30, 30)`; the `--help` text and three docstrings follow it. Three reasons,
  each checked rather than asserted:
  - **Necessary.** With `(30, 30)` a bare N is indistinguishable from an explicit
    `--size 30x30`, so the only discriminator left inward of the adapter is
    `width == height` — which would silently reshape `--size 25x25` on a portrait
    picture into 18x25. FR-023 forbids exactly that ("an explicit `--size NxM`
    ... is unaffected by this derivation"), and AC-096 is its criterion.
  - **Sound on G-6's own authority.** ADR-0010 puts *domain defaults* inward of
    the CLI, and squaring an unstated dimension WAS a domain default — a shape
    claim about the user's picture. Removing it moves the line in the direction
    G-6 invokes. Parsing itself is untouched: the grammar, the `x` separator, the
    `int()` conversion and the range-free posture all stand.
  - **Anticipated by the model.** `meta/architecture/trace.yml:776` lists FR-023's
    components as `[COMP-001, COMP-008, COMP-002, COMP-003]`, and COMP-001 is the
    CLI adapter — so G-6 contradicted the trace row of the requirement it was cut
    for. The guardrail template, not this card, is what was wrong.

  Filed as an intake line in `meta/architecture/inputs/raw-requirements.md`
  (last entry, 2026-09-02) so the decompose station stops emitting a G-6 of this
  shape for the next FR whose trace lists COMP-001. The full argument and the
  measured footprint are in `## Worktree notes` below.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never en... (check: TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by m... (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the othe... (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness... (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate... (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-lo... (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both ... (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded fil... (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (US-005, FR-011). (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library mode, resample attempts for difficulty matching, or pixel-nudge attempts for image mode) never ex... (check: TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in every source mode and at every point in its regenerate/resample/nudge lifecycle (US-016, CON-011... (check: TestGenerateRandom_AcceptsMaxSide30, TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)

## Architecture context

- **FR:** FR-023, FR-018 (the pair this builds on), FR-021 (its guard, unchanged)
- **NFR:** —
- **CON:** CON-011, CON-012
- **ADR:** ADR-0022 (revised twice 2026-09-01; R4 is this card's rule), ADR-0010
- **Components:** COMP-002, COMP-003
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

## Worktree notes

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Dependency gate]** CARD-027 `done` (merge 632fd18).
- **[Drift gate]** ⚠ warn, dismissed for the FOURTH consecutive card — the flagged events
  name this project's own commits. Filed to the backlog already; not repeated here.
- **[AC figures verified BEFORE the agent started]** Both measurable ACs were re-derived
  against today's tree, because CARD-030 changed what "the source's ratio" means and the
  card predates its merge:
  - AC-092: `eagle-silhouette1.jpg` is 563x980 **and its ink box is also 563x980** — the
    picture is ink-tight, so the file reading and the ink-box reading coincide and the
    stated 0.574 / 14x25 is unambiguous. Confirmed `round(25 * 563/980) = 14` both ways.
  - AC-093: mean retention 76% -> 99% and "20 of 25 under 90% -> 0" reproduce **exactly**,
    but only against the INK-BOX ratio. Against the raw file ratio the same corpus gives
    91% and 7 of 25. So the card's figures already assume CARD-030's trim, which is the
    correct baseline; a reader who re-derived them from file extents would wrongly
    conclude the card was stale.
- **[Why this card matters more than its estimate suggests]** It closes a real regression
  the owner hit on 2026-09-02: `silhouette/animals/ania/cat1.jpg` at `--size 25` loses the
  cat's ears, because CARD-030's trim turned a square file into a portrait drawing and the
  square grid then centre-cropped 28.6% off top and bottom. The corpus measurement above
  is that same defect at scale — 20 of 25 pictures currently retain under 90%. Verified
  that an explicit `--size 18x25` on that cat discards 0.9% and keeps the ears, which is
  the shape this card's rule derives automatically.

### Implementation (2026-09-02, agent)

**Where the derivation lives.** Two pure domain functions in
`sourcing/random_grid.py` next to `validate_extent` — the module that is already
"the single normative statement" of the extent rules, with `library` and `image`
delegating rather than restating (ADR-0022/R2's precedent):

* `derive_extent(width, height, source_width, source_height)` — the rule. Takes
  the **half-stated pair**, never a scalar `N`, so no public signature reduces
  extent to one number (ADR-0022/R1). Delegates the range rule to
  `validate_extent`; adds no second message format.
* `source_shape()` per mode — `random_grid.source_shape() -> (1, 1)`,
  `library.source_shape(key) -> template extent`, `image.source_shape(path) ->
  ink-box extent` — dispatched by a **second per-mode table**,
  `sourcing.shape_for_mode`, mirroring `sourcing.for_mode`. Random's square is a
  row in that table, not a branch in the derivation (**G-2**), and a rectangular
  template added later works with no further change (asserted:
  `derive_extent(25, None, 32, 16) == (25, 12)`).

`orchestrator._resolved_extent` composes them and is the only caller; the
resolved pair is carried on `Puzzle.extent` (new field) so exports record the
grid that was produced, and `_source_arguments` now **takes** the extent instead
of reading the request's — a half-stated request has no pair to read.

**THE RULE THE ACs ACTUALLY DESCRIBE — and one requirement wording that is
wrong.** EC-009 says the refusal fires "whenever `round(N * r)` would fall below
MIN_SIZE — *equivalently*, whenever long:short exceeds N/5". Those are not the
same boundary: `round(N*r) < 10` is `N/9.5`, not `N/5`. Only the `N/5` reading
satisfies AC-097 *and* AC-098 (its "--size 25" for a 5:1 source is `5*long/short`
exactly; the smallest N leaving that side *unclamped* is 48, past MAX_SIZE and
unofferable). So the implemented rule — the one both criteria and ADR-0022/R4's
own wording describe — is:

> derive `round(N * short/long)`, **apply** the MIN_SIZE floor, and refuse when
> the resulting grid would discard more than half the source.

That last clause is FR-021/CON-012's own criterion applied to the shape the
derivation *requests*, which is exactly where the ADR's "combined with the >2x
rule this yields an exact ceiling" comes from, and it lands the ceiling on
`N/5 : 1` — 2:1 / 4:1 / 6:1 — to the pixel. **G-4 holds in the strongest form:
the guard's meaning, subject and message are untouched; the derivation just
declines to request a shape the guard would refuse, and says something more
useful when it does.** Intake line filed in `inputs/raw-requirements.md`
(requirements.yml is not hand-edited).

**Measured, all reproduced exactly** (worktree, `pictures/`):

| claim | card says | measured |
| --- | --- | --- |
| eagle file / ink box | 563x980, ink-tight | 563x980 / 563x980 |
| eagle derived at N=25 | 14x25 | 14x25 |
| eagle retained, derived vs square | ~97% / ~57% | 97.3% / 57.5% |
| corpus mean retained, square -> derived | 76% -> 99% | 76.13% -> 98.57% |
| corpus pictures under 90% | 20 of 25 -> 0 | 20 -> 0 |
| ceiling at N = 10 / 20 / 30 | 2:1 / 4:1 / 6:1 | exact, both orientations |
| 5:1 source, smallest workable N | 25 | 25 (24 refused) |

Retention is measured by **pixel area of `fit_crop_box`'s rectangle**, not by
the ratio formula the guard uses — an independent second implementation, per
CLAUDE.md's test policy. Both agree to within the crop box's integer flooring.

**The cat.** `pictures/cat.jpg` is byte-identical (md5 `21d2fab9…`) to the
owner's `silhouette/animals/ania/cat1.jpg`: 580x580 file, 330x462 ink box.
Rendered to ASCII, top row only:

```
square 25x25 (before)   .......################..     one slab — ears cropped off
derived 18x25 (after)   ....##.........##.            two peaks — the ears
```

Pinned as `test_the_cats_ears_survive_a_bare_size_25` by run-length encoding the
top row: 2 runs derived, 1 run square. Retention 99% vs 71%.

**Tests.** `tests/test_derive_shape.py` (new, AC-092..AC-098 + the cat + the
"no supported size" refusal arm), two property tests appended to
`tests/property/test_grid_dimensions.py`
(`PropertyTest_DeriveShape_ShortSideIsRoundedRatioClampedAtMinOrRefused` over
21 N x 480 ratios x 2 orientations with a `Fraction` oracle;
`PropertyTest_BareSize_DerivesShorterSideFromSourceShape` end to end through all
three modes). One `_GUARD_SHAPES` row added: `derive_extent(n: int, ...)` must be
flagged — the signature FR-023 invites and this card deliberately did not write.

**AC-063's test changed, as CARD-027's own docstring predicted.** A bare
`--size 30` now reaches the domain as `width=30, height=None`. It has to: the
CLI cannot tell `(30, 30)` from an explicit `--size 30x30`, which AC-096
requires be left alone, so FR-023 is unimplementable without the distinction
surviving the adapter. Amendment filed as an intake line, not hand-edited.

**G-6 IS BROKEN, deliberately, and this is the disclosure.** `cli.py` is edited:
`_extent_token("30")` returns `(30, None)` instead of `(30, 30)` (plus the
`--help` text and three docstrings). No *parsing* changed — the grammar, the
separator, the `int()` conversion and the range-free posture are untouched.
What was removed is a **domain default wearing parsing's clothes**: choosing the
unstated dimension is a rule about puzzles whose answer depends on the source,
which is precisely what ADR-0010 puts inward and what G-6's own sentence ("work
inward of the CLI, per ADR-0010") asks for. trace.yml lists COMP-001 among
FR-023's components, so the architecture already expected the adapter to
participate. There is no alternative: with `(30, 30)` the domain cannot
distinguish a bare N, and deriving on `width == height` would silently reshape an
explicit `--size 25x25`, which FR-023 forbids in as many words.

**Other footprint beyond the card's prediction, all disclosed:**

| file | why |
| --- | --- |
| `src/nonogram/cli.py` | above (G-6) |
| `src/nonogram/errors.py` | `SizeTooSmallForSource(SizeOutOfRange)`. Subclassing means **no `cli._EXIT_CODES` row is needed** — `exit_code_for`'s MRO walk finds INVALID_INPUT — and it is honest: the requested *size* is what is wrong, and a larger one works. Not a subclass of `ImageNeedsManualCrop`, whose name asserts the remedy this message denies. |
| `src/nonogram/sourcing/random_grid.py` | the rule + random's shape (G-2 forbids special-casing random, so it needs a shape reporter) |
| `src/nonogram/sourcing/__init__.py` | the `shape_for_mode` dispatch table |
| `tests/test_derive_shape.py` | new; all seven `TestDeriveShape_*` names in one file |
| `tests/test_nudge.py` | `image.__all__` pin; two pinned image runs re-stated as `--size 22x22` / `10x10` (a bare N would now derive a different grid and stop being the pinned conversion) |
| `tests/test_resample.py`, `tests/test_sourcing_library.py` | `_source_arguments` signature; a bare-token request expectation |
| `README.md` | the `--size` section documented the old meaning; the image-conversion table was measured on square grids and was re-measured |
| `meta/architecture/inputs/raw-requirements.md` | the two amendments above |

`src/nonogram/export/**` untouched (**G-5**). `--size NxM` untouched (**G-1**):
AC-062/AC-063/AC-064/AC-065 and every FR-018 criterion green, and AC-096 pins
that an explicit extent never even consults the source (asserted by making the
shape reporter raise).

**One behaviour change worth naming:** an out-of-range extent is now refused
while the extent is resolved, so the source is called **zero** times instead of
once. Same error, same shared validator, same message; strictly cheaper, and it
is what keeps "an out-of-range request pays for nothing" true now that a bare
size otherwise decodes the file. Two tests that asserted `calls == 1` were
re-pointed at an invalid *density*, which is still the source's to refuse, so
they keep asserting what they were written to assert.

**Known cost, accepted rather than hidden:** a bare-`--size` image run decodes
the file **twice** — once for the ink box, once for the pixels. An explicit
`--size WxH` still decodes once, because it never asks for a shape. Handing a
decoded `Image` back out would put a Pillow object on a boundary that carries
`list[list[bool]]` and nothing else (ADR-0012).

**Mutation testing** (each mutation applied to `random_grid.py` alone, full
suite run, then reverted; md5 `5403445c86d13d3d04df41343ffdf1f3` before and
after, `git diff --stat` unchanged):

| mutation | result |
| --- | --- |
| (a) `derived = stated` — ignore the source's shape | **9 tests fail** (both property tests, 7 in `test_derive_shape.py` incl. the cat) |
| (b) return the clamped extent instead of refusing | **7 tests fail** (both property tests, all three AC-097 cases, both refusal tests) |
| (c) add a top clamp (`stated = min(stated, MAX_SIZE - 5)`) | **3 tests fail** (both property tests, AC-097 at N=30) |

Note on (c): the *natural* top clamp — `min(MAX_SIZE, derived)` — is a literal
no-op, since `derived <= stated <= MAX_SIZE` by construction. That is G-3's point
made mechanical: a top clamp is unreachable, so its presence could only ever
mask a defect. The mutation used is the reachable variant.

**Suite: 1494 passed, 1 xfailed** (baseline 1476 + 1 xfailed; +18 = 11 in
`test_derive_shape.py`, +4 property/precondition tests, +2 shape-dispatch guards
in `test_sourcing_image.py`, +1 `ERROR_EXIT_CODES` row).

Not done, and left to the closing pass: `trace.yml`'s FR-023 entry still reads
`status: partial` with the note "no kanban card cut for it".

### Cycle-1 review fixes (2026-09-02, forge:fix)

Score 7.5, gate failed on two Important findings. The reviewer's verdict was that
the **implementation is correct** — it re-derived the arithmetic and found the
requirement, not the code, was wrong — so no code logic changed. One test was
added, one comment and three docstrings corrected, and the bookkeeping the code
had outgrown was filed.

**F-001 (Important, INV-004) — the resolved extent reaching the aggregate is now
pinned.** `Puzzle.width`/`Puzzle.height` read `extent` and fall back to the
request; mutant m6 (`Puzzle.width` returning `self.request.width`
unconditionally) survived the whole suite, because `puzzle.extent` was asserted
exactly once and only in random mode, where the requested and resolved pairs
coincide. Nothing read the *properties*, or an exported document, for a
half-stated request on a non-square source — the only shape where they disagree.
New: `test_a_derived_extent_is_what_the_aggregate_and_the_document_record` in
`tests/test_export_json.py` (the co-change peer the reviewer named), parametrized
over `tests/fixtures/portrait.png` (40x60 -> 20x30) and `landscape.png`
(60x40 -> 30x20), so both accessors are exercised. It asserts the request really
is `(30, None)`, then `(puzzle.width, puzzle.height)`, then the exported
document's `request` block, then that the document's own `grid` has exactly those
row and column counts — agreement between the file's two statements of one fact,
which is what FR-012 promises. Real pipeline, ~10ms per case.

Mutation proof (each applied, run, reverted; `orchestrator.py` md5 identical
before and after, `git diff --stat` unchanged):

| mutation | before | after |
| --- | --- | --- |
| m6 `Puzzle.width` -> `self.request.width` | full suite green | **fails**, `(30, 30) == (20, 30)` |
| m6h `Puzzle.height` -> `self.request.height` | full suite green | **fails**, `None != 20` |

**F-003 (Important) — G-6 marked SUPERSEDED on the card** (`## Guardrails`), with
the necessary/sound/anticipated argument and the `trace.yml:776` + ADR-0010
citations, and the matching intake line filed in
`inputs/raw-requirements.md` alongside AC-063's and EC-009's. The breach was
already disclosed in these notes; what was missing is that a guardrail verdict is
read off `## Guardrails`, and an unamended "do not edit cli.py" beside a diff that
edits it cannot be told from an oversight.

**F-004 (minor) — FR-023's own statement amended by intake line.** The EC-009
amendment covered EC-009 only; `requirements.yml:922-925` carries the identical
defect ("cannot be reached by that N *without clamping*" / "would accommodate the
source's ratio *unclamped*" — both the N/9.5 reading, both contradicting AC-097
and AC-098). FR-023 is what `trace.yml` points at, so the EC-009 intake line was
extended rather than a second one filed. `requirements.yml` not hand-edited.

**F-005 (minor) — the AC-063 test renamed to match its body.**
`test_cli_square_size_shorthand_sets_both_sides` asserts `(30, None)`, i.e. that
the token sets exactly ONE side. Now
`test_cli_bare_size_token_reaches_the_domain_unsquared` /
`TestCLI_BareSizeTokenReachesTheDomainUnsquared`; the docstring records the old
id and points at the intake line, which was corrected — it had elected to keep
the old name, and that election was the defect. `requirements.yml` and
`trace.yml` still name the old id until the intake line is processed, deliberately
and disclosed.

**F-002 (minor) — the export-payload comment corrected.** It claimed the pair is
"fed from the request's own pair" and that "the aggregate carries what the user
asked for"; both are false for a bare `--size N`. It now says the pair is read off
`Puzzle.extent` through the accessors. Not a longer comment — one line more, and
one false claim fewer. `src/nonogram/export/**` untouched (G-5).

**F-006 (minor) — the double decode measured.** New
`test_a_bare_size_image_run_decodes_the_picture_exactly_twice` in
`tests/property/test_grid_dimensions.py` counts `image.load_greyscale` calls:
**2** for a bare `--size 10`, **1** for an explicit `--size 10x10`. The fixture is
`bands.png` (32x32), so the two requests differ in one token and produce the same
10x10 grid by the same route — the difference in the count can only be the shape
lookup. BOTH runs retry — the helper asserts `nudge.attempts == 2` for each:
bands at 10x10 converts to an ambiguous grid that two pixel-nudges repair, so
both counts are measured across three candidates and the difference cannot be an
artefact of one run retrying and the other not. 2 decodes across three
candidates is `_resolved_extent`'s once-outside-both-loops placement stated
as a count instead of as a comment. Proved to bite: with a second
`load_greyscale` added to `image.source_shape` it fails at `3 == 2`
(both files restored, md5 identical).

**F-007 (minor) — the falsified docstring narrowed.**
`test_a_non_unique_conversion_is_never_re_sourced` claimed "however a run turns
out, the picture is decoded once". It is a count of *conversions*, not decodes,
and the two now differ; the docstring says so and points at the counting test.

**One correction beyond the findings, same class and in the same blast radius:**
`test_a_bare_size_out_of_range_is_refused_before_the_source_is_consulted` asserted
`consulted == 1` under a failure message reading "the shape is read before the
stated side is validated — an out-of-range request must not pay for a decode",
and a docstring claiming the refusal comes "*before* the source's shape is read".
Both are inverted: `_resolved_extent` cannot reach `derive_extent` without the
shape, so a bare out-of-range N does read it, exactly once — the *source* is what
it never reaches. The assertion is right and unchanged; its prose now says what it
pins, which matters because the new decode-count test sits beside it asserting the
same fact the other way round.

**Suite: 1497 passed, 1 xfailed** (from 1494 + 1 xfailed; +3 = two parametrized
export cases and the decode counter). No test removed, none re-pointed.

Still left to the closing pass, unchanged: `trace.yml`'s FR-023 entry
(`status: partial`, "no kanban card cut for it", and R4's check ref missing from
its `tests:` list). F-008 (`derive_extent`'s Args block reading as axis-specific,
latent — no caller emits `(None, N)`) and F-009 (that same trace write-back) are
left `open` in the review report by instruction.

## AC/EC gate (2026-09-02)

**Verdict: PASS.** Eight criteria — AC-092..AC-098 and EC-009 — plus the six guardrails
that name tests. Every logical id resolves to exactly one `def`; `TestDeriveShape_
LibraryTemplateRatioAppliesSquareToday` and `TestDeriveShape_RandomSourceStaysSquare`
appear in `tests/test_cli.py` as well, but only as cross-references from a docstring, and
the criteria's own mapping table and section comments sit in `tests/test_derive_shape.py`
where the definitions are. **Suite: 1497 passed, 1 xfailed.**

The gate did not re-derive the measured figures a third time: the implementation measured
them, cycle 1's review re-derived them independently with an exact-`Fraction` oracle, and
cycle 2 re-derived them again over 10,000+ (N, ratio, orientation) cases plus a
cell-for-cell reproduction of the README table. Three independent agreements is enough;
a fourth pass would have been ritual.

### Closing pass — the four items cycle 2 required, all done here

- **F-013 (medium), the one cycle 2 said must not defer.** The F-005 rename left
  `trace.yml`'s two FR-018 rows pointing at `TestCLI_SquareSizeShorthandSetsBothSides`,
  which no longer exists — a live dead arrow in the model, created while fixing a
  prose defect. Both rows re-pointed at
  `TestCLI_BareSizeTokenReachesTheDomainUnsquared` / the pytest name, and both verified
  to resolve. `requirements.yml:645` still names the old id **deliberately** — that file
  is not hand-edited here — and is now the only thing the queued intake line has left to
  change. The intake line said "trace.yml's two rows must move with it"; since they have,
  the line itself was updated to say so, because leaving it would have been the same
  defect one level up.
- **F-009.** FR-023 flipped `partial` -> `covered`, with the eight pytest names appended.
  Its note said "not yet implemented — no kanban card cut for it" and named DEC-028 as
  unresolved; both were stale and are replaced. The note now also records the two
  corrections queued against `requirements.yml`, and corrects a third claim it carried:
  FR-021/CON-012's >2x refusal is **not** "structurally unreachable on this derived path"
  — it is the rule the ceiling is built from, which is why AC-098's refusal exists at all.
- **F-010, F-011, F-012** — three one-line prose corrections: a docstring citing
  `test_nudge.py` for `portrait.png`, which appears there zero times; a claim that only
  the bare run retries when the helper asserts `nudge.attempts == 2` for both; and a
  citation of `requirements.yml:922-925` for a quote starting at 921. F-011's sentence had
  been copied into this card too, and both copies are fixed.

[AC/EC check] All criteria/constraints ✓ (evidence: AC-092 test_image_bare_size_derives_from_the_ink_bounding_box_ratio, AC-093 test_corpus_mean_retention_rises_to_99_percent, AC-094 test_library_template_ratio_applies_square_today, AC-095 test_random_source_stays_square, AC-096 test_explicit_nxm_bypasses_derivation, AC-097 test_widest_accepted_ratio_is_exactly_n_over_five_to_one, AC-098 test_refuses_beyond_the_ceiling_naming_the_smallest_working_size, EC-009 test_the_derived_short_side_is_the_rounded_ratio_clamped_at_min_or_refused; plus test_the_cats_ears_survive_a_bare_size_25, the regression this card was reprioritised to close; suite 1497 passed, 1 xfailed) — every name resolved to exactly one `def` before this line was written; verified 2026-09-02.

