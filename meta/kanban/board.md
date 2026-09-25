# Kanban Board

_Updated: 2026-09-24 UTC_

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
| 26 | CARD-145 P0, CARD-128 P2, CARD-131 P2, CARD-132 P3, CARD-139 P1, CARD-140 P1, CARD-141 P2, CARD-142 P1, CARD-144 P2 | ⏳ 6/9 merged — CARD-132, CARD-140 next, CARD-139 last and alone · CARD-142 in review · CARD-128 + CARD-144 implementing · closes Increment 16 · CARD-139 runs last, alone (import sweep over app.py) |
| 27 | CARD-129 P2, CARD-143 P2, CARD-146 P2, CARD-147 P2, CARD-148 P1 | ⏳ blocked (→ wave 26) · closes Increment 15 |

_Note (2026-09-22): all 111 cards of waves 1–19 (CARD-001..CARD-112) are `done`. Waves 20–27 are the book generator (handoff Increments 13–16, CARD-113..CARD-135; CARD-133/CARD-134, the answer key, added by the 2026-09-22 (c) delta), numbered after the finished waves so `waves.yml` attribution cannot collide with them. The 2026-09-22 (d) delta added CARD-135 (interior PDF without the cover, cover as its own file; wave 20, before CARD-116's page parity) and folded the answer-key details into CARD-133/CARD-134/CARD-128; no wave was renumbered. Checkpoints per wave: [meta/kanban/waves.yml](waves.yml). The CON-019 golden-A4 tripwire (CARD-113) must stay green at the end of every book wave._

_Gantt: [meta/kanban/gantt.md](gantt.md)_

## Backlog
- CARD-135 follow-up: cover download on books list / book detail
- CARD-135 F-008 export_book docstring
- Pre-existing failure: test_size_configuration_applied

## Architecture
_(none)_

## Ready
- **CARD-148** P1 · The DB driver is named, not inherited from a SQLAlchemy default (prod outage 2026-09-25) · 0.5d · wave 27
- **CARD-147** P2 · The book PDF is written black-and-white or in colour (owner, print cost) · 1d · wave 27 · ⏸ blocked: after CARD-146
- **CARD-146** P2 · The frame reaches the printed two-up page (CARD-144 gap, owner's ruling) · 0.25d · wave 27 · ⏸ blocked: after CARD-128 + CARD-144 merge
- **CARD-132** P3 · Books list — actual vs planned, exact hints, sort by completeness · 0.5d · wave 26 · Inc 16 · after CARD-123, CARD-124, CARD-130
- **CARD-139** P1 · One import style in admin/ — a duplicate module tree cannot exist (live Print setup 500) · 0.25d · wave 26 · runs last, alone
- **CARD-140** P1 · Arrange screen shows the real page breaks (owner: "3 per page even for big ones") · 0.5d · wave 26 · after CARD-128
- **CARD-143** P2 · Type a puzzle's position in the arrange step (owner-requested) · 0.5d · wave 27 · after CARD-140
- **CARD-129** P2 · Finalise refuses when the interior page count needs a larger KDP gutter (cover not counted) · 0.5d · wave 27 · Inc 15 · after CARD-128, CARD-123, CARD-134

## In Progress


## Review

## Done
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
