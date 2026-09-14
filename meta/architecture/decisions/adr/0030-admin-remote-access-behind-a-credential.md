# ADR-0030: The admin panel may be reached from one configured host behind a credential

**Status:** Accepted (revises CON-015/CON-016, NFR-003's admin half)
**Date:** 2026-09-14
**Deciders:** Puzzle Creator (project owner)
**Revised:** —
**Migration:** expand
**Pattern:** —
**API-Posture:** internal

## Context

BCON-0001 puts one user on one machine, and NFR-003 turned that into a
threshold with an explicit second clause: *"binds 127.0.0.1 (loopback) only;
**no authentication enforced**"*. Its rationale rejected credentials by name —
a single-user tool "has no clean way to manage" them. CON-015 (the bind) and
CON-016 (the `Host` refusal) restate that for the admin panel, and CARD-081
implemented both.

The owner has since deployed the admin panel to Render, at
`https://nonogram-admin.onrender.com`, and wants to use it from there. Under
CON-016 every request to that hostname is refused, so the deployed panel
returns 404 on every route — correctly, and uselessly.

Two facts make this a decision rather than a bug fix:

1. **The panel has no authentication and a destructive route.** `POST /regrade`
   rewrites `difficulty_score`, `difficulty_tier` and `strategies_used` on
   every gradeable row, and since CARD-084 dropped the legacy columns it keeps
   no copy of what it replaced. "Reachable" and "authorised" were the same
   question precisely because nothing else answered it.
2. **NFR-003's rationale is now out of date, not wrong.** "No clean way to
   manage credentials" was true of a tool with no deployment. A deployment has
   a secret store — Render's environment — and one operator needs one password,
   which is the smallest credential-management problem there is.

The alternative readings of "make it reachable" were considered and rejected:

- **Widen `ALLOWED_HOSTS`.** Publishes an unauthenticated destructive admin.
- **Render Private Service.** No public URL at all, so a browser cannot reach
  it either; also not available on the free plan.
- **IP allowlist.** Render offers these for Postgres, not for web services.
- **Keep it loopback-only and tunnel.** Viable, and it remains the right answer
  for anyone who does not want a public URL — but it is a workflow the owner
  declined.

## Decision

The admin panel has **exactly one door open at a time**, chosen by the
environment variable `ADMIN_ALLOWED_HOST`.

**Local mode** (`ADMIN_ALLOWED_HOST` unset) is unchanged and remains the
default: the bind is loopback (CON-015), the `Host` must name this machine
(CON-016), and no credential is asked for.

**Deployed mode** (`ADMIN_ALLOWED_HOST` set to one hostname) replaces the
`Host` rule rather than adding to it. A request is served only when all three
hold:

1. its `Host` names exactly the configured hostname;
2. it carries the configured HTTP Basic credential;
3. the browser does not say another site started it.

A request claiming `Host: localhost` is refused in deployed mode like any other
stranger.

## Rules

- **R1** — The two modes are mutually exclusive. In deployed mode no request is
  served on the strength of naming a loopback host, and in local mode no
  credential is required or advertised. There is no configuration in which both
  doors are open.
- **R2** — In deployed mode every request is refused unless its `Host` equals
  the configured hostname, it carries the configured credential, and it is not
  marked cross-site by `Sec-Fetch-Site` or `Origin`. The cross-site rule is the
  admin's copy of CON-010 and exists for the same reason: a browser replays a
  cached Basic credential on a cross-site form POST, so the credential alone
  does not establish that the operator asked.
- **R3** — The process refuses to start in deployed mode without a credential
  of at least 16 characters and a `SECRET_KEY` other than the built-in
  development value. A misconfiguration fails the boot, never opens the panel.

## Consequences

**Positive.** The panel is usable from anywhere the owner is, without
publishing it. The `SECRET_KEY` fallback — a literal in this repository, and
therefore forgeable — becomes a fatal misconfiguration instead of a latent one.
The cross-site rule closes a hole that was unreachable only by accident of the
bind.

**Negative.** BCON-0001's "one user on one machine" no longer describes the
deployment, and NFR-003's second clause is retired for the admin surface: a
password is now the boundary where a network interface used to be. Nothing in
this package rate-limits guesses against that password, which is why R3 sets a
length floor rather than trusting the operator's choice; a lockout or throttle
is a separate decision and is not made here.

**Not decided here.** Whether the *web UI* (COMP-008, CON-009/CON-010) may be
deployed the same way. It may not, and this ADR does not license it: NFR-003's
web half and its rationale stand untouched.
