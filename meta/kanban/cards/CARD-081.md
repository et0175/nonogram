# CARD-081: The admin panel binds loopback like the web UI does, and a test says so ⚑

**Status:** ready
**Priority:** P2
**Category:** compliance
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/081-admin-binds-loopback
**Worktree:** —
**Source:** CARD-077 review cycle 1, finding F-003 (2026-09-13)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py (the `__main__` entrypoint), tests/test_admin_binding.py (new), meta/architecture/decisions/adr/... (CON-009's scope, if it is widened)
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why

CARD-077's system contract carried "NFR-003 / CON-009 — admin action bound to
localhost like the rest of the admin (check: existing admin binding tests)".
The review found both halves false.

- **No admin binding test exists.** CON-009's declared check,
  `TestWebServer_BindsLoopbackOnlyByDefault` (`tests/test_web_server.py:348`),
  covers COMP-008's web server. CON-009's own statement begins "The web UI's
  HTTP server", so the admin panel is not its subject — the card mapped a rule
  onto a component the rule does not reach.
- **The admin is not loopback-bound.** Its only entrypoint is
  `src/nonogram/admin/app.py:1598`:
  `app.run(host="0.0.0.0", port=5000, debug=True)` — every interface, with the
  Werkzeug debugger enabled. A reachable debug console is remote code
  execution, not just an information leak.

This mattered enough to card because CARD-077 added the admin's most
destructive route to that surface: `POST /regrade` rewrites the grade of every
stored puzzle, has no authentication and no CSRF token, and its own docstring
assumes it is "reached only from the preview page's button". Nothing enforces
that. The same is true of the delete and approve routes that were already
there — this card is about the surface, not about CARD-077's route.

⚑ The risk is not hypothetical the moment the admin runs on a laptop on a
café network, which is how a single-owner tool gets used.

## What to implement

1. **Default the entrypoint to loopback:** `app.run(host="127.0.0.1", ...)`,
   and drop `debug=True` from it. If a non-loopback bind is ever wanted, it
   must be an explicit opt-in the operator types, never the default — mirror
   whatever shape COMP-008's web server uses so the two agree.
2. **`tests/test_admin_binding.py`** — the test CON-009 names for the admin
   half. Follow `tests/test_web_server.py:348`'s existing structure rather than
   inventing a second idiom; that file already handles the "this host does not
   refuse a specific bind over a wildcard one" skip case.
3. **Decide CON-009's scope in the model, and write it down.** Either widen the
   constraint's statement to cover both inbound HTTP surfaces (admin included)
   and give it both checks, or add a sibling constraint for the admin. Today the
   admin is governed by nothing, which is why a card could assert the property
   and be believed.
4. **Do not** add authentication or CSRF in this card. They are worth having and
   they are a different decision with an ADR attached; conflating them with a
   one-line bind change would make this card unmergeable on its own.

## Acceptance criteria

- **AC-A** — the admin's default bind is `127.0.0.1`; a connection arriving on
  another interface is refused.
  *test:* `TestAdminPanel_BindsLoopbackOnlyByDefault`
- **AC-B** — `debug=True` is not the default for the admin entrypoint; the
  Werkzeug debug console is not reachable on a default run.
  *test:* `TestAdminPanel_DoesNotEnableTheDebuggerByDefault`
- **AC-C** — CON-009 (or its new admin sibling) names a check that exists and
  passes: `system_rules.py --verify-refs` reports it in neither
  `dead_check_ref` nor `no_check`.

## Guardrails

- G-1: No behaviour change to any route — this card moves a bind address and a
  debug flag, nothing else.
- G-2: No authentication, no CSRF, no rate limiting (see item 4).
- G-3: Commit only this card's files with explicit pathspecs; the working tree
  carries a large standing set of unrelated changes.

## System contract

- NFR-003 — the admin's HTTP surface is reachable only from the machine it runs
  on (check: TestAdminPanel_BindsLoopbackOnlyByDefault)
- CON-009 / BCON-0001 — socket reach is loopback-only (check: this card decides
  whether CON-009 covers the admin, and makes its `check:` true either way)
- ADR-0006/R1 — no new runtime dependency (check: review-lens)

## Architecture context

- **NFR:** NFR-003
- **CON:** CON-009 (scope question), CON-010 (the browser-mediated half — note
  whether it applies to the admin too, do not silently assume it does not)
- **Components:** admin panel (known mapping gap: no COMP owns it — trace.yml
  FR-029 row)

## Worktree notes

—
