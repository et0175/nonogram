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
// The extent and the tier. **Never the puzzle's title**, which is the
// picture's name, and the absence is a decision, measured rather than
// stylistic:
//
//   * CARD-282 measured a stored puzzle name that is the base-64 of its own
//     grid travelling into the bundle's declared `title`, and a published
//     index.json decoding back to all 144 cells of a 12x12 answer. A scan
//     cannot answer "does this string carry a grid?" — the set of encodings
//     is not enumerable, and that card's denylist missed 7 of 7 planted
//     encodings — so CARD-283 removed the channel from the puzzle files
//     instead of filtering it, and routed the same question for these two
//     listings here. Same answer: player/assemble.py rebuilds both from a
//     closed schema and the entry schema has no `title` at all;
//   * the picture's name IS the answer, which is why CARD-163 took it out of
//     the admin player's own header (FR-044 AC-322/AC-323). A library of
//     named tiles would spoil every puzzle in it before a tap.
//
// So no tile on either page ever reads a `title` field, and no served entry
// has one to read.
//
// THE BOOK'S OWN TITLE IS A DIFFERENT FIELD, AND IT IS SHOWN
// ----------------------------------------------------------
// /b/<slug> renders the BOOK's display title as its heading (`readTitle`,
// written into [data-pages-title]). That is owner-authored editorial text
// about a book, not a picture's name, and it is served under ADR-0041/R2's
// THIRD EXEMPTION, granted by the owner on 2026-10-28. That exemption is
// the authority. This comment argued for one round that "EC-048's
// enumeration does not reach a book's title", and cycle 2 of this card's
// review measured that false: EC-048's fourth clause is "or data from which
// any solution cell is recoverable", which is R2's own wording and is not
// an enumeration anything can fail to be named in. R2 was amended rather
// than reinterpreted, and it exempts the title by SCOPE rather than by
// safety -- served on /b/<slug> and nowhere else, with the residual
// declared. Why the owner granted it: /b/<slug> is a book customer's first
// contact with the product seconds after scanning a code off paper and a
// page with no name on it is not that. player/assemble.py's
// EXEMPT_LISTING_FIELDS carries the exemption, the cost in bits, and the
// refusal that keeps the two fields apart; the two must never be argued as
// one, which is what cycle 1 of this card's review gated on.
//
// It is written with textContent and never innerHTML: an editorial string
// is still untrusted markup.
//
// /library shows no title of any kind — index.json carries none, and there
// is no book for it to be the title of.
//
// NOTHING IS WRITTEN AND NOTHING IS COUNTED (ADR-0041/R4, R6, EC-050)
// -------------------------------------------------------------------
// The only request either page issues is the GET of its own listing file.
// There is no localStorage write here either — a filter choice is not play
// state, and a page that remembered it would be keeping something about the
// visitor for no gain. ADR-0041/R6's counting tag belongs to CARD-285, which
// owns the test its check ref names; the note in the retired play.html applied here too.
//
// window.playerPages, set once a page has rendered (and left unset when the
// listing could not be read, so a test cannot mistake a failed load for an
// empty library):
//   entries        the entries as loaded, frozen, in source order
//   getShown()     the keys currently rendered, in rendered order
//   getFilters()   {tier, size} as chosen
//   slug           the book's slug, or null on the library
//   title          the book's served display title, or "" (always "" on
//                  the library, which has no book and no title field)

// CARD-422: the Christmas decorations live in their own module, shared with
// the play page.
import { decorate } from "/decor.js";

// A public puzzle key or book slug: the first 10 lowercase hex characters of
// a SHA-256 digest (ADR-0041/R1 for a key, R7 for a slug — the same
// truncation, so the same shape). Checked before anything is fetched, so a
// hand-typed path cannot turn into a request for an arbitrary file. Held to
// player_bundle.KEY_LENGTH from the test tree, where importing the package is
// legal; the same reimplement-and-cross-check precedent the retired play.js's KEY used.
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
// from the test tree instead. That is the same arrangement the retired play.js's KEY and
// assemble.py's SERVED_TIERS live under.
// How many characters of a book's display title the page will render,
// equal to assemble.py's SERVED_TITLE_MAX_CHARS and held to it from the
// test tree (the same arrangement TIERS and SIZE_BANDS live under). The
// server truncates already; this is the second half of the same
// check-on-both-sides-of-the-wire rule the rest of this file follows, and
// it is the reason a hand-edited book file cannot push a 10,000-character
// heading into the page.
export const TITLE_MAX_CHARS = 120;

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
// deliberately twice, once on each side of the wire, for the reason the retired play.js
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

// The book's display title `data` carries, or "" when it has none this page
// will render. Whitespace collapsed and truncated exactly as assemble.py's
// `_book_title` does it, because this page may be serving a file that was
// hand-edited after assembly — the same reason `isEntry` re-checks the
// entries assemble.py wrote.
//
// This is NOT a defence against an encoded grid, and the symmetry with
// `isEntry` stops here: a title is free text, there is no decision procedure
// for "does this string carry a grid?", and the field is served under a
// declared exemption rather than a bound. See the header.
export function readTitle(data) {
  return readLine(data, "title");
}

// One of the book file's editorial lines — "title", "series" or "authors"
// (CARD-418) — read exactly as readTitle reads the title: a string,
// whitespace collapsed, capped at TITLE_MAX_CHARS, else "". All three are
// served under the same exemption (assemble.py's EXEMPT_LISTING_FIELDS).
export function readLine(data, field) {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return "";
  const value = data[field];
  if (typeof value !== "string") return "";
  return value.split(/\s+/).filter((part) => part !== "").join(" ").slice(0, TITLE_MAX_CHARS);
}

// CARD-420: the book themes the site draws (tokens.css's
// :root[data-theme=...] blocks; assemble.py's SERVED_BOOK_THEMES). Anything
// else the file carries is the default look, "".
export const BOOK_THEMES = Object.freeze(["christmas"]);

export function readTheme(data) {
  if (data === null || typeof data !== "object" || Array.isArray(data)) return "";
  return BOOK_THEMES.includes(data.theme) ? data.theme : "";
}

// The query a puzzle link carries when it is opened from a book:
// /play/<key>?book=<slug>, so the play page can wear the book's theme
// (CARD-420). The library has no book, and its links stay /play/<key>. Every
// link keeps its literal /play/ prefix at the assignment, which is what the
// site's self-containment scan reads.
export function bookQuery(slug = null) {
  return slug === null ? "" : `?book=${slug}`;
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
// The book landing (CARD-418): sections, squares, progress, jump, continue
// --------------------------------------------------------------------------

// A book this short opens every section (see renderBook).
export const OPEN_ALL_UP_TO = 24;

const TIER_NAMES = { easy: "Easy", medium: "Medium", hard: "Hard", "": "Puzzles" };

// The book's puzzles cut into sections: one per run of consecutive puzzles
// with the same tier, in print order. A printed book is grouped by level
// (INV-009), so that is Easy, Medium, Hard; a book that is not grouped still
// shows every puzzle once and in print order, which is the order a reader
// matches against the page (AC-387). Each item carries its PRINT number.
export function sectionsOf(entries) {
  const sections = [];
  entries.forEach((entry, index) => {
    const last = sections.at(-1);
    const item = { entry, number: index + 1 };
    if (last !== undefined && last.tier === entry.tier) last.items.push(item);
    else sections.push({ tier: entry.tier, items: [item] });
  });
  return sections.map((section) => ({
    ...section,
    name: TIER_NAMES[section.tier] ?? TIER_NAMES[""],
    from: section.items[0].number,
    to: section.items.at(-1).number,
  }));
}

// The PRINT number a reader typed, as an index into `entries`, or null.
// Digits only (spaces around them allowed): "47" is puzzle 47, "4 7" and
// "47a" are not a number at all.
export function jumpTarget(text, entries) {
  const typed = String(text).trim();
  if (!/^[0-9]{1,4}$/.test(typed)) return null;
  const number = Number(typed);
  return number >= 1 && number <= entries.length ? number - 1 : null;
}

// --------------------------------------------------------------------------
// Progress, read from this device only
// --------------------------------------------------------------------------
//
// The player keeps one save per puzzle in localStorage under
// "nonogram-player:" + key (solver_state.js saveKey). A public save carries the
// puzzle's own clues and the reader's strokes, so this page rebuilds the
// board with the player's OWN reader (deserializeState) and decides "solved"
// with the player's own clue check (isClueSolved, ADR-0041/R2) — nothing is
// fetched for it, and no answer comes from the site: a solved square's
// picture is the reader's own board. Read only; this page writes nothing.
// Any storage or parse failure is "not started", never an error.

export const SAVE_PREFIX = "nonogram-player:";

// {state: "new" | "started" | "solved", board} for one entry. `board` is
// {width, height, cells} in the player's cell states, or null for "new".
export function progressOf(entry, text, state) {
  const none = { state: "new", board: null };
  if (typeof text !== "string" || state === null) return none;
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    return none;
  }
  if (data === null || typeof data !== "object" || data.width !== entry.width
      || data.height !== entry.height || !Array.isArray(data.rows) || !Array.isArray(data.columns)) {
    return none;
  }
  const payload = {
    id: entry.key, width: entry.width, height: entry.height,
    rows: data.rows, columns: data.columns, mode: state.PUBLIC_MODE,
  };
  let history;
  try {
    history = state.deserializeState(text, payload);
  } catch {
    return none;
  }
  if (history === null) return none;
  const board = history.board;
  if (state.isClueSolved(board, data.rows, data.columns)) return { state: "solved", board };
  if (board.cells.some((cell) => cell !== state.UNKNOWN)) return { state: "started", board };
  return none;
}

async function readProgress(entries) {
  const found = new Map();
  let state = null;
  try {
    state = await import("/solver_state.js");
  } catch {
    state = null;
  }
  for (const entry of entries) {
    let text = null;
    try {
      text = window.localStorage.getItem(SAVE_PREFIX + entry.key);
    } catch {
      text = null;
    }
    found.set(entry.key, progressOf(entry, text, state));
  }
  return found;
}

// The reader's black cells as one SVG path. A viewBox of the board's own
// extent, so it scales to the square. The <svg> is made by the HTML parser
// from a constant (a <template>), which gives it the SVG namespace without
// this file naming any URL; nothing from the save reaches markup, only
// numbers into attributes.
function boardPicture(board, filled) {
  const template = document.createElement("template");
  template.innerHTML = '<svg class="square-picture" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><path></path></svg>';
  const svg = template.content.firstElementChild;
  svg.setAttribute("viewBox", `0 0 ${board.width} ${board.height}`);
  let d = "";
  board.cells.forEach((cell, index) => {
    if (cell !== filled) return;
    const x = index % board.width;
    const y = Math.floor(index / board.width);
    d += `M${x} ${y}h1v1h-1z`;
  });
  svg.firstElementChild.setAttribute("d", d);
  return svg;
}

// One square of the book landing: a link to /play/<key> showing the print
// number and the reader's progress. Still a `.tile` with the key and tier on
// it, so everything that reads tiles (the order, the number) reads these.
export function squareFor(item, progress, slug = null) {
  const { entry, number } = item;
  const tile = document.createElement("a");
  tile.className = "tile square";
  tile.href = `/play/${entry.key}${bookQuery(slug)}`;
  tile.dataset.key = entry.key;
  tile.dataset.tier = entry.tier;
  tile.dataset.band = bandOf(entry) ?? "";
  tile.dataset.progress = progress.state;
  if (progress.board !== null) tile.append(boardPicture(progress.board, "filled"));
  const ordinal = document.createElement("span");
  ordinal.className = "tile-number";
  ordinal.textContent = String(number);
  tile.append(ordinal);
  const state = progress.state === "new" ? "" : `, ${progress.state}`;
  tile.setAttribute(
    "aria-label",
    `Puzzle ${number}, ${entry.width} by ${entry.height}${entry.tier === "" ? "" : `, ${entry.tier}`}${state}`
  );
  return tile;
}

function sectionFor(section, progress, open, slug) {
  const box = document.createElement("section");
  box.className = "book-section";
  box.dataset.tier = section.tier;
  const id = `book-section-${section.from}`;
  const head = document.createElement("button");
  head.type = "button";
  head.className = "book-section-head";
  head.setAttribute("aria-expanded", String(open));
  head.setAttribute("aria-controls", id);
  const dot = document.createElement("span");
  dot.className = "book-section-dot";
  dot.setAttribute("aria-hidden", "true");
  const text = document.createElement("span");
  text.className = "book-section-text";
  const name = document.createElement("span");
  name.className = "book-section-name";
  const range = section.from === section.to ? `puzzle ${section.from}` : `puzzles ${section.from}–${section.to}`;
  name.textContent = `${section.name} · ${range}`;
  const count = document.createElement("span");
  count.className = "book-section-count";
  const solved = section.items.filter((item) => progress.get(item.entry.key)?.state === "solved").length;
  count.textContent = `${solved} of ${section.items.length} solved`;
  text.append(name, count);
  const sign = document.createElement("span");
  sign.className = "book-section-sign";
  sign.setAttribute("aria-hidden", "true");
  sign.textContent = open ? "−" : "+";
  head.append(dot, text, sign);

  const grid = document.createElement("div");
  grid.className = "pages-list book-squares";
  grid.id = id;
  grid.hidden = !open;
  for (const item of section.items) grid.append(squareFor(item, progress.get(item.entry.key), slug));
  head.addEventListener("click", () => {
    const opening = grid.hidden;
    grid.hidden = !opening;
    head.setAttribute("aria-expanded", String(opening));
    sign.textContent = opening ? "−" : "+";
  });
  box.append(head, grid);
  return box;
}

// The puzzle a reader most likely wants to go back to: the started (not
// solved) one with the HIGHEST print number. A save carries no time, so
// "most recent" is not knowable here; the furthest one along the book is the
// honest stand-in (CARD-418 item 3).
export function continueTarget(entries, progress) {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    if (progress.get(entries[index].key)?.state === "started") return index;
  }
  return null;
}

function renderBook(page, entries, progress, slug) {
  const list = page.querySelector("[data-pages-list]");
  const count = page.querySelector("[data-pages-count]");
  const empty = page.querySelector("[data-pages-empty]");
  const sections = sectionsOf(entries);
  const resume = continueTarget(entries, progress);
  // Open by default: the first Easy section (the first section when there is
  // none), and the section holding the Continue puzzle. The rest start
  // closed, so a 160-puzzle book is three headers and one grid, not a scroll.
  // A short book (OPEN_ALL_UP_TO puzzles or fewer) opens everything: there is
  // no scroll to save, and a closed header would only hide a few squares.
  const firstEasy = sections.findIndex((section) => section.tier === "easy");
  const opened = firstEasy === -1 ? 0 : firstEasy;
  const all = entries.length <= OPEN_ALL_UP_TO;
  list.replaceChildren(
    ...sections.map((section, k) =>
      sectionFor(
        section,
        progress,
        all || k === opened || (resume !== null && resume + 1 >= section.from && resume + 1 <= section.to),
        slug
      )
    )
  );
  if (count !== null) count.textContent = entries.length === 1 ? "1 puzzle" : `${entries.length} puzzles`;
  show(empty, entries.length === 0);
  show(page.querySelector("[data-pages-legend]"), entries.length > 0);

  const card = page.querySelector("[data-pages-continue]");
  if (card !== null) {
    if (resume === null) show(card, false);
    else {
      const entry = entries[resume];
      card.href = `/play/${entry.key}${bookQuery(slug)}`;
      const tier = entry.tier === "" ? "" : ` · ${TIER_NAMES[entry.tier]}`;
      card.querySelector("[data-pages-continue-name]").textContent =
        `Puzzle ${resume + 1} · ${entry.width}×${entry.height}${tier}`;
      show(card, true);
    }
  }

  const jump = page.querySelector("[data-pages-jump]");
  if (jump !== null && entries.length > 0) {
    const input = jump.querySelector("[data-pages-jump-number]");
    const hint = jump.querySelector("[data-pages-jump-hint]");
    input.placeholder = `1–${entries.length}`;
    const say = () => {
      const index = jumpTarget(input.value, entries);
      if (input.value.trim() === "") hint.textContent = "Type the number printed above the grid.";
      else if (index === null) hint.textContent = `This book has puzzles 1 to ${entries.length}.`;
      else {
        const tier = entries[index].tier;
        hint.textContent = `Opens puzzle ${index + 1}${tier === "" ? "" : ` (${TIER_NAMES[tier]})`}.`;
      }
      return index;
    };
    input.addEventListener("input", say);
    jump.addEventListener("submit", (event) => {
      event.preventDefault();
      const index = say();
      if (index !== null) window.location.assign(`/play/${entries[index].key}${bookQuery(slug)}`);
    });
    show(jump, true);
  }
  return entries.map((entry) => entry.key);
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
  const announce = page.querySelector("[data-pages-announce]");
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
  // A filter change replaces the whole tile list, the count and the empty
  // note at once, and a reader who cannot see the page gets nothing from
  // any of it: the controls stay put, so there is no focus change to
  // notice. One polite live region carries the result instead — and it
  // carries the page's OWN wording (the count element's text, or the empty
  // note's) rather than a third copy of it, so the announcement cannot
  // drift from what is on screen. Focus is deliberately NOT moved: it is in
  // the select the reader just used, and moving it there would take the
  // keyboard away from the control being operated.
  if (announce !== null) {
    announce.textContent =
      shown.length === 0 && empty !== null
        ? empty.textContent.replace(/\s+/g, " ").trim()
        : count !== null
          ? count.textContent
          : "";
  }
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

  // The book's display title, into the heading. textContent, never
  // innerHTML: the string is owner-authored but it is still a value off the
  // wire, and the heading of a page a stranger reached by scanning a code
  // is the last place to interpret markup. A book with no served title
  // keeps the document's own fallback heading rather than showing an empty
  // one.
  const heading = page.querySelector("[data-pages-title]");
  const title = numbered ? readTitle(data) : "";
  if (heading !== null && title !== "") heading.textContent = title;

  if (numbered) {
    // CARD-418: the series above the title and "by <authors>" beside the
    // count, both textContent for the reason the title is.
    const series = readLine(data, "series");
    const authors = readLine(data, "authors");
    const seriesLine = page.querySelector("[data-pages-series]");
    if (seriesLine !== null && series !== "") {
      seriesLine.textContent = series;
      show(seriesLine, true);
    }
    const byline = page.querySelector("[data-pages-byline]");
    if (byline !== null && authors !== "") {
      byline.textContent = `by ${authors} · `;
      show(byline, true);
    }
    // CARD-420: the book's theme on the page's root, before its squares draw.
    const theme = readTheme(data);
    if (theme !== "") document.documentElement.dataset.theme = theme;
    const progress = await readProgress(entries);
    const shown = renderBook(page, entries, progress, slug);
    if (theme === "christmas") {
      decorate(page.querySelectorAll(".book-jump, .book-continue, .book-section-head"));
    }
    const announce = page.querySelector("[data-pages-announce]");
    const count = page.querySelector("[data-pages-count]");
    if (announce !== null && count !== null) announce.textContent = count.textContent;
    window.playerPages = {
      entries: Object.freeze(entries.map((entry) => Object.freeze({ ...entry }))),
      getShown: () => shown,
      getFilters: () => ({ tier: "", size: "" }),
      getProgress: () => Object.fromEntries([...progress].map(([key, value]) => [key, value.state])),
      slug,
      title,
      series,
      authors,
      theme,
    };
    return;
  }

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
    title,
  };
}

if (typeof document !== "undefined") load();
