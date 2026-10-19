# CARD-249: The editor page says which puzzle it is editing

**Status:** ready
**Priority:** P2
**Category:** feature
**Complexity:** standard
**Estimate:** 0.5d
**Revision pending:** false
**Skill:** python-pro
**TDD:** false
**Branch:** card/249-editor-names-its-puzzle
**Worktree:** —
**Source:** owner, 2026-10-18 — found by eye on the wave-46 render (`~/Documents/nonogram-reviews/CARD-246/02-editor-as-opened-NO-DIFFICULTY-BADGE.png`), filed on owner instruction 2026-10-19
**Idea:** —
**Wave:** —
**Depends on:** —
**Touches:** src/nonogram/admin/app.py, src/nonogram/admin/templates/puzzle_edit.html, src/nonogram/admin/static/admin.css, tests/test_puzzle_editor_ui.py
**Review score:** —
**Started:** —
**Closed:** —
**Actual:** —
**Merge commit:** —
**Blocked by:** —

## What to implement

The editor page CARD-246 shipped is headed **`Edit puzzle 10×10`** and that is the *whole* of its
identification. `templates/puzzle_edit.html:61` hard-codes the heading to the extent, and the tab
title at `:49` says the same thing. The puzzle's **name is not on the page at all** — not in the
heading, not in the title, nowhere.

Three clicks earlier the list row says **"Duck · easy"**. Open the editor from it and the page says
`10×10`. With a dozen 10×10 drafts in review the only way to know which one is under the brush is
the grid itself and the URL — and the grid is the thing you are about to rewrite.

**Put the puzzle's name in the heading and in the document title.** Nothing else on the page
changes.

The route already has what it needs. `puzzle_edit_page` (`app.py:2599`) reads the row into
`puzzle` and then passes only `puzzle_id`, `extent` and `payload` to the template (`app.py:2648`).
The sibling route builds exactly the string this card wants, one line of its own
(`puzzle_solve`, `app.py:5824`):

```python
title = puzzle.get("puzzle_name") or puzzle.get("source_image") or str(puzzle["id"])[:8]
```

Use that **same fallback chain** — name, then source file, then a short id — so an unnamed puzzle
still gets a usable heading and the two pages cannot drift into two different ideas of what a
puzzle is called.

Recommended wording, not mandated: `Edit "Duck" — 10×10`, tab title `Edit "Duck" 10×10 - Nonogram
admin`. **The extent stays on the page** either way: it is the one fact the heading has today and
removing it to make room would be a trade, not a fix. Keep `×` as U+00D7, not the letter x
(the house spelling AC-323 pins on the player).

## Three traps, all of them documented in code this card touches

**Trap 1 — the player hides the name ON PURPOSE, and a careless fix will "fix" that too.**
`AC-322` and `AC-323` require the player page's header and document title to contain **no picture
name** until the puzzle is solved: the name is the answer (FR-044, CARD-163), and the solved
banner is the only place it may appear. `puzzle_solve.html:86-88` says so in its own header.

That reasoning **does not reach the editor**, and the card asserts the difference rather than
waving it away: the editor opens with the stored grid already painted — that is its AC-2
(`TestPuzzleEditor_OpensOnTheStoredGrid`) — so the answer is on screen in full before the name
could spoil anything. A page that shows the picture cannot be spoiled by naming it.

But the two pages share `base.html`, `.page-head`/`.player-head` and most of their furniture. **A
change made in a shared place instead of in `puzzle_edit.html` puts the name on the player and
breaks AC-322.** `TestPuzzleEditor_ThePlayerIsNotRegressed` is the class that already exists for
this; extend it rather than inventing a second home.

**Trap 2 — the name does NOT go in `payload`.** CARD-246's G-1 holds the board payload to
**exactly the six keys** `solver.js`'s header documents, and `_board_page_payload`
(`app.py:2480`) is written once for both pages with `mode` as "the whole difference between the
two callers". Adding a seventh key for a heading would put a player-visible field in the renderer's
contract to serve a server-rendered `<h1>`. Pass it as its own template variable, exactly as
`puzzle_solve` passes `title=`.

**Trap 3 — a name can be 120 characters and nothing shortens it.** `MAX_PUZZLE_NAME_LENGTH = 120`
(`puzzle_review.py:32`) is the only bound; `orchestrator._validated_name` refuses empty and
whitespace and **rewrites nothing else**. 120 characters in a display-size `<h1>` is several lines
at 390 px. The precedent is `tests/test_puzzle_solver_maybe.py:1010-1043`, which already pins a
120-character name — as words *and* as one unbroken token — wrapping inside the player's tools
width at three viewports. Do the same measurement here. **Wrapping is acceptable; horizontal
overflow and a clipped name are not** — a heading that ellipsises the name defeats the only reason
this card exists.

## Explicitly NOT in scope: the tier badge does not come back

CARD-246 removed the difficulty badge from this page deliberately and recorded why in two places —
`puzzle_edit.html:53-60` and the route docstring at `app.py:2631-2638` (review cycle 1, F-008): a
badge is a fact about a **stored** grid, this page rewrites the stored grid, so the badge went
stale on the first stroke and was still showing the pre-edit tier after Approve had stored another.
The difficulty is shown where it is true instead — in the save bar's message.

That reasoning is sound and this card does not touch it. A name is the puzzle's identity and does
not go stale under a brush; a tier is a measurement of the very thing being rewritten.

**The owner's open question stays open.** Whether the *pre-edit* difficulty should be shown
somewhere, labelled as the grade of the grid as stored, is one of the three decisions recorded
pending at wave 46's close. If the answer is yes it is a separate card, because it has to solve the
staleness problem F-008 found and this one does not. Do not pre-empt it here.

## Acceptance criteria

- **AC-1** (happy): *Given* a stored puzzle named "Duck", *when* its editor page is loaded, *then*
  the visible heading contains `Duck` and its extent, and the document title contains `Duck`.
  (test: `TestPuzzleEditor_NamesThePuzzleItEdits`)
- **AC-2** (boundary, the fallback chain): *Given* a puzzle with no `puzzle_name`, *then* the
  heading falls back to its `source_image`; *given* neither, *then* to the first 8 characters of
  its id — the same chain `puzzle_solve` uses, asserted against that route's output for the same
  row rather than against a re-derived literal.
  (test: `TestPuzzleEditor_NamesThePuzzleItEdits::test_the_fallback_chain_matches_the_players`)
- **AC-3** (guard, the player is not regressed): *Given* this change, *then* the player page's
  header and document title still contain no picture name before the puzzle is solved — AC-322 and
  AC-323 pass unchanged, asserted for a puzzle whose editor page in AC-1 *does* show the name, so
  the two pages are compared on the same row.
  (test: `TestPuzzleEditor_ThePlayerIsNotRegressed`, extended)
- **AC-4** (guard, the payload is untouched): *Given* the editor page, *then* its embedded payload
  holds exactly the six documented keys plus `mode`, and carries no name.
  (test: the existing CARD-246 G-1 payload test, passing unchanged)
- **AC-5** (guard, no badge): *Given* the editor page, *then* it still renders no tier badge and no
  difficulty of its own outside the save bar's message.
  (test: the existing F-008 test, passing unchanged)
- **AC-6** (boundary, the longest name): *Given* a 120-character name, as words and as one
  unbroken token, *when* the editor is opened at 1440×900, 1200×900 and 390×844, *then* the whole
  name is shown, the heading does not overflow its column horizontally, and the toolbar and the
  board are still fully visible. **State the measured figures.**
  (test: `TestPuzzleEditor_TheLongestNameFitsTheHeading`)

## Guardrails

- G-1: **The name is added to the editor only.** No shared template, partial or CSS rule may put a
  name on the player page (Trap 1). If AC-322's test needs editing, you have gone too far.
- G-2: The board payload gains no key (Trap 2, CARD-246 G-1).
- G-3: The fallback chain is the player's, not a second one. If it is copied rather than shared,
  say in the card why — two literals of one rule is the shape CARD-246's own F-015 found.
- G-4: No tier badge and no stored-difficulty display on this page (CARD-246 F-008).
- G-5: The name is rendered through Jinja's autoescaping like every other user-supplied string; no
  `|safe`, no manual markup assembly.
- G-6: No new runtime dependency (ADR-0006/R1). Browser tests stay in the dev-only extra and fail
  loudly without Chromium (ADR-0038/R7, R8).
- G-7: No test retired without a named survivor (CARD-220's rule).

## System contract

_Assembled 2026-10-19 by `system_rules.py --card CARD-249 --root meta/architecture` (57 rules returned, `card_scope: touches`). A projection — fix the source artifact, never this list._

**Curated to 8; 49 dropped and declared.** The projection returned **57**, almost all of them scoped `src/nonogram/**` or `src/nonogram/admin/**.py` — package-wide, so they match every card on this board and narrow to nothing. Owner decision 2026-10-17: ship the curated form with the dropped count stated. The kept rules are the ones a reviewer can hold *this diff* against; the package-wide scoping is a filed backlog item, not a judgement that the rest do not apply.

- **ADR-0006/R1** — The runtime dependency set is exactly stdlib + Pillow + NumPy. No third-
  party package joins the installed dependencies without revising this ADR. Non-executable
  static assets (fonts and similar data files) may ship as package data instead, and doing so is
  not a dependency change. (check: test: TestDependencyBaseline_IsExactlyPillowAndNumpy)
- **ADR-0019/R1** — The web UI adapter (src/nonogram/web/) contains HTTP concerns only —
  routing, form rendering, request parsing, and mapping onto orchestrator.GenerationRequest —
  and no domain logic or validation, mirroring cli.py; it may import the orchestrator but no
  capability module may import it or cli.py. (check: test:
  test_every_import_in_the_package_points_inward)
- **ADR-0038/R1** — The puzzle player's client is hand-written JavaScript and CSS served as
  static files by the admin panel. There is no front-end framework, no build step, no npm
  toolchain and no vendored third-party JavaScript library. Adding any of these reopens this ADR
  (and ADR-0006/R1 for vendored code). (check: review-lens)
- **ADR-0038/R3** — The player page's clues are embedded as JSON from compute_clues of the
  stored grid (the one encoder). The client never re-derives clues from the solution. (check:
  test: TestSolverPage_ShowsTheClues)
- **ADR-0038/R6** — Only the admin panel's player, behind the CON-015 / CON-016 door, may ship a
  puzzle's solution grid to the browser. A public or reader-facing player must not send the
  solution before the puzzle is solved, and any public phase reopens this ADR (CON-021). (check:
  review-lens)
- **ADR-0038/R7** — Browser tests use pytest-playwright with Chromium, declared only in a dev-
  only extra in pyproject.toml. It is never added to project.dependencies or to the admin extra.
  (check: review-lens)
- **ADR-0038/R8** — Browser tests run locally, against Chromium installed by `playwright install
  chromium`. When Chromium is not installed, browser tests fail or skip loudly, with a named
  skip reason visible in the run summary. They never pass silently. Once a CI pipeline exists,
  it installs Chromium (playwright install chromium) before running them; unti… (check: review-
  lens)
- **CON-016** — The admin panel serves a request through exactly one of two mutually exclusive
  doors, chosen by whether ADMIN_ALLOWED_HOST is set, and refuses every request that does not
  pass the door in force. With it unset (the default), it refuses any request whose Host header
  does not name this machine — a bare authority, no userinfo, path, query… (check: test:
  TestAdminPanel_RefusesEveryRequestTheDoorInForceDoesNotAdmit)

## Worktree notes

- **[How this was found]** Not by a test and not by review — by looking at the shipped page. The
  wave-46 render set includes four screenshots of the editor
  (`~/Documents/nonogram-reviews/CARD-246/`), taken through the panel's own `live` sqlite fixture;
  shot 01 is the list row reading "Duck · easy" and shot 02 is the same puzzle's editor reading
  `Edit puzzle 10×10`. Both are worth opening before starting: the gap is obvious side by side and
  invisible in either page alone.
- **[Why this is not filed as a regression]** The editor page is new in CARD-246; the name was
  never on it. Nothing that used to work stopped working, which is also why no test caught it —
  there was no claim to break.
- **[`app.py` is a conflict hotspot]** One line in one route, but the dispatcher serializes on the
  file. Expect to queue behind any sibling touching it.
- **[House rules]** `hypothesis` is not in the dependency baseline — seeded `random.Random` with an
  asserted minimum case count. Capability modules never import laterally (`tests/test_cli.py` has an
  `ast` guard). `tests/test_admin_design_tokens.py` forbids colour literals in CSS.
- **[CARD-235's registry does not see this file]** `tests/test_puzzle_editor_ui.py` declares its own
  page isolation because CARD-235's glob is `tests/test_puzzle_solver_*.py` (CARD-246 review cycle
  1, F-014). A new browser test in that file must be added to `PAGE_ISOLATION_DECLARATION` there;
  the glob itself is a filed backlog item, not this card's job.
