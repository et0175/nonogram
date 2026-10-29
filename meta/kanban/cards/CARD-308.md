# CARD-308: The card sync protocol erodes dead-ref detection — a review report that quotes a dead ref silences the warning about it, and the board has no record of which binary is the validator

**Status:** in progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/308-the-sync-erodes-dead-ref-detection
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-308
**Source:** Caught in the act 2026-10-29 while gating CARD-301; the validator-of-record half reversed the same day after CARD-284's fix round 2. Both measured by the orchestrator. Cut on owner decision.
**Idea:** —
**Wave:** 66
**Created wave:** 65
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/kanban/config.yml, meta/kanban/README.md, tests/** (one guard), meta/architecture/decisions/adr/**
**Review score:** —
**Started:** 2026-10-29
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists — two findings with one root: nothing on this board records what the instrument is

### 1. The sync protocol systematically retires the warnings it should preserve

The CARD SYNC PROTOCOL copies `meta/review/*.yml` one-way from a card's worktree
into the main repo, because `/commit` excludes `meta/` from card branches and the
reports would otherwise not exist for `forge:fix` and `forge:retrospective` to
read. It is **mandatory pipeline bookkeeping**, not an unusual act.

`symbol_exists()` is `git grep -lw <ref> -- . ':(exclude)meta/architecture'
':(exclude)*.md'`. **`meta/review/` is not excluded.** So a review report that
merely *discusses* a dead check ref puts that ref's exact string into tracked,
non-Markdown code — and the dead-ref warning about it disappears.

**Measured, same tree, same door, two commits:**

| | `git grep -lw <the ref>` | validator |
|---|---|---|
| `c2a45cf6`, before the sync | **exit 1** — resolves nowhere | 0 errors, **108** warnings |
| `c8935c51`, after the sync | **exit 0** — `meta/review/20261029T025000Z-CARD-301-cycle1.yml` | 0 errors, **107** warnings |

The ref was NFR-001/AC-038's `TestGenerate_50x50_RespectsTimeoutBound`. **The test
still does not exist.** The only commits in that range touching `meta/review/` are
two cycle-1 reports copied in by the protocol.

**The general consequence: a falling warning count is not evidence of repair, and
may be evidence of signal loss.** ADR-0006/R1 is the limit case — its ref
`TestDependencyBaseline_IsExactlyPillowAndNumpy` has **zero definitions anywhere**
and has read as mechanically checked for months on the strength of ~107 review
YAMLs spanning CARD-030→CARD-251, each cycle re-feeding the resolver. And the rule
it fails to check is the one `CLAUDE.md` singles out as needing the decision
revisited rather than just an edit to `pyproject.toml`.

### 2. The board does not say which binary is the validator, and the two disagree

There are two copies. The **forge plugin cache** reports
`[ERROR] ADR-0025 circular supersession: ADR-0025 → ADR-0031 → ADR-0025 → ADR-0025`
— a regex bug that counts "supersedes" and "superseded by" as two edges. The
**`forge_1`** copy
(`/Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py`)
reports **0 errors**. `validate.py` itself is byte-identical between them;
`adr_integrity.py` is the only differing file.

Cost already paid: CARD-284's fix round 2 chased the phantom error; the
orchestrator once announced *"I have been running the wrong validator all
session"* and had to retract it; and **both** of wave 65's implementation rounds
reported the phantom error as pre-existing fact. <!-- STALE as of 2026-10-29, review
cycle 1's F-009: AC-1 landed OFF-BRANCH in main commit `7c68a7b1`, at
`meta/kanban/config.yml:37-45`, because /commit excludes meta/kanban from card
branches. The sentence below describes the board before that. -->
`meta/kanban/config.yml` named no
validator at all.

## What to implement

1. **Name the validator of record in `meta/kanban/config.yml`**, with the path and
   one line on why — the plugin cache's ADR-0025 error is a regex bug and the
   honest error count on this board is 0. Anything that reports a validator figure
   must be able to say which binary produced it.
2. **A guard that makes the erosion visible rather than silent.** The honest fix —
   resolving a ref against a **definition** — is forge-side and **not in this
   repo**, so this card does not attempt it. What *is* in reach: a test that walks
   every `check: {kind: test}` ref whose resolution depends **only** on files under
   `meta/review/`, `meta/profiling/` or on non-`def`/`class` prose, and reds. In
   other words: **re-implement `symbol_exists()` strictly, inside the suite, and
   fail on any ref that the loose version accepts and the strict one does not.**
   Per ADR-0039/R2 it must be **derived** — a `check:` shape it cannot classify is
   a FAILURE — and it must **not absorb** refs that genuinely resolve to a
   definition.
3. **Decide and record whether `:(exclude)meta/review` is the right forge-side
   narrowing, and say why it is insufficient.** It is not sufficient:
   ADR-0006/R1's ref is also spelled in prose inside `tests/` itself
   (`tests/test_export_pdf.py` at a comment and a docstring,
   `tests/test_puzzle_editor_ui.py` at a docstring), and **`tests/` cannot be
   excluded** — it is the only place the search must look. Record this as the
   argument for a definition-based resolver, so the next person does not propose
   the pathspec narrowing again.
4. **State the interaction with CARD-307 and do not duplicate it.** CARD-307
   repairs the node-id refs that do not resolve to a definition — **re-measured
   2026-10-29 to seven, not thirty**, after this card's own round found the earlier
   census had omitted `trace.yml`'s `tests:` lists. This card stops the *detector*
   from being eroded. Either without the other leaves a hole: repaired refs can
   still be silenced later, and an un-eroded detector still reports refs it cannot
   resolve.

## Acceptance criteria

- **AC-1** (the validator of record is written down): *Given* `config.yml`, *then*
  it names the validator path and the reason, and the reason states the plugin
  cache's error is a regex artefact.
- **AC-2** (a prose-only resolution is a failure): *Given* a `check: {kind: test}`
  ref that the loose search resolves **only** via `meta/review/**`,
  `meta/profiling/**`, a comment or a docstring, *then* the guard reds and names
  the ref and the file that resolved it.
- **AC-3** (the guard does not absorb honest refs): *Given* a ref that resolves to
  a real `def`/`class`, *then* the guard stays green — **and** given a ref whose
  only hit is a prose line in the *same* file as the real definition, the guard
  still stays green. The second half is the edge: CARD-301 deliberately kept one
  prose line naming its own test, and deleting the module holding the `def` still
  leaves `git grep -lw` exiting 0 on that line. (**Two mutants, one at the claim's
  edge**, per ADR-0039/R1.)
- **AC-4** (the live instance is reproduced as a regression): *Given* the guard,
  *then* it reds on NFR-001/AC-038's `TestGenerate_50x50_RespectsTimeoutBound` as
  the board stands — the ref whose warning the sync silenced. If that ref has been
  repaired by then, say so and pin a different class-(c) ref by name instead;
  **do not weaken the assertion to keep it green.**
- **AC-5** (the forge-side argument is recorded, not just the shim): *Given* the
  card and an ADR note, *then* the reason `:(exclude)meta/review` is insufficient
  is written down with the `tests/`-prose limit case, and the in-repo guard is
  explicitly labelled a **detector, not a repair**.

## Engineering constraints

- **EC:** across every `check: {kind: test}` ref on the board, the strict resolver
  and the loose resolver are compared, and every ref where they disagree is
  reported — neither direction silently dropped, derived from the registry and the
  ADR set rather than from a list in the test.

## Guardrails

- **G-1: do not edit anything under `/Users/omelnikova/MyProjects/forge_1/`.** The
  resolver's repair is forge-side and out of this repo's scope; this card records
  the argument and builds the in-repo detector.
- **G-2: the guard must not become the thing it detects.** A test that holds a list
  of dead refs **spells those refs in tracked code** and so revives them through
  the very mechanism it exists to catch. Derive the set from the registry at run
  time; if a ref must be named in source, name it in a form the loose search
  cannot match as the whole `path::name` string, and assert that property.
- **G-3: do not retire the review-YAML sync.** It is load-bearing — `forge:fix`,
  `forge:commit` and `forge:retrospective` read those reports, and without the copy
  they would not exist. The erosion is a cost of a protocol that must stay.
- **G-4: do not report a warning count without naming the binary.** (See the
  measured disagreement above.)
- **G-5: no test deleted, renamed, skipped or merged.** (**gate**: node-id set
  difference with `-o addopts=''`.)

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail; a comment saying what a test catches needs two mutants, one at the claim's edge (check: review-lens)
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an unanalysable shape is a FAILURE (check: review-lens)
- ADR-0006/R1 — the dependency baseline (check: the limit case this card documents — zero definitions, resolved by 110+ files including two `tests/` prose mentions)
- ADR-0025 — the ADR whose phantom circular-supersession error is the plugin cache's regex bug

## Architecture context

- **ADR:** ADR-0039/R1-R2, ADR-0006/R1, ADR-0025
- **Trace:** no requirement row changes; this card is about the instrument.

## Worktree notes

- Sibling of **CARD-307**, which repairs the refs this card stops from being
  silenced. Neither supersedes the other.
- The standing memory `review-yamls-revive-dead-check-refs` holds every measurement
  quoted above, including the `-w` word-boundary hole (`_` is a word character, so
  `git grep -w PropertyTest_Foo` does not match `def test_PropertyTest_Foo`) and
  the CARD-301 case where **both** gates were blind at once: pytest never opened
  `tests/bench_generate.py` because of `python_files` defaults, while the ref check
  was satisfied by that file's own comment banner about itself.

## [SECOND MEASURED INSTANCE — 2026-10-29, caught during CARD-291's own review sync]

The defect fired again **hours after this card was cut**, during mandatory
bookkeeping, and this instance is stronger evidence than the one above because
**the report's author was actively defending against the mechanism and tripped it
anyway.**

CARD-291's cycle-1 reviewer knew about the hazard and guarded for it: it wrote
`TestDependencyBaseline_IsExactlyPillowAndNumpy` into its YAML **split into two
pieces** and verified `git grep -lw` did not match its own report. That worked —
**0** occurrences of the whole token in the synced file.

It made no difference, because **a review report's most-quoted refs are its own
card's**, and on `main` those were the dead ones:

```
main, before the sync                      0 errors, 107 warnings
main, with the cycle-1 YAML synced         0 errors, 106 warnings
```

The warning that disappeared, and the only thing resolving it:

```
[WARN ] FR-046/AC-395  check names test
        'tests/test_approval_guess_gate.py::test_unknown_verdict_fails_closed'
        but no definition was found in the code

git grep -l 'tests/test_approval_guess_gate.py::test_unknown_verdict_fails_closed' \
    -- . ':(exclude)meta/architecture' ':(exclude)*.md'
→ meta/review/20261029T000000Z-CARD-291-cycle1.yml        # and nothing else
```

On `main` at that moment **the test did not exist** — it is on
`card/291-approval-guess-gate`, unmerged. The YAML spelled the whole
`path::name` three times while *discussing* the ref, and that was the definition
the validator accepted.

**Three things this sharpens for this card's round:**

1. **Author discipline cannot fix this, so do not propose it as the remedy.** A
   reviewer who knows the rule, names it in their report, and splits one token to
   avoid it will still revive the refs their own card is about. Any guard that
   depends on a report being written carefully is not a guard. AC-2's detector is
   the right shape precisely because it does not rely on the author.
2. **A warning count falling across a card's own pipeline is doubly
   untrustworthy** — the sync of that card's review report mechanically retires
   the warnings about that card's refs. **A card's gate must not credit its own
   warning delta without re-deriving each cleared warning against a
   `def`/`class`.** CARD-291's branch figure (102) was measured *before* this sync
   and `main` then moved to 106, so even the baseline shifted underneath the
   comparison. Both numbers are honest; comparing them naively is not.
3. **It is self-healing in this one case and that is not a defence.** AC-395's
   ref becomes a real definition when CARD-291 merges, so the silenced warning
   was about to become correct anyway. The mechanism does not know that. The same
   sync on a card whose test never lands leaves a permanently false reading, which
   is exactly the `TestGenerate_50x50_RespectsTimeoutBound` case above.

**AC-4 is amended by this**: pin **both** instances — AC-038's
`TestGenerate_50x50_RespectsTimeoutBound` (a ref that never landed) and this one
(a ref that landed later) — because they are the two halves of the behaviour, and
a detector that only catches the permanent case will read as working while the
transient case erodes every wave.

## [FOURTH INSTANCE, and this one is the orchestrator's own bookkeeping — 2026-10-29]

AC-4 names a ref whose premise is **confirmed and worse than written**. The test it
names has **no `def` and no `class` anywhere in the repo**, and under the
validator's pathspec it has exactly **two** resolvers:

```
meta/review/20261029T025000Z-CARD-301-cycle1.yml      <- the sync protocol (instance 1)
meta/kanban/dispatcher.state                          <- the orchestrator's own state log
```

**`meta/kanban/dispatcher.state` has no `.md` extension, so it is INSIDE
`code_search`'s domain.** `board.md` is excluded; the state log is not. So every
test or ref name written into the state log revives that ref — and this session
wrote one in while *recording this very defect*. **By documenting the erosion the
orchestrator became one of its two load-bearing resolvers.**

Measured across the whole state log: of the test-like names in it, two are refs with
no definition — the one AC-4 names (2 resolvers, one of them the state log) and
ADR-0006/R1's (109 resolvers, one of them the state log). The remaining matches were
**module stems** (`test_book_pdf`, `test_web_server`, …), not refs, and are not part
of this finding — said plainly because an inflated count here would be the same
failure as the one being reported.

**The immediate mitigation needs no code and is adopted from now on:** ref and test
names go in **card files**, which are `.md` and excluded, and **never** in
`dispatcher.state`. Cleaning the existing two out does not restore either warning
(the review YAML and the other 108 files still resolve them), so this is hygiene
plus a rule, not a repair — say so rather than claiming a fix.

**What it adds to this card's argument.** G-2 already warned that a guard holding a
list of dead refs revives them. This is broader and worse: **ordinary pipeline
bookkeeping in any tracked non-Markdown file does it**, with no guard and no test
involved. Two independent mandatory processes — the review-YAML sync and the
dispatcher state log — both feed the resolver, which is why author discipline cannot
be the remedy and why AC-2's detector must derive its verdict from whether the hit
is a **definition**.

**AC-5 is widened**: the recorded argument must name the full set of in-domain
resolvers it has to survive — `meta/review/**`, `meta/profiling/**`,
`meta/kanban/dispatcher.state`, `meta/kanban/backlog-scored.yml`, and prose inside
`tests/` itself — and state that only the last cannot be excluded, which is why a
pathspec narrowing is insufficient.

## [Review cycle 1 — 7.5, DOES NOT CERTIFY, 2026-10-29]

`min_score: 8`, cycle 1 of 3. **One gating finding, and it is a measured false green
in this card's own central claim.** Report synced.

**The review's own report revives nothing, verified rather than asserted** — `…`
truncation on every model ref plus a prefix check on each, confirmed two ways after
writing (the module's own trie over the full ref set returns `[]`, and real
`git grep -lw` for three dead refs returns 0 hits in the file). Its own check caught
its first draft spelling one ref in full, which it recorded as a **sixth** instance
of the hazard, *caught by mechanism rather than by care*. That is the card's thesis
demonstrated on its own reviewer.

### F-001, GATING — the derived set silently drops 16 `trace.yml` refs, and the self-check is blind to exactly those

`_declared_refs()`'s `tests:` block scan **`break`s on the first line that is not a
`- item`** — and three `tests:` blocks in `trace.yml` carry `#` comment lines
**inside** the list. Verified by the orchestrator at `:313`, `:1734` and `:2045`, and
every one of the three is a comment *about a retired test*:

```
yaml.safe_load          510 refs      <- the orchestrator's independent figure, exactly
break-on-non-item scan  494 refs
dropped, silently        16
```

**The consequence was reproduced, not reasoned about**: planting a dropped ref as a
whole token in the module gives **17 passed**, while real `git grep -lw` confirms the
module has become one of its resolvers. So
`test_this_module_resolves_no_verifying_ref_at_all`'s claim to cover *"every ref in
the model"* is false — **576 of 579** — and that claim is the entire answer to the
CARD-291 lesson this card was cut from. The silent drop also violates **ADR-0039/R2**,
the module's own cited rule: an unanalysable shape must be a FAILURE, not a `break`.

**Honestly mitigated, and the reviewer said so:** all 3 union-dropped refs are loose-
*and* strict-alive (real `class` lines in `tests/test_book_puzzle_frame.py`), so **all
six pinned counts are unaffected** — each re-derived exact. **Luck, not design.** Fix
is ~5 lines: raise instead of `break`, then re-derive six baselines that should not
move.

### The census is 579, and BOTH the round and the orchestrator were wrong

- round **576** — 3 low, via F-001.
- orchestrator **580** — 1 high: my ADR-inline figure of 44 is an **occurrence**
  count, and 45 occurrences resolve to 43 distinct refs.
- my `trace.yml` figure of **510 is right**, and it is what exposed F-001.

### The `…` device's reasoning is wrong while its safety holds

Verified by the orchestrator in a throwaway repo: **`git grep -lw ZZPrefix` matches
`ZZPrefix…Tail`.** So `…` *terminates* the token and exposes every prefix — the
opposite of the stated reason. What actually makes it safe is the **self-check**: the
reviewer planted `TestExport_RejectsUnverified…ForPDF`, whose prefix is a live ref,
and got **1 failed**. Today 0 of 5 truncations has a declared-ref prefix. **Safe by
mechanism, wrong argument** — and the docstring owes the right one. My brief repeated
the wrong reasoning too.

### What survived

- **Count+digest is a real measurement with an enforced detector and an unenforced
  response.** Detection proved **on the real mechanism**: appending a dead ref to a
  `meta/review/*.yml` — exactly what the sync does — reds **2 cells**, 13→14 and
  164→165. The digest is sorted and order-insensitive. **Repair-vs-signal-loss is only
  documented**, in `_assert_class`'s message, which also hands over the paste-ready
  line — so the lazy fix is one copy away.
- **The prefix bug is controlled.** Rebuilt out-of-tree, the `body + "?"` bug makes
  all 3 prefix refs lose **every** hit (1→0, 17→0, 14→0), and all three are in the
  cross-checked set, so the control bites. **The 29 refs are not a sample but
  exhaustive** over all 13 bookkeeping-only, all 13 falsely-dead and all 3 prefix
  refs — and a fuller cross-check is **not affordable**: 101 ms/ref → 58 s for 576,
  with one multi-pattern `git grep` killed by the OS.
- **M2 reproduced exactly: 2 failed**, 644→644 lines, blob verified both sides. All 17
  cells audited for the same vacuity shape; 14 are closed by a pin or an exact
  equality, and the one left is `assert len(defined) > 300` against a measured 382 —
  82 refs of headroom (F-005, low).
- `backlog-scored.yml` **6 refs / 4 undefined** confirmed. ADR-0042/R4 **57** resolvers
  confirmed — **57 stands, 79 is wrong.** The node-id table 20/1/2 = 23 confirmed.
- **New, and it extends the card's own list:** `meta/kanban/waves.yml` resolves **3**
  model refs, 1 undefined — a **fifth** kanban-side resolver, which the ADR lists
  without a measurement.

### The correction that matters most to the board's standing story

**ADR-0006/R1's rule content IS tested.** `tests/test_export_pdf.py:1249` asserts
`packages == {"pillow","numpy"}`, and its own docstring says *"ADR-0006's revision is
what makes this the **rule's** check and not just one card's guardrail."* So the
defect is a **phantom pointer, not an untested rule** — the ADR names the real test
only in a `#` comment inside the excluded `meta/architecture/**`. One-line repair,
**CARD-307's**. Every earlier framing on this board, including the orchestrator's
memory, implied the dependency baseline itself was unverified. It is not.

### Finding 7 — the `LeakedPatch` one-off is sufficient, and it is `kill_matrix.py`'s

Proven from source rather than by racing: `kill_matrix.py:1345`'s `_apply` does
`path.write_text()` on the **real tracked path** with restore in a `finally`, so the
window provably exists and a concurrent `git status`/`git diff` gives exactly the
observed pair. `:1255` is the fail-closed *"reached no assertion node"* branch, not a
corrupt tree. **The residual is worth a card**: the module *reads* the full-suite lock
but states at `:96` that it "never writes a lock anywhere", so **nothing serialises
its plant window against a concurrent `git add`/`commit`** — live right now with
three cards in flight, and the orchestrator's own commits are what surfaced it.

### Figures the reviewer corrected in the round

Runtime ~8.4 s → a **band of 7.9–16.4 s** over 7 runs. M3 reds **5** cells, not 4. The
docstring's "163 bare refs have no containing definition" is **191** — 163 is the
*falsely-alive* bare count, two domains in one sentence.
`_module_scope_silences`/`_check_log_invocations` live in **`test_guard_integrity.py`**
(`:1511`, `:577`), not `test_suite_profile.py` — all three still return `[]`.

### Skips — the round's "ZERO" is wrong for the canonical set

Deriving scope with the repo's **own** `scripts/impact_set.py --base f64112f2` (31) + 5
= **36 modules**: **3454 passed, 11 skipped, 1 xfailed, 0 failed, 468 s**. All 11 are
`conftest.py:207` `DATABASE_URL is not set`, named individually (9 in
`test_admin_binding.py`, 2 in `test_db_engine_lifecycle.py`), **none a gate for this
card**. The round's set was narrower than the selector on exactly the three
`db_required` modules — so its "zero skips" was true of its own scope and not of the
card's.

### Amendments owed

- **F-009**: the card said *"`config.yml` names neither"* — **stale**; AC-1 landed
  off-branch in `7c68a7b1` at `config.yml:37-45`. Corrected above. Its `Touches:` also
  predicts an untouched `meta/kanban/README.md`.
- **F-008**: AC-4's substitution is **honest and documented** — the original ref really
  was repaired (`def` at `test_approval_guess_gate.py:649`) — but **both** pins are
  *permanent* cases, so one sentence is owed saying a transient instance cannot be
  pinned stably by construction and is covered generically by the gate's class.

## [Fix round 1 — F-001 closed, and the one count that moved was the one nobody had pinned, 2026-10-29]

`19bc968b` → **`3f3012a4`**, one commit, 2 files. **0 files** under `meta/kanban/` or
`meta/review/`; nothing under `forge_1/`. Module run **19 passed in 9.05 s**.

**The fix replaces a mute stop signal with a classification.** `_declared_refs()` now
delegates to `_tests_block()` (`:374`), which judges every line: a `- item` is
collected; **a `#` comment or a blank line survives** (YAML ends a block sequence at
neither); a mapping key at or outside the key's indentation ends the list (`_MAPPING_KEY`,
`:269`); and **anything else raises `RefShapeNotClassifiable`** (`:274`, raising at
`:312` and `:342`) — ADR-0039/R2 satisfied where it had been violated.

**All six pinned class baselines are unchanged**, as cycle 1 predicted. **But one count
moved, and it was the one nobody had pinned**: refs resolving to a definition, **382 →
385** — exactly the three refs the silent drop had been removing, all real `class` lines
in `tests/test_book_puzzle_frame.py`. It is now pinned as `DEFINED = (385, …)` alongside
`CENSUS = (579, …)` and `TRACE_TESTS = (510, …)`, and it was **reported as a finding
rather than pasted over as a digest** — which is the behaviour the card's own
repair-vs-signal-loss rule asks for, demonstrated on itself.

**And the round would not let the mitigation be called design.** *"The fix removes the
silence, not the luck."* The six classes' non-movement stays a fact about today's data,
said so in `_tests_block`'s docstring; what became design is the layer under it — a line
the scan cannot classify now raises, and the census and `trace.yml`'s contribution are
pinned *and* cross-read, so a count that moves for any reason reds.

### The new witness is genuinely independent, and the round proved its own survivor

`test_the_trace_tests_lists_agree_with_an_independent_reading` (`:1338`) reads
`trace.yml`'s refs a second time by `_trace_tests_refs_by_backward_scan` (`:442`), which
**walks backwards** from every `- item` to the nearest enclosing key — so *"no line
between two items can terminate anything"*, precisely the forward scan's blind spot.
Verified by the orchestrator: a real second algorithm, not a restatement.

**M2 is a declared survivor with a real insight.** Deleting the second implementation
(`independent = set(primary)`) leaves **19 passed** — because *"an instrument that agrees
with itself looks exactly like one that agrees with something else."* So **the
independence, not the assertion, is what carries the claim**, and that is now in the
docstring. M1 (replaying F-001) reds **3 cells, 16 passed** — the new witness naming all
16 dropped refs, the new control, and the `DEFINED` pin — while the six class baselines
stay green, which **is** the measurement behind "it was luck". M1+M2 together still red.

### Repair-vs-signal-loss: declined as enforceable, with the reason where a reader meets it

The sharpest thing in the round. Enforcement needs the **departed** refs; a stored ref
list is exactly what G-2 forbids, because it would revive them; and a digest cannot say
who left. **"The property that makes the guard safe is the property that makes the
response unenforceable."** So the message is a prompt rather than a gate, and the message
itself now says so and points at the docstring. That is the right call: the alternative
was a guard that becomes the thing it detects.

### ADR-0006/R1, recorded in both places

The ADR now states it outright: the ref has zero definitions and **109** resolvers so the
pointer is genuinely dead, **but the rule is tested** at `tests/test_export_pdf.py:1249`,
whose own docstring says ADR-0006's revision is what makes it the rule's check — and the
ADR names that test only in a `#` comment inside the excluded `meta/architecture/**`. The
round calls the overstatement **the more dangerous of the two errors**, which is right,
and the module's *"What a report here does NOT claim"* section carries the same
distinction. The one-line pointer repair stays CARD-307's.

### Census 579, with the derivation and all three wrong figures named

510 from `trace.yml` + `requirements.yml`'s `test:` keys and block-form `check:` + **43
distinct from 45 ADR occurrences** (two re-declarations), unioned. The ADR names why each
earlier figure was wrong: **576** = F-001, **580** = occurrences counted as refs, **510** =
right but one authority. Forms: bare 555 / nodeid 23 / path 1.

### Four corrections to the orchestrator's brief, and one of them matters beyond this card

1. **PyYAML is absent from `pyproject.toml` entirely — not even a dev extra.** Verified:
   no test imports it, and it is present only as a transitive install (6.0.3). So the
   brief's *"it must be test-side only, which it already is"* **understates the
   problem**: a test-side import would be a **collection error on a bare checkout**,
   which `CLAUDE.md` guarantees must work. The round used a second implementation instead
   and proved it against `yaml.safe_load` **out of tree**, both returning exactly 510
   with an empty symmetric difference.
2. **The `382` figure was pre-fix** — see above.
3. **`_module_scope_silences`/`_check_log_invocations`: the locations in the brief are
   right, but the module never claimed otherwise** — it cites `_conditional_silences`,
   correctly placed at `tests/test_suite_profile.py:2743`. **So the correction did not
   belong in this brief at all.** Fourth data point on the orchestrator's
   mis-propagation: a correction carried into a brief where nothing needed it.
4. Its own draft docstring said *"replaying the bug gives 1 failed"*, written from the
   brief's framing; measured **3 failed, 16 passed**, and the docstring now carries the
   measured figure.

### G-2 re-verified exhaustively, and cycle 1's cost figure corrected

The module's trie over all **579** refs against its own bytes → `[]`; and **real
`git grep -lw`, all 579 refs, restricted to this file → 0 hits in 10.7 s.** Exhaustive,
not a sample — the per-ref cost falls to ~18 ms with a single pathspec, so cycle 1's
"not affordable" (101 ms/ref whole-tree) **does not apply to the self-check**.

**Node ids 9723 → 9742, +19/−0** (cycle 1 added 17; this round adds 2). **Skips: 11, every
one named**, all `conftest.py:207` `DATABASE_URL is not set` — 9 in `test_admin_binding.py`
and 2 in `test_db_engine_lifecycle.py`, confirmed by re-running just those two modules —
**none a gate for this card.** Validator at HEAD: **0 errors, 102 warnings**, identical to
main, adding and silencing nothing.
<!-- RETRACTED 2026-10-29 by the orchestrator, which wrote it. The figure was right
at `3f3012a4` and the comparison was wrong even then. "Identical to main" was reached
by comparing a branch's count to main's, which this card's own subject makes UNSOUND:
the two trees differ in WHAT RESOLVES, not merely in which report sits in
`meta/review/`. At that commit the branch read 102 and main read 100, and main was the
depressed tree — the two FR-045 refs resolving only through a synced review report.
The honest reading at `3fab6828` is **0 errors, 100 warnings, 23 of them "no definition
was found"**, and the branch equals main now because **main was merged in**, not
because an edit closed a gap. Fix round 2's own replay names the two that left as
SIGNAL LOSS rather than repair — which is this card's instrument detecting, on live
data, the very thing the orchestrator did to the board. -->

### CARD-315's subject, reproduced live from the other side

While the 36-module run was in flight, `git status` **repeatedly showed
`tests/test_db_engine_lifecycle.py` as modified with the diff vanishing seconds later** —
the plant window, observed by accident. *"With three cards in flight an `/commit` landing
in that window would capture another module's mutation."* **It committed with explicit
pathspecs** (the standing rule) and verified `git show HEAD --name-only` lists exactly its
two files — so this commit provably did not capture it. **That is CARD-315 confirmed from
a second direction, and the standing pathspec rule earning its keep.**


---

## Fix round 2, 2026-10-29 — `65dd11b4` → `3fab6828`, 3 files

**The gating finding is closed on all six shapes and all four authorities, and not
with a bolted-on `else`.** Each authority's scan now derives the lines it **reads**
from one shared `_declaration_key_lines()`, and every `test:`/`tests:`/`check:` key
that no narrow pattern claims goes to a default-deny naming file, line and text.
**Collection and refusal cannot drift apart, because both come from one notion of
where a declaration lives** — which is a stronger repair than the brief asked for.

**One nuance, measured rather than assumed**: the refusal arrives in one of two
frames. `trace.yml`'s `tests:` and the bare `test:`/`check:` keys are refused by the
key default-deny, which names the **line**; `requirements.yml`'s `test:` key is wide
enough to collect the garbage after the colon, so it is refused one frame later in
`Declared.form`, which names the shape and the authority but **not the line**. Both
satisfy R2. The message-quality gap is recorded in the code rather than papered over.

**Proof is a matrix, not a case**: **26 illegal shapes** driven at all four
authorities' declaration keys against a synthetic authority set in `tmp_path`, **plus
4 legal shapes asserted to still derive their ref** — without those a derivation that
raised on everything would pass every negative case while reading nothing.
Cycle 2's false green was **reproduced and then killed**: with the raise muted, a
planted scalar ref leaves census 580 and the backward scan 510 unmoved, invisible to
**both** readings, and the self-check trie clean; with the fix live it **raises**,
naming the file and line.

**The sharper rule the round states, which is the card's real lesson**: *a
cross-reading is not a default-deny.* Two readings of the same assumption about where
refs live agreed at 510 and were **both wrong**.

### Two holes it found that neither the brief nor cycle 2 named

1. **A declaration-key default-deny needs a region notion or it reds on English — and
   the shape is live today.** All **68** anchored `check:` lines in the ADR set are
   inside a fence. Exactly **one** declaration-key-shaped line is outside one, and it
   is **prose**: `0042-…md:153` wraps a sentence onto a line beginning *"tests: its
   0.48/1.28/2.08 pt are the owner's figures"*. **It arrived with main's ADR-0042
   edit.** A naive `^\s*(tests?|check):` default-deny would have reded the suite on it.
2. **The opposite failure already existed, and it is worse for a census.** Before the
   two halves shared one region, the narrow `_TEST_KEY` **collected a wrapped prose
   line inside a `rationale: >-` block as a ref.** A guard that *invents* a ref out of
   prose corrupts the census in the direction nothing else here checks. Found by the
   synthetic authority set, not by reading the code.

### F-002c2 taken, and demonstrated on the real event

The "unenforceable" claim is corrected in the docstring rather than dropped.
Per-member 12-hex digests on the two classes whose shrink reduces to **one**
mechanical question; a departed member is recovered **by name** by re-deriving the
580-ref population and matching the missing digest, then judged repair-or-signal-loss.
All 580 digests collision-free, measured. **Replayed against the real live event** —
the cut's 30-member honest-dead set against today's 28 — it raises and names **both**
departed refs as SIGNAL LOSS, each with its single resolver and `defined at (nowhere)`.
Deliberately **not** extended to the four large classes, with the reason measured: no
single mechanical question exists for them. ~~and their closure is the partition
arithmetic, verified to close — **373 + 166 + 13 + 28 = 580**, and **386 = 13 + 373**~~
— **that half is WITHDRAWN, see cycle 3 below.**
G-2 holds: a digest is not a ref, and the module's trie over its own bytes returns `[]`.

<!-- WITHDRAWN 2026-10-30 by the orchestrator, which wrote it. The retired clause called
the partition arithmetic a "closure, verified to close". Cycle 3 measured it a
**TAUTOLOGY** — over 2000 random synthetic populations the two identities were violated
**0 times**, because the four predicates partition on `(bool(loose), bool(strict))` and
`defined` is the union of two cells. **Neither sum can ever red.** "Verified to close" was
true and meaningless: I verified that an identity holds, and reported it as if a control
had passed.

The DECISION it was defending is right, for a reason cycle 3 supplied and I had not: a
**count-preserving swap** leaves `FALSELY_ALIVE` at 166 and **moves its digest**, so
detection is closed for all four classes **by the digests**, and only *naming* is not.
Fix round 3 replaced the argument in the module itself and labelled the sums a
consistency check rather than a mechanism.

This correction is the card's own subject turned on the card: a figure stated as a
measurement when nothing could have refuted it. ADR-0039/R4 covers exactly this and
executes nothing — which is why **CARD-304** now carries R4's flip to an executing check,
stamped into wave 67 by the waves 63-65 retrospective. -->

### The five pins that red against main — re-derived against a def/class

Merging main made F-004c2's prediction fire for real. `CENSUS` 579→**580** and
`DEFINED` 385→**386** are **honest** (one new bare ref with a real definition);
`HONEST_DEAD` 30→**28**, `BOOKKEEPING_ONLY` 13→**15** and `FALSELY_ALIVE` 164→**166**
are the **same two refs moving**, and that move is **SIGNAL LOSS** — nothing was
written and nothing repaired; the validator simply stopped seeing two dead pointers.
Recorded on `HONEST_DEAD`'s docstring in those words.

### Figures corrected, including two of the orchestrator's

- **The brief's ADR path had a doubled `decisions/` segment.**
- **The brief's "44, not 45" was right at `3f3012a4` and STALE at HEAD.** Measured at
  three revisions with two independent instruments: the cut and cycle 2 read 44
  occurrences / 43 distinct; HEAD reads **45 occurrences / 44 distinct / 47
  ref-mentions**, because main's ADR-0042 edit added one. **Pasting the brief's figure
  would have written a wrong number into the ADR — the exact failure the brief
  warned about, demonstrated on the brief.**
- **The `requirements.yml` row now sums**: **404 distinct** = 401 (of 421 `test:`
  keys) ∪ 10 (of 11 block-form `check:`), with **7 refs declared by both forms** — so
  411 mentions, 404 distinct, and the overlap is the reconciliation cycle 2's
  arithmetic was missing.
- ADR-0006/R1's resolvers **110**, not 109; ADR-0042/R4's **58**, not 57 — both right
  for cycle 2's tree, both climbing, now stated as climbing rather than fixed.
- **The node-id table's second column is the ADR's own mechanism firing inside the
  ADR's own table**: falsely-alive 1→**3**, honest-dead 2→**0**. The validator stopped
  flagging both dead node-id refs with nothing repaired.
- **One figure was removed rather than corrected**, and the reason is the finding: the
  docstring's truncation count is **unstatable**, because the sentence stating it
  contains ellipses of its own and so changes the quantity it reports. Replaced by the
  **property** — no truncation has a declared ref as its prefix — derived on every run.

### Its own two instrument traps, and one process error, all self-reported

`grep -c '\[WARN'` returned **no matches, exit 1**, over output plainly containing 100
indented `[WARN ]` lines; it refused to report that 0 and cross-checked against the
validator's own summary. And `_conditional_silences` returning `[]` for a first
positive control was a **documented limit** of the helper, not a dead instrument —
verified with a `skipif`-mark control.

**The process error, reported rather than hidden:** it ran `git stash push` on the
module **while a 36-module run was reading that file** — exactly CARD-315's plant
window, which its brief had told it to avoid. It stopped the run, discarded the
partial result, and every figure above comes from a clean re-run; the node-id baseline
taken in that window was independently re-confirmed by diff-level evidence needing no
stash. **G-5 derived: node ids 9783 → 9786, +3/−0**, with `9783 − 19 = 9786 − 22`, so
no existing node id moved.

---

## Review cycle 3 — the LAST — 8.0, CERTIFIES AT THRESHOLD

7.5 → 7.5 → **8.0** against `min_score: 8`. Cycle 2's gating finding is **closed, and
better than it was asked to be** — one `_declaration_key_lines` feeds both collection and
refusal across all four authorities, so the halves cannot drift. Verified by mutant, not
by reading: muting the refusal reds the control on the first shape, and a derivation that
raises on *anything* passes the clean baseline and all 26 negatives and is caught **only**
by the four legal shapes — so the non-vacuity floor bites.

### The lever the reviewer left, deliberately and not silently

Held **at** 8.0 rather than above by one residual (**F-001c3**). The reviewer states
plainly: *under the orchestrator's own brief — "a region misclassification that invents a
ref is gating; one that drops a real one is gating; one that reds on prose is gating" —
F-001c3 is gating and the verdict would be 7.5 / does not certify.* It did not apply that
letter, because the rule was written about **live** shapes (which is what made F-001c2
gating: a live class with the self-check reporting CLEAN), and **all four of its shapes are
measured latent**. Both outcomes are recorded in the report's own
`note_on_the_briefs_gating_rule`, so the choice is the owner's.

### F-001c3 — the region notion is not total: four shapes, all latent

Driven from 13 region shapes plus 8 block-scalar indicator variants against a synthetic
authority set, clean baseline derived and asserted first.

- **(a) INVENTION, the sharpest.** `rationale: >- # a note` is legal YAML and is **not**
  matched by `_BLOCK_SCALAR`, which demands end-of-line after the indicator. So its body is
  not treated as prose, and a body line beginning `test: ` whose text is a valid identifier
  is **silently collected as a declared ref** — census 4→5, nothing raised. This is the
  invent-a-ref failure fix round 2 reports closed, **reproduced one notch out**. The
  default-deny is *structurally* blind to it: it fires only where no narrow pattern claims,
  and invention happens exactly where one does. `CENSUS` is pinned exact so it reds — but it
  points a reader at a new declaration, not at prose. **0 such openers live.**
- **(b) `~~~` fences.** `_FENCE` knows only backticks; inside a `~~~` fence the ADR refusal
  is silently skipped. **No ref is dropped** — ADR collection is document-wide, verified — so
  this loses the *refusal*, not a ref. **0 `~~~` fences.**
- **(c) REDS ON ENGLISH.** An unclosed fence makes the ADR remainder "inside a fence", so
  the live `0042:153` prose shape raises. **Every ADR's fence count is even.**
- **(d) QUOTED KEY.** `"tests": [X]` matches neither `_DECLARATION_KEY` nor any narrow
  pattern, so it is invisible to collection **and** refusal — F-001c2's asymmetry un-closed
  for the quoted spelling. **0 quoted keys.**

**Two of the four fail in the SILENT direction**, which is this card's entire subject.
Closing all four: ~10 lines across `_BLOCK_SCALAR`/`_FENCE`/`_DECLARATION_KEY` plus four
matrix rows.

**The passes are stated too, because a hole list without them is not a measurement**:
indented fence raises; **a fence marker inside a block scalar inside a fence preserves
parity** (the body skip consumes the marker before the fence toggle sees it — the reviewer
expected this to break and it did not); HTML comments declare nothing in or out of a fence;
nested block scalars suppress prose *and* still collect a real key at the outer indent; all
eight of `>- > | |- |+ >+ |2 |2-`; tab-indented key.

### The 26-shape matrix — 20 of 26 control the right line, verified line by line

20/20 key-route refusals name the **correct** line; 6/6 form-route refusals name none.
**On the missing line number the orchestrator's brief overstates it 5/6 of the time**: the
form refusal quotes the offending text verbatim plus the authority, and for five shapes that
text is a unique grep handle. For the sixth — `test: >-` — it quotes `'>-'` and nothing
else, and on a registry with **152** block scalars that is no handle at all; there the brief
is exactly right. ~2 lines to close all six by carrying the line in `Declared.sources`.
**One control weakness**: the matrix's key-route assertion checks only that the refusal
mentions the **filename**, not the line — so a regression losing the line number keeps the
cell green.

### The partition arithmetic is a TAUTOLOGY — and the conclusion survives anyway

Over **2000 random synthetic populations** the two identities were violated **0 times**:
they hold by construction, because the four predicates partition on
`(bool(loose), bool(strict))` and `defined` is the union of two cells. So `373+166+13+28 =
580` and `386 = 13+373` **cannot red**, and fix round 2's argument for them is wrong.

**But the decision they were defending is right, for a different reason the reviewer
measured**: a **count-preserving swap** leaves `FALSELY_ALIVE` at 166 and **moves its
digest**. So **detection is closed for all four classes by the digests**, and only *naming*
is not — which is exactly what the round conceded. **Scope the digests to 2 of 6: correct.
The argument given for it: replace it.**

### F-004c3 — pure withdrawal is silent

The digest replay reproduces **verbatim** — it raises, says 2 left without gaining a
def/class, says SIGNAL LOSS, names both refs, prints each one's single resolver and
`defined at (nowhere)` twice. But the fourth case's `withdrawn` text lives **inside the
assertion message**, which only fires when `losses` is non-empty, so a pure withdrawal is
**silent**, and the module's own case-4 control asserts only that it does not raise.

### Two figures of the orchestrator's were wrong again, both carried

- **The runtime band.** The brief stated 7.9–16.4 s; the reviewer's **cold** reading is
  **18.47 s**, outside it. Five readings: 18.47 / 11.57 / 10.80 / 11.21 / 11.01, range
  **10.80–18.47 s**. A band is a measurement too, and it goes stale.
- **The impact base.** `--base 3fab6828` yields **0** modules, because it *is* HEAD. The 31
  comes from `--base 65dd11b4`, fix round 2's own base.

**Nothing on the card or in the module measured wrong at HEAD.** Removing the truncation
count was **right** — the property is derived by the same instrument that establishes it,
so it cannot drift.

### The stash residue: NONE, checked three ways

Working blob == HEAD blob by both `git rev-parse HEAD:<path>` and `git hash-object`;
`git status --porcelain` clean under `tests/` even with `--untracked-files=all`; and
`git stash list --date=iso` holds four entries whose **newest is 2026-09-23**. Nothing from
today survives. **The remediation is complete.**

### The hazard caught the third reviewer too, by mechanism

The impact scope's one xfail has a full `path::name` that **is a model-declared ref** —
reporting a pre-existing xfail the way pytest prints it would have made that report a
tracked resolver for it. The bare name is not a ref, so that is what the report writes.
**Caught by the self-check, not by care** — this card's thesis, on its third reviewer
running.

---

## Fix round 3 — under the owner's decision, no cycle behind it — `3fab6828` → `bb7da562`

One commit, two files (`tests/test_check_ref_resolution.py`, ADR-0039), +362/−54.
**Every mutant and region probe ran out of tree** in a separate `python -I` process
rebinding the authority paths — **no tracked file was modified and no stash was taken**
(`git stash list`'s newest entry is still 2026-09-23), so **CARD-315's plant window was
never opened**. That is the discipline fix round 2 failed and this round kept.

It also **confirmed the lock holder was alive** (CARD-285's gate pytest at 29m42s) rather
than assuming a stale lock, did all reading and editing first, and ran nothing until the
lock cleared — so **no figure here is lock collateral**.

### Item 1 — the region notion is total, and each of the four shapes is a row that reds

Three patterns changed (`_DECLARATION_KEY`, `_BLOCK_SCALAR`, `_FENCE`); the region helper
now tracks the fence's **marker character** and takes a `label` so it can refuse by name.

| shape | after | mutant that reds its row |
|---|---|---|
| commented block-scalar opener | opener recognised, body is prose — nothing collected, nothing raised | drop `(?:#.*)?` → *"INVENTED a ref … 5 refs derived instead of 4"* |
| `~~~` fence | candidate inside it **raises**, naming file and line | `_FENCE` back to backticks only → *"was SILENTLY SKIPPED instead of raising"* |
| unclosed fence | fails naming **the fence** — *"this ``` code fence is never closed"* | neuter that raise → the refusal names the prose line instead |
| quoted key | candidate claimed by nothing → **raises**, naming file and line | drop the quote group → reds as a silent skip |

**Two deliberate shape decisions, both recorded rather than silent.** The invention row is
the only one asserting *the opposite of a raise* — nothing raised **and** nothing collected
— because the default-deny structurally cannot reach the inventing direction. And the
quoted key was made a **candidate** rather than taught to the five narrow patterns, which
is a **declared deviation from the brief**: the brief asked for the quote allowed in each
narrow pattern; the round widened only the declaration key, on the module's own rule
*"do not widen a narrow pattern until it swallows the shape without reading it"*, because
the brief's shape would have added **four latent, live-untested collection paths**. R2
permits "classified or raising", and raising is the safe half.

**Every pass cycle 3 verified was re-driven, not reasoned about** — and the live
`0042:153` prose line still does not raise, measured precisely: `_DECLARATION_KEY` **does**
match that line, and it is not a candidate **because it is outside every fence**. Region
figures re-derived exact: **68** anchored candidates inside fences across the ADRs, **432**
in `requirements.yml` (421 `test:` + 11 `check:`), **75** in `trace.yml` (64 block + 11
inline). All four shapes **re-measured latent by the round itself**: 0 commented openers,
0 `~~~` fences, 0 quoted keys, every ADR's fence parity even, all 46 fence lines exactly
three backticks.

### Items 2–4

**Item 2**: `Declared.sources` carries `<authority>:<line>` on **all four** authorities;
all **6** form-route refusals name a line and **26 of 26** rows assert it. The control
weakness is closed properly — `want` is derived **independently**, by reading the written
file back off disk and locating the probe line **with a uniqueness assertion**, and both
halves were shown load-bearing by isolating which control catches each mutant.

**Item 3**: the argument is replaced in the module, with the sums kept as a consistency
check **explicitly labelled as not a mechanism**. (The card's own copy of the withdrawn
claim is corrected above — the round was forbidden to touch `meta/kanban/` and said so.)

**Item 4**: the withdrawal count is now emitted **unconditionally** via `warnings.warn`
where it is computed, instead of only inside an assertion message that renders when
`losses` is non-empty. Mutant `if withdrawn:` → `if False:` reds it. The green half runs
under an `"ignore"` filter so the suite's warning count is unmoved — which is why 980 is
unchanged.

### Nothing moved that was not meant to

All nine pins, the census **580**, forms **bare 556 / nodeid 23 / path 1**, both stored
per-member sets (**15**, **28**), 580 digests collision-free, G-2's trie `[]`, validator
**0 errors / 100 warnings / 23 no-definition** — every one re-derived **exact**. **Node
ids +0/−0** (9786, module 22): the four region rows are data rows inside the existing
matrix cell and item 4's control is inside the existing case-4 cell, which is exactly what
cycle 3 scoped. Impact scope 36 modules: **3459 passed, 11 skipped, 1 xfailed, 0 failed**
— identical to cycle 3 on the same 36. All 11 skips `DATABASE_URL is not set`, enumerated
by name, none a gate.

### Three corrections it made, and one is to a trap the orchestrator invented

- **Cycle 3's `--base` explanation was right about the number and wrong about the reason.**
  It said `--base 3fab6828` yields 0 *"because it is HEAD"*. Measured: the 0 depends on the
  **tree being clean** — with fix round 3 uncommitted, `--base 3fab6828` yielded **31**.
  Honest form: *a base equal to HEAD with no uncommitted changes yields 0.*
- **Cycle 3's runtime band is already stale**: 16.07–22.84 s against its 10.80–18.47 s, on
  the same machine within the hour, with CARD-285's gate overlapping part of it.
- **The orchestrator's `grep -c '\[WARN'` trap DID NOT FIRE, for the second round running** —
  it returns **100, exit 0**, agreeing with the validator's own summary. The trap as the
  briefs stated it is **wrong**: the failure was the `^` **anchor** in the orchestrator's own
  pattern (`grep -cE "^\[WARN"`) against output that indents its warnings, not the pattern
  `\[WARN` itself. A mis-stated trap propagated into three briefs and cost two rounds a
  verification each. Retired.

### Residuals it found and deliberately did NOT fix, scope being closed

- **`_FENCE` compares the marker character but not its length** — CommonMark requires the
  closing fence to be at least as long as the opener, so a 4-backtick opener closed by 3
  closes here and should not. Latent: all 46 fence lines are exactly three backticks.
- **`_BLOCK_SCALAR` accepts `key: >-#x`** with no space before the `#`, which YAML does not
  treat as a comment. It errs toward treating prose *as* prose — the non-inventing
  direction — and cannot swallow a declaration key, because the key test runs first.
- **A new way for an ADR edit to red the suite**: any ADR leaving a fence unclosed now
  fails the derivation. Fail-closed, and the message names the fence and says *"Close the
  fence"* — but the gate should know it exists.
- The seventh `both-agree` baseline is still unpinned, and the `path`-form class is still
  size 1.
