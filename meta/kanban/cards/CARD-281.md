# CARD-281: The figures a guard module states about itself are copies, and copies are what drifted five times on one card

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 0.75d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/281-figures-about-itself
**Worktree:** —
**Source:** CARD-264's narrow re-entry review, 2026-10-23 — three minors (F-003, F-004, F-005) that are one cluster, left open deliberately because closing them needs a mechanism rather than a sentence.
**Idea:** —
**Wave:** —
**Depends on:** CARD-264 (it merges the module this card operates on; every line number below will move)
**Touches:** tests/test_guard_integrity.py, tests/test_web_server.py

## Why — the same defect, five times, in the one module whose subject is false claims

CARD-264 spent four fix rounds and five review cycles, and **every gating finding after its third cycle
was a figure or a direction-count the module states about itself**, never a defect in a guard:

| round | the figure | what it was |
| --- | --- | --- |
| cycle 4, F-2 | a declared bound's wording | narrower than the guard it described |
| cycle 5, F-002 | *"nine tables, four keyed, 11 entries"* | the tree **before** the same round added the tenth |
| re-entry, F-001 | *"seven directions, each naming the line"* | two of the seven name the **table** |
| re-entry, F-002 | *"eleven lines of slack"* | `57 − 45` is **twelve** |

Each was corrected by hand, and the correction is a copy too. The module already knows the better
pattern and uses it **once**: `test_the_path_suffix_census_is_the_one_this_comment_states` parses the
`#: SPANS:` declaration out of its own source and re-derives every figure in it, so a drift between the
comment and the tree **reds** instead of ageing. Everything else is prose a reader must trust.

## What survives of the cluster, measured

**F-004/F-005 — `5 / 12 / 57` exists in four places and nothing re-derives three of them.** The equality
`assert _declaration_census(_MEASURED_TABLE_LINE_KEYS) == (5, 12, 57)` is the authority and is checked on
every run. The prose copies at `:2960`, `:3159` and `:4801`, and a fourth copy as a literal inside the
census assert's **own failure message** (beside the tuple it reports on), are checked by nobody. All four
are correct today. The drift direction is one-way: the authority moves with the tree, the copies do not.

**F-003 — the "seven directions, each with a constructed case" count has no failing control.** Measured
on CARD-264's final tree: delete the `added` case — the one fix round 5 built to answer the review — from
the direction loop, and the file is **167 passed, exit 0**. The count and the cases agree today, and the
gap is pre-existing rather than introduced (it was equally true of the four cases at `8727e519`), which
is why the review filed it Minor. But it is the same shape as every row in the table above: a quantity
nothing recomputes.

## What to implement

1. **One mechanism, applied to every self-describing figure in both modules.** Follow the census
   precedent exactly: the figure lives in a declaration the test **parses out of its own source**, and
   the test re-derives it from the tree. Candidates enumerated by this card's own audit, not by reading:
   every `#:` block and docstring in `tests/test_guard_integrity.py` and `tests/test_web_server.py`
   containing a bare integer that describes the module's own tables, cases or directions.
2. **The direction census.** `TestTheDeclaredMissTables`' direction loop declares its own cases; the
   count in the surrounding prose must be derived from the loop rather than written beside it, so
   deleting a case reds the count.
3. **The failure message's literal.** A message that prints `(5, 12, 57)` beside the tuple it compares
   against is a second copy in the place most likely to be read as authoritative; print the expectation
   from the same source the assertion uses.
4. **Delete the copies that have no reader**, rather than adding controls for each. Four copies of one
   triple is three too many; the cheapest honest state is one authority plus pointers to it.

## Acceptance criteria

- **AC-1** *Given* both modules, *then* every integer that describes the module's own tables, entries,
  source lines, cases or directions is either **re-derived by a test from the tree** or **removed** —
  and the enumeration of such integers is produced by this card's own `ast`/text audit, committed, so a
  figure added later is caught rather than discovered.
  (test: `TestSelfDescribingFigures_EveryQuantityIsDerivedOrAbsent`)
- **AC-2** *Given* a **planted** drift in each derived figure (one per figure, by mutation), *then* the
  owning test **reds naming the figure and the line that states it** — the control that CARD-264's four
  corrected figures each lacked.
- **AC-3** *Given* a case deleted from `TestTheDeclaredMissTables`' direction loop, *then* the
  direction-count claim **reds**. Measured today as the gap: with the `added` case deleted the file is
  167 passed, exit 0.
- **AC-4** *Given* the census triple, *then* exactly **one** authority states it; `grep` for the triple's
  literal finds the authority and no other copy, asserted by a test rather than by a sweep at review
  time.
- **AC-5** *Given* the whole change, *then* no guard's behaviour moves: `_classify`,
  `_is_type_expression`, `_IDENTIFIER_CHAIN`, `_unkeyed_declaration_lines`, `_declaration_census` and
  `mentioned()` are byte-identical, and the collected count of both files is unchanged.

## Guardrails

- **G-1:** no guard behaviour changes. This card edits what the modules **say about themselves** and the
  tests that hold those statements. Any change to a detector is out of scope and belongs on its own card.
- **G-2:** `CLAUDE.md` untouched.
- **G-3:** no new dependency; stdlib only (`ast`, `re`, `pathlib` are already imported where needed).
- **G-4:** do **not** fix a figure by deleting the sentence that carries it when the sentence is the
  reason a reader understands the mechanism. The choice is *derive it* or *remove the number and keep
  the prose* — never remove the explanation to avoid the control.
- **G-5:** every new control gets a mutant that **deletes the mechanism it names**, not one that breaks
  what this card added. That rule's absence from one brief cost CARD-264 a full round.
- **G-6:** keep every edit **line-count preserving** where a review report or a card cites an assert by
  line number, or state in the notes which citations moved and re-derive them.
- **G-7:** no timing measurements, no durations (inherited from CARD-264 and for the same reason).

## Architecture context

ADR-0039/R1 is the rule this card finally applies to the module's own prose: *a claim needs a control
that CAN FAIL.* CARD-264 proved the rule for the guards; its own figures were the one place it kept
being broken. The precedent to copy is in the same file —
`test_the_path_suffix_census_is_the_one_this_comment_states`, and `MEASURED_*`'s per-line keying contract
above `_MEASURED_TABLE_LINE_KEYS`, which decided that **keying is per source line** and is worth reading
before touching anything here.

## Worktree notes

- **Locate everything by text, not by line.** CARD-264 paid twice for line numbers that had moved under
  a rebase; this card depends on that card and inherits the shift.
- The review reports `meta/review/20261023T103148Z-CARD-264-cycle5.yml` and
  `…T121204Z-CARD-264-reentry.yml` hold the measurements behind every row of the table above, including
  the exact cells each planted drift reds at. Read them rather than re-deriving from scratch.
- **The honest counter-argument, recorded so it is argued and not ignored:** four copies of a correct
  triple harm nobody today, and a mechanism that derives figures from source is itself code that can be
  wrong. The answer is the table at the top — this exact class of copy drifted **four times in one day**
  on one card, three of those times inside the round that was fixing the previous one. A mechanism that
  can be wrong and is tested beats prose that cannot be tested at all.
