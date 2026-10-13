# CARD-220: Retire tests whose coverage another test already provides — only with a named survivor

**Status:** ready
**Priority:** P2
**Category:** tech-debt
**Estimate:** 1d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/220-retire-subsumed-tests
**Worktree:** —
**Source:** owner request 2026-10-13 ("make cards for tests curation") — the deletion half, deliberately cut last and narrowest of the four
**Idea:** —
**Wave:** —
**Created wave:** 37
**Deferred waves:** 0
**Depends on:** CARD-217
**Touches:** tests/**
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

**This is the only curation card that deletes anything, and it is deliberately
the most constrained.** 3795 test functions across 198 files, 116 846 lines.
The accumulation is real: 20+ waves of cards, each adding directed tests named
after its own ACs, plus the review cycles' regression tests, plus per-card
baselines. Some of that is now genuinely subsumed — a later card restated a
mechanism and tested it better, and the earlier card's test asserts a weaker
form of the same thing.

**But most apparent duplication here is load-bearing, and deleting it is the
expensive mistake.** Three classes must never be touched:

1. **Independent second implementations.** `tests/helpers/brute_force_oracle.py`
   holds two independent brute-force counters that cross-check each other, and
   `solver/propagate.py`'s `mask_runs` is deliberately reimplemented rather
   than imported so the test tree can cross-check it against
   `clues.encode_line`. These look like duplication and are the correctness
   mechanism (CLAUDE.md states both as project policy).
2. **Per-card AC evidence.** A card's directed tests are what its AC/EC gate
   read as proof. Deleting them removes the traceability a later review
   depends on, even when a property test covers the same ground more broadly.
3. **Corpus minimums.** The project's property tests assert a minimum case
   count inside the test "so the corpus can't silently shrink". Lowering one
   is not curation; it is coverage reduction wearing curation's clothes.

**The rule this card works under — one sentence:** no test is deleted without
naming, in the diff, the surviving test that still covers its claim, and
proving by mutation that the survivor actually fails when that claim is broken.

**What to do.**

1. Start from CARD-217's rankings: candidates are tests that are both
   **expensive** (in the top-50 list or a top-20 file) and **suspected
   subsumed**. Cost alone is never a reason to delete — an expensive test with
   unique coverage is the suite earning its keep.
2. For each candidate, identify its claim (usually an `AC-N` in its docstring —
   this codebase's tests cite them) and search for the test that also makes it.
   Record the pair.
3. **Prove subsumption by mutation, per pair.** Break the production behaviour
   the claim is about; confirm the survivor fails. If the survivor passes while
   only the candidate fails, the candidate is NOT subsumed — keep it, and note
   the finding (the pair looked redundant and was not; that is a useful
   result).
4. Delete only the proven-subsumed ones. In the commit message and the card,
   one line per deletion: `removed <test> — claim <AC-N> covered by <test>
   (mutation: <what was broken, which survivor failed)`.
5. Where two tests are near-identical but neither subsumes the other (different
   edge, same body), prefer **parametrising** them into one test with two cases
   over deleting either — the case count stays, the code shrinks.
6. Re-profile solo (CARD-217's command) and record before/after, plus the
   collected-test-count delta, which must equal the number of deliberate
   deletions and nothing more.

**Expect a small number.** If this card deletes dozens of tests, something has
gone wrong with the subsumption bar — stop and escalate rather than continue; a
large deletion set means the proof step is being skipped.

## Acceptance criteria

- **AC-1** (happy): *Given* each deleted test, *when* the card is reviewed,
  *then* the diff names its surviving covering test and the mutation that
  proved the survivor fails on the broken behaviour. (test: the card's recorded
  mutation evidence, per `review.mutation_check`)
- **AC-2** (guard, accounted count): *Given* the suite, *when* it runs, *then*
  the collected test count equals the pre-card count minus exactly the
  enumerated deletions (parametrised merges keep their case count). (test:
  `TestCuration_CollectedCountMatchesTheEnumeratedDeletions`)
- **AC-3** (guard, protected classes): *Given* the diff, *when* it is
  reviewed, *then* it touches none of: `tests/helpers/brute_force_oracle.py`,
  `tests/property/test_solver_uniqueness.py`, the `mask_runs` cross-check, the
  A4 golden test, or `PropertyTest_CliExports_ByteIdenticalWhateverTheBookGeometry`.
  (test: `TestCuration_ProtectedTestsUntouched`)
- **AC-4** (guard, corpus minimums): *Given* every property test, *when* the
  diff is reviewed, *then* no asserted minimum case count is lower than before
  the card. (test: `TestCuration_CorpusMinimumsNeverLowered`)
- **AC-5** (edge, failed subsumption): *Given* a candidate pair where the
  survivor passes the mutation, *when* the card finishes, *then* the candidate
  is still present and the card records why the pair was not redundant. (test:
  recorded in the card, verified by review)
- **AC-6** (happy, measured): *Given* a solo profile before and after, *then*
  both wall-clocks and the deletion list are recorded. (recorded, not asserted)

## Guardrails

- G-1: No test is deleted without a named survivor and mutation proof (AC-1) —
  this is the card's whole contract, not a preference.
- G-2: The three protected classes above are untouched (AC-3).
- G-3: Corpus minimums are never lowered (AC-4).
- G-4: Do not edit `src/**` — if a test can only be retired by changing
  production code, it is not a redundant test.
- G-5: Do not regenerate or delete anything under `tests/fixtures/**` — every
  fixture carries a "NEVER regenerate" warning, and the superseded golden books
  are deliberately-kept provenance that cost no runtime (verified 2026-10-13:
  only `book_corpus.BASELINE_FIXTURE` is loaded; the other 13 appear solely in
  docstrings).
- G-6: Run this card on a quiet board. Its footprint is `tests/**`, which the
  dispatcher's conflict graph cannot usefully narrow — any other card in flight
  will collide with it.
- G-7: Out of scope — fixture scoping (CARD-218), plan-vs-pixel conversion
  (CARD-219), and rewriting `tests/README.md` (its own backlog item).

## Architecture context

- **FR:** — (test infrastructure)
- **ADR:** ADR-0006/R1 (no new dependency), ADR-0036/R1 (the A4 golden — G-2).
- **CON:** CON-005 (the one mandatory correctness property, protected by
  AC-3/G-2), CON-019.
- **Components:** none (test tree only).
- **Trace:** not applicable.

## Worktree notes

—
