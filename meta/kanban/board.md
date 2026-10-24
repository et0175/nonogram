# Kanban Board

_Updated: 2026-10-23 (decompose: CARD-282..CARD-285 added — the public player phase; same day: the architect delta landed as ADR-0041 / FR-045 / COMP-011, CON-021 amended, and CARD-282/283 unblocked — all four READY, chain 282 → 283 → 284 → 285)_  ·  <!-- forge:run wave=54 mode=interactive concurrency=2 -->

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| pre-field | 43 done cards with no `Wave:` field -- pre-field history, scattered (CARD-018…CARD-203) | ✅ done |
| 1 | CARD-001 P1, CARD-068 P2, CARD-072 P2, CARD-073 P1, CARD-074 P1, CARD-075 P2, CARD-076 P1, CARD-077 P2, CARD-078 P3, CARD-079 P2, CARD-080 P1, CARD-082 P2, CARD-083 P2, CARD-084 P3, CARD-085 P1, CARD-086 P2, CARD-087 P2, CARD-088 P1, CARD-089 P2, CARD-090 P2, CARD-091 P2, CARD-092 P3, CARD-093 P3, CARD-094 P3, CARD-095 P3, CARD-096 P2, CARD-097 P2, CARD-098 P2, CARD-099 P2, CARD-100 P1, CARD-101 P1, CARD-102 P2, CARD-103 P2, CARD-104 P2, CARD-105 P3, CARD-106 P2, CARD-107 P1, CARD-108 P2, CARD-109 P1 | ✅ done |
| 2 | CARD-002 P1, CARD-003 P1, CARD-035 P2 | ✅ done |
| 3 | CARD-004 P1, CARD-038 P2, CARD-039 P3, CARD-041 P2, CARD-042 P2, CARD-043 P2, CARD-044 P1 | ✅ done |
| 4 | CARD-005 P1 | ✅ done |
| 5 | CARD-006 P1, CARD-007 P1 | ✅ done |
| 6 | CARD-008 P2, CARD-009 P1, CARD-011 P2, CARD-012 P1, CARD-013 P1 | ✅ done |
| 7 | CARD-010 P1 | ✅ done |
| 8 | CARD-014 P2 | ✅ done |
| 9 | CARD-015 P2 | ✅ done |
| 10 | CARD-016 P2 | ✅ done |
| 11 | CARD-017 P3 | ✅ done |
| 12 | CARD-019 P1 | ✅ done |
| 13 | CARD-020 P1, CARD-022 P1 | ✅ done |
| 14 | CARD-021 P2 | ✅ done |
| 16 | CARD-023 P1, CARD-024 P1, CARD-025 P2 | ✅ done |
| 17 | CARD-026 P1 | ✅ done |
| 18 | CARD-027 P1 | ✅ done |
| 19 | CARD-028 P2 | ✅ done |
| 20 | CARD-113 P1, CARD-119 P1, CARD-135 P1 | ✅ done |
| 21 | CARD-114 P1, CARD-120 P1 | ✅ done |
| 22 | CARD-115 P1, CARD-122 P1, CARD-124 P1, CARD-125 P2, CARD-133 P2 | ✅ done |
| 23 | CARD-116 P1, CARD-121 P1 | ✅ done |
| 24 | CARD-117 P1, CARD-123 P1, CARD-126 P2, CARD-136 P1, CARD-137 P1 | ✅ done |
| 25 | CARD-118 P1, CARD-127 P2, CARD-130 P2, CARD-134 P2, CARD-138 P1 | ✅ done |
| 26 | CARD-128 P2, CARD-131 P2, CARD-132 P3, CARD-139 P1, CARD-140 P1, CARD-141 P2, CARD-142 P1, CARD-144 P2, CARD-145 P0 | ✅ done |
| 27 | CARD-129 P2, CARD-143 P2, CARD-146 P2, CARD-147 P2, CARD-148 P1, CARD-149 P2 | ✅ done |
| 28 | CARD-150 P2, CARD-151 P2, CARD-152 P2 | ✅ done |
| 29 | CARD-153 P1, CARD-154 P2, CARD-155 P3, CARD-156 P2 | ✅ done |
| 30 | CARD-157 P2, CARD-158 P2, CARD-159 P2 | ✅ done |
| 31 | CARD-160 P2, CARD-161 P2, CARD-162 P2, CARD-163 P2 | ✅ done |
| 32 | CARD-164 P1, CARD-165 P2, CARD-166 P2, CARD-167 P2, CARD-168 P2 | ✅ done |
| 33 | CARD-169 P1, CARD-170 P1, CARD-171 P2, CARD-172 P2, CARD-173 P2, CARD-174 P2, CARD-175 P3, CARD-176 P2 | ✅ done |
| 34 | CARD-177 P1, CARD-178 P2, CARD-179 P2, CARD-180 P3, CARD-181 P3, CARD-182 P3, CARD-183 P3, CARD-184 P2, CARD-186 P2, CARD-188 P2 | ✅ done |
| 35 | CARD-185 P2, CARD-187 P3, CARD-189 P2, CARD-190 P2, CARD-191 P2, CARD-192 P2 | ✅ done |
| 36 | CARD-193 P2, CARD-194 P2, CARD-195 P3, CARD-196 P2 | ✅ done |
| 37 | CARD-197 P2, CARD-198 P2, CARD-199 P2 | ✅ done |
| 38 | CARD-204 P2, CARD-205 P1, CARD-211 P2, CARD-212 P2, CARD-214 P1, CARD-221 P1 | ✅ done |
| 39 | CARD-217 P1 | ✅ done |
| 40 | CARD-234 P2, CARD-235 P1, CARD-237 P1 | ✅ done |
| 41 | CARD-238 P1 | ✅ done |
| 42 | CARD-213 P2, CARD-228 P1, CARD-239 P2, CARD-240 P3 | ✅ done |
| 43 | CARD-241 P1, CARD-242 P2 | ✅ done |
| 44 | CARD-222 P1, CARD-236 P2, CARD-243 P2 | ✅ done |
| 45 | CARD-223 P1, CARD-244 P1, CARD-248 P1 | ✅ done |
| 46 | CARD-224 P1, CARD-245 P1, CARD-246 P1 | ✅ done |
| 47 | CARD-250 P2, CARD-251 P2 | ✅ done |
| 48 | CARD-225 P1, CARD-247 P2, CARD-252 P1, CARD-253 P2 | ✅ done |
| 49 | CARD-254 P2, CARD-255 P1 | ✅ done |
| 50 | CARD-256 P1, CARD-257 P2 | ✅ done |
| 51 | CARD-258 P1, CARD-260 P1 | ✅ done |
| 52 | CARD-206 P2, CARD-259 P2 | ✅ done |
| 53 | CARD-261 P2, CARD-262 P2 | ✅ done (CARD-261 `ac63e17a`; CARD-262 `faea50a5` — escalated at cycle 2/3, re-entered on the owner's declare route, landed) |
| 54 | CARD-262 P2 ✅ `faea50a5`, CARD-270 P2 ✅ `64da37f6`, CARD-264 P2 ✅ `066ddc1f` | ▶ active. **CARD-264's escalation CLOSED 2026-10-23 — owner chose option 1:** fix the four controls-that-cannot-fail (S-1..S-4) the 8h spot-check found, then a **re-entry cycle 4** to certify, then re-gate and merge. **Cycle 4 then scored 7.65 NOT CERTIFIED — the fix round introduced two defects of the card's own kind — and the owner chose one more fix + cycle 5.** Fix 4 decided the declared-miss tables' semantics before touching an entry and applied them tree-wide (216 line-level variants, 0 survived; 9/9 mutants killed), committed `8727e519` and **pre-gated** (7/7 named tests by node id, 167+166 whole-file, 2 of 9 mutants re-derived at the gate). The gate passed (8931 executed, 0 failed) and **cycle 5 scored 7.6, NOT CERTIFIED — 2 important, both introduced by fix 4.** The mechanism itself held under independent re-derivation (197-variant sweep, 0 survivors; all five exemption reasons true; m-1 sound; the round's disagreement with its brief adjudicated in the round's favour) — both findings are in the *claims about* it. **⚠ improvement stalled** and **family regression at streak 2** both fire, neither premise failing, so this is with the owner. Aggregate round counter **5 of 6**. Queue behind it: CARD-271, CARD-267, CARD-269, CARD-268.|
| 55 | CARD-271 P2 ✅ `476abf18` | ▶ active. Owner's bugs-first order: **CARD-271 merged 2026-10-23** — 6.0 cycle 1 (NOT CERTIFIED on one real player-visible bug, re-derived by the orchestrator before a fix round was spent on it) → fix round 1 + two gate-found corrections → **9.5 cycle 2, CERTIFIED**, cycle 1's one ADR-0039/R1 violation closed with a control that FAILS. AC/EC/G 65/65 by node id, zero skips. Two full suites, both reds accounted for: attempt 1 the card's own browser-family registry debt (27 node ids, 25 owed since the implementation commit, unreachable by any scoped gate), attempt 2 a load-induced `Page.goto` timeout in an untouched file, reproduced green 3x. Merged on a stated union argument. Next: CARD-267, then CARD-269, CARD-268 — one at a time while they hold `solver.js`/`admin.css`. |
| 56 | CARD-218 P2 ✅ `3d2664f7` | ▶ active. **Suite-cost wave.** CARD-218 **merged 2026-10-24** and **closed rather than converting its other five files**, which is what both review cycles recommended and what its own measurement supports: its nine `Touches:` files are 69.79 s = 4.89 % of the suite at 131.9 ms/test — *below* the mean — and the mechanism's ceiling across all nine is **4.90 s**. What it bought, in the exact unit: **45 renders → 34**, eleven removed, corroborated by a second pure call counter; wall clock −0.74 s / −8.3 % over interleaved pairs. Scores 6.0 → 7.0, **merged on a recorded GATE OVERRIDE** against `min_score: 8` — the 7.0 scored the tree *before* fix round 2, whose two closures are certified load-bearing by the orchestrator's own mutants, and the round budget (6 of 6) could not buy the cycle to re-score it. The loop's real yield: cycle 1 caught **454,410,000 B = 18.0 page bitmaps retained to session end** (AC-5's named verifier structurally could not fail on it) and three controls passing with their mechanism DELETED under any narrowed selection; cycle 2 then caught the guards written for cycle 1 — a claim false by 0.21 % about a **pre-existing** 25 MB cache retention, and a denominator guard blind to `request.getfixturevalue`. Plus **eight fictional `TestCuration_*` verifiers across CARD-218/219/220**, six of them diff properties no standing test can hold. Merge gate: AC/EC/G 783 passed zero skips; full suite **8897 passed, 0 failed**, whose finding was its **skip count** — 101 against the baseline 27, the 74 extra traced to transient Postgres timeouts and every one re-run green. `src/` byte-identical to the fork point. Residue routed: CARD-219 carries the shared helper home with the instrument widening and the transitive-fixture closure; the pre-existing 24.4 MB retention and 53 duplicated lines are backlogged. |
| 57 | CARD-219 P2 | ▶ active. **Suite-cost wave, second card.** Dispatched 2026-10-24 on the owner's standing scheduling override: CARD-219 `Depends on:` six cards and **CARD-207/208/209 are still `ready` and undispatched**. Unlike CARD-218's override this one has a measured price, so three files are **fenced out** at dispatch with the cost recorded: `tests/test_book_solved_answer_key.py` (4.33 s) and `tests/helpers/book_corpus.py` because CARD-209 **changes the answer-section page arithmetic** a positional conversion would assert, and `tests/property/test_book_pdf_geometry.py` because it is CARD-208's. That third fence is the headline: at **51.82 s in four tests (3.63 % of the suite, 12,955 ms/test)** it is **bigger than this card's entire remaining scope**, it is the file the card's own 2026-10-15 re-pointing says to "start there", and **it was never in the card's `Touches:` line** — with `scope_gate: on`, taking it buys an escalation to be told so. **Owner-actionable: the largest prize in CARD-219's subject is behind CARD-208, which is `ready` and undispatched.** What is left in scope: six files, **50.49 s / 259 tests = 3.54 %** of a 1426.16 s suite, of which **two files are 68.3 %** and **eight tests are 54 %** (toc's seven positional tests at 1.69–1.81 s each, plus export_interior's one at 16.16 s) — concentrated, unlike CARD-218's, which is the argument for dispatching it. Carried from CARD-218: the shared home for nine duplicated helpers (53 executable lines) and its **two open holes**, the ADR-0039/R2 false negative being the one that matters. Flagged at dispatch: this card **reds `tests/test_suite_profile.py:482` by succeeding** — `RENDER_HEAVY_SNAPSHOT` is a live grep asserted as an equality and all six in-scope files are in it. One orchestrator defect already found and corrected on the card: a node-id regex of `(\S+)$` dropped **842 parametrised ids containing spaces**, inflating the suite mean 9.3 % and reversing the one comparison drawn from it. |
| unscheduled | CARD-207 P2, CARD-208 P2, CARD-209 P2, CARD-210 P2, CARD-215 P2, CARD-216 P2, CARD-220 P2, CARD-226 P2, CARD-227 P2, CARD-229 P2, CARD-230 P2, CARD-231 P2, CARD-232 P2, CARD-233 P2, CARD-249 P2, CARD-263 P2, CARD-265 P2, CARD-266 P2, CARD-282 P2, CARD-283 P2, CARD-284 P2, CARD-285 P2 | ⏳ not yet dispatched to a wave |

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
- CARD-258 deferred (declared as its bound 9, not as a code comment — the mechanical deferral scan
- CARD-147 F-007 (three cards old): should the baseline chain's fixtures get `superseded_by` back-pointers? Each fixture's `warning` ends "…and says so here",…
- Per-directory READMEs: no directory under `src/` has one, so every book card skips the docs step, and `tests/README.md` is still titled "Admin Panel Test Sui…
- **Should the editor page show the PRE-EDIT difficulty — the grade of the grid as stored — anywhere?** Carried out of wave 46 as owner decision 2 and left ope…
- **`test_web_upload.py` sweeps the machine-wide temp dir and reds whenever two worktrees run the suite at once.** `_uploaded_temp_files()` globs `nonogram-upl…
- **Stop asking implementation agents to run the full suite; let the orchestrator's merge gate be the only full run.** Observed in wave 37: every card brief en…

_Full list: [meta/kanban/backlog.md](backlog.md)_

## Ready
- **CARD-287** P2 · One class is a quarter of the suite and two thirds of its growth — and it is not rendering anything  _(unscheduled, **depends on CARD-276** — which rewrites the very walker that costs the time; from the 2026-10-23 profile read against 2026-10-15: `tests/test_book_export_interior_cover.py` 14.09 s → 344.29 s, 95.3 % of it in one AST-guard class at 14.3 s/test, and only 9.25 s of the file renders at all)_
- **CARD-276** P2 · Close the door axis for real — anchoring as a fixed point, and the residue CARD-262 declared  _(unscheduled, dependency CARD-262 `faea50a5` is merged so it is dispatchable; **its cycle gate pays ≈344 s in the class it edits**, and CARD-287 asks it to record that class's per-test durations before and after its change)_
- **CARD-286** P2 · The impact derivation cannot see a coupling no import edge carries — so it fails OPEN on the player, and wide on the book  _(unscheduled, from the owner's 2026-10-23 request + CARD-271's PG-2 and its red merge gate; prerequisite for trusting `test_scope: impact` board-wide)_
- **CARD-281** P2 · The figures a guard module states about itself are copies, and copies are what drifted five times on one card  _(unscheduled, from CARD-264's re-entry review)_
- **CARD-207** P2 · A book puzzle page's header splits — "Puzzle 37" flush left, "MEDIUM" flush right, a rule beneath  _(unscheduled, tier 1)_
- **CARD-208** P2 · Printed clue numbers sit in ruled boxes, like the player's clue cells  _(unscheduled, tier 1)_
- **CARD-209** P2 · Wide-but-short solutions pack 3 to a page, one column × three rows  _(unscheduled, tier 1)_
- **CARD-215** P2 · Given cells print — a black cell for a revealed filled cell, a dot for a revealed white one  _(unscheduled, tier 1)_
- **CARD-216** P2 · A puzzle's given cells are stored with it, and the player shows them as locked marks  _(unscheduled, tier 1)_
- **CARD-220** P2 · Retire tests whose coverage another test already provides — only with a named survivor  _(unscheduled, tier 1)_
- **CARD-226** P2 · A two-up page becomes two equal slots split by a light rule, with aligned bottoms  _(unscheduled, tier 1)_
- **CARD-227** P2 · The printed grid's rules get three weights — cell, every fifth, outer border  _(unscheduled, tier 1)_
- **CARD-229** P2 · "How to Solve" becomes a facing spread on pages 2 and 3, in the puzzle pages' own frame  _(unscheduled, tier 1)_
- **CARD-231** P2 · A section opener names its section in large type, with dots, range and a line of what to expect  _(unscheduled, tier 1)_
- **CARD-232** P2 · Solutions become fixed tiles, four to a page in a 2x2 grid, each with its clues  _(unscheduled, tier 1)_
- **CARD-249** P2 · The editor page says which puzzle it is editing  _(unscheduled, tier 1)_
- **CARD-218** P2 · Each book renders once per module, not once per test  _(unscheduled, tier 2)_
- **CARD-230** P2 · The guide's worked example runs as four steps, and the rows/columns tip becomes a callout  _(unscheduled, tier 2)_
- **CARD-233** P2 · A solution tile gets one header — number, picture name, dots — and the page a running head  _(unscheduled, tier 2)_
- **CARD-267** P2 · Crosshair — the player highlights the hovered cell's row, column and their clues  _(wave 54 queue, quick — owner decision 2026-10-22)_
- **CARD-269** P2 · Hint ladder — point at the line, explain the deduction, and only then reveal; plus a Check for wrong marks  _(wave 54 queue, quick — owner decision 2026-10-22)_
- **CARD-268** P2 · Probe mode — hypothesis marks in their own tint, abandoned or committed as one transaction  _(wave 54 queue, quick — owner decision 2026-10-22)_
- **CARD-280** P3 · The solved board stops being a worksheet and becomes the picture  _(unscheduled, 0.75d — owner request 2026-10-23; **serialises against CARD-267 / 268 / 269** on solver.js + solver_state.js + admin.css, which is why it is P3: a queue position, not a judgement)_
- **CARD-279** P2 · A loopback-binding control asks whether a port is free on a LAN address, and the answer depends on the network  _(unscheduled, trivial 0.25d — CON-009 probe seen red once 2026-10-23; carries the measured CON-010 **selector** defect too: `-k` by the requirement id collects **zero**)_
- **CARD-278** P2 · `_blind_propagation` blinds one propagation path of two, so the test named for the branch checkpoint passes without it  _(unscheduled, trivial 0.25d — found 2026-10-23 by the skeptic that **refuted** CARD-264's I-1; not absorbed because CARD-264 is at cycle 3/3 and a last-cycle widening ships uncertified)_
- **CARD-277** P2 · A drag at 200% zoom marked the whole board once — reproduce it before deciding what it is  _(unscheduled, quick — CARD-270 review 2 ruled it needs its own card; **does not block CARD-270**)_
- **CARD-276** P2 · Close the door axis for real — anchoring as a fixed point, and the residue CARD-262 declared  _(unscheduled, `architectural` — **blocked on CARD-262 merging**; carries the transitive fixed point, three declared residues, six unfired matrix cells and two prose defects the AC/EC/G gate found)_
- **CARD-275** P2 · The guide strip's frame vanishes against filled cells — the same ink-on-ink class, in the second place it lives  _(unscheduled — CARD-270 review F-004, carded on the owner's instruction; **merge CARD-270 first**, it reads the grey that card's pixel assertions depend on)_
- **CARD-265** P2 · The `_ADAPTER_COUNT` boundary, four one-line bounds, and the one sentence tests/README.md is missing  _(unscheduled, tier 2 — **now owns the folded `_ADAPTER_COUNT` question** (owner decision 2026-10-22); estimate 0.25d → 0.75d; its item 1 already measured BOTH rival bounds and neither dominates; **2026-10-23: the three stale "two" claims it inherits have NO control — `_adapter_counts` scans CLAUDE.md, not the prose around `_ADAPTERS`, and `len(_ADAPTERS)` appears nowhere)_
- **CARD-266** P2 · The standing check — no prose anywhere names a `validate_*`/`parse_*` symbol that does not exist  _(unscheduled, tier 2)_
- **CARD-272** P2 · The import guard gains the composite-capability rank (ADR-0040)  _(unscheduled — after CARD-265; delta carded 2026-10-22)_
- **CARD-273** P2 · Book production moves to src/nonogram/book/ — the ADR-0040 rewrite  _(unscheduled — after CARD-272 and the book wave drains; 17 deps)_
- **CARD-274** P3 · admin/app.py splits into route modules — the blueprint refactor  _(unscheduled — after CARD-273)_
- **CARD-282** P2 · The admin panel exports the player bundle — static JSON the public solver reads  _(unscheduled — public player phase head; FR-045/ADR-0041, key recipe pinned by ADR-0041/R1; unblocked 2026-10-23 when DEC-044 resolved)_
- **CARD-283** P2 · The public player page — the admin game served static, with no answer in the browser  _(unscheduled — after CARD-282; `architectural`; unblocked 2026-10-23 when CON-021 was amended / ADR-0041 landed)_
- **CARD-284** P2 · The QR landing and the library — /b/<slug> and /library around the player  _(unscheduled — public player phase, after CARD-282 + CARD-283; owner architecture decision 2026-10-23)_
- **CARD-285** P2 · Hosting and counting — the player goes public without storing anyone's IP  _(unscheduled — after CARD-283 + CARD-284; delivers the hosted URL base CARD-210's unblock needs; hosting account/provider choice is the owner's)_

## In Progress
- **CARD-219** P2 · Positional assertions read the page plan instead of rendering pixels  _(wave 57, started 2026-10-24, branch `card/219-assert-the-plan-not-the-pixels`, worktree `../PythonProject4-card-219` at fork point `808cf51f`)_ — implementation round in flight. Scope fenced to six files + a shared-helper home; see the card's `[DISPATCH]` section for the three fences and their cost.

## Review
_(none — CARD-264 merged `066ddc1f` and CARD-271 merged `476abf18`. CARD-218 is in its first review cycle, see In Progress.)_

## Blocked
- **CARD-210** 🔒 Each puzzle's QR code becomes a real, scannable link to that puzzle's online solver  ← owner decision 2026-10-13 — "keep the placeholder until infra exists". Real QR pixels wait on the next phase's infrastructure: a public solver that is actually hosted, and a per-puzzle URL namespace stable enough to p…
- **CARD-263** 🔒 The error count becomes the first hint, not a free one — and the player stops being told  ← FR-044 **AC-354** pins the error counter's DOM presence and order, and **AC-312..315**'s verifying browser test asserts the counter `is_visible()` before reading it. The requirement must change before the code — `/for…

## Done
_247 cards merged, waves 1–56 (plus 43 from before the `Wave:` field existed)._ Most recent:

- **CARD-218** Each book renders once per module, not once per test — **closed after converting two files of nine**, on its own measurement  _(wave 56, 6.0 → **7.0** cycle 2/3 NOT CERTIFIED, **merged on a recorded GATE OVERRIDE**; merge `3d2664f7`, 2 files +1210/−39, `src/` byte-identical to the fork point. The card's premise measured dead by its own implementation round: nine `Touches:` files = 69.79 s = 4.89 % at 131.9 ms/test, mechanism ceiling **4.90 s**. Delivered **45 renders → 34** — eleven removed, 24 %, corroborated by a second pure call counter — for −0.74 s / −8.3 % on the two files. The review loop's yield dwarfed the saving: **454,410,000 B = 18.0 page bitmaps retained to session end** (cycle 1, invisible to every guard on the board because AC-5's named verifier instruments another module's dict), three controls passing with their mechanism DELETED under any narrowed selection, then cycle 2 catching the guards written for cycle 1 — a claim false by 0.21 % about a **pre-existing** 25 MB cache retention, and a denominator guard blind to `request.getfixturevalue`. Plus **eight fictional `TestCuration_*` verifiers across three cards**, six of them diff properties no standing test can hold. Merge gate's own finding was its **skip count**: 101 against the baseline 27, the 74 extra transient Postgres timeouts, every one re-run green)_

- **CARD-271** Big boards lose their bottom and left clues — the clues stay in view where there is room, and the board says where there is not  _(wave 55, 6.0 → **9.5** cycle 2/2 CERTIFIED; merge `476abf18`, 9 files +2173/−14. Two full suites, 8953 passed / 27 skipped each, both reds accounted for and re-verified; 38 mutant directions across the card; six renders handed to the owner where three were required, with **two owner decisions deliberately not taken** — the 390 px phone's band, and whether `--player-zoom` should magnify the clue band at all (CARD-195))_

- **CARD-270** A filled cell draws its own division, so runs stop merging across every ink rule  _(wave 54, 8.4 → **9.7** cycle 2/3; merge `64da37f6`, gate 8856 passed / 27 skipped / 0 failed — the owner's reported defect, fixed by one CSS declaration)_
- **CARD-262** The page-position guard's door axis, **declared** rather than claimed closed  _(wave 53, 5.7 → 5.2 ⚠ stalled → escalated → owner chose DECLARE → AC/EC/G gate PASSED; merge `faea50a5`, gate 8837 passed / 27 skipped / 0 failed)_
- **CARD-260** Commit the per-assertion kill instrument once, with all six of its known traps as controls  _(wave 51, score 8.8 (round 5 — re-entry cycle 2/3))_
- **CARD-259** CARD-252's record is written in three places; single-source it and control the pointer  _(wave 52, score 8.5 (cycle 3/3 — ✓ review passed; AC/EC/G gate ✓ 10 of 10 after the owner's AC-2 narrowing))_
- **CARD-258** Make the next `relation "puzzles" does not exist` red say what it was talking to  _(wave 51, score 9.0 (cycle 3/3))_
- **CARD-257** Cut the guard's prose to what its 22 lines actually claim  _(wave 50, score 9.0 (cycle 3/3 — certified, no open Important))_
- **CARD-256** The lock guard's path-redirect variable gets the same control and the same loudness as its override  _(wave 50, score 9.0 (cycle 3/3 — certified, no open Important))_
- **CARD-255** A pytest run refuses to start while another worktree holds the full-suite lock  _(wave 49, score 9.0 (cycle 3/3 — certified, no open Important))_
- **CARD-254** Shrink CARD-252's private-globals guard to the part that has authority  _(wave 49, score 9.0 (cycle 3/3 — certified, no open Important))_
- **CARD-253** The player's reset confirmation names the button that opens it  _(wave 48, score 9.5 (cycle 2/3 — certified, zero findings at every severity))_
- **CARD-252** The test session's schema rebuild disposes the app's engine, so a gate's red means the code  _(wave 48, score 8.0 (cycle 3/3; merged on the final reviewer's verdict, claim cut back))_
- **CARD-251** A puzzle already in a book can be edited, behind a confirmation that names the book  _(wave 47, score 9.0 (cycle 2/3 — 8.0 → 9.0; certification complete, 0 critical, 0 important))_

