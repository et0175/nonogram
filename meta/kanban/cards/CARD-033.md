# CARD-033: A bare `--size N` derives the shorter side from the source's shape

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
- G-6: Do not edit `src/nonogram/cli.py` — `--size` PARSING is CARD-027's and is
  already done; this card works inward of the CLI, per ADR-0010.

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
