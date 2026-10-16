# CARD-238: The suite-timing tests stop asserting on gitignored host state

**Status:** review
**Priority:** P1
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/238-timing-log-host-state
**Worktree:** ../PythonProject4-card-238
**Source:** found in flight at CARD-235's merge gate, 2026-10-15; owner decision the same day to card the test fix and leave the local log untouched
**Idea:** —
**Wave:** 41
**Depends on:** —
**Touches:** tests/test_suite_profile.py
**Review score:** 6.0 (cycle 1/3)
**Started:** 2026-10-15T17:52:53Z
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
  **AMENDED at review cycle 1, 2026-10-16 — that branch is now LICENSED, because the data split
  AC-4's question in two and one half answers "legal".** Verified read-only by the orchestrator
  against the owner's log: **6 non-comment lines carry a rate bracket and only 3 yield a `rate`
  field.** Two lines use a *parenthesised* note after the bracket (log lines 19 and 24) — so that
  shape IS in use and IS legal by the only standard available, the log's own practice — and the
  greedy `notes` group swallows their bracket, leaving `rate=''`. One of the two is
  `card-217-profiling-run`, the entry the deleted test singled out. The third loss is CARD-217's
  merge-gate line, which carries a BARE trailing note and does not parse at all.
  So: **bare trailing prose is not legal** (no entry uses it) and stays rejected; **a parenthesised
  trailing note is legal, is used twice, and the parser mis-reads it** — fixing that is this
  card's work under AC-4's own "if it is legal, the parser is fixed and the fix is tested" branch.
  A test that instead pinned `rate == ''` as correct would enshrine a 50% field loss, which is the
  "aspirational green" the review caught. A strict xfail is not an option either — the owner's
  standing rule is that an xfail standing in for a defect blocks merge.
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

- [Env] forge unknown — no executing plugin manifest and no `forge.min_version` declared.
- [Scope] tests/test_suite_profile.py
- [Scope gate] IN_SCOPE — one changed file, exactly the card's `Touches:`. No excess at all, which
  for a card scoped to a single module is the expected result rather than a lucky one.
- [Guard] G-1 verified by the orchestrator independently, not taken on report: the owner's
  `meta/kanban/suite-timing.log` is byte-for-byte untouched — md5 `fd3e799a4ea30862d8d8e03966ae9349`,
  2802 bytes, mtime Oct 15 09:50. The agent read it to settle AC-4 and never wrote, moved or
  normalised it, which is what the owner's decision required.
- [Guard] the card's central claim verified mechanically: no test reads the live log. The eleven
  surviving mentions of `suite-timing` / `TIMING_LOG` in the module are all prose (comments and
  docstrings) **or the AST guard's own positive-control strings** — lines 1076–1078 are literally
  the three couplings the guard must flag, which is why a grep-based guard would have been useless
  here and the `ast` walk is not. `LIVE_LOG_STEM = "suite-timing"` at line 1005 is the deliberate
  indirection so the guard cannot flag the sandbox helper that legitimately names a log.
- [Build gate] the three affected classes green under the lock: 44 passed.

### Implementation notes (carried from the worktree)

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

### CARD-238 implementation notes (2026-10-15)

**Shape chosen.** Option 1 of the three the card lists, with the "last entry" assertion
*restated* rather than deleted. The format contract stays exactly where it was — in
`TestSuiteTimingLog_FormatUnchanged`, against entries the test constructs — and the live
`meta/kanban/suite-timing.log` is no longer read by any test. Option 2 (move the live-log check
into a `rank_durations.py` subcommand or a `/forge:ci` step) was **not** taken: it is a new tool
surface and G-4 scopes this card to `tests/test_suite_profile.py`. The owner can still check
their log by hand with `malformed_timing_lines`, and the check now has a test-backed statement of
what it would say about the one bad line (AC-4). What replaced the live reads:

- *was* `malformed_timing_lines(live log) == []` → `test_every_shape_the_real_log_uses_is_well_formed`
  over `REAL_SHAPES`, a constructed log transcribing every shape the owner's log actually used on
  2026-10-15 (plain wave run, em dash inside the notes, `---` duration, rate bracket, rate bracket
  followed by a parenthesised second note, header/GAP/NOTE comments) — plus a seeded corpus of 160
  generated entries and 1,416 mutants of them, cross-checked against `_looks_like_an_entry`, a
  second hand-written reading of the format that does not use `TIMING_LOG_LINE`.
- *was* `entries[-1]` is a profiling run / `PASS` / has a duration →
  `test_the_last_entry_is_the_last_uncommented_one` (file order, and a commented-out entry below
  the tail does not become the tail — the `status`/`duration`/`rate` assertions move here) and
  `test_a_profiling_run_is_recognisable_by_label_or_notes` (the `"profil" in label or notes` rule,
  and that it does *not* match a merge-gate line). The claim "a profiling run happened most
  recently" is asserted nowhere now: the dispatcher appends a gate line after every card, so no
  code can keep it true. That is the deleted part, deliberately.

**AC-4 ruling: the `[135ms/test] — note` shape is NOT legal.** Justified from the other 16 entries:
every one of them keeps its commentary inside the notes parentheses, em dashes included
(`wave-32 … (6083 passed, 0 failed — first wave with a clean suite since wave 20)`), and the single
entry that wanted a note *after* the rate bracket — `wave-38 card-212-merge-gate … [159ms/test]
(a first attempt on a shared host failed at 1476s …)` — parenthesised it, and parses. So the
convention the entries share is: prose lives in parentheses; the rate bracket ends the line.
Widening the regex to swallow a bare tail would make `notes` and `rate` ambiguous for every reader
of the log, and the cost trend is read off exactly those fields. **`rank_durations.py` was therefore
not touched at all (G-3).** The shape is pinned as rejected by
`test_the_trailing_prose_shape_is_not_legal`, which names the writer in a comment: the forge:kanban
dispatcher's merge-gate "SUITE TIMING" append step (`skills/kanban/references/cmd-run.md`, which
documents `<ISO ts> wave-<N> <label> <seconds>s <PASS|FAIL>` and carries no trailing-prose form;
`tests/README.md`'s "Logging the run" shows the same). The companion
`test_the_same_note_parenthesised_is_legal_and_keeps_its_fields` shows the same sentence accepted
the log's own way, so the ruling is a correction and not a lost note. G-1 held: the log itself was
read but never written, in the main repo or anywhere else.

**Test count for `TestSuiteTimingLog_FormatUnchanged`: 22 → 29** (module 83 → 105).
−2 removed (`test_the_real_log_is_entirely_well_formed`,
`test_the_last_entry_is_this_cards_profiling_run`, both host-coupled; every assertion in them
re-homed as listed above), +9 added: `test_every_shape_the_real_log_uses_is_well_formed`,
`test_the_trailing_prose_shape_is_not_legal`,
`test_the_same_note_parenthesised_is_legal_and_keeps_its_fields`,
`test_the_last_entry_is_the_last_uncommented_one`,
`test_a_profiling_run_is_recognisable_by_label_or_notes`,
`test_the_seeded_corpus_is_large_enough_to_be_a_corpus`,
`test_every_seeded_entry_parses_and_yields_back_its_own_fields`,
`test_every_seeded_mutant_is_rejected`,
`test_the_parser_agrees_with_an_independent_validator`. Nothing in `GOOD`/`BAD` or the
commented-out-entry cases changed, so the parser's accept/reject behaviour on constructed entries
is asserted over 1,589 constructed lines, cross-checked line by line against a second
implementation, where before it was 22 cases plus whatever the host's log happened to hold (G-2). Two new classes carry the guards:
`TestSuiteTiming_NoTestReadsTheLiveLog` (12) and
`TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog` (3).

**TDD, red→green.**

- AC-1: test `TestSuiteTiming_NoTestReadsTheLiveLog` red→green. Written first and run against the
  then-current code, where the `ast` walk found both couplings:
  `AssertionError: a test reaches for the gitignored live timing log, so its verdict depends on the
  host rather than on the code: {'tests/test_suite_profile.py': ['suite-timing.log', 'suite-timing.log
  is gitignored (*.log) and absent from this checkout']}` — `1 failed, 11 passed`. Green after the
  removals. Re-verified on the *final* code by re-introducing the constant and the skipif in a
  sandbox copy: `3 failed in 0.77s` (both guard tests plus the outcome comparison).
- AC-3: test `TestSuiteTiming_CollectsTheSameWithAndWithoutTheLog` red→green, two tests, both red
  first. Structural: `AssertionError: a skipif here turns 'this test cannot run on this machine'
  into silence rather than into a failure: [('test_the_real_log_is_entirely_well_formed', 'not
  TIMING_LOG.exists()'), ('test_the_last_entry_is_this_cards_profiling_run', 'not
  TIMING_LOG.exists()')]`. Behavioural (the class run twice in a `tmp_path` sandbox, log present
  vs absent): `Differing items: {…::test_the_real_log_is_entirely_well_formed': 'PASSED'} !=
  {…: 'SKIPPED'}` and the same for `test_the_last_entry_is_this_cards_profiling_run` — i.e. the
  defect itself, reproduced inside a test. Note the collected *count* was always equal (a skipif
  collects either way), so the test compares per-test **outcomes**, which is the claim that has
  content; it also asserts ≥20 outcomes were parsed and that all of them are `PASSED`, so it
  cannot pass by comparing two empty runs.
- AC-2: the existing cases, unchanged in substance; counted above.
- AC-4: test `test_the_trailing_prose_shape_is_not_legal` (+ the parenthesised companion),
  green on the unmodified parser — which *is* the ruling.
- AC-5: two full suites below.

**AC-5 — two full suites, locked and solo, on the final tree.**

- Run A, `meta/kanban/suite-timing.log` **present** in the worktree (a 4-line scratch log this card
  wrote, including CARD-217's malformed shape, so the file was not merely present but *dirty*):
  `7252 passed, 9 skipped, 17035 warnings in 1007.06s (0:16:47)` — rc=0.
- Run B, the same file **absent**:
  `7252 passed, 9 skipped, 17035 warnings in 1195.32s (0:19:55)` — rc=0.
- Identical pass/fail/skip: 7252 / 0 / 9 both ways. The 9 skips are the host's own and are
  accounted for: 8 from an unset `DATABASE_URL` (`tests/conftest.py:171`) and 1 from the kernel
  refusing `setrlimit(RLIMIT_AS)` (`tests/test_book_pdf_memory.py:1250`). The two timing-log skips
  are gone, which is the whole point: 11-skips-green vs 9-skips-red can no longer happen.
- Both runs held `meta/kanban/.full-suite.lock` (one holder across the pair, released after),
  ran solo, and ran `caffeinate -i`. A first attempt at the pair, before the caffeinate, hit 3 and
  then 4 `Page.goto: Timeout 30000ms exceeded` failures in the browser family — different tests
  each time, all through `test_puzzle_solver_page.py:744`'s `_open`, on a host whose wall clock
  gaps (2h23m of clock for 958s of pytest) show it suspended mid-run. Its **skip counts were
  already identical at 9/9**, so the host-state defect was gone even there; the retry above is
  clean on both counts. `tests/test_suite_profile.py` failed nothing in any of the four runs.

**Guardrails.** G-1 held: `meta/kanban/suite-timing.log` in the main repo was read (to settle AC-4)
and never written, moved or normalised; AC-5's "present" run used a file this worktree created and
then deleted, and `_run_format_class` writes only under `tmp_path`. G-2: see the count above.
G-3: `meta/profiling/rank_durations.py` is **untouched** — AC-4's ruling was "not legal", so no
parser change was licensed and none was made. G-4: `tests/test_suite_profile.py` is the only file
changed (CARD-217's artefact checks are untouched). G-5: no `src/**`, no new dependency — the
corpus is `random.Random`, not `hypothesis`.

- [Review sync] 1 report(s) → meta/review/20261016T032051Z-CARD-238-cycle1.yml
- [Review 1/3] Score: 6.0 — crit: **2**, imp: 2. Below min_score AND two Criticals, so the gate is
  closed twice over. Risk MEDIUM, lane DEEP. Every gating finding is backed by an **executed
  mutant or a measured count**, not by reading, which is why none of them is arguable.
- [Review 1/3] ⚠ **CRITICAL 1 — AC-1's guard does not prove its claim, and a mutant restoring the
  ORIGINAL defect survives every one of its 15 tests.** `_live_log_references` judges by syntactic
  position only, so it misses **10 of 12** re-introduction forms. The decisive miss is not an
  evasion but a routine refactor:
    `LOG_NAME = "suite-timing.log"` then `TIMING_LOG = REPO_ROOT / "meta" / "kanban" / LOG_NAME`
  — the original coupling, invisible. Also missed: `os.path.join` with a hoisted name, string
  concatenation, `glob("*.log")`, `Path(*PARTS)`, a fixture returning the path, `%`-format, a dict
  lookup, a slice. **And `f"{STEM}.log"` — the pattern this very module uses in
  `_run_format_class`, so the file demonstrates its own bypass.**
  Proven with real mutants, not just probes: MUT-3 (hoisted filename in another class) and MUT-5
  (**the original defect verbatim** — a host-conditional skip wrapped round a live-log read, in
  another class) both SURVIVED at rc=0 with 15/15 guards green. The only defence that actually
  fires is AC-3's sandbox outcome comparison, and that is scoped to ONE class of one module. So
  AC-1's stated claim and its class docstring's "proved structurally" are both false outside that
  class. The guard is AC-1's sole mechanism, which is why a surviving mutant is Critical.
- [Review 1/3] ⚠ **CRITICAL 2 — AC-4's ruling rests on two false statements about the log, and the
  remedy it prescribes silently destroys the field it calls load-bearing.** This fired on the exact
  criterion I wrote into the review brief ("if even one entry contradicts the stated convention,
  the ruling is wrong and the parser, not the log, is at fault"):
  * the comment claims "the ONE entry that wanted a note after the rate bracket parenthesised it".
    There are **TWO** — log line 19 (`wave-38 card-212-merge-gate`) and line 24
    (`wave-39 card-217-profiling-run`), **the very entry the deleted test singled out**.
  * so the stated convention "the rate bracket terminates the line" is contradicted by two real
    entries, not confirmed by sixteen.
  * and because `TIMING_LOG_LINE`'s `notes` group is a greedy `.*`, both of those parse with
    **`rate=''`**, the bracket swallowed into notes. Measured: **6 entries carry a rate bracket,
    only 3 yield a `rate` field.**
  The ruling's load-bearing argument — that widening the regex would make `notes` and `rate`
  ambiguous, and the cost trend is read off exactly those fields — therefore **describes the status
  quo**, and the ambiguity exists *because* the author used the parenthesised form the ruling
  recommends. G-3's "no parser change licensed" does not follow from a ruling that does not
  survive contact with the data.
  Not a one-liner, per the reviewer: making `notes` non-greedy would turn lines 19 and 24
  malformed, so an optional trailing parenthesised group is the shape actually needed — a decision,
  not a patch.
- [Review 1/3] Important: the skipif detector misses **5 of 5** spellings beyond the bare
  decorator, including module-level `pytestmark = pytest.mark.skipif(...)` — pytest's own
  documented module-skip idiom, which **would silence the guard test itself**. And
  `test_the_same_note_parenthesised_is_legal_and_keeps_its_fields` asserts `entry["rate"] == ""`
  under a name claiming the opposite, pinning the field loss as correct for exactly the shape AC-4
  recommends as its remedy. Its inline comment is honest; the NAME is the aspirational-green shape.
- [Review 1/3] What survived scrutiny, so the fix stays targeted: AC-2's counts verified
  independently on both revisions (class 22→29, module 83→105, corpus 160/1416/9 confirmed by
  import), every deleted assertion accounted for, and **the cross-check is genuinely independent**
  — `_looks_like_an_entry` uses `find`/`rfind`/`split`/`strptime`, shares no structure with the
  regex, and the author discloses a real divergence between the two (strptime rejects impossible
  dates the regex accepts), which is what an honest second implementation looks like. CLAUDE.md's
  requirement is met. AC-3's behavioural half cannot pass on two empty runs and the sandbox
  provably resolves its own root (MUT-2 passed with the sandbox log present and failed without it,
  impossible if it had reached the real repo). G-1 held by the reviewer too — log md5 identical.
  The deliberate deletion of "a profiling run ran most recently" was the **right** call.
