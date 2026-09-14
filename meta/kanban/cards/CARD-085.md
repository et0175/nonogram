# CARD-085: The admin panel can be reached from somewhere other than this machine, but only with a credential

**Status:** in_progress
**Priority:** P1
**Category:** feature
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/085-admin-auth-for-remote-access
**Worktree:** ../PythonProject4-CARD-085
**Source:** owner request — the Render deploy 404s on every route; "how can I switch authorisation on render?"
**Idea:** —
**Wave:** 1
**Depends on:** — (CARD-081 merged 44a5af4, which added the guard this card widens)
**Touches:** src/nonogram/admin/app.py, tests/test_admin_auth.py (new), tests/test_admin_binding.py, render.yaml, ADMIN_SETUP.md
**Review score:** —
**Started:** 2026-09-14
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

`https://nonogram-admin.onrender.com` returns 404 on every route. The deploy is
healthy and so is the database — Postgres has 6 days 20 hours of uptime and all
86 rows. The 404 is CARD-081's `_reject_non_loopback_requests` refusing the
`Host` header `nonogram-admin.onrender.com`, which is exactly what it was
written to do.

Measured, with `DATABASE_URL` pointed at a black-holed address so a database
attempt would be unmistakable:

| request | result |
|---|---|
| `Host: nonogram-admin.onrender.com` | **404 in 6.9 ms** — no socket opened |
| `Host: localhost` | **500 after 75 s** — `OperationalError` |

The guard is a `before_request` hook, so it returns before any view runs and
therefore before any query. Nothing about the 404 involves the database.

### Why the guard cannot simply be widened

The admin has **no authentication of any kind** — no login, no session check,
no API key; `grep` over `src/nonogram/admin/` finds none. It has `POST
/regrade`, which rewrites `difficulty_score`, `difficulty_tier` and
`strategies_used` on every row it can grade, and after CARD-084 keeps no copy of
what it replaced. It also has puzzle delete and bulk curation. Adding the Render
hostname to `ALLOWED_HOSTS` therefore publishes an unauthenticated destructive
admin panel to the internet.

So the host check is not the thing to remove. It is the thing to **replace, in
the deployed configuration, with something that actually establishes who is
asking** — which is what CARD-081's own docstring already says the header check
is standing in for:

> The admin panel has no authentication, no CSRF token and a route that
> rewrites every stored grade, so NFR-003's answer to "who can reach this?" is
> "whoever is on this machine".

### Why this is in the app and not in Render

Render has no authorisation switch for web services. Its private services have
no public URL at all (so a browser cannot reach them either, and they are not on
the free plan), and its IP allowlists are a Postgres feature, not a web-service
one. Env vars hold secrets but enforce nothing. The credential check has to be
code.

No new dependency: HTTP Basic Auth is `request.authorization` (Werkzeug parses
the header, already a runtime dep) plus `hmac.compare_digest` from the stdlib.
ADR-0006/R1's baseline is untouched.

## What is decided

1. **Exactly one door is open at a time, and an environment variable chooses
   which.** Not both, ever.
   - `ADMIN_ALLOWED_HOST` unset — *local mode*, today's behaviour exactly: the
     `Host` must name this machine, no credential is asked for, and anything
     else gets CARD-081's 404.
   - `ADMIN_ALLOWED_HOST` set — *deployed mode*: the `Host` must equal that one
     value, **and** every request must carry the credential. A request claiming
     `Host: localhost` is refused like any other stranger.

   The second half of that is the whole point. In a container behind a reverse
   proxy, "this request came from this machine" is not a fact the `Host` header
   can establish — the header is attacker-controlled and the proxy's own
   address is what `REMOTE_ADDR` shows (Render's logs prove it: every line
   reads `127.0.0.1`). Keeping the loopback door open in deployed mode would
   mean `Host: localhost` bypasses the password, which is not a defence.

2. **Misconfiguration fails closed, at startup.** `create_app` raises
   `AdminConfigurationError` when `ADMIN_ALLOWED_HOST` is set and either
   `ADMIN_PASSWORD` is missing/empty or `SECRET_KEY` is still the built-in dev
   default. A deploy that forgot the password must not boot serving an open
   panel; a build that fails loudly is recoverable, a silent open admin is not.

3. **`SECRET_KEY` is part of this card, not a separate one.** `app.py:238`
   falls back to `"dev-key-change-in-production"` and nothing in `render.yaml`,
   `Procfile` or `start.sh` overrides it, so the deployed app has been signing
   session cookies with a string published in this repository. That is
   session forgery for anyone who reads the source, and it becomes exploitable
   the moment the panel is reachable — which is what this card does.

4. **401 to a caller at the right host, 404 to everyone else.** A request to
   `ADMIN_ALLOWED_HOST` with no or wrong credentials gets `401` with
   `WWW-Authenticate: Basic`, because the browser needs that to prompt. A
   request to any other host keeps CARD-081's 404 disguise: telling a scanner
   "wrong host" would confirm something is there.

5. **Both halves of the credential are compared with `hmac.compare_digest`**,
   and both are compared *always* — no early return on a wrong username — so
   the response time does not separate "no such user" from "wrong password".

## Acceptance criteria

- **AC-1** (local mode is unchanged) — with `ADMIN_ALLOWED_HOST` unset, every
  case CARD-081 pinned still holds: local hosts served, everything else 404,
  no credential asked for.
  *test:* the existing `TestAdminPanel_RefusesRequestsThatDidNotAddressThisMachine`, unmodified
- **AC-2** (deployed mode needs the credential) — with `ADMIN_ALLOWED_HOST`
  set, a request to that host with correct Basic credentials is served; with
  absent, empty, malformed, or wrong credentials it is `401` carrying
  `WWW-Authenticate: Basic`.
  *test:* `TestAdminAuth_DeployedModeRequiresACredential`
- **AC-3** (no loopback bypass) — in deployed mode, `Host: localhost`,
  `127.0.0.1` and `[::1]` are refused with `404` **even carrying valid
  credentials**, because they are not the configured host.
  *test:* `TestAdminAuth_DeployedModeHasNoLoopbackBypass`
- **AC-4** (fails closed) — `create_app` raises `AdminConfigurationError` when
  `ADMIN_ALLOWED_HOST` is set and `ADMIN_PASSWORD` is missing or empty, or
  `SECRET_KEY` is the dev default. Local mode raises for neither.
  *test:* `TestAdminAuth_RefusesToBootMisconfigured`
- **AC-5** (the destructive route is behind it) — `POST /regrade`,
  `POST /puzzles/<id>/delete` and the bulk routes are unreachable without the
  credential in deployed mode; asserted on the routes themselves, not only on
  `/`, so a hook that somehow skipped them would be caught.
  *test:* `TestAdminAuth_EveryRouteIsBehindTheCredential`
- **AC-6** (no timing separation) — a wrong username and a wrong password take
  indistinguishable paths: both halves compared, with `compare_digest`, no
  early return.
  *test:* `TestAdminAuth_ComparesBothHalvesConstantTime` (structural + behavioural)
- **AC-7** (the deploy is documented) — `render.yaml` declares the new env vars
  with `sync: false` so Render prompts for them rather than storing secrets in
  the repo, and `ADMIN_SETUP.md` says what to set and that the panel is open to
  anyone holding the password.

## Guardrails

- **G-1** — **local mode's behaviour does not change by one byte.** CARD-081's
  test class must pass untouched. If a test in it needs editing, the design is
  wrong.
- **G-2** — no credential, hostname or key is committed. `render.yaml` gets
  `sync: false` declarations only; the values are typed into Render's dashboard.
- **G-3** — `_host_is_local` and `ALLOWED_HOSTS` keep their current meaning and
  stay cross-checked against `nonogram.web.handler` (ADR-0007, and the existing
  `test_the_allowlist_and_the_web_adapters_agree`). This card adds a second,
  separate question; it does not redefine the first.
- **G-4** — no new runtime dependency (ADR-0006/R1). `hmac`, `secrets` and
  Werkzeug's own header parsing only.
- **G-5** — the credential check runs **before** anything reads the database,
  like the host check it sits beside. A 401 must not cost a query.
- **G-6** — this card does not touch `start.sh`. Render runs the Flask
  development server, which is a real problem and a separate decision, because
  `gunicorn` would change ADR-0006/R1's baseline.

## Out of scope, deliberately

- **The development server.** `start.sh` runs `flask run`, which prints *"This
  is a development server. Do not use it in a production deployment."* on every
  boot. Fixing it means adding `gunicorn` to the runtime baseline — an
  ADR-0006/R1 decision, so it gets its own card rather than riding along here.
- **CSRF.** Basic auth means the browser attaches the credential to *every*
  request to the host, including one triggered by another page, so CSRF becomes
  reachable in a way it was not when the panel was loopback-only. Noted as a
  follow-up rather than fixed here; the practical exposure is low while the
  panel has one user who is not browsing hostile pages in the same session.
- **`autoDeploy: true`.** `render.yaml` deploys every merge to `main`
  automatically, which is how CARD-081's guard reached production without
  anyone choosing to send it. Worth revisiting; not this card.

## Worktree notes

**The diagnosis was measured, not inferred.** With `DATABASE_URL` pointed at a
black-holed address (`203.0.113.1`), a request carrying the Render `Host` came
back 404 in **6.9 ms** while the same request carrying `Host: localhost` took
**75 seconds** and raised `OperationalError`. That gap is the whole proof that
the 404s were the guard and not the database — no other evidence was needed,
and `pg_postmaster_start_time()` separately showed 6 days 20 hours of
uninterrupted Postgres uptime.

**`_host_is_local` was refactored, not rewritten.** Its parse moved into
`_hostname_of` so the new "is this the configured remote host?" question is
asked of *the same* parse. Two host checks that disagreed about what a host is
would be a bypass waiting to happen — the near-miss cases (`evil.com:80@HOST`,
`HOST.evil.com`) are refused by exactly the rules CARD-081 wrote, now shared.

**Mutation checks — five mutants, five killed.** Reading the tests is not
evidence that they discriminate; these are:

| # | mutation | killed by |
|---|---|---|
| M1 | `_credential_is_correct` always returns `True` | AC-2, AC-5, AC-6 (8 tests) |
| M2 | loopback branch kept alive in deployed mode | AC-3 (4 tests) |
| M3 | the missing-password boot check disabled | AC-4 (2 tests) |
| M4 | hostname equality relaxed to a substring test | AC-3's near-miss cases |
| M5 | the dev-`SECRET_KEY` boot check disabled | AC-4 (2 tests) |

M4 is the one worth keeping: `in` instead of `==` passes every ordinary test —
the right host is served, loopback is refused — and silently admits
`nonogram-admin.onrender.com.evil.com`. Only the near-miss parameters catch it.

**AC-5 walks the URL map rather than naming routes.** Asserting `/` alone would
pass equally against a per-route decorator applied to every route but one. The
sweep builds a concrete URL for each of the 40-odd rules and requires 401 from
all of them, with a floor assertion (`>= 30`) so a broken URL-map walk cannot
pass by finding nothing.

**Non-ASCII credentials are a real case, not a flourish.**
`hmac.compare_digest` raises `TypeError` on a `str` containing anything outside
ASCII. Comparing UTF-8 bytes is what stops "type a Cyrillic character into the
browser's login box" from being a 500 that anyone can trigger *without* a
credential.

**`SECRET_KEY` was folded in rather than split out.** It is a separate bug —
the deployed app has been signing session cookies with a literal published in
this repository — but it is only *exploitable* once the panel is reachable,
which is precisely what this card does. Shipping the reachability without the
key fix would have introduced the vulnerability this card is meant to avoid.
