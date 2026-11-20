# CARD-499: Two test instruments' blind spots: the globals guard ignores augmented and annotated assignment; the kill matrix cannot measure a test that patches its own module

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/499-instrument-blind-spots
**Worktree:** ../PythonProject4-card-499
**Source:** roadmap wave 5 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-113 WSJF 3.08, IDEA-196 WSJF 3.08; bundled as test-instrument fixes, each 0.125 d.
**Idea:** IDEA-113, IDEA-196
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** —
**Touches:** tests/test_db_engine_lifecycle.py, tests/kill_matrix.py, tests/test_kill_matrix.py, tests/README.md, src/nonogram/db/session.py (one comment, widened 2026-11-20 by the orchestrator)
**UI surface:** —
**Review score:** —
**Started:** 2026-11-20T10:24Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

1. **IDEA-113 (CARD-258 deferral).** tests/test_db_engine_lifecycle.py `_global_names_assigned_by` collects only `ast.Assign` targets, so a global the builder sets with `+=` (`ast.AugAssign`) or `x: T = …` (`ast.AnnAssign`) is never collected, and the guard passes by silence. Its docstring claims "a shape this function cannot analyse biases it to red rather than to a pass", which is false for those two shapes.
2. **IDEA-196.** tests/kill_matrix.py's child plugin (`pytest_configure` in the generated plugin source) registers the rewritten target module in `sys.modules` but never sets it as an attribute of its parent package. pytest's `monkeypatch.setattr("pkg.mod.name", …)` resolves a dotted target by attribute walk from the package, so any test that patches its own module by a dotted string cannot be measured (found by CARD-264). The backlog says a one-line fix.

## What to implement

1. The collector handles `AugAssign` and `AnnAssign` (value present) targets, or raises on any assignment shape it does not analyse, so the docstring's "biases to red" is true; the docstring says exactly what is collected.
2. The plugin sets the rewritten module on its parent package (and restores nothing it did not set); a test that dotted-`setattr`s its own module is measured.

## Acceptance criteria

* **AC-1**: a planted `global x; x += 1` (and `x: int = 1`) in a copy of session.py's builder reds the guard; control: the old collector stays green on it.
* **AC-2**: the kill matrix measures a fixture test that dotted-`setattr`s its own module (extend an existing kill-matrix test case if one fits); control: without the fix it reports the instrument failure it does today.
* **AC-3**: the guard and the kill matrix's own tests green; net test count at most +1.

## Guardrails

* **G-1**: never edit src/nonogram/db/session.py for the plant; plant in a copy or a parsed string.
* **G-2**: the kill matrix's existing measured figures elsewhere are unchanged (run its own test file).

## Worktree notes

### Implementation (2026-11-20)

**Premises re-verified before any change.**
- IDEA-113: with the shipped `_global_names_assigned_by`, a copy of `session.py` with `global _planted` + `_planted += 1` (and separately `_planted: int = 1`) prepended to `_init_engine` still derived `['SessionLocal', '_engine_url', 'engine']` -- the plant was not collected, so the guard's equality stayed green.
- IDEA-196: `test_card_499_a_test_that_patches_its_own_module_by_a_dotted_path_is_measured`, run against the unfixed plugin: `LeakedPatch: SHIPPED reached no assertion node ... 0 PASS, 0 FAIL, 1 NOT-REACHED ... pytest exit 1`; the child's own output: `AttributeError: module 'km_self_patch_pkg' has no attribute 'km_self_patch_target'` (CARD-264's shape).

**What changed.**
- `tests/test_db_engine_lifecycle.py`: `_global_names_assigned_by(function_name, source=None)` now collects every `ast.Name` in `Store` context inside the function (so `=`, tuple/starred, `+=`, `x: T = v`, `for`/`with` targets, walrus), intersected with the declared globals, and raises when a declared global is bound by an import, nested def/class, except-as or match capture (new helper `_string_bound_names`). The docstring states exactly that, plus what it cannot see (`globals()[...]`, `setattr` on the module). New helper `_session_source_with_builder_prelude` plants into an `ast.unparse`d copy; `session.py` itself is never edited for the plant (G-1).
- **Finding the fix surfaced:** the fixed collector sees `reset_engine`'s `_reset_count += 1` (CARD-258's declared bound 9), so `test_it_resets_exactly_the_globals_the_builder_creates`'s `reset == built` equality went red on the shipped code -- it had held only by being blind to that name. The equality is now `reset == built | _RESET_ONLY_GLOBALS`, with `_RESET_ONLY_GLOBALS = frozenset({"_reset_count"})` a declaration held inside the equality (a second reset-only global reds). The same test carries the CARD-499 arms: both plants give gap `{'_planted'}`, and a `global engine; import engine` plant raises.
- `src/nonogram/db/session.py`: comment only, above `_reset_count`: it said the guard's sweep is silent about this name, which this card made false; now it says the test derives it since CARD-499 and declares it. No code change. (Outside the card's Touches list -- flagged for review.)
- `tests/kill_matrix.py`: `_PLUGIN_SOURCE`'s `pytest_configure`, after the exec, does `setattr(importlib.import_module(package), stem, module)` when the target's dotted name has a package. It sets that one attribute and restores nothing.
- `tests/test_kill_matrix.py`: new `SELF_PATCH_TARGET` fixture source and `test_card_499_a_test_that_patches_its_own_module_by_a_dotted_path_is_measured` (package target, a test that `monkeypatch.setattr(f"{__name__}.VALUE", ...)`s its own module; SHIPPED must be exit 0, 1 PASS of 1, 1 collected). No existing case fit: every fixture target is a top-level module, and making one a package would move other figures. The CARD-257 anchor's line constants moved with `test_db_engine_lifecycle.py` (+80 lines): `PREAMBLE, NAMES, HEADS, POINTER = 1140, 1216, 1223, 1229` (re-derived by mapping the nine asserts of `test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters` HEAD-vs-branch; the old four are no assert lineno now), and `NAMES_BLIND_OCCURRENCES = (1012, 1140, 1302, 1348, 1475)` (re-derived by locating the message; counts 5 and 4 unchanged). `tests/README.md`'s copy of the four addresses updated. `_init_engine_globals` in `test_kill_matrix.py` still reads `ast.Assign` only; it is used on the builder alone, where it gives the same three names.

**Controls (each restored; `cmp` against a `cp -p` backup confirmed).**
- Old (Assign-only) collector: the test reds at its first equality: `reset_engine() resets ['SessionLocal', '_engine_url', 'engine'] but _init_engine() builds ['SessionLocal', '_engine_url', 'engine'] and the reset alone may add only ['_reset_count']`.
- Old collector + empty `_RESET_ONLY_GLOBALS` (to reach the plant arm): `a global the builder sets as '_planted += 1' is invisible to the derivation (gap [])`.
- Collector that skips `AnnAssign` targets only: `a global the builder sets as '_planted: int = 1' is invisible to the derivation (gap [])`.
- Raise disabled: `Failed: DID NOT RAISE AssertionError`.
- Plugin without the `setattr`: the `LeakedPatch` / `AttributeError` reading quoted under the premise above (measured before the fix was applied).

**Gate (worktree, `-o addopts= -rfs`).** Unarmed: `tests/test_kill_matrix.py tests/test_db_engine_lifecycle.py tests/test_admin_binding.py tests/test_db_url_driver.py tests/test_db_connect_timeout.py` -- 227 passed, 11 skipped (all `DATABASE_URL is not set`), 0 failed; the kill matrix's own file green, so its other figures (incl. the 165/165 lock anchor and CARD-257's four-arm grid) are unchanged (G-2). Armed with this worktree's own `nonogram_pythonproject4_card_499_1d20ff4f6cb0_test` on localhost: the four DB-touching files -- 154 passed, 0 skipped, 0 failed. One pre-existing `MovedIn20Warning` (models.py `declarative_base`), unrelated.

**Net test count:** 10710 -> 10711 (+1), `--collect-only -q -o addopts= tests/`.

### Fix round 1 (review cycle 1, 2026-11-20)

- **F-001** (`_RESET_ONLY_GLOBALS` not held to being reset-only). Inside `test_it_resets_exactly_the_globals_the_builder_creates`, no new test: (1) `assert not (built & _RESET_ONLY_GLOBALS)`; (2) a reset-side plant (`global _planted; _planted = 1` in a copy's `reset_engine`) must leave `reset - (built | _RESET_ONLY_GLOBALS) == {"_planted"}`. The plant helper is now `_session_source_with_prelude(prelude, function_name="_init_engine")` (was `_session_source_with_builder_prelude`).
- **F-002** (docstring). `_global_names_assigned_by` now says `x: T = v` on a declared global is a `SyntaxError` when compiled, so that arm guards a parsed string only. On nested scopes the requested wording ("over-collection can only red") **measured false**: on the round-0 collector, `global X` + `[X for X in range(2)]` in `reset_engine` was collected as resetting `X` and would have matched a builder `X = 1` -- a pass by silence. So the collector now **raises** on a declared global's name stored or taken as a parameter inside any nested scope (new `_nested_scope_bound_names`, over `_NESTED_SCOPES`: def, async def, lambda, class, the four comprehensions), and the docstring says so. Arm: a `global engine; [engine for engine in ()]` plant in `reset_engine` raises. The real `_init_engine`/`reset_engine` derive the same sets as before.
- **Controls, round 1** (each on a `cp -p` copy, restored, `cmp` identical):
  - M5, builder also declares and binds `_reset_count` (via the plant helper on `built`; session.py untouched): `AssertionError: _init_engine() now builds ['_reset_count'], which _RESET_ONLY_GLOBALS exempts as set by the reset alone; the allowance would absorb a builder global (CARD-499 F-001)`.
  - Exemption widened to `{"_reset_count", "_planted"}` alone: reds at the first equality (`... the reset alone may add only ['_planted', '_reset_count']`). Widened AND the equality loosened to `<=`: the plant arm reds -- `a second reset-only global is absorbed (extra []); _RESET_ONLY_GLOBALS must exempt _reset_count alone (CARD-499 F-001)`.
  - `_nested_scope_bound_names` dropped from the raise: `Failed: DID NOT RAISE AssertionError` (the comprehension plant).
- **Anchors re-derived** (file 1998 -> 2052 lines): mapping the nine asserts of `test_every_text_that_names_card_252_points_here_and_agrees_on_the_parameters` HEAD-vs-tree gives `PREAMBLE, NAMES, HEADS, POINTER = 1194, 1270, 1277, 1283`; the NAMES-BLIND message sits at `1047, 1194, 1356, 1402, 1529`; each new line's text equals the old anchor line's text, and the previous four are no assert lineno now. `tests/README.md` updated to match.
- **Gate, round 1** (`-o addopts= -rfs`): unarmed, `tests/test_kill_matrix.py tests/test_db_engine_lifecycle.py tests/test_admin_binding.py tests/test_db_url_driver.py tests/test_db_connect_timeout.py` -- 227 passed, 11 skipped (all `DATABASE_URL is not set`), 0 failed. Armed (own `nonogram_pythonproject4_card_499_1d20ff4f6cb0_test`, localhost), the four DB-touching files -- 154 passed, 0 skipped, 0 failed.
- **Net test count:** 10711 collected (10710 before the card; +1 unchanged).
