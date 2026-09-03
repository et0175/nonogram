# CARD-028: Web form's size field accepts the `NxM` extent token

**Status:** in_progress
**Priority:** P2
**Category:** feature
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/028-web-form-extent-token
**Worktree:** ../PythonProject4-card-028
**Source:** meta/architecture/handoff.md#increment-5
**Idea:** —
**Wave:** 19
**Depends on:** CARD-020, CARD-027
**Touches:** src/nonogram/web/pages.py, src/nonogram/web/handler.py, tests/test_web_submission.py
**Review score:** —
**Started:** 2026-09-03T10:30:00Z
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

- **FR:** FR-017, FR-018
- **NFR:** NFR-003, NFR-004
- **CON:** CON-011
- **ADR:** ADR-0019, ADR-0021, ADR-0022
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—

## Worktree notes

- **[Env]** forge 2026.8.17 (skew gate passed). **[Dependency gate]** CARD-020 and
  CARD-027 both `done`.
- **[Card age — verified before the agent started]** This card was cut at wave 19 and
  CARD-020 landed since, which moves what it maps onto:
  - The card says the `NxM` split goes in `handler.py`. It does not: CARD-020 introduced
    **`src/nonogram/web/submission.py`**, which is where the body is turned into a
    `GenerationRequest` (`submission.py:195` currently sets `width=numbers["size"]`,
    `height=None`). That module is the real site and is inside the card's
    `src/nonogram/web/**` scope, but the `Touches:` line naming `handler.py` predates it.
  - CARD-020 already settled the **bare** reading: one number means `(N, None)` — the
    longer side, other derived — matching `cli._extent_token`. This card adds the
    explicit `NxM` form on top; it must not disturb the bare case.
  - The form's label was already updated by CARD-020 to describe the bare reading
    (`pages.py:172`). It now needs to describe both forms.
  - **G-4's cited check now exists.** `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`
    was a dead ref in this card's guardrails when it was written; CARD-020 created it, so
    the guardrail is mechanically checkable for the first time.
- **[The design constraint that decides the implementation]** `tests/test_cli.py`'s
  structural guard states the rule as "nothing inward of the adapter imports `cli`", and
  `web/` is an adapter peer — so the token parsing may **not** be shared by importing
  `cli._extent_token`. It must be reimplemented natively in the web adapter and
  cross-checked against `cli._extent_token` **from the test tree**, where the import is
  legal. That is CLAUDE.md's stated precedent (`solver/propagate.py`'s `mask_runs`), and
  `tests/test_web_submission.py` already cross-checks the bare case that way today.

## Worktree notes — implementation (2026-09-03)

- **Landed in `submission.py`, not `handler.py`, confirming the note above.** The `NxM`
  split lives in a new `nonogram.web.submission._extent_token`, a native reimplementation
  of `cli._extent_token`'s grammar (split on a duplicated `_EXTENT_SEPARATOR = "x"`
  constant, `int()` each half, `None` on any shape other than `N`/`NxM`). `submission.read`
  calls it for the `size` field only (`density`/`seed` stay on the plain-`int` path via
  `_NUMERIC_FIELDS`, which no longer includes `size`) and wires the result into
  `GenerationRequest(width=..., height=...)`. `handler.py` is untouched — it already just
  calls `submission.read` and renders whatever it returns. Additional footprint beyond
  `Touches:`: `src/nonogram/web/pages.py`'s `_STYLE`-adjacent form-page docstring/comment
  and the `size` field's label were also updated (in scope, but not itself a code path
  named in `Touches:`).
- **Malformed-token decision: refused at the adapter, not passed inward.** Mirrors the
  CLI's own split exactly — `cli._extent_token` raises `argparse.ArgumentTypeError` for a
  malformed token before any request exists (AC-064), and passes a well-formed but
  out-of-range token inward for the domain to refuse (AC-065). `submission._extent_token`
  returns `None` for the same set of malformed shapes (`"30x"`, `"x20"`, `"3x4x5"`,
  `"30X20"`, `"30*20"`, `"30,20"`, `"30.5"`, `""`, `"x"` — all checked, all malformed per
  `cli._extent_token`), and `submission.read` turns that `None` into an `unreadable` entry,
  which `handler._generate` renders as the structured failure page (EC-003) without ever
  calling the orchestrator — the same wall `argparse` puts up for the CLI, one adapter
  later. A well-formed but out-of-range token (`"60"`, `"60x60"`) parses cleanly and
  travels inward unmodified; the domain (`sourcing.random_grid.validate_extent`) is the one
  place either adapter's out-of-range pair is ever judged. Verified live: `POST /generate`
  with `size=20x30` succeeds (200, `data-outcome="success"`, exported grid 20 wide x 30
  tall); `size=60x60` fails with `nonogram refused this request. — grid width must be
  between 10 and 30 inclusive, got 60`, writing no file.
- **`pages.py`**: no `min`/`max`/`pattern`/numeric `type` added (G-2); the `size` field's
  `inputmode="numeric"` hint was removed since the field now also accepts `x`, which is not
  a validation constraint but a virtual-keyboard hint that would have been actively wrong
  for the `NxM` form.
- **EC(ADR-0022/R2) test**: `tests/test_web_submission.py` adds a 369-token, fixed-seed
  (`random.Random(20260903)`) corpus — 9 named CARD-028 refusals, a 54-value bare-N sweep,
  6 `int`-tolerance probes, a 100-pair `NxM` product, 200 fuzz strings — checked in two
  parametrised arms (`test_the_adapters_size_parsing_matches_cli_extent_token_for_every_token`,
  `test_the_built_request_carries_the_same_pair_read_end_to_end`) against `cli._extent_token`
  as the oracle. Mutation-tested by hand: (a) making the `NxM` split always return
  `(N, None)` and (b) adding an adapter-side `width > 30` rejection both fail dozens of
  cases in the property arms; both mutations were reverted and the source file's md5
  (`398f8f3397e1f0c2a285fe04b15fa5b9` for `submission.py`) confirmed byte-identical to
  pre-mutation.
- **Full suite**: `2298 passed, 1 xfailed, 3 warnings in ~43s` (this worktree's actual
  baseline — larger than the `1590 passed, 1 xfailed` figure in the task brief, which was
  stale relative to this branch's parent).
