// The Christmas book's decorations (CARD-421, CARD-422): shared by the book
// landing (pages.js) and the play page of a puzzle opened from a christmas
// book (the loader player/assemble.py writes). Placed by decor.css.

// --------------------------------------------------------------------------
// The Christmas book's decorations (CARD-421, owner 2026-11-11)
// --------------------------------------------------------------------------
// A pine garland along the top of the page and snow lying on its panels,
// drawn here as inline SVG the way the squares' pictures are (an HTML-parsed
// <svg>, no file to serve). Every colour is a class player.css paints from
// the theme's tokens. Both are aria-hidden and placed by player.css so they
// cover no control. Deterministic: the garland's needles come from a fixed
// seed, so every visit draws the same bough.

// The drift on a panel's top edge, viewBox 400x22 stretched to the panel.
const SNOW_PATH = "M0 10 L0 2.7 Q8.3 0.2 16.7 5.8 Q25.0 0.2 33.3 2.7 Q41.7 -0.7 50.0 1.8 Q58.3 -0.7 66.7 3.6 Q75.0 1.1 83.3 4.9 Q91.7 -0.8 100.0 1.7 Q108.3 -1.4 116.7 1.1 Q125.0 -1.4 133.3 4.8 Q141.7 1.1 150.0 3.6 Q158.3 -1.5 166.7 1.0 Q175.0 -1.5 183.3 2.2 Q191.7 -0.3 200.0 5.7 Q208.3 0.4 216.7 2.9 Q225.0 -1.5 233.3 1.0 Q241.7 -1.5 250.0 3.5 Q258.3 1.0 266.7 5.1 Q275.0 -0.4 283.3 2.1 Q291.7 -0.6 300.0 1.9 Q308.3 -0.6 316.7 5.3 Q325.0 2.1 333.3 4.6 Q341.7 -1.5 350.0 1.0 Q358.3 -1.5 366.7 2.7 Q375.0 0.2 383.3 4.9 Q391.7 1.1 400.0 3.6 L400 11 L392 11 Q391 16 385 16 Q379 16 378 11 L337 11 Q336 20 330 20 Q324 20 323 11 L245 11 Q244 17 238 17 Q232 17 231 11 L157 11 Q156 21 150 21 Q144 21 143 11 L62 11 Q61 18 55 18 Q49 18 48 11 L0 11 Z";

// One garland tile: 240x64 units, one swag dipping between its edges.
const GARLAND_TILE = 240;
const GARLAND_HEIGHT = 64;
// Enough tiles for a wide window at the garland's drawn height.
const GARLAND_TILES = 8;

function seeded(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

const fixed = (value) => value.toFixed(1);

export function garlandTile() {
  const rnd = seeded(421);
  const swag = (x) => 12 + 20 * Math.sin((Math.PI * x) / GARLAND_TILE);
  const needles = [];
  for (let layer = 0; layer < 2; layer += 1) {
    for (let i = 0; i <= GARLAND_TILE; i += 2) {
      const x = i + rnd() * 2 - 1;
      const y = swag(x) + rnd() * 6 - 3;
      for (let k = 0; k < 2; k += 1) {
        const angle = rnd() * 2 * Math.PI - Math.PI;
        const length = 5 + rnd() * 4 - layer;
        const shade = 1 + Math.floor(rnd() * 4);
        needles.push(
          `<line class="decor-needle-${shade}" x1="${fixed(x)}" y1="${fixed(y)}" ` +
            `x2="${fixed(x + length * Math.cos(angle))}" y2="${fixed(y + length * Math.sin(angle) * 0.8)}"></line>`
        );
      }
    }
  }
  const bauble = (cx, cy, r, tone) =>
    `<line class="decor-gold-line" x1="${fixed(cx)}" y1="${fixed(cy - r - 5)}" x2="${fixed(cx)}" y2="${fixed(cy - r)}"></line>` +
    `<rect class="decor-gold" x="${fixed(cx - 2)}" y="${fixed(cy - r - 2)}" width="4" height="3" rx="1"></rect>` +
    `<circle class="decor-${tone}" cx="${fixed(cx)}" cy="${fixed(cy)}" r="${r}"></circle>` +
    `<circle class="decor-shine" cx="${fixed(cx - r * 0.35)}" cy="${fixed(cy - r * 0.35)}" r="${fixed(r * 0.28)}"></circle>`;
  const mid = GARLAND_TILE / 2;
  const berries = [mid - 26, mid + 26, 8, GARLAND_TILE - 8].flatMap((x) =>
    [[0, 0], [3.5, 1.5], [1, 3.5]].map(
      ([dx, dy]) => `<circle class="decor-berry" cx="${fixed(x + dx)}" cy="${fixed(swag(x) + 2 + dy)}" r="2"></circle>`
    )
  );
  return (
    `<svg viewBox="0 0 ${GARLAND_TILE} ${GARLAND_HEIGHT}" preserveAspectRatio="xMinYMin meet" aria-hidden="true" focusable="false">` +
    `<g class="decor-bough">${needles.join("")}</g>${berries.join("")}` +
    bauble(mid, swag(mid) + 13, 8, "red") +
    bauble(mid - 52, swag(mid - 52) + 10, 5.5, "gold") +
    bauble(mid + 52, swag(mid + 52) + 10, 5.5, "gold") +
    "</svg>"
  );
}

export function snowMarkup() {
  return `<svg viewBox="0 0 400 22" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="decor-snow-fill" d="${SNOW_PATH}"></path></svg>`;
}

// Hang the garland at the top of the page and lay snow on each of `panels`.
// Called once, after the page has drawn, for a book whose theme has
// decorations: by pages.js on the landing (its number box, Continue card and
// section heads) and by the play page's loader (no panels: the board is left
// as it is).
export function decorate(panels = []) {
  const garland = document.createElement("div");
  garland.className = "decor-garland";
  garland.setAttribute("aria-hidden", "true");
  const tile = garlandTile();
  garland.innerHTML = tile.repeat(GARLAND_TILES);
  document.body.prepend(garland);
  const snow = snowMarkup();
  for (const panel of panels) {
    const drift = document.createElement("span");
    drift.className = "decor-snow";
    drift.setAttribute("aria-hidden", "true");
    drift.innerHTML = snow;
    panel.prepend(drift);
  }
}
