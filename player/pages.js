// The two listing pages' glue — /library and /b/<slug> (COMP-011, FR-045,
// ADR-0041; CARD-284).
//
// One file for both doors, because they are the same page with two sources:
// the library reads index.json (every published puzzle), a book landing reads
// book/<slug>.json (that book's puzzles, in book order). Everything after the
// fetch — the tile, the link, the tier chip, the filters — is shared, so it
// is written once here and the two HTML documents differ only in which
// source they name and which controls they carry.
//
// WHAT A TILE SHOWS, AND WHAT IT DOES NOT
// ---------------------------------------
// The extent and the tier. Never a title — not the puzzle's and not the
// book's — and the absence is a decision, measured rather than stylistic:
//
//   * CARD-282 measured a stored puzzle name that is the base-64 of its own
//     grid travelling into the bundle's declared `title`, and a published
//     index.json decoding back to all 144 cells of a 12x12 answer. A scan
//     cannot answer "does this string carry a grid?" — the set of encodings
//     is not enumerable, and that card's denylist missed 7 of 7 planted
//     encodings — so CARD-283 removed the channel from the puzzle files
//     instead of filtering it, and routed the same question for these two
//     listings here. Same answer: player/assemble.py rebuilds both from a
//     closed schema and `title` is in neither;
//   * the picture's name IS the answer, which is why CARD-163 took it out of
//     the admin player's own header (FR-044 AC-322/AC-323). A library of
//     named tiles would spoil every puzzle in it before a tap.
//
// So this file never reads a `title` field, and there is none to read. The
// cost is named in the card: a book landing shows no book title. See
// player/assemble.py's docstring for what reopening that would take.
//
// NOTHING IS WRITTEN AND NOTHING IS COUNTED (ADR-0041/R4, R6, EC-050)
// -------------------------------------------------------------------
// The only request either page issues is the GET of its own listing file.
// There is no localStorage write here either — a filter choice is not play
// state, and a page that remembered it would be keeping something about the
// visitor for no gain. ADR-0041/R6's counting tag belongs to CARD-285, which
// owns the test its check ref names; the note in play.html applies here too.
//
// window.playerPages, set once a page has rendered (and left unset when the
// listing could not be read, so a test cannot mistake a failed load for an
// empty library):
//   entries        the entries as loaded, frozen, in source order
//   getShown()     the keys currently rendered, in rendered order
//   getFilters()   {tier, size} as chosen
//   slug           the book's slug, or null on the library

// A public puzzle key or book slug: the first 10 lowercase hex characters of
// a SHA-256 digest (ADR-0041/R1 for a key, R7 for a slug — the same
// truncation, so the same shape). Checked before anything is fetched, so a
// hand-typed path cannot turn into a request for an arbitrary file. Held to
// player_bundle.KEY_LENGTH from the test tree, where importing the package is
// legal; the same reimplement-and-cross-check precedent play.js's KEY uses.
const SLUG = /^[0-9a-f]{10}$/;

// The tier labels a chip and a filter may show, in the runtime's own order
// (easy, medium, hard — nonogram.difficulty.Tier, ordered for the book matrix
// by nonogram.admin.book_plan.TIERS). Served files carry one of these or the
// empty string, because assemble.py's _tier narrows anything else away. Held
// to that enum from the test tree.
export const TIERS = ["easy", "medium", "hard"];

// The size filter's bands, by LONGEST SIDE. Three bands, because the spec
// asks for three ("Size (10x10 / 20x20 / 30x30)", ONLINE_GAME_SPECIFICATION
// 1.1) — but the spec's three literals are square examples and the library
// holds oblong puzzles (25x15), so the rule is the longest side and the
// bounds partition the whole supported extent rather than naming three
// shapes.
//
// The bounds are MIN_SIZE..MAX_SIZE split into three equal bands. They are
// written here as numbers because a static page cannot read limits.py, which
// is the one thing CLAUDE.md's "use limits.py rather than writing 10 or 30"
// cannot have in a browser; the equality with limits.py — and the partition
// (every supported side in exactly one band, no gap, no overlap) — is held
// from the test tree instead. That is the same arrangement play.js's KEY and
// assemble.py's SERVED_TIERS live under.
export const SIZE_BANDS = [
  { id: "small", label: "Small", min: 10, max: 16 },
  { id: "medium", label: "Medium", min: 17, max: 23 },
  { id: "large", label: "Large", min: 24, max: 30 },
];

const longestSide = (entry) => Math.max(entry.width, entry.height);

// Which band an entry is in, or null when no band holds it — which cannot
// happen for a served entry (assemble.py's _extent refuses an extent outside
// MIN_SIZE..MAX_SIZE) and is still answered rather than assumed, because a
// filter that silently kept an unbanded entry would be the same silence the
// listings exist to remove.
export function bandOf(entry) {
  const side = longestSide(entry);
  return SIZE_BANDS.find((band) => side >= band.min && side <= band.max)?.id ?? null;
}

// --------------------------------------------------------------------------
// The payload, checked rather than trusted
// --------------------------------------------------------------------------

// Whether `entry` is one listing tile: a key-shaped key, two integer extents
// within the supported range, and a tier that is one of the served labels or
// blank. The same rule assemble.py applies when it writes the file —
// deliberately twice, once on each side of the wire, for the reason play.js
// gives: a page that trusts its input is a page whose input decides what it
// does.
export function isEntry(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const { key, width, height, tier } = value;
  if (typeof key !== "string" || !SLUG.test(key)) return false;
  for (const extent of [width, height]) {
    if (!Number.isInteger(extent)) return false;
    if (extent < SIZE_BANDS[0].min || extent > SIZE_BANDS.at(-1).max) return false;
  }
  return tier === "" || TIERS.includes(tier);
}

// The entries `data` carries, or null when it is not a listing this page can
// read. One shape for both files: {puzzles: [...]} — the library index and a
// book landing differ in which entries they hold and in their order, never in
// their shape, which is why one reader serves both.
export function readListing(data) {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return null;
  const { puzzles } = data;
  if (!Array.isArray(puzzles) || !puzzles.every(isEntry)) return null;
  return puzzles;
}

// --------------------------------------------------------------------------
// Drawing
// --------------------------------------------------------------------------

// One tile: a link to /play/<key> carrying the extent and, when there is one,
// the tier chip. A link and not a button, so it opens in a new tab, can be
// copied, and works with the keyboard without a line of script.
export function tileFor(entry, number) {
  const tile = document.createElement("a");
  tile.className = "tile";
  tile.href = `/play/${entry.key}`;
  tile.dataset.key = entry.key;
  tile.dataset.tier = entry.tier;
  tile.dataset.band = bandOf(entry) ?? "";

  if (number !== null) {
    const ordinal = document.createElement("span");
    ordinal.className = "tile-number";
    ordinal.textContent = String(number);
    tile.append(ordinal);
  }

  const size = document.createElement("span");
  size.className = "tile-size";
  // The multiplication sign, not the letter x: this is the extent as the
  // panel's own lists write it.
  size.textContent = `${entry.width}×${entry.height}`;
  tile.append(size);

  if (entry.tier !== "") {
    const chip = document.createElement("span");
    chip.className = "player-tier tile-tier";
    chip.textContent = entry.tier;
    tile.append(chip);
  }

  const label = number === null ? "" : `Puzzle ${number}, `;
  tile.setAttribute(
    "aria-label",
    `${label}${entry.width} by ${entry.height}${entry.tier === "" ? "" : `, ${entry.tier}`}`
  );
  return tile;
}

// --------------------------------------------------------------------------
// The page
// --------------------------------------------------------------------------

function show(element, visible) {
  if (element !== null) element.hidden = !visible;
}

function fail(page, message) {
  const notice = page.querySelector("[data-pages-notfound]");
  const text = page.querySelector("[data-pages-notfound-text]");
  if (text !== null && message !== null) text.textContent = message;
  show(notice, true);
  show(page.querySelector("[data-pages-list]"), false);
  show(page.querySelector("[data-pages-filters]"), false);
  show(page.querySelector("[data-pages-loading]"), false);
}

// `numbered` is the book landing: a reader matching a tile against a printed
// page needs the puzzle's number in the book, and the number is its position
// in the served order rather than a field (there is no such field, and the
// order is AC-387's requirement).
function render(page, entries, filters, numbered) {
  const list = page.querySelector("[data-pages-list]");
  const count = page.querySelector("[data-pages-count]");
  const empty = page.querySelector("[data-pages-empty]");
  const shown = [];
  list.replaceChildren();
  entries.forEach((entry, index) => {
    if (filters.tier !== "" && entry.tier !== filters.tier) return;
    if (filters.size !== "" && bandOf(entry) !== filters.size) return;
    list.append(tileFor(entry, numbered ? index + 1 : null));
    shown.push(entry.key);
  });
  if (count !== null) {
    count.textContent = shown.length === 1 ? "1 puzzle" : `${shown.length} puzzles`;
  }
  show(empty, shown.length === 0);
  return shown;
}

async function load() {
  const page = document.querySelector("[data-pages-page]");
  const numbered = page.dataset.pagesPage === "book";
  let source = "/index.json";
  let slug = null;
  if (numbered) {
    const segments = window.location.pathname.split("/").filter((part) => part !== "");
    const last = segments.at(-1);
    slug = last !== undefined && SLUG.test(last) ? last : null;
    if (slug === null) {
      fail(
        page,
        "This address names no book. A book link looks like /b/ followed by ten letters and digits."
      );
      return;
    }
    source = `/book/${slug}.json`;
  }

  let data;
  try {
    const response = await fetch(source, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    data = await response.json();
  } catch {
    fail(page, null);
    return;
  }
  const entries = readListing(data);
  if (entries === null) {
    fail(page, "This page's listing could not be read, so no puzzles were shown.");
    return;
  }

  show(page.querySelector("[data-pages-loading]"), false);
  show(page.querySelector("[data-pages-notfound]"), false);
  show(page.querySelector("[data-pages-list]"), true);

  const filters = { tier: "", size: "" };
  const controls = [...page.querySelectorAll("[data-pages-filter]")];
  let shown = render(page, entries, filters, numbered);
  // `shown` is read through the closure below, so re-rendering is the whole
  // of a filter change: there is no second copy of the rendered set to keep
  // in step with the DOM.
  for (const control of controls) {
    control.addEventListener("change", () => {
      filters[control.dataset.pagesFilter] = control.value;
      shown = render(page, entries, filters, numbered);
    });
  }
  const clear = page.querySelector("[data-pages-clear]");
  clear?.addEventListener("click", () => {
    for (const control of controls) {
      control.value = "";
      filters[control.dataset.pagesFilter] = "";
    }
    shown = render(page, entries, filters, numbered);
  });
  if (controls.length > 0) show(page.querySelector("[data-pages-filters]"), true);

  window.playerPages = {
    entries: Object.freeze(entries.map((entry) => Object.freeze({ ...entry }))),
    getShown: () => shown,
    getFilters: () => ({ ...filters }),
    slug,
  };
}

if (typeof document !== "undefined") load();
