# CARD-266: The standing check — no prose anywhere names a `validate_*`/`parse_*` symbol that does not exist

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/266-no-prose-names-a-dead-validator
**Worktree:** —
**Source:** CARD-264's implementation hand-back, 2026-10-22. That card's own notes proposed this as the general lesson; its implementation then went and **measured whether it is buildable** instead of leaving it as a wish, and reported the exemption surface. Every figure below is that measurement.
**Idea:** —
**Wave:** —
**Depends on:** CARD-264 (it fixes the three sites this check would catch; building the check first would red on them)
**Touches:** tests/test_guard_integrity.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why — six cards in one week were gated or carded on a claim naming something that does not exist

The shape, in six instances: CARD-206's `GEOMETRY_DOORS` second member carried nothing; CARD-262
inherited `AsyncFor` and `NamedExpr` with no control anywhere; CARD-264 found a guard whose token set
held `validate_size`, a symbol with **zero** definitions in `src/`; CARD-261's two gating findings were
both claims with no control; and `src/nonogram/web/__init__.py:21` still names a count its own docstring
guard cannot reach. Five of the six are the same sentence in different words: **a text names a symbol or
a quantity, and nothing checks that the named thing exists.**

CARD-264 fixed three instances of it by hand. This card makes the class impossible to reintroduce in the
one corner where it is cheaply decidable: **a symbol name in prose.**

## It is buildable, and the exemption surface was measured rather than guessed

This is the part that makes the card worth cutting. CARD-264's implementation ran the sweep:

| authority | unresolved names |
|---|---|
| naive — `src/nonogram` definitions only | **10**, of which **9 are legitimate** (`parse_qs`, `parse_args`, …) — a check at this breadth is 90% false positives and would be switched off within a week |
| widened — all `src/` + `tests/` definitions, **plus every attribute of every imported module** (9,040 repo definitions, 11,470 reachable attribute names) | **4**, all of which resolve once `meta/profiling/` joins the authority — **plus `validate_size` at exactly 3 sites: the three CARD-264 fixes** |

So at the right breadth the check has a **four-name exemption surface** and **would have caught all three
of CARD-264's prose defects**. That is the whole case for the card: not that the rule is desirable, but
that someone measured its false-positive rate before proposing it.

## What to implement

1. **The check.** No prose under `src/**` or `tests/**` — docstrings, comments and non-code string
   literals — names a `validate_*`/`parse_*` symbol that resolves against none of the enumerated
   authorities. Derive the authority with `ast`; never hand-write the symbol list (ADR-0039/R2).
2. **The authority must include what the measurement showed it must:** all `src/` and `tests/`
   definitions, every attribute of every imported module, and `meta/profiling/`. Deriving a narrower
   authority is how this check becomes 90% false positives and gets deleted.
3. **Default-deny on a shape it cannot analyse**, not a silent skip — an unparsable file is a FAILURE
   (ADR-0039/R2). CARD-264's `TestClaudeMd_EverySymbolItNamesExists` is the in-repo precedent and
   reports `0 unparsable files` as part of its own evidence; follow that shape.
4. **The four residual names become named ADR-0039/R3 exemptions**, each with a control for what it must
   **not** absorb, held to an equality against the sites that exist today — so a fifth unresolved name
   reds rather than joining a growing list.
5. **Do not widen the rule beyond `validate_*`/`parse_*`.** The measurement covers that prefix pair
   only. A wider prefix set is a different check with an unmeasured false-positive rate, and the
   temptation to widen it while in there is exactly what this board's scope discipline exists to stop.

## Acceptance criteria

- **AC-1** *Given* the tree, *then* every `validate_*`/`parse_*` name appearing in prose under `src/**`
  or `tests/**` resolves against the enumerated authority or is one of the named exemptions, with the
  authority **derived from the code** rather than listed. (test: `TestProse_NamesNoDeadValidator`)
- **AC-2** *Given* a **planted** prose reference to `validate_nonexistent`, *then* the control reds
  naming **the symbol and its file and line**; removed, it passes. Both states demonstrated.
  (test: `TestProse_APlantedDeadValidatorReds`)
- **AC-3** *Given* the historical defect — `validate_size` in any of CARD-264's three sites — *then* the
  control reds. **This is the card's acceptance test**: plant the exact text CARD-264 removed and show
  it caught. (test: same class, a committed case per site)
- **AC-4** *Given* a file the walk cannot parse, *then* the control **fails** naming the file; it never
  skips, and the count of unparsable files is reported as part of the evidence. Demonstrated with a
  deliberately malformed file in a temp dir. (test: `TestProse_AnUnparsableFileIsAFailure`)
- **AC-5** *Given* the four named exemptions, *then* each is held to an equality against today's sites,
  and each carries a control for what it must not absorb — the same name **in code** rather than in
  prose must still resolve or red appropriately. A fifth unresolved name reds.
  (test: `TestProse_TheExemptionsAreHeldToAnEquality`)
- **AC-6** *Given* the naive authority (`src/nonogram` definitions only), *then* a committed case records
  that it yields **10** unresolved names of which **9** are legitimate — so a future reader narrowing the
  authority sees the measured cost rather than rediscovering it. This is a regression test on the
  *design decision*, not on behaviour; state it as such.

## Guardrails

- G-1: **Do not hand-write the symbol list or the authority.** ADR-0039/R2. A second copy of the
  package's definitions is the disease CARD-261 and CARD-264 both treated.
- G-2: **Do not widen the prefix set** beyond `validate_*`/`parse_*`; the false-positive measurement does
  not cover anything else.
- G-3: **Do not weaken CARD-264's guards.** `_DOMAIN_VALIDATORS`'s derivation, its AST and substring
  sweeps, and its single R3 exemption all stay as shipped.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1); stdlib only.
- G-6: ADR-0036/R4 — this card edits no `src/` file, so it should hold by construction; **verify rather
  than assume**.
- G-7: Take no timing measurements and report no durations.

## Architecture context

- **ADR:** ADR-0039/R1–R3 are the whole subject — a claim needs a control that can fail, a guard's set is
  derived from an enumerable authority and defaults to deny, and an exemption carries a control for what
  it must not absorb. ADR-0022/R1 is why `validate_size` does not exist (extent as a pair).
- **Components:** none changed. One test file.
- **Trace:** `meta/architecture/trace.yml` — unchanged; no requirement's verifying test moves.

## Worktree notes

- **[The figures are measurements, not estimates]** 10 → 4 unresolved names, 9,040 repo definitions,
  11,470 reachable attribute names, and `validate_size` at exactly three sites all came from a sweep
  CARD-264's implementation actually ran. Re-derive before relying on one, but do not treat them as
  guesses to be re-litigated.
- **[Why this is worth a card rather than a backlog line]** The check's value is not that it is a nice
  rule; it is that **its false-positive rate was measured at two breadths before anyone proposed it**.
  Most standing checks on most boards are proposed the other way round and die of noise. Keep that
  property: if the fix's exemption surface grows past the measured four, stop and report rather than
  exempting your way to green.
- **[Use the committed instrument]** `tests/kill_matrix.py`, documented in `tests/README.md` from line
  453. Keep deletion mutants **line-count-preserving**, aggregate **ANY-RED**, and **report the DOMAIN**
  of every figure — assert-node count versus collected-test count, selection, arms reached, SHIPPED.
- **[And the instrument's exit code is not a kill signal]** `Pass.RECORDING`'s handler does not re-raise,
  so a killed mutant exits pytest 0 while the matrix records FAIL. Measured four times across three
  cards on 2026-10-22, on nine mutants in CARD-264 alone. CARD-265's AC-5 adds the sentence to the
  README; until it lands, carry it yourself.
- **[A known instrument blind spot that may bite here]** `kill_matrix.py` cannot measure a test that
  `monkeypatch.setattr`s a dotted target in its own module — the plugin registers the rewritten module
  in `sys.modules` without setting it as an attribute of the `tests` package. It fails in both passes
  with 0 FAIL cells, so it announces itself rather than lying. On the backlog with a one-line fix; if a
  control you write here needs that pattern, exclude it from the selection and evidence it by plain runs
  and plants instead, the way CARD-264 did.

---

## [Routed in 2026-10-23, from CARD-264's cycle 3] Widen the reach to `docs/**`, and add the **quantity** half

Two measured items from CARD-264's final review cycle. The first is the structural cause of that card's
only gating finding, and the reviewer named it as **shipping uncertified** precisely so it would land
here rather than close with that card.

### 1. `docs/**` belongs in this check's reach, and the measurement is one grep

**`grep -rn 'how-it-works' tests/` returns ZERO hits — no test reads that tree at all.** So every claim
on every page under `docs/how-it-works/` is prose with no control whatsoever, which is this card's exact
subject one directory over.

**What it cost, measured rather than hypothesised.** CARD-264's cycle-2 finding C-1 was a
`docs/how-it-works/` page carrying **three** false claims at once: a bold verbatim quotation of a comment
that had been reverted out of the tree, a past-tense "all three sites now state the rule" that was true
of one, and a citation of `TestAdapterAllowlist_NoProseClaimsAStaleCount` — a class with **zero** hits
anywhere. It survived a **passing** review cycle (8.3, zero gating findings) and an elective fix round
before a second cycle caught it, and it was caught by *reading*, not by any gate. A fourth defect of the
same kind on the same page — a line citation off by nine, pushed there by the card's own edit — had been
caught the same way one cycle earlier.

**The cheap half is already in scope.** This card's sweep is a symbol-name scan over prose; adding
`docs/**` to the trees it reads is a path-list change, and the two concrete shapes it would have caught
are (a) `TestAdapterAllowlist_NoProseClaimsAStaleCount`, a named test class resolvable against the test
tree exactly as a `validate_*` name is resolvable against `src/`, and (b) `src/nonogram/__init__.py:40`,
a **line-number** citation into a file, which resolves or does not. Both are decidable.

**The expensive half is out of scope and should stay out, with the boundary stated.** A *quotation* being
verbatim, and a *tense* being right, are not decidable by a symbol scan. Do not try: declare them as a
measured bound with their own failing control (ADR-0039/R3) and say what the check cannot see. The
durable partial answer — and it is cheap — is a rule that **a `docs/` page may not quote a code comment
verbatim unless the quoted string is found in the cited file**, which is a substring check and would have
caught C-1's quotation directly.

### 2. The **quantity** half: `tests/test_timeout.py:3651`'s "six sites" is an uncontrolled figure

This card's framing sentence is *"a text names a symbol **or a quantity**, and nothing checks that the
named thing exists"* — and the symbol half is what the measurement so far covers. A quantity instance,
filed as a Minor on CARD-264's last cycle and re-derived there by an `ast.Call` walk rather than by grep:
a docstring says the deadline is checked at **six sites across `propagate.py` and `search.py`**, and that
is **accurate today** (`propagate.py:983`, `:1129`, `search.py:1180`, `:1259`, `:1418`, `:1728`) and read
by nothing. A seventh site added, or one removed, leaves the sentence green and wrong.

It is the same shape as *"this set is closed at two names"* one file over — the claim CARD-265 inherited —
and the fix is the same shape too: a `check_deadline` call census held to an **equality**, two lines,
which would also stop three consecutive review cycles having to re-derive that figure by hand. **Note
what this is NOT:** it is not CARD-264's cycle-2 finding I-1, which was **refuted**, and it is no argument
for touching `CLAUDE.md:50`. That sentence enumerates *two checkpoints*, both of which are pinned; this is
the narrower object the refutation left behind — a count in a **docstring**, not a claim in the brief.

### Dependency note

This card already declares `Depends on: CARD-264`, and that dependency is satisfied by CARD-264's merge.
The two items above arrive **from** that card's final cycle, so they are inputs to this one, not new
blockers.
