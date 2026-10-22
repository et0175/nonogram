# CARD-264: CLAUDE.md's three remaining false claims, and the dead symbol one of them has already fed into a live guard

**Status:** in_progress
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
**Touches:** CLAUDE.md, tests/test_web_server.py, tests/test_timeout.py, tests/test_sourcing_image.py, tests/test_cli.py, tests/test_guard_integrity.py, docs/how-it-works/01-domain/puzzle-creation/09-the-three-inbound-adapters.md
**Review score:** 8.3 (cycle 1, PASS — one polish round before the gate)
**Started:** 2026-10-22T13:55Z
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
