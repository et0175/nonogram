# CARD-020: Web UI generation submission — form to pipeline to result page

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/020-web-submission-handler
**Worktree:** ../PythonProject4-card-020
**Source:** meta/architecture/handoff.md#increment-4
**Idea:** —
**Wave:** 13
**Depends on:** CARD-019
**Touches:** src/nonogram/web/**.py, tests/test_web_submission.py, tests/test_web_server.py (beyond the predicted footprint — disclosed in Worktree notes)
**Review score:** —
**Started:** 2026-09-02T14:20:00Z
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

## Worktree notes

- **[Env]** forge 2026.8.17 (skew gate passed). **[Dependency gate]** CARD-019 `done`.
- **[Drift gate]** clean for the first time in four cards — no `meta/drift-pending.yml`
  event names `src/nonogram/web/`.
- **[Visual loop]** `meta/design/` does not exist, so `review.visual: auto` degrades to a
  static review. Worth knowing when reading the review's coverage note: nobody will have
  LOOKED at the rendered page.
- **[CARD AGE — the one real gap, read before implementing]** This card was cut at wave 13
  and five cards have landed since that change what it maps onto. Verified against today's
  tree at start:
  - `orchestrator.export_puzzle(puzzle)` and `generate(request)` both still exist with
    those names, and `GenerationRequest` really does carry `out: Path | None`, so the
    card's field list is accurate on that point.
  - **But `GenerationRequest` has no `size` field.** It carries `width` and `height`
    separately (CARD-027/FR-018), and since CARD-033/FR-023 a bare single number is NOT a
    synonym for a square: `(N, None)` means "N on the longer side, derive the other from
    the source", while `(N, N)` forces a square. The card says "map the fields onto
    `GenerationRequest` — `mode`, `size`, ..." and predates the distinction, so it does
    not say which the form's one `size` box should produce. **That is a real decision this
    card has to take, and it is not in the card.**
  - Both ACs survive either choice, which is why this needs stating rather than
    discovering: AC-049 uses library key `cat`, whose template is 16x16 square, so
    `(20, None)` derives to exactly the 20x20 the criterion names; AC-050's 60 is refused
    by `validate_extent` either way.
  - The `NxM` form field itself is explicitly **CARD-028's**, not this card's.

### Implementation notes (CARD-020, worktree run)

**What landed.** `POST /generate` is routed by a `do_POST` that dispatches through the
same `_dispatch` `do_GET` uses (so the `Host` check and the 404 are shared, not copied).
A new `src/nonogram/web/submission.py` maps one urlencoded body onto
`orchestrator.GenerationRequest`; `handler._generate` reads the body, calls
`orchestrator.generate()` then `orchestrator.export_puzzle()` **synchronously on the
request thread** (ADR-0021 — no job store, no polling endpoint, no worker, no streamed
response), and renders one of two new pages in `pages.py`: a result page carrying the
puzzle name, the seed (ADR-0015) and the written paths, or a structured failure page
carrying the domain error's own message. `orchestrator.py` and every capability module
are untouched (G-1).

**THE DECISION THE CARD DID NOT MAKE — the one `size` box maps to `(N, None)`.**
`GenerationRequest` has no `size` field; it carries `width`/`height`, and since
CARD-033/FR-023 a bare single number is not a synonym for a square. The form's one box
fills `width` and leaves `height` unstated, exactly as `cli._extent_token` does for a bare
`--size N`. Why, in order of weight:

1. **FR-017 says the web exposes the *same* options as the CLI**, and this card's whole
   premise is that a web submission behaves as the argv would. `(N, N)` would make the one
   number mean *square* on one adapter and *longer side, derive the rest* on the other —
   the single option whose meaning changed on the way through the browser.
2. **`(N, N)` is a claim about the source that the adapter cannot make.** ADR-0022/R4 and
   `cli._extent_token`'s own docstring put "what fills an unstated dimension" inward,
   precisely because the answer depends on the source's shape, which no adapter can see.
   Re-deciding it here would be the same mistake CARD-033 removed from `cli.py`, re-made in
   the second adapter — and it would be a *domain* decision in the adapter (G-2).
3. **Neither AC could have told me.** AC-049 uses key `cat`, a 16x16 **square** template,
   so `(20, None)` derives to exactly the 20x20 the criterion names, and AC-050's 60 is
   refused either way. Confirmed empirically: mutating the mapping to `(N, N)` fails
   **exactly one** test — `test_the_one_size_box_travels_as_a_bare_side_exactly_as_argv_does`,
   which asserts against `cli._extent_token` rather than against a literal. Decided on the
   contract; the test exists to hold the contract, not the other way round.

The `NxM` form field itself was **not** added — that is CARD-028's (CARD-027 G-7). The
`size` label was reworded from "square grid edge length" to the longer-side reading,
because after this mapping the old label was false.

**A SECOND STALE POINT IN THE CARD — AC-049's difficulty "Medium" is unreachable.**
AC-049 asks for library key `cat`, size 20, difficulty **Medium**, and a *success*. It
cannot succeed: every built-in template scores **Easy** at 20x20 and library mode has no
randomness for POL-004 to resample into another tier, so `--difficulty Medium` on a
library key abandons after 20 identical attempts (verified against today's tree — the CLI
does the same, so this is not a web bug). AC-049's happy path is therefore exercised with
**Easy**, and the Medium request is not discarded but moved to where it is now true: it is
AC-051's "options make every candidate fail the difficulty checks up to the retry bound",
which makes AC-051 deterministic and 0.03s rather than seed-hunted.
`test_every_built_in_template_scores_easy_at_this_size` pins the premise, so a later card
that retunes the scorer fails there instead of silently swapping the two criteria.
**AC-049 in `requirements.yml` should be reworded to Easy** — not done here (out of scope).

**Two adapter-level checks that are *not* domain validation (G-2 tension, disclosed).**
Everything about a value's *range or vocabulary of meaning* travels inward untouched — a
60 goes in as 60, `density=500` as 500, `difficulty=extreme` as the string, a whitespace
name as the whitespace. Two things are refused in the adapter, and both are the web
spelling of something `cli.py` already does at the same rank:

* **`int` on `size`/`density`/`seed`.** `twenty` is not a number, so there is no number to
  put in a field typed `int | None`. This is argparse's `type=int`, not a range check.
* **A `mode` the form does not offer.** `sourcing.for_mode`'s own docstring says a bad mode
  "is rejected by argparse's `choices` at the adapter" and raises a bare `ValueError` —
  *not* a `NonogramError` — if one reaches it. Without the equivalent here, `mode=bogus`
  would escape as an unhandled exception, which EC-003 forbids outright. Checked against
  `pages.MODES`, the very tuple the form's `<select>` is rendered from, so the offered set
  and the accepted set are one object.

Also added: `handler.MAX_BODY_BYTES` (64 KiB), a transport bound like `IDLE_TIMEOUT_S` —
`http.server` bounds request lines and header counts and nothing else, so without it a
`Content-Length: 4000000000` is read into memory in full.

**Failure responses are `200`, deliberately.** The page *is* the report and delivering it
succeeded. Sorting domain outcomes into HTTP status families would be a second error
taxonomy beside `cli.exit_code_for`'s exit-code table — the adapter drift ADR-0019 names,
and the drift this card was told to avoid. The package therefore has **no table of error
classes at all**: it shows the error's own message, the same text `cli._report` prints.
`test_the_walked_corpus_is_the_whole_hierarchy` pins `set(cli._EXIT_CODES) <= set(hierarchy)`
so neither adapter can grow a class the other has never heard of.

**CON-010 / NFR-004 IS STILL OPEN, AND THIS CARD MADE IT MATTER MORE.** CARD-019's
docstrings said cross-origin refusal was "owned by CARD-020". It is **not** implemented
here: it has five acceptance criteria of its own (AC-054..AC-058) plus EC-004, none of them
on this card, and `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`
does not exist anywhere in the tree — so nothing was weakened, but nothing held it either.
What changed is the stakes: before this card a cross-origin page could read a static form;
now it can make the server generate and **write files**. The docstrings in `web/__init__.py`
and `handler.py` were corrected to stop attributing it to this card and to say plainly that
it is open. **Recommend a card for NFR-004 next, before the web UI is offered to anyone.**

**Footprint beyond the predicted Touches** (`src/nonogram/web/**.py`,
`tests/test_web_submission.py`):

* `tests/test_web_server.py` — unavoidable. CARD-019 pinned the pre-POST state in six
  places and every one of them is now false: the route table (one row), `do_POST`'s
  absence (twice), the package's import set, the docstring's future-tense mapping claim,
  and the stdlib-501 probe (which used `POST /`, now a routed path — changed to `PUT`).
  Each was rewritten to assert the new truth, not deleted. `tests/test_cli.py`'s import
  guard was **not** touched (G-6).
* `src/nonogram/web/__init__.py`, `handler.py`, `pages.py` — inside `web/**.py`, but worth
  naming: their docstrings made CARD-019-era claims ("this card never reads a request
  body", "a POST gets a 501", "CON-010 owned by CARD-020") that this card falsified.

**Evidence.**

* Full suite: **1553 passed, 1 xfailed** (baseline 1497 + 1 xfailed; 56 new tests).
* Mutation (a) — try/except removed so the domain exception escapes: **38 tests fail**.
* Mutation (b) — `export_formats` dropped from the mapping: **4 tests fail**.
* Mutation (c) — `size` mapped to `(N, N)`: **1 test fails**, the contract test named above.
  All three restored and verified byte-identical by md5.
* Real server, not just the suite: `nonogram serve --port 8791`, a real urlencoded POST
  (library/cat/20/Easy/png+json) → page reports success, names
  `/tmp/card020-out/cat.png` + `cat.json`, both files exist (72 KB PNG, 2396x2220), and a
  `size=60` POST renders the failure page with "grid width must be between 10 and 30
  inclusive, got 60" and writes nothing.
* Every test name cited in prose across the six touched files was checked mechanically to
  resolve to exactly one `def`/`class` (26 citations). The one exception is the logical
  property id `PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure`, which
  follows this project's existing convention (cf.
  `PropertyTest_Export_RoundTripsExactlyForAnyPuzzle`): a CamelCase id declared in the
  module header and a section banner, with snake_case `def`s as its arms — `PropertyTest_`
  is not collected by pytest's default `python_classes`, so a class of that name would
  have silently run nothing.
