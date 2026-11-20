# CARD-504: Nine stale texts: docstrings, comments, a README version, a script message, a test helper's name, a narrow regex

**Status:** ready
**Priority:** P3
**Category:** tech-debt
**Estimate:** 2c
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/504-stale-texts
**Worktree:** —
**Source:** roadmap wave 6 (cut 2026-11-20 on the owner's "please start the next wave"; premises re-read against main the same day). IDEA-026, 027, 030, 037, 039, 102, 134, 145, 197 (WSJF 2.31 each, each about 0.125 d: bundled because each alone is below `sizing.min_estimate`).
**Idea:** IDEA-026, IDEA-027, IDEA-030, IDEA-037, IDEA-039, IDEA-102, IDEA-134, IDEA-145, IDEA-197
**Wave:** 85
**Created wave:** 85
**Deferred waves:** 0
**Depends on:** —
**Touches:** src/nonogram/export/book_pdf_generator.py, src/nonogram/admin/book_proof.py, src/nonogram/admin/app.py, src/nonogram/web/__init__.py, scripts/README.md, scripts/*.sh, scripts/measure_difficulty_cutoff.py, tests/test_book_pdf_band.py, tests/test_difficulty_tiers.py, tests/test_start_admin_local.py, tests/test_admin_tier_surfaces.py
**UI surface:** —
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## Why this card exists

Each re-read against main on 2026-11-20 unless marked:

1. **IDEA-026 (CARD-135 F-008).** `export_book`'s docstring (or the comment beside it) claims every route goes through it.
2. **IDEA-027 (CARD-134).** `answer_page_number()` in tests/test_book_pdf_band.py encodes one answer page per puzzle in its name (7 occurrences).
3. **IDEA-030 (CARD-155 F-005).** test_difficulty_tiers.py's docstring regression regex catches only uppercase `GUESS` and "or Guess", not a lowercase "guess" used as a tier.
4. **IDEA-037 (CARD-152 F-006).** The "not reachable" message names only two causes (server down, database missing), not a wrong host, port or credentials; same wording in several scripts.
5. **IDEA-039 (CARD-152 F-007).** scripts/README.md says "Python 3.11+" (pyproject requires 3.14); a stale docstring in tests/test_start_admin_local.py (find it by the claim, not the old line number).
6. **IDEA-102 (CARD-170 F-007).** tests/test_book_pdf_band.py's class docstring states the "no other ink within about a line's height sideways" rule loosely.
7. **IDEA-134 (CARD-179 F-003).** book_proof.py `_wrapped`'s docstring does not say the token after an over-wide × is taken as M.
8. **IDEA-145 (CARD-181).** `requested_tier_label`'s docstring says `None` for any non-tier, but "guess" reads Hard; no test pins `Tier.label`; migration 014's "no puzzle row touched" claim is untested.
9. **IDEA-197 (CARD-264).** src/nonogram/web/__init__.py's docstring says the structural guard knows "exactly two adapter names"; `_ADAPTERS` in tests/test_cli.py has more.

## What to implement

Re-verify each first; drop any already closed with one line. Each text states only what the code and its tests show. IDEA-030: widen the regex so a lowercase tier "guess" in a docstring reds, without matching the legitimate uses (find them first). IDEA-145: fix the docstring; pin `Tier.label` inside an existing test; for migration 014 either an assertion in an existing migration test or soften the claim. IDEA-197: state no adapter count (CLAUDE.md's precedent) and point at `_ADAPTERS`.

## Acceptance criteria

* **AC-1**: each item fixed or dropped with its evidence.
* **AC-2**: the widened regex reds on a planted lowercase "guess" tier docstring and stays green on main's texts.
* **AC-3**: the `Tier.label` pin reds when one label is changed (control).
* **AC-4**: net test count 0 (the rename and pins live in existing tests); report it.

## Guardrails

* **G-1**: no behaviour change; script messages change wording only, and any test pinning the old wording moves with it.
* **G-2**: the CARD-257/kill-matrix line anchors and any line pins in tests (e.g. test_book_export_interior_cover's) are re-derived if a docstring edit moves them.

## Worktree notes
