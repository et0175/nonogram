# CARD-027: Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes

**Status:** done
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/027-grid-extent-width-height-pair
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 18
**Depends on:** CARD-023, CARD-024, CARD-026
**Touches:** src/nonogram/cli.py, src/nonogram/orchestrator.py, src/nonogram/sourcing/random_grid.py, src/nonogram/sourcing/library.py, src/nonogram/sourcing/image.py, src/nonogram/difficulty.py, tests/test_cli.py, tests/test_orchestrator.py, tests/test_sourcing_random.py, tests/test_sourcing_library.py, tests/test_sourcing_image.py, tests/property/test_grid_dimensions.py, README.md
**Review score:** 8.0 (cycle 2; cycle 1 8.5)
**Started:** 2026-09-01T18:48:34Z
**Closed:** 2026-09-02T07:25:00Z
**Actual:** 1.6d
**Merge commit:** 632fd180b0c3572ac6ae11d6a32ec46aed5c4c02
**Blocked by:** —

## What to implement

The core of the increment: grid extent stops being one scalar and becomes a
`(width, height)` pair carried through the request, all three source modes, and the CLI
(FR-018, FR-019, ADR-0022/R1 and R2). Everything else in Increment 5 either precedes this
card or follows it.

1. **`orchestrator.GenerationRequest`** — `size: int | None` becomes `width: int | None`
   and `height: int | None`. It remains ADR-0012's unvalidated, syntactically-typed
   CLI/domain boundary type: a request may carry an out-of-range side all the way to the
   domain function that rejects it. The `Puzzle` aggregate's `size` property and
   `_mode_args`'s per-mode argument tuples move with it, as do
   `orchestrator.py`'s docstrings that describe extent as one number (including
   `DEFAULT_DEADLINE`'s "50x50 maximum size" comment at ~line 177, left stale by CARD-023
   because that card does not own this file).
2. **`sourcing/random_grid.py`** — `validate_size(size)` becomes `validate_extent(width,
   height)`, validating **each side** to `MIN_SIZE..MAX_SIZE` (10..30 after CARD-023) and
   naming the offending side in the error. It stays a **pure domain function inward of the
   adapter** and stays the single definition every mode delegates to (ADR-0022/R2).
   `filled_target` and `generate` take the pair; the row-slicing at the end of `generate`
   becomes `height` rows of `width` cells.
3. **`sourcing/library.py`** — `coverage(template, width, height)` and `render(template,
   width, height, threshold)`. `_axis_overlaps(source_len, target_len)` is already written
   per axis, so this is mostly threading the two target lengths to the two calls that
   currently both receive `size`. The module docstring's exact-magnification discussion
   (which sizes are whole-number magnifications of a template) is stated over one dimension
   and must be restated over both.
4. **`sourcing/image.py`** — `generate(source, width, height, rng)` calls
   `validate_extent` and passes the pair to `binarize`. CARD-026 already shipped
   `fit_crop_box`, the aspect guard and `binarize`'s target pair, so this card's image-mode
   work is the call site only — and no non-square request ever passes through an
   anisotropic stretch.
5. **`cli.py`** — `--size` accepts both forms through the **single existing flag**:
   `--size 30` means 30x30, `--size 30x20` means 30 wide by 20 tall. **Splitting the `NxM`
   token is a parsing concern and stays in argparse (ADR-0010).** Range validation does
   **not**: no `choices=`, no range-checking `type=`. A malformed token (`30x`, `x20`,
   `3x4x5`) is an argparse usage error naming the flag; an out-of-range but well-formed
   token (`40x20`) parses fine and is rejected inward by `validate_extent`. Update the
   flag's help text and `README.md`.
6. **`difficulty.py`** — `total_cells` follows the grid, which is already how it is
   computed. **Only** what is needed to keep it correct for a rectangle; the area-based
   normalizer question stays open (G-4).

## Acceptance criteria

- **AC-062** (FR-018): given the CLI invoked with `--size 30x20`, when the arguments are
  parsed, then the `GenerationRequest` carries width 30 and height 20.
  kind: happy — test: `TestCLI_ParsesRectangularSizeToken`
- **AC-063** (FR-018): given the CLI invoked with `--size 30` (the square shorthand), when
  the arguments are parsed, then the `GenerationRequest` carries width 30 and height 30.
  kind: boundary — test: `TestCLI_SquareSizeShorthandSetsBothSides`
- **AC-064** (FR-018): given the CLI invoked with `--size 30x` (a malformed NxM token),
  when the arguments are parsed, then argparse fails with a usage error naming the flag,
  and no `GenerationRequest` is constructed.
  kind: negative — test: `TestCLI_RejectsMalformedSizeToken`
- **AC-065** (FR-018): given the CLI invoked with `--size 40x20`, whose width is outside the
  supported range, when the arguments are parsed, then parsing succeeds and the request
  reaches the domain, where validation raises a size-range `NonogramError` naming the
  offending side — argparse never applies a `choices=`/`type=` range check (ADR-0010).
  kind: negative — test: `TestCLI_OutOfRangeSideRejectedByDomainNotArgparse`
- **AC-066** (FR-019): given a request for a 20x20 random grid, when the grid is generated,
  then a 20-column, 20-row black/white grid is produced.
  kind: happy — test: `TestGenerateRandom_ProducesRequestedDimensions`
- **AC-067** (FR-019): given a request for a 30x12 random grid, when the grid is generated,
  then a grid of 12 rows of 30 columns is produced, not a square.
  kind: happy — test: `TestGenerateRandom_ProducesRectangularGrid`
- **AC-068** (FR-019, INV-004): given a request for 30x30, the largest supported grid, when
  the grid is generated, then a 30x30 grid is produced without error.
  kind: boundary — test: `TestGenerateRandom_AcceptsMaxSide30`
- **AC-069** (FR-019, INV-004): given a request for a 31x30 grid, whose width is one past
  the supported maximum, when generation is requested, then the request is rejected with a
  size-range error and no grid is produced.
  kind: negative — test: `TestGenerateRandom_RejectsSideAbove30`
- **AC-070** (FR-019, INV-004): given a request for a 30x9 grid, whose height is one below
  the supported minimum, when generation is requested, then the request is rejected with a
  size-range error and no grid is produced.
  kind: negative — test: `TestGenerateRandom_RejectsSideBelow10`

Also required by ADR-0022/R2's own `check:` — the direct unit on the shared validator:
`TestValidateExtent_RejectsSideAboveThirty`.

## Engineering constraints

- **EC-005** (FR-019, verbatim from requirements.yml)
  - statement: For any requested (width, height) pair with either side outside 10..30, and
    in every source mode (random, built-in library, uploaded image), the request is rejected
    with a size-range error before any grid is produced — the bound is a property of the
    request, not of one sourcing path.
  - kind: consistency
  - instances: AC-069, AC-070
  - test: `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`

  This generalizes CARD-023's scalar predecessor
  (`PropertyTest_SizeRange_EverySourceModeRejectsSizeOutside10To30`) to independent width
  and height; replace that test rather than keeping both. The corpus must vary the two
  sides independently — a corpus that only ever moves them together cannot distinguish "each
  side is checked" from "the larger side is checked".

- **EC(ADR-0022/R1):** Grid extent crosses every module boundary as a `(width, height)`
  pair. No public function signature, request field, or export field in
  `src/nonogram/**` reduces a grid's extent to a single scalar `size`, and no source mode
  constructs a grid from one integer.
  test: `PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar`

  Follow the precedent already in the repo: `tests/test_cli.py`'s structural import guard
  walks `src/nonogram/**/*.py` on disk with `ast` and fails the suite on a violation. The
  same shape works here — walk the public signatures and dataclass fields and assert no
  scalar-extent parameter survives — so the rule is enforced for modules added later, not
  just for the ones this card edits.

- **EC(ADR-0022/R2):** Each grid side is validated to 10..30 inclusive by one pure domain
  function inward of the CLI adapter, reached by every source mode; the CLI parses the
  `--size NxM` form and never enforces the range itself. For every well-formed token a user
  can type, the rejection comes from the domain, not from argparse.
  test: `PropertyTest_Extent_RangeRejectionAlwaysComesFromTheDomain`

## Guardrails

- G-1: Do not edit `src/nonogram/clues.py`, `src/nonogram/solver/**`. COMP-004 and COMP-005
  are ALREADY rectangle-native — verified empirically: an 8x14 grid solves uniquely and
  round-trips, and a 3x5 computes correct clues. The increment states they need no change;
  a diff here is a finding (test: PropertyTest_Solver_NeverFalsePositiveUniqueness,
  TestComputeClues_MatchesGridExactly).
- G-2: argparse parses, it does not judge (ADR-0010). No `choices=` and no range-checking
  `type=` appears on `--size`; a well-formed out-of-range token reaches the domain
  untouched. The existing "out of domain range values pass the parser untouched" table must
  keep asserting that for `--size` (extend it with rectangular tokens; do not delete its
  `--size` rows) (test: TestCLI_OutOfRangeSideRejectedByDomainNotArgparse).
- G-3: `--size` stays ONE flag. Do not add `--width`/`--height`, and do not add a second
  positional form. FR-018 is explicit: the CLI expresses the pair through the single
  existing flag, and the square shorthand keeps working (test:
  TestCLI_SquareSizeShorthandSetsBothSides).
- G-4: Out of scope — do not change `difficulty.py`'s area-based normalizer
  (`size_pressure`'s use of `total_cells` against `MIN_SUPPORTED_CELLS`/
  `MAX_SUPPORTED_CELLS`) or the tier weights. Whether area is the right normalizer for a
  rectangle is a deliberately OPEN question that no card in this increment decides; touch
  `difficulty.py` only as far as keeping `total_cells` correct for a rectangle requires
  (test: the existing tests/test_difficulty.py and tests/test_difficulty_tiers.py suites).
- G-5: Do not edit `src/nonogram/export/**` or `tests/test_export_*.py` /
  `tests/property/test_export_roundtrip.py`. CARD-024 already moved the export payload and
  both file formats to a width/height pair at schema v2; this card only supplies the two
  values at the single `ExportPayload(...)` construction site inside `orchestrator.py`
  (ADR-0023/R1).
- G-6: The image crop geometry and the aspect guard are unchanged — `fit_crop_box`, the >2x
  refusal predicate and `binarize`'s internals are CARD-026's and are already correct for
  any target shape. This card owns `image.py` only as far as `generate`'s signature, its
  `validate_extent` call and its call into those functions; a diff inside their bodies is a
  finding (test: PropertyTest_FitImage_CropBoxIsLargestCentredRectangleOfTargetAspect,
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore).
- G-7: Do not edit `src/nonogram/web/**` — CARD-028 owns the web form's extent field. Note
  the ordering consequence: between this card's merge and CARD-028's, the web adapter is the
  one caller that has not been moved to the pair. If that makes the suite red rather than
  merely feature-incomplete, raise `[BLOCKER]` and escalate to the decompose station for a
  re-slice; do not fix it here.
- G-8: Do not edit `MIN_SIZE`/`MAX_SIZE` values or `MAX_SUPPORTED_CELLS`. CARD-023 already
  narrowed the range to 10..30; this card generalizes *what* is validated, not the bound.

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

- **FR:** FR-018, FR-019
- **NFR:** —
- **CON:** CON-011
- **ADR:** ADR-0007, ADR-0010, ADR-0012, ADR-0022
- **Components:** COMP-001, COMP-002, COMP-003, COMP-006
- **Trace:** meta/architecture/trace.yml

## Failure matrix

Declared **before** implementation, per the card's `Complexity: architectural`
obligation. This card adds no I/O, no concurrency, no retry and no new external
boundary — but it is not the one-line "no failure-bearing boundary" case either,
because it owns a *parsing* boundary (argv) and a *validation* boundary (the
domain extent rule) and the whole point of ADR-0010/ADR-0022/R2 is which of the
two refuses what. The rows are those two boundaries crossed with every failure
mode a `--size` token can have.

| # | Operation / boundary | Failure mode | DECLARED behaviour | Bound |
|---|---|---|---|---|
| 1 | `cli._extent_token` (argparse `type=`) | token is not `N` or `NxM` — `30x`, `x20`, `3x4x5`, `big`, `3.5`, `""` | `argparse.ArgumentTypeError` → argparse's own usage error naming `--size`, exit code 2 (`ExitCode.USAGE`). **No `GenerationRequest` is constructed.** (AC-064) | one token, no retry, no I/O |
| 2 | `cli._extent_token` | token is well-formed but out of range — `40x20`, `0`, `9`, `31`, `-5`, `30x9` | Parses to an `(int, int)` pair and is carried inward **unchanged**. argparse applies no `choices=` and no range-checking `type=` (ADR-0010, G-2). The refusal comes from row 4. (AC-065) | — |
| 3 | `cli._extent_token` | separator case/extras — `30X20`, `30 x 20` | `X` is **not** a separator: `30X20` is row 1 (usage error). Each side is parsed with Python's `int()`, which tolerates surrounding whitespace, a leading sign and `_` digit separators (`1_0` is 10). Declared, not defended: these are the documented semantics of `int()` and are harmless — every such value still faces row 4. | — |
| 4 | `random_grid.validate_extent` (the single pure domain rule, reached by all three modes) | either side is `None` or outside `MIN_SIZE..MAX_SIZE` | `SizeOutOfRange` naming **which** side and its value. Width is judged first, so a request bad on both sides reports width. Pure function: no I/O, no randomness drawn, no partial grid. (AC-069, AC-070, EC-005) | total function, single call, no retry |
| 5 | `random_grid.generate` / `library.generate` / `image.generate` | invalid extent | Validated **before** any work: no cell is drawn, no RNG value consumed, no template rendered, no image file opened. Two rejected calls followed by a valid one produce the grid the single valid call would. | — |
| 6 | `library.generate` | invalid extent **and** unknown key | `UnknownLibraryImage` wins — the key is resolved first, unchanged from before this card. | — |
| 7 | `image.generate` | extent valid, grid aspect ratio more than 2x from the source's | `ImageNeedsManualCrop` (CARD-026's guard, untouched by this card — G-6). Now genuinely reachable for a non-square request, which is what it was built for. | — |
| 8 | `image.generate` | extent valid, source unreadable/missing | `UnreadableImage`, unchanged. Full ordering is **missing-source guard → range → probe → aspect → decode** (EC-007). Corrected at cycle-1 F-004: this row first declared it as `range → probe → aspect → decode`, omitting the `source is None` guard that precedes `validate_extent` (`sourcing/image.py:614-619`). Verified: `image.generate(None, 40, 20, rng)` raises `UnreadableImage`, NOT `SizeOutOfRange`, while a valid path with the same 40x20 raises `SizeOutOfRange`. That is the mirror of row 6, which was declared correctly, so the omission was inconsistency rather than a wrong belief about the code. | — |
| 9 | Every row above, at the CLI | any `NonogramError` | `cli.main` maps it through `exit_code_for`'s MRO walk; all of rows 4–8 are `INVALID_INPUT` (exit 3), never argparse's exit 2. | — |

Not applicable, stated so the reviewer does not look for it: no timeout, no
backoff, no circuit breaker, no idempotency key, no partial write, no schema
migration. The one durable artifact (the export file) is CARD-024's and is
untouched here.

## Worktree notes

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Dependency gate]** CARD-023, CARD-024 and CARD-026 all `done` — this card's
  three dependencies are satisfied for the first time since it was cut.
- **[Drift gate]** ⚠ warn, and worth reading before acting on: six of this card's
  files appear in `meta/drift-pending.yml` by EXACT path match, so the gate fires
  genuinely. But the events are this session's OWN commits (the newest three are
  timestamped minutes before this card started and name `export/layout.py` from
  CARD-034's merge), not unreconciled external change. Treat as signal noise from
  forge recording its own work, not as a reason to distrust the tree.

### Structural decisions (later cards read these as the local convention)

- **STRUCTURE: the pair is always `(width, height)`, in that order, in every
  signature, field, tuple and error message** — because the user-facing token is
  `WxH` (ADR-0022) and the export payload already orders them that way
  (CARD-024). The one place the order inverts is Pillow's `(width, height)` vs a
  row-major `list[list[bool]]`'s `height` rows, and that inversion was already
  named in `image.binarize`'s docstring; nothing new is introduced.

- **STRUCTURE: `validate_size(size)` is REPLACED by `validate_extent(width,
  height) -> tuple[int, int]`, not supplemented by it.** ADR-0022/R1 forbids a
  public signature that reduces extent to one scalar, and leaving the scalar
  validator alive "for convenience" would leave every later card a legal way to
  keep writing square code. The per-side check is a private `_validate_side`, so
  there is exactly one public statement of the rule and exactly one message
  format. Callers that only need one side do not exist — nothing in the model
  validates half an extent.

- **STRUCTURE: the range error names the offending side.** `grid width must be
  between 10 and 30 inclusive, got 40` rather than `grid size must be...`. With
  two independent sides, an unattributed message makes the user guess which one
  they typed wrong. Width is judged first when both are bad — declared in the
  failure matrix rather than left to argument order.

- **STRUCTURE: argparse holds the pair under `dest="extent"`, not `dest="size"`.**
  The *flag* stays `--size` (G-3, ADR-0022: one flag, and no existing invocation
  breaks). The parsed *value* is no longer a size, so naming the namespace
  attribute `size` would leave the codebase's most-copied example of "extent" a
  scalar noun holding a pair. `--size`'s `type=` is a pure tokenizer: it splits
  and calls `int()`, and enforces no bound (ADR-0010, G-2).

- **STRUCTURE: `_source_arguments` threads `(width, height)` positionally into
  each mode, immediately after the mode's own leading argument.** Random is
  `(width, height, density)`, library `(key, width, height)`, image `(path,
  width, height)` — the RNG still appended by the caller. So every mode reads
  "what the mode is about, then the extent, then the run's randomness", which is
  the shape CARD-033 will extend.

- **STRUCTURE: ADR-0022/R1 is enforced structurally, by an `ast` walk of
  `src/nonogram/**/*.py`, in the style of `tests/test_cli.py`'s import guard**
  (`PropertyTest_Extent_NoPublicBoundaryReducesGridToOneScalar`). It bans any of
  six scalar-extent names — `size`, `grid_size`, `edge`, `edge_length`, `side`,
  `n` — as a parameter of a **public** function, as a public class field
  (annotated `size: int` OR bare `size = 30`), or as the name of a public
  `int`-returning accessor. A parameter counts whether it is annotated `int`,
  annotated with anything containing an `int` (unions, `Optional`, `Annotated`,
  `builtins.int`, the quoted `'int'`), or **not annotated at all**.
  *This paragraph was wrong twice before it was right: cycle 1 asked for it to
  be updated when the rule changed, the fix commit did not, and cycle 2 found
  it still saying `int`-annotated and still listing four names of six. Its
  reach is now pinned by `_GUARD_SHAPES` — 15 source shapes with expected
  verdicts — so this prose can no longer drift from the code silently.*
  **Declared gaps, not oversights:** the guard walks annotation *syntax* and
  never resolves a name binding, so `Size = int` and a `NewType` defeat it.
  Both are pinned as expected-to-slip, so a later card that closes the gap gets
  a failing test telling it to update the table.
  **Known false-positive surface:** an absent annotation counts and `n`/`side`
  are in the name set, so an unannotated public `def chunk(items, n)` WILL be
  flagged. Loud and trivially fixed, but it will surprise whoever meets it.
  **Two deliberate exclusions**, each principled rather than an allowlist entry:
  **private** helpers
  (`export/pdf._header_font(size: int)` — a type size in pixels, not a boundary),
  and **non-`int`** annotations (`difficulty.SignalWeights.size: float` — a
  normalizer weight; G-4 forbids touching it, and a grid extent is a count of
  cells and can never be a float). A module a later card adds is covered from the
  moment it lands, exactly like the import rule.

- **STRUCTURE: `difficulty.py` is NOT edited.** Card item 6 asks only that
  `total_cells` stay correct for a rectangle; it is already sourced from the
  solver's signals, which count the clue sets rather than squaring a side, so a
  rectangle needs no change and a diff here would be G-4 scope growth. The
  `MIN_SUPPORTED_CELLS`/`MAX_SUPPORTED_CELLS` cross-check moves into the new
  property file unchanged.

### Implementation record

- **`tests/property/test_size_range.py` is deleted, replaced by
  `tests/property/test_grid_dimensions.py`**, as EC-005 instructs. The new
  corpus has its own precondition test
  (`test_the_corpus_really_does_move_the_two_sides_independently`), which
  asserts a floor on each of the three rejection classes — width-only bad,
  height-only bad, both bad — so EC-005's "a corpus that only moves them
  together proves nothing" cannot regress silently into a square corpus.
- **`_convert` in `tests/test_sourcing_image.py` now delegates to
  `image.generate`.** CARD-026 wrote it as a hand-assembled copy of `generate`'s
  body precisely *because* `generate` took a scalar and a rectangular request
  had no caller; this card supplies the caller, so the copy is retired rather
  than left to drift from the shipped pipeline. All of CARD-026's rectangular AC
  tests (AC-059, AC-071..AC-079) now run through the real entry point, which is
  the strongest available evidence the wiring is right.
- **Guardrail G-7 held, and the ordering consequence it predicts materialised as
  predicted — as a *declaration*, not a red suite.** `src/nonogram/web/**` is
  untouched. The CLI/web option-parity guard in `tests/test_web_server.py` now
  records two deliberate differences instead of one (`image`, argv-only, from
  CARD-021; and `extent` on argv against `size` on the form, until CARD-028),
  each as an exact set so neither gap can widen unnoticed. Nothing in the web
  adapter is *wrong* today: its `size` field is a plain text input that nothing
  wires to a `GenerationRequest` yet (CARD-020 owns that), so the adapter is
  older, not broken. No `[BLOCKER]` was raised.
- **Guardrail G-5 came closest to conflicting, and was honoured in substance.**
  `tests/test_export_*.py` and `tests/property/test_export_roundtrip.py` are on
  G-5's do-not-edit list, but they construct `GenerationRequest(size=...)`, and
  keeping a `size` alias on the request to avoid touching them is exactly what
  ADR-0022/R1 forbids. The edit there is therefore the mechanical minimum —
  `size=N` becomes `width=N, height=N` — plus retiring two comments that said
  the pair was "fed from one scalar until CARD-027", which this card made false.
  No export behaviour, format, schema or assertion changed.
- **Stale extent text left unfixed, in two separate groups.** Cycle 2 (F-204)
  found the first version of this note folded them into one sentence whose
  lead-in, attribution and fence were all false of the second group:
  - **Stale `50x50` docstrings** in `solver/search.py`, `solver/propagate.py`,
    `export/json_export.py`, `export/svg.py`. Left by CARD-023's narrowing to 30,
    not by this card; those packages are off limits under G-1 and G-5.
  - **The web form's label** in `src/nonogram/web/pages.py` — "Size — square grid
    edge length". Not a `50x50` string, not left by CARD-023, and fenced by a
    different guardrail: G-7, reserving that field for CARD-028.

## Architecture revision (2026-09-01) — RESOLVED, gate cleared

**Status: absorbed.** This card was gated on 2026-09-01 because it defines what a
bare `--size N` means and that meaning was being changed underneath it. The
change is now decided and formalized, so the gate is cleared and this section
records the settled delta rather than an open question.

**What was decided.** FR-023 and ADR-0022/R4: `--size NxM` specifies both sides
exactly (this card's job, unchanged); a bare `--size N` sets the LONGER side and
derives the other from the source's shape. The derivation itself is **CARD-033**,
which depends on this card — so THIS card lands the `(width, height)` pair,
`--size NxM` parsing, and per-side range validation, and a bare `--size N` may
continue to mean N x N when this card merges. That is an increment, not a
contradiction: FR-023 is delivered by CARD-033 immediately after.

**Why the split, given both cards touch the same files.** The expensive, risky
work is the pair refactor — the request type, all three source modes and their
tests. Once that exists, changing what a bare N maps to is a localized change in
one place. Doing them as one card would exceed `sizing.max_estimate` and put a
structural refactor and a policy rule in the same review.

**What this card must NOT do:** implement the derivation, the `N/5 : 1` refusal,
or page orientation. Those are CARD-033 and CARD-034, and building them here is
the scope growth the SCOPE GATE exists to catch.

**Also settled, and relevant to this card's tests:** NFR-005 and EC-008 no longer
claim printed cell size is a function of `max(width, height)` — it is not, and the
property was ill-posed for rectangles. If a test here asserts anything about cell
size across shapes, take the corrected ceiling-bound wording, not the old one.
CARD-034 owns that correction.

## AC/EC gate (2026-09-02)

**Verdict: PASS, after one repair.** Eleven criteria: AC-062..AC-065 (FR-018),
AC-066..AC-070 + EC-005 (FR-019), CON-011 via EC-005. Ten had a test that
existed, ran green, and asserted what the criterion says. One did not.

**AC-085 had no test at all.** The gate is what found it — neither review cycle
did, because both reviewed the card, and **AC-085 is not in this card's
`## Acceptance criteria` section**. It was added to `requirements.yml` by
`eb7df1c` (the FR-022 / DEC-025..027 architecture delta), which landed after
this card was decomposed. `trace.yml` does list
`TestCLI_RectangularRequestProducesWidthByHeightGrid` under FR-018, so the
delivery contract carried it and the card silently did not — the same
card-vs-model skew shape as CARD-024's F-001, arriving by a different route.

Nothing else covered the criterion either, and the reason is worth recording.
The behaviour "a rectangular request produces height rows of width columns" is
asserted in two places, neither of which is AC-085's seam:
`tests/property/test_grid_dimensions.py` asserts it for 300+ rectangles but
calls the **sourcing** functions directly; `test_orchestrator.py` has two
rectangular tests, one asserting the *aggregate's attributes* (15x22) and one
asserting the *arguments into a scripted source* (12x25). So the extent was
pinned going in and pinned as stored, but no test ran a real generation from a
rectangular request and looked at what came out. A transposition downstream of
`_source_arguments` — in the aggregate, the clue derivation, or the solver
round trip — passed the whole suite.

Repair: `test_cli_rectangular_request_produces_width_by_height_grid` in
`tests/test_orchestrator.py`, pinned-seed style per that module's own docstring.
It lives there rather than in `tests/test_cli.py`, despite the `TestCLI_` prefix
requirements.yml gives it, because the criterion's *given* is a
`GenerationRequest` and its *when* is "generation runs to completion" — COMP-002's
seam. `test_cli.py`'s `captured_requests` fixture stubs the pipeline out by
design (its docstring says so), which makes the criterion unassertable there.
The prefix is a naming slip in the model, not a placement instruction; flagged
rather than edited, since `requirements.yml` is not hand-edited.

Mutation-verified, source restored byte-identical:
- M1 — clues derived from the transpose, grid untouched → **KILLED** (clue assertion)
- M2 — grid stored transposed on the aggregate → **KILLED** (grid assertion)

Two mutants, killed by two different assertions, which is why the clue lengths
are asserted alongside the grid shape rather than as decoration.

**Suite: 1463 passed, 1 xfailed** (was 1462 + 1).

### Not a defect of this card, but found by its gate

Writing AC-085's test needed a real 30x20 generation and could not get one at
the default density. Measured across the density range, 3 seeds each: **0/3
uniquely solvable at every density from 10 to 45**, recovering at 50 (2/3) and
solid from 55 up. At 30 it is 0/6 over seeds 0-5, 7-18s each; at 35-45 it is
~30s each. Every failure is `GenerationAbandoned` after 20 attempts, not a
timeout. So `--size 30x20` at the default density fails for every seed tried,
inside the range CON-011 admits.

This is a real product limit and it is **not** CARD-027's subject — the card
delivers the width/height pair, and the pair is delivered correctly. Filed to
the backlog with the full table and four options. The test pins density 70 to
stay clear of the band, and says why in its docstring so the choice does not
read as arbitrary.

[AC/EC check] All criteria/constraints ✓ (evidence: AC-062 test_cli_parses_rectangular_size_token, AC-063 test_cli_square_size_shorthand_sets_both_sides, AC-064 test_cli_rejects_malformed_size_token, AC-065 test_cli_out_of_range_side_rejected_by_domain_not_argparse, AC-085 test_cli_rectangular_request_produces_width_by_height_grid, AC-066 test_generate_random_produces_requested_dimensions, AC-067 test_generate_random_produces_rectangular_grid, AC-068 test_generate_random_accepts_max_side_30, AC-069 test_generate_random_rejects_side_above_30, AC-070 test_generate_random_rejects_side_below_10, EC-005 test_every_source_mode_rejects_every_side_outside_ten_to_thirty + test_every_source_mode_accepts_every_extent_inside_ten_to_thirty, CON-011 via EC-005 and test_no_public_boundary_reduces_a_grid_to_one_scalar; suite 1463 passed, 1 xfailed) — AC-085 was absent and was added by this gate (see "AC/EC gate (2026-09-02)" above); all eleven verified against the current implementation on 2026-09-02.
