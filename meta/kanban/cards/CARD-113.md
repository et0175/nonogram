# CARD-113: Pin today's A4 output byte for byte before any PageSpec change (golden A4 tripwire)

**Status:** ready
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
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
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
