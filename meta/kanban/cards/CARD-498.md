# CARD-498: The registry's honest-dead check refs: each one points at a real test or says honestly that none checks it

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/498-honest-dead-refs
**Worktree:** —
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-216, WSJF 3.08 (partly; the rescore counted 11 as a floor).
**Idea:** IDEA-216
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, tests/test_check_ref_resolution.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_check_ref_resolution.py` pins a class it calls **honest-dead**: registry check refs (requirements.yml `test:`/`check:`/`tests:`) that both of its resolvers agree name a test existing nowhere. On main 2026-11-20 the pin is `HONEST_DEAD = (11, …)`. Each such ref reads as "mechanically checked" while nothing checks it (memory: ADR check refs must be honest).

## What to implement

For each of the 11 (list them by the module's own helpers, never by text search):

1. If a real test verifies the AC's claim (find it by `ast`, read it, and confirm it can fail when the claim is broken), re-point the ref to it.
2. If none does, either write the narrowest test (only where cheap and the AC is mandatory) or mark the ref honestly in the registry's existing convention for an unchecked criterion (find how the registry already says "not mechanically checked", e.g. a review-lens marker), never by deleting the AC.
3. Re-derive the module's frozen classes as sets (HONEST_DEAD, and every class an edit moves), explain each delta, and keep the module's pin rules.

## Acceptance criteria

* **AC-1**: HONEST_DEAD is 0, or every remaining member is listed in the notes with why it stays and how the registry now says so.
* **AC-2**: every re-pointed ref's test is shown able to fail on the AC's claim (one mutant or a reading of its assertion, recorded per ref).
* **AC-3**: the forge_1 validator reports no new finding (compare `--phase all --format json` before and after); tests/test_check_ref_resolution.py green with re-derived pins.
* **AC-4**: net test count at most +2.

## Guardrails

* **G-1**: no AC is deleted or weakened to make a ref resolve.
* **G-2**: a synced review YAML must not be what makes a ref resolve (memory: review YAMLs revive dead check refs); confirm by `ast` def lines.

## Worktree notes
