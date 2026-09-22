# CARD-053: Document or remove the orphaned generation/ and analysis/ packages

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/053-generation-analysis-drift
**Worktree:** ../PythonProject4-CARD-053
**Source:** meta/review/20260910T170025Z.yml#F-005
**Idea:** —
**Wave:** —
**Depends on:** CARD-050
**Touches:** src/nonogram/__init__.py, src/nonogram/generation/** (option-dependent), src/nonogram/analysis/strategy_counter.py (option-dependent), tests/test_random_generator.py, tests/test_strategy_counter.py, tests/test_card_050_quality_recognizability.py (the three AC-3 tests only), docs/REQUIREMENTS/DIFFICULTY_ENGINE.md (the CARD-071 banner, if anything is deleted) — NOT meta/architecture/domain/contexts.yml, which is the bounded-context analysis, not the component map
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.25d
**Merge commit:** —
**Blocked by:** —

## Re-cut 2026-09-22 — the orphan claim is half true, and both ACs are wider than they read

Checked against `main` at `7659f2b`. CARD-050 (the dependency) is **done**,
merge `62f8c62`.

**The orphan claim, as it stands today:**

| Module | Production callers | Verdict |
|---|---|---|
| `analysis/quality_metric.py` (303 ln) | `admin/app.py:78` | **live** — CARD-050 wired it, exactly as this card anticipated |
| `analysis/strategy_counter.py` (159 ln) | none | orphaned |
| `generation/random_generator.py` (295 ln) | none | orphaned |

So the card's own grep line — "nothing in `cli.py`/`web/**`/`admin/**`/
`orchestrator.py` imports either package" — is **stale for `admin/**`** and
should be read as applying to the two orphans only.

**What the card does not know: CARD-050 left a live cross-check between the two
orphans.** `tests/test_card_050_quality_recognizability.py:375-400`
(`test_ac3_reimplemented_difficulty_formula_matches_the_original_independently`)
imports `strategy_counter.calculate_difficulty_from_strategies` as the
**oracle** for `random_generator._difficulty_from_strategy_flags`, in the same
shape `mask_runs` is cross-checked against `clues.encode_line`. That happened
because fixing the `src.`-prefixed import (CARD-050 AC-3) made
`test_cli.py::test_every_import_in_the_package_points_inward` flag a lateral
capability import, so the function was reimplemented natively and pinned
against the original.

The consequence: **the two orphans are now one unit.** Deleting
`strategy_counter` alone removes the oracle; deleting `generation/` alone
removes the thing under test. Either goes with that test, or neither goes.

**AC-2 is a seven-file sweep, not a one-file one.** `from src.nonogram`
appears in:

    tests/test_strategy_counter.py      tests/test_random_generator.py
    tests/test_quality_metric.py        tests/test_puzzle_review.py
    tests/test_batch_generator.py       tests/test_pdf_generator.py
    tests/test_book_manager.py          tests/e2e/test_admin_workflow.py

Five of those are admin tests with nothing to do with this card's decision.
`random_generator.py` itself is clean — CARD-050 fixed it — so the *original*
motivation for AC-2 is already discharged; what is left is an unrelated
convention drift in the admin test files. It works only because the repo root
sits on `sys.path` beside `src/`, so the same module is importable under two
names. Worth fixing, but it is its own card, not this one's tail.

**AC-1 is blocked on a decision that is not the implementer's.** The
architecture docstring in `src/nonogram/__init__.py` lists eight components and
omits **`admin/`, `db/`, `analysis/`, `generation/`, `errors.py` and
`limits.py`** — and `admin/` is a whole Flask application, which also makes the
docstring's "there are exactly two adapters (ADR-0019)" false as a description
of the tree. `trace.yml:1414` already records this as a **"KNOWN MAPPING GAP
for the owner"**: COMP-008's declared glob is `src/nonogram/web/**.py`, and
*no component in `trace.yml` or `c4/` owns* `src/nonogram/admin/**` or
`src/nonogram/db/**`. Closing AC-1 literally means inventing COMP-009/COMP-010
(or widening COMP-008), which is an architecture decision the registry is
explicitly holding for the owner.

Two smaller corrections:

- **`meta/architecture/domain/contexts.yml` is the wrong file** for the
  component map (it is the bounded-context analysis). Components live in
  `meta/architecture/c4/components-CTX-001.puml` and in `trace.yml`'s
  `components:` rows.
- Noted, not fixed here: `components-CTX-001.puml`'s COMP-006 text still
  describes `Tier.GUESS` and ADR-0025, both retired by CARD-098/ADR-0031.

**And a tension this card now has with CARD-071, merged today.** The banner
CARD-071 put on `docs/REQUIREMENTS/DIFFICULTY_ENGINE.md` says that document's
engine "is still in the tree and still orphaned" — naming
`analysis/strategy_counter.py` as the prototype that survives while the
rescoring question is open. Deleting it makes that sentence false and removes
the only implementation of the design the banner preserves. Any "remove"
option has to update that banner in the same commit.

## What to implement

`src/nonogram/generation/` and `src/nonogram/analysis/` are not mentioned in
`src/nonogram/__init__.py`'s own architecture docstring (the package's canonical
component map: `cli`, `web`, `orchestrator`, `sourcing`, `clues`, `solver`,
`difficulty`, `export` — nothing else). Grep-verified: nothing in
`cli.py`/`web/**`/`admin/**`/`orchestrator.py` imports either package; their only
importers are each other (`generation/random_generator.py` imports `analysis`)
and their own dedicated test files (`test_random_generator.py`,
`test_quality_metric.py`, `test_strategy_counter.py`).

**Note the overlap with CARD-050**: that card's AC-3 already fixes
`generation/random_generator.py`'s broken `from src.nonogram.analysis...` import
(to `from nonogram.analysis...`) as part of wiring `nonogram.analysis.quality_metric`
into real image-mode quality scoring. **Do not duplicate that fix here** — this
card is the remaining, bigger call: what happens to these two packages as a
whole, now that `analysis.quality_metric` has a real production caller (via
CARD-050) but `generation.random_generator` and `analysis.strategy_counter`
still don't.

1. Decide, and record the decision (as an ADR or a note in the existing
   architecture docstring — implementer's judgment on which fits given this
   project's current level of formality):
   - **Keep and document** `nonogram.analysis.quality_metric` (now a real
     dependency of the admin panel per CARD-050) as a proper component in
     `src/nonogram/__init__.py`'s architecture map, and in
     `meta/architecture/domain/contexts.yml` if the project's model is being
     kept current.
   - **Remove** `nonogram.generation/` (`random_generator.py`) and
     `nonogram.analysis.strategy_counter` if nothing ends up depending on them
     after CARD-050 — confirm this with a fresh grep before deleting anything,
     since CARD-050 may be implemented differently than anticipated.
2. If anything is removed, remove its dedicated tests too
   (`tests/test_random_generator.py`, `tests/test_strategy_counter.py`, and the
   parts of `tests/test_quality_metric.py` that test removed code, if any —
   `quality_metric.py` itself is expected to survive per CARD-050).
3. If `nonogram.analysis.quality_metric` is kept, confirm (after CARD-050 lands)
   that every remaining import of it in the codebase uses the `nonogram.analysis...`
   form consistently — no module should import the same file two different ways.

## The decision, as three concrete options (re-cut 2026-09-22)

**Option A — remove both orphans.** Delete `src/nonogram/generation/` and
`src/nonogram/analysis/strategy_counter.py`, their two test files, and
`test_card_050_quality_recognizability.py`'s three AC-3 tests (vacuous once
the file they parse is gone; CARD-050's AC-3 stays discharged in its record).
Update the `DIFFICULTY_ENGINE.md` banner to say the prototype lives in git
history at this card's merge, not in the tree. ~980 lines out. Keeps
`analysis/` alive for `quality_metric.py` alone.

**Option B — remove `generation/` only.** It is the one with no defender:
nothing imports it, and its `_difficulty_from_strategy_flags` exists only to
avoid importing `strategy_counter`. `strategy_counter` stays as the
DIFFICULTY_ENGINE prototype the banner points at, documented as a prototype on
no shipping path. Costs the CARD-050 cross-check test either way, since the
thing under test goes. ~520 lines out.

**Option C — keep both, document them.** Add an "off the pipeline" section to
the architecture docstring naming `analysis/` and `generation/` as prototypes
with no inbound edge from the adapters, so the map stops being silent about
them. Nothing is deleted; the rescoring option keeps its implementation.

I recommend **B**. `generation/random_generator.py` is a second, unreachable
generator with its own seeding and difficulty story — the kind of thing that
gets found later and mistaken for the real one — while `strategy_counter` is a
prototype whose document CARD-071 just deliberately preserved, and deleting it
the day after that banner was written would be churn. B also keeps this card
away from `analysis/`, which G-1 already fences off.

**Not in any option: the `admin/`/`db/` mapping gap.** That needs a component
id invented, which `trace.yml:1414` reserves for the owner — see AC-1 below.

## Acceptance criteria

- **AC-1** *(narrowed 2026-09-22)* — `src/nonogram/__init__.py`'s architecture
  docstring accounts for `analysis/` and `generation/` — by listing what
  survives, or by not mentioning what is deleted — and the docstring no longer
  reads as if the tree contained only the eight components it maps. The
  `admin/`/`db/` half of the original wording is **out of scope**: no component
  owns those globs, and `trace.yml:1414` holds that decision for the owner.
  Raised as its own card instead of half-done here.
  *(Original wording: "lists every package that actually exists under
  `src/nonogram/` with a real production caller". Unmeetable as stated —
  `admin/` and `db/` are the two biggest packages in the tree and neither has a
  component id to list.)*
- **AC-2** *(narrowed 2026-09-22)* — no file this card keeps imports through
  the `from src.nonogram...` form. The five admin test files that use it are
  **out of scope**: they predate this card, have nothing to do with either
  package, and `random_generator.py` — the file AC-2 was written about — was
  already fixed by CARD-050. Filed separately.
- **AC-3** *(new)* — the suite's pass/fail set is unchanged except for tests
  deliberately deleted with their subject, and each such deletion is named in
  the Worktree notes with the criterion it used to verify.
- **AC-4** *(new)* — if anything is deleted, `docs/REQUIREMENTS/
  DIFFICULTY_ENGINE.md`'s CARD-071 banner is updated in the same commit, so it
  does not keep pointing at a file that no longer exists.

## Guardrails

- G-1: Do not touch `src/nonogram/analysis/quality_metric.py`'s own logic —
  CARD-050 owns wiring it in; this card only decides the surrounding packages'
  fate and updates documentation/tests accordingly.

## Worktree notes

### Delivered 2026-09-22 — option B

`src/nonogram/generation/` is gone (`__init__.py` + `random_generator.py`,
295 lines). `src/nonogram/analysis/` is untouched: `quality_metric.py` is live
(`admin/app.py:78`), and `strategy_counter.py` stays as the prototype of
`DIFFICULTY_ENGINE.md`'s design while the rescoring question is open.

**Suite: 3,670 passed, 26 skipped, 1 deselected** — 24 fewer than `main`'s
3,694, and the arithmetic is exactly the deletions (AC-3):

| Deleted | Count | What it verified |
|---|---|---|
| `tests/test_random_generator.py` | 21 | `RandomNonogramGenerator`'s own seeding, determinism and `get_generator` singleton — all of a class nothing constructs |
| `test_ac3_random_generator_has_no_src_prefixed_import_statement` | 1 | CARD-050 AC-3: the file carries no `from src.nonogram...` import |
| `test_ac3_random_generator_no_longer_laterally_imports_analysis` | 1 | nor any `nonogram.analysis` import — what kept ADR-0007's guard green |
| `test_ac3_reimplemented_difficulty_formula_matches_the_original_independently` | 1 | `_difficulty_from_strategy_flags` against `strategy_counter`'s original |

Nothing else changed: no test failed, none was skipped or renamed.

**Why the three AC-3 tests had to go with the file.** All three parse or
import `random_generator.py` by path; with the file gone they could only be
deleted or rewritten into assertions that a deleted file stays deleted, which
is a test of `git rm`, not of the codebase. CARD-050's AC-3 stays discharged on
its own record — the import was fixed in merge `62f8c62` — and the guard those
tests protected is not weakened: `test_cli.py::test_every_import_in_the_package_
points_inward` walks the whole package on disk with `ast`, so it covers
whatever is left without naming a file. Re-run alone after the deletion: green.
A note at the foot of `test_card_050_quality_recognizability.py` records all
three by name and why they went, so the coverage loss is legible from the file
that used to hold them rather than only from this card.

**The cross-check the re-cut found is what made B non-obvious.** CARD-050 had
pinned `_difficulty_from_strategy_flags` against
`strategy_counter.calculate_difficulty_from_strategies` — so the *only* live
relationship `strategy_counter` had was to the package being deleted. Keeping
it therefore keeps a module with no importer but its own test. That is the
honest cost of option B, accepted deliberately: it is a prototype being
preserved for a decision, not code believed to be reachable.

### AC-1 — what the map now says, and what it still cannot

`src/nonogram/__init__.py` previously listed eight components and was silent
about six other things in the tree, which read as "they are not here". It now
names `errors.py`/`limits.py` as the shared import-free pair, and carries an
"also in the tree, deliberately not components" block for `admin/`, `db/` and
`analysis/`.

It also stops the docstring asserting something false. "There are exactly two
adapters (ADR-0019)" is true of the pipeline and false of the tree — `admin/`
is a third entry point. The text now says which of those it means.

**Not closed here, by design:** `admin/` and `db/` still have no component id.
`trace.yml:1414` reserves that for the owner (COMP-008's glob is
`src/nonogram/web/**.py`; nothing owns the admin or db globs). Inventing
COMP-009/COMP-010 in a P3 tech-debt card would be deciding an architecture
question in a footnote. Filed as a follow-up instead.

### Follow-ups filed rather than absorbed

- **The `from src.nonogram...` import style** survives in five admin test files
  (`test_puzzle_review.py`, `test_batch_generator.py`, `test_pdf_generator.py`,
  `test_book_manager.py`, `e2e/test_admin_workflow.py`) plus
  `test_strategy_counter.py` and `test_quality_metric.py`. It resolves only
  because the repo root sits on `sys.path` beside `src/`, so the same module is
  importable under two names — the exact condition that hid `random_generator`'s
  ADR-0007 violation from the structural guard. AC-2 is met for what this card
  keeps; the sweep is its own card.
- **`admin/` and `db/` need a component id** (the `trace.yml:1414` gap).
- **`c4/components-CTX-001.puml`'s COMP-006 text** still describes `Tier.GUESS`
  and ADR-0025, both retired by CARD-098/ADR-0031.
