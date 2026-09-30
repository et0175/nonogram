# CARD-149: The guide page is legible at book size — its body is 6.7 pt today

**Status:** done
**Priority:** P2
**Category:** bug
**Estimate:** 0.25d
**Complexity:** trivial
**Revision pending:** false
**Skill:** python-pro
**TDD:** —
**Branch:** card/149-guide-page-type
**Worktree:** —
**Source:** measured 2026-09-30 while drafting the guide page's text (docs/guides/how-to-solve-nonograms.md)
**Idea:** —
**Wave:** 27
**Depends on:** —
**Touches:** src/nonogram/admin/book_pdf_generator.py, tests/test_book_guide_page_type.py, tests/fixtures/book_baseline_card149.json
**Review score:** 9.0 (1 cycle + fix)
**Started:** 2026-09-30T13:20:00Z
**Closed:** 2026-09-30T16:20:00Z
**Actual:** 0.2d
**Merge commit:** 2a18cf2
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
- [Env] forge 2026.8.17
- [Font fingerprint checked before starting] This machine's `font_fingerprint()` is
  `19f6bed7…d710a5`, identical to the one recorded in `book_baseline_card144.json`. So a
  baseline re-recorded here IS comparable with the existing one, and the guardrail's warning
  about recording on a mismatched machine does not bite. Had it differed, the right move would
  have been to record the fingerprint change deliberately rather than quietly.
- [Card authored by the orchestrator, 2026-09-30] Unusually for this board, the measurements in
  "What to implement" are the orchestrator's own, taken while drafting the guide page's
  replacement text. The reviewer should treat them as claims to check, not as given: re-derive
  the 6.7 pt / 11.5 pt figures and the proposed 46/92/71 px from the code and the page's DPI
  rather than accepting the table.

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
### Cycle 1 review (2026-09-30)

- [Review 1/3] **9.0** · risk LOW · lane FAST ·
  `meta/review/20260930T154039Z-CARD-149-cycle1.yml` · 0 critical, 0 important, 3 minor,
  3 info. **Ready to merge.** Branch base verified first (`merge-base` == main's head).
- **Mutation: 8 mutants, 8 killed, 0 survived.** Body 11→10 and 11→12, title 22→20, `type_px`
  made dpi-ignoring, `round`→`int`, leading 17→15 (just under the 15.4 pt floor — the boundary
  is live), `y += leading` → `y += body_size`, title gap 36→0. Mutated in a throwaway detached
  worktree under the scratchpad, never in the reviewed tree.
- **AC-236 is a real measurement, not a tautology — proven by trying to break it.** The test
  recovers point sizes by dividing the rendered glyph box by an ink-to-em ratio it measures
  itself at a 400 px probe, and imports no size from the module under test (grepped: the four
  constants and `type_px` appear in `tests/` only inside comments). Setting the body to 10 pt
  or 12 pt is killed; the ±0.4 pt tolerance is ~±1.7 px against a 4.17 px point, so 1 pt steps
  separate with room to spare.
- **The changed fingerprint verified from first principles.** The reviewer reimplemented
  `font_fingerprint()` from source and ran it: `(48, 28, 60)` → `19f6bed7…d710a5`, byte-identical
  to CARD-144's recorded value (so the machine has not changed), and `(92, 46, 60)` →
  `cfa57e76…ba30b`, byte-identical to the new one. And the decisive point: a careless
  re-recording on another machine **would have moved the divider's 60 entry too**. It did not.
- **G-2 called exemplary.** All eleven page records compared by hand rather than trusting the
  field: page 1's sha256 differs, pages 2–11 byte-identical. The two-commit split was judged
  not just acceptable but the point — `ce4adfe` alone is red on exactly two assertions, and
  that red intermediate *is* the evidence the ink moved; folding it into one commit would erase
  the only proof the baseline was re-recorded rather than relaxed.
- **The byte delta traced to the byte**: re-encoding the guide page at the old and new sizes
  with the exporter's own JPEG call gives 164,859 → 193,671 = **+28,812**, exactly the
  2,666,560 − 2,637,748 interior delta. Page 1 alone, confirmed arithmetically.
- **AC-238 is the only thing in the repo that pins the fix**: the mutant making `type_px` ignore
  its `dpi` argument was killed by exactly and only AC-238's two tests. The re-derivation (a
  `PageSpec` carries no DPI, so the test varies `BookPDFGenerator.dpi`) was judged faithful
  rather than a weakening — varying a spec's DPI would require touching `page_frame`, which G-3
  forbids.
- **The undeclared fallback addition belonged here.** It sits inside `except OSError:` of the
  Arial call, so on a machine with Arial it is structurally unreachable and can move no
  baselined pixel — confirmed by reading, not asserted. The `TypeError` guard is right for the
  declared floor: `load_default` gained its `size` parameter in Pillow 10.1, so 10.0 raises.
- System contract: 46 rules — 8 ✓, 38 ⚠ no_eligible_fact, 0 ✗. ADR-0036/R2 ✓ (the frame still
  comes from `page_frame(self.page_spec(…))`; `type_px` converts a *type size*, not page
  geometry — no cell fitted, no grid line placed). CON-018 and CON-019 checked by hand because
  the card's `Touches` omits `tests/helpers/book_corpus.py`, which the diff changes, so the
  assembler never offered them (F-006).
- Minor findings:
  - **F-001, the one worth fixing.** AC-237's corpus floor **cannot fail**:
    `count_and_trim_corpus()` builds with `while len(cases) < CORPUS_CASES`, so
    `len(corpus) >= CORPUS_CASES` is vacuously true at any value — the reviewer re-ran the
    sizing loop at 48, 12, 2 and 1 and it passes at all four. The 48 cases genuinely run today,
    so nothing is unverified now, but the guard against future silent shrinkage is inert — which
    is precisely the failure CLAUDE.md's seeded-corpus convention exists to prevent. Two
    stronger idioms already in the repo to copy: `test_cli_exports_byte_identity.py:66-73` (a
    separate `REQUIRED_CASES` below `CORPUS_SIZE`, commented "above the floor so the floor is a
    guard, not the target") and `test_books_list_plan_stats.py:808`
    (`assert checked >= CORPUS_CASES >= 24`).
  - F-002 `type_px`'s two `ValueError` branches are untested and unreachable in production.
  - F-003 the fingerprint's sized fallback is mis-described for the divider's 60 —
    `create_divider_page` and `create_cover` still call a bare `load_default()`. Direction
    checked: it fails safe (over-strict, never falsely comparable), so a comment defect rather
    than a soundness one. Not fixing the divider was correct — that would move pages 2/4/6/8
    and breach G-1.
  - F-005 (info, worth acting on later) **no standing CON pins the interior's body type.** The
    11 pt promise is held only by this card's tests. Given EV-0003 and ASM-0001, that is a rule
    the model should carry, not a card.
- **The reviewer looked at the renders** and adds two caveats for the owner: the white under the
  title is now *tighter* than the white between the text's own sections, and roughly 70% of the
  page is empty below the text — which is where the deferred worked-example rows would go.
  Neither is a defect of this card.
- [Build gate] PASSED, orchestrator's own run: 5392 collected, 5383 passed, 2 failed, 7 skipped.
- [Review sync] 1 report → meta/review/

### Implementation, 2026-09-30 (card/149-guide-page-type)

- [Measurements re-derived, not accepted] The card's table is **arithmetically
  right**: 28 px at 300 DPI is 6.72 pt and 48 px is 11.52 pt; 11 pt is 45.83 px
  (46), 22 pt is 91.67 px (92), 17 pt is 70.83 px (71). Two figures in the prose
  are **off**, both because they describe the *drafted* text rather than the text
  the book ships: the usable measure is **2288 px**, not 2250 (the frame is
  x 150..2438, y 113..3188 on CON-018's Book 1 — 2288 x 3075 usable), and the
  shipped 11-line text used **24.3%** of that measure at 28 px, not "~40%".
  39.8% is what it uses *after* this card. The "40-line draft ends at y=3141 of
  3187" line could not be checked and was not relied on: the draft is out of
  scope and was not landed; the shipped text's last ink now ends at y=1014 of
  3188.
- [What changed] `GUIDE_TITLE_PT` 22, `GUIDE_BODY_PT` 11, `GUIDE_LEADING_PT` 17,
  `GUIDE_TITLE_GAP_PT` 36 (the old 150 px restated), all converted once by
  `type_px(points, dpi)` against `BookPDFGenerator.dpi`. The method still draws
  the lines it is given and re-wraps nothing. The Arial-less fallback now asks
  Pillow's built-in face for the same size — a bare `load_default()` letters any
  page at a 10 px em, which is this card's own defect wearing a fallback's
  clothes. No-op wherever Arial exists.
- [AC -> test] AC-236 `TestGuidePage_TypeIsBookSized` (4 tests), AC-237
  `TestGuidePage_TextFitsTheUsableFrame` (3), AC-238
  `TestGuidePage_PointSizeIsIndependentOfDpi` (2), AC-239
  `TestGuidePage_LeadingClearsTheType` (2), all in
  `tests/test_book_guide_page_type.py`. Every size is recovered from a rendered
  glyph box and the face's own measured ink-to-em ratio; nothing imports a size
  from the module under test. 6 of the 11 fail against the pre-card code.
- [AC-238's wording, re-derived] A `PageSpec` states the sheet in **millimetres**
  and carries no DPI; the resolution that turns them into pixels is
  `nonogram.export.layout.DPI`, reaching the method as `BookPDFGenerator.dpi`.
  That is what the test varies (300 and 600), since G-3 forbids touching
  `page_frame` or the spec. The page's glyph boxes double and the point sizes
  stay put.
- [Baseline] `tests/fixtures/book_baseline_card149.json`, in its own commit,
  `changed_pages` `[1]` — verified page by page against CARD-144's digests: page
  1 and only page 1 moved. CARD-144's file is untouched. The machine was first
  shown to reproduce its recorded `font_fingerprint`
  (`19f6bed7...d710a5`) with `MACHINE_FACE_SIZES` still `(48, 28, 60)`; the tuple
  then had to be re-derived to `(92, 46, 60)` per its own comment, so the new
  file records the new digest (`cfa57e76...ba30b`) and says at length why it
  moved on an unchanged machine.
- [Looked at, since `review.visual` is off] Renders in
  `~/Documents/nonogram-reviews/CARD-149/` (`guide-page-before.png`,
  `guide-page-after.png`, `-view` downscales, `-before-after-top.png`). Before:
  a small dense block in the top-left eighth, 557 px of a 2288 px measure, the
  title only 1.7x the body and reading as a bold line of it. After: a title that
  reads as one, a text block using 908 px (39.8%) of the measure and ending at
  y=1014 of a 3188 bottom margin, with ~2000 px of the page still white. It
  reads as a book page.
- [One judgement left for the owner] The title-to-body gap was *restated*, not
  re-designed: 150 px is 36 pt and stayed 36 pt. Under a 92 px title that leaves
  74 px of white under the title against 99 px between the text's own sections,
  so the title is now the tightest white on the page. Deliberate — it keeps this
  card to the type — but `GUIDE_TITLE_GAP_PT` is one constant if more air is
  wanted.
- [Out of scope, flagged not done] Worked example rows, the title's wording and
  the drafted replacement text in `docs/guides/how-to-solve-nonograms.md` were
  all left alone. A measurement for whoever picks the copy up: at 11 pt the
  longest line the page ships is 908 px, and the narrowest measure a stored book
  can have on CON-018's margins (a 10 cm trim) is 919 px. It fits by 11 px
  (0.9 mm). The drafted 65-character lines would be ~1400 px and would **not**
  fit a 10 cm trim at 11 pt, so landing that copy carries a wrapping question
  with it — and wrapping is the caller's business, per this card.
- [Suite] 5383 passed, 2 failed, 7 skipped (5392 collected). The two failures are
  the pre-existing `test_size_configuration_applied` and
  `test_batch_creation_form_renders`. All 11 new tests execute; none skips.

### Orchestrator corrections to this card's own prose (2026-09-30)

The implementation re-derived the card's measurements as instructed, and found the table right
but two figures in the prose wrong. Both errors are the card author's — the orchestrator's —
and both came from measuring the *drafted* replacement text rather than the text the book ships:

- The usable measure is **2288 px**, not the 2250 the card says, and the bottom margin sits at
  **3188**, not 3187.
- "The text occupies the left ~40% of an 8.5x11 page" describes the page **after** this fix
  (908 px = 39.8%). The eleven lines the book ships used **557 px = 24.3%** at 28 px. The
  symptom was real — 6.7 pt either way — but that number described the wrong page.
- The "40-line draft ends at y=3141" figure was about the draft, which is out of scope and was
  not landed; it was correctly not relied on.

Confirmed right: 28 px at 300 DPI is 6.72 pt, 48 px is 11.52 pt, and 11/22/17 pt convert to
46/92/71 px. `docs/guides/how-to-solve-nonograms.md` has been corrected to match, and now also
carries the wrapping constraint the implementation measured (the drafted 65-character lines run
~1400 px, while the narrowest measure a stored book can have is 919 px).

### Orchestrator gates (2026-09-30)

- [Guard] Baseline discipline verified independently: `book_baseline_card144.json` is
  **byte-identical** on this branch, the new `book_baseline_card149.json` is in **its own
  commit** (0d20dc2, after the type fix ce4adfe), names CARD-144's file in `supersedes`, and its
  `changed_pages` is **[1]** — page 1 and only page 1, over eleven recorded pages.
- [Guard] Looked at the rendered page myself, before and after
  (`~/Documents/nonogram-reviews/CARD-149/guide-page-before-after-top.png`). Before: the title
  is barely larger than the body and the block reads as fine print. After: the title reads as a
  title and the body as book text.
- [Note on the changed fingerprint] The new baseline records `cfa57e76…`, not CARD-144's
  `19f6bed7…`. That is **not** a machine change — the orchestrator verified before starting that
  this machine still computes `19f6bed7…` for the old size tuple. The fingerprint digests the
  face *and the sizes asked of it*, so changing the guide page's sizes necessarily moves it. A
  reviewer seeing a changed fingerprint should read the new file's explanation rather than
  assume the recording machine differed.

### [Fix 1] — F-001 closed (2026-09-30)

**Reconstructed by the orchestrator from the fix agent's report.** The agent appended its own
`[Fix 1]` block to the worktree card copy and wrote `status: fixed` into the review YAML; an
orchestrator cleanup run before the rebase (`rm` on the untracked report plus `git checkout --`
on the card) destroyed both before they were synced. The substance below is the agent's; the
wording is the reconstruction's. The code commit itself was never at risk — it is `b3e900e` on
the branch.

- **F-001 closed** — `tests/test_book_guide_page_type.py:466` now reads
  `assert len(corpus) >= CORPUS_CASES >= 48`, the double-bound idiom of
  `tests/test_books_list_plan_stats.py:808`, with a five-line comment naming which bound is
  load-bearing so the "redundant" second bound is not deleted later.
- **Why that idiom and not the other.** `tests/property/test_cli_exports_byte_identity.py:66-73`
  keeps `REQUIRED_CASES = 60` deliberately below `CORPUS_SIZE = 72` — "above the floor so the
  floor is a guard, not the target" — because that corpus's size is *emergent* (corners plus
  filtered draws), so slack absorbs incidental variation without going red. Here the size is
  **exact by construction**: `while len(cases) < CORPUS_CASES` means `len == CORPUS_CASES`
  always, so slack would only weaken the guard and let a silent 48 → 44 shrink through. The
  property demanded ("lowering the constant must make a test fail") is unconditionally true only
  when the literal equals the constant, which is what the chosen precedent does.
- **Evidence the floor is now live.** Fix agent: 47 → red, 12 → red, 1 → red, 48 → green,
  60 → green (so growth is still permitted — a floor, not a pin). Orchestrator re-verified at
  12 independently: 1 failed, 10 passed, failing on
  `TestGuidePage_TextFitsTheUsableFrame::test_the_whole_corpus_of_trims_and_counts_fits` — the
  same value that passed silently before the fix.
- **Scope held.** `b3e900e` is `tests/test_book_guide_page_type.py | 10 ++++++++--` and nothing
  else: no `src/`, no other test, no fixture. Both baselines byte-identical, verified against
  HEAD and against `0d20dc2`; no baseline assertion ever went red. The corpus build is untouched
  — same `CORPUS_SEED = 149`, same pinned smallest-trim/largest-counts first case.
- **F-002 and F-003 deliberately left open** per the owner's decision, along with F-004..F-006.
- The existing declaration at `tests/test_book_guide_page_type.py:258-263` ("the corpus asserts
  its own size inside the test that uses it, so it cannot silently shrink") was re-derived rather
  than re-worded: it was the false claim F-001 named, and it is now true as written.
- [Suite] 5383 passed, 2 failed, 7 skipped — identical to the pre-fix baseline, the two failures
  being the long-known stale-heading assertions.
- [Orchestrator lesson, recorded because it nearly cost the evidence] Worktree `meta/` artefacts
  are destroyed by a `rm`/`git checkout --` cleanup exactly as they are by `worktree remove`.
  Sync first, clean second — the same rule this session has told four implementation agents about
  and the orchestrator then broke itself.
