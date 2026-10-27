"""CARD-295 AC-5 — what the vector puzzle page actually costs, measured.

Three questions, because the phase has three different numbers riding on this
card and they are not the same measurement:

    bytes   The written interior's puzzle-page bytes, vector against raster,
            over the Book 1 corpus. The spike's figure to beat is 407,976 B
            against 9,157,535 B for 24 pages (ADR-0042's Context).
    time    Generation wall clock, interleaved A/B/A/B, min and median, with
            the load average at both ends (CARD-292's AC-6 convention).
    claim   The one nobody has: what a CONVERTED ASSERTION costs. The spike
            measured the replacement at 4.1x smaller in LINES and the joined
            profile (meta/profiling/interior-raster-share-20261026.txt) says
            in as many words that "no one has measured a converted test's
            wall clock, and CARD-295/296/297 are the first chance to". This
            subcommand asserts ONE claim both ways — "every fifth grid rule
            is wider than the rules between them" — and times the two arms
            interleaved, with a COUNTER beside the stopwatch: how many page
            bitmaps each arm allocates, in the project's own
            PAGE_BITMAP_BYTES unit, which is exact and machine-independent
            where a wall clock is neither.

Run it, do not read figures out of it:

    .venv/bin/python meta/profiling/card295_puzzle_page_price.py bytes
    .venv/bin/python meta/profiling/card295_puzzle_page_price.py time --runs 7
    .venv/bin/python meta/profiling/card295_puzzle_page_price.py claim --runs 7

The recorded answers are in meta/profiling/card-295-puzzle-page-price.md,
with the load averages and the machine state the convention asks for.

**Nothing at module scope can stop this file being collected.**
``tests/test_guard_integrity.py::TestGuardModule_CannotGoQuietAboveItsOwnGuards``
walks ``meta/profiling/`` as well as ``tests/``, and a module-scope
``sys.exit()`` under a condition red the whole board two commits ago
(``fcd03c99``). Everything below lives inside a function.
"""

import json
import os
import statistics
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The project's own unit of retention (tests/test_book_pdf_memory.py).
PAGE_BITMAP_BYTES = 2550 * 3300 * 3


def _imports():
    """Everything this instrument needs, imported inside a call.

    ``sys.path`` is extended here rather than at module scope for the reason
    the docstring gives: this file is walked by a guard, and a guard that
    cannot import it is a guard that reports nothing.
    """
    for entry in (str(ROOT / "src"), str(ROOT)):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    import numpy as np

    from nonogram.admin.book_pdf_generator import BookPDFGenerator, print_order
    from nonogram.admin.book_vector import write_vector_pdf
    from tests.helpers.book_corpus import corpus_book, corpus_puzzles

    return BookPDFGenerator, print_order, write_vector_pdf, corpus_book, corpus_puzzles, np


def _arms(limit):
    """The book both arms draw, and the plan both arms draw it to.

    One plan, read once, so the two arms are the same pages in the same order
    at the same cell — "print what each arm IS" (CARD-292's G-4).
    """
    BookPDFGenerator, print_order, _write, corpus_book, corpus_puzzles, _np = _imports()
    generator = BookPDFGenerator(corpus_book())
    payloads = [
        BookPDFGenerator._payload(row) for row in print_order(corpus_puzzles())[:limit]
    ]
    sizes = generator.cell_sizes(payloads)
    plan = generator.puzzle_pages(payloads, cell_sizes=sizes)
    return generator, payloads, sizes, plan


def _raster_pages(generator, payloads, sizes, plan):
    for entry in plan:
        members = [payloads[number - 1] for number in entry.numbers]
        if entry.pair is None:
            yield generator._blank_page(
                members[0], entry.numbers[0], entry.page_number, sizes
            )
        else:
            yield generator._two_up_page(entry, members)


def _vector_streams(generator, payloads, sizes, plan):
    for entry in plan:
        members = [payloads[number - 1] for number in entry.numbers]
        if entry.pair is None:
            yield generator.vector_puzzle_page(
                members[0], entry.numbers[0], entry.page_number, sizes
            )
        else:
            yield generator.vector_two_up_page(entry, members)


def _identity(generator, payloads, plan):
    from collections import Counter

    return {
        "book": "corpus_book() — CON-018's Book 1 profile",
        "puzzles": len(payloads),
        "pages": len(plan),
        "two_up_pages": sum(1 for entry in plan if entry.is_two_up),
        "grid_sizes": dict(
            sorted(Counter(f"{p.width}x{p.height}" for p in payloads).items())
        ),
        "trim_px": [generator.page_width_px, generator.page_height_px],
        "dpi": generator.dpi,
        "interior_bitmap_mode": generator.interior_bitmap_mode,
    }


def cmd_bytes(args):
    _B, _o, write_vector_pdf, _cb, _cp, _np = _imports()
    generator, payloads, sizes, plan = _arms(args.limit)

    streams = list(_vector_streams(generator, payloads, sizes, plan))
    vector = write_vector_pdf(streams, len(streams)).getvalue()
    raster = generator._write_pdf(
        _raster_pages(generator, payloads, sizes, plan),
        len(plan),
        mode=generator.interior_bitmap_mode,
    ).getvalue()

    face = len(zlib.compress(
        __import__("nonogram.admin.book_vector", fromlist=["x"]).interior_face_bytes(), 9
    ))
    report = {
        "arm_identity": _identity(generator, payloads, plan),
        "vector_pdf_bytes": len(vector),
        "raster_pdf_bytes": len(raster),
        "ratio": round(len(raster) / len(vector), 2),
        "vector_per_page": round(len(vector) / len(plan)),
        "raster_per_page": round(len(raster) / len(plan)),
        "vector_font_once_bytes": face,
        "vector_per_page_excluding_font": round((len(vector) - face) / len(plan)),
        "ratio_excluding_font": round(
            len(raster) / max(1, len(vector) - face), 2
        ),
        "per_page_stream_bytes": [len(s.render()) for s in streams],
        "per_page_operators": [len(s.operators) for s in streams],
    }
    print(json.dumps(report, indent=2))


def cmd_time(args):
    _B, _o, write_vector_pdf, _cb, _cp, _np = _imports()
    generator, payloads, sizes, plan = _arms(args.limit)

    def vector_arm():
        streams = _vector_streams(generator, payloads, sizes, plan)
        return len(write_vector_pdf(streams, len(plan)).getvalue())

    def raster_arm():
        pages = _raster_pages(generator, payloads, sizes, plan)
        return len(
            generator._write_pdf(
                pages, len(plan), mode=generator.interior_bitmap_mode
            ).getvalue()
        )

    load_start = os.getloadavg()
    runs = {"vector": [], "raster": []}
    sizes_seen = {}
    order = []
    for _ in range(args.runs):
        for name, arm in (("vector", vector_arm), ("raster", raster_arm)):
            started = time.perf_counter()
            sizes_seen[name] = arm()
            runs[name].append(round(time.perf_counter() - started, 4))
            order.append(name)
    load_end = os.getloadavg()

    print(
        json.dumps(
            {
                "arm_identity": _identity(generator, payloads, plan),
                "arm_output_bytes": sizes_seen,
                "order": order,
                "raw_seconds": runs,
                "min": {k: round(min(v), 4) for k, v in runs.items()},
                "median": {k: round(statistics.median(v), 4) for k, v in runs.items()},
                "ms_per_page": {
                    k: round(min(v) / len(plan) * 1000, 3) for k, v in runs.items()
                },
                "speedup_on_min": round(min(runs["raster"]) / min(runs["vector"]), 2),
                "loadavg_start": load_start,
                "loadavg_end": load_end,
            },
            indent=2,
        )
    )


def cmd_claim(args):
    """The same claim, asserted both ways, timed interleaved.

    The claim: **every fifth grid rule is wider than the rules between them,
    and the page has exactly two rule widths on it** — which is
    ``tests/test_book_pdf_band.py``'s
    ``TestBookPdf_EveryFifthGridLineWider`` in its ink form.

    * the **ink arm** draws the page and then does exactly what that test
      does: ``page_ink.drawing_of`` to find the grid box (which is itself a
      scan of **every** line of a 2550x3300 page for its longest unbroken
      run), one scanline through the middle of the first cell, and the runs
      of ink along it. That is the reconstruction ADR-0042/R6 retires, and
      the helper is the project's own, not a simplification of it.
    * the **stream arm** writes the page, reads the ``w`` operands out of the
      content stream, and compares them.

    **Both arms draw the same page through the generator**, so what is being
    timed is the *reading*, plus the medium's own cost of producing something
    to read. The interior walk that a whole-file conversion would also pay is
    deliberately outside both arms: it is the same work either way, and
    including it would flatter the stream arm by a constant.

    Both arms **assert**, so neither is timing an empty loop, and both are
    checked to agree before either is timed.
    """
    _B, _o, write_vector_pdf, _cb, _cp, np = _imports()
    from tests.helpers import pdf_vector
    from tests.helpers.page_ink import drawing_of

    generator, payloads, sizes, plan = _arms(args.limit)
    entry = next(e for e in plan if not e.is_two_up)
    payload = payloads[entry.numbers[0] - 1]

    bitmaps = {"ink": 0, "stream": 0}

    def ink_arm():
        page = generator._blank_page(payload, entry.numbers[0], entry.page_number, sizes)
        bitmaps["ink"] += page.width * page.height * len(page.getbands())
        drawing = drawing_of(page)
        pixels = np.asarray(page.convert("L"))
        row = drawing.grid_top + round(
            (drawing.grid_bottom - drawing.grid_top) / drawing.rows / 2
        )
        scan = pixels[
            row,
            drawing.grid_left : drawing.grid_right
            + round((drawing.grid_right - drawing.grid_left) / drawing.columns),
        ]
        widths, run = [], 0
        for value in scan < 128:
            if value:
                run += 1
            elif run:
                widths.append(run)
                run = 0
        if run:
            widths.append(run)
        found = sorted(set(widths))
        assert len(found) == 2, found
        assert found[1] > found[0], found
        return found

    def _widths_from(written):
        found = sorted(set(pdf_vector.stroke_widths(written)))
        assert len(found) == 2, found
        assert found[1] > found[0], found
        return found

    def stream_file_arm():
        """One PDF per assertion — the naive conversion."""
        stream = generator.vector_puzzle_page(
            payload, entry.numbers[0], entry.page_number, sizes
        )
        data = write_vector_pdf([stream], 1).getvalue()
        (written,) = pdf_vector.content_streams(data)
        return _widths_from(written)

    # One interior written once, as a class- or module-scoped fixture would.
    # The assertion then reads page N out of it, which is what a converted
    # test in a file that makes several claims about one book really costs.
    shared = write_vector_pdf(
        list(_vector_streams(generator, payloads, sizes, plan)), len(plan)
    ).getvalue()
    page_index = [e.page_number for e in plan].index(entry.page_number)

    def stream_shared_arm():
        """The claim read off an interior somebody else already wrote."""
        return _widths_from(pdf_vector.content_streams(shared)[page_index])

    def stream_operators_arm():
        """The stream without a file at all — what ADR-0042/R6 does NOT ask for.

        Measured because it bounds the other two: it is the drawing cost and
        nothing else, so the gap between it and ``stream_file`` is exactly
        what writing and re-reading a PDF costs an assertion.
        """
        stream = generator.vector_puzzle_page(
            payload, entry.numbers[0], entry.page_number, sizes
        )
        return _widths_from("\n".join(stream.operators))

    arms = (
        ("ink", ink_arm),
        ("stream_file", stream_file_arm),
        ("stream_shared", stream_shared_arm),
        ("stream_operators", stream_operators_arm),
    )
    agreed = {name: arm() for name, arm in arms}
    bitmaps["ink"] = 0

    # Where the time in the naive arm actually goes, so the headline below is
    # explained by a measurement and not by a guess.
    def _time(call, runs):
        return round(min(time_one(call) for _ in range(runs)), 5)

    def time_one(call):
        started = time.perf_counter()
        call()
        return time.perf_counter() - started

    one_stream = generator.vector_puzzle_page(
        payload, entry.numbers[0], entry.page_number, sizes
    )
    one_pdf = write_vector_pdf([one_stream], 1).getvalue()
    parts = {
        "draw_the_page": _time(
            lambda: generator.vector_puzzle_page(
                payload, entry.numbers[0], entry.page_number, sizes
            ),
            args.runs,
        ),
        "write_a_one_page_pdf": _time(
            lambda: write_vector_pdf([one_stream], 1).getvalue(), args.runs
        ),
        # The suspected dominant term of the line above, timed on its own:
        # ``write_vector_pdf`` Flate-compresses the whole 757 KB face at
        # level 9 once per FILE (ADR-0042/R5), which is free across a 24-page
        # interior and is the entire cost of a one-page one.
        "flate_the_embedded_face": _time(
            lambda: zlib.compress(_face_bytes(), 9), args.runs
        ),
        "flate_the_page_stream": _time(
            lambda: zlib.compress(one_stream.render(), 9), args.runs
        ),
        "read_the_stream_back": _time(
            lambda: pdf_vector.content_streams(one_pdf), args.runs
        ),
        "draw_the_raster_page": _time(
            lambda: generator._blank_page(
                payload, entry.numbers[0], entry.page_number, sizes
            ),
            args.runs,
        ),
    }

    load_start = os.getloadavg()
    runs = {name: [] for name, _ in arms}
    order = []
    for _ in range(args.runs):
        for name, arm in arms:
            started = time.perf_counter()
            arm()
            runs[name].append(round(time.perf_counter() - started, 5))
            order.append(name)
    load_end = os.getloadavg()

    print(
        json.dumps(
            {
                "arm_identity": _identity(generator, payloads, plan),
                "page": f"{payload.width}x{payload.height} @ interior page {entry.page_number}",
                "every_arm_agrees_on": agreed,
                "order": order,
                "raw_seconds": runs,
                "min": {k: round(min(v), 5) for k, v in runs.items()},
                "median": {k: round(statistics.median(v), 5) for k, v in runs.items()},
                "speedup_on_min_against_ink": {
                    k: round(min(runs["ink"]) / min(v), 2)
                    for k, v in runs.items()
                    if k != "ink"
                },
                "where_the_time_goes_min_seconds": parts,
                "page_bitmaps_allocated": {
                    "ink": round(bitmaps["ink"] / PAGE_BITMAP_BYTES / args.runs, 4),
                    "stream_file": 0.0,
                    "stream_shared": 0.0,
                    "stream_operators": 0.0,
                },
                "loadavg_start": load_start,
                "loadavg_end": load_end,
            },
            indent=2,
        )
    )


def _face_bytes():
    """The embedded face's raw bytes, through the module that owns them."""
    from nonogram.admin.book_vector import interior_face_bytes

    return interior_face_bytes()


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=24, help="puzzles to draw")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bytes").set_defaults(func=cmd_bytes)
    timed = sub.add_parser("time")
    timed.add_argument("--runs", type=int, default=5)
    timed.set_defaults(func=cmd_time)
    claim = sub.add_parser("claim")
    claim.add_argument("--runs", type=int, default=5)
    claim.set_defaults(func=cmd_claim)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
