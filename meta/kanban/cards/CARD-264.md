# CARD-264: CLAUDE.md's three remaining false claims, and the dead symbol one of them has already fed into a live guard

**Status:** review
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/264-claude-md-outside-the-map
**Worktree:** ../PythonProject4-card-264
**Source:** CARD-261's implementation hand-back, 2026-10-22: it re-derived all three defects as real and **left them in place deliberately**, because G-4 confined that card to the layout block. Reported rather than absorbed, which is why they are a card and not a silent fix.
**Idea:** —
**Wave:** 54
**Depends on:** CARD-261 (**it rewrites the layout block, so every line number below will move — see the first Worktree note**)
**Touches:** CLAUDE.md, tests/test_web_server.py, tests/test_timeout.py, tests/test_sourcing_image.py, tests/test_guard_integrity.py, docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md  <!-- tests/test_cli.py REMOVED 2026-10-22: folded into CARD-265 -->
**Review score:** 8.3 (c1) → 5.5 (c2) → 9.6 (c3) → 8h spot-check FAILED 2 of 2 holds → owner: fix+certify → fix 3 `098ecd91` → 7.65 (c4: NOT CERTIFIED, 2 imp, both introduced BY fix 3) → **owner: one more fix + cycle 5** → fix 4 `8727e519` pre-gated + gated (8931 exec, 0 failed) → 7.6 (c5: NOT CERTIFIED, 2 imp, both introduced BY fix 4) — ⚠ improvement stalled, family regression streak 2 → owner: fix both + narrow re-entry review → fix 5 `6c29d282` pre-gated + **gated (8931 exec, 0 failed, count flat as predicted)** → **narrow re-entry review in flight**
**Started:** 2026-10-22T13:55Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —  <!-- escalation CLOSED 2026-10-23: owner chose option 1, fix S-1..S-4 then certify with a re-entry cycle -->

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
   `validate_size`" — **the symbol only; see the correction below, my "doubly wrong" was wrong**), `tests/test_sourcing_image.py:743`
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
- ~~**AC-7**~~ **WITHDRAWN FROM THIS CARD 2026-10-23 — moved to CARD-265, and this is bookkeeping the
  owner's 2026-10-22 decision already decided, not a weakening taken at review time.** It read:
  *Given* `tests/test_cli.py`'s adapter allowlist, *then* no prose around it claims a count that
  disagrees with `_ADAPTERS`, and the test's **name** states the rule rather than a number — held by a
  control that reads `len(_ADAPTERS)` rather than restating it.
  (test: `TestAdapterAllowlist_NoProseClaimsAStaleCount`)

  **Why it had to move with the file, and why leaving it here would have been worse than removing it.**
  Option 1 of the escalation folded `tests/test_cli.py` into CARD-265 and the narrowing merge
  `4f7263fb` resolved that file to **main's version, verified byte-identical**. So AC-7's named control
  is not in this branch: `git diff main...HEAD` does not list `tests/test_cli.py` at all. An AC whose
  test no longer exists in the diff can only be scored `✗ unverified` — and this board's own routing
  reads a repeated `unverified` as *the criterion is unverifiable as written*, which would have sent a
  correctly-executed owner decision back to the architect station as a requirement defect. The work
  itself is not lost and is not weakened: all nine functions are named on CARD-265, recoverable at
  `git show d5da18ff:tests/test_cli.py`, with the explicit condition that each must be **re-measured**
  against whichever `_ADAPTER_COUNT` bound that card settles on. CARD-265 additionally carries the
  two-way table showing neither bound dominates, which is more than this card ever knew.

  **What this card is still answerable for, and it is not nothing.** AC-7's subject was prose claiming
  a count; the *route* that made that prose reachable was `CLAUDE.md`'s pointer into `_ADAPTERS`, and
  this card still closes the `CLAUDE.md` end of it (see AC-1/AC-3 and `## Guardrails` G-1). The
  remaining open site is named on the card, measured, and deliberately left:
  `src/nonogram/web/__init__.py:21`.

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

## [Owner decision 2026-10-22] AC-7 stays here, and this card goes out next wave  <!-- SUPERSEDED 2026-10-23 -->

> **Superseded 2026-10-23 by the owner's fold decision**, recorded in the `Touches` comment at the top of
> this card and in the `## Narrowed` section: AC-7 moved to **CARD-265**. The section below is kept as the
> record of why it was *not* folded a day earlier, which is still the honest history — but it no longer
> states what is true, and the AC block above marks AC-7 withdrawn.

CARD-261's cycle 2 raised the question of folding AC-7 into that card's fix round, because CARD-261
creates the first **reachable** pointer from the every-session file into `_ADAPTERS`. The owner's decision
is to **keep it separate and dispatch CARD-264 next**, so CARD-261 stays inside its slice.

**The failure mode this card now closes is worse than the one CARD-261 removed, and it is reachable only
because of CARD-261.** The reviewer's reading, which is the sharpest argument on this card: the *value* in
`_ADAPTERS` is correct and matches the canonical map, but the prose around it says "two" in all three
places. A reader who follows CARD-261's new pointer, finds a set of three under prose saying two, and
concludes `admin` is the erosion will **remove a correct entry** — strictly worse than the stale count it
replaced. The window is one wave long by design; do not widen this card to shorten it.

## [System contract] derived at dispatch 2026-10-22 — projection 10, kept **5**, dropped **5**

Derived with `system_rules.py --card CARD-264 --root meta/architecture` and curated under
`meta/kanban/curation.md`: keep every `check.kind: review-lens` rule, keep every `kind: test` rule whose
ADR declares a reach limit, drop the remaining `kind: test` rules because the suite executes them on
every gate. The idiom grep ran **case-insensitively over the ADR files** and selected ADR-0036, ADR-0037
and ADR-0039 — ADR-0039 writes it in capitals, which is why the case-insensitive read matters.

**Sanity check passes:** this card's `Touches` includes `tests/**`, so ADR-0039 must be in the kept set,
and R1–R3 are all present. The projection is unusually small (10, where recent book cards saw 41–58)
because this card touches no `src/` file at all — four test files and `CLAUDE.md`.

**Kept (5):**

| rule | kind | why kept |
|---|---|---|
| ADR-0038/R7 | review-lens | `pytest-playwright` is declared only in a dev-only extra, never in `project.dependencies` or the admin extra — **directly relevant**, since AC-3 is about how `CLAUDE.md` describes the extras |
| ADR-0038/R8 | review-lens | browser tests fail or skip **loudly** with a named reason, never silently |
| ADR-0039/R1 | test, reach-limited | a claim needs a control that can fail; caught WITH the set member, missed WITHOUT it — **this card's AC-4/AC-5 are exactly this shape** |
| ADR-0039/R2 | test, reach-limited | a guard's set is derived from an authority the runtime can enumerate; where none exists it defaults to deny — **AC-1 and AC-4 both turn on it** |
| ADR-0039/R3 | test, reach-limited | an exemption is a claim and carries a control for what it must NOT absorb |

**Dropped (5), all `kind: test` with a named executing control:** CON-005
(`PropertyTest_Solver_NeverFalsePositiveUniqueness`), CON-009
(`TestWebServer_BindsLoopbackOnlyByDefault`), CON-010
(`PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`), CON-011
(`PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`), CON-012
(`PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore`).

**One of the dropped rules deserves a word, because this card edits the file that enforces it.** CON-009
and CON-010 are the web adapter's loopback and cross-origin controls, and they live in
`tests/test_web_server.py` — the file whose domain-validation guard this card repairs. They are dropped
because the suite executes them, not because they are irrelevant: **G-2 exists to keep them intact**, and
a repair to the forbidden-token set that happened to weaken them would red those two named tests. That is
the right division — the contract tells the reviewer what nothing executes, and the gate holds the rest.

## [Dispatch note] based on **CARD-261's tip**, not on `main`, and the rebase is owed

The worktree is cut from `feb3e6b5` — CARD-261's fix-1 commit — rather than from `main`. The reason is
this card's own first `## Worktree notes` entry: CARD-261 rewrites `CLAUDE.md`'s layout block and moves
every line number below it, and the orchestrator was already caught out by exactly that while drafting.
Cutting from `main` would have had the implementation read `:56`/`:58`/`:60` and write controls against a
file about to change underneath it in the same two paths. Cut from `feb3e6b5` the three defects sit at
**`:46`/`:48`/`:50`**, which is what the card's table predicted, and the implementation sees the real
post-CARD-261 file.

**The two cards share two paths and collide in neither**, which is by construction: G-4 on CARD-261 and
G-1 here were written as mirror images so every line of `CLAUDE.md` has exactly one owner. CARD-261 owns
the layout block (its diff is one hunk) and the `TestComponentMap_*` classes; this card owns `:46`/`:48`/
`:50` and the adapter-allowlist region. CARD-261's cycle 2 verified the out-of-block defects present and
byte-identical, from the other side.

**Owed:** a rebase onto `main` after CARD-261 merges, before this card's own gate, so the tree tested is
the tree merged. CARD-261 still has fix 2 in flight and a cycle 3 to run, so this base will fall behind;
the regions are disjoint, so the rebase should be clean, but it is not optional.

## Worktree notes -- implementation, 2026-10-22

### [Every defect located by text; the line numbers the dispatch note predicted held]

On `feb3e6b5` the three claims sat at `CLAUDE.md:46`, `:48`, `:50`, exactly as the dispatch note
predicted. **Every edit was located by its text**, and the only line number this card's controls
ever print is one they *computed* while reading: `CLAUDE.md:46` in the AC-2 plant's failure message.
`GUARDED_PARAGRAPHS` locates all three paragraphs by their bold lead-in, and a lead-in it cannot
find is a FAILURE, not a smaller sweep (mutant M5 below measures that).

### [What shipped, and the three shape decisions the brief asked me to state]

1. **AC-3 shipped as "do not restate" (no second copy).** The paragraph names the runtime baseline
   (`project.dependencies`: Pillow + NumPy) and points at `pyproject.toml` for the extras without
   enumerating them -- so there is no copy of the extras table to drift, which is what CARD-261 just
   treated in the component map. Both halves are still controlled from `pyproject.toml` via
   `tomllib`: every runtime distribution must be named, no extra-only distribution may be named, no
   extra name may appear in backticks, and the paragraph must cite the authority. The old wording
   named `pytest` as *the* dev-only extra; the corrected paragraph names no extra at all, which also
   keeps ADR-0038/R7 readable from it (see the verdict lines).
2. **AC-6/the timeout claim: the clause was deleted and replaced, not corrected.** It now says what
   the code guarantees -- one cooperative deadline per request, checked as the solver propagates and
   branches, raising `SolverTimeout` rather than running forever -- and **names
   `tests/test_timeout.py` in the same sentence**. "Not yet enforced" corrected to "enforced" would
   have been false again the day a check site was removed; a named test is a claim the suite carries.
   The control holds the pairing: the one sentence in the guarded paragraphs that speaks about a
   timeout or a deadline must cite a path under `tests/` that exists, and the count is pinned at one
   so dropping the clause has to be a deliberate edit (the `_LAUNCH_EDGE` precedent).
3. **The `40x40+` figure lost its number.** It reads "near `limits.MAX_SIZE`" -- a pointer at the
   authority rather than a second copy of 30 (G-3). The figure rule is kept as a standing deny with
   **no instance left in the tree**, so it carries a fabricated red case (`40x40` reds naming the
   side and the range; `30x30` passes). A deny rule with no instance and no fabricated case is the
   unfalsifiable arm this card is about.
4. **AC-7: the test was renamed.** `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters`
   -> `test_the_adapter_allowlist_is_closed_and_grows_only_by_a_deliberate_edit`. The name is the
   loudest of the three claims -- it is what every `-v` line and every failure report prints -- and
   AC-7 asks for a name that states the rule. The churn was measured first: **four live citations**
   outside `tests/test_cli.py`, of which one is committable
   (`docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md`, updated in the
   same commit) and three are card files under `meta/`, which the kanban procedure excludes from this
   branch and which are historical records of what was true when they were written.

### [AC-4/AC-5: the set was derived, not re-listed]

`_DOMAIN_VALIDATORS` is now `tuple(sorted(_domain_validator_names()))` -- every
`validate_*`/`parse_*` function the package defines **outside the adapter rank**, where which
modules are adapters is read from `tests.test_cli._ADAPTERS` (the same authority that defines the
rank; a fourth adapter admitted there changes this set with no edit here). Measured: **6 members**
(`_validate_side`, `parse_art`, `parse_tier`, `validate_aspect_ratio`, `validate_density`,
`validate_extent`) against the retired hand-written **3**, of which one was dead. Nothing the guard
caught before is given up (G-2): `validate_density` and `parse_tier` are both in the derived set and
still swept over the raw source text, and a floor pin reds if the derivation stops reaching them.

**The replacement was not free, and this is the measured finding of the card.** `validate_extent`
*already appears* in a web source -- `web/submission.py`'s `_extent_token` docstring, which says the
tokens it parses are "refused inward by `sourcing.random_grid.validate_extent`". That is the adapter
**documenting its compliance** with the rule the guard enforces, so a naive substitution would have
had the guard red on the sentence that states its own rule. The guard therefore runs two sweeps:

* an **AST sweep** (`_domain_validator_hits`, built on the module's existing `_docstring_nodes` the
  same way `_auth_vocabulary_hits` is): an import, an attribute, a bare name or a non-docstring
  string literal naming a validator is the erosion ADR-0019/R1 forbids. This is the rule, and it is
  **wider** than what shipped: 6 names, and `getattr(m, "validate_extent")` is inside it.
* a **substring sweep** keeping the old breadth (comments included), with exactly one ADR-0039/R3
  exemption, `MEASURED_PROSE_CITATIONS = (("submission.py", "validate_extent"),)`, held to an
  **equality** against the prose sites that exist today and held to what it must **not** absorb --
  the same name in code, which the AST arm catches regardless of the table.

### [The vacuity lesson, made executable where it was half-made]

`TestWebGuards_EveryStructuralLoopAssertsNonEmpty` empties every collection its guards loop over,
and its docstring says why: "an empty glob would have it certify that rule by reading nothing". That
is the **file** axis. The domain-validator guard loops over two collections, and the **set** axis had
no such case while a third of the set had silently died. The guard now asserts
`_DOMAIN_VALIDATORS` non-empty on the line after `_WEB_SOURCES`, and the class has a new case that
empties it and requires the named failure, plus its unmonkeypatched control.

### [Scope decisions to report, not taken silently]

* **`tests/test_guard_integrity.py` is added to `Touches`.** AC-1/AC-2/AC-3/AC-6's controls live
  there, not in `tests/test_cli.py`. Reasons: it already binds `GUIDANCE = REPO_ROOT / "CLAUDE.md"`
  and `PYPROJECT`, and it already holds one CLAUDE.md claim to pyproject.toml as the authority
  (`TestTheInterpreterFloor`, "pyproject.toml is authoritative ... CLAUDE.md is a document about
  it"), which is AC-3's shape exactly; and it keeps this card out of `tests/test_cli.py`'s
  CARD-261 region, which still has a fix round and a review cycle in flight. AC-7's control stays in
  `tests/test_cli.py`, beside `_ADAPTERS`, which is its subject.
* **`docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md` is added to
  `Touches`.** It quoted the old `_ADAPTERS` comment and cited the old test name, so the rename would
  have made it stale; it also already documented the three stale claims, and now records them closed
  and names the one site still open. Its line-number citations into `tests/test_cli.py` were replaced
  with by-name citations, since a line number in prose is this card's own subject.
* **A fourth stale "two adapters" site exists and was deliberately left:**
  `src/nonogram/web/__init__.py` ("The structural guard in `tests/test_cli.py` knows exactly two
  adapter names -- `cli` and `web`"). This card edits no file under `src/`, which is also what makes
  G-6 hold by construction (verified: `git diff --name-only` lists no `src/` path, and a sweep for
  U+25A0..U+25FF/U+2022/U+2219 over all seven changed files is clean). Worth a follow-up card: the
  file's own docstring guard, `TestWebDocstrings_MatchTheShippedPackage` (AC-060), exists to hold
  that docstring's claims to the code and does not reach this one -- the same shape again.
  `src/nonogram/__init__.py`'s "There are exactly two adapters (ADR-0019)" is **not** a defect: the
  docstring qualifies it in the next sentence as the pipeline's adapters rather than every entry
  point, and that file is CARD-261's.

### [A disagreement with the card's own wording, reported rather than fixed by invention]

The card calls `tests/test_timeout.py:13` "doubly wrong: the symbol and the size". Only the symbol
is wrong. The sentence is about **AC-038, the superseded criterion**, which really did say 50x50, and
the claim it makes about today ("a 50x50 request is now rejected before the solver is ever entered")
is true -- `validate_extent` refuses a 50-cell side. So the fix is the symbol, plus a parenthesis
recording why the old name has no definition. Proposed AC-4 wording: *"...`tests/test_timeout.py`'s
module docstring (the symbol; the superseded 50x50 figure is correct in context)"*.

### [Evidence: measured figures, with their domains]

**Claim census (AC-1's domain).** 24 backtick-quoted claims across the three guarded paragraphs:
9 paths, 8 symbols, 4 type-or-literal expressions, 2 keywords, 1 module. Authority: 1,347 symbol
names and 60 module names enumerated from `src/nonogram/**/*.py` with `ast`, 575 repo paths, 11
distributions declared in `pyproject.toml`, **0 unparsable src files** (an unparsable one is
returned and fails the test rather than being skipped). Type-or-literal spans are resolved against
`dir(builtins)`, not a list. The two keyword spans (`choices=`, `type=`) are the one exemption and
are held to an equality.

**Declared misses (ADR-0039/R3).** `MEASURED_CLAIM_MISSES`: a claim written without backticks, and a
claim in a paragraph whose lead-in is not in `GUARDED_PARAGRAPHS`. The first is demonstrated rather
than asserted in prose -- the same dead symbol unquoted passes the rule, quoted reds.

**On-disk plants, four, each red-then-green under a `cp -p` backup verified with `shasum -a 256`
and `diff -q`, restored from a trap:**

| plant | red | green |
|---|---|---|
| AC-2: `validate_extent` -> `validate_size` in `CLAUDE.md` | `AssertionError: CLAUDE.md:46: `validate_size` (symbol) names no symbol defined in src/nonogram` -- the symbol **and its line** | 21 passed |
| AC-5a: the historical triple back in `_DOMAIN_VALIDATORS` | three arms red, naming `['validate_size']`: the dead-member rule, the planted-case equality and the floor pin | 7 passed |
| AC-5b: a real `validate_density` import+call in `web/submission.py` | `['submission.py:354 imports validate_density', 'submission.py:356 names validate_density']` -- the repair did not weaken the guard | 2 passed |
| AC-7: the three count claims, verbatim as they shipped | one red naming all three sites and printing `len(_ADAPTERS) == 3` from the live set | 6 passed |

**Kill matrix (`tests/kill_matrix.py`, the committed instrument; no other was written).**
14 mutants over 3 targets, both passes, aggregated **ANY-RED**, SHIPPED re-run between mutants.
**14 of 14 killed, no survivors.** Every mutant produced at least one FAIL cell, so none was a
no-op; the instrument also refuses a mutant whose `old` is absent. Line-count preserving throughout.

*Domain of every figure below:* the denominator is the target file's **`ast.Assert` node count**, not
a collected-test count; both are printed separately by the instrument; child instrumentation **off**.

| target | selection | denominator | SHIPPED | arms reached | mutants |
|---|---|---|---|---|---|
| `tests/test_guard_integrity.py` | the four `TestClaudeMd_*` classes | 115 assert nodes / 21 collected tests | 0 FAIL of 35 reached, pytest exit 0 | 35 of 115 | M1-M6 killed |
| `tests/test_web_server.py` | `TestWebAdapter_*` + the guard | 236 assert nodes / 8 collected tests | 0 FAIL of 19 reached, pytest exit 0 | 19 of 236 | M7-M10 killed |
| `tests/test_cli.py` | `TestAdapterAllowlist_*` | 149 assert nodes / 6 collected tests | 0 FAIL of 11 reached, pytest exit 0 | 11 of 149 | M11-M14 killed |

Per-mutant attribution (recording pass): M1 dead symbol in CLAUDE.md -> FAIL at `:3212`; M2 extras
restated -> `:3373`; M3 "not yet enforced" again -> `:3484`; M4 a grid the limits forbid -> `:3523`;
M5 a paragraph lead-in renamed -> **8** arms red at `:3190 :3194 :3198 :3221 :3363 :3445 :3475 :3520`
(default-deny: a lead-in the rule cannot find fails everywhere, it does not read less); M6 the test
citation dropped -> `:3463`; M7 the dead token back in the set -> 8 arms; M8 a real validator call in
`web/` -> `:2169 :2173`; M9 the exempted prose site gone -> `:2253` (the exemption equality); M10 the
derivation narrowed to match nothing -> 7 arms; M11/M12/M13 the comment, the test name and the
docstring each claiming a count -> `:1055`; M14 `_ADAPTERS` and its pin diverged -> `:1122 :1123`.

**The trap the brief named, reproduced on nine mutants.** In the **recording** pass M1-M4, M6 and
M7-M10 all exited **pytest 0** while the matrix recorded 1, 1, 1, 1, 1, 8, 2, 1 and 7 FAIL cells. A
test-level reading of those runs would have published nine real kills as survivors. The re-raising
pass exits 1 on all of them. This is why the figures above are arm-level and why both passes were run.

**An instrument-domain bound, measured and pre-existing.** Five tests cannot be measured by
`kill_matrix.py` at all: `TestWebGuards_EveryStructuralLoopAssertsNonEmpty`'s four
`test_a_source_sweep_fails_when_the_glob_finds_nothing` parameters (pre-existing, CARD-022) and this
card's new `test_the_domain_validator_guard_fails_when_its_token_set_is_empty`. Cause, isolated to
one test and read off the child's own output: they `monkeypatch.setattr(f"{__name__}._WEB_SOURCES",
[])`, and pytest's `monkeypatch` resolves a dotted target by **attribute walk from the package** --
`AttributeError: 'module' object at tests.test_web_server has no attribute 'test_web_server'` --
because the instrument's plugin registers the rewritten module in `sys.modules` without also setting
it as an attribute of the `tests` package. It fails identically in **both** passes with **0 FAIL
cells**, which is the "exit 1 outside the matrix's domain" shape the instrument's own README names.
They were therefore excluded from the target-B selection so SHIPPED stays trustworthy (it is exit 0,
0 FAIL of 19 reached, with them out); their evidence is the plain pytest runs and the on-disk plants.
A one-line fix in the plugin preamble (`setattr(root_package, stem, module)`) would bring them into
the instrument's domain -- **not done here**, because this card does not modify the instrument.

**Suite runs (durations not recorded, per G-7).** 1,000 passed across the six affected files
(`test_guard_integrity.py`, `test_cli.py`, `test_web_server.py`, `test_suite_profile.py`,
`test_timeout.py`, `test_sourcing_image.py`), exit 0, and 451 passed over the three files carrying new
controls under the suite's **default random ordering**. CON-009 and CON-010 --
`TestWebServer_BindsLoopbackOnlyByDefault` and
`PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`, the two dropped contract
rules living in the file whose guard this card repairs -- were run on their own: 6 passed. The full
suite was never run: `NONOGRAM_FULL_SUITE_LOCK=/tmp/card264-impl.lock` was exported for every pytest
and every script invocation, and the board's own lock was never read, written or created.

### [A standing check worth having, now measured rather than only proposed]

The general lesson is *a guard over a **set** needs its set checked, not only its input*, and this is
the fifth card in a week gated or carded on a set member with no possible failure. I measured the
feasibility of the standing version -- *"no prose under `src/` or `tests/` names a `validate_*` or
`parse_*` symbol that does not exist"* -- rather than asserting it:

* a naive sweep over `src/` + `tests/` finds 10 names with no definition in `src/`, of which 9 are
  legitimate (`parse_qs`, `parse_args`, `parse_header` and other stdlib or cross-module helpers);
* with the authority widened to **every definition in `src/` + `tests/` plus every attribute of
  every module those trees import** (`dir()` over the imported module and its classes: 9,040 repo
  definitions, 11,470 reachable attribute names), the residual is **4** names -- `parse_artefact`,
  `parse_error`, `parse_header`, `parse_timing_line` -- all of which resolve once `meta/profiling/`
  joins the authority, plus **`validate_size` at exactly 3 sites: the three this card fixes**.

So the standing check is buildable and would have caught all three of this card's prose defects with
a four-name exemption surface. It is **not** built here (the owner's instruction was not to widen
this card, and it would reach ~60 test files). Recommended as its own card, with the measurement
above as its starting bound.

### [One pre-existing defect noticed in passing, not fixed]

`src/nonogram/sourcing/templates/dog_in_house.py:6` emits `SyntaxWarning: "\," is an invalid escape
sequence` on every parse -- ASCII art in a non-raw docstring. Pre-existing, outside this card's
`Touches`, and it is a `src/` file this card does not edit. `_domain_validator_names` passes
`filename=` to `ast.parse` so the warning now names the file instead of `<unknown>:6`.

---

### [Implementation landed] `d40e9d4a` — seven files, and the dead-token replacement was not free

All seven ACs met, each with a named control, and the four plant-based ACs demonstrated in **both**
states on disk with `cp -p` backups verified by `shasum -a 256` **and** `diff -q`. All three defects were
located **by text**; the dispatch note's `:46`/`:48`/`:50` held, and the only line number any control
prints is one it computed while reading. Build gate and review cycle 1 to follow.

**The measured finding of the card, and it is the kind that only shows up when you try it.** Replacing
the dead token was not a substitution: **`validate_extent` already appears in a web source** —
`web/submission.py`'s `_extent_token` docstring says the tokens it parses are *"refused inward by
`sourcing.random_grid.validate_extent`"*. That is the adapter **documenting its compliance** with the
very rule the guard enforces, so a naive substitution would have had the guard red on the sentence that
states its own rule. The shipped guard therefore runs two sweeps: an **AST sweep** over all six derived
names (catching imports, attributes, bare names and non-docstring string literals, so
`getattr(m, "validate_extent")` is inside it), plus the **old substring sweep at its original breadth**
with exactly one ADR-0039/R3 exemption, held to an equality against today's prose sites *and* to what it
must not absorb.

**The set is now derived, and it grew.** Every `validate_*`/`parse_*` function defined outside the
adapter rank, with the rank taken from `tests.test_cli._ADAPTERS` — **six members against the retired
hand-written three**. G-2 holds: `validate_density` and `parse_tier` are both still swept, and a floor
pin reds if the derivation stops reaching them.

**The lesson is executable rather than written down.** `_DOMAIN_VALIDATORS` is asserted non-empty on the
line *after* `_WEB_SOURCES`, and `TestWebGuards_EveryStructuralLoopAssertsNonEmpty` — the class that
guarded the **file** axis — gains a case emptying the **set** axis, with its unmonkeypatched control.
That is exactly the asymmetry the card was raised on: vacuity guarded on one axis and unguarded on the
other.

**AC-3 shipped the "do not restate" shape** — the paragraph names the runtime baseline and points at
`pyproject.toml` for the extras, with both halves still controlled from `pyproject.toml` via `tomllib`.
**AC-6 deleted the timeout clause rather than correcting it**, replaced it with what the code guarantees
plus a name-check on `tests/test_timeout.py` in the same sentence, and pinned the sentence count at one
on the `_LAUNCH_EDGE` precedent. `40×40+` became *"near `limits.MAX_SIZE`"* with no number — and since
that leaves **no instance of the figure rule in the tree**, it carries a fabricated red case so the rule
still has a control that can fail. **AC-7 renamed the test** to
`test_the_adapter_allowlist_is_closed_and_grows_only_by_a_deliberate_edit`, and the control finds its
subject **by the assertion it makes, not by its name** — which is the right answer to a card about names
that lie.

**Mutant domain, in full:** 14 mutants over 3 targets, both passes, ANY-RED, SHIPPED re-run between
mutants — **14 of 14 killed, no survivors**, every mutant producing ≥1 FAIL cell so none was a no-op,
line-count preserving throughout. Denominator is each target's **`ast.Assert` node count — 115 / 236 /
149 — never the collected-test count (21 / 8 / 6)**; arms reached 35 / 19 / 11; SHIPPED 0 FAIL with arms
reached and pytest exit 0 on all three; child instrumentation off.

**The recording-pass trap, reproduced on nine mutants.** M1–M4, M6 and M7–M10 all exited **pytest 0**
while the matrix recorded 1, 1, 1, 1, 1, 8, 2, 1, 7 FAIL cells. A test-level reading would have
published **nine real kills as survivors**. That is now **four** independent measurements across three
cards in one afternoon, and it is why CARD-265's AC-5 adds the sentence to `tests/README.md`.

**Contract: 5 of 5 verdict lines, all HOLD.** ADR-0038/R7 (pyproject untouched; the corrected paragraph
names no extra and no extra-only distribution, with mutant M2 killed at `:3373` proving the control reds
if it ever does). ADR-0038/R8 (no browser test touched and **no skip mechanism added anywhere** — the one
instrument limitation found was reported as a measured bound rather than converted into a skip, which is
the distinction that rule exists for). ADR-0039/R1, R2 (default-deny proved by mutants: a renamed
paragraph lead-in reds **8 arms** rather than reading less; a derivation narrowed to match nothing reds
7), and R3 (two exemptions, each held to an equality and to what it must not absorb, with
`MEASURED_CLAIM_MISSES` demonstrating the residual hole — the same dead symbol unquoted passes, quoted
reds).

### My error on the card, corrected by the implementation

**AC-4's table said `tests/test_timeout.py:13` was "doubly wrong: the symbol and the size". Only the
symbol is wrong.** I checked the file myself: the docstring reads *"AC-084 supersedes AC-038, which said
the same thing at 50x50"*, so the 50×50 figure is a correct description of the **superseded** criterion,
and the sentence's claim about today — that a 50×50 request is refused before the solver is entered — is
also true, because `validate_extent` refuses a 50-cell side. The agent reported the disagreement instead
of inventing a fix for a defect that was not there. Card text corrected above.

### Two `Touches` additions, both reported as scope decisions rather than taken silently

- **`tests/test_guard_integrity.py`** — it already binds `GUIDANCE` and `PYPROJECT` and already holds a
  `CLAUDE.md` claim to `pyproject.toml` as the authority (`TestTheInterpreterFloor`), which is precisely
  AC-3's shape; and putting AC-1's control there keeps the card **out of CARD-261's moving region** in
  `tests/test_cli.py`. Both reasons are good, and the second one is the better one.
- **`docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md`** — it quoted the old
  `_ADAPTERS` comment and cited the old test name, so the AC-7 rename would have made it stale. Its
  line-number citations into `tests/test_cli.py` were replaced with by-name ones, which is the durable
  form.

### A fourth stale site, measured and deliberately left

`src/nonogram/web/__init__.py:21` says *"the structural guard in `tests/test_cli.py` knows exactly two
adapter names — `cli` and `web`"*. This card edits no `src/` file — which is what makes G-6 hold **by
construction, verified rather than assumed**: no `src/` path in the diff, and a U+25A0..U+25FF /
U+2022 / U+2219 sweep over all seven changed files is clean.

**And the same shape again, one level further out:** that file has its own docstring guard,
`TestWebDocstrings_MatchTheShippedPackage` (AC-060), which exists to hold its claims to the code and
**does not reach this one**. Carded forward.

Separately confirmed, and correctly judged: `src/nonogram/__init__.py`'s *"There are exactly two
adapters"* is **not** a defect — the preceding sentence qualifies it as the *pipeline's* adapters, and
that file is CARD-261's. Which matches what CARD-261's cycle 3 concluded from the other side.

### [Build gate] PASSED at `d40e9d4a` — exit 0, 23 files, 2752 collected

**The selection is 23 files, not 185, and the contrast is informative.** CARD-261's gate selected 185 of
212 because it changed `src/nonogram/__init__.py`, the **package root**, which every test importing
anything under `nonogram` reaches transitively. This card changes **no `src/` file at all**, so the
selection collapses to the always-on tree-scanning set (22 files) plus the changed test files — 23 after
dedup. That is impact scoping working as designed rather than failing: narrowing buys almost nothing for
a root and almost everything for a card that touches only tests.

**All five changed test files are in the selection — verified by name, not assumed.** `test_cli.py`,
`test_guard_integrity.py`, `test_sourcing_image.py`, `test_timeout.py`, `test_web_server.py`. That
matters more than usual here, because `tests/test_web_server.py` carries CON-009 and CON-010 (the
loopback and cross-origin controls that G-2 exists to protect), and the implementation also ran them on
their own: **6 passed**.

**`CLAUDE.md` was handled separately and the coverage argument is now measured rather than asserted.**
The selector cannot model a repository-root file (it sits outside `KNOWN_ROOTS`, so it fails closed to
`FULL` — the known gap already on the backlog). The two files that **read** `CLAUDE.md` are
`tests/test_cli.py` and `tests/test_guard_integrity.py:80`, and both are in the selection on their own
merits as changed files, so the `CLAUDE.md` change is covered completely. Note this is the corrected
figure: I previously recorded *one* reader and was wrong — `test_guard_integrity.py` binds `GUIDANCE` and
reads it at `:2840`.

**Figures reported the defensible way:** pytest's **exit code 0** plus a separate `--collect-only` pass
at **2752** tests, which executes nothing. No pass count is quoted, because this repo's `-q` output does
not reliably print one — it appeared at one gate on this board and not at two later ones, and CARD-261's
cycle 3 ruled out the `full_suite_lock` hook as the cause. Board lock not taken; pytest announced the
scratch-path redirect itself in the output.

One pre-existing warning surfaced again and is already on the backlog: `datetime.utcnow()` at
`admin/image_manager.py:588`.

---

### [Review cycle 1] **8.3 — PASS** (baseline `10 − deductions`, stated), and one finding is the card's own defect walking back in

Report: `meta/review/20261022T114447Z-CARD-264-cycle1.yml`. Deductions **2.00** → 8.00, plus a **+0.30**
adjustment recorded as its own line rather than folded into weights → **8.30**. Twelve on-disk plants,
each with a `cp -p` backup, a `shasum -a 256` manifest and a trap restore verified **two ways**.

**F-1 (0.40) is the one that matters, because it is this card's subject turned on this card's control.**
AC-7's "find the subject by the assertion it makes, not by name" survives a legitimate rename, a second
pinning test, relocation into a class method and a deleted comment block — I asked for all four and all
four held. It does **not** survive the assertion being extracted into a **neutrally-named top-level
helper**: the helper becomes "the test that pins it", so the real test's name goes unjudged. **Plant 5d
restored `test_the_adapter_allowlist_is_closed_at_the_two_known_adapters` verbatim → exit 0, 7 passed.**
The card's own defect, back on the loudest surface in the repo, green. Fix is one assertion.

**F-9 (0.30) — and this one is almost funny.** `docs/.../09-the-three-inbound-adapters.md:32-33` still
cites `# tests/test_cli.py:747` and `# :760`. Actual: 748/761 at `feb3e6b5` and **756/769** at
`d40e9d4a` — **this card's own eight-line comment addition pushed them from off-by-one to off-by-nine**,
in the very file it edited, *after* rewriting every other line citation on that page to by-name form. No
control over it. Two deleted numbers close it.

**F-3 (0.25) — the AST sweep misses an assembled name, and the prose overclaims.** A real ADR-0019/R1
violation — `getattr(random_grid, "validate_" + "extent")`, and the f-string form in
`web/submission.py` — passes both sweeps at exit 0. The *hole* is the generic static-analysis limit and
is acceptable. What is not acceptable on this card is that `_domain_validator_hits`' docstring, the
notes, **and the test's own name `test_a_string_built_reference_is_caught_too`** all claim coverage the
body does not have (it tests a whole literal). **A name that lies, in a control for a card about names
that lie.**

**F-4 (0.20) — the exemption is keyed by basename and compared as a set**, so `web/rvsub/submission.py`
with the same prose mention passes with no divergence. The brief's own prediction — *"the shape that
quietly becomes two"* — realised. One line: a relative path instead of `path.name`.

**But the exemption held the two hardest attacks, which is the part worth keeping.** A second prose
citation elsewhere reds naming `('__init__.py','validate_density')`; and a **real import and call of the
exempted token, in the exempted file, under a docstring citing the rule** reds with two arms
(`submission.py:355 imports / :356 names`). **The exemption absorbs nothing in code.**

**The remaining minors are all one declared-miss line each.** F-8: AC-6's vocabulary is two words, so a
second uncited claim phrased without them keeps the count at 1 — and a second claim joined by a **colon
or comma** also evades the pin-at-one, where an em-dash or full stop reds. F-2: `_COUNT_CLAIM` catches
all three shipped defects and the digit form but misses "two **modules**", "two **entries**", "the
**two-adapter** allowlist", "a pair of", "both". F-5: a fenced ```` ```python ```` block inside a guarded
paragraph is invisible to the span regex — and `CLAUDE.md` already carries four fences — while tables and
bullets under the same line *are* caught. F-6: a false **type** claim passes, because the four type spans
are accepted for being builtin-shaped and never checked against the code. F-10: the extras table is
restated in prose in a docstring with no control — the copy AC-3 removed from `CLAUDE.md`, one file over.

**One figure does not reproduce (F-11, 0.10): "575 repo paths".** `_repo_paths()` globs `*`, so it counts
`__pycache__/*.pyc` — the same walk gives **604** today (97 cached) or **507** excluding cache, so 575
implies 68 cached at measurement time. **Non-reproducible by construction**, and benign in effect since a
`.pyc` can never satisfy a `.py`/`.toml`/`.md` span. Everything else reproduced exactly by an independent
method: 1,347 symbols (a separate recursive-descent walker, not `ast.walk`), 60 modules, 0 unparsable, 11
distributions, the 24 claims with the breakdown **9 + 8 + 4 + 2 + 1** exact, the six derived members by
name with definition sites, and 115 / 236 / 149 assert nodes by three independent methods.

### Both of my judgements confirmed, and one of them sharpened against the card

**The AC-4 table: the implementation was right, I was right to accept it, and the card is wrong on "the
size".** `requirements.yml` has AC-038 as `status: superseded, superseded_by: AC-084` with
`given: a 50x50 …`, and its `then` is character-for-character AC-084's; `_validate_side` raises
`SizeOutOfRange` on a 50 side. So **changing `50x50` to `30x30` would make both sentences false** — a
sharper statement than "only the symbol is wrong", and the reason the agent was right to report rather
than fix.

**The fourth stale site: leaving it is right, and AC-060 provably cannot reach it.** Six probes, each
keyed on a substring selector (`imports the X`, `GenerationRequest`, `501`, `Access control`, one
GET/POST literal) — the adapter-count sentence contains none, and **no test anywhere compares
`web.__doc__` to `_ADAPTERS`**. Filed at **zero**: touching it would put a `src/` path in the diff and
cost G-6-by-construction, it is disclosed in the docs page with the correct distinction, and the
*reachable* harm — the `CLAUDE.md` → `_ADAPTERS` route — is closed. And `src/nonogram/__init__.py` is
confirmed **not** a defect for a reason better than mine: the qualification at `:71-73` **pre-emptively
quotes the sentence verbatim**, so the two cannot drift.

### Contract, guardrails, scope — all clear

**Projection 10, kept 5, derived independently**, with the documented trap reproduced: the reach idiom
case-**insensitively** over the ADR files selects ADR-0036/0037/**0039**, where case-sensitively it
returns only 0036/0037. Sanity check passes. **Verdict line for each of the five, all PASS**, and two are
worth quoting: **ADR-0038/R7** is *favourable* to AC-3's rewrite, because the old "(plus `pytest` as a
dev-only extra)" was itself false about that extra's contents; and **ADR-0038/R8** holds with **zero**
skip mechanisms added across 1,199 added lines, cross-checked by whole-file `pytest.skip` counts
unchanged in all five files and zero bare-return early exits. Every deduction sits on **R3's last clause**
(undeclared residual) and none on R1 — no claim lacks a control, and the reviewer made each control fail.

**ADR-0039/R1 was demonstrated on arms the reviewer chose, not the committed ones** — its own dead member
`parse_colour_ramp`, its own AC-2 plants at **`:48` and `:50`** (red with *computed* lines, not the
hardcoded 46), and a plant of `validate_aspect_ratio` in `web/uploads.py`, a member the retired triple did
**not** contain. So the derivation **adds caught ground** rather than merely preserving it.

**G-1..G-7 all PASS.** G-1 is three single-line hunks, `@@ -46 +46 @@`, `@@ -48 +48 @@`, `@@ -50 +50 @@`,
nothing else, with line 40 byte-identical and the project's own `_CLAUDE_MD_ROW` / `_COMPONENT_ID` /
`_ADAPTER_COUNT` detectors all at 0 hits. G-6 verified **two ways** — no `src/` path in the diff *and* an
independent per-character sweep of all seven files at 0 hits, with no whole-tree claim. CON-009/CON-010
run by the reviewer: 6 collected, **exit 0**.

**The five unmeasurable tests: the exclusion hid nothing** — exactly 5 collect, running them is exit 0,
and target B with them excluded is exit 0, so SHIPPED is a true baseline for the remainder.

**Scope gate: in scope, and both `Touches` additions correct.** The second reason for
`tests/test_guard_integrity.py` checks out numerically: CARD-261's region sits at 1309+/1725+ while this
card's `test_cli.py` edits end at **1125**. The docs page was **not optional** — the rename would have
staled its verbatim quote and its test-name citation.

**Rebase: expect it clean, with a caveat worth acting on.** CARD-261's `feb3e6b5..335c641e` touches only
its card file and `tests/test_cli.py`, and **does not touch `CLAUDE.md` at all**; its earliest
`test_cli.py` hunk is old line **1105** against this card's last at **919** — 186 lines apart. The caveat:
the call is good as of `335c641e` only, and this card now carries a **by-name** citation of
`_adapter_counts` in a new comment, so **one grep after the rebase** is owed in case a later CARD-261
round renames it.

A nit of the reviewer's that is mine: the `Touches:` **field** was never edited on the branch copy (the
projection is 10 either way, verified both ways), and `CARD-264.md` is untracked at `d40e9d4a` so the
worktree notes are not in the commit — both correct, and both handled on main's copy by the one-way sync.

---

## [One-way sync] The polish round's own notes, pulled from the card branch

## Worktree notes -- polish round 1 (`forge:fix`), 2026-10-22, on review cycle 1 (PASS, 8.3)

Commit `d5da18ff`, on top of `d40e9d4a`. Four files: `tests/test_cli.py`, `tests/test_web_server.py`,
`tests/test_guard_integrity.py` and the adapters docs page. **No `src/` path in the diff** (G-6 keeps
holding by construction) and **`CLAUDE.md` is untouched** -- still exactly the three single-line hunks
at `:46`/`:48`/`:50` against `feb3e6b5` (G-1). In base coordinates my `tests/test_cli.py` hunks end at
old line **918**, so CARD-261's region from old line 1105 is still 187 lines away and the rebase
judgement is unchanged.

### [F-1 -- the bypass, and why a dynamically located subject is the thing to watch]

The finding is the most portable result on this card, so it is stated as the general shape first:
**a hole-assertion built on the real artefact can be satisfied by that artefact's live arms; one
built on a fabricated input cannot.** F-1 is the same shape one level up -- a control that locates
its *subject* dynamically can have its subject **substituted**. `_allowlist_prose()` finds the
pinning function by the assertion it makes, which is the right answer to a card about names that
lie, and it survived every attack worth making except one: extract `assert _ADAPTERS == {...}` into a
neutrally-named top-level helper and the helper becomes "the function that pins it", so the real
test's name goes unjudged and the count can come back to it green.

The repair is **one assertion**: the carrier must be a `test_*` function. I chose that over
"the name must equal the name the comment cites" deliberately -- the citation form would red the
legitimate rename (plant 5f), which would have traded one defect for another, and the brief flagged
exactly that trade.

Both states, measured, on `tests/test_cli.py` under a `cp -p` + `shasum -a 256` + `diff -q` trap
(18 files in the manifest **up front**, including the four `src/nonogram/web/` sources and
`CLAUDE.md`, because the reviewer's plant 1a was only caught by the trap's `git status` line):

| plant | before | after | message |
|---|---|---|---|
| 5d: the pin extracted into `_rv_pin_the_adapter_allowlist()`, the old test name restored verbatim | **GREEN, exit 0** | **RED, exit 1** | `the assertion that pins _ADAPTERS lives in '_rv_pin_the_adapter_allowlist', which pytest never names` |
| 5a: a second top-level test making the identical assert | RED | **RED, exit 1, 2 arms** | `['test_..._by_a_deliberate_edit', 'test_rv_second_pin_of_the_same_set']` / `assert 2 == 1` |
| 5b: the pin relocated into a class method | RED | **RED, exit 1** | `AssertionError: []` / `assert 0 == 1` |
| 5c: the comment block replaced by 23 blank lines | RED | **RED, exit 1** | `the comment block above _ADAPTERS has gone` |
| 5f: a legitimate, count-free rename | GREEN | **GREEN, exit 0** | 10 passed -- the control still found its one subject |

Unmutated control: exit 0, 10 passed. Restore after every plant: `shasum -a 256 -c` 18 OK, `diff -q`
clean for all 18, `git status --porcelain` showing only the two untracked `meta/` files that were
already there.

Two committed cases hold the repair, both on a **fabricated module** rather than on this file --
`_allowlist_prose` now takes an optional `source`, so no edit to `tests/test_cli.py` can satisfy
them: `test_the_pin_has_to_live_in_a_test_and_not_in_a_helper` (the relocation reds, naming the
helper) and `test_a_legitimate_rename_keeps_the_subject_and_the_name_judged` (a `test_*` carrier is
accepted however named, *and* its name is judged, so the restored count is caught in both places it
travels).

### [F-3 -- a name that lied, inside a control for a card about names that lie]

`test_a_string_built_reference_is_caught_too` tested a whole literal. Renamed to
`test_a_whole_literal_reference_is_caught_too`; `_domain_validator_hits`' docstring withdraws the
`getattr` coverage claim and names the limit; the card's own sentence above is corrected in place
with the original left visible; and the family is declared in `MEASURED_AST_SWEEP_MISSES` and held
**on the miss side** by `test_a_name_assembled_at_runtime_is_a_measured_miss`. Both states: the
renamed case still passes with its body unchanged, and the two assembled forms return `[]` from the
AST arm while **no contiguous run of either source spells the token**, which is what the second half
of that test asserts -- so the declaration is about the guard, not just about the function, and is
not one word wider than measured. The static limit itself is accepted; closing it means
constant-folding arbitrary expressions, which is a different rule.

### [F-4 -- the exemption was keyed by basename; it is keyed by path now]

`_web_relative(path)` replaces `path.name` at all three sites. The table's value does not move
(`submission.py` is directly under `web/`), only the key's derivation. Worth stating alongside the
fix, because it is the stronger half of the result: **the exemption absorbs nothing in code.** The
reviewer's two hardest attacks held before the fix and still hold -- a second prose citation
elsewhere reds the equality (plant 1a), and a real import+call of the exempted token *in the exempted
file, under a docstring citing the rule* reds on two arms (plant 1b-i). What the basename key could
absorb was a non-code mention in a same-named file in a subpackage, and `web/` has no subpackage, so
the state was reachable only by creating one. Committed case on fabricated paths, since there is
nothing real to point at.

### [The declared bounds -- the fix is to declare the miss, not to close it, except where noted]

Each one is a **committed case on the correct side**, not a sentence in a docstring:

- **F-2** `MEASURED_COUNT_CLAIM_MISSES` (5 families) + `test_the_rule_names_the_paraphrases_it_cannot_see`:
  8 paraphrases on the miss side ("two modules", "two entries", "the two-adapter allowlist", "a pair
  of names", "both adapter names", "a couple of", "the adapter names number two", three filler words)
  and 4 on the caught side, including **the correct count stated plainly** -- this rule denies counts,
  not only wrong ones.
- **F-5 closed, not declared.** A fence opener inside a guarded paragraph is now emitted by `_claims`
  as its own span and **denied** by `_classify` as unanalysable. I chose closing over declaring
  because `CLAUDE.md` already carries four fences, so a declared miss here is one blank line away
  from being live -- a worse trade than a deny-side rule whose cost is rewording one paragraph.
  `test_a_fence_inside_a_guarded_paragraph_is_denied` is caught-WITH / missed-WITHOUT; document order
  is preserved by sorting spans on match position, so the single-defect cases keep their 1:1 mapping.
  Measured side effect: both the opener and the closer are denied, two cells, and the test says so.
- **F-6 declared.** A third entry in `MEASURED_CLAIM_MISSES`, demonstrated executably beside the
  first: `dict[str, frozenset[bytes]]` substituted as the clue boundary type passes, while
  `list[validate_size]` is still denied -- the branch is tight about names and blind about truth.
- **F-8 declared, both bounds.** `MEASURED_TIMEOUT_CLAIM_MISSES` + `_timeout_sentences(body)`, which
  now takes the body so it can be run against fabricated paragraphs. Four miss cases (a claim without
  either vocabulary word, twice; a second claim joined by a colon; by a comma) and three caught cases
  (a second sentence using "deadline"; a clause after an em-dash **following the full stop**; a second
  sentence using "timeout"). The citation arms were already sound and stay so: dropped -> `cited == []`
  reds, pointed at a nonexistent path -> `missing_from_repo` reds.
- **F-10 dropped, not controlled.** The class docstring says "three extras, enumerated there and
  deliberately not repeated here" and names no member; the parametrized case keeps its fabricated
  paragraph but no longer hardcodes `['admin','db','dev']` in its expected fragment, and a new
  `test_the_restatement_rule_covers_every_extra_pyproject_declares` builds its paragraph from
  pyproject.toml's own keys, so a fourth extra is covered the day it is declared.
- **F-11 fixed.** `_repo_paths()` excludes `__pycache__`, so the figure is stable, and
  `test_the_path_authority_counts_no_bytecode` holds it. **Correction, stated here rather than by
  rewriting the round that made it:** the "575 repo paths" figure in the implementation notes above
  is non-reproducible by construction -- the same walk gave 604 (97 cached) at review time, and 575
  implies 68 cached files when it was taken. The reproducible figure is the `__pycache__`-free one.
  The original line stays as the record of what that round believed (same handling as CARD-261).
- **F-7** needed nothing: both declared misses are honest, and the asymmetry is now gone anyway --
  all three entries in `MEASURED_CLAIM_MISSES` are demonstrated executably.

### [F-9 -- the fix is to remove the rottable figure, not to pin it]

`docs/.../09-the-three-inbound-adapters.md:32-33` cited `# tests/test_cli.py:747` and `# :760`;
actual 748/761 at `feb3e6b5` and **756/769** at `d40e9d4a`, because this card's own eight-line
comment addition pushed them from off-by-one to off-by-nine. **The two numbers are deleted** and the
fence cites the file by name, exactly as the rest of that page was rewritten. No control was added,
and that is the point: a docs line-number citation into another file is a figure nothing can hold
cheaply, so the right move is to stop writing one -- the same reasoning this card applied to
`40x40+`, where the figure went away rather than acquiring a pin. The page's other `:NNN` citations
point into `src/`, are untouched by this card, and were left alone to keep the round scoped.

### [Kill matrix re-fire -- all 14, both passes, because all three targets changed]

My change touches the machinery of all three target files (`_claims`/`_sentences`/`_repo_paths` in
target A, the exemption key and the AST-sweep prose in B, `_allowlist_prose` in C), so **no cell was
left un-refired**. Same committed instrument, `tests/kill_matrix.py`; no second instrument written;
mutants line-count preserving; aggregation **ANY-RED**; SHIPPED re-run between mutants and held
FAIL-free each time. **14 of 14 killed, no survivors, every mutant with at least one FAIL cell.**

*Domain of every figure: the denominator is the target file's `ast.Assert` node count, carried
separately from the collected-test count; child instrumentation **off**.*

| target | selection | denominator (was) | collected (was) | SHIPPED | arms reached (was) | mutants |
|---|---|---|---|---|---|---|
| `tests/test_guard_integrity.py` | the four `TestClaudeMd_*` classes | **132** assert nodes (115) | **25** (21) | 0 FAIL of 52 reached, pytest exit 0 | **52** of 132 (35 of 115) | M1-M6 killed |
| `tests/test_web_server.py` | `TestWebAdapter_TheForbiddenTokenSetHasNoDeadMember` + the guard | **245** assert nodes (236) | **10** (8) | 0 FAIL of 28 reached, pytest exit 0 | **28** of 245 (19 of 236) | M7-M10 killed |
| `tests/test_cli.py` | `TestAdapterAllowlist_*`, one test excluded (below) | **157** assert nodes (149) | **8** (6) | 0 FAIL of 19 reached, pytest exit 0 | **19** of 157 (11 of 149) | M11-M14 killed |

Per-mutant attribution, recording pass: M1 `:3247`; M2 `:3247 :3479`; M3 `:3677`; M4 `:3716`;
M5 **8** arms at `:3225 :3229 :3233 :3256 :3469 :3607 :3668 :3713` (default-deny intact -- a lead-in
the rule cannot find still fails everywhere rather than reading less); M6 `:3624`; M7 **4** arms at
`:2253 :2264 :2267 :2284`; M8 `:2215 :2219`; M9 `:2299` (the exemption equality, now on the
path-keyed set); M10 **7** arms; M11/M12/M13 `:1096` each; M14 `:1163 :1164`.

**The recording-pass trap, reproduced a fifth time and wider: 13 of the 14 mutants exited pytest 0
in the recording pass while the matrix recorded FAIL cells** (every mutant but M5). A test-level
reading of those runs would have published thirteen real kills as survivors. The re-raising pass
exits 1 on all fourteen. This is why every figure above is arm-level.

**A new instrument-blind test, and it announced itself.**
`TestAdapterAllowlist_NoProseClaimsAStaleCount::test_the_pin_has_to_live_in_a_test_and_not_in_a_helper`
cannot be measured by the recording pass **by construction**: it is a `pytest.raises(AssertionError)`
over an assert inside the module being instrumented, and the recording pass suppresses propagation,
so the assert at `tests/test_cli.py:1073` records FAIL instead of raising and `pytest.raises` then
fails. With it in the selection the instrument **refuses** with `LeakedPatch` -- "SHIPPED is not
FAIL-free before any mutant ... FAIL (1073,)" -- which is the README's own gate doing its job, not a
reading I had to interpret. Excluded from target C's selection only, and the exclusion hides nothing:
the test collects as 1 and passes on its own at exit 0, it is in the 610-test run below, and target C
with it excluded is SHIPPED exit 0 with 19 arms reached. This is the same *kind* of bound as the five
`monkeypatch`-dotted-target tests already declared, a different cause, and like those it is a bound
on the **instrument**, not a skip: nothing in the diff adds a skip mechanism of any kind.

### [Suite runs, and what I did not do (G-7: no timing taken, no duration reported)]

The full suite was **never** run. `NONOGRAM_FULL_SUITE_LOCK=/tmp/card264-polish1.lock` was exported
for every pytest, every script and every plant; the board's own
`meta/kanban/.full-suite.lock` was never read, written or created. Exit codes and `--collect-only`
figures only, since this repo's `-q` output does not reliably print a pass-count line.

| selection | collect | exit | printed summary |
|---|---|---|---|
| `tests/test_guard_integrity.py -k TestClaudeMd` | 25 | **0** | 25 passed, 131 deselected |
| `tests/test_web_server.py -k 'TestWebAdapter_TheForbiddenTokenSetHasNoDeadMember or test_the_web_package_imports_no_domain_validator or TestWebGuards_EveryStructuralLoopAssertsNonEmpty'` | -- | **0** | 18 passed, 147 deselected |
| `tests/test_cli.py -k 'TestAdapterAllowlist_NoProseClaimsAStaleCount or test_the_adapter_allowlist'` | -- | **0** | 10 passed, 129 deselected |
| the five changed test files, default random ordering | 610 (139+156+133+17+165) | **0** | 610 passed |
| CON-009 + CON-010 (`TestWebServer_BindsLoopbackOnlyByDefault`, `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`) | 6 | **0** | 6 passed, 159 deselected |

Could not / did not do, stated plainly:

- `src/nonogram/web/__init__.py:21` is **not** touched, as instructed. Keeping `src/` out of the diff
  is what makes G-6 hold by construction, and AC-060's guard provably cannot reach that sentence.
- No whole-tree G-6 claim. The structural fact is that the diff contains no `src/` path at all.
- The 10th `SyntaxWarning` in the `TestClaudeMd` run (9 before) is the pre-existing
  `dog_in_house.py:6` ASCII-art escape, re-reported once more because one more test now calls
  `_src_symbols()`. Not introduced here and not fixed here.
- The five pre-existing `monkeypatch`-dotted-target blind tests were not brought into the
  instrument's domain; this round does not modify the instrument either.
- No timing measured and no duration reported anywhere in this round.

---

### [Polish round 1] `d5da18ff` — every finding closed or declared with a committed case, and one closed that I expected to be declared

Four files, explicit pathspecs, nothing under `meta/`. **Zero `src/` paths** in `feb3e6b5..HEAD`, and
`CLAUDE.md` still exactly three single-line hunks at `:46`/`:48`/`:50`.

**F-1 — fixed, and the fix chose the option the brief warned about *against*.** `_allowlist_prose()`
keeps locating its subject by the assertion; one added assertion requires the carrier to be a `test_*`
function. It picked `test_*` over *"the name must equal the comment's citation"* because **the citation
form reds plant 5f** — the legitimate count-free rename — which is exactly the over-tightening I told it
to check for. So the brief's warning was load-bearing rather than decorative.

| plant | before | after |
|---|---|---|
| 5d — pin extracted into `_rv_pin_the_adapter_allowlist()`, **old name restored verbatim** | GREEN exit 0 | **RED**: *"the assertion that pins `_ADAPTERS` lives in `'_rv_pin_the_adapter_allowlist'`, which pytest never names"* |
| 5a — second top-level pin | RED | **RED, 2 arms**, naming both |
| 5b — pin into a class method | RED | **RED**, `assert 0 == 1` |
| 5c — comment block → 23 blank lines | RED | **RED**: *"the comment block above `_ADAPTERS` has gone"* |
| 5f — legitimate count-free rename | GREEN | **GREEN, 10 passed** — not over-tightened |

**And both new controls are built on a fabricated module**, because `_allowlist_prose` gained an optional
`source`. That is the lesson from CARD-261's cycle 3 applied correctly on the first try: **no edit to
`tests/test_cli.py` can satisfy them**, so they cannot be satisfied by the artefact's own live arms.

**F-9 — the two line numbers are deleted**, the fence cites `tests/test_cli.py` by name, and **no control
was added, deliberately** — removing the rottable figure is the fix, the same reasoning this card applied
to `40×40+`. The page's other `:NNN` citations point into `src/` and were left alone.

**F-3 — renamed to `test_a_whole_literal_reference_is_caught_too`** (body unchanged, still passes), the
docstring withdraws the `getattr` claim, the card notes corrected **in place with the original left
visible**, and the family declared in `MEASURED_AST_SWEEP_MISSES` — held on the miss side by a control
that *also* asserts no contiguous run of either planted source spells the token, **so the declaration
bounds the guard rather than just the function.** That distinction is the difference between a bound and
a note.

**F-4 — `_web_relative(path)` replaces `path.name` at all three sites**, with the control on fabricated
paths. The table's value is unchanged, only the key's derivation — and stated alongside: what the
basename key could absorb was *only* a non-code mention in a same-named file in a subpackage that does
not exist, because plants 1a and 1b-i held before and still do. **The exemption absorbs nothing in code.**

**F-5 was closed rather than declared, and the reasoning is right.** `_claims` emits fence openers as
spans and `_classify` denies them. It chose closing because **`CLAUDE.md` already carries four fences**,
so a declared miss sits one blank line from going live. Measured side effect reported rather than
discovered later: opener *and* closer are both denied, two cells, and the test says so.

**F-10 — the restatement is dropped**, not controlled: the docstring says "three extras, enumerated
there", the parametrised fragment no longer hardcodes `['admin','db','dev']`, and a new control builds
its paragraph from `pyproject.toml`'s own keys. That is G-3 applied to the card's own test file.

**F-11 — `_repo_paths()` now excludes `__pycache__`** with a control holding it, and the 575 figure is
corrected **in the new notes only** — the original line stays as the record of what that round believed,
the same handling CARD-261 used.

**F-2, F-6, F-8 — declared, each as committed cases on the correct side**: five miss families plus four
caught cases including the correct count stated plainly; a third `MEASURED_CLAIM_MISSES` entry
demonstrated executably (`dict[str, frozenset[bytes]]` passes, `list[validate_size]` still denied); and
`MEASURED_TIMEOUT_CLAIM_MISSES` with four misses (two vocabulary evasions, colon, comma) against three
caught (second sentence with "deadline", em-dash after a full stop, second sentence with "timeout").

### The matrix was re-fired in full, and the denominators moved

All 14 re-fired because the change touches the machinery of all three targets. **14 of 14 killed, no
survivors, every mutant ≥1 FAIL cell, both passes.** Domain — denominator is each target's `ast.Assert`
node count, carried separately from the collected-test count, child instrumentation off:

| target | denominator (was) | collected (was) | arms reached (was) | SHIPPED |
|---|---|---|---|---|
| `tests/test_guard_integrity.py` | **132** (115) | **25** (21) | **52** of 132 (35 of 115) | 0 FAIL of 52, exit 0 |
| `tests/test_web_server.py` | **245** (236) | **10** (8) | **28** of 245 (19 of 236) | 0 FAIL of 28, exit 0 |
| `tests/test_cli.py` | **157** (149) | **8** (6) | **19** of 157 (11 of 149) | 0 FAIL of 19, exit 0 |

**The recording-pass trap reproduced a fifth time and wider: 13 of 14 mutants exited pytest 0 while the
matrix recorded FAIL cells** (all but M5). Re-raising exits 1 on all fourteen. That is five independent
measurements across three cards in one day.

**A new instrument-blind test, and it announced itself through the instrument's own gate rather than
through a reading someone had to interpret.** `test_the_pin_has_to_live_in_a_test_and_not_in_a_helper`
is a `pytest.raises(AssertionError)` over an assert inside the instrumented module, so the recording pass
suppresses the raise: the assert records FAIL and `pytest.raises` then fails. With it in the selection the
instrument **refuses** with `LeakedPatch` naming cell `(1073,)`. Excluded from target C only; the
exclusion hides nothing (collects as 1, exit 0 alone, inside the 610-test run, and target C without it is
SHIPPED exit 0 at 19 reached). **A bound on the instrument, not a skip** — and no skip mechanism anywhere
in the diff, which is ADR-0038/R8's own distinction.

### Runs and rebase

`-k TestClaudeMd` 25 collected exit 0; the web guard selection exit 0; the cli allowlist selection exit 0;
**the five changed files under default random ordering, 610 collected, exit 0**; CON-009 + CON-010 run
alone, 6 collected, **exit 0**. Full suite never run. Eighteen files in the `cp -p` manifest **up front**
— including the four `web/` sources and `CLAUDE.md` — restored in a trap and verified by `shasum -a 256 -c`
(18 OK), `diff -q` (clean) **and** `git status --porcelain` after every round. That is the manifest-up-front
discipline the reviewer's own plant-1a incident argued for, adopted.

**Rebase judgement unchanged:** base-coordinate hunks in `tests/test_cli.py` now end at old line **918**
against CARD-261's region starting at **1105** — 187 lines of separation.

Two things left undone and said so: `src/nonogram/web/__init__.py:21` untouched as instructed, and the
five pre-existing `monkeypatch`-dotted-target blind tests not brought into the instrument's domain (the
instrument was not modified). And the extra `SyntaxWarning` in the `TestClaudeMd` run, 9 → 10, is the
pre-existing `dog_in_house.py:6` ASCII-art escape re-reported once more because one more test calls
`_src_symbols()` — not introduced, not fixed, already on the backlog.

---

### [Escalated] 2026-10-22 — the merge is BLOCKED, and the reason is a slice, not a defect

**Station: decompose. Route: the owner chooses one of the three options below.** Worktree and branch are
KEPT — three good commits are on it (`d40e9d4a`, `d5da18ff`, and CARD-261's two inherited ones) and
nothing here says the work is wrong.

**What was measured, before anything was changed.** `run resume` diagnosed the worktree
(DIRTY + IMPL_HAS_COMMITS, where the only dirt is this card copy and the cycle-1 review report — both
procedurally uncommittable from a worktree, so this was a review-cycle restart, not an implementation
restart). The branch is **41 commits behind main**. A dry run of the merge, which changes nothing:

```
git merge-tree --write-tree --name-only main card/264-claude-md-outside-the-map
  -> exit 1
  meta/kanban/cards/CARD-261.md
  tests/test_cli.py
```

For contrast, the same dry run on the sibling card in flight is **exit 0** — CARD-262 merges clean, so
this is specific to this branch and not a stale main.

**The conflict is semantic, in seven regions, and all seven are one mechanism.** Both sides independently
wrote `_ADAPTER_COUNT` and its corpus:

| side | the pattern it wrote | its declared bound |
|---|---|---|
| this branch | numerals and number words only | gap of **two** words to the noun |
| **main** (CARD-261 cycle 2, merged) | numerals, number words, **and words that imply a number** — `both`, `only`, `sole`, `a pair of` | gap of **one** word, **measured over 32 committed forms** in `ADAPTER_COUNT_CASES` |

main's version is strictly the more developed one, and it records *why* the two-word bound was wrong, in
its own comment: two words is wide enough to swallow a verb phrase, so `"See section 3 about inbound
adapters."` and `"the four tests cover adapters"` both matched while stating no count — *"a deny-side
guard that reds on a cross-reference is one the next card switches off rather than obeys."* It also
catches the literal F-101 defect this guard exists for (`"the only inbound adapter"`), which the
two-word numeral-only pattern **cannot** match.

**So resolving this conflict by hand is the one thing that must not happen here.** Taking this branch's
side regresses a guard whose bound was measured over 32 forms one cycle ago, and it would regress it
*silently* — a narrower deny-side pattern reds on nothing, so every test stays green while the guard
stops catching the case it was built for. That is ADR-0039/R1's defect family exactly: a claim whose
control can no longer fail. Fifteen consecutive gating findings in that family across three waves is
why this is an escalation and not a judgement call made from a merge driver.

**And the boundary already belongs to a third card.** `CARD-265` is `ready`, titled *"The
`_ADAPTER_COUNT` boundary, four one-line bounds, and the one sentence `tests/README.md` is missing"*,
with `Touches: tests/test_cli.py`. Three cards now hold one mechanism: CARD-261 (merged), this card
(branch), CARD-265 (queued). The conflict graph would have serialized this card against CARD-265
anyway; what it could not see is that main had already absorbed the mechanism.

**The owner's three options, with what each costs:**

1. **Fold the guard into CARD-265 and narrow this card to its other six files** (recommended) —
   `CLAUDE.md`, `tests/test_web_server.py`, `tests/test_timeout.py`, `tests/test_sourcing_image.py`,
   `tests/test_guard_integrity.py` and the `docs/how-it-works/…` page carry this card's actual subject
   (three false CLAUDE.md claims). Those merge clean. `tests/test_cli.py` comes off `Touches:`, and
   CARD-265 inherits the one measured question — which of the two bounds is right — as its own, with
   main's 32 cases as the corpus it must not shrink.
2. **Rebase and keep main's guard wholesale** — resolve all seven regions in main's favour, drop this
   branch's `_ADAPTER_COUNT` work, keep its `TestAdapterAllowlist_NoProseClaimsAStaleCount` only if it
   passes against main's pattern. Cheaper, but it discards this branch's cycle-1 review evidence for
   the parts it deletes, and the deletion itself would ship uncertified.
3. **`/kanban redo CARD-264`** — discard the branch and re-implement against today's main. The three
   commits are good work; this is the most expensive option and is only right if the re-slice changes
   the card's subject substantially.

**Nothing on this branch was modified.** No rebase, no merge, no commit, no `git add`. The dry run wrote
only to `/tmp`. Cycle-1's review report has been synced into the main repo's `meta/review/` so the
evidence survives a later `redo`/`abandon`.


---

### [Narrowed] 2026-10-22 — the owner chose option 1, and the merge is done

**Decision: fold the `_ADAPTER_COUNT` guard into CARD-265, narrow this card to its other six files.**
Status returns to `review`; the escalation is closed. The card is **not** in `dispatcher.state -> active`
— the cap of 2 is held by CARD-262 and CARD-270, so this card takes the next free slot rather than
breaching it. It is the furthest along of anything queued (cycle 1 already passed at 8.3), so it is first
in line.

**The merge, and what it proves.** Merge commit `4f7263fb` on `card/264-claude-md-outside-the-map`.
Both predicted conflicts resolved to **main's** version:

- `tests/test_cli.py` — and the resolution is **verified byte-identical to `main:tests/test_cli.py`**, not
  asserted. This is the whole narrowing: this card's 369-added/8-removed lines and nine new test
  functions there leave with the question. main keeps CARD-261's measured guard untouched.
- `meta/kanban/cards/CARD-261.md` — `meta/` is never authored from a worktree, so main is authoritative
  there by procedure.

**The scope after narrowing, derived from the diff rather than described:**

```
$ git diff --numstat main..HEAD
3	3	CLAUDE.md
30	13	docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md
856	0	tests/test_guard_integrity.py
1	1	tests/test_sourcing_image.py
5	2	tests/test_timeout.py
375	4	tests/test_web_server.py
```

`tests/test_cli.py` is **absent from the diff entirely**. Of those six, main had touched only `CLAUDE.md`
since the merge-base (1/11, CARD-261 retiring the layout block) and it auto-merged — which is why the
narrowing made the whole merge decidable instead of a judgement call.

**One correction to the escalation note above, recorded rather than edited into it.** That note said
taking this branch's pattern "would regress a deny-side guard silently". That is true, and it was the
right reason to refuse to resolve seven semantic regions from a merge driver — but it is **half** the
measurement. CARD-265's item 1 had already measured the other half: main's one-word gap **misses**
`"three distinct inbound adapters"`, a real count with two adjectives, which this branch's two-word gap
catches. **Neither bound dominates; the regression runs both ways.** The full two-way table now lives on
CARD-265, which is where the question went. The fold is therefore better-founded than the escalation
knew: CARD-265's own card already held both revisions of this pattern, measured, with this branch's
revision as its `feb3e6b5` column.

**Nothing of this card's own work was discarded.** The nine folded tests are recoverable at
`git show d5da18ff:tests/test_cli.py` (the commit before the merge), the branch is kept, and CARD-265
records them by name with the caveat that each must be re-measured against whichever bound that card
settles on.

**What remains for this card**, unchanged by the narrowing: the three false `CLAUDE.md` claims and the
dead symbol one of them fed into a live guard — `tests/test_guard_integrity.py` (+856) is the standing
check, with the `tests/test_web_server.py` (+375) sweep and its `MEASURED_AST_SWEEP_MISSES` /
`MEASURED_PROSE_CITATIONS` bounds. Cycle 1 passed this at **8.3**, and the polish commit `d5da18ff`
**has never been reviewed** (it was applied after cycle 1). Two cycles of the budget remain, so the
right next step is a review cycle over the narrowed diff that reads the polish commit, followed by the
AC/EC/G gate — not the AC gate alone. The board's own rule: "the reviewer told me to" is not "a reviewer
saw the result."


### [Build gate] NOT RUN on the narrowed branch — deferred deliberately, and the reason is the cap

`make impact-set BASE=$(git merge-base HEAD main)` on the narrowed branch answers **`FULL`**, not a file
list. So the "impact" gate here *is* the full suite (~16.5 min), and the owner's cap of 2 exists for
exactly one stated reason: *merges run sequentially and never with concurrent full suites*. Two card
pipelines were running pytest at the time (CARD-262's review, CARD-270's implementation), so the run was
**started and then stopped** rather than left to contend with them.

Stated plainly: **this branch currently has no gate result.** The gate runs at the start of this card's
review cycle, when it takes a free slot — which is the right place for it anyway.

Cleanup verified after the stop, not assumed: `NONOGRAM_FULL_SUITE_LOCK` was pointed at
`/tmp/card264-narrowed.lock` throughout, and after the stop **neither that path nor the board's
`meta/kanban/.full-suite.lock` exists**; `git status --porcelain` in the worktree is empty; and the only
pytest left running was CARD-270's own scoped run. So no sibling was ever exposed to a foreign lock
holder (CARD-255's guard) and nothing was left half-written.

Worth carrying into whoever runs that gate: **why does a diff of one doc, one CLAUDE.md edit and four
test files answer `FULL`?** If the impact script falls back to full because `CLAUDE.md` is a repo-wide
fact, that is correct but worth a line in `tests/README.md`; if it falls back for a reason nobody
intended, that is a finding about the harness and belongs on its own card. Do not paper over it by
hand-picking test files — a narrowed gate chosen by a human is not an impact set.

---

### [Re-entry] 2026-10-23 — the owner's "start CARD-264"; the slot CARD-270's merge freed

`Status` was already `review`, so this is a **review-cycle re-entry, not an implementation
start**: nothing in the worktree is re-run, cycle 1's 8.3 stands, and the thing that has never
been looked at is the polish commit `d5da18ff`. Two cycles of the three-cycle budget remain.
`dispatcher.state -> active` now holds this card alone against the cap of 2 — the second slot is
left deliberately empty, because this card's gate **is** the full suite and it takes the board's
real lock for the duration.

**The owed rebase, taken a second time and clean this time.** Merge `99782837` brings wave 54's
two merged cards (`faea50a5` CARD-262, `64da37f6` CARD-270) onto the branch. The overlap was
**measured, not predicted**: `git diff --name-only <merge-base>..main` names 25 paths and
**none of them is one of this card's six** — main's code side is `admin.css` plus four player and
book test files, this card's is `CLAUDE.md`, one docs page and four test files.
`git merge-tree --write-tree` returned **exit 0 before the merge was run**, so unlike the first
rebase — seven semantic regions, escalated rather than resolved from a merge driver — this one
needed no judgement at all. `git diff --numstat main...HEAD` after the merge is byte-for-byte the
same six-file, 1270-line diff as before it.

### [Build gate] the `FULL` question the card left for whoever ran this gate — answered, and it is one path

The card asked: *why does a diff of one doc, one `CLAUDE.md` edit and four test files answer
`FULL`?* Measured on the merged branch, by elimination rather than by reading the script:

| selection | answer |
|---|---|
| all six changed files | `FULL` |
| the five that live under `KNOWN_ROOTS` (`CLAUDE.md` dropped) | **24 files**, a real selection |
| `CLAUDE.md` alone | `FULL` |

So the fallback has exactly one cause, and it is the **intended** branch:
`scripts/impact_set.py`'s `KNOWN_ROOTS` is `("src/", "tests/", "meta/", "docs/", "scripts/",
"migrations/")` and `select()` returns `FULL` for any changed path matching none of them —
*"I do not know what this is"* and *"this affects nothing"* are different answers and only one of
them is safe. A repo-root file is the first kind.

**No new card is owed, because the finding already exists and is sharper than this.**
`meta/kanban/backlog.md:338` carries it as an `@ops` item, filed at CARD-261's build gate, with
the readers already enumerated — `tests/test_cli.py` and `tests/test_guard_integrity.py:80` read
`CLAUDE.md`, while 40 of the 42 test files that mention it only cite it in prose — and with the
bound the fix must keep: the fallback stays `FULL`, never a guess. Today's measurement adds one
thing to it: the fallback is reachable from a **single** path in a six-path diff, so the cost of
the gap is the whole suite rather than a proportional widening. The sibling item at `:340` (the
`PY` default is `./.venv/bin/python`, which no worktree has) was hit again here and worked around
the same way, `PY=` pointing at main's interpreter as an interpreter only.

This is the answer the card asked to be carried, and it is the benign half of the fork it named:
the script falls back because `CLAUDE.md` is a repo-wide fact it cannot model, which is correct.
Nothing was hand-picked — the gate runs the full suite, which is what `FULL` means.

### [Review sync] cycle 1's report is in `meta/review/`; and **two of the polish round's own fixes left with the fold**

`meta/review/20261022T114447Z-CARD-264-cycle1.yml` (63 KB) is in the main repo, so the evidence
survives whatever happens to the worktree. Re-read for this re-entry: cycle 1 was **0 critical, 0
important** — all twelve findings were minor / nit / zero, which is why it passed the severity gate at
8.3. The polish round was therefore **elective**, not gate-forced, and that is exactly why it has never
been reviewed: the procedure's success path goes from a passing cycle to the AC gate, and this card
spent an extra round on minors before the narrowing interrupted it.

**Measured, not assumed: which of the polish round's fixes are still in the diff.** `d5da18ff` touched
four files; the narrowing merge resolved one of them (`tests/test_cli.py`) to main's version, so that
file's share of the fix round left the branch with it:

| finding | the polish fix | in this branch? |
|---|---|---|
| F-1 (the AC-7 bypass) | `_allowlist_prose` must find its subject in a `test_*` carrier | **gone** — `git grep _allowlist_prose HEAD` is empty; it is CARD-265's, by name |
| F-2 (`_COUNT_CLAIM`'s undeclared reach) | `MEASURED_COUNT_CLAIM_MISSES`, 5 families / 8 miss cases / 4 caught | **gone** — same file, same fold |
| F-3 (a name that lied) | the rename + `MEASURED_AST_SWEEP_MISSES` | **present** (`tests/test_web_server.py`) |
| F-4 (basename-keyed exemption) | `_web_relative` at all three sites | **present** (`tests/test_web_server.py`) |
| F-5 (fence blind spot) | **closed** rather than declared — `_classify` denies fence openers | **present** (`tests/test_guard_integrity.py`) |
| F-6, F-8 | `MEASURED_CLAIM_MISSES` 3rd entry; `MEASURED_TIMEOUT_CLAIM_MISSES` | **present** |
| F-9 (off-by-nine line citations) | the two numbers deleted, the fence cites by name | **present** (the docs page) |
| F-10 (extras restated in a docstring) | the restatement dropped; a control built from pyproject's keys | **present** |
| F-11 (the 575 figure) | `_repo_paths()` excludes `__pycache__`, with a control | **present** |
| F-7 | needed nothing | n/a |

So **nine of the eleven acted-on findings are in the tree for cycle 2 to read, and two are not** — and
the two that are not are the two whose subject was the folded file. Nothing was silently dropped: both
are named on CARD-265 (F-1's fix *is* `test_the_pin_has_to_live_in_a_test_and_not_in_a_helper` in that
card's list of nine), with the standing condition that each must be re-measured against whichever
`_ADAPTER_COUNT` bound that card settles on rather than adopted as written.

**[System contract] re-assembled fresh for this re-entry — projection 10, unchanged.** `system_rules.py
--card CARD-264 --root meta/architecture` returns exactly the same ten ids the card recorded at dispatch
(ADR-0038/R7, R8; ADR-0039/R1, R2, R3; CON-005, CON-009, CON-010, CON-011, CON-012), so the card's
section is **not** stale and needs no refresh. Checked rather than assumed, because the model did move
underneath this card while it waited: **ADR-0040** landed on main (book production at a
composite-capability rank) and the lens correctly does not project it here — this card's `Touches`
reaches no book path.

### [Build gate] **PASSED** at `99782837` — full suite, exit 0, and the delta reconciles to this card exactly

The gate owed since the narrowing. Run in the worktree under the board's **real**
`meta/kanban/.full-suite.lock` — not a redirected scratch path this time, because no sibling pipeline
is live and the lock's job here is to stop one appearing beside it. Lock written with an absolute
`worktree:` (CARD-255's guard refuses a relative one), released by the script and verified gone
afterwards; the worktree is clean.

| figure | value |
|---|---|
| pytest exit code | **0** |
| executed | **8919** |
| passed | **8892** |
| skipped | **27** |
| failed / error | **0 / 0** |
| `FAILED`/`ERROR` node lines in the output | **0** |

Counted from the progress rows (124 rows, character census), because this repo's `-q` output does not
reliably print a pass-count line — the same reading discipline the last three gates on this board used,
with the exit code as the authority either way. The 27 skips are the standing DB-mode skips (no
`nonogram_test` database), unchanged from CARD-262's and CARD-270's gates.

**Non-vacuity is structural here rather than asserted.** Against CARD-270's gate (8883 executed) this
is **+36**, and the per-file collection delta between `main` and this branch is:

```
tests/test_guard_integrity.py   131 -> 156   (+25)
tests/test_web_server.py        154 -> 165   (+11)
tests/test_timeout.py            17 ->  17   (  0)
tests/test_sourcing_image.py    133 -> 133   (  0)
                                             -----
                                              +36
```

**+36 and +36.** The gate's entire growth is this card's own additions and nothing else, which is a
stronger statement than "the suite is green": a green suite that gained tests it cannot account for is
how a vacuous gate reads from the outside. (The two files at +0 are the docstring corrections — one
symbol name each — so a zero there is the right answer, not a missing one.)

---

### [Review 2/3] Score: **5.5** — crit: 1, imp: 2. Report `meta/review/20261023T004419Z-CARD-264-cycle2.yml`

Baseline `10 − deductions`, the same as cycle 1 so the two are comparable: C-1 2.00, I-1 1.00,
I-2 0.50, eight minors 1.00 → **4.50 deducted**, no positive adjustment. Severity gate **closed**:
1 critical + 2 important, so the success path is shut regardless of score. Seven on-disk plants under a
manifest built **up front** (eight files, including the two `web/` sources that cycle 1's own plant-1a
incident missed), restored and verified three ways. The worktree is byte-identical to `HEAD` afterwards,
`git diff main...HEAD` unchanged at six files — including the six `src/` deadline lines the reviewer
mutated transiently and put back.

**[Review sync] 2 report(s) → `meta/review/`.** 52 KB for cycle 2 beside cycle 1's 63 KB, both in the
main repo now, so the evidence survives whatever happens to the worktree.

#### The polish round was good work, and that is a result in itself

Six of the eight findings it acted on verify as **genuinely resolved**, each re-derived by the reviewer
rather than taken from the card's word: F-3 (the name that lied — renamed, claim withdrawn, family
declared with a miss-side case), F-4 (**closed**, not merely declared — the identical plant that cycle 1
measured as *missed at exit 0* now reds on two arms at exit 1), F-5 (**closed rather than declared**,
exactly as the card claimed — a fence opener planted in the real `CLAUDE.md` reds naming
`CLAUDE.md:49`), F-9, F-10 and F-11 (whose fix is itself a recording-pass trap instance: the mutant
exits pytest 0 with 2 FAIL cells recorded, so a test-level reading would have published a real kill as a
survivor — the **sixth** independent measurement of that trap on this board).

#### What the unreviewed window actually cost is not in the polish commit at all

**C-1 is the narrowing merge's residue, not a fix defect.** The owner's fold took `tests/test_cli.py`
back to main's version — and left the docs page that *describes* its changes standing. The page now
carries a bold **verbatim quotation of a comment that does not exist**, a past-tense "all three now
state the rule" that is true of only one site, and a citation of `TestAdapterAllowlist_NoProseClaimsAStaleCount`,
a class with no occurrence anywhere in the branch. **main's version of that page was accurate**, so the
branch makes it strictly worse than what it replaced — and the harm is the exact one the page itself
documents: a reader following a pointer into a set of three under prose saying something else.

**I-1 is cycle 1's miss, measured where cycle 1 only read.** `CLAUDE.md:50`'s rewritten sentence cites
`tests/test_timeout.py` as pinning the mechanism's check sites. Deletion mutants over the six sites:
`propagate.py:983` **killed**; `propagate.py:1129`, `search.py:1180`, `:1259`, `:1418`, `:1728` **each
survived at exit 0**. So AC-6's remedy — *name the test in the same sentence* — shipped a **citation
where a control was wanted**, and the citation is the camouflage: this card exists to remove claims whose
controls cannot fail, and its own fix for the timeout clause is one. That is the sharpest finding of the
cycle and it is this card's subject turned on this card again, for the third time (cycle 1's F-1 was the
second).

#### The STALLED CHECK fires on these numbers, and I am overriding it — stated, not done quietly

Arithmetic, both conditions of the conjunction met: `score_improvement = 5.5 − 8.3 = −2.8`, under the
0.5 floor; `findings_reduction = 0 − 3 = −3`, not a decrease. A literal reading escalates here.

**I am not writing the literal `⚠ improvement stalled` marker, and the reason is that it would be false
data rather than a bent rule.** That string is a contract with `/kanban status` and
`forge:retrospective`, which read it as *the loop is not converging*. The check's premise is that cycles
N−1 and N reviewed the **same content**. These two did not:

- cycle 1 reviewed `d40e9d4a`; cycle 2 reviewed `d5da18ff` **plus a merge that removed content from the
  diff**. The unit of review changed between them in both directions.
- cycle 1 gated on **nothing** — 0 critical, 0 important, twelve minors — so `prev_findings_count = 0`
  is the floor, not a measurement of convergence. Against a floor of zero, *any* discovery trips
  condition (b) automatically. A check that fires on the first cycle to find anything is measuring
  discovery, not stall.

**An independent signal corroborates it rather than my say-so: the FAMILY REGRESSION CHECK does not
fire.** None of the three gating findings is attributable to the previous fix — C-1 is the **merge's**
residue (a slice change the owner made), I-1 is implementation-era text that cycle 1 reviewed and
**missed**, and I-2's missing control predates the F-4 fix that touched its neighbourhood.
`family_regression_streak = 0`. The two detectors disagree, and the one designed to catch *a loop
feeding on itself* says there is no loop.

So: into the fix round, with **cycle 3 of 3** as the certifying cycle. The budget is exactly right for
this shape — one fix round, one review to certify it — and it is also all there is, which the fix brief
says out loud.

#### [Adversarial] C-1 **CONFIRMED** — and the refutation attempt made the finding sharper in three ways

A fresh skeptic was given the claim and the code, not the reviewer's reasoning, and told to default to
refuted. It confirmed all three sub-claims mechanically and corrected the **mechanism** of one:

**1. The quotation is not fabricated — it is verbatim text from a version this branch reverted.**
`grep -rn "grows only by a deliberate edit" src tests` has no hits at HEAD, but
`git show d40e9d4a:tests/test_cli.py:743-746` reads character-for-character what the page quotes. So the
defect is *a quotation attributed to a file that no longer contains it* — which is a **better** statement
of this card's own thesis than a fabrication would have been: nobody invented anything, the text simply
stopped being true underneath the page, and no control noticed. That is the card's subject in one
artefact.

**2. The decisive fact is a hash, not a reading.** `git show main:tests/test_cli.py | shasum` and
`shasum tests/test_cli.py` are both `e30a6ac6…`, and `git diff main...HEAD -- tests/test_cli.py` is
empty. History confirms the asserted mechanism: `d40e9d4a` rewrote the comment and added the guard,
`4f7263fb` resolved the file back to main, the page was not reverted with it.

**3. A plain revert to main's text would reintroduce two defects — so "revert the hunk" is the wrong
fix.** main's page is *substantively true today* ("the guard's prose contradicts its own code" still
describes HEAD accurately), but its six line citations are **each off by one** (`:742`→743, `:743`→744,
`:740`→741, `:747`→748, `:904`→905, `:914`→915) and its lines 39-40 claim the stale count also appears at
`CLAUDE.md:45`, which is **false** — main's own `CLAUDE.md:42` states no count. The branch page already
fixed exactly those two things. So the fix must keep the branch's two genuine improvements (the line
numbers dropped, the CARD-261 note at `:54`) and restore only the **tense and the truth**.

**A fourth thing the skeptic found that neither cycle had: the stale count is unguarded, and the guard
that looks like it covers it does not.** `_ADAPTER_COUNT` (`tests/test_cli.py:1126`) is consumed by
`_adapter_counts` (`:1270-1307`), which scans **`CLAUDE.md`'s** text — `TestComponentMap_WhatTheClaudeMdReaderAbsorbs`,
named at `:1297` — not the prose around `_ADAPTERS`. And `len(_ADAPTERS)` appears nowhere at HEAD. So
`tests/test_cli.py:744`'s "closed at two names" has **no control at all**, which is a fact
**CARD-265** needs and did not have: it owns that file and that question, and its brief should say that
the count it settles has to be guarded *where the count is written*, not only where `CLAUDE.md` quotes it.

**Severity, adjusted down on the skeptic's argument and recorded rather than defended.** Critical →
**Important**: it is docs-only, no `src/` path is touched, `tests/test_cli.py` is byte-identical to main,
and `grep -rn "how-it-works" tests/*.py` has no hits — so **no gate in the suite catches this page at
all**, and no behaviour is affected. It still gates the card (Important blocks the success path exactly
as Critical does), so the flow does not change; what changes is that the card's record should not call
docs prose a correctness bug. It remains a genuine blocker for *this* card specifically, because a card
whose thesis is "a false claim in project prose gets acted on" cannot ship a page carrying three false
claims about the very guard it is about.

#### [Adversarial] dropped false positive: I-1 **REFUTED** — the measurement reproduces, the reading does not

This is the most useful thing the adversarial step has done on this board, because the finding was
mine-by-adoption and it was wrong for a reason worth keeping.

**The measurement reproduced exactly, and the skeptic extended it.** All six `check_deadline` call sites
confirmed independently by `grep -rn "check_deadline" src/` (one definition, one re-export, one import,
six call sites; `SolverTimeout` raised from exactly one place, `propagate.py:221`, and the only deadline
clock read at `:219`, so the set is complete). Single-site deletion: `propagate.py:983` **kills**, the
other five **each survive at exit 0**. Exactly as filed.

**But the finding graded the sentence against a referent the sentence does not use.** `CLAUDE.md:50`
says the solver *"checks it **as it propagates and branches**"* — that clause **is** the sentence's own
enumeration of its check sites: **two**, propagation-side and branch-side. It never claims six, never
claims per-call-site coverage, and never claims the suite reds on removing any individual
`check_deadline(...)` expression. Measured against what it *does* claim, every element is pinned:

| the sentence's claim | pinned? | evidence |
|---|---|---|
| propagation-side check site | **yes** | mutant M1 reds two tests, one asserting the check is *inside* the loop (`clock.reads >= 2`) |
| branch-side check site | **yes** | combined mutant C1 — **all four** `search.py` sites off — reds `test_the_search_checks_the_deadline_at_every_branch_node` with `assert 4 >= 6` at `:473` |
| one-deadline-per-request rule | **yes** | `test_every_attempt_in_one_request_shares_one_deadline:501`, `test_the_deadline_is_the_budget_measured_from_the_start_of_the_request:532` |

The combined mutants are the half the finding never ran, and they decide it: the branch-side checkpoint
is **pinned collectively**. Either `search.py:1180` or `:1418` alone satisfies it — so "satisfied by any
one of the remaining sites" is true in substance, and yet the *concept* is covered. **The internal
redundancy of a mechanism is not a false claim by the brief that names it.**

**Three independent things confirm the reading rather than my preference for it.** The cited test file
*explicitly disclaims* the granularity the finding demanded — its own section header reads *"where the
check happens (ADR-0011's **two** checkpoints)"* and its module docstring names **three** load-bearing
properties, which map one-to-one onto the three things `CLAUDE.md:50` says are pinned. The card's own
AC-6 bar is *"the clause is gone or the test that enforces it is named in the same sentence"* — the bar
is the naming, and the line meets it. And `CARD-264.md:296-300` anticipated this exact distinction when
the fix shipped: *"a named test is a claim the suite carries."* Reading "pinned by" as "every
implementation detail below it is individually mutation-covered" would make nearly every citation in
`CLAUDE.md` false, including the `test_solver_uniqueness.py` citation in the same sentence.

Dropped from the gating count. **This is what the adversarial step is for**: unrefuted, it would have
cost a fix round rewriting a sentence that is true, in the last cycle of the budget, and the rewrite
would have been a regression.

#### [Adversarial] one TRUE residue the skeptic found while refuting — and it is a control that cannot fail

`tests/test_timeout.py:479-485` — `test_the_branch_checkpoint_alone_stops_a_search_propagation_would_not`'s
docstring claims *"the only thing left that can raise is the branch-node check"*. **False under HEAD.**
`_blind_propagation` (`:424-451`) monkeypatches `search_module.propagate` only, while `search.py:694`
calls `propagate_overlap(board, ..., deadline)` with the real deadline — so `propagate.py:1129` raises
first. Demonstrated, not argued: under mutant C1, with **all four** branch-side sites neutralised, that
test **still passes**. So a test whose whole subject is "the branch checkpoint alone" passes for the
wrong reason and would survive the deletion of the thing it names. One unblinded path; the fix is one
line (stub `propagate_overlap` too).

**Not fixed here, and the reason is the budget rather than the scope.** `tests/test_timeout.py` *is* in
this card's `Touches`, and this is precisely the card's thesis — a claim whose control cannot fail — so
there is a real argument for absorbing it. Against: it is pre-existing, outside every hunk in the diff,
and **cycle 3 of 3 is the only cycle left**. Widening a card into its last certifying cycle is how a
card ships its final edit uncertified, which is the wave-48 lesson this board keeps re-learning.
Carded forward instead.

#### [Process] I dispatched two mutating skeptics into ONE worktree — my error, recorded

The I-1 skeptic reported, unprompted, that another agent was concurrently mutating
`tests/test_web_server.py` and `src/nonogram/web/handler.py` in the same tree, so its `git status
--porcelain` could not come back clean. That is the I-2 skeptic, and the collision is mine: the
adversarial step's brief gives each skeptic "the finding + the file scope", and I gave both the same
worktree without considering that a *measuring* skeptic mutates.

**No contamination, argued rather than assumed, in both directions.** I-1 mutated only
`solver/propagate.py` and `solver/search.py` and measured `tests/test_timeout.py`, which exercises the
solver; I-2 mutated `tests/test_web_server.py` and a comment token in `web/handler.py` and measures the
web guard, which sweeps `web/` sources only. I-1's inserted `pass  # MUTANT:` lines define no
`validate_*`/`parse_*` function, so I-2's derived set is unchanged by them; I-2's comment plant changes
no behaviour the solver reaches. Each skeptic verified restoration of **its own** files by
`shasum -a 256 -c` and `diff -q` (I-1: both files OK, `git diff --stat HEAD` empty, no `MUTANT` marker
anywhere in `src/` or `tests/`). The worktree must still be confirmed byte-identical to `HEAD` once I-2
finishes — that check is owed and is not optional, because "each verified its own files" is not the
same statement as "the tree is clean".

**Standing rule for this board, learned the cheap way:** a skeptic that measures by mutation needs its
own worktree, or the skeptics run serially. Two agents mutating one tree is how the concurrent-session
collision of 2026-10-22 started, and this time it was self-inflicted.

#### [Adversarial] I-2 **PARTIAL** — primary refuted (the arm is redundant, not unguarded), secondary confirmed

**Primary REFUTED, and the refutation is an exhaustive partition rather than a counter-example.** The
mutant reproduces — `if True or (where, token) in MEASURED_PROSE_CITATIONS:` on one line, `wc -l` 3360
before and after, and nothing kills it on a clean tree (whole file 165 passed, exit 0). But the finding
read "no test kills the mutant" as "the arm's detection is unguarded", and those are different
statements. Partition every `token in source` event:

| the violation appears… | caught by | measured |
|---|---|---|
| in **code** | the untouched AST arm's `assert hits == []` at `:2215` | plant (d): `_CARD264_PROBE = "validate_density"` in `web/handler.py` → **exit 1** with the arm off |
| in **prose only** | the exemption equality at `:2299`, computed by an independent comprehension that never routes through the mutated branch | plant (b): the finding's **own** demonstration case, a bare `parse_tier` comment → **exit 1** with the arm off |

Exhaustive, no residue — and the equality additionally reds if `_WEB_SOURCES` empties and errors if any
web source fails `ast.parse`. So **no violation the arm would catch goes unreported when the arm is
off**: the arm carries *zero unique detection*, G-2 is not at risk, and nothing becomes unfalsifiable.
A control for it would be a test for an arm that provably catches nothing of its own. Eleven other
candidate controls were checked and correctly ruled out one by one, including the four that *look* like
they cover it (`test_that_guard_passes_on_the_real_token_set` inherits the mutation because it calls the
guard; two empty-collection cases match messages raised **before** the loop; the floor pin is
indifferent to how the set is consumed).

Dropped from the gating count. The honest residue is the skeptic's own suggestion and it is one line: a
comment at `:2216` recording that the arm's two halves are held by `:2215` and `:2299`, so the next
reader does not re-derive this.

**Secondary CONFIRMED, at Minor.** `tests/test_web_server.py:2341`'s `assert "validate_density" in
planted` has both operands bound to a test-authored literal concatenation at `:2332-2336`. Its truth
value is fixed entirely by text in the test body — it reads no production code, no module global and no
guard path — so it cannot fail unless someone edits the fixture string, while the test's **name**
(`..._still_catches_a_real_reference_to_the_old_live_members`) and docstring (*"Both arms fire … the AST
one and the substring one"*) assert that the substring arm fires. The test's other two assertions are
real (`:2338-2340` exercises the AST arm behaviourally, `:2342` reads the exemption table), so it is a
valid AST-arm control carrying one decorative line and half an unsupported docstring.

#### The recount, and the one pattern this card should leave behind

**Gating after verification: 0 critical, 1 important.** C-1 (CONFIRMED, downgraded Critical→Important),
I-1 dropped (refuted), I-2 primary dropped (refuted) with its secondary surviving at Minor. The severity
gate stays closed on the one Important, so the fix round runs — but it runs on **one** gating finding
plus nine narrowings rather than on three, and two of the three findings that would have driven it were
false. That is the adversarial step paying for itself twice in one cycle, in the last cycle of a budget.

**The pattern worth carrying off this card, stated once:** *this card's own new controls describe
themselves as proving more than their bodies prove.* Cycle 1's F-3 was an instance
(`test_a_string_built_reference_is_caught_too` tested a whole literal); I-2's secondary is a second,
independent one (`...still_catches_a_real_reference...` claims both arms fire, and the substring half is
a literal-vs-literal line). Neither is attributable to the previous fix, so the board's family-regression
detector correctly reads **streak 0** and this is **not** an escalation — but one sentence covers both,
and it is the same sentence as the card's subject. A card raised to remove claims whose controls cannot
fail wrote two controls whose *names* claim more than they prove. If anything from this card belongs in
the board's standing rules, it is that a control's name and docstring are claims too, and the thing that
checks them is reading the body.

---

## [One-way sync] Fix round 2's own notes, pulled from the worktree


## Worktree notes -- fix round 2 (`forge:fix`, auto), 2026-10-23, on review cycle 2

Narrowing round, as briefed: ten items, no new mechanism. Scope held to the card's six files; no `src/`
path touched (`git diff --name-only $(git merge-base HEAD main)` lists `CLAUDE.md`, the adapters doc and
four `tests/` files, **zero** `src/` paths -- G-6 by construction). `tests/test_cli.py` left alone and
re-verified byte-identical to `main` (`shasum -a 256` = `f0a9dc3c24b62c0d…` on both sides; the brief's
`e30a6ac6…` was a different digest form, the identity is what matters and it holds). `CLAUDE.md` was
**not** edited this round -- cycle 2's I-1 was refuted and the file still carries exactly three
single-line hunks at `:46`/`:48`/`:50` (`git diff --unified=0` → three `@@ -N +N @@` headers, G-1).

### C-1 + M-7 -- the adapters page, put back into the present tense

Every line number re-derived in this worktree at HEAD before writing anything, not copied from the
brief:

| claim | cited on the page before | **re-derived** |
| --- | --- | --- |
| the qualified "exactly two adapters" sentence | `src/nonogram/__init__.py:40` | `:71`-`:73` (and the unqualified statement at `:78`); `:40` is inside the module-list block |
| the `_ADAPTERS` comment | by name (this branch had already dropped the number) | `tests/test_cli.py:743`-`:747`, `_ADAPTERS` itself at `:748` |
| the test that pins the set | by name | `def` at `:905`, its docstring's first line at `:906` |
| the web adapter's copy of the claim | by name | `src/nonogram/web/__init__.py:21`, still present |

Three false claims removed, one stale figure removed:

* **(a)** the bold verbatim quotation was text from `d40e9d4a`'s version of `tests/test_cli.py`, which
  the owner's fold reverted. `grep -rn "grows only by a deliberate edit" src tests` → **0 hits** at HEAD.
  Replaced with the comment the file actually carries, quoted whole -- including its stale "closed at
  two names", because that stale count *is* the subject of the block underneath and eliding it with an
  ellipsis would have been a second kind of dishonest framing.
* **(b)** the past tense ("contradicted … until CARD-264", "All three now state the *rule*") is now the
  present tense, because the contradiction is live at `:744` / `:905` / `:906`. The page now says the
  three sites in that file are **CARD-265's** subject (owner decision 2026-10-22) and that the count
  there is **unguarded**, which is the measured fact: `_ADAPTER_COUNT` (`tests/test_cli.py:1126`) is
  consumed by `_adapter_counts` (`:1270`), whose body reads `CLAUDE.md`'s text and nothing else.
* **(c)** the sentence citing `TestAdapterAllowlist_NoProseClaimsAStaleCount` and `len(_ADAPTERS)` is
  deleted. `grep -rn "NoProseClaims" src tests` → **0 hits**; `grep -rn "len(_ADAPTERS)" src tests` →
  **0 hits**.
* **M-7**: `src/nonogram/__init__.py:40` → cited by name ("module docstring"), consistent with the rest
  of the page.

Not done by reverting to `main`'s hunk, deliberately: `main`'s six line citations are each off by one
(743/744/741/748/905/915 against its 742/743/740/747/904/914) and its claim that the stale count also
sits at `CLAUDE.md:45` is false -- `main`'s own `CLAUDE.md:42` states no count. This branch's two real
improvements (no `:NNN` into another file; CARD-261 named as what removed `CLAUDE.md`'s copy) are kept,
and the verified-open `web/__init__.py` site is kept flagged open.

### I-2 secondary -- which shape, and why

**Chose: delete the decorative assertion and narrow the docstring to the AST arm.** The brief offered
the alternative of a fabricated source pair that genuinely exercises the substring arm, and that
alternative is incoherent with the brief's own primary follow-up: the substring arm carries **zero
unique detection**, so a control for it would pin a reach no other arm has -- a new unfalsifiable arm on
a card about unfalsifiable arms. `assert "validate_density" in planted` is gone; the docstring now
claims only what its body measures, and records what it used to claim and why that was wrong.

### I-2 primary follow-up -- the partition, re-measured here

Recorded as a comment above the substring loop in
`test_the_web_package_imports_no_domain_validator`. Re-derived rather than taken on trust, in memory,
against the real `_WEB_SOURCES` (no on-disk plant, so no `src/` file was ever mutated):

* real `prose_only` = `[('submission.py', 'validate_extent')]` = `MEASURED_PROSE_CITATIONS` -- the
  equality holds as shipped;
* a **prose**-shaped violation (the token in a docstring, in a non-exempted file): AST arm returns `[]`,
  `prose_only` grows by `('handler.py', 'validate_density')`, and the equality in
  `test_the_prose_exemption_is_exactly_the_sites_that_exist_today` **breaks**. That comprehension
  re-derives prose mentions from each source directly and does not route through the substring loop, so
  disabling the loop does not weaken it;
* a **code**-shaped violation: AST arm returns `['handler.py:1 imports validate_density']`, so it reds
  one line above the loop.

The arm is kept (G-2: nothing the guard caught is given up) and deliberately left without a control.

### The five declared-miss narrowings, before → after

Every "after" below is a measurement run in this worktree, not a figure inherited from a docstring.

| id | declaration | measured before | **after** |
| --- | --- | --- | --- |
| **M-1** | `MEASURED_TIMEOUT_CLAIM_MISSES[1]` | entry said an em-dash *breaks* the split. Measured against `_timeout_sentences`: em-dash-joined = **1** sentence (does **not** break); colon = 1; comma = 1; full stop = **2**; **semicolon = 2** (unmentioned by the entry) | entry names colon, comma **and em-dash** as non-breaking, and full stop **and semicolon** as breaking. The em-dash body moved from the caught list to the missed list -- it did read as 2 sentences, but on the full stop `cited` already ends with, which is why it looked like evidence. A semicolon body took its place on the caught side |
| **M-2** | `MEASURED_AST_SWEEP_MISSES[2]` | declared "a lookup table, an environment variable or a request" as a miss. Measured: `{"extent": "validate_extent"}` → `["x.py:1 writes 'validate_extent' in a string literal"]` -- **caught**, by both arms. `os.environ[...]` → `[]`; `posted["validator"]` → `[]` | narrowed to "a name supplied from outside the source -- an environment variable or a request field -- which no contiguous run of the file spells". New case holds the lookup table on the **caught** side and the two external forms on the **miss** side, and denies the re-widening (`assert "lookup table" not in declared`) |
| **M-3** | `MEASURED_CLAIM_MISSES` | three entries, two demonstrated executably, **none** of them read by any assertion -- which is why `F6-DECL-GUTTED` survived | each case now reads a fragment of its own entry. Entry `[1]` ("a lead-in not in `GUARDED_PARAGRAPHS`") had no case at all and gets one, shown both ways round (`_guarded_paragraphs` finds nothing under `**Test style.**`, finds the paragraph under a guarded lead-in) |
| **M-4** | `_dependency_claim_defects` | no declared reach. Measured evasions: un-backticked extras ("the dev, admin and db extras sit outside it") → `[]`; a **denial** ("`pyproject.toml` no longer declares Pillow or NumPy at runtime") → `[]`. Measured **non**-evasion: members un-backticked ("flask, gunicorn, reportlab, werkzeug are admin-only") → **4** defects | `MEASURED_DEPENDENCY_CLAIM_MISSES`, two entries, both held on the miss side by a new `test_the_rule_names_what_it_cannot_see` -- which also holds the member restatement on the **caught** side, generically (it picks the first extra with non-runtime members from pyproject's own tables, so a fourth extra needs no edit here) and keyed on the entries' own text. The backtick-independence of the member arm is **not** declared away |
| **M-6** | the dependency class's docstring | "pyproject.toml carries **three** extras" -- re-derived by `tomllib` as `['admin', 'db', 'dev']`, accurate today and rottable | the number is gone, not controlled (G-3: point at the authority). `test_the_restatement_rule_covers_every_extra_pyproject_declares` already builds from those keys, so no second reader was added |

`M-5`: `_src_symbols`' `ast.parse` now passes `filename=str(path)`. The ten SyntaxWarnings a
`TestClaudeMd` selection raises print
`src/nonogram/sourcing/templates/dog_in_house.py:6` instead of `<unknown>:6`, matching the sibling
helper `tests/test_web_server.py::_domain_validator_names`.

`M-8`: prose only -- "…was ``validate_size`` until CARD-264; that name has no definition anywhere in
``src/`` — ADR-0022/R1 …". The relative clause no longer attaches to the card id. The surrounding
superseded-50x50 reasoning is untouched.

### Mutants -- the controls were measured, not asserted

`tests/kill_matrix.py` (the committed instrument; nothing else written), line-count-preserving,
**ANY-RED**, SHIPPED re-run between mutants, **both passes**. Domains stated per the instrument's own
rule: the denominator is the target file's `ast.Assert` node count, carried separately from the
collected-test count.

`tests/test_guard_integrity.py` -- **149** assertion nodes; selection of **3** tests, **29** arms
reached; SHIPPED **0 FAIL of 29 reached** in both passes:

| mutant | recording | re-raising | FAIL cell(s) |
| --- | --- | --- | --- |
| `F6-DECL-GUTTED` (gut `MEASURED_CLAIM_MISSES[2]`'s middle line) | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3349` `assert "resolves in dir(builtins)" in MEASURED_CLAIM_MISSES[2]` |
| `TIMEOUT-MISS-2-GUTTED` | exit 0, **2 FAIL** | exit 1, **1 FAIL** (short-circuit) | `:3776`, `:3777` -- the two joiner halves |
| `DEP-MISS-1-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3640` `assert "without backticks" in MEASURED_DEPENDENCY_CLAIM_MISSES[0]` |
| `DEP-MISS-2-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3641` |

`tests/test_web_server.py` -- **251** assertion nodes; selection of **2** tests, **14** arms reached;
SHIPPED **0 FAIL of 14 reached** in both passes:

| mutant | recording | re-raising | FAIL cell |
| --- | --- | --- | --- |
| `AST-MISS-3-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:2466` `assert "an environment variable or a request field" in declared` |

Every mutant produced **≥1 FAIL cell** in both passes -- so none of them is the "absent `old` writes
nothing" shape. `F6-DECL-GUTTED` was the mutant cycle 2 measured as **surviving**; it is now killed, and
`AST-MISS-3-GUTTED` likewise. The recording pass's exit 0 with FAIL cells recorded is exactly the trap
the brief warned has caught this card six times -- hence both passes, read per cell.

### Gates run (scoped, never the full suite)

`NONOGRAM_FULL_SUITE_LOCK=/tmp/card264-fix2.lock` was exported for every pytest, script and mutant run,
so the board's own `meta/kanban/.full-suite.lock` was never read, written or created.

* `tests/test_guard_integrity.py tests/test_web_server.py tests/test_sourcing_image.py` -- **all green**,
  no failures.
* `tests/test_timeout.py` -- collection only (**17** collected, exit 0): this round's change there is one
  docstring sentence.
* **G-2**: `TestWebServer_BindsLoopbackOnlyByDefault` (CON-009) and CON-010's four arms
  (`test_the_corpora_are_large_and_cover_every_declared_signal`,
  `test_every_cross_origin_or_foreign_authority_request_is_refused`,
  `test_every_same_origin_or_metadata_free_request_is_served`,
  `test_the_accepted_fetch_metadata_is_the_two_spec_values`) -- **10 passed, exit 0**. CON-010 is
  module-level `def`s, not a class: the id `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`
  is the logical requirement id (stated in the comment at `tests/test_web_server.py:1950`), and
  `PropertyTest_` is not in pytest's `python_classes`, so selecting it as a class runs nothing. Worth
  knowing for any future brief that names it as a class.
* `_WEB_SOURCES`' non-empty assertion and `_DOMAIN_VALIDATORS`' are untouched; nothing the guard caught
  was given up.
* **G-7**: no durations measured or reported anywhere in this round.

### Flaky, pre-existing, and *not* this round's

`TestWebServer_BindsLoopbackOnlyByDefault::test_the_port_stays_free_on_every_other_interface` failed
**once** mid-round (`_port_is_free_on('192.168.0.109', 59110)` returned `False` where the test wants
`True`), then passed on three consecutive isolated re-runs and in the combined CON-009+CON-010 run. It
is at `tests/test_web_server.py:555`, inside no hunk this card touches, and depends on the host's
network and on whether another process on this machine holds the ephemeral port the fixture drew. It is
host-dependent flake, not a regression -- but it is a **real** flake on a CON-009 control, and it
deserves its own card rather than a shrug.

### Skipped, with the measurement

* **I-1** (`CLAUDE.md:50`) -- refuted in cycle 2 and **not touched**, per the brief. The sentence's own
  enumeration is two checkpoints and both are pinned.
* `tests/test_timeout.py:479`-`:485`'s `_blind_propagation` defect -- out of scope by the brief, being
  carded separately. `tests/test_timeout.py` was edited this round for M-8 only, in the module docstring;
  those lines are untouched.
* The three `U+2022` codepoints in `src/nonogram/admin/pdf_generator.py` are **not** a G-6 violation:
  they are a named, controlled exemption (`DINGBAT_EXEMPT_MODULES` in
  `tests/test_book_difficulty_dots.py`, whose reason is itself asserted). Checked because the brief
  asked for structural verification rather than assumption; the structural check that settles G-6 for
  this card is that the diff contains no `src/` path at all.

---

### [Correction, measured by the orchestrator] This card twice claimed to have run CON-010, and twice ran **nothing**

The fix round flagged a selection detail in passing. It is worse than a detail, and it falsifies two of
this card's own evidence lines, so it is recorded here rather than left in a hand-back.

**What this card's earlier rounds ran**, verbatim from the polish round's own table at line 938:
*"CON-009 + CON-010 (`TestWebServer_BindsLoopbackOnlyByDefault`,
`PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`) | 6 collected | exit 0 |
6 passed, 159 deselected"*. The implementation round reported the same shape.

**Measured now, on the same file:**

| selection | collects |
|---|---|
| `-k 'TestWebServer_BindsLoopbackOnlyByDefault or PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest'` | **6** |
| `-k 'TestWebServer_BindsLoopbackOnlyByDefault'` **alone** | **6** — the same six |
| `-k 'PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest'` | **0** |

So the compound selection collected CON-009's six tests and **nothing of CON-010's**. The `or` arm
contributed zero, exit 0 either way, and the line "CON-009 + CON-010 … 6 passed" is **false about
CON-010**: it was never executed. Both rounds reported a constraint as exercised that no process ever
touched.

**The cause is documented in the code, which is what makes it a trap rather than a typo.**
`PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest` is **not a test symbol** — it
occurs three times in `tests/test_web_server.py` and all three are prose: the module docstring's EC-004
line (`:10`), a docstring reference (`:1346`), and the section comment (`:1950`). The comment at `:1959`
says why: *"Written as module-level functions rather than as a class, which is this project's convention
for a property."* The id is the **requirement's declared check name**, and the project deliberately does
not spell it as a class. So the id is correct everywhere it appears as a contract reference — and selects
nothing everywhere it is used as a `-k` pattern.

**The real tests, and a selection that reaches them:** `test_the_corpora_are_large_and_cover_every_declared_signal`,
`test_every_cross_origin_or_foreign_authority_request_is_refused`,
`test_every_same_origin_or_metadata_free_request_is_served`. With CON-009 that is **8** collected, not 6
— which is also why the fix round's own run reported 10 for a slightly wider selection and the earlier
rounds reported 6: the discrepancy was visible in the numbers all along and nobody subtracted them.

**Blast radius, measured rather than feared: this card only.** `grep` across `meta/kanban/cards/` finds
the id in many cards, but every other occurrence is a `## System contract` projection line or an AC/EC
evidence reference — correct usage, since that is the rule's declared check id. The only place it is used
as a **pytest selector** is this card's line 938.

**Why it matters beyond the correction.** G-2 exists to keep CON-009 and CON-010 intact, and CON-010 is
the cross-origin refusal — a security boundary. Two rounds of this card asserted that boundary was
re-run and green on the strength of a selector that matched nothing, which is the vacuous-pass shape this
very card was raised to remove, one level up: **not a claim without a control, but a control without an
execution.** The board's own gate has a VACUOUS-GATE CHECK for exactly this (exit 0 with zero tests is
"an empty room, not a pass"); a card's hand-written evidence selection has no such check. Filed to the
backlog as its own shape.

**CON-010 is now actually run.** The fix round's run of the corrected selection: **10 passed, exit 0**,
and the post-fix full-suite gate executes all three functions by construction.

### [Build gate] **PASSED** at `e26e5473` (post-fix-2) — exit 0, and the +2 reconciles to the fix round exactly

| figure | value |
|---|---|
| pytest exit code | **0** |
| executed | **8921** |
| passed | **8894** |
| skipped | **27** |
| failed / error | **0 / 0** |

Board lock taken and released, verified gone. **+2 against this card's own first gate (8919)**, and the
per-file collection delta from `99782837` to `e26e5473` is `test_guard_integrity.py` 156→157 and
`test_web_server.py` 165→166. The fix round added exactly **two** new test functions —
`test_a_name_supplied_from_outside_the_source_is_a_measured_miss` (M-2's caught/miss case) and
`test_the_rule_names_what_it_cannot_see` in `TestClaudeMd_TheDependencyClaimMatchesPyproject` (M-4's
declared reach). **+2 and +2.** The round's other seven fixes changed assertions, declarations and prose
rather than adding tests, which is what a narrowing round should look like from the outside.

Cumulative against main: **8921 − 8883 = +38**, all of it this card's.

### [Review 3/3] dispatched as a **FULL** review, not in confirmation mode — and the reason is this card's history

Confirmation mode is mechanically available (cycle > 1; cycle 2 parsed cleanly; every commit since the
reviewed state is a fix commit against named findings; scope IN_SCOPE; the fix round addresses all three
of cycle 2's gating findings, two by refutation). I am declining it, deliberately:

1. **This is the only certification this card will get.** Cycle 3 of 3 is the last; there is no cycle
   after it to catch what it carries forward. A differential review legitimately *carries verdicts
   forward* for scope that the fix delta does not touch — and carrying a verdict forward is exactly the
   move whose failure mode this card exists to remove. On this card, of all cards, a verdict nobody
   re-derived is the wrong kind of saving.
2. **Both prior cycles missed real defects in this same diff**, which is the empirical case against
   trusting their verdicts as a floor. Cycle 1 passed at 8.3 and missed everything cycle 2 found; cycle 2
   found those and missed the CON-010 selector defect — a **security** control reported as run, twice,
   while the selector matched nothing — which neither reviewer caught and which only surfaced because a
   fix agent happened to look at a collection count.
3. The wall-clock confirmation mode saves is the cheapest thing on this card's balance sheet. Two of
   cycle 2's three gating findings were false and cost a verification round each; one real finding came
   from a docs page no gate in the suite reads. Spending a full review here is the correct trade.

Stated so the next reader knows it was a choice with a reason, not an omission.

---

### [Review 3/3] Score: **9.6 — PASSES** (0 critical, 0 important). Report `meta/review/20261023T015517Z-CARD-264-cycle3.yml`

Baseline `10 − deductions`, the same baseline cycles 1 and 2 declared, so all three are comparable:
four minors at 0.15 / 0.10 / 0.10 / 0.05 → **0.40 deducted**, no positive adjustment. **Nothing carried
from cycle 1 or 2** — every verdict re-derived in this cycle, which is what the full-review decision
bought.

**Severity gate OPEN:** score 9.6 ≥ 8 and findings_count 0. The score trajectory across the card is
8.3 → 5.5 → 9.6, and the dip is discovery rather than regression (see the stalled-check note above).

#### The round's most load-bearing claim verified independently: both previously-surviving mutants are dead

| mutant | FAIL cell | recording pass | re-raising pass |
|---|---|---|---|
| `F6-DECL-GUTTED` | `tests/test_guard_integrity.py:3349` | exit **0**, 1 FAIL of 64 reached | exit 1, 1 FAIL |
| `AST-MISS-3-GUTTED` | `tests/test_web_server.py:2466` | exit **0**, 1 FAIL of 34 reached | exit 1, 1 FAIL |

Both are **recording-pass-trap instances** — pytest exit 0 *with* a FAIL cell — which would have
published two real kills as survivors on a test-level reading. That is the **eighth** instance of that
trap on this card. 11 mutants fired in total, **11 killed, 0 survived**, every one with ≥1 FAIL cell (so
none is the absent-`old` shape), line-count preserving, ANY-RED over both passes, SHIPPED re-run between
mutants and FAIL-free each time. Domains stated and never conflated: `tests/test_guard_integrity.py`
**149** `ast.Assert` nodes / 64 reached / 19 collected tests; `tests/test_web_server.py` **251** / 34 / 11.

**The instrument refused one selection before any reading** (a method named as a module-level function →
pytest exit 4 → `UnmeasuredRun`), and the reviewer **recorded the refusal rather than quietly retrying**.
That is the README's own gate doing its job, and reporting it is the difference between a bound and a
silence.

#### Cycle 2's two ✗ contract verdicts re-judged to ✓, on re-measurement rather than on the fix's word

**System contract: 10 rules checked, 8 ✓ holds, 2 ⚠ unchecked (typed: `no_eligible_fact` — CON-005 and
CON-012), 0 ✗ violated.** ADR-0039/R1 and R3 were cycle 2's violations; both flip, and the flips are the
ones I sent independent skeptics after rather than accepting (see the spot-check below).

- **ADR-0039/R3** — all five narrowings re-measured independently, each no wider *and no narrower* than
  measured, each with a committed case the reviewer **made red**. M-1's declaration was checked by an
  **exhaustive single-character sweep** over `string.punctuation` plus U+2014/2013/2026: the breaking set
  is exactly `{'.', ';'}`, which is precisely what the entry now names. That is a stronger check than the
  fix round's own.
- **ADR-0039/R2** — every set re-derived in-process from its authority; default-deny measured two ways
  (`DERIVATION-RETURNS-ONE-NAME-ONLY` reds 6 cells including the floor pin at `:2302`;
  `SET-CARRIES-A-HAND-ADDED-DEAD-MEMBER` reds 4).
- **ADR-0038/R8** — the card's zero-skip claim verified mechanically: a grep of every added line for
  `pytest.skip|mark.skip|skipif|importorskip|unittest.skip|xfail` returns nothing.

**The reviewer also attacked a claim nobody had raised** — that
`test_every_name_in_the_set_is_defined_in_the_package` cannot fail, because the set is derived from the
same walk it consults — and **refuted it**: a hand-added dead member reds it on 4 cells, which is exactly
how `validate_size` got there in the first place. No finding filed. A reviewer that tries to break a
control and *fails* has produced evidence, not nothing.

#### All ACs pass, and AC-6's shape is stated rather than implied

AC-1 ✓ · AC-2 ✓ (both states on disk, the line **computed**) · AC-3 ✓ (the "do not restate" shape
shipped **and the class docstring says so**) · AC-4 ✓ (stronger than worded — a dead member *and* a
shrunken derivation both red) · AC-5 ✓ (both halves, both states, on disk) · AC-6 ✓ (objective 2's
decision made and stated: *says what the code guarantees and names the test that pins it*) ·
AC-7 **withdrawn, not scored**. Eight on-disk plants plus a baseline, all red, tree restored and verified
three ways with the manifest built up front.

#### Two corrections to my own brief, reported rather than reconciled

1. **CON-009 + CON-010 collects 9, not 8.** 6 + 3. My arithmetic was off by one, in a brief whose whole
   purpose was to stop a selection from under-collecting. Recorded here rather than quietly fixed.
2. **The CON-010 trap reproduced exactly**, with the detail I had not measured: selecting by the declared
   check name collects zero **and pytest exits 5**. An exit code that says "nothing was collected" was
   available all along, and two rounds of this card read exit 0 from a *compound* selection that collected
   CON-009's six instead.

#### Guardrails: G-1..G-7 all PASS, and two were verified two independent ways

G-1 — `git diff -U0 d90753df..HEAD -- CLAUDE.md` is exactly three single-line hunks at `@@ -46 +46 @@`,
`@@ -48 +48 @@`, `@@ -50 +50 @@`; CARD-261's layout paragraph byte-identical on both sides by sha256
(`3e767042…`); `grep -c COMP- CLAUDE.md` = 0. G-6 — structurally (no `src/` path in the diff, so the rule
holds by construction) **and** by an independent per-codepoint sweep of all six files, 0 hits each; the
`DINGBAT_EXEMPT_MODULES` exemption was deliberately **not** relied on. G-2 — both non-empty assertions
present (`:2222`, `:2223`), and nothing given up, shown on the real tree rather than argued.

#### [8h spot-check] CON-009 ✓ / CON-010 ✓ — **reproduced**, every figure, by an independent read-only skeptic

Given the two verdict lines verbatim and the worktree, told to reproduce every cited element and default
to `not_reproduced`, with the tree **read-only** to it. It reproduced all six selections exactly —
CON-009 6 collected / 160 deselected / exit 0 / **6 passed**; the declared-check-name selection **0
collected, exit 5**; the three functions 3 collected / exit 0 / 3 passed; combined **9 / exit 0 / 9
passed** — and confirmed it modified nothing (`git status --porcelain` showing only the three `meta/`
entries that predated it, run with `-p no:cacheprovider` so not even a cache was written).

**The CON-010 trap is sharper than I had it, in two directions.** It is a **documented project
convention**, not a broken reference: `meta/architecture/trace.yml:915-916` records the ref as resolving
to *"the EC-004 section of tests/test_web_server.py"* — a file region, not a selector — and
`tests/test_web_server.py:1963-1965` states the module-level-functions choice deliberately, naming the
same convention at `tests/test_web_submission.py:6`. An `ast` walk of every `*.py` in the repo for a
`ClassDef`/`FunctionDef` of that name, or any `Name`/`Attribute` referencing it, returns **zero**; of 148
textual occurrences across 123 files, exactly **three** are in Python and all three are prose
(`:10` the EC→check index, `:1346` a cross-reference, `:1950` a section banner).

And the second direction, which **bounds the fix** rather than the defect: pytest's default
`python_classes = Test*` is **not overridden anywhere** (`pyproject.toml:88-90` sets only `testpaths`,
`addopts`, `pythonpath`), so even a class *named* `PropertyTest_…` would collect **nothing, silently**.
The obvious repair reproduces the defect. That is now recorded as the second and stronger reason on
CARD-279's G-3 and in the backlog item.

**CON-010 is a genuine property, counted independently rather than taken from the file.** The skeptic
rebuilt both corpora in-process: **294** refused rows (294 distinct ids, both GET and POST, generated as
a *product* over authorities × fetch-sites × schemes × layouts × orderings) against the asserted floor of
200, and **58** served rows against a floor of 40. "Never routed to a handler" is checked by its
**consequence** — the POST rows carry a real `mode=library` submission with two export formats, and the
sweep asserts `tmp_path` is empty afterwards — not merely by a status code. Two qualifications reported
rather than smoothed: the floors sit **~32%** below the actual sizes, so a builder regression could drop
a whole group and still clear them; and **32** of the 294 rows are `Host`-allowlist rows answered by a
different check, which the code discloses at `:1646-1649` rather than hiding.

**G-2 confirmed from the other side, by line ranges rather than by argument.** The diff's four new-side
hunks are 95-213, 271-323, 2204-2487 and 2660-2688; CON-009's class is 507-607 and CON-010's arms and
helpers are 1487-2070. **Intersection: none.** The diff removes exactly four lines, three of them inside
the *domain-validation* guard, and the fourth is `_WEB_SOURCES`, replaced by an extract-variable refactor
with identical semantics (same root, same `rglob("*.py")`, same `sorted`) — with CON-009's consuming test
body **byte-identical to main** and its own non-vacuity assertion intact.

#### The spot-check's independent question refuted a hypothesis of mine, and the replacement is better

I had written on CARD-279 that CON-009's probe might **pass by probing nothing** on a host with no
non-loopback address. **It does not.** `_non_loopback_address()` (`:453-469`) returns `None` on `OSError`
or a `127.`-prefixed result, and both consumers `pytest.skip("host has no non-loopback IPv4 address to
probe")` (`:521-532`, `:534-555`) — verified by driving the helper with four constructed conditions and
both tests with it forced to `None`. ADR-0038/R8 is satisfied: the gap is a loud, named skip. **CARD-279's
AC-3 is withdrawn** and replaced on that card.

What the measurement found instead is worth more than what it refuted: **a green-with-skips run is
indistinguishable from a fully-verified one by every figure this board records except the passed count.**
On a loopback-only host the CON-009 selection still collects **6** and exits **0**, reporting
`4 passed, 2 skipped`. This card has already been bitten once in the mirror-image direction — a `-k` that
matched nothing, exit 0 inside a compound selection, a security constraint reported as re-run twice. Same
defect class, opposite side: **exit code plus collected count does not establish that a constraint was
verified; the passed count does.** The verdict line under test cites "6 passed", so it is sound — but the
evidence idiom this board writes ("N collected, exit 0") is not, and that is now on CARD-279.

#### [8h spot-check] ✗ **ADR-0039/R3 — `✓ holds` NOT fully reproduced.** Two of the five narrowings fail the verdict's universal claim

The spot-check exists because the `✓` half of a contract gates a merge as hard as the `✗` half, and
until this step nothing had checked it. Here it earned its keep. A skeptic in its own worktree, given
the rule and the verdict line verbatim and told to default to `not_reproduced`, re-derived all three of
R3's clauses per declared-miss entry — and **clause 3 ("its own failing control") reproduces for all
five**, as do both exemption equalities, and clauses 1 and 2 for M-1 and M-2. What does **not** reproduce
is the verdict's universal sentence, *"each is no wider and no narrower than measured"*:

**1. `MEASURED_CLAIM_MISSES[2]` (`tests/test_guard_integrity.py:2921-2923`) is WIDER than measured.** The
entry declares as a miss *"a span that parses and whose every name resolves in `dir(builtins)`"*. Measured
in-process: `` `bool` ``, `` `int` ``, `` `str` ``, `` `list` ``, `` `tuple` ``, `` `dict` ``,
`` `frozenset` `` each satisfy that condition **verbatim** and the guard **catches** every one of them —
`('symbol', 'names no symbol defined in src/nonogram')`. Cause located, not guessed: `_classify` tests
`_IDENTIFIER_CHAIN.fullmatch(span)` at **`:3175`** *before* `_is_type_expression(span)` at **`:3190`**, so
a bare builtin never reaches the type-expression branch. The steelman does not save it — *"clues cross the
boundary as `str`"* is a **false type claim** and reds. Only the subscripted and parenthesised forms
(`list[list[bool]]`, `(0,)`, `()`) are genuinely missed. **And it has a live consequence**: a future
`CLAUDE.md` reword to "grids are lists of `bool`" would red with a message this declaration says cannot
happen.

**2. `MEASURED_DEPENDENCY_CLAIM_MISSES` (`:3072-3079`) is NARROWER than reality.** A third evasion family
is undeclared: a paragraph that **invents** a runtime distribution. Measured — the live paragraph plus
`" and requests"` → `[]`; `` `pyproject.toml` declares exactly stdlib + Pillow + NumPy + requests `` →
`[]`; three invented dists at once → `[]`. Cause: `_dependency_claim_defects` (`:3082`) has four arms —
every declared runtime dist must be mentioned, no extra-only member may be, no backticked extra name, and
pyproject must be cited — and **none of them loops over the names the paragraph does mention**, so a
distribution in no pyproject table is invisible. It is live rather than hypothetical: the shipped
paragraph writes the dist names **unbackticked**, so AC-1's span rule cannot see them either
(`_claim_defects` on `"stdlib + Pillow + NumPy + requests"` → `[]`; only the backticked form reds). **The
word "exactly" in the guarded paragraph is unenforced on the upper side** — precisely the kind of residue
R3's last clause requires be recorded as a measured bound, and it is not in the table.

**The verdict line is therefore re-judged on this card: ADR-0039/R3 is `✗ violated` on its last clause,
not `✓ holds`.** Cycle 2 had marked it ✗ on that same clause; cycle 3 flipped it to ✓; this re-derivation
restores the ✗ with two *new* instances the flip did not cover. I am not leaving a ✓ on the card that an
independent agent could not reproduce.

**Why clause 3 passing everywhere is not a defence, and is in fact the sharpest result here.** All ten
mutants fired by the spot-check killed, each at the entry-keyed assertion — `CLAIM-MISS-2-GUTTED` reds at
`:3349`, exactly where the fix round said it would. But that assertion **pins the entry's *text*, not the
entry's *truth***. A declaration can have a perfect failing control and still say something false, and
that is how both defects above survived a 9.6 review. This is the card's own subject one level further
out than the card ever went: *a control over a claim is not a control over the claim's correctness.*

**Everything else about the verdict reproduced**, and some of it is stronger than claimed. M-1's em-dash
correction is right (`(?<=[.;])\s+` looks behind for `.` or `;` only, so colon, comma and em-dash all
join into one sentence; full stop and semicolon both split) and the breaking-set complement was probed —
`?`, `!`, en-dash and a parenthetical all give one sentence. M-2's narrowing is the measured one: the
lookup-table form it moved **off** the miss side is genuinely caught by **both** arms, and the two
remaining shapes are genuinely invisible to both. Both exemption equalities re-derived independently —
`MEASURED_PROSE_CITATIONS` is a true two-sided equality (its left side is derived from the sources, so a
new prose mention reds at `:2325`), while `MEASURED_KEYWORD_SPANS`' equality is **subset-by-construction**
and can only catch a *dead* exemption, never a newly absorbed site — a structural point the comment at
`:2908` claims and which is delivered by **default-deny elsewhere**, measured: `_classify("nargs=")` and
`_classify("metavar=")` both return `('unanalysable', 'is a shape this rule cannot read, so it is
denied')` and red at `:3274`. Equality plus default-deny satisfies the clause; the equality alone does
not.

**The recording-pass trap, a ninth time and at full strength: all ten mutants exited pytest 0 while the
matrix recorded a FAIL cell.** A test-level reading would have published ten real kills as survivors.
Domains stated and never conflated: target A **149** `ast.Assert` nodes / 29 reached / 3 collected tests;
target B **251** / 17 / 4. SHIPPED FAIL-free before every mutant. Worktree left clean, detached at
`e26e5473`, board lock never touched.

**Three by-catch items recorded, none of them gating.** `_dependency_claim_defects`' own docstring
(`:3093-3094`) still says the extras table "has grown **three times**" — an uncontrolled count one
function above the table M-6 just cleaned, and now inconsistent with `:3507`'s softened wording.
`_guarded_paragraphs` (`:2941`) cannot see a **continuation block** under a guarded lead-in (a second
`\n\n` block has no lead-in of its own), which entry [1] covers only by charity. And
`getattr(m, 'validate_' 'extent')` — implicit adjacent-literal concatenation — is **caught** by the AST
arm, because CPython folds it into one `Constant`, so `MEASURED_AST_SWEEP_MISSES[0]`'s head is over-wide
if read as a family rather than as the exact `+` expression it quotes.

#### [8h spot-check] ✗ **ADR-0039/R1 — `✓ holds` NOT reproduced either.** Two undeclared sites, and one of them has its own correct device 44 lines away

**Both cited evidence elements reproduced exactly**, which is worth saying first: `F6-DECL-GUTTED` kills
at `tests/test_guard_integrity.py:3349` and `AST-MISS-3-GUTTED` at `tests/test_web_server.py:2466`, under
the committed instrument, both passes, ANY-RED, with **twelve** SHIPPED readings taken and every one
cell-for-cell identical (`69 PASS / 0 FAIL / 80 NOT-REACHED` on the guard target, `34 / 0 / 217` on the
web target), and every mutant's `old` pre-counted as occurring exactly once so no reading is the
writes-nothing false survivor. The fix round did real work. **The rule-level `✓ holds` is what fails.**

One bounded independent pass, over hand-written sets the new guards consult and absence-assertions over a
clean file, found **two** claims whose control cannot fail. Both are new in this card. Of seven mutants
the skeptic chose itself, **five survived, four of them undeclared** — each verified at whole-file scope
with plain pytest, not just under the narrowed selection:

**1. `tests/test_guard_integrity.py:3789` — a set a guard consults, with nothing that reads it.**
`test_no_guarded_paragraph_says_the_mechanism_is_unenforced` consults
`("not yet enforced", "not enforced", "hook points")` and asserts `offenders == []` against the shipped
`CLAUDE.md`. Rot **all three** members → `tests/test_guard_integrity.py` is **157/157 green**. Nothing
else in the repo reads that set. So the claim its name and docstring make — the stale shape is denied by
value — has no control that can fail: an inert phrase set passes identically to the live one, which is
R1's *"narrative, not coverage"* clause verbatim.

**And the comparison is internal and unflattering.** Two methods further down the same class,
`test_the_figure_rule_reds_on_the_figure_that_shipped` (`:3834`), supplies exactly the
caught-WITH/missed-WITHOUT pair R1 asks for — and its docstring at `:3806-3814` *explains why*: **"a rule
with no instance and no fabricated case is exactly the unfalsifiable arm this card is about."** The device
was built, documented, and then not applied to its sibling rule 44 lines up. That is the single sharpest
finding on this card, because it is not an oversight about the rule — it is the rule understood, written
down, and missed once.

**2. `tests/test_web_server.py:120` — the derivation can silently shed half its members.**
`_DOMAIN_VALIDATOR_SHAPE = re.compile(r"^_?(?:validate|parse)_")`, whose own comment at `:115-119` names
`_validate_side` as what the `_?` is for. Drop the `_?` → measured `LOST members: ['_validate_side']`,
and **every control still passes, whole file green**. The floor pin at `:2302` names only
`validate_extent`, `validate_density`, `parse_tier` — **3 of the 6** derived members — so the set is
guarded for half of itself. The pin's own docstring at `:2295-2301` states this exact hazard: *"a
derivation that stopped matching would hand the guard a smaller set and look identical."* Contrast
`SHAPE-PARSE-DROP`, which removes `parse_tier`/`parse_art` and **is** killed at `:2302`: the control
exists and works, it is simply not complete over the set it guards.

**Two weaker survivors, reported and not gated on.** The `×` member of the figure rule's character class
(`:3819`) has no control — the planted case at `:3838` writes ASCII `40x40` — so a `30×40` figure would
pass while the helper's docstring claims *"every NxM figure"*. And `_PATH_SUFFIXES`' `.yml`/`.cfg`/`.txt`
members (`:2938`) have no completeness test, but `_classify` is **default-deny**, so losing a suffix makes
the rule *stricter* (the span falls to "unanalysable" and reds) — a false-positive risk, not a missed
catch. Correctly distinguished rather than lumped in.

**One survivor that is declared, and reproducing it is a point in the card's favour.**
`SUBSTRING-ARM-OFF` survives — and the diff **says so**, at `tests/test_web_server.py:2227-2241`: the arm
*"carries no unique detection, measured by exhaustive partition … it is deliberately left without a
control of its own … Do not read its presence as evidence that a prose mention is caught here."* The
skeptic reproduced that measurement rather than refuting it. That is R1's *"narrowed to what is
measured"* done honestly, and it is presumably part of what the ✓ was built on.

**A new bound on the instrument, and it is a gap in the instrument's own gate rather than in this card.**
A SHIPPED baseline can be **test-level red (pytest exit 1) with 0 FAIL cells** and `_refuse_unless_clean`
**accepts** it, because its contract is FAIL-free plus ≥1 arm reached. Cause: a selection containing
`with pytest.raises(AssertionError, ...)` (`tests/test_web_server.py:2660`, `:2679`) has the raise
swallowed by the recording pass, so the block fails `DID NOT RAISE` **outside** the `ast.Assert` domain
while plain pytest on the same selection is green (19 passed). Anyone re-measuring this diff must read
the **exit code**, not only the cells. Added to the backlog item that already carries the instrument's
blind spot — this is a sharper statement of it than the one on record.

**Ninth and tenth instances of the recording-pass trap:** all three declaration-gutting mutants exited
pytest **0** in the recording pass while the matrix recorded a FAIL cell. A one-pass reading would have
published three real kills as survivors.

---

### [Escalated] 2026-10-23 — the 8h spot-check failed on **2 of 2** holds sampled, and this is the owner's call

**Station: implementation. Route: the owner chooses one of the three options below.** Worktree and branch
are **KEPT** — five good commits are on them and the full suite is green at `e26e5473`.

**I said in-session that I would route this rather than escalate, on the premise that the fix was "two
text narrowings". That premise is now false and the decision is reversed.** R3's two defects are text;
R1's two are **missing controls** — work that adds assertions, in a card with no review cycle left to
certify them. Recording the reversal rather than quietly acting on the better information.

**What the sample says, and it is the part that decides this.** The spot-check is capped at 3 and samples
the review's `✓ holds` lines. I sampled **2** of the 8, choosing the two that cycle 2 had marked `✗` and
cycle 3 flipped to `✓` — the highest-risk flips. **Both failed re-derivation.** A third sample
(CON-009/CON-010) reproduced perfectly, so the review is not uniformly unreliable; but the two *flips*
are exactly where it was. Two of two is not a localized slip, and the cap means I cannot cheaply learn
whether the remaining five holds are sound.

**The four defects, all new in this card, all undeclared, each measured to a line:**

| id | site | defect | what the fix is |
|---|---|---|---|
| S-1 | `tests/test_guard_integrity.py:3789` | the phrase set `("not yet enforced", "not enforced", "hook points")` has **no control**: rot all three and the file is 157/157 green | **add a control** — a fabricated positive, exactly the device `:3834` already implements and `:3806-3814` documents |
| S-2 | `tests/test_web_server.py:120` + `:2302` | the floor pin names **3 of 6** derived members, so dropping `_?` sheds `_validate_side` with every control green | **widen the pin** to all six derived names |
| S-3 | `tests/test_guard_integrity.py:2921-2923` | `MEASURED_CLAIM_MISSES[2]` is **wider than measured** — declares as missed a family (`bool`, `int`, `str`, …) the guard catches, because `_classify` tests the identifier chain at `:3175` before the type branch at `:3190` | narrow the entry's condition to the subscripted/parenthesised forms it is really about |
| S-4 | `tests/test_guard_integrity.py:3072-3079` | `MEASURED_DEPENDENCY_CLAIM_MISSES` is **narrower than reality** — an invented runtime distribution evades all four arms, so "exactly" is unenforced upward | declare the third family, with a case |

Plus two weaker survivors not gated on (the `×` member of the figure class at `:3819`; `_PATH_SUFFIXES`
at `:2938`, where default-deny makes the loss *stricter* rather than blind), and three by-catch prose
items. S-1 and S-2 are **ADR-0039/R1 clause 1**; S-3 and S-4 are **R3's last clause**.

**What is NOT in doubt, so the options are about scope and not about quality.** The full suite is green at
`e26e5473` (8921 executed / 8894 passed / 27 skipped / 0 failed), every AC passes with on-disk plants in
both states, G-1..G-7 all hold with G-1 and G-6 verified two independent ways, CON-009 and CON-010 are
genuinely run and green (9 passed — and the selector trap that hid CON-010 twice is now measured and
documented), cycle 3 found 0 critical and 0 important, and the three cited mutant kills all reproduce.
The card's actual deliverable — the three false `CLAUDE.md` claims and the dead `validate_size` token in a
live guard — is **done and certified**.

**The three options, with what each costs:**

1. **Fix S-1..S-4, then one re-entry review cycle to certify them** (my recommendation). The aggregate
   round counter permits it — 3 rounds spent of the 6 that signal structural non-convergence — and the
   work is bounded: one fabricated positive, one widened pin, two declaration edits. Cost: a fix round, a
   review cycle, and a re-gate. This is the option that leaves no knowingly-false declaration in the tree,
   which matters more than usual on *this* card, since a false claim in a file agents read is its subject.
2. **Merge now; route S-1..S-4 to CARD-266**, which already owns the standing-check mechanism and has
   just been handed two related items. Cheapest, and defensible: R3's last clause asks that residues be
   *recorded as measured bounds*, and they now are — on this card, to the line, with their mechanisms. The
   cost is honest and should be stated: four controls that cannot fail ship in a card raised to remove
   controls that cannot fail, and S-1's site sits 44 lines from the correct device.
3. **Fix S-1..S-4 and merge without a certifying cycle**, naming them as shipping uncertified. Cheapest
   that still leaves the tree honest, and it is the wave-48 trap by name: the card's final edit would
   carry no reviewer. I do not recommend it, and I would not take it without being told to.

**Nothing was modified for this escalation.** No fix applied, no commit, no rebase. All three review
reports (cycles 1, 2, 3) are already synced into the main repo's `meta/review/`, so the evidence survives
whatever happens next. The two throwaway spot-check worktrees under the scratchpad are removed. The
worktree is clean at `e26e5473` and the branch is untouched.


---

### [Escalation CLOSED] 2026-10-23 — the owner chose **option 1**: fix S-1..S-4, then certify

**Decision: one fix round for all four, then a re-entry review cycle to certify it, then re-gate and
merge.** Status returns to `review`; the card leaves `escalated` and retakes its slot. The reasoning the
owner acted on, restated so the next reader does not have to reconstruct it: the four defects are
*controls that cannot fail*, in a card raised to remove controls that cannot fail — and S-1's site sits
**44 lines** from the correct device, whose own docstring explains why that device exists. Landing them as
residues would have been defensible on cost and wrong on substance.

**The budget allows it, which is why this is not a stretch.** The aggregate round counter stands at **3**
of the 6 that signal structural non-convergence, so a re-entry cycle 4 is inside the discipline rather
than an exception to it. The fix is bounded and adds no new mechanism: one fabricated positive (copying
`:3834`), one widened floor pin, two declaration edits.

**What this round must not do**, stated because the temptation is obvious: it must not touch
`CLAUDE.md` (G-1 — the three single-line hunks are final), must not add a control for the substring arm
(its zero-unique-detection is measured and declared), and must not rewrite `CLAUDE.md:50`'s timeout
sentence (refuted at cycle 2, and the `check_deadline` census belongs to CARD-266). Four defects, their
two weaker siblings, three prose by-catch items. Nothing else.

---

## [One-way sync] Fix round 3's own notes, pulled from the worktree


## Worktree notes -- fix round 2 (`forge:fix`, auto), 2026-10-23, on review cycle 2

Narrowing round, as briefed: ten items, no new mechanism. Scope held to the card's six files; no `src/`
path touched (`git diff --name-only $(git merge-base HEAD main)` lists `CLAUDE.md`, the adapters doc and
four `tests/` files, **zero** `src/` paths -- G-6 by construction). `tests/test_cli.py` left alone and
re-verified byte-identical to `main` (`shasum -a 256` = `f0a9dc3c24b62c0d…` on both sides; the brief's
`e30a6ac6…` was a different digest form, the identity is what matters and it holds). `CLAUDE.md` was
**not** edited this round -- cycle 2's I-1 was refuted and the file still carries exactly three
single-line hunks at `:46`/`:48`/`:50` (`git diff --unified=0` → three `@@ -N +N @@` headers, G-1).

### C-1 + M-7 -- the adapters page, put back into the present tense

Every line number re-derived in this worktree at HEAD before writing anything, not copied from the
brief:

| claim | cited on the page before | **re-derived** |
| --- | --- | --- |
| the qualified "exactly two adapters" sentence | `src/nonogram/__init__.py:40` | `:71`-`:73` (and the unqualified statement at `:78`); `:40` is inside the module-list block |
| the `_ADAPTERS` comment | by name (this branch had already dropped the number) | `tests/test_cli.py:743`-`:747`, `_ADAPTERS` itself at `:748` |
| the test that pins the set | by name | `def` at `:905`, its docstring's first line at `:906` |
| the web adapter's copy of the claim | by name | `src/nonogram/web/__init__.py:21`, still present |

Three false claims removed, one stale figure removed:

* **(a)** the bold verbatim quotation was text from `d40e9d4a`'s version of `tests/test_cli.py`, which
  the owner's fold reverted. `grep -rn "grows only by a deliberate edit" src tests` → **0 hits** at HEAD.
  Replaced with the comment the file actually carries, quoted whole -- including its stale "closed at
  two names", because that stale count *is* the subject of the block underneath and eliding it with an
  ellipsis would have been a second kind of dishonest framing.
* **(b)** the past tense ("contradicted … until CARD-264", "All three now state the *rule*") is now the
  present tense, because the contradiction is live at `:744` / `:905` / `:906`. The page now says the
  three sites in that file are **CARD-265's** subject (owner decision 2026-10-22) and that the count
  there is **unguarded**, which is the measured fact: `_ADAPTER_COUNT` (`tests/test_cli.py:1126`) is
  consumed by `_adapter_counts` (`:1270`), whose body reads `CLAUDE.md`'s text and nothing else.
* **(c)** the sentence citing `TestAdapterAllowlist_NoProseClaimsAStaleCount` and `len(_ADAPTERS)` is
  deleted. `grep -rn "NoProseClaims" src tests` → **0 hits**; `grep -rn "len(_ADAPTERS)" src tests` →
  **0 hits**.
* **M-7**: `src/nonogram/__init__.py:40` → cited by name ("module docstring"), consistent with the rest
  of the page.

Not done by reverting to `main`'s hunk, deliberately: `main`'s six line citations are each off by one
(743/744/741/748/905/915 against its 742/743/740/747/904/914) and its claim that the stale count also
sits at `CLAUDE.md:45` is false -- `main`'s own `CLAUDE.md:42` states no count. This branch's two real
improvements (no `:NNN` into another file; CARD-261 named as what removed `CLAUDE.md`'s copy) are kept,
and the verified-open `web/__init__.py` site is kept flagged open.

### I-2 secondary -- which shape, and why

**Chose: delete the decorative assertion and narrow the docstring to the AST arm.** The brief offered
the alternative of a fabricated source pair that genuinely exercises the substring arm, and that
alternative is incoherent with the brief's own primary follow-up: the substring arm carries **zero
unique detection**, so a control for it would pin a reach no other arm has -- a new unfalsifiable arm on
a card about unfalsifiable arms. `assert "validate_density" in planted` is gone; the docstring now
claims only what its body measures, and records what it used to claim and why that was wrong.

### I-2 primary follow-up -- the partition, re-measured here

Recorded as a comment above the substring loop in
`test_the_web_package_imports_no_domain_validator`. Re-derived rather than taken on trust, in memory,
against the real `_WEB_SOURCES` (no on-disk plant, so no `src/` file was ever mutated):

* real `prose_only` = `[('submission.py', 'validate_extent')]` = `MEASURED_PROSE_CITATIONS` -- the
  equality holds as shipped;
* a **prose**-shaped violation (the token in a docstring, in a non-exempted file): AST arm returns `[]`,
  `prose_only` grows by `('handler.py', 'validate_density')`, and the equality in
  `test_the_prose_exemption_is_exactly_the_sites_that_exist_today` **breaks**. That comprehension
  re-derives prose mentions from each source directly and does not route through the substring loop, so
  disabling the loop does not weaken it;
* a **code**-shaped violation: AST arm returns `['handler.py:1 imports validate_density']`, so it reds
  one line above the loop.

The arm is kept (G-2: nothing the guard caught is given up) and deliberately left without a control.

### The five declared-miss narrowings, before → after

Every "after" below is a measurement run in this worktree, not a figure inherited from a docstring.

| id | declaration | measured before | **after** |
| --- | --- | --- | --- |
| **M-1** | `MEASURED_TIMEOUT_CLAIM_MISSES[1]` | entry said an em-dash *breaks* the split. Measured against `_timeout_sentences`: em-dash-joined = **1** sentence (does **not** break); colon = 1; comma = 1; full stop = **2**; **semicolon = 2** (unmentioned by the entry) | entry names colon, comma **and em-dash** as non-breaking, and full stop **and semicolon** as breaking. The em-dash body moved from the caught list to the missed list -- it did read as 2 sentences, but on the full stop `cited` already ends with, which is why it looked like evidence. A semicolon body took its place on the caught side |
| **M-2** | `MEASURED_AST_SWEEP_MISSES[2]` | declared "a lookup table, an environment variable or a request" as a miss. Measured: `{"extent": "validate_extent"}` → `["x.py:1 writes 'validate_extent' in a string literal"]` -- **caught**, by both arms. `os.environ[...]` → `[]`; `posted["validator"]` → `[]` | narrowed to "a name supplied from outside the source -- an environment variable or a request field -- which no contiguous run of the file spells". New case holds the lookup table on the **caught** side and the two external forms on the **miss** side, and denies the re-widening (`assert "lookup table" not in declared`) |
| **M-3** | `MEASURED_CLAIM_MISSES` | three entries, two demonstrated executably, **none** of them read by any assertion -- which is why `F6-DECL-GUTTED` survived | each case now reads a fragment of its own entry. Entry `[1]` ("a lead-in not in `GUARDED_PARAGRAPHS`") had no case at all and gets one, shown both ways round (`_guarded_paragraphs` finds nothing under `**Test style.**`, finds the paragraph under a guarded lead-in) |
| **M-4** | `_dependency_claim_defects` | no declared reach. Measured evasions: un-backticked extras ("the dev, admin and db extras sit outside it") → `[]`; a **denial** ("`pyproject.toml` no longer declares Pillow or NumPy at runtime") → `[]`. Measured **non**-evasion: members un-backticked ("flask, gunicorn, reportlab, werkzeug are admin-only") → **4** defects | `MEASURED_DEPENDENCY_CLAIM_MISSES`, two entries, both held on the miss side by a new `test_the_rule_names_what_it_cannot_see` -- which also holds the member restatement on the **caught** side, generically (it picks the first extra with non-runtime members from pyproject's own tables, so a fourth extra needs no edit here) and keyed on the entries' own text. The backtick-independence of the member arm is **not** declared away |
| **M-6** | the dependency class's docstring | "pyproject.toml carries **three** extras" -- re-derived by `tomllib` as `['admin', 'db', 'dev']`, accurate today and rottable | the number is gone, not controlled (G-3: point at the authority). `test_the_restatement_rule_covers_every_extra_pyproject_declares` already builds from those keys, so no second reader was added |

`M-5`: `_src_symbols`' `ast.parse` now passes `filename=str(path)`. The ten SyntaxWarnings a
`TestClaudeMd` selection raises print
`src/nonogram/sourcing/templates/dog_in_house.py:6` instead of `<unknown>:6`, matching the sibling
helper `tests/test_web_server.py::_domain_validator_names`.

`M-8`: prose only -- "…was ``validate_size`` until CARD-264; that name has no definition anywhere in
``src/`` — ADR-0022/R1 …". The relative clause no longer attaches to the card id. The surrounding
superseded-50x50 reasoning is untouched.

### Mutants -- the controls were measured, not asserted

`tests/kill_matrix.py` (the committed instrument; nothing else written), line-count-preserving,
**ANY-RED**, SHIPPED re-run between mutants, **both passes**. Domains stated per the instrument's own
rule: the denominator is the target file's `ast.Assert` node count, carried separately from the
collected-test count.

`tests/test_guard_integrity.py` -- **149** assertion nodes; selection of **3** tests, **29** arms
reached; SHIPPED **0 FAIL of 29 reached** in both passes:

| mutant | recording | re-raising | FAIL cell(s) |
| --- | --- | --- | --- |
| `F6-DECL-GUTTED` (gut `MEASURED_CLAIM_MISSES[2]`'s middle line) | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3349` `assert "resolves in dir(builtins)" in MEASURED_CLAIM_MISSES[2]` |
| `TIMEOUT-MISS-2-GUTTED` | exit 0, **2 FAIL** | exit 1, **1 FAIL** (short-circuit) | `:3776`, `:3777` -- the two joiner halves |
| `DEP-MISS-1-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3640` `assert "without backticks" in MEASURED_DEPENDENCY_CLAIM_MISSES[0]` |
| `DEP-MISS-2-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:3641` |

`tests/test_web_server.py` -- **251** assertion nodes; selection of **2** tests, **14** arms reached;
SHIPPED **0 FAIL of 14 reached** in both passes:

| mutant | recording | re-raising | FAIL cell |
| --- | --- | --- | --- |
| `AST-MISS-3-GUTTED` | exit 0, **1 FAIL** | exit 1, **1 FAIL** | `:2466` `assert "an environment variable or a request field" in declared` |

Every mutant produced **≥1 FAIL cell** in both passes -- so none of them is the "absent `old` writes
nothing" shape. `F6-DECL-GUTTED` was the mutant cycle 2 measured as **surviving**; it is now killed, and
`AST-MISS-3-GUTTED` likewise. The recording pass's exit 0 with FAIL cells recorded is exactly the trap
the brief warned has caught this card six times -- hence both passes, read per cell.

### Gates run (scoped, never the full suite)

`NONOGRAM_FULL_SUITE_LOCK=/tmp/card264-fix2.lock` was exported for every pytest, script and mutant run,
so the board's own `meta/kanban/.full-suite.lock` was never read, written or created.

* `tests/test_guard_integrity.py tests/test_web_server.py tests/test_sourcing_image.py` -- **all green**,
  no failures.
* `tests/test_timeout.py` -- collection only (**17** collected, exit 0): this round's change there is one
  docstring sentence.
* **G-2**: `TestWebServer_BindsLoopbackOnlyByDefault` (CON-009) and CON-010's four arms
  (`test_the_corpora_are_large_and_cover_every_declared_signal`,
  `test_every_cross_origin_or_foreign_authority_request_is_refused`,
  `test_every_same_origin_or_metadata_free_request_is_served`,
  `test_the_accepted_fetch_metadata_is_the_two_spec_values`) -- **10 passed, exit 0**. CON-010 is
  module-level `def`s, not a class: the id `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`
  is the logical requirement id (stated in the comment at `tests/test_web_server.py:1950`), and
  `PropertyTest_` is not in pytest's `python_classes`, so selecting it as a class runs nothing. Worth
  knowing for any future brief that names it as a class.
* `_WEB_SOURCES`' non-empty assertion and `_DOMAIN_VALIDATORS`' are untouched; nothing the guard caught
  was given up.
* **G-7**: no durations measured or reported anywhere in this round.

### Flaky, pre-existing, and *not* this round's

`TestWebServer_BindsLoopbackOnlyByDefault::test_the_port_stays_free_on_every_other_interface` failed
**once** mid-round (`_port_is_free_on('192.168.0.109', 59110)` returned `False` where the test wants
`True`), then passed on three consecutive isolated re-runs and in the combined CON-009+CON-010 run. It
is at `tests/test_web_server.py:555`, inside no hunk this card touches, and depends on the host's
network and on whether another process on this machine holds the ephemeral port the fixture drew. It is
host-dependent flake, not a regression -- but it is a **real** flake on a CON-009 control, and it
deserves its own card rather than a shrug.

### Skipped, with the measurement

* **I-1** (`CLAUDE.md:50`) -- refuted in cycle 2 and **not touched**, per the brief. The sentence's own
  enumeration is two checkpoints and both are pinned.
* `tests/test_timeout.py:479`-`:485`'s `_blind_propagation` defect -- out of scope by the brief, being
  carded separately. `tests/test_timeout.py` was edited this round for M-8 only, in the module docstring;
  those lines are untouched.
* The three `U+2022` codepoints in `src/nonogram/admin/pdf_generator.py` are **not** a G-6 violation:
  they are a named, controlled exemption (`DINGBAT_EXEMPT_MODULES` in
  `tests/test_book_difficulty_dots.py`, whose reason is itself asserted). Checked because the brief
  asked for structural verification rather than assumption; the structural check that settles G-6 for
  this card is that the diff contains no `src/` path at all.

## Worktree notes -- fix round 3 (`forge:fix`, auto), 2026-10-23, on the Step 8h holds spot-check

The spot-check sampled **2 of 2** contract verdicts and both failed. All four gating defects are one
class, and it is this card's own subject: **a control that cannot fail.** Two were missing controls
(S-1, S-2); two were declarations that misstate what the guard does (S-3 wider than measured, S-4
narrower than reality). Scope was `tests/test_guard_integrity.py` and `tests/test_web_server.py` and
nothing else -- `CLAUDE.md` is untouched (G-1 re-verified: `git diff -U0` against the merge base
`d90753df` is exactly three single-line hunks, at `:46`, `:48`, `:50`, and the file is clean against
`HEAD`), and the branch diff contains **no `src/` path at all** (G-6, verified structurally rather than
assumed).

### S-1 -- `test_no_guarded_paragraph_says_the_mechanism_is_unenforced`: a set with nothing reading it

**Shape chosen:** the device that already existed 44 lines away. `_figures_outside` is a deny-side rule
with no instance left in the tree and it carries a fabricated red case for exactly that reason; the
phrase rule was in the same position and had none. The hand-written tuple was lifted out of the test
body into `_UNENFORCED_PHRASES` with a `_unenforced_claims(bodies)` classmethod beside it that takes
the paragraphs instead of reading `CLAUDE.md`, so a fabricated body can red on every run.

**The one trap worth recording:** keying the new cases on the tuple's *own members* would have produced
a control that still cannot fail -- rot a member and both the body and the expectation move together.
So each case writes its phrase as a **literal**, asserts it is a member, and asserts the fabricated
body reds with exactly that phrase. One case per member, so the control's reach equals the set's size.

* **Before (reproduced here, not taken on trust):** all three members rotted to `ROT ...` ->
  `tests/test_guard_integrity.py` **157 passed, pytest exit 0**. Nothing else in the repo reads the set.
* **After:** four mutants, each killed in **both** matrix passes --
  `S1-ROT-NOT-YET`, `S1-ROT-NOT-ENFORCED`, `S1-ROT-HOOK-POINTS` (one member each) and
  `S1-ROT-ALL-THREE`. Recording pass: 2 FAIL cells each; re-raising pass: exit 1, 1 FAIL each.

### S-2 -- `_DOMAIN_VALIDATOR_SHAPE` could shed half its members

**Shape chosen, and how the second copy was avoided.** The brief offered two shapes; I took the
stronger one. A hand-written list of six names is a second copy (G-3) that rots the day a seventh
validator is added, and pinning the three *shape classes* would still have left `parse_art` and
`validate_aspect_ratio` unpinned (a pattern narrowed to `^_?(?:validate|parse)_[a-z]*$` keeps one
member of every class and sheds `validate_aspect_ratio` silently). So the pin is an **equality against
an independently written second derivation**: `_independently_derived()` walks the same two authorities
the guard walks -- the package tree and `cli_tests._ADAPTERS` -- and applies a predicate spelled out in
the test (`node.name.removeprefix("_").startswith(("validate_", "parse_"))`) instead of consulting
`_DOMAIN_VALIDATOR_SHAPE`.

**So there is no second copy of the six names anywhere**: both sides are enumerated from the package, a
seventh validator or a fourth adapter moves both at once with no edit here, and what is deliberately
*not* shared is the regex -- a pin that consulted the same pattern would move with every narrowing of
it. This is CLAUDE.md's own standing test-style preference (`propagate.mask_runs` cross-checked against
`clues.encode_line` from the test tree), and here it is not a preference but the mechanism.

* **Before (reproduced here):** drop the `_?` -> `_validate_side` leaves the derived set and
  `tests/test_web_server.py` is **166 passed, pytest exit 0**, every control green. The floor pin named
  three of the six.
* **After:** all three narrowings killed in both passes. `S2-DROP-PRIVATE-PREFIX` kills exactly the new
  equality (`tests/test_web_server.py:2369`) and nothing else -- the cleanest possible reading, since
  that line is the whole of the fix. `S2-DROP-VALIDATE` kills 7-8 cells, `S2-DROP-PARSE` kills the
  three-name floor at `:2356`, which is the contrast the brief measured and which still holds.

### S-3 -- `MEASURED_CLAIM_MISSES[2]` was WIDER than measured

**Measurement reproduced:** `` `bool` ``, `` `int` ``, `` `str` ``, `` `list` ``, `` `tuple` ``,
`` `dict` ``, `` `frozenset` `` each satisfy the old entry's condition verbatim and the guard **catches
every one** -- `('symbol', 'names no symbol defined in src/nonogram')` -- because `_classify` tests
`_IDENTIFIER_CHAIN.fullmatch` before `_is_type_expression`. Only `list[list[bool]]`,
`tuple[tuple[int, ...], ...]`, `(0,)` and `()` are genuinely missed.

**Shape chosen:** the entry is narrowed to "a subscript or a tuple display", states in its own text that
a bare builtin does **not** reach `_is_type_expression`, and the narrowing is held **by value** on both
sides: five subscripted/parenthesised forms on the missed side, all seven bare builtins on the **caught**
side with their exact defect string, plus `assert "dir(builtins)" not in MEASURED_CLAIM_MISSES[2]` so
the entry cannot drift back to the over-wide wording. `CLAIM-MISS-2-GUTTED` keyed on
`"resolves in dir(builtins)"`, which the rewrite deliberately removes, so it was **re-keyed** onto
`"subscript or a tuple display"` and `"A bare builtin does not reach it"`.

* **After:** three mutants, all killed in both passes. `S3-DECL-GUTTED` (the narrowing sentence
  emptied), `S3-DECL-REWIDENED` (the `dir(builtins)` wording put back) and -- the behavioural half --
  `S3-CLASSIFY-REORDERED`, which makes `_classify` fall through to the type-expression branch for a
  bare builtin and reds the caught-side case. That last one is what makes the entry's claim about
  *ordering* load-bearing rather than decorative.

### S-4 -- `MEASURED_DEPENDENCY_CLAIM_MISSES` was NARROWER than reality

**Measurement reproduced:** the live paragraph plus `" and requests"` -> `[]`; a fabricated
`` `pyproject.toml` declares exactly stdlib + Pillow + NumPy + requests `` -> `[]`; three invented
distributions at once -> `[]`. All four arms of `_dependency_claim_defects` ask what pyproject.toml
declares and **none loops over the names the paragraph mentions**. And it is live, not hypothetical:
`_claim_defects` on `"stdlib + Pillow + NumPy + requests"` -> `[]`, because the shipped paragraph writes
the names unbackticked; only `` `requests` `` reds there.

**Declared, not closed** -- and that is the decision, with the reason: closing it means deciding what
counts as a distribution name in free prose, which is a different rule and not this card's. (I checked
whether it was cheap: it is not. Every cheap spelling I could write either reds on ordinary English in
the paragraph or re-introduces a hand-written list of known-bad names, which is the disease.) The third
family is now an entry stating all of that, held by a committed case on the **miss** side with three
bodies -- the live paragraph with one name appended, a fabricated one that still says "exactly", and
three invented distributions at once -- plus the AC-1 span half, so the sentence "the word *exactly* is
unenforced on the upper side" is measured in the test rather than asserted in prose.

* **After:** `S4-DECL-GUTTED` killed in both passes. `S4-UPPER-SIDE-CLOSED` -- a line-count-preserving
  mutant that gives the function a (crude) invented-name arm -- is also killed in both passes, which is
  the half that matters: the three miss-side cases are the thing that will red the day somebody *does*
  close this, so the declaration cannot outlive the reality it describes.

### The weaker survivors and the by-catch

* **W-1 (the `×` member).** The figure that shipped in `CLAUDE.md:50` was written with a multiplication
  sign -- `40×40+` -- and the planted case wrote ASCII `40x40`, so rotting `[x×]` to `[x]`
  survived. Both spellings now have a case. **And one thing the brief did not name, which I closed and
  am flagging explicitly:** `_figures_outside` bound the second side to `_other` and never looked at it,
  so `30x40` returned `[]` while the helper's docstring claimed *every NxM figure*. Measured before
  changing it, and measured safe to close: the guarded paragraphs carry **zero** NxM figures today, so
  the wider rule reds on nothing that ships. Three mutants, all killed in both passes:
  `W1-ASCII-ONLY`, `W1-MULT-SIGN-ONLY`, `W1-FIRST-SIDE-ONLY`.
* **W-2 (`_PATH_SUFFIXES`).** **Declared, not controlled by member**, and the direction is why. Measured:
  a suffix the tuple does *not* carry does not slip through -- `docs/GENERATION_ALGORITHM.json`
  classifies `('unanalysable', 'is a shape this rule cannot read, so it is denied')`, which the caller
  reads as a defect, while `docs/GENERATION_ALGORITHM.md` classifies `('path', '')`. `_classify` is
  default-deny, so losing a suffix makes the rule **stricter**: the hazard is a false positive somebody
  has to judge, never a missed catch, and a control over `.yml`/`.cfg`/`.txt` would pin a hazard that
  cannot cause a miss. The direction is declared in a comment on the tuple **and** held executably by
  `test_a_suffix_outside_the_table_is_denied_not_accepted`, which is the property that makes the
  declaration true -- so a default-*allow* rewrite reds. `W2-DEFAULT-ALLOW` killed in both passes
  (4 FAIL cells).
* **B-1 (the uncontrolled count).** `_dependency_claim_defects`' docstring said the extras are "a table
  that has grown **three times**", one function above the class docstring M-6 softened to "grown more
  than once". The number is **gone** rather than corrected, and the sentence points at the authority
  instead: "a table pyproject.toml owns and `_declared_distributions` reads" (G-3). No count survives in
  either place.
* **B-2 (the continuation block).** Measured first, as asked: a second `\n\n` block under a guarded
  lead-in has no lead-in of its own, `_guarded_paragraphs` hands on a body that stops at the blank line,
  and the dead symbol below it yields **0 claims and 0 defects**. `MEASURED_CLAIM_MISSES[1]` covered it
  only by charity, so its wording now names it; its own entry would have renumbered the tuple that two
  other cases index by position. The case shows both states -- invisible across the blank line, caught
  one blank line higher. `B2-DECL-GUTTED` and `B2-BLOCKS-WIDENED` (the splitter widened to see the
  continuation, which would make the declaration false) both killed in both passes.
* **B-3 (`MEASURED_AST_SWEEP_MISSES[0]`'s head).** Measured: `getattr(m, "validate_" "extent")` --
  implicit adjacent-literal concatenation -- **is caught** (`x.py:2 writes 'validate_extent' in a string
  literal`), because CPython folds it into one `ast.Constant` before `_domain_validator_hits` sees the
  tree, while the `+` form the entry quotes is genuinely missed. The head now names the operator and
  states the implicit form is caught; the caught form sits on the caught side of the case, next to a
  loop showing no contiguous run of *that* source spells the token either -- which is what makes the
  distinction about the fold and not about the substring arm. `B3-DECL-HEAD-REWIDENED` and
  `B3-LITERAL-ARM-BLINDED` both killed in both passes.

### Instrument discipline, and the two traps the brief named

Mutants were run only through the committed instrument, `tests/kill_matrix.py`, every edit
line-count-preserving, ANY-RED aggregation, SHIPPED re-run between mutants.

* **Trap (a), an absent `old`.** Every mutant's `old` was pre-counted in the driver with
  `assert src.count(old) == expect` before the run; all 20 occurred **exactly once**. The instrument's
  own `expect` check is the second gate.
* **Trap (b), a test-level-RED SHIPPED with no FAIL cells.** SHIPPED's **exit code** was read, not only
  its cells. `tests/test_guard_integrity.py` carries no `pytest.raises(AssertionError, ...)` at all
  (checked), so the whole file was a safe selection: **SHIPPED 0 FAIL of 172 reached, pytest exit 0**.
  For `tests/test_web_server.py` the selection was narrowed to
  `TestWebAdapter_TheForbiddenTokenSetHasNoDeadMember` plus
  `test_the_web_package_imports_no_domain_validator`, which excludes the two
  `pytest.raises(AssertionError)` blocks: **SHIPPED 0 FAIL of 39 reached, pytest exit 0**.

**Domain of every figure.** `tests/test_guard_integrity.py`: 15 mutants, denominator **172 `ast.Assert`
nodes**, collected tests **161** (the two are carried separately and neither is quoted for the other),
child instrumentation off, both passes. `tests/test_web_server.py`: 5 mutants, denominator **256
`ast.Assert` nodes** with **39 reached** under the narrowed selection, collected tests **11**, child
instrumentation off, both passes. **All 20 mutants killed in both passes**; no survivors, and no mutant
relied on an instrumented-only kill -- every one is also exit 1 in the re-raising pass.

### Gates

* `tests/test_guard_integrity.py` **161 passed** (157 before: +3 S-1 parametrized cases, +1 W-2 case).
* `tests/test_web_server.py` **166 passed** (unchanged count; S-2 and B-3 widen existing tests).
* Both together: **327 passed**.
* `tests/test_suite_profile.py` + `tests/test_kill_matrix.py`: **475 passed** -- run because
  `test_guard_integrity.py` and `test_suite_profile.py` are each other's second pair of eyes, so an
  edit to one is exactly the thing the other is built to notice.
* **G-2, CON-009 + CON-010:** selected by `TestWebServer_BindsLoopbackOnlyByDefault` plus CON-010's
  **three function names**, never by its requirement id -- **collects 9, 9 passed, pytest exit 0**. The
  trap was reproduced rather than taken on trust: `-k PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`
  collects **0** (166 deselected) and **pytest exits 5**. An empty room is not a pass.
  `_WEB_SOURCES`' and `_DOMAIN_VALIDATORS`' non-empty assertions are untouched.
* **G-5:** no new dependency; the only names used are `ast`, `re`, `pytest` and `cli_tests`, all already
  imported in the file that uses them.
* **G-7:** no timing measurement taken, no duration reported.
* Every on-disk plant ran under a verified trap -- manifest built **up front**, `cp -p` backups,
  restoration verified by `shasum -a 256 -c` **and** `diff -q` **and** `git status --porcelain`, shell
  trap armed on EXIT/INT/TERM -- and the instrument's own backup/restore/verify for the matrix runs. The
  tracked tree ends as `HEAD` plus the two scoped test files and this card's notes, and nothing else.

### Not touched, named so the next reader does not look for them

* `CLAUDE.md` (G-1), the docs page, `tests/test_timeout.py`, `tests/test_sourcing_image.py`,
  `tests/test_cli.py`, and anything under `src/`.
* **No control was added for the substring arm** in `tests/test_web_server.py`. Its zero unique
  detection is established by exhaustive partition and declared at `:2227`-`:2241`; a control there
  would pin a reach no other arm has.
* `CLAUDE.md:50`'s timeout sentence -- cycle 2's I-1 is refuted and the sentence's two checkpoints are
  both pinned.
* The `check_deadline` call census ("six sites") -- a real uncontrolled quantity, and **CARD-266's**.
* `tests/test_timeout.py:479`-`:485`'s `_blind_propagation` defect -- **CARD-278's**.

---

### [Fix 3] `098ecd91` — all four, plus five siblings, and one defect the brief never named

**FIX PRE-GATE run by the orchestrator rather than taken on report: 11 passed, exit 0** across the nine
node ids the FIXED lines name (S-1's control is parametrized ×3). Every FIXED line carries its
DECLARATIONS line; nothing was skipped. Scope verified before committing: two test files only, `CLAUDE.md`
untouched this round and still exactly three single-line hunks against the merge base, and **no `src/`
path in either the branch diff or the working diff** — so G-6 still holds by construction rather than by
sweep.

**S-2 is the fix worth reading, because it rejected two weaker shapes with a measurement.** The brief
offered a widened list or shape-class pins; the round took neither. A six-name list is a second copy
(G-3) that rots the day a seventh validator lands, and shape-class pins were **measured insufficient** —
`^_?(?:validate|parse)_[a-z]*$` keeps one member of each class, so `parse_art` and
`validate_aspect_ratio` stay sheddable. What shipped is an **equality against an independently written
second derivation**: `_independently_derived()` walks the same two authorities (the package tree and
`cli_tests._ADAPTERS`) with the predicate spelled out again in a different mechanism
(`name.removeprefix("_").startswith(("validate_", "parse_"))`), deliberately **not** sharing
`_DOMAIN_VALIDATOR_SHAPE` — *"a pin that consulted the same pattern would move with every narrowing of
it."* It cites this project's own precedent for the device, which is the right authority to cite:
`solver/propagate.py`'s `mask_runs` cross-checked against `clues.encode_line` from the test tree. **No
second copy of the six names on either side**, and a seventh validator moves both at once. I read the
shipped code rather than the report for this one: the non-emptiness assert, the three-name floor and the
`validate_size` tombstone all survive *beside* the new equality, so nothing was traded away for it.

**S-1 avoided the trap that would have recreated the defect.** Keying the new cases on
`_UNENFORCED_PHRASES`' own members would be unfalsifiable again — body and expectation move together
under a rot — so each case writes its phrase as a **literal**, one case per member. All three
single-member rots and the all-three rot are killed.

**S-4 was declared rather than closed, after checking that closing is not cheap** (every cheap spelling
either reds on ordinary English or re-introduces a hand-written bad-name list) — and the declaration is
held from **both** directions: a mutant that *closes* the upper side is killed too, so the entry cannot
quietly become false if someone later tightens the rule.

**One defect closed that no brief named, and the order of operations is the point.** `_figures_outside`
bound its second side to `_other` and never read it, so `30x40` returned `[]` while its docstring claimed
*every NxM figure*. The round **measured safety first** — the guarded paragraphs carry **zero** NxM
figures today, so widening the rule reds on nothing that ships — and only then closed it. That is the
right sequence for widening a deny-side rule, and it is the sequence CARD-262 had to learn the hard way.

**20 mutants, 20 killed in both passes**, with both named instrument traps handled explicitly: every
`old` pre-counted as occurring **exactly once** (so no reading is the writes-nothing false survivor), and
**SHIPPED's exit code read rather than only its cells** — the guard file carries no
`pytest.raises(AssertionError)` at all, so the whole file was safe at 0 FAIL of 172 reached, exit 0, and
the web selection was narrowed to exclude the two raises blocks at 0 FAIL of 39 reached, exit 0. Domains
stated and never conflated: **172** and **256** `ast.Assert` nodes against **161** and **11** collected
tests.

`tests/test_guard_integrity.py` 161 passed (157 before: +3 from S-1's parametrization, +1 from W-2),
`tests/test_web_server.py` 166, both together 327. **CON-009 + CON-010 by their three function names:
collects 9, 9 passed, exit 0** — and the selector trap reproduced rather than trusted, `-k` by the
requirement id collecting 0 with pytest **exit 5**.

**One bookkeeping note the round reported rather than letting me discover it.** S-4's docstring rewrite
removed the sentence cycle 3's **m-2** was about (*"The third assertion is the one that…"*, which did not
describe the third assertion), replacing the ordinal with *"The member-restatement assertions are what
keep…"*. The round did **not** claim m-2 as fixed, because m-2 had no id in its contract — correctly, and
worth recording: m-2 is closed as a **by-product**, not as a tracked fix, and cycle 4 should confirm that
rather than take this sentence for it.

### [Build gate] **PASSED** at `098ecd91` (post-fix-3) — exit 0, and the +4 reconciles to fix 3 exactly

| figure | value |
|---|---|
| pytest exit code | **0** |
| executed | **8925** |
| passed | **8898** |
| skipped | **27** |
| failed / error | **0 / 0** |

Board lock taken and released, verified gone. **+4 against the post-fix-2 gate (8921)**, and the per-file
collection delta is `tests/test_guard_integrity.py` **157 → 161** and `tests/test_web_server.py`
**166 → 166**. Fix 3's own additions are exactly those four — three from S-1's per-member parametrization
and one from W-2 — while S-2, S-3, S-4, W-1 and B-1/B-2/B-3 changed assertions, declarations and prose
rather than adding tests, which is what a round of this shape should look like from outside. **+4 and
+4.**

Three gates on this card now, each reconciling to its own round: **8919** (`99782837`, +36 = the card's
own additions) → **8921** (`e26e5473`, +2 = fix 2's two new tests) → **8925** (`098ecd91`, +4 = fix 3's
four). Cumulative against main: **+42**, every one of them accounted for. The 27 skips are the standing
DB-mode skips throughout, unchanged.

---

### [Review 4/4] Score **7.65 — NOT CERTIFIED**. Report `meta/review/20261023T055002Z-CARD-264-cycle4.yml`

Baseline `10 − deductions` as in all four cycles: F-1 1.00, F-2 1.00, four minors 0.35 → **2.35**.
Trajectory **8.3 → 5.5 → 9.6 → 7.65**.

#### What the escalation was actually about: both certified, with the strongest evidence in this review

**S-1 ✓ CERTIFIED.** 4/4 mutants killed, FAIL at `:4020` (membership) and `:4022` (behaviour). And the
**counterfactual was reproduced under a plant trap** rather than quoted: the pre-fix file with all three
phrases rotted inline gives **157 collected, exit 0, zero failures** — the "157/157 green" that opened
this whole escalation, re-derived independently.

**S-2 ✓ CERTIFIED, and the independence question I planted was answered with a measurement.**
`S2-DROP-optional-underscore` is killed **solely** by the new equality at `:2369`, with the floor pin at
`:2356` still passing — exactly the claim, and the precise hole that previously survived. The predicate's
independence was probed over **13** constructed names (`__validate_x`, `___parse_x`, `_parse_`,
`Validate_x`, …): **13 agree, 0 disagree**, so the regex and the `removeprefix/startswith` predicate are
genuinely equivalent *and* genuinely separate — and all four shape narrowings make them disagree.
Counterfactual reproduced: pre-fix with `_?` dropped → **166 collected, exit 0, zero failures**.

**S-4, W-1, B-1, B-2, B-3 ✓ CERTIFIED**, each from constructed inputs rather than the fix round's report.
W-1's safety claim in particular: **zero** NxM matches in the three guarded paragraphs *and* zero in the
whole of `CLAUDE.md`, so the widening reds on nothing that ships — the claim verified, not accepted.

**m-2 CLOSED, confirmed from the file as instructed**: `grep -rn "The third assertion is the one"` returns
nothing in the worktree, and `:3736` now reads *"The member-restatement **assertions** are what keep…"* —
plural and non-positional, so the defect is gone rather than reworded around.

#### And the two new findings, both introduced by fix round 3, both in this card's own family

**F-1 (Important) — S-3's rewrite made a control *weaker than it was before*.** `MEASURED_CLAIM_MISSES[2]`
spans `:2924-2929`; only `:2924` and `:2927` carry keyed fragments. **Lines 2925, 2926, 2928 and 2929 are
keyed by nothing.** Measured: `GUT-CLAIM-MISS-2-middle-line` and `INV-CLAIM-MISS-2-reds-to-passes` each
**survive — exit 0, 0 FAIL, in both passes** — while the *identical* gut at `e26e5473` gives **exit 1, 3
failed of 157**. At fix 2 the key sat *on* the middle line; S-3 moved the text out from under its own
control. **Three sibling entries the same round touched are in the same state** (B-2's text, S-4's text,
B-3's text at two sites) — four inversions in total, each making an entry state the **opposite** of what
fix 3 measured, all surviving. The docstring at `:3342` claims *"a gutted or reworded declaration reds
here"*, and it does not. **ADR-0039/R1 ✗.**

**F-2 (Important) — S-3's narrowing overshoots, which is the mirror of the defect it repaired.**
`_is_type_expression` accepts **any** expression whose every `ast.Name` resolves in `dir(builtins)`,
strictly wider than *"a subscript or a tuple display"*. Reproduced via `_classify`: `[]`, `{}`,
`{'a': 1}`, `frozenset()`, `0`, `0.5` and **`int | None`** each return `('type-expression', '')` — accepted,
no defect, and none is a subscript or a tuple display. **`int | None` is the live one**, because the entry
is about the boundary-types paragraph. Worse, the new assert at `:3445` **pins** the under-wide wording
and `:3450`'s `assert "dir(builtins)" not in …[2]` **blocks** the now-correct widening. **ADR-0039/R3 ✗.**

**The correct bound is now known exactly, which it was not when S-3 was written:** *an expression that
parses, whose every name resolves in `dir(builtins)`, **and which is not a bare identifier chain*** — the
exclusion clause being what the original wording lacked and the narrowing over-corrected for.

#### The stalled check fires again, the family detector reads **1**, and this one is not a premise failure

`score_improvement = 7.65 − 9.6 = −1.95` (under the 0.5 floor) and
`findings_reduction = 0 − 2 = −2` (not a decrease). **Both conditions met.** Unlike the override at cycle
2, I am **not** arguing the premise away: cycles 3 and 4 reviewed the same card with one pure fix commit
between them, which is exactly the comparison the check is built for.

**FAMILY REGRESSION, signal present at streak 1 (escalation needs 2).** Both gating findings are
attributed to the previous fix by signal (b): fix 3's own `DECLARATIONS S-3 — declared-miss table
MEASURED_CLAIM_MISSES (entry 2 narrowed; CLAIM-MISS-2-GUTTED re-keyed…)` names the exact boundary both
findings land on. The counter does not fire, and the substance does:

> **[Family] The declared-miss tables' semantics were never decided, so each round re-derives them
> differently — and a round that edits an entry's wording silently moves the text out from under the
> control that keys it, or states a bound narrower than the guard it describes.**
> F-3..F-11 (cycle 2) → S-3/S-4 (spot-check) → F-1/F-2 (cycle 4), three rounds in the same mechanism.

**Aggregate round counter: 4** of the 6 that signal structural non-convergence. Two rounds left before
the discipline says the problem is structural rather than one more fix away.

#### Two gifts to whoever verifies next, and a G-6 note

The reviewer recorded that **R3's equality clause kills at `:3307`, not at the equality at `:3328`** —
both sides shrink together — so *"a spot-check re-deriving R3's equality clause must cite `:3307` or it
will find `:3328` passing."* That is the first time on this card a reviewer has written down how to
reproduce its own verdict against a named trap. And **O-1, an honest non-finding**: `_independently_derived`
shares the entire traversal and only the predicate is independent — measured — but every `_ADAPTERS`
widening that sheds a non-floor validator also sheds a floor one in today's tree, so the floor pin catches
it. Recorded with the measurement so the next cycle does not re-litigate it. Finally: the three U+2022 in
`src/nonogram/admin/pdf_generator.py:321` are **pre-existing and declared** (CARD-056, with its case at
`tests/test_book_difficulty_dots.py:784`) — noted so the next structural G-6 check does not re-raise them.

**Everything else holds.** AC-1..AC-6 all **MET** with a reproduction line each; AC-7 withdrawn, not
scored. **G-1..G-7 all ✓**, with G-6 verified structurally *and* cross-checked by an AST scan of every
`src/nonogram/**` string literal, and G-2 a **net widening** (the delta's one removed assertion is replaced
by two narrower ones plus a new positive arm). CON-009 + CON-010 **9 collected / 9 passed**, with the
selector trap reproduced rather than trusted (`-k` by the requirement id: **0 collected, exit 5**).
15 mutants, both passes, ANY-RED, all 19 `old` strings pre-counted as occurring exactly once, SHIPPED's
**exit code** read every time, and the exit-0-with-FAIL-cells reading occurring for **7 of 15** mutants —
each confirmed at exit 1 in the re-raising pass.

---

### [Owner decision 2026-10-23] One more fix, then cycle 5 — and the brief's first instruction is to **decide the semantics**

Owner chose option 1 of three: fix F-1 and F-2, then a cycle-5 certification. The alternatives and why
they lost, recorded because the one rejected is informative: **revert S-3 only** would have restored a
control that demonstrably worked (the identical gut reds at `e26e5473` with exit 1, 3 failed) and left the
original over-wide wording — a known defect in the *safe* direction, since an over-wide declared miss errs
toward "check it yourself" — but it does not re-key the three sibling entries fix 3 also unkeyed, so it is
a partial revert, not a clean one. **Land-and-route-to-CARD-266** was the cheapest and the family sentence
argues for it (a design route, not a polish one), but the owner has twice now preferred the honest tree
over the cheap close on this card.

**Aggregate round counter goes to 5 of the 6 that signal structural non-convergence.** One round of margin
left. Said plainly on the card because the next round, if there is one, is the board's own signal that the
problem is structural.

**What makes this round different from the three that failed in the same mechanism, and it is the whole
bet:** the brief's **step 0** is not a fix. It is to *decide and write down, in the file*, the contract
every `MEASURED_*` entry obeys — what an entry's text means (exactly what is measured, neither wider nor
narrower, both directions having now failed in the same entry in consecutive rounds), how an entry is
keyed (one rule, chosen with a stated reason over the alternatives), and what its case must do — and then
to **apply that rule to every entry in both files**, not only the four the findings name. A fourth local
patch produces a fifth finding; that is what the family sentence says and it is now three rounds of
evidence. The round is also told to verify by gutting **and inverting every line of every entry**, because
the reviewer enumerated four surviving inversions and there may be more.

**F-2's correct bound is handed over exactly, which is the thing neither previous wording had:** *an
expression that parses, whose every name resolves in `dir(builtins)`, **and which is not a bare identifier
chain***. The exclusion clause is a statement about `_classify`'s own branch order — `_IDENTIFIER_CHAIN`
is tested at `:3175` before `_is_type_expression` at `:3190`, which is *why* bare builtins are caught — so
it is precise rather than a hedge. And the two asserts fix 3 added to lock the wrong wording in (`:3445`
pinning the under-wide text, `:3450` blocking the correct widening) are named for removal.

**Four open minors fold into this round so it leaves nothing behind:** m-1 (`mentioned()` escapes the
canonical pyproject name, so a PEP-503-equivalent spelling walks through undeclared), m-A
(`_UNENFORCED_PHRASES` is a deny-list whose missing-member direction is the **harmful** one and is
undeclared, while `_PATH_SUFFIXES` got a declared bound for a harmless one), m-B (W-2's census is four not
three, and its *"no instance to key on"* reason is refuted by the same commit's own test keying `.md` on a
repo file), and m-4 (the docs quotation's colon replaced by a full stop inside the quotation marks).

**The guard's behaviour is explicitly out of bounds.** `_classify`, `_is_type_expression` and
`_IDENTIFIER_CHAIN` are correct and measured; every item is a declaration or a keying defect. The one
permitted exception is m-1's `mentioned()` normalisation, which the round must flag as a behaviour change
if it takes it.

## [One-way sync] Fix round 4's own notes, pulled from the worktree

Agent-owned text, copied verbatim from the card's worktree copy at the end of the round. The orchestrator's
own pre-gate of this round is the section *after* it.

## Worktree notes -- fix round 4 (`forge:fix`, auto), 2026-10-23, FINAL, on cycle 4 (7.65, NOT CERTIFIED)

Scope: `tests/test_guard_integrity.py`, `tests/test_web_server.py`,
`docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md`. `CLAUDE.md` untouched.

### SEMANTICS -- the decision this round starts with, because a fifth patch would produce a fifth finding

Rounds 2, 3 and a holds spot-check each found a defect in the same place: the `MEASURED_*` declared-miss
tables and their controls. Round 3 left one **weaker than it found it** -- at `e26e5473` gutting the
middle line of `MEASURED_CLAIM_MISSES[2]` gave exit 1, 3 failed of 157; at `098ecd91` the identical gut
survives at exit 0, 0 FAIL in both passes, because the round reworded the entry and the fragments its
case keyed on moved off the lines carrying the claim. So the semantics are now **written down**, as a
module-level block above `_MEASURED_TABLE_LINE_KEYS`, and applied uniformly.

1. **What an entry's text means.** An entry declares a bound on a guard: *the guard does not catch the
   shapes this text describes*. The text is held to be **exactly** what was measured. Wider claims a
   hole that does not exist; narrower leaves a real hole undeclared. Both directions have now occurred
   in one entry in consecutive rounds (cycle 1 over-wide -> round 3 under-wide -> round 4 the branch
   condition itself).
2. **How an entry is keyed -- decided: per source line.** *Every physical source line of every prose
   entry carries a required phrase, and the phrase is checked against **that** line.*
   `_MEASURED_TABLE_LINE_KEYS` holds one phrase per line; `_unkeyed_declaration_lines` reads the tables
   back out of the test source with `ast` and checks each phrase against the line it belongs to.
   Gutting a line, rewording it, moving a keyed phrase onto a neighbouring line of the same entry,
   adding a line or dropping one all red, **by line number**.
   *Why not the alternatives, by measurement and not by taste:* keying only the operative clause is
   cheaper and is what rounds 2 and 3 did -- a key that lives anywhere in the entry leaves every other
   line free text, which is exactly how both surviving mutants survived. Whole-entry equality is
   strictly stronger, and was rejected because it churns on every reword and reports the failure as the
   paragraph printed twice, with nothing saying which line moved; per-line keys fail with the line
   number and the phrase that left it, which is the diagnosis three rounds did not have.
3. **What an entry's case must do.** A committed case on the correct side: the declared shape
   constructed and shown **missed** by the deployed rule, and, where the entry excludes a neighbouring
   shape, that shape constructed and shown **caught**.

**Scope, and what is exempt.** Three `MEASURED_*` tables in `tests/test_guard_integrity.py` are not
this card's and are **not prose**: `MEASURED_CHECK_LOG_MISSES` and `MEASURED_MODULE_SCOPE_MISSES` carry,
per entry, the *source* they were measured on and are already run through the deployed rule by a
parametrised test -- the declaration **is** the measurement -- and `MEASURED_MODULE_SCOPE_SILENCES` is
an empty baseline held to an equality. The two exemption tables (`MEASURED_KEYWORD_SPANS`,
`MEASURED_PROSE_CITATIONS`) are held to equalities, which key every member by value. All five are
exempted **by name with a reason** in `_MEASURED_TABLES_KEYED_ELSEWHERE`, and
`test_every_measured_table_in_the_tree_is_accounted_for` enumerates every `MEASURED_*` assignment in
both files from the AST and requires each to be either keyed per line or exempted -- there is no third
state, so a sixth table added later is a red rather than a discovery for a fifth round.

### The complete enumeration, and the mutant that proves each

`_measured_table_names` walks both files' AST and finds **nine** `MEASURED_*` assignments: four keyed
per line (11 entries, **57 source lines**), five exempted with a reason.

| table | entries | source lines | every line keyed | proved by |
| --- | --- | --- | --- | --- |
| `MEASURED_CLAIM_MISSES` | 3 | 1 + 4 + 13 = 18 | yes | `F1-GUT-SHAPE`, `F1-INVERT-STR`, `F2-DECL-NARROW`, `B2-GUT` |
| `MEASURED_DEPENDENCY_CLAIM_MISSES` | 3 | 3 + 3 + 10 = 16 | yes | `S4-GUT` |
| `MEASURED_TIMEOUT_CLAIM_MISSES` | 2 | 2 + 3 = 5 | yes | the 216-variant sweep below |
| `MEASURED_UNENFORCED_PHRASE_MISSES` (new, m-A) | 1 | 9 | yes | `MA-GUT` |
| `MEASURED_AST_SWEEP_MISSES` (`test_web_server.py`) | 3 | 6 + 1 + 2 = 9 | yes | `B3-INVERT-WEB` |
| `MEASURED_KEYWORD_SPANS` | -- | -- | exempt: equality over the spans that exist | -- |
| `MEASURED_PROSE_CITATIONS` | -- | -- | exempt: equality over the sites that exist | -- |
| `MEASURED_CHECK_LOG_MISSES` | -- | -- | exempt: each entry carries its measured source | -- |
| `MEASURED_MODULE_SCOPE_MISSES` | -- | -- | exempt: same shape | -- |
| `MEASURED_MODULE_SCOPE_SILENCES` | -- | -- | exempt: empty baseline, held to an equality | -- |

**The exhaustive measurement** (every line, not only the four the findings named): for each of the 57
lines, three mechanical mutations -- gut the line's literal, drop one load-bearing word of its keyed
phrase, alter one character of it -- plus, for every line after an entry's first, a swap with the line
above. **216 variants, 0 survived, 0 misattributed**: every gut/reword defect names the mutated line
number. Run against the deployed `_unkeyed_declaration_lines` rather than a copy of it. (An earlier
pass of this sweep reported 55 survivors and the sweep was wrong, not the control: its "invert" built
`"NOT" + word`, which still *contains* the keyed phrase as a substring. Recorded because a
measurement instrument that cannot fail is this card's subject one level up.)

`tests/test_web_server.py`'s table is keyed **from** `tests/test_guard_integrity.py`, so the table is
not copied (G-3) -- the same mutual arrangement that module's docstring opens with. A `#:` block above
the table points at the contract, so a reader of either file finds it.

### F-1 -- the control that was weaker than before round 3

The docstring at the old `:3342` claimed "a gutted or reworded declaration reds here". It did not.
That claim is **narrowed to what the test holds** -- the pairing of each case's constructed shape with
the sentence that declares it -- and the per-line claim now sits where it is true, naming
`_unkeyed_declaration_lines` and `TestTheDeclaredMissTables`. The two measured survivors and the three
siblings in the same state all red now, and `MA-GUT`, `F1-GUT-SHAPE`, `F1-INVERT-STR` and
`B3-INVERT-WEB` red at **exactly one** assert -- `:4707`, the keying control -- which is the point:
nothing else in the suite can see them.

### F-2 -- the bound restated as the branch condition, clause by clause

Round 3's wording ("a false type claim written as a subscript or a tuple display") is **narrower than
the guard**. Measured with `_classify(span, *TestClaudeMd_EverySymbolItNamesExists._authorities())`:
each of `[]`, `{}`, `{'a': 1}`, `frozenset()`, `0`, `0.5` and `int | None` returns
`('type-expression', '')` -- accepted, no defect -- and none of the seven is a subscript or a tuple
display. `int | None` is the live one, because the entry is about the boundary-types paragraph.

The restated bound:

> *a span that reaches `_is_type_expression`: not read as a path (no trailing `/` and no
> `_PATH_SUFFIXES` suffix), not read as a keyword, and not a bare identifier chain -- and which then
> parses as an expression whose every `ast.Name` resolves in `dir(builtins)`.*

* **"parses as an expression whose every `ast.Name` resolves in `dir(builtins)`"** -- that function's
  body, verbatim; the seven spans above are the measurement.
* **"not a bare identifier chain"** -- branch order, not a hedge: `_classify` tests
  `_IDENTIFIER_CHAIN.fullmatch(span)` before `_is_type_expression(span)`, which is *why* a bare builtin
  is caught. Measured: all seven of `bool`, `int`, `str`, `list`, `tuple`, `dict`, `frozenset` return
  `('symbol', 'names no symbol defined in src/nonogram')`.
* **"not read as a path, not read as a keyword"** -- the two arms the brief's version of this bound
  omits; see the disagreement below. Measured: `_is_type_expression("list[bool].md")` is `True` and
  `_classify` returns `('path', 'names no file in the repo')`, i.e. **caught**; both
  `MEASURED_KEYWORD_SPANS` members return `('keyword', '')`.

Both asserts round 3 added are gone: the one pinning `"subscript or a tuple display"` and
`assert "dir(builtins)" not in MEASURED_CLAIM_MISSES[2]`, which blocked the now-correct widening. The
case carries twelve shapes on the missed side (`int | None`, `0`, `0.5`, `[]`, `{}`, `{'a': 1}`,
`frozenset()` added), the seven bare builtins and the path and keyword arms on the caught side.
`_classify`, `_is_type_expression` and `_IDENTIFIER_CHAIN` are **untouched**.

### The fifth disagreement with the brief, stated rather than worked around

The brief gives F-2's correct bound as *"an expression that parses, whose every name resolves in
`dir(builtins)`, and which is not a bare identifier chain"*, and calls the exclusion clause a statement
about the code's own branch order. It is -- but it names **one** of the **three** arms that run first.
`_classify` tests the path arm (trailing `/`, or any `_PATH_SUFFIXES` suffix) and the keyword arm
*before* `_IDENTIFIER_CHAIN`. Measured: `_is_type_expression("list[bool].md")` is `True` (it parses,
`list` and `bool` are both in `dir(builtins)`, it is not an identifier chain) and `_classify` returns
`('path', 'names no file in the repo')` -- **caught**. So the brief's three-clause bound would declare
a hole that does not exist, in the same direction as cycle 1's over-wide wording and for the same
reason: it reads the arm it is interested in and not the ones above it. Four rounds, four briefs right
about the defect and one clause off about the fix.

### m-1 -- normalised, which is a behaviour change, and taken deliberately

`mentioned()` now treats runs of `-`, `_` and `.` as one separator (PEP 503) instead of `re.escape`-ing
pyproject.toml's canonical name whole. **This is the round's only behaviour change.** Measured before:
`psycopg2-binary` -> 1 defect, `psycopg2_binary` -> `[]`, `psycopg2.binary` -> `[]`. Case and quoting
were already independent (`PSYCOPG2-BINARY` -> 1, `` `psycopg2-binary` `` -> 1), so the comment's
three-part claim was two-thirds true; it is now true as written. Closed rather than declared because
the extras arm is **deny-side**: a spelling it cannot see is a missed catch, not a false positive.

No new false positive: the two runtime names are `pillow` and `numpy`, neither carries a separator, so
the pattern they generate is byte-identical to the old one -- asserted in the control -- and the live
paragraph is asserted clean in the same test. `M1-REVERT` (`"[-_.]+".join(` -> `"[-]".join(`, the old
behaviour for a hyphenated name) reds at `:4280`.

### m-A -- the bound the harmful direction needed

`_UNENFORCED_PHRASES` is a **deny-list over free prose**, so a member it does not carry is a **missed
catch**. Six synonyms measured missed (`_unenforced_claims` -> `[]`): "currently unenforced", "not
wired up yet", "still pending", "present but inert", "advisory only", "checked nowhere". Declared in
the new `MEASURED_UNENFORCED_PHRASE_MISSES`, with a case on the miss side per synonym, each synonym
also shown **caught** when the deny-list's own first member replaces it (so the misses are the phrasing
and not an inert rule), and the entry's enforced half measured too: the citation rule selects on
"timeout"/"deadline", so a claim reworded past the deny-list is still a sentence that must name an
existing test. Round 3 gave `_PATH_SUFFIXES` -- whose incompleteness is **harmless**, its reader being
default-deny -- a declared bound, and gave this one nothing; both comments now name their direction and
say why the other's argument does not transfer.

### m-B -- both the count and the reason, and the figure is now keyed

(i) The census is **four**, not three. Measured over the 24 backtick spans the guarded paragraphs
carry: `.py` 5, `.toml` 3, and `.md`, `.yml`, `.cfg`, `.txt` **zero each**. (ii) The reason ("no
instance in the guarded paragraphs, so nothing to key a control on") is refuted by the same commit's
own test, which keys `.md`'s control on `docs/GENERATION_ALGORITHM.md` -- a **repo file**, not a span --
and `_repo_paths()` holds 1 `.yml` and 8 `.txt` files for the same device. Only `.cfg` has no instance
anywhere.

One step past the brief, deliberately: *correcting* a figure in a comment that nothing reads reproduces
this card's own disease one file over. The census is two parseable lines in the comment, and
`test_the_path_suffix_census_is_the_one_this_comment_states` parses them out of this module's own source
and re-derives every figure from CLAUDE.md's guarded paragraphs and from `_repo_paths()`. The
repo-file half is a **presence** (".cfg none | every other suffix at least one") rather than counts,
because counts move with every file anyone adds and would make it a churn alarm. `MB-CENSUS`
(`.md 0` -> `.md 1`) reds at `:3991`. The load-bearing **direction** claim is unchanged and still held
by `test_a_suffix_outside_the_table_is_denied_not_accepted`.

### m-4 -- the quotation extended to the colon's clause

The page ended the quotation *"...every entry point in the tree."* where `src/nonogram/__init__.py:71`-`:73`
reads *"...in the tree: ``admin/`` is a third one, outside ADR-0019's scope as written."* -- the
source's colon replaced by a full stop **inside** the quotation marks, which stops the sentence just
before the clause that names the third adapter. Extended to the colon's clause rather than elided,
since that clause is the page's own subject, and the citation now carries the line range. The page's
other quotation (`web/server.py:9`-`:10`) was re-verified accurate at cycle 3 and is untouched.
**No test**: `grep -rn "09-the-three-inbound-adapters" tests/` finds nothing, and a guard that checks a
how-it-works page's quotations against their sources is a different card.

### Mutants -- committed instrument only, both passes, ANY-RED

`tests/kill_matrix.py`, target `tests/test_guard_integrity.py`, selection the whole file.
**Domain of every figure below: 210 `ast.Assert` nodes** (the target file's node count, carried
separately from the 167 collected tests); child instrumentation off.

* **Trap (a)**: every mutant's `old` pre-counted -- **each occurs exactly once**, and every edit is
  line-count-preserving (delta 0 for all nine).
* **Trap (b)**: SHIPPED's **exit code read, not only its cells** -- `pytest exit 0`, `0 FAIL of 210
  reached`, 167 collected, in **both** passes. `tests/test_guard_integrity.py` contains no
  `pytest.raises`, so the selection cannot hit the swallowed-raise shape.
* SHIPPED re-run between mutants, held cell-for-cell by the instrument's own gate.

| mutant | recording | re-raising | FAIL cells |
| --- | --- | --- | --- |
| `F1-GUT-SHAPE` gut `MEASURED_CLAIM_MISSES[2]`'s "never compared against the annotations" line | exit 0, 210 reached, 1 FAIL | exit 1, 210 reached, 1 FAIL | `:4707` |
| `F1-INVERT-STR` "`str` reds as a symbol" -> "passes as a symbol" | exit 0, 210, 1 FAIL | exit 1, 210, 1 FAIL | `:4707` |
| `F2-DECL-NARROW` entry 2's head back to "written as a subscript or a tuple display" | exit 0, 210, 3 FAIL | exit 1, 207, 2 FAIL | `:3810`, `:3817`, `:4707` |
| `B2-GUT` gut `MEASURED_CLAIM_MISSES[1]`'s continuation-block line | exit 0, 210, 2 FAIL | exit 1, 200, 2 FAIL | `:3731`, `:4707` |
| `S4-GUT` gut `MEASURED_DEPENDENCY_CLAIM_MISSES[2]`'s "live rather than hypothetical" line | exit 0, 210, 2 FAIL | exit 1, 210, 2 FAIL | `:4232`, `:4707` |
| `MA-GUT` gut `MEASURED_UNENFORCED_PHRASE_MISSES`' "measured to return []" line | exit 0, 210, 1 FAIL | exit 1, 210, 1 FAIL | `:4707` |
| `M1-REVERT` `"[-_.]+".join(` -> `"[-]".join(` | exit 1, 208, 1 FAIL | exit 1, 208, 1 FAIL | `:4280` |
| `MB-CENSUS` census line `.md 0` -> `.md 1` | exit 0, 210, 1 FAIL | exit 1, 207, 1 FAIL | `:3991` |
| `B3-INVERT-WEB` `test_web_server.py` "is **caught**: CPython folds" -> "is **missed**:" | exit 0, 210, 1 FAIL | exit 1, 210, 1 FAIL | `:4707` |

**9 of 9 killed, ANY-RED, in both passes.** Seven of the nine had a recording-pass **exit 0** while the
matrix recorded FAIL cells -- the reading the discipline warns about, and the reason the per-mutant
figure above states the pass, the exit code and the denominator together.

### Guardrails

* **G-1:** `CLAUDE.md` untouched. `git diff -U0 d90753df HEAD -- CLAUDE.md` -> exactly three
  single-line hunks, `:46`, `:48`, `:50`. `shasum -a 256 -c` confirms it was not touched by any plant.
* **G-2:** the web guard not weakened; `_WEB_SOURCES`' and `_DOMAIN_VALIDATORS`' non-empty assertions
  untouched. Selections, collected **and** passed: `-k "CON-010"` -> **0 collected, pytest exit 5**
  (the measured trap); `-k "TestWebServer_BindsLoopbackOnlyByDefault or
  test_the_corpora_are_large_and_cover_every_declared_signal or
  test_every_cross_origin_or_foreign_authority_request_is_refused or
  test_every_same_origin_or_metadata_free_request_is_served"` -> **9 collected, 9 passed, exit 0**
  (CON-009's six plus CON-010's three, named individually in the `-rA` listing). Whole-file runs:
  `tests/test_web_server.py` **166 collected, 166 passed, exit 0**; `tests/test_guard_integrity.py`
  **167 collected, 167 passed, exit 0**.
* **G-3:** no second copy. The contract's keys read `tests/test_web_server.py` from disk instead of
  restating its table; the census control re-derives from CLAUDE.md and `_repo_paths()`; `mentioned()`
  still reads pyproject.toml through `_declared_distributions`.
* **G-4:** `nonogram_poc` never named or touched; the instrument refuses such an edit by construction.
* **G-5:** stdlib only -- `ast`, `re`, `pathlib`, all already imported in the files that use them.
* **G-6:** no `src/` path in the diff. `git diff --name-only d90753df HEAD` lists six files, none under
  `src/`; the working tree adds only the three scoped files plus this card.
* **G-7:** no timing measurement taken, no duration reported.
* Plants: manifest built **up front** (`shasum -a 256` over all four files), `cp -p` backups, and
  restoration verified three ways after the run -- `shasum -a 256 -c` (4/4 OK), `diff -q` on both test
  files (identical), and `git status --porcelain` (only the three scoped files and this card). Every
  pytest, script and mutant ran with `NONOGRAM_FULL_SUITE_LOCK=/tmp/card264-fix4.lock`, so the board's
  own lock was never read, written or created; the instrument confirmed the override in every run.

### Not touched, named so the next reader does not look for them

* `CLAUDE.md` (G-1), `tests/test_cli.py` (byte-identical to main, folded to CARD-265),
  `tests/test_timeout.py`, `tests/test_sourcing_image.py`, anything under `src/`.
* **No control for the substring arm** in `tests/test_web_server.py` -- its zero unique detection is
  measured by exhaustive partition and declared at `:2227`-`:2241`.
* `CLAUDE.md:50`'s timeout sentence -- refuted at cycle 2; its two checkpoints are both pinned.
* The `check_deadline` census ("six sites") -- **CARD-266's**, routed with its measurement.
* `tests/test_timeout.py:479`-`:485`'s `_blind_propagation` -- **CARD-278's**.
* `src/nonogram/admin/pdf_generator.py:321`'s three U+2022 -- pre-existing from CARD-056, declared at
  `tests/test_book_difficulty_dots.py:784`.

## [Orchestrator pre-gate] Fix round 4, 2026-10-23 — the round's own figures re-derived, not accepted

Run before the commit, in the worktree, with `NONOGRAM_FULL_SUITE_LOCK` redirected to a scratch path, so
the board's own lock was never read, written or created.

**1. The seven tests the FIXED ids name, selected by explicit node id.** Not by `-k`: this card has
recorded twice that a hand-written `-k` selecting nothing exits 0 and reads as a pass, and a node id that
does not exist exits 4 instead of passing silently. **7 collected, 7 passed, exit 0**, each named
individually in the `-rA` listing:

* `TestTheDeclaredMissTables::test_every_line_of_every_declared_miss_entry_is_keyed`
* `TestTheDeclaredMissTables::test_every_measured_table_in_the_tree_is_accounted_for`
* `TestTheDeclaredMissTables::test_the_line_keying_control_reds_on_a_gutted_or_inverted_line`
* `TestClaudeMd_EverySymbolItNamesExists::test_the_rule_names_what_it_cannot_see` (F-2's restated bound)
* `TestClaudeMd_TheDependencyClaimMatchesPyproject::test_a_member_is_caught_however_it_is_spelled` (m-1)
* `TestClaudeMd_TheTimeoutClaimNamesItsTest::test_the_phrase_rule_names_the_synonyms_it_does_not_carry` (m-A)
* `TestClaudeMd_APlantedDeadSymbolReds::test_the_path_suffix_census_is_the_one_this_comment_states` (m-B)

**2. Both touched files whole, counts compared against the round's claims.**
`tests/test_guard_integrity.py` → **167 collected, 167 passed, exit 0**; `tests/test_web_server.py` →
**166 collected, 166 passed, exit 0**. Both figures match the round's notes exactly.

**3. Two of the nine mutants re-derived with an instrument written here, not with `tests/kill_matrix.py`.**
The point of a pre-gate on this card is to check the instrument's claim rather than re-run it, so the
spot-check is a separate script that honours both measured traps explicitly: every `old` **pre-counted**
(each occurs exactly once) and every edit **line-count preserving** — trap (a) — and the SHIPPED
baseline's **exit code read, not only its FAIL cells**, refusing to measure against a red baseline —
trap (b).

| | exit | failed / passed | FAIL cell | the round claimed |
| --- | --- | --- | --- | --- |
| SHIPPED | 0 | 0 / 167 | — | clean |
| `MB-CENSUS` (`.md 0` → `.md 1`) | 1 | 1 / 166 | `:3991` | `:3991` ✓ |
| `F1-GUT-SHAPE` (gut `MEASURED_CLAIM_MISSES[2]`'s shape line) | 1 | 1 / 166 | `:4707` | `:4707` ✓ |

Both killed, each reddening at **exactly** the cell the round's table names and at no other — which is
the load-bearing half of the round's argument, since `:4707` is the new per-line keying control and
nothing else in the suite can see those two defects. The target file was restored from a `cp -p` backup
and the restore verified by `sha256` against the pre-run digest (`eeedc7da…`); `git status --porcelain`
after the run lists the same four paths as before it.

**4. G-6 re-verified at the gate rather than taken from the round's own note:** no `src/` path appears in
the working diff — the four modified paths are the three scoped files plus this card.

### One thing the pre-gate found that the round did not report

**An explicit `-q` on this project's pytest silently removes the pass/fail count line.** `pyproject.toml:89`
already sets `addopts = "-q"`, so a `-q` written on the command line **stacks to `-qq`**, and at that
verbosity pytest prints no `N passed` line at all. Measured both ways on the same file: default run → the
count line present; `-qq` → absent, exit code unchanged. The first version of the spot-check script ran
`pytest -q --no-header` and parsed `N passed` out of the output; it matched nothing, and the mutant rows
read `passed=?` while the exit codes and FAIL cells were correct. Harmless here because the
exit code was read too — trap (b)'s discipline catching its own instrument — but it is this card's family
one level out: **evidence that is absent reads the same as evidence that is zero.** Every figure above
comes from a non-quiet run. Routed to the backlog beside the two sibling items (`-k` selecting nothing,
and green-with-skips being indistinguishable from fully verified).

## [Gate] Post-fix full suite at `8727e519` — PASSED, and the first attempt's lock provenance was mine to lose

**Result: exit 0, 8931 executed, 8904 passed, 27 skipped, 0 failed, 0 error.** No duration recorded (G-7).

**Reconciliation, and it closes exactly:** the suite's executed count goes **8925 → 8931, +6**, against a
per-file delta of `tests/test_guard_integrity.py` **161 → 167 (+6)** and `tests/test_web_server.py`
**166 → 166 (+0)**. The six are the six test functions the diff adds, enumerated from it by `ast` rather
than counted by eye: three in the new `TestTheDeclaredMissTables`, and
`test_the_path_suffix_census_is_the_one_this_comment_states`,
`test_a_member_is_caught_however_it_is_spelled`,
`test_the_phrase_rule_names_the_synonyms_it_does_not_carry` into existing classes. The **seventh** FIXED
id is a *modified* existing test (`test_the_rule_names_what_it_cannot_see`, F-2's restated bound), so it
adds no count — which is why the delta is 6 and not 7, and the figure that would otherwise look short.
Cumulative for the card: **+48** across four rounds, every one accounted for. 27 skips throughout, the
standing DB-mode skips.

### The gate was run twice, and the first run's record is the finding

The first run of this gate was **green and identical** — exit 0, 8904 passed, 27 skipped, 0 failed — and
it held **no lock at all**, because the orchestrator never wrote one. The division of labour is correct
and documented (`tests/README.md:335-339`: *"every gate script writes that one file, and
`tests/full_suite_lock.py` reads that one file"*; the module docstring explains why identity is
`worktree:` rather than a pid — the script writes the lock and launches pytest as a **child**, so no pid
in the file is ever the pid of the reading process). Pytest's hook only *reads*. I ran pytest and skipped
the write, then reported the gate as "board lock taken for real".

**Nothing here could have caught that, and the reason is structural:** `current_verdict()`'s first branch
is `if text is None: return True, None`. A missing lock is the normal case for every impact-scoped run and
every agent's selection, so it cannot be an error, and the guard's subject is a **foreign** lock — from
inside a run, *"no lock at all"* and *"my own lock, correctly released"* are the same observation. This
board has already paid for the near-miss once: `meta/kanban/suite-timing.log` records a gate that
*"spent part of its life holding nothing"* after a late `rm -f "$LOCK"`, and CARD-255's docstring opens on
CARD-225's gate reporting two failures that were not the tree.

**Re-run rather than argued through.** The exclusivity of the first run is in fact well supported — two
checkouts exist, no other pytest was running, and the board's known contention canary (`test_web_upload.py`'s
machine-wide temp-dir sweep, on the backlog precisely because it reds when two worktrees run at once)
passed — but that is an argument, and this card's entire subject is evidence that cannot fail. A gate
claiming protection it did not have is that defect committed in the gate of the card about it. So the
suite was run again with the lock written as `tests/README.md` specifies — `holder`, `at`, absolute
`worktree:`, `commit: 8727e519` — the `trap` armed where the lock became ours and disarmed in the same
breath as the `rm -f`, and the file verified gone afterwards. **The second run matched the first cell for
cell**, which is the outcome that makes this a provenance defect and not a measurement one.

**Not asserted either way:** whether this card's *earlier* gates took the lock. `dispatcher.state` records
"board lock taken and released" at `99782837`, written by an earlier session, and that is not verifiable
from here. Routed to the backlog with the fix stated as **default-deny** (ADR-0039/R2, the same shape the
lock guard already applies to an unresolvable `worktree:`): a full-suite run must be *requirable* to be
covered, so a gate that forgot is a red rather than a green with a footnote — plus the cheap half, that a
gate's evidence line should quote the lock it wrote.

## [Cycle 5] 7.6 — NOT CERTIFIED, and the two signals that have never both fired on this card before

Report `meta/review/20261023T103148Z-CARD-264-cycle5.yml` (synced; `yaml.safe_load` clean, 15 keys).
**0 critical, 2 important, 2 minor.** Score trajectory **8.3 → 5.5 → 9.6 → [8h spot-check failed] → 7.65 → 7.6**.

### What CONVERGED, and it is most of the round

The mechanism fix 4 decided and built **held under independent re-derivation**. The reviewer could not
break the per-line keying, the completeness arm, the exemptions or the enumeration:

* An independent **197-variant** per-line sweep over the **52 keyed lines the round's named mutants do not
  cover** → 0 survivors, 0 misattributions, run against the deployed `_unkeyed_declaration_lines`.
* A **planted sixth `MEASURED_*` assignment** reds `test_every_measured_table_in_the_tree_is_accounted_for`
  at `:4731` naming the plant — so the "no third state" claim **can fail**, which is the round's central one.
* **All five exemption reasons are TRUE**, each verified at its cited control, and the exemption table is
  itself held to an equality (`found == keyed | exempt`, 10 == 10; a stale exemption or a dropped table
  both break it).
* `_classify` is **default-deny** by measurement (five unanalysable shapes all refused), and
  `_measured_table_names` found the plant under both its original and a renamed id.
* **m-1 VERIFIED SOUND.** The byte-identity claim is independently confirmed — for both runtime names the
  new pattern equals `re.escape(name)` exactly; of 11 declared distributions only `psycopg2-binary` and
  `pytest-playwright` widen, both extras-only, i.e. deny-side. No false positive constructible on real
  prose. The round's one behaviour change is good.
* **The fifth disagreement: the ROUND IS RIGHT and the brief — mine — was wrong.** Re-derived
  independently: `_classify` runs **three** arms before `_is_type_expression`, and
  `_is_type_expression("list[bool].md")` is `True` while `_classify` returns `('path', …)` — caught. The
  brief's three-clause bound would have declared a hole that does not exist. The clause the round added
  *against* the objection is also controlled: deleting the path arm is killed with 6 FAIL cells.
* m-B's census re-derived **in a new domain** (the reviewer's own CLAUDE.md parse + `git ls-files`): 24
  backtick spans, `.py` 5, `.toml` 3, the other four zero each — "four, not three" is right. m-4's
  quotation verified by hand against `src/nonogram/__init__.py:71-73`, exact including the colon's clause.
* G-1..G-7 all clear, **0 banned codepoints** across all six changed files, additions enumerated by AST
  (6 new tests, 3 new helpers/tables, nothing removed), AC-1..AC-6's named tests all selected by node id
  and passed. Baselines 167/167 and 166/166, final post-check 333/333, exit 0. Hygiene verified three ways;
  the board's own lock never read, written or created.

### What did NOT converge — and it is the family, one level out

**F-001 (Important) — `tests/test_guard_integrity.py:3157`: the contract's own clause 2 is wider than any
case or mechanism holds.** Clause 2 claims *"gutting a line, inverting it, adding one, deleting one, or
moving a keyed phrase … all red"*. Three measurements refute it:

1. **A delete-the-mechanism mutant SURVIVES.** `:3157` (`if span != len(element_keys):`) is the only code
   implementing the add/delete directions. Disabling it → kill_matrix **exit 0, 210 reached, 0 FAIL**, and
   at test level **167 collected, 167 passed, exit 0**. `_unkeyed_declaration_lines` has no reader outside
   the file, so that is the complete reading.
2. **The "adding one" direction is constructed nowhere** — the test's own docstring enumerates four ways,
   the contract claims five, and the round's 216-variant sweep cannot reach it because none of its four
   mutations changes an entry's line count. The reviewer's 197-variant replication inherited the same
   blind spot.
3. **The "deleting one" direction is silent on the realistic edit** — a declaration line dropped
   *together with its key phrase* gives verdict `[]` with every value-read assert still passing, and the
   floor pin `assert keyed >= 45` reads 56 against a measured 57, i.e. **11 lines of slack**. The clause
   that can silently leave is the path/keyword arm **this round just added as F-2** — so the contract
   permits the entry to shrink back to exactly the round-3 wording round 4 exists to correct.

**Why the round missed it, and it is my brief's fault as much as the round's:** 8 of its 9 mutants mutate
declaration text or a comment figure and the 9th reverts a behaviour change — **none deletes a mechanism
its claims name.** That is a standing rule of this board (*"a fix must mutate by DELETING each mechanism
its claims name; a mutant that only breaks what the fix added certifies the addition and says nothing
about whether the mechanism is load-bearing"*), and `grep` over the fix-4 brief confirms **the brief did
not restate it**. I restated it to the cycle-5 reviewer and not to the round that was writing the controls.

**F-002 (Important) — `meta/kanban/cards/CARD-264.md:1604`: "The complete enumeration" says nine/four/11
where the tree holds ten/five/twelve.** Refuted by the deployed enumerator *and by the card's own table
three lines below* (ten rows, five keyed, 3+3+2+1+3 = 12 entries, 57 lines). The arithmetic names the
cause: 9/4/11 is exactly the tree **before m-A added `MEASURED_UNENFORCED_PHRASE_MISSES` in this same
round** — the headline figure predates the round's own last edit and was never recomputed. It is the
shape this card was opened for: a subset presented as complete.

**Minors (non-gating):** m-4 adds an untested line-number citation into a churning docstring in the same
round that *removed* line-number citations from this page for being untestable; and AC-7 is still live in
the AC block naming a test that exists in no file, while its withdrawal is recorded honestly at `:17` and
`:1109` — presentation, not a weakening.

### Both escalation checks fire, and this time neither premise fails

* **STALLED CHECK — FIRES, not overridden.** Δscore **7.65 → 7.6 = −0.05** (< `min_improvement` 0.5) **AND**
  Δgating findings **2 → 2 = 0** (≤ 0). Cycles 4 and 5 reviewed the same card with **one pure fix commit**
  between them, which is exactly the comparison the check is built for — unlike cycle 2, where the premise
  failed and the override was taken. The literal marker is therefore written, because it is now true:
  **⚠ improvement stalled**
* **FAMILY REGRESSION CHECK — FIRES at streak 2.** Cycle 4's two gating findings were attributed to fix 3;
  cycle 5's two are attributed to **fix 4**, and both land in one family. `family_regression: on` → escalate
  with the family and let the owner pick the source.

**The family sentence, updated by this cycle — the code converged and the record did not:** *each round
now builds the mechanism correctly and then writes its claims about the mechanism before its own last
edit, without re-deriving either against the final tree.* Clause 2's five directions and the 9/4/11 census
were both written before m-A landed. That is a different defect from the one cycle 4 described, and it is
cheaper to fix — but it is the fifth consecutive round in the family, and the aggregate round counter
stands at **5 of the 6** that signal structural non-convergence.

**Escalated to the owner.** Both fixes are small and local. The reviewer's own condition on a sixth round:
its matrix **must** include an add-a-line mutant and a co-edited-drop mutant, or it reproduces this cycle.

## [Owner decision 2026-10-23, cycle 5] Fix both, then a review scoped to the two fixes — and the brief carries what the last one did not

Options put to the owner were: (1) fix both then a **narrow** re-entry review of only those two fixes;
(2) fix both and merge on the gate with the last edit recorded as reviewer-uncertified, which this board's
own rule permits; (3) fix both plus a **full** cycle 6; (4) merge as-is and route both findings to a new
card. **The owner chose (1).** Either way the aggregate round counter reaches **6 of 6**; what (1) buys
over (2) is that the last edit is seen by a reviewer, on the one card where four consecutive rounds each
introduced a defect — and what it saves over (3) is re-reviewing content cycle 5 already re-derived
independently and found sound.

### F-001 — the fix is the second of the reviewer's two options, because the first only hides it

The reviewer offered *"narrow clause 2 to the four constructed directions, **or** add the two missing cases
and replace `assert keyed >= 45` with an equality"*. Narrowing would make the claim true and leave the
`:3157` mechanism with **no failing control** and the entry still free to shrink back to the round-3
wording. So:

1. **Add the two missing cases.** An **add-a-line** case — an unkeyed continuation line appended to the
   fabricated entry, which the deployed verdict must name — and a **co-edited-drop** case — a declaration
   line removed *together with its key phrase*, the realistic edit that is silent today.
2. **Replace the floor pin with an equality.** `assert keyed >= 45` reads 56 against a measured 57: eleven
   lines of slack, and the slack is what lets the drop pass. The equality is **5 tables / 12 entries / 57
   source lines**, re-derived through the deployed enumerator and not copied from this sentence.
3. **The control that proves it:** with `:3157` (`if span != len(element_keys):`) disabled, the new cases
   must **red**. That is the delete-the-mechanism mutant cycle 5 ran as `M2-SPAN-EQ-DROP` and found
   surviving at 167/167 green.

### F-002 — recompute, and name the door

"The complete enumeration" says **nine/four/11**; the tree holds **ten/five/twelve**, which the card's own
table three lines below already states (3+3+2+1+3 = 12 entries, 18+16+5+9+9 = 57 lines). Re-derive every
figure in that section **through the deployed enumerator** against the final tree, and say which door it
came through. The cause is on the record: 9/4/11 is the tree before m-A added
`MEASURED_UNENFORCED_PHRASE_MISSES` **in the same round**, so the headline predates the round's own last
edit. The round must also restate what its **216-variant sweep does not cover** — none of its four
mutations changes an entry's line count, which is exactly the blind spot F-001 lives in, and the cycle-5
reviewer's own 197-variant replication inherited it.

### What the fix-4 brief omitted, stated here as the round's first instruction

**A fix mutates by DELETING each mechanism its claims name.** A mutant that only breaks what the fix
*added* certifies the addition and says nothing about whether the mechanism is load-bearing. Fix 4 ran
nine mutants: eight mutate declaration text or a comment figure, the ninth reverts a behaviour change, and
**none deletes a mechanism**. The rule is a standing one on this board and `grep` confirms the fix-4 brief
did not restate it — it was restated to the cycle-5 reviewer instead, which is why the reviewer found
F-001 and the round did not. **This round's matrix must include an add-a-line mutant and a co-edited-drop
mutant**, which is also the cycle-5 reviewer's own stated condition on any further round.

### And the class, not the instance

Clause 2 is one claim that enumerates directions. **Enumerate every claim in this card's diff that says a
control "reds", "survives" or that some list of directions "all red", and require a constructed case per
direction or narrow the claim to what is constructed.** Cycle 5 named one sibling in passing — the census
comment's *"Dropping `.md` or `.py` reds, dropping `.yml` survives"* — and a brief that names a sibling
gets that sibling checked while a brief that names the class gets every arm checked.

## [Orchestrator] Cycle 5's two minors — one was already fixed in the copy that survives, and that is itself the finding

**F-004 (AC-7 left live naming a test that exists nowhere) is a CARD SYNC artifact, not a stale AC.** The
reviewer read `meta/kanban/cards/CARD-264.md` **in the worktree** — the agent-owned copy — where AC-7 is
still live and unmarked at `:118`. In **main's** copy, the orchestrator-owned one that survives the merge,
AC-7 has been struck through and marked *"WITHDRAWN FROM THIS CARD 2026-10-23 — moved to CARD-265"* since
the fold, with the byte-identical-resolution evidence beside it. So the finding is accurate about the file
it was pointed at and does not describe the card that merges.

**What was genuinely stale in main's copy**, and is now fixed, is the *other* half: the
`## [Owner decision 2026-10-22] AC-7 stays here` heading, which the 2026-10-23 fold superseded and which
contradicted the AC block four screens above it. It is now marked `<!-- SUPERSEDED 2026-10-23 -->` with a
blockquote naming what replaced it, and the section is **kept** rather than deleted: why AC-7 was *not*
folded a day earlier is honest history, it just no longer states what is true.

**The general shape, routed to the backlog.** The AC block, `Touches`, `Status` and the review-score field
are **orchestrator-owned** and live in *both* copies, while the CARD SYNC PROTOCOL only syncs
worktree→main, and only for the agent's own notes. So every reviewer reads orchestrator-owned fields from
the copy that is never updated, and will keep filing findings against text the merging card does not
contain. Cycle 5 is the second time this has cost a finding on this card.

F-003 (m-4's untested line-number citation in the docs page) is **deferred to after fix round 5 hands
back**: the file is in the worktree and the fix agent is live in it, and this board's standing rule is that
a mutating agent gets its own tree or the work serializes. An edit of mine landing there now would also
break the fixer's own `git status --porcelain` restore verification, which is the check that proves it put
every mutated file back.

## [One-way sync] Fix round 5's own notes, pulled from the worktree

Agent-owned text, copied verbatim at the end of the round. The orchestrator's pre-gate is the section after it.

## Worktree notes -- fix round 5 (`forge:fix`, auto), 2026-10-23, on cycle 5 (7.6, NOT CERTIFIED)

Scope: `tests/test_guard_integrity.py`, `tests/test_web_server.py` (the class audit reached it -- see
below) and this card. `CLAUDE.md` untouched (G-1); no `src/` path touched (G-6). Two gating findings,
plus the **class** of claim each belongs to.

### The instruction this round exists for: a fix mutates by DELETING the mechanism its claims name

Round 4 ran nine mutants. Eight mutate declaration text or a comment figure and the ninth reverts a
behaviour change; **none deletes a mechanism**. That is a matrix that certifies the round's own
additions and says nothing about whether they are load-bearing, and it is why F-001 survived a round
that was otherwise good work. Every mutant below deletes a mechanism this round's claims name, and two
more are required by shape: an **add-a-line** mutant on a real entry and a **co-edited-drop** mutant.

### F-001 -- clause 2, narrowed to what is constructed and widened where a case was owed

Cycle 5's three refutations, each answered with a case rather than a sentence:

1. **The delete-the-mechanism mutant is now killed.** `if span != len(element_keys):` is the only code
   implementing the add/delete directions; cycle 5 disabled it and got **exit 0, 210 reached, 0 FAIL**,
   167/167 green. `M1-SPAN-EQ-DELETE` below is that same mutant; it now reds at two assertion nodes in
   the recording pass (`:4954` on the added direction, `:4955` on the dropped one's misattribution) and
   at one in the re-raising pass, which stops at the first direction that fails.
2. **The add direction is constructed.** An unkeyed continuation line appended to the fabricated
   entry; the verdict must *name* it, by line number -- `fabricated.py:2: MEASURED_FABRICATED_MISSES[0]
   spans 3 source line(s) and carries 2 key(s)`. Appended at the **end** of the entry deliberately: the
   keys of every earlier line still sit on their own line, so with the span equality disabled the
   verdict is `[]` and this case is the only thing in the file that reds. A middle-line insertion would
   red for a *different* reason (every later key mismatching its line) and could not tell the two
   apart.
3. **The co-edited drop is constructed, as the empty verdict it is, and given a control.** A
   declaration line removed *together with* its key phrase: both counts fall by one, the span equality
   is satisfied, every surviving key is still on its line. The case asserts `== []` -- the honest
   reading -- and the control is the new **census equality**, which the round-4 floor could not be: at
   `>= 45` against a measured 57 it had eleven lines of slack.

**The equality, and the door each figure came through.** `assert _declaration_census(
_MEASURED_TABLE_LINE_KEYS) == (5, 12, 57)` replaces `assert keyed >= 45`. **5 tables / 12 entries / 57
source lines**, each figure re-derived against the final tree through **two independent doors** (see
"The complete enumeration" above, which is where F-002 put them): the keys mapping via
`_declaration_census`, and the deployed enumerator's own `ast.Assign`/tuple-element walk over both
sources summing `end_lineno - lineno + 1`. `(5, 12, 57)` both ways, with the deployed verdict `[]` on
both files at the same moment -- which is what makes the keys door's figures the *sources'* figures.
Nothing was copied from the brief or from the sentence being fixed.

**Every direction now has a constructed case, so clause 2 is widened rather than narrowed** -- seven of
them, each asserting the line the verdict names and `len(verdict) == 1` so a misattribution cannot
pass: gutted (`:3`), inverted (`:4`), moved (`:3`), dropped (`:2`, on the count), **added** (`:2`, on
the count), **entry count** (naming the table) and renamed (naming the table). The one direction with
no catch is the co-edited drop, and it is **declared** rather than claimed sound, in the contract block,
in the class docstring and in `tests/test_web_server.py`'s pointer -- with the census named as what
sees it. The existing `dropped` case, which cycle 5 correctly called a non-discriminating control,
becomes one by having its *message* pinned: with the span equality deleted it still reds, but at `:3`
for a key mismatch, and the `startswith` assert now fails on exactly that.

### F-002 -- the headline figures re-derived, and what the 216-variant sweep cannot see

Both are in "The complete enumeration" above, corrected in place with the cause on the record
(9/4/11 is the tree *before* m-A added the tenth table in that same round). The sweep's blind spot is
stated there in its own paragraph: **none of its four mutations changes an entry's line count**, so the
span equality is outside the domain of all 216 variants -- and of the reviewer's 197-variant
replication. A sweep is a measurement over the mutations it enumerates, never over the mechanism.

### Mutants -- committed instrument only, both passes, ANY-RED, every one a DELETION

`tests/kill_matrix.py`, target and selection `tests/test_guard_integrity.py` (one file: the instrument
**cannot** measure `tests/test_web_server.py`'s `TestWebGuards_EveryStructuralLoopAssertsNonEmpty`, so
that class was never in any measurement selection here -- stated rather than left to be inferred).
**Domain of every figure: 214 `ast.Assert` nodes**, carried separately from the 167 collected tests;
child instrumentation off.

* **Trap (a)**: every `old` pre-counted -- **eleven edits across ten mutants, each occurring exactly
  once, line-delta 0 for every one** (the two count-changing shapes are made line-count preserving by
  spending a blank line inside the same edit, which is why the instrument accepted them at all).
* **Trap (b)**: SHIPPED's **exit code read, not only its cells** -- `pytest exit 0`, `0 FAIL of 214
  reached`, 167 collected, in **both** passes; and SHIPPED re-run **between** every mutant, `exit 0,
  FAIL []`, ten times per pass.
* **Seven of the ten had a recording-pass exit 0 while the matrix recorded FAIL cells**, which is the
  reading the discipline warns about and why every row below states the pass, the exit code and the
  denominator together.
* **Measured three times, and only the reading against the FROZEN tree is quoted.** Every earlier run
  was taken before a later prose edit, and each of those edits moved the asserts below it -- sixteen
  lines, then three, then three more. The kill/survive verdicts were identical in all three runs, but a
  **cell citation** from an earlier one would have been a stale figure of precisely the kind F-002 is
  about, so the whole matrix was re-run once the file stopped changing, with all ten mutants
  re-pre-counted against that exact tree first (eleven edits, one occurrence each, line-delta 0, zero
  refusals). These are that run's figures, and no number below was carried over from the earlier ones.

| mutant | the mechanism it **deletes** | recording | re-raising | FAIL cells |
| --- | --- | --- | --- | --- |
| `M1-SPAN-EQ-DELETE` | `if span != len(element_keys):` -> `if False and ...`: the only code in this module that reads an entry's line **count**. Cycle 5's surviving `M2-SPAN-EQ-DROP` | exit 1, 209 reached, 2 FAIL | exit 1, 209, 1 FAIL | `:4954` + `:4955` (recording); `:4955` alone re-raising, which stops at the first direction that fails |
| `M2-PER-LINE-DELETE` | `if phrase not in line:`: the per-line phrase comparison | exit 1, 208, 1 | exit 1, 208, 1 | `:4954` |
| `M3-ENTRY-COUNT-DELETE` | `if len(value.elts) != len(entry_keys):`: the entry-count arm | exit 1, 209, 1 | exit 1, 209, 1 | `:4954` |
| `M4-ASSIGNED-NOWHERE-DELETE` | `if value is None:`: the keyed-here-but-assigned-nowhere arm | exit 0, 214, 1 | exit 1, 209, 1 | `:4955` -- the *message* assert, the defect becoming "is not a tuple display" instead |
| `M5-CENSUS-LINES-DELETE` | the line counting **inside** `_declaration_census` (`len(group)` -> `len(group) * 0`) | exit 0, 214, 3 | exit 1, 211, 2 | `:4807`, `:4973`, `:4974` (recording); `:4807`, `:4973` (re-raising) |
| `M5b-ADD-LINE-REAL` (**the add-a-line mutant**) | nothing deleted -- the shape the brief requires: a 14th, unkeyed line appended to the **real** `MEASURED_CLAIM_MISSES[2]` | exit 0, 214, 1 | exit 1, 213, 1 | `:4791` |
| `M6-CO-EDITED-DROP` (**the co-edited-drop mutant**) | the real entry's path/keyword declaration line **and** its key phrase, in one mutant (two edits) | exit 0, 214, 1 | exit 1, **214**, 1 | `:4807` **only** |
| `M7-MD-DROP` | `.md` out of `_PATH_SUFFIXES` | exit 0, 214, 7 | exit 1, 201, 4 | `:3875`, `:4011`, `:4058`, `:4070`, `:4071`, `:4101`, `:4102` |
| `M8-YML-DROP` | `.yml` out of `_PATH_SUFFIXES` -- round 3's measured **survivor**, and no longer one | exit 0, 214, 3 | exit 1, 209, 1 | `:4058`, `:4070`, `:4071` |
| `M9-PY-DROP` | `.py` out of `_PATH_SUFFIXES` | exit 0, 214, 6 | exit 1, 209, 4 | `:3702`, `:4009`, `:4011`, `:4025`, `:4058`, `:4070` |

**10 of 10 killed, ANY-RED, in both passes.**

**M6 is the row that matters most, and it is the one with a single cell.** The co-edited drop reds at
`:4807`, the census equality, and **nowhere else**: `:4791`'s per-line verdict passes, and so do the
three value-read asserts in that entry's own committed case (`:3889`-`:3891`). That is the asymmetry
the contract states, measured: the per-line arm is blind to it by construction and the equality is the
only thing that sees it. Before this round the same mutant took `keyed` from 57 to 56 against a floor
of 45 and the file stayed green. Note its re-raising figure -- **214 reached**, nothing short-circuited
past -- so the single cell is the whole reading rather than the first of several.

**M5b is the row cycle 5 asked for.** Adding a line to a real entry reds at `:4791` through the span
equality; under `M1` it would not red at all, which is the whole content of F-001.

**Every assertion this round added or changed has a mutant that reds it**: `:4791` (`M5b`), `:4807`
(`M6`, `M5`), `:4954` (`M1`, `M2`, `M3`), `:4955` (`M1`, `M4`), `:4973` and `:4974` (`M5`, the second
of the two in the recording pass only, the re-raising pass stopping at the first). No decorative arm
shipped.

### The class, not the instance -- every direction-enumerating claim in `git diff d90753df..8727e519`

The brief asked for the class rather than the sibling it named. Enumerated by grepping the diff's added
lines for `reds`, `survive`/`survives` and "all red", then reading each hit for whether it *enumerates*
directions, and finally checking each direction against the committed cases. Eleven claims, of which **two families** were defective -- clause 2 with its two
restatements, and the census sentence:

| the claim | directions | verdict |
| --- | --- | --- |
| contract clause 2 (module block above `_MEASURED_TABLE_LINE_KEYS`) | gut, invert, add, delete, move | **F-001.** Add constructed nowhere; delete non-discriminating. Now seven constructed directions, each asserting the line the verdict names, plus the co-edited drop **declared** with the census as its control |
| the same clause in `test_the_rule_names_what_it_cannot_see`'s docstring | the same five | restated to match, with the declared exception named |
| the same clause in `tests/test_web_server.py`'s `#:` block over `MEASURED_AST_SWEEP_MISSES` | gut, invert, move, entry count -- "by line number" | **corrected**: the entry-count defect names the **table**, not a line; add and drop named; the co-edited drop declared; the local figures removed in favour of the census. This is the one place the audit reached `tests/test_web_server.py` |
| `_PATH_SUFFIXES`' census comment: "Dropping `.md` or `.py` reds, dropping `.yml` **survives**" | 3 | **REFUTED by measurement.** `.md` reds at 7 assertion nodes, `.py` at 6, `.yml` at **3** -- the W-2 survivor was closed by m-B's census in the same round that kept quoting it. Sentence rewritten with the three figures and the cause |
| `MEASURED_TIMEOUT_CLAIM_MISSES[1]`: colon, comma, em-dash missed; full stop, semicolon caught | 5 | holds -- three missed and two caught bodies constructed in `test_the_rule_names_what_its_two_words_cannot_reach` |
| the dependency comment: the member arm is independent of **quoting**, **case** and **spelling** | 3 | holds -- five spellings (canonical, `_`, `.`, upper, backticked) in `test_a_member_is_caught_however_it_is_spelled` |
| "a paragraph that lists an extra's *members* unquoted still reds, **once per member**" | per member | holds -- `assert len(caught) == len(members)` over a real extra's real members |
| `_UNENFORCED_PHRASES`: "rotting any single member red" | per member | holds -- a parametrised case per member, caught WITH and missed WITHOUT |
| `MEASURED_UNENFORCED_PHRASE_MISSES`: six synonyms missed, each caught when a deny-list member replaces it | 6 x 2 | holds -- the loop covers all six on both sides |
| the figure rule: "both spellings and both sides of the figure now have a case" | 2 x 2 | holds, with one thing stated rather than implied: the **first** side alone has no input of its own; what demonstrates it is read is the two-report verdict on `40x40`/`40×40`, and the second side alone has its own case |
| the substring arm: a *code*-shaped reference reds at the AST arm, a *prose*-shaped one at the exemption equality (`tests/test_web_server.py:2257`-`:2270`) | 2 | **not touched** -- the brief puts the substring arm's declared zero unique detection out of scope. Flagged for the record: fix round 2 measured both directions **in memory**, and neither is a committed case; the declaration is honest about the arm's reach, but its two directions rest on a measurement nothing re-runs |

**One mutant no control can kill, declared rather than papered over**: deleting the census assertion
*line itself*. It is the control; nothing in the tree observes its absence, and no honest matrix can
claim otherwise. What is measured instead is that the mechanism the assertion reads can fail
(`M5-CENSUS-LINES-DELETE`) and that the assertion reds on the realistic edit (`M6`). The same is true
of every terminal control in this module, and it is the reason the contract is written where a reader
of the tables finds it.

### Declarations re-derived (`forge:fix` step 6b)

* **DECLARATIONS F-001** -- clause 2 in the module contract block, the same clause in
  `TestTheDeclaredMissTables`' class docstring and in `test_the_rule_names_what_it_cannot_see`'s, the
  pointer in `tests/test_web_server.py`, and this card's SEMANTICS 2 bullet: all five restated from the
  mechanism as it now stands, each naming the constructed cases and the one declared blind spot. The
  floor's own failure text ("the contract is reading too little") is gone with the floor.
* **DECLARATIONS F-002** -- the card's "The complete enumeration" headline figures and the
  216-variant sweep's stated coverage, both re-derived through the deployed enumerator; the contract
  block's "Two other shapes" count **retired** to the dict that can be re-derived; the `_PATH_SUFFIXES`
  census comment's survivor sentence corrected by measurement.
* No behaviour changed in any guard this round: `_unkeyed_declaration_lines`, `_measured_table_names`,
  `_classify`, `_is_type_expression`, `_PATH_SUFFIXES` and every `MEASURED_*` table are **byte-for-byte
  as fix round 4 left them**. What changed is one new pure helper (`_declaration_census`), one floor
  turned into an equality, three cases added to one control, and the declarations above.

### Selections, collected **and** passed

Every figure from a run that was **not** silenced (no `-q` passed, which would have stacked onto
`addopts` to make `-qq` and printed no count line at all):

| selection | collected | passed | pytest exit |
| --- | --- | --- | --- |
| `tests/test_guard_integrity.py` | 167 | **167** | 0 |
| `tests/test_web_server.py` | 166 | **166** | 0 |
| the three `TestTheDeclaredMissTables` tests by **explicit node id** | 3 | **3** | 0 |
| SHIPPED under the instrument, both passes | 167 | 214 of 214 assertion nodes PASS, 0 FAIL | 0 |

No skips hid in them: the passed count equals the collected count in every row, which is the only
figure that separates a green run from a green-with-skips one.

### Guardrails

* **G-1:** `CLAUDE.md` **untouched** -- byte-identical through every plant (`shasum -a 256 -c` OK in
  both manifests), and `git diff -U0 d90753df -- CLAUDE.md` still exactly the three single-line hunks
  round 4 left.
* **G-2:** the web guard not weakened. The only edit to `tests/test_web_server.py` is the `#:` comment
  above `MEASURED_AST_SWEEP_MISSES`; `_WEB_SOURCES`' and `_DOMAIN_VALIDATORS`' non-empty assertions and
  both sweeps are untouched. Whole-file run: **166 collected, 166 passed, exit 0**.
* **G-3:** no second copy. The census reads `_MEASURED_TABLE_LINE_KEYS`, the one authority, and the
  figures that were sitting in `tests/test_web_server.py`'s comment were **removed** rather than
  updated.
* **G-4:** `nonogram_poc` never named or touched; the instrument refuses such an edit by construction.
* **G-5:** stdlib only; `_declaration_census` adds no import.
* **G-6:** no `src/` path in the diff (`git diff --name-only` lists the two test files and this card),
  and **zero** codepoints in U+25A0..U+25FF, U+2022 or U+2219 added anywhere in it -- verified rather
  than assumed, since the rule's subject is `src/nonogram/**` and this round edits nothing there.
* **G-7:** no timing measurement taken, no duration reported.
* **The full suite was never run.** Impact-scoped only: the two test files, whole-file selections, plus
  the instrument's own selection of `tests/test_guard_integrity.py`. Every pytest, script and mutant ran
  with `NONOGRAM_FULL_SUITE_LOCK` pointing into this session's scratchpad
  (`.../scratchpad/card264-fix5.lock`); the board's own `meta/kanban/.full-suite.lock` was never read,
  written or created, and the suite printed the override line in every run.
* Plants: manifest built **up front** (`shasum -a 256` over the files any plant could reach), `cp -p`
  backups, and restoration verified **three ways** after each run -- `shasum -a 256 -c`, `diff -q`
  against the backups, and `git status --porcelain`, which shows only the two test files and this card.
* **Nothing committed**, per the brief: the orchestrator pre-gates and commits.

### Not touched, named so the next reader does not look for them

* `CLAUDE.md` (G-1), anything under `src/` (G-6), `tests/test_cli.py` (byte-identical to `main`;
  `_ADAPTER_COUNT` is **CARD-265's**), `tests/test_timeout.py` (`_blind_propagation` is **CARD-278's**),
  the `check_deadline` census (**CARD-266's**).
* The substring arm's declared zero unique detection in `tests/test_web_server.py:2227`-`:2241` and the
  two-direction comment under it -- out of scope by the brief, flagged in the class audit above.
* Cycle 5's two minors -- m-4's untested line-number citation (F-003) and AC-7's presentation (F-004) --
  are the orchestrator's, per the brief.
* The review report `meta/review/20261023T103148Z-CARD-264-cycle5.yml` was **not** edited: the brief
  scopes this round to the two test files and this card, and round 4 left its own findings `open` the
  same way.

## [Orchestrator pre-gate] Fix round 5 — three mutants re-derived, and my own instrument was wrong twice before it was right

Run before the commit, in the worktree, with `NONOGRAM_FULL_SUITE_LOCK` redirected to a scratch path.

**1. The enumeration first, by AST, because it decides what the gate should show.** Test methods in
`tests/test_guard_integrity.py`: **66 → 66**. One test **renamed**, none added —
`test_the_line_keying_control_reds_on_a_gutted_or_inverted_line` →
`…_reds_on_every_direction_it_declares`. `ast.Assert` nodes **210 → 214**. So the full suite's collected
count must **not move**: the prediction for this gate is 8931 executed again, unchanged.

**2. The renamed test selected by node id — 3 collected, 3 passed, exit 0**, each named in `-rA`
(`test_every_line_of_every_declared_miss_entry_is_keyed`,
`test_every_measured_table_in_the_tree_is_accounted_for`, and the renamed one). **And the OLD name was
run deliberately**: pytest answers `no match in any of [<Class TestTheDeclaredMissTables>]` rather than
passing — the rename fails loudly, which is the property that makes a node-id selection trustworthy and
that a `-k` would not have.

**3. Both touched files whole:** `tests/test_guard_integrity.py` **167/167 exit 0**,
`tests/test_web_server.py` **166/166 exit 0**. Exactly the round's figures.

**4. Three mutants re-derived with a plain `pytest`, not with `tests/kill_matrix.py`** — on this card the
instrument's trustworthiness is the subject, so checking its claim and re-running it are different acts. A
plain run has no line-number topology to protect, so a deletion is spelled here **as a deletion** rather
than being made line-count preserving. Trap (a) honoured: all four anchors pre-counted to exactly one
occurrence. Trap (b): SHIPPED's exit code read, not only its failures.

| mutant | verdict | reds at |
| --- | --- | --- |
| SHIPPED | clean — exit 0, 167 passed, no failures | — |
| **M1 span-equality disabled** — *the mutant that SURVIVED cycle 5 at 167/167* | **KILLED**, exit 1, 1 failed | `…::test_the_line_keying_control_reds_on_every_direction_it_declares` |
| **M6 co-edited drop** — the declaration line **and** its key phrase both deleted | **KILLED**, exit 1, 1 failed | `…::test_every_line_of_every_declared_miss_entry_is_keyed` |
| **M8 `.yml` dropped from `_PATH_SUFFIXES`** — round 3 measured this as a **survivor** | **KILLED**, exit 1, 1 failed | `…::test_the_path_suffix_census_is_the_one_this_comment_states` |

Target restored from a `cp -p` backup after every mutant, verified by `sha256` against the pre-run digest.

**One honest difference from the round's own table, worth stating rather than smoothing:** the round's M6
is line-count **preserving** (it spends a blank line in the same edit) and therefore reds at the *census
equality* and nowhere else; mine is a true deletion and reds at the *per-line keying* test. Both are kills
of the same direction, through different controls — which is the better outcome, because it shows the kill
does not depend on the line-count compensation. And M8 confirms the round's claim **flip**: round 3's
"dropping `.yml` survives" was true when it was measured and was closed by m-B's own census in the round
that kept quoting it, so the sentence was stale rather than wrong. That is this card's subject exactly.

**5. The equality's figures re-derived in a domain of my own** — my own `ast` walk over both sources,
counting physical lines myself, with no import of the module, no `_declaration_census` and no reuse of the
deployed enumerator: **10 `MEASURED_*` assignments, 5 keyed per line, 5 exempted by name,
`found == keyed | exempt` TRUE (no third state), and the census `(5, 12, 57)`** — agreeing with the
equality the test pins, and with per-table spans `1+4+13`, `3+3+10`, `2+3`, `9`, `6+1+2`.

**And my instrument was wrong twice before it was right, both times silently.** The first pass handled only
`ast.Assign` and so missed three tables and **both** registries — it reported `7 / 0 / 0` and a census of
`(0, 0, 0)` without erroring, because the tables are **annotated** assignments (`ast.AnnAssign`). The
second pass read `_MEASURED_TABLE_LINE_KEYS` one level too shallow and reported the two **file paths** as
if they were table names (`2` keyed). Both were caught by comparing against the equality the code pins —
**the control checked my measurement**, which is the inversion this whole card has been about, and the
reason the figures above are stated with the door they came through.

**6. Guardrails re-verified at the gate rather than taken from the round's note.** G-1: `git diff -U0
d90753df -- CLAUDE.md` is exactly three single-line hunks, `@@ -46 +46 @@`, `@@ -48 +48 @@`, `@@ -50 +50 @@`.
G-6: no `src/` path in the committed diff, and the working tree held only the three intended files.
ADR-0036/R4: **0** codepoints in U+25A0..U+25FF, U+2022 or U+2219 across both test files.

## [Gate] Post-fix full suite at `6c29d282` — PASSED, and the prediction was made before the run

**Result: exit 0, 8931 executed, 8904 passed, 27 skipped, 0 failed, 0 error.** No duration recorded (G-7).
The board's lock was **written by the gate** this time — `holder`, `at: 2026-10-23T11:24:47Z`, absolute
`worktree:`, `commit: 6c29d282` — and verified gone afterwards.

**The reconciliation is a prediction kept, not an arithmetic done afterwards.** The pre-gate recorded, in
the commit that precedes this one, that the suite's collected count **must not move**: fix 5 **renamed** one
test and added none (66 → 66 methods by AST), while raising `ast.Assert` nodes 210 → 214. The gate came
back at exactly the previous figures — **8904 passed, 27 skipped, 8931 executed, unchanged**. A gate whose
expected value is written down before it runs is the only kind that can be *wrong*; this one agrees.

Card cumulative: **+48** collected across five rounds (fix 5 contributes 0), every one accounted for.
