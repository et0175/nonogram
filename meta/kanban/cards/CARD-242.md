# CARD-242: The check-log guard learns the taint step its sibling already has

**Status:** done
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/242-check-log-taint-step
**Worktree:** ../PythonProject4-card-242
**Source:** CARD-239's review cycle 2 (2026-10-17), finding F-201 — measured there, recorded as a bound by owner decision rather than fixed, so CARD-239 could land without a third cycle
**Idea:** —
**Wave:** 43
**Depends on:** CARD-239 (it owns the guard and the recorded bound this card closes)
**Touches:** tests/test_guard_integrity.py, meta/review/CARD-239-claim-sweep.md
**Review score:** 8.5 (cycle 2/3)
**Started:** 2026-10-17T05:05:12Z
**Closed:** 2026-10-17T09:25:09Z
**Actual:** 0.5d
**Merge commit:** b194e3e
**Blocked by:** —

## What to implement

CARD-239's `_check_log_invocations` guards AC-6's promise that **no test invokes the deliberate
`--check-log` reader** — the one thing allowed to read the owner's live, gitignored timing log on
purpose. The guard works on every shape but one, and the exception is measured:

```python
_CMD = "python meta/profiling/rank_durations.py --check-log PATH"   # module scope
os.system(_CMD)                                                      # <- SURVIVES the guard
```

Inline, the same call is caught. Hoisted into a module-scope constant, it is exempt — because the
rule exempts **every** module-scope `ast.Assign` unconditionally on its value, on the stated grounds
that "a module-level binding is not an invocation". That is true of prose and false of a command
line that is then executed.

**The missing piece has a working precedent in the same codebase.** The sibling rule,
`_live_log_references` in `tests/test_suite_profile.py`, answers exactly this question with its
taint step (`_tainted_names` / `_string_values`): *does the bound name reach something that
executes it?* `_check_log_invocations` reimplemented the rule's shape and dropped that half. Give
it the taint step.

**Why the obvious narrowing is not the fix, measured in CARD-239's cycle 2.** Keying the exemption
on the value (`node.value == CHECK_LOG_OPTION`) does catch the hoist and keeps all seven positive
and four negative controls green — but it produces one new hit over the real tree:
`SANDBOX_CONTROL_MODULE` at `tests/test_suite_profile.py:4804`, a module-scope constant holding a
fabricated module's source that *mentions* the option as prose. A guard that cannot tell a quoted
example from an executed command is the same defect pointing the other way. The taint step is what
distinguishes them.

## Acceptance criteria

- **AC-1** (happy, the hoist dies): *Given* a module-scope constant holding a `--check-log` command
  line that is then passed to an executor (`os.system`, `subprocess.run(..., shell=True)`,
  `subprocess.run([...])`, `main([...])`), *then* the guard reports it — demonstrated by planting
  and reverting each form. (test: `TestCheckLog_TheDeliberateReader::*`)
- **AC-2** (guard, prose stays exempt): *Given* `SANDBOX_CONTROL_MODULE` and any other module-scope
  constant that merely *mentions* the option without reaching an executor, *then* the guard stays
  silent — and this is asserted over the **real tree**, not a fixture, so the card cannot pass by
  narrowing its own corpus.
- **AC-3** (guard, the exemption carries a control that can fail): *Given* each of the rule's
  exemptions, *then* there is a control for what it must **not absorb**, caught WITH the exemption
  removed and missed WITH it in place. This is CARD-239's own promoted rule and the reason this
  card exists; an exemption with a control only for what it exempts is what produced F-201.
- **AC-4** (guard, one rule, still): *Given* the three tests of that class, *then* each still calls
  `_check_log_invocations` and none re-derives the predicate — CARD-239's RC-1 pin
  (`test_the_invocation_rule_is_the_one_the_guard_runs`) stays green and is extended to the taint
  step. The defect it prevents — a control certifying a copy of the predicate — is what cycle 1
  found, and widening the rule must not reintroduce it.
- **AC-5** (guard, the bound is struck honestly): *Given* CARD-239's recorded bound for F-201 and
  its sweep row, *then* both are struck in the same diff that closes the route, and the sweep's
  equality goes **red** if the bound is struck without the route being closed.
- **AC-6** (edge, no new residue undeclared): *Given* the widened rule, *then* whatever it still
  cannot see is recorded as a measured miss with a control, in the `MEASURED_STRUCTURAL_MISSES`
  shape the sibling module uses.

## Guardrails

- G-1: **do not write, move, rename or normalise `meta/kanban/suite-timing.log`.** Standing owner
  decision from CARD-238. Note CARD-239's near-miss: a control carrying the literal log path was
  itself reported by the *other* module's path guard. Spell control destinations generically.
- G-2: coverage up, not down. Nothing CARD-239 left may be removed.
- G-3: do not weaken the sibling rule or the first module to make this one fit. If the taint step
  needs sharing, the project's convention is to reimplement natively rather than import across —
  see CLAUDE.md and `solver/propagate.py`'s `mask_runs` precedent — and the two guard modules are
  deliberately independent.
- G-4: no `src/**` change; no new runtime dependency (ADR-0006/R1).
- G-5: do not re-measure or regenerate any `meta/profiling` artefact.

## System contract

- ADR-0038/R7 — Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra. (check: review-lens)
- ADR-0038/R8 — Browser tests run locally, against Chromium installed by `playwright install chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible in the run summary. They never pass silently. Onc… (check: review-lens)
- ADR-0039/R1 — A set a guard consults needs a completeness test written before the set, and any claim the guard makes about what it catches needs a control that can fail: caught WITH the set member present, missed WITHOUT it. A claim whose control cann… (check: `test_the_control_for_each_spelling_depends_on_the_set`)
- ADR-0039/R2 — A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never a silent pass, and the unanalysable sites b… (check: `test_the_guard_sets_are_derived_and_not_hand_written`)
- ADR-0039/R3 — An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT absorb — caught with the exemption removed, missed with it in place — is held to an equality against the sites that exist today, and records w… (check: `test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw`)
- CON-005 — The uniqueness check must never produce a false positive: a puzzle accepted as unique must never actually have 0 or more than 1 solutions. This is the mandatory correctness property the whole tool depends on. (check: `PropertyTest_Solver_NeverFalsePositiveUniqueness`)
- CON-009 — The web UI's HTTP server binds its listening socket to 127.0.0.1 (loopback) only, and refuses connections arriving on any other interface. Restates NFR-003/AC-052 as a gate-enforced mandatory constraint — a `check:` the system contract a… (check: `TestWebServer_BindsLoopbackOnlyByDefault`)
- CON-010 — The web UI's HTTP server refuses any request the browser itself marks as cross-site (a Sec-Fetch-Site value other than same-origin/none, or an Origin header naming a non-loopback host), and refuses any absolute-form request target whose… (check: `PropertyTest_WebServer_RejectsAnyCrossOriginOrForeignAuthorityRequest`)
- CON-011 — Each grid side is 10 to 30 cells inclusive. 30 replaces 50 as MAX_SIZE project-wide and applies to every source mode (random, built-in library, uploaded image) and to both inbound adapters (CLI and web UI). This supersedes the 10..50 ran… (check: `PropertyTest_GridDimensions_EverySourceModeRejectsSideOutside10To30`)
- CON-012 — A generation request whose grid aspect ratio differs from the uploaded source image's INK BOUNDING BOX ratio (ADR-0022 revision 2026-09-01, DEC-025 — not its as-decoded file ratio) by more than 2x is refused with an explanatory error rat… (check: `PropertyTest_AspectGuard_AcceptsExactlyThoseRequestsRetainingHalfOrMore`)

## Architecture context

- **FR:** — (test-integrity card; its done-ness is the ACs above)
- **Components:** — (tests only)
- **Trace:** not updated by this card.

## Worktree notes

- [Why this is a card and not CARD-239's third cycle] Owner decision, 2026-10-17. CARD-239's cycle 2
  closed two findings by mechanism and minted two more in the same family, and its reviewer's
  objection to a third cycle was that it would be "the loop asked to audit the exemptions it just
  wrote" — which is how CARD-238 reached five cycles and 2.7 days. F-202 was a one-liner whose
  control came free and was fixed there; this one needs the taint step, which is real work.
- [Read before starting] CARD-239's cycle-2 report (`meta/review/*CARD-239-cycle2.yml`) has the
  measurements: M2 (hoisted) SURVIVED at 854 passed, M3 (inline) KILLED, and the `SANDBOX_CONTROL_MODULE`
  collision that rules out the naive narrowing. None of it needs re-deriving.
- [The rule this card is an application of] **An exemption is a claim, and it needs the same control
  a set member needs — caught WITH it, missed WITHOUT it, and the residue recorded as a bound.**
  CARD-239 produced that rule by violating it twice. This card is the first work done knowing it.
- [Env] forge 2026.8.17 (no meta/.skills.yml in this project — no min_version comparison)

### Implementation notes, 2026-10-17 (branch `card/242-check-log-taint-step`)

META EDIT: meta/review/CARD-239-claim-sweep.md

**What changed.** `tests/test_guard_integrity.py` only (plus the sweep, above).
`_check_log_invocations` keeps its substring predicate and its four exemptions, and
the `definition` exemption now carries a dataflow condition: a module-scope binding
is a definition only while its bound name reaches nothing that executes it. The
question is asked by a new native taint step — `_executed_names`, with `_bound_keys`
and `_names_within` — written here rather than imported from the sibling module
(G-3, and CLAUDE.md's `mask_runs` precedent). It runs backwards from the executor,
where the sibling's runs forwards from the log's name, because the option-bearing
end was already answered by the reporting predicate. The exemptions are now a table
(`CHECK_LOG_EXEMPTIONS`), each row carrying BOTH controls, and `exemptions` /
`executors` are parameters so a control can remove exactly one member — the shape
`_module_scope_silences` already had for `silencers`/`bindings`.

**TDD, red then green, one line per criterion.**

- AC-1: test `test_the_invocation_rule_catches_every_way_of_passing_it` red→green —
  the four hoisted shapes (`os.system`, `subprocess.run(..., shell=True)`, a
  `subprocess.run([...])` argv, `main([...])`) planted as positive controls first and
  measured `[]` against the rule as CARD-239 left it (M2 reproduced at function
  level), green after the taint step. A fifth, `a hoisted command line reached
  through a second constant`, was added when mutant M-C showed the three settling
  passes had no control of their own.
- AC-2: test `test_the_prose_the_real_tree_holds_is_present_and_still_silent`
  red→green — over the real tree, not a fixture: it finds the module-scope bindings
  that mention the option (`CHECK_LOG_OPTION` here, `SANDBOX_CONTROL_MODULE` in
  `tests/test_suite_profile.py`), asserts there are at least two in at least two
  files, and asserts the rule is silent on both. Red on mutant M-B, which drops the
  exemption and reproduces the naive narrowing's collision verbatim:
  `{'tests/test_guard_integrity.py': ["CHECK_LOG_OPTION = '--check-log'"],
  'tests/test_suite_profile.py': ['SANDBOX_CONTROL_MODULE = ...']}`.
- AC-3: tests `test_every_exemption_absorbs_its_control_only_because_it_is_on` and
  `test_no_exemption_absorbs_what_it_must_not` red→green — per exemption, the
  `absorbed` control is missed WITH the exemption and caught WITHOUT it (so the row
  is load-bearing), and the `rejected` control is reported with every exemption in
  place. Four rows, eight controls; the `definition` row's `rejected` is F-201's own
  mutant.
- AC-4: test `test_the_invocation_rule_is_the_one_the_guard_runs` stays green and is
  extended red→green — `_executed_names` is called from inside the deployed rule
  (not from a test), no test in the class calls the taint helpers directly, and every
  `EXEMPT_*` key the table declares is branched on in the rule.
  `test_the_hoisted_command_is_caught_by_the_taint_step` pins *which* half catches the
  hoist: with the executor set emptied the same source is silent again.
- AC-5: test `test_the_struck_bound_and_the_closed_route_agree` red→green — the bound
  (`MEASURED_CHECK_LOG_MISSES`' first entry) is struck, and sweep rows **E-9** and
  **G-16** are struck in the same diff. The test holds three statements together: the
  rule's verdict on the hoisted line, this module's record of it, and what those two
  rows say. It was genuinely red twice on the way: once with the route closed and the
  sweep rows still open (as written), and once on mutant M-G.
- AC-6: test `test_the_disclosed_check_log_misses_are_still_misses` red→green —
  `MEASURED_CHECK_LOG_MISSES` holds **ten** entries, each asserted `== []` against
  the deployed rule (the sibling's `MEASURED_STRUCTURAL_MISSES` shape). One is
  CARD-239's `error(...)` bound (sweep row G-11); the other **nine** are this card's.
  Six came from the build pass: an **aliased** executor (G-17), a
  **getattr**-fetched one (G-18), an executor the set does **not enumerate** (G-19,
  instance `pty.spawn` since review cycle 2 made `runpy.run_path` a member), an
  executor behind a **local wrapper** (G-20), a command line **bound in one module
  and executed from another** (G-21, the price of the exemption, stated), and an
  option **assembled from pieces** (G-22, the reporting predicate's bound rather
  than the taint step's). Three more came from **review cycle 3**, which verified
  this AC and found the list complete about instances and silent about the
  mechanism: the `registration` exemption's twin of G-11 (G-25), an `except ... as`
  alias (G-26), and the return direction of G-20's bound (G-27). The four binding
  forms the same cycle measured as laundering a hoisted command line past the
  settling loop are **closed** rather than recorded, with a control each, and the
  node types the loop does and does not follow are stated once in `_bindings`
  (sweep row **G-24**) — the figure "six measured residues" this line used to carry
  was a count of a growing table, which is the defect the row records.

**Mutants — thirteen planted, eleven killed, two survived.** The heading first read
"eleven planted, eleven killed, none survived"; the two survivors below were found by
review cycle 1's adversarial verification and are the reason the settling count became a
fixpoint. One per fresh pytest
process, each file restored from a byte copy with the md5 re-verified
(`tests/test_guard_integrity.py` and `meta/review/CARD-239-claim-sweep.md` both back
to their pre-mutant hashes; `tests/test_clues.py` back to
`942627df2b6df5a003bf52775ab1d398`, the hash CARD-239's cycle 2 recorded).

| mutant | what it breaks | verdict |
| --- | --- | --- |
| M-A | the taint step disabled (CARD-239's unconditional exemption) | KILLED — the 4 hoist controls, the chain control, the `definition` rejected control, the taint-step control, the sweep equality, every executor control |
| M-B | the `definition` exemption dropped (the naive narrowing) | KILLED — the real-tree guard names `SANDBOX_CONTROL_MODULE` and `CHECK_LOG_OPTION`; the AC-2 test and the absorbed control red |
| M-C | the three settling passes removed (`range(3)`→`range(0)`) | KILLED — only the chain control, which is why that control exists |
| M-C(1) | `range(3)`→`range(1)` | **SURVIVED — 117 passed.** Found by review cycle 1's adversarial verification, not by this pass |
| M-C(2) | `range(3)`→`range(2)` | **SURVIVED — 117 passed.** Both survivors sit in the same one-character family as M-C, and the heading above them originally read "none survived" — a wrong ledger row is worse than a missing one, because the ledger is what the next reviewer trusts |
| M-D (edge) | only a bare `Name` argument taints | KILLED — the argv-list and `main([...])` controls |
| M-E | a test calls `_executed_names` directly | KILLED — the extended RC-1 pin |
| M-F (edge) | an `EXEMPT_*` key declared and never branched on | KILLED — the extended RC-1 pin |
| M-G | the struck bound recorded again while the route is closed | KILLED — the disclosed-misses test and the sweep equality |
| M-H (edge) | `main` removed from the executor set | KILLED — the `main([...])` control |
| M-S | the sweep rows reverted to open | KILLED — the sweep equality, from the other direction |
| M-T | **end to end**: the hoist planted in `tests/test_clues.py` (module-scope constant + `os.system` in a never-called function) | KILLED — `test_no_guarded_source_invokes_the_check_log_subcommand` red. This is review cycle 2's M2, which SURVIVED at 854 passed; it is now reported |
| M-B(re-run) | same, re-run against the new AC-2 test alone | KILLED — and it SURVIVES M-A, which is correct: with the taint step off, prose is still silent |

**Coverage, measured (G-2).** `tests/test_guard_integrity.py` 77 → **131** collected,
all passing (122 after review cycle 2; cycle 3 adds six positive controls and
three recorded misses, all parametrized cases of tests that already existed).
`ast` name diff **against `main`**, counting `Assign` and `AnnAssign` `Name`
targets at module scope and `FunctionDef` names: tests +8/−0, module-level helpers
**+5/−0** (cycle 3's `_bindings`), module-level constants **+16/−0**. (The figure
first written here
said "constants +7/−0" against `HEAD`, which was wrong when written — review cycle 1
measured 12 and no reading of that revision yielded 7 — and the fix pass has since
added four more. The method is stated above so the number can be re-derived rather
than re-narrated; this is the "narrated figure goes stale while the asserted one
stays true" pattern, so it was corrected by measuring.) The four negative controls are
byte-identical to CARD-239's (`NOT_A_CHECK_LOG_INVOCATION` is now *derived* from the
exemption table and compares equal to the committed tuple, checked by executing both
revisions), and CARD-239's seven positive controls are unchanged: `CHECK_LOG_INVOCATIONS`
now holds **21** — the seven, plus five from this card's build pass, three from review
cycle 2 (`runpy.run_path` and the two four-deep chains) and six from review cycle 3
(one per binding node `_bindings` walks). Re-derived by executing both revisions, which
is also how the stale "with five added" was found: it was written when the table held
twelve and cycle 2 added three without it.

**Guardrails.** G-1: nothing wrote, moved or renamed the timing log; every control's
destination is spelled `PATH`, the mutants put `os.system` inside a never-called
function so nothing executed, and the sibling module's AC-1 path guard and
host-state guard were re-run green over this file. G-2: above. G-3:
`tests/test_suite_profile.py` is untouched — `git diff` names only
`tests/test_guard_integrity.py` under `tests/`; the taint step is reimplemented, not
imported. G-4: no `src/**` change, no new import at all (`ast`, `re`, `pathlib` were
already imported). G-5: no `meta/profiling` artefact read, re-measured or
regenerated.

**Not done, and why.** The full suite was not run (owner's standing instruction;
CARD-241 is in a sibling worktree). Targeted runs only: all of
`tests/test_guard_integrity.py`, and `tests/test_suite_profile.py`'s four
tree-walking guards (`test_no_guarded_module_reaches_for_the_live_log`,
`test_the_walk_actually_sees_both_guarded_trees`,
`test_the_host_state_silences_elsewhere_are_exactly_the_measured_ones`,
`test_an_untracked_file_cannot_decide_the_verdict`) — all green.

**One figure corrected beyond the strike (SCOPE+).** The sweep's counts table
declared `FOUND FALSE 13` where its own documented grep produces **14**, at `HEAD`
as well as after this card: `E-8` carries the token about *another* row's
falsification. The header paragraph explained the 13 by `B-4` and `D-2` alone, which
is measurably incomplete, so it is corrected along with the two counts this card does
move — rows 77 → 83 and non-claim G rows 16 → 22 **at this build pass**, 88 and 27 after
review cycles 2 and 3, which the sweep's own header paragraphs and counts table track
(review cycle 2's F-022: this sentence read as the present tense of a figure that had
moved). No verdict changed.

**The commit carries `tests/` only.** The two `meta/` edits — the sweep (AC-5) and
these notes — are left in the worktree for the orchestrator to carry at merge, per the
dispatch brief. AC-5's assertion lives in the committed test file, so the sweep edit
must land in the same merge or that test is red: which is the mechanism AC-5 asked
for, pointing at itself.

### Review cycle 3 notes — AC-6 made demonstrated, 2026-10-17

META EDIT: meta/review/CARD-239-claim-sweep.md (rows E-9, G-16, G-24…G-27, counts), and
this card's AC-6 line.

**What the gate found, and it is the third instance of one shape in this card.** The
seven disclosed residues were all genuine, each re-measured `== []` against the deployed
rule. What was not demonstrated was completeness: the settling loop walked
`Assign`/`AnnAssign`/`NamedExpr` bindings and **nothing in the module, the sweep or this
card said so**, so every other way a name can acquire the command line was a route
nothing saw and nothing recorded. F-001 was an undisclosed depth bound; G-16 was a
closed list that was not closed; this was a residue list complete about the instances
someone had measured and silent about the mechanism that produces them.

**The split, and it is the gate's with one line moved.** The dispatch brief proposed
closing two routes (a parameter default, an augmented assignment) and recording one (the
`registration` twin). Measurement moved the line: enumerating the binding nodes rather
than the measured instances found **four** forms, not two, that launder a hoisted command
line past the loop — a parameter default, an augmented assignment, a `for`/`async for`
or comprehension target, and a `with ... as` name. All four are the same mechanism the
loop already is (a node holding both the name and the expression it takes its value
from), so all four are **CLOSED**. Two further routes measured in the same sweep are
**RECORDED**, because neither is that mechanism one step further: an `except ... as`
alias binds a name whose value comes from the `raise` and not from the handler, and a
local function's `return` hands a value back across a call graph the step does not
resolve in either direction (G-20 is the same bound forwards).

**Before and after, per route, against the deployed rule** (`[]` = missed). Closed:
parameter default `[]` → reported; augmented assignment `[]` → reported; `for` target
`[]` → reported; `async for` target `[]` → reported; comprehension target `[]` →
reported; `with ... as` name `[]` → reported. Recorded, measured still `[]` after the
change: the `registration` twin (G-25), the `except ... as` alias (G-26), a local
function's `return` (G-27). Each closed route's source is now an entry of
`CHECK_LOG_INVOCATIONS` and each recorded one an entry of `MEASURED_CHECK_LOG_MISSES`,
so the measurement is the corpus rather than a note in this paragraph.

**The family statement, landed in `_bindings`' docstring** — the function the settling
loop calls, so a reader of the rule reaches it: *the settling loop follows a name
backwards only through a node that holds BOTH the name it binds and the expression that
name takes its value from — `Assign`, `AnnAssign`, `AugAssign`, a walrus `NamedExpr`, a
`for`/`async for` target over its iterable, a comprehension's target over its iterable, a
`with ... as` name over its context expression, and a parameter over its default — and
every other way a name can acquire the option's value is a route it does not follow.* The
residue family is the sentence beside it: a parameter filled at the call site, a value
returned by a call, an `except ... as` alias, a name bound in another module, and an
executor or receiver reached under a name the step cannot resolve. Sweep row **G-24**
carries the same statement; the misses table's comment and the rule's own docstring point
at it rather than restating it.

**Mutants — seven planted, seven killed.** One per fresh `pytest` process, the file
restored from a byte copy and the md5 re-verified (`8e4cf29b5b09692054842d121628393d`
after every restore). **M-N6** `AugAssign` dropped → 1 red, its own control. **M-N7**
parameter defaults dropped → 1 red, its own control. **M-N8** `For`/`AsyncFor`/
`comprehension` dropped → 3 red, exactly those three controls. **M-N9** `withitem`
dropped → 1 red, its own control. **M-N10** `_bound_keys`' `ast.arg` keying removed → 1
red, the parameter-default control. **M-N11** the `registration` exemption disabled → 4
red, including `test_the_disclosed_check_log_misses_are_still_misses[an add_argument()
whose own method executes what it is given]`, which is what makes G-25 a measured record
rather than an assertion of blindness. **M-N12** an `Assign`-only copy of the enumeration
inlined back into the step → 7 red, including the RC-1 pin. M-N12 is also why that pin
reads the enumeration as a **call**: with `"_bindings" in ast.unparse(step)` the mutant
survived the pin, because the step's docstring names the function.

**The real tree, re-run.** Closing four binding forms widens what the taint step sees
over all **223** guarded sources, so both halves were re-measured by executing the old
and new rule side by side on every one of them: **348** more names are tainted, across 8
files, and the number of reported sources is **0 → 0** — no new report, so no finding and
no false positive to adjudicate. The reason is measurable rather than hopeful: a wider
taint set only matters where a module-scope `Assign` holds a constant containing the
option, the tree holds exactly two such bindings (`MODULE_SCOPE_OPTION_BINDINGS`,
asserted as an equality), and neither `CHECK_LOG_OPTION` nor `SANDBOX_CONTROL_MODULE` is
in the new taint set — `test_the_prose_the_real_tree_holds_is_present_and_still_silent`
is the committed form of that.

**Counts re-derived, not re-narrated.** `tests/test_guard_integrity.py` 122 → **131**
collected, all passing. `CHECK_LOG_INVOCATIONS` 15 → **21**, `MEASURED_CHECK_LOG_MISSES`
7 → **10**, module-level helpers against `main` +4 → **+5** (`_bindings`). Sweep rows 84
→ **88**, non-claim G rows 23 → **27**, both re-counted with the greps the sweep's own
header documents (one of which still said `# 83` from the cycle before and now says 88).
The card's AC-6 line said "six measured residues" where the table held seven; it now
names the ten entries by sweep row and says which cycle measured each, because a total in
prose is the one claim in that line nothing can keep true.

**Scope.** `tests/test_guard_integrity.py`, the sweep and this card only. No `src/**`, no
edit to `tests/test_suite_profile.py` (G-3), no new import or dependency — `ast` was
already imported and `_bindings` is stdlib `ast` node types. `tests/test_clues.py`
untouched; the owner's `meta/kanban/suite-timing.log` is absent from this worktree and the
main repository's copy stands at md5 `ecfaa35af40c07943ecb01a48d62e6eb`, unchanged
(G-1). Targeted runs only, per the dispatch brief: all of `tests/test_guard_integrity.py`
and `tests/test_suite_profile.py`'s four tree-walking guards. Nothing committed.
- [Scope] tests/test_guard_integrity.py
- [Review sync] pulled agent notes from the worktree copy (119 lines)
- [System contract] section stale — refreshed from the model before review: +ADR-0038/R7, ADR-0038/R8, ADR-0039/R1, ADR-0039/R2, ADR-0039/R3, CON-005, CON-009, CON-010, CON-011, CON-012 / −ADR-0006/R1 (the lens does not scope the dependency baseline to tests/**; it stays covered by G-4). ADR-0039 landed in `7b07a93` AFTER this card was cut, and its R3 is this card's AC-3 as a standing rule — the card could not have carried it.
- [Build gate] PASSED (full, 879s; 7767 passed, 9 skipped, 0 failed, exit 0). Not vacuous: 7776 tests executed. Ran under `meta/kanban/.full-suite.lock`, released immediately after. Reference: CARD-239's merge gate was 7727 — the +49 is this card's `tests/test_guard_integrity.py` growth (77 → 117 collected) plus 9 pre-existing skips counted separately.
- [Scope gate] IN_SCOPE — actual files `tests/test_guard_integrity.py` (committed) + `meta/review/CARD-239-claim-sweep.md` (uncommitted, AC-5's META EDIT); both inside `Touches`. No hit under `src/**`, `meta/profiling/**` or `suite-timing.log` (G-1/G-4/G-5 structurally clean); `tests/test_suite_profile.py` untouched (G-3). No intersection with CARD-241's footprint — no sibling poaching.
- [Review 1/3] Score: 7.0 — crit: 0, imp: 2 (F-001 settling passes / F-002 executor-set polarity), minor: 2. Risk MEDIUM, lane DEEP. Report: `meta/review/20261017T055554Z-CARD-242-cycle1.yml` (passes `yaml.safe_load`).
- [Review sync] 1 report → meta/review/
- [Severity gate 1/3] Score 7.0 below min_score 8 AND 2 important findings — fix mandatory, success path closed.
- [Review 1/3] Step 8h coverage: 10/10 card rules carry a verdict line (0 ✓ holds, 7 ⚠ unchecked no_eligible_fact, 3 ✗ violated: ADR-0039/R1, R2, R3). All three ADR-0039 check refs were run green — the violations are about this card's new mechanism, not about those tests.
- [Adversarial] F-002 **dropped as a gating finding** (severity refuted; the mechanism fact stands, the prescription does not). Re-derived independently, by measurement, not by argument:
  - **Both prescribed remedies are measured-negative.** The `dir()`-derived projection (383 names over os/subprocess/runpy) **loses AC-1**: `main` is in the `dir()` of no plausible module (os, subprocess, runpy, shutil, multiprocessing, asyncio, sys, builtins all checked), and removing that member reds AC-1's control — the card's own recorded mutant M-H. Deny-by-default is worse: with the two name-keyed exemptions the finding prescribes, a `--check-log` command line hoisted into a constant *called* `CHECK_LOG_OPTION` or `SANDBOX_CONTROL_MODULE` and handed to `os.system` goes from CAUGHT (shipped) to **missed** — i.e. the fix for ADR-0039/R2 would commit the ADR-0039/R3 defect, re-opening the exact route this card exists to close. It also turns an execution guard into a use guard, which is the R1 family.
  - **R2's first clause is a conditional whose condition fails.** "Derived from an authority the runtime can enumerate" needs a namespace that can *produce* the set; no namespace is authoritative on "what executes a command line" (which is why `main` cannot appear in one). The finding charges both limbs of a disjunction at once — that an authority exists AND that the deny clause is unmet — and then prescribes the deny limb, which concedes the first.
  - **The residue is already disclosed, and the finding undercounted it**: 7 entries in `MEASURED_CHECK_LOG_MISSES` (G-11 + G-17..G-22), each asserted `== []`, each cross-held to the claim sweep by `test_the_struck_bound_and_the_closed_route_agree`. A named, controlled, asserted bound is the R3 residue disclosure, not a silent hole.
  - **The docstring claim (part d) does not hold**: `tests/test_guard_integrity.py:318-327` already rejects the bare projection AND names the classified-projection route by its in-repo name (`PYTEST_SURFACE`'s shape), with the size reason — 383 names against 88. The objection was anticipated on the record.
  - **Retained, not discarded:** (i) the mechanism fact is true and conceded — an executor the set does not hold is a silent pass, and this IS a verdict-deciding set, so R2 is the right subject matter; (ii) one strictly-better one-line variant was constructed and verified — `SHIPPED + runpy.run_path` closes G-19 and keeps AC-1 intact, and the sweep's own G-19 row already says "closing it is one line plus a reason, and the control comes free"; (iii) the repo-wide guard audit (re-pointing R1–R3's check refs, which today pin only `test_suite_profile.py`'s projected sets) is ADR-0039's own deferred item and belongs on a card, not in this cycle. Scope-growth refutation explicitly did NOT hold: the set is new code in this diff and R2 is `severity: mandatory`, `Migration: on-touch`, so raising it here was legitimate.
  - Worktree verified byte-identical afterwards (`git diff --stat -- tests/` empty); all probing done on `exec`-loaded in-memory copies.
- [Adversarial] F-001 **CONFIRMED** — every measurable part reproduced independently, and one fact was added that the review had not found.
  - (a) Whole-file runs per variant, one-line diff at `tests/test_guard_integrity.py:444`: `range(3)` 117 passed · **`range(1)` 117 passed** · **`range(2)` 117 passed** · `range(4)` 117 passed · `range(0)` rc=1 with exactly ONE failure (`…[a hoisted command line reached through a second constant]`, a depth-1 control). Widened to both guard modules in one process under `range(1)`: 515 tests, rc=0, byte-identical dot pattern. Nothing anywhere distinguishes 1 pass from 3.
  - **NEW (not in the review): the docstring's own justifying example needs one pass, not three.** Lines 421-428 justify the literal with "Three passes, so a chain settles backwards from the executor: `CMD = …`, `ARGV = ["sh","-c",CMD]`, `subprocess.run(ARGV)`". Measured at every pass count, that exact corpus entry is reported at N=1, 2 and 3 and silent only at N=0. The stated rationale for `3` is not what the mechanism does.
  - (b) Depth sweep against the DEPLOYED rule, forward-declared: depths **1-3 reported, 4+ missed** (the review said "1-4", off by one; its concrete five-binding `C0..C4` example is the depth-4 case and does return `[]`, so the example was right and only the label wrong). Disclosure verified absent in all three records: `MEASURED_CHECK_LOG_MISSES` holds exactly 7 entries, none about depth or pass count; sweep G-17..G-22 are one-for-one the same six; and struck row G-16 says "the bounds CARD-242 leaves in its place are G-17 to G-22 below" — an enumeration complete on its face that omits this route.
  - (c) The asymmetry is an exact staircase: forward-declared costs one pass per link (N=1 catches depth 1, N=3 catches depth 3, N=6 catches depth 6); reverse-declared settles in ONE pass at any depth 1-6. Cause visible in the code — the inner loop walks `ast.walk(tree)` in source order, so a binding already visited in a pass is not revisited after `executed` grows. The bound bites the **idiomatic** declaration order while the adversarial order is unbounded.
  - Strongest available refutation checked and UNAVAILABLE: `range(3)` is not a declared limit. The docstring makes a sufficiency statement ("chains settle"), names an example, and says nothing about what does not settle; the corpus comment documents only the `range(0)` control; the word "fixpoint" is wrong for a bounded loop. By this module's own genre — which records contrived-but-open routes (`getattr`, `globals()[...]`, aliasing) as named bounds with controls — this bound is simply missing.
  - **Severity: Important, on discipline rather than exposure** — and the exposure is honestly nil: a depth-4 chain is not something anyone writes by accident, and as an evasion it is strictly dominated by three cheaper routes (alias, `getattr`, local wrapper) that are already recorded bounds. It clears the bar for three other reasons: ADR-0039/R1 is `severity: mandatory` over `tests/**` and is violated as written; **the card's own mutant ledger asserts the opposite** ("eleven planted, eleven killed, none survived" with M-C presented as *the* control for the three passes) while two survivors sit in the same one-character family — a wrong ledger entry is worse than a missing one, because the ledger is what the next reviewer trusts; and R3's residue list presents itself as this exemption's complete residue and is not.
  - Worktree verified byte-identical (`tests/test_guard_integrity.py` md5 `5f9f5a6d2a6e9999114c7ec8be3eea3a`); all mutation work in a scratchpad copy that reproduced the baseline 117 exactly.
- [Severity gate 1/3] After adversarial verification: **1 CONFIRMED gating finding** (F-001). F-002 dropped to Minor + follow-up. Fix cycle 1 proceeds on F-001 + the retained F-002 one-liner + F-003/F-004.
- [Fix 1] ⚠ **INTERRUPTED** — the fix agent was terminated mid-pass by an account rate limit (weekly cap, HTTP 429), not by a defect. It had finished `tests/test_guard_integrity.py` (+220/−35 uncommitted) and all of `meta/review/CARD-239-claim-sweep.md`, and died turning to the card's own notes. No FIXED-line / DECLARATIONS contract was emitted, so the fix pre-gate had nothing to run; recorded here rather than treated as a non-compliant fix.
- [Fix 1] **F-001 fix verified independently by the orchestrator, by measurement rather than by report.** The settling loop now runs to a fixpoint and the literal is gone, with `passes` retained as a *control knob* (not the rule's) so a test can pin the old bounded behaviour against the new mechanism. Depth sweep of a forward-declared chain against the deployed rule: fixpoint catches depths **1–7**; `passes=3` catches 1–3 and misses **4–7** — reproducing exactly the defect F-001 named. That is the "caught WITH / missed WITHOUT" shape ADR-0039/R1 demands, and it is what the number never had. New control: `test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count`. File: 117 → **122 tests, all passing**.
- [Fix 1] F-002's retained one-liner landed (`run_path` is now an executor-set member) and the sweep's bookkeeping followed it honestly: G-19's recorded instance moved to `pty.spawn`, G-23 was added for the pass-count measurement, and **G-16's "the bounds CARD-242 leaves in its place are G-17 to G-22" was rewritten as a pointer to the table and explicitly "not a closed list"** — the closed-list sentence F-001 relied on is gone. The fix pass also found that "the last five" in row E-9 was off by one against its own enumeration, and corrected it.
- [Fix 1] **Bookkeeping completed by the orchestrator** (the dead agent's remaining task, done by measuring rather than by rewording): the mutant-ledger heading "eleven planted, eleven killed, none survived" is now "thirteen planted, eleven killed, two survived", with M-C(1) `range(3)→range(1)` and M-C(2) `range(3)→range(2)` entered as **SURVIVED at 117 passed** and attributed to review cycle 1's adversarial pass. F-004's figure was re-measured against `main` rather than copied from the review: constants **+16/−0** (not the narrated +7, and not the review's +12 — the fix pass added four more), tests +8/−0, helpers +4/−0, nothing removed, so G-2's substance holds. The counting method is now stated in the card so the figure can be re-derived instead of re-narrated.
- [Build gate] PASSED post-fix (full, 1659s; **7772 passed**, 9 skipped, 0 failed, 0 errors, exit 0). 7727 base + 45 (the file went 77 → 122 collected). The 1659s against the pre-fix 879s is concurrency, not regression — CARD-241's fix cycle was running its own targeted suites on the same machine.
- [Scope gate 2/3] IN_SCOPE — `tests/test_guard_integrity.py` + `meta/review/CARD-239-claim-sweep.md`, both inside `Touches`; no hit under `src/**`, `meta/profiling/**` or `suite-timing.log`.
- [Review 2/3] Entering **confirmation mode** (differential re-review): cycle > 1, cycle 1 parsed cleanly, the only changes since the reviewed state are the fix for its named findings, scope IN_SCOPE, and cycle 1 raised no gating finding beyond the two the fix addresses. Fix delta vs `3668c70`: `tests/test_guard_integrity.py` (+220/−35), `meta/review/CARD-239-claim-sweep.md` (+56/−10).
- [Review 2/3] Score: **8.5** ✓ threshold reached + no critical/important (0 crit, 0 imp, 3 minor, 2 out-of-scope). Confirmation mode, risk LOW, lane FAST. Improvement +1.5 ≥ min_improvement 0.5. Report: `meta/review/20261017T083321Z-CARD-242-cycle2.yml` (passes `yaml.safe_load`).
- [Review sync] 1 report → meta/review/
- [Review 2/3] Step 8h coverage: 10/10 rules carry a verdict line, **and nothing was carried** (`carried_verdicts: []`) — the reviewer failed the carry rule closed where it could not resolve scope: ADR-0038/R7+R8 declare `scope: {code: ["tests/**"]}` which the delta intersects, and the five CONs carry no `scope:` key at all, so all seven were re-verified fresh rather than inherited. 2 ✓ holds (ADR-0039/R1, R3), 7 ⚠ unchecked `no_eligible_fact`, 1 ✗ violated (ADR-0039/R2, non-gating and routed to a follow-up).
- [Review 2/3] Step 8f mutation check **RUN** (not deferred — this was the candidate passing cycle): 10 targeted mutants, 9 killed, 0 survived, 1 inconclusive (a disabled growth check hangs rather than failing, recorded as an observation with a suggested `walked <= len(names)` ceiling).
- [8h spot-check] **2/2 sampled holds reproduced** — re-derived by the orchestrator with real mutation runs rather than by a skeptic subagent (same recorded deviation as cycle 1: an account rate limit had already destroyed two agents' in-flight work, and a test run is stronger evidence here than a reading).
  - **ADR-0039/R1 reproduced, decisively.** Mutating *only* the rule's own `passes` default (line 504, not the control helper's at 409) back to a bounded 1, 2 or 3 now reds **exactly two tests** at every value: `…catches_every_way_of_passing_it[a four-deep chain declared forwards, the idiomatic order]` and `test_the_settling_loop_runs_to_a_fixpoint_and_not_to_a_count`. Cycle 1's identical mutants left **117 passed**. The claim now has a control that fails, which is the whole of R1.
  - **ADR-0039/R3 reproduced.** Cycle 1's F-003 `>= 2` is now a real equality (`bindings == sorted(MODULE_SCOPE_OPTION_BINDINGS)`, :2207). Planting a third module-scope binding that mentions the option into a guarded file (`tests/test_clues.py`) reds exactly one test — the real-tree exemption guard — so a newly absorbed site cannot appear unnoticed.
  - ⚠ **Method note against my own first attempt, recorded because it is this board's own failure class.** My first spot-check run reported "7 failures at every N including 3" and was wrong twice: the `sed` matched the `passes` default in *two* places (the rule's and the control helper's, so the controls themselves broke), and counting progress characters inflates once `FAILED` lines print file paths. I had also skipped the shadow copy's own baseline, which is the control that would have caught both immediately — it measures 122 passed, 0 failed, i.e. faithful. Re-run precisely, the result above is unambiguous. A harness whose verdict depends on something other than the code it judges is exactly what wave 40 spent three cards on.
- [AC/EC check] **Failed: AC-6 ⚠ partial** (fail-closed). 5 of 6 ACs and 5 of 5 guardrails demonstrated with fresh evidence; the card has no `## Engineering constraints` section, so none was invented.
  - AC-1 ✓ all four hoisted-executor forms green as distinct parametrizations · AC-2 ✓ real-tree **equality** over exactly two bindings, rule silent on both · AC-3 ✓ **and non-vacuity independently measured**: a 4×4 matrix removing one exemption key at a time shows every `absorbed` control flips only when its OWN key is removed and never when another is — specific, not merely load-bearing · AC-4 ✓ the deployed rule is the one the controls run, `rederivers == []`, `borrowers == []`, every `EXEMPT_*` key branched on · AC-5 ✓ **red in both directions by mutation** (route re-opened with the bound struck → red; route closed with the sweep rows reverted to `main` → red, naming `['E-9','G-16']`).
  - G-1 ✓ **behaviourally, not just structurally**: the owner's live log in the main repo is byte-unchanged — md5 `ecfaa35af40c07943ecb01a48d62e6eb`, mtime `2026-10-17T04:25:43`, which *predates* both the worktree checkout (08:05:17) and the branch's only commit (08:28:36), so nothing in this card's window wrote it; the worktree holds no `suite-timing.log` at all; every control destination is spelled `PATH`, so CARD-239's near-miss is avoided; and the *other* module's four path guards were re-run over this file as independent confirmation (4 passed). G-2 ✓ re-derived and **agrees with my own figures exactly** (constants +16/−0, helpers +4/−0, tests +8/−0, nothing removed). G-3 ✓ `test_suite_profile.py` untouched and the import list **byte-identical to `main`** — the taint step is native, with the sibling's helpers named only in three docstring citations. G-4 ✓ no `src/**`, no `pyproject.toml`, no import added or removed. G-5 ✓ no `meta/profiling` artefact touched.
- [AC/EC check] **AC-6's completeness claim is false, measured — and this is the THIRD instance of one shape in this single card.** The shape: *a disclosed-residue list that presents itself as complete and is not.* First F-001 (the `range(3)` depth bound, undisclosed); then sweep row G-16 ("the bounds CARD-242 leaves in its place are G-17 to G-22", a closed list); now AC-6 itself. The seven disclosed entries are all real (each re-measured `== []` against the **deployed** rule, not a fixture), but three further blind routes are recorded nowhere:
  1. **`registration`'s twin** — a class whose `add_argument` method itself executes (`class R2: def add_argument(self, c): os.system(c)`, then `r.add_argument("… --check-log PATH")`) → `[]`. The disclosed entry covers only `error()` on an `add_argument`-naming receiver; this needs *strictly less* to trigger (no `error` method, one call).
  2. **A function parameter default** — `CMD = "…--check-log PATH"` then `def f(c=CMD): os.system(c)` → `[]`. `_executed_names` returns `{'c'}`, but the settling loop walks only `Assign`/`AnnAssign`/`NamedExpr`.
  3. **An augmented assignment** — `ARGV = ""`; `ARGV += CMD`; `os.system(ARGV)` → `[]`; `AugAssign` is unwalked.
  Sanity controls in the same probe behaved correctly (class-scope constant, module-scope `AnnAssign`, for-loop target and comprehension target are all reported), so the family is specific: **the settling loop follows only `Assign`/`AnnAssign`/`NamedExpr` bindings.** Also narration: AC-6's text says "six measured residues" where the table holds seven (the code comment states the 1+6 split correctly).
- [Fix 1 → AC-6] **The fix went past its brief in the right direction, and the difference matters.** The brief proposed closing 2 known routes and recording 1. The agent stopped measuring the routes anyone had thought of and **enumerated the binding nodes instead** — which surfaced two more laundering routes nobody had named: a `for`/`async for`/comprehension target over its iterable, and a `with … as` name over its context expression. Closed **6 node types** (`AugAssign`, parameter defaults via `ast.arg`, `For`, `AsyncFor`, `comprehension`, `withitem`), each with its own positive control. Recorded **3** more as bounds instead of closing, with a stated reason per route: an `except … as` alias (the value comes from the `raise`, so it is not in the node at all), a local function's `return` (crosses a call graph the step resolves in neither direction — G-20 is the identical bound forwards), and the `registration` twin (keyed on a method *name*, needing the receiver resolution G-17/G-18 also wait on).
- [Fix 1 → AC-6] **It caught a vacuous control of its own before landing it.** Mutant M-N12 inlines an `Assign`-only copy of the enumeration back into the step; with the pin written as `"_bindings" in ast.unparse(step)` the mutant **SURVIVED**, because the step's own docstring names the function. Measured, then the pin was changed to read the enumeration as a *call* — after which M-N12 reds 7 tests including the RC-1 pin. A control that passes but cannot fail is this card's whole subject, and it was caught inside the pass rather than by the next gate.
- [Fix 1 → AC-6] Real-tree re-run, which closing routes made mandatory: 223 guarded sources, old and new rule side by side — **348 more names tainted across 8 files, reported sources 0 → 0.** The reason is structural rather than luck: a wider taint set only matters where a module-scope `Assign` holds a constant containing the option, the tree holds exactly two such bindings (asserted as an equality), and neither is tainted. So nothing reddens honest code.
- [AC/EC check] **AC-6 ✓ demonstrated — re-verified by the orchestrator, by measurement.** Both halves:
  - All **10** entries of `MEASURED_CHECK_LOG_MISSES` return `== []` against the **deployed** rule (defaults, not a fixture) — enumerated and checked one by one.
  - Every closed route has a control that CAN FAIL, each red named for the route it guards: dropping `AugAssign` reds its own control; dropping `withitem` reds its control plus the repo-wide guard; dropping `For`/`AsyncFor`/`comprehension` reds 4 including those three controls; dropping the `ast.arg` keying reds the parameter-default control. Shadow baseline 0 failures first — **and that control earned its place again**: my first shadow run showed 1 failure, which was `TestTheInterpreterFloor::test_the_floor_is_declared_in_pyproject_and_followed_by_the_guidance` failing only because I had not copied `CLAUDE.md` into the shadow. My harness, not the code; fixed and re-baselined before any mutant was trusted.
  - The family sentence landed in `_bindings`' docstring (the function the loop calls) and is carried by sweep row **G-24**, with the misses-table comment and `_executed_names` pointing at it rather than restating it — so there is one statement of reach, not three drifting copies.
- [Fix 1 → AC-6] Narration corrected by counting, each grepped after: the card's AC-6 line now names the **ten** entries by sweep row with the cycle that measured each and **no total a growing table can falsify**; coverage 122 → **131** collected; helpers +4 → **+5**; `CHECK_LOG_INVOCATIONS` "seven with five added" → **21** decomposed by cycle (already stale from cycle 2); sweep rows 84 → **88**, G rows 23 → **27**, and the reproducible-grep block's `# 83` → `# 88` — which closes cycle 2's F-021 and F-022 incidentally (both written back as `status: fixed`). F-023/F-024/F-025 left `open` deliberately.
- [Build gate] PASSED post-AC-6-fix (full, 928s; **7781 passed**, 9 skipped, 0 failed, 0 errors, exit 0). Arithmetic exact: 7727 base + 54 (the file went 77 → 131 collected).
- [AC/EC check] **Re-verified post-fix by the orchestrator for the two items the AC-6 fix could have invalidated** (the other nine were demonstrated before it, and the fix touched only the binding enumeration and prose):
  - **AC-5 ✓ still red in BOTH directions, now against the changed sweep** (rows 84 → 88, G rows 23 → 27, so the earlier evidence could not simply be inherited). Direction (i) — sweep reverted to `main` with the route left closed: reds exactly `test_the_struck_bound_and_the_closed_route_agree`. Direction (ii) — taint step disabled with the bound left struck: reds **38** tests including that same equality, all 19 executor controls, all 14 hoisted-form controls (the four new binding routes among them) and both `test_no_exemption_absorbs_what_it_must_not` rows. Clean shadow baseline 0 before each, re-baselined after every restore.
  - **AC-3's non-vacuity ✓ corroborated incidentally** — the `registration` and `definition` rows' `rejected` controls both appear in that 38, so the exemption table is still load-bearing after the widening.
  - ⚠ Method note, again on myself: my first direction-(ii) mutant injected `return []` into a function that returns a set, which tests a type error rather than a disabled taint step. Caught by re-baselining, replaced with the real mutant (`executed = frozenset()` at the call site). Recorded because this is the third time today the shadow/baseline discipline has caught my own measurement rather than the code's.
- [Docs] SKIPPED deliberately, with the reason on the record: the card changed `tests/` only, and `tests/README.md` is ~20 waves stale (still titled "Admin Panel Test Suite - Wave 1" and naming no book test file). Rewriting it is **an open owner decision in `meta/kanban/backlog.md`** — "either make 'no per-directory READMEs' the convention and drop the step, or create them once and rewrite `tests/README.md`" — and this card is not the place to settle it unilaterally. No per-directory README exists anywhere under `src/`, so the convention question is real and board-wide.
- [Merged] `b194e3e` (merge commit) over impl `3668c70` + fix `27ca26e`. Merge gate: full suite **7781 passed, 9 skipped, 0 failed, exit 0** — and no re-run was needed after rebase because `main` never moved from `b894e00` during the card, so the gate state and the merged state are the same tree.
- [Merged] META EDITs carried into the main repo by hand, as the brief promised, because `/commit` excludes `meta/`: `meta/review/CARD-239-claim-sweep.md` (AC-5's struck rows E-9/G-16, the six→ten bound rows G-17..G-27, the corrected counts and the `# 88` grep) and both review reports. **This is load-bearing, not bookkeeping**: AC-5's assertion lives in the committed test file and reads those sweep rows, so had the sweep not landed in the same merge, `test_the_struck_bound_and_the_closed_route_agree` would be red on `main`. The card's own mechanism polices its own paperwork.
