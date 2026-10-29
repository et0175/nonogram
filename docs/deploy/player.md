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
       --bundle build/player-bundle --out build/site
   ```

   The helper is a thin driver: it reads the analytics endpoints and nothing else out of
   *this page*, then delegates every byte of the assembling to `player/assemble.py`.
   Pass `--no-analytics` for a tree with no counting snippet (what a local run and the
   test fixtures use), and `--print-only` to see the delegated command line without
   running it.
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

### The analytics allow-list

**This block is the allow-list.** The assembly helper reads the endpoints from it, and
`tests/test_public_player_pages.py::test_no_homegrown_tracking` scans the assembled site
and fails on any external reference that is not here — and on any reference whose target
it cannot classify at all. Adding an endpoint to the site therefore means adding it
here, on purpose, in this file.

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

`vercel.json`'s `$schema` is an editor hint. It is served because `vercel.json` is served
(the host reads it), and no page references it.

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
4. **Do not count locally.** The helper's `--no-analytics` is what a local run uses, so
   development traffic is not in the owner's numbers.
