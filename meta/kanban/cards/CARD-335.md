# CARD-335: Committed measurement artefacts revive dead check refs — and the review YAMLs the reviews themselves write are the worst of them

**Status:** done
**Priority:** P1
**Category:** tech-debt
**Estimate:** 2c (1d)
<!-- Comment moved to its own line at the merge gate: the SAME CARD-341 defect the transplant commit fixed on `Touches` was still live here, and `parse_card_fields` was returning the whole comment as part of the Estimate value — so any census reading this field read the estimate as the string "2c (1d) <!-- RE-OPENED ... -->". The field now parses at `2c (1d)`. -->
<!-- RE-OPENED FOR RE-ESTIMATION 2026-11-01: a SECOND, independent harm was measured (the resolver's batch budget blown 4.7x by 132.6 MB of binary corpora that match no ref), with a DIFFERENT dominant population from this card's own. The 1d prices harm A only. Do not start this card without re-pricing it, and see the owner question at the end. NOTE: the attribution in this comment is itself retracted — the bytes were never being paid (git grep skips a binary file on a NUL byte in its first 8 kB) and the 4.7x is a wall-clock ratio that has since been read five different ways. See *A SECOND HARM* and correction 2. -->
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
**Review score:** 8.0 (cycle 1 of 3 — CERTIFIED)
**Started:** 2026-11-04T08:33Z
**Closed:** 2026-11-04T12:18Z
**Actual:** A **derived size datum**, not a clock reading. Landed on main: **4 files, 680 insertions / 30 deletions** — `tests/test_check_ref_resolution.py` **348/0**, `meta/kanban/cards/CARD-335.md` **256/30**, `.gitattributes` **49/0**, `.gitignore` **27/0** — with **3 test functions / 3 node ids added, 0 lost** and **0 lines of `src/`** (G-1). The sharper datum is the ratio the deliverable has to itself: of the **76** lines added to the two config files, **4 are rules** — `meta/review/*.yml`, `meta/profiling/*.txt` and `scratchpad/` in `.gitignore`, and `meta/profiling/*.txt binary` in `.gitattributes` — derived by stripping comment and blank lines from the added side of the diff rather than by trusting a count. The other 72 are the reasoning; the 348 test lines are three cells and their controls. So **680 insertions buy four lines of configuration and three cells**, and everything else is the measurement that establishes *which* four lines — this card's own thesis, that a figure is nothing without its instrument, applied to itself. **The wall-clock figure is excluded**, under the owner's standing ruling that wall-clock actuals are unusable for estimate calibration because the clock measures the **queue** rather than the work: this gate spent ~11 minutes blocked on CARD-337's implementation round holding the full-suite lock, and `main` advanced twice underneath it (`d4aa00ae` → `494c0aa2` → `b95e1a34`), costing three rebases; none of that is work done on this card. The size datum above substitutes for it, and this sentence is here so a reader **meets** the exclusion rather than noticing an omission. **Estimated 2c (1d) and certified on cycle 1 of a 3-cycle budget, so the cycle ratio is 1 / 2 = 0.500 — OVERESTIMATED.** That is the **first non-1.000 cycle ratio on this board**: CARD-278 (1c, cycle 1), CARD-339 (2c, cycle 2) and CARD-336 (1c, cycle 1) were each exact, so wave 74 went three-for-three and its calibration signal could only say the estimates were right. **This is the first one that points anywhere**, and it is recorded as a datum, not as a criticism of the estimate — a card re-opened for re-estimation on a second, independently measured harm, carrying a convention decision about 396 files, was honestly priced at two cycles and then certified on the first. The one duration recorded anywhere here is the gate suite's own wall-clock as pytest printed it, quoted as a gate fact; **nothing in this card's code was timed, and correction 4 is why — five such figures were removed from `.gitattributes` in this very round.**
**Merge commit:** `9a6b8e89` — merged `--no-ff` onto `ec42e9fd`, **one kanban-only commit past the `b95e1a34` the gated tree was rebased onto** (`board.md` plus CARD-322/358/364); it touches no `tests/`, no `src/` and none of the branch's three files, so the gated baseline is unaffected and no re-run was owed. Gated tree `a94e098b`; merge-base `b95e1a34`. **The rebase took NO conflict — not in the card file, not anywhere** — because the branch never committed under `meta/kanban/**`: INV-023 holding, rather than a gate working around it. **Full suite on the frozen gated tree, `DATABASE_URL` armed, `-o addopts=` as two argv items and `-rEfs`, under the board's own lock held as this worktree: 10281 passed / 0 failed / 0 errors / 1 skipped / 1 xfailed, exit 0, 1485.01s.** **Not vacuous:** passed + skipped + xfailed = 10281 + 1 + 1 = **10283 = the collected count exactly**. **Skip attributed from `-rEfs`, never recalled, and the count is 1 rather than an unarmed gate's 27:** the single skip is the `setrlimit(RLIMIT_AS)` platform gate in `tests/test_book_pdf_memory.py`. The bare-`DATABASE_URL` check fired **zero** times and no `Database not reachable` skip appeared at all — the positive evidence that the arming took, i.e. the 26 tests that skip unarmed were **executed**. **Neither CARD-349 hazard was live, checked BEFORE the run rather than diagnosed after:** the derived database `…_card_335_efaa212effb1_test` already existed, so the missing-database red could not fire, and its `alembic_version` was **018** against a single migration head of **018**, so the stale-schema red could not either. **G-8 honoured** — the URL names a `*_test` database on localhost, never production. **Node-id delta, two instruments agreeing on the SET and not merely the total: 10280 → 10283, 0 lost and 3 gained**, all three in `tests/test_check_ref_resolution.py`. Instrument A is whole-suite collection with `-o addopts=` on both sides; instrument B is an `ast` walk of the two blobs git holds for every `.py` file the branch touches, which names the same three and nothing else. **G-1/G-2 on the merged tree:** `git diff --name-only ec42e9fd HEAD -- src/` empty and `git status --porcelain src/` clean. **G-5 reads correctly and does not fire:** the validator of record on merged `main` is **0 errors / 89 warnings**, the standing baseline unmoved — nothing was untracked, so no revived ref lost its resolver, which also confirms on `main` that marking the dumps `binary` is answer-preserving. The force-add census on merged `main` measures **477**, equal to the baseline the cell pins.
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

1. ~~**There is a cliff between 120 and 140 patterns.**~~ **STRUCK by review cycle 1 and
   re-measured at the merge gate (ADR-0039/R4 — kept, not deleted, because it was acted on:
   it produced the `BATCH_SIZE = 120` recommendation below). There is no cliff.** The curve
   is smooth, monotone and **super-linear** — re-derived at the gate on the full-text corpus
   with the resolver's own argv (N=50 1.8 s · 80 8.8 s · 100 17.5 s · 110 23.0 s ·
   120 30.3 s · 140 51.7 s · 160 65.6 s · 200 109.3 s), an exponent near N^3 across the
   whole range with no step anywhere in it. The cycle-1 reading is the same shape with
   different constants (N^2.7–2.9). What the "cliff" actually was: the budget line
   `10.0 + 0.1 × N` crossing a super-linear cost curve once. **The real finding is the
   SHAPE** — see *Review cycle 1 — corrections*, correction 2.
2. ~~**The cliff only exists because of `meta/review/` + `meta/profiling/`.**~~ Half right,
   and the half that is wrong is the one the card leaned on: measured one directory at a
   time (round 1, confirmed at the gate) the cost is **`meta/profiling/*.txt` alone** —
   withholding all 396 review YAMLs leaves the batch indistinguishable from the full
   corpus. The "40 % of the domain's 592,810 text lines" figure counts lines, not cost. See
   *Harm B: fixed, and the attribution in the card is wrong*, below.

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

- ~~**Reduce the batch size below the cliff.** At 120 patterns the full corpus costs 10.5 s
  against a 22 s budget.~~ **WITHDRAWN at the merge gate: the figure does not work, and no
  fixed `BATCH_SIZE` can.** N=120 has now been read **five** times on this one tree —
  10.5 s (the card) · 31.55 s (round 1) · 41.76 s (cycle 1) · **30.3 s and 30.6 s (the
  gate, two instruments)** — and at four of the five readings it is **over** its own 22 s
  budget, so handing `forge_1` "lower it to 120" would hand it a constant that is already
  blown. The argument that survives is stronger than a constant: **a linear budget against
  a super-linear cost fails at some N for any constants, and the crossing moves with the
  corpus and with the host** — cycle 1 measured it already crossed at N=100, the gate
  measured N=100 still inside (0.90×) and N=110 over (1.09×), on the same tree. **So
  "calibrate N against the clock" is a figure that expires, not a repair**, and the budget's
  SHAPE is the finding. That is an argument *for* what this card did: the corpus fix takes
  N=200 from over three times its budget to **1.0 s against 30 s**, a margin of more than an
  order of magnitude, which no re-measurement is going to eat.
- **The two honest `forge_1` findings, then, are:** (a) the bare `except Exception` in
  `_grep_batch` collapsing timeout, uncompilable pattern and `OSError` into one untyped
  `None`, so the cause is lost while the signal survives; and (b) the budget's **shape** —
  `BATCH_TIMEOUT_BASE_S + BATCH_TIMEOUT_PER_NAME_S × N` models a cost that is not linear
  in N. **Not a new constant.**
- **Take `meta/review/` + `meta/profiling/` out of the resolver's domain** — which is
  **exactly the convention decision this card already carries for harm A.** With them
  excluded, 200 patterns costs 0.7 s. So one decision closes both harms, which is the
  strongest argument yet for making it: the same change that stops dead refs being revived
  also stops the resolver timing out.

~~**That convergence is the headline for whoever takes this card.** Harm A and harm B looked
like two problems with two populations. Measured, they are one population and one fix.~~
**RETRACTED by the implementation round and confirmed at the gate — two populations, two
fixes.** Harm A is 9/10 under `meta/review/`; harm B is 100 % under `meta/profiling/*.txt`.
See *Harm B: fixed, and the attribution in the card is wrong*.
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
| the resolver's whole domain | files | **1059 as of the commit, 2026-11-04** (the round wrote 1058) |
| files resolving ≥1 declared ref | files | 438 |

**The 1058 was a carried figure and it was off by one** — derived before the commit, and the
commit itself put `.gitattributes` in the index. Re-derived at the merge gate with the same
instrument (`_in_domain_files`) against the committed tree: **1059**. Recorded dated rather
than bare, because this row is a count of the index and moves on every commit — the same
trap, in miniature, that the four bracketing population figures above are about. The 10 and
the 9/1/0 split were re-derived at the gate and reproduced **exactly**; so did 11, and the
11th is the `meta/kanban/dispatcher.state` ref in *Residual* below.

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

**Instrument** (which the round's own table did not name, and that is correction 4): the
resolver's batched argv, pattern for pattern — `git grep -ow` with one `-e` per name at
N=`BATCH_SIZE`=200 under its own `10.0 + 0.1 × N` = 30.0 s, which is what
`_batch_answers_within` in `tests/test_check_ref_resolution.py` runs. Re-run with **one
directory withheld at a time**. Stated as the ORDERING it establishes and not as elapsed
seconds, for the reason `_batch_answers_within`'s own docstring gives: *"a wall-clock figure
measures this machine's queue as much as the search, and a stored one would be a number the
next reader cannot reproduce."* The round was right about that and then stored five of them.

| N=200, budget 30.0 s, one directory withheld | where it lands |
|---|---|
| full in-domain corpus | **several times over budget** |
| minus `meta/profiling/*.txt` | **inside budget by two orders of magnitude** |
| minus `meta/review/` (396 files) | still over budget — indistinguishable from the full corpus |
| minus `scratchpad/` | still over budget |
| minus all three | inside budget |
| **full corpus, `meta/profiling/*.txt` marked `binary`** | **inside budget by more than an order of magnitude** |

**THE DUMPS ARE THE WHOLE COST; THE REVIEW YAMLS ARE INSIDE THE NOISE.** That ordering is
the durable result, and it is why the five figures had to go: **on re-measurement one of
them inverts.** The round read `minus meta/review` as *faster* than the full corpus (115.41
< 117.38), i.e. the review YAMLs costing ~2 %; cycle 1 read it *slower* (140.12 > 138.19),
i.e. costing nothing at all. A quantity whose sign is not stable is not a 2 % contribution
— it is noise, and the ordering is what both readings agree on.

**The card's claim that the cliff "only exists because of `meta/review/` + `meta/profiling/`",
that they are "40 % of the domain's text lines" and that "harm A and harm B are one
population and one fix" is RETRACTED (ADR-0039/R4).** Varied one directory at a time, the
entire cost is the **10 machine-written `.txt` duration dumps**. Harm A is 9/10 under
`meta/review/` and harm B is 100 % under `meta/profiling/*.txt`: **two populations, two
fixes**, and the convergence argument the card calls "the headline for whoever takes this
card" does not hold.

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
board does not edit (G-4): the swallow (ADR-0038/R8), and — **corrected at the merge gate,
because the round said "sitting past the cliff" and there is no cliff** — the budget's
**shape**: `BATCH_TIMEOUT_BASE_S + BATCH_TIMEOUT_PER_NAME_S × N` is linear in N and the
cost is super-linear in it, so the two cross at some N for any constants and the crossing
moves with the corpus and the host. **Neither finding is "use a smaller `BATCH_SIZE`"** —
see correction 2.

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
* **Retiring the 396 review YAMLs is now carded as `CARD-362`** (`ready`, P2, 1c, depends
  on this card), priced at the 89 → 94 in correction 1. It exists because the work is an
  owner action on `main`, not because this card fell short.

---

## Review cycle 1 — corrections, folded in at the merge gate

Six corrections. Cycle 1 certified the card at **8.0** and **refuted two of the round's own
conclusions**; the gate re-derived the two figures that were the reviewer's rather than the
round's, and found one thing the review itself got wrong (correction 7, below). Every
figure here was measured against the committed tree `5448cf14` with the instrument named
beside it.

### Correction 1 — the round's F-8 conclusion is struck, and **AC-3 and G-5 stand as written**

F-8 claimed that un-reviving the 10 refs restores **ERRORs, not warnings**, and that this
"invalidates how this board has been reading its own validator output". **That conclusion
is false, and with it the round's declaration that an AC was unsatisfiable in kind.**

Re-derived at the gate, independently of cycle 1 and with **no tree mutation**: patch
`validators/utils.CodeSearch.exists` to answer `False` for exactly the 10 revived refs
(every consumer — `missing`, `unknown`, `is_dead` — routes through it), then run
`validate.run_phase(meta/architecture, "all")` against `5448cf14`.

| | errors | warnings |
|---|---|---|
| baseline (the 10 still revived) | 0 | **89** |
| the 10 reported dead | 0 | **94** |

**0 errors / 89 warnings → 0 errors / 94 warnings. Zero ERRORs appear.** WARN sets compared
with `comm` on `^[[:space:]]*\[WARN`, both sides asserted non-empty (89 and 94 unique
lines): **5 appeared, 0 disappeared.** The +5 are exactly cycle 1's:

* 3 **`DEAD check ref` WARNs** — `requirements.yml` FR-040/AC-252, FR-042/AC-291,
  FR-042/AC-292;
* 2 **partly-checked WARNs** — `domain/aggregates.yml` INV-011, INV-013.

A reading the gate adds: **10 refs produce 5 findings, not 10.** Seven of them are *bundled*
into those two aggregate messages (INV-011 names 6, INV-013 names 1), which is a second,
independent reason the ERROR count cannot move — the aggregate check reports per rule, not
per ref.

**The mechanism, confirmed on disk.** `trace.py`'s `_check_covered_tests` is scoped by name
and docstring to `status: covered` entries and begins each entry with
`if … entry.get("status") != "covered": continue`. The trace entry declaring **8 of the 10**
is `status: partial`; the remaining 2 are declared in `requirements.yml` only and have no
trace entry at all. So the walk skips them before it ever asks the resolver, and **the ERROR
channel never fires.**

**F-8's first half is verified and kept:** the 89-warning baseline contains **0**
`DEAD check ref`, **0** `dead link`, **0** `no definition was found` and **0** `existence
could not be determined`. The standing baseline has never held a dead-ref finding — which
is the real point F-8 was reaching for, and it survives without the false conclusion.

**The measured consequence of the repair is therefore: 89 → 94, +3 dead-ref WARNs, 0
errors.** That is the price `CARD-362` carries.

**That eight of ten produce no finding at all is a THIRD blind spot in the same detector,
independent of revival, and it is not this card's** — it is `CARD-361` (`ready`, P1, 2c):
22 refs with no definition anywhere produce no finding, because `trace.py` only asks the
resolver about `status: covered` entries. The reader who asks "why did CARD-335 not fix
that" is answered there.

### Correction 2 — there is no cliff, and no fixed `BATCH_SIZE` is safe

Folded in above, at *Two facts fall out* (item 1), at *The two fixes that WOULD work*, and
at *Is a blown batch loud now?*. The gate's own curve, full-text corpus, resolver's argv:
**N=50 1.8 s · 80 8.8 s · 100 17.5 s · 110 23.0 s · 120 30.3 s · 140 51.7 s · 160 65.6 s ·
200 109.3 s** — smooth, monotone, ≈N^3, no step. Two instruments: the branch worktree with
`git grep -a` forcing the `binary`-marked dumps back into the text scan, and the `main`
checkout which tracks no `.gitattributes` at all (N=100 17.53 / 18.04 s, N=120 30.33 /
30.55 s — agreement within 3 %, so `-a` is a faithful stand-in). Post-fix, same argv,
attribute in force: **N=200 in 1.0 s against 30 s.**

### Correction 3 — AC-4's reach bound, recorded in the cell's docstring

`test_no_new_artefact_file_is_force_added_into_the_resolver_domain` is deny-by-default over
**the ignore rules**, not over the resolver's domain. A tracked artefact whose path **no
ignore rule matches** never enters the census, so the cell stays green with no force-add
involved. Re-confirmed at the gate with `git check-ignore --no-index` against the committed
`.gitignore`: `meta/review/<CARD-NNN>/cycle1.yml` (**not** matched — `meta/review/*.yml` does
not cross a `/`, so a per-card subdirectory escapes it) and `meta/measurements/durations.txt`
(**not** matched — a new directory beside the two the rules name). Both take a plain
`git add`, rc 0, no warning. Both directories are flat today, so **there is no live hole**.

Recorded per **ADR-0039/R3** in the cell's docstring, with the **outcome-side backstop**
named: an artefact that actually revives an otherwise-undefined ref reds the pre-existing
**CARD-308** gate (`test_no_verifying_ref_is_resolved_only_by_pipeline_bookkeeping`)
whether or not its path was ever ignored. The new cell guards the cause for the paths the
convention covers; CARD-308's guards the effect for all of them. Docstring only — no code
change, and the census baselines are untouched.

### Correction 4 — the five wall-clock figures are gone from `.gitattributes`

Folded in above and in `.gitattributes` itself. The round's `_batch_answers_within`
docstring argues that a stored wall-clock figure "measures this machine's queue as much as
the search" and would be "a number the next reader cannot reproduce" — and the round then
committed five of them (117.38 / 0.55 / 115.41 / 123.30 / 1.10 s) with **no instrument
named**. Both files now state the **ordering** — *the dumps are the whole cost; the review
YAMLs are inside the noise* — and name the instrument. The reason it had to be an ordering
and not a correction to the numbers: **one of them inverts on re-measurement.** 115.41 <
117.38 makes `meta/review` cost 2 %; cycle 1's 140.12 > 138.19 makes it cost nothing. A
contribution whose **sign** is unstable is noise, and the ordering is what every reading
agrees on.

### Correction 5 — a carried figure, off by one

*the resolver's whole domain* read **1058**; it is **1059** against the committed tree,
because the commit itself added `.gitattributes` to the index. Re-derived at the gate with
`_in_domain_files`. Corrected and **dated** in the table above rather than left bare.

### Correction 6 — the worktree's card copy, overwritten from `main`

The uncommitted copy in `/Users/omelnikova/PycharmProjects/PythonProject4-card-335` carried
the **CARD-341 defect** (the `.gitattributes` explanation inline on `Touches`, so
`parse_card_fields` returned **8** entries instead of 6) and had `Branch`, `Worktree` and
`Started` all at `—`. It was overwritten byte-for-byte from `main`'s copy before the merge
and verified identical by `diff`, and `Touches` now parses at **6**. So no later sync can
push the defective version back over the stamped one.

### Finding 7 — for the next wave: a tracked `scratchpad/` probe now needs `git add -f`

`scratchpad/` is ignored from this card forward, so a probe that must be tracked is a
deliberate `git add -f` and **reds the force-add census at 477 → 478** — which is the guard
working, not a defect. Tracked `scratchpad/` commits are live practice on this board, so the
next card that commits a probe will meet this.

**The determinant is the RULE SHAPE, not the `git add` form — and that reconciles cycle 1's
reading with the gate's, which flatly contradicted each other.** Cycle 1's F-10 records that
`git add <dir>/` "and `git add -A` both rc 0 **AND SILENTLY ADD NOTHING**". The gate measured
`git add scratchpad/` at **rc 1, loud, naming `-f`**. Both are correct, of **different
rules**, and this card ships both shapes:

| `git add` form | `scratchpad/` — a **directory** rule | `meta/review/*.yml`, `meta/profiling/*.txt` — **glob-inside** rules |
|---|---|---|
| explicit file path | **rc 1, loud**, names `-f` | **rc 1, loud**, names `-f` |
| shell-expanded glob | **rc 1, loud**, names `-f` | **rc 1, loud**, names `-f` |
| `<dir>/` | **rc 1, loud**, names `-f` | **rc 0, SILENT** |
| `-A` | rc 0, silent | rc 0, silent |
| `-f <path>` | rc 0, adds it — the deliberate act the convention wants | same |

**Nothing is staged in any cell but the last.** The mechanism: naming `scratchpad/` names a
path the rules match, so git refuses the pathspec; naming `meta/review/` names a path they do
**not** match, so git walks in and skips the ignored files without comment. Measured with
real `git add` in a throwaway repository carrying this card's own three rules verbatim (git
2.50.1), cross-checked with `git add -n` in the card worktree.

**Why this matters for the brief it hands the next wave:** cycle 1's flat claim is true for
two of the three populations and **false for the one its own finding is about**. A next card
told "the directory form is silent" would expect silence from `git add scratchpad/` and get a
refusal — or, worse, read silence from `git add meta/review/` as success. The rule that
transfers: **for `scratchpad/`, every explicit form tells you; `git add -A` never does.** This
board's standing rule already forbids `-A`, which turns out to be the only way to lose a
`scratchpad/` probe silently.

The practice figure also needs its instrument, because the two obvious readings differ by a
factor of two — `git log --since="30 days ago" … -- scratchpad/` counts **39** commits that
*touched* the directory, while adding `--diff-filter=A` counts **19** that *added* a file to
it (121 files across those 19). Cycle 1's "19" is the add reading. Most recent either way:
today (`83728599`, CARD-336's own merge gate).

### Finding 8 — 16 of the 477 census entries are not artefacts at all

The force-add census baseline is **477**, and a reader must not mistake it for a measurement
of this card's subject. Re-derived at the gate from `git ls-files` through
`git check-ignore --no-index`:

| | files |
|---|---|
| `meta/review/*.yml` | 396 |
| `scratchpad/**` | 55 |
| `meta/profiling/*.txt` | 10 |
| **pre-existing non-artefact debt** | **16** — 4 `.DS_Store`, 6 `.idea/`, 6 `src/nonogram.egg-info/` |
| total | **477** |

461 + 16 = 477. Cycle 1 ruled the cell **is a guard and not a ratchet**, and the gate agrees
with the reasoning: the census counts **paths**, so `.DS_Store` churn and `pip install -e .`
move those files' *content* rather than the count, and a newly ignored file cannot enter the
index through `git add -A` at all (finding 7's table). The 16 are debt the convention's
absence accumulated, not this card's population, and no card owns them yet.
