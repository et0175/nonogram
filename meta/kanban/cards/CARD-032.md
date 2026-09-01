# CARD-032: Ship a Unicode TTF as package data so a non-ASCII name prints in the PDF header

**Status:** review
**Priority:** P2
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/032-unicode-pdf-header-font
**Worktree:** ../PythonProject4-card-032
**Source:** meta/architecture/handoff.md#increment-6
**Idea:** —
**Wave:** 19
**Depends on:** —
**Touches:** src/nonogram/export/pdf.py, src/nonogram/export/fonts/, pyproject.toml, tests/test_export_pdf.py
**Review score:** —
**Started:** 2026-09-01T12:26:14Z
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

- **[Env]** forge 2026.8.17 (project requires >= 2026.8.17 — skew gate passed).
- **[Drift gate]** ⚠ `pyproject.toml` intersects unprocessed external drift in
  `meta/drift-pending.yml` (15 events). `drift.gate` defaults to `warn`, so this
  proceeds — but the packaging config this card edits may have been changed outside
  forge and not reconciled. Check `git log -- pyproject.toml` before editing it.
- **[Pre-flight, orchestrator]** The font does not exist anywhere on this machine —
  verified 2026-09-01: no DejaVu on disk, and Pillow bundles no TTF (`load_default()`
  returns an embedded ASCII-only face). It must be fetched from the DejaVu project.
  Network reachability to `raw.githubusercontent.com` was confirmed before this card
  started. Guardrail G-7 was added at the decompose station for this reason: the macOS
  font directories on this machine are full of Arial/Helvetica/Times, which are
  proprietary and must NOT be bundled.

### Implementation (2026-09-01)

- **[G-7 / font provenance]** `DejaVuSans.ttf` was fetched from the DejaVu
  project's own GitHub release, not from any system font directory:
  `https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2`
  (tarball sha256 `fa9ca4d13871dd122f61258a80d01751d603b4d3ee14095d65453b4e846e17d7`),
  and `ttf/DejaVuSans.ttf` extracted from it verbatim.
  - `src/nonogram/export/fonts/DejaVuSans.ttf` — 757,076 bytes, sha256
    `7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954`
  - `src/nonogram/export/fonts/LICENSE` — 8,816 bytes, sha256
    `7a083b136e64d064794c3419751e5c7dd10d2f64c108fe5ba161eae5e5958a93`,
    the tarball's own `LICENSE`, byte-identical to
    `raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/LICENSE`
    (fetched separately and diffed, as a second source for the same notice).
  - Nothing was copied out of `/System/Library/Fonts`, `/Library/Fonts` or
    `~/Library/Fonts`.
- **[Subsetting — considered, not done]** The card permits subsetting to cut the
  757 KB footprint. Not done, deliberately: `fontTools` is not installed and is
  not in the dependency baseline even as a dev extra, so subsetting would mean
  adding a build-time tool to save ~700 KB in a repository that already carries
  megabytes of sample images. It would also break the one cheap audit this card
  has — the shipped file's sha256 matching the upstream release exactly. Ships
  pristine.
- **[Packaging]** `pyproject.toml` gained only a `[tool.setuptools.package-data]`
  table (`"nonogram.export" = ["fonts/*.ttf", "fonts/LICENSE"]`). The
  `dependencies` list is untouched — the diff hunk does not reach it. Verified
  end to end rather than by reading the config: `pip wheel . --no-deps` produces
  a wheel containing `nonogram/export/fonts/DejaVuSans.ttf` (757,076 B) and
  `nonogram/export/fonts/LICENSE` (8,816 B).
- **[Loading]** `pdf._font_bytes()` reads the resource through
  `importlib.resources` (stdlib) and caches it; `pdf._header_font(size)` wraps
  those bytes in a `BytesIO` for `ImageFont.truetype`, cached per size. Bytes
  rather than a path so a zip/wheel import works; no host font path is ever
  consulted (asserted by
  `test_the_header_font_is_the_bundled_file_and_not_the_hosts`). A missing
  resource raises rather than falling back to `load_default()` — that fallback
  is the defect, and reinstating it silently would report success while
  printing tofu.
- **[G-2]** The header separator is still a stroked rule, not a set em dash,
  even though DejaVu Sans carries U+2014: only the face changes. The
  `_ELLIPSIS` constant likewise stays `"..."`. Both docstrings were rewritten,
  since their stated reason ("the bundled face is an ASCII subset") is no
  longer true and this codebase treats a false docstring as a defect.
- **[G-3]** `_filename_stem` / `_sanitized_component` untouched;
  `orchestrator.py` (G-5) and `sourcing/image.py` (G-4) untouched.
- **[Scope]** No `SCOPE+` entries. Everything landed inside the card's Touches:
  `src/nonogram/export/pdf.py`, new `src/nonogram/export/fonts/`,
  `pyproject.toml`, `tests/test_export_pdf.py`.
- **[Honesty about coverage]** The module docstring states plainly that the
  bundled font's own coverage is the new boundary and that Chinese, Japanese,
  Arabic and Hebrew names still render as tofu. No claim of full Unicode
  support anywhere.
- **[Tests]** Full suite: **1363 passed, 1 xfailed** (baseline 1354 + 1 xfailed;
  +9 from this card, one existing test renamed rather than added). New:
  `test_the_notdef_comparison_can_actually_tell_tofu_from_a_glyph`,
  `test_a_cyrillic_header_sets_the_letters_and_not_notdef_boxes` (4 params:
  к/о/т/é), `test_the_header_band_of_a_cyrillic_name_is_not_a_row_of_tofu`,
  `test_a_cyrillic_name_still_reaches_the_filename`,
  `test_the_font_ships_as_package_data_and_not_as_a_dependency`,
  `test_the_header_font_is_the_bundled_file_and_not_the_hosts`. Renamed:
  `test_the_bundled_font_cannot_set_an_em_dash` ->
  `test_the_separator_is_stroked_by_choice_now_rather_than_by_necessity`, which
  now asserts both halves (default face still lacks the em dash; bundled face
  has it) so neither claim in `_draw_header`'s docstring can go stale.
  `test_the_pdf_renderer_imports_pillow_and_nothing_third_party` gained the
  three new stdlib roots plus a second, list-independent assertion that every
  non-Pillow root is in `sys.stdlib_module_names`.
