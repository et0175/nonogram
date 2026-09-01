# ADR-0020: Web UI HTTP layer

**Status:** Accepted
**Date:** 2026-08-30
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** —
**Pattern:** —
**API-Posture:** server-rendered

## Context

FR-017 adds a local web UI alongside the existing CLI (CON-007 supersedes CON-001's "no web/GUI" statement): a form for generation options, a submission endpoint, and a result page, living inside COMP-008 "Web UI Adapter" (ADR-0019) as a second inbound adapter parallel to COMP-001 (cli.py). Something has to serve HTTP for that adapter, and ADR-0006 already fixed the project's dependency baseline at stdlib + Pillow + NumPy, closing off third-party runtime dependencies except where a structurally identical need (CON-006, PDF export via Pillow's existing capability) justified staying inside that baseline rather than adding to it.

The image-upload half of FR-017 is the load-bearing detail: `cgi.FieldStorage`, the standard library's only multipart/form-data parser, was removed in Python 3.13 (PEP 594), and this project's floor is Python 3.14. Whatever serves HTTP either brings multipart parsing with it as a library feature, or that parsing has to be hand-written against lower-level stdlib pieces (`email.parser`) — there is no stdlib shortcut left. CON-008 has already scoped the UI down to one form page, one POST endpoint, and one result page, with no in-browser preview, no templating engine, no sessions, and no cookies needed.

NFR-003 requires the server to bind 127.0.0.1 only, with no authentication, per BCON-0001 (hard: the web UI must never be network-exposed, single actor, no accounts). That half of NFR-003 was deliberately not surfaced as a separate DEC: no candidate under consideration here makes loopback binding optional, hard to express, or off by default, so the binding posture is recorded as a required consequence of this decision rather than as a redundant decision of its own.

DEC-020 is a platform-axis (stack) decision: it reopens ADR-0006's dependency baseline in one narrow, additive direction — whether serving FR-017's small surface justifies one new third-party runtime dependency, or must be built on stdlib. It depends on DEC-021 (ADR-0019), which places this HTTP layer inside COMP-008; that placement is assumed here as context but not re-litigated.

## Decision

We adopt **`stdlib_http_server`**: `http.server.ThreadingHTTPServer` with a `BaseHTTPRequestHandler` subclass inside COMP-008 (ADR-0019) — a hand-written router over (method, path), the form page served as a static HTML string constant, urlencoded submission bodies parsed with `urllib.parse.parse_qs`, and, for the image-upload path specifically, multipart/form-data parsed by hand via `email.parser.BytesParser` over the reconstructed headers-plus-body.

This keeps ADR-0006's dependency baseline closed rather than reopening it in substance, on the same precedent CON-006 already set for PDF export: a structurally identical need (a missing/awkward stdlib capability) was met by working within the existing baseline rather than adding to it. It is also the second time this project has declined a comparable convenience dependency for the CLI adapter (ADR-0010's stdlib-argparse choice), and choosing a dependency here would need to clear that same bar. CON-008's scoping — one form, one POST, one result page, no sessions, no cookies — keeps the surface small enough that hand-rolled routing and hand-rolled multipart parsing are the genuinely fiddly, but bounded, cost of staying inside the baseline.

As a **required consequence** of this decision, the server binds loopback-only by construction: `HTTPServer(("127.0.0.1", port), ...)` is the literal constructor argument, satisfying NFR-003's AC-052 (socket bound to 127.0.0.1, refusing other interfaces) and AC-053 (no authentication enforced) directly, per BCON-0001.

## Alternatives considered

### bottle_microframework

Add Bottle as a single new runtime dependency: a routing decorator per endpoint, `request.forms`/`request.files` for urlencoded and multipart bodies (multipart parsing comes for free), a built-in template for the form page, and `run(host="127.0.0.1", port=...)`. Bottle is single-file, pure-Python, and has zero transitive dependencies, making it the smallest possible reopening of ADR-0006, and it removes the one genuinely hard piece of the stdlib option (multipart upload). It was rejected primarily on precedent: this project has twice declined a comparable convenience dependency (CON-006 for PDF export, ADR-0010's stdlib-argparse choice for the CLI), and choosing a dependency here needs justification proportional to that precedent. CON-008's "small surface" argument — one form, one POST, one result page — did not clear that bar, and Bottle's own bundled dev server carries the same "not for production" caveat as `http.server` without BCON-0001's threat model applying differently, so the dependency would buy ergonomics only, not robustness.

### flask_microframework

Add Flask: the most familiar and best-documented option, with Werkzeug handling multipart uploads and request parsing, Jinja2 rendering the form page, and declarative `errorhandler` registration mapping domain exceptions to responses (a clean fit for EC-003). Rejected because it pulls five transitive dependencies (Werkzeug, Jinja2, click, itsdangerous, blinker) for a surface CON-008 has already scoped down to one form, one POST, and one result page — grossly disproportionate to the need, and the largest possible reopening of ADR-0006. It also introduces project structure (a templates directory, app/blueprint conventions) the src-layout package of ADR-0008 does not currently have, and would set the precedent that "a framework is easier" outweighs the closed baseline — exactly the norm CON-006 established against.

### wsgiref_simple_server

`wsgiref.simple_server` with a hand-written WSGI application callable: stdlib only, like the chosen option, but written to the WSGI interface so the app could later be served by a real WSGI server without rewriting the adapter, and trivially testable without opening a socket (call the callable with a synthetic `environ`). Rejected because the portability it buys is optionality for a network-exposed future that BCON-0001 (hard) explicitly forbids — the web UI must never be network-exposed, so there is no future WSGI deployment to prepare for. It also does not solve the actual hard part: multipart parsing is still hand-rolled on top of `email.parser` either way, and the raw WSGI environ/`start_response` protocol is more awkward to write by hand than `BaseHTTPRequestHandler` for a three-endpoint UI.

## Consequences

### Positive
- Keeps the dependency baseline closed — the precedent this project has protected repeatedly (CON-006 for PDF export, ADR-0010 for CLI argument parsing), now extended a third time to the web UI's HTTP layer.
- No install- or audit-surface growth for a single-user hobby tool; the web UI stays as cheap to install as the CLI, with zero new third-party runtime dependencies.
- Loopback-only binding (NFR-003, BCON-0001) is a literal constructor argument (`HTTPServer(("127.0.0.1", port), ...)`), so it is trivially visible in the code and trivially verified by AC-052/AC-053, rather than resting on a framework default that could silently change.
- `http.server`'s documented "not recommended for production" caveat is defanged here: BCON-0001 already forbids network exposure, so the threat model that caveat addresses does not apply to this deployment.

### Negative
- The multipart/form-data upload path must be hand-rolled via `email.parser.BytesParser` (no `cgi.FieldStorage` since Python 3.13) — the fiddliest part of the whole capability, and easy to get subtly wrong on boundary handling, encoding, and large bodies; it needs its own focused test coverage.
- Hand-written routing and manual status/header/Content-Type writing for every response; EC-003's structured failure responses must be shaped by hand rather than via a declarative error-handler mechanism.
- More project-owned plumbing code to write, test, and maintain than either microframework alternative, in a spot where the code is HTTP mechanics rather than domain value.

### Neutral
- ADR-0006's platform.yml stack entry is unchanged; this ADR narrowly reopens the baseline's *scope* (what may serve HTTP) without changing its *value* — platform.yml still reads "Python 3.14 + Pillow + NumPy".
- The loopback-only bind (NFR-003, BCON-0001) is deliberately recorded here as a required consequence of this decision rather than as a separate DEC — no candidate considered made it optional, so there was no trade-off left to decide.
- Establishes the concrete shape (router, request parsing, multipart handling) that COMP-008 (ADR-0019) implements; the structural import-guard change ADR-0019 makes to allow COMP-008 to import the orchestrator is a separate but related consequence of that sibling decision, not this one.

## References

- DEC-020 (resolved by this ADR)
- ADR-0019 (COMP-008 "Web UI Adapter", the component this HTTP layer lives inside)
- ADR-0006 (dependency baseline this ADR narrowly reopens in scope, not in value)
- ADR-0010 (stdlib-argparse precedent for the CLI adapter)
- FR-017 (the web UI capability this ADR serves)
- NFR-003, AC-052, AC-053 (loopback-bind, no-authentication requirements satisfied as a required consequence)
- CON-006, CON-007, CON-008 (dependency-baseline precedent; the CLI/web dual-interface statement; the scoped-down UI surface)
- EC-003 (structured failure responses this ADR's hand-written error mapping must satisfy)
- CTX-001 (the single bounded context this adapter lives inside)

## History

- 2026-08-30: Created — resolves DEC-020. Adopted stdlib `http.server` + hand-rolled multipart parsing over Bottle, Flask, and `wsgiref`, keeping ADR-0006's dependency baseline closed on the same precedent CON-006 set for PDF export.
