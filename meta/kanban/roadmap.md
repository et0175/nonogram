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

## Wave 3 — DONE 2026-11-20 (board wave 82)

Merged: CARD-232 (`34938a8d`), CARD-486 (`5d62d5ae`), CARD-487 (`f6af67a6`), CARD-488 (`6fa650e2`). Wave close on `main` in two runs over the same code (only meta/docs changed between them): the FULL merge gate of `d50f0bde` (all of wave 3 plus the landing-page fix), 10661 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 13 wave_close_only deselected; then `make test-marked`, 13 passed. **The landing-page red carried since `c505bd44` is fixed** (`d50f0bde`: the book page restored its scroll before the jump box was shown, so the browser clamped it) and published 2026-11-20. Wave 3's player changes published the same day (`nonogram-studio-i0n5nyn31`, then `48qnaa31w`).


Cut against main on 2026-11-19. Closed at the cut rather than carded: **IDEA-069** (done by CARD-474), **IDEA-107** (superseded by `make test-gate`). Not carded: **IDEA-178** (owner layout call; reachable only on a band of 3 mm or less, which no stored profile has), **IDEA-106** (repo-wide guard audit: open-ended instrument work, held for the owner's say under the cut bar).

### feature  (1.00 / 1.50 d)
- **CARD-232** (IDEA-168 folded in) Solution tiles: what is left — the packing doc and its test (AC-8), the old 6-up wording (AC-9), CARD-202's dormant minors — 2c
- **CARD-486** (IDEA-149) Hint minors, verified first, fixed only where live — 1c

### tech-debt  (0.75 / 1.20 d)
- **CARD-487** (IDEA-006) ADR-0029/R4's check tests its rule — 1c
- **CARD-488** (IDEA-034, IDEA-017, IDEA-083, IDEA-100) Four small test-side gaps — 2c

## Wave 14 — DONE 2026-11-23 (board wave 93)

Five cards merged, all certified: CARD-527 (`83da95e2`, 9.5, net −1), CARD-528 (`4a687d3d`, 9.3, net +17), CARD-530 (`d978bd1c`, 9.5, net 0), CARD-529 (`bacbe8e7`, 9.5, net 0), CARD-531 (`57ae3ddc`, 9.5, net 0). Net tests +16. Wave close: `make test-wave-close` on main at `73afd872`, in a detached worktree pinned to that commit, 10682 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, 34 min. Two earlier close runs are void: owner-session merges landed on main while they ran (2d64b937, then c4d81904 inside the run's own worktree), so each tested a mix of trees. Their reds passed on the tip. The first also found one real red: 7a21d0ba's favicon.png was in no package-data glob and had no impact-set rule, which became CARD-531, and on the owner's word it also ships the generator form's metadata.js (review F-001). No product change of this wave's own, nothing to publish. Recorded, not carded: CARD-528 F-201/F-202, CARD-530 F-005, CARD-529 F-001, CARD-531 F-005.

### As cut

Cut against main on 2026-11-23 on the owner's "pick a no-decision wave from the backlog", while CARD-526 waits for held-out pictures. Three test-tooling items whose premises were re-checked on main at the cut: IDEA-181 (the page-isolation glob still reads only `tests/test_puzzle_solver_*.py`), IDEA-193 (`impact_set.py CLAUDE.md` still prints FULL), IDEA-212 (`_set_once` is still an unbounded `lru_cache` returning a view). IDEA-202 was considered and left: its fix (resolving every declared check id to a definition) is larger than one card, and `tests/test_check_ref_resolution.py` already reports its dead refs. CARD-529 starts when a slot frees (cap 2). Owner rulings 2026-11-23: IDEA-105 screened (Book 1 finalised), IDEA-227 screened (leave it reported).

### tech-debt
- **CARD-527** (IDEA-181) Every browser-test file must declare its page isolation — 1c
- **CARD-528** (IDEA-193) The impact selector resolves CLAUDE.md and other root files to their readers — 1c
- **CARD-529** (IDEA-212) The glyph cache stops keeping whole uncropped arrays alive — 1c
- **CARD-530** (added 2026-11-23, P1) The browser-family registry records the three tests Player QA v3 renamed (main red since 8f799d5b; blocks every merge gate) — 1c
- **CARD-531** (added 2026-11-23, P1) The admin tab icon ships in the wheel (the first wave close found 7a21d0ba's favicon.png in no package-data glob) — 1c

## Wave 13 — DONE 2026-11-22 (board wave 92)

One card merged: CARD-525 (`2f53bd60`), on the owner's ruling ("merge it now") after review 3 at 8.5, not certified; its AC-3 item 1 was corrected by the orchestrator to carry the `smooth_corr >= 0.96` floor (F-011). Wave close: `make test-wave-close` on `main` at `ce3835e0`, 10664 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, 32 min. Net tests +1 (the experiment script's test). No product change, nothing to publish. Result: on easy puzzles only, a stricter threshold kept only above the floor takes fixtures 69.7% -> 59.0% easy and the owner's folder 80.7% -> 70.3%; the rule was chosen post hoc. Dithering is not guarded by the floor (it adds checkered or scattered cells). Owner ruling 2026-11-22: build threshold, then dithering -> CARD-526 (IDEA-228), ready, unscheduled; it needs a dithering noise check and at least 10 held-out pictures. Recorded, not carded: the line-art warning (ink share < 0.230 and enclosed > 0.031) fits 6 failing fixtures from about 2100 candidate rules and has 1 held-out failing picture.

### As cut

Cut against main on 2026-11-22 on the owner's "yes, start wave 13", while wave 12's last card (CARD-524) is still open. One measured experiment on the picture-to-grid pipeline, following CARD-517 (70-81% of real-picture puzzles easy whatever the cutoff; about 1 request in 6 produces no puzzle). It changes no product behaviour; fix cards follow only from its numbers and the owner's eye on its renders.

### feature
- **CARD-525** Where picture puzzles lose their difficulty and fail to generate: a measured experiment — 2c

## Wave 12 — DONE 2026-11-22 (board wave 91)

Three cards merged: CARD-522 (`7110c1bc`, 9.5 cycle 2), CARD-523 (`a875c54e`, 9.0 cycle 1), CARD-524 (`9ad3fd2c`, 9.0 cycle 1). Wave close: `make test-wave-close` on `main` at `f5620362`, 10663 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, 38 min (CARD-525's experiment ran on the same machine). Net tests +1 (CARD-522's no-database refusal test). PUBLISHED 2026-11-22 after CARD-523 (`nonogram-studio-rd5i6sefk`, admin.css only, public board 0/0 on solve); CARD-524's admin.css is not yet published and changes nothing a public player sees. CARD-522 reaches Render only on the owner's next deploy. Findings: the public player does show Show grid once solved (the CARD-511 record listed only the unsolved toolbar; corrected in docs/deploy/player.md). Recorded, not carded: the import-failure refusal names no cause (CARD-522 cycle 2 F-001); Show grid is tabbed last though it sits in Line's slot, and the admin-only scoping relies on public mode removing Check (CARD-523 F-001/F-002); `_BANNER_LINES` would read a hidden label as shown, and a long second word still leaves line 1 as "Solved! The " (CARD-524 F-001/F-003, the latter the owner's call).


### As cut

Cut against main on 2026-11-22 on the owner's "let's take your suggestions for first 4 ideas". Owner rulings: the 90.0 medium/hard cutoff stays as it is for picture puzzles (CARD-517's measurement; no card); IDEA-226, refuse to start on the deployed server without a database; IDEA-225, Show grid takes Line's place once solved; IDEA-221, a long first word may break mid-word so the solved name starts on line 1. CARD-524 waits for CARD-523 (same stylesheet and sweep file). Still the owner's: IDEA-227 (kill-matrix per-tree lock) and IDEA-105 (Finalise guide preview).

### tech-debt
- **CARD-522** (IDEA-226) The deployed panel refuses to start without a database — 1c

### feature
- **CARD-523** (IDEA-225) On narrow phones the board stays put on solve: Show grid takes Line's place — 1c
- **CARD-524** (IDEA-221) A long first word in the solved name starts on line 1, breaking mid-word — 1c (after CARD-523)

## Wave 11 — DONE 2026-11-22 (board wave 90)

Four cards merged: CARD-518 (`715d84fe`, 9.0 cycle 1), CARD-519 (`849f06d3`, 9.0 cycle 2), CARD-521 (`5815bf05`, 9.0 cycle 2), CARD-520 (`ead96b76`, 9.0 cycle 3). Wave close: `make test-wave-close` on `main` at `f8c1fd5b`, 10662 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, 32 min. Net tests +1 (CARD-520's browser test). Nothing reaches the public player, so no publish. CARD-520 was added mid-wave on the owner's say, from CARD-519 review 1 F-002: nothing caught CARD-159's inches-trim bug coming back. Two review cycles showed a static "no script writes a bound" check could not be made complete, so cycle 3 measured the page in Chromium instead. Recorded, not carded: the browser test does not assert the field kept the typed value, nor wait for asynchronous work (CARD-520 cycle 3 F-001/F-002); AC-427 claims less than its test, AC-432's book-page link clause does not discriminate, AC-430's "beside" is not asserted as placement (CARD-519 cycle 2 F-101..F-103), and AC-423 can now be widened to the cm-opened page that CARD-520 covers; tests/README.md omits CARD-508's session lock among the guards and the per-worktree caveat of an exported TEST_DATABASE_URL (CARD-521 cycle 2 F-101/F-102); the kill matrix's key retirement also hides a different-bytes write between readings, and the trim corpus has no quoted value (CARD-518 F-001/F-002).


### As cut

Cut against main on 2026-11-22 on the owner's "start the no-decision wave 11": nothing in it waits on an owner decision. Two cards now at the cap; CARD-520 (the CARD-159 regression test, added on the owner's say) took the slot CARD-518 freed; CARD-521 (IDEA-002, tests/README.md) follows. Not carded: IDEA-221, 225, 226, 227 and 105 (owner decisions), IDEA-125/126 (screened by the owner).

### tech-debt
- **CARD-518** Two one-line follow-ups from wave 10's reviews (kill matrix stale inode key; the guard's trim held equal to the app's) — 1c
- **CARD-519** (IDEA-010) Write the wave-30 book behaviours into requirements.yml as acceptance criteria — 2c
- **CARD-520** A page opened in centimetres admits an inches trim: a test that catches CARD-159's bug coming back (owner's "yes, add a card", after CARD-519 review 1 F-002) — 1c
- **CARD-521** (IDEA-002) tests/README.md describes the suite as it is today — 1c

## Wave 10 — DONE 2026-11-22 (board wave 89)

Two cards merged: CARD-517 (`b947235b`, 9.0 cycle 1), CARD-315 (`32f92558`, 9.0 cycle 2). Wave close: `make test-wave-close` on `main` at `20104860`, 10661 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, 35 min. Net tests +1 (CARD-517's image-mode test). Nothing reaches the public player, so no publish. Findings: on real pictures the 90.0 cutoff gives 70-81% easy, 13-19% medium, 6-12% hard; easy is set by the pictures, and among non-trivial puzzles 90 is the cutoff nearest the plan's 2:1 (the split rests on about 15 pictures); no change proposed, the cutoff stays unless the owner says otherwise. The kill matrix now refuses a run when anything else writes a file it planted. Owner ruling 2026-11-22: IDEA-125/126 (the public make-your-own-puzzle QR) screened out for now, because arbitrary pictures too often give an unsolvable or unrecognisable puzzle. Recorded: **IDEA-227** (two kill-matrix runs in one tree; per-tree lock is the owner's call). Carried to wave 11: CARD-315 review 2 F-001/F-002 and CARD-515 F-202 (CARD-518).


### As cut

Cut against main on 2026-11-22 on the owner's "yes, start wave 10", as recommended: CARD-315 (the kill matrix's plant window, ready since wave 66 and unblocked by CARD-516) and IDEA-028 (the 90.0 cutoff measured against picture puzzles; measurement only, the cutoff is the owner's decision). Not carded: IDEA-221, 225, 226 and 105 (owner decisions), IDEA-125/126 (design first), IDEA-010 and IDEA-002.

### tech-debt
- **CARD-315** The kill matrix's plant window is guarded for every consumer — 2c
- **CARD-517** (IDEA-028) Measure the 90.0 medium/hard cutoff against picture-made puzzles — 2c

## Wave 9 — DONE 2026-11-22 (board wave 88)

Two cards merged: CARD-516 (`fe41d449`, 9.0 cycle 1), CARD-515 (`b79db921`, 9.5 cycle 2). Wave close: CARD-515's second merge gate answered FULL on `92353558` (main with CARD-516 merged), 10660 passed, 30 skipped (unarmed), 1 xfailed, 0 failed, all 13 marked tests run and nothing deselected, 31 min; `src/`, `tests/`, `player/` and `scripts/` on `main` after the merge are identical to that tree (`git diff --stat` empty), so no second full run was made. Net tests +1 (CARD-515's absent/blank parametrisation). Nothing reaches the public player, so no publish: a build from `9496e8f5` on 2026-11-21 matched production byte for byte (176 files). CARD-515's first FULL gate was red: `tests/database_guard.py` imported `trimmed_url` from `nonogram`, and `test_suite_profile`'s sandbox, which copies tests/ but not src/, reached another checkout's `nonogram`; fixed by trimming inline in the test tree. Recorded: **IDEA-226** (a blank DATABASE_URL boots the panel in in-memory mode; owner decision). Recorded, not carded: no test holds `database_guard._trimmed` equal to `session.trimmed_url` (CARD-515 F-202); the kill matrix's value rule over-marks non-spawning uses such as `subprocess.DEVNULL` (CARD-516 F-001); its AC-7 arms are now held by their wording (CARD-516 F-002).


### As cut

Cut against main on 2026-11-21 on the owner's "yes, start wave 9", which took the recommendation: IDEA-224 (trim, not refuse, as the owner's ruling) and one bundle of the kill matrix's own weak anchors and controls. Not carded: IDEA-221 and IDEA-225 (each needs the owner's choice of look), IDEA-125/126 (feature, needs design first), IDEA-111 (forge-plugin defect), IDEA-105 (owner to specify), CARD-315 (ready; touches the same two kill-matrix files, so it waits for CARD-516).

### tech-debt
- **CARD-515** (IDEA-224) A DATABASE_URL with surrounding whitespace connects to the database it names — 1c
- **CARD-516** (IDEA-182, 184, 185, 187, 188) The kill matrix's own anchors and controls hold what they claim — 2c

## Wave 8 — DONE 2026-11-21 (board wave 87)

Four cards merged: CARD-513 (`2fdbf14d`, 9.5 cycle 2), CARD-511 (`ee9b949f`, 9.5 cycle 1), CARD-514 (`187d765f`, 9.5 cycle 1), CARD-512 (`26ca4e7e`, 9.5 cycle 1). Wave close: CARD-512's merge gate answered FULL on `599ccf16` (main with the other three cards merged), 10659 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 10690 collected, nothing deselected, 44 min; `src/`, `tests/`, `player/` and `scripts/` on `main` after the merge are identical to that tree (`git diff --stat` empty), so no second full run was made. Net tests +1 over the wave (CARD-513's Finalise-download spy test). PUBLISHED 2026-11-21 on the owner's second "please publish player": CARD-511's `admin.css` (production `nonogram-studio-og58mwtjc`); a real solve at 600 x 900 moved the public board by 0 before and after, because the public toolbar has no Show grid. Findings: CARD-514 closed IDEA-148 as not reachable as reported (the solver-page test reads SQLite whatever DATABASE_URL holds); CARD-512's stricter lock refuses a child pytest started through a forking shell or a grandchild (none today). Recorded: **IDEA-225** (327-339 and 421-451 px still move the board on solve; owner decision). Recorded, not carded: a direct POST still downloads a no-puzzle interior (CARD-513 F-004); a no-puzzle row is 234 px tall at 390 px (CARD-513 cycle 2 F-001); `_held_by_parent`'s database clause has no committed control (CARD-512 F-002); one unexplained 1-in-49 failure of the banner class in review (CARD-512 F-001, not seen at the gate).

### As cut

Cut against main on 2026-11-21 on the owner's "yes, start wave 8". The feature bucket's top items still wait on the owner (IDEA-105, 125, 126, 178; IDEA-221 and IDEA-224 asked at the wave-7 close), so the wave takes the one player defect wave 7 measured (IDEA-223), its two test-instrument follow-ups, and the next tech-debt band (WSJF 2.31 and 1.92), bundled by area. Not carded: IDEA-028 (the image-mode difficulty sweep, its own wave), IDEA-111, 106, 112, 010 (as at wave 7), and the process items.

### feature
- **CARD-511** (IDEA-223) At 600x900 the board no longer moves when a puzzle is solved — 1c

### tech-debt
- **CARD-512** (IDEA-220, IDEA-222) The session lock's escape hatch; test_wraps' paint check — 1c
- **CARD-513** (IDEA-052, IDEA-043) A no-puzzle book's download; the plan tripwire logged twice — 1c
- **CARD-514** (IDEA-045, IDEA-148) The last one-session-per-puzzle loops; the largest-board flake — 2c

## Wave 7 — DONE 2026-11-21 (board wave 86)

Four cards merged: CARD-507 (`837cb27f`, 9.5 cycle 3), CARD-508 (`f2f4a420`, 9.5 cycle 1), CARD-509 (`965e5cda`, 9.5 cycle 1), CARD-510 (`67b434d3`, 9.5 cycle 1). Wave close: `make test-wave-close` on `main` at `1fa32b72`, 10658 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 43 min; net tests 0 over the wave (10689 both closes). PUBLISHED 2026-11-21 on the owner's "please publish player": CARD-507 and CARD-506 reach the public player (production `nonogram-studio-6p2wxvv2l`, rollback `nonogram-studio-48qnaa31w`; docs/deploy/player.md). CARD-510 found three of CARD-276's published kill counts too low (N12b 5 → 6, N18 1 → 6 on `ac479658`; N8h 1 → 5 on `f794d5a8`): its selection was narrower than the file and unrecorded; every node it named still reds. CARD-510's gate caught a page wording of mine (a backticked `--text-xs` in docs/deploy/player.md reads as an assembly-helper flag), fixed on main in `98f79a43`. Recorded, not carded: **IDEA-220** (a stale `NONOGRAM_TEST_DB_SESSION_LOCK` disables the session lock), **IDEA-221** (a no-space or long-first-word solved name starts on line 2; owner decision), **IDEA-222** (test_wraps' elementsFromPoint check is defeated by `pointer-events: none`), **IDEA-223** (the 600x900 board shift on solve, pre-existing), **IDEA-224** (trailing whitespace in DATABASE_URL passes into the db name; owner decision).

### As cut

Cut against main on 2026-11-20 on the owner's "go with option 2, start wave 7". The owner decided IDEA-218 (option 2: the compact two-line `--text-xs` clamp on the solved banner at every width). The rest is the test-database faults most likely to red a gate for no code reason, and two small leftovers. IDEA-215 added the same day on the owner's "add IDEA-215 to this wave too" (CARD-510). Not carded: IDEA-111, 106, 112, 010 (as at wave 6).

### feature
- **CARD-507** (IDEA-218) A long solved name no longer moves the desktop board — 1c

### tech-debt
- **CARD-508** (IDEA-031, 032, 140, 174) Test-database hygiene — 2c
- **CARD-509** (IDEA-219, IDEA-094) text.pdf in the cwd; whitespace around DATABASE_URL — 1c
- **CARD-510** (IDEA-215) Re-fire CARD-276's six mutant cells, or declare them — 1c

## Wave 6 — DONE 2026-11-20 (board wave 85)

Five cards merged: CARD-502 (`bda13f6f`, 9.5 cycle 1), CARD-503 (`8578049e`, 9.5 cycle 1), CARD-504 (`38d9eb58`, 9.7 cycle 2), CARD-505 (`916ee1bc`, 9.4 cycle 1), CARD-506 (`be1da7ae`, 9.5 cycle 1). Wave close: `make test-wave-close` on `main` at `72c2a3ff`, 10658 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 33 min. Net tests -22 over the wave (CARD-505 deleted 24 stub tests; CARD-502 +2). Not published: CARD-506's token move reaches the public player, but a build from base and HEAD differs in no measured value. Findings: CARD-503 found FR-044's "board cells are pointer-only" premise false (keyboard play exists since 2026-11-17, untested); recorded **IDEA-218** (a long solved name moves the desktop board, owner decision) and **IDEA-219** (pdf_vector writes text.pdf into the working directory). Recorded, not carded: EC-029 still says "explicit move" (CARD-503 F-002); two app.py sites title-case tier values instead of Tier.label (CARD-504 F-005); the guide strip's separator spells out the 28% mix (CARD-506 F-004).

### As cut

Cut against main on 2026-11-20 on the owner's "please start the next wave". The feature bucket still has nothing workable (IDEA-105, 125, 126, 178 wait on the owner), so the wave is the next tech-debt band (WSJF 2.31), bundled by area. Premises spot-checked against main the same day; each card re-verifies its items before changing anything. CARD-502 also takes CARD-496 F-003 (the status route's raw ValueError text), recorded at the wave-5 close. Not carded: IDEA-111, 106, 112, 031, 215, 010 (as at wave 5); the other three wave-5 leftovers stay recorded.

### tech-debt
- **CARD-502** (IDEA-138, IDEA-023, IDEA-050, CARD-496 F-003) The admin's remaining error paths — 2c
- **CARD-503** (IDEA-159, IDEA-167, IDEA-064) Registry wording owed: INV-009, AC-343, FR-044's two rules — 1c
- **CARD-504** (IDEA-026, 027, 030, 037, 039, 102, 134, 145, 197) Nine stale texts — 2c
- **CARD-505** (IDEA-172, IDEA-194, IDEA-208) Three test-instrument costs — 2c
- **CARD-506** (IDEA-053, 060, 095, 147, 151, 157, 161, 166) Player and admin-CSS minors — 2c

## Wave 5 — DONE 2026-11-20 (board wave 84)

Six cards merged: CARD-496 (`2ee32a1d`, 9.5 cycle 1), CARD-497 (`7a055f48`, 9.5 cycle 2), CARD-498 (`6ffb60f2`, 9.5 cycle 1, with the owner's AC-292 rewording), CARD-499 (`d2d00b91`, 9.6 cycle 2), and two the owner asked for during the wave: CARD-500 (`618d20de`, 9.8 cycle 2: after a refused Print setup save the edited marks follow the submitted plan) and CARD-501 (`7bda4cbd`, 9.5 cycle 1: typed cells judged against the submitted split). Wave close: `make test-wave-close` on `main` at `cec8c5a0`, 10680 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 33 min. No public-player file changed. Recorded, not carded (reviewers' out-of-scope findings): `update_book_status` still shows any ValueError's raw text unlogged (CARD-496 F-003); on Postgres `books.created_at` is the server's local time while `updated_at` is naive UTC (CARD-496 F-004); requirements.yml's NFR-005 labels are falsely-alive class names, so it and trace.yml name different tests for the same ACs (CARD-498 F-004); an edit whose value a later split's prefill happens to equal stays edited until retyped twice (CARD-501 F-003, CARD-120's left-alone rule).

### As cut

Cut against main on 2026-11-20, every premise re-read the same day. The feature bucket is still empty of workable items (IDEA-105 waits for the owner to say what the guide preview needs; IDEA-178, IDEA-125/126 are owner calls), so the wave is tech-debt. **IDEA-059 closed at the cut**: a flake watch with no fix, its likeliest cause removed by CARD-244 and no recurrence since. Not carded: IDEA-031 (skipped once as CARD-378), IDEA-106/112 (owner's say), IDEA-111 (forge-plugin defect), IDEA-215 (a re-fire of old mutants, no product effect), IDEA-010 (formalising shipped behaviour as ACs; next registry wave).

### tech-debt
- **CARD-496** (IDEA-101, IDEA-015) The book routes' error paths: Finalise's other status refusals, the proof route, the referrer redirects, utcnow — 2c
- **CARD-497** (IDEA-012) The Print setup refusal page shows the submitted plan — 1c
- **CARD-498** (IDEA-216) The registry's 11 honest-dead check refs — 2c
- **CARD-499** (IDEA-113, IDEA-196) Two test instruments' blind spots — 2c

## Wave 4 — DONE 2026-11-20 (board wave 83)

Five cards merged: CARD-489 (`0c3c6a0c`, 9.8 cycle 2), CARD-490 (`72813084`, 9.6 cycle 2), CARD-491 (`4a654343`, 9.3 cycle 2), CARD-492 (`31cfe144`, 9.3 cycle 1), CARD-493 (`8d589e5b`, 9.6 cycle 1). Wave close: `make test-wave-close` on `main` at `38ba72b2`, 10677 passed, 30 skipped (29 DATABASE_URL unset, 1 setrlimit), 1 xfailed, 0 failed, 40 min. Net tests +3 over the wave. No public-player file changed, so nothing to publish. **Added after the close, on the owner's requests:** CARD-494 (`2f2b6d9e`, 9.5 cycle 2: the arrange page's "page N, continued" label and warning-tinted marker; the last guess-is-a-tier passages) and CARD-495 (`cca388ba`, 9.6 cycle 2: a stored "guess" row is Hard in the database filter; the arrange row fits a phone); full suite on `main` at `1010f833` afterwards, 10677 passed, 30 skipped, 0 failed, 33 min. Owner's open questions (both since answered and built as CARD-494/495): CARD-490 F-003 (the arrange page's repeated page label and the marker's styling); three stale "guess is a tier" passages outside CARD-491's files (src/nonogram/export/__init__.py, src/nonogram/admin/puzzle_review.py, docs/GENERATION_ALGORITHM.md §7), recorded on that card. Recorded, not carded: CARD-489 F-003 (no test pins which split the plan reference uses on a count+split change), CARD-493 F-003 (a book_proof.py comment cites the refused 8.25 in trim).

### As cut

Cut against main on 2026-11-20, every premise re-read the same day. The feature bucket has nothing workable left: IDEA-178 is an owner layout call and IDEA-125/126 are owner questions, so its budget rolls over to tech-debt. **IDEA-009 shrank at the cut**: CARD-145 and CARD-237 already built the memory checks; only the NFR naming them is missing, so it joins the registry card. Not carded: IDEA-031 (skipped once already as CARD-378), IDEA-106/112 (held for the owner's say), IDEA-111 (forge-plugin defect).

### tech-debt  (≈ 2.6 d, feature roll-over included)
- **CARD-489** (IDEA-011, IDEA-014) Two book_manager leaks: hand-edit mark on a count change; memory mode's live Book — 2c
- **CARD-490** (IDEA-024) The arrange page marks a puzzle that will not print — 1c
- **CARD-491** (IDEA-009, IDEA-029, IDEA-081) Registry and docs: the memory-cap NFR, Tier's member count, the scripts README — 1c
- **CARD-492** (IDEA-035, IDEA-038, IDEA-054, IDEA-062, IDEA-044) Five small code-hygiene items — 2c
- **CARD-493** (IDEA-068, IDEA-093, IDEA-097) Three test minors — 1c

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
