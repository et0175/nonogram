"""The books CARD-145's memory tests export, built the same way every time.

CARD-145 changes *when* an interior page is released, never what is drawn on
it (G-1). Proving that needs the same book twice — once exported by the code
as it stood at the merge-base, recorded as a fixture of per-page digests, and
once by the streaming path — so the book's construction lives here rather than
in the test that compares the two. A book built twice from two copies of the
same literals is a book that can silently stop being the same book.

Two corpora, for two different questions:

:func:`baseline_puzzles` is the **small, complete** book — four puzzles that
between them make the interior hold one of every page kind the generator can
produce: the guide (CARD-201: 2 pages), a level divider (TERM-031, CARD-128), a
single-puzzle page, a two-up page (FR-040), the SOLUTIONS divider and the
answer section (FR-042). Since CARD-202 three of its puzzles (Duck, Owl,
Tree) qualify for packing (width<=15, height<=20) and pack onto two pages
(Duck+Owl 2-up, Tree alone 2-up), while the fourth (Snowflake, 30x30) still
gets CARD-198's own full page — three answer pages, not the four pages
CARD-198 alone would have drawn, and not the three pages the pre-CARD-198
packed key drew either (one per *level*, a different three). Twelve interior
pages in all (CARD-201: up from eleven — the guide's second page), still
every one of them a different kind of drawing. That is
the book :data:`BASELINE_FIXTURE` records, and the one AC-3 compares page for
page.

:func:`corpus_puzzles` is the **large** book — a seeded corpus of 150 puzzles
(no ``hypothesis``: stdlib ``random.Random``, per CLAUDE.md), grouped by tier
the way INV-009 groups a real book, each one too large for two-up pairing to
shorten the interior. Since CARD-201 it yields a roughly 306-page interior:
2 guide + 3 level dividers + 150 puzzle pages + the SOLUTIONS divider + 150
answer pages — one per puzzle, where the former packed key took only 27. That
is the "150-page book" AC-1 and AC-2 talk about, and it is a real export —
the page count is never faked.

**The same book, exported inside a capped child process.**
:func:`capped_export_report` exports :func:`corpus_puzzles` in whatever
process calls it, in either the streaming shape or the list shape this card
removed, and reports the page count it read back out of the file and the
process's own high-water resident set. ``tests/test_book_pdf_memory.py``
calls it in a fresh interpreter that has installed a memory cap first, which
is how AC-2's "under a memory cap that the current code fails" is executed
rather than derived. Both shapes are the production calls — ``export_interior``
and ``interior_pages`` — so the capped run exports the same book the
in-process measurements do.

**Determinism, and the host gate that is gone (CARD-221).** Nothing here reads
a clock, a database or a dict whose order is not fixed: the grids are computed,
the ids and names are literals, the tiers are positional, and the sizes come
from a seeded ``Random`` drawn in a fixed order. **Nor does anything read the
host's fonts any more.** Until CARD-221 the guide pages, the dividers and the
TOC were lettered in whatever Arial ``ImageFont.truetype`` found on the
machine, with Pillow's built-in face as a fallback, so those pages' pixels —
and, through the TOC's own row height, a book's page count and its printed KDP
gutter — were a function of the host. This module therefore carried a
``font_fingerprint()`` of that face over a hand-transcribed
``MACHINE_FACE_SIZES`` tuple, and every fixture carried the digest and the
list of pages a mismatched machine had to skip. All three are **removed**:
``_guide_face`` now returns the packaged DejaVu Sans
(``src/nonogram/export/fonts/``, ADR-0006/R1 package data) that the band and
the folio were already set in, so every page of this book is comparable on
every machine and ``book_baseline_card221.json``'s own
``font_dependent_pages`` is empty.

The measurement that justifies removing them, rather than an argument that it
ought to be safe: ``tests/test_book_interior_face.py`` exports this same book
twice in one process — once with the host's Arial available, once with
``ImageFont.truetype`` made to refuse every host path — and finds every page's
digest, the page count and the chosen gutter band identical; and the
page-by-page comparison recorded in ``book_baseline_card221.json``'s
``why_a_new_baseline`` shows that exactly the seven pages lettered through
``_guide_face`` moved under that card and the other six are byte-identical to
CARD-205's digests. What remains host-dependent, and is deliberately outside
this helper's reach, is the **generated title cover** (``create_cover_page``
still asks the host for Arial at 72 px): the cover is a separate file, no
baseline digests it, and ``MACHINE_FACE_SIZES`` never covered its size for
exactly that reason.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Sequence

from PIL import Image

from nonogram import clues
from nonogram.admin.book_manager import Book, BookMetadata

#: CON-018's Book 1 profile in millimetres, written out here rather than
#: imported, exactly as ``tests/test_book_pdf.py`` writes it out.
BOOK1_WIDTH_MM = 8.5 * 25.4
BOOK1_HEIGHT_MM = 11 * 25.4
GUTTER_MM = 0.5 * 25.4
OUTSIDE_MM = 0.375 * 25.4

#: Where the recorded per-page evidence of the interior's pages lives.
#:
#: Six recordings of this same book now sit side by side, each kept and none
#: regenerated, because every change after the first was *deliberate* — the one
#: reason CARD-145's fixture's own ``warning`` admits a successor:
#:
#: * ``book_baseline_card145.json`` — the merge-base's eight pages, before a
#:   line of CARD-145's refactor existed;
#: * ``book_baseline_card128.json`` — CARD-128 made the interior print grouped
#:   by level and open each level with a divider page (INV-009, TERM-031), so
#:   the interior became eleven pages and every page after the guide moved;
#: * ``book_baseline_card144.json`` — CARD-144's frame closes a book puzzle page's
#:   drawing off with one heavy rectangle, so the pages that carry a drawing
#:   moved again on top of CARD-128's eleven;
#: * ``book_baseline_card149.json`` — CARD-149 sets the guide page's type from
#:   points instead of pixels (11 pt body, 22 pt title, 17 pt leading, where it
#:   was 6.7 pt under an 11.5 pt "title"), so interior page 1 — and only page 1
#:   — moved on top of CARD-144's eleven;
#: * ``book_baseline_card146.json`` — CARD-146 carries CARD-144's frame onto the
#:   **two-up** page, which composes its own drawings and so had never drawn
#:   one, so interior page 3 — and only page 3 — moved on top of CARD-149's;
#: * ``book_baseline_card147.json`` — CARD-147 makes a black-and-white interior
#:   the book's own stored fact and the default, so every page is now written
#:   ``"L"`` with ``ColorSpace /DeviceGray``. **No page's digest moved** — the
#:   luma plane survives the colour-space change exactly, and ``pdf_pages``
#:   normalises a page to RGB before digesting it anyway — so this is the first
#:   recording in the chain whose ``changed_pages`` is empty and whose whole
#:   change is ``interior_bytes``: 2,273,541 where CARD-146 recorded 2,680,175.
#:   Its ``why_a_new_baseline`` carries the arithmetic, and its
#:   ``interior_colorspace`` carries the fact that each page entry's ``mode``
#:   field, still ``"RGB"``, is the reader's normalisation and not the file's
#:   declaration.
#:
#: * ``book_baseline_card167.json`` — CARD-167 retitles the guide page "How to
#:   Solve Nonograms" and adds its worked example, so interior page 1 — and
#:   only page 1 — moved on top of CARD-147's eleven, with ``interior_bytes``;
#:   it also records ``colour_interior_bytes`` for the colour export of the
#:   same book, which ``tests/test_book_pdf_ink_mode.py`` reads.
#:
#: * ``book_baseline_card184.json`` — CARD-184 sets the answer key's level
#:   heading and captions at CON-020's 10 pt (42 px) instead of 3.5 mm (41 px,
#:   9.84 pt), so interior pages 9, 10 and 11 — the answer pages, and only
#:   those — moved on top of CARD-167's eleven, with ``interior_bytes`` and
#:   ``colour_interior_bytes``.
#:
#: * ``book_baseline_card198.json`` — CARD-198 replaces the packed 6-up/4-up
#:   answer key with one full solved page per puzzle: the interior grows
#:   from eleven pages to **twelve** (the baseline book's three levels each
#:   held exactly one puzzle, so the old packed key already took one page
#:   per level — CARD-198 adds a fourth answer page only because puzzles 2
#:   and 3 share one *puzzle* page but still each get their own *answer*
#:   page). Pages 1-8 (guide through the SOLUTIONS divider) are
#:   byte-identical to CARD-184's recording (AC-9); pages 9-12 are new.
#:   ``font_dependent_pages`` is unchanged: the four machine-lettered pages
#:   are still 1, 2, 4 and 6, none of them in the answer section.
#:
#: * ``book_baseline_card202.json`` — CARD-202 packs an answer small enough
#:   (width<=15, height<=20) 2-or-4 to a page instead of giving it CARD-198's
#:   full page: of this book's four puzzles, Duck and Owl (10x10, Easy) and
#:   Tree (15x15, Medium) all qualify, Snowflake (30x30, Hard) does not. Duck
#:   and Owl pack onto one 2-up page (their run ends at two, the book's own
#:   count, not a leftover of four); Tree, alone in its level, packs onto its
#:   own 2-up page with one slot filled; Snowflake still gets CARD-198's full
#:   page. Interior pages 9-12 (four answer pages) become 9-11 (three) — the
#:   interior shrinks from twelve pages to **eleven**. Pages 1-8 are
#:   byte-identical to CARD-198's recording (G-1, G-2); `font_dependent_pages`
#:   is unchanged (1, 2, 4, 6, 8 — the answer section is never machine-lettered).
#:
#: * ``book_baseline_card201.json`` — CARD-201 grows the guide from one page
#:   to two (the full "how to solve" tutorial, FR-041's own deferred clause):
#:   every page from the first puzzle/divider page onward (interior page 1
#:   onward in CARD-202's eleven-page recording above) moves one page later,
#:   so the interior grows from CARD-202's eleven pages to **twelve** — not
#:   thirteen: CARD-201 only shifts *where* the puzzle/divider/answer section
#:   starts, it does not touch CARD-202's own packing decision, which still
#:   holds Duck+Owl and Tree to two packed answer pages and Snowflake to one
#:   full page (three answer pages, now at interior pages 10-12 instead of
#:   9-11). This is the one recording in the chain whose ``changed_pages``
#:   cannot be "the pages that moved" in the byte sense every predecessor's
#:   can: a page inserted before the puzzle section flips every later page's
#:   parity (recto/verso), and COMP-007 mirrors a book page's margins by
#:   parity (ADR-0036), so no later page is byte-identical to its pre-card
#:   self even though its *content* — which puzzle, which tier, which clues,
#:   which fill — is unchanged (G-2). See ``tests/test_book_pdf_memory.py``'s
#:   ``TestBookPdfMemory_EveryPageAfterTheGuideIsByteIdenticalShiftedByOne``
#:   for how AC-6 is verified instead: by content, cropped to each page's own
#:   ink (position-invariant to the parity-mirrored margin), not by raw bytes.
#:   ``font_dependent_pages`` grows from five pages to six: both guide pages
#:   are machine-lettered now, not only the first.
#:
#: * ``book_baseline_card200.json`` — CARD-200 inserts a 1-page table of
#:   contents (this book's four puzzles fit Book 1's own TOC capacity with
#:   room to spare) between the guide and the puzzle section, and adds a
#:   bottom-outer-corner page-number folio to every interior page but the
#:   cover. Every page's digest moves: pages 1-2 gain only the new folio,
#:   page 3 is entirely new (the TOC), and every page from 4 onward both
#:   shifts by the TOC's one page (another parity flip, the same kind
#:   CARD-201's own recording already explains) and gains the new folio.
#:   The interior grows from CARD-201's twelve pages to **thirteen**.
#:   ``font_dependent_pages`` grows from six pages to seven: the TOC page
#:   (3) is machine-lettered too (its title and every entry set through
#:   ``_guide_face``, the same Arial-or-fallback path the guide and divider
#:   pages already use) — the folio itself is not font-dependent (it reuses
#:   ``_band_font``, the packaged DejaVu Sans, exactly as the answer caption
#:   does). See ``tests/test_book_pdf_memory.py``'s
#:   ``TestBookPdfMemory_ContentAboveTheFooterBandIsUnchanged`` for the
#:   narrower "nothing but the footer band moved" claim, verified by
#:   content rather than by this whole-page digest.
#:
#: * ``book_baseline_card203.json`` — CARD-203 right-aligns the solved-page
#:   caption with ``placement.drawing_right`` (anchor ``"rm"`` instead of
#:   ``"mm"``) and moves it to a fixed ``ANSWER_TILE_GAP_MM`` (2.0 mm) gap
#:   above ``placement.drawing_bottom`` instead of centred across the whole
#:   bottom slack, in ``_draw_solved_slot``'s step 8 — the one shared
#:   implementation CARD-202 already extracted for both a full solved page
#:   (``solved_puzzle_page``) and a packed small-answer slot
#:   (``_packed_answer_page``), so this one change reaches both without a
#:   second edit. Only the three pages that actually draw a caption on this
#:   book move: 11 (Duck+Owl, packed), 12 (Tree, packed alone) and 13
#:   (Snowflake, full page). Pages 1-10 — both guide pages, the TOC, the
#:   three level dividers, the two-up page, the two single puzzle pages and
#:   the SOLUTIONS divider, none of which ever draws a caption — are
#:   byte-identical to CARD-200's own recording. The interior still holds
#:   **thirteen** pages; only ink on the three answer pages moved, not the
#:   page count.
#:
#: * ``book_baseline_card204.json`` — CARD-204 reverses FR-032's centred
#:   horizontal placement to right-aligned, mirrored by parity (owner
#:   reading (b)), and reserves/draws a 2x2cm placeholder QR icon on
#:   puzzle pages wherever the new geometry leaves room for one. Measured
#:   directly (git-stash diff of the renderer, and a page-by-page digest
#:   comparison against CARD-200's recording): pages 5, 7 and 9 (the
#:   two-up page and the book's two single-puzzle pages) move, for both
#:   reasons. Pages 11 and 12 (CARD-202's packed answer pages) do not: a
#:   tile-local centring formula FR-032's page-wide clause never covered.
#:   Page 13 (Snowflake's full answer page) does not move either, but as a
#:   coincidence of this one puzzle's own page-fit-bound geometry (its own
#:   spare is exactly 0, where the old and new formulas agree) rather than
#:   a structural exemption. Pages 1 and 2 (the guide) move too, by a
#:   small, documented, incidental sub-pixel rounding scatter: their own
#:   worked-example diagrams reuse ``compute_layout``'s placed-page branch
#:   for cell/rule consistency (ADR-0036/R2), and that branch's
#:   per-boundary rounding depends on the absolute anchor's own fractional
#:   part, which this card's formula changes even though the diagrams
#:   themselves are cropped and pasted at a fixed, card-independent
#:   position — flagged for the owner/architect in CARD-204's own Worktree
#:   notes, not treated as this card's to eliminate (G-3 forbids these
#:   helpers their own placement arithmetic). See
#:   ``tests/test_book_pdf_memory.py``'s
#:   ``TestBookPdfMemory_NonDrawingPagesAreByteIdentical`` for the test
#:   that verifies all of this directly.
#:
#: * ``book_baseline_card204.json`` (**re-recorded in place for CARD-204
#:   Fix 1**, same filename — a revision of this card's own fixture, not a
#:   new card superseding it): the owner's "reserve folio room" decision.
#:   Reading (b)'s flush formula pinned the two-up page's lower slot's
#:   drawing exactly to the usable area's outer margin, with zero slack —
#:   combined with that slot's own always-zero vertical slack, CARD-200's
#:   page-number folio was permanently omitted from every two-up page, both
#:   parities (see CARD-204's own Worktree notes, "Implementation,
#:   2026-10-10", exception 2). Fix 1 has ``book_pdf_generator.puzzle_pages``
#:   pass ``compute_pair_layout`` this exact page's own folio text width
#:   (``_folio_reserve_px``), which pulls the lower slot's drawing back from
#:   the flush edge by that many pixels (``export/layout.py``'s
#:   ``_slot_layout``) — just enough, and no more, for the folio's own
#:   horizontal-clearance check to pass. Measured directly (page-by-page
#:   digest comparison against this same file's own pre-Fix-1 recording):
#:   only interior page 5 (the two-up page) moves — its lower slot's
#:   drawing/QR-icon geometry shifts by the reserve and its folio now prints
#:   "5" instead of being omitted. No other page moves: pages 7 and 9
#:   (single-puzzle pages) are placed by ``compute_layout``, which this fix
#:   does not touch at all, and pages 11-13 (answer pages) never call
#:   ``compute_pair_layout``. ``interior_bytes`` moves from 3439483 to
#:   3439779 (+296 bytes — the new folio glyph's own ink). ``font_fingerprint``
#:   and ``font_dependent_pages`` are unchanged (Fix 1 touches no
#:   machine-lettered page).
#:
#: * ``book_baseline_card204.json`` (**re-recorded in place again for
#:   CARD-204 Fix 2**, same filename): the cycle-1 review's F-1 finding —
#:   Fix 1's ``folio_reserve_px`` was *this exact page's own* measured folio
#:   width, which made ``compute_pair_layout``'s accept/refuse verdict and
#:   shared cell depend on the page number's own digit count, not on the two
#:   puzzles' geometry (INV-010). Fix 2 has ``puzzle_pages``/
#:   ``puzzle_section`` derive **one** reserve for the whole book (or the
#:   whole standalone call), sized for the worst-case digit count that book
#:   could ever need, and pass the same value to every two-up page — so the
#:   reserve can no longer tell two pages of the same book apart. On this
#:   four-puzzle baseline book that worst case is a 2-digit page number
#:   (``max_page_number`` bound 10), one digit wider than Fix 1's own
#:   page-5-specific 1-digit measurement, so only interior page 5 moves
#:   again: its lower slot's reserved gap widens from 27 px to 54 px, with
#:   the pair's own 7.5 mm shared cell unchanged (height, not width, is this
#:   pair's own binding constraint — confirmed unaffected, not merely
#:   assumed). ``interior_bytes`` moves from 3439779 to 3440674 (+895 bytes
#:   — the wider reserve shifts the lower slot's own drawing/QR-icon ink,
#:   nothing added or removed). ``font_fingerprint`` and
#:   ``font_dependent_pages`` are unchanged (Fix 2 touches no
#:   machine-lettered page either).
#:
#: * ``book_baseline_card204.json`` (**re-recorded in place a third time for
#:   CARD-204 Fix 3**, same filename): the cycle-2 review's F-5 finding —
#:   Fix 2 narrowed Fix 1's bug from per-page to per-book-scale, but did not
#:   remove it: the same pair of puzzles still paired or refused differently
#:   depending on the book's own total page-number digit count, still a
#:   non-geometric quantity flipping INV-010's verdict (``meta/architecture/
#:   domain/aggregates.yml``'s own statement is geometry-only). Fix 3 removes
#:   the ``folio_reserve_px``/``outer_reserve_px`` mechanism from
#:   ``compute_pair_layout``/``_slot_layout`` entirely: the pairing/cell-size
#:   decision is geometry-only again, and the folio is decided afterward,
#:   cosmetically, from whatever natural slack the committed geometry leaves
#:   (``_draw_folio``'s own pre-existing "omit rather than collide" check,
#:   unchanged). Measured directly (page-by-page digest comparison against
#:   Fix 2's own recording): only interior page 5 (the two-up page) moves,
#:   back to its pre-Fix-1 ink — the lower slot's drawing/QR-icon geometry
#:   returns to the plain flush position and its folio is omitted again
#:   (this baseline pair's own natural spare at that corner is zero).
#:   ``interior_bytes`` moves from 3440674 back to 3439483 (-1191 bytes, the
#:   folio glyph's own ink removed). ``font_fingerprint`` and
#:   ``font_dependent_pages`` are unchanged (Fix 3 touches no machine-lettered
#:   page either).
#:
#: * ``book_baseline_card204.json`` (**re-recorded in place a fourth time for
#:   CARD-204 Fix 4**, same filename): the owner's decision, 2026-10-12,
#:   "fixed universal reserve" — Fix 3's own INV-010-pure removal of the
#:   reserve mechanism (correct in isolation) silently reintroduced the
#:   folio loss on *every* two-up page, not just a tight-fit one (cycle-3
#:   review F-7), which is the exact regression this card's owner-confirmed
#:   "reserve folio room" decision existed to prevent. Fix 4 restores
#:   ``folio_reserve_px``/``outer_reserve_px`` to ``compute_pair_layout``/
#:   ``_slot_layout``, but every production call now feeds it a single
#:   FIXED value (``book_pdf_generator._folio_reserve_px(dpi)`` — a function
#:   of the font and the DPI alone, computed once from the widest digit
#:   this font draws times a 4-digit ceiling, 108 px at 300 DPI — never a
#:   page number or any book content), so the pairing/cell-size verdict
#:   stays "this pair's own geometry plus one constant," structurally
#:   incapable of the cycle-1/cycle-2 coupling. On this baseline book's own
#:   Duck+Owl pair, the committed 7.5 mm shared cell is unchanged (height,
#:   not width, is this pair's own binding constraint, confirmed not
#:   assumed) — only the lower slot's drawing/QR-icon geometry shifts
#:   108 px toward the gutter, buying back enough room for CARD-200's
#:   folio to draw again. Measured directly (page-by-page digest
#:   comparison against Fix 3's own recording): only interior page 5 (the
#:   two-up page) moves. ``interior_bytes`` moves from 3439483 to 3440084
#:   (+601 bytes — the folio glyph's own ink, drawn again). ``font_fingerprint``
#:   and ``font_dependent_pages`` are unchanged (Fix 4 touches no
#:   machine-lettered page either).
#:
#: * ``book_baseline_card204.json`` (**re-recorded in place a fifth time for
#:   CARD-204 Fix 7**, same filename): the merge gate, and the one recording
#:   in this card's own chain whose cause is **not this card**. CARD-203 (the
#:   bullet above this card's own first one) merged to main *after* this
#:   branch was cut, so every earlier CARD-204 recording was taken on a tree
#:   without it. On the merged tree its caption move lands on this book's
#:   three caption-drawing pages: interior pages 11, 12 (CARD-202's packed
#:   answer pages) and 13 (Snowflake's full one) move, and move to exactly
#:   the pixels ``book_baseline_card203.json`` already recorded for them —
#:   asserted, not assumed, by ``tests/test_book_pdf_memory.py``'s
#:   ``TestBookPdfMemory_NonDrawingPagesAreByteIdentical``, which compares
#:   those three against CARD-203's fixture and the other ten against
#:   CARD-200's. Pages 1-10 are byte-identical to Fix 4's recording.
#:   ``interior_bytes`` moves from 3440084 to 3441912 (+1828 bytes — the
#:   identical delta CARD-203's own recording added over CARD-200's on this
#:   same book, 3420073 -> 3421901, measured on main without any of this
#:   card's changes). **Fix 7's own production change moves no page of this
#:   book**: ``export/layout.py``'s new ``caption_slot`` clamps a caption's
#:   right-aligned anchor off the trim margin, and fires only for a caption
#:   wider than its own grid, which none of this book's four (321-459 px
#:   against drawings of 1328 px and up) is — its evidence is
#:   ``tests/test_book_solved_page.py``'s
#:   ``TestBookSolvedPage_CaptionWiderThanItsGridStaysInsideTheMargin``,
#:   which prints the over-wide caption this corpus does not contain.
#:   ``font_fingerprint`` and ``font_dependent_pages`` are unchanged (no
#:   answer page is machine-lettered).
#:
#: * ``book_baseline_card205.json`` — CARD-205 replaces the table of
#:   contents' per-puzzle listing with a structural one: one "How to Solve
#:   Nonograms" row, a heading plus a ``Puzzles N–M`` range row per
#:   non-empty level, and one "Solutions" row, each numbered row carrying
#:   leader dots across to its page number. A **new file**, not a
#:   re-recording of CARD-204's: this is a different card's deliberate ink
#:   change, which the chain's own rule (every baseline's ``warning``
#:   field) gives its own card number. Measured directly (a page-by-page
#:   digest comparison against CARD-204's recording): interior page 3, the
#:   TOC, is the **only** page that moves — the other twelve are
#:   byte-identical, which is the evidence that a card touching
#:   ``create_toc_page`` and the TOC's own entry count reached no other
#:   page kind. ``interior_bytes`` moves from 3441912 to 3491813 (+49901 —
#:   the leader-dot runs carry more high-frequency ink than CARD-200's four
#:   plain caption rows did, so the page's own JPEG grows even though it
#:   holds fewer words). ``font_fingerprint`` and ``font_dependent_pages``
#:   are unchanged: page 3 is lettered in exactly the faces and sizes
#:   CARD-200 gave it.
#:
#:   **Re-recorded in place once, for this same card's Fix 1** (owner
#:   decision 2026-10-14): ``TOC_GROUP_GAP_PT`` sets extra white
#:   above each level heading, the blank line the owner's own sample shows
#:   between the groups — drawn as a fixed addition to the pen's ``y``,
#:   not as blank ``TocEntry`` rows, so the row count AC-1 pins and
#:   ``_toc_entries_per_page``'s uniform division are untouched. Same card,
#:   same page, same deliberate ink change carried one step further, so it
#:   stays this one file rather than becoming a sixteenth. Measured the same
#:   way (a page-by-page digest comparison against the pre-Fix-1 recording):
#:   page 3 is again the **only** page that moves, and ``interior_bytes``
#:   moves from 3491813 to 3504840 (+13027 — three of the eight rows shift
#:   down the page). The page count is still thirteen: the gaps are white
#:   inside a TOC that is one page on every trim KDP admits.
#:
#:   **And re-recorded in place a second time, for the same card's Fix 2**
#:   (the owner's second decision of 2026-10-14): ``Solutions`` opens the
#:   last group and is set off like a heading, so a three-level book now
#:   takes **four** group gaps rather than three — and four at Fix 1's
#:   10 pt would have left the shortest storable trim (10.00 cm) 31 px under
#:   its last row against the 49 the folio needs, un-numbering the one page
#:   that must carry a number (G-1). ``TOC_GROUP_GAP_PT`` is therefore
#:   **8.5 pt**, measured as the largest separation every storable trim can
#:   carry (59 px of headroom at the worst case). Both changes land on the
#:   same page: the three existing gaps shrink from 42 px to 35 while a
#:   fourth appears above ``Solutions``, so the list ends 14 px *lower*
#:   than it did (worst-case headroom 73 px -> 59) and all four of its
#:   lower rows sit at a new y. ``interior_bytes`` moves from 3504840 to
#:   **3498430** — down 6410, where Fix 1's own shift moved it up: the
#:   direction is the JPEG encoder's, not a measure of how much ink the
#:   page holds, and it is recorded because it is what the file does, not
#:   because it was predicted. Measured the same way, against Fix 1's own
#:   recording: page 3 is once more the **only** page that moves, and the
#:   page count is still thirteen.
#:
#:   **This book's page count does not change** (still thirteen): its four
#:   puzzles already fitted a one-page TOC under the old rule. A *large*
#:   book's does — see :data:`CORPUS_PAGE_COUNT` below, which falls from
#:   310 to 307.
#:
#: * ``book_baseline_card221.json`` — CARD-221 letters every reader-facing
#:   interior face in the **packaged** DejaVu Sans instead of the host's
#:   Arial, so that a book's page count (and therefore its printed KDP
#:   gutter band) is the same on the owner's Mac and on the deployed Linux
#:   panel. Exactly the seven pages that were lettered through
#:   ``_guide_face`` move — 1 and 2 (the guide), 3 (the TOC), 4, 6, 8 (the
#:   level dividers) and 10 (SOLUTIONS) — and the other six are
#:   byte-identical to CARD-205's digests, measured page by page before the
#:   file was written. ``interior_bytes`` 3498430 -> 3464123.
#:   ``font_dependent_pages`` becomes **empty**, and the
#:   ``font_fingerprint``/``MACHINE_FACE_SIZES`` machinery that went with it
#:   is removed from this module — see this module's own docstring for the
#:   measurement that retires it.
#:
#:   **Re-recorded in place once, for that card's own fix cycle 1**, after
#:   the owner ruled (2026-10-14) on the two consequences the packaged
#:   face's extra width had: the Book 1 guide page 2 had dropped a whole
#:   fallback level over 4 px of overflow, and the 10.00 cm trim's TOC
#:   folio was 2 px short. Neither was settled by accepting the loss — the
#:   guide page drops the difficulty box's three sentences and its rule
#:   (234 px, so every other line comes back; CARD-229 moves that legend
#:   into the guide's key strip) and ``TOC_GROUP_GAP_PT`` moves 8.5 -> 8.0
#:   pt (6 px clear of the folio on every height KDP admits, which is the
#:   owner's own rule re-measured on this face). Pages 2 and 3 move again
#:   and nothing else does; both strict ``xfail`` markers that carried the
#:   blocks are converted back to ordinary passing tests.
#:
#: All sixteen files carry the reasoning; this constant names the current one
#: (sixteen since CARD-221's own recording joined the fifteen CARD-205 had
#: brought the chain to; the stale counts this line used to carry,
#: "thirteen" and "twelve", were both left behind by earlier cards).
BASELINE_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "book_baseline_card221.json"

#: How many pages the baseline book's interior holds, asserted by the tests
#: that use it so the corpus cannot silently shrink (CLAUDE.md). Eleven until
#: CARD-198 took the packed answer key (three pages, one per level) to one
#: full solved page per puzzle (twelve); CARD-202 packed Duck+Owl and Tree
#: back onto two pages instead of three, back down to eleven; CARD-201 then
#: grew the guide from one page to two, back up to twelve; CARD-200 then
#: inserts a 1-page table of contents (this book's four puzzles fit Book 1's
#: own trim's TOC capacity with room to spare) immediately after the guide,
#: up to **thirteen**.
BASELINE_PAGE_COUNT = 13

#: How many puzzles the large corpus holds, and the interior that follows:
#: 2 guide (CARD-201) + **1** TOC page + 3 level dividers + 150 puzzle pages
#: + SOLUTIONS + 150 answer pages (CARD-198: one per puzzle, where the
#: packed key took 27).
#:
#: The TOC term was 4 until CARD-205 (CARD-200 listed one row per puzzle:
#: 150 entries at Book 1's own ~43-entries-per-page capacity). CARD-205's
#: structural list is eight rows for this three-level corpus — the guide,
#: three headings with their ranges, the solutions — which is one page on
#: any trim, so this interior is three pages shorter than it was. Still
#: measured off ``book_pdf_generator``'s own
#: ``structural_toc_entry_count``/``_toc_entries_per_page`` rather than
#: guessed, and still asserted against the live page plan by the tests that
#: use it.
CORPUS_PUZZLE_COUNT = 150
CORPUS_TOC_PAGE_COUNT = 1
CORPUS_PAGE_COUNT = (
    2 + CORPUS_TOC_PAGE_COUNT + 3 + CORPUS_PUZZLE_COUNT + 1 + CORPUS_PUZZLE_COUNT
)


def _cm(millimetres: float) -> str:
    """A trim or margin as the ``books`` table stores it: centimetres, 2 dp."""
    return f"{millimetres / 10:.2f}"


def corpus_book(book_id: str = "card-145") -> Book:
    """A book on CON-018's Book 1 profile, with no custom puzzle titles.

    The same stored print specification both corpora are exported on, so a
    page's geometry is the book's and not a default that happened to agree
    with it.
    """
    return Book(
        book_id=book_id,
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-145's memory tests export.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=_cm(BOOK1_WIDTH_MM),
        trim_height_cm=_cm(BOOK1_HEIGHT_MM),
        gutter_margin_cm=_cm(GUTTER_MM),
        outside_margin_cm=_cm(OUTSIDE_MM),
    )


def _gutter_grid(columns: int, rows: int, depth: int) -> List[List[bool]]:
    """A grid whose row **and** column clues are exactly ``depth`` entries deep.

    The same construction ``tests/test_book_pdf.py`` uses: every other cell
    filled along both axes, stopped after ``depth`` runs, so a line that
    carries any ink carries ``depth`` isolated single cells.
    """
    limit = 2 * depth - 1
    if limit > min(columns, rows):
        raise ValueError(f"a {columns}x{rows} grid cannot carry {depth}-deep clues")
    return [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(columns)]
        for y in range(rows)
    ]


def puzzle(
    puzzle_id: str,
    columns: int,
    rows: int,
    depth: int,
    tier: str,
    name: str,
) -> Dict[str, Any]:
    """One book puzzle, in the shape the review service hands the generator."""
    grid = _gutter_grid(columns, rows, depth)
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": columns,
        "height": rows,
        "puzzle_name": name,
        "difficulty_tier": tier,
    }


def baseline_puzzles() -> List[Dict[str, Any]]:
    """Four puzzles whose interior holds one of every page kind.

    Puzzle 1 is a 30x30 Hard: far too large to pair, so it prints alone.
    Puzzles 2 and 3 are 10x10 Easies side by side, which is the one
    arrangement the pairing walk turns into a two-up page (FR-040). Puzzle 4
    is a 15x15 Medium, alone again because its neighbours' tiers differ.

    **They are deliberately not in print order.** Since CARD-128 the book
    prints grouped easy, then medium, then hard (INV-009), so this list — hard
    first — exercises the grouping as well as the page kinds: the interior
    runs guide, "Easy", the two-up page, "Medium", the 15x15, "Hard", the
    30x30, SOLUTIONS, and the answer section. Since CARD-202, Duck and Owl
    (10x10) and Tree (15x15) all qualify for packing (width<=15, height<=20)
    while Snowflake (30x30) does not: Duck+Owl share one 2-up packed page,
    Tree packs onto its own 2-up page alone (its level has no other qualifying
    answer to join it), and Snowflake still gets CARD-198's full page — three
    answer pages, not four. Eleven pages in all, three of them level dividers.

    Four puzzles behind the SOLUTIONS divider, now three answer pages,
    is also no longer "the puzzle section's page count minus the two-up
    pairing, plus one": puzzles 2 and 3 (Duck, Owl) share both their *puzzle*
    page (FR-040) and, since CARD-202, their packed *answer* page — the one
    link between the two sections this book happens to exercise, though the
    two pairings are decided independently (INV-010's same-tier-neighbour
    rule for puzzle pages, CARD-202's qualifies-and-same-level rule for
    answer pages) and are not guaranteed to agree in general.
    """
    return [
        puzzle("card145-1", 30, 30, 9, "hard", "Snowflake"),
        puzzle("card145-2", 10, 10, 3, "easy", "Duck"),
        puzzle("card145-3", 10, 10, 3, "easy", "Owl"),
        puzzle("card145-4", 15, 15, 4, "medium", "Tree"),
    ]


def corpus_puzzles(
    count: int = CORPUS_PUZZLE_COUNT, seed: int = 145
) -> List[Dict[str, Any]]:
    """A seeded corpus of ``count`` puzzles, grouped by tier like a real book.

    Sizes are drawn from a seeded ``random.Random`` so the corpus is the same
    on every run and on every machine, and they are 18x18 or 20x20 with 6-deep
    clues — large enough that no two of them share a page however their tiers
    fall, so the interior's length is the puzzle count and not a verdict of the
    pairing walk. Tiers run Easy, then Medium, then Hard, which is the order
    INV-009 groups a book in and, since CARD-128, the order that gives the
    puzzle section three divider pages.
    """
    if count < 3:
        raise ValueError(f"the corpus is grouped into three tiers, not {count}")
    rng = random.Random(seed)
    tiers = ["easy", "medium", "hard"]
    puzzles: List[Dict[str, Any]] = []
    for index in range(count):
        tier = tiers[index * len(tiers) // count]
        side = rng.choice((18, 20))
        puzzles.append(
            puzzle(f"card145-corpus-{index + 1}", side, side, 6, tier, f"Picture {index + 1}")
        )
    return puzzles


# --------------------------------------------------------------------------
# Per-page evidence
# --------------------------------------------------------------------------


def page_digest(page: Image.Image) -> Dict[str, Any]:
    """One page's identity: its size, its mode and its raw pixels' sha256.

    Digests rather than images, because a 2550x3300 RGB page is 25.2 MB and a
    fixture is not a place to keep eight of them. ``Image.tobytes`` is the
    decoded bitmap itself, so two pages with the same digest are the same page
    to the pixel — no tolerance, unlike ``pdf_pages.same_page``, which allows
    JPEG noise and would hide exactly the change this evidence exists to catch.
    """
    return {
        "size": list(page.size),
        "mode": page.mode,
        "sha256": hashlib.sha256(page.tobytes()).hexdigest(),
    }


def page_digests(pages: Sequence[Image.Image]) -> List[Dict[str, Any]]:
    """:func:`page_digest` for every page, in page order."""
    return [page_digest(page) for page in pages]


# CARD-221 removed ``MACHINE_FACE_SIZES`` and ``font_fingerprint()`` from this
# module. They existed because the guide pages, the dividers and the TOC were
# lettered in the **host's** Arial (CARD-146/CARD-147 built the mechanism;
# CARD-149 and CARD-200 re-derived the tuple as the sizes it transcribed
# moved), so a fixture's recorded pixels could only be compared on a machine
# whose face matched: the fingerprint was that face's digest at each size the
# pages asked for, and ``font_dependent_pages`` named the pages a mismatched
# machine skipped.
#
# The condition is measurably gone, not argued away: ``_guide_face`` returns
# the packaged DejaVu Sans, so every interior page is lettered from this
# repository's own package data, and
# ``tests/test_book_interior_face.py``'s
# ``TestBookInterior_GeometryIsIdenticalWithAndWithoutHostFonts`` exports this
# book with the host's Arial available and again with ``ImageFont.truetype``
# refusing every host path and finds every page's digest, the page count and
# the chosen gutter band identical. ``book_baseline_card221.json``'s
# ``font_dependent_pages`` is therefore empty, and nothing in the test tree
# gates on a face any more (``tests/test_book_toc.py``'s own
# ``_lettered_as_recorded`` went with it).
#
# Two things this removal deliberately does NOT claim. (1) The **generated
# title cover** still reads the host's Arial at 72 px
# (``create_cover_page``): the cover is a separate file, INV-013 keeps it out
# of the interior, no baseline digests it, and this tuple never covered its
# size — recorded in CARD-221's notes as work outside that card, not gated
# here. (2) A puzzle page's clue digits come from Pillow's own embedded face
# rather than from this repository; that was always on the
# machine-independent side of this line (every predecessor fixture's own
# note), and it is a dependency's package data, not the host's.


def load_baseline() -> Dict[str, Any]:
    """The recorded merge-base evidence, as it sits in the fixture file."""
    with BASELINE_FIXTURE.open(encoding="utf-8") as handle:
        return json.load(handle)


def export_of(generator, puzzles: Sequence[Dict[str, Any]]) -> bytes:
    """``generator``'s interior PDF for ``puzzles``, as bytes.

    One call, so the recorder and the test that checks against it cannot
    differ in how they asked for the file.
    """
    written: BytesIO = generator.export_interior(list(puzzles))
    return written.getvalue()


# --------------------------------------------------------------------------
# The same book, exported inside a child process that is under a memory cap
# --------------------------------------------------------------------------
#
# AC-2 asks for "a 150-page book exports successfully under a memory cap that
# the current code fails". Both halves of that sentence want a *process* that
# a cap can kill, which is what these three shapes are for: a fresh
# interpreter installs the cap before it imports anything, then asks for one
# of them and reports what it cost. ``tests/test_book_pdf_memory.py`` runs the
# children and owns the cap's derivation; what lives here is only the work
# they do, so the capped run and the in-process run export the same book
# through the same two calls.

#: Import the stack, build one page, drop it, report. The **floor** a capped
#: child cannot go below on any platform: interpreter + PIL + numpy + the
#: corpus book + a single page bitmap. It is measured so a cap can be shown to
#: have room over the platform's own footprint rather than over a guess.
BASELINE_SHAPE = "baseline"

#: ``export_interior`` — the shape this card ships: no page survives the call
#: that builds the next one.
STREAMING_SHAPE = "stream"

#: ``interior_pages`` into a list, then written — the shape this card removed
#: from the export path and which :meth:`BookPDFGenerator.interior_pages` can
#: still produce for a caller that asks for it. This is "the current code" of
#: AC-2's second half, run rather than reasoned about.
MATERIALISED_SHAPE = "list"


def resident_bytes() -> int:
    """This process's high-water resident set, in bytes.

    ``ru_maxrss`` is bytes on Darwin and kibibytes on Linux — the one
    normalisation every reader of that field has to do. Imported inside the
    function because :mod:`resource` is POSIX-only and this module is imported
    by tests that have nothing to do with process memory.

    This is RSS, and ``tests/test_book_pdf_memory.py`` is explicit that RSS is
    not a number a test may *assert a shape on*. It is used only where it is
    the right instrument: as the quantity a process-level cap is enforced
    against, with orders of magnitude between the two outcomes it separates.
    """
    import resource

    used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return used if sys.platform == "darwin" else used * 1024


def capped_export_report(shape: str) -> Dict[str, Any]:
    """Do ``shape``'s work in **this** process and report what it cost.

    Called in a child interpreter that has already installed a memory cap, so
    it deliberately catches nothing: a shape that cannot fit the cap must die
    or raise :class:`MemoryError` at the caller, which is the whole point of
    running it here rather than in the test process.

    The page count in the report is read back **out of the written PDF's page
    tree**, never taken from the page plan — a memory test must not fake a
    page count, and the capped run is the one most tempted to.
    """
    from nonogram.admin.book_pdf_generator import BookPDFGenerator
    from tests.helpers.pdf_pages import pdf_page_count

    imported = resident_bytes()
    generator = BookPDFGenerator(corpus_book())

    if shape == BASELINE_SHAPE:
        page = generator.create_guide_page(4, 2, 1, 1)
        page_bytes = page.width * page.height * len(page.mode)
        del page
        return {
            "shape": shape,
            "outcome": "drawn",
            "imported": imported,
            "page_bytes": page_bytes,
            "resident": resident_bytes(),
        }

    puzzles = corpus_puzzles()
    started = time.perf_counter()
    if shape == STREAMING_SHAPE:
        written = generator.export_interior(puzzles).getvalue()
    elif shape == MATERIALISED_SHAPE:
        pages = generator.interior_pages(puzzles)  # the shape this card removed
        # CARD-147: written in the book's own interior colour space, so the
        # two shapes under the cap write the same file and differ only in when
        # they release a page.
        written = generator._write_pdf(
            iter(pages), len(pages), mode=generator.interior_bitmap_mode
        ).getvalue()
        del pages
    else:
        raise ValueError(f"unknown export shape: {shape!r}")

    return {
        "shape": shape,
        "outcome": "written",
        "imported": imported,
        "page_count": pdf_page_count(written),
        "file_bytes": len(written),
        "seconds": time.perf_counter() - started,
        "resident": resident_bytes(),
    }
