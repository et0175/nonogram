# CARD-522: The deployed panel refuses to start without a database

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/522-refuse-memory-mode-deployed
**Worktree:** ../PythonProject4-card-522
**Source:** roadmap wave 12, cut 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". IDEA-226 (CARD-515 review 1 F-003).
**Idea:** IDEA-226
**Wave:** 91
**Created wave:** 91
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/admin/app.py
**UI surface:** — (start-up only)
**Review score:** —
**Started:** 2026-11-22T13:38Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

After CARD-515 a blank or whitespace-only DATABASE_URL counts as unset, and the admin panel then starts quietly in in-memory mode: it logs "DATABASE_URL not set", and everything saved is lost on restart. Locally that is the intended fallback. On the deployed panel it would silently lose work. Owner's ruling 2026-11-22: refuse to start on the deployed server (where REMOTE_HOST is set); keep the in-memory fallback locally.

## What to implement

Re-verify on main first: how `create_app` chooses in-memory mode, how the deployed server is recognised (REMOTE_HOST, `_configured_hostname`; read how both are set and used), and what happens today with REMOTE_HOST set and DATABASE_URL unset or blank. Then make `create_app` refuse to start in that case, with one clear message naming what is missing (never echoing any URL or secret). Locally (REMOTE_HOST unset) nothing changes.

## Acceptance criteria

* **AC-1**: REMOTE_HOST set and DATABASE_URL unset, empty or whitespace-only: the app refuses to start, with a message that names DATABASE_URL and says the deployed panel needs a database (control: today's code starts in memory).
* **AC-2**: REMOTE_HOST unset and DATABASE_URL unset: the in-memory fallback still starts, unchanged.
* **AC-3**: REMOTE_HOST set and a valid DATABASE_URL: starts as before (no connection is needed to show this; stop at the mode decision).
* **AC-4**: net test count at most +1, preferring extensions of existing create_app tests. Report it.

## Guardrails

* **G-1**: never connect to the production database, and do not deploy; Render runs its own dashboard-configured service and this change reaches it only on the owner's next deploy.
* **G-2**: the refusal message carries no URL, host or credential.

## Worktree notes
