# CARD-028: Web form's size field accepts the `NxM` extent token

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/028-web-form-extent-token
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 19
**Depends on:** CARD-020, CARD-027
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py, tests/test_web_submission.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

CON-011 and ADR-0022 apply to **both inbound adapters**, not only the CLI. CARD-027 moved
`orchestrator.GenerationRequest` from a scalar `size` to a `(width, height)` pair; this card
moves the web UI's form field to match, so the second adapter builds the same request shape
the CLI does.

1. **`src/nonogram/web/pages.py`** — the `<input type="text" name="size">` field keeps its
   name and its free-text nature but now accepts both forms: `20` (square shorthand) and
   `20x30`. Its label/placeholder says so. Per ADR-0019/R1 and the package's own docstring
   ("Nothing here constrains a value: no `min`/`max` on `size`"), **do not** add `min`,
   `max`, a `pattern`, or a numeric input type — the form must keep letting a browser
   submit anything, because that is what makes the domain the single judge.
2. **`src/nonogram/web/handler.py`** — reading the field and splitting the `NxM` token is
   HTTP-side *parsing*, the exact counterpart of what argparse does for the CLI
   (ADR-0022/R2). Judging whether a side is in range is **not**: an out-of-range or
   malformed value builds a request that the orchestrator rejects with the same
   `NonogramError` the CLI raises, and the handler renders that error. No domain rule
   enters this package (ADR-0019/R1).
3. AC-050's existing behaviour — a 60x60 submission rejected with the same size-range domain
   error the CLI raises, writing nothing — must keep passing unchanged; at `MAX_SIZE = 30`
   60 is still out of range, so the criterion is intact and is this card's regression anchor.

**Requirement gap, surfaced not invented:** FR-018 and CON-011 both state that the rule
applies to the web adapter, but no acceptance criterion in `requirements.yml` covers the web
surface of the extent pair (AC-062..AC-065 are CLI-phrased). This card therefore carries an
engineering constraint and a regression anchor rather than a new AC. Reported as an
architect-station gap in the decompose run report; do not invent an AC here.

## Engineering constraints

- **EC(ADR-0022/R2):** The web form's size field parses the `NxM` token and the square
  shorthand into the request's width and height and applies no range, shape, or ratio check
  of its own. For every value a browser can submit — well-formed, malformed, out of range,
  empty — the rejection (or acceptance) comes from the same pure domain validator the CLI
  reaches, and the adapter's only job is to render whatever the domain said.
  test: `PropertyTest_WebForm_ExtentJudgedByDomainNotAdapter`

## Guardrails

- G-1: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/cli.py`,
  `src/nonogram/sourcing/**`, `src/nonogram/export/**`, `src/nonogram/clues.py`,
  `src/nonogram/solver/**`, `src/nonogram/difficulty.py` — this card is adapter-only. Every
  domain-side piece it needs was shipped by CARD-023, CARD-024, CARD-026 and CARD-027.
- G-2: No domain logic or validation enters `src/nonogram/web/` (ADR-0019/R1). No `min`/
  `max` attribute, no `pattern`, no numeric input type, no range check in the handler — the
  package's own module docstring already states this and the structural import guard
  enforces the boundary (test: test_every_import_in_the_package_points_inward).
- G-3: The synchronous request handling of ADR-0021/R1 is unchanged — no job store, polling
  endpoint, worker-thread handoff, or streamed/chunked response is introduced by this card.
- G-4: NFR-003/NFR-004's loopback posture is unchanged — the server still binds 127.0.0.1
  only and still refuses cross-site and foreign-authority requests (test:
  TestWebServer_BindsLoopbackOnlyByDefault,
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest).
- G-5: AC-049..AC-053's existing submission behaviour is unchanged in substance — same
  pipeline as the CLI, same domain errors, same abandonment reporting, no credentials. Only
  the extent field's accepted syntax moves (test: the tests/test_web_submission.py suite).

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0021/R1 — The web UI's POST handler calls the orchestrator synchronously on the request thread and must not introduce a job store, polling endpoint, worker-thread handoff, or streame... (check: review-lens)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0022/R2 — Each grid side is validated to 10..30 inclusive, as a pure domain function inward of the CLI adapter, for every source mode. The CLI parses the --size NxM form but never en... (check: TestValidateExtent_RejectsSideAboveThirty)
- ADR-0022/R3 — An uploaded image is fitted to the requested grid's aspect ratio by a centred crop, never by stretching and never by padding. A request whose grid aspect ratio differs by m... (check: TestFitImage_RefusesRatioMismatchBeyondTwice)
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

- **FR:** FR-017, FR-018
- **NFR:** NFR-003, NFR-004
- **CON:** CON-011
- **ADR:** ADR-0019, ADR-0021, ADR-0022
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
