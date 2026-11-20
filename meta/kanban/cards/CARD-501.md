# CARD-501: A typed matrix cell is judged against the count and split the owner submitted

**Status:** in_progress
**Priority:** P3
**Category:** tech-debt
**Estimate:** 1c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/501-judge-against-submitted-split
**Worktree:** ../PythonProject4-card-501
**Source:** owner 2026-11-20 ("yes, judge typed cells against the submitted split"), on CARD-500 review F-002 = CARD-489 review F-003.
**Idea:** —
**Wave:** 84
**Created wave:** 84
**Deferred waves:** 0
**Depends on:** CARD-489, CARD-500
**Touches:** src/nonogram/admin/book_manager.py, tests/test_book_plan_storage.py
**UI surface:** admin Print setup (step 2), which matrix cells are marked hand-edited after a save or a refusal
**Review score:** 9.5 (cycle 1/3 - CERTIFIED)
**Started:** 2026-11-20T13:01Z
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

`book_manager.revise_plan` decides whether a typed cell is hand-edited by comparing it with a reference prefill. CARD-489 made that reference use the **submitted count** but kept the **shown split**. So when the owner changes count and split together and types the new split's values, those cells are marked "edited" — contradicting the matrix caption ("until you change it back to the value the split gives"). Measured 2026-11-20 on CARD-500: 150 at 40/40/20 -> 120 at 30/45/25 with one cell typed off marked six cells.

## What to implement

The reference is the prefill at the submitted count **and** the submitted split. Unchanged: a value equal to the shown value is "left alone" and keeps its mark; un-edited cells re-derive from the new split.

## Acceptance criteria

* **AC-1**: count and split changed together, every cell typed to the new prefill but one typed off it (and off the shown value): only that one is edited; control: the shown-split reference reds it.
* **AC-2**: every existing revise_plan and Print setup test still holds (CARD-489's count-only case, CARD-120's rules, CARD-500's save-based marks).
* **AC-3**: net test count 0.

## Guardrails

* **G-1**: no schema change; a stored plan's existing marks are not rewritten (the rule applies to new submissions only).

## Worktree notes
Implemented by the orchestrator.

* **Change.** `revise_plan`: `reference = prefill(typed.count, split)` (was `shown.split`); the comment and the docstring's second bullet say the typed cell is judged against the prefill at the submitted count and split. The left-alone rule and `with_split`'s re-derivation unchanged.
* **AC-1.** `TestRevisePlan::test_a_count_change_judges_typed_cells_against_the_new_prefill` gains a second case (no new test): DEFAULT_PLAN, submitted 120 at 30/45/25, every cell typed to that prefill except 16-20 x medium (prefill + 5, asserted to differ from both the new prefill and the shown value — my first offset, +3, equalled the shown value and was rightly treated as left alone). Asserts the only edit is that cell and the matrix is as typed. Control (reference back on the shown split): reds, extra cells marked.
* **AC-2.** The plan and Print setup files (test_book_plan_storage, _setup_print_mobile, _trim_persistence, _player_domain, _divider_pages_option, test_print_specs, _pdf_ink_mode, _workflow_steps, test_admin_import_consistency, _proof_pages, test_book_manager, _ready_gate, test_book_plan and property/test_book_plan): 977 passed, 0 skipped, unarmed, -rfs. CARD-500's save-based oracle follows the new rule by construction (it reads what a save stores).
* **AC-3.** 10711 collected on main and on the branch, net 0.

[Review 1/3] Score: 9.5, nothing gating, certified. An independent oracle (its own Fraction-based prefill, matching book_plan.prefill on 3000 pairs) agreed with revise_plan on 60,000 seeded cases, 0 disagreements (14,895 count-only, 14,892 split-only, 18,226 both, 11,987 unchanged), and reds at once with the reference back on the shown split; the caption holds for split-only, count-only and both; CARD-120's survival rule and CARD-489's count-only case hold (mutants M2, M4 red); G-1 holds (one product caller, the Print setup POST). F-001 (low) a split-only change was unpinned (mutant M3, the submitted split only when the count also changed, survived 329 tests): fixed inline by the orchestrator — the same test also submits 150 at 30/45/25 with every cell typed to that prefill but one; M3 now reds it; 73 passed. F-002 (info) under the AC-1 control only the edited-set assertion reds, the cells assertion stays green (as it should). F-003 (info, pre-existing, CARD-120 F-001's left-alone rule) an edit whose value a later split's prefill happens to equal stays edited until retyped twice; the owner's call if it ever surprises.

**Merge gate (orchestrator).** `make test-gate BASE=main` answered SELECTION: 9011 passed / 30 skipped (the expected unarmed count: 29 DATABASE_URL unset + 1 setrlimit) / 1 xfailed / 0 failed, plus 11 marked passed in the lifted files.
