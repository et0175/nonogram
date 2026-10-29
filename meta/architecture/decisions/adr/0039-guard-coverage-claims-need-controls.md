# ADR-0039: A test guard's coverage claim is only as wide as the control that can fail

**Status:** Accepted
**Date:** 2026-10-17
**Deciders:** Puzzle Creator (project owner)
**Revised:** 2026-10-28 (R4 added — the family's fourth measurement, on figures rather than guards)
**Migration:** on-touch
**Pattern:** —
**API-Posture:** —

## Context

CON-005 is the one mandatory-severity constraint in the model, and ADR-0014 answered it by
requiring an independent brute-force oracle for the solver's uniqueness verdict. That pattern —
a claim is worth what the thing that could refute it is worth — has since been applied far
beyond the solver: this project's test tree now carries structural guards that make assertions
about *themselves*, auditing the package for a second drawing site, for a test that reads the
owner's gitignored timing log, for a module that silences itself above its own guards.

Those guards have a recurring defect, and it has been measured rather than suspected. Across
three cards and ten review cycles — CARD-238 cycles 1–5, CARD-228 cycles 1–3, CARD-239
cycles 1–2 — nineteen gating findings reduce to one sentence: a guard's stated coverage was
wider than the mechanism that enforced it. Two of those cards escalated. The pattern is not a
property of any one component: it appeared in a timing-log audit, in a page-geometry guard, and
in a module-scope-silencing guard, written at different times for different subsystems.

The family has already been promoted once. On 2026-10-05 a wave-33 retrospective wrote it into
the kanban implementation brief as "a comment or docstring claim about what a test catches needs
a mutant proving it". It did not bite, and the wave-40/41 retrospective diagnosed why in two
parts: living in a brief, it carried no `check:`, so nothing executed it; and its wording was
satisfiable while the defect persisted, because a mutant *inside* a claimed region passes while
the claim's *scope* stays unbounded. The 2026-10-16 approval to promote it into the model with a
check was not executed, and wave 42 then paid for the family across its two most expensive cards.

Two further facts bound the solution space. First, waves 41 and 42 produced three successively
sharper statements of the family rather than one — the later ones are not restatements, and each
names a mechanism the earlier one permitted. Second, the discriminator for whether such a guard
converges has been observed twice *within single cards*: the halves whose sets derive from an
authority (`dir(os)` and friends; `dir(ImageDraw.ImageDraw)`) were sound from their first pass,
while the sibling halves in the same cards, over surfaces with no enumerable authority, took
three cycles and two. EC-001's discipline — a property needs something independent to check it
against — is the standing precedent, but it is stated for the solver and nowhere generalised.

## Decision

We adopt three standing rules of the model, R1–R3 below, each checked by a test that exists and
executes in this repository today, and each stating its own reach rather than implying
repo-wide enforcement.

Three rules rather than one clause-bearing rule, because the observed failure modes are distinct
and separately satisfiable: CARD-239 honoured the completeness discipline and broke the exemption
discipline in the same module, and a single rule would have carried one `check:` ref for three
mechanisms that no single test can fail for. Each rule's check points at a test the paying cards
built, so the family is enforced by the mechanism its own provenance produced — which is the one
thing the 2026-10-05 promotion lacked.

The rules' checks cover the guards that exist. They do not reach a guard written tomorrow, and
R1–R3 say so in their own comments instead of implying otherwise; new guards are reached by the
decompose lens (6c4) and `forge:review` Step 8h until they carry audits of their own. Overclaiming
the reach here would commit, inside the rule meant to prevent it, precisely the defect the rule
is about.

## Alternatives considered

### One rule with three clauses
A single statement requiring that a guard derive its set or default-deny, carry a completeness
test written before the set, give every member and exemption a control, and record residue as a
bound. Rejected on the mechanics of the collector and the lens rather than on the content, which
is the same: there is no single test in this repository that fails for all three clauses, so the
rule would have had to pick one ref and leave two mechanisms unchecked. It would also hand every
card touching `tests/**` all three clauses regardless of applicability, which is how the
2026-10-05 brief promotion became background noise rather than a constraint.

### Defer, and build a repo-wide guard audit first
A meta-test that walks `tests/**`, finds every guard consulting a set, and asserts each carries a
completeness test and a discriminating control — then one rule pointing at that audit. This is
the strongest available check and would reach guards nobody has written yet. Rejected as the
*first* step, not as an idea: it is a card's worth of work, and the family has cost a wave each
time it stayed unpromoted, including the wave in which this very promotion was already approved.
Recorded as follow-up work instead, with these rules in force meanwhile.

### Leave it in the implementation brief and strengthen the wording
The 2026-10-05 approach, with sharper language. Rejected because the diagnosis of its failure was
specific and is not a wording problem: a brief carries no `check:`, so nothing executes it, and no
amount of rewording gives a brief a failing test.

## Consequences

### Positive
- The family gains three executing checks where it previously had none. A regression in the
  discipline of the guards that taught it now fails a test run rather than waiting for a reviewer
  to notice it a fourth time.
- The authority test (R2) is cheap to apply before a guard is written and was validated twice
  within single cards, which is stronger evidence than a promoted rule usually carries at
  promotion time.
- R3 names the construct that both earlier statements of the family reached for as their honest
  escape hatch. An exemption now carries the same burden of proof as a set member, which is where
  CARD-239's two cycles went.
- The decompose lens can hand a card the rules its `Touches:` intersect, so a card editing
  `tests/**` inherits the family's cost as a constraint rather than re-learning it.

### Negative
- Three mandatory rules scoped to `tests/**` is three more standing rules the lens hands every
  card that touches the test tree, including cards for which they are formally applicable and
  practically irrelevant. The cost is real and is accepted in exchange for not paying the family's
  price a fourth time.
- The checks are specific tests, not a repo-wide audit, so a guard written tomorrow is covered by
  judgement rather than by mechanism until the deferred audit exists. This is stated in the rules
  and remains the honest limit of this decision.
- R2's default-deny prescription is not free: making the unparseable a failure reddens honest code
  that the guard cannot analyse, and each such site then needs an exemption with a reason — which
  R3 then makes answerable for its own control. The discipline is self-reinforcing and therefore
  not cheap to adopt in a new guard.

### Neutral
- Three check refs now exist in the trace surface and will appear in `--verify-refs` output; two
  live in `tests/test_suite_profile.py` and one in `tests/test_book_difficulty_dots.py`, so a
  rename in either file is a dead-ref diagnostic rather than a silent loss.
- `Migration: on-touch` — guards already in `tests/**` that predate these rules are brought into
  line when a card next touches them, not in a sweep. Existing guards that do follow the rules are
  their provenance and need nothing.
- A repo-wide guard audit is now recorded follow-up work; when it exists, these rules' checks
  should be re-pointed at it and their stated reach widened accordingly — which is itself an
  application of R1 to this ADR.

## References

- DEC-042 (resolved by this ADR)
- CTX-001 (the single bounded context; the rules are scoped to its test tree)
- CON-005 (uniqueness must never produce a false positive — the standing precedent for
  claim-versus-mechanism in this model)
- EC-001 (the property CON-005 is tested by, and the narrowest prior instance of this discipline)
- ADR-0014 (uniqueness correctness oracle — the same reasoning, stated for the solver only)
- Provenance: CARD-238 cycles 1–5, CARD-228 cycles 1–3, CARD-239 cycles 1–2; nineteen gating
  findings, two escalations. Retrospective sections: `meta/kanban/retro.md` "Waves 40–41" and
  "Wave 42".

## History

- 2026-10-17: Created — resolves DEC-042. Promotes a finding family measured across three cards
  and ten review cycles into three standing rules with executing checks. Supersedes, in substance,
  the 2026-10-05 promotion of the same family into the kanban implementation brief, which carried
  no check and whose wording was satisfiable while the defect persisted.
- 2026-10-28: **R4 added** — promotes the same family's fourth measurement, this time on
  **figures rather than guards**, from wave 62's retrospective. R1 already said the sentence
  (*"a claim whose control cannot fail is narrative, not coverage"*) and **did not bite**: of
  wave 62's 7 gating findings, 6 were this family and **4 lived outside R1–R3's scope** — two
  in `meta/profiling/**`, one in `meta/kanban/**`, one unfiled — while the three inside
  `tests/**` were prose claims about numbers, not a guard's coverage claim over a set. So the
  cause was scope **and** subject, and the remedy is a sibling rule rather than a duplicate or
  a third scope widening. Provenance: CARD-292 cycle 1 F-001/F-002, cycle 2 F-201/F-202;
  CARD-287 cycle 1 F-287-01/-02/-03.

## Scope revision — 2026-10-19

R1–R3 were authored with `code: ["tests/**"]`, on the reading that a guard is a test. Waves 46–47
measured otherwise: of the ten instances of this family, the ones that cost the most review cycles
were claims written in **source docstrings and comments** about what a test catches — `puzzle_edit.js`'s
header and `inFlightIs`, `app.py`'s and `puzzle_review.py`'s `Returns:` blocks — which `tests/**` does
not reach. That is also the reading this ADR's own Context records from the wave-33 promotion: *"a
comment or docstring claim about what a test catches needs a mutant proving it"*.

The three scopes therefore now read `["tests/**", "src/nonogram/**"]`. The statements are unchanged.

Separately and mechanically, the `contexts: [CTX-001]` key was removed from these and 28 other rule
scopes across the model on the same day. On a single-context project that key matched every card
before the `code:` glob was ever consulted (`system_rules.py`: the contexts branch short-circuits the
glob branch), so every precisely-scoped rule was behaving as package-wide. Removing it is what makes
the authored globs load-bearing — including these two.

## Promotion — 2026-10-28: the family's fourth measurement, on figures

The 2026-10-19 revision above widened R1–R3 from `tests/**` because waves 46–47 measured that
the costly instances were claims in **source docstrings**. Wave 62 is the same discovery one
layer out: the costly instances were **figures in artefacts**, and they were costly in a
specific way — they were not wrong about the code, they were wrong about *how they had been
measured*.

What it cost, measured rather than suspected. Two cards, six review cycles, **7 gating findings
of which 6 are this family**:

| finding | the claim | what it actually was |
|---|---|---|
| CARD-292 c1 F-001 | a host cell reported through `pgrep -fc` | **not a flag on this platform** — exit 2, and an *empty* cell inside `$(...)` |
| CARD-292 c2 F-201 | its replacement, `pgrep -f 'bin/python -m pytest'` | **blind** — reads 0 whether or not pytest runs, because the venv's framework python re-execs through `Python.app`; and false-*positive* on a wrapper naming it. Wrong in both directions |
| CARD-292 c2 F-202 | "the right counts" | right counts, **wrong domain** — all 108 analyses were over planted texts, none over the real module |
| CARD-287 c1 F-287-01 | `get_source_segment` "re-splits the **whole** source" | a **bounded prefix**, mean 81.1 % — and the claim sat **300 lines from its own retraction in the same file** |
| CARD-287 c1 F-287-02 | "predicted 15.04, measured 15.19 — **1.0 %**" | **two compensating errors**: an over-measuring instrument subtracted from a *superseded* baseline. Honest figure 6–8 % |
| CARD-287 c1 F-287-03 | the capture is "the guard's **entire** observable answer" | **seven axes missing**, and "ten configurations" was 12 calls of which 4 were captured in full |

Three further facts decided the rule's wording rather than being decoration:

- **An instrument that cannot rise is indistinguishable from a quiet box.** `pgrep -fc`'s
  successor reported `0` for an entire session and nobody could tell, because *every* reading was
  0 and the box genuinely was quiet. What closed it was a **truth table with both controls** —
  five cases including a `zsh -c` whose own argv merely *mentions* pytest — now carried in
  `meta/kanban/config.yml`. Hence R4's positive **and** negative control.
- **A ratio's halves can come from different instruments.** CARD-292's published 9.9× speed-up
  divided a *profiled* numerator by an *unprofiled* denominator; through one door it is 8.0×.
  CARD-287 then repeated the shape at smaller scale. Hence R4's domain clause.
- **Three stations quoted three points for one quantity.** Cycle 2 said 22.0 %, fix round 2 said
  21.2 %, cycle 3 measured 21.30 / 21.52 / 21.86 and established the honest answer is a **band**,
  21.2–22.0 %, because the denominator carries 5.5 % run-to-run spread. A point estimate for a
  quantity with that spread is the defect, not any one of the points.

**The second family stays unpromoted and is recorded here as the one to watch**: *a refuted figure
must be retracted everywhere it was written.* One gating instance (four docstrings carrying the
306 KB that the same round had struck out) plus CARD-287's reinstatement. R4's last sentence states
it, but it has not yet been paid for twice in two cards — if it recurs it earns its own rule rather
than a clause.

## The validator's own ref resolver is a control that cannot fail — 2026-10-29 (CARD-308)

R1 is about a *guard's* claim. This section records the same defect one level up, in the
instrument the whole model is read through, because the finding kept being re-derived and
because the repair is **not in this repository**.

**The mechanism.** `validators/utils.symbol_exists()` — the single technique every
"the model names test X, was it written?" question goes through — is

```
git grep -lw <ref> -- . ':(exclude)meta/architecture' ':(exclude)*.md'
```

Its docstring says `-w` resolves a name "to its `def test_x` definition". It does not;
`-w` only enforces word boundaries. So **a ref is alive as soon as its string appears in
tracked, non-Markdown content**, including content that merely discusses it. The claim
"this criterion is mechanically checked" therefore has no control that can fail in the one
way it matters: a ref that nothing implements reads identically to one that is implemented.

**The in-domain writers a resolver has to survive.** `meta/architecture/**` and every
`*.md` are excluded, so the registry cannot self-validate and `board.md` resolves nothing.
Everything else tracked is in domain, and these are all **mandatory pipeline bookkeeping**,
not anybody's mistake:

| writer | why it exists | measured |
|---|---|---|
| `meta/review/**` | the CARD SYNC PROTOCOL copies each cycle's report into the main repo one-way, because `/commit` excludes `meta/` from card branches and `forge:fix`/`forge:commit`/`forge:retrospective` read them | twice: a warning retired on the sync commit alone, test still absent |
| `meta/kanban/dispatcher.state` | the orchestrator's state log. **No `.md` extension, so unlike `board.md` it is inside the domain** | it became one of two load-bearing resolvers for a dead ref while recording this defect |
| `meta/kanban/backlog-scored.yml` | scoring bookkeeping | resolves **6** model refs, **4** of them with no definition anywhere — a broader kanban-side resolver than the state log |
| `meta/kanban/waves.yml` | wave bookkeeping | resolves **3** model refs, **1** of them undefined; sole resolver for none. The **fifth** kanban-side resolver, and listed without a figure until review cycle 1 asked for one — an unmeasured row in this table is the same phantom as an unmeasured check ref |
| `meta/profiling/*.txt` | duration logs, which name every node id that ran | sole resolver for exactly **1** ref |
| prose inside `tests/` itself | comments and docstrings naming the test a module is about | ADR-0006/R1's ref: **zero definitions anywhere**, resolved by **110** files (109 at the cut — one more synced review report since), two of them a comment and a docstring under `tests/` |

**Author discipline is not available as the remedy.** CARD-291's cycle-1 reviewer knew the
hazard, wrote one ref into its YAML split across two pieces so the report would not revive
it, and verified the split worked. It made no difference: a review report's most-quoted
refs are its own card's, and on `main` those were the dead ones. A rule that depends on a
report being written carefully is not a control.

**Why `:(exclude)meta/review` is NOT the repair.** It is the obvious narrowing and it is
insufficient in two independent ways. First, it addresses one writer of five — the same
erosion arrives from `meta/profiling/**`, from `dispatcher.state` and from
`backlog-scored.yml`. Second and decisively, **`tests/` cannot be excluded**: it is the
only directory the search *must* look in, and it is also a place refs are named in prose.
ADR-0006/R1 is the limit case, and CARD-301's is the sharpest: `BenchGenerate_20x20_p95Under5s`
read as ALIVE on nothing but a docstring line and a `# AC-037 —` banner inside the very
file that could not run. No pathspec can separate "defines the test" from "mentions the
test", because that is not a property of the path. **Only a definition-based resolver can**:
the hit must be a `def`/`class` line, and for a `path::name` ref the `def` must be in that
path. That change belongs in `forge_1`'s `validators/utils.py` and is out of this
repository's scope; recording the argument here is what stops the pathspec narrowing being
proposed a third time.

**What this repository has instead, and what it is not.** `tests/test_check_ref_resolution.py`
re-implements the loose resolver strictly and reports every ref on which the two disagree,
in both directions, with its set derived from `requirements.yml`, `trace.yml` and the ADR
set at run time. It is a **DETECTOR, not a repair**: it changes nothing about what the
validator reports, and a green suite does not mean the model's refs resolve honestly — it
means the population of dishonest ones has not moved without being read. Its own
`test_this_module_resolves_no_verifying_ref_at_all` exists because a guard that lists dead
refs spells them into tracked non-Markdown code and revives them; on its first run that
test named three refs the module's own docstring had revived.

**The census is 580, and here is how it is derived** — *with the tree named, because it
moves*. Three different figures were quoted for it inside one card and each was wrong in a
way worth recording, and a fourth row in this very table was left unmeasured.

Every row below is re-derived at `card/308` after `main` was merged in (the figures at the
cut `f64112f2` are in brackets where they differ):

| source | distinct refs | decomposition |
|---|---|---|
| `trace.yml` `tests:` lists (block form and inline) | **510** | 64 block-form keys + 11 inline |
| `requirements.yml` `test:` keys and block-form `check:` refs | **404** | 401 distinct from 421 `test:` keys, 10 from 11 block-form `check:` blocks (the 11th is not kind `test`), **7 refs declared by both** — so 401 + 10 is 411 *mentions* and 404 distinct |
| ADR inline `check: {kind: test, ref: …}` | **44** [43] | **45** [44] occurrences, **47** [46] ref-mentions (one occurrence declares two comma-separated refs; one ref is declared 3× and one 2×) |
| **union, de-duplicated across authorities** | **580** [579] | |

The `requirements.yml` row was an em-dash until review cycle 2 asked for it, two lines below
the row that condemns unmeasured rows; and the figure first offered for it, "404 (401 `test:`
keys + 10 block-form `check:`)", does not add up on its face. The reconciliation is the
overlap: 7 refs are declared by both forms. A decomposition that does not sum is an
invitation to re-measure, which is the opposite of what a table is for.

The three wrong figures, and the one coincidence worth naming. **576** came from a forward
scan of `trace.yml` that stopped at the first non-`- item` line, so a `#` comment *inside*
three `tests:` lists truncated each one — 494 refs instead of 510, 16 dropped silently with
no exception, 3 of them declared nowhere else. **510** is right but is only one authority.
And **580** was, at the cut, an *erroneous* census: it came from counting the ADRs' 44
`check:` occurrences as 44 refs when one is declared three times and one twice
(579 − 43 + 44 = 580). It is now the *correct* census, because `main` declared one genuinely
new ref — defined at `tests/test_book_pdf.py:1797`, re-derived against that `def`. A figure
that is wrong on one tree and right on the next is the strongest argument this ADR has for
naming the tree beside the number.

The lesson is the smaller, duller one: a census is only as good as an **independent** reading
of the same file, which is why `trace.yml`'s contribution is derived twice by two different
algorithms — a forward scan that classifies every line it meets, and a backward scan from
each list item to its owning key — and the two are asserted equal.

**And a cross-reading is not a default-deny — review cycle 2 measured the difference and it
is the sharper half of R2.** The forward scan raises on a *line inside a list* it cannot
classify. It did **not** raise on a `tests:` **key** whose shape it could not read: a
multi-line flow sequence, a block scalar, a plain scalar, a comment after the key, a trailing
comment on an inline list, an anchor. Those six fell through the dispatch and contributed
nothing, and **two of them are invisible to the backward reading as well**, because both
readings assume a ref lives either in a flow sequence or in a block sequence of `- item`
lines. So the two readings agreed at 510 and both were wrong, every pinned count stayed
green, and the detector's own G-2 self-check — a trie built *from* the derived set — reported
CLEAN on a text spelling the missed ref in full. Two readings of the same assumption cannot
close that class; only refusing the key can. The derivation now default-denies on the
declaration **key** across all four authorities: a `test:`/`tests:`/`check:` key no pattern
claims is a FAILURE naming the file, line and text.

Two things that repair taught, both measured and both worth a line here because they are
general:

* **A default-deny needs a notion of where a declaration can live, or it reds on English.**
  All 68 anchored `check:` lines in the ADR set are inside a ``` fence; exactly one
  declaration-key-looking line is outside one, and it is prose —
  `0042-book-interior-is-vector-cover-stays-raster.md:153` wraps a sentence onto a line
  beginning *"tests: its 0.48/1.28/2.08 pt are the owner's figures"*. The same holds for block
  scalars in the YAML authorities (152 in `requirements.yml`, 69 in `trace.yml`, 2309 body
  lines, 0 of them declaration-key-shaped today). So the region is part of the rule.
* **The opposite failure exists and is worse for a census.** Before the regions were shared
  between the two halves, the narrow `test:` pattern still matched every line in the file and
  **collected a wrapped prose line inside a `rationale: >-` block as a ref**. A guard that
  invents a ref out of prose corrupts the census in the direction nothing else here checks.
  It was found by a synthetic authority set in the new control, not by reading the code.

**And a region notion is only worth its edges — review cycle 3 measured four shapes off them,
two of which fail silently.** Once both halves of the derivation rest on one region, the
region's own *totality* becomes the load-bearing property, and it was not total. A
block-scalar opener carrying a trailing YAML comment (`rationale: >- # a note`, legal YAML)
was not recognised as an opener, so a body line beginning `test: ` whose text is a valid
identifier was **collected as a declared ref** — the invent-a-ref failure above, reproduced
one notch out, and structurally outside the default-deny's reach: that refusal fires only
where no narrow pattern claims, and invention happens exactly where one does, so the repair
has to be in the region and cannot be in the refusal. A `~~~` fence was not a fence, so the
ADR refusal was **silently skipped** inside one (no ref is dropped there — ADR collection is
document-wide — so it loses the refusal, not a ref). A **quoted** declaration key
(`"tests": [X]`) matched neither the loose key pattern nor any narrow one, so it was invisible
to collection *and* to refusal. And an **unclosed** fence flipped the region for the whole
remainder of a document, which turns the one live out-of-fence prose line above into a
candidate and reds the guard on English. All four were measured **latent** on the real
authorities — 0 commented openers in either YAML authority or the ADR set, 0 `~~~` fences,
0 quoted declaration keys, every ADR's fence parity even and all 46 fence lines exactly three
backticks — and latency was the *only* thing holding them, because nothing asserted any of
those four invariants. Each is now classified or raising with its own row in the control's
matrix, and an unclosed fence is refused **by the fence** rather than by the innocent
sentence. The general rule, which belongs to R2 and not to this card: when a default-deny and
its collector are made to share a region, the region's edges inherit the entire rule, so every
edge needs a control that can fail.

**A sub-shape of the `tests/`-prose limit case that nothing on this board had named.** A guard
written to assert that some tests do **not** exist yet, holding their names as string
literals, would — if the model declared those refs in **bare** form — make the validator read
all three as checked. A test that tracks not-yet-written tests, silencing the warnings it
tracks, is the most self-defeating member of this family. It is **not** operative on this
board: the refs in question (FR-045's) are declared as node ids, and `git grep -lw` on a
`path::name` pattern cannot match a bare name — measured per ref, with the resolver's own
query. That is an argument **for** the node-id migration, and it is recorded here because the
next bare-form declaration re-opens it.

**`dead ref` and `untested rule` are different findings, and this board has been conflating
them in the worst possible direction.** ADR-0006/R1's ref
(`TestDependencyBaseline_IsExactlyPillowAndNumpy`) has zero definitions and **110** resolvers
(109 at the cut, and climbing with each synced report), so
it is the limit case above and the pointer is genuinely dead. **The rule it points at is
nevertheless tested.** `tests/test_export_pdf.py:1249` asserts the whole runtime dependency
list equals `{"pillow", "numpy"}`, and its own docstring says *"ADR-0006's revision is what
makes this the **rule's** check and not just one card's guardrail."* The ADR does name that
test — in a `#` comment inside `meta/architecture/**`, which `code_search` excludes, so the
validator cannot see it and reports the ref as dead.

So the defect is a **phantom pointer, not an unverified dependency baseline**, and every
earlier framing on this board — including the card that cut this work — implied the baseline
itself was unchecked. It is not, and the overstatement is the more dangerous error of the
two: it invites a card to go "verify" a rule that has a passing exact-equality assertion,
and it inflates the cost of a one-line repair. A detector in this family must therefore
report *"the model's pointer does not resolve to a definition"* and must not be read as
*"this rule is unchecked"* — a distinction the detector's own docstring now carries under
"What a report here does NOT claim". The one-line pointer repair belongs to CARD-307.

**Two figures that only mean something with a binary attached.** The validator of record
is `forge_1`'s `validate.py --root meta/architecture --phase all`; the forge plugin cache's
copy reports a spurious `[ERROR] ADR-0025 circular supersession` because its
`adr_integrity.py` counts "supersedes" and "superseded by" as two edges. `validate.py` is
byte-identical between the copies. Measured on `card/308` with `main` merged in, 2026-10-29:
**forge_1 — 0 errors, 100 warnings** (23 of them "no definition was found" dead-ref
warnings); the plugin cache's copy adds its one spurious error and agrees on the warnings.
The honest error count is 0. The figure was **102** earlier the same day on the same branch
before `main` was merged, and the 2 that went are the FR-045 pair above — so even this row is
a measurement of the defect and not just a reading of the instrument. A warning count
without both a binary **and** a tree is not a figure.

**Interaction with CARD-307, with the figure CARD-307 needs corrected.** CARD-307 repairs
the `path::nodeid` refs so they resolve; this section and its detector stop the resolution
from being eroded afterwards. Neither closes the hole alone: a repaired ref can still be
silenced by the next sync, and an un-eroded detector still reports refs nobody has
repaired.

CARD-307's headline — "30 of them read as mechanically checked, and the validator cannot
resolve any of them" — **is stale on `main`**, and the correction matters because it is the
card's scope. Derived 2026-10-29 over the 23 distinct `path::nodeid` check refs the model
carries (`requirements.yml` `test:` keys and block-form `check:`, `trace.yml` `tests:`
lists, ADR inline `check:`), forge_1 validator agreeing:

| | at the cut `f64112f2` | at HEAD, `main` merged in |
|---|---|---|
| loose-alive **and** defined in the named module | 20 | 20 |
| loose-alive, **no** definition anywhere (falsely alive) | 1 — FR-045/AC-392's | **3** |
| loose-dead and absent (the honest state, the only ones the validator flags) | 2 | **0** |

The docstring node-id tables that CARD-284, CARD-291 and CARD-294 landed are why 20 of 23
resolve. So the validator reported exactly **2** dead node-id refs, not 30.

**And then it reported none, without anything being repaired.** The two honest-dead node-id
refs at the cut were FR-045/AC-390's and AC-391's. On `main` each has exactly **one**
resolver — `meta/review/20261029T130000Z-CARD-285-cycle1.yml`, a synced cycle-1 review
report — and still no `def` or `class` anywhere, measured with `git grep` against both trees.
The validator's warning count fell from 102 to 100 for precisely those two. Nothing was
written; the board simply stopped being able to see them. That is this ADR's mechanism
firing on live data *while the card documenting it was in flight*, and the detector caught it
by reddening five of its pinned classes, which is why the last column exists.

**A third shape this turned up, and it is the one CARD-307 should actually be scoped on.**
Four node-id refs are defined in the module they name while that module does **not** spell
the `path::name` string — so the loose resolution rests entirely on files that are about a
card rather than about the code. Three of them are `tests/test_player_bundle.py`'s, a
module that spells **zero** of its own node ids (against 7, 6 and 5 for the three modules
that carry a table). **Two** of those three are resolved by **exactly two CARD-218 review
YAMLs and nothing else**: the tests exist and pass, and pruning two files under
`meta/review/` would turn both refs DEAD without a line of code changing. The third is
additionally named by `tests/test_public_player.py`'s table, so another module's shim is
carrying it — a first draft of this section said all three were review-only and the
detector's own assertion refuted it, which is R1 landing on this card's work. The fourth,
ADR-0042/R4's
`tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`, has **58**
resolvers — 52 `meta/review`, 4 `meta/profiling`, 1 `meta/kanban/backlog-scored.yml`, and
one `tests/` file that is *not* the module holding its `def`
(`tests/test_admin_serving.py`). It was 57 at the cut; the extra one is a review report
synced in since, which is this row measuring the mechanism rather than just illustrating it. Its definition is real
(`tests/test_export_pdf.py:1249`); none of the 57 is that definition.

The repair is the existing precedent: a docstring node-id table in
`tests/test_player_bundle.py`, held to the registry in both directions, as
`tests/test_public_player.py` and `tests/test_approval_guess_gate.py` already do. That is a
**shim with a control**, which is why the detector does not flag those 16 refs and does
pin them: a shim whose table can silently drift is a resolver, a shim whose table is
asserted against the registry is a declaration.

## Rules

```yaml
- id: ADR-0039/R1
  statement: >-
    A set a guard consults needs a completeness test written before the set, and
    any claim the guard makes about what it catches needs a control that can fail:
    caught WITH the set member present, missed WITHOUT it. A claim whose control
    cannot fail is narrative, not coverage, and must be narrowed to what is
    measured or deleted.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_control_for_each_spelling_depends_on_the_set}
  # tests/test_suite_profile.py — the CARD-238 artefact this rule generalises: a
  # control must be caught WITH its set member and missed WITHOUT it, which is a
  # guard on the guards' discriminating power. REACH, stated rather than implied:
  # this ref executes and fails if THAT guard's discipline regresses; it does not
  # reach a guard written tomorrow. New guards are reached by the decompose lens
  # (6c4) and forge:review Step 8h until the deferred repo-wide guard audit exists.
  severity: mandatory
- id: ADR-0039/R2
  statement: >-
    A guard's set is derived from an authority the runtime can enumerate, not
    hand-written. Where no such authority exists, the guard defaults to deny:
    a shape it cannot analyse is a FAILURE, never a silent pass, and the
    unanalysable sites become named exemptions under ADR-0039/R3.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_guard_sets_are_derived_and_not_hand_written}
  # tests/test_suite_profile.py. The discriminator was observed twice WITHIN single
  # cards: halves deriving from dir(os)/dir(ImageDraw.ImageDraw) were sound from the
  # first pass, while sibling halves over surfaces with no enumerable authority took
  # three cycles and two. A completeness test over a hand-enumerated set of syntactic
  # shapes is not a completeness test, because no authority enumerates the shapes.
  # Same stated reach as R1.
  severity: mandatory
- id: ADR-0039/R3
  statement: >-
    An exemption is a claim. Every exemption a guard grants carries a control for
    what it must NOT absorb — caught with the exemption removed, missed with it in
    place — is held to an equality against the sites that exist today, and records
    whatever it still cannot see as a measured bound with its own failing control.
  scope: {code: ["tests/**", "src/nonogram/**"]}
  check: {kind: test, ref: test_the_dingbat_exemption_is_only_for_a_module_that_cannot_draw}
  # tests/test_book_difficulty_dots.py — an equality against the modules that carry
  # the codepoint today, plus a second assertion that the exempt module cannot draw,
  # so the exemption can neither grow to cover a drawing module nor outlive its
  # reason. CARD-239 cycle 2 is the counter-example this rule exists for: the fix for
  # a too-narrow predicate added an exemption that re-opened the same route one hoist
  # later, and its controls tested only what it exempted. Same stated reach as R1.
  severity: mandatory
- id: ADR-0039/R4
  statement: >-
    A figure is a claim, and the instrument that produced it is part of it. Every
    figure committed to code, to a card or to an artefact names its instrument, and
    that instrument must be executable on the host that recorded the figure and
    demonstrated to respond to what it measures: a POSITIVE control that it rises,
    and a NEGATIVE control that it does not rise on a near-miss. A reading that
    cannot distinguish "the quantity is zero" from "the instrument is blind" is not
    a measurement. A figure's DOMAIN — which population, which revision, which arm —
    is part of the figure; a ratio whose halves come from different instruments,
    different runs or different baselines is not a ratio. A figure recomputed and
    refuted is retracted everywhere it was written.
  scope: {code: ["tests/**", "src/nonogram/**", "meta/profiling/**", "meta/kanban/**"]}
  check: {kind: review-lens}
  # NO EXECUTING CHECK TODAY, stated rather than implied: nothing in the tree can
  # decide whether a committed number names a live instrument, so a test ref here
  # would read as mechanically checked while checking nothing. The lens carries it
  # (decompose 6c4 writes it into a card's System contract; forge:review Step 8h
  # holds the diff to it) and **CARD-304 owes the flip** to an executing check over
  # the artefact directories. The scope is WIDER than R1–R3 on purpose: wave 62
  # measured 4 of its 7 gating findings OUTSIDE `tests/**` + `src/nonogram/**`.
  severity: mandatory
```
