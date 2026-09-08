# ADR-0021: Web UI request-handling model for long-running generation

**Status:** Accepted
**Date:** 2026-08-30
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** —

## Context

FR-017 requires the local web UI to drive the same `GenerationRequest`-shaped orchestrator pipeline the CLI uses, including its uniqueness verification and its regenerate/resample/nudge retry loops, and to report success or failure back to the page together with the paths of any files written. That pipeline is not fast in the worst case: NFR-001/ADR-0001 allow up to 5s p95 for grids at or below 20x20, but permit a hard 30-second timeout for larger grids up to the 50x50 maximum, and NFR-002/ADR-0002 permit up to 20 regenerate/resample attempts (plus 5 pixel-nudge attempts) inside a single generation request. A naive transposition of the CLI's blocking call onto HTTP means a single POST can legitimately hold the connection open for up to half a minute with no output in between.

AC-051 requires that when every candidate exhausts the retry bound (the same condition that raises `GenerationAbandoned` for the CLI today), the abandoned-generation case is reported back to the page "without hanging or returning an unhandled server error" — a guarantee this decision has to deliver by construction, not by hope. EC-003 further requires that any domain error the pipeline can raise for a web submission (invalid request, `GenerationAbandoned`, `SolverTimeout`, `ExportRejected`) is caught by the web adapter and surfaced as a structured failure, never an unhandled exception or raw stack trace. AC-050 depends on the web path surfacing "the same domain error the CLI would raise" for an out-of-range request, which constrains how far the web adapter's error handling is allowed to diverge from the CLI's synchronous call-and-catch shape.

ADR-0011 already established that generation is bounded from the inside: the orchestrator computes a deadline and the solver checks it cooperatively at each propagation fixed-point and branch node, raising `SolverTimeout` the instant the ADR-0001 bound is passed, which the orchestrator converts into the existing `GenerationAbandoned` abandonment path. This mechanism exists and is called on every generation attempt regardless of which adapter (CLI or web) invokes the orchestrator. CON-008 has separately ruled that the web UI's v1 does not render an in-browser preview of the generated image, so there is no progressive-rendering surface a request-handling model would need to feed. CON-003 forbids persistence beyond local file export, and BCON-0001/CON-003 together mean the web UI serves exactly one local, unauthenticated Puzzle Creator actor over loopback — concurrency (two submissions in flight at once) is explicitly out of scope for this decision, since BCON-0001 forbids multiple concurrent users outright and CON-003 forbids the shared state concurrent handling would require; a single in-flight run is a given this decision can rely on. This question sits downstream of the stdlib HTTP layer chosen in ADR-0020: whatever request-handling model is chosen here must be expressible as a plain `BaseHTTPRequestHandler` method with no additional framework machinery to lean on.

## Decision

We adopt the synchronous blocking request model: the POST handler calls the orchestrator inline, on the request-handling thread, and does not return a response until the orchestrator call returns — either a success result carrying the written file paths, or a domain exception that the handler catches and renders as a structured failure page.

This satisfies FR-017's "drives the SAME orchestrator pipeline the CLI uses" more literally than any alternative: the web adapter's call into the orchestrator is the identical synchronous call the CLI already makes, with the identical error semantics AC-050 depends on ("the same domain error the CLI would raise"). AC-051's "without hanging" requirement is met by an existing mechanism rather than new one: ADR-0011's cooperative solver deadline already guarantees every generation attempt terminates within ADR-0001's 30-second bound, so the request-handling thread can never block indefinitely — no additional timeout, watchdog, or cancellation machinery is needed to make that guarantee true. EC-003 is satisfied the same way the CLI already satisfies its own error handling: a single try/except around the orchestrator call catches every domain exception the pipeline can raise and converts it to a structured failure response before anything is written to the response stream, so no unhandled exception or raw stack trace can reach the browser.

## Alternatives considered

### background_job_with_polling

The POST handler starts the orchestrator run on a worker thread, returns 202 with a job id immediately, and the page polls a status endpoint until the job reports success or failure. This was rejected because it is real new machinery — a job registry, an id scheme, a status endpoint, thread lifecycle management, and cross-thread exception marshaling — built to enforce a bound the pipeline already enforces at 30 seconds via ADR-0011. The in-process job dict such a design requires is exactly the kind of state that outlives a single request that CON-003's no-persistence posture has so far avoided; it would need to be carved out as a special exception. It also diverges the web path's error handling from the CLI's synchronous raise-and-catch shape, weakening the "same pipeline, same errors" guarantee that AC-050 and EC-003 rely on — an exception raised on a worker thread has to be marshaled back across the thread boundary before it can even be compared to what the CLI would have raised.

### streaming_chunked_response

Keep a single request but stream the response body incrementally (chunked transfer or `text/event-stream`), emitting progress lines as the orchestrator's retry loop advances and closing with the final result. This was rejected because it requires the orchestrator to expose a progress callback it does not have today, and adding one would be adapter-driven change pushed inward across the ADR-0007 layering boundary — capability modules and the orchestrator must never be shaped by what an adapter needs to display, only the reverse. It also has a structural mismatch with EC-003 and AC-051: once a chunked response has started, the HTTP status code is already committed, so a `GenerationAbandoned` discovered late in the retry loop cannot cleanly become a failure status — the page would have to infer failure from a truncated stream rather than receiving a proper structured failure response.

## Consequences

### Positive

- The web adapter's call into the orchestrator is byte-for-byte the same synchronous call the CLI makes today, so the domain error semantics AC-050 and EC-003 depend on hold automatically rather than needing to be independently re-verified for a second call shape.
- AC-051's "without hanging" guarantee costs nothing new to build: it rides entirely on the ADR-0011 cooperative deadline that already exists and is already exercised by every CLI generation run.
- No new state is introduced anywhere in the system — CON-003's "no persistence beyond local file export" holds without needing an exception carved out for job records, and the single-container C4 view for the web UI needs no new component.
- The web adapter's implementation surface stays minimal: one handler method, one try/except around one orchestrator call, no client-side JavaScript, no polling endpoint, no meta-refresh.

### Negative

- A worst-case 50x50 generation leaves the browser on a blank spinner for up to 30 seconds with no progress feedback and no cancel option — indistinguishable, from the user's point of view, from a hung server. This is accepted, not fixed: the deferred backlog item "Progress/status feedback in the web UI for long-running generations" (meta/kanban/backlog.md, added 2026-08-30) is the explicit escape hatch if this becomes a real problem in practice.
- Some browsers or an interposed proxy may time out client-side before the server's 30-second bound is reached; when that happens the server-side generation run continues to completion and is simply discarded (harmless, but the user gets no result for work that did complete, and would need to resubmit). This is an accepted risk: BCON-0001's single-user, loopback-only context makes an orphaned local generation low-stakes.
- This decision forecloses ever reporting nudge/retry progress (FR-014's nudge count is only known once the run finishes) without a later rewrite of the web adapter's request-handling model — that rewrite is exactly what the deferred backlog item would trigger.

### Neutral

- The request-handling thread is occupied for the full duration of a generation run; because concurrency is explicitly out of scope for this decision (BCON-0001 forbids concurrent users, CON-003 forbids the shared state concurrent handling would need), this has no observable effect under the single-user assumption this project already makes everywhere else.
- This decision is downstream of ADR-0020 (the stdlib HTTP layer): the synchronous handler is written as a plain `BaseHTTPRequestHandler` method with no framework-level request/response abstraction to lean on.
- Revisiting this decision (e.g. to add progress feedback) would mean introducing the machinery rejected here as `background_job_with_polling` or `streaming_chunked_response` — the rejected-alternatives analysis above is the starting point for that future ADR revision, not work to redo from scratch.

## References

- DEC-022 (resolved by this ADR)
- FR-017, NFR-001, NFR-002, NFR-003, CON-003, CON-008, EC-003, AC-049, AC-050, AC-051
- ADR-0001 (generation-time thresholds), ADR-0011 (cooperative solver deadline mechanism), ADR-0020 (stdlib HTTP layer)

## History

- 2026-08-30: Created — resolves DEC-022 as `synchronous_blocking_request`: the web POST handler runs the orchestrator inline and relies on the existing ADR-0011 cooperative deadline for its non-hanging guarantee, rejecting background-job and streaming alternatives as unneeded new machinery.

## Rules
```yaml
- id: ADR-0021/R1
  statement: The web UI's POST handler calls the orchestrator synchronously on the request thread and must not introduce a job store, polling endpoint, worker-thread handoff, or streamed/chunked response for generation requests.
  scope: {code: ["src/nonogram/web/**"]}
  check: {kind: review-lens}
  severity: mandatory
```
