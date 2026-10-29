# CARD-310: A test's verdict stops depending on a sibling working tree — the board-time assertions move to the board's own gate, and the pattern is decided once

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** architectural
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** —
**Worktree:** —
**Source:** CARD-298 review cycle 2's F2-001, 2026-10-29, verified independently by the orchestrator. Cut on owner decision the same day. The finding was deliberately left non-gating there and its preferred remedy deliberately not attempted, because it changes a derivation and wants its own control in the same commit.
**Idea:** —
**Wave:** 67
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** CARD-298
**Touches:** tests/test_book_pdf.py, meta/kanban/config.yml, meta/kanban/README.md, tests/test_suite_profile.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

CARD-298 built the landing-direction half of ADR-0042/R2's expiry guard: a cell that
fails when every card named in a raster declaration's `expires_with` has reached
`done` while the entry is still in the registry. It is real engineering and it
closed a measured hole. **But to see a current board it reads the MAIN WORKING
TREE's card directory, because a card worktree's `meta/` is a snapshot of its cut
(`/commit` excludes `meta/`).**

Measured, from an out-of-tree plugin with the instrument proven on the unmutated
tree first — imposing ordinary-checkout semantics
(`main_repo_root = lambda worktree: worktree`, the documented fall-through at
`tests/full_suite_lock.py:167` when `.git` is a directory):

```
2 selected, 2 passed        # unmutated: the instrument works
1 failed, 1 passed          # ordinary-checkout semantics
FAILED test_no_declaration_outlives_the_cards_that_remove_it
tests/test_book_pdf.py: AssertionError  Left contains one more item: 'CARD-309'
```

The worktree held **304** card files against the main tree's **308**, with
`CARD-309.md` — the card the declarations name — among the four missing. So the
round's docstring claim that an ordinary checkout "sees no difference" was true of
the return value and **false of the test's verdict**; CARD-298 retired that sentence
in `35a4de1a` and wrote the honest property in its place:

> **this cell's verdict is a function of the main working tree's card directory,
> not of a commit** — marking `CARD-309` done on `main` reds a card branch with no
> commit made to that branch.

**That is the defect this card fixes.** It is a false RED and never a false green,
the merge gate runs from the main worktree, a fresh clone of `main` carries every
card, and **this repo has no CI** (`ci/` and `.github/` are absent), so nothing is
broken today. What is wrong is the shape: a test that is not reproducible from the
commit it is run against.

## What makes this a pattern decision and not a one-line move

**Measured on `main`: not one test reads `**Status:**`.** The coupling is novel in
the half that matters:

| reader | what it takes from the board | moves when |
|---|---|---|
| `tests/test_full_suite_lock.py` | path **prefixes** (`meta/kanban/cards/`) for a prose exemption | ~never |
| `tests/test_suite_profile.py` | a **listing idiom** as an allowed-negative | ~never |
| `tests/test_web_server.py` | a card **filename**, in a docstring citation | ~never |
| **CARD-298's cell** | **a card's mutable `Status:`** | **several times a day** |

`tests/test_suite_profile.py:3581-3588` carries an explicit allowed-negative for
*"a card-registry walk, of which this repo invites many"* — so walking the board is
sanctioned and will recur. **Reading a card's status is the new thing**, and the
distinction to write down is **existence versus workflow state**: a card's name is a
structural fact that outlives a wave, its status is a board-time fact that does not.

## What to implement

1. **Decide where a board-time assertion lives, and record the decision.** Three
   candidates; the card does not pre-pick one, but two are already ruled out by
   measurement and must stay ruled out:
   - **A board-side gate** — a repo-local check run where the board is current by
     construction (card close, board regeneration, the per-wave smoke test). The
     board is the subject rather than a neighbour. Note the constraint:
     `forge:kanban`'s own `done` flow lives in `forge_1` and **must not be edited**
     (CARD-308/G-1), so a repo-local home is needed.
   - **Commit-addressed reading** — read the board through `git show <ref>:…`
     rather than the filesystem, so the input is a commit rather than a working
     tree. Precedent exists: `tests/test_impact_set.py:410` already shells to
     `git rev-parse`. **State honestly whether this actually fixes it**: `main`'s
     tip still advances without a commit to the branch under test, so this may
     only narrow the window rather than close it.
   - **A committed derived artefact** — the board's tooling writes the set of
     terminal card ids into a tracked file that the suite reads. The input becomes
     commit-local, and a card branch's copy is **stale in the safe direction**: it
     would miss a newly-stale declaration rather than invent one. Say so if you
     choose it, because "fails safe" is the argument for it and also its limit.
2. **Move the landing-direction assertion out of `tests/`** (or re-home it per
   item 1) **and leave the conversion-direction assertion where it is.**
   `_declaration_findings`'s conversion check fires only when a page's medium
   actually changed, which is a fact about the tree under test — commit-local, and
   correct in the suite. The two directions are not interchangeable and the split
   must be stated wherever a reader meets either.
3. **Write the pattern down where the next author will hit it**, not only in this
   card: existence-of-card walks are fine in `tests/`; **status-of-card assertions
   are not**, and the reason is one sentence — a test must be a function of the
   commit it runs against.
4. **Keep `ADR-0042/R2`'s expiry covered at every moment of the change.** The
   landing direction is the only thing that catches a card closing **without**
   converting, which is the mis-attribution CARD-298's cycle 1 was gated for. A
   window in which neither home asserts it is a regression, however short.

## Acceptance criteria

- **AC-1** (no test's verdict depends on a sibling working tree): *Given* the
  suite run from a linked card worktree whose `meta/` snapshot predates a card,
  *then* no cell reds for that reason. (**gate**: reproduce CARD-298's F2-001
  probe — impose ordinary-checkout semantics from an **out-of-tree** plugin, with
  the instrument proven on the unmutated tree first, and show the cell that used
  to red now does not.)
- **AC-2** (the expiry is still caught in the landing direction): *Given* a
  declaration whose every named card is terminal while the entry is present,
  *then* the new home **fails**. (**Two mutants per ADR-0039/R1**, one inside the
  claim and one at its edge: every named card done, and all-but-one done.)
- **AC-3** (it is not an ungated door): *Given* the new home, *then* there is **no
  conditional skip** and no path on which the assertion silently does not run —
  per ADR-0039/R2 an unanalysable or unreachable shape is a **failure**. (**gate**:
  name where it runs and show it running; a skip count of zero stated by name.)
- **AC-4** (the conversion direction is untouched and still green): *Given* the
  branch, *then* `_declaration_findings`' conversion check and its tests are
  unchanged, and the split between the two directions is stated in the code the
  reader meets first.
- **AC-5** (the pattern is recorded, derived, not asserted by prose alone): *Given*
  the repo, *then* the existence-versus-status rule is written where the next
  author meets it, **and** a guard derives the rule rather than restating it — a
  new `**Status:**` read from `tests/` is a failure, classified from the tree per
  ADR-0039/R2, with its own control that a card-**name** walk is **not** flagged
  (otherwise the guard forbids the sanctioned pattern too).

## Engineering constraints

- **EC:** across every module under `tests/`, the set of board reads is derived and
  partitioned into existence reads and status reads, with the status set empty —
  neither direction slack, derived from the tree rather than from a list in the
  test.

## Guardrails

- **G-1: do not edit anything under `/Users/omelnikova/MyProjects/forge_1/`.** The
  kanban `done` flow is forge-side; this card needs a repo-local home.
- **G-2: no conditional skip, and no `xfail`,** to make the problem go away. A cell
  that does not run on a card branch is an ungated door — the shape AC-3 exists to
  refuse.
- **G-3: do not re-implement the linked-worktree walk.**
  `tests/full_suite_lock.main_repo_root` already does it, is driven in both
  directions by `tests/test_full_suite_lock.py:778-779`, and a second
  transcription is how the two come to disagree. If the chosen design stops needing
  it, stop **calling** it; do not copy it.
- **G-4: do not weaken `_RASTER_DECLARATIONS` or any `expires_with` value** to
  simplify the check. The registry is the authority; this card changes who reads it
  and from where, not what it says.
- **G-5: no test deleted, renamed, skipped or merged** — `parametrize` ids
  included. A **move** is expected here, so state the before/after node ids
  explicitly rather than letting a rename hide inside the diff. (**gate**: node-id
  set difference with `-o addopts=''`, both trees, with every moved id accounted
  for by name.)
- **G-6: a skip-related control attaches its marks by ASSIGNING `pytestmark`,
  never by decorator.** `tests/test_suite_profile.py::_conditional_silences`
  AST-walks every guarded source for a `skipif`/conditional-`xfail` and reports it
  **whatever it is keyed on**; a decorator in a synthetic probe registers as a new
  host-state silence tree-wide. The CARD-291 merge gate went red on exactly that.
  Verify `_conditional_silences(<your file's source>) == []`.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0042/R2 — a raster page is declared with a reason; an expired declaration is a defect (check: CARD-298's derived guard, whose landing half this card re-homes)
- ADR-0039/R1 — a claim needs a control that CAN fail; two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: **DEAD REF** — verify the substance; see CARD-307)

## Architecture context

- **ADR:** ADR-0042/R2, ADR-0039/R1-R2
- **Components:** COMP-009 (incidentally — the subject is the test instrument, not the generator)
- **Trace:** nothing is re-stamped. `trace.yml` holds **no ADR-0042 rule rows at all** (measured 2026-10-29: prose only, at `:1813` and `:1853`), which is the mistake CARD-298 inherited and corrected — do not write a Trace line promising a row that does not exist.

## Worktree notes

- **Serializes against CARD-306**: both declare `tests/test_book_pdf.py`. Neither
  names a `conflict.hotspots` path, so the overlap rule is what orders them, not the
  hotspot rule.
- **The false-RED direction is why this is P2 and not P1.** Nothing can ship a wrong
  book because of it. What it can do is red a card branch for a reason that has
  nothing to do with that branch, which costs a round the way a flaky gate does —
  and this board has paid that cost twice already from other causes.
- CARD-308 is the sibling in spirit: that card is about an instrument that reads
  **prose** and calls it a definition; this one is about an instrument that reads a
  **neighbouring working tree** and calls it the board.
