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
**Touches:** tests/test_suite_profile.py, meta/profiling/rank_durations.py
**Review score:** 6.0 → 7.5 → 7.5 → 6.5 (cycle 4, owner-authorised beyond max)
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
- [Scope] tests/test_suite_profile.py, meta/profiling/rank_durations.py
- [Scope gate] `Touches:` AMENDED to add `meta/profiling/rank_durations.py` rather than letting the
  gate read GROWN against a stale prediction. The prediction was written when AC-4's answer was
  assumed to be "not legal"; the data split that answer, G-3 was amended to license the parser
  branch, and `Touches:` is a prediction that should move with it. Recording the amendment instead
  of silently tolerating a 50%-outside-footprint diff.
- [Fix 2] FIXED all four gating findings plus six of the seven Minors (F-005 skipped by my
  instruction, routed to the retrospective; F-010 declined under G-4 as needing a new tool surface).
- [Fix 2] **Critical 1 fixed twice over, because the two defences fail differently:**
  * the behavioural sandbox went from ONE class to the **whole module** — 132 of 132 pass inside
    it, one node id deselected (the comparison itself, which would recurse). Worth recording how
    that nearly went wrong: symlinking `tests/` wholesale silently hid `tests/helpers` and
    `tests/property`, because `rglob` does not descend into a symlinked directory, and it broke
    the frozen-render-set test. Mirroring per-file fixed it, and the module is written as a real
    **copy** because a symlink would `resolve()` back to the real repo and defeat the isolation.
  * the AST guard now **taint-tracks** module-level bindings (3 passes, so `STEM → NAME → PATHS`
    settles) over literals, f-strings, `+`, `%`, tuples, dicts, slices, starred and comprehended
    values, plus flat bans on `glob`/`rglob` and `iterdir`/`scandir`/`listdir` over a
    `meta/kanban` receiver. A tainted name is followed only when its value *looks like a path*,
    which is what stops the module's own fabricated-source corpora tainting themselves.
  * the sandbox exemption is keyed on the join's **shape** (leftmost operand is a caller-supplied
    parameter), not on the name `root` — and pinned by
    `test_the_sandbox_exemption_turns_off_when_the_root_is_a_constant`, so it cannot be borrowed
    by a future real read.
- [Fix 2] MUT-3 and MUT-5 **both KILLED**, with the pre-fix survival reproduced first to prove the
  mutants were the right ones: pre-fix `_live_log_references` returned `[]` for both path shapes
  and `_skipif_decorators` returned `[]` for MUT-5's skip, with 15/15 guards green at rc=0.
  Post-fix MUT-3 fails twice (the AST guard and the outcome comparison) and MUT-5 three times (the
  guard, the skip detector, and the comparison). **MUT-5 is the original defect verbatim**, so the
  card now demonstrably catches the thing it was written to prevent.
- [Fix 2] evasion probes, measured not claimed: AC-1 **8/21 → 21/21**, AC-3 **1/6 → 6/6**, zero
  false positives on 9 innocent controls. **Three forms remain missed and are disclosed rather
  than hidden**: a path imported from another module, one read from an environment variable, and a
  stem rebuilt at run time (`"gol.gnimit-etius"[::-1]`). The first two are outside what a
  single-module AST walk can decide; the third is deliberate evasion, not a refactor. All three
  are caught by the whole-module outcome comparison, and the docstring says so — which is the
  right shape for a bounded claim.
- [Fix 2] **Critical 2 fixed, and the regex shape is justified by measurement.** Chosen:
  lazy `notes` + an optional trailing parenthesised `extra` group. Greedy `.*` cannot be rescued
  by adding a group, and `[^)]*` would have turned real log lines 19 and 24 malformed — the
  reviewer's own warning. The property that makes it safe was measured, not assumed: over **1759
  constructed lines, 0 accept/reject differences**, so G-2's contract is not weakened by a single
  case; only field assignment changes. Rate recovery **66/84 → 84/84** bracket-bearing accepted
  lines.
  Verified independently by me on the real line-19 text: `rate='159ms/test'`,
  `notes='7053 passed, 9 skipped, 0 failed'`, the aside in `extra` — and **bare trailing prose is
  still rejected**, so the illegal shape stayed illegal while the legal one gained its fields.
  All four of AC-4's false or stale statements were corrected rather than dropped, including the
  one that caused the whole error: **REAL_SHAPES' transcription of log line 24 had silently
  dropped that line's trailing note**, which is what made "the ONE entry" look true.
- [Fix 2] declarations: 8 FIXED lines, each with a DECLARATIONS line, and they name real
  corrections — `notes`' MEANING changed (from "everything between the first `(` and the last `)`"
  to "the first parenthesised note"), so the ranker's line contract, `parse_timing_line`'s
  docstring, the class docstring's bare "proved structurally", the stale `TARGET` constant, and
  the module docstring's false "shell out exactly once" were all corrected in the same fix.
- [Fix 2] coverage up on every axis: module **105 → 132**, the live-log guard class **12 → 30**,
  the sandbox class **3 → 11**, corpus mutants **1416 → 1580** with a tenth mutation and a
  post-bracket branch (16 of 160 entries), and the seeded-field test now requires ≥10
  rated-with-an-aside entries so that branch cannot silently vanish. Nothing removed.
- [Fix 2] ⚑ self-reported, and the kind of disclosure that makes the rest credible: its first
  attempt shipped a prefilter that short-circuited the directory-listing rule (which needs no
  filename at all), it found that by probing its own widened guard, and pinned it with
  `"listing the kanban directory, naming no log at all"` as a control. It also fixed a latent bug
  in its own timeout handler (`TimeoutExpired.stdout` is `str` under `text=True`, so the original
  `.decode` would have raised).
- [Fix pre-gate] PASSED — the whole module under the lock: **132 passed**. Every test named across
  the eight FIXED lines exists and passes; none was an invented name.
- [Guard] G-1 CONFIRMED by me again after this cycle: md5 `fd3e799a4ea30862d8d8e03966ae9349`,
  2802 bytes, mtime Oct 15 09:50. The agent reports it did not even READ the log this cycle —
  every real shape came from cycle 1's transcription and the review's quotations.
- [Review sync] 2 report(s) → meta/review/20261016T073645Z-CARD-238-cycle2.yml
- [AC/EC check] AC-5's cycle-2 pair, recorded here because the reviewer correctly found it was
  written nowhere — the card still carried cycle 1's numbers against a tree since changed by
  +926/−131 and +27 tests, and AC-5's own clause says "record both runs":
  * **Run A, worktree log PRESENT** (4-line dirty scratch: header, two good entries, CARD-217's
    bare-trailing-prose line, one post-bracket parenthesised note):
    `7279 passed, 9 skipped, 17035 warnings in 873.05s`, rc=0, wall 881s — clean.
  * **Run B, same file ABSENT**: `7279 passed, 9 skipped, 17035 warnings in 947.36s`, rc=0,
    wall **1988s** — the suspension signature.
  * **Identical: 7279 / 0 failed / 9 skipped both ways.** The 9 are the host's own: 8 unset
    `DATABASE_URL` (`tests/conftest.py:171`), 1 kernel-refused `setrlimit(RLIMIT_AS)`
    (`tests/test_book_pdf_memory.py:1250`).
  * Run B's gap is disclosed, not smoothed: the agent tried to redo it, the host went to **load
    average 212–296** (Defender's `wdavdaemon_unprivileged` plus Spotlight `mds`), it added a load
    gate (wait for 1-min load < 12) and could not get a second window.
  **AC-5 judged SATISFIED on this evidence, and the reasoning is the reviewer's, not convenience:**
  AC-5 asserts only that the counts match with the log present and absent, and a suspension is the
  right *kind* of noise to discount because when it bites it bites LOUDLY, as `Page.goto: Timeout`
  failures — exactly what cycle 1's first attempt showed and what run B did not. Had it mattered,
  run B would have carried extra failures and the comparison would have come back unequal; the
  failure mode runs in the direction that breaks the assertion. Burning another ~35 minutes of a
  load-212 host to re-measure a number that cannot move would cost more than it buys.
- [Review 2/3] Score: 7.5 — crit: 0, imp: **2**. **Both cycle-1 Criticals RESOLVED**, re-derived
  at full depth by the reviewer's own mutants: MUT-3 and MUT-5 both die, and it built a harder one
  (MUT-5 dressed in two plausible refactors at once) which dies too. 13 mutants executed.
  G-2 was re-derived **analytically, not just empirically**: the reviewer built its own corpus —
  32 adversarial shapes + 1,056 exhaustive suffix-grammar combinations + 40,000 seeded fuzz lines
  = **41,088 lines, 0 accept/reject differences** — and then proved it is an identity rather than a
  measurement: `L_old == L_new` exactly, because the new form always terminates in `)` when
  `extra` is present, so the old greedy `notes` could always absorb the whole suffix. Lazy vs
  greedy changes which match is found, never whether one exists. It also measured **fan-in zero**:
  nothing in the repo reads `notes`/`rate`/`extra`, so the field-semantics change has no consumer
  to break. The parser is finished and safe.
- [Review 2/3] ⚑ **FAMILY, and I am naming it because it is now three for three: on this card, a
  guard's STATED coverage has exceeded its ACTUAL coverage every single cycle.**
  * cycle 1: AC-1's "so a future test that re-introduces the read fails" — false for 10 of 12 forms.
  * cycle 2 finding #1: the fix's own residual-miss **disclosure** ("all three are caught by the
    behavioural comparison") — **false, by executed mutant.** Three survived at 41 passed: the log
    path constant placed in `meta/profiling/rank_durations.py` and read by a test; an env-var path
    to a file that exists; a sibling module reached through the sandbox symlink. Mechanism:
    `_build_sandbox` symlinks `meta/profiling` wholesale and `tests/` per file, so such a module's
    `Path(__file__).resolve()` escapes **through** the link to the real repository — its outcome is
    then invariant between the with-log and without-log sandboxes, and both `present == absent` and
    `== {"PASSED"}` hold **vacuously**.
  * cycle 2 finding #2: the skip detector's "All six forms are now reported" — false for
    module-level `pytest.skip(..., allow_module_level=True)`, which silences the whole module
    **including both guards** (pytest reports `found no collectors` for both guard classes) and on
    a log-less host reads as `1 skipped, exit 0`. That is the fresh-worktree case that hid the
    original defect, and it is the imperative twin of the `pytestmark` idiom cycle 1 had already
    named as the worst of its five misses.
  The aggravating detail in both: **the docstring now asserts the coverage the code lacks**, so the
  file reads as having been hardened against exactly what still gets through. The first of the two
  is a plausible refactor rather than evasion — `rank_durations.py` is now in this card's
  `Touches:`, and the declined Option 2 (`--check-log`) would put the log's path constant precisely
  there. Cycle-1's defect, one indirection out.
  Per `review.family_regression`, this is **occurrence 1** of the family (cycle 1's findings had no
  prior fix to attribute to). If cycle 3's review lands in it again the streak hits 2 and the card
  escalates rather than taking a fourth cycle — and `max_cycles` is 3, so cycle 3 is the last one
  available either way.
- [Fix 3] All four gating findings fixed plus four Minors, and **the family's root cause is fixed
  structurally rather than instance by instance.** The limits are now held as CONTROLS
  (`MEASURED_STRUCTURAL_MISSES`, asserting the known misses are still misses) instead of as
  prose, with the reason written in the file: *"a sentence cannot go red when it stops being
  true, and on this card a stated coverage outran the real one three review cycles running."*
  That is the correct response to the family — a claim that can rot was replaced by a claim that
  fails when it rots.
  Verified by me: **both false sentences are gone (0 grep hits)**, and the three surviving
  "all of them" matches are legitimate — a transcribed log entry, a comment about dict/slice/
  walrus forms, and a historical note recording the old wording as corrected.
- [Fix 3] F-107 — **AC-5's cycle-3 pair, recorded here because it is outside G-4 and therefore
  mine to write.** Both runs on the frozen tree `75cd1e98e03e19045a6bc83e41de7498`, under the
  lock, solo, `caffeinate -i`, each gated on 1-minute load < 12:
  * **log PRESENT**: `7295 passed, 9 skipped, 0 failed`, rc=0, pytest 1034.64s, wall 1040s —
    **gap 5.4s**, load 3.45 at the gate.
  * **log ABSENT**: `7295 passed, 9 skipped, 0 failed`, rc=0, pytest 1096.64s, wall 1101s —
    **gap 4.4s**, load 3.94 at the gate.
  * Identical counts AND identical skip reasons (8 × unset `DATABASE_URL`, 1 × kernel-refused
    `setrlimit(RLIMIT_AS)`). **Both windows clean — no suspension disclosure needed this time**,
    unlike cycle 2's run B at 1988s wall against 947s pytest.
  Cycle 1's pair (7252/9) and cycle 2's (7279/9) stand above as the pre-fix baselines; the count
  rises with each cycle's added tests, which is the expected direction.
- [Fix 3] the four kills, each re-run against the final file and reverted from a pre-captured copy
  with md5 verified:
  * **MUT-R** (the plausible-refactor one: log path constant in `rank_durations.py`, read by a
    test) — **KILLED by BOTH halves.** Structurally because `_test_sources` became
    `_guarded_sources` over `("tests", "meta/profiling")`, so the AST walk now sees the territory
    the defect was planted in; behaviourally with a `PASSED` vs `FAILED` divergence — **and that
    divergence IS the host-with-log case**, because the with-log sandbox is such a host. The
    CARD-234-green/CARD-235-red flip is now visible instead of vacuous.
  * **D1c** (sibling module resolving the real repo through the mirror) — **KILLED**, because
    `_build_sandbox` no longer symlinks: every `*.py` is a byte copy and every directory is
    created, so no module's `Path(__file__).resolve()` escapes. Verified both tracked and
    untracked, identical verdict.
  * **the module-level `allow_module_level=True` skip** — **KILLED by both halves** where the
    probe resolves to something present, and the comparison catches a self-silencing module via
    `len(present) >= 100`. **One limit stated rather than papered over:** the verbatim mutant
    keyed on the live log, run in a log-less worktree, silences its own module before any guard
    in it is collected. That is irreducible from inside one module — the comparison is itself one
    of the silenced tests — and it is now written as a limit in both docstrings.
  * **the exemption abuse** (`_log_under(REPO_ROOT)`) — structurally **NOT** caught, behaviourally
    **KILLED**, and stated in exactly those terms with the condition attached ("only while the
    helper is in a mirrored module").
- [Fix 3] ⚑ **The discipline test, and it passed.** Probing the env-var form two ways gave a split
  verdict, and the agent reported the half that **survived**: the shape a refactor actually
  produces (default spelled out in the source) is KILLED by both halves, but
  `Path(os.environ["..."])` with nothing named in the source **SURVIVED — 149 passed, nothing
  red**. An absolute path does not vary with the sandbox root and the source holds no literal to
  resolve. It is pinned as a control and written as *"NOT killed, by either half"* with the
  measurement. **An agent finding a hole in its own fix and documenting it as a hole is precisely
  what the previous two cycles failed to do.**
  Nine residuals are listed, each pinned by a control or written as a limit, and R4 is explicitly
  labelled **"reasoned, not measured"** because measuring it would need `src/**`, which G-5
  forbids — a distinction the earlier cycles collapsed.
- [Fix 3] G-2: tests **132 → 148**; positive controls 21 → 25; negative 6 → 7; conditional-silence
  controls 5 → 9; the AC-1 walk now covers 221 sources across two trees instead of 220 across one;
  controls running inside the sandbox 1 → 2. **Nothing removed.** Verified green by me: 148 passed.
- [Fix 3] G-1 CONFIRMED again at every checkpoint: md5 `fd3e799a4ea30862d8d8e03966ae9349`, 2802
  bytes, mtime Oct 15 09:50. AC-5's "present" leg used a **fabricated** log at the *worktree*
  path, clearly labelled as agent-written, removed before run B and gone now.
  G-3 CONFIRMED: `rank_durations.py` is **byte-identical to cycle 2** — the parser was not
  reopened.
- [Fix 3] two process disclosures, both volunteered: it **killed a first attempt at the AC-5 pair**
  because it had refined a docstring 60s in, and re-ran both suites from scratch against the
  frozen file rather than report a pair taken on a mid-edit tree — the same provenance discipline
  I had to enforce by hand on CARD-237, now applied unprompted. And its first red run flagged
  **its own new fabricated source** as a live-log read, because the source was an inline call
  argument naming the log: "the module was its own first offender", fixed by binding it to a
  constant.
- [Review sync] 3 report(s) → meta/review/20261016T093542Z-CARD-238-cycle3.yml
- [Review 3/3] Score: 7.5 — crit: 0, imp: 2. **max cycles reached.** The reviewer's own
  recommendation is ESCALATE, narrowly, and it was explicit that it was not softening.
- [Review 3/3] ⚠ **F-301, the gating one: a mutant that restores THIS CARD'S OWN DEFECT survives
  the entire guard suite.** `_LISTERS = frozenset({"iterdir","scandir","listdir"})` under the
  comment "Listing that directory is the same coupling without a filename at all" — but the rule
  tests the call's **receiver**, and `os.listdir` / `os.scandir` take the directory as an
  **argument**; there is no `Path.listdib`/`Path.scandir`. So **two of three members are
  structurally unreachable** and only `.iterdir()` is controlled.
  Measured end to end as MUT-L, planted in another tracked guarded source (`tests/test_clues.py`,
  reverted, md5 restored): `os.listdir` of the kanban dir, filtered to `*.log`, `pytest.skip` when
  the host has none, then an assertion on the live log — **the original defect verbatim**. Both
  guard classes PASS, **57 passed, rc=0**.
  Why the behavioural half cannot save it: the comparison runs only `tests/test_suite_profile.py`
  plus the control, so **220 of 221 guarded sources have the structural guard as their sole
  defence** — and this form is not in `MEASURED_STRUCTURAL_MISSES`, so nothing goes red.
- [Review 3/3] F-302 (Important): `_build_sandbox` states "a write here cannot land in the real
  tree even if a future edit points a source path at it". The mkdir argument covers directories,
  not the **57 data symlinks** the same function creates four lines earlier, whose `resolve()`
  escapes. Latent — nothing writes there today — but it is a false **safety** claim on the card
  whose hardest guardrail is "do not touch the owner's file", and the "even if a future edit…"
  clause invites reliance on it.
- [Review 3/3] ⚑ **FAMILY REGRESSION — occurrence 2, so the streak is 2 and the rule fires.**
  The root-cause mechanism cycle 3 built is **real and correct**: holding limits as
  `MEASURED_STRUCTURAL_MISSES` controls is the right answer, both false sentences are gone, and
  the reviewer verified **all four controls are honest** by running `_live_log_references` on each.
  What did not happen is a fresh sweep for NEW instances — the controls pin the misses already
  known, and **five new declarations that cannot go red were written in the same pass**, one of
  them (F-301) hiding a surviving mutant. The family is therefore: *a guard on this card acquires
  a stated coverage wider than its mechanism, every single pass.* Four passes, four occurrences.
- [Review 3/3] What HOLDS, so the escalation is proportionate and not a dismissal — the reviewer
  verified every one of these independently with executed mutants:
  * **all four claimed kills are genuine.** MUT-R dies to both halves, and crucially **the with-log
    sandbox is a real "host that has the log"** (the planted node is PASSED there and FAILED
    without, and the sandbox log genuinely exists/doesn't) — cycle 2's vacuity is gone. D1c's
    mechanism confirmed: **0 symlinked `.py`, 0 symlinked directories, 0 `.py` resolving outside
    the sandbox**. The module-level skip dies to both halves where the probe resolves to something
    present, and **its stated limit reproduces byte for byte** and is genuinely irreducible from
    inside one module.
  * the exemption-abuse split is exactly as stated: structurally not caught, behaviourally killed.
  * **the env-var survivor is an acceptable stated bound, not a blocker** — reproduced at 149
    passed, documentation accurate on both halves, and the key argument is that its failure mode is
    **loud**: the lethal property of the original defect was green-by-skipping, and an unset
    variable here fails rather than skips.
  * AC-2/AC-3/AC-4/AC-5 all SATISFIED; G-1 through G-5 all HELD; Step 8h 8 rules, 3 holds, 0
    violated; suite cost proportionate at **0.35%** of the full run, with the self-reported numbers
    independently reconciled.
  * G-1 verified at start, after every mutant, and at the end: md5 `fd3e799a4ea30862d8d8e03966ae9349`.
- [Escalated] 2026-10-16T09:40:34Z — family regression, occurrence 2, plus max_cycles reached · station:
  decompose/owner (the procedure forbids auto-assigning a station on a family regression — the
  evidence cannot distinguish the causes, and one question to a human can) · route: owner chooses
  between one more bounded fix cycle, merging with F-301/F-302 recorded as bounds plus a follow-up
  card, or a clean-slate redo carrying the family as a prior-attempt constraint.
  Worktree and branch are KEPT: `../PythonProject4-card-238`, `card/238-timing-log-host-state`.
- [Unblocked] 2026-10-16T10:27:36Z — **owner decision: one more fix cycle, with a mandatory claim sweep.**
  `review.max_cycles` is 3 and this is cycle 4, so the limit is exceeded deliberately and by the
  owner, not drifted past. Their stated reasoning, recorded because it is the rationale the next
  reader needs:
  * **not merging as-is**, because this card's entire deliverable IS the guard's completeness, and
    a mutant restoring the original defect passes. Merging it would ship a guard that does not
    guard — the exact thing CARD-238 exists to stop, and barred for the same reason the owner's
    standing rule bars an xfail standing in for a defect.
  * **not a clean-slate redo**, because three cycles of verified work would be discarded — the
    parser fix (safe over 41,088 lines, an analytic identity), the byte-copy sandbox, the taint
    tracker with 25 controls, 148 tests. The approach is right; what slips is the discipline on
    NEW claims.
  * the added condition is chosen to break the family rather than patch its latest instance:
    cycle 3 fixed every known instance **and wrote five new unfalsifiable claims in the same
    pass.** A mandatory sweep of the claims written in the pass is what catches that, and is
    precisely what cycle 3 omitted.
  **Two hard conditions on this cycle:**
  1. Fix F-301 by testing the call's **arguments** as well as its receiver, AND widen
     `_conditional_silences` to all **221 guarded sources** rather than `Path(__file__)` alone —
     the reviewer verified by hand that the second change also reports MUT-L's skip half, so it
     closes the finding from both directions and removes the "220 of 221 sources have one
     defence" asymmetry. Fix F-302's false write-containment sentence with a widened pinning test.
  2. **A mandatory claim sweep, reported as a list**: every claim about what is caught, reported
     or seen that this pass writes or leaves standing must be either pinned by a control or
     deleted. Four of the five claims cycle 3 left unpinned are already named (F-303 `IfExp`,
     F-304 `iglob`, F-305 the compositional reading, F-301 `_LISTERS`); the sweep must also cover
     anything NEW. A claim that cannot go red is the family, and this is the cycle that stops
     writing them.
- [Fix 4] All five findings fixed; three deferred to a follow-up card with reasons (F-306 needs
  `.gitignore`, F-308 needs a second guard module — both forbidden by G-4). **F-307 closed as a
  side effect** of F-301's second remedy rather than separately: the 221-sources-vs-1-module
  asymmetry is gone, and the false positive the reviewer predicted did not materialise — the scan
  over all 221 sources reports four entries in three modules, all genuine.
- [Fix 4] **MUT-L KILLED, by three tests and from both directions**, planted exactly as the
  reviewer did (`os.listdir` of the kanban dir, `*.log` filter, host-state skip, live-log
  assertion, in `tests/test_clues.py`). Cycle 3: both guard classes PASS, 57 passed, rc=0. Now
  rc=1, 3 failed / 66 passed:
  * path guard (the new argument rule): `{'tests/test_clues.py': ['listdir() of meta/kanban']}`
  * silence guard (widened territory): the frozen-baseline equality fails on
    `('tests/test_clues.py', 'test_the_timing_log_is_present_and_nonempty', 'not names')`
  * behavioural, transitively: the sandbox's own copy of the AC-1 guard flags the copied module.
  Verified independently by me on the raw function: `os.listdir`, `os.scandir` and a bare
  `from os import listdir` are all now caught, the F-303 ternary is caught, and the negative
  control (`cards` subdirectory) stays correctly clean.
- [Fix 4] the three previously-killed mutants all still die (MUT-R, D1c tracked and untracked, the
  module-level skip with a present probe) — widening the silence detector to 221 sources broke
  none of them. The env-var survivor **still survives and is still documented as surviving**
  (161 passed with the variable set; loud 2-failed when unset), with this cycle's re-measurement
  added beside cycle 3's and an explicit sentence that the widening does not close it.
- [Fix 4] ⚑ **THE CLAIM SWEEP WORKED, and the proof is that it caught the family reproducing
  inside its own pass.** Three of the new unpinned claims were found by the agent's own sweep, not
  by any review, and **it aborted a running AC-5 pair to fix them rather than ship them**:
  * **`_PATH_WRAPPERS` contained `PosixPath` and `WindowsPath`** — two members nobody writes, with
    nothing exercising them, so the set declared a width no control could fail on. The agent's own
    words: *"the F-301 shape in miniature, in my own pass."* Narrowed to three members, each
    generated into a control.
  * **`rglob` had no control** either — the per-spelling test was red at `['rglob']` before it
    added one.
  * **its own replacement sentence for F-302 was false in the same way as the original**: "`root`
    is the base of all writes, so this function puts nothing in the real tree" — the inference
    fails for a write through a data link. Deleted rather than requalified.
  Eight claims were **deleted rather than pinned**, including those. Nineteen were pinned, each
  with the named control. **No `[BLOCKER]`** — every claim found a control or was deleted. Two
  patterns worth keeping: the completeness guards are parametrized **from the sets themselves**
  (so adding a member without a control fails), and `MEASURED_SILENCES_ELSEWHERE` is an
  **equality**, so it goes red both when a new silence appears and when a recorded one is fixed
  without being struck.
  One control was deliberately written **bottom-up** because in source order its claim would have
  been vacuous — the two-pass alias resolution genuinely needs two passes, and the agent measured
  that rather than asserting it.
- [Fix 4] G-2: tests **148 → 168**; positive controls 25 → 36; negatives 7 → 10; measured misses
  4 → 5; `MEASURED_SILENCES_ELSEWHERE` new (4); silence-detector territory **1 module → 221
  guarded sources**; two new set-completeness guards. Nothing removed. Module cost 16.5–19.8s,
  cut from a measured 4.6s of added scanning to 1.2s by two provably-identical refactors.
- [Fix 4] AC-5: **7315 passed, 9 skipped, 0 failed on both legs**, rc=0, wall−pytest gaps of
  **4.8s and 2.8s** — at or inside cycle 3's standard. Skip lists verified IDENTICAL by `diff` of
  the `-rs` reports, not just the counts. 7315 = cycle 3's 7295 + this cycle's 20 tests.
  Two process disclosures, both volunteered: it aborted the first pair on finding the three
  unpinned claims mid-run, and then **rejected a clean 918s leg** because its own acceptance check
  could not read that run's summary (`-q` suppresses it on this host) — fixed the harness and
  re-ran both legs from scratch rather than report a leg whose counts it had not actually seen.
- [Fix 4] G-1 CONFIRMED at start, after every mutant revert, before and after each AC-5 leg, and
  by me after: md5 `fd3e799a4ea30862d8d8e03966ae9349`, 2802 bytes, mtime Oct 15 09:50:34.
  G-3 CONFIRMED by me: `rank_durations.py` **byte-identical** to cycle 3 — widening
  `_guarded_sources` needed no parser change, as predicted. G-4/G-5 held; no new import at all.
- [Fix 4] three things the agent flagged for the reviewer rather than burying, which is the right
  instinct on this card: (1) `MEASURED_SILENCES_ELSEWHERE` now **couples this module to the rest of
  `tests/`** — a future card adding a host-state skip anywhere under the guarded trees turns this
  module red. That is intended, but it is a new standing cost and the judgement call of the cycle.
  (2) The three pre-existing silences are **recorded, not fixed** (G-4 forbids editing those
  modules), and two of them are genuinely this card's own defect one module over. (3)
  `_kanban_directories` is the one place this cycle guesses wider — measured as producing no false
  positive across all 221 real sources, with three negative controls pinning the narrowness.
- [Review sync] 4 report(s) → meta/review/20261016T121120Z-CARD-238-cycle4.yml
- [Review 4/4] Score: 6.5 — crit: **1**, imp: 1. ⚠ **THE FAMILY RECURRED A FIFTH TIME**, and the
  reviewer's diagnosis is the one that matters: **cycle 4 fixed the INSTANCE, not the GENERATOR.**
  `_LISTERS` and `_HOST_STATE_PROBE` are still hand-written enumerations **whose completeness
  nothing can test**, and `os.walk` was simply not on the list.
  Verified independently by me on the raw function: `os.walk` hoisted, `os.walk` inline and
  `Path.walk()` **all return `[]`**, while `os.listdir` is caught. `os.listdir(path=...)` is
  missed too (the Important). MUT-W, planted end to end as MUT-L's shape with `os.walk`
  substituted, **survives at 168 passed** — and its own verdict on a log-less host is
  **`1 SKIPPED`**: the original defect verbatim, green-by-skipping.
  The sting: **`os.walk` is stdlib's most-written directory enumerator, more common than
  `os.scandir` — which IS in the set and which this very cycle went out of its way to make
  reachable.** Four standing sentences are falsified and none can go red, including
  `_live_log_references`' "or a listing of that directory **at all**".
- [Review 4/4] ⚠ **And one claim reported as pinned whose control cannot fail** — precisely the
  "worse than an unlisted one" case I warned the reviewer to look for.
  `test_every_path_wrapper_is_seen_through` was written in the sweep to justify removing
  `PosixPath`/`WindowsPath`, but `_unwrapped` peels whatever is in that same set, so the generated
  source passes **by construction**. Measured: re-adding `PosixPath` → 60 passed, green. Its
  sibling guard IS genuine (`walk` added to `_LISTERS` → 1 failed at `['walk']`), which is what
  makes the contrast diagnostic.
- [Review 4/4] ⚑ **My own spec defect, and it cost the audit.** I required the claim sweep "as a
  report section" rather than as a file. So the sweep's list **exists in no file** — the card
  narrates 19 pinned / 8 deleted but the list itself is unrecorded, and the owner's condition 2
  produced **no auditable artefact**. The reviewer had to redo the sweep from scratch, which is
  how it found the Critical's four falsified sentences and the decorative guard. That worked out,
  but by luck rather than design: had the reviewer trusted the narration, occurrence five would
  have shipped.
- [Review 4/4] What is verified sound, so the decision is about one hole and not about the work:
  **every claimed kill is genuine** — MUT-L dies to exactly the three claimed tests (cycle 3's
  `57 passed, rc=0` is closed), MUT-R 3 failed, the module-level skip 2 failed, D1c pinned,
  `MEASURED_SILENCES_ELSEWHERE` verified red in **both** directions, the fifth miss's behavioural
  kill reproduces exactly ("measured not reasoned"). All five `MEASURED_STRUCTURAL_MISSES` are
  **honest** (run individually). All 36 positives caught, all 10 negatives clean. Both
  "provably identical" refactors hold (re-implemented in their pre-refactor shape → 0 differences
  over 221 sources). All three self-flagged judgement calls **accepted**, and
  `_kanban_directories` produces **zero** hits across 221 real sources — more conservative than
  claimed. AC-2/AC-4/AC-5 satisfied; G-1 through G-5 held; Step 8h 8 rules, 3 holds, 0 violated.
  Cost measured at ~1.7% of the suite, this cycle adding ~0.5%.
- [Escalated] 2026-10-16T12:16:35Z — family regression occurrence 5 · station: **owner** (the procedure forbids
  auto-assigning a station on a family regression, and this is the second time the same family has
  reached a human) · the reviewer's recommendation is BACK TO THE OWNER, and it was explicit that
  **merging with recorded bounds is the case the owner barred at cycle 3**, so choosing it now is a
  *different* decision rather than the same one; and that a clean-slate redo would be wrong because
  the approach is right and four cycles of verified mechanism would be discarded.
  Its proposed route, if the owner spends another cycle: the deliverable must **not** be "add
  `walk`" — that is occurrence six waiting — but **one test that makes the enumeration falsifiable**:
  derive the listing surface from `dir(os)` / `dir(pathlib.Path)` and force every member into the
  sets or into an explicit exclusion list with a reason.
  Worktree and branch KEPT: `../PythonProject4-card-238`, `card/238-timing-log-host-state`.
- [Unblocked] 2026-10-16T13:32:32Z — **owner decision: cycle 5, scoped to the GENERATOR only, with a stop rule.**
  **The single deliverable is to make the enumeration falsifiable** — derive the listing surface
  from `dir(os)` / `dir(pathlib.Path)` and fail if any member sits in neither the guard's sets nor
  an explicit exclusion carrying a reason. Explicitly **NOT** "add `walk`": every previous cycle
  added members to a set nothing could audit, and that is why the same family returned five times.
  This attacks the auditability itself, so the next missing spelling becomes a **red test** rather
  than a review finding.
  Two small fixes ride along because they are one token and one assertion: the keyword-argument
  omission (F-402) and the decorative wrapper guard (F-403).
  **STOP RULE, stated up front and binding: if review 5 finds another member of an unfalsifiable
  set, the card merges with that hole recorded. There is no cycle 6.** The owner set this when
  authorising the cycle, not after seeing its result.
  Also fixed at my own station this cycle: the claim sweep must be written to a FILE under
  `meta/review/`, not narrated in a report. Requiring it "as a report section" was my spec defect
  — it left the owner's cycle-4 condition with no auditable artefact and forced the reviewer to
  redo the sweep from scratch, which is the only reason occurrence five was caught.
- [Fix 5] **The generator fix works, and the proof is that the audit named the Critical before the
  agent did.** The first red run — audit written, exclusion table empty — listed
  `'walk (os/pathlib.Path)'`, `'fwalk (os)'`, `'glob0 (glob)'`, `'scandir (os)'`,
  `'iterdir (pathlib.Path)'` among 271 unclassified names. So `os.walk` was identified by the
  mechanism rather than hand-added, which was the whole condition of this cycle — **and it found
  three more nobody had thought of**: `fwalk`, `glob0`, `glob1`. Those would have been occurrences
  six, seven and eight.
  The surface is derived from `dir(os)`, `dir(os.path)`, `dir(glob)`, `dir(pathlib.Path)` and
  pathlib's `PurePath` subclasses: **307 classified entries over a 271-name live surface, 18
  reasons.** `_HOST_STATE_PROBE` became `_probe_pattern(_HOST_STATE_PROBES)` so the silence half is
  a **set the audit can police too** — the Critical's two omissions compounded, and fixing one
  would have left the other. Sets filled by the audit: `_LISTERS` 3→5, `_GLOBBERS` 3→5,
  `_PATH_WRAPPERS` 3→20, probes 9→52.
- [Fix 5] verified independently by me, not taken on report:
  * `os.walk` hoisted → `['walk() of meta/kanban']`; `Path.walk()` → caught; `os.fwalk` → caught;
    `os.listdir(path=…)` → caught; bare-imported `listdir(path=…)` → caught; the `cards`
    subdirectory negative → `[]`, still correctly clean.
  * **the audit can fail**: I deleted `walk` from `_LISTERS` and got **5 red**, including
    `test_the_listing_sets_are_exactly_the_classified_spellings` — the audit itself — plus the
    three `os.walk` controls and the behavioural comparison. Reverted, md5 back to
    `2111403410773639e6b917428ee98a72`. **That is the difference from cycles 1–4: a missing
    spelling is now a red test rather than a review finding.**
  * G-1 `fd3e799a4ea30862d8d8e03966ae9349` and G-3 `1dab65e2e0d79581ef5dd48d971968fe` both
    confirmed; the sweep file exists (12,840 bytes).
- [Fix 5] ⚑ **the audit caught the family inside the agent's own pass, a second time and at a
  deeper level.** Its first `glob0` control used the pattern `"suite-timing.log"`, so the *string*
  rule caught it even with `glob0` removed from the set — **a control that proved nothing**. It
  then wrote `test_the_control_for_each_spelling_depends_on_the_set` (every spelling needs a
  control caught **with** its member and missed **without** it), watched it go red at `glob0`, and
  changed the pattern to `"latest.log"`. That is a guard on the guards' discriminating power, and
  it is the mechanism that would have caught cycle 4's decorative wrapper test.
  Two more self-corrections are on the record rather than quietly fixed: a false "exactly two of
  its members" count it wrote in `_probe_pattern`, and a "53 cases" miscount in its own sweep
  file's first draft (the set holds 52). It also **deleted its own first-draft claim** that the
  pre-classified Linux/Windows handful is complete for those hosts, replacing it with an explicit
  non-claim — the bound being that the surface is the *running* interpreter's, so a new platform's
  unclassified name is red by design.
- [Fix 5] mutants: **MUT-W KILLED** (3 failed / 237 passed — path guard `['walk() of meta/kanban']`,
  the silence equality, and the behavioural half transitively); **MUT-KB KILLED** (3 failed — the
  keyword fix on the path side, and the *derived* pattern matching bare `listdir(` where the
  hand-written `os\.listdir` could not). All four earlier regressions still die. The env-var
  survivor **still survives and is still documented as surviving** (341 passed with the variable
  set), now with `os.getenv` classified `KIND_NEITHER` and a negative control pinning it.
- [Fix 5] AC-5: **7488 passed, 9 skipped, 0 failed on both legs**, rc=0, gaps **2.4s and 2.8s**,
  loads 6.34 and 6.03 at the gates, **skip lists verified identical by `diff` of the `-rs`
  reports**. 7488 = cycle 4's 7315 − 168 + 341, exactly as predicted.
- [Fix 5] G-2: module **168 → 341** tests; positive controls 36 → 47; wrapper controls 3 → 40;
  probe controls 0 → 104 generated; new `NOT_A_PATH_WRAPPER` corpus. Nothing removed.
  G-5: **two new stdlib imports, `glob` and `pathlib`**, which the audit needs to read the surface
  — stated plainly because cycle 4's card text wrongly claimed "no new import at all".
  Scope limit honoured: F-405 and a newly-found `except FileNotFoundError` bound were **RECORDED,
  not fixed**, and the latter is pinned by a control that goes red if the detector grows past it.
- [Fix 5] the claim sweep is **a file this time**, synced to
  `meta/review/CARD-238-cycle5-claim-sweep.md` — 34 claims across four areas, each PINNED with a
  named control, DELETED, or RECORDED, plus a counts table. My spec defect from cycle 4 is closed.
