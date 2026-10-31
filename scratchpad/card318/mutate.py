#!/usr/bin/env python3
"""CARD-318 mutant harness.

Protocol, per the card's pipeline rules:
  * assert the target file's SHA-256 BEFORE each mutant and AFTER each restore
  * restore from the in-memory original, never `git checkout --` (which
    restores to HEAD and would revert real work, not the mutant)
  * sweep *.pyc / __pycache__ before and after each mutant
  * run the named node ids with `-o addopts=''` and record the PASS/FAIL cell
    for EACH node separately -- a file-level verdict hides a never-reached arm
"""
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path("/Users/omelnikova/PycharmProjects/PythonProject4-card-318")
PY = "/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python"

T_UNIT = "tests/test_solver_strategies.py"
T_PROP = "tests/property/test_solve_strategies.py"

# (id, kind, file, old, new, [node ids expected to be exercised])
MUTANTS = [
    ("M1", "deletion",
     "src/nonogram/orchestrator.py",
     "        self.strategies = tuple(rungs) + (\n            (GUESS_STRATEGY,) if branch_nodes > 0 else ()\n        )\n",
     "        self.strategies = tuple(rungs)\n\n\n",
     [f"{T_UNIT}::TestSolveStrategies_GuessPresentWhenSearchBranched::test_the_aggregate_records_the_guess_for_such_a_solve",
      f"{T_UNIT}::TestSolveStrategies_GuessAbsentForLineSolvable::test_the_aggregate_records_no_guess_for_such_a_solve",
      f"{T_PROP}::TestPropertySolveStrategies_GuessIffSearchBranched::test_guess_is_present_exactly_when_the_search_branched"]),

    ("M2", "deletion",
     "src/nonogram/admin/regrade.py",
     "    strategies = tuple(rungs)\n    if branch_nodes > 0:\n        return (*strategies, STRATEGY_GUESS)\n    return strategies\n",
     "    strategies = tuple(rungs)\n\n\n    return strategies\n",
     [f"{T_PROP}::TestPropertySolveStrategies_GuessIffSearchBranched::test_guess_is_present_exactly_when_the_search_branched",
      f"{T_PROP}::TestPropertySolveStrategies_GuessIffSearchBranched::test_the_list_never_names_guess_without_the_count_to_back_it"]),

    ("M3", "deletion",
     "src/nonogram/export/json_export.py",
     '        "strategies": list(payload.strategies),\n',
     "\n",
     [f"{T_UNIT}::TestExport_JSONCarriesStrategiesInOrder::test_the_written_array_is_the_list_in_order",
      f"{T_UNIT}::TestExport_JSONCarriesStrategiesInOrder::test_the_decoded_payload_is_the_list_in_order",
      f"{T_UNIT}::TestExport_JSONCarriesStrategiesInOrder::test_a_reordered_list_is_a_different_payload",
      f"{T_PROP}::TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd::test_the_aggregate_the_stored_row_and_the_export_hold_one_list"]),

    # The EDGE mutant for AC-140's order claim: the payload still carries every
    # name, only sorted. A test that compared against a list it had itself
    # derived from the payload would not notice.
    ("M4", "replacement (order only)",
     "src/nonogram/export/json_export.py",
     '        "strategies": list(payload.strategies),\n',
     '        "strategies": sorted(payload.strategies),\n',
     [f"{T_UNIT}::TestExport_JSONCarriesStrategiesInOrder::test_the_written_array_is_the_list_in_order",
      f"{T_UNIT}::TestExport_JSONCarriesStrategiesInOrder::test_a_reordered_list_is_a_different_payload"]),

    ("M5", "deletion",
     "src/nonogram/admin/puzzle_review.py",
     "                    recorded = puzzle.get(\"strategies_used\") or ()\n                    if filter_opts.strategy not in recorded:\n                        continue\n",
     "                    recorded = puzzle.get(\"strategies_used\") or ()\n\n\n",
     [f"{T_UNIT}::TestPuzzleReview_FiltersListByStrategy::test_exactly_the_three_guessing_puzzles_are_listed"]),

    ("M6", "deletion",
     "src/nonogram/admin/batch_generator.py",
     "                        strategies_used=list(puzzle.strategies),\n",
     "                        strategies_used=[],\n",
     [f"{T_UNIT}::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_a_random_batch_stores_a_real_list_for_every_row"]),

    # AC-143's order: the template renders the list reversed. Every name is
    # still present, so the pre-existing presence test stays green -- which is
    # the gap this card's AC-143 test exists to close.
    ("M7", "replacement (order only)",
     "src/nonogram/admin/templates/generated_puzzles.html",
     "{% for name in used %}",
     "{% for name in used|reverse %}",
     [f"{T_UNIT}::TestPuzzleReview_DetailShowsStrategiesInOrder::test_the_rendered_page_shows_them_in_the_stored_order"]),

    # EC-018's dilated-clock arm and AC-136: make the recorded ladder depend on
    # the clock, which is precisely what NFR-007/CON-014 forbid.
    ("M8", "replacement (clock becomes an input)",
     "src/nonogram/solver/search.py",
     "            rungs=tuple(rung for rung in RUNG_ORDER if rung_cells[rung]),",
     "            rungs=(tuple(rung for rung in RUNG_ORDER if rung_cells[rung]) if __import__('nonogram.solver.propagate', fromlist=['time']).time.monotonic() % 1000 < 100 else ()),",
     [f"{T_UNIT}::TestSolveStrategies_SameCluesSameListUnderDilatedClock::test_the_two_lists_are_identical_element_for_element",
      f"{T_PROP}::TestPropertySolveStrategies_PureFunctionOfCluesAndPreservedEndToEnd::test_a_fifty_times_slower_clock_changes_no_list"]),

    # AC-139's IMAGE half, which nothing covered before this card.
    ("M9", "replacement",
     "src/nonogram/admin/app.py",
     "                            strategies_used=list(puzzle.strategies),\n",
     "                            strategies_used=[],\n",
     [f"{T_UNIT}::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_an_image_batch_stores_a_real_list_for_every_row",
      f"{T_UNIT}::TestBatchGenerator_PersistsRealStrategiesUsedForRandomAndImage::test_a_random_batch_stores_a_real_list_for_every_row"]),
]


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sweep() -> None:
    for pyc in ROOT.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def run(nodes: list[str]) -> dict[str, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("DATABASE_URL", None)
    proc = subprocess.run(
        [PY, "-m", "pytest", *nodes, "-o", "addopts=", "-p", "no:randomly", "--tb=no", "-q", "-rA"],
        cwd=ROOT, capture_output=True, text=True, env=env,
    )
    cells = {}
    for line in proc.stdout.splitlines():
        for tag in ("PASSED", "FAILED", "ERROR", "SKIPPED"):
            if line.startswith(tag + " "):
                cells[line[len(tag) + 1:].strip()] = tag
    for node in nodes:
        cells.setdefault(node, "NOT-REPORTED")
    return cells


def main() -> int:
    rows = []
    for mid, kind, relpath, old, new, nodes in MUTANTS:
        target = ROOT / relpath
        original = target.read_text()
        before = sha(target)
        if old not in original:
            rows.append((mid, kind, relpath, "ANCHOR-MISS", {}))
            continue
        assert original.count(old) == 1, f"{mid}: anchor is not unique"

        sweep()
        target.write_text(original.replace(old, new, 1))
        mutated_sha = sha(target)
        assert mutated_sha != before, f"{mid}: mutant did not change the file"
        try:
            cells = run(nodes)
        finally:
            target.write_text(original)
            sweep()
        after = sha(target)
        assert after == before, f"{mid}: RESTORE FAILED {before} -> {after}"
        rows.append((mid, kind, relpath, "ok", cells))

    print("\n=== MUTANT TABLE (per node id) ===")
    for mid, kind, relpath, status, cells in rows:
        print(f"\n{mid}  [{kind}]  {relpath}   restore={status}")
        for node, verdict in cells.items():
            short = node.split("::", 1)[-1] if "::" in node else node
            where = "prop" if "property" in node else "unit"
            print(f"    {verdict:13s} ({where}) {short}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
