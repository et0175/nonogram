# Product Roadmap

_Generated: 2026-10-04 · from meta/kanban/backlog-scored.yml_
_Stage: pre-launch (Book 1 not yet on KDP) · Methodology: WSJF for every non-ops category (owner choice 2026-10-04: RICE reach is meaningless for a single-owner admin tool), FIFO for ops_

## Capacity Allocation

Wave budget assumed at **3 days** of card work (waves 28–31 ran 2.25–4.75 d of estimates). WSJF job size → days: 1→0.25 · 2→0.5 · 3→0.75 · 5→1.5 · 8→2.5 · 13→4 · 20→6 (already reflecting the retro calibration: estimates run ~0.55× actual).

| Category | % | Per wave (days) | Note |
|---|--:|--:|---|
| feature | 60 | 1.80 |  |
| enabler | 15 | 0.45 | no ideas — rolls over to tech-debt |
| tech-debt | 5 | 0.15 | own 5% + enabler/feature roll-over |
| compliance | 15 | 0.45 | no ideas — rolls over to ops |
| ops | 5 | 0.15 |  |

⚑ The backlog is 55 tech-debt vs 14 feature ideas (80/20), while pre-launch capacity gives tech-debt 5%. It still progresses because empty buckets roll over, and once the 14 features drain (wave 5, except IDEA-058/IDEA-075) tech-debt gets nearly the whole wave. If clearing debt before Book 1 matters more, set tech-debt higher in a `meta/.skills.yml` `capacity:` block.

⚑ Open owner decisions sit inside the plan — they cost nothing to schedule but nothing moves until answered: IDEA-001 (fixture back-pointers), IDEA-002 (per-directory READMEs), IDEA-003 (Render Blueprint vs dashboard), IDEA-036 (test runner default DB), IDEA-061 ("25x15" vs "×").

## Wave 1 (next iteration) — 3.00 d

### feature  (1.75 d)
1. **IDEA-051** CARD-159 owner look + plan inputs clip '20' at 390 px (WSJF 5.0) — 0.25 d
2. **IDEA-071** Guide page: worked-example rows and title wording (WSJF 5.0) — 0.75 d
3. **IDEA-046** Book page # column shows list order, not printed number (WSJF 4.0) — 0.5 d
4. **IDEA-061** Player size '25x15' vs '×' (owner call) (WSJF 3.0) — 0.25 d · ⚑ owner decision

### tech-debt  (0.50 d)
1. **IDEA-066** Red on main: test_size_configuration_applied (WSJF 24.0) — 0.25 d
2. **IDEA-067** Stale assertion test_wave3_e2e:366 ('New batch') (WSJF 24.0) — 0.25 d

### ops  (0.75 d)
1. **IDEA-003** Render: adopt Blueprint or record dashboard settings (FIFO) — 0.25 d · ⚑ owner decision
2. **IDEA-013** Empty ?status= disables approved-only default (FIFO) — 0.25 d
3. **IDEA-036** run_admin_tests.sh default DB name vs test guard (FIFO) — 0.25 d · ⚑ owner decision

## Wave 2 — 2.50 d

### feature  (1.75 d)
1. **IDEA-070** Square/landscape trims: no room for proof foot note (WSJF 3.0) — 0.75 d
2. **IDEA-041** Name page-plan error on GET Finalise (500 handler) (WSJF 2.5) — 0.5 d
3. **IDEA-049** Trim refusals worded in cm after inches submission (WSJF 2.0) — 0.5 d

### tech-debt  (0.50 d)
1. **IDEA-007** Validator ERROR: ADR-0025 <-> ADR-0031 circular supersession (WSJF 8.0) — 0.5 d

### ops  (0.25 d)
1. **IDEA-065** CI step 'playwright install chromium' (ADR-0038/R8) (FIFO) — 0.25 d

## Wave 3 — 2.25 d

### feature  (1.50 d)
1. **IDEA-072** Unreadable stored print spec: name the remedy (WSJF 2.33) — 0.75 d
2. **IDEA-073** Store a targeted batch's requested tier (column+migration) (WSJF 1.67) — 0.75 d

### tech-debt  (0.75 d)
1. **IDEA-016** _scheme_of echoes credentials in RuntimeError (CARD-148) (WSJF 8.0) — 0.25 d
2. **IDEA-021** book_proof.render_proof_pdf still writes DeviceRGB (WSJF 6.5) — 0.5 d

## Later waves (summary)

| Wave | Ideas | Days |
|--:|---|--:|
| 4 | IDEA-047, IDEA-057, IDEA-008, IDEA-040 | 2.25 |
| 5 | IDEA-074, IDEA-004 | 2.25 |
| 6 | IDEA-069, IDEA-001, IDEA-006, IDEA-017, IDEA-034, IDEA-044, IDEA-029 | 2.25 |
| 7 | IDEA-009, IDEA-011, IDEA-024, IDEA-014 | 2.25 |
| 8 | IDEA-031, IDEA-035, IDEA-038, IDEA-048, IDEA-054, IDEA-055, IDEA-062 | 2.25 |
| 9 | IDEA-068, IDEA-010, IDEA-059, IDEA-020 | 2.25 |
| 10 | IDEA-012, IDEA-015, IDEA-023, IDEA-026, IDEA-027, IDEA-030 | 2.25 |
| 11 | IDEA-037, IDEA-039, IDEA-043, IDEA-050, IDEA-053, IDEA-060, IDEA-064 | 2.25 |
| 12 | IDEA-058, IDEA-028 | 2.25 |
| 13 | IDEA-075, IDEA-022 | 6.50 |
| 14 | IDEA-025, IDEA-032, IDEA-045, IDEA-052 | 2.00 |
| 15 | IDEA-002, IDEA-019, IDEA-033, IDEA-042 | 2.25 |
| 16 | IDEA-056, IDEA-018 | 1.25 |

⚠ IDEA-075 (online solver, public phase: hosting, URL namespace, puzzle-number mapping) is ~6 d and exceeds any single wave bucket; it lands in wave 13 only because its scope is unconfirmed (score 0.8). If Book 1 carries per-puzzle QR codes it jumps to the top and needs a /forge:architect delta before the layout is final — split it then.

## All ranked ideas

| Rank | Wave | ID | Idea | Cat | Score | Depends |
|--:|--:|---|---|---|--:|---|
| 1 | 1 | IDEA-051 | CARD-159 owner look + plan inputs clip '20' at 390 px | feature | 5.0 | — |
| 2 | 1 | IDEA-071 | Guide page: worked-example rows and title wording | feature | 5.0 | — |
| 3 | 1 | IDEA-046 | Book page # column shows list order, not printed number | feature | 4.0 | — |
| 4 | 1 | IDEA-061 | Player size '25x15' vs '×' (owner call) | feature | 3.0 | — |
| 5 | 1 | IDEA-066 | Red on main: test_size_configuration_applied | tech-debt | 24.0 | — |
| 6 | 1 | IDEA-067 | Stale assertion test_wave3_e2e:366 ('New batch') | tech-debt | 24.0 | — |
| 7 | 1 | IDEA-003 | Render: adopt Blueprint or record dashboard settings | ops | FIFO | — |
| 8 | 1 | IDEA-013 | Empty ?status= disables approved-only default | ops | FIFO | — |
| 9 | 1 | IDEA-036 | run_admin_tests.sh default DB name vs test guard | ops | FIFO | — |
| 10 | 2 | IDEA-070 | Square/landscape trims: no room for proof foot note | feature | 3.0 | — |
| 11 | 2 | IDEA-041 | Name page-plan error on GET Finalise (500 handler) | feature | 2.5 | — |
| 12 | 2 | IDEA-049 | Trim refusals worded in cm after inches submission | feature | 2.0 | — |
| 13 | 2 | IDEA-007 | Validator ERROR: ADR-0025 <-> ADR-0031 circular supersession | tech-debt | 8.0 | — |
| 14 | 2 | IDEA-065 | CI step 'playwright install chromium' (ADR-0038/R8) | ops | FIFO | — |
| 15 | 3 | IDEA-072 | Unreadable stored print spec: name the remedy | feature | 2.33 | — |
| 16 | 3 | IDEA-073 | Store a targeted batch's requested tier (column+migration) | feature | 1.67 | — |
| 17 | 3 | IDEA-016 | _scheme_of echoes credentials in RuntimeError (CARD-148) | tech-debt | 8.0 | — |
| 18 | 3 | IDEA-021 | book_proof.render_proof_pdf still writes DeviceRGB | tech-debt | 6.5 | — |
| 19 | 4 | IDEA-047 | /books rows ~650 px tall at 390 px | feature | 1.5 | — |
| 20 | 4 | IDEA-057 | Player cells ~18 px at 390 px (tap target) | feature | 1.33 | — |
| 21 | 4 | IDEA-008 | CON-020: test 10 pt floor on every interior face | tech-debt | 7.0 | — |
| 22 | 4 | IDEA-040 | finalize_book outer except never logs (CARD-153 F-010) | tech-debt | 6.0 | — |
| 23 | 5 | IDEA-074 | Online solver hint button | feature | 1.33 | — |
| 24 | 5 | IDEA-004 | Fix dead check: refs on mandatory rules (CON-005, INV-*) | tech-debt | 6.6 | — |
| 25 | 6 | IDEA-069 | Upload tests glob shared temp dir (parallel interference) | tech-debt | 6.5 | — |
| 26 | 6 | IDEA-001 | Fixture superseded_by back-pointers (CARD-147 F-007) | tech-debt | 5.0 | — |
| 27 | 6 | IDEA-006 | ADR-0029/R4 check can't test its rule (overlap masks) | tech-debt | 5.0 | — |
| 28 | 6 | IDEA-017 | Pin migrations/env.py URL-not-logged by assertion (CARD-148) | tech-debt | 5.0 | — |
| 29 | 6 | IDEA-034 | db_required hook pings DATABASE_URL before _test guard | tech-debt | 5.0 | — |
| 30 | 6 | IDEA-044 | validate_margins accepts below 0.635 cm minimum | tech-debt | 5.0 | — |
| 31 | 6 | IDEA-029 | Stale 'four members' enum_note + ADR-0025 test narrative | tech-debt | 4.0 | — |
| 32 | 7 | IDEA-009 | NFR + check for the deployed panel's 512 MB memory limit | tech-debt | 4.67 | — |
| 33 | 7 | IDEA-011 | Hand-edit mark not released on revert (CARD-120 F-007) | tech-debt | 4.5 | — |
| 34 | 7 | IDEA-024 | Undrawable row shown between page labels w/o marker | tech-debt | 4.5 | — |
| 35 | 7 | IDEA-014 | Memory mode get_book returns live Book (CARD-136) | tech-debt | 4.0 | — |
| 36 | 8 | IDEA-031 | Concurrent runs share nonogram_test; DROP SCHEMA races | tech-debt | 4.33 | — |
| 37 | 8 | IDEA-035 | diagnose_postgres.sh hardcodes nonogram_poc | tech-debt | 4.0 | — |
| 38 | 8 | IDEA-038 | admin_scripts helper imports private test names | tech-debt | 4.0 | — |
| 39 | 8 | IDEA-048 | Limits box '18.90 in' exceeds the real 18.89 in max | tech-debt | 4.0 | — |
| 40 | 8 | IDEA-054 | Public read instead of _as_readable_grid (CARD-160 F-006) | tech-debt | 4.0 | — |
| 41 | 8 | IDEA-055 | isBoard reads value.cells (mutant survived) | tech-debt | 4.0 | — |
| 42 | 8 | IDEA-062 | Player shows tier 'MEDIUM' upper-case | tech-debt | 4.0 | — |
| 43 | 9 | IDEA-068 | Vacuous trim assertion in DB mode (CARD-120 F-009) | tech-debt | 4.0 | — |
| 44 | 9 | IDEA-010 | Formalise wave-30 card-only behaviours as ACs (FR-043) | tech-debt | 3.33 | — |
| 45 | 9 | IDEA-059 | Investigate flake: save_plan_returns_the_book_to_draft[db] | tech-debt | 3.33 | — |
| 46 | 9 | IDEA-020 | CARD-147 F-006: split the welded digest/colour-space claim | tech-debt | 3.0 | — |
| 47 | 10 | IDEA-012 | Refusal page Planned row reads stored plan (CARD-120 F-008) | tech-debt | 3.0 | — |
| 48 | 10 | IDEA-015 | CARD-118 minors: exc text flash, referrer redirect, utcnow | tech-debt | 3.0 | — |
| 49 | 10 | IDEA-023 | puzzle_section ValueError lands with no traceback (CARD-140) | tech-debt | 3.0 | — |
| 50 | 10 | IDEA-026 | export_book docstring claims every route uses it | tech-debt | 3.0 | — |
| 51 | 10 | IDEA-027 | Rename answer_page_number() test helper (CARD-134) | tech-debt | 3.0 | — |
| 52 | 10 | IDEA-030 | Docstring regression regex misses lowercase guess | tech-debt | 3.0 | — |
| 53 | 11 | IDEA-037 | 'Not reachable' message names only two causes | tech-debt | 3.0 | — |
| 54 | 11 | IDEA-039 | Stale 'Python 3.11+' and docstring (CARD-152 F-007) | tech-debt | 3.0 | — |
| 55 | 11 | IDEA-043 | Double-logged plan tripwire; spy scope (CARD-153 minors) | tech-debt | 3.0 | — |
| 56 | 11 | IDEA-050 | Route tests for below-min trims; wrong alert on New book | tech-debt | 3.0 | — |
| 57 | 11 | IDEA-053 | Player cell bounds to tokens.css (CARD-160 F-004) | tech-debt | 3.0 | — |
| 58 | 11 | IDEA-060 | CARD-163 minors: header comment, Redo aria-disabled | tech-debt | 3.0 | — |
| 59 | 11 | IDEA-064 | Formalise FR-044 drag-axis and pointer-only cell rules | tech-debt | 3.0 | — |
| 60 | 12 | IDEA-058 | Keyboard marking of player cells | feature | 0.8 | IDEA-064 |
| 61 | 12 | IDEA-028 | Image-mode difficulty sweep vs the 90.0 cutoff | tech-debt | 2.67 | — |
| 62 | 13 | IDEA-075 | Online solver public phase: hosting, QR URLs, no solution | feature | 0.8 | — |
| 63 | 13 | IDEA-022 | Arrange labels keyed by id(row): add count check (CARD-140) | tech-debt | 2.5 | — |
| 64 | 14 | IDEA-025 | CARD-145 minors: byte-length assertion, cover RGBA memory | tech-debt | 2.5 | — |
| 65 | 14 | IDEA-032 | Schema-once test fails when run alone (CARD-156 F-006) | tech-debt | 2.5 | — |
| 66 | 14 | IDEA-045 | Remaining one-session-per-puzzle loops (CARD-157 F-004) | tech-debt | 2.5 | — |
| 67 | 14 | IDEA-052 | No-puzzle book: /books offers download /book disables | tech-debt | 2.5 | — |
| 68 | 15 | IDEA-002 | Per-directory READMEs: adopt or drop the docs step | tech-debt | 2.33 | — |
| 69 | 15 | IDEA-019 | CARD-147 dead code: guard, redundant UPDATE, mode default | tech-debt | 2.0 | — |
| 70 | 15 | IDEA-033 | DROP SCHEMA needs public ownership; grants lost (CARD-156) | tech-debt | 2.0 | — |
| 71 | 15 | IDEA-042 | Public read-only gate instead of private BookManager call | tech-debt | 2.0 | — |
| 72 | 16 | IDEA-056 | CARD-161 minors: hint visibility, comments, old test | tech-debt | 2.0 | — |
| 73 | 16 | IDEA-018 | CARD-150 script-test precision (F-003/4/5/7) | tech-debt | 1.67 | — |

## Screened (kept on record, not ranked)

| ID | Idea | Class | Ref | Revival trigger |
|---|---|---|---|---|
| IDEA-005 | system_rules.py --verify-refs resolves node ids | out-of-scope | forge_1 repo | forge_1 accepts the fix (a forge bug report against system_rules.py/adr_integrity is filed and lands) |
| IDEA-063 | Picture name in player page source before solve | duplicate | IDEA-075 | a public player is confirmed separately from IDEA-075's public phase |
| IDEA-076 | Card-text defects for decompose (process) | out-of-scope | forge_1 repo | a forge bug report is filed against decompose/forge:commit and forge_1 accepts it |
| IDEA-077 | Gate hazard: diff against merge base (process) | out-of-scope | forge_1 repo | a forge bug report is filed against the kanban gate and forge_1 accepts it |
| IDEA-078 | Two full-suite lock conventions (process) | out-of-scope | forge_1 repo | a forge bug report is filed against cmd-start-review/dispatcher and forge_1 accepts it |
| IDEA-079 | Forbid concurrent mutation skeptics on one file (process) | out-of-scope | forge_1 repo | a forge bug report is filed against the card brief template and forge_1 accepts it |

## Gantt (next three waves)

```mermaid
gantt
  title Roadmap — waves 1-3
  dateFormat YYYY-MM-DD
  axisFormat %d %b
  section Wave 1 — feature
    IDEA-051 CARD-159 owner look + plan inputs clip ' :idea051, 2026-10-05, 2h
    IDEA-071 Guide page  worked-example rows and titl :idea071, 2026-10-05, 6h
    IDEA-046 Book page # column shows list order, not :idea046, 2026-10-05, 4h
    IDEA-061 Player size '25x15' vs '×' (owner call) :idea061, 2026-10-05, 2h
  section Wave 1 — tech-debt
    IDEA-066 Red on main  test_size_configuration_app :idea066, 2026-10-05, 2h
    IDEA-067 Stale assertion test_wave3_e2e 366 ('New :idea067, 2026-10-05, 2h
  section Wave 1 — ops
    IDEA-003 Render  adopt Blueprint or record dashbo :idea003, 2026-10-05, 2h
    IDEA-013 Empty ?status= disables approved-only de :idea013, 2026-10-05, 2h
    IDEA-036 run_admin_tests.sh default DB name vs te :idea036, 2026-10-05, 2h
  section Wave 2 — feature
    IDEA-070 Square/landscape trims  no room for proo :idea070, 2026-10-08, 6h
    IDEA-041 Name page-plan error on GET Finalise (50 :idea041, 2026-10-08, 4h
    IDEA-049 Trim refusals worded in cm after inches  :idea049, 2026-10-08, 4h
  section Wave 2 — tech-debt
    IDEA-007 Validator ERROR  ADR-0025 <-> ADR-0031 c :idea007, 2026-10-08, 4h
  section Wave 2 — ops
    IDEA-065 CI step 'playwright install chromium' (A :idea065, 2026-10-08, 2h
  section Wave 3 — feature
    IDEA-072 Unreadable stored print spec  name the r :idea072, 2026-10-11, 6h
    IDEA-073 Store a targeted batch's requested tier  :idea073, 2026-10-11, 6h
  section Wave 3 — tech-debt
    IDEA-016 _scheme_of echoes credentials in Runtime :idea016, 2026-10-11, 2h
    IDEA-021 book_proof.render_proof_pdf still writes :idea021, 2026-10-11, 4h
```

## Next step

No feature in waves 1-3 needs new architecture except IDEA-064 (formalise FR-044's unstated player rules) and the model-hygiene items (IDEA-004, -006, -007, -008, -009, -010, -029) — one `/forge:architect` session covers them. Everything else can be carded directly (`/forge:kanban quick`, or a decompose of a small handoff).
