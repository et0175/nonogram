# CARD-031: Image-mode puzzles auto-name from the source file's stem

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/031-image-mode-name-from-file-stem
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** CARD-027
**Touches:** src/nonogram/orchestrator.py, tests/test_naming.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`NameContext._auto_name` currently returns the library key for library-sourced puzzles
(AC-043) and otherwise falls through to `export.default_stem`'s
`<mode>-<YYYY-MM-DD>-<HHMM>`. Add the image-mode arm: an image-sourced puzzle with no
`--name` auto-names from the **source file's stem**, exactly as the library arm names from
its key. `cat.png` yields `cat`.

Mirror the existing library arm rather than inventing a parallel mechanism — including its
collision posture: ADR-0016 already states an auto-generated key like `"cat"` is not
guaranteed unique, and ADR-0017's export-time suffix is what resolves a collision. Two
puzzles from the same picture are two renderings of one picture, not a same-minute
accident, so they should behave exactly like two `"cat"` library puzzles do today.

A missing or unreadable file still falls through to the timestamp name, exactly as a
missing library key does — the run then fails in sourcing with the error that request
deserves, not a naming error.

## Acceptance criteria

- **AC-090** (happy) — test: `TestPuzzleName_AutoGeneratesFromImageFileStem`
  - **given** an image-mode generation request uploading a file named "cat.png" with no --name flag
  - **when** the puzzle is created
  - **then** the puzzle's name is auto-generated as "cat", not the "image-2026-09-01-1240"-shaped mode+timestamp default

## Guardrails

- G-1: AC-043's library-key naming is unchanged (test: `TestPuzzleName_UsesLibraryKeyVerbatim`)
- G-2: AC-042's `<mode>-<date>-<time>` default still applies to random mode, and to image
  mode when the stem is unusable (test: `TestPuzzleName_AutoGeneratesModeTimestamp`)
- G-3: AC-044/AC-045 unchanged — an explicit `--name` is still kept verbatim and an empty
  one still rejected inward of argparse. This card changes only the *auto-generated* default.
- G-4: Filename sanitization is untouched. `_filename_stem` is already Unicode-aware and
  passes `кот` through verbatim; a Cyrillic stem must keep reaching the filesystem
  unmangled. How such a name RENDERS in the PDF header is CARD-032's, not this card's.
- G-5: Do not edit `src/nonogram/sourcing/image.py` — owned by CARD-030 this wave
- G-6: Do not edit `src/nonogram/export/**` or `pyproject.toml` — owned by CARD-032
- G-7: Out of scope — the `<name>-<WxH>-<difficulty>.pdf` filename shape is DEC-026, held
  open until CARD-027 merges.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
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

- **FR:** FR-015
- **NFR:** —
- **ADR:** ADR-0016, ADR-0017, ADR-0018
- **Components:** COMP-002
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
