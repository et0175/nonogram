# CARD-021: Image upload via hand-rolled multipart parsing

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/021-web-image-upload
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-4
**Idea:** —
**Wave:** 14
**Depends on:** CARD-020
**Touches:** src/nonogram/web/**.py, tests/test_web_upload.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The increment's genuinely unproven mechanism, deliberately isolated into its own card:
`--mode image` from the browser.

1. **`<input type="file">` on the form**, which makes the submission
   `multipart/form-data` instead of `application/x-www-form-urlencoded`. Branch on the
   request's `Content-Type`; the urlencoded path CARD-020 shipped keeps working unchanged.
2. **Hand-rolled multipart parsing** via `email.parser.BytesParser` over the reconstructed
   headers-plus-body (ADR-0020). There is no stdlib shortcut left: `cgi.FieldStorage` was
   removed in Python 3.13 by PEP 594, and this project's floor is 3.14. This is the
   fiddliest code in the increment — boundary handling, encoding, and large bodies are all
   easy to get subtly wrong, and nothing before this card exercises any of it.
3. **Land the upload in a temp file** and pass its path as `GenerationRequest.image`. The
   conversion itself, the dithering, and the bounded pixel-nudge recovery are CARD-015's
   and CARD-016's and are reached unchanged — this card delivers the *bytes*, not the
   behavior.
4. **Whether the file is readable or decodable is a domain question**, not an adapter one:
   an unreadable upload must surface as `UnreadableImage` from the sourcing module through
   EC-003's structured-failure path, not as an adapter-side pre-check (AC-008, ADR-0010,
   ADR-0019/R1).
5. Clean up the temp file after the run — including on the failure path.

## Acceptance criteria

_Carried from FR-017 (AC-049's option surface explicitly includes "an uploaded image"), and
verified end-to-end against the existing image pipeline. FR-017's own AC-049..AC-051 are
CARD-020's; this card's criteria instantiate the same contract for the upload branch._

- **AC-049/upload** (happy) — given a `multipart/form-data` submission carrying a real PNG
  and size 20x20, when the form is submitted, then the upload is written to a temp file,
  passed to the same image sourcing path the CLI's `--image` uses, and the page reports
  success with the written file paths.
  *test:* `TestWebUpload_ConvertsUploadedImageThroughSamePipeline`
- **AC-050/upload** (negative) — given a `multipart/form-data` submission whose uploaded
  file is not a decodable image, when the form is submitted, then the same
  `UnreadableImage` domain error the CLI would raise is surfaced as a structured failure
  and no files are written.
  *test:* `TestWebUpload_RejectsUndecodableUploadLikeCLI`
- **AC-boundary/multipart** (boundary) — given a multipart body whose part boundary
  sequence also occurs inside the uploaded image's bytes, when the body is parsed, then
  the extracted file content is byte-for-byte identical to the uploaded file.
  *test:* `TestWebUpload_ParsesBoundaryCollidingBodyExactly`

## Guardrails

- G-1: Do not edit `src/nonogram/orchestrator.py`, `src/nonogram/sourcing/**`, or any other
  capability module — the upload lands a temp file and passes its path as
  `GenerationRequest.image`; conversion, dithering, and nudge behavior are CARD-015's and
  CARD-016's, unchanged (handoff Increment 4 Rollback)
- G-2: No new runtime dependency — multipart parsing is stdlib only (`email.parser`).
  ADR-0006's baseline and ADR-0020's choice stand; do not reach for a parsing library
- G-3: The existing urlencoded (non-upload) submission path is unchanged — adding the
  multipart branch must not alter how library/random-mode submissions are parsed
  (test: `TestWebUI_SubmitRunsSamePipelineAndReportsFiles`)
- G-4: No adapter-side image validation — whether the file decodes is the sourcing module's
  question, surfaced as `UnreadableImage` (ADR-0019/R1, ADR-0010, AC-008)
- G-5: Out of scope — no in-browser preview of the uploaded or generated image (CON-008),
  no client-side JavaScript
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

- **FR:** FR-017 (the uploaded-image half of its option surface), FR-003 (reached unchanged)
- **NFR:** NFR-003
- **ADR:** ADR-0020, ADR-0019, ADR-0021, ADR-0006, ADR-0010
- **Components:** COMP-008 (the multipart branch), COMP-003 (reached unchanged), COMP-002
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
