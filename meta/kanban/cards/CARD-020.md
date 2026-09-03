# CARD-020: Web UI generation submission — form to pipeline to result page

**Status:** review
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
**Touches:** src/nonogram/web/**.py, tests/test_web_submission.py, tests/test_web_server.py, meta/architecture/inputs/raw-requirements.md (the last two beyond the predicted footprint — disclosed in Worktree notes)
**Review score:** 7.5 (cycle 2; cycle 1 4.5; cycle 3 fixes applied, terminal)
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

**[SUPERSEDED BY CYCLE 1 — the paragraph below described the state at commit
177ba57. CON-010 / NFR-004 is now CLOSED on this card; see "Review cycle 1"
below for the scope expansion, the owner's approval of it, and the evidence.]**

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

### Review cycle 1 — fixes (score 4.5, GATE FAILED: 1 critical + 4 high)

Report: `meta/review/20260903T060056Z-CARD-020-cycle1.yml`.

**F-001 (critical) — the cross-origin hole is closed. THIS IS A DELIBERATE SCOPE
EXPANSION BEYOND THIS CARD'S ACs, AND THE OWNER APPROVED IT.** NFR-004 / CON-010
carry five acceptance criteria (AC-054..AC-058) and a property (EC-004) that were
never on this card, and the implementation notes above recommended a separate
card. The owner decided otherwise, on the reasoning the review put to them: the
violation predates this card, but this card is what turned it from "a
cross-origin page can read a static string" into "a cross-origin page can run the
pipeline and write files at a path it chooses", and a merge would ship that.

What landed, all of it in `handler.py` and all of it decided **before routing**,
beside the existing `Host` check:

* `_cross_origin_refusal` reads three signals and refuses on any of them —
  a `Sec-Fetch-Site` outside `ALLOWED_FETCH_SITES` (`same-origin`, `none`), an
  `Origin` whose host is not a loopback name, and an absolute-form request
  target whose authority is not one either (AC-056's shape, which arrives with
  no `Host` at all). *Every* value of each header is read, not just the first.
* `_host_is_local` now bounds the authority *shape*, which EC-004 names
  explicitly and which the function's own docstring had been recording as an
  open gap: `#` and `?` join `@` and `/` as refused characters, and the port
  must be absent or all digits. `127.0.0.1#evil.example.com`, `localhost?evil`,
  `127.0.0.1:` and `127.0.0.1:notaport` were all served before and are refused
  now. Same function, so the `Host`, `Origin` and request-target authorities are
  judged by one rule rather than three.
* `_origin_is_local` compares an `Origin` against the shape RFC 6454 gives it —
  scheme, host, optional port and nothing else — so `null`, an empty value and
  `http://127.0.0.1/path` are all refused rather than mined for a host substring.

**Status code: 400, and the choice is the model's rather than this card's.**
NFR-004's own threshold says "refused with HTTP 400 and never routed to a
handler", and AC-054/AC-055/AC-056 each say "refused with 400". 403 was the
obvious alternative and is wrong twice over here: nothing is authenticated and
nothing is forbidden to a principal — the request named an authority this server
does not answer to, or was started by a document it did not serve, which makes it
malformed — and AC-053's shipped guard
(`test_the_package_contains_no_authentication_vocabulary`) fails the suite on a
literal `403` or `HTTPStatus.FORBIDDEN` anywhere under `web/`. So 400 also keeps
"this UI has no authentication and no challenge" literally true.

`Referer` is deliberately **not** consulted, which is a departure from the
review's shorthand and not from the model (neither NFR-004, CON-010 nor EC-004
mentions it): a referrer policy the attacking page controls can suppress it, so a
rule resting on it is one the attacker can switch off. `Sec-Fetch-Site` and
`Origin` are forbidden header names to `fetch`/XHR and cannot be **set** by page
script. (Corrected in cycle 3: "cannot be suppressed" was too strong for
`Origin` — a cross-origin GET simply does not carry one. What makes "absent
means served" safe is not suppression-resistance but that the Fetch standard
*requires* an `Origin` on every cross-origin request whose method is not
GET/HEAD, plain `<form method=post>` included; the only route here that writes
files is `POST /generate`. A cross-origin GET carrying neither header reaches
`GET /` and a constant string. `_cross_origin_refusal`'s docstring now carries
that argument in full.)

**A request carrying none of the three signals is still served**, on every
protocol version — `curl`, a typed URL, a bookmark, and this module's own AC-052
interface probes (AC-058). Nothing about the loopback command-line flow changed.

Guardrails held: no `orchestrator` or capability-module edit (G-1), no job store
or worker (G-3), no puzzle rendering (CON-008), loopback bind untouched (CON-009).
The refusal reads header names and an authority and answers with a status code —
ADR-0019/R1's "HTTP concerns only" — and `tests/test_cli.py`'s ast import guard
is green.

**CON-010's declared check now exists.**
`PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest` is written
under that exact logical name in `tests/test_web_server.py`, following this
project's property convention (a CamelCase id in the module header and a section
banner, snake_case `def`s as its arms — `PropertyTest_` is not collected by
pytest's `python_classes`). No `hypothesis`. Three arms: a corpus check, the
refusal sweep, and the *served* sweep that bounds it. The corpora are products of
hand-built tuples — refused authorities × schemes × header positions × both
methods — giving **294 refused** and **58 served** cases, and both minimums
(`_MINIMUM_REFUSED_CASES = 200`, `_MINIMUM_SERVED_CASES = 40`) are asserted inside
the tests that consume them. The POST rows carry a real submission whose `out` is
`tmp_path`, so "never routed to a handler" is checked by its consequence on disk
and not only by a status code.

**F-002 (high) — `export_formats` and the NUL both refused in the adapter.**
`export.for_format` delegates the refusal of an unregistered name to the adapter
by contract, in the same words `sourcing.for_mode` does, and only `mode` had
discharged it. `submission.read` now checks posted formats against
`export.FORMATS` and reports them through the existing `unreadable` channel, so
`export_formats=png&export_formats=bogus` is refused *before* the PNG is written
rather than after. The drift assertion asked for is in
`test_an_export_format_the_registry_does_not_hold_is_refused_the_way_argv_is`:
`set(export.FORMATS) == set(_argv_export_choices())` (read off the built parser)
**and** `== _form_export_choices()` (read off the rendered markup), so all three
corners are one vocabulary. For `out=bad%00dir` — `Path.mkdir` raises a bare
`ValueError`, not an `OSError` — `submission.read` refuses a NUL in any field
rather than widening `_generate`'s except arm: a NUL cannot appear in argv at
all, so this removes an asymmetry the web adapter introduced instead of catching
a wider class of exception and hiding real bugs with it.

**F-003 (high) — the `except OSError` arm is pinned.** Two hermetic cases in
`tests/test_web_submission.py`, both reachable from the form with nothing
monkeypatched: `out` naming an existing regular file (`FileExistsError`) and
`out` under a 0500 directory (`PermissionError`, skipped as root, mode restored
in a `finally`). Both assert 200, `data-outcome="failure"`, and the errno text on
the page. Re-running the reviewer's M10 (deleting the whole `except OSError`
block) now fails both — see Evidence.

**F-004 (high) — `result_page`'s CLI-parity claim replaced by the truth.** The
docstring now says what the page reports (name, seed, paths) and states each of
the three differences from `cli._run_generate` and why: the name is shown because
a page can be reloaded and shared where a console line was typed by its reader;
the seed is shown unconditionally because a page has no scrollback, which is how
ADR-0015 is discharged; FR-014's nudge line is not reproduced, and the reason is
re-derived from the code rather than asserted — the counter is advanced only by
`orchestrator.generate`'s `mode == "image"` branch, and an image-mode submission
from this form carries no picture, so it renders the failure page instead. The
module docstring's copy of the same claim is gone.

**F-005 (high) — the escaping rule is now one rule with one exception.**
`failure_page`'s `summary` is escaped (one call), so the module docstring and
`_shell`'s docstring agree instead of disagreeing about whether the rule has
exceptions. **Superseded in cycle 3:** the sentence they agreed on ("the only
unescaped interpolation is `_shell`'s `title`") was itself false — an AST walk
finds 23 interpolations, 12 unescaped. See cycle 3's F-002 below.

**F-006 (medium) — eight statuses, not seven.** `_respond`'s enumeration now
reads 200, 400, 404, 413, 414, 431, 501, 505, and says which four this module
writes itself, which five `send_error` funnels, and that 400 is on both lists.
`tests/test_web_server.py`'s own "nine statuses" — wrong on `main` too, and not
in the finding — is corrected to eight in the same pass so the two agree.

**F-007 (medium) — the AC-049 defect is filed.** An `AMENDS AC-049` entry is
appended to `meta/architecture/inputs/raw-requirements.md`, in the format of the
AC-063 / AC-087 / EC-009 entries: the tier must read Easy, with the measurement,
the two structural reasons (all four templates score Easy at 20x20; library mode
draws no randomness for POL-004 to resample), the pinning test, and the note that
the Medium request survives as AC-051's exemplar. `requirements.yml` was **not**
hand-edited.

**F-008 (low) — the guardrail citations resolve again.** `pages.py:6` (G-6 →
ADR-0006's baseline, cited directly), `pages.py:28` and `pages.py:122` (G-4 →
ADR-0019/R1 + G-2), `handler.py`'s `ALLOWED_HOSTS` comment (G-4 → ADR-0019/R1 +
G-2). Where a durable authority says the same thing it is now cited instead of,
or beside, the card-local number, per the review's suggestion. `G-4` inside
`pages.py` now denotes only CON-008's no-preview rule.

**F-009 (low) — the OSError parity claim withdrawn and the message made true.**
`_generate`'s docstring no longer says the catch is there "for exactly the reason
`cli._run_generate` catches it around the same call"; it states that this arm is
*wider* than the CLI's (which wraps only `export_puzzle`), why the shared `try`
is nonetheless right for EC-003, and that the message must therefore hold for an
`OSError` from either call. The message is now "A file for this request could not
be read or written." rather than "The puzzle was generated but could not be
written.", which was false for an OSError out of `generate`.

**F-010 (low) — `_read_body`'s two sentences agree.** "refused before it is read"
is now "answered with 413 after at most the cap's worth of it has been read, and
none of it is ever acted on", and `MAX_BODY_BYTES`'s "three orders of magnitude"
is corrected to two (65536 / a few hundred ≈ 2.3).

**F-011 (info) — no action, and nothing regressed.** Both disclosed adapter
refusals stand exactly as they were; the asymmetry the verdict pointed at is
F-002, which is fixed.

**F-012 (info) — `Touches:` updated**, as its suggestion asked, and extended for
`raw-requirements.md`.

**Evidence (cycle 1).**

* Full suite: **1580 passed, 1 xfailed** (cycle-0 baseline 1553 + 1 xfailed; 27
  new tests).
* **M10 re-run** — `_generate`'s whole `except OSError` block deleted: now **2
  tests fail** (`test_an_out_naming_an_existing_file_is_reported_as_a_failure_page`,
  `test_an_out_under_an_unwritable_directory_is_reported_as_a_failure_page`),
  where it survived before. Restored; `md5` identical.
* **The cross-origin refusal has teeth**, five mutants, each restored and
  verified byte-identical by `md5` + `git diff --stat`:
  - whole refusal disabled (`return None` first) → **9 tests fail**;
  - `same-site` added to `ALLOWED_FETCH_SITES` → 2 fail;
  - `#`/`?` dropped from the refused authority characters → 3 fail;
  - the port-shape check removed → 3 fail;
  - only the *first* `Origin` header read → 1 fail (the property).
* **`export_formats` / NUL mutants**: the format check removed → 3 fail; the NUL
  check removed → 1 fail. Restored, `md5` identical.
* **Real server, the reviewer's own attack.** `LoopbackHTTPServer` on a
  kernel-chosen port, three POSTs to `/generate` with an allowlisted
  `Host: 127.0.0.1:<port>` and `out=/tmp/card020-attack/...`:
  - `Origin: https://evil.example.com` + `Referer: .../attack.html` +
    `Sec-Fetch-Site: cross-site` + `Sec-Fetch-Mode: navigate` → **400 Bad
    Request**, body `cross-site request: cross-site`, **nothing written** (the
    directory tree does not exist);
  - same-origin form POST (`Origin: http://127.0.0.1:<port>`,
    `Sec-Fetch-Site: same-origin`) → **200**, `data-outcome="success"`, **two**
    files written — one per requested `export_formats` value (`png`, `json`);
  - plain POST with **neither header** (`curl`'s shape) → **200**,
    `data-outcome="success"`, **two** more files. (Corrected in cycle 3: the
    original "four files" for each POST was a miscount of the *cumulative*
    directory, which holds four after both runs because the second collides and
    lands as `<name>-1.png` / `<name>-1.json`. Re-measured directly on
    `_ATTACK_FIELDS`: run 1 → `pwned.png`, `pwned.json`; run 2 → `pwned-1.png`,
    `pwned-1.json`.)
  Also on the wire: `GET http://evil.example.com/ HTTP/1.0` with no `Host` →
  400 (AC-056); `Origin: https://evil.example.com` on a GET → 400 (AC-055);
  `Sec-Fetch-Site: cross-site` on a GET → 400 (AC-054); `same-origin` → 200
  (AC-057); no metadata at all → 200 (AC-058); `export_formats=bogus`,
  `png&bogus` and `out=bad%00dir` → 200 + the structured failure page, no
  partial export.
* Every pytest name cited in prose across the six touched source and test files
  was re-checked mechanically: **27 citations, all resolving to exactly one
  `def`/`class`**. The one CamelCase property id
  (`PropertyTest_WebServer_...`) follows the existing convention and is declared
  in the module header and a section banner, as its EC-003 sibling is.

## Worktree notes — cycle 3 (terminal)

Cycle 2 scored 7.5 (gate failed: 1 high + 6 medium). The reviewer named the
mechanism behind the medium cluster precisely: *an absolute quantifier asserted
over a whole module from the author's mental model and never counted against the
artifact*. Two of the six were sentences a previous cycle's remedy had itself
reworded from memory. So the rule for this cycle was: **count it mechanically
first, and where the count is worth keeping, put it in a test rather than in
prose.** Every derivation below was run; two claims became assertions.

**F-001 (high) — the tautological drift guard, replaced with a real invariant.**
The reviewer was right and the reasoning is worth recording: `_ERROR_CLASSES` is
a transitive walk of `NonogramError.__subclasses__()`, and every key of
`cli._EXIT_CODES` is declared to be such a subclass, so
`set(cli._EXIT_CODES) <= set(_ERROR_CLASSES)` was a subset relation between a set
and its own construction-guaranteed superset. Deleting a row only shrank the left
side.

Took option (a) — a non-tautological invariant does exist here, but it is not the
one the review's suggestion proposed. `set(_ERROR_CLASSES) - set(cli._EXIT_CODES)`
would be **wrong**: `exit_code_for` walks the MRO, so a subclass legitimately
inherits its parent's code, and `SizeTooSmallForSource` correctly has no row of
its own. Measured across the shipped hierarchy — 12 classes, 10 with their own
row, `SizeTooSmallForSource` inheriting `SizeOutOfRange`'s code 3 through the MRO,
and only the base `NonogramError` reaching `INTERNAL_ERROR`. The real invariant is
therefore **"no class falls through to the catch-all"**:

```python
unclassified = sorted(
    cls.__name__ for cls in _ERROR_CLASSES
    if cls is not errors.NonogramError
    and cli.exit_code_for(cls("drift probe")) is cli.ExitCode.INTERNAL_ERROR
)
assert not unclassified, unclassified
```

`INTERNAL_ERROR` is what `exit_code_for`'s own docstring calls "a mapping gap ... a
bug, not a user error", and the base is the one deliberate exception because it is
what "unmapped" is defined against. **Proven by re-running the reviewer's own
mutation**: deleting `GenerationAbandoned: ExitCode.GENERATION_FAILED` from
`cli._EXIT_CODES` now **fails** the test with `AssertionError:
['GenerationAbandoned']`, where it passed before. The other drift direction was
mutated too — appending a fresh `DriftProbeError(NonogramError)` to `errors.py`
fails with `['DriftProbeError']`. And the control passes: `SizeTooSmallForSource`,
which has no row and should not need one, does not trip it. `cli.py` restored
byte-identical (`md5 b81ef08e04b13a978bae652ea1564a8f`, the reviewer's own hash);
`errors.py` restored with an empty `git diff`. The banner's "neither adapter grows
a class the other has never heard of" is gone, replaced by what the walk actually
carries. EC-003 untouched.

**F-002 (medium) — the escaping rule, counted and then asserted.** AST walk over
`pages.py`: **23 f-string interpolations, 11 calling `html.escape` at the point of
interpolation, 12 not** — matching the reviewer's count exactly. The 12 are four
kinds: 4 module constants (`_STYLE` ×2, `SUCCESS`, `FAILURE`), 5 fragments built
here by a function that escaped as it built them (`_options` ×2, `_checkboxes`,
`written`, `listed`), `_shell`'s two parameters (`title`, a literal by contract;
`body`, pre-escaped by the caller), and **one value off the wire** —
`result_page`'s `{seed:d}`, safe not because it is escaped but because the `:d`
format spec admits an int and nothing else. The module docstring now states the
rule over caller-supplied *strings* and enumerates all twelve; `_shell`'s docstring
no longer claims to hold the only one.

Rather than leave a third spelling of a sentence that has now been wrong twice,
the claim is a test: `TestWebPages_EscapingRuleIsTheOneTheDocstringStates`
(`tests/test_web_server.py`) walks the AST, pins the 23/11/12 split, requires every
unescaped expression to appear in a named classification table (both directions,
so a stale entry fails too), pins `{seed:d}`'s format spec and demonstrates it is
what does the work, and — the anti-rot device — **reads the counts back out of the
docstring prose and compares them with the walk**, so a docstring reworded from
memory fails here instead of at the next review. Mutation-checked: replacing
`html.escape(reason)` with `reason` in `failure_page` fails 3 of the 4 (restored,
empty diff).

**F-003 (medium) — "four files" is two, at five sites.** Measured directly:
`_ATTACK_FIELDS` requests `export_formats=png` and `export_formats=json`, and
`generate` + `export_puzzle` on it writes `['pwned.png', 'pwned.json']` — **2**. A
second run into the same `out` writes `['pwned-1.png', 'pwned-1.json']`, which is
where "four" came from: a cumulative directory reported as a per-POST count. All
four code sites now say two, phrased against the constant ("one file per
`export_formats` value") rather than as a bare literal, and the fifth site — this
card's own Evidence lines — is corrected above with the measurement.

**F-004 (medium) — the module banner, rewritten to the AST's answer.** Measured:
of the three AC classes, `submission.read` is called in **two**
(`TestWebUI_SubmitRunsSamePipelineAndReportsFiles`,
`TestWebUI_RejectsOutOfRangeSizeLikeCLI`) and in **none** of
`TestWebUI_ReportsAbandonedGenerationGracefully`; `cli.build_parser` is referenced
at **exactly one** site, inside `_argv_choices`, whose two consumers compare
`choices` lists. So "each class" and "compared against what `cli.build_parser`
builds" were both false, and the banner disclaimed ("not two lists that happen to
agree today") precisely what the module does. It now says the shipped truth and
names the two comparisons that *do* carry FR-017 —
`test_the_files_are_the_ones_the_cli_writes_for_the_same_options` (both adapters,
one seed, written bytes compared) and
`test_the_one_size_box_travels_as_a_bare_side_exactly_as_argv_does` (asserted
against `cli._extent_token`, not a literal). The two choices-list tests are named
by their real names, which were themselves looked up rather than recalled — the
first two names written here were wrong and an AST check caught them.

**F-005 (medium) — trace.yml flipped.** NFR-004 and CON-010 both go
`partial → covered`. The "Test is planned" sentences are replaced by the shipped
state: the check's location, the three arms, the measured corpora (294 refused
against a floor of 200, 58 served against a floor of 40 — both floors asserted
inside `test_the_corpora_are_large_and_cover_every_declared_signal`), the eight
mutants, and the F-009 bound on NFR-004's literal "400". `requirements.yml` was
**not** hand-edited. The file still parses as YAML and both rows read `covered`.

**F-006 (medium) — the comment now protects the `.strip()` instead of inviting its
removal.** Measured on this interpreter: `http.client`'s header parsing strips the
whitespace *after the colon* but leaves trailing whitespace alone —
`parsestr("X-A: none \r\n")` yields `['none ']`, space intact. So `handler.py`'s
`site.strip()` is the **only** strip in the chain and is load-bearing. The comment
says that, and adds a precision the finding did not: the two padded rows are **not
symmetric** — `" same-origin"` arrives already unpadded and duplicates the row
above it, while `"none "` is the one that actually reaches the handler padded.
Verified by mutation: replacing `site.strip()` with `site` fails exactly one test,
`test_every_same_origin_or_metadata_free_request_is_served` — the over-refusal
direction, as predicted. That count is in the comment.

**F-007 (medium) — three of four, and the fourth is subtler than filed.** Read off
this interpreter's own `parse_request` and confirmed on the wire against an
untouched `BaseHTTPRequestHandler`. The `Bad request syntax` exit guards on a
**word count**, so it is reached from *both* sides of the version assignment: a
**one-word** request line skips the version branch entirely and is bare (which the
finding missed), while four or more words have already parsed and assigned, and go
out with a status line even unpatched. So of the four request-line shapes that earn
a stdlib 400, **three are bare and one is not**; 505 is always bare. Both
docstrings now say that, and — since this sentence has been reworded twice and
over-generalised both times — the measurement is a test:
`test_which_stock_error_paths_never_reached_the_version_assignment` drives a stock
`BaseHTTPRequestHandler` and asserts bare/not-bare per shape, so a Python upgrade
that changes the stdlib makes the docstring fail rather than silently rot. Its
bound, `test_the_shipped_handler_answers_all_five_of_those_shapes_with_a_status_line`,
shows the reset erases the difference.

**Low findings, also fixed.** F-008: `result_page(name: str)` widened to
`str | None` to match `orchestrator.Puzzle.name`, escaping `name or ""` — the call
sits *after* `export_puzzle` has written files and *outside* the EC-003 `try`, so a
`None` would have meant a dropped socket after a successful export. No orchestrator
edit (G-1). F-009: `_cross_origin_refusal`'s docstring records that a method with no
`do_*` is answered 501 by the stdlib before `_dispatch` — probed live for PUT,
DELETE, PATCH, OPTIONS and HEAD, all 501 with nothing written — so EC-004 holds for
them by a different mechanism and NFR-004's "400" is a statement about the two
routed methods. F-010: the `Origin` "suppressed" overclaim replaced by the argument
that actually holds (see the corrected paragraph above). F-011: the unqualified
`G-5` is now `CARD-019's guardrail G-5`, with a note on why the bare number does not
resolve; `web/__init__.py` now records that `submission.py` reads `export.FORMATS`
too, as a validity check. F-012/F-013 (info) need no action and none was taken.

**Evidence (cycle 3).**

* Full suite: **1590 passed, 1 xfailed** (cycle-2 baseline 1580 + 1 xfailed; 10
  new tests — 4 escaping-rule, 5 stock-error-path rows, 1 shipped-handler bound).
  `tests/test_cli.py`'s ast import guard green.
* **F-001 mutation, the reviewer's own**: `GenerationAbandoned` row deleted from
  `cli._EXIT_CODES` → `test_the_walked_corpus_is_the_whole_hierarchy` **FAILS**
  (`['GenerationAbandoned']`), where it passed against the old assertion. Second
  direction: a new `DriftProbeError` in `errors.py` → **FAILS**
  (`['DriftProbeError']`). Both restored, `md5`/`git diff` clean.
* **All eight cycle-1 mutants re-run, every count unchanged**: M1 whole refusal
  disabled → **9**; M2 `same-site` allowlisted → **2**; M3 `#`/`?` dropped → **3**;
  M4 port-shape check removed → **3**; M5 only the first `Origin` read → **1**;
  M6 `export_formats` registry check removed → **3**; M7 NUL check removed →
  **1**; M10 `except OSError` deleted → **2**. Each restored and verified
  byte-identical by `md5`.
* **Two new mutants** for the two claims converted into tests: `html.escape(reason)`
  → `reason` fails 3 of the escaping-rule class's 4; `site.strip()` → `site` fails
  exactly 1.
* **Every test name cited in prose added by this cycle** re-checked mechanically
  against an AST index of `tests/`: **19 identifiers, all resolving to exactly one
  `def`/`class`** (the one `PropertyTest_` logical id resolving to its declared
  section banner, per the existing convention). Two names were wrong when first
  written and were corrected from the index.

**Requirements now satisfied:** NFR-004, CON-010, AC-054, AC-055, AC-056,
AC-057, AC-058, EC-004 — each with a test of its own, CON-010's declared
`check:` ref resolving, and both trace.yml rows flipped to `covered` (cycle 3).
AC-049 remains satisfied with the substitution the implementation notes above
record, and the model-side correction for it is filed as an intake line rather
than applied to `requirements.yml`.

## AC/EC gate (2026-09-03)

**Verdict: PASS, with one criterion satisfied by a documented and filed deviation.**
Four criteria — AC-049, AC-050, AC-051, EC-003 — plus the six requirements the approved
scope expansion added (NFR-004, CON-010, AC-054..AC-058, EC-004). Every named test
resolves to exactly one `def`/`class`. **Suite: 1590 passed, 1 xfailed.**

**AC-049 is NOT literally satisfied and must not be recorded as if it were.** The
criterion names difficulty "Medium"; the shipped test uses "Easy". This is not a shortcut:
every built-in template scores Easy at 20x20 and library mode has no randomness to
resample, so `cat` + Medium raises `GenerationAbandoned` in *both* adapters — the CLI does
the same. Independently reproduced twice (implementation and cycle-1 review) and again at
this gate. The criterion asks for a success the pipeline cannot produce. The deviation is
stated in the test's own class docstring, the amendment is filed as intake in
`meta/architecture/inputs/raw-requirements.md` ("AMENDS AC-049's `given`: the difficulty
must read **Easy**, not Medium"), and `requirements.yml` was not hand-edited. The Medium
request did not vanish — it became AC-051's deterministic abandonment case, which is a
better test than a contrived timeout would have been.

The AC-049 test also asserts more than the criterion asks: the same options submitted
through the form and through argv produce **byte-identical files under the same names**.
That turns "the same pipeline" from a resemblance into an identity, and it is what would
catch the web adapter growing a private default, a different naming rule, or a second
export call.

### Verified at this gate, not inherited from the reviews

- The cross-origin refusal, against a live server I ran myself: the attack
  (`Origin: https://evil.example.com` + `Sec-Fetch-Site: cross-site`) returns **400 and
  writes nothing**; a same-origin POST and a header-less `curl`-shaped POST both still
  succeed and write. The last of those was the one genuinely at risk — an over-eager
  refusal would have broken the loopback path the guard exists to protect.
- F-001's repaired drift guard: deleting the `GenerationAbandoned` row from
  `cli._EXIT_CODES` now fails `test_the_walked_corpus_is_the_whole_hierarchy` with
  `AssertionError: ['GenerationAbandoned']`. At cycle 2 that same mutation passed. `cli.py`
  restored byte-identical (md5 `b81ef08e04b13a978bae652ea1564a8f`).
- The 400-vs-403 choice is the model's, not a preference: NFR-004's threshold reads
  "refused with HTTP 400 and never routed to a handler", and AC-053's shipped guard fails
  the suite on a `403` literal anywhere under `web/`. My own suggestion of 403 was wrong.

### Known gap this card does not close

`meta/design/` does not exist, so `review.visual` degraded to static across all three
cycles. **Nobody has looked at the rendered result or failure pages** — only their HTML
source. Appearance, contrast, focus styles and real-browser behaviour are unverified, and
that is the one claim no gate here can make.

[AC/EC check] All criteria/constraints ✓ (evidence: AC-049 TestWebUI_SubmitRunsSamePipelineAndReportsFiles — satisfied with difficulty Easy, deviation filed as intake, see above; AC-050 TestWebUI_RejectsOutOfRangeSizeLikeCLI; AC-051 TestWebUI_ReportsAbandonedGenerationGracefully; EC-003 PropertyTest_WebUI_SurfacesAnyPipelineErrorAsStructuredFailure; and for the approved scope expansion NFR-004/CON-010/AC-054..AC-058/EC-004 PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest, whose declared check ref resolves for the first time; suite 1590 passed, 1 xfailed) — every name resolved to exactly one def/class before this line was written; verified 2026-09-03.

