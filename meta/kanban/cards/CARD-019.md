# CARD-019: Web UI server skeleton, `nonogram serve`, and the adapter import allowlist

**Status:** done
**Priority:** P1
**Category:** enabler
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/019-web-server-skeleton
**Worktree:** —
**Source:** meta/architecture/handoff.md#increment-4
**Idea:** —
**Wave:** 12
**Depends on:** —
**Touches:** src/nonogram/web/**.py, src/nonogram/cli.py, tests/test_cli.py, tests/test_web_server.py
**Review score:** 9.6 (cycle 3/3)
**Started:** 2026-08-30T10:28:09Z
**Closed:** 2026-08-30T13:05:00Z
**Actual:** 0.3d
**Merge commit:** 45391fc
**Blocked by:** —

## What to implement

The first card of COMP-008 — it lays the package skeleton every later web card copies, and
it is the only card of the increment that touches the structural import guard.

1. **New package `src/nonogram/web/`** (COMP-008, ADR-0019). It is the *second inbound
   adapter*, a sibling of `cli.py` — HTTP concerns only, zero domain logic, zero
   validation, exactly the "parsing only" rule COMP-001 already follows.
2. **`http.server.ThreadingHTTPServer` + a `BaseHTTPRequestHandler` subclass** (ADR-0020).
   A hand-written router over `(method, path)`; no framework, no new dependency —
   ADR-0006's baseline (stdlib + Pillow + NumPy) stays closed, on the same precedent
   CON-006 set for PDF export.
3. **Bind `("127.0.0.1", port)` as a literal constructor argument** (NFR-003, BCON-0001).
   ADR-0020 records this as a *required consequence*, not a framework default — it is
   what makes AC-052 checkable at all. No authentication of any kind (AC-053): the
   absence is the decision, not an oversight.
4. **`GET /` serves the static form page** as an HTML string constant — the option surface
   mirroring the CLI's flags (source, size, density/difficulty, name, export formats).
   This card renders the form; it does **not** submit it. `POST` is CARD-020's.
5. **`nonogram serve` subcommand** under the existing ADR-0010 argparse tree, keeping
   ADR-0008's single `[project.scripts]` console entry point. Not a second entry point.
6. **Extend `tests/test_cli.py`'s structural import guard** with a narrow, explicit adapter
   allowlist. Today it walks `src/nonogram/**/*.py` with `ast` and fails any module that
   imports `cli` or the orchestrator; `web` joins `cli` **at the same rank**, so both
   adapters may import COMP-002 while capability modules still may not import either
   adapter or each other laterally (ADR-0019/R1). Read the guard before editing it — the
   allowlist must stay two names; widening it erodes the rule it exists to enforce.

## Acceptance criteria

- **AC-052** (boundary) — given the web UI server started with its default configuration,
  when it binds its listening socket, then the socket is bound to 127.0.0.1 and refuses
  connections arriving on any other interface.
  *test:* `TestWebServer_BindsLoopbackOnlyByDefault`
- **AC-053** (happy) — given a request to any web UI endpoint with no Authorization header
  or session credentials, when the request is handled, then it is processed normally,
  since the server enforces no authentication check.
  *test:* `TestWebServer_ProcessesRequestsWithoutAuthentication`

## Guardrails

- G-1: Existing CLI behavior unchanged — `nonogram generate` and every one of its flags
  keep their current parsing, exit codes, and stdout; `serve` is added as a *sibling*
  subcommand under the same console entry point (ADR-0008, ADR-0010). COMP-001 is
  untouched by ADR-0019 (test: the existing `tests/test_cli.py` suite)
- G-2: Do not edit `src/nonogram/orchestrator.py` or any capability module
  (`src/nonogram/sourcing/**`, `src/nonogram/clues.py`, `src/nonogram/solver/**`,
  `src/nonogram/difficulty.py`, `src/nonogram/export/**`) — the web adapter is purely
  additive and drives the already adapter-agnostic `GenerationRequest`
  (handoff Increment 4 Rollback)
- G-3: The import guard's adapter allowlist stays exactly two names (`cli`, `web`) at the
  same rank. Do not relax the capability-module rule, and do not generalize the allowlist
  into a pattern — a guard with an allowlist is already weaker than one without
  (ADR-0019 Negative) (test: `test_every_import_in_the_package_points_inward`)
- G-4: No domain logic and no validation in `src/nonogram/web/` — an out-of-range value
  must reach the domain and be rejected there, exactly as it is for the CLI
  (ADR-0007, ADR-0010, ADR-0019/R1)
- G-5: Out of scope — no POST/submission handling (CARD-020), no file upload (CARD-021),
  no in-browser preview of a generated puzzle (CON-008)
- G-6: No new runtime dependency. ADR-0020 chose stdlib `http.server` precisely so
  ADR-0006's baseline is not reopened

## System contract

- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py (check: test_every_import_in_the_package_points_inward)
- ADR-0021/R1 — The web UI's POST handler calls the orchestrator synchronously on the request thread and must not introduce a job store, polling endpoint, worker-thread handoff, or streamed/chunked response for generation requests (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- INV-001 — A puzzle's row and column clues always equal the run-length encoding of its current solution grid (check: TestComputeClues_MatchesGridExactly)
- INV-002 — A puzzle is only marked ready for export after its uniqueness check has confirmed exactly one solution (check: TestExport_RejectsUnverifiedPuzzle, TestExport_RejectsUnverifiedPuzzleForPDF)
- INV-003 — A puzzle's automatic-retry counter (regenerate, resample, pixel-nudge) never exceeds its configured maximum bound (check: TestRegenerate_StopsAtMaxRetryBound, TestResample_StopsAtMaxRetryBound, TestNudge_ReportsFailureAtCap, TestRetryLoop_BoundedIterations)

## Architecture context

- **FR:** FR-017 (partial — the adapter exists and serves the form; submission is CARD-020)
- **NFR:** NFR-003
- **ADR:** ADR-0019, ADR-0020, ADR-0007, ADR-0008, ADR-0010
- **Components:** COMP-008 (new), COMP-001 (gains the `serve` subcommand only)
- **Trace:** meta/architecture/trace.yml

## Failure matrix

Declared *before* implementation. Every row states the behaviour COMP-008 commits to at
that boundary, with a numeric bound wherever one applies. Where the behaviour is the
standard library's rather than this card's code, that is stated explicitly — an inherited
default that has been read and accepted is still a declaration.

| # | Boundary | Failure mode | Declared behaviour | Numeric bound |
|---|----------|--------------|--------------------|---------------|
| F-1 | socket bind (`web.server.create_server`) | bind fails for any reason other than a busy port — `EACCES` on a privileged port, `EADDRNOTAVAIL`, an out-of-range `--port` | The `OSError` (or `OverflowError`, which is what CPython's socket layer raises for a port outside 0..65535 — *not* an `OSError`) propagates out of `create_server` unwrapped. `web/` neither validates the port nor translates the failure: it is not a domain error and `NonogramError` is not widened for it (G-4, G-2). `cli._run_serve` catches `(OSError, OverflowError)` **around the `web.create_server` call and nothing else** — the serve loop (`web.serve_on`) runs outside the `try` — reports it through the existing `cli._report` format, and returns `ExitCode.INVALID_INPUT` (3). The narrowing is load-bearing: every failure this clause reports carries the same implied instruction, "pass a different `--port`", and that is only true of the bind (which is the grouping rule `_EXIT_CODES` uses). An `OSError` raised *after* a successful bind — a selector failure, an `accept` the stdlib re-raises — is a bug, keeps its traceback, and is not reported as bad input. No traceback reaches the user for a bind failure. | 0 retries; 0 alternative ports tried; exit code exactly 3; exactly 1 call inside the `try` |
| F-2 | socket bind | port already in use (`EADDRINUSE`, errno 48/98) | Same path as F-1: `OSError` out of `create_server`, exit code 3, one stderr line. The server never scans for a free port and never steals a live one: `ThreadingHTTPServer.allow_reuse_address` is the stdlib's `SO_REUSEADDR` (verified `True`), which on BSD/Linux does **not** permit binding a port another socket is actively `listen()`ing on, so a busy port stays an error rather than silently rebinding. `SO_REUSEPORT` is left off (stdlib default `allow_reuse_port = False`) — turning it on would let two servers share the port and is exactly the silent-steal this row forbids. | 0 retries; 0 port probing; exit code exactly 3 |
| F-3 | response write (`wfile`) | client disconnects mid-response (browser stop/refresh) → `BrokenPipeError` / `ConnectionResetError` | The exception escapes the handler into `ThreadingMixIn.process_request_thread`, which routes it to `BaseServer.handle_error`. `LoopbackHTTPServer.handle_error` overrides that: a lost-connection error is reported as one line on stderr instead of the stdlib's traceback; every other exception falls through to the stdlib's traceback, which is a real bug and must stay loud. The connection is dropped, the request thread ends, the listening socket is untouched and the server keeps accepting. Nothing is rolled back because this card holds no state (CON-003). | exactly 1 connection affected; 0 other connections affected; 0 bytes retained; server stays up |
| F-4 | request line / headers | malformed request line, *unparseable* version token, over-long URI, too many headers, one over-long header line | ~~Entirely the stdlib's `BaseHTTPRequestHandler.parse_request`, which answers before any COMP-008 code runs~~ **Corrected by CARD-022 (post-hoc F-004):** the stdlib still *decides* these statuses, but since CARD-022's `send_error` override COMP-008 *writes* the responses. `parse_request` closes the connection: `400 Bad Request` for a request line it cannot parse — including a version token that is not a version at all (`HTTP/ABC`) — `414 URI Too Long` for a request line over `http.client._MAXLINE`, and `431` for **either** of two distinct header failures wearing the same status: more header fields than `_MAXHEADERS` (`Too many headers`) or one header line over `_MAXLINE` (`Line too long`). A *well-formed* version this server does not speak is a different answer and has its own row (F-10). Not re-implemented here; the router is only reached for a well-formed request. **The statuses are the stdlib's; the RESPONSES are not** — CARD-022's `WebUIRequestHandler.send_error` override writes them through `_respond`, so each is `text/plain` with `nosniff` and a real status line (as originally shipped, 400 and 505 carried no status line at all, because `parse_request` had not yet accepted a version and `send_response_only`/`end_headers` no-op for `HTTP/0.9`), and none echoes the request's method or version. | request line ≤ 65536 bytes incl. CRLF (65537 → `414`); **header fields ≤ 99** — `_MAXHEADERS` is 100 but `http.client.parse_headers` appends the terminating CRLF to the very list it length-checks, so 100 real fields → `431`; any single header line ≤ 65536 bytes incl. CRLF (65537 → `431`); 0 bytes of a rejected request are routed. **Corrected by CARD-022 (cycle-2 F-104):** this cell previously wrote the second bound's status as `431 Line too long`, which is the *log* line, not the wire. Probed on this head: 200 header fields and a 70 000-byte header line both return `HTTP/1.0 431 Request Header Fields Too Large`. "Too many headers" and "Line too long" name the two distinct CAUSES and appear only in the server log; a client cannot tell them apart |
| F-5 | request body | a request arrives carrying a body (oversized or otherwise) | This card serves `GET` only and **never reads a request body** — not one byte, whatever `Content-Length` claims. There is therefore no size cap to enforce and no memory to exhaust here; the body cap belongs to CARD-020, which is the card that first reads one (G-5). Desync is impossible because the handler keeps the stdlib default `protocol_version = "HTTP/1.0"`: the connection is closed after every response, so an unread body cannot be mistaken for the next request. `POST` has no `do_POST` at all and gets a `501` — the honest answer for a submission endpoint this card does not implement. The status is the stdlib's, but since CARD-022's `send_error` override the response reads `501 Not Implemented` (not `501 Unsupported method`) and is `text/plain` with `nosniff`. | exactly 0 bytes of request body read; 1 response per connection |
| F-6 | process lifecycle | `SIGINT` (Ctrl-C) while serving | Python turns `SIGINT` into `KeyboardInterrupt` inside `serve_forever`. `web.serve_on` catches it, prints nothing further, and closes the listening socket in a `finally` (`server_close`), so the port is released even if the loop exits by another route — including an exception the loop does not expect, which is re-raised (a bug stays loud) *after* the socket is released. `nonogram serve` then returns `ExitCode.OK` (0) — a deliberate stop is not a failure. In-flight request threads are **not** awaited: `ThreadingHTTPServer.daemon_threads` is `True`, and `_Threads.append` drops daemon threads, so `server_close`'s join is a no-op. An in-flight generation is therefore abandoned at exit — the same accepted "orphaned local generation" outcome ADR-0021 already records for a client-side timeout. **Corrected by CARD-022 (post-hoc F-008):** the original row declared "shutdown ≤ 0.5s" and cited "measured: 0.30s to shut down with a 1.0s request in flight". That was a one-off manual measurement with **no covering test** — the three tests that exercise `serve_on` all drive `_StubServer` and assert only that `server_close` was called once; nothing times anything and nothing puts a request in flight. Per this matrix's own preamble ("a bound is only declared if something would notice it moving"), the number was not a declaration and is withdrawn rather than restated. The clauses that *are* checked stay. | socket released on every path out of the loop (interrupt, clean return, unexpected exception); 0s grace for in-flight requests; exit code exactly 0 |
| F-7 | router | request for a path with no route (`GET /favicon.ico`, `GET /generate`) | `404 Not Found` with a short `text/plain` body, written by the router's single fallback. No stack trace, no directory listing (nothing inherits `SimpleHTTPRequestHandler`, so no path ever reaches the filesystem — the form is a string constant). The server keeps serving. | exactly 1 response; 0 filesystem paths touched |
| F-8 | authentication (AC-053) | a request carries an `Authorization` header, a cookie, or nothing at all | All three are handled identically: the router never reads them and the response is the same. No `401`, no `403`, no `WWW-Authenticate` header exists anywhere in COMP-008. The absence of an auth check is the decision (NFR-003, BCON-0001). The access control is **loopback binding (F-9) plus the `Host` check (F-12)**, and neither reads a credential: the bind stops a network peer, and the `Host` check stops **DNS rebinding** — a name the attacker controls that resolves to 127.0.0.1. **Corrected by CARD-022 (post-hoc F-001):** this row previously said the `Host` check "stops the browser-mediated path a loopback bind cannot see", which claims more than it closes. A browser sets `Host` from the *target*, so a form on `https://evil.example.com` posting to `http://127.0.0.1:<port>/` sends an **allowlisted** `Host` and is served — re-verified on the wire: `Host: 127.0.0.1:<port>` + `Origin: https://evil.example.com` + `Sec-Fetch-Site: cross-site` → **200** and the form. Nothing in `web/` reads `Origin`, `Referer` or `Sec-Fetch-Site`. Browser-mediated cross-origin reach is **NFR-004, unimplemented, owned by CARD-020**; it is not closed by this card and must not be assumed closed by the card that adds `POST /generate`. | 0 credential checks; 0 `401`/`403` responses reachable; exactly 2 access-control checks, both on the transport; **0 checks on request provenance** (`Origin`/`Referer`/`Sec-Fetch-Site`) |
| F-9 | listening interface (AC-052) | a connection arrives on a non-loopback interface | It never arrives: `("127.0.0.1", port)` is the literal constructor argument (ADR-0020), so the kernel never accepts the connection — the client sees a refusal or a drop, depending on the host firewall, and no COMP-008 code runs. There is no configuration flag, environment variable, or command-line option that can widen the bind address: `web.create_server(port)` takes a port and nothing else, `LOOPBACK_HOST` is a module constant, and `cli.py` has no `--host`. **Corrected by CARD-022 (post-hoc F-007):** the original row said "There is no … keyword argument anywhere in `web/` that can widen the bind address" and bounded it at "0 ways to bind another". Both are false as written. `web.server.__all__` exports `LoopbackHTTPServer`, whose first constructor parameter is `server_address`, and `tests/test_web_server.py:_wildcard_control` uses exactly that to bind `("0.0.0.0", 0)` — re-verified: `LoopbackHTTPServer(("0.0.0.0", 0), WebUIRequestHandler).server_address == ('0.0.0.0', <port>)`. The guard sweep cannot see it either: `test_no_api_in_the_package_can_widen_the_bind_address` walks the *package-level* `web.__all__` (which omits the class) and matches parameter names against `{host, address, bind, interface}`, which `server_address` is not. The real bound is about the launcher, not the module. | exactly 1 interface bound by the launcher; 0 ways to widen the bind address through `web.create_server`/`serve_on` or the CLI; `web.server.LoopbackHTTPServer(server_address, …)` remains a public constructor that can bind any address, and the suite itself uses it to |
| F-10 | request line (HTTP version) | a *parseable* HTTP version this server does not speak (`GET / HTTP/9.9`) | The stdlib's `parse_request` again, and a **different** status from F-4's: a version string it can parse but not support gets `505 HTTP Version Not Supported`, not `400`. Recorded as its own row because the two failures are genuinely different — "I cannot read this request line" versus "I read it and will not speak that dialect" — and the original single row declared `400` for both, which was refuted by probe. The status decision is the stdlib's, but since CARD-022's `send_error` override the response is written by COMP-008 through `_respond` — `text/plain`, `nosniff`, a real status line. The row exists so the declaration matches the wire. | exactly 1 status per malformed request; `505` for a version > 1.1; 0 bytes routed |
| F-11 | connection lifetime | a client connects and never sends a request line (an abandoned browser preconnect, a local port scanner, a stuck process) | `WebUIRequestHandler.timeout = 30` (`handler.IDLE_TIMEOUT_S`), which `socketserver.StreamRequestHandler.setup` applies to the accepted socket. The blocking `rfile.readline` that reads the request line therefore expires; the stdlib's `handle_one_request` catches it, sets `close_connection`, and the connection is closed from the server side and its thread ends. Without this, `ThreadingHTTPServer`'s one unbounded daemon thread per connection is held for the life of the process — measured before the fix: 12 silent connections took the process from 2 to 14 live threads and kept them. Blast radius was always bounded by BCON-0001 (one local user), so this is robustness, not an exploit path — but an HTTP boundary with no timeout is a declaration this card owed and did not make. | idle connection dropped after 30s; outstanding threads ≤ connections opened within any 30s window; 0 bytes read from a silent connection |
| F-12 | `Host` header | a request reaches this server under a name that is not loopback — a hostname an attacker controls that resolves to 127.0.0.1 (DNS rebinding); or under two names at once | `_dispatch` compares the header's *name* (port ignored, `urlsplit`-parsed so `[::1]:8765` reads correctly — a *bare* `::1` is refused, since `urlsplit("//::1").hostname` is `None`) against `handler.ALLOWED_HOSTS` — exactly `{localhost, 127.0.0.1, ::1}` — **before** routing, and answers `400 Bad Request` with the host escaped into a `text/plain` body. A header value carrying `@` or `/` is refused before parsing: a `Host` is an authority, not a URL, so userinfo and a path have no meaning in it. **Corrected by CARD-022 (post-hoc F-001, F-002, F-004) — three claims in this row were false:** (1) the failure-mode cell named "a cross-origin form POST"; it is not closed here at all (see F-8, and NFR-004/CARD-020) and has been struck. (2) The `@`/`/` narrowing was justified as bounding the set of accepted *values* to the size of the set of accepted *names*; it does not — `urlsplit` splits on `#` and `?` identically and neither is refused (`Host: 127.0.0.1#evil.example.com` → 200, `Host: localhost?evil` → 200), and the port is never validated (`Host: 127.0.0.1:notaport` → 200). What is actually enforced is one sentence: *the host component, as `urlsplit` reads it, must be one of three names.* (3) "0 routes reached on a refused host" is refuted by the **request-target form**, which no row declares: `GET http://evil.example.com/ HTTP/1.0` with no `Host` is served **200** and the form, re-verified on the wire — `_dispatch` takes only `urlsplit(self.path).path` and silently discards the target's authority, where RFC 7230 §5.4 makes the absolute-form authority authoritative. Not browser-reachable (browsers emit absolute-form only to proxies), so the rebinding threat is not reopened, but the declared scope is not what is enforced. Bounding the accepted shape space is EC-004's property and lands with CARD-020. **Every** `Host` header is read (`get_all`), not just the first: two that disagree are refused, since RFC 7230 §5.4 forbids the repetition and there is no single answer to which name the request used; one value repeated is served. A request with *no* `Host` at all is served **on every protocol version**, HTTP/1.1 included, which RFC 7230 would refuse — a deliberate, declared deviation: the attack this closes is browser-mediated and a browser cannot suppress the header (`Host` is a forbidden header name to `fetch`/XHR), while refusing it would break `curl --http1.0` and this card's own AC-052 interface probes, which send `GET / HTTP/1.0` with no `Host`. This is a fact about the transport, decided with a status code — not domain validation, no `NonogramError`, no `raise` (G-4, ADR-0019/R1 unaffected). It is not an auth check either: nothing is authenticated, hence `400` and never `401`/`403` (F-8, AC-053). | exactly 3 accepted host *names* (the host component as `urlsplit` reads it); the set of accepted header **values** is unbounded — `@` and `/` are refused, `#`, `?` and an unvalidated port are not; ≤ 1 distinct `Host` value per request; 0 routes reached on a refused `Host` **header**, but an absolute-form request-target naming a foreign authority does reach the route; `400` and never `401`/`403` |

## Follow-up required (2026-08-30)

This card is `done` and merged (`e177473`). An **independent post-hoc review**
(`meta/review/20260830T163436Z-CARD-019-posthoc.yml`, score 6.0, mode
`post-hoc-independent`) re-derived all twelve failure-matrix rows from the code, from a
live socket and by mutation, and found **9 accurate, 3 refuted**. It also found that four
of the guard loops cited across all three review cycles as the enforcement of ADR-0019/R1
and guardrail G-4 pass **vacuously** — they enumerate a collection discovered at import
time without asserting it is non-empty, so an empty glob or a stale selector retires the
guard silently.

**CARD-022** (`meta/kanban/cards/CARD-022.md`, branch `card/022-web-adapter-truth-repair`)
owns the repair and has done it. Seven matrix rows above (**F-4, F-5, F-6, F-8, F-9, F-10, F-12**) were
corrected in place by that card and are marked "Corrected by CARD-022"; the code and test
changes are in commits `81504e5` and `6daf56a`. F-6/F-8/F-9/F-12 were corrected in cycle 1;
F-4/F-5/F-10 followed in the fix for cycle-1 finding F-004, once the `send_error` override
had made their "entirely the stdlib's" framing false, and F-4's 431 bound was corrected
again for cycle-2 finding F-104. The corrections are recorded here rather than in a new
card because this card's matrix is the record other cards read.

What CARD-022 did **not** do, deliberately (its guardrail G-1 — ship no new access
control), and what therefore remains open:

- **NFR-004 — browser-mediated cross-origin reach is not closed.** No `Origin` /
  `Sec-Fetch-Site` check exists. Row F-8's corrected text says so. **CARD-020 must not
  ship `POST /generate` on the assumption that F-12 closes CSRF.**
- **The absolute-form request-target bypasses the `Host` check** (post-hoc F-002). Row
  F-12 now states it; rejecting it is CARD-020's.
- **The accepted `Host` *value* set is unbounded** (`#`, `?`, unvalidated port) — post-hoc
  F-004. Row F-12 now states what is enforced instead of claiming a bound. Narrowing the
  shape space is EC-004's property, with CARD-020.
- **AC-052's evidence is host-dependent** (post-hoc O-1): both non-loopback probes skip on
  a runner with no non-loopback IPv4, leaving the criterion resting on the constant pin.
  Not a defect; not portable either.

## Worktree notes

[Env] forge 2026.8.17 (meets forge.min_version 2026.8.17)
[Drift gate] ⚠ unprocessed external drift intersects this card's Touches: `src/nonogram/cli.py` appears in 5 unreconciled events in `meta/drift-pending.yml` (2026-08-27/28, alongside orchestrator.py and export/). gate: warn (no `drift:` block in .skills.yml) — proceeding. The drift is from forge's own earlier waves, not an outside editor, so the model is expected to already describe it; reconcile with `/forge:reverse drift` when convenient.
[Pin gate] n/a — legacy.enabled not set

### Implementation summary (CARD-019)

COMP-008 exists as a four-module package under `src/nonogram/web/`, `nonogram serve` launches
it from the existing argparse tree, and the structural import guard knows two adapters at one
rank. `GET /` serves the option form; nothing submits it. Tests: **1157 → 1207** collected
(1206 passed + the pre-existing `bench_generate` xfail, which stays xfail — it is CARD-018's).
Full suite green; the `generate` path and every one of its flags, defaults and exit codes were
re-verified out-of-process as well as in the suite.

### STRUCTURE decisions

- `STRUCTURE: four modules under src/nonogram/web/ — server.py (socket + serve loop),
  handler.py (router + handler class), pages.py (HTML constants), __init__.py (the component
  docstring and the package's public names)` — the split is the one ADR-0020 names when it
  describes what it chose: "a hand-written router over (method, path), the form page served as
  a static HTML string constant, ... multipart parsed by hand". CARD-020 adds a route row and a
  `do_POST` to handler.py and a result page to pages.py without either file becoming the other;
  CARD-021's multipart parsing has an obvious home beside them. One flat `web.py` would have
  the two later cards editing one file for three unrelated reasons.
- `STRUCTURE: the bind address is a module constant (web.server.LOOPBACK_HOST), never a
  parameter — create_server(port) takes a port and serve_on(server) takes the server that port
  produced; no API in the package accepts a host` — AC-052 is
  only a property of the *code* if no supported call can produce a different answer. A `host=`
  keyword, even defaulted to loopback, would move the criterion into every call site.
  `TestWebServer_BindsLoopbackOnlyByDefault::test_no_api_in_the_package_can_widen_the_bind_address`
  pins both signatures exactly *and* sweeps every public callable in `web.__all__` for a
  host-shaped parameter (so a third entry point is covered without editing the test), and a
  sibling test greps the whole package for another bind address.
  *(Amended in fix cycle 1: this line read "create_server(port) and serve(port) take a port and
  nothing else" until F-006 replaced `serve(port)` with `serve_on(server)`. The property it
  states is unchanged and still holds — no API takes a host — but the signature it named no
  longer exists.)*
- `STRUCTURE: create_server() is public and separate from the serve loop` — a test needs a real
  socket without also owning a blocking loop. This is what lets AC-052 be checked behaviourally
  instead of by reading `server_address` back. Fix cycle 1 made the split load-bearing rather
  than merely convenient: `cli._run_serve` now binds inside its `except` and serves outside it,
  which is the only way to report a bind failure as a port problem without also mislabelling
  every post-bind failure as one (F-006, F-1).
- `STRUCTURE: the router is a module-level dict keyed on (method, path), read by a private
  _dispatch(); do_GET is the only do_* method` — key on the pair, not the path, so CARD-020's
  `("POST", "/generate")` is one row rather than a second dispatch mechanism. No `do_POST` at
  all today: the stdlib answers `501 Unsupported method`, which is the truthful status for an
  endpoint this card deliberately did not build (G-5), and a hand-written `405` would be code
  written to describe absent behaviour.
- `STRUCTURE: WebUIRequestHandler subclasses BaseHTTPRequestHandler, never
  SimpleHTTPRequestHandler` — the latter maps request paths onto files on disk, and this UI
  serves zero files. Inheriting it would put the working directory one traversal bug away from
  a browser for no benefit. A traversal case is in the 404 parametrisation to pin that.
- `STRUCTURE: pages.py reads the export formats from export.FORMATS and the tiers from
  difficulty.Tier; the three sourcing modes are mirrored by hand` — exactly the split `cli.py`
  already makes (`--export`'s `choices` come from the registry; `--mode`'s do not, because
  COMP-003's modes share no call signature). What is read is *vocabulary*, not a rule: a value
  the form did not offer still parses and is still rejected inward. Hand-copying the lists
  instead would have paid ADR-0019's named "two adapters duplicate the option surface" cost
  where a registry already exists to read. `test_the_form_offers_the_same_option_surface_as_the_cli`
  compares the form's field names against `build_parser`'s own destinations, so drift fails the
  suite rather than being discovered later; `image` is asserted as the one deliberate gap
  (multipart upload is CARD-021).
- `STRUCTURE: LoopbackHTTPServer overrides handle_error to report a lost connection as one line
  and defer everything else to the stdlib's traceback` — a browser reload during a response is
  routine and printed as a crash by default (F-3). Narrowed to `ConnectionError` so a genuine
  bug in the adapter stays loud.
- `STRUCTURE: the failure matrix above is the declared contract; each row has a test` —
  F-1/F-2 in `tests/test_cli.py` (bind failures → exit 3, `OverflowError` caught beside
  `OSError`, and the post-bind failure that must *not* take that path), F-3..F-12 in
  `tests/test_web_server.py`. Corrected in fix cycle 1: this claim was false for F-6, whose
  only "tests" monkeypatched the function they would have exercised — see the fix-cycle
  section below, which also records the two rows (F-11, F-12) the original matrix was missing
  and the one (F-4) it got wrong.

### The one edge that needed deciding: `cli` imports `web`

`STRUCTURE: the import guard gains exactly one directed exemption, _LAUNCH_EDGE = ("cli",
"web"); the reverse stays forbidden` — this is the only place the card's instructions did not
already settle the answer, so it is recorded in full.

ADR-0008 keeps one `[project.scripts]` console entry point and ADR-0019 puts `nonogram serve`
in the argparse tree that entry point owns. Launching COMP-008 from there means `cli` imports
`web`. Both adapters are rank 0, and the guard's rule is `rank(imported) > rank(importer)`, so
that import is flagged as sideways unless something says otherwise. There is no way around it
that is not a dodge: a function-local import is still seen by the `ast` walk (correctly), and
an `importlib.import_module` would be routing around the guardrail rather than satisfying it.

Resolved as a single **ordered pair**, not as "the adapter rank is flat":

- `_ADAPTERS` stays exactly `{"cli", "web"}` at one rank (G-3), pinned by
  `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`.
- `_LAUNCH_EDGE` permits `cli -> web` only. `web -> cli` is still a violation
  (`test_the_import_rule_rejects_each_forbidden_edge[web-to-cli]`), and is separately checked
  against the real source by `test_the_web_adapter_never_imports_the_cli_adapter`.
- Every capability→adapter edge is now checked against *both* adapter names, not just `cli`
  (`cap-to-web`, `orch-to-web` added), so widening the allowlist did not widen the rule.
- Mutation-checked by hand: adding `from nonogram import cli` to `web/pages.py` fails two
  tests, and adding `from nonogram import web` to `clues.py` fails the guard. Neither passes.

⚠ **For the reviewer / model owner:** `meta/architecture/c4/components-CTX-001.puml` says of
COMP-001 and COMP-008 that "the two adapters never call each other" and draws no arrow between
them. That is true of the two *request paths* — the CLI never routes HTTP, the web adapter
never parses argv or owns an exit code — but it is not true of the launch edge ADR-0019 and
ADR-0008 jointly require. The C4 comment (and, if wanted, an ADR-0019 note) should be
reconciled to say "no arrow except the `serve` launch edge". Flagged rather than fixed: the
C4 is generated and lives under `meta/`, which this card does not commit.

### Scope

`SCOPE+ src/nonogram/__init__.py — one line added to the package-layout map (`web/ COMP-008`)
plus the dependency-rule paragraph updated to say "two adapters".` Outside the card's Touches,
but CLAUDE.md names that docstring the canonical package map, so leaving COMP-008 out of it
would have made the card's own architecture documentation wrong on landing. Additive only: no
code, no `__all__`, no import — the "`__init__` imports no submodule" property it describes is
still true of it.

No other file outside Touches was edited. `pyproject.toml` is untouched (no new dependency, no
second entry point). Nothing under `meta/` is committed.

### Guardrail compliance

- **G-1 — existing CLI behaviour unchanged.** `serve` is a sibling `add_parser` on the same
  `subcommands` object; not one `generate` argument, default, `choices`, exit code or stdout
  line was touched. Pinned two ways: the whole pre-existing `tests/test_cli.py` suite still
  passes unmodified in its `generate` half, and `test_generate_is_unchanged_by_the_second_
  subcommand` asserts the complete `generate` namespace literally, so a flag acquiring a
  default — or `serve` bleeding an option into the shared parser — fails. Re-verified
  out-of-process: `nonogram generate --size 10 --density 40 --seed 7 --export json` still
  writes and exits 0; `nonogram generate --size 5` still prints the domain message and exits 3.
- **G-2 — orchestrator and capability modules untouched.** `git diff --stat` covers only
  `src/nonogram/web/*` (new), `src/nonogram/cli.py`, `src/nonogram/__init__.py` (docstring),
  `tests/test_cli.py`, `tests/test_web_server.py` (new). No edit to `orchestrator.py`,
  `sourcing/`, `clues.py`, `solver/`, `difficulty.py`, `export/`. The web adapter does not yet
  call the orchestrator at all — this card has no submission to drive it with — and no domain
  error type was added or widened for the bind failure.
- **G-3 — the allowlist stays two names at one rank.** `_ADAPTERS = frozenset({"cli", "web"})`,
  literally asserted by a test so growth has to be a deliberate edit. It is a set of names, not
  a pattern or a prefix match. The capability rule was not relaxed: lateral
  capability→capability, capability→orchestrator, orchestrator→adapter and shared→capability
  all still fail, and the capability→adapter case is now checked against both adapter names
  instead of one. The single addition is the directed `cli -> web` launch edge described above.
- **G-4 — no domain logic, no validation in `web/`.** The form carries no `min`, `max`,
  `required` or `pattern` (asserted), so an out-of-range value posts and travels inward, as
  `--size 5000` does today. `web/` imports no validator (asserted against `validate_size`,
  `validate_density`, `parse_tier`) and contains no `raise` statement anywhere (asserted with
  an `ast` walk) — it translates failures, it never originates one. The `--port` range is not
  checked either: the socket layer refuses it and `cli.py` maps that to an exit code.
- **G-5 — scope held.** No `do_POST` exists (asserted); a POST gets the stdlib's 501. No
  multipart parsing, no file input in the form, no upload path. No preview: nothing renders a
  grid, a clue or an image, and the only route is the form.
- **G-6 — no new runtime dependency.** `pyproject.toml` unchanged. `web/` imports `http.server`,
  `urllib.parse`, `html`, `sys` and `nonogram` — stdlib and first-party only. ADR-0020's
  rejection of Flask/Bottle/`wsgiref` was not reopened.

### Fix cycle 1 (review 8.0/10 — the 4 Important + 4 Minor findings)

Report: `meta/review/20260830T113613Z-CARD-019-cycle1.yml`. All eight findings fixed; none
dismissed. Landed as commit `8f8e32a` (src/ and tests/ only; nothing under `meta/` committed).
Tests **1215 → 1245** passed (+30), 1 xfailed (`bench_generate`, still CARD-018's, untouched).
Every fix below was mutation-checked by reverting the fix and confirming the new test fails,
then restoring.

- **F-001 — `serve()` was never executed by the suite (F-6 unverified).** The serve loop is now
  `web.serve_on(server)` and is driven directly by three tests against a `_StubServer` whose
  `serve_forever` raises on cue: a `KeyboardInterrupt` is swallowed and the port released, an
  unexpected exception propagates *and* the port is still released (the `finally`), and a clean
  return closes too. No socket needed. **Mutation:** gutting the body to a bare
  `server.serve_forever()` now aborts the run with the escaping `KeyboardInterrupt`; deleting
  only the `finally` fails all three. Previously both mutants survived the whole suite.
  `DECLARATIONS F-001 — matrix row F-6 re-derived (names serve_on, states that an unexpected
  exception is re-raised *after* the socket is released); web/server.py and web/__init__.py
  docstrings updated.`
- **F-002 — matrix row F-4 declared `400` for an unsupported HTTP version; the wire says `505`.**
  Row F-4 now covers only what `parse_request` answers `400` for (an unparseable request line,
  *including* an unparseable version token such as `HTTP/ABC`), keeps its `414`/`431` bounds, and
  points at the new **row F-10** for a parseable-but-unsupported version.
  `test_the_stdlib_rejects_a_bad_request_line_before_the_router` parametrises the cases against a
  live socket, which is what the original row lacked — it was written from memory and nothing
  contradicted it.
  **Corrected in fix cycle 2:** this entry originally claimed the `414`/`431` bounds were "both
  re-probed and correct" and described the test as pinning "`414` at 65536, `431` at 100 headers".
  Only the `414` half had been re-probed. The test sent 70000 bytes and 150 headers — past every
  limit and therefore green for any limit at or below them — and the `431` bound was wrong. See
  F-101 below.
  `DECLARATIONS F-002 — the fix *is* the declaration: row F-4 split, row F-10 added.`
- **F-003 — no socket timeout; every silent connection held a daemon thread.**
  `WebUIRequestHandler.timeout = IDLE_TIMEOUT_S` (30), so `StreamRequestHandler.setup` applies
  it and the request-line read expires instead of blocking forever. Two tests: the shipped
  constant is pinned (30), and the behaviour is measured at a scaled-down 0.25s — eight silent
  connections, `threading.active_count()` must return to baseline — **run against a no-timeout
  control first**, exactly as the AC-052 probes are, so the test skips rather than passes if the
  host cannot show a held thread at all (it can: the control holds, 0 skips observed). A third
  test takes the client's view: the server closes the socket, EOF arrives without the client
  ever sending. No 30s sleep anywhere in the suite.
  `DECLARATIONS F-003 — new matrix row F-11 (bound: dropped after 30s; outstanding threads <=
  connections opened in any 30s window); handler.py module docstring updated to say why a
  transport timeout is not domain logic.`
- **F-004 — no `Host` check, so F-8's access-control claim omitted the browser-mediated path.**
  `_dispatch` now compares the header's name against `handler.ALLOWED_HOSTS`
  (`{localhost, 127.0.0.1, ::1}`, port ignored, `urlsplit`-parsed so `[::1]:8765` reads
  correctly) **before routing**, and answers `400` — not `401`/`403`: nothing is authenticated,
  so AC-053 and the auth-vocabulary rule are untouched. An absent `Host` is served (HTTP/1.0 may
  omit it; a browser never does), which the tests state explicitly rather than leave implicit.
  Ten tests: six accepted forms, six refused (including `127.0.0.1.evil.example.com` and
  `notlocalhost` against a naive substring check), ordering (`400` on *every* path, routed or
  not — the property CARD-020's POST depends on), the escaped rejection body, the no-Host case,
  and the allowlist pinned literally the way `_ADAPTERS` is. Pure HTTP: no domain rule, no
  `raise` (`test_the_web_package_raises_nothing` still green).
  `DECLARATIONS F-004 — matrix row F-8 rewritten (the access control is now two transport
  checks, and the old "loopback binding is the whole of it" is corrected in place, with why it
  read as true); new row F-12; _serve_form's docstring corrected.`
- **F-005 — unescaped path in the 404 body, no `nosniff`, vacuous assertion.** The path is
  `html.escape`d, `_respond` sends `X-Content-Type-Options: nosniff` on every response, and the
  404 parametrisation gains a `/<script>alert(document.domain)</script>` case — so `b"<" not in
  body` is load-bearing for the first time. A companion test asserts `&lt;script&gt;` *is* in
  the body, because "no `<`" would also hold for a handler that stopped echoing the path or for
  a request the stdlib rejected before the router.
  `DECLARATIONS F-005 — _respond/_dispatch docstrings state the escaping and the header;
  matrix row F-7's "short text body" is unchanged and still correct.`
- **F-006 — `_run_serve`'s `except` spanned the whole serve loop.** `web.serve(port)` is replaced
  by two calls, which is what the narrowing requires (and `web/` cannot `raise` a marker
  exception to distinguish them — that rule is what forces the split rather than a wrapper):
  `create_server(port)` binds and is the only thing inside the `try`; `serve_on(server)` runs
  the loop outside it. A post-bind `OSError` now keeps its traceback instead of being reported
  as "pass a different `--port`" with exit 3.
  `DECLARATIONS F-006 — matrix row F-1 re-derived from the new code (bound gains "exactly 1 call
  inside the try"); the two STRUCTURE notes above that named serve(port) amended in place;
  _run_serve and serve_on docstrings say which failure each half owns. Note the API change:
  web.serve no longer exists — web.__all__ is now create_server/serve_on, and nothing is left
  as a dead one-call wrapper.`
- **F-007 — `_LAUNCH_EDGE` had no closure test.**
  `test_the_launch_edge_is_closed_at_the_single_ordered_pair` asserts the literal pair, that it
  is a `tuple`, and that it has length 2 — so turning it into a container of edges fails, which
  the forbidden-edge parametrisation could not catch (it enumerates named edges, and an
  unrelated added pair is not among them). **Mutation:** widening it to
  `{("cli","web"), ("export","web")}` fails this test. `DECLARATIONS F-007 — none (test-only).`
- **F-008 — the auth-vocabulary scan banned the bare substrings `"401"`/`"403"`.** Rewritten
  onto the AST: symbolic names (`UNAUTHORIZED`, `FORBIDDEN`, `PROXY_AUTHENTICATION_REQUIRED`),
  status literals (`401`/`403`, int or str) in **code only** — docstrings are excluded by node
  identity — and `WWW-Authenticate` as a written string. That drops the over-broad half (a
  docstring can no longer trip it; this fix's own docstrings, which explain why there is no
  `403`, are live proof) and the docstring now *states* the limit instead of
  implying cover it lacks: a runtime-computed challenge evades it, and AC-053 rests on the three
  behavioural tests. **Mutation:** an injected `HTTPStatus.UNAUTHORIZED` gate is still caught by
  the scan (and by 6 behavioural tests); a bare `403` literal is caught.
  `DECLARATIONS F-008 — none (test-only); the test's own docstring re-derived.`

Not regressed, re-verified after the fixes: AC-052's `LOOPBACK_HOST = ""` mutant still kills
**3 of 6 tests with 0 skips**; AC-053's three behavioural tests still kill a source-scan-evading
auth gate; the import guard is still `_ADAPTERS = frozenset({"cli","web"})` plus the single
ordered `_LAUNCH_EDGE`, with `web -> cli` forbidden. Guardrails hold: nothing under
`orchestrator.py`, `sourcing/`, `clues.py`, `solver/`, `difficulty.py` or `export/` was touched
(G-2); `web/` still contains no `raise`, no validator import and no browser-side constraint
(G-4); no new dependency (G-6); `generate`'s parsing, defaults and exit codes are untouched
(G-1).

### Fix cycle 2 (review 9.5/10 — 1 Important + 4 Minor findings)

Report: `meta/review/20260830T122139Z-CARD-019-cycle2.yml`. All five findings fixed; none
dismissed. Landed as commit `7fd9048` (src/ and tests/ only; nothing under `meta/` committed).
Tests **1245 → 1261** passed (+16), 1 xfailed (`bench_generate`, still CARD-018's, untouched).
Two files touched: `src/nonogram/web/handler.py` and `tests/test_web_server.py` — no other
capability module, so G-2 is untouched by construction.

Every numeric bound below was probed against a live socket by a **standalone script that imports
nothing from the test tree**, before any test was written — the second-implementation rule, applied
to the thing that went wrong twice: bounds written from a library constant instead of from the wire.

- **F-101 — row F-4's header bound refuted a second time: the limit is 99 fields, not 100.**
  Probed: 98 → `200`, 99 → `200`, 100 → `431`, 101 → `431`. The cause is that
  `http.client.parse_headers` appends the terminating CRLF to the very list it length-checks
  against `_MAXHEADERS` (100), so the ceiling on *real* header fields is 99 — the row now states
  that reason inline, so the next reader does not "correct" it back to the constant. The
  request-line half was right and stays (probed 65536 → routed/`404`, 65537 → `414`), but the two
  halves of the cell had been written with opposite semantics ("≤ 65536" meant 65536 is accepted,
  "≤ 100" meant 100 is rejected); both now mean *accepted*. The undeclared second cause of the
  same status is declared too: one header line over `_MAXLINE` answers `431 Line too long`
  (probed 65536 → `200`, 65537 → `431`), which is a different failure from too many headers
  wearing the same number. New `test_the_declared_size_bounds_are_exact` pins all three bounds at
  N *and* N+1 — the old parametrisation sent 70000 bytes and 150 headers, comfortably past every
  limit and therefore green for any limit at or below them, which is exactly why nothing
  contradicted the wrong row. **Mutation:** flipping all six expected statuses fails all six
  params, so none is vacuous; the six sizes are byte-exact by construction (`_request_line_of` /
  `_header_line_of` assert their own length).
  `DECLARATIONS F-101 — matrix row F-4 re-derived from the probe: bound now reads "request line
  <= 65536 bytes incl. CRLF; header fields <= 99 (_MAXHEADERS counts the terminating CRLF); any
  single header line <= 65536 bytes incl. CRLF", and the Failure mode / Declared behaviour cells
  name the over-long header line as the second 431 cause. The fix-cycle-1 F-002 entry's "both
  re-probed and correct" and its "414 at 65536, 431 at 100 headers" are corrected in place rather
  than deleted, since the false claim is what the finding is about.`
- **F-102 — the `Host` check accepted userinfo and path forms.** `_host_is_local` now returns
  `False` for any header containing `@` or `/`, before parsing. Not a hole before and not
  presented as one: in every accepted case (`user:pass@127.0.0.1`, `evil.example.com@127.0.0.1`,
  `127.0.0.1/../evil`) the authority's host component genuinely *was* loopback, and the dangerous
  reversal `127.0.0.1@evil.example.com` was already refused — which is why that shape is now a
  parametrised case too, to prove the narrowing did not quietly replace `urlsplit` with a
  substring test. What it buys is that the set of accepted header *values* is now as small as the
  set of accepted *names*, which is what row F-12 declares. **Mutation:** removing the two-character
  guard fails exactly the three new params.
  `DECLARATIONS F-102 — matrix row F-12's bound re-derived: "exactly 3 accepted host names" is
  now also "exactly 3 accepted host-header shapes, with @ and / refused"; _host_is_local's
  docstring states the authority-not-a-URL reason.`
- **F-103 — the auth scan's claim was overstated.** Claim-accuracy only; the scan is unchanged,
  deliberately. Narrowing the literal check to a "status position" would have to enumerate every
  call that can carry one, and would stop catching `status = 403` followed by
  `self._respond(status, ...)` — a real loss to remove a trap that only two integers in the whole
  range can spring. So the prose is corrected instead, in both places it was wrong: the card's
  F-008 entry drops the port-number half, and the test's own docstring now states plainly that
  `_MAX_BODY_BYTES = 403` **does** fail it, names the failure message, and names the right
  response (spell the constant differently — never widen the scan, which is the edit that ends
  the guard). Verified by injecting exactly that constant: `handler.py:46 uses the literal 403`.
  `DECLARATIONS F-103 — none in code (test-prose only); two false claims corrected, one in the
  card's F-008 entry, one in test_the_package_contains_no_authentication_vocabulary's docstring.`
- **F-104 — only the first of duplicate `Host` headers was checked.** `_dispatch` now reads
  `self.headers.get_all("Host")` and refuses with `400` when the values disagree; one value
  repeated is served, since a repetition says nothing new. Both orders are pinned, because reading
  only the first accepted `127.0.0.1, evil.example.com` while refusing the reverse — and that
  asymmetry is the shape that becomes a smuggling difference the moment anything sits in front of
  the socket. **The absent-`Host` leniency is deliberately NOT changed**, and is now *declared*
  rather than assumed: it applies to every protocol version, HTTP/1.1 included, where RFC 7230
  would require `400`. Refusing it would gain nothing (a browser cannot suppress `Host` — it is a
  forbidden header name to `fetch`/XHR, so an absent one is never the attacker's shape) and would
  break `curl --http1.0` *and* this module's own AC-052 interface probes, which send
  `GET / HTTP/1.0` with no `Host` — i.e. it would break the evidence AC-052 rests on. The
  no-`Host` test is now parametrised over both versions so the leniency is pinned where it was
  previously only true by accident. **Mutation:** reverting to `get("Host")` fails the
  `local-then-foreign` and `two-loopback-names` params.
  `DECLARATIONS F-104 — matrix row F-12 re-derived: bound gains "<= 1 distinct Host value per
  request", the Declared behaviour cell states the get_all rule and restates the absent-Host
  leniency as an accepted RFC deviation with its reason and its cost; _dispatch's docstring
  updated to match. Row F-8's "exactly 2 access-control checks, both on the transport" was
  re-derived and is still correct — this adds a clause to the Host check, not a third check.`
- **F-105 — `nosniff` was unasserted on the 200 path.** One assertion added to
  `test_the_form_page_is_served_as_html`, plus a docstring saying why the 200 path is where it
  matters most once CARD-020 renders a result page built from user input. **Mutation:** removing
  the `send_header` line now fails the form test as well as the five 404 params — previously the
  form test passed unchanged.
  `DECLARATIONS F-105 — none (test-only); _respond's "sent on every response" was re-derived and
  is correct — it was the test coverage, not the claim, that was partial.`

Also corrected while in the file: the module docstring of `tests/test_web_server.py` said it
covers matrix rows "F-1 through F-9", which stopped being true when fix cycle 1 added F-10..F-12.

Not regressed, re-verified by mutation after the fixes on this head: AC-052's `LOOPBACK_HOST = ""`
still kills **exactly 3 of 6** tests with **0 skips**; AC-053's scan-evading gate
(`HTTPStatus(200 + 201)`, `"WWW-Auth" + "enticate"`) is still killed by **6 behavioural tests**
while the scan passes it, and the scan still catches both `HTTPStatus.UNAUTHORIZED` and
`HTTPStatus(403)`; the Host allowlist still refuses `127.0.0.1.evil.example.com`, `notlocalhost`,
`127.0.0.2`, `127.1`, the octal/decimal/v4-mapped forms and the empty header. The import guard was
not touched at all this cycle (`cli.py` and `__init__.py` are not in the diff), so `_ADAPTERS`,
`_LAUNCH_EDGE` and the forbidden `web -> cli` edge are unchanged. `web/` still contains no `raise`,
no validator import and no browser-side constraint (G-4); no new dependency (G-6); nothing under
`orchestrator.py`, `sourcing/`, `clues.py`, `solver/`, `difficulty.py` or `export/` (G-2).

### Notes for CARD-020

`pages.FORM_ACTION` is `/generate` and every form control is named for the
`GenerationRequest` field it fills, so the mapping is a lookup rather than a translation table.
`("POST", "/generate")` is one `ROUTES` row plus a `do_POST` that calls the existing
`_dispatch("POST")` — which, since fix cycle 1, applies the `Host` allowlist (F-12) before it
routes, so the POST inherits the cross-origin protection instead of having to remember it. The `image` field is absent by design (CARD-021), and
`test_the_form_offers_the_same_option_surface_as_the_cli` asserts that gap is exactly one field
wide, so it will fail the moment the upload lands without the form catching up.

### Orchestrator notes

- **[Env]** forge 2026.8.17 — meets `forge.min_version` 2026.8.17.
- **[Blocker check]** none — no `[BLOCKER` marker in the worktree card (prefix-matched, not exact-token).
- **[Guard]** implementation produced 1 commit (`623774c`); `meta/` correctly excluded from it.
- **[Build gate]** PASSED (full suite, 20.0s). Independently re-run by the orchestrator in the
  worktree venv: **1206 passed, 1 xfailed, exit 0**, against a main baseline of 1156 passed,
  1 xfailed — **+50 tests, no regressions**. Non-vacuous (1206 executed, not an empty room).
  Impact narrowing N/A: `pytest-testmon` is not installed, and the python-pro recipe forbids
  import-graph guessing — full suite is the correct gate here.
  The pre-existing `bench_generate.py::test_20x20_p95_is_under_5s` xfail is untouched and still
  xfail (it belongs to CARD-018).
- **[Scope]** GROWN, not runaway — continuing. Diff = 8 files. One existing file outside
  `Touches:` — `src/nonogram/__init__.py`, declared by the agent as `SCOPE+`, **docstring-only**
  (updates the canonical package-layout map CLAUDE.md points at, to name COMP-008). No component
  spread: `__init__.py` maps to no COMP in trace.yml.
- **[Touches drift]** `src/nonogram/__init__.py` — outside the prediction, additive, justified.
  Recorded for `forge:retrospective`'s Touches calibration (Step 4e).
- **[Scope poach] not a poach.** CARD-019's diff mechanically covers CARD-020's
  `src/nonogram/web/**.py` glob (~50% of its predicted footprint), but CARD-020's *work* is
  verifiably absent: no `do_POST` handler, no `GenerationRequest` mapping code, orchestrator not
  imported (all three appear only in docstrings explaining what CARD-020 will add). This is the
  intended sequential hand-off, not scope absorption — G-5 held.
- **[Guardrails]** G-1..G-6 all verified independently. G-2 confirmed mechanically: no
  orchestrator or capability-module file appears in the diff.
- **[System contract]** section stale at start — refreshed from the model before review 1:
  **+ADR-0021/R1** / −none. At decompose time ADR-0021/R1 was scoped to CARD-020/021
  (it governs the POST handler), but its declared scope is `src/nonogram/web/**`, which
  this card's footprint now matches — so the lens applies it here too. Its check is
  `review-lens`, and for this card it is satisfied by absence (no `do_POST` exists at
  all, G-5). Refreshed rather than left stale so the card records what the review
  actually judged against.
- **[Review sync]** 1 report → `meta/review/20260830T113613Z-CARD-019-cycle1.yml`.
  A stale duplicate cycle-1 report (`20260830T112120Z`, from an interrupted earlier
  review run) was deleted from BOTH the worktree and the main repo — two reports for
  one cycle would double-count findings for `forge:fix` and `forge:retrospective`.
- **[Review 1/3] 8.0/10 — FAIL (severity gate).** Risk `low`, lane `deep`. Zero Critical.
  **4 Important** findings block success regardless of the score clearing `min_score: 8`.
  Nothing in the diff alters existing behaviour, breaks a contract, or opens a security
  boundary — every deduction is a completeness gap.
  - F-001 `web/server.py` — `serve()` is never executed by the suite; failure-matrix row
    F-6 is unverified. Proven by mutation: gutting the whole `try/except
    KeyboardInterrupt/finally: server_close()` leaves all 1206 tests green, because the
    three cli-side tests monkeypatch the very function they would otherwise exercise.
  - F-002 card row F-4 — declared bound REFUTED: an unsupported HTTP version answers
    `505`, not the declared `400`. (The row's other two bounds hold — probed `414` at
    65536 and `431` at 100 headers.)
  - F-003 `web/handler.py` — no socket `timeout`; `rfile.readline()` blocks forever and
    each silent connection holds a daemon thread. Verified: 12 silent connections took
    the process from 2 to 14 live threads. No matrix row declares this boundary.
  - F-004 `web/handler.py` — no Host-header check, so F-8's "loopback binding is the whole
    of the access control" omits the browser-mediated path (DNS rebinding / cross-origin
    form POST). Exploit impact on THIS diff is nil (one static GET, no state, no secret),
    but CARD-020's `POST /generate` writes files to a caller-supplied `out` dir — cheapest
    to land here, before that.
  Plus 4 Minor (no deduction): unescaped path reflected into the 404 body with a vacuous
  covering assertion; `_run_serve`'s `except` spans the whole serve loop so a post-bind
  `OSError` misreports as a port problem; `_LAUNCH_EDGE` lacks the closure test `_ADAPTERS`
  has; the auth-vocabulary scan bans bare substrings `"401"`/`"403"`.
- **[Adversarial]** The two claims most worth doubting were both mutation-verified and HELD:
  - **AC-052 is genuinely non-vacuous.** `LOOPBACK_HOST` mutated to `""` (wildcard bind —
    chosen deliberately because it evades the source-grep tests that `"0.0.0.0"` would
    trip): **3 of 6 tests failed, 0 skipped**, killed independently by both the connect
    probe and the firewall-independent non-`SO_REUSEADDR` bind probe. Not a read-back of
    `server_address`. IPv4-only is sound — the bind is a literal IPv4 address.
  - **AC-053 is genuinely non-vacuous.** A real auth gate evading the source scan
    (`HTTPStatus(200 + 201)`, `"WWW-Auth" + "enticate"`) was killed by three behavioural
    tests. The grep test alone would have missed it (see Minor F-008).
- **[System contract]** 6/6 ✓ holds, 0 violated, 0 unchecked. ADR-0019/R1 re-derived by
  mutation in both directions; ADR-0021/R1 satisfied by absence (no `do_POST`, `ROUTES ==
  {('GET','/')}`) as predicted; CON-005/INV-001/INV-002/INV-003 confirmed green with their
  paths absent from the diff.
- **[Guard]** The import-guard change was TIGHTENED, not weakened — the highest-consequence
  thing on this card, and it survived scrutiny. Promoting `web` from implicit capability
  (rank 2) to adapter (rank 0) makes `orchestrator → web` newly *forbidden*; `_LAUNCH_EDGE`
  is a single ordered-pair equality with no pattern or set to widen. Mutation-verified both
  directions. Reviewer also ruled the `src/nonogram/__init__.py` SCOPE+ call correct.
- **[Housekeeping]** Reviewer restored the tree clean after 5 mutants — `git status
  --porcelain src/ tests/` empty, diff still 8 files / +1353 / −22. Verified independently.
- **[Correction]** The card's `Review score` field read `7.5 (cycle 1/3)` when this cycle's
  bookkeeping ran. That value was written by the INTERRUPTED review run — the same one that
  left the superseded `20260830T112120Z` report — and was never the verdict of a completed
  review. Corrected to **8.0**, the score of the only cycle-1 review that finished and whose
  report survives. Caught because the field was not the `—` the write anchored on; a blind
  write would have left a dead run's number standing as this cycle's result.
- **[Rebase]** Rebased onto `main` @ `873a207` (CARD-018's solver work) before fixing —
  so the fix cycle and re-review judge against reality, not the tree this card was built
  on. Clean, **no conflicts**: CARD-018 touched `solver/**`, `difficulty.py`,
  `bench_generate.py`, `test_solver.py`, `test_timeout.py`; this card touches none of them.
  New head `d897926`, diff unchanged at 8 files / +1353 / −22.
- **[Build gate]** RE-RUN on the new base: **1215 passed, 1 xfailed, exit 0** vs a
  new-main baseline of 1165 + 1 → the same **+50 tests, no regressions** against the
  changed solver. (Full suite, 33.3s.)
- **[Observation — not this card]** Two facts about the new base worth routing elsewhere:
  (a) `bench_generate.py::test_20x20_p95_is_under_5s` is STILL xfail after CARD-018 merged,
  though closing AC-037 was that card's purpose; (b) full-suite wall time on `main` went
  18.7s → 32.9s across that merge (+76%). Neither is CARD-019's to fix — flagged for the
  wave retrospective / `suite-timing.log` trend.
- **[Fix 1] orchestrator record** — 8/8 findings fixed in commit `8f8e32a` (6 files, src/
  and tests/ only). Build gate independently re-run: **1245 passed, 1 xfailed, exit 0**
  (from 1215 — +30 tests). Non-regression re-verified by the fixer and spot-checked here:
  AC-052's `LOOPBACK_HOST=""` mutant still kills 3 of 6 with 0 skips; AC-053's three
  behavioural tests still kill a scan-evading auth gate; the import guard is unchanged
  except for the added closure pin.
- **[Incident — orchestrator error, no code lost]** After the fix cycle I ran
  `rsync -a --delete` main→worktree to clear an unmerged index entry my own bad
  `git stash pop` had created, and destroyed every meta/ file the fix agent had written:
  the card's fix-cycle notes, the corrected failure-matrix rows, and the review YAML's
  `status: fixed` markers. Code was never at risk (`8f8e32a` was already committed) and
  `src`/`tests` were untouched. Recovered by asking the fix agent to re-emit from its own
  context rather than reconstructing from a summary; all three artifacts verified restored
  and cross-checked against the committed blobs. **Root cause:** the new cards and ADRs are
  uncommitted in main, so worktrees can't see them without a sync — the sync was a
  workaround for that, and syncing INWARD is what made it destructive. Fix: commit the
  planning artifacts once this card merges, so no inward sync is ever needed.
- **[Review sync]** 1 report → `meta/review/20260830T122139Z-CARD-019-cycle2.yml`. No stale
  cycle-2 report existed.
- **[Review 2/3] 9.5/10 — FAIL (severity gate).** Risk LOW, lane FAST. Score improvement
  +1.5 (8.0 → 9.5), far above `min_improvement: 0.5`. Zero Critical. **1 Important** blocks
  success regardless of score.
  **All 8 cycle-1 fixes HELD** — 19 mutants run, 18 killed, 1 survived by design. Highlights:
  gutting `serve_on` aborts the run and deleting only its `finally` fails all three stub
  tests; the five HTTP statuses are genuinely wire-probed (flipping all five expected values
  failed all five params); the timeout test's control genuinely discriminates (giving it a
  timeout makes the test SKIP, not pass) with no 30s sleep anywhere (slowest web test 1.53s);
  the Host allowlist killed a naive-substring mutant on exactly `127.0.0.1.evil.example.com`
  and `notlocalhost`, and a 30-header-shape sweep rejected decimal, octal, v4-mapped,
  `127.0.0.2` and `127.1`.
  **Non-regression held:** AC-052's `LOOPBACK_HOST=""` mutant still kills 3 of 6 with 0 skips;
  AC-053's scan-evading gate still killed by 6 behavioural tests; the import guard is still a
  literal 2-name frozenset plus one ordered pair, with `web → cli` killed from two angles.
  **"Absent Host is served" ruled deliberate and safe, not a hole** — `fetch`/XHR treat `Host`
  as a forbidden header name so page JS can neither suppress nor forge it, and this module's
  own AC-052 probes send HTTP/1.0 without one, so refusing it would break the evidence AC-052
  rests on.
- **[Severity gate] F-101 (Important)** — matrix row F-4's REWRITTEN header bound is refuted
  by probe a second time: the limit is **99**, not 100 (99 headers → 200, 100 → 431, because
  `_MAXHEADERS` counts the terminating CRLF). The request-line half of the same cell is right
  (65536 accepted, 65537 → 414), so one bound cell mixes two semantics; the covering test
  sends 150 headers and never touches the boundary; and the card asserts "both re-probed and
  correct" while its own prose says "431 at 100 headers". This row has now been wrong twice —
  which is the argument for fixing it rather than waiving it.
  Plus 4 Minor: Host accepts userinfo/path forms (`user:pass@127.0.0.1`) — not exploitable,
  the host component really is loopback; the auth scan still trips on a non-status `403`
  literal so the card's "a port number can no longer trip it" is overstated; only the first of
  duplicate `Host` headers is checked and HTTP/1.1-without-Host is served (RFC deviations, not
  browser-reachable); `nosniff` is unasserted on the 200 path (removing it killed only the 404
  params). One undeclared boundary found: an over-long single header VALUE also answers 431.
- **[Adversarial]** The API change `web.serve` → `create_server`/`serve_on` ruled **justified,
  not scope creep**: G-4 forbids `web/` raising a marker exception (mechanically pinned), so
  splitting the call is the only remaining mechanism to narrow the `except` to the bind.
  Fan-in 1, same unreleased card, no dead wrapper. AC-052 unweakened — the generic
  `test_no_api_in_the_package_can_widen_the_bind_address` sweeps `web.__all__` and covered the
  new pair without being edited.
- **[System contract]** 6/6 ✓ holds, 0 violated, 0 unchecked. ADR-0019/R1 re-derived by
  mutation both directions, zero `raise` in `web/`, and the new Host check and escaping ruled
  transport facts answered with a status code — not domain rules. ADR-0021/R1 satisfied by
  absence. All 8 check-refs resolve to real tests, green in the 1245 run.
- **[Card integrity]** Reviewer confirmed the destroyed-and-restored paperwork survived intact;
  the only two inaccuracies also appear in commit `8f8e32a`'s own message, so they were
  **authored, not corrupted** by the incident.
- **[Fix 2] orchestrator record** — 5/5 cycle-2 findings fixed in commit `7fd9048`
  (2 files: `web/handler.py`, `tests/test_web_server.py`; +226/−29). Build gate
  independently re-run: **1261 passed, 1 xfailed, exit 0** (from 1245, +16).
  `meta/` verified absent from the branch (0 files); the worktree's 35 meta entries stay
  uncommitted, and the fixer wrote them LAST and reported them explicitly so they could be
  synced out immediately — the countermeasure to the incident recorded above. Synced.
- **[Verification]** I re-probed F-101's core claim myself rather than trusting the chain:
  98 and 99 header fields → `200`; 100 and 101 → `431 Too many headers`. The corrected bound
  (`header fields <= 99`, because `parse_headers` appends the terminating CRLF to the list it
  length-checks against `_MAXHEADERS = 100`) is exact. Both halves of row F-4 now mean
  *accepted*, where before one meant accepted and the other rejected.
- **[Judgement call — F-103, accepted]** The fixer took the reviewer's second option (correct
  the claim) over the first (narrow the scan). Rationale checked and agreed: narrowing to a
  status position would stop catching `status = 403` → `self._respond(status, ...)`, which is
  a real trap worth keeping, and the residual over-breadth (`_MAX_BODY_BYTES = 403` trips it)
  is now a declared, reasoned boundary with a stated remedy rather than an unstated surprise.
  Trading an honest narrow claim for a dishonest broad one would have been the wrong way round.
- **[Review sync]** 1 report → `meta/review/20260830T125259Z-CARD-019-cycle3.yml`.
- **[Review 3/3] 9.6/10 — PASS.** Zero Critical, **zero Important** — the severity gate
  clears for the first time. All five cycle-2 fixes HELD under 11 mutants, 11 killed, 0
  survived. Reviewer's explicit recommendation: **MERGE**, escalation not warranted.
  Note on `min_improvement`: cycle 2→3 is +0.1, below the 0.5 threshold, but that rule
  exists to catch a *stalling* loop — a cycle with no gating findings is a converged
  review, not a stalled one. Recorded rather than silently ignored.
  **The failure matrix is accurate for the first time in three cycles** (12/12 rows, 0
  refuted). F-101's boundaries independently re-probed on the wire: request line
  65536→routed / 65537→414; header fields 99→200 / 100→431 "Too many headers"; header
  line 65536→200 / 65537→431 "Line too long".
  One Minor left open (F-201, non-gating): two residual Host-*shape* documentation gaps —
  `_host_is_local`'s docstring misfiles bare `::1`, and row F-12's "exactly 3 accepted
  shapes" omits `[::1]` without a port and an empty port. Both fail-closed, no client
  affected (browsers and curl always bracket IPv6), documentation-only. `ALLOWED_HOSTS`'s
  unbracketed `"::1"` is correct and must not be "fixed".
- **[AC/EC check] All criteria/constraints ✓** — verified by the orchestrator against the
  code, not the reports:
  - **AC-052** ✓ `tests/test_web_server.py::TestWebServer_BindsLoopbackOnlyByDefault`
    (6 tests, green) — the class name is literally the criterion's declared `test:`.
  - **AC-053** ✓ `tests/test_web_server.py::TestWebServer_ProcessesRequestsWithoutAuthentication`
    (7 tests, green) — likewise.
  - **EC:** none declared on this card (correct — the shape calls for none).
  - **G-1** ✓ `nonogram generate --mode random --size 10 --density 45 --seed 42 --export json`
    produces a **byte-identical** file on this branch and on `main`; `--size 5` still exits 3.
    `serve` is registered as a *sibling* subcommand under the same console entry point.
  - **G-2** ✓ no orchestrator or capability file in the diff (mechanical check).
  - **G-3** ✓ `_ADAPTERS = frozenset({"cli", "web"})`, `_LAUNCH_EDGE = ("cli", "web")`,
    both pinned by their own asserts; guard tests green.
  - **G-4** ✓ zero `raise` in `web/`; no domain validator imported.
  - **G-5** ✓ `do_POST` is docstring prose only (`hasattr` False); `ROUTES == {('GET','/')}`.
  - **G-6** ✓ `pyproject.toml` absent from the diff — no new dependency.
- **[Deferral scan]** No real deferrals. Every hit is a forward-looking design note
  ("a later card…") or a test double (`_StubServer`); the genuinely deferred scope
  (POST, upload, preview) is tracked as CARD-020/CARD-021 and CON-008, not lost in a comment.
