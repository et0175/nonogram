# CARD-279: A loopback-binding control asks whether a port is free on a LAN address, and the answer depends on the network

**Status:** ready
**Priority:** P2
**Category:** ops
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/279-loopback-probe-depends-on-the-lan
**Worktree:** —
**Source:** Observed 2026-10-23 by CARD-264's fix round 2, which hit it once mid-round and reported it rather than shrugging. Board precedent is one card old: CARD-277 was cut for a flake seen exactly once, on the rule that "recorded, not diagnosed" dies with the worktree.
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_web_server.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What was observed, and the honest width of it

**Once.** `tests/test_web_server.py:555` —
`TestWebServer_BindsLoopbackOnlyByDefault::test_the_port_stays_free_on_every_other_interface` — failed
during CARD-264's fix round: `_port_is_free_on('192.168.0.109', 59110)` returned `False` where the test
requires `True`. It then **passed on three isolated re-runs** and in the combined CON-009 + CON-010 run,
and the post-fix full-suite gate at `e26e5473` was green.

**It is inside no hunk CARD-264 touched.** That card changed `CLAUDE.md`, one docs page and four test
files, and its `tests/test_web_server.py` edits are the domain-validator guard region — not this class.
Pre-existing.

## Why this is a control defect and not just a flake

This test is part of **CON-009**, the constraint that the web server binds loopback only by default. Its
method is to assert the port is *not* bound on any other interface — and it does that by probing a
**real LAN address**, `192.168.0.109`, discovered from the host. That makes the assertion's truth
value depend on three things the test does not own:

1. whether the host currently *has* that address (a sleeping Wi-Fi link, a VPN, a dock, a different
   network, or a DHCP lease change all move it);
2. whether **something else on the machine** happens to hold that ephemeral port — 59110 is in the
   ephemeral range, so any other process, including another worktree's test server, can own it;
3. whether the probe's failure mode distinguishes *"the port is taken by the thing we are testing"* from
   *"the bind failed for an unrelated reason"*. A `False` from `_port_is_free_on` conflates them, and the
   conflation is the defect: the test reads an unrelated bind failure as **evidence the server bound a
   LAN interface**, which is a security claim.

So the control is sound in intent and under-specified in method: it can red for a reason that has nothing
to do with the server's binding, and — more quietly — it could **pass** on a host where that address does
not exist at all, certifying the constraint by probing nothing. That second half is the one worth
measuring, because it is the vacuous direction and nobody has looked at it.

## What to implement

1. **Reproduce or bound it.** Run the one test in a loop and report the hit rate with the host condition
   stated. A measured "N runs, 0 reproductions" is a publishable result here; what is not acceptable is a
   fix written against a guess.
2. **Decide what the probe is really asserting, and make the method match.** The constraint is *the
   server is not reachable on a non-loopback interface*. Candidate shapes, to be chosen with a reason
   rather than by preference:
   - probe the address the server was asked **not** to bind, and distinguish `ECONNREFUSED` (nothing is
     listening — the constraint holds) from `EADDRINUSE`/anything else (unrelated, so **skip loudly** or
     fail with a message naming the cause, never silently pass);
   - or assert on the socket the server actually opened (`getsockname`), which is a fact about the server
     rather than about the network, and needs no second address at all.
3. **Close the vacuous direction explicitly.** If the host has no non-loopback address, the test must say
   so and **fail or skip loudly with a named reason** (ADR-0038/R8) — it must not pass by probing an
   address that does not exist. Hold that with a case: a fabricated "no other interface" condition must
   not produce a green.
4. **Do not weaken the constraint to stop the noise.** CON-009 is a security boundary. Removing the
   other-interface assertion, or relaxing it to a range or a warning, is the one outcome worse than
   leaving the flake open.

## Acceptance criteria

- **AC-1** *Given* a declared reproduction budget, *then* the card reports **either** a reproduction with
  the host condition and the probe's errno, **or** a measured non-reproduction with the run count and the
  conditions — with the figure's domain stated either way. (evidence: the card's own measurement)
- **AC-2** *Given* the repaired control, *then* a bind failure **unrelated** to the server (the port held
  by another process) is distinguished from the server having bound a non-loopback interface: the first
  does not red the constraint, the second does. Both states demonstrated. (test: named by the
  implementation; state it)
- **AC-3** *Given* a host with **no** non-loopback address, *then* the test does not pass vacuously — it
  fails or skips with a named reason visible in the run summary (ADR-0038/R8). Demonstrated by
  fabricating that condition, not asserted in a docstring.
  (test: named by the implementation; state it)
- **AC-4** *Given* the change, *then* CON-009's other five tests and CON-010's three pass **unedited**,
  and the loopback-only guarantee is still asserted. (gate: `tests/test_web_server.py`)

## Guardrails

- G-1: **CON-009 and CON-010 must not be weakened.** This card repairs a probe's method; it does not
  relax what the constraint claims.
- G-2: **No `src/` change.** If the server's binding is genuinely wrong, that is a different and much
  larger card — say so and stop rather than editing the adapter.
- G-3: **Select CON-010 by its test functions, never by its requirement id.** Measured on this board
  2026-10-23: `-k 'PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest'` collects
  **zero** — the id is prose (the property is written as module-level functions, `tests/test_web_server.py:1959`),
  so a selection by id reports a security boundary as green while running nothing. The three functions are
  `test_the_corpora_are_large_and_cover_every_declared_signal`,
  `test_every_cross_origin_or_foreign_authority_request_is_refused`,
  `test_every_same_origin_or_metadata_free_request_is_served`. With CON-009 that is **8** collected.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-6: Take no timing measurements and report no durations — other work may share this machine. A
  **retry count** is not a duration and is the figure this card wants.

## System contract

- CON-009 — the web server binds loopback only by default (check: `TestWebServer_BindsLoopbackOnlyByDefault`)
- CON-010 — any cross-origin or foreign-authority request is refused (check: the three module-level
  functions named in G-3, **not** the requirement id)
- ADR-0038/R8 — a test fails or skips **loudly**, with a named reason in the run summary; never silently
  (check: review-lens)
- ADR-0039/R1 — a claim needs a control that can fail: caught WITH the mechanism, missed WITHOUT it
  (check: `test_the_control_for_each_spelling_depends_on_the_set`)

## Architecture context

- **ADR:** ADR-0019/R1 (the web adapter's boundary) is what CON-009/CON-010 protect; ADR-0038/R8 and
  ADR-0039/R1 are the rules the current probe strains.
- **Components:** none changed. This card edits one test file.
- **Trace:** `meta/architecture/trace.yml` — unchanged; CON-009's verifying test keeps its name.

## Worktree notes

- **[The observation, so it is not re-derived]** `_port_is_free_on('192.168.0.109', 59110)` → `False`
  once; three isolated re-runs green; the combined CON-009 + CON-010 run green; the full suite green at
  `e26e5473` (8919-class run, 0 failed). The address is this host's LAN address at the time, not a
  constant in the test.
- **[The vacuous direction is the unmeasured one]** Everyone's attention goes to the red. Ask the other
  question first: on a host with no non-loopback address, does this test *pass*? If it does, every green
  run on such a host certified CON-009 by probing nothing — and that is the same shape as the CON-010
  selector defect found on the same day (G-3), which is why both are on this card's contract.
- **[Do not run the full suite]** Export `NONOGRAM_FULL_SUITE_LOCK` to a scratch path for every pytest so
  the board's own lock is never read, written or created. The merge gate runs the full suite.
- **[Use the committed instrument]** `tests/kill_matrix.py`, `tests/README.md` from line 453. Both passes,
  ANY-RED, and report the **domain** of every figure — the denominator is the target file's `ast.Assert`
  node count, never the collected-test count.
