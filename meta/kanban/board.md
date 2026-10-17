# Kanban Board

_Updated: 2026-10-17 UTC_  ·  <!-- forge:run wave=42 mode=interactive concurrency=2 -->

## Wave plan
| Wave | Cards | Status |
|------|-------|--------|
| 1 | CARD-080 P1, CARD-001 P1, CARD-019 P1, CARD-022 P1, CARD-023 P1, CARD-024 P1, CARD-025 P2, CARD-045 P1, CARD-046 P2, CARD-047 P2, CARD-048 P3, CARD-049 P1, CARD-050 P1, CARD-051 P2, CARD-054 P3, CARD-055 P3, CARD-058 P3, CARD-059 P3, CARD-060 P3, CARD-061 P2, CARD-062 P2, CARD-063 P3, CARD-064 P2, CARD-065 P3, CARD-066 P3, CARD-067 P2, CARD-068 P2, CARD-069 P2, CARD-070 P2, CARD-071 P3, CARD-072 P2, CARD-073 P1, CARD-074 P1, CARD-075 P2, CARD-076 P1, CARD-077 P2, CARD-078 P3, CARD-079 P2, CARD-084 P3, CARD-085 P1, CARD-086 P2, CARD-087 P2, CARD-088 P1, CARD-089 P2, CARD-090 P2, CARD-091 P2, CARD-092 P3, CARD-093 P3, CARD-094 P3, CARD-095 P3, CARD-096 P2 | ✅ done |
| 2 | CARD-002 P1, CARD-003 P1, CARD-020 P1, CARD-026 P1, CARD-029 P3, CARD-052 P2, CARD-053 P3, CARD-056 P3 | ✅ done |
| 3 | CARD-004 P1, CARD-021 P2, CARD-027 P1 | ✅ done |
| 4 | CARD-005 P1, CARD-028 P2, CARD-030 P2, CARD-031 P2, CARD-032 P2 | ✅ done |
| 5 | CARD-006 P1, CARD-007 P1, CARD-033 P2, CARD-034 P2, CARD-035 P2, CARD-037 P2, CARD-038 P2, CARD-040 P2, CARD-041 P2, CARD-042 P2 | ✅ done |
| 6 | CARD-008 P2, CARD-009 P1, CARD-011 P2, CARD-012 P1, CARD-013 P1, CARD-018 P2, CARD-039 P3, CARD-043 P2, CARD-044 P1 | ✅ done |
| 7 | CARD-010 P1 | ✅ done |
| 8 | CARD-014 P2 | ✅ done |
| 9 | CARD-015 P2 | ✅ done |
| 10 | CARD-016 P2 | ✅ done |
| 11 | CARD-017 P3 | ✅ done |
| 20 | CARD-113 P1, CARD-135 P1, CARD-119 P1 | ✓ done |
| 21 | CARD-114 P1, CARD-120 P1 | ✓ done |
| 22 | CARD-125 P2, CARD-115 P1, CARD-122 P1, CARD-124 P1, CARD-133 P2 | ✓ done |
| 23 | CARD-116 P1, CARD-121 P1 | ✓ done |
| 24 | CARD-117 P1, CARD-123 P1, CARD-126 P2, CARD-136 P1, CARD-137 P1 | ✓ done · closes Increment 14 |
| 25 | CARD-118 P1, CARD-127 P2, CARD-130 P2, CARD-134 P2, CARD-138 P1 | ✅ all 5 merged · ⏳ Increment 13 waits on the owner's printed proof measurement |
| 26 | CARD-145 P0, CARD-128 P2, CARD-131 P2, CARD-132 P3, CARD-139 P1, CARD-140 P1, CARD-141 P2, CARD-142 P1, CARD-144 P2 | ✅ 9/9 merged · closes Increment 16 |
| 28 | CARD-150 P2, CARD-151 P2, CARD-152 P2 | ✓ done — all 3 merged |
| 29 | CARD-153 P1, CARD-154 P2, CARD-155 P3, CARD-156 P2 | ✓ done — all 4 merged |
| 30 | CARD-157 P2, CARD-158 P2, CARD-159 P2 | ✓ done — all 3 merged |
| 31 | CARD-160 P2, CARD-161 P2, CARD-162 P2, CARD-163 P2 | ✓ done — all 4 merged |
| 32 | CARD-164 P1, CARD-165 P2, CARD-166 P2, CARD-167 P2, CARD-168 P2 | ✓ done — all 5 merged; full suite exit 0 |
| 33 | CARD-169 P1, CARD-170 P1, CARD-171 P2, CARD-172 P2, CARD-173 P2, CARD-174 P2, CARD-175 P3, CARD-176 P2 | ✓ done — all 8 merged (CARD-170 after an owner-chosen targeted fix) |
| 34 | CARD-177 P1, CARD-178 P2, CARD-179 P2, CARD-180 P3, CARD-181 P3, CARD-182 P3, CARD-183 P3, CARD-184 P2, CARD-186 P2, CARD-188 P2 | ✓ done — all 10 merged (CARD-188 after two owner-chosen fixes) |
| 35 | CARD-185 P2, CARD-187 P3, CARD-189 P2, CARD-190 P2, CARD-191 P2, CARD-192 P2 | ✓ all 6 merged (185 ae25661, 189 0b637a9, 187 b291141, 190 22ce971, 191 cccfecb, 192 da93164) — board bookkeeping was stale, swept 2026-10-08 |
| 36 | CARD-193 P2, CARD-196 P2 | CARD-196 ✓ merged d7ba2ac (score 8.5, cycle 3/3) · CARD-193 ✓ merged c51982a (score 9.5, cycle 3/3) · CARD-194 ✓ merged e0214c9 (score 9.0, cycle 1/3) · CARD-195 ✓ merged 1b4bc97 (score 9.3, cycle 2/3; owner caught a real native pinch-zoom bug by eye in cycle 1's renders, fixed in cycle 2) · wave 36 complete |
| 37 | CARD-197 P2, CARD-198 P2, CARD-199 P2 | CARD-199 ✓ merged 7d4bcf8 (score 9.5, cycle 1/3) · CARD-197 ✓ merged 81156b1 (score 9.0, cycle 2/3) · CARD-198 ✓ merged da0f8bb (score 8.5, cycle 1/3; owner confirmed the three flagged consequences — level heading dropped, Finalise label narrower, page-growth ceiling risk — before merge) · wave 37 complete — owner solution-layout doc |
| 38 | CARD-204 P2, CARD-214 P1, CARD-205 P1, CARD-211 P2, CARD-221 P1, CARD-212 P2 | CARD-214 ✓ merged d49e73a (8.1, cycle 1/3) · CARD-204 ✓ merged cd641df (8.5 cycle 4, then 6.5 cycle 5 on a merge-gate fix; 8 fix cycles) · CARD-211 ✓ merged 4790243 (9.0, cycle 1/3) · CARD-205 ✓ merged d30e0f0 (8.8, cycle 1/3; AC/EC/G gate failed on G-1 and the guardrail was amended) · CARD-221 ✓ merged 806dbe1 (7.5 then 8.5, cycle 2/3; 5 fix cycles) · CARD-212 ✓ merged a2cd3f3 (7.0 then 8.5, cycle 2/3; 3 fix cycles) ✓ wave 38 complete, 6/6 merged — owner print-layout doc |
| 39 | CARD-217 P1 | CARD-217 ✓ merged 967a7fa (9.0, cycle 1/3; 2 fix cycles, both spent making the measurement's own claims checkable; 63 mutants) ✓ wave 39 complete — ran SOLO by owner decision, which is what made the number trustworthy. Answer: the browser family is 39.78% of the suite, neither card hypothesis; re-points CARD-218/219/220 and cuts CARD-235/236 |
| 40 | CARD-234 P2, CARD-235 P1, CARD-237 P1 | ✓ **3/3 merged** — CARD-237 ✓ 194cb40 (7.5 then 9.0; cut IN FLIGHT to unblock the wave; 0.7d) · CARD-234 ✓ c6dfeed (9.0 cycle 1, 11/11 AC/G, 6 mutants; 1.0d) · CARD-235 ✓ 6ac8627 (8.0 then 9.0, 11/11 AC/G; premise refuted — the lever was socketserver's poll, not fixture scope; 1.1d) — **2d of estimates, ~9h elapsed, and essentially all the overrun was test infrastructure**: three defects of one shape, a test whose verdict depends on something other than the code it judges |
| 41 | CARD-238 P1 | ✓ **1/1 merged** — CARD-238 ✓ 6c511a4, SOLO, scores 6.0 → 7.5 → 7.5 → 6.5 → **8.0** (cycle 5/3, two owner escalations), 5 fix cycles · **2.7d against 0.5d** · ⚑ the deliverable is the fix; the *result* is the rule it produced — a set a guard consults needs a completeness test written BEFORE the set, and a claim about coverage needs a control that can fail. Five passes each fixed the named instances and minted a new unfalsifiable claim; what broke the loop was deriving the enumeration from `dir(os)` et al, which named four spellings five hand-written passes had missed. Bounds shipped as recorded controls → **CARD-239** |
| 42 | CARD-228 P1, CARD-213 P2 | ✓ **done — 4/4 merged** — CARD-213 ✓ cbd5a8e (9.0 cycle 1, AC/EC/G 21/21, **0.2d** against 0.5d) · CARD-240 ✓ 9f0ab10 (9.0 c1, **0.1d**) · CARD-228 ✓ 08eecf3 (3 cycles + escalation; AC-4 narrowed, → **CARD-241**; 0.5d) · CARD-239 ✓ c0ab383 (2 cycles + escalation resolved as a split; → **CARD-242**; 0.6d against 1d) — ✓ **wave 42 complete, 4/4 merged, 2 escalations both resolved by owner decision rather than by another cycle.** The wave's through-line: **twice, the presence or absence of a derivable authority predicted whether a guard converged** — CARD-228's method half (`dir(ImageDraw)`) and CARD-239's stdlib surface (`dir(os)`) were sound from their first pass; their sibling halves, which had no authority to derive from, took three cycles and two cycles respectively. Smoke test satisfied by CARD-239's merge gate (7727/0) on a byte-identical code tree |
| 43 | CARD-241 P1, CARD-242 P2 | ▶ **active — 1 merged** · CARD-242 ✓ `b194e3e` (7.0 → 8.5, 0.5d) — dispatched 2026-10-17T05:05Z at concurrency 2, the two cards wave 42's escalations produced. Both carry `TDD: true`, both come pre-measured (CARD-228's and CARD-239's own review reports), and their `Touches` are disjoint — no conflict edge, so they genuinely run in parallel rather than queueing on `book_pdf_generator.py` like every other eligible card |
| 27 | CARD-129 P2, CARD-143 P2, CARD-146 P2, CARD-147 P2, CARD-148 P1, CARD-149 P2 | ✅ 6/6 merged · closes Increment 15 |

_Note (2026-09-22): all 111 cards of waves 1–19 (CARD-001..CARD-112) are `done`. Waves 20–27 are the book generator (handoff Increments 13–16, CARD-113..CARD-135; CARD-133/CARD-134, the answer key, added by the 2026-09-22 (c) delta), numbered after the finished waves so `waves.yml` attribution cannot collide with them. The 2026-09-22 (d) delta added CARD-135 (interior PDF without the cover, cover as its own file; wave 20, before CARD-116's page parity) and folded the answer-key details into CARD-133/CARD-134/CARD-128; no wave was renumbered. Checkpoints per wave: [meta/kanban/waves.yml](waves.yml). The CON-019 golden-A4 tripwire (CARD-113) must stay green at the end of every book wave._

_Note (2026-10-02): waves 29–30 come from the backlog sweep (CARD-153..CARD-159). Wave 29 is independent cards. CARD-153 and CARD-154 both edit `admin/app.py` but in different routes (Finalise vs Print setup). Wave 30 holds CARD-157 (depends on CARD-156's fixture) and the two template cards, which also touch `app.py` (book detail vs book create). CARD-158 uses CARD-157's bulk read if it has merged first. No owner checkpoint is declared for either wave; 158 and 159 put renders in ~/Documents/nonogram-reviews/ for the owner's eye._

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
_Source of truth: [backlog.md](backlog.md) (merged 2026-10-02 with the notes that used to live here). Top items:_
- **Owner decisions:** CARD-147 F-007 baseline back-pointers · per-directory READMEs convention · Render Blueprint vs dashboard
- **Architecture model (/forge:architect):** dead `check:` refs on mandatory rules (CON-005, ADR-0006/R1, INV-001/002/008..012, ADR-0029/R2) · `--verify-refs` matches text · ADR-0025↔ADR-0031 circular supersession ERROR · CON-020 partial · 512 MB memory NFR missing
- **Tests:** `test_size_configuration_applied` red · `test_wave3_e2e.py:366` stale heading · two vacuous assertions · shared temp-dir globbing
- **Deferred by the owner's V1 decision (doc 2026-10-13):** a public online solver (blocks CARD-210) · a stable per-puzzle URL namespace for printed QR codes (blocks CARD-210) · the "generate your own puzzle" QR · persisting user-generated puzzles
- **Features:** square/landscape trim proof page (revisit at page-layout finalisation) · guide page worked example · batch target-tier column

## Architecture
_(none)_

## Ready
_21 cards ready, 2 in progress, 1 blocked. **Eligible right now** (every dependency merged): CARD-222,
CARD-206, CARD-207, CARD-208, CARD-209, CARD-215, CARD-216, CARD-220, CARD-236 — the other 12 wait
on a sibling in the interior-redesign chain (CARD-222 → 223 → 224/225 → 226/227/229..233) or on
CARD-206..209 (CARD-218, CARD-219)._

**Carried out of wave 43's review cycles (owner decision 2026-10-17)**
- **CARD-243** The round-mark check sees the greys the book actually prints · P2 · 1d · standard · **TDD** · depends CARD-241 · ⛑ CARD-241's instrument thresholds ink at grey 128 while production draws the solved grid at grey **160**, so a difficulty dot in the book's own grey is invisible: measured, a grey-160 disc yields **0 ink regions** where the identical black disc yields 1, and 6 planted grey glyphs gave `found=0 unaccounted=0` — **ADR-0036/R3's declared check passes green with 18 undeclared dots on the pages** · ⛑ narrowed rather than closed in CARD-241 by owner choice, so this card inverts that bound's control instead of deleting it · ⛑ the generalisation worth carrying: the instrument discriminates on **silhouette only**, so darkness, colour and opacity are open by construction

**Carried out of the wave's two escalations (owner decisions 2026-10-16 and 2026-10-17)**
- ~~**CARD-242**~~ → In Progress (wave 43). The check-log guard learns the taint step its sibling already has · P2 · 0.5d · standard · **TDD** · depends CARD-239 · ⚑ carries CARD-239's F-201: a `--check-log` command line hoisted into a module-scope constant and then executed is **exempt**, where the same call inline is caught (M2 hoisted SURVIVED at 854 passed, M3 inline KILLED) · ⚑ the fix has a working precedent in the same codebase — `_live_log_references`' taint step answers exactly "does the bound name reach an executor?", and `_check_log_invocations` reimplemented the shape while dropping that half · ⚑ **the naive narrowing is ruled out by measurement**: keying the exemption on the value catches the hoist and keeps all 11 controls green, but hits `SANDBOX_CONTROL_MODULE`, a constant holding a fabricated module's source that *mentions* the option as prose — a guard that cannot tell a quoted example from an executed command is the same defect pointing the other way · ⚑ **the first card written knowing "an exemption is a claim"**
- ~~**CARD-241**~~ → In Progress (wave 43). One round mark on the page, proved by rendering it rather than by reading the source · **P1** · 1d · **architectural** · **TDD** · depends CARD-228 · ⚑ replaces the verification instrument four cards lean on. Three review cycles proved a static `ast` walk cannot hold AC-4's universal negative: 3 glyphs landed, then 2, then 3, **a new syntactic family each time** (receiver → binding form → call shape and cross-call ink), because the guard discriminates by syntactic form and **no authority enumerates the forms** — `dir(ImageDraw.ImageDraw)` is a real authority for *which methods* draw, but Python's grammar offers nothing importable that lists every way to write a vertex list. The instrument instead: render a page, find the ink, test it for roundness — blind to spelling, on the existing dependency baseline, and what CARD-207's printed proof does anyway. All three cycle-3 survivors die under it. **Keeps CARD-228's static guard as the cheap first line** rather than deleting it, and its AC-5 makes the limits list shrink honestly (the equality reds if a route is struck without being closed, or closed without being struck). Also carries the ADR question CARD-228 surfaced: the package-wide dingbat constraint is declared only inside a test file. ⚑ every figure it needs is already measured in CARD-228's three review reports, and the card says so — re-deriving them is how it costs 2d instead of 1d

_Cut 2026-10-13 from the owner's Google Doc "Nonograms - Print layout" (12 cards: CARD-205..CARD-216, one of them blocked). Not yet scheduled into a wave — run `/forge:kanban run` to dispatch. Print-side cards share the `book_pdf_generator.py` / `layout.py` hotspots and will serialize; CARD-207/208/209/210 depended on CARD-204, which merged as `cd641df` on 2026-10-14, so 206/207/208/209 are now eligible and 210 is blocked only by the owner's infrastructure decision._

_Wave bookkeeping (2026-10-14, **owner decision**): this run is **wave 38**. All six of its cards — CARD-204, CARD-214, CARD-205, CARD-211, CARD-221, CARD-212 — had been drafted as wave 37, which the table above already recorded as complete with CARD-197/198/199; the number was used twice and the retrospective reads it. The owner chose to renumber the whole batch rather than only its open cards, so one batch is not split across two wave numbers: CARD-204 and CARD-214 were renumbered too, closed records and all. The 2026-09-22 note above is the precedent for why the numbers must not collide._

**Interior redesign (cut 2026-10-14 from the owner's artifact "Puzzle page layout", https://claude.ai/artifact/Wp4iGB27cyBAV62da5ACMP)**

_One coherent frame, so the order is forced rather than chosen: the frame lands first and each later card places something inside it. Every one of them touches `book_pdf_generator.py`, so they serialize on that hotspot whatever the dispatcher does. **CARD-224 reverses CARD-204's flush-by-parity placement, which merged 2026-10-14 after 12.2 days** — the owner's own note explains why: the flush alignment existed to free the gutter strip for the QR, and once the QR has its own footer, centring is the calmer choice. CARD-204's QR slot, two-up folio reserve and `caption_slot` all stay._

- **CARD-222** Every interior page gets one frame — new margins, a header rule and a footer rule · **P1** · 1d · architectural · depends CARD-221 · ⚑ CON-018 amendment (outer/top/bottom only — **owner 2026-10-14: the gutter stays at KDP's 0.5 in**, not the artifact's 0.75 in) · measured: every cell not already at the 7.5 mm cap loses 1.6%, where the artifact as drawn cost 4.9%
- **CARD-223** The QR moves into the footer's **outer** corner, with a caption and a typed link · **P1** · 1d · depends CARD-222 · ⚑ the owner's functional complaint: a code printed into the spine does not scan
- **CARD-224** The grid goes back to centred, at 42% of the spare height · **P1** · 1d · architectural · depends CARD-222, CARD-223 · ⚑ FR-032: its "centred" statement becomes correct again (so CARD-204's pending amendment is **cancelled**), while its "fixed top edge" clause is what breaks
- **CARD-225** One cell size per grid size across the book, capped at 7.5 mm · **P1** · 1d · architectural · depends CARD-222 · ⚑ NFR-008 amendment · a book-wide size is by construction ≤ today's per-puzzle size, so some puzzles print smaller
- **CARD-226** A two-up page becomes two equal slots split by a light rule, bottoms aligned · P2 · 1d · depends CARD-223, CARD-224, CARD-225
- **CARD-227** The printed grid's rules get three weights — 0.3 / 0.8 / 1.3 pt · P2 · 0.5d · depends CARD-222 · ⚑ closes FR-033's stated open question ("threshold unstated")
- **CARD-229** "How to Solve" becomes a facing spread on pages 2 and 3 · P2 · 1d · depends CARD-206, CARD-222, CARD-228 · ⚑ INV-013 amendment, owed jointly with CARD-206
- **CARD-230** Its worked example runs as four steps; the rows/columns tip becomes a callout · P2 · 1d · depends CARD-229
- **CARD-231** Section openers — large type, dots, range, one line, always on a recto · P2 · 1d · depends CARD-222, CARD-228 · ⚑ inserted blanks move the page count and therefore the printed gutter
- **CARD-232** Solutions become fixed 2×2 tiles with their clues · P2 · 1d · depends CARD-222, CARD-225 · ⚑ narrows CARD-202's packing rule; CARD-209's page is the single exception
- **CARD-233** One tile header — number, name, dots — plus a running head · P2 · 1d · depends CARD-228, CARD-232 · ⚑ moves the 65-character picture name into a narrower box than the one that cost CARD-204 two fix cycles

**Book / print (PDF) — amended 2026-10-14 by the artifact above, not re-cut**
- **CARD-206** The interior opens with a blank title / copyright page, ahead of the guide · P2 · 0.5d · standard · ⚑ needs an INV-013/FR-043 amendment at the architect station
- **CARD-207** A book puzzle page's header splits — "Puzzle 37" flush left, "MEDIUM" flush right, a rule beneath · P2 · 0.5d · standard · depends CARD-204
- **CARD-208** Printed clue numbers sit in ruled boxes, like the player's clue cells · P2 · 1d · standard · depends CARD-204 · ⚑ rests on one reading of an unreadable doc image
- **CARD-209** Wide-but-short solutions pack 3 to a page, one column × three rows · P2 · 1d · standard · depends CARD-204


**Found in flight**
- ~~**CARD-234**~~ → done (wave 40, `c6dfeed`). The generated cover's title letters from packaged data, like the interior · P2 · 0.5d · bug · depends CARD-221 · ⚑ a hardcoded `/System/Library/Fonts/Arial.ttf` with a silent `load_default()` fallback: on the deployed Linux panel every generated cover takes that branch **and** loses the 72 px it asked for, so the title prints tiny on the one page a buyer sees first

**Test curation (cut 2026-10-13 on owner request; RE-POINTED 2026-10-15 by CARD-217's measurement)**


_CARD-217 profiled the suite solo and neither hypothesis CARD-218/219/220 were cut on is where the time is. `meta/profiling/suite-hotspots-20261015.md` is now this group's source of truth, ahead of the counts in the cards' own bodies. The two cards below came out of that profile and outrank the three that preceded it._

- ~~**CARD-235**~~ → done (wave 40, `6ac8627`). The browser tests stop paying for a page they throw away, 40% of the suite · **P1** · 1d · tech-debt · ⚑ the measured hotspot: 366.19 s / 39.78%, 868 ms per browser test against 83 ms for everything else, and 96% of all teardown time
- **CARD-236** The admin-local script tests stop spawning a subprocess per assertion · P2 · 0.5d · tech-debt · depends CARD-217
- **CARD-218** Each book renders once per module, not once per test · P2 · 1d · tech-debt · depends CARD-217 + CARD-205..209 · re-pointed: the render family is 21.23%, not the top cost
- **CARD-219** Positional assertions read the page plan instead of rendering pixels · P2 · 1d · tech-debt · depends CARD-217 + CARD-205..209 · re-pointed
- **CARD-220** Retire tests whose coverage another test already provides — only with a named survivor · P2 · 1d · tech-debt · depends CARD-217 · ⚑ footprint is `tests/**`; run on a quiet board · **CARD-217 recommends parking it** until 235/218/219/236 have run: the top 50 tests hold 32.1% and "no single test is worth retiring"

**Solver (the admin panel's player)**

**Generator POC (given cells)**
- **CARD-215** Given cells print — a black cell for a revealed filled cell, a dot for a revealed white one · P2 · 1d · standard · depends CARD-214
- **CARD-216** A puzzle's given cells are stored with it, and the player shows them as locked marks · P2 · 1d · standard · depends CARD-214

## In Progress
_Wave 43, dispatched 2026-10-17T05:05Z at concurrency 2 (owner's standing cap; `config.yml` allows 5).
Both cards are the residue of wave 42's two escalations, both resolved by owner decision rather than
by another review cycle._

- **CARD-241** → **Fix cycle 1** (review 1/3 scored **7.5**, 0 crit / 3 imp, all one root cause). One round mark on the page, proved by rendering it rather than by reading the source · **P1** · 1d · **architectural** · **TDD** · `card/241-round-mark-render-proof` · worktree `../PythonProject4-card-241` · ⚑ replaces the AC-4 instrument three review cycles could not hold (3 glyphs landed, then 2, then 3 — a new syntactic family each time) with render-and-measure · ⚑ **its four named tests do not exist yet and are not meant to** — `TestRoundMarkOnThePage_*` is what the card writes; checked against the tree at dispatch so the name is known-new rather than assumed-real

_No conflict edge: the two `Touches` sets share no path and neither hits a `conflict.hotspots` entry.
Verified at dispatch — `git worktree list` shows exactly these two beside `main`._

_⚠ Still owed at the architect station before the interior-redesign lane (CARD-222 → 11 cards) can run:
CARD-222's CON-018, CARD-225's NFR-008, CARD-206's INV-013/FR-043, and CARD-224 cancelling CARD-204's
pending FR-032 amendment. One `/forge:architect` session, not a card._

## Review

_(none)_ — CARD-213 and CARD-239 both merged; see Done.

## Blocked
- **CARD-210** Each puzzle's QR code becomes a real, scannable link to that puzzle's online solver · P2 · 1d · architectural · depends CARD-204 · blocked by the owner's 2026-10-13 decision: keep CARD-204's placeholder glyph until the public-solver infrastructure exists (hosting + a stable per-puzzle URL namespace). ACs are written; `/forge:kanban unblock CARD-210` when both exist

## Done
- **CARD-242** The check-log guard learns the taint step its sibling already has · P2 · tech-debt · **TDD** · scores 7.0 → **8.5** (2 cycles, cycle 2 in confirmation mode) · 1 fix cycle + 1 AC-gate fix · AC/EC/G **11/11** demonstrated · mutation check run on the passing cycle (9 killed, 0 survived) · merge gate 7781/0 · merged **b194e3e** · actual **0.5d** against 0.5d · ⛑ **the adversarial step paid for itself**: of two Important findings, one was CONFIRMED and one DROPPED — the dropped one's prescribed fix (deny-by-default) was measured to take the hoisted command line from CAUGHT to MISSED, i.e. the fix for ADR-0039/R2 would have committed the R3 defect inside the card written to apply R3 · ⛑ **the AC/EC/G gate caught what two review cycles and a mutation pass missed**: AC-6's residue list presented itself as complete and was not, which was the THIRD instance of that one shape in this card (F-001's depth bound, G-16's closed list, then AC-6 itself) — the fix answered it by enumerating the binding nodes rather than patching the three known routes, which surfaced two more laundering routes nobody had named · ⛑ its own paperwork is policed by its own mechanism: AC-5's assertion reads the claim-sweep rows, so the `meta/` carryover had to land in the same merge or the test would be red on `main` (verified green after)
- **CARD-239** The timing-log guards' remaining bounds, and the one place that reads the log on purpose · P2 · tech-debt · **TDD** · scores 8.0 → **7.5** (2 cycles) · 3 fix passes · **1 owner escalation, resolved as a split** · AC/EC/G gate PASS on every AC and guardrail over **14 mutants** · merge gate 7727/0 · merged **c0ab383** · actual **0.6d** against 1d · ⚑ **G-1 held end to end** — the owner's timing log is the same md5 it carried before the card started · ⚑ **its AC-7 sweep caught two false claims written by its own author in its own pass** (a set carrying a property not on the surface; a silencer set carrying `skip_module`, which does not exist in pytest, and `fail`, which errors loudly) — both independently reproduced by review, and the clearest evidence yet that CARD-238's 2.7d bought a mechanism and not a habit · ⚑ found the version floor stated **three** ways, not two: the PyPI classifier nobody had noticed also said 3.9, so two of three statements agreed with each other and not with the interpreter anyone runs · ⚑ **`__test__ = False` closed by mechanism** — it silenced a guarded module at rc=0 with 386 tests simply absent, the quietest form of the verdict this card exists to end · ⚑ the hoisted-command-line exemption **recorded as a bound that polices its own successor**: the same rule with its exemption narrowed returns the hoisted command, so **CARD-242 cannot close the route without this test going red** · ⚑ **the rule it produced is the sharpest of the three this wave reached** — *an exemption is a claim, and it needs the same control a set member needs*: it names the exemption, the construct CARD-238 and CARD-228 both reached for as the honest escape hatch, as itself needing a falsifier
- **CARD-228** Difficulty becomes three dots, filled by tier — one glyph the whole book reuses · **P1** · feature · scores 8.0 → 8.5 → **8.0** (3 cycles) · 2 fix cycles · **1 owner escalation, resolved** · AC/EC/G gate PASS on every item over **17 mutants** · merge gate 7592/0 · merged **08eecf3** · actual **0.5d against 0.5d** · ⚑ **the estimate was exactly right on wall-clock, and that is the point**: it measured the glyph, which was never in question (AC-1/2/3/5/6 green from cycle 1, geometry independently verified twice, G-5 held throughout, src diff purely additive with zero deletions). What it could not measure was the **promise around** the glyph — AC-4, that nothing else in the package draws a round mark, which is what makes "four cards reuse one glyph" real rather than aspirational · ⚑ **transferable root cause**: a guard that discriminates by *syntactic form* cannot be made complete, because no authority enumerates the forms. `dir(ImageDraw.ImageDraw)` served the *method* half for the same reason `dir(os)` served CARD-238 — and that half was sound from cycle 1. The vertex and receiver halves had none, so each cycle closed the named spellings and the next found a new family one level down (3 glyphs, then 2, then 3) · ⚑ cycle 2's **default-deny inversion** is the right pattern and still not sufficient: it killed receivers and binding forms for good, then cycle 3 returned via `draw.line`, cross-call ink and a stored bound method · ⚑ ships **six named limits, each with a mutant demonstrating it is open**, all pointing at **CARD-241** · ⚑ also corrected a *false* rationale: `FLAT_METHODS` claimed a straight line has no vertex list to hide a dot in, where Pillow's own docstring reads "a connected sequence of line segments" and the package feeds it computed lists in four places
- **CARD-240** FR-044's examples AC still enumerates only rules A and B · P3 · tech-debt · score **9.0** (cycle 1/3, 1 low — fixed) · AC/EC/G PASS · merged **9f0ab10** · actual **0.1d** against 0.25d · ⚑ found independently by CARD-213's review AND its AC/EC/G gate, which is what earned it a card · ⚑ its reword came out of review: the first draft's "is the length of exactly one closed run of the line" can be read as the *line* having one closed run, which `test_puzzle_solver_clues.py:178` contradicts by circling both numbers on a line with two · ⚑ validators baseline-diffed to byte-identical output, which is the load-bearing check rather than the 86-warning count · ⚑ merge gate a **recorded deviation**: every test reference to `requirements.yml` is a docstring, not a parse, so the full suite cannot observe this change — 5 such files ran at 383 passed and full coverage defers to the wave smoke test
- **CARD-213** A clue number unique in its line gets circled wherever its run is closed · P2 · feature · score **9.0** (cycle 1/3 — 0 critical, 0 important) · 1 build-gate fix cycle · AC/EC/G gate PASS on every item (AC-1..7, EC-044, G-1..5, ADR-0038/R3+R4, GA-1..4) · merge gate 7502/0 · merged **cbd5a8e** · actual **0.2d** against 0.5d · ⚑ the reviewer **proved** rule C sound rather than accepting the argument: an independent re-implementation plus its own brute force over all clues x all mark strings for every length 1..8 — **63,211 placement-bearing cases, 0 violations** · ⚑ the ordering wart it leaves is **pre-existing and dominated by rules A and B**, measured: impossible marks already drew >=2 circles in 941 cases at n<=7 before this card, rule C adds 226 — so an ordering check belongs to A and B too, and is a later card · ⚑ **it had to amend CARD-235's frozen browser-family baseline to merge at all**: that guard's own AC-2 scoped it to CARD-235's diff ("this card changes fixtures, never coverage") but it shipped as a standing repository assertion reading "no card may ever add a browser test again". Baseline now derives from CARD-217's set union an attributed allowlist; the 8 historical 422s left byte-identical · follow-up CARD-240
- **CARD-238** The suite-timing tests stop asserting on gitignored host state · P1 · tech-debt · scores 6.0 → 7.5 → 7.5 → 6.5 → **8.0** (cycle 5/3) · 5 fix cycles, **two owner escalations** · merged 6c511a4 · actual **2.7d against 0.5d** · ⚑ verified in the main repo after the merge: `tests/test_suite_profile.py` is 341 passed where `test_the_real_log_is_entirely_well_formed` was red on main before · ⚑ **the family ran five occurrences of one shape** — a guard's stated coverage wider than its mechanism — and four of the five passes fixed the named instances while minting the next pass's unfalsifiable claim. What broke it was a change of kind, not another fix: deriving the listing surface from `dir(os)` / `dir(os.path)` / `dir(glob)` / `dir(pathlib.Path)`, which named `os.walk`, `os.fwalk`, `glob0` and `glob1` *before* the agent added them. The most transferable artefact is `test_the_control_for_each_spelling_depends_on_the_set`: a control must be caught WITH its set member and missed WITHOUT it — a guard on the guards' discriminating power. Every Critical after cycle 1 was found by **review**, not by the fix · bounds shipped as recorded controls → CARD-239
- **CARD-235** The browser tests stop paying for a page they throw away · P1 · tech-debt · score 8.0 then 9.0 (cycle 2/3) · 1 fix cycle · AC/EC/G 11/11 demonstrated, zero skips · merge gate 7228/0 (attempt 1 was a false red from a gitignored host file — see CARD-238) · merged 6ac8627 · actual 1.1d against 1d · ⚑ **its premise was refuted by measurement, which is the better outcome**: a Chromium page lifecycle costs 57 ms and the 0.33 s/test was `socketserver`'s 0.5 s poll in the per-test `live` fixture, so NO file's page scope changed. Family 39.78% → 29.78%, teardown 137.97 s → 11.62 s, from a one-line `poll_interval` kwarg — and the repo already knew, `test_web_server.py` has carried `_POLL_INTERVAL_S = 0.01` since the start with a comment saying why
- **CARD-234** The generated cover's title letters from packaged data · P2 · bug · score 9.0 (cycle 1/3 — 0 critical, 0 important) · AC/EC/G 11/11 demonstrated, zero skips · 6 mutants each red by name · merge gate 7205/0 with the normal 11 skips, the first fully-executed green suite it had · merged c6dfeed · actual 1.0d against 0.5d, almost all of it the guard investigation · ⚑ measured the defect it fixed: 52 px of cap height from the packaged face against 8 px from the sizeless `load_default()` — a seventh of the intended size on every cover the deployed panel generated · leaves 4 recorded follow-ups (over-wide title, log-only error surfacing, the tab asymmetry, the anti-cache guard's weak assertion)
- **CARD-237** The streaming-shape memory guard measures the export, not CPython's footprint · P1 · tech-debt · **cut in flight 2026-10-15 by owner decision to unblock the wave** · score 7.5 then 9.0 · 1 fix cycle · AC/EC/G 12/12 · merged 194cb40 · actual 0.7d against 0.5d · ⚑ `CHILD_HEADROOM` **removed, not widened** — the bound is a closed argument (16 export + 8 floor = 24 of the cap's 32, so passing both guards *proves* the child fits with a quarter unused) · ⚑ **two of its ACs were amended because I had written criteria that could not detect what they claimed**: AC-5 demanded in-suite runs only and was blind to the inverted-polarity flake the first fix introduced (five green suites certified it), AC-6 demanded execution of a test this kernel refuses to run
- **CARD-217** Profile the suite once, serialized, and commit the duration record the curation cards work from · P1 · tech-debt · score 9.0 (cycle 1/3 — 0 critical, 0 important, 8 minor; the reviewer re-derived every headline number independently) · 2 fix cycles, both spent making the measurement's own claims checkable · AC/EC/G gate passed, 63 mutants across the card · merge gate 7156/0 · merged 967a7fa · actual ~0.25d against 0.5d · **ran solo by owner decision, which is what makes the number usable** · ⚑ answer: the browser family is 39.78% of the suite — neither CARD-218's nor CARD-219's hypothesis; produced CARD-235/236 and re-pointed CARD-218/219/220
- **CARD-221** The book interior letters from packaged data, so a book's printed gutter stops depending on the machine that made it · P1 · architectural · score 7.5 then 8.5 · **5 fix cycles** · AC/EC/G gate failed once on AC-2 being true-but-unevidenced (CARD-205 had already delivered its outcome), passed on re-verification with 34 mutants across both passes · merge gate 7073/0 · merged 806dbe1 · actual 2.0d against 1d · ⚑ `Pillow>=10.0` unbounded is the one lever left, carded to the architect station
- **CARD-212** Big boards repeat their clues on both sides — left and right, top and bottom · P2 · standard · score 7.0 then 8.5 · 3 fix cycles · AC/EC/G gate passed with 14 fresh mutants, 14 killed · merge gate failed once on its own test racing a 600 ms bound under concurrent load, then 7053/0 · merged a2cd3f3 · actual 0.7d · found and fixed two defects CARD-193 had shipped
- **CARD-205** The table of contents lists sections, not puzzles — guide, each level's range, Solutions · P1 · standard · score 8.8 (cycle 1/3 — 0 critical, 11/11 mutants killed) · 4 fix cycles · AC/EC/G gate FAILED on G-1 (its named test had never existed; its mechanism clause described CARD-200's behaviour) — amended at the decompose station, then passed · merge gate 7019/0 in 1042s · merged d30e0f0 · actual 1d against 1d, the one card of this batch to land on its estimate · corpus 310 → 307 pages · ⚑ FR-043's per-puzzle ToC criteria + the legacy admin/pdf_generator.py ToC owed at the architect station
- **CARD-211** Region leaves the brush menu and becomes its own control · P2 · standard · score 9.0 (cycle 1/3 — 0 critical; 1 fix cycle for two owner decisions: brush and Region independent, trigger pinned to its widest brush) · AC/EC gate: all evidenced (AC-7 added at the gate) · merge gate 6971/0 · merged 4790243 · actual 0.5d · unblocks CARD-212 and CARD-216
- **CARD-204** Puzzle pages right-align by parity, gain a 2x2cm QR slot, and keep every two-up folio · P2 · architectural · scores 8.5 (cycle 4) then 6.5 (cycle 5, on the merge-gate fix: 1 critical, fixed) · 8 fix cycles · gate 6938/0 · merged cd641df · ⚑ FR-040/EC-027 + FR-032 amendments owed at the architect station
- **CARD-214** Single-puzzle generation can reveal given cells to make a non-unique picture uniquely solvable · P1 · architectural · score 8.1 (cycle 1/3, fix cycle 1 closed the gating finding) · AC/EC gate: all 8 ACs, 2 ECs, 7 guardrails evidenced · merge gate 6883/0 · merged d49e73a · ⚑ ADR-0024 (POL-008) + INV-002 amendment owed at the architect station
- **CARD-203** The solved-page caption sits closer to the puzzle and right-aligns with its grid · P2 · standard · score 9.5 (cycle 3/3, clean, after fixing a real caption/folio collision regression found across 2 cycles) · merged 0e955d5
- **CARD-200** The book's interior PDF gets a visible page number on every page and a table-of-contents page · P2 · architectural · score 10.0 (cycle 3/3, clean) — note: a subagent-overspawn incident during implementation is documented on the card, no repo impact · merged e899369
- **CARD-201** The guide page becomes a 2-page "How to Solve a Nonogram" tutorial, sourced from the owner's reference guide · score 8.5 (cycle 4/3+1, owner-extended) · merged ed578fa
- **CARD-202** Small solutions (width<=15, height<=20) pack 2-or-4 to a page instead of one full page each · score 9.0 (cycle 2/3) · merged 040f10d
- **CARD-177** Finalise and the book PDF downloads flash a generic error, not the exception's text · score 9.0 (1 cycle) · merged d1995fd
- **CARD-178** A book reopened in inches never shows a trim outside the stated limits · score 9.5 (cycle 3/3) · merged 862f673
- **CARD-179** The wrapped proof note keeps each number with its unit and never starts a line with "×" · score 9.0 (cycle 2/3) · merged c5c2177
- **CARD-180** Book selection: `?status=all` lists every status instead of nothing · score 9.5 (1 cycle) · merged ef83b2c
- **CARD-181** A batch remembers the tier it asked for, and its pages show it · score 9.4 (cycle 1/3) · merged 5e96945
- **CARD-182** Puzzle player cells are a usable tap target on a 390 px phone · score 9.5 (cycle 2/3) · merged 1164582
- **CARD-183** The puzzle player gets a Hint button that reveals one deducible cell · score 9.0 (cycle 3/3) · merged bd8eccb
- **CARD-184** One test holds every interior face to CON-020's 10 pt floor, and the two faces below it today are fixed · score 9.5 (cycle 1/3) · merged 9117567
- **CARD-186** The puzzle player gets a "?" mark and a "?" brush for assumptions · score 9.0 (2 cycles) · merged ddfc116
- **CARD-188** The puzzle player circles a clue number once the player's marks settle its run · score 9.0 (cycle 4, owner-granted) · merged 0d7c82e
- **CARD-185** The puzzle player reopens a puzzle in the state it was left in (this browser only) · score 9.5 (cycle 2/3) · merged ae25661
- **CARD-189** In the puzzle player, a click follows the selected brush · score 9.0 (cycle 3/3) · merged 0b637a9
- **CARD-187** The puzzle player shows the percent of correctly marked cells next to the error counter · score 9.0 (cycle 2/3) · merged b291141
- **CARD-190** Puzzle review's size filter goes by the longest side, like book selection · score 9.5 (cycle 3/3) · merged 22ce971
- **CARD-191** On the Arrangement step, a "Sort by size" button orders each level by longest side, then shortest side · score 9.5 (cycle 2/3) · merged cccfecb
- **CARD-192** The Arrangement page can show one longest-side size, with what is left or over against the plan · score 9.2 (cycle 1/3) · merged da93164
- **CARD-169** The Finalise screen's guide preview shows "How to Solve Nonograms" and its worked example, read from the generator · score 9.5 (2 cycles) · merged cd13b6a
- **CARD-170** Prove from the PDF's pixels that a puzzle's band prints once ("Puzzle 5 · Hard" drawn twice?) · score 9.5 (3 cycles; stalled at cycle 2, owner-chosen targeted fix) · merged a5a2b99
- **CARD-171** Finalise names a page-plan error on screen, and logs every other error it flashes · score 10.0 (2 cycles) · merged 7713c65
- **CARD-172** Proof pages render on square and landscape trims, with the note in a clear spot inside the frame · score 9.2 (1 cycle; AC-2 amended by owner) · merged 0d6fb58
- **CARD-173** An unreadable stored print setup says so once, names the remedy, and offers no override that cannot work · score 9.5 (2 cycles) · merged da0283f
- **CARD-174** Trim refusals and the Limits box speak the same inches · score 9.5 (2 cycles) · merged 3812815
- **CARD-175** On a phone, a /books row folds its off-plan hints behind one summary line · score 9.6 (2 cycles) · merged ecca05d
- **CARD-176** A malformed DATABASE_URL's error never echoes text that could hold the password · score 9.5 (1 cycle) · merged 62ea1eb
- **CARD-166** Admin paper cuts: "25×15", unclipped plan inputs, empty status filter · score 9.5 (1 cycle) · merged 570241f
- **CARD-167** The guide page becomes "How to Solve Nonograms" with a worked example · score 9.0 (2 cycles) · merged e77df9b
- **CARD-165** The book page numbers puzzles the way the printed book will · score 9.0 (1 cycle) · merged 3e14de2
- **CARD-164** Main goes green: fix the two tests that have been red for weeks · score 9.5 (1 cycle) · merged 4f3226e · full suite exit 0
- **CARD-168** Ops housekeeping: Render settings doc, test runner defaults to nonogram_test · score 9.5 (1 cycle) · merged cca9f0f
- **CARD-163** The puzzle player keeps the picture name hidden until it's solved · score 9.3 (1 cycle) · merged 159d6ad
- **CARD-162** The solver counts errors and celebrates a solved puzzle · score 9.5 (3 cycles; stalled at cycle 2, owner-directed test) · merged 4b5ed9d
- **CARD-161** Mark cells in the solver: tools, click cycle, drag, undo and redo · score 9.0 (2 cycles) · merged 8b485cc
- **CARD-160** The admin panel opens any puzzle in a solver page with its clues · score 8.5 (4 cycles; escalated at cycle 3, owner-directed fix) · merged 625ce14
- **CARD-159** Book forms keep what you typed and say the right step · score 9.4 (1 cycle; G-3 owner check pending) · merged 7101fbf
- **CARD-158** The book list and book page show what the book actually holds · score 9.5 (2 cycles; G-3 owner-confirmed) · merged 66214c1
- **CARD-157** Read a book's puzzles in one query, not one session per puzzle · score 9.5 (2 cycles) · merged 32e30b9
- **CARD-154** Print setup saves the plan and the trim together, and refuses "nan" · score 9.5 (2 cycles) · merged 677744c
- **CARD-153** Finalise doesn't hide a broken page plan behind "About N" · score 9.5 (3 cycles; escalated at cycle 2, owner-directed fix) · merged 11bea97
- **CARD-152** The setup and test-runner scripts check the database they will use · score 9.5 (2 cycles) · merged 02ea77a
- **CARD-156** The db_session fixture stops dropping tables other tests are using · score 9.0 (2 cycles) · merged c095b22
- **CARD-155** One difficulty classifier: retire the prototype's 30/70 tiers · score 9.5 (2 cycles) · merged 05a4ff6
- **CARD-151** The launcher's database check understands the URLs the panel accepts · score 9.0 (3 cycles; escalated at cycle 2, owner-directed fix) · merged 4fc5821
- **CARD-150** The local launcher refuses a database it cannot use · score 8.0 (1 cycle + fix) · merged 0aab707
- **CARD-147** The interior is written black-and-white or in colour · score 9.5 (1 cycle + fix) · merged 0fa9302
- **CARD-143** Type a puzzle's position in the arrange step · score 8.5 (1 cycle + 2 fixes) · merged 2bfd6b8
- **CARD-129** Finalise refuses a gutter KDP will reject for the page count · score 9.0 (1 cycle + fix) · merged ce5b3c7 · **closes Increment 15**
- **CARD-146** The frame reaches the printed two-up page · score 9.0 (1 cycle + fix) · merged b9a17d3
- **CARD-149** The guide page is legible at book size (6.7 pt → 11 pt) · score 9.0 (1 cycle + fix) · merged 2a18cf2
- **CARD-139** One import style in admin/ — a duplicate module tree cannot exist · score 9.0 (1 cycle + fix) · merged a8bdade
- **CARD-132** Books list — actual vs planned, exact hints, sort by completeness · score 8.5 (2 cycles) · merged 32fcc52
- **CARD-148** The DB driver is named, not inherited from a SQLAlchemy default · score 8.5 (2 cycles) · merged e292c1e
- **CARD-140** The arrange screen shows the book's real page breaks · score 9.0 (2 cycles) · merged 5d54019
- **CARD-144** A frame around the puzzle on book pages · score 9.0 (2 cycles) · merged e2a5b3b
- **CARD-131** A published book asks before its puzzles change · score 9.0 (3 cycles) · merged 293f921
- **CARD-128** Level dividers and the difficulty order in print · score 8.5 (1 cycle + fix) · merged 557c7ac
- **CARD-142** The bulk buttons follow a per-puzzle approve or reject · score 9.0 (2 cycles) · merged 87ea085
- **CARD-141** Answer-page rows take the height they need; spare white at the page foot · score 9.0 (1 cycle) · merged a83cc54
- **CARD-145** The book PDF written a page at a time (4.3 GB -> 132 MB) · score 9.0 (3 cycles) · merged 554c437
- **CARD-134** The packed answer key in the book PDF · score 9.0 (3 cycles) · merged 72f7a3b
- **CARD-130** Books reopen into the step workflow · score 9.0 (3 cycles) · merged a101db1 · ⏳ owner screenshot check
- **CARD-127** Two-up pages in the book PDF · score 9.0 (2 cycles) · merged 679e78a · ⏳ owner render check
- **CARD-138** Batch generation can ask for a difficulty · score 9.0 (2 cycles) · merged cc64540 · ⏳ owner should submit one Medium batch
- **CARD-118** Proof pages (30×30 + 15×15) for the owner's printed measurement · score 8.5 (1 cycle) · merged 2782887 · ⏳ owner print check outstanding
- **CARD-136** Print setup stores the chosen trim · score 9.0 (4 cycles) · merged cb0440c
- **CARD-137** Medium/hard cutoff 66 -> 90 · score 8.0 · merged a949244
- **CARD-126** Book level order · score 9.0 · merged ea35a7f
- **CARD-123** Tile cell + floor flag + override · score 9.3 · merged 8b7b78e
- **CARD-117** "Puzzle N · Tier" band + print strokes · score 9.0 · merged 837a6f3
- **CARD-116** Book PDF on its own trim · score 9.3 · merged dff610b
- **CARD-121** 4.8 mm floor + override · score 9.0 · merged 9b2cfb7
- **CARD-133** Answer tiles · score 8.0 · merged be12385
- **CARD-124** Book readiness gate · score 9.0 · merged 238c6c0
- **CARD-122** Selection by longest-side tab · score 8.5 (3 cycles) · merged 37f1b68
- **CARD-125** Pair-aware two-up layout · score 9.0 · merged b106796
- **CARD-115** Book PageSpec builder · score 8.5 · merged 9f15c55
- **CARD-120** Plan stored with the book · score 8.5 · merged bc799f2
- **CARD-114** PageSpec · score 8.8 · merged e854cfc
- **CARD-135** Interior PDF without the cover, cover separate · score 9.0 · merged 1541007
- **CARD-119** Distribution plan as pure domain · score 9.0 · merged da6cf84
- **CARD-113** Golden A4 tripwire · score 9.0 · merged 365a7ff
- **CARD-112** P3 · The C4 diagrams show the system that ships — COMP-008 drawn for the first time, COMP-009/010 added, containers go from one to three · every arrow backed by a cited call or import; one label corrected before commit (book PDFs stream, never touch disk) · two arrows absent on purpose and explained in the diagram · not rendered — PlantUML unavailable — but a mutation-tested structural check passes · closes the CARD-110 → 111 → 112 thread · merged without a review cycle, at the owner's call · merged e6d93f0
- **CARD-111** P1 · CON-017 supersedes CON-003 — "no persistence, ever" had been contradicted by six tables, ten migrations and a deployment, while still serving as the premise for three C4 diagrams and two decisions collapsed rather than taken · split by surface (the pipeline is still stateless, the admin panel is the one exception) following ADR-0030, with the vision's Non-goals amended in the same change · the dead `users` tables are stated, not quietly narrowed away · both collapsed decisions annotated, neither reopened · unblocks CARD-110's AC-3 · merged without a review cycle, at the owner's call · merged ccedcc8
- **CARD-110** P2 · `admin/` and `db/` get component ids — COMP-009 and COMP-010 now own 38% of the package that no component did, so rows about admin behaviour stop naming COMP-008 (the web UI) · three rows repointed, though not the three the card named · **AC-3 deliberately not done**: both C4 diagrams assert the tool has no database, and CON-003 still says "no persistence beyond local file export, ever" while the admin ships Postgres — CON-001→CON-007 is the precedent for fixing it, and it is the owner's call · merged without a review cycle, at the owner's call · merged 353d83a
- **CARD-056** P3 · ADR-0032, and the two consumers that disagreed with it — the admin's storage path had no recorded guarantee, so `quality_score`'s `None` was answered three different ways · R1 writes down CARD-080's uniqueness guard; R2 defines the metric and fixes the `TypeError` two live routes could reach plus the book printing `Quality: None/100` · deployed Postgres behaviour unchanged — the in-memory path now agrees with it · printed wording chosen by the owner on a rendered page · 7 of 8 tests red first, 4 mutants all caught · merged without a review cycle, at the owner's call · merged 4158e4b
- **CARD-105** P3 · AC-137 checked by running both implementations — the old parity test asserted `math.gcd` against hardcoded numbers and grepped the JS for function names · node now runs metadata.js's own functions, cut from the shipped file, against metadata.py over 16 ratios; they agree, 1:1's 21-way tie included, because both sorts are stable (ES2019) · no production change: the card's own export-hook plan would have had to touch CARD-063's bounds path · 5 of 6 mutants caught, the sixth proven equivalent rather than chased · merged without a review cycle, at the owner's call · merged 5344de8
- **CARD-055** P3 · MockGenerator moves to the test tree — never reachable from a production route, but it sat in src/ under a name that reads as a real generator option, one mistaken import from writing invented metrics into a batch · copied verbatim, output byte-identical at four seeds · two tests patched the module it used to live in and failed correctly; the target follows the class, and both were mutation-checked in their new position · the two invented fields stay invented (option 1) · merged without a review cycle, at the owner's call · merged df192c1
- **CARD-053** P3 · The unreachable second generator is gone — generation/ had no production caller and never had one, so it went with its 21 tests and the three CARD-050 AC-3 tests that parsed it by path · analysis/strategy_counter.py kept deliberately as DIFFICULTY_ENGINE.md's prototype while the rescoring question is open, at the stated cost of having no importer left · the architecture docstring stops being silent about admin/, db/ and analysis/, and stops claiming "exactly two adapters" without saying it means the pipeline's · admin//db/ component ids left for the owner (trace.yml:1414) · option B of three · merged without a review cycle, at the owner's call · merged 8bc5e52
- **CARD-071** P3 · The documents now point at documents that exist — the headline task was already done, and two citations resolved to the WRONG requirement rather than to nothing · fixing two out-of-schema trace statuses unmasked nine dead test links the invalid word had been hiding · the banner the card specified was itself stale · 4 validator errors become 1, and the survivor is the validator's own regex bug · CARD-074 F-001/F-002 closed · merged without a review cycle, at the owner's call · merged 19eca81
- **CARD-052** P2 · The Minimum Quality Score filter is exercised at its boundary — two of three criteria had landed with CARD-050; AC-3 was genuinely uncovered, and the filter's failure mode is an empty batch that reads as "no good pictures" rather than a bug · threshold derived from the picture, not guessed · 4 mutants all caught · merged without a review cycle, at the owner's call · merged 43385ec
- **CARD-109** P1 · The suite refuses a database nobody chose — stops before collection unless `DATABASE_URL` is unset, names a test database, or the opt-out is set; never connects, never echoes the credential · the card's own "four exposed files" was wrong and is corrected in place: one was · merged without a review cycle, at the owner's call · merged 8135200
- **CARD-106** P2 · The AC-122..AC-143 collision is visible where it is read — a marker above each of the 22 registry entries (what a grep actually hits), a header note, and a banner per card naming the registry's meaning · nothing renumbered, verified by hashing the id set against main · merged without a review cycle, at the owner's call · merged 72370a3
- **CARD-043** P2 · The last result clears when a different picture is chosen — the one card of the wave-0 web family with work actually left · the mutation check found two flaws in the *tests*, not the code: an assertion satisfied by selector text in the page's own script, and a regex that matched both change listeners as one span · merged without a review cycle, at the owner's call · merged 2530c32
- **CARD-108** P2 · Deleting a book lets go of its puzzles in both storage modes — memory mode stranded them, and CARD-100's guard then refused to curate them ever · five failures before the fix, all five in memory mode · 3 of 4 mutants, the fourth confirming the design · merged without a review cycle, at the owner's call · merged 1a94ccd
- **CARD-107** P1 · A puzzle pointing at a book that is gone — the state `backfill` cannot see, because it walks books · found by a failed Render deploy; the migration refused safely and named the row · `release_orphans` clears the column the constraint would have cleared on delete · reproduced and fixed against real Postgres · merged without a review cycle, at the owner's call · merged df549ae
- **CARD-034** P2 · Client-side image metadata — the feature shipped; AC-138's fallback clause retired (it named CARD-031's server-side path, which never ran and CARD-104 deleted) · three unfailable assertions deleted, including `assert "if" in content` · the card's own claim that nothing can run the JS corrected — `node --check` does · parity deferred to CARD-105 · merged without a review cycle, at the owner's call · merged 989cad0
- **CARD-044** P1 · The picture a retry is holding is on screen — the result page had no preview markup at all, which the card had not noticed; `GET /upload/<token>` serves the retained upload and 404s everything it did not mint · AC-165 inverted, because CARD-037 keeps the picture that criterion assumed was gone · merged without a review cycle, at the owner's call · merged 666f685
- **CARD-037** P2 · A rejected submission keeps its picture — by opaque token, never a path: the salvaged design accepted a filesystem path from the client and opened it as the picture · retention ends when the *picture* was what was refused, which the suite caught · 4 of 5 mutants, the fifth reported rather than dressed up · merged without a review cycle, at the owner's call · merged e531cc7
- **CARD-103** P2 · `puzzles.book_id` constrained — `ON DELETE SET NULL`, migration 009 · unblocked by the owner's deploy and backfill · verified against real Postgres including its failure mode (a violating row leaves the upgrade refusing at 008, untouched) · five tests that fabricated book ids fixed with a new `make_book` helper · merged without a review cycle, at the owner's call · merged 9dd1480
- **CARD-104** P2 · Opened on a false premise and says so — CARD-030 and CARD-033 were tested all along under names their cards did not predict; the broken `*test:*` trail was the whole defect · the real find was CARD-031's server-rendered metadata, which no page ever produced: computed on every upload and discarded inside a catch-all except, now deleted · CARD-030/031/033 closed, six review files recovered · suite unchanged at 3,613 · merged without a review cycle, at the owner's call · merged 2780ef0
- **CARD-032** P2 · Web form image-only — the feature had shipped; AC-129 and AC-130's tests were **recovered** from the never-merged 2026-09-03 branch (retired as `card/032-superseded-2026-09-03`) and each given a stronger sibling · the PDF font citations re-pointed at ADR-0006/DEC-027, whose implementing card is missing rather than misnamed · AC-number collision with FR-028 recorded · merged without a review cycle, at the owner's call · merged be91cff
- **CARD-102** P2 · The test database enforces foreign keys, as production does — 29 failures and 14 errors were hiding behind SQLite's default; fixed by creating the batches the tests referenced, through one shared helper · the `book_id` constraint deferred to CARD-103 · no schema and no production code changed · merged without a review cycle, at the owner's call · merged a05e500
- **CARD-078** P3 · Density 0 and 100 refused — valid range 1..99, the verdict made once at `validate_density` and the docstring that promised a later stage would reject them deleted · the adapter audit changed nothing and says why · AC-B re-asked, since the web form has had no density field since CARD-032 · merged without a review cycle, at the owner's call · merged 4fda006
- **CARD-060** P3 · `grid_to_svg_bytes` and `get_svg_filename` removed from grid_renderer — zero callers re-confirmed before deleting; two imports went with them that this card did not make dead · AC-2's grep is a test now · merged without a review cycle, at the owner's call · merged 9d0ab5a
- **CARD-101** P1 · The book's JSON columns are mutation-tracked — "move up", "move down" and every title after a book's first were silently discarded in DB mode; the page count too · fixed in three column declarations, no call site changed · measured before and after through fresh sessions · one mutant survived and is reported, not papered over · merged without a review cycle, at the owner's call · merged 3bc8fa6
- **CARD-100** P1 · A puzzle in a book is protected again — membership written to both `Book.puzzle_ids` and `Puzzle.book_id` in one gesture; the three per-puzzle status changes became one rule, so a booked puzzle cannot even be rejected · the book builder stops offering a puzzle another book holds · backfill ships with a dry run, owner runs it (G-2) · `remove_puzzle_from_book` did nothing in DB mode and is fixed — the four with the same bug are CARD-101 · merged without a review cycle, at the owner's call · merged 0360c05
- **CARD-068** P2 · Batch results — the per-puzzle Delete (rejected only, option (a)), confirmations that name their count, and reports that say what needed nothing · re-cut first: `db4e0dc` had shipped the three bulk actions outside the board, and AC-2's >100 clause was retired (MAX_BATCH_COUNT is 50) · the in-book clause left unbuilt and the sidebar's untrue reassurance removed — see CARD-100 · verified on the rendered page · merged without a review cycle, at the owner's call · merged 3223753
- **CARD-099** P2 · The generated page counts pictures and puzzles separately, and a picture's sizes read as a group — heading per picture (option (a), owner's pick) · fixes a count CARD-069 broke ("2 puzzles from 2 pictures" for one picture) · the shortfall no longer blames the quality threshold · verified on the rendered page · merged without a review cycle, at the owner's call · merged 2ac201a
- **CARD-069** P2 · Up to four size options per picture, one puzzle per size — the last of the 2026-09-12 admin review items · every pre-existing single-size test passed untouched · merged without a review cycle, at the owner's call · merged 19564e5
- **CARD-067** P2 · Preview cards — picture left, ink ratio right, remove a picture · re-cut 2026-09-19: the live-prediction half had shipped on main meanwhile, so the stale branch is retired as `card/067-superseded-2026-09-12` and the rest was rebuilt · verified on the rendered admin · merged without a review cycle, at the owner's call · merged 9c97d88
- **CARD-098** P2 · The Guess tier retired — three score bands, branching reported as the `guess` strategy; ADR-0031 supersedes ADR-0025 · never assigned in ~7,400 measured puzzles · one of the two standing suite failures deleted with it · merged without a review cycle, at the owner's call · merged 0df8d63
- **CARD-097** P2 · A database that never answers no longer stops the suite — connect deadline, reachability probed once a session, faulthandler net dumping to a file · with Postgres listening: never finished → 2 m 08 s · merged without a review cycle, at the owner's call · merged a073d5c
- **CARD-072** P2 · A puzzle records the strategies its solve needed — carried to the JSON export (with CARD-079's deferred `binarisation`, no schema bump) and filterable in the admin list · merged without a review cycle, at the owner's call · merged 50996b6
- **CARD-079** P2 · Silhouettes thresholded, photographs dithered, blank conversions guarded — owner's visual gate discharged, ADR-0026 Accepted; shipped vs dither over 125 conversions: 110 vs 109 made, 91 vs 80 unique first time, 39 vs 53 nudges, 0 regressions · merged without a review cycle, at the owner's call · merged 97dc287
- **CARD-075** P2 · Image-mode nudge adds one cell per attempt from where the solver's witnesses disagree — 107 of 125 corpus conversions made against 89, 0 regressions; admin loss 3/5/7/7 → 2/2/3/3 · AC-172 closed at 18 of 19, owner kept the ink-boundary ranking · merged without a review cycle, at the owner's call · merged bb35762
- **CARD-096** P2 · Image-mode abandonment measured by cause — admin loses 3-7 of 25 per preset; witnesses disagree on 4 cells in 27 of 34; CARD-075 revised from it · a measurement, merged at the owner's call · merged ade79e8
- **CARD-095** P3 · An image batch stops on its own clock, as a random batch does — checked before every generate call, unstarted pictures stay loaded · merged without a review cycle, at the owner's call · merged d50bce7
- **CARD-094** P3 · Nothing still says 20 attempts or 200 puzzles where it means the live bound; the image preview reads the real ceiling · merged without a review cycle, at the owner's call · merged 949471a
- **CARD-093** P3 · A random batch that stops early keeps the puzzles it made — stored as made, COMPLETE with a note · merged without a review cycle, at the owner's call · merged 3a7f309
- **CARD-092** P3 · The generation algorithm reference describes the loop the code runs — §8 repair, §9 batches, findings re-established, symbol references checked by script · merged without a review cycle, at the owner's call · merged 50ba053
- **CARD-091** P2 · K recalibrated from 3 to 5 — measured (30x30 95% → 99%, wall clock 329 s → 226 s) · merged without a review cycle, at the owner's call · merged b27435c
- **CARD-090** P2 · The retry bound moves to 30 — measured at the knee of the curve (85% → 95% at 30x30) · merged without a review cycle, at the owner's call · merged 5d4bc3a
- **CARD-089** P2 · The retry bound measured, and left at 20 · closed as a measurement, no code change · merged d575708
- **CARD-088** P1 · A batch stops on its own clock, not on the worker's · merged without a review cycle, at the owner's call · merged 55d83a5
- **CARD-087** P2 · The synthetic image fixtures are what their tests say they are · merged without a review cycle, at the owner's call · merged 964b3c7
- **CARD-084** P3 · Drop the legacy difficulty columns — the snapshots replaced them · merged without a review cycle, at the owner's call · merged 20e9203
- **CARD-086** P2 · Serve the deployed admin with gunicorn, bound its slowest route, and say why a request was refused · merged without a review cycle, at the owner's call · merged f381d62
- **CARD-085** P1 · The admin panel can be reached from somewhere other than this machine, but only with a credential · score 9.0 (cycle 2/2) · merged 84fcc46
- **CARD-083** P2 · A batch survives a candidate it had to abandon · score 8.0 (cycle 1/1) · merged d3db715
- **CARD-082** P2 · The suite baseline says what it means — three standing failures and one 40% flake · score 9.0 (cycle 1/1) · merged a13c9bf
- **CARD-070** P2 · Generation quick fixes — batch tier spelling, stale nudge pins, docstring drift · score 9.0 (cycle 1/1) · merged 4362a7e
- **CARD-080** P1 · No write path can store a puzzle that is not uniquely solvable · score 8.5 (cycle 2/2) · merged b40e6b1
- **CARD-077** P2 · Re-grade the admin DB under the ladder scale — admin action, backup first, legacy columns kept · score 8.5 (cycle 2/2) · merged 3de767f
- **CARD-081** P1 · The admin panel binds loopback like the web UI does, and a test says so · merged without a review cycle, at the owner's call · merged 44a5af4
- **CARD-076** P1 · Difficulty by strategy ladder and the Guess tier — no clock, no size, one classifier · score 9.0 (cycle 2/2) · merged 76c1df4
- **CARD-074** P1 · Repair before redraw — flip one filled/empty pair inside the disagreement set, K=3 per lineage, one shared bound · merged aa6d863 · review 8.5
- **CARD-073** Solver exposes the undecided mask, a second witness on MANY, and the rung that settled each cell · score 9.0 (cycle 2/2) · merged ab851eb
- **CARD-066** Filter the puzzle review by status (draft / approved / rejected / in book) · score 9.5 (cycle 3/3) · merged d07f2a2
- **CARD-065** Small follow-ups from CARD-061..064 — honest percentages, preset labels, stale tests · score 9.5 (cycle 2/3) · merged 18a2287
- **CARD-064** Thin pictures — move up to Large instead of cropping, or say it can't be done · score 9.0 (cycle 2/3) · merged be582ea
- **CARD-063** One source of truth for the grid size range — shared `limits` module · score 9.0 (cycle 2/3) · merged 0a77655
- **CARD-062** Admin batch — retry an abandoned picture at long side ±1 before giving up · score 9.5 (cycle 2/3) · merged 696871d
- **CARD-061** Admin "small" preset — 10 is the short side, the long side follows the picture (+ large preset 30) · score 9.0 (cycle 2/3) · merged 3cf8517
- **CARD-058** Surface a note when admin silently substitutes the predicted puzzle size · score 8.5 (cycle 1/3) · merged 6f87e3c
- **CARD-059** Remove the unreachable, unverified SVG-preview-by-file_id routes · score 9.5 (cycle 1/3) · merged 47ca753
- **CARD-057** ADR-0006/R1's dependency baseline is stale — reportlab was added without updating it · score 9.0 (cycle 1/3) · merged 94c5a8d
- **CARD-054** Remove dead code — BatchGenerator._generate_puzzle_with_metrics · score 9.5 (cycle 1/3) · merged 77c450f
- **CARD-048** Widen ADR-0022/R3 and R4 scope.code to include the admin panel · score 9.5 (cycle 2/3) · merged b154886
- **CARD-047** predict_size() adds a synchronous full-image decode to batch page renders · score 9.0 (cycle 1/3) · merged 8e5b818
- **CARD-046** Regression test for ink-bbox-vs-file-dimensions sizing fix · score 9.5 (cycle 1/3) · merged 261706a
- **CARD-051** Stop reimplementing clue encoding in admin — call nonogram.clues · score 9.5 (cycle 1/3) · merged 352670f
- **CARD-050** quality_score and recognizability are hardcoded fakes, not measurements · score 9.0 (cycle 3/3) · merged 62f8c62
- **CARD-049** Route admin image-mode generation through the solver-verified pipeline · score 9.0 (cycle 1/3) · merged 98cdaaa
- **CARD-045** predict_size() can crash a whole batch page on a degenerate image · score 9.0 (cycle 1/3) · merged 2fc8094
- **CARD-199** Extend KDP's gutter table past 300 pages so larger books still finalise · score 9.5 (cycle 1/3) · merged 7d4bcf8
- **CARD-197** A new full-page solved layout: clues top and left, light-gray gridlines between filled cells · score 9.0 (cycle 2/3) · merged 81156b1
- **CARD-196** The puzzle player's clue numbers get their own size, independent of the cell, with a 12 px minimum · score 8.5 (cycle 3/3) · merged d7ba2ac
- **CARD-193** The puzzle player fits big boards to the phone width and mirrors row clues on the right above 15 cells · score 9.5 (cycle 3/3) · merged c51982a
- **CARD-194** The puzzle player's brushes become one dropdown with a Region option; a drag scrolls the page unless Region is picked · score 9.0 (cycle 1/3) · merged e0214c9
- **CARD-198** The book's answer key becomes one full solved page per puzzle, replacing the compact 6-up grid · score 8.5 (cycle 1/3) · merged da0f8bb
- **CARD-195** The puzzle player can zoom the board in and out · score 9.3 (cycle 2/3) · merged 1b4bc97
- **CARD-001** Package scaffolding and CLI entry point
- **CARD-002** Clue derivation via run-length encoding
- **CARD-003** Random grid sourcing with size and density validation
- **CARD-004** Nonogram solver with fail-fast uniqueness check
- **CARD-005** Pipeline orchestrator and regenerate-on-failure loop
- **CARD-006** Cooperative generation deadline and SolverTimeout
- **CARD-007** JSON export and the export-readiness gate
- **CARD-008** Built-in image library sourcing
- **CARD-009** Difficulty scoring formula from solver signals
- **CARD-010** Difficulty tier selection and resample loop
- **CARD-011** Puzzle naming (auto-generated and --name override)
- **CARD-012** PNG and SVG export renderers
- **CARD-013** CSV export and exact round-trip fidelity
- **CARD-014** Two-page PDF export with answer key
- **CARD-015** Uploaded-image conversion via resize and Floyd-Steinberg dithering
- **CARD-016** Bounded pixel-nudge recovery loop for image mode
- **CARD-017** Nudge-count reporting in CLI output
- **CARD-018** Strengthen solver search to meet AC-037 at 20x20 mid/low density
- **CARD-019** Web UI server skeleton, `nonogram serve`, and the adapter import allowlist
- **CARD-020** Web UI generation submission — form to pipeline to result page
- **CARD-021** Image upload via hand-rolled multipart parsing
- **CARD-022** Repair the web adapter's false claims and vacuous guards
- **CARD-023** Narrow the supported grid range to 10..30 project-wide, with a measured 30x30 deadline fixture
- **CARD-024** Export metadata carries width and height at schema version 2
- **CARD-025** Printed cell size becomes min(comfort cap, page fit)
- **CARD-026** Fit uploaded images to the requested grid shape, refusing a >2x aspect mismatch
- **CARD-027** Grid extent as a (width, height) pair through the request, `--size NxM`, and all three source modes
- **CARD-028** Web form's size field accepts the `NxM` extent token
- **CARD-029** Retire the last stale 10..50 range claims left by CON-011
- **CARD-035** Include source image filename in export (traceability)
- **CARD-038** Clear previous result message when submitting new generation ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-039** Clear size field when new image is uploaded ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-040** Implement suggestion algorithm (metadata.py module) ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-041** Add colored backgrounds to result messages (success/error visual distinction) ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes
- **CARD-042** Display image preview after upload ⚑ reconciled against `main` via `96da6ac`, not merged normally — see card notes

## Repository integrity note

`main` and the `card/037-044` worktree branches share **no common git
ancestor** (two disjoint root commits: `main` → `fb2ec7f`, the old chain →
`b7d14ca`). `96da6ac "feat: restore core nonogram modules and silhouette
images"` (2026-09-08) is a file-level restore from a backup onto `main`, not a
git merge — it is why `main` independently has equivalent functionality for
5 of these 7 cards despite no shared history.

**2026-09-11 — worktree cleanup, on confirmation:** `../PythonProject4-CARD-038`,
`-039`, `-041`, `-044` removed (`git worktree remove`, all clean, no uncommitted
changes). `../PythonProject4-CARD-037` removal was **correctly refused by git**
— it holds real, never-committed CARD-037 implementation work, preserved as a
patch (see CARD-037's own Worktree notes) before deciding what to do with it.
`../PythonProject4-CARD-040` and `../PythonProject4-CARD-042` also removed
(confirmed clean immediately before removal). The only worktree remaining
outside the main repo is `../PythonProject4-CARD-037`, kept deliberately —
it holds the uncommitted CARD-037 implementation work (see that card's notes).

Branch objects (`card/038-...` etc.) were not deleted — `git worktree remove`
only removes the working-tree checkout, not the branch ref itself.
