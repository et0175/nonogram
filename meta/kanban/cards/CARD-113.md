# CARD-113: Pin today's A4 output byte for byte before any PageSpec change (golden A4 tripwire)

**Status:** done
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/113-golden-a4-tripwire
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-13 (first card — "the golden-byte test lands first, on the commit before any geometry change")
**Idea:** —
**Wave:** 20
**Depends on:** —
**Touches:** tests/test_export_a4_golden.py, tests/fixtures/a4_golden/**, tests/property/test_cli_exports_byte_identity.py
**Review score:** 9.0 (cycle 1/3)
**Started:** 2026-09-22T15:26:35Z
**Closed:** 2026-09-22T16:06:44Z
**Actual:** 0.1d
**Merge commit:** 365a7ff
**Blocked by:** —

## What to implement

Increment 13 opens with a tripwire, not a feature. ADR-0036 is about to give
`compute_layout` an optional `PageSpec` (CARD-114). CON-019 and ADR-0036/R1 require
that the CLI and web UI output does not change **by a single byte**. This card pins that
output on `main` as it is today, **before any `src/` edit**, so the next card has
something to be checked against from its first commit.

This card changes tests and fixtures only.

1. **`TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`** (ADR-0036/R1's check ref).
   Take a fixed corpus of clue sets: the seeded 30×30 of AC-180 and a spread of extents
   and clue patterns across 10..30 that exercise both NFR-006 orientations and both
   NFR-005 regimes (cap-bound and page-fit-bound). Serialize `compute_layout(row, col)`
   deterministically (every field of `Layout`, including every `GridLine` and every
   `ClueEntry`) and store the result under `tests/fixtures/a4_golden/`. The test
   compares the live output to the golden file. The fixture is **generated once, from
   `main` at this card's base commit**. Say in the fixture header how it was generated
   and from which commit, and record the regeneration command in the test docstring.
   Regenerating the fixture is never how a red test gets fixed.
2. **`TestCliExports_ByteIdenticalAfterBookGeometry`** (AC-180). Run `nonogram generate`
   (or its in-process equivalent) for a seeded 30×30 request (seed 42) to PNG, SVG and
   PDF. Compare SHA-256 digests to golden digests stored in the same fixture tree. If
   the PDF embeds a creation timestamp, check first whether the PDF sink is already
   deterministic, and record what you found. If it is not deterministic, pin the
   deterministic part and say so explicitly. Do not change `src/` to make it
   deterministic in this card (that would be a `src/` change before the tripwire).
3. **`PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`** (EC-020, CON-019's
   check ref). Use a seeded corpus built with stdlib `random.Random`, following the
   repo's property-test style (no hypothesis). Cover at least 60 CLI requests across
   extents 10..30, densities and seeds. Store golden digests for PNG, SVG and PDF, and
   assert a minimum case count inside the test so the corpus cannot silently shrink.
   Include at least one web-UI export path (COMP-008 goes through the same export sink,
   and CON-019 names the web UI too).
4. Show that the tripwire is live. Mutate one constant in `export/layout.py` (for
   example `PAGE_MARGIN_MM`) locally, watch all three tests fail, then revert. Record
   the result in Worktree notes. The mutation is never committed.

Checkpoint slice (Increment 13): "The golden A4 test is green on both sides of the
change, and a seeded 30×30 `nonogram generate` writes byte-identical PNG/SVG/PDF before
and after." This card provides the "before" side. CARD-114 must keep it green.

## Acceptance criteria

- **AC-180** — given a fixed 30x30 puzzle request (seed 42) exported by `nonogram generate` as PNG, SVG and PDF on the commit before the book geometry lands, when the same request is exported after it lands, then all three files are byte-identical to the earlier ones.
  *test:* `TestCliExports_ByteIdenticalAfterBookGeometry`

## Engineering constraints

- **EC-020** (compatibility) — For any CLI generation request, the PNG, SVG and PDF files written are byte-identical whether or not the book geometry exists — the book's page size and margins never reach the CLI's layout (CON-019), under whichever alternative the geometry DEC selects.
  *test:* `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
- EC(ADR-0036/R1): `compute_layout` called without a PageSpec produces exactly today's A4 geometry, pinned field by field against a golden generated from this card's base commit.
  *test:* `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden`

## Guardrails

- G-1: Do not edit `src/**` — this card is tests and fixtures only. The tripwire must land on the commit *before* any geometry change (handoff Increment 13; ADR-0036/R1).
- G-2: Do not edit `src/nonogram/admin/book_plan.py` or `tests/test_book_plan.py` / `tests/property/test_book_plan.py` / `tests/property/test_longest_side_buckets.py` — they belong to CARD-119 in this wave.
- G-3: The golden fixtures are captured from today's code. Never regenerate them to turn a failing test green; a red golden test means the change broke CON-019.

## System contract

- ADR-0036/R1 — compute_layout called without a PageSpec produces exactly today's A4 geometry; CLI and web output are byte-for-byte unchanged by any book-only PageSpec field. (check: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden)
- ADR-0036/R2 — Book page geometry is computed only by COMP-007's layout functions (compute_layout, and the pair-aware call for two-up pages) with the book's PageSpec; the admin panel does not fit cells or place grid lines itself. (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the … (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form … (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This … (check: PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an … (check: PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)

## Architecture context

- **FR:** FR-030 (AC-180 only)
- **NFR:** —
- **CON:** CON-019
- **ADR:** ADR-0036
- **Components:** COMP-007
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

- [Env] forge 2026.8.17 (no meta/.skills.yml — version gate not configured)
- **Scope:** tests and fixtures only; no `src/` edit (G-1), no CARD-119 file touched (G-2). No SCOPE+.
  New files: `tests/test_export_a4_golden.py`, `tests/property/test_cli_exports_byte_identity.py`,
  `tests/fixtures/a4_golden/{__init__,golden,regenerate}.py`, `tests/fixtures/a4_golden/{layout,cli_exports}.json`.
- **Base commit of the goldens:** `89ed292add4c2da3678a932e3be8b0931db944fb` (recorded in each JSON's `_header`,
  with Python 3.14.3 / Pillow 12.3.0). `regenerate.py` refuses to run while `src/` is dirty, so a golden always names a real commit.
- **Regeneration command** (never how a red test is fixed, G-3):
  `./.venv/bin/python -m tests.fixtures.a4_golden.regenerate --capture-from-clean-src` (from the repo root).
- **Test-ref mapping:** `TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden` (class, 61 parametrised clue sets + a coverage gate:
  both NFR-006 orientations, both NFR-005 regimes classified against literal comfort points, 10..30 on both axes, AC-180's 30x30);
  `TestCliExports_ByteIdenticalAfterBookGeometry` (class, AC-180); `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`
  -> module-level `test_property_cli_exports_…` / `test_property_web_ui_exports_…` / corpus gate, per the repo's property convention.
- **PDF determinism finding:** the PDF sink is NOT byte-deterministic. Pillow's `PdfImagePlugin._save` stamps
  `/CreationDate` and `/ModDate` from `time.gmtime()` at save time; Pillow 12.3.0 honours no `SOURCE_DATE_EPOCH`, and `src/` passes no
  override. Measured: two identical runs a minute apart differ only in those two `D:YYYYMMDDHHMMSSZ` values. Pinned part: the test zeroes
  exactly those two fields (length-preserving, so xref offsets stay pinned) and digests the rest; it fails if either field is not found
  exactly once. PNG and SVG are byte-deterministic and are digested as written. Recommendation for a later card (not this one): pass fixed
  `creationDate`/`modDate` in `pdf.write_pdf` if full-byte PDF determinism is wanted.
- **Other determinism facts:** (1) every pinned request passes `--name`, because the default name is `random-<YYYY-MM-DD-HHMM>` off the
  wall clock and lands in both the filename and the PDF header; (2) AC-180 names no density and the CLI requires one — 60 is used;
  (3) the EC-020 corpus draws densities from 55..90 only: below ~50% random 20x20+ grids hit the 30 s `GENERATION_BUDGET_SECONDS`
  (measured 5/80 abandoned at 40..80%), so success depends on host speed, not the request.
- **EC-020 corpus:** 72 seeded CLI requests (seed 20260922; floor 60 asserted in-test), 10..30 on both axes incl. the 4 corners,
  bare-N and WxH tokens; 6 of them are also POSTed through a real loopback web UI server and must match the CLI's golden digests.
- **Tripwire liveness (item 4):** set `PAGE_MARGIN_MM = 12.5` in `src/nonogram/export/layout.py` locally -> all three tests red:
  61/61 layout cases (`margin: golden 142, now 148`, …), AC-180 (`PNG is not byte-identical`), EC-020 CLI (216/216 exports changed) and
  web (18/18). Reverted with `git checkout -- src/nonogram/export/layout.py`; `git status --porcelain src/` empty. Never committed.
- **Fixture size:** `layout.json` ~330 KB (full serialization of every GridLine/ClueEntry, one case per line), `cli_exports.json` ~30 KB (digests).
- **Env note:** the venv's editable install is a plain `.pth` path to the main repo; pytest's `pythonpath=["src"]` precedes it, verified
  `nonogram.__file__` resolves under this worktree during the run. The CLI is exercised in-process via `nonogram.cli.main`.
- [Scope] tests/fixtures/a4_golden/__init__.py, tests/fixtures/a4_golden/cli_exports.json, tests/fixtures/a4_golden/golden.py, tests/fixtures/a4_golden/layout.json, tests/fixtures/a4_golden/regenerate.py, tests/property/test_cli_exports_byte_identity.py, tests/test_export_a4_golden.py
- [Build gate] impact underivable (no pytest-testmon) — full suite
- [System contract] fresh lens = card section (7 rules, no drift)
- [Build gate] PASSED (full, 131s; narrowed: 1 pre-existing failure excluded — tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied fails identically on main 89ed292 (admin UI, unrelated; card touches no src/). Implementation run: 3774 tests — 3747 passed, 26 skipped, 1 failed (that one))
- [Scope gate] cycle 1: IN_SCOPE — 7/7 files under Touches globs; 0 guardrail hits (src/**, CARD-119 files)
- **Full suite (after commit 4719d13):** 3774 tests, 3747 passed, 26 skipped (DB), 1 failed —
  `tests/e2e/test_admin_workflow.py::TestFlow2BatchImageUpload::test_size_configuration_applied`. That failure is in the admin
  panel and was already there: it expects the text "Fixed" in an admin page, it imports none of this card's files, and `src/` is
  unchanged. The card's own tests run 66/66 green in about 13 s.
- [Review 1/3] Score: 9.0 — crit: 0, imp: 0
- [Review sync] 51 report(s) → meta/review/
- [Review 1/3] Score: 9.0 ✓ threshold reached + no critical/important (5 Minor: F-001 Pillow-version context in digest failures, F-002 pin GOLDEN_BASE_COMMIT, F-003 temp-dir churn ~55MB/run, F-004 circular web-slice floor, F-005 private helpers from test_web_server.py; O-001 follow-up: deterministic PDF dates in pdf.write_pdf; O-002 CON-019/AC-180 wording vs PDF timestamps). Owner questions: PDF date-blanking judged ACCEPTABLE (exactly 2 fields, exactly once, length-preserving; card permits); layout.json 336KB judged PROPORTIONATE (field-level diagnosability)
- [8h spot-check] 1/1 sampled holds reproduced (ADR-0036/R1 — 66 passed; src diff empty; golden headers = merge-base 89ed292)
- [Adversarial] no gating findings in cycle 1 — nothing to verify
- [AC/EC check] All criteria/constraints ✓ (evidence):
  AC-180 ✓ demonstrated — evidence: TestCliExports_ByteIdenticalAfterBookGeometry::test_seeded_30x30_writes_the_golden_png_svg_and_pdf PASSED (PNG/SVG raw SHA-256; PDF after zeroing /CreationDate+/ModDate only, length-preserving, exactly-once — within card item 2's allowance)
  EC-020 ✓ demonstrated — evidence: test_property_cli_exports_byte_identical_whatever_the_book_geometry + web_ui companion + corpus gate PASSED (72 seeded cases, floor 60 asserted; densities 55..90 = deterministic regime)
  EC(ADR-0036/R1) ✓ demonstrated — evidence: TestLayout_DefaultPageSpecIsByteIdenticalToA4Golden 61/61 PASSED + coverage gate PASSED
  G-1 ✓ demonstrated — evidence: git diff main...HEAD -- src empty; add-only diff
  G-2 ✓ demonstrated — evidence: no book_plan / longest_side_buckets paths in diff
  G-3 ✓ demonstrated — evidence: golden headers = merge-base 89ed292; fixtures added in exactly one commit (4719d13)
- [Docs] a4_golden/ purpose, PDF-timestamp normalization and regeneration rule are documented in golden.py/regenerate.py module docstrings and the JSON _header; no sibling fixture dir carries a README — none added (current)
- [Commit] no changes after cycle 1 (no fixes applied; minors F-001..F-005 left as recorded) — /commit had nothing to stage outside meta/; success commit = implementation commit 4719d13 (card/113-golden-a4-tripwire). Ready for done/merge.
- [Follow-up suggested] O-001: make pdf.write_pdf deterministic (fixed creationDate/modDate) after CARD-114; O-002: record the PDF-timestamp reading of byte-for-byte in CON-019/AC-180 (architect delta). F-001/F-002 cheap hardening worth doing before CARD-114 relies on the tripwire.

- [Done] merged 365a7ff (--no-ff). Merge gate: main unchanged since the branch base 89ed292, so the full-suite build gate of this exact tree (3747 passed / 1 pre-existing failure test_size_configuration_applied, also red on 89ed292) stands in for the rebase-gate run. Deferral scan: 1 hit, incidental (docstring about a later card). Trace: FR-030/CON-019 already list the evidence tests; FR-030 stays partial (open cards).
- [Owner] 2026-09-22 — confirmed: CON-019 means byte-identical except the two PDF timestamps (/CreationDate, /ModDate). Queued for the architect as raw-requirements delta 2026-09-22 (e).
