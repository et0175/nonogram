# CARD-264: CLAUDE.md's three remaining false claims, and the dead symbol one of them has already fed into a live guard

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/264-claude-md-outside-the-map
**Worktree:** —
**Source:** CARD-261's implementation hand-back, 2026-10-22: it re-derived all three defects as real and **left them in place deliberately**, because G-4 confined that card to the layout block. Reported rather than absorbed, which is why they are a card and not a silent fix.
**Idea:** —
**Wave:** 54 (next — see the sequencing note)
**Depends on:** CARD-261 (**it rewrites the layout block, so every line number below will move — see the first Worktree note**)
**Touches:** CLAUDE.md, tests/test_web_server.py, tests/test_timeout.py, tests/test_sourcing_image.py, tests/test_cli.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — three false claims in the file every agent brief is built from, and one has already spread

`CLAUDE.md` is loaded as project instructions in **every** session, and step 7a of the kanban `start`
procedure extracts its sections into **every implementation agent's brief**. CARD-261 gave the component
map a derived control and corrected it. These three are outside that block, were re-derived as real, and
were left alone because G-4 forbade touching them.

All three verified against `main` at the time of writing:

| where | the claim | reality |
|---|---|---|
| `CLAUDE.md:56` | cites `sourcing/random_grid.py`'s **`validate_size`**/`validate_density` | **`validate_size` has zero definitions anywhere in `src/`.** The public validator is `validate_extent` (`random_grid.py:131`); `_validate_side` (`:115`) is private, and ADR-0022/R1's refusal of a one-integer public validator is recorded in its docstring — *"half an extent is not a thing the model validates"* |
| `CLAUDE.md:58` | "stdlib + Pillow + NumPy … (plus **`pytest`** as a dev-only extra)" | the first half is exactly right; there are **three** extras — `dev` (`pytest`, **`pytest-playwright`**), `admin` (Flask, Werkzeug, reportlab, gunicorn), `db` (SQLAlchemy, alembic, psycopg2-binary). `pyproject.toml:42` already carries the correct wording: *"ADR-0006/R1's baseline is `project.dependencies` above … the extras have always been outside it"* |
| `CLAUDE.md:60` | "a cooperative timeout (hook points already present …, **not yet enforced**)" | **it is fully enforced.** `orchestrator.py:1793` fixes one `time.monotonic` deadline per request and passes it at `:1859`; it is checked at **six** sites — `propagate.py:983`, `:1129`, `search.py:1180`, `:1259`, `:1418`, `:1728` — and raises `SolverTimeout` at `propagate.py:221` |
| `CLAUDE.md:60` | "random mid-density grids at **40×40+**" | `limits.py:17` caps a side at **30**, so that size cannot be produced |

**`:60`'s first defect is the expensive one**, by the same argument CARD-261 made about "the only inbound
adapter": a brief is **acted on**. An agent told the cooperative timeout is *not yet enforced* may set
out to add it — re-implementing a mechanism that exists at six check sites, or worse, adding a second
one beside it.

## The dead symbol has already propagated into a live guard, where it is inert

This is why the card is more than a prose fix. `tests/test_web_server.py:2053` is a **live assertion**,
cited by its own docstring as the enforcement of ADR-0019/R1 (the web adapter performs no domain
validation):

```python
assert _WEB_SOURCES, "no web adapter sources found"
for path in _WEB_SOURCES:
    source = path.read_text(encoding="utf-8")
    for token in ("validate_size", "validate_density", "parse_tier"):
        assert token not in source, f"{path.name} references {token!r}"
```

Measured — `def <token>` across `src/`:

| token | definition |
|---|---|
| `validate_size` | **none anywhere** → the member can never fail for a real reason |
| `validate_density` | `sourcing/random_grid.py:383` |
| `parse_tier` | `difficulty.py:562` |

So **one third of this guard's vocabulary is dead**: a token that exists in no module cannot appear in a
web source, so that arm is unfalsifiable. It is the **fourth** appearance of this exact shape on this
board in a week — CARD-206's `GEOMETRY_DOORS` second member carried nothing (`args[0]` was the book),
CARD-262 inherits `AsyncFor` and `NamedExpr` with no control anywhere, and here a guard's set contains a
symbol that no longer exists.

**And the author was alert to the adjacent vacuity and missed this one.** The same docstring says
`_WEB_SOURCES` is asserted non-empty first *"because an empty glob would have it certify that rule by
reading nothing"* — vacuity guarded on the **file** axis, unguarded on the **token** axis. That is worth
stating in the fix, because it is the general lesson: a guard over a *set* needs its set checked, not
only its *input*.

## What to implement

1. **Correct `:56` and `:58`.** `validate_extent`, and the three extras as `pyproject.toml:42` already
   words them. Prefer pointing at `pyproject.toml` over restating its contents — a restated dependency
   set is a second copy that can drift, which is the disease CARD-261 just treated.
2. **`:60` — delete the claim rather than correct it.** "Not yet enforced" corrected to "enforced"
   becomes false again the day someone removes a check site, and nothing would notice. The durable form
   is to **say what the code guarantees and let the tests carry it**, or to drop the clause and cite the
   test that pins the enforcement. Decide and say which. The "40×40+" figure should become a size
   `limits.py` can actually produce, or lose the number — a figure in a brief is a claim whose only
   control is recomputation, and this one has been wrong since it was written.
3. **Repair the guard's set, and give the set a control.** Remove or replace the dead `validate_size`
   member, and add the check the guard lacks: **every token in that set must name a symbol that exists
   in `src/`**, so a member that stops existing reds instead of going quiet. Derive the symbol set from
   the code (`ast`), not from a second hand-written list — ADR-0039/R2.
4. **The three stale test docstrings.** `tests/test_timeout.py:13` ("a 50×50 request is now rejected by
   `validate_size`" — doubly wrong: the symbol and the size), `tests/test_sourcing_image.py:743`
   (`random_grid.validate_size`), and `tests/test_web_server.py:2053`'s token, covered by step 3.

## Acceptance criteria

- **AC-1** *Given* `CLAUDE.md`, *then* every code symbol it names in the boundary-types and
  dependency-baseline paragraphs exists in `src/`, asserted by a control that **derives the symbol set
  from the code** rather than from a list. (test: `TestClaudeMd_EverySymbolItNamesExists`)
- **AC-2** *Given* a **planted** reference in `CLAUDE.md` to a symbol that does not exist, *then* AC-1's
  control reds **naming the symbol and its line**; removed, it passes. Both states demonstrated.
  (test: `TestClaudeMd_APlantedDeadSymbolReds`)
- **AC-3** *Given* the dependency paragraph, *then* it does not restate `pyproject.toml`'s extras — or,
  if it does, a control holds the two in agreement and reds when they diverge. **State which shape
  shipped and why.** (test: `TestClaudeMd_TheDependencyClaimMatchesPyproject`)
- **AC-4** *Given* `tests/test_web_server.py`'s domain-validation guard, *then* every token in its set
  names a symbol defined in `src/`, and a token that names none is a **FAILURE**, not a silent pass.
  (test: `TestWebAdapter_TheForbiddenTokenSetHasNoDeadMember`)
- **AC-5** *Given* a **planted** dead token added to that guard's set, *then* AC-4's control reds naming
  it; removed, it passes — and separately, a planted *real* reference to `validate_density` in a web
  source still reds the original guard, so repairing the set did not weaken what it already caught.
- **AC-6** *Given* the whole change, *then* no claim about the solver's timeout survives that no test
  pins. Either the clause is gone or the test that enforces it is named in the same sentence.
- **AC-7** *Given* `tests/test_cli.py`'s adapter allowlist, *then* no prose around it claims a
  count that disagrees with `_ADAPTERS`, and the test's **name** states the rule rather than a
  number — held by a control that reads `len(_ADAPTERS)` rather than restating it.
  (test: `TestAdapterAllowlist_NoProseClaimsAStaleCount`)

## Routed in from CARD-261's review cycle 1 — F-107, measured wider than it was filed

The reviewer filed one minor at zero (pre-existing, outside the diff):
`test_the_adapter_allowlist_is_closed_at_the_two_known_adapters` asserts **three** names. I went and
looked, because CARD-261's F-101 fix points a reader straight at `_ADAPTERS`, and a reader following
that pointer lands here. It is **three** stale "two" claims in one place, not one:

| where | the claim | reality |
|---|---|---|
| `tests/test_cli.py:904` | the test's **name** says `_at_the_two_known_adapters` | the set holds **three** |
| `tests/test_cli.py:905` | the docstring's first line: *"ADR-0019's allowlist is two names, and staying two names is the rule"* | three names since `admin` joined |
| `tests/test_cli.py:743-744` | the module comment above `_ADAPTERS`: *"this set is closed at two names and is deliberately not a pattern — a third adapter is a decision, not a rename"* | the third adapter **was** that decision, and it landed; the sentence now reads as a prohibition on something already done |

**The assertion itself is correct and the control works** — `assert _ADAPTERS == {"cli", "web", "admin"}`
(`:914`) plus the rank check pins the set literally, which is exactly what it should do. Only the prose
lies. That is this card's whole subject in one function: a claim with no control, in a file agents read,
sitting **on top of** a control that does its job. The honest fix is to make the prose state the *rule*
("the set is closed and grows only by a deliberate edit to this line") instead of a *count*, and to let
the only number in the vicinity be the one the assertion holds.

**Why it is routed here and not fixed on CARD-261.** CARD-261's G-4 confines it to the layout block and
to the component map; this is neither. CARD-264 already carries `tests/test_cli.py` in its `Touches` and
already exists to fix claims-without-controls in agent-read prose. Rename the test if you judge the name
worth the churn — say which you chose and why. It is the **fifth** appearance of this shape on the board
in a week, after CARD-206's empty `GEOMETRY_DOORS` member, CARD-262's uncontrolled `AsyncFor`/`NamedExpr`,
this card's dead `validate_size` token, and CARD-261's two gating findings.

## Guardrails

- G-1: **The layout block is CARD-261's** — do not edit it, and do not reintroduce a component row.
  G-4 on that card and this one are mirror images; between them, every line of `CLAUDE.md` has exactly
  one owner.
- G-2: **The web adapter's guard must not be weakened.** `_WEB_SOURCES`'s non-empty assertion stays,
  and repairing the token set must not reduce what the guard catches — AC-5's second half is the control
  for that. ADR-0019/R1 is what the guard enforces.
- G-3: **No second copy of anything.** Not of the extras, not of the symbol list, not of the component
  map. The controls *read* their sources.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-6: ADR-0036/R4 — no codepoint in U+25A0..U+25FF, U+2022 or U+2219 in any `src/nonogram/**` string
  literal, docstrings included. This card edits no `src/` file, so the rule should be satisfied by
  construction — **verify that rather than assuming it**, since `CLAUDE.md` is not under `src/`.
- G-7: Take no timing measurements and report no durations.

## Architecture context

- **ADR:** ADR-0039/R1–R3 are the subject — a claim needs a control that can fail; a guard's set is
  derived from an authority the runtime can enumerate and a shape it cannot analyse is a FAILURE;
  an exemption carries a control. ADR-0019/R1 (the web adapter performs no domain validation) is what
  the repaired guard enforces. ADR-0022/R1 (extent as a pair) is why `validate_size` does not exist.
  ADR-0006/R1 (the closed dependency baseline) is what `:58` describes.
- **Components:** none changed. This card edits `CLAUDE.md` and test files only.
- **Trace:** `meta/architecture/trace.yml` — unchanged; no requirement's verifying test moves.

## Worktree notes

- **[Every line number in this card will have moved — re-derive them]** CARD-261 rewrites `CLAUDE.md`'s
  layout block, and its diff changes the file's line count. `:56`, `:58` and `:60` are the numbers on
  `main` at drafting time. **Locate each defect by its text, not by its line** — the orchestrator was
  caught out by exactly this while drafting: an earlier reading of these same three defects reported
  them at different lines, because the file had moved under it. This is the card's own subject in
  miniature.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files
  **case-insensitively** for the reach-limit idiom. Sanity check: `Touches` includes `tests/**`, so
  ADR-0039 must be in the kept set.
- **[Two figures the orchestrator got wrong on the way here, both re-derived by CARD-261's agent]** The
  deadline is checked at **six** sites, not the four the orchestrator's brief stated — a subset
  presented as complete. And "misinforming every brief for 51 waves" was never derivable: `git log -L`
  shows those lines touched by exactly two commits, 2026-09-08 and 2026-10-22, and nothing in the repo
  maps the former to a wave number, so the honest figure is a **date range of about six weeks**. Both
  are corrected on CARD-261. Named here because this card will be tempted to repeat them.
- **[Do not take timing measurements]** other cards may share this machine.
- **[Use CARD-260's committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from
  line 453, for any per-assertion figure. Do not write another. Keep deletion mutants
  **line-count-preserving**, aggregate **any-RED**, and **report the DOMAIN** of every figure.
- **[The general lesson this card should leave behind]** A guard over a **set** needs its *set* checked,
  not only its *input*. `test_web_server.py`'s own docstring shows the author guarding vacuity on the
  file axis — *"an empty glob would have it certify that rule by reading nothing"* — while a member of
  the token set had silently died. Four cards in one week have now been gated or carded on a set member
  with no possible failure. If a standing check is worth having anywhere on this board, it is *"every
  member of every hand-written guard set still names something that exists"*, and this card is the
  natural place to propose it.

## [Owner decision 2026-10-22] AC-7 stays here, and this card goes out next wave

CARD-261's cycle 2 raised the question of folding AC-7 into that card's fix round, because CARD-261
creates the first **reachable** pointer from the every-session file into `_ADAPTERS`. The owner's decision
is to **keep it separate and dispatch CARD-264 next**, so CARD-261 stays inside its slice.

**The failure mode this card now closes is worse than the one CARD-261 removed, and it is reachable only
because of CARD-261.** The reviewer's reading, which is the sharpest argument on this card: the *value* in
`_ADAPTERS` is correct and matches the canonical map, but the prose around it says "two" in all three
places. A reader who follows CARD-261's new pointer, finds a set of three under prose saying two, and
concludes `admin` is the erosion will **remove a correct entry** — strictly worse than the stale count it
replaced. The window is one wave long by design; do not widen this card to shorten it.
