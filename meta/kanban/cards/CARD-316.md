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
   **THAT RECIPE IS REFUTED — it selects 191 entries, not seven, and 21 once
   intersected with the three markers.** Measured: an `ast` index of 11005 definition
   nodes over `src/` and `tests/` finds no `def`/`class` for 191 of the 421 AC/EC
   `test:` keys, because the validator resolves a ref by **`git grep -w` over tracked
   files, excluding only `meta/architecture/` and `*.md`** — so a name spelled in a
   `.py` comment table or a committed `.txt` duration dump resolves. The authority
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
  — it selects 191, which is why the authority had to be the pair of resolvers.
- **AC-2** (no phantom key survives): *Given* the branch, *then* no `test:` key in
  `requirements.yml` names a symbol with no definition in `tests/` — asserted by a
  test, so the property holds for entries added later.

  **AC-2 IS UNSATISFIABLE AS WRITTEN and is not met in that form.** FR-001/AC-001..004
  still name four undefined symbols, and that is **CARD-317's explicit decision of
  2026-10-31**, stamped in FR-001's own block comment: their refs are "the honest
  statement that nothing verifies a retired criterion". A test asserting AC-2's
  universal would red on this branch the day it was written, and writing it would mean
  reversing a sibling card's decision by side effect. What the card actually wants —
  *the property holds for entries added later* — **is already enforced, exactly and in
  both directions**, by `tests/test_check_ref_resolution.py`'s pinned `HONEST_DEAD`
  (9, re-derived) and `CENSUS` (573, re-derived): an eighth phantom cannot enter
  `requirements.yml` without reddening both, and both were mutated this round to prove
  they can. No new test was written, deliberately. **The residue is a real gap and it
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
  - Both severities are WARN because `load_stage` finds no `.skills.yml` in this
    repo and returns `None`. **Note for whoever adds one:** at `stage: quality`
    BOTH of these become ERROR, so this trade is only severity-neutral while that
    file is absent.

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
  (**gate**: node-id set difference with `-o addopts=''`.)
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

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
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

**The premise held; the card's *partition* did not, and that is the finding to carry.**
The card says "three different situations, two different repairs" over seven entries. The
population is right, but the card's own recipe for deriving it — *"entries whose `test:`
names a symbol with no `class`/`def` definition in `tests/`"* — **does not select seven.
It selects 191**, of 421 AC/EC `test:` keys (an `ast` index of 11005 definition nodes
over `src/` and `tests/`; `scratchpad/card316/derive_phantoms.py`). Intersect that with
the three markers and it still selects **21**, not six. The gap is the validator's
resolution rule, which is a **text search**: `git grep -w` over tracked files, excluding
only `meta/architecture/` and `*.md`. So 14 markered phantoms are *equally* unwritten and
do **not** warn, because their names sit in prose a tool cannot tell from a definition:

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
| `src/nonogram/admin/book_plan.py:345` says `Split(40, 40, 20)` | **holds, line exact** | `DEFAULT_PLAN = prefill(150, Split(40, 40, 20))`; no `30, 45, 25` anywhere in `src/` |
| AC-205 is live and tested | **holds** | `class TestBookCreate_DefaultPlanIs150At40_40_20`, `tests/test_book_plan_storage.py` |
| 30/45/25 was chosen against | **holds** | DEC-036 → ADR-0034, `fixed_150_at_40_40_20`, 2026-09-22 |
| AC-129/134 describe a rejected branch | **holds** | DEC-034 → ADR-0027, `refuse_degenerate_density`, 2026-09-12 |
| the wide-grid survivor asserts the opposite | **holds** | `TestBookSelect_WideGridAboveFloorCarriesNoFlag`, `tests/test_book_select_floor_tiles.py`, and it is **AC-241's** — the criterion the RETIRED comment already names as the replacement |
| AC-379 is owed by CARD-226 | **holds** | CARD-226 is `Status: ready` and owns the slot split |
| AC-379 becomes `kind: review-lens` | **REFUTED** | a no-op; empty `comm` over the WARN set with it planted. See AC-4 |
| "100 → 93", main at 100, main at 90 | **REFUTED** | main is 88, branch is 88. See AC-5 |
| every table line number | **REFUTED twice** | right at dispatch, wrong again after this card's own commit. See the premise block |

Two further stalenesses found and **recorded rather than edited**, because they are
record changes outside this card's set: `FR-028._meta.dec_expected` and
`FR-035._meta.dec_expected` both still read `true` although DEC-034 and DEC-036 are in
`resolved.yml`. Noted in each criterion's new comment block.

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

**Impact run.** Two batches, both file-scoped with the count read by pattern:

- the registry's readers and the criteria's own live siblings (13 files:
  `test_check_ref_resolution`, `test_approval_guess_gate`, `test_grid_bound_agreement`,
  `test_nfr001_generation_time`, `test_public_player`, `test_public_player_pages`,
  `test_cli`, `test_collected_names`, `test_solver_strategies`, `test_sourcing_random`,
  `test_book_plan_storage`, `test_book_select_floor_tiles`, `test_book_pdf_band`) —
  **565 passed, 1 xfailed, 0 skipped**;
- the board's own guards, because `meta/kanban/config.yml` is inside the validator's
  search domain (`test_guard_integrity`, `test_impact_set`, `test_kill_matrix`,
  `test_full_suite_lock`, `test_suite_profile`, plus the census module and `test_cli`
  again) — **939 passed, 0 skipped**.

**Skips: zero in both batches, read with `-rs` rather than assumed** — which matters
here, because a stripped `PATH` makes platform-gated cells skip and a skip reads as a
surviving mutant. The single **xfail** is pre-existing and unrelated:
`tests/test_nfr001_generation_time.py::test_20x20_p95_is_under_5s` (AC-037, generation
time still over budget at the high densities; CARD-018's marker, read off `-rx`).

One thing worth recording for the next round rather than re-discovering: during the
second batch `git status` showed `tests/test_db_engine_lifecycle.py` as modified with a
diff that changed size between two reads. That is `test_guard_integrity`/
`test_kill_matrix` planting and restoring its own mutants in-tree. It restored cleanly.
**Do not read a dirty tree during those two modules as a stray edit, and do not commit
while they run.**

**Environment.** Validator and suite both run with
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python` (worktrees share the
main venv; `ruamel.yaml` exists only there). Every pytest call carried `-o addopts=` and
had its count line read by pattern, never by position. No `-k` was used. The full suite
was not run and no lock was touched.
