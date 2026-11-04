# CARD-335: Committed measurement artefacts revive dead check refs — and the review YAMLs the reviews themselves write are the worst of them

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d) <!-- RE-OPENED FOR RE-ESTIMATION 2026-11-01: a SECOND, independent harm was measured (the resolver's batch budget blown 4.7x by 132.6 MB of binary corpora that match no ref), with a DIFFERENT dominant population from this card's own. The 1d prices harm A only. Do not start this card without re-pricing it, and see the owner question at the end. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** general-purpose
**TDD:** false
**Branch:** `card/335-committed-artefacts-revive-dead-refs`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-335
**Source:** CARD-316's fix round 1, 2026-10-31, F-012, then **re-scoped twice the same day** — once by CARD-316's review cycle 2, which measured the surface the hazard actually occupies, and once by the orchestrator confirming it on `main`. The original cut was wrong about where the problem lives. See *What this card got wrong when it was cut*. It measured that a blanket `scratchpad/**` glob reds its own G-2 guard immediately on three tracked files from an earlier card, named them by site, and routed the hazard rather than fixing it by reddening another card's artefacts — the right call for that card's scope. Re-measured at the decompose station, where the population turned out to be larger than three. See below.
**Idea:** —
**Wave:** 75
**Created wave:** 72
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/review/, meta/profiling/, scratchpad/, .gitignore, .gitattributes, tests/test_check_ref_resolution.py
<!-- .gitattributes ADDED mid-round, 2026-11-04: it is the only lever measured to bound harm B that keeps every artefact tracked, on disk and readable by the suite. Nothing was committed under meta/review/ or meta/profiling/ — see Worktree notes. -->
**Review score:** —
**Started:** 2026-11-04T08:33Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —


> **[POPULATION RE-MEASURED AT THE WAVE-75 STATION, 2026-11-04 — the card's cut figures are
> stale, and the direction is GROWTH.]**
>
> | | at the card's cut | measured today |
> |---|---|---|
> | files in the resolver's surface | 245 | **626** |
> | under `meta/review/` | 231 | **396** |
> | under `meta/profiling/` | 6 | **15** |
> | under `scratchpad/` | 4 | **33**, across three card directories |
>
> **But that is a THIRD derivation, and the card already contains two.** The 245 was this
> card's own; CARD-316's cycle 2 measured **322** from a different ref derivation, and the card
> already records that *"the two bracket and neither is the number"*. Today's 626 is `git
> ls-files` minus `tests/`, `src/`, `*.md` and `meta/architecture` — a **fourth** way of asking
> the question, not the answer. **Re-derive the population with the RESOLVER'S OWN instrument
> and state which derivation produced your figure.** The transferable point is that this card's
> subject is a number nobody can quote without naming an instrument.
>
> **What is not derivation-dependent, and is the reason this card is P1 today:** the surface is
> **growing every wave**, and wave 74 added to it on both axes. `scratchpad/card336/` committed
> **15** files; `meta/profiling/` more than doubled. `scratchpad` is **still not in
> `.gitignore`** (verified). And two of wave 74's reviewers had to run the resolver's own
> instrument **by hand** to prove nothing had been revived, because the validator's 525
> warnings mean its dead-ref detector is effectively blind — which is this card's other half.
>
> **One hazard this card must not trip, stated because its `Touches` includes `meta/review/`:**
> the per-card review YAMLs under there are **what the retrospective reads**, and wave 74 had
> to reconstruct four of them from reviewers' reports because none had been written. They are
> deliberately **untracked**, which already puts them outside `git grep`'s reach and therefore
> outside this card's problem. **A fix that deletes or relocates them destroys the record this
> board's own retro depends on.** Gitignoring the directory is fine; emptying it is not.

## Why this card exists

The validator of record resolves a check ref by a **text search over tracked files**:

```
git grep -lw <name> -- . :(exclude)meta/architecture :(exclude)*.md
```

`validators/utils.py:237`'s own docstring states the reason the excludes exist, and it
is exactly the failure this card is about:

> `excludes` are git pathspecs that MUST drop the architecture model and docs from the
> search — otherwise the matrix self-validates: trace.yml/requirements.yml name the
> test, so a renamed-away (dead) test still "exists" inside the very file that
> references it and the check silently passes. **Scoping to source files is what makes
> a dead link detectable.**

`scratchpad/` is not in that exclude list. So a dead ref spelled as a whole token in
any **tracked** file under `scratchpad/` resolves, the ref reads as alive, and its
dead-ref warning disappears. The damage is silent and it is in the direction that
hides work: a ref nobody has written reads as written.

This is not hypothetical on this board. CARD-318's merge gate went red on precisely
this — "members resolved from outside `meta/`" — after 55 scratchpad files including
raw validator dumps were committed. Those were untracked again, but **not all of
them**, and three later cards have since committed their own measurement scripts.

### Measured 2026-10-31 by the orchestrator — and the card's original figure was the wrong population

**What this card got wrong when it was cut.** It was scoped to `scratchpad/` and said
"eight files", from a loose 541-candidate over-set derived by regex. Both halves were off.
Re-measured on `main` with declared refs taken from a **proper YAML walk** of
`requirements.yml` + `trace.yml` (the `test`/`tests`/`ref` keys, 534 refs) against the
resolver's real domain (1440 tracked files, excluding `meta/architecture` and `*.md`):

| directory | files resolving ≥1 declared ref |
|---|---|
| `meta/review/` | **231** |
| `meta/profiling/` | 6 |
| `meta/kanban/` | 3 |
| `scratchpad/card318fix/` | 3 |
| `scratchpad/card309/` | 1 |
| `player/` | 1 |

**245 files outside `tests/` and `src/`** — and `scratchpad/`, the directory this card was
cut to clean, is **4 of them**. The worst individual offenders:

| refs spelled | file |
|---|---|
| **292** | `meta/profiling/suite-durations-20261023.txt` |
| 285 | `meta/profiling/card-235-durations-after.txt` |
| 285 | `meta/profiling/card-235-durations-poll-001.txt` |
| 285 | `meta/profiling/suite-durations-20261015.txt` |
| 75 | `meta/review/20260930T123942Z-CARD-139-cycle1.yml` |
| 37 | `scratchpad/card309/census-converted.txt` |

CARD-316's review cycle 2 measured the same surface independently and got **322** files
outside `tests/` and `src/` from a 576-ref set (raw strings plus an ADR inline-check scan).
**The two figures bracket rather than agree, so neither is the number** — they differ in how
a declared ref is derived, which is this board's recurring instrument problem. **Re-derive
against the live authorities and the live resolver as the first act of the round, and state
which derivation you used.** The tables above establish the *shape* — that the population is
large and that `meta/review/` dominates it — and nothing more.

### The structural point, which is why this is P1 and not housekeeping

**The per-card review YAML is the worst offender by construction**, because it is written by
the one agent whose job is to name test refs. A review that does its job thoroughly produces
the most polluting artefact on the board. That is not a mistake any single round made; it is
the default, and 231 files is what the default has accumulated.

It has already caused measured damage. CARD-308 measured a synced review YAML **silencing a
live dead-ref warning on `main`** (108 → 107, nothing repaired) — an *active* silencing, not
a latent one. So the population splits two ways and the distinction decides the fix:

- **Active silencing** — the ref has **no** definition anywhere, and the artefact is the only
  thing making it resolve. The warning is suppressed *today*. This is the damage.
- **Revival hazard** — the ref does have a real definition, so it resolves regardless and the
  artefact changes nothing now; it would revive the ref if that definition were removed.
  CARD-316's cycle 2 verified the three `scratchpad/card318fix/` files are this kind (both
  refs defined, at `tests/test_solver_strategies.py:396` and `tests/test_strategies.py:490`).

**Only the first kind is a defect to repair. Report both counts separately** — a round that
reports one number has not understood the finding.

## What to implement

1. **Derive the real population.** For each tracked file in the resolver's domain, ask the
   resolver's own question: does this file cause `git grep -lw <ref>` to succeed for a
   ref that is otherwise **undefined**? That is the only hit that matters — a ref with
   a real `def`/`class` somewhere resolves regardless and the scratchpad copy changes
   nothing. Report the population as *refs revived*, not *files with hits*.
2. **Untrack what is revived, and keep it.** Round artefacts are evidence; the fix is
   that they stop being *tracked*, not that they stop existing. Move them out of the
   repo (`~/Documents/nonogram-reviews/CARD-NNN/` is where this board already keeps
   round renders) or untrack in place, and record for each file which card produced it
   so the trail survives.
3. **Shut the door, and in the place that keeps reopening it.** `.gitignore` `scratchpad/`;
   decide what the standing convention is for `meta/review/` and `meta/profiling/`, which is
   the real decision here and is **not** simply "untrack 231 files" — a review YAML is a
   record someone may want. The options worth measuring are: keep them but **outside the
   resolver's domain** (the `*.md` exclusion already demonstrates the mechanism), rename them
   to an excluded extension, or have reviews spell refs in pieces as this board's briefs
   already require. Recommend one with the measurement behind it. If any card genuinely needs an artefact tracked, it can force-add one
   file deliberately — that is a visible act rather than an invisible default.
4. **Give it a control that can fail.** A cell that asserts no tracked file in the
   resolver's domain revives an otherwise-undefined ref, with a **positive control in the
   same run** (plant a known-dead ref into a tracked file under the directory, prove
   the cell reds, restore). Without the positive control a trie built wrong reads
   identical to a clean tree — which is the trap CARD-316's own G-2 cell was written
   to avoid.

## Acceptance criteria

- **AC-1** — Given the tracked set in the resolver's domain, when each file is asked whether
  it causes an otherwise-undefined declared ref to resolve, then the count of **refs
  revived** is reported, derived from the live authorities and the live resolver, and
  the number of such refs afterwards is **zero**.
  `check: {kind: test}`
- **AC-2** — Given the repaired tree, when the guard cell runs, then it fails on a
  planted known-dead ref in a tracked file in the resolver's domain and passes once the
  plant is removed — both directions demonstrated in one run.
  `check: {kind: test}`
- **AC-3** — Given the validator of record, when it is run before and after, then the
  warning count and the WARN **set** are both recorded, and any warning that
  **appears** is accounted for as a ref that was dead all along rather than one this
  card broke. Expect the count to **rise**: un-reviving a ref restores its warning.
  `check: {kind: test}`
- **AC-4** — Given the chosen convention, when a new measurement artefact or review YAML is
  written, then it lands outside the resolver's domain by default rather than by the author
  remembering to keep it out.
  `check: {kind: test}`

## Guardrails

- **G-1** — `src/` is not touched. This card changes no production code.
- **G-2** — **Do not run this card's own measurement into a committed file.** The
  defect is committed measurement artefacts; producing another one would be the
  finding reproducing itself. Every dump stays in the session scratchpad, untracked.
- **G-3** — **Do not spell a declared ref in any tracked file in a way that could pass
  for a `def`/`class` line.** Derive names at run time or join them in pieces. The
  orchestrator has reddened this board's guard by naming a verifying ref inside an
  explanatory comment.
- **G-4** — `/Users/omelnikova/MyProjects/forge_1` is read-only. The resolver's
  behaviour is the authority here, not something to change. Note that the exclude list
  is the validator's, so **adding `scratchpad/` to it is not available to this board** —
  which is why the fix is on the repo side.
- **G-5** — The expected direction is **more** warnings, not fewer. A round that
  reports the count going down has either removed a real definition or measured the
  wrong tree.

## Notes

The four items CARD-316's round routed out are now owned as: this card (F-012, the
scratchpad hazard), **CARD-334** (the seven `_meta.dec_expected` flags), and
**CARD-333** + **CARD-319** (the re-point blind spot and mutant 4's residue — both
need a check that reads what a test *asserts*, and both live in `forge_1`).

**The estimate went 0.5d -> 1d at the re-scope**, and the work changed shape with it: the
original card was a tidy-up of four files, this one carries a convention decision about 231.

**Not scheduled into wave 72 deliberately.** Two cards are in review against `main`
right now and both measure census and validator figures off it; moving refs on `main`
mid-review would invalidate their baselines. This card waits for the wave to close.

---

## A SECOND HARM, measured 2026-11-01 — and it refutes the orchestrator's guess about its cause

While verifying CARD-316's merge gate, the validator of record went from its stable
**0 errors / 88 warnings** to **0 errors / 525 warnings** on the same commit, minutes
apart. Every one of the 437 new warnings reads *"existence could not be determined — the
search tool itself failed"*.

**It is a timeout, and it is reproducible.** The resolver's batched path
(`validators/utils.py`'s `_grep_batch`) runs one `git grep -ow` carrying up to 200 `-e`
patterns, under a budget of `BATCH_TIMEOUT_BASE_S + BATCH_TIMEOUT_PER_NAME_S × N`
= **10.0 + 0.1 × 200 = 30 s**. Measured on this repository today, that same 200-name
batch takes **140.1 s** — over budget by **4.7×**. A single *per-name* grep, by contrast,
is **0.12 s**, so nothing is wrong with `git grep` itself.

**One timeout poisons the whole run.** `symbols_exist` assigns `None` to *every* name
still pending the moment a batch fails and returns immediately, so one blown batch is
worth hundreds of warnings. That is why the count moves 88 → 525 rather than by a few.

**The budget was calibrated against a repository that no longer exists.** The constant's
own sibling comment records *"one 482-name batch takes 0.41 s"*, measured on this
repository. Today a **smaller** batch takes 140 s. That is roughly a **340× regression**
against the figure the budget was set from, and no one has been in a position to notice,
because the failure mode is extra warnings rather than a crash.

### RETRACTED, and then re-measured: the cause IS this card's population

**This section previously said "the cause is NOT this card's population — the orchestrator
predicted wrong", and blamed two large binary corpora. That is retracted: it was measured
in the wrong unit and the conclusion was false.** It is kept as a retraction rather than
deleted, per ADR-0039/R4, because the wrong reasoning was acted on — 422 files were
untracked on the strength of it.

**What the byte argument got wrong.** It ranked the search domain by *bytes*, where
`silhouette/animals/` (76.6 MB) and `nonogram-web/.next/` (56.0 MB) dominate at 74 %. But
git grep skips a binary file on a NUL byte in its first 8 kB, so those bytes were never
being paid. Untracking all 132.7 MB of them moved the batch from **140.1 s to 140.9 s** —
a 0.6 % change, i.e. nothing — and the validator still read 525.

**Measured properly, varying one thing at a time, the driver is an interaction:**

| patterns | corpus | time | budget | |
|---|---|---|---|---|
| 200 | full | **140.9 s** | 30 s | **over 4.7×** |
| 200 | **minus `meta/review` + `meta/profiling`** | **0.7 s** | 30 s | **201× faster** |
| 160 | full | 53.2 s | 26 s | over |
| 140 | full | 40.0 s | 24 s | over |
| **120** | full | **10.5 s** | 22 s | **ok** |
| 100 | full | 8.6 s | 20 s | ok |
| 80 | full | 7.4 s | 18 s | ok |
| 60 | full | 3.9 s | 16 s | ok |
| 50 | full | 0.3 s | 15 s | ok |

Two facts fall out, and both matter:

1. **There is a cliff between 120 and 140 patterns.** Below it the cost is near-linear and
   comfortably inside budget; at 140 it quadruples. `BATCH_SIZE = 200` sits well past it.
   The budget formula `10.0 + 0.1 × N` models cost as **linear in N**, which is true below
   the cliff and false above it — so the budget is least generous exactly where the cost
   explodes.
2. **The cliff only exists because of `meta/review/` + `meta/profiling/`.** With those two
   excluded, even 200 patterns runs in **0.7 s**. They are 40 % of the domain's 592,810
   text lines, and they are this card's own population — the files that spell ref names.

**So the original prediction was right and its correction was wrong.** The ref-spelling
corpus is the cause; it just does not work through bytes. It works by giving a large
alternation of word-bounded patterns an enormous number of near-matches to resolve.

### What is actually actionable, and what is the owner's

- **`nonogram-web/.next/` is already gitignored and still tracked.** `.gitignore` carries
  **three** matching rules — `:38 .next/`, `:39 .next/cache/`, `:45 nonogram-web/.next/` —
  and `.gitignore` does not untrack what is already in the index. So 56 MB of **build
  output** is committed against the repo's own stated intent. Untracking it
  (`git rm -r --cached`) leaves every file on disk and is reversible. This is the one
  clearly accidental item.
- **`silhouette/animals/` was also untracked**, on the owner's explicit instruction
  (254 files, 76.6 MB, all still on disk). Recorded because it changes a property rather
  than a detail: **git is no longer the backup for those files.** History retains them and
  re-adding restores the status quo, but a fresh clone will not carry them.
- **Neither untracking fixed anything**, and the commit (`7c987f67`) says so in its own
  message rather than claiming a win. Both stand on repository hygiene; the timeout was
  untouched by them.

### The two fixes that WOULD work, and only one is this board's

- **Reduce the batch size below the cliff.** At 120 patterns the full corpus costs 10.5 s
  against a 22 s budget. This lives in `BATCH_SIZE` in **`forge_1`**, which this board
  never edits — so it is not available here, only reportable. Worth reporting: the budget's
  linear model is what hides this, and a batch of 200 is the only size at which the
  resolver silently stops answering.
- **Take `meta/review/` + `meta/profiling/` out of the resolver's domain** — which is
  **exactly the convention decision this card already carries for harm A.** With them
  excluded, 200 patterns costs 0.7 s. So one decision closes both harms, which is the
  strongest argument yet for making it: the same change that stops dead refs being revived
  also stops the resolver timing out.

**That convergence is the headline for whoever takes this card.** Harm A and harm B looked
like two problems with two populations. Measured, they are one population and one fix.
- The resolver's exclude list lives in `forge_1`, which this board never edits, so a
  wider exclude is **not available here** — the same constraint this card already records.

### Credit where it is due: the validator behaved correctly

Its existence check is deliberately three-valued, and its docstring says why: *"None is
never coerced to either answer; True would let a broken grep silently revive dead refs,
False would let it fabricate drift ERRORs."* Under a tool failure it reported
**tooling failure, not a verdict** — on 437 refs at once. A two-valued check would have
silently declared them all dead, or all alive. **This is the single best argument on the
board for three-valued existence**, and it should be cited wherever that design is
questioned.

## Worktree notes

*(2026-11-04, implementation round 1. Nothing in this section is committed: `kanban
done` step 2d / INV-023 refuses a card branch that commits under `meta/kanban/**` or
`meta/review/**`, which is also the first finding below.)*

### The population, re-derived, with the instrument named

**Instrument:** `tests/test_check_ref_resolution.py` — this repository's own
reimplementation of the resolver (`_in_domain_files` = `git ls-files` minus
`meta/architecture/` and `*.md`; `_loose_resolution` = a trie with `git grep -w`'s word
boundaries over every in-domain file's bytes; `_strict_resolution` = a `def`/`class`
line). It is the resolver's own question asked over the resolver's own domain, and it
has its own controls (`test_the_loose_resolver_agrees_with_git_grep_itself`,
`test_the_definition_search_finds_a_definition_known_to_exist`).

| derivation | unit | figure |
|---|---|---|
| **refs REVIVED — active silencing (this round, the only unit AC-1 names)** | refs | **10** |
| of them, by `meta/review/*.yml` | refs | 9 |
| of them, by `meta/profiling/*.txt` | refs | 1 |
| of them, by `scratchpad/**` | refs | **0** |
| bookkeeping-only class (the module's own gate) | refs | 11 |
| the card's cut derivation, re-run today (files resolving ≥1 ref outside `tests/`+`src/`) | files | **310** (was 245) |
| the station's derivation, re-run today (`git ls-files` − `tests/` − `src/` − `*.md` − model) | files | **626** (reproduced exactly) |
| the resolver's whole domain | files | 1058 |
| files resolving ≥1 declared ref | files | 438 |

**The figure is derivation-dependent and the four existing figures are four different
questions**, not four answers: 245 and 310 count *files with hits outside the code
roots*, 626 counts *files in the domain outside the code roots* (it does not ask about
refs at all), 322 counted files against a wider ref set. None of them is a count of
harm. **10 is.** `scratchpad/` — the directory this card was originally cut to clean —
revives **nothing**: its 55 tracked files are the revival-*hazard* class CARD-316 cycle 2
already identified, not the active-silencing class.

### The convention, and what it is not

**Chosen:** `.gitignore` the three populations by the extension that carries the harm —
`meta/review/*.yml`, `meta/profiling/*.txt`, `scratchpad/` — so the next artefact lands
**outside** the resolver's domain by default and a tracked one is a visible `git add -f`.
Held by `test_no_new_artefact_file_is_force_added_into_the_resolver_domain`, whose
authority is `git check-ignore --no-index` over `git ls-files` — the repository's own
ignore rules, enumerated at run time (ADR-0039/R2), not a list in a test.

**Scoped by extension and not by directory, deliberately:** the `.md` records under both
directories are already outside the resolver's domain and are read by the suite
(`tests/test_guard_integrity.py` reads `meta/review/CARD-239-claim-sweep.md`), and the
`.py` tools under `meta/profiling/` are code that `test_guard_integrity.py`'s
`GUARDED_DIRECTORIES` is answerable for — ignoring that directory wholesale would quietly
move a future tool **outside** a guard, which is R2 inverted.

**NOT chosen — untracking what is revived (the card's item 2), because it is not
available to a card branch and is not reversible for consumers:**

1. **INV-023.** `kanban done` step 2d diffs `<merge-into>...HEAD -- meta/kanban meta/review`
   and **refuses** on any path. 9 of the 10 revived refs live under `meta/review/*.yml`.
   A card branch cannot touch them at all; retiring them is an owner action on `main`.
2. **A merge turns untracking into deletion.** Measured in a throwaway repository: branch
   `git rm -r --cached meta/review` + `.gitignore`, merge into `main` → the files are
   **gone from `main`'s working tree** (`meta/` removed entirely). "Untrack in place" is
   true only in the branch; for every other working copy it is `rm`. The review YAMLs are
   the only record of four of wave 74's cycles.
3. **The suite reads the dumps.** `tests/test_suite_profile.py` globs
   `suite-durations-*.txt` and asserts it finds one; `test_browser_fixture_scope.py` and
   `test_admin_local_cost.py` read five more `meta/profiling/*.txt` by name; this module's
   own `_G2_DOMAIN` globs `scratchpad/card316/*.py` and reds if the domain collapses below
   four files. Untracking any of the three populations therefore reds the suite on `main`
   one merge later, by the mechanism in (2).

**NOT chosen — renaming to an excluded extension (the card's third option): refuted.**
`forge_1` reads `meta/review/*.yml` by glob in at least four places (`done`'s canonical-report
refusal, `review_copies.py`, `release_notes.py`, `parse_review.py`), and the suite pins the
`.txt` dump names above. A rename breaks the consumers; it is strictly worse than leaving
the files where they are.

### Harm B: fixed, and the attribution in the card is wrong

`.gitattributes`: `meta/profiling/*.txt binary`. One line.

| N=200 (`BATCH_SIZE`), budget 30.0 s | elapsed |
|---|---|
| full in-domain corpus | **117.38 s** (over 3.9×) |
| minus `meta/profiling` | **0.55 s** |
| minus `meta/review` (396 files) | **115.41 s** |
| minus `scratchpad` | **123.30 s** |
| minus all three | 0.39 s |
| **full corpus, `meta/profiling/*.txt` marked `binary`** | **1.10 s** |

**The card's claim that the cliff "only exists because of `meta/review/` + `meta/profiling/`",
that they are "40 % of the domain's text lines" and that "harm A and harm B are one
population and one fix" is RETRACTED (ADR-0039/R4).** Varied one directory at a time, the
entire cost is the **10 machine-written `.txt` duration dumps**; removing all 396 review
YAMLs buys 2 %. Harm A is 9/10 under `meta/review/` and harm B is 100 % under
`meta/profiling/*.txt`: **two populations, two fixes**, and the convergence argument the
card calls "the headline for whoever takes this card" does not hold.

`binary` is **answer-preserving**, which is why it is this and not a rename or an
untracking. Measured on a token present only in those dumps: `git grep -lw` (the
per-name path, which reads the exit code) still lists all three files, so the ref still
resolves; the batched path prints `Binary file … matches`, so no name is recovered from
the chunk and the resolver leaves those names to the per-name path — the case
`symbols_exist`'s own docstring already documents (CARD-133 cycle-1 F-002).

**Validator of record, before → after** (`forge_1`, read-only, `--phase all`):
**0 errors / 525 warnings → 0 errors / 89 warnings**, wall 97 s → 8.3 s. WARN **sets**
compared with `comm` on `^[[:space:]]*\[WARN`, both sides asserted non-empty (525 and 89
unique lines): **436 disappeared, all 436 of them "existence could not be determined —
the search tool itself failed"; 0 appeared; 89 identical.** The drop is the tooling-failure
class and nothing else, so it is repair and not blindness. 525 = 89 + 436.

**G-5 ("expect MORE warnings") does not fire, and that is correct:** nothing was
untracked, so no revived ref lost its resolver and no suppressed warning came back. The
10 revived refs are still revived. Harm A is **diagnosed and bounded, not repaired**.

### Is a blown batch loud now?

**On this board, yes:** `test_the_resolver_batch_answers_inside_its_own_budget` runs the
resolver's own `git grep -ow` at `BATCH_SIZE` under the resolver's own budget and reds by
name when it does not answer, with an in-run control (a 0.05 s budget must report failure,
so the cell cannot be a function that returns `True`). Cost ~1 s green, bounded by the
30 s budget when red.

**Inside `forge_1`, no — and the defect is narrower than "silent".** `_grep_batch` catches
`TimeoutExpired` in a bare `except Exception` and returns `(None, set())`;
`symbols_exist` then assigns `None` to every pending name. The validator *does* report
that — 436 typed WARNs saying the search tool failed — so the signal is not lost. What is
lost is the **cause**: a timeout, an uncompilable pattern and an `OSError` are collapsed
into one untyped `None` with no message and no stderr, which is why two reviewers had to
re-measure by hand to find out it was a timeout. Two findings for `forge_1`, which this
board does not edit (G-4): the swallow (ADR-0038/R8) and `BATCH_SIZE = 200` sitting past
the cliff while the budget models cost as linear in N.

### The control: a planted dead ref, both directions, on disk

`meta/architecture/trace.yml` sha256 `737466b6…cff31` clean, `982e5553…9848` planted;
probe file sha256 `22733bb3…9cdb`. Restored byte-identical (`git diff --exit-code` clean).

| state | tree | errors | warnings | the planted ref |
|---|---|---|---|---|
| 0 | clean | 0 | 89 | — |
| 1 | a never-defined ref added to FR-015's `covered` tests | **1** | 89 | reported: "dead link: the test was renamed/removed, or never written" |
| 2 | **+ one force-added `scratchpad/card335/revival_probe.txt` spelling it** | **0** | 89 | **gone — revived by one tracked artefact** |
| 3 | that file untracked again | **1** | 89 | reported again |
| 4 | model restored | 0 | 89 | — |

State 2 is CARD-308's 108 → 107 reproduced by hand, with the direction and the mechanism
visible: one file, no code written, the error retired. At state 2 the new census cell
**redded by name** and it is green in every other state — so the guard catches the cause
and the detector still detects a dead ref. The `git add` at state 2 needed `-f`, which is
the convention being in force.

### Residual, owned by nobody yet

* **9 refs still actively silenced** by 5 tracked review YAMLs (`…CARD-139-cycle1` revives
  6 of them, `…CARD-134-cycle3` 2, `…CARD-117-cycle1` 1, `…CARD-305-cycle1/2` 2). Their
  declarations cluster at `requirements.yml:4310–4452` plus `:4609`, and one more at
  `:3847` is the `meta/profiling` one. Identified by `_digest_of` in the round's report,
  never by name (G-2/G-3). Retiring them means untracking 396 files on `main` with an
  out-of-repo copy taken first — an owner action, outside a card branch, and the merge
  mechanism in (2) above is why the copy has to come first.
* **`meta/kanban/dispatcher.state`** keeps one more bookkeeping-only ref alive and is
  board state that must stay tracked. No pathspec convention reaches it; this is the limit
  case the module's docstring already argues only a definition-based resolver can close.
