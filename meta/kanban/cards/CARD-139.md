# CARD-139: One import style in the admin package — a duplicate module tree cannot exist

**Status:** ready
**Priority:** P1
**Category:** bug
**Estimate:** 0.25d
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/139-admin-import-consistency
**Worktree:** —
**Source:** owner, 2026-09-23 (live panel: Print setup crashed on a stored plan)
**Idea:** —
**Wave:** 26
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/__init__.py, tests/test_admin_import_consistency.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The admin package mixes import styles: 44 absolute (`from nonogram.admin.x import ...`)
against 13 relative (`from .x import ...`), and `app.py` is itself mixed — 9 relative,
7 absolute. That is invisible until the package is imported under a second name, and
then it is a live 500.

Reproduced on the owner's panel, 2026-09-23. Launched as
`flask --app src.nonogram.admin.app`, Python loads the package twice —
`nonogram.admin.book_plan` **and** `src.nonogram.admin.book_plan` are both in
`sys.modules`, with two distinct `LongestSideBucket` enum classes whose members are
equal to nothing across the divide. `app.py` takes `PLAN_BUCKETS` from its relative
import; `book_manager` (absolute) builds the stored `Plan`, so `Plan.cell` indexes the
*other* module's `BUCKETS`:

    File "src/nonogram/admin/book_plan.py", line 240, in cell
      return self.cells[BUCKETS.index(bucket)][TIERS.index(tier)]
    ValueError: tuple.index(x): x not in tuple

It only fires once a plan is **stored** — a plan-less book renders `DEFAULT_PLAN`, which
comes from app's own copy — so it reads as a data bug and cost the owner a debugging
session. Verified: `import nonogram.admin.app` loads one `book_plan`;
`import src.nonogram.admin.app` loads two, and `A.LongestSideBucket is B.LongestSideBucket`
is `False`.

1. **Convert the 13 relative imports to absolute** (`src/nonogram/admin/__init__.py`, 3;
   `src/nonogram/admin/app.py`, 10), matching the 44 that already are. Absolute wins on
   count and is what every other admin module uses.
2. **Guard it structurally.** Add `tests/test_admin_import_consistency.py` with an `ast`
   walk over `src/nonogram/admin/**/*.py` that fails on any `ImportFrom` with
   `level > 0`. Follow the precedent of the layering guard in `tests/test_cli.py`: walk
   the files on disk, so a new admin module is covered the day it is written.
3. **A test that the tree cannot double.** Import the app under both names in a
   subprocess and assert exactly one `nonogram.admin.book_plan`-suffixed entry in
   `sys.modules` — the property that actually broke, stated directly. Run it in a
   subprocess so it cannot pollute the suite's own module table.

Out of scope: converting the rest of the codebase to one style (only `admin/` is mixed),
anything about how the panel is launched (a launch command is not a repo artifact), and
any behaviour change — this card is import lines and tests, nothing else.

## Acceptance criteria

- New: no module under `src/nonogram/admin/` uses a relative import.
  test: TestAdminImports_NoRelativeImports
- New: importing the app under a `src.`-prefixed name does not create a second copy of
  `book_plan`.
  test: TestAdminImports_PackageTreeCannotDouble
- Regression: Print setup renders a book whose plan is stored, with no `ValueError` from
  `Plan.cell`.
  test: TestAdminImports_StoredPlanRendersUnderEitherImportName

## Guardrails

- G-1: Behaviour is unchanged — this is an import-style sweep. No route, template or
  aggregate edits.
- G-2: The layering guard in `tests/test_cli.py` stays green: `export/` must still never
  import `admin/`, and absolute imports must not become a way around it.
- G-3: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019).

## Architecture context

- **ADR:** ADR-0031 (tiers — the enum that doubled), CTX-001 (one bounded context)
- **Components:** COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Owner, 2026-09-23. Found while diagnosing a live `ValueError` on Print setup
  step 2. The immediate unblock was to relaunch as `--app nonogram.admin.app` (no `src.`
  prefix); this card removes the trap rather than remembering the workaround.
- [Scheduling] Runs **alone** in wave 26, after CARD-128/131/132 merge: it rewrites the
  import block at the top of `app.py`, which every other admin card also edits.
