# CARD-320: A float reaches `uuid.UUID` through `add_puzzle`, and only under the full suite — four narrower reproductions all pass

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-299's first merge gate, 2026-10-29, which failed 2 of 9736 and whose second failure could not be attributed to the card. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** —
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_book_arrange_size_filter.py, src/nonogram/admin/puzzle_review.py, tests/conftest.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`tests/test_book_arrange_size_filter.py::TestArrangeSizeFilter_PropertyBandIsExactlyItsMembers::test_every_shown_row_is_in_the_band_and_every_member_is_shown[db]`
failed inside a **full** suite run and passes in every narrower run anyone has
tried. The failure is not a wrong assertion — it is a **type** arriving where a
uuid string belongs:

```
tests/test_book_arrange_size_filter.py:544  book_id, ids = panel.stock(sizes)
tests/test_book_arrange_size_filter.py:122  ids = [self.puzzle(w, h, tier) for ...]
tests/test_book_arrange_size_filter.py:112  self.store.approve_puzzle(puzzle_id)
src/nonogram/admin/puzzle_review.py:2232    return self._set_status(puzzle_id, PuzzleStatus.APPROVED)
src/nonogram/admin/puzzle_review.py:2166    row = db.query(Puzzle).filter(Puzzle.id == puzzle_uuid).first()
.../uuid.py:216                             AttributeError: 'float' object has no attribute 'replace'
```

`uuid.py:216` is `hex.replace(...)`, so **`uuid.UUID()` was handed a float**. A
second detail in the same traceback says the constructor died partway: the
half-built object's own `repr` raises
`AttributeError: 'uuid.UUID' object has no attribute 'int'`.

**`add_puzzle` returns a string on both of its paths** — memory mode builds
`f"puzzle_{self._next_id:06d}"` and the database path returns `str(puzzle.id)` —
so the float is **substituted somewhere between that return and the UUID
constructor**, not produced by the id generator. Finding where is the card.

## What is already measured, so nobody repeats it

**It is not reproducible by narrowing. Four attempts, all green:**

| attempt | result |
|---|---|
| the test alone, both params, on `main` `3c3f20db` | 2 passed |
| the test alone, both params, on the branch `f0304cb9` | 2 passed |
| `tests/property/test_book_export_interior.py` immediately before it, both arms | 5 passed / 10 passed |
| a **1018-test prefix** — `tests/e2e`, `tests/helpers`, `tests/property`, then every `tests/test_*.py` through its own file — on `7e434c72` | 1018 passed, 9 skipped, 0 failed, 3:26 |

That last one is the informative negative: **nothing collecting before this test
causes it.**

**And the answer is non-determinism, measured: one red, two greens on the same
code path.**

| full run | tree | verdict |
|---|---|---|
| CARD-299 merge gate 1 | `060df4e2` | **RED** — this test, plus one board-status failure of the orchestrator's |
| CARD-299 merge gate 2 | `7e434c72` | GREEN — 9736 passed, 27 skipped, 1 xfailed, 0 failed, 22:53 |
| `main` baseline | `47905251` | GREEN — 9720 passed, 27 skipped, 1 xfailed, 0 failed, 21:15 |

The only `tests/`+`src/` difference between the red tree and the green one is a
board-status fix in `tests/test_book_pdf.py` that does not touch this path — and
that file collects **after** `tests/test_book_arrange_size_filter.py`, so gate 1's
other failure ran *later* and cannot explain this one.

**What that does and does not establish.** It establishes non-determinism. It does
**not** establish the mechanism, and a single green run is not a fix — which is why
AC-1 below still asks for two unchanged full runs rather than treating CARD-299's
green as the answer. A flake seen once in three runs is a ~33 % reproduction rate at
23 minutes a sample, so the cheap instrument matters more than the sample count:
see item 3.

**The surrounding trees:**

- `main` at `47905251` runs the **full** suite green — 9720 passed, 27 skipped,
  1 xfailed, 0 failed, 21:15.
- CARD-298's merge gate at `1fd39bb1` was green with **the same 9720**, and the
  only non-`meta/` change on `main` between them is one test file that does not
  touch this path.
- CARD-299's gate at `060df4e2` read **9734 passed + 2 failed = 9736**, which is
  `9720 + 16` — exactly that card's additions. The counts reconcile, so nothing
  is being hidden by a collection change.
- **No randomisation plugin is installed** (`pytest-randomly` absent; `addopts`
  is `-q` alone), so suite order is deterministic file order. A failure that
  appears only in the full suite is therefore *position*-dependent, not
  order-random — which makes it reproducible in principle and is why the
  bisection below is worth doing rather than hopeless.

## What to implement

1. **Decide first whether it is deterministic.** Run the full suite on a tree
   where it failed, unchanged, twice. Two reds at the same node id means bisect;
   one red and one green means the subject is **flakiness**, and the card becomes
   about making the flake impossible rather than finding a polluter.
2. **If deterministic, bisect from the tail, not the head.** The 1018-test prefix
   is already cleared, so the polluter lies after it. Halve the remainder, not the
   whole suite.
3. **Find what substitutes the float.** The candidates worth checking before
   guessing: a `monkeypatch` that outlives its test (a fixture patching
   `uuid.uuid4`, `time.time`, or an id helper without a `with` scope or a
   teardown), a class-level attribute on a shared store, and a cached SQLAlchemy
   session or engine carrying state between modules. Name which one it is with a
   measurement, not a plausible story.
4. **Make the failure impossible rather than unlikely.** Per ADR-0039/R2, a value
   of the wrong *type* reaching a uuid conversion should be a stated failure at
   the seam, not an `AttributeError` from the standard library 200 frames down.
   The repair is a guard at `_set_status` that refuses a non-string id by name —
   which also makes the next instance legible instead of cryptic.
5. **Leave the pollution fixed at its source too.** A type guard turns a silent
   corruption into a loud one; it does not stop whatever is leaking. Both halves.

## Acceptance criteria

- **AC-1** (the verdict on determinism is recorded): *Given* two unchanged full
  runs on a tree where it failed, *then* the card states deterministic or flaky
  **with both results**, and the rest of the card is scoped to that answer.
- **AC-2** (the substituting value is named): *Given* the investigation, *then*
  the card names the exact source of the float and the mechanism by which it
  reaches `_set_status` — a file and a line, not a class of cause.
- **AC-3** (the seam refuses the wrong type): *Given* a non-string puzzle id,
  *then* `_set_status` raises a `nonogram.errors.NonogramError` subclass naming
  the argument and its type, rather than letting `uuid.UUID` fail. (**A control
  is owed**: a test passing a float and asserting the named refusal.)
- **AC-4** (the leak is closed at its source): *Given* the polluting test or
  fixture, *then* its patch no longer outlives it, and a control shows the
  leak would be caught — per ADR-0039/R1, a fix with no failing control is a
  claim.
- **AC-5** (the full suite is green twice): *Given* the branch, *then* two
  consecutive full runs pass, with the counts reconciled against `main`'s 9720
  at both ends. One green run cannot distinguish a fix from a flake.

## Guardrails

- **G-1: do not mark the test flaky, skip it, or add a retry.** The failure is a
  wrong type reaching a uuid conversion; a retry hides a real defect in the
  store's seam.
- **G-2: do not attribute to CARD-299 without both arms measured.** `main` at
  `47905251` is green and the branch failed once — that is one sample each, which
  is not an attribution. AC-1 exists because of this.
- **G-3: take the full-suite lock for every full run**, with an **absolute**
  `worktree:` line. The lock is scope-blind: while it exists, a pytest run in any
  other worktree refuses to start, and a test that spawns a nested pytest
  **fails** rather than waiting. Disarm the trap in the same breath as the `rm`.
- **G-4: attribute every skip by name.** The baseline is 27; DB-mode tests skip
  **silently** when `nonogram_test` is absent, so a green run can mean the db arm
  never ran. This card's whole subject is the `[db]` param, so a run where it
  skipped is not evidence.
- **G-5: do not connect to the production database.** The live panel runs on
  `nonogram_poc`; use `sqlite_session_scope` for regressions.
- **G-6: no test deleted, renamed, skipped or merged** — `parametrize` ids
  included. (**gate**: node-id set difference with `-o addopts=''`.)
- **G-7: `\b` is undefined in POSIX ERE and silently matches nothing**, and a
  `-q` written on the command line stacks with `addopts`' own into `-qq`, which
  prints **no** pass/fail count at all. Both read as clean results. Prove any
  instrument in both directions before trusting it.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- INV-006 — the store's fail-closed readings (check: review-lens — verify the substance)
- ADR-0006/R1 — the dependency baseline (check: **the ref is a phantom pointer; the RULE is tested at `tests/test_export_pdf.py:1249`** — verify the substance; the pointer repair is **CARD-317's**)

## Architecture context

- **ADR:** ADR-0039/R1-R2
- **Components:** COMP's puzzle-review store (`src/nonogram/admin/puzzle_review.py`),
  and whatever fixture is leaking — expected in `tests/`, not `src/`.
- **Trace:** nothing is re-stamped. The subject is a seam's type discipline and a
  test-isolation leak, neither of which is a requirement's acceptance criterion.
