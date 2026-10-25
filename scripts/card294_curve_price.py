#!/usr/bin/env python
"""CARD-294 — price the interior's round shape, the one unmeasured primitive.

CARD-293's spike drew straight lines, rectangles, fills and text and **never
a round shape**. AC-3 of CARD-294 asks for that primitive's price — lines of
code, operators per shape, and a verdict on whether a four-Bézier circle is
accurate enough for a difficulty dot at the size the book actually prints —
and this script is where every figure in
``meta/profiling/card-294-curve-price.md`` comes from. Re-run it and the
document reproduces.

Nothing imports this. It lives in ``scripts/`` because CARD-294's G-7 keeps
probes out of ``tests/``: ``meta/profiling/rank_durations.py`` defines the
frozen render-heavy set by grepping eight idioms over ``tests/**/*.py`` and
``tests/test_suite_profile.py`` asserts the live grep equal to a snapshot, so
a throwaway file under ``tests/`` is a red suite.

Three of the four measurements here are **deliberately second
implementations** of what the tests assert, not shared code with them
(CLAUDE.md: prefer an independent second implementation over re-deriving a
value with the function under test):

* the operator tally is tokenised here by a hand-written scanner, while
  ``tests/helpers/pdf_vector.py`` tokenises with a regular expression;
* the radial error is swept here over one quadrant in closed form, while the
  test samples all four quadrants of the *emitted* control points read back
  out of the content stream;
* the code-line count is an ``ast`` walk here and is not asserted by any test
  at all — it is a measurement of the source, and the artefact records it.

Usage::

    python scripts/card294_curve_price.py
    python scripts/card294_curve_price.py --samples 2000000
"""

from __future__ import annotations

import argparse
import ast
import math
import sys
import zlib
from pathlib import Path
from typing import Iterator, Sequence

_ROOT = Path(__file__).resolve().parent.parent
for _entry in (str(_ROOT / "src"), str(_ROOT)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

from nonogram.admin import book_vector  # noqa: E402
from nonogram.export.layout import (  # noqa: E402
    DPI,
    HEADER_BAND_MM,
    MIN_DIFFICULTY_DOT_MM,
    difficulty_dots,
)

MM_PER_INCH = 25.4

#: The resolutions a verdict is stated at: the book's own, a doubling, a press
#: RIP (the one CARD-293 measured the owner's rule weights at), and a high-end
#: imagesetter. Stated rather than inferred, because an accuracy claim that
#: does not name its resolution says nothing (ADR-0042/R6's second exemption
#: makes the same point about rendered widths).
RESOLUTIONS = (300, 600, 1200, 2400)

#: The kappa that minimises the *maximum* radial error, for comparison with
#: the one the module ships. Its error alternates in sign, so the mark's
#: bounding box is no longer exactly the declared diameter — which is why it
#: is reported here and not used.
MINIMAX_KAPPA = 0.5519150244935105

#: The names whose code lines are the round shape's price in lines.
CURVE_PRIMITIVE_NAMES = (
    "ContentStream.curve",
    "ContentStream.begin_path",
    "ContentStream.close_path",
    "ContentStream.paint",
    "ContentStream.round_mark",
)

#: For scale: the names the rest of the path vocabulary costs, so "the curve
#: is N lines" can be read against something.
STRAIGHT_PRIMITIVE_NAMES = (
    "ContentStream.line",
    "ContentStream.line_to",
    "ContentStream.rectangle",
)

#: The font work's price in lines. **Every top-level name of the module is
#: classified here or in :data:`NOT_FONT_NAMES`, and the partition is checked
#: against the module's own AST** (:func:`check_name_partition`) — a top-level
#: name in neither raises, so the script cannot report a font total that has
#: silently stopped covering the module.
#:
#: Why it is a partition and not a list: review cycle 2 found this tuple had
#: been TRANSCRIBED and then drifted. `_cap_height` (25 lines) and `_table` (5)
#: were added to `book_vector.py` by fix round 1 and never added here, so the
#: artefact reported the face at **216 lines when it was 246** — in a document
#: whose own §1 asserts "every figure in this table is re-derived and none is
#: transcribed". The figure WAS derived; its scope was hand-held. Deriving the
#: scope is what closes that, rather than correcting the number.
FONT_NAMES = (
    "FontMetrics",
    "_sfnt_tables",
    "_table",
    "_cmap_format_4",
    "_unicode_cmap",
    "_advances",
    "_cap_height",
    "_encoded_codepoints",
    "encode_text",
    "font_metrics",
    "interior_face_bytes",
    "interior_face_metrics",
    "_write_face",
)

#: The module's other top-level names, declared so the partition above is
#: total. Each is here for a stated reason rather than by omission:
#: `ContentStream` and `Layout` are the drawing vocabulary (priced by
#: :data:`CURVE_PRIMITIVE_NAMES` / :data:`STRAIGHT_PRIMITIVE_NAMES` at method
#: granularity, so counting the class whole would double-count), `_number`,
#: `_escape` and `_PLACES`' helpers are stream serialisation shared by every
#: primitive, `write_vector_pdf` is the document writer, and
#: `ContentStreamError` / `UnrepresentableText` are the error types.
NOT_FONT_NAMES = (
    "ContentStream",
    "ContentStreamError",
    "UnrepresentableText",
    "_number",
    "_grey",
    "_paint_operator",
    "_escape",
    "_exactly",
    "write_vector_pdf",
)


def check_name_partition(source: str) -> tuple[int, int]:
    """``(font, other)`` counts, after proving the partition covers the module.

    Raises when a top-level ``def``/``class`` of ``book_vector.py`` is in
    neither tuple, or is in both, or names something the module does not
    define. The whole point is that adding a function to the module and not
    classifying it here is a FAILURE rather than a quietly smaller total.
    """
    import ast as _ast

    top = {
        node.name
        for node in _ast.parse(source).body
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef))
    }
    font, other = set(FONT_NAMES), set(NOT_FONT_NAMES)
    both = font & other
    if both:
        raise SystemExit(f"classified twice: {sorted(both)}")
    phantom = (font | other) - top
    if phantom:
        raise SystemExit(f"classified but not defined in book_vector.py: {sorted(phantom)}")
    unclassified = top - font - other
    if unclassified:
        raise SystemExit(
            "top-level name(s) in neither FONT_NAMES nor NOT_FONT_NAMES: "
            f"{sorted(unclassified)} — classify them, or the font total below "
            "stops covering the module (review cycle 2's N-1)"
        )
    return len(font), len(other)


# --------------------------------------------------------------------------
# Lines of code
# --------------------------------------------------------------------------


def code_lines(source: str, names: Sequence[str]) -> dict[str, int]:
    """``{name: code lines}`` — blanks, comments and docstrings excluded.

    Counted mechanically, the way CARD-293's §1 table was counted, so "the
    curve costs N lines" is a measurement rather than an impression. A name
    is a module-level ``def``/``class`` or ``Class.method``.
    """
    tree = ast.parse(source)
    lines = source.splitlines()
    out: dict[str, int] = {}
    for name in names:
        node = _find(tree, name)
        if node is None:
            raise SystemExit(f"{name} is not in the module")
        out[name] = 1 + sum(  # the def/class line, then its body
            1
            for statement in _without_docstring(node)
            for number in range(statement.lineno, (statement.end_lineno or statement.lineno) + 1)
            if lines[number - 1].strip() and not lines[number - 1].strip().startswith("#")
        )
    return out


def _without_docstring(node: ast.AST) -> list[ast.stmt]:
    body = list(getattr(node, "body", []))
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return body


def _find(tree: ast.AST, name: str) -> ast.AST | None:
    head, _, tail = name.partition(".")
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name != head:
                continue
            return _find(node, tail) if tail else node
    return None


# --------------------------------------------------------------------------
# Operators per shape
# --------------------------------------------------------------------------


def operators(stream: str) -> list[str]:
    """Every operator token of ``stream``, operands and strings skipped.

    A hand-written scanner rather than a regular expression, which is what
    ``tests/helpers/pdf_vector.py`` uses — two implementations of the same
    count, which is the only way a count of this kind is evidence.
    """
    out: list[str] = []
    for token in _tokens(stream):
        if token.startswith("/"):
            continue
        try:
            float(token)
        except ValueError:
            out.append(token)
    return out


def _tokens(stream: str) -> Iterator[str]:
    index, end = 0, len(stream)
    while index < end:
        char = stream[index]
        if char == "(":  # a literal string: skip it, escapes and nesting
            depth, index = 1, index + 1
            while index < end and depth:
                if stream[index] == "\\":
                    index += 2
                    continue
                depth += {"(": 1, ")": -1}.get(stream[index], 0)
                index += 1
            continue
        if char.isspace():
            index += 1
            continue
        start = index
        while index < end and not stream[index].isspace() and stream[index] != "(":
            index += 1
        yield stream[start:index]


def shape_prices() -> dict[str, list[str]]:
    """One of each primitive, alone on its own page, as operator lists."""
    prices: dict[str, list[str]] = {}

    def one(name: str, draw) -> None:
        stream = book_vector.ContentStream(width_px=600, height_px=600, dpi=DPI)
        draw(stream)
        prices[name] = operators(stream.render().decode(book_vector.TEXT_ENCODING))

    one("line", lambda s: s.line(10, 10, 10, 500))
    one("rectangle (stroked)", lambda s: s.rectangle(10, 10, 500, 500))
    one("rectangle (filled)", lambda s: s.rectangle(10, 10, 500, 500, paint="fill"))
    one("text", lambda s: s.text("Puzzle 12", 10, 10, 10.0))
    one("stroke width + tone", lambda s: (s.stroke_width(0.3), s.stroke_grey(0.35)))
    one("round mark (filled)", lambda s: s.round_mark(300, 300, 21))
    one("round mark (outlined)", lambda s: s.round_mark(300, 300, 21, paint="both"))
    one("one bare cubic", lambda s: (s.begin_path(0, 0), s.curve(1, 1, 2, 2, 3, 3)))
    return prices


# --------------------------------------------------------------------------
# Accuracy
# --------------------------------------------------------------------------


def worst_radial_error(kappa: float, samples: int) -> tuple[float, float, float]:
    """``(lowest, highest, max abs)`` signed radial error, in units of radius.

    One quadrant of the unit circle in closed form: the cubic from ``(0, 1)``
    to ``(1, 0)`` with controls ``(kappa, 1)`` and ``(1, kappa)``. The four
    quadrants are rotations of each other, so one is the whole claim.
    """
    points = ((0.0, 1.0), (kappa, 1.0), (1.0, kappa), (1.0, 0.0))
    lowest = highest = 0.0
    for index in range(samples + 1):
        t = index / samples
        u = 1.0 - t
        weights = (u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t)
        x = sum(w * p[0] for w, p in zip(weights, points))
        y = sum(w * p[1] for w, p in zip(weights, points))
        error = math.hypot(x, y) - 1.0
        lowest, highest = min(lowest, error), max(highest, error)
    return lowest, highest, max(abs(lowest), abs(highest))


def printed_dot_diameters_mm() -> dict[str, float]:
    """The dot sizes the book really prints, from COMP-007's own measurement.

    Not invented sizes: the floor is :data:`MIN_DIFFICULTY_DOT_MM`, below
    which ``difficulty_dots`` returns ``None`` and nothing is drawn, and the
    ceiling is what a box as deep as a puzzle page's header band gives when
    the height cap rather than the width fit decides — ``DIFFICULTY_DOT_RATIO``
    of :data:`HEADER_BAND_MM`, asked of the function rather than multiplied
    out here.
    """
    band_px = round(HEADER_BAND_MM * DPI / MM_PER_INCH)
    widest = difficulty_dots(0, 0, 40 * band_px, band_px - 1, filled=2, total=3)
    assert widest is not None, "a full band cannot hold a dot?"
    return {
        "floor (difficulty_dots declines below it)": MIN_DIFFICULTY_DOT_MM,
        "puzzle-page band cap": widest.diameter * MM_PER_INCH / DPI,
    }


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=2_000_000)
    args = parser.parse_args(argv)

    source = Path(book_vector.__file__).read_text(encoding="utf-8")
    curve = code_lines(source, CURVE_PRIMITIVE_NAMES)
    straight = code_lines(source, STRAIGHT_PRIMITIVE_NAMES)
    n_font, n_other = check_name_partition(source)
    font = code_lines(source, FONT_NAMES)
    print(
        f"<!-- scope checked: {n_font} font + {n_other} other = "
        f"{n_font + n_other} top-level names, partition total -->\n"
    )

    print("## Lines of code (blanks, comments and docstrings excluded)\n")
    print("| piece | code lines |")
    print("|---|---|")
    for name, count in curve.items():
        print(f"| `{name}` | {count} |")
    print(f"| **the round shape, total** | **{sum(curve.values())}** |")
    for name, count in straight.items():
        print(f"| `{name}` (for scale) | {count} |")
    print(f"| the straight-line vocabulary, total | {sum(straight.values())} |")
    print(f"| the embedded face, total | {sum(font.values())} |")

    print("\n## Operators per shape\n")
    print("| shape | operators | the tokens |")
    print("|---|---|---|")
    for name, tokens in shape_prices().items():
        print(f"| {name} | {len(tokens)} | `{' '.join(tokens)}` |")

    print("\n## Bytes of content stream\n")
    print("| shape | raw | deflated |")
    print("|---|---|---|")
    for name, draw in (
        ("straight line", lambda s: s.line(10, 10, 10, 2000)),
        ("round mark, r=6 px (the floor dot)", lambda s: s.round_mark(1275, 1650, 6)),
        ("round mark, r=21 px (the band cap)", lambda s: s.round_mark(1275, 1650, 21)),
        ("round mark, r=60 px", lambda s: s.round_mark(1275, 1650, 60)),
        (
            "a three-dot difficulty glyph",
            lambda s: [s.round_mark(100 + index * 50, 100, 21) for index in range(3)],
        ),
    ):
        stream = book_vector.ContentStream(width_px=2550, height_px=3300, dpi=DPI)
        draw(stream)
        raw = stream.render()
        print(f"| {name} | {len(raw)} B | {len(zlib.compress(raw, 9))} B |")

    print("\n## Accuracy of the four-Bézier circle\n")
    print(f"Swept at {args.samples:,} + 1 points over one quadrant.\n")
    print("| kappa | signed radial error / r | max abs | bounding box |")
    print("|---|---|---|---|")
    for label, kappa, box in (
        ("`4*(sqrt(2)-1)/3` (shipped)", book_vector.BEZIER_CIRCLE_KAPPA, "exact"),
        ("0.5519150244935105 (min-max)", MINIMAX_KAPPA, "**under** the diameter"),
    ):
        low, high, worst = worst_radial_error(kappa, args.samples)
        print(f"| {label} | [{low:+.4e}, {high:+.4e}] | {worst:.6e} | {box} |")

    _, _, worst = worst_radial_error(book_vector.BEZIER_CIRCLE_KAPPA, args.samples)
    rounding_mm = 10.0 ** -3 / book_vector.POINTS_PER_INCH * MM_PER_INCH
    print(
        f"\nThe stream writes coordinates to 0.001 pt, which is "
        f"{rounding_mm:.6f} mm — the number to read the error against.\n"
    )
    print("| printed dot | radius | worst error | " + " | ".join(
        f"as device px @ {dpi} DPI" for dpi in RESOLUTIONS
    ) + " |")
    print("|---|---|---|" + "---|" * len(RESOLUTIONS))
    for label, diameter_mm in printed_dot_diameters_mm().items():
        radius_mm = diameter_mm / 2.0
        error_mm = worst * radius_mm
        cells = " | ".join(
            f"{error_mm / MM_PER_INCH * dpi:.5f}" for dpi in RESOLUTIONS
        )
        print(
            f"| {label}: {diameter_mm:.3f} mm | {radius_mm:.4f} mm | "
            f"{error_mm:.3e} mm | {cells} |"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - a probe
    raise SystemExit(main())
