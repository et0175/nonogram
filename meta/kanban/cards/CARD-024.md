# CARD-024: Export metadata carries width and height at schema version 2

**Status:** review
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/024-export-extent-schema-v2
**Worktree:** ../PythonProject4-card-024
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 16
**Depends on:** —
**Touches:** src/nonogram/export/__init__.py, src/nonogram/export/json_export.py, src/nonogram/export/csv_export.py, src/nonogram/orchestrator.py, tests/test_export_json.py, tests/test_export_csv.py, tests/property/test_export_roundtrip.py
**Review score:** 6.0 (cycle 1/3, failed gate), 9.0 (cycle 2/3) — gate passed; F-201..F-203 closed in 427d6ff
**Started:** 2026-08-31T16:14:49Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Today both structured export formats record grid extent as a single `size` integer, which
cannot express a rectangle: `json_export.document`'s `"size"` key and `csv_export`'s
`_META_KEYS` entry `"size"`. ADR-0023 replaces that scalar with a **width/height pair** in
both formats and bumps both schemas to **version 2**.

This card is **deliberately independent of the request-side extent pair (CARD-027)**. It
changes the export payload and the two file formats only, and it is verified end to end
without a rectangular request, because the export layer takes an `ExportPayload` rather
than a `Puzzle` — every existing test in `tests/test_export_json.py`,
`tests/test_export_csv.py` and `tests/property/test_export_roundtrip.py` already
constructs payloads directly. A 30x12 payload is therefore constructible today, which is
exactly what AC-060 and AC-061 need.

Concretely:

1. **`src/nonogram/export/__init__.py`** — `ExportPayload.size: int | None` becomes
   `width: int | None` and `height: int | None`, with the docstring's "The requested edge
   length" replaced by the pair's meaning. The ADR-0015 provenance rationale ("recorded as
   *asked for*, alongside the seed, so the request can be replayed exactly") carries over
   to both fields unchanged.
2. **`src/nonogram/export/json_export.py`** — `SCHEMA_VERSION = 2`. The `"size"` key in
   the request block becomes `"width"` and `"height"`; `parse` reads both. The version
   comparison stays an exact `!=` that raises naming both versions (ADR-0023/R2) — that
   code already does the right thing; do not loosen it.
3. **`src/nonogram/export/csv_export.py`** — `SCHEMA_VERSION = 2`. `_META_KEYS` becomes
   `("version", "seed", "mode", "width", "height", "density")` — six keys, all required,
   no others accepted (the `unknown key` refusal is what makes the CSV decoder strict where
   JSON's is lenient about extra keys; keep it). `None` still writes as an empty value and
   reads back as `None`, for both new keys.
4. **`csv_export.py`'s module docstring is normative and must move with the code.** It
   documents the `#meta` layout literally, including a worked `size,4` example and the
   sentence "all five keys required and no others accepted". A docstring left describing the
   version-1 key set is a defect here, not a cosmetic omission — it is the specification a
   reader will follow. Same for `json_export.py`'s docstring wherever it names the key set
   or the version.
5. **`src/nonogram/orchestrator.py`** — the single `export.ExportPayload(...)` construction
   (~line 1157) passes `width=` and `height=`. Until CARD-027 lands, the request still
   carries a scalar, so both take the same value; CARD-027 flips the source of those two
   values to the request's pair and touches nothing else in this file for this reason.
6. **Fixtures.** Both formats' round-trip fixtures carry `size` in their `#meta` /
   `request` blocks. All of them move to the new key set — including the property corpus's
   payload factory in `tests/property/test_export_roundtrip.py:127` and
   `tests/test_export_csv.py:72`'s `_payload(**defaults)` helper.
7. **A version-1 document is refused, not migrated.** Add the explicit negative test: a
   file (JSON and CSV) declaring `version: 1` is rejected with an error naming both the
   file's version and the decoder's own. No compatibility read path, no upgrade shim
   (ADR-0023/R2, G-3).

## Acceptance criteria

- **AC-060** (FR-012)
  - given: a finalized 30x12 puzzle exported as JSON
  - when: that JSON is decoded back
  - then: the decoded puzzle has width 30 and height 12, both read from the file's
    metadata rather than inferred as a square
  - kind: boundary
  - test: `TestExport_JSONRoundTripsRectangularDimensions`
- **AC-061** (FR-012)
  - given: a finalized 30x12 puzzle exported as CSV
  - when: that CSV is decoded back
  - then: the decoded puzzle has width 30 and height 12, both read from the file's
    metadata rather than inferred as a square
  - kind: boundary
  - test: `TestExport_CSVRoundTripsRectangularDimensions`
- **AC-031 / AC-032 / AC-033** (FR-012, regression) — the existing JSON/CSV write and
  exact-round-trip criteria for square puzzles keep holding; only the metadata key set and
  the version number move.
  tests: `TestExport_WritesJSON`, `TestExport_WritesCSV`, `TestExport_JSONRoundTripsExactly`

## Engineering constraints

- **EC-002** (FR-012, verbatim from requirements.yml)
  - statement: For any finalized puzzle, decoding its exported JSON or CSV representation
    reproduces the exact original solution grid and clues.
  - kind: consistency
  - instances: AC-033
  - test: `PropertyTest_Export_RoundTripsExactlyForAnyPuzzle`

  The existing corpus in `tests/property/test_export_roundtrip.py` must gain rectangular
  payloads: a corpus of squares can no longer discharge this property, because the very
  thing that could break fidelity now is a decoder that reconstructs one dimension from
  the other. The file's own corpus gate
  (`test_the_corpus_covers_what_ec_002_asks_for`) must be extended to assert a minimum
  count of non-square cases, so the corpus cannot silently shrink back to squares.

- **EC(ADR-0023/R1):** For every payload this project can produce, both export formats
  write the grid's extent as two separate metadata fields, and each decoder reads both
  from the file — neither format writes a scalar `size`, and neither decoder reconstructs
  a dimension it did not read.
  test: `PropertyTest_Export_MetadataCarriesBothDimensionsForAnyPuzzle`

- **EC(ADR-0023/R2):** For every version value a document can declare other than the
  decoder's own `SCHEMA_VERSION`, both decoders refuse it by exact comparison and raise an
  error naming both the file's version and their own — never a best-effort read of an
  older document.
  test: `PropertyTest_Export_RejectsEveryVersionOtherThanItsOwn`

## Guardrails

- G-1: Do not edit `src/nonogram/export/layout.py`, `src/nonogram/export/png.py`,
  `src/nonogram/export/svg.py`, `src/nonogram/export/pdf.py`, `tests/test_export_image.py`,
  `tests/test_export_pdf.py` — the raster/vector renderers already derive extent from the
  clue sets rather than from a size parameter and need no change; `layout.py` is owned by
  CARD-025 this wave.
- G-2: Do not edit `src/nonogram/sourcing/**`, `src/nonogram/difficulty.py`,
  `tests/test_timeout.py`, `tests/test_sourcing_random.py`,
  `tests/test_sourcing_library.py`, `tests/test_sourcing_image.py` — owned by CARD-023
  this wave.
- G-3: A version-1 document is REFUSED, not migrated. Do not add a compatibility read
  path, a best-effort decode, a `version in (1, 2)` acceptance, or an upgrade shim. The
  rollback story for this increment is "revert the branch"; no data is rewritten in place
  (test: TestExport_RejectsSupersededSchemaVersion).
- G-4: The exact-round-trip behaviour of AC-031/AC-032/AC-033 for square puzzles is
  unchanged in substance — the grid and clue payloads, ADR-0012's boundary types, and
  ADR-0015's provenance-fields-checked-separately discipline all stay as they are (test:
  TestExport_JSONRoundTripsExactly).
- G-5: `csv_export.py`'s module docstring is the normative description of the `#meta`
  format, worked example included; `json_export.py`'s is the same for its document shape.
  Both move with the code in this card. Shipping a docstring that documents version 1 is a
  finding, not an omission.
- G-6: Out of scope — do not introduce a `(width, height)` pair on `GenerationRequest`, on
  the CLI's `--size`, or in any source mode; and do not touch `MAX_SIZE`/`MIN_SIZE`. This
  card changes the export payload and the two file formats only. The request-side extent
  pair is CARD-027's (FR-018), the range narrowing is CARD-023's (CON-011).

## System contract

- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its
  current solution grid (US-004, FR-005). (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has
  confirmed exactly one solution (US-005, FR-011). (check:
  TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate attempts for random/library
  mode, resample attempts for difficulty matching, or pixel-nudge attempts for image
  mode) never exceeds its configured maximum bound (NFR-002). (check:
  TestNudge_ReportsFailureAtCap, TestRegenerate_StopsAtMaxRetryBound,
  TestResample_StopsAtMaxRetryBound, TestRetryLoop_BoundedIterations)
- INV-004 — A puzzle's grid width and height each lie within 10..30 cells inclusive, in
  every source mode and at every point in its regenerate/resample/nudge lifecycle
  (US-016, CON-011, FR-019). (check: TestGenerateRandom_AcceptsMaxSide30,
  TestGenerateRandom_RejectsSideAbove30, TestGenerateRandom_RejectsSideBelow10)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted
  as unique must never actually have 0 or more than 1 solutions. This is the mandatory
  correctness property the whole tool depends on. (check:
  PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback)
  only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052
  as a gate-enforced mandatory constraint — a `check:` the system contract actually
  collects — so BCON-0001's socket-reach half is discharged by more than a threshold
  visible only in requirements.yml. (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as
  cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header
  naming a non-loopback host), and refuses any absolute-form request target whose
  authority is not a loopback name (NFR-004). Restates NFR-004 as a gate-enforced
  mandatory constraint — a `check:` the system contract actually collects — so
  BCON-0001's browser-mediated-reach half is discharged too, not only its socket-reach
  half (CON-009): binding to 127.0.0.1 alone does not stop this, since a browser sets
  Host from the request's target url, not from the page's origin. (check:
  PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE
  project-wide and applies to every source mode (random, built-in library, uploaded
  image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 range
  FR-001 carried; FR-001 is marked status: superseded, superseded_by: FR-019, and FR-019
  restates the behaviour over the narrowed range. (check:
  PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded
  source image's by more than 2x is refused with an explanatory error rather than
  converted (FR-021). The centred crop of FR-020 retains exactly min(r_src, r_tgt) /
  max(r_src, r_tgt) of the source with r = width/height, so this is exactly the rule
  "never silently discard more than half the user's picture". Retaining exactly 50% (a
  ratio difference of exactly 2x) is ACCEPTED — the boundary is inclusive. (check:
  PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore)
- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
  routing, form rendering, request parsing, and mapping onto
  orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py;
  it may import the orchestrator but no capability module may import it or cli.py.
  (check: test_every_import_in_the_package_points_inward)
- ADR-0022/R1 — Grid extent crosses module boundaries as a (width, height) pair. No
  public function signature, request field, or export field reduces a grid's extent to a
  single scalar "size", and no source mode constructs a grid from one integer. (check:
  review-lens)
- ADR-0023/R1 — Export metadata records a grid's extent as separate width and height
  fields. No export format writes a scalar "size" field, and no decoder reconstructs a
  grid's dimensions from one. (check: review-lens)
- ADR-0023/R2 — A decoder accepts only its own SCHEMA_VERSION, by exact comparison, and
  raises an error naming both the file's version and its own. It never attempts a best-
  effort read of an older document. (check: TestExport_RejectsSupersededSchemaVersion)


## Architecture context

- **FR:** FR-012
- **NFR:** —
- **CON:** CON-011 (the extent pair it forces on the format)
- **ADR:** ADR-0012, ADR-0015, ADR-0023
- **Components:** COMP-007, COMP-002 (payload construction only)
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- **[Resumed 2026-09-01]** This card was implemented and reviewed on 2026-08-31
  (cycle 1: **6.0**, 1 critical / 2 high — a failing gate), then fixed in
  `1e612ae`, then left. No cycle 2 ran, `Review score` was never stamped, and
  these notes stayed empty, so the board showed it as ordinary in-progress work
  rather than as something one review short of done.
- **[Brought up to date]** The branch was 41 commits behind main. `main` merged
  in cleanly, no conflicts: **1393 passed, 1 xfailed** (main's 1377 plus this
  card's 16). Nothing here was broken by CARD-034's orientation change or
  CARD-032's bundled font.
- **[Stale artefacts discarded, checked first]** The worktree carried untracked
  copies of ADR-0022, ADR-0023 and a modified `requirements.yml` from 2026-08-31.
  All were stale: ADR-0022's copy had none of that day's two revisions, and
  `requirements.yml`'s unique lines were the PRE-amendment text — including
  NFR-005's old "Cell size is non-increasing in max(width, height)", the exact
  false claim the 2026-09-01 delta removed. Main had 435 lines they lacked and
  they had nothing unique, so main's versions were taken. Recorded because
  merging without checking would have resurrected a retracted claim.

- **[AC/EC check] All criteria/constraints ✓** — verified 2026-09-01 from FRESH
  evidence on the merged tree (41 commits of main brought in), not carried from
  cycle 1 (which FAILED at 6.0 with 1 critical / 2 high).
  - **AC-060 / AC-061 ✓** — re-derived independently of the tests that assert
    them: a real 30x12 payload round-tripped through `json_export.document ->
    decode` and `csv_export.document -> decode`, with the grid deliberately
    `(row+column)%3` so it is ASYMMETRIC under transposition and a swapped pair
    cannot pass by coincidence. Extent survives as 30/12, grid and both clue sets
    come back exact, cells are `bool` not `int`, provenance survives, and
    `width != height` so nothing was square-inferred. Cycle 2 additionally killed
    two mutants here — reading height from `request["width"]` (AC-060's own
    "inferred as a square" wording) and swapping the pair.
  - **EC-002 ✓** — `PropertyTest_Export_RoundTripsExactlyForAnyPuzzle` green over
    its 2080-case corpus (min 40 / max 43 heights per width, 70 square, 2010
    non-square, 396 mixed-extent, all measured by the cycle-2 reviewer).
  - **ADR-0023/R2 ✓** — probed directly: a version-1 JSON document is REFUSED,
    not best-effort read, and the error names both numbers —
    `"unsupported JSON export version 1; this build reads version 2"`.
  - **Correction to this gate's own first run:** it initially reported AC-060 and
    AC-061 as FAILING on a full-dataclass equality check, because `name` and
    `difficulty` come back as `None`. That is not a defect and the check was
    wrong: the JSON schema is `clues/grid/request/seed/version` with `request`
    holding `density/height/mode/width`, and name and difficulty are deliberately
    NOT persisted — they are presentation metadata carried by the filename and
    the PDF header. EC-002's contract is the puzzle and its provenance, which is
    exactly why `_assert_round_trip` exists as a purpose-built helper rather than
    a bare `==`. Recorded because a gate that reports a false failure costs a
    cycle and teaches people to distrust it.
