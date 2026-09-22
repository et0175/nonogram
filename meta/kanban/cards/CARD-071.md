# CARD-071: Architecture and docs hygiene — land the requirements registry on main, fix dangling references

**Status:** done
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/071-architecture-docs-hygiene
**Worktree:** ../PythonProject4-CARD-071
**Source:** docs/GENERATION_ALGORITHM.md §10-§11 (2026-09-12 generation code review), board.md "Repository integrity note", and CARD-074 review cycle 1 findings F-001/F-002 (2026-09-13); follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/kanban/cards/CARD-074.md (Touches line + AC-D wording), meta/review/20260913T173000Z-CARD-074-cycle1.yml (finding status), meta/architecture/requirements.yml, meta/architecture/trace.yml (FR-013/FR-027 status), meta/architecture/glossary.yml, meta/architecture/platform.yml, meta/architecture/inputs/raw-requirements.md, tests/test_difficulty_tiers.py (docstring mapping table only — see item 8), CLAUDE.md, meta/architecture/decisions/adr/0001-*.md, 0004-*.md, 0006-dependency-baseline.md, meta/architecture/domain/policies.yml, docs/REQUIREMENTS/README.md, docs/REQUIREMENTS/DIFFICULTY_ENGINE.md, docs/REQUIREMENTS/REQUIREMENTS_OVERVIEW.md, docs/REQUIREMENTS/ADMIN_CONSOLE_REQUIREMENTS.md, docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md
**Review score:** — _(merged without a review cycle, at the owner's call)_
**Started:** 2026-09-22
**Closed:** 2026-09-22
**Actual:** 0.4d
**Merge commit:** 19eca81
**Blocked by:** —

## Re-cut 2026-09-22 — item 1 is already done, and AC-1 can no longer be met as written

Every claim below was checked against `main` at `4effc67` before starting.
Four of the seven items stand as written; three do not.

**Item 1 — already done, by ordinary traffic.** All five files
(`requirements.yml`, `trace.yml`, `glossary.yml`, `platform.yml`,
`inputs/raw-requirements.md`) are **tracked on `main`**. Whatever committed
them, it was not this card; `requirements.yml` alone has been edited and
committed by CARD-078 and CARD-106 in the last two days. Nothing to do.

**Item 5 — stands.** `0006-dependency-baseline.md:7` still reads
`**Migration:** rewrite (DISCHARGED 2026-09-01 by CARD-032, merge 5bd126a)`
and the validator still WARNs on it.

**Items 2, 3, 4, 7 — stand.** `docs/requirements.md` does not exist and 58
references point at it; `README.md` points at a file that is not there;
none of the three stale docs carries a banner yet;
`ADMIN_CONSOLE_REQUIREMENTS.md:120` still says 60 s per image; both CARD-074
findings still read `status: open`.

Two corrections to the card's own text, and one new finding:

- **Item 3 understates it.** `README.md`'s directory tree names about twenty
  files. **Three exist**, and one of those under a different name
  (`TRACEABILITY/TRACEABILITY_MATRIX.md`, listed as
  `TRACEABILITY/REQUIREMENTS_MATRIX.md`). `NONOGRAM_GENERATION_FEATURES.md` is
  not the exception the card treats it as — it is one entry in a tree that is
  almost entirely aspirational. Replace the tree with what is on disk.
- **Item 7's F-001 half-misnames its target.** AC-D exists **only** in
  `meta/kanban/cards/CARD-074.md:133`. There is no AC-D on FR-025 in
  `requirements.yml` — its criteria are AC-111..AC-114, AC-132 and a property
  test. So F-001 is a one-file edit, not two.

**AC-1 cannot be met as written: the validator reports 4 errors today, and
one of them is a defect in the validator, not in this repo.**

| Error | What it is |
|---|---|
| `FR-013 status 'done' is not valid` | `trace.yml:279`, written by CARD-075. Schema allows `covered \| partial \| missing`. FR-013 lists 9 tests → `covered`. |
| `FR-027 status 'done' is not valid` | `trace.yml:1340`, written by CARD-079. Same fix. |
| `FR-026 test 'TestTiers_BranchingIsAStrategyNotATier' … dead link` | Real, and bigger than it looks — see below. |
| `ADR-0025 circular supersession: ADR-0025 → ADR-0031 → ADR-0025` | **A false positive.** See below. |

**The ADR-0025 cycle is the validator's bug.** `adr_integrity.py`'s
`_SUPERSEDES_PAT` is `supersed(?:es?|ed\s+by)\s+adr-NNNN` — it matches
*"superseded by"* and *"supersedes"* with the same regex and adds an edge in
the same direction for both. So ADR-0025's `Superseded by ADR-0031` gives
0025→0031, and ADR-0031's History line `Supersedes ADR-0025 on the owner's
decision` gives 0031→0025. Any correctly cross-linked supersession pair in any
repo trips it. ADR-0013→ADR-0029 escapes only because ADR-0029 never spells
the back-link in a matching form.

I can make it go away by writing ADR-0031's History line as *"superseding
ADR-0025"* (the participle does not match the regex) — but that is contorting
a correct record to satisfy a broken check, in a *history* line, and the next
person to write "supersedes" reintroduces it. **Proposed: leave both ADRs
alone, and re-word AC-1 to exempt this error by name.** The validator lives
outside this repo (`~/MyProjects/forge_1/…`); fixing it there is not this
card's business, and this card must not edit it silently.

**FR-026's dead link is a missing label line, and my first read of it was
wrong.** I first concluded CARD-098 had written none of its four named tests.
It wrote all four. The convention in this repo is that the registry cites a
CamelCase *label* and the test file carries that label in a comment or the
module docstring beside a snake_case function — `tests/test_nudge.py:8` maps
`AC-035  TestNudge_ReportsFailureAtCap`, `tests/test_orchestrator.py:9` maps
`AC-111  TestRecovery_RepairFlipsOnePairInsideUndecidedMask`, and the
validator's `git grep -w` finds the label there. `test_difficulty_tiers.py`
already keeps such a table at the top of the file (AC-020, AC-021) — CARD-098
simply did not add its four rows to it. The functions are
`test_tiers_three_bands_and_no_fourth_tier` and its three siblings at lines
643-705, each with the matching `AC-N:` docstring, all passing.

So the fix is four lines in that file's existing mapping table, not five
renames in the registry — and the registry's CamelCase spellings are correct
as they stand. **Item 8 below** takes it. This is a comment-only edit to a
test file; AC-5's "no test file is edited" is narrowed accordingly, since its
intent was that no test's *behaviour* be changed to make a record true.

## Why

The 2026-09-12 review (`docs/GENERATION_ALGORITHM.md` §10, and §11 "Where
this differs from the other documents") found that the architecture
registry and the prose docs had drifted from `main` in three ways:

- `main` had **no** `requirements.yml`, `trace.yml`, `glossary.yml`,
  `platform.yml` or `inputs/raw-requirements.md`. They existed only on the
  disjoint old chain (the `card/037-persist-upload-retry` worktree, which
  shares no common ancestor with `main` — see board.md "Repository
  integrity note"). On 2026-09-12 they were copied onto `main`'s working
  tree, uncommitted, from `git show card/037-persist-upload-retry:<path>`;
  the validators report 0 errors on them. They are the files this card's
  ADRs, policies and trace point at, and they are currently untracked.
- Several living documents cite a `docs/requirements.md` that never
  existed on `main` (CLAUDE.md, two ADRs, a policy rationale, two NFR
  rationales, the generation-requirements references section).
- Two documents under `docs/REQUIREMENTS/` describe an algorithm (Otsu
  binarisation, strategy-count difficulty) that was never built (§11),
  one README points at a file that does not exist, and the admin
  requirements state a 60 s per-image timeout where the code enforces
  30 s per request.

None of this needs an ADR: no decision changes, only where the decisions
are recorded and what they point at.

## What to implement

1. ~~**Commit the five restored files** under `meta/architecture/`.~~
   **Done before this card started** — all five are tracked on `main`. Left
   in place because it is what the card was opened for; see the re-cut.
2. **Replace every reference to `docs/requirements.md`** with
   `meta/architecture/requirements.yml` (or the specific FR/NFR id where
   the sentence is about one requirement). Known sites: `CLAUDE.md`,
   `decisions/adr/0001-generation-time-thresholds.md`,
   `decisions/adr/0004-pixel-nudge-diff-reporting.md`,
   `domain/policies.yml` (POL-003 rationale), `requirements.yml`
   NFR-001/NFR-002 rationale text,
   `docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md` references
   section. A grep on 2026-09-12 also hits `meta/business/vision.md`,
   `decisions/adr/0005-*.md`, `0008-*.md`, `0013-*.md`,
   `inputs/raw-requirements.md`, `glossary.yml`, and the closed cards
   `CARD-009`, `CARD-023`, `CARD-029` — fix the living documents the same
   way; for the closed cards, rewrite only the path (their narrative is
   history). `grep -rn "docs/requirements.md"` must return nothing
   afterwards (AC-2).
3. **`docs/REQUIREMENTS/README.md`'s directory tree is fiction.** It names
   about twenty files across `FEATURES/`, `USER_STORIES/`,
   `ACCEPTANCE_CRITERIA/`, `TEST_CASES/`, `TRACEABILITY/`, `NON_FUNCTIONAL/`,
   `FINDINGS/` and `TESTING/`. Three exist, one of them under a different name
   (`TRACEABILITY/TRACEABILITY_MATRIX.md`, listed as `REQUIREMENTS_MATRIX.md`).
   Replace the tree with the nine files actually on disk, and say in one line
   that the live registry is `meta/architecture/requirements.yml` and the live
   algorithm reference is `docs/GENERATION_ALGORITHM.md`. Delete nothing.
4. **Banners and corrections on the stale docs** — do not delete anything:
   - `docs/REQUIREMENTS/DIFFICULTY_ENGINE.md`: add a status banner at the
     top in the same blockquote style as the one already at the top of
     `NONOGRAM_GENERATION_REQUIREMENTS.md`, saying the shipped formula is
     ADR-0013's (`100·effort·relief`, tiers at 33/66 — §7 of
     GENERATION_ALGORITHM.md) and that a rescoring decision is pending;
     the strategy-count formula exists only in the orphaned
     `analysis/strategy_counter.py` (CARD-053).
   - `docs/REQUIREMENTS/REQUIREMENTS_OVERVIEW.md` lines 65 and 79 mention
     Otsu: add a one-line note pointing to `GENERATION_ALGORITHM.md` §4.3
     (the shipped path is LANCZOS resize + Floyd–Steinberg dither).
   - `docs/REQUIREMENTS/ADMIN_CONSOLE_REQUIREMENTS.md` REQ-2.3.1
     (around line 120, "Generation completes within timeout (60s per
     image)"): correct to the enforced 30 s per request
     (`orchestrator.GENERATION_BUDGET_SECONDS`) plus the admin's up to
     three runs per picture (the base run and CARD-062's ±1 retries).
5. **`decisions/adr/0006-dependency-baseline.md` metadata.** The
   validator WARNs that its `**Migration:**` value —
   `rewrite (DISCHARGED 2026-09-01 by CARD-032, merge 5bd126a)` — is not
   one of `rewrite | on-touch | grandfather | —`. Set it to a valid value
   and move the discharge note ("discharged 2026-09-01 by CARD-032, merge
   5bd126a") into the ADR's existing `## History` section.
6. **Do not duplicate CARD-053** (the orphaned `analysis/` and
   `generation/` packages) — link to it from the DIFFICULTY_ENGINE banner
   and leave that work where it is.
7. **CARD-074's two open review findings** (cycle 1, 2026-09-13 — both are
   record corrections to merged work, no code):
   - **F-001.** AC-D in `meta/kanban/cards/CARD-074.md:133` (and *only*
     there — there is no AC-D on FR-025 in `requirements.yml`; see the re-cut)
     names
     "the 100-request 20x20 density-20 seeded corpus", but its test runs 36
     seeds at 10x10 density 30. The *test* is the right artefact: on the
     stated corpus the assertion is vacuous, because all 60 sampled requests
     abandon at both `MAX_CONSECUTIVE_REPAIRS = 0` and `= 3`. Re-word AC-D to
     name the corpus the test uses and why, keeping the id and the test name
     (the FR-003/AC-009 convention). The 20x20 measurement AC-D also asks for
     stays where it is, in CARD-074's Worktree notes.
   - **F-002.** `tests/test_naming.py` and `tests/test_sourcing_image.py`
     each gained one `MAX_CONSECUTIVE_REPAIRS = 0` line in CARD-074 and are
     absent from that card's `Touches`. Add them, with the one-clause reason
     (both are scripted random-mode tests counting *source* calls, which a
     repair does not make).
   Mark both `status: fixed` in
   `meta/review/20260913T173000Z-CARD-074-cycle1.yml` when done.
8. **The three validator errors that are this repo's** (added by the 2026-09-22
   re-cut; the fourth is the validator's own bug and is exempted in AC-1):
   - `trace.yml:279` (FR-013) and `trace.yml:1340` (FR-027): `status: done`
     → `status: covered`. Both list tests; `done` is not in the schema's
     `covered | partial | missing`. Leave the `notes` prose untouched — it is
     the delivery record and it is accurate.
   - `tests/test_difficulty_tiers.py`: add CARD-098's four AC rows to the
     mapping table the file's docstring already carries, in the existing
     format (`AC-1  TestTiers_ThreeBandsAndNoFourthTier -> test_tiers_three_
     bands_and_no_fourth_tier`, and the three siblings). Comment/docstring
     only — no test body, no assertion, no collection change.

## Acceptance criteria

- **AC-1** — `validate.py --root meta/architecture` reports **one** error:
  `ADR-0025 circular supersession`, which the re-cut establishes is a
  false positive from `adr_integrity.py`'s `_SUPERSEDES_PAT` treating
  "supersedes" and "superseded by" as the same direction. FR-013, FR-027 and
  the FR-026 dead link are gone, and so is the ADR-0006 Migration WARN. The
  "no tests yet" WARNs may remain.
- **AC-2** — that same grep returns nothing **in the living documents**:
  `CLAUDE.md`, `meta/business/`, `meta/architecture/` outside `inputs/`, and
  `docs/`. *(Narrowed while implementing, 2026-09-22 — the original "returns
  nothing anywhere" would have required falsifying records. Three kinds of hit
  are deliberately left: `meta/architecture/inputs/raw-requirements.md`, whose
  own header forbids editing processed lines and which now carries a note
  saying the path does not resolve; the closed cards `CARD-009`, `CARD-023` and
  `CARD-029`, which record work done on that file when it existed on the
  disjoint old chain — `CARD-029` even cites the lines it edited, so rewriting
  the path would make the card describe something that never happened; and this
  card, which has to name what it retired.)*
- **AC-3** — the three superseded/stale docs (`DIFFICULTY_ENGINE.md`,
  `REQUIREMENTS_OVERVIEW.md`, `ADMIN_CONSOLE_REQUIREMENTS.md`) carry their
  banners or corrections, every path in `README.md`'s tree exists on disk, and
  nothing under `docs/` or `meta/architecture/` is deleted.
- **AC-4** — pytest is unaffected: the suite's pass/fail set is identical
  before and after (docs and registry text; `tests/test_cli.py`'s
  structural import guard still passes). The one test-file edit is a docstring
  table — `3,694 passed, 0 failed` before and after.
- **AC-5** — CARD-074's AC-D and `Touches` match what the code and the tests
  actually do, and both CARD-074 findings read `status: fixed` in the cycle-1
  review report. No test *behaviour* is edited by this card.

## Guardrails

- G-1: No edits under `src/` — text-only changes elsewhere (none are
  expected in `src/`; if one turns out to be needed, stop and note it).
- G-5: No edits to the forge validator at
  `~/MyProjects/forge_1/forge/skills/architect-validate/` — it is outside this
  repo. Its supersession-cycle bug is reported in this card, not patched here.
- G-6: `tests/test_difficulty_tiers.py` may gain docstring lines and nothing
  else. If item 8 turns out to need a code change, stop and say so.
- G-2: Do not rewrite any ADR's Decision, Consequences or Alternatives —
  only references and header metadata; ADR-0006's discharge history is
  moved, not dropped.
- G-3: Do not touch `meta/kanban/` beyond this card's own notes, and do
  not delete `docs/REQUIREMENTS/*` — supersede with banners.
- G-4: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes (`nonogram_admin.db`,
  `*.pdf`, `egg-info`); use explicit pathspecs.

## Worktree notes

### Delivered 2026-09-22

Docs and registry only, plus three docstring tables in the test tree. **Suite
identical before and after: 3,694 passed, 26 skipped, 1 deselected** (AC-4).

**The validator reports 1 error, down from 4** (AC-1). The survivor is
`ADR-0025 circular supersession`, which is a bug in
`~/MyProjects/forge_1/.../validators/adr_integrity.py`: `_SUPERSEDES_PAT`
matches "supersedes" and "superseded by" with one regex and adds an edge in the
same direction for both, so any correctly cross-linked supersession pair looks
like a cycle. Left alone on the owner's call, with G-5 forbidding a patch to a
tool outside this repo. ADR-0013→ADR-0029 escapes it only by accident: ADR-0029
never spells the back-link in a form the regex matches.

### Fixing the schema violation unmasked nine more dead links

`trace.yml`'s two `status: done` entries were not just cosmetic — `done` is
outside the schema, and the validator skips the test-link check for an entry it
cannot classify. Correcting them to `covered` turned 2 errors into 10, all of
them FR-013's and FR-027's test names. Every one was the same defect as
FR-026's: the registry cites a CamelCase **label**, the convention is that the
label appears in a comment or docstring beside a snake_case function
(`test_nudge.py:8`, `test_orchestrator.py:9`), and CARD-075/CARD-079/CARD-098
never wrote their rows. The tests were all present and passing. Added 14 label
rows across three files; no test body touched.

**One label had no test at all.**
`TestNudge_MaskDrivenAttemptsRemainCumulativeFromOriginalConversion` (FR-013's
AC-117) was never written, here or anywhere — `git log -S` over the test tree
finds it never existed. CARD-075 re-amended the mask-driven mechanism it was
named for before the test was written. AC-117's claim *is* asserted, and over a
corpus rather than one conversion, by EC-014's
`PropertyTest_Nudge_FlippedCellsSubsetOfUndecidedMaskAndNested`, so AC-117 is
re-pointed there rather than retired; the trace entry is dropped because the
property test was already listed on the next line.

### What I got wrong, and corrected

I first concluded CARD-098 had never written its four named tests and started
to plan five registry renames. It wrote all four; they are snake_case functions
in `test_difficulty_tiers.py:643-705` with matching `AC-N:` docstrings. The
registry's CamelCase spellings were right all along — what was missing was the
mapping table row. Corrected in the re-cut before implementing.

### Citations that were worse than dangling

Two sites did not just name a missing file, they **resolved to the wrong
requirement**:

- `policies.yml`'s POL-003 rationale cited "FR-016 (Decisions Log #4)" against
  the intake document's numbering. FR-016 in this registry is the two-page PDF
  export; the nudge cap is FR-013. Re-pointed.
- `glossary.yml`'s TERM-008 cited that document's `#FR-16` for "Pixel nudge" —
  the same mismatch. Now `FR-013`.

A grep-and-replace of the path would have left both pointing confidently at the
wrong thing. This is why item 2 was not done mechanically.

### Scope found on the way (all fixed, all one line each)

- `meta/business/vision.md` named **three** intake documents under `docs/`;
  none of the three exists.
- `NONOGRAM_GENERATION_REQUIREMENTS.md`'s references section named
  `src/nonogram/sourcing/grid.py` (never existed — it is `random_grid.py`),
  `docs/ADMIN_CONSOLE_REQUIREMENTS.md` (wrong directory) and
  `TESTING_AND_REQUIREMENTS_INDEX.md` (does not exist).
- `REQUIREMENTS_OVERVIEW.md` pointed at
  `docs/NONOGRAM_GENERATION_REQUIREMENTS.md`, also the wrong directory.

### The DIFFICULTY_ENGINE banner the card asked for would have been wrong

The card (written 2026-09-12) says to write that the shipped formula is
ADR-0013's `100·effort·relief`. ADR-0013 was **superseded by ADR-0029 the same
day**. What ships is the strategy ladder — `simple_overlap` < `line_dp` <
`probe_contradiction`, scored as `band_low(rung) + share·band_width(rung)` —
which is *closer* to that document's strategy-based idea than the card credits.
The banner says that instead. The tier edges the card gives (33/66) are right,
and they are ADR-0005's, which is what makes the Easy band non-empty.

Checked rather than repeated: `analysis/strategy_counter.py` is still orphaned,
but `analysis/quality_metric.py` is **not** — `admin/app.py:78` imports it
(CARD-050). CARD-053's "nothing in `admin/**` imports either package" is stale;
not corrected here, since G-3 keeps this card out of other cards' notes.

### Left deliberately

`docs/REQUIREMENTS/README.md` describes a whole parallel requirements framework
(`REQ-xxx`/`AS-xxx`/`TC-xxx`, checklists, metrics) that was never populated —
of ~20 files its tree listed, three exist. The tree is replaced with what is on
disk plus a table mapping each planned directory to the live thing that holds
it; the checklists below it are kept as the plan they were, per G-3.
