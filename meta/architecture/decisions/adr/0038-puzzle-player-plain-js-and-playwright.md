# ADR-0038: The puzzle player is plain JavaScript in the admin panel, tested with pytest-playwright

**Status:** Accepted
**Date:** 2026-10-03
**Deciders:** Olga (project owner)
**Revised:** 2026-10-06 (History: R8 — there is no CI; browser tests run locally, the CI clause applies once CI exists)
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

FR-044 adds a puzzle player (TERM-037) to the admin panel (COMP-009, CAP-007 Puzzle play): a page at `/puzzle/<puzzle_id>/solve` where a person marks cells by click cycle and line drags, with stroke-level undo and redo, a live error count (TERM-038), a solved state and a reset. All of that must run in the browser: AC-311 forbids a network request per mark, which rules out any server round-trip-per-mark design (server-rendered forms, htmx-style partials). CON-021, which supersedes CON-002, allows interactive play only as this admin page behind the door of CON-015 / CON-016, persists no play state (CON-017), and permits the page to ship the puzzle's solution grid to the browser for the admin panel only.

Two questions stay open. The first, DEC-040, is how the browser client is built and delivered. ADR-0006/R1 closes the runtime dependency set at stdlib + Pillow + NumPy and draws its line between executable dependencies (closed) and static data (admissible). The admin panel is a Flask adapter (ADR-0030, ADR-0032) that already serves `admin/static/` (`admin.css`, `tokens.css`), and several of its templates already carry inline `<script>` blocks. `pyproject.toml` package-data for `nonogram.admin` lists only `templates/*.html` and `static/*.css`. The `nonogram-web/` directory holds only stale build artefacts of an earlier Next.js experiment, with no source to reuse.

The second, DEC-041, is what verifies the player's browser behaviour. Several FR-044 criteria are only observable in a real browser: drag constrained to one line (AC-305, AC-306), keyboard shortcuts and accessible names (AC-309, AC-310), no request per mark (AC-311), reduced motion (AC-319) and an in-page confirmation instead of `confirm()` (AC-321). EC-035..EC-037 are property tests over the client's state logic. `pytest-playwright` and Chromium are installed in the venv today, but no `pyproject.toml` entry declares them and no test uses them. Any tool chosen here is dev-only and outside ADR-0006/R1's runtime baseline, as the `dev` and `admin` extras always were. The repo has already been caught by tests that skip green when their prerequisite is missing (the DB-mode tests without a `nonogram_test` database), so a silent skip is a known failure mode here.

## Decision

**We will build the puzzle player as hand-written JavaScript and CSS served as static files by the Flask admin panel, and verify it with browser-level tests run by pytest-playwright and Chromium, declared as a dev-only extra.** This ADR resolves both DEC-040 (`plain_js_static_files_in_flask`) and DEC-041 (`pytest_playwright_dev_extra`). They are decided together because the test runner only makes sense once the client is known.

**Client (DEC-040).** A Jinja-rendered `/puzzle/<puzzle_id>/solve` page embeds the puzzle as JSON: its clues as `compute_clues` of the stored grid (the one encoder, FR-005, never re-derived in JavaScript) and its solution grid. Static `.js` and `.css` files under `src/nonogram/admin/static/` do all marking, undo and redo, the error count and the solved check in the browser. There is no framework, no build step, no npm, no vendored third-party library and no new runtime dependency, so ADR-0006/R1 holds unchanged. The player's state logic (board, strokes, undo and redo history, error count, solved predicate) lives in a small pure module separate from DOM rendering, so it can be tested in isolation. One consequence must be carried by the implementation: `pyproject.toml` package-data for `nonogram.admin` must also list `static/*.js`, or the player's script is missing from every built wheel. That is the same trap the bundled font and the templates hit before.

**Solution in the page (CON-021, restated).** The admin player ships the puzzle's solution grid to the browser to compute the error count and the solved state. This is permitted for the admin panel only, because the page sits behind the same door as every other admin page (CON-015, CON-016). A public or reader-facing player must not send a puzzle's solution to the browser before it is solved. Any public phase therefore reopens this ADR to move the check server-side or reveal the solution only on solve. The page must not be re-hosted publicly as-is.

**Tests (DEC-041).** `pytest-playwright` is declared in a dev-only extra in `pyproject.toml`, never in `project.dependencies` or the `admin` extra. Browser tests drive the real page served by the Flask test app inside the existing pytest suite. The EC-035..EC-037 property corpora are built in Python with stdlib `random.Random` (the repo's property-test style, no `hypothesis`) and evaluated against the page's state module in the browser, each checked against an independent Python reference. When Chromium is not installed, browser tests must fail or skip **loudly**, with a named skip reason shown in the run summary, and never pass silently. CI needs an explicit `playwright install chromium` step.

This ADR records the decision only. It does not itself change `pyproject.toml` or code: CARD-160 implements the package-data entry and the dev extra.

The choice is also the lowest-cost option on both questions. It adds no container, no deploy unit, no toolchain and no executable dependency. It keeps one process, one origin and one auth door. It is the only testing option that puts the shipped JavaScript, not a copy of it, under automated test for every browser-only AC.

## Alternatives considered

### Separate React/Next.js front end over a JSON API (DEC-040)
A separate React/Next.js app consuming a new JSON endpoint on the admin panel for the clues and solution. It would bring a component model, a mature ecosystem and JavaScript-native test tooling. Rejected: it brings in a Node build toolchain, a second deploy unit, a new C4 container, a new API contract and a two-origin auth story now, for a public phase that is not yet decided. `nonogram-web/` holds only stale build artefacts, so there is nothing to reuse. The owner rejected it on 2026-10-03.

### Plain JavaScript plus one vendored micro-library such as Preact+htm or Alpine.js (DEC-040)
The same static-file delivery, with one small reactive library vendored as a static file. It would reduce hand-written state-to-DOM sync. Rejected: it ships third-party executable code inside the package, which pushes against ADR-0006/R1's line between executable dependencies (closed) and static data (admissible). That would need the rule revisited or explicitly scoped to browser assets. It would also bring licence, update and supply-chain ownership, for a UI (one board, three tools, undo/redo, a counter) small enough not to need it.

### Node's built-in test runner for the state module (DEC-041)
Test the JavaScript state module directly under `node:test`, with no npm packages, keeping browser-only ACs manual. Rejected: it adds Node as a dev and CI prerequisite outside the Python toolchain, plus a second test runner beside pytest. AC-305, AC-306, AC-309, AC-310, AC-311, AC-319 and AC-321 would still have no automated check.

### Python harness only, no browser tests (DEC-041)
Mirror the client's state rules in a Python reference model for the property tests, check the page only as server HTML, and verify interaction by eye. Rejected: it tests a Python copy, not the JavaScript users run, so drift between the two would go unnoticed. The browser-only ACs AC-305, AC-306, AC-309, AC-310, AC-311, AC-319 and AC-321 would get no automated check at all. That was the owner's stated reason for rejecting it.

## Consequences

### Positive
- ADR-0006/R1 and the `admin` extra are unchanged: no new runtime dependency and no third-party executable code in the package.
- One process, one deploy and one auth door. The page sits behind the same CON-015 / CON-016 guard as every admin page, with no CORS or token plumbing.
- No C4 change. The player is a route, a template and static assets of the existing COMP-009, so only a trace-only synthesis follows.
- Every browser-only FR-044 AC and EC-035..EC-037 get automated checks inside the existing pytest suite, against the shipped JavaScript.
- The pure state module keeps the correctness-relevant logic (history replay, error count, solved predicate) testable apart from rendering.

### Negative
- State-to-DOM sync for a board of up to 30×30 is hand-written. Keeping the state module pure and separate from rendering is the implementer's discipline, not a framework's guarantee.
- The package-data entry is a trap: without `static/*.js` in `pyproject.toml`, an editable install works and a built wheel ships a page with no script.
- Chromium is a large binary that pip does not install. Fresh checkouts and CI need `playwright install chromium`, and a missing browser must be loud, not green.
- Browser tests are slower and flakier than unit tests and need a marker so the fast suite stays fast.
- The decision is scoped to the admin POC. A public player must reopen it because of CON-021's solution clause, and it may outgrow plain JavaScript then.

### Neutral
- `pytest-playwright` moves from "installed but undeclared" to declared in a dev-only extra. It is a dev-tooling dependency, outside `project.dependencies`.
- CARD-160..CARD-162 are re-decomposed against this outcome. CARD-160 carries the package-data and dev-extra changes.
- The solution grid is visible in the page source to anyone who can open the admin page. That is accepted for admins and is the line a public player must not cross.

## References

- DEC-040, DEC-041 (resolved by this ADR)
- CTX-001 (affected context); CAP-007 Puzzle play; COMP-009 Admin Panel
- FR-044 (the puzzle player); AC-305, AC-306, AC-309, AC-310, AC-311, AC-319, AC-321; EC-035, EC-036, EC-037
- CON-021 (interactive play admin-only; solution-in-the-page clause), CON-015, CON-016, CON-017; CON-002 (superseded by CON-021)
- FR-005 (`compute_clues`, the one encoder)
- ADR-0006 (dependency baseline, R1), ADR-0030 and ADR-0032 (admin panel deployment and storage guard), ADR-0019 (inbound-adapter boundary the admin panel follows as a rank-0 adapter)

## History

- 2026-10-03: Created. It resolves DEC-040 (plain JavaScript and CSS as static files in the Flask admin panel, with no framework, build step or vendored library) and DEC-041 (pytest-playwright and Chromium as a dev-only extra, with a loud skip). Both are owner-confirmed choices that add no runtime dependency, no container and no toolchain, and that put the shipped JavaScript under browser-level test.
- 2026-10-06: Revised (owner decision, IDEA-065; raw-requirements.md Delta 2026-10-06 (a); no DEC — a correction of a rule's premise, not a new decision). R8 assumed a CI pipeline ("CI installs Chromium ... before running them"); the project has none. R8 now states the local reality: browser tests run on a developer machine with Chromium installed by `playwright install chromium`, and when it is missing they fail or skip loudly (unchanged). The CI sentence becomes conditional — it applies only once a CI pipeline exists — and "no CI" is recorded as a known gap, not a satisfied rule. No other rule's meaning changes. (Same day, outside this ADR: FR-044 now admits browser-local resume in localStorage, CON-021 amended; R2 — no network request per mark — is unchanged and still holds for it.) Migration: on-touch — no test or code is out of step with the revised R8; the CI clause binds whoever first builds a CI pipeline.

## Rules

```yaml
- id: ADR-0038/R1
  statement: >-
    The puzzle player's client is hand-written JavaScript and CSS served as
    static files by the admin panel. There is no front-end framework, no build
    step, no npm toolchain and no vendored third-party JavaScript library.
    Adding any of these reopens this ADR (and ADR-0006/R1 for vendored code).
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/static/**", "src/nonogram/admin/templates/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0038/R2
  statement: >-
    Marking, undo, redo, the error count and the solved check run entirely in
    the browser. A loaded player page issues no network request per mark.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/static/**"]}
  check: {kind: test, ref: TestSolverMarking_NoRequestPerMark}   # FR-044 AC-311 (planned, CARD-161)
  severity: mandatory
- id: ADR-0038/R3
  statement: >-
    The player page's clues are embedded as JSON from compute_clues of the
    stored grid (the one encoder). The client never re-derives clues from the
    solution.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/**"]}
  check: {kind: test, ref: TestSolverPage_ShowsTheClues}   # FR-044 AC-297 (planned, CARD-160)
  severity: mandatory
- id: ADR-0038/R4
  statement: >-
    The player's state logic (board, strokes, undo/redo history, error count,
    solved predicate) lives in a pure module with no DOM access, separate from
    rendering.
  scope: {contexts: [CTX-001], code: ["src/nonogram/admin/static/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0038/R5
  statement: >-
    pyproject.toml package-data for nonogram.admin includes static/*.js
    alongside templates/*.html and static/*.css, so the player's script ships
    in every built wheel.
  scope: {code: ["pyproject.toml"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0038/R6
  statement: >-
    Only the admin panel's player, behind the CON-015 / CON-016 door, may ship
    a puzzle's solution grid to the browser. A public or reader-facing player
    must not send the solution before the puzzle is solved, and any public
    phase reopens this ADR (CON-021).
  scope: {contexts: [CTX-001], code: ["src/nonogram/**"]}
  check: {kind: review-lens}
  severity: mandatory
- id: ADR-0038/R7
  statement: >-
    Browser tests use pytest-playwright with Chromium, declared only in a
    dev-only extra in pyproject.toml. It is never added to project.dependencies
    or to the admin extra.
  scope: {code: ["pyproject.toml", "tests/**"]}
  check: {kind: review-lens}
  severity: mandatory
# Revised 2026-10-06 (IDEA-065): was "CI installs Chromium ... before
# running them" — unconditional, though no CI exists.
- id: ADR-0038/R8
  statement: >-
    Browser tests run locally, against Chromium installed by
    `playwright install chromium`. When Chromium is not installed, browser
    tests fail or skip loudly, with a named skip reason visible in the run
    summary. They never pass silently. Once a CI pipeline exists, it installs
    Chromium (playwright install chromium) before running them; until then
    there is no CI, and that is a known gap, not a met clause.
  scope: {code: ["tests/**"]}
  check: {kind: review-lens}
  severity: mandatory
```
