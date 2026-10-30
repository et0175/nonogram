# 08 — Playing a stored puzzle (CAP-007 / FR-044)

> Scope: one admin route, one template and two static scripts —
> `GET /puzzle/<puzzle_id>/solve` (`admin/app.py:6191`),
> `admin/templates/puzzle_solve.html`, `admin/static/solver.js` (76,946 bytes)
> and `admin/static/solver_state.js` (42,903 bytes). Governed by ADR-0038.

## Why this capability exists, and why it has no command

CAP-007 was added on 2026-10-03 and `capabilities.yml`'s header records the
reasoning for it being a *new* capability rather than a fold into an existing one:
"CAP-001..CAP-005 produce a puzzle (sourcing, clues, uniqueness, difficulty,
files) and CAP-006 assembles books; **none lets a person solve one**." CAP-005
Puzzle export was considered — CON-002 had framed playable output beside the static
exports — and rejected: "the player emits no artifact and runs in the admin panel,
not COMP-007."

It is the only capability in the model with **no event, no command and no
aggregate**, and that is deliberate: *playing changes no system state.* All marks
are browser-local (CON-021), so there is nothing for a CMD to be. CON-002 is
superseded by CON-021, which was narrow when it was written on 2026-10-03:
interactive play allowed, but **only as this admin-panel page** — no public
player, no persisted play state, no accounts; and the admin POC may ship the
solution while a public one may not (`requirements.yml:247`). CON-021 was amended
on 2026-10-06 to allow play state in *this browser's* `localStorage` only — "still
nothing on the server".

**That "only as this admin-panel page" clause no longer holds, and this file is
about the first of the two forms that replaced it.** FR-045 and ADR-0041
(2026-10-23) added the public player, and CON-021's current statement
(`trace.yml:631`) reads "interactive play in exactly two forms — the admin panel's
puzzle player (behind CON-015/CON-016, may ship the solution) and the public
player per ADR-0041 (static, read-only, no accounts, localStorage-only, never
ships a solution); everything else forbidden, no server-persisted play state
anywhere". Both are CAP-007. The second one is
[11 — the public player](11-the-public-player.md); everything below here is the
panel's page, which is still the only one that may ship a solution grid.

## The naming trap, stated by the model itself

`requirements.yml:4067` is unusually emphatic, and it is the first thing to get
right about this file:

> NAMING: this is the PUZZLE PLAYER (TERM-037), a page a person solves a puzzle
> on. It is **NOT** the uniqueness solver (COMP-005, `src/nonogram/solver/`,
> TERM-004), and nothing here changes that component. "Solver" unqualified keeps
> meaning COMP-005.

The route's own docstring says the same from the code side (`app.py:6195`): "Not
the uniqueness solver (COMP-005): this only *reads* one puzzle and hands it to
`static/solver.js`, which does everything else in the browser. Nothing is written
(G-3, CON-017)."

## How the route works

The whole of the server-side mechanism is nine lines:

```python
@app.route("/puzzle/<puzzle_id>/solve")                  # app.py:6191
def puzzle_solve(puzzle_id):
    puzzle, _grid, payload = _board_page_payload(puzzle_id)
    tier = tier_of_record(puzzle.get("difficulty_tier"))
    title = puzzle.get("puzzle_name") or puzzle.get("source_image") or str(puzzle["id"])[:8]
    return render_template(
        "puzzle_solve.html",
        title=title,
        extent=(payload["width"], payload["height"]),
        tier_label=tier.value.upper() if tier else None,
        payload=payload,
    )
```

Four things in it are load-bearing.

**1. The clues are re-encoded from the stored grid, never read off the row**
(ADR-0038/R3, `app.py:6199`): "the row's stored clue and size columns are never
read, **so a stale row cannot show clues that disagree with its own grid**." That
goes through `compute_clues` — the one encoder, COMP-004 — which is why `db/models.py:63`
annotates `clues_rows` as `# display only`: the authority is always the grid.

**2. The solution grid ships in the payload**, for the live error count
(`app.py:6202`). This is scoped by ADR-0038/R6 and CON-021 to the admin player
specifically, "allowed for the admin player only, behind the panel's door … **a
public player must not do this.**" It is a security property of the panel's door
(see [09](09-the-three-inbound-adapters.md)), not of this route.

**3. The picture's name is the answer, so it is deliberately not on the page
header.** The header and the tab title show the grid's `width × height` and tier
instead (FR-044 AC-322/AC-323); `title` reaches only the solved banner, which
reveals it (AC-316). Same instinct as the book band's omission of the title in
[07](07-book-assembly-and-the-admin-panel.md) — a titled page gives the picture
away before the solver has drawn it.

**4. The payload is shared with the editor page and written once.**
`_board_page_payload` serves both, and the comment records why (`:6210`, review
cycle 1 F-015). No `mode` is passed, "so this payload stays exactly the six keys
`solver.js`'s header documents (CARD-246 G-1)."

## What ships in the browser

`admin/static/solver.js` (76,946 bytes) and `admin/static/solver_state.js`
(42,903 bytes) implement the board itself: marking cells by click cycle and line
drags, stroke-level undo and redo, the live error count against the solution, the
solved state, and reset. `capabilities.yml` CAP-007 adds one scope bound
explicitly: **hints are out of V1.**

ADR-0038 names the two technology choices — plain JavaScript, and Playwright for
the tests. `pyproject.toml:35` is `dev = ["pytest>=8.3", "pytest-playwright>=0.7"]`
with a comment that is itself part of how this works: "pip does not install the
browser itself — run `playwright install chromium` once per checkout and as a CI
step before the suite (ADR-0038/R8); **without it the `browser`-marked tests fail
with that instruction rather than skipping green.**" The marker is declared at
`pyproject.toml:92`.

ADR-0038/R5 is why the scripts are listed as package data (`pyproject.toml:85`):
"`static/*.js` is the puzzle player's client; without it an editable install works
and a built wheel serves a player page with no script."

## The "nothing is written" claim is tested as a property

`tests/test_puzzle_solver_page.py` does not assert the absence of writes by
reading the code. It watches the tables:

```python
_WATCHED_TABLES = ("puzzles", "books", "batches", "generation_history")   # :1298
```

It seeds a `generation_history` row (`:1316`) and then asserts that "open, 10
strokes, solve: no row of puzzles, books, batches or generation_history changes"
(`:1324`, AC-302). That is the shape of guard this project reaches for: a property
over observable state, not an inspection of intent.

## Bounds and honest gaps

- **CAP-007 is absent from the component diagram.** `capabilities.yml` and
  `contexts.yml` both carry it, and `trace.yml`'s 2026-10-03 (b) note confirms the
  component as COMP-009 and corrects an earlier mislabel ("the decision-surfacing
  note's 'COMP-008' was a mislabel"). But the COMP inventory comment block in
  `c4/components-CTX-001.puml` still lists CAP-001..CAP-006 only, COMP-009's
  capability line reads `CAP-006`, and its ADR list stops at ADR-0037 with no
  ADR-0038. **The registries are ahead of the diagram here.**
- The two scripts, 120 KB of shipped browser code, are named by no component in
  the model. ADR-0038 governs them; no C4 element contains them.
- `localStorage` resume is browser-side by CON-021's 2026-10-06 amendment, so
  **nothing about a play session is recoverable server-side at all** — not by the
  owner, not by an operator, not by a later card without re-opening CON-021.

## Related

- [11-the-public-player.md](11-the-public-player.md) — the other form of play: static, answer-free, outside the door
- [07-book-assembly-and-the-admin-panel.md](07-book-assembly-and-the-admin-panel.md) — the panel this route lives in
- [09-the-three-inbound-adapters.md](09-the-three-inbound-adapters.md) — the door that makes shipping the solution acceptable
- [04-uniqueness-and-recovery.md](04-uniqueness-and-recovery.md) — COMP-005, the *other* thing called a solver
- ADR: [ADR-0038](../../../../meta/architecture/decisions/adr/0038-puzzle-player-plain-js-and-playwright.md)
