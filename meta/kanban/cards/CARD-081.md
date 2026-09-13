# CARD-081: The admin panel binds loopback like the web UI does, and a test says so ⚑

**Status:** done
**Priority:** P2
**Category:** compliance
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/081-admin-binds-loopback
**Worktree:** ../PythonProject4-CARD-081
**Source:** CARD-077 review cycle 1, finding F-003 (2026-09-13)
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** ADMIN_SETUP.md (reachability note + the SSH-tunnel replacement), meta/architecture/requirements.yml (CON-015, CON-016; scope note on CON-009), meta/architecture/trace.yml (rows for the two new constraints), src/nonogram/admin/app.py (LOOPBACK_HOST + main(port) + the Host guard), tests/test_admin_binding.py (new — AC-A/B/C)
**Review score:** — (merged without a review cycle, at the owner's call)
**Started:** 2026-09-13T14:00Z
**Closed:** 2026-09-13T15:10Z
**Actual:** 0.25d
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

### What was there, and what is there now (2026-09-13)

**The starting state was narrower than the card implies, and also worse.**
`ADMIN_SETUP.md` documents `flask --app src.nonogram.admin.app run`, which is
Flask's own CLI and defaults to `127.0.0.1` — so the documented, actually-used
launch path was already loopback. The `0.0.0.0` lived in a second, undocumented
entry point (`python -m nonogram.admin.app`), together with `debug=True`, which
is a Werkzeug console on every interface. Worth stating plainly: the panel was
probably never exposed in practice, and the exposure was one command away with
nothing to stop it.

**Two defences, deliberately independent** (item 4's "do not add auth" still
holds — neither of these authenticates anybody):

1. `LOOPBACK_HOST = "127.0.0.1"`, and `main(port)` takes no host. Mirrors
   `web.create_server`'s shape, so the same signature-sweep test applies.
2. A `Host`-header refusal on every request. This is the one that matters,
   because `flask run --host=0.0.0.0` is the documented path plus one flag and
   this package cannot remove that flag. The bind is the wall; the header check
   is what stands when someone opens a door in it.

**The header check is `web.handler._host_is_local` reimplemented, not
imported** — ADR-0007 forbids the lateral import and CLAUDE.md's rule is to
reimplement natively (the `mask_runs` precedent). The first version omitted the
`@ / # ?` rejection the web adapter does before parsing, and
`evil.com:80@127.0.0.1` went through: `urlsplit` reads the host component of
that as `127.0.0.1`. Its own test caught it. The two copies are now held to
identical answers on eleven authorities by a differential test in the test tree,
where the import is legal.

**Model (item 3): a sibling pair, not a widened CON-009.** A constraint carries
one `check:`, and two inbound surfaces sharing one test between them is exactly
how the admin came to be governed by nothing. CON-015 is the bind (mirrors
CON-009), CON-016 the Host refusal (mirrors CON-010), both scoped by code glob
to `src/nonogram/admin/**`. CON-009 keeps its statement and gains a note saying
it is COMP-008's rule and pointing at the new pair — so the next card cannot
repeat CARD-077's mapping error.

Component mapping gap unchanged: no COMP owns `src/nonogram/admin/**`, so both
rows name COMP-008 like the FR-029 row does. The code-glob scope is what makes
the lens collect them correctly regardless.

**Verification.** 24 tests. Six mutants, all killed: wildcard bind restored,
debugger restored, `@/#?` check dropped, port-shape check dropped,
`before_request` guard removed, and `LOOPBACK_HOST` typo'd to `127.0.0.2`
(the case a probe on a host where all of 127/8 is local would not catch).
Validator 0 errors; `system_rules.py --verify-refs` lists neither new rule in
`dead_check_ref`. Full suite: 14 failures, the same pre-existing set as main.

**One thing the literal sweep had to do differently from the web's.**
`test_web_server.py` greps raw source for `0.0.0.0`, which works there only
because those modules never discuss the address they avoid. This module's
docstring has to say which address it replaced, so the sweep tokenises and
strips strings and comments first — a constraint on behaviour rather than on
prose.
