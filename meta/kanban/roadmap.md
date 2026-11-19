# Product Roadmap

_Generated: 2026-11-18 · mode: `rescore` (full triage, then score, then plan)_
_Stage: **pre-launch** (kept so the forge validator does not escalate 20 known findings to errors) · capacity mix: **mature** 40/15/25/10/10 · Methodology: **WSJF for every scored category**, FIFO for ops_

## What this rescore did

All **186 open items** in `backlog.md` were checked against cards 300–473 and the current tree (read-only; no test was run, so "unverified" below means exactly that). The 2026-10-30 roadmap had left 107 of them unscored.

| Outcome | Ideas |
|---|---:|
| Scored and waiting (`backlog`, with a score) | 113 |
| Waiting on the owner (not scored as work) | 14 |
| Already carded (`in_kanban`) | 2 |
| `done` (shipped or made moot) | 63 |
| `screened` / `rejected` (permanent record) | 25 |
| **Total in `backlog-scored.yml`** | **217** |

Changed by this pass: **35 ideas marked done** on evidence (9 already-scored ideas flipped, 26 unscored items recorded as done), **17 screened out-of-scope** (process lessons and forge-plugin issues, owner-approved), **51 newly scored**, 9 new owner items, 2 recorded against existing cards (CARD-279, CARD-315).

Not re-checked: IDEA-106, 107, 111 and 112 come from retrospectives and have no `backlog.md` line, so the triage did not reach them; their October scores stand.

## Capacity allocation

Wave budget 3.0 d (`day_calibration.wave_budget_d`, set 2026-10-04 and not re-measured since — treat the wave numbers as an ordering guide, not a schedule).

| Category | % | Budget per wave (d) | Scored ideas | Total (d) |
|---|--:|--:|--:|--:|
| feature | 40 | 1.20 | 10 | 7.12 |
| enabler | 15 | 0.45 | 0 | 0.00 |
| tech-debt | 25 | 0.75 | 102 | 24.38 |
| compliance | 10 | 0.30 | 1 | 0.75 |
| ops | 10 | 0.30 | 0 | 0.00 |

Empty buckets roll over: enabler has no ideas, so its 0.45 d goes to tech-debt (1.20 d per wave); ops has only owner actions, so its 0.30 d goes to feature (1.50 d per wave).

**The mix still under-serves tech-debt**: about 24 d of scored tech-debt against 1.2 d per wave is some 25 waves, while the whole feature list fits in 5. Most of that tail is single-line minors that the cut bar says to fix inline when the file is next touched rather than to card.

## Waiting on the owner (nothing here is scheduled)

- **IDEA-002** Per-directory READMEs: adopt or drop the docs step
- **IDEA-028** Image-mode difficulty sweep vs the 90.0 cutoff
- **IDEA-080** Fill render.md TODO(owner) rows from the Render dashboard
- **IDEA-104** CARD-174 minors: 47.9999 comment; "on both sides" wording
- **IDEA-105** Finalise guide preview needs changes after the owner look (owner to specify)
- **IDEA-114** Should the editor show the pre-edit (stored) difficulty?
- **IDEA-137** Owner check: CARD-177 generic flash wording
- **IDEA-139** Owner check: CARD-178 18.89 reopen renders
- **IDEA-142** Owner check: CARD-180 ?status=all renders
- **IDEA-144** Owner action: back up and apply migration 014
- **IDEA-153** Owner check: CARD-190 review-page longest-side renders
- **IDEA-158** Owner check: CARD-191 Sort by size renders
- **IDEA-162** Owner check: CARD-192 band filter renders
- **IDEA-198** Decide whether gates run with the database armed

## Wave 1 — DONE 2026-11-19

Seven cards merged: CARD-474 (IDEA-108), CARD-475 (IDEA-082), CARD-476 (IDEA-110), CARD-477 (IDEA-129), CARD-478 (IDEA-143), CARD-479 (IDEA-209, published 2026-11-19), CARD-480 (IDEA-130). Wave close: full suite on `main` at `0d8e43f9`, 10663 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 32 min. Not carded, still open: IDEA-149 (verify first), IDEA-178 (owner layout call), IDEA-111 (forge-plugin defect).

### feature  (1.25 / 1.50 d)
1. **IDEA-209** ResizeObserver on .player-stage to re-measure clue bands by construction (WSJF 4.62) — 0.125 d (partly done)
2. **IDEA-143** Selection page still says approved under ?status=all (WSJF 3.08) — 0.125 d
3. **IDEA-129** Grid image route needs ETag; four pages show stale grids (WSJF 2.56) — 0.375 d
4. **IDEA-149** Hint minors: double announcement, focus, animation window, stale text (WSJF 1.54) — 0.25 d ⚑ verify first
5. **IDEA-178** Degraded drawing can touch the header rule on thin bands (WSJF 1.54) — 0.375 d

### tech-debt  (0.62 / 1.20 d)
1. **IDEA-110** Resolve every card's backticked test:/check: name against tests/ at the decompose station (WSJF 12.31) — 0.125 d
2. **IDEA-108** test_web_upload.py sweeps the machine-wide temp dir and reds on concurrent worktrees (WSJF 10.0) — 0.125 d
3. **IDEA-111** Review reports disagree with themselves on severity (markdown Important vs YAML medium) (WSJF 7.69) — 0.125 d
4. **IDEA-082** Five hollow e2e tests post the dead `images` field (WSJF 5.38) — 0.25 d

### compliance  (0.75 / 0.30 d)
1. **IDEA-130** Handlers still flash or return raw exception text (WSJF 2.0) — 0.75 d  ⚠ exceeds the bucket: split it, or spend another category's budget

## Wave 2 — DONE 2026-11-19

Five cards merged: CARD-481 (IDEA-004), CARD-482 (IDEA-021), CARD-483 (IDEA-176), CARD-484 (IDEA-192), and CARD-485 (no idea: the owner's report on the live book that single-puzzle pages lost their footer; 15 pages in that book, 0 after). Wave close: full suite on `main` at `c1f921a2`, 10669 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 1 failed, 31 min. The one red is `tests/test_book_landing_page.py::test_the_way_back_from_a_puzzle_keeps_the_sections_and_the_place` (scrollY 145 vs 220), red on main since another session's merge `c505bd44` and outside every wave-2 card; not fixed here. CARD-485 owner-confirmed on the live book after the push, 2026-11-19.

## Wave 3 (next) — carded 2026-11-19 (board wave 82)

Cut against main on 2026-11-19. Closed at the cut rather than carded: **IDEA-069** (done by CARD-474), **IDEA-107** (superseded by `make test-gate`). Not carded: **IDEA-178** (owner layout call; reachable only on a band of 3 mm or less, which no stored profile has), **IDEA-106** (repo-wide guard audit: open-ended instrument work, held for the owner's say under the cut bar).

### feature  (1.00 / 1.50 d)
- **CARD-232** (IDEA-168 folded in) Solution tiles: what is left — the packing doc and its test (AC-8), the old 6-up wording (AC-9), CARD-202's dormant minors — 2c
- **CARD-486** (IDEA-149) Hint minors, verified first, fixed only where live — 1c

### tech-debt  (0.75 / 1.20 d)
- **CARD-487** (IDEA-006) ADR-0029/R4's check tests its rule — 1c
- **CARD-488** (IDEA-034, IDEA-017, IDEA-083, IDEA-100) Four small test-side gaps — 2c

## Wave 2 as planned

### feature  (1.50 / 1.50 d)
6. **IDEA-176** Is the two-up folio reserve still needed? It costs pairings (WSJF 1.23) — 0.75 d
7. **IDEA-192** Order and name hints by the solver's per-cell technique grade (WSJF 1.23) — 0.75 d (partly done)

### tech-debt  (1.00 / 1.20 d)
5. **IDEA-004** Fix dead check: refs on mandatory rules (CON-005, INV-*) (WSJF 5.08) — 0.75 d (partly done)
6. **IDEA-021** book_proof.render_proof_pdf still writes DeviceRGB (WSJF 5.0) — 0.25 d

## Ranked by category

### feature — WSJF, 10 ideas

| Rank | Wave | ID | Idea | Score | Days | Depends | State |
|--:|--:|---|---|--:|--:|---|---|
| 1 | 1 | IDEA-209 | ResizeObserver on .player-stage to re-measure clue bands by construction | 4.62 | 0.125 | — | partly |
| 2 | 1 | IDEA-143 | Selection page still says approved under ?status=all | 3.08 | 0.125 | — | open |
| 3 | 1 | IDEA-129 | Grid image route needs ETag; four pages show stale grids | 2.56 | 0.375 | — | open |
| 4 | 1 | IDEA-149 | Hint minors: double announcement, focus, animation window, stale text | 1.54 | 0.25 | — | unverified |
| 5 | 1 | IDEA-178 | Degraded drawing can touch the header rule on thin bands | 1.54 | 0.375 | — | open |
| 6 | 2 | IDEA-176 | Is the two-up folio reserve still needed? It costs pairings | 1.23 | 0.75 | — | open |
| 7 | 2 | IDEA-192 | Order and name hints by the solver's per-cell technique grade | 1.23 | 0.75 | — | partly |
| 8 | 3 | IDEA-168 | Eight dormant minors carried from CARD-202's review | 0.77 | 0.375 | — | partly |
| 9 | 4 | IDEA-125 | Second QR: generate your own puzzle from a picture | 0.53 | 2 | — | open |
| 10 | 5 | IDEA-126 | Persist user-generated puzzles | 0.36 | 2 | IDEA-125 | open |

### compliance — WSJF, 1 ideas

| Rank | Wave | ID | Idea | Score | Days | Depends | State |
|--:|--:|---|---|--:|--:|---|---|
| 1 | 1 | IDEA-130 | Handlers still flash or return raw exception text | 2.0 | 0.75 | — | open |

### tech-debt — WSJF, 102 ideas (top 30; the rest are in `backlog-scored.yml`)

| Rank | Wave | ID | Idea | Score | Days | Depends | State |
|--:|--:|---|---|--:|--:|---|---|
| 1 | 1 | IDEA-110 | Resolve every card's backticked test:/check: name against tests/ at the decompos | 12.31 | 0.125 | — | open |
| 2 | 1 | IDEA-108 | test_web_upload.py sweeps the machine-wide temp dir and reds on concurrent workt | 10.0 | 0.125 | — | open |
| 3 | 1 | IDEA-111 | Review reports disagree with themselves on severity (markdown Important vs YAML  | 7.69 | 0.125 | — | not re-checked |
| 4 | 1 | IDEA-082 | Five hollow e2e tests post the dead `images` field | 5.38 | 0.25 | — | open |
| 5 | 2 | IDEA-004 | Fix dead check: refs on mandatory rules (CON-005, INV-*) | 5.08 | 0.75 | — | partly |
| 6 | 2 | IDEA-021 | book_proof.render_proof_pdf still writes DeviceRGB | 5.0 | 0.25 | — | open |
| 7 | 3 | IDEA-069 | Upload tests glob shared temp dir (parallel interference) | 5.0 | 0.25 | — | partly |
| 8 | 3 | IDEA-107 | Install pytest-testmon so review.test_scope: impact stops falling back to full | 5.0 | 0.25 | — | not re-checked |
| 9 | 4 | IDEA-106 | ADR-0039's repo-wide guard audit: make R1-R3 reach a guard written tomorrow | 4.46 | 0.75 | — | not re-checked |
| 10 | 4 | IDEA-112 | Promote the remaining wave-37 discipline rules into the model (one architect pas | 4.1 | 0.375 | IDEA-106 | not re-checked |
| 11 | 5 | IDEA-006 | ADR-0029/R4 check can't test its rule (overlap masks) | 3.85 | 0.25 | — | open |
| 12 | 5 | IDEA-017 | Pin migrations/env.py URL-not-logged by assertion (CARD-148) | 3.85 | 0.125 | — | unverified |
| 13 | 5 | IDEA-034 | db_required hook pings DATABASE_URL before _test guard | 3.85 | 0.125 | — | open |
| 14 | 5 | IDEA-044 | validate_margins accepts below 0.635 cm minimum | 3.85 | 0.125 | — | open |
| 15 | 5 | IDEA-083 | Size test not tied to the form's field names (mutant M8) | 3.85 | 0.125 | — | open |
| 16 | 5 | IDEA-100 | CARD-175 minors: summary focus ring token; test comments | 3.85 | 0.125 | — | open |
| 17 | 6 | IDEA-009 | NFR + check for the deployed panel's 512 MB memory limit | 3.59 | 0.375 | — | open |
| 18 | 6 | IDEA-011 | Hand-edit mark not released on revert (CARD-120 F-007) | 3.46 | 0.25 | — | open |
| 19 | 6 | IDEA-024 | Undrawable row shown between page labels w/o marker | 3.46 | 0.25 | — | open |
| 20 | 7 | IDEA-031 | Concurrent runs share nonogram_test; DROP SCHEMA races | 3.33 | 0.375 | — | partly |
| 21 | 7 | IDEA-014 | Memory mode get_book returns live Book (CARD-136) | 3.08 | 0.25 | — | open |
| 22 | 7 | IDEA-029 | Stale 'four members' enum_note + ADR-0025 test narrative | 3.08 | 0.125 | — | open |
| 23 | 7 | IDEA-035 | diagnose_postgres.sh hardcodes nonogram_poc | 3.08 | 0.125 | — | open |
| 24 | 7 | IDEA-038 | admin_scripts helper imports private test names | 3.08 | 0.125 | — | open |
| 25 | 7 | IDEA-054 | Public read instead of _as_readable_grid (CARD-160 F-006) | 3.08 | 0.125 | — | open |
| 26 | 8 | IDEA-062 | Player shows tier 'MEDIUM' upper-case | 3.08 | 0.125 | — | open |
| 27 | 8 | IDEA-068 | Vacuous trim assertion in DB mode (CARD-120 F-009) | 3.08 | 0.25 | — | unverified |
| 28 | 8 | IDEA-081 | scripts/README Manual Commands run pytest against nonogram_poc | 3.08 | 0.125 | — | open |
| 29 | 8 | IDEA-093 | CARD-176 minors: pin bare-token echo row; AC-1 echo check per case | 3.08 | 0.125 | — | open |
| 30 | 8 | IDEA-097 | CARD-172 minors: cap-height comment source; square page-2 docstring claim | 3.08 | 0.125 | — | partly |

## Notes that change how to read the ranking

- **IDEA-004 carries a registry defect worth knowing regardless of rank.** CON-005, the one mandatory solver property, names the check `PropertyTest_Solver_NeverFalsePositiveUniqueness`, which is defined nowhere; the real test is `test_never_false_positive_uniqueness` in `tests/property/test_solver_uniqueness.py`. The property is tested; the registry's pointer to it is dead. The aging triage slotted IDEA-214 (the "check ref resolves to a mention" family, four independent reviews) into IDEA-004.
- **IDEA-108 and IDEA-069 are the same defect** (the upload tests glob the machine-wide temp dir); one fix closes both.
- **The kill-matrix items overlap heavily** (IDEA-182, IDEA-183, IDEA-184, IDEA-185, IDEA-187, IDEA-188, IDEA-196, IDEA-203): IDEA-185, IDEA-187 and IDEA-188 are one job on the AC-7 anchors, and IDEA-196 and IDEA-203 share one missing `setattr`; card them together if at all.
- **IDEA-176** (two-up folio reserve): its payoff figures predate CARD-392's footer change; re-measure before sizing.
- **IDEA-125 / IDEA-126** (second QR, persisting user puzzles) need a public generator that does not exist, and the one-QR ruling of 2026-11-07 may have settled the first. They are ranked last and are really owner questions.
- **IDEA-178** (header-rule ink on thin bands) sits in wave 1 by score, but no stored print profile reaches the band where it shows; whether to fix it at all is an owner call.
- **⚑ verify first** marks an item whose current state could not be established without running a test.

## Signals consulted

- **Aging ratchet (Step 2.5b)**: ran for the first time. One mandatory item (IDEA-214), slotted into IDEA-004 and recorded in `meta/kanban/triage-outcomes.yml`; `verify` exits 0.
- **Risk register**: `meta/risk-register.yml` was created **empty** on 2026-11-18 so the ratchet could read it. It records no risks because none have been captured, not because none exist. Run `/forge:risk`.
- **ASM-0001** (unvalidated, non-fatal; its check is overdue): no scored idea rests on large grids.
- **Effort calibration**: new job sizes use the same cumulative ×1.3 the October scores carry. The python-pro/feature signal (2.05×, 4 cards) is `confidence: low` and bimodal, so it was not applied.
- No `intents.md`, `weights.md`, `constraints.md` or research synthesis → no intent, interest-weight, constraint or anti-positioning screens ran.
- No `waves.duration` configured → no velocity forecast.

## Next step

Not `/forge:architect`: wave 1 is small fixes and one compliance item, none needing design. What would move things: answer the owner items above, card wave 1 through `/forge:kanban`, and capture real risks with `/forge:risk`.
