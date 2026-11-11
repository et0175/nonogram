# CARD-425: The “book not found” page should not offer “Browse the library”

**Status:** done
**Priority:** P3
**Category:** ux-polish
**Estimate:** 1c (0.25d)
<!-- One element and one test claim. The cost is deciding what, if anything, replaces it — see the decision. -->
**Complexity:** standard
**Revision pending:** false
**Skill:** python-pro
**TDD:** true
**Branch:** card/425-notfound-no-library
**Worktree:** /Users/omelnikova/PycharmProjects/PythonProject4-card-425
**Source:** owner play-test findings, Google Doc "Гра - тест", 2026-11-11, item 1. Reproduced on production (https://nonogram.adverax.io) before drafting; the measurements below are mine, the finding is the owner's.
**Idea:** —
**Wave:** 79
**Created wave:** 79
**Deferred waves:** 0
**Depends on:** —
**Touches:** player/book.html, tests/test_public_player_pages.py
<!-- Derived 2026-11-11 by reading where the panel lives: the not-found block in `player/book.html`, and the one test that asserts its link (`test_unknown_slug_lands_softly`, which both asserts `a.pages-library-link` inside `[data-pages-notfound]` AND follows it). Nothing under `src/`: this page is the assembler's, not the admin's. -->
**Review score:** 9.0 (cycle 2)
**Started:** 2026-11-11T18:40:00Z
**Closed:** 2026-11-11T18:05:00Z
**Actual:** 2 review cycles + 1 fix round + 2 orchestrator prose edits (wall clock excluded, owner ruling)
**Merge commit:** c1a81086
**Blocked by:** —

## Why this card exists

Measured on production at `/b/deadbeef99` (an unknown slug):

```
Your book
We could not find this book
This link does not match a book on the site. The code may have been mistyped,
or the book may not be published online yet.
[Browse the library]        -> /library
New to nonograms? How to solve one -> /how-to-solve
```

The owner's finding is the first control: a reader who scanned a QR code from **their own printed book** and landed here does not want someone else's library — they want their book, and the page cannot give it to them. Offering the library turns a dead end into a detour, and on a page whose whole job is to say "this is not it", a prominent `btn` is the most clickable thing on the screen.

The second link (`/how-to-solve`) was not objected to and stays unless the owner says otherwise: it is an offer of help, not a redirection.

## Decision owed before implementation (owner)

**D1:** does the panel keep **nothing** but the explanation; keep the how-to-solve link only; or say something actionable instead (for example "check the code on the back of your book")? **Default if unanswered:** remove the library button, keep the how-to-solve line, change no wording — the smallest change that satisfies the finding.

## What to implement

1. Remove the `<a class="btn pages-library-link" href="/library">Browse the library</a>` paragraph from the not-found block in `player/book.html`. The same class is used elsewhere on the listing pages; remove the element, not the class.
2. `tests/test_public_player_pages.py::test_unknown_slug_lands_softly` asserts that link exists **and** follows it to `/library`. That claim is retired by this card: replace it in the same place with the new claim (the panel is visible, explains itself, and offers no library link), per the owner's test budget — change the existing test, do not add one.

## Acceptance criteria

- **AC-1** *Given* `/b/<unknown>` and `/b/not-a-slug`, *then* `[data-pages-notfound]` is visible and contains no `a.pages-library-link`; *and* the page still explains itself in words. (test: `tests/test_public_player_pages.py::test_unknown_slug_lands_softly`, changed; plant: re-add the anchor and the test reds.)
- **AC-2** (nothing else loses its library link): the `/library` link on the book landing proper and on the listing pages is unchanged. (test: the existing landing cells.)

**Net test count: 0 added.**

## Worktree notes

- **[Env]** forge version unresolved (no `.claude-plugin/plugin.json` at the executing path; no `meta/.skills.yml`, so no `forge.min_version` comparison and no `models:` block — agents inherit the session model).
- **[Start gate]** `make_probe.py start-gate` → exit 0, `decision: gate`, `source: test_command`. **Exit 127 in a worktree** (none has a `.venv`): use `/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python`. Fork point `2ab3ac11`, interactive mode.
- **[Impact scope]** Derive with `scripts/impact_set.py --gate --against main`, never from a standing note — CARD-423 shipped two criticals past a hand-picked set the script would have caught.
- **[Concurrency]** CARD-426 and CARD-428 are `in_progress` in their own worktrees, and CARD-424 is queued behind 426. **None of them touches this card's files**: they own `src/nonogram/admin/static/{solver.js,admin.css}` and the solver test modules, while this card owns `player/book.html` and `tests/test_public_player_pages.py`. No serialization needed — but three agents are running Chromium suites on this host at once, so keep every run narrow.
- **[Owner decision]** D1 was not answered; the card's recorded default applies — remove the library button, keep the how-to-solve line, change no wording. The owner said only "start 425 too", which is not a ruling on the wording, so the author takes the default as written and does not reword the panel.

### Implementation (wave 79, station=implementation, model=claude-opus-5)

Commit `2d5ebf36` on `card/425-notfound-no-library`. Two files, as `Touches:`
derived them: `player/book.html` and `tests/test_public_player_pages.py`.
Nothing else, and no new copy — D1 was not answered, so the card's recorded
default is what was built: the anchor removed, the explanation and the
footer's how-to-solve line untouched to the word.

**AC-1: test `test_unknown_slug_lands_softly` red→green.** Red first, with
the anchor still in the markup, and for the right reason: the two assertions
ahead of it (the panel is visible; its text explains itself) passed, and the
failure was `panel.locator("a.pages-library-link").count() == 0` reporting
`1 == 0` at `/b/0000000000` — the element, not a fixture or a selector typo.
Green after the paragraph came out: 33 passed in the file.

**AC-2: no node changed on the landing proper or the listing pages.** The
whole module is green (33 passed), and `tests/test_book_landing_page.py` plus
`tests/test_book_landing_address.py` were run because the change sits in the
landing's own template (34 passed). `test_book_landing_lists_and_links` and
every `/library` node still hold their links untouched.

**The plant, run twice, because the second one is the honest one.** Re-adding
the anchor verbatim reds the test (that is the red run above). But a *fresh
class* would have slipped past a class-only assertion, so the panel is now
held to the `href` as well: planting
`<a class="btn pages-other-link" href="/library">Browse the library</a>`
reds `panel.locator('a[href="/library"]').count() == 0`, measured, and the
markup was restored from a scratchpad copy and re-verified green.

**What the panel reads after the change** — nothing was reworded, and what
is quoted is the whole panel for the 404 path:

```
We could not find this book
This link does not match a book on the site. The code may have been
mistyped, or the book may not be published online yet.
```

The malformed-address path keeps its own `pages.js` sentence, unchanged:
"This address names no book. A book link looks like /b/ followed by ten
letters and digits." The how-to-solve line survives because it was never in
the panel — it lives in `book.html`'s `footer.book-foot`, outside
`[data-pages-notfound]`, so the card's "keep the how-to-solve line" needed no
edit at all.

**Net collected node ids: 0 added** (target met). 33 collected before and
after; the diff touches no `def test_`/`class Test` line, and the two unknown
shapes are a loop inside the body rather than a parametrization, so the node
set is identical. One test function changed in place, none added, none
deleted.

**No cleanup was needed inside the panel.** `player.css`'s
`.pages-notfound p:last-child { margin-bottom: 0; }` now lands on the
explanation paragraph, which is exactly what it is for, so removing the
button left no hanging margin and no empty `<p>`.

#### One finding, raised and then authorized (see the SCOPE+ record below)

`What to implement` step 1 says "The same class is used elsewhere on the
listing pages; remove the element, not the class." **That premise is wrong,
measured:** `grep -rn pages-library-link player/ src/ tests/` has four hits
and no fifth — this one anchor, the CSS rule, and the two test lines now
retired. So the class was used nowhere else, and `.pages-library-link
{ text-decoration: none; }` in `player/player.css` is dead as of this commit.
`player.css` is outside this card's scope and outside `Touches:`, so it was
left alone rather than quietly widened. The library links that AC-2 protects
are *different elements*: `a.book-continue[data-pages-continue]` on the
landing proper, and `how-to-solve.html`'s `a.hts-home-top` /
`a.btn.hts-go.hts-home-end`. A one-line dead-rule sweep, if anyone wants it,
is smaller than a card.

### SCOPE+ `player/player.css` — the dead `.pages-library-link` rule

Commit `89353b6a`, separate from `2d5ebf36`. **A third file moved on this
card**, which is what this line is here to tell the gate's selection and the
reviewer. Authorized by the coordinator on the measurement above, after it
checked the concurrency: CARD-426 owns `solver.js` / `admin.css` /
`test_player_base_css.py`, CARD-428 owns `admin.css`'s landscape block and
`test_puzzle_solver_zoom.py`, and neither touches `player/player.css`, so the
sweep creates no rebase.

**Why:** removing the anchor in `2d5ebf36` left
`.pages-library-link { text-decoration: none; }` styling nothing. One dead
declaration, caused by this card's own diff — below the cut bar for a card of
its own, and the fix is smaller than the card would be.

**The measurement the deletion rests on, re-derived after `2d5ebf36` rather
than carried from before it:** `grep -rn pages-library-link player/ src/
tests/` → **3 hits, none of them a use.** The rule itself
(`player/player.css`); one line of `test_unknown_slug_lands_softly`'s
docstring naming the anchor this card retired; and that same node's assertion
that no such anchor is in the panel. The pre-commit count was 4 — the
difference is exactly the anchor removed in `2d5ebf36`. No markup in the
served tree carries the class, so nothing lost a style.

**Verified on the narrowed set, and the set was derived rather than assumed:**
`grep -rln "player\.css" tests/` names every module that reads the
stylesheet, and all four are green — `tests/test_public_player_pages.py`
(its `scan_site`), `tests/test_how_to_solve_page.py` (which *parses*
`player.css` for `var()`/token agreement, so it is the one that would notice
a mis-edit), `tests/test_impact_set.py` and `tests/test_public_player.py`:
**262 passed.** `tests/test_book_landing_page.py` was EXCLUDED on that same
measurement — it does not read the stylesheet. No full suite, no
`make test-gate`, and the full-suite lock was not taken: the coordinator owns
this card's gate and acquiring it would have refused two live worktrees'
pytest at `pytest_configure`.

Net test count across both commits: **0 added.**

### [Orchestrator] notes on the implementation

- **[Card defect, mine]** This card's `## Why this card exists` presents the how-to-solve link as the second control *of the not-found panel*, and says it "stays". Measured: it was never in the panel — it lives in `book.html`'s `footer.book-foot`, outside `[data-pages-notfound]`, so nothing had to be kept and the sentence described a page that does not exist. I read it off the rendered body text of `/b/deadbeef99` and assumed adjacency meant containment. The finding is the implementer's; the defect is mine.
- **[SCOPE+ authorized by the orchestrator]** `player/player.css` is not in this card's `Touches:`. The implementer measured that `2d5ebf36` left `.pages-library-link { text-decoration: none; }` with nothing to style, raised it, and correctly refused to widen the card itself. I authorized the one-line deletion rather than cutting a card: one dead declaration, caused by this diff, below the cut bar, and I checked the concurrency before saying yes — CARD-426 owns `solver.js`/`admin.css`/`test_player_base_css.py`, CARD-428 owns `admin.css`'s landscape block and `test_puzzle_solver_zoom.py`, so no in-flight card touches `player/player.css` and the sweep creates no rebase. Commit `89353b6a`, separate from the AC work.
- **[Verification, derived not assumed]** I suggested a pair of modules to check the sweep against; the implementer resolved the real set with `grep -rln "player\.css" tests/` and ran four — `test_public_player_pages.py`, `test_how_to_solve_page.py`, `test_impact_set.py`, `test_public_player.py` — 262 passed, and excluded `test_book_landing_page.py` on the measurement that it does not read the stylesheet. **The sharpest node was not in my pair:** `test_how_to_solve_page.py::test_the_lesson_uses_tokens_and_the_players_probe_colours` parses `player.css` for `var()`/token agreement and hex literals, so it is what would have caught a mis-edit. Third time on this board that deriving a set beat naming one from memory (CARD-423's gate, CARD-428's geometry home, this).
- **[Plant, at two strengths]** Re-adding the anchor verbatim reds the new assertion; so does a replacement under a fresh class (`a.btn.pages-other-link`), which is why the cell asserts `a[href="/library"]` absent rather than the class alone. The weaker assertion would have passed a page that still offered the library under a different class.
- **[Build gate] still DEFERRED.** CARD-426's and CARD-428's reviewers are running pytest from their own worktrees; the lock's guard refuses every pytest from a worktree while a foreign one holds it, so taking it now would break them. The gate runs when the host is quiet, before this card merges.

- [Review 1/3] Score: 8.5 — forge:review, `overall_verdict: pass`, `task_contract_verdict: pass`, `system_contract_verdict: pass` (38 rules assembled, 7 ✓, 31 ⚠ `no_eligible_fact`, 0 ✗). **0 critical, 1 important**, 1 minor, 1 out-of-scope. Report `meta/review/20261111T164104Z-CARD-425-cycle1.yml`. **[Severity gate]** FAIL on the one important finding — and the reviewer's own framing of why is worth keeping: both circuits pass and the finding sits outside both by construction, because *no standing rule says "an AC agrees with the test it names"*. It is the severity gate, not a contract, that holds this card.
- **[Review 1/3] the finding: three places still promise the link this card removed, and nothing guards any of them.** `meta/architecture/requirements.yml`'s **AC-388** `then:` reads "the not-found page renders with a way to the library" and names `test_unknown_slug_lands_softly` as its verifier — the node that now asserts the opposite twice over; `player/book.html`'s own header comment, *in the file this card edited*, still says "and offers the library (AC-388)"; and `meta/design/components.md`'s PagesNotFound entry still describes "a `.pages-library-link` to `/library`", a class that now exists nowhere but an absence assertion. The reviewer read both candidate guards and showed the drift is silent: the registry guard checks that each AC's node id **resolves**, never its `then:` text, and the inventory guard enumerates `data-pages-*` hooks markup→inventory only, so a sentence about a retired class is invisible to it. `components.md` is also the diff's strongest `[history]` signal — it co-changed with `book.html` in 3 of its 7 commits and is absent here.
- **[Review 1/3] what it verified rather than accepted:** the replacement claim discriminates per failure path (planting `fail(page, "Sorry.")` on the 404 branch reds it, so "explains itself" cannot pass on a rewritten or empty panel); `fail()` is the panel's only writer and creates no element and no href, so the panel admits no runtime-built or JS-handler library link; `/library` is still reached by about ten other nodes in the module, so the retired click-through was not its only cover. **Mutation check RAN** (2 mutants, both killed) rather than being deferred, with the reason stated: the gating finding says nothing about whether the replacement claim discriminates.
- **[Correction, mine]** I relayed to the reviewer that its worktree's `## Worktree notes` carried only `—`. That was the implementer's statement from when IT started, before it wrote its own notes there; by review time the implementation and SCOPE+ records were present and the reviewer read them. Stale relay, not a wrong fact — but I passed it on as current.
- **[Scope check for the fix round]** `meta/architecture/requirements.yml` IS editable from a card branch: CARD-400 (`77c0ccd6`), CARD-229 (`67707e94`, `a25b254a`) and CARD-399 (`4f2d131f`) each merged with it in their diffs. Verified in the log rather than assumed from the `/commit` rule about `meta/`, so the fix round carries all three edits on the branch instead of the orchestrator making them in main.

### [Fix round] (wave 79, station=fix, model=claude-opus-5, review cycle 1 — 8.5)

Commit `54c6a8bc`, four files. Prose and YAML plus one assertion; no behaviour
change, no CSS, no new test.

**F-001 (important) — the retired claim retracted in all three sites.**
`meta/architecture/requirements.yml`, FR-045's **AC-388**: `then:` now reads
that the not-found page renders, explains in words why it is up, offers no way
to the library, and throws no script error, with the owner's 2026-11-11
play-test decision as a dated reason comment above it, in the shape **AC-387**
uses for its own 2026-10-28 restatement. The `test:` ref is untouched —
`test_unknown_slug_lands_softly` is still the verifier, it simply verifies the
new claim — and no AC was added, renumbered or otherwise edited.
`player/book.html`'s header comment lost the library clause from its AC-388
bullet and kept the AC reference. `meta/design/components.md`'s **PagesNotFound**
entry lost the `.pages-library-link` clause only; its second half, the text node
rewritten for a malformed address, is still true and stays. `CARD-284.md` was
not touched: a closed card's body is a record, not a live claim.

**The validator WARN-set comparison for the `requirements.yml` edit.** The
validator of record named in `meta/kanban/config.yml` under
`architecture_validator:` (forge_1's `validate.py --root meta/architecture
--phase all`), run before and after the edit from this worktree:
**0 error(s), 98 warning(s), 0 info** both times — and the sets, not the
totals, were compared: `comm -3` over the two sorted `[WARN ]` sets prints
**0 lines**, so no warning entered and none left. (The totals alone would not
have settled it; config.yml records a +1/-1 pair hiding inside an unchanged
count.) `tests/test_check_ref_resolution.py` — the registry's own census and
check-ref guard, resolved by reading which modules read `requirements.yml`
rather than guessed — is **26 passed, 0 skipped**. Its one `UserWarning`
(the 'honest-dead' class losing 12 members) is **pre-existing, measured**: the
module was re-run against the pre-edit `requirements.yml` restored from HEAD
and printed the identical warning and 26 passed, then the edited file was put
back.

**F-002 (minor, taken) — one absence assertion instead of two.**
`test_unknown_slug_lands_softly` now asserts `panel.locator("a").count() == 0`
in place of the `a.pages-library-link` and `a[href="/library"]` pair. The
docstring states what that means and that it was deliberate: the decision is
that the panel offers **no link at all**, which is stronger than this card's
AC-1 wording ("no `a.pages-library-link`") and is what the owner's finding
implies. The ground for it is in the docstring too — `pages.js`'s `fail`
creates no element, it sets one `textContent` and toggles `hidden`, so the
panel's subtree is static markup plus one text node, and the single assertion
also closes the two shapes the pair missed (a replacement anchor under a fresh
class, and one whose `href` is assigned at runtime).

**Both plants re-run against the collapsed assertion rather than assumed.**
Planting the verbatim anchor
(`<p><a class="btn pages-library-link" href="/library">Browse the library</a></p>`)
reds it — `AssertionError: /b/0000000000, assert 1 == 0` on
`panel.locator("a").count() == 0`. Planting the fresh-class form
(`<a class="btn pages-other-link" href="/library">`) reds the same assertion
the same way. `player/book.html` was copied to the scratchpad first and
restored after each, md5 back to the pre-plant `73518939c5d0…` both times, and
the node is green again after the restore.

**Net collected node ids: 0.** `--collect-only -q` over
`tests/test_public_player_pages.py` reports **33**, the figure the
implementation round and the review both measured; the fix round's diff touches
no `def test_`/`class Test` line.

**Verification runs** (budget, not the gate — the orchestrator owns this card's
gate; no full suite, no `make` target, the full-suite lock not taken, two peer
worktrees live). All with
`/Users/omelnikova/PycharmProjects/PythonProject4/.venv/bin/python -m pytest -o addopts= -rEfs`
(the worktree has no `.venv`, and a bare `-q` would make `-qq` and print no
summary):

* `test_unknown_slug_lands_softly`, `test_the_public_tile_is_registered_in_the_design_inventory`,
  `test_the_registrys_refs_for_this_file_resolve_or_are_card_285s`,
  `test_book_landing_lists_and_links` → **4 passed, 0 skipped**;
* `tests/test_check_ref_resolution.py` → **26 passed, 0 skipped**;
* `test_unknown_slug_lands_softly` alone, after each plant was reverted →
  **1 passed**.

`meta/design/components.md`'s only machine reader is
`test_the_public_tile_is_registered_in_the_design_inventory`, which is in that
first run — re-derived here rather than carried: `grep -rln components.md
tests/ src/` names one other test module, and its single hit is a docstring
sentence, not a read.

- [Review 2/3] Score: 9.0 — forge:review, all three verdicts `pass` (38 rules: 7 ✓, 31 ⚠, 0 ✗). 0 critical, 0 important, 1 minor, 3 out-of-scope. Report `meta/review/20261111T170742Z-CARD-425-cycle2.yml`. **[Severity gate]** PASS. Its mutation check killed **three** mutants including one the fix round had not planted — a fresh-class anchor with **no href at all**, the runtime-assigned shape that was the stated reason for collapsing the assertion. The cycle-2 minor (AC-388 page-scoped vs a panel-scoped test) was applied by the orchestrator in `6bf3c95d`, rebased as `4514c260`.
- **[Validator trap, recorded for every future before/after comparison]** The reviewer reproduced the fix round's validator figures (0 errors / 98 warnings, `comm -3` over the sorted WARN sets printing 0 lines) and found the trap: run the same validator against a **detached copy** of `meta/architecture` and it answers 0 / 88 / 11, because check-ref resolution searches the surrounding tree. Only worktree-rooted pairs are comparable.
- **[Build gate]** Rebased onto main first, so the gate measured what merges. Derived selection (`scripts/impact_set.py --gate --against main`): 79 files, 5382 tests. Result: **5354 passed, 19 skipped, 9 deselected, 1 xfailed, 1 failed** in 22:22, lock held through `acquire()` and released. The one red is `tests/test_book_pdf_memory.py::TestMemoryGuard_StillFailsWhenTheExportItselfRegresses`, **pre-existing on main** (a drifted host-calibration bound, verified on main earlier today). 19 skips is the proportional DB count for a 79-file subset (18 bare-`DATABASE_URL` + 1 `setrlimit` the kernel refuses here) — nothing newly skipped.
- **[Rebase note]** `git rebase main` autostashed the worktree's frozen card copy and the autostash conflicted. Resolved by taking the branch's version; the autostash was then verified to hold nothing but `CARD-425.md`, all three of whose `###` sections were already synced into main's copy, and dropped by its explicit id. **The owner's three own WIP stashes were untouched.** For the remaining cards: clean the worktree card file before rebasing rather than letting git autostash it.
- **[Done]** Merged `c1a81086` on the gates. Estimate 1c against 2 cycles — ratio 2.000, and the reason is the same shape CARD-423 showed: the markup change was one element, and everything after it was the retraction of claims the change refuted.
