# CARD-014: Two-page PDF export with answer key

**Status:** done
**Priority:** P2
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/014-pdf-export
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-2
**Idea:** —
**Wave:** 8
**Depends on:** CARD-010, CARD-012, CARD-013
**Touches:** src/nonogram/export/pdf.py, src/nonogram/export/__init__.py, src/nonogram/export/layout.py, src/nonogram/orchestrator.py, tests/test_export_pdf.py
**Review score:** 9.2 (cycle 1/3)
**Started:** 2026-08-29T00:30:00Z
**Closed:** 2026-08-29T06:00:00Z
**Actual:** 0.7d
**Merge commit:** 4a8f47c
**Blocked by:** —

## What to implement

A fifth renderer inside COMP-007, **not** a new component: CON-006 makes PDF a second sink
on the existing PNG raster path (trace.yml FR-016 note).

1. **Two pages.** Page 1: the blank puzzle with clues, i.e. exactly CARD-012's PNG raster.
   Page 2: the answer key — the same layout with the solution grid revealed. Both pages
   carry a header reading `<name> — <difficulty tier>` (the name from FR-015/CARD-011, the
   tier from FR-008/CARD-010).
2. **Assembly (ADR-0006, CON-006).** Render each page as a Pillow raster through CARD-012's
   `layout.py` + `png.py` path, then `save(..., save_all=True, append_images=[page2])`.
   Pillow's built-in PDF save is the whole mechanism — **no new dependency**, and ADR-0006's
   baseline is not reopened.
3. **Filename (ADR-0016).** The on-disk name is `<name>-<difficulty>.pdf`. Sanitize the
   puzzle name into a filesystem-safe slug (it can come from `--name` with arbitrary user
   input).
4. **Collision handling (ADR-0017).** On an existing file, append an incrementing suffix.
   That suffix search is export-path logic COMP-007 owns and must test — including the
   sequence beyond the first collision (`-1`, `-2`, ...) and the case where an intervening
   file appears.
5. **AC-048 — the INV-002 gate.** Same gate as AC-030: an unverified puzzle is refused and
   no PDF is written. Enforced in COMP-002, not COMP-007 (ADR-0007).

## Acceptance criteria

- **AC-046** (happy) — given a finalized, uniqueness-confirmed puzzle named `"cat"` with
  difficulty tier `"Medium"`, when it is exported as PDF, then a two-page PDF file is written
  to disk whose page 1 shows the blank grid with clues and a header reading `"cat — Medium"`.
  *test:* `TestExport_WritesPDFPageOneBlankWithHeader`
- **AC-047** (happy) — given the same finalized puzzle exported as PDF, when page 2 is
  inspected, then page 2 shows the revealed solution grid with the same `"cat — Medium"`
  header.
  *test:* `TestExport_WritesPDFPageTwoAnswerKeyWithHeader`
- **AC-048** (negative, INV-002) — given a puzzle that has not yet passed the uniqueness
  check, when PDF export is requested, then export is rejected and no PDF file is written,
  because the puzzle is not ready.
  *test:* `TestExport_RejectsUnverifiedPuzzleForPDF`

## Guardrails

- G-1: **No new third-party dependency.** PDF is the existing PNG raster path saved with
  Pillow's `save_all`/`append_images` (CON-006, ADR-0006). Do not add `reportlab`, `fpdf`,
  `weasyprint` or similar, and do not edit `pyproject.toml`'s dependency list
- G-2: Do not edit `src/nonogram/export/png.py`, `src/nonogram/export/svg.py`,
  `src/nonogram/export/csv_export.py` — CARD-012/013's deliverables. This card **reuses**
  the raster path; if it needs a change to be reusable, that is an escalation, not an edit
  (test: TestExport_WritesPNG, TestExport_WritesSVG)
- G-3: Do not edit `src/nonogram/solver/**`, `src/nonogram/clues.py`,
  `src/nonogram/sourcing/**`, `src/nonogram/difficulty.py` — export is additive on top of
  Increment 1 and must revert without touching the solver or the orchestrator's core
  generation logic (handoff Increment 2 Rollback)
- G-4: The INV-002 readiness gate stays in COMP-002 (ADR-0007, trace.yml FR-016 note) — do
  not duplicate the check inside `pdf.py`
- G-5: Collision handling never overwrites an existing file (ADR-0017) — the suffix search
  must be the only outcome, including when the base name is already taken several times over
- G-6: Out of scope — no interactive/playable output; the PDF is a static print artifact
  (CON-002). No embedded solver state or nudge metadata in the image exports
  (trace.yml FR-014 note)

## System contract

- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-016
- **NFR:** —
- **INV:** INV-002
- **CON:** CON-002, CON-006
- **ADR:** ADR-0006, ADR-0007, ADR-0016, ADR-0017
- **Components:** COMP-007 (Export Renderers), COMP-002 (readiness gate)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

[Follow-up from CARD-007 review, cycle 1 — **stale, kept for history**: this predates
CARD-011's stem consolidation; see below for current state.] `orchestrator.py`'s export
plumbing currently computes ONE filename stem for the whole run (`default_stem(mode)`, the
FR-015/AC-042 `<mode>-<timestamp>` convention) and passes it to `export.write()` per
format. ADR-0016 fixes the PDF filename as `<puzzle-name>-<difficulty>.pdf`, a different
convention. The plumbing already supports a per-call stem (`export.write(..., stem=...)`
takes it as an argument), so giving PDF its own stem is a change in `orchestrator.py`'s
call site, not in `export/` — don't be surprised to find the single-stem-for-all-formats
assumption baked in and needing a small generalization here.

### What was built (CARD-014 implementation)

**`src/nonogram/export/pdf.py` (new).** The fifth renderer. `render_pages(payload)` returns
`(puzzle_page, answer_page)` as Pillow `Image`s; `write_pdf` saves them with
`img1.save(path, format="PDF", save_all=True, append_images=[img2], resolution=300.0)`.
No new dependency (G-1) — `pyproject.toml` untouched, and a test now pins the runtime
dependency list to exactly `{pillow, numpy}` so "no new dependency" is asserted rather
than asserted-about-three-named-libraries.

Page 1 is **literally** `png.render_image(payload)` — CARD-012's raster, unmodified, with
the header band composited above it (a test asserts the page-1 pixels below the band are
byte-identical to `png.render_image`'s output). Page 2 is that image `.copy()`-ed with the
filled cells painted in, addressed by the same `origin + index * cell` arithmetic
`layout.py` used for the rules. `png.py`/`svg.py`/`csv_export.py` were **not** edited (G-2)
and needed no change to be reusable — CARD-012's decision to expose the `Image` rather than
only a file sink is exactly what made this a one-card renderer.

**`src/nonogram/export/layout.py`.** Added `HeaderBand` + `header_band(layout)` (+
`HEADER_BAND_MM = 12.0`, `HEADER_FONT_MM = 5.0`). Deliberately a *second* measurement laid
above a computed `Layout`, not a parameter of `compute_layout`: folding a header into
`compute_layout` would move `grid_top` and every clue centre for the PNG and SVG too, which
have no header. `compute_layout` is byte-for-byte unchanged, so CARD-012's output is
untouched.

**`src/nonogram/export/__init__.py`.** One registry row (`PDF: ExportFormat(PDF, ".pdf",
pdf.render)`) — the CLI picked the format up unedited, as the registry design promised.
`ExportPayload` gained two display fields, `name` and `difficulty`.

### Key design decisions

**Per-format stems (the generalization the stale note above anticipated).** The note above
predates CARD-011: `export_puzzle` no longer uses `default_stem(mode)`, it uses
`_filename_stem(puzzle)`. The single-shared-stem loop was generalized as follows:

* `_filename_stem(puzzle)` is still called **once** per run and stays the *base* stem. It is
  not recomputed per format on purpose — its unnamed-aggregate fallback reads the clock, so
  a run straddling a minute boundary would otherwise write `...-1429.json` next to
  `...-1430.png`.
* `_stem_for_format(format_name, *, base, tier)` decides what each format actually writes
  under: `base` for JSON/CSV/PNG/SVG, `f"{base}-{tier}"` for PDF only. ADR-0016 scopes its
  convention to PDF and explicitly leaves FR-011/FR-012's filenames alone, so this is one
  named exception rather than a per-format naming policy pushed into the registry.
* The sanitizer was **factored, not duplicated**: `_UNSAFE_STEM_CHARACTERS.sub(...).strip("-.")`
  moved out of `_filename_stem` into `_sanitized_component(text)`, which both the name and
  the tier suffix now go through — ADR-0016's "both components sanitized" by one rule, as
  `_filename_stem`'s own docstring asked for.
* Tier spelling: the **filename** takes `Tier.value` (`cat-medium.pdf`, ADR-0016's own
  `cat-hard.pdf` example), the **header** takes `Tier.label` (`"cat — Medium"`, AC-046).
  `Tier` being a `StrEnum` is what lets those be one string apart with no lookup table.
* An unscored aggregate (`difficulty_tier is None`) keeps the bare name — `cat.pdf`, never
  `cat-.pdf`/`cat-None.pdf`.

**Collision handling was reused, not rebuilt (ADR-0017, G-5).** `export.write` →
`_free_path` already implements the `-1`, `-2`, ... search CARD-007 built, and it asks the
filesystem on every candidate rather than remembering a counter. PDF inherits it by being a
registry row; this card added **no** collision code, only tests for it on the PDF path —
the sequence past the first collision, and a file appearing in between (the second export
lands on `-2` and the intruder's bytes are intact).

**The readiness gate stayed put (G-4, AC-048/INV-002).** `export_puzzle`'s existing
`puzzle.require_ready_for_export()` covers PDF for free. `pdf.py` contains no readiness
check, pinned by a source-level test (the same guard `test_export_image.py` applies to
`png`/`svg`).

**The header separator is a stroked rule, not a glyph.** Pillow's bundled default face
(`ImageFont.load_default(size=...)`) is an **ASCII subset**: `"—"` (U+2014) sets as a
`.notdef` box, so a naive `draw.text("cat — Medium")` would put a tofu box in the middle of
every PDF this tool produces. Since an em dash *is* a horizontal rule, `_draw_header` draws
it as one — no glyph, no second font, no dependence on the host's font stack (which
`png._clue_font` documents as a rule). `pdf.header_text(payload)` still returns the literal
AC-046 string `"cat — Medium"`. A test pins the font gap so nobody "simplifies" the header
drawing back into a single `draw.text` call.

**The header always fits the page.** `--name` is arbitrary user text (AC-045 only forbids
blank) and a small puzzle's page is narrow, so an over-wide header is set smaller (down to
a third of the nominal size) and, if it still does not fit, the name is elided with `...`
rather than run off both edges.

### Scope notes / findings

1. **Three pre-existing tests outside `Touches:` had to change** (the established
   hand-on pattern each format card has performed): `pdf` was the stand-in for "a format
   this build does not have" in `tests/test_cli.py` (`format-not-registered`) and twice in
   `tests/test_export_json.py` (`for_format("pdf")` raises; argparse rejects `--export pdf`)
   — exactly as `png` was until CARD-012 and `csv` until CARD-013. PDF is the last planned
   format, so the stand-in is now `xlsx`, a format the tool deliberately does not have
   (FR-012 answers the spreadsheet case with CSV). No behaviour was changed, only the
   placeholder format name.
2. **Finding (not fixed here, CARD-012's file):** `tests/test_export_image.py`'s
   `test_the_png_contains_the_clues` asserts `crop(...).getbbox() is not None`. On an
   ink-on-**white** RGB image that is vacuously true (white is non-zero), so the assertion
   cannot fail — the gutters are never actually checked for ink. This card's own tests use
   an explicit `_has_ink` (`convert("L").getextrema()[0] < 128`) instead. Editing
   `test_export_image.py` was out of scope; worth a follow-up card.
3. **Finding:** `README.md` still says "no export writer, so `--export` is ..." — stale
   since CARD-007 and now four formats out of date. Left alone (docs are `forge:readme`'s).
4. **Known limitation:** CARD-011 keeps Unicode names verbatim (`кот`, `café`, `日本語`), but
   the only font the Pillow-only baseline can guarantee is that ASCII subset, so a non-ASCII
   *name* sets as `.notdef` boxes in the PDF header. Fixing it means either a font
   dependency (reopens ADR-0006/G-1) or shipping a font file, so it is flagged rather than
   decided here. The filename is unaffected — sanitization is Unicode-aware and the file is
   still `кот-medium.pdf`.
5. Pillow's PDF writer stamps `/Title` with the output filename stem and a creation date.
   No solver state, nudge metadata or interactive layer is embedded (G-6).

### Test run

`./.venv/bin/python -m pytest`: **1045 passed, 1 xfailed**, from a 1003-passed/1-xfailed
baseline. The delta is 41 new tests in `tests/test_export_pdf.py` plus one extra
parametrization of the existing `test_every_registered_format_is_accepted_by_the_cli` (it
iterates `export.FORMATS`, now five formats). The pre-existing AC-037 xfail
(`tests/bench_generate.py::test_20x20_p95_is_under_5s`, tracked by CARD-018) is unchanged
in status and reason. No regressions.

### Orchestrator notes

- **[Scope]** Touches match predicted plus three explicitly-flagged pre-existing
  test edits (`tests/test_cli.py`, `tests/test_export_json.py` — placeholder
  unregistered-format name `"pdf"` → `"xlsx"`, since PDF is now real; no
  behaviour changed). No silent creep.
- **[Build gate]** PASSED (full, independently re-run by orchestrator in a
  fresh venv: 1045 passed, 1 xfailed, exit 0; AC-037 xfail unchanged in
  status and reason). `pyproject.toml` confirmed untouched (G-1).
- **[Review 1/3] 9.2/10 — PASS.** Report:
  `meta/review/20260829T054400Z-CARD-014-cycle1.yml`. All 8 judgment points
  independently re-verified against the actual bytes, not just the tests —
  including decoding the emitted PDF and diffing the embedded raster.
  **Explicit ruling on the em-dash-as-rule header (point 6): legitimate,
  satisfies AC-046/047's literal wording, not a finding.** Pillow's bundled
  font genuinely cannot set "—" (verified: identical bitmap to an
  unassigned codepoint), and every alternative either fails the AC's
  literal string, substitutes a different character, or reopens G-1/ADR-0006
  — stroking the em dash as the rule it typographically is was ruled the
  only route *to* AC-046, not a workaround around it. Zero Critical/Important
  findings. Four Minor: (F-001) non-ASCII `--name` renders as tofu boxes in
  the PDF header — deliberately not escalated to Important since every
  in-card fix breaks a guardrail, but needs a **user decision**, not left
  to die in worktree notes; (F-002) PDF pages are content-sized not
  literally A4 despite a docstring/test name implying otherwise (harmless,
  doc-only mismatch); (F-003) Pillow saves pages as lossy JPEG internally,
  measurable pixel drift on white background (invisible at print size, no
  AC/NFR governs it); (F-004) one test's docstring claims more than its
  assertion checks (a rule "between" the header halves — only checked that
  the two halves differ, not that the rule sits between them). Merging.
