# CARD-317: Six check refs name tests that exist under other names — and the dead ref on FR-001 has been hiding a grid bound the code abandoned

**Status:** in_progress
**Priority:** P1
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** moderate
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** `card/317-check-refs-and-the-grid-bound`
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-317
**Source:** CARD-307's fourth premise re-measurement, 2026-10-29. CARD-307 was cut; this is one of its four successors, and the only one with a live defect behind it. Cut by the orchestrator on owner decision.
**Idea:** —
**Wave:** 71 <!-- STAMPED 2026-10-31 at dispatch. Opens the requirements chain's second link now that CARD-318 has merged and released meta/architecture/requirements.yml. CARD-316 serializes BEHIND this card on that same file (overlap 1.00 of its single entry). -->
**Created wave:** 66
**Deferred waves:** 0
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/decisions/adr/0001-generation-time-thresholds.md, meta/architecture/decisions/adr/0006-dependency-baseline.md, meta/architecture/trace.yml, meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md <!-- ADDED fix round 1: ADR-0042/R4 declared the identical node id F-001 retires from ADR-0006/R1, and was that string's only other declaration -- see the fix-round-1 notes for why splitting it off would have made the repair unprovable. -->
**Review score:** —
**Started:** 2026-10-31T02:39:21+00:00
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists, and why it is not bookkeeping

Six check refs name tests that **do not exist under that name but do exist under
another**. Re-pointing them is clerical. **What makes this a P1 is what the clerical
work uncovers.**

### The defect: FR-001 still describes a 50x50 maximum the code abandoned

`requirements.yml` AC-001–AC-004 name four class-style tests that have no definition
anywhere. The behaviour is fully covered — by **function-style** tests in
`tests/test_sourcing_random.py`:

| AC | `requirements.yml` says | the test that actually covers it |
|---|---|---|
| AC-001 `:288` | a 20x20 grid is produced | `test_generate_random_produces_requested_dimensions` |
| AC-002 `:294` | **a 50x50 grid is produced without error** | `test_generate_random_accepts_max_side_30` |
| AC-003 `:300` | **rejects size above 50** | `test_generate_random_rejects_side_above_30` |
| AC-004 `:306` | rejects size below 10 | `test_generate_random_rejects_side_below_10` |

**AC-002 and AC-003 say 50. The code says 30.**
`tests/test_sourcing_random.py:107` asserts `random_grid.MAX_SIZE == 30` outright, and
`CLAUDE.md` instructs the reader to use `limits.py` *"instead of writing 10 or 30"*.
**ADR-0001 also still says "the 50x50 maximum"** in its reaffirmation paragraph.

So the model says 50 in two places and the code says 30, **and the dead check ref is
what let that sit.** A live ref would have pointed at a test asserting 30, and the
contradiction would have surfaced the first time anyone opened it. This is the
concrete answer to the question CARD-307 was reaching for — *what does a dead
`kind: test` ref actually cost?* It costs this.

**This card does not decide which number is right.** That is an architectural
question: either the supported range narrowed to 30 and the model is stale, or 50 is
still intended and the implementation regressed. The card's job is to **surface the
contradiction, record the decision, and leave the registry agreeing with exactly one
of them.** If the answer is "50 was never delivered", the honest outcome is an AC
whose `then` says 30 and an ADR-0001 amendment saying when and why it moved — not a
quiet edit of the number.

### The other two, and the ADR pointer

- **AC-268 / AC-269** (`:4047`, `:4056`) name `TestBookAnswerKey_CaptionPuzzleNumberAndTitle`
  and `..._CaptionUsesCustomBookTitle`. The family exists —
  `TestBookAnswerKey_CaptionSeparatorIsADrawnGlyph` and eight siblings in
  `tests/test_book_answer_key.py` — but neither of these two does. AC-269 already
  carries `# REWORDED 2026-09-22`. **These may be re-pointable or may be genuine
  gaps; the card must determine which and say so**, not assume the family's existence
  means coverage.
- **ADR-0006/R1's pointer.** Its check ref `TestDependencyBaseline_IsExactlyPillowAndNumpy`
  has **zero definitions**, while the rule itself **is** tested — at
  `tests/test_export_pdf.py:1249`, which pins the whole runtime list. This is a
  phantom pointer, not an unverified rule, and **every earlier framing on this board
  overstated it**. Twelve cards carry a hand-written `**DEAD REF**` note about it.
  Re-point it to the real test and the twelve notes become true.
  **Measured subtlety worth knowing before you start:** the phantom name is
  *text-present* in two tracked test files, so it raises no warning and would resolve
  falsely even if ADR rule refs were checked — which they are not (see CARD-319).

## What to implement

1. **Derive the set.** Walk `requirements.yml` and the ADR `check:` entries for refs
   whose named symbol has no `class`/`def` in `tests/`, and for each, search for a
   test covering the same behaviour under another name. **Per ADR-0039/R2, a ref the
   walk cannot classify is a FAILURE**, not a silent skip.
2. **Re-point the four FR-001 refs** to the function-style tests that cover them.
3. **Surface the 50-vs-30 contradiction as a decision**, not an edit. Record it where
   a reader meets it: the AC text, ADR-0001, and a line in this card saying which way
   it went and why. Reconcile `requirements.yml` and ADR-0001 so they agree with each
   other **and** with `limits.py`.
4. **Resolve AC-268/269** — re-point if a covering test exists, demote with a reason
   if not. Per ADR-0039 a demotion is a success here.
5. **Re-point ADR-0006/R1** to `tests/test_export_pdf.py:1249`'s test, and state in
   the ADR that the rule is verified by substance there.
6. **Do not leave the twelve cards' notes stale.** They are prose in `.md` files and
   still navigable, but once the pointer is live, say so in **one** place — this
   card's worktree notes — rather than editing twelve live cards.

## Acceptance criteria

- **AC-1** (the re-pointing is derived, not hand-listed): *Given* the registry,
  *then* every re-pointed ref is produced by a walk that resolves definitions from
  `tests/`, and an unclassifiable ref fails the walk.
- **AC-2** (every re-pointed ref resolves to a definition): *Given* the branch,
  *then* each named test has a real `def`/`class` in the file the ref names — asserted
  **by definition, not by text presence**, so a mention cannot satisfy it. This is the
  distinction the whole CARD-307 family exists to draw.
- **AC-3** (the bound agrees everywhere): *Given* the branch, *then*
  `requirements.yml`'s FR-001 criteria, ADR-0001's text and `limits.MAX_SIZE` state
  **the same number**, and a test asserts the registry's number equals the constant —
  so the two cannot drift apart again silently.
- **AC-4** (the decision is recorded with its alternative): *Given* the card and
  ADR-0001, *then* the chosen bound is stated **with why the other was not**, and with
  the date the divergence is believed to have started if that is recoverable.
- **AC-5** (AC-268/269 are honest): *Given* the branch, *then* each is either pointed
  at a test that exists or demoted to `review-lens` with a recorded reason, and
  neither remains `kind: test` with no definition.
- **AC-6** (the count moves only downward): *Given* `main` and the branch, *then* the
  validator of record reports **six fewer dead-ref warnings** and **no warning of any
  kind added** — warning **sets** diffed line by line, not counts compared.

## Guardrails

- **G-1: do not silently change the bound.** Editing `50` to `30` without recording
  the decision converts a visible contradiction into an invisible one. The ADR is the
  place; a commit message is not.
- **G-2: do not write a new test for behaviour already covered.** Four of these are
  re-pointing jobs. A duplicate test is a second thing to keep in sync.
- **G-3: resolve refs by DEFINITION, never by `git grep -lw`.** A text search is what
  made this population invisible. Use `git grep -nE '^[[:space:]]*(async )?def NAME\('`
  or `class NAME[(:]`, and `--collect-only` to confirm the node collects.
  **`\b` is undefined in POSIX ERE and silently matches nothing** — an instrument
  using it returns empty and reads as a clean verdict. Prove any instrument in both
  directions (finds a known name, rejects a nonsense one) before trusting it.
- **G-4: no test deleted, renamed, skipped or merged** — `parametrize` ids included.
  (**gate**: node-id set difference with `-o addopts=''`.)
- **G-5: do not compare this branch's warning count to main's without holding the
  review YAMLs equal** — `meta/review/**` is inside the validator's ref-resolution
  domain. Swap the files inside one worktree. **And do not validate a `git archive`
  copy**: no `.git` means staleness and drift checks fall silent (77 against 102).
- **G-6: name the validator binary beside every figure** — the `forge_1` copy named
  in `meta/kanban/config.yml`, not the plugin cache, whose phantom
  `[ERROR] ADR-0025 circular supersession` is a regex bug.
- **G-7: do not touch FR-029's refs.** Those are **CARD-318's** and are a genuine
  coverage gap, not a re-pointing job.

## System contract (subset — the pipeline re-derives the full list at dispatch)

- ADR-0039/R1 — a claim needs a control that CAN fail. **`check: {kind: test}`**,
  not `review-lens` as this list said at dispatch: the model declares
  `test_the_control_for_each_spelling_depends_on_the_set`, whose `def` is at
  `tests/test_suite_profile.py:4127` and which resolves. Corrected in fix round 1
  (review cycle 1) — a check ref must be honest about whether it is mechanically
  checked, in both directions, and calling a live test a lens is the same defect
  as calling a lens a test.
- ADR-0039/R2 — a guard's set is derived from an enumerable authority; an
  unanalysable shape is a FAILURE. **`check: {kind: test}`** likewise:
  `test_the_guard_sets_are_derived_and_not_hand_written`, `def` at
  `tests/test_suite_profile.py:4215`, resolves.
- ADR-0001 — the generation-time thresholds and the supported grid range (check: **this card's subject** — the ADR's own text is one side of the contradiction)
- ADR-0006/R1 — the dependency baseline (check: **this card re-points the pointer**; the RULE is tested at `tests/test_export_pdf.py:1249`)

## Architecture context

- **ADR:** ADR-0001 (the bound), ADR-0006/R1 (the pointer), ADR-0039/R2 (derivation)
- **Components:** `src/nonogram/limits.py` is the authority the registry must agree
  with; no `src/` change is expected unless the decision goes the other way.
- **Trace:** FR-001's row is re-stamped once its ACs name live tests; FR-042's row is
  re-read after AC-268/269 resolve.

## Worktree notes

### Which way the bound went, and that this card did not decide it

**The bound is 30.** It was decided on **2026-08-30** by the owner
(raw-requirements.md lines 83-88, US-016) and formalized the same day as
CON-011 / FR-019 / INV-004, with AC-038 superseded by AC-084.
`src/nonogram/limits.py` has read `MAX_SIZE = 30` for as long as this
repository's history goes back. **This card decided nothing**: it found the
decision already made and recorded, and reconciled the one artefact that had
never been told — ADR-0001, last revised 2026-08-28, two days before.

ADR-0001's new History entry states the chosen bound, both alternatives not
taken (restoring 50x50; editing "50x50" to "30x30" in place with no note), and
the date the divergence began. The code-side date is **not recoverable**: the
earliest commit touching the constant (96da6ac4, 2026-09-08) already carries
30 and `MAX_SIZE = 50` appears nowhere in this repository's history. Said so
rather than guessed.

### The card's central premise is false, and the measurement

> "the dead ref on FR-001 has been hiding a grid bound the code abandoned"

**It was not hiding it.** `requirements.yml` records the 50 -> 30 narrowing
**five times**: the 2026-08-30 delta header (lines 12, 14, 25), FR-001's own
11-line supersession block (which maps AC-001 -> AC-066, AC-002 -> AC-068,
AC-003 -> AC-069, AC-004 -> AC-070 by name), FR-019's statement, NFR-001's
`threshold` comment and AC-038's supersession note. FR-001 itself carries
`status: superseded`. Nothing there was invisible.

**What WAS hidden is FR-019's refs — the live requirement for the bound.** All
six (AC-066..AC-070 and EC-005) named class-style symbols with **zero**
`def`/`class` lines anywhere, and raised **no warning of any kind**, because
each resolved through the validator's text search by appearing in the
docstring of the very test that covers it. That is strictly worse than
FR-001's four, which at least warn. CON-011's `check:` named the same phantom
as EC-005 and, like it, carried pytest's never-collected `PropertyTest_`
prefix.

So the re-pointing job the card describes is real, and it belongs to FR-019,
not FR-001. **FR-001's four refs are deliberately not re-pointed.** AC-002's
`then` is "a 50x50 grid is produced without error", which is FALSE at
MAX_SIZE=30; the only tests that exist assert the opposite, so pointing at one
would make a false criterion read as verified (CARD-318's F-009, repeated).
AC-001/AC-003/AC-004 are still true but are *preserved historical records*,
and re-pointing a record rewrites it. They now carry `status: superseded` +
`superseded_by` + `superseded_at` instead — the form the registry already uses
for exactly this case (AC-009, AC-038, AC-303, AC-304) and which FR-001's
comment claimed in prose that no tool could read.

### AC-6 is refuted: two fewer warnings, not six

Measured with the validator of record (`meta/kanban/config.yml:38`, the
`forge_1` copy), warning **sets** diffed line by line inside one worktree:
**0 err / 90 warn -> 0 err / 88 warn, 2 removed, 0 added.** The two are
FR-042/AC-268 and FR-042/AC-269, the only honestly dead refs in the card's
set.

FR-001's four **cannot** be retired without a lie or a swap, and this is
mechanical, not a judgement call. `_validate_ac_ec_test_refs` applies the
dead-ref check to every criterion carrying a `test:`, with **no exemption for
`status: superseded`** — AC-009's and AC-038's equivalents are silent only
because a review report or a duration log happens to spell their names, which
is the accident this card family exists to stop relying on. The validator's
own suggested fix (drop the `test:`) trades one warning for the "acceptance
criterion has no 'test'" warning, net zero, and would break AC-6's "no warning
of any kind added" as well. **Routed, not fixed here:** the model-side change
is to exempt a `status: superseded` criterion from the dead-ref check, which
is forge-side (`validators/requirements.py`) and `forge_1` is read-only by
standing rule.

The brief's "main is now 0 errors / 100 warnings" is also wrong: main at
b18fd397 measures **90**. 100 was the pre-CARD-318 figure, consistent with the
brief's own "100 -> 90" for that card.

### The twelve `**DEAD REF**` notes about ADR-0006/R1 are now true

Said here once, per the card's item 6, instead of editing twelve live cards.
ADR-0006/R1's `check:` now names
`tests/test_export_pdf.py::test_the_dependency_baseline_is_still_closed`,
whose `def` is at `tests/test_export_pdf.py:1249` and which parses
`pyproject.toml` and asserts `project.dependencies == {pillow, numpy}` — R1 by
substance, the whole runtime list and not a denylist. The retired name had
**112** text resolvers at b18fd397 (ADR-0039's prose says ~110; both figures
are re-derivable and neither is a constant, so the ADR's wording now says so).
The docstring line at `tests/test_export_pdf.py:1250` that spells the retired
name is left alone: it is the human-readable record of what the ref was, and
it now resolves nothing because nothing declares that name any more.

### Out of scope, measured, routed

- **FR-042's trace row** lists 28 test names, most of them still "planned
  names from requirements.yml" and several defining nothing — measured, not
  assumed: AC-261's, AC-263's and AC-264's refs are falsely alive with zero
  `def`/`class` lines, and bookkeeping-only besides. Only AC-268's and
  AC-269's were swapped. The rest is that row's own standing debt.
- **AC-269 is verified in substance and under-verified in form.** Its new ref
  asserts that the per-book title, not the picture's name, is what the answer's
  caption carries — with a control — but no test reads the rendered caption
  string back for the custom-title case. Written beside the criterion rather
  than passed off as coverage.
- **CON-019's ref and the two ADR-0029 `check:` refs** resolve only through
  docstrings and synced review YAMLs, as the dispatch brief said. Confirmed,
  not touched.

### Traps paid for in this round

- A new test module in `tests/` is inside the validator's **loose-resolution
  domain**, and so is `scratchpad/`. Every instrument this round committed
  derives ref names at run time and spells none, and that property was
  **measured** before the commit by running the whole declared population's
  trie over all four new files (0 hits, trie proved in both directions). The
  census was re-derived after the commit to confirm the new tracked files
  moved nothing.
- `MAX_SIZE = 30 -> 29` is **not** a usable mutant: it breaks
  `tests/conftest.py`'s import, because `book_proof.py` validates a proof
  fixture against the range at module scope. It reds every control too, which
  makes the mutant unanalysable (ADR-0039/R2). `MIN_SIZE = 10 -> 9` widens the
  range, leaves every fixture legal and still breaks the comparison.
- `_strict_resolution` matches a bare ref as a **substring** of a definition's
  name, so renaming `def X` to `def X_renamed` leaves the ref resolving and a
  rename mutant survives for the wrong reason. The AC-2 control mutant renames
  to a name that does not contain the old one.
- A **3-part node id** (`path::Class::method`) resolves in neither instrument:
  the guard's `_strict_resolution` partitions on the first `::` and looks up
  `Class::method` as a symbol. Both re-pointed FR-042 tests are methods, so
  they are referenced by **bare name**, which resolves at the `def` line in
  the guard and in the validator alike. That is also why FR-019's six are bare
  names rather than node ids: the validator resolves a node id only by finding
  that literal string somewhere in the tree (AC-037's lives in two review
  reports and four profiling logs), which is the text-search accident this
  family is about.

## Fix round 1 — review cycle 1 (6.0, three Important + two Minor)

`meta/review/CARD-317-cycle1.yml`. The review verified **every** numeric claim
round 0 made and confirmed all three premise refutations; the defects were one
blind spot, named exactly: the round **re-measured everything handed to it as a
number and trusted what was handed to it as a mechanism**. Two of the three
Important findings are that one root cause. Nothing below revisits a figure the
review certified.

### F-001 — the headline repair had landed in its own erosion class

ADR-0006/R1's repaired `check:` was a **2-part node id**. Measured at
`f70c2d84` under the validator's own pathspec (`git grep -lw <ref> -- .
':(exclude)meta/architecture' ':(exclude)*.md'`, so `meta/review/**` and
`meta/profiling/**` are **inside** the domain):

| ref form | tracked resolvers | includes the module holding the `def`? |
|---|---|---|
| `tests/test_export_pdf.py::test_…closed` | **58** — 52 `meta/review/*.yml`, 4 `meta/profiling/*.txt`, `meta/kanban/backlog-scored.yml`, `tests/test_admin_serving.py:134` | **no** |
| bare `test_…closed` | **82** — those 58 + 24 more review reports + `tests/test_export_pdf.py` | **yes**, the `def` at :1249 |

So the pointer resolved by bookkeeping, just a smaller pile. Fixed to the bare
name. Prune `meta/review/` + `meta/profiling/` + `backlog-scored.yml` and the
bare form still resolves at its `def`; **one honest correction to the review's
wording**, measured: the node-id form does not go fully dead there, it falls to
**exactly one** file — the docstring line at `tests/test_admin_serving.py:134`,
in a module that defines nothing. That strengthens rather than weakens F-001:
the surviving resolver is itself an instance of the accident.

**ADR-0042/R4 carried the identical string and was fixed in the same change.**
Not routed to another card, and the reason is mechanical rather than tidiness:
at the base ADR-0042/R4 was that string's **only** declaration, so repairing
ADR-0006/R1 alone would have left the ref in `RESOLVED_FROM_AFAR` and grown the
census by one — the repair would have been unprovable by this card's own
instrument. Fixing both empties the declaration and the class moves **4 → 3**.
The fix is the 26-character prefix deletion that ADR-0042/R5's own comment
specified on 2026-10-25 and routed, in prose, to "whoever next touches R4";
nothing has owned it since, and prose-only routing is what this card family
exists to stop. **Scope added deliberately:** `Touches` gains
`meta/architecture/decisions/adr/0042-book-interior-is-vector-cover-stays-raster.md`.
R4's statement, scope and severity are untouched.

### F-002 — a false claim about the validator, retracted in place

The comment read *"ADR rule refs are in any case not yet verified at all by the
validator (CARD-319)."* **False, and verified in the validator of record**
(`meta/kanban/config.yml:38`, the `forge_1` copy, read-only):
`validators/requirements.py:169` — `run()` calls
`_validate_adr_rule_check_refs(a, stage, cs)`, **one line above** the AC/EC
check at `:170` the round read correctly; that function (`:729`) walks every
**Accepted** ADR's `## Rules` block and hands each `check:` to the same
`_check_ref_findings`; ADR-0006 is `**Status:** Accepted` and its Rules block
parses, so R1 is reached. Retracted in full rather than softened, with the call
site and the function name cited beside it, because an accepted ADR's claim must
be as legible retracted as it was asserted.

**Consequence routed, not re-derived by the next reader:** the claim came from
**CARD-319**, whose *"Defect 2 — ADR rule check refs are never checked"* is
therefore **refuted at this HEAD**; the orchestrator has marked CARD-319's board
entry as needing re-measurement before it is unblocked. Only the second half of
the retracted sentence survives, and for a different reason than it gave — the
pointer resolved falsely because `_check_ref_findings` asks existence with a
**text** search, not because nothing asked.

### F-003 — AC-269's `then` is now asserted, not narrated

Option **(a)**, the close, not the mark. The review was exactly right that
"verified in substance, under-verified in form" was accurate and that recording
it was right; the defect was that **no card owed the closure**, so the net
effect was a visibility regression — a dead-ref WARN a reader met every run,
replaced by prose. AC-269 now declares **two** comma-separated refs (the form
`requirements.yml:5447` already uses):

1. the wiring test (`tests/test_book_solved_answer_key.py:308`), kept;
2. **new** — `tests/test_book_pdf_band.py:1533`, which composes the caption
   from that module's `ANSWER_CAPTION` template literal (`:182`, a deliberate
   second implementation, not `book_answer_key.answer_caption` run twice),
   asserts that line of ink is on the answer page **exactly once at a size
   other than the band's**, and asserts the picture's own name is printed
   **nowhere** on it.

Why (a) rather than a tool-readable mark plus an owing card: the gap was four
lines wide and the technique already existed in the sibling re-point, so
marking it would have bought a card and a second round to spend what one cell
spends now. The wiring test cannot see this: both sides of its byte comparison
compose the caption through the same primitive, so `"Winter Star — Puzzle 1"`,
or a dropped number, or a dropped em dash would all have kept it green.

### F-004 — the ADR-agreement cell is sentence-scoped now

The cell shipped **line**-scoped while its docstring claimed what sentence scope
buys, and ADR-0001's paragraphs are single lines over a thousand characters —
so one cue anywhere in a paragraph exempted every stale extent in it, and the
**Decision** paragraph (which already carries `narrowed` and `History`) is
exactly where a future reaffirmation would be written. Now split on terminal
punctuation, and the cue must occur in the **same sentence** as the stale
extent. One cue added, measured and not guessed: the sentence scan over the real
file reports **six** sentences holding a stale extent, and the History entry's
two rejected-alternative sentences are retracted by the phrase *"alternative not
taken"* alone — their paragraph's `retired` and `narrowed` sit in other
sentences. The docstring now also states what is still **not** caught: an extent
spliced inside an existing cue-bearing sentence, and a paragraph written as one
sentence. Sentence scope is the narrowest unit a text scan can draw without a
parser.

### F-005 — the six baseline notes are class-specific

Round 0 wrote one union block and pasted it into five notes, so each claimed the
other four's movements. The counts and digests were exact; the attribution was
not. Split, with the **shared method stated once** above the baselines (base,
set diff not count diff, independent `ast` index, nothing pasted from the
failure message, refs by site only). Re-derived against `main` at **b18fd397**,
whose own **nine** stored baselines this derivation reproduces exactly — which
is what makes it a base rather than a nearby commit:

| class | main → HEAD | OUT | IN |
|---|---|---|---|
| bookkeeping-only | 11 → 11 | 0 | 0 |
| falsely-alive | 162 → 155 | 7 | 0 |
| falsely-dead | 13 → 13 | 0 | 0 |
| honest-dead | 18 → 16 | 2 | 0 |
| resolved-from-afar | **4 → 3** | 1 | 0 |
| same-file-prose | 19 → 19 | 0 | 0 |
| census | **586 → 580** | 10 | 4 |
| trace-tests | 513 → 507 | **8** | 2 |
| defined | **406 → 409** | 1 | 4 |

**`TRACE_TESTS` is OUT 8, not 7** — the round-0 summary said seven and the
baseline (513 − 8 + 2 = 507) was right, so only the prose was wrong. The eight:
FR-019's five criteria refs, the phantom its EC-005 and CON-011's `check:`
share (**two declaration sites, one name**, withdrawn from `trace.yml:993` and
`trace.yml:1226`), and FR-042/AC-268's and AC-269's old refs. Corrected in the
guard's own note too.

Also fixed in that module, flagged out-of-scope by the review but re-derived by
this round anyway: `HONEST_DEAD_MEMBERS`'s docstring opened *"The 28 members of
`HONEST_DEAD`"* while the class is 16 (already wrong by 2 on `main`). The
**sentence** now describes the stored **snapshot** and why the gap is the point
of the set; the **set is unchanged**. `HONEST_DEAD_MEMBERS` and
`BOOKKEEPING_ONLY_MEMBERS` are deliberately left as they are — erasing a digest
makes that retirement unrecoverable by name, and the `UserWarning` ("lost 5
member(s)", up from `main`'s 3) is the documented honest-residual path and
cannot fail a gate (no `filterwarnings` anywhere in this tree).

### Hand-off to CARD-316, which serializes behind this card on `requirements.yml`

**Re-derive. Do not offset.** The round-0 hand-off figure ("+27 below FR-001 and
+19 below FR-019") was wrong and has been retracted by the orchestrator; it was
a single pair of offsets where the real shift is **cumulative across five
insertion sites**, and this round moved it again. Measured off the `  - id:`
lines at `b18fd397` and at this HEAD, the file being 6867 → **6985** lines:

| from | shift |
|---|---|
| FR-001's block | +0 |
| FR-002 … FR-019 | +44 |
| FR-020 … FR-042 | +61 |
| FR-043 … NFR-001 | +101 |
| NFR-002 … CON-011 | +111 |
| CON-012 and below | +118 |

Those are the figures **at this commit only**. CARD-316 touches seven criteria
across the same registry; a line number is not a stable handle here and
offsetting one is how the previous figure came to be wrong. Find each criterion
by its `- id:` line.

### Gates re-measured for this round

* **Validator of record** (`meta/kanban/config.yml:38`, the `forge_1` copy):
  **0 err / 88 warn**, against `main` b18fd397's **0 err / 90 warn**. WARN
  **sets** diffed with `comm` inside identical `meta/review/` file sets
  (verified equal with `git ls-files`): **2 removed, 0 added** — FR-042/AC-268's
  and AC-269's dead-ref warnings, unchanged from round 0. Fix round 1 added no
  warning of any kind.
* **G-4, node-id set difference** (`-o addopts=''`, `--collect-only -q`):
  **10,056 → 10,061**, **0 removed**, 5 added — round 0's four new cells plus
  this round's one. No test deleted, renamed, skipped or merged.
* **G-2 / the hard rule**: the guard module names **0 of the 580** declared
  refs, re-verified mechanically after the edits with the module's own trie,
  proved in both directions (finds a known ref, rejects a nonsense one). The
  new band-module cell names its sibling ref **by site** for the same reason.
