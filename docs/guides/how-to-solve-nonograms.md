# How to solve a nonogram — in plain words

Reader-facing explanations of the three solving techniques, written for a puzzle-book
audience rather than for engineers. Two versions below: a long one for a web page or an
Amazon description, and a tight one sized to the book's own guide page.

The three techniques are the same ones the generator's solver uses, and they are what
decides a puzzle's difficulty tier — so the names in `src/nonogram/difficulty.py`
(`simple_overlap`, `line_dp`, `probe_contradiction`) and the names below describe the same
things. See ADR-0029 for the ladder and ADR-0005 for the tier cutoffs.

---

## Part 1 — the long version

### How a nonogram works

The numbers beside each row and above each column tell you the runs of filled squares in
that line, in order, with at least one empty square between runs. A row marked `4 2` has a
run of four, a gap, then a run of two.

Fill the squares you are certain of, and cross out the ones you are certain are empty. The
crosses do as much work as the fills — most of the time it is a crossed-out square that
unlocks the next row.

### Technique 1 — Squeeze from both ends

Slide a run as far left as it will go, then as far right. Any square covered by *both*
extremes must be filled, because no arrangement can avoid it.

> A row of 10 with the clue `8`. Pushed left, it covers squares 1–8. Pushed right, 3–10.
> Squares 3–8 are covered either way, so fill them. Six squares solved without knowing
> where the run starts.

The part beginners miss: this is not an opening move you do once. It works **relative to
what you already know**, so every time a square is settled the ends squeeze tighter and the
rule pays out again. Come back to it after every discovery.

### Technique 2 — Keep what every arrangement agrees on

Rather than only the two extreme positions, consider *every* legal way the clue could sit on
the line, and keep what they all agree about. Filled in all of them → fill it. Empty in all
of them → cross it out.

> A row of 10, clue `3 2`, and you already know square 5 is empty. That kills every
> arrangement that puts the 3 across square 5. List what survives, and some squares are
> filled in all of them and some empty in all of them — things squeezing from both ends
> alone would never have found.

This technique contains the first one; it is the same idea taken to its limit. It is also
the one that produces most of the crosses, which is why crossing out is worth the effort.

### Technique 3 — Assume, and watch it break

Pick a square you cannot settle. Pencil it in as filled and follow the consequences through
the rows and columns it touches. If you reach something impossible — a line whose clue can
no longer fit at all — then filled was wrong, so that square is **empty**. Write that in and
carry on.

> Everything has stalled. You try filling one square, and four rows later a row with clue
> `5` has only four spaces left for it. Impossible. So that square is empty, and the board
> moves again.

**This is not guessing.** You are not choosing a branch and hoping; you are proving one
option impossible so the other is forced. The trial always gets rubbed out. Nothing is ever
left resting on a coin-flip.

### What the difficulty labels mean

| Tier | What it takes |
|---|---|
| Easy | Squeezing from both ends is enough, start to finish |
| Medium | Needs "what every arrangement agrees on", and may need assume-and-break for part of the grid |
| Hard | Needs assume-and-break over most of the grid |

A caution for marketing copy: since the Medium/Hard cutoff moved from 66 to 90 on
2026-09-23 (CARD-137), **Medium puzzles already require the hardest technique** for part of
the grid. "Easy and Medium need only simple logic" was true at the old cutoff and is not
true now. Easy is the only tier where no lookahead can be promised.

### The promise worth printing

Every puzzle has **exactly one solution**, proved by the solver before the puzzle could even
be stored, and no guess-tier puzzle can enter a book at all. So: you never have to guess,
and there is never a second answer. Competitors' reviews complain about exactly this, so it
belongs on the guide page *and* in the product description.

---

## Part 2 — the guide page, at book size

Sized against the real page: the usable frame is 2550 px wide with room for 63 body lines at
the renderer's 50 px spacing, so vertical space is not the constraint — readability is. Lines
are kept near 65 characters.

### First, a defect this draft uncovered: the guide page's type is about 6.7 pt

`create_guide_page` sets the body font to 28 px and the title to 48 px. The interior renders
at **300 DPI**, where 1 pt = 4.167 px — so the body is **6.7 pt** and the title **11.5 pt**.
Book body text is normally 10–12 pt; 6.7 pt is smaller than a legal footnote, and the "title"
is set at ordinary body size. Rendering the draft at the current sizes shows the symptom
plainly: the text occupies the left ~40% of an 8.5×11 page with a large empty right column,
because 65 characters at 6.7 pt is only about 1000 px of a 2250 px measure.

This matters beyond looks. The research behind these books recorded a 2★ review of a
competitor — EV-0003 — reading *"Very tiny squares. Not good for older people."* A guide page
in 6.7 pt aims at exactly that complaint.

Measured replacements that fit the same text on one page, verified by rendering:

| | now | proposed | why |
|---|---|---|---|
| body | 28 px (6.7 pt) | **46 px (11 pt)** | ordinary book body size |
| title | 48 px (11.5 pt) | **92 px (22 pt)** | reads as a title |
| line spacing | 50 px | **71 px (17 pt)** | ~1.5× leading; 50 px would collide at 46 px type |

At those sizes the 40-line draft ends at y=3141 of 3187 usable — it fits on one page with
nothing to spare, which is the right density for a guide page. The longest line uses 69% of
the measure, a comfortable reading width.

**This is a code change to `create_guide_page`, not a copy change, so it needs its own card.**
Note the same method is the one that would have to change to draw worked example rows, and
the title text is a one-line edit in it too — all three belong in one card.

**What the current renderer can and cannot do.** `BookPDFGenerator.create_guide_page`
(`src/nonogram/admin/book_pdf_generator.py`) draws plain left-aligned lines in one size:
no bold, no indentation beyond leading spaces, and **no worked-row pictures**. A guide page
with drawn example rows — which is how nonogram technique is best taught — needs a change to
that method and deserves its own card. The draft below is written to work as plain lines.

The three `{...}` slots are the existing dynamic counts; keep them.

```text
This book holds {puzzle_count} puzzles: {easy_count} easy, {medium_count} medium, {hard_count} hard.

HOW A NONOGRAM WORKS

The numbers beside each row and above each column tell you the
runs of filled squares in that line, in order, with at least one
empty square between runs. A row marked 4 2 has a run of four,
a gap, then a run of two.

Fill the squares you are sure of. Cross out the ones you are sure
are empty - the crosses do as much work as the fills.

THREE TECHNIQUES, IN THE ORDER YOU NEED THEM

1. Squeeze from both ends.
   Push a run as far left as it will go, then as far right. Any
   square covered both times must be filled. In a row of ten with
   the clue 8, that settles six squares before you know where the
   run begins. Do it again after every discovery - the ends
   squeeze tighter each time.

2. Keep what every arrangement agrees on.
   Consider the ways the clue could still fit the line. Squares
   filled in all of them are filled; squares empty in all of them
   are empty. One crossed-out square rules out whole arrangements,
   which is why crossing out pays.

3. Assume, and watch it break.
   Stuck? Pencil in one square as filled and follow it through the
   rows and columns it touches. If you reach a line whose clue can
   no longer fit, that square must be empty. Rub out the trial and
   write the answer instead. You are not guessing - you are
   proving one option impossible.

EVERY PUZZLE HAS EXACTLY ONE SOLUTION

Checked by computer before it went into this book. You never need
to guess, and there is never a second answer to find.

Answers begin after the SOLUTIONS divider at the back.
```

44 lines including the blank spacers — 2200 px of the 3150 available, so it fits with room
to spare and does not crowd the page.

**The page title** is drawn separately by the renderer and currently reads "How to Use This
Book". "How to Solve These Puzzles" would describe the page better now that it teaches
technique rather than listing counts; changing it is a one-line edit in the same method, so
it belongs in the same card as anything else done to this page.
