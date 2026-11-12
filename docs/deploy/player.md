# The public player: what runs where

The public player (COMP-011) is **static files on Vercel** — DEC-045/ADR-0041. It is a
different deployment from the admin panel, and that separation is the point of the
phase: customer traffic from a printed QR code never reaches the Render service, which
sleeps (see `docs/deploy/render.md`). Nothing in `src/nonogram/**` serves a player page,
and there is no `/play/...` Flask route.

This page cannot read the Vercel dashboard. A value is filled in only where there is
evidence for it in the repository, and the evidence is dated. Everything else is marked
`TODO(owner): copy from the Vercel dashboard`. An observed fact describes the project on
the day it was observed; it is not a claim about today's settings.

Observed in the repository on **2026-10-29** (CARD-285):

- `player/` holds the hand-written pages, one Python assembler, and `vercel.json`.
  Importing `player/assemble.py` needs only the standard library, and it imports nothing
  from `nonogram` by name; *assembling* the site needs the admin extra (jinja2, which
  comes with Flask), because the generated `/play/<key>` shell renders the admin's
  template fragment. ADR-0006/R1 is unaffected: extras sit outside the closed runtime baseline.
- `vercel.json` is the only host configuration in the repo, and the test fixtures route
  by reading it, so the rewrites below are the ones that deploy.
- Nothing under `src/nonogram/**` references the assembler, and `pyproject.toml` ships
  no `player/` package data.

## What production is

Observed on **2026-10-30**, at the first deploy. Everything here was read back from
the CLI or fetched over the network, not copied from a plan.

| Fact | Value |
| --- | --- |
| Project | `nonogram-studio`, id `prj_9SoVGUETjWldt1HN3CwrC8GCZbF1` |
| Scope | `et0175's projects` (`team_p379UJJnEKFQ9nJC15tzcTyp`) |
| Production URL | `https://nonogram.adverax.io` — the owner's custom domain, registered and verified serving this site 2026-10-30 (DNS is third-party; Vercel lists `adverax.io` and `nonogram-studio.co` under the scope) |
| Vercel URL | `https://nonogram-studio-et0175s-projects.vercel.app`, still answering |
| Framework Preset · Build Command · Root Directory | `Other` · none · `.` |
| Output Directory | "`public` if it exists, or `.`" — the deploy root *is* the site |
| Deployed from | the Vercel CLI, out of `build/site`; **no Git repository connected** (the CLI's own attempt to connect `et0175/nonogram` failed, which is the wanted outcome — see "Why not a git-driven deploy of the same tree") |
| Deployment Protection | **disabled** by the owner on 2026-10-30. It was on by default for a project under a team scope, and every path answered `302 → vercel.com/sso-api`; a printed QR code pointing at an SSO login would have been worse than no QR code |
| Counting | none: the deployed tree was assembled without `--analytics`, because the GoatCounter site code below is still a placeholder |
| Bundle behind it | exported 2026-10-29 — 160 puzzles, one book (`6578fe3f67`) |

Checked on the live site the same day: `/library`, `/play/<key>` and `/b/<slug>` all
200, the served `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`,
`width` (no solution, no puzzle title), and the served `solver_state.js` is SHA-256
identical to `src/nonogram/admin/static/solver_state.js` — ADR-0041/R3's
byte-identical copy, verified against production rather than against the assembler.

`TODO(owner): confirm Auto-Deploy in the dashboard and record it here.` With the CLI
publish this page documents, a push should deploy nothing at all.

### Publishes since the first deploy

Observed on **2026-11-05**, read back from the CLI and from the live site rather than
copied from a plan. The public player gained zoom (CARD-324, merge `18aeac30`), and the
tree was published the way this page describes, with one addition: a **preview first, then
promote**.

| Step | What was observed |
| --- | --- |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-zoom-deploy`, no `--analytics`, so no counting snippet in any file. 160 puzzles, one book landing. The bundle is the 2026-10-29 export, unchanged. A fresh output directory was used rather than `build/site`. |
| Check before publishing | The built `play.js` and `player.css` are SHA-256 identical to `player/`; `solver_state.js` is identical to `src/nonogram/admin/static/solver_state.js`. Every `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`, `width`. A local preview answered 200 on `/library`, `/play/<key>`, `/b/<slug>` and `puzzle/<key>.json`. |
| Preview | `vercel deploy --yes` from the tree with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported, no `.vercel/` in the tree: deployment `nonogram-studio-dd5c55h5p`. The same three files, fetched from it, matched the local hashes. |
| Production | `vercel promote <that deployment URL> --scope <team> --yes` created production deployment `nonogram-studio-bji650yak` (Ready). `https://nonogram.adverax.io` then served the same three hashes, answered 200 on the three doors, and its puzzle file carried the same five fields. |
| Rollback target | The production deployment before it, `nonogram-studio-b5dbrnyxf`, was still Ready afterwards. This page records that it existed; it does not record that a rollback was tried. |

Why a preview first: it puts the exact artifact on the host, where the hashes can be
compared, before any QR code's domain serves it, and `vercel promote` then publishes that
artifact without rebuilding it. Not observed: the zoom controls in a real browser on the
live site, Auto-Deploy's dashboard state, and any counting (there is none until the
GoatCounter code below is real).

**The crosshair publish, 2026-11-05 (same day, a few hours later).** The public player gained the
crosshair (CARD-325, merge `fd37038c`), and the same recipe was run again, this time with the
behaviour exercised in a real browser on the live URLs before and after the switch.

| Step | What was observed |
| --- | --- |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-crosshair-deploy`, no `--analytics`. 160 puzzles, one book landing; the bundle is still the 2026-10-29 export. `play.js`, `player.css`, `solver_state.js` and `tokens.css` are SHA-256 identical to their sources; no goatcounter reference and no external `http(s)` reference in the tree; every `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`, `width`; `build/site` and `build/site-zoom-deploy` were not touched. |
| Preview | `vercel deploy --yes` with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported and no `.vercel/` in the tree: deployment `nonogram-studio-bqoj489om`. It sat at "Initializing" for about seven minutes before it became Ready (the zoom preview, earlier the same day, was Ready at once), and the CLI process outlived the tool's five-minute limit and was left running. Once Ready: the three doors and the puzzle file answered 200 and the four files above matched the local hashes. |
| Behaviour on the preview | Headless Chromium on `/play/00d5d88065`: hovering a cell marked 34 elements as crossed (32 cells and the row and column clue boxes); moving the pointer off the stage cleared all of them; a click still changed the cell's state; the three zoom controls were present; no page error. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created production deployment `nonogram-studio-a47h6w2y5`. It stayed at "Initializing" for about eleven minutes, and during that time `https://nonogram.adverax.io` kept serving the previous (zoom) deployment `nonogram-studio-bji650yak`, which stays Ready as the rollback target. After it became Ready the production URL served the same four hashes, answered 200 on the three doors, the puzzle file carried the same five fields, and the same browser check gave the same figures (34 crossed on hover, 0 after leaving, a click still marks, no page error). |

What this adds to the record: a promote is not instant, and the switch of `nonogram.adverax.io`
follows the new deployment becoming Ready, not the promote command returning; so verify the
production hashes after the status says Ready, not after the command exits. Not observed: a real
phone, the native-pinch behaviour on a real device, Auto-Deploy's dashboard state, and any counting.

**The circles publish, 2026-11-06.** The public player gained circled clue numbers (CARD-326, merge
`423aef15`), and the same recipe was run a third time. Main then carried zoom, the crosshair and the circles.

| Step | What was observed |
| --- | --- |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-circles-deploy`, no `--analytics`. 160 puzzles, one book landing; the bundle is still the 2026-10-29 export. `play.js`, `player.css`, `solver_state.js` and `tokens.css` SHA-256 identical to their sources; the built `play.js` carries `circledClues`, `wireCrosshair` and the zoom code, the built stylesheet `is-circled` and `is-crossed`; no goatcounter reference and no external `http(s)` reference; every `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`, `width`; `build/site`, `build/site-zoom-deploy` and `build/site-crosshair-deploy` were not touched. |
| Preview | `vercel deploy --yes` with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported and no `.vercel/` in the tree, run in the background: deployment `nonogram-studio-92v2egpwd`, Ready 28 seconds after the command started (the zoom preview was Ready at once; the crosshair preview took about seven minutes: the delay VARIES from publish to publish and is not a fixed cost). The three doors and the puzzle file answered 200 and the four files matched the local hashes. |
| Behaviour on the preview | Headless Chromium on `/play/00d5d88065`: no number circled at load; after marking the first run of row 0 (4 cells) with the run still OPEN, still none; after closing the run with a white mark, exactly one circled (the row's number), its ring a `1px solid rgb(28, 35, 51)` border; one undo removed it, redo restored it; with the pointer over a cell of row 0 the row's clue box was crossed AND its number circled; `body[data-solved]` stayed "false"; Reset cleared the circles; no page error. (A first attempt that marked the run without closing it circled nothing, which is the module's rule, not a defect: a number circles only once its run is closed by an empty mark or an edge.) |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created production deployment `nonogram-studio-914baad47`, Ready within seconds. `https://nonogram.adverax.io` then served the same four hashes, answered 200 on the three doors, the puzzle file carried the same five fields, the same circle run gave the same figures, and the crosshair and zoom checks gave their earlier figures (34 crossed on hover, 0 after leaving, a click still marks, three zoom controls, no page error). |
| Rollback target | The production deployment before it, `nonogram-studio-a47h6w2y5` (the crosshair build), was still Ready afterwards; the zoom build `nonogram-studio-bji650yak` also remains. A rollback was not tried. |

Not observed: a real phone, how the compact ring reads on one (the rings are slim pills, tighter than the
admin's, a declared design choice recorded on CARD-326), Auto-Deploy's dashboard state, and any counting.

## What is owner-managed and what is repo-managed

| Thing | Who owns it |
| --- | --- |
| The Vercel account, the project, and the production domain | **Owner.** Not created by this card; CARD-285 ships no network call to a host. |
| GoatCounter account and site code | **Owner.** See "Usage counting" below. |
| A custom domain and its DNS | **Owner**, and out of scope for CARD-285 (G-4). |
| `player/**` — the pages, the CSS, the assembler | Repo. |
| `vercel.json` — the rewrites for the three doors | Repo. |
| The allow-list and the QR shapes on this page | Repo. This page is read by the tooling; see the two blocks below. |
| The bundle's contents | Repo code, owner action: the panel's **Export player bundle** button. |

### The first deploy, start to finish

The owner steps and the commands, in the order they have to happen. Each step says
what evidence to bring back to this page, because this page is the only place the
repository records what production is. Nothing below has been run — every step is
`TODO(owner)` until someone does it and dates it here.

**The project is created by the first deploy, not in the dashboard.** The CLI asks
what it needs and writes the project; there is no "Framework Preset / Build Command /
Output Directory" form to fill in first, because a static tree has no build step
(ADR-0041/R3) and because the directory those settings would name is one a
git-driven deploy could not see anyway (see "Deploying the tree" below for the
measurement).

1. **Sign in to the CLI.** `vercel login`, once per machine. It opens a browser.
   Observed 2026-10-29: the CLI is installed (59.11.7) and its stored token is
   stale, so this step is real rather than a formality. In Claude Code, run it as
   `! vercel login` so the prompts reach you.
2. **Export the bundle** — the admin panel's **Export player bundle** button.
   Only non-draft books reach it; the panel says so if the book you pressed it
   from is a draft. Details in "Publishing a new bundle" below.
3. **Assemble the site** — "Publishing a new bundle" step 2. For this first
   deploy, drop `--analytics` from that command: the counting endpoint is still a
   placeholder until step 7, and the pages render and play with no snippet at all.
4. **Look at it before publishing it.**
   `./.venv/bin/python scripts/preview_player_site.py build/site 8081`, then open
   `/library`, one `/play/<key>` and one `/b/<slug>`. A plain `python -m
   http.server` is the trap here — it 404s every rewrite while `/library` keeps
   working, which reads as a broken tree on a tree that is fine.
5. **Create the project and deploy, in one command:**

   ```bash
   cd build/site && vercel deploy --prod
   ```

   The first run has no `.vercel/` to read, so it asks: the scope (your account or
   a team), whether to link to an existing project, and a project name — the name
   decides the default domain, so `nonogram-player` gives
   `nonogram-player.vercel.app`, which is the shape the QR block below currently
   guesses. Non-interactively the same thing is `vercel link -p nonogram-player
   -y` followed by the deploy. *Evidence to record here:* the production domain the
   deploy prints, and the date.
6. **Write the domain into the QR block below**, replacing the placeholder, and
   re-assemble so the site and this page agree. CARD-210 (printed QR codes) is
   blocked on exactly this value, and a printed base cannot be changed later —
   see drift step 3.
7. **Create the GoatCounter site**, note its code, and if it is not `nonogram` put
   the real one in the allow-list block below — in that one line. Then re-assemble
   **with** `--analytics` and deploy again. This is the first counted tree, and it
   is deliberately last: a visit that was never counted cannot be counted later,
   and counting to a site code that does not exist is worse than not counting.
   *Evidence to record here:* the site code and the date.
8. **Confirm Auto-Deploy** in the dashboard, and record the toggle's state. The
   admin panel's deploy was bitten by a dashboard setting nobody wrote down
   (`docs/deploy/render.md`, the 2026-09-23 incident). With the CLI publish this
   page documents, a git push should deploy nothing at all; if the dashboard says
   otherwise, that disagreement is the thing to record.

After the first deploy, a publish is steps 2, 3 and 5 — and step 5 is just the one
command, provided the project identity survives (see "The project link cannot live
in the output directory" below; it does not survive by default).

## The three doors

`vercel.json`'s rewrites, read from the file on 2026-10-29:

| URL | Serves | Why a rewrite |
| --- | --- | --- |
| `/play/<key>` | `play/index.html` | One document plays every puzzle; its loader reads the key out of the path and fetches `puzzle/<key>.json`, then hands it to the admin's `solver.js`. |
| `/b/<slug>` | `b/index.html` | The QR landing for one book. |
| `/library` | `library/index.html` | The extensionless path needs the rule; `/library/` would resolve by directory index. |
| `/how-to-solve` | `how-to-solve/index.html` | The site-wide lesson page (CARD-419); same arrangement as `/library`. |

### The QR URL base and shapes

CARD-210 consumes this block. The path shapes are repo facts — they are
`vercel.json`'s rewrite sources, and
`tests/test_public_player_pages.py::test_the_qr_url_shapes_here_are_the_shipped_routes`
holds this block to that file, so the two cannot drift. The **base** is the one value
only the owner can supply.

<!-- BEGIN qr-url-shapes -->
```
base    = https://nonogram.adverax.io
book    = {base}/b/{slug}
play    = {base}/play/{key}
library = {base}/library
lesson  = {base}/how-to-solve
```
<!-- END qr-url-shapes -->

**Since CARD-332 this page is no longer the only place a base is written down,
so here is the rule for which one wins where.** The panel's Print setup stores a
**player domain on each book**, and the arrangement screen builds that book's
reader links from the book's own value and from nothing else — this block is not
read as a fallback, and a book with no stored domain shows no link at all rather
than one built from a base nobody chose for it. CARD-210 prints from the same
stored value. So:

* **For a book** — what the book stores wins, always. A printed run records what
  was printed, and a book printed before a domain change cannot be corrected.
* **For the deploy** — this block wins, and keeps the meaning it always had: the
  shapes production serves, and the base it serves them at today. It is what the
  owner copies into a book's Print setup, not what any code reads.

The two can therefore disagree, and that is the intended state once a domain
moves: the books printed before the move keep the base they were printed with.

**What a book prints (CARD-389, ADR-0041/R8).** The printed shape is
`{book's stored domain}/b/{slug}` and nothing else: one code for the whole book.
`/play/<key>` stays served, because the landing page's tiles and anything already
printed link to it, but it is no longer printed. The slug is computed, never stored
(R7), by `player_bundle.landing_address`, which the bundle's own `export_bundle`
agrees with by construction: both read the book's puzzle keys in **print order**
(easy, then medium, then hard, INV-009), so tile *i* on the landing page is the puzzle
the interior prints as number *i*. A book stored in an older mixed order therefore
gets the slug of its print order, which differs from the slug older exports named it
by. A book holding a row that is stored but has no readable grid gets no landing address
and no `book/<slug>.json` (the exporter names the book and the row), because the
interior refuses to print such a book. A puzzle id whose puzzle was deleted is
different: the panel prints the surviving puzzles, numbered over the survivors, so the
book is addressed over the survivors and the deleted id is only reported as left out.
A row the interior drops (malformed clues) takes no number on the page and none in the
landing page. A book with no stored domain has no address at all.

The `base` above is the owner's **custom domain**, registered on 2026-10-30 and
**observed serving this site the same day**: `/library`, `/play/<key>`, `/b/<slug>`
and `puzzle/<key>.json` all answer 200 on it, the served puzzle file carries the same
five fields and no answer, and `solver_state.js` is SHA-256 identical to the panel's.
This is the base a printed QR code should carry — it is short, it is the owner's, and
it does not move if the project is ever rebuilt or renamed on the host.

The project's Vercel URL (`https://nonogram-studio-et0175s-projects.vercel.app`,
"What production is" below) still answers and is the fallback if DNS is ever pointed
away. It is the *team-suffixed* form because the bare `nonogram-studio.vercel.app`
is already another of the owner's projects — it serves a page titled "My Google AI
Studio App" — so that shorter domain was never available to this one.

`TODO(owner): copy the production domain here again if the custom domain is ever
moved or retired.` That is the one way this value still moves, and a printed base
cannot be re-pointed (drift step 3): a book carries whatever was true the day it was
printed. `{slug}` is `player_bundle.book_slug` of the book's ordered keys; `{key}` is
ADR-0041/R1's 10 hex characters.

**The hint publish, 2026-11-06.** The public player gained the derived hint (CARD-327, merge `c8a19833`), and the same recipe was run a fourth time. Main then carried zoom, the crosshair, the circles and the hint.

| Step | What was observed |
| --- | --- |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-hint-deploy`, no `--analytics`. 160 puzzles, one book landing; the bundle is still the 2026-10-29 export. `play.js` (`687a5bd061d7`), `player.css` (`5251cc51502e`), `solver_state.js` (`e586c9da20b6`) and `tokens.css` (`979ab7a50e43`) SHA-256 identical to their sources (the first twelve hex digits); no goatcounter reference; every `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`, `width`; no `.vercel/` in the tree. `build/site`, the three earlier deploy directories and the card worktree's `build/site-hint` play-test build were not touched. |
| Preview | `vercel deploy --yes` with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported, run in the background: deployment `nonogram-studio-6pd1yeznt`, Ready within about a minute. The three doors and the puzzle file answered 200 and the four files matched the local hashes. |
| Behaviour on the preview | Headless Chromium on `/play/00d5d88065`: one Hint button, not inside `.player-toolbar`; the first press lit a line (14 elements) and said "Hint: look at column 5."; the second said why ("... the 12-run must overlap in the middle ..."); the third marked one cell as a recorded stroke ("Hint: row 2, column 5 is black.", `Hints: 1`, one `.is-hinted` element, no line lit); one Undo removed the mark and returned the counter to 0; no page error. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created production deployment `nonogram-studio-6s7mfek5n`, Ready within seconds. `https://nonogram.adverax.io` then served the same four hashes, answered 200 on the three doors, the puzzle file carried the same five fields, and the same hint run gave the same figures. |
| Rollback target | The production deployment before it, `nonogram-studio-914baad47` (the circles build), was still Ready afterwards, as were the crosshair build `nonogram-studio-a47h6w2y5` and the zoom build `nonogram-studio-bji650yak`. A rollback was not tried. |

Not observed: a real phone, how the hint reads at 300% zoom on one (the lit line can be out of view; neither page auto-scrolls, recorded on CARD-327), the other machines' rendering of the hint tint (a floor of 8 against a smallest measured 10, one machine), Auto-Deploy's dashboard state, and any counting.

**The probe publish, 2026-11-07.** The public player gained probe mode (CARD-380, merge `652c16f8`: the hypothesis transaction: Probe, Keep and Contradiction), and the same recipe was run a fifth time. The tree also carries one file change that is not probe mode: CARD-385's public-mode additions to `src/nonogram/admin/static/solver_state.js`, which ADR-0041/R3's byte-identical copy ships whether wanted or not (the owner ruled: no partial deploy). Main then carried zoom, the crosshair, the circles, the hint and probe.

| Step | What was observed |
| --- | --- |
| What changed against production | `play.js` `687a5bd061d7` to `31e430147309`, `player.css` `5251cc51502e` to `6aa20c7eddc1`, `play/index.html` `d6cf779ca491` to `3172d3d7cf0d` (the Probe bar and its note): probe mode. `solver_state.js` `e586c9da20b6` to `e3ff8f5760f5`: CARD-385 (`PUBLIC_MODE`, `PUBLIC_GRID`, `runsOf`, `isClueSolved`, `requireSolution`, a null-solution branch in `hintCell`, a `stampOf` save stamp). `play.js` imports none of the changed paths and the puzzle JSON carries no `mode`, so it is inert on the public page; the browser run below is the evidence. `tokens.css`, `pages.js`, `library/index.html`, `b/index.html` and the puzzle files unchanged. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out ~/Documents/nonogram-reviews/deploy-2026-11-07/site`, no `--analytics`. 160 puzzles, one book landing; the bundle is still the 2026-10-29 export. The four files SHA-256 identical to their sources; no goatcounter reference; every `puzzle/<key>.json` carries exactly `clues`, `height`, `key`, `tier`, `width`; the default tree is the same file set as before (the opt-in shared-UI preview, since retired, was not built). |
| Preview | `vercel deploy --yes` with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported: deployment `nonogram-studio-einto95gr`, Ready within about a minute. The six files above matched the local hashes; `/play/<key>`, `/b/<slug>` and `/library` 200, an unknown path 404. |
| Behaviour on the preview | Headless Chromium on a 10x10 (`22f1a32460`) and a 20x20 (`6259eb2b56`) puzzle: a click marks and undo clears; zoom 100% to 125% and back; hover crossed 21 (10x10) and 41 (20x20) elements and 0 after leaving; closing row 0's runs circled 2 numbers; Hint ladder advanced point, explain, reveal (counter 1); Probe opened with Keep and Contradiction shown, one probe mark, Keep kept the cell as filled, Contradiction abandoned the cell back to unknown; the save was restored identically on reload (`nonogram-public:<key>`); Reset cleared the board; marking the solution (computed here by the solver from the clues) set `body[data-solved]` true and showed the Solved banner. Zero page errors, zero non-GET requests, no served JSON containing a `solution` key. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created production deployment `nonogram-studio-qu83cb3hw`, Ready about 20 seconds later. `https://nonogram.adverax.io` then served the same six hashes, 200 on the three doors and 404 on an unknown path, the puzzle file with the same five fields, and the same browser run gave the same figures (0 page errors, 0 non-GET). |
| Rollback target | The production deployment before it, `nonogram-studio-6s7mfek5n` (the hint build), was still Ready afterwards. A rollback was not tried. |

Not observed: a real phone, how probe reads there, Auto-Deploy's dashboard state, and any counting.

**The curated-bundle publish, 2026-11-09. A BUNDLE-ONLY publish, and the first one whose code is deliberately older than `main`.** The owner curated the book in the panel against the production database and exported a new bundle; the request was to publish it. `main` could not be the source: CARD-399 has deleted `player/play.js` and the shared-UI player is on `main`, and the owner's ruling of 2026-11-08 holds that player off production until CARD-394, CARD-400..413 and CARD-414 have merged — CARD-400 to CARD-413 were all still `ready` on the day. So the site was assembled from the tree production already served, with only the bundle new.

| Step | What was observed |
| --- | --- |
| What changed in the bundle | The same 160 puzzle keys, in a book whose **order moved**: one key (`2758040fc4`) fell from position 54 to 57, and the title changed `c1` to `Christmas Nonograms`. R7 hashes the ordered keys and not the title, so the reorder alone moved the book's address: **`/b/6578fe3f67` to `/b/bc271a1524`**. No `/play/<key>` moved, because no grid changed. The previous bundle was copied to `build/player-bundle.pre-20261109` before the export overwrote it. |
| Which code was published | The tree at `8643b9b3` (CARD-385's public mode, 2026-11-06), identified by hashing rather than by reading this page: at that commit `play.js` `31e430147309`, `player.css` `6aa20c7eddc1`, `pages.js` `f62fd1a57607`, `solver_state.js` `e3ff8f5760f5` and `tokens.css` `979ab7a50e43` are each byte-identical to what `https://nonogram.adverax.io` was serving. `main`'s files differ on four of the five (`play.js` does not exist there at all), which is the shared-UI work under the 2026-11-08 hold. |
| Assemble | `git archive 8643b9b3 player src/nonogram/admin/static src/nonogram/limits.py` into a scratch directory, then that commit's own `player/assemble.py --bundle build/player-bundle --out ./site`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. The five files hashed identically to production's, every `puzzle/<key>.json` carried exactly `clues`, `height`, `key`, `tier`, `width`, no served JSON contained the string `solution`, no goatcounter reference, `.player-site` present and no `.vercel/` in the tree. `build/site` and the earlier deploy directories were not touched. |
| Preview | `vercel deploy --yes` with `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` exported: `nonogram-studio-33jnkofek`, Ready in seconds. `/library`, `/play/<key>`, `/b/bc271a1524` and the puzzle file 200; an unknown path 404; the five hashes matched. `/b/6578fe3f67` answers 200 — it is a rewrite to one document — but `book/6578fe3f67.json` is **404**, so the old address now gets the unknown-book soft landing. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created production deployment `nonogram-studio-qhh7e0idm`, Ready in about 2 s. On `https://nonogram.adverax.io`: the three doors and both JSON files 200, `/nope` and `book/6578fe3f67.json` 404, the five hashes unchanged, the served puzzle file carrying the same five fields, and `book/bc271a1524.json` carrying `Christmas Nonograms` with 160 puzzles. |
| Rollback target | `nonogram-studio-qu83cb3hw`, the probe build this replaced, still Ready. A rollback was not tried. |

Not observed: a real phone, any behavioural run on this publish (the code is byte-identical to the build already play-tested on 2026-11-07, so the browser run was not repeated), Auto-Deploy's dashboard state, and any counting.

**What this publish leaves owed.** A printed QR code pointing at `/b/6578fe3f67` would now land on the soft "unknown book" page. Nothing is known to be printed — CARD-210 (real scannable codes) is still `ready` — but a book's address moves with its print order, which is R7 working as designed and drift step 3's whole point: curate before printing, not after.

**The shared-UI publish, 2026-11-09. The owner lifted their own hold.** The 2026-11-08 ruling held the shared-UI player off production until CARD-394, CARD-400..413 and CARD-414 had merged. The owner lifted it the next day, with the reason stated: *"it's not a real prod yet as we don't have any book published"* — no printed book points at this site, so the fourteen findings cards (CARD-400 to CARD-413, all still `ready`) are improvements to a site no reader has been sent to yet. Published from `main` at `aa578932`, with the curated bundle of the publish above.

| Step | What was observed |
| --- | --- |
| What changed against production | Everything the page is made of. `play.js` is **gone** (404 on the live site now): CARD-399 retired it on 2026-11-08 and `/play/<key>` is the admin's own player rendered at build time, in public mode. The tree gained `solver.js` `ed9c1c80f2fd`, `admin.css` `70602d9d2d03` and `base.css` `3f02fa5cd666` (CARD-394's Bootstrap stand-in); `solver_state.js` moved `e3ff8f5760f5` to `c8b29135f6e5`, `player.css` `6aa20c7eddc1` to `f27af72c85cd` (it now styles only the two listing pages), `pages.js` `f62fd1a57607` to `90e0ac2733f9`; `tokens.css` unchanged. The puzzle files, `index.json` and the book landing are the curated bundle's, unchanged from the publish above. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-shared-ui-20261109`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. All seven copied files byte-identical to their sources, every `puzzle/<key>.json` carrying exactly `clues`, `height`, `key`, `tier`, `width`, **no JSON anywhere containing the string `solution`**, no goatcounter reference, `.player-site` present, no `.vercel/` in the tree, and no external URL in any served page or script. |
| The injected payload | The generated `play/index.html` fetches its puzzle and injects `{id, width, height, rows, columns, mode: "public"}` — no solution field, and the solved banner's name is set to `Puzzle <key>`, never a picture name (the name IS the answer, FR-044 AC-322/AC-323). |
| Preview | `vercel deploy --yes`: `nonogram-studio-5vzgwxvcu`, Ready in seconds. Three doors 200, unknown path 404, seven hashes matched the local build. |
| Behaviour on the preview | Headless Chromium at 1280x900 on `33fa80994c` (10x10). **What public mode must not offer is absent from the DOM, not merely hidden**: `[data-player-errors]`, `[data-player-progress]` and the Check action each have element count **0**; the page's text contains no "solution"; the solved banner reads `Solved: Puzzle 33fa80994c`. Working: a click marks and Undo clears; zoom 100% to 125% and back; hover crossed 21 elements and 0 after leaving; the hint ladder gave all three rungs (`Hint: look at row 2.`, then `... the 3-run must overlap in the middle ...`, then `Hint: row 2, column 1 is black.`) with the counter at 1; Probe opened, marked one cell (`data-probe="true"`), and Contradiction returned it to `unknown` with no marker left; the save restored row 0 identically across a reload; Reset cleared the board. Clue circles: **0 with a row's runs filled and 3 once its gaps were marked white** — the module's rule, unchanged from the admin's. Marking all 60 filled cells of the solver's grid set `table.is-solved` and `.player-toolbar.is-solved`, showed the banner, and announced `Solved: Puzzle 33fa80994c`. Zero page errors, zero non-GET requests, no host contacted but the site. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created `nonogram-studio-2md4ocijv`, Ready in about 2 s. On `https://nonogram.adverax.io`: three doors 200, `/nope` and `/play.js` 404, the seven hashes unchanged, and the same 60-cell solve run gave the same solved figures with zero page errors. |
| Rollback target | `nonogram-studio-qhh7e0idm` (the bundle-only publish of the same day) and `nonogram-studio-qu83cb3hw` (the probe build) both still Ready. A rollback was not tried. |

Not observed: a real phone (the fourteen findings cards are mostly about phones, and none of them has merged), the brush *menu* on a touch screen, any counting, and Auto-Deploy's dashboard state.

**What this publish leaves owed.** CARD-400 to CARD-413 are the known gaps, now live rather than held. And two documents describe the player this publish retired: `docs/how-it-works/01-domain/puzzle-creation/11-the-public-player.md` and `docs/qa/public-player-test-cases.md`, both written against `play.js` on 2026-11-06 and committed on 2026-11-09, a day after CARD-399 deleted it. Each now carries a banner saying so; neither has been rewritten.

**The how-to-solve publish, 2026-11-10. A fifth door, and the site gained a page that is not a puzzle.** Published from `main` at `65344aed`, carrying the same curated bundle as the two publishes above (`build/player-bundle`, untouched since 2026-11-09).

| Step | What was observed |
| --- | --- |
| What changed against production | Three cards' worth. **CARD-419 adds `/how-to-solve`**, a site-wide five-step wizard with a guided 5x5 and a probe demo — a **fourth rewrite in `vercel.json`** and two new served files (`how-to-solve/index.html`, `how-to-solve.js` `55cf1db08571`). **CARD-418 rebuilds the book landing**: picture squares in sections by level, per-puzzle progress, a jump box and a "continue where you stopped" card. **CARD-402** gives landscape phones the toolbar as a vertical column. By file: `solver.js` `ed9c1c80f2fd` to `dfde50312a45`, `solver_state.js` `c8b29135f6e5` to `68762fc3c389`, `admin.css` `70602d9d2d03` to `5053cc6dfced`, `pages.js` `90e0ac2733f9` to `a04109dc994a`, `player.css` `f27af72c85cd` to `431ed27cc487`; `tokens.css` and `base.css` unchanged. The puzzle files, `index.json` and the book landing's data are the same curated bundle. |
| Where the book landing's pictures come from | **The reader's own saved board, never the site** — `player/pages.js`'s `boardPicture` draws from the `nonogram-public:<key>` entry, and the served `book/<slug>.json` still carries only `height`, `key`, `tier`, `width` per puzzle. A solved square showing a picture is therefore this device's record of its own play, which is what makes the feature compatible with ADR-0041/R2 at all. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261110`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. All **eight** copied files byte-identical to their sources, every `puzzle/<key>.json` carrying exactly `clues`, `height`, `key`, `tier`, `width`, no JSON anywhere containing the string `solution`, **no external URL in any served page, script or stylesheet**, no goatcounter reference, `.player-site` present, no `.vercel/` in the tree. |
| Preview | `vercel deploy --yes`: `nonogram-studio-qsp8eryj7`, Ready in seconds. **Five** doors now: `/library`, `/how-to-solve`, `/play/<key>`, `/b/<slug>` and the puzzle file all 200, an unknown path 404, and the eight hashes matched the local build. |
| Behaviour on the preview | Headless Chromium at 1280x900. `/play/33fa80994c`: public mode carries **no** error-count, progress or Check element (count 0 each), no "solution" in the page text, and marking all 60 filled cells of the solver's grid matched the solution exactly, showed the banner and set both `.is-solved` locks. `/b/bc271a1524`: **160 squares, 159 `new` and 1 `solved`** — the one just played — with exactly **1** picture drawn, the book's title, and the jump box present. `/how-to-solve`: 5 steps with 5 dots walked 1 to 5 by its own `.hts-next` control, 3 brushes, 3 levels, a 25-button guided board whose first tap went `unknown` to `filled` with the coaching line ("Tap a square to make it black. Row 3 says 5..."), and a 25-button probe demo. Zero page errors, zero non-GET requests, no host contacted but the site, across all three pages. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created `nonogram-studio-hwokhvuou`, Ready within a minute. On `https://nonogram.adverax.io`: five doors 200, `/nope` 404, all eight hashes as built, and **both behavioural runs repeated against the live domain gave the same figures** (160 squares / 159 new / 1 solved / 1 picture; the wizard walked 1 to 5; the guided tap marked; zero page errors, zero non-GET). |
| Rollback target | `nonogram-studio-2md4ocijv` (the shared-UI publish) and `nonogram-studio-qhh7e0idm` (the bundle-only one) both still Ready. A rollback was not tried. |

Not observed: a real phone — CARD-402's landscape column is the one change here most about phones, and it was exercised only at 1280x900 — the wizard on a touch screen, any counting, and Auto-Deploy's dashboard state. CARD-400 was `in_progress` and is not in this build; CARD-401 and CARD-403..413 are still `ready`, so the known gaps remain live.

**The festive-solve publish, 2026-11-10 (the day's second).** Published from `main` at `8ffa7194`, same curated bundle. One card: **CARD-280**, the solved board becoming the picture — plus its post-merge follow-up, which is the interesting half.

| Step | What was observed |
| --- | --- |
| What changed against production | `solver.js` `dfde50312a45` to `77a022299425`, `solver_state.js` `68762fc3c389` to `1ea4d93d17c2`, `admin.css` `5053cc6dfced` to `3c137f6e16d2`. Everything else — `tokens.css`, `base.css`, `pages.js`, `player.css`, `how-to-solve.js`, the puzzle files, the index and the book landing — byte-identical to the publish three hours earlier. `COPIED_FROM_ADMIN` is still the same four files: the reveal added no served file. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261110b`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. Eight copied files byte-identical to their sources, five served fields on every puzzle file, no JSON holding the string `solution`, no external URL in any served page or script, `.player-site` present, no `.vercel/`, no goatcounter. |
| Preview | `vercel deploy --yes`: `nonogram-studio-127s6860i`. Five doors 200, unknown path 404, eight hashes matched. |
| Behaviour: the reveal fires once, and only on the last cell | Headless Chromium, 10x10 `33fa80994c`. The CSS custom property --player-wave resolves on a cell (the sweep's per-cell delay). **One cell short of solved: `is-celebrating` false, `is-solved` false** — nothing fires early. On the last click: `is-celebrating` **true**, `is-solved` true, cells computing `animation-name: player-solved-flash`, banner `Solved!`. **After a reload the board is still `is-solved` but `is-celebrating` is false** — the celebration is one-shot and a reload does not replay it. |
| Behaviour: the follow-up, measured by colour rather than by class | `8605a5e9` ("no crosshair band across the solved picture") does **not** remove `.is-crossed` — it repaints it, so the class count is the wrong instrument. Hovering the solved picture leaves **21 `.is-crossed` elements** and the band is nonetheless invisible: a crossed cell's computed background **equals** a plain cell's, `rgb(28, 35, 51)` for filled and `rgb(255, 253, 248)` for unknown. Pressing **Show grid** brings the worksheet and the band back — crossed `rgb(241, 235, 221)` against plain `rgb(255, 253, 248)`. That is the rule's own `:not(.is-showing-grid)` condition, exercised both ways. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created `nonogram-studio-k4z5mb8sh`. On `https://nonogram.adverax.io`: five doors 200, `/nope` 404, the eight hashes as built, and **both runs repeated against the live domain gave identical figures** — one-cell-short quiet, celebration on the last cell, no replay after reload, 21 crossed and both colour equalities true, band back with the grid shown. Zero page errors, zero non-GET requests, no other host, on every run. |
| Rollback target | `nonogram-studio-hwokhvuou` (the how-to-solve publish of the same day) still Ready. A rollback was not tried. |

Not observed: a real phone, the sweep's timing by eye (it is proven by the computed `animation-name` and the one-shot class, not by watching), any counting, and Auto-Deploy's dashboard state. CARD-400 was still `in_progress` — its test set held the full-suite lock during this publish — and CARD-401 and CARD-403..413 remain `ready`.

**The book-theme publish, 2026-11-10 (the day's third). The theme code is live and no theme shows — by the bundle's date, not by a defect.** Published from `main` at `d80ed5c5`, with the 2026-11-09 curated bundle unchanged. One card: **CARD-420** (a book's theme dresses its landing and the puzzles opened from it) and its case-insensitive follow-up.

| Step | What was observed |
| --- | --- |
| What changed against production | `tokens.css` `979ab7a50e43` to `41cd8c918f84` — its **first** change since the site was first deployed, because the themes are `:root[data-theme=...]` blocks in it — `pages.js` `a04109dc994a` to `950a317c20b1`, `player.css` `431ed27cc487` to `23cbedd204db`. `solver.js`, `solver_state.js`, `admin.css`, `base.css` and `how-to-solve.js` byte-identical to the publish four hours earlier, so `/play/<key>`'s own behaviour is untouched by this build. |
| **The served book file gained three fields, and one of them is empty for a reason worth recording** | `SERVED_BOOK_SCHEMA` is now `authors, puzzles, series, slug, theme, title`. CARD-418 extended R2's third exemption from the title alone to `title, series, authors` — the owner asked for them on the landing on 2026-11-10, each costing what the title costs, and the PUZZLE title stays forbidden. **The bundle on disk predates all of it**: `build/player-bundle`'s book file carries only `puzzle_keys`, `slug`, `title`, so the assembler fills `series`, `authors` and `theme` with empty strings. Measured on the live landing: `data-theme` is `''`, and neither Series nor Authors appears. **A Christmas-themed landing therefore needs a fresh bundle export from the panel** (ADR-0041/R5: an explicit owner action), with the book's stored `theme` set — `book_manager.BOOK_THEMES` is the vocabulary and `player_bundle.BOOK_FILE_FIELDS` now carries the field, so the exporter will pass it through. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261110c`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. Eight copied files byte-identical to their sources, five served fields on every puzzle file, no JSON holding the string `solution`, no external URL in any served page or script, `.player-site` present, no `.vercel/`, no goatcounter. |
| Preview | `vercel deploy --yes`: `nonogram-studio-9fpt0xz7x`. Five doors 200, unknown path 404, eight hashes matched. |
| Behaviour on the preview, and again on production | The landing's 160 squares now link **`/play/<key>?book=<slug>`**, which is how a puzzle learns which book it was opened from; following one fetched exactly two files, `book/<slug>.json` and `puzzle/<key>.json`, both the site's own. On that page: `data-theme` `''` (the empty theme is inert, not broken), 100 cells, a click marks, and public mode still carries no error-count, progress or Check element. `/library` drew its 160 tiles with 2 filter controls after the `pages.js` change; `/how-to-solve` still has its 5 steps and its guided board marked on the first tap. Zero page errors, zero non-GET requests, no other host, on every run. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created `nonogram-studio-ilkutodkg`. Six doors checked 200 (`book/<slug>.json` included), `/nope` 404, eight hashes as built, and both runs above repeated against `https://nonogram.adverax.io` with identical figures. |
| Rollback target | `nonogram-studio-k4z5mb8sh` (the festive-solve publish) still Ready. A rollback was not tried. |

Not observed: a themed landing at all (see above — it needs a re-export), a real phone, any counting, and Auto-Deploy's dashboard state. CARD-400 remains `in_progress`; CARD-401 and CARD-403..413 remain `ready`.

**The themed-landing publish, 2026-11-11. A fresh export, and the theme arrives.** Published from `main` at `041f05d9` with a bundle exported from the panel against the production database the same morning. This is the publish the 2026-11-10 record said was needed.

| Step | What was observed |
| --- | --- |
| What the new bundle changed | `theme` is now **`christmas`** where the 2026-11-09 export carried the field not at all. The book also **moved address again**: one puzzle was swapped at position 7 (`7dfb93e055` out, `08642cb1b2` in), so R7's hash of the ordered keys gives **`/b/0a958d036e`** where production served `/b/bc271a1524`. On the live site `book/bc271a1524.json` is now 404 (the old address gets the unknown-book soft landing) and `puzzle/7dfb93e055.json` is 404 while `puzzle/08642cb1b2.json` is 200. Still 160 puzzles and one book. |
| **`series` and `authors` came out empty: `player_bundle` read the wrong object** | The production row has `series_name` = "Anna & Olga's Ultimate Puzzle Selection" and `authors` = "Anna and Olga" (read directly from the database that morning), and the export wrote `""` for both while `theme` came through. **Cause, after a wrong first answer** — this record first said two row-to-`Book` converters disagreed, which is false; `_row_to_book` sets all three lines correctly: `series_name` and `authors` are fields of the **`Book`** dataclass, `theme` is a field of its **`BookMetadata`**, and `player_bundle._book_line` read all of them off `book.metadata`. So the two lines were always `None` there and always served `""`, and `theme` worked and hid it. `book_pdf_generator` and `book_create.html` both read the lines off the book, which is what settles where they live. Fixed the same day (`BOOK_LINE_HOMES`, below). |
| Which code was published | `main` had moved since the 2026-11-10 publish: `pages.js` `950a317c20b1` to `edbe33119eaf`, `player.css` `23cbedd204db` to `0835badaab4f`. The other six copies unchanged, so `/play/<key>`'s behaviour is the festive-solve build still. CARD-421 (the Christmas book's garland and snow) and the folio/contents work in that range are the printed interior, not this site. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261111`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. Eight copied files byte-identical to their sources, five served fields on every puzzle file, no JSON holding the string `solution`, no external URL in any served page or script, `.player-site` present, no `.vercel/`, no goatcounter. The previous bundle was copied to `build/player-bundle.pre-20261111` before the export overwrote it. |
| Preview | `vercel deploy --yes`: `nonogram-studio-j6fioar26`. Five doors 200, the new book JSON 200 and the old one 404, unknown path 404, eight hashes matched. |
| Behaviour on the preview, and again on production | **`data-theme` is `christmas` on the landing AND on a puzzle opened from it** — the `?book=<slug>` link is what carries it, and following one fetched exactly two files, both the site's own. 160 squares, the book's title, no Series or Authors line (empty, as above). Play: 100 cells, a click marks, public mode still carries no error-count, progress or Check element. The festive solve still fires on the last cell only, with the banner, both locks and no replay after a reload. `/library` 160 tiles with 2 filter controls; `/how-to-solve` 5 steps and a guided board that marks on the first tap. Zero page errors, zero non-GET requests, no other host, on every run. |
| Production | `vercel promote <the preview URL> --scope <team> --yes` created `nonogram-studio-1p6esk90l`. On `https://nonogram.adverax.io`: the doors as above with the same 200/404 pattern, `pages.js` at the built hash, and both runs repeated with identical figures. |
| Rollback target | `nonogram-studio-ilkutodkg` (the book-theme publish) still Ready — but note it serves the OLD bundle, so a rollback also rolls the book's address back to `bc271a1524`. |
| **The fix, and why no test caught it** | `player_bundle.BOOK_LINE_HOMES` now names each line's home (`series_name` and `authors` on the book, `theme` on its metadata) and `_book_line` raises on a field it does not know, so "not set" and "I looked in the wrong object" can no longer be spelled the same way. **The test could not have caught it: its own independent oracle read the lines off `book.metadata` too** — the same wrong place as the code it checks — so a served `""` matched an expected `""`; and no corpus book had either line set, so the scan had nothing non-empty to carry. Both halves are fixed: the oracle resolves each line's home from the dataclasses themselves (`dataclasses.fields`, so a field moved between them reds the hand-written map), and one of the three corpus books now carries a stored series and author line while the others stay unset. Two plants confirmed the control: the pre-fix read reds `test_bundle_is_clean_of_answers` naming both lines, and a wrong home for `theme` in the map reds five tests. 0 tests added — one oracle and one fixture changed. |

Not observed: a real phone, the theme's look by eye (`data-theme` is asserted, the garland is not), any counting, and Auto-Deploy's dashboard state. CARD-400 remains `in_progress`; CARD-401 and CARD-403..413 remain `ready`.

**The series-and-authors publish, 2026-11-11 (the day's second). Two exports, because a running panel does not reload.** Published from `main` at `578b2a29` — the fix of the same morning — with a bundle re-exported after it.

| Step | What happened |
| --- | --- |
| **The export that did not take** | The owner re-exported at 12:29, after the fix had landed at about 12:15, and the bundle still carried `series: ""` and `authors: ""`. The panel had been started at 11:41 with --no-reload (the panel's flag), so the process still held the **pre-fix** `player_bundle` module: a source fix does not reach a running panel. The panel was restarted, the loaded module checked for `BOOK_LINE_HOMES`, and the export route posted again — one POST, read-only against the database (EC-049). **Worth remembering: after any change under `src/`, restart the panel before trusting an export.** |
| What the bundle then carried | `series` = "Anna & Olga's Ultimate Puzzle Selection", `authors` = "Anna and Olga", `theme` = `christmas`, 160 keys. **The slug did not move** (`0a958d036e`): the print order was unchanged, so the book keeps the address the earlier publish gave it. |
| Which code was published | Unchanged from the publish 31 minutes earlier — all eight copied files byte-identical to their sources and to what production was already serving. **This publish is the bundle and nothing else.** |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261111b`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. Five served fields on every puzzle file, no JSON holding the string `solution`, no external URL in any served page or script, `.player-site` present, no `.vercel/`. |
| Preview, then production | `vercel deploy --yes` gave `nonogram-studio-o152gk44w`; `vercel promote` created **`nonogram-studio-8cibfqpfn`**. Five doors 200, unknown path 404, on both. |
| **How the lines render, and a check of mine that lied** | The served JSON carries both lines on the live domain. The landing's header is `<p class="book-series">` with the series, the `<h1>` title, and a byline `by Anna and Olga · 160 puzzles`. A first check reported the series **missing**, because it compared exact case against `innerText` and `.book-series` is `text-transform: uppercase` — Chromium's `innerText` returns rendered text, so the compare failed on a line that was plainly there. Re-measured through `textContent` and through the computed `text-transform`: present, one element, uppercased by CSS. The assertion was wrong, not the page. |
| Everything else, on production | `data-theme` `christmas` on the landing and on a puzzle opened from it; following a square fetched exactly its book JSON and its puzzle JSON; 100 cells, a click marks, public mode still carries no error-count, progress or Check element; no picture name anywhere on the play page; `/library` 160 tiles; `/how-to-solve` 5 steps marking on the first tap. Zero page errors, zero non-GET requests, no other host. |
| Rollback target | `nonogram-studio-1p6esk90l` still Ready. It serves the same code and the previous bundle, so a rollback keeps the address and loses only the two lines. |

Not observed: a real phone, any counting, Auto-Deploy's dashboard state. CARD-400 remains `in_progress`; CARD-401 and CARD-403..413 remain `ready`.

**The tap-target publish, 2026-11-11 (the day's second).** Published from `main` at `90ad2023`, same curated bundle as the two publishes above. One card, **CARD-423**: the compact toolbar's tap-target floor is 44 px in **both** dimensions, where it had been written in width alone. Asked for as "deploy the card — and everything else", so this is the whole of main, not a cherry-pick.

| Step | What was observed |
| --- | --- |
| What changed against production | One declaration, and nothing else in any served file. `admin.css` `5053cc6dfced` to **`5a4dab0fb59b`**: the compact block (`@media (max-width: 600px), (max-height: 500px)`) gained `.player-toolbar .btn { min-height: 44px; }`, plus comment prose. `solver.js`, `solver_state.js`, `tokens.css`, `base.css`, `player.css`, `pages.js`, `decor.css`, `decor.js` and the whole bundle are unchanged. The merge is `40f12185`; review 8.5 at cycle 3 of 3, nothing gating. |
| What the floor was before | Measured on production the day before: **nine controls at 44 x 36** — the brush trigger, Region, Undo, Redo, Reset, Hint, `-`, `+`, Probe — except the two zoom steppers, which were 44 x 38.78 (their glyph's line box). The compact block set `min-width: 44px` and no height floor, so the height fell through to `.player-toolbar .btn`'s `min-height: var(--control-h)` = 36px. `.player-zoom-readout[role="button"]` already carried `min-height: 44px` in that same block, and CARD-402's landscape block already set both — which is why the same sweep found no landscape control under 44 px. The floor was written in one dimension, and this publish is the other one. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-tap-targets-deploy`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. All five `COPIED_FROM_ADMIN`-class files byte-identical to their sources (`solver.js` `77a022299425`, `solver_state.js` `1ea4d93d17c2`, `admin.css` `5a4dab0fb59b`, `tokens.css` `41cd8c918f84`, `base.css` `3f02fa5cd666`), the floor present once in the served stylesheet, every one of the 160 `puzzle/<key>.json` carrying exactly `clues`, `height`, `key`, `tier`, `width`, no served file holding the string `solution`, no goatcounter reference, no `.vercel/` directory, and the only external URL anywhere in the tree being `vercel.json`'s own `$schema` (not a runtime fetch). |
| Preview | `vercel deploy --yes`: **`nonogram-studio-3dug1dt9e`**, Ready in about 30 s. Five doors 200 (`/library`, `/play/<key>`, `/b/0a958d036e`, `/how-to-solve`, the puzzle file), unknown path 404, five hashes matched the local build. **A note for the next publish: the deploy command's output was piped through `tail -6`, which threw the deployment URL away.** It was recovered with `vercel ls`; do not pipe that command through `tail`. |
| Behaviour on the preview | Headless Chromium under iPhone emulation (390x844 and 844x390, touch, DPR 3). **Nine controls drawn, zero under 44 px, every height exactly 44, at both orientations.** No horizontal page scroll, zero page errors. |
| **Two non-GET requests on the PREVIEW, and what they were** | The preview reported 2 non-GET: `POST https://vercel.live/login/validate?hostname=…&deploymentId=…` and a `HEAD` of the play page. That is **Vercel's own preview toolbar**, injected by the platform into preview deployments — not in our tree, and `vercel.live` is a third-party host the site's self-containment rule forbids. It appeared under the iPhone user agent and not without it (7 requests, 0 non-GET). Production was then measured rather than assumed: **0 non-GET under both user agents, 7 requests, no host but the site**. The rule holds where it is asserted; the preview toolbar is the platform's and is not published. |
| Production | `vercel promote <the preview URL> --scope et0175s-projects --yes` created **`nonogram-studio-2pwp1thd9`**, Ready in seconds. On `https://nonogram.adverax.io`: five doors 200, `/nope` 404, all five hashes as built, the floor present once in the served `admin.css`. |
| Behaviour on the live domain | The same run repeated: **nine controls, zero under 44, all heights 44, portrait and landscape**; no horizontal page scroll; **zero page errors and zero non-GET**; 7 requests, one host. The landing still carries `data-theme` `christmas` with 160 `.square` tiles and the garland and snow drawn (4083 decor nodes); `/how-to-solve` still 6 sections. |
| A check of mine that lied, again, and the lesson is the same one | A first landing check reported **0 squares**, which would have been alarming: it queried `.book-square`, and the tiles are `.square` (`a[href^="/play/"]` is 160, `first_play_link_classes` is `tile square`). Same class of error as the 2026-11-11 `innerText` case recorded above — my selector was wrong, not the page. Measure the DOM before believing a zero. |
| Rollback target | `nonogram-studio-8cibfqpfn` (the series-and-authors bundle publish) still Ready. It serves the same bundle and the pre-floor stylesheet, so a rollback keeps every address and loses only the 44 px height floor. |

Not observed: **a real phone — and this publish is specifically about thumbs**, so the emulation is geometry and not a verdict on feel; the brush menu's own options on a touch screen (142 x 36 px in the bundle this row publishes, the one tap target that floor does not reach — CARD-424, `ready` at the time, carried that decision and deliberately no default; the owner ruled **"44 px, like the rest"** on 2026-11-11 and CARD-424 raised them, so a bundle published after it serves 142 x 44 options in a 206 px popover); any counting; Auto-Deploy's dashboard state. **CARD-400 and CARD-401 and CARD-403..413 are all `done` as of this publish** — the fourteen findings cards the shared-UI publish of 2026-11-09 left live rather than held are closed, which the earlier records above, written while they were open, do not say. CARD-424 is the only player card now `ready`.

**The play-test publish, 2026-11-12. Three of the owner's seven findings.** Published from `main` at `0d1a3430`, same curated bundle (`build/player-bundle`, untouched since 2026-11-09). The owner read the live site on their own phone on 2026-11-11 and wrote seven findings into a Google Doc; five were reproduced on production before any card was cut, and three of those have merged. **Two of the five — CARD-424 (the brush menu's own options at 44 px) and CARD-427 (the hint and probe message centred) — are NOT in this publish**: their gates were still running when the owner asked for it, and the owner chose three now over five in an hour.

| Step | What was observed |
| --- | --- |
| What changed against production | Three cards. **CARD-425** removes "Browse the library" from the `/b/<slug>` not-found panel, sweeps the then-dead `.pages-library-link` rule, and retracts the three statements that still promised the link (AC-388's `then:`, `book.html`'s header comment, `components.md`'s PagesNotFound entry). **CARD-426** makes the brush menu dismissable — a document capture-phase `pointerdown` calling `closeMenu()` — and, on the owner's ruling of the same day, leaves the box opaque so its own chrome swallows the tap. **CARD-428** gives the landscape zoom group its own two-column grid so the steppers stay a pair. By file: `solver.js` `dfde50312a45` → **`0607f28f0187`**, `admin.css` `5a4dab0fb59b` → **`49666273bb51`**; `tokens.css`, `base.css`, `solver_state.js`, `player.css`, `pages.js` and the whole bundle unchanged. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261112`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. All five `COPIED_FROM_ADMIN`-class files byte-identical to their sources, every `puzzle/<key>.json` carrying exactly `clues`, `height`, `key`, `tier`, `width`, no served file holding the string `solution`, no goatcounter reference, no `.vercel/` directory. |
| Preview | `vercel deploy --yes`: **`nonogram-studio-a9xwgws4z`**. Five hashes matched the local build; five doors 200, `/nope` 404. |
| Behaviour on the preview, then repeated on the live domain | **CARD-425:** `/b/deadbeef99` shows the panel with **0 anchors inside it** and its own explanation. **CARD-426:** with the menu open at 1440x900 (box `[40, 134, 160, 174]`), a click on the **chrome** closes it and marks nothing — the owner's ruling — a click on an **item** picks that brush (Black → White), and a click **clear of the box** closes it *and* marks (`unknown: 260` → `unknown: 259, filled: 1`). **CARD-428:** at 844x390 and 874x402 the zoom group is two rows with `−` at x 40 and `+` at x 92 **sharing y 240**, the readout spanning 96 px at y 292. |
| Production | `vercel promote <the preview URL> --scope et0175s-projects --yes` created **`nonogram-studio-9an5hs43g`**, Ready within a minute. On `https://nonogram.adverax.io`: the five hashes as built, five doors 200, `/nope` 404, and every behavioural figure above reproduced. |
| **Two probe errors of mine, recorded because a false negative nearly shipped as a finding** | The first behavioural run reported the clear-of-box tap as "closes AND marks" with marks `0 → 0`, which reads as the owner's ruling having broken ordinary marking. It had not. Two faults in the probe, neither in the site: the step before had switched the brush to **White**, while the counter only counted `data-state="filled"`; and the "clear of the box" test compared the **cell's top-left corner** against the menu's rectangle when the click lands at the cell's **centre** — (123, 313) against a box ending at y 308, genuinely clear. Re-run with the brush at rest and any brush state counted, it marks. The lesson is the one this page has recorded twice before: a zero from a selector or a geometry assumption is not a measurement. |
| Rollback target | `nonogram-studio-2pwp1thd9` (the tap-target publish of 2026-11-11) still Ready. It serves the same bundle and the pre-play-test code. |

Not observed: **a real phone** — the owner's seven findings came from one, and these three were verified only under emulation; **the hint message and the menu's own option height are unchanged in this publish** (CARD-427 and CARD-424, both review-clean and gating at the time of writing); any counting; Auto-Deploy's dashboard state.

**What this publish leaves owed.** CARD-424 and CARD-427 need a second publish once they merge — the deploy that carries them is the one where the owner should look at the centred message over a real picture, which no test and no reviewer has eyeballed. Findings 6 and 7 of the Google Doc (the board jumping when the clues are scrolled; "Contradict" discarding a mark with no confirmation when it has scrolled out of view) are **not carded**: neither reproduced under emulation, and the owner's own reproduction steps are owed before an author is given them to re-derive.

**The second play-test publish, 2026-11-12 (the day's second). All five carded findings are now live.** Published from `main` at `149e802c`, same curated bundle. This is the publish the record above said was owed: it carries **CARD-427** (the hint and probe message centred in the viewport) and **CARD-424** (the brush menu's four options at 44 px), the two that were still gating when the owner asked for the first one.

| Step | What was observed |
| --- | --- |
| What changed against the publish three hours earlier | `solver.js` `0607f28f0187` → **`e1baf6066c0e`**, `admin.css` `49666273bb51` → **`2f68f772a86c`**; `tokens.css`, `base.css`, `solver_state.js` and the bundle unchanged. **CARD-427** deletes `placeExplain`, `replaceExplain`, their three call sites, the `.is-top` class and `.player-stage-wrap { position: relative; }` — the strip's old placement machinery — and makes `.player-explain` a contained box centred by layout (`position: fixed; inset: 0; margin: auto`). **CARD-424** adds one declaration, `.player-tool-item { min-height: 44px; }`, plus the two `solver.js` minors CARD-426's review raised (the chrome dismissal's scoped focus restore, and the exemption selector narrowed to `#puzzle-player-tool-menu .player-tool-item`). |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261112b`, no `--analytics`. 160 puzzles, one book landing, `dropped (not in the served schema): title`. All five `COPIED_FROM_ADMIN`-class files byte-identical to their sources; the served `solver.js` carries **zero** occurrences of `placeExplain`, which is CARD-427's deletion reaching the public tree. |
| Preview | `vercel deploy --yes`: **`nonogram-studio-1r60xwipp`**. |
| Behaviour, on the preview and then repeated on the live domain | **CARD-424:** at 390x844 the open menu's box is `[16, 115, 160, 206]` — the +32 px growth — with all four options at **142 x 44**, and it fits the viewport. **CARD-427:** at 1440x900 and 390x844 the message is `299 x 50`, `position: fixed`, centre offset **dx 0, dy 0**, and it clears on the next tap. **21% of the page at 1440x900**, against the 1360 px / 94% the owner's finding complained about; at 390x844 it is 77% of the page but **narrower than the board** (299 against 358), which is the comparison that matters there. |
| Production | `vercel promote <the preview URL> --scope et0175s-projects --yes` created **`nonogram-studio-6obyc8p6m`**, Ready within a minute. On `https://nonogram.adverax.io`: the five hashes as built, five doors 200, `/nope` 404, and every figure above reproduced exactly. |
| Rollback target | `nonogram-studio-9an5hs43g` (this morning's three-card publish) still Ready. It serves the same bundle with the hint strip and the 36 px menu options. |

Not observed, and this is the publish where it matters most: **a real phone, and a rendered eyeball on one of the owner's own pictures.** Every check in both of today's publishes was geometry under emulation. Two things on this build are deliberately drawn **over the picture** and have never been seen on one: the centred message (the owner's ruling, which accepted that it can cover the cells the sentence names), and the solve celebration, which rides the same box for 4 seconds at the moment the picture is revealed — measured at 4.0% of the board at 390x844, 7.7% at 844x390, 3.5% on desktop, never the centre, and dismissible by any tap. The owner ruled to leave it centred with the rest.

**What this publish leaves owed.** CARD-429 (the zoom readout moves after `+`, so landscape focus order follows the eye, at the cost of `− 100% +` becoming `− + 100%` everywhere) is `ready` and unblocked. Findings 6 and 7 stay uncarded pending the owner's reproduction steps.

**The zoom-order publish, 2026-11-12 (the day's third, and the wave's last).** Published from `main` at `aa3243c4`, same curated bundle. One card, **CARD-429**, which the publish above listed as owed. **All six cards of the play-test wave are now live.**

| Step | What was observed |
| --- | --- |
| What changed | `admin.css` `2f68f772a86c` → **`bf012406cb33`** — **comment-only**; the behaviour is in the two templates, which the assembler renders at build time. `solver.js`, `tokens.css`, `base.css`, `solver_state.js` and the bundle are unchanged. The `.player-zoom-readout` span now follows the `in` button in `puzzle_solve.html` **and** in `puzzle_edit.html`, which carried the byte-identical group. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261112c`, no `--analytics`. 160 puzzles, one book landing. All five copied files byte-identical to their sources; **the rendered `play/index.html` carries the group in the order `out, in, readout`**, which is the move reaching the public tree. 160/160 puzzle files with exactly the five served fields, no `solution` anywhere, no goatcounter, no `.vercel/`. |
| Preview | `vercel deploy --yes`: **`nonogram-studio-12n2b6l8w`**. Five hashes matched, five doors 200, `/nope` 404. |
| Behaviour, on the preview and repeated on the live domain | At **844x390, 874x402, 390x844 and 1440x900**: DOM order and drawn order are both `out, in, readout` — they agree at every viewport, which is the whole point of the card, since focus order follows DOM order and CSS cannot change it. Landscape geometry is unchanged (out at x 40, in at x 92, both y 240; readout spanning at y 292), so the steppers stay the pair CARD-428 made them. Desktop and portrait now read `− + 100%`, which is the cost the owner accepted when told that the readout could not move in one layout without moving in the other. |
| Production | `vercel promote <the preview URL> --scope et0175s-projects --yes` created **`nonogram-studio-fh3vjj9o9`**. The live `admin.css` served the previous hash for the first few seconds after the promote returned — worth knowing: **the promote command returning is not the deployment being live**, and the first verification pass caught the old bytes. Re-checked until the hash matched, then every figure above reproduced on `https://nonogram.adverax.io`. |
| Rollback target | `nonogram-studio-6obyc8p6m` (the second play-test publish) still Ready. It serves the same bundle with the retired zoom order. |

Not observed: **a real phone, still.** Three publishes in two days and every behavioural figure in all of them is emulated geometry. The things most worth a human eye remain the ones drawn over the picture — the centred message and the solve celebration — and now also whether `− + 100%` reads naturally to the owner on a desktop, since that order changed on a layout nobody complained about.

**What this publish leaves owed.** Nothing from the carded wave. Finding 7 of the owner's Google Doc — "Contradict" discarding a mark with no confirmation when it has scrolled out of view — was **withdrawn on 2026-11-12**: the owner rewrote that document with a new list of seven findings, which replaced the old one rather than extending it, and ruled the dropped item closed when asked. It was never carded and never reproduced. **Finding 6 is now carded as CARD-432**, reproduced the same day from a different question: the owner asked why the board still scrolls after they stop, and the answer is that it does not — the PAGE does. `.player-stage` computes `overscroll-behavior: auto` and the page has 23 px of slack, so a drag over the puzzle moves the document and keeps gliding when the finger lifts; worse, 104 px of the board is then unreachable by gesture at 175% zoom (stage stuck at 215 of 319, while assigning `scrollTop` reaches 319 at once). `overscroll-behavior` appears exactly once in the stylesheet — on the landscape strip, added by CARD-402 for this same class — and never on the surface a reader actually drags.

**The joined-zoom publish, 2026-11-12 (the day's fourth).** Published from `main` at `a10c5145`, same curated bundle. Two cards, both of which had been sitting merged-but-unpublished: **CARD-430** (the compact zoom as one joined control) and **CARD-431** (the compact portrait title at 20 px). Asked for as "please deploy it", mid-flight on CARD-437, so this is the whole of `main` as it stood — not a cherry-pick, and **not** CARD-437, which is still in its review cycle.

| Step | What was observed |
| --- | --- |
| What changed | `admin.css` `bf012406cb33` → **`9d310cb2f3cc`**. `solver.js` `baa34f4eac8c`, `solver_state.js` `171451de779f`, `tokens.css` `41cd8c918f84` and the bundle all unchanged, so this publish is one stylesheet. |
| Assemble | `scripts/assemble_player_site.py --bundle build/player-bundle --out build/site-20261112d`, no `--analytics` (matching every publish before it). 160 puzzles, one book landing, `dropped (not in the served schema): title`. All four copied files byte-identical to their sources; 160/160 puzzle files carrying exactly `clues`, `height`, `key`, `tier`, `width`; no goatcounter reference, no `.vercel/`, the `.player-site` marker present. |
| Preview | `vercel deploy --yes`: **`nonogram-studio-dgednoj95`**. Its `admin.css` and `solver_state.js` matched the local tree byte for byte, `/library`, `/play/<key>`, `/b/<slug>`, `/puzzle/<key>.json` and `/how-to-solve` all 200, and the preview's puzzle file carried the same five fields. |
| Behaviour, measured on the live domain after the promote | **Portrait 390x844:** the zoom group is one control — 140x44 at (16, 103), `display: flex`, **one** row, `border-radius: 22px`, a box-shadow ring rather than a border, and the gaps between its three members are **0 and 0**, which is what "joined" has to mean to be true. Members `−` 44x44, `+` 44x44, readout 52x44, so CARD-423/424's 44 px floor survives the join. The title computes **20px** (CARD-431). **Landscape 844x390:** the same control as a 96x88 **grid** of two rows — `−` and `+` side by side at 48x44 each, the readout spanning 96x44 below, radius 12px — i.e. CARD-428's arrangement, now joined. Title 16px there, unchanged. |
| Production | `vercel promote <the preview URL> --scope et0175s-projects --yes`. Verified on `https://nonogram.adverax.io` rather than trusting the command's return (the publish above is why): live `admin.css` reads `9d310cb2f3cc`, the stylesheet carries three `CARD-430`/`CARD-431` comments, and the four doors answer 200. |
| Rollback target | `nonogram-studio-fh3vjj9o9` (the zoom-order publish) still Ready. It serves the same bundle with the three zoom controls separate and the 30 px portrait title. |

**CORRECTION to this record, written 2026-11-12 within the hour, by its own author.** This record said "Two cards" and "this publish is one stylesheet". **Both are false.** The publish also carried **CARD-439** — *"A big puzzle on a phone can be solved one row or column at a time, in big cells"*, the owner's own project-thread request of the same day, merged on their go-ahead (`1192a889`) with no review cycle — which the other session landed on `main` shortly before I assembled. It is 1080 added lines across `admin.css` (+87), `solver.js` (+460) and `solver_state.js` (+55), so the publish shipped a whole new mode, not a stylesheet.

The real before/after, measured after the fact against the rollback deployment `nonogram-studio-fh3vjj9o9`:

| File | before this publish | after |
| --- | --- | --- |
| `admin.css` | `bf012406cb33` | `9d310cb2f3cc` |
| `solver.js` | **`e1baf6066c0e`** | **`baa34f4eac8c`** |
| `solver_state.js` | **`1ea4d93d17c2`** | **`171451de779f`** |

**How the error was made, because the shape of it matters more than the figures.** Every check in the table above compared a file in the assembled tree with its source in the repo, and then with the same file on the preview — i.e. it proved the COPY was faithful, which is what `COPIED_FROM_ADMIN` needs. Only `admin.css` was also compared **before-and-after on the live domain**. For `solver.js` and `solver_state.js` the word "unchanged" was asserted from the local hashes alone, and a local hash cannot say what production was serving an hour earlier. A faithful copy of a changed file is still a changed file. **The check that was missing is the cheap one:** read the live hashes BEFORE promoting, not only after.

CARD-439 is live and was verified present (seven `CARD-439` references in the served `solver.js`, its marker in the served stylesheet) but **its behaviour was not exercised by this session at all** — no tap, drag or long-press of the new line mode, on any viewport. It carries no review score by design (merged on the owner's go-ahead), so nothing upstream of the publish exercised it either.

**A correction to the publish records above, not to the tree.** Three of them state "no `solution` anywhere" or "no served file holding the string `solution`" among the pre-publish checks. That sentence is **over-broad as written** and will raise a false alarm for the next person who runs it as a check: the assembled tree has always held the *identifier* `solution` in five files — `solver_state.js` (73 occurrences) and `solver.js` (42), which derive the solution from the clues at runtime because that is how Hint works; `how-to-solve.js` and `how-to-solve/index.html`, which ship their own tutorial puzzle; and one mention in `pages.js`. The property actually worth checking, and the one verified at every publish including this one, is narrower: **no puzzle data file carries a solution** — all 160 `puzzle/<key>.json` hold exactly the five served fields. Nothing about the tree changed; the check's wording did.

**Not observed: a real phone, for the fourth publish running.** Every behavioural figure above is emulated geometry, and the two cards in this publish are purely about how something looks in the hand. Whether a 22 px pill reads as one control, and whether a 20 px title still reads as a title, are questions a screenshot answers badly.

**What this publish leaves owed.** **CARD-432** (the board hands its scroll to the page — the fling that carries on, and 104 px of board unreachable at 175% zoom) is `ready`, P1, and unstarted: it is a live defect on the site this publish just updated. **CARD-437** (the book page showing stale progress after a Back) is mid-review and NOT in this publish, so returning from a puzzle still shows the book as it was before you played. **CARD-433 to CARD-436 and CARD-438** are `ready` and unstarted — the four rulings of 2026-11-12 (Region sticky while the board fits; circles needing a closed run; the probe silent until Hint; the way back to the book) plus the two-row portrait toolbar.

**The line-focus publish, 2026-11-12 — asked for, and found already live.** The request was to publish `main` for **CARD-439** (line focus mode: a big puzzle solved one row or column at a time on a phone). Before assembling, the check found nothing to publish: merge `1192a889` is an ancestor of `a10c5145`, so CARD-439 went out **with the joined-zoom publish above**, and the only commit on `main` since is that publish's own record. No new deployment was made — a promote of identical bytes would add a production deployment and change nothing.

| Step | What was observed |
| --- | --- |
| What production serves | `https://nonogram.adverax.io` → **`nonogram-studio-1196mrvzr`** (Ready, created 15:47 +0200, the joined-zoom promote). Live hashes equal the sources on `main`: `solver.js` `baa34f4eac8c` (carries `buildLineView`), `solver_state.js` `171451de779f`, `admin.css` `9d310cb2f3cc`, `tokens.css` `41cd8c918f84`, `base.css` `3f02fa5cd666`; the live `/play/<key>` and `/library` pages equal `build/site-20261112d`'s byte for byte. |
| Doors | `/library`, `/play/<key>`, `/b/<slug>`, `/how-to-solve`, `/puzzle/<key>.json` all 200; `/nope` 404. |
| Behaviour on the live domain | Headless Chromium, 390x844, touch, on the 30x30 `/play/52603b6dee`: one **Line** button, 44x44, visible; tapping it opens the `#puzzle-player-line` dialog (`aria-expanded` true) titled "Row 1 of 30", with the row's clue, the mini-map, the two 15-cell strips and the brush tools; no page error. At 1440x900 the button stays hidden. |

**A correction to the joined-zoom record above.** Its "What changed" row says `solver.js` and `solver_state.js` were unchanged, so the publish was "one stylesheet". Both had changed — `solver.js` `e1baf6066c0e` → `baa34f4eac8c`, `solver_state.js` `1ea4d93d17c2` → `171451de779f` (read from `build/site-20261112c`) — because that tree carried CARD-439. The hashes it lists were right; the "unchanged" was carried from the publish before rather than compared against it.

Not observed: a real phone, for the fifth publish record running — and line focus is the feature most about the hand: the long-press to open a line and a drag along the strip.

## Publishing a new bundle

Nothing here is automatic, and that is deliberate: per ADR-0041/R5 a bundle export is an
explicit owner action and never a side effect of finalising a book or exporting a PDF.

1. In the admin panel, press **Export player bundle**. It is read-only against the
   database (EC-049) and writes a bundle directory.
2. Assemble the site:

   ```bash
   ./.venv/bin/python scripts/assemble_player_site.py \
       --bundle build/player-bundle --out build/site --analytics
   ```

   The helper is a thin driver: it reads the analytics endpoints and nothing else out of
   *this page*, then delegates every byte of the assembling to `player/assemble.py`.
   **`--analytics` is the flag that makes this a counted tree, and it is opt-in**: a bare
   run writes no snippet at all, which is what a local run and every test fixture want
   (see drift step 4 — the safe side is the default, not a flag to remember). Pass
   `--print-only` to see the delegated command line without running it.
3. Deploy the tree — one command, and it is in "Deploying the tree" below. That
   section exists because of the two things which are *not* one command: a project link
   that cannot live inside the tree, and a git-driven deploy that cannot see the tree at
   all.

The output directory **is** the site: one directory holding the pages, the two
byte-identical copies from the panel (`solver_state.js`, `tokens.css`), `vercel.json`,
the rebuilt `puzzle/<key>.json` files, the rebuilt `index.json` and `book/<slug>.json`,
and a `.player-site` marker. Assembling into a directory deletes it first, and the
marker is what the assembler recognises its own output by, so a directory it did not
write is refused.

### Deploying the tree

Observed on this machine on **2026-10-29** (CARD-285): Vercel CLI 59.11.7 is installed,
`vercel whoami` answers *"The specified token is not valid"*, and the checkout holds no
`.vercel/` directory — so the first publish from here begins with a `vercel login`, and
no project has ever been linked from this repository.

```bash
cd build/site && vercel deploy --prod
```

The assembled tree **is** the deploy root. It carries its own `vercel.json`, so the three
rewrites travel with the files that need them and are not a dashboard setting somebody
has to keep in step — which is the same argument the allow-list below is built on.

**Why not a git-driven deploy of the same tree.** This rules out one half of the choice
this page used to leave open ("or let the dashboard's Output Directory point at it"):
`build/` is ignored, `git check-ignore -v build/site` answers `.gitignore:7`, so the
tree is in no commit and a git deploy would publish a project with no site in it. Every
file that makes the site — the pages, the rebuilt `puzzle/<key>.json`, the two
byte-identical copies from the panel — is written into the output directory, and none of
them is tracked there. Committing the output instead would put a second copy of
`solver_state.js` and `tokens.css` in the repository, which is precisely the drift
ADR-0041/R3's build-time-copy rule exists to prevent. `TODO(owner): record what the
project's Git integration and Output Directory are actually set to` — the repository
rules out one wiring; which one the dashboard is configured for is still a fact only the
dashboard has.

**Why not `vercel deploy --prebuilt`.** An earlier revision of this page named that
command and it is the wrong one. The CLI's own help for 59.11.7 reads *"Use in
combination with `vc build`. Deploy an existing build"*: the flag uploads the
`.vercel/output` tree that `vercel build` writes, in Vercel's Build Output API layout.
`player/assemble.py` writes neither of those. It writes a plain static tree with a
`.player-site` marker, because per ADR-0041/R3 "building" this site is copying and there
is no toolchain to run. Read out of the help text on the date above, not out of a
deploy — nothing in this repository has deployed yet, and this page does not claim
otherwise.

**The project link cannot live in the output directory.** `vercel deploy` records the
project's identity in `.vercel/project.json` beside the files it deploys, and the
assembler calls `shutil.rmtree` on its output directory before writing a byte — so a
link stored in `build/site` is gone with the next bundle, and the publish after it
prompts to link again. Either answer that prompt every publish, or keep the identity
outside the tree, where a rebuild cannot reach it:

```bash
export VERCEL_ORG_ID=team_p379UJJnEKFQ9nJC15tzcTyp
export VERCEL_PROJECT_ID=prj_9SoVGUETjWldt1HN3CwrC8GCZbF1
cd build/site && vercel deploy --prod
```

Those are this project's real ids, and they are the same two values "What production is"
records above — read from the `.vercel/project.json` the first deploy wrote (`orgId`
and `projectId`), which is the file the variables stand in for. An earlier revision of
this block left them as `...` with a note to fetch them from the dashboard, and kept
that note after the deploy had already recorded both: the page was sending a reader to
look up something it was holding two sections higher. They are **not** secrets — an id
names a project, it does not authorise anything; the credential is the CLI login, which
lives in `~/.local/share/com.vercel.cli` and never belongs in a published tree (the same
reason `vercel link`'s `.env.local`, which carries a real `VERCEL_OIDC_TOKEN`, is
deleted before any upload — see the deploy record above).

The 2026-10-30 deploy did **not** test these two variables: it ran with a live
`.vercel/project.json` in the tree, so the variables were never the thing being read.
**The 2026-11-05 publish did** (see "Publishes since the first deploy" above): the tree
held no `.vercel/` directory, both variables were exported, and `vercel deploy --yes`
published to `nonogram-studio` without a link prompt. Observed once, on CLI 59.11.7.

**The first publish comes after the GoatCounter site code, not before.** The publish
command above the deploy carries `--analytics` because a deploy counts, and the code it
would count to is the placeholder in the allow-list below until owner step 3 replaces
it. So for a publish made before that step, drop that one flag from the command: the
pages render and play with no snippet at all, and
`tests/test_public_player_pages.py::test_pages_work_with_analytics_blocked` is what holds
that. The reverse order sends production traffic to a site code that may not be
registered, and a visit that was never counted cannot be counted later.

## Usage counting

**GoatCounter** (DEC-046/ADR-0041). It gives visits, estimated uniques, country and
device. It sets no cookies, needs no consent banner, and **stores no raw IP for us**:
the per-book slug in the QR URL is the primary signal of which book drives visits, and
an IP is both personal data under GDPR and a poor unique-visitor key, because carrier
NAT puts thousands of phones behind one address.

What we ship is **one script tag and no package** — the runtime dependency baseline
(ADR-0006/R1) is untouched. The tag exists in exactly one place in the repository,
`player/assemble.py`'s `ANALYTICS_SNIPPET`, and the assembler injects it once into each
published page, so "include-once across all player pages" is a property of the one
definition rather than of three copies somebody keeps in step. The pages render and play
with the snippet **blocked or absent**: nothing on them waits for it, and
`tests/test_public_player_pages.py::test_pages_work_with_analytics_blocked` holds that
with the script aborted at the network layer rather than deleted from the page.

Nothing we ship reads, stores or transmits a visitor's IP or any per-visitor identifier
(ADR-0041/R6, G-3). The player's only storage is one `localStorage` entry per puzzle key
(ADR-0041/R4).

**What holds that claim, and what it does not reach.** Two things hold it together, and
neither alone: the assembled site's external references are a closed set, held to the
allow-list below, so there is no egress a visitor identifier could leave by; and every
request the pages actually issue is observed in a browser and held to method, origin and
path (`tests/test_player_shared_ui_site.py::test_every_control_every_gesture_the_solve_and_the_reload_are_clean` and its
plant, the `a-network-call-is-added` mutant of `tests/test_player_public_mode.py`). The static scan is the first half and it has a stated bound:
it is lexical, single-file and one-hop, it is default-deny **within** the reference
shapes it knows — a shape it finds and cannot place is a failure, never a silent pass —
and it is silent about a sink shape that is not in its set at all, such as a fetch
reached through an alias or markup assembled by `document.write`.

One residual inside that bound is worth naming, because it was measured rather than
imagined and because a narrowed admission reads as a bounded risk. The scan blanks
comments before two of its patterns read a file, and it recognises a comment delimiter by
the single character in front of it — so a `/*`, `<!--` or `//` opened from inside a
string literal, a CSS value, an attribute value or a regex literal can still make it
blank a region. Cycle 2 of CARD-285's review measured four such shapes swallowing a live
external reference and scanning **clean**. They do not any more, and the reason is not a
better guess about delimiters: everything that could hide egress — every absolute URL,
every quoted `//authority`, and every fetching position (`src=`, `href=`, a CSS `url()`,
a network call, a `.src =` assignment) — is read from the file **as written**, comments
included. (The identifier vocabulary is read raw as well, so a comment is not a hiding
place for an identifier read either; its miss could never have been egress, which is why
it is named separately here.)

**This paragraph understated its own cost until cycle 3 measured it, and the correction
is the point.** The sentence used to say that what a bad strip can cost is "a dangling
*internal* reference" and that every quoted `//host` is read as written. The second half
was true only for a **dotted letter-TLD** authority: the raw pattern required the
authority's last label to be two or more ASCII letters, while the stripped pattern that
reads quoted *rooted* paths also matches a quoted `//authority` and the scan classifies
anything beginning `//` as external. So for an IPv4 literal, a bracketed IPv6 literal or
a single-label host, the stripped pattern was the only reader, and four such live
references — an `import` of one, a bare CSS `@import` of one, a single-label host and an
IPv6 literal — were measured passing with **no finding at all**. Each one's no-comment
twin was caught in the same run, so the cause was the two ingredients together.

The raw pattern now reads any quoted `//` followed by a non-slash character, so the claim
above is true as written: an IP literal, a single-label host, a percent- or
unicode-encoded authority, a userinfo form and a port form are all read from the file as
written, and all seven shapes are planted as controls in `test_no_homegrown_tracking`,
each asserted to be a silent pass under the old pattern and a finding under this one.
**What remains unread is one shape, named here rather than discovered later:** an
**unquoted** `//authority`. That is refused on purpose — a bare `//` is a comment far
more often than a reference, and a pattern loose enough to read one also reads `//
assemble.py's` out of a comment — and it is why a protocol-relative target is read only
where a quote says the value is one. A `///path` is not in that gap: it has an empty
authority and resolves to this site's own `/path`.

The relaxation costs something in the other direction and it is named here too: a quoted
value that merely *begins* `//` — a comment parked in a string — is now reported, where
the narrower pattern said nothing. That is a false positive rather than a silent pass, so
it is the direction this scan is built to fail in; the served tree holds no such literal
today, and a finding is a sentence someone reads.

So what a bad strip can still cost is one reading of the two patterns that do read the
stripped text — an `import … from` specifier, or a quoted path genuinely rooted at the
site: a dangling *internal* reference going unreported. That is a defect worth knowing
about and it is not a channel anything can leave by.

The scan's vocabulary for "this names a visitor" is also declared rather than derived, and is a trip-wire for new
code rather than a proof: the set of spellings for an IP is not enumerable (CARD-282
measured a denylist of that shape missing 7 of 7 planted encodings). So the scan's job
is to make a new egress impossible to add quietly; the browser tests are what observe
the egress that exists. Widening either half is a decision, not a refactor.

### The analytics allow-list

**This block is the allow-list.** The assembly helper reads the endpoints from it, and
`tests/test_public_player_pages.py::test_no_homegrown_tracking` scans the assembled site
and fails on every external reference it finds that is not here — and on any reference
whose target it cannot classify at all. Adding an endpoint to the site therefore means
adding it here, on purpose, in this file. "Every reference it finds" is the honest
wording: the bound on what the scan looks for is stated above, beside the claim it
carries.

**The two blocks below are not one list.** A runtime endpoint may be fetched; a
non-runtime reference may not. The scan holds that split rather than documenting it: the
same URL that is clean inside `vercel.json` is a finding in a `src=`, an `href=`, a CSS
`url()`, an import specifier or a network call.

Runtime: the visitor's browser fetches these.

<!-- BEGIN analytics-allow-list -->
```
count  = https://nonogram.goatcounter.com/count
script = https://gc.zgo.at/count.js
```
<!-- END analytics-allow-list -->

`TODO(owner): confirm the GoatCounter site code.` `nonogram` is a placeholder; the real
code is whatever the owner registered. Change it here and re-run the helper — this is
the only line in the repository that holds it.

Non-runtime: named here so the scanner can classify them, and declared as what they are.
Nothing fetches these at page load.

<!-- BEGIN non-runtime-allow-list -->
```
vercel_schema = https://openapi.vercel.sh/vercel.json
```
<!-- END non-runtime-allow-list -->

**An endpoint written here has four shapes it may not have**, and each one is a
`ValueError` from `player/assemble.py`'s `with_analytics` rather than a silent
pass-through, because each is a way for a deployed page to count somewhere this list does
not name. A value must start with `https://` — a self-hosted counter on `http://` is
refused here, not downgraded; it must be a bare URL, with no quote, no `<` and no
whitespace in it; the document being counted must not already carry the
`data-goatcounter` attribute; and it must have exactly one `</head>`. A page with none or
two cannot be counted exactly once, and the assembler says so instead of guessing which
head to use. (Cycle 1 of CARD-285's review raised these as undeclared and the fix round
closed a renumbered item instead; this is the sentence it owed.)

`vercel.json`'s `$schema` is an editor hint. It is served because `vercel.json` is served
(the host reads it), and no page references it — which is an assertion and not a
reassurance: a page that fetched this URL would red `test_no_homegrown_tracking` even
though the URL is named right here, and removing this line reds the scan on
`vercel.json` itself.

## Drift check

Do this after any change to `player/**`, `vercel.json`, this page, or a Vercel dashboard
setting.

1. **This page vs. the dashboard.** Compare the production domain, the Output Directory
   and Auto-Deploy with the tables above. Replace a `TODO(owner)` with the value you
   saw, and date the edit.
2. **This page vs. the repo.** Re-run the helper. If the site now references an endpoint
   this page does not name, `test_no_homegrown_tracking` reds — fix the page or the site,
   never the test.
3. **The QR base vs. what is printed.** A book already printed carries the base it was
   printed with. Changing the base means the old QR codes need a redirect, which is a
   decision and not a deploy step.
4. **Do not count locally.** Counting is opt-in: the helper writes a snippet only with
   `--analytics`, so a bare local run cannot put development traffic in the owner's
   numbers. The rule is the default rather than a flag to remember — which is the same
   standard this page holds the scan to. **This rule binds the test suite
   too.** The two browser tests that drive the *counted* tree
   (`test_assembled_site_is_self_contained`, `test_pages_work_with_analytics_blocked`)
   both abort the hosts in the runtime block at the network layer, with the pattern
   derived from that block. A journey without the interceptor was measured sending three
   live requests to the script host per run — counted development traffic, a suite that
   depends on a vendor being reachable, and the cross-origin request shape CARD-283/284's
   same-origin controls forbid, re-introduced from the test side. Any new browser test
   over a counted tree carries the same two lines.

## One implementation: the public page runs the admin's own player (CARD-386, CARD-399)

`/play/<key>` runs the admin's own `solver.js`, `solver_state.js`, `admin.css` and
`tokens.css`, published as byte-identical build-time copies (ADR-0041/R3,
`COPIED_FROM_ADMIN` in `player/assemble.py`) with no override stylesheet; `solver.js` runs
in public mode, with no solution grid (CARD-385). `play/index.html` is a thin generated
shell: the admin's `puzzle_solve.html` markup rendered once at build time (the assembler
imports Jinja lazily for that, so **assembling needs the admin extra**, `pip install -e
'.[admin]'`), plus a loader that reads the key from the path, fetches `puzzle/<key>.json`
and hands `solver.js` an answer-free payload. There is no second implementation: the old
`player/play.js`, `play.html` and the play half of `player.css` were deleted in CARD-399, and
every change to the play surface is made once, in the admin files. `player/player.css` is
now the listing pages' stylesheet only.

The page needs **no Bootstrap file** (CARD-394). `admin.css` was written for a page that
also loads Bootstrap 5.3; the tree links the project's own `player/shared-ui-base.css`
instead (published as `/base.css`), a small hand-written file with the base rules and the
few classes the page uses, whose computed styles and layout rectangles are held to the real
Bootstrap's by `tests/test_player_base_css.py`. The tree passes the served-tree scan with
one known residue, `solver.js`'s relative `./solver_state.js` import. To re-run the fidelity
comparison live, set `NONOGRAM_REAL_BOOTSTRAP` to a local copy of Bootstrap 5.3's CSS
(never committed) when running that module; without it the module compares against the values
recorded from it.

**The old player can be rebuilt** until the shared-UI build is live in production: the local
git tag `play-js-last` marks the last commit that has `player/play.js` and the opt-in
shared-UI preview assembly (the old command-line flag for it is gone). Production itself serves whatever tree was last deployed; the
"What production is" tables above describe `play.js` deployments and are dated history.
