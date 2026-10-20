# CARD-259: CARD-252's record is written in three places; single-source it and control the pointer

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Complexity:** trivial
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** —
**Worktree:** —
**Source:** CARD-257 review cycle 1, F-005 (a second surviving doubling) and the card's own declared residue (`reset_engine()` is 135 lines for a 6-line body)
**Idea:** —
**Wave:** 51 (queued)
**Depends on:** CARD-257 (must merge first — it creates the single source this card points at)
**Touches:** tests/conftest.py, src/nonogram/db/session.py, tests/test_db_engine_lifecycle.py
**Review score:** —
**Started:** — · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why — CARD-257 retired one doubling and the review found the next one behind it

CARD-257's cut 1 retired a rule that had **no control**: *"the same words in two places"* was itself a
claim, and nothing red if the two copies drifted. It replaced it with AC-2 — an equality over the
mechanism's own parameters, derived from the code. That worked, and its cycle-1 review then found the
same pattern one file over.

**F-005, measured:** `tests/conftest.py:469-479` still carries, verbatim in substance, the step-3
narration CARD-257 cut from `session.py` — *"Deliberate, but not load-bearing, and the earlier reading of
G-3 here was wrong"*, the moved-ahead-of-Alembic measurement, and *"re-measured as cycle-1 review mutant
R7"*. It is uncontrolled, it is review history shipped inside code, and it was absent from CARD-257's
residue list, which is the part worth a card: the residue was written honestly and still did not see it.

**The card's own declared residue is the other half.** `reset_engine()`'s docstring is **135 lines for a
6-line body**. Its `Who calls it and why` and `What is pinned, and what is not` sections are CARD-252's
record, outside CARD-257's three cuts — correctly deferred rather than taken, because taking them would
have made that card a rewrite of another card's record. This is the card that takes them.

So **CARD-252's record exists in three places**: `session.py`'s `reset_engine()` docstring, `conftest.py`'s
step 3, and `tests/test_db_engine_lifecycle.py`'s class docstring opening paragraph. One of those three is
now **load-bearing for a control** (CARD-257 F-004), which is what makes the drift expensive rather than
untidy.

## What to implement

1. **One statement of the convention and its measurement**, in `reset_engine()`'s docstring, with
   `conftest.py` step 3 reduced to what the *caller* needs — the ordering and why step 3 is last — plus a
   pointer. The refutation, the re-measurement and the mutant name are CARD-252's record, not a thing a
   fixture reader needs inline.
2. **Give the pointer a control, the way CARD-257's AC-2 did.** Not a string comparison of docstrings: an
   equality over the mechanism's own parameters, derived from the code, extended to `conftest.py` as a
   third text. CARD-257's control reads the globals from `session.py`'s AST and the spelling heads off the
   compiled patterns; extend the *same* control rather than writing a second one.
3. **Word-bound every membership test it adds.** CARD-257's gating finding was that `engine` is a
   substring of `reset_engine`, `_init_engine`, `_engine_url` and `create_engine`, so the arm could not
   fail for that name. Any text check this card adds carries the word boundary and a **per-name** matrix.

## Acceptance criteria

- **AC-1** *Given* the single-sourced record, *then* each clause of CARD-252's record appears **once**,
  and the other two sites carry a pointer. No clause is lost: split the retired copies and show every one
  survives somewhere, as CARD-257's AC-1 did.
- **AC-2** (the control) *Given* the three texts, *then* one test holds that all three agree on the
  mechanism's parameters, **derived from the code**, with every membership test word-bounded and a
  **per-name, per-text** kill matrix — three names × three texts, not one mutant that happens to pick a
  name without the hazard.
- **AC-3** *Given* the cuts, *then* `tests/test_db_engine_lifecycle.py`'s per-assert kill matrices are
  unchanged for every arm, measured with the line-count-preserving instrument and **any-RED aggregation**.
- **AC-4** (guard) *Given* all cuts, *then* the tree sweep is unchanged — 9 sites, 6 pairs, dict-equal,
  zero matches elsewhere — and `session.py`'s docstring-stripped AST still hashes to
  `bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c` (dump length 9154), byte-identical to
  main's, proving the `session.py` edit is docstring-only rather than asserting it.

## Guardrails

- G-1: **No mechanism change.** Docstrings and comments only, plus the one extended control.
- G-2: No clause retired without a named surviving statement.
- G-3: `nonogram_poc` is never created, dropped, connected to or truncated; `_refuse_unless_test_database`
  is neither widened nor bypassed.
- G-4: No new runtime dependency (ADR-0006/R1), stdlib only.
- G-5: ADR-0036/R4 — no codepoint in U+25A0..U+25FF, U+2022 or U+2219 in any `src/nonogram/**` string
  literal, docstrings included. `pdf_generator.py`'s three U+2022 are the declared exemption; a clean-scan
  claim over the whole tree would be false.

## Worktree notes

- **[Do not take timing measurements]** other cards may share this machine.
- **[The trap]** This is the third card in a row to cut prose that was each added to close a real finding.
  The failure mode is cutting a sentence that is the **only** statement of a bound. CARD-257 paid for this
  with a 41-clause survival diff; do the same.
- **[The second trap]** `tests/test_db_engine_lifecycle.py`'s class docstring **opening paragraph is
  load-bearing** — it is the only place all three globals are written out, and the control holds the text
  to names in double backticks, which the scan does not count. CARD-257 F-004 added a clause saying so.
  Do not delete that paragraph as CARD-252 history without moving what the control needs.
- **[Instrument traps, all three paid for already]** aggregate **any-RED**, never last-write-wins (a RED
  from an assert inside a `for` loop is otherwise lost); keep mutants **line-count-preserving**; target the
  occurrence **inside the arm you mean** (identical source lines appear earlier in the file and a
  first-occurrence replacement silently mutates the wrong arm, returning a false all-green); and report the
  **domain** of any per-assertion figure — CARD-256 reported a test count as an assertion count.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`, reading the ADR files
  **case-insensitively** for the reach-limit idiom. This card is about ADR-0039/R1.
