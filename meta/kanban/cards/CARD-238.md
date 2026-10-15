# CARD-238: The suite-timing tests stop asserting on gitignored host state

**Status:** ready
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/238-timing-log-host-state
**Worktree:** —
**Source:** found in flight at CARD-235's merge gate, 2026-10-15; owner decision the same day to card the test fix and leave the local log untouched
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** tests/test_suite_profile.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

Two tests in `tests/test_suite_profile.py::TestSuiteTimingLog_FormatUnchanged` read the **live**
`meta/kanban/suite-timing.log` and assert on its contents. That file is gitignored
(`.gitignore:61` — `*.log`), so it is host state: it exists on some machines and not others,
differs per worktree, and is appended to by the pipeline itself. Their verdict is therefore a
fact about the machine, not about the code.

```python
@pytest.mark.skipif(
    not TIMING_LOG.exists(),
    reason="suite-timing.log is gitignored (*.log) and absent from this checkout",
)
def test_the_real_log_is_entirely_well_formed(self) -> None:
    text = TIMING_LOG.read_text(encoding="utf-8")
    assert ranker.malformed_timing_lines(text) == []

@pytest.mark.skipif(not TIMING_LOG.exists(), reason=...)
def test_the_last_entry_is_this_cards_profiling_run(self) -> None:
    entries = ranker.timing_log_entries(TIMING_LOG.read_text(encoding="utf-8"))
    last = entries[-1]
    assert "profil" in last["label"] or "profil" in last["notes"], ...
```

**Both are currently failing somewhere, and for different reasons.** Measured 2026-10-15:

1. **`test_the_real_log_is_entirely_well_formed` is RED on main.** The local log carries
   CARD-217's own merge-gate entry, and its `[135ms/test] — the profiling card's own gate; +83
   tests, …` suffix is rejected by `malformed_timing_lines`. So CARD-217 wrote an entry its own
   format validator refuses: 1 malformed line of 17 non-comment lines.
2. **`test_the_last_entry_is_this_cards_profiling_run` is RED for any card whose gate logs a
   line** — which `cmd-run.md` instructs the dispatcher to do on every gate and every wave smoke
   test. It went red at CARD-235's merge gate with `expected the profiling run last, got
   card-235-merge-gate`. The assertion can only hold in the moment just after a profiling run,
   and the pipeline's documented behaviour is to append after that.

**And the skip is not a safety net, it is the reason nobody noticed.** The two tests skip when the
log is absent, which is the common case in a fresh worktree. That is why CARD-234's gate was green
at 11 skips while CARD-235's was red at 9 — the same suite, the same code, a different host file.
A gate whose verdict flips on whether a gitignored file happens to exist is not a gate.

**What to change.** Keep the format contract — that part is valuable and the rest of the class
already tests it well against strings the test constructs itself (`GOOD`, `BAD`, the
commented-out-entry cases). What must go is the dependency on the live file:

- The format assertion should be made against entries the test builds, not against whatever is on
  the host. The class already has `self.GOOD` / `self.BAD` for exactly this.
- If it is genuinely valuable to check that *this repo's* log is well formed, that belongs in a
  tool the owner runs deliberately (a `rank_durations.py` subcommand, or a `/forge:ci` style
  check), not in the suite — because the suite's job is to judge the code, and the log is not code.
- The "last entry is a profiling run" assertion should be deleted or restated. As written it
  encodes "a profiling run happened most recently", which is a claim about workflow order that no
  code can keep true. If something about profiling-run ordering is worth asserting, assert it over
  a constructed log.

Decide and state in the implementation which of these shapes you chose and why. Do not simply
widen the skip condition — a test that skips more often is not a test that works.

## Acceptance criteria

- **AC-1** (happy, no host coupling): *Given* the test module, *then* no test in
  `TestSuiteTimingLog_FormatUnchanged` reads `meta/kanban/suite-timing.log`, proved structurally
  the way `tests/test_cli.py`'s import guard walks the tree with `ast` — so a future test that
  re-introduces the read fails. (test: `TestSuiteTiming_NoTestReadsTheLiveLog`)
- **AC-2** (happy, the format contract survives): *Given* the well-formed and malformed entry
  corpora the class constructs, *then* the parser's behaviour on each is asserted exactly as
  before — this card removes a coupling, not coverage. Show the before/after test count for the
  class and account for every removed assertion.
  (test: the existing `TestSuiteTimingLog_FormatUnchanged` cases, unchanged in substance)
- **AC-3** (guard, it cannot pass by skipping): *Given* the class, *then* no test in it carries a
  `skipif` on a file's existence, and the class's collected count is the same whether or not
  `meta/kanban/suite-timing.log` exists on disk — run it both ways and record both.
  (test: `TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog`)
- **AC-4** (edge, the malformed entry that started this): *Given* CARD-217's real entry text
  (`… 963s PASS (7156 passed, 9 skipped, 0 failed) [135ms/test] — the profiling card's own gate;
  …`), *then* the test suite states unambiguously whether that shape is legal. If it is legal, the
  parser is fixed to accept it and the fix is tested; if it is not, a test asserts it is rejected
  and the writer that produced it is named in a comment so the next author does not repeat it.
  Decide which, and say why. (test: `TestSuiteTimingLog_FormatUnchanged` with that literal)
- **AC-5** (guard, the suite's verdict stops depending on the machine): *Given* the full suite run
  twice — once with `meta/kanban/suite-timing.log` present and once with it absent — *then* the
  pass/fail/skip counts are identical. Record both runs.
  (test: two recorded full-suite runs, locked and solo)

## Guardrails

- G-1: Do not touch `meta/kanban/suite-timing.log` itself. **Owner decision, 2026-10-15:** their
  timing history is not to be edited by this card. If the file's content is wrong, that is a
  separate matter and the owner holds it.
- G-2: Do not weaken the format contract to make anything pass. The parser's accept/reject
  behaviour on constructed entries must be at least as strictly asserted after this card as
  before — AC-2 is the evidence.
- G-3: Do not touch `meta/profiling/rank_durations.py`'s parsing behaviour unless AC-4's decision
  is "the shape is legal", in which case the change is to the parser and must be tested. Say which.
- G-4: `tests/test_suite_profile.py` only. The rest of the profiling harness (CARD-217's
  artefact checks) stays as it is.
- G-5: No `src/**` change. No new dependency (ADR-0006/R1).

## System contract

- ADR-0006/R1 — runtime dependencies are exactly stdlib + Pillow + NumPy (check:
  `tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`)

## Architecture context

- **FR:** — (untraced test-integrity card; its done-ness is the ACs above)
- **Components:** — (tests only)
- **Trace:** not updated by this card.

## Worktree notes

- [Why P1] It is the third test-integrity defect to block this wave, after the memory headroom
  guard (CARD-237) and the unguarded poll interval (CARD-235's F-001). All three share one shape:
  **a test whose verdict depends on something other than the code it claims to judge** — a
  drifting interpreter footprint, a frozen artefact, and now a gitignored host file. The merge
  gate runs once per card and 16 cards of the interior redesign remain.
- [Why the skip hid it] `skipif(not TIMING_LOG.exists())` reads as defensive and is the opposite.
  It converts "this test cannot run here" into silence, so the suite reports green on a machine
  where the check never happened — and red, confusingly, on the one where it did. The lesson
  generalises past this card: a skip predicated on host state is a hole in the gate, not a
  concession to portability.
- [Measured, so the next card need not re-derive it] 1 malformed line of 17 non-comment lines in
  the owner's local log, the last *parseable* entry being `card-217-profiling-run`; CARD-234's
  worktree green at 11 skips with the file absent; CARD-235's worktree red at 9 skips with it
  present; same suite, same code, same host.
