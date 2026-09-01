# CARD-022: Repair the web adapter's false claims and vacuous guards

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/022-web-adapter-truth-repair
**Worktree:** ../PythonProject4-card-022
**Source:** meta/review/20260830T163436Z-CARD-019-posthoc.yml
**Idea:** —
**Wave:** 13
**Depends on:** —
**Touches:** src/nonogram/web/__init__.py, src/nonogram/web/handler.py, tests/test_web_server.py, tests/test_cli.py, meta/kanban/cards/CARD-019.md
**Review score:** 8.5 (cycle 2/3)
**Started:** 2026-08-30T18:15:00Z
**Closed:** 2026-08-31T07:30:00Z
**Actual:** —
**Merge commit:** 137e367
**Blocked by:** —

## What to implement

An independent post-hoc review of merged CARD-019 (`meta/review/20260830T163436Z-CARD-019-posthoc.yml`,
score 6.0) found that the code is behaviourally sound but **says things about itself that are not
true**, and that four of the guards cited as evidence for those claims can pass without executing.
This card repairs truth and evidence. It ships **no new protection** — the missing access control is
NFR-004 and belongs to CARD-020.

Why it goes first: two of the vacuous guards are cited in every prior review's verdict as the
enforcement of ADR-0019/R1 and guardrail G-4. Until they actually run, every future web card is
resting on evidence that does not exist.

1. **Four guard loops pass vacuously (post-hoc F-003).** The cycle-2 fix added
   `assert _WEB_SOURCES, "..."` to exactly one of five identical loops. Add the same non-empty
   assertion to the other four:
   - `tests/test_web_server.py:349` — AC-052's source half
   - `tests/test_web_server.py:1283` — ADR-0019/R1's guard (`imports no domain validator`)
   - `tests/test_web_server.py:1298` — G-4's guard (`raises nothing`)
   - `tests/test_cli.py:774` — `test_the_web_adapter_never_imports_the_cli_adapter`, which loops
     `_MODULES.items()` filtered to `web`; if the filter matches nothing the body never runs. This is
     one of the two tests every cycle named as the `web -> cli` enforcement.
   Each fix must be mutation-verified: empty the iterated collection and confirm the test now FAILS.

2. **`src/nonogram/web/__init__.py` states two falsehoods (post-hoc F-005).** Three lines below the
   sentence a human already had to correct in `e177473`:
   - *"this package imports the orchestrator"* — nothing under `web/` imports it. Say what is true:
     it imports inward only, and today that is the difficulty and export registries.
   - *"routing, rendering, request parsing, and mapping form fields onto
     `orchestrator.GenerationRequest`"* — request parsing and request mapping are CARD-020's, and
     guardrail G-5 explicitly excludes them from CARD-019. Describe what this package does today and
     name the rest as forthcoming.

3. **`handler.py`'s "nosniff is sent on every response" is false (post-hoc F-006).** Statuses 400,
   414, 431, 501 and 505 are written by the stdlib's `send_error`: `text/html`, no `nosniff`, and the
   501 reflects the request method back. Prefer overriding `send_error` so the claim becomes true;
   if that proves awkward, narrow the docstring to "every response this handler writes" — but do not
   leave the broad claim standing. Whichever you choose, add a test pinning the actual behaviour of
   those five statuses.

4. **The `@`/`/` narrowing's stated rationale is false (post-hoc F-004).** The comment argues the two
   character sets stay the same size; they do not — `#` and `?` split under `urlsplit` exactly as `@`
   and `/` do. Correct the rationale. **Do not widen the check here** — bounding the shape space is
   EC-004's property and lands with CARD-020.

5. **The auth-vocabulary scan is case-sensitive (post-hoc O-2).** `send_header("www-authenticate", …)`
   evades it. Make the header comparison case-insensitive; HTTP header names are.

6. **Correct four failure-matrix rows in `meta/kanban/cards/CARD-019.md`** so the record states what is
   true today. CARD-019 is `done`; this card owns the correction and must add a
   `## Follow-up required (2026-08-30)` section to that card pointing here.
   - **Row F-12** claims the Host check handles a cross-origin form POST. It does not — a browser sets
     `Host` from the *target*, so a form on a malicious page reaches `127.0.0.1` with an allowlisted
     `Host` (verified on the wire: 200). State that the check closes DNS rebinding only, and that
     browser-mediated cross-origin reach is NFR-004, unimplemented, owned by CARD-020.
   - **Row F-12 / F-8** also claim "0 routes reached on a refused host". An absolute-form target
     (`GET http://evil.example.com/ HTTP/1.0`, no Host) is served 200. State it.
   - **Row F-9** claims "0 ways to bind another address". `LoopbackHTTPServer` is exported and takes
     `server_address`; the test suite itself uses it to bind `0.0.0.0`. State the real bound.
   - **Row F-6**'s "shutdown <= 0.5s" has no covering test. Either add one or drop the numeric bound —
     an unmeasured number is worse than no number.

## Acceptance criteria

- **AC-059** (negative) — given the collection each of the four guard loops iterates, when that
  collection is emptied, then the test fails rather than passing over zero items.
  *test:* `TestWebGuards_EveryStructuralLoopAssertsNonEmpty`
- **AC-060** (happy) — given `src/nonogram/web/__init__.py`'s module docstring, when its factual
  claims about imports and responsibilities are checked against the package, then every claim is
  true of the code as shipped.
  *test:* `TestWebDocstrings_MatchTheShippedPackage`
- **AC-061** (boundary) — given a request producing each of the five stdlib error statuses (400, 414,
  431, 501, 505), when the response is inspected, then its `nosniff` behaviour matches what the
  handler's docstring claims.
  *test:* `TestWebHandler_ErrorResponsesMatchTheDeclaredNosniffBound`
- **AC-062** (negative) — given a response carrying a lowercase `www-authenticate` header, when the
  auth-vocabulary scan runs, then the header is detected.
  *test:* `TestAuthScan_IsCaseInsensitiveOnHeaderNames`

## Guardrails

- G-1: **Ship no new access control.** The origin/`Sec-Fetch-Site` check, the absolute-form rejection,
  and any widening of the accepted host-shape set are NFR-004's and belong to CARD-020. This card
  corrects claims and evidence only — if a fix here starts adding protection, stop.
- G-2: Do not edit `src/nonogram/orchestrator.py` or any capability module
  (`sourcing/`, `clues.py`, `solver/`, `difficulty.py`, `export/`).
- G-3: Do not weaken the import guard. `_ADAPTERS` stays a literal two-name frozenset and
  `_LAUNCH_EDGE` a single ordered pair; `web -> cli` stays forbidden. You are making its loops
  execute, not changing what they permit.
- G-4: Do not weaken or delete any existing test to make a claim true. If a claim cannot be made true
  cheaply, correct the claim instead — that is this card's whole point.
- G-5: No new runtime dependency; no domain logic or validation in `web/`.
- G-6: Do not touch the 13 unprocessed analyzer entries in
  `meta/architecture/inputs/raw-requirements.md`, or any `meta/architecture/` file — the model was
  corrected separately (NFR-004, CON-009, CON-010) and is not this card's business.

## System contract

- ADR-0019/R1 — The web UI adapter (src/nonogram/web/) contains HTTP concerns only — routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest — and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no capability module may import it or cli.py (check: test_every_import_in_the_package_points_inward)
- ADR-0021/R1 — The web UI's POST handler calls the orchestrator synchronously on the request thread and must not introduce a job store, polling endpoint, worker-thread handoff, or streamed/chunked response for generation requests (check: review-lens)
- CON-005 — The uniqueness check must never produce a false positive (check: PropertyTest_Solver_NeverFalsePositiveUniqueness)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 only (check: TestWebServer_BindsLoopbackOnlyByDefault)
- CON-010 — The web UI's HTTP server refuses any request the browser marks as cross-site (check: PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest) — NOT satisfied yet; CARD-020 owns it
- INV-001 / INV-002 / INV-003 — untouched by this card's scope

## Architecture context

- **FR:** — (defect repair against merged FR-017 work; no new requirement)
- **NFR:** NFR-003 (its evidence base), NFR-004 (documented as unimplemented, not implemented here)
- **ADR:** ADR-0019, ADR-0020, ADR-0007
- **Components:** COMP-008
- **Trace:** meta/architecture/trace.yml

## Worktree notes

—
- **[Env]** forge 2026.8.17 (meets min_version).
- **[Drift gate]** clear — `meta/drift-pending.yml`'s 11 modeled files do not intersect this
  card's Touches (the drift is in `cli.py`/`orchestrator.py`/`sourcing`/`export`/`solver`;
  this card touches `web/`, the two test files, and CARD-019's card).
- **[System contract]** verified against the lens rather than hand-trusted: the section matches
  the lens output exactly (ADR-0019/R1, ADR-0021/R1, CON-005, CON-009, CON-010, INV-001/002/003),
  including CON-009/CON-010 created by today's architecture correction.
- **[Sync discipline]** `meta/` was seeded into the worktree ONCE, at creation, before any agent
  existed. Every later sync is outward only. This is the protocol whose violation destroyed the
  CARD-019 fix agent's bookkeeping.

### Implementation (2026-08-30) — commit `81504e5`

Env: a fresh `.venv` in the worktree (`python3.14 -m venv .venv`, `pip install -e '.[dev]'`);
`nonogram.__file__` verified to resolve inside the worktree, not the main repo.
**Suite: 1261 passed / 1 xfailed before → 1290 passed / 1 xfailed after** (+29 tests, no
regressions, no existing test edited to accommodate a change). The `bench_generate.py`
xfail is untouched.

Every mutation below was applied to a byte-exact copy, run, and restored by `cp` from a
backup taken before the first mutation; `git status --porcelain src/ tests/` was clean of
unintended changes afterwards.

**1 — the four vacuous guard loops (AC-059).**
- `tests/test_web_server.py` — `assert _WEB_SOURCES, "no web adapter sources found"` added
  to `test_no_module_in_the_package_names_another_bind_address`,
  `test_the_web_package_imports_no_domain_validator` and `test_the_web_package_raises_nothing`
  (the fourth sibling, `test_the_package_contains_no_authentication_vocabulary`, already had it).
- `tests/test_cli.py` — `test_the_web_adapter_never_imports_the_cli_adapter` consumes a
  *filter* over `_MODULES`, not a glob, so the non-empty assertion is about the filtered set:
  it now builds `web_modules` and asserts it contains the four web modules **by name**
  (`nonogram.web`, `.handler`, `.pages`, `.server`) rather than by count — a module vanishing
  from the sweep fails, a module being added does not.
- New `TestWebGuards_EveryStructuralLoopAssertsNonEmpty` makes the mutation permanent:
  each guard is invoked with its own collection emptied and must raise, plus a control that
  the `web -> cli` guard still passes unmonkeypatched.
- **Mutation M1** — glob `*.py` → `*.NOPE` (`_WEB_SOURCES == []`): *before* this card that
  produced "1 failed, 3 passed"; now **4 failed**, each on `no web adapter sources found`.
- **Mutation M2** — selector `_component(module) == "web"` → `"webXX"` (filtered set empty):
  *before*, "1 passed"; now **1 failed** in `test_cli.py`, and the new AC-059 control fails too.
- **Mutation M2b (G-3 control)** — `from nonogram import cli` injected into `web/server.py`:
  still fails **both** `test_every_import_in_the_package_points_inward` and
  `test_the_web_adapter_never_imports_the_cli_adapter`. `_ADAPTERS` and `_LAUNCH_EDGE` are
  untouched; the guard was made to execute, not to permit more.

**2 — `src/nonogram/web/__init__.py`'s two falsehoods (AC-060).**
Re-derived first: `grep -rn orchestrator src/nonogram/web/` returns only docstring hits, and
the package's complete outward import set is `{difficulty, export}`. Line 11's "this package
imports the orchestrator" is now "imports inward only — today the difficulty and export
registries", with the permission (it *may* import the orchestrator) kept distinct from the
fact (it does not). The "request parsing, and mapping form fields onto
`GenerationRequest`" paragraph is scoped to what ships (routing and rendering) and the
`size=5000` / AC-050 reasoning is explicitly attributed to CARD-020, the card that will make
it true.
- New `TestWebDocstrings_MatchTheShippedPackage`: the import set is asserted exactly; any
  `imports the <component>` sentence obliges the import to exist (one-directional, so
  CARD-020 is not forced into a phrasing); every sentence naming `GenerationRequest` must
  also name CARD-020; and the behavioural half — no `do_POST`, `ROUTES` GET-only, no
  `GenerationRequest` in non-docstring source — so it is not prose checked against prose.
- **Mutation M4** — `git show HEAD:src/nonogram/web/__init__.py` restored over the fix:
  **2 failed** (`..._claims_no_import_the_package_does_not_make`,
  `..._claims_no_responsibility_the_package_lacks`).
- **Mutation M7** — a real, *permitted* `from nonogram import orchestrator` added to
  `web/pages.py`: `test_the_package_imports_exactly_what_the_docstring_names` **fails**, so
  the claim is pinned in both directions.

**3 — "nosniff on every response" (AC-061).** Re-probed rather than trusted, and the wire
was **worse than the post-hoc report says**. Against stock `BaseHTTPRequestHandler`:
414/431/501 come back `text/html` with no `nosniff`, and **400 and 505 come back with no
status line and no headers at all** — `parse_request` assigns the parsed version only after
accepting it, so `request_version` is still the `HTTP/0.9` default and both
`send_response_only` and `end_headers` no-op. So those two had no `Content-Type` either, and
the stdlib's 501 reflects the request method into the **reason phrase**
(`501 Unsupported method ('POST')`), not only the body.
`WebUIRequestHandler.send_error` now funnels all five through `_respond`: `text/plain`,
`nosniff`, `Content-Length`, a real `HTTP/1.0 <code> <phrase>` status line, and a body of the
status alone — nothing off the wire is echoed. `message`/`explain` are still logged, so an
operator loses nothing. `HEAD` (which has no `do_HEAD` and so arrives as a 501) still gets
`Content-Length: 0` and no body, per RFC 9110 §9.3.2 — the one thing a naive override loses.
- New `TestWebHandler_ErrorResponsesMatchTheDeclaredNosniffBound`: all five statuses probed
  raw, each pinned to its exact status line (spelled out in the test, **not** read back from
  `BaseHTTPRequestHandler.responses`, which is the table the handler formats from); three
  non-echo probes (method, markup-as-method, version); the HEAD case; and a control that the
  four `_respond` statuses (200 / 404 / both `Host` 400s) still carry it.
- **Mutation M3** — the `send_error` override deleted: **9 of the 10 new tests fail**. The
  tenth is the `_respond` control, which is correctly unaffected.
- Note: `_respond`'s docstring keeps the broad claim because the claim is now true; the card
  allowed narrowing it instead, but the override is what it says it prefers.
- The three pre-existing `test_the_stdlib_rejects_a_bad_request_line_before_the_router`
  params for 400/505 were **not** edited (G-4). They asserted `b" 400 "` and matched it inside
  the stdlib's HTML explanation line; they now match the real status line. That they kept
  passing without an edit is itself evidence the status behaviour did not move.

**4 — the `@`/`/` rationale (docstring only; no AC, no behaviour change).**
Re-derived by direct call, not read: `urlsplit("//127.0.0.1#evil").hostname == "127.0.0.1"`,
`urlsplit("//localhost?evil").hostname == "localhost"`,
`urlsplit("//127.0.0.1:notaport").hostname == "127.0.0.1"`. The "keeps the two sets the same
size" argument is withdrawn and replaced with what the function enforces — *the host
component, as `urlsplit` reads it, must be one of three names* — plus an explicit note that
bounding the shape space is EC-004's and CARD-020's. The same docstring's "a bare `::1` is
read correctly" was also false (`urlsplit("//::1").hostname is None`, so it is **refused**);
corrected in the same paragraph. **The check itself is byte-identical** — `git diff` on
`handler.py` removes no executable line from `_host_is_local` or `_dispatch` (G-1).

**5 — the case-sensitive auth scan (AC-062).** Two under-detections, not one: the AST scan's
`"WWW-Authenticate" not in node.value`, and `_Response.headers`, which was
`dict(response.getheaders())` — a plain dict keyed on the wire spelling, so the behavioural
`assert "WWW-Authenticate" not in response.headers` was equally case-sensitive. The scan is
lifted into `_auth_vocabulary_hits(source, name)` so it can be shown discriminating against a
fabricated source (run only over a package expected to be clean, a scan that had stopped
matching looks identical to one passing) and now compares `.lower()`; `_Response.headers` is
the parsed `http.client.HTTPMessage`, whose `in`/`[]` are case-insensitive as HTTP field
names are.
- New `TestAuthScan_IsCaseInsensitiveOnHeaderNames`: four spellings through the scan, a
  negative control (no auth vocabulary → no hits), the docstring-exclusion property kept, a
  real socket serving a lowercase `www-authenticate` from a test-local handler, and a control
  that the shipped server sends none.
- **Mutation M5** — comparison reverted to case-sensitive: **3 failed** (`www-authenticate`,
  `Www-Authenticate`, `WWW-AUTHENTICATE`).
- **Mutation M6** — `_Response.headers` reverted to `dict(getheaders())`: **1 failed**
  (`test_a_response_carrying_the_header_is_detected[www-authenticate]`).

**6 — CARD-019's failure matrix.** All four facts re-probed here, on a live socket against
this branch (`git diff` confirms no executable line of `_dispatch`/`_host_is_local` changed,
so these are merged main's behaviour):
- cross-site GET, `Host: 127.0.0.1:<port>` + `Origin: https://evil.example.com` +
  `Sec-Fetch-Site: cross-site` → **`HTTP/1.0 200 OK`, form returned**; control
  `Host: rebind.attacker.test` → **400**. Row F-8 rewritten: the check closes DNS rebinding
  only; browser-mediated cross-origin reach is NFR-004, unimplemented, CARD-020's. Row F-12's
  failure-mode cell no longer names "a cross-origin form POST".
- `GET http://evil.example.com/ HTTP/1.0` with no `Host` → **200 and the form** (also 200 with
  a loopback `Host`). Row F-12's "0 routes reached on a refused host" corrected.
- `server.__all__` exports `LoopbackHTTPServer`; its first parameter is `server_address`;
  `LoopbackHTTPServer(("0.0.0.0", 0), WebUIRequestHandler).server_address == ('0.0.0.0', …)`.
  Row F-9's "0 ways to bind another" replaced with the launcher-scoped bound, and the reason
  the guard sweep cannot see it recorded (it walks the *package* `__all__`, which omits the
  class, and matches `{host, address, bind, interface}`, which `server_address` is not).
- Row F-6's "shutdown ≤ 0.5s": confirmed to have **no covering test** — the three `serve_on`
  tests all drive `_StubServer` and assert only `server_close` was called once; the only
  `time.monotonic` in the module is in the idle-timeout test. The number is **dropped**
  rather than a timed test added: the card allows either, and a wall-clock assertion on an
  arbitrary runner is precisely the host-dependent evidence the post-hoc review criticised in
  O-1. The checkable clauses (socket released on every path out, 0s grace, exit code 0) stay.
- `## Follow-up required (2026-08-30)` added to CARD-019, pointing here, listing what CARD-022
  deliberately did **not** close (NFR-004, the absolute-form bypass, the unbounded `Host`
  value set) and flagging that rows F-4/F-5/F-10 now describe the *response* shape in stale
  terms because of item 3.

**Guardrails.** G-1 held: no line of access-control logic was added or widened — the
`ALLOWED_HOSTS` comparison, the `@`/`/` refusal and the `Host` parsing are byte-identical,
and every fix that could have been a widening was written as a narrowing of the *claim*
instead. G-2: no capability module or the orchestrator touched. G-3: `_ADAPTERS` and
`_LAUNCH_EDGE` untouched and re-verified by mutation M2b. G-4: no existing test weakened or
deleted; the auth scan was refactored into a helper and made *stricter*. G-5: no runtime
dependency, no domain logic in `web/`. G-6: nothing under `meta/architecture/` touched —
`git status` confirms the only `meta/` files this card wrote are `CARD-019.md` and this card.

**Not done / open.** Nothing blocked. Two items deliberately out of scope and left for
CARD-020, both now recorded in CARD-019's matrix rather than fixed here (G-1): the
absolute-form request-target bypass, and any bound on the accepted `Host` value set. The
post-hoc's fifth, milder vacuous loop —
`test_the_form_lists_every_registered_export_format`, which iterates `export.FORMATS` with
no minimum-count assertion — is **not** fixed: it is outside this card's four-loop AC-059
scope and its collection comes from COMP-007, not from `web/`. Worth a follow-up.

### Orchestrator notes

- **[Blocker check]** none.
- **[Guard]** 1 commit `81504e5`, 4 files, code only — `meta/` verified absent from the branch.
- **[Build gate]** PASSED, independently re-run: **1290 passed, 1 xfailed, exit 0** (from 1261,
  **+29**). No regressions; the `bench_generate` xfail is untouched. All four AC tests green by name.
- **[Scope]** in scope — 4 changed files, all inside the declared `Touches`.
- **[G-1 verified on the wire, not from the report]** the guardrail this card lived or died on.
  `grep` finds no `Sec-Fetch`/`Origin` read in `web/`, and behaviourally: cross-site GET with an
  allowlisted Host → **200** (still open), absolute-form target → **200** (still open), foreign
  Host → **400** (unchanged). The card repaired the claims and left the protection to CARD-020,
  which is exactly the split it was cut for.
- **[Behaviour change, judged acceptable]** `send_error` now funnels the five stdlib statuses through
  `_respond`. It is a real change, not prose — but it is the only way "nosniff on every response"
  can be made TRUE rather than narrowed, it is not access control, and it fixed something worse than
  the report found: 400 and 505 previously returned **no status line and no headers at all**
  (`request_version` stuck at HTTP/0.9). Verified: a malformed request line now answers
  `HTTP/1.0 400 Bad Request` where it used to answer with a bare connection close.
- **[Judgement calls accepted]** (a) F-6's `<= 0.5s` shutdown bound was DROPPED rather than given a
  timed test — the card permitted either, and a wall-clock assertion is exactly the host-dependent
  evidence the post-hoc review criticised. (b) A fifth, milder vacuous loop
  (`test_the_form_lists_every_registered_export_format`, iterating `export.FORMATS`) was left alone:
  outside AC-059's four, and its collection comes from COMP-007, not `web/`. Both need a follow-up
  card rather than silent inclusion here.
- **[Review sync]** 1 report → `meta/review/20260830T175453Z-CARD-022-cycle1.yml`.
- **[Review 1/3] 7.5/10 — FAIL (severity gate).** 0 Critical, **4 Important**, all one root cause
  and it is the sharpest possible criticism of this card: **it fixed the named instance of each
  false claim, not the family.** Two of the four were falsified by *this card's own* `send_error`
  change — a truth-repair card that introduced fresh inaccuracies, which is precisely the failure
  mode the review was pointed at.
  - F-001 `handler.py:55` — the `ALLOWED_HOSTS` comment still says the Host check "closes the
    browser-mediated half of the access control". That is **verbatim the sentence this card struck
    from matrix row F-8**, left standing three files away.
  - F-002 `web/__init__.py:42` — "a POST gets the standard library's own 501" was falsified by this
    card's own override; `handler.py:15-19` now says the opposite. The two docstrings contradict
    each other and AC-060's test does not catch it.
  - F-003 `web/__init__.py:44` — "Access control is the bind address and nothing else" contradicts
    `handler.py:56`/`:288` and this card's own corrected row F-8 ("exactly 2 checks"). **AC-060 is
    therefore not met for the docstring as a whole**, only for its two named sentences.
  - F-004 CARD-019 rows **F-4, F-5, F-10** — falsified by the same `send_error` override and left
    uncorrected, while the card asserts "this card's matrix is the record other cards read".
  Plus 4 Minor, one genuinely ironic: **F-005 — a NEW unguarded `_WEB_SOURCES` loop at
  `tests/test_web_server.py:1503`**, the very pattern AC-059 exists to remove.
- **[Guard] G-1 HELD, verified independently and thoroughly.** The reviewer diffed the wire
  main-vs-branch across eight request shapes — cross-site 200/200, absolute-form 200/200, foreign
  Host 400/400, `#evil` 200/200, `?evil` 200/200, `:notaport` 200/200, bare `::1` 400/400,
  `[::1]:8765` 200/200 — all identical. Nothing widened, nothing narrowed, both CSRF vectors
  correctly still open. G-2/G-3/G-5/G-6 hold; **G-4 discharged by evidence**: under the
  `send_error`-removal mutant all six pre-existing request-line params pass unedited.
- **[Verified] the escalation over the post-hoc report was accurate.** On main, 400 and 505 returned
  a bare body with no status line and no headers, and the 501 reflected the request method into the
  reason phrase **unescaped** (`501 Unsupported method ('<script>alert(1)</script>')`). All five now
  carry a real status line, `text/plain`, `nosniff`, and echo nothing. No status the handler already
  owned changed.
- **[Accepted] both deliberate omissions ruled defensible** — the dropped 0.5s bound genuinely had
  no covering test and a wall-clock assertion is the host-dependent evidence the post-hoc
  criticised; the fifth loop's collection (`export.FORMATS`) cannot go empty the way a glob can.
  But neither deferral reached `backlog.md` (Minor F-008) — capture, don't just narrate.

- **[Fix 1] declarations** — commit `6daf56a` (new commit; `81504e5` intact).
  All 8 cycle-1 findings resolved. F-001/F-002/F-003/F-006 were claim
  corrections in `web/__init__.py` and `handler.py` — the card's own purpose was
  repairing false claims and cycle 1 found it had introduced four more.
  F-005/F-007 restored the test guards (`_WEB_SOURCES` non-empty assertion,
  `match=` on AC-059's selector-emptying test).
  F-004 folded the CARD-019 matrix corrections into rows F-4/F-5/F-10 themselves
  and deleted the separate section that had held them — applied to BOTH the
  worktree copy and main's, since main's is 10 lines longer and copying the file
  would have lost orchestrator notes.
  F-008 moved the two deliberate omissions out of card prose and into
  `meta/kanban/backlog.md`, where the next wave's planner sees them.
  Suite: 1292 passed, 1 xfailed.
- **[Review sync]** 1 report(s) → meta/review/; F-001..F-008 marked fixed_in 6daf56a.

- **[Review 2/3]** Score: 8.5 — crit: 0, imp: 0 ✓ threshold reached + no
  critical/important. Report: `meta/review/20260831T013708Z-CARD-022-cycle2.yml`.
  CONFIRMATION MODE with **0 verdicts carried** — the reviewer's own intersection
  check found the delta touches every guardrail's and every rule's scope, so all
  8 system rules and all 6 guardrails were re-verified fresh.
  System contract: 8 checked, 3 ✓ holds, 5 ⚠ unchecked (4 no_eligible_fact,
  1 check_ref_missing: CON-010), 0 ✗ violated.
  All 8 cycle-1 findings resolved and MUTATION-VERIFIED — 4 mutants, all killed,
  including reverting each corrected docstring sentence to prove the new tests
  actually pin it. An AST comparison with docstrings stripped shows all three
  changed src modules EXECUTABLE-IDENTICAL to 81504e5, so nothing on the wire
  could have moved; confirmed anyway by ~15 raw-socket probes.
  Both accuracy questions re-derived on the wire rather than accepted: "the
  statuses are the stdlib's, the responses are not" is TRUE, and the 501 reason
  phrase really did change from `Unsupported method ('POST')`/text-html to
  `Not Implemented`/text-plain+nosniff.
  5 Minor findings, none gating — and notably 3 of them are FRESH inaccurate
  claims in the fix delta's own new prose. That is the third consecutive cycle in
  which this card, whose purpose is repairing false claims, shipped new ones.
  The reviewer deducted 0.5 for the recurrence itself rather than for any defect.
- **[Review sync]** 1 report(s) → meta/review/.
- **[AC/EC check]** GATE: all items verified. Run by the orchestrator directly
  after the gate agent died on an API error mid-run (it had reached the wire
  probes); these are mechanical checks and were re-derived rather than re-spawned.
  No `## Engineering constraints` section on this card, so no EC verified
  directly.
  **Executable-identical claim VERIFIED independently** — an AST comparison with
  docstrings stripped shows `web/handler.py`, `web/__init__.py` and
  `web/pages.py` all IDENTICAL to `81504e5`. This is the load-bearing fact: the
  delta adds no executable line, so no behavioural regression is possible.
  G-3 verified: `_ADAPTERS = frozenset({"cli","web"})` and `_LAUNCH_EDGE =
  ("cli","web")` are untouched by the delta (0 diff hits), and their pinning
  assertions still stand at test_cli.py:653/672.
  G-4 verified: the one apparently-removed assertion is the rewrite
  `assert set(w) >= {X}` → `missing = {X} - set(w); assert not missing`. Checked
  the set theory rather than accepting it: `A ⊇ B ⟺ B − A = ∅`, so it is
  identical, and the new form names WHICH modules are missing on failure — an
  improvement, not a weakening. 12 assertions added, none removed.
  The card's two NEW tests verified non-tautological: each asserts a behavioural
  precondition first (`send_error in vars(...)`; `_host_is_local` discriminating
  both ways) and guards its sentence list with `assert sentences, ...` before
  iterating — AC-059's own discipline applied to the card's new evidence.
  AC-059 verified: five `assert _WEB_SOURCES` guards now present (the fifth at
  :1567 is the one cycle 1 found missing), and both `pytest.raises` calls carry
  `match=`.
  Both meta/ fixes verified in the worktree AND main: CARD-019's rows carry the
  correction, the separate section is gone, and the backlog has both entries.
  `tests/test_web_server.py` + `tests/test_cli.py`: all pass. Worktree clean.

- **[Merge]** Merged to main as `137e367` (--no-ff). Merge gate: full suite on
  the MERGED tree = **1292 passed, 1 xfailed**, matching the branch result.
  Cycle-2 F-104/F-105 were fixed in BOTH copies of CARD-019.md before merging
  (main's is longer and carries orchestrator notes, so the file was never
  copied across — the edits were applied to each independently). F-104's claim
  was re-probed on the wire first rather than taken from the review: 200 header
  fields and a 70,000-byte header line both return `431 Request Header Fields
  Too Large`, so "Too many headers"/"Line too long" name the two CAUSES and
  appear only in the log — the bound cell had written the log line as if it were
  the wire. F-101/F-102/F-103 dismissed to the backlog with the reason recorded
  in the cycle-2 report.
  84 of the user's staged files (docs/cell_size.md, pic1/ x62, pictures/ x21)
  plus 2 untracked templates were unstaged before the merge so the merge commit
  could not sweep them in, then restored to their exact prior AM split and
  verified byte-for-byte against pre-merge backups.
