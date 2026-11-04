"""CARD-337: what a VECTOR interior page declares about colour, measured.

The module under repair asks "what colour space does the FILE declare", off
image XObjects. A vector page has none. This script answers the ADR-0042/R6
question -- *is there an equivalent declaration in the content stream?* -- by
measurement rather than by reading the writer:

1. export the same book both ways with the five kinds lifted to vector;
2. decompress every page's content stream and collect every colour-setting
   operator actually emitted (`g`, `G`, `rg`, `RG`, `k`, `K`, `cs`, `CS`, `sc`,
   `scn`, `SC`, `SCN`);
3. report the page Resources' `ProcSet` and whether any `/ColorSpace` is named;
4. diff the two modes' bytes.

Everything printed is read off the produced file. Nothing asks the generator
what it meant to do.
"""
from __future__ import annotations

import hashlib
import re
import sys
import zlib
from io import BytesIO

sys.path.insert(0, "src")
sys.path.insert(0, ".")

from scratchpad.card338 import probe_five_kinds


class _Config:
    pass


probe_five_kinds.pytest_configure(_Config())

from PIL import PdfParser

from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_page_spec import InkMode
from tests.helpers.book_corpus import baseline_puzzles, corpus_book, export_of

#: Every colour-setting operator PDF has, so "which did it emit" is a derived
#: answer and not a search for the two I expected.
COLOUR_OPS = ("g", "G", "rg", "RG", "k", "K", "cs", "CS", "sc", "scn", "SC", "SCN")
TOKEN = re.compile(rb"(?<![A-Za-z0-9*'\"])(" + b"|".join(
    op.encode() for op in COLOUR_OPS) + rb")(?![A-Za-z0-9*'\"])")


def export(mode: InkMode) -> bytes:
    book = corpus_book("card-147")
    book.interior_ink_mode = mode.value
    return export_of(BookPDFGenerator(book), baseline_puzzles())


def read(data: bytes) -> dict:
    parser = PdfParser.PdfParser(buf=data)
    try:
        out = {"pages": [], "with_xobject": 0, "with_colorspace": 0}
        for ref in parser.pages:
            page = parser.read_indirect(ref)
            res = page[b"Resources"]
            has_xobj = b"XObject" in res
            has_cs = b"ColorSpace" in res
            out["with_xobject"] += int(has_xobj)
            out["with_colorspace"] += int(has_cs)
            procset = [getattr(n, "name", n) for n in res.get(b"ProcSet", [])]
            ops: set[str] = set()
            if not has_xobj:
                body = parser.read_indirect(page[b"Contents"])
                raw = zlib.decompress(body.buf)
                ops = {m.group(1).decode() for m in TOKEN.finditer(raw)}
            out["pages"].append(
                {
                    "xobject": has_xobj,
                    "colorspace": has_cs,
                    "procset": [p.decode() if isinstance(p, bytes) else str(p) for p in procset],
                    "colour_ops": sorted(ops),
                }
            )
        return out
    finally:
        parser.close()


bw = export(InkMode.BLACK_AND_WHITE)
colour = export(InkMode.COLOUR)

for label, data in (("BLACK_AND_WHITE", bw), ("COLOUR", colour)):
    info = read(data)
    print(f"--- {label}: {len(data)} bytes, sha256={hashlib.sha256(data).hexdigest()[:16]}")
    print(f"    pages={len(info['pages'])}  with XObject={info['with_xobject']}"
          f"  with /ColorSpace={info['with_colorspace']}")
    procsets = {tuple(p["procset"]) for p in info["pages"]}
    print(f"    distinct ProcSets: {sorted(procsets)}")
    ops = {tuple(p["colour_ops"]) for p in info["pages"] if not p["xobject"]}
    print(f"    distinct colour operator sets on VECTOR pages: {sorted(ops)}")

print()
print(f"len(bw) < len(colour) ?  {len(bw)} < {len(colour)} -> {len(bw) < len(colour)}")
print(f"bw == colour byte-for-byte ? {bw == colour}")
if bw != colour:
    # Where do they differ? The Info dictionary's two timestamps move per call,
    # so a difference is only interesting if it is outside them.
    diffs = [i for i, (a, b) in enumerate(zip(bw, colour)) if a != b]
    print(f"    differing byte offsets: {len(diffs)} (first 8: {diffs[:8]})")
    print(f"    lengths: {len(bw)} vs {len(colour)}")
