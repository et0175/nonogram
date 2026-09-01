# CARD-029: Retire the last stale 10..50 range claims left by CON-011

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/029-stale-range-prose
**Worktree:** —
**Source:** CARD-023 cycle-1 review, adversarial verification of F-002
**Idea:** —
**Wave:** —
**Depends on:** CARD-023, CARD-025
**Touches:** src/nonogram/orchestrator.py, src/nonogram/solver/propagate.py, src/nonogram/solver/search.py, src/nonogram/export/json_export.py, src/nonogram/export/svg.py, tests/test_solver.py, tests/test_export_image.py, tests/property/test_solver_uniqueness.py, tests/property/test_export_roundtrip.py, docs/requirements.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CARD-023 narrowed the supported grid range to 10..30 (CON-011, ADR-0022) and updated
every site inside its own `Touches:`. It could not update the rest: guardrail G-1
forbade it `src/nonogram/solver/**` and G-5 forbade it `src/nonogram/export/**` and
`orchestrator.py`. This card sweeps up what those guardrails protected.

**This is documentation drift, not a numeric defect — and that distinction was
verified before this card was cut.** The constants justified by "50" remain correct
at 30:

- `export/layout.py`'s `_CLUE_FONT_RATIO = 0.62` is sized for "a two-digit clue (the
  longest possible run is 50, AC-038)". At 30 the longest run is still two digits, so
  the ratio is unchanged. Only the number and the AC id in its rationale are stale.
- Nothing else in the sweep feeds a computation. Every remaining hit is prose in a
  docstring or a `#:` comment.

So the work is: make the statements true, change no behaviour, and expect the full
suite to be byte-for-byte unaffected.

### The sites

Each is stale in the number, and several are also stale in the AC id — AC-038 was
superseded by AC-084 when the fixture moved to 30x30, so a reference reading
"AC-038" now points at a retired criterion.

**Source (guardrail-blocked for CARD-023):**

| File | Line | What it says |
|---|---|---|
| `orchestrator.py` | 177 | "to the 50x50 maximum size" |
| `solver/search.py` | 35 | "at the 50x50 upper bound (ADR-0001)" |
| `solver/propagate.py` | 101 | "a few tens of megabytes on a 50x50 run" |
| `solver/propagate.py` | 588 | "50x50 upper bound, each O(length x runs)" |
| `export/json_export.py` | 85 | "at the maximum supported 50x50 (AC-038)" — number **and** AC id |
| `export/svg.py` | 142 | "at the maximum supported 50x50" |

**Tests (outside CARD-023's `Touches:`, not guardrailed):**

| File | Line | What it says |
|---|---|---|
| `tests/test_solver.py` | 561 | "ADR-0014's free-direction check asks for this all the way to 50x50" — its own `parametrize` is already `[10, 20, 30]`, so the prose contradicts the code beside it |
| `tests/test_export_image.py` | 329 | "A 50x50 whose clues run to 25 numbers needs 75 cells across" |
| `tests/property/test_solver_uniqueness.py` | 49, 105 | "scaled to 50x50"; "the 10x10..50x50 *product* range (AC-003/...)" |
| `tests/property/test_export_roundtrip.py` | 50, 142 | "50x50 is where a row is 50 CSV cells wide"; "the 10x10..50x50 request range (AC-003/...)" |

**Raw intake:**

| File | Line | What it says |
|---|---|---|
| `docs/requirements.md` | 47, 150 | "10x10 to 50x50" |

`docs/requirements.md` is the highest-traffic one: CLAUDE.md points contributors at it
as "the full spec", so it is the most likely place for a newcomer to read the wrong
range. It is raw intake rather than a generated artifact, so amend it in place and
note the amendment — do not regenerate it.

### Explicitly NOT in this card

- **`src/nonogram/export/layout.py`** — four stale sites (61, 98, 111, 314) plus
  `_CLUE_FONT_RATIO`'s rationale at 129. **CARD-025 already owns this file** and is
  rewriting its cell-size rule wholesale for NFR-005. Two cards editing one file back
  to back is exactly the overlap the dispatcher serializes against, and CARD-025 has
  to touch these lines anyway. Fold them in there; this card must not touch
  `layout.py`. Note especially `MIN_CELL_MM`'s justification, "small enough that a
  50x50 still fits" — under NFR-005's `min(comfort cap, page fit)` that floor's whole
  rationale is being replaced, so it is CARD-025's to restate, not this card's to
  patch.
- **Historical references that SHOULD say 50x50.** `tests/test_timeout.py:38, 88, 266`
  and `tests/test_difficulty.py:269` were written BY CARD-023 to explain why the
  narrowing happened and what it broke ("50%, the hard class CARD-004 found at 50x50,
  is now trivially easy at 30x30"). Those are correct history and must survive. A
  blind find-and-replace of "50x50" would destroy exactly the record that makes the
  next range change safe.

## Acceptance criteria

- **AC-085** (happy) — given the repository after CARD-023 and CARD-025 have merged,
  when the source tree and test tree are searched for `50x50`, `10x10..50x50`,
  `10..50` and "10 and 50", then every remaining hit is either a deliberate historical
  reference (the four sites named above) or absent entirely; no file states the
  supported range as anything but 10..30.
  *test:* `TestNoStaleRangeClaimsRemain`
- **AC-086** (boundary) — given a reference that cites `AC-038` for a range or size
  fact, when it is updated, then it cites `AC-084` (or the requirement that actually
  governs the statement), because AC-038 was superseded and a citation to it resolves
  to a retired criterion.
  *test:* `TestNoStaleRangeClaimsRemain`
- **AC-087** (negative) — given this card's changes, when the full suite runs, then
  the pass/xfail counts are identical to before it, because nothing but prose changed.
  *test:* the full suite itself

## Guardrails

- G-1: Change **no executable line**. An AST comparison with docstrings and comments
  stripped must show every touched module identical to its pre-card state. This card
  is prose only; if a fix appears to require a behaviour change, that is a finding —
  stop and report it rather than making the change.
- G-2: Do not touch `src/nonogram/export/layout.py` — CARD-025 owns it (see above).
- G-3: Do not delete or rewrite the four deliberate historical references in
  `tests/test_timeout.py` and `tests/test_difficulty.py`. They are the record of why
  the range moved.
- G-4: Do not change `docs/requirements.md`'s structure or regenerate it — it is raw
  intake; amend the two range statements in place.
- G-5: Do not weaken, retarget or delete any test. `tests/test_solver.py:561`'s prose
  is stale but its `parametrize` is already correct — fix the sentence, not the cases.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never en... (check: TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by m... (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
- ADR-0022/R4 — A `--size` token carrying both dimensions specifies the grid exactly and the source is fitted to it. A bare `--size N` sets the grid's LONGER side to N and derives the othe... (check: PropertyTest_BareSize_DerivesShorterSideFromSourceShape)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions ... (check: review-lens)
- ADR-0023/R2 — A decoder accepts only its own SCHEMA_VERSION, by exact comparison, and raises an error naming both the file's version and its own. It never attempts a best-effort read of ... (check: TestExport_RejectsSupersededSchemaVersion)
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

- **FR:** FR-019
- **NFR:** —
- **CON:** CON-011
- **ADR:** ADR-0022 (grid extent and size range)
- **Components:** COMP-002, COMP-003, COMP-005, COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
