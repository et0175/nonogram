# CARD-316: Seven acceptance criteria name tests that were never meant to exist — rejected alternatives, retired features and one forward declaration, each reading as mechanically checked

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.25d
**Complexity:** simple
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/316-seven-phantom-acceptance-keys`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-316
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29, which found that the board's real dead-ref population is bare class names rather than node ids. CARD-307 was cut; this is one of its four successors. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** 72 <!-- STAMPED 2026-10-31 at dispatch. Free of CARD-329 (intersection EMPTY) and no longer behind CARD-317, which merged 8e2ce9ed and released requirements.yml. Premise VERIFIED at dispatch: all seven ACs present, all seven named tests still phantom by an ast index. -->
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml
**Review score:** —
**Started:** 2026-10-31T06:47:15+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## [Premise verified at dispatch, 2026-10-31] — and every line number in the table is stale

**Checked before dispatch, per the rule four earlier cards of this family produced
(a premise built on a text-search reading dissolves on contact, so resolve it by
definition first).** This card's premise **holds, completely**:

- all **seven** ACs are still present in `requirements.yml`;
- all **seven** named tests still resolve to **no `def`/`class` anywhere** in `tests/`
  or `src/`, by an `ast` index — they are genuinely phantom, not merely un-grepped.

So this card is dispatchable as cut. **What was stale is every line number in the table
above — all 7 of 7**, because CARD-318 and CARD-317 both landed in this file since the
card was written.

**THE TABLE OF LINE NUMBERS IS DELETED, NOT CORRECTED A FOURTH TIME.** It held, at
dispatch, the readings `:1863 :1871 :2542 :2550 :3087 :3094 :3712`. Those were
reproduced exactly by the implementation round at `f7ba9c96` by the `- id:` scan below
— and they were **wrong again within the same round**, because this card's own commit
adds comment lines above all seven entries, which moves every figure below them
(the same seven are at `:1877 :1886 :2567 :2575 :3125 :3132 :3779` after it, and that
reading is just as perishable). A `requirements.yml` line number is a reading at a
commit, it goes stale on the next write to the file, and CARD-316 is the third card in a
row to inherit one. **The durable locator is the criterion id**, which is what the
derivation and every comment this card wrote use. Find any entry by its `- id:` line:

```python
import re, pathlib
for i, line in enumerate(pathlib.Path("meta/architecture/requirements.yml")
                         .read_text().splitlines(), 1):
    if re.match(r"^\s*- id: AC-206\s*$", line):
        print(i)
```

**Two facts from the cards that shifted the file, both load-bearing here:**

- **CARD-318's F-009 is the defect to avoid repeating.** Demoting a criterion's `then`
  to match the code, without checking that its named test asserts the new `then`, left
  a criterion that *resolves* — so nothing warns — while verifying nothing. If any of
  these seven is repaired by re-pointing rather than by removing the key, **check the
  target asserts the criterion's own `then`**, not merely that the name resolves.
- **CARD-317 measured that the validator has NO `status: superseded` exemption** for an
  AC dead ref (`_validate_ac_ec_test_refs`, no `status` test in the function), and that
  its suggested fix — dropping the `test:` — trades the dead-ref warning for an
  "acceptance criterion has no 'test'" warning: **net zero**. So expect the warning
  count to move by less than seven, and **derive what it actually does** rather than
  predicting it. ~~Main stands at **0 err / 90 warn**~~ — **main stands at 0 err /
  88 warn**, measured by this card at `f7ba9c96` in two trees with an empty `comm`
  both ways; the 90 was stamped at `03f96e87` (06:35) and CARD-317's merge landed
  48 minutes later, so it was already refuted when it was handed over. Retracted at
  its own site in `meta/kanban/config.yml` as well as here (ADR-0039/R4). Diff the
  WARN **sets** with `comm`, never the totals.

  **CARD-317's "net zero" was right, and it is the one inherited figure this card
  did not have to retract.** Measured: 88 → 88, seven dead-ref warnings out and
  seven "has no 'test'" in, on the same seven criteria, nothing else moving.

## Why this card exists

Seven entries in `requirements.yml` carry a `test:` key naming a test that **nobody
should ever write**, because the thing the AC describes was rejected, retired, or has
not been built yet. Each one produces a `DEAD check ref` warning, and — worse — each
one reads as *mechanically checked* to `forge:status` and to anything judging
readiness.

They are already marked, in comments, as not-to-be-built. The comment says one thing
and the `test:` key says another. **The key is the part the machine reads.**

| entry | owning requirement | the marker already there |
|---|---|---|
| AC-129 | FR-028 | `# alternative: allow_degenerate_grids` |
| AC-134 | FR-028 | `# alternative: allow_degenerate_grids` |
| AC-206 | FR-035 | `# alternative: fixed_research_mix_30_45_25` |
| AC-207 | FR-035 | `# alternative: derived_from_audience` |
| AC-191 | FR-032 | `# RETIRED 2026-09-22 (b) unimplemented — the wide-grid flag is dropped` |
| AC-192 | FR-032 | `# RETIRED 2026-09-22 (b) unimplemented — no wide-grid flag exists to be absent` |
| AC-379 | FR-040 | `# OWED by CARD-226, which splits the two-up page into two equal slots` |

(The line-number and test-name columns are gone on purpose. The line numbers were
stale twice over — see the premise block. The test names are not needed to act on
the card, they are reproduced by `scratchpad/card316/derive_set.py`, and spelling a
withdrawn ref in a new place is the one thing this family of cards has learned not
to do casually.)

**Three different situations, ~~two different repairs~~ — and in the end ONE repair,
for three different reasons, because the second repair the card proposed does not
exist.** The three situations are real and each criterion's comment block records its
own; what collapsed is the second mechanism. See AC-4.

**The four alternatives and the two retired ACs (six)** describe behaviour the project
chose *against*. AC-206/207 are the clearest: they assert the default split is
**30/45/25**, while the chosen criterion AC-205 — six lines above, with a live test —
says **40/40/20**, and `src/nonogram/admin/book_plan.py:345` says
`Split(40, 40, 20)`. **Both verified, the line number exact** (`DEFAULT_PLAN =
prefill(150, Split(40, 40, 20))`, and no `30, 45, 25` anywhere in `src/`), with the
decision behind it: **DEC-036 → ADR-0034, `fixed_150_at_40_40_20`, 2026-09-22**.
AC-191/192 assert a wide-grid flag whose own comment says it was dropped, and the
surviving test is `TestBookSelect_WideGridAboveFloorCarriesNoFlag`, which asserts the
*opposite* — **verified, and it belongs to AC-241**, the very criterion the RETIRED
comment already names as the replacement. AC-129/134's authority, which the card did
not state: **DEC-034 → ADR-0027, `refuse_degenerate_density`, 2026-09-12**. For these
six the repair is to drop the `test:` key, per the validator's own advice: *"write the
test, or drop the `test:` … an honest gap is fixable, a phantom one is not."*

**AC-379 is different and must not be lumped in.** It is an honest forward
declaration — CARD-226 genuinely owes it. The defect is only that `kind: test` makes
an owed test read as a performed one. This is exactly the
`adr-check-refs-must-be-honest` pattern. ~~It becomes a **`review-lens` naming
CARD-226**, and flips back to `kind: test` when that card lands.~~ **An AC cannot
carry a `review-lens` — the kind is a no-op there, measured. It keeps the same repair
as the six and the flip-back obligation moves to CARD-226's AC-8. See AC-4.**

## What to implement

1. **Derive the set, do not copy the table above.** ~~Walk `requirements.yml` for
   entries whose `test:` names a symbol with no `class`/`def` definition in `tests/`,
   and partition them by the marker in the comment lines directly above the entry.~~
   **THAT RECIPE IS REFUTED — it selects 191 entries by the recipe's own reading and
   175 by the authority's, not seven; 18 once intersected with the three markers.**
   **Every figure here now names the matching rule it was measured under
   (ADR-0039/R4), because the family below was first reported under one rule and
   attributed to another.** Of the 421 AC/EC `test:` keys at `f7ba9c96`:
   - **191** have no `def`/`class` under **EXACT NAME equality** against an `ast`
     index of **11005 distinct definition NAMES** over `src/` + `tests/` (330
     modules; the node count is **12418** — the index maps a name to a *list* of
     sites, so "definition nodes" was the wrong noun for 11005). This is
     `scratchpad/card316/derive_phantoms.py:84`'s rule, `if name in idx`, and the
     figure the sentence above now owns.
   - **175** have none under **the authority's rule**, which is
     `tests/test_check_ref_resolution.py`'s `_strict_resolution` (`:1001-1007`):
     for a bare ref it tests **substring containment** (`declared.ref in symbol`)
     over the whole **in-domain** definition index (11278 names), deliberately,
     because this board's convention is a `def test_<RefName>` wrapper. The
     authority is stricter about what counts as defined, so it finds 16 fewer
     phantoms. The refutation's direction is unaffected either way.
   - **18**, not 21, once intersected with the three markers — and this one is a
     **miscount, not an arm mismatch**: re-run, `derive_phantoms.py`'s own output at
     the base classifies 13 `# alternative:` + 4 `# RETIRED` + 1 `# OWED` = **18**,
     and the authority's substring rule gives **18** as well (the 16 refs the two
     rules disagree about are all unmarkered). 18 − this card's 7 = **11**, which is
     exactly the list enumerated below — so the "14" in that sentence was the same
     miscount carried forward.
   The gap is the validator's resolution rule, which is a **text search**:
   `git grep -w` over tracked files, excluding only `meta/architecture/` and
   `*.md` — so a name spelled in a `.py` comment table or a committed `.txt`
   duration dump resolves. The authority
   that does select seven is **dead on BOTH resolvers**, and
   `scratchpad/card316/derive_set.py` states it that way, importing
   `tests/test_check_ref_resolution.py`'s own `_loose_resolution` and
   `_strict_resolution` rather than re-implementing them. Partition by the marker, as
   cut, plus a fourth box for `status: superseded`. **Per ADR-0039/R2 an entry the walk
   cannot classify is a FAILURE, never a silent omission** — the instrument exits
   non-zero; it reported 0 unclassifiable.
2. **For the six: remove the `test:` key.** Keep the AC. Keep the comment. An AC
   without a `test:` is an honest unverified example; an AC with a phantom one is a
   lie with a green tint. Do **not** delete the ACs — they record what was considered
   and rejected, which is why the alternatives were written down in the first place.
   *(Done, and the comment block on each records the authority. The `test:` keys are
   the only non-comment lines the commit removes, and it adds none — the mechanical
   discharge of AC-3.)*
3. ~~**For AC-379: convert to `review-lens`, naming CARD-226**~~ **REFUTED — the lens
   is a no-op on the validator of record, measured, and was not shipped. AC-379 got the
   same `test:`-key withdrawal as the other six and its comment block names CARD-226
   and the planned test. See AC-4 for the measurement.** The second half stands and is
   done: **CARD-226 now carries AC-8**, requiring the flip back *and* requiring the
   restored ref's test to assert AC-379's own `then`, so the obligation is carried by a
   card rather than by a comment.
4. **Say what the warning count did, measured on the validator of record**, with the
   binary named. ~~Expect **100 → 93**.~~ **REFUTED — measured 88 → 88, seven out and
   seven in; see AC-5 for the retraction and its basis.** Diff the warning **sets**
   line by line, not the counts — a count that moves by seven can hide seven arrivals
   and fourteen departures, and in this card's case an UNCHANGED count hid exactly
   seven of each.

## Acceptance criteria

- **AC-1** (the set is derived): *Given* `requirements.yml`, *then* the seven entries
  are produced by a walk that reads ~~definitions from `tests/`~~ **both resolvers**,
  not from a list in this card, and an unclassifiable entry fails rather than being
  skipped. **Met** by `scratchpad/card316/derive_set.py`: 11 dead AC refs, boxed
  4/2/1/4, 0 unclassifiable, non-zero exit on an unboxable entry; and after the repair
  it reports **in scope: 0**. The `tests/`-definitions wording is corrected in step 1
  — it selects 191 by exact-name equality over `tests/`+`src/`, 175 under the
  authority's substring rule, and 18 under either once intersected with the markers,
  which is why the authority had to be the pair of resolvers. Figures and rules are
  paired in step 1.
- **AC-2** (no phantom key survives): *Given* the branch, *then* no `test:` key in
  `requirements.yml` names a symbol with no definition in `tests/` — asserted by a
  test, so the property holds for entries added later.

  **AC-2 IS UNSATISFIABLE AS WRITTEN and is not met in that form.** FR-001/AC-001..004
  still name four undefined symbols, and that is **CARD-317's explicit decision of
  2026-10-31**, stamped in FR-001's own block comment: their refs are "the honest
  statement that nothing verifies a retired criterion". A test asserting AC-2's
  universal would red on this branch the day it was written, and writing it would mean
  reversing a sibling card's decision by side effect. What the card actually wants —
  *the property holds for entries added later* — **is enforced in the two directions
  that matter here and in no others, and the third direction is a measured bound rather
  than a claim (ADR-0039/R1, fix round 1's F-004)** — by
  `tests/test_check_ref_resolution.py`'s pinned `HONEST_DEAD` (9, re-derived) and
  `CENSUS` (573, re-derived): an eighth phantom cannot ENTER `requirements.yml`, and a
  declaration cannot LEAVE, without reddening both, and both were mutated this round to
  prove they can.

  **THE BOUND, measured in review cycle 1 and not closed by this card.** The pins do
  **not** detect a criterion **re-pointed** at an existing, defined, already-declared
  test that asserts something else — which is the cheaper and more tempting regression
  of the two. Planted and run: AC-379 given back a `test:` key naming AC-205's live
  class-style ref, a test about a default distribution plan rather than a slot float.
  Result: **23 passed, every cell green**, and the validator of record **88 → 87**, one
  warning OUT (`has no 'test'`) and **nothing IN**, because the name resolves. `CENSUS`
  does not move (the ref was already declared), `DEFINED` does not move (it already had
  a definition), `HONEST_DEAD` does not move (it was never dead). **So the combined gate
  — nine pinned classes plus the warning count — strictly PREFERS that lie to the honest
  gap this card shipped.** This card's own new comment above AC-191 diagnoses exactly
  that shape in prose ("a criterion re-pointed at a test that asserts something else
  resolves, so nothing warns, while verifying nothing") and had **no control for it**;
  the bound is now recorded at both sites — beside `HONEST_DEAD` and `CENSUS` in the
  module, and in the registry above AC-191. **No guard is built here, deliberately:**
  catching it needs a check that reads what a test ASSERTS, which no instrument on this
  board does, and building one would widen this card past its subject. It is the
  registry-side twin of CARD-333's item 2 and of CARD-319's text-search defect — all
  three wait on the same forge_1 decision — and it is routed to the orchestrator to card
  alongside them rather than left in a review YAML. No new test was written, deliberately. **The residue is a real gap and it
  is the owner's call, not this card's:** the four FR-001 refs, where CARD-316's thesis
  and CARD-317's decision disagree.
- **AC-3** (~~the six~~ **all seven** keep their ACs): *Given* the branch, *then*
  AC-129, AC-134, AC-191, AC-192, AC-206, AC-207 **and AC-379** still exist with their
  `given`/`when`/`then` and their comments intact — only the `test:` key is gone.
  **Met, and verified mechanically at the diff level rather than by a test** (stated as
  the weaker control it is): in `git diff -U0` over `requirements.yml`, every removed
  non-comment line is one of the seven `test:` keys and the set of **added** non-comment
  lines is **empty**. The YAML was re-parsed afterwards and all seven still carry
  `given`/`when`/`then` with `test: None`. AC-379 is in the list because AC-4's lens
  was refuted; G-3's AC-205 is untouched by the same reading.
- **AC-4** (AC-379's obligation is carried by a card): *Given* the branch, *then*
  ~~AC-379 is `kind: review-lens` naming CARD-226~~ AC-379 carries **no `test:`
  key**, its comment block records the planned name and names CARD-226, **and**
  CARD-226 carries an acceptance criterion requiring the flip back. A demotion
  with no card owing the flip is how a shim becomes an end state.

  **The `review-lens` half is refuted and was not implemented (ADR-0039/R4).**
  `kind: review-lens` on an acceptance criterion is a **no-op**: an AC's `kind:`
  is its *scenario* kind, the validator does not validate it at all, and
  `_validate_ac_ec_test_refs` passes the **literal string `"test"`** as the check
  kind for every AC `test:` ref it walks, so the entry's own `kind:` is never
  read. `review-lens` is a member of `VALID_CON_CHECK_KINDS` — it belongs to a
  CON's or an ADR rule's `check: {kind:, ref:}` mapping, a shape an AC does not
  have, and every one of the nine `review-lens` occurrences in `requirements.yml`
  today is on a CON. **Measured, not reasoned from the source alone:** the kind
  was planted on AC-379 by text (anchor asserted unique), the validator of record
  re-run, and the symmetric difference over the whole WARN set was **EMPTY** —
  AC-379's DEAD check ref warning still reported, verbatim. The file was restored
  to its exact SHA-256 (`51ac92f0…47f2ec`). Had this card shipped the lens it
  would have shipped a criterion that reads repaired and warns identically, which
  is CARD-318's F-009 in a new costume.

  So AC-379 got the same repair as the other six, for a different reason, and the
  obligation moved to **CARD-226's new AC-8** — which also requires the restored
  ref's test to assert AC-379's *own* `then`, not merely to resolve.
- **AC-5** (~~the count moved, and only downward~~ → **the trade is one-for-one and
  nothing else moves**): *Given* `main` and the branch, *then* the validator of
  record's WARN sets differ by exactly fourteen entries — the departing seven are
  the seven DEAD check ref warnings named here, the arriving seven are
  "acceptance criterion has no 'test'" on the same seven criteria — and **nothing
  else moves in either direction**. Sets diffed with `comm`, not counts.

  **AC-5 AS CUT IS REFUTED, on all three of its figures, and is rewritten above
  rather than scored against (ADR-0039/R4).** Measured 2026-10-31 on the
  validator of record (`/Users/omelnikova/MyProjects/forge_1/forge/skills/
  architect-validate/scripts/validate.py --root meta/architecture --phase all`,
  run with the main venv for `ruamel.yaml`):
  - **main is 88, not 100.** Basis: two independent runs at `f7ba9c96`, one in
    the main checkout and one in this worktree, WARN sets compared with `comm`
    and the symmetric difference EMPTY both ways — which also discharges G-5
    without swapping any file, because the two trees are at the same commit.
  - **the branch is 88, not 93.** Basis: same binary, same invocation, after all
    seven repairs.
  - **"no warning of any kind is added" is false by construction, and CARD-317
    said so before this card ran.** Dropping an AC's `test:` hands the validator
    the other half of the same pair: `_validate_ac_ec_test_refs` stops reporting
    a dead ref and `_validate_criterion`'s `if not crit.get("test")` starts
    reporting "acceptance criterion has no 'test'". Measured one-for-one, on the
    same seven criteria, and proved reversible — restoring AC-191's key alone
    flips exactly that one warning back and leaves the total at 88.
  - Both severities are WARN, and **the first version of this note drew the wrong
    conclusion from a right premise (fix round 1, F-008).** The premise holds:
    `_dead_ref_severity` (`validators/requirements.py:593-598`) and the no-`test`
    branch (`:215`) both read `Severity.ERROR if stage == "quality" else
    Severity.WARN`; `stage` has one source, `load_stage` (`validators/utils.py:74-89`),
    which searches three directories for `.skills.yml` and returns `None` here
    because no such file exists or is tracked in either tree. What does **not**
    follow is "at `stage: quality` this trade stops being neutral". **Both sides of
    the trade are gated on the same condition and flip together**, so at
    `stage: quality` the change is seven ERRORs out and seven ERRORs in — still
    one-for-one, still net zero, identical before and after this card. What
    `stage: quality` would change is the BOARD: these seven criteria (and FR-001's
    four) would be ERRORs rather than WARNs, whoever had edited them. One further
    precision: the gate is `stage != "quality"`, not "stage is `None`", so any
    other stage value also leaves both at WARN.

  The repair this card delivers is therefore not in the count and never could
  have been. It is in what the model CLAIMS: a criterion with no `test:` reads as
  an unverified example to `forge:status` and to the kanban AC/EC gate, where one
  naming a test nobody wrote read as mechanically checked.

## Guardrails

- **G-1: do not write a test to retire a warning.** Six of these describe behaviour
  that does not exist. A test asserting rejected behaviour is worse than the warning.
- **G-2: do not delete the acceptance criteria.** The rejected alternatives are a
  record of a decision. Removing them loses why 40/40/20 was chosen.
- **G-3: do not touch AC-205.** It is the live, correct, tested criterion and the
  control that AC-206/207 are the rejected pair.
- **G-4: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.) **Discharged, fix round 1:**
  `tests/test_check_ref_resolution.py` is the ONLY file under `tests/` this branch changes
  (`git diff --name-only 9932bb07..HEAD -- tests/`), and its collected node ids at `main`
  and at HEAD are **23 and 23 with an EMPTY set difference in both directions** — nothing
  added, nothing removed, nothing renamed. Both lists were asserted non-empty before being
  compared, the module's SHA-256 was identical before and after the temporary checkout of
  main's copy, and `--collect-only -q` was run with `-o addopts=` (bare `-q` stacks to
  `-qq` and prints no node ids at all).
- **G-5: do not compare this branch's warning count to main's without holding the
  review YAMLs equal.** `meta/review/**` is inside the validator's ref-resolution
  domain, so a tree with different reports in it resolves differently. Swap the files
  inside one worktree and re-run. **And do not validate a `git archive` copy** — a
  copy has no `.git`, so staleness and drift checks fall silent (measured: 77 against
  a worktree's 102).
- **G-6: name the validator binary beside every figure.** The plugin-cache copy
  reports a phantom `[ERROR] ADR-0025 circular supersession` from a regex bug; the
  copy of record is the `forge_1` one named in `meta/kanban/config.yml`.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: **test**, `tests/test_suite_profile.py::…::test_the_control_for_each_spelling_depends_on_the_set` at `:4127`) — **corrected: this card first labelled R1 and R2 `review-lens`, which would have had a reviewer treat two mechanically-checked `mandatory` rules as reviewer judgement.** Both refs are live (`def` lines read directly) and both cells ran green in this round's impact set
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: **test**, `tests/test_suite_profile.py::…::test_the_guard_sets_are_derived_and_not_hand_written` at `:4215`)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer; the RULE is tested at `tests/test_export_pdf.py:1249`** — verify the substance; the pointer repair is **CARD-317's**)

## Architecture context

- **ADR:** ADR-0039/R2
- **Components:** none in `src/` — this is the requirements registry
- **Trace:** ~~six ACs lose a `test:` key and one becomes a lens~~ — **all seven lose
  the `test:` key** (see AC-4). `trace.yml` was re-read afterwards as this bullet asks,
  and the answer is **no change, measured**: not one of the seven refs is named anywhere
  in `trace.yml` (zero hits each, which is also why `CENSUS` loses exactly seven with no
  overlap term moving), the FR-028, FR-032, FR-035 and FR-040 rows were `status: partial`
  before and after, their `tests:` lists are untouched, `TRACE_TESTS` stands still at 507
  by set difference, and the validator added no coverage finding on any of the four.
  Corroboration worth noting: FR-035's trace description already reads "150 puzzles at
  40/40/20", agreeing with ADR-0034 and with the code against AC-206/AC-207.

## Worktree notes

**Round 0, 2026-10-31.** Two commits: `b4dd33f7` (the instruments, deliberately first)
and `5d3674a6` (the repair). `meta/kanban/config.yml` and this card follow in a third.

---

### Fix round 1, 2026-10-31 — after review cycle 1 (6.0)

**The branch was rebased onto `main` at `9932bb07`** (merge base was `f7ba9c96`; `main`
moved twice under this round, and both moves bear on this card). The three commits
replay as `ecba9638` + `c0802fba` + `51a6b1e4`.

**`meta/kanban/config.yml` is no longer touched by this branch at all (F-002).** The
conflict the review predicted is real and was observed: the rebase stopped on
`meta/kanban/config.yml` with content conflict markers, in the exact hunk `main`'s
`a29c3c96` had rewritten in the opposite direction. It was resolved by taking **main's
version whole** — `git diff 9932bb07..HEAD -- meta/kanban/config.yml` is now **empty** —
because main's block is strictly better: it carries no current figure at all, it states
the method (run the validator of record, diff the WARN **sets** with `comm`, never the
totals), and it already records this card's own 88 at `f7ba9c96` as one of four **dated
readings**. Resolving it the branch's way would have restored, forty minutes later, the
very practice the orchestrator had removed — on reasoning this card's own ADR-0039/R4
retraction agrees with. The measurement is worth recording and is recorded **here**,
dated, where a figure is allowed to be a reading rather than a fact.

**The owner's retirement-shape decision of 2026-10-31 (`366e5ffc`) is executed in full
(F-001).** The decision was taken on the contradiction this round surfaced, settled it in
this card's favour, and routed the registry work to this fix round because this branch
already owns `requirements.yml`. Against the five points:

1. **Drop the key.** Done for the seven in round 0; done now for FR-001's four.
2. **A `status:` stays for the HUMAN record, labelled as prose.** Done — this was the
   half that was missing. Six of the seven now carry one; the vocabulary, the reason for
   each value, and the *measurement* that it is prose are written once, in FR-001's own
   block comment, with the other sites pointing there rather than repeating it.
3. **The planned test name in a comment, not a key.** Already done for AC-379; FR-001's
   four withdrawn names are likewise kept as prose, as the record of what the keys
   claimed.
4. **CARD-317's four are CONVERTED to match.** Done: `FR-001/AC-001..AC-004` lose their
   `test:` keys and keep `status: superseded`, `superseded_by`, `superseded_at` and
   `superseded_note`, so the supersession stays reversible and the record is unchanged.
5. **CARD-333 cut and blocked.** The orchestrator's, not this round's.

**AC-379 still has no `status:`, deliberately,** and the registry now says why in terms:
a forward declaration is not a retirement, and the owner's decision reserves its exact
form to CARD-333's item 4.

**Why the `status:` values are `rejected` and `retired` rather than `superseded`.** The
review asked for a deliberate choice rather than a silent invention, and here it is. The
validator reads an acceptance criterion's `status` **not at all** — measured, not
assumed: `_validate_criterion` (`validators/requirements.py:196-235`) reads the id,
`given`/`when`/`then`, the `test:` key and the wording heuristics and nothing else, and
the lifecycle check that *does* read `status` (`_validate_con_lifecycle`, `:501`) has
exactly **one** call site, `:460`, inside the constraints loop. So no vocabulary is
enforced for an AC and nothing honours the marker; it is prose until CARD-333 lands, and
it is labelled as prose at every site. This file's AC vocabulary before today was
`superseded` (9 keys) and `unmet` (1). `superseded` fits FR-001's four, which each name a
successor. It fits neither family of the six, so two words are added and the registry
says so: **`rejected`** for AC-129, AC-134, AC-206, AC-207 (each states the branch a
resolved DEC chose *against* — nothing superseded them, because they were never adopted),
and **`retired`** for AC-191, AC-192 (adopted under BK-3 and then amended away; it is the
word ADR-0027, ADR-0034 and the registry's own comment above AC-191 already use).
Corroborating that the choice is free: the validator run after the six were added is
byte-for-byte the same WARN set as before them — an unknown AC `status` raises nothing.

**The review's expected pin movement is REFUTED, and this is the round's own finding
against itself.** Cycle 1 expected the conversion to take `CENSUS` 573 → 569 and
`HONEST_DEAD` 9 → 5, on the premise that FR-001's four refs were "the whole of
`HONEST_DEAD`'s `requirements.yml` remainder". Measured: **all nine classes have an EMPTY
symmetric difference before and after the conversion** — `CENSUS` 573 → 573,
`HONEST_DEAD` 9 → 9, every other class unmoved, re-derived with
`scratchpad/card316/census_snapshot.py` (which reproduced all nine stored baselines,
count *and* digest, on the rebased tree before anything was edited). The cause is
mechanical and resolved against the authority rather than argued: **each of the four is
also declared by `meta/architecture/trace.yml` at `:110-113`**, which this card does not
touch, so dropping the `requirements.yml` key removes a declaration **site**, not the
**declaration**. A census counts refs, not sites. Each of the four was then resolved
individually against a `def`/`class` under **both** matching rules — exact name and the
authority's substring containment — over an independent `ast` index (11005 distinct
definition names, 330 modules, positive control on a name known to be defined): **zero
definitions for all four**, so all four stay undefined, stay declared, and stay members
of `HONEST_DEAD`. Nothing was pasted from a failure message; the pins never fired.

**What the validator did, measured on the validator of record.** `88 → 88`, and the sets
were diffed with `comm` after **asserting both line counts non-zero** (88 and 88 — the
reviewer's own first `comm` compared nothing with nothing because the validator indents
its WARN lines two spaces and `^\[WARN` matched nothing). OUT: the four dead-ref
warnings on `FR-001/AC-001..AC-004`. IN: four `acceptance criterion has no 'test'` on the
same four criteria. **Nothing else moved in either direction** — the six new `status:`
keys moved nothing at all. The same one-for-one trade as the seven, for the same reason.

**The premise held; the card's *partition* did not, and that is the finding to carry.**
The card says "three different situations, two different repairs" over seven entries. The
population is right, but the card's own recipe for deriving it — *"entries whose `test:`
names a symbol with no `class`/`def` definition in `tests/`"* — **does not select seven.
It selects 191** by the recipe's own exact-name rule, of 421 AC/EC `test:` keys (an
`ast` index of **11005 distinct definition NAMES** — 12418 nodes — over `src/` and
`tests/`; `scratchpad/card316/derive_phantoms.py:84`, `if name in idx`), and **175**
under the authority's rule, `_strict_resolution`'s substring containment over the whole
in-domain index. Intersect either with the three markers and it still selects **18**, not
six — **corrected from 21, which was a miscount of the instrument's own output** (13
`# alternative:` + 4 `# RETIRED` + 1 `# OWED`, re-run at the base). The gap is the
validator's resolution rule, which is a **text search**: `git grep -w` over tracked
files, excluding only `meta/architecture/` and `*.md`. So **11** markered phantoms —
18 − this card's 7, which is the count of the list below rather than a separate figure —
are *equally* unwritten and do **not** warn, because their names sit in prose a tool
cannot tell from a definition:

- **AC-128 / AC-133** (FR-028's *surviving* refuse-branch pair, the control this card
  leans on) are resolved by an AC/test-id comment table in `tests/test_sourcing_random.py`
  — neither has a `def`;
- **AC-124 / AC-125 / AC-126 / AC-173 / AC-111 / AC-132 / AC-114** likewise, from comment
  tables in `tests/test_sourcing_image.py` and `tests/test_orchestrator.py`;
- **AC-252** is resolved by a committed duration dump, `meta/profiling/card-235-durations-after.txt`
  — a `.txt`, so inside the search domain. This is the `commit-no-measurement-dumps` rule
  observed in the wild rather than recalled;
- **AC-190** is the honest version of the same thing, and the registry already says so: its
  comment was CORRECTED on 2026-10-18 because "kept as the record, with its test" turned
  out to be false after CARD-224 deleted the test, and it records that the name "lives on
  only as prose in `tests/test_book_pdf.py`".

The card's seven are therefore the subset that is phantom **and** that the validator can
see is phantom. `derive_set.py` states that as the authority — dead on *both* resolvers,
the module's own `_loose_resolution` and `_strict_resolution` imported rather than
re-implemented — and exits non-zero on anything it cannot box (ADR-0039/R2). Its reading:
11 dead AC refs, `# alternative:` 4, `# RETIRED` 2, `# OWED` 1, `status: superseded` 4,
unclassifiable **0**. The four superseded are FR-001/AC-001..004, which **CARD-317 decided
48 minutes before this card was dispatched** to leave carrying their dead refs, as "the
honest statement that nothing verifies a retired criterion". **That is a live disagreement
with this card's thesis and it is the owner's to settle, not this round's.** Both end
states say "nothing verifies this"; CARD-317 says it with a dead ref plus a
machine-readable `status:`, CARD-316 says it with an absent ref. The warning count is
identical either way. Flagged, not reconciled.

**Every claim in the card verified against the artifact before being acted on:**

| claim as cut | verdict | basis |
|---|---|---|
| all seven ACs present, all seven tests phantom | **holds** | `ast` index, 0 `def`/`class` each; `derive_set.py` |
| AC-206/207 assert 30/45/25 against AC-205's 40/40/20 | **holds** | the three criteria read directly |
| `src/nonogram/admin/book_plan.py:345` says `Split(40, 40, 20)` | **holds, line exact; quotation corrected** | the line reads `DEFAULT_PLAN: DistributionPlan = prefill(150, Split(40, 40, 20))` — quoted as it stands, the annotation no longer dropped — and it is the only `Split` literal in `src/`. Absence narrowed to the spelling searched: zero hits for `30, 45, 25` under `src/`; the string `30/45/25` **does** occur once there, in `book_plan.py:36`'s module docstring as a worked largest-remainder example, which is prose inside the resolution domain and so this card's own subject |
| AC-205 is live and tested | **holds** | `class TestBookCreate_DefaultPlanIs150At40_40_20`, `tests/test_book_plan_storage.py` |
| 30/45/25 was chosen against | **holds** | DEC-036 → ADR-0034, `fixed_150_at_40_40_20`, 2026-09-22 |
| AC-129/134 describe a rejected branch | **holds** | DEC-034 → ADR-0027, `refuse_degenerate_density`, 2026-09-12 |
| the wide-grid survivor asserts the opposite | **holds** | `TestBookSelect_WideGridAboveFloorCarriesNoFlag`, `tests/test_book_select_floor_tiles.py`, and it is **AC-241's** — the criterion the RETIRED comment already names as the replacement |
| AC-379 is owed by CARD-226 | **holds** | CARD-226 is `Status: ready` and owns the slot split |
| AC-379 becomes `kind: review-lens` | **REFUTED** | a no-op; empty `comm` over the WARN set with it planted. See AC-4 |
| "100 → 93", main at 100, main at 90 | **REFUTED** | main is 88, branch is 88. See AC-5 |
| every table line number | **REFUTED twice** | right at dispatch, wrong again after this card's own commit. See the premise block |

**A staleness family found and recorded rather than edited**, because it is a record
change outside this card's set. The round first reported it as **two** —
`FR-028._meta.dec_expected` and `FR-035._meta.dec_expected`, both still `true` although
DEC-034 and DEC-036 are in `resolved.yml` — and **two was the count of what was in front
of the reader, which is the very defect this card convicts its own brief of.** Derived
from the authority instead (every `_meta.dec_expected: true` in `requirements.yml`,
checked against `decisions/resolved.yml` and `decisions/open.yml`), the family is
**SEVEN**, and every one has a resolved DEC behind it with none open:
**FR-025** (DEC-029 → ADR-0024), **FR-026** (DEC-030 → ADR-0025), **FR-027** (DEC-032 →
ADR-0026), **FR-028** (DEC-034 → ADR-0027), **FR-030** (DEC-035 → ADR-0036),
**FR-035** (DEC-036 → ADR-0034) and **FR-044** (DEC-040/DEC-041 → ADR-0038). At two it
reads as a footnote; at seven it is a card, which is why the count mattered. **The
orchestrator is cutting that card and this one only points at it** — the registry's two
NB comments now name the seven rather than the two, and nothing in `_meta` is edited
here.

**The digest cross-check is CORROBORATION, not the mechanism (fix round 1, F-011).**
The departure helper's withdrawal count went 5 → 12, exactly +7, by digest matching
rather than set difference, and the review re-derived it independently and agrees. But
it **gates nothing**: `_refuse_unexplained_departures` reports that count through
`warnings.warn`, `pyproject.toml`'s `[tool.pytest.ini_options]` sets no
`filterwarnings = error`, and the assertion beside it renders only for a departure the
helper CAN name — which, for a pure withdrawal, is none. Observed live in the green run:
the module passes while emitting *"the 'honest-dead' class lost 12 member(s) whose digest
matches no ref the model declares today"*. **The cell that actually gates this move is
the `CENSUS` pin** (`test_the_trace_tests_lists_agree_with_an_independent_reading`),
which mutant 1 reds. And the snapshot is decaying, which is now recorded as a measured
bound beside `HONEST_DEAD_MEMBERS` rather than left to be re-derived: of its 28 stored
digests **9** are still members, **19** have departed, and only **7** of those 19 are
still recoverable by name — the other **12** are unrecoverable, because the declaration
left with the membership. Not trimming the snapshot is still right (erasing a digest
makes that retirement unrecoverable by name); the cost of not trimming is that
paragraph.

**AC-2 is discharged by the guard that already exists, not by a new test.** As written
("no `test:` key in `requirements.yml` names a symbol with no definition in `tests/`") it
is **unsatisfiable on this branch**: FR-001/AC-001..004 still name four, by CARD-317's
explicit decision, and writing a test asserting otherwise would red immediately. The
property the card wants is already enforced, exactly and in both directions, by
`tests/test_check_ref_resolution.py`'s pinned `HONEST_DEAD` and `CENSUS` — an eighth
phantom cannot be added without reddening them, which is what "holds for entries added
later" means. Both baselines were moved by this card as set differences, and both were
mutated to prove they can fail.

**Mutants.** Each plant located by text with its anchor asserted to occur exactly once,
`PYTHONDONTWRITEBYTECODE=1`, `__pycache__` swept both ends, SHA-256 recorded before the
plant and after the restore and found identical in every case
(`requirements.yml` `ea0b89cf…62dad3`, `test_check_ref_resolution.py` `f5478ba8…2affbc`,
`derive_set.py` `41e291ec…36ffe4`).

| # | plant (by text) | region | node(s) it reds | controls green in the same run |
|---|---|---|---|---|
| 1 | restore AC-191's withdrawn `test:` key after its `kind: happy` | **inside** the claim "OUT 7, IN 0" | `test_the_two_directions_of_disagreement_are_exactly_the_measured_ones` (*honest-dead moved: measured (10, '3d6b9c2f…'), baseline (9, 'e109f654…')*) and `test_the_trace_tests_lists_agree_with_an_independent_reading` (the `CENSUS` pin) | 21 of the module's 23 cells |
| 2 | one prose line naming a **trace-only** honest-dead ref in `scratchpad/card316/derive_set.py`, a tracked file inside the search domain | the claim's **edge**: a shrink by *erosion* instead of *withdrawal* | `test_no_verifying_ref_is_resolved_only_by_pipeline_bookkeeping` (*members resolved from outside meta/: ['scratchpad/card316/derive_set.py']*) and `test_the_two_directions_of_disagreement_are_exactly_the_measured_ones` (*falsely-alive moved: measured (156, 'bfe6bafd…'), baseline (155, '8465e851…')*) | 21 of 23 |
| 3 | mutant 1's plant, measured on the **validator** instead of the suite | the AC-5 claim that the trade is one-for-one | not a test node — the WARN set itself: AC-191's "has no 'test'" **out**, its DEAD check ref **in**, total still 88, nothing else moving | the other six criteria's warnings unchanged |

Mutants 1 and 2 red at **different** node pairs, which is the edge the comment on
`HONEST_DEAD` claims: a withdrawal reds at the census pin, an erosion reds at the gate
and at falsely-alive. The two cases are distinguishable by the guard, not just by prose.

**Fix round 1's mutants — four plants, same discipline** (`PYTHONDONTWRITEBYTECODE=1`,
`__pycache__` swept both ends, each anchor's occurrence asserted `== 1`, SHA-256 recorded
before the plant and after the restore and **identical in all four**, `git status` clean
after each, and all four planted on a COMMITTED tree):

| # | plant (by text) | what it is for | result |
|---|---|---|---|
| 4 | restore **FR-001/AC-001**'s withdrawn `test:` key | the claim that the conversion moves no pin — a mutant *inside* a negative claim | **23 passed, NO cell red**; validator stays 88 with that criterion's `has no 'test'` **out** and its DEAD check ref **in**. This is the refutation's mechanism made visible: the ref is still declared by `trace.yml`, so `CENSUS` cannot move, and it was already honest-dead, so `HONEST_DEAD` cannot move. **An honest bound falls out of it: for FR-001's four the pins cannot see the key come back either** — the only instrument that sees this change in either direction is the validator |
| 5 | restore **AC-191**'s withdrawn `test:` key (round 0's mutant 1, re-fired on the rebased tree) | that the pins still gate after the rebase and the new comments | **2 failed, 21 passed** — `test_the_trace_tests_lists_agree_with_an_independent_reading` (the `CENSUS` pin) and `test_the_two_directions_of_disagreement_are_exactly_the_measured_ones` (honest-dead). Identical to round 0; validator flips that one warning back, total still 88 |
| 6 | a **live declared+defined ref with 13 existing loose resolvers**, named as a comment in `meta/kanban/config.yml` | the decisive control for F-012's widened G-2 cell: a ref chosen so that **no pinned class can move** | **1 failed, 22 passed** — and the one red is `test_this_module_resolves_no_verifying_ref_at_all` **alone**. **Counterfactual measured, not argued:** with the plant in place, a trie over the census applied to the OLD cell's domain (`Path(__file__)`, this module only) returns **0 hits**, so the cell as it stood **would have passed**. The widening is what catches it |
| 7 | a live declared ref named in `scratchpad/card316/derive_set.py` | the same, through the **glob** arm rather than the literal arm | **2 failed, 21 passed** — the G-2 cell plus `test_the_two_directions_…` (the planted ref was *falsely-dead*, so giving it a loose resolver also moved `FALSELY_DEAD`; with the class-immobile ref of mutant 6 the G-2 cell is the sole red) |

Mutant 6 is the one that matters: it is a regression that **nothing on this board could
see before this fix round**, caught by the cell this round widened, with the
counterfactual measured rather than reasoned.

**Controls this round does NOT have, stated rather than implied.** AC-3 ("the six keep
their given/when/then and their comments intact") has no test and is not worth one; it is
discharged mechanically at the diff level, which is weaker and labelled as such: every
removed non-comment line in `requirements.yml` is one of the seven `test:` keys, and the
set of **added** non-comment lines is **empty** (`git diff -U0`, filtered). G-3 (AC-205
untouched) falls out of the same reading. A reviewer should re-run that filter rather than
take this sentence for it.

**G-2 re-verified mechanically before each commit**, because this is the rule the family
has broken by accident: a trie over the **union** of the census before and after the
change (580 names) finds **zero** in `tests/test_check_ref_resolution.py` and zero in all
three instruments, and the trie was proved in the positive direction on a known declared
ref in the same run. Refs in the new baseline notes are identified by criterion id.

**And four of those five files had nothing that re-ran the check (fix round 1, F-012).**
The suite's own G-2 cell read `Path(__file__)` — its own module and nothing else — so
`meta/kanban/config.yml` and the three scratchpad instruments were tracked, in domain and
uncovered. The cell's domain is now `_G2_DOMAIN`: this module, `meta/kanban/config.yml`
and `scratchpad/card316/*.py`, **globbed rather than enumerated** so a new instrument
under the card's scratchpad is covered on arrival (ADR-0039/R2), with a floor assertion
so a collapsed domain cannot pass it vacuously. Measured after widening: **0 resolved
refs in all five files, 23 passed**.

**Deliberately NOT widened to all of `scratchpad/`, and the reason is a finding.**
Measured at this commit, a blanket `scratchpad/*/*.py` glob **reds immediately** on three
tracked files belonging to earlier cards — `scratchpad/card318fix/final_mutants.py`,
`y1_control.py` and `y_discrimination.py` — each of which spells **one live declared ref**
as a whole token. So the revival hazard this cell exists to catch is **already in the wild
on `main`**, outside this card's subject. Recorded and routed, not fixed by widening a
glob until the suite reds.

**The second limit is stated rather than closed.** `_G2_DOMAIN`'s trie is built from
`_declared_refs()` — the census **as it stands at run time** — so a ref this card
**withdrew** is outside the cell's reach *by construction*: spelling one of the seven in
any file in the domain passes the cell and still revives the name for the validator's
`git grep -w`, because the validator reads text and not the census. Covering it would mean
storing the withdrawn names, which G-2 forbids in that module. It is a measured bound and
is written beside the cell as one.

**Impact run, fix round 1 — the set is DERIVED, with the rule stated (F-007).** Cycle 1
found round 0's set was named "the registry's readers" and omitted six of the fifteen,
including the two modules the card's own analysis names as the prose-resolvers of
AC-124/125/126/173 and AC-111/132/114. The set is now the union of three enumerable arms:

- **A — every module under `tests/` that reads the registry**: `git grep -l 'requirements\.yml' -- tests/` → **15**;
- **B — the live-sibling modules**: every live `test:` ref on the six FRs this card
  touches (FR-001, FR-019, FR-028, FR-032, FR-035, FR-040), 36 refs, each resolved to its
  defining module by an `ast` index → **12** modules. **5 of the 36 resolve to no module
  under `tests/` at all** — `TestGenerateRandom_AcceptsDensityOneAndNinetyNine`,
  `TestGenerateRandom_RefusesDensityZeroAndHundred`,
  `TestGenerateRandom_DegenerateDensityVerdictIsMadeAtValidateDensitySeam`,
  `TestBookPdf_PuzzleTopEdgeSamePositionOnEveryPage` and
  `TestBookPdf_TwoUpUpperSlotSharesFixedTopEdge` — which is the prose-resolution
  population this card is about, surfacing again from the authority rather than by eye;
- **C — the board's own guards**, because `meta/kanban/**` is inside the validator's
  search domain and the G-2 cell now reads `config.yml`: `test_guard_integrity`,
  `test_impact_set`, `test_kill_matrix`, `test_full_suite_lock`, `test_suite_profile`,
  `test_collected_names` → **6**.

Union: **31 modules** (the figure is the union's size, not the sum). Run in three batches
only because two cells need different environments:

- **29 modules** (the union less `test_kill_matrix` and `test_suite_profile`) —
  **1441 passed, 1 xfailed, 9795 warnings in 212.07s (0:03:32)**;
- **`test_kill_matrix` alone, under `NONOGRAM_TEST_HANG_SECONDS=900`** — **76 passed in 106.33s (0:01:46)**. Its last two
  whole-file reproduction cells exceed the default 120 s hang budget on a loaded box, and
  the guard then `os._exit`s the session leaving its in-tree plant unrestored; `git status`
  was checked after and the tree was clean;
- **`test_suite_profile` alone, under the DEFAULT hang budget**, because an override would
  mask one of its own profile assertions — **450 passed in 42.19s**.

**Total: 1967 passed, 0 failed, 1 xfailed, 0 skipped.** Every count line was
located by pattern (`-q` stacks to `-qq` and prints none; with `-q` the count line is not
the last line), every call carried `-o addopts=`, no `-k` was used and no call was
nodeless. **Skips: 0, read with `-rfs` rather than assumed** — none, so neither DB gate nor a platform gate fired; a stripped PATH would have shown up here as a skip reading like a surviving mutant. The 1 **xfail** is
pre-existing and unrelated: `tests/test_nfr001_generation_time.py::test_20x20_p95_is_under_5s`
(AC-037, generation time still over budget at the high densities; CARD-018's marker). The
full suite was NOT run, `NONOGRAM_FULL_SUITE_LOCK` was not touched and the ignore flag was
not set.

One thing worth recording for the next round rather than re-discovering: during the
second batch `git status` showed `tests/test_db_engine_lifecycle.py` as modified with a
diff that changed size between two reads. That is `test_guard_integrity`/
`test_kill_matrix` planting and restoring its own mutants in-tree. It restored cleanly.
**Do not read a dirty tree during those two modules as a stray edit, and do not commit
while they run.**

**Routed out of this card rather than done in it**, each with the reason, so nothing sits
only in a review YAML:

1. **the re-point blind spot** (F-004) — the registry-side twin of CARD-333's item 2 and
   CARD-319's text-search defect, all three waiting on the same forge_1 decision. Needs a
   check that reads what a test ASSERTS; nothing on this board does. Recorded as a bound
   at three sites and carded, not built here.
2. **the seven stale `_meta.dec_expected: true` flags** (F-006) — a registry record change
   outside this card's set. The orchestrator is cutting it; the count and the seven FR ids
   are above.
3. **the G-2 hazard already live on `main`** (F-012) — three tracked files under
   `scratchpad/card318fix/` each spell one live declared ref as a whole token, so they are
   in-domain resolvers written by hand. Measured, named by site, and left: widening this
   card's glob to cover them would red the suite on another card's artefacts.
4. **AC-2's residue** — FR-001's four were the owner's call and are now settled; what
   remains is that no mechanical instrument on this board sees a `test:` key arrive at or
   leave a criterion whose ref a *second* authority also declares (mutant 4). That is
   item 1's population, one layer out.

**Environment.** Validator and suite both run with
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python` (worktrees share the
main venv; `ruamel.yaml` exists only there). Every pytest call carried `-o addopts=` and
had its count line read by pattern, never by position. No `-k` was used. The full suite
was not run and no lock was touched.
