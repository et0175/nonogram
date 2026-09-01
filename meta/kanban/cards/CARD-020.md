# CARD-020: Web UI generation submission — form to pipeline to result page

**Status:** ready
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/020-web-submission-handler
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-4
**Idea:** —
**Wave:** 13
**Depends on:** CARD-019
**Touches:** src/nonogram/web/**.py, tests/test_web_submission.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The card that makes the web UI actually generate. CARD-019 serves the form; this one
submits it.

1. **`POST` handler**: parse the urlencoded body with `urllib.parse.parse_qs` (ADR-0020),
   map the fields onto `orchestrator.GenerationRequest` — `mode`, `size`, `density`,
   `difficulty`, `library_key`, `name`, `export_formats`, `out` — and call
   `orchestrator.generate()` then `orchestrator.export_puzzle()`. The `--image` field is
   CARD-021's; this card covers the library and random sources.
2. **Synchronously, on the request thread** (ADR-0021). No job store, no polling endpoint,
   no worker-thread handoff, no chunked/streamed response. ADR-0011's cooperative solver
   deadline already guarantees the run terminates within ADR-0001's 30s, so "without
   hanging" (AC-051) is delivered by a mechanism that already exists — do not build a
   second one.
3. **The mapping carries no validation** (ADR-0019/R1). A `size` of 60 is passed inward as
   60 and rejected by `sourcing.validate_size`, which is exactly what makes AC-050's "the
   same size-range domain error the CLI would raise" true by construction rather than by
   duplication. The same holds for density, an unsupported difficulty tier, and an empty
   `--name`.
4. **Result page** on success: outcome text plus the paths `export_puzzle()` returned.
   Nothing else — CON-008 rules out rendering the puzzle itself.
5. **Structured failure page** on any `NonogramError` (EC-003): one `try/except` around
   the orchestrator call, converting the domain exception into a failure response *before*
   anything is written to the response stream. No unhandled exception and no raw traceback
   may ever reach the browser. Note the drift risk ADR-0019 names explicitly: `cli.py`
   already maps the same `NonogramError` hierarchy to exit codes via `exit_code_for`'s MRO
   walk — read it first and keep the two taxonomies telling the same story.

## Acceptance criteria

- **AC-049** (happy) — given a web UI submission choosing library key "cat", size 20x20,
  difficulty "Medium", no name override, and export formats png+json, when the form is
  submitted, then the page reports success with the written PNG/JSON file paths, after the
  same orchestrator pipeline the CLI uses runs to completion.
  *test:* `TestWebUI_SubmitRunsSamePipelineAndReportsFiles`
- **AC-050** (negative) — given a web UI submission requesting a grid size of 60x60 (above
  the supported range), when the form is submitted, then the same size-range domain error
  the CLI would raise is surfaced to the page as a rejected request, and no files are
  written.
  *test:* `TestWebUI_RejectsOutOfRangeSizeLikeCLI`
- **AC-051** (error) — given a web UI submission whose options make every candidate fail
  the uniqueness/difficulty checks up to the configured retry bound (the same condition
  that raises `GenerationAbandoned` for the CLI), when the form is submitted, then the page
  reports the generation-abandoned failure and its reason, without hanging or returning an
  unhandled server error.
  *test:* `TestWebUI_ReportsAbandonedGenerationGracefully`

## Engineering constraints

- **EC-003** (resilience) — Any domain error the orchestrator pipeline raises for a web UI
  submission (an invalid-request error, `GenerationAbandoned`, `SolverTimeout`, or
  `ExportRejected`) is caught by the web adapter and surfaced to the page as a structured
  failure response, never as an unhandled exception or a raw stack trace, for any error
  type the pipeline can raise. Generalizes AC-051.
  *test:* `PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure`
  — a genuinely multi-case property test over the `NonogramError` hierarchy (walk the
  subclasses; do not hand-pick two).

## Guardrails

- G-1: Do not edit `src/nonogram/orchestrator.py` or any capability module
  (`src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `src/nonogram/solver/**`,
  `src/nonogram/difficulty.py`, `src/nonogram/export/**`) — the adapter maps the form onto
  the existing `GenerationRequest` and calls `generate()`/`export_puzzle()` unchanged
  (handoff Increment 4 Rollback; FR-017 "the SAME orchestrator pipeline")
- G-2: No domain validation in the adapter — an out-of-range size/density, an unsupported
  difficulty, or an empty name reaches the domain and is rejected there, exactly as for the
  CLI (ADR-0007, ADR-0010, ADR-0019/R1; AC-050)
- G-3: Out of scope — no job store, polling endpoint, worker thread, or chunked/streamed
  response for generation requests (ADR-0021). The bound is ADR-0011's existing deadline
- G-4: Out of scope — no in-browser preview of the generated puzzle (CON-008); the result
  page reports outcome text and file paths only. No progress/streaming feedback either
  (deferred, see `meta/kanban/backlog.md`)
- G-5: Existing CLI behavior and its `exit_code_for` error mapping unchanged — this card
  adds a second presentation of the same `NonogramError` hierarchy, it does not restructure
  the hierarchy or the CLI's mapping of it (ADR-0019 Negative)
- G-6: Do not edit `tests/test_cli.py`'s import guard — CARD-019 owns the adapter allowlist

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0021/R1 — The web UI's POST handler calls the orchestrator synchronously on the request thread and must not introduce a job store, polling endpoint, worker-thread handoff, or streame... (check: review-lens)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
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

- **FR:** FR-017
- **NFR:** NFR-001 (the 30s bound this handler relies on), NFR-002
- **ADR:** ADR-0021, ADR-0019, ADR-0020, ADR-0011, ADR-0010, ADR-0007
- **Components:** COMP-008 (the handler), COMP-002 (driven unchanged)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
