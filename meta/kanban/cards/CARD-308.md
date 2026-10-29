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
reported the phantom error as pre-existing fact. `meta/kanban/config.yml` names no
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
