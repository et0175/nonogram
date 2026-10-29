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
