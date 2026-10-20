# CARD-254: Shrink CARD-252's private-globals guard to the part that has authority

**Status:** in_progress
**Priority:** P2
**Category:** tech-debt
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/254-shrink-the-private-globals-guard
**Worktree:** ../PythonProject4-card-254
**Source:** CARD-252 review cycle 3's direct answer to "is this guard worth keeping at all?" — *"No, not at this size. I'd keep about a fifth of it."*
**Idea:** —
**Wave:** 49
**Depends on:** — (CARD-252 is merged; this card edits what it shipped)
**Touches:** tests/test_db_engine_lifecycle.py, src/nonogram/db/session.py (docstring only), meta/architecture/ — no
**Review score:** —
**Started:** 2026-10-20T05:15:11Z · **Closed:** — · **Actual:** — · **Merge commit:** —
**Blocked by:** —

## Why

CARD-252's AC-5 guard — "no test reaches into `session.py`'s private globals" — cost **three review
cycles, nine helpers, ~180 lines of AST machinery, ~220 lines of docstring claims and eleven
controls**, and caught **zero real violations**: the nine sites it reports are the nine it was
written around, and a full-tree triage found nothing new (0 unanalysable, 2 declared residual, 328
correctly out of scope). Every gating finding on that card was the guard's description of itself.

The final reviewer's reason is the one to carry: **a convention enforced at review is honest about
being a convention; an AST deny-default is a *proof* claim, and a proof claim in a dynamic language
always has one more axis.** That card paid three cycles to learn it at one axis per cycle —
spellings, then argument binding, then (measured at zero sites) computed targets.

This card is not a retraction of CARD-252. The engine fix merged with zero production delta and is
not in question. What shrinks is the guard around it.

## What to implement

**Keep (~55 lines — the part with real authority):**
1. `_global_names_assigned_by` + `test_it_resets_exactly_the_globals_the_builder_creates` — the one
   genuinely *derived* authority in the file, so a fourth global added to `_init_engine` tomorrow is
   inside the check that day. Cycle-1 mutant R4 killed it; keep that control.
2. The AST call-site test and the public-seam test (M1/M1b kill them).
3. The exemption **equality**, reduced to a cheap per-file **textual** count of the three literal
   global names. It still reds on a new file, a new name or a tenth site — and it makes **no claim
   about reach**, so there is nothing left to probe.

**Retire (~400 lines of code and prose):** `_is_setattr_call`, `_string_target_tail`,
`_string_target_module`, the arity dispatch, the binding-frontier helpers and the five shape
controls — replaced by a declared convention in `session.py`'s docstring and one line in the
engineering standards: *tests do not hand-set `session.py`'s engine globals;
`test_db_url_driver.py` and `test_db_connect_timeout.py` are the recorded exceptions; a new one is a
card, not a commit.*

## Acceptance criteria

- **AC-1** *Given* the reduced guard, *when* a test in a new file hand-sets one of the three engine
  globals, *then* the guard reds and names the file. (test: the kept exemption-equality test)
- **AC-2** (the control) *Given* the kept derived check, *when* a fourth global is added to
  `_init_engine`, *then* `test_it_resets_exactly_the_globals_the_builder_creates` reds with the name.
  (test: the same, under the R4 mutant — recorded on the card)
- **AC-3** *Given* the retirement, *then* **every** retired test is named with its survivor or
  recorded as deliberately unreplaced with the reason. A reach the new guard cannot see is stated in
  the convention, not left implicit. (test: the card's own retirement table + G-6)
- **AC-4** *Given* the new convention text, *then* it says what it does **not** enforce. The failure
  this card exists to end is a guard whose claim is wider than its mechanism; a convention that
  claims to be a guarantee repeats it in prose.

## Guardrails

- G-1: `src/nonogram/db/session.py` keeps `reset_engine()` and its call site unchanged — **docstring
  edits only**. Prove it the way CARD-252's cycles did: docstring-stripped AST identical.
- G-2: No test is made to skip. The suite's skip profile is unchanged (1 on this machine).
- G-3: No test retired without a named survivor **or** an explicit "deliberately unreplaced, because
  …" line on the card.
- G-4: `nonogram_poc` is never created, dropped, connected to or truncated;
  `_refuse_unless_test_database` is neither widened nor bypassed.
- G-5: No new runtime dependency (ADR-0006/R1).

## Worktree notes

- **[Do not take timing measurements]** other cards share this machine.
- **[The trap]** This card *removes* a control. The failure mode is removing the part that had
  authority and keeping the part that was decorative. The kept list above is not a suggestion: it is
  what cycle 3 measured as load-bearing (R4 kills the derived check; M1/M1b kill the call-site test;
  the exemption equality reds on a tenth site). Anything you keep beyond it needs its own killing
  mutant, and anything you drop from it needs an argument.
- **[System contract]** to be derived at dispatch under `meta/kanban/curation.md`.

## System contract

Curated to **10 of 29** in-scope rules under `meta/kanban/curation.md`: every rule whose
enforcement does not reach this card's new code is kept; the rest are dropped because the suite runs them
on every gate. **19 dropped.**

- **ADR-0022/R1** — _review-lens — nothing executes it_
  Grid extent crosses module boundaries as a (width, height) pair. No public function signature,
  request field, or export field reduces a grid's extent to a single scalar "size", and no source
  mode constructs a grid from one integer.
- **ADR-0036/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  Exactly one function in src/nonogram/** puts a round mark on a page. A second one is a defect
  whatever Pillow call it is written with: four cards print the same difficulty glyph, and four
  slightly different dots cannot be fixed once a book is on paper.
- **ADR-0036/R4** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  No string literal anywhere in src/nonogram/** -- docstrings included -- holds a codepoint in
  U+25A0..U+25FF, U+2022 or U+2219. A round mark is drawn, never typed: the cheapest way to print
  a difficulty dot is to append a bullet to a header string, and that route bypasses the one
  drawing site and CON-020's type floor at once.
- **ADR-0038/R6** — _review-lens — nothing executes it_
  Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a puzzle's solution
  grid to the browser. A public or reader-facing player must not send the solution before the
  puzzle is solved, and any public phase reopens this ADR (CON-021).
- **ADR-0038/R7** — _review-lens — nothing executes it_
  Browser tests use pytest-playwright with Chromium, declared only in a dev-only extra in
  pyproject.toml. It is never added to project.dependencies or to the admin extra.
- **ADR-0038/R8** — _review-lens — nothing executes it_
  Browser tests run locally, against Chromium installed by `playwright install chromium`. When
  Chromium is not installed, browser tests fail or skip loudly, with a named skip reason visible
  in the run summary. They never pass silently. Once a CI pipeline exists, it installs Chromium
  (playwright install chromium) before running them; until then there is no CI, and that is a
  known gap, not a met clause.
- **ADR-0039/R1** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A set a guard consults needs a completeness test written before the set, and any claim the guard
  makes about what it catches needs a control that can fail: caught WITH the set member present,
  missed WITHOUT it. A claim whose control cannot fail is narrative, not coverage, and must be
  narrowed to what is measured or deleted.
- **ADR-0039/R2** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  A guard's set is derived from an authority the runtime can enumerate, not hand-written. Where no
  such authority exists, the guard defaults to deny: a shape it cannot analyse is a FAILURE, never
  a silent pass, and the unanalysable sites become named exemptions under ADR-0039/R3.
- **ADR-0039/R3** — _`kind: test`, but its ADR declares the check's reach stops at the code that existed when it was written_
  An exemption is a claim. Every exemption a guard grants carries a control for what it must NOT
  absorb — caught with the exemption removed, missed with it in place — is held to an equality
  against the sites that exist today, and records whatever it still cannot see as a measured bound
  with its own failing control.
- **CON-021** — _review-lens — nothing executes it_
  Interactive play exists only as the admin panel's puzzle player (TERM-037, FR-044), served
  behind the door that guards every other admin page (CON-015, CON-016). No other surface — the
  CLI, the web UI, or any public or hosted page — offers an interactive or playable puzzle. Play
  state is never persisted on the server: no progress, marks, error count, score or solve time is
  written to a database, file or server, no network request is made per mark, and no user account
  exists for playing (CON-017). The one place play state may be kept is the browser's own
  localStorage, per puzzle, so that a puzzle reopened in that browser resumes where it was; it
  never leaves that browser. The admin player ships the puzzle's solution grid to the browser to
  compute the error count and the solved state; this is permitted for the admin panel only, and a
  public or reader-facing player must not send a puzzle's solution to the browser before the
  puzzle is solved.


---

## Worktree notes — implementation, 2026-10-20

Branch `card/254-shrink-the-private-globals-guard`, based on `a60d53a4`.

**Shape of the change.** `tests/test_db_engine_lifecycle.py` 1415 → 919 lines (`+293 / −748`);
21 tests → 11; the AC-5 class 15 tests → 5; nine module-level helpers retired, three added
(`_hand_set_spellings`, `_hand_set_sites_in`, `_hand_set_sites`). `src/nonogram/db/session.py`
`+41 / −0`, all inside `reset_engine`'s docstring.

### G-1: `session.py` is docstring-only, proved by AST identity

Both revisions of `src/nonogram/db/session.py` (`a60d53a4` and this head) were parsed, had **every**
module/class/function docstring stripped, were round-tripped through `ast.unparse` and re-parsed, and
`ast.dump`-compared:

```
docstring-stripped AST identical: True
base dump len: 9154   head dump len: 9154
base sha256: bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c
head sha256: bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c
raw diff: +41 / −0 lines
```

`reset_engine()` and its single call site (`tests/conftest.py:512`, untouched) are unchanged.

### What was kept, and the mutant that proves each one load-bearing

| kept | mutant | result |
|---|---|---|
| `_global_names_assigned_by` + `test_it_resets_exactly_the_globals_the_builder_creates` | **R4** — a fourth global (`_engine_dialect`) added to `_init_engine` | **KILLED**, exactly one test, with the promised message (`reset_engine() resets [...] but _init_engine() builds [... '_engine_dialect' ...]`) |
| `test_conftest_names_the_seam_at_its_call_site` (AST call) | **M1** — the `app_session.reset_engine()` call deleted from conftest, all prose kept | **KILLED** (also reds the real AC-1 test, as CARD-252 recorded) |
| the same test's **receiver** check | **RECV** — the call kept, spelled `reset_engine()` on an unrelated object | **KILLED** — the receiver check is not decoration |
| `_session_aliases_in` (alias derivation, reduced to conftest's own imports) | **ALIAS** — the `from nonogram.db import session as X` branch deleted | **KILLED** with the blind-guard message |
| `test_reset_engine_is_public_and_says_who_calls_it` | **M1b** — every mention of `conftest` removed from the docstring; **M1b2** — `reset_engine` renamed `_reset_engine` | **KILLED** by both |
| the exemption **equality**, now a per-file textual count | **M3** — a `setattr`-spelled hand-set appended to `tests/test_db_isolation.py` (a file no exemption lists); **M3b** — the same as a dotted assignment; **R1** — a *tenth* site under an already-exempt pair | **KILLED** by all three, each naming the file and printing found-vs-expected (AC-1) |
| the `setattr(… "name")` half of `_hand_set_spellings` | **P1** — that regex deleted | **KILLED** — reds both the equality and the new control |
| the `.name =` half of `_hand_set_spellings` | **P2** — that regex deleted | **KILLED only by the new control.** The equality stays **green**: all nine real sites are `setattr`-spelled, so this half has no traffic. It is kept because it is the spelling the convention is about (the card's rejected sketch), and the control is what makes it load-bearing. **Stated, not hidden.** |
| deriving the name set inside the equality test | **D1** — a fourth global added to *and* retired by `session.py`, then hand-set in a non-exempt file → **KILLED**. **D2** — D1 plus the equality's name set hardcoded to today's three → **5 passed, green** | the derivation is load-bearing: hardcoding lets a hand-set fourth global pass silently |

Restores: every mutant applied alone from a `cp -p` backup, restored from that backup, verified with
`diff -q` **and** `shasum -a 256` after each run; never `git checkout --`. Final hashes identical to
the pre-mutation values for all five targets.

**Nothing in the keep list turned out to be decorative.** The one honest qualification is P2 above:
the `.name =` half of the textual scan has zero traffic in this tree, so only the added control kills
it.

### Retirement table (G-3 / AC-3)

| retired | survivor, or why unreplaced |
|---|---|
| `_private_global_sites_in`, `_private_global_sites` | `_hand_set_sites_in` / `_hand_set_sites` — a textual count with no reach claim |
| `_is_setattr_call` | **deliberately unreplaced, because** the whole point of the shrink is that enumerating call shapes is the claim surface that cost three cycles. The text scan matches any line spelling `setattr(` with the name quoted, whatever its receiver and *whatever its argument binding* — which is why it also counts the keyword-bound shape (C3-F-001's `A1`) that the AST guard missed. |
| `_string_target_tail`, `_string_target_module` | **deliberately unreplaced, because** `monkeypatch.setattr("nonogram.db.session.engine", None)` contains `setattr(` and `"…engine"`… but the quoted literal is the *whole path*, so the scan does **not** count it. This is a real loss of reach, and it is now stated in both conventions (the "blind to every spelling that does not put the literal name beside a `setattr(` or a `.<name> =`" bullet) instead of being claimed away. |
| the arity dispatch (`len(node.args) >= 3` / `== 2`) | **deliberately unreplaced** — same reason; a text scan has no arity. |
| `_binding_frontier_reaches_in`, `_binding_frontier_reaches` + `test_the_binding_frontier_is_empty_in_this_tree` | **deliberately unreplaced, because** the frontier existed only to bound the AST dispatch. With no dispatch there is no frontier; what remains is one honest "blind to" list. The keyword-bound shape it was written for is now *counted* by the text scan; the tuple/list-unpacking shape is not, and that is in the "blind to" list. |
| `_dotted`, `_names_the_session_module`, `_SESSION_ALIASES` (the literal floor) | the call-site test now resolves its receiver with `ast.unparse(...) in _session_aliases_in(tree) | _SESSION_MODULE_PATHS`. Certified by **RECV** and **ALIAS**. |
| `test_the_alias_set_covers_every_way_the_tree_names_the_module` | **deliberately unreplaced, because** it was the completeness test for the retired literal floor. There is no floor left: the only consumer derives its aliases from the one file it reads. |
| `test_a_tenth_site_in_an_already_exempt_pair_is_counted` (R1) | arm 4 of `test_the_count_reds_on_a_new_file_a_new_name_and_a_tenth_site`; mutant **R1** re-run as a real-file mutant |
| `test_the_string_target_spelling_is_a_site` (R2) | **deliberately unreplaced** — its mechanism is retired (see `_string_target_*` above); the loss is declared, not controlled |
| `test_a_plain_import_alias_is_a_site` (R3) | the alias derivation it protected survives, certified by **ALIAS**. The *site*-counting half is gone with the AST scan: the text scan does not care how the module was named. |
| `test_the_bare_builtin_setattr_spelling_is_a_site` (X2) | the text scan matches `setattr(` with no receiver requirement at all; arm 1 of the new control |
| `test_a_non_literal_attribute_name_is_a_failure` (X1) | **deliberately unreplaced, because** the deny-on-unanalysable default is retired with the AST guard. A computed attribute name is in the declared "blind to" list. |
| `test_a_computed_string_target_is_a_failure` (X3) | **deliberately unreplaced** — same reason |
| `test_a_setattr_on_another_module_is_not_this_guards_business` | **deliberately unreplaced, because** it controlled the *discrimination* that made a total deny default affordable. The text scan has no discrimination and does not want one: it over-reds by design, which is now the first "does not enforce" bullet. Measured: over-reding costs nothing today — the whole of `tests/` yields exactly the nine exempt sites and no false positives. |
| `test_a_computed_target_with_an_unreadable_name_is_the_declared_bound` | **deliberately unreplaced** — the residual it pinned was a corner of the retired dispatch |
| `test_a_spelling_the_guard_cannot_resolve_is_a_failure` | **deliberately unreplaced** — ditto; there is no "cannot resolve" verdict left to default |
| `_EXEMPT_PRIVATE_GLOBAL_SITES` (renamed) | `_EXEMPT_HAND_SET_SITES`, same six keys and nine counts. Renamed because the old name claimed the entries were *sites that set private globals*, which a text scan cannot know. |

`_test_functions_in` and CARD-252's AC-4 count are **untouched** — out of this card's scope
(C3-F-002 is a CARD-252 residue, not this card's).

### The convention text, and what it says it does not enforce (AC-4)

Written in two places: `src/nonogram/db/session.py`'s `reset_engine()` docstring (the declared
convention) and `TestEngineLifecycle_TheResetIsAPublishedSeam`'s docstring (the same bound, next to
the mechanism). Both say, in these words:

- the convention: *tests do not hand-set `engine` / `SessionLocal` / `_engine_url`; they call
  `reset_engine()`. `test_db_url_driver.py` and `test_db_connect_timeout.py` are the two recorded
  exceptions. A third is a card, not a commit.*
- it is a **convention enforced at review**, and the only mechanism behind it is a textual count
  held to a declared equality, so it reds on a new file, a new name, or a tenth site;
- **it does not enforce**: (1) *reach* — it counts text, does not know what object a counted line
  sets, counts an unrelated class's attribute of the same name and counts occurrences in docstrings,
  comments and string literals, i.e. it over-reds; (2) *coverage* — it is blind to every spelling
  that does not put one of the three literal names beside a `setattr(` or a `.<name> =`: a runtime-computed
  name, a `globals()`/`vars()` write, `importlib` into a local, a `sys.modules` swap,
  `monkeypatch.delattr`, a list-unpacking target, a `monkeypatch.setattr("dotted.path.name", …)`
  whole-path string; (3) it is therefore **not a proof** that no test hand-sets these globals, and
  nothing here claims it is.

The last bullet names the retired predecessor explicitly: an AST deny-default was tried for exactly
that claim and withdrawn, because in a dynamic language a proof claim always has one more axis.

### Why `test_db_engine_lifecycle.py` is not itself an exemption

Every probe line in the kept controls is **built** from a derived name at runtime
(`f'    monkeypatch.setattr(db_session, "{name}", None)\n'`), and the retired prose that quoted the
spellings is gone, so the guard file contributes **zero** counted sites. The equality checks this:
an entry for it would break the dict. Measured over `tests/**/*.py`: 9 sites, 6 pairs, byte-equal to
`_EXEMPT_HAND_SET_SITES`, and no other file in the tree matches at all.

### Test selections run (no full suite, no timings)

`meta/kanban/.full-suite.lock` checked absent before **every** run. Database
`nonogram_pythonproject4_card_254_ffd0825b4ddf_test` (derived by `tests/db_name.py` for this
worktree), passed as both `DATABASE_URL` and `TEST_DATABASE_URL` as literals. `nonogram_poc` was
never named, created, dropped, connected to or truncated; `_refuse_unless_test_database` untouched.

- `tests/test_db_engine_lifecycle.py` — **11 passed, 0 skipped** (was 21 passed)
- `tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam` — **5 passed**
  (baseline for every guard mutant above)
- touched-adjacent: `test_db_engine_lifecycle`, `test_db_url_driver`, `test_db_connect_timeout`,
  `test_db_isolation`, `test_cli` (the structural import guard), `test_book_difficulty_dots`
  (ADR-0036/R3+R4), `test_card_156_db_fixture`, `test_db_e2e_smoke`,
  `test_card_109_database_guard` — **407 passed, 0 skipped, 0 failed** (`-rs` reports no skips)

G-2: no skip path added or removed. The eleven retired tests were none of them `db_required` and
introduced no skip; both `db_required` tests in the module are untouched and still ran.
G-5: no dependency change — the only new import is stdlib `re`.

### System-contract rules checked

- **ADR-0039/R1** — every claim in the new text has a control that can fail, and the three claims
  that have none (`_string_target_*`'s reach, the arity axis, the discrimination) are **deleted**,
  not narrowed-and-kept. The one asymmetry is recorded above (P2).
- **ADR-0039/R2** — the name set is still derived from `session.py`'s AST, and D1/D2 measure that
  the derivation is load-bearing. The guard no longer *defaults to deny*, because it no longer
  claims the reach that made a deny default necessary; that trade is the card.
- **ADR-0039/R3** — the exemption is still an equality over counts (not a floor, not a pair set),
  with its own control, and what it cannot see is stated rather than bounded by a measurement that
  would need maintaining.
- **ADR-0036/R3 / R4** — `src/nonogram/**` scanned after the docstring edit: no codepoint in
  U+25A0..U+25FF, U+2022 or U+2219; `tests/test_book_difficulty_dots.py` green in the selection.
- **ADR-0006/R1 / G-5** — `pyproject.toml` untouched.
- **ADR-0022/R1, ADR-0038/R6–R8, CON-021** — review-lens only; nothing in this card touches grid
  extent, a player surface, Playwright, or interactive play.

### Note for the orchestrator

The card's "What to implement" also asks for *one line in the engineering standards*. There is no
engineering-standards artifact in this repository — `forge:engineering-standards` lives outside the
checkout and `Touches:` does not list it — so the convention was written into `session.py`'s
docstring and the guard class's docstring only. **The standards line is still outstanding and has to
be added wherever that skill lives**; it is the half of the remedy a worktree cannot land.

- **[Orchestrator] the shrink bought reach it did not set out to buy, and that is the result worth
  keeping.** CARD-252's AST deny-default gated cycle 3 on one hole: a **keyword-bound**
  `monkeypatch.setattr(app_session, name="engine", …)` reached a session global and passed silently,
  because the dispatch was arity-based. **The textual scan counts it**, because a grep has no notion
  of argument binding. Three review cycles of proof machinery were beaten, on that axis, by the
  dumber mechanism — which is the sharpest argument this board has produced for preferring a small
  true claim to a large one.
- **[Orchestrator] the one honest asymmetry, left stated rather than tidied away.** Deleting the
  `.name =` half of the scan leaves the tree-wide equality **green** (mutant P2), because all nine
  real exempt sites are `setattr`-spelled; it is load-bearing only through the control written for
  it. The agent kept it — it is the spelling the convention is actually about, CARD-252's rejected
  `app_session.engine = None` sketch — and said so instead of letting the asymmetry sit unnoticed.
  That is the rule from last wave's retro working on the first card that could have broken it.
- **[Orchestrator] one real loss of reach, declared**: the whole-path string target
  `monkeypatch.setattr("nonogram.db.session.engine", None)` is no longer seen, and is named in the
  convention's "blind to" list rather than quietly dropped.
- **[Owner] the half of the remedy a worktree cannot land.** The card asks for one line in the
  engineering standards; **there is no engineering-standards artifact in this repository** — that
  skill lives outside the checkout under `~/MyProjects/forge_1`, and it is not in this card's
  `Touches`. The convention is written in `session.py`'s docstring and the guard class's docstring,
  which is where a maintainer of this code will meet it. The standards line is **outstanding** and is
  the owner's to place, since it edits another repository.
- **[Owner instruction, done] the standards line is placed** —
  `~/MyProjects/forge_1/forge/skills/engineering-standards/SKILL.md`, §6 "Testing policy", as a
  standing bullet before the suite-performance rules. Written **generically**, since that artifact is
  cross-project: *a test does not hand-set another module's private globals — it calls that module's
  published seam*, with recorded exceptions listed where the seam is defined. Two enforcement notes
  carried with it, both earned here: that a count-based backstop **must state what it does not
  enforce**, and that the rule **must not be escalated into a proof** — with CARD-252's three cycles
  (spellings → argument binding → computed targets) as the cited cost, and the shrunk version's
  catch of the shape the AST version missed as the punchline.
- **[Owner] that file is not under version control.** `~/MyProjects/forge_1` has no git repository
  (`git status` exits 128), so this edit has no history and nothing will tell you if it is
  overwritten by a skill update. Worth knowing before more hard-won rules are written there.
- **[Build gate 1 — PASSED]** `de0ea945`, solo: **8585 passed**, 1 skipped, 16:42, EXIT=0. The count
  reconciles exactly: main was 8595 at CARD-225's merge gate, this card retires **10** tests
  (21 → 11 in its module), 8595 − 10 = 8585. A shrink card's gate is worth reading for the
  subtraction as much as for the colour.

### [Review 1/3] Score 8.5 — FAILED on the severity gate (1 open Important)

Report: `meta/review/20261020T062646Z-CARD-254-cycle1.yml` (copied to main).

- **The shrink is certified where it matters.** G-1 re-derived independently to **the same sha256**
  (`bdb10905…`, both dumps 9154 bytes). The retirement table checked **item by item against an AST
  diff**: 11 test functions retired and 1 added, 9 helpers retired and 3 added, 2 globals — **all 22
  accounted for**, nothing retired that is in neither list, and the two survivor claims most able to
  be hollow were spot-checked and are real. The derivation is load-bearing (D2: hardcode the name set
  and the equality goes green while D1 reds). The declared P2 asymmetry reproduces exactly.
- **The headline is TRUE, verified rather than repeated**: the textual scan **counts** the
  keyword-bound `monkeypatch.setattr(app_session, name="engine", …)` shape that was CARD-252 cycle
  3's gating hole. The dumber mechanism closes the axis the proof claim could not.
- **F-001 (important) — AC-4 unmet, and it is the one failure this card could least afford.** The
  regexes exclude newlines *and* parentheses, so a **formatter-wrapped** `setattr(` call — the single
  most likely way a contributor actually writes that line — reaches the globals, is **not** in the
  declared "blind to" list, and is **not** counted. Certified by a surviving real-file mutant
  (**M3c**: the wrapped form appended to a non-exempt file → 5 passed, guard silent) where the
  one-line and dotted forms each killed the equality. No live site is missed today (an AST sweep
  found zero), so it is a disclosure defect with a latent miss. *The claim is wider than the
  mechanism, in the one sentence written to stop exactly that.*
- **Remedy split, deliberately.** The reviewer proposed narrowing both texts. That is right for the
  parens-in-receiver shape and **wrong for the wrapped call**: a backstop whose only job is to red
  when someone adds a hand-set site, and which is blind to the most common spelling of one, has no
  job left. So the fix cycle widens the *mechanism* for (a) — normalise whitespace before matching,
  with an edge control proving it does not start matching across unrelated calls — and *declares* (b).
- **F-002 (minor, out of scope — routed, not fixed)**: ADR-0039/R2's deny-default clause is traded
  away by this card while the ADR still reads Accepted / mandatory. **R2 as written forbids what this
  board actually decided.** An amendment sanctioning "drop the reach claim" as an alternative to the
  deny-default is owed to the architect station; `meta/architecture/` is not in this card's Touches
  and was not touched.
- **OBS-1 — my own record was overstated.** The card claimed a clean U+2022 scan over `src/nonogram/**`;
  `admin/pdf_generator.py` carries U+2022 three times. The rule **holds** (that module is the declared
  `DINGBAT_EXEMPT_MODULES` entry, and it pre-dates this card), so the verdict was right and the
  sentence was wrong. Being corrected on an overstated self-scan, on the card whose subject is
  overstated claims, is the wave's joke at my expense and is fixed in the fix cycle.

## Worktree notes — review cycle 1 fixes, 2026-10-20

Report: `meta/review/20261020T062646Z-CARD-254-cycle1.yml` — score 8.5, one open Important (F-001),
one Minor out of scope (F-002), one card-prose observation (OBS-1). Fixed on
`card/254-shrink-the-private-globals-guard`, on top of `de0ea945`.

### F-001 (Important) — CLOSED. The mechanism was widened; the remaining case was declared.

The scan's `setattr(` pattern was `setattr\([^()\n]*?["']NAME["']`. The character class excluded
**newlines and parentheses**, so two spellings put a literal global name inside a real `setattr(`
call, reached the globals, were **not** in the declared "blind to" list, and were **not** counted:

```python
monkeypatch.setattr(                                               # (a) formatter-wrapped
    app_session, "engine", None
)
setattr(sys.modules.get("nonogram.db.session"), "engine", None)    # (b) parens in the receiver
```

The remedy is split, and the split is the point. This card's thesis is *narrow the claim, don't
widen the mechanism* — which is right for (b) and wrong for (a): a formatter wraps long calls, so
(a) is the single most likely way a contributor actually writes that line, and a backstop blind to
the most common spelling of a hand-set site has no job left.

**(a) — mechanism fixed, no reach claim added.** `_hand_set_spellings`
(`tests/test_db_engine_lifecycle.py:328`) now compiles `setattr\([^()]*?["']NAME["']`: the `\n` is
gone from the character class, so the scan is newline-insensitive and the parenthesis stop is the
only thing that ends it. This is the "collapse newlines before matching" remedy expressed as one
pattern instead of two mechanisms — a `[^()]` class already matches newlines, so normalising the
text first and then excluding `\n` would be the same behaviour with a dead exclusion left in the
regex. Counting unit **unchanged**: per `(file, name)` text match, byte-comparable with
`_EXEMPT_HAND_SET_SITES`.

**Re-measured tree sweep, after the change:** `9 sites, 6 pairs, dict(_hand_set_sites(names)) ==
_EXEMPT_HAND_SET_SITES → True, zero matches in any other file under tests/`. Identical to the
pre-fix numbers, so the dict needed no adjustment. A differential sweep (old pattern vs new,
per `(file, name)`, over every `tests/**/*.py`) returned **no delta at all**: the widening
introduced **zero false positives anywhere in `tests/**`**.

**(b) — declared, in both texts, in the same words.** `reset_engine()`'s docstring
(`src/nonogram/db/session.py:288-305`) and `TestEngineLifecycle_TheResetIsAPublishedSeam`'s
docstring (`tests/test_db_engine_lifecycle.py:729-752`) both now list *a `setattr(` whose **receiver
argument itself contains parentheses*** among the blind cases, and both now state the converse —
that position in the file is not a blind case, because the scan stops at a parenthesis and never at
a newline.

**Controls (one inside the claimed region, one at its edge, one for the declaration).** New test
`TestEngineLifecycle_TheResetIsAPublishedSeam::test_a_wrapped_call_is_counted_and_a_parenthesised_receiver_is_not`
(`tests/test_db_engine_lifecycle.py:955`), four arms:

| arm | claim | mutant that kills it |
|---|---|---|
| 1 — in the region | a wrapped `setattr(` is counted exactly as the one-line form | **NORM-DEL** (`\n` put back into the class) → **KILLED**; and **M3c** as a real-file mutant → **KILLED** (see below) |
| 2a — at the edge | a wrapped `setattr(` carrying a name that is **not** one of the three globals is **not** counted, even with a global name quoted further down the file | **PAREN-DEL** (`[^()]*?` → `.*?` under `re.DOTALL`) → **KILLED** |
| 2b — at the edge | the scan does not run past one call's closing parenthesis into the next call's arguments (two wrapped calls in a row count exactly 1) | **PAREN-DEL** → same |
| 3 — the (b) declaration | a receiver argument containing parentheses is **not** counted, so the blind list is a measured statement rather than prose | broadening the pattern past parens makes it counted → reds |

**M3c, re-run as a real-file mutant** on `tests/test_db_isolation.py` (a file no exemption lists),
shape (a) appended as a new test function:

- at `de0ea945`: `TestEngineLifecycle_TheResetIsAPublishedSeam` → **5 passed, guard silent** (the
  defect, reproduced before fixing);
- after the fix: **`test_no_test_file_outside_the_exemption_sets_those_globals` FAILED**, reporting
  `found: … (('test_db_isolation.py', 'engine'), 1) …` against the expected dict — exactly one extra
  item, correctly attributed.

Restored from a byte-identical `cp` backup and `diff`-verified (`RESTORE OK (byte-identical)`);
never `git checkout --`. Same for every regex mutant on `tests/test_db_engine_lifecycle.py`.

**`session.py` is still docstring-only.** Re-proved after the edit: every module/class/function
docstring stripped, `ast.dump` sha256 —

```
a60d53a4 (base)  : bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c
de0ea945 (card)  : bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c
worktree (fixed) : bdb10905cdf413c531b907fc0311ec049a3619406860e5702d26b60b0653186c
```

G-1 unaffected: `reset_engine()` and its single call site are unchanged.

### F-002 (Minor) — NOT FIXED HERE, recorded as an orchestrator finding

**Out of this card's scope by its own `Touches:` line (`meta/architecture/` — no), and it belongs to
the architect station. `meta/architecture/` was not touched.**

The reviewer's finding, in the reviewer's own wording: ADR-0039/R2 (severity *mandatory*, scope
`tests/**`) states that *"a guard's set is derived from an authority the runtime can enumerate, not
hand-written. Where no such authority exists, the guard defaults to deny: a shape it cannot analyse
is a FAILURE, never a silent pass."* This card's guard splits against that rule: its **name** set
satisfies the first clause and does so measurably (D1 killed / D2 green), but its **shape** set is
two hand-written regexes with no enumerable authority, and a shape it cannot see is a silent pass —
which is precisely the trade this card makes and the board's retro endorsed. The defect is that the
decision lives in a worktree note while ADR-0039 still reads `Status: Accepted`, `Revised: —`,
`severity: mandatory`. *"Left as is, the model asserts a discipline the tree knowingly does not hold
— which is the same 'claim wider than mechanism' failure this card exists to end, one layer up — and
the next guard-shrink card re-litigates it from scratch."*

**What is owed:** an amendment to ADR-0039/R2 adding a sanctioned alternative to the deny-default —
*a guard MAY instead drop the reach claim entirely, provided the narrowed claim is stated where the
mechanism lives and every remaining claim keeps a failing control (R1)* — citing CARD-252 / CARD-254
as the measured case. **R2 as written forbids what the board actually decided.** This needs a
follow-up card on the architect station; nothing in this worktree can land it.

### OBS-1 (card prose) — CORRECTED

The card's ADR-0036/R3/R4 line claimed *"`src/nonogram/**` scanned after the docstring edit: no
codepoint in U+25A0..U+25FF, U+2022 or U+2219"*. **Literally false**:
`src/nonogram/admin/pdf_generator.py` carries U+2022 three times. Re-measured here — that module is
the *only* hit in `src/nonogram/**`, it is the declared `DINGBAT_EXEMPT_MODULES` entry
(`tests/test_book_difficulty_dots.py:787`), and it pre-dates this card, so the rule and the verdict
were right and only the sentence was wrong. The sentence now says what was actually checked: this
card's diff introduces no such codepoint, and the authoritative check is green. An overstated
self-scan is the exact genre this card exists to criticise.

### Test selections run in this cycle (no full suite, no timings)

`meta/kanban/.full-suite.lock` checked absent before **every** run. Database
`nonogram_pythonproject4_card_254_ffd0825b4ddf_test` (derived by `tests/db_name.py` for this
worktree), passed as both `DATABASE_URL` and `TEST_DATABASE_URL` as literals. `nonogram_poc` was
never named, created, dropped, connected to or truncated.

- `tests/test_db_engine_lifecycle.py::TestEngineLifecycle_TheResetIsAPublishedSeam` — **6 passed**
  (the mutant baseline; 5 before the added control)
- `tests/test_db_engine_lifecycle.py` — **12 passed, 0 skipped** (11 before the added control)
- `tests/test_db_engine_lifecycle.py tests/test_db_url_driver.py tests/test_db_connect_timeout.py
  tests/test_db_isolation.py tests/test_suite_profile.py tests/test_book_difficulty_dots.py` —
  **673 passed, 0 failed, 0 skipped**
- the same plus `tests/test_cli.py` (the structural import guard, re-run because `src/` was edited)
  — **769 passed, 0 failed, 0 skipped** (final state, all mutants restored and `diff`-verified)

G-2: no skip path added or removed; the added control is not `db_required`, so
`EXPECTED_DB_REQUIRED_TESTS = 2` is unchanged and both DB tests still ran.
G-5: no dependency change; no new import (`re` was already imported).

### DECLARATIONS

- `DECLARATIONS F-001 — updated.` The mechanism's reach changed (a wrapped `setattr(` now counts),
  so every statement of the old behaviour was re-derived from the code: `_hand_set_spellings`'
  docstring, `_hand_set_sites_in`'s docstring, item 3 of the guard class's "what this class is"
  list, the guard class's "blind to" bullet, `reset_engine()`'s "blind to" bullet in `session.py`,
  and this card's AC-4 convention section. The per-file counting unit and
  `_EXEMPT_HAND_SET_SITES` are **re-derived and confirmed unchanged** (9 sites, 6 pairs, equality
  true). No config field, parameter or timeout acquired a second job.
- `DECLARATIONS F-002 — none (not fixed here; recorded above as an orchestrator finding).`
- `DECLARATIONS OBS-1 — updated.` The card's ADR-0036 line now states what was measured.

- **[Orchestrator] figures above this line are the pre-fix ones.** The implementation record states
  919 lines / 11 tests / AC-5 class 5; after the cycle-1 fix the file is **1062 lines / 12 tests /
  AC-5 class 6** (the new four-arm control). The worktree's copy of this card edited those numbers in
  place; main's keeps the original and names the correction here, so the sequence stays readable —
  which is also what "a committed figure is a claim" means for a card's own record.

- **[Orchestrator] the deviation the fix flagged against itself, and I think it is right.** I asked
  for "newlines collapsed before matching"; the agent removed `\n` from the character class instead,
  because **`[^()]` already matches newlines** — so normalising first *and* keeping the `\n`
  exclusion would leave a dead exclusion in the regex, which is the "mechanism nobody can delete"
  shape this card exists to criticise. The certification cycle is asked to judge it on the merits and
  to look for any input where the two forms differ (`\r\n`, a line continuation, a docstring
  containing `setattr(`). Flagging a deviation from the brief, with the reason, is the behaviour this
  board wants; following the brief into a dead exclusion would not have been.
- **[Orchestrator] the widening added no false positive anywhere.** A differential sweep — old
  pattern vs new, per `(file, name)`, over every `tests/**/*.py` — returned **no delta at all**, and
  the tree sweep is unchanged: 9 sites, 6 pairs, dict-equal, zero matches elsewhere. The dict needed
  no adjustment, quiet or otherwise, which is the part I would have wanted to catch if it had.
