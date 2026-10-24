# CARD-290: The shared control home's guard derives 13 of the 15 names it declares — and the two it misses are the ones that re-open a closed finding

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/290-derive-the-set-from-the-authority
**Worktree:** —
**Source:** CARD-219 review cycle 2, findings F-203 (minor, non-gating) and F-205 (minor), both routed here rather than taken in CARD-219's last mile — that card's round budget was spent and F-203 is a mechanism change to a derived-set guard. Verified by the orchestrator 2026-10-24 before this card was written.
**Idea:** —
**Wave:** —
**Created wave:** 57
**Deferred waves:** 0
**Depends on:** CARD-219
**Touches:** tests/helpers/shared_fixture_controls.py, tests/test_shared_fixture_controls.py, tests/helpers/book_corpus.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

### 1. The guard's set is not derived from the best authority available (F-203)

`tests/test_shared_fixture_controls.py`'s `_shared_names()` derives the protected
set by introspecting the module and keeping public **functions and classes**.
`tests/helpers/shared_fixture_controls.py` also declares `__all__`. Measured
2026-10-24:

```
__all__ declares : 15
the guard derives: 13
MISSED by the guard: ['DEFAULT_CLASS_PATTERNS', 'DEFAULT_FUNCTION_PATTERNS']
derived but not in __all__: []
```

The derived set is a **strict subset** of `__all__`, so `__all__` is the better
authority on the same question and loses nothing (ADR-0039/R2: derive from an
authority the runtime can enumerate — and prefer the *more* authoritative one
when two exist).

**Why the two it misses are the two that matter, and not an arbitrary pair.**
They are the fallback pattern tuples for pytest's `python_functions` /
`python_classes`. CARD-219's fix round 1 closed cycle 1's **F-002** — a
consumer denominator that emptied under an `autouse` fixture and under a
non-default test-name pattern, so a default-deny decline **passed** under a
narrowed selection — by reading the patterns from `config.getini` at the guard,
with these tuples as the fallback for callers that have no config. **An importer
that binds `DEFAULT_FUNCTION_PATTERNS = ("test_",)` locally reinstates F-002
verbatim, and the agreement guard says nothing.** Latent today; the remedy is
one line.

### 2. Two sibling modules in `tests/helpers/` answer one question differently (F-205)

```
tests/helpers/shared_fixture_controls.py:101  def page_digest(page: Any) -> bytes:
tests/helpers/book_corpus.py:757              def page_digest(page: Image.Image) -> Dict[str, Any]:
```

One returns the raw 32 bytes of a sha256; the other returns a hex digest inside a
dict. **Same name, same package, same question, two readings** — which is the
exact defect CARD-218 shipped as nine duplicated helpers and CARD-219 built the
agreement guard to end. It is **pre-existing** (both present at CARD-219's fork
point `808cf51f`) and it was **not a live defect there**:
`tests/test_book_puzzle_frame.py:138` imports from the shared home, so CARD-219's
measured figures hold. What was defective in CARD-219 was the *sentence* claiming
there were zero such names in the tree; that sentence is corrected and the
collision itself is this card's.

**Decide it, do not just rename it.** Either name is defensible; what is not
defensible is two. Whichever survives, the other's call sites move to it and the
agreement guard's reach is extended to catch the next one — a guard that protects
one module's names while a sibling in the same package shadows them is protecting
the wrong boundary.

### 3. The three shapes CARD-219's cycle 2 named as unprobed

Cycle 2 said plainly it did not check these, and an unexamined area named is
worth more than a silent one. `declared_consumers` is unprobed for:

* a class-decorator `@pytest.mark.usefixtures` on a **nested** `Test` class;
* a **staticmethod** test;
* a **signature-rewriting decorator** (one that replaces `__wrapped__` or rebuilds
  the signature).

Probe each. **Whichever are visible need no change; whichever are not go into the
declared bound at `shared_fixture_controls.py:301` with their own failing
control.** The bound already has four numbered entries and its completeness is
the thing cycle 1's F-002 was: an enumeration that omits a shape reads as having
been checked.

## Acceptance criteria

- **AC-1** (derived from the better authority): *Given* the agreement guard,
  *then* its protected set is derived from `shared_fixture_controls.__all__`, and
  a name added to `__all__` is protected without anyone editing the guard.
  (test: `TestSharedControls_TheCopiesCannotComeBack::test_the_protected_set_is_every_name_the_home_declares`
  — asserted as an **equality** against `__all__`, not a superset, so a name
  dropped from `__all__` while the module still defines it also reds.)
- **AC-2** (guard, F-002 cannot be reinstated): *Given* an importer that binds
  `DEFAULT_FUNCTION_PATTERNS` or `DEFAULT_CLASS_PATTERNS` locally, *when* the
  suite runs, *then* the agreement guard refuses it — caught WITH the `__all__`
  derivation, **missed WITHOUT** it. (test:
  `test_a_locally_bound_pattern_tuple_is_refused`, plus the paired
  missed-before arm. ADR-0039/R1: the control must fail when the mechanism is
  deleted.)
- **AC-3** (one reading of one question): *Given* `tests/helpers/**`, *then* no
  two modules in it define the same public name with different behaviour.
  (test: `test_no_two_helper_modules_answer_one_question_differently` — an AST
  guard over `tests/helpers/*.py`, **default-deny per ADR-0039/R2**: it derives
  the name sets and refuses any collision, rather than checking the one pair this
  card knows about. Ships with a control that fails: a second deliberate
  collision must red it, and a name legitimately re-exported must stay green.)
- **AC-4** (the three unprobed shapes, each resolved either way): *Given* a
  nested-class `usefixtures` consumer, a staticmethod test and a
  signature-rewriting decorator, *then* each is **either** caught by
  `declared_consumers` with a found-now/missed-before pair, **or** named in the
  declared bound with its own failing control. (test: parametrised, one node id
  per shape — not three asserts in one body, because a surviving mutant and a
  never-reached assert look identical.)
- **AC-5** (no coverage loss): *Given* the touched files, *then* their collected
  node-id set loses nothing. (**gate**: set difference with `-o addopts=''`,
  **removals 0**; additions named. Baseline at CARD-219's merge:
  `tests/test_shared_fixture_controls.py` **52**.)
- **AC-6** (the closed findings stay closed): *Given* this card's HEAD, *then*
  CARD-219's cycle-1 probes still fail on their mutants — the faithful alias
  third copy reds the agreement guard, the autouse consumer is seen by
  `declared_consumers`, the decline fires under a narrowed selection, and all six
  retention hiding places are seen. (**gate**: re-run the four, recorded. They
  are on CARD-219's `[FIX ROUND 1 PRE-GATE]` section with their exact shapes.)

## Guardrails

- **G-1: do not edit `src/**`.** Test-tree only; `git diff <fork>..HEAD -- src/`
  must be 0 lines.
- **G-2: no test deleted, renamed, skipped or merged** (AC-5). In particular the
  two per-file `test_no_test_in_this_module_takes_a_fixture_through_getfixturevalue`
  tests in band and frame are redundant with the shared one and **are still not
  this card's to delete** — that is CARD-220's, with the shared version named as
  the survivor.
- **G-3: the three fenced drawn-tie carriers are untouched** (they are
  CARD-220's fence, in `tests/test_book_toc.py`, which this card does not touch
  at all).
- **G-4: do not widen a guard and forget its exemption.** Widening the agreement
  guard to `tests/helpers/**` (AC-3) will need an exemption for legitimate
  re-exports; that exemption is a claim and ships with a control for what it must
  NOT absorb (ADR-0039/R3).
- **G-5: do not change `_set_once`'s cache or its allowance.** Its ~111 MB
  retention is pre-existing, backlogged with the corrected figure, and
  deliberately outside this card — and both exemption controls ask *which cache
  names* are exempt, never how many bytes, which is what kept them true when that
  figure moved by 4.5×.
- **G-6: no new runtime dependency** (ADR-0006/R1: stdlib + Pillow + NumPy); **no
  `hypothesis`**.
- **G-7: do not buy a figure by guarding less** — no narrowed selection, lowered
  corpus or dropped control.

## Architecture context

- **ADR:** ADR-0039/R1 (every claim about what a guard catches needs a control
  that can fail), **ADR-0039/R2 — the card's whole subject**: a guard's set is
  derived from an authority the runtime can enumerate, and where two authorities
  exist the more authoritative one wins; ADR-0039/R3 (AC-3's re-export
  exemption).
- **FR/CON:** none. Test-tree only; no requirement's verifying test changes.
- **Components:** none.
- **Trace:** not applicable.

## Worktree notes

- **Why this was not taken in CARD-219's last mile**, recorded because the
  judgement is the reusable part: that card's round budget was spent at 6 of 6,
  and its orchestrator took cycle 2's two **prose** findings inline while
  refusing this one. The distinction is that F-203 is a **mechanism** change to a
  derived-set guard — the exact class that produced a gating finding in both of
  that card's cycles — and there was no reviewer left to check it. Two corrected
  sentences can ship uncertified; a re-derived guard set cannot.
- **Read CARD-219's card before starting.** Its `[CYCLE 1 ADJUDICATION]`,
  `[FIX ROUND 1 PRE-GATE]` and `[CYCLE 2 ADJUDICATION]` sections hold the exact
  probe shapes for AC-6, the four declared bounds this card extends, and the two
  confounding traps that cost that card two mutants: **a mutant aimed at one
  guard must not also trip the guard in front of it**, and **a mutant that also
  breaks behaviour cannot tell you whether the guard saw the structure**.
- **Estimate 0.75d, not trivial**, per the owner's wave-50 rule: the diff is
  small and the subject is a claim about a guard's reach, which is the card class
  that has consistently spent its whole cycle budget on this board.
