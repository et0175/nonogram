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
**Review score:** 8.3 (cycle 1, PASS) → polish `d5da18ff` (unreviewed) → narrowed → build gate PASSED `99782837` → cycle 2/3 running
**Started:** 2026-10-22T13:55Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —  <!-- unblocked 2026-10-22: narrowed per the owner's decision; awaiting a free slot, cap is 2 -->

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
