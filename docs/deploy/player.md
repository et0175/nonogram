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
  `player/assemble.py` needs the standard library and nothing else; it imports nothing
  from `nonogram` by name.
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
| `/play/<key>` | `play/index.html` | One document plays every puzzle; `play.js` reads the key out of the path and fetches `puzzle/<key>.json`. |
| `/b/<slug>` | `b/index.html` | The QR landing for one book. |
| `/library` | `library/index.html` | The extensionless path needs the rule; `/library/` would resolve by directory index. |

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
```
<!-- END qr-url-shapes -->

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

`TODO(owner): confirm the two variables are honoured on the first publish that relies
on them.` The 2026-10-30 deploy did **not** test them: it ran with a live
`.vercel/project.json` in the tree, so the variables were never the thing being read.
They are the mechanism Vercel documents for CI, where there is likewise no `.vercel/`
to read — documented, not observed, and this page keeps that distinction.

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
path (`tests/test_public_player.py::test_no_write_request_for_any_interaction` and the
three controls beside it). The static scan is the first half and it has a stated bound:
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
