# CARD-071: Architecture and docs hygiene — land the requirements registry on main, fix dangling references

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 0.5d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/071-architecture-docs-hygiene
**Worktree:** —
**Source:** docs/GENERATION_ALGORITHM.md §10-§11 (2026-09-12 generation code review) and board.md "Repository integrity note"; follow-up card, not decomposed from handoff.md
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** meta/architecture/requirements.yml, meta/architecture/trace.yml, meta/architecture/glossary.yml, meta/architecture/platform.yml, meta/architecture/inputs/raw-requirements.md (commit the restored copies), CLAUDE.md, meta/architecture/decisions/adr/0001-*.md, 0004-*.md, 0006-dependency-baseline.md, meta/architecture/domain/policies.yml, docs/REQUIREMENTS/README.md, docs/REQUIREMENTS/DIFFICULTY_ENGINE.md, docs/REQUIREMENTS/REQUIREMENTS_OVERVIEW.md, docs/REQUIREMENTS/ADMIN_CONSOLE_REQUIREMENTS.md, docs/REQUIREMENTS/NONOGRAM_GENERATION_REQUIREMENTS.md
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

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

1. **Commit the five restored files** under `meta/architecture/`
   (`requirements.yml`, `trace.yml`, `glossary.yml`, `platform.yml`,
   `inputs/raw-requirements.md`). First re-run
   `python /Users/omelnikova/MyProjects/forge_1/forge/skills/architect-validate/scripts/validate.py --root meta/architecture`
   — 0 errors required; the 38 "no tests yet" WARNs are pre-existing and
   out of scope.
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
3. **`docs/REQUIREMENTS/README.md`** lists `NONOGRAM_GENERATION_FEATURES.md`
   (lines 12-14) which does not exist — point it at
   `docs/GENERATION_ALGORITHM.md`.
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

## Acceptance criteria

- **AC-1** — `validate.py --root meta/architecture` reports 0 errors, and
  the ADR-0006 Migration WARN is gone (the 38 "no tests yet" WARNs may
  remain).
- **AC-2** — `grep -rn "docs/requirements.md" . --include=*.md --include=*.yml --include=*.py`
  (excluding `.venv`, `.git`, and the `../PythonProject4-CARD-037`
  worktree) returns nothing.
- **AC-3** — the three superseded/stale docs (`DIFFICULTY_ENGINE.md`,
  `REQUIREMENTS_OVERVIEW.md`, `ADMIN_CONSOLE_REQUIREMENTS.md`) carry their
  banners or corrections, `README.md` points at an existing file, and
  nothing under `docs/` or `meta/architecture/` is deleted.
- **AC-4** — pytest is unaffected: the suite's pass/fail set is identical
  before and after (docs-only plus ADR text; `tests/test_cli.py`'s
  structural import guard still passes).

## Guardrails

- G-1: No edits under `src/` — text-only changes elsewhere (none are
  expected in `src/`; if one turns out to be needed, stop and note it).
- G-2: Do not rewrite any ADR's Decision, Consequences or Alternatives —
  only references and header metadata; ADR-0006's discharge history is
  moved, not dropped.
- G-3: Do not touch `meta/kanban/` beyond this card's own notes, and do
  not delete `docs/REQUIREMENTS/*` — supersede with banners.
- G-4: Commit only your own files — the working tree carries a large
  standing set of unrelated staged/untracked changes (`nonogram_admin.db`,
  `*.pdf`, `egg-info`); use explicit pathspecs.

## Worktree notes

—
