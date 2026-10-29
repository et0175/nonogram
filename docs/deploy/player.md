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

### Owner steps, in order

Each one says what evidence to bring back here, because this page is the only place the
repository records what production is.

1. **`TODO(owner)`: create the Vercel project** from this repository, with
   *Framework Preset:* **Other**, *Build Command:* **empty**, *Output Directory:* the
   directory the assembly helper wrote (see "Publishing a new bundle"). A static tree
   needs no build step and no toolchain (ADR-0041/R3). *Evidence to record here:* the
   production domain, and the Output Directory setting as the dashboard shows it.
2. **`TODO(owner)`: write the production domain into the QR block below**, replacing the
   placeholder, and re-run the assembly helper so the site and this page agree.
   CARD-210 (printed QR codes) is blocked on exactly this value.
3. **`TODO(owner)`: create the GoatCounter site**, note its code, and if it is not
   `nonogram` put the real one in the allow-list block below — in that one line — then
   re-run the helper. *Evidence to record here:* the site code and the date.
4. **`TODO(owner)`: confirm Auto-Deploy**. The admin panel's deploy was bitten by a
   dashboard setting nobody wrote down (`docs/deploy/render.md`, the 2026-09-23
   incident). *Evidence to record here:* the toggle's state and the date.

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
base    = https://nonogram-player.vercel.app
book    = {base}/b/{slug}
play    = {base}/play/{key}
library = {base}/library
```
<!-- END qr-url-shapes -->

`TODO(owner): copy the production domain from the Vercel dashboard` — the `base` above
is Vercel's default shape for a project named `nonogram-player` and has **not** been
observed. `{slug}` is `player_bundle.book_slug` of the book's ordered keys; `{key}` is
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
3. Deploy `build/site` with the Vercel CLI (`vercel deploy --prebuilt`) or let the
   dashboard's Output Directory point at it. `TODO(owner): record which of the two the
   project actually does.`

The output directory **is** the site: one directory holding the pages, the two
byte-identical copies from the panel (`solver_state.js`, `tokens.css`), `vercel.json`,
the rebuilt `puzzle/<key>.json` files, the rebuilt `index.json` and `book/<slug>.json`,
and a `.player-site` marker. Assembling into a directory deletes it first, and the
marker is what the assembler recognises its own output by, so a directory it did not
write is refused.

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
every quoted `//host`, every fetching position (`src=`, `href=`, a CSS `url()`, a network
call, a `.src =` assignment) and the identifier vocabulary — is read from the file **as
written**, comments included. What a bad strip can still cost is one reading of the two
patterns that do read the stripped text, an `import … from` specifier and a quoted rooted
path: a dangling *internal* reference going unreported. That is a defect worth knowing
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
