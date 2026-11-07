"""The owner's uploaded divider pages: the four slots, and the one fitting rule (CARD-311).

A book's interior opens each non-empty level ("Easy", "Medium", "Hard") and its
answer key ("SOLUTIONS") with a divider page (TERM-031). The owner supplies
those pages as pictures; the interior prints the picture in place of the page
it would otherwise draw. This module is the part of that which has no database
and no generator in it: **which slots exist**, and **what an upload must be to
be accepted and how it is fitted onto a page**.

**The store.** An upload is kept in the ``book_divider_images`` table
(migration 019), one row per ``(book, slot)``, as a PNG re-encoded here. A
database row and not a file because the panel runs on a host whose disk is
ephemeral: a directory survives neither a redeploy nor a temp purge, and the
cover's temp-directory-plus-session-key arrangement is exactly the weakness
CARD-311's AC-5 is written against. A row has no client filename (the key is
the book id and a slot from the closed set below) and no path to escape from,
so the cover's two path guards have nothing left to guard.

**What is stored is the owner's picture, upright and re-encoded, at its own
size** -- not a copy already cut to today's trim. The trim lives on the book
and can be changed after the upload; the fit is therefore made at export, from
the page the export is about to print (:func:`fit_to_page`), and an upload the
new trim no longer suits is *refused at that moment*, loudly, not stretched.

**The refusals** (AC-4), each naming which:

* not an image at all (:class:`NotAnImage`);
* the wrong shape for the page -- its aspect ratio differs from the page's by
  more than :data:`ASPECT_TOLERANCE` (:class:`WrongAspectRatio`). *Refused*,
  not letterboxed or cropped: either would silently print something other than
  what the owner uploaded;
* too few pixels for the page at the book's resolution
  (:class:`BelowBookDpi`). *Refused*, never upscaled: an upscaled picture
  prints soft and says nothing about it.

**CON-020's 10 pt floor and an image.** The floor is checked on text the
generator sets, and an uploaded page sets none. The floor therefore cannot be
checked on it by this module and is *not claimed*: the lettering inside an
owner's picture is the owner's, exactly as it is on the cover, and the
declaration that makes the page a bitmap
(``book_pdf_generator._RASTER_DECLARATIONS``) says so. What *is* held is the
resolution: a page that is not below the book's DPI cannot be a smaller
picture blown up to fill the sheet.
"""

from __future__ import annotations

import io
from typing import Any, Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

from nonogram.difficulty import Tier

#: The slot of the page that opens the answer key (AC-292).
SOLUTIONS_SLOT = "solutions"

#: The four slots, in the order the interior prints them: the three levels by
#: their ADR-0031 tier value, then the answer key. Derived from :class:`Tier`
#: rather than written out, so a tier added tomorrow has a slot today.
DIVIDER_SLOTS: Tuple[str, ...] = tuple(tier.value for tier in Tier) + (SOLUTIONS_SLOT,)

#: How far an upload's width/height ratio may differ from the page's, as a
#: fraction of the page's. 1% is a few pixels on a 2550 px page: room for a
#: file exported with a rounded size, none for a square picture on a portrait
#: sheet.
ASPECT_TOLERANCE = 0.01

#: The largest upload accepted, in bytes (the cover form states the same 10 MB).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class DividerRefused(ValueError):
    """An upload was refused. ``str(error)`` is the message the owner reads."""


class NotAnImage(DividerRefused):
    """The upload could not be decoded as a picture."""


class WrongAspectRatio(DividerRefused):
    """The picture's shape is not the page's."""


class BelowBookDpi(DividerRefused):
    """The picture has too few pixels to fill the page at the book's DPI."""


class TooLarge(DividerRefused):
    """The upload is larger than :data:`MAX_UPLOAD_BYTES`."""


def slot_for_level(level: Tier) -> str:
    """The slot of the divider that opens ``level``."""
    return Tier(level).value


def slot_label(slot: str) -> str:
    """The word the drawn divider for ``slot`` prints: ``"Easy"``, ``"SOLUTIONS"``."""
    require_slot(slot)
    return slot.upper() if slot == SOLUTIONS_SLOT else Tier(slot).label


def require_slot(slot: Any) -> str:
    """``slot`` if it is one of :data:`DIVIDER_SLOTS`, else ``ValueError``.

    The closed set is what stands in for a filename: nothing the client sends
    reaches the store except through this.
    """
    if slot not in DIVIDER_SLOTS:
        raise ValueError(
            f"{slot!r} is not a divider slot; the slots are {', '.join(DIVIDER_SLOTS)}"
        )
    return slot


def _check_shape(
    width: int, height: int, page_width_px: int, page_height_px: int, dpi: int
) -> None:
    """Raise the refusal that names what is wrong with a ``width`` x ``height`` picture."""
    wanted = page_width_px / page_height_px
    have = width / height
    if abs(have - wanted) > ASPECT_TOLERANCE * wanted:
        raise WrongAspectRatio(
            f"the picture is {width} x {height} px (width/height {have:.3f}) but "
            f"this book's pages are {page_width_px} x {page_height_px} px at "
            f"{dpi} DPI (width/height {wanted:.3f}). Upload one in the page's shape."
        )
    if width < page_width_px or height < page_height_px:
        raise BelowBookDpi(
            f"the picture is {width} x {height} px, below the "
            f"{page_width_px} x {page_height_px} px this book's page needs at "
            f"{dpi} DPI. Upload a larger one; it is not enlarged."
        )


def accept_upload(
    stream: Any, page_width_px: int, page_height_px: int, dpi: int
) -> bytes:
    """Validate an uploaded file against the page and return the PNG to store.

    The picture is decoded, turned upright by its EXIF orientation (a phone
    photo is stored sideways with a rotate tag PNG does not carry), checked
    against the page (:func:`_check_shape`), and re-encoded as PNG: what is
    stored is bytes this function wrote, never the client's.

    Raises:
        TooLarge: more than :data:`MAX_UPLOAD_BYTES`.
        NotAnImage: not a decodable picture.
        WrongAspectRatio: the shape is not the page's.
        BelowBookDpi: too few pixels for the page.
    """
    raw = stream.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise TooLarge(
            f"the file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
        )
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise NotAnImage(
            f"the file is not an image this panel can read ({error.__class__.__name__})"
        ) from error
    image = ImageOps.exif_transpose(image).convert("RGB")
    _check_shape(image.width, image.height, page_width_px, page_height_px, dpi)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def fit_to_page(
    stored: bytes, page_width_px: int, page_height_px: int, dpi: int
) -> Image.Image:
    """The stored picture as an RGB page of exactly ``page_width_px`` x ``page_height_px``.

    Run at export, against the page that export prints: the shape and
    resolution checks of :func:`accept_upload` are made again, so a trim changed
    after the upload refuses here rather than printing a stretched page. The
    only resampling is a *reduction* by a factor within :data:`ASPECT_TOLERANCE`
    of uniform; the picture is never enlarged (:class:`BelowBookDpi` first).

    Raises:
        NotAnImage: the stored bytes are not a picture.
        WrongAspectRatio: the page is no longer the picture's shape.
        BelowBookDpi: the page now needs more pixels than the picture has.
    """
    try:
        with Image.open(io.BytesIO(stored)) as opened:
            image = opened.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise NotAnImage("the stored divider is not a readable image") from error
    _check_shape(image.width, image.height, page_width_px, page_height_px, dpi)
    if image.size != (page_width_px, page_height_px):
        image = image.resize((page_width_px, page_height_px), Image.Resampling.LANCZOS)
    return image

