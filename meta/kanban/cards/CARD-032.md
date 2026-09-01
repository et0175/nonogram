# CARD-032: Ship a Unicode TTF as package data so a non-ASCII name prints in the PDF header

**Status:** ready
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/032-unicode-pdf-header-font
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** —
**Touches:** src/nonogram/export/pdf.py, src/nonogram/export/fonts/, pyproject.toml, tests/test_export_pdf.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Bundle a Unicode TTF as **package data** and use it for PDF header text instead of
`ImageFont.load_default()`.

The defect is verified, not assumed: Pillow bundles no TTF at all and `load_default()`
returns an ASCII-only face, so `к`, `о`, `т` and `é` each render a bitmap byte-identical
to an unassigned codepoint while `c` renders correctly. Filenames were never affected —
the sanitizer is already Unicode-aware — so the failure is confined to header text, which
is why it sat unnoticed from 2026-08-29 until now.

Font: **DejaVu Sans** (Bitstream Vera-derived licence, redistribution and bundling
explicitly allowed), for Latin + Cyrillic + Greek in one widely-vetted file. Subsetting to
the covered scripts is permitted to cut the install footprint — subsetting tools are
build-time, not runtime. Ship the licence notice with it; that obligation is real and new.

**This is package data, NOT a dependency.** `pyproject.toml`'s `dependencies` list must not
gain an entry; what changes is the package-data configuration that makes the file install
correctly from the src-layout. ADR-0006/R1 is the standing rule that draws this line, and
this card is its first implementation.

**What this does not fix, and must not claim to.** The bundled font's own coverage becomes
the new boundary. A name in a script it does not cover — Chinese, Japanese, Arabic, Hebrew
— reproduces the identical tofu failure one layer down. This card shrinks the failing set;
it does not eliminate it. Say so in the module docstring rather than implying full Unicode
support.

## Acceptance criteria

- **AC (card-local — this is an ADR-0006 revision with `Migration: rewrite`, so no FR
  carries it; see the Architecture context note)** — test: `TestPdfHeader_RendersCyrillicName`
  - **given** a puzzle named `кот` exported to PDF
  - **when** the header is rendered
  - **then** the Cyrillic glyphs render as themselves, not as `.notdef` boxes — asserted by
    comparing the rendered bitmap against an unassigned codepoint's and requiring them to
    DIFFER, the same technique that verified the defect on 2026-09-01
- **AC (card-local)** — test: `TestPdfHeader_CyrillicNameStillReachesTheFilename`
  - **given** the same puzzle
  - **when** the export filename is produced
  - **then** it is still `кот-...`, unchanged — the sanitizer's Unicode behaviour is
    untouched by this card

## Engineering constraints

- **EC(ADR-0006/R1):** the installed runtime dependency set remains exactly stdlib +
  Pillow + NumPy. A bundled non-executable asset is not a dependency change, and nothing in
  this card adds an `install_requires` entry.
  test: `TestDependencyBaseline_IsExactlyPillowAndNumpy`

## Guardrails

- G-1: `pyproject.toml`'s `dependencies` list is unchanged (ADR-0006/R1;
  test: `TestDependencyBaseline_IsExactlyPillowAndNumpy`)
- G-2: The two-page PDF structure, the answer key, and the `<name> — <tier>` header
  composition are unchanged — only the face the text is drawn with changes
  (test: `TestExportPdf_HasPuzzleAndAnswerKeyPages`)
- G-3: `_filename_stem` and the sanitizer are not touched — filenames already handle
  Unicode correctly and this card must not disturb that
- G-4: Do not edit `src/nonogram/sourcing/image.py` — owned by CARD-030
- G-5: Do not edit `src/nonogram/orchestrator.py` — owned by CARD-031
- G-6: Out of scope — the `<name>-<WxH>-<difficulty>.pdf` filename shape is DEC-026, held
  open until CARD-027 merges.

## System contract

- ADR-0006/R1 — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-party package joins the installed dependencies without revising this ADR. Non-executable static asse... (check: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no doma... (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No public function signature, request field, or export field reduces a grid's extent to a single scalar "si... (check: review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height fields. No export format writes a scalar "size" field, and no decoder reconstructs a grid's dimensions ... (check: review-lens)
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

- **FR:** — (an ADR revision with `Migration: rewrite`; no FR obliges this work, which is
  exactly why the migration marker is what gets it scheduled at all)
- **NFR:** —
- **ADR:** ADR-0006 (revised 2026-09-01 — this card is its migration), ADR-0016
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
