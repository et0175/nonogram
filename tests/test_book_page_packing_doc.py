"""docs/BOOK_PAGE_PACKING.md is held to the code (CARD-232 AC-8, AC-9).

AC-8: the doc's constants block and its three tables are GENERATED here, from
the real constants and the real planner, every run, and compared with the
committed text byte for byte. Nothing in the doc's generated blocks is typed
by hand: re-record them after an intended change with

    PYTHONPATH=src python -m tests.test_book_page_packing_doc

which rewrites only the text between each ``<!-- BEGIN name -->`` /
``<!-- END name -->`` pair.

The planner calls are the export's own, in the export's order
(``BookPDFGenerator.interior_stream``): puzzle pages through
``BookPDFGenerator.puzzle_pages`` with the book's ``cell_sizes``; answer pages
through ``plan_small_answer_pages``, then ``_degrade_infeasible_packed_pages``
on ``answer_section_spec``, then ``compute_packed_solved_layout`` on the same
spec for the cell. The puzzles are synthetic: an all-filled grid of the size,
with every row clue and every column clue ``depth`` runs of 1 (capped at what
the line can hold), because the planner reads clue depth and extent and
nothing else of a puzzle.

AC-9: FR-042's text and the passages of the named docs that describe the
answer key carry none of the retired rule's marks -- six to a page, the
20-cell longest-side switch, grid-only answers, a 5 mm answer cap.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

from nonogram.admin import book_answer_key, book_page_spec, book_pdf_generator
from nonogram.admin.book_answer_key import Answer, PackedAnswerPage, plan_small_answer_pages
from nonogram.admin.book_pdf_generator import (
    BookPDFGenerator,
    _answer_extent,
    _degrade_infeasible_packed_pages,
    _pairable_tier,
    answer_section_spec,
)
from nonogram.export import layout
from nonogram.export.layout import compute_packed_solved_layout

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs" / "BOOK_PAGE_PACKING.md"

#: The trims the doc tabulates: the panel's "Common sizes" box, as the books
#: table stores a trim (cm, two decimals). Margins are the Book 1 profile's.
TRIMS = (
    ("8.5x11 in (default)", "21.59", "27.94"),
    ("8x10 in", "20.32", "25.40"),
    ("6x9 in", "15.24", "22.86"),
    ("A4", "21.00", "29.70"),
)

#: The sizes the doc tabulates, width x height in cells.
SIZES = (
    (10, 10), (12, 12), (15, 10), (15, 15), (15, 20), (20, 10),
    (20, 15), (20, 20), (25, 25), (30, 10), (10, 30), (30, 30),
)

#: The "typical" clue depth the first solutions table is read at.
TYPICAL_DEPTH = 3

#: Every constant the doc's constants block states, and where it lives.
CONSTANTS = (
    ("TWO_UP_MIN_CELL_MM", layout, "export/layout.py"),
    ("MIN_CELL_MM", layout, "export/layout.py"),
    ("SOLVED_TILE_CAPACITIES", layout, "export/layout.py"),
    ("SOLVED_TILE_GAP_MM", layout, "export/layout.py"),
    ("SOLVED_TILE_MAX_CELL_MM", layout, "export/layout.py"),
    ("INTERIOR_FOOTER_MM", layout, "export/layout.py"),
    ("RUNNING_HEAD_MM", book_pdf_generator, "admin/book_pdf_generator.py"),
    ("PACKED_MAX_WIDTH", book_answer_key, "admin/book_answer_key.py"),
    ("PACKED_MAX_HEIGHT", book_answer_key, "admin/book_answer_key.py"),
)


def _format(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _constants_block() -> str:
    profile = book_page_spec.BOOK1_PROFILE
    rows = [(name, _format(getattr(module, name)), where) for name, module, where in CONSTANTS]
    rows += [
        ("BOOK1_PROFILE.band_mm", _format(profile.band_mm), "admin/book_page_spec.py"),
        ("BOOK1_PROFILE.cell_cap_mm", _format(profile.cell_cap_mm), "admin/book_page_spec.py"),
    ]
    lines = ["| Constant | Value | Defined in |", "|---|---|---|"]
    lines += [f"| `{name}` | {value} | `src/nonogram/{where}` |" for name, value, where in rows]
    return "\n".join(lines)


def _generator(width_cm: str, height_cm: str) -> BookPDFGenerator:
    return BookPDFGenerator(
        SimpleNamespace(
            trim_width_cm=width_cm,
            trim_height_cm=height_cm,
            gutter_margin_cm=None,
            outside_margin_cm=None,
            interior_ink_mode=None,
            interior_divider_pages=True,
        )
    )


def _puzzle(width: int, height: int, depth: int, number: int) -> dict:
    rows = [[1] * min(depth, (width + 1) // 2) for _ in range(height)]
    columns = [[1] * min(depth, (height + 1) // 2) for _ in range(width)]
    return {
        "grid": [[True] * width for _ in range(height)],
        "clues_rows": rows,
        "clues_cols": columns,
        "width": width,
        "height": height,
        "puzzle_name": f"P{number}",
        "difficulty_tier": "easy",
        "puzzle_id": number,
        "id": number,
    }


def _deepest(width: int, height: int) -> int:
    return (max(width, height) + 1) // 2


def _puzzle_cell(gen: BookPDFGenerator, width: int, height: int) -> str:
    """Two same-level neighbours of one size: up to which clue depth they share a page."""
    pairs = []
    for depth in range(1, _deepest(width, height) + 1):
        payloads = [gen._payload(_puzzle(width, height, depth, n)) for n in (1, 2)]
        pages = gen.puzzle_pages(payloads, cell_sizes=gen.cell_sizes(payloads))
        pairs.append(pages[0].pair is not None)
    deepest = sum(pairs)
    # The cell says "up to depth d", which is only true if pairing never
    # comes back at a deeper clue once it has stopped.
    assert pairs == [True] * deepest + [False] * (len(pairs) - deepest), (width, height, pairs)
    return f"2 up to depth {deepest}" if deepest else "1"


def _solution_cell(gen: BookPDFGenerator, width: int, height: int, depth: int) -> str:
    """Four same-level answers of one size: the page the first one lands on."""
    payloads = [gen._payload(_puzzle(width, height, depth, n)) for n in (1, 2, 3, 4)]
    answers = [
        Answer(
            number=n,
            width=_answer_extent(p, n)[0],
            height=_answer_extent(p, n)[1],
            level=_pairable_tier(p),
        )
        for n, p in enumerate(payloads, start=1)
    ]
    spec = answer_section_spec(gen.page_spec(11))
    plan = _degrade_infeasible_packed_pages(
        plan_small_answer_pages(answers), list(zip((1, 2, 3, 4), payloads)), spec
    )
    first = plan[0]
    if not isinstance(first, PackedAnswerPage):
        return "1 per page"
    members = [(p.row_clues, p.column_clues) for p in payloads[: len(first.answers)]]
    packed = compute_packed_solved_layout(members, first.capacity, spec)
    assert packed is not None
    return f"{first.capacity} at {packed.cell_mm:.2f} mm"


def _table(cell) -> str:
    generators = [(name, _generator(w, h)) for name, w, h in TRIMS]
    lines = [
        "| Size (w x h) | " + " | ".join(name for name, _ in generators) + " |",
        "|---|" + "---|" * len(generators),
    ]
    for width, height in SIZES:
        cells = [cell(gen, width, height) for _, gen in generators]
        lines.append(f"| {width}x{height} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def generated_blocks() -> dict[str, str]:
    """Every generated block of the doc, as the code produces it now."""
    return {
        "packing-constants": _constants_block(),
        "puzzles-per-page": _table(_puzzle_cell),
        "solutions-per-page-typical": _table(
            lambda gen, w, h: _solution_cell(gen, w, h, TYPICAL_DEPTH)
        ),
        "solutions-per-page-deepest": _table(
            lambda gen, w, h: _solution_cell(gen, w, h, _deepest(w, h))
        ),
    }


def _block_pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        rf"(<!-- BEGIN {re.escape(name)} -->\n)(.*?)(\n<!-- END {re.escape(name)} -->)",
        re.DOTALL,
    )


def documented_blocks(text: str) -> dict[str, str]:
    found = {}
    for match in re.finditer(r"<!-- BEGIN ([\w-]+) -->\n(.*?)\n<!-- END \1 -->", text, re.DOTALL):
        assert match.group(1) not in found, f"block {match.group(1)} appears twice"
        found[match.group(1)] = match.group(2)
    return found


def test_the_packing_doc_states_the_codes_constants() -> None:
    """AC-8: the constants block is the code's constants, and the doc states CARD-485's footer rule."""
    text = DOC.read_text(encoding="utf-8")
    assert documented_blocks(text).get("packing-constants") == _constants_block()
    # CARD-485: a single-puzzle page reserves the footer strip as a two-up page does.
    assert "footer_reserve_px" in text and "single-puzzle page" in text


def test_the_packing_doc_tables_are_what_the_planner_produces() -> None:
    """AC-8: each table is the real planner's output for each documented size and trim."""
    documented = documented_blocks(DOC.read_text(encoding="utf-8"))
    generated = generated_blocks()
    assert sorted(documented) == sorted(generated)
    for name in ("puzzles-per-page", "solutions-per-page-typical", "solutions-per-page-deepest"):
        assert documented[name] == generated[name], f"{name}:\n{generated[name]}"

    # The tables copy interior_stream's answer-planning steps rather than call
    # it, so the copy is also checked against the real export (review F-2): a
    # book of four such puzzles, its answer-page count from `interior_stream`
    # itself. 6x9, 10x30 at depth 12 is a case where the degrade pass splits a
    # 4-up page only on the answer page's own spec (running head and footer
    # strips off); its deepest-clue row is checked as the doc prints it.
    trim, width, height = "6x9 in", 10, 30
    column = [name for name, _, _ in TRIMS].index(trim) + 1
    _, width_cm, height_cm = TRIMS[column - 1]
    gen = _generator(width_cm, height_cm)
    (row,) = [
        line for line in documented["solutions-per-page-deepest"].splitlines()
        if line.startswith(f"| {width}x{height} |")
    ]
    for depth in (12, _deepest(width, height)):
        cell = (
            row.strip("|").split("|")[column].strip()
            if depth == _deepest(width, height)
            else _solution_cell(gen, width, height, depth)
        )
        capacity = 1 if cell == "1 per page" else int(cell.split(" at ")[0])
        puzzles = [_puzzle(width, height, depth, n) for n in (1, 2, 3, 4)]
        exported = _generator(width_cm, height_cm).interior_stream(puzzles).answer_page_count
        assert exported == -(-4 // capacity) == 2, (depth, cell, exported)


#: The marks of the retired answer-key rule (AC-9). Read case-insensitively.
RETIRED_RULE = (
    r"\b(6|six)[- ]up\b",
    r"\b(6|six) (answers )?(per|to a) page\b",
    r"\bup to \**6\b",
    r"longest[- ]side",
    r"\blonger than 20\b|[≤<]=? ?20\b",
    r"grid only|grid-only|\bno clues\b|no (row or column )?clue numbers?|without (its |their )?clues|clueless",
    r"(?<![\d.])5(\.0)? ?mm\b",
)


def _fr042_text() -> str:
    data = yaml.safe_load((REPO_ROOT / "meta/architecture/requirements.yml").read_text(encoding="utf-8"))
    (fr,) = [entry for entry in data["functional"] if entry.get("id") == "FR-042"]
    parts = [fr["statement"]]
    for criterion in fr.get("acceptance", []):
        parts += [str(criterion.get(key, "")) for key in ("given", "when", "then")]
    parts += [str(rule.get("statement", "")) for rule in fr.get("engineering_constraints", [])]
    return "\n".join(parts)


def _lines_starting(path: str, *prefixes: str) -> str:
    lines = (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
    picked = [line for line in lines if line.lstrip().startswith(prefixes)]
    assert len(picked) >= len(prefixes), (path, prefixes, picked)
    return "\n".join(picked)


def _span(path: str, start: str, stop: str | tuple[str, ...]) -> str:
    """The text of ``path`` from the line starting ``start`` up to the next line starting ``stop``."""
    lines = (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
    (first,) = [i for i, line in enumerate(lines) if line.startswith(start)]
    rest = [i for i in range(first + 1, len(lines)) if lines[i].startswith(stop)]
    return "\n".join(lines[first : rest[0] if rest else len(lines)])


HOW_IT_WORKS = "docs/how-it-works/01-domain/puzzle-creation/07-book-assembly-and-the-admin-panel.md"


def answer_key_passages() -> dict[str, str]:
    """Where FR-042 and the named docs state the answer key's rule."""
    module = ast.get_docstring(ast.parse(Path(book_answer_key.__file__).read_text(encoding="utf-8")))
    assert module
    return {
        "requirements.yml FR-042": _fr042_text(),
        "07 how-it-works, The answer key": _span(HOW_IT_WORKS, "### The answer key", "#"),
        "07 how-it-works, book_answer_key.py": _span(
            HOW_IT_WORKS, "- **`book_answer_key.py`**", ("- **", "#")
        ),
        "book_generation_admin_panel.md": _lines_starting(
            "docs/book_generation_req/book_generation_admin_panel.md",
            "| Solutions |",
            "- **BK-8",
            "| BK-8 |",
        ),
        "book_admin_ui_requirements.md rule 12": _lines_starting(
            "docs/book_generation_req/book_admin_ui_requirements.md", "12. Answers"
        ),
        "book_answer_key.py module docstring": module,
    }


def retired_rule_hits(passages: dict[str, str]) -> list[str]:
    return [
        f"{where}: {match.group(0)!r} ({pattern})"
        for where, text in passages.items()
        for pattern in RETIRED_RULE
        for match in re.finditer(pattern, text, re.IGNORECASE)
    ]


def test_the_retired_answer_key_rule_is_gone_from_the_requirements_and_docs() -> None:
    """AC-9: no passage that states the answer key carries the retired rule."""
    passages = answer_key_passages()
    assert all(text.strip() for text in passages.values())
    hits = retired_rule_hits(passages)
    assert not hits, "\n".join(hits)


def _rewrite_doc() -> None:
    text = DOC.read_text(encoding="utf-8")
    for name, block in generated_blocks().items():
        pattern = _block_pattern(name)
        assert pattern.search(text), f"no {name} block in {DOC}"
        text = pattern.sub(lambda m: m.group(1) + block + m.group(3), text)
    DOC.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    _rewrite_doc()
    sys.exit(0)
