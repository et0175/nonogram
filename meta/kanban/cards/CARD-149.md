# CARD-149: The guide page is legible at book size — its body is 6.7 pt today

**Status:** ready
**Priority:** P2
**Category:** bug
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** —
**Worktree:** —
**Source:** measured 2026-09-30 while drafting the guide page's text (docs/guides/how-to-solve-nonograms.md)
**Idea:** —
**Wave:** 27
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page_type.py, tests/fixtures/book_baseline_card149.json
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

`BookPDFGenerator.create_guide_page` (book_pdf_generator.py:1170-1175) sets its fonts in
**pixels** on a surface that renders at **300 DPI**:

    title_font = ImageFont.truetype(".../Arial.ttf", 48)
    text_font  = ImageFont.truetype(".../Arial.ttf", 28)

At 300 DPI one point is 4.167 px, so the body is **6.7 pt** and the title **11.5 pt**. Book
body text is normally 10–12 pt. 6.7 pt is smaller than a legal footnote, and the "title" is
set at ordinary body size — measured, not estimated, by rendering the page and reading the
box back.

The symptom is visible the moment the page is rendered with real content: 65 characters at
6.7 pt is about 1000 px of a 2250 px measure, so the text hugs the left ~40% of an 8.5×11
page and leaves a large empty right column. The page reads as a mistake rather than as a
book page.

**Why this is worth a card rather than a comment.** The audience for these books is the one
that complains about small print: EV-0003 is a 2★ review of a competitor reading *"Very tiny
squares. Not good for older people."*, and it is one of the three pieces of evidence behind
ASM-0001. Shipping the one page that explains how to play in 6.7 pt aims straight at that
complaint. Every book this project prints carries this page as interior page 1.

Measured replacements, verified by rendering the drafted 40-line guide text through
`page_frame` and the same font file:

| | now | this card | why |
|---|---|---|---|
| body | 28 px (6.7 pt) | **46 px (11 pt)** | ordinary book body size |
| title | 48 px (11.5 pt) | **92 px (22 pt)** | reads as a title, not as body |
| line spacing | 50 px | **71 px (17 pt)** | ~1.5x leading; 50 px collides at 46 px type |

At those sizes the 40-line draft ends at y=3141 of 3187 usable — one page, nothing to spare,
which is the right density for a guide page.

1. **Derive the sizes from points and the page's own DPI, not from bare pixels.** The defect
   is that the numbers are pixels with no stated relationship to the page. Name the point
   sizes as constants and convert once, so the next person reading the method can see that
   11 pt was intended. A book profile at a different DPI must not silently change the
   apparent type size.
2. **Do not re-wrap the caller's text.** The method takes lines and draws them; keep that.
   Wrapping is the caller's business and is out of scope here.
3. **Re-record the book baseline.** See the guardrails: page 1's pixels change by design.

Out of scope, and deliberately so — both touch this same method and either could be folded
in by whoever picks this up, but neither is this defect:
- **Worked example rows on the guide page.** Nonogram technique reads as gibberish in prose
  and clicks instantly as a picture, so the page ought to draw one example row per technique.
  That is a feature, needs grid drawing on a page that currently draws only text, and is
  much larger than a type fix.
- **The page's title wording.** It says "How to Use This Book"; if the page comes to teach
  technique it should say so. One line, but it is copy, not this defect.
- **The guide page's text itself.** A drafted replacement sized to this page is in
  `docs/guides/how-to-solve-nonograms.md` Part 2. Landing it is a copy decision for the
  owner, not part of fixing the type.

## Acceptance criteria

- **AC-236** — given the book's interior, when the guide page is rendered at 300 DPI, then its
  body type is 11 pt and its title 22 pt, each measured from the rendered glyph box rather
  than read back from the constant that set it.
  *test:* `TestGuidePage_TypeIsBookSized`
- **AC-237** — given a guide page carrying the longest text the book ships, when it is
  rendered, then every line fits inside the usable frame's width and the last line sits above
  its bottom margin.
  *test:* `TestGuidePage_TextFitsTheUsableFrame`
- **AC-238** — given two page specs whose DPI differs, when each renders a guide page, then
  the type's size **in points** is the same on both.
  *test:* `TestGuidePage_PointSizeIsIndependentOfDpi`
- **AC-239** — given the guide page, when its lines are drawn, then consecutive baselines are
  at least 1.4x the body's point size apart, so 46 px type cannot be set on 50 px leading.
  *test:* `TestGuidePage_LeadingClearsTheType`

## Guardrails

- G-1: **Only the guide page's own pixels may move.** The level dividers and the SOLUTIONS
  divider (Arial at 60) keep their type; every puzzle page, answer page and the cover are
  untouched. The book baseline names the font-dependent pages as `[1, 2, 4, 6, 8]` — page 1
  is this card's, pages 2/4/6/8 are the dividers' and must not change.
- G-2: **Re-record the baseline, never relax it.** `tests/fixtures/book_baseline_card144.json`
  carries an explicit instruction: a baseline "must NEVER be regenerated to make a test fail
  less", and a card that deliberately changes a page's content "records a NEW baseline in a
  commit of its own, with its own card number". Follow that — a new
  `book_baseline_card149.json` that supersedes CARD-144's, in its own commit, naming the
  commit it was recorded from, with `changed_pages` listing page 1 and only page 1. Do not
  edit CARD-144's file.
- G-3: Do not change `page_frame`, the page spec, any margin or the interior's page count.
  This card changes ink inside an unchanged frame (ADR-0036/R2: geometry is COMP-007's).
- G-4: Do not edit `src/nonogram/export/**` or `tests/fixtures/a4_golden/**` (CON-019). The
  guide page is book-only; the A4 goldens must stay byte-identical.

## Architecture context

- **FR:** FR-043 (the interior and its guide page)
- **INV:** INV-013 (the interior starts at the guide page as page 1)
- **ADR:** ADR-0036 (geometry ownership), ADR-0037 (print strokes and legibility)
- **CON:** CON-018 (margins), CON-019 (A4 byte-identity — must not move)
- **Components:** COMP-007 (geometry, unchanged), COMP-009
- **Trace:** meta/architecture/trace.yml

## Worktree notes

- [Origin] Measured 2026-09-30 while drafting the guide page's replacement text. The draft and
  the arithmetic are in `docs/guides/how-to-solve-nonograms.md` Part 2; the finding is on the
  board's backlog.
- [How it survived] Nothing rendered the guide page and looked at it. The page is pinned by a
  sha256 in the book baseline, which proves it has not *changed* — not that it was ever right.
  A digest is a regression guard, not a judgement, and `review.visual: off` in this project
  means no automated step has ever looked at a rendered page. Worth remembering when reading
  the other baselined pages: they carry the same kind of evidence.
- [Font dependence, read before recording anything] The guide page letters in the system's
  Arial when Pillow finds it and in Pillow's built-in face when it cannot, so its pixels are
  machine-dependent — `font_fingerprint` in the baseline exists for exactly this. Record the
  new baseline on a machine whose fingerprint matches the recorded one, or record the
  fingerprint change deliberately and say so in the file.
- [Evidence] EV-0003 (2★, "Very tiny squares. Not good for older people."), one of the three
  observations behind ASM-0001. The research also recommends this audience explicitly for the
  beginner/large-print shelf.
